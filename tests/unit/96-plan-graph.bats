#!/usr/bin/env bats
# FA21: the plan workflow as a declarative graph (decisions 30b/31a/64a/65a/73);
# FA32 converts the draft (and the revision behind it) from batch tool nodes to
# seats and renames the panel judge-a/judge-b/judge-c, one registry row each, so
# no node runs factory-batch.py in the runner's own process any more -- a run
# started from the devShell needs no lane handed to it. The mechanical verbs
# (factory-artifact.py tally and stage) stay local tool nodes: no lane, no
# model. The graph-walk cases dry-run the runner; the verb cases invoke the
# tools directly against loopback fixtures (no network, no credential).

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
GRAPH="$SEAT/factory-graph.py"
ART="$SEAT/factory-artifact.py"
BATCH="$SEAT/factory-batch.py"
RUNNER="$SEAT/factory-run.py"
REG="$SEAT/factory-registry.py"
ROUTE="$BATS_TEST_DIRNAME/../../tools/factory/route.py"
PLAN="$BATS_TEST_DIRNAME/../../.claude/workflows/plan.toml"
TABLE="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"
FIXTURE="$BATS_TEST_DIRNAME/fixtures/fa20-batch-server.py"

bats_require_minimum_version 1.5.0

setup() {
  T="$BATS_TEST_TMPDIR"
}

teardown() {
  stop_servers
}

write_input() { # $1 = path ; $2 = key (default K9)
  local key="${2:-K9}"
  cat >"$1" <<EOF
{"kind": "input", "key": "$key", "node": "seed", "rung": 1,
 "claims": [], "repro": null, "errata": [], "verdict": "ok", "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
}

# Scores that total 34 with every floor row (2,3,5,6,7,13) at >= 2.
OK_SCORES="3,3,2,2,2,2,2,3,3,2,2,3,3,2"
# One row lowered to total 33 -> rework.
LOW_SCORES="2,3,2,2,2,2,2,3,3,2,2,3,3,2"
# Sum 36 but row 3 (self-contained, index 2) at 1 -> rework.
FLOOR_SCORES="3,3,1,3,2,2,2,3,3,3,3,3,3,2"
# Non-floor row 4 (index 3) differs across the three judges (1 / 2 / 3), so the
# median (2) is neither the max (3) nor the min (1): a median->max or
# median->min mutant must change a verdict to survive (M12/M13). DIFF_OK totals
# 34 with the median (ok; min -> 33 rework), DIFF_LOW totals 33 (rework; max ->
# 34 ok).
DIFF_OK_A="3,3,2,1,2,2,2,3,3,2,2,3,3,2"
DIFF_OK_B="3,3,2,2,2,2,2,3,3,2,2,3,3,2"
DIFF_OK_C="3,3,2,3,2,2,2,3,3,2,2,3,3,2"
DIFF_LOW_A="2,3,2,1,2,2,2,3,3,2,2,3,3,2"
DIFF_LOW_B="2,3,2,2,2,2,2,3,3,2,2,3,3,2"
DIFF_LOW_C="2,3,2,3,2,2,2,3,3,2,2,3,3,2"

# --- (a) the graph is sound ----------------------------------------------

@test "(a) plan.toml is a sound graph: check exits 0 silently" {
  run python3 "$GRAPH" check "$PLAN"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (b) the straight approve: draft -> panel -> tally -> stage -----------

@test "(b) a straight approve walks draft through the panel to the stage" {
  write_input "$T/in.json"
  run env FACTORY_ROUTING_TABLE="$TABLE" python3 "$RUNNER" "$PLAN" --input "$T/in.json" --run "$T/run-b" \
    --dry-run --stub-verdicts "ok,ok,ok,ok,ok"
  [ "$status" -eq 0 ]
  # the success walk ends at stage: the tenth `stage -> refusal ok` edge is gone
  # and `stage` is the terminal success node, so no refusal is reached.
  [ "$output" = "draft → judge-a → judge-b → judge-c → tally → stage" ]
  [ ! -e "$T/run-b/K9.escalate" ]
  [ ! -e "$T/run-b/K9.escalation.json" ]
}

# --- (c) three reworks exhaust the revision budget ------------------------

@test "(c) three reworks exhaust tally->revise and end at the refusal" {
  write_input "$T/in.json"
  run env FACTORY_ROUTING_TABLE="$TABLE" python3 "$RUNNER" "$PLAN" --input "$T/in.json" --run "$T/run-c" \
    --dry-run --stub-verdicts \
    "ok,ok,ok,ok,rework,ok,ok,ok,ok,rework,ok,ok,ok,ok,rework"
  [ "$status" -eq 0 ]
  [[ "$output" == *" → tally → refusal" ]]
  run grep -o '"tally->revise": 0' "$T/run-c/budgets.json"
  [ "$status" -eq 0 ]
  [ "$output" = '"tally->revise": 0' ]
}

# --- (d) a reject at the first tally escalates directly -------------------

@test "(d) a reject at the tally escalates directly to the refusal" {
  write_input "$T/in.json"
  run env FACTORY_ROUTING_TABLE="$TABLE" python3 "$RUNNER" "$PLAN" --input "$T/in.json" --run "$T/run-d" \
    --dry-run --stub-verdicts "ok,ok,ok,ok,reject"
  [ "$status" -eq 0 ]
  [[ "$output" == *"tally → refusal" ]]
  # the arrival-at-refusal journal line names the explicit reject edge (its
  # `when` is "reject") and a spent budget; when the reject edge is deleted the
  # reject verdict falls through to the exhausted edge, whose `when` is
  # "exhausted" -- the two edges share the "tally->refusal" key, so the `when`
  # field is what makes the reject edge observably load-bearing.
  run python3 - "$T/run-d/journal.jsonl" <<'PY'
import json, sys
refusal = None
for line in open(sys.argv[1]):
    d = json.loads(line)
    if d["node"] == "refusal":
        refusal = d
assert refusal is not None, "no refusal journal line"
assert refusal["edge"] == "tally->refusal", refusal
assert refusal["when"] == "reject", refusal
assert refusal["budget_left"] is not None, refusal
print("reject-edge")
PY
  [ "$status" -eq 0 ]
  [ "$output" = "reject-edge" ]
}

# --- (e) the graph names no model id --------------------------------------

@test "(e) a model key on a node is refused as an unknown key" {
  local g="$T/model.toml"
  cp "$PLAN" "$g"
  chmod u+w "$g"
  cat >>"$g" <<'EOF'

[[node]]
name = "draft2"
type = "tool"
rung = 1
model = "google/gemini-3"
command = ["noop"]
EOF
  run python3 "$GRAPH" check "$g"
  [ "$status" -eq 2 ]
  [[ "$output" == *"draft2: unknown key"* ]]
}

# --- (f) the stage node stages under docs/reviews/plan-drafts -------------

@test "(f) the stage node pins --under to docs/reviews/plan-drafts" {
  run python3 - "$PLAN" <<'PY'
import sys, tomllib
data = tomllib.load(open(sys.argv[1], "rb"))
for n in data.get("node", []):
    if n.get("name") == "stage":
        cmd = n.get("command")
        assert cmd == ["tools/factory/seat/factory-artifact.py", "stage",
                       "--under", "docs/reviews/plan-drafts"], cmd
        print("stage pinned")
        break
else:
    raise SystemExit("no stage node")
PY
  [ "$status" -eq 0 ]
  [ "$output" = "stage pinned" ]
}

# --- (g) the judges are blind ---------------------------------------------

@test "(g) each judge sees only the draft, and the journal says so" {
  write_input "$T/in.json"
  run env FACTORY_ROUTING_TABLE="$TABLE" python3 "$RUNNER" "$PLAN" --input "$T/in.json" --run "$T/run-g" \
    --dry-run --stub-verdicts "ok,ok,ok,ok,ok"
  [ "$status" -eq 0 ]
  run python3 - "$T/run-g/journal.jsonl" <<'PY'
import json, sys
draft_path = None
judges = {}
for line in open(sys.argv[1]):
    d = json.loads(line)
    if d["node"] == "draft":
        draft_path = d["artifact"]
    if d["node"] in ("judge-a", "judge-b", "judge-c"):
        judges[d["node"]] = d["input"]
names = list(judges)
assert len(names) == 3 and len(set(names)) == 3, names
for n, inp in judges.items():
    assert inp == draft_path, (n, inp, draft_path)
print("blind")
PY
  [ "$status" -eq 0 ]
  [ "$output" = "blind" ]
}

# --- (h) the tally rule ---------------------------------------------------

write_judge() { # $1 = path ; $2 = scores ; $3 = key ; $4 = node
  python3 "$ART" write verdict --key "$3" --node "$4" --rung 1 --verdict ok \
    --scores "$2" --wrong-facts 0 --input draft="$T/draft.md" >"$1"
}

@test "(h) the tally takes the median of three and applies the 34/floor/reject rule" {
  # the three judges differ on non-floor row 4 (1 / 2 / 3): the median (2) is
  # neither the max (3) nor the min (1), so a median->max or median->min mutant
  # changes a verdict below and the case fails.
  write_judge "$T/j1.json" "$DIFF_OK_A" K9 judge-a
  write_judge "$T/j2.json" "$DIFF_OK_B" K9 judge-b
  write_judge "$T/j3.json" "$DIFF_OK_C" K9 judge-c
  run python3 "$ART" tally "$T/j1.json" "$T/j2.json" "$T/j3.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["verdict"]); print(d["scores"])' <<<"$output"
  [ "${lines[0]}" = "ok" ]
  [ "${lines[1]}" = "[3, 3, 2, 2, 2, 2, 2, 3, 3, 2, 2, 3, 3, 2]" ]

  # median total 33 -> rework; a median->max mutant takes row 4 to 3 (total 34)
  # and would wrongly approve.
  write_judge "$T/j1.json" "$DIFF_LOW_A" K9 judge-a
  write_judge "$T/j2.json" "$DIFF_LOW_B" K9 judge-b
  write_judge "$T/j3.json" "$DIFF_LOW_C" K9 judge-c
  run python3 "$ART" tally "$T/j1.json" "$T/j2.json" "$T/j3.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["verdict"])' <<<"$output"
  [ "$output" = "rework" ]

  # sum 36 but row 3's median is 1 -> rework
  write_judge "$T/j1.json" "$FLOOR_SCORES" K9 judge-a
  write_judge "$T/j2.json" "$FLOOR_SCORES" K9 judge-b
  write_judge "$T/j3.json" "$FLOOR_SCORES" K9 judge-c
  run python3 "$ART" tally "$T/j1.json" "$T/j2.json" "$T/j3.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["verdict"])' <<<"$output"
  [ "$output" = "rework" ]

  # one judge scores row 2 (correct facts) at 0 -> reject (median sum 40)
  write_judge "$T/j1.json" "3,0,3,3,3,3,3,3,3,3,3,3,3,1" K9 judge-a
  write_judge "$T/j2.json" "3,3,3,3,3,3,3,3,3,3,3,3,3,1" K9 judge-b
  write_judge "$T/j3.json" "3,3,3,3,3,3,3,3,3,3,3,3,3,1" K9 judge-c
  run python3 "$ART" tally "$T/j1.json" "$T/j2.json" "$T/j3.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["verdict"])' <<<"$output"
  [ "$output" = "reject" ]

  # fewer than three paths -> exit 2
  run python3 "$ART" tally "$T/j1.json" "$T/j2.json"
  [ "$status" -eq 2 ]
  [[ "$output" == *"need 3 scored artifacts, got 2"* ]]
}

# --- (i) the node verb wraps the batch endpoint synchronously -------------

# A minimal loopback replay for the completion-body cases (a fenced block the
# shared FA20 fixture never serves); the poll-mapping cases use FA20's fixture.
write_node_server() { # $1 = path
  cat >"$1" <<'PY'
import http.server, json, os
CONTENT = os.environ.get("NODE_CONTENT", "")
LOG = os.environ.get("NODE_LOG", "")
BATCH_ID = os.environ.get("NODE_BATCH_ID", "node-batch")
def _content():
    if CONTENT and os.path.isfile(CONTENT):
        with open(CONTENT, encoding="utf-8") as f:
            return f.read()
    return ""
class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)
    def _log(self, method, path, body):
        if LOG:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(f"{method} {path}\n{body}\n")
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode("utf-8", "replace")
        self._log("POST", self.path, raw)
        self._send(202, {"id": BATCH_ID, "status": "validating"})
    def do_GET(self):
        self._log("GET", self.path, "")
        self._send(200, {"id": BATCH_ID, "status": "completed",
            "results": [{"custom_id": "node-result", "response": {"status_code": 200,
                "body": {"model": "m", "choices": [{"message": {"content": _content()}}]}}}]})
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
print(f"PORT={httpd.server_address[1]}", flush=True)
httpd.serve_forever()
PY
}

start_servers() {
  unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
  unset OPENROUTER_API_KEY AUTH_TOKEN FACTORY_BATCH_BASE
  export FA20_REQ_LOG="$T/fa20-req.log"
  export FA20_NEXT_ID="$T/fa20-next-id"
  python3 "$FIXTURE" --log "$T/fa20-req.log" >"$T/fa20-port" 2>"$T/fa20.err" &
  FA20_PID=$!
  local i
  for i in $(seq 1 100); do grep -q '^PORT=' "$T/fa20-port" 2>/dev/null && break; sleep 0.1; done
  FA20_PORT=$(sed -n 's/^PORT=//p' "$T/fa20-port")

  write_node_server "$T/node-server.py"
  NODE_CONTENT="$T/node-content" NODE_LOG="$T/node-log" NODE_BATCH_ID="node-batch" \
    python3 "$T/node-server.py" >"$T/node-port" 2>"$T/node.err" &
  NODE_PID=$!
  for i in $(seq 1 100); do grep -q '^PORT=' "$T/node-port" 2>/dev/null && break; sleep 0.1; done
  NODE_PORT=$(sed -n 's/^PORT=//p' "$T/node-port")
}

stop_servers() {
  [ -n "${FA20_PID:-}" ] && kill "$FA20_PID" 2>/dev/null || true
  [ -n "${NODE_PID:-}" ] && kill "$NODE_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}

write_batch_input() { # $1 = path
  cat >"$1" <<EOF
{"kind": "input", "key": "PLAN-9", "node": "seed", "rung": 1,
 "claims": [], "repro": null, "errata": [], "verdict": "ok",
 "inputs": {"block": "$T/block.md"}, "scores": null, "wrong_facts": null}
EOF
}

@test "(i) node --role draft wraps submit/poll/fetch and maps every failure" {
  start_servers
  printf 'block text for the request log\n' >"$T/block.md"
  write_batch_input "$T/in.json"

  # happy path: a fenced attempt block plus free draft text
  printf 'free draft text\n```json\n{"kind":"attempt","key":"x","node":"y","rung":1,"claims":[],"repro":null,"errata":[],"verdict":"ok","inputs":{},"scores":null,"wrong_facts":null}\n```\n' >"$T/node-content"
  export FACTORY_BATCH_BASE="http://127.0.0.1:$NODE_PORT"
  run env FACTORY_ROUTING_TABLE="$TABLE" FACTORY_NODE=draft FACTORY_RUNG=1 FACTORY_RUN_DIR="$T/run1" \
    FACTORY_BATCH_INTERVAL=0 FACTORY_BATCH_TIMEOUT=5 \
    python3 "$BATCH" node --role draft "$T/in.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys,os; d=json.loads(sys.stdin.read()); print(d["node"], d["rung"], d["kind"]); print(d["inputs"]["draft"]); print(os.path.isfile(d["inputs"]["draft"]))' <<<"$output"
  [ "${lines[0]}" = "draft 1 attempt" ]
  [[ "${lines[1]}" == "$T/run1/"* ]]
  [ "${lines[2]}" = "True" ]
  run bash -c "ls '$T'/run1/batch-*/batch.json"
  [ "$status" -eq 0 ]
  run grep -F 'block text for the request log' "$T/node-log"
  [ "$status" -eq 0 ]

  # batch-fail (FA20 fixture): poll exit 3 -> broken with the status
  printf 'batch-fail\n' >"$T/fa20-next-id"
  run env FACTORY_ROUTING_TABLE="$TABLE" FACTORY_NODE=draft FACTORY_RUNG=1 FACTORY_RUN_DIR="$T/run2" \
    FACTORY_BATCH_INTERVAL=0 FACTORY_BATCH_TIMEOUT=5 \
    FACTORY_BATCH_BASE="http://127.0.0.1:$FA20_PORT" \
    python3 "$BATCH" node --role draft "$T/in.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["verdict"]); print(d["errata"])' <<<"$output"
  [ "${lines[0]}" = "broken" ]
  [ "${lines[1]}" = "['batch batch-fail: failed']" ]

  # batch-stall (FA20 fixture): poll exit 4 -> broken timeout, under 5s
  printf 'batch-stall\n' >"$T/fa20-next-id"
  run env FACTORY_ROUTING_TABLE="$TABLE" FACTORY_NODE=draft FACTORY_RUNG=1 FACTORY_RUN_DIR="$T/run3" \
    FACTORY_BATCH_INTERVAL=0 FACTORY_BATCH_TIMEOUT=1 \
    FACTORY_BATCH_BASE="http://127.0.0.1:$FA20_PORT" \
    python3 "$BATCH" node --role draft "$T/in.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["verdict"]); print(d["errata"])' <<<"$output"
  [ "${lines[0]}" = "broken" ]
  [ "${lines[1]}" = "['batch batch-stall: timeout after 1 s']" ]

  # a body with no fenced block
  printf 'just prose, no block\n' >"$T/node-content"
  run env FACTORY_ROUTING_TABLE="$TABLE" FACTORY_NODE=draft FACTORY_RUNG=1 FACTORY_RUN_DIR="$T/run4" \
    FACTORY_BATCH_INTERVAL=0 FACTORY_BATCH_TIMEOUT=5 \
    FACTORY_BATCH_BASE="http://127.0.0.1:$NODE_PORT" \
    python3 "$BATCH" node --role draft "$T/in.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["verdict"]); print(d["errata"])' <<<"$output"
  [ "${lines[0]}" = "broken" ]
  [ "${lines[1]}" = "['no artifact block in the batch result']" ]

  # judge-c with a block lacking scores
  printf '```json\n{"kind":"verdict","key":"x","node":"y","rung":1,"claims":[],"repro":null,"errata":[],"verdict":"ok","inputs":{},"scores":null,"wrong_facts":null}\n```\n' >"$T/node-content"
  run env FACTORY_ROUTING_TABLE="$TABLE" FACTORY_NODE=judge-c FACTORY_RUNG=1 FACTORY_RUN_DIR="$T/run5" \
    FACTORY_BATCH_INTERVAL=0 FACTORY_BATCH_TIMEOUT=5 \
    FACTORY_BATCH_BASE="http://127.0.0.1:$NODE_PORT" \
    python3 "$BATCH" node --role judge-c "$T/in.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["verdict"]); print(d["errata"])' <<<"$output"
  [ "${lines[0]}" = "broken" ]
  [ "${lines[1]}" = "['judge block lacks scores']" ]

  stop_servers
}

# --- (j) the stage verb ---------------------------------------------------

@test "(j) stage refuses a non-plan-drafts --under and stages under plan-drafts" {
  printf 'draft body\n' >"$T/draft.md"
  cat >"$T/in.json" <<EOF
{"kind": "verdict", "key": "PLAN-9", "node": "tally", "rung": 1,
 "claims": [], "repro": null, "errata": [], "verdict": "ok",
 "inputs": {"draft": "$T/draft.md"}, "scores": null, "wrong_facts": null}
EOF

  # first half: --under docs/superpowers/plans refuses and writes nothing
  run python3 "$ART" stage --under docs/superpowers/plans "$T/in.json"
  [ "$status" -eq 2 ]
  [[ "$output" == *"--under must be docs/reviews/plan-drafts"* ]]

  # second half: --under docs/reviews/plan-drafts stages the draft
  mkdir -p "$T/sandbox/docs/reviews/plan-drafts"
  run bash -c "cd '$T/sandbox' && python3 '$ART' stage --under docs/reviews/plan-drafts '$T/in.json'"
  [ "$status" -eq 0 ]
  local artifact="$output"
  run python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["inputs"]["staged"])' <<<"$artifact"
  [ "$status" -eq 0 ]
  local staged="$output"
  [ -f "$staged" ]
  [[ "$staged" == "$T/sandbox/docs/reviews/plan-drafts/"* ]]
  # the staged basename is exactly <YYYY-MM-DD>-<key>.md.
  local base
  base=$(basename "$staged")
  [[ "$base" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}-PLAN-9\.md$ ]]
}

# --- (k) errata travel from all three judges -------------------------------

@test "(k) errata travel from all three judges into the tally's errata" {
  write_judge "$T/k1.json" "$OK_SCORES" K9 judge-a
  write_judge "$T/k2.json" "$OK_SCORES" K9 judge-b
  write_judge "$T/k3.json" "$OK_SCORES" K9 judge-c
  # one disjoint erratum per judge, so the tally's concatenation is observable.
  run python3 - "$T/k1.json" "$T/k2.json" "$T/k3.json" <<'PY'
import json, sys
for path, tag in zip(sys.argv[1:], ("err-a", "err-b", "err-c")):
    d = json.load(open(path))
    d["errata"] = [tag]
    json.dump(d, open(path, "w"))
print("ok")
PY
  [ "$status" -eq 0 ]
  run python3 "$ART" tally "$T/k1.json" "$T/k2.json" "$T/k3.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["errata"])' <<<"$output"
  [ "$output" = "['err-a', 'err-b', 'err-c']" ]
}

# --- FA32: the draft is a seat and the panel is three families -------------

@test "(FA32 a) the draft and every judge are agent nodes; no node runs factory-batch" {
  # Interface 1's substance: the model-facing nodes are seats, so no node
  # needs a lane handed to it -- nothing runs the batch wrapper in the
  # runner's own process. The tool-node census pins the deliberate shape:
  # the only tool nodes left are FA21's local mechanical verbs (factory-
  # artifact.py tally and stage: no lane, no model), so a NEW tool node fails
  # here rather than slipping in silently. M1 (draft back to a batch tool)
  # fails this case.
  run python3 - "$PLAN" <<'PY'
import sys, tomllib
data = tomllib.load(open(sys.argv[1], "rb"))
nodes = {n["name"]: n for n in data["node"]}
for name in ("draft", "judge-a", "judge-b", "judge-c"):
    n = nodes[name]
    assert n["type"] == "agent", (name, n["type"])
    assert n["role"] == name, (name, n.get("role"))
assert "command" not in nodes["draft"], nodes["draft"]
for n in data["node"]:
    cmd = n.get("command") or []
    assert not any("factory-batch" in c for c in cmd), (n["name"], cmd)
tools = sorted(n["name"] for n in data["node"] if n["type"] == "tool")
assert tools == ["stage", "tally"], tools
print("seats")
PY
  [ "$status" -eq 0 ]
  [ "$output" = "seats" ]
}

@test "(FA32 b) draft, judge-a, judge-b and judge-c resolve to four distinct non-empty models" {
  # Interface 4: four roles, four models, all distinct -- no judge on the
  # drafter's family. M2 (a judge pointed at glm-5.3) and M4 (resolve
  # discarding variant, collapsing the three judges onto one row) both fail
  # this case. Resolving through the registry, not by reading the routing
  # file, is the point: a row that silently fails to resolve cannot pass.
  # FACTORY_ROUTING_TABLE is pinned so an ambient copy of the env var (the
  # operator's live tree) cannot redirect the resolution away from this
  # workspace's table.
  models=""
  for r in draft judge-a judge-b judge-c; do
    run env FACTORY_ROUTING_TABLE="$TABLE" python3 "$REG" resolve "$r"
    [ "$status" -eq 0 ]
    [ -n "$output" ]
    models="$models
$output"
  done
  [ "$(printf '%s\n' "$models" | grep -c .)" -eq 4 ]
  [ "$(printf '%s\n' "$models" | sort -u | grep -c .)" -eq 4 ]
}

@test "(FA32 c) the drafter resolves to z-ai/glm-5.3, not the Flash ladder" {
  # Interface 3: the draft seat lands on the plain glm-5.3 drafting row, not
  # the implement/docs default (deepseek-v4-flash) its class used to fall
  # through to. M3 (dropping the drafting rows) fails this case.
  run env FACTORY_ROUTING_TABLE="$TABLE" python3 "$REG" resolve draft
  [ "$status" -eq 0 ]
  [ "${output%% *}" = "z-ai/glm-5.3" ]
  [ "${output%% *}" != "deepseek/deepseek-v4-flash" ]
}

@test "(FA32 d) factory-registry.py check is silent after render" {
  run env FACTORY_ROUTING_TABLE="$TABLE" python3 "$REG" render --out "$T/fa32-agents"
  [ "$status" -eq 0 ]
  run env FACTORY_ROUTING_TABLE="$TABLE" python3 "$REG" check --shims "$T/fa32-agents"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "(FA32 f) a non-plan caller still resolves on openrouter-batch" {
  # Interface 2: the batch path is not deleted -- the route and its rows stay
  # for any caller that still wants them; this task only changes which route
  # the plan graph's roles resolve on. M5 (deleting the batch rows) fails
  # this case.
  run python3 "$ROUTE" --file "$TABLE" lookup openrouter-batch implement docs M --class docs-spec
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3:batch high" ]
  run bash -c ". '$SEAT/factory-lib.sh'; factory_route --route openrouter-batch --class docs-spec implement docs M '$TABLE'"
  [ "$status" -eq 0 ]
  [ "$output" = "z-ai/glm-5.3:batch high" ]
}

@test "(FA32 h) a registry row asking for a variant no table row carries falls back to the any row" {
  # The fixture table carries a variant-"a" row whose model differs from the
  # default's, and the registry row asks for variant "zzz", which no row
  # carries: the resolution must fall back to the any-variant row (m/base)
  # rather than failing -- and rather than matching the variant row the way
  # `area` matches (an area-keyed row captures ANY request; variant must not,
  # or the judge rows would capture every review/docs call). Green today by
  # construction: no reader passes --variant yet, and the variant row's
  # role (review) does not match the any/any request, so the default wins.
  cat >"$T/h-table.toml" <<'TOMLEOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/base"
effort = "low"

[[route]]
route = "openrouter"
role = "review"
kind = "docs"
size = "any"
variant = "a"
model = "m/va"
effort = "high"
TOMLEOF
  cat >"$T/h-reg.toml" <<'TOMLEOF'
[[agent]]
name = "prober"
route = "openrouter"
role = "any"
kind = "any"
size = "any"
class = "any"
variant = "zzz"
rung = 1
tools = ["Read"]
schema = "verdict"
prompt = "tools/factory/plan/judge-prompt.md"
TOMLEOF
  run env FACTORY_ROUTING_TABLE="$T/h-table.toml" python3 "$REG" --registry "$T/h-reg.toml" resolve prober
  [ "$status" -eq 0 ]
  [ "$output" = "m/base low" ]
}
