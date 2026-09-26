---
plan_defect: missing-case
mutants_total: 3
mutants_killed: 3
mutants_outside_named: 2
model: opus
---
# Opus gate — seat run pr1g, task PR1c — APPROVED

## Summary

The fix is right and it is proved on the ground the section names. `render` no
longer emits a `Paths` column and no longer reads the file list at all (`del
files`), so the generated page is a function of `docs/ledger/subsystems.toml`
alone: rendered against three different file lists — 798 tracked paths, 801, and
a single-element list — the output is byte-identical at
`md5 0851b317084bfded537c61a73065bd3c` all three times. The coverage guarantee
survived untouched: `validate` still refuses `uncovered:` and `ambiguous:`, both
measured through the shipped `subsystems-manifest` check on the real tree, not
only on fixtures. `validate --counts` prints one `<name>: <n>` line per row,
exits 0, and leaves `git status --porcelain` empty and the file-listing hash
unchanged. The module docstring no longer advertises the count and now describes
`--counts`.

The decisive end-to-end fact reproduces both ways. With one unrelated tracked
file added (`docs/runbooks/zzz-gate-probe.md`, which moves Knowledge's owned
count 103 → 104), `subsystems-manifest` on PR1c's code is **green**; with the
same file present and PR1b's module and page checked out in its place, the same
check is **red** with the exact message this task exists for —
`subsystems: docs/subsystems.md is stale`. That is the tax removed, measured on
the real repository rather than argued.

All three `acceptance` checks are green in a fresh clone under `--rebuild`
(`557 passed`), three further checks outside the list are green, red before green
reproduces independently at `1 failed, 554 passed` byte-for-byte, and all three
named mutants die with the errors the commit body pastes. Both commits carry both
trailers in policy order; PR1c's subject is byte-identical to the section's at
`md5 b84a1ceac97311fa29112043cbda396a`.

**The `checks_scope: dirty` question resolves clean, and the premise behind it is
wrong.** `checks_scope` is not a statement about the working tree. It is a static
classification of the *committed* diff (`factory-task:588-602`): "dirty when the
diff touches `flake.nix`, `tests`, or `githooks`" — a scope warning that the task
changed the machinery the checks run on, so a green check is not fully
independent evidence. The two named files are exactly the two check-machinery
files in `0f58f81..task/PR1c`, and both arrive from the cherry-picked PR1b
commit, not from PR1c's own. Nothing was left uncommitted: the seat workspace is
`git status --porcelain` clean against `HEAD` apart from an untracked `.scratch/`
the seat used for its own mutation copies. The commit and the tested tree do not
differ, in those two files or any other. No MAJOR here.

The two-commit shape is safe to land. Both subjects are their own sections'
verbatim, both bodies carry their own run's `Generated-By`, and `0f58f81` is an
ancestor of live `main`, so merging the branch brings PR1b and PR1c to `main`
together, which is the intended outcome. G6 has since been amended to require
folding; the ambiguity is the plan's and is not re-punished here.

One measured finding the integrator must act on before the merge, and it is not
PR1c's doing: `docs/ledger/rules.toml` landed on `main` with KN1b *after* this
branch was cut, and no row's `owns` glob covers it, so
`subsystems-manifest` will refuse `uncovered: docs/ledger/rules.toml` at
integrate. One glob line in a file already inside the chain's `touches` fixes it.
Recorded as MAJOR-1 below with the reasoning for why it does not gate PR1c.

**APPROVED.**

## Diff against the section

Fresh clone of `task/PR1c` at `df7147a`, base `0f58f81` from `PR1c.result`.

```
$ git -C <clone> log --oneline -3
df7147a program: the subsystems page drops its path count so the check stops going stale on unrelated commits (test: subsystems-manifest, evidence-unit, lint)
ed0f519 program: PR1 fix round — one matcher, per-row glob dedup, the unrequested refusal dropped (test: subsystems-manifest, evidence-unit, lint)
0f58f81 docs: type PR1c — the subsystems page drops its path count (test: lint)

$ git -C <clone> rev-list --count 0f58f81..HEAD
2
```

Two commits, not the one Step 5 orders and the one `PR1c.result` claims — which
is why `factory-task:757` demoted the run to `status=failed`. The orchestrator
has accepted that as a plan defect of its own (G6 did not say whether a fix round
folds its predecessor's cherry-pick; PR1b's seat folded, PR1c's did not) and G6
now requires folding. I record the shape and judge the content.

The shape is sound. `ed0f519` is `git cherry-pick` of PR1b's own commit — the
reflog in the workspace shows `HEAD@{1}: cherry-pick`, and its subject and body
are PR1b's verbatim, including PR1b's `Generated-By … factory run pr1d`. It was
gated APPROVED on 2026-09-10 (`docs/reviews/2026-09-10-opus-review-pr1d-PR1b.md`)
and its content is unchanged here. `df7147a` is PR1c's own work and nothing else.
Landing both is how PR1b and PR1c reach `main` together, and `0f58f81` is an
ancestor of live `main`:

```
$ git -C /home/dalhaka/nixos-agent-env merge-base --is-ancestor 0f58f81 main && echo YES
YES
```

The two commits' own diffstats:

```
$ git -C <clone> show --stat --format="" ed0f519      # the cherry-picked PR1b
 docs/MAP.md                       |   3 +-
 docs/ledger/subsystems.toml       | 254 ++++++++++++++++++++++++++++++++++++++
 docs/subsystems.md                |  13 ++
 flake.nix                         |  21 ++++
 pkgs/evidence/subsystems.py       | 230 ++++++++++++++++++++++++++++++++++
 tests/evidence/test_subsystems.py | 170 +++++++++++++++++++++++++
 6 files changed, 690 insertions(+), 1 deletion(-)

$ git -C <clone> show --stat --format="" df7147a      # PR1c's own
 docs/OPERATIONS.md                |  2 +-
 docs/subsystems.md                | 22 +++++++++----------
 pkgs/evidence/subsystems.py       | 41 +++++++++++++++++++++++++---------
 tests/evidence/test_subsystems.py | 46 ++++++++++++++++++++++++++++++++++-----
 4 files changed, 84 insertions(+), 27 deletions(-)
```

**Touches.** A fix round's contract is the chain's union:

```
$ nix develop -c python3 pkgs/evidence/tasks.py touches docs/superpowers/plans/2026-09-09-program.md PR1c
docs/ledger/subsystems.toml
pkgs/evidence/subsystems.py
tests/evidence/test_subsystems.py
flake.nix
docs/subsystems.md
docs/MAP.md

$ git -C <clone> diff --name-only 0f58f81..task/PR1c
docs/MAP.md
docs/OPERATIONS.md
docs/ledger/subsystems.toml
docs/subsystems.md
flake.nix
pkgs/evidence/subsystems.py
tests/evidence/test_subsystems.py
```

Six of the seven are union members. The seventh, `docs/OPERATIONS.md`, is G5's
first standing exemption and the diff is confined to the derived queue block —
one line, between the `<!-- tasks:begin -->` and `<!-- tasks:end -->` markers,
nothing else in the file:

```
$ git -C <clone> show df7147a -- docs/OPERATIONS.md | grep -c '^@@'
1
-**Queued …** FIX5 FIX5b FIX5c HH5 HH6 IS1c KN1 KN1b PR1c (…)
+**Queued …** EV2 FA1 FIX5 FIX5b FIX5c HH5 HH6 IS1c KN1 KN1b (…)
```

That is the G8c-forced regeneration G6 orders — PR1c leaves the queue and EV2 and
FA1 enter it — and it is machine-written, not board prose. Declared under G5. The
second exemption (`docs/MAP.md`) is not needed: the file is in the union on its
own account, and PR1c's own commit does not touch it at all. No undeclared touch.

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` line (`docs/superpowers/plans/2026-09-09-program.md:780`):

```
$ wc -c subj_commit.txt subj_plan.txt
151 subj_commit.txt
151 subj_plan.txt
$ md5sum subj_commit.txt subj_plan.txt
b84a1ceac97311fa29112043cbda396a  subj_commit.txt
b84a1ceac97311fa29112043cbda396a  subj_plan.txt
$ cmp subj_commit.txt subj_plan.txt && echo IDENTICAL
IDENTICAL
```

`(test: subsystems-manifest, evidence-unit, lint)` equals the `acceptance` list,
and the area prefix is `program:` per G4. Both trailers, in policy order
(`docs/board/policies.md:30-36`), on both commits:

```
$ git -C <clone> log -1 --format=%B df7147a | grep -n "Generated-By\|Co-Authored-By"
71:Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pr1g)
72:Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>

$ git -C <clone> log -1 --format=%B ed0f519 | grep -n "Generated-By\|Co-Authored-By"
43:Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pr1d)
44:Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `PR1c.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`), the run equal to `pr1g`; the cherry-picked
commit keeps `pr1d`, which is correct — it is PR1b's commit, made in PR1b's run.
`ed0f519`'s subject is byte-equal to PR1b's own section line (`:666`). Correct.

**The `checks_scope: dirty` field, resolved.** The result records
`checks_scope: dirty`, `checks_scope_files: 2`,
`checks_scope_list: flake.nix tests/evidence/test_subsystems.py`. Read at the
source, this is not a working-tree statement:

```
$ sed -n '588,602p' tools/factory/seat/factory-task
    # checks_scope: dirty when the diff touches flake.nix, tests, or githooks.
    if [ -n "$base_sha" ]; then
      scope_roots=$(mktemp -p "$runs_dir" ".scope-$key.XXXXXX")
      printf 'flake.nix\ntests\ngithooks\n' >"$scope_roots"
      checks_scope=clean
      …
      done < <(git -C "$ws" diff --name-only "$base_sha..task/$key" 2>/dev/null || true)
```

The input is `git diff --name-only "$base_sha..task/$key"` — the **committed**
range — filtered against three roots. It flags that the task changed the check
machinery itself, so a green check is not fully independent evidence; it says
nothing about uncommitted work. Two files in the range match those roots
(`flake.nix`, `tests/evidence/test_subsystems.py`), both from the cherry-picked
PR1b commit; `checks_scope_files: 2` reconciles exactly.

The other half of the question — whether anything was left uncommitted in those
two files — is answered directly in the workspace, and the answer is no:

```
$ git -C /home/dalhaka/factory/ws/pr1g/PR1c status --porcelain
?? .scratch/
$ git -C /home/dalhaka/factory/ws/pr1g/PR1c diff HEAD --stat
(empty)
```

`.scratch/` is the seat's own untracked working directory (`commit-msg.txt`, a
`cache/`, a `mutc/` holding its mutant copies); it contains no tracked file and
no source. The commit and the tree the seat tested are the same tree. And the
scope warning the field exists to raise is answered by this review's own
`--rebuild` runs below, which rebuild the acceptance checks *from the committed
tree* rather than trusting the seat's or the driver's build. No defect.

**The section's Interfaces, each with its command.**

*Interface 1 — `write` produces a page that is a function of
`docs/ledger/subsystems.toml` alone; two runs over different file lists produce
byte-identical output.* Measured against the real manifest with three different
file lists (my own probe, independent of the seat's fixtures):

```
$ nix develop -c python3 probe1.py <clone>/pkgs/evidence/subsystems.py
len(a)=798 len(b)=801
md5(render_a)= 0851b317084bfded537c61a73065bd3c
md5(render_b)= 0851b317084bfded537c61a73065bd3c
BYTE-IDENTICAL
md5(render_one_file)= 0851b317084bfded537c61a73065bd3c IDENTICAL
counts(a)[5]= ('Evidence', 447)  counts(b)[5]= ('Evidence', 449)
```

Three lists — every tracked path, that plus three invented ones, and the
one-element list `["flake.nix"]` — one hash. The last line is the other half of
the property: the *counts* still move with the file list, so the number is not
lost, it is merely no longer written into a tracked file. In the code this is not
an accident of the current manifest: `render` opens with `del files`, so the
parameter cannot be read at all.

*Interface 2 — `validate` is unchanged; an uncovered or ambiguous path still
refuses.* Both halves, on the real manifest:

```
validate(real) = []
validate(uncovered) = ['uncovered: zzz-nobody-owns-this.txt']
validate(ambiguous) = ['ambiguous: flake.nix (Isolation, Platform)']
```

and both again through the shipped check on the real tree as mutants **C** and
**D** below, which is the stronger statement — the guarantee is live in
`subsystems-manifest`, not only in unit fixtures.

*Interface 3 — `validate --counts` prints one `<name>: <n>` line per row and
exits 0 without writing.* Measured with a `git status --porcelain` and a whole-
tree file-listing hash on both sides:

```
$ git -C <clone> status --porcelain                       # before: empty
$ find . -path ./.git -prune -o -type f -print | sort | md5sum
ecbeaa8d5f39e688a2948fd751c7f347  -
$ nix develop -c python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root . --counts
Isolation: 38
Platform: 53
Helm: 28
Seat/Harness: 20
Factory: 106
Evidence: 447
Generation: 0
Knowledge: 103
Program: 3
EXIT=0
$ git -C <clone> status --porcelain                       # after: empty
$ find . -path ./.git -prune -o -type f -print | sort | md5sum
ecbeaa8d5f39e688a2948fd751c7f347  -
```

Nine lines for nine rows, exit 0, the working tree untouched and the file listing
hash unchanged. All nine integers reproduce the commit body's paste exactly
(G11), including `Evidence: 447` — the value that was `445` on the page PR1b
generated, which is precisely the volatility this task removes.

*Files bullet 1, the docstring.* Corrected, and it now documents the new flag:

```
$ sed -n '4,11p' <clone>/pkgs/evidence/subsystems.py
path must match exactly one row's `owns` globs (0 matches -> "uncovered", 2+
-> "ambiguous"). `subsystems.py write` regenerates `docs/subsystems.md` (a
table: subsystem, prefix, area, gate, depends) and, under `--check`, exits 1
when the on-disk page differs; the page is a function of the manifest alone,
never of the file list, so it does not go stale when unrelated files land.
`subsystems.py validate --counts` prints one `<name>: <n>` owned-path line per
row to stdout and writes nothing.
```

"path count" is gone from the table description. Satisfied by inspection; no test
pins this half — MINOR-3.

**The end-to-end fact, both directions.** This is the claim the whole task rests
on, so I measured it as a controlled pair rather than inferring it from the unit
tests. One unrelated file added and tracked (`docs/runbooks/zzz-gate-probe.md`,
owned by Knowledge, moving its count 103 → 104 — exactly the kind of commit that
used to turn the page stale):

```
# PR1c's code, extra file present
$ nix build <clone>#checks.x86_64-linux.subsystems-manifest -L --no-link
building '/nix/store/x17g35r4m7g55q81gswcks4y36qqzdvm-subsystems-manifest.drv'...
EXIT=0

# PR1b's module and page checked out in place, the SAME extra file present
$ git -C <clone> checkout ed0f519 -- pkgs/evidence/subsystems.py docs/subsystems.md
$ nix build <clone>#checks.x86_64-linux.subsystems-manifest -L --no-link
> subsystems: docs/subsystems.md is stale (regenerate: python3 pkgs/evidence/subsystems.py write docs/ledger/subsystems.toml --root .)
EXIT=1
```

Green where it was red, on the real repository, with one file as the only
variable. That is the section's premise and its cure, both measured.

## Red before green

Reproduced in the clone, independently of the commit body, by reconstructing the
state Step 1 describes: PR1b's module, PR1b's page, PR1b's test file, plus the
byte-stability test alone appended. Nothing of PR1c's fix is present.

```
$ git -C <clone> checkout ed0f519 -- pkgs/evidence/subsystems.py docs/subsystems.md tests/evidence/test_subsystems.py
$ cat >> tests/evidence/test_subsystems.py <<'EOF'
def test_render_is_a_function_of_the_manifest_alone():
    files_a = base_files()
    files_b = base_files() + ["gamma/g2.txt", "gamma/g3.txt"]
    assert sub.render(base_text(), files_a) == sub.render(base_text(), files_b)
EOF
$ nix build <clone>#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> E       AssertionError: assert '# Subsystems...et |  | 1 |\n' == '# Subsystems...et |  | 3 |\n'
evidence-unit> tests/evidence/test_subsystems.py:176: AssertionError
evidence-unit> FAILED tests/evidence/test_subsystems.py::test_render_is_a_function_of_the_manifest_alone - AssertionError: assert '# Subsystems...et |  | 1 |\n' == '# Subsystems...et...
evidence-unit> 1 failed, 554 passed in 14.12s
```

That is RED 1, byte-identical to the three lines the commit body pastes, and it
is one failure out of 555 — a discriminating fixture, not a suite failing for
other reasons.

RED 2 is the live failure the task exists for, and I took it at the cherry-picked
commit itself rather than by reconstruction:

```
$ git -C <clone> checkout -f ed0f519 && git status --porcelain   # clean
$ nix build <clone>#checks.x86_64-linux.subsystems-manifest -L --no-link
> subsystems: docs/subsystems.md is stale (regenerate: python3 pkgs/evidence/subsystems.py write docs/ledger/subsystems.toml --root .)
EXIT=1
```

Byte-identical to the body's RED 2. Both reds are therefore reproduced here
without reference to the commit body, and the counts reconcile under G11:
PR1b's suite was `554`; PR1c removes `test_render_counts_paths` and adds four
(`test_render_drops_the_paths_column`, `test_counts_one_line_per_row`,
`test_counts_flag_prints_and_writes_nothing`,
`test_render_is_a_function_of_the_manifest_alone`), giving `554 - 1 + 4 = 557` —
the green count below and in the body. `git status --porcelain` empty after every
mutation and every restore in this review.

## Checks

Fresh clone, `XDG_CACHE_HOME` under the gate scratch directory, `--rebuild` on
every acceptance check so none is a cached echo of the seat's own run — which is
the answer the `checks_scope: dirty` warning asks for, since `flake.nix` and the
test file are both inside the diff. (Mutant and red runs drop `--rebuild`: a
mutated source is a new derivation, and `--rebuild` refuses one never built.)

| check | command | result |
|---|---|---|
| subsystems-manifest | `nix build <clone>#checks.x86_64-linux.subsystems-manifest -L --no-link --rebuild` | **PASS** — `checking outputs of '…-subsystems-manifest.drv'`, `EXIT=0` |
| evidence-unit | `… evidence-unit -L --no-link --rebuild` | **PASS** — `557 passed in 13.99s`, `EXIT=0` |
| lint | `… lint -L --no-link --rebuild` | **PASS** — `EXIT=0`; every formatter and linter arm zero (`Found 0 warnings and 0 errors`), `repomap check` silent |
| ledger-unit (not in `acceptance`) | `… ledger-unit -L --no-link` | **PASS** — `59 passed in 1.47s`, `EXIT=0` |
| factory-unit (not in `acceptance`) | `… factory-unit -L --no-link` | **PASS** — `plan.test.mjs: all assertions passed`, `EXIT=0` |
| unit (not in `acceptance`) | `… unit -L --no-link` | **PASS** — `ok 687 now-paragraph accepts the real board's Now paragraph`, `EXIT=0` |

`557 passed` reproduces the commit body exactly. The flake still evaluates whole:
`nix eval <clone>#checks.x86_64-linux --apply` → `{ has = true; n = 61; }` — 61
checks, `subsystems-manifest` among them, the same count PR1b's gate measured, so
this round adds and removes none.

`ruff` is worth one line: `render` keeps its now-unused `files` parameter for
call-site symmetry, and `lint` is green because the body opens with
`del files` — the disposal is what makes the unused argument legal *and* makes
the independence unmistakable to a reader. That is a deliberate choice, not a
lint suppression.

## Mutants

Applied in the clone, run, restored from pristine copies; the tree ends
`git status --porcelain` empty after each. `mutants_total: 3` counts the
section's Step 4 set; two more were applied outside it.

| # | mutant | named? | outcome |
|---|---|---|---|
| **A** | restore the `Paths` column: `render` takes `tally = dict(counts(text, files))` instead of `del files`, and the header and row f-string regain the sixth cell | yes (Step 4) | **KILLED** — `evidence-unit` red: `FAILED …::test_render_is_a_function_of_the_manifest_alone - AssertionError: assert '# Subsystems...et \|  \| 1 \|\n' == '# Subsystems...et…` and `FAILED …::test_render_drops_the_paths_column - AssertionError: assert '\| Paths \|' not in …`, `2 failed, 555 passed in 14.09s`. Matches the commit body verbatim, and **two** tests catch it, not one |
| **B** | make `--counts` write instead of print: the `print` loop replaced by `Path(args.toml).parent/"counts.txt"`.`write_text(…)` | yes (Step 4) | **KILLED** — `evidence-unit` red: `FAILED …::test_counts_flag_prints_and_writes_nothing - AssertionError: assert [] == ['Alpha: 1', …', 'Gamma: 2']`, `1 failed, 556 passed in 13.99s`. Matches the commit body verbatim |
| **C** | drop a row's `owns` glob (`"pkgs/basket/*"` from Isolation, `docs/ledger/subsystems.toml:17`) | yes (Step 4) | **KILLED** — by hand `uncovered: pkgs/basket/basket.sh`, `EXIT=1` (the body's line verbatim) **and** by the shipped check: `subsystems-manifest> uncovered: pkgs/basket/basket.sh`, `builder failed with exit code 1`. The coverage guarantee is live on the real tree |
| B′ | `--counts` that **both** prints and writes `counts.txt` | OUTSIDE | **KILLED** — `evidence-unit` red on the *other* assertion: `FAILED …::test_counts_flag_prints_and_writes_nothing - AssertionError: assert {'counts.txt'…systems.toml'} == {'files.txt',…systems.toml'}`, `1 failed, 556 passed in 14.00s` |
| D | give a second row Isolation's `"pkgs/basket/*"` glob, so a real tracked path is matched by two rows | OUTSIDE | **KILLED** — `subsystems-manifest` red: `ambiguous: pkgs/basket/basket.sh (Isolation, Platform)`, `builder failed with exit code 1` |

Five for five. Two are worth naming. **B′** exists because the section's mutant
**B** kills on the *stdout* assertion, which comes first — on its own it proves
only that `--counts` prints, not that it writes nothing. Making the flag print
*and* write isolates the second half, and the directory-listing assertion is what
dies. That is Interface 3's "writes nothing" pinned in its own right. **D** does
the same service for Interface 2: the section's **C** covers only `uncovered`,
while the interface promises "an uncovered **or ambiguous** path still refuses",
and `ambiguous` is now proved through the shipped check on a real path.

## Defects

**MAJOR-1 — the branch will not merge green onto today's `main`:
`docs/ledger/rules.toml` is owned by no row.** Not PR1c's doing; owed as one
glob line at integrate.

KN1b landed on `main` (`43ed6db integrate KN1b into integ/pr1e`) *after* this
branch was cut at `0f58f81`, bringing four new tracked files. Three are covered;
one is not:

```
$ nix develop -c python3 -c "…fnmatch each new path against every row's owns…"
docs/ledger/rules.toml                              -> []
docs/reviews/2026-09-10-opus-review-pr1e-KN1b.md    -> ['Evidence']
pkgs/evidence/rules.py                              -> ['Evidence']
tests/evidence/test_rules.py                        -> ['Evidence']
```

Against the post-merge tracked set (main's 798 paths ∪ the branch's, 802), the
manifest refuses, while the page — the thing this task fixed — is stable:

```
$ python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --files merged-files.txt
uncovered: docs/ledger/rules.toml
EXIT=1
$ python3 pkgs/evidence/subsystems.py write docs/ledger/subsystems.toml --files merged-files.txt --check docs/subsystems.md
PAGE_EXIT=0
```

So `factory-integrate`, which merges `main` before running the checks, will
report `CHECK subsystems-manifest fail` again — with a different message this
time (`uncovered:`, not `is stale`). This is the check working exactly as
designed (mutant **C** is the same failure induced deliberately), and PR1c's
content is not at fault: the seat branched before the file existed and could not
have known. `docs/ledger/subsystems.toml` is already inside the chain's `touches`
union, so the fix is one line — add `"docs/ledger/rules.toml"` (or widen
Knowledge's or Evidence's ledger enumeration) — folded by the integrator or typed
as a one-liner. It does not gate PR1c because a third round on PR1c would not
prevent the next such file either; see MINOR-1 for the general form.

**MINOR-1 — plan defect `missing-case`: the section cured one of the page's two
file-list dependencies and left the other, which has the same shape.**
Non-gating.

The section's own diagnosis is that "a build-time refusal that fires on unrelated
work is not a guard, it is a tax". It then identifies exactly one mechanism (the
`Paths` column) and removes it, correctly and completely. But `subsystems-manifest`
runs `validate` as well as `write --check`, and `validate` reads the file list
too. Because the manifest's globs are largely enumerations of individual paths —

```
rows 9  globs 153  literal 97
```

— 97 of 153 globs name one file each, and `docs/ledger/` is enumerated entry by
entry (`:182-190`). Any commit that adds a path outside the existing globs turns
the check red, wherever in the repo it lands. MAJOR-1 is the live instance,
arriving within a day of the fix. The staleness mode is cured absolutely (three
file lists, one hash); the uncovered mode remains and is by design, but the
section did not weigh it when it wrote "the page then changes only when
`docs/ledger/subsystems.toml` changes — rare". The page does; the *check* does
not.

*Owed*: an orchestrator's decision, not a fix round — either accept that a new
kind of path costs one manifest line (and say so in the section that introduces
the check, so the integrator expects it), or widen the enumerated rows to
directory globs where a subsystem genuinely owns a directory. I lean to the
first: the enumeration is what makes the ownership meaningful, and one line at
integrate is a smaller tax than a wrong owner assigned by a wildcard.

**MINOR-2 — `validate --counts` short-circuits validation and exits 0 on a
manifest that does not cover the tree.** As specified; non-gating.

Measured under mutant **C**, with `pkgs/basket/basket.sh` genuinely uncovered:

```
$ python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root .
uncovered: pkgs/basket/basket.sh
EXIT=1
$ python3 pkgs/evidence/subsystems.py validate docs/ledger/subsystems.toml --root . --counts >/dev/null
COUNTS_EXIT=0
```

The flag returns before `validate` is called (`subsystems.py:215-219`), so
`validate --counts` is a reporting command wearing the validator's name. Interface
3 says "prints … and exits 0", so the code does what the plan asked, and nothing
today depends on the difference: `flake.nix:1400` runs `validate` **without**
`--counts`, and no other caller of `--counts` exists in the tree
(`grep -rn -- "--counts" flake.nix githooks tools pkgs docs` returns only the
module's own docstring and its `add_argument`). The risk is future and small: if
anyone ever wires `--counts` into a check expecting a refusal, that check is
vacuous by construction. One sentence in the runbook or a `--counts` that
validates first and still exits on the counts would close it. Recorded, not owed.

**MINOR-3 — the docstring correction is untested.** Non-gating.

The Files bullet asks for the docstring at `:7` to be corrected "since it names
the path count as part of the table", and it is (quoted above). But the only
docstring assertion in the suite is PR1b's
`test_docstring_describes_the_matcher_used`, which pins `fnmatch.fnmatch` in and
`file_class` out — nothing asserts the count is gone. Restoring the old wording
would leave `evidence-unit` green. The section's Step 4 set has no docstring
mutant either, so this is a gap in the plan's mutant list rather than an omission
by the seat, and the substance behind the docstring — the column itself — is
pinned twice over (`test_render_drops_the_paths_column`, mutant **A**). A one-line
`assert "path count" not in sub.__doc__` would close it if a later round touches
this file.

**Step 7 — what this could break that its checks do not cover.** One pass, four
questions, all measured; nothing found that gates.

*Consumers of the page and of the removed column.* `docs/subsystems.md` has
exactly one consumer, the check that generates it
(`grep -rn subsystems flake.nix githooks tools pkgs/evidence/tasks.py
pkgs/evidence/repomap.py docs/runbooks` → `flake.nix:1386-1401` and nothing
else). No board section, runbook, or script reads the `Paths` numbers, so
deleting the column loses no downstream reader. The numbers remain reachable on
demand and reproduce the body's paste exactly.

*The file-list source, and PR1b's open symlink question.* PR1b's gate flagged
that `subsystems-manifest` feeds `--files` from `find ${self} -type f` while a
human uses `--root .` (`git ls-files`), and that a tracked symlink would be
dropped by `find -type f` — a page that regenerates differently under the two
sources. For the *page* that risk is now gone outright: `render` ignores the file
list, so the two sources cannot disagree about the page's bytes, and
`write --root . --check docs/subsystems.md` → `EXIT=0` confirms it. The concern
survives only for `validate`'s coverage, where it is the correct direction (a
tracked symlink would go unchecked, never falsely refused). PR1c narrows that
open question rather than widening it.

*Could the check go red on the operator's live tree from untracked files?*
No, re-measured here since PR1c changes the derivation's inputs: with and without
an untracked, non-ignored file in the clone, `nix eval
…subsystems-manifest.drvPath` returns the same
`/nix/store/s68wwnn9x7qdvj3s1llxcrdzggig5xnf-subsystems-manifest.drv`. `${self}`
is the tracked set. The operator's two untracked files (`.msg-ui1.txt`,
`docs/research-2026-09-09-bug-workflow-packet.md`) cannot make this red.

*Anything outside `pkgs/evidence/subsystems.py`?* PR1c's own commit touches no
other code — `git show --name-only df7147a | grep -c tasks.py` → `0`, and the
only import from `tasks` is still `CLASS_GLOB_RE`. `ledger-unit`, `factory-unit`
and `unit` — all outside the acceptance list, and `unit` is the check that has
bitten this factory before — are green above. The `counts()` helper carries the
per-row set comprehension forward, so PR1b's within-row deduplication is
preserved where the counting now lives, and `test_within_row_overlap_counts_once`
was correctly re-pointed at `counts` rather than deleted.

## Verdict

**APPROVED.**

The content is right and the two-commit shape is safe to land. `render` is
provably a function of the manifest alone — three different file lists, one hash
`0851b317084bfded537c61a73065bd3c`, and `del files` at the top of the body so it
cannot regress by accident — while the counts remain available and reproduce the
body's nine integers exactly. The coverage guarantee survived: `uncovered` and
`ambiguous` both still refuse, both proved through the shipped
`subsystems-manifest` check on real tracked paths (mutants **C** and **D**), not
only on fixtures. `validate --counts` prints one line per row, exits 0, and
leaves both `git status --porcelain` and a whole-tree file hash unchanged. The
docstring no longer advertises the count. The decisive end-to-end pair holds: one
unrelated tracked file added, green under PR1c's code and red with
`docs/subsystems.md is stale` under PR1b's — the tax removed, measured on the
real repository.

All three `acceptance` checks are green on the committed tree in a fresh clone
under `--rebuild` (`subsystems-manifest` `EXIT=0`, `evidence-unit` `557 passed`,
`lint` `EXIT=0`), three further checks outside the list are green, the flake still
evaluates to 61 checks, red before green reproduces independently at
`1 failed, 554 passed` and at `docs/subsystems.md is stale` on the cherry-picked
commit, and five mutants died — the section's three plus two of mine that split
the assertions their named counterparts merged. Subject byte-identical at
`md5 b84a1ceac97311fa29112043cbda396a`, both trailers in policy order on both
commits with each commit's own run and the model from its own `.result`, and no
undeclared touch: six of the seven changed files sit in the chain's `touches`
union and the seventh is a queue-block-only `docs/OPERATIONS.md` diff, G5's first
standing exemption.

The `checks_scope: dirty` flag is resolved and clean. It classifies the committed
diff, not the working tree (`factory-task:588-602`: dirty when
`base..task/<key>` touches `flake.nix`, `tests` or `githooks`), and the two named
files are exactly the two check-machinery files in the range, both from the
cherry-picked PR1b commit. The seat workspace holds nothing uncommitted —
`git diff HEAD` empty, one untracked `.scratch/` of the seat's own scratch files —
so the commit and the tested tree do not differ, and the warning the flag exists
to raise is discharged by rebuilding all three checks from the committed tree.

The `status=failed` on `PR1c.result` is the two-commit demotion alone, which the
orchestrator has taken as its own plan defect and closed by amending G6. Both
subjects are their sections' verbatim, `0f58f81` is an ancestor of live `main`,
and landing both is how PR1b and PR1c reach `main` together.

It is approved with one action owed before the merge and three recorded notes.
MAJOR-1: `docs/ledger/rules.toml` arrived on `main` with KN1b after this branch
was cut and no row owns it, so `factory-integrate` will hit
`uncovered: docs/ledger/rules.toml`; one glob line in a file already inside the
chain's `touches` clears it, and nothing in PR1c caused it. MINOR-1 is the
general form and the plan defect of record (`missing-case`): the section removed
the page's file-list dependency and left `validate`'s, which fires the same way
on unrelated work because 97 of the manifest's 153 globs name a single file —
an orchestrator's decision, not a fix round. MINOR-2 notes that
`validate --counts` returns before validating, as Interface 3 specified and with
no caller today. MINOR-3 notes that the docstring correction is pinned by no
test, a gap in the section's mutant list rather than the seat's work.
