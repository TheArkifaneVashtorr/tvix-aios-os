#!/usr/bin/env bats
# SD2: the technical class derived from touches. factory_task_class (a pure-bash
# line walk over docs/ledger/task-classes.toml plus `case` glob matching)
# classifies a task's touches and must agree with tasks.py's task_class; and
# factory-task passes --class into factory_route and records `class:` in the
# .result. Every driver script runs through "$REAL_BASH", never a shebang.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
EV="$BATS_TEST_DIRNAME/../../pkgs/evidence"

setup_file() {
  bats_require_minimum_version 1.5.0

  # Six sections whose touches are the six classifying rows SD2 pins.
  cat >"$BATS_FILE_TMPDIR/plan.md" <<'EOF'
### C1 (code, S) — majority
**touches:** nixosModules/a.nix, tests/unit/b.bats, tests/unit/c.bats

### C2 (code, S) — tie
**touches:** nixosModules/a.nix, tests/unit/b.bats

### C3 (code, S) — later rule
**touches:** tests/evidence/x.py

### C4 (code, S) — first rule wins
**touches:** tests/unit/x.bats

### C5 (code, S) — no touches

### C6 (code, S) — no match
**touches:** nowhere/x
EOF

  cat >"$BATS_FILE_TMPDIR/rules.toml" <<'EOF'
[[rule]]
class = "nix-module"
glob = "nixosModules/*"

[[rule]]
class = "bats-test"
glob = "tests/unit/*"

[[rule]]
class = "python-evidence"
glob = "tests/*"

[[rule]]
class = "docs-plan"
glob = "docs/superpowers/*"
EOF

  cat >"$BATS_FILE_TMPDIR/malformed.toml" <<'EOF'
[[rule]]
class = "typo"
glob = "x/*"
EOF
}

setup() {
  REAL_BASH="$(command -v bash)"
  # factory_task_touches (which factory_task_class builds on) runs tasks.py
  # through factory_py -- the toolbox repo plus a real python (the unit-check
  # sandbox has no devShell, so FACTORY_PYTHON3_CMD names its python3).
  export FACTORY_TOOLBOX_REPO="$BATS_TEST_DIRNAME/../.."
  export FACTORY_PYTHON3_CMD="$(command -v python3)"
}

@test "factory_task_class prints the six classifying answers" {
  plan="$BATS_FILE_TMPDIR/plan.md"
  rules="$BATS_FILE_TMPDIR/rules.toml"
  local pair key ans
  for pair in "C1 bats-test" "C2 nix-module" "C3 python-evidence" "C4 bats-test" "C5 any" "C6 any"; do
    key=${pair%% *}
    ans=${pair##* }
    run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_class '$plan' '$key' '$rules'"
    [ "$status" -eq 0 ]
    [ "$output" = "$ans" ]
  done
}

@test "factory_task_class degrades a malformed rules table to any with a warning" {
  plan="$BATS_FILE_TMPDIR/plan.md"
  run --separate-stderr "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_class '$plan' C1 '$BATS_FILE_TMPDIR/malformed.toml'"
  [ "$status" -eq 0 ]
  [ "$output" = "any" ]
  [[ "$stderr" == *"factory_task_class: $BATS_FILE_TMPDIR/malformed.toml: rule 1: unknown class typo"* ]]
}

@test "factory_task_class yields any for a missing rules file, section, or plan" {
  plan="$BATS_FILE_TMPDIR/plan.md"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_class '$plan' C1 '$BATS_FILE_TMPDIR/nope.toml'"
  [ "$status" -eq 0 ]
  [ "$output" = "any" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_class '$plan' NOSUCH '$BATS_FILE_TMPDIR/rules.toml'"
  [ "$status" -eq 0 ]
  [ "$output" = "any" ]
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_class '$BATS_FILE_TMPDIR/noplan.md' C1 '$BATS_FILE_TMPDIR/rules.toml'"
  [ "$status" -eq 0 ]
  [ "$output" = "any" ]
}

@test "factory_task_class agrees with tasks.py task_class on every section" {
  plan="$BATS_FILE_TMPDIR/plan.md"
  rules="$BATS_FILE_TMPDIR/rules.toml"
  cat >"$BATS_TEST_TMPDIR/pyclass" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import tasks
rules = tasks.load_class_rules(sys.argv[2])[0]
plan = tasks.parse_plan(sys.argv[3])
key = sys.argv[4]
touches = next(t["touches"] for t in plan["tasks"] if t["key"] == key)
print(tasks.task_class(touches, rules))
PY
  local key bash_cls py_cls
  for key in C1 C2 C3 C4 C5 C6; do
    bash_cls=$("$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_class '$plan' '$key' '$rules'")
    py_cls=$(python3 "$BATS_TEST_TMPDIR/pyclass" "$EV" "$rules" "$plan" "$key")
    [ "$bash_cls" = "$py_cls" ]
  done
}

@test "factory-task passes --class into factory_route and records class: in the .result" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  # The copied scripts keep their `#!/usr/bin/env bash` shebang, which the
  # build sandbox has no /usr/bin/env to honour; factory-task invokes
  # factory-brief by that shebang, so repoint it to the sandbox bash.
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  # factory-ws prints a workspace path and succeeds, so factory-task runs to
  # completion and writes the .result file.
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  # The toolbox holds the routing table (one class-carrying row) and the
  # task-classes rules (the task's touch classifies to bats-test).
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger" "$fx/pkgs/evidence"
  cp "$EV"/*.py "$fx/pkgs/evidence/"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]
role = "implement"
kind = "any"
size = "any"
class = "bats-test"
model = "m/x"
effort = "xhigh"
EOF
  cat >"$fx/docs/ledger/task-classes.toml" <<'EOF'
[[rule]]
class = "bats-test"
glob = "tests/unit/*"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

**touches:** tests/unit/x.bats
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  # A fake dsh-openrouter records the --model argument.
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
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  rec="$BATS_TEST_TMPDIR/rec"

  REC="$rec" FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= FACTORY_SEAT_UNIT=0 \
    run "$REAL_BASH" "$seat_copy/factory-task" r1 "$repo" K1
  [ "$status" -eq 0 ]
  run cat "$rec"
  # The class-specific row (m/x) beat the plain default -- the class reached
  # the lookup rather than being dropped.
  [[ "$output" == *"model=m/x"* ]]
  run cat "$root/runs/r1/K1.result"
  [[ "$output" == *"class: bats-test"* ]]
  [[ "$output" == *"model: m/x"* ]]
  [[ "$output" == *"route: implement/docs/XS"* ]]
}

@test "the committed rules put docs-spec and docs-plan-run first; a runbook stays docs-runbook" {
  plan="$BATS_TEST_TMPDIR/classplan.md"
  cat >"$plan" <<'EOF'
### S1 (docs, S) — spec
**touches:** docs/superpowers/specs/x.md

### S2 (docs, S) — plan-judgement
**touches:** docs/reviews/plan-judgements/x.md

### S3 (docs, S) — runbook
**touches:** docs/runbooks/x.md
EOF
  rules="$FACTORY_TOOLBOX_REPO/docs/ledger/task-classes.toml"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_class '$plan' S1 '$rules'"
  [ "$status" -eq 0 ]
  [ "$output" = "docs-spec" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_class '$plan' S2 '$rules'"
  [ "$output" = "docs-plan-run" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_task_class '$plan' S3 '$rules'"
  [ "$output" = "docs-runbook" ]
}