---
plan_defect: none
mutants_total: 19
mutants_killed: 14
mutants_outside_named: 7
---
# Opus gate — seat run pa7, task P3A — APPROVED

## Summary

One commit `b7ca5f5` on `be43169`, 13 files (+932/−10), subject byte-identical
to the plan's. The seed is exact: 48 rows, every one matching design Appendix B
row for row, every `review` path present, every `date` equal to its basename's
prefix, and the distribution the contract names (45 plan-caused = vacuous 15,
missing-case 16, underspecified 8, wrong-fact 6; implementer 2; process 1). The
block-aware parser leaves every consumer intact (`check`, `brief`, `waves`,
`conflicts`, `write-board`, `tools/session-start.sh`, `tools/ritual.sh
inflight`), `write-board` reproduces the live board byte for byte, and the new
`check` rule stays silent on the twelve block-less reviews the live tree filed
on 2026-09-06 while refusing the same file renamed to 2026-09-07. Every one of
the plan's eleven named mutants dies against the contracted test. Seven minors,
no major.

## The seed

No deviation from Appendix B. Audited with `tomllib` against the table parsed
out of `docs/superpowers/specs/2026-09-05-planning-agent-design.md` lines
863–905:

```
rows: 48
meta: {'front_matter_from': datetime.date(2026, 9, 7)}
primary: {'missing-case': 16, 'wrong-fact': 6, 'underspecified': 8,
          'vacuous': 15, 'process': 1, 'implementer': 2}
secondary: {'implementer': 2, 'wrong-fact': 1, 'vacuous': 1, 'missing-case': 2}
plan-caused: 45
missing files: []
date mismatch: []
dup run/key: []
```

All 43 Appendix B rows compared one by one; every class matches, including the
three two-class rows (`cr15 · CR2r` missing-case / implementer, `ev1 · R5`
missing-case / wrong-fact, `sc1 · G2` process / vacuous — primary first as the
appendix directs) and `cr2 · CR1` as ONE `missing-case` row despite its
"missing-case ×4". The prose rows are present exactly as contracted (`sc5 ·
G12` and `oi1 · DA1`, both `implementer` with secondary `missing-case`), and
the three post-corpus rows are `cr17 · CR2rb` → missing-case, `bk3 · B1b` →
vacuous, `cr18 · CR2r2` → missing-case with secondary `implementer`. The set
difference against Appendix B is exactly those six extra rows and nothing else:

```
extra rows: [('a3','W2-N6b'), ('bk3','B1b'), ('cr17','CR2rb'),
             ('cr18','CR2r2'), ('oi1','DA1'), ('sc5','G12')]
```

(`a3 · W2-N6b` is an Appendix B row my parser's slice dropped; checked by hand
— appendix `missing-case`, ledger `missing-case`.)

No row for `bk4 · B1c` (the approval), and no row for any review filed after
the plan: `cr19`, `cr20`, `pa1`–`pa5`, `pb4`, `pb6`, `sb8` are all absent, as
the contract requires — those are the orchestrator's to add.

Four rows point at files whose basename is not
`<date>-opus-review-<run>-<key>.md`, because the review was filed under another
name; each was opened and is the right review:
`docs/ledger/plan-defects.toml:13` `a3 · W2-N6b` →
`2026-09-04-opus-review-a3-N6.md` (`# Opus gate — fix chain W2-N6a → W2-N6b`),
`:34` `a9 · N19` → `…-a9-N19-H4.md`, `:41` `b3 · F9/BFIX` →
`…-dsh-harness-b3.md`, `:48` `b2 · F6` → `…-dsh-harness-F6.md`. Appendix B's
own note allows this ("Run and key as in …"); not a deviation.

## The parser and the consumers

Run from the clone against the live tree (read-only) and against a `git clone`
copy of it.

```
$ tasks.py --root /home/dalhaka/nixos-agent-env check          → (silent) exit=0
$ tasks.py --root /home/dalhaka/nixos-agent-env waves --repo nixos-agent-env
"SB5"                                                              exit=0
$ tasks.py --root /home/dalhaka/nixos-agent-env conflicts
nixos-agent-env: CR4 (…) × SB5 (…): CLAUDE.md ~ CLAUDE.md         exit=0
$ tasks.py --root <copy of live tree> write-board                  exit=0
BOARD BYTE-IDENTICAL
$ bash tools/session-start.sh </dev/null                            exit=0, stderr empty
$ bash tools/ritual.sh inflight /home/dalhaka/nixos-agent-env       exit=0
```

The brief is unchanged but for the one line. Old (`be43169`) vs new, same tree,
same flags:

```
1c1
< # Task brief (generated 2026-09-06T08:32:35Z)
---
> # Task brief (generated 2026-09-06T08:32:34Z)
7a8
> **Record (7 d):** 48 rejections, 45 plan-caused (vacuous 15, missing-case 16, underspecified 8, wrong-fact 6)
```

It lands directly after `**Next wave**`, before `**Running:**`, as
`pkgs/evidence/tasks.py:1388–1398` places it.

`nix build .#checks.x86_64-linux.unit` (360 bats tests, incl. the 16
session-start tests) is green, so no hook consumer regressed.

## The check rule

Today's block-less reviews pass, and the boundary is real. The live tree holds
twelve `2026-09-06-*opus-review*.md` files, none with a block; with the ledger
placed in a clone of that tree:

```
$ tasks.py --root <live copy> --repos <one-repo> check
exit=0   (silent — the 12 block-less 2026-09-06 reviews pass)

$ cp …/2026-09-06-opus-review-bk4-B1c.md <live copy>/docs/reviews/2026-09-07-opus-review-fake-X1.md
$ tasks.py --root <live copy> --repos <one-repo> check
tasks: review 2026-09-07-opus-review-fake-X1.md: no front-matter block (plan_defect is required from 2026-09-07)
exit=1
```

By hand on fixtures (every enum value × both verdicts, dated 2026-09-07):

```
  none            APPROVED  -> ok
  none            REJECTED  -> ['tasks: review …: a rejection names its cause']
  vacuous         APPROVED  -> ok      vacuous         REJECTED  -> ok
  missing-case    APPROVED  -> ok      missing-case    REJECTED  -> ok
  underspecified  APPROVED  -> ok      underspecified  REJECTED  -> ok
  wrong-fact      APPROVED  -> ok      wrong-fact      REJECTED  -> ok
  implementer     APPROVED  -> ok      implementer     REJECTED  -> ok
  process         APPROVED  -> ok      process         REJECTED  -> ok
```

- secondary equal to primary → `plan_defect_secondary equals plan_defect`
- secondary outside the enum → `plan_defect_secondary nonsense not in none | vacuous | …`
- `plan_defect` absent from an otherwise valid block → `plan_defect missing`
- unknown keys (`surprise: 42`) → ignored, silent
- block with no closing `---` → read as no block: `no front-matter block` on a
  new-dated file, and `read_reviews` returns `{}`
- CRLF line endings → block parsed, `read_reviews` returns the verdict, the
  `none`+REJECTED rule fires
- early file (2026-09-05) with `plan_defect: maybe` → `plan_defect maybe not in
  …`; early file with no block → silent (only the missing-block error is
  date-gated, as contracted)
- ledger row pointing at a missing file → `tasks: plan-defects row ev1/R9: no
  such review docs/reviews/…`
- unparsable ledger → `tasks: plan-defects: …/plan-defects.toml unreadable` in
  `check`, `**Record: unavailable**` in the brief
- absent ledger → silent, record 0

One gap, minor 4 below: a block followed by a BLANK line before the H1 makes
`read_reviews` return `{}` and silently skips the verdict rule — `plan_defect:
none` on a REJECTED review passes `check` in that shape.

## The record line

The contracted live numbers, from the clone's own `tasks.py` over the seeded
ledger (the one-repo `--repos` form, because `repos.toml` points every graph at
`~/nixos-agent-env`; the same line comes out of a clone of the live tree with
the ledger dropped in, which is what main will look like once this lands):

```
$ tasks.py --root . --repos <one-repo → the clone> brief --today 2026-09-06 | grep Record
**Record (7 d):** 48 rejections, 45 plan-caused (vacuous 15, missing-case 16, underspecified 8, wrong-fact 6)

$ tasks.py --root <clone of live tree + ledger> --repos <one-repo> brief --today 2026-09-06 | grep Record
**Record (7 d):** 48 rejections, 45 plan-caused (vacuous 15, missing-case 16, underspecified 8, wrong-fact 6)
```

Window and dedup, by hand:

| probe | result |
|---|---|
| the plan's `--today 2026-09-12` fixture (3/1/2/0 + 2 implementer + 2 plan-class secondaries) | `7 rejections, 6 plan-caused (vacuous 3, missing-case 1, underspecified 2, wrong-fact 0)` |
| edges: a row dated exactly 7 d back and one 8 d back | `1 rejections … vacuous 1` |
| a row dated today + 1 | `0 rejections` |
| a ledger row and a block on the same file (classes differ) | `1 rejections … vacuous 1, missing-case 0` — counted once, the block winning |
| unreadable ledger | `**Record: unavailable**` |
| `--today` absent | `_today_utc()` → `2026-09-06`, equal to `datetime.datetime.now(timezone.utc).date()` |
| `--today 2026-13-99` | `tasks brief: error: argument --today: invalid fromisoformat value` , exit 2 |

## Tests and mutants

Fourteen new tests, matching the fourteen cases of Step 1 one for one; eight new
fixtures under `tests/evidence/fixtures/reviews/`; 158 tests pass.

Every one of the plan's eleven named mutants dies against the contracted test
(applied to `pkgs/evidence/tasks.py` or the ledger, run, reverted):

| # | mutant | result |
|---|---|---|
| M1 | `_split_front_matter` always returns `lines[0]` | KILLED (1 failed) |
| M2 | `date > fmf` for `>=` (`tasks.py:972`) | KILLED |
| M3 | block validation skipped on early files (`:977`) | KILLED |
| M4 | `"maybe"` added to `PLAN_DEFECT_ENUM` | KILLED (2 failed) |
| M5 | the REJECTED/`none` arm made unreachable | KILLED |
| M6 | the secondary-equality arm made unreachable | KILLED |
| M7 | secondaries also counted in `counts` | KILLED |
| M8 | ledger rows carrying a secondary skipped | KILLED |
| M9 | `start < date <= today` for `<=` (`:1061`) | KILLED |
| M10 | the `review in block_primary` dedup removed | KILLED |
| M11 | every `plan_defect = "vacuous"` seed row → `underspecified` | KILLED |
| M11b | one seed row (`og4 · OG1r2`) → `underspecified` | KILLED |

Seven mutants of my own, outside the plan's list. Two die; five survive, and
each survivor is a contracted behaviour the plan's fourteen-case list never
asked for a test (all five verified correct by hand above — the gap is
coverage, not conduct):

| # | mutant | result |
|---|---|---|
| E1 | the ledger-row `no such review` arm removed | KILLED (1 failed) |
| E5 | `_review_defect_errors` unwired from `check()` | KILLED (7 failed) |
| E2 | unreadable ledger degrades to `(None, [])` instead of `None` | SURVIVED |
| E3 | the `plan_defect missing` error removed | SURVIVED |
| E4 | the `--today` default frozen to 1970-01-01 | SURVIVED |
| E6 | the `*opus-review*.md` glob widened to `*.md` | SURVIVED |
| E7 | the secondary-outside-the-enum arm removed | SURVIVED |

`mutants_total: 19, mutants_killed: 14, mutants_outside_named: 7`.

## Checks

All from inside the clone.

```
nix develop -c ruff check pkgs/evidence tests/evidence          All checks passed!
nix develop -c ruff format --check pkgs/evidence tests/evidence 43 files already formatted
nix develop -c pytest tests/evidence -q                         158 passed
nix build .#checks.x86_64-linux.evidence-unit -L --rebuild       158 passed
nix build .#checks.x86_64-linux.lint --no-link                   exit 0
nix build .#checks.x86_64-linux.unit -L --no-link                ok 360 …
nix develop -c githooks/pre-commit                               green (see note)
nix develop -c python3 pkgs/evidence/repomap.py --root . write
  git diff --exit-code docs/MAP.md                               MAP REPRODUCES
nix develop -c python3 pkgs/evidence/claims.py validate … --today 2026-09-06  silent, exit 0
```

The hook note: run at HEAD it asks once for `docs/OPERATIONS.md` (the queue
block loses `P3A` and gains `P10` — because P3A's own subject is now in
`git log`). That is a post-commit condition, not an owed board edit: with the
branch's TREE checked out over the BASE's log — exactly what the hook saw at
commit time — `githooks/pre-commit` exits 0 with a clean `git diff --stat`. No
board commit is missing.

The clone's own `tasks.py check` over a copy of the live tree carrying THIS
review file (the first file in the new shape):

```
$ cp docs/reviews/2026-09-06-opus-review-pa7-P3A.md <live copy>/docs/reviews/
$ tasks.py --root <live copy> --repos <one-repo> check
(no output)
exit=0
```

## Red before green

`git show be43169:pkgs/evidence/tasks.py` over this branch's tests: 13 of the
14 new tests fail.

```
$ nix develop -c pytest tests/evidence -q
13 failed, 145 passed in 5.40s
…
tasks: error: unrecognized arguments: --today 2026-09-06
FAILED …::test_read_reviews_reads_line_after_front_matter_block
FAILED …::test_check_requires_block_on_or_after_front_matter_from
FAILED …::test_check_validates_enum_on_early_file_block
FAILED …::test_check_rejects_unknown_plan_defect_value
FAILED …::test_check_rejects_plan_defect_none_on_rejection
FAILED …::test_check_ledger_row_review_must_exist
FAILED …::test_plan_defect_enum_arms_by_verdict
FAILED …::test_check_rejects_secondary_equal_to_primary
FAILED …::test_brief_record_line_counts_and_classifies
FAILED …::test_record_window_is_inclusive
FAILED …::test_brief_record_dedups_ledger_row_with_block
FAILED …::test_brief_record_line_over_seeded_ledger
FAILED …::test_main_brief_accepts_today_option
```

The fourteenth, `test_read_reviews_no_block_still_parses`, passes on main by
design: it is the regression guard that the old shape still parses. Restoring
the branch's `tasks.py`: 158 passed.

## Findings

No majors. Seven minors.

1. **`--today` is not the global the Interfaces line names.**
   `pkgs/evidence/tasks.py:1567` attaches it to the `brief` subparser, so
   `tasks.py --root . --today 2026-09-06 brief` exits 2 with
   `argument command: invalid choice: '2026-09-06'`. The plan's Interfaces
   calls it "a new global option of `tasks.py` … consumed by `brief` only",
   while the plan's own Step 1(5), Step 3 and the acceptance line all write
   `brief --today …`. The implementation followed the usage lines; the
   Interfaces sentence is the outlier.

2. **An approval counts as a rejection in the record.**
   `pkgs/evidence/tasks.py:1038–1053` puts every in-window block into the
   count, whatever its `plan_defect` or its H1 verdict. A single APPROVED file
   carrying `plan_defect: none` yields
   `**Record (7 d):** 1 rejections, 0 plan-caused (…)`. That is literal to the
   plan's counting rule ("ledger rows plus blocks of files dated ≥
   `front_matter_from`"), but from 2026-09-07 every approval inflates the "N
   rejections" figure, which is the number P10 will join to landings.

3. **Five contracted behaviours ship with no test** (the surviving mutants
   E2/E3/E4/E6/E7): the `plan_defect missing` error, the secondary-outside-the-
   enum error, the unreadable-ledger pair (`Record: unavailable` plus one
   `check` error), the UTC default of `--today`, and the restriction of the
   rule to `*opus-review*.md`. All five are named in the plan's Interfaces and
   none appears in its fourteen-case Step 1 list. Each behaves correctly today
   (proved by hand in "The check rule" and "The record line"); a later edit
   would not be caught.

4. **A stray blank line silently deletes a review from the graph.**
   `_split_front_matter` (`pkgs/evidence/tasks.py:211–229`) returns
   `lines[i + 1]` as the H1 line. With a blank line between the closing `---`
   and the H1, `read_reviews` returns `{}` — the review's verdict vanishes from
   the task graph — and `check` reports nothing, so a REJECTED review with
   `plan_defect: none` in that shape passes:
   `none+REJECTED with blank line -> ok (verdict rule silently skipped)`.
   The block shape is contracted ("the H1 follows on the next line"), and every
   review is hand-written, so a shape error should be an error, not silence.

5. **`mutants_total` / `mutants_killed` / `mutants_outside_named` are not
   parsed.** `_split_front_matter` stores every value as a string;
   `mutants_total: banana` is accepted silently. The plan calls them "optional
   ints", so P10 inherits the validation.

6. **The session hook's brief part is now 1,110 of its 1,200-char cap.**
   `tools/session-start.sh:186` (`cap_part BRIEF "$brief" 1200`); the Record
   line is ~103 of those 1,110, leaving 90 chars of headroom. Total hook output
   7,686 of 8,000. One more repo row or a longer next-wave label truncates the
   brief — the same budget class P4 was rejected on.

7. **The commit body's "Live run" is not reproducible as written.** The body
   states `brief --today 2026-09-06` printed the 48/45 line; from the workspace
   that exact invocation prints `0 rejections`, because
   `docs/ledger/repos.toml` points every graph at `~/nixos-agent-env`, which
   has no ledger until this lands. The numbers themselves are right — I
   reproduced them twice (one-repo `--repos` at the workspace, and a clone of
   the live tree with the ledger in place) — and the plain form will print them
   from main.

## Verdict

**APPROVED.** The seed is exact against Appendix B; the parser change breaks no
consumer; the check rule is silent on today's corpus and fires on the boundary;
every named mutant dies; the live record line is byte-exact; every acceptance
check and the lint gate are green; one commit, subject byte-identical, both
trailers, no file outside `touches` but `docs/MAP.md`, which regenerates. Fold
minors 1–6 into the next `tasks.py` task; minor 7 is a commit-body wording note
only.
