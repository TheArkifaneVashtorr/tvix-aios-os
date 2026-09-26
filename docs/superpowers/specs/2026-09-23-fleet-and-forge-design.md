# A declared fleet, and the forge host on the LAN — design

**Status:** draft, 2026-09-23. Operator answers taken the same evening:
- the forge runs on a second machine on the LAN, which already runs NixOS;
- it is LAN-only for v1;
- machines are linked over SSH, declared in this flake and automated, using plain
  NixOS (no deploy tool) with a YubiKey-backed deploy key.

The first step toward the forge the lease spec
(`docs/superpowers/specs/2026-09-23-lease-and-verify-design.md` §3) and the public
evidence page (`docs/decisions/2026-09-23-democratic-os-answers.md`, "Public
evidence") both need. The lease assigner and leases themselves are not in this
spec; the lease spec is held by the operator.

## 1. What exists

Measured on 2026-09-23:

- **SSH is off on core.** `services.openssh.enable` evaluates to `false`. No
  `programs.ssh` settings exist, `users.users.<operator>.openssh.authorizedKeys` is
  empty, and nothing is pinned in `knownHosts`.
- **The YubiKey is used only for basket unlock**, through `age-plugin-yubikey` (the
  PIV applet; `keys.toml`, `keys/recipients.txt`, `tools/enroll-yubikey.sh`). No
  FIDO2 SSH key exists.
- **The flake has one host,** `nixosConfigurations.core` (`flake.nix:1899`), with a
  flat `hosts/core/` layout. Its `hardware-configuration.nix` is verbatim generator
  output: it is exempt from formatting (`treefmt.toml:4-10`) and hash-pinned in lint
  (`flake.nix:2373-2382`). Host facts are asserted by checks (`host-core`,
  `core-*-wiring`).
- **Secrets** are hand-placed files under `/var/lib/secrets`, with permissions set
  by tmpfiles (`nixosModules/seatLane.nix:329`).
- **Backups** use `services.proton-backup`, a parameterised module
  (`nixosModules/protonBackup.nix`): restic to a local repo, then pushed to Proton
  Drive.
- **Forgejo 16.0.3** and `services.forgejo` are in the pinned nixpkgs.
- **No fleet exists:** no `target-host`, deploy tool or remote deploy anywhere.

## 2. The fleet: one list, everything derived

A module, `nixosModules/fleet.nix`, reads one declared list. The list lives in
`hosts/fleet.nix`, and every host imports the module:

```nix
fleet.machines = {
  core  = { address = null;           hostKey = "ssh-ed25519 AAAA…"; roles = [ "operator" ]; };
  forge = { address = "192.168.x.y";  hostKey = "ssh-ed25519 AAAA…"; roles = [ "forge" ]; };
};
fleet.deployKeys = [ "sk-ssh-ed25519@openssh.com AAAA… yubikey-<serial>" ];
```

From that list every host gets two things:

- **Pinned identities.** `programs.ssh.knownHosts.<name>` for every other machine.
  A host whose key differs from the declared one is refused, never trusted on first
  use.
- **Who may deploy.** A machine with a role that accepts deploys runs
  `services.openssh` with `PasswordAuthentication = false` and
  `KbdInteractiveAuthentication = false`. It listens only on the LAN interface, and
  its firewall opens port 22 only to the LAN subnet. It authorises only the declared
  `deployKeys`, for a dedicated `deploy` user that holds sudo rights for
  `nixos-rebuild` switching and nothing else.

**Core never runs an SSH server** (the lease spec's "core never accepts an inbound
connection"). Core only initiates. The module asserts at evaluation time that no
machine with the `operator` role enables `services.openssh`.

**The deploy key is a FIDO2 key on the operator's YubiKey** (`ed25519-sk`, touch
required, created with `ssh-keygen -t ed25519-sk -O verify-required`). It is a
separate applet from the PIV slot the baskets use, and OpenSSH supports it natively
with no new tool. Every deploy needs a physical touch, so no process can push to a
machine silently, and that includes the orchestrator. The second YubiKey holds a
second enrolled deploy key as the backup.

## 3. Deploying

Core builds each machine's system and switches it remotely with the built-in
`nixos-rebuild switch --flake .#<name> --target-host deploy@<address> --use-remote-sudo`.
It is wrapped as one command, `tools/fleet deploy <name>`, which:

1. builds the system and prints `nix store diff-closures` against the machine's
   current system (fetched over SSH) before switching;
2. switches, which takes the operator's touch;
3. confirms the machine answers over SSH afterwards.

The same rules as core apply. The orchestrator only builds and prints the command,
and the operator runs it. `nixos-rebuild`'s own rollback
(`--rollback --target-host`) is the recovery path, and the runbook states it.

## 4. Enrolling a machine

Enrolment happens once per machine and needs the operator at both machines.

1. **On the new machine's console,** the operator runs `fleet-join`: a short
   standalone script, copied from core by USB or typed from the runbook. It enables
   the SSH server on the LAN for the declared deploy keys only (an imperative
   bootstrap that the first real deploy replaces), then prints the machine's host-key
   fingerprint and its LAN address.
2. **On core,** `tools/fleet enroll <name> <address>`:
   - fetches the host key over SSH, and the operator confirms it matches the
     fingerprint shown on the console;
   - fetches `nixos-generate-config --show-hardware-config` read-only;
   - writes `hosts/<name>/hardware-configuration.nix` verbatim and adds the fleet
     entry.

   The operator commits both, which is the approval.
3. **The first `tools/fleet deploy <name>`** replaces the bootstrap with the
   declared configuration.

Later, `nixos-anywhere` can do fresh installs the same way. It is not in v1.

## 5. The forge host, v1

`hosts/forge/` follows `hosts/core`'s layout: `default.nix`, the verbatim
`hardware-configuration.nix` (format-exempt and hash-pinned like core's), and
feature files.

- **Forgejo** (`services.forgejo`) serves the web UI and git over SSH on the LAN
  only. Registration is closed, and accounts are created by the operator.
- **LAN access** reuses `services.lan-access`, the bcrypt-gated reverse proxy core
  already uses for the Helm and the worlds, running on the forge for its own site.
  The firewall opens only the proxy's port and SSH, and only to the LAN subnet.
- **Repo mirroring.** Core pushes to the forge outbound: a user timer runs
  `git push` of `main` and the release tags, using a push-only key held in the
  operator's account. The forge never pulls from core.
- **Secrets** (the Forgejo admin token, the push key's forge-side account) use the
  existing `/var/lib/secrets` convention.
- **Backups** are a second `services.proton-backup` instance with the forge's own
  repo, password and paths (the Forgejo state directory).
- **Not in v1:** the lease assigner, leases, the pre-receive hooks, the evidence
  page, and any internet exposure. Each arrives with its own spec.

## 6. Acceptance

- **The fleet module:**
  - an evaluation check asserts each declared host's `knownHosts` contains every
    other machine's declared key and no other key;
  - it asserts core has no `services.openssh`;
  - it asserts the forge's SSH refuses password logins and listens only on the LAN
    interface.
- **Pinning.** A VM test with two machines: deploying to a machine whose host key
  differs from the declared one fails before anything is copied.
- **Deploy.** The same VM test: core's deploy switches the forge, and a key that is
  not declared cannot log in. (The test key stands in for the YubiKey. The touch
  requirement is checked once by hand, and the runbook says so.)
- **The forge,** as `forge-wiring` checks:
  - Forgejo is enabled;
  - registration is off;
  - it is bound to the LAN;
  - the proxy is in front of it;
  - the backup instance exists and its paths are documented in
    `docs/runbooks/backup.md`.
- **Enrolment.** `tools/fleet enroll` writes a `hardware-configuration.nix` that is
  byte-identical to the machine's own generator output, and it refuses when the
  fetched host key does not match the fingerprint the operator types.
- **The hardware file** is hash-pinned in lint, like core's.

## 7. Operator steps

1. Create the FIDO2 deploy key on each YubiKey. The runbook gives the one command.
2. Run `fleet-join` on the forge machine's console, then `tools/fleet enroll forge
   <address>` on core, and commit.
3. Run `tools/fleet deploy forge` and touch the key.

## 8. Not in this design

- Internet exposure: the VPS relay or the isolated port forward, decided when the
  first outside contributor is near.
- A deploy tool with automatic rollback (deploy-rs, Colmena).
- Declarative secrets tools (agenix, sops-nix).
- Fresh installs with `nixos-anywhere`.
- The lease assigner, the evidence page, and contributor machines. Those use the
  fleet but are specced separately.
