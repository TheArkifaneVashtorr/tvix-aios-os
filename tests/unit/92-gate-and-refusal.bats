#!/usr/bin/env bats
# FA17: the gate and refusal nodes (decision 25b / decision 73) — the runner
# re-runs the plan section's probes, acceptance checks and the input artifact's
# claim commands mechanically (no model), then files and maps the reviewer's
# verdict; a refusal node escalates with <KEY>.escalation.json + <KEY>.escalate.
# FA17b fix round adds: an absent/unreadable/no-section plan is `broken:plan`
# with no model (MAJOR-1), and a reviewer with no verdict line or a non-zero
# exit is `broken` + `no verdict line`, reachable under `set -euo pipefail`
# (MAJOR-2: guard the grep pipeline; run_gate reads the reloaded verdict).

setup() {
  REAL_BASH="$(command -v bash)"
  REAL_PYTHON3="$(command -v python3)"
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  REPO_ROOT="$BATS_TEST_DIRNAME/../.."
  export FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"
  export FACTORY_RUNS="$BATS_TEST_TMPDIR/factory/runs"
  export FACTORY_WS="$BATS_TEST_TMPDIR/factory/ws"
  export FACTORY_TOOLBOX_REPO="$REPO_ROOT"
  export FACTORY_PYTHON3_CMD="$REAL_PYTHON3"
  export FACTORY_SHARED_DSH_HOME_SRC="$BATS_TEST_TMPDIR/share"
  mkdir -p "$FACTORY_SHARED_DSH_HOME_SRC"
  T="$BATS_TEST_TMPDIR"
}

# copy_committed_tree DEST — the committed-tree pieces the registry check (and
# the runner's preflight) reaches, into a writable scratch tree, like
# 91-node-executors: route.py/agents.toml/plan/.claude/agents joined beside
# the seat tools so factory-registry.py resolves against __file__.
copy_committed_tree() {
  local dest="$1"
  mkdir -p "$dest/tools/factory" "$dest/.claude" "$dest/docs"
  cp -r "$SEAT" "$dest/tools/factory/seat"
  cp "$REPO_ROOT/tools/factory/route.py" "$dest/tools/factory/route.py"
  cp "$REPO_ROOT/tools/factory/agents.toml" "$dest/tools/factory/agents.toml"
  cp -r "$REPO_ROOT/tools/factory/plan" "$dest/tools/factory/plan"
  cp -r "$REPO_ROOT/.claude/agents" "$dest/.claude/agents"
  cp -r "$REPO_ROOT/docs/ledger" "$dest/docs/ledger"
  chmod -R u+w "$dest"
}

# write_plan PATH BAD_VALUE — a fixture plan section for key K9 with two probes
# (`count` always passes; `target` passes only when BAD=yes) and acceptance unit.
write_plan() { # $1 = path ; $2 = BAD value (default no)
  local bad="${2:-no}"
  cat >"$1" <<EOF
### K9 (code, M) — FA17 gate fixture

**acceptance:** unit
**probe_env:** BAD=$bad

**probes:**
- count: \`printf '3'\` :: ge 1 :: the count fixture always passes
- target: \`printf '%s' "\$BAD"\` :: eq yes :: the probe_env fixture fails unless BAD=yes
EOF
}

# write_input PATH KEY CLAIMS — an input artifact; CLAIMS is a JSON list.
write_input() { # $1 = path ; $2 = key ; $3 = claims JSON (default [])
  local key="${2:-K9}" claims="${3:-[]}"
  cat >"$1" <<EOF
{"kind": "input", "key": "$key", "node": "seed", "rung": 1,
 "claims": $claims, "repro": null, "errata": [], "verdict": "ok", "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
}

# write_gate_graph FILE — a gate node `g` (reviewer review, probes true) into a
# refusal node `r` on broken; approval at the gate is terminal.
write_gate_graph() {
  cat >"$1" <<'EOF'
[graph]
name = "gate"
start = "g"
input_kind = "input"

[[node]]
name = "g"
type = "gate"
rung = 1
reviewer = "review"
probes = true

[[node]]
name = "r"
type = "refusal"
rung = 2

[[edge]]
from = "g"
to = "r"
when = "broken"
budget = 1
EOF
}

# setup_node_tree — build the scratch tree with a fake factory-ws (prints and
# creates a review workspace), a fake nix (records argv, exit NIX_EXIT) and a
# fake dsh-openrouter review seat (REVIEW_MODE: approve|rework|prose).
setup_node_tree() {
  scratch="$T/scratch"
  copy_committed_tree "$scratch"

  bin="$T/bin"; mkdir -p "$bin"

  review_ws="$T/review-ws"
  cat >"$scratch/tools/factory/seat/factory-ws" <<FAKE
#!$REAL_BASH
mkdir -p '$review_ws'
printf '%s\n' '$review_ws'
FAKE
  chmod +x "$scratch/tools/factory/seat/factory-ws"

  cat >"$bin/nix" <<FAKE
#!$REAL_BASH
printf 'nix-argv=%s\n' "\$*" >> "\${NIX_REC:-$T/nix-rec}"
exit "\${NIX_EXIT:-0}"
FAKE
  chmod +x "$bin/nix"

  cat >"$bin/dsh-openrouter" <<FAKE
#!$REAL_BASH
printf 'REVIEWED model=%s\n' "\$2" >> "\${REVIEW_REC:-$T/review-rec}"
case "\${REVIEW_MODE:-approve}" in
  approve) printf 'FACTORY-REVIEW verdict=approve\n' ;;
  rework) printf 'FACTORY-REVIEW verdict=rework\n' ;;
  prose) printf 'just prose, no verdict line\n'; exit 1 ;;
esac
FAKE
  chmod +x "$bin/dsh-openrouter"
}

# mkdir_task_ws RUN — the real factory-review requires the task workspace to
# already exist (factory_need_dir at factory-review:164).
mkdir_task_ws() { # $1 = run name
  mkdir -p "$FACTORY_WS/$1/K9"
}

# gate_run PLAN RUNDIR — run factory-run.py in the scratch repo against the.
gate_run() {
  local plan="$1" rundir="$2"
  cd "$scratch"
  FACTORY_NIX="$bin/nix" NIX_REC="$nixrec" REVIEW_REC="$reviewrec" \
    PATH="$bin:$PATH" REVIEW_MODE="$REVIEW_MODE" NIX_EXIT="${NIX_EXIT:-0}" \
    FACTORY_PLAN="$plan" \
    run python3 tools/factory/seat/factory-run.py "$T/gate.toml" \
      --input "$T/in.json" --run "$rundir" --plan "$plan"
}

# verdict_of FILE — print the gate artifact's verdict and errata (one per line).
verdict_of() {
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["verdict"]); print("\n".join(d["errata"]))' "$1"
}

# --- (a) a false probe gates the model ---------------------------------------

@test "(a) the false probe breaks the gate and the review is never invoked" {
  setup_node_tree
  write_plan "$T/plan.md"
  write_gate_graph "$T/gate.toml"
  write_input "$T/in.json"
  mkdir_task_ws run-a
  nixrec="$T/nix-a"; reviewrec="$T/review-a"
  REVIEW_MODE=approve gate_run "$T/plan.md" "$T/run-a"
  [ "$status" -eq 0 ]
  run verdict_of "$T/run-a/1-g.json"
  [ "${lines[0]}" = "broken" ]
  [[ "$output" == *"broken:target"* ]]
  [ ! -s "$T/review-a" ]
}

# --- (b) both probes true, review approves -> ok, review filed ---------------

@test "(b) both probes true and an approving review is ok and filed under docs/reviews" {
  setup_node_tree
  write_plan "$T/plan.md" yes
  write_gate_graph "$T/gate.toml"
  write_input "$T/in.json"
  mkdir_task_ws run-b
  nixrec="$T/nix-b"; reviewrec="$T/review-b"
  REVIEW_MODE=approve gate_run "$T/plan.md" "$T/run-b"
  [ "$status" -eq 0 ]
  run verdict_of "$T/run-b/1-g.json"
  [ "${lines[0]}" = "ok" ]
  run bash -c 'ls "$0"/docs/reviews/*-review-K9.md' "$scratch"
  [ "$status" -eq 0 ]
  run tail -n 1 "$(ls "$scratch/docs/reviews/"*-review-K9.md)"
  [ "$output" = "FACTORY-REVIEW verdict=approve" ]
}

# --- (c) a latest review is mapped to rework and filed -------------------

@test "(c) a rework review is mapped to rework and filed" {
  setup_node_tree
  write_plan "$T/plan.md" yes
  write_gate_graph "$T/gate.toml"
  write_input "$T/in.json"
  mkdir_task_ws run-c
  nixrec="$T/nix-c"; reviewrec="$T/review-c"
  REVIEW_MODE=rework gate_run "$T/plan.md" "$T/run-c"
  [ "$status" -eq 0 ]
  run verdict_of "$T/run-c/1-g.json"
  [ "${lines[0]}" = "rework" ]
  run tail -n 1 "$(ls "$scratch/docs/reviews/"*-review-K9.md)"
  [ "$output" = "FACTORY-REVIEW verdict=rework" ]
}

# --- (d) version command exit 1 breaks despite status=done text ---------

@test "(d) a claim whose command exits 1 breaks even with FACTORY-RESULT done" {
  setup_node_tree
  write_plan "$T/plan.md" yes
  write_gate_graph "$T/gate.toml"
  write_input "$T/in.json" K9 '[{"text":"FACTORY-RESULT status=done","command":"false","citation":"x:1"}]'
  mkdir_task_ws run-d
  nixrec="$T/nix-d"; reviewrec="$T/review-d"
  REVIEW_MODE=approve gate_run "$T/plan.md" "$T/run-d"
  [ "$status" -eq 0 ]
  run verdict_of "$T/run-d/1-g.json"
  [ "${lines[0]}" = "broken" ]
  [[ "$output" == *"broken:claim0"* ]]
  [ ! -s "$T/review-d" ]
}

# --- (e) the refusal writes escalation json + .escalate ----------------

@test "(e) a refusal writes the escalation and the journal ends with launch:" {
  setup_node_tree
  write_plan "$T/plan.md" no
  write_gate_graph "$T/gate.toml"
  write_input "$T/in.json"
  mkdir_task_ws run-e
  nixrec="$T/nix-e"; reviewrec="$T/review-e"
  REVIEW_MODE=approve gate_run "$T/plan.md" "$T/run-e"
  [ "$status" -eq 0 ]
  run python3 "$SEAT/factory-artifact.py" check "$T/run-e/K9.escalation.json"
  [ "$status" -eq 0 ]
  run grep -c '^launch:' "$T/run-e/K9.escalate"
  [ "$output" = "1" ]
  run tail -n 1 "$T/run-e/journal.jsonl"
  [[ "$output" == "launch:"* ]]
}

# --- (f) --verdict-artifact without a value is usage exit 2 -----------------

@test "(f) factory-review --verdict-artifact without a value is a usage error" {
  run "$REAL_BASH" "$SEAT/factory-review" run rev K9 --verdict-artifact
  [ "$status" -eq 2 ]
  [[ "$output" == *"--verdict-artifact needs a value"* ]]
}

# --- (k) OC7: the review file's first two lines name the reviewer model and
# --- the rung, the seat's log verbatim below them -----------------------------

@test "factory-review writes reviewer-model and rung as the review file's first two lines, the log verbatim below" {
  # (Mutation: append the lines after the log -> line 1 is the seat's text;
  # write the route effort instead of the rung -> line 2 differs.)
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  mkdir -p "$BATS_TEST_TMPDIR/wspath"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/wspath" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "review"
kind = "any"
size = "any"
model = "z-ai/glm-5.3"
effort = "high"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  printf '### K1 (docs, XS) — t\n\nbody one.\n' >"$plan"
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root/ws/r1/K1" "$root/runs"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  printf '#!%s\nprintf "seat text\\nFACTORY-REVIEW verdict=approve\\n"\n' "$REAL_BASH" >"$bin/dsh-openrouter"
  chmod +x "$bin/dsh-openrouter"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" PATH="$bin:$PATH" \
    OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-review" r1 "$repo" K1
  [ "$status" -eq 0 ]
  run head -n 3 "$root/runs/r1/K1.review.md"
  [ "${lines[0]}" = "reviewer-model: z-ai/glm-5.3" ]
  [ "${lines[1]}" = "rung: 1" ]
  [ -z "${lines[2]}" ]
  run tail -n 1 "$root/runs/r1/K1.review.md"
  [ "$output" = "FACTORY-REVIEW verdict=approve" ]
  run head -n 1 "$root/runs/r1/K1.review.log"
  [ "$output" = "seat text" ]
}

# --- (g) NIX_EXIT=1 breaks the unit and gates the model ------------------

@test "(g) NIX_EXIT=1 breaks the unit acceptance check and gates the model" {
  setup_node_tree
  write_plan "$T/plan.md" yes
  write_gate_graph "$T/gate.toml"
  write_input "$T/in.json"
  mkdir_task_ws run-g
  nixrec="$T/nix-g"; reviewrec="$T/review-g"
  NIX_EXIT=1 REVIEW_MODE=approve gate_run "$T/plan.md" "$T/run-g"
  [ "$status" -eq 0 ]
  run verdict_of "$T/run-g/1-g.json"
  [ "${lines[0]}" = "broken" ]
  [[ "$output" == *"broken:unit"* ]]
  run grep -c '.#checks.x86_64-linux.unit' "$T/nix-g"
  [ "$output" = "1" ]
  [ ! -s "$T/review-g" ]
}

# --- (h) a gate without --plan refused ------------------------------------

@test "(h) a gate without --plan is refused at preflight, nothing written" {
  setup_node_tree
  write_plan "$T/plan.md" yes
  write_gate_graph "$T/gate.toml"
  write_input "$T/in.json"
  cd "$scratch"
  FACTORY_NIX="$bin/nix" PATH="$bin:$PATH" \
    run python3 tools/factory/seat/factory-run.py "$T/gate.toml" \
      --input "$T/in.json" --run "$T/run-h"
  [ "$status" -eq 2 ]
  [[ "$output$stderr" == *"--plan required"* ]]
  [ ! -e "$T/run-h/journal.jsonl" ]
}

# --- (i) FA17b: an absent plan section is broken:plan, no model ---------

@test "(i) an absent plan path is broken:plan with no model and no review" {
  setup_node_tree
  write_gate_graph "$T/gate.toml"
  write_input "$T/in.json"
  mkdir_task_ws run-i
  nixrec="$T/nix-i"; reviewrec="$T/review-i"
  REVIEW_MODE=approve gate_run "$T/NOSUCHPLAN.md" "$T/run-i"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["verdict"]); print(d["errata"]); print(len(d["claims"])); print(d["claims"][0]["text"])' \
    "$T/run-i/1-g.json"
  [ "${lines[0]}" = "broken" ]
  [ "${lines[1]}" = "['broken:plan']" ]
  [ "${lines[2]}" = "1" ]
  [[ "${lines[3]}" == *"NOSUCHPLAN.md"* ]]
  [[ "${lines[3]}" == *"K9"* ]]
  [ ! -s "$T/review-i" ]
}

# --- (j) FA17b: a verdict-less reviewer => broken + no verdict line ---------

@test "(j) a reviewer with no verdict line (exit 1) is broken with no verdict line" {
  setup_node_tree
  write_plan "$T/plan.md" yes
  write_gate_graph "$T/gate.toml"
  write_input "$T/in.json"
  mkdir_task_ws run-j
  nixrec="$T/nix-j"; reviewrec="$T/review-j"
  REVIEW_MODE=prose gate_run "$T/plan.md" "$T/run-j"
  [ "$status" -eq 0 ]
  run verdict_of "$T/run-j/1-g.json"
  [ "${lines[0]}" = "broken" ]
  [[ "$output" == *"no verdict line"* ]]
}