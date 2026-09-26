# Release upgrade — nixpkgs-host → NixOS 26.05 head (2026-09-05)

## Summary

PB1 moves the host `core` from `nixpkgs-host` at `ac62194c3917d5f474c1a844b6fd6da2db95077d`
(NixOS 25.05 head, 2026-01-02) to the current `refs/heads/nixos-26.05` head,
`a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` (NixOS `26.05.20260903.a5cc6f2`).
This is the same rev PB0 relocked `~/flakes/gaming` to (PB0 gated green; this
task is its host counterpart, per PB0's "For the orchestrator" handoff).

The rev was read read-only from `~/flakes/gaming/flake.lock` (its `nixpkgs`
node), set as `nixpkgs-host.url`, and the `nixpkgs-host` and `gaming` inputs
were re-locked together. `nix flake check -L` is **green on the first build at
26.05** — all 38 checks pass, including the five NixOS VM tests. The release
forced exactly **one** module change: two `services.xserver.*` options were
renamed out from under `services.xserver` at 26.05 (`desktopManager.gnome`,
`displayManager.gdm`); the two-line move in `hosts/core/default.nix` is the
only module edit. A third piece of drift (the `nixfmt-rfc-style` package
alias) was recorded but deliberately not fixed, consistent with PB0's ruling
that a cosmetic deprecation alias is out of scope for a "fix only on failure"
upgrade.

## The rev

- Old `nixpkgs-host` rev: `ac62194c3917d5f474c1a844b6fd6da2db95077d` (NixOS
  `25.05.20260102.ac62194`, the running `/run/current-system`).
- New `nixpkgs-host` rev: `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` (NixOS
  `26.05.20260903.a5cc6f2`).
- `gaming` input re-locked to PB0's merged `main`:
  `a4088d7e0146839ea267f5c9ea660d0ea03d9eb8`.
- Lock-node confirmation: `nixpkgs-host` node `rev` =
  `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4`; gaming's transitively-locked
  `nixpkgs` (node `nixpkgs_2`) `rev` = the same `a5cc6f2c…`. The two are equal,
  satisfying `checks.core-gaming-wiring`'s lock-node equality assertion.

`nix flake lock` transition (verbatim):

```
• Updated input 'gaming':
    'git+file:///home/dalhaka/flakes/gaming?ref=main&rev=cb51a610a2ddf2116d77b55656b24df605fd0f92' (2026-09-03)
  → 'git+file:///home/dalhaka/flakes/gaming?ref=main&rev=a4088d7e0146839ea267f5c9ea660d0ea03d9eb8' (2026-09-05)
• Updated input 'gaming/nixpkgs':
    'github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d?narHash=sha256-16KkgfdYqjaeRGBaYsNrhPRRENs0qzkQVUooNHtoy2w%3D' (2026-01-02)
  → 'github:NixOS/nixpkgs/a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4?narHash=sha256-r2f1oUwixlgq9zOdYLqJLfS/lWBT60/IITjhTKI59JU%3D' (2026-09-03)
• Updated input 'nixpkgs-host':
    'github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d?narHash=sha256-16KkgfdYqjaeRGBaYsNrhPRRENs0qzkQVUooNHtoy2w%3D' (2026-01-02)
  → 'github:NixOS/nixpkgs/a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4?narHash=sha256-r2f1oUwixlgq9zOdYLqJLfS/lWBT60/IITjhTKI59JU%3D' (2026-09-03)
```

## Checks — every verdict

`nix flake check -L`: **exit 0**, "running 38 flake checks". All 38 pass at
26.05. The five NixOS VM tests below actually boot a NixOS test machine and
run their `testScript` (minutes of wall time), not just evaluate.

| check | verdict |
|---|---|
| `host-core` (builds the host toplevel) | PASS |
| `core-gaming-wiring` | PASS |
| `lint` | PASS |
| `core-backup-wiring` | PASS |
| `proton-drive-cli` | PASS |
| `proton-backup-eval` | PASS |
| `proton-backup-vm` (VM) | PASS |
| `assertion-positive` / `assertion-negative` | PASS |
| `manifests-validate` | PASS |
| `addon` | PASS |
| `factory-unit` | PASS |
| `helm-unit` / `helm-eval` / `helm-assertion-negative` | PASS |
| `helm-vm` (VM) | PASS |
| `helm-control-eval` | PASS |
| `helm-control-assertion-negative-profiles` | PASS |
| `helm-control-assertion-negative-enable` | PASS |
| `helm-control-assertion-negative-agentunit` | PASS |
| `helm-control-assertion-negative-workspace` | PASS |
| `helm-control-vm` (VM) | PASS |
| `evidence-unit` / `evidence-eval` | PASS |
| `claims-validate` | PASS |
| `ledger-unit` | PASS |
| `lane-eval` / `lane-assertion-negative` | PASS |
| `lane-unit` / `lane-polkit-unit` | PASS |
| `lane-vm` (VM) | PASS |
| `integration` (broker VM) | PASS |
| `managed-settings` / `managed-settings-user-scope` | PASS |
| `managed-settings-assertion-negative` | PASS |
| `cowork-eval` | PASS |
| `module-eval` | PASS |
| `unit` | PASS |

Acceptance subset rebuilt individually (`nix build .#checks.x86_64-linux.<name>
-L --no-link`): `host-core` **PASS**, `core-gaming-wiring` **PASS**, `lint`
**PASS**.

## Upstream drift, and the module change it forced

The full `evaluation warning` set emitted at 26.05, annotated:

1. **Renamed option (fixed).** `services.xserver.desktopManager.gnome.enable`
   → `services.desktopManager.gnome.enable`.
2. **Renamed option (fixed).** `services.xserver.displayManager.gdm.enable` →
   `services.displayManager.gdm.enable`.

   Both are in `hosts/core/default.nix`. At 26.05 the GNOME desktop manager and
   GDM display manager moved out from under `services.xserver` to top-level
   `services.*`. nixpkgs still ships `mkRenamedOptionModule` aliases, so the
   old paths evaluate (the check was green before the edit), but they are
   deprecated and scheduled for removal. The minimal fix is a two-line move:
   `displayManager.gdm.enable` and `desktopManager.gnome.enable` promoted out of
   the `xserver = { … }` block to their new homes. This is the only module
   change the release forced (file `hosts/core/default.nix`); verified: both
   new paths resolve as `boolean`, and the warnings disappear on re-check.

3. **Deprecated package alias (recorded, not fixed).**
   `nixfmt-rfc-style is now the same as pkgs.nixfmt which should be used
   instead.` — from `lintTools` in `flake.nix`. This is the exact warning PB0's
   gate predicted ("the host's own `lintTools`/devShell name it too") and ruled
   a follow-up, not a fix-on-failure. `lint` stays green; the alias still
   resolves. Left in place to keep this upgrade minimal.

4. **Pre-existing noise (unrelated to the pin).** `unknown flake output
   'phase3NegativeDemo'` — a bespoke demo output `nix flake check` has always
   warned about; present at 25.05, not release drift.

No renamed-option warning remains after the `hosts/core/default.nix` fix; the
only surviving warning is the recorded `nixfmt-rfc-style` alias (and the
pre-existing `phase3NegativeDemo` noise).

## Closure diff (verbatim)

`nix build .#nixosConfigurations.core.config.system.build.toplevel --no-link
--print-out-paths` → `/nix/store/nxpb7h4j5rg49cj051r14fsgwx2bzsv6-nixos-system-core-26.05.20260903.a5cc6f2`,
then `nix store diff-closures /run/current-system
/nix/store/nxpb7h4j5rg49cj051r14fsgwx2bzsv6-nixos-system-core-26.05.20260903.a5cc6f2`
(`/run/current-system` = `nixos-system-core-25.05.20260102.ac62194`). ANSI
colour stripped; `∅` = removed, `ε` = empty/added with no version.

Surprising items, named as the plan asked (kernel, glibc, NVIDIA, mitmproxy,
python, node, systemd, plus a few it didn't):

- **kernel** `6.12.63 → 6.18.49` (+15.8 MiB each for `linux` and `initrd-linux`),
  `linux-firmware 20251125 → 20260810` (+60.7 MiB).
- **glibc** `2.40-66 → 2.42-67`.
- **NVIDIA driver** `nvidia-open 6.12.63-570.195.03 → 595.71.05-6.18.49`,
  `nvidia-x11 570.195.03 → 595.71.05` (+31.9 MiB); the driver jumps a full
  release (570 → 595) and the kernel-module suffix order flips.
- **systemd** `257.10 → 260.2` (a `systemd-minimal-libs-261.2` also appears in
  the new closure — split/naming churn the flat diff renders as `→ ∅`).
- **mitmproxy** `python3.12-mitmproxy 12.1.1 → python3.13-mitmproxy 12.2.3`
  (redeployed onto the python3.13 ABI, `-9.6 MiB` / `+9.3 MiB`).
- **python** `python3 3.12.12 → 3.13.15`; the entire `python3.12-*` package set
  is removed and replaced by its `python3.13-*` counterparts.
- **node** `nodejs 22.20.0 → 24.19.0` (a `nodejs-slim 24.19.0` is newly
  dragged in, +196.8 MiB unpacked added while the full `nodejs` shrinks).
- **electron** `37.10.2 → 43.1.0` (`electron-unwrapped` +60.6 MiB).
- **dbus** `1.14.10 → ∅` replaced by `dbus-broker 37`.
- **openssl** `3.4.3 → ∅` (superseded at a newer version under a different
  name; the old 3.4.3 path is gone).

```
55-nixos-aslr-entropy.conf: ∅ → ε
NetworkManager-fortisslvpn-gnome: 1.4.0 → ∅, -591.8 KiB
NetworkManager-iodine-gnome: 1.2.0-unstable-2024-11-02 → ∅, -244.7 KiB
NetworkManager-l2tp-gnome: 1.20.20 → ∅, -1037.2 KiB
NetworkManager-openconnect: 1.2.10 → ∅, -3260.8 KiB
NetworkManager-openvpn: 1.12.0 → ∅, -1690.0 KiB
NetworkManager-sstp-gnome: 1.3.2 → ∅, -1077.9 KiB
NetworkManager-vpnc: 1.4.0 → ∅, -781.4 KiB
OVMF: 202411 → 202602
SDL2_ttf: 2.24.0 → ∅, -184.6 KiB
X-Reload-Triggers: ∅ → ε
X-Restart-Triggers-dbus: ∅ → ε
X-Restart-Triggers-wpa_supplicant: ∅ → ε
abseil-cpp: 20210324.2, 20250127.1 → ∅, -1773.2 KiB
accountsservice: +8.2 KiB
acl: +34.9 KiB
ada: ∅ → 3.4.4, +1336.1 KiB
adwaita-fonts: 48.2 → 50.0, +168.6 KiB
adwaita-icon-theme: 48.0 → 50.0, +42.7 KiB
alsa-lib: 1.2.13 → ∅, +248.7 KiB
alsa-plugins: +14.3 KiB
alsa-ucm-conf: 1.2.12 → ∅, +585.3 KiB
apache-httpd: 2.4.66 → 2.4.68, -24.0 KiB
append-initrd: ε → ∅
appstream: 1.0.4 → ∅, +314.9 KiB
apr: 1.7.5 → 1.7.6
apr-util: 1.6.3 → 1.6.5
aspell: 0.60.8.1 → 0.60.8.2, +38.1 KiB
at-spi2-core: 2.56.2 → ∅, +2308.6 KiB
attr: +22.5 KiB
audit: 4.1.0, ε → ∅, -1585.0 KiB
autostart-ibus: ∅ → ε
avahi: +119.8 KiB
aws-c-auth: 0.8.1 → 0.9.1
aws-c-cal: 0.8.0 → 0.9.2, +13.6 KiB
aws-c-common: 0.10.3 → 0.12.4
aws-c-compression: 0.3.0 → 0.3.1
aws-c-event-stream: 0.5.0 → 0.7.0
aws-c-http: 0.9.2 → 0.11.0, +24.5 KiB
aws-c-io: 0.15.3 → 0.27.2, +42.6 KiB
aws-c-mqtt: 0.11.0 → 0.13.3
aws-c-s3: 0.7.1 → 0.8.7, +28.0 KiB
aws-c-sdkutils: 0.2.1 → 0.2.4
aws-checksums: 0.2.2 → 0.2.7
aws-crt-cpp: 0.29.4 → 0.34.3, +30.1 KiB
aws-sdk-cpp: 1.11.448 → ∅, -7370.3 KiB
baobab: 48.0 → 50.0, +95.2 KiB
bash: 5.2p37 → ∅, +365.5 KiB
bash-completion: 2.16.0 → 2.17.0, +32.0 KiB
bash-interactive: 5.2p37 → ∅, +808.6 KiB
bc: 1.08.1 → 1.08.2
bcache-tools: 1.0.8 → 1.1, +75.6 KiB
bind: 9.20.15 → 9.20.26, +77.1 KiB
bluez: 5.80 → ∅, +806.4 KiB
boehm-gc: 8.2.8 → 8.2.12
boost: 1.87.0 → 1.89.0, -99.2 KiB
bootspec: 1.0.0 → 2.0.0, +36.1 KiB
brltty: 6.7 → 6.9.1, +521.0 KiB
brotli: 1.1.0 → ∅, +119.5 KiB
btrfs-progs: 6.14 → 6.19.1, -11.7 KiB
bubblewrap: 0.11.0 → ∅
busybox: 1.36.1 → 1.37.0
bzip2: -56.9 KiB
c-ares: +800.9 KiB
c-dvar: ∅ → 1.2.0, +118.7 KiB
c-ini: ∅ → 1.1.0, +59.5 KiB
c-rbtree: ∅ → 3.2.0, +56.9 KiB
c-shquote: ∅ → 1.1.0, +37.6 KiB
c-utf8: ∅ → 1.1.0, +20.6 KiB
cairo: 1.18.2 → ∅, +570.8 KiB
ccid: 1.6.2 → 1.7.1
cdparanoia-III: 10.2 → ∅, -721.1 KiB
cdparanoia-iii: +714.9 KiB
celt: 0.11.3 → ∅, -328.3 KiB
chromaprint: 1.5.1 → ∅, +15.5 KiB
cjson: 1.7.18 → ∅, +8.4 KiB
colord: 1.4.6 → 1.4.8, +387.1 KiB
colord-gtk: -73.4 KiB
command-not: ε → ∅
container: +426.8 KiB
coreutils: 9.7 → ∅, +448.4 KiB
coreutils-full: 9.7 → 9.11, -65.0 KiB
cpio: +8.4 KiB
cracklib: 2.10.0 → ∅, -17885.6 KiB
cryptsetup: 2.7.5 → ∅, +684.9 KiB
cups: 2.4.14 → ∅, +191.1 KiB
cups-browsed: +8.3 KiB
cups-filters: +24.8 KiB
cups-pk-helper: +16.2 KiB
curl: 8.14.1 → 8.21.0, +693.4 KiB
dash: 0.5.12 → 0.5.13.3, +14.4 KiB
dav1d: 1.5.1 → ∅, -24.3 KiB
db: -4756.5 KiB
dbus: 1.14.10 → ∅, +149.2 KiB
dbus-broker: ∅ → 37, +413.4 KiB
dconf: 0.40.0 → ∅, +28.9 KiB
decibels: 48.0 → 49.6.1, +112.7 KiB
desktop-file-utils: ∅ → 0.28, +243.3 KiB
dhcpcd: 10.1.0 → 10.3.1, +42.9 KiB
diffutils: +8.5 KiB
dnsmasq: 2.91 → 2.93, +65.2 KiB
dosfstools: +16.9 KiB
duktape: +8.3 KiB
e2fsprogs: 1.47.2 → 1.47.4, +108.5 KiB
ed: 1.21.1 → 1.22.5
editline: 1.17.1 → 1.17.1-unstable-2025-05-24
editorconfig-core-c: 0.12.9 → 0.12.11
egl-gbm: ∅ → 1.1.3, +68.9 KiB
egl-wayland: ∅ → 1.1.21, +251.8 KiB
egl-wayland2: ∅ → 1.0.1, +223.7 KiB
egl-x11: ∅ → 1.0.5, +405.5 KiB
electron: 37.10.2 → 43.1.0
electron-unwrapped: 37.10.2 → 43.1.0, +60609.7 KiB
elfutils: 0.192 → ∅, +200.3 KiB
ell: 0.76 → ∅
empty: ∅ → ε
epiphany: 48.3 → 50.4, +5344.0 KiB
espeak-ng: 1.51.1 → 1.52.0.1-unstable-2025-09-09, +6856.5 KiB
etc-environment.d: ∅ → 50-systemd-path.conf
etc-gai.conf: ∅ → ε
etc-wpa_supplicant-nixos.conf: ∅ → ε
ethtool: 6.14 → 7.0, +823.0 KiB
evince: 48.0 → 48.4, +131.3 KiB
evolution-data-server: 3.56.2 → 3.60.2, +410.8 KiB
exempi: 2.6.5 → 2.6.6, -60.7 KiB
exiv2: 0.28.7 → 0.28.9
expat: 2.7.3 → 2.8.3, +160.5 KiB
f2fs-tools: -58.2 KiB
fc: +189.7 KiB
fdk-aac: +94.5 KiB
ffado: -23.1 KiB
ffmpeg: 7.1.1 → 8.1.2, +5631.6 KiB
ffmpeg-headless: 7.1.1 → 8.1.2, +6880.4 KiB
fftw-double: +5076.6 KiB
fftw-single: 3.3.10 → ∅, -12.0 KiB
file: 5.45 → ∅, +4200.7 KiB
file-roller: 44.5 → ∅, -4579.1 KiB
findutils: +18.0 KiB
firefox: 146.0.1 → 155.0, -228.3 KiB
firefox-unwrapped: 146.0.1 → 155.0, +49679.0 KiB
firmware: +71.7 KiB
flac: +58.5 KiB
flatpak: 1.16.1 → 1.16.6, +263.9 KiB
flite: +9.4 KiB
fluidsynth: 2.4.4 → ∅, +184.4 KiB
fmt: 10.2.1 → 12.1.0
folks: 0.15.9 → 0.15.12, +29.4 KiB
font-alias: ∅ → 1.0.6, +17.3 KiB
font-util: 1.4.1 → 1.4.2
fontconfig: 2.16.0 → ∅, +98.8 KiB
freeglut: 3.6.0 → 3.8.0, +146.5 KiB
freeglut-mupdf: 3.0.0-r13ae6aa2c2f9a7b4266fc2e6116c876237f40477 → 3.0.0-rd5e2256d571b3ef66fb60716c99e35e9d3e570a2, +41.6 KiB
freerdp: 3.15.0 → 3.30.0, +677.2 KiB
freetype: 2.13.3 → ∅, +1099.6 KiB
fribidi: +88.2 KiB
fstrm: ∅ → 0.6.1, +64.1 KiB
fuse: 3.16.2 → ∅, +29.4 KiB
game-music-emu: 0.6.3 → ∅, +827.3 KiB
gamemode: +10.2 KiB
gamescope: 3.16.17 → 3.16.23, +330.8 KiB
gawk: 5.3.2 → 5.4.1, +1108.1 KiB
gcc: 14.3.0 → ∅, -250646.5 KiB
gcr: +67.9 KiB
gd: +88.0 KiB
gdbm: 1.25 → ∅
gdk-pixbuf: 2.42.12 → 2.44.7, +638.9 KiB
gdm: 48.0 → 50.2, -333.7 KiB
gdm-fingerprint.pam: ε → ∅
gdm-launch-environment-env: ∅ → ε
geary: 46.0 → ∅, -16673.2 KiB
getent-glibc: 2.40-66 → 2.42-67
gettext: 0.22.5 → 1.0, +14172.6 KiB
gexiv2: 0.14.5 → 0.16.2, -18.3 KiB
ghostscript-with-X: 10.05.1 → 10.07.1, +1057.8 KiB
git: 2.50.1 → 2.54.0, +3543.8 KiB
gjs: 1.84.2 → 1.88.1, +162.6 KiB
glew: 2.2.0 → ∅, -2152.0 KiB
glfw: -542.5 KiB
glib: 2.84.3 → ∅, +969.4 KiB
glibc: 2.40-66 → ∅, +9954.6 KiB
glibc-iconv: 2.40 → 2.42
glibc-locales: 2.40-66 → 2.42-67, +876.8 KiB
glibc-multi: 2.40-66 → 2.42-67
glibmm: 2.84.0 → 2.88.1, -155.5 KiB
glu: -1462.6 KiB
glycin-loaders: 1.2.1 → 2.1.5, +3700.5 KiB
glycin-thumbnailer: ∅ → 2.1.5, +612.8 KiB
gmime: 3.2.15 → ∅, -724.6 KiB
gmobile: ∅ → 0.7.1, +319.3 KiB
gmp: 6.3.0 → ∅, -730.6 KiB
gmp-with-cxx: +195.1 KiB
gnome-backgrounds: 48.2.1 → 50.0, +1841.3 KiB
gnome-bluetooth: 47.1 → 47.2
gnome-calculator: 48.1 → 50.0, +1515.6 KiB
gnome-calendar: 48.1 → 50.0, +316.8 KiB
gnome-characters: 48.0 → 50.0, +71.2 KiB
gnome-clocks: 48.0 → 50.0, +1867.0 KiB
gnome-color-manager: 3.32.0 → 3.36.2, -1195.9 KiB
gnome-connections: 48.0 → 50.0, +118.5 KiB
gnome-console: 48.0.1 → 50.0, +326.7 KiB
gnome-contacts: 48.0 → 50.0, +89.0 KiB
gnome-control-center: 48.2 → 50.4, +758.2 KiB
gnome-desktop: 44.3 → 44.5, +8.4 KiB
gnome-disk-utility: +13.6 KiB
gnome-font-viewer: 48.0 → 50.0, +140.6 KiB
gnome-initial-setup: 48.1 → 50.1, +95.0 KiB
gnome-keyring: 48.0 → 50.0, +26.5 KiB
gnome-logs: 45.0 → 50.0, +70.5 KiB
gnome-maps: 48.4 → 50.3, +180.2 KiB
gnome-menus: 3.36.0 → 3.38.1, +12.5 KiB
gnome-music: 48.0 → 50.0, +80.4 KiB
gnome-online-accounts: 3.54.3 → 3.58.1
gnome-remote-desktop: 48.1 → 50.2, +446.8 KiB
gnome-session: 48.0 → 50.1, -179.5 KiB
gnome-session-ctl: 47.0.1 → 50.0
gnome-settings-daemon: 48.1 → 50.1, 50.1-gsettings, -24.0 KiB
gnome-shell: 48.2 → 50.4, -114.6 KiB
gnome-system-monitor: 48.1 → 50.0, +278.2 KiB
gnome-text-editor: 48.3 → 50.1, +244.1 KiB
gnome-tour: 48.1 → 50.0, -28.5 KiB
gnome-user-docs: 48.2 → 50.4, +3358.6 KiB
gnome-user-share: 48.0 → 48.3, +55.0 KiB
gnome-weather: 48.0 → 50.0, +58.8 KiB
gnugrep: 3.11 → ∅
gnum4: 1.4.19 → ∅, +509.4 KiB
gnupg: 2.4.8 → 2.4.9, -3392.1 KiB
gnused: ∅ → 4.10, +159.6 KiB
gnutar: -13.1 KiB
gnutls: 3.8.9 → ∅, +738.5 KiB
gobject-introspection: 1.84.0 → ∅, +1635.4 KiB
gobject-introspection-wrapped: 1.84.0 → 1.86.0, +24.8 KiB
gom: 0.5.3 → 0.5.6
gperftools: 2.15 → 2.17.2, -835.1 KiB
gpgme: 1.24.2 → 2.0.1, -603.7 KiB
gpm-unstable: -73.0 KiB
graphics: +11.8 KiB
graphite2: ∅ → 1.3.15, +42.5 KiB
grilo-plugins: 0.3.16 → 0.3.18, +45.4 KiB
groff: 1.23.0 → 1.24.1, +816.9 KiB
gsettings-desktop-schemas: 48.0 → ∅, +1419.8 KiB
gsm: 1.0.22 → ∅
gspell: 1.14.0 → 1.14.4, +21.1 KiB
gssdp: 1.6.3 → 1.6.6
gst-devtools: 1.26.3 → 1.26.11, -1304.9 KiB
gst-editing-services: 1.26.3 → 1.26.11, -69.1 KiB
gst-libav: 1.26.3 → 1.26.11
gst-plugins-bad: 1.26.3 → ∅, -317.4 KiB
gst-plugins-base: 1.26.3 → ∅
gst-plugins-good: 1.26.3 → 1.26.11, -394.6 KiB
gst-plugins-rs: 0.13.5 → 0.14.4, -14986.4 KiB
gst-plugins-ugly: 1.26.3 → 1.26.11, -16.0 KiB
gst-rtsp-server: 1.26.3 → 1.26.11, -20.1 KiB
gst-thumbnailers: ∅ → 1.0.0, +1841.0 KiB
gstreamer: 1.26.3 → ∅, -6494.4 KiB
gtest: 1.16.0 → ∅, +834.4 KiB
gtk+3: 3.24.49 → ∅, +17180.2 KiB
gtk-frdp: 0-unstable-2025-03-14 → 0-unstable-2026-04-24
gtk-vnc: +91.8 KiB
gtk3-immodule.cache: ∅ → ε
gtk4: 4.18.6 → ∅, +1661.7 KiB
gtkmm: 4.18.0 → 4.22.0, +164.8 KiB
gtksourceview: 5.16.0 → 5.20.0, -14.4 KiB
gumbo: 0.13.0 → 0.13.2, +8.5 KiB
gupnp: ∅ → 1.6.10
gupnp-av: 0.14.3 → 0.14.5
gvfs: 1.57.2 → 1.60.2, +221.8 KiB
gweather-locations: ∅ → 2026.2, +22505.1 KiB
gyre-fonts: 2.005 → 2.501, +484.8 KiB
gzip: -154.2 KiB
harfbuzz: 10.2.0 → ∅, +2897.4 KiB
harfbuzz-icu: 10.2.0 → 13.2.1, +308.1 KiB
hfst-ospell: +8.7 KiB
hidapi: 0.14.0 → 0.15.0
hostname-debian: +65.7 KiB
hunspell: -8.8 KiB
hwdata: 0.393 → ∅, +897.9 KiB
hwdb.bin: +813.7 KiB
hwloc: ∅ → 2.13.0, +450.7 KiB
iana-etc: 20250108 → ∅
ibus: 1.5.31 → 1.5.33, +13999.1 KiB
ibus-with-plugins: ∅ → 1.5.33, +23.8 KiB
icu4c: 75.1 → ∅, +2720.9 KiB
ijs: 10.05.1 → 10.07.1
imath: 3.1.12 → ∅, +19.0 KiB
inih: 58 → 62
initrd-linux: 6.12.63 → 6.18.49, +15425.3 KiB
intel2200BGFirmware: 3.1 → ∅, -242.2 KiB
iodine: 0.8.0 → ∅, -190.9 KiB
iproute2: 6.14.0 → 7.0.0, -3923.1 KiB
iptables: 1.8.11 → 1.8.13, +35.4 KiB
iputils: -16.1 KiB
ipw2200-firmware: ∅ → 3.1, +242.2 KiB
isl: 0.20 → ∅, -2576.5 KiB
iso-codes: 4.17.0 → ∅, +4207.0 KiB
jansson: 2.14.1 → 2.15.0
jbig2dec: +8.2 KiB
jemalloc: 5.3.0 → 5.3.1, -2329.4 KiB
jq: 1.7.1 → ∅, +87.4 KiB
json-glib: 1.10.6 → ∅, +8.9 KiB
kbd: 2.7.1 → ∅, +174.1 KiB
kexec-tools: 2.0.29 → ∅, +34.3 KiB
krb5: 1.21.3 → ∅, +61.9 KiB
lame: +18.0 KiB
lcms2: 2.17 → ∅, +18.3 KiB
ldb: 2.9.2 → ∅, -864.3 KiB
ldns: 1.8.4 → 1.9.2, +9.3 KiB
lerc: 4.0.0 → 4.1.1, -54.2 KiB
less: 668 → 692, +45.0 KiB
libICE: 1.1.2 → ∅, -122.9 KiB
libSM: 1.2.5 → ∅, -44.9 KiB
libX11: 1.8.12 → ∅, -5303.7 KiB
libXNVCtrl: 570.195.03 → 595.71.05
libXScrnSaver: 1.2.4 → ∅, -32.6 KiB
libXau: 1.0.12 → ∅, -49.7 KiB
libXaw: 1.0.16 → ∅, -1580.1 KiB
libXcomposite: 0.4.6 → ∅, -49.5 KiB
libXcursor: 1.2.3 → ∅, -155.3 KiB
libXdamage: 1.1.6 → ∅, -35.3 KiB
libXdmcp: 1.1.5 → ∅, -61.7 KiB
libXext: 1.3.6 → ∅, -189.0 KiB
libXfixes: 6.0.1 → ∅, -74.9 KiB
libXfont2: 2.0.7 → ∅, -271.7 KiB
libXft: 2.3.9 → ∅, -301.4 KiB
libXi: 1.8.2 → ∅, -172.2 KiB
libXinerama: 1.1.5 → ∅, -42.7 KiB
libXmu: 1.2.1 → ∅, -161.7 KiB
libXpm: 3.5.17 → ∅, -92.6 KiB
libXrandr: 1.5.4 → ∅, -132.3 KiB
libXrender: 0.9.12 → ∅, -109.6 KiB
libXres: 1.2.2 → ∅, -22.7 KiB
libXt: 1.3.1 → ∅, -487.1 KiB
libXtst: 1.2.5 → ∅, -238.4 KiB
libXv: 1.0.13 → ∅, -62.0 KiB
libXxf86vm: 1.1.6 → ∅, -80.4 KiB
libadwaita: 1.7.5 → 1.9.3, -15.8 KiB
libajantv2: 17.1.3 → ∅, +498.6 KiB
libaom: 3.11.0 → ∅, -1827.4 KiB
libapparmor: 4.1.2 → ∅
libarchive: 3.8.2 → 3.8.8, +18.4 KiB
libargon2: -13.1 KiB
libass: 0.17.3 → ∅
libassuan: -103.3 KiB
libatasmart: -43.8 KiB
libavif: 1.2.1 → 1.4.1, +23.5 KiB
libblake3: 1.8.2 → 1.8.5, -18.2 KiB
libblockdev: 3.3.0 → 3.4.0, -21.4 KiB
libbluray: 1.3.4 → ∅, +1205.6 KiB
libbpf: 1.5.0 → ∅, +477.4 KiB
libbytesize: 2.11 → 2.12
libcacard: +137.8 KiB
libcamera: 0.5.0 → ∅, +636.9 KiB
libcanberra: -19.1 KiB
libcap: 2.75 → ∅, +181.0 KiB
libcap-ng: 0.8.5 → ∅, +101.0 KiB
libcbor: 0.12.0 → ∅, +8.3 KiB
libcdio: 2.2.0 → 2.3.0
libcloudproviders: 0.3.6 → 0.4.0
libcpuid: 0.7.1 → 0.8.1, -25.2 KiB
libde265: 1.0.15 → ∅, -287.5 KiB
libdecor: 0.2.2 → ∅
libdeflate: 1.23 → ∅, +25.4 KiB
libdisplay-info: 0.2.0 → 0.3.0, +494.1 KiB
libdrm: 2.4.125 → ∅, +516.9 KiB
libdvdread: 6.1.3 → ∅, +197.4 KiB
libedit: 20240808-3.1 → 20251016-3.1
libei: 1.4.1 → 1.5.0, +35.0 KiB
libepoxy: -79.7 KiB
liberation-fonts: -18.9 KiB
libev: +225.9 KiB
libevdev: 1.13.4 → 1.13.6
libevent: ∅ → 2.1.13
libexif: 0.6.25 → 0.6.26, +250.1 KiB
libffi: 3.4.8 → ∅, +33.7 KiB
libfido2: 1.15.0 → ∅, +332.7 KiB
libfontenc: 1.1.8 → 1.1.9, +101.4 KiB
libfyaml: +951.1 KiB
libgcrypt: 1.10.3 → ∅, +713.7 KiB
libgdata: 0.18.1 → ∅, -2022.9 KiB
libgee: -24.0 KiB
libgit2: 1.9.0 → 1.9.7, +16.3 KiB
libglvnd: -2210.9 KiB
libglycin: ∅ → 2.1.5, +4994.0 KiB
libglycin-gtk4: ∅ → 2.1.5, +358.1 KiB
libgnomekbd: +8.5 KiB
libgpg-error: 1.51 → ∅, +108.3 KiB
libgphoto2: 2.5.31 → 2.5.34, +1070.5 KiB
libgsf: 1.14.53 → 1.14.58, +14.0 KiB
libgtop: +8.3 KiB
libgweather: 4.4.4 → 4.6.0, -21577.2 KiB
libgxps: +13.0 KiB
libheif: 1.19.8 → 1.23.1, +927.7 KiB
libice: ∅ → 1.1.2, +164.2 KiB
libidn: 1.42 → 1.44
libiec61883: +11.6 KiB
libimagequant: 4.3.4 → 4.4.1, +195.7 KiB
libimobiledevice: 1.3.0-unstable-2024-05-20 → 1.4.0, +49.2 KiB
libimobiledevice-glue: 1.3.1 → 1.3.2
libinput: 1.27.1 → 1.31.3, +145.9 KiB
libiptcdata: 1.0.5 → ∅, -167.4 KiB
libjpeg-turbo: 3.0.4 → ∅, +545.0 KiB
libjxl: 0.11.1 → 0.11.2, +2187.2 KiB
libksba: +8.9 KiB
liblouis: +8.8 KiB
libmanette: 0.2.12 → 0.2.13, +16.2 KiB
libmbim: 1.30.0 → 1.34.0, +126.1 KiB
libmd: -60.7 KiB
libmicrohttpd: 1.0.1 → ∅
libmnl: -18.2 KiB
libmodplug: +12.0 KiB
libmpc: 1.3.1 → 1.4.0, -253.3 KiB
libmpg123: 1.32.10 → 1.33.7, +53.5 KiB
libmsgraph: 0.3.3 → 0.3.4
libmysofa: ∅ → 1.3.4
libndctl: 79 → 83, +48.6 KiB
libnetfilter_conntrack: 1.1.0 → 1.1.1, +12.7 KiB
libnftnl: 1.2.9 → 1.3.1, +9.0 KiB
libnl: 3.11.0 → ∅, +65.1 KiB
libnma: -12.0 KiB
libnotify: 0.8.6 → ∅, +11.3 KiB
libnvme: 1.11.1 → 1.16.1, +199.7 KiB
libogg: 1.3.5 → ∅
libopenmpt: 0.7.16 → ∅, +475.8 KiB
libopus: 1.5.2 → ∅, +59.0 KiB
libpcap: 1.10.5 → ∅, -546.2 KiB
libpciaccess: 0.18.1 → ∅, +203.0 KiB
libpeas: 1.36.0 → ∅, -603.1 KiB
libphonenumber: 9.0.3 → 9.0.31, -167.6 KiB
libplist: 2.6.0 → 2.7.0
libpng: 1.6.46 → ∅, -260.4 KiB
libpng-apng: 1.6.46 → ∅, +256.6 KiB
libportal-gtk3: 0.9.1 → ∅, -278.2 KiB
libppd: +8.0 KiB
libproxy: 0.5.9 → 0.5.12
libpulseaudio: -131.1 KiB
libqmi: 1.36.0 → 1.38.0, +124051.6 KiB
libqrtr-glib: -8.0 KiB
libraqm: 0.10.2 → 0.10.5
libressl: 4.1.1 → 4.2.1, -46.6 KiB
librest: ∅ → 0.10.2, +211.2 KiB
librsvg: 2.60.0 → 2.62.3, -99.7 KiB
libseccomp: ∅ → 2.6.1
libselinux: 3.8.1 → ∅, +10.8 KiB
libshumate: 1.4.0 → 1.6.3, +17.9 KiB
libsm: ∅ → 1.2.6, +65.7 KiB
libsndfile: +25.2 KiB
libsodium: 1.0.20 → 1.0.22-unstable-2026-04-09, +133.0 KiB
libsoup: 2.74.3, 3.6.5 → ∅, -1183.1 KiB
libspelling: 0.4.8 → 0.4.10
libsrtp: 2.7.0 → ∅, +8.4 KiB
libssh: 0.11.3 → 0.12.2, +158.5 KiB
libssh2: +8.9 KiB
libtasn1: 4.20.0 → ∅
libtatsu: ∅ → 1.0.5, +60.0 KiB
libthai: 0.1.29 → ∅, +11.7 KiB
libtheora: +12.0 KiB
libtiff: 4.7.0 → 4.7.2, +909.6 KiB
libtirpc: 1.3.6 → 1.3.7
libtpms: 0.10.0 → ∅
libtraceevent: ∅ → 1.9, +609.4 KiB
libtracefs: ∅ → 1.8.3, +480.9 KiB
libunistring: 1.3 → ∅, +20.9 KiB
libunwind: 1.8.1 → ∅
liburcu: 0.15.2 → 0.15.6, +10.3 KiB
liburing: 2.9 → ∅, +13.6 KiB
libusb: 1.0.28 → ∅, +9.8 KiB
libusbmuxd: 2.1.0 → 2.1.1
libuv: 1.51.0 → ∅, +15.3 KiB
libva: 2.22.0 → ∅, +8.3 KiB
libva-minimal: 2.22.0 → ∅, +8.2 KiB
libvmaf: +26.3 KiB
libvoikko: 4.3.2 → 4.3.3
libvpx: 1.15.2 → ∅, +709.2 KiB
libwacom: 2.15.0 → 2.18.0, +8.9 KiB
libwebp: 1.5.0 → ∅, +116.9 KiB
libx11: +5558.0 KiB
libxau: +60.1 KiB
libxaw: ∅ → 1.0.16, +1578.2 KiB
libxcb: +2088.2 KiB
libxcb-image: ∅ → 0.4.1, +27.0 KiB
libxcb-keysyms: ∅ → 0.4.1, +35.4 KiB
libxcb-render-util: ∅ → 0.3.10, +27.8 KiB
libxcb-util: ∅ → 0.4.1, +35.5 KiB
libxcb-wm: ∅ → 0.4.2, +111.2 KiB
libxcomposite: +55.4 KiB
libxcrypt: 4.4.38 → ∅, -199.8 KiB
libxcursor: +177.1 KiB
libxdamage: +39.5 KiB
libxdmcp: +57.2 KiB
libxext: +251.1 KiB
libxfixes: +80.3 KiB
libxfont_2: ∅ → 2.0.9, +271.9 KiB
libxft: +323.5 KiB
libxi: ∅ → 1.8.3, +234.9 KiB
libxinerama: +49.7 KiB
libxkbcommon: 1.8.1 → ∅, +584.8 KiB
libxml++: 3.0.1 → ∅, -8.9 KiB
libxml2: 2.13.8 → ∅, -282.3 KiB
libxmlb: 0.3.22 → ∅
libxmu: ∅ → 1.3.1, +160.0 KiB
libxpm: ∅ → 3.5.19, +87.9 KiB
libxrandr: +150.6 KiB
libxrender: +144.3 KiB
libxres: ∅ → 1.2.3, +22.5 KiB
libxscrnsaver: +32.9 KiB
libxslt: 1.1.43 → ∅
libxt: ∅ → 1.3.1, +483.7 KiB
libxtst: +234.1 KiB
libxv: +61.5 KiB
libxxf86vm: ∅ → 1.1.7, +80.1 KiB
libyaml: +8.8 KiB
libytnef: 2.1.2 → ∅, -216.6 KiB
libyuv: -361.8 KiB
libzip: ∅ → 1.11.4, +265.6 KiB
lilv: 0.24.24 → ∅, +30.6 KiB
linux: 6.12.63, 6.12.63-modules → 6.18.49, +15790.5 KiB
linux-firmware: 20251125 → 20260810, +60730.2 KiB
linux-headers: 6.12.7 → 6.18.7, +355.2 KiB
linux-headers-static: 6.12.7 → 6.18.7, +355.2 KiB
linux-pam: 1.6.1 → ∅, +1133.2 KiB
llhttp: 9.2.1 → ∅, -68.2 KiB
llvm: 19.1.7 → 21.1.8, +85233.1 KiB
lm-sensors: 3.6.0 → 3.6.2, -176.9 KiB
lmdb: ∅ → 0.9.35, +209.7 KiB
localsearch: 3.9.0 → 3.11.1, -362.9 KiB
logrotate: -9.6 KiB
loupe: 48.1 → 50.0, -830.2 KiB
lowdown: 1.3.2 → 3.0.1, +49.4 KiB
lttng-ust: 2.13.8 → ∅, +541.6 KiB
lua: +28.0 KiB
luajit: 2.1.1741730670 → 2.1.1774638290, +38.2 KiB
lvm2: 2.03.31 → ∅, -176.5 KiB
lynx: +19.8 KiB
lz4: -8.0 KiB
lzo: -86.5 KiB
malcontent: 0.13.0 → 0.13.1
man-db: 2.13.0 → 2.13.1, -100.0 KiB
mangohud: 0.8.1 → 0.8.3, +6741.0 KiB
mbedtls: 3.6.5 → ∅, +716.6 KiB
mbrola-voices: ∅ → 0-unstable-2020-03-30, +660126.5 KiB
mcpp: 2.7.2.1 → 2.7.2.3, +737.9 KiB
mdadm: 4.3 → 4.4, -20.2 KiB
merve: ∅ → 1.2.2, +106.3 KiB
mesa: 25.0.7 → 26.1.8, +227336.5 KiB
mesa-demos: +638.2 KiB
mesa-libgbm: 25.0.1 → ∅
mkpasswd: 5.6.4 → 5.6.6
modemmanager: 1.22.0 → 1.24.2, +1713.5 KiB
mount-pstore.sh: ε → ∅
mpdecimal: 4.0.0 → ∅
mpfr: -803.7 KiB
mpg123: 1.32.10 → 1.33.7, +53.6 KiB
mtools: 4.0.48 → 4.0.49, +9.3 KiB
mupdf: 1.25.3 → 1.27.2, +4458.9 KiB
mutter: 48.3.1 → 50.4, +884.6 KiB
nano: 8.6 → 9.2, +209.9 KiB
nautilus: 48.2 → 50.2.2, +291.7 KiB
ncurses: 6.5 → ∅, +169.4 KiB
neon: 0.32.5 → ∅, +136.0 KiB
net-snmp: 5.9.4 → 5.9.5.2, -29.9 KiB
net-tools: 2.10 → ∅, -1049.2 KiB
nettle: 3.10.1 → ∅, +18.8 KiB
networkmanager: 1.52.2 → 1.56.0, +1339.4 KiB
nftables: 1.1.3 → 1.1.6, +117.4 KiB
nghttp2: 1.65.0 → ∅, +2923.0 KiB
nghttp3: +599.5 KiB
ngtcp2: +1351.8 KiB
nilfs-utils: 2.2.11 → 2.2.12, -12.9 KiB
nix: 2.28.5 → 2.34.8, -57124.9 KiB
nix-cmd: ∅ → 2.34.8, +1066.8 KiB
nix-expr: ∅ → 2.34.8, +3373.1 KiB
nix-fetchers: ∅ → 2.34.8, +1538.2 KiB
nix-flake: ∅ → 2.34.8, +956.8 KiB
nix-ld: 2.0.4 → 2.0.6
nix-main: ∅ → 2.34.8, +393.5 KiB
nix-manual: ∅ → 2.34.8, +24299.5 KiB
nix-nswrapper: ∅ → 2.34.8, +131.8 KiB
nix-store: ∅ → 2.34.8, +5913.1 KiB
nix-util: ∅ → 2.34.8, +2409.6 KiB
nixos: -72.4 KiB
nixos-configuration-reference: -14166.4 KiB
nixos-icons: 0-unstable-2024-04-10 → 0-unstable-2025-06-28
nixos-init: ∅ → 0.1.0, +679.1 KiB
nixos-manual: +7095.4 KiB
nixos-rebuild-ng: ∅ → 26.05, +296.8 KiB
nixos-system-core: 25.05.20260102.ac62194 → 26.05.20260903.a5cc6f2, +354.8 KiB
nodejs: 22.20.0 → 24.19.0, -88093.9 KiB
nodejs-slim: ∅ → 24.19.0, +196843.0 KiB
noto-fonts-cjk-sans: ∅ → 2.004, +63078.2 KiB
noto-fonts-cjk-serif: ∅ → 2.003, +56142.2 KiB
noto-fonts-color-emoji: 2.047 → 2.051, +467.1 KiB
npth: -44.1 KiB
nsncd: 1.5.1 → 1.5.2, +31.8 KiB
nspr: 4.38 → 4.40
nss: 3.101.2, 3.119.1 → 3.128, +332.0 KiB
nss-cacert: 3.117, 3.117-p11kit → 3.126, 3.126-p11kit, -125.7 KiB
ntfs3g: 2022.10.3 → 2026.7.7, +29.1 KiB
numactl: +25.8 KiB
nuspell: 5.1.6 → 5.1.7
nvidia-egl-external: ∅ → ε
nvidia-egl-external-platforms-x32: ∅ → ε
nvidia-open: 6.12.63-570.195.03 → 595.71.05-6.18.49, +2487.6 KiB
nvidia-settings: 570.195.03 → 595.71.05, +48.9 KiB
nvidia-vaapi-driver: 0.0.13 → 0.0.17, +8.0 KiB
nvidia-x11: 570.195.03-6.12.63 → 595.71.05, +31993.6 KiB
ocl-icd: 2.3.2 → ∅, +190.4 KiB
onetbb: ∅ → 2022.3.0, +626.1 KiB
onnxruntime: 1.22.0 → 1.24.4, +5248.6 KiB
openal-soft: 1.24.2 → ∅, +36.1 KiB
openapv: +1404.8 KiB
openconnect: 9.12 → ∅, -1355.2 KiB
opencore-amr: +8.0 KiB
openexr: 3.2.4 → ∅, -3289.0 KiB
openfec: 1.4.2.11 → ∅
openfortivpn: 1.23.1 → ∅, -139.2 KiB
openh264: +24.4 KiB
openjpeg: 2.5.2 → ∅, +43.6 KiB
openldap: 2.6.9 → 2.6.13, +191.5 KiB
openresolv: 3.13.2 → 3.17.4, +34.7 KiB
openssh: 10.0p2 → 10.5p1, +92.2 KiB
openssl: 3.4.3 → ∅, +1880.8 KiB
openvpn: 2.6.14 → ∅, -1459.9 KiB
orc: -28.0 KiB
orca: 48.2 → 50.2, +2818.0 KiB
osinfo-db: 20250124 → 20251212, +313.6 KiB
ostree: 2025.2 → 2026.1, +79.2 KiB
p11-kit: 0.25.5 → ∅, +1673.1 KiB
p7zip: +448.3 KiB
packagekit: 1.3.1 → 1.3.5, +465.7 KiB
pango: 1.56.3 → ∅, +1744.1 KiB
pangomm: 2.56.1 → 2.56.2
papers: ∅ → 50.2, +19989.1 KiB
parted: 3.6 → 3.7, +142.8 KiB
patch: 2.7.6 → 2.8, -30.5 KiB
pciutils: 3.13.0 → 3.15.0, +138.4 KiB
pcre2: 10.44 → ∅, +261.9 KiB
pcsclite: 2.3.0 → ∅
pcsclite-with-polkit: 2.3.0 → 2.4.1
perl: 5.40.0 → ∅, -4486.5 KiB
perl5.40.0-Authen-SASL: 2.1700 → ∅, -77.1 KiB
perl5.40.0-CGI: 4.59 → ∅, -316.7 KiB
perl5.40.0-CGI-Fast: 2.16 → ∅, -13.1 KiB
perl5.40.0-Clone: 0.46 → ∅, -47.1 KiB
perl5.40.0-Config-IniFiles: 3.000003 → ∅, -91.2 KiB
perl5.40.0-Crypt-URandom: 0.39 → ∅, -13.7 KiB
perl5.40.0-DBD-SQLite: 1.74 → ∅, -431.0 KiB
perl5.40.0-DBI: 1.644 → ∅, -2070.4 KiB
perl5.40.0-Digest-HMAC: 1.04 → ∅, -9.3 KiB
perl5.40.0-Encode-Locale: 1.05 → ∅, -30.2 KiB
perl5.40.0-FCGI: 0.82 → ∅, -79.9 KiB
perl5.40.0-FCGI-ProcManager: 0.28 → ∅, -27.6 KiB
perl5.40.0-File-BaseDir: 0.09 → ∅, -37.8 KiB
perl5.40.0-File-DesktopEntry: 0.22 → ∅, -54.4 KiB
perl5.40.0-File-Listing: 6.16 → ∅, -34.5 KiB
perl5.40.0-File-MimeInfo: 0.33 → ∅, -157.3 KiB
perl5.40.0-File-Slurp: 9999.32 → ∅, -33.5 KiB
perl5.40.0-HTML-Parser: 3.81 → ∅, -307.3 KiB
perl5.40.0-HTML-TagCloud: 0.38 → ∅, -12.8 KiB
perl5.40.0-HTML-Tagset: 3.20 → ∅, -31.3 KiB
perl5.40.0-HTTP-CookieJar: 0.014 → ∅, -51.0 KiB
perl5.40.0-HTTP-Cookies: 6.10 → ∅, -80.8 KiB
perl5.40.0-HTTP-Daemon: 6.16 → ∅, -67.2 KiB
perl5.40.0-HTTP-Date: 6.06 → ∅, -30.3 KiB
perl5.40.0-HTTP-Message: 6.45 → ∅, -283.9 KiB
perl5.40.0-HTTP-Negotiate: 6.01 → ∅, -38.4 KiB
perl5.40.0-IO-HTML: 1.004 → ∅, -44.5 KiB
perl5.40.0-IO-Socket-SSL: 2.083 → ∅, -481.4 KiB
perl5.40.0-IO-Stringy: 2.113 → ∅, -77.5 KiB
perl5.40.0-IPC-System-Simple: 1.30 → ∅, -73.0 KiB
perl5.40.0-JSON: 4.10 → ∅, -174.7 KiB
perl5.40.0-LWP-MediaTypes: 6.04 → ∅, -117.5 KiB
perl5.40.0-Mozilla-CA: 20230821 → ∅, -523.4 KiB
perl5.40.0-Net-DBus: 1.2.0 → ∅, -935.6 KiB
perl5.40.0-Net-HTTP: 6.23 → ∅, -75.6 KiB
perl5.40.0-Net-SMTP-SSL: 1.04 → ∅
perl5.40.0-Net-SSLeay: 1.92 → ∅, -1126.2 KiB
perl5.40.0-String-ShellQuote: 1.04 → ∅, -16.1 KiB
perl5.40.0-TermReadKey: 2.38 → ∅, -47.3 KiB
perl5.40.0-Test-Fatal: 0.017 → ∅, -36.9 KiB
perl5.40.0-Test-Needs: 0.002010 → ∅, -22.9 KiB
perl5.40.0-Test-RequiresInternet: 0.05 → ∅, -12.0 KiB
perl5.40.0-TimeDate: 2.33 → ∅, -176.2 KiB
perl5.40.0-Try-Tiny: 0.31 → ∅, -47.3 KiB
perl5.40.0-URI: 5.21 → ∅, -316.3 KiB
perl5.40.0-WWW-RobotRules: 6.02 → ∅, -37.0 KiB
perl5.40.0-X11-Protocol: 0.56 → ∅, -488.7 KiB
perl5.40.0-XML-Parser: 2.46 → ∅, -859.2 KiB
perl5.40.0-XML-Twig: 3.52 → ∅, -1005.4 KiB
perl5.40.0-libnet: 3.15 → ∅, -211.0 KiB
perl5.40.0-libwww-perl: 6.72 → ∅, -584.1 KiB
perl5.42.0-Authen-SASL: ∅ → 2.1900, +84.5 KiB
perl5.42.0-CGI: ∅ → 4.59, +316.7 KiB
perl5.42.0-CGI-Fast: ∅ → 2.16, +13.1 KiB
perl5.42.0-Clone: +43.1 KiB
perl5.42.0-Config-IniFiles: ∅ → 3.000003, +91.2 KiB
perl5.42.0-Crypt-URandom: ∅ → 0.55, +32.5 KiB
perl5.42.0-Digest-HMAC: ∅ → 1.05, +9.2 KiB
perl5.42.0-Encode-Locale: +30.2 KiB
perl5.42.0-FCGI: ∅ → 0.82, +80.5 KiB
perl5.42.0-FCGI-ProcManager: ∅ → 0.28, +27.6 KiB
perl5.42.0-File-BaseDir: +37.8 KiB
perl5.42.0-File-DesktopEntry: +54.4 KiB
perl5.42.0-File-Listing: +34.5 KiB
perl5.42.0-File-MimeInfo: +157.5 KiB
perl5.42.0-File-Slurp: ∅ → 9999.32, +33.5 KiB
perl5.42.0-HTML-Parser: +307.4 KiB
perl5.42.0-HTML-TagCloud: ∅ → 0.38, +12.8 KiB
perl5.42.0-HTML-Tagset: +31.3 KiB
perl5.42.0-HTTP-CookieJar: +51.0 KiB
perl5.42.0-HTTP-Cookies: +80.8 KiB
perl5.42.0-HTTP-Daemon: +69.1 KiB
perl5.42.0-HTTP-Date: +30.3 KiB
perl5.42.0-HTTP-Message: +283.9 KiB
perl5.42.0-HTTP-Negotiate: +38.4 KiB
perl5.42.0-IO-HTML: +44.5 KiB
perl5.42.0-IO-Socket-SSL: ∅ → 2.083, +481.4 KiB
perl5.42.0-IO-Stringy: ∅ → 2.113, +77.5 KiB
perl5.42.0-IPC-System-Simple: +73.0 KiB
perl5.42.0-JSON: ∅ → 4.10, +174.7 KiB
perl5.42.0-LWP-MediaTypes: +117.5 KiB
perl5.42.0-Mozilla-CA: ∅ → 20230821, +466.0 KiB
perl5.42.0-Net-DBus: +935.5 KiB
perl5.42.0-Net-HTTP: +75.6 KiB
perl5.42.0-Net-SMTP-SSL: ∅ → 1.04
perl5.42.0-Net-SSLeay: ∅ → 1.92, +1142.2 KiB
perl5.42.0-TermReadKey: ∅ → 2.38, +47.3 KiB
perl5.42.0-Test-Fatal: +36.9 KiB
perl5.42.0-Test-Needs: +22.9 KiB
perl5.42.0-Test-RequiresInternet: +12.0 KiB
perl5.42.0-TimeDate: +176.2 KiB
perl5.42.0-Try-Tiny: +47.3 KiB
perl5.42.0-URI: +316.3 KiB
perl5.42.0-WWW-RobotRules: +37.0 KiB
perl5.42.0-X11-Protocol: +489.0 KiB
perl5.42.0-XML-Parser: +859.2 KiB
perl5.42.0-XML-Twig: +1005.5 KiB
perl5.42.0-libnet: ∅ → 3.15, +211.0 KiB
perl5.42.0-libwww-perl: +584.6 KiB
phodav: ∅ → 3.0, +147.8 KiB
picotts: ∅ → 0-unstable-2021-05-06, +6923.5 KiB
pipewire: 1.4.7 → 1.6.6, +3096.7 KiB
pipewire-ladspa: ∅ → ε
pixman: 0.44.2 → ∅, +84.3 KiB
plutosvg: ∅ → 0.0.8, +76.2 KiB
plutovg: ∅ → 1.3.3, +480.5 KiB
plymouth: 24.004.60 → 26.134.222, +52.1 KiB
polkit: 126 → 127, +84.8 KiB
poppler-glib: 25.07.0 → 26.06.0, +379.8 KiB
poppler-utils: 25.07.0 → 26.06.0, +488.4 KiB
popt: -55.0 KiB
ppp: +45.5 KiB
procps: 4.0.4 → ∅, +697.7 KiB
protobuf: 21.12, 30.2 → 34.1, -17430.8 KiB
proton-ge-bin-GE-Proton10: 25 → ∅
proton-ge-bin-GE-Proton11: ∅ → 1
proton-pass: 1.31.2 → 1.36.1, +50309.9 KiB
protonmail-bridge: 3.19.0 → 3.24.2, +3485.7 KiB
protonmail-desktop: 1.9.1 → 1.13.0, -55.4 KiB
protontricks: 1.12.1 → 1.14.1, +96.1 KiB
publicsuffix-list: 0-unstable-2025-03-12 → ∅, +28.6 KiB
python3: 3.12.12 → 3.13.15, -90874.8 KiB
python3.12-aioquic: 1.2.0 → ∅, -1390.2 KiB
python3.12-argcomplete: 3.5.3 → ∅, -335.5 KiB
python3.12-argon2-cffi: 23.1.0 → ∅, -111.2 KiB
python3.12-argon2-cffi-bindings: 21.2.0 → ∅, -69.3 KiB
python3.12-asgiref: 3.8.1 → ∅, -218.2 KiB
python3.12-attrs: 25.3.0 → ∅, -611.1 KiB
python3.12-blinker: 1.9.0 → ∅, -77.7 KiB
python3.12-brotli: 1.1.0 → ∅, -944.8 KiB
python3.12-certifi: 2025.01.31 → ∅, -543.0 KiB
python3.12-cffi: 1.17.1 → ∅, -1437.0 KiB
python3.12-click: 8.1.8 → ∅, -1226.9 KiB
python3.12-cryptography: 44.0.2 → ∅, -5197.0 KiB
python3.12-dbus-python: 1.4.0 → ∅, -695.0 KiB
python3.12-dnspython: 2.7.0 → ∅, -3613.2 KiB
python3.12-flask: 3.1.0 → ∅, -1093.9 KiB
python3.12-gst-python: 1.26.0 → ∅, -172.8 KiB
python3.12-h11: 0.16.0 → ∅, -269.2 KiB
python3.12-h2: 4.2.0 → ∅, -710.5 KiB
python3.12-hpack: 4.1.0 → ∅, -614.5 KiB
python3.12-hyperframe: 6.1.0 → ∅, -134.9 KiB
python3.12-idna: 3.10 → ∅, -904.4 KiB
python3.12-itsdangerous: 2.2.0 → ∅, -148.2 KiB
python3.12-jinja2: 3.1.6 → ∅, -1820.0 KiB
python3.12-kaitaistruct: 0.10 → ∅, -87.3 KiB
python3.12-ldap3: 2.9.1 → ∅, -6567.9 KiB
python3.12-libevdev: 0.11 → ∅, -267.7 KiB
python3.12-libpass: 1.9.0 → ∅, -2777.2 KiB
python3.12-lz4: 4.4.3 → ∅, -998.3 KiB
python3.12-markdown: 3.8.2 → ∅, -1053.2 KiB
python3.12-markupsafe: 3.0.2 → ∅, -85.8 KiB
python3.12-mitmproxy: 12.1.1 → ∅, -9610.0 KiB
python3.12-mitmproxy-linux: 0.12.3 → ∅, -2353.2 KiB
python3.12-mitmproxy-rs: 0.12.3 → ∅, -7753.9 KiB
python3.12-msgpack: 1.1.0 → ∅, -381.4 KiB
python3.12-packaging: 24.2 → ∅, -689.0 KiB
python3.12-passlib: 1.9.0 → ∅
python3.12-pillow: 11.2.1 → ∅, -4582.1 KiB
python3.12-psutil: 7.0.0 → ∅, -2924.9 KiB
python3.12-publicsuffix2: 2.20191221 → ∅, -293.7 KiB
python3.12-pyasn1: 0.6.1 → ∅, -1249.9 KiB
python3.12-pyasn1-modules: 0.4.2 → ∅, -2901.3 KiB
python3.12-pycairo: 1.27.0 → ∅, -500.8 KiB
python3.12-pycparser: 2.22 → ∅, -1760.3 KiB
python3.12-pycups: 2.0.4 → ∅, -242.4 KiB
python3.12-pycurl: 7.45.3-unstable-2024-10-17 → ∅, -432.3 KiB
python3.12-pygobject: 3.50.0 → ∅, -1218.6 KiB
python3.12-pylsqpack: 0.3.20 → ∅, -906.6 KiB
python3.12-pyopenssl: 25.0.0 → ∅, -716.2 KiB
python3.12-pyparsing: 3.2.3 → ∅, -1375.9 KiB
python3.12-pyperclip: 1.9.0 → ∅, -93.5 KiB
python3.12-pysmbc: 1.0.25.1 → ∅, -101.4 KiB
python3.12-pyudev: 0.24.3 → ∅, -544.6 KiB
python3.12-pyxdg: 0.28 → ∅, -604.1 KiB
python3.12-ruamel-base: 1.0.0 → ∅, -10.3 KiB
python3.12-ruamel-yaml: 0.18.10 → ∅, -1787.9 KiB
python3.12-ruamel-yaml-clib: 0.2.12 → ∅, -432.8 KiB
python3.12-service-identity: 24.2.0 → ∅, -101.3 KiB
python3.12-setproctitle: 1.3.5 → ∅, -45.9 KiB
python3.12-setuptools: 78.1.1 → ∅, -13431.4 KiB
python3.12-six: 1.17.0 → ∅, -121.1 KiB
python3.12-sortedcontainers: 2.4.0 → ∅, -407.0 KiB
python3.12-tornado: 6.5.1 → ∅, -5865.9 KiB
python3.12-typing-extensions: 4.13.2 → ∅, -526.5 KiB
python3.12-urwid: 2.6.16 → ∅, -3574.9 KiB
python3.12-vdf: 3.4 → ∅, -107.8 KiB
python3.12-wcwidth: 0.2.13 → ∅, -588.0 KiB
python3.12-werkzeug: 3.1.3 → ∅, -2543.0 KiB
python3.12-wsproto: 1.2.0 → ∅, -259.0 KiB
python3.12-zstandard: 0.23.0 → ∅, -2683.4 KiB
python3.13-aioquic: ∅ → 1.2.0, +1400.4 KiB
python3.13-argcomplete: ∅ → 3.6.3, +343.1 KiB
python3.13-argon2-cffi: ∅ → 25.1.0, +111.9 KiB
python3.13-argon2-cffi-bindings: ∅ → 25.1.0, +70.1 KiB
python3.13-asgiref: ∅ → 3.11.1, +234.1 KiB
python3.13-attrs: ∅ → 26.1.0, +647.5 KiB
python3.13-bcrypt: ∅ → 5.0.0, +686.6 KiB
python3.13-blinker: ∅ → 1.9.0, +76.5 KiB
python3.13-brotli: ∅ → 1.2.0, +48.9 KiB
python3.13-certifi: ∅ → 2026.01.04, +481.6 KiB
python3.13-cffi: ∅ → 2.0.0, +1459.6 KiB
python3.13-click: ∅ → 8.3.1, +1256.9 KiB
python3.13-cryptography: ∅ → 48.0.0, +6381.4 KiB
python3.13-dasbus-unstable: ∅ → 11-10-2022, +609.6 KiB
python3.13-dbus-python: ∅ → 1.4.0, +685.3 KiB
python3.13-dnspython: ∅ → 2.8.0, +3888.7 KiB
python3.13-flask: ∅ → 3.1.2, +1077.4 KiB
python3.13-gst-python: ∅ → 1.26.11, +211.5 KiB
python3.13-h11: ∅ → 0.16.0, +270.1 KiB
python3.13-h2: ∅ → 4.3.0, +703.4 KiB
python3.13-hpack: ∅ → 4.1.0, +613.4 KiB
python3.13-hyperframe: ∅ → 6.1.0, +135.7 KiB
python3.13-idna: ∅ → 3.15, +894.5 KiB
python3.13-itsdangerous: ∅ → 2.2.0, +148.0 KiB
python3.13-jinja2: ∅ → 3.1.6, +1827.0 KiB
python3.13-kaitaistruct: ∅ → 0.11, +145.3 KiB
python3.13-ldap3: ∅ → 2.9.1, +6613.3 KiB
python3.13-lz4: ∅ → 4.4.5, +966.0 KiB
python3.13-mako: ∅ → 1.3.10, +1014.5 KiB
python3.13-markdown: ∅ → 3.10.2, +1083.2 KiB
python3.13-markupsafe: ∅ → 3.0.3, +85.5 KiB
python3.13-mitmproxy: ∅ → 12.2.3, +9269.0 KiB
python3.13-mitmproxy-linux: ∅ → 0.12.8, +2543.6 KiB
python3.13-mitmproxy-rs: ∅ → 0.12.8, +8158.1 KiB
python3.13-msgpack: ∅ → 1.1.2, +351.3 KiB
python3.13-packaging: ∅ → 26.1, +1099.0 KiB
python3.13-pillow: ∅ → 12.3.0, +4816.0 KiB
python3.13-psutil: ∅ → 7.2.2, +1164.5 KiB
python3.13-publicsuffix2: ∅ → 2.20191221, +404.2 KiB
python3.13-pyasn1: ∅ → 0.6.3, +1257.8 KiB
python3.13-pyasn1-modules: ∅ → 0.4.2, +2928.3 KiB
python3.13-pycairo: ∅ → 1.29.0, +508.2 KiB
python3.13-pycparser: ∅ → 3.00, +660.1 KiB
python3.13-pycups: ∅ → 2.0.4, +242.3 KiB
python3.13-pycurl: ∅ → 7.46.0, +540.8 KiB
python3.13-pygobject: ∅ → 3.56.3, +1213.4 KiB
python3.13-pylsqpack: ∅ → 0.3.23, +906.7 KiB
python3.13-pyopenssl: ∅ → 26.0.0, +721.8 KiB
python3.13-pyparsing: ∅ → 3.3.2, +1475.6 KiB
python3.13-pyperclip: ∅ → 1.11.0, +93.6 KiB
python3.13-pysmbc: ∅ → 1.0.25.1, +101.7 KiB
python3.13-pyxdg: ∅ → 0.28, +612.7 KiB
python3.13-ruamel-base: ∅ → 1.0.0, +10.3 KiB
python3.13-ruamel-yaml: ∅ → 0.19.1, +1841.2 KiB
python3.13-ruamel-yaml-clib: ∅ → 0.2.15, +379.3 KiB
python3.13-service-identity: ∅ → 24.2.0, +101.7 KiB
python3.13-setproctitle: ∅ → 1.3.7, +48.2 KiB
python3.13-setuptools: ∅ → 80.10.1, +11599.1 KiB
python3.13-sortedcontainers: ∅ → 2.4.0, +390.1 KiB
python3.13-tornado: ∅ → 6.5.7, +5962.5 KiB
python3.13-typing-extensions: ∅ → 4.15.0, +494.6 KiB
python3.13-urwid: ∅ → 3.0.5, +3503.7 KiB
python3.13-vdf: ∅ → 3.4, +109.5 KiB
python3.13-wcwidth: ∅ → 0.6.0, +604.0 KiB
python3.13-werkzeug: ∅ → 3.1.6, +2537.5 KiB
python3.13-wsproto: ∅ → 1.3.2, +264.5 KiB
python3.13-zstandard: ∅ → 0.25.0, +2701.6 KiB
qpdf: 11.10.1 → 12.3.2, +1752.2 KiB
rapidcheck: 0-unstable-2023-12-14 → ∅, -672.9 KiB
rclone: 1.69.1 → 1.75.0, +26270.8 KiB
readline: 8.2p13 → ∅, +50.3 KiB
reload: ε → ∅
rest: 0.9.1 → ∅, -202.3 KiB
restic: 0.18.0 → 0.18.1, +2046.6 KiB
roc-toolkit: +60.0 KiB
rsync: 3.4.1 → 3.4.4, +41.7 KiB
rt5677-firmware: ε → 4.16-10
rtkit: 0.13 → 0.14
rtl8192su-firmware: ∅ → 0-unstable-2016-10-05, +310.7 KiB
rtl8192su-unstable: 2016-10-05 → ∅, -310.7 KiB
rtl8761b-firmware: ε → ∅, -17.0 KiB
rtl8761b-firmware-rtk1395: ∅ → ε, +17.0 KiB
rtmpdump: +13.5 KiB
rygel: 0.44.2 → 45.2, +109.3 KiB
s2n-tls: 1.5.17 → 1.7.6, +22.6 KiB
samba: 4.20.8 → 4.23.10, +2721.3 KiB
sane-backends: 1.3.1 → 1.4.0, +60.9 KiB
sbc: 2.0 → ∅, +8.8 KiB
sbin: ε → ∅
sdl2-compat: 2.32.56 → ∅
sdl3: 3.2.20 → ∅, +5260.5 KiB
sdl3-ttf: ∅ → 3.2.2, +316.6 KiB
seahorse: +13.6 KiB
seatd: 0.9.1 → 0.9.3
security-wrapper-dbus-daemon-launch-helper-x86_64-unknown-linux: ε → ∅, -70.0 KiB
security-wrapper-polkit-agent-helper: 1-x86_64-unknown-linux → ∅, -70.0 KiB
serd: 0.32.4 → ∅
shadow: 4.17.4 → 4.19.4, -83.8 KiB
shared-mime-info: +65.1 KiB
showtime: ∅ → 50.0, +618.9 KiB
simdjson: ∅ → 4.6.4, +7783.4 KiB
simdutf: +3047.8 KiB
simple-scan: 46.0 → 50.0, +375.1 KiB
slang: +60.4 KiB
snapshot: 48.0.1 → 50.0, -1365.6 KiB
sndio: +8.7 KiB
socat: 1.8.0.3 → ∅, +30.0 KiB
sof-firmware: 2025.01.1 → 2025.12.2, +2773.9 KiB
sord: 0.16.18 → ∅
soundtouch: 2.3.3 → ∅
source: -591066.8 KiB
soxr: -8.0 KiB
spandsp: +1031.9 KiB
spdlog: 1.15.2 → 1.17.0, +31.4 KiB
speech-dispatcher: +182.4 KiB
spice-gtk: ∅ → 0.42, +2181.1 KiB
spidermonkey: 128.5.0 → 140.13.0, +5443.8 KiB
sqlite: 3.48.0 → ∅, +8082.3 KiB
sratom: 0.6.18 → ∅
srt: -660.0 KiB
sstp-client-unstable: 2023-03-25 → ∅, -151.6 KiB
steam: ∅ → 1.0.0.85, 1.0.0.85-fhsenv, +12659.5 KiB
steam-fhsenv: ε → ∅, -9991.5 KiB
steam-run: ∅ → 1.0.0.85, 1.0.0.85-fhsenv, +24715.3 KiB
steam-run-fhsenv: ε → ∅, -19603.4 KiB
steam-unwrapped: 1.0.0.82 → 1.0.0.85, +818.8 KiB
stoken: 0.93 → ∅, -438.4 KiB
strace: 6.17 → 7.2, +510.6 KiB
strongswan: 5.9.14 → ∅, -4610.5 KiB
sudo: -92.6 KiB
sushi: 46.0 → 50.0, +105.8 KiB
svox: 2018-02-14 → ∅, -6926.8 KiB
svt-av1: 2.3.0 → ∅, -143.2 KiB
switch: ∅ → ε
switch-to-configuration: -877.6 KiB
system: -223.1 KiB
systemd: 257.10 → ∅, +45077.5 KiB
systemd-generator-environment.json: ∅ → ε
systemd-minimal: 257.10 → ∅, +7982.0 KiB
systemd-minimal-libs: 257.10 → ∅, +4639.9 KiB
taglib: 2.0.2 → 2.2.1, +410.8 KiB
talloc: 2.4.3 → 2.4.4, +19.7 KiB
tbb: 2021.11.0 → ∅, -1935.8 KiB
tcl: +16.5 KiB
tdb: 1.4.13 → 1.4.15
tecla: 48.0.2 → 50.0, +20.6 KiB
tevent: 0.16.2 → 0.17.1
texlive-bin: 2024 → 2025
thin-provisioning-tools: 1.1.0 → 1.3.2, -158.7 KiB
time: 1.9 → 1.10
tinysparql: 3.9.2 → ∅, +107.0 KiB
totem: 43.1 → ∅, -6976.6 KiB
totem-pl-parser: 3.26.6 → 3.26.7, +10.6 KiB
tpm2-tss: ∅ → 4.2.0, -55.6 KiB
tzdata: 2025b → ∅, -13.1 KiB
udev: +51.6 KiB
udisks: 2.10.2 → 2.11.2, +2119.7 KiB
umockdev: 0.19.1 → 0.19.3
unbound: 1.24.1 → 1.26.0, +62.1 KiB
unifont: 16.0.03 → 17.0.04
unit-audit.service: ε → ∅
unit-autovt: .service → ∅
unit-container: .service → ∅
unit-dbus-broker.service: ∅ → ε
unit-filter-chain.service: ∅ → ε
unit-gcr-ssh-agent.service: ∅ → ε
unit-gcr-ssh-agent.socket: ∅ → ε
unit-getty.target: ∅ → ε
unit-gnome-session-monitor.service: ∅ → ε
unit-graphical-session-pre.target: ∅ → ε
unit-lastlog2-import.service: ∅ → ε
unit-linger-users.service: ∅ → ε
unit-modprobe: ∅ → .service
unit-mount-pstore.service: ε → ∅
unit-network-setup.service: ε → ∅
unit-network.target: ∅ → ε
unit-networking-scripted.target: ∅ → ε
unit-polkit-agent-helper: ∅ → .service
unit-polkit-agent-helper.socket: ∅ → ε
unit-post-boot.service: ∅ → ε
unit-post-resume.service: ε → ∅
unit-post-resume.target: ε → ∅
unit-pre-sleep.service: ε → ∅
unit-save-hwclock.service: ε → ∅
unit-script-container_: ε → ∅
unit-script-container_-post: ε → ∅
unit-script-container_-pre: ε → ∅
unit-script-linger-users: ∅ → ε
unit-script-network-local-commands: ∅ → ε
unit-script-network-setup: ε → ∅
unit-script-post-boot: ∅ → ε
unit-script-post-boot-pre: ∅ → ε
unit-script-post-resume: ε → ∅
unit-script-pre-sleep: ε → ∅
unit-script-sleep-actions: ∅ → ε
unit-script-sleep-actions-pre: ∅ → ε
unit-script-systemd-timesyncd-pre: ε → ∅
unit-script-wpa_supplicant: ∅ → ε
unit-sleep-actions.service: ∅ → ε
unit-systemd-hostnamed.service: ∅ → ε
unit-systemd-localed.service: ∅ → ε
unit-systemd-tmpfiles-clean.timer: ∅ → ε
unit-systemd-udev-settle.service: ε → ∅
unit-wpa_supplicant.service: ∅ → ε
unrar-free: ∅ → 0.3.3, +34.2 KiB
unzip: +12.2 KiB
upower: 1.90.6 → 1.91.3, +71.0 KiB
uriparser: 0.9.8 → 1.0.2, +71.8 KiB
usbredir: +133.4 KiB
usbutils: ∅ → 019, +317.7 KiB
util-linux: 2.41.1 → ∅, +1950.0 KiB
util-linux-minimal: 2.41.1 → ∅, +874.9 KiB
uvwasi: +238.0 KiB
v4l-utils: 1.24.1 → ∅, -259.8 KiB
vid.stab: +1110.9 KiB
vid.stab-unstable: 2022-05-30 → ∅, -339.5 KiB
virtiofsd: 1.13.2 → 1.13.3, -188.6 KiB
vpnc-scripts-unstable: 2023-01-03 → ∅, -80.9 KiB
vpnc-unstable: 2024-12-20 → ∅, -242.4 KiB
vte: 0.80.1 → 0.84.1, -1078.8 KiB
vulkan-headers: 1.4.313.0 → ∅, -31647.7 KiB
vulkan-loader: 1.4.313.0 → ∅, +88.0 KiB
w3m: 0.5.3+git20230121 → 0.5.6, +239.5 KiB
wavpack: 5.8.1 → ∅, +21.4 KiB
wayland: 1.23.1 → ∅, +485.2 KiB
wayland-protocols: ∅ → 1.48, +1037.0 KiB
webkitgtk: 2.50.4+abi=4.1, 2.50.4+abi=6.0 → 2.52.5+abi=4.1, 2.52.5+abi=6.0, +13628.0 KiB
webp-pixbuf-loader: 0.2.6 → 0.2.7
webrtc-audio-processing: +726.3 KiB
which: -9.4 KiB
wildmidi: +12.2 KiB
winetricks: 20250102 → 20260125, +42.0 KiB
wireless-regdb: 2025.02.20 → 2026.05.30
wireplumber: 0.5.10 → 0.5.14, +343.4 KiB
woff2: 1.0.2 → ∅, -150.7 KiB
wpa_supplicant: +61.0 KiB
x265: +1711.0 KiB
xauth: 1.1.4 → 1.1.5
xcb-util: 0.4.1 → ∅, -35.8 KiB
xcb-util-image: 0.4.1 → ∅, -27.1 KiB
xcb-util-keysyms: 0.4.1 → ∅, -35.6 KiB
xcb-util-renderutil: 0.3.10 → ∅, -28.1 KiB
xcb-util-wm: 0.4.2 → ∅, -111.8 KiB
xdg-dbus-proxy: 0.1.6 → 0.1.7
xdg-desktop-portal: 1.20.3 → 1.20.4, +186.7 KiB
xdg-desktop-portal-gnome: 48.0 → 50.0, +112.2 KiB
xdg-desktop-portal-gtk: +32.5 KiB
xdg-user-dirs: 0.18 → ∅, +93.0 KiB
xdg-user-dirs-gtk: 0.14 → 0.16
xfsprogs: 6.13.0 → 6.19.0, +291.4 KiB
xgcc: 14.3.0 → ∅, -8.2 KiB
xkbcomp: 1.4.7 → 1.5.0
xkeyboard-config: 2.44 → ∅, +7493.5 KiB
xl2tpd: 1.3.19 → ∅, -169.7 KiB
xorg-server: 21.1.20 → 21.1.24, -54.8 KiB
xorgproto: +1675.0 KiB
xprop: 1.2.7 → 1.2.8
xrandr: 1.5.2 → 1.5.4
xterm: 397 → 410, +101.0 KiB
xvidcore: -12.0 KiB
xwayland: 24.1.9 → 24.1.13, +193.5 KiB
xxHash: 0.8.3 → ∅, -393.8 KiB
xxhash: ∅ → 0.8.3, +413.9 KiB
xz: 5.8.1 → ∅, -106.3 KiB
yad: +29.7 KiB
yelp: 42.2 → 49.1, +32.6 KiB
yelp-xsl: 42.4 → 49.0
zenity: 4.1.90 → ∅, +72.7 KiB
zimg: 3.0.5 → ∅, -659.9 KiB
zix: 0.4.2 → ∅
zlib: 1.3.1 → ∅, +294.3 KiB
zlib-ng: 2.2.4 → 2.3.3, +24.9 KiB
zstd: -148.7 KiB
zvbi: +40.7 KiB
zxing-cpp: -35.2 KiB
```

## Files touched

- `flake.nix` — `nixpkgs-host.url` rev (one line).
- `flake.lock` — `nixpkgs-host`, `nixpkgs_2` (gaming's nixpkgs) and `gaming`
  nodes.
- `hosts/core/default.nix` — the gnome/gdm rename (two lines moved).
- `docs/reviews/2026-09-05-release-upgrade-26.05.md` — this record.
