# FL5 (plan 2026-09-24-fleet-and-forge.md): the console bootstrap module
# TEMPLATE -- `fleet join-script` substitutes @DEPLOY_KEYS@ (the deploy keys
# list literal) and @PARENT_IMPORTS@ (the parent's module paths, or empty)
# and prints the result as the bash script the operator pipes to `sudo bash`
# on the new machine's console; checks.fleet-eval substitutes the same two
# with the fixture key to eval the module, and FL6's VM test imports it as
# the forge's initial state. The placeholders in expression position keep
# this file from being parseable Nix until substituted, so the Nix linters
# skip it (treefmt.toml, statix, deadnix) the way they skip the generator
# files -- the substituted module is what every check evaluates.
{
  lib,
  config,
  ...
}:
let
  cfg = config.fleet-join;
in
{
  imports = [ @PARENT_IMPORTS@ ];

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
      openssh.authorizedKeys.keys = @DEPLOY_KEYS@;
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
