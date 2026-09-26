---
plan_defect: wrong-fact
mutants_total: 22
mutants_killed: 20
mutants_outside_named: 2
---
# Opus gate — seat run pb8, task P8b — APPROVED

Branch `task/P8b`, base `00ae401`, head `0acdb9d`, ONE commit, nine files
(+581/−11). Reviewed in a fresh clone
(`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-pb8-P8b`);
nothing under `/home/dalhaka/factory` or `/home/dalhaka/nixos-agent-env` was
modified except this file. No seat was run: `factory-plan.sh` was driven only
against fake `factory-plan-brief` and `factory-task` scripts under
`FACTORY_PLAN_BRIEF` / `FACTORY_BIN_OVERRIDE`, on fixtures under the scratch
directory.

## Summary

Both of pa9's MAJORs are fixed and the fixes are proved by the mutants that
survived last time. `tools/factory/plan` is in `checks.unit`'s copy list, the
`|| skip` guard is gone, and the acceptance build now reports
`ok 242 seat-plan.md carries the seat constraints and no typed task heading`
with no `# skip`; a typed heading appended to `seat-plan.md` turns that build
**red**, which is exactly the mutation that passed the gate on pa9. The size
rule has one home — `factory_plan_size` in `factory-lib.sh`, called by both
`factory-plan.sh` and `factory-plan-brief.sh` — and each boundary mutant
(`-le 1500 → -lt 1500`, `-le 4000 → -lt 4000`) is killed **twice**, once
through each caller's test. Contracts 3, 4, 5, 6 and 8 all hold, measured.

`unit`, `factory-unit` and `lint` are green from forced rebuilds; 114/114 bats
in the devShell with no skips; the real `~/factory/runs` is byte-identical
before and after every bats run I made.

Twenty of twenty-two mutants die, including all twelve P8 kills. The one named
survivor is contract 7's own mutation (“the export removed from one test → the
teardown check fails”): with **both** `setup` exports removed, no test in
`80-seat-driver.bats` writes to `$HOME/factory/runs` at all, so there is
nothing for the check to catch. That is a plan wrong-fact, not a vacuous test —
I proved the check has teeth by making a test write one entry, and the file
went red (`not ok 76 teardown_file failed`, naming the entry). No MAJOR.

## The sandbox

`flake.nix:2019`, immediately after the seat copy at :2014:

```
              mkdir -p tools/factory
              cp -r ${self}/tools/factory/seat tools/factory/seat
              # tests/unit/80-seat-driver.bats asserts on the seat's plan file
              # (no typed task heading), so copy it in or the test would skip
              # in the sandbox (P8b MAJOR-1: a skip there lets a typed heading
              # into the file with a green unit check).
              cp -r ${self}/tools/factory/plan tools/factory/plan
```

`tests/unit/80-seat-driver.bats:3293` is now a hard assertion (`[ -f "$f" ]`),
not a `|| skip`. `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild`
→ exit 0, 486 tests; the five P8 tests plus the two new ones, from
`nix log`:

```
ok 235 route.py and factory_route accept the plan role and refuse the planner role
ok 236 role plan resolves to the openrouter default row, not a typed plan row
ok 237 factory-plan sizes the spec, routes plan/docs, and hands the brief and seat-plan to factory-task
ok 238 factory-plan refuses an L spec or a refusing brief before the drafting seat runs
ok 239 factory_plan_size pins the size boundaries: 1500→S, 1501→M, 4000→M, 4001→L
ok 240 factory-plan rejects a name that is not ^[a-z0-9][a-z0-9-]{0,63}$ before composing
ok 241 factory-plan refuses a missing or unreadable spec with exit 2 before routing
ok 242 seat-plan.md carries the seat constraints and no typed task heading
```

The only `# skip` lines in the whole build are the six mount tests and the two
`setsid`/`ps` tests — the pre-existing ones. The mutant that survived pa9 now
dies in the acceptance check. Appended
`### PLAN-x (docs, S) — a typed heading` to `seat-plan.md`, `git add`, rebuild:

```
unit-tests> not ok 242 seat-plan.md carries the seat constraints and no typed task heading
unit-tests> #   `[ "$output" = "0" ]' failed
error: Cannot build '/nix/store/x4lxchipghmpfhz7sqhhjblxdcflvkpp-unit-tests.drv'.
       Reason: builder failed with exit code 1.
```

And the copy line itself is load-bearing: deleting `flake.nix:2019` alone (the
file restored) no longer skips — it **errors**, because the guard is gone:

```
unit-tests> not ok 242 seat-plan.md carries the seat constraints and no typed task heading
unit-tests> # (in test file tests/unit/80-seat-driver.bats, line 3293)
unit-tests> #   `[ -f "$f" ]' failed
```

Both reverted; the tree is at `0acdb9d` for every other result below.

## The size rule

One definition, and only one. `grep -rn '1500\|4000' tools/` over the whole
tree:

```
tools/factory/seat/factory-lib.sh:381:# Compute a spec's size label from its word count: S <= 1500 < M <= 4000 < L.
tools/factory/seat/factory-lib.sh:388:  if [ "$words" -le 1500 ]; then
tools/factory/seat/factory-lib.sh:390:  elif [ "$words" -le 4000 ]; then
```

(plus the prose line in `README.md:182`; the only other hit in `tools/` is an
unrelated token count in `tools/ledger/schema.md`). `factory-plan-brief.sh:409`
is now `size=$(factory_plan_size "$spec")` and `factory-plan.sh:75` is
`size=$(factory_plan_size "$spec_path")`. The plan offered `--size-only` or a
shared function; the shared function was taken, which also removes P8's
`FACTORY_PLAN_SIZE` seam entirely — nothing is passed between the two scripts
any more, so there is no seam left to drift.

The four boundaries **through `factory-plan.sh`** (fake brief + fake task,
`FACTORY_TOOLBOX_REPO` on a fixture tree; word counts confirmed with `wc -w`):

| spec | words | observed | exit |
|---|---|---|---|
| `s1500.md` | 1500 | brief called, `factory_plan_size` → `S`, seat reached | 0 |
| `s1501.md` | 1501 | → `M`, seat reached | 0 |
| `s4000.md` | 4000 | → `M`, seat reached | 0 |
| `s4001.md` | 4001 | `factory-plan.sh: factory-plan: an L spec is split before a plan is written` | 2 |

and through the brief's own `TARGET` part (`size:` in the packet) —
`tests/unit/83-plan-brief.bats:266,283-288` adds the 4,000-word fixture beside
P2b's 1,500 / 1,501 / 4,001, and the P2b test is still green.

Both boundary mutants die, each in **two** tests:

```
--- -le 1500 -> -lt 1500
not ok 72 factory_plan_size pins the size boundaries: 1500→S, 1501→M, 4000→M, 4001→L
#   `[ "$output" = "S" ]' failed                       (80-seat-driver.bats:3198)
not ok 79 factory-plan-brief sizes the spec by word count (P2 d)
#   `[[ "$output" == *"size: S"* ]]' failed            (83-plan-brief.bats:276)

--- -le 4000 -> -lt 4000
not ok 72 factory_plan_size pins the size boundaries: 1500→S, 1501→M, 4000→M, 4001→L
#   `[ "$output" = "M" ]' failed                       (80-seat-driver.bats:3204)
not ok 79 factory-plan-brief sizes the spec by word count (P2 d)
#   `[[ "$output" == *"size: M"* ]]' failed            (83-plan-brief.bats:287)
```

## Exit codes and names

`factory-plan.sh:94-96` is now an explicit `if ! brief=$(…); then exit 2; fi`.
Measured with fake briefs, `FACTORY_TOOLBOX_REPO` on the fixture tree:

| probe | observed stderr | exit |
|---|---|---|
| brief exits 2 | `fake brief: failing with 2` | **2** |
| brief exits 3 | `fake brief: failing with 3` | **2** |
| brief exits 1 | `fake brief: failing with 1` | **2** |
| brief exits 127 | `fake brief: failing with 127` | **2** |
| brief missing (shell 127) | `…/nope: No such file or directory` | **2** |
| routing row missing `model` | `factory_route: …/routing.toml: row 1: missing one of role/kind/size/model/effort` | **3** |
| routing table absent | `factory_route: no routing table: …/routing.toml` | **3** |

The brief's stderr is never swallowed (only stdout is captured), and 2 and 3
are distinguishable in every case. pa9's MINOR 1 is closed.

`<name>` (`factory-plan.sh:64-65`, `[[ $name =~ ^[a-z0-9][a-z0-9-]{0,63}$ ]]`),
checked before the spec is resolved, before routing, before any file name is
composed:

| name | exit | message / effect |
|---|---|---|
| `a/b` | 2 | `factory-plan: bad name: a/b` |
| `helm home 1` | 2 | `bad name: helm home 1` |
| `` (empty) | 2 | `bad name: ` |
| `-x` | 2 | `bad name: -x` |
| `Helm-Home` | 2 | `bad name: Helm-Home` |
| `x$(id)` | 2 | `bad name: x$(id)` (no expansion — the value is compared, not evaluated) |
| 64 × `a` | 0 | key `PLAN-aaa…a` (64) — the inclusive upper bound |
| 65 × `a` | 2 | `bad name: aaa…a` |
| `helm-home-1` | 0 | key `PLAN-helm-home-1`, out `docs/reviews/plan-drafts/2026-09-06-helm-home-1-deepseek-deepseek-v4-pro-0813.md` |
| `1abc`, `a` | 0 | accepted (leading digit and one character are inside the regex) |

pa9's MINOR 2 is closed.

## The seam and the tree

`factory-plan.sh:19-27`'s Env block names `FACTORY_PLAN_BRIEF`,
**`FACTORY_BIN_OVERRIDE`** ("factory-lib.sh's seam; the tests override it so
they never reach the real driver") and `FACTORY_TOOLBOX_REPO`. The bare
`FACTORY_BIN` no longer appears in the header — its only appearance in the file
is the `exec "$FACTORY_BIN/factory-task"` at :105, which is the value
`factory-lib.sh:23` derives from the override. `grep -n 'FACTORY_BIN=' tests/unit/*.bats`
→ **no hits**; every test uses `FACTORY_BIN_OVERRIDE`
(`80-seat-driver.bats:3167,3178,3227,3233,3267,3276`). Traced: `factory-plan.sh`
has exactly one `exec`, through `$FACTORY_BIN`, so with the override set no
path reaches the real driver; `factory_route` is a sourced shell function, not
a process. pa9's MINOR 3 is closed.

`factory-plan.sh:44` `export FACTORY_TOOLBOX_REPO` — the child sees it even
when the caller does not set it (fake brief printing its own env, caller's
variable unset):

```
child sees FACTORY_TOOLBOX_REPO=/home/dalhaka/nixos-agent-env
task PLAN=/home/dalhaka/nixos-agent-env/tools/factory/plan/seat-plan.md
```

`<spec>` is now resolved the brief's way (`:70`,
`realpath -m -- "$FACTORY_TOOLBOX_REPO/$spec"`), so the two agree from any CWD:

| spec | observed | exit |
|---|---|---|
| `docs/superpowers/specs/s1500.md` | resolved under the tree, brief called with the same relative string | 0 |
| an absolute path to that same file | `factory-plan.sh: no such spec: /…/s1500.md` | 2 |
| `../../etc/hostname` | `no such spec: ../../etc/hostname` | 2 |
| `docs/superpowers/specs/../specs/s1500.md` | accepted (normalises inside the tree) | 0 |

The absolute path used to pass `factory-plan.sh` and then be refused by the
brief (pa9 MINOR 5); both now refuse it. The `[ -r ]` guard is pinned — see the
mutant table. pa9's MINORs 4 and 5 are closed.

## Isolation

`80-seat-driver.bats:17-42` adds `setup_file`/`teardown_file`: a sorted
`ls -A1` of `$HOME/factory/runs` before any test, the same after, `diff -u` to
stderr and `return 1` with `a test wrote to the real ~/factory/runs` on any
change (both arms handle the directory being absent, which is the sandbox
case). `setup` (:55-56) exports `FACTORY_ROOT` and `FACTORY_RUNS` under
`$BATS_TEST_TMPDIR` for every test.

I listed the real runs dir immediately before and immediately after **every**
bats invocation I made (eight of them, including the mutant runs) and diffed:
identical each time. The baseline:

```
$ ls -A1 /home/dalhaka/factory/runs | sort > runs-b2.txt
$ nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/82-factory-dispatch.bats tests/unit/83-plan-brief.bats
1..114   (114 ok, 0 not ok, 0 skipped)
$ ls -A1 /home/dalhaka/factory/runs | sort > runs-a2.txt
$ diff runs-b2.txt runs-a2.txt   →   (no output)
```

(The dir did gain `pb3arb2` and `pb3arb2.wave.log` between my session-start
snapshot and my first bats run — the operator's own seat run pb3arb2, launched
while I was reading. Not this branch, and not inside any bats run: every
before/after pair I took brackets one bats invocation and every pair matched.)

The check's teeth, proved directly rather than by reading it. With `HOME`
redirected to a fixture home (`$SP/fakehome3/factory/runs`, containing one
`marker`), I added `mkdir -p "$HOME/factory/runs/leak-probe"` to one test:

```
ok 75 seat-plan.md carries the seat constraints and no typed task heading
not ok 76 teardown_file failed
# (from function `teardown_file' in test file tests/unit/80-seat-driver.bats, line 39)
#   `return 1' failed
# --- …/runs.before   +++ …/runs.after
# @@ -1 +1,2 @@
# +leak-probe
#  marker
# a test wrote to the real ~/factory/runs
# bats warning: Executed 76 instead of expected 75 tests
```

`bats` exit 1. The guard works, names the entry, and fails the file — and the
real runs dir was untouched by that experiment (checked before/after).

The contract's own mutation does **not** fire, though, and that is the plan's
error rather than the branch's — see Findings, MINOR 1.

## Tests and mutants

114/114 in the devShell (`80` 75, `82` 25, `83` 14), no skips; 486/486 in the
`unit` sandbox.

**Named mutants (20): 19 killed, 1 survived.**

| mutant | result |
|---|---|
| a typed heading in `seat-plan.md` | **killed in the `unit` sandbox** — `not ok 242` |
| the `flake.nix` copy line dropped | killed — `not ok 242`, `[ -f "$f" ]' failed` (errors, no longer skips) |
| `-le 1500` → `-lt 1500` | killed twice — `not ok 72` and `not ok 79` |
| `-le 4000` → `-lt 4000` | killed twice — `not ok 72` and `not ok 79` |
| the brief's exit passed through (`… \|\| :`) | killed — `not ok 71`, `[ "$status" -eq 2 ]' failed` |
| the `<name>` validation removed | killed — `not ok 73`, `bad name` missing |
| `[ -r "$spec_path" ]` → `true` | killed — `not ok 74`, `no such spec:` missing |
| the `setup` `FACTORY_ROOT`/`FACTORY_RUNS` exports removed | **SURVIVED** (MINOR 1) |
| `plan` in `factory-lib.sh` only (route.py reverted) | killed — `not ok 68` |
| `plan` in `route.py` only (lib reverted) | killed — `not ok 68` |
| a `plan` row written into `docs/ledger/routing.toml` | killed — `not ok 69` |
| the `FACTORY_PLAN=` export dropped from the exec | killed — `not ok 70` |
| the brief's exit ignored | killed — `not ok 71` |
| the `/` kept in the out path | killed — `not ok 70` |
| the L refusal dropped | killed — `not ok 71` |
| `--model "$model"` dropped | killed — `not ok 70` |
| `OPENROUTER_REASONING_EFFORT` emptied | killed — `not ok 70` |
| the `PLAN-` prefix dropped from the key | killed — `not ok 70` |
| `read -r effort model` (fields swapped) | killed — `not ok 70` |
| the model dropped from the out path | killed — `not ok 70` |

**Outside the named list (2): 1 killed.**

| mutant | result |
|---|---|
| one test writes `$HOME/factory/runs/leak-probe` (fixture `HOME`) | killed — `not ok 76 teardown_file failed` |
| `export FACTORY_TOOLBOX_REPO` (`:44`) removed | **SURVIVED** — 0 failures (MINOR 2) |

Total 22 mutants, 20 killed.

Everything P8 established still holds, re-measured on this tree:
`grep -c 'role = "plan"' docs/ledger/routing.toml` → `0`;
`factory_route --route openrouter plan docs S` → `deepseek/deepseek-v4-pro-0813 medium`;
`factory_task_kind_size tools/factory/plan/seat-plan.md PLAN-helm-home-1` →
`any any`; `seat-plan.md` has exactly two `## ` headings and no typed
`### KEY (kind, size)` heading; `factory-brief` composes them and appends the
ad-hoc packet.

## Checks

All from inside the clone, `--rebuild` where the derivation already existed:

| check | result |
|---|---|
| `shellcheck factory-plan.sh factory-plan-brief.sh factory-lib.sh` | 0 |
| `shfmt -d -i 2 -ci factory-plan.sh factory-plan-brief.sh` | 0 (no diff) |
| `ruff check tools/factory/route.py` | `All checks passed!` |
| `bats 80 + 82 + 83` | 114/114 ok, no skips; real runs dir identical before/after |
| `nix build .#checks.x86_64-linux.unit --rebuild` | 0 — 486 tests, `ok 242 … ` with **no** `# skip` |
| `nix build .#checks.x86_64-linux.factory-unit --rebuild` | 0 — `render.test.mjs: all assertions passed` |
| `nix build .#checks.x86_64-linux.lint --rebuild` | 0 |
| `bash tests/lint/bats-and-chain.sh` | 0 |
| `repomap.py write` + `git diff docs/MAP.md` | no diff |
| `tasks.py check` | silent, exit 0 |
| `githooks/pre-commit` | regenerated the board's queue block once (the clone reads the live `~/factory/runs`, where pb8 has already run, so `P8b` drops out of the derived queue). Reverted; **not** a finding — the branch's commit does not touch `docs/OPERATIONS.md`, and the diff was that one line. |

Commit convention: exactly one commit; subject byte-identical to the plan's
(`cmp` against the plan line, 194 bytes, exit 0); a blank line before the
trailers, so `git log -1 --format='%(trailers)'` now prints both
(`Generated-By: …`, `Co-Authored-By: Claude Fable 5.1 …`) — pa9's MINOR 6 is
closed; all nine touched files inside `touches` (`flake.nix` included, which
§P8b admits); no board commit; the `.result` carries
`FACTORY-RESULT status=done`, `FACTORY-CHECKS unit=pass factory-unit=pass
lint=pass`, `FACTORY-COMMITS 1` in the exact form.

## Red before green

There is no landed P8 to revert to (P8 was rejected, not integrated), so I
built the P8 state surgically on this base: P8's `factory-plan.sh`
(`git -C /home/dalhaka/factory/ws/pa9/P8 show task/P8:…`), the brief's inlined
size rule and the lib without `factory_plan_size` (the P8b diff for those two
files reversed), and the `flake.nix` copy line deleted — everything else, and
all tests, at P8b. A wholesale swap of `factory-lib.sh` is not a fair probe:
P8's branch is older than this base and its lib lacks `factory_abs_plan`, which
reds twenty unrelated driver tests.

```
not ok 70 factory-plan sizes the spec, routes plan/docs, and hands the brief and seat-plan to factory-task
#   `[ "$status" -eq 0 ]' failed              (P8 resolves <spec> against the CWD)
not ok 71 factory-plan refuses an L spec or a refusing brief before the drafting seat runs
#   `[[ "$output" == *"an L spec is split before a plan is written"* ]]' failed
not ok 72 factory_plan_size pins the size boundaries: 1500→S, 1501→M, 4000→M, 4001→L
#   `[ "$status" -eq 0 ]' failed              (no such function)
not ok 73 factory-plan rejects a name that is not ^[a-z0-9][a-z0-9-]{0,63}$ before composing
#   `[[ "$output" == *"bad name"* ]]' failed
```

(`not ok 68`, the role test, also reds — the lib revert takes the `| plan` arm
with it, which P8 had; ignore it.) The two cases the surgical tree masks, run
by hand against P8's script from the toolbox root:

```
$ … FACTORY_PLAN_BRIEF=<fake exiting 3> bash <P8's factory-plan.sh> r1 … s1500.md helm-home-1
fake brief: part M3 failed mid-packet
exit=3                                   # P8b's test asserts 2
$ … bash <P8's factory-plan.sh> r1 … s1500.md "a/b"
exit=0                                   # accepted; P8b's test asserts 2
```

and the sandbox line: with the copy line absent the seat-plan test does not run
at all — under P8's own `|| skip` guard it printed
`ok 217 … # skip tools/factory/plan/seat-plan.md not copied into the unit-check sandbox`
(pasted in the pa9 review); under P8b's guard-free test it errors,
`not ok 242 … [ -f "$f" ]' failed`. Restored: 114/114 green, `unit` green.

## Findings

No MAJORs.

### MINOR 1 — contract 7's own mutation cannot fire (a plan wrong-fact)

§P8b contract 7 predicts: "the export removed from one test → the teardown
check fails". It does not. I removed **both** `setup` exports
(`80-seat-driver.bats:55-56`) and ran the whole file with `HOME` redirected to
a fixture home: 75/75 green, and `find $HOME` showed **nothing** written —
not `factory/runs`, not `factory/ws`, not `factory/base`. No test in this file
leaks by omission today, so there is no leak for the teardown check to catch,
and the named mutant is unkillable by construction.

That does not make the check vacuous: a real leak dies (see "Isolation" — one
`mkdir` in one test turns the file red, `bats` exit 1, the entry named). The
belt (`setup`'s exports) and the braces (`teardown_file`) are both present; the
plan's premise about the state of the file is what is wrong.

The premise looks wrong at its source, too. The pa9 gate's own MINOR 3
records that it ran the **real** driver by hand, with `FACTORY_BIN=<fixtures>/bin`,
and pasted `factory-task: workspace: factory-ws run1 …/h/repo PLAN-nm` —
`factory-ws:54` is `mkdir -p -- "$FACTORY_BASE" "$FACTORY_WS/$run" "$FACTORY_RUNS/$run"`,
which creates exactly a `run1` entry in the real runs dir, and the gate's other
probes used `r1`. The strays the board attributes to "a driver bats test"
(`r1`, `run1`) are the shapes that gate's own manual probes make. I cannot
prove authorship after the fact — the entries were removed by hand — but no
bats test in this file produces them, before or after this branch.

Nothing to fix in the code. The board's line "fold a FACTORY_RUNS isolation
assertion into the next driver task" has been honoured, and honoured usefully;
the ledger's Facts should carry the correction so the next plan does not
re-prescribe an unkillable mutant.

### MINOR 2 — `export FACTORY_TOOLBOX_REPO` is unpinned

Removing `factory-plan.sh:44` leaves the whole file green. Every test passes
`FACTORY_TOOLBOX_REPO=…` in the command's own env prefix, so the child
inherits it whether or not the script exports it — the tests cannot see this
line. It does work (measured above, with the caller's variable unset the child
still sees `/home/dalhaka/nixos-agent-env`), and the split it prevents is the
one pa9's MINOR 4 described. One probe with `env -u FACTORY_TOOLBOX_REPO` and a
brief that echoes its own env would pin it.

### MINOR 3 — the exported `FACTORY_RUNS` is inert

`factory-lib.sh:21` is `FACTORY_RUNS=$FACTORY_ROOT/runs`, an unconditional
assignment, and every consumer (`factory-task:116`, `factory-wave:143`,
`factory-review:58`, `factory-integrate:45`, `factory-dispatch:185`,
`factory-ws:54`) reads it only after sourcing the lib. So of
`80-seat-driver.bats:55-56` only the `FACTORY_ROOT` export has any effect;
`FACTORY_RUNS` is overwritten before anything reads it. Contract 7 asked for
both and the test's own comment says as much, so this is honest belt-and-braces
— worth knowing only so nobody later "fixes" a leak by exporting `FACTORY_RUNS`
alone, which would do nothing.

### MINOR 4 — the `teardown_file` check can go red on the operator's own wave

The check diffs the **live** `~/factory/runs`, so a wave the operator launches
while `bats tests/unit/80-seat-driver.bats` is running in the devShell turns the
file red with `a test wrote to the real ~/factory/runs` and points at an entry
no test made. This is not theoretical: `pb3arb2` and `pb3arb2.wave.log`
appeared in that directory during this review. The sandbox is immune (no
`$HOME/factory/runs` there), and a false red fails closed and is cheap to read,
so this is a note rather than a defect — but if it bites, the fix is to compare
only entries whose mtime falls inside the run, or to name the entries the file
could plausibly have made.

### MINOR 5 — the name test leans on the live-repo default

`80-seat-driver.bats:3210-3236` sets `FACTORY_BIN_OVERRIDE` but not
`FACTORY_TOOLBOX_REPO`, so everything after the name check would resolve
against `factory-lib.sh:27`'s hard-coded `/home/dalhaka/nixos-agent-env`. Today
the refusal fires first, so the live tree is never read; under the very mutant
the test exists to kill (validation removed) it reads the live repo's
`routing.toml` and stats a path there. Harmless (reads only, and the fake
driver still fences the seat), but the fixture tree is one more assignment
away.

### MINOR 6 — the commit body does not carry Step 4's pastes

§P8b Step 4 asks for the sandbox `ok` line and the before/after runs listing to
be pasted. They are in the seat's report and transcript
(`~/factory/runs/pb8/P8b.log:2272,2523`), not in the commit message, so the
history alone does not carry the evidence. The house convention (subject shape
plus trailers) is met, and the `.result` block is exact, so this is a note.

## Verdict

**APPROVED.** Both pa9 MAJORs are closed and each is proved by the mutant that
survived last time: the seat-plan assertion runs in `unit` (`ok 242`, no skip)
and a typed heading now reds the acceptance build; the size rule has exactly
one definition and both boundaries are pinned twice over. Contracts 3–6 and 8
hold, measured value by value; all twelve P8 kills still die; `unit`,
`factory-unit` and `lint` are green from forced rebuilds; the real
`~/factory/runs` is untouched by every bats run, and the new teardown check
demonstrably fails when a test does write there.

20 of 22 mutants die. The one named survivor is contract 7's own mutation,
whose premise — that some test leaks by omission — is false on this file; the
check it doubts is proved to work by a direct leak. Six minors, none of them
worth a round: two are coverage (the `export`, the name test's fixture), two
are notes about the isolation check's mechanics, one is the ledger's Facts, one
is where the evidence was pasted.
