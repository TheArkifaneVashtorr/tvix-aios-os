#!/usr/bin/env bats
# FA16: the runner's `agent` and `tool` executors drive the seat's bash tools
# (decision 33a). An agent node shells out to factory-task --node, which
# resolves the registry row, composes the node brief, submits ONE seat job and
# converts the answer's first fenced JSON block into an artifact; the runner
# overwrites kind/key/node/rung and refuses a seat-less run. A tool node runs
# `command` (argv[0] under tools/factory/seat/) with the input path appended,
# FACTORY_NODE/FACTORY_RUNG/FACTORY_RUN_DIR in its environment, cwd the repo,
# no shell; a non-zero exit is `broken` with the stderr tail. A fake
# seat-submit on PATH records its argv and cats a fixture answer.

setup() {
  REAL_BASH="$(command -v bash)"
  REAL_PYTHON3="$(command -v python3)"
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  export FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"
  export FACTORY_RUNS="$BATS_TEST_TMPDIR/factory/runs"
  T="$BATS_TEST_TMPDIR"
}

write_input() { # $1 = path ; $2 = key (default "K9")
  local key="${2:-K9}"
  cat >"$1" <<EOF
{"kind": "input", "key": "$key", "node": "seed", "rung": 1,
 "claims": [], "repro": null, "errata": [], "verdict": "ok", "inputs": {},
 "scores": null, "wrong_facts": null}
EOF
}

# copy_committed_tree DEST — the committed-tree pieces the registry check (and
# the runner's preflight) reaches, into a writable scratch tree (FA13b's drift
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

# write a single agent node `a` -> refusal `r`.
write_agent_graph() {
  cat >"$1" <<'EOF'
[graph]
name = "node"
start = "a"
input_kind = "input"

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
}

# write a single tool node `t` -> refusal `r`; $1 = the command list TOML.
write_tool_graph() {
  cat >"$1" <<EOF
[graph]
name = "node"
start = "t"
input_kind = "input"

[[node]]
name = "t"
type = "tool"
rung = 1
command = [$2]

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
}

# Build the scratch tree, the fake seat-submit ($bin) and a fixture tool that
# records its environment and prints a valid artifact (or $1 = bad | exit1).
setup_node_tree() { # $1 = fixture mode: good | bad | exit1
  local mode="${1:-good}"
  scratch="$T/scratch"
  copy_committed_tree "$scratch"

  bin="$T/bin"; mkdir -p "$bin"
  cat >"$bin/seat-submit" <<FAKE
#!$REAL_BASH
printf 'args=%s\\n' "\$*" >> "\$REC"
cat "\$FAKE_ANSWER"
printf 'FACTORY-RESULT status=done\\n'
FAKE
  chmod +x "$bin/seat-submit"

  if [ "$mode" = "exit1" ]; then
    cat >"$scratch/tools/factory/seat/fixture-tool" <<FIX
#!$REAL_BASH
printf 'node=%s rung=%s rundir=%s\\n' "\$FACTORY_NODE" "\$FACTORY_RUNG" "\$FACTORY_RUN_DIR" >> "\$FIXTURE_REC"
printf 'the tool broke\\n' >&2
exit 1
FIX
  elif [ "$mode" = "bad" ]; then
    cat >"$scratch/tools/factory/seat/fixture-tool" <<FIX
#!$REAL_BASH
printf 'node=%s rung=%s rundir=%s\\n' "\$FACTORY_NODE" "\$FACTORY_RUNG" "\$FACTORY_RUN_DIR" >> "\$FIXTURE_REC"
printf '{"kind":"attempt"}\n'
FIX
  else
    cat >"$scratch/tools/factory/seat/fixture-tool" <<FIX
#!$REAL_BASH
printf 'node=%s rung=%s rundir=%s\\n' "\$FACTORY_NODE" "\$FACTORY_RUNG" "\$FACTORY_RUN_DIR" >> "\$FIXTURE_REC"
printf '{"kind":"attempt","key":"tkey","node":"tnode","rung":1,"claims":[],"repro":null,"errata":[],"verdict":"ok","inputs":{},"scores":null,"wrong_facts":null}\n'
FIX
  fi
  chmod +x "$scratch/tools/factory/seat/fixture-tool"
}

# PATH with every directory that ships a seat-submit stripped (the devShell
# leaks both the operator's /run/current-system/sw/bin/seat-submit and the nix
# store's own seat-submit onto PATH, so a "no seat-submit" case must remove
# each such dir, not one).
path_without_seat_submit() {
  local dir out=""
  while IFS= read -r -d: dir; do
    [ -n "$dir" ] || continue
    [ -x "$dir/seat-submit" ] || out="${out}${out:+:}$dir"
  done <<<"$PATH:"
  printf '%s\n' "$out"
}

# --- (a) an agent node runs one seat job and the runner owns node/rung ------

@test "(a) an agent node runs one seat job; the runner owns node and rung" {
  setup_node_tree good
  write_agent_graph "$T/a.toml"
  write_input "$T/a-in.json"
  cat >"$T/answer" <<'EOF'
```json
{"kind":"attempt","key":"x","node":"y","rung":9,"claims":[],"repro":null,"errata":[],"verdict":"ok","inputs":{},"scores":null,"wrong_facts":null}
```
EOF
  cd "$scratch"
  REC="$T/rec" FAKE_ANSWER="$T/answer" PATH="$bin:$PATH" \
    FACTORY_TOOLBOX_REPO="$scratch" FACTORY_PYTHON3_CMD="$REAL_PYTHON3" \
    run python3 tools/factory/seat/factory-run.py "$T/a.toml" \
      --input "$T/a-in.json" --run "$T/run-a"
  [ "$status" -eq 0 ]
  [ -f "$T/run-a/1-a.json" ]
  run python3 "$SEAT/factory-artifact.py" check "$T/run-a/1-a.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["node"], d["rung"])' \
    "$T/run-a/1-a.json"
  [ "$output" = "a 1" ]
  expected_model=$(cd "$scratch" && python3 tools/factory/seat/factory-registry.py resolve implement | awk '{print $1}')
  run grep -o -- '--model [^ ]*' "$T/rec"
  [ "$output" = "--model $expected_model" ]
}

# --- (b) no seat-submit and no SEAT_SUBMIT -> seat unavailable, exit 3 ------

@test "(b) a seat-less run ends exit 3 with 'seat unavailable' in the journal" {
  setup_node_tree good
  write_agent_graph "$T/b.toml"
  write_input "$T/b-in.json"
  cat >"$T/answer" <<'EOF'
```json
{"kind":"attempt","key":"x","node":"y","rung":1,"claims":[],"repro":null,"errata":[],"verdict":"ok","inputs":{},"scores":null,"wrong_facts":null}
```
EOF
  cd "$scratch"
  REC="$T/rec" FAKE_ANSWER="$T/answer" PATH="$(path_without_seat_submit)" \
    FACTORY_TOOLBOX_REPO="$scratch" FACTORY_PYTHON3_CMD="$REAL_PYTHON3" \
    run python3 tools/factory/seat/factory-run.py "$T/b.toml" \
      --input "$T/b-in.json" --run "$T/run-b"
  [ "$status" -eq 3 ]
  run tail -n 1 "$T/run-b/journal.jsonl"
  [[ "$output" == *"seat unavailable"* ]]
}

# --- (c) prose with no block but FACTORY-RESULT done -> broken --------------

@test "(c) prose with no JSON block is broken despite FACTORY-RESULT done" {
  setup_node_tree good
  write_agent_graph "$T/c.toml"
  write_input "$T/c-in.json"
  printf 'just some prose, no block\n' >"$T/answer"
  cd "$scratch"
  REC="$T/rec" FAKE_ANSWER="$T/answer" PATH="$bin:$PATH" \
    FACTORY_TOOLBOX_REPO="$scratch" FACTORY_PYTHON3_CMD="$REAL_PYTHON3" \
    run python3 tools/factory/seat/factory-run.py "$T/c.toml" \
      --input "$T/c-in.json" --run "$T/run-c"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["verdict"], d["errata"])' \
    "$T/run-c/1-a.json"
  [ "${lines[0]%% *}" = "broken" ]
  [[ "$output" == *"no artifact block in the seat's answer"* ]]
}

# --- (d) a tool node runs its command with the FACTORY_* env ----------------

@test "(d) a tool node runs its command; the fixture saw FACTORY_NODE/RUNG/RUN_DIR" {
  setup_node_tree good
  write_tool_graph "$T/d.toml" '"tools/factory/seat/fixture-tool"'
  write_input "$T/d-in.json"
  cd "$scratch"
  FIXTURE_REC="$T/fix-rec" FACTORY_TOOLBOX_REPO="$scratch" \
    FACTORY_PYTHON3_CMD="$REAL_PYTHON3" PATH="$bin:$PATH" \
    run python3 tools/factory/seat/factory-run.py "$T/d.toml" \
      --input "$T/d-in.json" --run "$T/run-d"
  [ "$status" -eq 0 ]
  run python3 "$SEAT/factory-artifact.py" check "$T/run-d/1-t.json"
  [ "$status" -eq 0 ]
  run cat "$T/fix-rec"
  [[ "$output" == "node=t rung=1 rundir=$T/run-d" ]]
}

# --- (e) the tool exits 1 -> broken with its stderr -------------------------

@test "(e) a tool that exits 1 is broken with its stderr as errata" {
  setup_node_tree exit1
  write_tool_graph "$T/e.toml" '"tools/factory/seat/fixture-tool"'
  write_input "$T/e-in.json"
  cd "$scratch"
  FIXTURE_REC="$T/fix-rec" FACTORY_TOOLBOX_REPO="$scratch" \
    FACTORY_PYTHON3_CMD="$REAL_PYTHON3" PATH="$bin:$PATH" \
    run python3 tools/factory/seat/factory-run.py "$T/e.toml" \
      --input "$T/e-in.json" --run "$T/run-e"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["verdict"]); print(d["errata"])' \
    "$T/run-e/1-t.json"
  [ "${lines[0]}" = "broken" ]
  [[ "$output" == *"the tool broke"* ]]
}

# --- (f) the fake seat is invoked exactly once per agent node ---------------

@test "(f) one seat job per agent node" {
  setup_node_tree good
  write_agent_graph "$T/f.toml"
  write_input "$T/f-in.json"
  cat >"$T/answer" <<'EOF'
```json
{"kind":"attempt","key":"x","node":"y","rung":1,"claims":[],"repro":null,"errata":[],"verdict":"ok","inputs":{},"scores":null,"wrong_facts":null}
```
EOF
  cd "$scratch"
  REC="$T/rec" FAKE_ANSWER="$T/answer" PATH="$bin:$PATH" \
    FACTORY_TOOLBOX_REPO="$scratch" FACTORY_PYTHON3_CMD="$REAL_PYTHON3" \
    run python3 tools/factory/seat/factory-run.py "$T/f.toml" \
      --input "$T/f-in.json" --run "$T/run-f"
  [ "$status" -eq 0 ]
  run wc -l <"$T/rec"
  [ "$output" -eq 1 ]
}

# --- (g) a tool argv[0] outside tools/factory/seat/ is refused, exit 2 ------

@test "(g) a tool command outside tools/factory/seat/ is refused before any write" {
  setup_node_tree good
  write_tool_graph "$T/g.toml" '"/bin/echo"'
  write_input "$T/g-in.json"
  cd "$scratch"
  FACTORY_TOOLBOX_REPO="$scratch" FACTORY_PYTHON3_CMD="$REAL_PYTHON3" PATH="$bin:$PATH" \
    run python3 tools/factory/seat/factory-run.py "$T/g.toml" \
      --input "$T/g-in.json" --run "$T/run-g"
  [ "$status" -eq 2 ]
  [ ! -e "$T/run-g/journal.jsonl" ]
}
