# Capturing the usage data — OpenRouter and Claude (2026-09-08)

The operator at 16:50: "Can this be pulled via API?" (the OpenRouter activity
export) and "how can we capture the Claude data — do they have CSV or API
tools?" Answered from the vendors' docs, the repo and the host by two
Workflows (`wf_583cf737-351`, `wf_c02d9567-a2c`: a docs reader, a repo or
local reader and an Opus skeptic each). Facts first, then the recommendation.

## OpenRouter

- **The data already arrives with every completion.** Every chat-completions
  response carries `usage.cost`, `usage.cost_details`,
  `usage.prompt_tokens_details.cached_tokens` and `cache_write_tokens`,
  `completion_tokens_details.reasoning_tokens`, the top-level `id` (`gen-…`)
  and `provider`; the old `usage: {include: true}` flag is a no-op now.
  Verified on this host: a lane result under `/var/lib/lanes/openrouter/
  results/` holds `usage.cost` 9.9e-07, the prompt/completion cost split and
  `provider: DeepInfra`, and the ledger already records it as `cost_usd`
  (`tools/ledger/factory.py:358-381`). The seat drops it: dsh's `TokenUsage`
  normalises to four token counts (no cost, provider or id), and
  `tools/factory/seat/factory-usage.py` maps exactly those four into the
  `.result` `usage:` line. That is why the seat side has no dollars — a
  local drop, not a missing API.
- **The account-level endpoints.** `GET /api/v1/activity` is the CSV's API
  twin: one row per UTC day × model × endpoint with `usage` (USD), `requests`,
  `prompt_tokens`, `completion_tokens`, `reasoning_tokens`, `provider_name`,
  for the last 30 completed days — no generation id, no cache/web-search
  split. `POST /api/v1/analytics/query` (metrics × up to two dimensions,
  minute to month) and `GET /api/v1/credits` sit beside it. All three need a
  **management key**, minted separately and barred from completions — a
  second secret. A regular key reaches `GET /api/v1/generation?id=` (the full
  per-generation record, incl. `cache_discount`, `provider_name`,
  `native_tokens_cached`, one id at a time, no bulk listing) and
  `GET /api/v1/key` (that key's own rolling day/week/month totals).
  Retention of generation ids and the rate limits of these endpoints are
  undocumented.
- **The egress rule decides where a pull may run.** Invariant 3 (`docs/
  brief.md` §3): every byte leaves through the broker; the broker's host
  rule drops any connection not from a lane veth (`nixosModules/
  egressBroker.nix:182`), and it injects the key for every `openrouter.ai`
  path (`inject … paths == ["/"]`, `flake.nix:817-821`; `deny_paths` only
  `/api/v1/messages`). So a host timer with the operator's key file is the
  wrong direction (an unattended, off-chokepoint reader of the secret), and
  a pull inside a lane netns already gets the key injected and audited. The
  2026-09-05 telemetry decision kept the manual export for now.
- **The ledger's reader** needs three columns (`created_at`,
  `model_permaslug`, `cost_total`; `factory.py:418, 465-512`) and ignores
  `cost_cache`, `tokens_cached`, `provider_name` and `generation_id`; an API
  JSON would feed it through a few-line adapter, but it would still price by
  (date, model), which is the bucket the price-table gap lives in.

## Claude

- **The transcripts are the ground truth for tokens** — every assistant line
  under `~/.claude/projects/…` carries `message.usage` (input, cache write,
  cache read, output), `message.model` and a timestamp; the workflow agents'
  transcripts sit under `<session>/subagents/workflows/wf_*/`. The one
  correct dedup rule is MAX per field per `message.id` per file (concept
  2026-09-08d §4, corrected). The house already declared the home
  (`/var/lib/evidence/ledger/*.jsonl`, `pkgs/evidence/streams.py:395-519`:
  `factory-runs`, `factory-agents` with tokens by kind, model, role, wall)
  and the writer (`tools/ledger/factory.py extract | backfill`) — which has
  never run here: it crashes at `_read_findings` (`factory.py:167`, called
  from `:241`) on a string finding in today's review shape.
- **Claude Code's OpenTelemetry export is real and can stay local.**
  `CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER=otlp`,
  `OTEL_LOGS_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`
  (the docs' own example) push `claude_code.token.usage` (by type
  input/output/cacheRead/cacheCreation, model, `query_source`, effort, agent
  and skill names), `claude_code.cost.usage` and an `api_request` event with
  `cost_usd`, `duration_ms` and the token counts, plus `session.count` and
  `active_time.total`. Cost is computed locally at list price. Content
  logging is off by default; identity is ON by default (`user.email`,
  `user.account_uuid`, `organization.id`, `session.id`) and the email has no
  documented off-switch. It needs a collector service on core (a module and
  a switch), the env must be exported per launch (not settable in
  `settings.json`), it is prospective only, and it carries no quota metric.
- **The Admin API usage and cost reports** (`/v1/organizations/
  usage_report/messages`, `/v1/organizations/cost_report`) need an Admin key
  of an API organization; the docs state the Admin API is unavailable for
  individual accounts, and the Console CSV and the Enterprise Analytics API
  are org-only. A Max subscription has none of them.
- **The weekly limit is a screen-only number.** The subscription's usage
  view (claude.ai Settings › Usage; `/usage` in Claude Code, held in-process
  for up to 60 minutes) is not persisted anywhere on disk, not in OTel, not
  in the transcripts. What the transcripts do keep is the 429 tombstone:
  `quotaLimits` records with `status`, `resetsAt`, `rateLimitType`,
  `overageStatus` — thirteen here, every one `five_hour`, none weekly.
  `~/.claude.json` holds only tier labels (`default_claude_max_20x`) and
  `cachedExtraUsageDisabledReason: out_of_credits`. The scheduled reset
  probe is a boolean at one instant.

## Recommendation

1. **Seat dollars at the source, no new egress.** The response already
   carries cost, provider and id: keep them. Two places can do it — the seat
   harness (`factory-usage.py` mapping `usage.cost`, `provider` and `id`
   through if dsh exposes them; dsh's `TokenUsage` does not today, so this is
   a change in the harness's own repo) or the broker, which terminates TLS
   and sees every response for seats and lanes alike and already writes a
   JSONL audit line per request: recording the response's `usage` object,
   `provider` and `id` beside that line into the evidence store covers both
   consumers at once, with no key exposure and no harness change. The broker
   path is the one to type.
2. **The activity endpoint later, if ever, through a lane** with a
   management key that the broker injects for `/api/v1/activity` only —
   never a host timer. It buys the 30-day rollup and the account's dollars
   per day; it does not buy per-generation cache pricing, which (1) already
   gives.
3. **Claude tokens now: fix and run the existing extractor** into the ledger
   with the MAX-per-id rule as a tested part of it (a fixture of one
   `message.id` over three lines, output 2 / 2 / 7912, must fail under
   first-wins before the fix; a second fixture for the identical-repeat main
   shape so naive summing dies). Re-derive concept 2026-09-08d §4 from the
   ledger before it reaches the board's numbers.
4. **The limit: capture the 429 tombstones** in the same extractor pass and
   say plainly that the weekly percentage has no durable source; keep the
   reset probe as the proxy.
5. **OpenTelemetry later, optional**, only for forward-looking per-request
   cost and skill attribution: its own phase, a loopback-only collector, a
   processor that drops `user.email` / `user.id` / `organization.id` before
   anything is written, and a check that proves the drop.

None typed — nothing else is owed this session; listed for the operator
beside the measurements concept 2026-09-08d names.
