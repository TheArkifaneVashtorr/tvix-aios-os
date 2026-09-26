# 2026-09-22 — goal 2 planning begins: two plans, routing unpinned, the run audited

## The operator's words

"begin goal 2 planning. Fun idea, you can throw planning steps into the workflow or audit
etc. As long as you gathering data about it and improving the system. Also don't consider
my openrouter model preferences as set in stone, anything openrouter has available is free
to use as far as I am concerned." (2026-09-22, ~18:00, session 35.)

## What was measured before deciding

- **The spec sequences goal 2 as migration step 4**, after the guard cutover (step 2:
  IS22, IS24, IS25 — released 2026-09-22, IS22 ran ungated, IS24/IS25 blocked) and the
  daemon-dispatch step (step 3, `aiosd-dispatch-differential`), and names goal 2's own
  check `aios-workflow-vm` (`docs/superpowers/specs/2026-09-22-tvix-aios-design.md` §2,
  §8). The spec's planning-scope rule types one plan per step, each after the previous
  step's check is green; §9 demands a measurement of cloud-hypervisor's virtiofs and vsock
  on `core` before the seat guest is typed.
- **The gap** (measured on HEAD 6fc6e17d): no bootable image output exists (`flake.nix`
  has one `nixosConfigurations` entry, `core`; every `*-vm` check is an ephemeral
  `runNixOSTest` fixture); the daemon has only its `declaration` module; the guard crate
  is not landed; the seat, the broker's usage log, the review-and-integrate pipeline and
  the evidence store are all host-only, with no channel from a guest to
  `/var/lib/evidence`.
- **The record's rejection classes** (`evidence tasks brief`, "Record (7 d)"): 171
  rejections, 129 plan-side — missing-case 60, wrong-fact 48, underspecified 12, vacuous
  9. The 2026-09-21 planning-step redesign (score does not gate; touches > 3 need a
  reason; citations by quoted anchor; acceptance names every dependent check) is approved
  and not implemented in `.claude/workflows/plan.js`.
- **What a planning run costs is not recorded**: the `plans` stream carries the fourteen
  judgement fields and nothing else; `gate_tokens` and `wall_s` are null on all 521
  `derived/gates` rows; no stream links a Workflow run to dollars or wall-clock
  (`docs/research-2026-09-17-planning-redesign-packet.md`, "Not measured").
- **Routing evidence** (duckdb over `/var/lib/evidence`, session 35 scout; gates
  windowed on `review_commit_ts`, usage on `ts_epoch` — see the data-quality finding
  below):

  | window | model | runs | done | code done/n | $/done |
  |---|---|---|---|---|---|
  | 30 d | deepseek/deepseek-v4-pro-0813 | 456 | 381 (84%) | 219/280 | $1.73 |
  | 30 d | deepseek/deepseek-v4-flash | 69 | 49 (71%) | 21/26 | $0.22 |
  | 30 d | z-ai/glm-5.3 | 68 | 50 (74%) | 37/49 | $2.87 |
  | 7 d | deepseek/deepseek-v4-pro-0813 | 138 | 88 (64%) | 85/132 | $1.94 |
  | 7 d | z-ai/glm-5.3 | 67 | 49 (73%) | 37/49 | $2.87 |
  | 7 d | deepseek/deepseek-v4-flash | 35 | 22 (63%) | 7/10 | $0.40 |

  Chains approved at the first gate, by implementer: glm-5.3 34/37 (92%),
  deepseek-v4-pro-0813 109/228 (48%), deepseek-v4-flash 27/55 (49%). The only in-store
  Rust evidence is OS2 (the Cargo workspace, glm-5.3, approved by the rung-1 review and
  a parallel Opus gate) and IS22 (the guard differential harness, glm-5.3, done,
  ungated). As a reviewer, glm-5.3 approved 10/10 at rung 1, among them OS1 while its
  `evidence-unit` check failed (`docs/reviews/2026-09-22-sonnet-review-os1-OS1.md`,
  front matter `reviewer-model: z-ai/glm-5.3`) — leniency, not rigor; Opus approves 54%
  first-round over 122 chains. `$/done` divides only the attributed usage subset (15–68%
  of a model's done tasks). Every OpenRouter model outside {deepseek-v4-pro-0813,
  deepseek-v4-flash, z-ai/glm-5.3, kimi-k3 (3 runs), gpt-6-astra (6 runs)} has zero
  measured runs in the store; the catalogue's untried code-branded candidates are
  `moonshotai/kimi-k2.7-code` ($0.71/$3.30 per M, reasoning),
  `qwen/qwen3-coder-plus` ($0.65/$3.25, no reasoning) and `deepseek/deepseek-v3.2`
  ($0.27/$0.40, reasoning). `docs/ledger/openrouter-prices.csv` is stale for glm-5.3
  (csv 0.90/2.85; catalogue 0.654/2.055).

## Decisions

1. **Goal 2 is two plans.** Plan A, `docs/superpowers/plans/2026-09-22-aios-daemon-dispatch.md`,
   types step 3 (the daemon's `workflow`, `scheduler`, `evidence` modules,
   `aiosd-dispatch-differential`, the bash driver as the reference), the §9 measurement
   of cloud-hypervisor virtiofs and vsock on `core` as claim rows, and
   `aios-classification-negative` over a seat's declared inputs (goal 6). It types no
   guest. Plan B types step 4 (`aios.vms`, `aios.seats.<name>.placement.vm`,
   microvm.nix, `aios-workflow-vm`) once the differential has gone red then green and
   the claim rows are filed. Plan A is typed before step 2's check is green on the
   operator's word above; its `dependsOn` on the step-2 keys keeps dispatch honest. The
   spec's §8 carries this as a dated addendum so the drafter reads it.
2. **The OpenRouter models are unpinned; the numbers decide.** `docs/ledger/routing.toml`'s
   rows are the default, not a constraint. Plan A carries one routing question with the
   table above and this recommendation: implement/code stays `z-ai/glm-5.3` high at
   rung 1 (the only Rust evidence, 92% first-gate approval), with one S-sized code task of
   plan A dispatched to an untried candidate (`moonshotai/kimi-k2.7-code`, the closest in
   price and the only code-branded reasoning model) as a controlled trial that fills the
   store's largest collection gap; implement/docs stays `deepseek/deepseek-v4-flash`
   medium; every root key of plan A that touches `pkgs/aiosd` carries `gate="opus"` in
   parallel with rung 1 (the OS2 precedent), because the rung-1 reviewer's 10/10 is
   leniency. The answer lands as routing rows before wave 1 dispatches.
3. **The planning run is instrumented and audited.** `.claude/workflows/plan-audit.js`
   runs the plan skill unchanged as a child workflow, then five lenses named after the
   four defect classes and the redesign's §3.2–3.4 rules, a refuter per lens, a Fable
   revision, a blind re-judge through the same skill, and one record under
   `docs/reviews/plan-runs/` (output tokens per phase, errata proposed and surviving per
   lens, panel total before and after). Which lenses earn a place inside `plan.js` is
   decided from those records after plan A and plan B have run, not before. Dollars and
   wall-clock stay unmeasured until an emitter exists; the Workflow tool exposes output
   tokens only.

## Data-quality finding (for the bug ledger, operator's call)

`derived/gates.jsonl`'s envelope `ts` carries one value, `2026-09-22T02:17:56Z`, on
hundreds of re-ingested rows; window gate rows on `review_commit_ts` (non-null on every
opus/sonnet/deepseek row, null on every glm-5.3 row). `ledger/openrouter-usage.jsonl`'s
envelope `ts` is likewise the ingest time; window on `ts_epoch`, as `seat_stats()` does.
Any rollup that windows either stream on `ts` reads the ingest date, not the event date.

## Not decided here

The implement/code model for plan B; whether the rung-1 reviewer role moves off glm-5.3
(one measured row, OS1, is not a decision); the emitter for plan-run dollars.
