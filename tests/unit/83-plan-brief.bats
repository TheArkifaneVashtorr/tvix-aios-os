#!/usr/bin/env bats
# factory-plan-brief (plan P2): the planning packet script. It composes, in a
# fixed order, thirteen mechanical evidence parts (M1..M13) under `## M<n>`
# headings, then FIELD (the driver's contract by fixed grep), OPERATOR (the
# operator model), TARGET (the spec, sized), RUBRIC, CHECKLIST and RULES; and
# it refuses (exit 2, nothing on stdout) when the derived graph is not sound.
#
# The script reads a *toolbox tree* (FACTORY_TOOLBOX_REPO) rather than the repo
# it lives in, so every test point it at a fixture tree built here: the real
# pkgs/evidence/tasks.py + claims.py copied in (so the graph is real), a
# minimal sound ledger, a one-task plan `2026-09-05-evidence-store.md` (so M13
# has an E1 to brief), and fakes for ritual.sh/session-start.sh. `evidence` is
# deliberately kept OFF the PATH (the only tool it lives in on the operator
# host is /run/current-system/sw/bin, which also carries git, so git is restored
# through a shim), which makes M6 degrade deterministically in every sandbox.
#
# Every script runs through bash directly (the way checks.unit's sandbox runs
# them), and FACTORY_TOOLBOX_REPO + FACTORY_PYTHON3_CMD are the sandbox seams the
# plan specifies; HOME is a third, scrubbed here too (setup() below) so
# tasks.py's own ~/factory/runs default can never read the operator's real,
# live run history into a fixture's output.

bats_require_minimum_version 1.5.0

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup() {
  REAL_BASH="$(command -v bash)"
  REAL_GIT="$(command -v git)"
  REAL_PYTHON3="$(command -v python3)"

  # tasks.py's --runs-dir defaults to ~/factory/runs (pkgs/evidence/tasks.py
  # DEFAULT_RUNS_DIR); on the operator's own host that is a real, growing
  # directory of live seat-driver run.meta files. Left as the operator's real
  # $HOME, M3's JSON embeds real age_days floats (now - a real file mtime),
  # whose json.dumps repr length is not stable between two separate process
  # invocations a few milliseconds apart -- flaking the P2b streams byte-count
  # comparison on this host while nix build's sandboxed check (HOME with no
  # ~/factory/runs) never sees it. Give every test here its own empty HOME so
  # DEFAULT_RUNS_DIR resolves to nothing, matching the sandbox.
  export HOME="$BATS_TEST_TMPDIR/home"
  mkdir -p "$HOME"

  # Build a PATH for the SUT that has everything but `evidence`: drop the
  # /run/current-system/sw/bin entry (the only place `evidence` resolves on
  # this host, and the only place `git` resolves there too), then restore git
  # through a shim that carries nothing else.
  local shim="$BATS_TEST_TMPDIR/bin" dir kept=""
  mkdir -p "$shim"
  ln -sfn "$REAL_GIT" "$shim/git"
  while IFS= read -r dir; do
    [ -z "$dir" ] && continue
    [ "$dir" = "/run/current-system/sw/bin" ] && continue
    kept="${kept:+$kept:}$dir"
  done < <(printf '%s\n' "$PATH" | tr ':' '\n')
  export PATH="$shim${kept:+:$kept}"

  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO/docs/ledger" "$REPO/docs/superpowers/specs" \
    "$REPO/docs/superpowers/plans" "$REPO/docs/board" "$REPO/pkgs/evidence" \
    "$REPO/tools/factory/seat" "$REPO/tools"
  git -C "$REPO" init -q
  git -C "$REPO" -c user.name=seat -c user.email=seat@example.com \
    commit -q --allow-empty -m "fixture: base"

  # The graph's repo row: name it nixos-agent-env (M4 hard-codes that name).
  cat >"$REPO/docs/ledger/repos.toml" <<EOF
[[repo]]
name = "nixos-agent-env"
path = "$REPO"
EOF

  # Empty (comment-only) claims file: M7's validate must be silent and exit 0.
  printf '# minimal claims file for the plan-brief fixture\n' \
    >"$REPO/docs/ledger/claims.toml"

  # A minimal routing table (M11 only cats it; nothing here validates it).
  cat >"$REPO/docs/ledger/routing.toml" <<'EOF'
# minimal routing table for the plan-brief fixture

[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-flash"
effort = "off"
EOF

  # MAP.md with a Checks section (M10 reads it verbatim).
  cat >"$REPO/docs/MAP.md" <<'EOF'
# MAP

## Checks

- lint
- unit
- evidence-unit

## Other
EOF

  # A START HERE block (FIELD pastes it).
  cat >"$REPO/docs/OPERATIONS.md" <<'EOF'
# operations

## START HERE

fixture start-here block

## Next section

more prose
EOF

  # Two dated board-log paragraphs, one before and one after a 2026-09-04 cut.
  cat >"$REPO/docs/board/log-2026-09.md" <<'EOF'
**2026-09-03 before paragraph.**

old body line

**2026-09-05 after paragraph.**

new body line
EOF

  # The operator model (OPERATOR pastes it in full).
  printf 'operator model text for the fixture\n' >"$REPO/docs/board/operator-model.md"

  # The default spec: a few words (size S).
  printf 'spec body for the fixture\n' >"$REPO/docs/superpowers/specs/x-design.md"

  # The design spec RUBRIC (### 5.1) and CHECKLIST (## Appendix A) extract from.
  cat >"$REPO/docs/superpowers/specs/2026-09-05-planning-agent-design.md" <<'EOF'
# planning agent design

### 5.1 The rubric (14 rows)

rubric row fixture

### 5.2

after rubric

## Appendix A — the eight questions

appendix fixture line

## Appendix B

after appendix
EOF

  # The one-task plan M13 briefs; carries the Global Constraints/Assumptions
  # factory-brief expects, and an E1 section.
  cat >"$REPO/docs/superpowers/plans/2026-09-05-evidence-store.md" <<'EOF'
## Global Constraints

fixture constraints

## Assumptions

fixture assumptions

### E1 (code, S) — evidence store example

**dependsOn:** none

**touches:** tools/evidence-store.md

**acceptance:** unit

**commit subject:** `evidence: store E1 (test: unit)`
EOF

  # The real graph and claims validator.
  cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/tasks.py" "$REPO/pkgs/evidence/tasks.py"
  cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/claims.py" "$REPO/pkgs/evidence/claims.py"
  cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/evidence.py" "$REPO/pkgs/evidence/evidence.py"
  cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/streams.py" "$REPO/pkgs/evidence/streams.py"
  cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/bugs.py" "$REPO/pkgs/evidence/bugs.py"
  cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/repomap.py" "$REPO/pkgs/evidence/repomap.py"
  # ER9 (judged_state -> panels_naming) imports judgements.py at check time.
  cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/judgements.py" "$REPO/pkgs/evidence/judgements.py"

  # The seat scripts M13 and the FIELD greps read.
  cp "$SEAT"/* "$REPO/tools/factory/seat/"

  # Fakes that print one line each (M8/M9).
  printf '#!/usr/bin/env bash\necho "ritual inflight ok"\n' >"$REPO/tools/ritual.sh"
  printf '#!/usr/bin/env bash\necho "session start ok"\n' >"$REPO/tools/session-start.sh"

  OUT="docs/reviews/plan-drafts/x-probe.md"
  SPEC="docs/superpowers/specs/x-design.md"

  export FACTORY_TOOLBOX_REPO="$REPO"
  export FACTORY_PYTHON3_CMD="$REAL_PYTHON3"
}

# Write a spec of exactly <n> whitespace-separated words to <file>.
spec_with_words() {
  local n=$1 out=$2 i
  : > "$out"
  for ((i = 1; i <= n; i++)); do
    printf 'word%d ' "$i" >> "$out"
  done
  printf '\n' >> "$out"
}

# The thirteen M-part headings, in order of appearance, one per line.
m_order() {
  printf '%s\n' "$output" | grep -oE '^## M[0-9]+' | sed 's/^## //'
}

expected_m_order() {
  printf 'M1\nM2\nM3\nM4\nM5\nM6\nM7\nM8\nM9\nM10\nM11\nM12\nM13\n'
}

@test "factory-plan-brief composes the packet in order (P2 a)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  # Thirteen mechanical parts, once each, ascending.
  [ "$(m_order)" = "$(expected_m_order)" ]
  # The fixed section headings follow them, in this exact order.
  section="$(printf '%s\n' "$output" | grep -oE '^## (FIELD|OPERATOR|TARGET|RUBRIC|CHECKLIST|RULES)$' | sed 's/^## //')"
  [ "$section" = "$(printf 'FIELD\nOPERATOR\nTARGET\nRUBRIC\nCHECKLIST\nRULES\n')" ]
  # The graph was sound, so M1 reports an empty check.
  [[ "$output" == *"checkEmpty: true"* ]]
}

@test "factory-plan-brief refuses a broken graph and runs nothing past check (P2 b)" {
  # A dangling dependsOn breaks the graph; M1 must refuse before any later part.
  cat >"$REPO/docs/superpowers/plans/2026-09-05-evidence-store.md" <<'EOF'
## Global Constraints

fixture constraints

## Assumptions

fixture assumptions

### E1 (code, S) — evidence store example

**dependsOn:** Q9

**touches:** tools/evidence-store.md

**acceptance:** unit

**commit subject:** `evidence: store E1 (test: unit)`
EOF

  # A python shim records every tasks.py subcommand, then runs the real graph.
  local rec="$BATS_TEST_TMPDIR/tasks.calls" shim="$BATS_TEST_TMPDIR/pyshim"
  : > "$rec"
  cat >"$shim" <<SHIM
#!$REAL_BASH
printf '%s\\n' "\$*" >> "$rec"
exec "$REAL_PYTHON3" "\$@"
SHIM
  chmod +x "$shim"

  FACTORY_PYTHON3_CMD="$shim" \
    run --separate-stderr "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 2 ]
  # Nothing on stdout: a refusal prints no brief at all.
  [ -z "$output" ]
  [[ "$stderr" == *"refusing"* ]]
  # Only M1's `check` ran -- no `brief` (or anything else) leaked past it.
  run cat "$rec"
  [[ "$output" == *"check"* ]]
  [[ "$output" != *"brief"* ]]
  [[ "$output" != *"json"* ]]
}

@test "factory-plan-brief degrades M6 when evidence is not on PATH (P2 c)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"unavailable: evidence not on PATH"* ]]
}

@test "factory-plan-brief sizes the spec by word count (P2 d)" {
  local s1500="$REPO/docs/superpowers/specs/s1500.md"
  local s1501="$REPO/docs/superpowers/specs/s1501.md"
  local s4000="$REPO/docs/superpowers/specs/s4000.md"
  local s4001="$REPO/docs/superpowers/specs/s4001.md"
  spec_with_words 1500 "$s1500"
  spec_with_words 1501 "$s1501"
  spec_with_words 4000 "$s4000"
  spec_with_words 4001 "$s4001"

  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "docs/superpowers/specs/s1500.md" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"words: 1500"* ]]
  [[ "$output" == *"size: S"* ]]

  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "docs/superpowers/specs/s1501.md" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"size: M"* ]]

  # 4000 words are still M: the L threshold is strictly greater than 4000.
  # Mutant in factory_plan_size's one home (-le 4000 -> -lt 4000) turns this
  # into size: L, failing this assert.
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "docs/superpowers/specs/s4000.md" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"size: M"* ]]

  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "docs/superpowers/specs/s4001.md" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"size: L"* ]]
  [[ "$output" == *"refuse: an L spec is split into sub-project plans before any task is typed"* ]]
}

@test "factory-plan-brief refuses an out path outside plan-drafts (P2 e)" {
  run --separate-stderr "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "docs/superpowers/plans/stray.md"
  [ "$status" -eq 2 ]
  [ -z "$output" ]
  [[ "$stderr" == *"plan-drafts"* ]]
}

@test "factory-plan-brief filters the board log by --since (P2 f)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT" --since 2026-09-04
  [ "$status" -eq 0 ]
  [[ "$output" != *"before paragraph"* ]]
  [[ "$output" == *"after paragraph"* ]]
}

@test "factory-plan-brief no longer briefs the E1 section in M13, cut to WORKSPACE RULES by P3 (P2 g)" {
  # Was: M13 pasted factory-brief's full output for an unrelated sample task
  # (Global Constraints, Assumptions AND the ### E1 section) so the drafting
  # seat could see a brief's shape. The packet-budget round (P3, 2026-09-19)
  # cut that to the WORKSPACE RULES block alone -- the part of a brief that
  # is actually a CONTRACT the seat must obey, not the unrelated task's own
  # substance -- so ### E1 no longer survives into M13.
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" != *"### E1"* ]]
  [[ "$output" == *"## WORKSPACE RULES"* ]]
}

@test "factory-plan-brief states the plan-drafts contract in RULES (P2 h)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"factory-brief <draft> <KEY>"* ]]
  [[ "$output" == *"docs/reviews/plan-drafts"* ]]
}
# --- P2b: stream separation, whole-or-nothing, and the folded minors ---

# M3's byte count line ("<n> bytes"), or the empty string when absent.
m3_byte_count() {
  printf '%s\n' "$1" | grep -oE '^[0-9]+ bytes$'
}

@test "factory-plan-brief keeps nix noise out of M3 and M7 (P2b streams)" {
  # The wrapper-free baseline count (FACTORY_PYTHON3_CMD is the bare python3).
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  local clean_bytes
  clean_bytes="$(m3_byte_count "$output")"
  [ -n "$clean_bytes" ]

  # A noisy interpreter: one nix "dirty" warning and one real tool line on
  # stderr, then the real python3. The warning must be stripped; the real line
  # must survive under a `stderr:` fence; M3's count and M7's rendering must be
  # identical to the clean run.
  local noisy="$BATS_TEST_TMPDIR/noisy-python"
  cat >"$noisy" <<SHIM
#!$REAL_BASH
printf '%s\n' "warning: Git tree '/x' is dirty" >&2
printf '%s\n' "real tool line" >&2
exec "$REAL_PYTHON3" "\$@"
SHIM
  chmod +x "$noisy"

  FACTORY_PYTHON3_CMD="$noisy" \
    run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [ "$(m3_byte_count "$output")" = "$clean_bytes" ]
  [[ "$output" == *"silent (exit 0)"* ]]
  [[ "$output" == *"stderr:"* ]]
  [[ "$output" == *"real tool line"* ]]
  [[ "$output" != *"is dirty"* ]]
}

@test "factory-plan-brief refuses up front when a packet source is missing (P2b)" {
  rm -f "$REPO/tools/factory/seat/factory-integrate"
  rm -f "$REPO/docs/OPERATIONS.md"
  run --separate-stderr "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 3 ]
  [ -z "$output" ]
  [[ "$stderr" == *"factory-integrate"* ]]
  [[ "$stderr" == *"docs/OPERATIONS.md"* ]]
}

@test "factory-plan-brief names a part that fails mid-packet (P2b)" {
  # A python shim that fails only `tasks.py json` (M3), after M1 and M2 have
  # already succeeded, so the failure is mid-composition.
  local shim="$BATS_TEST_TMPDIR/fail-json"
  cat >"$shim" <<SHIM
#!$REAL_BASH
for a in "\$@"; do
  [ "\$a" = "json" ] && exit 1
done
exec "$REAL_PYTHON3" "\$@"
SHIM
  chmod +x "$shim"

  FACTORY_PYTHON3_CMD="$shim" \
    run --separate-stderr "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 3 ]
  [ -z "$output" ]
  [[ "$stderr" == *"M3"* ]]
}

@test "factory-plan-brief extracts RUBRIC and CHECKLIST from the design spec (P2b)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"rubric row fixture"* ]]
  [[ "$output" == *"appendix fixture line"* ]]
  [[ "$output" != *"unavailable: no rubric.md"* ]]
}

@test "factory-plan-brief refuses a design spec without Appendix A (P2b)" {
  cat >"$REPO/docs/superpowers/specs/2026-09-05-planning-agent-design.md" <<'EOF'
# planning agent design

### 5.1 The rubric (14 rows)

rubric row fixture

### 5.2

after rubric
EOF
  run --separate-stderr "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 3 ]
  [ -z "$output" ]
  [[ "$output" != *"unavailable:"* ]]
}

@test "factory-plan-brief refuses a traversing spec or out path (P2b)" {
  run --separate-stderr "$REAL_BASH" "$SEAT/factory-plan-brief.sh" \
    "docs/superpowers/specs/../../../etc/passwd" "$OUT"
  [ "$status" -eq 2 ]
  [ -z "$output" ]
  [[ "$stderr" == *"spec must be under docs/superpowers/specs/"* ]]

  run --separate-stderr "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" \
    "docs/reviews/plan-drafts/../../../etc/passwd"
  [ "$status" -eq 2 ]
  [ -z "$output" ]
  [[ "$stderr" == *"out must be under docs/reviews/plan-drafts/"* ]]
}

@test "factory-plan-brief refuses a malformed --date or --since (P2b)" {
  run --separate-stderr "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT" --date notadate
  [ "$status" -eq 2 ]
  [ -z "$output" ]
  [[ "$stderr" == *"--date"* ]]

  run --separate-stderr "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT" --since notadate
  [ "$status" -eq 2 ]
  [ -z "$output" ]
  [[ "$stderr" == *"--since"* ]]
}

# --- P2b: the eight formerly-unpinned contract clauses, one test each ---

@test "factory-plan-brief fences the packet with ~~~ (P2b pin fences)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"~~~"* ]]
}

@test "factory-plan-brief dates the header (P2b pin header)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  first_line="$(printf '%s\n' "$output" | head -1)"
  [[ "$first_line" =~ ^#\ Planning\ packet\ —\ [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\ —\ spec\  ]]
}

@test "factory-plan-brief stamps every part with a TS line (P2b pin TS)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  headings="$(printf '%s\n' "$output" | grep -cE '^## (M[0-9]+|FIELD|OPERATOR|TARGET|RUBRIC|CHECKLIST|RULES)( |$)')"
  ts="$(printf '%s\n' "$output" | grep -cE '^TS: [0-9]{4}-[0-9]{2}-[0-9]{2}T')"
  [ "$headings" -eq 19 ]
  [ "$ts" -eq "$headings" ]
}

@test "factory-plan-brief pins M4's --repo nixos-agent-env (P2b pin M4)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *$'## M4 — '*"--repo nixos-agent-env"* ]]
}

@test "factory-plan-brief pins M7's --today (P2b pin M7)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *$'## M7 — '*"--today "* ]]
}

@test "factory-plan-brief runs M9 with FACTORY_RUN unset (P2b pin M9)" {
  printf '#!/usr/bin/env bash\necho "session run: ${FACTORY_RUN:-unset}"\n' \
    >"$REPO/tools/session-start.sh"
  FACTORY_RUN=pa6zzz \
    run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"session run: unset"* ]]
  [[ "$output" != *"session run: pa6zzz"* ]]
}

@test "factory-plan-brief pins M10's Checks section (P2b pin M10)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"- evidence-unit"* ]]
}

@test "factory-plan-brief pins FIELD's START HERE block (P2b pin FIELD)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"fixture start-here block"* ]]
}

@test "factory-plan-brief scopes M6 to the live toolbox repo (P2b M6 scope)" {
  # Put a fake `evidence` on PATH (the shim dir already holds git) so the
  # "not on PATH" branch is not the one taken; the scratch toolbox repo is not
  # the live host, so M6 must report the live-host message instead.
  printf '#!/usr/bin/env bash\necho "fake evidence bundle"\n' \
    >"$BATS_TEST_TMPDIR/bin/evidence"
  chmod +x "$BATS_TEST_TMPDIR/bin/evidence"
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"unavailable: evidence describes the live host, not this tree"* ]]
}

# --- P3: the packet budget (operator decision 2026-09-19) -----------------
# Measured (nix develop -c bash tools/factory/seat/factory-plan-brief.sh
# docs/superpowers/specs/2026-09-18-world-feed-ui-design.md <out> | wc -c):
# a real packet ran 218823 bytes, of which M13 (a sample brief of an
# unrelated plan) contributed 28070 -- but only 2114 of that is the
# WORKSPACE RULES the drafting seat actually needs to obey; the rest is the
# unrelated plan's own Global Constraints/Assumptions/task body. M9
# (tools/session-start.sh) re-emits a second, MORE truncated copy of the
# evidence bundle (M6), the task brief (M2) and the operator model
# (OPERATOR); only its board queue and in-flight blocks are unique. FIELD's
# own board-log pull (paragraphs since 7 days ago, unbounded) turned out to
# be the actual dominant cost at 114472 bytes on its own -- not M13 as
# estimated before measuring -- so it is now capped by byte budget, keeping
# the mechanism (recent paragraphs) but bounding its size the same way
# session-start.sh already caps its own parts.

@test "factory-plan-brief cuts M13 to WORKSPACE RULES only, dropping the sample plan's own body (P3 M13)" {
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  # The contract the seat must obey survives.
  [[ "$output" == *"## WORKSPACE RULES"* ]]
  [[ "$output" == *"Practice TDD"* ]]
  # The unrelated sample plan's own substance does not.
  [[ "$output" != *"fixture constraints"* ]]
  [[ "$output" != *"fixture assumptions"* ]]
  [[ "$output" != *"evidence store example"* ]]
}

@test "factory-plan-brief drops M9's duplicate bundle/brief/operator copies, keeping its board queue and in-flight state (P3 M9)" {
  # A realistic-shaped session-start.sh fake, mirroring tools/session-start.sh's
  # own fixed headings, so the dedup filter's markers are genuinely exercised.
  cat >"$REPO/tools/session-start.sh" <<'EOF'
#!/usr/bin/env bash
echo "## Board — derived queue (docs/OPERATIONS.md)"
echo "fixture board queue line"
echo
echo "# Evidence bundle — fixture timestamp"
echo "fixture bundle duplicate line"
echo
echo "# Task brief (generated fixture)"
echo "fixture brief duplicate line"
echo
echo "## In flight"
echo "fixture in-flight line"
echo
echo "## Operator model (docs/board/operator-model.md)"
echo "operator model text for the fixture"
echo
echo "Where everything is: docs/runbooks/session.md"
EOF
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"fixture board queue line"* ]]
  [[ "$output" == *"fixture in-flight line"* ]]
  [[ "$output" == *"Where everything is: docs/runbooks/session.md"* ]]
  [[ "$output" != *"fixture bundle duplicate line"* ]]
  [[ "$output" != *"fixture brief duplicate line"* ]]
  # The operator model's own text (docs/board/operator-model.md, pasted in
  # full by the separate OPERATOR part) appears exactly once in the whole
  # packet -- M9's duplicate copy of it is gone.
  count=$(grep -c "operator model text for the fixture" <<<"$output")
  [ "$count" -eq 1 ]
}

@test "factory-plan-brief caps FIELD's board-log pull instead of embedding it unbounded (P3 FIELD cap)" {
  # A board log with many large dated paragraphs, all within the --since
  # window, whose combined size would otherwise dwarf the rest of the packet
  # (mirroring the measured 114472-byte pull on the live board log).
  {
    for i in $(seq 1 40); do
      printf '**2026-09-05 entry %02d.** ' "$i"
      head -c 800 /dev/zero | tr '\0' 'x'
      printf '\n\n'
    done
  } >"$REPO/docs/board/log-2026-09.md"
  run "$REAL_BASH" "$SEAT/factory-plan-brief.sh" "$SPEC" "$OUT" --since 2026-09-04
  [ "$status" -eq 0 ]
  [[ "$output" == *"entry 01."* ]]
  [[ "$output" == *"board log capped at"* ]]
  # Nowhere near all 40 entries (each ~820 bytes) survive under any sane cap.
  [[ "$output" != *"entry 40."* ]]
}

@test "factory-plan-brief keeps the composed packet under the operator's 90000-byte budget for the world-feed-ui-design spec (P3 budget)" {
  real_repo=$(cd -- "$BATS_TEST_DIRNAME/../.." && pwd -P)
  real_spec="docs/superpowers/specs/2026-09-18-world-feed-ui-design.md"
  [ -f "$real_repo/$real_spec" ] || skip "world-feed-ui-design spec not present in this checkout"
  out_file="$BATS_TEST_TMPDIR/real-packet.txt"
  FACTORY_TOOLBOX_REPO="$real_repo" FACTORY_PYTHON3_CMD="$REAL_PYTHON3" \
    run "$REAL_BASH" -c "'$SEAT/factory-plan-brief.sh' '$real_spec' docs/reviews/plan-drafts/9999-01-01-budget-probe.md > '$out_file'"
  [ "$status" -eq 0 ]
  bytes=$(wc -c <"$out_file")
  # Mutant: re-inline M13's dropped plan body, restore M9's duplicates, or
  # widen/remove the FIELD board-log cap -- any of those pushes this red.
  [ "$bytes" -lt 90000 ]
  grep -q '^## WORKSPACE RULES' "$out_file"
  grep -q '^## FIELD$' "$out_file"
  grep -q '^## TARGET$' "$out_file"
  grep -q '^## RUBRIC$' "$out_file"
  grep -q '^## CHECKLIST$' "$out_file"
  grep -q '^## RULES$' "$out_file"
}
