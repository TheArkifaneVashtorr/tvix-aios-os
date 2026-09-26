#!/usr/bin/env bats
# tools/run-result-hook.sh — the UserPromptSubmit hook that reminds the
# orchestrator, when a prompt is a Run-button command result, to report that
# result only and never re-issue a command block already given (the operator's
# feedback of 2026-09-21: repeated blocks were pressed again, three times each).
# Hooks run outside the devShell, so the script uses bash alone: no jq.

setup() {
  HOOK="$BATS_TEST_DIRNAME/../../tools/run-result-hook.sh"
}

@test "a Run-button result prompt gets the reminder as additionalContext" {
  run bash "$HOOK" <<'EOF'
{"session_id":"s1","hook_event_name":"UserPromptSubmit","prompt":"<bash-input>cd ~/repo && nix build .#x</bash-input><bash-stdout>ok</bash-stdout>"}
EOF
  [ "$status" -eq 0 ]
  [[ "$output" == *'"hookEventName": "UserPromptSubmit"'* ]]
  [[ "$output" == *'"additionalContext"'* ]]
  [[ "$output" == *"Run-button result"* ]]
  [[ "$output" == *"never repeat a command block already given"* ]]
}

@test "the reminder also fires when the JSON has a space after the colon" {
  run bash "$HOOK" <<'EOF'
{"prompt": "<bash-input>true</bash-input><bash-stdout></bash-stdout>"}
EOF
  [ "$status" -eq 0 ]
  [[ "$output" == *"additionalContext"* ]]
}

@test "an ordinary prompt gets nothing" {
  run bash "$HOOK" <<'EOF'
{"session_id":"s1","hook_event_name":"UserPromptSubmit","prompt":"merge them when the reviews approve"}
EOF
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "a prompt that merely mentions the tag mid-text gets nothing" {
  run bash "$HOOK" <<'EOF'
{"prompt":"why does <bash-input> appear in my transcript?"}
EOF
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "empty stdin exits 0 and prints nothing" {
  run bash "$HOOK" </dev/null
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "the reminder is valid JSON (the harness parses it)" {
  command -v python3 >/dev/null || skip "python3 not on PATH outside the devShell"
  run bash -c 'printf "%s" "{\"prompt\":\"<bash-input>ls</bash-input>\"}" | bash "$0" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d[\"hookSpecificOutput\"][\"hookEventName\"]==\"UserPromptSubmit\"; print(\"valid\")"' "$HOOK"
  [ "$status" -eq 0 ]
  [ "$output" = "valid" ]
}
