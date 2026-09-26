# Decision 2026-09-16 — session 28 runs on Fable 5.1 at high effort, low-Fable-token mode, planning runs held

**Status:** adopted by the orchestrator on the operator's word at the start of
session 28 (2026-09-16 10:26 CDT): "Fable 5.1 high effort for this run,
please document this. We are continuing to run in low fable token use mode
via agent use and summarization via agent calls. Please continue on any
unfinished plans. Do not dispatch any planning agents and hold them in the
queue. You may unhold any previously held plans other than planning step
plans." Append-only; supersede with a dated entry if it changes. Extends
`2026-09-15-seat-driver-effort.md` (sessions 26–27: extra/xhigh).

## What changes

| axis | sessions 26–27 | session 28 |
|---|---|---|
| main seat driver (this Claude Code context window) | Fable 5.1, ultracode off, effort **extra (xhigh)** | Fable 5.1, ultracode off, effort **high** |
| reads, greps, probes, digests | Sonnet/Haiku `Agent` calls returning digests | unchanged, and the rule is restated: every read of more than a screen goes to an agent; Fable keeps decisions, the board and commits |
| planning runs (`docs-plan-run` keys: PLAN-FA, PLAN-PL, PLAN-SA; the batch-plan / context-blocks / gather / loose-ends / plan skills) | dispatchable when ready | **held in the queue** — not dispatched this session; the derived queue still lists them as ready because the hold is an operator word, not a manifest state |
| implementation keys previously held on the operator's word | held | **unheld** — anything not a planning run may dispatch |

Nothing else moves: the factory role table (`2026-09-02-factory-model-policy.md`),
the seat driver's own `OPENROUTER_REASONING_EFFORT` axis, and the review
ladder (`2026-09-15-review-ladder-depth.md`) are untouched.

## Baseline at the moment of the decision

Live generation 62 (`f2ddcb6`), HEAD `36c0ede` docs-only ahead, no seat
running, `nix flake check -L` green at `fa985e3` (session 27). The operator
did not read plan-usage percentages at this session start; the 2026-09-15
reading (all 52 %, Fable 76 %, reset Monday 02:00) stands as the prior
point. Queue at start: 15 ready keys in nixos-agent-env (three of them the
held planning runs), 3 in media, 22 blocked, 28 rung-2 escalations.

## How an audit measures it

Same measures as the 2026-09-15 entry, with one added column: effort level
per session (xhigh vs high), so the three readings — ultracode (≤ session
25), xhigh (26–27), high (28) — can be compared on tasks landed per session,
first-pass gate verdicts, fix rounds per key and Fable plan-usage consumed.
The `effort-policy-n1` claim (`docs/ledger/claims.toml`, review by
2026-09-19) is about the seat driver's effort axis, not this one, and is not
closed by this entry.

## Reading at close (2026-09-17 01:10 CDT, appended)

Session 28 ran 10:26 to 01:10 at effort high with zero Workflow launches.
Measures for the audit table above (the operator's plan-usage percentages
are theirs to add at the next session start):

| measure | session 28 |
|---|---|
| keys landed | 31 across two repos (GN10 the last, switch #38) |
| gates filed | 32 (Opus for code, Sonnet for docs) |
| first-pass gate approvals | 18 of 31 root or fix-round keys |
| rejections → fix rounds | 13; 11 fix rounds approved on their first gate, 2 needed a second |
| rung-1 vs Opus splits | 8 rung-1 approves the Opus gate rejected; 0 the other way |
| orchestrator decisions later corrected | 6 (the piped integrator, the duplicate HM8c, four plan wrong-facts) |
| switches | 2 (#37 gen 63, #38 gen 64), both with acceptance green |

Compare with session 27 (xhigh): two touch chains landed in one night, 11
Opus rejections. The quality side did not move against the token saving
that is visible in this session's agent-delegated reads; the operator
re-decides on the plan-usage reading.
