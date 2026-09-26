---
plan_defect: none
mutants_total: 16
mutants_killed: 15
mutants_outside_named: 4
model: opus
---
# Opus gate — seat run sp67, task SP6 — APPROVED

## Summary

One commit, `c4cf141`, on `task/SP6` over base `ced500a`; eight files, every one
inside the section's `touches` (`docs/MAP.md` exempt by rule); subject
byte-identical to the section's; both trailers present. The section's contract is
met item by item.

The counting rule — the thing this task exists for — is right and is **tested to
be right**. `tools/ledger/factory.py:575` takes `max` per usage field per
`message.id`, in a `by_gid` dict created fresh inside `_read_main_session`
(`:536`), so the grouping is per `(file, message.id)` as §Errata applied G
requires. The fixture discriminates all three readings of the rule: its three
`msg_main_grow` lines carry **growing** output (2 / 2 / 7912) with identical
`input`/cache counts, so `tokens.out` is 7952 under MAX, 42 under first-wins and
7956 under sum. I applied both mutants and both died on the number, not on a
crash:

```
=== M1 first-wins ===
E         {'out': 42} != {'out': 7952}
=== M2 sum ===
E         {'in': 7000} != {'in': 3000}
E         {'cache_read': 102765} != {'cache_read': 34255}
E         {'cache_write': 87150} != {'cache_write': 29050}
E         {'out': 7956} != {'out': 7952}
```

"Numbers only" holds **by rule**, not by fixture luck: the row (`:614–628`) and
each `by_model` entry (`:583–592`) are literal dicts of declared keys; nothing
from the wire is spread into either, and `streams.validate` refuses any
undeclared or forbidden name on top of that. The project slug never enters the
row (it is the parent directory, not read); `cwd`/`gitBranch`/`slug` sit on every
fixture line and reach nothing.

Twelve named mutants, twelve dead. Four mutants outside the named set, three
dead, one survivor (the id-less-line arm of a re-implemented helper — MINOR-1).
`ledger-unit` and `lint` are green on `--rebuild`; `ruff check`/`ruff format
--check`; `repomap … write` then `git diff --exit-code docs/MAP.md` clean;
`tasks.py check` silent, exit 0.

Five MINORs, none gating. No MAJOR.

## Contract items

Files (all present, all in `touches`):

| item | evidence |
|---|---|
| session fixture: a `user` line, three assistant lines sharing `msg_main_grow` for `claude-opus-4-1` out 2 / 2 / 7912, cache_write 29050 and cache_read 34255 each; one `claude-sonnet-4-5[1m]` line, out 40, one `tool_use`; a 429 tombstone `req_main_1`; a 500 line without `quotaLimits`; `version` / `cwd` / `gitBranch` / `slug` on every line | `tests/ledger/fixtures/projects/-fixture-project/11111111-2222-4333-8444-555555555555.jsonl:1–7` — exactly that, seven lines, trailing newline closed |
| the wf tree under the session dir | `…/11111111-…-555555555555/subagents/workflows/wf_fixture/journal.jsonl:1`, `…/agent-a5555555555555555.jsonl:1` |
| `torn.jsonl`: one good assistant line, then a truncated line | `tests/ledger/fixtures/projects/-fixture-project/torn.jsonl:1–2` (`…"id":"msg_torn_2` — unterminated) |

Interfaces:

| # | contract | met | evidence |
|---|---|---|---|
| 1 | `_read_main_session(session_file) -> tuple[dict, list[dict]]` | yes | `tools/ledger/factory.py:505`, `:632 return row, limit_events` |
| 2 | lines via `_read_lines` | yes | `:518 for line in _read_lines(session_file)` |
| 3 | a non-JSON line skipped and counted, stderr `factory.py: {file}: {k} unparseable line(s) skipped`, once per file | yes | `:519–526`; test at `tests/ledger/test_factory.py:1805` asserts `"1 unparseable line(s) skipped"` and `"torn.jsonl"` in stderr |
| 4 | usage grouped MAX per `message.id`, keyed `(file, message.id)` | yes, but re-implemented rather than delegated | `:536 by_gid` is function-local; `:575 max(...)`. The section says "by SP2's `_usage_groups`" — the code copies it instead (MINOR-1) |
| 5 | `by_model` = one entry per `message.model`, first-seen order, split by SP2's `_model_split` | yes | `:579–598`, `model_order` preserves first-seen; `:584 head, suffix = _model_split(model)` (SP2's function, `:159`) |
| 6 | a ninth model → the fence's cap refuses the row, named on stderr | partly | measured: `StreamRefused row 0: by_model: over cap 8` — the fence names it, but it aborts the whole merge rather than skipping the row, and no test covers it (MINOR-3) |
| 7 | `tokens` = the sum over models | yes | `:580–581` sums per group; per-model sums at `:597–598` give the same totals |
| 8 | `message_count` = groups | yes | `:622 "message_count": len(groups)`; mutant E1 (assistant-line count) dies `assert 4 == 2` |
| 9 | `tool_uses` per line | yes | `:557–559` counts per line, inside the per-event loop; mutant E2 (per group) dies `assert 0 == 1` |
| 10 | `started`/`ended` = min/max `timestamp`; `wall_s` | yes | `:601–605`; the fixture spans 10:00:00 → 10:02:00, `wall_s` 120.0 (`tools/ledger/schema.md:110`) |
| 11 | `harness_version` = the first line's `version` | yes (first line that *has* a `version`) | `:528–532`; benign widening — the section's fixture puts `version` on every line |
| 12 | `session_id` = `session_file.stem` | yes | `:515`; mutant E6 (`session_id = None`) fails five tests |
| 13 | `limit_events` = count of `_limit_event(line, "main")`, returned beside the row | yes | `:607–612`, `:624`, `:632`; `tests/ledger/test_factory.py:1772` asserts `origin == "main"`, `request_id == "req_main_1"` |
| 14 | `backfill -> tuple[int,int,int]`, workflow walk unchanged, then `sorted(projects.glob("*/*.jsonl"))` | yes | `tools/ledger/factory.py:383–404`; `:393` is the exact glob; `:385–390` untouched |
| 15 | merges `main-sessions.jsonl` and `limit-events.jsonl` | yes | `:402–403` through `_merge_jsonl` → `evidence.replace_stream` (the fence; no `open(…, "a")`, `lint` green). `replace_stream` merges by key (`pkgs/evidence/evidence.py:179–186`), so the agent-origin limit rows written at `:379` survive the main-side merge — checked, not assumed |
| 16 | the CLI prints `backfill: {w} workflow dirs, {m} main sessions, {l} limit events` | yes | `:1319–1323`; `tests/ledger/test_factory.py:1795` drives `factory.main([...])` and asserts the literal `backfill: 1 workflow dirs, 2 main sessions, 1 limit events` |
| 17 | `rollup --week` prints `main sessions: {n} sessions, in … out … cache_read … cache_write … thinking …`, windowed half-open on ISO-8601 `started` | yes | `:883–889` (`since <= … < until`), `:977–994` totals, `:1011–1017` the line; CLI routes through the same `rollup()` at `:1325–1337` |
| 18 | no `cwd`, `gitBranch`, `slug`, prompt or reply on the row | yes, by rule | the row and each `by_model` entry are literal dicts (`:583–592`, `:614–628`); no `**event`, no wire spread; `streams.validate` refuses undeclared/forbidden names |
| 19 | `schema.md`: the `main-sessions.jsonl` writer paragraph and the `backfill` line | yes | `tools/ledger/schema.md:103–110` (paragraph), `:99–110` (field table), `:128–134` (backfill), `:284–286` (the windowing bullet) |

## Red before green

Base implementation against branch tests
(`git checkout ced500a -- tools/ledger/factory.py`, then
`nix develop -c pytest tests/ledger -q -k main_session`):

```
FAILED tests/ledger/test_factory.py::test_main_session_row_tokens_and_by_model
FAILED tests/ledger/test_factory.py::test_main_session_limit_event_origin_and_request_id
FAILED tests/ledger/test_factory.py::test_main_session_row_validates_and_drops_identity
FAILED tests/ledger/test_factory.py::test_main_session_backfill_counts_and_cli
FAILED tests/ledger/test_factory.py::test_main_session_torn_line_skipped - At...
FAILED tests/ledger/test_factory.py::test_main_session_backfill_idempotent - ...
FAILED tests/ledger/test_factory.py::test_main_session_rollup_week_line - Ass...
7 failed, 52 deselected in 0.25s
```

All seven of the section's assertions are red at the base — the first six on
`AttributeError: module 'factory' has no attribute '_read_main_session'` (the
line the commit body pastes), the seventh on the missing rollup line. Restored:
`59 passed in 1.42s`. No test in this section can pass without the change.

## Mutants

Applied in the clone, one at a time, reverted with `git checkout HEAD --` after
each. `run = nix develop -c pytest tests/ledger -q -k main_session` unless noted.

| # | mutant (named by the section) | killed by | failing line |
|---|---|---|---|
| 1 | first-wins (`if …== 0: = value` for `max`) | test 1 | `{'out': 42} != {'out': 7952}` |
| 2 | sum (`+=` for `max`) | test 1 | `{'out': 7956} != {'out': 7952}`, `{'in': 7000} != {'in': 3000}` |
| 3 | `by_model` keyed on the first model only (`model = groups[0]["model"]`) | test 1 | `assert len(row["by_model"]) == 2` → `assert 1 == 2` |
| 4 | the bracket split at `]` (`_model_split`, `:167`) | tests 1, 3, 4, 6 | `4 failed, 3 passed` — `StreamRefused` at `pkgs/evidence/evidence.py:150` |
| 5 | the 429 test dropped (`:289–290` removed) | `test_non_429_error_yields_no_limit_event` (whole suite; **not** by SP6's fixture — MINOR-2) | `assert factory._limit_event(with_limits, "agent") is None` → a row |
| 6 | an identity field copied into the row (`"cwd": "leak"`) | tests 3, 4, 6 | `StreamRefused` at `evidence.py:150` |
| 7 | `by_model.message_count` renamed back to `messages` | tests 3, 4, 6 | `StreamRefused` at `evidence.py:150` |
| 8 | the main walk globs `**/*.jsonl` | tests 3, 4, 6 | `3 failed, 4 passed`; the agent and journal files become sessions |
| 9 | the unparseable skip removed | tests 3, 4, 5, 6 | `json/decoder.py:361: JSONDecodeError` |
| 10 | store `append` instead of the keyed replace | test 6 | `test_main_session_backfill_idempotent` at `test_factory.py:1821` |
| 11 | `<=` on the far side of the window | test 7 | the rollup text carries `…cache_write 1300 thinking 1400` — both sessions summed |
| 12 | the `main sessions:` line omitted | test 7 | `assert 'main sessions: 1 sessions, …' in text` |

Outside the named set:

| # | mutant | result |
|---|---|---|
| E1 | `message_count` = the assistant-line count | killed — `assert 4 == 2` |
| E2 | `tool_uses` counted per group, not per line | killed — `assert 0 == 1` |
| E6 | `session_id` not the file stem | killed — 5 failed, 2 passed |
| E8 | id-less assistant lines collapse into one group (`gid = "__none__"`) | **survives** — `59 passed in 1.06s` (MINOR-1) |

`mutants_total: 16`, `mutants_killed: 15`, `mutants_outside_named: 4`. Every
named mutant dies inside the section's own acceptance check (`ledger-unit`).

## Checks

| check | command | result |
|---|---|---|
| ledger-unit | `nix build .#checks.x86_64-linux.ledger-unit -L --no-link --rebuild` | **pass** — `ledger-unit> 59 passed in 1.14s`, exit 0 |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass** — exit 0 |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1, **one line only**: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. `diff` against the same hook run at base `ced500a` in a second clone (exit 0) shows that line is the only difference. The queue block is exempt by §Global Constraints and is the board commit's; the seat correctly did not commit it (MINOR-5) |
| ruff | `nix develop -c ruff check tools/ledger tests/ledger` | `All checks passed!`, exit 0 |
| ruff format | `nix develop -c ruff format --check tools/ledger tests/ledger` | `3 files already formatted`, exit 0 |
| repomap | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | clean, exit 0 (the commit already carries `tests/ledger — 22 files`) |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, 0 bytes, exit 0 |

## Touches and commit

Diff files, all inside the section's list:

```
docs/MAP.md                                                   (exempt by rule)
tests/ledger/fixtures/projects/-fixture-project/11111111-2222-4333-8444-555555555555.jsonl
tests/ledger/fixtures/projects/-fixture-project/11111111-.../subagents/workflows/wf_fixture/agent-a5555555555555555.jsonl
tests/ledger/fixtures/projects/-fixture-project/11111111-.../subagents/workflows/wf_fixture/journal.jsonl
tests/ledger/fixtures/projects/-fixture-project/torn.jsonl
tests/ledger/test_factory.py
tools/ledger/factory.py
tools/ledger/schema.md
```

`touches_extra` 0. The plan file is untouched; `docs/OPERATIONS.md` is untouched;
no board commit.

`git rev-list --count ced500a..HEAD` → `1`. `cmp` of `git log -1 --format=%s`
against the section's commit subject → **byte-identical**. Body states the why,
pastes the red
(`tests/ledger/test_factory.py:1747: AttributeError: module 'factory' has no
attribute '_read_main_session'`) and the green (`ledger-unit> 59 passed in
1.16s`, `lint … -> exit 0`), then a blank line and the two trailers:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sp67)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

## Findings

**MINOR-1 — the grouping helper is copied, not called, and the copy's id-less arm
is untested.** `tools/ledger/factory.py:534–577` re-implements
`_usage_groups` (`:121–154`) inline; the section's Interfaces say "usage groups
by SP2's `_usage_groups`". The re-implementation is semantically equal on the
tested paths (the copy exists because `_usage_groups` calls `json.loads`
unguarded, which the torn-line contract forbids, and because `by_model` needs
each group's model). Its untested arm is the id-less line: replacing

```python
        if gid is None:
            groups.append({"model": message.get("model"), "fields": fields})
            continue
```

at `:563–566` with `if gid is None: gid = "__none__"` — collapsing every id-less
assistant line into one maxima group, exactly what `_usage_groups`' docstring
forbids — leaves the whole suite green: `59 passed in 1.06s`. Two copies of one
rule can now drift apart with no check to notice. Not gating: main-session
assistant lines carry `message.id` (Assumption 7), so the arm is unreachable on
the shapes the section fixtures.

**MINOR-2 — test 2's "discriminating fixture" does not discriminate its own
mutant.** The section's row 2 names the fixture as "the two error lines" and the
mutant as "the 429 test dropped". The delivered 500 line,
`tests/ledger/fixtures/projects/-fixture-project/11111111-2222-4333-8444-555555555555.jsonl:7`,
carries no `quotaLimits`:

```
{"…","type":"assistant","requestId":"req_main_500","timestamp":"2026-09-03T10:02:00.000Z","apiErrorStatus":500,"error":"provider_error","isApiErrorMessage":true}
```

so `_limit_event` (`tools/ledger/factory.py:291–293`) returns `None` on the
`quotaLimits` guard whether or not the 429 guard is there. Deleting `:289–290`
leaves all seven SP6 tests green; the mutant dies only on SP2b's pre-existing
`tests/ledger/test_factory.py::test_non_429_error_yields_no_limit_event`:

```
>       assert factory._limit_event(with_limits, "agent") is None
E       AssertionError: assert {'kind': 'limit-event', …} is None
1 failed, 58 passed in 1.38s
```

Counted killed (it dies inside `ledger-unit`, the section's acceptance), but
SP6's own assertion "the 500 line yields none" is vacuous with respect to the
429 guard. A 500 line carrying `quotaLimits` would have made it load-bearing.

**MINOR-3 — the ninth-model arm is untested and coarser than the section reads.**
The Interfaces say "a ninth model → the fence's cap refuses the row, named on
stderr"; the Tests table names no row for it. Measured with a nine-model session
file (`by_model` cap is 8, `pkgs/evidence/streams.py:592–608`):

```
by_model entries: 9
validate: ['by_model: over cap 8']
backfill raised: StreamRefused row 0: by_model: over cap 8
```

`replace_stream` is all-or-nothing (`pkgs/evidence/evidence.py:144–150`), so one
pathological file aborts the whole `main-sessions.jsonl` merge and the CLI dies
with a traceback rather than skipping that row and continuing. The same shape
applies to an assistant line whose `message` has no `model`:

```
no-model backfill raised: StreamRefused row 0: by_model[0].model: null not allowed
```

This is the known gap the plan itself records (§Assumptions 15, `tel2/T1W`:
"`_merge_jsonl` lacks per-record refusal"), and SP6 was not asked to close it —
but Operator step 6 runs `backfill` over the live `~/.claude/projects` tree, so
worth a queue row rather than a surprise at the console.

**MINOR-4 — stale CLI help.** `tools/ledger/factory.py:1283` still reads
`sub.add_parser("backfill", help="backfill every past workflow dir")` though
`backfill` now walks both trees and prints three counts.

**MINOR-5 — pre-commit is red on the branch, on the derived queue block alone.**
`nix develop -c githooks/pre-commit` exits 1 with `tasks: docs/OPERATIONS.md
queue block was stale and has been regenerated — git add docs/OPERATIONS.md and
commit again`; the regenerated block only drops `SP6` from the queued list. The
same hook at base `ced500a` in a separate clone exits 0, and `diff` of the two
logs shows that line is the only delta. Recorded, not owed: the block is exempt
and belongs to the board commit.

## Verdict

**APPROVED.** No MAJOR. The counting rule the operator's spend accounting rests
on is MAX per `message.id` per file, it is implemented that way, and the fixture
proves it against both wrong readings — first-wins reports 42 where the truth is
7952, a naive sum reports 7956, and both mutants die on the number. "Numbers
only" is guaranteed by construction and by the fence, not by a fixture that
happens to omit the slug. `backfill` walks both trees with the exact glob the
section names and prints the three counts through `main()`; the 429 tombstone
becomes a `limit-event` row with `origin == "main"`; `rollup --week` prints the
main line and excludes a session that starts on the far boundary. Twelve named
mutants, twelve dead; one outside-named survivor, in an unreachable arm.
`ledger-unit` and `lint` green on `--rebuild`; `docs/MAP.md` current; `tasks.py
check` silent. Five MINORs, none gating; MINOR-2 and MINOR-3 are worth a line in
the plan's errata so SP4 does not inherit them silently.
