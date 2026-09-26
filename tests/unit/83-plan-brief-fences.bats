#!/usr/bin/env bats
# docs/concepts/2026-09-21a-fence-aware-briefing.md: factory-brief's task
# extractor must not mistake a `##`/`###`-shaped line inside a fenced ```
# block for the next section boundary. pkgs/evidence/tasks.py's parse_plan
# already tracks an in_fence flag for this exact grammar; tools/factory/seat/
# factory-lib.sh's factory_extract_task and factory_extract_h2 (the awk
# extractors factory-brief calls) did not, so a task section that embeds a
# markdown body with its own ##/### headings inside a fenced content block
# (a decision file, a README, a runbook) truncated at the first inner
# heading line -- the live failure that starved PG4's seat on 2026-09-21
# (docs/reviews/2026-09-21-opus-review-pgw3-PG4.md, BLOCKER 1).
#
# Opus review of the fix (commit d744427) found three uncovered mutants:
# factory_extract_h2's own guard could be dropped with nothing here noticing
# (every earlier assertion here exercises factory_extract_task, the "### KEY"
# arm, never the "## Heading" arm); the toggle line's `print` could be
# dropped, silently eating the fence delimiters themselves out of the
# section; and the toggle regex could be narrowed to a bare "```" only,
# missing a language-tagged fence such as "```toml". The three tests below
# close each gap in turn.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup() {
  REAL_BASH="$(command -v bash)"
  PLAN="$BATS_TEST_TMPDIR/plan.md"
  cat >"$PLAN" <<'EOF'
### FX1 (docs, S) — one

body one.

```
## The rule
### An inner three-hash heading
last line of the block
```

**probes:** unit

### FX2 (docs, S) — two

body two.

```toml
### A tagged-fence heading
fenced toml content
```
EOF

  # A separate, minimal plan for the h2 arm (factory_extract_h2, used for
  # "## Global Constraints" / "## Assumptions"): kept apart from PLAN above so
  # its own fenced block's inner heading can never be mistaken for FX1/FX2
  # content, and vice versa.
  H2_PLAN="$BATS_TEST_TMPDIR/h2-plan.md"
  cat >"$H2_PLAN" <<'EOF'
## Assumptions

assumption prose.

```
## An h2-fenced heading
assumption fence line
```

### FX3 (docs, S) — h2 arm probe

body three.
EOF
}

@test "factory-brief does not truncate FX1's section at a heading-shaped line inside its fenced block" {
  run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" FX1
  [ "$status" -eq 0 ]
  # The fenced block's own heading-shaped lines survive whole.
  [[ "$output" == *"## The rule"* ]]
  [[ "$output" == *"### An inner three-hash heading"* ]]
  [[ "$output" == *"last line of the block"* ]]
  # What follows the fence (FX1's own probes line) still made it into the brief.
  [[ "$output" == *"**probes:** unit"* ]]
  # FX2's heading, which really is the next section, still ends FX1's section.
  [[ "$output" != *"### FX2"* ]]
  # The fence delimiter lines themselves (the opening and the closing ```)
  # are section content too -- a mutant that drops the `print` on the toggle
  # line would silently eat both and still pass every assertion above.
  fence_lines=$(printf '%s\n' "$output" | grep -cx '```')
  [ "$fence_lines" -ge 2 ]
}

@test "factory-brief still briefs FX2 on its own, unaffected by FX1's fence" {
  run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" FX2
  [ "$status" -eq 0 ]
  [[ "$output" == *"### FX2 (docs, S) — two"* ]]
  [[ "$output" == *"body two."* ]]
  [[ "$output" != *"### FX1"* ]]
  [[ "$output" != *"## The rule"* ]]
  # FX2's own block opens with a language-tagged fence ("```toml"), not a bare
  # ```. A mutant that toggles in_fence only on an exact "```" line would
  # never notice this fence opened, so its inner heading-shaped line would
  # end the section early instead of surviving as content.
  [[ "$output" == *"### A tagged-fence heading"* ]]
  [[ "$output" == *"fenced toml content"* ]]
}

@test "factory-brief keeps a heading-shaped line inside Assumptions' own fenced block (the h2 arm)" {
  run "$REAL_BASH" "$SEAT/factory-brief" "$H2_PLAN" FX3
  [ "$status" -eq 0 ]
  # factory_extract_h2 (Global Constraints/Assumptions) has its own copy of
  # the fence guard, separate from factory_extract_task's. Nothing above
  # exercises it: this is the one test that would catch that guard being
  # dropped on its own.
  [[ "$output" == *"## An h2-fenced heading"* ]]
  [[ "$output" == *"assumption fence line"* ]]
}
