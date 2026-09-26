#!/usr/bin/env bats
# factory-integrate ingests reviews (plan 2026-09-06-telemetry-store-1, T3):
# after every check observation and the summary, `ingest_reviews()` hands the
# repo path and $FACTORY_RUNS to the evidence CLI (the fake recorder here).
# Like 80-seat-driver.bats, the factory root is overridden to the test tmpdir
# and the recorder is a script that echoes its arguments.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup_file() {
  bats_require_minimum_version 1.5.0
  # No test in this file may write to the operator's real runs dir.
  if [ -d "$HOME/factory/runs" ]; then
    LC_ALL=C ls -A1 "$HOME/factory/runs" 2>/dev/null |
      LC_ALL=C sort >"$BATS_FILE_TMPDIR/runs.before"
  else
    : >"$BATS_FILE_TMPDIR/runs.before"
  fi
}

teardown_file() {
  if [ -d "$HOME/factory/runs" ]; then
    LC_ALL=C ls -A1 "$HOME/factory/runs" 2>/dev/null |
      LC_ALL=C sort >"$BATS_FILE_TMPDIR/runs.after"
  else
    : >"$BATS_FILE_TMPDIR/runs.after"
  fi
  if ! diff -u "$BATS_FILE_TMPDIR/runs.before" "$BATS_FILE_TMPDIR/runs.after" >&2; then
    printf 'a test wrote to the real ~/factory/runs\n' >&2
    return 1
  fi
}

setup() {
  REAL_BASH="$(command -v bash)"
  export FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"
  export FACTORY_RUNS="$BATS_TEST_TMPDIR/factory/runs"
}

_fixture() {
  # A throwaway src repo with a task/K1 branch, a base clone, and a ws clone,
  # mirroring 80-seat-driver.bats so the integration can merge one key.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs"
  src="$BATS_TEST_TMPDIR/src"; git init -q -b main "$src"
  git -C "$src" config user.name t
  git -C "$src" config user.email t@x
  git -C "$src" commit -q --allow-empty -m "init"
  git clone -q "$src" "$root/base/src"
  git clone -q "$src" "$root/ws/r1/K1"
  git -C "$root/ws/r1/K1" config user.name t
  git -C "$root/ws/r1/K1" config user.email t@x
  git -C "$root/ws/r1/K1" checkout -q -b task/K1
  echo x >"$root/ws/r1/K1/x"; git -C "$root/ws/r1/K1" add x
  git -C "$root/ws/r1/K1" commit -q -m "k1: add x (test: unit, lint)"
}

@test "factory-integrate ingests reviews after a successful integration" {
  _fixture
  root="$BATS_TEST_TMPDIR/factory"; src="$BATS_TEST_TMPDIR/src"
  rec="$BATS_TEST_TMPDIR/rec.sh"; log="$BATS_TEST_TMPDIR/rec.log"
  printf '#!%s\nprintf "%%s\\n" "$*" >>%q\n' "$REAL_BASH" "$log" >"$rec"
  chmod +x "$rec"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true FACTORY_EVIDENCE_CMD="$rec" \
    EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev" \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 0 ]
  run tail -n 1 "$log"
  [ "$output" = "--store $BATS_TEST_TMPDIR/ev ingest reviews $src $root/runs" ]
}

@test "factory-integrate still exits 0 when the reviews ingest fails" {
  # ingest_reviews never changes overall_rc: a recorder that exits 1 leaves the
  # integration exit 0 and only prints the recording note. Mutant: set -e (a
  # bare call) -> the integration exits 1 and the note never prints.
  _fixture
  root="$BATS_TEST_TMPDIR/factory"; src="$BATS_TEST_TMPDIR/src"
  rec="$BATS_TEST_TMPDIR/rec.sh"
  printf '#!%s\nexit 1\n' "$REAL_BASH" >"$rec"
  chmod +x "$rec"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true FACTORY_EVIDENCE_CMD="$rec" \
    EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev" \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 0 ]
  [[ "$output" == *"evidence: could not record reviews"* ]]
}