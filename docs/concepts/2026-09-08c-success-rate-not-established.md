# Has the success rate moved? — not established (2026-09-08)

The operator's question at 15:20: "As we have introduced better guardrails
and more structured expectations, has the success rate moved in a meaningful
way?" Answered from the review corpus (213 `docs/reviews/*-opus-review-*.md`),
the defect ledger, the seat result files and git history, by one script and
four independent readers (Workflow `wf_62f54899-41c`: a recount, a guardrail
timeline, a rejection-cause classification, an Opus skeptic). This note keeps
the numbers and the conclusion; the readers' full returns are in the session
transcript.

## The headline rate did not move outside noise

First-round landing share of roots landed, by the day of the root's first
gate (a root is a task key with its fix-round suffixes stripped):

| day | roots landed | round 1 | round 2 | 3+ | first-round share |
|---|---|---|---|---|---|
| 09-05 | 57 | 25 | 22 | 10 | 44 % |
| 09-06 | 12 | 5 | 6 | 1 | 42 % |
| 09-07 | 13 | 4 | 8 | 1 | 31 % |
| 09-08 | 16 | 9 | 7 | 0 (in flight: OG3 at round 3) | 56 % |

Non-monotone; every Wilson 95 % interval overlaps every other; Fisher exact
09-05 vs 09-08 p = 0.41. Two of 09-08's nine round-1 landings (CX2, SB5) had a
first round that died before any gate; counting those as round 2 gives 44 %,
identical to 09-05. Gates per landed root (1.91 → 2.08 → 1.77 → 1.62) is a
censoring effect: a day still running cannot yet have grown a 3+ tail, and
09-05's tail (ten roots, CR2 alone eight gates) is 35 % of that day's gates.

The day is the wrong unit. Gates cluster by plan (about two plans a day) and
the between-plan spread of first-round share is 83 points (effort-comparison
100 %, seat-harness 67 %, seat-driver 50 %, seat-routing 20 %, telemetry-1
17 %) against a 25-point day-to-day spread. 09-07's low is one plan.

## What did move, measurably

- **The plans.** Mutant mentions per task section stepped from 0.0–1.4 in every
  09-04/09-05 plan to 5.4–12.0 in every plan from the planning agent
  (2026-09-06) on — about 10×. Across the twelve plans with four or more landed
  roots, that density correlates −0.07 with first-round landing share.
- **The work per task.** Median insertions per seat run 155 → 596 → 1071 → 478;
  median seat wall 7.8 → 13.8 → 33.0 → 26.9 min. The size label barely moved
  (S share 69 % → 78 %), so the label does not track magnitude. The same
  first-round share on tasks three to seven times larger is the one reading
  that favours the guardrails, and it is not a rate.
- **What rejections are about.** Of the rejections read: 09-05 — 18 vacuous or
  untestable tests, 16 untested arms, 10 seat substance bugs of 48; 09-08 —
  2 vacuous, 3 untested, 3 plan wrong-facts, 2 seat substance bugs of 11.
  Vacuous tests, the 09-05 signature, are nearly gone; the residual is facts
  pasted into plans without running them (today: SD1, OG3b, SD11b — all mine).
- **Detection.** The driver's vocabulary (`error_class`, `checks_verified`,
  `touches_extra`, `unreported`) exists only from 09-07 (SB7, SH3, SH4, SH5);
  09-05's zero partial/unreported runs are the instrument's absence, not
  cleanliness. On the one case both instruments ran (SB6b) the gate caught the
  same defect, so the driver's catch changed the record, not the round count.
- **The labelling instrument.** The ledger was created 09-06 and back-filled;
  per-review front matter began 09-07; the plan-class vs implementer tie-break
  rule changed 09-07 15:18. The vacuous → implementer shift in the ledger rides
  partly on those changes.
- **The gate itself** is unversioned (`~/factory/bin/opus-gate.js`, outside git,
  edited today) and two models (Opus for code, Sonnet for docs; every file is
  named `opus-review`). From today the review front matter carries `model:`.

## What "success rate" should mean here

Rounds-to-land per root, with the root's life cycle closed, rounds counting
attempts that died before a gate, and the plan as the unit — not the day.
Two natural experiments already span days inside one plan: seat-behind-broker
(SB1 1, SB2 3, SB3 2, SB4 1, SB7 2, SB5 1, SB6 2 rounds — no trend) and
seat-harness (SH1 1, SH2 1, SH3 3, SH4 1, SH5 2, SH6 1). The harness report
(SH1) and the ladder report (SD9) group by class, model and rung; a
by-plan, rounds-to-land-per-closed-root view is the owed measurement, and it
needs the pre-gate deaths recorded as rounds (`~/factory/runs/<run>/<KEY>.result`
with `FACTORY-COMMITS 0`, and withdrawn roots such as SB5/SB6).

## Conclusion

Not established. The plans' proof content and the driver's detection moved by
an order of magnitude and are real; the first-round landing rate is flat
within noise on tasks that grew several-fold; the ledger's class shift is
partly the ledger changing. Until the by-plan rounds-to-land view exists, the
honest claim is "same rate, much larger tasks, failures now named and caught
earlier", not "the rate went up".
