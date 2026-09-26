#!/usr/bin/env bats
# The board-shape rule (KN17, 50a/51a) lives in tests/lint/now-paragraph.sh and
# is called from both githooks/pre-commit and checks.lint. These rows run that
# script against its own fixtures, against the repo's REAL board, and against a
# board with a hand-typed line after the block, the way the two callers do, so
# the rule's verdict on the live board is asserted, not assumed.

SCRIPT="$BATS_TEST_DIRNAME/../lint/now-paragraph.sh"

@test "now-paragraph self-test passes against its boundary fixtures" {
  run bash "$SCRIPT" --self-test
  [ "$status" -eq 0 ]
}

@test "now-paragraph accepts the real board's shape" {
  run bash "$SCRIPT" "$BATS_TEST_DIRNAME/../../docs/OPERATIONS.md"
  [ "$status" -eq 0 ]
}

@test "now-paragraph rejects a board with a hand-typed line after the block" {
  cp "$BATS_TEST_DIRNAME/../../docs/OPERATIONS.md" "$BATS_TEST_TMPDIR/after"
  chmod +w "$BATS_TEST_TMPDIR/after"
  echo "a hand-typed line" >>"$BATS_TEST_TMPDIR/after"
  run bash "$SCRIPT" "$BATS_TEST_TMPDIR/after"
  [ "$status" -eq 1 ]
  [[ "$output" == *"prose outside the derived block"* ]]
}