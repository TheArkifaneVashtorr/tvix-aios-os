{ pkgs, lib, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ./agent-prereqs.nix
    ./graphics.nix
    ./proton-backup.nix
    ./firefox.nix
    ./claude-desktop.nix
    ./helm.nix
    ./lanes.nix
    ./seat.nix
  ];

  boot.loader = {
    # Bootloader.
    systemd-boot.enable = true;
    efi.canTouchEfiVariables = true;
  };

  # Profile marker for Helm's drift/status tile and for the operator
  # (host-wiring plan Task 1). Base stays "base"; the gaming specialisation
  # overrides it to "gaming". hosts/core/gaming.nix (Steam/Proton-GE/
  # gamescope/gamemode/MangoHud) is imported ONLY here, never at the top
  # level, so the base profile never gains programs.gaming.enable.
  #
  # environment.etc."<name>".text is `types.lines`, which nixpkgs MERGES
  # (concatenates) across definitions at the same priority rather than
  # letting the later one win -- specialisation.<name>.configuration extends
  # the parent's modules, so without mkForce the child's "gaming" definition
  # and the parent's "base" definition both survive and concatenate into
  # "gaming\nbase" (confirmed with `nix eval
  # .#nixosConfigurations.core.config.specialisation.gaming.configuration.environment.etc.\"helm/profile\".text`).
  # mkForce drops the parent's lower-priority definition so only "gaming"
  # remains -- true override, matching this file's stated intent (deviation
  # from the plan's plain assignment, which does not achieve that intent).
  environment.etc."helm/profile".text = "base";
  specialisation.gaming.configuration = {
    imports = [ ./gaming.nix ];
    environment.etc."helm/profile".text = lib.mkForce "gaming";
  };

  networking = {
    hostName = "core"; # absorbed from /etc/nixos (was "nixos")

    # Enable networking
    networkmanager.enable = true;
  };

  # Set your time zone.
  time.timeZone = "America/Chicago";

  i18n = {
    # Select internationalisation properties.
    defaultLocale = "en_US.UTF-8";

    extraLocaleSettings = {
      LC_ADDRESS = "en_US.UTF-8";
      LC_IDENTIFICATION = "en_US.UTF-8";
      LC_MEASUREMENT = "en_US.UTF-8";
      LC_MONETARY = "en_US.UTF-8";
      LC_NAME = "en_US.UTF-8";
      LC_NUMERIC = "en_US.UTF-8";
      LC_PAPER = "en_US.UTF-8";
      LC_TELEPHONE = "en_US.UTF-8";
      LC_TIME = "en_US.UTF-8";
    };
  };

  services = {
    # Phase 4b: Cowork (dedicated UID, broker netns, waypipe display, one rw
    # basket) + its generated managed-settings lockdown. Defaults from
    # nixosModules/cowork.nix match this host: basket "cowork-workspace",
    # brokerInstance "cowork" (also the default egress-broker instance
    # cowork.nix declares), operatorUser "dalhaka" (this host's only human
    # user, defined below). Neither starts anything at boot — cowork.service
    # is operator-started only (tools/cowork-up.sh, Task 3) because basket
    # decryption needs the YubiKey in hand.
    # enable stays false: turning this on would write the lockdown to
    # /etc/claude-code/managed-settings.json MACHINE-WIDE, which would apply
    # to every Claude Code session on this host -- including the operator's
    # own orchestrator session -- forcing its subprocess network (nix/curl/
    # git) through the cowork-only broker after the next rebuild. That
    # machine-wide enforcement is deferred until the orchestrator's own
    # confinement is designed. Cowork still gets the identical rendered
    # settings, but at claude-app user scope only, via cowork.nix (which
    # consumes services.claude-managed-settings.settingsFile) -- see
    # docs/research-2026-09-02-phase4.md: Cowork reads proxy/strictness
    # config from the running user's ~/.claude/settings.json just as well,
    # and the security-relevant keys are honored only from user/managed/CLI
    # scope (verified for mask entries; acceptance step 6 empirically tests the
    # rest before Cowork touches real data), so this still holds the brief §7 Phase 4
    # guarantee for Cowork.
    claude-managed-settings = {
      enable = false;
      brokerInstance = "cowork";
    };
    # Decision 2026-09-02 (docs/decisions/2026-09-02-cowork-tier-parked.md):
    # the tier-A Cowork bubble stays in the flake (module + checks) but is
    # OFF on this host; the operator builds in the desktop app's Code tab on
    # the host instead (./claude-desktop.nix). Flip to true to redeploy.
    cowork.enable = false;

    evidence-store.enable = true;

    xserver = {
      # Enable the X11 windowing system.
      enable = true;

      # Configure keymap in X11
      xkb = {
        layout = "us";
        variant = "";
      };
    };

    # Enable the GNOME Desktop Environment. At nixos-26.05 these two options
    # moved out from under services.xserver (see the release-upgrade review:
    # docs/reviews/2026-09-05-release-upgrade-26.05.md).
    displayManager.gdm.enable = true;
    desktopManager.gnome.enable = true;

    # Enable CUPS to print documents.
    printing.enable = true;

    # Enable sound with pipewire.
    pulseaudio.enable = false;
    pipewire = {
      enable = true;
      alsa.enable = true;
      alsa.support32Bit = true;
      pulse.enable = true;
    };
  };

  security.rtkit.enable = true;

  # Define a user account. Don't forget to set a password with 'passwd'.
  users.users.dalhaka = {
    isNormalUser = true;
    description = "dalhaka";
    # Fixed at the live host's uid (verified 2026-09-02 with `id`):
    # services.proton-backup (nixosModules/protonBackup.nix) needs a
    # deterministic /run/user/<uid> to kick the user-scope push unit.
    uid = 1000;
    extraGroups = [
      "networkmanager"
      "wheel"
    ];
    packages = with pkgs; [ ];
  };

  # firefox: enabled + hardened in ./firefox.nix

  nixpkgs.config.allowUnfree = true; # Allow unfree packages

  # List packages installed in system profile. To search, run:
  # $ nix search wget
  environment.systemPackages = with pkgs; [ ];

  # This value determines the NixOS release from which the default
  # settings for stateful data, like file locations and database versions
  # on your system were taken. It's perfectly fine and recommended to leave
  # this value at the release version of the first install of this system.
  # Before changing this value read the documentation for this option
  # (e.g. man configuration.nix or on https://nixos.org/nixos/options.html).
  system.stateVersion = "25.05"; # Did you read the comment?
}
