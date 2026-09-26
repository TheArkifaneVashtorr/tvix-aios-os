{
  pkgs,
  claudeTelemetryModule,
  evidenceStoreModule,
}:
let
  # Assumption 11's shape, in stdlib: OTLP/HTTP JSON POSTs to /v1/metrics and
  # /v1/logs. The five identity keys are planted on the RESOURCE, on the
  # claude_code.token.usage DATA POINT, and on an api_request LOG RECORD --
  # plus a user_prompt record carrying a prompt -- so the transform allowlist
  # (resource/datapoint/log contexts) and the filter/events processor are the
  # ONLY thing standing between those keys and disk.
  probe = pkgs.writeText "telemetry-vm-probe.py" ''
    import json
    import urllib.request

    def attr(k, v):
        if isinstance(v, bool):
            val = {"boolValue": bool(v)}
        elif isinstance(v, int):
            val = {"intValue": str(v)}
        elif isinstance(v, float):
            val = {"doubleValue": v}
        else:
            val = {"stringValue": str(v)}
        return {"key": k, "value": val}

    IDENTITY = ["organization.id", "user.account_uuid", "user.id", "user.email", "user.name"]

    def identity():
        return [attr(k, k + "-secret") for k in IDENTITY]

    def common_resource():
        return identity() + [
            attr("service.name", "claude-code"),
            attr("service.version", "2.1.258"),
            attr("os.type", "linux"),
            attr("host.arch", "amd64"),
        ]

    def post(path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:4318" + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()

    # /v1/metrics: one claude_code.token.usage sum, data point carrying the
    # identity keys plus type/model/session.id and an asDouble value.
    point_attrs = identity() + [
        attr("type", "cacheRead"),
        attr("model", "claude-fable-5-1"),
        attr("session.id", "sess-x"),
    ]
    metrics = {
        "resourceMetrics": [
            {
                "resource": {"attributes": common_resource()},
                "scopeMetrics": [
                    {
                        "scope": {"name": "com.anthropic.claude_code"},
                        "metrics": [
                            {
                                "name": "claude_code.token.usage",
                                "unit": "1",
                                "sum": {
                                    "dataPoints": [
                                        {
                                            "attributes": point_attrs,
                                            "timeUnixNano": "1750000000000000000",
                                            "asDouble": 1234.0,
                                        }
                                    ],
                                    "aggregationTemporality": 2,
                                    "isMonotonic": False,
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }
    post("/v1/metrics", metrics)

    # /v1/logs: an api_request record (kept) and a user_prompt record carrying
    # a prompt attribute (dropped). The api_request record also carries every
    # identity key, so the log-context allowlist is what strips them.
    api_request_attrs = identity() + [
        attr("event.name", "api_request"),
        attr("model", "claude-fable-5-1"),
        attr("cost_usd", 0.001),
        attr("input_tokens", 2),
        attr("request_id", "req_x"),
        attr("session.id", "sess-x"),
    ]
    logs = {
        "resourceLogs": [
            {
                "resource": {"attributes": common_resource()},
                "scopeLogs": [
                    {
                        "scope": {"name": "com.anthropic.claude_code.events"},
                        "logRecords": [
                            {
                                "timeUnixNano": "1750000000000000000",
                                "severityNumber": 9,
                                "body": {"stringValue": "api_request"},
                                "attributes": api_request_attrs,
                            },
                            {
                                "timeUnixNano": "1750000000000000001",
                                "severityNumber": 9,
                                "body": {"stringValue": "SECRET PROMPT CONTENT"},
                                "attributes": [
                                    attr("event.name", "user_prompt"),
                                    attr("prompt", "SECRET PROMPT CONTENT"),
                                ],
                            },
                        ],
                    }
                ],
            }
        ]
    }
    post("/v1/logs", logs)
  '';
in
pkgs.testers.runNixOSTest {
  name = "claude-telemetry-loopback-collector";
  nodes.machine =
    { ... }:
    {
      imports = [
        claudeTelemetryModule
        evidenceStoreModule
      ];
      services.claude-telemetry.enable = true;
      users.users.dalhaka = {
        isNormalUser = true;
        uid = 1000;
      };
      environment.systemPackages = [
        # `ss` for the loopback-port assertions below (same as seat-vm).
        pkgs.iproute2
      ];
    };
  testScript = ''
    machine.wait_for_unit("opentelemetry-collector.service")
    machine.wait_for_open_port(4318)
    machine.succeed("${pkgs.python3}/bin/python3 ${probe}")
    machine.wait_until_succeeds("test -s /var/lib/opentelemetry-collector/claude-metrics.jsonl")
    machine.wait_until_succeeds("test -s /var/lib/opentelemetry-collector/claude-logs.jsonl")
    machine.succeed("grep -q -F '\"cacheRead\"' /var/lib/opentelemetry-collector/claude-metrics.jsonl")
    machine.succeed("grep -q -F 'api_request' /var/lib/opentelemetry-collector/claude-logs.jsonl")
    machine.succeed("grep -q -F 'sess-x' /var/lib/opentelemetry-collector/claude-logs.jsonl")
    for key in ["user.email", "user.id", "user.account_uuid", "organization.id", "user.name", "SECRET PROMPT", "user_prompt"]:
        machine.fail(f"grep -q -F '{key}' /var/lib/opentelemetry-collector/claude-metrics.jsonl /var/lib/opentelemetry-collector/claude-logs.jsonl")
    machine.succeed("ss -ltnH | grep -q '127.0.0.1:4318'")
    machine.fail("ss -ltnH | grep -q '0.0.0.0:4318'")
    machine.fail("ss -ltnH | grep -q ':4317'")
    machine.succeed("systemctl show opentelemetry-collector -p User --value | grep -qx dalhaka")
  '';
}
