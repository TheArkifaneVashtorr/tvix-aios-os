# A fleet installer image: a fresh forge from one USB, SSH from first boot — design

**Status:** draft, 2026-09-25, measured at HEAD `6cfadfcd`. Not yet judged.
Operator request the same day: "a more complete installation process over
the USB … fresh install what we need and redo the ssh authentication".
Approved in outline: an installer USB built from this flake; the current
forge is recovered by hand meanwhile.

## 1. Purpose

The fleet spec (`docs/superpowers/specs/2026-09-23-fleet-and-forge-design.md`
§4) joins a machine that **already runs NixOS**: a console bootstrap, then
`fleet enroll`, then `fleet deploy`. On the forge (2026-09-24/25) that path
cost a hand install, a live 25.05→26.05 switch that killed the GNOME session,
a deleted login account, a failed first switch and four console-only steps
(open bugs `BUG-forge-user-declared-from-core`,
`BUG-fleet-first-deploy-before-proxy-password`,
`BUG-fleet-drops-remote-error-output`,
`BUG-forge-backup-cannot-read-forgejo`, `docs/ledger/bugs.toml`).

Here, for a machine already declared and enrolled, one ISO built on core
installs the declared system offline, takes the password and two secrets at
the console, and boots into a machine core reaches over SSH.

**Goals, each with its acceptance:**

- **G1 — one image, no hand install.** `nix build .#installer-forge` yields
  an ISO; booted on the forge it ends at a login prompt of the *declared*
  26.05 system after one reboot. Acceptance: A1, A2.
- **G2 — the account exists and logs in.** The operator account's name comes
  from one declared field; the password typed at the console logs in; no
  password or hash is in git or the store. Acceptance: A3, A4.
- **G3 — SSH from first boot.** The deploy user and the operator account
  accept the declared YubiKey keys and nothing else; the operator can reboot,
  write the proxy hash and create the Forgejo admin from core. Acceptance:
  A5.
- **G4 — nothing fails on first boot.** `systemctl --failed` is empty and
  caddy answers. Acceptance: A6.
- **G5 — the wipe cannot hit the wrong disk.** The destructive step runs only
  after the operator types the serial of the disk shown on screen.
  Acceptance: A7.

## 2. What exists

Commands run on core in the devShell with `XDG_CACHE_HOME` under `/tmp`.
`<probe>` is a throw-away `nix eval --impure -f` file in the session's
scratch directory that `builtins.getFlake`s this checkout; its expression is
quoted where it matters.

1. **The pinned host nixpkgs has the installer modules and the ISO builder.**
   `nix eval --raw --impure --expr '(builtins.getFlake "git+file://$PWD").inputs.nixpkgs-host.outPath'`
   → a `-source` path; `ls <it>/nixos/modules/installer/cd-dvd/` lists
   `installation-cd-minimal.nix`, `installation-cd-graphical-gnome.nix`,
   `iso-image.nix`; `cat <it>/.version` → `26.05`.
2. **An ISO carrying the forge's declared system evaluates.** `<probe>`:
   `nixpkgs-host.lib.nixosSystem { modules = [ installation-cd-minimal.nix { isoImage.storeContents = [ forge.toplevel ]; } ]; }`
   → `drv` `…-nixos-minimal-26.05.20260903.a5cc6f2-x86_64-linux.iso.drv`,
   `squashfsCompression` `zstd -Xcompression-level 19`, in 22 s.
   `nix build --dry-run <drv>^out` → `89 derivations will be built`,
   `83 paths will be fetched (69.4 MiB download, 159.6 MiB unpacked)`.
   **Not built** (the squashfs of fact 3's closure is the cost; §9).
3. **The forge's closure.** `nix eval --raw .#nixosConfigurations.forge.config.system.build.toplevel.outPath`
   → `/nix/store/xz85l1sd…-nixos-system-forge-26.05.20260903.a5cc6f2`,
   present on core; `nix path-info -Sh <it>` → `6.8 GiB`;
   `nix path-info -r <it> | wc -l` → `1446`. Largest members
   (`nix path-info -rs | sort -k2 -n | tail`): linux-firmware 782 MiB,
   mbrola-voices 645 MiB, llvm-lib 540 MiB, mesa 264 MiB (GNOME, FL4's
   desktop answer).
4. **The forge's toplevel does not depend on its own host key or its
   stateVersion.** `<probe>`: `forge.extendModules` with
   `fleet.machines.forge.hostKey = mkForce "<another ed25519 key>"` → the
   toplevel `drvPath` is **equal** (`"same":true`); the machine's own entry
   never reaches its own `knownHosts` (`forge.config.programs.ssh.knownHosts`
   → `{}`). The same with `system.stateVersion = mkForce "26.05"` →
   `"same":true`; `services.forgejo.package.name` → `forgejo-lts-15.0.7`
   under both (the module's `mkPackageOption pkgs "forgejo-lts"`, not
   stateVersion).
5. **The disk layout is two by-uuid filesystems.**
   `hosts/forge/hardware-configuration.nix` (generator output, hash-pinned in
   `hosts/hardware-pins.sha256`): `/` ext4 and `/boot` vfat with
   `fmask=0077 dmask=0077`, both `/dev/disk/by-uuid/…`, no swap.
   `nix eval --json .#nixosConfigurations.forge.config.fileSystems` confirms
   the two devices. `fileSystems.<n>.device` is `null or string` — a second,
   different definition of it (a disko layout) is a merge conflict.
6. **Both mkfs tools can set the IDs the hardware file pins.**
   `mkfs.ext4` usage shows `[-U UUID]`; `mkfs.fat --help` shows
   `-i VOLID  Set volume ID to VOLID (a 32 bit hexadecimal number)`
   (e2fsprogs 1.47.4, dosfstools 4.2 in the local store).
7. **No disko.** `grep -c disko flake.lock` → `0`; no `*disko*` path in the
   store; `jq '.nodes | length' flake.lock` → `15`.
8. **The account is declared from core's name.** `grep -rnc '<operator>'`
   finds the name once each in `hosts/forge/default.nix`,
   `hosts/forge/lan-access.nix` (the proxy's basic-auth user),
   `hosts/forge/proton-backup.nix`, and twice in
   `nixosModules/protonBackup.nix` (the `passwordFile` default under the
   operator's home). Core declares its own at `hosts/core/default.nix:166`
   (uid 1000). `hosts/*` is withheld from publication
   (`docs/ledger/publish.toml:101`); the name is a deny word (`[deny] words`).
9. **User creation.** `nix eval` on the forge: `users.mutableUsers` → `true`,
   `services.userborn.enable` → `false`, `systemd.sysusers.enable` → `false`;
   two normal users (the operator, `deploy`). The option text
   (`nixos/modules/config/users-groups.nix:87-109`): with `mutableUsers`
   true, `hashedPasswordFile` "will only be set when the user is created for
   the first time"; with no password option the user "will not be able to do
   password-based logins" — the forge's lockout.
10. **nixos-install activates inside the target.** `nixos-install.sh` accepts
    `--system|--closure|--store-path`, `--flake`, `--no-channel-copy`,
    `--no-root-passwd`; line 310 runs `nixos-enter` then
    `switch-to-configuration boot`; `nixos-enter.sh:104` runs
    `$system/activate` in the chroot — users are created there, from files
    already under the mount point.
11. **SSH today.** `nixosModules/fleet.nix` renders sshd for a
    deploy-accepting machine: `listenAddresses` = the declared address,
    `PasswordAuthentication`/`KbdInteractiveAuthentication` false,
    `PermitRootLogin "no"`, one nft rule for port 22 from the LAN subnet, and
    `users.users.deploy.openssh.authorizedKeys.keys = fleet.deployKeys`. The
    forge's evaluated `services.openssh.settings` carries **no
    `PubkeyAuthOptions`**, and the two `deployKeys` lines in
    `hosts/fleet.json` carry no `verify-required` option: the keys were made
    with `-O verify-required` (plan §Operator step 3) but the server does not
    demand the PIN attestation.
12. **deploy is already root-equivalent.** Its sudo rule is NOPASSWD
    `/nix/store/*/bin/switch-to-configuration switch` (`fleet.nix`
    `sudoRule`); `nix.settings.trusted-users` on the forge → `["root","deploy"]`
    (so an unsigned path it copies is accepted, FL9). Whoever holds a deploy
    key can make any store path the running system.
13. **The operator's sudo.** Forge `security.sudo` → `enable true`,
    `wheelNeedsPassword true`; the operator is in `wheel`.
14. **The proxy hash and the backup password.** `nixosModules/lanAccess.nix`
    reads `{file.<hashFile>}` in the Caddyfile and creates
    `/var/lib/lan-access` `0710 root caddy` by tmpfiles; the group's gid is
    static (`users.groups.caddy.gid` → `239`). The restic job reads
    `passwordFile` (default under the operator's home) on a `daily`,
    `Persistent` timer (`nixosModules/protonBackup.nix:43-97`).
15. **The stock installer is a network surface.** `<probe>` on plain
    `installation-cd-minimal.nix`: `services.openssh.enable` → `true`,
    `PermitRootLogin` → `"yes"`, `networkmanager.enable` → `true`,
    `isoImage.makeEfiBootable`/`makeUsbBootable` → `true`
    (`installation-device.nix:79-90`: login only after a password or key is
    added).
16. **VM tests can do both halves.** nixpkgs `nixos/tests/installer.nix`
    (`makeInstallerTest`, lines 705-830): an `installer` node with
    `profiles/installation-device.nix`, a shared `./target.qcow2`, the
    install's inputs in `system.extraDependencies`, substituters off; a
    `target` node with `useBootLoader` and `useEFIBoot` boots the result.
    `nixos/tests/boot.nix:65-73,162-183` boots a real `isoImage` (with
    `test-instrumentation.nix`) as a CD and a USB drive under OVMF. Core's
    `system-features` → `benchmark big-parallel kvm nixos-test`.
    `tests/integration/fleet-vm.nix:20` takes throw-away keys from nixpkgs'
    `tests/ssh-keys.nix`.
17. **Nothing on the forge is worth keeping.** `grep -c mirror hosts/fleet.json`
    → `0` (plan step 10 never ran, so no repository was pushed); the Forgejo
    admin (step 9) and the restic repository are console-side and unmeasured
    from core (§9).
18. **enroll needs the bootstrap's sudo.** `fleet.py` `cmd_enroll` runs
    `sudo -n …/nixos-generate-config --show-hardware-config`; only the
    bootstrap module (`pkgs/fleet/fleet-join.nix`) grants it — the declared
    deploy rule set (fact 12) does not. `enroll` against an installed,
    declared machine fails at its hardware step.

## 3. Decisions

### D1 — The image: one ISO per declared machine, the minimal installer, the closure baked in

**Recommendation.** A function `mkInstaller <machine>` over
`nixpkgs-host.lib.nixosSystem` with `installation-cd-minimal.nix`, plus
`isoImage.storeContents = [ nixosConfigurations.<machine>.toplevel ]` and the
`fleet-install` program; exposed as `nixosConfigurations.installer-forge` and
`packages.x86_64-linux.installer-forge` (its `system.build.isoImage`). The
installer's own sshd and NetworkManager are **off**
(`services.openssh.enable = false`, `networking.networkmanager.enable = false`,
no DHCP): the install is offline, so the image has no network surface.
`isoImage.squashfsCompression` stays the default unless the plan's first
build measures it too slow (§9).

**Reason.** Fact 2 (it evaluates on the pinned set); fact 15 (the stock image
runs sshd with root login); the per-machine image is the one whose baked
closure is exactly what `fleet deploy` would have switched to (fact 3).

**Rejected.** *A generic ISO with a machine argument*: it bakes every
machine's closure or fetches one (D3). *A graphical installer*: the declared
system brings its own GNOME. *`nixos-anywhere`* (fleet spec §8): a new input
driving the install over SSH into a running installer — the network surface
this image removes.

### D2 — Partitioning: scripted, recreating the enrolled filesystem IDs

**Recommendation.** `fleet-install` reads the two IDs from the machine's
evaluated `fileSystems` at **build** time (`/` → ext4 UUID, `/boot` → vfat
volume ID) and on the chosen disk writes: a GPT; partition 1 ESP (FAT32, the
volume ID, size a plan-time fact read from the current machine, default
1 GiB); partition 2 the rest as ext4 with the UUID (`mkfs.ext4 -U`,
`mkfs.fat -i`, fact 6). `hosts/forge/hardware-configuration.nix` and its pin
stay byte-identical, so the baked toplevel is the one core already built
(fact 3). Before `mkfs` it refuses if any *other* block device already
answers `blkid -U <uuid>`.

**The wipe's confirmation.** The script lists candidate disks
(`lsblk -d -o NAME,MODEL,SERIAL,SIZE,TRAN`), excludes the device the ISO
booted from, and asks the operator to **type the serial** of the target
disk; a mismatch, an empty serial, or a disk that is the boot medium ends
the run with nothing written. It then prints the partition table it will
write and asks for the word `wipe`. With a declared `disk` serial (question
Q4) the script pre-selects that disk and still requires the typed serial.

**Reason.** Fact 5 (two by-uuid filesystems), fact 6 (the tools set the IDs),
fact 7 (no disko today). A layout owned by the hardware file keeps one
source of truth for the mounts.

**Rejected.** *disko* (a new input; MIT per upstream, unmeasured here): its
layout defines `fileSystems`, which conflicts with the hardware file's
(fact 5), so either the pinned generator file is edited or disko only
partitions and loses its point — one more input (fact 7) for two
filesystems. Revisit for generic machines (§7). *Fresh UUIDs, re-enrolled*:
a new toplevel after the install — the two-stage path this spec removes.
*Labels*: the same edit to the generator file.

### D3 — Install: `nixos-install --system`, offline, from the ISO's store

**Recommendation.** After mounting at `/mnt` and placing the secrets (D4,
D6, D7): `nixos-install --system <baked toplevel> --no-root-passwd
--no-channel-copy --root /mnt`. The ISO's store is the only source.

**Reason.** Fact 10: `--system` takes a built closure; nothing is evaluated
on the forge. Fact 3: the closure exists on core already.

**Rejected.** *`--flake <store path>#forge`*: evaluates on the installer,
needs every input in the ISO, yields the same path at best. *Fetching from
core over the LAN*: core never accepts an inbound connection (fleet spec
§2; `fleet.nix` assertion (c)). *A small ISO plus `fleet deploy` after
first boot*: the first boot runs an undeclared system — the forge's
original failure.

**Cost.** One image of the 6.8 GiB closure compressed (size unmeasured, §9);
the USB must hold it. A new generation of the forge means a new image only
for a *reinstall*; day-to-day changes still go through `fleet deploy`.

### D4 — The operator account: declared once, password typed at install

**Recommendation.** A fleet-wide field in `hosts/fleet.json`:
`"operator": { "name": "<operator>", "uid": 1000 }`, exposed as
`fleet.operator` by `nixosModules/fleet.nix`. `hosts/forge/{default,
lan-access,proton-backup}.nix` read `config.fleet.operator.name` instead of
the literal (fact 8). Core keeps its own declaration (its toplevel is not
touched in phase 1) and gains an **assertion** that
`users.users.${fleet.operator.name}` exists with that uid, so the two can
never diverge silently. The forge declares
`users.users.${name}.hashedPasswordFile = "/var/lib/secrets/operator-password.hash"`.

`fleet-install` prompts twice (no echo), hashes with `mkpasswd -m yescrypt`
(in the ISO), and writes only the hash, `0600 root:root`, to
`/mnt/var/lib/secrets/operator-password.hash` **before** `nixos-install`, so
the activation inside the chroot creates the user with it (facts 9, 10). The
plaintext exists only in the installer's RAM.

**Reason.** Fact 9: with `mutableUsers = true` the hash is applied at
creation, then `passwd` owns it — the file is a one-time seed, and a later
`passwd` on the forge keeps working. Fact 8: `hosts/*` is withheld, so the
name in `fleet.json` never reaches a published file.

**Rejected.** *The name typed at install*: the declaration would not know the
account the machine has — the forge bug in reverse. *`chpasswd -e` through
`nixos-enter` after install*: works, but the account would again have no
declared password source; a reinstall would repeat the prompt with nothing
to check. *`hashedPassword` in the tree*: a hash in git is a secret in a
repository.

### D5 — SSH from first boot: both accounts, the YubiKey keys, PIN enforced

**Recommendation.** The fleet module gives
`users.users.${fleet.operator.name}.openssh.authorizedKeys.keys =
fleet.deployKeys` on a deploy-accepting machine, and sets
`services.openssh.settings.PubkeyAuthOptions = "verify-required"` (fact 11:
today the server does not demand the PIN). The operator's sudo stays
password-gated (`wheelNeedsPassword`, fact 13). Nothing else changes: no
password login, no root login, the address- and subnet-scoped port 22.
With this, reboot (`ssh -t <operator>@forge sudo systemctl reboot`), the
proxy hash rotation and Forgejo's admin creation (plan steps 7 and 9) run
from core.

**What it changes in the threat model** (fleet spec §2 chose deploy-only).
- **The ceiling does not rise.** A deploy key holder is already root (fact
  12). The operator account adds a door behind the *same* keys, PIN and
  touch.
- **New:** a remote shell into the operator's home on the forge (the restic
  password, the Proton Drive session). Same key holder, so no new principal —
  but it no longer needs a crafted system to read them.
- **New:** the sudo password is typed on core, into a terminal whose pty
  other processes of the operator's uid can read. Seat agents on core run as
  the operator today (strict-user-spaces phase-1a spec §2 fact 5). Mitigation: type it only
  from a terminal the operator opened; the phase-1a guest work removes the
  shared uid.
- **Tightened:** `verify-required` makes every login, deploy included, need
  the PIN as well as the touch. No agent can use a key silently (it never
  could — the touch).
- **Unchanged:** core never listens; the forge accepts only the listed keys.

**Rejected.** *Deploy-only with more NOPASSWD rules*: a new rule per
console step on a root-equivalent user, and still no `forgejo admin` as
`forgejo`. *NOPASSWD sudo for the operator*: drops the one factor a stolen
session lacks. *Separate sk keys per account*: more credentials, same
holder (Q3).

### D6 — Secrets placed at install time; one module fix kept

**Recommendation.** `fleet-install` prompts for:
- **the proxy password** → `caddy hash-password` (caddy is in the baked
  closure) → `/mnt/var/lib/lan-access/forge.bcrypt`, `0640 root:239` (the
  static caddy gid, fact 14), directory `0710`;
- **the restic password** → the declared `passwordFile`, written after
  `nixos-install` (the home exists then), `0600`, owned by the operator's uid.

Proton Drive's `auth login` stays a console step on the first GNOME login
(its credential store is the GNOME Keyring, FL4). Separately,
`BUG-fleet-first-deploy-before-proxy-password` keeps its own fix for the
join path — caddy not started while the file is absent — because the
join-script path stays (D9).

**Reason.** Fact 14: caddy fails without the file; the restic job fails
without its password. With both placed, the first boot has no failed unit
(A6).

**Rejected.** *Only the module tolerating absence*: the forge boots with its
proxy down and still needs a root write. *Secrets on the USB*: anyone
holding it reads them, after the install too.

### D7 — The host key: generated at install, enrolled by fingerprint

**Recommendation.** `fleet-install` runs
`ssh-keygen -t ed25519 -N '' -f /mnt/etc/ssh/ssh_host_ed25519_key` and prints
its SHA256 fingerprint and public key at the end. On core a new
`fleet rekey forge` scans the key, takes the typed fingerprint (enroll's
existing refusal on mismatch, exit 3), and rewrites only `hostKey` in
`hosts/fleet.json`; the operator commits. The forge needs no rebuild (fact
4); core's `/etc/ssh/ssh_known_hosts` follows at its next switch, and
`fleet` itself trusts only `fleet.json` (plan D3), so the next deploy works
at once. Until the rekey, core refuses the new forge — the old key is pinned
— which is the intended failure.

**Rejected.** *Pre-generated on core*: a host private key on core and on
removable media, outside the ISO's store (readable by anyone holding the
USB), on a partition that outlives the install. *Re-running `fleet
enroll`*: its hardware step needs the bootstrap's sudo (fact 18).

### D8 — Verification: one VM test, the nixpkgs installer shape, plus an ISO boot

**Recommendation.** `checks.fleet-installer-vm`, after `installer.nix`
(fact 16):
- **installer node** = the same `fleet-install` module the ISO carries,
  minus `iso-image.nix`, root on an empty disk, the *fixture* forge's
  toplevel in `system.extraDependencies`, substituters off; the target a
  blank shared `target.qcow2` with a known serial (`-drive …,serial=`).
- `fleet-install` reads its answers from a file only when built with the
  test-only `answersFile` option; **the shipped ISO's script refuses** the
  option (an eval check on `installer-forge`).
- **target node** boots the disk with `useBootLoader` and `useEFIBoot`.
  Subtests: a wrong typed serial writes nothing (`sfdisk -d` of the disk
  still fails); the right one installs; the declared account logs in on tty1
  with the typed password (the `login.nix` pattern); sshd admits the
  fixture's key for `deploy` and for the operator and refuses an unlisted
  key and any password; `sudo -n true` as the operator fails and
  `sudo -S true` with the password succeeds; `systemctl --failed
  --no-legend` prints nothing; `caddy.service` is active and `curl` returns
  401 without the proxy credential and not 401 with it.
- **A second check, `installer-forge-boots`**, boots an ISO under OVMF as a
  USB drive (the `boot.nix` `uefiUsb` shape) to the `fleet-install` prompt.

**Proxies, declared.** The fixture forge (fixture address, the VM's
interface) stands in for the enrolled one; the ISO in the second check
carries `test-instrumentation.nix`, so it is not byte-identical to the
shipped one; the fixture uses nixpkgs' throw-away ed25519 keys, so the PIN,
touch and `verify-required` are checked once by hand on the real forge
(the fleet spec's precedent).

**Rejected.** *The shipped ISO as the installer node*: the driver needs a
backdoor the shipped ISO must not have. *The real 6.8 GiB closure in the
test*: copied into a qcow2 every run for the same code paths (a plan-time
cost measurement, §9).

### D9 — Scope: the forge in phase 1; join and enroll kept

**Recommendation.** Phase 1 builds `installer-forge` only, and lands D4's
`fleet.operator`, D5's module lines, D7's `fleet rekey`, the two checks.
`fleet join-script` and `fleet enroll` stay for machines that already run
NixOS and that the flake has not seen; the runbook states which path fits
which machine. A new, unseen machine still needs one enroll (the hardware
file) before an image can exist.

## 4. The install, as the operator sees it

1. On core: `nix build .#installer-forge`; the operator writes it to a USB.
2. At the forge: boot it in UEFI mode (the script refuses BIOS; the machine
   declares `efi = true`); `sudo fleet-install`.
3. It prints the machine and toplevel path and the disk list; the operator
   types the target's serial, then `wipe`.
4. Prompts: the operator's password (twice), the proxy password, the restic
   password.
5. It partitions, formats with the pinned IDs, places the hashes, generates
   the host key, runs `nixos-install --system`, writes the restic password,
   and compares `nixos-generate-config --show-hardware-config --root /mnt`
   with the baked file: equal → `hardware: matches`; different → prints the
   diff, keeps the file at `/mnt/etc/nixos/hardware-configuration.generated.nix`
   and asks for `continue`.
6. It prints the host key fingerprint and `remove the USB and reboot`.
7. On core: `fleet rekey forge`, commit; `ssh <operator>@forge` works; plan
   step 9 (Forgejo admin) runs over SSH.

## 5. Acceptance

Each with an accepted arm and a refused arm.

- **A1 — the image evaluates and builds.** Accepted: `nix build
  .#installer-forge` succeeds and `isoImage.storeContents` holds
  `nixosConfigurations.forge`'s toplevel (an eval check compares the two
  paths). Refused: the check fails when the forge's toplevel changes and the
  installer's does not follow (a fixture with a mismatched toplevel).
- **A2 — first boot is the declared system.** Accepted (VM, D8):
  `readlink /run/current-system` on the target equals the fixture toplevel.
  Refused: with the installer's `extraDependencies` stripped of it, the
  install fails and writes no bootloader entry.
- **A3 — the declared account logs in.** Accepted: tty1 login with the typed
  password. Refused: a wrong password is rejected; `grep -rn` over the tree
  and `nix path-info -r` of both toplevels find no `$y$` hash.
- **A4 — the name is declared once.** Accepted: `grep -rn '<operator>'
  hosts/forge nixosModules/fleet.nix` → nothing; core's assertion holds.
  Refused: a fixture `fleet.json` whose `operator.name` differs from core's
  account fails core's evaluation with the assertion's message.
- **A5 — SSH.** Accepted: the fixture key logs in as `deploy` and as the
  operator; `sudo -S` works for the operator. Refused: an unlisted key, a
  password, and `root` are each refused; `sudo -n` fails for the operator.
- **A6 — no failed unit.** Accepted: `systemctl --failed --no-legend` empty,
  caddy active, 401 without the credential. Refused: the same test with the
  proxy prompt answered empty ends the install before `nixos-install` (the
  script refuses an empty secret) — so a failing caddy can never be the
  installed state.
- **A7 — the wipe.** Accepted: the right serial proceeds. Refused: a wrong
  serial, the boot medium's serial, and a non-`wipe` answer each exit
  non-zero with the target disk's first MiB unchanged (`cmp` against its
  pre-state).

## 6. Failure modes and rollback

- **Stopped midway:** re-run from step 2; nothing on core changed.
- **An old image:** the forge boots an older declared system (the path is
  printed before the wipe); `fleet deploy` moves it forward.
- **Hardware drift:** step 5's diff; re-enroll, rebuild the image.
- **A lost password:** console, `init=/bin/sh`, `passwd` (as on 2026-09-25);
  `mutableUsers` keeps it (fact 9).

## 7. Not in this design

- **Generic machines**: an unseen machine needs its hardware file first; a
  later phase may generate it on the ISO and use disko for unpinned layouts.
- **Disk encryption** (LUKS): the enrolled forge has none.
- **`BUG-forge-backup-cannot-read-forgejo`**,
  **`BUG-fleet-drops-remote-error-output`**: independent of the install.
- **`nixosModules/protonBackup.nix`'s default** (fact 8) and **core reading
  `fleet.operator`**: their own tasks.

## 8. Operator questions — answered 2026-09-25

All six match the recommendations, so no decision text changes:
- **Q1 wipe the current forge** — `yes` (nothing is mirrored to it, fact 17).
- **Q2 the operator's account name** — `core`: core's name, declared once in `fleet.json`.
- **Q3 keys for the operator account** — `same`: the two YubiKey deploy keys (default).
- **Q4 record the disk serial in `fleet.json`** — `yes`: the installer pre-selects the disk
  and still demands the typed serial.
- **Q5 stateVersion of the reinstalled forge** — `26.05` (default).
- **Q6 enforce `verify-required` on the server now** — `yes` (D5; deploys too).

## 9. Not measured — and what the web research settled

Settled by `docs/research-2026-09-25-installer-image-web.md` (98 claims supported, 0 refuted):
- disko (MIT) has no filesystem-UUID or FAT volume-ID option and writes its own
  `fileSystems`: D2's scripted `mke2fs -U` / `mkfs.fat -i` stands.
- The ISO squashfs is zstd-19; estimated 2.5–2.7 GiB for the forge: **an 8 GB stick**.
- `nixos-install --system … --no-root-passwd --no-channel-copy --option substituters ''`
  installs with no network contact.
- `verify-required` binds only `sk-` keys; the VM test's plain fixture keys are unaffected.
- A `Persistent` daily timer does not fire at first boot: the first backup runs the first
  night after install, and the runbook says so.

Still not measured:
- The ISO's real size and build time (the plan's first measurement).
- The forge's current ESP size, disk serial and Forgejo/restic state:
  console-side, not reachable from core without the operator.
- Whether `nixos-generate-config` on the ISO reproduces the enrolled file
  byte for byte (step 5 handles both outcomes).
