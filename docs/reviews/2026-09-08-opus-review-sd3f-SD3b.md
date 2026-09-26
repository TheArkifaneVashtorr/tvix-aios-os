---
plan_defect: none
mutants_total: 14
mutants_killed: 14
mutants_outside_named: 6
---
# Opus gate — seat run sd3f, task SD3b — APPROVED

## Summary

SD3b is the fix round for SD3, and it closes the thing SD3 was rejected on. The
acceptance check `unit` is **green** in a fresh clone under `--rebuild`:
`1..649`, zero `not ok`. The red the previous gate measured
(`tests/unit/87-prior-attempt.bats:390`, `[ "$status" -eq 0 ]` failing because
SD3's rung rule makes `K1b` a rung-2 key while 87's routing fixture carried a
rung-1 row only) is reproduced here by mutant **A** — removing the six-line
rung-2 row from that fixture puts the *identical* failure back:

```
1..10
not ok 6 factory-task --prior composes the block into the brief and records prior:
# (in test file tests/unit/87-prior-attempt.bats, line 390)
#   `[ "$status" -eq 0 ]' failed
```

So the MAJOR is closed by a change that was shown red first, by the very red the
gate named.

All eight mutants the section names (A–H) die, each on the exact line the commit
body claims. Six further mutants I invented outside the named set also die. All
three acceptance checks are green under `--rebuild` (`unit` 649/649,
`evidence-unit` 479 passed, `lint` rc 0); `githooks/pre-commit` is rc 0 on the
documented two-step flow; `ruff check` / `ruff format --check` clean; `repomap.py
write` leaves `docs/MAP.md` unchanged; `tasks.py --root . check` silent.

The production code is **byte-identical** to SD3's `139a40b`
(`git diff 139a40b..HEAD -- tools/factory/seat pkgs/evidence` names only
`seat-drive.sh`, which arrived from main with SD7b) — so the claim "no production
line the fourteen SD3 mutants target moved" is verified structurally, and I
re-killed two of them by hand as a spot check. Every one of the previous review's
seven MINORs is closed. Exactly one commit, subject byte-identical (316 bytes,
`diff` empty), both trailers in order, no board commit, plan untouched, touches
inside the list.

Three MINORs recorded, none owed: one is a typo in the plan's own item 5 that the
seat correctly refused to follow and disclosed.

## Contract items

Judged against `### SD3b (` of `docs/superpowers/plans/2026-09-06-seat-driver.md`
(items 1–8), on `git diff c3a3073..HEAD` in a fresh clone at `2dfabf6`.

**1. The sibling fixture (MAJOR-1) — MET.**
`tests/unit/87-prior-attempt.bats:302-309` adds exactly the row the section
dictates, one variable moved (effort medium → high, model unchanged), which is
what SD1's ladder checker requires:

```
[[route]]
role = "any"
kind = "any"
size = "any"
rung = 2
model = "m/a"
effort = "high"
```

`nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` → rc 0,
`unit-tests> 1..649`, `grep -c 'not ok'` → `0`. The adjacency assertion the
section says must stay is untouched (`87:411-415`, `grep -A2 '^route:'` →
`route:`/`class:`/`prior:`), and the added assertion for the new `rung:` line
sits at `87:416-419`:

```
  run grep -A1 '^effort:' "$root/runs/r2/K1b.result"
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "effort: high" ]
  [ "${lines[1]}" = "rung: 2" ]
```

Disclosed in the commit body as the interaction's minimal fix ("SD3b is the fix
round for the rejected SD3: close MAJOR-1 (the acceptance check `unit` red on a
landed sibling's routing fixture)…"). Mutant **A** kills it (above).

**2. `fallback:`'s position — MET.** `tests/unit/86-rung-and-escalate.bats:287-290`:

```
  run grep -A1 '^class:' "$FACTORY_RUNS/r6/K2.result"
  [ "$status" -eq 0 ]
  [ "${lines[0]}" = "class: any" ]
  [ "${lines[1]}" = "fallback: m/f" ]
```

against `tools/factory/seat/factory-task:946-949` (`class:` then the
`fallback:` block). Mutant **B** kills it at `86:290`.

**3. The `.escalate`'s lines — MET.** `86:211-213` pins
`route: implement/code/M`, `class: any` and `plan: $plan` against
`factory-task:185-187`. Mutant **C** kills it at `86:211`.

**4. The newest run wins — MET.** `tests/evidence/test_tasks.py:795-807`: two run
directories `r1` (rung 3) and `r9` (rung 2) both hold `E7.escalate`, and the
mtimes are pinned with `os.utime` so glob order cannot decide it; `:818` asserts
the brief line names `rung 2, run r9` and `:822-823` assert
`read_escalations(runs)["E7"]` is `r9`/`"2"`. Mutant **D** (`>` → `<` at
`pkgs/evidence/tasks.py:689`) kills it at `test_tasks.py:818`.

**5. The review `.escalate`'s launch line — MET in substance, and the plan's own
wording is wrong.** `86:321-322`:

```
  [[ "$output" == *"rung: 2"* ]]
  [[ "$output" == *"launch: opus-gate task/K2b ~/factory/ws/r6/K2b"* ]]
```

The section's item 5 says the test should assert "a `launch: Workflow({` line".
That contradicts SD3's own interface 3, which states the review launch line is
`launch: opus-gate task/<KEY> ~/factory/ws/<run>/<KEY>` (and it is what
`tools/factory/seat/factory-review:40` writes, and what mutant **E** — named in
the same item — targets). The seat asserted the code's real sentence and
disclosed the discrepancy in its reply ("the plan's item 5 typo says
`launch: Workflow({` — the review MINOR-4 and the code both use the `opus-gate`
sentence"). That is the right call; recorded as MINOR-1 against the plan text,
not against the branch. Mutant **E** kills the assertion at `86:322`.

**6. Item 5's derived state — MET.** `tests/evidence/test_tasks.py:528` gives
`repo_with` a `runs_dir` kwarg; `:806-811` builds the graph against the runs dir
that HOLDS the `.escalate`; the escalated key is `E7`, which *is* in the fixture
plan (`tests/evidence/fixtures/plans/typed.md:37`, `### E7 (code, S)`), and
`:825` reads that key's state: `assert e7["state"] == "ready"`. Mutant **F**
(scan_repo merging escalations into `results`) kills it with
`AssertionError: assert 'ran' == 'ready'` at `test_tasks.py:825`.

**7. Interface 2's explicit and exit-3 arms — MET.** Two new tests.
`86:410-440` (test 9): `factory-task r9 <repo> K2b --model m/x` → the fake seat
records `model=m/x` (it prints `$2` of `dsh-openrouter --model "$model"
--headless`, `factory-task:437`), and the `.result` carries `route: explicit`
and `rung: 2`. `86:442-479` (test 10): a table with an unknown key
(`bogus = "1"`) → `stderr` holds `warning: routing table unusable`, the seat sees
`model=deepseek/deepseek-v4-pro-0813`, the `.result` carries that model and
`rung: 2`, and `[ "$status" -eq 0 ]`. Mutants **G** and **H** kill them at
`86:439` and `86:472`; H also proves the arm exercised really is the `3)` case
(the mutant replaced only that arm and the test flipped).

**8. The body and the block — MET.** `git log -1` pastes the item-1 red
(`not ok 6 … line 390 [ "$status" -eq 0 ]`), a one-line red for each of items
2–7 by its mutant, the greens (`1..167` for the six-file bats list, `478 passed,
1 skipped` for pytest, the three `nix build` results, `githooks/pre-commit` exit
0) and the A–H mutant table with the killing line for each. The seat's reply ends
in the grammar exactly — verified in `/home/dalhaka/factory/runs/sd3f/SD3b.log`
and `SD3b.result`:

```
FACTORY-RESULT status=done
FACTORY-CHECKS unit=pass evidence-unit=pass lint=pass
FACTORY-COMMITS 1
FACTORY-NOTES SD3b: rung-2 fixture row + 8 pinned mutants (A-H) and 2 new interface-2 arms; no production change, all three checks green
```

`error_class: none`, `touches_extra: 0`, `checks_verified_src: unit=run
evidence-unit=run lint=run`.

### The previous review's items, one by one

| prior finding | closed | evidence |
|---|---|---|
| MAJOR-1 `unit` red on `87:390` | yes | the rung-2 row at `87:302-309`; `unit` 649/649 rc 0; mutant A puts the exact red back |
| MINOR-1 `fallback:` position untested | yes | `86:287-290`; mutant B dies at `86:290` |
| MINOR-2 `.escalate`'s `route:`/`class:`/`plan:` untested | yes | `86:211-213`; mutant C dies at `86:211` |
| MINOR-3 newest-run rule untested | yes | two run dirs + pinned mtimes, `test_tasks.py:795-823`; mutant D dies at `:818` |
| MINOR-4 review `.escalate`'s `launch:` (and `rung:`) untested | yes | `86:321-322`; mutant E dies at `86:322`, my O3 (drop `rung:`) dies at `86:321` |
| MINOR-5 derived state on the wrong key / wrong runs dir | yes | `E7` is in the fixture plan and the graph is scanned against the escalation's runs dir; mutant F dies at `:825` |
| MINOR-6 explicit and exit-3 arms untested | yes (bar one tail) | tests 9 and 10; mutants G, H die. The tail — the `<TASKS>` success path — is still unexercised: MINOR-2 below |
| MINOR-7 body pastes neither red nor green | yes | `git log -1` pastes both, plus the mutant table |

## Red before green

**(a) The section's own red — item 1.** Mutant A (the rung-2 row removed) on the
branch tree:

```
1..10
not ok 6 factory-task --prior composes the block into the brief and records prior:
# (in test file tests/unit/87-prior-attempt.bats, line 390)
#   `[ "$status" -eq 0 ]' failed
```

Reverted → `87` is 10/10 inside the 167-test six-file run and inside `unit`'s 649.

**(b) Every test of `86` against the base implementation.** In a scratch copy,
`git checkout c3a3073 -- tools/factory/seat/{factory-lib.sh,factory-task,factory-review,factory-wave} pkgs/evidence/tasks.py`
with the branch's tests kept, `nix develop -c bats tests/unit/86-rung-and-escalate.bats`:

```
1..10
not ok 1 factory_rung_of_key classifies the chain suffix: root 1, fix 2, replan 3
#   `got=$("$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_rung_of_key '$key'")' failed with status 127
not ok 2 factory-task climbs the rung from the key and records rung: after effort:
#   `[[ "$output" == *"rung: 1"* ]]' failed
not ok 3 factory-task escalates a rung-3 key: .escalate, exit 4, no run artifacts
#   `[ "$status" -eq 4 ]' failed
not ok 4 factory-task --rung overrides the key (explicit) and rejects a bad value
#   `[ "$status" -eq 0 ]' failed
not ok 5 factory-task --fallback chooses the sideways model and records fallback:
#   `[ "$status" -eq 0 ]' failed
not ok 6 factory-review escalates a rung-2 review: .escalate, exit 4, no gate marker
#   `[ "$status" -eq 4 ]' failed
not ok 7 factory-wave prints an escalated key and records driver: when SEAT_JOB_ID is set
#   `[[ "$output" == *"K2r status=escalated checks=- commits=- minutes=- tokens=- escalate=claude/implement"* ]]' failed
not ok 8 factory-task spools (--no-start --wait) inside a seat unit, not on the host
#   `[[ "$output" == *"--no-start --wait"* ]]' failed
not ok 9 factory-task --model keeps route: explicit and still records rung:
#   `[[ "$output" == *"rung: 2"* ]]' failed
not ok 10 factory-task exit-3 arm: an unroutable table warns, uses the built-in default, rung:
#   `[[ "$output" == *"rung: 2"* ]]' failed
```

Ten of ten red, including SD3b's two new tests (9 and 10). The pytest, same
scratch:

```
>       assert "**Escalated:** E7 (claude/implement, rung 2, run r9)" in md
E       AssertionError
tests/evidence/test_tasks.py:818: AssertionError
1 failed, 145 deselected in 0.21s
```

Restored → `1..167` over the six-file list, zero `not ok`; `evidence-unit` 479
passed. No test in this section is vacuous.

## Mutants

Each applied in a scratch copy of the fresh clone, run, reverted. Named A–H,
plus six of my own.

| # | mutant | file | died? | on (killing line) |
|---|---|---|---|---|
| A | the rung-2 row removed from 87's fixture | tests/unit/87-prior-attempt.bats:302-309 | yes | `87:390` `[ "$status" -eq 0 ]` (exit 4) |
| B | `fallback:` printed before `class:` | tools/factory/seat/factory-task:946-949 | yes | `86:290` `[ "${lines[1]}" = "fallback: m/f" ]` |
| C | the `.escalate` drops `route:`/`class:`/`plan:` | tools/factory/seat/factory-task:185-187 | yes | `86:211` `[[ "$output" == *"route: implement/code/M"* ]]` |
| D | `read_escalations` keeps the oldest run (`>` → `<`) | pkgs/evidence/tasks.py:689 | yes | `test_tasks.py:818` (`rung 2, run r9` absent) |
| E | the review launch sentence becomes the literal `MUTANT` | tools/factory/seat/factory-review:40 | yes | `86:322` `launch: opus-gate task/K2b ~/factory/ws/r6/K2b` |
| F | an `.escalate` counted as a result (scan_repo merge) | pkgs/evidence/tasks.py:894 | yes | `test_tasks.py:825` `AssertionError: assert 'ran' == 'ready'` |
| G | the explicit arm drops `rung:` (`rung_label=`) | tools/factory/seat/factory-task:259 | yes | `86:439` `[[ "$output" == *"rung: 2"* ]]` |
| H | the exit-3 arm escalates instead of warning | tools/factory/seat/factory-task:266-270 | yes | `86:472` `[ "$status" -eq 0 ]` |
| O1 | `rung:` printed after `route:` instead of after `effort:` | factory-task:946-947 | yes | `86:173` (the `effort: medium`/`rung: 1` adjacency) **and** `87:413` |
| O2 | `read_escalations` hard-codes the rung field | tasks.py:686 | yes | `test_tasks.py:818` |
| O3 | the review `.escalate` drops its `rung:` line | factory-review:44 | yes | `86:321` `[[ "$output" == *"rung: 2"* ]]` |
| O4 | 87's new rung-2 row given a different model/effort | 87-prior-attempt.bats:307-308 | yes | `87:420` `[ "${lines[0]}" = "effort: high" ]` |
| S11 | (SD3's #11) `driver:` written when `SEAT_JOB_ID` is unset | factory-wave:157-159 | yes | `86:365` `[[ "$output" != *"driver:"* ]]` |
| S3 | (SD3's #3) the escalation writes a `.result` too | factory-task:191 | yes | `86:215` `[ ! -e "$FACTORY_RUNS/r3/K2r.result" ]` |

mutants_total 14 · mutants_killed 14 · mutants_outside_named 6 (O1–O4, S11, S3).

O1 is worth naming: it kills on *both* files, which is the proof that 87's added
adjacency assertion is load-bearing and not decoration. S11 and S3 are two of
SD3's fourteen, re-killed by hand; the rest are covered structurally — the
production files are byte-identical to `139a40b` (`git diff 139a40b..HEAD --stat
-- tools/factory/seat pkgs/evidence` lists only `seat-drive.sh`, which came from
main with SD7b), and every test that killed them is still present and green.

## Checks

Every command from inside the fresh clone
`…/scratchpad/scratch/SD3b/gate-sd3f-SD3b`, tools through `nix develop -c`.

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass** — rc 0, `unit-tests> 1..649`, `grep -c 'not ok'` → `0` |
| evidence-unit | `… evidence-unit -L --no-link --rebuild` | **pass** — `479 passed in 13.25s` |
| lint | `… lint -L --no-link --rebuild` | **pass** — rc 0 |
| lint gate | `nix develop -c githooks/pre-commit` | **pass** on the documented flow: first run rc 1 with `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`; after `git add docs/OPERATIONS.md`, rc 0. The staleness is this gate clone's own doing (it already holds SD3b's commit, so the derived queue drops `SD3b` and adds `SD9`); the whole diff is one line inside `<!-- tasks:begin -->…<!-- tasks:end -->`. Exempt; not a finding. |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| shellcheck | `nix develop -c shellcheck` on the four driver scripts | rc 0 |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | clean (rc 0) |
| graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent (rc 0) |
| section Step 3 bats | `bats 86 87 84 85 80 92` | `1..167`, 167 `ok`, zero `not ok` |

The `unit` green is the point of this round, so the whole of it:

```
RC=0
0          # grep -c 'not ok'
unit-tests> 1..649
```

## Touches and commit

**Touches — clean.** The section's list is `factory-lib.sh, factory-task,
factory-review, factory-wave, pkgs/evidence/tasks.py, tests/evidence/test_tasks.py,
tests/unit/86-rung-and-escalate.bats, tests/unit/87-prior-attempt.bats`.
`git diff c3a3073..HEAD --stat` names exactly those eight plus `docs/MAP.md`
(`tests/unit` 25 → 26, generated and exempt by rule, and the lint gate's MAP diff
requires it). Nothing outside; `docs/OPERATIONS.md` is not in the diff at all.

**Commit — clean.** Exactly one commit, `2dfabf67fe00a13c7f99f29e6e775e14e6487967`
(`git rev-list --count c3a3073..HEAD` → `1`). Subject byte-identical to the
section's `**commit subject:**`: both 316 bytes, compared programmatically
against the plan's own line → `IDENTICAL`. The body states the why, pastes the
red of item 1, a red per mutant for items 2–7, the greens, and the A–H table.
The two trailers follow a blank line in the WORKSPACE RULES order:

```
''
'Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sd3f)'
'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'
```

No second commit, no board commit, the plan file untouched.

## Interfaces and error contracts

SD3's interfaces stand unchanged (the production code is byte-identical to
`139a40b`, and the previous gate found every one of them MET). SD3b's job was the
arms and clauses that had no discriminating assertion; after this round every
producer and every enum arm of interface 2 is exercised:

- rung from the key / `--rung` explicit / `--rung x` refused → tests 2, 4
  (mutants covered by SD3's #2, #6).
- lookup exit 0 (with and without `--fallback`) → tests 2, 5 (mutants B, SD3 #7).
- lookup exit 3 → test 10 (mutant H) — **new this round**.
- lookup exit 4 → test 3 (mutants C, S3), and under `--fallback` → `die 2` with
  nothing written, test 5.
- explicit `--model`/`OPENROUTER_MODEL` → test 9 (mutant G) — **new this round**.
- interface 3's review escalation, all its lines → test 6 (mutants E, O3).
- interface 4's summary line and `driver:` pair → test 7 (mutant S11).
- interface 5's `read_escalations` newest-run rule and the "not a run" state →
  `test_brief_lists_escalations` (mutants D, F, O2).
- interface 6's spool flags, both rows → test 8.

One stated behaviour of interface 2 is still unexercised and is recorded as
MINOR-2: the `<TASKS>` array's *success* path.

`graph["runs_dir"]` — the key `render_brief` reads at `tasks.py:1905` — is really
set by the production graph builder (`tasks.py:1044`, `tasks.py:2121`), so the
brief's `**Escalated:**` line is not a test-only path.

## Findings

**MINOR-1 — the plan's item 5 contradicts SD3's interface 3, and the seat was
right not to follow it.** `docs/superpowers/plans/2026-09-06-seat-driver.md`
(SD3b item 5) says test 6 must assert that `K2b.escalate` "holds a
`launch: Workflow({` line". SD3's interface 3 states the review launch line is
`launch: opus-gate task/<KEY> ~/factory/ws/<run>/<KEY>`, which is what
`tools/factory/seat/factory-review:40` writes:

```
  launch="opus-gate task/$key ~/factory/ws/$run/$key"
```

and what the same item's own mutant **E** (`factory-review:40` → the literal
`MUTANT`) targets. Asserting `Workflow({` there would have been an assertion that
can only fail. `tests/unit/86-rung-and-escalate.bats:322` asserts the real
sentence; the seat disclosed the conflict in its reply. No code owed; the plan's
sentence should be corrected if that section is ever re-used.

**MINOR-2 — the `<TASKS>` success path of the implement escalation is still never
exercised, and the placeholder is never asserted.**
`tools/factory/seat/factory-task:157-160`:

```
  tasks_json=$(factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/tasks.py" \
    --root "$repo_path" waves --repo "$repo_name" --plan "$plan_base" --factory-args 2>/dev/null) \
    || tasks_json='[ /* tasks.py waves --factory-args failed: run it by hand */ ]'
```

Every escalation in the suite runs with a `FACTORY_TOOLBOX_REPO` fixture that
holds only `docs/ledger/routing.toml`, so the query always fails and the literal
placeholder always wins; test 3 asserts only the `launch: Workflow({` prefix
(`86:214`), never the array. Carried from the previous review's MINOR-6 tail;
SD3b's item 7 named only the explicit and exit-3 arms, so nothing was owed here.
A future round wants a fixture toolbox with a real `tasks.py` and an assertion on
the emitted `tasks:` array.

**MINOR-3 — a stale comment in test 5.**
`tests/unit/86-rung-and-escalate.bats:292-293` reads "Without a fallback row
(`--rung 2` on K2b has no fallback), `--fallback` dies 2", but the command two
lines below passes no `--rung` — `K2b` is rung 2 by its key, which is the better
thing to be testing. Comment only; the test is correct and mutant-killing.

## Verdict

**APPROVED.** The MAJOR that rejected SD3 is closed by a change shown red first —
mutant A reproduces the previous gate's exact `87:390` failure — and the
acceptance check it was red on is now green in a fresh clone under `--rebuild`
(`1..649`, zero `not ok`). All eight named mutants die on the lines the body
claims; six of mine die too; the production code is byte-identical to SD3's, so
its fourteen kills stand, and two re-killed by hand confirm it. All three
acceptance checks, the lint gate, ruff, shellcheck, the MAP regeneration and the
task-graph check are green. One commit, subject byte-identical, both trailers,
touches inside the list, the reply ending in the grammar. Three MINORs, none
gating: one is a defect in the plan's own prose that the seat caught and
disclosed.
