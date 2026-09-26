# options.aios — the declaration surface of tvix-aios (spec
# 2026-09-22-tvix-aios §4). Step 3's slice (plan 2026-09-22-aios-daemon-
# dispatch, OS10): `aios.data` (the data classes — an alias of
# services.baskets.definitions, the enforcement of invariants 1 and 8),
# `aios.egress` (an alias of services.egress-broker.instances), `aios.seats`
# placed in a unit (rendered into services.baskets.agents, so basketStore's
# four assertions bind a seat exactly as they bind an agent), the rendered
# declaration `aios.json` (config.aios.declaration — the only thing `aiosd`
# reads, invariant 5) and the two assertions of invariant 8 below. Later
# steps own `aios.vms`, `placement.vm`, `aios.workflows`, `aios.worlds`,
# `aios.models` and `aios.policy.guard` (spec §8); the rendering carries their
# empty maps so the parser's shape (pkgs/aiosd/src/declaration.rs) is met.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.aios;
  jsonFormat = pkgs.formats.json { };
  seatBasketPairs = lib.flatten (
    lib.mapAttrsToList (
      seat: s:
      map (b: {
        inherit seat;
        basket = b;
      }) s.baskets
    ) cfg.seats
  );
  declaration = {
    version = 1;
    vms = { };
    seats = lib.mapAttrs (_: s: {
      inherit (s)
        harness
        role
        baskets
        egress
        ;
      placement = {
        unit = { };
      };
    }) cfg.seats;
    workflows = { };
    worlds = { };
    egress = lib.mapAttrs (_: e: {
      inherit (e) listenPort allow;
    }) config.services.egress-broker.instances;
    policy = {
      guard = [ ];
      classes = lib.mapAttrs (_: d: {
        inherit (d) classification mount;
      }) config.services.baskets.definitions;
    };
  };
in
{
  imports = [
    ./basketStore.nix
    ./egressBroker.nix
    (lib.mkAliasOptionModule [ "aios" "data" ] [ "services" "baskets" "definitions" ])
    (lib.mkAliasOptionModule [ "aios" "egress" ] [ "services" "egress-broker" "instances" ])
  ];

  options.aios = {
    seats = lib.mkOption {
      default = { };
      description = "Seats: a harness placed in a unit, reading only its declared aios.data classes through its declared aios.egress instance (spec §4).";
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            harness = lib.mkOption {
              type = lib.types.enum [
                "claude-code"
                "dsh"
                "codex"
              ];
            };
            role = lib.mkOption { type = lib.types.str; };
            baskets = lib.mkOption {
              type = lib.types.listOf lib.types.str;
              default = [ ];
              description = "The aios.data classes this seat reads — class names and nothing else (invariant 8).";
            };
            egress = lib.mkOption {
              type = lib.types.str;
              description = "The aios.egress instance that is this seat's only route (invariant 3).";
            };
            placement = lib.mkOption {
              default = { };
              description = "Where the seat runs: `unit = { }` (a systemd unit on the host); `vm` is plan B's.";
              type = lib.types.submodule {
                options.unit = lib.mkOption {
                  type = lib.types.submodule { };
                  default = { };
                };
              };
            };
          };
        }
      );
    };
    declaration = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      description = "aios.json — the rendered declaration, a store path; what aiosd reads and nothing else.";
    };
  };

  config = {
    aios.declaration = jsonFormat.generate "aios.json" declaration;

    # A seat is an agent to basketStore: its A1-A4 assertions (the basket
    # exists, local-only never reaches an off-box route, the broker instance
    # exists, mounts are unique) apply unchanged.
    services.baskets.agents = lib.mapAttrs (_: s: {
      inherit (s) baskets;
      egress = "broker:${s.egress}";
      placement = "bubblewrap";
    }) cfg.seats;

    assertions =
      # I8-1: every entry of a seat's baskets list is a declared class — a
      # path, a mount point or any other spelling is refused by name.
      map (p: {
        assertion = config.services.baskets.definitions ? ${p.basket};
        message = "aios.seats.${p.seat}.baskets names '${p.basket}', which is not a declared aios.data class — a seat reads only the classes declared for it (brief §3 invariant 8)";
      }) seatBasketPairs
      # I8-2: the seat's egress names a declared instance (its only route).
      ++ lib.mapAttrsToList (seat: s: {
        assertion = config.services.egress-broker.instances ? ${s.egress};
        message = "aios.seats.${seat}.egress names '${s.egress}', which is not a declared aios.egress instance (brief §3 invariant 3)";
      }) cfg.seats;
  };
}
