---
plan_defect: wrong-fact
mutants_total: 11
mutants_killed: 7
mutants_outside_named: 6
reviewer: opus
majors: null
minors: 5
---
# Opus gate — seat run pb3ar3, task P3Ar3 — APPROVED

## Summary

The change of approach works, and it works for the reason the orchestrator
said it would. `flake.nix:1134,1146-1147` exports `EVIDENCE_UNIT_SANDBOX=1`,
makes the store-copied `docs/ledger` writable, and copies the frozen seed over
`docs/ledger/plan-defects.toml`; `tests/evidence/test_tasks.py:2677-2689`
asserts the pinned copy is byte-identical to the fixture and skips with a
stated reason outside the sandbox. The consequence the six previous rounds
never achieved is now mechanical: I wrote a scratch test hard-coding today's
live Record line, `60 rej, 53 plan (vac 15, miss 20, under 9, fact 9)`, over
`docs/ledger/plan-defects.toml`. It **passes** in the devShell and **fails** in
the sandbox build. It fails not because a scanner recognised its spelling but
because the number it names does not exist inside the check. No spelling
defeats that.

The text-scanning guard and all four of its helpers are gone from the tree, no
scratch attack file remains, the frozen-seed record test (48/45) and the shape
test with its negative case stand and both still kill their mutants inside the
sandbox, a 61st row appended to the live ledger leaves the check green, the
ledger diff against main is empty, and every check is green. One commit, subject
byte-identical to P3A's, both trailers, touched files inside `touches` plus
`docs/MAP.md` by rule, result block in the exact form.

The findings are all MINOR, but the first is worth the orchestrator's attention
because it is a plan wrong-fact the commit body repeats. **There is no red on
main.** Main's `flake.nix` exports nothing, so the branch's pin test *skips*
there and the sandbox build is green (`174 passed, 1 skipped`). The plan's
Step 1 predicted a red on main; item 1's own skip condition forecloses it. The
commit body's "Red on main —" paste is in fact the item-1 mutation (copy line
dropped, export kept), which is the same run pasted again two paragraphs later
under its correct name. The test *is* load-bearing and I made it red three
ways — but not on main.

## The pin in the sandbox

Clone `…/scratchpad/gate-pb3ar3-P3Ar3`, branch `task/P3Ar3`, head `ef0852f`,
base `61ffee8`, tree clean. Mutations were run in a second clone
(`…/scratchpad/mut`) so the review clone was never written to.

The check is green and the pin test **passes** rather than skipping. The bare
counts already prove it — outside the sandbox the suite is `174 passed, 1
skipped`, inside it is `175 passed, 0 skipped`:

```
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> 175 passed in 4.47s                              EXIT=0
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild
checking outputs of '/nix/store/z66wcx…-evidence-unit.drv'...
evidence-unit> 175 passed in 4.64s                              EXIT=0
```

Named explicitly — a scratch copy with the check's `pytest tests/evidence -q`
replaced by `pytest tests/evidence -v -rs`, nothing else changed:

```
evidence-unit> tests/evidence/test_tasks.py::test_sandbox_ledger_is_the_frozen_seed PASSED [ 90%]
evidence-unit> ============================= 175 passed in 4.45s ==============================
```

No `SKIPPED` line for it anywhere in that log.

**The item-1 mutation — the `cp` line dropped, the export left in place.**
KILLED:

```
evidence-unit> >       assert ledger.read_bytes() == FROZEN_SEED.read_bytes()
evidence-unit> E       assert b'# The plan-...mplementer"\n' == b'# The plan-..."implementer"'
evidence-unit> FAILED tests/evidence/test_tasks.py::test_sandbox_ledger_is_the_frozen_seed
evidence-unit> 1 failed, 174 passed in 4.52s
error: Cannot build '/nix/store/pr5yf19…-evidence-unit.drv'. builder failed with exit code 1.
```

Note the `174 passed` beside it: with the live 60-row ledger back in place
nothing else in the suite moves, which is the cleanest evidence that the pin
breaks no other reader.

**The `chmod` is required.** `cp -r` out of the store preserves 0555 dirs and
0444 files, so without it the copy cannot land. Dropped in a scratch copy:

```
evidence-unit> cp: cannot create regular file 'docs/ledger/plan-defects.toml': Permission denied
error: Cannot build '/nix/store/7qi1i33…-evidence-unit.drv'.
```

The comment at `flake.nix:1144-1145` states exactly this reason, correctly.

**Item 7 — the skip logic's negative case.** In the clone, where the ledger is
live, forcing the variable makes the assertion fire and fail; without it the
skip carries its reason:

```
$ EVIDENCE_UNIT_SANDBOX=1 nix develop -c pytest tests/evidence -q
>       assert ledger.read_bytes() == FROZEN_SEED.read_bytes()
E       assert b'# The plan-...mplementer"\n' == b'# The plan-..."implementer"'
FAILED tests/evidence/test_tasks.py::test_sandbox_ledger_is_the_frozen_seed
1 failed, 174 passed in 4.46s

$ nix develop -c pytest tests/evidence -q -rs
SKIPPED [1] tests/evidence/test_tasks.py:2686: the sandbox-pin assertion runs only in the evidence-unit sandbox
174 passed, 1 skipped in 4.46s
```

**Red before green — and what main actually does.** Contracted: main's
`flake.nix` (`git show 61ffee8:flake.nix`) with the branch's tests → the pin
test red in the sandbox. Reproduced, and it is **not** red:

```
$ git show 61ffee8:flake.nix > flake.nix && git add -A
$ grep -n "EVIDENCE_UNIT_SANDBOX\|plan-defects-seed" flake.nix
(no match — main's flake has neither the export nor the cp)
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> 174 passed, 1 skipped in 4.47s                   EXIT=0
```

Main lacks the *export* as well as the copy, so the test skips itself. Restore
the branch's `flake.nix` → `175 passed`. See Findings, MINOR 1.

**The seed.** Byte-identical to the row the record test was built on, 48 rows
against the live 60:

```
$ git show 3937d98:docs/ledger/plan-defects.toml | cmp - tests/evidence/fixtures/ledger/plan-defects-seed.toml
IDENTICAL
$ sha256sum tests/evidence/fixtures/ledger/plan-defects-seed.toml
6b2f745d14be98c09071af1914673f47603f05aef1ddfcf4228c76ae4117ed34
$ grep -c '^\[\[rejection\]\]' tests/evidence/fixtures/ledger/plan-defects-seed.toml   -> 48
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml                           -> 60
```

## The consequence

Today's live Record line, from the clone:

```
$ nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep Record
**Record (7 d):** 60 rej, 53 plan (vac 15, miss 20, under 9, fact 9)
```

My scratch test (`tests/evidence/test_scratch_live.py`, since removed) loads
`tasks.py`, copies `HERE.parents[2] / "docs" / "ledger" / "plan-defects.toml"`
into `tmp_path`, renders the brief at `2026-09-06` and asserts that string —
main's own defect shape, no evasion, no obfuscation. `git add`ed so the flake
sees it:

```
$ nix develop -c pytest tests/evidence/test_scratch_live.py -q
1 passed in 0.01s

$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> >       assert "60 rej, 53 plan (vac 15, miss 20, under 9, fact 9)" in line
evidence-unit> E       AssertionError: assert '60 rej, 53 plan (vac 15, miss 20, under 9, fact 9)'
evidence-unit>   in '**Record (7 d):** 48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)'
evidence-unit> FAILED tests/evidence/test_scratch_live.py::test_scratch_hardcoded_live_count
evidence-unit> 1 failed, 175 passed in 4.84s
```

Passes in the devShell, fails in the check. That is item 2, reproduced.

**The inverse.** The same test with the SEED count substituted:

```
$ nix develop -c pytest tests/evidence/test_scratch_live.py -q
E       AssertionError: assert '48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)'
  in '**Record (7 d):** 60 rej, 53 plan (vac 15, miss 20, under 9, fact 9)'
1 failed in 0.02s

$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> 176 passed in 4.55s                              EXIT=0
```

So the polarity is exactly inverted between the two environments, and the seed
count is the only number that is stable under the check. That is the intended
property, and it is why the devShell run cannot be the truth: a test that is
green locally can be red in the check and vice versa. The runbook says so
(`docs/runbooks/evidence.md:110-118`): "A test that hard-codes the live count
passes in the devShell (which reads the live ledger) but fails in the sandbox —
the sandbox is the truth, the devShell run is not."

## The other readers

Only two places in the whole evidence suite touch the real ledger path:

```
$ grep -n "parents\[2\]" tests/evidence/*.py
tests/evidence/test_tasks.py:2384:LIVE_LEDGER = HERE.parents[2] / "docs" / "ledger" / "plan-defects.toml"
tests/evidence/test_tasks.py:2687:    root = HERE.parents[2]
… (the rest resolve pkgs/evidence/*.py, not the ledger)
```

`LIVE_LEDGER` is read by `test_live_record_line_shape_only` only; `2687` is the
pin test. Every other ledger in the file is written under `tmp_path` from inline
strings or from `FROZEN_SEED` — `_defect_repo` at `tests/evidence/test_tasks.py:2395`.
No test names a run (`pa4`, `cr19`, `pb3a`, `sc*`, `bk*`, `oi*`) as a literal:

```
$ grep -nE '"(pa[0-9]|cr[0-9]+|pb3a[a-z0-9]*|sc[0-9]+|bk[0-9]+|oi[0-9]+)"' tests/evidence/*.py
(no matches)
```

So nothing depends on the live row count or on rows filed after the seed, and
nothing that the pin changes is broken. The shape test inside the sandbox reads
the seed: `rej >= 48` holds with equality, and it passes (it is one of the 175).
Its shape and negative assertions are content-independent and still bite there —
mutant X5 below proves it. `test_claims.py:174` reads
`docs/ledger/claims.toml`, which the pin does not touch; the pin overwrites one
file only.

Outside `evidence-unit`, two other checks copy `docs/ledger` — `ledger-unit`
(`flake.nix:1180`) and `unit` (`flake.nix:2042`) — but nothing under
`tests/ledger` or `tests/unit` reads `plan-defects.toml`:

```
$ grep -rln "plan-defects" . | grep -v '^./docs/reviews\|^./.git'
flake.nix  docs/runbooks/evidence.md  docs/runbooks/session.md
docs/superpowers/specs/…  docs/superpowers/plans/…
tests/evidence/test_tasks.py  pkgs/evidence/tasks.py  .claude/workflows/plan.js
```

so no other check wants the same pin. The `lint` check and the pre-commit hook
run `tasks.py --root . check` over the real tree (`flake.nix:1053`,
`githooks/pre-commit:54`) — that is by design, and it is now the only thing in
CI that validates the live ledger.

**The scratch-row proof.** A 61st `[[rejection]]` for
`docs/reviews/2026-09-06-opus-review-pb3ar-P3Ar.md` (exists, REJECTED, dated
before `front_matter_from`), `git add`ed:

```
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml   -> 61
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check -> EXIT=0 (silent)
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> 175 passed in 4.44s                             EXIT=0
$ nix develop -c pytest tests/evidence -q
174 passed, 1 skipped in 4.59s
--- reverted ---
$ grep -c '^\[\[rejection\]\]' docs/ledger/plan-defects.toml   -> 60
$ git status --porcelain                                       -> (empty)
$ git diff 61ffee8..HEAD -- docs/ledger                        -> (empty)
```

## The guard's removal

Gone from the tree — the four names appear only in earlier review documents and
in the plan's own prose, never in code:

```
$ grep -rn "test_no_literal_record_count_against_live_ledger\|_test_function_bodies\|_reads_live_ledger\|_reads_frozen_seed" .
docs/reviews/2026-09-06-opus-review-pb3ar2-P3Ar2.md:…      (prose)
docs/reviews/2026-09-06-opus-review-pb3arb2-P3Arb.md:…     (prose)
docs/reviews/2026-09-06-opus-review-pb3ar2b-P3Ar2b.md:…    (prose)
docs/superpowers/plans/2026-09-06-planning-agent.md:606    (the contract)
```

No scratch attack file survives; `tests/evidence` holds exactly `test_claims.py`,
`test_evidence.py`, `test_judgements.py`, `test_repomap.py`, `test_tasks.py` and
`fixtures/`. The branch's diff against main adds no `ast`/`tokenize` import —
only `re` and `pytest` (`tests/evidence/test_tasks.py:8,10`).

The frozen-seed record test (`:2627-2654`, asserting `48 rej, 45 plan (vac 15,
miss 16, under 8, fact 6)` over `FROZEN_SEED`) and the shape test (`:2657-2674`,
`RECORD_SHAPE` + `rej >= 48` + the negative case
`RECORD_SHAPE.match("**Record: unavailable**") is None`) both stand and both
pass. The runbook says the pin replaced the guard
(`docs/runbooks/evidence.md:114-116`): "This pin replaced P3Ar2b's
text-scanning guard and its helpers (deleted): rather than scan test code for
literal counts over the live ledger, the environment itself can no longer reach
it."

## Mutants

11 applied, 7 killed, 4 survived; 6 outside the named set.

| # | mutant | result |
|---|---|---|
| M1 | **named:** the `cp` of the seed dropped (export kept) | KILLED — `FAILED …::test_sandbox_ledger_is_the_frozen_seed`, `1 failed, 174 passed`, build red |
| M2 | **named:** the `chmod u+w` dropped | KILLED — `cp: cannot create regular file 'docs/ledger/plan-defects.toml': Permission denied`, build red |
| M3 | **named:** `export EVIDENCE_UNIT_SANDBOX=1` dropped (cp kept) | **SURVIVED** — `174 passed, 1 skipped`, build green; the pin test silently disarms. But the property still holds: with my live-count scratch test present the same mutant is `1 failed, 174 passed, 1 skipped` — the environment, not the test, is what catches it. MINOR 2 + pin |
| M4 | **named:** the skip condition inverted (`!= "1"` → `== "1"`) | KILLED — the devShell run goes red: `FAILED …::test_sandbox_ledger_is_the_frozen_seed` |
| M5 | **named:** the seed fixture edited by one tally-bearing byte (`plan_defect = "vacuous"` → `"vacuouS"`, byte 2144) | KILLED — but by the **record** test, not the pin test: `'48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)' in '… 48 rej, 44 plan (vac 14, miss 16, under 8, fact 6)'`, `1 failed, 174 passed` |
| X1 | *outside:* cp **and** export both dropped — i.e. **main's own `flake.nix`** | **SURVIVED** — `174 passed, 1 skipped` clean; with my live-count scratch test present, `175 passed, 1 skipped` — the hard-coded live count passes. Two edits, but they are exactly the state of main. MINOR 1/2 |
| X2 | *outside:* the seed fixture edited by one **inert** byte (a comment character, byte 4) | **SURVIVED** — `175 passed`. Nothing observable changes; the tally-bearing bytes are guarded by M5. The pin test cannot see a seed edit by construction — both sides of its compare come from the same file |
| X3 | *outside:* the attack itself — a hard-coded live count in the sandbox | KILLED — pasted in **The consequence** |
| X4 | *outside:* a 61st row appended to the live ledger | KILLED (property held) — sandbox `175 passed`, devShell `174 passed, 1 skipped`, `tasks.py check` silent |
| X5 | *outside:* `RECORD_SHAPE` loosened to `re.compile(r"^(.*)")` | KILLED **in the sandbox** — `assert <re.Match … match='**Record: unavailable**'> is None`, `1 failed, 174 passed`. The shape test's negative case still bites under the pin |
| X6 | *outside:* the record test's source swapped `FROZEN_SEED` → `LIVE_LEDGER` | **SURVIVED the check** — sandbox `175 passed`; devShell `1 failed, 173 passed, 1 skipped`. Inside the sandbox the two are the same bytes, so nothing can tell them apart. MINOR 3 |

Probe, not a mutant — is a second marker available for the MINOR 2 pin? Yes.
With the export dropped, `NIX_BUILD_TOP` is still set inside the check:

```
E       AssertionError: export dropped but NIX_BUILD_TOP present
FAILED tests/evidence/test_scratch_marker.py::test_scratch_second_marker_available
1 failed, 174 passed, 1 skipped in 4.49s
```

So `skip only when NIX_BUILD_TOP is absent; assert EVIDENCE_UNIT_SANDBOX == "1"
when it is present` is a one-line change that kills M3 and X1 both.

## Checks

All from the fresh clone (`ef0852f`, base `61ffee8`, tree clean at start and end).

```
$ nix develop -c ruff check pkgs/evidence tests/evidence
All checks passed!                                            EXIT=0
$ nix develop -c ruff format --check pkgs/evidence tests/evidence
49 files already formatted                                    EXIT=0
$ nix develop -c pytest tests/evidence -q -rs
SKIPPED [1] tests/evidence/test_tasks.py:2686: the sandbox-pin assertion runs only in the evidence-unit sandbox
174 passed, 1 skipped in 4.56s
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild
evidence-unit> 175 passed in 4.64s                            EXIT=0
$ nix build .#checks.x86_64-linux.lint -L --no-link
lint> Found 0 warnings and 0 errors.                          EXIT=0
$ nix develop -c nixfmt --check flake.nix                      EXIT=0
$ nix develop -c statix check flake.nix                        EXIT=0
$ nix develop -c deadnix --fail flake.nix                      EXIT=0
$ nix develop -c githooks/pre-commit
render.test.mjs: all assertions passed                        EXIT=0
$ nix develop -c python3 pkgs/evidence/repomap.py --root . write && git diff --exit-code docs/MAP.md
MAP-CLEAN
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check
EXIT=0        (silent, 0 bytes on stdout)
$ git diff 61ffee8..HEAD -- docs/ledger
(empty)
$ git status --porcelain
(empty)
```

`nix flake check` was not run (minutes). No other check needs the pin — see
**The other readers**.

Commit convention: `git rev-list --count 61ffee8..HEAD` → `1`; the subject
`cmp`s byte-identical to the plan's `commit subject` for P3A/P3Ar3
(`SUBJECT IDENTICAL`); `Generated-By:` and `Co-Authored-By:` follow a blank line
at the end of the body; the touched files are `flake.nix`,
`tests/evidence/test_tasks.py`,
`tests/evidence/fixtures/ledger/plan-defects-seed.toml`,
`docs/runbooks/evidence.md` (all in `touches`) plus `docs/MAP.md` by rule; no
board commit (`docs/OPERATIONS.md` untouched); the result block
(`~/factory/runs/pb3ar3/P3Ar3.result`) is in the exact form,
`status=done`, `evidence-unit=pass lint=pass`, `FACTORY-COMMITS 1`. The body
pastes both `evidence-unit` runs and the consequence demonstration.

## Findings

**MINOR 1 — there is no red on main, and the commit body says there is.**
Plan `docs/superpowers/plans/2026-09-06-planning-agent.md` §P3Ar3 Step 1: "the
sandbox-pin test (red: the file differs, since main copies the live ledger)."
Main's `flake.nix` copies the live ledger *and* exports nothing, so the branch's
own skip condition (`tests/evidence/test_tasks.py:2685`) disarms the test there:

```
$ git show 61ffee8:flake.nix > flake.nix && git add -A
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link
evidence-unit> 174 passed, 1 skipped in 4.47s                  EXIT=0
```

Item 1's design and Step 1's prediction contradict each other — hence
`plan_defect: wrong-fact`. The commit body then labels the item-1 mutation's
output "Red on main — the sandbox-pin test with the flake.nix copy line absent
(the sandbox still copies the live 60-row ledger, so the byte compare fails)",
and pastes the identical run again two paragraphs down as "The item-1 mutation
(copy line dropped, export left in place)". The run is real; only its name is
wrong. The `FACTORY-NOTES` line repeats it ("red before green"). The test is
nevertheless load-bearing and provably red-able — M1, M4 and item 7 above — so
this is a labelling defect, not an unfalsifiable test.

**MINOR 2 — the export-drop mutant (M3) survives the check, and it is the same
edit that makes main's flake (X1) invisible.** Dropping
`export EVIDENCE_UNIT_SANDBOX=1` from `flake.nix:1134` leaves the build green at
`174 passed, 1 skipped`: the pin test disarms itself and says nothing. The
property is not lost — the `cp` still pins the environment, so a hard-coded live
count still fails (`1 failed, 174 passed, 1 skipped` with my scratch test
present) — which is why this is a MINOR and not a MAJOR under the matrix's own
condition. But drop both lines and the check is green with the live count
passing (X1), and that two-line state is precisely main. Pin, one line, proven
above: `NIX_BUILD_TOP` is set inside the check, so skip only when it is absent
and assert `EVIDENCE_UNIT_SANDBOX == "1"` when it is present. That kills M3 and
X1 and would have made the plan's "red on main" true.

**MINOR 3 — inside the sandbox nothing can tell the seed fixture from the
ledger path, so the record test's source is no longer enforced by the check.**
`tests/evidence/test_tasks.py:2635` reads `FROZEN_SEED`; swap it to
`LIVE_LEDGER` and the sandbox is `175 passed` (green) while the devShell is
`1 failed, 173 passed, 1 skipped` (X6). The regression that six rounds fought —
a record assertion reading the live ledger — is now caught only by the run the
runbook declares is not the truth. Harmless while the pin holds (the two files
are byte-identical there); worth a sentence in a later round, or a `# the
fixture, deliberately, not the ledger path` assertion the sandbox can see.

**MINOR 4 — `evidence-unit` no longer renders the Record line over the live
ledger at all, and the shape test's comment still claims it does.**
`tests/evidence/test_tasks.py:2658` reads "The LIVE ledger is asserted by SHAPE
only" — true in the devShell, false in the check, where `LIVE_LEDGER` is the
seed and `rej >= 48` holds with equality. The test is not vacuous there (X5
shows its negative case still kills a `.*` loosening), but its stated purpose —
"the ledger may grow without turning this check red" — is unfalsifiable under
the pin, because the ledger the check sees never grows. The live tree's ledger
is still validated in CI by `tasks.py check` in `lint` and the pre-commit hook;
only the *rendering* of it lost check coverage. A sentence in the comment would
close it.

**MINOR 5 — the pin test cannot detect a seed edit, by construction.** Both
sides of `assert ledger.read_bytes() == FROZEN_SEED.read_bytes()`
(`tests/evidence/test_tasks.py:2689`) come from the same file, so it verifies
that the copy happened, never what was copied. A tally-bearing seed edit is
caught by the record test (M5); a semantically inert one — I changed byte 4, a
comment character — is caught by nothing (`175 passed`, X2). Nothing turns on
it today; the `sha256` in this review and in P3Ar2b's is the standing record of
the seed's identity.

**Note, not a finding.** `front_matter_from = 2026-09-07` is tomorrow. From
then the Record also draws on review front matter, and `docs/reviews` is not
copied into the sandbox at all — so the sandbox's Record will diverge further
from the devShell's, in the same safe direction (less data, still pinned). The
pin covers the ledger file; the reviews are pinned by absence.

## Verdict

**APPROVED.** Every contract item is met and demonstrated. The pin test runs and
passes in the sandbox (`test_sandbox_ledger_is_the_frozen_seed PASSED`, no skip
line) and skips with its stated reason outside; dropping the `cp` turns the
build red on that test and dropping the `chmod` breaks the copy outright, so
both flake lines are load-bearing. The consequence is real and reproduced by me
end to end: today's live count `60 rej, 53 plan (vac 15, miss 20, under 9, fact
9)` passes in the devShell and fails in the check, and the seed count does the
exact opposite — the environment, not a scanner, is what decides. The guard and
all four helpers are deleted with no scratch attack files left, the frozen-seed
and shape tests stand and still kill their mutants under the pin, nothing else
reads the live ledger, no other check needs the same pin, a 61st row leaves the
check green and the ledger diff against main is empty, and every check is green
with one conforming commit. Four of the five named mutants die; the survivor
(the export dropped) does not defeat the property, because the copy still pins
the environment — the matrix's own condition for calling that a MAJOR is not
met. What is left is a plan wrong-fact the commit body repeats: main is green,
not red, and the one-line `NIX_BUILD_TOP` pin above would make it red and close
the only two-edit hole at the same time. That belongs in the next round's plan,
not in a rejection. **P10b is released.**
