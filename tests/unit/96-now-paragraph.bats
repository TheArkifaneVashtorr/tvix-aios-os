#!/usr/bin/env bats
# The Now-paragraph rule (CR4/CR4b) lives in tests/lint/now-paragraph.sh and is
# called from both githooks/pre-commit and checks.lint. These rows run that
# script against its own fixtures and against the repo's REAL board the way the
# two callers do, so the rule's verdict on the live board is asserted, not
# assumed.

SCRIPT="$BATS_TEST_DIRNAME/../lint/now-paragraph.sh"

@test "now-paragraph self-test passes against its boundary fixtures" {
  run bash "$SCRIPT" --self-test
  [ "$status" -eq 0 ]
}

@test "now-paragraph accepts the real board's Now paragraph" {
  run bash "$SCRIPT" "$BATS_TEST_DIRNAME/../../docs/OPERATIONS.md"
  [ "$status" -eq 0 ]
}