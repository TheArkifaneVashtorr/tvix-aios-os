---
plan_defect: implementer
plan_defect_secondary: missing-case
mutants_total: 37
mutants_killed: 34
mutants_outside_named: 7
---
# Opus gate — seat run sh2, task SH3 — REJECTED

## Summary

The section is implemented in full and to the letter almost everywhere: `tasks.py touches`,
the four `factory-lib.sh` helpers, the workspace `commit-msg` hook, the driver's post-seat
recompute and demotion, the `touches-violation` arm, the integrator's refusal, and the two
nullable fence fields. All three acceptance checks (`unit`, `evidence-unit`, `lint`) are green
at `--rebuild`; `docs/MAP.md` regenerates clean; `tasks.py check` is silent; every file in the
diff is inside the section's `touches`; the commit subject is byte-identical. Red-before-green
reproduces: with the base's implementation files against the branch's tests, 22 of 30 bats
tests and all four new pytest tests fail with the reds the commit body quotes. All 30 mutants
the section names die, and so do the two field mutants the run cared about most — a seat that
commits with `--no-verify` **and** `-c core.hooksPath=/nonexistent` is still demoted by the
driver's recompute, and `factory-ws` adds `githooks/commit-msg` *beside* the tracked
`githooks/pre-commit` on the real repo (porcelain clean, hooksPath `githooks`), so the lint
gate is not silently removed.

It fails on one thing, and it is the load-bearing one. `factory_disclosed` word-splits the
message line **unquoted and with globbing on**, so a commit body containing a bare `*` — a
token equal to no path at all — makes every top-level extra file read as disclosed. That
defeats the hook and, worse, makes the driver's authoritative count a function of the driver's
own working directory rather than of the branch. One MAJOR, five MINORs.

## Contract items

Every numbered interface of the section, taken literally.

| # | contract | file:line | verdict |
|---|---|---|---|
| 1 | `tasks.py touches <plan> <KEY>`: chain-root union, first-seen order, dedup, trailing `/` stripped, exit 0 / 3 / 2 | `pkgs/evidence/tasks.py:186-215`, dispatch `:1738-1747` | met (rows 1–2 green; M1a/M1b/M1c/M2 all die) |
| 2 | `factory_task_touches <plan> <KEY>` through `factory_py` | `tools/factory/seat/factory-lib.sh:552-555` | met |
| 3 | `factory_touches_covers`: equality or prefix with the `/` boundary, never substring, never glob | `factory-lib.sh:560-572` | met (M3a, M3b die) |
| 4 | `factory_board_confined`: awk cut byte-equal **and** exactly one begin and one end marker in both versions; `git show` failure → 1 | `factory-lib.sh:576-593` | met (M4 dies on the missing-end-marker evasion) |
| 5 | `factory_touches_extra`: uncovered paths in the changed list's order, MAP always exempt, board exempt only when confined | `factory-lib.sh:598-615` | met (M5a, M5b, M5c die) |
| 6 | `factory_disclosed`: 0 when some line, split on whitespace and backticks, has a **token equal to** `<path>` after stripping one trailing `,;.:)`; 1 otherwise | `factory-lib.sh:617-629` | **violated — MAJOR-1** |
| 7 | `factory-ws` (1) hooksPath (2) skip on a tracked `githooks/commit-msg` (3) write + chmod 0755 + exclude (4) `.factory-touches` when `FACTORY_PLAN` and non-empty; porcelain empty after | `tools/factory/seat/factory-ws:116-141` | met (M8a–M8d die; verified against a real clone of this repo — `githooks/` keeps `pre-commit` and `pre-push`, porcelain empty) |
| 8 | `factory-commit-msg.sh` (a) MERGE_HEAD → 0 (b) no `.factory-touches` → 0 (c) `git diff --cached --name-only`, failure → allow line, 0 (d) extra (e) undisclosed collected, unreadable message → allow, 0 (f) refusal text and exit 1 | `tools/factory/seat/factory-commit-msg.sh:17-68` | met behaviourally; (e)'s stderr text differs from the plan's "the same allow line" (MINOR-2); (c)'s branch is unreachable by its own named trigger (MINOR-3) |
| 9 | `factory-task`: recompute after the CR3r block, before `case $status`; counts for every status; demote only a `done` with n > m; notes clause; `status=` rewritten in place; `.result` gains the two counts and `touches_files` when n > 0 | `factory-task:353-405`, `:476-482` | met (M9a, M9b, M11, M12a, M12b die); the `n > 0` condition on `touches_files` is untested (MINOR-4) |
| 10 | `factory_error_class`: `touches)` arm beside `zero-commits \| echo`, before the tail patterns | `factory-lib.sh:135-138` | met (M14b dies) |
| 11 | `factory-integrate`: after the board guard, before the merge; refuse when `extra > disc`; missing file or lines → `logonly` and merge | `factory-integrate:102-120` | met (M13 dies) |
| 12 | `streams.py`: `"touches-violation"` immediately before `"none"`; two nullable-int fields | `streams.py:130`, `:303-304` | met (M15, O7 die) |
| 13 | `ingest_result.py`: `_as_int` of both lines, absent or non-integer → `None` | `ingest_result.py:279-280`, `:327-328` | met (M16a, M16b die) |
| 14 | Consumers: the integrator refusal, the `.result` for the gate, the fields for SH6 | as above | met |

Self-check: run against its own branch, `tasks.py touches <this plan> SH3` prints the 15
entries and `factory_touches_extra . <them> 71763d9 HEAD <the diff>` prints nothing — the
change is inside its own contract.

## Red before green

Base implementation files (`factory-lib.sh`, `factory-task`, `factory-ws`, `factory-integrate`,
`tasks.py`, `streams.py`, `ingest_result.py` at 71763d9; `factory-commit-msg.sh` deleted)
against the branch's tests:

- `bats tests/unit/94-seat-harness.bats` → **22 of 30 not ok**; rows 9–12 as
  `factory_touches_covers: command not found` (exit 127), row 7 as
  `.../factory-commit-msg.sh: No such file or directory`, row 9 as
  `` `[ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]' failed ``.
- `pytest tests/evidence/test_tasks.py -q -k touches` → 2 failed, `argument command: invalid
  choice: 'touches' (choose from 'brief', 'json', 'waves', 'conflicts', 'check', 'write-board')`.
- `pytest tests/evidence/test_streams_policy.py tests/evidence/test_ingest_result.py -q` →
  15 failed, including `test_enum_arms_literal_matches_declared`,
  `test_touches_extra_and_disclosed_are_nullable_ints` and
  `test_touches_result_ingests_touches_counts`.

Restored: `bats tests/unit/94-seat-harness.bats` → 30/30 ok; `pytest tests/evidence -q` →
420 passed, 1 skipped. The three reds the commit body pastes are the reds I reproduced.
No test in the file is vacuous — every added `@test` is killed by at least one mutant,
including row 7(g), for which the section names none (O11).

## Mutants

**Named by the section: 30 applied, 30 killed.** (Row 7's "treat any board change as confined"
is the same one-line edit as row 5's "exempt the whole board"; counted once, killed by both
test 11 and test 19.)

| mutant | killed by |
|---|---|
| row 1 only the key's own section | `assert 'b\nc\n' == 'a\nb\nc\n'` |
| row 1 `key.startswith(root)` | `assert 'a\nb\nc\ne\n' == 'a\nb\nc\n'` |
| row 1 keep the slash | `assert 'a\nb\nc/\n' == 'a\nb\nc\n'` |
| row 2 exit 0 for a missing section | `assert 0 == 3` |
| row 3 drop the `/` boundary / substring | `not ok 9`, `not ok 11` |
| row 4 drop the marker-count rule | `not ok 10` |
| row 5 exempt every `.md` / the whole board / sort | `not ok 11` (and `not ok 19` for the board) |
| row 6 fixed-string substring / exact token only | `not ok 12` |
| row 7 drop MERGE_HEAD / refuse without a contract / drop the disclosure check / drop the refusal | `not ok 16` / `13-18` / `not ok 15` / `not ok 14`, `19` |
| row 8 skip the exclude / skip chmod / overwrite the tracked hook / always write `.factory-touches` | `not ok 21` / `21`,`22` / `23` / `22` |
| row 9/10 demote regardless of disclosure / never demote | `not ok 25` / `not ok 24` |
| row 11 demote every status | `not ok 26` |
| row 12 count MAP / write `touches_extra: 0` without a contract | `not ok 27` / `not ok 28` |
| row 13 `extra -gt 0` | `not ok 29` |
| row 14 the demoted case after the tail patterns | `not ok 30` |
| row 15 declare as `id` | `touches_extra: null not allowed` |
| row 16 default 0 / store `touches_files` | `assert row2["touches_extra"] is None` / `touches_files: undeclared field` |

**Outside the named set: 7 applied, 4 killed, 3 survived.**

- **O1 — the field mutant that matters.** Make the driver's recompute conditional on the
  workspace still carrying `.factory-touches` (i.e. on the hook having been installed):
  **killed** (`not ok 24-28`). And positively: a seat that commits with
  `git -c core.hooksPath=/nonexistent commit --no-verify` on a workspace that *did* have the
  hook is still recorded `FACTORY-RESULT status=partial`, `touches_extra: 1`,
  `error_class: touches-violation`. The enforcing arm is genuinely the driver's.
- **O7** enum arm after `"none"` instead of before: killed (`At index 9 diff: 'none' != 'touches-violation'`).
- **O8** hook reads the worktree diff instead of `--cached`: killed (`not ok 14`, `19`).
- **O11** drop the unreadable-message allow branch: killed (`not ok 20`).
- **O2 — survived.** `factory-task:374` passing `HEAD HEAD` instead of `"$base_sha" "task/$key"`
  to `factory_touches_extra`: no test goes red. The driver's board exemption is a stated
  interface with no test (MINOR-5).
- **O10 — survived.** Printing `touches_files:` unconditionally instead of only when n > 0:
  no test goes red (MINOR-4).
- **M14 — survived, equivalent.** Moving the `touches` arm out of the `case` and to just
  before the first tail pattern: still "before the tail patterns", so behaviour is unchanged
  for every input. Not a defect; the section's actual mutant (after *all* tail patterns) is
  M14b above and dies.

## Checks

Run in the fresh clone of `task/SH3` at 265213d.

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass — `ok 525 factory_error_class maps a touches demotion to touches-violation` |
| evidence-unit | `… evidence-unit …` | pass — `421 passed in 11.14s` |
| lint | `… lint …` | pass — `Found 0 warnings and 0 errors.` |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | clean |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | exit 0, zero bytes of output |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 **only** on `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`; after `git add docs/OPERATIONS.md`, exit 0. Not a lint failure: the derived queue drops SH3 once the commit exists, and the same rev's base (71763d9) is exit 0. This is the standing queue-block exemption and SH2's landing recipe already carried it as `merge: main into task/SH2 (board block and MAP regenerated)`. |

## Touches and commit

`git diff --stat 71763d9..HEAD` names 16 files. Fifteen are the section's `touches` list
verbatim; the sixteenth is `docs/MAP.md`, in by the standing rule (one line, the
`tests/evidence` count 84 → 85). Nothing outside, so no `Deviation:` line is owed and none is
present. `docs/OPERATIONS.md` is untouched; the plan file is untouched.

One commit, `265213d`. Subject byte-identical to the section's (`cmp` against the plan's
string: identical). `git rev-list --count` = 1. The body states the why in a paragraph and
pastes the four reds by test and row. The two trailers follow a blank line:
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sh2)`
and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. The body pastes no green
(MINOR-1).

## Findings

### MAJOR-1 — `factory_disclosed` glob-expands the commit body, so a bare `*` discloses files it never names, and the driver's record depends on the driver's cwd

`tools/factory/seat/factory-lib.sh:617-629`

```
factory_disclosed() {
  local path=$1 file=$2 line token
  [ -r "$file" ] || return 1
  while IFS= read -r line; do
    line=${line//\`/ }
    for token in $line; do          # <- unquoted, and pathname expansion is on
      token=${token%[;,.:)]}
```

The section's contract is equality: "0 when some line of the file, split on whitespace and
backticks, has a token equal to `<path>` after stripping one trailing `,`, `;`, `.`, `:` or
`)`". `for token in $line` performs word splitting **and pathname expansion**; nothing sets
`set -f`. A token that is a glob is replaced by the filenames it matches in the process's
current directory, so a line naming no path at all can make the function answer 0.

Shown directly, with the branch as it stands:

```
$ ls d; cat d/msg
extra.txt
Deviation: * — everything
$ (cd d && . factory-lib.sh; factory_disclosed 'extra.txt' d/msg); echo $?
0
```

Through the hook, on a repo whose contract is `src` and whose staged extra is `extra.txt`,
with a body that names no path:

```
git commit -m "work" -m "Deviation: * — everything"   →  rc=0, the commit lands
```

And through the driver — the arm the section calls the record — the same branch, the same
commit body, run twice from two working directories:

```
from an empty cwd:                              touches_extra: 1   touches_disclosed: 0
from a cwd holding a file called extra.txt:     touches_extra: 1   touches_disclosed: 1
                                                FACTORY-RESULT status=done exit_code=0
```

The second run is not demoted, does not get `error_class: touches-violation`, and would be
merged by `factory-integrate` (`extra == disc`). Two consequences, either of which is
disqualifying for this section:

1. The contract is gameable from the commit body. `Deviation: * — everything`, or the more
   natural `Deviation: docs/*.md — regenerated`, discloses paths the body never names. The
   section exists to make the record ungameable ("the driver recomputes this from the branch
   after you exit; `--no-verify` does not change the record" — the hook's own last line).
2. The record is not a function of the branch. `factory-task` calls `factory_disclosed` with
   its own cwd (`factory-task:385`), so the same branch produces a different
   `touches_disclosed`, a different `status` and a different `error_class` depending on where
   the operator stood when they launched the driver. SH6 will later count these as a measured
   effect.

The same unquoted expansion is in `factory-task:378` (`for p in $extra`) and
`factory-commit-msg.sh:44,55,60,64` (`for path in $extra` / `$undisclosed`), where a tracked
path containing `*`, `?` or `[` would be re-expanded; that is the same root cause and much
rarer in practice, but it is the same one-word fix.

The section's row 6 fixture set (bare token, backticked, comma-trailed, `flake.nix.bak`, empty
message) contains no glob row and no mutant that would have caught this — the same corner the
plan judgement's errata row 11 flags as underspecified for the *leading* side. But the stated
rule is equality of a token, and the code answers 0 where no token equals the path: the seat
violated a contract the brief stated, so this is an implementer defect with the plan's thin
row 6 as the secondary.

### MINOR-1 — the commit body pastes the red but not the green

`git log -1` body. Step 2's requirement (paste the reds) is met; the run's gate asks for the
green too. The greens are reproducible and were green here, so nothing is owed beyond the line.

### MINOR-2 — the unreadable-message allow line is not the line the section names

`tools/factory/seat/factory-commit-msg.sh:29` prints
`commit-msg: message file unreadable; allowing (the driver recomputes touches after the seat
exits)`. The section's bullet (e) says an unreadable message file takes "the same allow line",
i.e. `commit-msg: git diff failed; allowing (…)`. The behaviour (allow, exit 0, an `allowing`
line on stderr) is what row 7(g) asserts and it passes; the wording is better than the plan's.
Recorded, not owed.

### MINOR-3 — the `git diff failed; allowing` branch is unreachable by its named trigger and untested

`tools/factory/seat/factory-commit-msg.sh:35-38`. The section justifies the branch with "(no
HEAD yet)". On the pinned git, `git diff --cached --name-only` succeeds in a repo with no
commits (it diffs against the empty tree), so the hook takes the normal path and correctly
refuses:

```
$ git init; …; git add other.txt; git commit -m "first commit"
commit-msg: 1 file(s) outside this task's touches:
  other.txt
```

The allow branch is therefore dead under the trigger the plan gives it. It is harmless, and it
is the branch the plan judgement's errata row 2 already names as having no test row; the plan
also states the trigger wrongly. Nothing to fix in the code.

### MINOR-4 — the `touches_files` guard is a stated contract with no test

`tools/factory/seat/factory-task:479-481`. The section says the line appears "when n > 0".
Removing the `[ "$touches_extra" -gt 0 ]` guard (mutant O10) leaves every test green.

### MINOR-5 — the driver's board exemption is a stated interface with no test

`tools/factory/seat/factory-task:374` passes `"$base_sha" "task/$key"` as the two specs.
Replacing them with `HEAD HEAD` (mutant O2) leaves every test green: no driver-level row puts
`docs/OPERATIONS.md` in the branch diff, so the queue-block exemption is exercised only
through the hook's `HEAD :` pair. Rows 9–12 would need one more workspace shape.

## Verdict

**REJECTED.** MAJOR-1 stands on its own: the disclosure check answers "disclosed" for files no
commit body names, which lets a seat walk an undisclosed extra past both the hook and the
integrator, and makes the driver's `touches_disclosed` depend on the driver's working
directory rather than on the branch. Everything else in the section is landed, tested and
green, so the fix round is narrow — quote the expansion or disable globbing around it
(`local -; set -f`, or read the tokens with `read -ra`), and add the glob row to
`tests/unit/94-seat-harness.bats`'s `factory_disclosed` test with the mutant "expand tokens as
globs → a bare `*` discloses". The two untested contracts (MINOR-4, MINOR-5) are worth folding
into the same round.
