---
plan_defect: implementer
plan_defect_secondary: missing-case
mutants_total: 38
mutants_killed: 30
mutants_outside_named: 7
reviewer: opus
majors: 1
minors: 7
---
# Opus gate — seat run tel2, task T2 — REJECTED

## Summary

Reviewed in a fresh clone of `task/T2` at `cc224a7` on base `e0b80e2` (one commit, subject
byte-identical to the section's). The section's contract is met almost everywhere: the ingest
is a metadata-only producer, the runs-root fence is checked over every path before any write,
the `checks` map is refused (never stored) on a hostile or forbidden key, `error_class` in the
driver carries the precedence the test rows demand, and all three acceptance checks
(`evidence-unit`, `unit`, `lint`) are green on a fresh build *and* on `--rebuild`. Thirteen
pytest tests and five bats tests were shown red against the base implementation and green
against the branch.

One MAJOR: the **`synth=submit` → `submit-failed` arm of `factory_error_class`** — the first rule
of the section's stated order and the driver's own first synthesising branch — has **no test at
all**. Deleting the whole arm leaves all 80 tests in `tests/unit/80-seat-driver.bats` green.
Row 14's mutant column reads "any rule", so this is a named mutant that survives, which is the
same failure shape the T1 gate rejected on (one arm per enum, deletions survive). Six further
stated behaviours have no test (recorded as MINORs, each with a surviving mutant).

The section itself carries one real defect, recorded here and not charged to the seat: its
`factory_error_class` **Interfaces order contradicts its own test rows 4, 5 and 14** (see
*Plan defect* below). The seat implemented the side the tests demand; that was the right call.

## Contract items

Line numbers are in the clone at `cc224a7`.

### CLI (`ingest_result.main` / `ingest`)

| # | contract | verdict | evidence |
|---|---|---|---|
| I1 | `evidence [--store S] ingest result [--runs-root DIR] <path>...`, subparser `result`, `--runs-root` defaults to `~/factory/runs`, expanded | MET | `pkgs/evidence/ingest_result.py:370-383`: `rp = sub.add_parser("result", …)`, `rp.add_argument("--runs-root", default=os.path.expanduser("~/factory/runs"))`, `runs_root = os.path.expanduser(args.runs_root)` |
| I2 | every path `realpath`-ed and inside `<root>/` **before any write**; first outside → `evidence: ingest result: <path> is outside <root>`, exit 2, nothing written | MET | `ingest_result.py:335-341` (fence loop runs to completion before the parse loop), `:386-391` (exit 2). `tests/evidence/test_ingest_result.py:415-429` asserts rc 2 and `not (store2/"derived"/"tasks.jsonl").exists()` for `[good, /etc/passwd]` |
| I3 | no `FACTORY-RESULT status=` line, or no `run:`/`key:` line → `…: not a result file`, counted refused | MET (partly untested) | `ingest_result.py:226-232, 352-356`; `test_ingest_result.py:227-232`. The `run:`/`key:` arm has no test — see MINOR-6 |
| I4 | a path inside the root that does not exist → the same line, counted refused, no unhandled `FileNotFoundError` | MET | `ingest_result.py:346-351` (`except OSError`); `test_ingest_result.py:431-437` asserts rc 1, the line, and `"Traceback" not in r3.stderr` |
| I5 | a refused row → its reasons on stderr prefixed with the path, counted refused, the other rows still land | MET | `ingest_result.py:357-362`; `test_ingest_result.py:498-507` (`model: not a model-id`, only `T5` lands) |
| I6 | stdout `ingested {n} rows into derived/tasks ({m} refused)`; exit 0 when `m == 0` else 1 | MET | `ingest_result.py:392-393`; `test_ingest_result.py:507` asserts the literal |
| I7 | the log beside the result is never opened | MET | no read of any `.log` anywhere in `ingest_result.py`; `test_ingest_result.py:531-546` (a `chmod 000` sibling log); mutant M20 killed |

### Row producers (`kind: task-result`, stream `derived/tasks`, key `(run_id, key)`)

| # | contract | verdict | evidence |
|---|---|---|---|
| P1 | `run_id` ← `run:`; `key` ← `key:` | MET | `ingest_result.py:229-230, 293-294` |
| P2 | `repo` ← `tasks._repo_from_workspace(...)` or `None` | MET | `ingest_result.py:239-240`; `test_ingest_result.py:510-528` |
| P3 | `plan` ← the `plan:` line mapped to `docs/superpowers/plans/<basename>` when it contains `/docs/superpowers/plans/`, else `None`; absent → `None` | MET | `ingest_result.py:174-179`; `test_ingest_result.py:392-412`; mutant M15 killed |
| P4 | `route` ← the route pattern else `unknown` | MET (one arm untested) | `ingest_result.py:74-83`; `test_ingest_result.py:477-496`. The `explicit` arm (12 of 86 in the corpus, the section's own Facts) has no fixture — MINOR-4 |
| P5 | **`task_kind`** (T1b correction, not `kind`) / `size` ← the `implement/<kind>/<size>` parts, `unknown` otherwise | MET | declared field is `task_kind` (`pkgs/evidence/streams.py:276`); producer writes `"task_kind": task_kind` (`ingest_result.py:297`); `test_ingest_result.py:186-187` asserts `row["task_kind"] == "code"`, `row["size"] == "S"`, and `:484-485, 494-495` the `unknown` arms. A row with the `<kind>` part lands (`evidence-unit`, 371 passed) |
| P6 | `model` ← `model:`; `effort` ← the enum else `unknown` | MET | `ingest_result.py:286-287, 299`; `test_ingest_result.py:470-475`; mutant M19 killed |
| P7 | `status` ← the **last** `FACTORY-RESULT status=` line's word when in the enum, else `unknown` | MET (the "last" rule untested) | `ingest_result.py:226, 233-234`; `test_ingest_result.py:218-224`; mutant O3 (`[-1]`→`[0]`) survives — MINOR-3 |
| P8 | `exit_code`, `wall_s` ← int or `None` | MET | `ingest_result.py:242-243`; `test_ingest_result.py:192-193` |
| P9 | `commits` ← lines between `commits (…):` and the next blank matching `^[0-9a-f]{7,40} `; `commits_declared` ← `FACTORY-COMMITS N` or `None` | MET | `ingest_result.py:86-98, 274-277`; `test_ingest_result.py:194-195, 300`; mutant M2 killed |
| P10 | `checks`/`checks_parse`: `<name>=<verdict>`, name `^[a-z][a-z0-9-]{0,63}$`, verdict in the three, ≤64 tokens, a `streams.FORBIDDEN` name is a violation → `{}` + `refused`, row lands; no line → `missing`; `FACTORY-CHECKS none` → `refused` | MET | `ingest_result.py:101-122, 322-328`; `test_ingest_result.py:235-289` covers all six cases incl. 64 → `ok`, 65 → `refused`; mutants M4, M5, M6 all killed |
| P11 | `head`/`base` ← the 40-hex value or `None` | MET | `ingest_result.py:281-284`; `test_ingest_result.py:198-199` |
| P12 | `files_changed`/`insertions`/`deletions` from the diffstat summary, absent parts 0, no summary 0/0/0 | MET (one form tested) | `ingest_result.py:27-30, 125-129`; `test_ingest_result.py:200-202`. Only the full three-part form is asserted; mutant O1 survives — MINOR-1 |
| P13 | `usage` ← the JSON remapped, `0` for a missing integer, `None` for a missing `duration_s`; `usage: {}` → zeros and `None` | MET (the `{}` case untested) | `ingest_result.py:132-163`; `test_ingest_result.py:203-210`; mutant M1 killed, mutant O2 survives — MINOR-2 |
| P14 | `error_class` ← the `error_class:` line when present, else the metadata-only fallback in the stated order | MET | `ingest_result.py:189-218, 253-267`; `test_ingest_result.py:292-389`; mutants M7, M9, M11, M12, M13, M14 all killed |
| P15 | `seat_unit` ← `seat: unit seat@<id>` → `<id>` else `None`; `result_path` ← the real path; `result_mtime` ← the file mtime as `ts` | MET | `ingest_result.py:33-35, 269-272, 289, 317-318`; `test_ingest_result.py:405, 214-215` |
| P16 | re-ingest is byte-identical; two files, one `(run, key)` → the later replaces | MET | `test_ingest_result.py:440-465`; mutant M18 (key by `result_path`) killed |

### `tools/factory/seat/factory-lib.sh`

| # | contract | verdict | evidence |
|---|---|---|---|
| L1 | `factory_error_class <log> <status> <exit_code> <wall_s> <events> <synth> <demoted>` prints one enum word; empty `wall_s`/`events` count as 0; never fails, an unreadable log reads as empty | MET | `factory-lib.sh:106-108` (the seven positionals, the two `[ -n … ] \|\| =0` lines), `:136` (`tail … 2>/dev/null \|\| true`) |
| L2 | rule 1 `submit` → `submit-failed` | **MET but untested — MAJOR-1** | `factory-lib.sh:110-115`; deleting lines 110-115 leaves all 80 bats tests green |
| L3 | rule 2 `exit_code` 124 → `timeout` | MET | `:116-119`; mutant S5 killed |
| L4 | rule 3 `status` done → `none` (the done guard) | MET | `:120-123`; mutant M21 killed |
| L5 | `budget-402` / `provider-error` / `unknown-model` tail rules, over `tail -c 4000` | MET | `:136-148`; mutants S1, S2, S3, M22 all killed |
| L6 | `synth` in `nearmiss\|none` → `no-result-line`; `demoted` in `zero-commits\|echo` → `template-echo` | MET, and ordered **before** the tail rules as rows 4/5/14 require | `:124-134`; mutants M8, M10 killed separately |
| L7 | `wall_s` < 10 and `events` < 50 → `boot-failure`, else `none` | MET | `:149-153`; mutant S6 killed |
| L8 | `factory_ingest_result <result>`: `FACTORY_EVIDENCE_CMD` when set else `factory_py …/evidence.py`, `${EVIDENCE_STORE:+--store …} ingest result "$result"`, stdout+stderr appended to `$log`, returns the status | MET (the `factory_py` branch untested) | `factory-lib.sh:159-166` — byte-for-byte the shape the section states. MINOR-5 |

### `tools/factory/seat/factory-task`

| # | contract | verdict | evidence |
|---|---|---|---|
| F1 | `synth` set in the three synthesising branches; `demoted` in the three CR3r arms | MET | `factory-task:249-250` (init), `:252` `synth=submit`, `:261` `nearmiss`, `:269` `none`, `:301` `mismatch`, `:306` `zero-commits`, `:311` `echo` |
| F2 | `events` parsed with `[[ $usage_json =~ \"events\":\ *([0-9]+) ]]`; `error_class=$(factory_error_class …)` after the CR3r block | MET | `factory-task:361-365`, byte-for-byte the stated expression, at line 365 (the CR3r block ends at 316) |
| F3 | `printf 'plan: %s\n' "$plan"` after `route:`, `printf 'error_class: %s\n' "$error_class"` after `exit_code:` | MET | `factory-task:375-376` and `:387-388` |
| F4 | after `} >"$result"`: `factory_ingest_result "$result" \|\| factory_log "evidence: could not record $key"`; `exit "$task_rc"` unchanged | MET | `factory-task:399-401`; `tests/unit/80-seat-driver.bats` "…ingests the result once the file exists" (the fake records `[ -f "$3" ]` → `FOUND`, exactly two recorded lines) and "…keeps its exit code when the evidence recorder fails" |

## Red before green

The section's Step 2 red, reproduced in a copy of the branch with `pkgs/evidence/ingest_result.py`
removed and `factory-lib.sh` / `factory-task` checked out at base `e0b80e2` (branch tests kept):

```
$ nix develop -c pytest tests/evidence/test_ingest_result.py -q
../gate-tel2-T2/tests/evidence/test_ingest_result.py:39: in _load_ingest
    src = next(p for p in candidates if p.exists())  # StopIteration when absent
E   StopIteration
ERROR tests/evidence/test_ingest_result.py - StopIteration
1 error in 0.08s
```

```
$ nix develop -c bats tests/unit/80-seat-driver.bats --filter error_class
1..4
not ok 1 factory_error_class classifies the tail patterns with the done/124/synth/demoted precedence
#   `[ "$output" = "budget-402" ]' failed
not ok 2 factory_error_class reads only the last 4,000 bytes of the log
not ok 3 factory-task writes error_class and plan, and ingests the result once the file exists
not ok 4 factory-task records error_class=no-result-line for a near-miss FACTORY-RESULT
BW01: … `factory_error_class …` exited with code 127, indicating 'Command not found'
```

and the fifth bats test, which `--filter error_class` does not match:

```
$ nix develop -c bats tests/unit/80-seat-driver.bats --filter 'evidence recorder fails'
not ok 1 factory-task keeps its exit code when the evidence recorder fails
#   `[[ "$output" == *"evidence: could not record K1"* ]]' failed
```

Restored to the branch: `13 passed` (pytest) and `ok 76 … ok 80` (bats, 80 of 80). Every one of
the 18 new tests was shown red. No test in the section is vacuous.

## Mutants

38 applied in a scratch copy, each reverted after the run. **31 named by the section, 30 killed;
7 outside the named set, all 7 survived.**

| # | mutant (section row) | file | test that must kill it | result |
|---|---|---|---|---|
| M1 | row 1 "any one field's producer" — `("cacheRead","cache_read")` → `("cache_read",…)` | ingest_result.py:152 | pytest row 1 | KILLED |
| M2 | row 1 — commits counter `n += 1` → `n += 0` | ingest_result.py:96 | pytest row 1 (`commits 1`) | KILLED |
| M3 | row 2 "accept any word" | ingest_result.py:234 | row 2 (`status: not in enum …`) | KILLED |
| M4 | row 3 "store the map anyway" | ingest_result.py:117-121 | row 3 (`checks.xxxx…: not a re`) | KILLED |
| M5 | row 3 "`>` vs `>=`" | ingest_result.py:110 | row 3 (64 tokens → `ok`) | KILLED |
| M6 | row 3 "keep the forbidden-named key" | ingest_result.py:119-120 | row 3 (`checks.log: forbidden name`) | KILLED |
| M7 | row 4 "drop the zero-commit rule" | ingest_result.py:210-211 | row 4 (`assert 'none' == 'template-echo'`) | KILLED |
| M8 | row 4 "reorder the demoted check after the tail-pattern checks" | factory-lib.sh:130-134 | bats row 14 (`[ "$output" = "template-echo" ]`) | KILLED |
| M9 | row 5 "drop the exit-124 rule" | ingest_result.py:194-195 | row 5 (`assert 'none' == 'timeout'`) | KILLED |
| M10 | row 5 "reorder the synth check after the tail-pattern checks" | factory-lib.sh:124-129 | bats row 14 (`[ "$output" = "no-result-line" ]`) | KILLED |
| M11 | row 6 "each rule" — drop `no-result-line` | ingest_result.py:198-204 | row 6 | KILLED |
| M12 | row 6 — drop `boot-failure` | ingest_result.py:212-217 | row 6 | KILLED |
| M13 | row 6 — drop `submit-failed` (ingest fallback) | ingest_result.py:192-193 | row 5 (`assert 'timeout' == 'submit-failed'`) | KILLED |
| M14 | row 7 "ignore the line" | ingest_result.py:254-255 | row 7 (`assert 'none' == 'provider-error'`) | KILLED |
| M15 | row 8 "keep the absolute path" | ingest_result.py:177-179 | row 8 (`plan: outside root docs/superpowers/plans/`) | KILLED |
| M16 | row 9 "check paths while writing" (fence lazily **and** write per file) | ingest_result.py:335-366 | row 9 (`assert not (store2/derived/tasks.jsonl).exists()`) | KILLED |
| M17 | row 9 "let the missing-file case raise" | ingest_result.py:346-351 | row 9 (`Traceback` in stderr) | KILLED |
| M18 | row 10 "replace by path" — key `("result_path",)` | streams.py:270 | row 10 (`assert 2 == 1`) | KILLED |
| M19 | row 11 "map an unknown effort through" | ingest_result.py:287 | row 11 (`effort: not in enum …`) | KILLED |
| M20 | row 13 "open the log for the tail" | ingest_result.py:352 | row 13 (traceback on the `chmod 000` log) | KILLED |
| M21 | row 14 "the done guard" | factory-lib.sh:120-123 | bats row 14 + row 16 | KILLED |
| M22 | row 15 "drop `tail -c 4000`" → `cat` | factory-lib.sh:136 | bats row 15 | KILLED |
| M23 | row 16 "write the line before the file" (call moved above the `{…} >"$result"` block) | factory-task:399 | bats row 16 (`[ "${lines[0]}" = "FOUND" ]`) | KILLED |
| M24 | row 16 "skip the call" | factory-task:399 | bats row 16 (`[ "${#lines[@]}" -eq 2 ]`) | KILLED |
| M25 | row 17 "`set -e` on the call" (drop the `\|\| factory_log`) | factory-task:399 | bats row 17 (`[ "$status" -eq 0 ]`) | KILLED |
| S1 | row 14 "any rule" — drop `budget-402` | factory-lib.sh:137-140 | bats rows 14, 15 | KILLED |
| S2 | row 14 — drop `provider-error` | factory-lib.sh:141-144 | bats row 14 | KILLED |
| S3 | row 14 — drop `unknown-model` | factory-lib.sh:145-148 | bats row 14 | KILLED |
| **S4** | **row 14 — drop the `synth=submit` → `submit-failed` arm** | **factory-lib.sh:110-115** | **none** | **SURVIVED** |
| S5 | row 14 — drop the exit-124 rule (shell) | factory-lib.sh:116-119 | bats row 14 | KILLED |
| S6 | row 14 — drop `boot-failure` (shell) | factory-lib.sh:149-153 | bats row 14 | KILLED |

Outside the named set (7 tried, 7 survived — each is a stated behaviour with no assertion):

| # | mutant | file | result |
|---|---|---|---|
| O0 | fence lazily, writing the rows accumulated *before* the current path (a weaker "check paths while writing") | ingest_result.py:335-341 | SURVIVED (the section's fixture is `[good, outside]`; a third path would be needed) |
| O1 | diffstat `^ (\d+) files? changed` → `files` (plural only) | ingest_result.py:28 | SURVIVED |
| O2 | `usage["duration_s"]` default `None` → `0` | ingest_result.py:139 | SURVIVED |
| O3 | `status_matches[-1]` → `[0]` (first, not last) | ingest_result.py:233 | SURVIVED |
| O4 | `_notes_body` `ms[-1]` → `ms[0]` | ingest_result.py:170 | SURVIVED |
| O5 | drop the `route: explicit` arm | ingest_result.py:78-79 | SURVIVED |
| O6 | drop the `run is None or key is None` refusal | ingest_result.py:231-232 | SURVIVED |

## Checks

Every command run inside the fresh clone at `cc224a7` (`XDG_CACHE_HOME` under the scratchpad).

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` then `--rebuild` | `rc=0`, `rc=0` (371 passed, both runs) |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link` then `--rebuild` | `rc=0`, `rc=0` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` then `--rebuild` | `rc=0`, `rc=0` |
| pre-commit | `nix develop -c githooks/pre-commit` | `rc=1` on the **first** run, `rc=0` on the second — **not attributable to the change**: the hook regenerates the board's queue block and, in my environment, drops `T2` from the queued list (`… SD8 T1W T2 T3 …` → `… SD8 T1W T3 …`), because `tel2`'s own `.result` now exists under the live runs dir and `tasks` marks the key `ran` (§Waves documents this: `--runs-dir /nonexistent` "hides their `ran` state"). Nothing else in the hook is red; after `git add docs/OPERATIONS.md` the hook exits 0 |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!`, rc=0 |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `64 files already formatted`, rc=0 |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc=0 (the committed MAP is current) |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, rc=0 |
| pytest | `nix develop -c pytest tests/evidence/test_ingest_result.py -q` | `13 passed` |
| bats | `nix develop -c bats tests/unit/80-seat-driver.bats` | 80 ok, 0 not ok |

No acceptance check is red.

## Touches and commit

Fifteen files in `git diff e0b80e2..HEAD --stat`. Thirteen are the section's `touches`, exactly:

`pkgs/evidence/ingest_result.py`, `tests/evidence/test_ingest_result.py`, the eight fixtures
under `tests/evidence/fixtures/results/` (`done`, `status-pass`, `hostile-checks`,
`template-echo`, `timeout`, `submit-failed`, `no-result-line`, `classified`),
`tools/factory/seat/factory-lib.sh`, `tools/factory/seat/factory-task`,
`tests/unit/80-seat-driver.bats`.

The two outside `touches` are both **by rule**, not deviations:

- `docs/MAP.md` (1 line: `tests/evidence — 57 files` → `66 files`) — Global Constraints, "One
  writer per tree", exception 1; regenerating it produces no further diff.
- `docs/OPERATIONS.md` (1 line) — exception 2, the board's queue block. The change is confined
  to line 15, strictly between `<!-- tasks:begin -->` (line 14) and `<!-- tasks:end -->` (line
  16); nothing outside the block moved. Verified with `git diff … -- docs/OPERATIONS.md` and
  `grep -n 'tasks:begin\|tasks:end' docs/OPERATIONS.md`.

**No unexplained file outside `touches`. No board commit. The plan file is untouched.**

Commit convention:

- Exactly one commit, `cc224a7`, on base `e0b80e2`.
- Subject byte-identical to the section's — `cmp` against the section's literal:
  `SUBJECT BYTE-IDENTICAL`.
- Body states the why (the tasks stream, the fence before any write, the refusal of free text
  and forbidden check names, the exit code never changed by a recording problem).
- Both trailers present after a blank line: `Generated-By: dsh 0.1.2-rc.1 / deepseek/…` and
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- The body does **not** paste the red and the green (MINOR-7).

## Plan defect (recorded, not charged to the seat)

The section's `factory_error_class` **Interfaces** bullet states the order:

> … `status` = `done` → `none`; … `402` and `budget_exhausted` → `budget-402`; … `provider-error`;
> … `UNKNOWN_MODEL` → `unknown-model`; `synth` in `nearmiss|none` → `no-result-line`; `demoted`
> in `zero-commits|echo` → `template-echo`; …

but its own test rows say the opposite twice, and name the reordering as the mutant:

> row 4: a `demoted=echo` result whose log tail contains the word `provider` → `template-echo`,
> not `provider-error` (**the demoted rule wins over the tail-pattern rule**) … mutant: reorder
> the demoted check after the tail-pattern checks
> row 5: a `synth=nearmiss` result whose log tail contains `503` → `no-result-line`, not
> `provider-error` (**the synth-branch rule wins over the tail-pattern rule**)

Errata 2 and 3 of `docs/reviews/plan-judgements/2026-09-06-telemetry-1.md` are exactly this
("document and pin whichever precedence is intended"); the fixtures were folded into the test
tables at ship, the Interfaces order was not. Compounding it, rows 4 and 5 place those two
clauses in the **pytest** table, though the ingest never opens a log and so cannot express them —
they can only live in bats. The seat resolved the contradiction the right way (synth/demoted
before the tail patterns, `factory-lib.sh:124-134`) and put the assertions in bats
(`80-seat-driver.bats:3337-3346`). Class: `wrong-fact` in the section's Interfaces order. It is
**not** the reason for this rejection.

Errata 5 and 11 were folded into the section's text before dispatch and the seat implemented
both correctly (I4 and P10 above; mutants M17 and M6 killed).

## Findings

### MAJOR-1 — the `synth=submit` → `submit-failed` arm of `factory_error_class` has no test; a named mutant survives

`tools/factory/seat/factory-lib.sh:110-115`

```bash
  case $synth in
    submit)
      printf 'submit-failed\n'
      return 0
      ;;
  esac
```

This is rule 1 of the section's stated order, and the class the driver assigns to every seat
whose submit produced no job id (`tools/factory/seat/factory-task:252` sets `synth=submit` in
that branch). Row 14's mutant column is "any rule". Deleting the six lines above:

```
$ nix develop -c bats tests/unit/80-seat-driver.bats | grep -c '^ok '
80
$ nix develop -c bats tests/unit/80-seat-driver.bats | grep -E '^not ok'
(no output)
```

Every one of the 80 tests stays green. `grep -rn 'factory_error_class' tests/` shows the only
invocations are `80-seat-driver.bats:3307-3368`, and **not one passes `submit` as the `synth`
argument** — the fourteen calls pass `''`, `nearmiss`, `none`, `zero-commits` or `echo`. The
precedence pair the section states first (`submit` beating `exit_code` 124) is likewise
unasserted; the pytest side tests only the *ingest's* metadata fallback (`test_ingest_result.py:325-338`),
which is a different code path and is not what classifies a live run.

This is the same shape the T1 gate rejected on ("row 13's arm deletions survive — one arm per
enum parametrised"). Closing it is one line in the existing test:

```bash
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_error_class '$log' failed 124 100 100 submit ''"
  [ "$output" = "submit-failed" ]
```

### MINOR-1 — the seven diffstat forms are not parametrised

`tests/evidence/test_ingest_result.py:174-215`, `tests/evidence/fixtures/results/*.result`

The section's **Tests** line names "the seven diffstat forms (one fixture each in row 1's
parametrisation)". Three shapes appear in the fixtures (` 2 files changed, 10 insertions(+), 3
deletions(-)`, ` 1 file changed`, ` 0 files changed`) and only the first is ever asserted; the
"no summary → 0/0/0" arm has no fixture at all. Mutant O1 (`files?` → `files`, i.e. the singular
form stops matching) leaves `13 passed`.

### MINOR-2 — `usage: {}` has no fixture

`pkgs/evidence/ingest_result.py:132-163`, `tests/evidence/test_ingest_result.py:78`

The section states "`usage: {}` → zeros and `None`" and names it a discriminating fixture. No
fixture or inline result carries `usage: {}` (`grep -n 'usage:' tests/evidence/fixtures/results/*.result`
shows a full object in all eight). Mutant O2 (`"duration_s": None` → `0` in the default) leaves
`13 passed`.

### MINOR-3 — "the **last** `FACTORY-RESULT status=` line" is not pinned

`pkgs/evidence/ingest_result.py:233`

`status_word = status_matches[-1].group(1)` implements the rule, but no fixture carries two
`FACTORY-RESULT status=` lines. Mutant O3 (`[-1]` → `[0]`) leaves `13 passed`.

### MINOR-4 — the `route: explicit` arm has no fixture

`pkgs/evidence/ingest_result.py:78-79`

The section's own Facts count `explicit` in 12 of the 86 routed results, and `streams.py:280`
declares it in the route pattern. Mutant O5 (delete the two lines, so `explicit` falls through
to `unknown`) leaves `13 passed`.

### MINOR-5 — `factory_ingest_result`'s `factory_py` branch is never exercised

`tools/factory/seat/factory-lib.sh:159-166`

Every bats test sets `FACTORY_EVIDENCE_CMD`, so only the seam is tested; the production branch
(`factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py" … ingest result`) has no
coverage. Related, and a consequence of the section's exact command line rather than of the
seat's work: `factory_ingest_result` passes no `--runs-root`, so the ingest always fences
against the real `~/factory/runs`; with `FACTORY_ROOT` pointed elsewhere the call exits 2 and is
swallowed by `|| factory_log "evidence: could not record $key"` (`factory-task:399`). Harmless in
production (`FACTORY_ROOT` is `~/factory`), but it means the driver→ingest path can never be
proved end to end from a test tree.

### MINOR-6 — the "no `run:`/`key:` line" refusal arm has no test

`pkgs/evidence/ingest_result.py:231-232`

The section states two ways a file "does not parse"; only the missing-`FACTORY-RESULT` way is
asserted (`test_ingest_result.py:227-232`). Mutant O6 (delete the guard) leaves `13 passed` —
the row then fails the fence instead, with a different stderr line and the same exit code.

### MINOR-7 — the commit body pastes neither the red nor the green

`cc224a7` (commit message)

The body states the why in five sentences and carries both trailers, but no red or green output
is quoted, as the house convention for a TDD task requires.

## Verdict

**REJECTED** — one MAJOR: the `synth=submit` → `submit-failed` arm of `factory_error_class`
(`tools/factory/seat/factory-lib.sh:110-115`) is untested and a mutant named by row 14 ("any
rule") survives the whole suite. Everything else in the section's contract is met, all three
acceptance checks are green on a fresh clone including `--rebuild`, all 18 new tests were shown
red before green, and 30 of the 31 named mutants die. `plan_defect: implementer`
(the seat left a stated enum arm with no test), secondary `missing-case` (row 14's fixture list
omits a `synth=submit` case while its mutant column demands one). The section's own
`factory_error_class` precedence contradiction is recorded above as a plan defect to fix in the
re-plan; it did not cause this rejection.
