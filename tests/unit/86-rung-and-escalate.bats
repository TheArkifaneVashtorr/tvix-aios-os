#!/usr/bin/env bats
# SD3: the climb is rule A1. A key's rung comes from its chain suffix
# (factory_rung_of_key): a bare root is rung 1, a fix-round suffix (a trailing
# one or two lowercase letters after a digit without an `r`) is rung 2, a
# re-plan suffix (with an `r`) is rung 3. factory-task and factory-review climb
# the routing ladder to that rung; when the ladder is exhausted at that rung
# the task is a claude rung -- the driver prints a launch line and exits 4,
# writing a <KEY>.escalate record instead of running (no workspace, log, pid
# file or .result). Every script runs through "$REAL_BASH", never a shebang.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup_file() {
  bats_require_minimum_version 1.5.0

  # The rung/escalate fixture: an openrouter implement/code/any ladder with
  # rungs 1..2 only (rung 3 is exhausted -> a claude rung), a fallback-bearing
  # implement row, a review default at rung 1 only, and the claude rows the
  # escalation resolves: implement/any/any sonnet high, review/code/any opus
  # high, any/any/any sonnet medium.
  cat >"$BATS_FILE_TMPDIR/rung.toml" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/d"
effort = "low"

[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
model = "m/a"
effort = "medium"
fallback = "m/f"

[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
rung = 2
model = "m/a"
effort = "high"

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
model = "m/f"
effort = "off"

[[route]]
route = "openrouter"
role = "review"
kind = "any"
size = "any"
model = "m/a"
effort = "medium"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"

[[route]]
route = "claude"
role = "implement"
kind = "any"
size = "any"
model = "sonnet"
effort = "high"

[[route]]
route = "claude"
role = "review"
kind = "code"
size = "any"
model = "opus"
effort = "high"
EOF
}

setup() {
  REAL_BASH="$(command -v bash)"
  export FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"
  export FACTORY_RUNS="$BATS_TEST_TMPDIR/factory/runs"
}

# A seat copy whose factory-brief shebang is repointed to the sandbox bash and
# whose factory-ws prints $1 and (when $2 is given) appends its argv to $2.
# Usage: seat_env <seat-copy> [<ws-record-file>]
seat_env() {
  local copy=$1 rec=${2:-}
  cp -r "$SEAT" "$copy"
  chmod -R u+w "$copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  if [ -n "$rec" ]; then
    printf '#!%s\nprintf "call %%s\\n" "$*" >> %q\nprintf "%%s\\n" %q\n' \
      "$REAL_BASH" "$rec" "$BATS_TEST_TMPDIR/ws" >"$copy/factory-ws"
  else
    printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$copy/factory-ws"
  fi
  chmod +x "$copy/factory-ws"
}

# Route a (code, M) short plan so every test can name K2/K2b/K2c/K2r headings.
write_plan() {
  cat >"$1" <<'EOF'
### K2 (code, M) — t

body two.

### K2b (code, M) — t

body two-b.

### K2c (code, M) — t

body two-c.

### K2r (code, M) — t

body two-r.
EOF
}

@test "factory_rung_of_key classifies the chain suffix: root 1, fix 2, replan 3" {
  for spec in "SD3:1" "SD3b:2" "SD3c:2" "SD3r:3" "SD3rb:3" "P3Ar2:1" "CR2r3b:2"; do
    key=${spec%%:*}
    want=${spec##*:}
    got=$("$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_rung_of_key '$key'")
    [ "$got" = "$want" ]
  done
}

@test "factory-task climbs the rung from the key and records rung: after effort:" {
  seatcpy="$BATS_TEST_TMPDIR/seat"; seat_env "$seatcpy"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cp "$BATS_FILE_TMPDIR/rung.toml" "$fx/docs/ledger/routing.toml"
  plan="$BATS_TEST_TMPDIR/plan.md"; write_plan "$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'model=%s\\n' "\$2" >> "\$REC"
printf 'effort=%s\\n' "\${OPENROUTER_REASONING_EFFORT:-}" >> "\$REC"
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  rec1="$BATS_TEST_TMPDIR/rec1"; rec2="$BATS_TEST_TMPDIR/rec2"

  # K2 (no suffix) is rung 1 -> m/a medium.
  REC="$rec1" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    PATH="$bin:$PATH" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seatcpy/factory-task" r1 "$repo" K2
  [ "$status" -eq 0 ]
  run cat "$rec1"
  [[ "$output" == *"model=m/a"* ]]
  [[ "$output" == *"effort=medium"* ]]
  run cat "$FACTORY_RUNS/r1/K2.result"
  [[ "$output" == *"rung: 1"* ]]
  [[ "$(cat "$FACTORY_RUNS/r1/K2.result")" == *"effort: medium"$'\n'"rung: 1"* ]]

  # K2b (fix suffix) is rung 2 -> m/a high.
  REC="$rec2" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    PATH="$bin:$PATH" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seatcpy/factory-task" r2 "$repo" K2b
  [ "$status" -eq 0 ]
  run cat "$rec2"
  [[ "$output" == *"model=m/a"* ]]
  [[ "$output" == *"effort=high"* ]]
  run cat "$FACTORY_RUNS/r2/K2b.result"
  [[ "$output" == *"rung: 2"* ]]
  [[ "$(cat "$FACTORY_RUNS/r2/K2b.result")" == *"effort: high"$'\n'"rung: 2"* ]]
}

@test "factory-task escalates a rung-3 key: .escalate, exit 4, no run artifacts" {
  seatcpy="$BATS_TEST_TMPDIR/seat"; seat_env "$seatcpy" "$BATS_TEST_TMPDIR/ws-calls"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cp "$BATS_FILE_TMPDIR/rung.toml" "$fx/docs/ledger/routing.toml"
  plan="$BATS_TEST_TMPDIR/plan.md"; write_plan "$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"

  FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    run --separate-stderr "$REAL_BASH" "$seatcpy/factory-task" r3 "$repo" K2r
  [ "$status" -eq 4 ]
  [[ "$output" == "launch: Workflow({"* ]]
  [[ "$output" != *$'\n'* ]]

  esc="$FACTORY_RUNS/r3/K2r.escalate"
  [ -f "$esc" ]
  run cat "$esc"
  [[ "$output" == *"run: r3"* ]]
  [[ "$output" == *"key: K2r"* ]]
  [[ "$output" == *"role: implement"* ]]
  [[ "$output" == *"rung: 3"* ]]
  [[ "$output" == *"escalate: claude/implement"* ]]
  [[ "$output" == *"model: sonnet"* ]]
  [[ "$output" == *"effort: high"* ]]
  [[ "$output" == *"route: implement/code/M"* ]]
  [[ "$output" == *"class: any"* ]]
  [[ "$output" == *"plan: $plan"* ]]
  [[ "$output" == *"launch: Workflow({"* ]]
  [ ! -e "$FACTORY_RUNS/r3/K2r.result" ]
  [ ! -e "$FACTORY_RUNS/r3/K2r.log" ]
  [ ! -e "$FACTORY_RUNS/r3/K2r.pid" ]
  [ ! -e "$BATS_TEST_TMPDIR/ws-calls" ]
}

@test "factory-task --rung overrides the key (explicit) and rejects a bad value" {
  seatcpy="$BATS_TEST_TMPDIR/seat"; seat_env "$seatcpy"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cp "$BATS_FILE_TMPDIR/rung.toml" "$fx/docs/ledger/routing.toml"
  plan="$BATS_TEST_TMPDIR/plan.md"; write_plan "$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'model=%s\\n' "\$2" >> "\$REC"
printf 'effort=%s\\n' "\${OPENROUTER_REASONING_EFFORT:-}" >> "\$REC"
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  rec="$BATS_TEST_TMPDIR/rec"

  # --rung 2 on a bare K2 climbs to rung 2 -> m/a high, recorded explicit.
  REC="$rec" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    PATH="$bin:$PATH" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seatcpy/factory-task" r4 "$repo" K2 --rung 2
  [ "$status" -eq 0 ]
  run cat "$rec"
  [[ "$output" == *"effort=high"* ]]
  run cat "$FACTORY_RUNS/r4/K2.result"
  [[ "$output" == *"rung: 2 (explicit)"* ]]

  # A non-integer --rung is refused before anything runs.
  FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seatcpy/factory-task" r5 "$repo" K2 --rung x
  [ "$status" -eq 2 ]
}

@test "factory-task --fallback chooses the sideways model and records fallback:" {
  seatcpy="$BATS_TEST_TMPDIR/seat"; seat_env "$seatcpy" "$BATS_TEST_TMPDIR/ws-calls"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cp "$BATS_FILE_TMPDIR/rung.toml" "$fx/docs/ledger/routing.toml"
  plan="$BATS_TEST_TMPDIR/plan.md"; write_plan "$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'model=%s\\n' "\$2" >> "\$REC"
printf 'effort=%s\\n' "\${OPENROUTER_REASONING_EFFORT:-}" >> "\$REC"
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  rec="$BATS_TEST_TMPDIR/rec"

  # --fallback on a row carrying fallback=m/f -> m/f (effort still the row's).
  REC="$rec" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    PATH="$bin:$PATH" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seatcpy/factory-task" r6 "$repo" K2 --fallback
  [ "$status" -eq 0 ]
  run cat "$rec"
  [[ "$output" == *"model=m/f"* ]]
  run cat "$FACTORY_RUNS/r6/K2.result"
  [[ "$output" == *"fallback: m/f"* ]]
  [[ "$output" == *"route: implement/code/M"* ]]
  # fallback: sits immediately after class:, before prior: (SD4b's reader spot).
  run grep -A1 '^class:' "$FACTORY_RUNS/r6/K2.result"
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "class: any" ]
  [ "${lines[1]}" = "fallback: m/f" ]

  # Without a fallback row (--rung 2 on K2b has no fallback), --fallback dies 2
  # and writes nothing under the run dir.
  rm -rf "$FACTORY_RUNS/r5"
  REC="$rec" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    PATH="$bin:$PATH" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seatcpy/factory-task" r5 "$repo" K2b --fallback
  [ "$status" -eq 2 ]
  [ ! -e "$FACTORY_RUNS/r5" ]
}

@test "factory-review escalates a rung-2 review: .escalate, exit 4, no gate marker" {
  seatcpy="$BATS_TEST_TMPDIR/seat"; seat_env "$seatcpy" "$BATS_TEST_TMPDIR/ws-calls"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cp "$BATS_FILE_TMPDIR/rung.toml" "$fx/docs/ledger/routing.toml"
  plan="$BATS_TEST_TMPDIR/plan.md"; write_plan "$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  mkdir -p "$BATS_TEST_TMPDIR/ws"

  # K2b is rung 2, but the openrouter review row is rung 1 only -> exhausted.
  FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    run --separate-stderr "$REAL_BASH" "$seatcpy/factory-review" r6 "$repo" K2b
  [ "$status" -eq 4 ]

  esc="$FACTORY_RUNS/r6/K2b.escalate"
  [ -f "$esc" ]
  run cat "$esc"
  [[ "$output" == *"role: review"* ]]
  [[ "$output" == *"escalate: claude/review"* ]]
  [[ "$output" == *"model: opus"* ]]
  [[ "$output" == *"rung: 2"* ]]
  [[ "$output" == *"launch: opus-gate task/K2b ~/factory/ws/r6/K2b"* ]]
  [ ! -e "$FACTORY_RUNS/r6/K2b.review.md" ]
  [ ! -e "$FACTORY_RUNS/r6/K2b.gate" ]
}

@test "factory-wave prints an escalated key and records driver: when SEAT_JOB_ID is set" {
  # A fake factory-task that writes a .escalate (and no .result) and exits 4.
  fbin="$BATS_TEST_TMPDIR/fakebin"; mkdir -p "$fbin"
  cat >"$fbin/factory-task" <<FAKE
#!$REAL_BASH
run=\$1
mkdir -p "\$FACTORY_RUNS/\$run"
{
  printf 'run: %s\\n' "\$run"
  printf 'key: K2r\\n'
  printf 'role: implement\\n'
  printf 'rung: 3\\n'
  printf 'escalate: claude/implement\\n'
  printf 'model: sonnet\\n'
  printf 'effort: high\\n'
} >"\$FACTORY_RUNS/\$run/K2r.escalate"
exit 4
FAKE
  chmod +x "$fbin/factory-task"
  plan="$BATS_TEST_TMPDIR/plan.md"; write_plan "$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"

  # With SEAT_JOB_ID the run.meta carries a driver: line after plan:.
  SEAT_JOB_ID=20260906-120000-abcdef FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r7 "$repo" "K2r"
  [ "$status" -ne 0 ]
  [[ "$output" == *"K2r status=escalated checks=- commits=- minutes=- tokens=- escalate=claude/implement"* ]]
  run cat "$FACTORY_RUNS/r7/run.meta"
  [[ "$output" == *"plan: $plan"* ]]
  [[ "$output" == *"driver: 20260906-120000-abcdef"* ]]
  [[ "$(cat "$FACTORY_RUNS/r7/run.meta")" == *"plan: $plan"$'\n'"driver: 20260906-120000-abcdef"* ]]

  # Without SEAT_JOB_ID there is no driver: line.
  FACTORY_BIN_OVERRIDE="$fbin" FACTORY_PLAN="$plan" \
    run "$REAL_BASH" "$SEAT/factory-wave" r8 "$repo" "K2r"
  [ "$status" -ne 0 ]
  run cat "$FACTORY_RUNS/r8/run.meta"
  [[ "$output" == *"plan: $plan"* ]]
  [[ "$output" != *"driver:"* ]]

  # ritual.sh inflight still reads the run (the extra driver: key is ignored).
  FACTORY_ROOT="$FACTORY_ROOT" run "$REAL_BASH" \
    "$BATS_TEST_DIRNAME/../../tools/ritual.sh" inflight "$repo"
  [ "$status" -eq 0 ]
}

@test "factory-task spools (--no-start --wait) inside a seat unit, not on the host" {
  seatcpy="$BATS_TEST_TMPDIR/seat"; seat_env "$seatcpy"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cp "$BATS_FILE_TMPDIR/rung.toml" "$fx/docs/ledger/routing.toml"
  plan="$BATS_TEST_TMPDIR/plan.md"; write_plan "$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/seat-submit" <<FAKE
#!$REAL_BASH
printf 'args=%s\\n' "\$*" >> "\$REC"
printf '20260906-120000-abcdef\\n'
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/seat-submit"
  rec1="$BATS_TEST_TMPDIR/rec1"; rec2="$BATS_TEST_TMPDIR/rec2"

  # Inside a seat unit (SEAT_JOB_ID set) the submit spools: --no-start --wait.
  REC="$rec1" SEAT_JOB_ID=20260906-120000-abcdef FACTORY_TOOLBOX_REPO="$fx" \
    FACTORY_PLAN="$plan" PATH="$bin:$PATH" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seatcpy/factory-task" r9 "$repo" K2
  [ "$status" -eq 0 ]
  run cat "$rec1"
  [[ "$output" == *"--no-start --wait"* ]]

  # On the host (SEAT_JOB_ID unset) the submit starts: neither flag.
  REC="$rec2" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seatcpy/factory-task" r10 "$repo" K2
  [ "$status" -eq 0 ]
  run cat "$rec2"
  [[ "$output" != *"--no-start"* ]]
  [[ "$output" != *"--wait"* ]]
}

@test "factory-task --model keeps route: explicit and still records rung:" {
  seatcpy="$BATS_TEST_TMPDIR/seat"; seat_env "$seatcpy"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cp "$BATS_FILE_TMPDIR/rung.toml" "$fx/docs/ledger/routing.toml"
  plan="$BATS_TEST_TMPDIR/plan.md"; write_plan "$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'model=%s\\n' "\$2" >> "\$REC"
printf 'effort=%s\\n' "\${OPENROUTER_REASONING_EFFORT:-}" >> "\$REC"
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  rec="$BATS_TEST_TMPDIR/rec"

  # An explicit --model wins over the ladder and is still recorded with the
  # key's rung (K2b -> 2), route: explicit.
  REC="$rec" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    PATH="$bin:$PATH" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seatcpy/factory-task" r9 "$repo" K2b --model m/x
  [ "$status" -eq 0 ]
  run cat "$rec"
  [[ "$output" == *"model=m/x"* ]]
  run cat "$FACTORY_RUNS/r9/K2b.result"
  [[ "$output" == *"route: explicit"* ]]
  [[ "$output" == *"rung: 2"* ]]
}

@test "factory-task exit-3 arm: an unroutable table warns, uses the built-in default, rung:" {
  seatcpy="$BATS_TEST_TMPDIR/seat"; seat_env "$seatcpy"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  # A table that does not parse: an unknown key makes factory_route exit 3.
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/a"
effort = "medium"
bogus = "1"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"; write_plan "$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'model=%s\\n' "\$2" >> "\$REC"
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-CHECKS unit=pass\\n'
printf 'FACTORY-COMMITS 1\\n'
printf 'FACTORY-NOTES ok\\n'
FAKE
  chmod +x "$bin/dsh-openrouter"
  rec="$BATS_TEST_TMPDIR/rec"

  REC="$rec" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run --separate-stderr "$REAL_BASH" "$seatcpy/factory-task" r11 "$repo" K2b
  [ "$status" -eq 0 ]
  [[ "$stderr" == *"warning: routing table unusable"* ]]
  run cat "$rec"
  [[ "$output" == *"model=deepseek/deepseek-v4-pro-0813"* ]]
  run cat "$FACTORY_RUNS/r11/K2b.result"
  [[ "$output" == *"model: deepseek/deepseek-v4-pro-0813"* ]]
  [[ "$output" == *"rung: 2"* ]]
}