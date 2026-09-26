# Decision 2026-09-17 — session 29 runs on Fable 5.1 at medium effort, low-Fable-token mode, planning runs still held

**Status:** adopted by the orchestrator on the operator's word at the start of
session 29 (2026-09-17): "This session running in fable 5.1 medium, please
document this. Continue with the media and any additional projects that can
be launched. Continue to operate using agents to preserve fable tokens."
Clarified minutes later, after the first launch was refused: "no plans at
this time — plans are held until otherwise noted." Append-only; supersede
with a dated entry if it changes. Extends `2026-09-16-session-effort-high.md`
(session 28: high) and `2026-09-15-seat-driver-effort.md` (sessions 26–27:
extra/xhigh).

## What changes

| axis | session 28 | session 29 |
|---|---|---|
| main seat driver (this Claude Code context window) | Fable 5.1, ultracode off, effort **high** | Fable 5.1, ultracode off, effort **medium** |
| reads, greps, probes, digests | Sonnet/Haiku `Agent` calls returning digests | unchanged: every read of more than a screen goes to an agent; Fable keeps decisions, the board and commits |
| planning runs (PLAN-FA, PLAN-PL, PLAN-SA; the batch-plan / context-blocks / gather / loose-ends / plan skills) | held in the queue | **still held**, restated by the operator on 2026-09-17; the derived queue keeps listing them as ready because the hold is an operator word, not a manifest state |
| implementation keys | unheld | unheld in principle; the first six-key launch of the session (GN11, FA16, HM10, PL4, PL7, SA4) was refused at the tool prompt and awaits the operator's explicit go |

Nothing else moves: the factory role table, the seat driver's own
`OPENROUTER_REASONING_EFFORT` axis, and the review ladder are untouched.

## Baseline at the moment of the decision

Live generation 64 (`ac81435`, switch #38), HEAD `6dfa917` docs-only ahead,
`nix flake check -L` green at `7ddab8d`, no seat running, no gate in
flight. Queue at start (nixos-agent-env): ready GN11, FA16, HM10, PL4, PL7,
SA4 plus the three held planning runs; media has no undispatched key of its
own (GN11/GN12 live in this repo's generation plan; GN12 is blocked on
GN11). `tasks.py conflicts` reports GN11, PL4 and SA4 sharing `flake.nix`;
`tasks.py waves` still groups them as one parallel group.

## How an audit measures it

Same measures and the same table as the 2026-09-16 entry, with the effort
column extended: ultracode (≤ 25), xhigh (26–27), high (28), medium (29).
Compare tasks landed per session, first-pass gate verdicts, fix rounds per
key, orchestrator decisions later corrected, and Fable plan-usage consumed.
A "Reading at close" section is appended when the session ends.
