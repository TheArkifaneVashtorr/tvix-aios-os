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
  # 1..3, an implement/docs/any rung-1 row with a fallback, a review default,
  # and the two claude rows factory_route_check's second probe needs.
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
  # --class bash-driver reach the class row.
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
class = "bash-driver"
model = "m/c"
effort = "xhigh"
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

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 2 implement code S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-pro-0813 high" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 3 implement code S '$table'"
  [ "$status" -eq 4 ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --rung 3 implement docs S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-pro-0813 medium" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route orchestrate any any '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-pro-0813 medium" ]

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

  # A runbook task stays on the openrouter Flash ladder (rung 1), unchanged:
  # docs-runbook has no claude row, so there is no cross-route escalation.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --class docs-runbook implement docs S '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-flash off" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter implement docs S --class docs-runbook"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-flash off" ]
}

@test "the openrouter-batch route resolves docs-spec/docs-plan-run only when asked, default caller unchanged" {
  table="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
  [ -f "$table" ] || skip "docs/ledger/routing.toml not copied into the unit-check sandbox"

  # Batch is opt-in: --route openrouter-batch resolves the fable batch row for
  # the two unattended drafting classes (the batched counterpart of the FA1
  # rung-3 claude terminus, which stays the operator-watched interactive path).
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route openrouter-batch --class docs-spec implement docs M '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "anthropic/claude-fable-5.1:batch high" ]

  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --route openrouter-batch --class docs-plan-run implement docs M '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "anthropic/claude-fable-5.1:batch high" ]

  # route.py agrees for both classes (parity).
  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter-batch implement docs M --class docs-spec"
  [ "$status" -eq 0 ]
  [ "$output" = "anthropic/claude-fable-5.1:batch high" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter-batch implement docs M --class docs-plan-run"
  [ "$status" -eq 0 ]
  [ "$output" = "anthropic/claude-fable-5.1:batch high" ]

  # A batch row must never capture an interactive call: the default openrouter
  # docs-spec lookup still resolves the docs/any Flash row, not the batch row.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route --class docs-spec implement docs M '$table'"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-flash off" ]

  run "$REAL_BASH" -c "python3 '$route_py' --file '$table' lookup openrouter implement docs M --class docs-spec"
  [ "$status" -eq 0 ]
  [ "$output" = "deepseek/deepseek-v4-flash off" ]
}

@test "an area-specific openrouter row beats a class-any row (area counts in specificity)" {
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
area = "factory"
model = "m/area"
effort = "high"

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