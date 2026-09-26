---
plan_defect: wrong-fact
plan_defect_secondary: implementer
mutants_total: 32
mutants_killed: 29
mutants_outside_named: 8
---
# Opus gate — seat run pb3a, task P3Ab — REJECTED

## Summary

One commit `20de584` on `e4e0169`, 8 files (+298/−39), subject byte-identical to
the plan's, both trailers, every file inside `touches` but `docs/MAP.md`, which
regenerates. Contract items 1–5 are met exactly: an APPROVED review's in-window
block never counts (`0 rej` where P3A printed `1 rej`); a block not immediately
followed by the H1 is now an error and the verdict is still read within three
lines, so the review is never silently absent from the graph; the three
`mutants_*` keys parse; `--today` works as a global and as a `brief` option; all
five previously-untested arms have a test, and each one's removal kills it. All
24 named mutants (P3Ab's ten, P3A's fourteen) die; 5 of my 8 extra mutants die.
Every check is green.

Contract item 6 is not met, and cannot be met by the means the plan names. The
brief part is **1,097 chars of its 1,200 cap — 103 chars of headroom**, not the
"at least 200" the contract requires. The shortening saved 41 chars (109 → 68)
while the brief itself grew 28 chars since P3A's measurement; deleting the
Record line *entirely* would leave 1,028 chars and 172 of headroom, so no
edit to that line reaches 200. Nothing in the branch raises the cap
(`tools/session-start.sh` is untouched), no test guards the headroom, and the
commit body carries neither the measurement the contract ordered pasted nor the
live Record line. MAJOR 1 and MAJOR 2 below.

## The record

Fixture repos under the scratch dir, driven through the clone's own `tasks.py`
(`render_brief` + `check`), `front_matter_from = 2026-09-07`,
`--today 2026-09-12`.

| # | fixture | expected | observed |
|---|---|---|---|
| 1a | in-window APPROVED file, block `plan_defect: none` | not counted | `**Record (7 d):** 0 rej, 0 plan (vac 0, miss 0, under 0, fact 0)`, `check` silent |
| 1b | same file, H1 REJECTED, `plan_defect: vacuous` | 1 rejection, 1 plan-caused | `1 rej, 1 plan (vac 1, miss 0, under 0, fact 0)` |
| 1c | ledger row (`missing-case`) AND in-window REJECTED block (`vacuous`), same file | counted once, the block wins | `1 rej, 1 plan (vac 1, miss 0, under 0, fact 0)` |
| 1d | ledger row (`missing-case`) AND in-window **APPROVED** block (`none`), same file | — | `1 rej, 1 plan (vac 0, miss 1, under 0, fact 0)`: the ledger row counts, the block is skipped before the dedup and so never shadows it, and no error names the contradiction |

1d is the only behaviour the contract leaves open, and the implementation
resolves it the safe way: an APPROVED block cannot erase a rejection the
orchestrator recorded. `pkgs/evidence/tasks.py:1082–1084` skips a non-REJECTED
block *before* `block_primary` is populated, so the row is never shadowed.

Ledger arithmetic, by hand against `docs/ledger/plan-defects.toml` with
`tomllib` (window `2026-08-30 .. 2026-09-06`):

```
live   rows: 54  in-window: 54  caused: 50
       {'missing-case': 19, 'wrong-fact': 7, 'underspecified': 9,
        'vacuous': 15, 'process': 1, 'implementer': 3}
branch rows: 53  in-window: 53  caused: 49  (miss 18 — main gained one row after e4e0169)
```

The branch's seeded-ledger test asserts `53 rej, 49 plan (vac 15, miss 18,
under 9, fact 7)` against its own ledger — right for its base, and it moves with
the ledger (a one-row class flip kills it, mutant M11b below).

## The block shape

`_split_front_matter` now returns a 4-tuple with a two-line lookahead
(`tasks.py:236`), `_review_h1` (`:251`) matches the H1 over `first` then those
two, and `check` requires the H1 on the very next line (`:1001`).

| shape | `read_reviews` | `check` |
|---|---|---|
| blank line before the H1 (REJECTED / `none`) | `{'W1': 'REJECTED'}` | **both** errors: `… the H1 must follow the block` and `… a rejection names its cause` |
| prose between | `{'W1': 'REJECTED'}` | both errors |
| a second block between | `{}` | `… the H1 must follow the block` |
| H1 four lines below the block | `{}` | `… the H1 must follow the block` |
| CRLF, H1 immediately after | `{'W1': 'REJECTED'}` | only `a rejection names its cause` (no shape error) |
| CRLF with a blank line | `{'W1': 'REJECTED'}` | both errors |
| block, no H1 at all | `{}` | `… the H1 must follow the block` |

So P3A's minor 4 is closed: the blank-line file is no longer silent, and its
verdict is back in the graph. Where the H1 falls further than three lines away
(the second-block and four-lines cases) the file *is* absent from the graph, but
never silently — the shape error fires. That matches the contract, which scopes
`read_reviews`'s tolerance to three lines.

## The arms

All five, by hand on fixture repos:

```
missing plan_defect  : ['tasks: review 2026-09-08-opus-review-x1-K1.md: plan_defect missing']
secondary maybe      : ['… plan_defect_secondary maybe not in none | vacuous | missing-case | underspecified | wrong-fact | implementer | process']
mode-000 ledger      : check -> ['tasks: plan-defects: …/plan-defects.toml unreadable']   (exactly one error)
                       brief -> ['**Record: unavailable**']
_today_utc()         : 2026-09-06  == datetime.now(timezone.utc).date()
non-opus name        : check errs [] ; record 0 rej
```

The UTC test pins the clock rather than merely running: it substitutes a
`datetime.datetime` subclass whose `now()` returns 2026-09-06 and asserts a row
dated exactly seven days back is inside the window. Freezing `_today_utc` to
1970-01-01 (P3A's surviving mutant E4) kills it.

One asymmetry to record: `2026-09-08-review-notnamed.md` is ignored by the check
rule *and* by the record (both glob `*opus-review*.md`), but **not** by
`read_reviews`, which globs `*.md` — `read_reviews` returned
`{'W1': 'REJECTED'}` for it. So such a file still supplies a verdict to the task
graph while carrying an unvalidated block. Contracted as written; worth knowing.

Integer parsing (`tasks.py:1003–1011`), each value by hand:

```
'banana' -> mutants_total must be an integer      '0'     -> ok
'-1'     -> mutants_total must be an integer      '19'    -> ok
'3.0'    -> mutants_total must be an integer      '99999999999999999999999999' -> ok
''       -> mutants_total must be an integer      '+5'    -> ok
'0x10'   -> mutants_total must be an integer      '1_0'   -> ok (Python reads 10)
key absent -> silent                              '٣'     -> ok (Python reads 3)
all three keys bad -> three errors, one per key
```

## Live line and the hook budget

The clone's `tasks.py` over the live tree (read-only), both `--today` forms:

```
$ tasks.py --root /home/dalhaka/nixos-agent-env brief --today 2026-09-06 | grep Record
**Record (7 d):** 54 rej, 50 plan (vac 15, miss 19, under 9, fact 7)
$ tasks.py --root /home/dalhaka/nixos-agent-env --today 2026-09-06 brief | grep Record
**Record (7 d):** 54 rej, 50 plan (vac 15, miss 19, under 9, fact 7)
$ tasks.py --root /home/dalhaka/nixos-agent-env check     → (silent) exit=0
```

Byte-exact against my own `tomllib` tally above. Both forms agree; given both
with different values, the `brief` option wins (it is parsed last) — global
`2026-09-12` + sub `2026-10-30` printed `0 rej`, the reverse printed `1 rej`.
A bad value on the global exits 2 with
`tasks: error: argument --today: invalid fromisoformat value: '2026-13-99'`.

The budget, from the clone:

```
$ bash tools/session-start.sh </dev/null | wc -c
7676                       (7,542 chars, cap 8,000 — fine)
$ brief part, as cap_part measures it (${#brief}, tools/session-start.sh:186, cap 1200)
1097 chars (1103 bytes)  →  HEADROOM 103 chars / 97 bytes
   same brief with P3A's long line: 1138 chars (headroom 62)
   record line: old 109 chars, new 68 — the shortening saves 41
   brief with NO record line at all: 1028 chars → headroom 172
```

The runbooks say the right things: `docs/runbooks/evidence.md` documents the new
line, that an APPROVED block never counts, the shape rule, the integer rule, and
that the line is display only; `docs/runbooks/session.md` says the line is
abbreviated to keep the brief inside its budget. Neither states a headroom
figure, and no test asserts one.

P10 has **not** landed — it is `3a7994b` on branch `task/P10` at
`/home/dalhaka/factory/ws/pa10/P10`, on top of `3937d98`. It reads the ledger:
`pkgs/evidence/report.py:126` calls `tasks.plan_defect_record([{"path": repo}],
today_d)` and never parses the rendered line. Contract item 6's P10 clause
holds. See minor 4 for the signature it will collide with.

## Tests and mutants

Ten new tests (168 pass, was 158), three new fixtures, one for each of the three
new shapes. Thirty-two mutants applied to `pkgs/evidence/tasks.py` or
`docs/ledger/plan-defects.toml`, run, reverted. **All 24 named die.**

P3Ab's ten (the plan's six items; item 5 counts as five arms):

| # | mutant | result |
|---|---|---|
| N1 | the verdict test dropped (`:1082–1084`) | KILLED — `test_record_ignores_approved_block` |
| N2 | the shape check dropped (`:1000–1001`) | KILLED — `test_check_shape_h1_must_follow_block` |
| N3 | the int parse dropped (`:1002–1011`) | KILLED — `test_check_rejects_non_integer_mutant_counts` |
| N4 | the global `--today` dropped (`:1603`) | KILLED — `test_main_accepts_today_global` (`… invalid choice: '2026-09-06'`) |
| N5a | `plan_defect missing` arm removed | KILLED — `test_check_plan_defect_missing` |
| N5b | secondary-outside-enum arm removed | KILLED — `test_check_secondary_outside_enum` |
| N5c | unreadable ledger degrades to `(None, [])` | KILLED — `test_unreadable_ledger_errors_and_record_unavailable` |
| N5d | `_today_utc` frozen to 1970-01-01 | KILLED — `test_record_default_today_is_utc` |
| N5e | the `*opus-review*.md` glob widened to `*.md` | KILLED — `test_check_ignores_non_opus_review` |
| N6 | the long record line restored (`:1434`) | KILLED — `test_brief_record_line_counts_and_classifies` |

P3A's fourteen, all still dead: M1 `_split_front_matter` returns `lines[0]`; M2
`date > fmf`; M3 block validation skipped on early files; M4 `"maybe"` in the
enum; M5 the REJECTED/`none` arm unreachable; M6 the secondary-equality arm
unreachable; M7 secondaries also counted; M8 ledger rows with a secondary
skipped; M9 `start < date`; M10 the dedup removed; M11 all fifteen `vacuous`
seed rows → `underspecified`; M11b one seed row flipped; E1 the `no such review`
arm removed; E5 `_review_defect_errors` unwired.

Eight of my own, outside the named list; five die, three survive:

| # | mutant | result |
|---|---|---|
| X1 | the lookahead removed from `_review_h1` | KILLED |
| X2 | the shape check date-gated to `date > fmf` | KILLED |
| X3 | `n < 0` → `n < -1` | KILLED |
| X6 | `PLAN_DEFECT_SHORT` `vac`↔`miss` swapped | KILLED (5 failed) |
| X8 | the `brief --today` option dropped | KILLED |
| X4 | negatives accepted, parse errors still refused (`-1` passes) | SURVIVED |
| X5 | the verdict test → `if m is not None and m["verdict"] == "APPROVED"` (a block with no H1 counts) | SURVIVED |
| X7 | the lookahead widened from three lines to six | SURVIVED |

The three survivors are contracted clauses with no test: "non-**negative**"
(only `banana` is tested, never `-1`), the `m is None` half of the verdict test,
and the "within the next three lines" width. Minor 3.

`mutants_total: 32, mutants_killed: 29, mutants_outside_named: 8`.

## Checks

All from inside the fresh clone.

```
nix develop -c ruff check pkgs/evidence tests/evidence          All checks passed!
nix develop -c ruff format --check pkgs/evidence tests/evidence 46 files already formatted
nix develop -c pytest tests/evidence -q                         168 passed
nix build .#checks.x86_64-linux.evidence-unit -L --no-link      168 passed
nix build .#checks.x86_64-linux.lint -L --no-link --rebuild     exit 0 (0 warnings, 0 errors)
nix build .#checks.x86_64-linux.unit -L --no-link               ok 361 …
nix develop -c githooks/pre-commit                              exit 0
repomap.py --root . write ; git diff --exit-code docs/MAP.md    MAP REPRODUCES
tasks.py --root . check                                         (silent) exit 0
claims.py validate docs/ledger/claims.toml --today 2026-09-06   (silent) exit 0
git status --porcelain after all of it                          clean
```

`lint --rebuild` runs the check rule over the real `docs/reviews/`, which now
holds three block-carrying files (`pa6-P2`, `pa7-P3A`, `pb11-P11b`, all dated
2026-09-06): green, and the new shape rule fires on none of them.

The clone's own `tasks.py check` over the live tree carrying THIS review file
(a copy of the tree could not be made — the session's plan-file guard refuses a
`git clone` of the repo into the scratch dir, so the run is read-only against
the live tree, where the file already sits untracked):

```
$ tasks.py --root /home/dalhaka/nixos-agent-env check
(no output)
exit=0
$ _read_review(…-pb3a-P3Ab.md)
block {'plan_defect': 'wrong-fact', 'plan_defect_secondary': 'implementer',
       'mutants_total': '32', 'mutants_killed': '29', 'mutants_outside_named': '8'}
first '# Opus gate — seat run pb3a, task P3Ab — REJECTED'   (H1 immediately after the block)
errors naming this file: []
```

Commit convention: one commit; subject byte-identical to the plan's P3A/P3Ab
subject (195 bytes, compared programmatically); `Generated-By` and
`Co-Authored-By` both present; no board commit; every file inside `touches`
except `docs/MAP.md`, which regenerates byte-identically. The body is the breach
— see MAJOR 2.

## Red before green

`git -C /home/dalhaka/factory/ws/pa7/P3A show task/P3A:pkgs/evidence/tasks.py`
(byte-identical to `e4e0169:pkgs/evidence/tasks.py`, `cmp` clean) under this
branch's tests:

```
11 failed, 157 passed in 4.90s
FAILED …::test_brief_record_line_counts_and_classifies
FAILED …::test_record_window_is_inclusive
FAILED …::test_brief_record_dedups_ledger_row_with_block
FAILED …::test_brief_record_line_over_seeded_ledger
FAILED …::test_main_brief_accepts_today_option
FAILED …::test_main_accepts_today_global
FAILED …::test_record_ignores_approved_block
FAILED …::test_check_shape_h1_must_follow_block
FAILED …::test_read_reviews_finds_verdict_within_three_lines
FAILED …::test_check_rejects_non_integer_mutant_counts
FAILED …::test_record_default_today_is_utc
```

Restored: `168 passed`. The APPROVED-block count, the blank-line shape, the
`banana` parse, the global `--today` and the short line are all red on P3A, as
the plan asked. Four of the ten new tests (`test_check_plan_defect_missing`,
`test_check_secondary_outside_enum`,
`test_unreadable_ledger_errors_and_record_unavailable`,
`test_check_ignores_non_opus_review`) pass on P3A by design — they are the
coverage-only arms of item 5, whose contract is "the arm removed → the test
fails", which N5a/N5b/N5c/N5e verify.

## Findings

### MAJOR 1 — the brief part keeps 103 chars of headroom, not the contracted 200, and the contract's remedy cannot reach 200

`tools/session-start.sh:186` caps the BRIEF part at 1,200. Measured from the
clone, exactly as `cap_part` measures it:

```
brief part            1097 chars (1103 bytes)  →  headroom 103
same brief, long line 1138 chars               →  headroom  62
record line           old 109 chars → new 68   →  saving 41
brief with the record line deleted outright    →  1028 chars, headroom 172
```

Contract item 6: "The record line shortens to … so the brief part keeps at least
200 chars of headroom under its cap on this host (measure and paste …)". The
shortening is real and correctly implemented (`tasks.py:1431–1434`), but the
target is arithmetically out of reach through that line: the whole line is 68
chars, and removing it leaves 172 of headroom. Headroom could only come from
raising `SESSION_START_CAP_BRIEF`'s 1,200 default (the branch does not touch
`tools/session-start.sh`, and it is not in `touches`) or from shrinking other
brief content. Nothing in the branch, and no test anywhere, guards the figure,
so the budget class P4 was rejected on is still open: one more repo row or a
longer next-wave label truncates the brief.

### MAJOR 2 — the commit body carries neither the measurement nor the live Record line

Step 4 of the contract orders the numbers measured and pasted, and the gate's
commit convention requires the body to carry the live Record line and the hook
measurement. `20de584`'s body says only "the record line abbreviates to `N rej,
M plan (vac a, miss b, under c, fact d)` to preserve the brief part's budget
headroom" — no figure, no live line, and no note that the 200-char target was
missed. Had the implementer run the measurement the contract ordered, MAJOR 1
would have surfaced in the seat rather than in the gate. (P3A took minor 7 for a
body claim it could not reproduce; this is the same class, one round on.)

### Minors

1. **`int()` is more permissive than "integer".** `tasks.py:1006` accepts
   `+5`, `1_0` (read as 10) and the Arabic-Indic digit `٣` (read as 3) as
   `mutants_total`. Harmless today; a stricter `str.isdigit()` guard would match
   the runbook's wording.

2. **A ledger row and an APPROVED block can contradict each other in silence.**
   Fixture 1d: the ledger says the review was a rejection, the review's own H1
   says APPROVED, and `check` reports nothing. The row wins, which is the safe
   resolution, but nothing flags the disagreement for the orchestrator.

3. **Three contracted clauses ship untested** (the survivors X4, X5, X7): the
   "non-negative" half of the integer rule (only `banana` is tested, never
   `-1`), the `m is None` half of the record's verdict test (a block whose H1 is
   out of reach counts as a rejection if that half is dropped), and the
   three-line width of the lookahead (widening it to six lines passes every
   test). Same class as P3A's minor 3, one layer down.

4. **`_read_review`'s signature change will break P10 on integration.**
   `pkgs/evidence/tasks.py:241` now returns a 4-tuple;
   `/home/dalhaka/factory/ws/pa10/P10/pkgs/evidence/report.py:72` unpacks three:
   `_, block, _ = tasks._read_review(path)`. P10 is unlanded (`3a7994b` on
   `task/P10`, based on `3937d98`), so no check is red today, but whichever of
   the two lands second needs the one-line fix.

5. **`read_reviews` still reads `*.md` while the block rule reads
   `*opus-review*.md`.** A `…-review-….md` file without "opus" contributes a
   verdict to the task graph while its block is never validated. Contracted, and
   now tested on the check side only.

## Verdict

**REJECTED.** Contract items 1–5 are met exactly and every named mutant dies;
item 6's headroom requirement is missed (103 chars, not 200) and cannot be met
by shortening the line at all, which the commit body's missing measurement would
have exposed in the seat. Re-plan item 6 with a means that can reach the target
(raise `SESSION_START_CAP_BRIEF`'s default, or shrink another part of the brief)
and a test that pins the figure; carry the five minors into the same round. The
rest of the branch is sound and should be kept as is.
