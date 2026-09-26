# Eval-only stand-in for services.egress-broker.instances: declares the
# same option shape as nixos-agent-env/nixosModules/egressBroker.nix:22-63
# (copied verbatim below) so checks/eval-harness.nix can evaluate
# services.comfyui against a real broker-instance submodule without pulling
# in the real module's systemd units, nftables rules, or mitmproxy wiring —
# none of which this repo can build or run (build-only, no live host). The
# real module on the host provides this option for real; this file exists
# only so `services.egress-broker.instances.media = { ... }` type-checks
# here the same way it will there.
{ lib, ... }:
{
  options.services.egress-broker.instances = lib.mkOption {
    default = { };
    description = "Per-netns TLS-terminating egress brokers.";
    type = lib.types.attrsOf (
      lib.types.submodule {
        options = {
          hostAddress = lib.mkOption { type = lib.types.str; };
          namespaceAddress = lib.mkOption { type = lib.types.str; };
          prefixLength = lib.mkOption {
            type = lib.types.int;
            default = 30;
          };
          listenPort = lib.mkOption {
            type = lib.types.port;
            default = 3128;
          };
          allow = lib.mkOption {
            type = lib.types.listOf lib.types.str;
            default = [ ];
          };
          inject = lib.mkOption {
            default = { };
            type = lib.types.attrsOf (
              lib.types.submodule {
                options = {
                  header = lib.mkOption {
                    type = lib.types.str;
                    default = "Authorization";
                  };
                  prefix = lib.mkOption {
                    type = lib.types.str;
                    default = "Bearer ";
                  };
                  valueFile = lib.mkOption { type = lib.types.str; };
                };
              }
            );
          };
        };
      }
    );
  };

  config = { };
}
