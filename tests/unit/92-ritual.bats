#!/usr/bin/env bats
# tools/ritual.sh is the context-reset ritual hooks (.claude/settings.json):
# stop blocks a turn that would leave durable state uncommitted or the board
# stale; precompact writes a derived handoff; inflight lists live seat runs.
# These tests run it against a fake repo, a fake `evidence` binary and a fake
# ~/factory runs dir; all hook state lives under $XDG_STATE_HOME.

SCRIPT="$BATS_TEST_DIRNAME/../../tools/ritual.sh"

bats_require_minimum_version 1.5.0

# make_board_stale -- a marker under the repo root that the tree's renderer
# stub (below) reads as "stale" (exit 1), without touching a tracked file, so
# the board check blocks while the tree stays clean (no dirty check fires).
make_board_stale() {
  touch "$REPO/.stale-board"
}

setup() {
  REAL_BASH="$(command -v bash)"
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO/docs/reviews" "$REPO/.claude" "$REPO/pkgs/evidence" "$BATS_TEST_TMPDIR/bin"
  # The board check must run the TREE's renderer, so the fake repo carries a
  # minimal stub at the path the ritual invokes ($repo/pkgs/evidence/tasks.py).
  # It is a stub rather than a copy of the real tasks.py because the unit
  # sandbox does not ship pkgs/evidence; the real renderer's own derivation is
  # covered by evidence-unit and the live host probe. The stub is "current"
  # (exit 0) unless a .stale-board marker exists, letting each test pin current
  # vs stale.
  cat >"$REPO/pkgs/evidence/tasks.py" <<'PYEOF'
import os, sys
args = sys.argv[1:]
root = args[args.index("--root") + 1] if "--root" in args else "."
sys.exit(1 if os.path.exists(os.path.join(root, ".stale-board")) else 0)
PYEOF
  git -C "$BATS_TEST_TMPDIR" init -q "$REPO"
  git -C "$REPO" config user.email t@x
  git -C "$REPO" config user.name t
  printf '# Operations board\n\n## START HERE (today)\n\nQueued: CR1.\n' >"$REPO/docs/OPERATIONS.md"
  touch "$REPO/docs/reviews/.gitkeep"
  git -C "$REPO" add docs/OPERATIONS.md docs/reviews/.gitkeep
  git -C "$REPO" commit -qm "board"
  # The checks.unit sandbox has no /usr/bin/env, so the fake binary carries the
  # real bash's absolute path as its shebang (same trick as 80-seat-driver.bats).
  # It exits with EVIDENCE_RC whenever `check --board` is requested.
  {
    printf '#!%s\n' "$REAL_BASH"
    cat <<'EOF'
for a in "$@"; do
  [ "$a" = "--board" ] && exit "${EVIDENCE_RC:-0}"
done
echo "unexpected: $*" >&2
exit 9
EOF
  } >"$BATS_TEST_TMPDIR/bin/evidence"
  chmod +x "$BATS_TEST_TMPDIR/bin/evidence"
  XDG_STATE_HOME="$BATS_TEST_TMPDIR/state"
  FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"
  STATEDIR="$XDG_STATE_HOME/nixos-agent-env/ritual"
  __stdin='{"session_id":"s1","stop_hook_active":false}'
  EVIDENCE_RC=0
}

# ritual <cmd> [repo] runs the hook against a controlled env, feeding $__stdin
# (JSON) on stdin.
ritual() {
  local cmd=$1
  shift
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
    RITUAL_EVIDENCE="$BATS_TEST_TMPDIR/bin/evidence" \
    EVIDENCE_RC="${EVIDENCE_RC:-0}" \
    bash "$SCRIPT" "$cmd" "$@" <<< "$__stdin"
}

# --- stop ---------------------------------------------------------------

@test "stop blocks on an untracked review file, naming the path in the JSON" {
  touch "$REPO/docs/reviews/x.md"
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"decision":"block"'* ]]
  [[ "$output" == *"docs/reviews/x.md"* ]]
}

@test "stop blocks on a modified plan section" {
  mkdir -p "$REPO/docs/superpowers/plans"
  echo x >"$REPO/docs/superpowers/plans/p.md"
  git -C "$REPO" add docs/superpowers/plans/p.md
  git -C "$REPO" commit -qm "plan"
  echo y >>"$REPO/docs/superpowers/plans/p.md"
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"decision":"block"'* ]]
  [[ "$output" == *"commit or revert"* ]]
}

@test "a clean tree with a clean board check is silent and stamps last-stop" {
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [ -f "$STATEDIR/last-stop" ]
}

@test "a stale board check blocks naming write-board" {
  make_board_stale
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"decision":"block"'* ]]
  [[ "$output" == *"write-board"* ]]
}

@test "the third block in one session allows and appends to ritual.log" {
  touch "$REPO/docs/reviews/x.md"
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"decision":"block"'* ]]
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"decision":"block"'* ]]
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [[ "$(cat "$STATEDIR/ritual.log")" == *"allowed after 2 blocks"* ]]
}

@test "a block counter is reset once a later run is clean" {
  touch "$REPO/docs/reviews/x.md"
  ritual stop "$REPO"
  [[ "$output" == *'"decision":"block"'* ]]
  ritual stop "$REPO"
  [[ "$output" == *'"decision":"block"'* ]]
  rm "$REPO/docs/reviews/x.md"
  ritual stop "$REPO"
  [ -z "$output" ]
  touch "$REPO/docs/reviews/y.md"
  ritual stop "$REPO"
  [[ "$output" == *'"decision":"block"'* ]]
}

@test "the ritual override file allows and reports the override" {
  touch "$REPO/.claude/ritual-override"
  touch "$REPO/docs/reviews/x.md"
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" != *'"decision":"block"'* ]]
  [[ "$output" == *"override present"* ]]
}

@test "stop is silent for a factory agent" {
  touch "$REPO/docs/reviews/x.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
    FACTORY_RUN=ev3 \
    bash "$SCRIPT" stop "$REPO" <<< '{"session_id":"s1"}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "stop is silent in a linked worktree" {
  git -C "$REPO" worktree add -q "$BATS_TEST_TMPDIR/wt" -b wt
  mkdir -p "$BATS_TEST_TMPDIR/wt/docs" && cp "$REPO/docs/OPERATIONS.md" "$BATS_TEST_TMPDIR/wt/docs/"
  ritual stop "$BATS_TEST_TMPDIR/wt"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "malformed stdin degrades to allow with a warning" {
  __stdin='not json at all'
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$(printf '%s' "$output" | grep 'decision')" ]
  [[ "$output" == *"allowing"* ]]
}

# --- board debt ---------------------------------------------------------

@test "six review commits since the board commit block on debt" {
  for i in 1 2 3 4 5 6; do
    printf 'x\n' >"$REPO/docs/reviews/r$i.md"
    git -C "$REPO" add docs/reviews/r$i.md
    git -C "$REPO" commit -qm "review $i"
  done
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"decision":"block"'* ]]
  [[ "$output" == *"board was last written"* ]]
}

@test "five review commits since the board commit still allow" {
  for i in 1 2 3 4 5; do
    printf 'x\n' >"$REPO/docs/reviews/r$i.md"
    git -C "$REPO" add docs/reviews/r$i.md
    git -C "$REPO" commit -qm "review $i"
  done
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- precompact ---------------------------------------------------------

@test "precompact writes a handoff naming the dirty path, leaving the repo untouched" {
  touch "$REPO/docs/reviews/x.md"
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log line\n' >"$FACTORY_ROOT/runs/r1/K.log"
  before=$(git -C "$REPO" status --short)
  __stdin='{"session_id":"s1","trigger":"manual"}'
  ritual precompact "$REPO"
  [ "$status" -eq 0 ]
  handoff="$STATEDIR/handoff-s1.md"
  [ -f "$handoff" ]
  [[ "$(cat "$handoff")" == *"docs/reviews/x.md"* ]]
  [ "$(git -C "$REPO" status --short)" = "$before" ]
}

@test "precompact's handoff carries the in-flight line" {
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log line\n' >"$FACTORY_ROOT/runs/r1/K.log"
  __stdin='{"session_id":"s1","trigger":"manual"}'
  ritual precompact "$REPO"
  [ "$status" -eq 0 ]
  [[ "$(cat "$STATEDIR/handoff-s1.md")" == *"r1"*"K"* ]]
}

# --- inflight -----------------------------------------------------------

@test "inflight reports a dead wave as live-by-rule with a relaunch hint that reproduces the argv" {
  # CR3b: a fresh log with a dead run-level pid is live by rule (never DEAD),
  # but a wave whose pid is dead and whose keys have no status=done result still
  # gets a relaunch hint reconstructing the original quoted group argv.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "base: 658c923f34002d3ebeabc08dcdf1d26e9d11c0ca"
    echo "pid: 999999"
    echo 'group: K'
    echo 'group: L\ M'
    echo "then: gate; ff"
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"K - running - log age 0m"* ]]
  [[ "$output" != *"DEAD"* ]]
  [[ "$output" == *'relaunch: # plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave r1 /tmp/repo K L\ M --then gate\;\ ff'* ]]
}

@test "inflight treats a fresh log with a dead run pid as live, never DEAD" {
  # No <KEY>.pid file, so the run-level pid is the fallback; it is dead, but a
  # fresh log is live by rule, so the line reads running (mutation: printing
  # DEAD on the fallback pid must fail).
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"K - running"* ]]
  [[ "$output" != *"DEAD"* ]]
}

@test "inflight reads a running gate from <KEY>.gate, not the dead run pid" {
  # The wave landed (CR3.result is done) and its pid is dead; a fresh review
  # log with a live <KEY>.gate pid is a running gate -> running, no DEAD, and
  # no relaunch (the key already has status=done).
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/CR3.log"
  printf 'FACTORY-RESULT status=done\n' >"$FACTORY_ROOT/runs/r1/CR3.result"
  printf 'reviewing\n' >"$FACTORY_ROOT/runs/r1/CR3.review.log"
  printf '%s\n' "$$" >"$FACTORY_ROOT/runs/r1/CR3.gate"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    echo 'group: "CR3"'
    echo "then: gate CR3; integrate; ff"
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"CR3.review - running - log age 0m"* ]]
  [[ "$output" != *"DEAD"* ]]
  [[ "$output" != *"relaunch:"* ]]
}

@test "inflight reports a live pid as alive" {
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  {
    echo "run: r1"
    echo "pid: $$"
    echo "then: gate"
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"alive"* ]]
}

@test "inflight omits a key whose result is already written" {
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  printf 'result\n' >"$FACTORY_ROOT/runs/r1/K.result"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "an old log with no run.meta is collapsed into the stale summary, never listed" {
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  touch -d '3 hours ago' "$FACTORY_ROOT/runs/r1/K.log"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" != *"r1 K -"* ]]
  [[ "$output" == *"and 1 stale logs older than 2h"* ]]
}

@test "inflight lists only the live runs, sorted, collapsing 170 stale logs into one summary line" {
  mkdir -p "$FACTORY_ROOT/runs/stale" "$FACTORY_ROOT/runs/zz" "$FACTORY_ROOT/runs/aa" "$FACTORY_ROOT/runs/mm"
  for ((i = 1; i <= 170; i++)); do
    printf 'log\n' >"$FACTORY_ROOT/runs/stale/s$(printf '%03d' "$i").log"
    touch -d '29 hours ago' "$FACTORY_ROOT/runs/stale/s$(printf '%03d' "$i").log"
  done
  printf 'log\n' >"$FACTORY_ROOT/runs/zz/K.log"
  printf 'log\n' >"$FACTORY_ROOT/runs/aa/K.log"
  printf 'log\n' >"$FACTORY_ROOT/runs/mm/K.log"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [ "${#output}" -le 1200 ]
  [[ "$output" == *"aa K - running - log age 0m"* ]]
  [[ "$output" == *"mm K - running - log age 0m"* ]]
  [[ "$output" == *"zz K - running - log age 0m"* ]]
  [[ "$output" == *"and 170 stale logs older than 2h"* ]]
  [[ "$output" != *"s001"* ]]
  a=$(printf '%s\n' "$output" | grep -n 'aa K - running' | head -1 | cut -d: -f1)
  b=$(printf '%s\n' "$output" | grep -n 'mm K - running' | head -1 | cut -d: -f1)
  c=$(printf '%s\n' "$output" | grep -n 'zz K - running' | head -1 | cut -d: -f1)
  [ "$a" -lt "$b" ]
  [ "$b" -lt "$c" ]
}

@test "inflight prefers a dead per-key pid over an alive run pid: old log counted stale, not listed" {
  # M-B/M-B3 discriminator: the run-level pid is ALIVE ($$), the key's own pid is
  # dead, and the log is old. Correct: the dead <KEY>.pid wins, so the key is
  # stale. Mutation (pid=$wave_pid, or deleting the *) case arm) reports it alive
  # via the run pid instead.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  touch -d '3 hours ago' "$FACTORY_ROOT/runs/r1/K.log"
  printf '999999\n' >"$FACTORY_ROOT/runs/r1/K.pid"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: $$"
    echo 'group: K'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" != *"r1 K -"* ]]
  [[ "$output" != *"alive"* ]]
  [[ "$output" == *"and 1 stale logs older than 2h"* ]]
}

@test "inflight prefers an alive per-key pid over a dead run pid: old log listed alive" {
  # M-B discriminator, the mirror of the one above: run-level pid is DEAD, the
  # key's own pid is $$ (alive). Correct: the alive <KEY>.pid wins, so an old log
  # is listed "pid $$ alive". Mutation (pid=$wave_pid) counts it stale instead.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  touch -d '3 hours ago' "$FACTORY_ROOT/runs/r1/K.log"
  printf '%s\n' "$$" >"$FACTORY_ROOT/runs/r1/K.pid"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    echo 'group: K'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"r1 K - pid $$ alive"* ]]
  [[ "$output" != *"stale logs"* ]]
}

@test "inflight prefers a dead gate over an alive run pid: old review log counted stale" {
  # M-B2 discriminator: run-level pid ALIVE ($$), the gate's pid (reviewer) dead,
  # review log old. Correct: the dead <KEY>.gate wins, so the review is stale.
  # Mutation (pid=$wave_pid, or deleting the *.review arm) lists it live.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'review\n' >"$FACTORY_ROOT/runs/r1/CR3.review.log"
  touch -d '3 hours ago' "$FACTORY_ROOT/runs/r1/CR3.review.log"
  printf '999999\n' >"$FACTORY_ROOT/runs/r1/CR3.gate"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: $$"
    echo 'group: CR3'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" != *"CR3.review -"* ]]
  [[ "$output" == *"and 1 stale logs older than 2h"* ]]
}

@test "inflight prefers an alive gate over a dead run pid: old review log listed" {
  # M-B2 discriminator, the mirror: run-level pid DEAD, the gate's pid $$ alive.
  # Correct: the alive <KEY>.gate wins, so an old review log is listed running.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'review\n' >"$FACTORY_ROOT/runs/r1/CR3.review.log"
  touch -d '3 hours ago' "$FACTORY_ROOT/runs/r1/CR3.review.log"
  printf '%s\n' "$$" >"$FACTORY_ROOT/runs/r1/CR3.gate"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    echo 'group: CR3'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"CR3.review - running"* ]]
  [[ "$output" != *"stale logs"* ]]
}

@test "inflight's relaunch hint reproduces the original argv including --then" {
  # MINOR-2: the relaunch hint must append the run.meta then: value via %q, so
  # copy-pasting the hint re-records the run's intent byte-for-byte (a hand-
  # double-quoted value collapses an embedded quote).
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    echo 'group: K'
    echo 'then: say "hi"; ff'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'relaunch: # plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave r1 /tmp/repo K --then say\ \"hi\"\;\ ff'* ]]
  [[ "$output" != *'relaunch: factory-wave r1 /tmp/repo K --then "say "hi"; ff"'* ]]
}

@test "inflight's relaunch hint for a mixed wave lists only the missing key's group" {
  # MINOR-1: K1 landed (done result), K2 has no result. The hint reproduces only
  # K2's group, not the landed K1, so re-dispatching does not re-run landed work.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K1.log"
  printf 'FACTORY-RESULT status=done\n' >"$FACTORY_ROOT/runs/r1/K1.result"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K2.log"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    echo 'group: K1'
    echo 'group: K2'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"K2 - running"* ]]
  [[ "$output" == *'relaunch: # plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave r1 /tmp/repo K2'* ]]
  [[ "$output" != *"K1"* ]]
}

@test "inflight's relaunch hint never appears beside a live per-key pid" {
  # MINOR-3: K's own pid ($$) is alive while the wave pid is dead; the hint must
  # not fire (acting on it would double-dispatch a running seat).
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  printf '%s\n' "$$" >"$FACTORY_ROOT/runs/r1/K.pid"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    echo 'group: K'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"alive"* ]]
  [[ "$output" != *"relaunch:"* ]]
}

@test "inflight round-trips a %q-quoted group containing a quote and a backslash" {
  # MINOR-7 (read side): a group holding a quote and a backslash is written with
  # %q by factory-wave, read back eval-free, and re-quoted with %q in the
  # relaunch line, so the byte string survives the round-trip.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  grp='a"b\c'
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    printf 'group: %q\n' "$grp"
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  expected=$(printf 'relaunch: # plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave r1 /tmp/repo %q' "$grp")
  [[ "$output" == *"$expected"* ]]
}

@test "inflight's relaunch hint for a pre-P11 run (no plan: line) names the plan as unknown" {
  # A run.meta without a plan: line (written by a driver older than P11) cannot
  # be relaunched with a FACTORY_PLAN, so the hint must say so rather than print
  # a hint whose argv exits 2. Mutation: always prefix `FACTORY_PLAN=` (empty) ->
  # the "plan unknown" wording vanishes.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    echo 'group: K'
    echo "then: gate; ff"
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'relaunch: # plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave r1 /tmp/repo K --then gate\;\ ff'* ]]
}

@test "inflight's relaunch hint carries FACTORY_PLAN= from run.meta so it is a live launch" {
  # P11 made FACTORY_PLAN mandatory on factory-wave, so a hint without it is a
  # dead launch (exit 2). The hint must read the plan: line and prefix it, and
  # running the hint verbatim (with FACTORY_PLAN absent from the caller's env,
  # as the operator's recipe is) must hand the plan to the wave. The fake
  # factory-wave records the FACTORY_PLAN it inherits and its argv. Mutation:
  # drop the `plan:` read -> the hint prints "(plan unknown ...)" and the fake
  # never sees the plan, failing the rec assertions.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "plan: /tmp/with space/plan.md"
    echo "pid: 999999"
    echo 'group: K'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  rec="$BATS_TEST_TMPDIR/rec"
  cat >"$BATS_TEST_TMPDIR/bin/factory-wave" <<FAKE
#!$REAL_BASH
printf 'plan=%s\n' "\${FACTORY_PLAN:-}" > "\$REC"
printf 'args=%s\n' "\$*" >> "\$REC"
FAKE
  chmod +x "$BATS_TEST_TMPDIR/bin/factory-wave"
  __stdin=''
  REC="$rec" ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'relaunch: FACTORY_PLAN=/tmp/with\ space/plan.md factory-wave r1 /tmp/repo K'* ]]
  hint=$(printf '%s\n' "$output" | sed -n 's/^.*relaunch: //p')
  PATH="$BATS_TEST_TMPDIR/bin:$PATH" REC="$rec" eval "${hint}"
  run cat "$rec"
  [[ "$output" == *'plan=/tmp/with space/plan.md'* ]]
  [[ "$output" == *'args=r1 /tmp/repo K'* ]]
}

@test "the plan-unknown relaunch hint is paste-safe: a comment that evaluates to exit 0 and launches nothing" {
  # Mutation: drop the leading `#` from the unknown form -> evaluating the hint
  # launches the fake factory-wave, the rec file appears, and the no-launch
  # assertion fails.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    echo 'group: K'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  rec="$BATS_TEST_TMPDIR/rec"
  cat >"$BATS_TEST_TMPDIR/bin/factory-wave" <<FAKE
#!$REAL_BASH
printf 'launched %s\n' "\$*" >"\$REC"
FAKE
  chmod +x "$BATS_TEST_TMPDIR/bin/factory-wave"
  __stdin=''
  REC="$rec" ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'relaunch: # plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave r1 /tmp/repo K'* ]]
  hint=$(printf '%s\n' "$output" | sed -n 's/^.*relaunch: //p')
  PATH="$BATS_TEST_TMPDIR/bin:$PATH" REC="$rec" run eval "${hint}"
  [ "$status" -eq 0 ]
  [ ! -e "$rec" ]
}

@test "a repo path with a space round-trips through the relaunch hint" {
  # P11b MINOR-1: repo: was spliced unquoted, so a repo with a space split the
  # hint's argv. Mutation: splice repo_meta without %q -> the space becomes an
  # argv break, the fake records arg2=[/tmp/with] and a stray arg3=[space], and
  # the repo assertion fails.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  {
    echo "run: r1"
    echo "repo: /tmp/with space/repo"
    echo "plan: /tmp/p.md"
    echo "pid: 999999"
    echo 'group: K'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  rec="$BATS_TEST_TMPDIR/rec"
  cat >"$BATS_TEST_TMPDIR/bin/factory-wave" <<FAKE
#!$REAL_BASH
printf 'plan=%s arg2=%s arg3=%s\n' "\${FACTORY_PLAN:-}" "\$2" "\$3" >"\$REC"
FAKE
  chmod +x "$BATS_TEST_TMPDIR/bin/factory-wave"
  __stdin=''
  REC="$rec" ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'relaunch: FACTORY_PLAN=/tmp/p.md factory-wave r1 /tmp/with\ space/repo K'* ]]
  hint=$(printf '%s\n' "$output" | sed -n 's/^.*relaunch: //p')
  PATH="$BATS_TEST_TMPDIR/bin:$PATH" REC="$rec" run eval "${hint}"
  [ "$status" -eq 0 ]
  run cat "$rec"
  [[ "$output" == *'plan=/tmp/p.md'* ]]
  [[ "$output" == *'arg2=/tmp/with space/repo'* ]]
  [[ "$output" == *'arg3=K'* ]]
}

@test "inflight prints the full relaunch hint once per run, then as above" {
  # Mutation: drop the once-per-run dedup -> every dead group prints the full
  # hint, so two full hints (not one plus a later "as above") appear and the
  # count assertion fails.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K1.log"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K2.log"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "plan: /tmp/p.md"
    echo "pid: 999999"
    echo 'group: K1'
    echo 'group: K2'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'relaunch: FACTORY_PLAN=/tmp/p.md factory-wave r1 /tmp/repo K1 K2'* ]]
  [[ "$output" == *'relaunch: as above'* ]]
  [ "$(printf '%s\n' "$output" | grep -c 'FACTORY_PLAN=/tmp/p.md')" -eq 1 ]
}

@test "inflight reaps stranded pid and gate files older than stale-after, naming them in the summary" {
  # MINOR-5 (reaper): a .pid and a .gate holding a dead pid and older than
  # stale-after are removed, leaving fresh dead pid files alone.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf '999999\n' >"$FACTORY_ROOT/runs/r1/Old1.pid"
  touch -d '3 hours ago' "$FACTORY_ROOT/runs/r1/Old1.pid"
  printf '999998\n' >"$FACTORY_ROOT/runs/r1/Old2.gate"
  touch -d '3 hours ago' "$FACTORY_ROOT/runs/r1/Old2.gate"
  printf '999997\n' >"$FACTORY_ROOT/runs/r1/Fresh.pid"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [ ! -e "$FACTORY_ROOT/runs/r1/Old1.pid" ]
  [ ! -e "$FACTORY_ROOT/runs/r1/Old2.gate" ]
  [ -e "$FACTORY_ROOT/runs/r1/Fresh.pid" ]
  [[ "$output" == *"and 2 stale pid files"* ]]
}

@test "inflight denies alive for a recycled pid (process younger than the pid file)" {
  # MINOR-5 (recycled-pid guard): kill -0 says the pid is alive, but ps -o lstart=
  # shows the process started after the pid file was written -- a recycled pid.
  # The pid file's mtime is NOW, and the fake ps reports a start time one minute
  # later, so the fake ps alone decides the outcome: the real ps would say alive
  # ($$ started before the file was written). The reader must deny alive, then
  # count the old log stale.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/K.log"
  touch -d '3 hours ago' "$FACTORY_ROOT/runs/r1/K.log"
  printf '%s\n' "$$" >"$FACTORY_ROOT/runs/r1/K.pid"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  cat >"$BATS_TEST_TMPDIR/bin/ps" <<FAKE
#!$REAL_BASH
printf '%s\n' "\$(date -d '+1 minute')"
FAKE
  chmod +x "$BATS_TEST_TMPDIR/bin/ps"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" != *"alive"* ]]
  [[ "$output" != *"r1 K -"* ]]
  [[ "$output" == *"and 1 stale logs older than 2h"* ]]
}

@test "inflight lists a finished gate as gate done once its review.md exists" {
  # MINOR-6: a landed key whose review gate finished (review.md written, marker
  # removed) reads "gate done", not "running", and gets no relaunch hint.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'log\n' >"$FACTORY_ROOT/runs/r1/CR3.log"
  printf 'FACTORY-RESULT status=done\n' >"$FACTORY_ROOT/runs/r1/CR3.result"
  printf 'review\n' >"$FACTORY_ROOT/runs/r1/CR3.review.log"
  printf 'FACTORY-REVIEW verdict=approve\n' >"$FACTORY_ROOT/runs/r1/CR3.review.md"
  {
    echo "run: r1"
    echo "repo: /tmp/repo"
    echo "pid: 999999"
    echo 'group: CR3'
  } >"$FACTORY_ROOT/runs/r1/run.meta"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"CR3.review - gate done"* ]]
  [[ "$output" != *"CR3.review - running"* ]]
  [[ "$output" != *"relaunch:"* ]]
}

@test "inflight counts an aged finished gate as stale, never listing it" {
  # MAJOR-1 fixture: `gate done` must sit BELOW the stale-after cut, so a review
  # gate whose .review.md exists but whose log is older than stale-after folds
  # into the stale summary instead of being listed forever.
  mkdir -p "$FACTORY_ROOT/runs/r1"
  printf 'review\n' >"$FACTORY_ROOT/runs/r1/CR3.review.log"
  touch -d '3 hours ago' "$FACTORY_ROOT/runs/r1/CR3.review.log"
  printf 'FACTORY-REVIEW verdict=approve\n' >"$FACTORY_ROOT/runs/r1/CR3.review.md"
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" != *"CR3.review"* ]]
  [[ "$output" == *"and 1 stale logs older than 2h"* ]]
}

@test "inflight keeps 23 aged finished gates under the 1200-byte cap, folded into the stale count" {
  # MAJOR-1 live-shaped fixture: 23 finished review gates aged ~30h beside three
  # live keys. The aged gates must collapse into one stale-summary line, never
  # be listed, so the output stays far under SESSION_START_CAP_INFLIGHT and the
  # newest live key still appears. (Mutation: gate_done restored above the cut
  # lists all 23 and overflows the cap, dropping the newest live key.)
  mkdir -p "$FACTORY_ROOT/runs/r1"
  for i in $(seq 1 23); do
    printf 'review\n' >"$FACTORY_ROOT/runs/r1/REV$i.review.log"
    touch -d '30 hours ago' "$FACTORY_ROOT/runs/r1/REV$i.review.log"
    printf 'FACTORY-REVIEW verdict=approve\n' >"$FACTORY_ROOT/runs/r1/REV$i.review.md"
  done
  for k in LIVE1 LIVE2 LIVE3; do
    printf 'log\n' >"$FACTORY_ROOT/runs/r1/$k.log"
    printf '%s\n' "$$" >"$FACTORY_ROOT/runs/r1/$k.pid"
  done
  __stdin=''
  ritual inflight "$REPO"
  [ "$status" -eq 0 ]
  [ "${#output}" -le 1200 ]
  [[ "$output" == *"LIVE3 - pid $$ alive"* ]]
  [[ "$output" == *"and 23 stale logs older than 2h"* ]]
  [[ "$output" != *"REV"* ]]
}

@test "stop blocks with valid JSON when the path has a space and a non-ASCII byte" {
  f="$REPO/docs/reviews/2026-09-05 draft—x.md"
  printf 'x\n' >"$f"
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"decision":"block"'* ]]
  python3 -c 'import json,sys; o=json.load(sys.stdin); assert o["decision"] == "block", o' <<< "$output"
}

# --- the tree's renderer (CR5) -------------------------------------------

@test "a stale packaged evidence plus a current tree renderer still allows" {
  # The packaged `evidence` on PATH always says stale (exit 1), but the TREE's
  # tasks.py derives the current board; the ritual must trust the tree, so a
  # clean tree allows. (Mutation: back to `$ev` → the fake's exit 1 blocks.)
  EVIDENCE_RC=1
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [ -f "$STATEDIR/last-stop" ]
}

@test "a current packaged evidence plus a stale tree renderer still blocks" {
  # The reverse: the tree's renderer says stale (drift), the packaged fake says
  # current (exit 0); the ritual must block on the tree, not trust the fake.
  make_board_stale
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"decision":"block"'* ]]
  [[ "$output" == *"write-board"* ]]
}

@test "stop_hook_active true allows without writing a block, naming the loop guard" {
  make_board_stale
  __stdin='{"session_id":"s1","stop_hook_active":true}'
  run --separate-stderr env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
    bash "$SCRIPT" stop "$REPO" <<< "$__stdin"
  [ "$status" -eq 0 ]
  [[ "$output" != *'"decision":"block"'* ]]
  [[ "$stderr" == *"continuing after a block - allowing"* ]]
  [ ! -f "$STATEDIR/s1.blocks" ]
}

@test "no python3 and no evidence degrades to allow with the renderer stderr line" {
  # A PATH with the ritual's tools but neither python3 nor a packaged evidence:
  # the board check must degrade to allow (never block) on its own missing tool.
  toolbin="$BATS_TEST_TMPDIR/toolbin"
  mkdir -p "$toolbin"
  for t in bash git sed head tr cut sort find date awk wc cat stat readlink mkdir rm grep; do
    p=$(command -v "$t" 2>/dev/null) && ln -sf "$p" "$toolbin/$t"
  done
  run --separate-stderr env -i PATH="$toolbin" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
    bash "$SCRIPT" stop "$REPO" <<< "$__stdin"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [[ "$stderr" == *"no python3 for the tree"*"allowing"* ]]
}

@test "RITUAL_PYTHON wrapper runs the tree's tasks.py for the stop board check" {
  # RITUAL_PYTHON names a wrapper that records its argv, then execs the real
  # python3; the recorded argv must carry `pkgs/evidence/tasks.py`, proving the
  # stop board check forks the tree's renderer through that interpreter.
  record="$BATS_TEST_TMPDIR/recorded-argv"
  {
    printf '#!%s\n' "$REAL_BASH"
    printf 'printf "%%s\\n" "$@" >> "%s"\n' "$record"
    printf 'exec %q "$@"\n' "$(command -v python3)"
  } >"$BATS_TEST_TMPDIR/bin/ritual-python"
  chmod +x "$BATS_TEST_TMPDIR/bin/ritual-python"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
    RITUAL_PYTHON="$BATS_TEST_TMPDIR/bin/ritual-python" \
    bash "$SCRIPT" stop "$REPO" <<< "$__stdin"
  [ "$status" -eq 0 ]
  [[ -s "$record" ]]
  [[ "$(cat "$record")" == *"pkgs/evidence/tasks.py"* ]]
}

@test "no python3 on PATH but the packaged evidence wrapper names one uses it" {
  # python3 absent, but a packaged `evidence` wrapper (walkShellApplication shape)
  # exports a python3 dir in its PATH line; the ritual must resolve that
  # interpreter and still run the tree's tasks.py. The packaged copy itself is
  # stale (exit 1), so calling it for the board check would block.
  toolbin="$BATS_TEST_TMPDIR/wrapperbin"
  mkdir -p "$toolbin"
  for t in bash git sed head tr cut sort find date awk wc cat stat readlink mkdir rm grep; do
    p=$(command -v "$t" 2>/dev/null) && ln -sf "$p" "$toolbin/$t"
  done
  pydir=$(dirname "$(command -v python3)")
  {
    printf '#!%s\n' "$REAL_BASH"
    printf 'export PATH="%s:$PATH"\n' "$pydir"
    printf 'exit 1\n'
  } >"$toolbin/evidence"
  chmod +x "$toolbin/evidence"
  run env -i PATH="$toolbin" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
    bash "$SCRIPT" stop "$REPO" <<< "$__stdin"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [ -f "$STATEDIR/last-stop" ]
}

@test "stop returns within 2s when stdin is closed" {
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
    RITUAL_EVIDENCE="$BATS_TEST_TMPDIR/bin/evidence" \
    timeout 2 bash -c 'exec 0<&-; bash "$0" stop "$1"' "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
}

@test "stop returns within 2s when stdin is a pipe that never writes" {
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
    RITUAL_EVIDENCE="$BATS_TEST_TMPDIR/bin/evidence" \
    timeout 2 bash "$SCRIPT" stop "$REPO" 0< <(:)
  [ "$status" -eq 0 ]
}

@test "precompact's handoff carries the newest board-log line" {
  mkdir -p "$REPO/docs/board"
  printf '# Board log\n\n## Log (newest first)\n\n**NEWEST ENTRY** today.\n\n**OLDER** yesterday.\n' \
    >"$REPO/docs/board/log-2026-09.md"
  git -C "$REPO" add docs/board/log-2026-09.md
  git -C "$REPO" commit -qm "board log"
  __stdin='{"session_id":"s1","trigger":"manual"}'
  ritual precompact "$REPO"
  [ "$status" -eq 0 ]
  [[ "$(cat "$STATEDIR/handoff-s1.md")" == *"**NEWEST ENTRY** today."* ]]
}

@test "the override notice goes to stderr, leaving stdout empty" {
  touch "$REPO/.claude/ritual-override"
  touch "$REPO/docs/reviews/x.md"
  run --separate-stderr env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$XDG_STATE_HOME" FACTORY_ROOT="$FACTORY_ROOT" \
    RITUAL_EVIDENCE="$BATS_TEST_TMPDIR/bin/evidence" \
    bash "$SCRIPT" stop "$REPO" <<< "$__stdin"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [[ "$stderr" == *"override present"* ]]
}

@test "blocks files older than 7 days are reaped on each run" {
  mkdir -p "$STATEDIR"
  printf '2\n' >"$STATEDIR/sx.blocks"
  touch -d '8 days ago' "$STATEDIR/sx.blocks"
  ritual stop "$REPO"
  [ "$status" -eq 0 ]
  [ ! -f "$STATEDIR/sx.blocks" ]
}