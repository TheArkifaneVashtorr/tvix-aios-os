# PL14: gaming's own 11 checks, absorbed in-repo from the retired sibling
# flake (~/flakes/gaming, git subtree add --prefix gaming; the flake and
# its lock are git rm'd, mirroring GN12's media/checks.nix extraction).
# Two deliberate renames avoid the collision the two-way guard exists for:
# `lint` -> `gaming-lint`, `drill-unit` -> `gaming-drill-unit` (the other
# nine names were already prefixed gaming-* in the source flake). The two
# ${self} shell references point at ${self}/gaming -- the copied tree is
# the subtree, not the whole repo -- and harness's module argument is the
# relative ./nixosModules/gaming.nix import (gaming's own flake no longer
# exists to hold nixosModules.default).
{
  pkgs,
  lib,
  self,
  nixpkgs,
  system,
}:
let
  lintTools = with pkgs; [
    treefmt
    nixfmt-rfc-style
    shfmt
    shellcheck
    statix
    deadnix
  ];
  harness = import ./checks/eval-harness.nix {
    inherit nixpkgs system;
    module = import ./nixosModules/gaming.nix;
  };
  mkNegative =
    name: extra: expect:
    let
      attempt = builtins.tryEval (harness extra).config.system.build.toplevel.drvPath;
    in
    if attempt.success then
      throw "${name}: the build DID NOT FAIL (${expect})"
    else
      pkgs.runCommand "${name}-ok" { } "touch $out";
in
{
  gaming-lint = pkgs.runCommand "lint" { nativeBuildInputs = lintTools; } ''
    cp -r ${self}/gaming src && chmod -R u+w src && cd src
    treefmt --ci --config-file treefmt.toml --tree-root .
    shellcheck githooks/pre-push githooks/pre-commit
    if [ -d tests ]; then
      # -x: follow shellcheck source= directives (tests/unit/listeners.sh
      # sources tests/acceptance/gaming.sh); its source-path=SCRIPTDIR
      # directive resolves the source= path from the file's own
      # directory, so this works regardless of shellcheck's cwd.
      find tests -name '*.sh' -print0 | xargs -0 --no-run-if-empty shellcheck -x
    fi
    statix check .
    deadnix --fail .
    touch $out
  '';
  # listeners.sh sources ../acceptance/gaming.sh by relative path, so it
  # needs the tree laid out the way the repo has it -- a lone
  # ${./tests/unit/listeners.sh} store path has no such sibling.
  gaming-drill-unit =
    pkgs.runCommand "drill-unit"
      {
        nativeBuildInputs = [
          pkgs.bash
          pkgs.gawk
        ];
      }
      ''
        cp -r ${self}/gaming src && chmod -R u+w src
        bash src/tests/unit/listeners.sh
        bash src/tests/unit/drill-success.sh
        touch $out
      '';
  gaming-eval =
    let
      c = (harness { programs.gaming.enable = true; }).config;
      fw = c.networking.firewall;
      steamTCPPorts = [
        27015
        27036
        27040
      ];
      steamUDPPorts = [
        27015
        27036
      ];
      hasAny = ps: l: lib.any (p: lib.elem p l) ps;
      inRange = r: lib.any (x: x.from <= 27036 && x.to >= 27031) r;
    in
    assert lib.assertMsg (
      !(hasAny steamTCPPorts fw.allowedTCPPorts)
    ) "gaming-eval: TCP Steam port open by default";
    assert lib.assertMsg (
      !(hasAny steamUDPPorts fw.allowedUDPPorts)
    ) "gaming-eval: UDP Steam port open by default";
    assert lib.assertMsg (
      !(inRange fw.allowedUDPPortRanges)
    ) "gaming-eval: UDP Steam range open by default";
    assert lib.assertMsg (
      !(c.security.wrappers ? gamescope)
    ) "gaming-eval: gamescope wrapper present by default";
    assert lib.assertMsg (
      !c.programs.gamemode.enableRenice
    ) "gaming-eval: gamemode renice wrapper on by default";
    assert lib.assertMsg (lib.any (
      p: lib.hasPrefix "proton-ge" (p.pname or p.name or "")
    ) c.programs.steam.extraCompatPackages) "gaming-eval: proton-ge-bin missing";
    assert lib.assertMsg c.programs.steam.enable "gaming-eval: steam not enabled";
    assert lib.assertMsg c.programs.gamescope.enable "gaming-eval: gamescope not enabled";
    assert lib.assertMsg (lib.elem pkgs.mesa-demos c.environment.systemPackages)
      "gaming-eval: mesa-demos missing (the drill's and runbook's smoke test is gamescope -- glxgears)";
    builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "gaming-eval-ok" { } "touch $out");

  gaming-eval-everything =
    let
      c =
        (harness {
          services.pipewire.enable = true;
          # heroic pulls in an electron build nixpkgs marks insecure at
          # this pin (EOL electron-36.9.5); a host enabling
          # launchers.heroic needs the same permittedInsecurePackages
          # entry (see nixosModules/gaming.nix's option description).
          nixpkgs.config.permittedInsecurePackages = [ "electron-36.9.5" ];
          programs.gaming = {
            enable = true;
            gamescope.capSysNice = true;
            gamescope.session.enable = true;
            gamemode.renice = true;
            controllers.xone = true;
            controllers.xpadneo = true;
            launchers = {
              heroic = true;
              lutris = true;
              bottles = true;
            };
            firewall = {
              remotePlay = true;
              localNetworkGameTransfers = true;
              dedicatedServer = true;
            };
            lowLatencyAudio.enable = true;
          };
        }).config;
      fw = c.networking.firewall;
    in
    assert lib.assertMsg (
      lib.elem 27015 fw.allowedTCPPorts
      && lib.elem 27036 fw.allowedTCPPorts
      && lib.elem 27040 fw.allowedTCPPorts
    ) "everything: TCP ports";
    assert lib.assertMsg (
      lib.elem 27015 fw.allowedUDPPorts && lib.elem 27036 fw.allowedUDPPorts
    ) "everything: UDP ports";
    assert lib.assertMsg (c.security.wrappers ? gamescope) "everything: gamescope wrapper";
    assert lib.assertMsg c.programs.gamemode.enableRenice "everything: renice";
    assert lib.assertMsg c.hardware.xone.enable "everything: xone";
    assert lib.assertMsg c.hardware.xpadneo.enable "everything: xpadneo";
    assert lib.assertMsg (
      c.services.pipewire.extraConfig.pipewire."92-gaming-low-latency"."context.properties"."default.clock.quantum"
      == 256
    ) "everything: pipewire quantum";
    builtins.seq c.system.build.toplevel.drvPath (
      pkgs.runCommand "gaming-eval-everything-ok" { } "touch $out"
    );

  gaming-eval-session-no-cap =
    let
      c =
        (harness {
          programs.gaming = {
            enable = true;
            gamescope.session.enable = true;
          };
        }).config;
    in
    assert lib.assertMsg (
      !(c.security.wrappers ? gamescope)
    ) "session-no-cap: wrapper present without capSysNice";
    assert lib.assertMsg c.programs.steam.gamescopeSession.enable "session-no-cap: session not enabled";
    builtins.seq c.system.build.toplevel.drvPath (
      pkgs.runCommand "gaming-eval-session-no-cap-ok" { } "touch $out"
    );

  gaming-assertion-negative-1 = mkNegative "session-without-gamescope" {
    programs.gaming = {
      enable = true;
      gamescope.enable = false;
      gamescope.session.enable = true;
    };
  } "session requires gamescope";

  gaming-assertion-negative-2 = mkNegative "graphics-disabled" {
    programs.gaming.enable = true;
    # hardware/graphics.nix only sets .package{,32} inside `config =
    # lib.mkIf cfg.enable`, so force-disabling graphics.enable leaves
    # them with no value and builtins.tryEval swallows nixpkgs' "option
    # has no value defined" eval error before our own assertion ever
    # runs. Supply them here so the module's assertion is the first
    # failure and this check actually exercises it.
    hardware.graphics = {
      enable = lib.mkForce false;
      package = pkgs.mesa;
      package32 = pkgs.pkgsi686Linux.mesa;
    };
  } "enable requires hardware.graphics";

  gaming-assertion-negative-3 = mkNegative "steam-port-open-without-switch" {
    programs.gaming.enable = true;
    networking.firewall.allowedTCPPorts = [ 27036 ];
  } "steam port without firewall switch";

  gaming-assertion-negative-4 = mkNegative "gamescope-wrapper-without-switch" {
    programs.gaming.enable = true;
    programs.gamescope.capSysNice = lib.mkForce true;
  } "wrapper without capSysNice";

  gaming-assertion-negative-5 = mkNegative "renice-without-switch" {
    programs.gaming.enable = true;
    programs.gamemode.enableRenice = lib.mkForce true;
  } "renice without gamemode.renice";

  gaming-assertion-negative-6 = mkNegative "audio-without-pipewire" {
    programs.gaming = {
      enable = true;
      lowLatencyAudio.enable = true;
    };
    services.pipewire.enable = false;
  } "lowLatencyAudio requires pipewire";
}
