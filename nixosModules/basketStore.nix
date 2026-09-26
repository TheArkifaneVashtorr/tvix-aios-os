{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.baskets;
  jsonFormat = pkgs.formats.json { };
  agentBasketPairs = lib.flatten (
    lib.mapAttrsToList (
      agent: a:
      map (b: {
        inherit agent;
        basket = b;
      }) a.baskets
    ) cfg.agents
  );
in
{
  options.services.baskets = {
    definitions = lib.mkOption {
      default = { };
      description = "Basket declarations — the single source of truth for classification.";
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            classification = lib.mkOption {
              type = lib.types.enum [
                "local-only"
                "redacted"
                "permitted"
              ];
            };
            mount = lib.mkOption { type = lib.types.str; };
            access = lib.mkOption {
              type = lib.types.enum [
                "ro"
                "rw"
              ];
              default = "ro";
            };
          };
        }
      );
    };
    agents = lib.mkOption {
      default = { };
      description = "Agent declarations: which baskets they mount and how they egress.";
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            baskets = lib.mkOption {
              type = lib.types.listOf lib.types.str;
              default = [ ];
            };
            egress = lib.mkOption {
              type = lib.types.str;
              default = "none";
              description = ''"none", or "broker:<instance>" naming a services.egress-broker instance.'';
            };
            placement = lib.mkOption {
              type = lib.types.enum [
                "host"
                "microvm"
                "bubblewrap"
              ];
              default = "bubblewrap";
            };
          };
        }
      );
    };
    manifestsPackage = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      description = "Generated Phase 1 manifest JSONs, one per basket definition.";
    };
  };

  config = {
    services.baskets.manifestsPackage = pkgs.linkFarm "basket-manifests" (
      lib.mapAttrsToList (id: d: {
        name = "${id}.json";
        path = jsonFormat.generate "${id}.json" {
          inherit id;
          inherit (d) classification mount access;
        };
      }) cfg.definitions
    );

    assertions =
      # A1: referenced baskets exist
      map (p: {
        assertion = cfg.definitions ? ${p.basket};
        message = "basket agent '${p.agent}' references basket '${p.basket}', which has no services.baskets.definitions entry";
      }) agentBasketPairs
      # A2: the invariant — local-only never reaches a network-capable agent
      ++ map (p: {
        assertion =
          (cfg.agents.${p.agent}.egress == "none")
          || !(cfg.definitions ? ${p.basket})
          || cfg.definitions.${p.basket}.classification != "local-only";
        message = "agent '${p.agent}' has egress '${cfg.agents.${p.agent}.egress}' but mounts local-only basket '${p.basket}' — local-only baskets may only be mounted into agents with no off-box route (invariant: brief section 3.1/5.2)";
      }) agentBasketPairs
      # A3: named broker instances exist
      ++ lib.mapAttrsToList (agent: a: {
        assertion =
          a.egress == "none"
          || (
            lib.hasPrefix "broker:" a.egress
            && config.services.egress-broker.instances ? ${lib.removePrefix "broker:" a.egress}
          );
        message = "agent '${agent}' egress '${a.egress}' is neither \"none\" nor \"broker:<instance>\" naming an existing services.egress-broker instance";
      }) cfg.agents
      # A4: mount paths unique within one agent
      ++ lib.mapAttrsToList (agent: a: {
        assertion =
          let
            mounts = map (b: cfg.definitions.${b}.mount) (lib.filter (b: cfg.definitions ? ${b}) a.baskets);
          in
          lib.length mounts == lib.length (lib.unique mounts);
        message = "agent '${agent}' mounts two baskets at the same path — mount points must be unique per agent";
      }) cfg.agents;
  };
}
