---
plan_defect: underspecified
mutants_total: 3
mutants_killed: 3
mutants_outside_named: 3
model: opus
---
# Opus gate — seat run pr1d, task PR1b — APPROVED

## Summary

All three of PR1's minors are closed, each pinned by a test that is shown to
fail. The within-row glob overlap is deduplicated in both `validate` and
`render`; the unrequested global "no dependencies declared" refusal and its test
are gone and an absence test stands in their place; the docstring no longer
claims a matcher the code does not call. All three `acceptance` checks are green
in a fresh clone under `--rebuild` (`554 passed`), red before green reproduces
independently, and all three named mutants die with the errors the commit body
pastes — including mutant C's assertion line, which reproduces byte for byte
under the docstring form the seat used.

The MAJOR PR1's gate raised is void, as the section says: `docs/OPERATIONS.md`
is not touched at all in this round, so G5's first standing exemption is not
even called upon. Every one of the six changed files sits inside the chain's
`touches` union.

One thing is not what the section asked for. Interface 1 requires that
`subsystems.py` "calls `tasks.py`'s matching function rather than
re-implementing the call"; the code still calls `fnmatch.fnmatch` directly and
took the section's *other* branch — correct the docstring — which the section
itself offers ("either import and call `tasks.py`'s own matching function, or
correct the docstring and the interface's wording to what the code does"). The
claim is now true and tested, so the minor the gate raised is closed; the
interface's own text is not satisfied, and its second half — "correct … the
interface's wording" — is a plan edit no seat may make (`orchestrator-guard.sh`,
and the plan is not in `touches`). That is a plan defect of class
`underspecified`, recorded as MINOR-1 and owed as one line from the
orchestrator, not as a third round.

The step-7 pass (what could this break that its checks do not cover) found no
behavioural breakage: `tasks.py` is untouched, its CLI and its own users of the
matcher still run, `docs/subsystems.md` regenerates byte-stable from the *other*
file-list source, three checks outside the acceptance list are green, and the
one failure mode I expected — the operator's untracked files entering `${self}`
and turning the new every-path-owned check red on the live tree — is disproved
by measurement.

**APPROVED.**

## Diff against the section

Fresh clone of `task/PR1b` at `0b1829a`, base `4972422` from `PR1b.result`.

```
$ git -C <clone> log --oneline -3
0b1829a program: PR1 fix round — one matcher, per-row glob dedup, the unrequested refusal dropped (test: subsystems-manifest, evidence-unit, lint)
4972422 docs: type PR1b and give G5 the derived-queue-block exemption (test: lint)
43629f6 docs: board — queue block regenerated after IS2 landed (test: lint)

$ git -C <clone> rev-list --count 4972422..HEAD
1

$ git -C <clone> diff --stat 4972422..HEAD
 docs/MAP.md                       |   3 +-
 docs/ledger/subsystems.toml       | 254 ++++++++++++++++++++++++++++++++++++++
 docs/subsystems.md                |  13 ++
 flake.nix                         |  21 ++++
 pkgs/evidence/subsystems.py       | 230 ++++++++++++++++++++++++++++++++++
 tests/evidence/test_subsystems.py | 170 +++++++++++++++++++++++++
 6 files changed, 690 insertions(+), 1 deletion(-)
```

One commit, as Step 5 orders. PR1b is a fresh pass carrying PR1's whole
deliverable plus this round's three fixes, which is why the manifest, the
validator, the check and the page all appear as additions.

**Touches.** A fix round's contract is the chain's union:

```
$ nix develop -c python3 pkgs/evidence/tasks.py touches docs/superpowers/plans/2026-09-09-program.md PR1b
docs/ledger/subsystems.toml
pkgs/evidence/subsystems.py
tests/evidence/test_subsystems.py
flake.nix
docs/subsystems.md
docs/MAP.md

$ git -C <clone> diff --name-only 4972422..HEAD
docs/MAP.md
docs/ledger/subsystems.toml
docs/subsystems.md
flake.nix
pkgs/evidence/subsystems.py
tests/evidence/test_subsystems.py
```

Six changed files, six union members, set-equal. No undeclared touch. G5's two
standing exemptions are not needed: `docs/OPERATIONS.md` does not appear in the
diff at all (the queue-block exemption is unused), and `docs/MAP.md` is named in
the union on its own account (the `repomap.py write` exemption is unused). The
`docs/MAP.md` hunk is exactly what `repomap.py write` produces for one added
check and one added test file — `+ subsystems-manifest` in the check list and
`tests/evidence — 100 files` → `101 files` — and `lint`, which runs
`repomap.py --root . check`, is green below.

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` line (`docs/superpowers/plans/2026-09-09-program.md:666`):

```
$ wc -c subj_commit.txt subj_plan.txt
141 subj_commit.txt
141 subj_plan.txt
$ md5sum subj_commit.txt subj_plan.txt
9d2a8c83b19b87f19f1cd2b4d5e27939  subj_commit.txt
9d2a8c83b19b87f19f1cd2b4d5e27939  subj_plan.txt
$ cmp subj_commit.txt subj_plan.txt && echo IDENTICAL
IDENTICAL
```

`(test: …)` equals the `acceptance` list. Both trailers, in policy order
(`docs/board/policies.md:30-36`):

```
$ git -C <clone> log -1 --format=%B | grep -n "Generated-By\|Co-Authored-By"
43:Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pr1d)
44:Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `PR1b.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`), the run equal to `pr1d`. Correct.

**The prior round's MAJOR, void and correctly not "fixed".**

> major docs/OPERATIONS.md:23 -- write outside the task's stated `touches`: the
> commit removes `IS1` from the derived "Queued" block.

The section declares it void under G5's first standing exemption, and this round
neither touches that file nor reverts a derived block:

```
$ git -C <clone> diff --name-only 4972422..HEAD | grep -c OPERATIONS.md
0
```

The commit body states the finding was a plan defect in one line, as Step 5
requires.

**The prior round's three minors, each quoted and each closed.**

> minor pkgs/evidence/subsystems.py:12,27 -- the docstring claims the matcher
> (`tasks.py`'s `file_class`) "is imported here", but only `CLASS_GLOB_RE` is
> imported and `fnmatch.fnmatch` is called directly … the docstring/commit
> claim is inaccurate.

Closed as a *claim*. PR1's docstring read "The matcher is tasks.py's
(`file_class`, which is `fnmatch.fnmatch`); it is imported here, never copied."
(`git show FETCH_HEAD:pkgs/evidence/subsystems.py`, lines 11-12, fetched from
`~/factory/ws/pr1/PR1`). It now reads:

```
$ sed -n '10,14p' <clone>/pkgs/evidence/subsystems.py
Glob semantics are `task-classes.toml`'s: `*` spans `/`, no `**`, and a glob
must match `tasks.CLASS_GLOB_RE`. Paths are matched with the stdlib
`fnmatch.fnmatch`; the only import from `tasks` is `CLASS_GLOB_RE` — no matcher
is copied from `tasks.py`.
"""
```

which is what the code does:

```
$ grep -n "^from tasks import\|^import fnmatch\|fnmatch.fnmatch\|file_class" <clone>/pkgs/evidence/subsystems.py
12:`fnmatch.fnmatch`; the only import from `tasks` is `CLASS_GLOB_RE` — no matcher
19:import fnmatch
28:from tasks import CLASS_GLOB_RE
130:            {name for (name, glb) in owners if fnmatch.fnmatch(path_, glb)}
146:        for name in {name for (name, glb) in owners if fnmatch.fnmatch(path_, glb)}:
```

`test_docstring_describes_the_matcher_used` pins it in both directions
(`"fnmatch.fnmatch" in sub.__doc__`, `"file_class" not in sub.__doc__`, and
`sub.fnmatch is fnmatch`), and mutants **C** and **c′** below show both
assertions can fail. The interface half of this minor is MINOR-1.

> minor pkgs/evidence/subsystems.py:123-124 -- the "no dependencies declared"
> global refusal (and `test_no_dependencies_refused`) is not in the task's
> `validate` spec; an unrequested rule …

Closed. PR1's `validate` counted `total_edges` and appended
`"no dependencies declared"` at zero; both the counter and the refusal are gone,
and the test is inverted into an absence test:

```
$ grep -n "total_edges\|no dependencies declared" <clone>/pkgs/evidence/subsystems.py
(no matches)

$ grep -n "def test_no_dependencies_refused\|def test_manifest_without_dependencies_is_clean" <clone>/tests/evidence/test_subsystems.py
119:def test_manifest_without_dependencies_is_clean
```

The fixture is the base manifest with every `depends` emptied and
`assert sub.validate(text, base_files()) == []`. Mutant **B** re-adds PR1's
exact rule and kills it. Interface 3 holds: every refusal `validate` still
makes — missing field, duplicate name/prefix/area, unknown gate, no plans, a
glob failing `CLASS_GLOB_RE`, dangling dependency, cycle, uncovered, ambiguous —
is named in PR1's interfaces and carries a fixture in the file.

> minor pkgs/evidence/subsystems.py:131-136,145-149 -- within-row glob overlap
> is not deduplicated: one path matching two globs in the *same* row yields
> `ambiguous: <path> (Name, Name)` and double-counts in `render`.

Closed, in both places (`:130` in `validate`, `:146` in `render`, both now set
comprehensions). Proved with my own fixture, independent of the seat's, which
puts both halves of Interface 2 in one manifest: row **Alpha** owns
`["alpha/*", "alpha/a.txt"]` (two globs of one row matching `alpha/a.txt`),
while row **Beta** owns `shared/*` and row **Gamma** owns `*/s.txt` (two globs
of different rows matching `shared/s.txt`):

```
$ nix develop -c python3 overlap_probe.py <clone>/pkgs/evidence/subsystems.py
validate -> ['ambiguous: shared/s.txt (Beta, Gamma)']
render rows:
    | Alpha | AL | alpha | opus |  | 1 |
    | Beta | BE | beta | sonnet |  | 1 |
    | Gamma | GA | gamma | sonnet |  | 1 |
```

The within-row overlap is counted **once** (`Paths = 1`) and is **not** reported
ambiguous — it does not appear in `validate`'s output at all — while the
cross-row overlap still reports `ambiguous: shared/s.txt (Beta, Gamma)` with
both names, sorted. That is Interface 2, measured on a fixture the seat never
saw.

**The section's Interfaces, each with its command.**

*Interface 1 — one matcher, and the docstring says what the code does.* The
`grep` above is the whole answer: `from tasks import CLASS_GLOB_RE` is the only
import from `tasks`, `file_class` is never called, and `fnmatch.fnmatch` is
called at `:130` and `:146`. Second half satisfied and tested; first half not
satisfied — MINOR-1.

*Interface 2 — within-row overlap counts once and is not ambiguous; cross-row
overlap still reports `ambiguous: <path> (A, B)`.* The `overlap_probe.py` run
above, plus `test_within_row_overlap_counts_once` (which asserts both the empty
`validate` and the `| Alpha | AL | alpha | opus | Beta | 1 |` render row) and
`test_ambiguous_path_refused`. Mutants **A** and **d** kill the two halves
separately.

*Interface 3 — every refusal the validator makes is named in the interfaces and
has a mutant.* The `grep` for `total_edges` is empty, so the one unnamed refusal
is gone; the remaining nine refusals each carry a fixture
(`test_missing_field_refused`, `test_duplicate_prefix_refused`,
`test_duplicate_area_refused`, `test_unknown_gate_refused`,
`test_no_plans_refused`, `test_dangling_depends_refused`, `test_cycle_refused`,
`test_uncovered_path_refused`, `test_ambiguous_path_refused`), and mutant **e**
below shows the shipped `subsystems-manifest` check can actually refuse.

## Red before green

Reproduced in the clone, independently of the commit body, by reverting the
per-row deduplication the fix introduced — the two set comprehensions back to
list comprehensions, which is the pre-fix code and is also the section's mutant
**A**:

```
$ nix develop -c python3 mutate.py A
mutant A applied
$ nix build <clone>#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> E       AssertionError: assert ['ambiguous: ...lpha, Alpha)'] == []
evidence-unit> E         Left contains one more item: 'ambiguous: alpha/a.txt (Alpha, Alpha)'
evidence-unit> FAILED tests/evidence/test_subsystems.py::test_within_row_overlap_counts_once - AssertionError: assert ['ambiguous: ...lpha, Alpha)'] == []
evidence-unit> 1 failed, 553 passed in 14.67s
error: Cannot build '/nix/store/x5v22gjzfwaxp1ws2w6nrh8b3b30j3a0-evidence-unit.drv'.
       Reason: builder failed with exit code 1.
```

That is Step 1's red, byte-identical to the three lines the commit body pastes,
and it is one failure out of 554 — the fixture is discriminating, not a suite
that fails for other reasons. Restored with a pristine copy;
`git status --porcelain` empty after every mutation in this review.

The other two minors carry their own reds, which are mutants **B** and **C**
below: the absence test and the docstring test each fail when the removed rule
or the removed claim comes back. All three reds are therefore reproduced here
without reference to the commit body, and 553 + 1 = 554 reconciles the body's
green count (G11).

## Checks

Fresh clone, `XDG_CACHE_HOME` under the gate scratch directory, `--rebuild` on
every acceptance check so none is a cached echo of the seat's own run. (Mutant
runs drop `--rebuild`: a mutated source is a new derivation, and `--rebuild`
refuses one that was never built.)

| check | command | result |
|---|---|---|
| subsystems-manifest | `nix build <clone>#checks.x86_64-linux.subsystems-manifest -L --no-link --rebuild` | **PASS** — `checking outputs of '…-subsystems-manifest.drv'`, `EXIT=0` |
| evidence-unit | `… evidence-unit -L --no-link --rebuild` | **PASS** — `554 passed in 15.47s`, `EXIT=0` |
| lint | `… lint -L --no-link --rebuild` | **PASS** — `EXIT=0`; every formatter and linter arm zero, `repomap check` silent |
| ledger-unit (not in `acceptance`) | `… ledger-unit -L --no-link` | **PASS** — `59 passed in 1.15s`, `EXIT=0` |
| factory-unit (not in `acceptance`) | `… factory-unit -L --no-link` | **PASS** — `plan.test.mjs: all assertions passed`, `EXIT=0` |
| unit (not in `acceptance`) | `… unit -L --no-link` | **PASS** — `ok 687 now-paragraph accepts the real board's Now paragraph`, `EXIT=0` |

`554 passed` reproduces the commit body exactly, and it is PR1's `552` plus the
two tests this round adds (`test_docstring_describes_the_matcher_used`,
`test_within_row_overlap_counts_once`) with `test_no_dependencies_refused`
replaced in place by `test_manifest_without_dependencies_is_clean`. The flake
still evaluates whole: `nix eval <clone>#checks.x86_64-linux --apply` counts
`61` checks and `subsystems-manifest` is among them (`true`).

## Mutants

Applied in the clone, run, restored from a pristine copy; the tree ends
`git status --porcelain` empty after each. `mutants_total: 3` counts the
section's Step 4 set; three more were applied outside it.

| # | mutant | named? | outcome |
|---|---|---|---|
| **A** | re-introduce the duplicate count: both set comprehensions (`subsystems.py:130,146`) back to lists | yes (Step 4) | **KILLED** — `evidence-unit` red: `FAILED …::test_within_row_overlap_counts_once - AssertionError: assert ['ambiguous: ...lpha, Alpha)'] == []`, `1 failed, 553 passed`. Matches the commit body verbatim |
| **B** | re-add PR1's unrequested global refusal verbatim (`total_edges` counter + `errs.append("no dependencies declared")`) | yes (Step 4) | **KILLED** — `evidence-unit` red: `FAILED …::test_manifest_without_dependencies_is_clean - AssertionError: assert ['no dependencies declared'] == []`, `1 failed, 553 passed`. Matches the commit body verbatim |
| **C** | point the docstring back at a matcher the code does not use — PR1's own wording restored ("The matcher is tasks.py's (`file_class`, which is `fnmatch.fnmatch`); it is imported here, never copied.") | yes (Step 4) | **KILLED** — `evidence-unit` red: `FAILED …::test_docstring_describes_the_matcher_used - AssertionError: assert 'file_class' not in 'The subsyst...er copied.\n'`, `1 failed, 553 passed` |
| c′ | the same claim without the incidental `fnmatch.fnmatch` mention ("The matcher is `tasks.file_class`; it is imported here, never copied.") | OUTSIDE | **KILLED** — `evidence-unit` red: `FAILED …::test_docstring_describes_the_matcher_used - AssertionError: assert 'fnmatch.fnmatch' in 'The subsystem manifest validat...`, `1 failed, 553 passed`. This is the assertion the commit body pastes for **C**, and it reproduces byte for byte |
| d | revert the dedup in `render` **only**, leaving `validate`'s set intact | OUTSIDE | **KILLED** — `evidence-unit` red: `FAILED …::test_within_row_overlap_counts_once - assert '| Alpha | AL | alpha | opus | Beta | 1 |' in …'| AL | alpha | opus | Beta | 2 |…'`, `1 failed, 553 passed`. The fixture pins **both** call sites, not just the one the message came from |
| e | delete one `owns` glob from the shipped manifest (`docs/ledger/subsystems.toml`, Program's `docs/concepts/2026-09-09a-redesign-charter.md`) | OUTSIDE | **KILLED** — `subsystems-manifest` red: `subsystems-manifest> uncovered: docs/concepts/2026-09-09a-redesign-charter.md`, `builder failed with exit code 1`. The new acceptance check is load-bearing on the real tree, not only on fixtures |

Six for six. Mutant **d** is the one worth naming: the section's mutant A
reverts both call sites at once, so on its own it could not distinguish "the
message is fixed" from "the count is fixed". Reverting `render` alone still
dies, on the render assertion inside the same test — Interface 2's two halves
are pinned separately.

## Defects

**MINOR-1 — Interface 1's import half is unmet: `subsystems.py` still calls
`fnmatch.fnmatch`, not `tasks.py`'s matcher.** Plan defect: `underspecified`.
Non-gating.

Interface 1 reads "One matcher: `subsystems.py` calls `tasks.py`'s matching
function rather than re-implementing the call, and the docstring says what the
code does." The code does the second and not the first (`grep` above: `:130`,
`:146`). The section's own prose, however, offers the alternative and the seat
took it: "either import and call `tasks.py`'s own matching function, **or**
correct the docstring and the interface's wording to what the code does. Prefer
the import." The seat disclosed the branch it took in the commit body ("nothing
is copied, so the docstring now says what the code does") and pinned it with a
test and a live mutant, so nothing here is hidden or untested.

Two things make this the plan's defect rather than the seat's. First, the
section offers an option its own Interfaces line forbids — an internal
contradiction of the same shape as the `docs/OPERATIONS.md` one this round was
convened to retire. Second, the offered option's second half, "correct … the
interface's wording", is an edit to
`docs/superpowers/plans/2026-09-09-program.md`, which is neither in `touches`
nor writable by any agent but the orchestrator
(`tools/orchestrator-guard.sh:12-20`) — the plan asked the seat for something it
may not do, so the branch could only ever be half-executed.

The residual technical risk is drift, not a bug: `tasks.file_class` is a loop
over `fnmatch.fnmatch` (`tasks.py:396-401`), so the two agree exactly today, and
`CLASS_GLOB_RE` — the part that decides which globs are *legal* — is genuinely
shared by import. What is not shared is the matching semantics the docstring
asserts ("`*` spans `/`, no `**`"): if `file_class` ever changes, `subsystems.py`
does not, and no test would notice. The import is also the tidier way to get
Interface 2: `tasks.file_class(path, [(r["name"], g) for g in r["owns"]])`
returns the row's name on any of its globs and dedupes per row by construction.

*Owed*: one line from the orchestrator — either correct Interface 1's wording to
what the code does, or type a follow-up that performs the import. Recorded, not
gated: the defect PR1's gate actually named (an inaccurate claim) is closed, the
behaviour is identical, and a third round on a docstring is not worth a wave.

**Step 7 — what this could break that its checks do not cover.** One pass, three
questions, all measured; nothing found that gates.

*`tasks.py`'s own users of the matcher.* `tasks.py` is not in the diff
(`git diff --name-only 4972422..HEAD | grep -c tasks.py` → `0`), and the
dependency runs one way: `subsystems.py` imports `CLASS_GLOB_RE` from it. That
import executes `tasks.py` at module load, so I checked it has no module-level
side effects — the only top-level statement outside definitions and constants is
`if __name__ == "__main__":` at `:2421`. `file_class`, `task_class` and the seat
grouping are untouched, and `tasks.py`'s own CLI still runs in the clone:
`tasks.py --root . check` → `EXIT=0`, and
`tasks.py --root . waves --repo nixos-agent-env --plan 2026-09-09-program.md` →
`EXIT=0`. Nothing else in the tree imports `subsystems.py` or reads
`docs/subsystems.md`: `grep -rn subsystems githooks tools pkgs docs/runbooks`
(excluding the module itself) returns nothing, so the only consumer is the new
check. `ledger-unit`, `factory-unit` and `unit` — all outside the acceptance
list, and `unit` is the check that has bitten this factory before — are green
above.

*Does `docs/subsystems.md` still regenerate byte-stable?* Yes, and from **both**
file-list sources, which is the part the acceptance check alone does not prove.
`subsystems-manifest` feeds `--files` from `find ${self} -type f -printf '%P\n'`,
while a human regenerating the page uses `--root .`, i.e. `git ls-files`. Run
by hand in the clone: `subsystems.py write … --root . --check docs/subsystems.md`
→ `EXIT=0` and `subsystems.py validate … --root .` → `EXIT=0`. The two lists are
equal on this tree (`796` tracked paths; the only difference `find` reports is
`pkgs/evidence/__pycache__/*.pyc`, which my own probe runs created and which
`.gitignore:1` excludes), and the repo has no tracked symlinks
(`git ls-files -s | awk '$1=="120000"'` is empty), which is the one class of
tracked path `find -type f` would silently drop. Worth one line in a future
round if a symlink is ever committed; not a defect today.

*Could the new check go red on the operator's live tree?* This was my main
worry, and it is disproved. `core`'s worktree carries untracked files
(`.msg-ui1.txt`, `docs/research-2026-09-09-bug-workflow-packet.md`), and an
every-path-owned validator fed a superset of the tracked set would refuse them
as `uncovered`. Measured instead of assumed: with an untracked, non-ignored file
present in the clone, the derivation hash does not move —
`nix eval …subsystems-manifest.drvPath` returns
`/nix/store/633ywvvi29g7hjmyjvzjgmpair96kpa6-subsystems-manifest.drv` both with
and without it, and the check builds `EXIT=0`. `${self}` is the tracked set, as
CLAUDE.md's gotcha says, so untracked files cannot make this check red. The
converse holds too and is by design: a *tracked* file no row owns turns
`subsystems-manifest` red, which is mutant **e**.

## Verdict

**APPROVED.**

All three of PR1's minors are closed and each is pinned by a test proved able to
fail: the docstring now describes the matcher the code actually calls
(mutants **C** and **c′**), the unrequested global "no dependencies declared"
refusal and its test are gone with an absence test in their place (mutant
**B**), and the within-row glob overlap counts once in both `validate` and
`render` while cross-row overlap still reports `ambiguous: shared/s.txt
(Beta, Gamma)` (mutants **A** and **d**, plus my own two-sided fixture). All
three `acceptance` checks are green in a fresh clone under `--rebuild`
(`554 passed`), three further checks outside the list are green, red before
green reproduces independently at `1 failed, 553 passed`, all three named
mutants die with the commit body's own errors, one commit, subject
byte-identical at `md5 9d2a8c83b19b87f19f1cd2b4d5e27939`, both trailers in
policy order with the model from `PR1b.result`, and all six changed files sit
inside the chain's `touches` union — `docs/OPERATIONS.md` untouched, so G5's
first exemption is not even needed and the void MAJOR is correctly not "fixed".

It is approved with one recorded plan defect. Interface 1's first half — call
`tasks.py`'s matcher — is unmet; the seat took the section's explicitly offered
alternative, disclosed it, and tested it, and the alternative's second half was
an edit to the plan that no seat may make. The owed correction is one line of
the orchestrator's: bring Interface 1's wording to what the code does, or type a
follow-up that performs the import.
