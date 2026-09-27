#!/usr/bin/env bats
# tools/experiments/jaz/check-truncation.py -- proves .claude/workflows/
# draft-packet.js and draft-byref.js are byte-identical truncations of
# plan.js and plan-byref.js on the constructs they share (RULES, schemas,
# reader prompts, draftPrompt), per docs/superpowers/specs/
# 2026-09-25-jaz-planning-experiment-design.md §6a "Revision 2": "Both are
# derived by truncation into two new workflow scripts, so plan.js and
# plan-byref.js stay untouched." Python3 only (stdlib), same as the script
# itself. Exercised against small synthetic fixtures under --root, never the
# real repo tree, so a red case never needs to survive as a real defect.

setup() {
  JAZ_DIR="$BATS_TEST_DIRNAME/../../tools/experiments/jaz"
  CHECK_PY="$JAZ_DIR/check-truncation.py"
  T="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/jaztrunc.XXXXXX")"
  mkdir -p "$T/.claude/workflows"
}

teardown() {
  rm -rf "$T"
}

# Writes a minimal, self-consistent plan.js/draft-packet.js and
# plan-byref.js/draft-byref.js pair into $T/.claude/workflows: plan.js
# carries the header consts, RULES, PACKET_SCHEMA, DRAFT_SCHEMA, READERS,
# draftPrompt and a Packet+Draft control-flow block wrapped in
# `if (!A.judgeOnly) { ... }` (plus a Judge-only CRITERIA the truncated copy
# must never carry); draft-packet.js starts as an exact copy with the wrapper
# stripped and its meta.name changed. Same shape for plan-byref.js/
# draft-byref.js (header consts incl. STORE, RULES, DRAFT_SCHEMA,
# draftPrompt, a flat Draft-only control-flow block, LENSES as its
# Judge-only name).
write_pair() {
  cat >"$T/.claude/workflows/plan.js" <<'EOF'
export const meta = { name: 'plan' }
const A = args || {}
const REPO = A.repo || '/repo'
const SCRATCH = A.scratch
const SINCE = A.since || '2026-09-04'
const REPLAN = A.replan || null
const RULES = `HARD RULES:
- shared rule text, byte for byte.`
const PACKET_SCHEMA = { type: 'object', properties: { part: { type: 'string' } } }
const DRAFT_SCHEMA = { type: 'object', properties: { path: { type: 'string' } } }
const READERS = [
  { part: 'mechanical', prompt: `read ${'x'} and write it to ${SCRATCH}/packet/${'mechanical'}.md` },
]
const CRITERIA = ['spec coverage']
function draftPrompt(packet, prior, errata) {
  return `${RULES}
Inputs: ${packet.join(', ')}${prior ? `, prior ${prior}` : ''}.`
}
if (!A.judgeOnly) {
  phase('Packet')
  const parts = await parallel(READERS.map((r) => () => agent(r.prompt, { phase: 'Packet', model: 'sonnet' })))
  const mech = parts[0]
  if (mech.checkEmpty !== true) throw new Error('plan: the graph is not sound')
  phase('Draft')
  const d = await agent(draftPrompt(packetPaths, null, null), { label: 'draft', model: 'fable', effort: 'max' })
  draft = d.path
  questions = d.questions
  selfScore = d.selfScore
  log(`draft: ${d.words} words, ${d.tasks.length} tasks, ${d.questions.length} operator questions`)
}
EOF
  cp "$T/.claude/workflows/plan.js" "$T/.claude/workflows/draft-packet.js"
  sed -i "s/name: 'plan'/name: 'draft-packet'/" "$T/.claude/workflows/draft-packet.js"
  # the truncation itself: draft-packet.js never carries plan.js's Judge-only CRITERIA
  sed -i "/^const CRITERIA = /d" "$T/.claude/workflows/draft-packet.js"
  # strip the if(!A.judgeOnly) wrapper: draft-packet.js's control flow is
  # flat. Scoped to the wrapper's own line range only (a sed ADDRESS RANGE,
  # not a bare `s/^  //` over the whole file) -- the file also has a
  # genuinely-2-space-indented READERS array item outside that range, which
  # must keep its indent untouched or it would break READERS' own
  # byte-identity check against plan.js.
  sed -i "/^if (!A\.judgeOnly) {\$/,/^}\$/{ /^if (!A\.judgeOnly) {\$/d; /^}\$/d; s/^  //; }" \
    "$T/.claude/workflows/draft-packet.js"
  # and its own error prefix + a per-phase budget.spent() line the DROP strips from both sides
  sed -i "s/'plan: the graph/'draft-packet: the graph/" "$T/.claude/workflows/draft-packet.js"
  sed -i "/^phase('Draft')\$/a\\  const spentBeforeDraft = budget.spent()" "$T/.claude/workflows/draft-packet.js"

  cat >"$T/.claude/workflows/plan-byref.js" <<'EOF'
export const meta = { name: 'plan-byref' }
const A = args || {}
const REPO = A.repo || '/repo'
const SCRATCH = A.scratch
const STORE = A.store || '/var/lib/evidence'
const RULES = `HARD RULES:
- shared rule text, byte for byte, arm B.`
const DRAFT_SCHEMA = { type: 'object', properties: { path: { type: 'string' } } }
const LENSES = [{ name: 'implementer' }]
function draftPrompt(prior, errata) {
  return `${RULES}
No packet.`
}
phase('Draft')
const d0 = await agent(draftPrompt(null, null), { label: 'draft', model: 'fable', effort: 'max' })
log(`draft: ${d0.words} words, ${d0.tasks.length} tasks, ${d0.questions.length} operator questions`)
EOF
  cp "$T/.claude/workflows/plan-byref.js" "$T/.claude/workflows/draft-byref.js"
  sed -i "s/name: 'plan-byref'/name: 'draft-byref'/" "$T/.claude/workflows/draft-byref.js"
  # the truncation itself: draft-byref.js never carries plan-byref.js's Judge-only LENSES
  sed -i "/^const LENSES = /d" "$T/.claude/workflows/draft-byref.js"
  sed -i "/^phase('Draft')\$/a\\const spentBeforeDraft = budget.spent()" "$T/.claude/workflows/draft-byref.js"
}

@test "passes (exit 0) when every shared construct is byte-identical and no Judge-only name leaked" {
  write_pair
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS arm A"* ]]
  [[ "$output" == *"PASS arm B"* ]]
}

@test "red: fails (exit 1) and names RULES when draft-packet.js's copy is mutated" {
  write_pair
  # A real drift the tool must catch: alter RULES in the truncated copy only.
  sed -i 's/byte for byte\./byte for byte, MUTATED./' "$T/.claude/workflows/draft-packet.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  [[ "$output" == *"RULES"* ]]
  [[ "$output" == *"differs"* ]]
  [[ "$output" == *"draft-packet.js"* ]]
}

@test "green again once the mutation is reverted" {
  write_pair
  sed -i 's/byte for byte\./byte for byte, MUTATED./' "$T/.claude/workflows/draft-packet.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  # revert -- the same pair, unmutated, must go green
  sed -i 's/byte for byte, MUTATED\./byte for byte./' "$T/.claude/workflows/draft-packet.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 0 ]
}

@test "fails (exit 1) and names draftPrompt when draft-byref.js's copy is mutated" {
  write_pair
  sed -i 's/No packet\./No packet at all./' "$T/.claude/workflows/draft-byref.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  [[ "$output" == *"draftPrompt"* ]]
  [[ "$output" == *"draft-byref.js"* ]]
}

@test "fails (exit 1) when a Judge-only name (CRITERIA) survives into draft-packet.js" {
  write_pair
  # a truncation defect: the "Judge phase" const leaked into the Draft-only file
  printf "\nconst CRITERIA = ['spec coverage']\n" >>"$T/.claude/workflows/draft-packet.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  [[ "$output" == *"CRITERIA"* ]]
}

@test "fails (exit 1) when a Judge-only name (LENSES) survives into draft-byref.js" {
  write_pair
  printf "\nconst LENSES = [{ name: 'implementer' }]\n" >>"$T/.claude/workflows/draft-byref.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  [[ "$output" == *"LENSES"* ]]
}

@test "usage error (exit 2) when a required file is missing" {
  # only plan.js exists -- draft-packet.js and both arm-B files are absent
  printf "export const meta = { name: 'plan' }\n" >"$T/.claude/workflows/plan.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 2 ]
  [[ "$output" == *"missing file"* ]]
}

@test "against the real repo tree: exit 0, both pairs reported PASS" {
  run python3 "$CHECK_PY" --root "$BATS_TEST_DIRNAME/../.."
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS arm A (plan.js -> draft-packet.js)"* ]]
  [[ "$output" == *"PASS arm B (plan-byref.js -> draft-byref.js)"* ]]
}

# The five mutants below (Opus review, 2026-09-26) exercise a coverage gap a
# synthetic minimal fixture cannot: a mutant hiding inside the CONTROL FLOW
# that surrounds the shared constructs (a reader's own model, the soundness
# gate) or in a HEADER CONST's default value, neither of which the earlier
# construct-only check walked at all. Each copies the REAL four workflow
# files into $T (a private mutable copy under --root, never the tracked
# files) and mutates one real line, so the assertion is against the actual
# production shape rather than a hand-maintained mirror that could drift
# from it.
copy_real_pair() {
  local real="$BATS_TEST_DIRNAME/../../.claude/workflows"
  cp "$real/plan.js" "$real/plan-byref.js" "$real/draft-packet.js" "$real/draft-byref.js" "$T/.claude/workflows/"
}

@test "mutant: drafter model fable->opus in draft-packet.js's Draft call is red" {
  copy_real_pair
  # "label: 'draft'," names only the real Draft agent() call (meta.phases has
  # no `label` field), so scoping the substitution to that range never
  # touches meta.phases' own (irrelevant, outside the compared slice) 'fable'.
  sed -i "/label: 'draft',/,/schema: DRAFT_SCHEMA,/{s/model: 'fable',/model: 'opus',/}" \
    "$T/.claude/workflows/draft-packet.js"
  grep -q "model: 'opus'," "$T/.claude/workflows/draft-packet.js" # the sed actually landed
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  [[ "$output" == *"control flow differs"* ]]
  [[ "$output" == *"-  model: 'fable',"* ]]
  [[ "$output" == *"+  model: 'opus',"* ]]
}

@test "mutant: drafter effort max->high in draft-packet.js's Draft call is red" {
  copy_real_pair
  sed -i "/label: 'draft',/,/schema: DRAFT_SCHEMA,/{s/effort: 'max',/effort: 'high',/}" \
    "$T/.claude/workflows/draft-packet.js"
  grep -q "effort: 'high'," "$T/.claude/workflows/draft-packet.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  [[ "$output" == *"control flow differs"* ]]
  [[ "$output" == *"-  effort: 'max',"* ]]
  [[ "$output" == *"+  effort: 'high',"* ]]
}

@test "mutant: reader model sonnet->haiku in draft-packet.js's Packet call is red" {
  copy_real_pair
  # the READERS array itself carries no model field -- only the agent() call
  # wrapping it does. meta.phases' Packet entry ALSO says model: 'sonnet',
  # but has no `phase:` field (only `title`/`detail`/`model`), so scoping to
  # the "phase: 'Packet',".."schema: PACKET_SCHEMA," range hits only the real
  # reader agent() call inside the control-flow slice, never the meta noise.
  sed -i "/phase: 'Packet',/,/schema: PACKET_SCHEMA,/{s/model: 'sonnet',/model: 'haiku',/}" \
    "$T/.claude/workflows/draft-packet.js"
  grep -q "model: 'haiku'," "$T/.claude/workflows/draft-packet.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  [[ "$output" == *"control flow differs"* ]]
  [[ "$output" == *"-          model: 'sonnet',"* ]]
  [[ "$output" == *"+          model: 'haiku',"* ]]
}

@test "mutant: the soundness gate 'if (mech.checkEmpty !== true)' -> 'if (false)' is red" {
  copy_real_pair
  sed -i "s/if (mech\.checkEmpty !== true)/if (false)/" "$T/.claude/workflows/draft-packet.js"
  grep -q '^if (false)$' "$T/.claude/workflows/draft-packet.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  [[ "$output" == *"control flow differs"* ]]
  [[ "$output" == *"-if (mech.checkEmpty !== true)"* ]]
  [[ "$output" == *"+if (false)"* ]]
}

@test "mutant: draft-byref.js's STORE default changed is red (header consts)" {
  copy_real_pair
  sed -i "s#const STORE = A.store || '/var/lib/evidence'#const STORE = A.store || '/tmp/evidence'#" \
    "$T/.claude/workflows/draft-byref.js"
  grep -q "/tmp/evidence" "$T/.claude/workflows/draft-byref.js"
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 1 ]
  [[ "$output" == *"header consts differ"* ]]
  [[ "$output" == *"/var/lib/evidence"* ]]
}

@test "the five real-file mutants are all green again once copy_real_pair is unmutated" {
  copy_real_pair
  run python3 "$CHECK_PY" --root "$T"
  [ "$status" -eq 0 ]
}
