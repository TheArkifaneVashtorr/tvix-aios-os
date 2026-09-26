#!/usr/bin/env bats
# factory-dispatch (plan FD1b): launch a plan's next wave straight from the
# derived task graph, doing NO graph logic of its own. The dispatcher asks
# `tasks.py waves --repo NAME --plan <basename> --next` for the ONE next wave
# (a single shell-quoted-group line, or nothing when the plan is fully
# landed/in flight) and launches exactly that through factory-wave; it never
# re-reads dependsOn. The graph is faked through FACTORY_WAVES_CMD for the
# error/injection cases (malformed line, graph crash, --all no-progress, a
# running task omitted from --next) and run for REAL against a fixture git
# repo for the wave-derivation cases (the next wave really is A1+B1, then A2
# once they land). The factory-wave that would launch a seat is faked on PATH
# via FACTORY_WAVE_CMD, so no real seat ever runs here.
#
# Every script runs through bash directly, the way checks.unit's sandbox runs
# them (no /usr/bin/env there), and FACTORY_ROOT is overridden to the test
# tmpdir so nothing here touches the operator's real ~/factory or the network.
#
# The real-graph cases need pkgs/evidence/tasks.py and python. `checks.unit`
# copies pkgs/evidence and docs/ledger into its sandbox (flake.nix) and carries
# python, so these tests RUN there too -- no skip -- via FACTORY_PYTHON3_CMD
# (the sandbox's `python3`); under `nix develop -c bats` that override is empty
# and the dispatcher falls back to the devShell python.

bats_require_minimum_version 1.5.0

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup() {
  REAL_BASH="$(command -v bash)"
  REC="$BATS_TEST_TMPDIR/rec"
  FAKE="$BATS_TEST_TMPDIR/bin/factory-wave"
  mkdir -p "$(dirname "$FAKE")"

  # A git fixture repo the graph reads: repos.toml names it "fx" at its own
  # (canonical) path, and one typed plan holds A1 -> A2 (code/S) and B1
  # (docs/XS), A1 and B1 both depending on nothing, touches disjoint so they
  # stay two separate groups in the first wave (A2 is blocked on A1).
  local repo_raw="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$repo_raw/docs/ledger" "$repo_raw/docs/superpowers/plans"
  git -C "$repo_raw" init -q 2>/dev/null || true
  REPO="$(cd "$repo_raw" && pwd -P)"
  cat >"$REPO/docs/ledger/repos.toml" <<EOF
[[repo]]
name = "fx"
path = "$REPO"
EOF
  PLAN="$REPO/docs/superpowers/plans/plan.md"
  cat >"$PLAN" <<'EOF'
### A1 (code, S) — a1

**dependsOn:** none

**touches:** tools/a1.sh

**acceptance:** unit

**commit subject:** `fx: add a1 (test: unit)`

### A2 (code, S) — a2

**dependsOn:** A1

**touches:** tools/a2.sh

**acceptance:** unit

**commit subject:** `fx: add a2 (test: unit)`

### B1 (docs, XS) — b1

**dependsOn:** none

**touches:** docs/b1.md

**acceptance:** lint

**commit subject:** `fx: add b1 (test: lint)`
EOF

  # The fake factory-wave: records its argv and FACTORY_PLAN, then exits 0
  # (or 7 when FAKE_WAVE_FAIL=1). Reached via FACTORY_WAVE_CMD so the real
  # $SEAT/factory-wave never runs.
  cat >"$FAKE" <<FAKE
#!$REAL_BASH
{
  printf 'CALL args:'
  for a in "\$@"; do printf ' <%s>' "\$a"; done
  printf '\\n'
  printf 'FACTORY_PLAN=%s\\n' "\${FACTORY_PLAN:-}"
} >>"$REC"
if [ "\${FAKE_WAVE_FAIL:-0}" = "1" ]; then exit 7; fi
exit 0
FAKE
  chmod +x "$FAKE"

  # Exported so the dispatched script (exec'd via bash) and the fake it
  # launches both see them.
  export FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"
  export FACTORY_TOOLBOX_REPO="$BATS_TEST_DIRNAME/../.."
  export FACTORY_PYTHON3_CMD="$(command -v python3)"
  export FACTORY_WAVE_CMD="$FAKE"
  export REC
}

# A fake --next graph source: prints the given one-line output and exits with
# the given code (default 0), standing in for `tasks.py waves ... --next`.
fake_waves() {
  local line=$1 code=${2:-0} script="$BATS_TEST_TMPDIR/waves-$RANDOM"
  cat >"$script" <<EOF
#!$REAL_BASH
printf '%s\n' '$line'
exit $code
EOF
  chmod +x "$script"
  printf '%s\n' "$script"
}

@test "factory-dispatch --dry-run prints the next wave and does not launch (FD1b a)" {
  run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN" --dry-run
  [ "$status" -eq 0 ]
  # A1 and B1 are the first wave (A2 blocked on A1); disjoint touches keep
  # them two groups, so the would-run line names both, and A2 is absent.
  [[ "$output" == *"would run: factory-wave r1 $REPO \"A1\" \"B1\""* ]]
  [[ "$output" != *"A2"* ]]
  # --dry-run must not invoke the wave launcher at all.
  [ ! -e "$REC" ]
}

@test "factory-dispatch launches the next wave through factory-wave and prints the brief (FD1b b)" {
  run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN"
  [ "$status" -eq 0 ]
  # After the wave, the dispatch prints the task brief.
  [[ "$output" == *"# Task brief"* ]]
  # Exactly one launch, with argv r1 <repo> "A1" "B1" -- A2 is not in it.
  [ "$(grep -c '^CALL args:' "$REC")" -eq 1 ]
  run cat "$REC"
  [[ "$output" == *"<r1>"* ]]
  [[ "$output" == *"<$REPO>"* ]]
  [[ "$output" == *"<A1>"* ]]
  [[ "$output" == *"<B1>"* ]]
  [[ "$output" != *"<A2>"* ]]
  # FACTORY_PLAN is handed to the wave launcher as the plan path.
  [[ "$output" == *"FACTORY_PLAN=$PLAN"* ]]
}

@test "factory-dispatch schedules the next wave after A1 and B1 land (FD1b c)" {
  git -C "$REPO" -c user.name=seat -c user.email=seat@example.com \
    commit -q --allow-empty -m "fx: add a1 (test: unit)"
  git -C "$REPO" -c user.name=seat -c user.email=seat@example.com \
    commit -q --allow-empty -m "fx: add b1 (test: lint)"
  run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN" --dry-run
  [ "$status" -eq 0 ]
  # A2's dependency is landed, so it is now the only schedulable task.
  [[ "$output" == *"would run: factory-wave r1 $REPO \"A2\""* ]]
  [[ "$output" != *"\"A1\""* ]]
  [[ "$output" != *"\"B1\""* ]]
}

@test "factory-dispatch reports nothing schedulable and exits 0 when all landed (FD1b d)" {
  for subject in "fx: add a1 (test: unit)" "fx: add a2 (test: unit)" "fx: add b1 (test: lint)"; do
    git -C "$REPO" -c user.name=seat -c user.email=seat@example.com \
      commit -q --allow-empty -m "$subject"
  done
  run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"nothing schedulable"* ]]
  [ ! -e "$REC" ]
}

@test "factory-dispatch exits 2 when no repos.toml row matches the path (FD1b e)" {
  # Point repos.toml's path elsewhere: the graph must know the repo, so the
  # dispatch refuses before any graph query (this test needs none).
  cat >"$REPO/docs/ledger/repos.toml" <<EOF
[[repo]]
name = "fx"
path = "/somewhere/else"
EOF
  run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN" --dry-run
  [ "$status" -eq 2 ]
  [[ "$output" == *"repo"* ]]
  [ ! -e "$REC" ]
}

@test "factory-dispatch exits 5 on a malformed waves line and launches nothing (FD1b f)" {
  # FACTORY_WAVES_CMD stands in for the graph and emits a line that is not
  # shell-quoted groups -- the dispatch must refuse it rather than eval it.
  malformed="$(fake_waves 'rm -rf /')"
  FACTORY_WAVES_CMD="$malformed" \
    run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN" --dry-run
  [ "$status" -eq 5 ]
  [ ! -e "$REC" ]
}

@test "factory-dispatch --all stops at the first failing wave and propagates the code (FD1b g)" {
  FAKE_WAVE_FAIL=1 \
    run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN" --all
  [ "$status" -eq 7 ]
  # Only the first wave was launched even though --all was requested.
  [ "$(grep -c '^CALL args:' "$REC")" -eq 1 ]
}

@test "factory-dispatch resolves a repo-relative plan path from another cwd (FD1b h)" {
  local wrk="$BATS_TEST_TMPDIR/elsewhere"
  mkdir -p "$wrk"
  cd "$wrk" || return 1
  # The plan is given repo-relative; it must resolve against <repo-path>, not
  # the (unrelated) cwd, and still name only the A1+B1 wave (A2 stays blocked).
  run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "docs/superpowers/plans/plan.md" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"would run: factory-wave r1 $REPO \"A1\" \"B1\""* ]]
  [[ "$output" != *"A2"* ]]
  [ ! -e "$REC" ]
}

@test "factory-dispatch exits 2 when the plan is not readable (FD1b i)" {
  run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "no/such/plan.md" --dry-run
  [ "$status" -eq 2 ]
  [ ! -e "$REC" ]
}

@test "factory-dispatch exits 6 when the graph query fails and launches nothing (FD1b j)" {
  failing="$(fake_waves '' 1)"
  FACTORY_WAVES_CMD="$failing" \
    run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN" --dry-run
  [ "$status" -eq 6 ]
  [[ "$output" == *"graph query failed"* ]]
  [ ! -e "$REC" ]
}

@test "factory-dispatch --all dies 7 when the wave repeats with no progress (FD1b k)" {
  # A graph that never changes: the same wave comes back after a wave that
  # exited 0, so the progress guard stops it after exactly one launch.
  samewave="$(fake_waves '"A1" "B1"')"
  FACTORY_WAVES_CMD="$samewave" \
    run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN" --all
  [ "$status" -eq 7 ]
  [[ "$output" == *"no progress"* ]]
  [ "$(grep -c '^CALL args:' "$REC")" -eq 1 ]
}

@test "factory-dispatch writes the wave line to dispatch.log (FD1b l)" {
  run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN"
  [ "$status" -eq 0 ]
  [ -f "$FACTORY_ROOT/runs/r1/dispatch.log" ]
  run cat "$FACTORY_ROOT/runs/r1/dispatch.log"
  [[ "$output" == *"factory-dispatch: run r1 plan plan.md groups: A1 B1"* ]]
}

@test "factory-dispatch writes the wave line to stderr (FD1b m)" {
  run --separate-stderr "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN"
  [ "$status" -eq 0 ]
  [[ "$stderr" == *"factory-dispatch: run 'r1' plan 'plan.md': wave groups: A1 B1"* ]]
}

@test "factory-dispatch honours --repo-name for the graph query (FD1b n)" {
  # --repo-name skips the repos.toml path lookup and feeds NAME straight to
  # the graph. Resolve still defaults to "fx" here, so the override must yield
  # the same wave; the point is the flag path is exercised end-to-end.
  run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN" --repo-name fx --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" == *"would run: factory-wave r1 $REPO \"A1\" \"B1\""* ]]
  [ ! -e "$REC" ]
}

@test "factory-dispatch does not launch a running task the graph omits (FD1b o)" {
  # A running task is absent from --next's output; the dispatcher must launch
  # only what the graph returns, so a B1 kept out of the line stays unlaunched.
  onlya="$(fake_waves '"A1"')"
  FACTORY_WAVES_CMD="$onlya" \
    run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN"
  [ "$status" -eq 0 ]
  [ "$(grep -c '^CALL args:' "$REC")" -eq 1 ]
  run cat "$REC"
  [[ "$output" == *"<A1>"* ]]
  [[ "$output" != *"<B1>"* ]]
  [[ "$output" != *"<A2>"* ]]
}

@test "factory-dispatch --all runs wave after wave through the real factory-wave (DF7b)" {
  # DF7b: --all launches wave after wave into ONE run directory by design. The
  # second wave is admitted by factory-wave's reuse rule (the previous
  # factory-wave has exited, same plan), so both keys run and no refusal line
  # appears. Unset FACTORY_WAVE_CMD (the setup's fake) so the REAL factory-wave
  # runs; fake only factory-task and the graph (K1, then K2, then nothing).
  # The real script's #!/usr/bin/env bash shebang cannot exec in the checks.unit
  # sandbox (no /usr/bin/env), so hand it bash through a wrapper that runs the
  # real script by its real path -- the same trick as 92-ritual's relaunch-hint
  # test.
  unset FACTORY_WAVE_CMD
  fwave="$BATS_TEST_TMPDIR/bin/factory-wave-real"
  printf '#!%s\n' "$REAL_BASH" >"$fwave"
  cat >>"$fwave" <<EOF
"$REAL_BASH" "$SEAT/factory-wave" "\$@"
EOF
  chmod +x "$fwave"

  fbin="$BATS_TEST_TMPDIR/fakebin"
  mkdir -p "$fbin"
  printf '#!%s\n' "$REAL_BASH" >"$fbin/factory-task"
  cat >>"$fbin/factory-task" <<'FAKE'
run=$1
key=$3
mkdir -p "$FACTORY_ROOT/runs/$run"
printf '%s\n' "$key" >>"$FACTORY_ROOT/runs/$run/invocations"
printf 'FACTORY-RESULT status=done\nFACTORY-CHECKS none=not-run\nFACTORY-COMMITS 0\nFACTORY-NOTES fake\n' >"$FACTORY_ROOT/runs/$run/$key.result"
FAKE
  chmod +x "$fbin/factory-task"

  waves_script="$BATS_TEST_TMPDIR/waves-seq"
  printf '#!%s\n' "$REAL_BASH" >"$waves_script"
  cat >>"$waves_script" <<'EOF'
counter="$(dirname "$0")/.waves-n"
n=0
[ -f "$counter" ] && n=$(cat "$counter")
case "$n" in
  0) printf '"K1"\n'; printf '1' >"$counter" ;;
  1) printf '"K2"\n'; printf '2' >"$counter" ;;
  *) printf '\n' ;;
esac
EOF
  chmod +x "$waves_script"

  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_WAVES_CMD="$waves_script" FACTORY_WAVE_CMD="$fwave" \
    run "$REAL_BASH" "$SEAT/factory-dispatch" r1 "$REPO" "$PLAN" --all

  [ "$status" -eq 0 ]
  # The dispatcher pre-created the run directory (its own mkdir -p, then
  # dispatch.log) before the first wave; the wave admits that meta-less
  # directory (only a dispatch.log inside) rather than refusing it, so --all's
  # first wave is never refused (the empty-pre-created-directory arm).
  [ -f "$FACTORY_ROOT/runs/r1/dispatch.log" ]
  run cat "$FACTORY_ROOT/runs/r1/invocations"
  [[ "$output" == *"K1"* ]]
  [[ "$output" == *"K2"* ]]
  [[ "$output" != *"already exists"* ]]
}