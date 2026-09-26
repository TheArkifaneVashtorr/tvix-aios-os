# Concept 2026-09-05b — the evidence bundle replaces the persisted plan

**Class:** process / data. **Status:** planned (docs/superpowers/plans/2026-09-05-evidence-store.md, E1–E9). **Origin:** arXiv 2609.01481 (Harness-of-Harness) via docs/research-2026-09-04-paper-2609.01481.md, and the 2026-09-05 environment review's finding that the board's START HERE contradicted itself.

**Idea.** Two kinds of text have been sharing one file. Facts (what generation is live, which revision each check passed at, which tile is red and since when, which debts are open) and the plan (what is queued, parked, owned). Facts persisted as prose go stale the moment they are written, and appending new blocks on top keeps the stale ones readable. The paper's discipline: the plan is rebuilt every loop from the fixed spec plus an evidence bundle of claims bound to execution records; the plan itself is never carried forward and appended to. Here that means an append-only store on the host (checks observed at a revision with how they were checked, Helm verdict transitions, factory run reports), a claims file in the repo where "verified" is only ever a named check at a revision or an operator drill, and a board that keeps one START HERE block for the plan and prints the facts with a command at session start.

**Payoff.** A fresh session reads one screen and one generated bundle instead of 106 KB of stacked blocks. A tile or a bundle reuses a check that already ran instead of re-running it. A claim cannot be marked verified by prose. A gap past its review date fails the commit hook.

**Dependencies.** Python stdlib only (tomllib, fcntl); one operator switch to create the store and give the Helm units their write path.

**Earliest landing.** Wave 1 (store, factory attribution, ledger path) needs no switch; the tiles and the board follow after the switch.
