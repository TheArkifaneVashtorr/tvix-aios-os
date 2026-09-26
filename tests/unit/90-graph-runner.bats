#!/usr/bin/env bats
# FA15: the repo-side graph runner (factory-run.py). It preflights the graph
# (factory-graph.py check), the registry (factory-registry.py check) and the
# input artifact (factory-artifact.py check), then walks the graph from
# graph.start, runs each node's executor (the dry-run stub), checks each
# produced artifact, chooses each edge by the artifact's verdict, and spends
# the edges' attempt budgets. Fixture graphs and artifacts are written into
# $BATS_TEST_TMPDIR. The script is invoked with python3, so a missing file
# reads python's "can't open file '.../factory-run.py'" (the documented red
# signal).

setup() {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  RUNNER="$SEAT/factory-run.py"
}

write_input() { # $1 = path ; $2 = kind (default "input")
  local kind="${2:-input}"
  cat >"$1" <<EOF
{"kind": "$kind", "key": "K9", "node": "seed", "rung": 1,
 "claims": [], "repro": null, "errata": [], "verdict": "ok", "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
}

# the "a-shaped" graph FA14's checker fixture uses: an agent a, a gate g and a
# refusal r, with the g->a broken edge budget set by $1 (default 2).
write_graph_a() { # $1 = path
  cat >"$1" <<'EOF'
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
budget = 5

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 2

[[edge]]
from = "g"
to = "r"
when = "exhausted"
budget = 1
EOF
}

# copy_committed_tree DEST — the committed-tree pieces the registry check (and
# so the runner's preflight) reaches: the seat dir, route.py, agents.toml, the
# plan prompts, .claude/agents and docs/ledger, into a writable scratch tree so
# a no-override factory-registry.py check resolves against it (FA13b's drift
# fixture, tests/unit/89-agent-registry.bats case (j)).
copy_committed_tree() {
  local dest="$1"
  local repo="$BATS_TEST_DIRNAME/../.."
  mkdir -p "$dest/tools/factory" "$dest/.claude" "$dest/docs"
  cp -r "$SEAT" "$dest/tools/factory/seat"
  cp "$repo/tools/factory/route.py" "$dest/tools/factory/route.py"
  cp "$repo/tools/factory/agents.toml" "$dest/tools/factory/agents.toml"
  cp -r "$repo/tools/factory/plan" "$dest/tools/factory/plan"
  cp -r "$repo/.claude/agents" "$dest/.claude/agents"
  cp -r "$repo/docs/ledger" "$dest/docs/ledger"
  chmod -R u+w "$dest"
}

# --- (a) the budget-driving loop ------------------------------------------

@test "(a) an unspendable gate loop exhausts g->a and ends at r" {
  write_graph_a "$BATS_TEST_TMPDIR/a.toml"
  write_input "$BATS_TEST_TMPDIR/in.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/a.toml" --input \
    "$BATS_TEST_TMPDIR/in.json" --run "$BATS_TEST_TMPDIR/run-a" --dry-run \
    --stub-verdicts "ok,broken,ok,broken,ok,broken"
  [ "$status" -eq 0 ]
  [ "$output" = "a → g → a → g → a → g → r" ]
  run grep -o '"g->a": 0' "$BATS_TEST_TMPDIR/run-a/budgets.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; print(json.load(open("'"$BATS_TEST_TMPDIR"'/run-a/7-r.json"))["verdict"])'
  [ "$output" = "exhausted" ]
}

# --- (b) a one-step ok run is a terminal ok at the gate --------------------

@test "(b) a one-step ok run ends at the gate" {
  write_graph_a "$BATS_TEST_TMPDIR/b.toml"
  write_input "$BATS_TEST_TMPDIR/bin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/b.toml" --input \
    "$BATS_TEST_TMPDIR/bin.json" --run "$BATS_TEST_TMPDIR/run-b" --dry-run \
    --stub-verdicts "ok"
  [ "$status" -eq 0 ]
  [ "$output" = "a → g" ]
}

# --- (c) an unsound graph is refused before any write -----------------------

@test "(c) a dangling edge is refused before anything is written" {
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

[[edge]]
from = "a"
to = "g"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "gone"
when = "ok"
budget = 1
EOF
  write_input "$BATS_TEST_TMPDIR/cin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/c.toml" --input \
    "$BATS_TEST_TMPDIR/cin.json" --run "$BATS_TEST_TMPDIR/run-c" --dry-run
  [ "$status" -eq 2 ]
  [ ! -e "$BATS_TEST_TMPDIR/run-c/journal.jsonl" ]
}

# --- (d) a node artifact that fails check refuses the run -------------------

@test "(d) a stub writing an illegal verdict is refused (exit 3)" {
  write_graph_a "$BATS_TEST_TMPDIR/d.toml"
  write_input "$BATS_TEST_TMPDIR/din.json"
  run env FACTORY_STUB_BAD=1 python3 "$RUNNER" "$BATS_TEST_TMPDIR/d.toml" \
    --input "$BATS_TEST_TMPDIR/din.json" --run "$BATS_TEST_TMPDIR/run-d" --dry-run
  [ "$status" -eq 3 ]
  run tail -n 1 "$BATS_TEST_TMPDIR/run-d/journal.jsonl"
  [[ "$output" == *"artifact refused"* ]]
  # the refusal line carries the key `artifact` (Interface 6), never `refused`
  # (the FA15 key that dropped the field).
  run python3 - "$BATS_TEST_TMPDIR/run-d/journal.jsonl" <<'PY'
import json, sys
d = json.loads(open(sys.argv[1]).readlines()[-1])
print("artifact" in d, "refused" in d)
PY
  [ "$output" = "True False" ]
}

# --- (e) --max-rung refuses a node whose rung is above the cap -----------------

@test "(e) --max-rung 1 caps a rung-2 start node to a refusal" {
  cat >"$BATS_TEST_TMPDIR/e.toml" <<'EOF'
[graph]
name = "e"
start = "a"
input_kind = "input"

[[node]]
name = "a"
type = "agent"
rung = 2
role = "implement"

[[node]]
name = "g"
type = "agent"
rung = 1
role = "implement"

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
when = "exhausted"
budget = 1
EOF
  write_input "$BATS_TEST_TMPDIR/ein.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/e.toml" --input \
    "$BATS_TEST_TMPDIR/ein.json" --run "$BATS_TEST_TMPDIR/run-e" --dry-run \
    --max-rung 1
  [ "$status" -eq 0 ]
  [ "$output" = "r" ]
  run python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["verdict"])' \
    "$BATS_TEST_TMPDIR/run-e/1-r.json"
  [ "$output" = "exhausted" ]
}

# --- (f) one journal line per step ------------------------------------------

@test "(f) the journal has one line per node of (a)'s path" {
  write_graph_a "$BATS_TEST_TMPDIR/f.toml"
  write_input "$BATS_TEST_TMPDIR/fin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/f.toml" --input \
    "$BATS_TEST_TMPDIR/fin.json" --run "$BATS_TEST_TMPDIR/run-f" --dry-run \
    --stub-verdicts "ok,broken,ok,broken,ok,broken"
  [ "$status" -eq 0 ]
  run wc -l <"$BATS_TEST_TMPDIR/run-f/journal.jsonl"
  [ "$output" -eq 7 ]
}

# --- (g) an input kind outside graph.input_kind is refused -------------------

@test "(g) an artifact whose kind is not input_kind is refused (exit 2)" {
  write_graph_a "$BATS_TEST_TMPDIR/g.toml"
  write_input "$BATS_TEST_TMPDIR/gin.json" "attempt"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/g.toml" --input \
    "$BATS_TEST_TMPDIR/gin.json" --run "$BATS_TEST_TMPDIR/run-g" --dry-run
  [ "$status" -eq 2 ]
  [ ! -e "$BATS_TEST_TMPDIR/run-g/journal.jsonl" ]
}

# --- (h) --start re-homes the walk -------------------------------------------

@test "(h) --start rehomes the walk, and a bad --start is refused" {
  write_graph_a "$BATS_TEST_TMPDIR/h.toml"
  write_input "$BATS_TEST_TMPDIR/hin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/h.toml" --input \
    "$BATS_TEST_TMPDIR/hin.json" --run "$BATS_TEST_TMPDIR/run-h" --dry-run \
    --stub-verdicts "ok" --start g
  [ "$status" -eq 0 ]
  [ "$output" = "g" ]
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/h.toml" --input \
    "$BATS_TEST_TMPDIR/hin.json" --run "$BATS_TEST_TMPDIR/run-h2" --dry-run \
    --start zz
  [ "$status" -eq 2 ]
  [[ "$output" == *"no such node"* ]]
  [ ! -e "$BATS_TEST_TMPDIR/run-h2/journal.jsonl" ]
}

# --- (i) input_from single and list ------------------------------------------

@test "(i) input_from hands the named node's latest artifact (single and list)" {
  cat >"$BATS_TEST_TMPDIR/i.toml" <<'EOF'
[graph]
name = "i"
start = "a"
input_kind = "input"

[[node]]
name = "a"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "b"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "c"
type = "agent"
rung = 1
role = "implement"
input_from = "a"

[[node]]
name = "t"
type = "tool"
rung = 1
command = ["noop"]
input_from = ["a", "b"]

[[node]]
name = "r"
type = "refusal"
rung = 2

[[edge]]
from = "a"
to = "b"
when = "ok"
budget = 1

[[edge]]
from = "b"
to = "c"
when = "ok"
budget = 1

[[edge]]
from = "c"
to = "t"
when = "ok"
budget = 1

[[edge]]
from = "t"
to = "r"
when = "ok"
budget = 1
EOF
  write_input "$BATS_TEST_TMPDIR/iin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/i.toml" --input \
    "$BATS_TEST_TMPDIR/iin.json" --run "$BATS_TEST_TMPDIR/run-i" --dry-run
  [ "$status" -eq 0 ]
  run python3 - "$BATS_TEST_TMPDIR/run-i/journal.jsonl" <<'PY'
import json, sys
for line in open(sys.argv[1]):
    d = json.loads(line)
    if d["node"] == "c":
        print(d["input"]); break
PY
  [ "$output" = "$BATS_TEST_TMPDIR/run-i/1-a.json" ]
  run python3 - "$BATS_TEST_TMPDIR/run-i/journal.jsonl" <<'PY'
import json, sys
for line in open(sys.argv[1]):
    d = json.loads(line)
    if d["node"] == "t":
        print(json.dumps(d["input"])); break
PY
  [ "$output" = "[\"$BATS_TEST_TMPDIR/run-i/1-a.json\", \"$BATS_TEST_TMPDIR/run-i/2-b.json\"]" ]
}

# --- (j) the explicit exhausted edge beats the BFS refusal --------------------

@test "(j) the explicit exhausted edge beats the nearer refusal" {
  cat >"$BATS_TEST_TMPDIR/j.toml" <<'EOF'
[graph]
name = "j"
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
name = "t"
type = "tool"
rung = 1
command = ["noop"]

[[node]]
name = "r1"
type = "refusal"
rung = 3

[[node]]
name = "r2"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "any"
budget = 6

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 1

[[edge]]
from = "g"
to = "t"
when = "rework"
budget = 1

[[edge]]
from = "t"
to = "r2"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r1"
when = "reject"
budget = 1

[[edge]]
from = "g"
to = "r2"
when = "exhausted"
budget = 1
EOF
  write_input "$BATS_TEST_TMPDIR/jin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/j.toml" --input \
    "$BATS_TEST_TMPDIR/jin.json" --run "$BATS_TEST_TMPDIR/run-j" --dry-run \
    --stub-verdicts "broken,broken,broken,broken"
  [ "$status" -eq 0 ]
  [[ "$output" == *" → g → r2" ]]
}

# --- (k) without the explicit edge, BFS distance beats node order --------------

@test "(k) BFS distance to a refusal beats node file order" {
  cat >"$BATS_TEST_TMPDIR/k.toml" <<'EOF'
[graph]
name = "k"
start = "a"
input_kind = "input"

[[node]]
name = "r2"
type = "refusal"
rung = 3

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
name = "t"
type = "tool"
rung = 1
command = ["noop"]

[[node]]
name = "r1"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "any"
budget = 6

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 1

[[edge]]
from = "g"
to = "t"
when = "rework"
budget = 1

[[edge]]
from = "t"
to = "r2"
when = "ok"
budget = 1

[[edge]]
from = "g"
to = "r1"
when = "reject"
budget = 1
EOF
  write_input "$BATS_TEST_TMPDIR/kin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/k.toml" --input \
    "$BATS_TEST_TMPDIR/kin.json" --run "$BATS_TEST_TMPDIR/run-k" --dry-run \
    --stub-verdicts "broken,broken,broken,broken"
  [ "$status" -eq 0 ]
  [[ "$output" == *" → g → r1" ]]
}

# --- (l) the diamond: the budget survives returning the same gate --------------

@test "(l) an edge budget is per run, surviving the node re-entered from h" {
  cat >"$BATS_TEST_TMPDIR/l.toml" <<'EOF'
[graph]
name = "diamond"
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
name = "h"
type = "agent"
rung = 1
role = "implement"

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "a"
to = "g"
when = "any"
budget = 5

[[edge]]
from = "g"
to = "a"
when = "broken"
budget = 1

[[edge]]
from = "g"
to = "h"
when = "rework"
budget = 2

[[edge]]
from = "h"
to = "g"
when = "any"
budget = 2

[[edge]]
from = "g"
to = "r"
when = "exhausted"
budget = 1
EOF
  write_input "$BATS_TEST_TMPDIR/lin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/l.toml" --input \
    "$BATS_TEST_TMPDIR/lin.json" --run "$BATS_TEST_TMPDIR/run-l" --dry-run \
    --stub-verdicts "ok,broken,ok,rework,ok,broken"
  [ "$status" -eq 0 ]
  [ "$output" = "a → g → a → g → h → g → r" ]
  run grep -o '"g->a": 0' "$BATS_TEST_TMPDIR/run-l/budgets.json"
  [ "$status" -eq 0 ]
}

# --- (m) the preflight registry check refuses a drifted shim before any write

@test "(m) a drifted registry refuses the run before anything is written" {
  local scratch="$BATS_TEST_TMPDIR/scratch"
  copy_committed_tree "$scratch"
  sed -i 's/^effort: high$/effort: low/' "$scratch/.claude/agents/draft.md"
  write_graph_a "$BATS_TEST_TMPDIR/m.toml"
  write_input "$BATS_TEST_TMPDIR/min.json"
  run python3 "$scratch/tools/factory/seat/factory-run.py" \
    "$BATS_TEST_TMPDIR/m.toml" --input "$BATS_TEST_TMPDIR/min.json" \
    --run "$BATS_TEST_TMPDIR/run-m" --dry-run
  [ "$status" -eq 2 ]
  [ "$output" = "registry: draft: drift" ]
  [ ! -e "$BATS_TEST_TMPDIR/run-m/journal.jsonl" ]
}

# --- (n) --plan is recorded verbatim in run.json ----------------------------

@test "(n) --plan is recorded verbatim in run.json" {
  write_graph_a "$BATS_TEST_TMPDIR/n.toml"
  write_input "$BATS_TEST_TMPDIR/nin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/n.toml" --input \
    "$BATS_TEST_TMPDIR/nin.json" --run "$BATS_TEST_TMPDIR/run-n" --dry-run \
    --stub-verdicts "ok" --plan /some/path.md
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; print(json.load(open("'"$BATS_TEST_TMPDIR"'/run-n/run.json"))["plan"])'
  [ "$output" = "/some/path.md" ]
}

# --- (o) every journal line's edge and budget_left match an independent replay

@test "(o) every journal edge and budget_left match an independent replay" {
  write_graph_a "$BATS_TEST_TMPDIR/o.toml"
  write_input "$BATS_TEST_TMPDIR/oin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/o.toml" --input \
    "$BATS_TEST_TMPDIR/oin.json" --run "$BATS_TEST_TMPDIR/run-o" --dry-run \
    --stub-verdicts "ok,broken,ok,broken,ok,broken"
  [ "$status" -eq 0 ]
  run python3 - "$BATS_TEST_TMPDIR/o.toml" "$BATS_TEST_TMPDIR/run-o/journal.jsonl" <<'PY'
import json, sys, tomllib
edges = tomllib.load(open(sys.argv[1], "rb")).get("edge", [])
budget = {f"{e['from']}->{e['to']}": e["budget"] for e in edges}
nodes = []
ok = True
for line in open(sys.argv[2]):
    d = json.loads(line)
    nodes.append(d["node"])
    i = len(nodes) - 1
    if i == 0:
        exp_edge, exp_left = None, None
    else:
        key = f"{nodes[i - 1]}->{nodes[i]}"
        budget[key] -= 1
        exp_edge, exp_left = key, budget[key]
    if d["edge"] != exp_edge or d["budget_left"] != exp_left:
        ok = False
        print(f"line {i + 1}: edge={d['edge']!r} budget_left={d['budget_left']!r} "
              f"expected={exp_edge!r}/{exp_left!r}")
        break
print("match" if ok else "mismatch")
PY
  [ "$output" = "match" ]
}

# --- (p) budgets.json is rewritten once per qualifying step -------------------

@test "(p) budgets.json is rewritten once per step, not once at the end" {
  write_graph_a "$BATS_TEST_TMPDIR/p.toml"
  write_input "$BATS_TEST_TMPDIR/pin.json"
  local site="$BATS_TEST_TMPDIR/site"
  mkdir -p "$site"
  cat >"$site/sitecustomize.py" <<'PY'
import atexit, builtins, os
COUNT_FILE = os.environ["FACTORY_BUDGET_COUNT"]
count = [0]
_real_open = builtins.open
def _counting_open(file, mode="r", *a, **k):
    f = _real_open(file, mode, *a, **k)
    if (isinstance(file, (str, os.PathLike))
            and os.path.basename(os.fspath(file)) == "budgets.json"
            and any(c in mode for c in "wax+")):
        count[0] += 1
    return f
builtins.open = _counting_open
_real_replace = os.replace
def _counting_replace(src, dst, *a, **k):
    if os.path.basename(os.fspath(dst)) == "budgets.json":
        count[0] += 1
    return _real_replace(src, dst, *a, **k)
os.replace = _counting_replace
def _flush():
    with _real_open(COUNT_FILE, "w") as fh:
        fh.write(str(count[0]) + "\n")
atexit.register(_flush)
PY
  run env PYTHONPATH="$site" FACTORY_BUDGET_COUNT="$BATS_TEST_TMPDIR/writes" \
    python3 "$RUNNER" "$BATS_TEST_TMPDIR/p.toml" --input \
    "$BATS_TEST_TMPDIR/pin.json" --run "$BATS_TEST_TMPDIR/run-p" --dry-run \
    --stub-verdicts "ok,broken,ok,broken,ok,broken"
  [ "$status" -eq 0 ]
  run python3 - "$BATS_TEST_TMPDIR/run-p/journal.jsonl" <<'PY'
import json, sys
lines = open(sys.argv[1]).readlines()
print(1 + sum(1 for l in lines if json.loads(l).get("edge") is not None))
PY
  local expected="$output"
  run cat "$BATS_TEST_TMPDIR/writes"
  [ "$output" -eq "$expected" ]
}

# --- (q) a cyclic refusal graph hits the step cap instead of hanging ----------

@test "(q) a cyclic refusal graph hits the step cap instead of hanging" {
  cat >"$BATS_TEST_TMPDIR/q.toml" <<'EOF'
[graph]
name = "q"
start = "r1"
input_kind = "input"

[[node]]
name = "r1"
type = "refusal"
rung = 1

[[node]]
name = "r2"
type = "refusal"
rung = 1

[[edge]]
from = "r1"
to = "r2"
when = "exhausted"
budget = 1

[[edge]]
from = "r2"
to = "r1"
when = "exhausted"
budget = 1
EOF
  write_input "$BATS_TEST_TMPDIR/qin.json"
  run timeout 10 python3 "$RUNNER" "$BATS_TEST_TMPDIR/q.toml" --input \
    "$BATS_TEST_TMPDIR/qin.json" --run "$BATS_TEST_TMPDIR/run-q" --dry-run
  [ "$status" -eq 3 ]
  run tail -n 1 "$BATS_TEST_TMPDIR/run-q/journal.jsonl"
  [[ "$output" == *"step limit"* ]]
}

# --- (r) a terminal node ends the run on ok with no escalation -------------

@test "(r) a terminal tool node ends the run with no escalation" {
  # t is one past start, marked terminal = true, and it keeps an ok -> r edge so
  # a runner that ignores `terminal` would still route the ok verdict to the
  # refusal (and write .escalate); the terminal mechanism short-circuits that.
  cat >"$BATS_TEST_TMPDIR/r.toml" <<'EOF'
[graph]
name = "rterm"
start = "s"
input_kind = "input"

[[node]]
name = "s"
type = "tool"
rung = 1
command = ["tools/factory/seat/some-tool.py"]

[[node]]
name = "t"
type = "tool"
rung = 1
command = ["tools/factory/seat/some-tool.py"]
terminal = true

[[node]]
name = "r"
type = "refusal"
rung = 3

[[edge]]
from = "s"
to = "t"
when = "any"
budget = 1

[[edge]]
from = "t"
to = "r"
when = "ok"
budget = 1
EOF
  write_input "$BATS_TEST_TMPDIR/rin.json"
  run python3 "$RUNNER" "$BATS_TEST_TMPDIR/r.toml" --input \
    "$BATS_TEST_TMPDIR/rin.json" --run "$BATS_TEST_TMPDIR/run-r" --dry-run \
    --stub-verdicts "ok,ok"
  [ "$status" -eq 0 ]
  [ "$output" = "s → t" ]
  [ ! -e "$BATS_TEST_TMPDIR/run-r/K9.escalate" ]
  [ ! -e "$BATS_TEST_TMPDIR/run-r/K9.escalation.json" ]
  run python3 - "$BATS_TEST_TMPDIR/run-r/journal.jsonl" <<'PY'
import json, sys
lines = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
assert lines, "empty journal"
last = json.dumps(lines[-1], sort_keys=True)
assert lines[-1]["node"] == "t", last
assert "launch:" not in last and "escalate" not in last, last
print("terminal")
PY
  [ "$status" -eq 0 ]
  [ "$output" = "terminal" ]
}