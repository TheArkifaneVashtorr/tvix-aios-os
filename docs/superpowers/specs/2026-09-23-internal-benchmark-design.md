# The internal benchmark — design

**Status:** draft, 2026-09-23. Measured on core at generation 83.

## 1. Why ours, and not a public one

Two ways of ranking models are available and both fail here, for the same
reason.

**Public benchmarks cannot be joined.** The unit of analysis is the model, and
`derived/tasks` holds outcome rows for **five**: `deepseek-v4-pro-0813` (456
tasks), `z-ai/glm-5.3` (77), `deepseek-v4-flash` (70), `gpt-6-astra` (6),
`moonshotai/kimi-k3` (3). A correlation over five points needs r ≈ 0.88 to
clear p < 0.05, and two of the five have so few tasks that their own rates are
noise. There is also no source: OpenRouter publishes prices and context, not
scores.

**Production outcomes cannot rank cleanly.** The natural dependent variable is
first-gate approval, and it varies by *reviewer* — with the reviewer
identities the ingest currently drops restored, `opus` 58.0% (n=324), `glm`
90.3% (n=31), `deepseek` 71.5% (n=144), `sonnet` 74.1% (n=27) — and by
whatever the model happened to be assigned. Self-review inflates one model and
not another: deepseek's self-reviews approve 13 points above its other
reviewers, glm's do not. A model's production rate is a measurement of its
work, its judge and its luck, entangled.

So the instrument has to be built: a fixed battery, held constant while the
model varies.

## 2. The control property

The benchmark is a control in two senses, and both must hold or it is worth
nothing.

**Difficulty is fixed.** Every model runs the same tasks from the same briefs
at the same effort on the same lane. A score difference is then attributable to
the model rather than to what it drew.

**Scoring is reviewer-free.** This is the binding constraint. A suite scored by
a judge measures the judge across every arm — the defect the four-family panel
was designed to avoid, and the one the reviewer spread above demonstrates. So
every task must pass or fail on its own evidence: a differential harness
proving row-for-row equivalence, a check exiting 0 or 1, and **mutants killed
over mutants planted**.

The mutant ratio deserves emphasis because it is already collected and already
discriminates: `gpt-6-astra` 32/32, `z-ai/glm-5.3` 108/121, `deepseek-v4-flash`
104/129, `deepseek-v4-pro-0813` 1,493/1,762. Today those numbers are not
comparable across models, because each task's mutants were planted by whoever
wrote its section and differ in difficulty. Inside a **fixed** suite the
mutants are fixed too, and the ratio becomes a real score. That is much of the
argument for a suite at all.

## 3. Composition

Small enough to re-run per model per version; broad enough that the score
generalises beyond one kind of work. These pull against each other and the
tension is the design's central judgement, not something to resolve by
assertion.

Two consequences follow:

- **The suite's domain is what it predicts.** An all-Rust battery predicts Rust
  ports and says nothing about a runbook. Given goal 2 is a Rust OS, Rust
  belongs in it — but a suite that is only Rust must be described as a Rust
  benchmark, never as a capability score.
- **Per-task verdicts, not one aggregate.** A single number hides which kind of
  work a model is good at, which is the question a routing floor actually asks.

OS5's shape is the natural first task: a bounded port with a differential
harness that proves equivalence and passes or fails without an opinion.

## 4. Identity and versioning

A score belongs to a **served model identity** — the id the provider reported,
plus `provider` — never to a requested name. `z-ai/glm-5.3` carries no date and
a provider may move what it points at; when it does, the accumulated score is
invalidated rather than extended, and the invalidation is itself recorded.

This makes the benchmark the instrument that answers a question production data
cannot: *did capability change when the identity did?*

## 5. Triggers

Explicit, never continuous. A run happens when a candidate has no score, or
when a served identity changes under a name we route to. Each run costs a model
call per task, so the suite is a measurement taken deliberately, not a cron job.

## 6. What it unlocks, in order

1. **Comparable scores across models**, including models never used in
   production — which is how n grows past five without waiting for work.
2. **A version instrument**, per §4.
3. **A ground truth for public benchmarks.** Once enough models carry an
   internal score, that score becomes the dependent variable and public
   benchmarks become candidate predictors. Then the question "which public
   benchmark predicts performance on our roles" is answerable, and candidates
   can be pre-screened cheaply instead of every one being run. This is the
   payoff, and it is only reachable through §6.1.

## 7. Limits, stated plainly

- **Saturation.** A fixed suite gets easier as models improve; a score at
  ceiling stops discriminating and the suite needs replacing, which resets
  comparability.
- **Training overlap.** Public-shaped tasks may be memorised. Tasks drawn from
  this repository's own work are less exposed, and that is a reason to prefer
  them over synthetic ones.
- **Domain specificity** (§3).
- **Cost.** Model × version × task, paid on every re-run.
- **It is not production.** A model that scores well on bounded tasks with
  objective verdicts may still fail at long-horizon agentic work — which is
  precisely the failure `moonshotai/kimi-k3` showed here (1 done of 3,
  "produced nothing twice"). The benchmark predicts what it measures.

## 8. Acceptance

- Every task in the suite yields a verdict with no reviewer in the path;
  a task whose verdict depends on a judgement is refused by a check.
- The same model run twice on the same snapshot produces the same verdicts, or
  the variance is measured and reported with the score.
- Scores key on served identity; a changed identity invalidates rather than
  extends, asserted by a negative case.
- Per-task verdicts are retained, not just an aggregate.
- A model with no score is distinguishable from a model that scored zero.

## 9. Not in this design

The suite's contents beyond the first task's shape. Any automatic routing
action taken on a score — that belongs to
[model cards](2026-09-23-model-cards-design.md), which consume this as one of
two sources, the other being production outcomes with their very different
error properties. Acquiring public benchmark data, which is §6.3 and needs
§6.1 first.
