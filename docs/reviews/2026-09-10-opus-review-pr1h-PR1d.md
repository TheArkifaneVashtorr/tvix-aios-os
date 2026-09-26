---
plan_defect: wrong-fact
mutants_total: 3
mutants_killed: 3
mutants_outside_named: 2
model: opus
---
# Opus gate — seat run pr1h, task PR1d — APPROVED

## Summary

This is the round that lands, so I gated the whole four-deep deliverable and not
only the two lines it adds. The decisive question — does the chain merge green
onto today's `main` — resolves clean, and it resolves by measurement rather than
by argument. Today's `main` is `499c2e4`, which is exactly this branch's base:
nothing has landed since the branch was cut, `git merge refs/remotes/live/main`
reports `Already up to date`, and on the merged tree every one of **803** tracked
paths is owned **exactly once** — `validate --root .` exits 0, and an independent
per-path fnmatch sweep of my own returns `uncovered=0 ambiguous=0`. The
per-row counts sum to 803, equal to the tracked count, which is the partition
property stated as an arithmetic identity rather than as an absence of error
lines. **No uncovered path, no ambiguous path.** The landing blocker PR1c's gate
predicted is gone.

Ownership of `docs/ledger/rules.toml` is *exclusive*, not merely present. One row
and one glob match it (`Evidence` via the literal `docs/ledger/rules.toml`), and
the section's mutant **B** proves the exclusivity from the other side: give the
Factory row the same glob and the validator answers
`ambiguous: docs/ledger/rules.toml (Evidence, Factory)`, by hand and again
through the shipped `subsystems-manifest` check on the real tree.

`--counts` now validates first, and I proved it where it counts rather than only
in a fixture: under mutant **A**, with `docs/ledger/rules.toml` genuinely
uncovered on the real 803-path tree, `validate --root . --counts` prints
`uncovered: docs/ledger/rules.toml` and exits 1 with **no count line** — the same
invocation that under PR1c's code printed nine counts and exited 0. On the clean
manifest it prints one line per row, exits 0, and leaves both
`git status --porcelain` empty and a whole-tree file-listing hash unchanged at
`254699ad43b26a572676ab34ff12fe92`.

Nothing the two predecessor gates approved has regressed. PR1c's property holds
byte for byte: rendered against 803 paths, 806 paths and a one-element list the
page is identical at `md5 0851b317084bfded537c61a73065bd3c` — the *same hash*
PR1c's gate recorded, and the same as the page on disk, so PR1d changed it not at
all. PR1b's two properties hold and are still pinned by live tests: a path
matching two globs of one row validates clean and tallies once, a path matching
two rows still reports both names, and removing the per-row deduplication
(outside mutant **E**) turns `evidence-unit` red on
`test_within_row_overlap_counts_once`. PR1b's amended Interface 1 also survives —
`from tasks import CLASS_GLOB_RE` is the only import from `tasks`, the docstring
says so, and its test is still in the suite; the unrequested "no dependencies"
refusal is absent from both the module and the tests.

The branch carries **one** commit off its base — `54ccde5`,
`git rev-list --count 499c2e4..HEAD` → `1` — and it contains PR1c's content and
PR1d's together: diffed against PR1c's own tip, the only differences on the
chain's files are this round's three (`+1` glob line, the `--counts` reordering,
`+17` test lines). G6's folding rule is satisfied, which is what PR1c's shape
could not claim.

All three acceptance checks are green in a fresh clone under `--rebuild`
(`569 passed`), three further checks outside the list are green, the flake still
evaluates to 61 checks, red before green reproduces independently in both of its
halves, and all three named mutants die with the commit body's own errors. Both
trailers are in policy order with this run's name and the model from this task's
own `.result`, the subject is byte-identical to the section's, and no undeclared
touch survives under G5 — all six changed files are chain `touches` members, and
`docs/OPERATIONS.md` is not touched at all.

**APPROVED.**

## Diff against the section

Fresh clone of `task/PR1d` at `54ccde5`, base `499c2e4` from `PR1d.result`.

```
$ git -C <clone> log --oneline -2
54ccde5 program: Evidence owns the rules ledger and --counts validates before counting (test: subsystems-manifest, evidence-unit, lint)
499c2e4 docs: PR1c's Opus gate filed — APPROVED; type PR1d for the one glob that blocks its landing (test: lint)

$ git -C <clone> rev-list --count 499c2e4..HEAD
1
```

**One commit, folded.** This is what G6 asked for and what PR1c's branch could not
say. The fold is not merely a count — the commit carries PR1c's content as well
as PR1d's. Fetching PR1c's own branch and diffing tree to tree, the only
differences on the chain's files are this round's three edits:

```
$ git -C <clone> fetch /home/dalhaka/factory/ws/pr1g/PR1c task/PR1c:refs/remotes/prev/PR1c
$ git -C <clone> diff --stat refs/remotes/prev/PR1c HEAD -- docs/ledger/subsystems.toml pkgs/evidence/subsystems.py tests/evidence/test_subsystems.py
 docs/ledger/subsystems.toml       |  1 +
 pkgs/evidence/subsystems.py       | 11 +++++------
 tests/evidence/test_subsystems.py | 17 +++++++++++++++++
```

The manifest edit is the one line the Files bullet names, in the Evidence row
beside the ledgers it already lists:

```
@@ -186,6 +186,7 @@ owns = [
   "docs/ledger/task-classes.toml",
   "docs/ledger/task-status.toml",
   "docs/ledger/subsystems.toml",
+  "docs/ledger/rules.toml",
   "docs/ledger/claude-prices.csv",
```

and the module edit is exactly the ordering the section asked for — validate,
print the refusals, refuse, and only then count:

```
     if args.command == "validate":
-        if args.counts:
-            for name, n in counts(text, files):
-                print(f"{name}: {n}")
-            return 0
         errs = validate(text, files)
         for line in errs:
             print(line, file=sys.stderr)
-        return 1 if errs else 0
+        if errs:
+            return 1
+        if args.counts:
+            for name, n in counts(text, files):
+                print(f"{name}: {n}")
+        return 0
```

Nothing else moves. The commit's whole diffstat against the base is the chain's
cumulative content, because the base predates PR1:

```
$ git -C <clone> show --stat --format="" HEAD
 docs/MAP.md                       |   3 +-
 docs/ledger/subsystems.toml       | 255 ++++++++++++++++++++++++++++++++++++++
 docs/subsystems.md                |  13 ++
 flake.nix                         |  21 ++++
 pkgs/evidence/subsystems.py       | 252 +++++++++++++++++++++++++++++++++++++
 tests/evidence/test_subsystems.py | 223 +++++++++++++++++++++++++++++++++
 6 files changed, 766 insertions(+), 1 deletion(-)
```

**Touches.** A fix round's contract is the chain's union, and here the changed
set and the union are the same six files:

```
$ nix develop -c python3 pkgs/evidence/tasks.py touches docs/superpowers/plans/2026-09-09-program.md PR1d
docs/ledger/subsystems.toml
pkgs/evidence/subsystems.py
tests/evidence/test_subsystems.py
flake.nix
docs/subsystems.md
docs/MAP.md

$ git -C <clone> diff --name-only 499c2e4..HEAD
docs/MAP.md
docs/ledger/subsystems.toml
docs/subsystems.md
flake.nix
pkgs/evidence/subsystems.py
tests/evidence/test_subsystems.py
```

Six for six, no seventh. **Neither G5 exemption is needed this round.**
`docs/OPERATIONS.md` is not in the diff at all — the result's note that the queue
block "netted zero diff (already current at HEAD)" is accurate for the moment the
pre-commit ran, and I confirmed the mechanism rather than the claim: regenerating
the block on the committed tree now *does* move it, because the commit itself is
what takes PR1d out of the queue.

```
$ nix develop -c python3 pkgs/evidence/tasks.py --root . write-board ; git status --porcelain
 M docs/OPERATIONS.md
-**Queued …** FIX5 FIX5b FIX5c HH5 HH6 IS1c PR1d (…)
+**Queued …** EV2 FA1 FIX5 FIX5b FIX5c HH5 HH6 IS1c (…)
```

That is the ordinary chicken-and-egg of a derived block — the hook runs before the
commit exists, so it could not have written this — and it gates nothing: the block
is asserted only by the pre-commit hook (`githooks/pre-commit:69`), by no Nix
check (`grep -n 'write-board\|tasks:begin' flake.nix` → empty). The integrator's
own commit regenerates it. Reverted; the clone is clean. `docs/MAP.md` is in the
union on its own account and is current (`repomap.py --root . check` → `EXIT=0`,
and `lint` asserts it below).

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` line (`docs/superpowers/plans/2026-09-09-program.md:812`):

```
$ wc -c subj_commit.txt subj_plan.txt
128 subj_commit.txt
128 subj_plan.txt
$ md5sum subj_commit.txt subj_plan.txt
868c2e218b26ccb198c92661cce786e4  subj_commit.txt
868c2e218b26ccb198c92661cce786e4  subj_plan.txt
$ cmp subj_commit.txt subj_plan.txt && echo IDENTICAL
IDENTICAL
```

`(test: subsystems-manifest, evidence-unit, lint)` equals the `acceptance` list,
and the area prefix is `program:` per G4. Both trailers, in policy order
(`docs/board/policies.md:30-36`):

```
$ git -C <clone> log -1 --format=%B HEAD | tail -2
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pr1h)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `PR1d.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`), the run equal to `pr1h`. Correct. Because the
predecessor was folded rather than replayed, the branch carries one
`Generated-By` and it is this run's — the chain's history lives in the plan and in
these reviews, which is what G6 intends.

**G11.** Every integer the body pastes reproduces. The nine `--counts` values
(`38 53 28 20 106 452 0 103 3`) come back identical below and sum to 803, the
tracked count; `569 passed` is the green count I measured under `--rebuild`; the
two red pastes reproduce byte for byte.

**G9 areas, applied by hand (EV2 has not landed).** PR1d's own four `touches` all
resolve to one subsystem:

```
docs/ledger/subsystems.toml       -> [('Evidence', ['docs/ledger/subsystems.toml'])]
pkgs/evidence/subsystems.py       -> [('Evidence', ['pkgs/evidence/*'])]
tests/evidence/test_subsystems.py -> [('Evidence', ['tests/evidence/*'])]
docs/subsystems.md                -> [('Evidence', ['docs/subsystems.md'])]
```

Single-area, no `**areas:**` owed. The folded commit also carries `flake.nix`
(`-> [('Platform', ['flake.nix'])]`) and `docs/MAP.md` (`-> ['Evidence']`) from
PR1's own section, which predates the manifest it creates; G9 binds "from EV2 on",
so nothing is owed here. Noted below so the crossing is not rediscovered.

**The section's Interfaces, each with its command.**

*Interface 1 — `validate --root .` on the shipped manifest exits 0 with
`docs/ledger/rules.toml` owned by Evidence and by no one else.* Both halves, on
the merged tree, and the second half is the one the section insisted on:

```
$ nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root .
VALIDATE EXIT=0

$ nix develop -c python3 <gate probe: fnmatch every row's owns against the path>
docs/ledger/rules.toml    -> [('Evidence', ['docs/ledger/rules.toml'])]
pkgs/evidence/rules.py    -> [('Evidence', ['pkgs/evidence/*'])]
tests/evidence/test_rules.py -> [('Evidence', ['tests/evidence/*'])]
tracked=803 uncovered=0 ambiguous=0
```

One row, one glob — presence *and* exclusivity, the latter proved again from the
other direction by mutant **B**. The three other files KN1b brought are covered by
Evidence's directory globs, which is why only this one needed a line.

*Interface 2 — `validate --counts` exits 1 and prints no counts when validation
fails; exits 0 and prints one line per row when it passes.* The passing half,
measured with `git status --porcelain` and a whole-tree file-listing hash on both
sides:

```
$ git -C <clone> status --porcelain                       # before: empty
$ find . -path ./.git -prune -o -type f -print | sort | md5sum
254699ad43b26a572676ab34ff12fe92  -
$ nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root . --counts
Isolation: 38
Platform: 53
Helm: 28
Seat/Harness: 20
Factory: 106
Evidence: 452
Generation: 0
Knowledge: 103
Program: 3
COUNTS EXIT=0
$ git -C <clone> status --porcelain                       # after: empty
$ find . -path ./.git -prune -o -type f -print | sort | md5sum
254699ad43b26a572676ab34ff12fe92  -
```

Nine lines for nine rows, exit 0, the tree and its file listing untouched, and all
nine integers equal to the commit body's paste. `38+53+28+20+106+452+0+103+3 =
803`, exactly the tracked count — the exactly-once partition as an identity, which
is a stronger statement than "no error lines were printed".

The failing half I took on the real manifest rather than on a fixture, under
mutant **A**, where `docs/ledger/rules.toml` is genuinely unowned:

```
$ nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root . --counts
uncovered: docs/ledger/rules.toml
COUNTS EXIT=1
```

No count line, exit 1. That same command on PR1c's code, on the same tree, printed
the nine counts and exited 0 — the bug this round closes, shown closed at the
place the operator would meet it. Its fixture is
`test_counts_flag_validates_first`, which pins all three halves (`rc == 1`,
stdout empty, `uncovered: delta/d.txt` on stderr); outside mutant **D** below
shows the stdout half is load-bearing on its own.

**The whole-tree guarantee on today's `main` — the decisive step.**

```
$ git -C /home/dalhaka/nixos-agent-env log --oneline -1 main
499c2e4 docs: PR1c's Opus gate filed — APPROVED; type PR1d for the one glob that blocks its landing (test: lint)

$ git -C <clone> fetch /home/dalhaka/nixos-agent-env main:refs/remotes/live/main
$ git -C <clone> merge-base --is-ancestor 499c2e4 refs/remotes/live/main && echo YES
YES
$ git -C <clone> log --oneline 499c2e4..refs/remotes/live/main
(empty — nothing has landed on main since the branch was cut)

$ git -C <clone> checkout -b gate/merge-main task/PR1d
$ git -C <clone> merge --no-edit refs/remotes/live/main
Already up to date.

$ git -C <clone> ls-files | wc -l                          # merged tree
803
$ git -C /home/dalhaka/nixos-agent-env ls-files | wc -l    # live main
799
$ comm -23 <(git -C /home/dalhaka/nixos-agent-env ls-files | sort) <(git -C <clone> ls-files | sort)
(empty — every path on main is on the merged tree)
```

The merge is a fast-forward because `main` *is* the base; the merged tree is
main's 799 paths plus the four this chain creates. On that tree:

```
$ nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root .
VALIDATE EXIT=0
$ <gate probe, independent fnmatch sweep>
tracked=803 uncovered=0 ambiguous=0
$ nix build <clone>#checks.x86_64-linux.subsystems-manifest -L --no-link --rebuild
checking outputs of '/nix/store/fm0zbj39jdd3alv7g419gfrfc81mvdww-subsystems-manifest.drv'...
EXIT=0
```

**Clean. No uncovered path, no ambiguous path, on today's `main`.** The check the
integrator will run is the one run here, from the committed tree, rebuilt rather
than trusted. And it cannot be perturbed by the operator's untracked files: with
and without an untracked file in the clone the derivation is the same,
`/nix/store/fm0zbj39jdd3alv7g419gfrfc81mvdww-subsystems-manifest.drv`, so
`.msg-ui1.txt` and `docs/research-2026-09-09-bug-workflow-packet.md` cannot turn
it red while they stay untracked.

**PR1c's property survived, byte for byte.** The page is still a function of the
manifest alone, and the hash is the *same one PR1c's gate recorded*, so this round
moved it not at all:

```
$ nix develop -c python3 <gate probe: render against three file lists>
len(a)=803 len(b)=806 len(c)=1
md5(render_a) = 0851b317084bfded537c61a73065bd3c
md5(render_b) = 0851b317084bfded537c61a73065bd3c
md5(render_c) = 0851b317084bfded537c61a73065bd3c
BYTE-IDENTICAL
on-disk docs/subsystems.md md5 = 0851b317084bfded537c61a73065bd3c
'| Paths |' in page: False
```

Three lists — the merged tracked set, that plus three invented paths, and the
one-element `["flake.nix"]` — one hash, equal to the committed page. The Files
bullet's prediction ("only if regeneration changes it: it should not") is met
exactly.

**PR1b's properties survived, and are still pinned.** Within a row, one path
matching two globs is owned once and is not ambiguous; across rows, both names are
still reported:

```
within-row (one row, globs ["alpha/*", "alpha/a.txt"], path alpha/a.txt):
  validate = []
  counts   = [('Alpha', 1)]
cross-row (Alpha owns "alpha/*", Beta owns "alpha/a.txt"):
  validate = ['ambiguous: alpha/a.txt (Alpha, Beta)']
shipped manifest:
  validate(real) = []
```

Not by inspection only: outside mutant **E** removes the per-row deduplication and
`evidence-unit` goes red on `test_within_row_overlap_counts_once`, so the property
is guarded by a live test in `validate` as well as in `counts`. PR1b's other
approved items also stand — `from tasks import CLASS_GLOB_RE` is still the only
import from `tasks` (`subsystems.py:31`, used at `:114`), the docstring still says
so and `test_docstring_describes_the_matcher_used` still guards it, and the
unrequested "no dependencies" refusal is gone from both files
(`grep -c no_dependencies` → `0` in the module and `0` in the tests).

## Red before green

Reproduced in the clone, independently of the commit body, by reconstructing the
state Step 1 describes rather than by trusting the paste. Both reds needed
PR1c's files, which the fold means are not a commit on this branch — so I fetched
PR1c's branch and checked its blobs into the working tree.

RED 1 — the manifest without the new glob, on a tree that carries
`docs/ledger/rules.toml`. Nothing of PR1d's fix is present:

```
$ git -C <clone> checkout refs/remotes/prev/PR1c -- docs/ledger/subsystems.toml pkgs/evidence/subsystems.py tests/evidence/test_subsystems.py
$ grep -c 'rules.toml' docs/ledger/subsystems.toml
0
$ nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root .
uncovered: docs/ledger/rules.toml
EXIT=1
```

Byte-identical to the body's RED 1. Stronger, and this is the form the integrator
would have met: the same failure through the shipped check on the real tree —

```
$ nix build <clone>#checks.x86_64-linux.subsystems-manifest -L --no-link
       Last 1 log lines:
       > uncovered: docs/ledger/rules.toml
CHECK EXIT=1
```

That is `factory-integrate`'s `CHECK subsystems-manifest fail` reproduced exactly,
which is the landing blocker this whole round exists to remove.

RED 2 — PR1c's `--counts` early return with PR1d's new test present, everything
else at HEAD, so the failure is isolated to the one line under test:

```
$ git -C <clone> checkout HEAD -- docs/ledger/subsystems.toml tests/evidence/test_subsystems.py
$ git -C <clone> status --porcelain
M  pkgs/evidence/subsystems.py
$ nix build <clone>#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> >       assert rc == 1
evidence-unit> E       assert 0 == 1
evidence-unit> FAILED tests/evidence/test_subsystems.py::test_counts_flag_validates_first - assert 0 == 1
evidence-unit> 1 failed, 568 passed in 14.00s
CHECK EXIT=1
```

Byte-identical to the body's RED 2, and one failure out of 569 — a discriminating
fixture, not a suite falling over for other reasons. The counts reconcile under
G11: PR1c's suite was `557`, and `568 + 1 = 569`, the green count below and in the
body. `git status --porcelain` was empty after every restore in this review.

## Checks

Fresh clone, `XDG_CACHE_HOME` under the gate scratch directory, `--rebuild` on
every acceptance check so none is a cached echo of the seat's own run — the answer
the `checks_scope: dirty` field asks for, since `flake.nix` and the test file are
both inside the committed range. (Mutant and red runs drop `--rebuild`: a mutated
source is a new derivation, and `--rebuild` refuses one never built.)

| check | command | result |
|---|---|---|
| subsystems-manifest | `nix build <clone>#checks.x86_64-linux.subsystems-manifest -L --no-link --rebuild` | **PASS** — `checking outputs of '…-subsystems-manifest.drv'`, `EXIT=0` |
| evidence-unit | `… evidence-unit -L --no-link --rebuild` | **PASS** — `569 passed in 15.20s`, `EXIT=0` |
| lint | `… lint -L --no-link --rebuild` | **PASS** — `EXIT=0`; every real arm zero (`Found 0 warnings and 0 errors`), `repomap check` silent |
| ledger-unit (not in `acceptance`) | `… ledger-unit -L --no-link` | **PASS** — `59 passed in 1.14s`, `EXIT=0` |
| factory-unit (not in `acceptance`) | `… factory-unit -L --no-link` | **PASS** — `render.test.mjs: all assertions passed`, `plan.test.mjs: all assertions passed`, `EXIT=0` |
| unit (not in `acceptance`) | `… unit -L --no-link` | **PASS** — `EXIT=0`, `grep -c '^unit> not ok'` → `0` |

`569 passed` reproduces the commit body exactly. `checks_scope: dirty` resolves
the same way PR1c's did — it classifies the committed diff
(`factory-task:588-602`), the two named files are the two check-machinery files in
the range, and the warning it raises is discharged by the `--rebuild` runs above.

One line of `lint` output is worth naming so nobody reads it as a failure:
`Found 0 warnings and 1 error.` appears once, from the linter's own negative
fixture (a duplicated key in a one-line test file), followed by
`Finished in 26ms on 1 file`. The arm is a self-test; `lint` exits 0.

The flake still evaluates whole and adds or removes no check:

```
$ nix eval <clone>#checks.x86_64-linux --apply 'cs: { n = builtins.length (builtins.attrNames cs); has = cs ? subsystems-manifest; }'
{ has = true; n = 61; }
```

61 checks, `subsystems-manifest` among them — the same count PR1b's and PR1c's
gates measured.

## Mutants

Applied in the clone, run, restored from pristine copies; the tree ends
`git status --porcelain` empty after each. `mutants_total: 3` counts the section's
Step 4 set; two more were applied outside it.

| # | mutant | named? | outcome |
|---|---|---|---|
| **A** | drop the new glob — remove the single line `"docs/ledger/rules.toml",` from the Evidence row's `owns` | yes (Step 4) | **KILLED** — by hand `uncovered: docs/ledger/rules.toml`, `EXIT=1` (the body's line verbatim); through the shipped check `subsystems-manifest> uncovered: docs/ledger/rules.toml`, `builder failed with exit code 1`; **and** `validate --counts` now refuses too, `uncovered: docs/ledger/rules.toml`, `COUNTS EXIT=1`, no count line — the ordering fix proved on the real manifest |
| **B** | add the same glob to a second row — `"docs/ledger/rules.toml"` inserted into the Factory row's `owns` beside `routing.toml` | yes (Step 4) | **KILLED** — `ambiguous: docs/ledger/rules.toml (Evidence, Factory)`, `EXIT=1`, and the same through the shipped check, `builder failed with exit code 1`. This is the exclusivity proof the section demanded: the ownership is *one* row's, not merely present |
| **C** | restore the early return in `--counts` (PR1c's ordering, reinstated verbatim) | yes (Step 4) | **KILLED** — `evidence-unit` red: `>       assert rc == 1` / `E       assert 0 == 1` / `FAILED …::test_counts_flag_validates_first - assert 0 == 1`, `1 failed, 568 passed in 13.94s`. Matches the commit body verbatim |
| D | `--counts` that validates, refuses with exit 1, **but still prints the counts** | OUTSIDE | **KILLED** — `evidence-unit` red on the *other* assertion: `>       assert out.getvalue() == ""` / `E       AssertionError: assert 'Alpha: 1\nBe...1\nGamma: 1\n' == ''`, `1 failed, 568 passed in 13.92s` |
| E | remove PR1b's per-row deduplication in `validate` (the set comprehension becomes a list) | OUTSIDE | **KILLED** — `evidence-unit` red: `>       assert msgs == []` / `E       AssertionError: assert ['ambiguous: ...lpha, Alpha)'] == []` / `FAILED …::test_within_row_overlap_counts_once`, `1 failed, 568 passed in 13.88s` |

Five for five. The two outside mutants are the ones this round needed. **D**
exists because the section's **C** kills on the exit code, which comes first — on
its own it proves `--counts` refuses, not that it *stops counting*; making the flag
refuse *and* print isolates the second half, and the stdout assertion is what dies.
**E** is the regression probe for the predecessor: PR1c re-pointed
`test_within_row_overlap_counts_once` at `counts`, and I wanted to know whether
`validate`'s own deduplication was still guarded. It is — the test kept its
`assert msgs == []` half, and breaking `validate` alone turns it red.

## Defects

None gating. One plan defect of record and three notes.

**MINOR-1 — plan defect `wrong-fact`: the section's stated reason for splitting
`docs/ledger/` names the wrong owner for one of its two files.** Non-gating; the
fix is unaffected.

The Why says the manifest "splits that directory file by file because Factory owns
`routing.toml` and `task-classes.toml`, so a directory glob would make those
ambiguous", and the seat copied the sentence into the commit body. Half of it does
not reproduce:

```
docs/ledger/routing.toml      -> [('Factory',  ['docs/ledger/routing.toml'])]
docs/ledger/task-classes.toml -> [('Evidence', ['docs/ledger/task-classes.toml'])]
```

`task-classes.toml` sits in the **Evidence** row (`docs/ledger/subsystems.toml:186`),
one line above `task-status.toml` and three above the glob this task adds. The
conclusion still holds — `routing.toml` alone makes a `docs/ledger/*` glob
ambiguous — so the one-line fix is right for the right reason, minus one wrong
name. G11 makes a pasted integer that does not reproduce a MAJOR; this is a pasted
*attribution*, in a Why rather than in a measurement, and it changes no decision,
so I record it as the plan's defect and not as the seat's. *Owed*: nothing in
code; correct the sentence if the section is ever revised.

**MINOR-2 — the next plan file this same plan writes will be uncovered.**
Non-gating today; the concrete instance of PR1c's MINOR-1, now dated.

Factory's `owns` enumerates plan files by date prefix — `2026-09-02*` through
`2026-09-08*`, plus the named `2026-09-09-bugs.md` — and Program owns
`2026-09-09-program.md` by name. Nothing matches a later date:

```
docs/superpowers/plans/2026-09-08-helm-home-1.md -> ['Factory']
docs/superpowers/plans/2026-09-11-new.md         -> []
docs/superpowers/specs/SPEC-PL.md                -> ['Factory']     (docs/superpowers/specs/* is a real glob)
rows 9  globs 154  literal 98
```

`PLAN-PL`, `PLAN-SA` and `PLAN-FA` in this very plan run `plan.js` and produce new
plan files, which will be dated 2026-09-10 or later; each will refuse at integrate
with `uncovered: docs/superpowers/plans/<file>` until a line is added. The specs
directory is already a wildcard, so `SPEC-PL/SA/FA` are safe; it is the plans
directory that is enumerated. This is PR1c's MINOR-1 exactly — 98 of 154 globs
name a single file — but with a date on it, so I raise it from "general form" to a
scheduled event. *Owed*: an orchestrator's decision before wave 4, not a fix round.
Either widen the plans enumeration to `docs/superpowers/plans/*` under one owner
(Factory or Program) with the other's files listed as exceptions, or accept the
one-line cost and say so in the sections that write plan files. Nothing here
blocks PR1d.

**MINOR-3 — a switch is owed when this lands, contrary to PR1's Why.**
Non-gating; nothing breaks without it.

PR1's Why calls the manifest "the first code increment that lands without a
switch". Measured, it changes the system closure, because `pkgs/evidence` is
packaged whole:

```
$ nix build /home/dalhaka/nixos-agent-env#evidence   → /nix/store/y00nysx6…-evidence   (live main)
$ nix build <clone>#evidence                          → /nix/store/mm75rsl6…-evidence   (this branch)
$ nix store diff-closures /nix/store/y00nysx6…-evidence /nix/store/mm75rsl6…-evidence
evidence: 8.3 KiB
$ diff <(ls …-evidence-src-A) <(ls …-evidence-src-B)
> subsystems.py
$ nix-store -q --requisites /run/current-system | grep -c -- '-evidence$'
3
```

One line, one file, 8.3 KiB: `subsystems.py` joins the packaged `evidence`
sources, and `evidence` is in the live system closure, so the toplevel moves. The
consequence is small and entirely benign — the module is not wired to any
`evidence` subcommand, adds no unit, timer or runtime behaviour, and the check
invokes it from the source tree, not from the store — so nothing is broken while
the switch is deferred. It smoke-tests fine from the store path
(`python3 /nix/store/…-evidence/subsystems.py validate … --root .` → `EXIT=0`, its
`from tasks import CLASS_GLOB_RE` resolving against its sibling). *Owed*: the
closure diff at the next switch will carry this line; the section's "without a
switch" sentence is wrong and should not be relied on when the operator plans
switch #28.

**Note — the chain's `touches` union spans two subsystems.** PR1d's own four files
are all Evidence; the folded commit also carries `flake.nix` (Platform) and
`docs/MAP.md` (Evidence) from PR1's section. G9 binds "from EV2 on", and PR1 is
the task that creates the manifest G9 reads, so nothing is owed. Recorded because
once EV2 lands, a section shaped like PR1's will need `**areas:** evidence,
platform` and the refusal will be automatic.

**Step 7 — what lands on `main` with this that no check covers.** One pass, five
questions, all measured; nothing found that gates.

*The files the landing itself adds.* The integrate commit will bring this review
and a board update. Both are owned: `docs/reviews/2026-09-10-opus-review-pr1h-PR1d.md`
→ `['Evidence']`, `docs/OPERATIONS.md` → `['Knowledge']`,
`docs/ledger/task-status.toml` → `['Evidence']`. So the merge commit cannot
reintroduce an `uncovered:` of its own making.

*The operator's untracked files.* `docs/research-2026-09-09-bug-workflow-packet.md`
→ `['Knowledge']`, so committing it is safe. `.msg-ui1.txt` → `[]` — a scratch
message file at the repo root that nobody owns; it is untracked and the check's
derivation is provably indifferent to untracked files (same drv hash with and
without one), so it is harmless where it is, and would refuse the moment anyone
`git add`s it. Worth knowing, not worth a line in the manifest.

*Does the check now depend on anything the chain did not test?* No new derivation
inputs: `subsystems-manifest` still feeds `--files` from
`find ${self} -type f -printf '%P\n'`, and the page half of PR1b's old symlink
question is moot because `render` ignores the file list entirely. The residue is
`validate`'s coverage over a tracked symlink, which would be silently unchecked
rather than falsely refused — the safe direction, unchanged by this round.

*The board block and the queue.* Regenerating it on the committed tree moves one
line (PR1d out, EV2 and FA1 in), and no Nix check asserts it — only the pre-commit
hook does. So a stale block cannot turn the integrate red; the integrator's own
commit fixes it. Measured above and reverted.

*Anything outside `pkgs/evidence/subsystems.py`?* The commit touches no other
module. `ledger-unit`, `factory-unit` and `unit` — all outside the acceptance list,
and `unit` is the check that has bitten this factory before — are green, and the
flake still evaluates to the same 61 checks. `tasks.py` is untouched, and the only
symbol crossing between them is still `CLASS_GLOB_RE`.

## Verdict

**APPROVED.**

This is the round that lands, and the deliverable lands clean. The decisive fact
is measured, not argued: today's `main` is `499c2e4`, which is this branch's own
base, `git merge` reports `Already up to date`, and on the merged tree **every one
of 803 tracked paths is owned exactly once** — `validate --root .` `EXIT=0`, an
independent fnmatch sweep `uncovered=0 ambiguous=0`, the nine per-row counts
summing to 803, and `subsystems-manifest` green from the committed tree under
`--rebuild`. **No uncovered path and no ambiguous path.** The blocker PR1c's gate
recorded as MAJOR-1 is closed by the one line it predicted.

The ownership is exclusive, not merely present. `docs/ledger/rules.toml` matches
one row through one glob, and mutant **B** proves it from the other side with the
message the section demanded — `ambiguous: docs/ledger/rules.toml (Evidence,
Factory)` — by hand and through the shipped check. `--counts` validates first, and
the proof is on the real manifest rather than a fixture: under mutant **A** the
same command that printed nine counts and exited 0 on PR1c's code now prints
`uncovered: docs/ledger/rules.toml` and exits 1 with no count line, while on the
clean manifest it prints one line per row, exits 0, and leaves `git status
--porcelain` empty and the whole-tree hash unchanged at
`254699ad43b26a572676ab34ff12fe92`.

Nothing the predecessors' gates approved has regressed. PR1c's property holds at
the *same hash they recorded* — `0851b317084bfded537c61a73065bd3c` across 803, 806
and one-element file lists, equal to the committed page, so PR1d moved it not at
all. PR1b's within-row deduplication and cross-row reporting both hold and are
still pinned by a live test (outside mutant **E** kills), its amended Interface 1
survives with `CLASS_GLOB_RE` the only import from `tasks` and its docstring test
in place, and the unrequested refusal it removed has not crept back.

The branch carries **one folded commit**, `54ccde5`, `rev-list --count` → `1`,
containing PR1c's content and PR1d's — diffed against PR1c's tip, the only
differences on the chain's files are this round's `+1` glob, the `--counts`
reordering and `+17` test lines. G6 is satisfied where PR1c's shape could not be.
All three acceptance checks are green in a fresh clone under `--rebuild`
(`subsystems-manifest` `EXIT=0`, `evidence-unit` `569 passed`, `lint` `EXIT=0`),
three further checks outside the list are green, the flake still evaluates to 61
checks, red before green reproduces independently in both halves — `uncovered:
docs/ledger/rules.toml` by hand *and* through the shipped check, and `assert 0 ==
1` at `1 failed, 568 passed` — and five mutants died: the section's three plus two
of mine that split assertions the named set merged and that probe the predecessor
for regression. The subject is byte-identical at
`md5 868c2e218b26ccb198c92661cce786e4`, both trailers are in policy order with
this run's name and the model from this task's own `.result`, all six changed files
are chain `touches` members, and neither G5 exemption is even needed — the commit
does not touch `docs/OPERATIONS.md` at all.

It is approved with three notes and none owed before the merge. MINOR-1 is the
plan defect of record (`wrong-fact`): the section's reason for splitting
`docs/ledger/` names Factory as the owner of `task-classes.toml`, which the
Evidence row owns — the conclusion survives on `routing.toml` alone. MINOR-2 dates
PR1c's MINOR-1: the plans directory is enumerated by date prefix through
`2026-09-08*`, so the new plan files `PLAN-PL`, `PLAN-SA` and `PLAN-FA` will write
in this same plan are uncovered by construction and will refuse at their integrate
— an orchestrator's decision before wave 4, not a fix round. MINOR-3 corrects PR1's
"lands without a switch": `subsystems.py` joins the packaged `evidence` sources, so
the closure moves by one line, `evidence: 8.3 KiB`; nothing breaks while the switch
is deferred, but the next closure diff will carry it.
