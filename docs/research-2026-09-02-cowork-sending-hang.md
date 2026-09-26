# Research digest 2026-09-02 — Cowork "Sending…" hang on core

Orchestrator investigation (systematic-debugging, Phase 1 evidence only; no
fixes were applied to the live host). Companion plan:
`docs/superpowers/plans/2026-09-02-phase4b-cowork-sending-hang.md`.

## Symptom

Operator, after Phase 4b bring-up: the Cowork window renders, sign-in works
(email code), a workspace folder is connected, but any message stays at
"Sending…" and never gets a reply. The app also pops the help link
`code.claude.com/docs/en/remote-control#resume-sessions-after-stopping-the-server`
(xdg-open, journal 16:12:15, 16:12:23, 16:12:35, 16:15:01).

## What the host says (all readable without sudo)

| Source | Fact |
| --- | --- |
| `systemctl status cowork` | active since 16:03:22; Electron main, renderers, `cowork-linux-helper -socket /run/claude-app/claude-cowork-vm.sock` running; **no `qemu-system-*` process** |
| `journalctl -u egress-broker-cowork` | broker healthy; 776 requests to claude.ai, 608 to assets-proxy, 25 to api.anthropic.com, all 200; websocket to `/v1/sessions/ws/session_01SZ…/subscribe` up (ping/pong) |
| `/var/lib/egress-broker/cowork/audit.jsonl` (0644) | 1615 allow / **475 deny** / 12 error. Deny hosts: datadog 189, **downloads.claude.ai 96**, bridge.claudeusercontent.com 78, assets-proxy 51 (before it was allowlisted), sentry 23, gvt1 11, a.claude.ai 8, s-cdn/a-cdn 7 each, hcaptcha 6, accounts.google.com 5, intercom 3, assets.claude.ai 2 |
| audit timeline | `POST /v1/code/sessions/cse_01SZ…/events` 200 at 16:04:24, 16:07:58, 16:08:08, 16:09:38, 16:10:37 (the messages DID reach the server-side session). `CONNECT downloads.claude.ai` deny bursts with backoff at 16:00:55–16:01:07, 16:03:24–36, 16:04:00–31, 16:09:33–45, 16:12:06–07 — i.e. every time a session (re)started |
| `journalctl -u cowork` | `nologin[…]: Attempted login by UNKNOWN (UID: 991)` at every app start and session start (16:03:23, 16:04:03, 16:05:15, 16:09:33, 16:12:06); `chromium: …libc.so.6: version GLIBC_ABI_DT_X86_64_PLT not found (required by glibc-2.42-67/lib/libmvec.so.1)` on every xdg-open |
| `/usr/share/OVMF/*`, `/usr/libexec/virtiofsd`, `/dev/kvm`, `/dev/vhost-vsock`, `lsmod` | all present; `qemu-system-x86_64 --version` (claude-desktop closure, qemu 11.0.1) and both virtiofsd binaries run fine under the Electron wrapper's `LD_LIBRARY_PATH` |

## What the app says (read from the Nix store, `app.asar` + helper + `smol-bin.x64.img`)

- VM bundle manifest in `app.asar`: `versions:[{sha:'2a762adf…', files:{unix:{x64:[{name:'rootfs.img', size:1286740082, rawSize:10737418240, …}, vmlinuz, initrd…]}}}]`; download base `https://downloads.claude.ai/vms/linux/${arch}/${sha}` (`J_n()`); status check `[Bundle:status] rootfs.img missing`. Harness bundle base `https://downloads.claude.ai/claude-code-releases/rc/<sha>` (~75 MB zst). Bundled in the .deb: only `smol-bin.x64.img` (27 MB) — the helper logs `startVM: rootfs not found` without the download.
- Helper (`cowork-linux-helper`, Go): `qemuBinaryName` = `qemu-system-x86_64` looked up on PATH (the package wrapper prefixes qemu — fine); firmware `/usr/share/OVMF/OVMF_CODE_4M.fd`; `readSystemCACertificates` reads `/etc/ssl/certs/ca-certificates.crt`; `installHostCACertificates` sends them to the guest; guest `coworkd` writes `/usr/local/share/ca-certificates` + `update-ca-certificates --fresh`. RPC `hostProxyConfig{httpProxy,httpsProxy,noProxy,pacScript,hostLoopbackIP}` exists on both ends but the desktop app (this build) never sends it; the harness gets proxy/CA env from managed settings + `~/.claude/settings.json` (docs/network-config, v2.1.217+ rule) — which is exactly claude-app's provisioned `~/.claude/settings.json`.
- Env resolver: `E()` picks `process.env.SHELL` if it exists → systemd's `SHELL=…/nologin` → `nologin -l -i -c env` → fails.
- `CLAUDE_CODE_MANAGED_SETTINGS_PATH` is honored by this build (directory containing `managed-settings.json`) — an additive way to give Cowork a managed tier without a machine-wide `/etc/claude-code` file. Not used yet; candidate for the lockdown mini-phase.
- Desktop app's own managed config lives at `/etc/claude-desktop/managed-settings.json` (`disableNonessentialTelemetry`, auto-update toggles…) — candidate for silencing datadog/sentry/gvt1 at the source.

## Upstream docs (fetched 2026-09-02)

- `code.claude.com/docs/en/desktop-linux`: Cowork on Linux = QEMU + KVM + OVMF + virtiofsd, `kvm` group, `vhost_vsock`. Matches our setup.
- `code.claude.com/docs/en/network-config`: `downloads.claude.ai` is a required host (installer/updater/plugin downloads); in Cowork sessions proxy + CA env are read only from managed settings and `~/.claude/settings.json`; Claude Code trusts the OS trust store by default (`CLAUDE_CODE_CERT_STORE=bundled,system`); streaming watchdogs abort a silent stream after 180 s; `bridge.claudeusercontent.com` = Claude-in-Chrome bridge; `*.frame.claudeusercontent.com` = artifacts; datadog hosts = optional telemetry (`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`).

## mitmproxy facts (12.1.1 in the closure)

- `stream_large_bodies` default `None` → every body is buffered before forwarding.
- `addons/server_side_events.py` exists only to WARN that SSE is swallowed without streaming (issue #4469).

## Reproductions

- Browser: `env LD_LIBRARY_PATH=<wrapper value> chromium --version` → GLIBC error; `env -u LD_LIBRARY_PATH chromium --version` → `Chromium 143.0.7499.169`.
- Deny/host pattern: `jq 'select(.verdict=="deny" and .host=="downloads.claude.ai")' audit.jsonl` → 96 entries clustered at session starts.

## Conclusion

Root cause: the Cowork VM image is fetched at first session start from
`downloads.claude.ai`, which the broker denies, so the VM never boots and the
session has no worker to pick up the message. Fix = allowlist that one host
(both lists). Predicted follow-on blockers (guest CA trust, SSE/large-body
buffering at the broker) and two hygiene bugs (nologin shell, browser glibc)
are fixed in the same rebuild so the operator retries once. Nothing here
weakens the netns/nftables layer.
