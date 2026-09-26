{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.gaming;
  mkOff =
    d:
    lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = d;
    };
  mkOn =
    d:
    lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = d;
    };
in
{
  options.programs.gaming = {
    enable = lib.mkEnableOption "gaming stack (Steam, Proton-GE, gamescope, gamemode, MangoHud); every privileged or inbound behaviour stays off unless its own switch is on";
    protonGE.enable = mkOn "Add Proton-GE (pkgs.proton-ge-bin) to Steam's compatibility tools.";
    protontricks.enable = mkOn "Install protontricks.";
    gamescope = {
      enable = mkOn "Install gamescope (programs.gamescope.enable).";
      capSysNice = mkOff "Install the cap_sys_nice wrapper for gamescope (programs.gamescope.capSysNice). A capability wrapper — off by default.";
      session.enable = mkOff "Steam's gamescope session (Big-Picture-style). Requires gamescope.enable.";
    };
    gamemode = {
      enable = mkOn "programs.gamemode.enable (daemon that applies CPU governor tweaks while a game runs).";
      renice = mkOff "Let gamemoded renice game processes: installs a CAP_SYS_NICE wrapper (programs.gamemode.enableRenice). Off by default — the upstream default is on.";
      settings = lib.mkOption {
        type = lib.types.attrs;
        default = { };
        description = "Passthrough to programs.gamemode.settings.";
      };
    };
    mangohud.enable = mkOn "Install MangoHud (in-game overlay).";
    controllers = {
      xone = mkOff "hardware.xone: Xbox wireless dongle/wired driver (out-of-tree module; also enables xpad-noone and blacklists in-tree xpad).";
      xpadneo = mkOff "hardware.xpadneo: Xbox Bluetooth pads (out-of-tree module).";
    };
    launchers = {
      heroic = mkOff "Install Heroic (Epic/GOG/Amazon launcher). At the pinned nixpkgs rev its electron dependency may be marked insecure/EOL; add the affected version string to nixpkgs.config.permittedInsecurePackages on the host if the build refuses to evaluate.";
      lutris = mkOff "Install Lutris.";
      bottles = mkOff "Install Bottles.";
    };
    firewall = {
      remotePlay = mkOff "Open the firewall for Steam Remote Play (programs.steam.remotePlay.openFirewall).";
      localNetworkGameTransfers = mkOff "Open the firewall for Steam local network game transfers.";
      dedicatedServer = mkOff "Open the firewall for a Steam dedicated server.";
    };
    lowLatencyAudio.enable = mkOff "PipeWire 256-sample quantum override (services.pipewire.extraConfig). Requires services.pipewire.enable.";
    extraPackages = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [ ];
      description = "Extra packages inside Steam's FHS environment (programs.steam.extraPackages).";
    };
  };

  config = lib.mkIf cfg.enable {
    programs = {
      steam = {
        enable = true;
        extraCompatPackages = lib.optional cfg.protonGE.enable pkgs.proton-ge-bin;
        protontricks.enable = cfg.protontricks.enable;
        gamescopeSession.enable = cfg.gamescope.session.enable;
        remotePlay.openFirewall = cfg.firewall.remotePlay;
        localNetworkGameTransfers.openFirewall = cfg.firewall.localNetworkGameTransfers;
        dedicatedServer.openFirewall = cfg.firewall.dedicatedServer;
        extraPackages = (lib.optional cfg.mangohud.enable pkgs.mangohud) ++ cfg.extraPackages;
      };
      gamescope = {
        inherit (cfg.gamescope) enable capSysNice;
      };
      gamemode = {
        inherit (cfg.gamemode) enable settings;
        enableRenice = cfg.gamemode.renice;
      };
    };
    hardware = {
      xone.enable = cfg.controllers.xone;
      xpadneo.enable = cfg.controllers.xpadneo;
    };
    environment.systemPackages =
      # mesa-demos: the runbook's and drill's smoke test is
      # `gamescope -- glxgears`; without this package the documented command
      # cannot run.
      [ pkgs.mesa-demos ]
      ++ (lib.optional cfg.mangohud.enable pkgs.mangohud)
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

    assertions =
      let
        fw = config.networking.firewall;
        steamTCP = [
          27015
          27036
          27040
        ];
        steamUDP = [
          27015
          27036
        ];
        anySwitch =
          cfg.firewall.remotePlay || cfg.firewall.localNetworkGameTransfers || cfg.firewall.dedicatedServer;
        openTCP = lib.filter (p: lib.elem p fw.allowedTCPPorts) steamTCP;
        openUDP = lib.filter (p: lib.elem p fw.allowedUDPPorts) steamUDP;
        openRange = lib.filter (r: r.from <= 27036 && r.to >= 27031) fw.allowedUDPPortRanges;
      in
      [
        {
          assertion = cfg.gamescope.session.enable -> cfg.gamescope.enable;
          message = "programs.gaming.gamescope.session.enable needs programs.gaming.gamescope.enable";
        }
        {
          assertion = config.hardware.graphics.enable;
          message = "programs.gaming needs hardware.graphics.enable (a host force-disabled it)";
        }
        {
          assertion = anySwitch || (openTCP == [ ] && openUDP == [ ] && openRange == [ ]);
          message = "Steam ports are open in networking.firewall (${toString openTCP} ${toString openUDP}) but no programs.gaming.firewall.* switch is on";
        }
        {
          assertion = (config.security.wrappers ? gamescope) -> cfg.gamescope.capSysNice;
          message = "a gamescope capability wrapper exists but programs.gaming.gamescope.capSysNice is off";
        }
        {
          assertion = config.programs.gamemode.enableRenice -> cfg.gamemode.renice;
          message = "programs.gamemode.enableRenice is on (CAP_SYS_NICE wrapper) but programs.gaming.gamemode.renice is off";
        }
        {
          assertion = cfg.lowLatencyAudio.enable -> config.services.pipewire.enable;
          message = "programs.gaming.lowLatencyAudio needs services.pipewire.enable";
        }
      ];

    warnings =
      lib.optional cfg.gamescope.capSysNice "programs.gaming: gamescope.capSysNice installs a cap_sys_nice wrapper"
      ++ lib.optional cfg.gamemode.renice "programs.gaming: gamemode.renice installs a CAP_SYS_NICE wrapper on gamemoded";
  };
}
