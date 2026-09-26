#!/usr/bin/env bats
# FA14: the declarative workflow-graph grammar (factory-graph.py) and the
# node-artifact grammar (factory-artifact.py), each with a checker that
# refuses an unsound file. Graphs are TOML written by the tests into
# $BATS_TEST_TMPDIR; artifacts are JSON. The scripts live in
# tools/factory/seat and are invoked with python3, so a missing script reads
# python's "can't open file '.../factory-graph.py'" (the documented red
# signal) rather than a bats "command not found".

setup() {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  GRAPH="$SEAT/factory-graph.py"
  ART="$SEAT/factory-artifact.py"
}

# --- a sound graph passes silently ----------------------------------------

@test "a sound graph passes check with empty output" {
  cat >"$BATS_TEST_TMPDIR/a.toml" <<'EOF'
[graph]
name = "demo"
start = "a"
input_kind = "input"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/a.toml"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (b) dangling edge: exact single line ------------------------------

@test "(b) an edge whose to names no node is a dangling edge" {
  cat >"$BATS_TEST_TMPDIR/b.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2

[[edge]]
from = "g"
to = "gx"
when = "ok"
budget = 1
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/b.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/b.toml: edge g->gx: dangling edge" ]
}

# --- (c) unreachable node ----------------------------------------------

@test "(c) a node with no incoming edge is unreachable" {
  cat >"$BATS_TEST_TMPDIR/c.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[node]]
name = "z"
type = "refusal"
rung = 4

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/c.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/c.toml: z: unreachable" ]
}

# --- (d) zero budget ----------------------------------------------------

@test "(d) a zero budget is refused" {
  cat >"$BATS_TEST_TMPDIR/d.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 0

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/d.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/d.toml: edge a->g: zero budget" ]
}

# --- (e) undeclared rung -------------------------------------------------

@test "(e) a node without a rung is refused" {
  cat >"$BATS_TEST_TMPDIR/e.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/e.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/e.toml: a: undeclared rung" ]
}

# --- (f) no exit to refusal ----------------------------------------------

@test "(f) a loop with no refusal has no exit to refusal" {
  cat >"$BATS_TEST_TMPDIR/f.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "ok"
budget = 1
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/f.toml"
  [ "$status" -eq 2 ]
  [[ "$output" == *"no exit to refusal"* ]]
}

# --- (g) a written artifact passes check --------------------------------

@test "(g) a written artifact passes check" {
  run bash -c "python3 '$ART' write attempt --key K1 --node a --rung 1 --claim 't::true::x.sh:1' | python3 '$ART' check /dev/stdin"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (h) bad verdict -----------------------------------------------------

@test "(h) a verdict outside the enum is bad" {
  cat >"$BATS_TEST_TMPDIR/h.json" <<'EOF'
{"kind": "attempt", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "true", "citation": "x.sh:1"}],
 "repro": null, "errata": [], "verdict": "maybe", "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/h.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/h.json: verdict: bad verdict" ]
}

# --- (i) claim without command -----------------------------------------

@test "(i) a claim with an empty command is refused" {
  cat >"$BATS_TEST_TMPDIR/i.json" <<'EOF'
{"kind": "attempt", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "", "citation": "x.sh:1"}],
 "repro": null, "errata": [], "verdict": null, "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/i.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/i.json: claims: claim without command" ]
}

# --- (j) duplicate node ---------------------------------------------------

@test "(j) two node rows with one name are refused" {
  cat >"$BATS_TEST_TMPDIR/j.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/j.toml"
  [ "$status" -eq 2 ]
  [[ "$output" == *"graph $BATS_TEST_TMPDIR/j.toml: a: duplicate node"* ]]
}

# --- (k) bad kind ----------------------------------------------------------

@test "(k) an unknown kind is bad kind" {
  cat >"$BATS_TEST_TMPDIR/k.json" <<'EOF'
{"kind": "nonesuch", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "true", "citation": "x.sh:1"}],
 "repro": null, "errata": [], "verdict": null, "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/k.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/k.json: kind: bad kind" ]
}

# --- (l) bad citation --------------------------------------------------

@test "(l) a non-line citation is bad citation" {
  cat >"$BATS_TEST_TMPDIR/l.json" <<'EOF'
{"kind": "attempt", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "true", "citation": "f.sh:notaline"}],
 "repro": null, "errata": [], "verdict": null, "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/l.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/l.json: citation: bad citation" ]
}

# --- (m) bad type -----------------------------------------------------------

@test "(m) a node type outside the enum is bad type" {
  cat >"$BATS_TEST_TMPDIR/m.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agnet"
rung = 1

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/m.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/m.toml: a: bad type" ]
}

# --- (n) bad when -----------------------------------------------------------

@test "(n) an edge when outside the enum is bad when" {
  cat >"$BATS_TEST_TMPDIR/n.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "okk"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/n.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/n.toml: edge g->r: bad when" ]
}

# --- (o) unknown key (node and edge) -------------------------------------

@test "(o) a foreign key on a node or edge is unknown key" {
  cat >"$BATS_TEST_TMPDIR/o.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"
model = "openai/gpt-5"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
retries = 3
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/o.toml"
  [ "$status" -eq 2 ]
  [[ "$output" == *"graph $BATS_TEST_TMPDIR/o.toml: a: unknown key"* ]]
  [[ "$output" == *"graph $BATS_TEST_TMPDIR/o.toml: edge g->a: unknown key"* ]]
}

# --- (p) unreadable -----------------------------------------------------

@test "(p) an absent or malformed file is unreadable" {
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/nonesuch.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/nonesuch.toml: unreadable: No such file or directory" ]

  printf '[graph\n' >"$BATS_TEST_TMPDIR/bad.toml"
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/bad.toml"
  [ "$status" -eq 2 ]
  [[ "$output" == *"unreadable"* ]]

  run python3 "$ART" check "$BATS_TEST_TMPDIR/nonesuch.json"
  [ "$status" -eq 2 ]
  [[ "$output" == *"unreadable: No such file or directory"* ]]
}

# --- (q) bad input_from ----------------------------------------------------

@test "(q) input_from must name a node and stay scalar off a tool" {
  cat >"$BATS_TEST_TMPDIR/q1.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true
input_from = "zz"

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/q1.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/q1.toml: g: bad input_from" ]

  # input_from naming a node is clean.
  cat >"$BATS_TEST_TMPDIR/q2.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true
input_from = "a"

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/q2.toml"
  [ "$status" -eq 0 ]

  # a list on a non-tool node is bad input_from.
  cat >"$BATS_TEST_TMPDIR/q3.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"
input_from = ["a", "g"]

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/q3.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/q3.toml: a: bad input_from" ]

  # the same list on a tool node is clean.
  cat >"$BATS_TEST_TMPDIR/q4.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "t"
type = "tool"
rung = 1
command = ["tools/factory/seat/some-tool.py"]
input_from = ["a", "g"]

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 2

[[edge]]
from = "a"
to = "t"
when = "ok"
budget = 1

[[edge]]
from = "t"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/q4.toml"
  [ "$status" -eq 0 ]
}

# --- (r) bad start --------------------------------------------------------

@test "(r) a start naming no node is bad start" {
  cat >"$BATS_TEST_TMPDIR/r.toml" <<'EOF'
[graph]
start = "nonesuch"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "g"
type = "gate"
rung = 2
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/r.toml"
  [ "$status" -eq 2 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/r.toml: start: bad start" ]
}

# --- (s) wrong row count ---------------------------------------------------

@test "(s) thirteen scores is a wrong row count" {
  cat >"$BATS_TEST_TMPDIR/s.json" <<'EOF'
{"kind": "verdict", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "true", "citation": "x.sh:1"}],
 "repro": null, "errata": [], "verdict": "ok", "inputs": {},
 "scores": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
 "wrong_facts": null}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/s.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/s.json: scores: wrong row count" ]
}

# --- (t) score out of range ----------------------------------------------

@test "(t) a score outside 0-3 is out of range" {
  cat >"$BATS_TEST_TMPDIR/t.json" <<'EOF'
{"kind": "verdict", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "true", "citation": "x.sh:1"}],
 "repro": null, "errata": [], "verdict": "ok", "inputs": {},
 "scores": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4],
 "wrong_facts": null}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/t.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/t.json: scores: score out of range" ]
}

# --- (u) bad score, and a fully valid write+check -------------------------

@test "(u) a non-integer score or negative wrong_facts is a bad score" {
  cat >"$BATS_TEST_TMPDIR/u1.json" <<'EOF'
{"kind": "verdict", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "true", "citation": "x.sh:1"}],
 "repro": null, "errata": [], "verdict": "ok", "inputs": {},
 "scores": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, "x"],
 "wrong_facts": null}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/u1.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/u1.json: scores: bad score" ]

  cat >"$BATS_TEST_TMPDIR/u2.json" <<'EOF'
{"kind": "verdict", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "true", "citation": "x.sh:1"}],
 "repro": null, "errata": [], "verdict": "ok", "inputs": {},
 "scores": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
 "wrong_facts": -1}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/u2.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/u2.json: wrong_facts: bad score" ]

  run bash -c "python3 '$ART' write verdict --key K2 --node a --rung 2 --verdict ok --claim 't::true::x.sh:1' --scores 3,3,3,3,3,3,3,3,3,3,3,3,3,3 --wrong-facts 0 --input draft=x.md | python3 '$ART' check /dev/stdin"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (v) an artifact without a repro key is refused -----------------------

@test "(v) an artifact without a repro key is refused" {
  cat >"$BATS_TEST_TMPDIR/v.json" <<'EOF'
{"kind": "attempt", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "true", "citation": "x.sh:1"}],
 "errata": [], "verdict": null, "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/v.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/v.json: repro: missing" ]
}

# --- (w) a non-object repro is bad repro ----------------------------------

@test "(w) a non-object repro is bad repro" {
  cat >"$BATS_TEST_TMPDIR/w.json" <<'EOF'
{"kind": "attempt", "key": "K1", "node": "a", "rung": 1,
 "claims": [{"text": "t", "command": "true", "citation": "x.sh:1"}],
 "repro": 42, "errata": [], "verdict": null, "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
  run python3 "$ART" check "$BATS_TEST_TMPDIR/w.json"
  [ "$status" -eq 2 ]
  [ "$output" = "artifact $BATS_TEST_TMPDIR/w.json: repro: bad repro" ]
}

# --- (x) dump of an unsound graph exits 1 with the fault ------------------

@test "(x) dump of an unsound graph exits 1 with the fault" {
  cat >"$BATS_TEST_TMPDIR/x.toml" <<'EOF'
[graph]
start = "nonesuch"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "r"
type = "refusal"
rung = 2

[[edge]]
from = "a"
to = "r"
when = "ok"
budget = 1
EOF
  run python3 "$GRAPH" dump "$BATS_TEST_TMPDIR/x.toml"
  [ "$status" -eq 1 ]
  [ "$output" = "graph $BATS_TEST_TMPDIR/x.toml: start: bad start" ]
}

# --- (y) dump of a sound graph emits full node objects --------------------

@test "(y) dump of a sound graph emits full node objects" {
  cat >"$BATS_TEST_TMPDIR/y.toml" <<'EOF'
[graph]
name = "dump"
start = "t"
input_kind = "input"

[[node]]
name = "t"
type = "tool"
rung = 1
command = "tools/factory/seat/greet.py"

[[node]]
name = "r"
type = "refusal"
rung = 2

[[edge]]
from = "t"
to = "r"
when = "ok"
budget = 1
EOF
  run python3 "$GRAPH" dump "$BATS_TEST_TMPDIR/y.toml"
  [ "$status" -eq 0 ]
  run bash -c "python3 '$GRAPH' dump '$BATS_TEST_TMPDIR/y.toml' | python3 -c 'import json,sys; d=json.load(sys.stdin); n=d[\"nodes\"][0]; assert n[\"type\"]==\"tool\", d; assert n[\"command\"]==\"tools/factory/seat/greet.py\", d; assert n[\"name\"]==\"t\", d'"
  [ "$status" -eq 0 ]
}

# --- (z) get of a present field prints it ---------------------------------

@test "(z) get of a present field prints it" {
  cat >"$BATS_TEST_TMPDIR/z.json" <<'EOF'
{"kind": "attempt", "key": "K9", "node": "a", "rung": 1,
 "claims": [], "repro": null, "errata": [], "verdict": null, "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
  run python3 "$ART" get "$BATS_TEST_TMPDIR/z.json" key
  [ "$status" -eq 0 ]
  [ "$output" = '"K9"' ]
}

# --- (aa) get of an absent field exits 1 ----------------------------------

@test "(aa) get of an absent field exits 1" {
  cat >"$BATS_TEST_TMPDIR/aa.json" <<'EOF'
{"kind": "attempt", "key": "K9", "node": "a", "rung": 1,
 "claims": [], "repro": null, "errata": [], "verdict": null, "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
  run python3 "$ART" get "$BATS_TEST_TMPDIR/aa.json" nosuchfield
  [ "$status" -eq 1 ]
  [ "$output" = "$BATS_TEST_TMPDIR/aa.json: no field nosuchfield" ]
}

# --- (ab) write refuses a verdict outside the enum ------------------------

@test "(ab) write refuses a verdict outside the enum" {
  run python3 "$ART" write attempt --key K9 --node a --rung 1 --verdict maybe
  [ "$status" -eq 2 ]
  [[ "$output" == *"bad verdict"* ]]
}

# --- (ac) a terminal node is exempt from "no exit to refusal" --------------

@test "(ac) a terminal node with no refusal edge passes; a non-bool terminal is refused" {
  # a terminal = true node with no edge to any refusal is the graph's real
  # success terminus, so the soundness rule that every non-refusal node reach a
  # refusal must exempt it; a non-bool terminal value is a `bad terminal` fault.
  cat >"$BATS_TEST_TMPDIR/ac.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "tool"
rung = 1
command = ["tools/factory/seat/some-tool.py"]
terminal = true
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/ac.toml"
  [ "$status" -eq 0 ]
  [ -z "$output" ]

  # the sibling: terminal = "yes" (non-bool) is refused as bad terminal.
  cat >"$BATS_TEST_TMPDIR/ac-bad.toml" <<'EOF'
[graph]
start = "a"

[[node]]
name = "a"
type = "tool"
rung = 1
command = ["tools/factory/seat/some-tool.py"]
terminal = "yes"

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "r"
when = "ok"
budget = 1
EOF
  run python3 "$GRAPH" check "$BATS_TEST_TMPDIR/ac-bad.toml"
  [ "$status" -eq 2 ]
  [[ "$output" == *"bad terminal"* ]]
}