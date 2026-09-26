#!/usr/bin/env bats
# SD4: a fix round carries the prior attempt. factory_prior_block (in
# tools/factory/seat/factory-lib.sh) composes a ## Prior attempt block from the
# prior .result -- its four FACTORY-* lines and keyed metadata, the diffstat,
# the rejecting Opus review's numbered findings and mutation-table survivors,
# and the seat review's defects -- never the log, never a transcript. It is
# gated on shellcheck by checks.lint and exercised here by its deterministic
# behaviours. Every driver script runs through "$REAL_BASH", never a shebang.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup_file() {
  bats_require_minimum_version 1.5.0
}

setup() {
  REAL_BASH="$(command -v bash)"
}

@test "factory_prior_block composes result, findings and survivors, never the log" {
  runs="$BATS_TEST_TMPDIR/runs"
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$runs/r1" "$repo/docs/reviews"

  cat >"$runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=failed exit_code=2
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 0
FACTORY-NOTES the prior attempt failed
run: r1
key: K1
model: m/a
effort: medium
route: implement/code/S
class: bash-driver
rung: 1
workspace: /ws
branch: task/K1
head: abc123
base: def456
wall_s: 5
exit_code: 2
error_class: none

commits (base..task/K1):
abc123 the prior commit

diffstat:
tools/factory/seat/factory-task | 2 +-
tools/factory/seat/factory-lib.sh | 3 +-

extra: line
usage: {"input": 10, "output": 5}
EOF
  printf 'CANARY-LOG-LINE\n' >"$runs/r1/K1.log"

  # The seat review (its defect contract: `major ` / `minor ` prefixes).
  cat >"$runs/r1/K1.review.md" <<'EOF'
major tools/x:1 -- the first defect
minor tools/y:2 -- a nit
note tools/z:3 -- not a defect
info: something
FACTORY-REVIEW verdict=rework
EOF

  # The newest review (later-sorting date) is APPROVED and must be ignored; the
  # REJECTED one sorts earlier and is the one whose findings are used. This is
  # the discriminating row for the newest-REJECTED rule.
  cat >"$repo/docs/reviews/2026-09-06-opus-review-r0-K1.md" <<'EOF'
---
plan_defect: none
---
# Opus gate — seat run r0, task K1 — APPROVED
APPROVED-ONLY-MARKER
EOF

  cat >"$repo/docs/reviews/2026-09-05-opus-review-r1-K1.md" <<'EOF'
---
plan_defect: implementer
plan_defect_secondary: underspecified
mutants_total: 22
mutants_killed: 22
mutants_outside_named: 1
---
# Opus gate — seat run r1, task K1 — REJECTED

One MAJOR stops it.

**MAJOR-1 — the unit check is red**

**MAJOR-2 — the second defect is also red**

MAJOR-1's evidence is pasted below.

the MAJOR-2 finding continues here

| # | mutant | file | died? | on |
|---|---|---|---|---|
| 5 | drop x | factory-lib.sh | no | t1 |
| 6 | drop y | factory-lib.sh | yes | t2 |
| 7 | **drop the guard** | f.sh | **no** | — |
EOF

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_block '$runs' '$repo' r1 K1"
  [ "$status" -eq 0 ]
  # The block opens on its heading, and carries no trace of the log or the
  # ignored (newer, APPROVED) review.
  [[ "$output" == "## Prior attempt (r1/K1)"* ]]
  [[ "$output" != *CANARY* ]]
  [[ "$output" != *APPROVED-ONLY-MARKER* ]]
  # The result section: the four FACTORY-* lines verbatim, then the keyed lines
  # in file order, usage included -- and none of the excluded metadata keys.
  [[ "$output" == *"**Result:**"*"FACTORY-RESULT status=failed exit_code=2"* ]]
  [[ "$output" == *"FACTORY-CHECKS none=not-run"* ]]
  [[ "$output" == *"FACTORY-COMMITS 0"* ]]
  [[ "$output" == *"FACTORY-NOTES the prior attempt failed"* ]]
  [[ "$output" == *"model: m/a"*"effort: medium"*"route: implement/code/S"*"class: bash-driver"*"rung: 1"* ]]
  [[ "$output" == *"wall_s: 5"* ]]
  [[ "$output" == *"exit_code: 2"* ]]
  [[ "$output" == *"error_class: none"* ]]
  [[ "$output" == *'usage: {"input": 10, "output": 5}'* ]]
  [[ "$output" != *"run: r1"* ]]
  [[ "$output" != *"key: K1"* ]]
  [[ "$output" != *"workspace: /ws"* ]]
  [[ "$output" != *"branch: task/K1"* ]]
  [[ "$output" != *"head: abc123"* ]]
  [[ "$output" != *"base: def456"* ]]
  # The diffstat section carries the two stat lines, never the surrounding
  # `commits (...)` header or the log's lines.
  [[ "$output" == *"**Diffstat:**"*"tools/factory/seat/factory-task | 2 +-"*"tools/factory/seat/factory-lib.sh | 3 +-"* ]]
  [[ "$output" != *"commits (base..task/K1)"* ]]
  [[ "$output" != *"abc123 the prior commit"* ]]
  # The diffstat section ends at the blank line after its stat rows: the
  # `extra: line` that follows it in the .result never leaks in.
  [[ "$output" != *"extra: line"* ]]
  # The Opus review's front-matter facts come verbatim; its findings are
  # numbered 1..; the summary prose line "One MAJOR stops it" is NOT a finding.
  [[ "$output" == *"plan_defect: implementer"* ]]
  [[ "$output" == *"mutants_total: 22"* ]]
  [[ "$output" == *"mutants_killed: 22"* ]]
  [[ "$output" == *"mutants_outside_named: 1"* ]]
  [[ "$output" == *"1. **MAJOR-1 — the unit check is red**"* ]]
  [[ "$output" == *"2. **MAJOR-2 — the second defect is also red**"* ]]
  [[ "$output" != *"One MAJOR stops it"* ]]
  # A line that begins with a word is prose, never a numbered finding, even
  # when it carries MAJOR/MINOR mid-line.
  [[ "$output" != *"MAJOR-1's evidence is pasted below"* ]]
  [[ "$output" != *"the MAJOR-2 finding continues here"* ]]
  # The seat review's defects are numbered after the Opus findings (continuous);
  # a non-defect severity line (`note`, `info:`) is not numbered.
  [[ "$output" == *"3. major tools/x:1 -- the first defect"* ]]
  [[ "$output" == *"4. minor tools/y:2 -- a nit"* ]]
  [[ "$output" != *"note tools/z:3 -- not a defect"* ]]
  [[ "$output" != *"info: something"* ]]
  # Mutation-table survivors: the died?=no row and the bold **no** row, never
  # the yes row or a delimiter/header row.
  [[ "$output" == *"**Mutation-table survivors:**"*"| 5 | drop x | factory-lib.sh | no | t1 |"* ]]
  [[ "$output" == *"| 7 | **drop the guard** | f.sh | **no** | — |"* ]]
  [[ "$output" != *"| 6 | drop y"* ]]
  [[ "$output" != *"| # | mutant"* ]]
  [[ "$output" != *"|---|---"* ]]
}

@test "factory_prior_block reads the pa9-style ### findings and a **SURVIVED** survivor row" {
  runs="$BATS_TEST_TMPDIR/runs"
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$runs/r1" "$repo/docs/reviews"

  cat >"$runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=failed exit_code=2
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 0
FACTORY-NOTES nope
model: m/a
diffstat:
a.txt | 1 +

usage: {}
EOF

  cat >"$repo/docs/reviews/2026-09-05-opus-review-r1-K1.md" <<'EOF'
---
plan_defect: missing-case
mutants_total: 16
mutants_killed: 12
mutants_outside_named: 7
---
# Opus gate — seat run r1, task K1 — REJECTED

### MAJOR 1 — the seat-plan assertion is dead

### MINOR 2 — the boundary is not pinned

| mutant | result |
|---|---|
| a typed heading | **SURVIVED** |
| another | killed |
EOF

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_block '$runs' '$repo' r1 K1"
  [ "$status" -eq 0 ]
  # The ### findings qualify (leading # stripped) and are numbered.
  [[ "$output" == *"1. ### MAJOR 1 — the seat-plan assertion is dead"* ]]
  [[ "$output" == *"2. ### MINOR 2 — the boundary is not pinned"* ]]
  # The survivor arm: a row carrying **SURVIVED** is kept even without a `no`
  # cell; the plain `killed` row is not.
  [[ "$output" == *"| a typed heading | **SURVIVED** |"* ]]
  [[ "$output" != *"| another | killed |"* ]]
}

@test "factory_prior_block reports Review: none filed when no review exists" {
  runs="$BATS_TEST_TMPDIR/runs"
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$runs/r1" "$repo/docs/reviews"

  cat >"$runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=failed exit_code=2
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 0
FACTORY-NOTES nope
model: m/a
diffstat:
a.txt | 1 +

usage: {}
EOF

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_block '$runs' '$repo' r1 K1"
  [ "$status" -eq 0 ]
  [[ "$output" == *"**Review:** none filed"* ]]
  [[ "$output" != *"**Review findings ("* ]]
  # No Opus review means no survivor row: the mutation section falls back to
  # the (none) line.
  [[ "$output" == *"**Mutation-table survivors:**"*"(none)"* ]]
}

@test "factory_prior_block exits 2 with the missing-result message when the .result is absent" {
  runs="$BATS_TEST_TMPDIR/runs"
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$repo/docs/reviews"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_block '$runs' '$repo' r1 NOPE"
  [ "$status" -eq 2 ]
  [[ "$output" == *"factory_prior_block: no prior result $runs/r1/NOPE.result"* ]]
}

@test "factory_prior_block caps a findings list at 60 lines" {
  runs="$BATS_TEST_TMPDIR/runs"
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$runs/r1" "$repo/docs/reviews"

  cat >"$runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=failed exit_code=2
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 0
FACTORY-NOTES nope
model: m/a
diffstat:
a.txt | 1 +

usage: {}
EOF

  {
    printf '%s\n' '---'
    printf '%s\n' 'plan_defect: implementer'
    printf '%s\n' '---'
    printf '%s\n' '# Opus gate — seat run r1, task K1 — REJECTED'
    printf '\n'
    for ((i = 1; i <= 200; i++)); do
      printf '**MAJOR-%d — finding %d**\n' "$i" "$i"
    done
  } >"$repo/docs/reviews/2026-09-05-opus-review-r1-K1.md"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_block '$runs' '$repo' r1 K1"
  [ "$status" -eq 0 ]
  [[ "$output" == *"1. **MAJOR-1 — finding 1**"* ]]
  [[ "$output" == *"60. **MAJOR-60 — finding 60**"* ]]
  [[ "$output" == *"… (140 more lines)"* ]]
  [[ "$output" != *"61. **MAJOR-61"* ]]
  [[ "$output" != *"**MAJOR-200"* ]]
}

@test "factory-task --prior composes the block into the brief and records prior:" {
  seat_copy="$BATS_TEST_TMPDIR/seat"
  cp -r "$SEAT" "$seat_copy"
  chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"
  chmod +x "$seat_copy/factory-ws"

  fx="$BATS_TEST_TMPDIR/toolbox"
  mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/a"
effort = "medium"

[[route]]
role = "any"
kind = "any"
size = "any"
rung = 2
model = "m/a"
effort = "high"
EOF

  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1b (code, S) — the fix round

body one.
EOF

  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$bin"

  # The fake seat-submit records the composed brief and prints a job id then a
  # valid FACTORY-RESULT block, the way 80-seat-driver.bats drives factory-task.
  cat >"$bin/seat-submit" <<FAKE
#!$REAL_BASH
printf 'args=%s\\n' "\$*" >> "\$REC"
brief=
prev=
for a in "\$@"; do
  if [ "\$prev" = "--brief" ]; then brief="\$a"; fi
  prev="\$a"
done
printf 'brief_begin\\n' >> "\$REC"
cat -- "\$brief" >> "\$REC"
printf 'brief_end\\n' >> "\$REC"
printf '20260905-120000-abcdef\\n'
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/seat-submit"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
: > "\$DSH_CALLED"
printf 'FACTORY-RESULT status=done\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"

  root="$BATS_TEST_TMPDIR/factory"
  mkdir -p "$root/runs/r1"
  # The prior attempt: a full .result plus a canary log and a rejecting review.
  cat >"$root/runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=failed exit_code=2
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 0
FACTORY-NOTES nope
run: r1
key: K1
model: m/a
effort: medium
route: implement/code/S
rung: 1
attempts: 1
workspace: /ws
wall_s: 5
exit_code: 2
error_class: none

commits (base..task/K1):
abc123 the prior commit

diffstat:
tools/factory/seat/factory-task | 2 +-

usage: {}
EOF
  printf 'CANARY-LOG-LINE\n' >"$root/runs/r1/K1.log"
  mkdir -p "$repo/docs/reviews"
  cat >"$repo/docs/reviews/2026-09-05-opus-review-r1-K1.md" <<'EOF'
---
plan_defect: implementer
---
# Opus gate — seat run r1, task K1 — REJECTED

**MAJOR-1 — the unit check is red**
EOF

  rec="$BATS_TEST_TMPDIR/rec"
  dsh_called="$BATS_TEST_TMPDIR/DSH_CALLED"
  share="$BATS_TEST_TMPDIR/share"
  mkdir -p "$share"

  REC="$rec" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    DSH_CALLED="$dsh_called" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r2 "$repo" K1b --prior r1/K1
  [ "$status" -eq 0 ]
  [ ! -e "$dsh_called" ]

  run cat "$rec"
  # The prior block sits between the task section and the WORKSPACE RULES, and
  # the log's canary never leaks into the brief.
  [[ "$output" == *"### K1b"*"## Prior attempt (r1/K1)"*"## WORKSPACE RULES"* ]]
  [[ "$output" != *CANARY* ]]
  [[ "$output" == *"FACTORY-RESULT status=failed exit_code=2"* ]]

  # The new .result carries the class: line immediately after route: (SD2),
  # then OC8's area/kind/size lines, then the prior: line, before plan:.
  run grep -A5 '^route:' "$root/runs/r2/K1b.result"
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "route: implement/code/S" ]
  [ "${lines[1]}" = "class: any" ]
  [ "${lines[2]}" = "area: unknown" ]
  [ "${lines[3]}" = "kind: code" ]
  [ "${lines[4]}" = "size: S" ]
  [ "${lines[5]}" = "prior: r1/K1" ]

  # SD3: K1b derives rung 2 from the prior record's rung 1 (and attempts 2 from
  # its attempts 1), so the .result carries rung: 2 then attempts: 2 after
  # effort: (the rung-2 row climbs model m/a, effort high).
  run grep -A2 '^effort:' "$root/runs/r2/K1b.result"
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "effort: high" ]
  [ "${lines[1]}" = "rung: 2" ]
  [ "${lines[2]}" = "attempts: 2" ]

  # A --prior value naming no result refuses before any new run dir exists.
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r3 "$repo" K1b --prior r1/NOPE
  [ "$status" -eq 2 ]
  [ ! -e "$root/runs/r3" ]
  [[ "$output" == *"factory_prior_block: no prior result $root/runs/r1/NOPE.result"* ]]

  # A --prior value outside the shape is refused at parse time.
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r4 "$repo" K1b --prior bad
  [ "$status" -eq 2 ]
  [ ! -e "$root/runs/r4" ]
  [[ "$output" == *"--prior bad is not a <run>/<KEY> pair"* ]]

  # A three-segment value is refused for its shape, not for a missing result:
  # r1/K1 exists, but r1/K1/extra never reaches the composer.
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" r5 "$repo" K1b --prior r1/K1/extra
  [ "$status" -eq 2 ]
  [ ! -e "$root/runs/r5" ]
  [[ "$output" == *"--prior r1/K1/extra is not a <run>/<KEY> pair"* ]]
}

@test "factory-brief run bare prints no prior block" {
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1b (code, S) — the fix round

body one.
EOF

  unset_out="$BATS_TEST_TMPDIR/unset.out"
  empty_out="$BATS_TEST_TMPDIR/empty.out"
  env -u FACTORY_BRIEF_PRIOR "$REAL_BASH" "$SEAT/factory-brief" "$plan" K1b >"$unset_out"
  FACTORY_BRIEF_PRIOR= "$REAL_BASH" "$SEAT/factory-brief" "$plan" K1b >"$empty_out"

  # A bare brief (FACTORY_BRIEF_PRIOR unset) is byte-identical to one with the
  # variable set to the empty string: nothing extra is emitted either way.
  run cmp "$unset_out" "$empty_out"
  [ "$status" -eq 0 ]

  run cat "$unset_out"
  [ "$status" -eq 0 ]
  [[ "$output" != *"## Prior attempt"* ]]
  # WORKSPACE RULES is preceded by exactly one blank line.
  [[ "$output" == *$'\n\n'"## WORKSPACE RULES"* ]]
  [[ "$output" != *$'\n\n\n'"## WORKSPACE RULES"* ]]
}

@test "factory_prior_block lists a bold-survivor review's rows, never (none)" {
  runs="$BATS_TEST_TMPDIR/runs"
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$runs/r1" "$repo/docs/reviews"

  cat >"$runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=failed exit_code=2
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 0
FACTORY-NOTES nope
model: m/a
diffstat:
a.txt | 1 +

usage: {}
EOF

  cat >"$repo/docs/reviews/2026-09-06-opus-review-pb11-K1.md" <<'EOF'
---
plan_defect: implementer
mutants_total: 9
mutants_killed: 2
mutants_outside_named: 7
---
# Opus gate — seat run pb11, task K1 — REJECTED

| # | mutant | file | died? | on |
|---|---|---|---|---|
| 3 | drop the guard | f.sh | **no** | — |
| 7 | widen the arm | g.sh | **no** | — |
EOF

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_block '$runs' '$repo' r1 K1"
  [ "$status" -eq 0 ]
  [[ "$output" == *"| 3 | drop the guard | f.sh | **no** | — |"* ]]
  [[ "$output" == *"| 7 | widen the arm | g.sh | **no** | — |"* ]]
  [[ "$output" != *"**Mutation-table survivors:**"*"(none)"* ]]
}

@test "factory_prior_byte_cap caps at 8,000 bytes, counting bytes" {
  dash_line=$(printf '—%.0s' $(seq 190))
  {
    for ((i = 0; i < 60; i++)); do
      printf '%s\n' "$dash_line"
    done
  } >"$BATS_TEST_TMPDIR/dashes"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_byte_cap <'$BATS_TEST_TMPDIR/dashes'"
  [ "$status" -eq 0 ]
  byte_count=$(printf '%s' "$output" | wc -c)
  [ "$byte_count" -le 8000 ]
  [[ "$output" == *"… ("*" more lines)"* ]]

  x_line=$(printf 'x%.0s' $(seq 190))
  {
    for ((i = 0; i < 60; i++)); do
      printf '%s\n' "$x_line"
    done
  } >"$BATS_TEST_TMPDIR/xes"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_byte_cap <'$BATS_TEST_TMPDIR/xes'"
  [ "$status" -eq 0 ]
  # At most 41 ASCII lines (60 × 191 bytes > 8,000) pass before the cut.
  line_count=$(printf '%s\n' "$output" | grep -c '^x')
  [ "$line_count" -le 41 ]
}

@test "factory_prior_block prints no none-filed marker when a seat review file exists" {
  runs="$BATS_TEST_TMPDIR/runs"
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$runs/r1" "$repo/docs/reviews"

  cat >"$runs/r1/K1.result" <<'EOF'
FACTORY-RESULT status=failed exit_code=2
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 0
FACTORY-NOTES nope
model: m/a
diffstat:
a.txt | 1 +

usage: {}
EOF

  # A seat review FILE that carries no defect line: the marker claims more than
  # it knows when it prints "none filed" for a review that simply has no
  # severity line.
  cat >"$runs/r1/K1.review.md" <<'EOF'
FACTORY-REVIEW verdict=rework
EOF

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_prior_block '$runs' '$repo' r1 K1"
  [ "$status" -eq 0 ]
  [[ "$output" != *"**Review:** none filed"* ]]
  [[ "$output" != *"**Review findings ("* ]]
}

@test "factory_rung_from_prior and factory_attempts_from_prior read the prior record" {
  runs="$BATS_TEST_TMPDIR/runs"
  mkdir -p "$runs/p"
  cat >"$runs/p/K1.result" <<'EOF'
rung: 1
attempts: 1
EOF

  # A prior at rung 1 / attempts 1 yields the next round's 2 / 2.
  FACTORY_RUNS="$runs" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_rung_from_prior p/K1"
  [ "$status" -eq 0 ]
  [ "$output" = "2" ]
  FACTORY_RUNS="$runs" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_attempts_from_prior p/K1"
  [ "$status" -eq 0 ]
  [ "$output" = "2" ]

  # No prior record defaults to rung 1 / attempts 1.
  FACTORY_RUNS="$runs" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_rung_from_prior ''"
  [ "$output" = "1" ]
  FACTORY_RUNS="$runs" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_attempts_from_prior ''"
  [ "$output" = "1" ]

  # A prior whose rung:/attempts: line carries an "(explicit)" marker (written
  # by an explicit --rung N) still parses: the first whitespace-delimited token
  # is the integer, the trailing marker is ignored. factory-lib.sh derives
  # FACTORY_RUNS from FACTORY_ROOT on source, so the call names FACTORY_ROOT
  # (not FACTORY_RUNS, which the source overwrites).
  cat >"$runs/p/K2.result" <<'EOF'
rung: 5 (explicit)
attempts: 5 (explicit)
EOF
  FACTORY_ROOT="$BATS_TEST_TMPDIR" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_rung_from_prior p/K2"
  [ "$status" -eq 0 ]
  [ "$output" = "6" ]
  FACTORY_ROOT="$BATS_TEST_TMPDIR" run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_attempts_from_prior p/K2"
  [ "$status" -eq 0 ]
  [ "$output" = "6" ]
}