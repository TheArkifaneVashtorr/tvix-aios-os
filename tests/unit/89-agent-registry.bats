#!/usr/bin/env bats
# FA13: the pinned agent registry (tools/factory/agents.toml) and its generated
# .claude/agents/<name>.md shims (factory-registry.py). The registry is TOML;
# the shims are markdown rendered from it and the routing table. The tests run
# against a fixture registry written into $BATS_TEST_TMPDIR (the unit sandbox
# copies tools/factory/seat and tools/factory/plan but neither
# tools/factory/agents.toml nor .claude/agents), so the checker is exercised
# without depending on the committed files; the scripts are invoked with
# python3 so a missing script reads python's "can't open file" (the documented
# red signal).

# run --separate-stderr (the rung-9 ladder-exhausted case) needs bats >= 1.5;
# declare it above the first @test so the BW02 heuristic stays quiet.
bats_require_minimum_version 1.5.0

setup() {
  SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"
  REG="$SEAT/factory-registry.py"
  ROUTE="$SEAT/../route.py"
  # REPO is the committed tree root under the sandbox: where tools/factory,
  # .claude and docs/ledger were copied, so a no-flag check/render resolves
  # against the committed registry and shims (FA13b's drift-check cases).
  REPO="$BATS_TEST_DIRNAME/../.."
  ROOT="$BATS_TEST_TMPDIR"
  REGISTRY="$ROOT/agents.toml"
  SHIMS="$ROOT/agents"
  write_fixture_registry "$REGISTRY"
}

write_fixture_registry() {
  cat >"$1" <<'EOF'
[[agent]]
name = "implement"
route = "openrouter"
role = "implement"
kind = "code"
size = "any"
class = "any"
rung = 1
tools = ["Read", "Edit", "Write", "Bash"]
schema = "attempt"
prompt = "tools/factory/seat/README.md"

[[agent]]
name = "review"
route = "openrouter"
role = "review"
kind = "any"
size = "any"
class = "any"
rung = 1
tools = ["Read", "Bash"]
schema = "verdict"
prompt = "tools/factory/seat/README.md"

[[agent]]
name = "draft"
route = "openrouter-batch"
role = "implement"
kind = "docs"
size = "any"
class = "docs-spec"
rung = 1
tools = ["Read"]
schema = "attempt"
prompt = "tools/factory/plan/seat-plan.md"

[[agent]]
name = "judge"
route = "openrouter"
role = "review"
kind = "docs"
size = "any"
class = "any"
rung = 1
tools = ["Read", "Bash"]
schema = "verdict"
prompt = "tools/factory/plan/judge-prompt.md"

[[agent]]
name = "judge-fable"
route = "openrouter-batch"
role = "review"
kind = "docs"
size = "any"
class = "any"
rung = 1
tools = ["Read"]
schema = "verdict"
prompt = "tools/factory/plan/judge-prompt.md"
EOF
}

render_shims() {
  python3 "$REG" --registry "$REGISTRY" render --out "$SHIMS"
}

copy_committed_tree() {
  # The pieces of the committed tree the registry script reaches (itself, its
  # seat dir for the prompts, route.py, agents.toml, the plan prompts, the
  # .claude/agents shims and the ledger route.py reads) into $1, so a no-flag
  # check/render resolves against this scratch copy rather than the sandbox's.
  local dest="$1"
  mkdir -p "$dest/tools/factory" "$dest/.claude" "$dest/docs"
  cp -r "$SEAT" "$dest/tools/factory/seat"
  cp "$REPO/tools/factory/route.py" "$dest/tools/factory/route.py"
  cp "$REPO/tools/factory/agents.toml" "$dest/tools/factory/agents.toml"
  cp -r "$REPO/tools/factory/plan" "$dest/tools/factory/plan"
  cp -r "$REPO/.claude/agents" "$dest/.claude/agents"
  cp -r "$REPO/docs/ledger" "$dest/docs/ledger"
  # the sandbox's copies are read-only (nix store); make the scratch tree
  # writable so the drift sed, render's write_text and bats' cleanup all work.
  chmod -R u+w "$dest"
}

# --- (a) a clean registry and its rendered shims pass check silently -------

@test "(a) a clean registry with its rendered shims passes check silently" {
  render_shims
  run python3 "$REG" --registry "$REGISTRY" check --shims "$SHIMS"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (b) a trailing newline on a shim is drift -----------------------------

@test "(b) a trailing newline on a shim is drift" {
  render_shims
  printf '\n' >>"$SHIMS/review.md"
  run python3 "$REG" --registry "$REGISTRY" check --shims "$SHIMS"
  [ "$status" -eq 2 ]
  [ "$output" = "registry: review: drift" ]
}

# --- (c) a row whose class does not resolve is unresolvable ----------------

@test "(c) a row whose class does not resolve is unresolvable" {
  render_shims
  cp "$REGISTRY" "$ROOT/class.toml"
  sed -i '0,/^class = "any"/s/class = "any"/class = "nonesuch"/' "$ROOT/class.toml"
  run python3 "$REG" --registry "$ROOT/class.toml" check --shims "$SHIMS"
  [ "$status" -eq 2 ]
  [ "$output" = "registry: implement: unresolvable" ]
}

# --- (d) resolve prints the routed model and effort ------------------------

@test "(d) resolve draft prints the routed model and high effort" {
  route_model="$(python3 "$ROUTE" lookup openrouter-batch implement docs any --class docs-spec --rung 1 | cut -d' ' -f1)"
  run python3 "$REG" --registry "$REGISTRY" resolve draft
  [ "$status" -eq 0 ]
  [ "${output%% *}" = "$route_model" ]
  [[ "$output" == *" high" ]]
}

# --- (e) render is idempotent ----------------------------------------------

@test "(e) render twice changes nothing" {
  render_shims
  cp -r "$SHIMS" "$ROOT/first"
  render_shims
  run diff -r "$ROOT/first" "$SHIMS"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (f) a prompt naming no file is prompt missing -------------------------

@test "(f) a prompt naming no file is prompt missing" {
  render_shims
  cp "$REGISTRY" "$ROOT/prompt.toml"
  sed -i '/name = "review"/,/^prompt =/s/^prompt = .*/prompt = "tools\/factory\/plan\/nonesuch.md"/' "$ROOT/prompt.toml"
  run python3 "$REG" --registry "$ROOT/prompt.toml" check --shims "$SHIMS"
  [ "$status" -eq 2 ]
  [ "$output" = "registry: review: prompt missing" ]
}

# --- (g) a schema outside FA14's kinds is unknown schema -------------------

@test "(g) a schema outside FA14's kinds is unknown schema" {
  render_shims
  cp "$REGISTRY" "$ROOT/schema.toml"
  sed -i '/name = "judge"/,/^schema =/s/^schema = .*/schema = "nonesuch"/' "$ROOT/schema.toml"
  run python3 "$REG" --registry "$ROOT/schema.toml" check --shims "$SHIMS"
  [ "$status" -eq 2 ]
  [ "$output" = "registry: judge: unknown schema" ]
}

# --- (h) a deleted shim is shim missing ------------------------------------

@test "(h) a deleted shim is shim missing" {
  render_shims
  rm "$SHIMS/judge.md"
  run python3 "$REG" --registry "$REGISTRY" check --shims "$SHIMS"
  [ "$status" -eq 2 ]
  [ "$output" = "registry: judge: shim missing" ]
}

# --- (i) the committed registry and shims pass a no-override check ---------

@test "(i) the committed registry and shims pass a no-override check" {
  run python3 "$REG" check
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (j) a drift edit on a scratch tree is reported ------------------------

@test "(j) a drift edit on a scratch tree is reported by a no-override check" {
  local scratch="$BATS_TEST_TMPDIR/scratch"
  copy_committed_tree "$scratch"
  sed -i 's/^effort: high$/effort: low/' "$scratch/.claude/agents/draft.md"
  run python3 "$scratch/tools/factory/seat/factory-registry.py" check
  [ "$status" -eq 2 ]
  [ "$output" = "registry: draft: drift" ]
}

# --- (k) rendering the committed registry twice leaves the shims unchanged --

@test "(k) rendering the committed registry twice leaves the shims unchanged" {
  local scratch="$BATS_TEST_TMPDIR/scratch"
  copy_committed_tree "$scratch"
  git -C "$scratch" init -q
  git -C "$scratch" -c user.name=t -c user.email=t@x add .claude/agents
  git -C "$scratch" -c user.name=t -c user.email=t@x commit -q -m "committed shims"
  python3 "$scratch/tools/factory/seat/factory-registry.py" render --out .claude/agents
  python3 "$scratch/tools/factory/seat/factory-registry.py" render --out .claude/agents
  run git -C "$scratch" diff --quiet .claude/agents
  [ "$status" -eq 0 ]
}

# --- (l) a rung-9 implement row exits 4 with nothing on stdout ------------

@test "(l) a rung-9 implement row exits 4 with nothing on stdout" {
  render_shims
  cp "$REGISTRY" "$ROOT/rung9.toml"
  sed -i '/name = "implement"/,/^rung =/s/^rung = 1/rung = 9/' "$ROOT/rung9.toml"
  run --separate-stderr python3 "$REG" --registry "$ROOT/rung9.toml" resolve implement
  [ "$status" -eq 4 ]
  [ -z "$output" ]
  [[ "$stderr" == *"ladder exhausted at rung 9"* ]]
  run python3 "$REG" --registry "$ROOT/rung9.toml" check --shims "$SHIMS"
  [ "$status" -eq 2 ]
  [ "$output" = "registry: implement: unresolvable" ]
}

# --- (m) a draft row escalated to rung 3 resolves, and check does not fault it

@test "(m) a draft row escalated to rung 3 resolves and is not unresolvable" {
  cp "$REGISTRY" "$ROOT/rung3.toml"
  sed -i '/name = "draft"/,/^rung =/s/^rung = 1/rung = 3/' "$ROOT/rung3.toml"
  run python3 "$REG" --registry "$ROOT/rung3.toml" resolve draft
  [ "$status" -eq 4 ]
  [ "$output" = "fable high" ]
  python3 "$REG" --registry "$ROOT/rung3.toml" render --out "$ROOT/rung3-shims"
  run python3 "$REG" --registry "$ROOT/rung3.toml" check --shims "$ROOT/rung3-shims"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- (n) the committed implement shim matches route.py and the registry row -

@test "(n) the committed implement shim matches route.py and the registry row" {
  model_effort="$(python3 "$ROUTE" lookup openrouter implement code any --class any --rung 1)"
  model="${model_effort% *}"
  effort="${model_effort#* }"
  tools="$(python3 - "$REPO/tools/factory/agents.toml" <<'PY'
import sys, tomllib
rows = tomllib.load(open(sys.argv[1], "rb"))["agent"]
row = next(r for r in rows if r["name"] == "implement")
print(", ".join(row["tools"]))
PY
)"
  shim="$REPO/.claude/agents/implement.md"
  run grep -x "model: $model" "$shim"
  [ "$status" -eq 0 ]
  run grep -x "effort: $effort" "$shim"
  [ "$status" -eq 0 ]
  run grep -x "tools: $tools" "$shim"
  [ "$status" -eq 0 ]
}
