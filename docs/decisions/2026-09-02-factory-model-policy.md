# Decision 2026-09-02 — factory model policy (shave Fable tokens)

**Status:** adopted by the orchestrator at the operator's request ("we are
using a ton of fable tokens for development, I was hoping we could shave
those down"). Append-only; supersede with a dated entry if it changes.

## What was happening

Every dark-factory script so far set `model: 'sonnet'` on implementers and
fix agents but **omitted `model` on the review gate, the re-review after each
fix round, and (in the early scripts) the whole-phase verifier**. An omitted
model inherits the orchestrator's model — Fable — at effort `high`. Reviews
read the full diff plus every touched file in full plus the plan, so they are
the largest agents in a run. Measured on the Cowork "Sending…" fix run:

| run | agents | subagent tokens | wall clock | Fable agents |
|---|---|---|---|---|
| wf_6b889b1e (Cowork fix, 5 tasks) | 21 | 1.96 M | 2 h 09 m | 8 review/re-review, 1 verify |

At list prices Fable is $10/$50 per million input/output tokens, Opus 5 is
$5/$25 and Sonnet 5 is $2/$10 (Claude API reference, cached 2026-06-24).
One docs task (T5) took four review rounds and seven agents because a
commit-subject nit was rated "major".

## Policy

Roles and the model that fills them. **Every factory agent names its model
explicitly** — an omitted `model` is a bug, not a default.

| role | model | effort | notes |
|---|---|---|---|
| orchestrator (this session) | Fable | — | plans, specs, gate decisions, reading *summaries*. Delegates file reading/grepping to Explore agents on Haiku/Sonnet instead of paging files into its own context |
| baseline | Sonnet | low | plan committed, lint gate green on HEAD |
| implement / fix | Sonnet | high | unchanged |
| review gate, **code** tasks | Opus | high | adversarial; **max 2 fix rounds**, then the task is reported blocked to the orchestrator instead of looping |
| review gate, **docs / runbook / acceptance-script** tasks | Sonnet | medium | one pass; a fix round only for a *blocker* (a command that cannot run, a wrong path). Style nits are logged, never re-reviewed |
| whole-run verify | Sonnet | medium | mechanical: `nix flake check -L`, toplevel build, `nix store diff-closures` vs `/run/current-system`, commit list. The checks are the gate ("test-based reality"); a reader is not |
| research | Sonnet | medium | unchanged |
| invariant audit (optional) | Fable | high | only for tasks touching basket crypto, the broker, managed settings or the firewall; reads the diff summary against brief §3's six invariants; one agent per run, opt-in via `args.invariantAudit` |

Caps: fix rounds ≤ 2; docs tasks 1 review round; a 4-task plan should close
in ≤ 12 agents. Ultracode being on changes *structure* (workflows by default),
not this table — the models still come from here.

## Mechanism

`tools/factory/dark-factory.js` is the reusable script. A run is
`Workflow({ scriptPath: 'tools/factory/dark-factory.js', args: {...} })`
with the plan path, commit prefix and task list in `args` — the orchestrator
no longer re-authors ~150 lines of factory script per run (Fable *output*
tokens, the most expensive kind).

Every run appends one line to docs/OPERATIONS.md: agents, fix rounds per
task, output tokens (`budget.spent()`), wall clock. Expected effect: Fable's
share of factory tokens drops from roughly half to under a tenth; the
orchestrator's own spend drops with the script authoring and the file paging.

## What this does not change

Phase gates, TDD, the lint gate, the build-only rule, adversarial review for
code. Quality is held by tests and the Opus gate; Fable is spent where
judgment is needed, not on reading diffs.
