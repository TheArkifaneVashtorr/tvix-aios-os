#!/usr/bin/env bats
# tools/session-start.sh is the SessionStart hook (.claude/settings.json):
# it prints the board's START HERE, the evidence bundle and the task brief.
# These tests run it against a fake repo and fake `evidence` binaries.

SCRIPT="$BATS_TEST_DIRNAME/../../tools/session-start.sh"

bats_require_minimum_version 1.5.0

setup() {
  REAL_BASH="$(command -v bash)"
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO/docs" "$REPO/pkgs/evidence" "$BATS_TEST_TMPDIR/bin"
  # The brief runs the TREE's renderer, so the fake repo carries a minimal stub
  # at the path the hook invokes ($repo/pkgs/evidence/tasks.py). It is a stub
  # rather than a copy of the real tasks.py because the unit sandbox does not
  # ship pkgs/evidence; the real renderer is covered by evidence-unit and the
  # live host probe. It just prints the brief's heading.
  cat >"$REPO/pkgs/evidence/tasks.py" <<'PYEOF'
import sys
if "brief" in sys.argv[1:]:
    print("# Task brief")
PYEOF
  git -C "$BATS_TEST_TMPDIR" init -q "$REPO"
  printf '# Operations board\n\n## START HERE (today)\n\nQueued: G5.\n\n## Log\n\nold\n' >"$REPO/docs/OPERATIONS.md"
  # The checks.unit sandbox has no /usr/bin/env, so the fake binary carries the
  # real bash's absolute path as its shebang (same trick as 80-seat-driver.bats).
  {
    printf '#!%s\n' "$REAL_BASH"
    cat <<'EOF'
case "$1 $2" in
  "bundle --markdown") echo "# Evidence bundle"; echo "live gen 40" ;;
  *) echo "unexpected: $*" >&2; exit 9 ;;
esac
EOF
  } >"$BATS_TEST_TMPDIR/bin/evidence"
  chmod +x "$BATS_TEST_TMPDIR/bin/evidence"
}

@test "prints START HERE, bundle, brief and the runbook pointer, in order" {
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"## START HERE (today)"* ]]
  [[ "$output" == *"Queued: G5."* ]]
  [[ "$output" != *"old"* ]]
  [[ "$output" == *"# Evidence bundle"* ]]
  [[ "$output" == *"# Task brief"* ]]
  [[ "$output" == *"docs/runbooks/session.md"* ]]
  a=$(printf '%s' "$output" | grep -n 'START HERE' | head -1 | cut -d: -f1)
  b=$(printf '%s' "$output" | grep -n 'Evidence bundle' | cut -d: -f1)
  c=$(printf '%s' "$output" | grep -n 'Task brief' | cut -d: -f1)
  [ "$a" -lt "$b" ]
  [ "$b" -lt "$c" ]
}

@test "without evidence on PATH the board still prints and each missing part says unavailable" {
  run env -i PATH="$PATH" HOME="$BATS_TEST_TMPDIR" SESSION_START_EVIDENCE=/nonexistent/evidence bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Queued: G5."* ]]
  [[ "$output" == *"unavailable: evidence not on PATH"* ]]
}

@test "silent when FACTORY_RUN is set" {
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" FACTORY_RUN=ev3 bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "silent in a linked worktree" {
  git -C "$REPO" -c user.name=t -c user.email=t@x commit -q --allow-empty -m init
  git -C "$REPO" worktree add -q "$BATS_TEST_TMPDIR/wt" -b wt
  mkdir -p "$BATS_TEST_TMPDIR/wt/docs" && cp "$REPO/docs/OPERATIONS.md" "$BATS_TEST_TMPDIR/wt/docs/"  # the empty commit carried no files
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$BATS_TEST_TMPDIR/wt"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "output over the cap ends with a truncation line" {
  { echo '# Operations board'; echo; echo '## START HERE (big)'; yes 'a line of board text that repeats' | head -400; } >"$REPO/docs/OPERATIONS.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" SESSION_START_CAP=2000 bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [ "${#output}" -le 2200 ]
  [[ "$output" == *"…truncated"* ]]
}

@test "a bundle over its cap (2100) is cut and the brief and pointer still print" {
  { printf '#!%s\n' "$REAL_BASH"; cat <<'EOF'
case "$1 $2" in
  "bundle --markdown") printf '# Evidence bundle\n'; yes x | tr -d '\n' | head -c 4000; printf '\n' ;;
  "tasks --root") printf '# Task brief\n| repo |\n' ;;
  *) echo "unexpected: $*" >&2; exit 9 ;;
esac
EOF
  } >"$BATS_TEST_TMPDIR/bin/evidence"
  chmod +x "$BATS_TEST_TMPDIR/bin/evidence"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"…bundle truncated at 2100 chars (SESSION_START_CAP_BUNDLE)"* ]]
  [[ "$output" == *"# Task brief"* ]]
  [[ "$output" == *"docs/runbooks/session.md"* ]]
}

@test "a board over its cap (2300) is cut and the bundle still follows" {
  { echo '# Operations board'; echo; echo '## START HERE (big)'; yes 'a line of board text that repeats' | head -400; } >"$REPO/docs/OPERATIONS.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"…board truncated at 2300 chars (SESSION_START_CAP_BOARD)"* ]]
  [[ "$output" == *"# Evidence bundle"* ]]
  a=$(printf '%s' "$output" | grep -n 'board truncated' | head -1 | cut -d: -f1)
  b=$(printf '%s' "$output" | grep -n 'Evidence bundle' | head -1 | cut -d: -f1)
  [ "$a" -lt "$b" ]
}

@test "a brief over its cap (1400) is cut at the default 1400" {
  # The brief part's default cap is 1400 (raised from 1200 so the Record line
  # keeps headroom), so a 3000-char brief is cut at 1400, not 1200. Mutant:
  # leave the default at 1200 -> the truncation line says 1200 and the 1400
  # assertion fails.
  { printf 'print("# Task brief")\nprint("y" * 3000)\n'; } >"$REPO/pkgs/evidence/tasks.py"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"…brief truncated at 1400 chars (SESSION_START_CAP_BRIEF)"* ]]
}

@test "the total cap applies after the parts and ends the output" {
  { echo '# Operations board'; echo; echo '## START HERE (big)'; yes 'a line of board text that repeats' | head -400; } >"$REPO/docs/OPERATIONS.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" SESSION_START_CAP=1000 bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  last=$(printf '%s\n' "$output" | tail -1)
  [ "$last" = "…truncated at 1000 chars (SESSION_START_CAP)" ]
}

@test "a failing evidence bundle says unavailable while the brief still prints from the tree" {
  { printf '#!%s\n' "$REAL_BASH"; printf 'exit 9\n'; } >"$BATS_TEST_TMPDIR/bin/evidence"
  chmod +x "$BATS_TEST_TMPDIR/bin/evidence"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"unavailable: evidence bundle failed"* ]]
  [[ "$output" == *"# Task brief"* ]]
  [[ "$output" == *"Queued: G5."* ]]
}

@test "the brief runs the tree's tasks.py through RITUAL_PYTHON" {
  # RITUAL_PYTHON names a wrapper that records its argv then execs the real
  # python3; the recorded argv must carry `pkgs/evidence/tasks.py`, proving the
  # brief forks the tree's renderer through that interpreter. (Mutation: calling
  # `$ev tasks` instead leaves the record untouched and the test fails.)
  record="$BATS_TEST_TMPDIR/recorded-argv"
  {
    printf '#!%s\n' "$REAL_BASH"
    printf 'printf "%%s\\n" "$@" >> "%s"\n' "$record"
    printf 'exec %q "$@"\n' "$(command -v python3)"
  } >"$BATS_TEST_TMPDIR/bin/ritual-python"
  chmod +x "$BATS_TEST_TMPDIR/bin/ritual-python"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    RITUAL_PYTHON="$BATS_TEST_TMPDIR/bin/ritual-python" \
    bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ -s "$record" ]]
  [[ "$(cat "$record")" == *"pkgs/evidence/tasks.py"* ]]
  [[ "$output" == *"# Task brief"* ]]
}

@test "with defaults the brief and the pointer print last even when all three parts overflow" {
  # A 400-line board, a 4000-char bundle and a 3000-char brief: each part exceeds
  # its own cap, so the total ceiling must still leave room for the brief and the
  # pointer. This is the one test that kills M3 (pointer printed before the brief),
  # M8 (brief cap removed) and M10 (total cap reverted to 6000).
  { echo '# Operations board'; echo; echo '## START HERE (big)'; yes 'a line of board text that repeats' | head -400; } >"$REPO/docs/OPERATIONS.md"
  { printf '#!%s\n' "$REAL_BASH"; cat <<'EOF'
case "$1 $2" in
  "bundle --markdown") printf '# Evidence bundle\n'; yes x | tr -d '\n' | head -c 4000; printf '\n' ;;
  *) echo "unexpected: $*" >&2; exit 9 ;;
esac
EOF
  } >"$BATS_TEST_TMPDIR/bin/evidence"
  chmod +x "$BATS_TEST_TMPDIR/bin/evidence"
  # The brief is the tree's renderer; stub it to emit a 3000-char brief so the
  # per-part cap still gets exercised (the renderer's output is what is capped).
  { printf 'print("# Task brief")\nprint("y" * 3000)\n'; } >"$REPO/pkgs/evidence/tasks.py"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | tail -n1)" = "Where everything is: docs/runbooks/session.md" ]
  [[ "$output" == *"…board truncated at 2300 chars (SESSION_START_CAP_BOARD)"* ]]
  [[ "$output" == *"…bundle truncated at 2100 chars (SESSION_START_CAP_BUNDLE)"* ]]
  [[ "$output" == *"…brief truncated at 1400 chars (SESSION_START_CAP_BRIEF)"* ]]
  [[ "$output" == *"# Task brief"* ]]
  [ "${#output}" -le 8000 ]
  brief=$(printf '%s' "$output" | grep -n 'Task brief' | head -1 | cut -d: -f1)
  last=$(printf '%s' "$output" | grep -n 'docs/runbooks/session.md' | head -1 | cut -d: -f1)
  [ "$brief" -lt "$last" ]
}

@test "source=compact with a handoff file prints it under ## Handoff" {
  mkdir -p "$BATS_TEST_TMPDIR/state/nixos-agent-env/ritual"
  printf 'objective: CR1\nnext: write the ritual\n' >"$BATS_TEST_TMPDIR/state/nixos-agent-env/ritual/handoff-s1.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$BATS_TEST_TMPDIR/state" \
    bash "$SCRIPT" "$REPO" <<< '{"session_id":"s1","source":"compact"}'
  [ "$status" -eq 0 ]
  [[ "$output" == *"## Handoff"* ]]
  [[ "$output" == *"objective: CR1"* ]]
}

@test "a last-stop stamp two hours old prints the idle notice" {
  mkdir -p "$BATS_TEST_TMPDIR/state/nixos-agent-env/ritual"
  printf '%s\n' "$(( $(date +%s) - 7200 ))" >"$BATS_TEST_TMPDIR/state/nixos-agent-env/ritual/last-stop"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$BATS_TEST_TMPDIR/state" \
    bash "$SCRIPT" "$REPO" <<< '{"session_id":"s1","source":"resume"}'
  [ "$status" -eq 0 ]
  [[ "$output" == *"idle 120 min"* ]]
}

@test "the in-flight part lists live runs under ## In flight" {
  mkdir -p "$BATS_TEST_TMPDIR/factory/runs/aa"
  printf 'log\n' >"$BATS_TEST_TMPDIR/factory/runs/aa/K.log"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    XDG_STATE_HOME="$BATS_TEST_TMPDIR/state" FACTORY_ROOT="$BATS_TEST_TMPDIR/factory" \
    bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"## In flight"* ]]
  [[ "$output" == *"aa K - running"* ]]
}

@test "session-start returns within 2s when stdin is closed" {
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    timeout 2 bash -c 'exec 0<&-; bash "$0" "$1"' "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
}

@test "session-start returns within 2s when stdin is a pipe that never writes" {
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    timeout 2 bash "$SCRIPT" "$REPO" 0< <(:)
  [ "$status" -eq 0 ]
}
@test "the operator-model part prints after the brief, capped at 500 by default" {
  # A 700-char operator model exceeds the default cap, so the fifth part must be
  # cut and followed by the part's truncation line, leaving exactly 500 `o`s.
  # (Mutation: removing the cap prints all 700 `o`s and this test fails.)
  mkdir -p "$REPO/docs/board"
  head -c 700 /dev/zero | tr '\0' o >"$REPO/docs/board/operator-model.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"## Operator model (docs/board/operator-model.md)"* ]]
  [[ "$output" == *"…operator truncated at 500 chars (SESSION_START_CAP_OPERATOR)"* ]]
  # exactly 500 o's then the newline the truncation line starts on, never 501
  [[ "$output" == *"$(printf 'o%.0s' $(seq 1 500))"* ]]
  [[ "$output" != *"$(printf 'o%.0s' $(seq 1 501))"* ]]
}

@test "a missing operator model degrades to one unavailable line and the pointer stays last" {
  # The hook must not fail the session when the file is missing: it prints the
  # unavailable line, exits 0 and still ends on the runbook pointer. (Mutation:
  # skipping the part on a missing file drops the pointer from last; exiting 1
  # on a missing file fails the status-0 assertion.)
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"unavailable: docs/board/operator-model.md not readable"* ]]
  [ "$(printf '%s\n' "$output" | tail -n1)" = "Where everything is: docs/runbooks/session.md" ]
}

@test "the operator-model part prints between the brief and the pointer" {
  # The part must appear after the brief heading and before the runbook pointer.
  # (Mutation: printing the part before the brief inverts the line-number order.)
  mkdir -p "$REPO/docs/board"
  printf '# test operator model\n' >"$REPO/docs/board/operator-model.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  brief=$(printf '%s' "$output" | grep -n 'Task brief' | head -1 | cut -d: -f1)
  model=$(printf '%s' "$output" | grep -n 'Operator model' | head -1 | cut -d: -f1)
  pointer=$(printf '%s' "$output" | grep -n 'Where everything is' | head -1 | cut -d: -f1)
  [ -n "$brief" ]
  [ -n "$model" ]
  [ -n "$pointer" ]
  [ "$brief" -lt "$model" ]
  [ "$model" -lt "$pointer" ]
}

@test "SESSION_START_CAP_OPERATOR overrides the default 500" {
  # The cap must come from the environment, not the hard-coded default.
  # (Mutation: hard-coding 500 ignores SESSION_START_CAP_OPERATOR=100 and the
  # test fails because the 700-char file is cut at 500, not 100.)
  mkdir -p "$REPO/docs/board"
  head -c 700 /dev/zero | tr '\0' o >"$REPO/docs/board/operator-model.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    SESSION_START_CAP_OPERATOR=100 bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"…operator truncated at 100 chars (SESSION_START_CAP_OPERATOR)"* ]]
}

@test "the five part defaults sum to at most the total ceiling minus 700" {
  # The five per-part defaults (board, bundle, brief, in-flight, operator) are
  # read out of tools/session-start.sh itself — never hard-coded here — and must
  # sum to at most SESSION_START_CAP minus 700, so the six headings, the six
  # truncation lines and the pointer always fit under the 8000 total even when
  # every part overflows. (Mutation: raising one default by 700 pushes the sum
  # over the budget and this test fails.)
  total=$(grep -oE 'SESSION_START_CAP:-[0-9]+' "$SCRIPT" | head -n1 | grep -oE '[0-9]+')
  parts=$(grep -oE 'cap_part [A-Z_]+ "[^"]+" [0-9]+' "$SCRIPT" | awk '{print $NF}')
  count=$(printf '%s\n' "$parts" | wc -l | tr -d ' ')
  sum=0
  for n in $parts; do
    sum=$((sum + n))
  done
  [ "$count" -eq 5 ]
  [ "$sum" -le "$((total - 700))" ]
}

@test "with every part overflowing the output stays under 8000 and the pointer stays last" {
  # Fill all six parts past their caps — a >2300-char board, a >2100-char bundle,
  # a >1400-char brief, a >1000-char in-flight table (many fake live runs) and a
  # >500-char operator model. The five caps sum to 7300, leaving room for the six
  # headings, six truncation lines and the pointer under the 8000 total, so the
  # pointer survives and every heading prints. (Mutation: restoring the old
  # defaults 3000/2500/1500/1200/600 pushes the assembled output past 8000, the
  # total cap fires and the pointer is truncated away, failing this test.)
  { echo '# Operations board'; echo; echo '## START HERE (big)'; yes 'a line of board text that repeats' | head -400; } >"$REPO/docs/OPERATIONS.md"
  { printf '#!%s\n' "$REAL_BASH"; cat <<'EOF'
case "$1 $2" in
  "bundle --markdown") printf '# Evidence bundle\n'; yes x | tr -d '\n' | head -c 4000; printf '\n' ;;
  *) echo "unexpected: $*" >&2; exit 9 ;;
esac
EOF
  } >"$BATS_TEST_TMPDIR/bin/evidence"
  chmod +x "$BATS_TEST_TMPDIR/bin/evidence"
  { printf 'print("# Task brief")\nprint("y" * 3000)\n'; } >"$REPO/pkgs/evidence/tasks.py"
  i=0
  while [ "$i" -lt 50 ]; do
    mkdir -p "$BATS_TEST_TMPDIR/factory/runs/aa$(printf '%02d' "$i")"
    printf 'log\n' >"$BATS_TEST_TMPDIR/factory/runs/aa$(printf '%02d' "$i")/K.log"
    i=$((i + 1))
  done
  mkdir -p "$REPO/docs/board"
  head -c 2000 /dev/zero | tr '\0' o >"$REPO/docs/board/operator-model.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    FACTORY_ROOT="$BATS_TEST_TMPDIR/factory" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  # precondition: the in-flight part is genuinely filled, not empty
  [[ "$output" == *"## In flight"* ]]
  [[ "$output" == *"aa00 K - running"* ]]
  [ "${#output}" -le 8000 ]
  [ "$(printf '%s\n' "$output" | tail -n1)" = "Where everything is: docs/runbooks/session.md" ]
  [[ "$output" == *"## Board — START HERE (docs/OPERATIONS.md)"* ]]
  [[ "$output" == *"# Evidence bundle"* ]]
  [[ "$output" == *"# Task brief"* ]]
  [[ "$output" == *"## Operator model (docs/board/operator-model.md)"* ]]
  [[ "$output" == *"…board truncated at 2300 chars (SESSION_START_CAP_BOARD)"* ]]
  [[ "$output" == *"…bundle truncated at 2100 chars (SESSION_START_CAP_BUNDLE)"* ]]
  [[ "$output" == *"…brief truncated at 1400 chars (SESSION_START_CAP_BRIEF)"* ]]
  [[ "$output" == *"…inflight truncated at 1000 chars (SESSION_START_CAP_INFLIGHT)"* ]]
  [[ "$output" == *"…operator truncated at 500 chars (SESSION_START_CAP_OPERATOR)"* ]]
}

@test "a non-numeric part cap falls back to that part's default" {
  # A non-numeric SESSION_START_CAP_<NAME> (e.g. "abc") must not print the part
  # uncapped: the one helper every part uses falls back to that part's default.
  # (Mutation: removing the numeric fallback makes `[ "${#text}" -gt abc ]` error
  # and take the uncapped branch, so this >2300-char board prints whole and the
  # truncation line never appears, failing this test.)
  { echo '# Operations board'; echo; echo '## START HERE (big)'; yes 'a line of board text that repeats' | head -400; } >"$REPO/docs/OPERATIONS.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" \
    SESSION_START_CAP_BOARD=abc bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"…board truncated at 2300 chars (SESSION_START_CAP_BOARD)"* ]]
}
