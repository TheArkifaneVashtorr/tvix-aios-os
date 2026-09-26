# Decision 2026-09-15 — the main seat driver runs on Fable 5.1 at extra effort, ultracode off

**Status:** adopted by the orchestrator on the operator's word at the start of
session 26 (2026-09-15 09:50 CDT): "we are going to start running the system
on fable 5.1 extra effort, down from ultracode as the main seat drive". This
entry exists so a retrospective audit can measure the before and the after.
Append-only; supersede with a dated entry if it changes.

## What changes

| axis | before (sessions 22–25) | from session 26 |
|---|---|---|
| main seat driver (this Claude Code context window) | Fable 5.1, **ultracode on** — a Workflow for every substantive task by default (`docs/decisions/2026-09-02-factory-model-policy.md` line 42 records the toggle) | Fable 5.1, **ultracode off**, session effort **extra (xhigh)** |
| when a Workflow runs | by default | only on the operator's explicit opt-in per task (the Workflow tool's own rule) |
| reads, greps, probes, drafts | mostly inside the Workflow's agents | Sonnet/Haiku `Agent` calls returning digests; Fable keeps decisions, the board and commits (the 2026-09-08 rule, unchanged) |

The factory role table (`2026-09-02-factory-model-policy.md`) is untouched:
Sonnet builds, Opus gates, DeepSeek rung 1. Nothing about the seat driver
(`tools/factory/seat/`), its `OPENROUTER_REASONING_EFFORT` axis, or the
review ladder (`2026-09-15-review-ladder-depth.md`) moves.

## Baseline at the moment of the decision

Plan usage as the operator read it from the Claude app, 2026-09-15 09:50 CDT
(the weekly windows reset Monday 02:00):

| pool | used |
|---|---|
| all models | 52 % |
| Fable | 76 % |

For the record of what ultracode cost: the nine-plan batch of 2026-09-11
(session 22) ran the nine parallel fills into the five-hour window; the
2026-09-14 re-judge ran one plan at a time and landed nine of nine. The
71 M cache-read / $35.59 in 41 minutes measurement of 2026-09-08 is the
main-loop read cost that the delegation rule answers.

## How an audit measures it

Compare, per session, from the evidence store and the session log
(`docs/OPERATIONS.md` derived block, `evidence bundle`, the spend rows
once SP2–SP8 land):

- Fable plan usage consumed per session and per landed task (the two
  percentages above are the day-zero reading; the next reading is the
  operator's at the following session start).
- Tasks landed per session, gate verdicts on first pass, fix rounds per key —
  the quality side, so a token saving that costs first-pass approvals shows.
- Workflow launches per session (zero is the expectation now; each one is an
  explicit opt-in and should be named in the session log).
- Decisions typed per session that later needed correction (HM7/HM8 in
  session 25 are the before-side example).

If the after-side shows fewer landed tasks or more fix rounds at the same
token spend, the operator re-decides; ultracode stays available per task.
