# Ledger schema

`tools/ledger/factory.py` is the source of truth for the ledger JSONL shapes
below. Ledger files are **data, not source** — they live under
`/var/lib/evidence/ledger/` (`services.evidence-store`, a restic path), never
committed; `EVIDENCE_STORE` overrides the root. Every line is one JSON object
with `v` (schema version, currently `1`) and `src` (which reader produced it).

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
{"v":1,"src":"factory","run_id":"workflow","started":"2026-09-03T10:00:00.000Z","ended":"2026-09-03T10:01:45.000Z","plan":null,"prefix":null,"repo":null,"tasks":[],"agents":2,"output_tokens":330,"input_tokens":2800,"cache_read":14000,"cache_write":3000,"thinking":165,"wall_s":105.0}
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
{"v":1,"src":"factory","run_id":"workflow","agent_id":"a1111111111111111","label":null,"role_model":"claude-fable-5","model_id":"claude-fable-5","tokens":{"in":1100,"out":120,"cache_read":5000,"cache_write":1000,"thinking":60},"wall_s":30.0,"tool_uses":2}
```

| field | meaning |
|---|---|
| `run_id` | the run this agent belongs to (its only tie to a window; agents carry no timestamp) |
| `agent_id` | the `agent-<id>.jsonl` filename id |
| `label` | the Workflow tool's per-agent label is ephemeral and not in the transcript — `null` |
| `role_model`/`model_id` | the model string the transcript records (one value; they coincide here) |
| `tokens` | `in`/`out`/`cache_read`/`cache_write`/`thinking`, same source fields as the run |
| `wall_s` | min→max timestamp for that agent |
| `tool_uses` | count of `tool_use` content blocks across the agent's assistant messages |

### `factory-findings.jsonl`

```json
{"v":1,"src":"factory","run_id":"workflow","task":null,"round":null,"label":null,"severity":"major","file":"pkgs/x.py","title":"X does Y","class":null}
```

| field | meaning |
|---|---|
| `severity`/`file`/`title` | the review finding's `severity`/`file`/`issue` |
| `task`/`round`/`label` | `task`/`round`/`label` from the result's `task_key`/`round`/`label` when the factory recorded them (E3, 2026-09-05); `null` for older runs; `class` still null |

## dsh session usage (`extract-dsh <sessions-dir>`)

Input: `<sessions-dir>/<slug>/<uuid>/session.jsonl` **or** `session.jsonl.zstd`
(the durable layout — `$DSH_HOME/sessions/*.jsonl` matches zero files;
decompression is `zstd -dc`), plus `<sessions-dir>/manifest.json` mapping
`session_id → {role, model}`.

### `dsh-sessions.jsonl`

```json
{"v":1,"src":"dsh","session_id":"session-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","slug":"slug-a","role":"deepseekPro","model":"deepseek/deepseek-v4-pro-0813","started":1788546865000,"turns":1,"steps":3,"tools":3,"in":600,"out":90,"cache_read":180,"reasoning":60,"wall_s":14.0}
```

| field | meaning |
|---|---|
| `session_id` | the `session` event's `id` (falls back to the `<uuid>` dir name) |
| `slug` | the `<slug>` dir name |
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
{"v":1,"src":"lane","lane":"openrouter","job_id":"3f9a1c7e2b04","model":"deepseek/deepseek-v4-flash","provider":"DeepInfra","ts":1788546900.0,"cost_usd":2.5e-05}
```

| field | meaning |
|---|---|
| `lane` | the lane name (results dir parent, or `--lane`) |
| `job_id` | the result file stem |
| `model`/`provider` | from the result file (absent on a refusal/error) |
| `ts` | epoch **seconds** from the result file — carried so `rollup --week` can window the job |
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
- lane jobs are windowed by their `ts` (epoch **seconds**).
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
