# Planning patterns — the record's own documentation of how a section lands

**Date:** 2026-09-22 · **Status:** approved by the operator in session 35 ("Now, before plan B")
· **Size:** S · **Plan:** `docs/superpowers/plans/2026-09-22-planning-patterns.md`

## 1 The operator's words

"What if we designed a workflow that created documentation for planning steps? Call a bunch
of deepseek agents with their 1 million context window. Have them systematically create it
based patterns lifted from high quality examples like GLM 5.3 or Fable." (2026-09-22,
~15:00.)

## 2 What was measured

- Of 171 gate rejections in the seven days to 2026-09-22, 129 were plan-side: missing-case
  60, wrong-fact 48, underspecified 12, vacuous 9 (`evidence tasks brief`, "Record (7 d)";
  the classes are `docs/ledger/plan-defects.toml`).
- Author does not separate the cohorts: in-chat Fable plans 31/57 first-gate approvals
  (54%), the 2026-09-11 batch 56/99 (57%), hand 2/3 (session-35 measurement, all-time,
  n=278 root tasks with a first-gate row). Touches does: two files or fewer 62/91 (68%),
  five or more 51/102 (50%), z=2.55. Plan task-count shows no clean trend (1–4 tasks 67%,
  9–12 81%, 13+ 51%); size label is flat (56–58%).
- The corpus does not fit one context: plans 715,648 words in 66 files (≈1.0M tokens),
  reviews 1,061,427 words in 440 files (≈1.5M), judgements 178,473 words (≈0.25M). One
  planning step's slice — every Facts block with its verdict, every Tests block with its
  verdict — fits in 1M. `z-ai/glm-5.3` carries 1.31M context, `deepseek/deepseek-v4-pro-0813`
  and `deepseek/deepseek-v4-flash` 1.05M; a full 1M-token read costs ≈$0.05 on flash,
  ≈$0.66 on pro (catalogue 2026-09-22, `docs/decisions/2026-09-22-goal-2-planning.md`).
- A docs task already routes to `deepseek/deepseek-v4-flash` medium at rung 1
  (`docs/ledger/routing.toml`, `[[route]] route = "openrouter" role = "implement"
  kind = "docs"`); routing rows carry no context setting. The dsh seat's window is
  `context_window=${OPENROUTER_CONTEXT_WINDOW:-262144}` (`pkgs/dsh-openrouter/dsh-openrouter.sh`),
  per-launch only. A seat's workspace is a git worktree (`factory-task`, `worktree add`):
  only committed files reach it. `docs/planning/` matches no `owns` glob in
  `docs/ledger/subsystems.toml` and no row in `docs/ledger/publish.toml`; both checks go
  red on an unclassified path.
- What already exists and must not be duplicated: the 14-row rubric
  (`tools/factory/plan/rubric.md`), the judge rule (`judge-prompt.md`), Appendix A's eight
  questions and §4's anticipation rows (`pkgs/dsh-harness/skills/planning/references/`).

## 3 The number this moves

Goal 5 of brief §2 — the surface area shrinks: chat questions and fix rounds per landed
task, read from the `ledger/operator` and `derived/gates` streams. The intermediate number
is the plan-side share of rejections (129/171 today); the acceptance is that plan B's run
record (`docs/reviews/plan-runs/`) names the pattern docs' commit and its tasks' first-gate
approval rate is read against plan A's.

## 4 Items

1. **`tasks.py outcomes`** — a subcommand that writes `docs/ledger/plan-outcomes.jsonl`,
   one row per root task of every plan under `docs/superpowers/plans/`: `key, plan, heading,
   kind, size, touches_n, verdict, plan_defect, review_path, gate_ts`. The join is the
   session-35 measurement's: `tasks.py json` for the graph, `derived/gates.jsonl` filtered to
   `round_kind = "first"` and `key = chain_root`, the earliest row per key by
   `review_commit_ts` (the envelope `ts` is the ingest time — never window on it), tasks
   without a gate row written with `verdict = null`, join losses printed. The file is
   derived, never typed; the orchestrator runs the writer on the host and commits it
   (`docs/OPERATIONS.md`'s START HERE block is the precedent). Unit-tested on a fixture
   store; the writer refuses a store it cannot read rather than writing an empty file.
2. **Six pattern docs under `docs/planning/`**, one per planning step, each written by a
   seat that reads its slice — the sections of that step from every plan, with each
   section's row in `plan-outcomes.jsonl` and, for a rejection, the sentence in its
   review: (a) `facts.md`, (b) `interfaces.md`, (c) `steps.md`, (d) `tests.md` (mutants,
   fixtures, probes), (e) `graph.md` (touches, dependsOn, waves, sizes), (f)
   `operator-dispatch.md`. Each doc carries: the rules (a rule, never a list of
   spellings); at least three exemplars verbatim with the key and its `approve` row; at
   least three anti-patterns verbatim with the key, the class and the review's sentence; a
   checklist for the role that writes that block; and, per pattern, a `predicate:` line
   where one is mechanical — a regex over the section text or a property `tasks.py`
   derives — or `predicate: none` with the reason. A doc cites the rubric, the judge rule
   and Appendix A by path and does not restate them. Exemplars are chosen by verdict, not
   by author; the author is a column, not a filter.
3. **`patterns.py check`** and the flake check `planning-patterns`: parses every
   `docs/planning/*.md`; refuses an exemplar whose key did not `approve` at its first gate
   or an anti-pattern whose key was not rejected; for every mechanical predicate measures
   its presence rate in landed and in rejected sections of that step from
   `plan-outcomes.jsonl` and the plan files, and refuses a predicate whose rate difference
   is under 15 points or whose smaller side has fewer than 10 rows (the threshold is a
   starting number, unmeasured; the check prints every rate so the plan-runs record can
   move it). Mutants: an exemplar with a rejected key → red naming it; a predicate with a
   2-point difference → red naming it; a doc with no exemplar → red.
4. **The ledger rows**: `"docs/planning/*"` under Evidence's `owns` in `subsystems.toml`
   (paralleling `docs/reviews/*`) and under `withhold` in `publish.toml` (paralleling
   `docs/reviews/*`, until the public-project flip lands).
5. **The seat's window**: the six docs tasks launch with
   `OPENROUTER_CONTEXT_WINDOW=1048576`; the plan measures whether `factory-wave` →
   `factory-task` → the seat unit carries the launching shell's environment to
   `dsh-openrouter.sh`, and if it does not, one code task adds the pass-through (a named
   allow-list, not a blanket env copy). Until measured, a docs task's section tells the
   seat to read its slice in key order and to stop reading at 900k tokens, naming what it
   skipped.
6. **Wiring** — `.claude/workflows/plan-team.js`'s brief and role prompts read
   `docs/planning/<step>.md`: the section owner reads `facts`, `interfaces`, `steps`; the
   test planner `tests`; the architect `graph`; the integrator `operator-dispatch`. The
   orchestrator lands this by hand (OS3's precedent); it is out of the plan.

## 5 Waves

Item 1 and item 4 first (item 4 is XS, docs). Items 2a–2f in one wave of six seats on
`deepseek/deepseek-v4-flash` (wave cap 8) after item 1's file is committed. Item 3 after
2a–2f land, gated red-then-green on the six docs. Item 5's measurement rides with item 1's
wave as a probe; its code task, if needed, precedes wave 2.

## 6 Failure modes

- A pattern is taste: item 3's check refuses it; the doc keeps it only as prose with
  `predicate: none` and a reason, and the plan-runs record says how many were cut.
- The 1M window does not reach the seat: the seat reads under 256k and says what it
  skipped; item 5's task lands the pass-through; the docs are regenerated in a fix round.
- The store is unreadable on the host at write time: the writer refuses; nothing is
  committed.
- 244 graph tasks have no first-gate row (never dispatched or docs-only): they are rows
  with `verdict = null` and no exemplar or anti-pattern may cite them.

## 7 Not in this spec

Changes to `plan.js`, the rubric or the judge rule; a DeepSeek judge role; a change to the
dsh harness beyond the environment pass-through; the public-project flip of `withhold`
rows; a generator for other repos' plans.
