# The review ladder's depth for code (2026-09-15)

Taken by the orchestrator on the operator's "fix per your recommendations" at the close of session 25, from the measurement recorded in `docs/concepts/2026-09-14a-review-ladder-depth.md` (its `## Decision (2026-09-15)` section carries the numbers).

## Decision 1 — the Opus gate is the code review in `gate = "opus"` areas

For every key whose subsystem row in `docs/ledger/subsystems.toml` says `gate = "opus"` (Isolation, Platform, Helm, Seat/Harness, Factory, Program), the Opus gate runs beside the driver's rung-1 review, on the first pass and on every fix round, launched by the orchestrator from the seat's `.result` with the prior rejecting review as `prior`; both verdicts are recorded and the gate's decides. Docs tasks and `gate = "sonnet"` areas (Evidence, Generation, Knowledge) stay rung-1 only. The routing table keeps its rung-1 row; it is not the gate for code.

Why: nine of nine Opus rejections of code this session sat on rung-1 approves, each on a measured defect.

## Decision 2 — a code section's commit body is generated, never typed

Every code section's commit step prescribes a script that runs each named command and appends its output to the message file, committed with `git commit -F` (the recipe of `### DF8d` in `docs/superpowers/plans/2026-09-11-defects.md`); a typed integer or a paraphrased tail is a record defect by construction. The house standard in `.claude/workflows/batch-plan.js` carries the rule; `SA10` in `docs/superpowers/plans/2026-09-11-seat-harness.md` types the driver-side mechanism (`FACTORY-RECORD`) that makes the seat's paste unnecessary.

Why: DF8 took four rounds on a record that was never wrong in the code — no red, a paraphrase, an invented TAP line — and passed at once when the body was produced by a script.

## Decision 3 — the plan-review rule for probes

A probe asserts the post-state only and never pins a line number; `DF13` types the check that refuses both shapes on open keys. Ten probes failed by construction this session (KN12 ×2, KN13 ×6, HM3, KN17), all plan-side.
