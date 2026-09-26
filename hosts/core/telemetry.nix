_:
# SP3 (plan 2026-09-08-spend-telemetry): Claude Code's OpenTelemetry through a
# loopback collector that keeps an allowlist of attributes on every data point
# and record, with the exporter variables in an env-only managed-settings
# file. The loopback receiver and the drop-the-identity allowlist only reach
# the live broker here at switch #23.
{
  services.claude-telemetry.enable = true;
}
