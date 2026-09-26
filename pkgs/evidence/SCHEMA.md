# Evidence store — streams and row shapes (v1)

Directory: `services.evidence-store.path`, default `/var/lib/evidence` (env `EVIDENCE_STORE`
overrides for tests and pre-switch use; every writer also passes `--store` explicitly). One JSONL
file per stream; append-only under flock; every row: `{"v":1,"ts":"2026-09-05T12:00:00Z","kind":"<kind>", ...}`.
Stream names match `^[a-z][a-z0-9-]{0,31}$`. The envelope (`v`, `ts`) is
written after the writer's row, so a writer cannot override v or ts.

| stream | kind | fields | writers |
|---|---|---|---|
| `checks` | `check` | `name` (check name; `flake-check` = the whole `nix flake check`), `rev` (40 hex), `ok` (bool), `class` (`unit|eval|vm|nix-check|curl|browser|operator|unmeasured`), `src` (`helm-nightly`, `seat-integrate`, `dark-factory-verify`, …), `duration_s`?, `log_tail`? (≤ 4000 chars) | helm-flake-check (E5), factory-integrate (E7), dark-factory verify (E3) |
| `helm-status` | `helm-status` | `tiles` (name → `ok|warn|fail|unknown`), `reason` (`change|heartbeat`) | helm-collect (E6) |
| `runs` | `factory-run` | `plan`, `prefix`, `baseline`, `integration_branch`, `tasks[]{key,status,commit,fixRounds}`, `verify` (`pass|fail|skipped|none`), `delivered`, `agents`, `output_tokens`, `run_id`? | dark-factory recorder (E3) |
| `plans` | `plan-judgement` | the 14 fields of the `plan-judgements` front-matter block (`plan`, `spec`, `author`, `effort`, `words`, `tasks`, `judges[]`, `judges_dropped[]`, `scores[14]`, `total`, `self_score`, `threshold`, `decision`, `revision`), `judged_ts` (first git commit time, RFC3339 Z), `judgement_path` (repo-relative `docs/reviews/plan-judgements/*.md`); every field validated by `judgements.validate_judgement` | evidence ingest judgements (P6) |
| `ledger/*.jsonl` | per `tools/ledger/schema.md` | the token/cost ledger; unchanged shapes; idempotent merge, the one non-append-only area | `tools/ledger/factory.py` (E4) |

Readers: `pkgs/helm/collect.py` (tiles), `evidence bundle` (E9), `tools/ledger/factory.py`.
A reader skips a torn line and never fails the whole read on one bad row.
The claims file `docs/ledger/claims.toml` is NOT a stream: it is policy, in the repo (E2).