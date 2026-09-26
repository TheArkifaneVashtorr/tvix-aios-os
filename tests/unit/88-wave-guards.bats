#!/usr/bin/env bats
# DF7/DF7b: factory-wave guards. (a) BUG-run-name-reuse: a run whose
# $FACTORY_RUNS/<run>/run.meta already exists is refused (exit 2, nothing
# written) only for a live wave (its run.meta pid still answers kill -0) or a
# different plan (its run.meta plan differs from FACTORY_PLAN's realpath) --
# the second is lifted by FACTORY_WAVE_REUSE=1, the first never; a dead wave of
# the same plan is reused with a reusing-run line. (b) BUG-double-submit:
# within one run, a key whose <runs_dir>/<KEY>.lock/pid names a live
# factory-task is not submitted again -- factory-task is never invoked, a
# status=skipped .result is written and the rest of its chain is skipped too; a
# stale (dead-pid) lock and a recycled pid (live but not factory-task) are both
# reclaimed, and the lock is released after the task returns whatever its exit
# code. This file is self-contained: it builds the whole fake harness and
# touches no other test file.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup() {
  REAL_BASH="$(command -v bash)"
  export FACTORY_ROOT="$BATS_TEST_TMPDIR/factory" FACTORY_RUNS="$BATS_TEST_TMPDIR/factory/runs"

  # A fake factory-task recorded by factory-wave via FACTORY_BIN_OVERRIDE: it
  # appends each key it is asked to run to invocations and writes a done
  # result. $1 == run, $2 == repo-path, $3 == key.
  fbin="$BATS_TEST_TMPDIR/fakebin"
  mkdir -p "$fbin"
  printf '#!%s\n' "$REAL_BASH" >"$fbin/factory-task"
  cat >>"$fbin/factory-task" <<'FAKE'
run=$1
key=$3
mkdir -p "$FACTORY_RUNS/$run"
printf '%s\n' "$key" >>"$FACTORY_RUNS/$run/invocations"
printf 'FACTORY-RESULT status=done\nFACTORY-CHECKS none=not-run\nFACTORY-COMMITS 0\nFACTORY-NOTES fake\n' >"$FACTORY_RUNS/$run/$key.result"
FAKE
  chmod +x "$fbin/factory-task"

  # A two-key plan and an empty (non-git) repo directory; factory-wave records
  # base: from the repo and tolerates a non-git directory.
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'PLAN'
### K1 (code, S) — t

body.

### K2 (code, S) — t

body.
PLAN
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$repo"

  # A live holder whose /proc/<pid>/cmdline names factory-wave -- the process
  # that actually writes a key lock (factory-wave's own group subshell), never
  # a script with another name. A bare sleep is a *recycled* pid, not this.
  # The TERM trap reaps the sleep child, so killing LOCK_PID leaves no orphan.
  fhold="$BATS_TEST_TMPDIR/fakebin/factory-wave"
  printf '#!%s\n' "$REAL_BASH" >"$fhold"
  cat >>"$fhold" <<'HOLD'
trap 'kill "$sp" 2>/dev/null; exit 0' TERM
sleep 300 &
sp=$!
wait
HOLD
  chmod +x "$fhold"

  # A live factory-task -- the orphan's specimen (BUG-double-submit-orphan,
  # DF12). Invoked with run/repo/key so its /proc/<pid>/cmdline names
  # factory-task and carries the run and key as argv, and it sleeps to stay
  # live while its wave is gone. It lives in its own directory so it never
  # collides with the $fbin fake that factory-wave itself invokes.
  fodir="$BATS_TEST_TMPDIR/holdbin"
  mkdir -p "$fodir"
  printf '#!%s\n' "$REAL_BASH" >"$fodir/factory-task"
  cat >>"$fodir/factory-task" <<'ORPHAN'
trap 'kill "$sp" 2>/dev/null; exit 0' TERM
sleep 300 &
sp=$!
wait
ORPHAN
  chmod +x "$fodir/factory-task"
}

teardown() {
  if [ -n "${TASK_PID:-}" ]; then
    kill "$TASK_PID" 2>/dev/null || true
    wait "$TASK_PID" 2>/dev/null || true
  fi
  if [ -n "${LOCK_PID:-}" ]; then
    kill "$LOCK_PID" 2>/dev/null || true
    wait "$LOCK_PID" 2>/dev/null || true
  fi
}

@test "factory-wave refuses a run name whose run.meta exists" {
  mkdir -p "$FACTORY_RUNS/r1"
  printf 'launched: 2026-09-05T00:00:00Z\n' >"$FACTORY_RUNS/r1/run.meta"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 2 ]
  [[ "$output" == *"already exists"* ]]
  [ ! -e "$FACTORY_RUNS/r1/invocations" ]
}

@test "FACTORY_WAVE_REUSE=1 proceeds" {
  mkdir -p "$FACTORY_RUNS/r1"
  printf 'launched: 2026-09-05T00:00:00Z\n' >"$FACTORY_RUNS/r1/run.meta"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" FACTORY_WAVE_REUSE=1 \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 0 ]
  [ "$(wc -l <"$FACTORY_RUNS/r1/invocations")" -eq 1 ]
}

@test "factory-wave skips a key whose lock pid is alive" {
  mkdir -p "$FACTORY_RUNS/r1/K1.lock"
  "$fhold" &
  LOCK_PID=$!
  printf '%s\n' "$LOCK_PID" >"$FACTORY_RUNS/r1/K1.lock/pid"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"

  [ ! -e "$FACTORY_RUNS/r1/invocations" ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"status=skipped"* ]]
  [[ "$output" == *"already live under pid"* ]]
}

@test "a stale lock is removed and the key runs once" {
  # A pid guaranteed dead: one above the kernel's pid_max cap (re-read at run
  # time, so the test never guesses the machine's limit).
  pid_max=$(cat /proc/sys/kernel/pid_max 2>/dev/null || printf '4194304')
  stale_pid=$((pid_max + 1))
  mkdir -p "$FACTORY_RUNS/r1/K1.lock"
  printf '%s\n' "$stale_pid" >"$FACTORY_RUNS/r1/K1.lock/pid"
  kill -0 "$stale_pid" 2>/dev/null && skip "pid $stale_pid is unexpectedly live"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 0 ]
  [ "$(wc -l <"$FACTORY_RUNS/r1/invocations")" -eq 1 ]
  [ ! -d "$FACTORY_RUNS/r1/K1.lock" ]
}

# --- DF7b: the reuse rule and the lock guards ---------------------------

@test "a dead wave of the same plan is reused and logs reusing run" {
  # A run.meta whose pid is dead and whose plan is FACTORY_PLAN's realpath: a
  # finished wave of the same plan, so wave 2 proceeds (both keys run) and the
  # reusing-run line appears.
  mkdir -p "$FACTORY_RUNS/r1"
  pid_max=$(cat /proc/sys/kernel/pid_max 2>/dev/null || printf '4194304')
  dead_pid=$((pid_max + 1))
  kill -0 "$dead_pid" 2>/dev/null && skip "pid $dead_pid is unexpectedly live"
  {
    printf 'run: r1\n'
    printf 'plan: %s\n' "$(realpath "$plan")"
    printf 'pid: %s\n' "$dead_pid"
    printf 'launched: 2026-09-05T00:00:00Z\n'
  } >"$FACTORY_RUNS/r1/run.meta"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1 K2"

  [ "$status" -eq 0 ]
  [[ "$output" == *"reusing run"* ]]
  [ -f "$FACTORY_RUNS/r1/K1.result" ]
  [ -f "$FACTORY_RUNS/r1/K2.result" ]
}

@test "a live wave is refused even with FACTORY_WAVE_REUSE=1" {
  # A run.meta whose pid is a live factory-wave (the holder rule: kill -0 AND
  # cmdline names factory-wave): a double launch, refused whatever
  # FACTORY_WAVE_REUSE says (a live double launch has no legitimate form).
  mkdir -p "$FACTORY_RUNS/r1"
  "$fhold" &
  LOCK_PID=$!
  {
    printf 'run: r1\n'
    printf 'plan: %s\n' "$(realpath "$plan")"
    printf 'pid: %s\n' "$LOCK_PID"
    printf 'launched: 2026-09-05T00:00:00Z\n'
  } >"$FACTORY_RUNS/r1/run.meta"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" FACTORY_WAVE_REUSE=1 \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"

  [ "$status" -eq 2 ]
  [ ! -e "$FACTORY_RUNS/r1/invocations" ]
}

@test "another plan's run is refused without FACTORY_WAVE_REUSE=1 and reused with it" {
  # A run.meta whose plan differs from FACTORY_PLAN's realpath (another plan's
  # leftovers): refused without the override, reused with it (the pid is dead).
  mkdir -p "$FACTORY_RUNS/r1"
  {
    printf 'run: r1\n'
    printf 'plan: %s\n' "$BATS_TEST_TMPDIR/other-plan.md"
    printf 'pid: 999999\n'
    printf 'launched: 2026-09-05T00:00:00Z\n'
  } >"$FACTORY_RUNS/r1/run.meta"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 2 ]
  [[ "$output" == *"already exists"* ]]
  [ ! -e "$FACTORY_RUNS/r1/invocations" ]

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" FACTORY_WAVE_REUSE=1 \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 0 ]
  [[ "$output" == *"reusing run"* ]]
  [ "$(wc -l <"$FACTORY_RUNS/r1/invocations")" -eq 1 ]
}

@test "a lock-skipped key skips the rest of its chain" {
  # "K1 K2" with K1's lock held by a live factory-task: K1 is skipped, and so
  # is every later key of the chain (K2), with nothing invoked.
  mkdir -p "$FACTORY_RUNS/r1/K1.lock"
  "$fhold" &
  LOCK_PID=$!
  printf '%s\n' "$LOCK_PID" >"$FACTORY_RUNS/r1/K1.lock/pid"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1 K2"

  [ ! -e "$FACTORY_RUNS/r1/invocations" ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"status=skipped"* ]]
  run cat "$FACTORY_RUNS/r1/K2.result"
  [[ "$output" == *"status=skipped"* ]]
}

@test "the lock is released on a non-zero task exit" {
  # A fake factory-task that exits 1 (fails): the lock is released whatever the
  # exit code, so no lock dir is left behind.
  printf '#!%s\n' "$REAL_BASH" >"$fbin/factory-task"
  cat >>"$fbin/factory-task" <<'FAKE'
run=$1
key=$3
mkdir -p "$FACTORY_RUNS/$run"
printf '%s\n' "$key" >>"$FACTORY_RUNS/$run/invocations"
exit 1
FAKE
  chmod +x "$fbin/factory-task"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"

  [ ! -d "$FACTORY_RUNS/r1/K1.lock" ]
}

@test "unlock refuses a lock another pid owns" {
  # factory_key_unlock removes a lock only when its pid is this shell's
  # $BASHPID; a lock another pid owns is left alone.
  . "$SEAT/factory-lib.sh"
  mkdir -p "$FACTORY_RUNS/r1/K1.lock"
  printf '999999\n' >"$FACTORY_RUNS/r1/K1.lock/pid"

  factory_key_unlock "$FACTORY_RUNS/r1" K1

  [ -d "$FACTORY_RUNS/r1/K1.lock" ]
  [ "$(cat "$FACTORY_RUNS/r1/K1.lock/pid")" = "999999" ]
}

@test "a live lock whose pid is not factory-wave is stale" {
  # A live pid whose cmdline names neither factory-wave nor factory-task (here
  # a bare sleep): a recycled pid, so the lock is stale and the key runs rather
  # than being skipped.
  mkdir -p "$FACTORY_RUNS/r1/K1.lock"
  sleep 300 &
  LOCK_PID=$!
  printf '%s\n' "$LOCK_PID" >"$FACTORY_RUNS/r1/K1.lock/pid"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"

  [ "$(wc -l <"$FACTORY_RUNS/r1/invocations")" -eq 1 ]
}

@test "two groups naming one key in one wave submit it once" {
  # DF7b's E1: a wave whose two groups both name K1. The first group holds the
  # key's lock while its (sleeping) fake runs; the second group's submit must be
  # refused -- the fake runs once, and the skip note names the live holder's
  # pid. The fake writes no result, so the loser's status=skipped result is the
  # one left behind.
  printf '#!%s\n' "$REAL_BASH" >"$fbin/factory-task"
  cat >>"$fbin/factory-task" <<'FAKE'
run=$1
key=$3
mkdir -p "$FACTORY_RUNS/$run"
printf '%s\n' "$key" >>"$FACTORY_RUNS/$run/invocations"
sleep 2
FAKE
  chmod +x "$fbin/factory-task"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1" "K1"

  [ "$status" -eq 1 ]
  [ "$(wc -l <"$FACTORY_RUNS/r1/invocations")" -eq 1 ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"status=skipped"* ]]
  [[ "$output" == *"already live under pid"* ]]
}

@test "an empty pre-created run directory is admitted silently" {
  # factory-dispatch mkdir -p's the run directory before the first wave; an
  # empty one (no run.meta, no results) is a fresh start, admitted with no
  # reusing-run or refusal line.
  mkdir -p "$FACTORY_RUNS/r1"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"

  [ "$status" -eq 0 ]
  [[ "$output" != *"reusing run"* ]]
  [[ "$output" != *"already exists"* ]]
  [ "$(wc -l <"$FACTORY_RUNS/r1/invocations")" -eq 1 ]
}

@test "a run directory with results and no run.meta is refused" {
  # Another run's leftovers (a .result, no run.meta): the original
  # BUG-run-name-reuse symptom, refused before anything is written.
  mkdir -p "$FACTORY_RUNS/r1"
  printf 'FACTORY-RESULT status=done\n' >"$FACTORY_RUNS/r1/OLD.result"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"

  [ "$status" -eq 2 ]
  [[ "$output" == *"already exists"* ]]
  [ ! -e "$FACTORY_RUNS/r1/invocations" ]
}

@test "the skip note names its parent" {
  # A lock-skipped first key must record prev before continue, so the synthetic
  # skip note for the next key names the parent (after K1), not an empty parent.
  mkdir -p "$FACTORY_RUNS/r1/K1.lock"
  "$fhold" &
  LOCK_PID=$!
  printf '%s\n' "$LOCK_PID" >"$FACTORY_RUNS/r1/K1.lock/pid"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1 K2"

  run cat "$FACTORY_RUNS/r1/K2.result"
  [[ "$output" == *"after K1"* ]]
}

@test "reusing run prints the pid it read" {
  # The reusing-run line names the run.meta pid it read, never `?`; with no
  # pid: line it reads `unknown` (the DF7b bug printed `pid ?`).
  mkdir -p "$FACTORY_RUNS/r1"
  pid_max=$(cat /proc/sys/kernel/pid_max 2>/dev/null || printf '4194304')
  dead_pid=$((pid_max + 1))
  kill -0 "$dead_pid" 2>/dev/null && skip "pid $dead_pid is unexpectedly live"
  {
    printf 'run: r1\n'
    printf 'plan: %s\n' "$(realpath "$plan")"
    printf 'pid: %s\n' "$dead_pid"
  } >"$FACTORY_RUNS/r1/run.meta"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 0 ]
  [[ "$output" == *"previous wave pid $dead_pid dead"* ]]

  # No pid: line -> `unknown`, never `?`.
  mkdir -p "$FACTORY_RUNS/r2"
  printf 'run: r2\nplan: %s\n' "$(realpath "$plan")" >"$FACTORY_RUNS/r2/run.meta"
  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r2 "$repo" "K1"
  [ "$status" -eq 0 ]
  [[ "$output" == *"previous wave pid unknown"* ]]
  [[ "$output" != *"pid ?"* ]]
}

# --- DF12: an orphan factory-task refuses the resubmit --------------------

@test "an orphan factory-task refuses the resubmit" {
  # A wave SIGKILLed mid-run leaves its factory-task alive while the wave group
  # subshell that wrote the key lock is dead: <KEY>.lock/pid names a dead pid,
  # but the key's own <KEY>.pid names the still-running task. The relaunch must
  # NOT reclaim and resubmit -- the orphan's own one invocation stands and the
  # skip note names the orphan.
  mkdir -p "$FACTORY_RUNS/r1"
  pid_max=$(cat /proc/sys/kernel/pid_max 2>/dev/null || printf '4194304')
  dead_pid=$((pid_max + 1))
  kill -0 "$dead_pid" 2>/dev/null && skip "pid $dead_pid is unexpectedly live"
  {
    printf 'run: r1\n'
    printf 'plan: %s\n' "$(realpath "$plan")"
    printf 'pid: %s\n' "$dead_pid"
    printf 'launched: 2026-09-05T00:00:00Z\n'
  } >"$FACTORY_RUNS/r1/run.meta"
  # The one dispatch that already happened (the orphan's own).
  printf 'K1\n' >"$FACTORY_RUNS/r1/invocations"
  mkdir -p "$FACTORY_RUNS/r1/K1.lock"
  printf '%s\n' "$dead_pid" >"$FACTORY_RUNS/r1/K1.lock/pid"
  "$fodir/factory-task" r1 "$repo" K1 &
  TASK_PID=$!
  printf '%s\n' "$TASK_PID" >"$FACTORY_RUNS/r1/K1.pid"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"

  [ "$(wc -l <"$FACTORY_RUNS/r1/invocations")" -eq 1 ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"status=skipped"* ]]
  [[ "$output" == *"orphan"* ]]
  [[ "$output" == *"$TASK_PID"* ]]
}

@test "a dead task pid file is stale" {
  # A <KEY>.pid whose task process is dead (the task finished and, its wave
  # having died, nothing reaped the record) must not block: the stale lock is
  # reclaimed and the key runs.
  mkdir -p "$FACTORY_RUNS/r1"
  pid_max=$(cat /proc/sys/kernel/pid_max 2>/dev/null || printf '4194304')
  dead_pid=$((pid_max + 1))
  kill -0 "$dead_pid" 2>/dev/null && skip "pid $dead_pid is unexpectedly live"
  {
    printf 'run: r1\n'
    printf 'plan: %s\n' "$(realpath "$plan")"
    printf 'pid: %s\n' "$dead_pid"
    printf 'launched: 2026-09-05T00:00:00Z\n'
  } >"$FACTORY_RUNS/r1/run.meta"
  mkdir -p "$FACTORY_RUNS/r1/K1.lock"
  printf '%s\n' "$dead_pid" >"$FACTORY_RUNS/r1/K1.lock/pid"
  printf '%s\n' "$dead_pid" >"$FACTORY_RUNS/r1/K1.pid"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"

  [ "$status" -eq 0 ]
  [ "$(wc -l <"$FACTORY_RUNS/r1/invocations")" -eq 1 ]
}

@test "a recycled pid whose argv names another key is stale" {
  # A live pid whose cmdline names factory-task but a DIFFERENT key (another
  # task's orphan) is a recycled pid, not this key's holder: the lock is stale
  # and the key runs.
  mkdir -p "$FACTORY_RUNS/r1"
  pid_max=$(cat /proc/sys/kernel/pid_max 2>/dev/null || printf '4194304')
  dead_pid=$((pid_max + 1))
  kill -0 "$dead_pid" 2>/dev/null && skip "pid $dead_pid is unexpectedly live"
  {
    printf 'run: r1\n'
    printf 'plan: %s\n' "$(realpath "$plan")"
    printf 'pid: %s\n' "$dead_pid"
    printf 'launched: 2026-09-05T00:00:00Z\n'
  } >"$FACTORY_RUNS/r1/run.meta"
  mkdir -p "$FACTORY_RUNS/r1/K1.lock"
  printf '%s\n' "$dead_pid" >"$FACTORY_RUNS/r1/K1.lock/pid"
  "$fodir/factory-task" r1 "$repo" K2 &
  TASK_PID=$!
  printf '%s\n' "$TASK_PID" >"$FACTORY_RUNS/r1/K1.pid"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"

  [ "$status" -eq 0 ]
  [ "$(wc -l <"$FACTORY_RUNS/r1/invocations")" -eq 1 ]
  [[ "$(cat "$FACTORY_RUNS/r1/invocations")" == "K1" ]]
}

# --- ER12 (FA33b, 2026-09-24): an outer `timeout` parent refuses -----------
# factory-task before any workspace, run dir, log or .result exists: the outer
# timeout kills the collector while the seat runs on and the result gets
# hand-written. Only an exactly-named `timeout` parent refuses (a wrapper
# named timeout-wrapper runs), and FACTORY_ALLOW_TIMEOUT_PARENT=1 lifts the
# refusal with one log line (a bats harness under a CI timeout, if ever).

# The full driver harness the way 87-prior-attempt.bats drives factory-task:
# a seat copy with a stubbed factory-ws (prints a plain workspace path, so no
# .factory-meta -- the run ends at the seat's own done result), a routing
# toolbox, and a fake seat-submit on PATH. Sets e12_seat, e12_fx, e12_bin,
# e12_root and e12_share.
er12_harness() {
  e12_seat="$BATS_TEST_TMPDIR/seat"
  cp -r "$SEAT" "$e12_seat"
  chmod -R u+w "$e12_seat"
  sed -i "1s@.*@#!$REAL_BASH@" "$e12_seat/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$e12_seat/factory-ws"
  chmod +x "$e12_seat/factory-ws"

  e12_fx="$BATS_TEST_TMPDIR/toolbox"
  mkdir -p "$e12_fx/docs/ledger"
  cat >"$e12_fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/a"
effort = "medium"
EOF

  e12_bin="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$e12_bin"
  cat >"$e12_bin/seat-submit" <<FAKE
#!$REAL_BASH
if [ "\$1" = "--help" ]; then
  printf 'usage: seat-submit --task RUN/KEY [options]\n'
  exit 0
fi
printf '20260924-120000-0abcde\n'
printf 'FACTORY-RESULT status=done\n'
printf 'FACTORY-CHECKS none=not-run\n'
printf 'FACTORY-COMMITS 0\n'
printf 'FACTORY-NOTES fake seat ran\n'
FAKE
  chmod +x "$e12_bin/seat-submit"

  e12_root="$BATS_TEST_TMPDIR/factory"
  e12_share="$BATS_TEST_TMPDIR/share"
  mkdir -p "$e12_share"
}

@test "factory-task refuses to run under a timeout parent" {
  er12_harness

  # (a) the refusal: under an outer `timeout`, exit 2 with the message on
  # stderr and nothing written -- no run dir yet.
  FACTORY_ROOT="$e12_root" FACTORY_TOOLBOX_REPO="$e12_fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$e12_share" PATH="$e12_bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run timeout 60 "$REAL_BASH" "$e12_seat/factory-task" r1 "$repo" K1
  [ "$status" -eq 2 ]
  [[ "$output" == *"refusing to run under timeout"* ]]
  [ ! -e "$FACTORY_RUNS/r1" ]

  # (b) the control: the same command without the timeout parent runs the
  # seat -- the refusal is caused by the timeout parent, not the arguments.
  FACTORY_ROOT="$e12_root" FACTORY_TOOLBOX_REPO="$e12_fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$e12_share" PATH="$e12_bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$e12_seat/factory-task" r1 "$repo" K1
  [ "$status" -ne 2 ]
  [ -d "$FACTORY_RUNS/r1" ]

  # (d) an exactly-named `timeout` parent only: a wrapper whose comm is
  # timeout-wrapper (a shebang script that stays the parent of its command) is
  # not coreutils timeout, so the seat runs.
  printf '#!%s\n"$@"\n' "$REAL_BASH" >"$BATS_TEST_TMPDIR/timeout-wrapper"
  chmod +x "$BATS_TEST_TMPDIR/timeout-wrapper"
  FACTORY_ROOT="$e12_root" FACTORY_TOOLBOX_REPO="$e12_fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$e12_share" PATH="$e12_bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$BATS_TEST_TMPDIR/timeout-wrapper" "$REAL_BASH" "$e12_seat/factory-task" r1 "$repo" K1
  [ "$status" -ne 2 ]
  [ -d "$FACTORY_RUNS/r1" ]
}

@test "FACTORY_ALLOW_TIMEOUT_PARENT=1 lets factory-task run under a timeout parent" {
  er12_harness

  # (c) the escape: one log line, then the control's outcome -- the seat runs
  # and the run dir exists.
  FACTORY_ROOT="$e12_root" FACTORY_TOOLBOX_REPO="$e12_fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$e12_share" PATH="$e12_bin:$PATH" \
    FACTORY_ALLOW_TIMEOUT_PARENT=1 OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run timeout 60 "$REAL_BASH" "$e12_seat/factory-task" r1 "$repo" K1
  [ "$status" -ne 2 ]
  [ -d "$FACTORY_RUNS/r1" ]
  [[ "$output" == *"running under a timeout parent (FACTORY_ALLOW_TIMEOUT_PARENT=1)"* ]]
}
