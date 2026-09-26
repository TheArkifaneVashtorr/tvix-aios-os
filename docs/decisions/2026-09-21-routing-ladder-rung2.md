# Decision 2026-09-21 — the docs and XS implement ladders climb by one field per rung, and rung 1 leaves reasoning off

**Status:** adopted by the orchestrator on the operator's word, 2026-09-21,
through the multiple-choice dialog, after the Opus gate on the routing-ladder
fix (`docs/reviews/2026-09-21-opus-review-hand-LADDER.md`, MAJOR 1) put the
choice to the operator. Append-only; supersede with a dated entry if it
changes. Cited by `docs/ledger/routing.toml`'s docs and XS rows and by
`tests/unit/84-routing-ladder.bats`.

## What was measured

- The `implement/docs/any` and `implement/any/XS` rung-2 rows paired
  `z-ai/glm-5.3` with `effort = "off"` since the GLM1 model swap of
  2026-09-19; OpenRouter answers HTTP 400 "Reasoning is mandatory for this
  endpoint and cannot be disabled", and the seat dies in two seconds
  (`~/factory/runs/pgw1b/PG3b.result`, 2026-09-21).
- Flash at `off` (rung 1) failed both docs tasks of 2026-09-21: PG3 pasted no
  probe line and rewrote a byte-exact block in its own words; PG4 delivered
  its own brief as the decision file, no trailers, no mutants
  (`docs/board/log-2026-09.md`, the entry "THE PUBLISH GATE LANDED").
  `z-ai/glm-5.3` at `medium` repaired both (PG3b, PG4b, both Opus-approved;
  `evidence report ladder` lines `openrouter/implement/docs/S/docs-runbook
  z-ai/glm-5.3 medium rung 2` and `…/docs/M/docs-runbook z-ai/glm-5.3 medium
  rung 2`).
- The ladder validator (`tools/factory/route.py`, the adjacency rule at its
  `rungs N→N+1 change model and effort` refusal) allows one field to change
  per rung; with GLM unable to run at `off`, GLM is unreachable at rung 2 from
  a rung 1 at `off`. The first fix (commit 753d714) chose rung 2 = flash at
  `high`, a configuration with no measured run anywhere in the store.

## The decision

For `openrouter/implement/docs/any` and `openrouter/implement/any/XS`:

| rung | model | effort |
|---|---|---|
| 1 | `deepseek/deepseek-v4-flash` | `medium` |
| 2 | `z-ai/glm-5.3` | `medium` |
| 3 | `z-ai/glm-5.3` | `high` |

One field changes per rung; rung 2 is the measured repair configuration; the
cost accepted is reasoning on for every docs and XS task at rung 1. The
`implement/code` ladder keeps the fix's rung 2 (`z-ai/glm-5.3` at `xhigh`,
accepted by the endpoint per `~/factory/runs/pwg2/PW1glm.result`, quality
unmeasured — the claim stays open). The two validator rules the fix added
stand: a reasoning-mandatory model never pairs with `off`; every
`implement` ladder has a rung 2.

## What it changes on the record

- `docs/ledger/claims.toml`: the four `ladder-implement-{docs,xs}-rung{2,3}-unmeasured`
  rows are rewritten to the new shapes by the orchestrator in the commit that
  lands this decision's rows (the operator's ledger; not the builder's).
- `tools/factory/seat/README.md` (the ladder mirror) is rewritten by the same
  fix round that lands the rows.

## Landed, and one side effect

Landed 2026-09-21 as the merge `8693ca0` (the folded commit `f71acbd`), after
the second Opus gate (`docs/reviews/2026-09-21-opus-review-hand-LADDERb.md`,
APPROVED). The fix round also gave the `openrouter/any/any/any` default row a
rung 2 (`z-ai/glm-5.3` at `xhigh`), which the gate names as a behaviour change
for every role that falls through that row: `plan docs S --rung 2` now
resolves to that row instead of escalating; `review` and `orchestrate` still
escalate at rung 2. The claims rows for the four rewritten comparisons and the
two new rung-2 rows (`ladder-implement-code-rung2-unmeasured`,
`ladder-default-rung2-unmeasured`) are in `docs/ledger/claims.toml`.
