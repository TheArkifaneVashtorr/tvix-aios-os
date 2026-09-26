---
plan_defect: none
mutants_total: 15
mutants_killed: 10
mutants_outside_named: 4
reviewer: opus
majors: 0
minors: 8
---
# Opus gate — seat run sh1, task SH1 — APPROVED

## Summary

The branch `task/SH1` (one commit, `5c27b6e`, base `1dbc2ec`) adds
`evidence report harness` to `pkgs/evidence/report.py`, eleven tests in a new
`tests/evidence/test_harness_report.py`, and a "The harness report" section to
`docs/runbooks/evidence.md`. Every numbered interface item of the SH1 section
is met literally, including the ones no test exercises — I proved those by
probe against the branch's own code. The eleven tests are red at the base
implementation (both red lines the commit body pastes reproduce verbatim) and
green on the branch. `evidence-unit` (411 passed), `lint`, `ruff check`,
`ruff format --check`, `repomap write` + `git diff --exit-code docs/MAP.md`
and `tasks.py --root . check` are all green/silent. The diff is exactly the
section's `touches` plus `docs/MAP.md` by the standing rule; the subject is
byte-identical to the section's; both trailers are present; the plan file and
the board are untouched.

Ten of the section's eleven named mutants die on the test the section names.
One survives — **row 11's** "drop the forwarding" — and it survives because
the section's own row-11 assertion is only "prints the header", which is true
of any store. That is a gap the plan section carries, not a contract the seat
ignored, so it is recorded as a MINOR and as a plan-defect note rather than a
MAJOR. Under that mutant the subprocess silently falls through to
`DEFAULT_STORE = /var/lib/evidence` and still exits 0, so the row as written
is both non-discriminating and the one place a future regression could reach
the live store from a unit test — worth closing in SH6 or a `SH1r`.

No MAJORs. Approved.

## Contract items

Taken from the section's **Interfaces** list, in order.

| # | contract item | verdict | evidence |
|---|---|---|---|
| 1 | CLI `evidence [--store S] report harness [--before] [--since] [--min-n]`, subparser `harness` beside `plans`, forwarded by `evidence.py` | met | `pkgs/evidence/report.py:426-429` adds the subparser; `pkgs/evidence/evidence.py:533` (untouched) forwards. Probe P8: `python3 evidence.py --store <tmp> report harness` → rc 0, header + `population: 1 task rows, 1 with a gate verdict`. |
| 2 | reads the store only, through `evidence.join_tasks_gates(store)` | met | `pkgs/evidence/report.py:325`; `--repo` is not on the `harness` subparser (`report.py:426-429`), and nothing in `harness_report` opens a repo path. |
| 3 | exit 2 + `report: --before <v>: invalid date (YYYY-MM-DD)` (or `--since`) | met | `report.py:314-322` raises `ReportUnreadable`; `main` prints `report: {exc}`. `--before`: test `test_cli_malformed_date_and_empty_store` (tests/evidence/test_harness_report.py:284-288). `--since` probe P1 → rc 2, stderr `report: --since 2026-99-01: invalid date (YYYY-MM-DD)`. |
| 4 | exit 2 + `report: cannot read store <S>: <err>` when the store dir is unreadable | met, untested | `report.py:324-327`. Probe P3 (a `derived/` chmod 000): rc 2, stderr `report: cannot read store /tmp/.../bad: [Errno 13] Permission denied: '/tmp/.../bad/derived'`. No test covers it → MINOR-5. |
| 5 | `--min-n` below 1 → argparse's exit 2 | met, untested | `report.py:408-412` (`_positive_int`). Probe P2: `SystemExit 2`, stderr `report harness: error: argument --min-n: must be at least 1`. No test → MINOR-3/5. |
| 6 | otherwise exit 0 after printing, an empty store included | met | test at tests/evidence/test_harness_report.py:290-296 (rc 0, the four empty-store lines). |
| 7 | window `since <= result_mtime[:10] < before`, `since` inclusive, `before` exclusive, absent bound open | met | `report.py:282-300`; test `test_window_bounds_before_and_since` (lines 112-132) pins all three forms. |
| 8 | rows with no `result_mtime` are out of every bounded window and in the open one | met, untested | `report.py:287-290`. Probe P4: open → `population: 2`, `--before 2026-09-08` → `population: 1`, `--since 2026-09-01` → `population: 1`. No test → MINOR-5. |
| 9 | `harness_report(store, before=None, since=None, min_n=5) -> list[str]` | met | `pkgs/evidence/report.py:312`. |
| 10 | line 1 `HARNESS_HEADER` verbatim | met | `report.py:32-36`; the same literal is re-typed in the test at tests/evidence/test_harness_report.py:18-22 and asserted through the CLI at line 310. |
| 11 | line 2 `window: since <since\|open> before <before\|open>` | met | `report.py:332`. Not asserted by any test → MINOR-5 (the string is exercised only in the runbook). |
| 12 | line 3 `population: N task rows, G with a gate verdict` | met | `report.py:333-335`; tests at lines 126, 129, 132, 213. |
| 13 | groups `all`, then every `<task_kind>/<size>` pair present among the window's rows, sorted | met (order untested) | `report.py:337-339`; `test_groups_are_all_then_present_pairs_only` (lines 257-270) pins "present pairs only". Line order is not asserted anywhere → MINOR-2. |
| 14 | `<group>: insufficient (n=<gated>)` when gated rows < `min_n` | met | `report.py:350-352`. The gated-vs-first-round distinction is untested → MINOR-4. Text equals `evidence.n_gate`'s (`pkgs/evidence/evidence.py:244-248`) but is re-formatted inline → MINOR-6. |
| 15 | `<group>: first-gate approved a/n (p%); fix-round approved b/m; re-plan approved c/l`, `p=0` when n=0 | met | `report.py:353-366`; tests at lines 149-152, 175-178, 214-217. `p=0` probe P6: `all: first-gate approved 0/0 (0%); fix-round approved 5/5; re-plan approved 0/0`. `p=0` untested → MINOR-5. |
| 16 | `<group>: median output tokens … median wall_s …`, `-` for an empty verdict, a `None` wall_s skipped, `round()`ed | met | `report.py:302-306, 367-386`; `test_median_output_tokens_even_count` (lines 181-198). `-` probe P5 (`… approved 100 / rejected -`) and the null-`wall_s` probe P7 (`median wall_s approved 600 …`, the `None` row skipped, not crashing) are untested → MINOR-5. |
| 17 | `error_class:` over every windowed row, count desc then class asc; empty window → `error_class: none 0` | met | `report.py:388-393`; tests at line 236 and line 295. |
| 18 | `plan_defect:` over rejected gates only, `None` → `unclassified`, same sort; none → `plan_defect: unclassified 0` | met | `report.py:395-401`; tests at line 254 and line 296. |
| 19 | lines 7 and 8 (`tags:` / `rung/class:`) verbatim | met | `report.py:38-50, 403-404`; `test_tags_and_rung_lines_verbatim` (lines 273-278). |
| 20 | `plans_report` and every existing `report plans` line unchanged | met | the diff touches `main` only to branch on `args.command`; `tests/evidence/test_report.py` is not in the diff and `evidence-unit` is 411 passed. |

Files/steps: `tests/evidence/test_harness_report.py` created; `pkgs/evidence/report.py` modified; `docs/runbooks/evidence.md` gets `## The harness report` at line 152, immediately after `## The planning report` (line 123), with the command, the eight line kinds and both `unmeasured` closes — the section's Step 5 exactly.

## Red before green

The section's stated red (Step 2) is `nix develop -c pytest tests/evidence/test_harness_report.py -q` against the pre-change `report.py`. I checked the base's implementation file out under the branch's tests:

```
git checkout 1dbc2ec -- pkgs/evidence/report.py
nix develop -c pytest tests/evidence/test_harness_report.py -q
…
E       AttributeError: module 'report' has no attribute 'harness_report'
tests/evidence/test_harness_report.py:125: AttributeError
…
E        +  where 2 = CompletedProcess(…"report: error: argument command: invalid choice: 'harness' (choose from 'plans')\n").returncode
11 failed in 0.49s
```

All eleven fail; both lines the commit body pastes reproduce verbatim. Restored (`git checkout HEAD -- pkgs/evidence/report.py`):

```
nix develop -c pytest tests/evidence/test_harness_report.py -q
11 passed in 0.46s
```

No test in the file is incapable of failing.

## Mutants

Applied in the clone, one at a time, reverted with `git checkout HEAD -- <file>` after each.

**Named by the section (rows 1–11; row 12 names no mutant): 11 applied, 10 killed.**

| row | mutant | result | failing line |
|---|---|---|---|
| 1 | `not (d < before)` → `not (d <= before)` (report.py:295) | killed | `E AssertionError: assert 'population: 2 task rows, 0 with a gate verdict' in [… 'population: 3 task rows, …']` — test_harness_report.py:126 |
| 2 | `a = sum(… for r in first …)` → `… for r in gr …` (report.py:357) | killed | `E AssertionError: assert 'all: first-gate approved 3/5 (60%); …' in [… 'code/S: first-gate approved 4/5 (80%); …']` — :149 (the section's predicted `4/5`) |
| 3 | `if len(gr) < min_n:` → `<= min_n` (report.py:350) | killed | `E AssertionError: assert 'all: first-gate approved 5/5 (100%); …' in [… 'all: insufficient (n=5)' …]` — :175 |
| 4 | `_median_or_dash` → upper median `sorted(s)[len(s)//2]` (report.py:302-306) | killed | `E AssertionError: assert 'all: median output tokens approved 25 / rejected 7; …'` — :195 |
| 5 | gateless rows kept as a synthetic `rejected`/`first` gate (report.py:329) | killed | `E AssertionError: assert 'population: 6 task rows, 5 with a gate verdict' in [… 'code/S: first-gate approved 3/6 (50%); …']` — :213 (the section's predicted `3/6`) |
| 6 | `key=lambda kv: (-kv[1], kv[0])` → `key=lambda kv: kv[0]` (report.py:389) | killed | `E AssertionError: assert 'error_class: none 2, no-result-line 1, template-echo 1' in [… 'error_class: no-result-line 1, none 2, template-echo 1' …]` — :236 |
| 7 | drop `if r["gate"].get("verdict") == "rejected"` (report.py:398) | killed | `E AssertionError: assert 'plan_defect: missing-case 2, unclassified 1, vacuous 1' in […]` — :254 |
| 8 | groups → the full `kind × size` enum product (report.py:337-339) | killed | `tests/evidence/test_harness_report.py:270: AssertionError` (the `docs/XS` line appears) |
| 9 | delete `lines.append(RUNG_LINE)` (report.py:404) | killed | `E assert "rung/class: unmeasured until the seat-driver plan's rung (SD1, SD3) and class (SD2) fields are declared" in […]` — :278 |
| 10 | raise `ReportUnreadable` on an empty store (report.py:328) | killed | `assert rc == 0` / `E assert 2 == 0` — :291 |
| 11 | drop the `--store` forwarding in `evidence.py:533` | **SURVIVED** | `1 passed, 10 deselected in 0.10s` |

**Outside the named set: 4 applied, 0 killed.**

| # | mutant | result |
|---|---|---|
| o5 | `d = mt[:10]` → `d = mt` (report.py:291) | survives — but **equivalent** for well-formed ISO `ts` values (`"2026-09-08T00:00:00Z" < "2026-09-08"` is False, `"2026-09-07T00:00:00Z" < "2026-09-07"` is False), so no finding |
| o6 | group order reversed, `all` printed last (report.py:337-339) | survives — no test asserts line order (MINOR-2) |
| o8 | `insufficient (n=…)` counts first-round rows instead of gated rows (report.py:351) | survives — the distinction is untested (MINOR-4) |
| o9 | `min_n` ignored, `5` hardcoded (report.py:350) | survives — no test passes a non-default `--min-n` (MINOR-3) |

`mutants_total: 15`, `mutants_killed: 10`, `mutants_outside_named: 4`.

## Checks

All run in the fresh clone `…/scratchpad/gate-sh1-SH1/gate-sh1-SH1`, with
`XDG_CACHE_HOME` under the scratchpad.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | green — `evidence-unit> 411 passed in 10.46s` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | green — `EXIT=0` (the `no-dupe-keys` / `no-debugger` lines in the log are `tests/lint/fixtures/js/*`, the arm-A fixtures, by construction) |
| pre-commit | `nix develop -c githooks/pre-commit` | `EXIT=1`, sole reason `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` (the derived queue dropped `SH1` once the store recorded this run). After `git add docs/OPERATIONS.md`: `EXIT=0`. Environmental, not the seat's (MINOR-8). |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` (rc 0) |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` (rc 0) |
| MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc 0 / rc 0 — the committed MAP is current |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | rc 0, silent |

Store rule: every assertion runs against fixture stores under `tmp_path` /
`tempfile.mkdtemp()`. The one incidental read of `/var/lib/evidence` in this
gate happened under mutant 11 (below) and is reported as the finding; nothing
was written there and no further read was made.

## Touches and commit

Diff `1dbc2ec..5c27b6e --stat`:

```
 docs/MAP.md                           |   2 +-
 docs/runbooks/evidence.md             |  37 ++++
 pkgs/evidence/report.py               | 172 ++++++++++++++++++-
 tests/evidence/test_harness_report.py | 310 ++++++++++++++++++++++++++++++++++
 4 files changed, 517 insertions(+), 4 deletions(-)
```

The section's `touches` is `pkgs/evidence/report.py, tests/evidence/test_harness_report.py, docs/runbooks/evidence.md`; `docs/MAP.md` is the standing exemption (a one-line file count, `tests/evidence — 82 files` → `83 files`). **No file outside the list.** No `Deviation:` line is needed and none is present. The plan file, `docs/OPERATIONS.md` and the board are untouched.

Commit convention:

- exactly one commit: `git rev-list --count 1dbc2ec..HEAD` → `1`.
- subject byte-identical: `git log --format=%s -1` `cmp`'d against the section's string → `SUBJECT-IDENTICAL`.
- body states the why (what the report reads, joins, windows and prints, and what the two `unmeasured` lines stand in for) and pastes the red (`AttributeError: module 'report' has no attribute 'harness_report'` and `report: error: argument command: invalid choice: 'harness' (choose from 'plans')`) — both reproduced above.
- trailers after a blank line, `cat -A` verified: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sh1)$` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>$`.

## Findings

No MAJORs.

**MINOR-1 (plan-carried; row 11's assertion cannot kill row 11's mutant) — `tests/evidence/test_harness_report.py:299-310`.**
The section's row 11 assertion is "`python3 evidence.py --store <S> report harness` prints the header", and the test implements exactly that:

```
309	    assert proc.returncode == 0
310	    assert HARNESS_HEADER in proc.stdout
```

The header is printed for any store, so the row's own named mutant survives. With the forwarding dropped at `pkgs/evidence/evidence.py:533`
(`forwarded = (["--store", store] if store else []) + rest[1:]` → `forwarded = rest[1:]`):

```
MUTANT m11 applied (store forwarding dropped)
1 passed, 10 deselected in 0.10s
```

and the same subprocess then reads `evidence.DEFAULT_STORE = /var/lib/evidence`:

```
P8 evidence.py forwarding, what the header test would see:
  rc 0
   # evidence report harness — proxies for docs/superpowers/specs/2026-09-07-seat-h
   population: 251 task rows, 177 with a gate verdict
```

The seat implemented the section literally, so this is a plan defect of class
`vacuous` at the row level rather than an implementer fault, and it is not a
MAJOR under the gate's plan-gap rule. Two things follow for the plan side: the
row wants an assertion on a store-dependent line (`population: 1 task rows,
1 with a gate verdict`, or the row's own key), and the subprocess wants
`env["EVIDENCE_STORE"] = str(store)` so a forwarding regression can never reach
the operator's live store from a unit test (Assumption 4's belt).

**MINOR-2 — line order is stated but not asserted: `pkgs/evidence/report.py:331-404`, `tests/evidence/test_harness_report.py` (whole file).**
The Interfaces block says "the lines in this order" and "Per group, in this
order: `all`, then every `<task_kind>/<size>` pair present, sorted". Every
assertion in the test file is membership (`… in lines`, `… in out`), never
position. Outside mutant o6 (groups sorted `reverse=True` with `all` appended
last) leaves all eleven green: `11 passed in 0.27s`.

**MINOR-3 — `--min-n` is an interface with no non-default test: `pkgs/evidence/report.py:429`, `report.py:350`.**
Outside mutant o9 (`if len(gr) < 5:`, the parameter ignored) leaves all eleven
green: `11 passed in 0.27s`. Behaviour is correct as written; nothing pins it.

**MINOR-4 — `insufficient (n=<gated>)` semantics untested: `pkgs/evidence/report.py:350-352`.**
The contract says the printed `n` is the count of gated rows. Outside mutant o8
(printing the first-round count instead) leaves all eleven green: `11 passed in
0.27s`, because every fixture's gated rows are all `round_kind="first"`. A
single fixture with one `fix` gate under `min_n` would pin it.

**MINOR-5 — stated contracts with no test (all verified correct by probe against the branch).**
`report: --since …: invalid date` (`report.py:314-322`); `--min-n 0` → argparse
exit 2 (`report.py:408-412`); `report: cannot read store <S>: <err>`
(`report.py:324-327`); rows with no `result_mtime` (`report.py:287-290`); the
`-` an empty verdict prints and the skipped `None` `wall_s`
(`report.py:302-306, 380-381`); `p = 0` when `n = 0` (`report.py:364`); the
`window:` line text (`report.py:332`). Probes P1–P7 above show each behaving as
the section states, so this is coverage owed, not a defect.

**MINOR-6 — the refusal string is duplicated rather than taken from `evidence.n_gate`: `pkgs/evidence/report.py:351`.**
The section says the line is "the string `evidence.n_gate` returns"
(`pkgs/evidence/evidence.py:244-248` → `return f"insufficient (n={len(rows)})"`).
`report.py:351` re-formats `f"{group}: insufficient (n={len(gr)})"` inline. The
text is identical today; the two copies can drift with nothing to catch it.

**MINOR-7 — a wrong word in the test's own explanation: `tests/evidence/test_harness_report.py:182-183`.**

```
182	    # Approved outputs [10,20,30,40] -> median 25 (lower-median of the even
183	    # pair); rejected [5,100,7] -> 7. Mutant: upper median -> 30.
```

25 is the mean of the middle pair, which is what `statistics.median` returns;
the *lower* median (`statistics.median_low`) of `[10,20,30,40]` is 20. The
assertion and the code are right; the comment names the wrong function.

**MINOR-8 (process, not the seat) — `githooks/pre-commit` exits 1 in a gate clone taken after the run was ingested.**
The only refusal is `tasks: docs/OPERATIONS.md queue block was stale and has
been regenerated — git add docs/OPERATIONS.md and commit again`; the
regeneration is a one-line queue diff dropping `SH1` (`… SD8 SH1 SH2 (…)` →
`… SD8 SH2 (…)`), i.e. the derived queue moved because the store now records
this very run. After staging it the hook is `EXIT=0`. Nothing in the branch
causes it, and the branch correctly carries no `docs/OPERATIONS.md` change.

## Verdict

**APPROVED.** Zero MAJORs; every numbered contract item of the SH1 section is
met and demonstrated; the eleven tests are genuinely red at the base and green
on the branch; 10 of the 11 named mutants die on the test the section names,
and the survivor is the section's own non-discriminating row 11, against a file
this task does not touch. `evidence-unit`, `lint`, `ruff`, the MAP regeneration
and `tasks check` are green; the touches, the single commit, the byte-identical
subject and both trailers are correct.

Owed to the plan side (not blocking this landing): row 11 of the SH1 test table
should assert a store-dependent line and set `EVIDENCE_STORE` on the
subprocess, and SH6 — which extends `harness_report` and keeps these lines'
text — is the natural place to add the order, `--min-n` and `insufficient`-n
assertions (MINOR-2/3/4) as it lands.
