---
plan: /home/dalhaka/factory/batch/2026-09-11/drafts-r2/2026-09-11-platform.md
spec: docs/concepts/2026-09-09a-redesign-charter.md
author: fable-workflow-revision
effort: high
words: 12200
tasks: 7
judges: [sonnet, sonnet, opus]
judges_dropped: []
scores: [3, 3, 3, 3, 3, 2, 3, 3, 3, 3, 3, 3, 3, 3]
total: 41
self_score: null
threshold: 34
decision: dispatch
revision: 0
---

## Errata

| # | Criterion | Task | Finding | Fix |
|---|---|---|---|---|
| 1 | 3 | PL2 | `lib/patchSeries.nix` gives `readSeries`/`renderPostPatch`/`applySeries` signatures with all three bodies elided; Steps names the Nix builtins to reach for rather than giving the expression — an invention burden this plan does not impose on PL3/PL4, whose bodies are handed over verbatim. | Give the three functions' Nix bodies in full in Files (as PL4's core-patches-wiring already does), or at minimum give the duplicate-number fold verbatim and leave the other two as exercises against the demonstrated pattern. |
| 2 | 3 | PL5 | The `dshHarnessSrc` runCommand's builder script is elided; five nontrivial bash loops (Interfaces 2a, 2b, 3, 4) are described only by their assertions/error text, and the brief expects a shared `dshHarnessBuilder` shell function invokable three times with no sketch of the wiring. | Give the shared-builder-function skeleton and the trickiest loop (the SKILL.md name === directory check) verbatim in Files. |
| 3 | 13 | plan-level | The judge could not `cp -a`/`tar`/`git clone` the live tree into scratch to independently re-run `tasks.py check/conflicts/waves` — this session's own plan-file guard hook refused every copy mechanism even into a private scratch dir. Scored conservatively (2, not 3) for the residual, environment-caused uncertainty. | Not a defect in the draft — a future blind-judging session needs a copy path into scratch the plan-file guard whitelists so this row can be checked mechanically. |
| 4 | 5 | PL2 | Interface 5 (`applyTo`) has no dedicated mutant in PL2's own Tests table (Interfaces 1,2,3,4,6a all have one — 5 is skipped); a mutant dropping the package-name interpolation is not killed until PL3 indirectly exercises it. | Add M8 mutating the `applyTo` binding's interpolation, killed by a probe/eval asserting `applyTo "a" != applyTo "b"` as store-path strings, before PL3 runs. |
| 5 | 6 | PL2 | No interface states the contract for a `readDir` entry of type `symlink`/`unknown` inside a series directory — Interface 2's stray-file throw names "any other entry, including a subdirectory" but not symlinks. | State the rule over every `readDir` type value; add a symlink fixture to a `bad-*` directory and a mutant/fixture pair that would pass if symlinks were silently ignored. |
| 6 | 7 | PL2 | Same gap restated as a boundary-spelling issue: the stray-file rule's coverage of the full `readDir` type space is implicit, not stated. | Reword Interface 2 to cover every non-regular, non-matching entry by type; add the symlink fixture from erratum 5. |
| 7 | 12 | whole plan | 482 lines / 7 tasks has no word-count baseline to check economy against (no second plan for the same spec exists). | When a second implementation exists (or at report time), record a word-count-to-task-map ratio in the plan body. |
| 8 | 6 | PL4 | `patches/` has no top-level rule — `filterAttrs (_: t: t == "directory")` silently skips a mistyped `patches/claude-code.patch` at the top level; PL2 Interface 2's stray rule governs only inside a series directory. | Add `readPackages` throwing on any top-level entry that isn't a directory or `README.md`; wire both `hosts/core/patches.nix` and `core-patches-wiring` through it; add mutant M6 `stray-at-root`. |
| 9 | 6 | PL4 | A `patches/<pkg>` directory with no `applyTo` call site is still rendered into `/etc/helm/patches.json` as a patch the next switch "carries," though nothing applies it — `core-patches-wiring` never asserts every rendered key has a consumer. | Add a `wired = [ "claude-code" ]` list and throw for any rendered key outside it; each later wiring task extends the list; mutant: add `patches/unwired/README.md`. |
| 10 | 10 | PL5 | Rollback paragraph says a rollback "undoes PL4's and PL5's closure," but PL5's flake package/subtree read is never referenced by `nixosConfigurations.core`, so a rollback undoes nothing of PL5 — contradicts `## Operator` step 2. | Rewrite the Rollback sentence to name PL4's closure only; PL5 reverts as a plain commit. |
| 11 | 10 | ## Operator | The rollback generation is never named — step 5 records the new generation only after the switch, not the target to roll back to. | Insert a step before the switch: `readlink /run/current-system` → record as the rollback target; name it in the Rollback paragraph. |
| 12 | 5 | PL3 | Interface 1's permanent proof (`grep -c 'applyTo "claude-code"'`) binds the call but not its object — a mutant applying the series to the wrong package survives both the grep and `apply-check-depends`. | Tighten the probe to the whole binding line; name the wrong-object mutant as M1b with its pasted `0` kill. |
| 13 | 5 | PL7 | Interface 1 checks only that named checks exist, not that the runbook's central command spelling is current (`nix flake lock --update-input` is deprecated vs. `nix flake update`) — this mutant survives every assertion. | Add a red step running each `## Procedure` command in `--help` form to prove the spelling is current; add mutant M5 `stale-verb` and a probe grepping for the current verb. |
| 14 | 8 | ## Dispatch | Cite is off: `factory-wave:150` is the `FACTORY_JOBS` guard, not the default; the literal default `jobs_cap=5` is at `:157`. | Re-anchor to `:157` (or quote `jobs_cap=5` instead of a line number). |

## Judge reasons

### Judge 1 (sonnet)

- Charter-to-task map traces every §2/§6/§8 charter line and cited decision to a task or an explicit "## Not in this plan" bullet with an owner named; siblings, harness payload, ledger, Helm view all accounted for.
- Spot-re-ran 8 cited commands against the live tree — all reproduced exactly, zero wrong facts found.
- Ran `factory-brief` on PL2, PL5, PL7 as a blind implementer: PL7 fully landable from the brief alone; PL2/PL5 give exhaustive Interfaces but elide implementation bodies, inconsistent with PL3/PL4's verbatim standard.
- Every task carries an explicit Red step with exact expected failing output, then a named Green re-run.
- Each interface maps to a named mutant with an exact kill signature; discriminating fixtures named per row; explicit negative controls.
- Producer/consumer contracts pinned exactly (throw text, argument order, JSON shape, drvPath-equality); absent/empty-directory and re-applied-patch behavior stated.
- Boundaries stated as regexes/structural rules and enforced by throwing guards rather than left to a driver's discretion.
- "## Waves" shows actual `tasks.py waves --json` output; "## Cross-plan" runs `conflicts` and states a published cross-plan order; touches are explicit file lists.
- G12 binds all six brief §3 invariants to named tasks rather than a blanket assertion.
- Each Operator step is one command with expected output; a dedicated Rollback paragraph names which tasks revert as plain commits vs. `git revert -m 1`.
- Anticipation section supplies the switch delta, claims to close, a reserved relaunch task, and explicitly notes non-applicable triggers.
- No section restates another; Global Constraints and Assumptions appear once and are referenced by ID.
- Plan structurally matches what `tasks.py` expects; A5's guard replay and pasted `waves`/`conflicts` JSON are reported, but the judge could not independently re-run `check/waves/conflicts` on a scratch copy because the plan-file guard hook refused every copy mechanism — scored conservatively for that residual uncertainty.
- Exactly three operator questions, each bounded with a reasoned recommendation; five further decisions demoted to assumptions with the same bound/assumed/veto-surface structure.

### Judge 2 (sonnet)

- Every charter item for Platform maps to a PL task or an explicit out (node2/node3 to A25, harness payload/ledger/Helm view to cross-plan pointers); nothing found dropped.
- Re-ran far more cited commands than required (check count, uncovered-line list, areas count, sibling measurements, waves JSON, conflicts breakdown) — all reproduced exactly, zero wrong facts.
- `factory-brief` on PL2/PL5 (plus PL7's prose) hands an implementer exact throw-message strings, regexes, shell fragments, file lists, and probe commands — function bodies given as precise contracts rather than literal Nix in PL2's three exports, a minor gap.
- Every task's Steps opens with a Red step naming the exact expected failure, closing green by check name; double/triple-red sequences where a naive first fix still leaves a second red.
- Mutant coverage dense (4-7 per task); found survivors: PL2 Interface 5's `applyTo` binding has no dedicated mutant, and the symlink arm of the stray-file rule is never fixtured or mutated.
- Interfaces state exact producer/exit/stdout contracts almost everywhere; gap: the `readDir` symlink/unknown type arm is not addressed.
- Touches are exact file lists; waves derived and pasted, reproduced byte-identically on independent re-run; conflicts output reproduced exactly.
- G12 explicitly binds all six invariants to this plan's tasks; A10 confirms no broker-wiring line touched.
- Operator section gives seven numbered commands with expected output, the switch closure, and an explicit Rollback paragraph naming which tasks revert how.
- Anticipation instantiates every applicable §4 row (switch delta, claims to close, prepared relaunch, bounded questions, explicit non-applicability of the hook/deny-rule table).
- 482 lines for seven substantial tasks with 25 prior errata folded in is dense but not confirmably repetitive; without a comparable clean plan for the same spec, economy can't be confirmed, scored conservatively.
- On a scratch copy with the draft placed alongside the other tracked plans, `tasks.py check` exits 0 and `waves`/`conflicts` reproduce the plan's pasted numbers exactly.
- Exactly three operator questions, each bounded to what its last sentence changes, with a stated recommendation and effect; five further decisions stated as assumed-with-recommendation rather than silently baked in.

### Judge 3 (opus)

- Every Platform line of the charter is mapped, including a vacuous-answer case declared on a re-run measurement (`git -C ~/flakes/dsh-harness ls-files | grep -cx 'flake\.\(nix\|lock\)'` → 0).
- Zero wrong facts across roughly 15 re-run commands (check window count, areas count, plan-file listing, claude-code-pkg binding line, stale pin comment, dsh-harness file/skill counts, subsystems validate output, task states, runbook count, helm profile imports, six-key greps, byte-faithful G1-G12 quote including its inherited stale cite).
- `factory-brief` on PL4 printed the module body and the full `core-patches-wiring` expression verbatim with exact reds, greens, mutants and a control; PL1/PL3/PL6/PL7 hold the same standard; PL2/PL5 stop at signatures plus exact throw messages and fixture recipes rather than Nix bodies.
- Every task opens with a Red step naming the exact expected failure and closes green by check name; PL2 and PL5 carry multi-red sequences; PL3's red is a deliberately non-applying temporary patch declared not in touches.
- Each task ends with a Mutants step (4-7 named mutants, fixtures, negative control); PL4's self-testing arm and PL2's enum-complete fixtures are strong; survivors named: the wrong-package-object mutant and PL7's procedure-verb mutant (see errata).
- Strong on producers/enum arms/failure output (exact throw text, empty/absent-directory behavior, exit-line contracts); but the `patches/` top level has no rule at all, and a wired-but-unconsumed patch directory is never asserted against — two arms where a guard can never fire.
- Boundaries are rules, not spellings, almost everywhere; refusals live in code reachable through host eval, not sentences a driver is trusted to honor.
- Waves reproduced byte for byte on a scratch copy; conflicts reproduced exactly for both invocation forms the draft cites; touches are exhaustive file lists, no globs; cross-plan publishes an order on every shared file.
- brief §3 is quoted verbatim as G12 with a Platform-specific binding; no task touches basket mounting, a credential, the broker, or promotes code between baskets; no task widens an agent's reach.
- The Operator drill is seven numbered commands with expected output each; two defects found: the Rollback paragraph's overreaching claim about PL5, and the unnamed rollback generation (both filed as errata).
- Every applicable §4 row has its artefact (dispatch lines, switch-delta step, reserved relaunch task, named claims to close, bounded questions, an explicit non-applicability statement); plan also anticipates its own probe drift with re-measurable bounds.
- 12,200 words for seven tasks against a 25,824-word program plan — inside 3x, no appendix; the one large restatement (Global Constraints) is mechanically forced and cited; cross-references are pointers, not repeats.
- On the scratch copy, `check` exits 0, `waves --json` reproduces the pasted list, `conflicts` runs clean, `parse_plan` reads all seven tasks typed with populated fields and no probe errors; commit subjects match the required format; no typed heading found under the live plans glob.
- Exactly three operator questions with lettered options, grounded recommendations, and explicit effects; five further questions demoted to assumptions with the same structure, none hidden inside a task body.
