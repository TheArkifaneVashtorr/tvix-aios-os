---
plan_defect: none
mutants_total: 8
mutants_killed: 8
mutants_outside_named: 6
model: opus
---
# Opus gate — seat run sp2b, task SP2b — APPROVED

## Summary

The central claim holds, measured in a fresh clone of `task/SP2b`
(`618eadd`, base `ab836b7`). `factory.extract` over the
`workflow-strfinding` fixture now completes and writes **both** rows,
including the null-severity/null-file one, and `factory.backfill` walks a
synthesized `subagents/workflows/wf_*` tree carrying that fixture without
raising — both proven through `extract`/`backfill`, not through
`_read_findings`. The rewritten `test_string_finding_is_accepted` reads its
assertions off `factory-findings.jsonl` on disk
(`tests/ledger/test_factory.py:1584-1586`), so the regression class that was
invisible in SP2 is now visible: reverting the two field declarations turns
all three tests red with the exact refusal the previous gate reported.

The seat's disclosed third edit (`_name_fence`) is **necessary, correct and
in scope**: the section's assertion that only two field declarations needed
to change is a section wrong-fact, not scope creep — measured below
(mutant C: 11 tests red, `file: forbidden name`).

The section's `key_of` claim re-verified independently: a null `file` in the
`(run_id, file, title_sha256)` key round-trips through `replace_stream` and
does **not** collapse two distinct findings.

`ledger-unit`, `evidence-unit` and `lint` pass under `--rebuild`;
`ruff check` / `ruff format --check` clean; `repomap` regenerates to the
committed `docs/MAP.md`; `tasks.py check` silent. Eight mutants tried, eight
killed (two named, six outside). No MAJORs. Three MINORs, none gating; one
is addressed to the orchestrator, not the seat.

## Contract items

Numbered as the section numbers them. Line numbers are `618eadd`'s.

| # | item | verdict | evidence |
|---|---|---|---|
| 1 | `severity` → `("null", "id")`, `file` → `("null", ("path", ("",), 200))`; key at `:475` unchanged; a new `test_factory_finding_accepts_null_severity_and_file` asserting `validate(...) == []` | **met** | `pkgs/evidence/streams.py:482` `"severity": ("null", "id"),`; `:483` `"file": ("null", ("path", ("",), 200)),`; `:475` still `"key": ("run_id", "file", "title_sha256"),` — unchanged byte for byte against `2d40f41`. Test at `tests/evidence/test_streams_policy.py:505-514`. Killed by mutants A, D, E |
| 1a | "no key-handling code changes, **only the two field declarations**" | **not met — and rightly so** | a third site was required: `pkgs/evidence/streams.py:632-634` `if isinstance(cls, tuple) and cls[0] == "null": cls = cls[1]` in `_name_fence`. Without it the `("null", …)` wrapper hides the `path` exemption and the forbidden name `file` is fenced. Disclosed in FACTORY-NOTES and in the commit body. See MINOR-2 and mutant C |
| 2 | `test_string_finding_is_accepted` rewritten onto `factory.extract`, rows read back from `factory-findings.jsonl`, same assertions moved onto the written rows, stderr assertion unchanged | **met** | `tests/ledger/test_factory.py:1576-1598`: `_run, _agents, _findings = factory.extract(STRFINDING_FIXTURE, out)` then `rows = read_jsonl(out / "factory-findings.jsonl")`; `len(rows) == 2`; `string_row["severity"] is None`, `["file"] is None`, `["class"] is None`, `title_sha256 == sha256(b"a string finding")`; `obj_row["severity"] == "minor"`, `["file"] == "x.py"`; `assert "finding 2 is neither a string nor an object, skipped" in err` at `:1598`. `factory._read_findings` no longer appears in this test |
| 3 | `test_backfill_walks_workflow_with_string_finding`: synthesized `proj/subagents/workflows/wf_str/`, `backfill(...) == 1`, raises nothing, 2 rows on disk incl. the null one | **met** | `tests/ledger/test_factory.py:1601-1620`; `assert factory.backfill(tmp_path / "proj", ledger_dir) == 1` at `:1616`; `assert any(r["severity"] is None and r["file"] is None for r in rows)` at `:1619`. Killed by mutants A, D, E and by mutant H (glob) |
| 4a | MINOR-4 carried: five fixture files gain a trailing newline; no `\ No newline` marker in the diff | **met** | `tail -c 1` of all five paths → `\n`; `git show HEAD \| grep -c 'No newline at end of file'` → `0`. Files: `workflow-dedup/agent-a3333333333333333.jsonl`, `…334.jsonl`, `workflow-dedup/journal.jsonl`, `workflow-strfinding/journal.jsonl`, `workflow-strfinding/agent-a4444444444444444.jsonl` |
| 4b | MINOR-2 carried: `test_limit_event_requires_quotalimits_dict` — `quotaLimits` absent and `quotaLimits: "throttled"` both → `None` | **met** | `tests/ledger/test_factory.py:1688-1705`; both arms asserted; guard at `tools/ledger/factory.py:291-293`. Killed by mutant B |
| 4c | MINOR-1/3/5 not carried, one reason each | **met** | none of the three is touched by the diff; MINOR-1 stays open (MINOR-3 below) |
| 5 | commit body: the three reds against the carried tree, mutant B's red, the three green lines, the A–B mutant table, SP2's 15 re-run | **met** | body pastes all of it; the three red lines reproduce verbatim in my clone (below); `FACTORY-CHECKS`/`FACTORY-COMMITS` are the seat's final reply, not a repo file, per the constraints |
| 7 (interfaces) | every producer / enum arm / refusal path exercised | **met** | the widened classes still refuse their inner violations — probed directly: `severity=123` → `severity: not a id`; `severity="bad name!"` → `severity: not a id`; `file=123` → `file: not a string`; `file="../escape"` → `file: '..' segment`; `file="/abs/path"` → `file: outside root `; `file="x"*300` → `file: over cap 200`. The `("null", …)` wrapper admits `None` and nothing else |

### The orchestrator's three named verifications

**(a) `extract` writes both rows.** `tests/ledger/test_factory.py:1576`
passes on the branch and fails on the carried tree (below). The entry point is
`factory.extract`, and the assertions are read off the file the store wrote.

**(b) `backfill` walks the tree.** `tests/ledger/test_factory.py:1601`
passes; returns `1`; `factory-findings.jsonl` holds 2 rows.

**(c) the null `file` in the key round-trips.** Independent probe (not the
seat's test): a journal with **two** string findings, both producing
`file = None`, run through `factory.extract` twice into the same store —

```
PASS1 rows: 2
   key= ('wf', None, '1c0e20fa') severity= None
   key= ('wf', None, 'f69fc5d6') severity= None
PASS2 rows: 2 ts preserved: True
```

Two distinct findings with a null `file` keep two distinct keys (they differ
in `title_sha256`), and the second pass matches them by key through the
JSON `null` → `None` read-back, preserving `ts` and appending nothing. The
section's claim is correct; `keyed(r)` reads `None` as an ordinary hashable
element.

## Red before green

The section's stated red is "the branch's tests against the carried
(unfixed) tree". Performed as `git checkout FETCH_HEAD -- pkgs/evidence/streams.py`
(SP2's `2d40f41`, fetched read-only from `/home/dalhaka/factory/ws/sp2/SP2`),
branch tests untouched:

```
E           streams.StreamRefused: row 0: severity: null not allowed; row 0: file: null not allowed
pkgs/evidence/evidence.py:150: StreamRefused
FAILED tests/evidence/test_streams_policy.py::test_factory_finding_accepts_null_severity_and_file
FAILED tests/ledger/test_factory.py::test_string_finding_is_accepted - stream...
FAILED tests/ledger/test_factory.py::test_backfill_walks_workflow_with_string_finding
3 failed, 259 passed in 4.16s
```

Byte-for-byte the refusal the commit body pastes. Restored
(`git checkout HEAD -- pkgs/evidence/streams.py`), green:

```
262 passed in 4.22s
```

Mutant B's red for the fourth test is under `## Mutants`. Every one of the
four new tests has been shown to fail. None is vacuous.

## Mutants

Applied one at a time in the clone, the tree restored between each
(`git status --porcelain` empty after every revert).

`mutants_total: 8`, `mutants_killed: 8`, `mutants_outside_named: 6`.

Named by the section — 2 of 2 killed.

| mutant | result | failing line |
|---|---|---|
| **A** revert `:482`/`:483` to SP2's form | KILLED | `E streams.StreamRefused: row 0: severity: null not allowed; row 0: file: null not allowed` — all three tests (`…accepts_null_severity_and_file`, `test_string_finding_is_accepted`, `test_backfill_walks_workflow_with_string_finding`), `3 failed, 259 passed` |
| **B** `tools/ledger/factory.py:291-293` `if not isinstance(q, dict): return None` → `q = q or {}` | KILLED | `E AssertionError: assert {'kind': 'limit-event', 'v': 1, 'src': 'transcript', 'session_id': 'sess_fixture', ...} is None` at `tests/ledger/test_factory.py:1700`; `1 failed, 51 passed` |

Outside the named set — 6 tried, 6 killed.

| mutant | result | failing line |
|---|---|---|
| **C** drop the `_name_fence` null unwrap (`streams.py:632-633`), keep the two nullable declarations | KILLED, loudly | `E streams.StreamRefused: row 0: file: forbidden name; row 1: file: forbidden name`; `11 failed, 251 passed`, including the pre-existing `test_declared_field_walk_none_forbidden_but_path`, `test_one_valid_row_per_kind_and_shape[factory-finding-row10]`, `test_findings_idempotency_key_includes_file`, `test_factory_extract_rollup` |
| **D** revert `severity` alone to `"id"` | KILLED | the same `StreamRefused`; `3 failed, 259 passed` |
| **E** revert `file` alone to `("path", ("",), 200)` | KILLED | the same `StreamRefused`; `3 failed, 259 passed` |
| **F** the `str` arm disabled (`if isinstance(finding, str) and False:`) — SP2's mutant (C) re-run through the NEW entry point | KILLED | `tests/ledger/test_factory.py:1618` AssertionError; stderr now shows `finding 0 … skipped`; `2 failed, 260 passed` |
| **H** `backfill`'s glob `wf_*` → `zz_*` (`tools/ledger/factory.py:385`) | KILLED | `E AssertionError: assert 0 == 1` at `tests/ledger/test_factory.py:1616` — the backfill test is not vacuous about the walk itself |
| **I** the stderr skip line deleted from `_read_findings` — SP2's mutant re-run through the NEW entry point | KILLED | `E AssertionError: assert 'finding 2 is neither a string nor an object, skipped' in ''` at `tests/ledger/test_factory.py:1598` |

On the seat's "SP2's own 15 named mutants: 15/15 KILLED": I did not re-run
all fifteen. The two that pass through the surface this fix changed
(`_read_findings`'s `str` arm, and its stderr skip line — both re-pointed at
`extract` by item 2) I re-ran here as F and I; both still die. The other
thirteen exercise `_usage_groups`, `_model_split`, `_labels` and the
`limit-event` kind, none of which this commit touches (`git diff
FETCH_HEAD..HEAD -- tools/ledger/factory.py` is empty), and the full suite is
green.

## Checks

Fresh clone at `/tmp/…/scratchpad/gate/sp2b-SP2b/gate-sp2b-SP2b`,
`XDG_CACHE_HOME` under the session scratchpad, tree clean at `618eadd`.

| check | command | result |
|---|---|---|
| ledger-unit | `nix build .#checks.x86_64-linux.ledger-unit -L --no-link --rebuild` | pass — `ledger-unit> 52 passed in 0.91s` |
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | pass — `evidence-unit> 508 passed in 13.67s` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | pass — `lint> Found 0 warnings and 0 errors.` |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 on the first run, **only** `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`; the regeneration is the derived `SP2b` peel-off (`… SD12 SP2b SP3` → `… SD12 SP3 SP6 SP7`). The block is exempt from `touches` and the seat is right not to commit the board. `git add docs/OPERATIONS.md` then re-run → exit 0. The same hook on the base `ab836b7` (a `git worktree` at the base) exits 0, so the staleness is the branch's own derived queue, not a pre-existing main defect. Restored; tree clean |
| ruff | `nix develop -c ruff check pkgs/evidence tools/ledger tests/evidence tests/ledger` | `All checks passed!` (exit 0) |
| ruff format | `nix develop -c ruff format --check …` (same four dirs) | `85 files already formatted` (exit 0) |
| MAP.md | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0 — the committed `tests/evidence — 91 files` is what the generator produces |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

## Touches and commit

`git rev-list --count ab836b7..HEAD` → `1`. `git diff --name-only ab836b7..HEAD`:

```
docs/MAP.md
pkgs/evidence/streams.py
tests/evidence/test_streams_policy.py
tests/ledger/fixtures/workflow-dedup/agent-a3333333333333333.jsonl
tests/ledger/fixtures/workflow-dedup/agent-a3333333333333334.jsonl
tests/ledger/fixtures/workflow-dedup/journal.jsonl
tests/ledger/fixtures/workflow-strfinding/agent-a4444444444444444.jsonl
tests/ledger/fixtures/workflow-strfinding/journal.jsonl
tests/ledger/test_factory.py
tools/ledger/factory.py
tools/ledger/schema.md
```

The eight declared files, plus `docs/MAP.md` (exempt), plus
`tools/ledger/factory.py` and `tools/ledger/schema.md`. The last two are
**SP2's carried commit**, which the section's own Gate paragraph mandates
(`git cherry-pick -n FETCH_HEAD` of `2d40f41`): `git diff FETCH_HEAD..HEAD --
tools/ledger` is **empty** — the seat added not one byte to either file. See
MINOR-1.

Subject: byte-identical to the section's `commit subject` (331 bytes each,
compared programmatically against the plan line, em dash and `(test: …)` tail
included). Body states the why, pastes the three reds, mutant B's red, the
three green lines and the A–B table. Two trailers after a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sp2b)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`docs/OPERATIONS.md` untouched — no board commit.
`docs/superpowers/plans/2026-09-08-spend-telemetry.md` untouched.

### The previous review's findings, item by item

| prior finding | closed? | evidence |
|---|---|---|
| **MAJOR-1** — a string finding still cannot be written; `extract` refuses the row; the test called `_read_findings` | **CLOSED, both halves** | the kind half at `streams.py:482-483` (+ the `_name_fence` unwrap the section missed); the test half at `test_factory.py:1584-1586` (`factory.extract`) and the new `backfill` test at `:1601`. Red-before-green shown above with the exact `StreamRefused` the review reported |
| **MINOR-1** — `_model_split` annotations | not carried, by the section's own item 4 | unchanged; still open (MINOR-3 below) |
| **MINOR-2** — `quotaLimits`-object arm untested | **CLOSED** | `test_limit_event_requires_quotalimits_dict` at `test_factory.py:1688`; kills mutant B, which SURVIVED in SP2's round |
| **MINOR-3** — dedup fixture repeats the bracketed id | not carried, reason stated | unchanged |
| **MINOR-4** — three of five fixtures end without a newline | **CLOSED** | all five end `\n`; zero `No newline` markers in the commit |
| **MINOR-5** — same-wave collision with SP8 on `test_streams_policy.py` / `streams.py` | not carried (integration note) | still live, and this commit adds one more hunk to `streams.py` (`_name_fence`) — the merge instruction stands; re-run `evidence-unit` on the merge result |

## Findings

**MINOR-1 — the commit carries two files outside the section's `touches`,
with no `Deviation:` line; the omission is the section's, not the seat's.**

`tools/ledger/factory.py` and `tools/ledger/schema.md` are in the diff
(`ab836b7..HEAD`) because the section's Gate paragraph orders
`git cherry-pick -n FETCH_HEAD` of SP2's `2d40f41`, and its `touches` list
names only the fix-round delta. The seat changed neither file:

```
$ git diff FETCH_HEAD..HEAD -- tools/ledger
(empty)
```

Per Assumption 16, `factory-integrate` "refuses … undisclosed files outside
`touches`". Either the integrator's `touches` for SP2b must be read as
SP2's ∪ SP2b's, or the commit needed two `Deviation:` lines. Orchestrator's
call at integrate time; nothing for the seat to fix.

**MINOR-2 — the section's item 1 states a false fact: three sites needed to
change, not two. The seat found the third, fixed it correctly and disclosed
it.**

Item 1 says "so no key-handling code changes, only the two field
declarations". Wrapping `file` in `("null", …)` moves the forbidden-name
fence's `path` exemption out of reach, because
`pkgs/evidence/streams.py:635` tests `cls[0] == "path"` on the outer tuple.
Measured (mutant C — the two declarations kept, the unwrap removed):

```
E   streams.StreamRefused: row 0: file: forbidden name; row 1: file: forbidden name
11 failed, 251 passed
FAILED tests/evidence/test_streams_policy.py::test_declared_field_walk_none_forbidden_but_path
FAILED tests/evidence/test_streams_policy.py::test_one_valid_row_per_kind_and_shape[factory-finding-row10]
FAILED tests/ledger/test_factory.py::test_findings_idempotency_key_includes_file
…
```

The fix (`streams.py:632-634`) is two lines, unwraps `("null", X)` once and
only then applies the `path` exemption; a null-wrapped **non**-path forbidden
name is still fenced (`cls` becomes a bare string and
`_forbidden_name(name)` returns). It is necessary, correct, minimal, inside
the declared file, covered by pre-existing tests that fail loudly without it,
and named in both FACTORY-NOTES and the commit body. **Not scope creep.**
Recorded against the section (a `wrong-fact` sentence in an otherwise sound
item), not against the seat; it does not gate.

**MINOR-3 — the previous round's MINOR-1 stays open.**
`tools/ledger/factory.py:159` `def _model_split(model_id):` still carries no
annotations and can return `None` outside its stated signature. The section
explicitly deferred it ("a cosmetic annotation gap with no behavioural
surface and no surviving mutant"); recording it so it is not lost.

## Verdict

**APPROVED.** No MAJORs. The rejecting review's single MAJOR is closed in
both halves — the kind admits the null row *and* the test now goes through
`extract` and `backfill`, so the next regression of this class is visible.
Two carried MINORs closed; three MINORs recorded, none gating, one of them
addressed to the orchestrator (`touches` for a carried commit) and one to the
plan's defect ledger (item 1's "only the two field declarations" is wrong —
`_name_fence` was the third site, and the seat was right).
