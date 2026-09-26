---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run pb1, task PB1 — APPROVED

## Summary

PB1 moves `nixpkgs-host` from `ac62194c3917d5f474c1a844b6fd6da2db95077d`
(NixOS 25.05, 2026-01-02 — what `/run/current-system` runs today) to
`a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` (NixOS 26.05.20260903), and re-locks
`gaming` to PB0's merged `main` `a4088d7`. I reproduced every claim by ref in a
throwaway clone: one commit on base `b01bd08`, five files, subject byte-identical
to the plan, trailer present, nothing under brief §3 touched. `nix flake check -L`
is green — 38/38, exit 0, 101 s. The toplevel builds and the closure diff I
produced is **byte-identical** to the 1,104 lines the review doc records verbatim.

Three things the implementer's record does not say, which I measured myself:

1. **Only one check actually moved.** All five VM tests (`integration`,
   `helm-vm`, `helm-control-vm`, `lane-vm`, `proton-backup-vm`) have
   **derivation paths byte-identical to base** — they build against the
   unchanged tools `nixpkgs` pin, not `nixpkgs-host`, which is referenced at
   exactly one site (`flake.nix:629`). Their store outputs were built between
   2026-09-03 and 15:56 today, i.e. *before* this task's 16:08 commit. They are
   green, but they carry **no 26.05 signal**. The real 26.05 evidence is
   `host-core` (builds the 26.05 toplevel), `core-gaming-wiring` (evaluates the
   26.05 config plus the lock-equality assertion) and `lint`.
2. **I closed the one gap that mattered.** The host will run mitmproxy
   **12.2.3 on python 3.13.15**; the broker VM test exercises **12.1.1**. I
   rebuilt the broker policy addon's suite against the host pin: **56/56 pass**,
   and the internal API `mitmproxy.net.http.http1.expected_http_body_size` that
   `pkgs/broker/policy.py` imports still resolves. Egress control is not
   silently at risk.
3. **The upgrade shrinks the tools/host skew rather than widening it.** Host
   node goes 22.20.0 → 24.19.0, exactly the version the checks already use;
   host python goes 3.12.12 → 3.13.15, moving *toward* the 3.14.7 the unit
   tests run on. mitmproxy is the only place the host ends up ahead of the
   tested version, and I measured that one green.

The pin move is sound and the switch is safe on this evidence. Findings below
are corrections to the record, not defects in the change.

## Checks

`nix flake check -L` in the clone (fresh `XDG_CACHE_HOME`, so evals ran for real):
**exit 0, 38 checks, 101 s wall**. Per-check wall time is not broken out by
`nix flake check`; the aggregate is a store walk — every derivation was already
realised, so this verifies that these exact derivations have successful outputs,
it does not re-execute the builders. Column 3 records whether the derivation
changed at all relative to base `b01bd08`.

| check | verdict | drv vs base |
|---|---|---|
| `host-core` | PASS | **CHANGED** — `nixos-system-core-26.05.20260903.a5cc6f2` |
| `lint` | PASS | **CHANGED** (source-derived; tree contents moved) |
| `core-gaming-wiring` | PASS | same drv (constant marker; the work is the eval — see Findings) |
| `integration` (broker VM) | PASS | **same drv as base** — built 2026-09-05 09:15 |
| `helm-vm` (VM) | PASS | **same drv as base** — built 2026-09-05 15:56 |
| `helm-control-vm` (VM) | PASS | **same drv as base** — built 2026-09-05 15:56 |
| `lane-vm` (VM) | PASS | **same drv as base** — built 2026-09-05 10:23 |
| `proton-backup-vm` (VM) | PASS | **same drv as base** — built 2026-09-03 09:22 |
| `unit`, `addon`, `factory-unit`, `helm-unit`, `ledger-unit`, `lane-unit`, `lane-polkit-unit`, `evidence-unit` | PASS | unchanged |
| `module-eval`, `helm-eval`, `helm-control-eval`, `lane-eval`, `cowork-eval`, `evidence-eval`, `proton-backup-eval` | PASS | unchanged |
| `assertion-positive`, `assertion-negative`, `helm-assertion-negative`, `lane-assertion-negative`, `managed-settings-assertion-negative` | PASS | unchanged |
| `helm-control-assertion-negative-{profiles,enable,agentunit,workspace}` | PASS | unchanged |
| `managed-settings`, `managed-settings-user-scope` | PASS | unchanged |
| `manifests-validate`, `claims-validate` | PASS | unchanged |
| `core-backup-wiring`, `proton-drive-cli` | PASS | unchanged |

Extra evidence I produced (not in the implementer's record):

| probe | result |
|---|---|
| broker addon suite against **host-pin** python 3.13.15 + mitmproxy 12.2.3 | **56/56 PASS**; `expected_http_body_size` import OK |
| `nix build …system.build.toplevel` | exit 0, 18 s → `/nix/store/h1v22m8s…-nixos-system-core-26.05.20260903.a5cc6f2` (= the `host-core` drv's output) |
| my closure diff vs the doc's verbatim block | **1,104 lines, byte-identical** |
| implementer's recorded toplevel vs the committed tree's toplevel | `diff-closures` between them is **empty** (closures identical) |
| base vs HEAD `system.nixos.release` | `"25.05"` vs `"26.05"` |
| `hardware.nvidia.open` / package, base and gaming specialisation | `true` / `595.71.05` in both; kernel `6.18.49` |

Commit shape: one commit `3f98468` on base `b01bd08`; files exactly
`flake.nix`, `flake.lock`, `hosts/core/default.nix`,
`docs/reviews/2026-09-05-release-upgrade-26.05.md`, `docs/OPERATIONS.md`
(regenerated `tasks:` block only); subject byte-identical to the plan
(verified with `od -c`); `Co-Authored-By` trailer present.
`flake.nix`: only the `nixpkgs-host.url` rev. `flake.lock`: only the `gaming`,
`nixpkgs-host` and `nixpkgs_2` (gaming's transitive nixpkgs) nodes — `gaming`
= `a4088d7e0146839ea267f5c9ea660d0ea03d9eb8`, which I confirmed equals
`git -C ~/flakes/gaming rev-parse main`. `hosts/core/default.nix`: only the two
renamed options, correctly relocated into the enclosing `services = { … }`
block (`flake.nix:70`), and I confirmed they take effect —
`services.displayManager.gdm.enable` and `services.desktopManager.gnome.enable`
both evaluate `true` and `systemd.services.display-manager` is present.
**No brief §3 file is touched** (no `nixosModules/basketStore.nix`,
`egressBroker.nix`, `claudeManagedSettings.nix`, no firewall change).

## Closure diff by category

1,104 lines; 389 lines with `→ ∅`, 214 with `∅ →`. **Read `∅` carefully**: this
`diff-closures` prints the *set difference* of versions per name, so
`X: 1.2 → ∅` means "version 1.2 left and every surviving version of X was
already present in the old closure" — **not** "X was removed". I checked the
real closures (2,455 → 2,563 paths) rather than trusting the arrows.

- **Kernel / firmware.** `linux 6.12.63 → 6.18.49` (+15.8 MiB, and again for
  `initrd-linux`), `linux-headers 6.12.7 → 6.18.7`,
  `linux-firmware 20251125 → 20260810` (+60.7 MiB). **Reboot required.**
- **NVIDIA.** `nvidia-open 6.12.63-570.195.03 → 595.71.05-6.18.49`,
  `nvidia-x11 570.195.03 → 595.71.05` (+32.0 MiB), `nvidia-settings` likewise,
  `nvidia-vaapi-driver 0.0.13 → 0.0.17`. `hardware.nvidia.open = true` holds in
  both the base profile and the gaming specialisation — the RTX 5090 open-module
  requirement is satisfied, and 595 is a full branch newer than the 570 running
  now. `mesa 25.0.7 → 26.1.8` (+227.3 MiB).
- **glibc / toolchain.** `glibc 2.40-66 → 2.42-67` (verified present as
  `glibc-2.42-67`; the `→ ∅` line is the set-difference artifact above),
  `getent-glibc 2.40-66 → 2.42-67`, `glibc-locales`, `glibc-multi` the same.
- **systemd.** `257.10 → 260.2` (260.2 was already in the old closure via the
  other pins, hence the `∅`). `dbus-broker 37` is genuinely **new** — 26.05
  makes it the default bus implementation — but **`dbus` itself is not gone**:
  `dbus-1.16.2` is in both closures.
- **Broker / python.** `python3 3.12.12 → 3.13.15`; the whole `python3.12-*`
  set is replaced by `python3.13-*`; `python3.12-mitmproxy 12.1.1` →
  `python3.13-mitmproxy 12.2.3` (+ `mitmproxy-rs`/`-linux 0.12.8`). Measured
  green against the addon suite (above).
- **node / electron.** `nodejs 22.20.0 → 24.19.0` (plus a new `nodejs-slim
  24.19.0`), `electron 37.10.2 → 43.1.0`. `claude-code-2.1.258` and
  `dsh-0.1.2-rc.1` are **byte-identical in both closures** — they come from the
  `llm-agents` pin, which deliberately does not follow `nixpkgs-host`, so the
  seat tooling is untouched by this move.
- **Desktop.** `gdm 48.0 → 50.2`, `gnome-shell 48.2 → 50.4`, `mutter 48.3.1 →
  50.4`, `gnome-session 48.0 → 50.1`, `xorg-server 21.1.20 → 21.1.24`,
  `gtk4 4.18.6 → 4.22.4`. See "For the switch".
- **Security-relevant, unchanged or improved.** `age` does not appear in the
  diff at all (`age-1.3.1` both sides) — **basket encryption is untouched**.
  `nftables 1.1.3 → 1.1.6` (broker's egress enforcement),
  `pcsclite-with-polkit 2.3.0 → 2.4.1` (YubiKey path), `restic 0.18.0 → 0.18.1`.
- **Gaming specialisation intact.** `/specialisation/gaming` exists in both
  toplevels; `steam` → `steam-1.0.0.85` (a *pname* change, not a removal),
  `proton-ge-bin GE-Proton10-25 → GE-Proton11-1`, `protontricks 1.12.1 → 1.14.1`.
- **Genuine removals, checked against the repo.** `nixos-container`,
  `net-tools`, `command-not-found`, `openvpn`/`openconnect`/`vpnc`/`l2tp`/
  `sstp`/`fortisslvpn` NetworkManager plugins, `totem`, `geary`, `file-roller`.
  I grepped `hosts/`, `nixosModules/`, `pkgs/`, `tools/`, `lib/` for
  `ifconfig`, `netstat`, `net-tools`, `nixos-container`, `openvpn`,
  `command-not-found`, `arp` — **no references**. (`route` matches are the
  factory router, not the binary.)
- **Renames that look like removals.** The X libraries were lowercased
  (`libX11-1.8.12` → `libx11-1.8.13`, and the same for `libXext`, `libSM`,
  `libICE`, …) — present, not dropped. `nixos-rebuild` → **`nixos-rebuild-ng-26.05`**,
  and `/sw/bin/nixos-rebuild` still resolves in the new system-path.
- **No version regressions.** I scanned all 323 real version transitions for a
  decreasing major component: none.

## Drift

The full warning set from my own `nix flake check -L` run, with a fresh eval
cache so nothing was suppressed:

- `evaluation warning: nixfmt-rfc-style is now the same as pkgs.nixfmt which
  should be used instead.` — from `lintTools` in `flake.nix`. This is on the
  **tools** pin, not the release move. Recorded, not fixed; `lint` is green.
- `warning: unknown flake output 'phase3NegativeDemo'` — pre-existing, by
  design (the negative demo is deliberately not a `nixosConfiguration`).
- `install-info: warning: no info dir entry … gawknotes.info` — build noise.

**No renamed-option warning remains** — the implementer's claim holds, and it is
a meaningful negative because the same code path *does* emit those warnings: my
mutation (below) produced them verbatim. So there are no other renamed or
deprecated options this configuration still uses.

Upstream drift reported, not adapted to, per CLAUDE.md:

- `nixos-rebuild` is now `nixos-rebuild-ng` at 26.05 (Python rewrite is the
  default). No action needed; the `nixos-rebuild` command still exists.
- `dbus-broker` becomes the default system bus implementation.
- `boot.enableContainers` appears to default off (`nixos-container` gone).
  Nothing here uses NixOS containers.
- `hosts/core/graphics.nix` pins `hardware.nvidia.package =
  config.boot.kernelPackages.nvidiaPackages.latest`, a *moving* selector that
  resolves to **595.71.05** at this pin, while
  `docs/decisions/2026-09-04-…-driver` names **595.99.02** as today's
  nvidia.com production row. Different mechanism, pre-existing config choice,
  **out of scope for PB1** — flagged for the board, not for this task.

## Red before green

- **Release actually moves.** `nix eval .#nixosConfigurations.core.config.system.nixos.release`
  → `"25.05"` on base `b01bd08` (and `system.nixos.version` = `25.05.20260102.ac62194`,
  matching the live `/run/current-system/nixos-version`), `"26.05"` on HEAD.
  The `host-core` derivation name changes accordingly:
  `nixos-system-core-25.05.20260102.ac62194.drv` →
  `nixos-system-core-26.05.20260903.a5cc6f2.drv`.
- **Mutation — and it falsifies the implementer's framing.** I reverted
  `hosts/core/default.nix` to its base form (the two options back under
  `services.xserver`) in a detached worktree and evaluated the toplevel. It
  **does not fail**. It emits:

  ```
  evaluation warning: The option `services.xserver.desktopManager.gnome.enable' … has been renamed to `services.desktopManager.gnome.enable'.
  evaluation warning: The option `services.xserver.displayManager.gdm.enable' … has been renamed to `services.displayManager.gdm.enable'.
  ```

  and then evaluates a valid toplevel derivation, exit 0. So the fix was **not
  forced** — 26.05 still ships the `mkRenamedOptionModule` aliases. The
  mutation is still load-bearing in the useful direction: it proves the two
  target option paths are genuinely the 26.05 names (nixpkgs itself names them
  in the rename message), and it proves warnings surface on this path, which is
  what makes their absence on HEAD meaningful. The edit is correct and worth
  keeping — the aliases are scheduled for removal — it just was not compelled.

## For the switch

**The change is safe to switch on this evidence.** Operator steps:

1. **Prefer `boot` + reboot over `switch`.** The kernel moves 6.12.63 → 6.18.49
   and the NVIDIA driver 570.195.03 → 595.71.05. A plain `switch` activates the
   new userspace NVIDIA libraries while the **running kernel is still 6.12.63**,
   whose loaded `nvidia-open` module is the 570 one — GL/CUDA applications can
   break until reboot. Recommended:

   ```
   sudo nixos-rebuild boot --flake ~/nixos-agent-env#core
   sudo reboot
   ```

   If you use `switch` instead, reboot promptly afterwards.
2. **You will be logged out.** GDM 48.0 → 50.2, gnome-shell 48.2 → 50.4,
   mutter 48.3.1 → 50.4, and dbus → dbus-broker. On `switch`, the
   `display-manager` unit restarts and the graphical session is killed — the
   desktop app's Code tab and anything unsaved goes with it. Another reason to
   use `boot` and reboot at a moment you choose.
3. **Rollback.** Live is **generation 42** (`system-42-link`,
   `25.05.20260102.ac62194`). The switch creates **generation 43**; the rollback
   target is **generation 42**. `systemd-boot` with no `configurationLimit` is
   configured, so 42 stays in the boot menu — pick it there if 26.05 misbehaves,
   or `sudo nixos-rebuild switch --rollback`.
4. **Nothing will build.** Everything is already in the store; my toplevel build
   took 18 s. The integration commit will change the source hash and therefore
   the toplevel's store path, but I verified that a path change of exactly this
   kind leaves the **closure identical**, so the switch remains a store walk plus
   activation.
5. **After the reboot, verify:**
   - `nixos-version` → `26.05.20260903.a5cc6f2`
   - `nvidia-smi` → driver `595.71.05`, GPU detected (open module, kernel 6.18.49)
   - `basket doctor` (host invariants; `age` is unchanged, so no surprises expected)
   - the broker: allowlist behaviour and a fresh line in
     `/var/lib/egress-broker/openrouter/audit.jsonl`. This is the one subsystem
     whose *runtime* is not VM-tested at 26.05 (see Findings 1); its policy addon
     is measured green on the new mitmproxy, but a live smoke is cheap insurance.
   - user timers: a switch does not start newly enabled *user* timers in an
     already-logged-in session — after a reboot and fresh login the Proton Drive
     mirror timer comes up normally.
6. `nixos-rebuild` on the host is `nixos-rebuild-ng` from now on. Same command,
   different implementation.

## Findings

1. **MINOR — the record does not name what the VM tests cover.** The commit
   body ("all 38 checks pass, including the five NixOS VM tests") and the doc's
   Summary are literally true but leave the operator to infer that the five VM
   tests validate 26.05. They do not: their derivations are byte-identical to
   base, they build against the unchanged tools pin, and their outputs predate
   this task by hours to two days. `docs/decisions/2026-09-03-test-based-reality-amendments.md`
   requires a proxy measurement to name what it stands in for and the gap; this
   one does not. Corrected here rather than sent back, and the gap that actually
   mattered is now measured (Finding 2).
2. **MINOR, resolved by this gate — broker at the host pin.** The host will run
   mitmproxy 12.2.3 on python 3.13.15; every check runs 12.1.1. I rebuilt the
   broker policy addon's suite against `nixpkgs-host`: **56/56 pass**, including
   the internal `mitmproxy.net.http.http1.expected_http_body_size` import that
   `policy.py` depends on. Follow-up worth considering: a `broker-addon-hostpin`
   check so this is not re-discovered by hand at the next release move.
3. **MINOR — "forced" is the wrong word.** The commit body and the doc's
   Summary say "The release forced exactly one minimal module change." My
   mutation shows the old option paths still evaluate at 26.05 (warnings only,
   valid toplevel, exit 0). The doc's own Drift section states this correctly
   ("nixpkgs still ships `mkRenamedOptionModule` aliases … the check was green
   before the edit"), so the record contradicts itself rather than hides the
   truth. The edit is correct and should stay.
4. **MINOR — two closure-diff glosses misread `∅`.** The doc says dbus
   `1.14.10 → ∅` is "replaced by dbus-broker 37" and openssl `3.4.3 → ∅` is
   "superseded at a newer version under a different name; the old 3.4.3 path is
   gone". Neither package is removed: `dbus-1.16.2` and `openssl-3.6.3` are in
   both closures under the same names. `∅` here is a set-difference artifact,
   which is also why the size deltas on those lines are *positive*. Same
   artifact explains the `glibc`, `systemd`, `linux-pam` and `gtk4` `∅` lines.
5. **INFORMATIONAL — the doc's toplevel path is not the committed tree's.** The
   doc records `/nix/store/nxpb7h4j…`; the committed tree produces
   `/nix/store/h1v22m8s…`. Unavoidable — the doc is inside the tree it measures.
   I confirmed `diff-closures` between the two is **empty**, so the verbatim
   1,104-line block is trustworthy for the committed tree.
6. **INFORMATIONAL — `core-gaming-wiring`'s derivation is a constant marker**
   (`runCommand … "touch $out"`), so it is identical at base and HEAD. It is
   **not** vacuous: the whole assertion chain, including
   `gamingNixpkgsRev != hostNixpkgsRev`, runs at *eval* time and `nix flake
   check` forces it. I confirmed it evaluates on HEAD, which is a real proof
   that the gaming lock and the host pin are both `a5cc6f2` and that the gaming
   specialisation still evaluates at 26.05.
7. **INFORMATIONAL — skew moves the right way.** Host node 22.20.0 → 24.19.0
   equals the tools pin exactly; host python 3.12.12 → 3.13.15 moves toward the
   3.14.7 the unit tests run on. The 26.05 host is *better* covered by the
   existing checks than the 25.05 host was, mitmproxy aside.
8. **INFORMATIONAL — NVIDIA selector.** `nvidiaPackages.latest` resolves to
   595.71.05 here, while the driver decision addendum names 595.99.02 as
   today's production row. Out of scope for PB1; a board item if the operator
   wants the production row pinned rather than nixpkgs' `latest`.

## Deviations

- The gate procedure asked me to prove the two option renames were forced by
  reverting them and watching `host-core` fail. It does not fail — it warns.
  I report the falsification rather than the expected result (Finding 3, Red
  before green).
- The procedure asked me to `nix eval github:NixOS/nixpkgs/a5cc6f2…#lib.version`
  as a smoke test for the 26.05 option names. I did not need it: the new
  nixpkgs' own `mkRenamedOptionModule` messages, produced by my mutation, name
  both target paths verbatim — stronger evidence than a version string, and it
  needs no network fetch.
- I added one measurement the task did not ask for (the broker addon suite
  against `nixpkgs-host`) because the check inventory left the host's mitmproxy
  untested and the broker is a brief §3 invariant.
- Nothing was written outside my throwaway clone, its two worktrees, the
  scratchpad cache and this file. The implementer's workspace was not touched,
  no commit was made, and no switch was performed.
