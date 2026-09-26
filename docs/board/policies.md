# Standing policies (moved verbatim from docs/OPERATIONS.md on 2026-09-05)

## Standing policy — documentation
docs/superpowers/specs (architecture; one per structural change) · plans (one per
phase, written by orchestrator, executed by factory) · decisions (append-only,
incl. retractions) · concepts (one per turn, dated) · runbooks (operator-facing,
plain language, one command each) · upstream-verification (dated; re-verify any
upstream a phase is about to depend on) · OPERATIONS.md (this board, every turn)
· README (status only). Memory (orchestrator-side) mirrors gate status.

## Standing policy — linting
Two enforcement points, always both: githooks/pre-commit (refuses commits outside
the devShell) and `nix flake check` (sandboxed). Current gate: treefmt (nixfmt +
shfmt + ruff format) · shellcheck · statix · deadnix · ruff check. Rule: a new
language lands WITH its formatter+linter in the same task (Python arrived with
ruff in Phase 2 Task 1). Tests are lint: parity ladder rungs 1-4 run in CI
(= flake check), rung 5 is the operator gate. Candidate addition: markdownlint
(docs-heavy repo, low priority).

## Standing policy — factory economics (2026-09-02, docs/decisions/2026-09-02-factory-model-policy.md)
Fable is the orchestrator only (plans, specs, gate decisions, summaries). In
factories: implement/fix = Sonnet, code review gate = Opus (≤ 2 fix rounds),
docs/runbook review = one Sonnet pass, verify = Sonnet running the mechanical
checks. Every factory agent names its model explicitly — an omitted `model`
inherits Fable. Reusable script: tools/factory/dark-factory.js (Workflow
`scriptPath` + `args`). Every run logs agents / fix rounds / output tokens /
wall clock here. Reference run before the policy: 21 agents, 1.96 M tokens,
2 h 09 m (Cowork fix).

## Standing policy — commit trailers on seat-made commits (2026-09-05)
A seat-made commit carries two trailers, in this order: the machine-set
`Generated-By: dsh … / <model> (seat headless, factory run <run>)` (dsh-harness
F11 — attribution of the tool and model) and the plan's
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` (attribution of the
plan that specified the change). Gates accept both; neither replaces the other.
The `(test: …)` list in a subject holds check names only.
