#!/usr/bin/env bats
# SD1: the routing table carries ladders. A [[route]] row gains three optional
# keys -- `class` (the technical class, default "any"), `rung` (a positive
# integer, default 1) and `fallback` (a sideways model id) -- and the lookup
# gains --rung/--class/--fallback plus exit 4 on exhaustion. The bash
# factory_route (tools/factory/seat/factory-lib.sh) and the python route.py
# (tools/factory/route.py) must agree, exactly as 80-seat-driver.bats pins the
# plain lookup. Every driver script runs through "$REAL_BASH", never a shebang.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup_file() {
  bats_require_minimum_version 1.5.0

  # The base ladder fixture: an openrouter implement/code/any ladder with rungs
  # 1..3, an implement/docs/any rung-1 row with a fallback plus its own rung 2
  # (route.py's rung-2-required-for-implement rule, 2026-09-21 fix, refuses
  # any implement key with a rung 1 and no rung 2), a review default, and the
  # two claude rows factory_route_check's second probe needs.
  cat >"$BATS_FILE_TMPDIR/ladder.toml" <<'EOF'
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
kind = "code"
size = "any"
rung = 3
model = "m/b"
effort = "high"

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
model = "m/f"
effort = "off"
fallback = "m/a"

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
rung = 2
model = "m/f"
effort = "medium"

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
role = "review"
kind = "code"
size = "any"
model = "opus"
effort = "high"
EOF

  # The class fixture: the class row sits AFTER the plain row, so row order
  # alone would pick the plain one -- only counting class in specificity makes
  # --class bash-driver reach the class row. Both implement/code keys (plain
  # and class="bash-driver") carry their own rung 2, per route.py's
  # rung-2-required-for-implement rule (2026-09-21 fix).
  cat >"$BATS_FILE_TMPDIR/class.toml" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/default"
effort = "low"

[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
model = "m/a"
effort = "medium"

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
kind = "code"
size = "any"
class = "bash-driver"
model = "m/c"
effort = "xhigh"

[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
class = "bash-driver"
rung = 2
model = "m/c"
effort = "high"
EOF

  # The reversed ladder: the implement/code/any rung-2 row is written BEFORE its
  # rung-1 row, so the "earliest row wins" tie rule alone would pick the rung-2
  # row -- only the rung-1 filter keeps the default lookup on m/a medium.
  cat >"$BATS_FILE_TMPDIR/ladder-reversed.toml" <<'EOF'
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
rung = 2
model = "m/a"
effort = "high"

[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
model = "m/a"
effort = "medium"
EOF

  # The class-carrying default: the route's only any/any/any row carries a
  # class, so it is NOT the default row -- both readers must refuse it.
  cat >"$BATS_FILE_TMPDIR/ladder-classdefault.toml" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
class = "bash-driver"
model = "m/d"
effort = "low"
EOF
}

setup() {
  REAL_BASH="$(command -v bash)"
  route_py="$SEAT/../route.py"
}

@test "factory_route and route.py climb the implement/code ladder and exit 4 at exhaustion" {
  ladder="$BATS_FILE_TMPDIR/ladder.toml"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 2 implement code S '$ladder'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/a high" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 3 implement code S '$ladder'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/b high" ]

  run --separate-stderr "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 4 implement code S '$ladder'"
  [ "$status" -eq 4 ]
  [ "$output" = "" ]
  [[ "$stderr" == *"ladder exhausted at rung 4 for openrouter/implement/code/any/any/any"* ]]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$ladder' lookup openrouter implement code S --rung 2"
  [ "$status" -eq 0 ]
  [ "$output" = "m/a high" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$ladder' lookup openrouter implement code S --rung 4"
  [ "$status" -eq 4 ]
  [[ "$output" == *"route.py: ladder exhausted at rung 4 for openrouter/implement/code/any/any/any"* ]]
}

@test "the default lookup is unchanged: rung 1 wins by specificity, not by rung" {
  ladder="$BATS_FILE_TMPDIR/ladder.toml"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement code S '$ladder'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/a medium" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route any any any '$ladder'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/d low" ]
}

@test "--fallback prints the winning row's fallback and effort, exit 4 without one" {
  ladder="$BATS_FILE_TMPDIR/ladder.toml"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --fallback implement docs S '$ladder'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/a off" ]

  run --separate-stderr "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --fallback implement code S '$ladder'"
  [ "$status" -eq 4 ]
  [ "$output" = "" ]
  [[ "$stderr" == *"no fallback at rung 1 for openrouter/implement/code/any/any/any"* ]]

  run --separate-stderr "$REAL_BASH" -c "python3 '$route_py' --file '$ladder' lookup openrouter implement code S --fallback"
  [ "$status" -eq 4 ]
  [ "$output" = "" ]
  [[ "$stderr" == *"no fallback at rung 1 for openrouter/implement/code/any/any/any"* ]]
}

@test "factory_route_check and route.py check accept the ladder fixture" {
  ladder="$BATS_FILE_TMPDIR/ladder.toml"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$ladder'"
  [ "$status" -eq 0 ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$ladder' check"
  [ "$status" -eq 0 ]
}

@test "both implementations refuse each ladder violation (one edit per fixture)" {
  ladder="$BATS_FILE_TMPDIR/ladder.toml"

  # duplicate rung: a second rung-2 row for implement/code/any.
  f="$BATS_TEST_TMPDIR/dup.toml"
  cp "$ladder" "$f"
  sed -i 's/^rung = 3$/rung = 2/' "$f"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$f'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"ladder openrouter/implement/code/any/any/any: rung 2 twice"* ]]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"rung 2 twice"* ]]

  # gap: rung 3 present, rung 2 absent (renumber the rung-2 row out of the way).
  f="$BATS_TEST_TMPDIR/gap.toml"
  cp "$ladder" "$f"
  sed -i 's/^rung = 2$/rung = 4/' "$f"
  run --separate-stderr "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$f'"
  [ "$status" -eq 3 ]
  [[ "$stderr" == *"rung 3 without rung 2"* ]]
  [[ "$stderr" != *"for its key"* ]]
  run --separate-stderr "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$stderr" == *"rung 3 without rung 2"* ]]
  [[ "$stderr" != *"for its key"* ]]

  # unreachable: a key with a rung 2 and no rung-1 row (implement/code/S).
  f="$BATS_TEST_TMPDIR/unreachable.toml"
  cp "$ladder" "$f"
  cat >>"$f" <<'EOF'
[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "S"
rung = 2
model = "m/z"
effort = "high"
EOF
  run --separate-stderr "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$f'"
  [ "$status" -eq 3 ]
  [[ "$stderr" == *"rung 2 without rung 1 for its key"* ]]
  run --separate-stderr "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$stderr" == *"rung 2 without rung 1 for its key"* ]]

  # two-variable: rung 2 changes model AND effort from rung 1.
  f="$BATS_TEST_TMPDIR/two-var.toml"
  cat >"$f" <<'EOF'
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

[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
rung = 2
model = "m/b"
effort = "low"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$f'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"rungs 1→2 change model and effort"* ]]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"rungs 1→2 change model and effort"* ]]

  # zero-variable (GLM1b, gate rejection 2026-09-19): rung 2 changes NEITHER
  # model nor effort from rung 1 -- a degenerate climb a fix round could
  # relaunch forever with no different outcome. This is the defect that
  # shipped in implement/code before the gate caught it: a byte-identical
  # rung 1/rung 2 row passed both checks silently because they only refused
  # a step changing BOTH fields, never a step changing neither.
  f="$BATS_TEST_TMPDIR/zero-var.toml"
  cat >"$f" <<'EOF'
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
effort = "high"

[[route]]
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
rung = 2
model = "m/a"
effort = "high"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$f'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"rungs 1→2 change neither model nor effort"* ]]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"rungs 1→2 change neither model nor effort"* ]]

  # fallback naming a model with no row on its route.
  f="$BATS_TEST_TMPDIR/fallback.toml"
  cp "$ladder" "$f"
  sed -i 's/fallback = "m\/a"/fallback = "m\/zzz"/' "$f"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$f'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"fallback m/zzz has no row of its own"* ]]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"fallback m/zzz has no row of its own"* ]]

  # class outside the vocabulary.
  f="$BATS_TEST_TMPDIR/class-typo.toml"
  cp "$ladder" "$f"
  cat >>"$f" <<'EOF'
[[route]]
route = "openrouter"
role = "review"
kind = "docs"
size = "any"
class = "typo"
model = "m/x"
effort = "medium"
EOF
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$f'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"unknown class"* ]]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"unknown class"* ]]

  # rung below 1 and a non-integer rung are both a bad rung.
  f="$BATS_TEST_TMPDIR/rung-zero.toml"
  cp "$ladder" "$f"
  sed -i 's/^rung = 2$/rung = 0/' "$f"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$f'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"bad rung"* ]]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"bad rung"* ]]

  f="$BATS_TEST_TMPDIR/rung-x.toml"
  cp "$ladder" "$f"
  sed -i 's/^rung = 2$/rung = x/' "$f"
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$f'"
  [ "$status" -eq 3 ]
  [[ "$output" == *"bad rung"* ]]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"bad rung"* ]]
}

@test "a requested class matches its own row, and any never matches a class row" {
  classfx="$BATS_FILE_TMPDIR/class.toml"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --class bash-driver implement code S '$classfx'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/c xhigh" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement code S '$classfx'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/a medium" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --class docs-plan implement code S '$classfx'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/a medium" ]
}

@test "factory_route and route.py agree across rungs, class, fallback and claude (seven-tuple pattern)" {
  ladder="$BATS_FILE_TMPDIR/ladder.toml"
  classfx="$BATS_FILE_TMPDIR/class.toml"

  for r in 1 2 3 4; do
    run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung '$r' implement code S '$ladder'"
    bs=$status
    b=$output
    run "$REAL_BASH" -c "python3 '$route_py' --file '$ladder' lookup openrouter implement code S --rung '$r'"
    ps=$status
    p=$output
    [ "$bs" -eq "$ps" ]
    if [ "$bs" -eq 0 ]; then
      [ "$b" = "$p" ]
    else
      [ "$bs" -eq 4 ]
    fi
  done

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --class bash-driver implement code S '$classfx'"
  b=$output
  run "$REAL_BASH" -c "python3 '$route_py' --file '$classfx' lookup openrouter implement code S --class bash-driver"
  p=$output
  [ "$b" = "$p" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --fallback implement docs S '$ladder'"
  b=$output
  run "$REAL_BASH" -c "python3 '$route_py' --file '$ladder' lookup openrouter implement docs S --fallback"
  p=$output
  [ "$b" = "$p" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route claude review code S '$ladder'"
  b=$output
  run "$REAL_BASH" -c "python3 '$route_py' --file '$ladder' lookup claude review code S"
  p=$output
  [ "$b" = "$p" ]
}

@test "the committed table carries the first rungs and both checks accept it" {
  table="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
  [ -f "$table" ] || skip "docs/ledger/routing.toml not copied into the unit-check sandbox"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$table'"
  [ "$status" -eq 0 ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' check"
  [ "$status" -eq 0 ]

  # implement/code carries a rung 2 (GLM2, 2026-09-21, reverses GLM1b): the
  # resolved row itself is proved by "implement/code rung 2 resolves instead
  # of exhausting" below; rung 3 still doesn't exist for this key.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 2 implement code S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 xhigh" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 3 implement code S '$table'"
  [ "$status" -eq 4 ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 3 implement docs S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 high" ]

  # GLM2b (operator decision, docs/decisions/2026-09-21-routing-ladder-rung2.md):
  # implement/docs and implement/any/XS both climb flash "medium" -> glm
  # "medium" -> glm "high", one field per rung. Rung 1 was "off" before this
  # decision (GLM1's LEAVE ALONE); rung 2 is the measured repair
  # configuration -- PG3b and PG4b ran glm-5.3 "medium" and were
  # Opus-approved (docs/board/log-2026-09.md).
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 1 implement docs S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-flash medium" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 2 implement docs S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 medium" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 1 implement any XS '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-flash medium" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 2 implement any XS '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 medium" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 3 implement any XS '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 high" ]

  # GLM2b MINOR: an "implement any any" dispatch falls through to the
  # openrouter default row (no implement row carries both kind="any" and
  # size="any"), which now carries its own rung 2, same one-field shape as
  # implement/code (model held, effort escalates).
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 1 implement any any '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 high" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 2 implement any any '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 xhigh" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route orchestrate any any '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 high" ]

  # The orchestrate row's model and effort equal the default row's, so no
  # lookup can see it; pin its presence through the parser.
  run "$REAL_BASH" -c "python3 -c 'import sys, tomllib; rows = tomllib.load(open(sys.argv[1], \"rb\"))[\"route\"]; ok = any(r.get(\"route\", \"openrouter\") == \"openrouter\" and r[\"role\"] == \"orchestrate\" and r.get(\"kind\", \"any\") == \"any\" and r.get(\"size\", \"any\") == \"any\" and r.get(\"rung\", 1) == 1 for r in rows); sys.exit(0 if ok else 1)' '$table'"
  [ "$status" -eq 0 ]

  # The seven tuples 80-seat-driver.bats pins must still agree on the table.
  while read -r route role kind size; do
    [ -n "$route" ] || continue
    run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route '$route' '$role' '$kind' '$size' '$table'"
    a=$output
    run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup '$route' '$role' '$kind' '$size'"
    b=$output
    [ "$a" = "$b" ]
  done <<'EOF'
claude review code S
claude review docs XS
claude implement code M
claude verify code L
claude audit any any
openrouter implement docs XS
openrouter review code S
EOF
}

@test "implement/code rung 2 resolves instead of exhausting (GLM2 fix, decision 2026-09-21, reverses GLM1b)" {
  # GLM1 (2026-09-19) collapsed implement/code rung 1 and rung 2 to the same
  # z-ai/glm-5.3 high row -- a fix round would have relaunched the identical
  # configuration. GLM1b (fix round, 2026-09-19) deleted the rung-2 row
  # outright so a --rung 2 request hits the ordinary "ladder exhausted" path
  # (factory-lib.sh's rung climb, not the FA1 class-scoped-claude-row
  # terminus) and factory-task's exit-4/.escalate handling takes it from
  # there, exactly as it already does for any key with no ladder past rung 1.
  # The actual effect, measured 2026-09-21 landing the publish-gate plan
  # (docs/board/log-2026-09.md, the "THE PUBLISH GATE LANDED" entry): a fix
  # round -- which defaults to the prior rung + 1 -- exhausts on its very
  # first retry (~/factory/runs/pgw2/PG2b.escalate) and the driver escalates
  # to the plan graph as though the plan itself were wrong, not as though the
  # model config needed a second try. GLM2's fix (2026-09-21, this commit): a
  # real rung 2 -- the same model at a higher effort, one field changed per
  # check_ladders' rule (tools/factory/route.py:198-206) -- so a fix round
  # gets a genuinely different configuration instead of an immediate
  # escalation. Rung 3 still does not exist for this key: a *second* fix
  # round still escalates to the plan graph, which is the intended terminus.
  table="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
  [ -f "$table" ] || skip "docs/ledger/routing.toml not copied into the unit-check sandbox"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 1 implement code S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 high" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 2 implement code S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 xhigh" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter implement code S --rung 2"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 xhigh" ]

  run --separate-stderr "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 3 implement code S '$table'"
  [ "$status" -eq 4 ]
  [ "$output" = "" ]
  [[ "$stderr" == *"ladder exhausted at rung 3 for openrouter/implement/code/any/any/any"* ]]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter implement code S --rung 3"
  [ "$status" -eq 4 ]
  [[ "$output" == *"route.py: ladder exhausted at rung 3 for openrouter/implement/code/any/any/any"* ]]
}

@test "the docs-spec/docs-plan-run claude rung-3 terminus escalates (4) and docs-runbook stays on Flash" {
  table="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
  [ -f "$table" ] || skip "docs/ledger/routing.toml not copied into the unit-check sandbox"

  # The operator terminus: rung 3 on docs-spec resolves the claude fable row
  # and escalates (exit 4, the row printed) instead of the openrouter docs/any
  # rung-3 row (pro medium, exit 0).
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 3 --class docs-spec implement docs M '$table'"
  [ "$status" -eq 4 ]
  [ "$output" = "fable high" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 3 --class docs-plan-run implement docs M '$table'"
  [ "$status" -eq 4 ]
  [ "$output" = "fable high" ]

  # route.py agrees for both new classes (parity).
  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter implement docs M --class docs-spec --rung 3"
  [ "$status" -eq 4 ]
  [ "$output" = "fable high" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter implement docs M --class docs-plan-run --rung 3"
  [ "$status" -eq 4 ]
  [ "$output" = "fable high" ]

  # A runbook task stays on the openrouter Flash ladder (rung 1): docs-runbook
  # has no claude row, so there is no cross-route escalation. Effort is
  # "medium" per GLM2b (docs/decisions/2026-09-21-routing-ladder-rung2.md,
  # rung 1 was "off" before that decision).
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --class docs-runbook implement docs S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-flash medium" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter implement docs S --class docs-runbook"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-flash medium" ]
}

@test "the openrouter-batch route resolves docs-spec/docs-plan-run only when asked, default caller unchanged" {
  table="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
  [ -f "$table" ] || skip "docs/ledger/routing.toml not copied into the unit-check sandbox"

  # Batch is opt-in: --route openrouter-batch resolves the glm batch row for
  # the two unattended drafting classes (the batched counterpart of the FA1
  # rung-3 claude terminus, which stays the operator-watched interactive path).
  # The batch model is z-ai/glm-5.3:batch since e37737b2 (2026-09-23, operator's
  # call: glm-5.3 batch is a tenth of Fable batch's output price with more
  # context); this test's four assertions still read fable and were red from
  # that commit until FA32 fixed them.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route openrouter-batch --class docs-spec implement docs M '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3:batch high" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route openrouter-batch --class docs-plan-run implement docs M '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3:batch high" ]

  # route.py agrees for both classes (parity).
  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter-batch implement docs M --class docs-spec"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3:batch high" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter-batch implement docs M --class docs-plan-run"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3:batch high" ]

  # A batch row must never capture an interactive call: the default openrouter
  # docs-spec lookup resolves FA32's plain drafting row (z-ai/glm-5.3, not the
  # Flash ladder it fell through to before FA32 and not the batch row).
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --class docs-spec implement docs M '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 high" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter implement docs M --class docs-spec"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3 high" ]
}

@test "an area-specific openrouter row beats a class-any row (area counts in specificity)" {
  # Both implement/docs keys (area="any" and area="factory") carry their own
  # rung 2, per route.py's rung-2-required-for-implement rule (2026-09-21 fix).
  area="$BATS_TEST_TMPDIR/area.toml"
  cat >"$area" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/default"
effort = "low"

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
model = "m/classany"
effort = "medium"

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
rung = 2
model = "m/classany"
effort = "high"

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
area = "factory"
model = "m/area"
effort = "high"

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
area = "factory"
rung = 2
model = "m/area"
effort = "xhigh"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
EOF

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement docs M '$area'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/area high" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$area' lookup openrouter implement docs M"
  [ "$status" -eq 0 ]
  [ "$output" = "m/area high" ]
}

@test "the rung-1 filter holds when the rung-2 row is written first (reversed fixture)" {
  rev="$BATS_FILE_TMPDIR/ladder-reversed.toml"

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement code S '$rev'"
  [ "$status" -eq 0 ]
  [ "$output" = "m/a medium" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$rev' lookup openrouter implement code S"
  [ "$status" -eq 0 ]
  [ "$output" = "m/a medium" ]
}

@test "a class-carrying default row is refused: no default (any/any/any) row" {
  cd="$BATS_FILE_TMPDIR/ladder-classdefault.toml"

  run --separate-stderr "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route_check '$cd'"
  [ "$status" -eq 3 ]
  [[ "$stderr" == *"no default (any/any/any) row"* ]]

  run --separate-stderr "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route implement code S '$cd'"
  [ "$status" -eq 3 ]
  [ "$output" = "" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$cd' check"
  [ "$status" -eq 1 ]

  run --separate-stderr "$REAL_BASH" -c "python3 '$route_py' --file '$cd' lookup openrouter implement code S"
  [ "$status" -eq 1 ]
  [ "$output" = "" ]
  [[ "$stderr" == *"no default (any/any/any) row"* ]]
  [[ "$stderr" != *"Traceback"* ]]
}

@test "route.py check refuses a reasoning-mandatory model paired with effort off (2026-09-21 fix)" {
  # Measured landing the publish-gate plan 2026-09-21 (docs/board/log-2026-09.md,
  # the "THE PUBLISH GATE LANDED" entry): the implement/docs rung-2 row then in
  # the committed table paired z-ai/glm-5.3 with effort "off" -- OpenRouter
  # answers HTTP 400 "Reasoning is mandatory for this endpoint and cannot be
  # disabled" and the seat died in two seconds (evidence:
  # /var/lib/seat/jobs/20260921-112923-a7859a/stderr.txt,
  # ~/factory/runs/pgw1b/PG3b.result). This fixture reproduces that shape --
  # the committed table itself has moved on (GLM2b) -- to prove
  # route.py's validator still refuses it for any openrouter row, driven by
  # its REASONING_MANDATORY_MODELS table -- data, not a special case for this
  # one row. route.py only: factory-lib.sh's factory_route_check does not
  # carry this rule (the fix's stated scope).
  f="$BATS_TEST_TMPDIR/reasoning-off.toml"
  cat >"$f" <<'EOF'
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
kind = "docs"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"

[[route]]
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
rung = 2
model = "z-ai/glm-5.3"
effort = "off"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
EOF

  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"z-ai/glm-5.3"* ]]
  [[ "$output" == *"reasoning"* ]]
  [[ "$output" != *"Traceback"* ]]
}

@test "route.py check requires an implement key with a rung 1 to also carry a rung 2 (2026-09-21 fix)" {
  # Measured landing the publish-gate plan 2026-09-21 (docs/board/log-2026-09.md):
  # GLM1b (2026-09-19) deleted the implement/code rung-2 row outright so a
  # byte-identical rung climb couldn't relaunch forever; the actual effect is
  # that a fix round -- which defaults to the prior rung + 1 -- exhausts on
  # its very first retry ("ladder exhausted at rung 2 for
  # openrouter/implement/code/any/any/any", ~/factory/runs/pgw2/PG2b.escalate)
  # and the driver escalates to the plan graph as though the plan were wrong,
  # not as though the model config needed a second try. route.py's validator
  # now refuses any openrouter implement key that has a rung 1 and no rung 2.
  # route.py only, matching the reasoning-mandatory rule's scope above.
  f="$BATS_TEST_TMPDIR/no-rung2.toml"
  cat >"$f" <<'EOF'
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
model = "z-ai/glm-5.3"
effort = "high"

[[route]]
route = "claude"
role = "any"
kind = "any"
size = "any"
model = "sonnet"
effort = "medium"
EOF

  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' check"
  [ "$status" -eq 1 ]
  [[ "$output" == *"implement/code"* ]]
}
@test "the FA32 variant axis changes nothing that does not ask for it (pre-existing resolutions, value for value)" {
  # FA32 Interface 7: every role that existed before the task resolves to the
  # same model and effort afterwards, through BOTH readers (bash factory_route
  # and route.py), compared value for value against the measured pre-change
  # resolutions -- the guard that keeps a new routing axis from quietly
  # re-pointing the seat ladder. review/docs is the sharpest row: the three
  # judge rows (review/docs, variant a/b/c) must never capture a plain call,
  # so a variant match implemented the area way (any variant row captures any
  # request) or a discarded variant filter fails here with qwen/kimi/grok in
  # the output.
  table="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
  [ -f "$table" ] || skip "docs/ledger/routing.toml not copied into the unit-check sandbox"

  pin_one() { # $1 route, $2 role, $3 kind, $4 size, $5 rung, $6 class, $7 expected
    run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route '$1' --rung '$5' --class '$6' '$2' '$3' '$4' '$table'"
    [ "$status" -eq 0 ]
    [ "$output" = "$7" ]
    run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup '$1' '$2' '$3' '$4' --rung '$5' --class '$6'"
    [ "$status" -eq 0 ]
    [ "$output" = "$7" ]
  }

  pin_one openrouter implement code S 1 any "z-ai/glm-5.3 high"
  pin_one openrouter implement code S 2 any "z-ai/glm-5.3 xhigh"
  pin_one openrouter implement docs S 1 any "deepseek/deepseek-v4-flash medium"
  pin_one openrouter implement docs S 2 any "z-ai/glm-5.3 medium"
  pin_one openrouter implement docs S 3 any "z-ai/glm-5.3 high"
  pin_one openrouter implement any XS 1 any "deepseek/deepseek-v4-flash medium"
  pin_one openrouter implement any XS 2 any "z-ai/glm-5.3 medium"
  pin_one openrouter implement any XS 3 any "z-ai/glm-5.3 high"
  pin_one openrouter implement any any 1 any "z-ai/glm-5.3 high"
  pin_one openrouter implement any any 2 any "z-ai/glm-5.3 xhigh"
  pin_one openrouter review any any 1 any "z-ai/glm-5.3 high"
  pin_one openrouter review docs any 1 any "z-ai/glm-5.3 high"
  pin_one openrouter review code any 1 any "z-ai/glm-5.3 high"
  pin_one openrouter orchestrate any any 1 any "z-ai/glm-5.3 high"
  pin_one openrouter verify any any 1 any "z-ai/glm-5.3 high"
  pin_one openrouter-batch implement docs M 1 docs-spec "z-ai/glm-5.3:batch high"

  # The same axis, asked for: variant is the LEAST-specific discriminator, so
  # a specific any-variant row beats a vague variant row for a
  # variant-carrying request (spec (1,0) > (0,1)); a mutant ordering variant
  # above class flips this lookup. bash factory_route never asks for a variant,
  # so this pin is route.py's alone.
  T="$(mktemp -d)"
  f="$T/fa32-order.toml"
  cat >"$f" <<'TOMLEOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/default"
effort = "low"

[[route]]
route = "openrouter"
role = "review"
kind = "any"
size = "any"
model = "m/specific"
effort = "low"

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
variant = "a"
model = "m/vague"
effort = "low"
TOMLEOF
  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' lookup openrouter review docs any --variant a"
  [ "$status" -eq 0 ]
  [ "$output" = "m/specific low" ]
  run "$REAL_BASH" -c "python3 '$route_py' --file '$f' lookup openrouter any any any --variant a"
  [ "$status" -eq 0 ]
  [ "$output" = "m/vague low" ]
}
