# Phase 4 de-risk research digest — 2026-09-02

Three research agents (one extracted and string-analyzed the official .deb).
Raw output: session workflow wf_2ccafe7c-cd8. Decisions locked for the plan:

## The verdict that matters: netns confinement of Cowork is SOUND

Confirmed from the helper binary itself: the Cowork VM uses QEMU user-mode
(slirp) networking — the VM's sockets are opened by qemu, a child of the app
process; there is no root helper, no setuid, no external networking daemon.
**Confining the app's process tree to a netns confines every byte the VM
sends.** Control plane is vsock (needs /dev/vhost-vsock, kvm group — we have
both). Proxy settings are forwarded into the guest cooperatively
(hostProxyConfig RPC + guest CA install) — treat proxy as cooperation, netns +
broker as enforcement, exactly the two-layer stance.

## Display: waypipe pattern chosen

Dedicated UID needs a way onto the operator's GNOME-Wayland screen:

- **Chosen:** systemd SYSTEM unit (`User = claude-app`, `SupplementaryGroups =
  kvm`, `NetworkNamespacePath=` into the broker's netns) running
  `waypipe --socket <shared> server -- claude-desktop`; the operator session
  runs the waypipe client as a user unit. waypipe ≥0.10 in nixpkgs; force shm
  rendering if the young Vulkan/dmabuf path glitches (`--no-gpu`).
- User units CANNOT do netns (systemd #29429 open) — system unit is mandatory.
- Portals do not cross users: file dialogs must be plain GTK (no
  GTK_USE_PORTAL); test dialogs explicitly in acceptance.
- Runner-up (fallback): setfacl-share the compositor socket — simpler but hands
  the app UID full mutter access incl. clipboard; only if waypipe misbehaves.
- /dev/kvm is orthogonal to netns; works in the system unit (DeviceAllow).

## Packaging: pin and paths

- Pin `github:nmcbride/claude-desktop-nix` at **2479d511** (Claude Desktop
  1.40609.1, bumped daily upstream — our pin moves only deliberately).
- Its `nixosModules.default`: `programs.claude-desktop.enable`,
  `.cowork.enable`, `.cowork.kvmUsers`; tmpfiles-symlinks the Debian-hardcoded
  paths the helper probes (/usr/libexec/virtiofsd, /usr/share/OVMF/*).
- The .deb's AppArmor profile is unconfined (anthropics/claude-code#84386) —
  our netns/unit hardening is the actual confinement.

## Proxy plumbing correction (design delta, applied)

Since Claude Code v2.1.217, Cowork/Code sessions read proxy config **only from
managed settings and ~/.claude/settings.json — shell env is ignored** for the
harness. So the broker address goes into `/etc/claude-code/managed-settings.json`
(env block / proxy keys), and the Electron shell gets `--proxy-server` via the
package's `commandLineArgs`. Env vars alone would silently not apply.
Managed settings ARE read by Cowork on the user's machine (confirmed in docs);
server-managed settings are never fetched in Cowork.

## Filesystem exposure notes (for the plan + runbook)

Single virtiofs share tag `claudeshared`; bundled virtiofsd runs
`--sandbox none` (no chroot) — a guest FS escape reaches the app UID's whole
home. Mitigations: the dedicated `claude-app` home contains ONLY the basket
mount and `~/.config/Claude` (VM state, incl. persistent `sessiondata.img` —
belongs in/next to the basket); nothing else lives there. Verify the actual
shared-dir path at first launch (`ps aux | grep shared-dir`). On every version
bump, re-grep the helper for `user,id=net0` and `tag=claudeshared` before
trusting the pin (added as a runbook step).
