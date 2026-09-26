---
plan_defect: none
mutants_total: 44
mutants_killed: 42
mutants_outside_named: 10
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run pb3ar, task P3Ar — APPROVED

## Summary

One commit `83d3dfd` on `110ba13`, 13 files (+508/−71), subject byte-identical
to the plan's (195 bytes, compared programmatically), both trailers, every file
inside `touches` but `docs/MAP.md`, which regenerates byte-identically. The
re-plan's premise holds up under measurement: the headroom now comes from the
caps, not from the line. `SESSION_START_CAP_BRIEF` is 1,400 and
`SESSION_START_CAP_BOARD` 2,300, the five-cap sum is still exactly 7,300, P4b's
structural sum test is byte-unchanged and green, and the worst case recomputes
to **7,703 chars of the 8,000 total** — 297 to spare. On this host the hook
prints 7,391 bytes / 7,263 chars with the pointer last, and the brief part
measures 1,017 chars against its 1,400 cap: **383 chars of headroom**, well
past the contracted 250. The seat's own figures (7,466 B / 1,093 chars → 307)
are the same measurement taken while `pb3ar` was itself in flight; both clear
the bar, and unlike P3Ab the seat actually ran the ordered probe and pasted it.

Items 1–5 of P3Ab stand: the `tasks.py` diff against `task/P3Ab` is exactly the
three minors and a docstring, and every one of those items re-verified by hand.
Forty-four mutants applied, run and reverted: all thirty-four named die
(P3Ab's 29, P3Ar's five), and eight of my ten extra. The two survivors are
untested halves of contracted clauses — minors 1 and 2, the same class one
layer down. Every check is green, and both `--today` forms print the live
Record line byte-exact against my own `tomllib` tally.

## The caps and the measurement

`tools/session-start.sh:182,186` — the only two lines the branch changes there:

```
  cap_part BOARD "$board" 2300      (was 2500)
  cap_part BUNDLE "$bundle" 2100
  cap_part BRIEF "$brief" 1400      (was 1200)
  cap_part INFLIGHT "$ritual_text" 1000
  cap_part OPERATOR "$operator_model" 500
                                     sum 7300  (unchanged)
```

The worst case, recomputed from the script rather than trusted (five parts full,
five truncation lines, five blank separators, the operator heading and the
pointer, every string measured):

| item | chars |
|---|---|
| the five caps | 7,300 |
| the five truncation lines (56 + 58 + 56 + 62 + 61) | 293 |
| their newlines + the five blank `echo` lines | 10 |
| `## Operator model (docs/board/operator-model.md)` + `\n` | 49 |
| `Where everything is: docs/runbooks/session.md` + `\n` | 46 |
| the five parts' own newlines | 5 |
| **total** | **7,703** ≤ 8,000 |

`tests/unit/90-session-start.bats:292` (P4b's structural sum test) is
byte-unchanged — it reads the `cap_part … N` literals out of the script and
asserts the sum ≤ `SESSION_START_CAP` − 700 — and green. The all-overflow test
(`:310`) is unchanged in structure (in-flight precondition, ≤ 8,000, pointer
last, every heading present) with only its three literal truncation strings
moved to the new numbers; green. Both fail under a cap regression: raising the
board default by 700 kills them, and so does dropping the total to 7,000
(mutants Y1, Y9 below).

`docs/runbooks/session.md:58–70` lists 2,300 / 2,100 / 1,400 / 1,000 / 500 and
the sum line "= 7,300 chars" — arithmetic correct, table matches the script.

The live probe, from inside the fresh clone (`FACTORY_RUN` unset, stdin
`/dev/null`):

```
$ bash tools/session-start.sh </dev/null | wc -c
7391                     (7,263 chars; cap 8,000)
$ … | tail -n 1
Where everything is: docs/runbooks/session.md
$ brief part, as cap_part measures it (${#brief}, UTF-8 locale)
1017 chars (1022 bytes)  →  HEADROOM 383 chars, cap 1400
```

With the LIVE `docs/OPERATIONS.md` copied over the clone's: byte-identical
output (7,391 B / 7,263 chars, pointer last, four parts truncated) — the board
is cut at 2,300 either way, so the live board changes nothing.

The commit body pastes 7,466 bytes and 1,093 brief chars (307 of headroom). The
delta to my reading is live in-flight state inside the brief: when the seat
measured, `**Running:**` named `P3Ar (pb3ar)` and the rejected-fix-round list
still carried `P3Ab`; today both are `none` / a different list. Δbrief 76 chars
≈ Δtotal 75 bytes. Both readings satisfy the contract; the figure is a moving
one and only the cap, not a test, bounds it (minor 5).

The new guard, `tests/unit/90-session-start.bats:112` — "a brief over its cap
(1400) is cut at the default 1400". Mutant P1 (the brief default left at 1,200):

```
not ok 8 a brief over its cap (1400) is cut at the default 1400
#   `[[ "$output" == *"…brief truncated at 1400 chars (SESSION_START_CAP_BRIEF)"* ]]' failed
```

## Items 1–5 re-verified

`git diff task/P3Ab..HEAD -- pkgs/evidence/tasks.py` is four hunks: the
`_read_review` docstring, the `read_reviews` glob, the integer rule and the
contradiction arm. Nothing in items 1–5 moved. By hand on fixture repos through
the clone's own `check` / `render_brief` / `read_reviews`
(`front_matter_from = 2026-09-07`, `--today 2026-09-12`):

| item | probe | observed |
|---|---|---|
| 1 | in-window APPROVED block, `plan_defect: none` | `0 rej, 0 plan (vac 0, miss 0, under 0, fact 0)`; `check` silent; verdict still in the graph |
| 1 | the same file REJECTED / `vacuous` | `1 rej, 1 plan (vac 1, …)` |
| 2 | blank line before the H1, REJECTED / `none` | both errors — `the H1 must follow the block` **and** `a rejection names its cause`; `read_reviews` still `{'W1': 'REJECTED'}` |
| 2 | prose between block and H1 | identical pair of errors |
| 3 | `mutants_total: banana` | `mutants_total must be an integer` |
| 4 | `--today` global and `brief --today` | both print the same live line (below) |
| 5a | block without `plan_defect` | `plan_defect missing` |
| 5b | `plan_defect_secondary: maybe` | `plan_defect_secondary maybe not in none \| vacuous \| …` |
| 5c | unparsable ledger | exactly one `plan-defects: … unreadable` + `**Record: unavailable**` |
| 5d | `_today_utc()` | `2026-09-06` == `datetime.now(timezone.utc).date()` |
| 5e | `2026-09-07-review-notnamed.md` | no error; not in the record |

The new-test count against `task/P3Ab` is additive: `git diff` of
`tests/evidence/test_tasks.py` shows 152 insertions and 18 deletions, and every
deletion is either a fixture-name rename (`a.md` → `opus-review-a.md`, forced by
the narrowed `read_reviews` glob) or the seeded-ledger figures moving with the
ledger (`53 rej, 49 plan (… miss 18 … fact 7)` → `56 rej, 51 plan (… miss 19 …
fact 8)`). No P3Ab test was removed, weakened or re-scoped. 168 → 173 tests.

## The minors

Item 3, each clause by hand.

**The integer rule** is `re.fullmatch(r"[0-9]+", raw)` at
`pkgs/evidence/tasks.py:1010`:

```
'+5'   -> mutants_total must be an integer      '0'   -> ok
'1_0'  -> mutants_total must be an integer      '12'  -> ok
'٣'    -> mutants_total must be an integer      '99999999999999999999' -> ok
'-1'   -> mutants_total must be an integer
'3.0'  -> mutants_total must be an integer
''     -> mutants_total must be an integer
'0x10' -> mutants_total must be an integer
```

All three of P3Ab's `int()` leaks (`+5`, `1_0`, `٣`) are closed; `-1` and the
empty value are refused.

**The contradiction** (`:1036–1042`). A ledger row plus an APPROVED block on the
same file:

```
errors : ['tasks: review 2026-09-08-opus-review-ap2.md: a ledger row contradicts an APPROVED block']
record : **Record (7 d):** 1 rej, 1 plan (vac 0, miss 1, under 0, fact 0)
```

— i.e. the row still counts and the APPROVED block still never counts (P3Ab's
resolution is untouched); the disagreement is now named instead of silent. A row
plus a **REJECTED** block is silent, as it should be.

**The three clauses.** `-1` refused (above). A block whose H1 is out of reach
plus a ledger row → `the H1 must follow the block` from `check`, no verdict in
the graph, and the record counts the row only (`1 rej … miss 1, vac 0`). The
same shape with no ledger row → `0 rej`. A block-less REJECTED file in the
window plus its row → `no front-matter block (plan_defect is required from
2026-09-07)` and `1 rej … miss 1`, the row alone. The H1 four lines below the
block → `the H1 must follow the block`, `read_reviews` returns `{}`.

**The glob.** `read_reviews` now globs `*opus-review*.md`
(`pkgs/evidence/tasks.py:285`), matching the block rule.
`2026-09-08-review-x.md` carrying `plan_defect: maybe` is invisible to both:
`check` silent, `read_reviews` `{}`, record `0 rej`. Behaviour-neutral on the
real corpus — I diffed `read_reviews` between `110ba13` and HEAD over every repo
`repos.toml` configures:

```
nixos-agent-env  main 127  branch 127  LOST: none
media            main   6  branch   6  LOST: none
gaming / nixos-skill / dsh-harness      0 / 0 / 0, LOST: none
```

**The docstring.** `_read_review` (`:242–247`) names the 4-tuple, each element,
and the unreadable case `(False, {}, "", ())`. P10b has what it needs to adapt.

## Live line

The clone's `tasks.py` over the live tree, read-only, both forms:

```
$ tasks.py --root /home/dalhaka/nixos-agent-env --today 2026-09-06 brief | grep Record
**Record (7 d):** 56 rej, 51 plan (vac 15, miss 19, under 9, fact 8)
$ tasks.py --root /home/dalhaka/nixos-agent-env brief --today 2026-09-06 | grep Record
**Record (7 d):** 56 rej, 51 plan (vac 15, miss 19, under 9, fact 8)
$ tasks.py --root /home/dalhaka/nixos-agent-env check     → (silent) exit=0
```

Byte-identical to the commit body's pasted line. Hand tally with `tomllib`,
window `2026-08-30 .. 2026-09-06`:

```
live   rows 56  in-window 56  caused 51
       {'missing-case': 19, 'wrong-fact': 8, 'underspecified': 9,
        'vacuous': 15, 'process': 1, 'implementer': 4}
branch rows 56  in-window 56  caused 51   (the two ledgers are byte-identical;
                                           main has not moved since 110ba13)
```

So the branch's seeded-ledger assertion (`56 rej, 51 plan (vac 15, miss 19,
under 9, fact 8)`) is right for both trees, and it moves with the ledger — a
one-row class flip kills it (mutant M11b).

## Tests and mutants

Five new tests (173 pass, was 168), six new fixtures, one new bats test (362
bats tests, was 361). Forty-four mutants applied to `pkgs/evidence/tasks.py`,
`docs/ledger/plan-defects.toml` or `tools/session-start.sh`, run against
`pytest tests/evidence -q` or `bats tests/unit/90-session-start.bats`, then
reverted; the tree was verified clean after the sweep.

**All thirty-four named die.** P3Ar's six:

| # | mutant | result |
|---|---|---|
| P1 | the brief default left at 1200 (`session-start.sh`) | KILLED — `not ok 8` |
| P2 | `int(raw)` + `n < 0` restored (`+5` accepted) | KILLED |
| P3 | the contradiction arm dropped | KILLED |
| P4 | `read_reviews` glob widened to `*.md` | KILLED |
| P5 | the record's verdict skip → `m is not None and verdict == "APPROVED"` | KILLED |
| P6 | the lookahead widened from three lines to six | KILLED |

P3Ab's ten, all still dead: N1 the verdict test dropped; N2 the shape check
dropped; N3 the int parse dropped; N4 the global `--today` dropped; N5a
`plan_defect missing`; N5b secondary-outside-enum; N5c unreadable ledger
degrades to `(None, [])`; N5d `_today_utc` frozen to 1970-01-01; N5e the check
glob widened; N6 the long record line restored.

P3A's fourteen, all still dead: M1 `_split_front_matter` returns `lines[0]`;
M2 `date > fmf`; M3 block validation date-gated; M4 `"maybe"` in the enum; M5
the REJECTED/`none` arm unreachable; M6 the equality arm unreachable; M7
secondaries also counted; M8 rows with a secondary skipped; M9 `start < date`;
M10 the dedup removed; M11 every `vacuous` seed row flipped; M11b one seed row
flipped; E1 the `no such review` arm removed; E5 `_review_defect_errors`
unwired.

P3Ab's four surviving-list-free extras, still dead: X1 the lookahead removed
from `_review_h1`; X2 the shape check date-gated; X6 `PLAN_DEFECT_SHORT`
`vac`↔`miss` swapped; X8 the `brief --today` option dropped. P3Ab's three
survivors (X4 negatives, X5 the `m is None` half, X7 the lookahead width) are
now P2/P2b, P5 and P6 — all three die.

Ten of my own, outside the named list; eight die, two survive:

| # | mutant | result |
|---|---|---|
| P2b | the integer regex loosened to `-?[0-9]+` | KILLED |
| Y1 | the board default raised by 700 (2300 → 3000) | KILLED |
| Y2 | the board default restored to 2500 (sum 7500) | KILLED |
| Y5 | the shape check reads the 3-line lookahead (a blank line passes) | KILLED |
| Y6 | the contradiction fires with no matching ledger row | KILLED |
| Y7 | the record keeps a block it cannot verdict | KILLED |
| Y8 | `read_reviews` glob → `*review*.md` | KILLED |
| Y9 | the total cap dropped to 7,000 | KILLED (the structural sum test) |
| Y3 | the integer regex loosened to `[0-9]*` (an empty value accepted) | SURVIVED |
| Y4 | the contradiction fires on any verdict, not only APPROVED | SURVIVED |

`mutants_total: 44, mutants_killed: 42, mutants_outside_named: 10`.

## Checks

All from inside the fresh clone.

```
nix develop -c ruff check pkgs/evidence tests/evidence          All checks passed!
nix develop -c ruff format --check pkgs/evidence tests/evidence 49 files already formatted
nix develop -c pytest tests/evidence -q                         173 passed
nix build .#checks.x86_64-linux.evidence-unit -L --rebuild      173 passed, exit 0
nix build .#checks.x86_64-linux.unit -L --rebuild               ok 362 …, exit 0
nix build .#checks.x86_64-linux.lint -L --rebuild               0 warnings, 0 errors, exit 0
nix develop -c githooks/pre-commit                              exit 0
nix develop -c bats tests/unit/90-session-start.bats            24/24 ok
repomap.py --root . write ; git diff --exit-code docs/MAP.md    MAP REPRODUCES
tasks.py --root . check                                         (silent) exit 0
claims.py validate docs/ledger/claims.toml --today 2026-09-06   (silent) exit 0
bash tests/lint/bats-and-chain.sh                               exit 0
git status --porcelain after all of it                          clean
```

`lint --rebuild` runs the check rule over the real `docs/reviews/`, which now
holds four block-carrying files, all dated 2026-09-06: green, and neither the
shape rule, the integer rule nor the contradiction rule fires on any of them.

The clone's own `tasks.py check` over the live tree carrying THIS review file
(a `cp -a` copy could not be made — this session's plan-file guard refuses a
copy of the repo into the scratch dir, the same class of refusal the pb3a gate
hit with `git clone`, so the run is read-only against the live tree, where the
file already sits untracked):

```
$ nix develop -c python3 pkgs/evidence/tasks.py --root /home/dalhaka/nixos-agent-env check
(no output)
exit=0
$ _read_review(…-pb3ar-P3Ar.md)
block {'plan_defect': 'none', 'mutants_total': '44', 'mutants_killed': '42',
       'mutants_outside_named': '10'}
first '# Opus gate — seat run pb3ar, task P3Ar — APPROVED'   (the H1 immediately after the block)
errors naming this file: []
```

Commit convention: one commit `110ba13..83d3dfd`; subject byte-identical to the
plan's P3A/P3Ab/P3Ar subject (195 bytes each, compared byte for byte);
`Generated-By` and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
both present; no board commit; every touched file inside `touches` except
`docs/MAP.md`, which regenerates (`tests/evidence` 37 → 43, the six new
fixtures). The body carries the ordered measurement (`7466` bytes, `1093` brief
chars, 307 under 1,400) and the live Record line, which is exactly what P3Ab
omitted. `P3Ar.result` ends with the FACTORY-RESULT block in its exact form
(`status=done`, `FACTORY-CHECKS evidence-unit=pass unit=pass lint=pass`,
`FACTORY-COMMITS 1`, `FACTORY-NOTES …`).

## Red before green

P3Ab's tree (`git show task/P3Ab:pkgs/evidence/tasks.py` and
`task/P3Ab:tools/session-start.sh`) under this branch's tests:

```
$ nix develop -c pytest tests/evidence -q
3 failed, 170 passed in 4.55s
FAILED …::test_check_rejects_signed_and_underscore_mutant_counts
FAILED …::test_check_rejects_row_with_approved_block_contradiction
FAILED …::test_read_reviews_ignores_non_opus_review

$ nix develop -c bats tests/unit/90-session-start.bats
not ok  7 a board over its cap (2300) is cut and the bundle still follows
not ok  8 a brief over its cap (1400) is cut at the default 1400
not ok 12 with defaults the brief and the pointer print last even when all three parts overflow
ok     22 the five part defaults sum to at most the total ceiling minus 700
not ok 23 with every part overflowing the output stays under 8000 and the pointer stays last
not ok 24 a non-numeric part cap falls back to that part's default
```

Restored: `173 passed`, `24/24 ok`. The cap default, the integer strictness, the
contradiction and the glob are all red on P3Ab, as the plan asked. Test 22 —
P4b's structural sum test — is green on both trees, which is the point: the sum
never moved. Two of the five new pytest tests
(`test_record_out_of_reach_h1_counts_by_row_only`,
`test_h1_four_lines_down_is_shape_error_and_absent_from_graph`) pass on P3Ab by
design: they are the coverage-only halves of item 3's "three untested clauses",
whose contract is "the mutation kills them" — P5 and P6 above. Minor 3.

## Findings

No majors. Six minors.

1. **The `+` in `^[0-9]+$` is untested.** `pkgs/evidence/tasks.py:1010`; the
   new test drives `-1`, `+5`, `1_0` and `٣` but never the empty value, so
   loosening the pattern to `[0-9]*` — which accepts `mutants_total:` with no
   value — passes the whole suite (mutant Y3). The implementation is right (an
   empty value is refused, verified by hand); the guard is one string short.

2. **The contradiction arm's `APPROVED` restriction is untested.** `:1037`;
   dropping the verdict test so the error fires on any block with a matching
   ledger row passes the whole suite (mutant Y4). Every REJECTED review that
   also gets an orchestrator row would then draw a spurious error. Same class
   as minor 1.

3. **Two of item 3's five tests are green on P3Ab.** Step 1 asks for "the three
   clauses" red on P3Ab; only the `-1` clause is (inside
   `test_check_rejects_signed_and_underscore_mutant_counts`). The row-only and
   lookahead-width clauses were already correct on P3Ab (its surviving mutants
   X5 and X7), so their tests are coverage-only and are pinned by mutants P5
   and P6 instead. Contracted that way in substance, and the same pattern the
   gate accepted for P3Ab's item 5 — recorded so the pattern stays visible.

4. **"Unchanged" holds for the structural sum test, not literally for the
   all-overflow test.** `tests/unit/90-session-start.bats:310–350` keeps its
   shape, its precondition and its three behavioural assertions, but its three
   truncation-line literals moved (2500 → 2300, 1200 → 1400) because the
   assertion names the cap value. Unavoidable given the contract changes the
   caps; the sum test at `:292` is byte-unchanged, as the contract intends.

5. **Nothing pins the headroom figure.** The brief's length varies with live
   in-flight state — 1,093 chars when the seat measured, 1,017 today, a 76-char
   swing from one `**Running:**` line — and no test asserts a floor. The cap
   bounds the damage (a long brief is truncated, the pointer survives), which is
   the property the all-overflow test does hold, so this is a reporting note,
   not an exposure: the "at least 250" is a snapshot, not an invariant.

6. **The narrowed `read_reviews` glob is silent about files it now drops.**
   `:285`. Verified behaviour-neutral over all five configured repos today
   (no verdict lost), but it changed enough that eleven existing test fixtures
   had to be renamed `a.md` → `opus-review-a.md` to keep supplying verdicts.
   A future review filed under a name without "opus-review" is now absent from
   the task graph and never block-validated, with no error anywhere. Contracted
   ("`read_reviews` globs `*opus-review*.md` like the block rule"), documented
   in `docs/runbooks/evidence.md`, and worth an eye when the naming convention
   is next touched.

## Verdict

**APPROVED.** The caps carry the headroom exactly as the re-plan says: the sum
is still 7,300, the worst case recomputes to 7,703 of 8,000, P4b's structural
sum test is byte-unchanged and green, and the brief part keeps 383 chars of
headroom under its 1,400 cap on this host (307 as the seat measured it, with the
probe actually run and pasted this time). Items 1–5 of P3Ab are untouched and
re-verified by hand; the five minors are folded and each is killed by its named
mutant; all thirty-four named mutants die and eight of my ten extras; the live
Record line is byte-exact against a hand tally; every check and the lint gate are
green; one commit, subject byte-identical, both trailers, nothing outside
`touches` but the regenerated MAP. Fold minors 1–2 (the two untested clause
halves) into the next `tasks.py` task; 3–6 are notes.
