# The GLM plan as a seat provider — design

**Status:** WITHDRAWN 2026-09-23 evening, before planning. The operator: glm-5.3
through OpenRouter is cheap enough, and the Z.ai subscription is being
cancelled. Kept as the record of what a direct-provider seat would need.
Operator answers taken earlier the same day: the endpoint through the broker (no
ZCode), Z.ai for public repos only, this design.

## 1. The premise

glm-5.3 is the house implementer: 79 seat runs in seven days, 58 done, about
$2.72 per done task, all billed per token through OpenRouter (session 37 brief).
The operator also holds a Z.ai GLM subscription. It has two API endpoints,
OpenAI-shaped `https://api.z.ai/api/coding/paas/v4` and Anthropic-shaped
`https://api.z.ai/api/anthropic`. Both take an API key and cover glm-5.3, with a
quota counted in prompts per 5 hours plus a weekly ceiling rather than in tokens
(web research, 2026-09-23, not yet measured here). If one seat run costs few
enough prompts, a quota the operator already pays for replaces per-token spend.

The vendor's desktop client, ZCode, is not part of this design. It is a GUI with
no documented headless mode, and a reported 2026 incident had it uploading whole
workspaces, `.git` included. The seat talks to the endpoint directly, through
the broker, like every other upstream.

Nothing in the tree names Z.ai today: `grep -rn -i 'api.z.ai\|zhipu'` finds
nothing.

## 2. What exists

- **The broker.** `nixosModules/seatLane.nix:260-296` builds the `seat` broker
  instance for one upstream, `cfg.host` (default `openrouter.ai`). It has an
  exact-host allowlist (`:262`, pinned by the assertion at `:132-135`), key
  injection (`inject.${cfg.host}.valueFile`, `:263`, key file outside the
  store), a zero-data-retention body patch (`:269-283`) and a denied Anthropic
  path (`:284-288`). The seat process holds only the placeholder
  `OPENROUTER_API_KEY=injected-by-broker` (`:350`).
- **The launcher.** `pkgs/dsh-openrouter/dsh-openrouter.sh` speaks
  `openai-completions` only (`:725`), with the base URL from
  `OPENROUTER_BASE_URL` (`:247`) and the model from `--model` (`:88-89`).
  `--broker` mode proves it is running inside the broker's namespace
  (`:309-421`).
- **Selection.** `tools/factory/route.py:48` fixes `ROUTES` as a closed tuple.
  The one alternative harness that shipped, Codex, is not a route row but an
  arm: `FACTORY_SEAT=codex` in `tools/factory/seat/factory-task:301-351`.
- **Spend.** `pkgs/evidence/ingest_openrouter_usage.py` reads the broker's
  `usage.jsonl` into `ledger/openrouter-usage`. That stream measures cost and
  tokens (`pkgs/evidence/streams.py:561-580`) and has no quota notion.

## 3. The design

**3.1 Shape.** The seat speaks the OpenAI-shaped endpoint. The launcher already
speaks nothing else, so Z.ai costs a base URL, a model id and a key placeholder,
not a second protocol. The Anthropic-shaped endpoint stays unused.

**3.2 The broker admits Z.ai, and the key never reaches the seat.** The Z.ai key
lives at `/var/lib/secrets/zai-key` (placed by the operator, outside the store,
asserted like the OpenRouter key). The broker injects it on requests to
`api.z.ai`. The seat sees only a placeholder. Every Z.ai request is logged to the
same chokepoint as OpenRouter's (brief §3 invariants 2 and 3).

**3.3 Public repos only, enforced by the network.** Z.ai offers no known
zero-data-retention control, so it may see only what is already public. The
invariant: **a task on a repo not declared public runs in a namespace whose
broker does not admit `api.z.ai`.** The set of public repos is declared in Nix
(invariant 5: the data-class policy is config, reviewable in a diff), and today
it is this repo alone. A check at launch alone is not enough, because a subverted
seat could still reach any host its broker admits. The plan measures whether
`seatLane` can carry a second instance (a `seat-zai` lane admitting only
`api.z.ai`) or needs another shape. The acceptance test binds only the
invariant.

**3.4 Selection is an arm.** `FACTORY_SEAT=zai` at launch, following the Codex
precedent, with no change to `route.py`'s route list. The arm refuses to start
when the task's repo is not in the declared public set. The refusal is a
one-line message naming the repo, and the check does not stand in for 3.3.

**3.5 The quota is measured before anything else.** The first task measures
only: one real seat task runs through the Z.ai lane, and the broker log gives
its request count against the plan's prompt quota. The number is compared with
the same task class's OpenRouter cost per done task from the evidence store. It
goes into the plan's record, and the operator decides whether Z.ai becomes a
default for any class. Until that number exists, no route defaults to Z.ai.

**3.6 Accounting.** Z.ai requests land in the evidence store as per-request rows
(instance, task attribution, status, tokens when the response carries them)
with no `cost_usd`. The quota is a count, not a price, and forcing it into cost
fields would corrupt the spend rollups. The exact stream shape is the plan's
choice, provided the SP-series rollups never add Z.ai rows into a dollar sum.

**3.7 When the quota runs out.** A quota refusal from Z.ai ends the task with
its own error class, distinct from `budget-402`. The operator relaunches the
task on OpenRouter. There is no automatic fallback across providers in this
version: `route.py`'s `fallback` stays within one route (`:260-263`), and
changing that is out of scope.

## 4. Operator steps

1. Place the Z.ai plan key at `/var/lib/secrets/zai-key` (root-owned, 0400).
2. Switch after the lane tasks land, then run the acceptance script.
3. Read the quota measurement (3.5) and decide on defaults.

## 5. Acceptance

- A seat on this repo with `FACTORY_SEAT=zai` finishes one task through the
  broker, and the broker log shows its requests to `api.z.ai` with the key
  injected. `/proc/<pid>/environ` of the seat holds no key.
- A task on a repo outside the declared public set: the arm refuses at launch,
  and a direct request to `api.z.ai` from that task's namespace is refused by
  its broker (the negative test for 3.3).
- The Nix assertion fails the build when `api.z.ai` is admitted to a lane that
  can run a non-public repo.
- The quota measurement (3.5) is written to the plan's record as a number, with
  the OpenRouter comparison beside it.
- No `ledger/openrouter-usage` dollar rollup changes when Z.ai rows are present.

## 6. Not in this design

- ZCode, in any form.
- Z.ai's Anthropic-shaped endpoint.
- Automatic fallback from Z.ai to OpenRouter, or quota-aware routing.
- Making Z.ai a default route for any class (that waits for the 3.5 number and
  the operator's word).
- Private repos on Z.ai.
