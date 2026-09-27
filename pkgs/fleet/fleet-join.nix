# FL5 (plan 2026-09-24-fleet-and-forge.md): the console bootstrap module —
# a FUNCTION, not a template (PL27, plan 2026-09-11-platform.md): the caller
# applies it with deployKeys (the deploy keys list) and parentImports (the
# parent's module paths, or empty). `fleet join-script` embeds this file
# verbatim in the bash script the operator pipes to `sudo bash` on the new
# machine's console, wrapping it in a one-line application;
# checks.fleet-eval imports it with the fixture key, and FL6's VM test
# applies it as the forge's initial state. The file is ordinary parseable
# Nix, so the Nix linters cover it like any other module (the old
# statix/deadnix/treefmt template exemptions retired with PL27).
{
  deployKeys,
  parentImports ? [ ],
}:
{
  config,
  lib,
  ...
}:
let
  cfg = config.fleet-join;
in
{
  imports = parentImports;

  options.fleet-join.enable = lib.mkOption {
    type = lib.types.bool;
    default = true;
    description = "the console bootstrap; the first fleet deploy replaces it";
  };

  config = lib.mkIf cfg.enable {
    services.openssh = {
      enable = true;
      settings = {
        PasswordAuthentication = false;
        KbdInteractiveAuthentication = false;
        PermitRootLogin = "no";
      };
    };

    users.users.deploy = {
      isNormalUser = true;
      description = "fleet deploy user (bootstrap)";
      openssh.authorizedKeys.keys = deployKeys;
    };

    security.sudo.extraRules = [
      {
        users = [ "deploy" ];
        commands = [
          {
            command = "/run/current-system/sw/bin/nix-env --profile /nix/var/nix/profiles/system --set /nix/store/*";
            options = [ "NOPASSWD" ];
          }
          {
            command = "/nix/store/*/bin/switch-to-configuration switch";
            options = [ "NOPASSWD" ];
          }
          {
            command = "/run/current-system/sw/bin/nixos-generate-config --show-hardware-config";
            options = [ "NOPASSWD" ];
          }
        ];
      }
    ];

    nix.settings.trusted-users = [ "deploy" ];
  };
}
