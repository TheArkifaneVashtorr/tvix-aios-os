# Research digest — arXiv:2609.01481 (Harness-of-Harness), 2026-09-04

One mapper, one synthesiser, three adversarial verifiers per claim (evidence,
value, feasibility). Five applicability claims were drafted; **one survived**,
and it survived in narrowed form. The four refuted are listed with reasons, as
is the practice for the dsh review.

## 1. The paper

**Harness-of-Harness: Multi-Day Autonomous Software Development with Continual
Improvement.** Yan, Su, Zhang, Li (equal), Zhang, Zhang, Chen, Bai, Hu —
Shanghai AI Laboratory. arXiv:2609.01481v1, 1 Sep 2026. Preprint, not
peer-reviewed.

HoH wraps an existing coding-agent harness (the command-line tool that drives a
model) in a repeated plan → build → QA loop. Three role-scoped invocations of
the *same* harness and model: a Planner that may not write, a Developer that is
the sole writer, and a QA Tester handed a frozen, read-only candidate it cannot
repair (p.9). Two states cross each loop boundary — the artifact, warm-started,
and an evidence bundle partitioned disjointly into verified and gap claims,
each bound to an observed execution record; source presence never counts as
verification (p.6–7, 26–27). The next loop's plan is rebuilt from the fixed
spec plus the last evidence bundle rather than persisted (p.29).

Headline: +52.25% average relative gain at three loops across three
harness-model pairs on three benchmarks (p.1, 11–12).

Evidence strength: better than the genre norm. A pass-controlled arm shows
structure, not tokens, carries the gain (p.13, 45), and single-channel
ablations price plan-update (−8.13), evidence-feedback (−6.28) and warm-start
(−7.85, plus ~32% more tokens) at *lower* token cost than the full system
(p.14, 48). Weaknesses: one run per task-condition, no seed or temperature
control (p.30); partial task sampling (45/140, 15/17); four Performance tasks
score 0.00 in every condition; the 70-loop game is a single deployment with 17
of 81 issues reopened and 16 still open (p.15). **Cite the mechanisms, never
the magnitudes.**

## 2. Applicable — survived verification

### A1 — structure beats extra generic passes; a stale run gets re-planned, not extended

*Pages 13 (Table 2), 34–35 (§B.5), 45.* Extending the same harness with two
more passes on a fixed prompt ("Continue developing and testing the current
game"), each pass starting from the latest artifact but given **no plan
document and no QA evidence**, reaches 58.24 at 6.33M tokens; three structured
loops reach 71.52 at 8.41M. By the paper's own efficiency metric (Eq. 12,
p.36), 3.77 score points per additional million tokens for the structured loop
versus 2.32 for continuation; two structured loops (64.84 at 5.67M) already
beat three continuation passes. Conditions: matched on passes, *not* on token
budget; one benchmark, one harness-model pair; no confidence interval.

**Our component:** the Claude-side dark factory (`tools/factory/dark-factory.js`
— the script that fans agents out into isolated workspaces and collects their
branches) and the budget habit on the board.

**Correction applied — two errors in the draft.** (a) `FIX_ROUNDS` defaults to
**2**, not 1 (`dark-factory.js:73`; docs tasks get 1 at `:458`), and the record
shows that budget is used: wave 1 landed after three rework→fix→approve cycles,
dsh-harness master after four. Cutting it to 1 would have closed those chains
unapproved. (b) Our fix round is **not** the paper's continuation arm: the fix
agent is handed the reviewer's blocker/major findings as JSON (`:484`), so it
sits on the structured side of Table 2. The paper is evidence against unguided
"just keep going", not against an evidence-fed repair pass.

**Proposal (XS).** One board rule, no decision document, no schema work: *a run
that ends unapproved is closed and re-planned, not extended; `fixRounds` is
never raised above 2 within a run.* Bounded rounds, the single integration fix
("there is no second attempt", `:398`) and withholding non-approved branches
from the merge are already enforced in code and already written down in
`docs/decisions/2026-09-04-parallel-agent-workflows.md`; the only residual is a
human typing a bigger number.

**Acceptance (falsifiable, from the return value alone):** a `factory-unit`
case, red first, asserting no chain in a run reports `fixRounds > 2`; and on
the board, every unapproved chain is followed by a plan revision rather than a
rerun with a larger bound.

**Gain:** removes the most tempting wrong move under a tight budget.
**Effort:** XS. **Not proposed:** cost-per-closed-gap. `tools/ledger` records
`task`, `round` and agent `label` as null by schema, so that number cannot be
computed today; claiming it as dated debt would license a measurement the
plumbing cannot produce.

## 3. Not applicable

- Headline magnitudes — different domain, rubric-scored, n=1 per condition; our unit of work is a change to a live host with no score to move.
- One fixed harness+model for all roles — held constant by design (p.30); our model policy assigns roles deliberately and the paper neither tests nor contradicts it.
- Warm-start — we already have it (wave-tip workspaces, fix branches off the implementer's); the ablation confirms the existing design.
- Evaluation isolation (hidden tests, scores never in prompts) — benchmark hygiene against score-gaming; we have no hidden scorer, and our agents should read our checks.
- Unattended multi-day autonomy — the operator switch is a boundary in brief §3, not a bottleneck to remove.
- Domain tooling from the case study (Godot MCP, asset skills, the player-experience instrument) — excluded from the controlled runs, so unmeasured anyway.
- Their token accounting — restricted to within one harness-model pair by cache-accounting differences (p.36); our ledger spans two seats and dsh records no cost (D5).
- The compile/run gate that zeroes the score — a coarser version of `nix flake check` + toplevel build + closure diff.

## 4. Refuted applicability claims

- **P1, evidence bundle as a machine-readable ledger** — the ledger already exists (`docs/reviews/2026-09-04-dsh-debt-measurements.md`, D1–D10, O1–O11, with gaps demonstrably reaching the next plan: D6→N4, D9→N8, D5→O2); the "verdicts read by nothing" defect was dsh-side and is closed (F1); and the writer would be the untrusted party, so a `verified` row is agent prose the next planner is told to trust. Residue: the Claude factory writes nothing to disk — a run-report dump is XS, not M.
- **P2, a separate blinded QA role** — its black-box half is void under the build-only rule (our product boundary is a switched host no agent may reach), the blinding removes the very evidence that caught our defect (a wrong argv pinned in a unit test), and its decisive acceptance test is a tautology: `tests/acceptance/helm-v1.sh:435` already labels step 8 operator judgment.
- **P4, required `preserve` / `acceptance` task fields** — `checks` *is* the preservation gate and is enforced four times (implementer, reviewer, wave integrator, verify); the observable condition already rides in `spec`; and the plan-template assertion would mean rewriting 22 prose plans. Real residual: `validateGraph` accepts a code task with no checks.
- **P5, per-task plan extracts** — the 71.6%/39.9% read figures are dsh-seat measurements of a different script in a different repo; the Claude factory already passes a validated per-task `spec`; and the review already adjudicated this slice (H6 refuted 3-0, "the fix is pass the spec"), which has landed.

## 5. Open questions

- Can an evidence row ever say *verified* without the operator? On a build-only host the strongest agent-side record is a VM check plus a closure diff. This must be settled before any ledger schema is written; it fixes the schema.
- What is the plan-prose share for the **Claude** seat? No measurement exists. `tools/ledger/factory.py` would need a read-result character field. Until then P5-shaped work has no baseline.
- Would `tools/ledger` carrying `task`, `round` and agent label be worth its own task? It is the precondition for every cost-per-outcome claim, including A1's discarded half and O2.
- What is the right loop count when a human gate sits inside the loop? The paper shows gains still accruing at ten loops but 16 issues open at loop 70; our T is bounded by operator attention, not budget.

## 6. Recommendation

- **A1 — adopt now**, as a one-line board rule plus the `fixRounds > 2` unit case. XS.
- **P1 residue (persist the factory return value) — plan.** Cheap, but only after deciding what it is for; do not build a second evidence format.
- **P4 residue (require non-empty `checks` for code tasks) — plan.** XS, red-first, closes a silent degradation to the lint gate.
- **Ledger attribution (`task`/`round`/label) — plan.** Gates several measurements including O2.
- **P2, P5, and every HoH magnitude — ignore.**

**Single best next task — `N12` (nixos-agent-env, XS, code):** in
`tools/factory/dark-factory.js`, refuse a `kind: 'code'` task with an empty or
absent `checks` array in `validateGraph`, and assert no chain reports
`fixRounds > 2`; both cases red-first in `factory-unit`, with the board rule
from A1 landed in the same commit. Check: `factory-unit`, `lint`.

## Provenance note (2026-09-04 18:12, second pass)

The first pass could not parse the reader output for pages 21-40. A resumed run read that slice and re-derived the synthesis and verification: no applicability claim sourced from pages 21-40 survived, and the verifiers refuted the resumed synthesis where it over-reached (a proposal to cut `fixRounds` to 1, a decision document, a cost-per-gap metric), while confirming A1 exactly as filed above. Every claim in this digest therefore rests on a first-hand read of all 157 pages.
