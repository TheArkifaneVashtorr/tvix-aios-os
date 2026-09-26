---
plan_defect: implementer
plan_defect_secondary: underspecified
mutants_total: 22
mutants_killed: 22
mutants_outside_named: 1
reviewer: opus
majors: 5
minors: 6
---
# Opus gate — seat run pb11, task P11b — REJECTED

## Summary

One commit (`a10d973`), nine files (+816/−26), all inside `touches`, subject
byte-identical to the plan's (`cmp` on line 417's value → identical), both
trailers, no board commit. Every one of the five contract items is implemented
and behaves as specified, and **22 of 22 mutants die** — the nine P11b names,
P11's twelve, and one extra I invented. `shellcheck` is clean on all six
scripts, `bats` is 125/125 across the three files, `factory-unit` and `lint`
are green, the lint gate's only failure is the known queue-block regeneration
inside the markers, `repomap.py write` leaves `docs/MAP.md` untouched, and
`tests/lint/bats-and-chain.sh` exits 0.

Two things stop it.

**MAJOR-1 — `unit`, a named acceptance check, is RED.** The new test
`factory-wave makes FACTORY_PLAN absolute once …` launches the driver as
`exec "$2"` — through the script's own `#!/usr/bin/env bash` shebang — instead
of `"$REAL_BASH" "$SEAT/factory-wave"` the way every other test in the file
does. The build sandbox has no `/usr/bin/env` (`flake.nix` says so in its own
comment and `patchShebangs` only touches `tests/mocks`), so in the `unit`
derivation the launch dies with exit 126 before the driver runs. The seat
reported `FACTORY-CHECKS unit=pass lint=pass`; `unit` fails.

**MAJOR-2 — `factory-integrate` now exits 0 with a key silently dropped.**
Replacing `conflicts=$((${#keys[@]} - ${#merged[@]}))` with an incrementing
counter removed the missing-workspace `SKIP` from the exit code. `factory-integrate
r1 <repo> NOPE K2` prints `SKIP NOPE …`, `MERGE K2 ok`, `conflicts: 0`,
`refused: 0`, the fast-forward recipe — and exits **0**. Both P11 and today's
`main` exit 1 for that run. Nothing in the plan asked for this, and no test
pins it.

Facts checked in a fresh clone of `task/P11b` at
`…/scratchpad/gate-pb11-P11b`. Every driver invocation used a fixture repo, a
`FACTORY_ROOT`/`FACTORY_RUNS` under the scratchpad and fake
`dsh-openrouter`/`factory-task`/`factory-wave` on PATH. The real repo and the
real `~/factory/runs` were never written; the only live command was the
read-only `tools/ritual.sh inflight`.

## The hint

Contract 1 is right. `tools/ritual.sh:314` reads `plan_meta` and `:391-399`
builds either form. A fixture runs dir with (a) a dead post-P11 run whose
`plan:` is `/tmp/pl an's/plan.md` (a space **and** a single quote), (b) a dead
pre-P11 run with no `plan:`, (c) a live run:

```
dead K - running - log age 0m - then: gate; ff - relaunch: FACTORY_PLAN=/tmp/pl\ an\'s/plan.md factory-wave dead /tmp/repo K\ L --then gate\;\ ff
live K3 - pid 2710896 alive - log age 0m
old K2 - running - log age 0m - relaunch: (plan unknown — set FACTORY_PLAN) factory-wave old /tmp/repo K2
```

(a)'s hint text, taken verbatim and evaluated in a shell with
`FACTORY_PLAN` removed from the environment and a recording `factory-wave` on
PATH:

```
PLAN=[/tmp/pl an's/plan.md]      ARGC=5
ARG1=[dead] ARG2=[/tmp/repo] ARG3=[K L] ARG4=[--then] ARG5=[gate; ff]
```

`%q` survives the space and the quote byte for byte (`cmp` against the meta's
value → IDENTICAL), and the argv is run/repo/groups/`--then` exactly as before.
(b) prints the "plan unknown" form and is never a bare launch — pasted verbatim
it is a bash **syntax error** (`syntax error near unexpected token
'factory-wave'`, exit 2, the fake never runs), so it cannot launch a wave
without a plan. (c) prints no hint. Table:

| fixture | expected | observed | exit |
|---|---|---|---|
| (a) dead, `plan:` with space+quote | `FACTORY_PLAN=<%q> factory-wave …` | as above; child saw the meta's value byte-identical | 0 |
| (b) dead, no `plan:` | `(plan unknown — set FACTORY_PLAN) factory-wave …` | as above; evaluating it launches nothing | 2 (syntax) |
| (c) live wave pid | no hint | no hint | 0 |

**Live**, from the clone over the real runs dir
(`bash tools/ritual.sh inflight /home/dalhaka/nixos-agent-env`, exit 0,
776 chars):

```
cr20 wave-group-1 - running - log age 67m
cr21 CR2r3b - pid 2665208 alive - log age 0m
cr21 wave-group-1 - pid 2665188 alive - log age 0m
pa1 integrate - running - log age 33m
pa1 wave-group-1 - running - log age 96m
pa2 integrate - running - log age 31m
pa2 wave-group-1 - running - log age 92m
pa3 wave-group-1 - running - log age 98m
pa4 wave-group-1 - running - log age 107m
pa5 wave-group-1 - running - log age 104m
pa6 wave-group-1 - running - log age 8m
pa7 wave-group-1 - running - log age 18m
pb11 wave-group-1 - running - log age 12m
pb4 integrate - running - log age 34m
pb4 wave-group-1 - running - log age 74m
pb6 integrate - running - log age 32m
pb6 wave-group-1 - running - log age 73m
sb8 integrate - running - log age 15m
… and 233 stale logs older than 2h
```

**No hint line prints live at all today.** Two reasons, both checked: (1) not
one of the 18 live `run.meta` files carries a `plan:` line — `grep -l '^plan: '
/home/dalhaka/factory/runs/*/run.meta` returns nothing, because P11 was
rejected and its `factory-wave` never landed (`cr18`, `pa3`, `pb11`, `pa7` all
read `run:/repo:/base:/pid:/launched:/group:` only); so every live run would
print the "plan unknown" form, not `FACTORY_PLAN=`. (2) Even that does not
appear, because each dead wave's group already has a `status=done` `.result`,
so `missing_groups` is empty. Step 4's demanded live paste is therefore
unsatisfiable until this branch's `factory-wave` has launched a run — a fact
the plan got wrong, not the implementer. The commit body carries neither the
live lines nor the red block (MINOR-6).

## The plan path

Contract 2 is right and complete. `factory-wave:100-106` computes `plan_abs`
and `export`s it; `factory-lib.sh:47` adds `[ -r "$1" ]`.

| case | expected | observed | exit |
|---|---|---|---|
| relative `FACTORY_PLAN=plan.md`, cwd `…/fx2/launch` | meta and child agree, absolute | `plan: …/fx2/launch/plan.md`; child `plan=…/fx2/launch/plan.md` | 0 |
| symlinked **file** `link-p.md` → `real/p.md` | — | recorded **as given** (`…/fx2/link-p.md`); child identical | 0 |
| symlinked **directory** `linkdir/p.md` | — | dir realpathed (`…/fx2/real/p.md`); child identical | 0 |
| mode-000 plan, `factory-task` | exit 2, nothing created | `factory-task: no such file: …/p000.md`; `runs/` and `ws/` absent | 2 |
| mode-000 plan, `factory-wave` | exit 2, nothing created | `factory-wave: no such file: …/p000.md`; `runs/` absent, recorder never ran | 2 |
| a directory as plan, both | exit 2 | `no such file: …/fx2/real` | 2 |
| unset (`env -u`) / empty, both | refuse, nothing created | `FACTORY_PLAN is unset — name the plan (FACTORY_PLAN=<plan.md> …) or launch through factory-dispatch` | 2 |
| scratch-launcher `"K1 K2"` one group | chain, both see the plan | `K1`, then `K2 --after K1`; both `plan=<abs>`; `group: K1\ K2`; `then: gate; ff` | 0 |

So the answer to "realpath or absolute-as-given?" is: the **directory**
components are realpathed (`cd -P … && pwd -P`), the final component is kept as
given, so a symlinked plan file is recorded by its link path. Both are absolute
and readable; meta and child never disagree. `factory-dispatch` is untouched
(`:204` still sets `FACTORY_PLAN="$plan_file"`) and its 15 bats tests are green,
including `--dry-run` (FD1b a) and a real launch through `factory-wave`
(FD1b b).

## The brief

Contract 3 is right. Diffing `factory-brief`'s output for the same fixture
section, P11 → P11b, the ONLY change is the move:

```
 - End your final reply with a summary in exactly this format, each item on
-  its own line and nothing after it:
+  its own line and nothing after it. The first line is exactly the result
+  line, one space, status=done|partial|failed — no colon, no markdown; any
+  other spelling is recorded as failed:
 FACTORY-RESULT status=<done|partial|failed>
 …
-  The first line is exactly FACTORY-RESULT, one space, …
```

The sentence is prose inside the summary bullet, above the four template lines,
and names "the result line". Lines in the whole brief that contain
`FACTORY-RESULT` and no `<`: **0** on P11b, **1** on P11. Measured with a fake
seat that echoes the composed brief (`$4`) and exits:

| brief | `.result` notes | exit |
|---|---|---|
| P11b | `FACTORY-NOTES the seat produced no usable FACTORY-RESULT line; see <log>` | 2 |
| P11 | `FACTORY-NOTES result-misparse:   The first line is exactly FACTORY-RESULT, one space, …` | 2 |

pa3's MINOR-3 is closed. The two trailers are byte-unchanged
(`Generated-By: …`, `Co-Authored-By: …`), and the rest of the brief is identical.

## Integrate

Contract 4 is implemented — and it broke the skip path.

Nine-key fixture, `main` moving both its prose and its queue block after every
fork, one run `K1 K2 K3 K4 K5 K6 K7`:

| key | branch's board change | expected | observed |
|---|---|---|---|
| K1 | prose outside the markers | REFUSED | `REFUSED K1: docs/OPERATIONS.md changed outside the queue block` |
| K2 | none | merge | `MERGE K2 ok` |
| K3 | only between the markers | merge or conflict | `CONFLICT K3` (main's block moved too — a textual conflict, as in P11) |
| K4 | inside **and** outside | REFUSED | `REFUSED K4` |
| K5 | none, forked before main's board moved | merge | `MERGE K5 ok` |
| K6 | orphan history | REFUSED | `REFUSED K6: no merge base with origin/main` |
| K7 | block only, conflicting | conflict | `CONFLICT K7` |

Summary `merged: K2 K5` / `conflicts: 2` / `refused: 3` / `head: 0bd2a0e`,
exit 1, `CHECK custom pass` run once against a tree holding only K2 and K5
(`git log integ/r1` carries `k2: add y` and `k5: add z`, not `k1:`/`k4:`).
pa3's MINOR-4 is closed: one refusal beside one merge prints `refused: 1` and
`conflicts: 0`. MINOR-5 is closed: `K1` alone → `no branch merged cleanly` /
`merged: (none)` / `conflicts: 0` / `refused: 1`, exit 1; `K1 K4 K6` → `refused: 3`,
exit 1. MINOR-8 is closed: the orphan branch is refused, never merged.

The regression (MAJOR-2), measured on the same fixture:

```
$ factory-integrate r1 <src> NOPE K2        # P11b
SKIP NOPE: no workspace …/ws/r1/NOPE
MERGE K2 ok
CHECK custom pass
merged: K2 / conflicts: 0 / refused: 0
exit=0

$ factory-integrate r1 <src> NOPE K2        # P11 and main (c2d5e7f)
SKIP NOPE: no workspace …/ws/r1/NOPE
MERGE K2 ok
merged: K2 / conflicts: 1
exit=1
```

`factory-integrate:174-178`'s own comment states the intent — "conflicts counts
just the merge failures, never a refusal **or a skip**" — but the skip then
reaches no counter at all, so the run's exit code says success while a key was
dropped, and the script prints the fast-forward recipe. The orchestrator's gate
recipe reads that exit code.

## The near miss

Contract 5 is right; every P11 row still holds. Fake seat, one payload per run,
`.result` read back:

| payload | line 1 | notes | exit |
|---|---|---|---|
| `FACTORY-RESULT status:done` (colon, no space) | `status=failed exit_code=0` | `result-misparse: FACTORY-RESULT status:done` | 2 |
| `…status=bogus\tand\x1b[31mred\x1b[0m tail` | failed | `result-misparse: FACTORY-RESULT status=bogus and ^[[31mred ^[[0m tail` (tab and ESC → spaces) | 2 |
| 300-byte near miss | failed | note body exactly **200** bytes | 2 |
| `FACTORY-RESULT status=done\r` (CRLF) | `status=done\r` — CR is `[[:space:]]`, so **ACCEPTED**, as in P11 | seat's own notes | 0 |
| near miss then a real `status=done` block | `status=done` | seat's own notes | 0 |
| a real block then a near miss | `status=done` | never re-classified | 0 |
| only a line containing `<` | failed | `the seat produced no usable FACTORY-RESULT line; see <log>` | 2 |

Plus, from the bats rows: `status: done`, `status=succeeded`,
`**…**`, `- …` each recorded verbatim; `status=partial` and
`status=done extra=1` accepted with no `result-misparse`.

## The in-flight reader

`tools/ritual.sh`'s only change is the hint (13 lines; `plan_meta` added to the
`local` list at :264, read at :314, used at :391-399). All 48 tests in
`92-ritual.bats` pass, count 46 → 48; the four pre-existing hint assertions are
unchanged in verdict, only in expected text (they now read
`(plan unknown — set FACTORY_PLAN) factory-wave …`, which is what a fixture
`run.meta` without `plan:` must produce). The 1,200-byte cap test, the gate-done
test and the stale-summary tests are untouched and green.

Budget: the live INFLIGHT part is 776 chars today with zero hints, against
`cap_part INFLIGHT … 1000` in `tools/session-start.sh:188`. To measure the new
form's cost I copied the live runs dir to scratch, inserted
`plan: /home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-06-planning-agent.md`
(81 chars) into every `run.meta` and removed the dead runs' `.result` files so
every dead wave prints a hint: the reader emits **5,402** chars where main's
form emits **2,837** — each hint grows by 94 chars (`FACTORY_PLAN=` + the path).
Both already overflow the 1,000-char part cap in that contrived state, so this
is not a new break — `cap_part` truncates — but the number of hint-carrying runs
that fit before truncation drops from about five to about two (MINOR-4).

## Tests and mutants

`bats --count`: `80-seat-driver` 45 → **62** (17 appended: P11's nine plus eight
new); `92-ritual` 46 → **48**; `82-factory-dispatch` 15, unchanged. 125/125 pass
in the devShell. No old test is renamed or deleted, and no old verdict changes.

Every mutant was applied with `perl -0777 -i` (or a whole-file swap for the
brief), proven to have changed the tree (`git diff --quiet` before running),
run, then reverted with a clean `git diff` check.

| # | mutant | file | died? | on |
|---|---|---|---|---|
| 1 | the `plan:` read dropped (`plan_meta=""`) | ritual.sh | yes | 92:31 |
| 2 | `export FACTORY_PLAN="$plan_abs"` dropped | factory-wave | yes | 80:56 |
| 3 | `[ -r ]` removed (back to `-f`) | factory-lib.sh | yes | 80:57 |
| 4 | the sentence back inside the template (P11's brief) | factory-brief | yes | 80:55, 58 |
| 5 | `conflicts=$((#keys − #merged))` restored | factory-integrate | yes | 80:59 |
| 6 | the all-refused exit without `conflicts:`/`refused:` | factory-integrate | yes | 80:60, 61 |
| 7 | `[ -n "$mb" ] &&` skip restored | factory-integrate | yes | 80:61 |
| 8 | `\| tr '[:cntrl:]' ' '` dropped | factory-task | yes | 80:62 |
| 9 | ACCEPTED loosened to `status[:=]` (no space) | factory-task | yes | 80:62 |
| 10 | P11 M-A: the 2026-09-04 default plan restored | factory-task | yes | 80:46 |
| 11 | P11 M-B: wave guard moved after `run.meta` | factory-wave | yes | 80:47, 48, 56 |
| 12 | P11 M-C: the `plan:` line dropped | factory-wave | yes | 80:48, 56 |
| 13 | P11 M-D: the board check dropped | factory-integrate | yes | 80:49, 50, 59, 60 |
| 14 | P11 M-E: `mb` → `origin/<default>` tip | factory-integrate | yes | 80:51, 61 |
| 15 | P11 M-F: the block masking dropped | factory-integrate | yes | 80:50 |
| 16 | P11 M-G: the near-miss arm dropped | factory-task | yes | 80:52, 53, 62 |
| 17 | P11 M-H: ACCEPTED loosened to `status[:=][[:space:]]*` | factory-task | yes | 80:53, 62 |
| 18 | P11 M-I: the 200-byte cut removed | factory-task | yes | 80:53 |
| 19 | CR3rb M-I: the commit-verification block disabled | factory-task | yes | 80:42, 44, 45 |
| 20 | CR3rb M-I2: the bare-`ok` rejection removed | factory-task | yes | 80:45 |
| 21 | CR3rb M-E: `group: %q` → `%s` | factory-wave | yes | 80:29, 30, 41 |
| 22 | *(outside the named set)* `refused` no longer sets `overall_rc` | factory-integrate | yes | 80:49, 50, 59 |

**22 of 22.** Both of pa3's survivors (MINORs 6 and 7) are now pinned.

Two caveats. Mutant 2's only killer is test 56 — the test that cannot run in the
`unit` sandbox at all, so inside the acceptance check that clause is pinned by
nothing. And nothing anywhere pins the `SKIP` exit code: the regression in
MAJOR-2 passes all 125 tests.

## Checks

| check | result |
|---|---|
| `shellcheck` on the six scripts | clean, exit 0 |
| `bats tests/unit/80-seat-driver.bats tests/unit/82-factory-dispatch.bats tests/unit/92-ritual.bats` | 125/125 ok |
| `bats --count` 80 / 92 / 82 | 62 (was 45) / 48 (was 46) / 15 (unchanged) |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | **exit 1** — `not ok 222` (below) |
| `nix build .#checks.x86_64-linux.factory-unit -L --no-link` | 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 |
| `nix develop -c githooks/pre-commit` | 1 — only the queue-block regeneration; the one changed line lies between `tasks:begin`/`tasks:end`, and the branch never commits the board |
| `python3 pkgs/evidence/repomap.py --root . write` | no diff to `docs/MAP.md` |
| `bash tests/lint/bats-and-chain.sh` | 0 |
| new host-PATH dependencies | none — `sed awk grep cmp tr head printf git dirname basename`; no python3/jq/node |

The `unit` failure, from the pristine clone's build log:

```
not ok 222 factory-wave makes FACTORY_PLAN absolute once and exports the same value to every task
# (in test file tests/unit/80-seat-driver.bats, line 2543)
#   `[ "$status" -eq 0 ]' failed
```

Diagnosed by re-running the same derivation from a scratch copy with the
status and output echoed to fd 3:

```
DBGSTATUS=126
DBGOUT<<_: /build/tests/unit/../../tools/factory/seat/factory-wave: /usr/bin/env: bad interpreter: No such file or directory>>
DBGMETA<<cat: …/factory/runs/r1/run.meta: No such file or directory>>
```

and proven by the one-word repair — passing `$REAL_BASH` as the interpreter
(`exec "$4" "$2" r1 …`), the way all 61 other tests invoke the drivers — which
makes the whole `unit` check build green (`DBGSTATUS=0`, exit 0).

## Red before green

P11's four drivers and `factory-lib.sh`
(`git -C /home/dalhaka/factory/ws/pa3/P11 show task/P11:<path>`, head
`e96158e`) plus main's `tools/ritual.sh`, against this branch's two test files:
**97 ok, 13 not ok**.

```
not ok 55 factory-brief states the grammar in prose before the template, without the literal label
not ok 56 factory-wave makes FACTORY_PLAN absolute once and exports the same value to every task
not ok 57 factory-task refuses a mode-000 (unreadable) FACTORY_PLAN before any workspace or run dir exists
not ok 58 factory-task records an echoing seat that copies the brief as no-usable-line, not a near miss
not ok 59 factory-integrate counts a refused key in refused: only, never in conflicts:
not ok 60 factory-integrate still prints refused: N when every key is refused
not ok 61 factory-integrate refuses a key with no merge base, never silently merging it
not ok 77 inflight reports a dead wave as live-by-rule with a relaunch hint that reproduces the argv
not ok 88 inflight's relaunch hint reproduces the original argv including --then
not ok 89 inflight's relaunch hint for a mixed wave lists only the missing key's group
not ok 91 inflight round-trips a %q-quoted group containing a quote and a backslash
not ok 92 inflight's relaunch hint for a pre-P11 run (no plan: line) names the plan as unknown
not ok 93 inflight's relaunch hint carries FACTORY_PLAN= from run.meta so it is a live launch
```

Every case the plan names goes red except one: test 62 (the control byte and
`status:done`) stays **ok** on P11. That is correct and expected — pa3 found
those two behaviours already right and merely unpinned, so the new test can only
be shown to fail against a mutant, and mutants 8 and 9 do exactly that.
Restoring the branch's six files → 110/110 ok, tree clean.

## Findings

### MAJOR-1 — the `unit` check is red: the new wave test runs the driver through a shebang the sandbox cannot resolve

`tests/unit/80-seat-driver.bats:2542`

```bash
run "$REAL_BASH" -c 'cd -- "$1" && exec "$2" r1 "$3" "K1"' _ "$workdir" "$SEAT/factory-wave" "$repo"
```

`$2` is executed directly, so the kernel reads `factory-wave`'s
`#!/usr/bin/env bash`. `flake.nix:2025-2030` says the build sandbox has no
`/usr/bin/env` and only `patchShebangs tests/mocks` runs, so the launch exits
126 and every assertion below it is moot: in the acceptance environment this
test never exercises `plan_abs` at all. Measured above: `not ok 222`, exit 126,
`bad interpreter`. Passing `"$REAL_BASH"` as the interpreter — the pattern of
the other 61 tests — makes `unit` build green. `acceptance: unit, lint` and the
seat's own `FACTORY-CHECKS unit=pass` are both wrong.

### MAJOR-2 — `factory-integrate` exits 0 when a key is skipped for a missing workspace

`tools/factory/seat/factory-integrate:68, 105, 174-178` vs `main`'s
`conflicts=$((${#keys[@]} - ${#merged[@]}))`

```
$ factory-integrate r1 <src> NOPE K2
SKIP NOPE: no workspace …/ws/r1/NOPE
MERGE K2 ok
merged: K2 / conflicts: 0 / refused: 0
exit=0            # P11 and main: conflicts: 1, exit=1
```

Contract 4 asked only that a refusal stop being counted twice. Turning
`conflicts` into a counter also dropped the `SKIP` branch at `:71-74` from the
exit code, so an integration that dropped a key reports success and prints the
fast-forward recipe. No test objects. Count the skip (its own `skipped: N` line,
or fold it into the non-zero rc) and pin it.

### MINOR-1 — the hint still splices `repo:` unquoted

`tools/ritual.sh:400`: `[ -n "$repo_meta" ] && relaunch="$relaunch $repo_meta"`.
The plan path is `%q`-quoted and the groups are, but a repo path with a space
would still break the hint's argv. Pre-existing (unchanged by this branch), but
this was the round that made the hint executable, so it is now load-bearing.

### MINOR-2 — a symlinked plan file is recorded by its link path

`factory-wave:100` resolves the directory (`cd -P … && pwd -P`) but keeps
`$(basename)`. `FACTORY_PLAN=…/link-p.md` → `plan: …/link-p.md`. Absolute and
readable, so the contract holds, but the record does not name the file the seat
actually read. Say which you mean in the README, or use `realpath`.

### MINOR-3 — `factory-task` never absolutises its own plan

Contract 2 binds `factory-wave` only, and `factory-task` calls `factory-brief`
before it `cd`s into the workspace, so a relative plan works today. It is a
latent asymmetry: `factory-task`'s `plan=$FACTORY_PLAN` at `:75` is whatever the
caller passed, and nothing records it.

### MINOR-4 — the hint costs 94 chars, and the INFLIGHT budget is 1,000

Measured on a copy of the live runs dir with `plan:` inserted and the dead runs'
results removed: 2,837 chars under main's form, 5,402 under the new one.
`tools/session-start.sh:188` caps that part at 1,000, so roughly two
hint-carrying runs fit instead of five before `cap_part` truncates. Consider
naming the plan by basename in the hint, or budgeting the part again.

### MINOR-5 — the "plan unknown" hint is not runnable text

`relaunch: (plan unknown — set FACTORY_PLAN) factory-wave …` is what the
contract asked for, and it is honestly better than a dead launch — but pasted
after `relaunch: ` it is a bash syntax error, not a command with a blank to
fill. `relaunch: FACTORY_PLAN=<set me> factory-wave …` would be editable in
place.

### MINOR-6 — the commit body carries neither the live hint lines nor the red block

Step 4 asks for the live paste and Step 1's red block. The body has prose only.
Half-excusable: no live `run.meta` carries `plan:` yet (P11 never landed), so
there is no live hint to paste — the plan asked for something that cannot exist
until this branch runs a wave.

## Verdict

REJECTED — MAJOR-1 (the `unit` acceptance check is red; the test that pins the
absolute-plan export cannot run in the sandbox at all) and MAJOR-2 (a
`factory-integrate` run that drops a key now exits 0, a regression against both
P11 and main, pinned by nothing).

Everything else in this round is right and I would land it unchanged: the hint
is a live launch and survives a space and a quote, the plan path is absolute and
readable and refused when it is not, the grammar sentence can no longer be
mistaken for a result line, refusals are counted once and always printed, the
empty merge base is refused, and 22 of 22 mutants die.

Fix round **P11c**, same `touches`: (1) launch the driver as
`"$REAL_BASH" "$SEAT/factory-wave"` inside the `bash -c` wrapper of
`tests/unit/80-seat-driver.bats:2542` and prove `nix build
.#checks.x86_64-linux.unit` green; (2) give `factory-integrate` a skip counter
that reaches the exit code and a summary line, with a bats row asserting
`factory-integrate <run> <repo> MISSING K2` exits non-zero (mutation: the skip
dropped from `overall_rc` → fails). Fold MINORs 1-5 as the section's minor list,
and drop the live-hint demand from Step 4 until a post-P11 `run.meta` exists —
or restate it as "the fixture hint plus the live output, whatever it shows".
