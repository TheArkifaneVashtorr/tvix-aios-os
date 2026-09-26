# Decision 2026-09-03 — a second remote model endpoint (OpenRouter → DeepSeek V4 Flash) for `permitted` data; the cheap model does Tier B work only

**Decided by the operator, 2026-09-03** ("we need to get an OpenRouter API
token to let DeepSeek V4 Flash handle that summary, data collect,
deterministic task work"; then, to the assessment's §9.2: "understood …
let's use some DeepSeek agents for the tasks going forward, whatever you feel
is appropriate"). Recorded by the orchestrator with the scope it recommended.

1. **Recipient.** OpenRouter (`openrouter.ai`, the only host) routing to
   DeepSeek V4 Flash (`deepseek/deepseek-v4-flash`, dated snapshot) is a
   permitted remote endpoint alongside Anthropic. Every request carries
   `provider: { zdr: true, data_collection: "deny" }`; the account's
   zero-data-retention toggle for the Non-frontier group and the training
   opt-out are set. Digest: `docs/research-2026-09-03-openrouter-deepseek.md`.
2. **Data that may reach it:** content classed `permitted` — this repo, the
   flakes under `~/flakes`, their factory transcripts and journals, eval
   seeds and results, rollups. **Never:** Claude memory directories,
   baskets, `~/strategy` economics and income data, Helm history, broker
   audit logs, backup state (all `local-only`).
3. **Path:** only through the egress broker instance `openrouter` (allowlist
   of one host, audit of every request), with the key injected by the broker
   from `/var/lib/secrets/openrouter-key` (`0440 root:egress-broker`, set by
   the lane module's tmpfiles rule). The key's vault of record is Proton
   Pass. No agent, script or lane process ever holds it (brief §3
   invariants 2 and 3).
4. **What the cheap model does:** Tier B of the data-and-models assessment
   (`docs/superpowers/specs/2026-09-03-data-and-models-system-design.md` §6):
   summaries, classification, drafts, triage, research sweeps over public
   pages, and large-context whole-repo coherence reviews. Deterministic
   collection and rollups stay scripts. Tier C seats (Fable plans and judges
   gates; Opus reviews code; Sonnet implements) change only on
   proving-grounds evidence; the first such experiment is a `deepseek`
   implementer arm on the NixOS-skill eval seeds.
5. **Not yet active.** The lane needs a switch (broker instance + unit
   template); it lands with wiring round 2. Until then no DeepSeek agent runs.

## Addendum 2026-09-03 (operator): free model use in exchange for our data is an acceptable exception, chosen per job

The operator: "people using our data if they allow for free model use is an
exception. We will just need to keep that in mind as a choice." Recorded as:

- **Default unchanged:** every lane request carries `provider.zdr = true` and
  `provider.data_collection = "deny"`.
- **Explicit opt-in, per job:** a job may set `dataPolicy = "free-training-ok"`
  to use a free-tier endpoint whose provider may retain and train on the
  prompt. Allowed only for `permitted` data (never `local-only`; never memory,
  baskets, strategy economics, telemetry). The lane writes the policy actually
  used into the result and the ledger line, so the trade is visible after the
  fact. Free-tier limits at the time of the digest: 20 requests/min, 50/day
  until $10 lifetime credit, then 1000/day.
- **Where it lands:** Lane L plan follow-up task T2b — `services.model-lanes.<name>.dataPolicies`
  (allowed set, default `[ "zdr" ]`; core sets `[ "zdr" "free-training-ok" ]`
  for the openrouter lane), `lane-submit --data-policy`, an assertion that
  `free-training-ok` is never combined with a class other than `permitted`,
  and a unit test that the request body differs exactly in the provider block.

## Addendum 2026-09-04 (O3 resolved, fail closed): `/api/v1/messages` is denied on the openrouter lane

The open question O3 left on `/api/v1/messages` — whether OpenRouter honours
a `provider` block on that Anthropic-style path — is moot: nothing consumes
it. The Claude-Code-through-OpenRouter route (`--kind agent`,
`ANTHROPIC_BASE_URL=https://openrouter.ai/api` → `/api/v1/messages`) was a
dead end (it returned empty results and was replaced by the `dsh` job kind),
and both the operator's seat (`dsh-openrouter`) and the lane call
`/api/v1/chat/completions`. So the half-measure — `patchMessagesPath`,
default `false`, which *could* still let a credential-injected, unpatched
request leave the instance — is replaced with a deny:

- **Wiring.** `nixosModules/modelLane.nix` sets
  `services.egress-broker.instances.<name>.denyPaths.<host>.pathPrefixes =
  [ "/api/v1/messages" ]`; `nixosModules/egressBroker.nix` renders it into
  the broker policy as `deny_paths.<host>.path_prefixes`.
- **Mechanism.** `pkgs/broker/policy.py` denies any request whose path
  matches a `deny_paths` prefix — in `requestheaders()`, **before**
  credential injection — with audit reason `path-not-permitted`.
- **The chat prefix list is unchanged.** `bodyPatch.<host>.pathPrefixes`
  stays `[ "/api/v1/chat/completions" ]`; the per-request ZDR/training
  opt-out for chat is exactly as §1 and the earlier addendum described.
- **The U7 gap closes.** The credential-injected, unpatched POSTs to
  `/api/v1/messages` this decision's §1–§2 could not cover are now
  impossible: the deny runs before injection, so no such request reaches any
  provider. Enforced at eval time (`checks.host-core`, `checks.lane-eval`)
  and at runtime (`checks.lane-vm` POSTs to `/api/v1/messages` through the
  broker and asserts a `path-not-permitted` deny in the audit log and no
  upstream arrival).

## Addendum 2026-09-05 (operator): the seat stays on Pro; the headless driver routes per task

The operator, seeing all OpenRouter usage on DeepSeek V4 Pro: "I never intended on changing the seat model, I just don't want to use one for everything." Recorded:

1. **The interactive seat** (`dsh-openrouter` opened by the operator on core) keeps its default, `deepseek/deepseek-v4-pro-0813` (commit 835e454, 2026-09-03, which superseded this decision's original Flash default for the seat). Nothing automated changes the operator's saved selection: per-task homes no longer inherit it (P0, 2026-09-05).
2. **The headless seat driver** (`tools/factory/seat`) routes model and effort per task from one deterministic table, `docs/ledger/routing.toml`, keyed on role × kind × size, most specific row wins, explicit overrides always win. Plan: `docs/superpowers/plans/2026-09-05-seat-routing.md`. First rows follow the measurements of 2026-09-05: docs and XS tasks → Flash at effort off; code → Pro at medium; reviews → Pro at medium (`docs/reviews/2026-09-05-m2b-effort-measurement.md`, `docs/reviews/2026-09-05-model-comparison.md`).
3. The Claude-side roles (Fable orchestrates, Opus gates, Sonnet builds in the dark factory) are a separate route and a separate decision (`2026-09-02-factory-model-policy.md`); the table does not govern them.

**Correction, same day (operator):** "the entire thing is the dark factory" — the seat driver, the Opus gates and the Workflow runs are one factory, not two routes with separate policies. Point 3 above is withdrawn: the routing table governs every factory role on both routes (`route = "openrouter" | "claude"`), and the Claude-side model policy of 2026-09-02 becomes rows in that table (plan `2026-09-05-seat-routing.md`, RT2). Fable orchestrates; it does not implement.

**Correction 2 (2026-09-05 evening, orchestrator error):** the statement above that "every run so far asked for Pro" and that nothing automated chose another model was wrong. The dsh harness (`~/flakes/dsh-harness`, README "roles") has its own role→model map — `deepseekPro`, `deepseekFlash` (structured backend worker), `kimi` (product/UX/frontend, product review), `glm` (feasibility, planning, wave integration, completeness review, routine bulk), `glmFlash` (cheap routine) — and the seat wrapper's picker extras exist to serve it. The OpenRouter activity export (read 2026-09-05 through `rollup --activity`) shows that routing in use: 2026-09-04 — z-ai/glm-5.3 459 requests $28.25, moonshotai/kimi-k3 64 requests $1.69, deepseek/deepseek-v4-flash $0.001, deepseek/deepseek-v4-pro 3,197 requests $32.27; 2026-09-05 — glm-5.3 $1.94, kimi-k3 $0.13, flash $0.13, pro 3,746 requests $64.38 (all app "DeepSeek Harness"). So there are now two routing sources on the OpenRouter route: the harness's internal role map (its repo) and this repo's `docs/ledger/routing.toml` (the seat driver's launch model and effort per task, RT1/RT2). Whether the harness reads this table or this table mirrors the harness rows is a cross-repo decision under `docs/decisions/…claude-dsh-separation` (separate gits; cross over only as reviewed diffs) and is put to the operator as item RT3.
