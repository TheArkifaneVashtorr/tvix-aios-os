# Phase 4b — Cowork Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude Cowork runs on `core` as tier A: dedicated UID in its own netns behind its own broker instance, one rw basket as its only workspace, managed settings generated from Nix and locally unoverridable, its VM's traffic visible in the broker audit log.

**Architecture:** Verified foundations (docs/research-2026-09-02-phase4.md): Cowork's VM networking is QEMU slirp inside the app's process tree, so a netns around the app confines the VM; the app is packaged by `nmcbride/claude-desktop-nix` (pin `2479d51149838ddf049fdcd8cefe360ce904ed00`, v1.40609.1) whose NixOS module satisfies the helper's hardcoded Debian paths; display crosses the user boundary via waypipe (system unit runs the app as `claude-app` inside the broker netns; the operator session runs the waypipe client); Cowork reads proxy config ONLY from managed settings (v2.1.217+), so the broker address lives in `/etc/claude-code/managed-settings.json`, with `--proxy-server` in the Electron wrapper for the shell. Basket decryption needs the YubiKey, so Cowork lifecycle is operator-invoked (`cowork-up` / `cowork-down`), never boot-time.

**Tech Stack:** claude-desktop-nix (pinned input), waypipe (nixpkgs), existing egressBroker + basketStore modules, managed-settings schema from docs/research (managed-settings section).

**Spec:** design doc §2.1 tier A + §2.3; brief §5.1 + §7 Phase 4; research digests 2026-09-02 (phase4 + derisk managed-settings section).

## Global Constraints

- All Phase 1–4a Global Constraints apply. Commits: `phase4b: <summary>` + trailers.
- New flake inputs pinned EXACTLY: `claude-desktop.url = "github:nmcbride/claude-desktop-nix/2479d51149838ddf049fdcd8cefe360ce904ed00"`. waypipe from the existing host nixpkgs pin.
- The broker remains the enforcement layer; every proxy/env setting is cooperation. Never weaken the netns/nftables layer to make the app work — widen the allowlist instead, one audited domain at a time.
- Managed settings JSON must follow the verified schema (docs/research-2026-09-02-derisk.md → managed-settings): the three lock keys (`allowManagedDomainsOnly`, `sandbox.filesystem.allowManagedReadPathsOnly`, `allowManagedPermissionRulesOnly`) are mandatory; `disableBypassPermissionsMode: "disable"` (string); no secrets in the file.
- Nothing GUI runs at build/test time except in the operator acceptance; automated rungs assert on units, files, netns wiring, and rendered JSON.

---

### Task 1: claudeManagedSettings.nix — the generated lockdown file

**Files:**
- Create: `nixosModules/claudeManagedSettings.nix`
- Modify: `flake.nix` (export module; `checks.managed-settings` asserting rendered JSON)

**Interfaces:**
- Produces: `services.claude-managed-settings = { enable; brokerInstance (str — names an egress-broker instance; derives proxy URL and CA path); allowedDomains (listOf str); extraSettings (attrs, deep-merged last); }`. Renders `/etc/claude-code/managed-settings.json` via `environment.etc`. Content skeleton (jq-assertable in the check):

```json
{
  "permissions": { "disableBypassPermissionsMode": "disable", "defaultMode": "default" },
  "allowManagedPermissionRulesOnly": true,
  "allowManagedHooksOnly": true,
  "allowManagedMcpServersOnly": true,
  "allowedMcpServers": [],
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "network": {
      "allowedDomains": ["api.anthropic.com", "claude.ai", "statsig.anthropic.com"],
      "allowManagedDomainsOnly": true,
      "strictAllowlist": true
    },
    "filesystem": { "allowManagedReadPathsOnly": true }
  },
  "env": {
    "HTTPS_PROXY": "http://<broker hostAddress>:<port>",
    "HTTP_PROXY": "http://<broker hostAddress>:<port>",
    "NODE_EXTRA_CA_CERTS": "/var/lib/egress-broker/<instance>/ca/mitmproxy-ca-cert.pem"
  }
}
```

- [ ] Steps: write `checks.managed-settings` first (build a nixosSystem with the module + a broker instance; runCommand jq-asserts the etc file content: lock keys true, proxy URL matches the instance's hostAddress:port, disableBypassPermissionsMode == "disable") → red → implement module (options + `environment.etc."claude-code/managed-settings.json".source = (pkgs.formats.json {}).generate ...`, reading the broker instance's `hostAddress`/`listenPort` from `config.services.egress-broker.instances.<brokerInstance>`; assertion: named instance exists) → green → lint → commit.

---

### Task 2: cowork.nix — user, netns service, waypipe, basket wiring

**Files:**
- Create: `nixosModules/cowork.nix`
- Modify: `flake.nix` (input `claude-desktop` pinned; export module; `checks.cowork-eval`)

**Interfaces:**
- Produces: `services.cowork = { enable; basket (str, default "cowork-workspace"); brokerInstance (default "cowork"); shareGroup (default "claude-gui"); operatorUser (default "dalhaka"); }`. The module:
  1. Imports `claude-desktop.nixosModules.default`; sets `programs.claude-desktop.enable = true; programs.claude-desktop.cowork.kvmUsers = [ "claude-app" ];` and overrides the package with `commandLineArgs = [ "--proxy-server=http://<broker>:<port>" "--ozone-platform=wayland" ]`.
  2. User `claude-app` (isNormalUser = false is wrong for a GUI home — use isSystemUser with explicit home `/var/lib/claude-app`, createHome, group claude-app, extraGroups [ "kvm" shareGroup ]).
  3. `systemd.services.cowork` — NOT wantedBy anything (operator-started): `User=claude-app`, `SupplementaryGroups=kvm <shareGroup>`, `NetworkNamespacePath=/var/run/netns/egress-<brokerInstance>`, `Requires/After=egress-broker-<brokerInstance>.service`, environment `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR=/run/claude-app` (RuntimeDirectory), ExecStartPre asserts the basket is mounted at `/run/baskets/<basket>` (fail loudly if not — mounting is the operator's `cowork-up`, YubiKey in hand), ExecStart `waypipe --socket /run/claude-gui/wp.sock server -- claude-desktop`; hardening: NoNewPrivileges, ProtectSystem=strict with ReadWritePaths for `/var/lib/claude-app` and `/run/baskets/<basket>`, DeviceAllow `/dev/kvm rw` + `/dev/vhost-vsock rw`.
  4. `systemd.user.services.cowork-display` (for operatorUser): `waypipe --socket /run/claude-gui/wp.sock client`, partOf graphical-session.target; socket dir via tmpfiles `d /run/claude-gui 0770 root <shareGroup>`.
  5. Trust: `security.pki.certificateFiles` gains the broker CA? NO — CA file is runtime-generated, not a store path; instead the managed-settings env NODE_EXTRA_CA_CERTS covers the harness, and Electron shell gets `--ignore-certificate-errors`? NEVER. Electron trusts NSS db — add ExecStartPre that imports the broker CA into `claude-app`'s NSS db (`certutil -A -d sql:$HOME/.pki/nssdb`) — pkgs.nss tools. Record as the one imperative-at-runtime step (idempotent, per-start).
  6. Basket declarations for the workspace: `services.baskets.definitions.<basket> = { classification = "permitted"; mount = "/data/cowork"; access = "rw"; }` and `services.baskets.agents.cowork = { baskets = [ <basket> ]; egress = "broker:<brokerInstance>"; placement = "host"; }` — Phase 3 assertions engage automatically.
  7. Default broker instance `cowork` (hostAddress 10.100.1.1, namespaceAddress 10.100.1.2, listenPort 3129, allow = the managed-settings allowedDomains).
- [ ] Steps: `checks.cowork-eval` (nixosSystem with module builds; jq/grep assertions on rendered unit files: NetworkNamespacePath present, User=claude-app, waypipe in ExecStart) → red → implement → green → lint → commit.

---

### Task 3: operator lifecycle + wiring into hosts/core

**Files:**
- Create: `tools/cowork-up.sh`, `tools/cowork-down.sh`
- Modify: `hosts/core/default.nix` (enable services.cowork + claude-managed-settings)

**Interfaces:**
- `cowork-up`: checks `basket doctor`; mounts the cowork-workspace basket (sudo + YubiKey touch); `systemctl start cowork`; tails broker audit log for first entries. `cowork-down`: `systemctl stop cowork`; `basket teardown`; confirms no plaintext remains; prints audit summary (`jq` verdict counts).
- [ ] Steps: scripts (shellcheck-clean, set -e discipline, timeouts) → enable modules in hosts/core with the default instance → `nix flake check` (host-core now includes Cowork stack) → commit.

---

### Task 4: acceptance script + runbook (brief §7 Phase 4, operator-run)

**Files:**
- Create: `tests/acceptance/phase4b.sh`, `docs/runbooks/phase4b-acceptance.md`
- Modify: README, docs/OPERATIONS.md

**Interfaces — the acceptance must prove, in order:**
1. `cowork-up` succeeds: basket mounted, service active, waypipe socket present, Cowork window appears on the operator desktop (operator confirms visually).
2. VM boots: `~claude-app/.config/Claude/logs/` shows Cowork VM startup; `pgrep -u claude-app qemu-system` non-empty.
3. Confinement: `nsenter`/`ip netns identify` of the app PID == egress netns; from inside the netns, direct egress fails (reuse Phase 2 pattern).
4. Basket and nothing outside: operator connects `/data/cowork` (the basket bind target) in the Cowork UI, has the agent write a file; file appears under `/run/baskets/cowork-workspace/`; a write attempt outside the workspace fails (managed read-path locks + FS perms).
5. Traffic audited: broker audit log for instance `cowork` shows allow entries to api.anthropic.com during a short session; deny entries for anything unlisted (the iterative-allowlist procedure in the runbook: read denies → add domain → rebuild → retry).
6. Managed settings unoverridable: drop a `.claude/settings.json` inside the workspace attempting `allowedDomains` widening + `dangerouslySkipPermissions`; verify the session still denies (strictAllowlist + lock keys) — this is the brief's explicit test.
7. `cowork-down` leaves no plaintext, no mounts, `basket doctor` green.
- [ ] Steps: script (each check PASS/FAIL, operator-interactive where visual) → runbook (plain language) → README/board → full `nix flake check` + Phase 1–3 regressions → commit `phase4b: operator acceptance (test: brief §7 Phase 4)`.

---

## Verification (whole phase)

1. `nix flake check` green (managed-settings, cowork-eval, host-core incl. Cowork stack, all prior checks).
2. Phase 1–3 regressions green.
3. Factory runs acceptance steps that need no GUI/YubiKey (unit assertions, netns identity of a dry-run process, managed-settings render).
4. Operator: switch to the updated system, run `tests/acceptance/phase4b.sh` with YubiKey — the Phase 4 gate.

## Known-unknowns the factory must verify at implementation (report as deviations)

- Exact `programs.claude-desktop` option names at pin 2479d511 (enumerated in research; re-read the module source).
- Whether `commandLineArgs` is a module option or a package override at that pin.
- waypipe flag set on the nixpkgs version (`--socket` syntax, `--no-gpu` availability).
- Whether Electron respects NSS db under `claude-app` for the broker CA, or needs `NODE_EXTRA_CA_CERTS` equivalent for the shell; NEVER ship certificate-error bypass flags.
- statsig/sentry telemetry domains Cowork needs: start with the minimal allowlist; grow ONLY from audit-log denies, each addition committed.
