# Gaming flake — design (2026-09-02, rev 2)

**Decision basis (operator, 2026-09-02 evening):** separate repo
`~/flakes/gaming`, always-on module, nixpkgs-only, with every privileged or
network-opening behaviour off unless a named switch is flipped. Research:
docs/research-2026-09-02-gaming-stack.md. Rev 2 folds in the adversarial
review: gamemode's renice wrapper, PipeWire config shape, unfree in checks,
module-embedded assertions, one negative test per assertion.

**Scope note on the brief's invariants (needs the operator's sign-off at
the spec gate):** brief §3 invariant 3 ("every byte leaving the machine
passes the chokepoint") is read here as binding the AI-agent harnesses the
brief is about, not the operator's own desktop software — Firefox, the
Proton apps and the desktop app already run on `core` outside the broker.
Steam is treated the same way: operator software, direct egress. If the
operator wants Steam brokered later, the route is a broker instance plus a
netns-joined launcher, a separate design.

## Goal

Steam with Proton (incl. Proton-GE), gamescope, gamemode, MangoHud,
controllers, optional non-Steam launchers and low-latency audio on `core`,
enabled by one option. No firewall opening and no capability/setuid
wrapper unless its named switch is on. Reusable on other hosts (Phase 9
node2/node3 — revisit egress posture there) as a pinned flake input.

## Non-goals

Sandboxing Steam beyond what it does itself (its FHS environment is
compatibility, not containment — README says so); a dedicated gaming
user; a boot specialisation; nix-gaming as an input (documented option for
title-specific packages only).

## Repository

`~/flakes/gaming` — a fresh local git repo shaped like nixos-agent-env:
`flake.nix` (input `nixpkgs` pinned to the SAME rev as nixos-agent-env's
`nixpkgs-host`, ac62194c…), `nixosModules/gaming.nix`, `checks/`
(including `checks/eval-harness.nix`, a copy of the stub nixos-agent-env
uses for `checks.cowork-eval`: `fileSystems."/"`, `boot.loader.grub.enable
= false`, `system.stateVersion`, plus `nixpkgs.config.allowUnfree = true`
because `steam` is unfree — proton-ge-bin is BSD-3), `tests/`,
`githooks/` (copied pre-commit lint + pre-push allowlist; `core.hooksPath`
set by the devShell), `treefmt.toml`, `README.md`, `docs/OPERATIONS.md`,
`docs/decisions/`. Lint gate: nixfmt, shfmt, shellcheck, statix, deadnix.

The module never imports the flake's own nixpkgs: it uses the consuming
host's `pkgs`. The flake's `nixpkgs` input exists for checks and the
devShell only.

## Module `programs.gaming`

| option | default | effect |
|---|---|---|
| `enable` | false | `programs.steam.enable` (which itself forces `hardware.graphics.enable32Bit` and `hardware.steam-hardware.enable` — documented) |
| `protonGE.enable` | true | `programs.steam.extraCompatPackages = [ pkgs.proton-ge-bin ]` (GE-Proton10-25 at the pin) |
| `protontricks.enable` | true | `programs.steam.protontricks.enable` |
| `gamescope.enable` | true | `programs.gamescope.enable` |
| `gamescope.capSysNice` | false | `programs.gamescope.capSysNice` — installs a `cap_sys_nice` wrapper; the module emits a build-time warning naming the wrapper when set |
| `gamescope.session.enable` | false | `programs.steam.gamescopeSession.enable`; requires `gamescope.enable` (assertion) |
| `gamemode.enable` | true | `programs.gamemode.enable` **with `programs.gamemode.enableRenice = false`** — the pinned gamemode module defaults `enableRenice` to true, which installs a `CAP_SYS_NICE` wrapper on gamemoded unconditionally (nixos/modules/programs/gamemode.nix at the pin). Off here by default |
| `gamemode.renice` | false | `programs.gamemode.enableRenice = true` (named switch, README explains the wrapper) |
| `gamemode.settings` | {} | passthrough to `programs.gamemode.settings` |
| `mangohud.enable` | true | `pkgs.mangohud` in `programs.steam.extraPackages` and systemPackages |
| `controllers.xone` | false | `hardware.xone.enable` (also enables `hardware.xpad-noone` and blacklists in-tree `xpad` — documented); out-of-tree module, `meta.broken = false` at the pin |
| `controllers.xpadneo` | false | `hardware.xpadneo.enable`; `meta.broken = false` at the pin |
| `launchers.heroic` / `.lutris` / `.bottles` | false | each adds its package to systemPackages |
| `firewall.remotePlay` / `.localNetworkGameTransfers` / `.dedicatedServer` | false | pass-through to `programs.steam.*.openFirewall` |
| `lowLatencyAudio.enable` | false | `services.pipewire.extraConfig.pipewire."92-gaming-low-latency" = { "context.properties" = { "default.clock.quantum" = 256; "default.clock.min-quantum" = 256; }; }` (the pinned option is `attrsOf json`, values nested under a section name) |
| `extraPackages` | [] | appended to `programs.steam.extraPackages` |

Module-embedded assertions (build fails; brief §8 "prefer failing the
build"):

1. `gamescope.session.enable` → `gamescope.enable`.
2. `enable` → `config.hardware.graphics.enable` (guards a host that force-disables it).
3. Unless the matching `firewall.*` switch is on, none of the Steam ports
   (TCP 27015, 27036, 27040; UDP 27015, 27031-27036) appear in
   `config.networking.firewall.allowedTCPPorts`/`allowedUDPPorts`/ranges.
4. `config.security.wrappers ? gamescope` → `gamescope.capSysNice`.
5. `config.programs.gamemode.enableRenice` → `gamemode.renice`.
6. `lowLatencyAudio.enable` → `config.services.pipewire.enable`.

(The controllers/kernel assertion from rev 1 is dropped: the upstream
modules carry their own kernel guards.)

## Host wiring (nixos-agent-env, separate task after the flake exists)

`inputs.gaming.url = "git+file:///home/dalhaka/flakes/gaming?ref=main"`
(flake.lock records the exact rev); `nixosConfigurations.core` imports
`gaming.nixosModules.default`; `hosts/core/gaming.nix` sets
`programs.gaming.enable = true` (v0: defaults; controllers and launchers
off until asked). Backup: add `/home/dalhaka/flakes` to the restic paths.
`hosts/core/graphics.nix` already has `hardware.nvidia.open = true` +
modesetting (required for Blackwell; verified).

## Testing

- `checks.gaming-eval` (defaults): evaluates on the harness; asserts no
  Steam port in the firewall lists, no `security.wrappers.gamescope`,
  `programs.gamemode.enableRenice == false`, proton-ge-bin in
  `extraCompatPackages`.
- `checks.gaming-eval-everything` (all switches on): firewall contains
  exactly the Steam ports; `security.wrappers.gamescope` exists;
  `enableRenice == true`; the rendered PipeWire config file contains
  `default.clock.quantum` under `context.properties`.
- `checks.gaming-eval-session-no-cap` (session on, `capSysNice` off):
  no `security.wrappers.gamescope` — the control for assertion 4.
- One custom-output negative check per assertion 1-6
  (`checks.gaming-assertion-negative-<n>`), each failing with the
  module's message.
- `checks.lint`.
- Operator acceptance `tests/acceptance/gaming.sh` (GUI): `steam` starts
  (operator judgment); `gamemoded -s`; `gamescope --version`; `mangohud
  --version`; `ss -ltnu` shows no new listeners; `sudo nft list ruleset |
  grep -E '2703[1-6]|27015|27040'` empty; a Proton-GE entry in Steam's
  compatibility list (operator judgment); gamescope smoke test of one game
  window (the research flags possible coredumps with upscaling + explicit
  sync on NVIDIA ≥ 555 — this test is the measurement).

## README notes

Steam is a proprietary, self-updating client running as the operator with
full home-directory access and direct network egress; the module adds no
privilege and opens nothing inbound. gamescope on NVIDIA: smoke-test
upscaling before daily reliance. Stronger separation would be a separate
login seat, not socket sharing.

## Verify-first items for the plan

1. `programs.gamemode` options at the pin: `enable`, `enableRenice`,
   `settings` (research confirmed `enableRenice` default true).
2. `git+file://…?ref=main` lock entry shape on first `nix flake lock`.
3. Rendering of `services.pipewire.extraConfig.pipewire` to a file path
   the eval check can read.
