#!/usr/bin/env bats
# SD8: hook-guard --house-guard hands every bash, edit and write payload to
# tools/orchestrator-guard.sh (the orchestrator's Claude Code hook) after its
# own rules allow, and fails closed on a fault or a missing guard. This file
# is the proof of parity: for all 442 sweep rows the house guard's verdict over
# a payload is exactly the verdict `bash "$GUARD"` reaches on the equivalent
# Claude Code payload, plus the cwd/workdir rule, the edit/write heading rule,
# and the fault arms. hook-guard is driven bare (a hook needs no harness); the
# guard is run as `bash "$GUARD"` — never its shebang — because the build
# sandbox has no /usr/bin/env.

# run --separate-stderr (the stderr-record assertions) needs bats >= 1.5.
bats_require_minimum_version 1.5.0

GUARD="$BATS_TEST_DIRNAME/../../tools/orchestrator-guard.sh"
SWEEP="$BATS_TEST_DIRNAME/91-orchestrator-guard-sweep.txt"
ROUTING_TABLE="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"

setup() {
  PROJECT="$BATS_TEST_TMPDIR/project"
  PLANS_DIR="$PROJECT/docs/superpowers/plans"
  mkdir -p "$PLANS_DIR"
  PLAN="$PLANS_DIR/test.md"
  cat >"$PLAN" <<'EOF'
# Test plan

### A1 (code, S) — first task

body one line

### B2 (docs, S) — second task

body two line
EOF
  SHELL_BIN="$(command -v bash)"
}

# --- payload builders (python3 JSON-encodes so quotes/backslashes/em-dashes
# survive verbatim; ensure_ascii=False keeps the em-dash raw) ---

# hg_bash COMMAND [WORKDIR] -> a dsh PreToolUse bash payload.
hg_bash() {
  if [ -n "${2-}" ]; then
    python3 -c 'import json,sys; print(json.dumps({"hook_event_name":"PreToolUse","tool_name":"bash","tool_input":{"command":sys.argv[1],"workdir":sys.argv[2]}}, ensure_ascii=False, separators=(",",":")))' "$1" "$2"
  else
    python3 -c 'import json,sys; print(json.dumps({"hook_event_name":"PreToolUse","tool_name":"bash","tool_input":{"command":sys.argv[1]}}, ensure_ascii=False, separators=(",",":")))' "$1"
  fi
}

# hg_edit FILE OLD NEW -> a dsh PreToolUse edit payload.
hg_edit() {
  python3 -c 'import json,sys; print(json.dumps({"hook_event_name":"PreToolUse","tool_name":"edit","tool_input":{"file_path":sys.argv[1],"old_string":sys.argv[2],"new_string":sys.argv[3]}}, ensure_ascii=False, separators=(",",":")))' "$1" "$2" "$3"
}

# hg_write FILE CONTENT -> a dsh PreToolUse write payload.
hg_write() {
  python3 -c 'import json,sys; print(json.dumps({"hook_event_name":"PreToolUse","tool_name":"write","tool_input":{"file_path":sys.argv[1],"content":sys.argv[2]}}, ensure_ascii=False, separators=(",",":")))' "$1" "$2"
}

# bpayload COMMAND -> the house guard's own Claude Code Bash payload.
bpayload() {
  python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}, ensure_ascii=False, separators=(",",":")))' "$1"
}

# Run hook-guard with the house guard wired; stdout in $output, stderr in $stderr.
run_house() {
  run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" \
    hook-guard --routing-table "$ROUTING_TABLE" --house-guard "$GUARD" --house-shell "$SHELL_BIN" <<<"$1"
}

# denied STDOUT — assert the deny decision JSON with a non-empty reason, without
# clobbering the test's own $output/$status.
denied() {
  printf '%s' "$1" | python3 -c 'import json,sys;o=json.load(sys.stdin);h=o["hookSpecificOutput"];assert h["hookEventName"]=="PreToolUse" and h["permissionDecision"]=="deny" and h["permissionDecisionReason"], o'
}

# --- parity over the 442-row sweep ---

@test "parity: hook-guard with the house guard matches the guard on every sweep row, one stderr record per deny" {
  local tmpd cmd p n=0 data_rows=0 seen_header=0
  local hgp hsp hg_out hs_out hgv hsv
  tmpd=$(mktemp -d)
  while IFS= read -r cmd; do
    if [ "$seen_header" -eq 0 ]; then
      [[ "$cmd" == '# rows: '* ]] || {
        printf 'sweep header missing (first line: %s)\n' "$cmd"
        return 1
      }
      n=${cmd#'# rows: '}
      seen_header=1
      continue
    fi
    data_rows=$((data_rows + 1))
    # JSON-escape the command for both payloads the way 91 does (the sweep holds
    # no control or non-ASCII characters).
    p=${cmd//\\/\\\\}
    p=${p//\"/\\\"}
    hgp="{\"hook_event_name\":\"PreToolUse\",\"tool_name\":\"bash\",\"tool_input\":{\"command\":\"$p\"}}"
    hsp="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$p\"}}"
    hg_out=$(env CLAUDE_PROJECT_DIR="$PROJECT" \
      hook-guard --routing-table "$ROUTING_TABLE" --house-guard "$GUARD" --house-shell "$SHELL_BIN" \
      2>"$tmpd/err" <<<"$hgp")
    hs_out=$(env CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" <<<"$hsp" 2>/dev/null)
    hgv=allow; [ -n "$hg_out" ] && hgv=deny
    hsv=allow; [ -n "$hs_out" ] && hsv=deny
    if [ "$hgv" != "$hsv" ]; then
      printf 'row %d diverges: house=%s hook=%s (cmd: %s)\n' "$data_rows" "$hsv" "$hgv" "$cmd"
      return 1
    fi
    if [ "$hgv" = deny ]; then
      if [ ! -s "$tmpd/err" ]; then
        printf 'row %d denied without a stderr record (cmd: %s)\n' "$data_rows" "$cmd"
        return 1
      fi
    fi
  done < "$SWEEP"
  [ "$data_rows" -eq "$n" ] || {
    printf 'sweep data-row count %d does not match header %d\n' "$data_rows" "$n"
    return 1
  }
  rm -rf "$tmpd"
}

# --- the cwd/workdir rule ---

@test "a bash command whose workdir is a plans subdirectory is denied by the house guard" {
  local p
  # The dsh bridge carries the session cwd as the payload's top-level `cwd`
  # (Assumption 13), so a relative workdir is joined onto it before hand-off.
  p=$(python3 -c 'import json,sys; print(json.dumps({"hook_event_name":"PreToolUse","tool_name":"bash","tool_input":{"command":sys.argv[1],"workdir":sys.argv[2]},"cwd":sys.argv[3]}, ensure_ascii=False, separators=(",",":")))' 'rm x.md' 'docs/superpowers/plans' "$PROJECT")
  run_house "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"house: plan files change only through the Edit and Write tools"* ]]
}

@test "a bash command whose workdir is an absolute /tmp path is allowed" {
  local p
  p=$(hg_bash 'rm x.md' '/tmp')
  run_house "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- the edit/write heading rule ---

@test "an edit removing a typed task heading is denied by the house guard" {
  local p
  p=$(hg_edit "$PLAN" '### A1 (code, S) — first task' '')
  run_house "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"house: typed task headings are append-only"* ]]
}

@test "an edit of body text is allowed" {
  local p
  p=$(hg_edit "$PLAN" 'body one line' 'body one line changed')
  run_house "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "a write dropping a typed task heading is denied by the house guard" {
  local content p
  content=$(cat <<'EOF'
# Test plan

### A1 (code, S) — first task

body one line
EOF
)
  p=$(hg_write "$PLAN" "$content")
  run_house "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"house: typed task headings are append-only"* ]]
}

# --- the fault arms (fail closed) ---

@test "an unreadable house guard denies every bash payload fail-closed" {
  run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" \
    hook-guard --routing-table "$ROUTING_TABLE" --house-guard /nonexistent --house-shell "$SHELL_BIN" \
    <<<"$(hg_bash 'echo hi')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"house guard unreadable at /nonexistent"* ]]
}

@test "a house guard exiting non-zero is a fault deny" {
  local stub="$BATS_TEST_TMPDIR/stub-exit1"
  printf '#!/bin/sh\nexit 1\n' >"$stub"
  chmod +x "$stub"
  run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" \
    hook-guard --routing-table "$ROUTING_TABLE" --house-guard "$stub" --house-shell "$SHELL_BIN" \
    <<<"$(hg_bash 'echo hi')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"house guard fault"* ]]
}

@test "a house guard printing garbage is a fault deny" {
  local stub="$BATS_TEST_TMPDIR/stub-garbage"
  printf '#!/bin/sh\nprintf garbage\n' >"$stub"
  chmod +x "$stub"
  run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" \
    hook-guard --routing-table "$ROUTING_TABLE" --house-guard "$stub" --house-shell "$SHELL_BIN" \
    <<<"$(hg_bash 'echo hi')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"house guard fault"* ]]
}

@test "a house guard that hangs is a timeout fault within 11 seconds" {
  local stub="$BATS_TEST_TMPDIR/stub-sleep"
  printf '#!/bin/sh\nsleep 20\n' >"$stub"
  chmod +x "$stub"
  local start=$SECONDS
  run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" \
    hook-guard --routing-table "$ROUTING_TABLE" --house-guard "$stub" --house-shell "$SHELL_BIN" \
    <<<"$(hg_bash 'echo hi')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"house guard fault"* ]]
  [ $((SECONDS - start)) -le 11 ]
}

# --- negative control and the stderr record ---

@test "without --house-guard a bare git push is allowed (today's behaviour)" {
  run hook-guard --routing-table "$ROUTING_TABLE" <<<"$(hg_bash 'git push')"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "a house deny writes one stderr record naming the house reason and the command" {
  run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" \
    hook-guard --routing-table "$ROUTING_TABLE" --house-guard "$GUARD" --house-shell "$SHELL_BIN" \
    <<<"$(hg_bash 'git push')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"house: "* ]]
  [ "$(printf '%s\n' "$stderr" | wc -l)" -eq 1 ]
  run python3 -c 'import json,sys; rec=json.load(sys.stdin); assert rec["tool"]=="bash", rec; assert rec["reason"].startswith("house: "), rec; assert rec["subject"]=="git push", rec' <<<"$stderr"
  [ "$status" -eq 0 ]
}