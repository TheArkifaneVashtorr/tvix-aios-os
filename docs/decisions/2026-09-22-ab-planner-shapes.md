# 2026-09-22 — the A/B of the two planner shapes: the single drafter's plan is released

## The operator's words

On being offered a recommendation between the two plans: "I mean perform a cost/time
analysis and find out what is better." (2026-09-22, session 35.) The A/B itself was the
operator's call earlier the same evening, after asking whether plan scope is why plans
fail and proposing "essential specialized planners" modelled on how human teams pass
information.

## What was measured

Two plans exist for the same spec section (`docs/superpowers/specs/2026-09-22-tvix-aios-design.md`
§8 step 3), written by two shapes, judged by the same blind panel and audited by the same
five lenses:

| | single drafter (`plan-audit.js`) | team (`plan-team.js`) |
|---|---|---|
| plan | `2026-09-22-aios-daemon-dispatch.md` | `2026-09-22-aios-daemon-dispatch-team.md` |
| tasks | 8 (OS5–OS12) | 11 (AD1–AD11) |
| named contracts between tasks | none | 14 (C1–C14) |
| bytes | 331,124 | 1,079,602 |
| touches, largest task | 19 | 6 |
| first panel | 39/42 | 40/42 |
| audit errata proposed / surviving | 24 / 12 | 37 / 14 |
| re-judge after the audit | 38/42 | never ran (spend limit) |
| planning agents / output tokens | 26 / 3.56 M | 72 / 13.47 M |

**The approval curve, re-measured at fine grain** (n=276 root tasks, first gate,
all-time; `derived/gates` windowed on `review_commit_ts`, the envelope `ts` being the
ingest time):

| touches | 1–2 | 3–4 | 5–6 | 7–9 | 10–14 | 15+ |
|---|---|---|---|---|---|---|
| first-gate approval | 68% | 57% | 48% | 54% | 54% | 50% |
| n | 91 | 84 | 52 | 28 | 13 | 8 |

The decline stops at five or six touches and flattens near 50% out to 27 touches; a
single-predictor logistic fit gives a coefficient of −0.041 (p=0.21, not significant).
The earlier 77%/53% finding of `docs/superpowers/specs/2026-09-21-planning-step-redesign-design.md`
holds at the low end and does not extend past it. **A task above five touches is a coin
flip whatever its size, so splitting a large task into more tasks buys no approval odds.**
A rejected task costs 1.57 further gate rounds on average (median 1); 7.8% never approve.

**Execution prices** (per seat run, priced from billed tokens × the catalogue, the live
GLM rate 0.654/2.055 rather than the stale sheet): M $1.147, S $0.692, XS $0.145 at the
historical model mix; GLM 5.3, the routed implementer, runs 3.4× that. Durations: M 43
min, S 27, XS 19. Measured wave concurrency across 75 clean waves is 2, and wall-clock
equals the sum of run times — waves do not in fact run to the cap.

| | single drafter | team |
|---|---|---|
| expected seat runs, incl. fix rounds | 13.4 | 18.6 |
| expected seat spend, historical mix | $12 | $15 |
| expected seat spend, GLM rates | $38 | $48 |
| seat-hours, serial (as measured) | 8.2 | 10.4 |
| seat-hours, full wave parallelism | 5.2 | 4.8 |
| Opus gate reviews | 8 | 11 |

## Decisions

1. **OS5–OS12 are released; AD1–AD11 are withdrawn.** The single drafter's plan expects
   5.2 fewer seat runs, costs 22–25% less on either price basis, needs three fewer Opus
   gates, and is two hours faster at the concurrency the record actually shows. Both plan
   files and both run records stay in the tree as the A/B's evidence.
2. **The team shape is not adopted as the default planner, and not discarded.** It
   produced a marginally better-scored plan for 3.8× the planning tokens, and its one
   claimed advantage — smaller tasks — is worth nothing under the flattened curve. Its
   roles that demonstrably caught defects before any judge (the facts clerk, the
   implementer dry run) are candidates to fold into `plan-audit.js`, decided from the
   run records rather than from this one comparison.
3. **The plan-side lever is task count, not task size.** A plan that can do the work in
   fewer tasks is cheaper at equal odds. This replaces "split until touches ≤ 3" as the
   drafting rule; `.claude/workflows/plan-team.js`'s `maxTouches` default stays only as a
   prompt for a written reason, never as a splitting mandate.

## What this cannot settle

Whether the team plan's explicit contracts and resolved dry-run stops raise approval above
what touches predicts: nothing in the record measures plan quality independently of
touches, and the touches slope itself is not significant. The gate's own cost is
unmeasured — `gate_tokens` and `wall_s` are null on all 587 rows and Opus reviews run
outside the broker, so the three extra reviews the team plan needs are priced at zero
here and are not zero. The first-gate approval rate of OS5–OS12 is the next measurement
and tests the curve's prediction directly.
