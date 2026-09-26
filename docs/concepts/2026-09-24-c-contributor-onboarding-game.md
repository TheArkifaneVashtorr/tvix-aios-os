# Concept — contributor onboarding: the map, replays, tiers and settled points

**Class:** program / contributor experience
**Status:** parked — clarified with the operator 2026-09-24 (brainstorm, five answers below); no spec until the public Forgejo coordinator is up
**Origin:** the operator, 2026-09-24: onboarding material for the devs that makes the software very easy to understand through abstracted visuals, breaks work down to the level each person enjoys (the way routing breaks it down for models), and gamifies participation, because people who feel useful keep taking part.

**Idea.** In this project agents write the code, so a human contributor is a **steerer and verifier**: the scarce work is judgement, and about 65% of rejections are plan-side, not code. The program has four parts, each built on data the project already records.

1. **The map.** One public page generated from the task graph and the evidence store, not hand-drawn. Subsystems are regions, tasks move spec → plan → seat → gate → main, and open questions are markers. It is generated the way the board is, so it cannot drift. Helm mirrors it later for people running the OS.
2. **Replays.** Settled cases from the record, served as puzzles: "here is a plan section — would it pass, and what is the defect?", "here is a gate verdict — was it right?". The answer is scored instantly against what actually happened. Feedback is fast, and there is nothing to cheat, because every answer was settled before the contributor arrived. Replays also teach the house rubric.
3. **Tiers.** Replay accuracy places a person on a ladder of live work, sized the way `docs/ledger/routing.toml` sizes it for models:
   - Tier 1: read a card and flag what is unclear.
   - Tier 2: judge a plan section against the rubric.
   - Tier 3: find defects in live plans before dispatch.
   - Tier 4: write specs and plans.
4. **Settled points.** Live points arrive only when the record later confirms the contributor: a flagged defect a gate reproduces, a judgement that matched the landed outcome. Points unlock tiers and **never** buy vote weight; the constitution keeps ballots neutral (`2026-09-23-constitution-design.md`, neutral ballots).

**The operator's answers (2026-09-24):**
- Onboarding is built first around the steerer + verifier role. The donor role (unattended, lease-and-verify §5) and hands-on coding are not the target.
- Record-settled points that unlock tiers, rather than activity points, cosmetics, or no score at all. The reason is the credit-attracts-cheating finding (`docs/research-2026-09-23-democratic-os-packet.md`, SETI@home).
- The visuals are a generated public map, not Helm-only and not a hand-made explainer set.
- First contact is replays from the record, not a self-chosen tier or a mentored tour.
- The success metric is the share of plan-side defects caught by contributors before a seat runs, together with the operator's minutes per landed task falling. Onboarding pauses if this does not beat today's baseline after N outside landings (the packet's proposal).

**Payoff.** Engagement is tied to the project's real bottleneck, which is plan quality, instead of to activity. Newcomers get game-speed feedback without a mentor. The evidence store measures the whole program, with no new trust surface to defend.

**Decomposition — three specs, in this order.**
- **A. Replays.** The corpus is drawn from `derived/tasks`, `derived/gates`, the plan-outcomes ledger and the classed plan defects. Scoring runs against the settled outcome, with accuracy per tier. It can be calibrated offline by the operator and the orchestrator before anyone joins.
- **B. Tiers and settled points.** These need membership and identity (constitution Article 4) and the coordinator.
- **C. The map.** It earns its place once there is something to take part in.

**Dependencies.** B and C need the public Forgejo coordinator (`2026-09-23-lease-and-verify-design.md` §3) and constitution membership. A needs neither, but it is parked with the rest by the operator's decision.

**Earliest landing.** When Forgejo is up: spec A through the planning lane, then B and C.
