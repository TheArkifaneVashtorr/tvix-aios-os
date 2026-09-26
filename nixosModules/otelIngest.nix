# otel-ingest: a system oneshot + hourly timer that merges the collector's
# Claude telemetry into the evidence store (SP9, plan
# 2026-09-08-spend-telemetry). Modelled on usageIngest.nix with one difference
# that matters: the collector ROTATES its files
# (claude-metrics-2026-09-21T08-29-54.995-size.jsonl beside the live
# claude-metrics.jsonl), so the unit ingests every claude-*.jsonl under
# sourceDir -- live and rotated alike. Re-reading is safe and intended:
# ledger/otel-claude is keyed (session_id, sample_id), so a rotated file read
# again on every tick adds nothing. The unit reads the collector's local files
# and writes only the local store (brief §3 invariant 3), so it runs no
# network.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.otel-ingest;
  evidence = config.services.evidence-store.package;
  # The payload ExecStart runs (writeShellScript embeds it verbatim; the unit
  # tests extract this same '' block and run it against a fake sourceDir).
  # bash does the globbing (systemd does not): every claude-*.jsonl under the
  # source dir reaches ONE evidence call, so a rotation never strands a file,
  # and an empty source dir exits 0 rather than failing on an empty argument
  # list. A refusal (evidence exits 1 -- an identity attribute the
  # otel-claude validator refused, say) is journaled, not unit-fatal: the
  # hourly unit stays green while the refusal line still reaches the journal,
  # and evidence exits >= 2 (a usage error, a path outside the root) does fail
  # the unit.
  ingestPayload = ''
    set --
    for f in "${cfg.sourceDir}"/claude-*.jsonl; do
      [ -f "$f" ] && set -- "$@" "$f"
    done
    [ $# -eq 0 ] && exit 0
    "${evidence}/bin/evidence" --store "${cfg.store}" ingest otel --root "${cfg.sourceDir}" "$@"
    rc=$?
    [ "$rc" -le 1 ] && exit 0
    exit "$rc"
  '';
  otelIngestScript = pkgs.writeShellScript "otel-ingest" ingestPayload;
in
{
  options.services.otel-ingest = {
    enable = lib.mkEnableOption "the hourly otel-ingest timer (merges the collector's Claude telemetry into the evidence store)";
    onCalendar = lib.mkOption {
      type = lib.types.str;
      default = "hourly";
      description = "systemd OnCalendar for the otel-ingest timer.";
    };
    store = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/evidence";
      description = "The evidence store the ingest writes.";
    };
    sourceDir = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/opentelemetry-collector";
      description = "The collector directory whose claude-*.jsonl files (live and rotated alike) the ingest reads.";
    };
    user = lib.mkOption {
      type = lib.types.str;
      description = "The user the oneshot service runs as. No default: the host must set it.";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.services.otel-ingest = {
      description = "otel-ingest: merge the collector's Claude telemetry into the evidence store";
      # Skipped (never failed) while the collector has written nothing yet:
      # the glob matches no file, live or rotated.
      unitConfig.ConditionPathExistsGlob = "${cfg.sourceDir}/claude-*.jsonl";
      serviceConfig = {
        Type = "oneshot";
        User = cfg.user;
        ExecStart = "${otelIngestScript}";
        ProtectSystem = "strict";
        ReadWritePaths = [ cfg.store ];
        UMask = "0027";
        PrivateTmp = true;
        NoNewPrivileges = true;
      };
    };
    systemd.timers.otel-ingest = {
      description = "otel-ingest: hourly collector-telemetry ingest";
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = cfg.onCalendar;
        Persistent = true;
      };
    };
  };
}
