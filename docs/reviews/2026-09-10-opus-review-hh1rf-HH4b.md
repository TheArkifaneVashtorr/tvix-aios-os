---
plan_defect: none
mutants_total: 1
mutants_killed: 1
mutants_outside_named: 1
model: opus
---
# Opus gate — seat run hh1rf, task HH4b — APPROVED

## Summary

The MAJOR is closed, and it is closed the only way a one-line restoration can be
judged: by evaluating the output that was missing, in a fresh clone, and by
deleting the line again to watch it break.

```
$ nix eval --offline '<clone>#formatter.x86_64-linux.name'
"treefmt-2.5.0"
EXIT=0
```

That is `flake.nix:3003`, `      formatter.${system} = pkgs.treefmt;`, restored
byte-identical and in the same position `afb6e2d~1` had it — last binding of the
output set, six spaces of indent, the blank line above it kept. `nix fmt` has
its program back: `formatter.x86_64-linux.meta.mainProgram` → `treefmt`.

The other half of the contract is that **nothing else moved**, and it did not.
`git diff afb6e2d HEAD -- lib flake.nix` is two added lines in `flake.nix` and
an empty diff for `lib/`. Across the whole tree, `helm.nix`, all six declaration
fixtures, `lib/checkHelmDeclaration.nix` and `docs/MAP.md` are byte-identical to
`afb6e2d`. HH4's checker was carried, not rewritten — and I confirmed it still
*fires* on the real declaration rather than merely building (mutant b below).

All six `helm-declaration*` checks are green with `--rebuild`, `lint` is green,
one commit with a byte-identical subject, both trailers in policy order with the
model from `HH4b.result`, every file inside the chain's `touches` union, and
`docs/OPERATIONS.md` correctly left alone.

One thing is worth the operator's attention and is *not* owed on this commit:
under the section's own mutant, both acceptance checks stay green. The line that
was deleted is still guarded by nothing in CI. Measured, MINOR-1.

**APPROVED.**

## Diff against the section

Fresh clone of `task/HH4b` at `a53aa48`, base `01a734c` from `HH4b.result`.

```
$ git -C <clone> log --oneline -3
a53aa48 helm-home: restore the flake's formatter output HH4 deleted; the declaration checker stands (test: helm-declaration, lint)
01a734c docs: type HH4b — restore the flake's formatter output HH4 deleted; HH4 gated rework on that one MAJOR (test: lint)
a48de82 docs: board — queue block regenerated after HH3 landed (test: lint)

$ git -C <clone> rev-list --count 01a734c..HEAD
1

$ git -C <clone> diff --stat 01a734c..HEAD
 docs/MAP.md                                  |   8 +-
 flake.nix                                    | 103 ++++++++++-
 helm.nix                                     |  32 ++++
 lib/checkHelmDeclaration.nix                 | 264 +++++++++++++++++++++++++++
 tests/helm-home/declarations/bad-block.nix   |  30 +++
 tests/helm-home/declarations/bad-field.nix   |  33 ++++
 tests/helm-home/declarations/bad-profile.nix |  32 ++++
 tests/helm-home/declarations/bad-program.nix |  32 ++++
 tests/helm-home/declarations/bad-seat.nix    |  32 ++++
 tests/helm-home/declarations/good-core.nix   |  32 ++++
 10 files changed, 596 insertions(+), 2 deletions(-)
```

**One commit, and the shape Step 1 allows.** Step 1 prescribes
`git fetch … && git cherry-pick FETCH_HEAD` — a working step, on top of which
Step 2 applies the fix — and Step 5 orders **one commit** carrying the section's
subject. The seat squashed the cherry-picked tree and the restored line into
that single commit (`FACTORY-NOTES`: "squashed into one commit: HH4's checker
tree + the formatter line"). That is Step 5's shape, not a deviation from
Step 1: Step 1 never says the cherry-pick survives as its own commit, and the
section's `commit subject` byte is singular. Two commits would have been the
wrong shape, not this.

**Touches.** This is a fix round, so the contract is the chain's union:

```
$ nix develop -c python3 pkgs/evidence/tasks.py touches docs/superpowers/plans/2026-09-08-helm-home-1.md HH4b
lib/checkHelmDeclaration.nix
helm.nix
tests/helm-home/declarations/good-core.nix
tests/helm-home/declarations/bad-profile.nix
tests/helm-home/declarations/bad-program.nix
tests/helm-home/declarations/bad-seat.nix
tests/helm-home/declarations/bad-block.nix
tests/helm-home/declarations/bad-field.nix
flake.nix
docs/OPERATIONS.md
```

Nine of the ten are in the diff; `docs/OPERATIONS.md` is simply unused, which is
what its Files line asks for ("only if the hook's G8c asks"). The tenth file in
the diff, `docs/MAP.md`, is the declared exemption and is byte-identical to
`afb6e2d`'s regenerated map. **No undeclared touch**; the plan file is
untouched.

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` — both 122 bytes, `md5sum` `3d7375ddcdbedfa984b3fadb94f21262`
on each. The body pastes Step 1's red, Step 3's four green lines and Step 4's
mutant; each reproduces below. The last two lines, in the policy order
(`docs/board/policies.md:30-36`):

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run hh1rf)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `HH4b.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`), the run equal to `hh1rf`. Correct.

**The fix, at the byte.**

```
$ grep -n 'formatter' <clone>/flake.nix
3003:      formatter.${system} = pkgs.treefmt;

$ git -C <clone> diff afb6e2d~1..afb6e2d -- flake.nix    # what HH4 removed
       };
-
-      formatter.${system} = pkgs.treefmt;
     };
 }
```

`afb6e2d~1`'s tail under `cat -A` ends `      formatter.${system} = pkgs.treefmt;$`
/ `    };$` / `}$` — the same six-space indent, the same blank line above, the
same last-binding position the clone now has. "Exactly where HH4's diff removed
it" is met literally, not approximately.

**HH4's deliverable is intact.** The section's Interfaces line asks that the six
checks, `lib`, `helm` and the fixtures be byte-identical to `afb6e2d`. Fetched
`task/HH4` from `~/factory/ws/hh1r/HH4` (read-only); `FETCH_HEAD` is `afb6e2d`.

```
$ git -C <clone> diff afb6e2d HEAD -- lib flake.nix
diff --git a/flake.nix b/flake.nix
index de41c02..5625a27 100644
--- a/flake.nix
+++ b/flake.nix
@@ -2999,5 +2999,7 @@
           else
             pkgs.runCommand "helm-declaration-negative-field-ok" { } "touch $out";
       };
+
+      formatter.${system} = pkgs.treefmt;
     };
 }
```

`lib/` produces no diff at all, and `flake.nix` differs by exactly the two
restored lines — the whole delta the section asked for, and nothing else. The
full-tree comparison confirms the rest:

```
$ git -C <clone> diff --stat afb6e2d..HEAD
 docs/OPERATIONS.md                               |  2 +-
 docs/board/log-2026-09.md                        |  4 ++++
 docs/superpowers/plans/2026-09-08-helm-home-1.md | 26 ++++++++++++++++++++++++
 flake.nix                                        |  2 ++
 4 files changed, 33 insertions(+), 1 deletion(-)
```

`helm.nix`, all six fixtures and `docs/MAP.md` do not appear — byte-identical.
The three files that do appear beside `flake.nix` are **not** this commit's:
they arrive with the base (`a48de82` regenerated the queue block after HH3
landed; `01a734c` typed HH4b into the plan and the log), and `a53aa48`'s own
diff (`01a734c..HEAD`, above) touches none of them. The one-line
`docs/OPERATIONS.md` difference against `afb6e2d` is the derived queue block at
a newer main, i.e. the prior gate's non-owed minor, resolved by rebase rather
than by an edit.

## Red before green

Reproduced independently in the clone by deleting the restored line — the
section's Step 4 mutant, which is also Step 1's red:

```
$ sed -i '3003d' <clone>/flake.nix
$ nix eval --offline '<clone>#formatter.x86_64-linux.name'
error: flake 'git+file:///…/gate-hh4b' does not provide attribute
'packages.x86_64-linux.formatter.x86_64-linux.name',
'legacyPackages.x86_64-linux.formatter.x86_64-linux.name' or
'formatter.x86_64-linux.name'
EXIT=1
```

Word for word the error the commit body pastes, and word for word the regression
the prior gate's MAJOR named. Restored (`git checkout -- flake.nix`), same
command → `"treefmt-2.5.0"`, `EXIT=0`, and `git status --porcelain` empty. The
assertion can fail, so it is not vacuous; the green is not a cache echo, since
the eval is re-run against the mutated tree in between.

Step 3's third line — `nix fmt` resolves treefmt — I took build-only:

```
$ nix eval --offline --raw '<clone>#formatter.x86_64-linux.meta.mainProgram'
treefmt
```

## Checks

Fresh clone, `XDG_CACHE_HOME` under the gate scratch directory. `--rebuild` on
every one, so nothing below is a cached echo of the seat's own run.

| check | command | result |
|---|---|---|
| helm-declaration | `nix build <clone>#checks.x86_64-linux.helm-declaration -L --no-link --rebuild` | **PASS** — `checking outputs of '…-helm-declaration-nixos-agent-env-ok.drv'`, `EXIT=0` |
| lint | `… lint -L --no-link --rebuild` | **PASS** — `EXIT=0`; every formatter and linter arm zero |
| helm-declaration-negative-profile | `… -L --no-link --rebuild` | **PASS** — `…-helm-declaration-negative-profile-ok.drv`, `EXIT=0` |
| helm-declaration-negative-program | `… -L --no-link --rebuild` | **PASS** — `…-helm-declaration-negative-program-ok.drv`, `EXIT=0` |
| helm-declaration-negative-seat | `… -L --no-link --rebuild` | **PASS** — `…-helm-declaration-negative-seat-ok.drv`, `EXIT=0` |
| helm-declaration-negative-block | `… -L --no-link --rebuild` | **PASS** — `…-helm-declaration-negative-block-ok.drv`, `EXIT=0` |
| helm-declaration-negative-field | `… -L --no-link --rebuild` | **PASS** — `…-helm-declaration-negative-field-ok.drv`, `EXIT=0` |
| MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root . check` | silent, `EXIT=0` |

Both `acceptance` names green, and the whole `helm-declaration*` family with
them. A note on the count: the family is **six** checks — one positive plus
**five** negatives (`grep -n '^        helm-declaration' <clone>/flake.nix`
returns exactly those six names at lines 2908/2932/2948/2963/2975/2989). There is
no sixth `-negative-*`; the prior round's "six" is the family, and all six are
green here.

`lint` is itself non-vacuous in this tree: its log shows its own negative
fixtures firing (`eslint(no-debugger)` on `tests/lint/fixtures/js/bad.mjs`,
`eslint(no-dupe-keys)` on `workflow-bad.js`, Prettier on `unformatted.mjs`)
while the check exits 0 — the linters are demonstrably alive, not silent.

## Mutants

Applied in the clone, run, then reverted; the tree ends `git status --porcelain`
empty. `mutants_total: 1` counts the section's Step 4 set, which names one.

| # | mutant | named? | outcome |
|---|---|---|---|
| **a** | delete the restored `formatter.${system} = pkgs.treefmt;` (`flake.nix:3003`) | yes (Step 4) | **KILLED** — `nix eval --offline '<clone>#formatter.x86_64-linux.name'` → `error: … does not provide attribute 'packages.x86_64-linux.formatter.x86_64-linux.name', 'legacyPackages.x86_64-linux.formatter.x86_64-linux.name' or 'formatter.x86_64-linux.name'`, `EXIT=1`. Matches the commit body verbatim. Restored → `"treefmt-2.5.0"` |
| b | `helm.nix` `card.blocks` gains `"bogus"` — the carried checker's discrimination on the *real* declaration | OUTSIDE | **KILLED** — `helm-declaration` red: `error: helm declaration nixos-agent-env: card.blocks holds bogus, not one of why, state, do, notes, cost, lastRun, terminal`, `EXIT=1`. Restored → green |

Mutant b is the measurement that matters for "the declaration checker stands":
the six checks building green proves they evaluate, not that they discriminate.
They do — the carried `lib/checkHelmDeclaration.nix` rejects a bad block in
`helm.nix` with a precise message, so HH4's deliverable arrives working, not
merely present.

Mutant a's kill instrument is the section's `nix eval`, and only that. See
MINOR-1.

## Defects

None gating.

**MINOR-1 — the restored line is guarded by nothing in CI, and I measured it.**
With mutant a applied, both of the section's `acceptance` checks stay green:

```
$ sed -i '3003d' <clone>/flake.nix
$ nix build <clone>#checks.x86_64-linux.helm-declaration -L --no-link   → EXIT=0
$ nix build <clone>#checks.x86_64-linux.lint            -L --no-link   → EXIT=0
```

So the assertion "the formatter output resolves" is killed only by a hand-run
`nix eval`; no check in the flake sees the deletion (`grep -n 'formatter'
<clone>/flake.nix` returns the one line and nothing else — no check references
it). That is precisely the blind spot that let `afb6e2d` delete the line without
turning anything red, and it is unchanged after this round: a repeat of HH4's
mistake would still ship green. Nothing is owed on this commit — the section
scopes itself to "restores the one line", `touches` is two files, and a new
check would be a scope expansion — but the cheap guard exists (one attribute in
`checks.${system}` asserting `self.formatter.${system}` resolves, `docs/MAP.md`
being exempt anyway), and it belongs in a follow-on row rather than in this
gate. Recorded, non-gating.

**MINOR-2 — a `--rebuild` gotcha for future gates, not a fault of this round.**
Running an acceptance check with `--rebuild` against a *mutated* tree does not
build it; it exits 1 on
`error: some outputs of '/nix/store/…-lint.drv' are not valid, so checking is
not possible / Hint: --rebuild and --check error if the derivation was not
previously built and cannot be substituted.` A gate that reads that as a kill
would score a mutant dead when it is alive — I did, for one run, before
re-measuring without the flag (the green results in MINOR-1 are the corrected
ones). `--rebuild` is the right flag for the clean tree and the wrong one for a
mutated one.

## Verdict

**APPROVED.**

The prior round's MAJOR is measurably closed: `formatter.${system} =
pkgs.treefmt;` is back at `flake.nix:3003`, byte-identical and in `afb6e2d~1`'s
own position, `nix eval --offline '#formatter.x86_64-linux.name'` prints
`"treefmt-2.5.0"` where it used to raise "does not provide attribute", and
`meta.mainProgram` is `treefmt`, so `nix fmt` has its program. HH4's deliverable
came through untouched — `git diff afb6e2d HEAD -- lib flake.nix` is the two
restored lines and nothing more, with `helm.nix`, the six fixtures and
`docs/MAP.md` byte-identical — and it still discriminates, not merely builds
(mutant b). All six `helm-declaration*` checks and `lint` are green in a fresh
clone under `--rebuild`; the section's one mutant dies with the exact error the
commit body pastes; one commit, subject byte-identical, both trailers in policy
order with the model from `HH4b.result`, every file inside the chain's union and
`docs/OPERATIONS.md` correctly untouched. The one thing left open is a coverage
gap the section deliberately did not buy: nothing in CI would catch the same
deletion tomorrow.
