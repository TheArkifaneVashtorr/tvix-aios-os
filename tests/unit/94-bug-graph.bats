#!/usr/bin/env bats
# FA19b: the bug workflow as a graph (decision 27c / decision 28) — Flash first,
# a mechanical re-resolver before any paid gate, gated, and escalated to Fable
# at the ladder's end. The committed .claude/workflows/bug.toml is
# soundness-checked by factory-unit and the gate's probes (bug-graph-present /
# bug-graph-nodes / bug-graph-no-models); this file opens that shipped file
# directly (the `unit` check copies .claude/workflows/ into the sandbox like
# tests/, tools/ and .claude/agents, FA19b MAJOR-1 — deleting the committed graph
# turns every case red, where FA19's heredoc twin stayed green) and checks the
# committed input fixture tests/unit/fixtures/fa19-bug-row.json. Case (h) drives
# the refusal's real escalation (FA19b MAJOR-2): the launch line names the
# running graph, never the plan.toml the FA19 Interface-5 claim named. The
# script is invoked with python3, so a missing script reads python's
# "can't open file" (the documented red signal).

setup() {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  FIXTURE="$BATS_TEST_DIRNAME/fixtures/fa19-bug-row.json"
  GRAPH="$BATS_TEST_DIRNAME/../../.claude/workflows/bug.toml"
}

# --- (a) the sound graph is accepted silently ---------------------------------

@test "(a) factory-graph.py check accepts the sound bug graph silently" {
  run python3 "$SEAT/factory-graph.py" check "$GRAPH"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (b) the drill climbs both rungs and ends at the refusal ------------------

@test "(b) the drill dry run reaches the refusal through both rungs" {
  run python3 "$SEAT/factory-run.py" "$GRAPH" --dry-run --input "$FIXTURE" \
    --run "$BATS_TEST_TMPDIR/run-b" --stub-verdicts ok,ok,rework,ok,ok,rework
  [ "$status" -eq 0 ]
  [ "$output" = "flash → reresolve → gate → pro → reresolve2 → gate2 → refusal" ]
}

# --- (c) the re-resolver breaks twice, the gate reworks, rung 2 exhausts ------

@test "(c) the re-resolver breaks twice at rung 1 and the budgets bound the loop" {
  run python3 "$SEAT/factory-run.py" "$GRAPH" --dry-run --input "$FIXTURE" \
    --run "$BATS_TEST_TMPDIR/run-c" \
    --stub-verdicts broken,broken,broken,broken,rework,ok,rework,ok,ok,rework
  [ "$status" -eq 0 ]
  [ "$output" = "flash → reresolve → flash → reresolve → flash → reresolve → gate → pro → reresolve2 → gate2 → refusal" ]
  run grep -o '"reresolve->flash": 0' "$BATS_TEST_TMPDIR/run-c/budgets.json"
  [ "$status" -eq 0 ]
}

# --- (d) a one-step ok run is terminal at the gate (the negative control) -----

@test "(d) a one-step ok run ends at the gate" {
  run python3 "$SEAT/factory-run.py" "$GRAPH" --dry-run --input "$FIXTURE" \
    --run "$BATS_TEST_TMPDIR/run-d" --stub-verdicts ok,ok
  [ "$status" -eq 0 ]
  [ "$output" = "flash → reresolve → gate" ]
}

# --- (e) a model id on a node is refused as an unknown key --------------------

@test "(e) a model id on a node is refused as an unknown key" {
  sed 's/^name = "flash"$/name = "flash"\nmodel = "openai\/gpt-5"/' \
    "$GRAPH" >"$BATS_TEST_TMPDIR/e.toml"
  run python3 "$SEAT/factory-graph.py" check "$BATS_TEST_TMPDIR/e.toml"
  [ "$status" -eq 2 ]
  [[ "$output" == *"flash: unknown key"* ]]
}

# --- (f) --max-rung 1 climbs to the refusal without reaching pro --------------

@test "(f) --max-rung 1 ends at the refusal without reaching pro" {
  run python3 "$SEAT/factory-run.py" "$GRAPH" --dry-run --input "$FIXTURE" \
    --run "$BATS_TEST_TMPDIR/run-f" --max-rung 1 --stub-verdicts ok,ok,rework
  [ "$status" -eq 0 ]
  [ "$output" = "flash → reresolve → gate → refusal" ]
}

# --- (g) the committed input fixture is a sound artifact ----------------------

@test "(g) the committed input fixture passes factory-artifact.py check" {
  run python3 "$SEAT/factory-artifact.py" check "$FIXTURE"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (h) the refusal's escalation relaunches the running bug graph ------------

@test "(h) the refusal's escalation launch line names the running bug graph" {
  # The dry-run stub executor never writes the .escalate (run_stub returns an
  # artifact), and a full non-dry walk shells a seat at the agent nodes, so
  # --start refusal reaches the exact run_refusal MAJOR-2 inspected; --plan is
  # only non-None to pass the preflight's gate-without-plan refuse (no gate
  # runs here).
  run python3 "$SEAT/factory-run.py" "$GRAPH" --input "$FIXTURE" \
    --run "$BATS_TEST_TMPDIR/run-h" --start refusal --plan "$GRAPH"
  [ "$status" -eq 0 ]
  # the .escalate launch: line names .claude/workflows/bug.toml, never plan.toml
  run grep -c '^launch:.*\.claude/workflows/bug\.toml' \
    "$BATS_TEST_TMPDIR/run-h/BUG-run-name-reuse.escalate"
  [ "$output" = "1" ]
  run grep -c 'plan\.toml' "$BATS_TEST_TMPDIR/run-h/BUG-run-name-reuse.escalate"
  [ "$output" = "0" ]
  # the paragraph line names the key and the ladder's end: rung 3, 3 attempts
  run head -n 1 "$BATS_TEST_TMPDIR/run-h/BUG-run-name-reuse.escalate"
  [[ "$output" == "BUG-run-name-reuse:"* ]]
  [[ "$output" == *"at rung 3 after 3 attempts"* ]]
}
