---
plan_defect: implementer
plan_defect_secondary: missing-case
mutants_total: 9
mutants_killed: 3
mutants_outside_named: 4
---
# Opus gate — seat run sh2f, task SH3b — REJECTED

## Summary

The fix works. Every behaviour the sh2 gate's MAJOR-1 broke is closed at all four sites, and
I reproduced the reviewer's three demonstrations independently — the function, the hook and
the driver — and all three now answer correctly. `local -` is honoured by the devShell's bash
(5.3.15, ≥ 4.4) and `set -f` leaks on no return path, including the unreadable-file path. A
path that genuinely contains a glob character is one token: the driver records
`touches_files: x*.txt` and never the `xy.txt` sitting in its own cwd. The two untested
contracts of MINOR-4 and MINOR-5 are now pinned and their mutants die. `unit`,
`evidence-unit` and `lint` are green at `--rebuild`; `docs/MAP.md` regenerates clean; `tasks
check` is silent; the subject is byte-identical; one commit; every file in the diff is inside
`touches` plus `docs/MAP.md` by the standing rule; the commit body pastes both the reds and
the greens, and every paste I re-ran reproduced byte for byte, line numbers included.

It fails on one thing, and it is a coverage claim the section made explicitly. Item 1's third
named mutant — `put for p in $extra back with a path that contains *` — **survives**. No
fixture in the branch carries a path with a glob character, so two of the four sites the fix
touched (`factory-task`'s extra loop and `factory-commit-msg.sh`'s three loops) are changed
but unpinned: reverting either to the SH3 idiom leaves all 34 bats tests and all 420 pytest
tests green. The code is right; nothing holds it there. Step 4 required the mutants of item 1
"applied, shown red, reverted — pasted"; the body pastes one of the three and drops this one
silently. That is the same failure mode that produced this fix round, left half-pinned.

One MAJOR, four MINORs.

## Contract items

The section's four numbered items, taken literally.

| # | contract | file:line | verdict |
|---|---|---|---|
| 1a | `factory_disclosed` tokenises with `read -ra` under a function-local `set -f`, restored on every return path | `tools/factory/seat/factory-lib.sh:621-642` (`local -` `:628`, `set -f` `:629`, `read -r -a tokens` `:633`) | **met** — evidence below |
| 1b | the three `for … in $unquoted` loops become `while IFS= read -r` over newline-separated lists | `factory-task:378-395`, `factory-commit-msg.sh:44-49,56-59,62-65,67-70` | met in the code; **unpinned by any test — MAJOR-1** |
| 1c | row 6 gains the `*` and `ex*.txt` bodies with a file named `extra.txt` in the test's cwd | `tests/unit/94-seat-harness.bats:480-492` | met (both assert exit 1) |
| 1d | row 7 gains (b′): the same staged extra, body `Deviation: * — everything`, from a cwd holding `extra.txt` → exit 1, commit refused | `tests/unit/94-seat-harness.bats:541-554` | met |
| 1e | rows 9/10 gain a driver run from a cwd holding `extra.txt` → `touches_disclosed: 0`, `status=partial`, `error_class: touches-violation` | `tests/unit/94-seat-harness.bats:838-854`, fixture mode `glob` at `:752-757` | met |
| 2 | MINOR-4: a result with `touches_extra: 0` carries no `touches_files:` line | guard `factory-task:480-482`; test `94-seat-harness.bats:878`, `:891` | met (mutant dies) |
| 3 | MINOR-5: a queue-block-only board change → `touches_extra: 0`; a prologue line → `touches_extra: 1` with `docs/OPERATIONS.md` in `touches_files` | specs passed at `factory-task:374`; tests `:882-893` and `:895-908`; fixture modes `board`/`board-prologue` at `:764-773` | met (mutant dies) |
| 4 | MINOR-1: the body pastes the reds of items 1–3, the mutants red and reverted, and the greens | `git log -1` body | **partly met** — the greens and two mutants are pasted; item 1's third named mutant is not (MINOR-1 below) |

The prior review's items, one by one:

- **MAJOR-1 — closed.** All three of the reviewer's demonstrations re-run against this branch:

  *Direct*, cwd holding `extra.txt` and `other.txt`:
  ```
  msg  (Deviation: * — everything)     -> 1
  msg2 (Deviation: ex*.txt — glob)     -> 1
  msg3 (Deviation: extra.txt — real)   -> 0
  msg4 (Deviation: `extra.txt` — bt)   -> 0
  msg5 (Deviation: extra.txt, — comma) -> 0
  msg6 (Deviation: extra.txt.bak)      -> 1
  ```
  and the option state is untouched on every path:
  ```
  noglob before:                 set +o noglob
  noglob after return-0 path:    set +o noglob
  noglob after return-1 path:    set +o noglob
  noglob after unreadable path:  set +o noglob
  glob still works: extra.txt other.txt
  ```
  A path spelled with a glob is literal and self-disclosing only:
  ```
  literal-glob-path (weird*name.txt vs its own body) -> 0
  extra.txt vs the weird*name.txt body               -> 1
  ```

  *Through the hook*, contract `src`, staged extra `extra.txt`, worktree root holds `extra.txt`:
  ```
  $ git commit -m "work" -m "Deviation: * — everything"
  commit-msg: 1 file(s) outside this task's touches:
    extra.txt
  Add one line per file to the commit body, exactly this form, then the reason:
  Deviation: extra.txt — <why this task needs it; …>
  The driver recomputes this from the branch after you exit; --no-verify does not change the record.
  rc=1
  commits before=1 after=1
  ```
  `Deviation: ex*.txt — glob` likewise rc=1; `Deviation: extra.txt — fixture` rc=0 and the
  commit lands.

  *Through the driver*, `94-seat-harness.bats:838` runs `factory-task` from a cwd holding a
  file called `extra.txt` against a branch whose body is `Deviation: * — everything`, and
  asserts `FACTORY-RESULT status=partial exit_code=0`, `touches_extra: 1`,
  `touches_disclosed: 0`, `error_class: touches-violation`, rc 1. Green here and in the
  sandbox (`ok 522`). The verdict no longer depends on the driver's cwd.

- **MINOR-4 — closed** (item 2 above; mutant kills at `:878` and `:891`).
- **MINOR-5 — closed** (item 3 above; mutant kills at `:902`).
- **MINOR-1 — mostly closed**: the greens are pasted and all five reproduce (below); one of
  item 1's three named mutants is missing from the paste (MINOR-1 here).
- **MINOR-2 / MINOR-3** were recorded by the plan as the plan's own and not owed; unchanged.

Self-check against its own contract: `tasks.py touches <plan> SH3b` prints the 15 entries; the
diff against base names those 15 plus `docs/MAP.md`. Nothing outside; no `Deviation:` owed.

## Red before green

Two ways, both reproduced in the clone.

**(a) The base's implementation files against the branch's tests.** `factory-lib.sh`,
`factory-task`, `factory-ws`, `factory-integrate`, `tasks.py`, `streams.py`,
`ingest_result.py` checked out at `ed1233b`, `factory-commit-msg.sh` deleted:

```
bats tests/unit/94-seat-harness.bats  -> 26 of 34 not ok, including
  not ok 12 factory_disclosed matches a token, not a substring
  not ok 15 the commit-msg hook refuses a glob body that names no path (b')
  not ok 27 a glob body names no path: the extra stays undisclosed from any driver cwd
  not ok 29 docs/MAP.md alone is exempt from touches
  not ok 30 a queue-block-only docs/OPERATIONS.md change is exempt at the driver
  not ok 31 a docs/OPERATIONS.md prologue change is an extra at the driver
pytest tests/evidence -q -> 17 failed, 403 passed, 1 skipped
```
Restored: `bats … 94` → 34/34 ok; `pytest tests/evidence -q` → 420 passed, 1 skipped.

**(b) The SH3 idiom put back on this tree** — the honest red for the new assertions, and
exactly the three the commit body pastes, at the same line numbers:

```
not ok 12 factory_disclosed matches a token, not a substring
# (in test file tests/unit/94-seat-harness.bats, line 489)
#   `[ "$status" -eq 1 ]' failed
not ok 15 the commit-msg hook refuses a glob body that names no path (b')
# (in test file tests/unit/94-seat-harness.bats, line 551)
#   `[ "$status" -eq 1 ]' failed
not ok 27 a glob body names no path: the extra stays undisclosed from any driver cwd
# (in test file tests/unit/94-seat-harness.bats, line 849)
#   `[ "${lines[0]}" = "FACTORY-RESULT status=partial exit_code=0" ]' failed
```

The body's other two pastes reproduce byte for byte too: mutant item 2 → `not ok 29 …
line 878`; mutant item 3 → `not ok 31 … line 902`.

No test added by this commit is vacuous: each of the four new `@test`s and both extended
assertions is killed by at least one mutant above.

## Mutants

**Named by the section: 5 applied, 2 killed, 3 survived.**

| # | mutant (section's words) | result |
|---|---|---|
| N1 | item 1: "put the unquoted `for token in $line` back" | **survived — equivalent.** `set -f` remains, so the unquoted split still performs no pathname expansion. 34/34 ok. |
| N2 | item 1: "drop the `set -f`" | **survived — equivalent.** `read -r -a` remains, and `read -a` splits on IFS only. 34/34 ok. |
| N3 | item 1: "put `for p in $extra` back with a path that contains `*`" | **survived — not equivalent. MAJOR-1.** |
| N4 | item 2: "always write the line" (`if true` for `[ "$touches_extra" -gt 0 ]`) | killed: `not ok 29` line 878, `not ok 30` line 891 |
| N5 | item 3: "compare `HEAD HEAD`" at `factory-task:374` | killed: `not ok 31` line 902 |

N1 and N2 are a matched pair: the implementation defends twice (globbing off **and** a
splitter that never globs), so neither half alone changes behaviour for any input. That is
strictly safer than an implementation either mutant would break, and an equivalent mutant
cannot be killed by any test — the same call the sh2 gate made for its M14. Recorded as
MINOR-2 (the section's two mutant sentences are false against a belt-and-braces fix), not as
findings against the code. The combined mutant — both halves removed, i.e. the SH3 bug
reapplied — is O1 below and dies loudly.

**Outside the named set: 4 applied, 1 killed, 3 survived.**

- **O1 — the SH3 bug reapplied** (N1 + N2 together): **killed**, `not ok 12`, `15`, `27` —
  the red quoted above. This is the mutant the body actually pasted under "item 1".
- **O2 — `factory-commit-msg.sh`'s four loops back to `for path in $extra` /
  `$undisclosed`: survived.** 34/34 ok. Same root as MAJOR-1.
- **O3 — drop `local -` from `factory_disclosed`, keeping `set -f`** (so noglob leaks to the
  caller for the rest of the driver): **survived.** 34/34 ok. The shipped code is correct — I
  proved no leak directly — but nothing pins it.
- **O4 — the hook joins `undisclosed` with a space instead of `$'\n'`** (which, against the
  `while IFS= read -r` consumers, collapses two undisclosed files into one line and reports
  `n=1`): **survived.** No hook row has two undisclosed files.

## Checks

Run in a fresh clone of `task/SH3b` at `2915c77`.

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass — `ok 529 factory_error_class maps a touches demotion to touches-violation`; rc 0 |
| evidence-unit | `… evidence-unit …` | pass — `421 passed in 11.09s` |
| lint | `… lint …` | pass — `Found 0 warnings and 0 errors.` |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| shellcheck | `nix develop -c shellcheck …/factory-lib.sh …/factory-task …/factory-commit-msg.sh` | rc 0 |
| bats (tree) | `nix develop -c bats tests/unit/94-seat-harness.bats tests/unit/80-seat-driver.bats` | 34 ok + 80 ok = 114 ok, 0 not ok — the body's figure |
| pytest (tree) | `nix develop -c pytest tests/evidence -q` | `420 passed, 1 skipped` |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | clean |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | exit 0, zero bytes |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 **only** on `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`; the regeneration is one line inside the markers (`… SH3b (…)` → `… SH4 (…)`); after `git add docs/OPERATIONS.md`, exit 0. The standing queue-block exemption, identical to the sh2 round. |

Store rule: `94-seat-harness.bats` sets neither `FACTORY_EVIDENCE_CMD` nor `EVIDENCE_STORE`,
so the driver's `factory_ingest_result` (`factory-task:494`) falls through to
`evidence.py … ingest result` whose `--store` defaults to `/var/lib/evidence`
(`pkgs/evidence/evidence.py:31,538`). I checked whether that writes: with `EVIDENCE_STORE`
pointed at an empty temp dir, running the driver row leaves the store directory **not even
created** — the ingest fails and is swallowed into `$log` by design. No row is written to any
store by these tests. Every driver test is synthetic (a `printf` fake on `PATH` via
`fake_seat`); no test reads a real seat log, and `teardown_file` proves `~/factory/runs`
gained no entry.

## Touches and commit

`git diff ed1233b..HEAD --stat` names 16 files. Fifteen are the section's `touches` list
verbatim; the sixteenth is `docs/MAP.md`, in by the standing rule (one line). Nothing outside,
so no `Deviation:` line is owed and none is present. `docs/OPERATIONS.md` is untouched by the
commit; `docs/superpowers/plans/2026-09-07-seat-harness-redesign.md` is untouched.

One commit, `2915c77`, `git rev-list --count ed1233b..HEAD` = 1. The subject is byte-identical
to the section's (`cmp` of `git log -1 --format=%s` against the plan's line 688 string:
identical). The two trailers follow a blank line:
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sh2f)`
and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. No board commit.

Step 1 verified: `git diff FETCH_HEAD..HEAD` against `~/factory/ws/sh2/SH3`'s `task/SH3`
shows the whole of SH3 carried through, with the only source changes being the four fix sites
in `factory-lib.sh`, `factory-task` and `factory-commit-msg.sh` plus the test additions; the
docs differences are main's own advance between the two bases.

## Findings

### MAJOR-1 — the section's third named mutant survives: `factory-task`'s and the hook's loops are changed but pinned by no test

`tools/factory/seat/factory-task:378` and `tools/factory/seat/factory-commit-msg.sh:44,56,62,67`

The section states the contract and the mutant in one breath:

> the three `for p in $extra` / `for path in $undisclosed` loops in `factory-task` and
> `factory-commit-msg.sh` become `while IFS= read -r p` loops over the newline-separated lists
> (a path containing a glob character is one token). … Mutants: … put `for p in $extra` back
> with a path that contains `*` → red.

The code half is done and is correct. The test half is absent: no fixture in
`tests/unit/94-seat-harness.bats` — nor anywhere in `tests/unit` — puts a `*`, `?` or `[` in a
*path*. Applying the mutant exactly as named:

```
-    while IFS= read -r p; do
-      [ -n "$p" ] || continue
+    for p in $extra; do
…
-    done <<<"$extra"
+    done
```
→ `bats tests/unit/94-seat-harness.bats` → **34 ok, 0 not ok.** The same for the hook's four
loops (O2): 34 ok, 0 not ok.

The mutant is not equivalent — it is a live behaviour change the suite cannot see. I wrote the
missing fixture to prove it: a workspace whose extra file is named `x*.txt`, the driver run
from a cwd containing `xy.txt`:

```
@test "GATE-PROBE a path that contains a glob character is one token at the driver" {
  mk_touches_ws globpath          # commits src/a and a file literally named x*.txt
  globcwd=…; printf 'z\n' >"$globcwd/xy.txt"; cd "$globcwd"
  run_task_touches "…status=done…"
  [[ "$output" == *"touches_files: x*.txt"* ]]
  [[ "$output" != *"xy.txt"* ]]
}
```

On this branch: `ok 1`. With the named mutant applied:

```
not ok 1 GATE-PROBE a path that contains a glob character is one token at the driver
#   `[[ "$output" == *"touches_files: x*.txt"* ]]' failed
# FACTORY-RESULT status=partial exit_code=0
# touches_extra: 1
# touches_disclosed: 0
# touches_files: xy.txt
```

The driver records a file that is not on the branch at all, taken from the driver's own
working directory — the very failure MAJOR-1 of the sh2 round was about, at a second site.
The shipped code prevents it; nothing keeps it prevented. Two of the four sites this fix round
exists to correct are therefore free to regress silently, and `factory-task` and the hook are
exactly the arms the section calls "the record".

Step 4 also required "the mutants of item 1 applied, shown red, reverted — pasted". Item 1
names three; the body pastes one (the combined SH3 bug). This mutant is not among them,
which is consistent with it never having been run.

Classification: `implementer` — the seat had the mutant sentence and the parenthetical
contract in the section text it was given, and shipped neither the fixture nor the paste.
Secondary `missing-case`: the section's own **Tests** clause enumerates the rows to extend
("row 6 gains …; row 7 gains (b′); rows 9/10 gain …; row 12 …") and its closing **Tests:**
line lists the discriminating fixtures ("a file in the cwd named like the extra, the `*` and
`ex*.txt` bodies, the prologue line") — neither names a glob-bearing *path*, so the plan's
mutant list demands a row the plan's test list never asks for.

The fix is one fixture: the `globpath` mode and the test above, plus the same shape at the
hook (stage a file named `x*.txt`, assert the refusal names `x*.txt` and not the cwd's
`xy.txt`).

### MINOR-1 — the body pastes one of item 1's three named mutants

`git log -1` body, the "Mutants, shown red then reverted" block. It carries item 1 (as the
whole SH3 bug), item 2 and item 3. Item 1's second and third named mutants are absent. The
second is unrunnable-as-named (MINOR-2); the third is MAJOR-1.

### MINOR-2 — two of the section's named mutant sentences are false against this implementation

`tools/factory/seat/factory-lib.sh:628-633`. The section says "put the unquoted `for token in
$line` back → row 6's `*` case red; drop the `set -f` → the same". Neither is true on its own:
the fix uses both `set -f` and `read -r -a`, and either alone is sufficient, so each single
mutant is behaviourally equivalent (34/34 ok). This is a strictly better implementation than
the one the plan imagined, and there is nothing to fix in the code — but the plan's mutant
sentences are unrunnable as written, and a future gate should apply them as a pair.

### MINOR-3 — `set -f` not leaking to the caller is a stated contract with no test

`tools/factory/seat/factory-lib.sh:628`. The section requires the option "restored on every
return path, e.g. `local -` in bash ≥ 4.4". `local -` is present and works (verified directly:
`set +o noglob` after the return-0, return-1 and unreadable-file paths; devShell bash is
5.3.15). Deleting the `local -` line (O3) leaves every test green.

### MINOR-4 — the hook's undisclosed-list separator is untested for more than one file

`tools/factory/seat/factory-commit-msg.sh:47`. The fix changed the join from `" "` to
`$'\n'` because the consumers became `while IFS= read -r` loops; reverting the separator alone
(O4) leaves every test green, though it would report two undisclosed files as one line with
`n=1`. No hook row stages two undisclosed extras.

## Verdict

**REJECTED.** Behaviourally this round is correct everywhere I could reach it: the sh2 gate's
MAJOR-1 is closed at the function, the hook and the driver, the verdict no longer depends on
the driver's cwd, `local -` and `set -f` behave, MINOR-4 and MINOR-5 are pinned with mutants
that die, and all three acceptance checks are green at `--rebuild`. It is rejected on one
thing: the section's third named mutant for item 1 survives, so the `while IFS= read -r`
change at `factory-task:378` and at the hook's four loops — half the sites this fix round
exists for — is held by no test, and a one-line revert to the SH3 idiom passes the entire
suite while making the driver record a filename taken from its own cwd. The missing fixture is
small and is written out above; Step 4's paste of that mutant is owed with it.
