# 2026-09-23 — the running scripts get fixes that save seats; the distributed OS is specced lease-first

Amends `docs/decisions/2026-09-22-freeze-and-triage.md` point 5 ("no further task is
typed to improve" the bash factory).

## The operator's words

"If we can't safely, and that a keyword, efficiently and quickly route workloads to
other people to run on the OS and share those improvements across all the operating
systems then it's kinda pointless to press the OS in my opinion. The dev speed also
requires some levels of coordination that we haven't speced as far as I know." And:
"OS spec is priority to add more people working on the project."

## What was measured before deciding

- **The scripts run all the work for weeks yet.** The only written daemon plan
  (`docs/superpowers/plans/2026-09-22-aios-daemon-dispatch.md`, OS5–OS12) ends at a
  daemon that can run one task by hand (OS5 → OS6 → OS8 → OS9, about 2–10 days at the
  measured pace of 163 landings in 14 days and a 34% first-gate rejection rate). The
  takeover itself (dispatch wiring, the gate, integration, VM placement) is "plan B",
  which is not written. No plan touches `factory-review` or `factory-integrate`.
- **Their defects cost seats on 2026-09-23 alone.** EV21 lost 51 minutes to the guard's
  generic fallback reason (`tools/orchestrator-guard.sh:770-775`). 39 plan sections
  parsed to zero probes (`BUG-probes-blank-line-dropped`), so at least nine tasks were
  gated or landed unprobed. A relaunch line named a task that had already landed (FA35).
- **The panel caught plan-side defects before dispatch.** KN16 scored 18/42, and it
  targets the `AGENTS.md` seats do not read.

## Decided

1. **Fix what wastes seats.** A defect in the running scripts that burned a seat run
   or produced a wrong answer gets a task. Every such fix lands a test that the Rust
   port must also pass, so the fix doubles as the port's spec. Features and refactors
   of the scripts stay frozen.
2. **Under that rule:**
   - FA35 (relaunch line) and FA36 (probe parser) proceed.
   - FA26 (the guard's documented-allow over-refusals) is released. Its stale
     dependency on FA24b moves to the FA24r replan, and both are re-judged inside
     their plan's own sections (the bare-section panel of 2026-09-23 scored
     extraction artifacts).
   - KN16 and OC10 are features and stay held, as the 2026-09-22 triage held them.
   - The fallback-reason defect that killed EV21 gets its own fix task.
3. **The distributed OS is the spec priority, lease-first.** The premise: the OS
   matters only if it can route work to other people's machines and share
   improvements across every copy. The answers taken the same evening:
   - **Safety means all four guarantees.** The contributor's machine is safe from our
     tasks; our code is safe from their results, which stay untrusted until our gate
     re-runs the checks; secrets never leave, so tasks carry public code only and each
     machine brings its own subscription; and improvements are reproducible, signed and
     built from reviewed source.
   - **Merging:** the automated gate lands results on staging, and the operator
     approves promotion to the release every machine picks up.
   - **Routing:** machines pull work, and no machine accepts inbound work.
     Corrected the same evening: "People can volunteer tokens but cannot decide what
     they are used for." The coordinator assigns the next task in the project's
     queue order; a donated machine declines only for lack of capability. Direction
     is democratic: contributors are asked questions through the Helm, and their
     answers steer the queue (the governance spec).
   - **The goal metric** is operator minutes per landed task. More machines must
     push it down.
   - **Specced first:** lease and verify. Coordination, distribution and the
     contributor host follow as their own specs.
4. **Prerequisites for outside contributors,** recorded here, still open: the repo has
   no git remote (never pushed despite `2026-09-22-public-project.md`), `README.md:13-15`
   still describes a local-only repo, and there is no contributor guide.
