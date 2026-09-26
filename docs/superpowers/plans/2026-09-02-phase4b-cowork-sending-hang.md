# Phase 4b field fix — Cowork "Sending…" hang (VM never boots)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. One task = one commit. TDD where a test rung exists. Build-only: **never** `nixos-rebuild switch`, never start/stop/restart any unit, never `sudo` (the host is live from this repo).

**Symptom (operator, 2026-09-02 16:xx):** in the Cowork window a message stays at "Sending…" forever; no reply ever arrives.

**Diagnosis (orchestrator, evidence in `docs/research-2026-09-02-cowork-sending-hang.md`):**

1. Cowork on Linux runs the agent inside a QEMU/KVM micro-VM (`cowork-linux-helper`). The VM's root filesystem is **not** shipped in the .deb — the app downloads it on first session start from `https://downloads.claude.ai/vms/linux/x64/<sha>/` (manifest inside `app.asar`: `rootfs.img` 1,286,740,082 bytes compressed, `vmlinuz`, `initrd`) plus the Claude Code harness bundle from `https://downloads.claude.ai/claude-code-releases/…`.
2. The cowork broker allowlist is `api.anthropic.com, claude.ai, statsig.anthropic.com, assets-proxy.anthropic.com, claude.com`. `downloads.claude.ai` is denied: the audit log holds **96 `CONNECT downloads.claude.ai` denies**, in retry bursts exactly when a session was started (16:00:55, 16:03:24, 16:04:00, 16:09:33, 16:12:06 CDT).
3. No rootfs → the helper never launches `qemu-system-x86_64` (acceptance step 2 "no qemu-system process" is the same fact). The desktop app *did* deliver the message to the server-side session (`POST /v1/code/sessions/cse_…/events` → 200) but no worker (the VM) ever picks it up, so the UI never leaves "Sending…". QEMU/OVMF/virtiofsd/KVM/vsock are all present and verified working; they are not the cause.

**Predicted next failures once the download is allowed (each with a code-level citation, each fixed here so the operator needs ONE rebuild):**

4. **Guest trust of the broker CA.** The helper (`main.(*vmManager).installHostCACertificates`, `main.readSystemCACertificates`) reads the host's `/etc/ssl/certs/ca-certificates.crt` and the guest (`coworkd`) installs those into `/usr/local/share/ca-certificates` + `update-ca-certificates --fresh`. The broker CA lives only in `/var/lib/egress-broker/cowork/ca/ca.pem` and claude-app's NSS db, so the guest would not trust the TLS-terminating broker. Claude Code trusts the OS store by default (`CLAUDE_CODE_CERT_STORE=bundled,system`, docs/network-config), so getting the CA into the bundle the helper reads is sufficient.
5. **mitmproxy buffers response bodies by default** (`stream_large_bodies` unset). mitmproxy's own `server_side_events` addon documents that SSE is swallowed without streaming (issue #4469). Claude Code aborts a streaming API response after 180 s with no bytes (first-byte deadline / byte watchdog, docs/network-config). A buffered 1.3 GB rootfs download also shows zero progress for its whole duration. Both need streaming at the broker.
6. **`nologin` spam / broken environment resolution.** systemd sets `SHELL=…/nologin` for the `claude-app` system user; the app runs `$SHELL -l -i -c env` to resolve the session environment (`CLAUDE_DESKTOP_RESOLVING_ENVIRONMENT`), which fails every time (journal: "Attempted login by UNKNOWN (UID: 991)").
7. **In-bubble browser is broken** (`chromium-browser` wrapper): the Electron wrapper exports `LD_LIBRARY_PATH` (claude-desktop's nixpkgs, glibc 2.42 world); host `chromium` (glibc 2.40) inherits it via `xdg-open` and dies with `GLIBC_ABI_DT_X86_64_PLT not found`. Reproduced and fixed by unsetting `LD_LIBRARY_PATH` (verified 2026-09-02 with `chromium --version`). Sign-in worked only because the operator used the email code inside the app.

**Not changed (documented as expected denies):** `browser-intake-us5-datadoghq.com`, `o1158394.ingest.us.sentry.io` (telemetry), `redirector.gvt1.com` (Chrome component updater), `bridge.claudeusercontent.com` (Claude-in-Chrome bridge, retries every 30 s), `js.hcaptcha.com`/`accounts.google.com`/`widget.intercom.io` (login page extras), `a.claude.ai`/`a-cdn.anthropic.com`/`s-cdn.anthropic.com`/`assets.claude.ai` (CDN/analytics). Likely next legit denies: `platform.claude.com` (OAuth refresh per docs), `*.frame.claudeusercontent.com` (artifacts). Grow only from denies, per runbook.

## Global constraints

- All Phase 1–4b constraints. Commits: `phase4b: <summary> (test: <check>)` + trailers
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_0198W9P9iK9fSLcC6x45aZeX`.
- Commit from the devShell (`nix develop -c git commit …`, hook needs the lint tools). `git add` new files BEFORE `nix build` (flake sees only tracked files). statix rejects `{ ... }:` module headers — use `_:`. Never `2>/dev/null` a gated command.
- The broker stays the enforcement layer; the allowlist grows by exactly one documented domain (`downloads.claude.ai`) in BOTH lists (broker instance allow + managed-settings allowedDomains), mirroring commit 62ccfc4.
- Never ship a certificate-error bypass flag. Trust changes are scoped to `cowork.service`'s mount namespace, never host-wide.

---

### Task 0: baseline

- [ ] Run `nix build .#checks.x86_64-linux.managed-settings -L` and `nix build .#checks.x86_64-linux.cowork-eval -L`. Record whether they are green on HEAD (`d5ac9ae`). Suspected drift: `checks.managed-settings` asserts `allowedDomains == [api, claude.ai, statsig]` while the module default has grown to five domains (62ccfc4, ed2ec8b). If red, Task 1 fixes it.

### Task 1: allowlist `downloads.claude.ai` (root cause)

**Files:** `nixosModules/cowork.nix` (instance `allow`), `nixosModules/claudeManagedSettings.nix` (`allowedDomains` default), `flake.nix` (checks).

- [ ] Red: extend `checks.cowork-eval` to assert `coworkEvalSystem.config.services.egress-broker.instances.cowork.allow` contains `downloads.claude.ai` (eval-time; e.g. `lib.assertMsg`/`throw` or grep the rendered policy JSON `config.systemd.services.egress-broker-cowork.environment.BROKER_POLICY`).
- [ ] Green: add the domain to both lists with a one-line comment: `# Cowork VM image + Claude Code harness bundle (audit-log denies 2026-09-02)`.
- [ ] Fix `checks.managed-settings` so its expected `allowedDomains` equals the module's current default (compare against `managedSettingsSystem.config.services.claude-managed-settings.allowedDomains` rendered via `builtins.toJSON`, not a stale literal).
- [ ] lint → commit.

### Task 2: broker CA reaches the Cowork guest (scoped overlay)

**Files:** `nixosModules/egressBroker.nix`, `nixosModules/cowork.nix`, `tests/integration/broker-vm.nix`, `flake.nix`.

- [ ] Broker `ExecStartPost` export script additionally writes `/var/lib/egress-broker/<name>/ca/ca-bundle.crt` = `/etc/ssl/certs/ca-certificates.crt` + `ca.pem` (tmp + `mv`, mode 0644). Comment cites why (helper reads that path; guest installs it).
- [ ] `cowork.service`: `BindReadOnlyPaths = [ "/var/lib/egress-broker/${cfg.brokerInstance}/ca/ca-bundle.crt:/etc/ssl/certs/ca-certificates.crt" ]`. Comment: scoped to this unit's mount namespace; host trust store untouched; NEVER an ignore-certificate flag.
- [ ] Red→Green tests: (a) `checks.cowork-eval` greps the `BindReadOnlyPaths=` line; (b) `tests/integration/broker-vm.nix`: assert `ca-bundle.crt` exists, contains the mitmproxy CA subject AND ≥ 100 `BEGIN CERTIFICATE` blocks; add a tiny throwaway `systemd.services.overlay-probe` in the VM test with `ProtectSystem=strict` + the SAME `BindReadOnlyPaths` shape (source = the broker's `ca-bundle.crt`, destination `/etc/ssl/certs/ca-certificates.crt`) whose script `grep -q mitmproxy /etc/ssl/certs/ca-certificates.crt` — this proves the bind lands on NixOS's symlinked destination (the known-unknown of this task).
- [ ] lint → commit.

### Task 3: broker streams SSE and large bodies

**Files:** `pkgs/broker/policy.py`, `tests/broker/test_policy.py`, `nixosModules/egressBroker.nix`, `tests/integration/broker-vm.nix`.

- [ ] Red (pytest): `responseheaders` sets `flow.response.stream = True` when content-type starts with `text/event-stream`; audit `bytes_in` falls back to the `content-length` header when `raw_content` is `None` (streamed); `requestheaders` performs the same allow/SNI check as `request` (deny before any body is streamed upstream) and existing tests still pass (no double audit).
- [ ] Green: implement; keep `DENY_BODY`/403 semantics; ruff clean.
- [ ] `egressBroker.nix`: add `--set stream_large_bodies=1m` with a comment (VM image 1.3 GB; mitmproxy buffers by default). Integration test: nginx serves a 3 MiB file on `allowed.test/big` (e.g. `pkgs.runCommand` generating it); curl via broker receives exactly 3 MiB; audit entry for `/big` has `bytes_in == 3145728` (content-length fallback).
- [ ] lint → commit.

### Task 4: session shell + in-bubble browser

**Files:** `nixosModules/cowork.nix`, `flake.nix`.

- [ ] `systemd.services.cowork.environment.SHELL = "/bin/sh"` (comment: the app resolves its session env with `$SHELL -l -i -c env`; systemd otherwise exports the system user's `nologin`). Red→Green: `cowork-eval` greps `Environment=.*SHELL=/bin/sh`.
- [ ] `bubbleBrowser`: `exec ${pkgs.coreutils}/bin/env -u LD_LIBRARY_PATH ${pkgs.chromium}/bin/chromium …` (comment: glibc-world mismatch, reproduced 2026-09-02). Red→Green: `cowork-eval` locates the `chromium-browser` wrapper via the unit's `PATH` (`coworkEvalSystem.config.systemd.services.cowork.path`) and greps `env -u LD_LIBRARY_PATH`.
- [ ] lint → commit.

### Task 5: acceptance, runbook, board, concept

**Files:** `tests/acceptance/phase4b.sh`, `docs/runbooks/phase4b-acceptance.md`, `docs/OPERATIONS.md`, `README.md`, `docs/concepts/2026-09-02i-vm-image-provenance.md`, `docs/research-2026-09-02-cowork-sending-hang.md` (orchestrator-written; commit as-is).

- [ ] `phase4b.sh`: the VM boots only when the first session starts — reorder so the operator connects the workspace and sends the first message BEFORE the qemu/netns checks; poll up to 15 min for `pgrep -u claude-app qemu-system`, printing download progress from the audit log (`allow` entries to `downloads.claude.ai`) every 30 s; keep every other check. shellcheck-clean.
- [ ] Runbook: first-boot download (~1.3 GB through the broker, watch with `tail -f /var/lib/egress-broker/cowork/audit.jsonl` — it is world-readable), expected-deny table (above), the `platform.claude.com` / `*.frame.claudeusercontent.com` likely-next note, VM logs at `/var/lib/claude-app/.config/Claude/logs/` (sudo).
- [ ] OPERATIONS.md: Lane A field-bug ledger entries 12–16 (this plan's items), gate still pending; README status line.
- [ ] Concept (one per turn): **VM image provenance pin** — pin the Cowork VM bundle sha from the app manifest at the claude-desktop pin, prefetch `rootfs.img`/`vmlinuz`/`initrd` with checksum verification into a local mirror served from an allowlisted local origin, so first boot has no runtime dependency on `downloads.claude.ai`, images are content-addressed (feeds proving-grounds seeds), and the desktop pin bump re-greps the manifest as a runbook step.
- [ ] lint → commit.

## Verification (whole change)

1. `nix flake check -L` all green (incl. `integration` VM test with the new cases).
2. `nix build .#nixosConfigurations.core.config.system.build.toplevel` succeeds; `nix store diff-closures /run/current-system ./result` summarized (expect: egress policy JSON, broker unit, cowork unit, chromium-browser wrapper, managed-settings JSON, acceptance script).
3. NOT done by the factory: the switch and the live retry. Operator gate afterwards:
   `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core` → in the Cowork window send the message again → watch `tail -f /var/lib/egress-broker/cowork/audit.jsonl` for `downloads.claude.ai` allows and `pgrep -u claude-app qemu-system` → then `nix develop -c tests/acceptance/phase4b.sh`.
