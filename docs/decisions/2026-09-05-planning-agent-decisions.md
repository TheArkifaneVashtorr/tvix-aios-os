# Decision — the planning agent's three questions (operator, 2026-09-06 ~00:20 CDT)

**Context.** The planning-agent design draft
(`docs/superpowers/specs/2026-09-05-planning-agent-design.md`, committed
b169fac) closed with three questions. The operator answered in one line:
"1 two Sonnet now, 2 approved, 3 approved after five plans."

## Answers

1. **The judge panel's second family** — two Sonnet judges plus the Opus
   judge now; a DeepSeek judge joins only once the seat unit
   (seat-behind-broker, SB4/SB5) can run a judge job, so the judged text
   travels the same audited route as an implementer's brief. No direct
   headless DeepSeek judge run in the meantime.
2. **The first plan** — Helm Home sub-project 1 is the first plan written
   through the planning agent (as decided on the board at ~23:30). The
   design's own Discord recommendation (a broker lane) is overridden by the
   operator's earlier decision: Discord is a basket, total isolation
   (`2026-09-05-telemetry-store-decisions.md`, answer 7).
3. **The measurement plan** (about twelve seat plan-writing runs and twelve
   panel judgements, of the order of $50) — approved, to run after five real
   plans have gone through the gate so the panel is calibrated first.

Decided in the design's text and not vetoed: the threshold starts at 34 of
42 with the six-row floor and moves only by a commit citing a report line;
the workflow prints launch lines it never runs; the operator model is a repo
file derived only from text the repo already holds.

## Consequences

- The planning-agent plan (when written) carries these three as fixed
  constraints; its judge panel is `sonnet, sonnet, opus` until the seat unit
  lands.
- The first product of the process is the Helm Home sub-project 1 plan; the
  fifth real plan through the gate triggers the measurement plan.
