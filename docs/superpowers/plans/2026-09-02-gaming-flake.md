# Gaming Flake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Executor: `tools/factory/dark-factory.js` from nixos-agent-env with `bootstrap: true`, `repo: /home/dalhaka/flakes/gaming`.

**Goal:** A standalone flake `~/flakes/gaming` exporting `nixosModules.default` (`programs.gaming`) that turns on Steam/Proton-GE/gamescope/gamemode/MangoHud/controllers/launchers/low-latency audio with every privileged or inbound-network behaviour off unless a named switch is on, proven by eval checks and build-time assertions.

**Architecture:** One NixOS module file plus a shared eval harness; every property the spec promises is either a module assertion (fails the build) or an eval check (fails `nix flake check`). No extra flake inputs; the module uses the consuming host's `pkgs`.

**Tech Stack:** Nix flakes, NixOS module system, nixpkgs at `ac62194c3917d5f474c1a844b6fd6da2db95077d` (`programs.steam`, `programs.gamescope`, `programs.gamemode`, `services.pipewire.extraConfig`, `hardware.xone`, `hardware.xpadneo`), lint gate copied from nixos-agent-env (treefmt/nixfmt/shfmt/shellcheck/statix/deadnix).

**Spec:** `/home/dalhaka/nixos-agent-env/docs/superpowers/specs/2026-09-02-gaming-flake-design.md` (rev 2). Read it first. The decision doc `docs/decisions/2026-09-02-invariants-bind-agents-not-operator-apps.md` there explains why Steam is not brokered.

## Global Constraints

- New repo at `/home/dalhaka/flakes/gaming` (plain git, branch `main`, no remote; the pre-push hook refuses every remote — copy it verbatim from nixos-agent-env `githooks/`).
- `inputs.nixpkgs.url = "github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d"` — the host pin; never `follows`, never a branch.
- The module never references the flake's own `nixpkgs`; only `pkgs` from the consuming host.
- Eval harness sets `nixpkgs.config.allowUnfree = true` (steam is unfree).
- Defaults: everything privileged or inbound OFF: `gamescope.capSysNice=false`, `gamemode.renice=false` (⇒ `programs.gamemode.enableRenice=false`), all `firewall.*=false`, `controllers.*=false`, `launchers.*=false`, `lowLatencyAudio.enable=false`.
- Commit subjects: `gaming: <summary> (test: <check names>)`; docs-only `docs: …`.
- Nix style: statix rejects `{ ... }:` headers (use `_:` or named args); deadnix must pass; nixfmt via treefmt.
- Build-only; never activate anything.

---

### Task 1 (bootstrap): repository skeleton, lint gate, empty module, eval harness

**Files (all new, in `/home/dalhaka/flakes/gaming`):**
- `flake.nix`, `flake.lock` (generated), `.gitignore` (`result*`), `treefmt.toml`, `githooks/pre-commit`, `githooks/pre-push`, `githooks/allowed-remotes.txt`, `nixosModules/gaming.nix` (options `programs.gaming.enable` only, config empty), `checks/eval-harness.nix`, `README.md`, `docs/OPERATIONS.md`, `docs/superpowers/plans/2026-09-02-gaming-flake.md` (this file, already committed by the orchestrator)

- [ ] **Step 1: `flake.nix`**

```nix
{
  description = "Gaming on NixOS: Steam/Proton-GE, gamescope, gamemode, MangoHud, controllers — every privileged or inbound behaviour opt-in";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d";

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      lib = nixpkgs.lib;
      lintTools = with pkgs; [ treefmt nixfmt-rfc-style shfmt shellcheck statix deadnix ];
      harness = import ./checks/eval-harness.nix { inherit nixpkgs system; module = self.nixosModules.default; };
    in
    {
      nixosModules = {
        gaming = import ./nixosModules/gaming.nix;
        default = self.nixosModules.gaming;
      };

      checks.${system} = {
        lint =
          pkgs.runCommand "lint" { nativeBuildInputs = lintTools; } ''
            cp -r ${self} src && chmod -R u+w src && cd src
            treefmt --ci --config-file treefmt.toml --tree-root .
            shellcheck githooks/pre-push githooks/pre-commit
            find tests -name '*.sh' -print0 2>/dev/null | xargs -0 --no-run-if-empty shellcheck
            statix check .
            deadnix --fail .
            touch $out
          '';
        gaming-eval =
          let
            c = (harness { programs.gaming.enable = true; }).config;
          in
          builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "gaming-eval-ok" { } "touch $out");
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = lintTools;
        shellHook = ''
          git config core.hooksPath githooks
        '';
      };
    };
}
```
(`lib` is used from Task 2 on; if deadnix flags it unused in Task 1, omit it until Task 2.)

- [ ] **Step 2: `checks/eval-harness.nix`**
```nix
{ nixpkgs, system, module }:
extra:
nixpkgs.lib.nixosSystem {
  inherit system;
  modules = [
    module
    (_: {
      boot.loader.grub.enable = false;
      fileSystems."/".device = "none";
      fileSystems."/".fsType = "tmpfs";
      system.stateVersion = "25.11";
      nixpkgs.config.allowUnfree = true;
    })
    extra
  ];
}
```
- [ ] **Step 3: `nixosModules/gaming.nix`** (Task 1 version): `{ lib, ... }: { options.programs.gaming.enable = lib.mkEnableOption "gaming stack (Steam, Proton-GE, gamescope, gamemode, MangoHud)"; }`.
- [ ] **Step 4:** copy `githooks/pre-push` and `githooks/allowed-remotes.txt` verbatim from `/home/dalhaka/nixos-agent-env/githooks/`; write `githooks/pre-commit` as the nixos-agent-env one minus the python/basket-specific lines (treefmt, shellcheck of the two hooks + `tests/**/*.sh`, statix, deadnix); `treefmt.toml` with the `nix` (nixfmt) and `shell` (shfmt `-i 2 -ci -w`, includes `*.sh`, `githooks/pre-push`, `githooks/pre-commit`) formatters; `.gitignore` = `result*`.
- [ ] **Step 5:** `README.md` (what it is, how to enable on a host, the security note from the spec's "README notes" section verbatim), `docs/OPERATIONS.md` (a 10-line board: tasks 1-4 with checkboxes).
- [ ] **Step 6:** `git add -A && nix develop -c true` (builds the devShell; the hook path is set by the shellHook), `nix flake check -L` → `lint` and `gaming-eval` green, then `nix develop -c git commit -F <msg>` — `gaming: bootstrap — flake, lint gate, hooks, eval harness, empty module (test: lint, gaming-eval)`.

---

### Task 2: options and configuration

**Files:** Modify `nixosModules/gaming.nix`; modify `flake.nix` checks (`gaming-eval` grows, add `gaming-eval-everything`, `gaming-eval-session-no-cap`).

**Interfaces (Produces):** every option in the spec's table with the exact names: `programs.gaming.{enable, protonGE.enable, protontricks.enable, gamescope.enable, gamescope.capSysNice, gamescope.session.enable, gamemode.enable, gamemode.renice, gamemode.settings, mangohud.enable, controllers.xone, controllers.xpadneo, launchers.heroic, launchers.lutris, launchers.bottles, firewall.remotePlay, firewall.localNetworkGameTransfers, firewall.dedicatedServer, lowLatencyAudio.enable, extraPackages}`.

- [ ] **Step 1: Failing checks** — replace `gaming-eval` and add two more:

```nix
gaming-eval =
  let
    c = (harness { programs.gaming.enable = true; }).config;
    fw = c.networking.firewall;
    steamPorts = [ 27015 27036 27040 ];
    hasAny = ps: l: lib.any (p: lib.elem p l) ps;
    inRange = r: lib.any (x: x.from <= 27036 && x.to >= 27031) r;
  in
  assert lib.assertMsg (!(hasAny steamPorts fw.allowedTCPPorts)) "gaming-eval: TCP Steam port open by default";
  assert lib.assertMsg (!(hasAny steamPorts fw.allowedUDPPorts)) "gaming-eval: UDP Steam port open by default";
  assert lib.assertMsg (!(inRange fw.allowedUDPPortRanges)) "gaming-eval: UDP Steam range open by default";
  assert lib.assertMsg (!(c.security.wrappers ? gamescope)) "gaming-eval: gamescope wrapper present by default";
  assert lib.assertMsg (c.programs.gamemode.enableRenice == false) "gaming-eval: gamemode renice wrapper on by default";
  assert lib.assertMsg (lib.any (p: lib.hasPrefix "proton-ge" (p.pname or p.name or "")) c.programs.steam.extraCompatPackages) "gaming-eval: proton-ge-bin missing";
  assert lib.assertMsg c.programs.steam.enable "gaming-eval: steam not enabled";
  assert lib.assertMsg c.programs.gamescope.enable "gaming-eval: gamescope not enabled";
  builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "gaming-eval-ok" { } "touch $out");

gaming-eval-everything =
  let
    c =
      (harness {
        services.pipewire.enable = true;
        programs.gaming = {
          enable = true;
          gamescope.capSysNice = true;
          gamescope.session.enable = true;
          gamemode.renice = true;
          controllers.xone = true;
          controllers.xpadneo = true;
          launchers = { heroic = true; lutris = true; bottles = true; };
          firewall = { remotePlay = true; localNetworkGameTransfers = true; dedicatedServer = true; };
          lowLatencyAudio.enable = true;
        };
      }).config;
    fw = c.networking.firewall;
  in
  assert lib.assertMsg (lib.elem 27015 fw.allowedTCPPorts && lib.elem 27036 fw.allowedTCPPorts && lib.elem 27040 fw.allowedTCPPorts) "everything: TCP ports";
  assert lib.assertMsg (lib.elem 27015 fw.allowedUDPPorts && lib.elem 27036 fw.allowedUDPPorts) "everything: UDP ports";
  assert lib.assertMsg (c.security.wrappers ? gamescope) "everything: gamescope wrapper";
  assert lib.assertMsg c.programs.gamemode.enableRenice "everything: renice";
  assert lib.assertMsg c.hardware.xone.enable "everything: xone";
  assert lib.assertMsg c.hardware.xpadneo.enable "everything: xpadneo";
  assert lib.assertMsg (c.services.pipewire.extraConfig.pipewire."92-gaming-low-latency"."context.properties"."default.clock.quantum" == 256) "everything: pipewire quantum";
  builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "gaming-eval-everything-ok" { } "touch $out");

gaming-eval-session-no-cap =
  let
    c = (harness { programs.gaming = { enable = true; gamescope.session.enable = true; }; }).config;
  in
  assert lib.assertMsg (!(c.security.wrappers ? gamescope)) "session-no-cap: wrapper present without capSysNice";
  assert lib.assertMsg c.programs.steam.gamescopeSession.enable "session-no-cap: session not enabled";
  builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "gaming-eval-session-no-cap-ok" { } "touch $out");
```
Verify the exact port lists against `$NP/nixos/modules/programs/steam.nix` at the pin before trusting the numbers above (`NP=$(nix eval --raw github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d#path)`); adjust the assertions to what the pinned module really opens and say so in the commit body. Run: `nix build .#checks.x86_64-linux.gaming-eval -L --no-link` → red (options missing).

- [ ] **Step 2: Implement the module.**
```nix
{ config, lib, pkgs, ... }:
let
  cfg = config.programs.gaming;
  mkOff = d: lib.mkOption { type = lib.types.bool; default = false; description = d; };
  mkOn = d: lib.mkOption { type = lib.types.bool; default = true; description = d; };
in
{
  options.programs.gaming = {
    enable = lib.mkEnableOption "gaming stack (Steam, Proton-GE, gamescope, gamemode, MangoHud); every privileged or inbound behaviour stays off unless its own switch is on";
    protonGE.enable = mkOn "Add Proton-GE (pkgs.proton-ge-bin) to Steam's compatibility tools.";
    protontricks.enable = mkOn "Install protontricks.";
    gamescope.enable = mkOn "Install gamescope (programs.gamescope.enable).";
    gamescope.capSysNice = mkOff "Install the cap_sys_nice wrapper for gamescope (programs.gamescope.capSysNice). A capability wrapper — off by default.";
    gamescope.session.enable = mkOff "Steam's gamescope session (Big-Picture-style). Requires gamescope.enable.";
    gamemode.enable = mkOn "programs.gamemode.enable (daemon that applies CPU governor tweaks while a game runs).";
    gamemode.renice = mkOff "Let gamemoded renice game processes: installs a CAP_SYS_NICE wrapper (programs.gamemode.enableRenice). Off by default — the upstream default is on.";
    gamemode.settings = lib.mkOption { type = lib.types.attrs; default = { }; description = "Passthrough to programs.gamemode.settings."; };
    mangohud.enable = mkOn "Install MangoHud (in-game overlay).";
    controllers.xone = mkOff "hardware.xone: Xbox wireless dongle/wired driver (out-of-tree module; also enables xpad-noone and blacklists in-tree xpad).";
    controllers.xpadneo = mkOff "hardware.xpadneo: Xbox Bluetooth pads (out-of-tree module).";
    launchers.heroic = mkOff "Install Heroic (Epic/GOG/Amazon launcher).";
    launchers.lutris = mkOff "Install Lutris.";
    launchers.bottles = mkOff "Install Bottles.";
    firewall.remotePlay = mkOff "Open the firewall for Steam Remote Play (programs.steam.remotePlay.openFirewall).";
    firewall.localNetworkGameTransfers = mkOff "Open the firewall for Steam local network game transfers.";
    firewall.dedicatedServer = mkOff "Open the firewall for a Steam dedicated server.";
    lowLatencyAudio.enable = mkOff "PipeWire 256-sample quantum override (services.pipewire.extraConfig). Requires services.pipewire.enable.";
    extraPackages = lib.mkOption { type = lib.types.listOf lib.types.package; default = [ ]; description = "Extra packages inside Steam's FHS environment (programs.steam.extraPackages)."; };
  };

  config = lib.mkIf cfg.enable {
    programs.steam = {
      enable = true;
      extraCompatPackages = lib.optional cfg.protonGE.enable pkgs.proton-ge-bin;
      protontricks.enable = cfg.protontricks.enable;
      gamescopeSession.enable = cfg.gamescope.session.enable;
      remotePlay.openFirewall = cfg.firewall.remotePlay;
      localNetworkGameTransfers.openFirewall = cfg.firewall.localNetworkGameTransfers;
      dedicatedServer.openFirewall = cfg.firewall.dedicatedServer;
      extraPackages = (lib.optional cfg.mangohud.enable pkgs.mangohud) ++ cfg.extraPackages;
    };
    programs.gamescope = {
      enable = cfg.gamescope.enable;
      capSysNice = cfg.gamescope.capSysNice;
    };
    programs.gamemode = {
      enable = cfg.gamemode.enable;
      enableRenice = cfg.gamemode.renice;
      settings = cfg.gamemode.settings;
    };
    hardware.xone.enable = cfg.controllers.xone;
    hardware.xpadneo.enable = cfg.controllers.xpadneo;
    environment.systemPackages =
      (lib.optional cfg.mangohud.enable pkgs.mangohud)
      ++ (lib.optional cfg.launchers.heroic pkgs.heroic)
      ++ (lib.optional cfg.launchers.lutris pkgs.lutris)
      ++ (lib.optional cfg.launchers.bottles pkgs.bottles);
    services.pipewire.extraConfig.pipewire = lib.mkIf cfg.lowLatencyAudio.enable {
      "92-gaming-low-latency" = {
        "context.properties" = {
          "default.clock.quantum" = 256;
          "default.clock.min-quantum" = 256;
        };
      };
    };
  };
}
```
Check each upstream option name against the pinned module files (`programs/steam.nix`, `programs/gamescope.nix`, `programs/gamemode.nix`, `hardware/xone.nix`, `hardware/xpadneo.nix`, `services/desktops/pipewire/pipewire.nix`) before committing; record any rename as a deviation.

- [ ] **Step 3: Run** the three checks + `lint` → green (the `everything` check needs `services.pipewire.enable = true` in its harness extra, as written). **Step 4: Commit** — `gaming: programs.gaming options and wiring; renice and gamescope wrappers off by default (test: gaming-eval, gaming-eval-everything, gaming-eval-session-no-cap, lint)`.

---

### Task 3: build-time assertions and one negative check each

**Files:** Modify `nixosModules/gaming.nix` (add `assertions`), `flake.nix` (six `gaming-assertion-negative-<n>` checks).

- [ ] **Step 1: Failing checks** — the negative pattern (from nixos-agent-env `assertion-negative`):
```nix
mkNegative = name: extra: expect:
  let
    attempt = builtins.tryEval (harness extra).config.system.build.toplevel.drvPath;
  in
  if attempt.success then
    throw "${name}: the build DID NOT FAIL (${expect})"
  else
    pkgs.runCommand "${name}-ok" { } "touch $out";
```
and:
```nix
gaming-assertion-negative-1 = mkNegative "session-without-gamescope" { programs.gaming = { enable = true; gamescope.enable = false; gamescope.session.enable = true; }; } "session requires gamescope";
gaming-assertion-negative-2 = mkNegative "graphics-disabled" { programs.gaming.enable = true; hardware.graphics.enable = lib.mkForce false; } "enable requires hardware.graphics";
gaming-assertion-negative-3 = mkNegative "steam-port-open-without-switch" { programs.gaming.enable = true; networking.firewall.allowedTCPPorts = [ 27036 ]; } "steam port without firewall switch";
gaming-assertion-negative-4 = mkNegative "gamescope-wrapper-without-switch" { programs.gaming.enable = true; programs.gamescope.capSysNice = lib.mkForce true; } "wrapper without capSysNice";
gaming-assertion-negative-5 = mkNegative "renice-without-switch" { programs.gaming.enable = true; programs.gamemode.enableRenice = lib.mkForce true; } "renice without gamemode.renice";
gaming-assertion-negative-6 = mkNegative "audio-without-pipewire" { programs.gaming = { enable = true; lowLatencyAudio.enable = true; }; services.pipewire.enable = false; } "lowLatencyAudio requires pipewire";
```
Run one → it throws "DID NOT FAIL" (no assertions yet).

- [ ] **Step 2: Implement** `assertions` inside `config`:
```nix
assertions =
  let
    fw = config.networking.firewall;
    steamTCP = [ 27015 27036 27040 ];
    steamUDP = [ 27015 27036 ];
    anySwitch = cfg.firewall.remotePlay || cfg.firewall.localNetworkGameTransfers || cfg.firewall.dedicatedServer;
    openTCP = lib.filter (p: lib.elem p fw.allowedTCPPorts) steamTCP;
    openUDP = lib.filter (p: lib.elem p fw.allowedUDPPorts) steamUDP;
    openRange = lib.filter (r: r.from <= 27036 && r.to >= 27031) fw.allowedUDPPortRanges;
  in
  [
    { assertion = cfg.gamescope.session.enable -> cfg.gamescope.enable; message = "programs.gaming.gamescope.session.enable needs programs.gaming.gamescope.enable"; }
    { assertion = config.hardware.graphics.enable; message = "programs.gaming needs hardware.graphics.enable (a host force-disabled it)"; }
    { assertion = anySwitch || (openTCP == [ ] && openUDP == [ ] && openRange == [ ]); message = "Steam ports are open in networking.firewall (${toString openTCP} ${toString openUDP}) but no programs.gaming.firewall.* switch is on"; }
    { assertion = (config.security.wrappers ? gamescope) -> cfg.gamescope.capSysNice; message = "a gamescope capability wrapper exists but programs.gaming.gamescope.capSysNice is off"; }
    { assertion = config.programs.gamemode.enableRenice -> cfg.gamemode.renice; message = "programs.gamemode.enableRenice is on (CAP_SYS_NICE wrapper) but programs.gaming.gamemode.renice is off"; }
    { assertion = cfg.lowLatencyAudio.enable -> config.services.pipewire.enable; message = "programs.gaming.lowLatencyAudio needs services.pipewire.enable"; }
  ];
```
Also `warnings = lib.optional cfg.gamescope.capSysNice "programs.gaming: gamescope.capSysNice installs a cap_sys_nice wrapper" ++ lib.optional cfg.gamemode.renice "programs.gaming: gamemode.renice installs a CAP_SYS_NICE wrapper on gamemoded";`.
Note on assertion 3: when a switch is on, the ports it opens are expected; the assertion only fires when NO switch is on. (Negative check 3 sets a port by hand with all switches off.)

- [ ] **Step 3: Run** all six negatives + the three eval checks + lint → green. **Step 4: Commit** — `gaming: six build-time assertions with a negative check each (test: gaming-assertion-negative-1..6, gaming-eval, lint)`.

---

### Task 4 (docs): acceptance drill, README, runbook, board

**Files:** `tests/acceptance/gaming.sh` (bash; PASS/FAIL lines in the style of nixos-agent-env `tests/acceptance/backup.sh`: `command -v steam`, `gamemoded -s`, `gamescope --version`, `mangohud --version`, `ss -ltnu` before/after Steam start shows no new listeners, `sudo nft list ruleset | grep -E '2703[1-6]|27015|27040'` empty, operator-judged prompts for the Steam login window, the Proton-GE entry and a gamescope smoke test), `docs/runbooks/gaming.md` (plain language; how to flip each switch on the host and rebuild; the gamescope/NVIDIA caveat), `README.md` (security notes verbatim from the spec), `docs/OPERATIONS.md`.

- [ ] `nix develop -c bash -n tests/acceptance/gaming.sh`; lint gate; commit `docs: gaming — acceptance drill, runbook, README notes (test: lint)`.

---

## Self-review (orchestrator)

Spec coverage: repo skeleton (T1), options table + pipewire shape + unfree harness (T2), assertions 1-6 + negatives + control scenario (T3), acceptance/README (T4). Host wiring and backup path are in the wiring plan (`2026-09-02-host-wiring.md` in nixos-agent-env). Type consistency: option names identical in T2 module, T2 checks, T3 assertions.
