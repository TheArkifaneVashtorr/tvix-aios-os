#!/usr/bin/env bats
# FA18: the mechanical re-resolver node. factory-reresolve.py re-runs every
# claim's citation (path:line or path:A-B within `wc -l`) and command
# (subprocess.run, exit 0) in a sandbox repo, then writes a `reresolve`
# artifact whose errata are one entry per claim -- `held:<i>` when both hold,
# or `broken:<i>: <reason>`. No model, no network: the script's imports are
# stdlib only. The script lives in tools/factory/seat and is invoked with
# python3, so a missing script reads python's "can't open file" (the documented
# red signal).

setup() {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  ART="$SEAT/factory-artifact.py"
  RR="$SEAT/factory-reresolve.py"
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO"
  cat >"$REPO/f.sh" <<'EOF'
#!/bin/sh
echo hello
echo goodbye
EOF
  IN="$BATS_TEST_TMPDIR/in.json"
  OUT="$BATS_TEST_TMPDIR/out.json"
}

# make_input TEXT COMMAND CITATION [VERDICT] -> writes a one-claim artifact to $IN.
make_input() {
  local verdict="${4:-ok}"
  python3 "$ART" write input --key r1 --node n1 --rung 1 \
    --claim "$1::$2::$3" --verdict "$verdict" >"$IN"
}

# --- (a) a claim that reproduces holds --------------------------------

@test "(a) a citation and command that reproduce hold" {
  make_input 'f.sh says `echo hello`' 'grep -q hello f.sh' 'f.sh:2'
  run python3 "$RR" "$IN" --repo "$REPO" --out "$OUT"
  [ "$status" -eq 0 ]
  [ "$(python3 "$ART" get "$OUT" verdict)" = '"ok"' ]
  [ "$(python3 "$ART" get "$OUT" errata)" = '["held:0"]' ]
}

# --- (b) a citation line beyond the file length ---------------------------------

@test "(b) a citation line past the file length is a line out of range" {
  make_input 'is there a line nine' 'true' 'f.sh:9'
  run python3 "$RR" "$IN" --repo "$REPO" --out "$OUT"
  [ "$status" -eq 0 ]
  [ "$(python3 "$ART" get "$OUT" verdict)" = '"broken"' ]
  [ "$(python3 "$ART" get "$OUT" errata)" = '["broken:0: line out of range"]' ]
}

# --- (c) a citation naming a missing file -------------------------------------

@test "(c) a citation naming a missing file is a missing file" {
  make_input 'g.sh exists' 'true' 'g.sh:1'
  run python3 "$RR" "$IN" --repo "$REPO" --out "$OUT"
  [ "$status" -eq 0 ]
  [ "$(python3 "$ART" get "$OUT" verdict)" = '"broken"' ]
  [ "$(python3 "$ART" get "$OUT" errata)" = '["broken:0: missing file"]' ]
}

# --- (d) a command that exits nonzero

@test "(d) a command that exits nonzero is a command exit" {
  make_input 'false exits' 'false' 'f.sh:1'
  run python3 "$RR" "$IN" --repo "$REPO" --out "$OUT"
  [ "$status" -eq 0 ]
  [ "$(python3 "$ART" get "$OUT" verdict)" = '"broken"' ]
  [ "$(python3 "$ART" get "$OUT" errata)" = '["broken:0: command exit 1"]' ]
}

# --- (e) the literal sits on the cited line, not just anywhere

@test "(e) a literal absent from the cited range is literal not on cited line" {
  make_input 'f.sh says `echo hello`' 'true' 'f.sh:1'
  run python3 "$RR" "$IN" --repo "$REPO" --out "$OUT"
  [ "$status" -eq 0 ]
  [ "$(python3 "$ART" get "$OUT" verdict)" = '"broken"' ]
  [ "$(python3 "$ART" get "$OUT" errata)" = '["broken:0: literal not on cited line"]' ]
}

# --- (f) a per-command timeout marks the claim broken:timeout

@test "(f) a claim whose command outlives --timeout is a timeout" {
  make_input 'sleeps long' 'sleep 5' 'f.sh:1'
  local start=$SECONDS
  run python3 "$RR" "$IN" --repo "$REPO" --out "$OUT" --timeout 1
  local elapsed=$((SECONDS - start))
  [ "$status" -eq 0 ]
  [ "$elapsed" -lt 3 ]
  [ "$(python3 "$ART" get "$OUT" verdict)" = '"broken"' ]
  [ "$(python3 "$ART" get "$OUT" errata)" = '["broken:0: timeout"]' ]
}

# --- (g) an artifact the checker refuses is refused, not rewritten

@test "(g) an artifact with a bad verdict is refused with exit 2" {
  cat >"$IN" <<'EOF'
{
  "kind": "input",
  "key": "r1",
  "node": "n1",
  "rung": 1,
  "claims": [{"text": "x", "command": "true", "citation": "f.sh:1"}],
  "repro": null,
  "errata": [],
  "verdict": "maybe",
  "inputs": {},
  "scores": null,
  "wrong_facts": null
}
EOF
  run python3 "$RR" "$IN" --repo "$REPO" --out "$OUT"
  [ "$status" -eq 2 ]
  [[ "$output" == *"bad verdict"* ]]
}

# --- (h) no network imports

@test "the script imports no network or HTTP module" {
  local matches
  matches="$(grep -c 'import urllib\|import http\|requests' "$RR" || true)"
  [ "$matches" = "0" ]
}

# --- (i) a no-literal claim is judged by its command alone

@test "(i) no-literal claims are held or broken by their command" {
  make_input 'the file has three lines' 'test $(wc -l < f.sh) -eq 3' 'f.sh:1'
  run python3 "$RR" "$IN" --repo "$REPO" --out "$OUT"
  [ "$status" -eq 0 ]
  [ "$(python3 "$ART" get "$OUT" verdict)" = '"ok"' ]
  [ "$(python3 "$ART" get "$OUT" errata)" = '["held:0"]' ]

  make_input 'the file has three lines' 'test $(wc -l < f.sh) -eq 4' 'f.sh:1'
  run python3 "$RR" "$IN" --repo "$REPO" --out "$OUT"
  [ "$status" -eq 0 ]
  [ "$(python3 "$ART" get "$OUT" verdict)" = '"broken"' ]
  [ "$(python3 "$ART" get "$OUT" errata)" = '["broken:0: command exit 1"]' ]
}