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
`derived` ⊆ `checks|commits`, `touches_extra`/`touches_disclosed` nullable int,
`checks_verified` nullable map of check name → `pass|fail|not-run:absent|not-run:cache-miss|not-run:verify-timeout`,
`checks_scope` in `clean|dirty` (nullable), `checks_scope_files`/`verify_s` nullable int,
`probes_verified` nullable map of probe name → `pass|fail|missing|not-run|drift`, and the
`error_class` arms `touches-violation`, `checks-misreported`, `checks-unverifiable`, `verify-timeout`,
`probe-mismatch`, `probe-missing`) and
`derived/gates` (kind `gate-verdict`, key `review_path`) are declared here and written by
`evidence ingest result` / `ingest reviews`, which `replace_stream` by key rather than append.

| stream | kind | fields | writers |
|---|---|---|---|
| `checks` | `check` | `name` (check name; `flake-check` = the whole `nix flake check`), `rev` (40 hex), `ok` (bool), `class` (`unit|eval|vm|nix-check|curl|browser|operator|unmeasured`), `src` (`helm-nightly`, `seat-integrate`, `dark-factory-verify`, …), `duration_s`?, `log_tail`? (≤ 4000 chars) | helm-flake-check (E5), factory-integrate (E7), dark-factory verify (E3) |
| `helm-status` | `helm-status` | `tiles` (name → `ok|warn|fail|unknown`), `reason` (`change|heartbeat`) | helm-collect (E6) |
| `runs` | `factory-run` | `plan`, `prefix`, `baseline`, `integration_branch`, `tasks[]{key,status,commit,fixRounds}`, `verify` (`pass|fail|skipped|none`), `delivered`, `agents`, `output_tokens`, `run_id`? | dark-factory recorder (E3) |
| `plans` | `plan-judgement` | the 14 fields of the `plan-judgements` front-matter block (`plan`, `spec`, `author`, `effort`, `words`, `tasks`, `judges[]`, `judges_dropped[]`, `scores[14]`, `total`, `self_score`, `threshold`, `decision`, `revision`), `judged_ts` (first git commit time, RFC3339 Z), `judgement_path` (repo-relative `docs/reviews/plan-judgements/*.md`); every field validated by `judgements.validate_judgement` | evidence ingest judgements (P6) |
| `ledger/openrouter-usage` | `openrouter-usage` | `src` (`broker`), `instance` (id), `request_id` (32 hex), `ts_epoch` (num), `streamed` (bool), `http_status` (int), `status` (`ok|no-usage|unparsed`); nullable `gen_id`, `model` (model-id), `provider`, `cost_usd`, `upstream_cost_usd`, `is_byok`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `cached_tokens`, `cache_write_tokens`, `reasoning_tokens`; key `(instance, request_id)` | evidence ingest openrouter-usage (SP8) |
| `ledger/otel-claude` | `otel-claude` | key `(session_id, sample_id)`; `src` (`otel`), `sample` (`request|tokens`), `at` (RFC3339 Z); nullable `model` (model-id), `model_suffix`, `harness_version`, `terminal_type`, `query_source`, `speed`, `effort`, `agent_name`, `skill_name`, `request_id`, `cost_usd` (num), `duration_ms`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` (int), `token_type` (`input|output|cacheRead|cacheCreation`), `value` (num); refuses an identity attribute (`user`/`organization` first token), a missing `session.id` / non-numeric `timeUnixNano`, a missing `request_id`, and a non-model-id `model` | evidence ingest otel (SP7) |
| `ledger/*.jsonl` | per `tools/ledger/schema.md` | the token/cost ledger; unchanged shapes; idempotent merge, the one non-append-only area | `tools/ledger/factory.py` (E4) |

Readers: `pkgs/helm/collect.py` (tiles), `evidence bundle` (E9), `tools/ledger/factory.py`.
A reader skips a torn line and never fails the whole read on one bad row.
A reader of `<stream>.jsonl` also reads every sibling `<name>-YYYY-MM.jsonl`
(monthly partition; `^<name>-\d{4}-\d{2}\.jsonl$`) after the base file, in name
order; any other sibling is ignored and the writer still names one file.
The claims file `docs/ledger/claims.toml` is NOT a stream: it is policy, in the repo (E2).