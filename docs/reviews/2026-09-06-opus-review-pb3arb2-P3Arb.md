---
plan_defect: implementer
plan_defect_secondary: wrong-fact
mutants_total: 14
mutants_killed: 9
mutants_outside_named: 5
---
# Opus gate — seat run pb3arb2, task P3Arb — REJECTED

## Summary

Three of the four contract items are met exactly, and the headline defect is
gone: the record test now asserts `48 rej, 45 plan (vac 15, miss 16, under 8,
fact 6)` over a byte-identical frozen copy of the 48-row seed, `evidence-unit`
is green on the 57-row tree and stays green when I appended a 58th ledger row,
and no scratch row is left behind. Every check I ran is green.

Item 3 is not. The structural guard
`test_no_literal_record_count_against_live_ledger`
(`tests/evidence/test_tasks.py:2692`) does not implement the contract's rule
("grep the test file for the two spellings and assert every hit sits in a
function whose fixture is the frozen seed"). It implements the inverse: it
looks for functions whose body contains the *identifier* `LIVE_LEDGER` and
then checks those for a literal. Consequence, proven by running it: **main's
own defective test — the exact code this task exists to eradicate — passes the
guard.** `test_brief_record_line_over_seeded_ledger` at c168505 reads the live
ledger through an inline path (`seed = HERE.parents[2] / "docs" / "ledger" /
"plan-defects.toml"`) and asserts `"56 rej, 51 plan (…)"`; it never spells
`LIVE_LEDGER`, so the guard is green on it. The plan's Step 1 required exactly
the opposite ("the structural test (red: the live literal exists)"). A guard
that is green on the code it was written to forbid is a named mutant surviving
in the only form the defect has ever actually taken — twice, at 9b20d32 and
4f7f3ae. That is the MAJOR.

Secondary, and the plan's own fault: Step 4's "P3Ar's 42 kills still die"
contradicts contract items 1–2. P3Ar's named mutants M11 and M11b mutate rows
of the LIVE `docs/ledger/plan-defects.toml`; item 1 forbids the record test
from opening that file and item 2 pins the live line to shape plus `rej >= 48`,
so a class flip there is by construction unobservable. I applied both: 15 rows
flipped and 1 row flipped, suite green in each case. The mutants' *intent*
transfers cleanly to the frozen fixture (the same flip on
`plan-defects-seed.toml` is KILLED), so this is a plan wrong-fact, not an
implementer defect — but it means the Step-4 acceptance sentence is not
satisfiable as written and should be reworded in the next round.

## The frozen seed

Byte-identical, confirmed two ways:

```
$ git show 3937d98:docs/ledger/plan-defects.toml | cmp - tests/evidence/fixtures/ledger/plan-defects-seed.toml && echo IDENTICAL
IDENTICAL
$ git show 3937d98:docs/ledger/plan-defects.toml | sha256sum
6b2f745d14be98c09071af1914673f47603f05aef1ddfcf4228c76ae4117ed34  -
$ sha256sum tests/evidence/fixtures/ledger/plan-defects-seed.toml
6b2f745d14be98c09071af1914673f47603f05aef1ddfcf4228c76ae4117ed34  …/plan-defects-seed.toml
$ grep -c '^\[\[rejection\]\]' tests/evidence/fixtures/ledger/plan-defects-seed.toml
48
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml
57
```

The path is traced and clean. `tests/evidence/test_tasks.py:2381` defines
`FROZEN_SEED = HERE.parent / "fixtures" / "ledger" / "plan-defects-seed.toml"`
(`HERE` is `pathlib.Path(__file__).resolve()`, line 12 — the file itself, so
`HERE.parent` is `tests/evidence/`). `test_brief_record_line_over_seeded_ledger`
writes `FROZEN_SEED.read_bytes()` into its tmp repo (line 2651) and asserts the
short form at line 2669 with `today=datetime.date(2026, 9, 6)` (line 2668):

```
    assert "48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)" in line
```

The live path `docs/ledger/plan-defects.toml` appears in the record tests only
as `LIVE_LEDGER` (line 2382), used solely by the shape test (line 2682). No
record test pins a live count. Removing the fixture makes the frozen test red
on the missing file, as the plan's Step 1 requires:

```
E  FileNotFoundError: [Errno 2] No such file or directory: '…/tests/evidence/fixtures/ledger/plan-defects-seed.toml'
FAILED tests/evidence/test_tasks.py::test_brief_record_line_over_seeded_ledger
1 failed, 174 deselected in 0.18s
```

## The scratch-row proof

Done by me, in the clone. I appended a 58th row for a review that exists and
is REJECTED without a front-matter block (so no APPROVED contradiction):

```
[[rejection]]
review = "docs/reviews/2026-09-05-opus-review-cr12-CR2b.md"
run = "cr12"
key = "CR2b"
date = 2026-09-05
plan_defect = "vacuous"
```

```
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml
58
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check ; echo EXIT=$?
EXIT=0
$ nix develop -c pytest tests/evidence -q | tail -1
175 passed in 4.49s
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link
building '/nix/store/g1wxxpdvi0ch1sl99xmarxqqqk0prajk-evidence-unit.drv'...
evidence-unit> 175 passed in 4.47s
EXIT=0
```

Green with the row. The same check on the untouched 57-row tree:

```
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild
checking outputs of '/nix/store/ndlhwlg9z9q0dbxz3slraikxhxfb1qig-evidence-unit.drv'...
evidence-unit> 175 passed in 4.49s
EXIT=0
```

The row was then reverted; the branch's ledger is byte-identical to main's
(`git diff c168505..HEAD -- docs/ledger` is empty, and the working tree is
clean at 57 rows after every experiment below).

The item-1 mutation — the frozen test pointed at the live ledger — dies on the
57-row tree:

```
>       assert "48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)" in line
E       AssertionError: assert '48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)' in '**Record (7 d):** 57 rej, 52 plan (vac 15, miss 20, under 9, fact 8)'
tests/evidence/test_tasks.py:2669: AssertionError
```

and on the 58-row tree it takes the structural guard down with it (two
failures), which is the right coupling.

## The shape and structural tests

`test_live_record_line_shape_only` (line 2672) copies `LIVE_LEDGER.read_bytes()`
into a tmp repo, renders the brief at `today=2026-09-06`, and asserts

```python
RECORD_SHAPE = re.compile(
    r"^\*\*Record \(7 d\):\*\* ([0-9]+) rej, [0-9]+ plan "
    r"\(vac [0-9]+, miss [0-9]+, under [0-9]+, fact [0-9]+\)$"
)
…
    m = RECORD_SHAPE.match(line)
    assert m is not None, f"Record line does not match shape: {line!r}"
    assert RECORD_SHAPE.match("**Record: unavailable**") is None
    assert int(m.group(1)) >= 48
```

Contract item 2's regex, the `rej >= 48` floor and the negative case are all
present. Loosening `RECORD_SHAPE` to `(.*)` dies, and it dies on the negative
case, exactly as the contract names:

```
>       assert RECORD_SHAPE.match("**Record: unavailable**") is None
E       AssertionError: assert <re.Match object; span=(0, 23), match='**Record: unavailable**'> is None
tests/evidence/test_tasks.py:2684: AssertionError
```

The sandbox has what the test needs: `flake.nix:1136-1139` copies
`${self}/tests/evidence` (which carries the new `fixtures/ledger/` directory)
and `${self}/docs/ledger`, and `HERE.parents[2]` inside the sandbox is
`/build`, where both live. That is why **nothing was owed in `flake.nix`** —
confirmed by the green `evidence-unit` builds above, not by reading alone.

Two notes on the shape test, neither a finding: freezing `today` at 2026-09-06
rather than the real today is the right call (a sliding window would eventually
empty and drive `rej` below 48 by the calendar alone); the cost is that the
`>= 48` floor is effectively pinned to today's in-window set and can only bind
if rows are deleted.

The structural guard (line 2692) is where the contract is missed:

```python
    literal = re.compile(r"[0-9]+\s*rej(?:ection)?s?\b")
    bad = []
    for name, body in _test_function_bodies().items():
        if name == "test_no_literal_record_count_against_live_ledger":
            continue
        if "LIVE_LEDGER" in body and literal.search(body):
            bad.append(name)
    assert not bad, f"literal record counts over the live ledger in: {bad}"
```

Both spellings are covered (`assert "57 rej" in line` and
`assert "57 rejections" not in line` each make it fire), and the named mutant
in the seat's own spelling dies:

```
E       AssertionError: literal record counts over the live ledger in: ['test_live_record_line_shape_only']
FAILED tests/evidence/test_tasks.py::test_no_literal_record_count_against_live_ledger
```

But the predicate is `"LIVE_LEDGER" in body`, not "the function's fixture is
the frozen seed". Any test that reaches the live ledger by any other spelling
is invisible to it. See Findings.

## Tests and mutants

175 tests pass (was 172 on main plus the three new ones; main's suite is red).
Fourteen mutants applied and reverted; nine die, five survive.

| # | mutant | result |
|---|---|---|
| A1 | the frozen test's fixture path → `LIVE_LEDGER` (57-row and 58-row trees) | KILLED |
| A2 | `RECORD_SHAPE` loosened to `(.*)` | KILLED — the negative case, line 2684 |
| A3 | `assert "57 rej" in line` added to the shape test | KILLED |
| A4 | `assert "57 rejections" not in line` added to the shape test | KILLED |
| A5 | the frozen fixture file removed | KILLED — `FileNotFoundError` |
| A6 | one row's class flipped in the FROZEN fixture (M11b transferred) | KILLED — `vac 14, miss 17` |
| A7 | `plan_defect_record`: `start <= date` → `start < date` (M9) | KILLED — 3 failures |
| A8 | `plan_defect_record`: the block/row dedup removed (M10) | KILLED — `test_brief_record_dedups_ledger_row_with_block` |
| A9 | `plan_defect_record`: the verdict skip inverted to `== "APPROVED"` (P5) | KILLED — `test_record_out_of_reach_h1_counts_by_row_only` |
| B1 | the shape test's `LIVE_LEDGER.read_bytes()` replaced by the inline path `(HERE.parents[2] / "docs" / "ledger" / "plan-defects.toml").read_bytes()` **plus** `assert "57 rej" in line` | **SURVIVED — 175 passed** |
| B2 | main's `test_brief_record_line_over_seeded_ledger` (inline live path + `assert "56 rej, …"`) placed in the file alongside the branch's guard | **SURVIVED — the guard passed; only the live-count assertion itself failed** |
| B3 | a new file `tests/evidence/test_scratch_live.py` asserting a literal live count | **SURVIVED — 176 passed** |
| B4 | one row's class flipped in the LIVE ledger (M11b as named) | **SURVIVED — 175 passed** |
| B5 | all 15 `vacuous` rows flipped in the LIVE ledger (M11 as named) | **SURVIVED — 175 passed** |

B1/B2/B3 are one root cause: the guard's `"LIVE_LEDGER" in body` predicate.
B2 is the decisive one — it is the historical defect verbatim.

B4/B5 are forced by contract items 1–2 and are a plan contradiction, not an
implementer miss (A6 shows the intent transferred to the fixture).

I did not re-run all 42 of P3Ar's kills individually; `pkgs/evidence/tasks.py`,
`docs/ledger/plan-defects.toml` and `tools/session-start.sh` are byte-unchanged
on this branch and only one existing test's fixture changed, so the three
record-path mutants most exposed by that change (M9, M10, P5) were re-applied
and all three still die, and the two that the change does expose (M11, M11b)
are reported above.

## Checks

All from inside the fresh clone
`…/scratchpad/gate-pb3arb2-P3Arb` (branch `task/P3Arb`, head db1c375, base
c168505).

```
$ nix develop -c ruff check pkgs/evidence tests/evidence
All checks passed!
$ nix develop -c ruff format --check pkgs/evidence tests/evidence
49 files already formatted
$ nix develop -c pytest tests/evidence -q
175 passed in 4.62s
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild
evidence-unit> 175 passed in 4.49s        EXIT=0
$ nix build .#checks.x86_64-linux.lint -L --no-link
EXIT=0
$ nix develop -c githooks/pre-commit
render.test.mjs: all assertions passed    EXIT=0
$ nix develop -c python3 pkgs/evidence/repomap.py --root . write && git diff --exit-code docs/MAP.md
MAP-CLEAN
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check ; echo EXIT=$?
EXIT=0        (silent)
$ git diff c168505..HEAD -- docs/ledger
(empty)
$ git status --porcelain
(clean)
```

Commit convention: exactly one commit (`git rev-list --count c168505..HEAD` →
`1`); the subject is byte-identical to P3A's (`cmp` against the plan's
`commit subject` line passes); `Generated-By:` and `Co-Authored-By:` follow a
blank line; the three touched files are `tests/evidence/test_tasks.py` and
`tests/evidence/fixtures/ledger/plan-defects-seed.toml` (both in `touches`)
plus `docs/MAP.md` (by rule); no board commit.

## Red before green

```
$ git checkout c168505 && nix build .#checks.x86_64-linux.evidence-unit -L --no-link
> assert "56 rej, 51 plan (vac 15, miss 19, under 9, fact 8)" in line
E AssertionError: assert '56 rej, 51 plan (vac 15, miss 19, under 9, fact 8)' in '**Record (7 d):** 57 rej, 52 plan (vac 15, miss 20, under 9, fact 8)'
FAILED tests/evidence/test_tasks.py::test_brief_record_line_over_seeded_ledger
1 failed, 172 passed in 4.54s
EXIT=1
```

main at c168505 is RED, as the section says. The branch is green (175 passed,
above). The frozen test is red with the fixture absent (quoted above).

The structural test, however, is **not** red on main. I rebuilt the Step-1
scenario exactly: main's `tests/evidence/test_tasks.py` at c168505 with the
branch's `LIVE_LEDGER` constant, `_test_function_bodies` helper and
`test_no_literal_record_count_against_live_ledger` appended verbatim:

```
$ nix develop -c pytest tests/evidence/test_tasks.py -q -k "no_literal or record_line_over_seeded"
> assert "56 rej, 51 plan (vac 15, miss 19, under 9, fact 8)" in line
E AssertionError: …
FAILED tests/evidence/test_tasks.py::test_brief_record_line_over_seeded_ledger
1 failed, 1 passed, 117 deselected in 0.18s
```

`1 passed` is `test_no_literal_record_count_against_live_ledger`. The guard is
green on the very defect it was written to forbid. Step 1's "the structural
test (red: the live literal exists)" was never demonstrated, and cannot be
with this implementation.

## Findings

**MAJOR — the structural guard is vacuous against the defect it names**
(`tests/evidence/test_tasks.py:2703`). The predicate is

```python
        if "LIVE_LEDGER" in body and literal.search(body):
```

Contract item 3 says: "grep the test file for the two spellings and assert
every hit sits in a function whose fixture is the frozen seed." The
implementation runs the other direction — it enumerates functions that name the
constant, then looks for a literal — so a live-reading test that does not spell
`LIVE_LEDGER` is never examined. Evidence, three ways: (B2) main's own
`test_brief_record_line_over_seeded_ledger` at c168505 (`seed = HERE.parents[2]
/ "docs" / "ledger" / "plan-defects.toml"`, `assert "56 rej, …"`) passes the
guard; (B1) the same evasion inside the branch — swap `LIVE_LEDGER.read_bytes()`
for the inline path in the shape test and add `assert "57 rej" in line` — leaves
175 tests green; (B3) a new file under `tests/evidence/` with a literal live
assertion leaves 176 green. Fix: implement the contracted direction — scan every
`test_*.py` under `HERE.parent`, find every `[0-9]+\s*rej(?:ection)?s?\b` hit,
and assert each hit's enclosing function reads the frozen seed (`FROZEN_SEED`,
or a fixture path under `fixtures/`) and never the string
`docs/ledger/plan-defects.toml` / `parents[2]`-rooted ledger path.

**MINOR — the guard scans one file, not `tests/evidence/`**
(`tests/evidence/test_tasks.py:2426`, `_test_function_bodies` reads only
`HERE`). Contract item 3's leading clause is "no test **under
`tests/evidence/`**"; its parenthetical says "the test file", which is what was
built. Today nothing else under `tests/evidence/` touches the ledger (grep:
`plan-defects.toml` appears in no other test file), so the gap is latent — but
B3 shows it is real. Folded into the MAJOR's fix (glob `HERE.parent`).

**MINOR — P3Ar's M11/M11b no longer die, and cannot** (plan, §P3Arb Step 4
against items 1–2). Flipping one live ledger row's class, or all fifteen
`vacuous` rows, leaves the suite green. Contract item 1 forbids the record test
from opening the live ledger and item 2 pins only shape and a floor, so no test
can observe a live class flip; `tasks.py check` does not compare a row's class
to its review's block, so it does not catch it either. The mutants' intent is
preserved on the frozen fixture (A6 kills). Fix in the next round's wording:
Step 4 should read "P3Ar's 42 kills still die, except M11/M11b, which transfer
to the frozen fixture", and the plan should say so rather than leaving a seat to
discover it at the gate.

**MINOR — the commit body does not paste the two `evidence-unit` runs.** The
convention for this task is "the body pastes both evidence-unit runs"; the body
carries a four-sentence prose summary only. Subject, trailers, commit count and
touched-file scope are all correct, so this is a report-completeness miss, not a
malformed commit.

**MINOR — `docs/runbooks/evidence.md` was correctly left untouched.** Its
"The plan-defect ledger" section (lines 77-93) documents the ledger's schema and
the `Record (7 d)` line's semantics; it never claims the live count is asserted
by a test, so no sentence went stale. Recorded here only because the plan's
`touches` named the file and a reader will ask.

## Verdict

**REJECTED.** One MAJOR: contract item 3's structural test does not detect the
defect class it exists to forbid — its named mutant survives in the exact form
the bug took twice on main, and the plan's Step-1 red ("the structural test
(red: the live literal exists)") is unattainable with this implementation, which
is why the seat could not have shown it red. Items 1, 2 and 4 are met exactly
and every check is green, so the fix round is small: replace the
`"LIVE_LEDGER" in body` predicate with the contracted literal-first scan over
every `test_*.py` under `tests/evidence/`, and prove it red against
`git show c168505:tests/evidence/test_tasks.py`. The next plan round should also
correct Step 4's mutant sentence (M11/M11b transfer to the fixture) and require
the commit body to carry both `evidence-unit` pastes.
