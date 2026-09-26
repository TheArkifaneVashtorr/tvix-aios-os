# Research digest — OpenRouter as the cheap remote lane (DeepSeek V4 Flash), 2026-09-03

Three Sonnet sweeps (model, privacy/API, integration) plus one Sonnet skeptic
who re-opened every load-bearing page; 23 of 24 checked claims held. All
facts below were fetched 2026-09-03 from primary pages unless marked. The
orchestrator's own training data has no record of a DeepSeek "V4" release;
everything here rests on the live pages, which is why each line carries its
URL. Re-verify before any lane depends on a number.

## The model

- **Ids on OpenRouter:** `deepseek/deepseek-v4-flash` (dated snapshot,
  page titled "DeepSeek V4 Flash 0423"); rolling alias
  `deepseek/deepseek-v4-flash-latest` (its page shows a 1,310,720-token
  context, i.e. a newer build than 0423's 1,048,576). A vision variant
  `deepseek-v4-flash-vision-exp` exists. Pin the dated snapshot id in Nix
  and confirm it against `GET /api/v1/models` at lane bring-up.
  https://openrouter.ai/deepseek/deepseek-v4-flash ·
  https://openrouter.ai/deepseek/deepseek-v4-flash-latest
- **OpenRouter pricing, per million tokens:** 0423 snapshot input $0.0679 /
  output $0.168 / cache read $0.0168; `-latest` alias $0.05 / $0.16 / $0.013.
  (same pages)
- **DeepSeek's own API, for comparison:** v4-flash cache-miss input $0.22
  off-peak / $0.44 peak, output $0.66 / $1.32, cache hit $0.007 / $0.014;
  1M context, 384K max output. Aggregator sites quote lower numbers that
  contradict this primary page — rejected.
  https://api-docs.deepseek.com/quick_start/pricing/
- **Capabilities on OpenRouter:** tools + `tool_choice`, structured outputs
  via `response_format` JSON schema, reasoning efforts `high`/`xhigh`; 17
  providers serve the 0423 snapshot (DigitalOcean, StreamLake, DeepInfra,
  GMICloud, SiliconFlow, Alibaba Cloud Intl, Venice, NextBit, CoreWeave,
  Baidu Qianfan, NovitaAI, AtlasCloud, Parasail, Mancer, Phala, Azure US,
  Cloudflare). Provider sets differ per snapshot.
- **Model card:** released 2026-04-26, MoE 284B total / 13B active, hybrid
  attention, 1M context, MIT licence; MMLU 88.7, HumanEval 69.5; modes
  non-think / think-high / think-max.
  https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash

## Privacy and data policy (policy dated 2026-08-31)

- OpenRouter does not train on inputs/outputs and does not retain text
  beyond routing except for abuse, security, billing or legal reasons; the
  **chosen provider's** retention/training policy governs its copy.
  https://openrouter.ai/privacy
- **Zero Data Retention:** routes only to endpoints whose provider stores
  nothing. Set account-wide per model group (the "Non-frontier" group covers
  DeepSeek), per key/team as a guardrail, or per request with
  `"provider": {"zdr": true}` (a request can only turn ZDR on, never off).
  Machine-readable list of ZDR endpoints: `GET /api/v1/endpoints/zdr`.
  https://openrouter.ai/docs/guides/features/zdr
- **Training opt-out:** account settings (separate toggles for paid and
  free models); per request `"provider": {"data_collection": "deny"}`.
  https://openrouter.ai/docs/guides/privacy/provider-logging ·
  https://openrouter.ai/docs/guides/routing/provider-selection
- Personal data may be transferred to the US / outside the EEA under
  standard contractual clauses. (privacy page)
- UNVERIFIED: the live list of ZDR providers for this exact snapshot (time-
  varying; read the endpoint at bring-up and pin the provider allowlist in
  the request body); the precedence between account, key and request
  settings (docs describe them consistently but no single page states it).

## API surface and egress facts

- **Host:** `openrouter.ai` only — both API surfaces live under it; no
  separate API subdomain was found. The broker allowlist is one host; a live
  capture at bring-up confirms no CDN side-connections.
- **OpenAI-compatible:** base `https://openrouter.ai/api/v1`, chat
  completions `POST /api/v1/chat/completions`.
  https://openrouter.ai/docs/api-reference/overview
- **Anthropic-Messages-compatible:** base `https://openrouter.ai/api`; Claude
  Code speaks its native protocol to it with `ANTHROPIC_BASE_URL` and
  `ANTHROPIC_AUTH_TOKEN` (sent as `Authorization: Bearer …`).
  https://openrouter.ai/docs/cookbook/coding-agents/claude-code-integration
- **Auth:** `Authorization: Bearer <key>` on every request; 401 otherwise.
  https://openrouter.ai/docs/api_reference/authentication
- **Limits:** paid models carry no OpenRouter request cap; a negative credit
  balance returns 402; per-key spend caps are readable at `GET /api/v1/key`.
  https://openrouter.ai/docs/api_reference/limits
- **Broker fit (repo facts):** `services.egress-broker.instances.<i>.inject."openrouter.ai"`
  = `{ header = "Authorization"; prefix = "Bearer "; valueFile = …; }`;
  `policy.py` reads the file at start and sets the header from
  `requestheaders()` for that exact host (`pkgs/broker/policy.py:170-186`),
  overwriting whatever the client sent — so a client may carry a dummy
  token and never the real one.

## Serving stack notes

- Bifrost (brief §5.4's router) is **not in nixpkgs** at the pin or on
  master; it needs its own derivation (Go + npm) or a container. Current
  tags: `core/v1.8.4` (2026-08-27), `transports/v2.0.0` (2026-08-26). It
  supports OpenRouter as an outbound provider (`openrouter/<model>`) and an
  Anthropic-format inbound at `/anthropic`.
  https://github.com/maximhq/bifrost/tags ·
  https://docs.getbifrost.ai/integrations/anthropic-sdk
- Community proxies (claude-code-router) exist; not needed given
  OpenRouter's native Anthropic surface.

## What this settles for the lane design

Pin `deepseek/deepseek-v4-flash` (0423) in Nix; broker instance
`openrouter` with `allow = [ "openrouter.ai" ]` and the injected key; every
request body carries `provider: { zdr: true, data_collection: "deny" }` and,
once read at bring-up, an explicit provider allowlist; the account-level ZDR
toggle for the Non-frontier group is set as belt and braces. The lane's
client uses the OpenAI-compatible endpoint; Claude Code itself can be pointed
at the Anthropic-compatible surface through the broker when an experiment
wants it.
