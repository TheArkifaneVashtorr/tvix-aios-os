#!/usr/bin/env bats
# FA20: the batch tool (tools/factory/seat/factory-batch.py) drives the
# OpenRouter lane's batch endpoint in the grammar FA2 measured
# (docs/research-2026-09-11-batch-lane.md:84-131). The wire cases boot a
# fixture replay of those two exchanges against loopback -- no network, and
# no credential of any value. The lane-only refusal, the non-202 submit
# refusal, the terminal-status exits, the non-2xx GET, the error-result
# separation and the no-credential-on-the-wire rule are all shown to fail
# first (2026-09-14) against the missing tool, then pass.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
FIXTURE="$BATS_TEST_DIRNAME/fixtures/fa20-batch-server.py"
BATCH="$SEAT/factory-batch.py"

DEFAULT_ID="batch-1789094338-KsxdGYx0U4WjU5j0W5La"
MODEL="anthropic/claude-fable-5.1:batch"

bats_require_minimum_version 1.5.0

setup() {
  T="$BATS_TEST_TMPDIR"
  REQ_LOG="$T/req.log"
  # Unset everything that would leak a proxy or credential from the ambient
  # shell: the tool's refusal and the on-wire credential rule both read these.
  unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
  unset OPENROUTER_API_KEY AUTH_TOKEN FACTORY_BATCH_BASE
  # The fixture reads these as file paths (re-read per request); point them at
  # per-test scratch files so no test writes to the operator's environment.
  export FA20_REQ_LOG="$REQ_LOG"
  export FA20_SUBMIT_STATUS="$T/submit-status"
  export FA20_NEXT_ID="$T/next-id"
  python3 "$FIXTURE" --log "$REQ_LOG" >"$T/port" 2>"$T/fixture.err" &
  FIX_PID=$!
  local i
  for i in $(seq 1 100); do
    grep -q '^PORT=' "$T/port" 2>/dev/null && break
    sleep 0.1
  done
  PORT=$(sed -n 's/^PORT=//p' "$T/port")
  [ -n "$PORT" ]
  export FACTORY_BATCH_BASE="http://127.0.0.1:$PORT"
  : >"$T/req.json"
  printf '[{"custom_id":"fa2-probe-1","body":{"model":"%s","messages":[{"role":"user","content":"hi"}]}}]\n' \
    "$MODEL" >"$T/req.json"
}

teardown() {
  if [ -n "${FIX_PID:-}" ]; then
    kill "$FIX_PID" 2>/dev/null || true
    wait "$FIX_PID" 2>/dev/null || true
  fi
}

@test "submit prints id and validating status on 202" {
  run python3 "$BATCH" submit "$T/req.json" --model "$MODEL"
  [ "$status" -eq 0 ]
  [ "$output" = "$DEFAULT_ID validating" ]
}

@test "poll --until-terminal exits 0 and prints completed 1/1" {
  run python3 "$BATCH" poll "$DEFAULT_ID" --until-terminal --interval 0
  [ "$status" -eq 0 ]
  [ "$output" = "completed 1/1" ]
}

@test "a failed batch is terminal: --until-terminal and plain poll both exit 3" {
  run python3 "$BATCH" poll batch-fail --until-terminal --interval 0
  [ "$status" -eq 3 ]
  [ "$output" = "failed 0/1" ]
  run python3 "$BATCH" poll batch-fail
  [ "$status" -eq 3 ]
  [ "$output" = "failed 0/1" ]
}

@test "fetch writes the completed result and the batch object" {
  run python3 "$BATCH" fetch "$DEFAULT_ID" --out "$T/out"
  [ "$status" -eq 0 ]
  [ -f "$T/out/fa2-probe-1.json" ]
  [ -f "$T/out/batch.json" ]
  result_model=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["model"])' "$T/out/fa2-probe-1.json")
  [ "$result_model" = "$MODEL" ]
  usage_cost=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["usage"]["cost"])' "$T/out/batch.json")
  [ "$usage_cost" = "0.00039" ]
}

@test "a non-200 result is written as .error.json and fetch exits 3" {
  run python3 "$BATCH" fetch batch-429 --out "$T/out"
  [ "$status" -eq 3 ]
  [ -f "$T/out/rate-limited-probe.error.json" ]
  [ ! -e "$T/out/rate-limited-probe.json" ]
}

@test "submit exits 2 when the server answers 400" {
  printf '400\n' >"$T/submit-status"
  run python3 "$BATCH" submit "$T/req.json" --model "$MODEL"
  [ "$status" -eq 2 ]
  [[ "$output" == *"bad request"* ]]
}

@test "submit refuses when the base is the default and there is no lane proxy" {
  unset FACTORY_BATCH_BASE
  run python3 "$BATCH" submit "$T/req.json" --model "$MODEL"
  [ "$status" -eq 2 ]
  [[ "$output" == *"factory-batch: refusing -- no lane proxy in the environment (invariant 3)"* ]]
}

@test "submit sends no credential on the wire" {
  run env OPENROUTER_API_KEY=canary-7c1e AUTH_TOKEN=canary-7c1e \
    python3 "$BATCH" submit "$T/req.json" --model "$MODEL"
  [ "$status" -eq 0 ]
  run grep -i '^authorization:' "$REQ_LOG"
  [ "$status" -eq 1 ]
  run grep -F 'canary-7c1e' "$REQ_LOG"
  [ "$status" -eq 1 ]
}

@test "a non-2xx GET is not a batch status: poll exits 2 with or without --until-terminal" {
  run python3 "$BATCH" poll batch-nonesuch
  [ "$status" -eq 2 ]
  [[ "${lines[0]}" == "factory-batch: GET /api/beta/batches/batch-nonesuch -> 404" ]]
  run python3 "$BATCH" poll batch-nonesuch --until-terminal --interval 0
  [ "$status" -eq 2 ]
  [[ "${lines[0]}" == "factory-batch: GET /api/beta/batches/batch-nonesuch -> 404" ]]
}

@test "fetch refuses a traversal custom_id and writes nothing outside --out" {
  run python3 "$BATCH" fetch batch-traverse --out "$T/out"
  [ "$status" -eq 3 ]
  [[ "$output" == *"../../escaped"* ]]
  [ ! -e "$T/out/../../escaped.json" ]
  [ ! -e "$T/out/batch.json" ]
}

@test "fetch refuses an absolute custom_id and writes nothing" {
  run python3 "$BATCH" fetch batch-absolute --out "$T/out"
  [ "$status" -eq 3 ]
  [[ "$output" == *"/abs/escaped"* ]]
  [ ! -e "/abs/escaped.json" ]
  [ ! -e "$T/out/batch.json" ]
}

@test "poll retries a 503 and succeeds when the server recovers" {
  run python3 "$BATCH" poll batch-5xx --interval 0
  [ "$status" -eq 0 ]
  [ "$output" = "completed 1/1" ]
}

@test "poll --until-terminal exits 4 when a stalled batch times out" {
  run python3 "$BATCH" poll batch-stall --until-terminal --interval 0.1 --timeout 1
  [ "$status" -eq 4 ]
}

@test "poll and fetch refuse off the lane like submit" {
  unset FACTORY_BATCH_BASE
  run python3 "$BATCH" poll "$DEFAULT_ID"
  [ "$status" -eq 2 ]
  [[ "$output" == *"factory-batch: refusing -- no lane proxy in the environment (invariant 3)"* ]]
  run python3 "$BATCH" fetch "$DEFAULT_ID" --out "$T/out"
  [ "$status" -eq 2 ]
  [[ "$output" == *"factory-batch: refusing -- no lane proxy in the environment (invariant 3)"* ]]
}

@test "fetch refuses a custom_id carrying a trailing newline and writes nothing" {
  # FA20c case (a): re.match's `$` anchors before a trailing newline, so the
  # id "abc\n" slipped past CUSTOM_ID_RE and its write landed on a file whose
  # name embeds a newline. fullmatch must refuse it.
  run python3 "$BATCH" fetch batch-newline --out "$T/out"
  [ "$status" -eq 3 ]
  [[ "$output" == *"refusing result custom_id"* ]]
  [ ! -e "$T/out" ]
}

@test "fetch refuses an off-alphabet but contained custom_id (.hidden)" {
  # FA20c case (b): ".hidden" is one basename (no /, not ..), so the realpath
  # guard alone allows it; only CUSTOM_ID_RE refuses it. Dropping the regex
  # must turn this case red.
  run python3 "$BATCH" fetch batch-hidden --out "$T/out"
  [ "$status" -eq 3 ]
  [[ "$output" == *"refusing result custom_id"* ]]
  [ ! -e "$T/out/.hidden.json" ]
  [ ! -e "$T/out/batch.json" ]
}

@test "fetch refuses a symlink planted at the write path and leaves the target untouched" {
  # FA20c case (c): the id is benign (fa2-probe-1 passes CUSTOM_ID_RE), but a
  # symlink at <out>/fa2-probe-1.json points outside --out. The realpath guard
  # must refuse and leave the victim bytes alone; dropping it follows the
  # symlink and overwrites the victim.
  mkdir -p "$T/out"
  printf 'ORIGINAL\n' >"$T/victim"
  ln -s "$T/victim" "$T/out/fa2-probe-1.json"
  run python3 "$BATCH" fetch "$DEFAULT_ID" --out "$T/out"
  [ "$status" -eq 3 ]
  [[ "$output" == *"refusing result custom_id"* ]]
  grep -q '^ORIGINAL$' "$T/victim"
  [ ! -e "$T/out/batch.json" ]
}
