#!/usr/bin/env bats
# SH2: the driver completes a lost result block. When the seat's own
# FACTORY-RESULT line is a near miss (or absent) but the branch has commits,
# the driver records status=unreported with the real git facts instead of a
# failed run; the derived lines are labelled (`derived: checks commits`) and
# factory-brief re-prints the template after REPO NOTES so a headless seat
# still sees the grammar last. These are exercised with fakes on PATH — the
# same idiom as 80-seat-driver.bats: a fake dsh-openrouter that prints the
# seat's lines, a real git workspace, and FACTORY_ROOT under the tmpdir.
#
# Every script runs through $REAL_BASH (never exec'd by path: the build
# sandbox has no /usr/bin/env).

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup_file() {
  bats_require_minimum_version 1.5.0
  # No test in this file may write to the operator's real runs dir
  # ($HOME/factory/runs). Snapshot it once, before any test runs, so
  # teardown_file can prove none gained an entry.
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
  PLAN="$BATS_TEST_TMPDIR/plan.md"
  : >"$PLAN"
  export FACTORY_PLAN="$PLAN"
  export FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"
  export FACTORY_RUNS="$BATS_TEST_TMPDIR/factory/runs"
}

# Build a real git workspace at $WS: a base commit on main, task/K1 branched
# from it with <n> commits on top (0 = the branch sits on the base), and —
# unless the second arg is "0" — a .factory-meta recording that base sha at the
# path factory_task_base_sha reads ($FACTORY_ROOT/ws/r1/K1/.factory-meta).
mk_ws_with_commits() {
  local n=$1 meta=${2:-1} i=0
  WS="$BATS_TEST_TMPDIR/ws"
  rm -rf "$WS"
  git init -q -b main "$WS"
  git -C "$WS" config user.email t@x
  git -C "$WS" config user.name t
  printf 'base\n' >"$WS/f"
  git -C "$WS" add f
  git -C "$WS" commit -qm base
  BASE_SHA=$(git -C "$WS" rev-parse HEAD)
  git -C "$WS" checkout -qb task/K1
  while [ "$i" -lt "$n" ]; do
    printf '%s\n' "$i" >"$WS/work$i"
    git -C "$WS" add "work$i"
    git -C "$WS" commit -qm "work $i"
    i=$((i + 1))
  done
  if [ "$meta" = "1" ]; then
    mkdir -p "$FACTORY_ROOT/ws/r1/K1"
    printf 'base_sha=%s\n' "$BASE_SHA" >"$FACTORY_ROOT/ws/r1/K1/.factory-meta"
  fi
}

# Write a fake dsh-openrouter to $BIN whose body is the given payload (a printf
# command that emits the seat's stdout lines) and which exits 0.
fake_seat() {
  BIN="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$BIN"
  {
    printf '#!%s\n' "$REAL_BASH"
    printf '%s\n' "$1"
  } >"$BIN/dsh-openrouter"
  chmod +x "$BIN/dsh-openrouter"
}

# Run the real factory-task in a seat_copy against the workspace/brief built by
# mk_ws_with_commits/fake_seat; $status is the task's exit code afterward.
run_task() {
  SEAT_COPY="$BATS_TEST_TMPDIR/seat"
  rm -rf "$SEAT_COPY"
  cp -r "$SEAT" "$SEAT_COPY"
  chmod -R u+w "$SEAT_COPY"
  sed -i "1s@.*@#!$REAL_BASH@" "$SEAT_COPY/factory-brief"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$WS" >"$SEAT_COPY/factory-ws"
  chmod +x "$SEAT_COPY/factory-ws"
  FX="$BATS_TEST_TMPDIR/toolbox"
  rm -rf "$FX"
  mkdir -p "$FX/docs/ledger"
  cat >"$FX/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO"
  SHARE="$BATS_TEST_TMPDIR/share"
  mkdir -p "$SHARE"
  FACTORY_TOOLBOX_REPO="$FX" FACTORY_PLAN="$PLAN" \
    FACTORY_SHARED_DSH_HOME_SRC="$SHARE" PATH="$BIN:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$SEAT_COPY/factory-task" r1 "$REPO" K1
}

@test "near miss with one commit completes an unreported block from the git facts" {
  # Mutant: keep the arm's old FACTORY-COMMITS 0 -> line 3 reads 0, not 1;
  # task_rc=2 (failed) -> the exit assertion reads 2, not 0.
  mk_ws_with_commits 1
  fake_seat "printf 'FACTORY-RESULT: status=done\\n'"
  run_task
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=unreported exit_code=0" ]
  [ "${lines[1]}" = "FACTORY-CHECKS none=not-run" ]
  [ "${lines[2]}" = "FACTORY-COMMITS 1" ]
  [ "${lines[3]}" = "FACTORY-NOTES result-misparse: FACTORY-RESULT: status=done" ]
  [[ "$output" == *"derived: checks commits"* ]]
  [[ "$output" == *"error_class: no-result-line"* ]]
  [ "$(printf '%s\n' "$output" | sed -n 's/^head: //p')" = "$(git -C "$WS" rev-parse task/K1)" ]
  [ "$task_rc" -eq 0 ]
}

@test "no result line at all with one commit completes the same unreported block" {
  # Mutant: hoist only the near-miss arm -> this row's line 1 reads failed, not
  # unreported (the empty-payload seat reaches synth=none).
  mk_ws_with_commits 1
  fake_seat "printf 'some prose, no result block here\\n'"
  run_task
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=unreported exit_code=0" ]
  [ "${lines[1]}" = "FACTORY-CHECKS none=not-run" ]
  [ "${lines[2]}" = "FACTORY-COMMITS 1" ]
  [[ "${lines[3]}" == "FACTORY-NOTES the seat produced no usable FACTORY-RESULT line; see "* ]]
  [[ "$output" == *"derived: checks commits"* ]]
  [[ "$output" == *"error_class: no-result-line"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "near miss with zero commits stays failed with no derived line" {
  # Mutant: drop the -gt 0 guard -> unreported is recorded over an empty count.
  mk_ws_with_commits 0
  fake_seat "printf 'FACTORY-RESULT: status=done\\n'"
  run_task
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=failed exit_code=0" ]
  [ "${lines[2]}" = "FACTORY-COMMITS 0" ]
  [[ "$output" != *"derived: checks commits"* ]]
  [ "$task_rc" -eq 2 ]
}

@test "an accepted status=done with one commit is not reclassified and has no derived line" {
  # Mutant: apply the arm to every status -> a derived: line appears on a done
  # result (and status is rewritten).
  mk_ws_with_commits 1
  fake_seat "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished the work\\n'"
  run_task
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" != *"derived:"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "near miss with one commit but no .factory-meta stays failed with base unknown" {
  # Mutant: treat an empty count as > 0 -> an unverifiable branch reads
  # unreported instead of failed.
  mk_ws_with_commits 1 0
  fake_seat "printf 'FACTORY-RESULT: status=done\\n'"
  run_task
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=failed exit_code=0" ]
  [[ "$output" == *"base: unknown"* ]]
  [[ "$output" != *"derived: checks commits"* ]]
  [ "$task_rc" -eq 2 ]
}

@test "factory-brief re-prints the template after REPO NOTES when FACTORY_BRIEF_EXTRA is set" {
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  FACTORY_RUN=r1 FACTORY_MODEL=deepseek/deepseek-v4-pro-0813 FACTORY_BRIEF_EXTRA=x \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1
  [ "$status" -eq 0 ]
  template_lines=$(printf '%s\n' "$output" | grep -cE '^(FACTORY-RESULT status=<done\|partial\|failed>|FACTORY-CHECKS <name>=<pass\|fail\|not-run> \.\.\.|FACTORY-COMMITS <n>|FACTORY-NOTES <one line>)$')
  [ "$template_lines" = "8" ]
  last_four=$(printf '%s\n' "$output" | grep -v '^[[:space:]]*$' | tail -n 4 | tr '\n' '|')
  [ "$last_four" = "FACTORY-RESULT status=<done|partial|failed>|FACTORY-CHECKS <name>=<pass|fail|not-run> ...|FACTORY-COMMITS <n>|FACTORY-NOTES <one line>|" ]

  # Without EXTRA the template appears exactly once (the RULES block's own).
  FACTORY_RUN=r1 FACTORY_MODEL=deepseek/deepseek-v4-pro-0813 \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1
  [ "$status" -eq 0 ]
  template_lines=$(printf '%s\n' "$output" | grep -cE '^(FACTORY-RESULT status=<done\|partial\|failed>|FACTORY-CHECKS <name>=<pass\|fail\|not-run> \.\.\.|FACTORY-COMMITS <n>|FACTORY-NOTES <one line>)$')
  [ "$template_lines" = "4" ]
}

@test "factory-brief's re-print sentence does not carry the literal label or repeat the phrase" {
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  FACTORY_RUN=r1 FACTORY_MODEL=deepseek/deepseek-v4-pro-0813 FACTORY_BRIEF_EXTRA=x \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1
  [ "$status" -eq 0 ]
  brief=$output
  run grep -c 'no colon, no markdown' <<<"$brief"
  [ "$output" = "1" ]
  sentence=$(printf '%s\n' "$brief" | grep -n 'Your final four lines' | cut -d: -f2-)
  [ -n "$sentence" ]
  [[ "$sentence" != *"FACTORY-RESULT"* ]]
}

@test "factory-wave reads the word from a fake factory-task's unreported result and chains on" {
  # Mutant: print `unknown` for a word outside the four handled words -> the K1
  # summary reads unknown; or `[ "$status" = done ] || overall_rc=0` -> the wave
  # exits 0 instead of 1 (the unreported key not reached a done).
  fact="$BATS_TEST_TMPDIR/factbin"
  mkdir -p "$fact"
  CALLS="$BATS_TEST_TMPDIR/calls"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
printf '%s\n' "\$key" >>"$CALLS"
if [ "\$key" = "K1" ]; then
  cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=unreported exit_code=0
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 1
FACTORY-NOTES result-misparse: FACTORY-RESULT: status=done
wall_s: 60
usage: {"input":1,"output":2}
RESULT
else
  cat >"\$d/\$key.result" <<RESULT
FACTORY-RESULT status=done exit_code=0
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok
wall_s: 30
usage: {"input":1,"output":2}
RESULT
fi
exit 0
FAKE
  chmod +x "$fact/factory-task"
  # The wave re-execs under setsid unless it already leads its session; fake
  # both so the run stays in-process (the sandbox has no session leader here).
  psbin="$BATS_TEST_TMPDIR/psbin"
  mkdir -p "$psbin"
  cat >"$psbin/ps" <<FAKE
#!$REAL_BASH
pid=""; prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\n' "\${pid:-0}"
FAKE
  chmod +x "$psbin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$psbin/setsid"
  chmod +x "$psbin/setsid"
  repo="$BATS_TEST_TMPDIR/repo"
  git init -q -b main "$repo"
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

body.

### K2 (code, M) — t

body.
EOF
  CALLS="$CALLS" PATH="$psbin:$PATH" FACTORY_BIN_OVERRIDE="$fact" \
    FACTORY_PLAN="$PLAN" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1 K2"
  [ "$status" -eq 1 ]
  [[ "$output" == *"K1 status=unreported checks=none=not-run commits=1 minutes=1.0 tokens=1+2"* ]]
  [[ "$output" == *"K2 status=done"* ]]
  run cat "$CALLS"
  [ "${lines[0]}" = "K1" ]
  [ "${lines[1]}" = "K2" ]
}

# --- SH3: touches enforced by the driver ---

@test "factory_touches_covers honours the / boundary, never a substring" {
  # Mutant: drop the `/` boundary -> tests/unit2 covered; substring -> flake.nix.bak covered.
  touches="$BATS_TEST_TMPDIR/touches"
  printf 'tests/unit\nflake.nix\ndocs/runbooks/\n' >"$touches"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_touches_covers 'tests/unit/x.bats' '$touches'"
  [ "$status" -eq 0 ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_touches_covers 'tests/unit2/x.bats' '$touches'"
  [ "$status" -eq 1 ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_touches_covers 'flake.nix' '$touches'"
  [ "$status" -eq 0 ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_touches_covers 'flake.nix.bak' '$touches'"
  [ "$status" -eq 1 ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_touches_covers 'docs/runbooks/a.md' '$touches'"
  [ "$status" -eq 0 ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_touches_covers 'tests' '$touches'"
  [ "$status" -eq 1 ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_touches_covers 'docs/MAP.md' '$touches'"
  [ "$status" -eq 1 ]
}

# Build a repo whose HEAD and index each carry a controlled docs/OPERATIONS.md.
# $1 = HEAD content, $2 = index (staged) content.
mk_board_repo() {
  BOARD_REPO="$BATS_TEST_TMPDIR/boardrepo"
  rm -rf "$BOARD_REPO"
  mkdir -p "$BOARD_REPO/docs"
  git init -q -b main "$BOARD_REPO"
  git -C "$BOARD_REPO" config user.email t@x
  git -C "$BOARD_REPO" config user.name t
  printf '%s' "$1" >"$BOARD_REPO/docs/OPERATIONS.md"
  git -C "$BOARD_REPO" add docs/OPERATIONS.md
  git -C "$BOARD_REPO" commit -qm base
  printf '%s' "$2" >"$BOARD_REPO/docs/OPERATIONS.md"
  git -C "$BOARD_REPO" add docs/OPERATIONS.md
}

@test "factory_board_confined requires one begin and one end marker" {
  # Mutant: drop the marker-count rule -> the missing-end-marker evasion returns 0.
  mk_board_repo 'prologue
<!-- tasks:begin -->
queue
<!-- tasks:end -->
epilogue
' 'prologue
<!-- tasks:begin -->
queue changed
<!-- tasks:end -->
epilogue
'
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_board_confined '$BOARD_REPO' HEAD :"
  [ "$status" -eq 0 ]
  # A prologue line added outside the markers is a rewrite.
  mk_board_repo 'prologue
<!-- tasks:begin -->
queue
<!-- tasks:end -->
epilogue
' 'prologue2
prologue
<!-- tasks:begin -->
queue
<!-- tasks:end -->
epilogue
'
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_board_confined '$BOARD_REPO' HEAD :"
  [ "$status" -eq 1 ]
  # The index version lacks the end marker: the awk swallows everything below the
  # begin marker, so the cut is byte-equal, but the marker count catches it.
  mk_board_repo 'prologue
<!-- tasks:begin -->
queue
<!-- tasks:end -->
' 'prologue
<!-- tasks:begin -->
queue
'
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_board_confined '$BOARD_REPO' HEAD :"
  [ "$status" -eq 1 ]
  # Two begin markers are malformed.
  mk_board_repo 'prologue
<!-- tasks:begin -->
queue
<!-- tasks:end -->
epilogue
' 'prologue
<!-- tasks:begin -->
<!-- tasks:begin -->
queue
<!-- tasks:end -->
epilogue
'
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_board_confined '$BOARD_REPO' HEAD :"
  [ "$status" -eq 1 ]
  # docs/OPERATIONS.md absent at HEAD -> not confined.
  rm -rf "$BOARD_REPO"
  mkdir -p "$BOARD_REPO/docs"
  git init -q -b main "$BOARD_REPO"
  git -C "$BOARD_REPO" config user.email t@x
  git -C "$BOARD_REPO" config user.name t
  printf 'base\n' >"$BOARD_REPO/f"
  git -C "$BOARD_REPO" add f
  git -C "$BOARD_REPO" commit -qm base
  printf 'prologue\n<!-- tasks:begin -->\nqueue\n<!-- tasks:end -->\nepilogue\n' >"$BOARD_REPO/docs/OPERATIONS.md"
  git -C "$BOARD_REPO" add docs/OPERATIONS.md
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_board_confined '$BOARD_REPO' HEAD :"
  [ "$status" -eq 1 ]
}

@test "factory_touches_extra lists only uncovered paths, exempting MAP and a confined board" {
  # Mutant: exempt every .md -> docs/x.md missing; exempt the whole board -> the
  # prologue row red; sort the output -> order red.
  mk_board_repo 'prologue
<!-- tasks:begin -->
queue
<!-- tasks:end -->
epilogue
' 'prologue
<!-- tasks:begin -->
queue changed
<!-- tasks:end -->
epilogue
'
  touches="$BATS_TEST_TMPDIR/touches"
  printf 'tests/unit\n' >"$touches"
  changed="$BATS_TEST_TMPDIR/changed"
  printf 'tests/unit/x.bats\ndocs/MAP.md\ndocs/OPERATIONS.md\nflake.nix\ntests/unit2/y\ndocs/x.md\n' >"$changed"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_touches_extra '$BOARD_REPO' '$touches' HEAD : '$changed'"
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "flake.nix" ]
  [ "${lines[1]}" = "tests/unit2/y" ]
  [ "${lines[2]}" = "docs/x.md" ]
  [ "${#lines[@]}" -eq 3 ]
  # A prologue edit is not confined, so docs/OPERATIONS.md is also listed.
  mk_board_repo 'prologue
<!-- tasks:begin -->
queue
<!-- tasks:end -->
epilogue
' 'prologue2
prologue
<!-- tasks:begin -->
queue
<!-- tasks:end -->
epilogue
'
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_touches_extra '$BOARD_REPO' '$touches' HEAD : '$changed'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"docs/OPERATIONS.md"* ]]
}

@test "factory_disclosed matches a token, not a substring" {
  # Mutant: fixed-string substring -> flake.nix.bak discloses; exact token only ->
  # the backticked and comma rows red.
  msg="$BATS_TEST_TMPDIR/msg"
  printf 'Deviation: flake.nix — needs the copy list\n' >"$msg"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_disclosed 'flake.nix' '$msg'"
  [ "$status" -eq 0 ]
  printf 'Deviation: flake.nix.bak — needs the copy list\n' >"$msg"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_disclosed 'flake.nix' '$msg'"
  [ "$status" -eq 1 ]
  printf 'see `flake.nix` here\n' >"$msg"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_disclosed 'flake.nix' '$msg'"
  [ "$status" -eq 0 ]
  printf 'flake.nix,\n' >"$msg"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_disclosed 'flake.nix' '$msg'"
  [ "$status" -eq 0 ]
  printf '' >"$msg"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_disclosed 'flake.nix' '$msg'"
  [ "$status" -eq 1 ]
  # A glob is a literal token, never a pathname pattern: a body of
  # `Deviation: * — everything` names no path, so it must not disclose extra.txt
  # even when a file named extra.txt sits in the cwd (pathname expansion off).
  # Mutant: expand tokens as globs -> the * matches extra.txt and both cases read 0.
  globcwd="$BATS_TEST_TMPDIR/globcwd"
  mkdir -p "$globcwd"
  printf 'x\n' >"$globcwd/extra.txt"
  printf 'Deviation: * — everything\n' >"$msg"
  run "$REAL_BASH" -c "cd '$globcwd' && . '$SEAT/factory-lib.sh' && factory_disclosed 'extra.txt' '$msg'"
  [ "$status" -eq 1 ]
  printf 'Deviation: ex*.txt — fixture\n' >"$msg"
  run "$REAL_BASH" -c "cd '$globcwd' && . '$SEAT/factory-lib.sh' && factory_disclosed 'extra.txt' '$msg'"
  [ "$status" -eq 1 ]
}

# Build a repo with core.hooksPath=githooks and a stub commit-msg that execs the
# real factory-commit-msg.sh; the base commit carries docs/OPERATIONS.md with
# markers so the board guard has a HEAD to compare against.
mk_hook_repo() {
  HOOK_REPO="$BATS_TEST_TMPDIR/hookrepo"
  rm -rf "$HOOK_REPO"
  git init -q -b main "$HOOK_REPO"
  git -C "$HOOK_REPO" config user.email t@x
  git -C "$HOOK_REPO" config user.name t
  git -C "$HOOK_REPO" config core.hooksPath githooks
  mkdir -p "$HOOK_REPO/githooks" "$HOOK_REPO/docs"
  printf '#!%s\nexec "%s" "%s/factory-commit-msg.sh" "$@"\n' "$REAL_BASH" "$REAL_BASH" "$SEAT" >"$HOOK_REPO/githooks/commit-msg"
  chmod +x "$HOOK_REPO/githooks/commit-msg"
  printf 'base\n' >"$HOOK_REPO/f"
  printf 'prologue\n<!-- tasks:begin -->\nqueue\n<!-- tasks:end -->\nepilogue\n' >"$HOOK_REPO/docs/OPERATIONS.md"
  git -C "$HOOK_REPO" add f docs/OPERATIONS.md
  git -C "$HOOK_REPO" commit -qm base
}

@test "the commit-msg hook allows a change inside touches" {
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  mkdir -p "$HOOK_REPO/src"
  printf 'x\n' >"$HOOK_REPO/src/a"
  git -C "$HOOK_REPO" add src/a
  run git -C "$HOOK_REPO" commit -qm "add src/a"
  [ "$status" -eq 0 ]
  [ "$(git -C "$HOOK_REPO" rev-list --count HEAD)" -eq 2 ]
}

@test "the commit-msg hook refuses an undisclosed file outside touches" {
  # Mutant: drop the refusal -> this commit lands and the count assertion goes red.
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  mkdir -p "$HOOK_REPO/src"
  printf 'x\n' >"$HOOK_REPO/src/a"
  printf 'y\n' >"$HOOK_REPO/other.txt"
  git -C "$HOOK_REPO" add src/a other.txt
  before=$(git -C "$HOOK_REPO" rev-list --count HEAD)
  run git -C "$HOOK_REPO" commit -qm "add the new files"
  [ "$status" -eq 1 ]
  [ "$(git -C "$HOOK_REPO" rev-list --count HEAD)" -eq "$before" ]
  [[ "$output" == *"Deviation: other.txt —"* ]]
  [[ "$output" == *"--no-verify does not change the record"* ]]
}

@test "the commit-msg hook refuses a glob body that names no path (b')" {
  # Mutant: expand tokens as globs -> the * discloses extra.txt and the commit lands.
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  mkdir -p "$HOOK_REPO/src"
  printf 'x\n' >"$HOOK_REPO/src/a"
  printf 'y\n' >"$HOOK_REPO/extra.txt"
  git -C "$HOOK_REPO" add src/a extra.txt
  before=$(git -C "$HOOK_REPO" rev-list --count HEAD)
  run git -C "$HOOK_REPO" commit -qm "work" -m "Deviation: * — everything"
  [ "$status" -eq 1 ]
  [ "$(git -C "$HOOK_REPO" rev-list --count HEAD)" -eq "$before" ]
  [[ "$output" == *"Deviation: extra.txt —"* ]]
}

@test "the commit-msg hook allows a disclosed file outside touches" {
  # Mutant: drop the disclosure check -> the disclosed commit is refused.
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  mkdir -p "$HOOK_REPO/src"
  printf 'x\n' >"$HOOK_REPO/src/a"
  printf 'y\n' >"$HOOK_REPO/other.txt"
  git -C "$HOOK_REPO" add src/a other.txt
  run git -C "$HOOK_REPO" commit -qm "add the new files" -m "Deviation: other.txt — fixture"
  [ "$status" -eq 0 ]
}

@test "the commit-msg hook lets a merge through" {
  # Mutant: drop the MERGE_HEAD rule -> the merge commit is refused.
  mk_hook_repo
  git -C "$HOOK_REPO" checkout -qb feature
  printf 'y\n' >"$HOOK_REPO/other.txt"
  git -C "$HOOK_REPO" add other.txt
  git -C "$HOOK_REPO" commit -qm "add other.txt on feature"
  git -C "$HOOK_REPO" checkout -q main
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  run git -C "$HOOK_REPO" merge --no-ff feature -m "merge feature"
  [ "$status" -eq 0 ]
}

@test "the commit-msg hook allows anything without a touches contract" {
  # Mutant: refuse without a contract -> this commit is refused.
  mk_hook_repo
  printf 'y\n' >"$HOOK_REPO/other.txt"
  git -C "$HOOK_REPO" add other.txt
  run git -C "$HOOK_REPO" commit -qm "add other.txt"
  [ "$status" -eq 0 ]
}

@test "the commit-msg hook exempts docs/MAP.md and a queue-block-only board change" {
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  printf 'map\n' >"$HOOK_REPO/docs/MAP.md"
  sed -i 's/^queue$/queue2/' "$HOOK_REPO/docs/OPERATIONS.md"
  git -C "$HOOK_REPO" add docs/MAP.md docs/OPERATIONS.md
  run git -C "$HOOK_REPO" commit -qm "board + map"
  [ "$status" -eq 0 ]
}

@test "the commit-msg hook refuses a board prologue edit" {
  # Mutant: treat any board change as confined -> the prologue edit is allowed.
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  sed -i 's/^prologue$/prologue2/' "$HOOK_REPO/docs/OPERATIONS.md"
  git -C "$HOOK_REPO" add docs/OPERATIONS.md
  run git -C "$HOOK_REPO" commit -qm "board prose"
  [ "$status" -eq 1 ]
  [[ "$output" == *"docs/OPERATIONS.md"* ]]
}

@test "the commit-msg hook allows when the message file is unreadable" {
  if [ "$(id -u)" = "0" ]; then skip "root can read a 000 file"; fi
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  printf 'y\n' >"$HOOK_REPO/other.txt"
  git -C "$HOOK_REPO" add other.txt
  msg="$BATS_TEST_TMPDIR/msg"
  printf 'subject\n' >"$msg"
  chmod 000 "$msg"
  run "$REAL_BASH" -c "cd '$HOOK_REPO' && '$REAL_BASH' '$SEAT/factory-commit-msg.sh' '$msg'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"allowing"* ]]
}

@test "factory-ws installs the commit-msg hook and writes .factory-touches from the plan" {
  # Mutant: skip the exclude -> porcelain non-empty; skip chmod -> [ -x ] red;
  # write an empty .factory-touches when the union is empty -> the no-K1 row red.
  repo="$BATS_TEST_TMPDIR/srcrepo"
  mkdir -p "$repo"
  git init -q -b main "$repo"
  git -C "$repo" config user.email t@x
  git -C "$repo" config user.name t
  printf 'hello\n' >"$repo/README"
  git -C "$repo" add README
  git -C "$repo" commit -qm initial
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**touches:** src

body.
EOF
  FACTORY_TOOLBOX_REPO="$BATS_TEST_DIRNAME/../.." FACTORY_PYTHON3_CMD="$(command -v python3)" \
    run "$REAL_BASH" "$SEAT/factory-ws" r1 "$repo" K1
  [ "$status" -eq 0 ]
  ws="$FACTORY_ROOT/ws/r1/K1"
  [ "$(cat "$ws/.factory-touches")" = "src" ]
  [ -x "$ws/githooks/commit-msg" ]
  [ "$(head -n1 "$ws/githooks/commit-msg")" = "#!$REAL_BASH" ]
  [[ "$(sed -n '2p' "$ws/githooks/commit-msg")" == *"factory-commit-msg.sh"* ]]
  run cat "$ws/.git/info/exclude"
  [[ "$output" == *".factory-meta"* ]]
  [[ "$output" == *"githooks/commit-msg"* ]]
  [[ "$output" == *".factory-touches"* ]]
  [ -z "$(git -C "$ws" status --porcelain)" ]
  [ "$(git -C "$ws" config core.hooksPath)" = "githooks" ]
}

@test "factory-ws installs the hook but writes no .factory-touches when the plan lacks the key" {
  repo="$BATS_TEST_TMPDIR/srcrepo2"
  mkdir -p "$repo"
  git init -q -b main "$repo"
  git -C "$repo" config user.email t@x
  git -C "$repo" config user.name t
  printf 'hello\n' >"$repo/README"
  git -C "$repo" add README
  git -C "$repo" commit -qm initial
  cat >"$PLAN" <<'EOF'
### K2 (code, M) — t

**touches:** src

body.
EOF
  FACTORY_TOOLBOX_REPO="$BATS_TEST_DIRNAME/../.." FACTORY_PYTHON3_CMD="$(command -v python3)" \
    run "$REAL_BASH" "$SEAT/factory-ws" r1 "$repo" K1
  [ "$status" -eq 0 ]
  ws="$FACTORY_ROOT/ws/r1/K1"
  [ ! -e "$ws/.factory-touches" ]
  [ -x "$ws/githooks/commit-msg" ]
  [[ "$output" == *"touches: no contract for K1"* ]]
}

@test "factory-ws keeps a source repo's own tracked githooks/commit-msg" {
  # Mutant: overwrite the tracked hook -> the bytes red.
  repo="$BATS_TEST_TMPDIR/srcrepo3"
  mkdir -p "$repo/githooks"
  git init -q -b main "$repo"
  git -C "$repo" config user.email t@x
  git -C "$repo" config user.name t
  printf 'hello\n' >"$repo/README"
  printf '#!/bin/sh\nexit 7\n' >"$repo/githooks/commit-msg"
  chmod +x "$repo/githooks/commit-msg"
  git -C "$repo" add README githooks/commit-msg
  git -C "$repo" commit -qm initial
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**touches:** src

body.
EOF
  FACTORY_TOOLBOX_REPO="$BATS_TEST_DIRNAME/../.." FACTORY_PYTHON3_CMD="$(command -v python3)" \
    run "$REAL_BASH" "$SEAT/factory-ws" r1 "$repo" K1
  [ "$status" -eq 0 ]
  ws="$FACTORY_ROOT/ws/r1/K1"
  [ "$(cat "$ws/githooks/commit-msg")" = "#!/bin/sh
exit 7" ]
  [[ "$output" == *"not installed"* ]]
}

# Build a real workspace with a base commit and one task/K1 commit; $1 selects
# the change: "extra" (undisclosed extra.txt), "disclosed" (body discloses
# extra.txt), "glob" (body is `Deviation: * — everything`), "map" (only
# docs/MAP.md), "board" (docs/OPERATIONS.md changed only inside the queue block),
# or "board-prologue" (a prologue line changed).
mk_touches_ws() {
  local mode=${1:-extra}
  WS="$BATS_TEST_TMPDIR/ws"
  rm -rf "$WS"
  git init -q -b main "$WS"
  git -C "$WS" config user.email t@x
  git -C "$WS" config user.name t
  mkdir -p "$WS/src"
  printf 'base\n' >"$WS/src/a"
  case $mode in
    board | board-prologue)
      mkdir -p "$WS/docs"
      printf 'prologue\n<!-- tasks:begin -->\nqueue\n<!-- tasks:end -->\nepilogue\n' >"$WS/docs/OPERATIONS.md"
      git -C "$WS" add src/a docs/OPERATIONS.md
      ;;
    *)
      git -C "$WS" add src/a
      ;;
  esac
  git -C "$WS" commit -qm base
  BASE_SHA=$(git -C "$WS" rev-parse HEAD)
  git -C "$WS" checkout -qb task/K1
  case $mode in
    extra)
      printf 'x\n' >"$WS/src/a"
      printf 'y\n' >"$WS/extra.txt"
      git -C "$WS" add src/a extra.txt
      git -C "$WS" commit -qm "do the work"
      ;;
    disclosed)
      printf 'x\n' >"$WS/src/a"
      printf 'y\n' >"$WS/extra.txt"
      git -C "$WS" add src/a extra.txt
      git -C "$WS" commit -qm "change" -m "Deviation: extra.txt — fixture"
      ;;
    glob)
      printf 'x\n' >"$WS/src/a"
      printf 'y\n' >"$WS/extra.txt"
      git -C "$WS" add src/a extra.txt
      git -C "$WS" commit -qm "change" -m "Deviation: * — everything"
      ;;
    globpath)
      printf 'x\n' >"$WS/src/a"
      printf 'y\n' >"$WS/x*.txt"
      git -C "$WS" add -- src/a ':(literal)x*.txt'
      git -C "$WS" commit -qm "do the work"
      ;;
    globpath-disclosed)
      printf 'x\n' >"$WS/src/a"
      printf 'y\n' >"$WS/x*.txt"
      git -C "$WS" add -- src/a ':(literal)x*.txt'
      git -C "$WS" commit -qm "do the work" -m "Deviation: x*.txt — fixture"
      ;;
    map)
      mkdir -p "$WS/docs"
      printf 'map\n' >"$WS/docs/MAP.md"
      git -C "$WS" add docs/MAP.md
      git -C "$WS" commit -qm "regenerate MAP"
      ;;
    board)
      sed -i 's/^queue$/queue2/' "$WS/docs/OPERATIONS.md"
      git -C "$WS" add docs/OPERATIONS.md
      git -C "$WS" commit -qm "board queue"
      ;;
    board-prologue)
      sed -i 's/^prologue$/prologue2/' "$WS/docs/OPERATIONS.md"
      git -C "$WS" add docs/OPERATIONS.md
      git -C "$WS" commit -qm "board prose"
      ;;
  esac
  mkdir -p "$FACTORY_ROOT/ws/r1/K1"
  printf 'base_sha=%s\n' "$BASE_SHA" >"$FACTORY_ROOT/ws/r1/K1/.factory-meta"
}

# Run the real factory-task against the workspace built by mk_touches_ws, with a
# fake seat printing $1 and the toolbox pointing at the real repo root.
run_task_touches() {
  local payload=$1
  SEAT_COPY="$BATS_TEST_TMPDIR/seat"
  rm -rf "$SEAT_COPY"
  cp -r "$SEAT" "$SEAT_COPY"
  chmod -R u+w "$SEAT_COPY"
  sed -i "1s@.*@#!$REAL_BASH@" "$SEAT_COPY/factory-brief"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$WS" >"$SEAT_COPY/factory-ws"
  chmod +x "$SEAT_COPY/factory-ws"
  fake_seat "$payload"
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**touches:** src

body one.
EOF
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO"
  SHARE="$BATS_TEST_TMPDIR/share"
  mkdir -p "$SHARE"
  FACTORY_TOOLBOX_REPO="$BATS_TEST_DIRNAME/../.." FACTORY_PYTHON3_CMD="$(command -v python3)" \
    FACTORY_PLAN="$PLAN" FACTORY_SHARED_DSH_HOME_SRC="$SHARE" \
    PATH="$BIN:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$SEAT_COPY/factory-task" r1 "$REPO" K1
}

@test "an undisclosed extra file demotes a done to partial with touches-violation" {
  # Mutant: never demote -> this row's status stays done; demote regardless of
  # disclosure -> row 10 red.
  mk_touches_ws extra
  run_task_touches "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [ "${lines[3]}" = "FACTORY-NOTES finished; 1 file(s) outside touches undisclosed: extra.txt" ]
  [[ "$output" == *"touches_extra: 1"* ]]
  [[ "$output" == *"touches_disclosed: 0"* ]]
  [[ "$output" == *"touches_files: extra.txt"* ]]
  [[ "$output" == *"error_class: touches-violation"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a disclosed extra file keeps the done status" {
  # Mutant: count disclosed as undisclosed -> this row demotes to partial.
  mk_touches_ws disclosed
  run_task_touches "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"touches_extra: 1"* ]]
  [[ "$output" == *"touches_disclosed: 1"* ]]
  [[ "$output" == *"error_class: none"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "a glob body names no path: the extra stays undisclosed from any driver cwd" {
  # Mutant: expand tokens as globs -> the * matches the extra.txt in the cwd, the
  # extra reads disclosed, and status stays done (touches_disclosed: 1).
  mk_touches_ws glob
  globcwd="$BATS_TEST_TMPDIR/driverglobcwd"
  mkdir -p "$globcwd"
  printf 'z\n' >"$globcwd/extra.txt"
  cd "$globcwd"
  run_task_touches "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"touches_extra: 1"* ]]
  [[ "$output" == *"touches_disclosed: 0"* ]]
  [[ "$output" == *"error_class: touches-violation"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a failed seat with an extra file keeps its own status" {
  # Mutant: demote every status -> the failed row reads partial.
  mk_touches_ws extra
  run_task_touches "printf 'FACTORY-RESULT status=failed exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES failed\\n'"
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=failed exit_code=0" ]
  [[ "$output" == *"touches_extra: 1"* ]]
  [[ "$output" == *"touches_disclosed: 0"* ]]
  [[ "$output" != *"error_class: touches-violation"* ]]
  [ "$task_rc" -eq 2 ]
}

@test "docs/MAP.md alone is exempt from touches" {
  # Mutant: count MAP -> this row demotes to partial; always write
  # touches_files -> the no-touches_files assertion red.
  mk_touches_ws map
  run_task_touches "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"touches_extra: 0"* ]]
  [[ "$output" != *"touches_files:"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "a queue-block-only docs/OPERATIONS.md change is exempt at the driver" {
  # Mutant: pass HEAD HEAD to factory_touches_extra -> the board always reads
  # confined, so the prologue case below reads touches_extra: 0 instead of 1.
  mk_touches_ws board
  run_task_touches "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"touches_extra: 0"* ]]
  [[ "$output" != *"touches_files:"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "a docs/OPERATIONS.md prologue change is an extra at the driver" {
  # Mutant: pass HEAD HEAD to factory_touches_extra -> the prologue case reads
  # confined, so this row reads touches_extra: 0 and status stays done.
  mk_touches_ws board-prologue
  run_task_touches "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"touches_extra: 1"* ]]
  [[ "$output" == *"touches_disclosed: 0"* ]]
  [[ "$output" == *"touches_files: docs/OPERATIONS.md"* ]]
  [[ "$output" == *"error_class: touches-violation"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a toolbox without tasks.py is no contract and writes no touches lines" {
  # Mutant: write touches_extra: 0 without a contract -> this row red.
  mk_touches_ws extra
  SEAT_COPY="$BATS_TEST_TMPDIR/seat"
  rm -rf "$SEAT_COPY"
  cp -r "$SEAT" "$SEAT_COPY"
  chmod -R u+w "$SEAT_COPY"
  sed -i "1s@.*@#!$REAL_BASH@" "$SEAT_COPY/factory-brief"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$WS" >"$SEAT_COPY/factory-ws"
  chmod +x "$SEAT_COPY/factory-ws"
  fake_seat "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  FX="$BATS_TEST_TMPDIR/toolbox"
  rm -rf "$FX"
  mkdir -p "$FX/docs/ledger"
  cat >"$FX/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**touches:** src

body one.
EOF
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO"
  SHARE="$BATS_TEST_TMPDIR/share"
  mkdir -p "$SHARE"
  FACTORY_TOOLBOX_REPO="$FX" FACTORY_PYTHON3_CMD="$(command -v python3)" \
    FACTORY_PLAN="$PLAN" FACTORY_SHARED_DSH_HOME_SRC="$SHARE" \
    PATH="$BIN:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$SEAT_COPY/factory-task" r1 "$REPO" K1
  task_rc=$status
  task_output=$output
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" != *"touches_extra:"* ]]
  [ "$task_rc" -eq 0 ]
  [[ "$task_output" == *"touches: no contract for K1"* ]]
}

@test "factory-integrate refuses an undisclosed touches extra and merges a disclosed one" {
  # Mutant: `extra -gt 0` -> the 2/2 row is refused.
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/base" "$root/ws/r1" "$root/runs/r1"
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
  git -C "$root/ws/r1/K1" commit -q -m "k1: add x (test: unit)"
  git clone -q "$src" "$root/ws/r1/K2"
  git -C "$root/ws/r1/K2" config user.name t
  git -C "$root/ws/r1/K2" config user.email t@x
  git -C "$root/ws/r1/K2" checkout -q -b task/K2
  echo y >"$root/ws/r1/K2/y"; git -C "$root/ws/r1/K2" add y
  git -C "$root/ws/r1/K2" commit -q -m "k2: add y (test: unit)"
  # K1's result discloses only 1 of 2 extra files -> refused.
  cat >"$root/runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=done exit_code=0
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok

run: r1
key: K1
touches_extra: 2
touches_disclosed: 1
EOF
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1 K2
  [ "$status" -eq 1 ]
  [[ "$output" == *"REFUSED K1: 1 undisclosed file(s) outside touches"* ]]
  [[ "$output" == *"MERGE K2 ok"* ]]
  [[ "$output" == *"refused: 1"* ]]
  # A fully disclosed pair merges.
  cat >"$root/runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=done exit_code=0
FACTORY-CHECKS unit=pass
FACTORY-COMMITS 1
FACTORY-NOTES ok

run: r1
key: K1
touches_extra: 2
touches_disclosed: 2
EOF
  rm -rf "$root/base/src"
  git clone -q "$src" "$root/base/src"
  FACTORY_ROOT="$root" FACTORY_CHECK_CMD=true \
    run "$REAL_BASH" "$SEAT/factory-integrate" r1 "$src" K1
  [ "$status" -eq 0 ]
  [[ "$output" == *"MERGE K1 ok"* ]]
}

@test "factory_error_class maps a touches demotion to touches-violation" {
  # Mutant: the demoted case after the tail patterns -> a provider tail reads
  # provider-error.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_error_class log partial 0 100 100 '' touches"
  [ "$output" = "touches-violation" ]
  printf 'provider: x\n' >"$BATS_TEST_TMPDIR/provlog"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_error_class '$BATS_TEST_TMPDIR/provlog' partial 0 100 100 '' touches"
  [ "$output" = "touches-violation" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_error_class log done 0 100 100 '' touches"
  [ "$output" = "none" ]
}

@test "factory_disclosed treats a glob path as a literal token from a cwd with matches" {
  # Mutant: expand tokens as globs (M1) -> the x*.txt token reads xy.txt xz.txt, so
  # the first case reads 1 and the second 0; pattern-match equality (M8) -> the
  # third case reads 0 (xy.txt matches the pattern x*.txt).
  globcwd="$BATS_TEST_TMPDIR/globcwd17"
  mkdir -p "$globcwd"
  printf 'b\n' >"$globcwd/xy.txt"
  printf 'c\n' >"$globcwd/xz.txt"
  msg="$BATS_TEST_TMPDIR/msg17"
  printf 'Deviation: x*.txt — fixture\n' >"$msg"
  run "$REAL_BASH" -c "cd '$globcwd' && . '$SEAT/factory-lib.sh' && factory_disclosed 'x*.txt' '$msg'"
  [ "$status" -eq 0 ]
  run "$REAL_BASH" -c "cd '$globcwd' && . '$SEAT/factory-lib.sh' && factory_disclosed 'xy.txt' '$msg'"
  [ "$status" -eq 1 ]
  printf 'Deviation: xy.txt — wrong\n' >"$msg"
  run "$REAL_BASH" -c "cd '$globcwd' && . '$SEAT/factory-lib.sh' && factory_disclosed 'x*.txt' '$msg'"
  [ "$status" -eq 1 ]
  printf 'see `x*.txt`, here\n' >"$msg"
  run "$REAL_BASH" -c "cd '$globcwd' && . '$SEAT/factory-lib.sh' && factory_disclosed 'x*.txt' '$msg'"
  [ "$status" -eq 0 ]
}

@test "factory_disclosed restores the caller's noglob on every return path" {
  # Mutant: delete `local -` (M2) -> set -f leaks to the caller: the disclosed and
  # undisclosed calls print `set -o noglob` instead of `set +o noglob`.
  msg="$BATS_TEST_TMPDIR/msg18"
  printf 'Deviation: x*.txt — fixture\n' >"$msg"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_disclosed 'x*.txt' '$msg'; set +o | grep -w noglob"
  [ "$output" = "set +o noglob" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_disclosed 'xy.txt' '$msg'; set +o | grep -w noglob"
  [ "$output" = "set +o noglob" ]
  chmod 000 "$msg"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_disclosed 'x*.txt' '$msg'; set +o | grep -w noglob"
  [ "$output" = "set +o noglob" ]
}

@test "a glob-spelled path: the driver records x*.txt byte for byte from any cwd" {
  # Mutant: `for p in $extra` (M3) -> the x*.txt token expands against the driver's
  # cwd to xy.txt xz.txt: touches_extra 2, touches_files xy.txt xz.txt, and the
  # notes clause names them.
  mk_touches_ws globpath
  driverglobcwd="$BATS_TEST_TMPDIR/driverglobcwd19"
  mkdir -p "$driverglobcwd"
  printf 'b\n' >"$driverglobcwd/xy.txt"
  printf 'c\n' >"$driverglobcwd/xz.txt"
  cd "$driverglobcwd"
  run_task_touches "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [ "${lines[3]}" = "FACTORY-NOTES finished; 1 file(s) outside touches undisclosed: x*.txt" ]
  [[ "$output" == *"touches_extra: 1"* ]]
  [[ "$output" == *"touches_disclosed: 0"* ]]
  [[ "$output" == *"touches_files: x*.txt"* ]]
  [[ "$output" == *"error_class: touches-violation"* ]]
  [[ "$output" != *"xy.txt"* ]]
  [[ "$output" != *"xz.txt"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a glob-spelled path can be disclosed and landed" {
  # Mutant: expand the body token as a glob (M1) -> nothing in the driver's cwd
  # equals x*.txt: touches_disclosed 0 and the status demotes to partial.
  mk_touches_ws globpath-disclosed
  driverglobcwd="$BATS_TEST_TMPDIR/driverglobcwd20"
  mkdir -p "$driverglobcwd"
  printf 'b\n' >"$driverglobcwd/xy.txt"
  printf 'c\n' >"$driverglobcwd/xz.txt"
  cd "$driverglobcwd"
  run_task_touches "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  task_rc=$status
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"touches_extra: 1"* ]]
  [[ "$output" == *"touches_disclosed: 1"* ]]
  [[ "$output" == *"error_class: none"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "the commit-msg hook treats a glob-spelled staged path as one literal name" {
  # Mutant: revert any of the four loops to `for path in $X` (M4a-M4d) -> the
  # x*.txt token expands against the worktree's xy.txt xz.txt and the counts/lines
  # read 2+ with xy.txt and xz.txt leaking in; pattern-match equality (M8) -> the
  # (c) `Deviation: xy.txt — wrong` body discloses x*.txt and the commit lands.
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  mkdir -p "$HOOK_REPO/src"
  printf 'x\n' >"$HOOK_REPO/src/a"
  printf 'y\n' >"$HOOK_REPO/x*.txt"
  printf 'b\n' >"$HOOK_REPO/xy.txt"
  printf 'c\n' >"$HOOK_REPO/xz.txt"
  git -C "$HOOK_REPO" add -- src/a ':(literal)x*.txt'
  before=$(git -C "$HOOK_REPO" rev-list --count HEAD)
  run git -C "$HOOK_REPO" commit -qm "work"
  [ "$status" -eq 1 ]
  [ "$(git -C "$HOOK_REPO" rev-list --count HEAD)" -eq "$before" ]
  [[ "$output" == *"commit-msg: 1 file(s) outside this task's touches:"* ]]
  [[ "$output" == *"  x*.txt"* ]]
  [[ "$output" == *"Deviation: x*.txt —"* ]]
  [[ "$output" != *"xy.txt"* ]]
  [[ "$output" != *"xz.txt"* ]]
  run git -C "$HOOK_REPO" commit -qm "work" -m "Deviation: x*.txt — fixture"
  [ "$status" -eq 0 ]
  [ "$(git -C "$HOOK_REPO" rev-list --count HEAD)" -eq "$((before + 1))" ]
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  mkdir -p "$HOOK_REPO/src"
  printf 'x\n' >"$HOOK_REPO/src/a"
  printf 'y\n' >"$HOOK_REPO/x*.txt"
  git -C "$HOOK_REPO" add -- src/a ':(literal)x*.txt'
  run git -C "$HOOK_REPO" commit -qm "work" -m "Deviation: xy.txt — wrong"
  [ "$status" -eq 1 ]
}

@test "the commit-msg hook lists each undisclosed file on its own line" {
  # Mutant: join with a space (M5) -> `1 file(s)` and one line `  other.txt third.txt`
  # instead of two files on two lines.
  mk_hook_repo
  printf 'src\n' >"$HOOK_REPO/.factory-touches"
  mkdir -p "$HOOK_REPO/src"
  printf 'x\n' >"$HOOK_REPO/src/a"
  printf 'y\n' >"$HOOK_REPO/other.txt"
  printf 'z\n' >"$HOOK_REPO/third.txt"
  git -C "$HOOK_REPO" add src/a other.txt third.txt
  run git -C "$HOOK_REPO" commit -qm "work"
  [ "$status" -eq 1 ]
  [[ "$output" == *"commit-msg: 2 file(s) outside this task's touches:"* ]]
  [[ "$output" == *"  other.txt"* ]]
  [[ "$output" == *"  third.txt"* ]]
  [[ "$output" == *"Deviation: other.txt —"* ]]
  [[ "$output" == *"Deviation: third.txt —"* ]]
  run git -C "$HOOK_REPO" commit -qm "work" -m "Deviation: third.txt — fixture"
  [ "$status" -eq 1 ]
  [[ "$output" == *"commit-msg: 1 file(s) outside this task's touches:"* ]]
  [[ "$output" == *"  other.txt"* ]]
  [[ "$output" != *"Deviation: third.txt —"* ]]
}

@test "the hook allows when git diff fails but refuses a first commit in an empty repo" {
  # Mutant: drop the `if ! … fi` (M6) -> git diff fails under set -e: exit 128, no
  # `allowing` line; `git rev-parse --verify HEAD || exit 0` (M7) -> the first
  # commit in an empty repo exits 0 instead of refusing other.txt.
  dir="$BATS_TEST_TMPDIR/gitfailcwd"
  mkdir -p "$dir"
  printf 'src\n' >"$dir/.factory-touches"
  msg="$BATS_TEST_TMPDIR/msg23"
  printf 'subject\n' >"$msg"
  run "$REAL_BASH" -c "cd '$dir' && GIT_DIR='$BATS_TEST_TMPDIR/nonexistent' '$REAL_BASH' '$SEAT/factory-commit-msg.sh' '$msg'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"commit-msg: git diff failed; allowing (the driver recomputes touches after the seat exits)"* ]]
  fresh="$BATS_TEST_TMPDIR/freshrepo"
  rm -rf "$fresh"
  git init -q -b main "$fresh"
  git -C "$fresh" config user.email t@x
  git -C "$fresh" config user.name t
  git -C "$fresh" config core.hooksPath githooks
  mkdir -p "$fresh/githooks"
  printf '#!%s\nexec "%s" "%s/factory-commit-msg.sh" "$@"\n' "$REAL_BASH" "$REAL_BASH" "$SEAT" >"$fresh/githooks/commit-msg"
  chmod +x "$fresh/githooks/commit-msg"
  printf 'src\n' >"$fresh/.factory-touches"
  printf 'y\n' >"$fresh/other.txt"
  git -C "$fresh" add other.txt
  run git -C "$fresh" commit -qm "first"
  [ "$status" -eq 1 ]
  [[ "$output" == *"other.txt"* ]]
}

@test "no path-list consumer uses an unquoted for-in-\$ loop" {
  # Mutant: revert any consumer to `for x in $var` (M3, M4a-M4d) -> one hit and
  # exit 0 instead of no output and exit 1.
  run grep -nE 'for [A-Za-z_][A-Za-z0-9_]* in \$' "$SEAT/factory-lib.sh" "$SEAT/factory-task" "$SEAT/factory-commit-msg.sh"
  [ "$status" -eq 1 ]
  [ -z "$output" ]
}

# --- SH4: the driver re-runs the acceptance checks at the committed rev ---

# fake_nix writes $BATS_TEST_TMPDIR/bin/nix that reads $FAKE_NIX_TABLE and
# appends each invocation's argv (one line per call) to $FAKE_NIX_REC.
# $FAKE_NIX_TABLE: a first line `EVAL <ok|fail>` then one line per check:
#   <name> <present|absent> <plain|kvm|toplevel> <cached|uncached> <pass|fail|hang>
fake_nix() {
  BIN="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$BIN"
  cat >"$BIN/nix" <<'NIX'
#!__REAL_BASH__
printf '%s\n' "$*" >>"$FAKE_NIX_REC"
table=$FAKE_NIX_TABLE
eval_ok=$(sed -n '1p' "$table")
eval_ok=${eval_ok#EVAL }
name=
for a in "$@"; do
  case "$a" in
    git+file://*'#checks.x86_64-linux.'*) name=${a##*.} ;;
  esac
done
case " $* " in
  *' --apply builtins.attrNames'*)
    [ "$eval_ok" = "ok" ] || { printf 'error: eval failed\n' >&2; exit 1; }
    out=
    while read -r n present rest; do
      [ "$n" = "EVAL" ] && continue
      [ "$present" = "present" ] || continue
      out="$out\"$n\","
    done <"$table"
    out=${out%,}
    printf '[%s]\n' "$out"
    exit 0
    ;;
  *'toplevel.drvPath'*)
    printf '/nix/store/000-toplevel.drv\n'
    exit 0
    ;;
esac
case "$1" in
  derivation)
    row=$(awk -v n="$name" '$1==n' "$table")
    [ -n "$row" ] || { printf '{}\n'; exit 0; }
    set -- $row
    shape=$3
    if [ "$shape" = "kvm" ]; then
      printf '{"%s":{"env":{"requiredSystemFeatures":"kvm nixos-test"}}}\n' "/nix/store/$name.drv"
    elif [ "$shape" = "toplevel" ]; then
      printf '{"%s":{"env":{}}}\n' "/nix/store/000-toplevel.drv"
    else
      printf '{"%s":{"env":{}}}\n' "/nix/store/$name.drv"
    fi
    exit 0
    ;;
  build)
    case " $* " in
      *' --dry-run'*)
        row=$(awk -v n="$name" '$1==n' "$table")
        [ -n "$row" ] || exit 0
        set -- $row
        cached=$4
        if [ "$cached" = "uncached" ]; then
          printf 'these 1 derivations will be built:\n' >&2
        fi
        exit 0
        ;;
    esac
    row=$(awk -v n="$name" '$1==n' "$table")
    [ -n "$row" ] || exit 0
    set -- $row
    verdict=$5
    case "$verdict" in
      pass) exit 0 ;;
      fail) exit 1 ;;
      hang) sleep 60; exit 0 ;;
      *) exit 0 ;;
    esac
    ;;
esac
exit 0
NIX
  sed -i "1s@.*@#!$REAL_BASH@" "$BIN/nix"
  chmod +x "$BIN/nix"
}

# fake_evidence writes $BATS_TEST_TMPDIR/bin/evidence answering latest-check
# from $FAKE_LATEST (<name> <ok|fail> lines; exit 1 when absent) and recording
# every argv to $FAKE_EVIDENCE_REC.
fake_evidence() {
  BIN="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$BIN"
  cat >"$BIN/evidence" <<'EV'
#!__REAL_BASH__
printf '%s\n' "$*" >>"$FAKE_EVIDENCE_REC"
name=; rev=; prev=
for a in "$@"; do
  case "$prev" in
    --name) name=$a ;;
    --rev) rev=$a ;;
  esac
  prev=$a
done
for a in "$@"; do
  if [ "$a" = "latest-check" ]; then
    row=$(awk -v n="$name" '$1==n' "$FAKE_LATEST" 2>/dev/null)
    if [ -n "$row" ]; then
      set -- $row
      if [ "$2" = "ok" ]; then v=true; else v=false; fi
      printf '{"kind":"check","name":"%s","rev":"%s","ok":%s}\n' "$name" "$rev" "$v"
      exit 0
    fi
    exit 1
  fi
done
exit 0
EV
  sed -i "1s@.*@#!$REAL_BASH@" "$BIN/evidence"
  chmod +x "$BIN/evidence"
}

# Common setup for the direct factory_verify_checks / factory_acceptance_names
# tests: fakes on PATH, empty rec/table/latest files, a dummy rev and workspace.
verify_env() {
  fake_nix
  fake_evidence
  export FAKE_NIX_REC="$BATS_TEST_TMPDIR/nix.rec"
  export FAKE_NIX_TABLE="$BATS_TEST_TMPDIR/nix.table"
  export FAKE_EVIDENCE_REC="$BATS_TEST_TMPDIR/ev.rec"
  export FAKE_LATEST="$BATS_TEST_TMPDIR/latest"
  : >"$FAKE_NIX_REC"
  : >"$FAKE_NIX_TABLE"
  : >"$FAKE_EVIDENCE_REC"
  : >"$FAKE_LATEST"
  export FACTORY_EVIDENCE_CMD="$BATS_TEST_TMPDIR/bin/evidence"
  export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
  REV="$(printf 'c%.0s' $(seq 1 40))"
  WS="$BATS_TEST_TMPDIR/wsdir"
  mkdir -p "$WS"
}

run_verify() {
  local budget=$1
  shift
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_verify_checks '$WS' '$REV' $budget $* 2>/dev/null"
}

@test "factory_verify_checks runs, defers, and records exactly the buildable checks" {
  # Mutant: drop the attrNames step -> nosuch is built; drop the kvm rule ->
  # seat-vm is built; drop the drvPath rule -> host-core is built; record with
  # seat-integrate -> the src assertion red.
  verify_env
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
lint present plain uncached fail
seat-vm present kvm uncached pass
host-core present toplevel uncached pass
EOF
  run_verify 1800 unit lint nosuch seat-vm host-core
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 5 ]
  [[ "${lines[0]}" == "unit pass run"* ]]
  [[ "${lines[1]}" == "lint fail run"* ]]
  [ "${lines[2]}" = "nosuch not-run:absent -" ]
  [ "${lines[3]}" = "seat-vm not-run:cache-miss -" ]
  [ "${lines[4]}" = "host-core not-run:cache-miss -" ]
  run grep -- 'record-check --name' "$FAKE_EVIDENCE_REC"
  [ "${#lines[@]}" -eq 2 ]
  [[ "${lines[0]}" == *"record-check --name unit --rev $REV --ok --class nix-check --src seat-verify --duration "* ]]
  [[ "${lines[1]}" == *"record-check --name lint --rev $REV --fail --class nix-check --src seat-verify --duration "* ]]
  run grep -- ' --no-link' "$FAKE_NIX_REC"
  [ "${#lines[@]}" -eq 2 ]
  [[ "${lines[0]}" == *"unit"* ]]
  [[ "${lines[1]}" == *"lint"* ]]
}

@test "a cached kvm check is a store hit and is built, not deferred" {
  # Mutant: defer every kvm check -> cache-miss instead of pass run.
  verify_env
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
seat-vm present kvm cached pass
EOF
  run_verify 1800 seat-vm
  [ "$status" -eq 0 ]
  [[ "${lines[0]}" == "seat-vm pass run"* ]]
  run grep -- ' --no-link' "$FAKE_NIX_REC"
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == *"seat-vm"* ]]
}

@test "a recorded verdict is replayed from the store, never rebuilt" {
  # Mutant: always build -> the build argv appears for lint.
  verify_env
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
lint present plain uncached pass
EOF
  printf 'lint fail\n' >"$FAKE_LATEST"
  run_verify 1800 unit lint
  [ "$status" -eq 0 ]
  [[ "${lines[0]}" == "unit pass run"* ]]
  [ "${lines[1]}" = "lint fail recorded" ]
  run grep -- ' --no-link' "$FAKE_NIX_REC"
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == *"unit"* ]]
  run grep -- 'record-check --name' "$FAKE_EVIDENCE_REC"
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == *"--name unit"* ]]
}

@test "a hung check under a one-second budget times out and stops the loop" {
  # Mutant: drop the timeout -> this test hangs past 30 s (asserted on the wall).
  verify_env
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached hang
lint present plain uncached pass
EOF
  t0=$(date +%s)
  run_verify 1 unit lint
  t1=$(date +%s)
  [ "$status" -eq 3 ]
  [ "${lines[0]}" = "unit not-run:verify-timeout run" ]
  [ "${lines[1]}" = "lint not-run:verify-timeout -" ]
  [ $((t1 - t0)) -lt 30 ]
  run grep -- ' --no-link' "$FAKE_NIX_REC"
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == *"unit"* ]]
}

@test "a flake that does not evaluate fails every check with src eval, building nothing" {
  # Mutant: treat an eval failure as not-run:absent -> this row reads absent.
  verify_env
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL fail
unit present plain uncached pass
lint present plain uncached pass
EOF
  run_verify 1800 unit lint
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "unit fail eval" ]
  [ "${lines[1]}" = "lint fail eval" ]
  run grep -c '^build ' "$FAKE_NIX_REC"
  [ "$output" = "0" ]
}

@test "factory_acceptance_names reads the acceptance line, never the subject's test list" {
  # Mutant: read the commit subject -> helm-unit appears instead of unit/lint.
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit, lint

**commit subject:** `fx: add a check (test: helm-unit)`
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_acceptance_names '$PLAN' K1"
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "unit" ]
  [ "${lines[1]}" = "lint" ]
  [ "${#lines[@]}" -eq 2 ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_acceptance_names '$PLAN' NOPE"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- SH4 end-to-end: the driver verifies at the committed rev ---

# A real workspace: base commit on main, one task/K1 commit changing src/a, and
# a .factory-meta recording the base sha (so the fork point is known).
mk_verify_ws() {
  WS="$BATS_TEST_TMPDIR/ws"
  rm -rf "$WS"
  git init -q -b main "$WS"
  git -C "$WS" config user.email t@x
  git -C "$WS" config user.name t
  mkdir -p "$WS/src"
  printf 'base\n' >"$WS/src/a"
  git -C "$WS" add src/a
  git -C "$WS" commit -qm base
  BASE_SHA=$(git -C "$WS" rev-parse HEAD)
  git -C "$WS" checkout -qb task/K1
  printf 'x\n' >"$WS/src/a"
  git -C "$WS" add src/a
  git -C "$WS" commit -qm "do the work"
  mkdir -p "$FACTORY_ROOT/ws/r1/K1"
  printf 'base_sha=%s\n' "$BASE_SHA" >"$FACTORY_ROOT/ws/r1/K1/.factory-meta"
}

mk_verify_fakes() {
  fake_nix
  fake_evidence
  export FAKE_NIX_REC="$BATS_TEST_TMPDIR/nix.rec"
  export FAKE_NIX_TABLE="$BATS_TEST_TMPDIR/nix.table"
  export FAKE_EVIDENCE_REC="$BATS_TEST_TMPDIR/ev.rec"
  export FAKE_LATEST="$BATS_TEST_TMPDIR/latest"
  : >"$FAKE_NIX_REC"
  : >"$FAKE_NIX_TABLE"
  : >"$FAKE_EVIDENCE_REC"
  : >"$FAKE_LATEST"
}

mk_verify_plan() {
  cat >"$PLAN" <<EOF
### K1 (code, M) — t

**acceptance:** $1

**touches:** src

body one.
EOF
}

run_verify_task() {
  local payload=$1
  SEAT_COPY="$BATS_TEST_TMPDIR/seat"
  rm -rf "$SEAT_COPY"
  cp -r "$SEAT" "$SEAT_COPY"
  chmod -R u+w "$SEAT_COPY"
  sed -i "1s@.*@#!$REAL_BASH@" "$SEAT_COPY/factory-brief"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$WS" >"$SEAT_COPY/factory-ws"
  chmod +x "$SEAT_COPY/factory-ws"
  fake_seat "$payload"
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO"
  SHARE="$BATS_TEST_TMPDIR/share"
  mkdir -p "$SHARE"
  FACTORY_TOOLBOX_REPO="$BATS_TEST_DIRNAME/../.." FACTORY_PYTHON3_CMD="$(command -v python3)" \
    FACTORY_PLAN="$PLAN" FACTORY_SHARED_DSH_HOME_SRC="$SHARE" \
    FACTORY_EVIDENCE_CMD="$BIN/evidence" EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev" \
    PATH="$BIN:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$SEAT_COPY/factory-task" r1 "$REPO" K1
  task_rc=$status
  task_output=$output
}

@test "a claimed pass over a red check demotes a done to partial checks-misreported" {
  # Mutant: never demote -> the done status and error_class none stand.
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached fail
EOF
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [ "${lines[3]}" = "FACTORY-NOTES finished; unit claimed pass, driver fail" ]
  [[ "$output" == *"checks_verified: unit=fail"* ]]
  [[ "$output" == *"checks_verified_src: unit=run"* ]]
  [[ "$output" == *"verify_s: "* ]]
  [[ "$output" == *"error_class: checks-misreported"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a claimed pass whose check is absent from the flake demotes to checks-unverifiable" {
  # Mutant: accept a claimed pass with no check -> this row stays done.
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass pre-commit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"checks_verified: unit=pass pre-commit=not-run:absent"* ]]
  [[ "$output" == *"error_class: checks-unverifiable"* ]]
  [[ "${lines[3]}" == *"; pre-commit claimed pass, driver not-run:absent"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "an honest fail and a deferred check leave the done status standing" {
  # Mutant: demote a claimed fail -> the first row red; demote a cache-miss ->
  # the second row red.
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached fail
EOF
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=fail\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  [[ "$task_output" == *"result:"* ]]
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"error_class: none"* ]]
  [ "$task_rc" -eq 0 ]

  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit, seat-vm"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
seat-vm present kvm uncached pass
EOF
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"checks_verified: unit=pass seat-vm=not-run:cache-miss"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "an unclaimed red check demotes to checks-misreported" {
  # Mutant: leave not-run claims alone (never verify unclaimed acceptance names)
  # -> this row stays done despite the red check.
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached fail
EOF
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS none=not-run\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"error_class: checks-misreported"* ]]
  [[ "${lines[3]}" == *"; unit claimed not-run, driver fail"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a misreport and an unverifiable both firing keep checks-misreported and both clauses" {
  # Mutant: pick the last firing cell -> checks-unverifiable; drop a clause ->
  # the two-clause notes assertion red.
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached fail
EOF
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass pre-commit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"error_class: checks-misreported"* ]]
  [[ "${lines[3]}" == *"; unit claimed pass, driver fail; pre-commit claimed pass, driver not-run:absent"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a failed seat keeps its own status and still records the verified verdicts" {
  # Mutant: demote every status -> the failed row reads partial.
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached fail
EOF
  run_verify_task "printf 'FACTORY-RESULT status=failed exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES failed\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=failed exit_code=0" ]
  [[ "$output" == *"checks_verified: unit=fail"* ]]
  # the demotion table applies only to a still-done status; a failed seat is
  # never demoted, so no checks demotion class (the fake seat exits instantly,
  # leaving error_class at the harness's boot-failure fallback, not a demotion).
  [[ "$output" != *"error_class: checks-misreported"* ]]
  [[ "$output" != *"error_class: checks-unverifiable"* ]]
  [ "$task_rc" -eq 2 ]
}

@test "a cut budget leaves a done standing with verify-timeout, or checks-misreported over a red check" {
  # Mutant: let verify-timeout outrank a demotion -> the second row reads verify-timeout.
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached hang
EOF
  FACTORY_VERIFY_TIMEOUT=1 run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"checks_verified: unit=not-run:verify-timeout"* ]]
  [[ "$output" == *"error_class: verify-timeout"* ]]
  [ "$task_rc" -eq 0 ]

  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "lint, unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
lint present plain uncached fail
unit present plain uncached hang
EOF
  FACTORY_VERIFY_TIMEOUT=1 run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS lint=pass unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"error_class: checks-misreported"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "checks_scope is dirty when the diff touches flake.nix, tests, or githooks" {
  # Mutant: drop githooks -> the third case red; substring -> tests2 red.
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  # flake.nix + tests/unit/x.bats -> dirty, 2 files.
  rm -rf "$WS"
  git init -q -b main "$WS"
  git -C "$WS" config user.email t@x
  git -C "$WS" config user.name t
  printf 'base\n' >"$WS/f"
  git -C "$WS" add f
  git -C "$WS" commit -qm base
  BASE_SHA=$(git -C "$WS" rev-parse HEAD)
  git -C "$WS" checkout -qb task/K1
  printf 'x\n' >"$WS/flake.nix"
  mkdir -p "$WS/tests/unit"
  printf 'y\n' >"$WS/tests/unit/x.bats"
  git -C "$WS" add flake.nix tests/unit/x.bats
  git -C "$WS" commit -qm "checks files"
  mkdir -p "$FACTORY_ROOT/ws/r1/K1"
  printf 'base_sha=%s\n' "$BASE_SHA" >"$FACTORY_ROOT/ws/r1/K1/.factory-meta"
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [[ "$output" == *"checks_scope: dirty"* ]]
  [[ "$output" == *"checks_scope_files: 2"* ]]
  [[ "$output" == *"checks_scope_list: flake.nix tests/unit/x.bats"* ]]

  # tests2/x + src/a -> clean, 0, no list line.
  rm -rf "$WS"
  git init -q -b main "$WS"
  git -C "$WS" config user.email t@x
  git -C "$WS" config user.name t
  printf 'base\n' >"$WS/f"
  git -C "$WS" add f
  git -C "$WS" commit -qm base
  BASE_SHA=$(git -C "$WS" rev-parse HEAD)
  git -C "$WS" checkout -qb task/K1
  mkdir -p "$WS/tests2"
  printf 'x\n' >"$WS/tests2/x"
  mkdir -p "$WS/src"
  printf 'y\n' >"$WS/src/a"
  git -C "$WS" add tests2/x src/a
  git -C "$WS" commit -qm "not checks files"
  mkdir -p "$FACTORY_ROOT/ws/r1/K1"
  printf 'base_sha=%s\n' "$BASE_SHA" >"$FACTORY_ROOT/ws/r1/K1/.factory-meta"
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [[ "$output" == *"checks_scope: clean"* ]]
  [[ "$output" == *"checks_scope_files: 0"* ]]
  [[ "$output" != *"checks_scope_list:"* ]]

  # githooks/pre-commit -> dirty.
  rm -rf "$WS"
  git init -q -b main "$WS"
  git -C "$WS" config user.email t@x
  git -C "$WS" config user.name t
  printf 'base\n' >"$WS/f"
  git -C "$WS" add f
  git -C "$WS" commit -qm base
  BASE_SHA=$(git -C "$WS" rev-parse HEAD)
  git -C "$WS" checkout -qb task/K1
  mkdir -p "$WS/githooks"
  printf 'x\n' >"$WS/githooks/pre-commit"
  git -C "$WS" add githooks/pre-commit
  git -C "$WS" commit -qm "hook"
  mkdir -p "$FACTORY_ROOT/ws/r1/K1"
  printf 'base_sha=%s\n' "$BASE_SHA" >"$FACTORY_ROOT/ws/r1/K1/.factory-meta"
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [[ "$output" == *"checks_scope: dirty"* ]]
}

@test "the unreported arm derives the seat-grammar FACTORY-CHECKS from verification, folding not-run:*" {
  # Mutant: keep none=not-run -> red; write not-run:cache-miss into the seat
  # grammar -> the ingest's checks_parse reads refused (assert ok).
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit, seat-vm"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
seat-vm present kvm uncached pass
EOF
  run_verify_task "printf 'FACTORY-RESULT: status=done\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=unreported exit_code=0" ]
  [ "${lines[1]}" = "FACTORY-CHECKS unit=pass seat-vm=not-run" ]
  [[ "$output" == *"derived: checks commits"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "FACTORY_VERIFY=0 skips verification and logs verify: skipped" {
  # Mutant: verify anyway -> the checks_verified line appears.
  mk_verify_fakes
  mk_verify_ws
  mk_verify_plan "unit"
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached fail
EOF
  FACTORY_VERIFY=0 run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" != *"checks_verified:"* ]]
  [[ "$task_output" == *"verify: skipped (FACTORY_VERIFY=0)"* ]]
  [ "$task_rc" -eq 0 ]
}
# --- SH5: probes ---

# A runner script that sources factory-lib and calls factory_run_probe with its
# four args $2..$5 (the seat dir, workspace, env-tokens, remaining, command),
# preserving its exit status; its stdout is the last trimmed probe line.
mk_probe_runner() {
  PROBE_RUNNER="$BATS_TEST_TMPDIR/probe-runner.sh"
  cat >"$PROBE_RUNNER" <<'EOF'
. "$1/factory-lib.sh"
factory_run_probe "$2" "$3" "$4" "$5"
EOF
}

# Write a plain-ASCII README of $1 bytes into $WS (the probe's working tree).
mk_readme() {
  head -c "$1" /dev/zero | tr '\0' 'a' >"$WS/README"
}

@test "factory_probe_compare applies each operator to its boundary values" {
  # Mutant: use `<` for `<=` -> `le 8000 8000` reads fail; string-compare the
  # numbers -> `le 100 99`, `lt 10 9`, `ge 10 9`, `gt 9 10` and `le 8000 10000`
  # each read the wrong side (their digit counts differ, which a lexicographic
  # compare misorders).
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare le 8000 7999"
  [ "$output" = "pass" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare le 8000 8000"
  [ "$output" = "pass" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare le 8000 8001"
  [ "$output" = "fail" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare lt 5 5"
  [ "$output" = "fail" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare ge 2 2.5"
  [ "$output" = "pass" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare gt 2 abc"
  [ "$output" = "fail" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare le 100 99"
  [ "$output" = "pass" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare lt 10 9"
  [ "$output" = "pass" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare ge 10 9"
  [ "$output" = "fail" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare gt 9 10"
  [ "$output" = "pass" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare le 8000 10000"
  [ "$output" = "fail" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare eq bar bar"
  [ "$output" = "pass" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare ne bar bar"
  [ "$output" = "fail" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare empty '' ''"
  [ "$output" = "pass" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare empty '' x"
  [ "$output" = "fail" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare nonempty '' ''"
  [ "$output" = "fail" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_probe_compare nonempty '' x"
  [ "$output" = "pass" ]
}

@test "factory_run_probe unsets FACTORY_RUN, applies env tokens, trims to the last line, and times out" {
  # Mutant: drop `env -u FACTORY_RUN` -> the first case reads r1; take the first
  # line -> `printf 'a\nb\n'` reads a.
  mk_probe_runner
  local ws="$BATS_TEST_TMPDIR/probe-ws"
  mkdir -p "$ws"
  export FACTORY_RUN=r1
  run "$REAL_BASH" "$PROBE_RUNNER" "$SEAT" "$ws" '' 10 'printf "%s\n" "${FACTORY_RUN:-unset}"'
  [ "$output" = "unset" ]
  unset FACTORY_RUN
  run "$REAL_BASH" "$PROBE_RUNNER" "$SEAT" "$ws" 'FOO=bar' 10 'printf %s "$FOO"'
  [ "$output" = "bar" ]
  run "$REAL_BASH" "$PROBE_RUNNER" "$SEAT" "$ws" '' 10 "printf 'a\nb\n'"
  [ "$output" = "b" ]
  run "$REAL_BASH" "$PROBE_RUNNER" "$SEAT" "$ws" '' 10 "printf 'x\ty'"
  [ "$output" = "x y" ]
  run "$REAL_BASH" "$PROBE_RUNNER" "$SEAT" "$ws" '' 10 "printf 'a%.0s' \$(seq 1 300)"
  [ "${#output}" -eq 200 ]
  run "$REAL_BASH" "$PROBE_RUNNER" "$SEAT" "$ws" '' 1 "sleep 60"
  [ "$status" -eq 124 ]
}

@test "factory_error_class maps probe demotions" {
  # Mutant: the demoted cases after the tail patterns -> a provider tail reads
  # provider-error.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_error_class log partial 0 100 100 '' probe-mismatch"
  [ "$output" = "probe-mismatch" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_error_class log partial 0 100 100 '' probe-missing"
  [ "$output" = "probe-missing" ]
}

@test "a probe the seat pastes correctly verifies pass and records the values" {
  # Mutant: put the command first in the probes output -> the bash tab-split
  # reads the wrong field; skip the construct -> no probes_verified line.
  mk_verify_fakes
  mk_verify_ws
  mk_readme 120
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- readme-bytes: `wc -c < README` :: le 200 :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-PROBE readme-bytes=120\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"probes_verified: readme-bytes=pass"* ]]
  [[ "$output" == *"probe_values: readme-bytes=120|120"* ]]
  [[ "$output" == *"probe_env: -"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "a stale pasted number against the driver's demotes to probe-mismatch" {
  # Mutant: trust the seat's value alone -> this row reads pass.
  mk_verify_fakes
  mk_verify_ws
  mk_readme 300
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- readme-bytes: `wc -c < README` :: le 200 :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-PROBE readme-bytes=120\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"probes_verified: readme-bytes=fail"* ]]
  [[ "$output" == *"probe_values: readme-bytes=300|120"* ]]
  [[ "$output" == *"error_class: probe-mismatch"* ]]
  [[ "${lines[3]}" == *"; probe readme-bytes driver 300 le 200: fail"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a probe the seat never pasted demotes to probe-missing" {
  # Mutant: pass on the driver's value alone -> this row reads done.
  mk_verify_fakes
  mk_verify_ws
  mk_readme 120
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- readme-bytes: `wc -c < README` :: le 200 :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"probes_verified: readme-bytes=missing"* ]]
  [[ "$output" == *"probe_values: readme-bytes=120|-"* ]]
  [[ "$output" == *"error_class: probe-missing"* ]]
  [[ "${lines[3]}" == *"; probe readme-bytes not pasted by the seat"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a drifted paste is recorded, never demoted" {
  # Mutant: demote drift -> this row reads partial.
  mk_verify_fakes
  mk_verify_ws
  mk_readme 120
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- readme-bytes: `wc -c < README` :: le 200 :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-PROBE readme-bytes=119\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"probes_verified: readme-bytes=drift"* ]]
  [[ "$output" == *"probe_values: readme-bytes=120|119"* ]]
  [[ "$output" == *"error_class: none"* ]]
  [[ "${lines[3]}" == *"; probe readme-bytes drift: seat 119, driver 120"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "probe_env tokens apply and FACTORY_RUN is unset inside the probe" {
  # Mutant: drop `env -u FACTORY_RUN` -> the second probe reads the run name.
  mk_verify_fakes
  mk_verify_ws
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- foo: `printf %s "$FOO"` :: eq bar :: fixture
**probe_env:** FOO=bar

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-PROBE foo=bar\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"probes_verified: foo=pass"* ]]
  [[ "$output" == *"probe_values: foo=bar|bar"* ]]
  [[ "$output" == *"probe_env: FOO=bar"* ]]
  [ "$task_rc" -eq 0 ]

  mk_verify_fakes
  mk_verify_ws
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- runname: `printf %s "${FACTORY_RUN:-unset}"` :: eq unset :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-PROBE runname=unset\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"probes_verified: runname=pass"* ]]
  [[ "$output" == *"probe_values: runname=unset|unset"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "a timed-out probe reads not-run with verify-timeout, and D5 precedence holds" {
  # Mutant: let verify-timeout outrank a demotion, or reorder D5 -> the second /
  # third rows read the wrong demotion class.
  mk_verify_fakes
  mk_verify_ws
  mk_readme 120
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- readme-bytes: `sleep 60` :: le 200 :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  FACTORY_VERIFY_TIMEOUT=1 run_verify_task "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"probes_verified: readme-bytes=not-run"* ]]
  [[ "$output" == *"error_class: verify-timeout"* ]]
  [ "$task_rc" -eq 0 ]

  # a misreported check plus a failing probe -> checks-misreported wins, both clauses.
  mk_verify_fakes
  mk_verify_ws
  mk_readme 300
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- readme-bytes: `wc -c < README` :: le 200 :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached fail
EOF
  run_verify_task "printf 'FACTORY-PROBE readme-bytes=120\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"error_class: checks-misreported"* ]]
  [[ "${lines[3]}" == *"; unit claimed pass, driver fail"* ]]
  [[ "${lines[3]}" == *"; probe readme-bytes driver 300 le 200: fail"* ]]
  [ "$task_rc" -eq 1 ]

  # a passing check, an undisclosed extra file, and a failing probe ->
  # touches-violation (D5: touches outranks probe-mismatch).
  mk_verify_fakes
  mk_verify_ws
  mk_readme 300
  printf 'x\n' >"$WS/extra.txt"
  git -C "$WS" add extra.txt
  git -C "$WS" commit -qm "undisclosed extra"
  BASE_SHA=$(git -C "$WS" rev-parse main)
  mkdir -p "$FACTORY_ROOT/ws/r1/K1"
  printf 'base_sha=%s\n' "$BASE_SHA" >"$FACTORY_ROOT/ws/r1/K1/.factory-meta"
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- readme-bytes: `wc -c < README` :: le 200 :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-PROBE readme-bytes=120\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 2\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]
  [[ "$output" == *"error_class: touches-violation"* ]]
  [[ "$output" == *"probes_verified: readme-bytes=fail"* ]]
  [ "$task_rc" -eq 1 ]
}

@test "a failed seat keeps its own status and still records the probe verdict" {
  # Mutant: demote every status -> this row reads partial.
  mk_verify_fakes
  mk_verify_ws
  mk_readme 300
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- readme-bytes: `wc -c < README` :: le 200 :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached fail
EOF
  run_verify_task "printf 'FACTORY-RESULT status=failed exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES failed\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=failed exit_code=0" ]
  [[ "$output" == *"probes_verified: readme-bytes=fail"* ]]
  [ "$task_rc" -eq 2 ]
}

@test "a toolbox without the probes graph is no contract and writes no probe lines" {
  # Mutant: write probes_verified: empty -> this row reads that line.
  mk_verify_fakes
  mk_verify_ws
  mk_readme 120
  FX="$BATS_TEST_TMPDIR/toolbox"
  rm -rf "$FX"
  mkdir -p "$FX/docs/ledger"
  cat >"$FX/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- readme-bytes: `wc -c < README` :: le 200 :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  SEAT_COPY="$BATS_TEST_TMPDIR/seat"
  rm -rf "$SEAT_COPY"
  cp -r "$SEAT" "$SEAT_COPY"
  chmod -R u+w "$SEAT_COPY"
  sed -i "1s@.*@#!$REAL_BASH@" "$SEAT_COPY/factory-brief"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$WS" >"$SEAT_COPY/factory-ws"
  chmod +x "$SEAT_COPY/factory-ws"
  fake_seat "printf 'FACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO"
  SHARE="$BATS_TEST_TMPDIR/share"
  mkdir -p "$SHARE"
  FACTORY_TOOLBOX_REPO="$FX" FACTORY_PYTHON3_CMD="$(command -v python3)" \
    FACTORY_PLAN="$PLAN" FACTORY_SHARED_DSH_HOME_SRC="$SHARE" \
    FACTORY_EVIDENCE_CMD="$BIN/evidence" EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev" \
    PATH="$BIN:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$SEAT_COPY/factory-task" r1 "$REPO" K1
  task_rc=$status
  task_output=$output
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" != *"probes_verified:"* ]]
  [[ "$task_output" == *"probes: no contract for K1"* ]]
  [ "$task_rc" -eq 0 ]
}

@test "factory-brief names the FACTORY-PROBE line inside the RULES bullet and keeps the four-line template" {
  # Mutant: put the FACTORY-PROBE line into the template (directly above
  # FACTORY-RESULT, or directly below FACTORY-NOTES) -> the bullet-line and
  # position assertions red, and the line above FACTORY-RESULT is no longer the
  # prose ending `recorded as failed:`.
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  FACTORY_RUN=r1 FACTORY_MODEL=deepseek/deepseek-v4-pro-0813 \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1
  [ "$status" -eq 0 ]
  [[ "$output" == *"FACTORY-PROBE <name>=<value>"* ]]
  probe_count=$(printf '%s\n' "$output" | grep -c 'FACTORY-PROBE <name>=<value>')
  [ "$probe_count" = "1" ]
  probe_pos=$(printf '%s\n' "$output" | grep -n 'FACTORY-PROBE <name>=<value>' | head -n1 | cut -d: -f1)
  probe_line=$(printf '%s\n' "$output" | sed -n "${probe_pos}p")
  [[ "$probe_line" == "- "* ]]
  result_pos=$(printf '%s\n' "$output" | grep -nE '^FACTORY-RESULT status=<done\|partial\|failed>$' | head -n1 | cut -d: -f1)
  [ "$probe_pos" -le $((result_pos - 2)) ]
  checks_pos=$(printf '%s\n' "$output" | grep -nE '^FACTORY-CHECKS <name>=<pass\|fail\|not-run> \.\.\.$' | head -n1 | cut -d: -f1)
  commits_pos=$(printf '%s\n' "$output" | grep -nE '^FACTORY-COMMITS <n>$' | head -n1 | cut -d: -f1)
  notes_pos=$(printf '%s\n' "$output" | grep -nE '^FACTORY-NOTES <one line>$' | head -n1 | cut -d: -f1)
  [ "$checks_pos" -eq $((result_pos + 1)) ]
  [ "$commits_pos" -eq $((result_pos + 2)) ]
  [ "$notes_pos" -eq $((result_pos + 3)) ]
  above=$(printf '%s\n' "$output" | sed -n "$((result_pos - 1))p")
  [[ "$above" == *"recorded as failed:" ]]
}

@test "an empty or nonempty probe runs end to end through factory-task with its command intact" {
  # Mutant: drop the third argument at the factory_probe_compare call site -> the
  # probe aborts with `$3: unbound variable` and writes no .result; read the rows
  # with IFS=$'\t' -> the empty value column collapses so pcmd empties and the fake
  # git never records the command's argv.
  mk_verify_fakes
  mk_verify_ws
  REAL_GIT="$(command -v git)"
  export REAL_GIT PROBE_GIT_REC="$BATS_TEST_TMPDIR/git.rec"
  cat >"$BIN/git" <<'GIT'
#!__REAL_BASH__
if [ "$*" = "status --porcelain docs/MAP.md" ]; then
  printf '%s\n' "$*" >>"$PROBE_GIT_REC"
fi
exec "$REAL_GIT" "$@"
GIT
  sed -i "1s@.*@#!$REAL_BASH@" "$BIN/git"
  chmod +x "$BIN/git"
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- checks-current: `git status --porcelain docs/MAP.md` :: empty :: the lint gate

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-PROBE checks-current=\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"probes_verified: checks-current=pass"* ]]
  [ "$task_rc" -eq 0 ]
  run cat "$PROBE_GIT_REC"
  [ "$output" = "status --porcelain docs/MAP.md" ]

  # nonempty on `printf x` -> pass.
  mk_verify_fakes
  mk_verify_ws
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- nonempty-ok: `printf x` :: nonempty :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-PROBE nonempty-ok=x\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]
  [[ "$output" == *"probes_verified: nonempty-ok=pass"* ]]
  [ "$task_rc" -eq 0 ]

  # nonempty on `printf ''` -> fail (the driver demotes to probe-mismatch).
  mk_verify_fakes
  mk_verify_ws
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

**acceptance:** unit

**touches:** src

**probes:**
- nonempty-empty: `printf ''` :: nonempty :: fixture

body one.
EOF
  cat >"$FAKE_NIX_TABLE" <<'EOF'
EVAL ok
unit present plain uncached pass
EOF
  run_verify_task "printf 'FACTORY-PROBE nonempty-empty=\\nFACTORY-RESULT status=done exit_code=0\\nFACTORY-CHECKS unit=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES finished\\n'"
  run cat "$FACTORY_ROOT/runs/r1/K1.result"
  [[ "$output" == *"probes_verified: nonempty-empty=fail"* ]]
  [ "$task_rc" -eq 1 ]
}
