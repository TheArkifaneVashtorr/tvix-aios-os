#!/usr/bin/env bats
# SP9 (code, S): the otel-ingest timer unit. 69 MB of the collector's Claude
# telemetry sat undrained because the hourly timer lane only knew the broker's
# usage.jsonl, and rotation is the trap: a unit pointed at the live
# claude-metrics.jsonl alone silently drops every rotated -size.jsonl sibling.
# The behavioral cases run the module's REAL ingest payload -- the '' block
# nixosModules/otelIngest.nix binds to writeShellScript and ExecStart runs --
# against a fake sourceDir, with the test's store and tree's evidence.py
# substituted for the module's Nix interpolations. The structural cases pin
# the unit's shape on the module's text. Proxies and their gaps (decision
# 2026-09-03-test-based-reality-amendments): (1) the payload runs substituted
# paths, not the store-path ExecStart systemd would run -- the quoting and the
# packaged CLI are host-core's eval job, and the substitution seam is exactly
# the module's three interpolations; (2) bats cannot run systemd, so the
# ConditionPathExistsGlob skip and the timer cadence are asserted on the
# module's text, not by watching a unit skip. M5 (no network) is by
# inspection: the payload's only command is the evidence CLI, and the module
# text carries no fetch.

MODULE="$BATS_TEST_DIRNAME/../../nixosModules/otelIngest.nix"
EVIDENCE="$BATS_TEST_DIRNAME/../../pkgs/evidence/evidence.py"
RUNBOOK="$BATS_TEST_DIRNAME/../../docs/runbooks/evidence.md"

setup() {
  bats_require_minimum_version 1.5.0
  SRC="$BATS_TEST_TMPDIR/collector"
  STORE="$BATS_TEST_TMPDIR/store"
  mkdir -p "$SRC"
}

# One claude_code.token.usage data point (session $1, nanoseconds $2) in
# OTLP-JSON export shape -- an invented fixture (record §15), modelled on the
# measured wire shape, not on any real session.
metrics_line() {
  printf '{"resourceMetrics":[{"resource":{"attributes":[{"key":"service.version","value":{"stringValue":"2.1.258"}}]},"scopeMetrics":[{"scope":{"name":"com.anthropic.claude_code"},"metrics":[{"name":"claude_code.token.usage","unit":"1","sum":{"dataPoints":[{"attributes":[{"key":"type","value":{"stringValue":"input"}},{"key":"model","value":{"stringValue":"claude-opus-5"}},{"key":"session.id","value":{"stringValue":"%s"}}],"timeUnixNano":"%s","asInt":"17584"}]}}]}]}]}\n' "$1" "$2"
}

# One api_request log record (session $1, request $2, nanoseconds $3).
logs_line() {
  printf '{"resourceLogs":[{"resource":{"attributes":[{"key":"service.version","value":{"stringValue":"2.1.258"}}]},"scopeLogs":[{"scope":{"name":"com.anthropic.claude_code.events"},"logRecords":[{"attributes":[{"key":"event.name","value":{"stringValue":"api_request"}},{"key":"session.id","value":{"stringValue":"%s"}},{"key":"request_id","value":{"stringValue":"%s"}},{"key":"model","value":{"stringValue":"claude-opus-5"}}],"timeUnixNano":"%s"}]}]}]}\n' "$1" "$2" "$3"
}

# The same api_request record carrying user.email -- the identity attribute
# the otel-claude validator refuses (Interface 4).
identity_line() {
  printf '{"resourceLogs":[{"resource":{"attributes":[{"key":"service.version","value":{"stringValue":"2.1.258"}}]},"scopeLogs":[{"scope":{"name":"com.anthropic.claude_code.events"},"logRecords":[{"attributes":[{"key":"event.name","value":{"stringValue":"api_request"}},{"key":"session.id","value":{"stringValue":"%s"}},{"key":"request_id","value":{"stringValue":"%s"}},{"key":"model","value":{"stringValue":"claude-opus-5"}},{"key":"user.email","value":{"stringValue":"who@example.net"}}],"timeUnixNano":"%s"}]}]}]}\n' "$1" "$2" "$3"
}

# The ingest payload between the module's two '' markers: the same bash the
# unit's ExecStart runs (writeShellScript embeds this block verbatim). The
# dots stand in for the quote characters so the awk program needs no quote
# literal of its own.
payload_of() {
  awk '
    /ingestPayload = ..$/ { grab = 1; next }
    grab && /^  ..;$/ { exit }
    grab { print }
  ' "$MODULE"
}

# The payload with the module's three Nix interpolations replaced by this
# test's values -- the source dir ($1), the store, and the tree's evidence.py
# in place of the packaged CLI. Fails (rather than skips) when the module or
# its payload is missing, so a deleted or renamed block is a red test, not a
# silent pass.
render_payload() {
  local p src_marker store_marker cli_marker cli_cmd
  p="$(payload_of)" || return 1
  [ -n "$p" ] || return 1
  src_marker='${cfg.sourceDir}'
  store_marker='${cfg.store}'
  cli_marker='"${evidence}/bin/evidence"'
  cli_cmd="python3 $EVIDENCE"
  p="${p//$src_marker/$1}"
  p="${p//$store_marker/$STORE}"
  p="${p//$cli_marker/$cli_cmd}"
  printf '%s\n' "$p"
}

# The number of rows in the stream file $1 whose session_id is $2.
session_count() {
  jq -se --arg s "$2" '[.[] | select(.session_id == $s)] | length' "$1"
}

@test "every claude-*.jsonl under the source dir is ingested, live and rotated alike (Interface 1, M1)" {
  metrics_line sess-live 1788906253213778862 >"$SRC/claude-metrics.jsonl"
  logs_line sess-rot req-rot 1788906253213778863 >"$SRC/claude-logs-2026-09-21T08-29-54.995-size.jsonl"
  PAYLOAD="$(render_payload "$SRC")" || return 1
  run bash -c "$PAYLOAD"
  [ "$status" -eq 0 ]
  grep -qF 'ingested 2 rows into ledger/otel-claude (0 refused, 0 skipped)' <<<"$output"
  [ "$(wc -l <"$STORE/ledger/otel-claude.jsonl")" -eq 2 ]
  [ "$(session_count "$STORE/ledger/otel-claude.jsonl" sess-live)" -eq 1 ]
  [ "$(session_count "$STORE/ledger/otel-claude.jsonl" sess-rot)" -eq 1 ]
}

@test "a tick run twice, and the same rows under a second filename, write no second copy (Interface 2, M2)" {
  metrics_line sess-once 1788906253213778862 >"$SRC/claude-metrics.jsonl"
  PAYLOAD="$(render_payload "$SRC")" || return 1
  run bash -c "$PAYLOAD"
  [ "$status" -eq 0 ]
  [ "$(wc -l <"$STORE/ledger/otel-claude.jsonl")" -eq 1 ]
  # The same tick again: the (session_id, sample_id) key upserts, so the row
  # count does not move.
  run bash -c "$PAYLOAD"
  [ "$status" -eq 0 ]
  [ "$(wc -l <"$STORE/ledger/otel-claude.jsonl")" -eq 1 ]
  # The same rows under a second (rotated-shaped) name: still one copy -- the
  # key does the dedup, never the path.
  cp "$SRC/claude-metrics.jsonl" "$SRC/claude-metrics-2026-09-21T08-29-54.995-size.jsonl"
  run bash -c "$PAYLOAD"
  [ "$status" -eq 0 ]
  [ "$(wc -l <"$STORE/ledger/otel-claude.jsonl")" -eq 1 ]
  [ "$(session_count "$STORE/ledger/otel-claude.jsonl" sess-once)" -eq 1 ]
}

@test "an empty source dir skips rather than fails (Interface 1, M3)" {
  PAYLOAD="$(render_payload "$SRC")" || return 1
  run bash -c "$PAYLOAD"
  [ "$status" -eq 0 ]
  [ "$output" = "" ]
  [ ! -e "$STORE/ledger/otel-claude.jsonl" ]
}

@test "a rotated claude-metrics-…-size.jsonl sibling alone still reaches the store (rotation control, M1)" {
  metrics_line sess-mrot 1788906253213778862 >"$SRC/claude-metrics-2026-09-21T08-29-54.995-size.jsonl"
  PAYLOAD="$(render_payload "$SRC")" || return 1
  run bash -c "$PAYLOAD"
  [ "$status" -eq 0 ]
  grep -qF 'ingested 1 rows into ledger/otel-claude (0 refused, 0 skipped)' <<<"$output"
  [ "$(session_count "$STORE/ledger/otel-claude.jsonl" sess-mrot)" -eq 1 ]
}

@test "an identity attribute is refused, the rest of the file still lands, and the tick exits 0 (Interface 4, M4)" {
  identity_line sess-id req-id 1788906253213778862 >"$SRC/claude-logs.jsonl"
  logs_line sess-ok req-ok 1788906253213778863 >>"$SRC/claude-logs.jsonl"
  PAYLOAD="$(render_payload "$SRC")" || return 1
  run bash -c "$PAYLOAD"
  [ "$status" -eq 0 ]
  grep -qF 'identity attribute present' <<<"$output"
  grep -qF 'ingested 1 rows into ledger/otel-claude (1 refused, 0 skipped)' <<<"$output"
  [ "$(session_count "$STORE/ledger/otel-claude.jsonl" sess-ok)" -eq 1 ]
  [ "$(session_count "$STORE/ledger/otel-claude.jsonl" sess-id)" -eq 0 ]
}

@test "the unit's ExecStart is the writeShellScript of the ingest payload the cases above run" {
  grep -qF 'otelIngestScript = pkgs.writeShellScript "otel-ingest" ingestPayload' "$MODULE"
  grep -qF 'ExecStart = "${otelIngestScript}"' "$MODULE"
}

@test "the unit globs claude-*.jsonl and never pins the live filenames (M1)" {
  grep -qF 'claude-*.jsonl' "$MODULE"
  run ! grep -F 'claude-metrics.jsonl"' "$MODULE"
  run ! grep -F 'claude-logs.jsonl"' "$MODULE"
}

@test "the unit skips, never fails, while the collector has written nothing (M3)" {
  grep -qF 'ConditionPathExistsGlob = "${cfg.sourceDir}/claude-*.jsonl"' "$MODULE"
}

@test "the module carries no fetch: no egress path beyond the local ingest (invariant 3, M5)" {
  # The file check first: a missing module must fail this case, not pass it
  # vacuously through run ! grep's status inversion.
  [ -f "$MODULE" ]
  run ! grep -E 'curl|wget|https?://' "$MODULE"
}

@test "the unit keeps usage-ingest's hardening, timer shape and defaults" {
  local marker
  for marker in \
    'Type = "oneshot"' \
    'ProtectSystem = "strict"' \
    'ReadWritePaths = [ cfg.store ]' \
    'UMask = "0027"' \
    'PrivateTmp = true' \
    'NoNewPrivileges = true' \
    'wantedBy = [ "timers.target" ]' \
    'Persistent = true' \
    'default = "/var/lib/opentelemetry-collector"' \
    'default = "/var/lib/evidence"' \
    'default = "hourly"'; do
    grep -qF "$marker" "$MODULE" || return 1
  done
}

@test "the user option carries no hard-coded default (the host must set it)" {
  local block
  block="$(sed -n '/^    user = lib.mkOption {/,/^    };/p' "$MODULE")"
  [ -n "$block" ]
  ! grep -qF 'default =' <<< "$block"
}

@test "the runbook documents the otel-ingest timer, the rotation rule and the measured backfill" {
  grep -q '^## The otel-ingest timer$' "$RUNBOOK"
  grep -qF 'ingested 143635 rows into ledger/otel-claude (0 refused, 33559 skipped)' "$RUNBOOK"
  grep -qF 'size.jsonl' "$RUNBOOK"
}
