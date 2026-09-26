#!/usr/bin/env bats
# tools/debug/bug-note — one JSON line into the operator's inbox
# (plan 2026-09-23-debug-sweep, DS1). Bash and coreutils only: the seat and
# the operator's shell have no jq or python3 on PATH.

setup() {
  BN="$BATS_TEST_DIRNAME/../../tools/debug/bug-note"
  INV="$BATS_TEST_DIRNAME/../../tools/debug/investigate"
  T="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/bn.XXXXXX")"
  export BUG_NOTE_INBOX="$T/inbox.jsonl"
  unset BUG_NOTE_REPORTER
  cd "$T"
}

@test "a symptom appends one line with the five keys in order and prints it" {
  run bash "$BN" "the guard denied a cp" --evidence s37ev/EV21
  [ "$status" -eq 0 ]
  [ "$(wc -l <"$BUG_NOTE_INBOX")" -eq 1 ]
  line=$(cat "$BUG_NOTE_INBOX")
  [ "$output" = "$line" ]
  [[ "$line" == '{"v":1,"ts":"'*'Z","reporter":"operator","symptom":"the guard denied a cp","evidence":"s37ev/EV21"}' ]]
}

@test "without --evidence the evidence field is null" {
  run bash "$BN" "no evidence"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"evidence":null}' ]]
}

@test "a quote, a backslash and a tab are escaped; the line stays one line" {
  run bash "$BN" "$(printf 'say "hi" \\ tab\there')"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"symptom":"say \"hi\" \\ tab\u0009here"'* ]]
  [ "$(wc -l <"$BUG_NOTE_INBOX")" -eq 1 ]
}

@test "the reporter is <run>/<KEY> inside a factory workspace marked by .factory-meta" {
  mkdir -p "$T/factory/ws/dsw1/DS1/sub"
  printf 'base_sha=abc\nbase_branch=main\n' >"$T/factory/ws/dsw1/DS1/.factory-meta"
  cd "$T/factory/ws/dsw1/DS1/sub"
  run bash "$BN" "from a seat"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"reporter":"dsw1/DS1"'* ]]
}

@test "BUG_NOTE_REPORTER overrides the derived reporter; a bad value is refused" {
  BUG_NOTE_REPORTER=plan/drafter run bash "$BN" "from a planner"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"reporter":"plan/drafter"'* ]]
  BUG_NOTE_REPORTER='bad value!' run bash "$BN" "x"
  [ "$status" -eq 2 ]
  [[ "$output" == *BUG_NOTE_REPORTER* ]]
  [ "$(wc -l <"$BUG_NOTE_INBOX")" -eq 1 ]
}

@test "malformed calls exit 2 with one stderr line and append nothing" {
  # One quoted call per refusal: a whitespace symptom must reach the script as
  # one argument, which an unquoted $args loop cannot deliver.
  run bash "$BN"
  [ "$status" -eq 2 ]
  [ "$(printf '%s\n' "$output" | wc -l)" -eq 1 ]
  [[ "$output" == bug-note:* ]]
  run bash "$BN" ""
  [ "$status" -eq 2 ]
  [ "$output" = "bug-note: the symptom is empty" ]
  run bash "$BN" "   "
  [ "$status" -eq 2 ]
  [ "$output" = "bug-note: the symptom is empty" ]
  run bash "$BN" --evidence
  [ "$status" -eq 2 ]
  [[ "$output" == bug-note:* ]]
  run bash "$BN" "x" --evidence
  [ "$status" -eq 2 ]
  [[ "$output" == bug-note:* ]]
  run bash "$BN" "x" --bogus
  [ "$status" -eq 2 ]
  [ "$output" = "bug-note: unknown option --bogus" ]
  run bash "$BN" "x" "y"
  [ "$status" -eq 2 ]
  [ "$output" = "bug-note: one symptom, then options" ]
  run bash "$BN" "$(printf 'two\nlines')"
  [ "$status" -eq 2 ]
  [ "$output" = "bug-note: the symptom must be one line" ]
  run bash "$BN" "$(head -c 2001 /dev/zero | tr '\0' a)"
  [ "$status" -eq 2 ]
  [ "$output" = "bug-note: the symptom is over 2000 bytes" ]
  run bash "$BN" "x" --evidence 'not a shape'
  [ "$status" -eq 2 ]
  [[ "$output" == bug-note:* ]]
  [ ! -e "$BUG_NOTE_INBOX" ]
}

@test "a 2000-byte symptom is accepted: the boundary is exact" {
  run bash "$BN" "$(head -c 2000 /dev/zero | tr '\0' a)"
  [ "$status" -eq 0 ]
  [ "$(wc -l <"$BUG_NOTE_INBOX")" -eq 1 ]
}

@test "each evidence shape is accepted: a path, run/KEY, a commit" {
  for ev in docs/ledger/bugs.toml ./x s37ev/EV21 abc1234 0123456789abcdef0123456789abcdef01234567; do
    run bash "$BN" "e" --evidence "$ev"
    [ "$status" -eq 0 ]
  done
  [ "$(wc -l <"$BUG_NOTE_INBOX")" -eq 5 ]
}

@test "an unwritable inbox exits 3 and names the path" {
  BUG_NOTE_INBOX=/proc/nope/inbox.jsonl run bash "$BN" "x"
  [ "$status" -eq 3 ]
  [[ "$output" == *"/proc/nope/inbox.jsonl"* ]]
}

@test "the investigate wrapper names the missing module and exits 2" {
  # A copy of the wrapper in an empty tree has no pkgs/evidence/debug_sweep.py
  # beside it. python3 on a missing file also exits 2, so the wrapper's own
  # line is the assertion, not the status alone.
  mkdir -p "$T/tree/tools/debug"
  cp "$INV" "$T/tree/tools/debug/investigate"
  run bash "$T/tree/tools/debug/investigate" --dry-run
  [ "$status" -eq 2 ]
  [ "$output" = "investigate: pkgs/evidence/debug_sweep.py is missing (DS3 lands it)" ]
}
