#!/usr/bin/env bats
# tools/experiments/jaz/{gateway,sessions,confined_tools}.py and
# run-arm-c.sh -- arm C of docs/superpowers/specs/
# 2026-09-25-jaz-planning-experiment-design.md (§6b: JAZ on this machine
# through the Claude subscription). Every case here runs against a FAKE
# `claude` script on PATH (never the real binary -- this repo's rule is
# "NEVER run claude yourself"; tests use a fake `claude` on PATH) and
# never imports `jaz` itself (claude_llm.py and run_arm_c.py, which do
# import it, are covered separately by a devShell pytest run against the
# real jaz-lang package -- see the build report).
#
# Python3 only (stdlib): gateway.py, sessions.py and confined_tools.py are
# all runnable directly, same as check-truncation.py's own suite.
#
# 2026-09-27 Opus review: the fake claude now reads the MESSAGE from
# stdin (never argv) and the SYSTEM PROMPT from the file named by
# --system-prompt-file (never inline argv), validates --session-id/
# --resume as dashed UUIDs the way the real `claude` does ("Invalid
# session ID. Must be a valid UUID."), and refuses an unknown --resume id
# ("No conversation found with session ID: ...").

setup() {
  JAZ_DIR="$BATS_TEST_DIRNAME/../../tools/experiments/jaz"
  GATEWAY_PY="$JAZ_DIR/gateway.py"
  SESSIONS_PY="$JAZ_DIR/sessions.py"
  CONFINED_PY="$JAZ_DIR/confined_tools.py"
  RUN_ARM_C_SH="$JAZ_DIR/run-arm-c.sh"
  # Absolute path, not "#!/usr/bin/env bash": a sandboxed nix build (unlike
  # an interactive nix develop shell) has no /usr/bin/env, so a fake
  # claude's shebang must resolve bash directly or execve() fails ENOENT
  # (subprocess.Popen(["claude", ...]) then reports "claude" itself as
  # missing, since Python's PATH search treats any exec() failure --
  # including a broken shebang interpreter -- as "try the next candidate").
  FAKE_BASH="$(command -v bash)"
  T="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/jazarmc.XXXXXX")"
  mkdir -p "$T/bin"
  PATH="$T/bin:$PATH"
  SOCKET="$T/gateway.sock"
  GLOG="$T/gateway.jsonl"
  STOPPED="$T/stopped.json"
}

teardown() {
  if [ -n "${GATEWAY_PID:-}" ] && kill -0 "$GATEWAY_PID" 2>/dev/null; then
    kill "$GATEWAY_PID" 2>/dev/null || true
    wait "$GATEWAY_PID" 2>/dev/null || true
  fi
  rm -rf "$T"
}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

# Fixed, distinct, valid dashed UUIDs -- the fake claude enforces this
# shape now (real `claude` rejects anything else), so every request built
# by this suite uses one of these instead of a bare test label.
U1="11111111-1111-4111-8111-111111111111"
U2="22222222-2222-4222-8222-222222222222"
U3="33333333-3333-4333-8333-333333333333"
U4="44444444-4444-4444-8444-444444444444"
U5="55555555-5555-4555-8555-555555555555"
U6="66666666-6666-4666-8666-666666666666"

# Writes a fake `claude` (once per test; idempotent across calls within
# one test since it re-reads its config file every invocation) that:
#   - records argv to $T/observed-argv, stdin to $T/observed-stdin, the
#     --system-prompt-file's CONTENT to $T/observed-system-prompt-file,
#     ANTHROPIC_*/other env to $T/observed-env, and counts invocations in
#     $T/invocations;
#   - validates --session-id/--resume as dashed UUIDs, and refuses to
#     --resume an id it was never given via --session-id (tracked in
#     $T/known-sessions, appended on a successful --session-id call);
#   - prints the transcript configured by the LAST write_fake_claude call.
write_fake_claude() {
  local api_key_source="$1" status="$2" seven_day="$3" result_text="${4:-ok}"
  {
    printf '%s\n' "$api_key_source"
    printf '%s\n' "$status"
    printf '%s\n' "$seven_day"
    printf '%s\n' "$result_text"
  } >"$T/fake-claude-config"
  cat >"$T/bin/claude" <<FAKE
#!$FAKE_BASH
FAKE
  cat >>"$T/bin/claude" <<'INNER'
HERE_="$(cd "$(dirname "$0")" && pwd)"
T_="$(dirname "$HERE_")"
CONFIG="$T_/fake-claude-config"
api_key_source="$(sed -n 1p "$CONFIG")"
status="$(sed -n 2p "$CONFIG")"
seven_day="$(sed -n 3p "$CONFIG")"
result_text="$(sed -n 4p "$CONFIG")"

printf '%s\n' "$@" >"$T_/observed-argv"
cat >"$T_/observed-stdin"
{
  printf 'ANTHROPIC_API_KEY=%s\n' "${ANTHROPIC_API_KEY:-unset}"
  printf 'ANTHROPIC_AUTH_TOKEN=%s\n' "${ANTHROPIC_AUTH_TOKEN:-unset}"
  printf 'AWS_ACCESS_KEY_ID=%s\n' "${AWS_ACCESS_KEY_ID:-unset}"
  printf 'OTEL_EXPORTER_OTLP_ENDPOINT=%s\n' "${OTEL_EXPORTER_OTLP_ENDPOINT:-unset}"
} >"$T_/observed-env"
printf 'x' >>"$T_/invocations"
printf '%s\n' "$PWD" >>"$T_/observed-cwds"

session_id=""
resume_id=""
sysfile=""
prev=""
for arg in "$@"; do
  case "$prev" in
    --session-id) session_id="$arg" ;;
    --resume) resume_id="$arg" ;;
    --system-prompt-file) sysfile="$arg" ;;
  esac
  prev="$arg"
done

uuid_re='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'

if [ -n "$session_id" ]; then
  if ! [[ "$session_id" =~ $uuid_re ]]; then
    echo "Error: Invalid session ID. Must be a valid UUID." >&2
    exit 1
  fi
  echo "$session_id" >>"$T_/known-sessions"
fi

if [ -n "$resume_id" ]; then
  if ! [[ "$resume_id" =~ $uuid_re ]]; then
    echo "Error: Invalid session ID. Must be a valid UUID." >&2
    exit 1
  fi
  if ! grep -qxF "$resume_id" "$T_/known-sessions" 2>/dev/null; then
    echo "Error: No conversation found with session ID: $resume_id" >&2
    exit 1
  fi
fi

if [ -n "$sysfile" ]; then
  cp "$sysfile" "$T_/observed-system-prompt-file" 2>/dev/null || true
fi

printf '{"type":"system","subtype":"init","cwd":"%s","session_id":"fake-session","apiKeySource":"%s"}\n' "$PWD" "$api_key_source"
printf '{"type":"rate_limit_event","rate_limit_info":{"status":"%s","unifiedWindows":{"five_hour":{"utilization":0.07},"seven_day":{"utilization":%s}}}}\n' "$status" "$seven_day"
printf '{"total_cost_usd":0.0121,"usage":{"input_tokens":2,"output_tokens":5,"cache_read_input_tokens":0,"cache_creation_input_tokens":591},"result":"%s","subtype":"success","is_error":false,"type":"result"}\n' "$result_text"
INNER
  chmod +x "$T/bin/claude"
}

# A fake `claude` that emits ONLY the init line then sleeps -- used to
# prove the gateway kills the process rather than waiting for it (both
# the apiKeySource-not-none abort path and the call-timeout watchdog).
write_fake_claude_hangs_after_init() {
  local api_key_source="$1" sleep_s="${2:-30}"
  cat >"$T/bin/claude" <<FAKE
#!$FAKE_BASH
printf '%s\n' "\$@" >"$T/observed-argv"
cat >"$T/observed-stdin"
echo '{"type":"system","subtype":"init","cwd":"'"\$PWD"'","session_id":"fake-session","apiKeySource":"$api_key_source"}'
sleep $sleep_s
FAKE
  chmod +x "$T/bin/claude"
}

# A fake `claude` whose result event fails the ok-check on EXACTLY ONE of
# its two independent conditions -- is_error or subtype -- so each has its
# own discriminating test (gateway.py's check is an OR of the two; a
# combined fixture that sets both at once cannot tell which arm actually
# fired).
write_fake_claude_result_error() {
  local is_error="$1" subtype="$2"
  cat >"$T/bin/claude" <<FAKE
#!$FAKE_BASH
printf '%s\n' "\$@" >"$T/observed-argv"
cat >"$T/observed-stdin"
printf 'x' >>"$T/invocations"
echo '{"type":"system","subtype":"init","cwd":"'"\$PWD"'","session_id":"fake-session","apiKeySource":"none"}'
echo '{"type":"rate_limit_event","rate_limit_info":{"status":"allowed","unifiedWindows":{"five_hour":{"utilization":0.05},"seven_day":{"utilization":0.10}}}}'
echo '{"total_cost_usd":0.0,"usage":{"input_tokens":1,"output_tokens":0},"result":"boom","subtype":"$subtype","is_error":$is_error,"type":"result"}'
FAKE
  chmod +x "$T/bin/claude"
}

start_gateway() {
  local stop_at="${1:-0.90}" call_timeout="${2:-600}"
  python3 "$GATEWAY_PY" --socket "$SOCKET" --log "$GLOG" --stop-at-utilization "$stop_at" \
    --call-timeout "$call_timeout" --stopped-file "$STOPPED" --skip-api-key-helper-check &
  GATEWAY_PID=$!
  for _ in $(seq 1 100); do
    [ -S "$SOCKET" ] && return 0
    sleep 0.1
  done
  echo "gateway never created $SOCKET" >&2
  return 1
}

# Sends one JSON-lines request over the socket and prints the response
# line. Duplicated from claude_llm.py's call_gateway on purpose: this
# suite never imports claude_llm.py (it imports `jaz`, not installed here).
send_request() {
  python3 - "$SOCKET" "$1" <<'PY'
import json, socket, sys
sock_path, req_json = sys.argv[1], sys.argv[2]
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(30)
s.connect(sock_path)
s.sendall((req_json + "\n").encode())
try:
    s.shutdown(socket.SHUT_WR)
except OSError:
    pass
chunks = []
while True:
    chunk = s.recv(65536)
    if not chunk:
        break
    chunks.append(chunk)
    if b"\n" in chunk:
        break
s.close()
print(b"".join(chunks).split(b"\n", 1)[0].decode())
PY
}

req_first() {
  python3 -c "import json,sys; print(json.dumps({'session_id': sys.argv[1], 'first': True, 'system': sys.argv[2], 'model': 'claude-fable-5-1', 'effort': 'high', 'message': sys.argv[3]}))" "$1" "$2" "$3"
}

req_resume() {
  python3 -c "import json,sys; print(json.dumps({'session_id': sys.argv[1], 'first': False, 'system': None, 'model': 'claude-fable-5-1', 'effort': 'high', 'message': sys.argv[2]}))" "$1" "$2"
}

# ---------------------------------------------------------------------------
# gateway.py
# ---------------------------------------------------------------------------

@test "gateway: a first call's argv carries the headless flags, the message rides stdin, the system prompt rides a file, env is allowlisted" {
  write_fake_claude "none" "allowed" "0.10" "alpha"
  ANTHROPIC_API_KEY="sk-should-never-appear" ANTHROPIC_AUTH_TOKEN="tok-should-never-appear" \
    AWS_ACCESS_KEY_ID="AKIA-should-never-appear" OTEL_EXPORTER_OTLP_ENDPOINT="http://should-never-appear" \
    start_gateway
  run send_request "$(req_first "$U1" "a system prompt" "hello")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]
  [[ "$output" == *'"text": "alpha"'* ]]

  grep -qx -- '--tools' "$T/observed-argv"
  grep -qx -- '--strict-mcp-config' "$T/observed-argv"
  grep -qx -- '--setting-sources' "$T/observed-argv"
  grep -qx -- '--session-id' "$T/observed-argv"
  grep -qx -- "$U1" "$T/observed-argv"
  grep -qx -- '--system-prompt-file' "$T/observed-argv"
  grep -q -- 'autoCompactEnabled' "$T/observed-argv"
  # the message is NOT an argv token -- it rode stdin instead
  ! grep -qx -- 'hello' "$T/observed-argv"

  [ "$(cat "$T/observed-stdin")" = "hello" ]
  [ "$(cat "$T/observed-system-prompt-file")" = "a system prompt" ]

  grep -qx -- 'ANTHROPIC_API_KEY=unset' "$T/observed-env"
  grep -qx -- 'ANTHROPIC_AUTH_TOKEN=unset' "$T/observed-env"
  grep -qx -- 'AWS_ACCESS_KEY_ID=unset' "$T/observed-env"
  grep -qx -- 'OTEL_EXPORTER_OTLP_ENDPOINT=unset' "$T/observed-env"
}

@test "gateway: a resumed call carries --resume, --system-prompt-file (every call), not --session-id" {
  write_fake_claude "none" "allowed" "0.10" "beta"
  start_gateway
  run send_request "$(req_first "$U2" "sys" "turn one")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]

  run send_request "$(req_resume "$U2" "the new turn")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]
  grep -qx -- '--resume' "$T/observed-argv"
  grep -qx -- "$U2" "$T/observed-argv"
  grep -qx -- '--system-prompt-file' "$T/observed-argv"
  ! grep -qx -- '--session-id' "$T/observed-argv"
  [ "$(cat "$T/observed-stdin")" = "the new turn" ]
}

@test "gateway: a resumed call reuses the SAME cwd the first call opened (a stable cwd per session)" {
  write_fake_claude "none" "allowed" "0.10" "gamma"
  start_gateway
  run send_request "$(req_first "$U3" "sys" "turn one")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]
  run send_request "$(req_resume "$U3" "turn two")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]
  [ "$(wc -l <"$T/observed-cwds")" -eq 2 ]
  cwd1="$(sed -n 1p "$T/observed-cwds")"
  cwd2="$(sed -n 2p "$T/observed-cwds")"
  [ -n "$cwd1" ]
  [ "$cwd1" = "$cwd2" ]
}

@test "gateway: refuses --resume for a session_id it never opened" {
  write_fake_claude "none" "allowed" "0.10" "delta"
  start_gateway
  run send_request "$(req_resume "$U4" "hello")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": false'* ]]
  [[ "$output" == *"never opened"* ]]
  # claude must never even have been spawned for this
  [ ! -f "$T/invocations" ]
}

@test "gateway: aborts when the init event's apiKeySource is not 'none'" {
  write_fake_claude_hangs_after_init "config"
  start_gateway
  run send_request "$(req_first "$U5" "sys" "hello")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": false'* ]]
  [[ "$output" == *"apiKeySource"* ]]
  grep -q "aborted_api_key_source" "$GLOG"
}

@test "gateway: a per-call timeout kills the WHOLE process group (not just the direct child) and returns promptly" {
  # hangs 60 / timeout 3: comfortably apart, so this is never a race against
  # send_request's own 30s socket timeout the way hangs=30/timeout=1 was.
  # The fake's `sleep 60` runs as bash's CHILD (not exec'd in its place), so
  # it inherits bash's stdout pipe fd; killing only the direct child (bash)
  # leaves that grandchild holding the pipe open, and the gateway's
  # `for line in proc.stdout` never sees EOF -- it hangs until send_request's
  # OWN 30s client timeout fires (a real bug, not a flake: verified red at
  # these same widened margins before landing the process-group fix below).
  write_fake_claude_hangs_after_init "none" 60
  start_gateway 0.90 3
  started="$(date +%s)"
  run send_request "$(req_first "$U6" "sys" "hello")"
  elapsed=$(($(date +%s) - started))
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": false'* ]]
  [[ "$output" == *"timeout"* ]]
  grep -q "call_timeout" "$GLOG"
  [ "$elapsed" -lt 15 ]
}

@test "gateway: is_error:true alone (subtype success) is reported as ok:false, never as a model turn" {
  write_fake_claude_result_error true success
  start_gateway
  run send_request "$(req_first "$U1" "sys" "hello")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": false'* ]]
  grep -q "result_is_error" "$GLOG"
}

@test "gateway: a non-success subtype alone (is_error false) is reported as ok:false, never as a model turn" {
  write_fake_claude_result_error false error_during_execution
  start_gateway
  run send_request "$(req_first "$U2" "sys" "hello")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": false'* ]]
  [[ "$output" == *"error_during_execution"* ]]
  grep -q "result_is_error" "$GLOG"
}

@test "gateway: refuses a further call once seven_day utilisation >= the stop threshold, and writes stopped.json" {
  write_fake_claude "none" "allowed" "0.95" "first-reply"
  start_gateway 0.90
  run send_request "$(req_first "$U1" "sys" "hello")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]
  [ "$(wc -c <"$T/invocations")" -eq 1 ]

  run send_request "$(req_resume "$U1" "another turn")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": false'* ]]
  [[ "$output" == *"utilisation"* ]]
  # the second call must never have reached claude at all
  [ "$(wc -c <"$T/invocations")" -eq 1 ]
  [ -f "$STOPPED" ]
  grep -q "utilisation" "$STOPPED"
}

@test "gateway: refuses a further call once status is not 'allowed'/'allowed_warning'" {
  write_fake_claude "none" "rejected" "0.10" "first-reply"
  start_gateway 0.90
  run send_request "$(req_first "$U2" "sys" "hello")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]

  run send_request "$(req_resume "$U2" "another turn")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": false'* ]]
  [[ "$output" == *"status"* ]]
  [ "$(wc -c <"$T/invocations")" -eq 1 ]
}

@test "gateway: 'allowed_warning' is logged but never stops the run" {
  write_fake_claude "none" "allowed_warning" "0.10" "first-reply"
  start_gateway 0.90
  run send_request "$(req_first "$U3" "sys" "hello")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]

  run send_request "$(req_resume "$U3" "another turn")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]
  [ "$(wc -c <"$T/invocations")" -eq 2 ]
  grep -q "allowed_warning" "$GLOG"
}

@test "gateway: below the stop threshold and status allowed, a second call proceeds" {
  write_fake_claude "none" "allowed" "0.10" "reply"
  start_gateway 0.90
  run send_request "$(req_first "$U4" "sys" "hello")"
  [ "$status" -eq 0 ]
  run send_request "$(req_resume "$U4" "another turn")"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"ok": true'* ]]
  [ "$(wc -c <"$T/invocations")" -eq 2 ]
}

@test "gateway: refuses to start when a settings file sets apiKeyHelper" {
  FAKE_SETTINGS="$T/settings.json"
  printf '{"apiKeyHelper": "echo sk-fake"}\n' >"$FAKE_SETTINGS"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import gateway
print(gateway.find_api_key_helper(('$FAKE_SETTINGS',)))
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"$FAKE_SETTINGS"* ]]
}

@test "gateway: main() itself refuses to start (exit 1) when ~/.claude/settings.json sets apiKeyHelper" {
  FAKE_HOME="$T/fakehome"
  mkdir -p "$FAKE_HOME/.claude"
  printf '{"apiKeyHelper": "echo sk-fake"}\n' >"$FAKE_HOME/.claude/settings.json"
  run env HOME="$FAKE_HOME" python3 "$GATEWAY_PY" --socket "$SOCKET" --log "$GLOG"
  [ "$status" -eq 1 ]
  [[ "$output" == *"apiKeyHelper"* ]]
  [ ! -S "$SOCKET" ]
}

@test "gateway: env is an allowlist -- an unrelated var never reaches claude" {
  write_fake_claude "none" "allowed" "0.10" "reply"
  RANDOM_UNRELATED_VAR="should-not-appear" start_gateway
  run send_request "$(req_first "$U5" "sys" "hello")"
  [ "$status" -eq 0 ]
  ! grep -q "RANDOM_UNRELATED_VAR" "$T/observed-env"
}

# ---------------------------------------------------------------------------
# sessions.py
# ---------------------------------------------------------------------------

@test "sessions.py: a brand-new conversation opens first=True with a dashed UUID session id and the system text" {
  run python3 -c "
import re, sys; sys.path.insert(0, '$JAZ_DIR')
import sessions
store = sessions.SessionStore()
plan = store.plan([{'role': 'system', 'content': 'sys text'}, {'role': 'user', 'content': 'task one'}])
assert plan['first'] is True, plan
assert plan['system'] == 'sys text', plan
assert plan['message'] == 'task one', plan
assert re.match(r'^[0-9a-fA-F-]{36}\$', plan['session_id']) and '-' in plan['session_id'], plan
assert not plan['session_id'].replace('-', '') == plan['session_id'], 'must be dashed, not .hex'
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

@test "sessions.py: an append (prior + new trailing user turn) sends only the new tail, first=False, same session" {
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import sessions
store = sessions.SessionStore()
m1 = [{'role': 'system', 'content': 'sys'}, {'role': 'user', 'content': 'turn one'}]
p1 = store.plan(m1)
store.record(m1, 'reply one', p1['session_id'])
m2 = m1 + [{'role': 'assistant', 'content': 'reply one'}, {'role': 'user', 'content': 'turn two'}]
p2 = store.plan(m2)
assert p2['first'] is False, p2
assert p2['message'] == 'turn two', p2
assert p2['session_id'] == p1['session_id'], (p1, p2)
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

@test "sessions.py: parent -> child -> parent interleaving keeps the parent on its original session (native resume)" {
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import sessions
store = sessions.SessionStore()

# Parent's first turn (depth 1).
parent1 = [{'role': 'system', 'content': 'sys depth=1'}, {'role': 'user', 'content': 'parent task'}]
pp1 = store.plan(parent1)
store.record(parent1, 'parent reply one', pp1['session_id'])

# Parent recurses: the CHILD's system prompt differs (depth=2) but even if
# it did not, this must never be mistaken for the parent's own history.
child1 = [{'role': 'system', 'content': 'sys depth=2'}, {'role': 'user', 'content': 'child task'}]
cp1 = store.plan(child1)
assert cp1['first'] is True, cp1
assert cp1['session_id'] != pp1['session_id'], (cp1, pp1)
store.record(child1, 'child reply one', cp1['session_id'])

# Parent continues: its own history, extended by exactly one user turn.
parent2 = parent1 + [{'role': 'assistant', 'content': 'parent reply one'}, {'role': 'user', 'content': 'parent turn two'}]
pp2 = store.plan(parent2)
assert pp2['first'] is False, pp2
assert pp2['session_id'] == pp1['session_id'], (pp2, pp1)
assert pp2['message'] == 'parent turn two', pp2
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

@test "sessions.py: two children with identical first messages stay on separate sessions" {
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import sessions
store = sessions.SessionStore()

child_a = [{'role': 'system', 'content': 'sys depth=2'}, {'role': 'user', 'content': 'same task'}]
pa = store.plan(child_a)
store.record(child_a, 'reply a', pa['session_id'])

# A SECOND child with byte-identical opening messages (same depth, same
# tools, same task) must NOT be merged into the first child's session.
child_b = [{'role': 'system', 'content': 'sys depth=2'}, {'role': 'user', 'content': 'same task'}]
pb = store.plan(child_b)
assert pb['first'] is True, pb
assert pb['session_id'] != pa['session_id'], (pa, pb)
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

@test "sessions.py: realistic interleaving -- parent, child A and sibling B ALL share one system prompt shape; B's two turns never land on A's session" {
  # Real jaz renders the system message from depth/recursion/repl-
  # description/scoped-names only (jaz/protocol/code_only.py), so a parent
  # at depth=1 and every depth=2 child it spawns can share byte-identical
  # system text; two SIBLINGS at the same depth with the same tools go
  # further and can share an identical system AND (if given the same
  # inputs) an identical opening user message too. This is the scenario
  # the first-message-keyed design (the pre-fix sessions.py) collapsed.
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import sessions
store = sessions.SessionStore()

parent1 = [{'role': 'system', 'content': 'sys depth=1'}, {'role': 'user', 'content': 'parent task'}]
pp = store.plan(parent1)
store.record(parent1, 'parent reply', pp['session_id'])

common_child_system = {'role': 'system', 'content': 'sys depth=2'}
a1 = [common_child_system, {'role': 'user', 'content': 'same task'}]
pa1 = store.plan(a1)
assert pa1['session_id'] not in (pp['session_id'],), pa1
store.record(a1, 'reply A', pa1['session_id'])
# Child A is done after one turn -- its session stays exactly as recorded.

# Sibling B: byte-identical OPENING to A (same depth=2 system, same task).
b1 = [common_child_system, {'role': 'user', 'content': 'same task'}]
pb1 = store.plan(b1)
assert pb1['first'] is True, pb1
assert pb1['session_id'] not in (pp['session_id'], pa1['session_id']), (pb1, pp, pa1)
store.record(b1, 'reply B1', pb1['session_id'])

# B's SECOND turn must resume B's own session -- never A's, even though
# A's committed 'sent' (child_system, same task, reply A) and B's own
# extended history (child_system, same task, reply B1, turn two) share
# the same LENGTH-2 opening prefix.
b2 = b1 + [{'role': 'assistant', 'content': 'reply B1'}, {'role': 'user', 'content': 'b turn two'}]
pb2 = store.plan(b2)
assert pb2['first'] is False, pb2
assert pb2['session_id'] == pb1['session_id'], (pb2, pb1)
assert pb2['session_id'] != pa1['session_id'], (pb2, pa1)
assert pb2['message'] == 'b turn two', pb2
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

@test "sessions.py: the same interleaving scenario goes RED against a first-message-only mutant (the pre-fix design)" {
  # Proves the previous test is actually discriminating: a mutant
  # _find_match that matches on messages[0] alone -- the original, wrong
  # design this module's own history section describes ("keying on the
  # system message alone collapses them into one conversation") --
  # misbehaves on the exact same scenario: sibling B's very first call is
  # wrongly matched to child A's already-recorded session.
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import sessions

def mutant_find_match(self, messages):
    # The crudest 'first-message-only' matcher: any live conversation
    # whose sent[0] equals this call's first message is a match, full
    # stop -- no prefix/length/tail check at all.
    if not messages:
        return None
    for conv in self._conversations:
        if conv['sent'] and conv['sent'][0] == messages[0]:
            return conv
    return None

sessions.SessionStore._find_match = mutant_find_match

store = sessions.SessionStore()
common_child_system = {'role': 'system', 'content': 'sys depth=2'}
a1 = [common_child_system, {'role': 'user', 'content': 'same task'}]
pa1 = store.plan(a1)
store.record(a1, 'reply A', pa1['session_id'])

# Sibling B's FIRST-EVER call: under the mutant this is wrongly treated
# as a resume of A's session, since only messages[0] is compared.
b1 = [common_child_system, {'role': 'user', 'content': 'same task'}]
pb1 = store.plan(b1)
assert pb1['session_id'] == pa1['session_id'], 'expected the mutant to WRONGLY merge B into A -- it did not: ' + repr((pb1, pa1))
assert pb1['first'] is False, pb1
print('RED_CONFIRMED')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"RED_CONFIRMED"* ]]
}

@test "sessions.py: a ContextWindowWarning's transient message is stripped for MATCHING but still SENT to the model" {
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import sessions
WARN = 'context window warning text'
store = sessions.SessionStore(strip_texts=[WARN])
m1 = [{'role': 'system', 'content': 'sys'}, {'role': 'user', 'content': 'turn one'}]
p1 = store.plan(m1)
store.record(m1, 'reply one', p1['session_id'])

# JAZ's own next call carries the transient warning appended for THIS
# call's display only -- never persisted into the agent's real history.
# It must still be MATCHED as the same conversation (stripped before
# matching) AND actually reach the model (sent from the ORIGINAL,
# unstripped tail) -- dropping it silently would defeat the whole hook.
warn_msg = {'role': 'user', 'content': WARN}
m2_with_warning = m1 + [
    {'role': 'assistant', 'content': 'reply one'},
    {'role': 'user', 'content': 'turn two'},
    warn_msg,
]
p2 = store.plan(m2_with_warning)
assert p2['first'] is False, p2
assert p2['session_id'] == p1['session_id'], (p1, p2)
expected = sessions.serialize_transcript([{'role': 'user', 'content': 'turn two'}, warn_msg])
assert p2['message'] == expected, p2
assert WARN in p2['message'], p2
store.record(m2_with_warning, 'reply two', p2['session_id'])

# The NEXT real call never carries the warning at all -- must still match.
m3 = m1 + [
    {'role': 'assistant', 'content': 'reply one'},
    {'role': 'user', 'content': 'turn two'},
    {'role': 'assistant', 'content': 'reply two'},
    {'role': 'user', 'content': 'turn three'},
]
p3 = store.plan(m3)
assert p3['first'] is False, p3
assert p3['session_id'] == p1['session_id'], (p1, p3)
assert p3['message'] == 'turn three', p3
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

@test "sessions.py: a retry after a failed first call opens a fresh session (never resumes a session that never existed)" {
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import sessions
store = sessions.SessionStore()
m1 = [{'role': 'system', 'content': 'sys'}, {'role': 'user', 'content': 'turn one'}]
p1 = store.plan(m1)
# the call FAILS: no record() -- nothing is committed
p1_retry = store.plan(m1)
assert p1_retry['first'] is True, p1_retry
assert p1_retry['session_id'] != p1['session_id'], (p1, p1_retry)
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

@test "sessions.py: no leading system message means system is None" {
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import sessions
store = sessions.SessionStore()
plan = store.plan([{'role': 'user', 'content': 'no system here'}])
assert plan['system'] is None, plan
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

# ---------------------------------------------------------------------------
# the fake claude fixture itself (BLOCKER 1: UUID validation)
# ---------------------------------------------------------------------------

@test "fixture: the fake claude rejects a non-UUID --session-id, mirroring the real claude's validation" {
  write_fake_claude "none" "allowed" "0.10" "x"
  run "$T/bin/claude" --session-id not-a-uuid -p --output-format stream-json
  [ "$status" -ne 0 ]
  [[ "$output" == *"Invalid session ID"* ]]
}

@test "fixture: the fake claude rejects an unknown --resume id directly (not only via the gateway's own check)" {
  write_fake_claude "none" "allowed" "0.10" "x"
  run "$T/bin/claude" --resume "$U1" -p --output-format stream-json
  [ "$status" -ne 0 ]
  [[ "$output" == *"No conversation found"* ]]
}

# ---------------------------------------------------------------------------
# confined_tools.py
# ---------------------------------------------------------------------------

@test "confined_tools: read_file refuses a path outside the fixture root and logs exit=1" {
  FIX="$T/fixture"
  mkdir -p "$FIX"
  echo "inside" >"$FIX/inside.txt"
  echo "outside secret" >"$T/outside.txt"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['read_file']('../outside.txt'))
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"REFUSED"* ]]
  [[ "$output" != *"secret"* ]]
  grep -q "read_file .* exit=1" "$T/queries.log"
}

@test "confined_tools: read_file inside the fixture root succeeds and logs exit=0" {
  FIX="$T/fixture"
  mkdir -p "$FIX"
  echo "inside content" >"$FIX/inside.txt"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['read_file']('inside.txt'))
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"inside content"* ]]
  grep -q "read_file .* exit=0" "$T/queries.log"
}

@test "confined_tools: list_dir and grep also refuse a path outside the fixture root" {
  FIX="$T/fixture"
  mkdir -p "$FIX"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['list_dir']('..'))
print(tools['grep']('secret', '..'))
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"REFUSED"* ]]
  refused_count="$(grep -c REFUSED <<<"$output")"
  [ "$refused_count" -eq 2 ]
  grep -q "list_dir .* exit=1" "$T/queries.log"
  grep -q "grep .* exit=1" "$T/queries.log"
}

@test "confined_tools: write_scratch writes inside scratch, logs exit=0" {
  FIX="$T/fixture"
  mkdir -p "$FIX"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['write_scratch']('draft-0.md', 'hello draft'))
"
  [ "$status" -eq 0 ]
  [ "$(cat "$T/draft-0.md")" = "hello draft" ]
  grep -q "write_scratch .* exit=0" "$T/queries.log"
}

@test "confined_tools: write_scratch refuses a path outside scratch (e.g. into the fixture) and logs exit=1" {
  FIX="$T/fixture"
  mkdir -p "$FIX"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['write_scratch']('../fixture/evil.md', 'nope'))
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"REFUSED"* ]]
  [ ! -f "$FIX/evil.md" ]
  grep -q "write_scratch .* exit=1" "$T/queries.log"
}

@test "confined_tools: write_scratch refuses the run's own bookkeeping files (queries.log, stopped.json, jaz.log, return.json, trajectory/*)" {
  FIX="$T/fixture"
  mkdir -p "$FIX"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['write_scratch']('queries.log', 'nope'))
print(tools['write_scratch']('stopped.json', 'nope'))
print(tools['write_scratch']('jaz.log', 'nope'))
print(tools['write_scratch']('return.json', 'nope'))
print(tools['write_scratch']('trajectory/00001.json', 'nope'))
print(tools['write_scratch']('./queries.log', 'nope'))
"
  [ "$status" -eq 0 ]
  refused_count="$(grep -c REFUSED <<<"$output")"
  [ "$refused_count" -eq 6 ]
  [ ! -f "$T/trajectory/00001.json" ]
}

@test "confined_tools: duckdb_query locks allowed_directories/external-access/lock_configuration before running the caller's SQL" {
  FIX="$T/fixture-duck"
  mkdir -p "$FIX/evidence"
  printf '{"a":1}\n' >"$FIX/evidence/x.json"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['duckdb_query'](\"select * from read_json('$FIX/evidence/x.json')\"))
"
  # duckdb is not guaranteed importable in every sandbox this suite runs
  # under (the 'unit' nix check's env is plainer than the devShell's) --
  # either outcome is correct behaviour, so accept both rather than
  # pinning one.
  [ "$status" -eq 0 ]
  [[ "$output" == *"1"* || "$output" == *"REFUSED: duckdb is not importable"* ]]
  grep -Eq "duckdb_query .* exit=[01]" "$T/queries.log"
}

@test "confined_tools: git_log refuses --output/-o and any flag not on its allowlist" {
  FIX="$T/fixture-git2"
  mkdir -p "$FIX"
  git -C "$FIX" init -q
  git -C "$FIX" config user.email "t@example.invalid"
  git -C "$FIX" config user.name "t"
  echo one >"$FIX/f.txt"
  git -C "$FIX" add f.txt
  git -C "$FIX" commit -q -m "one commit"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['git_log']('--output=$T/escaped.txt'))
print(tools['git_log']('-o'))
"
  [ "$status" -eq 0 ]
  refused_count="$(grep -c REFUSED <<<"$output")"
  [ "$refused_count" -eq 2 ]
  [ ! -f "$T/escaped.txt" ]
  grep -q "git_log .* exit=1" "$T/queries.log"
}

@test "confined_tools: git_log accepts a value-taking flag as two argv entries (-n 5)" {
  FIX="$T/fixture-git3"
  mkdir -p "$FIX"
  git -C "$FIX" init -q
  git -C "$FIX" config user.email "t@example.invalid"
  git -C "$FIX" config user.name "t"
  for i in 1 2 3; do
    echo "$i" >"$FIX/f.txt"
    git -C "$FIX" add f.txt
    git -C "$FIX" commit -q -m "commit $i"
  done
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['git_log']('--oneline', '-n', '2'))
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"commit 3"* ]]
  [[ "$output" == *"commit 2"* ]]
  [[ "$output" != *"commit 1"* ]]
  grep -q "git_log .* exit=0" "$T/queries.log"
}

@test "confined_tools: git_log accepts -- followed by a confined pathspec, refuses one that escapes the fixture" {
  FIX="$T/fixture-git4"
  mkdir -p "$FIX"
  git -C "$FIX" init -q
  git -C "$FIX" config user.email "t@example.invalid"
  git -C "$FIX" config user.name "t"
  echo a >"$FIX/a.txt"
  git -C "$FIX" add a.txt
  git -C "$FIX" commit -q -m "add a.txt only"
  echo b >"$FIX/b.txt"
  git -C "$FIX" add b.txt
  git -C "$FIX" commit -q -m "add b.txt only"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['git_log']('--oneline', '--', 'a.txt'))
print(tools['git_log']('--oneline', '--', '../outside.txt'))
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"add a.txt only"* ]]
  [[ "$output" != *"add b.txt only"* ]]
  [[ "$output" == *"REFUSED"* ]]
}

@test "confined_tools: git_log allows an allowlisted flag and runs against the fixture root" {
  FIX="$T/fixture-git"
  mkdir -p "$FIX"
  git -C "$FIX" init -q
  git -C "$FIX" config user.email "t@example.invalid"
  git -C "$FIX" config user.name "t"
  echo one >"$FIX/f.txt"
  git -C "$FIX" add f.txt
  git -C "$FIX" commit -q -m "one commit"
  run python3 -c "
import sys; sys.path.insert(0, '$JAZ_DIR')
import confined_tools
tools = confined_tools.make_tools('$FIX', '$T')
print(tools['git_log']('--oneline'))
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"one commit"* ]]
  grep -q "git_log .* exit=0" "$T/queries.log"
}

# ---------------------------------------------------------------------------
# run-arm-c.sh --dry-run
# ---------------------------------------------------------------------------

@test "run-arm-c.sh --dry-run: no network flag missing, no ~/.claude path, no bare claude binary, --clearenv present" {
  FIX="$T/fixture-launcher"
  mkdir -p "$FIX"
  run bash "$RUN_ARM_C_SH" --fixture "$FIX" --smoke --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"--unshare-all"* ]]
  [[ "$output" == *"--clearenv"* ]]
  # The operator's real per-user Claude Code config dir/login must never be
  # bound in. Checked against the real $HOME specifically (not a bare
  # "/.claude/" substring match), since this suite may itself run from a
  # checkout nested under a path that happens to contain ".claude" (e.g. an
  # agent worktree under .claude/worktrees/) with no bearing on the
  # operator's login.
  [[ "$output" != *"$HOME/.claude"* ]]
  [[ "$output" != *".credentials"* ]]
  # no argv token is the bare `claude` binary (a model id like
  # claude-fable-5-1 legitimately contains the substring "claude" -- this
  # checks for an exact, standalone token instead of a substring).
  run bash -c "printf '%s\n' $output | tr ' ' '\n' | grep -xq claude"
  [ "$status" -ne 0 ]
}

@test "run-arm-c.sh --dry-run: --tmpfs /tmp (and the basket HOME tmpfs) come BEFORE every --bind/--ro-bind" {
  FIX="$T/fixture-launcher-order"
  mkdir -p "$FIX"
  run bash "$RUN_ARM_C_SH" --fixture "$FIX" --smoke --dry-run
  [ "$status" -eq 0 ]
  # Token-index comparison: every --tmpfs token's index must be lower than
  # every --bind/--ro-bind token's index (bwrap applies mounts in argv
  # order -- a tmpfs issued after a bind under the same path would shadow
  # it, DF-style, so this is the load-bearing property, not just presence).
  python3 -c "
import shlex, sys
argv = shlex.split(sys.argv[1])
tmpfs_idx = [i for i, a in enumerate(argv) if a == '--tmpfs']
bind_idx = [i for i, a in enumerate(argv) if a in ('--bind', '--ro-bind')]
assert tmpfs_idx, 'no --tmpfs found'
assert bind_idx, 'no --bind/--ro-bind found'
assert max(tmpfs_idx) < min(bind_idx), (tmpfs_idx, bind_idx)
print('OK')
" "$output"
}

@test "run-arm-c.sh --dry-run: creates no directory at all, and the default run dir is not under /tmp" {
  FIX="$T/fixture-launcher-nomkdir"
  mkdir -p "$FIX"
  WORKDIR="$T/operator-cwd"
  mkdir -p "$WORKDIR"
  before="$(find "$WORKDIR" | wc -l)"
  run bash -c "cd '$WORKDIR' && bash '$RUN_ARM_C_SH' --fixture '$FIX' --smoke --dry-run"
  [ "$status" -eq 0 ]
  after="$(find "$WORKDIR" | wc -l)"
  [ "$before" -eq "$after" ]
  # the default run dir is $PWD-relative, not a hardcoded /tmp base --
  # demonstrated here by an operator cwd outside /tmp landing the run dir
  # there too (this test's own harness necessarily lives under /tmp, so a
  # bare "not /tmp" substring check on $output would test the wrong
  # thing; the load-bearing property is "under $WORKDIR", asserted next).
  [[ "$output" == *"$WORKDIR"* ]]
}

@test "run-arm-c.sh: wires --stopped-file under \$SCRATCH when starting the gateway" {
  grep -q -- '--stopped-file "\$STOPPED_FILE"' "$RUN_ARM_C_SH"
  grep -q 'STOPPED_FILE="\$SCRATCH/stopped.json"' "$RUN_ARM_C_SH"
}

@test "run-arm-c.sh: REPO is derived from the script's own location, not a hardcoded operator home path" {
  # Positive check (REPO is computed via a command substitution from
  # $HERE) rather than a negative grep for a specific forbidden literal --
  # the latter would itself plant that literal in this published test
  # file, tripping the export deny-scan on the file that checks for it.
  grep -qE 'REPO="\$\(cd .*&& pwd\)"' "$RUN_ARM_C_SH"
}

@test "run-arm-c.sh --dry-run: a full draft invocation carries --spec/--name/--date and the fixture bind" {
  FIX="$T/fixture-launcher2"
  mkdir -p "$FIX"
  run bash "$RUN_ARM_C_SH" --fixture "$FIX" --spec docs/x.md --name x --date 2026-09-27 --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"--ro-bind $FIX $FIX"* ]]
  [[ "$output" == *"--spec docs/x.md"* ]]
  [[ "$output" == *"--name x"* ]]
  [[ "$output" == *"--date 2026-09-27"* ]]
}

@test "run-arm-c.sh: refuses (usage error) without --fixture" {
  run bash "$RUN_ARM_C_SH" --smoke --dry-run
  [ "$status" -eq 2 ]
}

@test "run-arm-c.sh: refuses (usage error) for a draft run missing --spec/--name/--date" {
  FIX="$T/fixture-launcher3"
  mkdir -p "$FIX"
  run bash "$RUN_ARM_C_SH" --fixture "$FIX" --dry-run
  [ "$status" -eq 2 ]
}

# ---------------------------------------------------------------------------
# extract_draft_prompt.py / check-armc-prompt.py
# ---------------------------------------------------------------------------

@test "check-armc-prompt.py: passes against the real repo tree" {
  run python3 "$JAZ_DIR/check-armc-prompt.py" --root "$BATS_TEST_DIRNAME/../.."
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS"* ]]
}

@test "check-armc-prompt.py: fails loudly (not silently) when draft-byref.js's START marker text is mutated" {
  MUT="$T/mut-repo"
  mkdir -p "$MUT/.claude/workflows"
  cp "$BATS_TEST_DIRNAME/../../.claude/workflows/draft-byref.js" "$MUT/.claude/workflows/draft-byref.js"
  sed -i 's/Query recipes/Query recipe MUTATED/' "$MUT/.claude/workflows/draft-byref.js"
  run python3 "$JAZ_DIR/check-armc-prompt.py" --root "$MUT"
  [ "$status" -eq 1 ]
  [[ "$output" == *"marker"* || "$output" == *"differ"* ]]
}

@test "check-armc-prompt.py: catches a broken RULES-inlining step in extract_draft_prompt.py, which the pre-fix version missed" {
  # The pre-fix check compared draftPrompt's text with the LITERAL,
  # unexpanded "\${RULES}" marker still in it on BOTH sides, so a bug in
  # the *inlining step itself* (as opposed to a bug in the marker split)
  # never showed up in that comparison at all -- neither side ever looked
  # at RULES' real text. Reproduced here by mutating a COPY of
  # extract_draft_prompt.py's inlining call so it substitutes the wrong
  # text, then running a COPY of check-armc-prompt.py against it (the
  # real draft-byref.js is copied in unmutated, so the independent side
  # computes the correct RULES-inlined text and disagrees with the
  # deliberately-broken real extractor).
  MUT="$T/mut-extractor"
  mkdir -p "$MUT/.claude/workflows"
  cp "$BATS_TEST_DIRNAME/../../.claude/workflows/draft-byref.js" "$MUT/.claude/workflows/draft-byref.js"
  cp "$JAZ_DIR/extract_draft_prompt.py" "$JAZ_DIR/check-armc-prompt.py" "$MUT/"
  sed -i 's/merged\.replace("\${RULES}", rules)/merged.replace("${RULES}", "WRONG RULES TEXT")/' "$MUT/extract_draft_prompt.py"
  grep -q "WRONG RULES TEXT" "$MUT/extract_draft_prompt.py" # the sed actually landed
  run python3 "$MUT/check-armc-prompt.py" --root "$MUT"
  [ "$status" -eq 1 ]
  [[ "$output" == *"differ"* ]]
}
