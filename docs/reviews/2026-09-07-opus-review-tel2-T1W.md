---
plan_defect: implementer
plan_defect_secondary: vacuous
mutants_total: 11
mutants_killed: 9
mutants_outside_named: 3
reviewer: opus
majors: 3
minors: 7
---
# Opus gate — seat run tel2, task T1W — REJECTED

## Summary

The fence itself is real and I could not break it. Every writer named by the
section goes through `evidence.append` / `evidence.replace_stream`, the two
recorder tests are genuinely load-bearing, all five acceptance checks are green
on a fresh clone (`helm-vm` included, re-run with `--rebuild`), the diff stays
inside `touches`, and the commit subject is byte-identical. Red before green
reproduces exactly as the section describes: nine hits and `exit=1` from the
lint script against the base sources, `2 failed` in `tests/helm`, `10 failed` in
`tests/ledger`, and the `render.test.mjs` regex failure with the base
`dark-factory.js`. Seven of the eight named mutants die, several loudly — the
`PYTHONPATH` mutant turns `helm-vm` red with `ModuleNotFoundError: No module
named 'evidence'` inside the VM's `helm-collect.service`, which is the strongest
build-time proof in this task.

Three MAJORs stop it.

The first is the one the section explicitly set out to prevent. The
`--self-test` guard exists so the gate can never go vacuous, and three of its
four arms work — but the fourth, the `clean.py` arm, **cannot fail**. Its
pattern is built with `\|` between the three rules, and under `grep -E` that is
a *literal pipe*, not an alternation; the combined pattern matches nothing. I
appended all three escape hatches to `clean.py` and `--self-test` still exited
0. A gate whose vacuity guard is itself vacuous in one arm is exactly the
failure mode the section names.

The second is the section's first named mutant: dropping `pkgs/helm` from
`ROOTS` survives everything in the deliverable. I proved it is not a cosmetic
survival — with that root dropped I restored the base `collect.py`, complete
with the old `_append_status_row`, and both the project sweep and `--self-test`
exited 0. The section claims the mutant is "pinned by a fixture copy of the old
`_append_status_row` in `bad-append.py`"; the fixture pins the *pattern*, not
the *root list*, so nothing pins the roots at all. Per the gate's rule a
surviving named mutant is a MAJOR; the cause is plan-side (the row's kill
mechanism does not exist), which is why the secondary defect class is
`vacuous`.

The third is convention: the commit body pastes neither the red nor the green.
The Global Constraints require the failing check shown with its output, and the
section's second mutant row requires the body to paste "the run with the fixture
edited and restored". The body is prose only. The work *is* genuinely red-first
— I reproduced it independently — but the record the constraint asks for is not
in the commit.

Two plan-side matters I am not charging to the seat. Erratum 10 stands
unaddressed: `_merge_jsonl` is a bare `replace_stream` call, so one bad record
still refuses a whole ledger file, and there is no per-record refusal test. The
section as written prescribes exactly the code that is here, so this is the
plan's missing case, carried forward, not an implementer fault. Erratum 18 is
already folded — the section carries both the `/pkgs` grep and the
`sed -n '1169,1183p'` command, and both facts check out against the tree.

`docs/OPERATIONS.md` is 2 lines, entirely inside the
`<!-- tasks:begin -->…<!-- tasks:end -->` block, which the Global Constraints
exempt. `docs/MAP.md` is current. The T1b correction is honoured: `extract_lane`
writes `ts_epoch`, `schema.md`'s `lane-jobs` example follows, and reverting it
to `ts` is killed by two ledger tests.

## Contract items

| # | contract item (section, literal) | verdict | evidence |
|---|---|---|---|
| 1 | `collect.py`: `import evidence` at module top after the stdlib imports | met | `pkgs/helm/collect.py:27` (after `import sys` at :25) |
| 2 | `_append_status_row` and its `import fcntl` deleted | met | `grep -n 'fcntl\|_append_status_row' pkgs/helm/collect.py` → no output, rc=1 |
| 3 | `record_status` builds `{"kind","tiles","reason"}` and returns `evidence.append(_store(cfg), "helm-status", row, ts=…)` | met | `pkgs/helm/collect.py:753-776` |
| 4 | `_status_rows(cfg)` = `[r for r in evidence.read(_store(cfg), "helm-status") if r.get("kind") == "helm-status"]` | met | `pkgs/helm/collect.py:745-751` |
| 5 | `_store(cfg) = cfg.get("evidence_dir") or evidence.DEFAULT_STORE`; the three `/var/lib/evidence` literals gone; `checks.jsonl` reader uses `_store` | met | `pkgs/helm/collect.py:577-579`, `:582-585`; `store-writers.sh` exit 0 on the tree |
| 6 | refusal never fails the collector: `except (OSError, ValueError) … print("helm-collect: evidence: {e}", stderr); return None` | met | `pkgs/helm/collect.py:777-779`; test at `tests/helm/test_collect.py:1239-1249` |
| 7 | `nixosModules/helm.nix` + `flake.nix` `helmCollect` gain the `PYTHONPATH` export before `exec`; texts otherwise identical | met | `nixosModules/helm.nix:103`, `flake.nix:138`; both blocks read identically apart from `../` vs `./` |
| 8 | `helm-unit` copies `pkgs/evidence`; `ledger-unit` copies it beside `ledger` | met | `flake.nix:1126`, `flake.nix:1188-1189`; deleting both lines turns both checks red (extra mutant O3) |
| 9 | `factory.py`: two-candidate `sys.path` insertion (`parents[2]`, then `parents[1]`), `ImportError("tools/ledger/factory.py needs pkgs/evidence on sys.path")` | met (untested — MINOR-3) | `tools/ledger/factory.py:41-56` |
| 10 | `_write_jsonl` deleted; `_merge_jsonl(path, records)` (no `key`) = `_stream_of` + `replace_stream` | met | `tools/ledger/factory.py:106-109`; `git diff` removes `_write_jsonl` |
| 11 | `_stream_of`: parent must be `ledger` else `SystemExit(2)` with `ledger dir must be named ledger: <path>`; `store = path.parent.parent`; `stream = f"ledger/{path.stem}"` | met (message unpinned — MINOR-1) | `tools/ledger/factory.py:92-103`; test `tests/ledger/test_factory.py:430-434` |
| 12 | every reader's record gains `kind`: `factory-run-usage`, `factory-agent`, `factory-finding` (+`title_sha256` replacing `title`), `dsh-session` (no `slug`), `lane-job` | met | `tools/ledger/factory.py:223`, `:152`, `:178`, `:327`, `:372`; test at `:404` |
| 13 | **T1b correction:** `extract_lane` writes `ts_epoch`, not `ts`; `schema.md`'s `lane-jobs` example follows | met | `tools/ledger/factory.py:379` `"ts_epoch": data.get("ts")`; `tools/ledger/schema.md:118`; the windowing/bucket helpers follow at `:457`, `:607` |
| 14 | `DEFAULT_LEDGER = os.path.join(os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE, "ledger")`; `_read_jsonl` stays | met | `tools/ledger/factory.py:58-61`, `:88` |
| 15 | `schema.md`: `kind` in every example, `title_sha256`, no `slug`, the `replace_stream`/`streams.py` paragraph | met | `tools/ledger/schema.md:4-9, 38, 52, 68, 73, 86, 118, 126` |
| 16 | `dark-factory.js` two prompts drop `--store "…"`; `render.test.mjs` two regexes drop it | met | `tools/factory/dark-factory.js:785`, `:892`; `tests/factory/render.test.mjs:1226`, `:1234` |
| 17 | `store-writers.sh`: the six roots, `find` enumeration, the three exclusions, three `grep -nE` patterns, `store-writers: <file>:<line>: <pattern>`, exit 1 / 0 / 2 | met (exit 2 untested — MINOR-2) | `tests/lint/store-writers.sh:19-63`; red run below |
| 18 | `--self-test` exits 0 **only if** each bad fixture yields exactly one hit of its own pattern **and `clean.py` none** | **VIOLATED** | **MAJOR-1** — `tests/lint/store-writers.sh:92` |
| 19 | wired as two lines (never `&&`) in `flake.nix`'s `lint` and `githooks/pre-commit` beside the `js-lint.sh` pair | met | `flake.nix:1052-1053`, `githooks/pre-commit:39-40` |
| 20 | direct-open recorder tests in both suites (`{"append"}`; `{"replace_stream"}`, no `collect`/`factory` frame) | met | `tests/helm/test_collect.py:1194-1225`, `:1229`, `tests/ledger/test_factory.py:64-95`, `:388-401` |

## Red before green

All four reds were reproduced in a scratch copy of the branch by checking out
the **base** implementation files against the **branch's** tests, then
restoring.

**(1) the lint script, against the base sources** (`git checkout e0b80e2 --
pkgs/helm/collect.py tools/ledger/factory.py tools/factory/dark-factory.js`):

```
store-writers: pkgs/helm/collect.py:743: O_APPEND
store-writers: pkgs/helm/collect.py:747: open(…,"a…")
store-writers: pkgs/helm/collect.py:578: /var/lib/evidence
store-writers: pkgs/helm/collect.py:757: /var/lib/evidence
store-writers: pkgs/helm/collect.py:793: /var/lib/evidence
store-writers: tools/ledger/factory.py:25: /var/lib/evidence
store-writers: tools/ledger/factory.py:41: /var/lib/evidence
store-writers: tools/factory/dark-factory.js:785: /var/lib/evidence
store-writers: tools/factory/dark-factory.js:892: /var/lib/evidence
exit=1
```

Nine hits, exactly the count Step 2 predicts. Restored: `exit=0`,
`selftest=0`.

**(2) `tests/helm` against the base `collect.py`:**

```
FAILED tests/helm/test_collect.py::test_record_status_writes_only_through_evidence_append
FAILED tests/helm/test_collect.py::test_record_status_refusal_is_logged_not_raised
2 failed, 148 passed in 13.35s
```

**(3) `tests/ledger` against the base `factory.py`:**

```
FAILED tests/ledger/test_factory.py::test_extract_writes_only_through_replace_stream
FAILED tests/ledger/test_factory.py::test_records_carry_kind_and_title_sha256
FAILED tests/ledger/test_factory.py::test_ledger_dir_must_be_named_ledger - F...
FAILED tests/ledger/test_factory.py::test_dsh_session_usage_rollup - KeyError...
FAILED tests/ledger/test_factory.py::test_factory_extract_rollup - KeyError: ...
… 10 failed, 32 passed in 0.24s
```

**(4) `render.test.mjs` against the base `dark-factory.js`:**

```
AssertionError [ERR_ASSERTION]: The input did not match the regular expression
  /pkgs\/evidence\/evidence\.py record-check --name flake-check --rev \$\(git rev-parse HEAD\)/
```

Every test the section names has been shown to fail. No test in the diff is
vacuous **except** the `clean.py` arm of `--self-test` (MAJOR-1).

## Mutants

11 applied; 9 killed. Named: 8, of which 7 killed and 1 survived.

| # | mutant | named? | result | evidence |
|---|---|---|---|---|
| M1 | drop `pkgs/helm` from `ROOTS` (`store-writers.sh:19`) | named | **SURVIVED** | `tree_exit=0`, `selftest_exit=0`. Re-run with the base `collect.py` restored: `tree_exit_with_regression=0` — the old `_append_status_row` passes the gate |
| M2 | `self_check() { return 0` (skip the per-fixture counts) | named | killed | baseline with `bad-open.py`'s `"a"`→`"w"`: `store-writers: self-test: bad-open.py: expected 1 open(…"a…") hit, got 0`, `selftest=1`; mutated: `selftest_mutated=0` |
| M3 | `record_status` writes with `open(path, "a")` instead of `evidence.append` | named | killed | `FAILED tests/helm/test_collect.py::test_record_status_writes_only_through_evidence_append` (+ the refusal test) |
| M4 | drop the `try/except`, let the refusal propagate | named | killed | `E ValueError: x` … `FAILED …::test_record_status_refusal_is_logged_not_raised`, `1 failed, 149 passed` |
| M5 | `_read_findings` keeps `"title": title` | named | killed | `FAILED …::test_records_carry_kind_and_title_sha256 - streams.St...` (6 failed, 36 passed) |
| M6 | `_stream_of`: `store = path.parent` | named | killed | `15 failed, 27 passed`, incl. `test_records_carry_kind_and_title_sha256 - FileNot...` |
| M7 | leave one `--store "/var/lib/evidence"` at the recorder prompt site | named | killed twice | `AssertionError … did not match /pkgs\/evidence\/evidence\.py record runs --json/`; and `store-writers: tools/factory/dark-factory.js:892: /var/lib/evidence`, `lint_exit=1` |
| M8 | drop the `PYTHONPATH` line from `nixosModules/helm.nix` | named | killed | `helm-vm` red: `helm-collect[894]: ModuleNotFoundError: No module named 'evidence'` → `RequestedAssertionFailed: command 'systemctl --user -M alice@ start helm-collect.service' failed`, `EXIT=1` |
| O1 | append `O_APPEND`, `open("x","a")` and `/var/lib/evidence` to `clean.py` | outside | **SURVIVED** | `selftest_with_dirty_clean=0` — see MAJOR-1 |
| O2 | `_lane_job_record` writes `"ts"` instead of `"ts_epoch"` | outside | killed | `FAILED …::test_extract_lane_records_cost_usd`, `…::test_rollup_week_windows_activity_export`, `2 failed, 40 passed` |
| O3 | delete both `cp -r ${self}/pkgs/evidence pkgs/evidence` lines from `flake.nix` | outside | killed | `helm-unit`: `ERROR tests/helm/test_collect.py … Interrupted: 2 errors during collection`; `ledger-unit`: `ERROR tests-ledger/test_factory.py … Interrupted: 1 error` |

## Checks

All run in a fresh clone of `task/T1W` at `be8fc0a`. The four unit checks had to
be built once first (`--rebuild` refuses a derivation that was never built here:
`some outputs of '…-helm-unit-tests.drv' are not valid, so checking is not
possible`), then re-run with `--rebuild`; both runs are reported.

| check | command | result |
|---|---|---|
| helm-unit | `nix build .#checks.x86_64-linux.helm-unit -L --no-link --rebuild` | **green** — `150 passed in 13.36s`, `EXIT=0` (first build also `150 passed`) |
| ledger-unit | `… ledger-unit … --rebuild` | **green** — `42 passed in 0.64s`, `EXIT=0` |
| factory-unit | `… factory-unit … --rebuild` | **green** — `render.test.mjs: all assertions passed`, `plan.test.mjs: all assertions passed`, `EXIT=0` |
| helm-vm | `… helm-vm -L --no-link --rebuild` | **green** — VM ran, `(finished: cleanup, in 0.01 seconds)`, `EXIT=0` |
| lint | `… lint … --rebuild` | **green** — `All checks passed!`, `EXIT=0` |
| pre-commit | `nix develop -c githooks/pre-commit` | **red, not caused by T1W** — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`, `PRECOMMIT=1`. The same command at the **base** commit `e0b80e2` fails identically (`BASE_PRECOMMIT=1`, same message). See MINOR-6 |
| ruff check | `nix develop -c ruff check pkgs/helm tests/helm tools/ledger tests/ledger tests/lint/fixtures/store` | green — `All checks passed!` |
| ruff format | `… ruff format --check …` (same paths) | green — `12 files already formatted` |
| MAP.md | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | green — `MAPDIFF=0`, working tree clean |
| task graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | green — silent, `TASKSCHECK=0` |

`treefmt`, `statix`, `deadnix`, `shellcheck`, the js-lint pair and the new
store-writers pair all ran inside the hook before the board gate and passed
(`formatted 114 files (0 changed)`, `84 files already formatted`, `All checks
passed!`).

## Touches and commit

Seventeen files. Fifteen are the section's `touches`, verbatim. The two others
are the two standing exemptions in the Global Constraints:

- `docs/MAP.md` (1 line: `tests/lint — 6 files` → `11 files`) — the "regenerate
  whenever a file is added" rule; verified current.
- `docs/OPERATIONS.md` (2 lines) — the change is **entirely inside** the
  `<!-- tasks:begin -->…<!-- tasks:end -->` block (the queued keys gain
  `T1W T2 T3` and the plan filename), which the hook regenerates. Nothing
  outside the markers moved. By rule, not a deviation.

Nothing outside the list; nothing unexplained. The plan file is untouched; there
is no separate board commit.

Commit: exactly one, `be8fc0a` on base `e0b80e2`. Subject byte-identical to the
section (`cmp` against the section's string: `SUBJECT_IDENTICAL`, 195 bytes
each). Trailers correct and last, after a blank line:
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless,
factory run tel2)` then `Co-Authored-By: Claude Fable 5.1
<noreply@anthropic.com>`. The body states the why accurately and at the right
altitude — but pastes no red and no green (MAJOR-3).

## Findings

### MAJOR-1 — the `--self-test`'s `clean.py` arm cannot fail

`tests/lint/store-writers.sh:92`

```bash
c="$(count_hits "$FIXTURES/clean.py" "$P_APPEND\|$P_OPEN\|$P_LITERAL")"
```

`count_hits` runs `grep -cE`. In an ERE, `\|` is an **escaped pipe** — a literal
`|` character — not alternation. The pattern the shell hands to `grep` is
therefore the single string
`O_APPEND|open\([^)]*['"]a[bt+]*['"]|/var/lib/evidence`, which matches only text
containing those literal pipes. The arm counts 0 for any input.

Demonstrated directly — I appended all three escape hatches to `clean.py`:

```
"""A writer that goes through evidence.append, so no rule fires."""
def record(evidence, store, stream, row):
    return evidence.append(store, stream, row)
STORE = "/var/lib/evidence"
import os
F = os.O_APPEND
fh = open("x", "a")

selftest_with_dirty_clean=0
```

and the mechanism, on a file that contains both literals on separate lines:

```
$ grep -cE 'O_APPEND\|/var/lib/evidence' probe.txt
0
```

The section states the contract literally: `--self-test` "exits 0 **only if** …
`clean.py` none". The code cannot enforce the second half. This is the one arm
that would catch a rule broadened until it matches everything — the sibling of
the very mutant the section's second row is about — and it is dead. The comment
above it at `:75` ("otherwise the gate is vacuous") documents an assertion that
is itself vacuous. **Fix:** drop the backslashes (`"$P_APPEND|$P_OPEN|$P_LITERAL"`),
or count each of the three patterns separately as the three bad-fixture arms do,
and re-run the arm against a deliberately dirtied `clean.py` before trusting it.

### MAJOR-2 — the section's first named mutant survives: nothing pins the root list

`tests/lint/store-writers.sh:19`

```bash
ROOTS=(pkgs/evidence pkgs/helm tools/ledger tools/factory tools/session-start.sh tools/ritual.sh)
```

Mutant applied (`ROOTS` without `pkgs/helm`):

```
19:ROOTS=(pkgs/evidence tools/ledger tools/factory tools/session-start.sh tools/ritual.sh)
tree_exit=0
selftest_exit=0
```

and with the pre-T1W `collect.py` restored underneath it — the regression the
gate exists to catch:

```
tree_exit_with_regression=0
selftest=0
```

So the mutated gate passes while `pkgs/helm/collect.py` still contains
`os.open(…, os.O_APPEND, 0o640)`, `os.fdopen(fd, "a")` and three
`/var/lib/evidence` literals. The section asserts this mutant is "pinned by a
fixture copy of the old `_append_status_row` in `bad-append.py`" — it is not:
the fixture proves the *pattern* still matches, never that `pkgs/helm` is still
swept. The only thing that ever distinguished the two was the one-shot red run
before Step 3, which is not a repeatable assertion (and, per MAJOR-3, is not
even in the commit).

The kill mechanism the section names does not exist, so the cause is plan-side
(`plan_defect_secondary: vacuous`); by the gate's rule the surviving named
mutant is still a MAJOR. **Fix (small):** extend `--self-test` with a root
assertion — for each root, `find` it and require a non-empty file list, and
assert the root list equals the six declared paths; or run the project sweep
once over `tests/lint/fixtures/store/` as a synthetic root and require exactly
three hits.

### MAJOR-3 — the commit body pastes neither the red nor the green

`git log -1 --format=%B` (commit `be8fc0a`)

The body is 17 lines of prose (`Every evidence row now enters the store
through…`) followed by the two trailers. There is no command output in it.

Two stated contracts ask for it. The Global Constraints: "TDD: the failing check
first, **shown red with its output**, then green." And the section's own second
mutant row: "the commit body pastes the run with the fixture edited and
restored" — that run is the *only* assertion the section offers for the
`--self-test` behaviour, so with the paste missing there is no record of it at
all. (I reproduced it myself: `expected 1 open(…"a…") hit, got 0`, `selftest=1`.)

The underlying work is genuinely red-first — I verified all four reds
independently — so this is a record-keeping violation, not a fabrication.
**Fix:** amend the body with the nine-hit lint red, the two pytest red summaries,
the `--self-test` fixture-edit run, and the green counterparts.

### MINOR-1 — `_stream_of`'s refusal message is unpinned

`tools/ledger/factory.py:100`, test at `tests/ledger/test_factory.py:434`

The section states the message `ledger dir must be named ledger: <path>`. The
test asserts only `excinfo.value.code == 2`; deleting the `print` leaves it
green. Add `capsys` and assert the string.

### MINOR-2 — the exit-2 path has no test

`tests/lint/store-writers.sh:26-31`

"`grep`/`find` missing → exit 2" is a stated contract with no exercise. A
`PATH=` run in the self-test (or a `command -v` seam) would cover it.

### MINOR-3 — the `ImportError` contract has no test

`tools/ledger/factory.py:51-56`

`ImportError("tools/ledger/factory.py needs pkgs/evidence on sys.path")` is
stated by the section and never exercised. Both sandbox layouts are covered
implicitly by `ledger-unit`, but the failure message is not.

### MINOR-4 — a finding with neither `issue` nor `title` now crashes

`tools/ledger/factory.py:175,187`

```python
title = finding.get("issue") or finding.get("title")
… "title_sha256": hashlib.sha256(title.encode()).hexdigest(),
```

`title` is `None` when both keys are absent, and `None.encode()` raises
`AttributeError`; the pre-T1W code stored `None`. `dark-factory.js:211` makes
`issue` a required schema field, so no factory-written journal can trigger it —
but a hand-edited or older journal can, and the extractor is meant to survive
its inputs. Plan-verbatim code, so plan-side; worth one `or ""` and a row.

### MINOR-5 — two pre-existing ledger fixtures silently narrowed to satisfy T1's types

`tests/ledger/test_factory.py:298` (`repo="/home/dalhaka/example"` → `"example"`)
and `:530` (`"commit": "abc123"` → `"a" * 40`)

Both were forced by T1's `streams.py` (`repo` is `id`, and `ID_RE` excludes `/`;
`tasks[].commit` is `rev`, 40 hex). The section names neither change and the
commit body does not explain them. The behavioural consequence is real and
unrecorded: `factory.py extract --repo /home/dalhaka/x` now raises
`StreamRefused` and loses the whole run row. Nothing in-tree passes `--repo`
today, so this is a note, not a break — but it belongs in the body or in T2's
section.

### MINOR-6 — `githooks/pre-commit` is red at HEAD, and equally red at the base

`docs/OPERATIONS.md:15`

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
PRECOMMIT=1
```

In this clone the regenerated block drops `T1W` (the tree now contains T1W's
commit, so the derived queue no longer lists it). I ran the same hook on a
clone checked out at the base `e0b80e2`: it also exits 1, regenerating the block
to *exactly what the seat committed* (`… SD8 T1W T2 T3`). So the block was
correct when written and goes stale the instant its own commit lands — a
property of a self-referential derived block, not of this change. No action for
the seat; worth a line in the runbook so the next gate does not read it as a
regression.

### MINOR-7 — a dead assertion

`tests/ledger/test_factory.py:400`

```python
assert names == {"replace_stream"}
assert names <= {"append", "replace_stream", "_write_atomic"}
```

The second assertion is implied by the first and can never fail on its own.
Harmless, but it reads as coverage that is not there.

## Verdict

**REJECTED.** Three MAJORs: the `--self-test`'s `clean.py` arm cannot fail
(`store-writers.sh:92`, `\|` is a literal pipe under `grep -E`); the section's
first named mutant survives because nothing pins the root list
(`store-writers.sh:19`); and the commit body pastes neither the red nor the
green. MAJOR-1 and MAJOR-3 are the implementer's; MAJOR-2's cause is the plan's
fictional kill mechanism, hence `plan_defect: implementer`,
`plan_defect_secondary: vacuous`.

Everything else holds: 20 contract items met (one violated, three untested), all
four reds reproduced, 9 of 11 mutants killed including the `helm-vm` `PYTHONPATH`
proof, all five acceptance checks green on a fresh clone, `touches` clean, the
subject byte-identical, the T1b `ts_epoch` correction honoured. A fix round of
roughly a dozen lines — the `grep -E` alternation, a root assertion in
`--self-test`, and an amended commit body — closes all three.
