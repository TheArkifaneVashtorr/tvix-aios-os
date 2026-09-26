# Model cards and the routing frontier — design

**Status:** draft, 2026-09-23. Measured on core at generation 83.

## 1. The problem, measured

Every model choice in this project has been made by hand-reading review files
against a static price sheet. `docs/reviews/2026-09-05-model-comparison.md`
tabulated five reviews and `docs/ledger/openrouter-prices.csv` by hand;
`routing.toml`'s own change-log comments cite narrative ("DeepSeek pro
wrote-but-never-committed twice"); `docs/decisions/2026-09-22-model-bakeoff.md`
is store-*aware* but its design is a manual launch plan. No query against
`derived/tasks`, `derived/gates` or `ledger/openrouter-usage` has ever decided
a routing row.

Three failures on a single day, 2026-09-23, show what that costs:

- **"Is this model the one that ran?"** could not be answered. The store's
  usage `model` is response-reported (`pkgs/broker/policy.py:267`, from the
  parsed response frame, alongside `gen_id` and `provider`), but
  `derived/tasks.model` is the id we *asked for*
  (`tools/factory/seat/factory-task:1221`). Nothing joins or reconciles them,
  so a silent provider substitution would be invisible to every aggregate.
- **A model was chosen on price and context and was the wrong tier.**
  `openai/gpt-6-luna-pro` ranked first on the only two facts the pricing
  endpoint exposes — $0.10/$0.50 per million, 1.05M context. Its vendor's
  description says "positioned below GPT-6 Sol … suited for high-volume and
  latency-sensitive workloads such as chat, classification, and lightweight
  agentic". Caught by the operator before dispatch, not by any check.
- **A judge's leniency was invisible — and so, for most rows, was the judge.**
  First-gate approval by reviewer family *as stored* in `derived/gates` reads
  `opus` 55.0% (n=149) against `glm` 87.5% (n=16), with 398 of 566 rows
  `unknown`. That table is mostly an ingest artifact: 358 of the 398 unknown
  identities are already on disk and the ingest fails to read them (§6). With
  them restored the same comparison is `opus` 58.0% (n=324) against `glm`
  90.3% (n=31). The gap survives and widens; the sample sizes it was resting on
  did not exist.

A fourth is latent: `routing.toml` carries no date on any row.

Seven model ids also appear outside it (`dsh-openrouter.sh`, `helm.nix`,
`lanes.nix`, `modelLane.nix`, `seatLane.nix`, `route.py`), and a first draft of
this spec called consolidating them a prerequisite. Measured site by site, **none
of them is a routing decision**: two are UI defaults for the operator's own
`dsh-openrouter` picker (one listing ids no route ever names), two are option
defaults for launches the operator triggers by hand — each diverging from the
nearest routing row on `effort`, so they are independent knobs rather than
copies — one is a doc-string example, one is the seat broker's ZDR exception
allowlist, and one is model-capability metadata (`REASONING_MANDATORY_MODELS`).
Folding any of them into `routing.toml` would make it lie about what it routes.
The roster check reads the router; the other sites are out of its scope by
kind, not by oversight.

## 2. What a card is

One document per **served model identity**, with three parts kept separate
because they have different truth conditions:

**Identity.** The id the provider reported serving, its `provider`, and the
window of `gen_id`s the card covers. Not the requested id. A card is scoped to
a snapshot: `deepseek-v4-pro-0813` carries its date, `z-ai/glm-5.3` does not,
and a name whose target moves silently must invalidate rather than extend the
record (§5).

**Upstream facts.** Context window, price in and out, modality, and — the
lesson above — a **tier or positioning** field, sourced from the provider's own
description string. Price and context alone actively mis-rank; this field is
what separates a classification tier from a reasoning tier.

**Measured record.** From this project's own store, on the four axes: cost per
**approved** task, first-gate approval rate, wall time to land, and capability
headroom. Never cost per token and never cost per run — a cheap model needing
three rounds is not cheap, and the Pro-vs-Flash comparison already turned on
exactly that.

Every measured number carries its window and its n. A card with n=1 must look
like a card with n=1 — the deepseek reviewer row has exactly one gate.

## 3. Floors filter, the record ranks

A route declares a **floor**: the hard requirements it can state honestly —
minimum context window, price ceiling, tier, tool-calling. Floors filter the
candidate set from the roster. Among survivors, the measured record ranks, and
the useful answer is not a winner but the **non-dominated set** on the four
axes. "Which model is best" has no answer; "which models are not dominated"
usually has three or four, and a route picks a point by its own weighting.

Floors are hand-written and therefore wrong eventually, so each carries a
`review_by` date and goes stale loudly, exactly as `claims.toml` rows already
do (`pkgs/evidence/claims.py:77-85`).

This is the only way an unrun model is ever considered: it can clear a floor on
facts alone, which admits it as a candidate; the record then decides adoption.

## 4. What refuses, what reports

A check fails the build on exactly two things, both facts:

1. A routing row naming a model that violates its route's declared floor.
2. A routing row naming a model the upstream roster no longer carries — a
   retired id fails at dispatch today, silently, which is the failure this
   whole thread began from.

Everything judgemental is a report you read. Ranking does not refuse; a
dominated model on the frontier is a question, not an error.

## 5. Identity is not stable, and the card must know it

A measurement belongs to a snapshot, not a name. The card's identity key is the
**served** id plus `provider`; when what a name resolves to changes, the
accumulated record for that name is invalidated rather than extended, and the
change itself is a recordable event. That is the mechanism that would have
caught a reroute automatically, whichever way the question turns out.

Two store hazards any aggregate must respect, both measured today:

- **Window on `ts_epoch`, never on `ts`.** The envelope `ts` is the ingest
  time, rewritten on every `replace_stream` merge; windowing on it made a
  two-week stream look like seventeen hours and manufactured a truncation that
  had not happened.
- **`ingest_openrouter_usage.py` logs `len(rows)`** — source lines read — not
  `replace_stream`'s merged total, so the ingest log can never show shrinkage.

## 6. What is blocked before a per-class card is possible

`derived/tasks` carries `model`, `kind`, `size` and `route` but **no `class`**;
the routing taxonomy's classes live only on raw `.result` files on disk.
`area` is on the row but populated on 20 of 610. So "glm-5.3 overall" is
answerable today and "glm-5.3 on Rust" is not, and there is no `rust` class in
`CLASSES` (`tools/factory/route.py:52-65`) at all — the taxonomy is
Nix/Python/Bash/JS/docs-shaped while goal 2 is a Rust OS.

Ingesting `class` and adding a `rust` class are prerequisites for the
per-class frontier, and they are separate tasks from this one.

**The approval axis needs the reviewer identities first, then an adjustment.**
Measured 2026-09-23: 358 of 398 `reviewer = unknown` gate rows are recoverable
from facts already on disk. The docs route never falls back from `reviewer` to
the `model` field its own stored row carries (200 rows), and the seat route
scans only three header lines while all 159 seat review files name their model
in an older banner line. Forty rows are genuinely lost. That fix is a
prerequisite, and it changes what the adjustment has to do:

- The confound is **not** total separation. With identities restored, `opus`
  reviewed glm 13 times and `glm` reviewed deepseek 10 times, so the design is
  thin but identifiable.
- **Stratify, never pool.** Report approval per (model, reviewer) cell; show a
  cell below about 13 rows as counts, not a rate.
- The one like-for-like comparison available today is a shared reviewer: under
  `opus`, deepseek-v4-pro 56.7% (169/298) against glm-5.3 84.6% (11/13) — glm's
  n flagged as thin.
- **Self-review is model-specific, not universal.** deepseek's self-reviews
  approve 70.8% against 57.8% from other reviewers (both n > 100 — real);
  glm's do not inflate at all (88.9% self against 92.0% other).
- A regression with reviewer as a covariate is identifiable but not causal:
  reviewer assignment is not randomised and may track task size, area or
  period. Adjusted cell means, not a coefficient with a p-value.

A figure previously cited here — "GLM's 94% became 90% once self-review was
stripped", from `docs/decisions/2026-09-22-model-bakeoff.md` — **cannot be
reproduced from the store** under any definition tried, partly because
seat-route gate rows carry no event timestamp at all, so the store cannot be
windowed back to when it was computed. It is not cited as evidence here, and
a figure that cannot be recomputed by a command should not be cited anywhere.

## 7. The measured record has two sources

A card's measured half comes from two places with very different error
properties, and they must be reported separately rather than averaged.

**Production outcomes** — what the model did on real tasks. Large n for the
models we route to, but entangled: first-gate approval varies by reviewer
(§6), by what the model was assigned, and by the plan's own quality.

**Benchmark scores** — the fixed battery specified in
[the internal benchmark](2026-09-23-internal-benchmark-design.md): the same
tasks, the same briefs, reviewer-free verdicts, keyed to a served identity and
re-run when that identity changes. Small n by construction, but clean, and
available for models never used in production — which is the only way a
candidate gets a number at all.

Operator's decision, against harvesting real tasks for this: Rust competence in
particular is measured by that suite, re-run per model *version*, because a
version-specific claim needs the same difficulty every time.

A card that shows only one source is misleading in a predictable direction:
production-only over-credits whatever the lenient reviewers approved,
benchmark-only over-credits models that do well on bounded tasks and fail at
long-horizon work.

## 8. Acceptance

- A card exists per served model identity, carrying identity, upstream facts
  (tier included) and the measured record with windows and n.
- A routing row violating its floor fails the build; so does one naming an id
  absent from the roster. Both are asserted with a negative case.
- A floor past its `review_by` fails, the way a stale claim does.
- The frontier report names the non-dominated set and the axis each dominated
  model loses on.
- Aggregates window on `ts_epoch`; a fixture with misleading `ts` values proves
  it.
- A served id differing from its requested id is counted and excluded from
  ranking rather than silently averaged in.

## 9. Not in this design

Automatic route selection — the card informs a routing row, a person changes
it; the A/B discipline depends on the model being a fixed, named variable.
Ingesting `class` (EV22), adding a `rust` class (FA33) and restoring the
reviewer identities the ingest drops (EV21): prerequisites, each its own task.
Consolidating the hard-coded model ids is not one (§1). The
Rust suite's contents. Any change to the bake-off already decided.
