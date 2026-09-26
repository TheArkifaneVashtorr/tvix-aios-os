# usage-ingest: a system oneshot + hourly timer that merges the seat broker's
# usage.jsonl into the evidence store (EV1). The evidence CLI is the one the
# evidenceStore module declares; the ingest reads the broker's log locally and
# writes only the local store (invariant 3), so the unit runs no network.
{
  config,
  lib,
  ...
}:
let
  cfg = config.services.usage-ingest;
  evidence = config.services.evidence-store.package;
in
{
  options.services.usage-ingest = {
    enable = lib.mkEnableOption "the hourly usage-ingest timer (merges the seat broker's usage.jsonl into the evidence store)";
    onCalendar = lib.mkOption {
      type = lib.types.str;
      default = "hourly";
      description = "systemd OnCalendar for the usage-ingest timer.";
    };
    store = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/evidence";
      description = "The evidence store the ingest writes.";
    };
    source = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/egress-broker/seat/usage.jsonl";
      description = "The broker usage.jsonl the ingest reads.";
    };
    user = lib.mkOption {
      type = lib.types.str;
      default = "dalhaka";
      description = "The user the oneshot service runs as.";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.usage-ingest = {
      description = "usage-ingest: merge the seat broker's usage.jsonl into the evidence store";
      # Skipped (never failed) while the broker has written nothing yet.
      unitConfig.ConditionPathExists = cfg.source;
      serviceConfig = {
        Type = "oneshot";
        User = cfg.user;
        ExecStart = "${evidence}/bin/evidence --store ${cfg.store} ingest openrouter-usage ${cfg.source}";
        ProtectSystem = "strict";
        ReadWritePaths = [ cfg.store ];
        UMask = "0027";
        PrivateTmp = true;
        NoNewPrivileges = true;
      };
    };
    systemd.timers.usage-ingest = {
      description = "usage-ingest: hourly broker-usage ingest";
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = cfg.onCalendar;
        Persistent = true;
      };
    };
  };
}
