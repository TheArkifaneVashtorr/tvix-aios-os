# Concept 2026-09-07a — a named proof shape is not a mutant

**Class:** planning rule (a sharpening of §3 Step 4 / Appendix A question 1 of
`docs/superpowers/specs/2026-09-05-planning-agent-design.md`). **Status:**
landed 2026-09-07 (`1b8d126`: spec §3, rubric row 5 in both copies, Appendix
A Q1, Appendix B row, the judge lens in `judge-prompt.md` and `plan.js`).

**Origin (the bk3 · B1b re-read, 2026-09-07):** the ledger called B1b
`vacuous`; every examples-grounded classifier called it `implementer`. Three
adversarial readers — one told to refute `vacuous` — converged on `vacuous`
(0.70, 0.72, 0.82). The plan's Step 3 named killing mutants for contract items
1 and 2a and none for 2b; it named two *proof shapes* for 2b instead ("a
fixture directory listing in `proton-backup-eval`, or an assertion over the
known lane layout"). The seat satisfied every mutant the plan named and shipped
an `elem` assertion subsumed by the line above it. The mutant that exposes it —
a fourth lane child in modelLane's tmpfiles → `host-core` red naming it —
appeared for the first time in B1c, written by the planner after the gate.

**Idea:** a proof shape says *where* a proof might live; a mutant says *what
turns it red*. Only the second is a falsifier. A contract item whose only
falsifier is a proof shape — or an "or" between two — is decoration as
written, and a seat that satisfies every mutant the section does name has met
the section. The classifier that read "instruction present → implementer" was
not wrong about the text; it was applying the boundary the repo resolves the
other way: **instruction present, mutant absent → plan fault.** That boundary
was unwritten until this turn; it now has a name and four homes.

**Payoff:** the judges score it (rubric row 5's "0 means" and its falsifier
column); the planner is asked it (Appendix A Q1); the gate has the worked row
(Appendix B). A future B1b is caught at the desk, where it costs a sentence,
not at the gate, where it costs a fix round.

**Dependencies:** none landed; the same sharpening belongs in the seat-harness
redesign spec's mutant mechanism (spec §7 Q6–Q7, draft for review) when that
spec is approved.

**Earliest landing:** landed. Next use: the planning agent's next plan is
judged under it.
