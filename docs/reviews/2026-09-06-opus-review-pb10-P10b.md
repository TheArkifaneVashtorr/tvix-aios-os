---
plan_defect: wrong-fact
mutants_total: 22
mutants_killed: 18
mutants_outside_named: 4
reviewer: opus
majors: null
minors: 7
---
# Opus gate — seat run pb10, task P10b — APPROVED

## Summary

Branch `task/P10b`, base `cf87659`, head `f068ca5`, ONE commit, 16 files
(+798/−1), subject byte-identical to the plan's, both trailers after a blank
line, every touched file inside `touches` plus `docs/MAP.md` by rule
(`repomap.py write` reproduces it exactly). Reviewed in a fresh clone
(`…/scratchpad/gate-pb10-P10b`); nothing under `/home/dalhaka/factory` or
`/home/dalhaka/nixos-agent-env` was modified except this file, and every run
used `--store /nonexistent` or a scratch store.

All three of P10's majors are fixed and the fixes are pinned:

- **Line 2 is now all-rows and verdict-aware.** `report.py:85` `_all_rows_record`
  replaces the call into P3A's seven-day record. `--today` no longer moves the
  figure at all (`2026-09-05`, `2026-09-12`, `2026-09-20`, `2027-12-31`,
  `1999-01-01` → `51/56 (91%)` on this tree, every time), and an APPROVED block
  carrying a `plan_defect` never enters the denominator (my fixture: `2/2`,
  where P10 printed `2/3`). Both mutations the plan names die.
- **The n-gate default is pinned.** `test_default_n_gate_is_five` calls
  `plans_report` without `min_n` on a four-chain fixture; lowering the default
  to 2 fails it. The parenthetical now names the gate in force
  (`refused: n=4 < 8 (no conclusion under 8)`).
- **Rounds follow the prose**, over landed chains only; the fixture's line 4 is
  `2/4 = 0.50`, recomputed by hand in the test, and counting rounds over gated
  chains (`3/4`) fails.

Every figure the report prints matches my own hand tally — computed with my own
script, no import of `report.py` — digit for digit, on the clone and on the live
tree, in both scopes. The rounds figure the seat pasted (`47/59 = 0.80`) rather
than the plan's `46/58 = 0.79` is right, and its stated cause is right: the
newly landed chain is **CR2r3** (`CR2r3` REJECTED → `CR2r3b` APPROVED, cr21),
not CR2 — CR2 (`CR2, CR2b, CR2r, CR2rb`, 3 rounds) is still open, and a CR2
landing would have moved the figure by three rounds, not one.

18 of 22 mutants die, including every one the plan names and all nine P10's gate
killed. The four survivors are all in the same place — the report-local copy of
the block reader, whose dedup, `front_matter_from` cut and `*opus-review*` glob
no test in `test_report.py` exercises — and none of them changes a figure today
(the copy is byte-for-byte P3Ar's rule minus the window; I proved the two agree
on a fixture inside one window). Six minors, no MAJORs.

## The hand tally

My rule, applied by hand: a chain is a `chain_root` key claimed by a typed task;
members = the root plus every reviewed key whose root is this root; gated = ≥ 1
member reviewed; first-try = the root's own review is APPROVED; re-plan = a
member whose suffix past the root contains `r`; landed = the last member (root
first, then alphabetical) is APPROVED; rounds = members beyond the root, **over
landed chains only**.

| line | scope `2026-09-05-*.md` (clone) | report (clone) | all typed plans (clone) | report (clone) | live tree |
|---|---|---|---|---|---|
| 1 first-try | 28/63 = 44.4 % | `28/63 chains (44%)` | 32/73 = 43.8 % | `32/73 chains (44%)` | 28/63 · 32/74 |
| 2 plan-caused | 51/56 = 91.1 % | `51/56 (91%)` | 51/56 | `51/56 (91%)` | 52/57 (91 %) |
| 3 re-plan | 10/63 | `10/63 chains` | 11/73 | `11/73 chains` | 10/63 · 11/74 |
| 4 rounds ÷ landed | 47/59 = 0.796 | `47/59 = 0.80` | 52/67 = 0.776 | `52/67 = 0.78` | 47/59 · 52/67 |
| 5 rubric | n=0 | `n=0, refused` | n=0 | `n=0, refused` | same |

Every cell reproduced independently. The ten re-plan chains are CR2, CR3, E2,
E7, G11, G12, OG1, R3, RT5, SB2 (the eleventh in the unrestricted scope is P11,
from the 2026-09-06 plan). `ls docs/superpowers/plans/2026-09-05-*.md` is
thirteen files, **twelve** of which carry typed tasks
(`2026-09-05-night-plan.md` has none) — as the runbook now says.

The arithmetic of the difference against pa10's `46/58`:

```
CR2r3   members=['CR2r3', 'CR2r3b']   landed=Y (cr21 CR2r3b APPROVED)   rounds=1
CR2     members=['CR2','CR2b','CR2r','CR2rb']   landed=n   rounds=3    ← unchanged
```

so landed 58 → 59 and rounds 46 → 47. `47/59 = 0.7966 → 0.80`.

**The suffix-limit direction, checked on this tree.** Merging `CR2r2`, `CR2r3`,
`OG1r2` into their parents gives 28/60 = 46.7 % against the as-is 28/63 = 44.4 %
(unrestricted: 32/70 = 45.7 % against 32/73 = 43.8 %): the limit **lowers** the
rate, as the commit body says. The body cites pa10's clone numbers (69 → 66,
45 % → 47 %) and labels them as such; on this tree they are 73 → 70 and
43.8 % → 45.7 %.

## Line 2 and the record reader

Hand count of the ledger, `grep -c '^\[\[rejection\]\]'` plus the class tally:

| tree | rows | vac | miss | under | fact | impl | proc | plan-caused | report |
|---|---|---|---|---|---|---|---|---|---|
| clone (base `cf87659`) | 56 | 15 | 19 | 9 | 8 | 4 | 1 | 51 | `51/56 (91%)` |
| live `main` (`00ae401`) | 57 | 15 | 20 | 9 | 8 | 4 | 1 | 52 | `52/57 (91%)` |

`front_matter_from = 2026-09-07` on both trees and no review is dated ≥ that, so
no block is in play yet; the difference between the trees is the pa9 row
(missing-case) the orchestrator added after the branch's base.

Behaviour by hand, all through the CLI on scratch fixtures:

| case | result |
|---|---|
| ledger row + REJECTED block + APPROVED block, all dated far in the past | `2/2 (100%)` — the APPROVED block never counts |
| the same, `--today` 2026-01-01 / 2026-02-02 / 2026-09-06 / 2030-01-01 | `2/2` in every case — no window |
| the ledger row names the **same file** as the REJECTED block | `1/1` — counted once, the block's class wins |
| `front_matter_from` moved past the block dates | `0/1` — the block drops, the ledger row stays |
| a REJECTED block on a non-`opus-review` filename | ignored (glob), as in `tasks` |
| a blank line between the block and the H1, REJECTED / APPROVED | counted / not counted (the lookahead path) |
| an unparseable ledger | `plan-caused share of rejections: unmeasured (n=0)`, exit 0 |
| the live tree, `--today` from 1999 to 2027 | `51/56 (91%)` unchanged |

**`_all_rows_record` versus P3Ar's `plan_defect_record`.** The report
re-implements the reader rather than calling it. I read both line by line
(`report.py:85-125` against `tasks.py:1062-1140`): same `*opus-review*.md` glob,
same `_review_date` / `< front_matter_from` cut, same `_read_review` 4-tuple,
same `_review_h1` + `verdict != "REJECTED"` test, same `pd is None` skip, same
`"docs/reviews/" + name` key, same block-wins dedup over the ledger rows. The
only differences are deliberate: no seven-day window, and one repo instead of a
repo list. A differential run on a fixture whose dates all fall inside one
window agrees exactly:

```
P3Ar record (7d window, today=2026-09-06): (3, {'missing-case': 1, 'underspecified': 1, 'implementer': 1})
report._all_rows_record                  : (3, {'missing-case': 1, 'underspecified': 1, 'implementer': 1})
```

No divergence changes a count — MINOR 2, not a MAJOR — but the copy is unpinned
(see the mutants).

## The cases

Driven through `evidence.py … report plans`, not the library, unless noted.

| case | result |
|---|---|
| the six-chain fixture | `2/5 (40%)`, `1/5 (20%)`, `1/5`, `2/4 = 0.50` — all four by hand |
| the default n-gate, four chains, no `--min-n` | `refused: n=4 < 5 (no conclusion under 5)`, no line 1 ✔ |
| `--min-n 4` (at the gate) / `--min-n 2` | all four lines print ✔ |
| `--min-n 8` on four chains | `refused: n=4 < 8 (no conclusion under 8)` — the parenthetical follows the gate ✔ |
| zero denominators (five gated, none landed, no ledger) | `plan-caused …: unmeasured (n=0)`, `rework rounds …: unmeasured (n=0)` ✔ |
| an empty store | `rubric score before dispatch: n=0, refused` ✔ |
| an empty repo with `--min-n 0` | `first-try landing rate: 0/0 chains (0%)`, `re-plan rate: 0/0 chains` — MINOR 3 |
| the two-revision join | one line, latest revision (`p0.md total 40 decision revise`), `n=5` ✔ |
| ten rows, one plan repeated (9 distinct) | no `threshold proposal` line ✔ |
| eleven rows, one plan repeated (10 distinct) | `threshold proposal: 30`, the repeated plan at its latest revision ✔ |
| `--plan '2026-09-05-*.md'` on a mixed repo | `5/5 (100%)`; `'2026-09-0[56]-*.md'` → `5/10 (50%)` ✔ |
| a glob matching nothing | `refused: n=0 < 5 …`, exit 0 (no crash, no figure) |
| `--today notadate` | `report: --today notadate: invalid date (YYYY-MM-DD)` on stderr, **exit 2** ✔ |
| an unreadable repo | `report: cannot read repo /nope`, **exit 2** ✔ |
| an unreadable store (`chmod 000 plans.jsonl`) | `report: cannot read store …: [Errno 13] Permission denied`, **exit 2** ✔ |
| the CLI end to end | `test_cli_end_to_end_dispatch_and_store_forwarding` runs `evidence.py --store … report plans --repo …` in a subprocess and asserts rc 0 and line 1 ✔ |
| stdout discipline | header first, every figure with its n, **0 bytes on stderr** on success |

## The runbook

`docs/runbooks/evidence.md:112-139`, a new "## The planning report" section
(the design file is untouched: `git diff cf87659..HEAD -- docs/superpowers/specs`
is empty, as are `docs/superpowers/plans`, `docs/OPERATIONS.md` and
`docs/ledger`). All three corrections the decision requires are present and
worded as the decision says:

- line 2 is "every ledger row plus every REJECTED block, no seven-day window and
  an APPROVED block never counts";
- rounds "are counted over landed chains only", line 1 and line 3 divide by
  chains gated;
- "The design §7 'today' column is superseded by this report's numbers: §7 used
  landed chains as its denominator for every row and counted rework rounds over
  gated chains, and it said 'ten typed 2026-09-05 plans' where twelve are typed.
  On this tree, over `--plan '2026-09-05-*.md'`, the report prints first-try
  28/63, re-plan 10/63 and rework rounds 47/59 = 0.80 — not the design's 28/58,
  11/58, 30/58."

Two of those three claims I reproduce exactly (58 = the landed count at pa10's
tree; twelve typed plans). The third — that §7 "counted rework rounds over gated
chains" — is the plan's own words and is **not** reproducible: rounds over gated
chains is 52 (46/47 over landed), nowhere near §7's 30. See the plan defect
below; the seat wrote what §P10b's contract told it to write.

## Tests and mutants

188 evidence tests green in the devShell and inside the `evidence-unit`
derivation (173 at the base + 15 in `test_report.py`). 22 mutants applied to
`pkgs/evidence/report.py`, `pytest tests/evidence` after each, reverted after
each; 18 killed.

| # | mutant | named? | result |
|---|---|---|---|
| N1 | line 2 back to `tasks.plan_defect_record` (P10's code, the window restored) | yes | **killed** (`test_line_two_is_all_rows_not_windowed`, `…never_counts_an_approved_block`) |
| N1' | a seven-day window applied inside `_all_rows_record` | yes | **killed** (3 tests) |
| N2 | the `verdict != "REJECTED"` test dropped | yes | **killed** |
| N3 | `plans_report`'s `min_n` default 5 → 2 | yes | **killed** (`test_default_n_gate_is_five`) |
| N4 | rounds counted over gated chains (`3/4`) | yes | **killed** |
| N5a | the zero guard dropped on line 2 | yes | **killed** |
| N5b | the zero guard dropped on line 4 | yes | **killed** |
| N6 | the join iterates rows, not plans | yes | **killed** (2 tests) |
| N7 | `--plan` matched exactly, no glob | yes | **killed** |
| N8 | `--today` unvalidated | yes | **killed** |
| M1 | any `b` member counted as a re-plan | P10's | **killed** |
| M2 | the open chain counted (`gated = list(roots)`) | P10's | **killed** |
| M4 | `max` instead of `min` for the threshold | P10's | **killed** |
| M5 | the join keyed on the full plan path | P10's | **killed** |
| M6 | the plan class set widened to `implementer` | P10's | **killed** |
| M7 | survivors `gates` counted over every review | P10's | **killed** |
| M8 | line 5's n-gate dropped | P10's | **killed** |
| M9 | `--plan` ignored | P10's | **killed** |
| X1 | the block-wins dedup dropped in `_all_rows_record` | no | **SURVIVED** |
| X2 | the argparse `--min-n` default 5 → 2 (the second copy) | no | **SURVIVED** |
| X3 | the `>= front_matter_from` cut dropped | no | **SURVIVED** |
| X4 | the record's glob widened to `*.md` | no | **SURVIVED** |

All four survivors sit in `_all_rows_record` / the CLI default — the clauses the
report duplicates from P3Ar and never exercises in its own suite (MINOR 1 and
MINOR 2). Every mutant the plan names, and every mutant P10's gate killed, dies
here.

## Checks

All inside the clone, in the devShell.

| check | result |
|---|---|
| `ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| `ruff format --check pkgs/evidence tests/evidence` | `60 files already formatted` |
| `pytest tests/evidence -q` | `188 passed in 4.69s` |
| `nix build .#checks…evidence-unit -L --no-link --rebuild` | built, `188 passed in 4.62s` |
| `nix build .#checks…lint -L --no-link` | exit 0 |
| `githooks/pre-commit` | **exit 1**: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated…` — the regenerated block only drops `P10b` from the queue (the commit's subject lands the task); the base `cf87659` passes clean. Identical to what pa10's gate recorded; the Global Constraints call the regenerate-and-commit-again path "still ONE commit" and every wave has the orchestrator regenerating at integration. Recorded, not counted. |
| `repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | no diff (43 → 55 files reproduced) |
| `tasks.py --root . check` | silent, exit 0 |
| `claims.py validate … --today 2026-09-06` | silent, exit 0 |
| commit convention | one commit; subject byte-identical (`diff` of `%s` against the plan's line: empty); `Generated-By` + `Co-Authored-By` after a blank line; 16 files, all inside `touches` or `docs/MAP.md` |

Live lines, clone (`--store /nonexistent report plans --repo .`):

```
first-try landing rate: 28/63 chains (44%)      # --plan '2026-09-05-*.md'
plan-caused share of rejections: 51/56 (91%)
re-plan rate: 10/63 chains
rework rounds per landed task: 47/59 = 0.80
rubric score before dispatch: n=0, refused

first-try landing rate: 32/73 chains (44%)      # no --plan
plan-caused share of rejections: 51/56 (91%)
re-plan rate: 11/73 chains
rework rounds per landed task: 52/67 = 0.78
rubric score before dispatch: n=0, refused
```

Both blocks are byte-identical to the commit body's. On the live tree the same
runs give `28/63`, `52/57 (91%)`, `10/63`, `47/59 = 0.80` and `32/74`, `52/57`,
`11/74`, `52/67` — the ledger row and the P8 chain that landed on main since the
branch's base.

## Red before green

P10's `report.py` (`git -C /home/dalhaka/factory/ws/pa10/P10 show
task/P10:pkgs/evidence/report.py`) dropped into this branch's tree, this
branch's tests:

```
12 failed, 3 passed in 0.17s
FAILED test_corpus_lines_reproduce_by_hand            # rounds 3/4, not 2/4
FAILED test_line_two_is_all_rows_not_windowed
FAILED test_line_two_never_counts_an_approved_block
FAILED test_default_n_gate_is_five
FAILED test_refusal_parenthetical_names_the_gate_in_force
FAILED test_zero_denominators_print_unmeasured
FAILED test_rubric_refuses_under_five_and_joins_at_five
FAILED test_join_iterates_plans_latest_revision_only
FAILED test_threshold_proposal_is_the_minimum_clearing_total
FAILED test_survivors_outside_named_set
FAILED test_plan_flag_accepts_a_glob
FAILED test_malformed_today_is_exit_two
```

Every contracted red is there (all-rows line 2, the APPROVED denominator, the
default gate, the rounds, the zero guard, the join, the glob, `--today`).
Restoring the branch's module: 188 passed. The CLI end-to-end test passes under
P10 too — it asserts line 1, which P10 also printed — so it is new coverage
rather than a red; the commit body does not claim otherwise.

## Findings

No MAJORs.

### MINOR 1 — the CLI's `--min-n` default is a second, unpinned copy

`pkgs/evidence/report.py:271`

```python
    p.add_argument("--min-n", type=int, default=5)
```

`test_default_n_gate_is_five` pins `plans_report`'s default (mutating it to 2
fails the suite, as the plan requires), but lowering *this* copy alone leaves
188 green, and this is the default the operator meets. Pin: give `main()` no
default of its own (`default=None` → pass through, or a module constant
`MIN_N = 5` used in both places) and add a `report.main([...])` case on the
four-chain fixture asserting the refusal on stdout.

### MINOR 2 — the record reader is duplicated from P3Ar, and its clauses are unpinned

`pkgs/evidence/report.py:85-125` re-implements `tasks.plan_defect_record`'s
block scan. Today the two agree exactly (differential run above), but three of
the copy's clauses have no test in `test_report.py`: dropping the block-wins
dedup (X1), dropping the `>= front_matter_from` cut (X3) and widening the glob
to `*.md` (X4) all leave 188 green. A change to P3Ar's rule would not reach the
report and nothing would go red. Pin: one test per clause (a file in the ledger
*and* carrying a REJECTED block → `1/1`; a block dated before
`front_matter_from` → excluded; a REJECTED block on a non-`opus-review` name →
excluded), or lift the window out of `plan_defect_record` (`window=None`) and
call it.

### MINOR 3 — `--min-n 0` defeats contract item 4 for lines 1 and 3

`pkgs/evidence/report.py:177,271`. `--min-n` is unvalidated, so `--min-n 0` (or
a negative) prints `first-try landing rate: 0/0 chains (0%)` and `re-plan rate:
0/0 chains` on an empty repo — the very form item 4 forbids. With any
`--min-n >= 1` those denominators cannot be zero, so this is only reachable by
asking for it. Refuse a `--min-n` below 1.

### MINOR 4 — an unreadable ledger reads as "no rejections"

`pkgs/evidence/report.py:184-190`: `_all_rows_record` returns `None` for an
unparseable `plan-defects.toml` and the report prints
`plan-caused share of rejections: unmeasured (n=0)` — the same words as a repo
with no rejections at all, and exit 0. `tasks.brief` distinguishes the two
(`**Record: unavailable**`). A ledger typo would silently retire the metric.
The `None` branch has no test.

### MINOR 5 — `--today` is now inert

`pkgs/evidence/report.py:155-159`: `today` is validated and then never used —
line 2 was its only consumer. Keeping the flag (the contract asks for the exit-2
path) is fine, but the help text should say it affects nothing today, or the
value should be threaded to whatever next needs it.

### MINOR 6 — no test for the unreadable-store exit 2

`tests/evidence/test_report.py` covers the unreadable repo and the malformed
`--today`; the store's `ReportUnreadable` path (`report.py:152-153`) is exercised
only by hand (I confirmed it: exit 2, message on stderr).

## Plan defects (not counted against the seat)

- **wrong-fact.** §P10b's contract item 7 dictates the runbook sentence "§7 …
  counted rework rounds over gated chains". Rounds over gated chains is **52**
  over the 2026-09-05 scope (47 over landed, 46 at pa10's tree); §7's figure is
  30, which neither reading yields — pa10's gate said exactly this ("Neither
  reading gets near 30"). The correct half of the correction (58 = the landed
  count, so 28/58 contradicts §7's own definition) is reproduced and right; the
  rounds half asserts a mechanism that is not the one §7 used, and it is now
  written into a runbook as the record. The seat had no latitude here: the
  contract quotes the sentence.
- Item 7's `rounds 46/58 = 0.79` was already stale when the plan was typed (cr21
  landed CR2r3b before it). The plan says "verify by hand and paste", the seat
  verified and pasted `47/59 = 0.80`, and my own tally agrees — the right call,
  correctly explained in the commit body.

## Verdict

**APPROVED.** Every line the report prints equals my independent hand tally
digit for digit in both scopes and on both trees; line 2 is over all rejection
rows, verdict-aware and unaffected by `--today`; the n-gate default, the rounds
rule, the zero guard, the per-plan join, the glob and the exit-2 paths are each
pinned by a test that dies under its named mutation; the three corrections stand
in the runbook and the design file is untouched; ruff, 188 tests, `evidence-unit`
and `lint` are green, the map and the graph reproduce, and the commit is one
commit with the plan's subject and both trailers. The six minors are follow-up
material — chiefly the duplicated record reader, which should be pinned or
folded back into `tasks.plan_defect_record` before P3Ar's rule moves again.
