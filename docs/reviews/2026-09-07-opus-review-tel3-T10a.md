---
plan_defect: none
mutants_total: 21
mutants_killed: 14
mutants_outside_named: 14
reviewer: opus
majors: 1
minors: 6
---
# Opus gate — seat run tel3, task T10a — APPROVED

## Summary

Branch `task/T10a` in `/home/dalhaka/factory/ws/tel3/T10a`, base
`5f22a92d6875405f7469f046bfe7be99db26f602`, head `8875436`. Reviewed in a fresh
clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/2e56f544-dc33-4c36-836e-c2b840c3e5fc/scratchpad/gate-tel3-T10a/gate-tel3-T10a`.
Nothing under `/home/dalhaka/factory` was modified; `/var/lib/evidence` was
never read or written — every store in this review lives under the scratchpad
and was reached through `--store`/`EVIDENCE_STORE`.

Every numbered item of the section's Interfaces is met in code. All seven
mutants the section names die, each on the row that must kill it, with the exact
counts the plan predicted (`['K1','K2'] == ['K1','K2','K3']` and
`['K1','K2','K3','K4'] == ['K1','K2','K3']`). Red before green reproduces: the
base's `pkgs/evidence/evidence.py` against the branch's test file fails all
seven tests. All four acceptance surfaces are green with `--rebuild`, plus
`githooks/pre-commit` (exit 0, tree clean), ruff, the repomap and `tasks.py
check`. The commit is one, its subject byte-identical, both trailers present.

Beyond the fixtures I ran the real thing: 172 gate rows ingested from this
tree's `docs/reviews` by T3's `ingest_reviews.py` into a scratch store (27 of
them legacy) all carry a `run_id` and a `key`, and `join_tasks_gates` pairs all
172 against synthesised task rows; a 172-row stream split into
`gates.jsonl` + `gates-2026-08.jsonl` + `gates-2026-09.jsonl` with two decoy
siblings (`gates-2026-09.jsonl.bak`, `gates-old.jsonl`) reads back as exactly
172 rows in the right order.

Six MINORs, all of the same shape: stated contracts the test file does not pin
(the two `kind` filters, sibling name order, task file order, the pattern's `$`
anchor, a non-zero `with_activity`), plus the missing red/green paste in the
commit body. None is a defect in the shipped code — I verified each behaviour is
correct — so none is a MAJOR. **APPROVED.**

## Contract items

| # | the section's Interfaces sentence | verdict | evidence |
|---|---|---|---|
| 1 | `read(store, stream)` returns `<stream>.jsonl`'s rows **followed by** every sibling `<stream>-YYYY-MM.jsonl` | met | `pkgs/evidence/evidence.py:107-122`; base rows then siblings at 116/121-122; test `tests/evidence/test_join.py:167-182` asserts `["K1","K2","K3"]` |
| 2 | the `^<name>-\d{4}-\d{2}\.jsonl$` pattern; any other sibling ignored | met | `evidence.py:117` `month_re = re.compile(r"^" + re.escape(name) + r"-\d{4}-\d{2}\.jsonl$")`; `tasks-notamonth.jsonl` ignored (`test_join.py:178-182`); my split-store run ignored `gates-2026-09.jsonl.bak` and `gates-old.jsonl` (172 rows read, not 174) |
| 3 | in name order | met (untested — MINOR-3) | `evidence.py:118-120` `sorted(...)` |
| 4 | torn lines skipped as today | met | `_read_rows` extracted verbatim from the old `read` at `evidence.py:93-105`; the fixture writes a torn line at `test_join.py:174-175` and the count stays 3 |
| 5 | `[]` when nothing exists | met | `evidence.py:112-115` (`parent.exists()` guard, then `path.exists()`); exercised by the empty-store bundle at `test_join.py:220-231` |
| 6 | `stream_path` unchanged (writers still name one file) | met | `git diff <base>..HEAD -- pkgs/evidence/evidence.py \| grep 'def stream_path'` → no output; only its two call sites move |
| 7 | `join_tasks_gates(store)` → one entry per `derived/tasks` row (`kind task-result`) | met (the `kind` filter untested — MINOR-2) | `evidence.py:214` |
| 8 | in file order | met (untested — MINOR-4) | `evidence.py:229-241` iterates `tasks` in read order |
| 9 | entry shape `{"run_id","key","task","gate","activity"}` | met | `evidence.py:232-240`; pinned at `test_join.py:148-150` |
| 10 | the gate is the newest `derived/gates` row with the same `(run_id, key)`, taken from the row's own `run_id`/`key` fields | met | `evidence.py:216-221` keys on `(g.get("run_id"), g.get("key"))`; `test_join.py:63-85` (two runs, one key) |
| 11 | "newest" = max by `(review_commit_ts or "", ts)` | met | `evidence.py:205-207` `_gate_key`; both arms at `test_join.py:88-130` (unequal commit_ts, then equal commit_ts with the later `ts`) |
| 12 | a legacy-H1 file's name-derived key still joins | met | not a T10a code path (T3 populates it); verified live-shaped: 172/172 ingested rows have `run_id` and `key`, 27 legacy, `missing run_id or key: 0`, and all 172 join |
| 13 | a gate row whose `(run_id, key)` matches no task is not returned | met | `evidence.py:229` iterates tasks only; `test_join.py:133-150` asserts `len(joined) == 1` against a planted orphan `r9/K9` |
| 14 | `activity` = the `ledger/activity-days` row for `(result_mtime[:10], model)` | met | `evidence.py:222-227, 231, 238`; `test_join.py:153-164` (matching model joins, wrong model does not) |
| 15 | a missing stream reads as `[]` (activity does not exist until T4) | met | `test_join.py:150` `activity is None`, no exception |
| 16 | `n_gate(rows, n=5)` → `rows` when `len >= n`, else `insufficient (n=<len>)` | met | `evidence.py:244-248`; `test_join.py:185-190` pins `"insufficient (n=4)"`, `is rows5`, and `n=3` at 3 |
| 17 | exported for T10b / the ladder report | met | module-level `def n_gate` at `evidence.py:244`; no `__all__` in `pkgs/evidence/*.py` to update (`grep -n '__all__' pkgs/evidence/*.py` → exit 1) |
| 18 | `bundle()` gains `"join": {"tasks","with_gate","with_activity"}`, `{0,…}` when the streams are absent | met (non-zero `with_activity` unexercised — MINOR-6) | `evidence.py:386-392, 402`; `test_join.py:216, 228` |
| 19 | `render_bundle_markdown` prints, **after the Helm section**, `## Join: {t} task rows, {g} with a gate verdict, {a} with activity`, one line | met | `evidence.py:448-454`, inserted between the Helm block (ends 451 in the old numbering) and the Claims block; `test_join.py:218, 229-231` |
| 20 | the heading is what Operator step 6 greps (`^## Join`) | met | my scratch-store bundle printed `## Join: 172 task rows, 172 with a gate verdict, 0 with activity` at column 0 |
| 21 | `pkgs/evidence/SCHEMA.md` states the monthly file rule | met | `pkgs/evidence/SCHEMA.md:28-30` |
| 22 | regression: the existing `read` tests and `latest_check` stay green | met | `nix develop -c pytest tests/evidence -q` → `399 passed, 1 skipped`; `evidence-unit` 400 passed |

No stated contract is violated by the code.

## Red before green

The section's Step 2 command, run with the base's implementation file checked
out under the branch's test file:

```
$ git checkout 5f22a92d6875405f7469f046bfe7be99db26f602 -- pkgs/evidence/evidence.py
$ nix develop -c pytest tests/evidence/test_join.py -q
…
>       assert b["join"] == {"tasks": 3, "with_gate": 2, "with_activity": 0}
               ^^^^^^^^^
E       KeyError: 'join'

tests/evidence/test_join.py:216: KeyError
=========================== short test summary info ============================
FAILED tests/evidence/test_join.py::test_join_two_runs_sharing_key_each_reads_its_own_gate
FAILED tests/evidence/test_join.py::test_join_newest_gate_by_commit_ts_then_ts
FAILED tests/evidence/test_join.py::test_join_missing_gate_orphan_gate_and_missing_activity
FAILED tests/evidence/test_join.py::test_join_activity_present - AttributeErr...
FAILED tests/evidence/test_join.py::test_read_includes_monthly_siblings_not_other_files
FAILED tests/evidence/test_join.py::test_n_gate_boundary - AttributeError: mo...
FAILED tests/evidence/test_join.py::test_bundle_join_counts_and_markdown - Ke...
7 failed in 0.14s
```

All seven are red, and the two reds the section predicts are both there: the
`AttributeError: module 'evidence' has no attribute 'join_tasks_gates'` arms and
the `read` row (which at the base returns 2 rows, not 3 — see mutant M4a for the
same assertion's message). Restored, the same command is `7 passed in 0.14s`.
Every one of the seven is load-bearing: each is the only test of its Interfaces
sentence, and each dies under at least one mutant below.

## Mutants

Applied one at a time in the clone with `git checkout HEAD -- pkgs/evidence/evidence.py`
between each; the clone was verified clean (`git status --porcelain` empty) and
green afterwards.

**Named by the section — 7 tried, 7 killed.**

| # | row | mutant | result | failing line |
|---|---|---|---|---|
| M1 | 1 | join on `key` alone (`k = (g.get("key"),)`, lookup `newest.get((key,))`) | **killed** | `test_join.py:84` `E + approved` (r1 reads r2's verdict) |
| M2 | 2 | take the first (`if cur is None:`) | **killed** | `test_join.py:110` `E + rejected` |
| M3 | 3 | raise on the missing stream (`_read_rows(stream_path(...))`, no guard) | **killed** | `E FileNotFoundError: [Errno 2] No such file or directory: '…/nostore/derived/tasks.jsonl'`, `pkgs/evidence/evidence.py:95` |
| M4a | 4 | drop the glob (`siblings = []`) | **killed** | `test_join.py:182` `E AssertionError: assert ['K1', 'K2'] == ['K1', 'K2', 'K3']` — the plan's predicted 2 |
| M4b | 4 | admit any sibling (`p.name != path.name`) | **killed** | `test_join.py:182` `E AssertionError: assert ['K1', 'K2', 'K3', 'K4'] == ['K1', 'K2', 'K3']` — the plan's predicted 4 |
| M5 | 5 | `>` for `>=` in `n_gate` | **killed** | `test_join.py:189` `E AssertionError: assert 'insufficient (n=5)' is [1, 2, 3, 4, 5]` |
| M6 | 6 | drop the markdown join line | **killed** | `test_join.py:218` `E AssertionError: assert '## Join: 3 task rows, 2 with a gate verdict, 0 with activity' in '# Evidence bundle — …## Helm now…## Claims: 0 verified…'` |

Row 7 names no mutant (it is the regression row); it is discharged by the full
suite and `evidence-unit`.

**Outside the named set — 14 tried, 7 killed, 7 survived.** All run against the
whole `tests/evidence` suite (400 tests), not just the new file.

| # | mutant | result |
|---|---|---|
| X1 | `_gate_key` drops `review_commit_ts`, keys on `ts` alone | killed (`test_join.py:110`) |
| X2 | activity joined on the date alone | killed (`test_join.py:164`) |
| X3 | drop the `kind == "task-result"` filter on `derived/tasks` | **survived** → MINOR-2 |
| X4 | drop the `kind == "gate-verdict"` filter on `derived/gates` | **survived** → MINOR-2 |
| X5 | siblings sorted `reverse=True` | **survived** → MINOR-3 |
| X6 | `n_gate` returns `list(rows)` instead of `rows` | killed (`test_join.py:189`, the `is` assertion) |
| X7 | `read` never reads the base file, only siblings | killed (46 failures across `test_evidence.py` and `test_streams_policy.py`) |
| X8 | `bundle`'s `with_activity` hardcoded to `0` | **survived** → MINOR-6 |
| X9 | `bundle`'s `with_gate` = `len(joined)` | killed (`test_join.py:216`) |
| X10 | drop the `$` anchor from the month pattern | **survived** → MINOR-5 |
| X12 | siblings emitted *before* the base file | killed (`test_join.py:182`) |
| X13 | `return out[::-1]` (join output not in task file order) | **survived** → MINOR-4 |
| X15 | `_gate_key` drops `ts`, keys on `review_commit_ts` alone | killed (`test_join.py:110`) |
| X16 | `>=` for `>` when picking the newest gate | **survived** — equivalent under the stated contract (which of two rows with an identical `(review_commit_ts, ts)` wins is not specified); recorded, not charged |

Totals: **21 tried, 14 killed, 14 outside the named set.**

## Checks

Run in the fresh clone with `XDG_CACHE_HOME` under the scratchpad. Nothing was
suppressed with `2>/dev/null`.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **pass** — `evidence-unit> 400 passed in 10.05s`, exit 0 |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass** — exit 0 |
| pre-commit | `nix develop -c githooks/pre-commit` | **pass** — `All checks passed!`, `render.test.mjs: all assertions passed`, exit 0; `git status --porcelain` empty afterwards (the queue block is already regenerated in the commit) |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | **pass** — `All checks passed!` |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | **pass** — `79 files already formatted` |
| repomap | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | **pass** — exit 0, no diff (`tests/evidence — 82 files` already committed) |
| task graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | **pass** — silent, exit 0 |
| suite | `nix develop -c pytest tests/evidence -q` | `399 passed, 1 skipped` |

Fixture smoke, never touching `/var/lib/evidence` (store under the scratchpad):

```
$ python3 pkgs/evidence/ingest_reviews.py --store <scratch>/store reviews . <scratch>/runs --runs-root <scratch>/runs
ingested 172 gate rows (docs/reviews: 172, H1 parsed 145, blocks 26, legacy 27; runs: 0)

gate rows: 172
missing run_id or key: 0
distinct (run_id,key): 172
joined: 172 with_gate: 172 with_activity: 0
bundle join: {'tasks': 172, 'with_gate': 172, 'with_activity': 0}
['## Join: 172 task rows, 172 with a gate verdict, 0 with activity']
n_gate(4): insufficient (n=4)

split read: 172 expected 172          # base + gates-2026-08 + gates-2026-09,
                                      # with gates-2026-09.jsonl.bak and
                                      # gates-old.jsonl planted and ignored
first of month-08 block at index 100: True
```

The section's Facts quote the live 2026-09-06 numbers (237 tasks, 142 with a
verdict); they are stale by construction and are the operator's step 6 to
recount. No live store was read here.

## Touches and commit

Diff `5f22a92..8875436`:

```
 docs/MAP.md                 |   2 +-
 docs/OPERATIONS.md          |   2 +-
 pkgs/evidence/SCHEMA.md     |   3 +
 pkgs/evidence/evidence.py   |  85 +++++++++++++++-
 tests/evidence/test_join.py | 231 ++++++++++++++++++++++++++++++++++++++++++++
 5 files changed, 316 insertions(+), 7 deletions(-)
```

- `tests/evidence/test_join.py`, `pkgs/evidence/evidence.py`, `pkgs/evidence/SCHEMA.md` — the section's three `touches`.
- `docs/MAP.md` — the Global Constraints' first standing exception; regenerating it is a no-op (`git diff --exit-code` clean).
- `docs/OPERATIONS.md` — the board's queue block, the second standing exception. Proved confined: stripping the `<!-- tasks:begin -->…<!-- tasks:end -->` interior from both revisions leaves the two files byte-identical (`outside-block identical: True | lines: 40 40`). The single changed line drops `T10a` from the queued list. Not a finding.

Nothing else is in the diff. **The plan file is untouched. There is no board commit.**

Commit convention:

- **Exactly one commit** — `git log --format='%h %s' 5f22a92..HEAD` → one line, `8875436`.
- **Subject byte-identical** to the section's `commit subject` — `diff <(git log -1 --format=%s) <(printf '%s\n' "evidence: … (test: evidence-unit, lint)")` is empty.
- **Both trailers**, after a blank line, in the WORKSPACE RULES' order:
  `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run tel3)` then
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- **The body states the why** (four lines: monthly partitions, task rows paired
  with gate verdicts and activity, feeding the ladder report and the bundle's
  join section) but **pastes no red and no green** — MINOR-1.

The seat's NOTES claim of "a single amended commit with both trailers" is
accurate as the branch stands.

## Findings

### MINOR-1 — the commit body pastes neither the red nor the green

`git log -1 --format=%B` (commit `8875436`), `pkgs/evidence/evidence.py` — the
whole change.

The body is four lines of prose plus the two trailers; there is no command
output in it. The Global Constraints ask for it ("TDD: the failing check first,
**shown red with its output**, then green"), and the gate's commit rule asks the
body to paste the red and the green. Unlike T1W, this section names no mutant
row whose only record would be that paste, so it is a record-keeping gap, not a
lost assertion: I reproduced the red independently (all seven tests fail against
the base's `evidence.py`) and the work is genuinely red-first. Classed as MINOR
for consistency with the T2 gate (MINOR-7) and the T3 gate (MINOR-7); T1W's
MAJOR-3 turned on a section-specific paste requirement that T10a does not have.
**Fix (if a fix round runs for other reasons):** amend the body with the
seven-failure pytest summary and the `7 passed` counterpart.

### MINOR-2 — both `kind` filters are stated in Interfaces and untested

`pkgs/evidence/evidence.py:214-215`

```python
    tasks = [r for r in read(store, "derived/tasks") if r.get("kind") == "task-result"]
    gates = [r for r in read(store, "derived/gates") if r.get("kind") == "gate-verdict"]
```

The section's Interfaces say "one entry per `derived/tasks` row (`kind
task-result`)". Deleting either filter (mutants X3, X4) survives all 400 tests,
because `tests/evidence/test_join.py` never plants a foreign-kind row in either
stream. In practice the fence makes such a row hard to write (`streams.py:267,
315` bind each stream to one kind), so the filters are defensive — but they are
stated, so they should be pinned. **Fix:** write one row of another kind into
`derived/tasks.jsonl` by hand (the test already writes a raw line at
`test_join.py:174`) and assert it is not joined.

### MINOR-3 — the monthly siblings' "name order" has no discriminating fixture

`pkgs/evidence/evidence.py:118-122`; fixture `tests/evidence/test_join.py:176-180`

The Interfaces say the siblings are read "in name order", but the fixture
contains exactly one monthly sibling, so `sorted(..., reverse=True)` (mutant X5)
survives the whole suite. The shipped code is correct; the assertion is missing.
**Fix:** add a `tasks-2026-08.jsonl` alongside `tasks-2026-09.jsonl` and assert
the August rows precede the September ones.

### MINOR-4 — "in file order" for the join output is untested

`pkgs/evidence/evidence.py:229-241`; `tests/evidence/test_join.py:82-85, 161-164`

The Interfaces say `join_tasks_gates` returns "one entry per `derived/tasks` row
… **in file order**". Every multi-task assertion in the test file first
re-indexes the result by `run_id` or `key` (`by_run = {…}`, `joined = {j["key"]:
j …}`), so `return out[::-1]` (mutant X13) survives all 400 tests. **Fix:** one
`assert [j["key"] for j in joined] == ["K1", "K2", "K3"]`.

### MINOR-5 — the month pattern's `$` anchor is untested

`pkgs/evidence/evidence.py:117`

```python
    month_re = re.compile(r"^" + re.escape(name) + r"-\d{4}-\d{2}\.jsonl$")
```

The Interfaces quote the anchored pattern. The fixture's only decoy
(`tasks-notamonth.jsonl`) discriminates the prefix, not the suffix, so dropping
the `$` (mutant X10) survives all 400 tests — under that mutant a
`tasks-2026-09.jsonl.bak` would be read as a partition. The shipped code is
right: my split-store run planted `gates-2026-09.jsonl.bak` and read back 172
rows, not 173. **Fix:** add a `tasks-2026-09.jsonl.bak` decoy to the fixture.

### MINOR-6 — `bundle`'s `with_activity` count is never non-zero in any test

`pkgs/evidence/evidence.py:390`; `tests/evidence/test_join.py:216, 228`

`"with_activity": sum(1 for j in joined if j["activity"] is not None)` can be
replaced by the literal `0` (mutant X8) and all 400 tests pass: row 6's fixture
has no activity rows and the empty-store arm expects zero too. The plan is the
cause — row 6 asks only for `0` — and `join_tasks_gates`' own activity join is
tested at `test_join.py:153-164`, so the exposure is confined to the counting
line in `bundle()`. **Fix:** add one `ledger/activity-days` row to row 6's store
and assert `with_activity == 1`.

## Verdict

**APPROVED.** Every Interfaces sentence of the section is met in code; all seven
named mutants die on the rows the section assigns them, with the predicted
counts; red before green reproduces on all seven tests; every acceptance surface
is green with `--rebuild`; the diff is inside `touches` plus the two standing
exceptions, with the board change proved confined to the queue block; one
commit, subject byte-identical, both trailers. The six MINORs are all missing
assertions around behaviour I verified to be correct, plus the body paste — none
is owed before landing. `plan_defect: none`.
