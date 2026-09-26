---
plan_defect: wrong-fact
plan_defect_secondary: missing-case
mutants_total: 21
mutants_killed: 14
mutants_outside_named: 7
---
# Opus gate — seat run ca1, task CA2 — REJECTED

## Summary

The implementation is the plan's pasted code, byte for byte in effect: `seat_stats`,
`render_seats_line`, the one line in `render_brief`, `"runs_dir"` in `build` and `main`,
`import statistics`. Every acceptance check is green from a fresh clone of `task/CA2`
(`evidence-unit` 447 passed, `lint` pass, `githooks/pre-commit` — see Checks), the diff is
exactly the section's two files, and the commit subject is byte-identical to the section's.

Two of the fourteen mutants the section names **survive**, and each leaves a stated clause
of the Interfaces contract with no test at all:

- the section's S1 mutant "sort by name → `gpt-6-astra` first" is factually false on S1's own
  fixture — the model with 2 runs (`deepseek/…`) also sorts first alphabetically, so
  `key=lambda r: r["model"]` produces the identical line. "sorted by `runs` descending" is
  untested.
- the section's S2 mutant "glob `*` → `log-model`" does not fire, because the `.log` fixture is
  written **unaged** while `NOW = 1_800_000_000` is 2027‑01‑15 — 129 days in the future — so the
  `.log` is excluded by the seven-day cutoff, not by the `*.result` glob. "a `.log` … is never
  opened" is untested.

Both are MAJORs by the gate's rule (a named mutant that survives). Both trace to the plan's
Tests table, which asserts a consequence its own fixture cannot produce (wrong-fact) and omits
the ageing that would have made the `.log` row discriminating (missing-case). The seat
implemented S1–S5 literally as written.

**On the driver's `checks_scope: dirty`.** The seat's checks ran against the **committed**
content. `~/factory/ws/ca1/CA2` is clean today and its blobs are the commit's:

```
$ git -C /home/dalhaka/factory/ws/ca1/CA2 diff -- tests/evidence/test_tasks.py
(no output)
$ git -C … diff-files --name-only
(no output)
$ git -C … hash-object tests/evidence/test_tasks.py   → 4ff040bfadb3e437a2e59c1be6f7c62d1ae50fbd
$ git -C … rev-parse HEAD:tests/evidence/test_tasks.py → 4ff040bfadb3e437a2e59c1be6f7c62d1ae50fbd
```

and no post-commit edit or restore is possible: the file's mtime is `2026-09-08 01:09:00.585`,
earlier than the commit (reflog `HEAD@{2026-09-08 01:10:46}`) and earlier than the driver's own
verify (`~/factory/runs/ca1/CA2.log`, `"ts": "2026-09-08T06:11:59Z"` = 01:11:59 CDT). The
`checks_scope: dirty` / `checks_scope_list: tests/evidence/test_tasks.py` lines in
`~/factory/runs/ca1/CA2.result` therefore name a difference that does not exist — a driver
bookkeeping artefact (MINOR-7), not a substitution of tests. Everything below was re-run from a
fresh clone that contains only committed content.

**Do the committed tests alone satisfy S1–S5?** S1, S3, S4 and S5 yes; **S2 no** — its `.log`
half is vacuous (MAJOR-2) — and S1's "runs descending" half is vacuous (MAJOR-1).

## Contract items

Section `### CA2 (code, XS)`, Interfaces, taken clause by clause. Line numbers are
`pkgs/evidence/tasks.py` at `4ca0fe6`.

| # | clause | met | evidence |
|---|---|---|---|
| 1 | `seat_stats(runs_dir, now=None, days=7)` new | yes | `pkgs/evidence/tasks.py:1620` `SEATS_DAYS = 7`, `:1623` `def seat_stats(runs_dir, now=None, days=SEATS_DAYS):` |
| 2 | reads every `<runs_dir>/*/*.result` | yes | `:1632` `for p in glob.glob(os.path.join(str(runs_dir), "*", "*.result")):` — but see MAJOR-2: no test discriminates the `*.result` half |
| 3 | mtime ≥ `now − days·86400`; `now` defaults to `time.time()` | yes | `:1629-1630` `now = time.time() if now is None else now` / `cutoff = now - days * 86400`; `:1634` `if os.path.getmtime(p) < cutoff:` — killed by M7 and ON5 |
| 4 | a file that cannot be read is skipped | code yes, **untested** | `:1636-1640` `try: … except OSError: continue`; ON3 (replace `OSError` with `ValueError`) SURVIVES — MINOR-1 |
| 5 | no `^FACTORY-RESULT status=` line ⇒ skipped | yes | `:1641-1644`; `tests/evidence/test_tasks.py:815-819` asserts `seat_stats(noresult, now=now) == []` |
| 6 | `model` = the **first** `^model:` line, `unknown` when absent | code yes, "first" untested | `:1642` `model = _field(text, r"^model:[ \t]*(.+)$") or "unknown"` (`_field` is `re.search`); M9 kills the `unknown` half; ON6 (take the last match) SURVIVES — MINOR-3 |
| 7 | `done` = the **last** `FACTORY-RESULT status=` word | yes | `:1645` `re.findall(…, re.MULTILINE)`, `:1647` `if statuses[-1] == "done":`; M4 killed |
| 8 | wall sample only when `wall_s:` is an integer | yes | `:1651` `r"^wall_s:[ \t]*(\d+)[ \t]*$"`; the no-`wall_s` path killed by M10 |
| 9 | `billed` += `input` + `output` when each is an `int` and not a `bool`; a missing key adds 0 | yes; "missing key" untested | `:1655-1662`; M1 and M11 killed; no assertion pins the missing-key case — MINOR-6 |
| 10 | rows `{"model","runs","done","wall","billed"}` sorted by runs desc, then model asc | code yes, **runs-desc untested** | `:1663` `key=lambda r: (-r["runs"], r["model"])`; M2 SURVIVES — MAJOR-1 |
| 11 | `render_seats_line` exact format, `run`/`runs`, `? min`, `median_low+30//60` | yes | `:1666-1681`; M3, M5, M6, M10 killed. The `+30` rounding itself is untested (ON2 survives) — MINOR-2 |
| 12 | `render_brief`: the line immediately after the `**Record …**` line, `none` without `runs_dir` | yes | `:1729-1734`; adjacency pinned at `tests/evidence/test_tasks.py:914-915` (`lines[i+1] == seats_line`); M13 killed |
| 13 | `build()` and `main()` put `"runs_dir"` in the graph | yes | `:915` `"runs_dir": runs_dir,` and `:1977` `"runs_dir": args.runs_dir,`; M12 killed |
| 14 | `render_board_block` untouched | yes | no hunk in the diff touches `render_board_block` (`:1807`); `tests/evidence/test_tasks.py:936-940` asserts `"Seats" not in render_board_block(...)`; M14 killed |
| 15 | imports added: `statistics` only | yes | diff hunk `@@ -31,6 +31,7 @@` adds `import statistics` and nothing else |

## Red before green

The section's Step 2 red, run in the clone with the base's implementation file against the
branch's tests:

```
$ git checkout b440969 -- pkgs/evidence/tasks.py
$ nix develop -c pytest tests/evidence/test_tasks.py -q -k seats --tb=line
E   AttributeError: module 'tasks' has no attribute 'render_seats_line'   tests/evidence/test_tasks.py:728
E   AttributeError: module 'tasks' has no attribute 'seat_stats'          tests/evidence/test_tasks.py:764
E   AttributeError: module 'tasks' has no attribute 'render_seats_line'   tests/evidence/test_tasks.py:773
E   AssertionError: assert '**Seats (7 d):** deepseek/…' in ['# Task brief (generated …', …]  tests/evidence/test_tasks.py:912
FAILED tests/evidence/test_tasks.py::test_seats_line_sums_per_model_ordering_and_last_status
FAILED tests/evidence/test_tasks.py::test_seats_ignores_aged_logs_and_dotfiles
FAILED tests/evidence/test_tasks.py::test_seats_absent_fields_and_unreadable
FAILED tests/evidence/test_tasks.py::test_seats_line_in_the_cli_brief
4 failed, 1 passed, 132 deselected in 0.10s
```

Restored, green: `nix develop -c pytest tests/evidence -q` → `446 passed, 1 skipped in 11.92s`.

- **S1, S2, S3, S4** — shown red on the base, green on the branch. Genuine.
- **S5** (`test_seats_never_touches_the_board_block`, `tests/evidence/test_tasks.py:936`) passes on
  the base — it is a regression guard whose red is its named mutant, which the section
  contemplates ("Where a behaviour already exists … the red is the named mutant"). M14 turns it
  red (below), so it is not vacuous.
- S2's *red* here is the whole function being absent; the row's **discriminating** power for the
  `.log` is separately vacuous — see MAJOR-2. A red from `AttributeError` proves the test loads,
  not that its fixture discriminates.

## Mutants

Applied in the fresh clone, one at a time, each reverted (`git status --porcelain` empty after
every batch; each script asserts the file is restored).

### The fourteen the section names — 12 killed, 2 survive

| id | row | mutant | result | line |
|---|---|---|---|---|
| M1 | S1 | `for k in ("input", "output")` → `("input",)` | KILLED | `AssertionError: assert '**Seats (7 d…' == '**Seats (7 d…'` |
| M2 | S1 | sort by name (`key=lambda r: (r["model"],)`) | **SURVIVED** | `1 passed, 136 deselected` |
| M3 | S1 | `statistics.median_low` → `statistics.median` | KILLED | AssertionError on the line |
| M4 | S1 | `statuses[-1]` → `statuses[0]` | KILLED | AssertionError on the line |
| M5 | S1 | `run` unpluralised | KILLED | AssertionError on the line |
| M6 | S1 | `median_low` → `statistics.mean` | KILLED | AssertionError on the line |
| M7 | S2 | drop the cutoff (`if os.path.getmtime(p) < cutoff:` → `if False:`) | KILLED | `AssertionError: assert 2 == 1` |
| M8 | S2 | glob `*` instead of `*.result` | **SURVIVED** | `1 passed, 136 deselected` |
| M9 | S3 | `str(_field(...))` instead of `… or "unknown"` | KILLED | `assert 'unknown: 1 run…' in '**Seats (7 d):** None: 1 run…'` |
| M10 | S3 | drop the `if r["wall"]` guard | KILLED | `statistics.StatisticsError: no median for empty data` |
| M11 | S3 | `isinstance(v, int)` without the `bool` exclusion | KILLED | `assert 'm: 1 run, 1 done, ? min, 0 billed' in '… m: 1 run, 1 done, ? min, 1 billed …'` |
| M12 | S4 | `main` drops `"runs_dir": args.runs_dir` | KILLED | the S1 line absent from the CLI brief |
| M13 | S4 | the Seats block moved after `**Running:**` | KILLED | `assert '**Running:** none' == '**Seats (7 d…'` |
| M14 | S5 | the Seats line added to `render_board_block` | KILLED | `assert 'Seats' not in '**Queued (d…d):** none\n'` |

### The seven outside the named set — 2 killed

| id | mutant | result |
|---|---|---|
| ON1 | sort `(r["runs"], r["model"])` (runs **ascending**) | KILLED — proves S1 pins *an* order, just not `-runs` |
| ON2 | drop the `+ 30` rounding | SURVIVED (600 and 2400 are exact multiples of 60) |
| ON3 | `except OSError:` → `except ValueError:` in `seat_stats` | SURVIVED |
| ON4 | `render_brief` passes `now=None` instead of `now=graph.get("now")` | SURVIVED |
| ON5 | `SEATS_DAYS = 7` → `14` | KILLED (`assert 2 == 1`) |
| ON6 | `model` = the **last** `^model:` line | SURVIVED |
| ON7 | `statuses[-1] == "done"` → `.startswith("done")` | SURVIVED |

`mutants_total: 21` · `mutants_killed: 14` · `mutants_outside_named: 7`.

## Checks

All from the fresh clone `…/scratchpad/gate/gate-ca1-CA2` at `4ca0fe6`.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **pass** — `evidence-unit> 447 passed in 12.65s`, exit 0 |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass** — exit 0 |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1, and **by design**: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. The rewrite drops `CA2` from the queue because this tree now carries CA2's commit — `board_graph` reads THIS tree only and `tasks.py` reports `CA2 landed "evidence: the brief's Seats line — …"`. A base-only clone at `b440969` runs the same hook green (`BASE-HOOK-EXIT:0`, `git status` empty), including with a `task/CA2` branch present. `githooks/pre-commit:62-64`: "a landed key leaves the queue, so staleness is by design". Not a finding. |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!`, exit 0 |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted`, exit 0 |
| MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | no change, exit 0 |
| tasks check | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

## Touches and commit

- Diff `b440969..4ca0fe6 --stat`: `pkgs/evidence/tasks.py | 73 +`, `tests/evidence/test_tasks.py | 301 +`
  — 2 files, 374 insertions, 0 deletions. Both are inside the section's
  `touches: pkgs/evidence/tasks.py, tests/evidence/test_tasks.py`. Nothing outside; no
  `Deviation:` line needed and none present. `docs/MAP.md` correctly untouched (no new file).
  `docs/OPERATIONS.md` untouched. The plan file untouched. No board commit.
- Exactly one commit: `git rev-list --count b440969..task/CA2` = 1 (the `.result` agrees:
  `FACTORY-COMMITS 1`).
- Subject byte-identical to the section's `commit subject` — `cmp` of `git log -1 --format=%s`
  against the plan's string: `SUBJECT-BYTE-IDENTICAL`.
- Trailers, after a blank line, each on its own line:
  `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run ca1)`
  and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- The body states the why and pastes the red
  (``Red first … `AttributeError: module 'tasks' has no attribute 'seat_stats'` ``) but pastes no
  green — MINOR-5.

## Findings

**MAJOR-1 — the section's S1 mutant "sort by name" survives; "sorted by `runs` descending" has no
test.**
`pkgs/evidence/tasks.py:1663` — `return sorted(rows.values(), key=lambda r: (-r["runs"], r["model"]))`.
Replacing it with `key=lambda r: (r["model"],)` leaves every seats test green:

```
M2 [S1] SURVIVED: 1 passed, 136 deselected in 0.03s
```

because on S1's fixture the two orders coincide — the 2-run model also sorts first by name:

```
correct order      : [('deepseek/deepseek-v4-pro-0813', 2), ('gpt-6-astra', 1), ('two-status-model', 1)]
name-only order    : [('deepseek/deepseek-v4-pro-0813', 2), ('gpt-6-astra', 1), ('two-status-model', 1)]
runs-ASC then name : [('gpt-6-astra', 1), ('two-status-model', 1), ('deepseek/deepseek-v4-pro-0813', 2)]
```

The section's mutant column claims the opposite ("sort by name → `gpt-6-astra` first"), which is
false for the fixture the same row specifies — a wrong-fact in the plan. S1's assertion at
`tests/evidence/test_tasks.py:729-733` therefore pins only *an* order (ON1, runs ascending, does
turn it red), never the `-runs` key. A fixture whose highest-run model sorts **last** by name
(e.g. `zeta-model` with 2 runs beside `alpha-model` with 1) closes it.

**MAJOR-2 — the section's S2 mutant "glob `*`" survives; "a `.log` … is never opened" has no
test.**
`tests/evidence/test_tasks.py:756-760` writes the log-shaped fixture with a bare `write_text` and
no `os.utime`, while `tests/evidence/test_tasks.py:259` sets `NOW = 1_800_000_000`:

```
NOW      = 1800000000 2027-01-15 08:00:00
realtime = 1788848385 2026-09-08 06:19:45
log mtime  = 1788848385 -> age at NOW, days: 129.06960877104214
log inside the 7-day window? False
```

so the `.log` is dropped by the cutoff at `pkgs/evidence/tasks.py:1634`, never by the
`*.result` glob at `:1632`. The named mutant is therefore inert:

```
M8 [S2] SURVIVED: 1 passed, 136 deselected in 0.04s
```

Proof that ageing is the only missing piece — the same fixture with the `.log` aged 1 day:

```
real code, .log aged 1 d:        ['inside-model']
glob-`*` mutant, .log aged 1 d:  ['inside-model', 'log-model']
glob-`*` mutant, .log NOT aged:  ['inside-model']      ← the branch's fixture
```

The same hole covers the Interfaces' `.pid` and "the store" clauses; the `.marker-K3.x` file at
`tests/evidence/test_tasks.py:763` adds nothing either, since Python's `glob` never matches a
leading dot. The section's S2 row named a `K2.log` "in a run dir" without saying to age it — a
missing case in the plan, given its own future-dated `NOW`. Pass `_write_aged`-style
`os.utime(p, (NOW - 86400, NOW - 86400))` to the `.log` and the row discriminates.

**MINOR-1 — the "cannot be read" clause is untested, and the test that claims it does not test
it.** `pkgs/evidence/tasks.py:1636-1640` (`try: … except OSError: continue`). ON3 (narrow the
guard to `ValueError`) SURVIVES: `5 passed, 132 deselected`. The test named
`test_seats_absent_fields_and_unreadable` (`tests/evidence/test_tasks.py:769`) contains no
unreadable fixture — a `chmod 000` result, or a `runs/<run>` that is a file, would close it.

**MINOR-2 — the `+ 30` half-minute rounding is untested.** `pkgs/evidence/tasks.py:1673`. Both
wall samples in the suite (600 and 2400) are exact multiples of 60, so ON2 (drop `+ 30`)
SURVIVES. A `wall_s: 570` sample would pin it.

**MINOR-3 — "the **first** `^model:` line" is untested.** `pkgs/evidence/tasks.py:1642`. No
fixture carries two `model:` lines; ON6 (take the last match) SURVIVES.

**MINOR-4 — the `now=graph.get("now")` seam is untested and inert.**
`pkgs/evidence/tasks.py:1731`. Neither `build()` (`:915`) nor `main()` (`:1977`) ever sets
`"now"` in the graph, and no test passes it, so ON4 (`now=None`) SURVIVES. The clause comes from
the section's own Interfaces text; noting it, not charging it.

**MINOR-5 — the commit body pastes the red but not the green.** `git log -1 --format=%B` ends
with the `AttributeError` line and the two trailers; no `447 passed` / check line. The gate asks
for both.

**MINOR-6 — "a missing key adds 0" is stated but never asserted.**
`pkgs/evidence/tasks.py:1658-1662`. The only single-key usage in the suite is
`'{"input": 1}'` at `tests/evidence/test_tasks.py:758` and `:764`, whose `billed` is never
asserted.

**MINOR-7 (process, the driver) — `checks_scope: dirty` names a difference that does not
exist.** `~/factory/runs/ca1/CA2.result` records `checks_scope: dirty`, `checks_scope_files: 1`,
`checks_scope_list: tests/evidence/test_tasks.py`, yet the workspace's blob for that path equals
`HEAD`'s (`4ff040bfadb3e437a2e59c1be6f7c62d1ae50fbd` both ways), `git diff` and `git diff-files`
are both empty, and the file's mtime (01:09:00) predates both the commit (01:10:46) and the
verify (`2026-09-08T06:11:59Z`), so no post-verify restore could have happened. The seat's
checks did cover the committed content; the driver's scope line is a false positive worth
chasing before it masks a real one.

## Verdict

**REJECTED.** Two of the section's own named mutants survive, and each leaves a stated clause of
the Interfaces contract — "sorted by `runs` descending" and "a `.log` … is never opened" — with no
discriminating test. The code itself is correct against every behaviour I could probe, every
acceptance check is green, the touches and the commit are clean; the defect is in the tests the
section specified, so the re-plan is small: age the `.log` fixture into the window, and give S1 a
model whose run count and name disagree on order. `plan_defect: wrong-fact` (the S1 and S2 mutant
columns state consequences their own fixtures cannot produce), secondary `missing-case` (S2's
fixture row omits the ageing its future-dated `NOW` makes necessary).
