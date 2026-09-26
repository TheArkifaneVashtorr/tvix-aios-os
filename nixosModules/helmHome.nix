{
  config,
  lib,
  ...
}:
let
  helm = config.services.helm;
  cfg = helm.home;
  # D-H4's four rules, applied to the flakes list. (S) -- seats -- is not an
  # assertion: its enum type refuses an unknown seat at evaluation, not here.
  absoluteOffenders = lib.filter (f: !(lib.hasPrefix "/" f.path)) cfg.flakes;
  profileOffenders = lib.filter (
    f: f.profile != null && !(lib.elem f.profile helm.control.profiles)
  ) cfg.flakes;
  paths = map (f: f.path) cfg.flakes;
in
{
  options.services.helm.home = {
    enable = lib.mkEnableOption "Helm Home: the home screen (docs/superpowers/specs/2026-09-04-helm-home-design.md)";

    package = lib.mkOption {
      type = lib.types.package;
      description = ''
        The Helm Home package. The host passes the flake's `helm-home` (HH9
        wires it); a fixture passes a stub. The module installs it as a
        system package and points the autostart entry at its
        `bin/helm-home`.
      '';
    };

    flakes = lib.mkOption {
      type = lib.types.listOf (
        lib.types.submodule (
          { config, ... }:
          {
            options = {
              path = lib.mkOption {
                type = lib.types.str;
                description = "Absolute path of the flake checkout.";
              };
              declaration = lib.mkOption {
                type = lib.types.str;
                default = "${config.path}#helm";
                defaultText = "\"<path>#helm\"";
                description = "The flake attribute Helm Home opens; defaults to <path>#helm.";
              };
              profile = lib.mkOption {
                type = lib.types.nullOr lib.types.str;
                default = null;
                description = "The profile this flake switches to; null for none.";
              };
              seats = lib.mkOption {
                type = lib.types.listOf (
                  lib.types.enum [
                    "claude"
                    "deepseek"
                  ]
                );
                default = [ ];
                description = "The seats this flake opens (claude and/or deepseek).";
              };
            };
          }
        )
      );
      default = [ ];
      description = "The flakes Helm Home lists, held to D-H4's four rules.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = helm.enable && helm.control.enable;
        message = "services.helm.home requires services.helm.enable and services.helm.control.enable (the helm-switch@ unit and its polkit rule)";
      }
      {
        assertion = absoluteOffenders == [ ];
        message = "services.helm.home.flakes: every path must be absolute; offenders: ${
          lib.concatStringsSep " " (map (f: f.path) absoluteOffenders)
        }";
      }
      {
        assertion = profileOffenders == [ ];
        message = "services.helm.home.flakes: profile must be null or one of ${lib.concatStringsSep " " helm.control.profiles}; offenders: ${
          lib.concatStringsSep " " (map (f: f.profile) profileOffenders)
        }";
      }
      {
        assertion = lib.length (lib.unique paths) == lib.length paths;
        message = "services.helm.home.flakes: a path is declared twice";
      }
    ];

    environment = {
      etc = {
        "helm/home.json" = {
          text = builtins.toJSON {
            schema = 1;
            flakes = map (f: {
              inherit (f)
                path
                declaration
                profile
                seats
                ;
            }) cfg.flakes;
          };
          mode = "0644";
        };

        "xdg/autostart/helm-home.desktop" = {
          text = ''
            [Desktop Entry]
            Type=Application
            Name=Helm Home
            Exec=${cfg.package}/bin/helm-home
            OnlyShowIn=GNOME;
            X-GNOME-Autostart-Phase=Application
          '';
          mode = "0644";
        };
      };
      systemPackages = [ cfg.package ];
    };
  };
}
