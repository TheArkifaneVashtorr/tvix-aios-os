# shellcheck shell=bats

setup() {
  REAL_BASH="$(command -v bash)"
}

# ER8: the drift fixtures -- a real git repo workspace branched task/K1 off
# a base commit, with .factory-meta naming that base so the driver's fork
# point is known. "work": task/K1 carries one commit on top of the base
# (actual_commits 1); "empty": task/K1 sits at the base (actual_commits 0).
# The fake factory-ws prints the workspace path, as 94-seat-harness.bats's
# run_verify_task fixture does.
mk_drift_fixture() {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  ws="$BATS_TEST_TMPDIR/ws"
  git init -q -b main "$ws"
  git -C "$ws" config user.email t@x
  git -C "$ws" config user.name t
  printf 'base\n' >"$ws/f"
  git -C "$ws" add f
  git -C "$ws" commit -qm base
  base_sha=$(git -C "$ws" rev-parse HEAD)
  git -C "$ws" checkout -qb task/K1
  if [ "$1" = work ]; then
    git -C "$ws" commit --allow-empty -qm x
  fi
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  printf '[[route]]\nrole = "implement"\nkind = "any"\nsize = "any"\nmodel = "m/a"\neffort = "medium"\n' >"$fx/docs/ledger/routing.toml"
  plan="$BATS_TEST_TMPDIR/plan.md"
  printf '### K1 (code, M) — t\n\nbody one.\n' >"$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf '%b\n' "\${PAYLOAD}"
FAKE
  chmod +x "$bin/dsh-openrouter"
}

# One factory-task launch against the drift fixture: $1 the seat payload,
# $2 the run name (each run gets its own .factory-meta naming the base).
run_drift_task() {
  mkdir -p "$root/ws/$2/K1"
  printf 'base_sha=%s\n' "$base_sha" >"$root/ws/$2/K1/.factory-meta"
  PAYLOAD="$1" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" "$2" "$repo" K1
}

@test "a FACTORY-RESULT heading is recorded with the grammar it missed" {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf '%b\n' "\${PAYLOAD}"
FAKE
  chmod +x "$bin/dsh-openrouter"
  run_task() {
    PAYLOAD="$1" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
      FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
      OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
      run "$REAL_BASH" "$seat_copy/factory-task" "$2" "$repo" K1
  }

  # A FACTORY-RESULT heading (markdown, not column-one) is a near-miss.
  run_task $'## FACTORY-RESULT\nstatus=done' r1
  [ "$status" -eq 2 ]
  # O1: the hint is logged to the seat's stderr (factory_log "$hint_line"), not
  # only written into the .result block's fifth line below.
  [[ "$output" == *"factory-task: FACTORY-HINT grammar: ^FACTORY-RESULT status=(done|partial|failed) at column one, no markdown"* ]]
  run cat "$root/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=failed exit_code=0" ]
  [[ "$output" == *"result-misparse: ## FACTORY-RESULT"* ]]
  [ "${lines[4]}" = "FACTORY-HINT grammar: ^FACTORY-RESULT status=(done|partial|failed) at column one, no markdown" ]
  ! grep -q '<' "$root/runs/r1/K1.result"

  # Negative control: an accepted line is never re-classified; no FACTORY-HINT.
  # The result block is the FACTORY-* labels up to the blank line that separates
  # them from the keyed metadata; an accepted result has exactly four.
  run_task $'FACTORY-RESULT status=done\nFACTORY-CHECKS none\nFACTORY-COMMITS 0\nFACTORY-NOTES ok' r2
  run awk '/^$/ { exit } { print }' "$root/runs/r2/K1.result"
  # The first label line confirms an accepted result; no fifth hint line.
  [[ "${lines[0]}" == "FACTORY-RESULT status=done"* ]]
  [ "${#lines[@]}" -eq 4 ]
  [[ "$output" != *"FACTORY-HINT"* ]]
  ! grep -q 'FACTORY-HINT' "$root/runs/r2/K1.result"
}

@test "the hint line reaches the --prior block" {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  runs="$BATS_TEST_TMPDIR/runs"
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$runs/r1" "$runs/r2" "$repo/docs/reviews"

  # r1 is the near-miss: a five-line .result whose fifth line is the hint.
  cat >"$runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=failed exit_code=0
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 0
FACTORY-NOTES result-misparse: ## FACTORY-RESULT
FACTORY-HINT grammar: ^FACTORY-RESULT status=(done|partial|failed) at column one, no markdown
EOF

  # r2 is an accepted result: a four-line .result, no hint.
  cat >"$runs/r2/K1.result" <<'EOF'
FACTORY-RESULT status=done
FACTORY-CHECKS none
FACTORY-COMMITS 0
FACTORY-NOTES ok
EOF

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_block '$runs' '$repo' r1 K1"
  [ "$status" -eq 0 ]
  [[ "$output" == *"FACTORY-HINT grammar:"* ]]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_block '$runs' '$repo' r2 K1"
  [ "$status" -eq 0 ]
  [[ "$output" != *"FACTORY-HINT"* ]]
}

@test "a FACTORY-RESULT heading with a commit records unreported plus the fifth hint line" {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  # The workspace is a real git repo branched task/K1 with one commit on top of
  # main, and a .factory-meta recording that base so the driver's fork point is
  # known and actual_commits resolves to 1 (the Interface 1 unreported arm).
  ws="$BATS_TEST_TMPDIR/ws"
  git init -q -b main "$ws"
  git -C "$ws" config user.email t@x
  git -C "$ws" config user.name t
  printf 'base\n' >"$ws/f"
  git -C "$ws" add f
  git -C "$ws" commit -qm base
  base_sha=$(git -C "$ws" rev-parse HEAD)
  git -C "$ws" checkout -qb task/K1
  printf 'work\n' >"$ws/work"
  git -C "$ws" add work
  git -C "$ws" commit -qm work
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (code, M) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  mkdir -p "$root/ws/r1/K1"
  printf 'base_sha=%s\n' "$base_sha" >"$root/ws/r1/K1/.factory-meta"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf '%b\n' "\${PAYLOAD}"
FAKE
  chmod +x "$bin/dsh-openrouter"

  PAYLOAD=$'## FACTORY-RESULT\nstatus=done' FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" \
    FACTORY_PLAN="$plan" FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  run cat "$root/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=unreported exit_code=0" ]
  [ "${lines[2]}" = "FACTORY-COMMITS 1" ]
  [ "${lines[3]}" = "FACTORY-NOTES result-misparse: ## FACTORY-RESULT" ]
  [ "${lines[4]}" = "FACTORY-HINT grammar: ^FACTORY-RESULT status=(done|partial|failed) at column one, no markdown" ]
}

@test "the .result names area, kind and size; a toolbox without the graph writes unknown" {
  # (Mutation: drop the `|| out=unknown` fallback -> factory-task dies and no
  # .result exists; write "$kind $size" raw -> "any any" for an untyped heading.)
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  REPO_ROOT="$BATS_TEST_DIRNAME/../.."
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger" "$fx/pkgs"
  cp -r "$REPO_ROOT/pkgs/evidence" "$fx/pkgs/evidence"; chmod -R u+w "$fx/pkgs/evidence"
  printf '[[route]]\nrole = "implement"\nkind = "any"\nsize = "any"\nmodel = "m/a"\neffort = "medium"\n' >"$fx/docs/ledger/routing.toml"
  cat >"$fx/docs/ledger/subsystems.toml" <<'EOF'
[[subsystem]]
name = "Evidence"
prefix = "EV"
area = "evidence"
gate = "sonnet"
owns = ["pkgs/evidence/*"]
plans = ["docs/superpowers/plans/*.md"]
depends = []
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  printf '### K1 (code, M) — t\n\n**touches:** pkgs/evidence/a.py\n\nbody.\n' >"$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  printf '#!%s\nprintf "FACTORY-RESULT status=done\\nFACTORY-CHECKS none\\nFACTORY-COMMITS 0\\nFACTORY-NOTES ok\\n"\n' "$REAL_BASH" >"$bin/dsh-openrouter"
  chmod +x "$bin/dsh-openrouter"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PYTHON3_CMD="$(command -v python3)" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  run grep -E '^(area|kind|size): ' "$root/runs/r1/K1.result"
  [ "${lines[0]}" = "area: evidence" ]
  [ "${lines[1]}" = "kind: code" ]
  [ "${lines[2]}" = "size: M" ]
  # The same launch against a toolbox without the graph: unknown, never a death.
  rm -r "$fx/pkgs/evidence"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PYTHON3_CMD="$(command -v python3)" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r2 "$repo" K1
  [ "$status" -eq 0 ]
  run grep -c '^area: unknown$' "$root/runs/r2/K1.result"
  [ "$output" = "1" ]
  # An untyped heading: kind/size map `any` to `unknown`, never `kind: any`.
  plan2="$BATS_TEST_TMPDIR/plan-untyped.md"
  printf '### K1 — t\n\n**touches:** pkgs/evidence/a.py\n\nbody.\n' >"$plan2"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PYTHON3_CMD="$(command -v python3)" FACTORY_PLAN="$plan2" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" FACTORY_SEAT_UNIT=0 \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r3 "$repo" K1
  [ "$status" -eq 0 ]
  run grep -c '^kind: unknown$' "$root/runs/r3/K1.result"
  [ "$output" = "1" ]
}

@test "a colon after the FACTORY-RESULT label is accepted with the drift recorded" {
  # (a) The colon payload: the seat did report, only the format drifted --
  # the line is accepted with the colon stripped and the status kept, the
  # drift is recorded on the keyed line right after exit_code and as a
  # notes clause, and the grammar hint stays the block's fifth line.
  mk_drift_fixture work
  run_drift_task $'FACTORY-RESULT: status=done\nFACTORY-CHECKS none=not-run\nFACTORY-COMMITS 1\nFACTORY-NOTES finished' r1
  [ "$status" -eq 0 ]
  run cat "$root/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done" ]
  [ "${lines[4]}" = "FACTORY-HINT grammar: ^FACTORY-RESULT status=(done|partial|failed) at column one, no markdown" ]
  run awk '/^exit_code:/{getline; print; exit}' "$root/runs/r1/K1.result"
  [ "$output" = "format_drift: colon" ]
  grep -q '^format_drift: colon$' "$root/runs/r1/K1.result"
  grep -q '^FACTORY-NOTES finished; format-drift: colon$' "$root/runs/r1/K1.result"

  # A fourth status word is never the colon arm's to accept: the near-miss
  # arms still own it (result-misparse), and the branch's one commit keeps
  # the record unreported (SH2), not failed.
  run_drift_task $'FACTORY-RESULT: status=finished\nFACTORY-CHECKS none=not-run\nFACTORY-COMMITS 1\nFACTORY-NOTES finished' r2
  [ "$status" -eq 0 ]
  run cat "$root/runs/r2/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=unreported exit_code=0" ]
  grep -q 'result-misparse: FACTORY-RESULT: status=finished' "$root/runs/r2/K1.result"
  ! grep -q 'format_drift' "$root/runs/r2/K1.result"

  # A strict line anywhere in the log outranks the colon line: the strict
  # grammar wins, no drift is recorded, no hint is written.
  run_drift_task $'FACTORY-RESULT: status=done\nFACTORY-RESULT status=partial\nFACTORY-CHECKS none=not-run\nFACTORY-COMMITS 1\nFACTORY-NOTES finished' r3
  [ "$status" -eq 1 ]
  run cat "$root/runs/r3/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=partial" ]
  ! grep -q 'format_drift' "$root/runs/r3/K1.result"
  ! grep -q 'FACTORY-HINT' "$root/runs/r3/K1.result"
}

@test "a sha-valued FACTORY-COMMITS is resolved against the branch with the drift recorded" {
  # (b) The sha arm: the seat reported the branch head's sha instead of a
  # count. The claim is resolved to the commit count up to that sha (here
  # actual_commits, so a truthful seat stays done), and the drift is
  # recorded; a strict result line carries no hint.
  mk_drift_fixture work
  head=$(git -C "$ws" rev-parse task/K1)
  payload=$(printf 'FACTORY-RESULT status=done\nFACTORY-CHECKS none=not-run\nFACTORY-COMMITS %s\nFACTORY-NOTES finished' "$head")
  run_drift_task "$payload" r1
  [ "$status" -eq 0 ]
  run cat "$root/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done" ]
  run awk '/^exit_code:/{getline; print; exit}' "$root/runs/r1/K1.result"
  [ "$output" = "format_drift: commits-sha" ]
  grep -q '^FACTORY-NOTES finished; format-drift: commits-sha$' "$root/runs/r1/K1.result"
  ! grep -q 'FACTORY-HINT' "$root/runs/r1/K1.result"
}

@test "a sha-valued FACTORY-COMMITS not on the branch records no drift" {
  # (c) Negative control: deadbeef is a hex token but not an ancestor of
  # task/K1, so the sha arm never fires -- the claim stays empty (the
  # lenient path: no `claimed N commits, found M` clause) and no drift is
  # recorded. The branch carries no commit, so CR3r's zero-commit rule
  # demotes the done claim to failed, today and after the change alike.
  mk_drift_fixture empty
  run_drift_task $'FACTORY-RESULT status=done\nFACTORY-CHECKS none=not-run\nFACTORY-COMMITS deadbeef\nFACTORY-NOTES finished' r1
  [ "$status" -eq 2 ]
  run cat "$root/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=failed" ]
  grep -q '^FACTORY-NOTES status=done but the branch has no commits$' "$root/runs/r1/K1.result"
  ! grep -q 'commits, found' "$root/runs/r1/K1.result"
  ! grep -q 'format_drift' "$root/runs/r1/K1.result"
}

# --- ER13: --recollect rebuilds a result from the seat job's own files ---

# A pre-made run directory -- the launch is not exercised at all. The dead
# launch left runs/r1/K1.log ending at the seat job id line (the collector
# died; the seat job finished anyway and wrote brief.txt, stdout.txt,
# exit_code.txt and result.txt under its own SEAT_JOBS_DIR directory), and
# the workspace lives where the recollect reads it, $FACTORY_WS/<run>/<KEY>:
# a real git repo branched task/K1 with one commit and a .factory-meta naming
# the base. A recording fake seat-submit sits on PATH: any launch (M4's
# discriminating row) leaves SEAT_REC behind.
mk_recollect_fixture() {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  # The workspace is the one --recollect reads by name, $FACTORY_WS/<run>/<KEY>
  # (no faked factory-ws redirection): a real git repo branched task/K1 with
  # one commit, its .factory-meta naming the base.
  root="$BATS_TEST_TMPDIR/factory"
  ws=$root/ws/r1/K1
  mkdir -p -- "$root/runs/r1" "$(dirname -- "$ws")"
  git init -q -b main "$ws"
  git -C "$ws" config user.email t@x
  git -C "$ws" config user.name t
  printf 'base\n' >"$ws/f"
  git -C "$ws" add f
  git -C "$ws" commit -qm base
  base_sha=$(git -C "$ws" rev-parse HEAD)
  git -C "$ws" checkout -qb task/K1
  printf 'work\n' >"$ws/work"
  git -C "$ws" add work
  git -C "$ws" commit -qm work
  printf 'base_sha=%s\n' "$base_sha" >"$ws/.factory-meta"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  printf '[[route]]\nrole = "implement"\nkind = "any"\nsize = "any"\nmodel = "m/a"\neffort = "medium"\n' >"$fx/docs/ledger/routing.toml"
  plan="$BATS_TEST_TMPDIR/plan.md"
  printf '### K1 (code, M) — t\n\nbody one.\n' >"$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/seat-submit" <<FAKE
#!$REAL_BASH
printf 'called\n' >>"\$SEAT_REC"
printf '20990101-000000-ffffff\n'
FAKE
  chmod +x "$bin/seat-submit"
  export SEAT_REC="$BATS_TEST_TMPDIR/seat-rec"
  rm -f -- "$SEAT_REC"
  # The seat job the dead launch left behind: the unit's own files. The dead
  # first job (the run was relaunched once) has no result.txt yet; the last
  # job holds the finished seat's stdout, exit code and result marker.
  jobs="$BATS_TEST_TMPDIR/jobs"
  mkdir -p "$jobs/20260924-110000-111111" "$jobs/20260924-120000-abcdef"
  printf 'the first, dead brief\n' >"$jobs/20260924-110000-111111/brief.txt"
  printf 'the brief\n' >"$jobs/20260924-120000-abcdef/brief.txt"
  printf 'FACTORY-RESULT status=done\nFACTORY-CHECKS unit=pass\nFACTORY-COMMITS 1\nFACTORY-NOTES finished\n' >"$jobs/20260924-120000-abcdef/stdout.txt"
  printf '0\n' >"$jobs/20260924-120000-abcdef/exit_code.txt"
  printf 'ok\n' >"$jobs/20260924-120000-abcdef/result.txt"
  # The log the dead launch left: the submitting line, the dead job's id,
  # the relaunched job's id -- and nothing after (the collector died before
  # stdout.txt streamed back).
  {
    printf 'factory-task: submitting seat job via seat-submit headless\n'
    printf '20260924-110000-111111\n'
    printf '20260924-120000-abcdef\n'
  } >"$root/runs/r1/K1.log"
  export SEAT_JOBS_DIR="$jobs"
}

# Run the recollect verb against the fixture; $@ the extra factory-task args.
run_recollect() {
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1 "$@"
}

@test "--recollect rebuilds the result from the seat job's own files" {
  # (a) The happy path. Mutants this row discriminates: the appended
  # stdout.txt feeds the collection (skip the append -> the log still ends
  # at the id line, no result block, status=failed); the LAST job id wins
  # (head -n1 takes the dead first job and its missing result.txt refuses);
  # nothing is launched (a fall-through into the arms calls the recording
  # fake seat-submit on PATH and SEAT_REC appears).
  mk_recollect_fixture
  run_recollect --recollect
  [ "$status" -eq 0 ]
  run cat "$root/runs/r1/K1.result"
  [ "${lines[0]}" = "FACTORY-RESULT status=done" ]
  [[ "$output" == *"seat: unit seat@20260924-120000-abcdef"* ]]
  [[ "$output" == *"recollected: "* ]]
  grep -q -- '--- recollect' "$root/runs/r1/K1.log"
  [ ! -e "$SEAT_REC" ]
}

@test "--recollect refuses an existing untouched .result and a log without a job id" {
  # (b) The existing .result: exit 2 before any write, the file's bytes
  # unchanged (mutant: overwrite it -> the byte comparison fails).
  mk_recollect_fixture
  printf 'FACTORY-RESULT status=failed\nFACTORY-CHECKS none=not-run\nFACTORY-COMMITS 0\nFACTORY-NOTES old\n' >"$root/runs/r1/K1.result"
  cp "$root/runs/r1/K1.result" "$BATS_TEST_TMPDIR/old.result"
  run_recollect --recollect
  [ "$status" -eq 2 ]
  [[ "$output" == *"K1.result exists"* ]]
  cmp "$BATS_TEST_TMPDIR/old.result" "$root/runs/r1/K1.result"
  # (c) No id line in the log: exit 2, nothing written (no .result appears).
  rm -f -- "$root/runs/r1/K1.result"
  printf 'factory-task: submitting seat job via seat-submit headless\n' >"$root/runs/r1/K1.log"
  run_recollect --recollect
  [ "$status" -eq 2 ]
  [[ "$output" == *"no seat job id"* ]]
  [ ! -e "$root/runs/r1/K1.result" ]
}

@test "--recollect takes no launch option" {
  # (d) --after (likewise --prior, --model, --node, --fallback) alongside
  # --recollect is refused with exit 2 before anything runs.
  mk_recollect_fixture
  run_recollect --recollect --after K0
  [ "$status" -eq 2 ]
  [[ "$output" == *"takes no launch option"* ]]
}
