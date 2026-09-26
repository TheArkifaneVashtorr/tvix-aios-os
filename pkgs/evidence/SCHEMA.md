# Evidence store — streams and row shapes (v1)

Directory: `services.evidence-store.path`, default `/var/lib/evidence` (env `EVIDENCE_STORE`
overrides for tests and pre-switch use; every writer also passes `--store` explicitly). One JSONL
file per stream; append-only under flock; every row: `{"v":1,"ts":"2026-09-05T12:00:00Z","kind":"<kind>", ...}`.
Stream names match `^[a-z][a-z0-9-]{0,31}$`, optionally under a `derived/` or `ledger/`
subdirectory. The envelope (`v`, `ts`) is written after the writer's row, so a writer cannot
override v or ts.

Every row is validated against `pkgs/evidence/streams.py` **before the lock**: a row with an
undeclared kind or field, a forbidden field name, a secret-shaped value, or a value outside its
declared class is refused (`StreamRefused`) and nothing is written. Streams may live under
`derived/` or `ledger/`; `derived/tasks` (kind `task-result`, key `(run_id, key)`, classification
field `task_kind` in `code|docs|unknown`, `status` in `done|partial|failed|skipped|unreported|unknown`,
`route` in `explicit|unknown|implement/<kind>/<size>|codex/<kind>/<size>` (`<kind>` in `code|docs`, `<size>` in `XS|S|M|L`),
`area` in the manifest's areas plus `unknown` (`isolation|platform|helm|seat|factory|evidence|generation|knowledge|program|unknown`, pinned to `docs/ledger/subsystems.toml`),
`class` nullable in `tasks.CLASS_NAMES` plus `any` (`nix-module|nix-check|bash-driver|python-evidence|js-workflow|bats-test|vm-test|docs-runbook|docs-plan|docs-board|docs-spec|docs-plan-run|rust|any`, one source `streams.TASK_CLASS_NAMES`; copied from the `.result`'s `class:` line, `null` when the line is absent, never inferred),
`derived` ⊆ `checks|commits`, `touches_extra`/`touches_disclosed` nullable int,
`checks_verified` nullable map of check name → `pass|fail|not-run:absent|not-run:cache-miss|not-run:verify-timeout`,
`checks_scope` in `clean|dirty` (nullable), `checks_scope_files`/`verify_s` nullable int,
`probes_verified` nullable map of probe name → `pass|fail|missing|not-run|drift`, and the
`error_class` arms `touches-violation`, `checks-misreported`, `checks-unverifiable`, `verify-timeout`,
`probe-mismatch`, `probe-missing`) and
`derived/gates` (kind `gate-verdict`, key `review_path`, `reviewer` in `opus|sonnet|deepseek|fable|glm|kimi|unknown`,
nullable `rung` 1–9) are declared here and written by
`evidence ingest result` / `ingest reviews`, which `replace_stream` by key rather than append.

| stream | kind | fields | writers |
|---|---|---|---|
| `checks` | `check` | `name` (check name; `flake-check` = the whole `nix flake check`), `rev` (40 hex), `ok` (bool), `class` (`unit|eval|vm|nix-check|curl|browser|operator|unmeasured`), `src` (`helm-nightly`, `seat-integrate`, `dark-factory-verify`, …), `duration_s`?, `log_tail`? (≤ 4000 chars) | helm-flake-check (E5), factory-integrate (E7), dark-factory verify (E3) |
| `helm-status` | `helm-status` | `tiles` (name → `ok|warn|fail|unknown`), `reason` (`change|heartbeat`) | helm-collect (E6) |
| `runs` | `factory-run` | `plan`, `prefix`, `baseline`, `integration_branch`, `tasks[]{key,status,commit,fixRounds}`, `verify` (`pass|fail|skipped|none`), `delivered`, `agents`, `output_tokens`, `run_id`? | dark-factory recorder (E3) |
| `plans` | `plan-judgement` | the 14 fields of the `plan-judgements` front-matter block (`plan`, `spec`, `author`, `effort`, `words`, `tasks`, `judges[]`, `judges_dropped[]`, `scores[14]`, `total`, `self_score`, `threshold`, `decision`, `revision`), `judged_ts` (first git commit time, RFC3339 Z), `judgement_path` (repo-relative `docs/reviews/plan-judgements/*.md`); every field validated by `judgements.validate_judgement`; key `(judgement_path)` — every judgement file is its own row, never deduped by `(plan, revision)` (a re-drafted-and-rejudged plan carries `revision: 0` on both rounds); `evidence report plans` selects the latest per plan by `judged_ts` | evidence ingest judgements (P6) |
| `ledger/openrouter-usage` | `openrouter-usage` | `src` (`broker`), `instance` (id), `request_id` (32 hex), `ts_epoch` (num), `streamed` (bool), `http_status` (int), `status` (`ok|no-usage|unparsed`); nullable `gen_id`, `model` (model-id), `provider`, `cost_usd`, `upstream_cost_usd`, `is_byok`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `cached_tokens`, `cache_write_tokens`, `reasoning_tokens`, `run_id`?, `key`?, `attribution`? (`header|window|none`, written by the ingest); key `(instance, request_id)` | evidence ingest openrouter-usage (SP8) |
| `ledger/operator` | `operator-ask` | `session`, `ask_id` (16 hex, hashes never ids), `phase` (`ask|answer`), `header` (≤ 12 chars, the only string), `options`, `recommended_index`?, `chosen_index`?, `took_recommended`?, `latency_s`?, `key`?, `surface` (`chat|run-button|helm`), `src` (`hook|orchestrator`); key `(session, ask_id, phase)` | `evidence append operator` — two AskUserQuestion hooks, or the orchestrator (OC4) |
| `ledger/otel-claude` | `otel-claude` | key `(session_id, sample_id)`; `src` (`otel`), `sample` (`request|tokens`), `at` (RFC3339 Z); nullable `model` (model-id), `model_suffix`, `harness_version`, `terminal_type`, `query_source`, `speed`, `effort`, `agent_name`, `skill_name`, `request_id`, `cost_usd` (num), `duration_ms`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` (int), `token_type` (`input|output|cacheRead|cacheCreation`), `value` (num); refuses an identity attribute (`user`/`organization` first token), a missing `session.id` / non-numeric `timeUnixNano`, a missing `request_id`, and a non-model-id `model` | evidence ingest otel (SP7) |
| `ledger/debug-usage` | `debug-usage` | batch, item, rung (1–2), model (model-id), status (done|failed|timeout), confidence (confirmed|probable|unknown|none), wall_s, signature (seat:…|check:…|bug:…|note:…); nullable cost_usd, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, num_turns, session_id; key (batch, item, rung); no free text | tools/debug/investigate (DS4) via evidence.append |
| `ledger/engagement` | `engagement` | `day`, `surface`, `opens`, `dwell_s`, `feed_likes`; key `(day, surface)` | Helm backend via `evidence.replace_stream` (HM8; question 2) |
| `ledger/*.jsonl` | per `tools/ledger/schema.md` | the token/cost ledger; unchanged shapes; idempotent merge, the one non-append-only area | `tools/ledger/factory.py` (E4) |

## Engagement — the counts-only data class (decision 18b)

1. Stream `ledger/engagement`, kind `engagement`, key `(day, surface)`: one row per surface per UTC day. The writer's verb is `evidence.replace_stream(store, "ledger/engagement", rows)` (`pkgs/evidence/evidence.py:133`): keyed, all-or-nothing, a changed row replaces the row under the same key. `evidence.append` is not keyed — two appends of one key are two rows — so it is not this stream's verb.
2. `day`: `^\d{4}-\d{2}-\d{2}$` (the same regex class `activity-day` uses for `date`, `streams.py:395`).
3. `surface`: closed enum, initially `("home", "feed", "seats")` — the Helm pages HM7/HM8 create (`pkgs/helm/api_home.py`, absent today); extending the enum is an Evidence task with a mutant, never a Helm-side change.
4. `opens`, `dwell_s`, `feed_likes`: non-negative integers, bounded `0 ≤ n ≤ 10_000_000` — the bounded `("int", lo, hi)` class (`streams.py:752-757`), so a negative, a float or a bool is refused with `not a int`. A counter absent from a row reads as 0: the validator has no required-field arm (Assumption 4), and the declaration says so rather than pretending otherwise.
5. No other field. No free text, no identifiers, no titles, no URLs, no session ids: the row carries counts and the envelope (`v`, `ts`, `kind`) and nothing else.
6. The row is local-only: written under `/var/lib/evidence/ledger/engagement.jsonl`, never ingested from or exported to any path outside the store; no ingest module, no timer (question 2, writer (a)).
7. The name fence is a second, independent guarantee: a field named in `streams.FORBIDDEN` (`note`, `title`, `url`, … — `streams.py:39-60`) is refused as `<name>: forbidden name` whether or not a future entry declares it (`_name_fence`, `:666-679`); the five names above are outside the set.

The validator is the guarantee: a row with any field outside these five is refused before the lock (`streams.py:871`), and a content-shaped field name is refused even when declared (`streams.py:39-60,666-679`). Adding a string-valued field to this kind is a decision, not a task — it requires a new answer in `docs/decisions/` amending 18b.

## The operator stream — the text-free data class (question 1 of the operator-and-collection plan)

`ledger/operator` (kind `operator-ask`, key `(session, ask_id, phase)`) carries the operator's AskUserQuestion turns as data, never text: one bounded string (`header`, 12 chars, the tool's chip label), hashes for ids, counts and indices for everything else. `question`, `questions`, `answer`, `answers` are forbidden names for every kind (`streams.FORBIDDEN`), so a question or an answer can never be declared by mistake; adding a string field to this kind is a decision amending 18b, not a task.

Readers: `pkgs/helm/collect.py` (tiles), `evidence bundle` (E9), `tools/ledger/factory.py`.
A reader skips a torn line and never fails the whole read on one bad row.
A reader of `<stream>.jsonl` also reads every sibling `<name>-YYYY-MM.jsonl`
(monthly partition; `^<name>-\d{4}-\d{2}\.jsonl$`) after the base file, in name
order; any other sibling is ignored and the writer still names one file.
The claims file `docs/ledger/claims.toml` is NOT a stream: it is policy, in the repo (E2).