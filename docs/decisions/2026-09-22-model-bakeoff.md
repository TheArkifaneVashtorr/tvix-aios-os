# 2026-09-22 — the six-arm model bake-off on the pattern documents

## The operator's words

"Have you considered testing any of the models that opened up on openrouter?" and, choosing
the design: the six-arm bake-off on the docs tasks (session 35, ~22:45).

## Why this shape

The store has measured runs for five models only: `deepseek/deepseek-v4-pro-0813`,
`deepseek/deepseek-v4-flash`, `z-ai/glm-5.3`, `moonshotai/kimi-k3` (3 runs) and
`gpt-6-astra` (6). Every other model on the catalogue has none, so any claim about them is
price-sheet reading, not evidence.

Two findings of the same evening set the design. The implementer cross-tab showed a
fourteen-task arm is already too thin to conclude from, so one task per model answers
nothing. And reviewers approve at rates from 43% to 100%, so an arm gated by a different
reviewer measures the reviewer. The pattern plan's six document tasks (PT4–PT9) are the
closest thing this project will have to a controlled comparison: one template, one
acceptance set, six near-identical jobs, all cheap. The precedent is the three-model
plan-writing comparison keyed PW1 (2026-09-05).

## The design

| task | document | model | why |
|---|---|---|---|
| PT4 | facts | `deepseek/deepseek-v4-flash` | **the control**: the incumbent docs implementer, anchoring task difficulty |
| PT5 | interfaces | `deepseek/deepseek-v3.2` | cheapest reasoning model on the catalogue |
| PT6 | steps | `minimax/minimax-m2` | untried entirely, reasoning |
| PT7 | tests | `mistralai/devstral-2512` | agentic-coding branded, no reasoning |
| PT8 | graph | `moonshotai/kimi-k2.7-code` | the goal-2 decision's own pick |
| PT9 | operator-dispatch | `x-ai/grok-4.7` | created 2026-09-21, the newest arm |

Rules that make the result readable:

1. **One reviewer for all six, and it is Opus.** Every gate runs with the reviewer forced to
   the Claude Opus route, never rung 1. Rung 1 approving its own family is how GLM's 94%
   became 90% once self-review was stripped; with six families in play an unpinned gate would
   make the table meaningless.
2. **Explicit route, recorded.** Each arm is a hand launch carrying `--model <id>`, so the
   run's `.result` records the model and the route reads `explicit`. No routing row changes,
   so no open key outside this bake-off is affected.
3. **The control is not special-cased.** PT4 runs the same way as the other five, through the
   same launch shape, so a difference between it and the incumbent's historical rate is itself
   a signal about the harness rather than the model.
4. **Read the outcome, not the prose.** The comparison is first-gate verdict, the defect class
   on a rejection, dollars from the usage ledger and minutes from `wall_s`. The documents'
   content is judged by the same `planning-patterns` check for every arm.

## What it cannot show

Docs tasks are not code tasks: the record has 34 gated docs tasks against 242 code, and a
model that writes a good pattern document may still fail an M-sized Rust task. This bake-off
ranks six models on one task shape at one difficulty. It is a screen for the two or three
worth a code arm later, not a routing decision for `implement/code`.

Six arms of one task each is still n=1 per model. The result is a ranking with wide error
bars, and it is honest only if reported that way: no arm's single verdict is evidence of a
model's ceiling, and a rejection may be the document rather than the model.

## Dependencies

PT4–PT9 depend on PT1, PT2, PT3 and PT10. PT2 and PT3 are dispatched the night of
2026-09-22 alongside OS10b (disjoint touches); PT1 and PT10 wait for OS10b to land, sharing
`docs/ledger/subsystems.toml` and `docs/MAP.md` with it.
