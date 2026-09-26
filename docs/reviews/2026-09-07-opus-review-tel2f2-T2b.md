---
plan_defect: none
mutants_total: 13
mutants_killed: 10
mutants_outside_named: 7
reviewer: opus
majors: null
minors: 5
---
# Opus gate — seat run tel2f2, task T2b — APPROVED

## Summary

Reviewed in a fresh clone of `task/T2b` at `84cbaf3` on base `719bd59` (one commit, subject
byte-identical to the section's). The branch is T2's commit `cc224a7` cherry-picked onto current
main plus the fix round, so the diff against base carries all of T2; the prior gate
(`docs/reviews/2026-09-07-opus-review-tel2-T2.md`) already confirmed T2's 18 reds and 30 of its
31 named mutants, so this gate concentrated on the section's five contract items.

All five are met. The seat's claim that **no production code changed** is true: `git diff
cc224a7..84cbaf3` touches no file under `pkgs/` or `tools/` — only three new fixtures, 28 lines
of pytest, 8 lines of bats (the rest of that diff is main moving under the branch: the three
gate reviews, the ledger, the board, the plan's own T2b section). The MAJOR the last round
rejected on is dead: deleting the `synth=submit` arm of `factory_error_class` now turns
`80-seat-driver.bats` red, and so does moving it below either of the two rules it must outrank.
All six mutants the section names die; three outside-named mutants and one test-side vacuity
probe die too; the only survivors are the three the section explicitly records as **not owed**
here (MINORs 1, 2 and 4 of the prior review). `evidence-unit`, `unit` and `lint` are green with
`--rebuild`. No MAJOR.

## Contract items

Line numbers are in the clone at `84cbaf3`.

### Item 1 — MAJOR-1: the `synth=submit` → `submit-failed` arm tested with its precedence — **MET**

`tests/unit/80-seat-driver.bats:3329-3337`, in the `factory_error_class …precedence` test:

```bash
  # synth=submit beats exit 124 (the first stated precedence pair).
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_error_class '$log' failed 124 100 100 submit ''"
  [ "$output" = "submit-failed" ]

  # synth=submit beats the done guard.
  run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_error_class '$log' done 0 100 100 submit ''"
  [ "$output" = "submit-failed" ]
```

Both assertions are the section's two literals, one `[ … ]` per line. Both mutants the item names
die (N1, N2 below), and both assertions are independently load-bearing (probe N10 below).

### Item 2 — the `error_class` order stated once, on the side the tests demand — **MET**

`tools/factory/seat/factory-lib.sh:106-153` implements exactly the order item 2 states. The
branch sequence as `grep -n ''` prints it, matching the paste in the commit body line for line:

```
110:  case $synth in
111:    submit)
116:  if [ "$exit_code" = "124" ]; then
120:  if [ "$status" = "done" ]; then
124:  case $synth in
125:    nearmiss | none)
130:  case $demoted in
131:    zero-commits | echo)
136:  tail=$(tail -c 4000 -- "$log" 2>/dev/null || true)
137:  … '402' … 'budget_exhausted' → 138: budget-402
141:  … '\b(502|503|529)\b|upstream|provider' → 142: provider-error
145:  … 'UNKNOWN_MODEL' → 146: unknown-model
149:  if [ "$wall_s" -lt 10 ] && [ "$events" -lt 50 ]; then → 150: boot-failure
153:  printf 'none\n'
```

i.e. `submit` → 124 → `done` → synth `nearmiss|none` → demoted → the three tail patterns →
`boot-failure` → `none`: the synth and demoted rules precede the tail patterns, which is what
rows 4, 5 and 14 demand and what item 2 declares supersedes T2's Interfaces bullet. Both reorder
mutants of rows 4 and 5 die (N4, N5 below), at the two line numbers the body pastes (3352 and
3346). The body carries both the `grep -n` sequence and the two reorder reds.

### Item 3 — MINOR-3: the **last** `FACTORY-RESULT status=` line pinned — **MET**

Fixture `tests/evidence/fixtures/results/two-status-lines.result:1-2`:

```
FACTORY-RESULT status=failed
FACTORY-RESULT status=done
```

Test `tests/evidence/test_ingest_result.py:235-242` (`test_last_status_line_wins`) asserts
`rows_of(store)[0]["status"] == "done"` after a rc-0 ingest. The `[-1] → [0]` mutant dies (N6).

### Item 4 — MINOR-6: the missing `run:` / `key:` refusal pinned — **MET**

Fixtures `tests/evidence/fixtures/results/no-run-line.result` (a `key:` line, no `run:`) and
`no-key-line.result` (a `run:` line, no `key:`). Test
`tests/evidence/test_ingest_result.py:245-260` (`test_missing_run_or_key_line_refused`) asserts,
for each, `returncode == 1`, the exact stderr line
`evidence: ingest result: {path}: not a result file`, and `rows_of(store) == []` — the section's
three requirements (stderr as stated, counted refused, nothing written). Deleting the guard at
`pkgs/evidence/ingest_result.py:231-232` dies (N7); so does halving it (N8, N9), so both halves
of the guard are load-bearing.

### Item 5 — the body pastes the red and the green — **MET**

`git log -1` body: the item-1 red under its command line
(`$ nix develop -c bats tests/unit/80-seat-driver.bats --filter error_class`, `not ok 1 …`,
`line 3331`, `` `[ "$output" = "submit-failed" ]' failed ``), the arm-moved-below-124 red, the two
reorder reds of item 2, the item-3 red under `pytest … -k last_status_line`
(`AssertionError: assert 'failed' == 'done'`), the item-4 red under `pytest … -k
missing_run_or_key`, then the greens: `15 passed`, `1..4 / ok 1…ok 4`, `372 passed, 1 skipped`,
`ok 1 .. ok 80`, and the three checks' last lines. Every figure it quotes I reproduced exactly
(see **Checks**). The body also states the why, and states plainly that no production code
changed and why.

### Carried, explicitly not owed by the section

The prior review's MINORs 1, 2, 4 and 5 (the seven diffstat forms unparametrised, `usage: {}`
unfixtured, `route: explicit` unfixtured, `factory_ingest_result`'s `factory_py` branch
unexercised) are still open; the section records them as "recorded, not owed here". I re-applied
three of their mutants and all three still survive — restated below as MINOR-1..3, not charged.

## Red before green

The section's Step 2 defines the red for this round as the *mutants*, since no production code
changes. I ran both that red and the base-implementation red.

1. **Base implementation, branch tests.** In a scratch copy: `factory-lib.sh` and `factory-task`
   checked out at base `719bd59` and `pkgs/evidence/ingest_result.py` moved aside:

```
$ nix develop -c pytest tests/evidence/test_ingest_result.py -q
    src = next(p for p in candidates if p.exists())  # StopIteration when absent
E   StopIteration
ERROR tests/evidence/test_ingest_result.py - StopIteration

$ nix develop -c bats tests/unit/80-seat-driver.bats --filter error_class
not ok 1 factory_error_class classifies the tail patterns with the done/124/synth/demoted precedence
not ok 2 factory_error_class reads only the last 4,000 bytes of the log
not ok 3 factory-task writes error_class and plan, and ingests the result once the file exists
not ok 4 factory-task records error_class=no-result-line for a near-miss FACTORY-RESULT
```

   Restored: `15 passed` (pytest), `80` ok / `0` not ok (bats).

2. **Each new assertion red against its own mutant** — items 1, 3 and 4, pasted under **Mutants**
   (N1/N2 for item 1, N6 for item 3, N7 for item 4), each reverted afterwards, each green again.

No new test is vacuous: every one of the four new assertions was shown red by a mutant that
touches only the rule it pins, including the second `submit` assertion, which bats' abort-on-
first-failure hides until the first is removed (probe N10).

## Mutants

13 applied in a scratch copy of the clone, each reverted after its run. **6 named by the section,
6 killed; 7 outside the named set, 4 killed and 3 survived (all three explicitly not owed).**

| # | mutant | file | test that must kill it | result |
|---|---|---|---|---|
| N1 | item 1 — delete the `synth=submit` arm | factory-lib.sh:110-115 | bats item 1 | KILLED |
| N2 | item 1 — move the arm below the exit-124 rule | factory-lib.sh:110-119 | bats item 1 (first assertion) | KILLED |
| N4 | item 2 — move the demoted check after the tail patterns | factory-lib.sh:130-135 | bats row 4 case | KILLED |
| N5 | item 2 — move the synth check after the tail patterns | factory-lib.sh:124-129 | bats row 5 case | KILLED |
| N6 | item 3 — `status_matches[-1]` → `[0]` | ingest_result.py:233 | `test_last_status_line_wins` | KILLED |
| N7 | item 4 — delete `if run is None or key is None: return None` | ingest_result.py:231-232 | `test_missing_run_or_key_line_refused` | KILLED |
| N3 | *outside* — move the arm below the done guard | factory-lib.sh | bats item 1 | KILLED |
| N8 | *outside* — guard `or` → `and` | ingest_result.py:231 | item 4's test | KILLED |
| N9 | *outside* — guard keeps only the `run` half | ingest_result.py:231 | item 4's test (the `no-key` half) | KILLED |
| N10 | *outside, vacuity probe* — N3 **with item 1's first assertion deleted** | both | bats item 1 (second assertion) | KILLED |
| O1 | *outside, carried MINOR-1* — diffstat `files?` → `files` | ingest_result.py:28 | — | SURVIVED |
| O2 | *outside, carried MINOR-2* — `"duration_s": None` → `0` | ingest_result.py:139 | — | SURVIVED |
| O5 | *outside, carried MINOR-4* — drop the `route: explicit` arm | ingest_result.py:78-79 | — | SURVIVED |

Evidence, as the runs printed it:

```
===== N1 (submit arm deleted)
not ok 1 factory_error_class classifies the tail patterns with the done/124/synth/demoted precedence
# (in test file tests/unit/80-seat-driver.bats, line 3331)
#   `[ "$output" = "submit-failed" ]' failed

===== N2 (arm moved below the exit-124 rule)
not ok 1 …
# (in test file tests/unit/80-seat-driver.bats, line 3331)
#   `[ "$output" = "submit-failed" ]' failed

===== N3 (arm moved below the done guard)
not ok 1 …
# (in test file tests/unit/80-seat-driver.bats, line 3331)
#   `[ "$output" = "submit-failed" ]' failed

===== N4 (demoted check after the tail patterns)
not ok 1 …
# (in test file tests/unit/80-seat-driver.bats, line 3352)
#   `[ "$output" = "template-echo" ]' failed

===== N5 (synth check after the tail patterns)
not ok 1 …
# (in test file tests/unit/80-seat-driver.bats, line 3346)
#   `[ "$output" = "no-result-line" ]' failed

===== N6 ([-1] -> [0])
>       assert rows_of(store)[0]["status"] == "done"
E       AssertionError: assert 'failed' == 'done'
FAILED tests/evidence/test_ingest_result.py::test_last_status_line_wins
1 failed, 14 passed in 2.10s

===== N7 (guard deleted)
>       assert f"evidence: ingest result: {out}: not a result file" in r.stderr
E       AssertionError: assert '…/factory/runs/tel2/T2.result: not a result file' in
        '…/factory/runs/tel2/T2.result: run_id: null not allowed\n'
FAILED tests/evidence/test_ingest_result.py::test_missing_run_or_key_line_refused
1 failed, 14 passed in 2.09s

===== N8 (or -> and)      same failure, same test                         1 failed, 14 passed
===== N9 (run half only)  >  assert … {out2}: not a result file … in '… key: null not allowed\n'
                          FAILED … test_missing_run_or_key_line_refused   1 failed, 14 passed

===== N10 (N3 with the first submit assertion removed; line 3331 is now the second)
not ok 1 …
# (in test file tests/unit/80-seat-driver.bats, line 3331)
#   `[ "$output" = "submit-failed" ]' failed

===== O1 / O2 / O5        15 passed in 2.10s  (each survives — carried MINORs, not owed here)
```

## Checks

Every command run inside the fresh clone at `84cbaf3`, `XDG_CACHE_HOME` under the scratchpad.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | rc=0, `373 passed in 9.60s` |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | rc=0, `ok 491 …` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | rc=0 |
| pre-commit | `nix develop -c githooks/pre-commit` | rc=1 first run, rc=0 second — **not attributable to the change**, the same environment effect the tel2 gate recorded: the hook regenerates the board's queue block and drops `T2b` (`… T1Wb T2b T3b` → `… T1Wb T3b`) because `tel2f2`'s own `.result` exists under the live runs dir. The edit is confined to line 15, strictly between `<!-- tasks:begin -->` (14) and `<!-- tasks:end -->` (16); nothing else in the hook is red |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!`, rc=0 |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `64 files already formatted`, rc=0 |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc=0 (the committed MAP is current) |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, rc=0 |
| pytest | `nix develop -c pytest tests/evidence/test_ingest_result.py -q` | `15 passed` |
| pytest | `nix develop -c pytest tests/evidence -q` | `372 passed, 1 skipped` |
| bats | `nix develop -c bats tests/unit/80-seat-driver.bats` | 80 ok, 0 not ok |

No acceptance check is red. Every figure the commit body quotes reproduces exactly.

## Touches and commit

Seventeen files in `git diff 719bd59..84cbaf3 --stat`. Sixteen are the section's `touches`,
exactly: `pkgs/evidence/ingest_result.py`, `tests/evidence/test_ingest_result.py`, the eleven
fixtures under `tests/evidence/fixtures/results/` (`done`, `status-pass`, `hostile-checks`,
`template-echo`, `timeout`, `submit-failed`, `no-result-line`, `classified`, `two-status-lines`,
`no-run-line`, `no-key-line`), `tools/factory/seat/factory-lib.sh`,
`tools/factory/seat/factory-task`, `tests/unit/80-seat-driver.bats`.

The one file outside `touches` is `docs/MAP.md` (1 line), the Global Constraints' exception 1;
regenerating it produces no further diff. `docs/OPERATIONS.md` is **not** in the commit — the
section's Step 1 required main's copy, and that is what the tree carries.

**No unexplained file outside `touches`. No board commit. The plan file is untouched.**

Commit convention:

- Exactly one commit, `84cbaf3` (`git rev-list --count 719bd59..HEAD` → `1`).
- Subject byte-identical to the section's literal, compared as bytes: `BYTE-IDENTICAL`
  (`b'evidence: the tasks stream, fix round \xe2\x80\x94 the submit-failed arm tested with its
  precedence, the error_class order stated once, the last status line and the run/key refusal
  pinned (test: evidence-unit, unit, lint)'`).
- The body states the why, pastes the reds and the greens (item 5), and states the no-production-
  change claim.
- Both trailers after a blank line: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813
  (seat headless, factory run tel2f2)` and `Co-Authored-By: Claude Fable 5.1
  <noreply@anthropic.com>`.

The seat's "no production code changed" claim, verified against T2's branch
(`/home/dalhaka/factory/ws/tel2/T2`, `task/T2` = `cc224a7`): `git diff cc224a7..84cbaf3
--name-only` lists no path under `pkgs/` or `tools/` — only the three new fixtures,
`tests/evidence/test_ingest_result.py` (+28), `tests/unit/80-seat-driver.bats` (+8), and the
docs main advanced by (`docs/MAP.md`, `docs/OPERATIONS.md`, `docs/board/log-2026-09.md`,
`docs/ledger/plan-defects.toml`, the three tel2 reviews, the plan's T2b section).

## Findings

### MINOR-1 — the seven diffstat forms are still unparametrised (carried, not owed)

`tests/evidence/test_ingest_result.py:174-215`, `pkgs/evidence/ingest_result.py:28`

Mutant O1 (`files?` → `files`, so the singular form stops matching) leaves `15 passed`. The
section records this as not owed in this round; it survives into T2's ledger, not into this
verdict.

### MINOR-2 — `usage: {}` still has no fixture (carried, not owed)

`pkgs/evidence/ingest_result.py:139`

Mutant O2 (`"duration_s": None` → `0`) leaves `15 passed`.

### MINOR-3 — the `route: explicit` arm still has no fixture (carried, not owed)

`pkgs/evidence/ingest_result.py:78-79`

Mutant O5 (delete the arm, so `explicit` falls through to `unknown`) leaves `15 passed`. The
section's own Facts count `explicit` in 12 of the 86 routed results.

### MINOR-4 — the section's "delete the arm → both red" is not observable in one bats run

`docs/superpowers/plans/2026-09-06-telemetry-store-1.md` (T2b item 1), `tests/unit/80-seat-driver.bats:3329-3337`

bats aborts a test at its first failed assertion, so N1 reports only the first of the two new
`submit` assertions; the seat said so in the body rather than manufacturing a second run. Not a
defect in the work — I confirmed the second assertion is load-bearing by deleting the first and
re-applying N3 (probe N10, red at the second assertion). Worth one sentence in a future section
("→ red at the first assertion; bats stops there") so the expectation matches the tool.

### MINOR-5 — `factory_ingest_result`'s `factory_py` branch is still unexercised (carried, not owed)

`tools/factory/seat/factory-lib.sh:159-166`

Unchanged from the tel2 review: every bats test sets `FACTORY_EVIDENCE_CMD`, and
`factory_ingest_result` passes no `--runs-root`, so the driver→ingest path cannot be proved end
to end from a test tree. Recorded, not owed here.

## Verdict

**APPROVED** — all five contract items are met with the evidence the section demands; the MAJOR
that rejected tel2 is dead (three separate mutants of the `synth=submit` arm and its two
precedence pairs now go red); the two reorder mutants of rows 4 and 5 confirm the `error_class`
order item 2 states is what the code implements; the two-status-line and missing-`run:`/`key:`
fixtures each kill their named mutant; `evidence-unit`, `unit` and `lint` are green with
`--rebuild`, `ruff`, `ruff format`, the MAP regeneration and `tasks.py check` are clean, and the
commit is one commit with the byte-exact subject, both trailers, and a body carrying the reds and
the greens. No production code changed, as the seat claimed and the diff against `cc224a7`
confirms. Five MINORs, four of them explicitly carried forward by the section itself and none
charged to this round. `plan_defect: none`.
