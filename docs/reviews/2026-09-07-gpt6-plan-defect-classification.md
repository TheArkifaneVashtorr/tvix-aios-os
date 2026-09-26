# GPT-6-Astra vs the `plan_defect` ledger — a routing probe

**Question.** Could the OpenAI models, reached through the Codex CLI on the
flat ChatGPT subscription, take over `plan_defect` classification — mundane,
high-volume, and already schema-constrained — freeing the OpenRouter key and
Opus for judgement work? A new `route` value in `docs/ledger/routing.toml`
would need evidence of the kind its header already cites.

**Answer: no.** Best configuration reaches 67 % (6/9) primary-label
agreement, and every attempt to improve it made it worse. Do not add a route
row for this task.

## Method

Ground truth is `docs/ledger/plan-defects.toml` — 65 rejections, each with an
Opus-assigned `plan_defect` and a path to the review that justified it. All
65 review files exist; median 17.7 KB.

Classification ran as `codex exec` (0.153.4, `-m gpt-6-astra`,
`model_reasoning_effort=high`, `--sandbox read-only`) with
`--output-schema` pinning the six-value enum, so the label is enforced by
schema rather than trusted from prose — the same discipline
`tools/lane/jobs/findings-classify.sh` uses.

### Leaks found and closed

Three, and they are the reusable part of this document:

1. **Front matter.** Reviews filed after task P3 carry `plan_defect:` in YAML
   front matter (e.g. `2026-09-07-opus-review-tel1b-T1.md`). Stripped.
2. **Body lines.** `P6` and `P4` carry a literal `plan_defect: …` line in the
   body. Stripped by line match, not just front matter.
3. **Appendix B prose.** `docs/superpowers/specs/2026-09-05-planning-agent-design.md`
   Appendix B is a *table* of 43 labelled rows, but §7 and the ledger's own
   seed comment name `sc5 · G12` and `oi1 · DA1` **in prose**. A regex over
   table rows alone does not hold them out. G12 was sampled before this was
   noticed and had to be voided — its rationale read *"Appendix B explicitly
   classifies sc5 · G12 as implementer-primary."* The model disclosed the
   leak; the harness did not catch it.

Held out by construction: the 22 rows filed after Appendix B, less G12 and
DA1 = 20 usable. Nine were used to iterate, eleven kept untouched.

## Results

| run | grounding given to the model | tuned-on (9) | fresh (11) |
|---|---|---|---|
| 1 | Appendix B's 43 worked examples, no written rules | **6/9 = 67 %** | — |
| 2 | glossary v1 — tie-break "would exact compliance have prevented it?" | 4/9 = 44 % | — |
| 3 | glossary v2 — tie-break "implementer is the residual class" | 3/9 = 33 % | 5/11 = 45 % |

Run 3 overall: 8/20 = 40 %.

**Examples beat rules.** Two hand-written rule sets, each defensible and each
derived from the corpus, both degraded accuracy below the few-shot baseline,
and they failed in opposite directions — v1 pulled labels toward
`implementer` (P2, P4), v2 pulled them toward `vacuous` (P10, T3, T1, T1W,
T2).

**Confidence carries no signal.** Run 1 mean confidence was 0.96 on misses
against 0.97 on hits. There is no low-confidence tail to escalate, which
removes the obvious hybrid (cheap model labels, Opus adjudicates the unsure
ones).

**Secondary labels were the strong point.** Where the ledger records a
secondary, run 1 matched 4 of 5 exactly (P2, P3Ab, P10, T3). The model finds
the contributing defect reliably even when it disputes the primary.

**Comprehension was never the failure.** Rationales cite specific MAJOR
findings accurately. Two of run 1's three misses are defensible readings:
`CR2r3` was answered `missing-case`, which is *the ledger's own secondary for
that row*; `P6` was answered `vacuous` with the argument that the 13-score
test "still passes without the count check because its mismatched total
independently triggers rejection" — a textbook vacuity argument.

## What this says about the ledger, not the model

Three competent rule sets produce three different label distributions over
the same reviews. The taxonomy has an enum (§7) and 43 worked examples
(Appendix B) but **no written definitions**, and the two boundaries that
absorb most of the disagreement — `vacuous`/`implementer` and
`missing-case`/`underspecified` — are exactly the two nowhere defined.

This bears on `gates.plan_defect` as a *metric*. The planning-agent design
tracks "plan-caused share of rejections … 42/59 = 71 %" against a "< 40 %"
target. If a capable judge holding explicit definitions cannot reproduce the
existing labels better than two in three, that series carries more noise than
a 40 % threshold implies. Worth a consistency pass — two independent
relabellings of the same rows — before the number gates anything.

One concrete inconsistency surfaced: `P4`'s own review body records
`plan_defect: wrong-size`, a value **not in the enum**; the ledger records
`wrong-fact`.

## Cost

39 classifications at roughly 30 k tokens each, ≈ 1.2 M tokens, on the flat
ChatGPT subscription — nil at the margin against the OpenRouter key. The
economics were never the obstacle; the accuracy is.

## Recommendation

1. **No `routing.toml` row** for `plan_defect` classification.
2. The label stays with the Opus gate.
3. If the flat-rate capacity is to be used, point it at work whose output is
   mechanically checkable and whose vocabulary is concrete — extraction
   ("list each MAJOR and what it requires") rather than adjudication. This
   probe gives no evidence for or against that; it would need its own.
4. Independent of routing: give `plan_defect` written definitions, then
   re-measure inter-rater agreement among the existing labels.

## Reproducing

Corpus extraction, leak stripping, both glossaries, the schema and the
scoring scripts were run from a session scratchpad and are not committed.
The method above is sufficient to rebuild them; the only subtle step is leak
class 3, which a table-only regex will miss.

## Addendum, 2026-09-07 later — definitions cannot be fit from this corpus; examples of `implementer` can

Recommendation 4 above ("give `plan_defect` written definitions") is
withdrawn. It was tested and it fails for a reason in the data, not the
model.

**Fitting definitions.** Four Sonnet builders each derived a glossary from
Appendix B alone by a different strategy (contrastive pairs, ordered decision
tree, marker lexicon, minimal description length), under a sealed-test rule:
no ledger, no review dated 2026-09-06/07. Each reproduced the 43 training rows
by its own account. Scored on the 20 sealed rows with the glossary in place of
the appendix:

| glossary | 6-way | plan-vs-implementer | rows called `vacuous` (ledger: 1) |
|---|---|---|---|
| contrastive | 9/20 = 45 % | 13/20 | 8 |
| decision tree | 6/20 = 30 % | 11/20 | 11 |
| marker lexicon | 9/20 = 45 % | 14/20 | 8 |
| minimal | 5/20 = 25 % | 13/20 | 15 |
| baseline (appendix as examples) | 15/20 = 75 % | 18/20 | — |

Every fitted rule set collapses `implementer` into `vacuous`. The cause is
the training set: Appendix B is 42 plan-primary rows plus one `process` row —
**zero `implementer` rows** — while eleven of the twenty sealed rows are
`implementer`. No rule fit to that table can learn the one boundary the test
set is mostly made of. The two hand-written glossaries in the main text
failed the same way, from the same cause.

**Adding the missing class as examples.** Leave-one-out: each sealed row was
classified with the run-1 prompt plus a block of the ledger's *other*
`implementer` rows, each as `run · key | implementer | <review summary>`
(mechanically extracted; the row under test never appears in its own
examples).

| grounding | 6-way | plan-vs-implementer | fresh 11 |
|---|---|---|---|
| appendix examples | 15/20 = 75 % | 18/20 = 90 % | 9/11 · 10/11 |
| appendix + `implementer` examples (LOO) | **16/20 = 80 %** | **19/20 = 95 %** | **10/11 · 11/11** |

All eleven `implementer` rows correct. One row better than baseline — at
n = 20 that is direction, not significance. Standing six-way misses: B1b, P6,
CR2r3, P3Ar2b, the same boundary disputes as before.

**B1b is the row to re-read, not the model.** Ledger: `vacuous`. Every
examples-grounded run (three) said `implementer`; the four `vacuous`-leaning
glossaries said `vacuous`, as they did for 8–15 of 20. When the only
configurations that agree with a label are the ones that over-predict it,
the label is the suspect. That re-read is an operator-class act (ground
truth) and the one thing in this document that is theirs.

**Revised recommendations.**

1. No `routing.toml` row — unchanged.
2. Do not write definitions. Give the classifier, and the next judge, worked
   examples of `implementer`. The ledger's eleven rows and their reviews are
   the source; the example block is generated from them (summary paragraph
   per review) and lives prompt-side. Appendix B stays as written.
3. The harness has one honest use: a label-consistency auditor. Run it over
   the ledger; rows where the examples-grounded classifier disagrees are
   re-read candidates. B1b is the first.
4. `pkgs/evidence/streams.py:438` (`factory-finding.class` typed `("null",
   "id")`, raised by the candidate survey) is **not** a defect: the plan's
   own contract at `docs/superpowers/plans/2026-09-06-telemetry-store-1.md:312`
   declares it so. Withdrawn.

Cost of the addendum: 100 further classifications (≈ 3 M flat-rate tokens)
and ≈ 320 k Sonnet tokens for the four derivations.
