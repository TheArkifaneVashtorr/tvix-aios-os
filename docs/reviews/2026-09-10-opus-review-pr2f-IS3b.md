---
plan_defect: underspecified
mutants_total: 2
mutants_killed: 2
mutants_outside_named: 3
model: opus
---
# Opus gate — seat run pr2f, task IS3b — APPROVED

## Summary

This round exists to close one hole IS3's gate found: `waveJobs = 0` evaluated
green — `maxUnits` derives to 1 and the strict `1 > 0` relation holds — and then
`factory-wave` refused at every dispatch. A guard written to make the wrong
configuration unrepresentable had a value that passed evaluation and broke every
wave run. It is closed, and closed where the section said to close it.

The decisive fact is measured directly, not inferred from the suite. On the
committed tree a `waveJobs = 0` configuration now fails evaluation, and the
**only** failed assertion is the new one:

```
error:
Failed assertions:
- services.seat-lane.waveJobs must be at least 1, got 0 -- factory-wave refuses a non-positive jobs cap
```

It refuses for the right reason rather than incidentally: `maxUnits` still
derives to 1 there, so the `maxUnits >= 1` and `maxUnits > waveJobs` rows both
still pass and neither is what fires. The boundary holds on the other side too —
`waveJobs = 1` evaluates green, derives `maxUnits = 2` and renders
`/etc/seat-lane/wave-jobs` as `"1"` — and `waveJobs = -3` refuses naming the
value. The eval guard's refusal set is now exactly `factory-wave`'s: the driver
rejects `'' | *[!0-9]* | 0`, and any `int >= 1` renders through `toString` as a
non-zero digit string, so no configuration that lands can now break a dispatch.

All six `acceptance` checks pass on the committed tree, red before green
reproduces independently with the commit body's exact error string, **both**
named mutants die and three more outside the named set die with them. The
subject is byte-identical to the section's, both trailers are right, one commit
folds IS3's cherry-pick as G6 orders, and all six changed files sit inside the
chain's `touches` union.

One minor is recorded, non-gating: three source-location cites (`factory-wave:139-141`)
were carried from the section's prose without being re-derived and are stale on
the committed tree, where the refusal is at `161-163`. The plan defect recorded
is the section's, and it is not that: Step 4's mutant B demands "the positive
fixture" that its own **Files** list never asks for.

**No G5 finding is raised, and the exemption was checked rather than assumed** —
see *Touches* below. This is the fourth gate in the chain where it could have
been raised falsely; `docs/OPERATIONS.md` is not in this commit at all.

**APPROVED.**

## Diff against the section

Fresh clone of `task/IS3b` at `00cca00`, base `0b27ada` from `IS3b.result`; the
base is an ancestor of live `main` (`db2a01e`).

```
$ git -C <clone> rev-list --count 0b27ada..00cca00
1

$ git -C <clone> diff --stat 0b27ada..00cca00
 docs/runbooks/seat.md           |  31 ++++++--
 flake.nix                       | 128 +++++++++++++++++++++++++++++++--
 nixosModules/seatLane.nix       |  40 +++++++++--
 tests/seat/test_seat_spool.py   |  37 ++++++++++
 tests/unit/80-seat-driver.bats  | 152 ++++++++++++++++++++++++++++++++++++++++
 tools/factory/seat/factory-wave |  30 ++++++--
 6 files changed, 397 insertions(+), 21 deletions(-)
```

**G6, the fold.** One commit, and it is a real fold rather than a stack of
replayed commits. Against IS3's own head (`b39eb84`) the four carried files are
byte-identical and only the two the section names carry new work:

```
$ for f in docs/runbooks/seat.md tools/factory/seat/factory-wave \
           tests/seat/test_seat_spool.py tests/unit/80-seat-driver.bats \
           nixosModules/seatLane.nix flake.nix; do
    git diff --quiet b39eb84 00cca00 -- $f && echo "SAME     $f" || echo "DIFFERS  $f"; done
SAME     docs/runbooks/seat.md
SAME     tools/factory/seat/factory-wave
SAME     tests/seat/test_seat_spool.py
SAME     tests/unit/80-seat-driver.bats
DIFFERS  nixosModules/seatLane.nix
DIFFERS  flake.nix
```

IS3b's own delta is exactly the section's four items and nothing else:
`seatLane.nix` gains the nine-line `waveJobs >= 1` assertion and its comment;
`flake.nix` gains `seatWaveJobsZeroSystem` (the `waveJobs = 0` negative system),
its `seat-assertion-negative` arm, `seatWaveJobsOneSystem` (the `waveJobs = 1`
positive fixture) and its `seat-eval` assertion. No other hunk.

The assertion sits inside the enable guard — `config = lib.mkIf cfg.enable` at
`:83`, `assertions` at `:84` — so it binds exactly when `/etc/seat-lane/wave-jobs`
exists and `factory-wave` reads it. Correct scope, neither over- nor under-reaching.

**Touches.** The chain's union is six names and the six changed files are
exactly it:

```
$ nix develop -c python3 pkgs/evidence/tasks.py touches \
    docs/superpowers/plans/2026-09-09-program.md IS3b
nixosModules/seatLane.nix
tools/factory/seat/factory-wave
tests/seat/test_seat_spool.py
tests/unit
flake.nix
docs/runbooks/seat.md
```

`IS3b.result` records `touches_extra: 0 / touches_disclosed: 0`, and it
reproduces. **`docs/OPERATIONS.md` is not in this commit** (`git diff --name-only
0b27ada..00cca00` lists six files, and it is not among them), so the G5
queue-block exemption does not even need to be invoked — there is nothing to
exempt. For completeness, because three prior gates in this chain raised this
falsely: `githooks/pre-commit` run now in the clone *does* regenerate the queue
block and exit 1 —

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
$ git diff -- docs/OPERATIONS.md      # the whole diff, one line, inside the block
-… EV2 FA1 FA10 FA11 FIX5 FIX5b FIX5c HH5 HH6 IS3 IS3b IS4 (…)
+… EV2 FA1 FA10 FA11 FIX5 FIX5b FIX5c HH5 HH6 IS3     IS4 (…)
```

— and that is neither an authored edit nor anything the seat could have
committed. `tasks.py` derives the queue from live state outside the repo
(`DEFAULT_RUNS_DIR = os.path.expanduser("~/factory/runs")`, `:136`), so `IS3b`
left the queue the moment `pr2f/IS3b.result` was written, i.e. *after* the
commit. The diff is confined to the `<!-- tasks:begin -->`/`<!-- tasks:end -->`
block, which G5 declares exempt. Not a finding.

`docs/MAP.md` is correctly untouched: IS3b adds no module, package, check or
test name (`seat-eval` and `seat-assertion-negative` both already existed), and
`lint`, which runs `repomap.py --root . check`, is green below.

**G9, areas.** `docs/ledger/subsystems.toml` puts `nixosModules/seatLane.nix` in
the `IS`/`isolation` row (`:30`) and `flake.nix` in the `PL`/`platform` row
(`:57`), so the declared `areas: isolation, platform` is right — the crossing is
real and unavoidable, since a seat-lane guard can only be proved by a fixture in
`flake.nix`. The section itself types no `**areas:**` line, but EV2 has not
landed (it is still in the queue), G9 leaves the rule to the gate by hand until
it does, and the plan grandfathers keys typed before EV2's landing. No wrong
outcome; noted, not charged.

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` line:

```
$ md5sum subj.commit subj.plan
c3502904a6b6738e17eb080899c37450  subj.commit
c3502904a6b6738e17eb080899c37450  subj.plan
$ wc -c subj.commit subj.plan
149 subj.commit
149 subj.plan
$ cmp subj.commit subj.plan && echo BYTE-IDENTICAL
BYTE-IDENTICAL
```

`(test: seat-eval, seat-assertion-negative, seat-unit, unit, host-core, lint)`
equals the section's `**acceptance:**` list — G4 satisfied. Both trailers, in
policy order (G3):

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pr2f)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `IS3b.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`), the run equal to `pr2f`. The body states in
one line that the gate's MAJOR was void under G5's queue-block exemption, as
Step 5 requires.

## Red before green

Reproduced in the clone without trusting the commit body, by restoring **IS3's**
module under **IS3b's** tests — Step 1's starting point exactly. The delta
between the two module versions is only the new assertion, so this is the
parent's implementation with the new arm applied and nothing else:

```
$ git -C <clone> checkout b39eb84 -- nixosModules/seatLane.nix
$ nix build .#checks.x86_64-linux.seat-assertion-negative -L --no-link
       … while calling the 'throw' builtin
         at …/flake.nix:2438:13:
         2438|             throw "seat-assertion-negative: services.seat-lane.waveJobs = 0 DID NOT FAIL the build (the waveJobs >= 1 assertion is missing or wrong)"
error: seat-assertion-negative: services.seat-lane.waveJobs = 0 DID NOT FAIL the build (the waveJobs >= 1 assertion is missing or wrong)
EXIT=1
```

That is the commit body's pasted red, string for string. The red is the arm the
change fixes, and it is specific — under the same red `seat-eval` stays **green**
(`EXIT=0`), so the new arm is what moves and not some collateral breakage:

```
$ nix build .#checks.x86_64-linux.seat-eval -L --no-link     # same red tree
EXIT=0
```

`git checkout 00cca00 -- nixosModules/seatLane.nix` restored the tree;
`git status --porcelain` and `git diff HEAD` are both empty.

The section's red and its mutant **A** are the same experiment — "remove the new
assertion" *is* "go back to IS3's module" — so the run above is reported under
both, honestly, rather than counted twice.

## Checks

Fresh clone, `XDG_CACHE_HOME` under the gate's scratch directory, `--rebuild` on
every check whose derivation was already in the store.

| check | command | result |
|---|---|---|
| seat-eval | `nix build .#checks.x86_64-linux.seat-eval -L --no-link --rebuild` | **PASS** — `checking outputs of '/nix/store/mx9hiddkfy4h4g0bn1rmvi1vk6vlhw5l-seat-eval-ok.drv'...`, `EXIT=0` |
| seat-assertion-negative | `… seat-assertion-negative -L --no-link --rebuild` | **PASS** — `checking outputs of '/nix/store/1dyh38hi46rj1c49aw24l0gj0i7s47ys-seat-assertion-negative-ok.drv'...`, `EXIT=0` |
| seat-unit | `… seat-unit -L --no-link --rebuild` | **PASS** — `seat-unit-tests> 63 passed in 0.13s`, `EXIT=0` |
| unit | `… unit -L --no-link --rebuild` | **PASS** — `unit-tests> ok 691 now-paragraph accepts the real board's Now paragraph`, `EXIT=0` |
| host-core | `nix build .#nixosConfigurations.core.config.system.build.toplevel -L --no-link` | **PASS** — `EXIT=0` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **PASS** — `EXIT=0` |

All six `acceptance` names are green. `63 passed` and `ok 691` reproduce the
commit body's counts exactly.

`lint` is the one check where `--rebuild` could not be used: the derivation was
not previously built in this store, and nix refuses (`some outputs of
'…-lint.drv' are not valid, so checking is not possible`), so it was built
fresh instead — which is strictly stronger than a rebuild-check, not weaker.
`githooks/pre-commit` run separately exits 1 on the derived board queue block
alone; that is the G5-exempt regeneration described under *Touches*, caused by
live state outside the repo, and every formatter and linter arm inside it is
clean.

The defaults are unchanged from IS3, re-derived rather than copied:

```
$ nix eval .#nixosConfigurations.core.config.services.seat-lane.waveJobs    → 8
$ nix eval .#nixosConfigurations.core.config.services.seat-lane.maxUnits    → 9
$ nix eval --raw …environment.etc."seat-lane/wave-jobs".text                → 8
$ nix eval --raw …environment.etc."seat-lane/max-units".text                → 9
```

## Negative controls

Evaluated directly against the committed module, outside the checks, to confirm
the assertion refuses for the right reason and admits the boundary:

| configuration | outcome |
|---|---|
| `waveJobs = 0` | **refused**, and the *only* failed assertion is `services.seat-lane.waveJobs must be at least 1, got 0 -- factory-wave refuses a non-positive jobs cap`. `maxUnits` derives to 1 there, so neither `maxUnits >= 1` nor `maxUnits > waveJobs` is what fires |
| `waveJobs = -3` | **refused**, naming the value: `…must be at least 1, got -3…` (the `maxUnits must be at least 1, got -2` row fires alongside it, as it should) |
| `waveJobs = 1` | **green** — `drvPath` produced; `maxUnits` = 2, `/etc/seat-lane/wave-jobs` = `"1"`. The boundary admits 1 and the `+1` relation survives at it |
| `waveJobs = 2` | **green** |

The guard's refusal set now coincides exactly with `factory-wave`'s. The driver
refuses `'' | *[!0-9]* | 0` (`tools/factory/seat/factory-wave:161-163`); every
`int >= 1` renders through `toString` as a non-zero digit string, so no
configuration that survives evaluation can be refused at dispatch. The three
remaining paths to a non-positive cap are all deliberate overrides that refuse
loudly and name their source — `FACTORY_JOBS`, `FACTORY_WAVE_JOBS_FILE`, and the
logged literal-5 last resort when the lane is disabled and no file exists.

## Mutants

Applied in the clone, run, reverted; `git status --porcelain` and `git diff HEAD`
are empty after each. `mutants_total: 2` counts the section's Step 4 set (A, B).
Three more were applied outside it: **c** because a bound deserves pressure from
both sides, and **e**/**f** because the section's Tests line claims "IS3's rows
carry over unchanged" and that claim deserves a mutant rather than a reading.
`--rebuild` is meaningless on a mutated source, so the mutant runs drop it.

| # | mutant | named? | outcome |
|---|---|---|---|
| **A** | the new `waveJobs >= 1` assertion removed (`git checkout b39eb84 -- nixosModules/seatLane.nix`, whose only delta is that block) | yes (Step 4) | **KILLED** — `seat-assertion-negative` red: `error: seat-assertion-negative: services.seat-lane.waveJobs = 0 DID NOT FAIL the build (the waveJobs >= 1 assertion is missing or wrong)`, `EXIT=1`. Specific: `seat-eval` stays green (`EXIT=0`) on the same tree |
| **B** | `assertion = cfg.waveJobs >= 1;` → `cfg.waveJobs > 1;` | yes (Step 4) | **KILLED** — `seat-eval` red on the positive fixture: `error: seat-eval: services.seat-lane.waveJobs = 1 must evaluate green (the boundary admits 1; a >1 assertion would refuse it)`, `EXIT=1`. Specific: `seat-assertion-negative` stays green (`EXIT=0`), since `0 > 1` still refuses — so `seat-eval` is the only discriminator, exactly as the section claims |
| c | `assertion = cfg.waveJobs >= 1;` → `cfg.waveJobs >= 0;` (the bound relaxed by one on the other side) | OUTSIDE | **KILLED** — `seat-assertion-negative` red: `error: seat-assertion-negative: services.seat-lane.waveJobs = 0 DID NOT FAIL the build (…)`, `EXIT=1` |
| e | IS3's strict relation neutralised: `assertion = cfg.maxUnits > cfg.waveJobs;` → `assertion = true;` | OUTSIDE | **KILLED** — `seat-assertion-negative` red: `error: seat-assertion-negative: services.seat-lane.maxUnits = waveJobs (8) DID NOT FAIL the build (the maxUnits > waveJobs assertion is missing or wrong)`, `EXIT=1` |
| f | IS3's derived default undone: `default = cfg.waveJobs + 1;` → `default = 5;` | OUTSIDE | **KILLED** — `seat-eval` red: `error: seat-eval: services.seat-lane.maxUnits must default to waveJobs + 1 (9) on core (the running-unit cap seat-submit enforces)`, `EXIT=1` |

Five for five. **B** and **c** together pin the bound at exactly 1 from both
sides — relaxing it by one admits the defect, tightening it by one refuses a
legitimate configuration — which is what makes the new `seatWaveJobsOneSystem`
fixture load-bearing rather than decorative. **e** and **f** turn the section's
"IS3's rows carry over unchanged" from an assertion into a measurement.

## Defects

None gating. One minor, plus the plan defect recorded in the front matter.

**MINOR-1 — three source cites are stale on the committed tree.** Implementer
defect (G11), non-gating.

`factory-wave:139-141` appears three times in the artifact: the new
`nixosModules/seatLane.nix` comment, the new `flake.nix` comment, and the commit
body. On the committed tree the non-positive refusal is at **161-163**:

```
$ git show 00cca00:tools/factory/seat/factory-wave | grep -n 'positive integer'
162:  '' | *[!0-9]* | 0) factory_die 2 "$jobs_cap_src must be a positive integer, got '$jobs_cap'" ;;

$ git show 0b27ada:tools/factory/seat/factory-wave | grep -n 'positive integer'
140:  '' | *[!0-9]* | 0) factory_die 2 "FACTORY_JOBS must be a positive integer, got '$jobs_cap'" ;;
```

Concrete failure scenario: a maintainer (or the next gate re-deriving the
guard's justification, which G11 requires) reads
`nixosModules/seatLane.nix:118-122`, opens `tools/factory/seat/factory-wave` at
139-141 on the landed tree, and finds IS3's resolution-order comment block
instead of the refusal the assertion cites as its whole reason for existing. The
stated justification cannot be checked at the stated location.

The number was *true* when the section was written — at the base it is the
`case` block at 139-141 — and it goes stale purely because G6 orders the fold
that moves it. G11 puts the duty to re-derive on the seat, and the seat copied
the section's prose instead. I record this as a minor rather than G11's MAJOR
deliberately: G11's MAJOR clause exists to catch fabricated *measurements* in
the commit body, and every measurement here reproduces exactly — `63 passed`,
`ok 691`, `8`, `9`, the red's error string, and both mutants' error strings. The
stale item is a prose cite whose staleness is a mechanical consequence of a rule
the same plan imposes, and no behaviour depends on it. The operator may overrule
me; the cost of the fix is three lines in whatever round next opens either file.

**Plan defect — Step 4 demands a fixture the Files list never asks for.** Class
`underspecified`.

The section's **Files** names exactly two edits: an `assertions` entry in
`nixosModules/seatLane.nix`, and "`flake.nix` — `seat-assertion-negative` gains
the arm proving `waveJobs = 0` is refused at eval". Step 4's mutant B then reads
"a legitimate `waveJobs = 1` is refused, and **the positive fixture** fails" —
definite article, as though it already existed. It does not: nothing in IS3's
tree evaluates a `waveJobs = 1` configuration, and the negative arm cannot kill
B, because under `> 1` the `waveJobs = 0` system still refuses and
`seat-assertion-negative` stays green (measured, mutant B above).

Concrete failure scenario: a seat implementing **Files** literally ships the
assertion and the negative arm, runs Step 4, finds mutant B alive, and either
reports an unkilled named mutant or discovers mid-round that it must invent an
artifact the plan never named. This seat inferred the fixture correctly and
built `seatWaveJobsOneSystem` plus its `seat-eval` assertion — the right call,
and the reason the round is approvable — but it was the plan's job to name it. A
section whose mutant table requires an artifact its Files list omits is
underspecified by one line.

## Verdict

**APPROVED.**

The hole IS3's gate found is closed, and closed for the right reason: on the
committed tree `waveJobs = 0` fails evaluation with the new assertion as the
*only* failure, while `maxUnits` still derives to 1 and its two rows still pass —
so the refusal is the new guard's and nothing else's. The boundary is pinned
from both sides: `waveJobs = 1` evaluates green with `maxUnits = 2` and
`/etc/seat-lane/wave-jobs` = `"1"`, and mutants **B** (`> 1`) and **c** (`>= 0`)
each turn exactly one check red. The eval guard's refusal set now coincides with
`factory-wave`'s, so no configuration that survives a switch can break a
dispatch.

All six `acceptance` checks pass (`seat-eval`, `seat-assertion-negative`,
`seat-unit` at `63 passed`, `unit` at `ok 691`, `host-core`, `lint`). Red before
green reproduces independently under IS3's own module with the commit body's
error string character for character, and is specific — `seat-eval` stays green
on the same tree. Both named mutants die; three more outside the named set die
with them, two of which convert the section's "IS3's rows carry over unchanged"
from a reading into a measurement. One commit folds IS3's cherry-pick as G6
orders, with the four carried files byte-identical to IS3's and only the two the
section names carrying new work. Subject byte-identical at
`md5 c3502904a6b6738e17eb080899c37450`, both trailers in policy order with the
model and run from `IS3b.result`, six changed files against a six-name union,
`docs/MAP.md` untouched and `lint` green over it.

**No G5 finding is raised.** `docs/OPERATIONS.md` is not in this commit at all;
the pre-commit's queue-block regeneration observed in the clone is driven by
`~/factory/runs` state written after the commit, is confined to the
`tasks:begin`/`tasks:end` block, and is exempt on the face of G5. Three previous
gates in this chain charged this falsely; it is checked here, and there is
nothing to charge.

The one minor is recorded rather than gated: three `factory-wave:139-141` cites
went stale when G6's fold moved the refusal to 161-163, so the assertion's stated
justification cannot be checked where it points. The plan defect is the
section's (`underspecified`): Step 4's mutant B requires a positive `waveJobs = 1`
fixture that the section's Files list never asks for, and only the seat's own
judgement kept that from costing a round.
