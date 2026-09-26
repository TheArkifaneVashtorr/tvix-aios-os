#!/usr/bin/env bats
# tools/debug/investigate -- the wrapper execs pkgs/evidence/debug_sweep.py
# (plan 2026-09-23-debug-sweep, DS3): argparse runs with prog="investigate".

@test "investigate --help prints a usage line and exits 0" {
  run bash "$BATS_TEST_DIRNAME/../../tools/debug/investigate" --help
  [ "$status" -eq 0 ]
  [[ "$output" == usage:\ investigate* ]]
}
