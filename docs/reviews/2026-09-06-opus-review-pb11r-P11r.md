---
plan_defect: none
mutants_total: 30
mutants_killed: 29
mutants_outside_named: 3
reviewer: opus
majors: null
minors: 7
---
# Opus gate — seat run pb11r, task P11r — APPROVED

## Summary

One commit (`12eb379`), nine files (+1,116/−35), every one inside `touches`,
subject byte-identical to the plan's (`cmp` against line 475's value and P11's
line 131 → identical), both trailers in order, no board commit.

**The sandbox `unit` build is GREEN**, and the last line the commit body pastes
reproduces byte-for-byte. That was the first thing I ran, in a pristine clone,
with `--rebuild`:

```
unit-tests> ok 388 blocks files older than 7 days are reaped on each run
EXIT=0
```

Both of P11b's majors are closed and pinned. All six contract items behave as
specified. **29 of 30 mutants die** — P11b's 22 (including P11's twelve and
CR3rb's three), the plan's five named P11r mutations, and two more the gate
matrix names; the thirtieth is the matrix's own behaviour-preserving probe
("the helper duplicated"), which survives by construction and is reported
below, not as a defect. `shellcheck` is clean on all six scripts, `bats` is
133/133 across the three files, `factory-unit` and `lint` build green, the lint
gate's only failure is the known queue-block regeneration between the markers,
`repomap.py write` leaves `docs/MAP.md` untouched, `tests/lint/bats-and-chain.sh`
exits 0, and the red block reproduces (with one extra red the body did not
list — MINOR-1).

Facts checked in a fresh clone of `task/P11r` at
`/tmp/claude-1000/…/scratchpad/gate-pb11r-P11r`. Every driver invocation used a
fixture repo with `FACTORY_ROOT`/`FACTORY_RUNS` under the scratchpad and fake
`dsh-openrouter`/`factory-task`/`factory-wave`/`factory-brief`/`factory-ws` on
PATH or under `FACTORY_BIN_OVERRIDE`. The real repo and the real
`~/factory/runs` were never written; the only live command was the read-only
`tools/ritual.sh inflight`, plus a metadata-only copy of the runs dir into
scratch for the budget measurement.

## The sandbox build

The seat's `FACTORY-CHECKS unit=pass lint=pass` is true this time, and the paste
is real.

| what | expected | observed | exit |
|---|---|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` (pristine clone) | green | 388/388 ok | **0** |
| the body's pasted last line | matches | `unit-tests> ok 388 blocks files older than 7 days are reaped on each run` — identical | — |
| `nix build .#checks.x86_64-linux.lint` | green | — | 0 |
| `nix build .#checks.x86_64-linux.factory-unit` | green | `render.test.mjs: all assertions passed` | 0 |

**Item 1, my own grep.** No test in either file launches a driver through its
own shebang. Every `$SEAT/` occurrence outside a `$REAL_BASH` invocation is
one of: a `route.py` path assignment (`80:792, 856, 897, 1016`), an output
assertion (`80:1529`), a plain variable (`80:1871`), the structural test's own
patterns (`80:2773, 2775`), or an argument to a `bash "$3"` wrapper in the two
`setsid` tests (`80:1553, 1585`) — which hand an interpreter and in any case
`skip` when the sandbox has no real `setsid`/`ps`. `exec` appears nowhere as a
driver launch: `92:835` is `printf 'exec %q "$@"\n'` and `92:876` is
`exec 0<&-`, neither matching the guard's regex.

**The structural test's own grep does catch the P11b shape.** I applied the
exact regression at `tests/unit/80-seat-driver.bats:2547`:

```bash
    run "$REAL_BASH" -c 'cd -- "$1" && exec "$2" r1 "$3" "K1"' _ "$workdir" "$SEAT/factory-wave" "$repo"
```

Locally `bats` goes red on the structural test alone; in the sandbox **both**
tests die and the build fails:

```
not ok 63 no bats test launches a driver through its own shebang          (local)

unit-tests> not ok 223 factory-wave makes FACTORY_PLAN absolute once and exports the same value to every task
unit-tests> #   `[ "$status" -eq 0 ]' failed
unit-tests> not ok 230 no bats test launches a driver through its own shebang
unit-tests> #   `[ "$status" -eq 1 ]' failed
error: Cannot build '/nix/store/6ljh7ycjqbafdvmzvivsl0vskk5gvj4j-unit-tests.drv'.
       Reason: builder failed with exit code 1.
```

Reverted with `git restore`, tree clean.

## The hint

Contract 3 holds completely. `tools/ritual.sh:400-412` builds either form and
`%q`-quotes plan, repo, every group and `--then`. Fixture: one dead-pid run with
a hostile `run.meta`, the printed hint text taken verbatim after `relaunch: `
and evaluated with `FACTORY_PLAN` removed from the environment and a recording
fake `factory-wave` on PATH.

| fixture | printed | eval exit | child saw |
|---|---|---|---|
| repo `/tmp/re po's/repo`, plan `/tmp/pl an"s/p.md`, group `K L`, `--then` `gate; ff && rm -rf /` | `relaunch: FACTORY_PLAN=/tmp/pl\ an\"s/p.md factory-wave r1 /tmp/re\ po\'s/repo K\ L --then gate\;\ ff\ \&\&\ rm\ -rf\ /` | 0 | `PLAN=[/tmp/pl an"s/p.md]` `ARGC=5` `ARG2=[/tmp/re po's/repo]` `ARG3=[K L]` `ARG5=[gate; ff && rm -rf /]` |
| no `plan:` line | `relaunch: # plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave r1 /tmp/repo K --then gate\;\ ff` | **0** | **nothing launched** (no rec file) |
| group `K"\a b` (CR3rb round-trip) | `… factory-wave r1 /tmp/repo K\"\\a\ b` | 0 | `ARG3=[K"\a b]` |

Every field is byte-identical through the fake, the space and the quote in the
repo survive (P11b MINOR-1 closed), and the `; ff && rm -rf /` inside `--then`
stays one argument — it is passed, never executed. The unknown form is a bash
comment: pasted verbatim it exits 0 and launches nothing (P11b MINOR-5 closed;
P11b's form was a syntax error).

**Live**, from the clone over the real runs dir
(`env -u FACTORY_RUN bash tools/ritual.sh inflight /home/dalhaka/nixos-agent-env`,
exit 0, **695 chars**, no hint line at all):

```
cr20 wave-group-1 - running - log age 119m
cr21 wave-group-1 - running - log age 26m
pa10 wave-group-1 - running - log age 30m
pa1 integrate - running - log age 85m
pa2 integrate - running - log age 84m
pa6 wave-group-1 - running - log age 61m
pa7 integrate - running - log age 45m
pa7 wave-group-1 - running - log age 71m
pb11r wave-group-1 - running - log age 10m
pb11 wave-group-1 - running - log age 64m
pb2 wave-group-1 - running - log age 18m
pb3ar P3Ar - pid 3811762 alive - log age 0m
pb3ar wave-group-1 - pid 3811736 alive - log age 0m
pb3a wave-group-1 - running - log age 29m
pb4 integrate - running - log age 87m
pb6 integrate - running - log age 84m
sb8 integrate - running - log age 67m
… and 240 stale logs older than 2h
```

`grep -l '^plan: ' /home/dalhaka/factory/runs/*/run.meta | wc -l` → **0** of 23,
exactly as the body says. My output differs from the body's paste only because
the seat's own `runs/pb11r/P11r.result` has since been written, so `pb11r` now
has no missing group. Replaying the body's state on a metadata-only scratch
copy of the runs dir with that one `.result` removed reproduces both lines
byte-for-byte:

```
pb11r P11r - running - log age 0m - relaunch: # plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave pb11r /home/dalhaka/nixos-agent-env P11r
pb11r wave-group-1 - running - log age 0m - relaunch: as above
```

The live paste is honest, and it happens to demonstrate the once-per-run rule on
the seat's own run.

## Integrate

Contract 2 holds. `factory-integrate:69, 74, 119, 189` add the counter and both
summary lines; `:183` puts it in the rc; `:191` gates the recipe on
`[ "${#merged[@]}" -eq "${#keys[@]}" ]`. Nine-key fixture (a clean key, a
board-prose key, a queue-block key, a rival-edit key, an orphan-history key, a
missing workspace), a fresh base clone per run, `FACTORY_CHECK_CMD=true`:

| run | expected | observed | exit |
|---|---|---|---|
| `NOPE K2` | SKIP, MERGE, `skipped: 1`, rc≠0, no recipe | `SKIP NOPE …` / `MERGE K2 ok` / `merged: K2` / `conflicts: 0` / `refused: 0` / **`skipped: 1`**, no `pull --ff-only` | **1** |
| `K2 K3` (all merged) | recipe printed, rc 0 | `merged: K2 K3` / `0` / `0` / `0` + `git -C … pull --ff-only …` | **0** |
| `K1 K5` (all refused) | each counted, rc≠0 | `REFUSED K1: docs/OPERATIONS.md changed outside the queue block` / `REFUSED K5: no merge base with origin/main` / `merged: (none)` / `conflicts: 0` / `refused: 2` / `skipped: 0` | 1 |
| `NOPE NADA` (all skipped) | rc≠0 | `merged: (none)` / `conflicts: 0` / `refused: 0` / `skipped: 2` | 1 |
| `K3 K4 NOPE K1` (mixed) | one line each | `MERGE K3 ok` / `CONFLICT K4` / `SKIP NOPE` / `REFUSED K1` / `merged: K3` / `conflicts: 1` / `refused: 1` / `skipped: 1` | 1 |

P11b MAJOR-2 is closed: the `NOPE K2` run that P11b exited **0** now exits 1 and
withholds the recipe. Checks run for merged keys only — after the mixed run,
`git log integ/r1` carries `k3: add z` and nothing else, the tree holds `z` but
not K1's board edit (`docs/OPERATIONS.md` line 2 still reads `prose line`), and
`CHECK custom pass` ran once.

## The plan path

Contract 4 holds for **both** drivers, through **one** helper.
`factory-lib.sh:56` defines `factory_abs_plan` (`realpath -- "$1"`);
`factory-wave:103` and `factory-task:82` are its only callers; `git grep` finds
no second implementation and no other `realpath` in the seat.

`factory-wave` (fake `factory-task` recording its inherited `FACTORY_PLAN`):

| case | meta `plan:` | child env | run.meta written? | exit |
|---|---|---|---|---|
| relative `FACTORY_PLAN=rel.md`, cwd `…/fx-wave/launch` | `…/fx-wave/launch/rel.md` | identical | yes | 0 |
| symlink `link.md → real/p.md` | **`…/fx-wave/real/p.md`** | identical | yes | 0 |
| `env -u FACTORY_PLAN` | — | never started | **no** | **2** (`FACTORY_PLAN is unset — name the plan …`) |

`factory-task` (fake `factory-brief` recording the plan path it is handed):

| case | brief saw | `runs/<run>` created? | exit |
|---|---|---|---|
| relative `rel.md`, cwd `…/fx-task/launch` | `…/fx-task/launch/rel.md` | yes | 0 |
| symlink `link.md → real/p.md` | **`…/fx-task/real/p.md`** | yes | 0 |
| mode-000 plan | `<no rec>` | **no** | **2** (`no such file: …/zero.md`) |
| `env -u FACTORY_PLAN` | `<no rec>` | **no** | **2** |

P11b MINOR-2 and MINOR-3 are both closed: the basename is resolved and
`factory-task` absolutises its own plan. `factory-dispatch` is untouched by this
diff and still sets `FACTORY_PLAN="$plan_file"` at `:204`; its 15 bats tests are
green, including `--dry-run` (FD1b a) and the real launch through `factory-wave`
(FD1b b).

## The in-flight reader

Contract 5 holds. `tools/ritual.sh:269` declares `local -A hinted_run`, `:400`
reads it, `:403` sets it, `:401` prints `relaunch: as above`.

Fixture, three dead groups in one run (`92-ritual.bats` test 34 pins two): one
full hint, the rest `as above`, and `grep -c FACTORY_PLAN=` is 1.

**Budget.** Measured on a mtime-faithful metadata copy of the live runs dir
(124 run dirs, 23 `run.meta`), each `run.meta` given an 81-char `plan:` line and
every `.result` removed so every dead wave prints a hint — the same contrivance
the P11b gate used, and all three readers run against the *same* fixture:

| reader | in-flight part | full hints | `as above` |
|---|---|---|---|
| `main` (144cb1c) | 2,470 chars | — | — |
| P11b | 4,655 chars | 23 | 0 |
| **P11r** | **3,274 chars** | **13** | **10** |

The once-per-run rule buys back 1,381 chars — about 30% of P11b's hint cost, and
it turns 23 hints into 13. `tools/session-start.sh:188` caps that part at 1,000,
so this contrived state still truncates (as `main`'s 2,470 already did), which
is why `README.md:138-139` now says so and points at `run.meta`:

> it may be cut by the session brief's 1,000-character in-flight cap, and the
> authoritative relaunch source is always `~/factory/runs/<run>/run.meta`.

Today's real cost is 695 chars with zero hints, comfortably under the cap. P11b
MINOR-4 is answered.

## Tests and mutants

`bats --count`: `80-seat-driver` 45 → **67**; `92-ritual` 46 → **51**;
`82-factory-dispatch` 15, unchanged. 133/133 pass in the devShell. No old test
is deleted or renamed; four pre-existing `92-ritual` hint assertions
(`:248, :454, :476, :515`) change only their expected text to the new unknown
form — the verdicts (status 0, a hint present, the anti-assertion absent) are
unchanged.

Every mutant was applied by exact-text replacement, proven to have changed the
tree (`git diff --quiet` before and after), run, then reverted with a clean
`git diff` check.

**The plan's five named P11r mutations**

| # | mutant | file | died? | on |
|---|---|---|---|---|
| M1 | the absolute-plan test reverted to the direct `exec` | 80-seat-driver.bats | **yes** | structural test 63, **and the sandbox build red** (223 + 230) |
| M2 | the skip left out of the rc | factory-integrate | yes | 80:64 |
| M3 | the recipe printed anyway (`if true`) | factory-integrate | yes | 80:64 |
| M4 | the repo spliced unquoted | ritual.sh | yes | 92:33 |
| M6 | the basename left unresolved (dir-only abs) | factory-lib.sh | yes | 80:66, 67 |

**Two more the gate matrix names**

| # | mutant | file | died? | on |
|---|---|---|---|---|
| M5 | the unknown form made a bare launch | ritual.sh | yes | 92:15, 26, 27, 29, 30, 32 |
| M7 | the once-per-run rule dropped (`if false`) | ritual.sh | yes | 92:34 |

**P11b's 22, all still dying**

| # | mutant | file | died? | on |
|---|---|---|---|---|
| p1 | the `plan:` read dropped | ritual.sh | yes | 92:31, 33, 34 |
| p2 | `export FACTORY_PLAN="$plan_abs"` dropped | factory-wave | yes | 80:56 |
| p3 | `[ -r ]` removed | factory-lib.sh | yes | 80:57 |
| p4 | the grammar sentence back inside the template | factory-brief | yes | 80:54, 55 |
| p5 | `conflicts=$((#keys − #merged))` restored | factory-integrate | yes | 80:59 |
| p6 | the all-refused summary lines dropped | factory-integrate | yes | 80:60, 61 |
| p7 | the empty merge base no longer refuses | factory-integrate | yes | 80:61 |
| p8 | `tr '[:cntrl:]' ' '` dropped | factory-task | yes | 80:62 |
| p9 | ACCEPTED loosened to `status[:=]` | factory-task | yes | 80:62 |
| p10 | the 2026-09-04 default plan restored | factory-task | yes | 80:46 |
| p11 | the wave guard moved after `run.meta` | factory-wave | yes | 80:47, 56, 66 |
| p12 | the `plan:` line dropped from `run.meta` | factory-wave | yes | 80:48, 56, 66 |
| p13 | the board mask comparison dropped | factory-integrate | yes | 80:49, 50, 59, 60 |
| p14 | merge base → `origin/<default>` tip | factory-integrate | yes | 80:51, 61 |
| p15 | the queue-block masking dropped | factory-integrate | yes | 80:50 |
| p16 | the near-miss arm dropped | factory-task | yes | 80:52, 53, 62 |
| p18 | the 200-byte cut removed | factory-task | yes | 80:53 |
| p19 | the commit-verification block disabled | factory-task | yes | 80:42, 44, 45 |
| p20 | the bare-`ok` rejection removed | factory-task | yes | 80:45 |
| p21 | `group: %q` → `%s` | factory-wave | yes | 80:29, 30, 41 |
| p22 | `refused` no longer sets `overall_rc` | factory-integrate | yes | 80:49, 50, 59 |
| p17 | (P11 M-H, the same site as p9) | factory-task | yes | 80:62 |

P11b's two caveats are both closed. Mutant p2's killer, test 56, now **runs in
the sandbox** — I confirmed it by watching it fail there under M1 — so the
`export` clause is pinned inside the acceptance check, not only locally. And
the `SKIP` exit code is now pinned by 80:64.

**The behaviour-preserving probe (the matrix's "helper duplicated").** Replacing
`plan=$(factory_abs_plan "$plan")` in `factory-task` with an inline
`plan=$(realpath -- "$plan")` leaves every one of the 67 tests green — the
mutant **SURVIVES**. Nothing pins the "one helper in `factory-lib.sh`" clause;
only the behaviour is pinned, on both drivers, by 80:56/66/67. That is a
structural preference, not a behaviour, so I do not treat it as a surviving
mutant — but the answer to the matrix's question is: no, nothing pins one
definition (MINOR-3).

**The three P11 rules, re-checked directly.** `FACTORY_PLAN` unset → exit 2
before `run.meta`/`runs/<run>` on both drivers (tables above). The board mask at
the merge base with K1–K5 (table in *Integrate*): prose-outside refused,
untouched merged, orphan history refused, and the mask compared against `mb`,
not the tip (p14 dies). The near-miss classifier, on a fake seat:

| payload | result line | notes | exit |
|---|---|---|---|
| `FACTORY-RESULT status:done` | `status=failed exit_code=0` | `result-misparse: FACTORY-RESULT status:done` | 2 |
| `status=bogus` + TAB + two ESC sequences | failed | `result-misparse: FACTORY-RESULT status=bogus and  [31mred [0m tail` (tab and ESC → spaces) | 2 |
| `**FACTORY-RESULT status=done**` | failed | `result-misparse: **FACTORY-RESULT status=done**` | 2 |
| a good block | `status=done` | the seat's own | 0 |
| a near miss then a good block | `status=done` | never re-classified | 0 |

## Checks

| check | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **0** — 388/388 |
| `nix develop -c shellcheck` on `factory-task factory-wave factory-integrate factory-brief factory-lib.sh tools/ritual.sh` | clean, 0 |
| `nix develop -c bats tests/unit/80-seat-driver.bats 82-factory-dispatch.bats 92-ritual.bats` | **133/133 ok** |
| `bats --count` 80 / 92 / 82 | 67 (was 45) / 51 (was 46) / 15 (unchanged) |
| `nix build .#checks.x86_64-linux.factory-unit` | 0 |
| `nix build .#checks.x86_64-linux.lint` | 0 |
| `nix develop -c githooks/pre-commit` | 1 — only `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the single changed line is line 15, between the markers at 14 and 16, and the branch never commits the board |
| `python3 pkgs/evidence/repomap.py --root . write` | no diff to `docs/MAP.md` |
| `bash tests/lint/bats-and-chain.sh` | 0 |
| new host-PATH dependency under `tools/factory/seat` | `realpath` (coreutils) is new — no `python3`, `jq` or `node`; present in the `unit` sandbox, as the green build proves (MINOR-4) |
| commits on `144cb1c..HEAD` | 1 |
| subject vs plan line 475 / P11's line 131 | `cmp` → identical |
| trailers | `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pb11r)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` |
| files vs `touches` | the same nine, no more |
| the run's `.result` block | the exact four lines then the record; `status=done`, `unit=pass lint=pass`, `FACTORY-COMMITS 1` (the branch has 1) |

Contract 6's four items are all present in the commit body and all real: the red
block (reproduced below), the sandbox build's last line (reproduced above), the
live in-flight output (reproduced above from the seat's own state), and the
fixture hint that was evaluated
(`# plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave r1 /tmp/repo K`).

## Red before green

P11b's seven non-test files
(`git -C /home/dalhaka/factory/ws/pb11/P11b show task/P11b:<path>`; six differ —
`factory-brief` is byte-identical between the rounds) against this branch's two
test files: **107 ok, 11 not ok** of 118.

```
1..118
not ok 64  factory-integrate counts a skipped key in skipped: and exits non-zero without printing the fast-forward recipe
not ok 66  a symlinked FACTORY_PLAN is recorded by its real path, basename included
not ok 67  factory-task absolutises its own FACTORY_PLAN through realpath before composing the brief
not ok 82  inflight reports a dead wave as live-by-rule with a relaunch hint that reproduces the argv
not ok 93  inflight's relaunch hint reproduces the original argv including --then
not ok 94  inflight's relaunch hint for a mixed wave lists only the missing key's group
not ok 96  inflight round-trips a %q-quoted group containing a quote and a backslash
not ok 97  inflight's relaunch hint for a pre-P11 run (no plan: line) names the plan as unknown
not ok 99  the plan-unknown relaunch hint is paste-safe: a comment that evaluates to exit 0 and launches nothing
not ok 100 a repo path with a space round-trips through the relaunch hint
not ok 101 inflight prints the full relaunch hint once per run, then as above
```

Every line the body claims is here; **82 is one the body did not list**
(MINOR-1). Restoring the branch's files → 118/118 ok, tree clean.

The structural test is correctly *green* in this state: it greps the test files,
which are P11r's. Its own red proof is M1 above — the reverted `exec`, which
takes both the test and the sandbox build down.

## Findings

No MAJORs.

### MINOR-1 — the red block is a subset: `not ok 82` is missing

The body lists ten red tests; against P11b's drivers eleven go red. `not ok 82
inflight reports a dead wave as live-by-rule with a relaunch hint that
reproduces the argv` is a pre-existing test whose expected text this round
changed, and it fails on P11b for exactly the reason the round exists. Contract
6 asks for "the red block", not "a red block"; a reader comparing counts would
find one unexplained failure.

### MINOR-2 — the structural grep misses a driver path held in a variable

`tests/unit/80-seat-driver.bats:2773-2775`:

```bash
  run grep -nE 'exec[[:space:]]*"' "$driver_bats" "$ritual_bats"
  [ "$status" -eq 1 ]
  run grep -nE '(run|exec)[[:space:]]+"\$SEAT/' "$driver_bats" "$ritual_bats"
  [ "$status" -eq 1 ]
```

Both patterns are literal. A launch written as `drv="$SEAT/factory-wave"; run
"$drv" …` matches neither, and I confirmed the structural test stays green under
that shape. The contract's own wording ("a `"$SEAT/…"` launch outside a
`$REAL_BASH` invocation") is broader than the regex. The backstop is sound —
such a launch still dies 126 in the sandbox and takes the `unit` build with it,
which is the acceptance check the seat must now paste — so this costs a clear
diagnosis, not correctness. Conversely, pattern (a) is over-broad: any future
`exec "` in either file, driver or not, trips it. Erring toward refusal is the
right direction here; it is worth a comment saying so.

### MINOR-3 — nothing pins "one helper in factory-lib.sh"

Inlining `realpath -- "$plan"` in `factory-task:82` in place of the
`factory_abs_plan` call leaves all 67 tests green. The contract's structural
clause is unpinned; only the behaviour it produces is. A `grep`-shaped test
(one definition, two call sites) would close it, the way the no-direct-exec test
closes its own structural clause.

### MINOR-4 — `realpath` is a new external dependency for the seat

`factory-lib.sh:57` is the first use of `realpath` under `tools/factory/seat`;
`main` used only `cd -P`/`pwd -P`. It is coreutils and it is in the `unit`
sandbox (the green build proves it), so this is a note, not a problem — but the
seat's stated dependency set (`sed awk grep cmp tr head printf git dirname
basename`) grew and the README does not say so.

### MINOR-5 — the run name is the one hint field not `%q`-quoted

`tools/ritual.sh:405, 407` splice `$run` — `basename` of the run directory
(`:299`) — raw into both forms, while plan, repo, groups and `--then` are all
quoted. A run directory holding a space would split the hint's argv. Contract 3
names four fields and this is not one of them, and run keys are orchestrator-
chosen, so it is theoretical; it is also the last unquoted field left.

### MINOR-6 — the unknown form is paste-safe only after `relaunch: `

`# plan unknown — …` is a comment, so evaluating the hint launches nothing — but
the whole in-flight line (`pb11r P11r - running - log age 0m - relaunch: # …`)
is not; pasting it whole is a `pb11r: command not found`. That is a harmless
failure and matches the contract exactly, but the README's description of the
hint does not say that the `relaunch: ` prefix must be stripped first.

## Verdict

APPROVED. The sandbox `unit` build is green and its pasted last line reproduces;
both of P11b's majors are fixed and pinned (the skipped key exits 1 with its own
`skipped:` line and no recipe; every test launches its driver through an
interpreter, with a structural test and the sandbox itself both refusing the
regression); the hint quotes every field the contract names and round-trips a
space and a quote byte-for-byte; the plan-unknown form is a comment that
evaluates to exit 0 and launches nothing; both drivers absolutise through one
`realpath` helper and record a symlinked plan by its real name; the hint costs
one line per run; and 29 of 30 mutants die, the thirtieth being a
behaviour-preserving probe. Six minors, none blocking; MINOR-1 (the incomplete
red block) and MINOR-3 (the unpinned one-helper clause) are the two worth
folding into a later round's minor list.
