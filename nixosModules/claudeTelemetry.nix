{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.claude-telemetry;

  # The collector writes its own StateDirectory (the module's unit keeps
  # StateDirectory = "opentelemetry-collector" under /var/lib), so this
  # literal is the one path both the file exporters and the hardening
  # (ReadWritePaths / InaccessiblePaths) agree on.
  stateDir = "/var/lib/opentelemetry-collector";

  # OTTL keep_keys(attributes, [...]) applied at the transform processor's
  # resource + datapoint (metrics) and resource + log (logs) contexts. The
  # identity attributes (organization.id, user.email, user.id,
  # user.account_uuid, user.name) are NONE of these -- an allowlist, not a
  # denylist, so an unlisted identity key is dropped before anything is
  # written to disk (Assumption 9c-d; prompt.id / prompt content never kept).
  keep = keys: "keep_keys(attributes, [${lib.concatMapStringsSep ", " (k: ''"${k}"'') keys}])";
  keepResource = [
    "service.name"
    "service.version"
    "os.type"
    "host.arch"
  ];
  keepPoint = [
    "session.id"
    "terminal.type"
    "type"
    "model"
    "query_source"
    "start_type"
  ];
  keepLog = [
    "event.name"
    "event.timestamp"
    "event.sequence"
    "session.id"
    "terminal.type"
    "model"
    "cost_usd"
    "cost_usd_micros"
    "duration_ms"
    "input_tokens"
    "output_tokens"
    "cache_read_tokens"
    "cache_creation_tokens"
    "request_id"
    "client_request_id"
    "speed"
    "query_source"
    "effort"
    "agent.name"
    "skill.name"
  ];

  settings = {
    receivers.otlp.protocols.http.endpoint = "127.0.0.1:${toString cfg.port}";
    processors = {
      "transform/allowlist" = {
        error_mode = "propagate";
        metric_statements = [
          {
            context = "resource";
            statements = [ (keep keepResource) ];
          }
          {
            context = "datapoint";
            statements = [ (keep keepPoint) ];
          }
        ];
        log_statements = [
          {
            context = "resource";
            statements = [ (keep keepResource) ];
          }
          {
            context = "log";
            statements = [ (keep keepLog) ];
          }
        ];
      };
      "filter/events" = {
        error_mode = "propagate";
        logs.log_record = [
          ''attributes["event.name"] != "api_request" and attributes["event.name"] != "api_error"''
        ];
      };
    };
    exporters = {
      "file/metrics" = {
        path = "${stateDir}/claude-metrics.jsonl";
        flush_interval = "1s";
        rotation = {
          max_megabytes = 64;
          max_backups = 8;
        };
      };
      "file/logs" = {
        path = "${stateDir}/claude-logs.jsonl";
        flush_interval = "1s";
        rotation = {
          max_megabytes = 64;
          max_backups = 8;
        };
      };
    };
    service = {
      telemetry.metrics.level = "none";
      pipelines = {
        metrics = {
          receivers = [ "otlp" ];
          processors = [ "transform/allowlist" ];
          exporters = [ "file/metrics" ];
        };
        logs = {
          receivers = [ "otlp" ];
          processors = [
            "transform/allowlist"
            "filter/events"
          ];
          exporters = [ "file/logs" ];
        };
      };
    };
  };
in
{
  options.services.claude-telemetry = {
    enable = lib.mkEnableOption "Claude Code's OpenTelemetry captured by a loopback collector into the evidence store";

    port = lib.mkOption {
      type = lib.types.port;
      default = 4318;
      description = ''
        Loopback port the collector's OTLP/HTTP receiver listens on, and the
        OTEL_EXPORTER_OTLP_ENDPOINT the generated managed-settings env points
        at. Loopback only (D5, question 3).
      '';
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = config.services.evidence-store.owner;
      description = ''
        User the collector unit runs as (its StateDirectory owner). Defaults
        to the evidence-store owner, so the files land daemons-visible.
      '';
    };

    env = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      readOnly = true;
      default = {
        CLAUDE_CODE_ENABLE_TELEMETRY = "1";
        OTEL_METRICS_EXPORTER = "otlp";
        OTEL_LOGS_EXPORTER = "otlp";
        OTEL_EXPORTER_OTLP_PROTOCOL = "http/json";
        OTEL_EXPORTER_OTLP_ENDPOINT = "http://127.0.0.1:${toString cfg.port}";
        OTEL_METRIC_EXPORT_INTERVAL = "5000";
        OTEL_LOGS_EXPORT_INTERVAL = "5000";
        OTEL_METRICS_INCLUDE_ACCOUNT_UUID = "false";
      };
      description = ''
        The exporter variables Claude Code's settings-file env block carries.
        An env-only block, not environment.sessionVariables: a settings env
        block drives the exporter and overrides the shell (Assumption 9a).
        No OTEL_LOG_* name is ever set -- those content switches stay off.
      '';
    };

    settingsFile = lib.mkOption {
      type = lib.types.path;
      readOnly = true;
      default = (pkgs.formats.json { }).generate "claude-code-telemetry-settings.json" {
        inherit (cfg) env;
      };
      description = ''
        The Claude-Code-scoped /etc/claude-code/managed-settings.json with an
        env-only block (the eight exporter variables above), generated with
        the same JSON format claudeManagedSettings.nix uses.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = !(config.services.claude-managed-settings.enable or false);
        message = "services.claude-telemetry and services.claude-managed-settings both write /etc/claude-code/managed-settings.json; enable one";
      }
    ];

    environment.etc."claude-code/managed-settings.json".source = cfg.settingsFile;

    services.opentelemetry-collector = {
      enable = true;
      package = pkgs.opentelemetry-collector-contrib;
      validateConfigFile = true;
      inherit settings;
    };

    systemd.services.opentelemetry-collector.serviceConfig = {
      DynamicUser = lib.mkForce false;
      User = cfg.user;
      SupplementaryGroups = lib.mkForce [ ];
      ProtectSystem = lib.mkForce "strict";
      ProtectHome = true;
      PrivateTmp = true;
      NoNewPrivileges = true;
      CapabilityBoundingSet = "";
      RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX";
      IPAddressDeny = "any";
      IPAddressAllow = "localhost";
      ReadWritePaths = [ stateDir ];
      InaccessiblePaths = [ "-/var/lib/evidence" ];
    };
  };
}
