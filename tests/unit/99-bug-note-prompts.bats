#!/usr/bin/env bats
# The one line every worker gets: note a defect outside your task with
# tools/debug/bug-note, never fix it (plan 2026-09-23-debug-sweep, DS6/DS6b).

setup() {
  REAL_BASH="$(command -v bash)"
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  PLAN="$BATS_TEST_TMPDIR/plan.md"
}

@test "factory-brief's bug-note bullet directly follows the no-push bullet in WORKSPACE RULES" {
  # The fixture plan's one typed heading is assembled by printf so that no
  # line of this test file begins with a typed heading.
  printf '### %s (code, XS) %s t\n\nbody one.\n' K1 '—' >"$PLAN"
  FACTORY_RUN=r1 FACTORY_MODEL=z-ai/glm-5.3 \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1
  [ "$status" -eq 0 ]
  [[ "$output" == *"tools/debug/bug-note"* ]]
  [[ "$output" == *"is noted, never fixed"* ]]
  head_ln=$(printf '%s\n' "$output" | grep -nF '## WORKSPACE RULES' | head -1 | cut -d: -f1)
  push_ln=$(printf '%s\n' "$output" | grep -nxF -- '- Never `git push`.' | head -1 | cut -d: -f1)
  note_ln=$(printf '%s\n' "$output" | grep -nF -- '- A defect you meet outside this task' | head -1 | cut -d: -f1)
  [ -n "$head_ln" ]
  [ -n "$push_ln" ]
  [ -n "$note_ln" ]
  [ "$head_ln" -lt "$push_ln" ]
  [ "$note_ln" -eq $((push_ln + 1)) ]
}

@test "factory-review's sentence sits inside the brief heredoc, every backtick there escaped" {
  # The sentence's line must lie between `brief=$(` and that heredoc's
  # closing EOF line, and the heredoc is unquoted (cat <<EOF): an unescaped
  # backtick there would run a command substitution when the brief is built.
  f="$SEAT/factory-review"
  brief_ln=$(grep -nF 'brief=$(' "$f" | head -1 | cut -d: -f1)
  [ -n "$brief_ln" ]
  end_ln=$(awk -v s="$brief_ln" 'NR > s && $0 == "EOF" { print NR; exit }' "$f")
  [ -n "$end_ln" ]
  sent_ln=$(grep -nF 'not a finding against the seat' "$f" | head -1 | cut -d: -f1)
  [ -n "$sent_ln" ]
  [ "$brief_ln" -lt "$sent_ln" ]
  [ "$sent_ln" -lt "$end_ln" ]
  awk -v s="$brief_ln" -v e="$end_ln" 'NR > s && NR < e' "$f" | grep -qF 'tools/debug/bug-note'
  bare=$(awk -v s="$brief_ln" -v e="$end_ln" 'NR > s && NR < e' "$f" | grep -cE '(^|[^\\])`' || true)
  [ "$bare" -eq 0 ]
}
