# Telemetry store, sub-project 1 — the fence, the `tasks` and `gates` streams, the join (spec for the planning agent, 2026-09-06)

**Operator, 2026-09-06 ~09:40 CDT:** "If you can get those 4 telemetry tasks
done I will approve those." The four are T1, T2, T3 and T10a of the telemetry
store design (`docs/superpowers/specs/2026-09-05-telemetry-store-design.md`,
committed 1473a22; every task T1–T18 approved by
`docs/decisions/2026-09-05-telemetry-store-decisions.md`). That design is
16,864 words — an L, which the planning agent refuses — so this sub-project
spec carries the four tasks' contracts in full, re-verified against the tree
at a53d2e5, and names the design's sections as the record of *why*. Where
this spec and the design disagree, this spec is the newer fact.

**Goal.** Every row entering `/var/lib/evidence` passes one allowlist; every
seat result and every gate review becomes a row; a reader joins them. This is
the floor the seat-driver spec's ladder report stands on
(`docs/superpowers/specs/2026-09-06-operator-seat-driver-design.md`, §6).

**Invariants touched:** none of brief §3. The store stays operator-only (the
telemetry decision, answer 1); nothing new leaves the machine; no credential
moves. The exclusion rule of design §3.5 (identifiers, enums, numbers,
timestamps, hashes, sizes — never free text) is the policy this sub-project
makes enforceable.

## What exists (verified 2026-09-06 at a53d2e5)

- `pkgs/evidence/evidence.py`: `VERSION = 1` stamped on every stream
  (line 28), `STREAM_RE`, `append()` under an exclusive flock (the envelope
  `{v, ts, kind}` written after the caller's row), `read()`, `latest_check()`,
  `bundle()`; the CLI `evidence record --json <object-with-kind> <stream>`,
  `record-check`, `latest-check`, `bundle`, `tasks`, `repomap`. No allowlist:
  `record` accepts any object that has a `kind`.
- `pkgs/evidence/SCHEMA.md` (v1): streams `checks` (kind `check`),
  `helm-status`, `runs` (kind `factory-run`, shape A — the dark factory's
  recorder, which has never run on core), `plans` (kind `plan-judgement`),
  `ledger/*` (per `tools/ledger/schema.md`).
- **One fence exists already:** `pkgs/evidence/judgements.py`
  `validate_judgement(fields)` — the 14 allowlisted fields of the
  plan-judgement block, every string ≤ 200, free text refused (plan
  2026-09-06-planning-agent, P6b). There is no `streams.py`.
- Writers that bypass the library today: `pkgs/helm/collect.py:738
  _append_status_row` (called from `record_status`, :774);
  `tools/ledger/factory.py:74 _write_jsonl` and `:80 _merge_jsonl` (the
  `ledger/*` files; never run on core). `nixosModules/helm.nix:121` already
  embeds the whole `pkgs/evidence` directory for the collector; `:150`
  records the nightly `flake-check` through `record-check`.
  `tools/factory/seat/factory-lib.sh:82 factory_record_check` records the
  integrator's checks.
- Results: 237 `.result` files under `~/factory/runs/*/` (2026-09-06 09:40);
  each carries the `FACTORY-RESULT` block, `model:`, and since RT1 `effort:`
  and `route:`; the `usage:` line from `factory-usage.py`. No result carries a
  plan reference. `factory-task` writes the result at `} >"$result"`.
- Reviews: 164 `docs/reviews/*opus-review*.md`; the H1
  `# Opus gate — seat run <run>, task <key> — APPROVED|REJECTED` is parsed by
  `REVIEW_RE` (`pkgs/evidence/tasks.py:63`); 25 files open with the
  front-matter block that P3A introduced — keys `plan_defect`,
  `mutants_total`, `mutants_killed`, `mutants_outside_named`, optional
  `plan_defect_secondary` — and `tasks.py check` requires that block on every
  review dated from 2026-09-07 (`docs/ledger/plan-defects.toml`,
  `front_matter_from`). `_split_front_matter` (`tasks.py:217`) reads it.
- The seat's DeepSeek reviews (`factory-review`) leave a `.review.md` with a
  verdict line under the run directory.
- Tests: `tests/evidence/` (`test_evidence.py`, `test_tasks.py`,
  `test_judgements.py`, `test_report.py`, …) under check `evidence-unit`;
  `factory-unit` and `unit` (bats) cover the driver.
- The rules of record: every writer keeps today's rule — a recording problem
  is logged and never fails the caller; every ingest that takes a path binds
  it to a declared root and exits non-zero outside it (design §3.4).

## Design — the four tasks

### T1 (code, M) — the fence: `pkgs/evidence/streams.py`, every writer through `append()`

1. `streams.py` holds one dict per kind: field → class, nested shapes, map
   key patterns and entry caps, list element classes, and the per-stream
   version map (`v` becomes per stream; `checks` stays v1 here — v2 is T18,
   not in this sub-project). Kinds declared: `check` (v1, as SCHEMA.md),
   `helm-status`, `factory-run` shape A (the recorder's literal in
   `tools/factory/dark-factory.js` must validate unchanged) and shape B
   (`factory-wave` start/end rows, design §3.3 — declared now, written by
   T16 later), `plan-judgement` (the 14 fields — `judgements.py`'s list
   becomes this entry and `validate_judgement` calls the shared validator,
   so there is one allowlist), `task-result` (T2's fields), `gate-verdict`
   (T3's fields), `activity-day` (design §3.3, written by T4 later), and the
   five `ledger/*` shapes of `tools/ledger/schema.md`.
2. String classes, exactly: `enum`; `id` `^[A-Za-z0-9._:+-]{1,120}$`;
   `model-id` `^[a-z0-9][a-z0-9._-]{0,63}(/[a-z0-9][a-z0-9._-]{0,63})?$`;
   `key` `^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$`; `rev` 40 hex; `ts` RFC3339 `Z`;
   `hash` 64 hex; `rooted path` declared per field with its roots and cap,
   resolved under a root, no `..`, no newline. A string matching no class is
   refused, never capped.
3. `append()` validates before taking the lock: an undeclared kind, field,
   enum value, class miss, map key or list element outside its pattern at any
   depth, a map over its cap, or a row over 16 KB → exit 2, nothing written.
   `validate(kind, row) -> list[str]` and `replace_stream(store, stream, rows)`
   (atomic rewrite by key under the same lock) are the library's two other
   entry points.
4. Forbidden names (design §3.5 fence 2): exact match on the case-folded
   name with `-`/`_` normalised, at every depth including map keys — the
   list as written there (`prompt` … `slug`). Declared exceptions are
   rooted-path entries: `factory-findings.file`, `tasks.result_path`
   (`~/factory/runs/`), `gates.review_path` (`docs/reviews/`, `runs/`),
   `tasks.plan`/`runs.plan` (`docs/superpowers/plans/`), `checks.log_tail`
   in v1 only.
5. Secret shapes (fence 4): every string scanned for `sk-or-v1-`, `sk-ant-`,
   `Bearer `, `-----BEGIN`, `AKIA[0-9A-Z]{16}`, `ghp_`, `xox[bp]-`,
   `AGE-SECRET-KEY-`, word-initial `age1`, word-initial `eyJ`.
6. Writers: `collect.py` imports `evidence` and `record_status` calls
   `append()`; `_append_status_row` is deleted. `factory.py`'s
   `_write_jsonl`/`_merge_jsonl` route through `validate()` per record and
   `replace_stream()`.
7. The lint gate gains a grep that refuses `O_APPEND`, `open(…, "a")` and a
   literal `/var/lib/evidence` outside `pkgs/evidence/evidence.py` under
   `pkgs/evidence`, `pkgs/helm`, `tools/ledger`, `tools/factory` and the two
   hook scripts (`tools/session-start.sh`, `tools/ritual.sh`). A unit test
   runs each writer against a temp store with `os.open` wrapped and asserts
   the only opener of a store path is `append`/`replace_stream`.

Tests, each red before the change: `tests/evidence/test_streams_policy.py`
with a valid and an invalid fixture per kind and the declared-field walk
(every declared field of every kind passes the name fence); the mutations
(a)–(j) of design §3.5 verbatim: a row with `"prompt": "x"`; a 201-char
sentence in a string field; `sk-or-v1-abc` in a string; the v1 `log_tail`
entry deleted; each fence tested with the other removed; a direct-open test
module; a hostile `FACTORY-CHECKS` key of 4 KB (`checks_parse: refused`); the
tile status object handed to a writer; a path-shaped or address-shaped id;
a `>>` row without an envelope (audit-only — recorded as a T17 dependency,
not tested here). Acceptance: `evidence record` refuses an undeclared kind,
field, class and key; `test_judgements.py` still passes unchanged; the
recorder's shape-A literal validates.

### T2 (code, S) — the `tasks` stream: `evidence ingest result`, `error_class`

1. `evidence ingest result <path>`: the path must resolve under
   `~/factory/runs/` (else exit non-zero); one `task-result` row per file,
   key `(run_id, key)`, idempotent (a re-ingest replaces by key through
   `replace_stream`); the derived stream lives at
   `/var/lib/evidence/derived/tasks.jsonl`. Fields as design §3.3 `tasks`:
   `run_id`, `key`, `repo`, `plan` (rooted or null), `kind`/`size` from the
   `route:` line (`unknown` when absent), `model`, `effort` (`unknown`
   without an `effort:` line), `route` (pattern
   `^(explicit|unknown|implement/(code|docs)/(XS|S|M|L))$`), `status`,
   `exit_code`, `wall_s`, `commits` (counted from the list) and
   `commits_declared` (the `FACTORY-COMMITS` number), `checks` (map, key
   pattern `^[a-z][a-z0-9-]{0,63}$`, ≤ 64) with `checks_parse`
   `ok|refused|missing`, `head`, `base`, `files_changed`, `insertions`,
   `deletions`, `usage {input, output, cache_read, reasoning, events,
   duration_s}`, `error_class`, `seat_unit`, `result_path`, `result_mtime`.
   `FACTORY-NOTES` is dropped. The log is never read by the ingest.
2. `error_class` is a function in `factory-lib.sh` run by `factory-task` at
   task end, over metadata and a fixed pattern list applied to the last 4,000
   bytes of the log; it prints one enum word into the result block. The
   table, exactly: `budget-402` (a `402` with `budget_exhausted`),
   `provider-error` (`502`, `503`, `529`, `upstream`, `provider`),
   `unknown-model` (`UNKNOWN_MODEL`), `boot-failure` (`wall_s` < 10 and
   `usage.events` < 50 and no pattern), `no-result-line` (the driver
   synthesised the block), `template-echo` (`status=done` with an empty
   commit list — CR3r refuses it going forward; classified for old files),
   `timeout` (`exit_code` 124), `submit-failed` (the `seat: submit failed`
   line), `killed` (no result and a `.killed-by-*` log — recorded on the
   `runs` end row, T16), `none`.
3. One line in `factory-task` after `} >"$result"`:
   `evidence ingest result "$result" || factory_log "evidence: could not record $key"`.
   The driver runs on the host as the wave's child, outside the seat unit.

Tests, red first: the 4,000-byte bound (a 1 MB fake log must not make the
test slow — mutant: drop the bound); the exit-124 rule (mutant: drop it → the
timeout fixture reads `none`); the hostile-`FACTORY-CHECKS` fixture
(`checks_parse: refused`, no key over 64 chars stored); a synthetic
`status=done` with no commits → `template-echo`; `ingest result /etc/passwd`
exits non-zero; a re-ingest of the same file leaves one row. Acceptance on
core (the operator's step, one loop over every existing result — 237 today):
one row per file; the failed results classify without anyone opening a log.

### T3 (code, M) — the `gates` stream: the front-matter block completed, `ingest reviews`

1. **One block, not two.** The existing P3A block is extended, never
   duplicated: new keys `reviewer` (`opus|sonnet|deepseek|fable|unknown`),
   `majors`, `minors` (integers). `run`, `key` and `verdict` stay in the H1
   and are read by `REVIEW_RE`; the block never carries a verdict, so the
   two sources cannot disagree. The lint (in `tasks.py check`, which the
   lint gate already runs) refuses a review dated from 2026-09-07 without
   the block, with an unknown key, with a non-integer count, or with an H1
   verdict outside `APPROVED|REJECTED`; older reviews are read as they are.
2. A migration script (kept in the tree, re-runnable, idempotent) adds
   `reviewer: opus` and the counts to the 139 reviews without a block,
   from the `MAJOR`/`MINOR` markers and the `N/M` or `N killed` mutation
   forms where they parse, `null` where they do not; it never writes
   `plan_defect` (that key is the ledger's, and `tasks.py check` must stay
   silent after the script runs). The 164 edited files land as one docs
   commit.
3. `evidence ingest reviews <repo> <runs-dir>`: roots `docs/reviews/` of the
   repo and `~/factory/runs/`; one `gate-verdict` row per file, key
   `review_path`, into `/var/lib/evidence/derived/gates.jsonl`. Fields as
   design §3.3 `gates`: `run_id`, `key`, `chain_root` (per
   `tasks.py chain_root()`), `round_kind` (`first|fix|replan|unknown` —
   `b`/`c` = fix, `r`/`rb` = re-plan), `round`, `reviewer`, `route`, `model`,
   `verdict` (`approved|rejected|unknown|none` — no `rework`), `majors`,
   `minors`, `mutants_total`, `mutants_killed`, `gate_tokens`, `wall_s`,
   `review_path`, `review_sha256`, `review_commit`, `review_commit_ts` (from
   `git log` of the `docs: gate review` commit). The DeepSeek `.review.md`
   verdict line under a run directory yields a row with `reviewer: deepseek`,
   `route: openrouter`. The body of a review never enters the store.
4. One line in `factory-integrate` after the review commit:
   `evidence ingest reviews "$repo" "$runs" || factory_log "evidence: could not record reviews"`.
   The rollup timer that would also run it is T8's, not this sub-project's.

Tests, red first: a review with `verdict: rework` in the H1 fails the lint
(mutant: accept it → the test fails); the H1 removed → the `REVIEW_RE` test
fails; the migration script on the fixture corpus is byte-identical on its
second run; a block with a second `plan_defect` source is refused; the ingest
refuses a path outside its roots. Acceptance: 164 + the `.review.md` rows on
core; the automatic parse count (104 H1 verdicts at the design's sample;
recount at landing) printed by the ingest; `tasks.py check` silent after the
migration commit.

### T10a (code, S) — the reader and the join

1. `evidence.read()` learns the derived directory and monthly globs
   (`<stream>-YYYY-MM.jsonl`), skipping torn lines as today.
2. `join_tasks_gates(store)`: one row per `task-result` with the newest
   `gate-verdict` for the same `(run_id, key)` — never on `key` alone — and
   the `activity-day` row for `(date, model)` when one exists (T4 writes
   those later; the join tolerates their absence).
3. The n-gate helper `n_gate(rows, n=5)` returns the rows or the string
   `insufficient (n=…)`; every report built later (T10b, the seat-driver
   spec's `report ladder`) calls it and prints nothing else below n.

Tests, red first: two runs sharing a key with different verdicts — a join on
key alone fails the fixture (the named mutant); a monthly-glob fixture with a
torn line; `n_gate` at n = 4 refuses. Acceptance on core: after T2's loop
and T3's ingest, the join yields one row per result with its verdict where a
review exists. T6 (the full migration: `ingest runs`, `rebuild --derived`,
the other sources) is not in this sub-project; the live rows come from T2
and T3 alone.

## Waves, touches, conflicts (for the plan to confirm from `tasks.py`)

T1 alone first (M; `pkgs/evidence/evidence.py`, `streams.py`,
`judgements.py`, `pkgs/helm/collect.py`, `tools/ledger/factory.py`,
`tests/evidence/`, the lint gate under `flake.nix`/`githooks`). Then T2 and
T3 in one wave only if their `touches` are disjoint: T2 owns
`pkgs/evidence/ingest_result.py` (or the module the plan names),
`factory-lib.sh`, `factory-task`; T3 owns `pkgs/evidence/ingest_reviews.py`,
`tasks.py` (the lint), `factory-integrate`, the migration script and
`docs/reviews/*.md`. Both add a CLI subcommand to `evidence.py`: the plan
either gives `evidence.py` to one of them and has the other register through
a table the first lands, or runs them in sequence. T10a last.

## Operator steps (the plan's `## Operator` section spells the commands)

After T2 lands: the one loop that ingests every existing result. After T3
lands: the migration commit. After T10a: `evidence bundle` prints the join's
row count. Rollback per task: `git revert` of the task's commit; derived
streams are rebuildable, so a bad row is fixed by re-running the ingest.

## Questions for the operator (each with a recommendation and a default)

1. **The migration commit touches 164 review files at once.** Recommendation:
   land it as T3's second commit, gated with T3 (the gate reads the script
   and a sample of the diff, not every file). Default: as recommended.
2. **T10a without T6.** Recommendation: accept the live rows from T2's loop
   and T3's ingest as the join's input now; T6 (runs without results, the
   activity export, transcripts, the audit rollups) is its own task later.
   Default: as recommended.

## Risks weighed

- `judgements.py`'s fence and `streams.py` could drift into two allowlists;
  the declared-field walk and the rule that `validate_judgement` delegates
  keep one source.
- A wrong `error_class` pattern misclassifies silently; the seven failed
  results of design §2.1 are the fixture that pins the table.
- The 139-file migration is a large docs diff the guard must not refuse
  (reviews are not plans); it names no plan path.
- `tasks.py check` is on the lint gate: a stricter review lint that refuses
  an old file would turn the whole gate red — hence "older reviews are read
  as they are".

## Not in this sub-project

T4–T9, T10b–T18 of the design (the activity export, host metrics, the
migration proper, incidents, rollups, access modes, the reports, the Helm
tiles, denials, sessions, the relaunch table, shape-B writers, the audit and
quarantine, `checks` v2); the seat-driver ladder; any change to what a review
says.
