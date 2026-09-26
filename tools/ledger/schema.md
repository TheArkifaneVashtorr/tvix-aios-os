# Ledger schema

`tools/ledger/factory.py` is the source of truth for the ledger JSONL shapes
below. Ledger files are **data, not source** — they live under
`/var/lib/evidence/ledger/` (`services.evidence-store`, a restic path), never
committed; `EVIDENCE_STORE` overrides the root. Every line is one JSON object
with `kind` (the stream's declared kind), `v` (schema version, currently `1`)
and `src` (which reader produced it). Every ledger file is written by
`evidence.replace_stream` and validated against `pkgs/evidence/streams.py`.

## Principles

- **Append-only, idempotent by key.** Each reader merges into its output file
  keyed on an identity (`run_id`/`agent_id` for factory records, `session_id`
  for dsh sessions, `(lane, job_id)` for lane jobs), so re-running never
  duplicates a line.
- **OpenRouter-reported dollars come first; the price table is the fallback.**
  dsh's `TokenUsage` declares `inputTokens`, `outputTokens`, `totalTokens?`,
  `cacheReadTokens?`, `cacheWriteTokens?`, `reasoningTokens?` — there is **no
  cost field** (verified against pin `0.1.2-rc.1`). Reported cost enters from
  the two places that *do* carry it: lane result files (`usage.cost` →
  `cost_usd`) and the OpenRouter activity export (`--activity`). The price
  table (`--costs`) is only the fallback estimate for what neither reports.
- **A dollar total is never printed as confident when any unit is unpriced.**
  The rollup prints reported and estimated totals separately and names the
  unpriced count plus each missing key, rather than a bare total that silently
  understates spend.

## Factory workflow transcripts (`extract <dir>`)

Input: a Workflow-tool transcript dir — `journal.jsonl` (per-agent structured
returns, including review findings) plus `agent-*.jsonl` (per-turn model id,
token usage, timestamps, tool calls) and `agent-*.meta.json`.

### `factory-runs.jsonl`

```json
{"v":1,"kind":"factory-run-usage","src":"factory","run_id":"workflow","started":"2026-09-03T10:00:00.000Z","ended":"2026-09-03T10:01:45.000Z","plan":null,"prefix":null,"repo":null,"tasks":[],"agents":2,"output_tokens":330,"input_tokens":2800,"cache_read":14000,"cache_write":3000,"thinking":165,"wall_s":105.0}
```

| field | meaning |
|---|---|
| `run_id` | the transcript dir's basename (stable on disk) |
| `started`/`ended` | min/max assistant-message timestamp across agents |
| `plan`/`prefix`/`repo`/`tasks` | not present in the transcript; supplied via `--plan`/`--prefix`/`--repo`/`--tasks` (or the dark-factory hook), otherwise `null`/`[]` |
| `input_tokens`/`output_tokens`/`cache_read`/`cache_write`/`thinking` | summed from `agent-*.jsonl` usage (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `output_tokens_details.thinking_tokens`) |
| `wall_s` | `ended - started` in seconds |

### `factory-agents.jsonl`

```json
{"v":1,"kind":"factory-agent","src":"factory","run_id":"workflow","agent_id":"a1111111111111111","label":null,"role_model":"claude-opus-5","model_id":"claude-opus-5","model_suffix":"1m","message_count":3,"tokens":{"in":2105,"out":8017,"cache_read":4105,"cache_write":0,"thinking":100},"wall_s":30.0,"tool_uses":2}
```

| field | meaning |
|---|---|
| `run_id` | the run this agent belongs to (its only tie to a window; agents carry no timestamp) |
| `agent_id` | the `agent-<id>.jsonl` filename id |
| `label` | the Workflow tool's per-agent label, joined from the journal's `result.label` by `agentId` (`null` when no result event carries one) |
| `role_model`/`model_id` | the model id's head (split at the first `[`; one value — they coincide here) |
| `model_suffix` | the bracketed tail without its brackets (`"claude-opus-5[1m]"` → `"1m"`), `null` when there is no `[` |
| `message_count` | the number of usage groups, not lines: one per `message.id` in the file plus one per line without a `message.id` |
| `tokens` | `in`/`out`/`cache_read`/`cache_write`/`thinking`, **the MAX per usage field per `message.id` per file, summed across groups** (§Errata applied G: the group key is `(file, message.id)`, never `message.id` alone, so two files that reuse an id each contribute their own maximum) |
| `wall_s` | min→max timestamp for that agent |
| `tool_uses` | count of `tool_use` content blocks across the agent's assistant messages |

### `factory-findings.jsonl`

```json
{"v":1,"kind":"factory-finding","src":"factory","run_id":"workflow","task":null,"round":null,"label":null,"severity":"major","file":"pkgs/x.py","title_sha256":"1ecd2a8c6afe6dc179d1e37b0c9f13e9f9fecba8ea29e875f26868d534672867","class":null}
```

| field | meaning |
|---|---|
| `severity`/`file`/`title_sha256` | the review finding's `severity`/`file`/`issue`; `title_sha256` is the 64-hex SHA-256 of the finding's `issue`/`title` text (the dedup key is `(run_id, file, title_sha256)`) |
| `task`/`round`/`label` | `task`/`round`/`label` from the result's `task_key`/`round`/`label` when the factory recorded them (E3, 2026-09-05); `null` for older runs; `class` still null |

A `str` finding is accepted as-is (`title` is the string, `severity`/`file`/`class`
null); a `dict` is read as above; anything else is skipped with one stderr line.

### `limit-events.jsonl`

The 429 rate-limit tombstones (`isApiErrorMessage` true, `apiErrorStatus` 429,
a `quotaLimits` object) a transcript carries. Declared here (SP2) and written
by `extract` (origin `"agent"`, one per tombstone across every agent file);
SP6's main-session walk reuses the same reader with origin `"main"`.

```json
{"v":1,"kind":"limit-event","src":"transcript","session_id":"sess_fixture","request_id":"req_fixture_1","at":"2026-09-08T17:01:00.123Z","api_error_status":429,"error_kind":"rate_limit","rate_limit_type":"five_hour","limit_status":"rejected","resets_at":1788680400,"overage_status":"rejected","overage_disabled_reason":"org_level_disabled","is_using_overage":false,"fallback_available":false,"origin":"agent"}
```

| field | meaning |
|---|---|
| `session_id`/`request_id` | the tombstone's `sessionId`/`requestId` (the dedup key) |
| `at` | the tombstone's `timestamp` (millisecond fraction accepted) |
| `api_error_status` | always `429` — the tombstone is a limit event by construction |
| `error_kind` | the tombstone's `error` (`rate_limit`) |
| `rate_limit_type`/`limit_status`/`resets_at`/`overage_status`/`overage_disabled_reason`/`is_using_overage`/`fallback_available` | the `quotaLimits` object's seven keys mapped one to one (`rateLimitType`→`rate_limit_type`, `status`→`limit_status`, `resetsAt`→`resets_at`, `overageStatus`, `overageDisabledReason`, `isUsingOverage`, `unifiedRateLimitFallbackAvailable`→`fallback_available`) |
| `origin` | `"agent"` (SP2's workflow walk) or `"main"` (SP6's main-session walk) |

### `main-sessions.jsonl`

Declared here (SP2) so SP6 and SP7 never edit `streams.py` in one wave; the
writer is SP6's main-session walk (`_read_main_session`). One row per main
session file — `<project>/<session>.jsonl`, `session_id` = the file stem —
carrying **numbers only**: per-model token totals (MAX-per-`message.id` dedup
applied identically), message/tool counts, min/max timestamps, the harness
`version`, and `limit_events` = the number of `limit-event` rows that session
produced. Bodies are never read, so no `cwd`, `gitBranch`, `slug`, prompt or
reply leaves the file. A non-JSON line is skipped and counted once to stderr.

```json
{"v":1,"kind":"main-session","src":"transcript","session_id":"11111111-2222-4333-8444-555555555555","harness_version":"2.1.258","started":"2026-09-03T10:00:00.000Z","ended":"2026-09-03T10:02:00.000Z","message_count":2,"tool_uses":1,"limit_events":1,"tokens":{"in":3000,"out":7952,"cache_read":34255,"cache_write":29050,"thinking":0},"by_model":[{"model":"claude-opus-4-1","model_suffix":null,"message_count":1,"in":2000,"out":7912,"cache_read":34255,"cache_write":29050,"thinking":0},{"model":"claude-sonnet-4-5","model_suffix":"1m","message_count":1,"in":1000,"out":40,"cache_read":0,"cache_write":0,"thinking":0}],"wall_s":120.0}
```

| field | meaning |
|---|---|
| `session_id` | the main-session file's stem (the dedup key) |
| `harness_version` | the first line's top-level `version` (e.g. `2.1.258`) |
| `started`/`ended` | min/max `timestamp` across the file |
| `message_count` | the number of usage groups (one per `message.id` plus one per id-less line) |
| `tool_uses` | count of `tool_use` content blocks |
| `limit_events` | how many `limit-event` rows (origin `main`) this session produced |
| `tokens` | `in`/`out`/`cache_read`/`cache_write`/`thinking`, MAX per `message.id` per file summed across groups |
| `by_model` | one entry per `message.model` in first-seen order; each `model`/`model_suffix` is the id split at the first `[` (the bracketed tail without its brackets), plus that model's own `message_count` and token totals |
| `wall_s` | `ended − started` in seconds |

`backfill` now walks both trees: the workflow glob
`**/subagents/workflows/wf_*` (unchanged) and `sorted(<projects>/*/*.jsonl)`
(the main-session files directly under a project directory — a workflow agent
file nests deeper and never matches), merging `main-sessions.jsonl` and
`limit-events.jsonl`, and returns `(workflow_dirs, main_sessions,
limit_events)`; the CLI prints `backfill: {w} workflow dirs, {m} main
sessions, {l} limit events`.

## dsh session usage (`extract-dsh <sessions-dir>`)

Input: `<sessions-dir>/<slug>/<uuid>/session.jsonl` **or** `session.jsonl.zstd`
(the durable layout — `$DSH_HOME/sessions/*.jsonl` matches zero files;
decompression is `zstd -dc`), plus `<sessions-dir>/manifest.json` mapping
`session_id → {role, model}`.

### `dsh-sessions.jsonl`

```json
{"v":1,"kind":"dsh-session","src":"dsh","session_id":"session-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","role":"deepseekPro","model":"deepseek/deepseek-v4-pro-0813","started":1788546865000,"turns":1,"steps":3,"tools":3,"in":600,"out":90,"cache_read":180,"reasoning":60,"wall_s":14.0}
```

| field | meaning |
|---|---|
| `session_id` | the `session` event's `id` (falls back to the `<uuid>` dir name) |
| `role`/`model` | joined from `manifest.json` by `session_id` |
| `started` | epoch **milliseconds** of `min(createdAt, first event time)` — carried so the rollup can join by date (price table and activity export) |
| `turns` | count of `turn/start` events |
| `steps` | count of `step/start` events |
| `tools` | count of `tool/call` events |
| `in`/`out`/`cache_read`/`reasoning` | summed from `assistant/message.data.usage` (`inputTokens`, `outputTokens`, `cacheReadTokens`, `reasoningTokens`) |
| `wall_s` | (last event `time` − `started`) / 1000 |

`started` is the one field beyond the N6 spec's shorthand list: the "dollars
joined by date and model" requirement has no date to join on without it. The
leading `session` event carries `createdAt` (not `time`), so `started` and
`wall_s` count from whichever of `createdAt` and the first event `time` is
earlier.

## Lane job results (`extract-lane <results-dir>`)

Input: `/var/lib/lanes/<lane>/results/<job-id>.json` — the result spool
`docs/runbooks/lanes.md` names. A success result is
`{output, usage, model, provider, ts}` and its `usage` carries OpenRouter's
`cost`; a refused or failed job is `{error, ts}` with no `usage`. The lane
name defaults to the results dir's parent (`/var/lib/lanes/openrouter/results`
→ `openrouter`), overridable with `--lane`.

### `lane-jobs.jsonl`

```json
{"v":1,"kind":"lane-job","src":"lane","lane":"openrouter","job_id":"3f9a1c7e2b04","model":"deepseek/deepseek-v4-flash","provider":"DeepInfra","ts_epoch":1788546900.0,"cost_usd":2.5e-05}
```

| field | meaning |
|---|---|
| `lane` | the lane name (results dir parent, or `--lane`) |
| `job_id` | the result file stem |
| `model`/`provider` | from the result file (absent on a refusal/error) |
| `ts_epoch` | epoch **seconds** from the result file — carried so `rollup --week` can window the job |
| `cost_usd` | `usage.cost` when present, else `null` — recorded from OpenRouter, never estimated |

## `rollup --costs <price-table.csv>` and `--activity <activity.csv>`

`rollup` prints token totals and a cost block that keeps **reported** and
**estimated** dollars separate.

- **Reported.** The OpenRouter activity export, `--activity <csv>`, keyed by
  `date,model` with a `cost` column, is the **single source of truth** for
  reported cost per `(date, model)`. The export is account-wide, so a bucket
  already contains the lane's requests for that date and model; a lane job's
  own `cost_usd` is added only for a bucket the export does not cover (or when
  no export is given), never double-counting. The export is per request, so
  rows sharing a date+model are summed, and a bucket that joins to no session
  still counts and is named `unattributed`:

  ```csv
  date,model,cost
  2026-09-04,deepseek/deepseek-v4-pro-0813,0.000500
  2026-09-04,deepseek/deepseek-v4-pro-0813,0.000500
  2026-09-04,openai/gpt-9,5.000000
  ```

  **Both shapes are accepted.** The reader takes the real OpenRouter activity
  export and the legacy `date,model,cost` shorthand alike:

  - the real export (`created_at,model_permaslug,cost_total`, plus many more
    columns) maps `created_at` (ISO timestamp) to its `YYYY-MM-DD` date part,
    `model_permaslug` to `model`, and `cost_total` to `cost`; a
    `cancelled == "true"` row still counts its cost;
  - the legacy `date,model,cost` columns still parse.

  A wrong shape fails loudly: a CSV matching neither column set raises
  `ActivityExportError` naming both accepted column sets and the columns
  found, and a non-numeric cost cell raises `ActivityExportError` naming the
  row.

- **Estimated.** `--costs <price-table.csv>`, a fallback rate table keyed by
  `(date, model)`:

  ```csv
  date,model,in_per_1m,out_per_1m,cache_read_per_1m
  2026-09-04,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1
  ```

  It computes `in/1e6*in_per_1m + out/1e6*out_per_1m +
  cache_read/1e6*cache_read_per_1m` per session, joined on the session's
  `started` date and `model`. The committed `docs/ledger/openrouter-prices.csv`
  records rows dated so the date join picks the right one: `docs/runbooks/lanes.md`
  (2026-09-03) is the source of the Flash row ($0.08/$0.16) and the 2026-09-03
  Pro row ($1.02/$2.05), while `tools/factory/seat/README.md` (2026-09-04) is
  the source of the 2026-09-04 Pro row ($0.55/$2.19). Neither source named a
  cache-read rate, so `cache_read_per_1m` is `0.0` (cache reads unpriced) there.

A session whose `(date, model)` has an activity row is **reported** and is not
re-estimated — the price table only covers what the activity export does not
("prefer reported over the price table wherever it exists"), so:

```
reported cost: 0.001000 USD (lane 0.000000 + activity 0.001000)
estimated cost: 0.003990 USD (price table, 1 session(s))
```

When every unit is covered there is no further line. When any unit is
unpriced, the rollup refuses a confident total: it names the count and each
gap, e.g. `unpriced: 3 of 5 unit(s): no start time for 1 session(s); no cost
row for (2026-09-04, deepseek/deepseek-v4-flash); no reported cost for 1 lane
job(s)`. The three named gaps, in the order the code emits them, are: a
session with no `started` to derive a date from (`no start time for N
session(s)`, never a `(None, model)` miss), a session whose date+model has
neither an activity row nor a price row (`no cost row for …`), and a lane job
whose result carried no `usage.cost` (`no reported cost for N lane job(s)`).

**Residual on attribution.** Seat sessions join the activity export only at
`(date, model)` granularity — dsh records no per-request cost — so a reported
bucket shared by several sessions that day is attributed to the bucket, not to
any one session: per-session reported cost stays approximate.

Without `--costs` and `--activity` (and no lane `cost_usd`), the rollup prints
token totals and `cost: unknown (no price table)`; if lane jobs are present
but all unpriced, it
also names their count and ids rather than printing only the unknown-cost line.
A `--costs` CSV that is not
a rate table raises `PriceTableError`; an `--activity` CSV that is neither
`date,model,cost` nor the real export (`created_at,model_permaslug,cost_total`)
raises `ActivityExportError` — each names the columns found instead of a
`KeyError`.

### Windowed rollup (`rollup --week`)

`--week` rolls up a half-open window `[since, until)`, UTC. By default the
window is the trailing 7 days (`until` = now, `since` = now − 7 days);
`--since`/`--until` override either bound (a missing bound derives from the
other: `--since` alone ends at now, `--until` alone starts 7 days back).

- dsh sessions are windowed by their `started` (epoch **milliseconds**).
- lane jobs are windowed by their `ts_epoch` (epoch **seconds**).
- main sessions are windowed by their `started` (ISO-8601); the
  `main sessions: {n} sessions, in … out … cache_read … cache_write …
  thinking …` line sums the in-window rows' `tokens`.
- factory runs are windowed by their `started` (ISO-8601). `factory-agents`
  and `factory-findings` carry no timestamp, so each joins to its run by
  `run_id` and inherits that run's window.

The first output line names the bounds, e.g.
`window: 2026-08-28T00:00:00Z .. 2026-09-04T00:00:00Z`. Records whose
timestamp falls outside the window — or whose run has no windowable
`started` — are excluded from every lane, role, fix-round and cost total: the
reported/estimated cost block and its unpriced denominator use the same
windowed session and lane-job lists as the lane lines. A dsh session with no
`started` cannot be windowed, but it is not silently dropped either: the cost
block names it as `no start time for N session(s)` on the `--week` path the
same as without it.

`--since`/`--until` are only meaningful with `--week`; passing either
without `--week` is a usage error.
