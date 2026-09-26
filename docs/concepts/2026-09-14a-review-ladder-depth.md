# Concept 2026-09-14a — declare the review ladder's depth

**Class:** routing-ledger amendment (one `docs/ledger/routing.toml` row, or a one-line terminus marker on the existing row; not a program charter, no spec size).

**Status:** proposed 2026-09-14, session 24, during the first dispatch after the batch landing (HM1 on run hm3).

**Origin:** the read of the review procedure (`tools/factory/seat/factory-review`) before gating HM1.

**Idea:** `routing.toml:106-113` carries exactly one `role = "review"` row (openrouter, all fields any, no `rung` so rung 1, `deepseek-v4-pro-0813` medium) — confirmed by direct read; implement ladders run three rungs (`:30/:41/:52` docs, `:61/:72/:83` XS) or two (`:92/:103` code), and `tools/factory/seat/README.md:554` shows review's ladder as the same one line.

The rung comes from the KEY: `factory-lib.sh:846-864` `factory_rung_of_key` (no suffix → 1, non-`r` suffix → 2, `r` suffix → 3). Correction: the ladder walk and cross-route escalate check live in `factory_route` (`factory-lib.sh:758-813`), not in `factory-review` as first drafted.

`factory-review:101` only requests the rung, and `:134-136` fires `factory_review_escalate` (`:35-54`, writes `<KEY>.escalate`) on the exit-4 branch. Net effect: any fix-round key (rung 2) finds no rung-2 review row and escalates to `claude/review` unconditionally.

Evidence: `ls ~/factory/runs/*/*.escalate` → **13** files, all `role: review`, all `rung: 2`. Correction to the draft claim: not all are `b`-suffixed — 7 end `b`, 4 end `c`, 2 end `d`; all share only a non-`r` suffix (rung 2), not the letter `b`.

Decision check: `docs/decisions/2026-09-09-redesign-answers.md:144-147` ("`FA1`'s `docs-spec` and `docs-plan-run` claude rows move from rung 1 to rung 3") is decision 28's rung-3 terminus, not `:126-129` as first drafted — corrected.

Grepping that file and `docs/context/factory.md` for `review`+`rung` finds only that terminus and a future graph-runner's rung mechanics (decisions 26/27) — no line states review's own depth as a decision, so it is fall-through, not a choice.

`routing.toml:17-18`'s row-change rule: "a row above rung 1 exists only with a claims row until the report justifies it" — so a rung-2 openrouter review row (a second DeepSeek pass, `--prior` the rejecting review, ~$0.5) or a `terminus = "claude/review"` marker on the rung-1 row turns the 13-escalation backlog into a measured, priced choice instead of a table gap.

**Payoff:** the escalation count becomes something the routing table predicts, so the orchestrator's Opus/Sonnet gate load per wave is known before dispatch rather than discovered in `~/factory/runs/*.escalate`.

**Dependencies:** grepped every `**touches:**` line in `docs/superpowers/plans/2026-09-11-seat-harness.md` — none names `docs/ledger/routing.toml` or `tools/factory/seat/factory-review`. The row is unowned by that plan.

**Earliest landing:** as a one-row measured change once a fix-round review has been run both ways (DeepSeek rung 2 vs the current Opus escalation) and the two verdicts compared against the integrate outcome; no SA task gates it.

## Decision (2026-09-15)

Measured in session 25 (the fourteen-task wave, seventeen Opus gates, `docs/reviews/2026-09-15-opus-review-*.md`): every Opus rejection of a code task sat on a rung-1 DeepSeek approve — DF7, DF8, HM4, HM6 at the first pass and DF7b, DF8b, DF8c, HM4b, HM6b after — nine of nine; no rung-1 review rejected a task the gate then approved except DF9 (a commit-body red pasted green, a record defect). The rejections were measured defects: an untested declared arm, a subprocess called bare, a mutant alive in the sandbox, a section's own wrong-fact, a fabricated TAP line. So: **for every key in a subsystem whose manifest row says `gate = "opus"`, the Opus gate is the code review and runs beside the rung-1 review, launched by the orchestrator from the seat's `.result` (base, head, subject, acceptance, touches) with the prior rejecting review as `prior` on fix rounds; both verdicts are recorded, the gate's decides.** Docs tasks and `gate = "sonnet"` areas stay rung-1 only. The routing table is not changed: the rung-1 row stays because it is cheap (10–15 min on the lane), catches record defects, and produces the paired data the ladder gaps (`ladder-*-unmeasured`) need. Cost measured: 17 gates ≈ 3 M Claude tokens, 10–30 min each, for a wave of fourteen. Revisit when `evidence report ladder` prints rung-2 lines at n ≥ 5 with a first-gate fraction beside rung 1's (the gaps' review-by is 2026-09-20).
