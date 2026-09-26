---
plan_defect: none
mutants_total: 33
mutants_killed: 32
mutants_outside_named: 4
---
# Opus gate — seat run sd1f, task SD1b — APPROVED

## Summary

Every one of SD1's four MAJORs is closed, and closed the way the section names:
by a discriminating fixture or a discriminating assertion, each proved by the
mutant it was written to kill. The code delta over the carried commit `af19c5e`
is exactly the section's items 4 and 6 — three lines:
`tools/factory/seat/factory-lib.sh:605` (`&& [ "$cur_class" = "any" ]`),
`tools/factory/route.py:256` (`and rclass == "any"`) and
`tools/factory/seat/factory-lib.sh:615` (`local fr …`) — plus the MAP count line
and the new tests. Items 1, 2, 3 and 5 are test-only, which is correct: they pin
behaviour SD1 already had right, and their red is the mutant, not the base.

All eight named mutants A–H die, on the tests and at the assertion lines the
commit body claims, line for line. All 23 mutants the previous gate killed still
die (22 on `84-routing-ladder.bats`; #21, python's `spec >= best_spec`, still on
`80-seat-driver.bats`'s test 22 — unchanged). Nothing named survives.

`unit` (616 `ok`, the ten ladder tests at 308–317, test 315 running and not
skipped), `factory-unit` and `lint` are green under `--rebuild`; the hook, ruff,
shellcheck, the MAP diff, `tasks check`, `claims validate` and the node suite are
all clean. One commit, subject byte-identical, both trailers, body with the red,
the green and the A–H table. Touches clean, plan file untouched.

Seven MINORs: three are the previous gate's plan-text MINORs (the plan's to
carry), three are new and small, one is the section's own item 7 asking for a red
that cannot exist.

## Contract items

**Item 1 — the rung-1 filter, `ladder-reversed.toml` and test (9). Met.**
`tests/unit/84-routing-ladder.bats:120-145` writes the fixture with
`implement/code/any` **rung 2 first** (`m/a high`) and its rung 1 second
(`m/a medium`); test (9) at `:477-487` asserts `m/a medium` from both readers.
Mutants A (`factory-lib.sh:742`) and B (`route.py:261`) both die on it — see
Mutants. The fixture discriminates exactly as the section says: under A the bash
lookup returns `m/a high`, under B the python one does.

**Item 2 — the orchestrate row pinned through the parser. Met.**
`tests/unit/84-routing-ladder.bats:453-456` is the `tomllib` one-liner the
section dictates, verbatim in substance (route defaulted to `openrouter`, role
`orchestrate`, kind/size defaulted to `any`, rung defaulted to 1), asserting
status 0. The row is `docs/ledger/routing.toml:102-109`, still Pro `medium`.
Mutant C (drop the row and its comment) dies at `:456`.

**Item 3 — the unreachable-rung message in full, and the gap case's negative
arm. Met.** `tests/unit/84-routing-ladder.bats:271-276`: both halves now run
under `run --separate-stderr` and assert the full
`rung 2 without rung 1 for its key`; the gap case at `:249-256` asserts
`rung 3 without rung 2` **and** `[[ "$stderr" != *"for its key"* ]]` on both
readers. Mutants D (`factory-lib.sh:641-644`) and E (`route.py:162-164`) die at
`:273` and `:276`.

**Item 4 — `have_default` requires `class = any`, test (10). Met.**
`tools/factory/seat/factory-lib.sh:605` and `tools/factory/route.py:252-258` now
carry the class condition; the refusals are today's messages and today's exit
codes (`factory-lib.sh:733-736` → 3; `route.py:272-273` → `SchemaError` → 1).
Test (10) at `:489-508` covers `factory_route_check` → 3, `factory_route` → 3
with empty stdout, `route.py check` → 1, `route.py lookup` → 1 with the message
and no `Traceback`. Mutants F and G die at `:497` and `:506`. Measured
independently on a fixture that also carries a `claude` default row (so the
claude probe cannot mask the openrouter verdict):

```
HEAD:   factory_route_check rc=3  [factory_route: …: no default (any/any/any) row]
        route.py check      rc=1  [route.py: no default (any/any/any) row for route 'openrouter']
F+G:    factory_route_check rc=0  []
        route.py check      rc=1  TypeError: 'NoneType' object is not subscriptable (route.py:297)
```

That is the MAJOR-3 behaviour, gone.

**Item 5 — the python `--fallback` no-fallback arm. Met.**
`tests/unit/84-routing-ladder.bats:215-218`: exit 4, stdout empty, stderr
`no fallback at rung 1 for openrouter/implement/code/any/any`. Mutant H
(`route.py:296` returning `("", effort)`) dies at `:216`.

**Item 6 — `fr` local. Met.** `tools/factory/seat/factory-lib.sh:615`
(`local fr frroute frmodel found`); `nix develop -c shellcheck
tools/factory/seat/factory-lib.sh` → rc 0.

**Item 7 — the commit body. Met, with one caveat (MINOR-4).** The body pastes
the red run against the carried implementation (`1..10`, tests 1–9 `ok`, test 10
`not ok` at line 497), the green (`bats` 106 tests over the three files, the
three `nix build` lines), and the A–H table with a killing line per row. Every
killing line in that table reproduces here. The `.result` block uses the grammar
exactly: `FACTORY-RESULT status=done`, `FACTORY-CHECKS unit=pass
factory-unit=pass lint=pass`, `FACTORY-COMMITS 1`.

**SD1's carried contract.** Interfaces 1–5 are unchanged from `af19c5e` except
the two class lines; the previous gate found them met and I re-verified the
parts a change could have moved: the twenty-row table (`docs/ledger/routing.toml`
— docs rungs 2/3, XS rungs 2/3, code rung 2, the orchestrate row, each with its
`# unmeasured: <id>` comment, the header's ladder sentences at `:14-18`), the
seven claims (`docs/ledger/claims.toml:303-371`, all `status = "gap"`,
`class = "unmeasured"`, `owner = "orchestrator"`, `opened = 2026-09-06`,
`review_by = 2026-09-20`), and `route.py models` still reading rung-1 `claude`
rows (scenario 27 green in `factory-unit`).

## Red before green

**Against the base (`78d2601`, main).** Base `factory-lib.sh`, `route.py` and
`routing.toml` checked out under the branch's tests:

```
$ nix develop -c bats tests/unit/84-routing-ladder.bats
1..10
not ok 1 …climb the implement/code ladder…      line 170  `[ "$status" -eq 0 ]' failed
not ok 2 …the default lookup is unchanged…      line 195  `[ "$status" -eq 0 ]' failed
not ok 3 …--fallback…                           line 207  `[ "$status" -eq 0 ]' failed
not ok 4 …both checks accept the fixture…       line 225  `[ "$status" -eq 0 ]' failed
not ok 5 …refuse each ladder violation…         line 240  `[[ … "rung 2 twice"* ]]' failed
not ok 6 …a requested class…                    line 378  `[ "$status" -eq 0 ]' failed
not ok 7 …agree across rungs…                   line 401  `[ "$bs" -eq "$ps" ]' failed
not ok 8 …the committed table…                  line 439  `[ "$status" -eq 0 ]' failed
not ok 9 …the rung-1 filter…                    line 481  `[ "$status" -eq 0 ]' failed
not ok 10 …a class-carrying default row…        line 494  `[[ … "no default (any/any/any) row"* ]]' failed
```

10/10 red; restored to HEAD, 10/10 `ok`.

**Against the carried implementation (`af19c5e`'s two implementation files,
HEAD's tests)** — the red this section actually asks for:

```
1..10
ok 1 … ok 9 the rung-1 filter holds when the rung-2 row is written first (reversed fixture)
not ok 10 a class-carrying default row is refused: no default (any/any/any) row
# (in test file tests/unit/84-routing-ladder.bats, line 497)
#   `[ "$status" -eq 3 ]' failed
```

Byte-for-byte the block the commit body pastes, failing line included. Tests (9),
(5)'s amended assertions and (3)'s python half are green against the carried
implementation because SD1 already implemented all three correctly — they are
mutation detectors, and their red is mutant A/B/D/E/H, all of which I reproduced
(see Mutants). See MINOR-4 on the section's wording.

## Mutants

33 applied one at a time in the clone, each reverted before the next; the killing
run is `nix develop -c bats tests/unit/84-routing-ladder.bats` unless noted. 32
killed, 1 survived (`OM2`, outside the named set — MINOR-2). Outside-named: 4
(`13` and `28`, the bad-rung split the previous gate already counted as its own
two; `OM1`/`OM2`, mine).

### The section's eight

| # | mutant | file | died? | killing line |
| - | - | - | - | - |
| A | delete `[ "$wrung" = "1" ] \|\| continue` | factory-lib.sh:742 | yes | t9 `:482` `[ "$output" = "m/a medium" ]` |
| B | delete `and rrung == "1"` | route.py:261 | yes | t9 `:486` `[ "$output" = "m/a medium" ]` |
| C | drop the `orchestrate/any/any` row + comment | routing.toml:102-109 | yes | t8 `:456` `[ "$status" -eq 0 ]` (the tomllib probe) |
| D | delete the unreachable rule | factory-lib.sh:641-644 | yes | t5 `:273` `[[ "$stderr" == *"rung 2 without rung 1 for its key"* ]]` |
| E | delete the unreachable rule | route.py:162-164 | yes | t5 `:276` same substring |
| F | `have_default` from role/kind/size alone | factory-lib.sh:605 | yes | t10 `:497` `[ "$status" -eq 3 ]` |
| G | `have_default` from role/kind/size alone | route.py:256 | yes | t10 `:506` `[[ "$stderr" == *"no default (any/any/any) row"* ]]` |
| H | no-fallback returns `("", effort)` | route.py:296 | yes | t3 `:216` `[ "$status" -eq 4 ]` |

### SD1's 23, re-run

| # | mutant | file | died? | killing line |
| - | - | - | - | - |
| 1 | `--rung` arm assigns `rung=1` | factory-lib.sh | yes | t1 `:171` |
| 2 | exhaustion falls back to the rung-1 row | factory-lib.sh | yes | t1 `:178` |
| 4 | `--fallback` prints `out_model` | factory-lib.sh | yes | t3 `:208` |
| 5 | no-fallback sets `out_fb=""` | factory-lib.sh | yes | t3 `:211` |
| 6 | `class` not counted in `spec_i` | factory-lib.sh | yes | t6 `:379` |
| 7 | delete the duplicate-rung rule | factory-lib.sh | yes | t5 `:240` |
| 8 | delete the gap rule | factory-lib.sh | yes | t5 `:251` |
| 10 | two-variable condition → `false` | factory-lib.sh | yes | t5 `:315` |
| 11 | delete the fallback-has-a-row rule | factory-lib.sh | yes | t5 `:326` |
| 12 | class enum arm accepts anything | factory-lib.sh | yes | t5 `:346` |
| 13 | bad-rung pattern never matches *(outside named)* | factory-lib.sh | yes | t5 `:358` |
| 14 | `lookup` ignores `--rung` | route.py | yes | t1 `:184` |
| 15 | exhaustion assigns `target = best_row` | route.py | yes | t1 `:187` |
| 16 | `LadderError` → `return 3` | route.py | yes | t1 `:187`, t3 `:216` |
| 18 | `--fallback` returns `target["model"]` | route.py | yes | t7 `:419` |
| 20 | `class` not in `spec` | route.py | yes | t7 `:413` |
| 21 | `spec > best_spec` → `>=` | route.py | yes | **not by 84** — `80-seat-driver.bats:947`, test 22 |
| 22 | delete the duplicate-rung rule | route.py | yes | t5 `:243` |
| 23 | delete the gap rule | route.py | yes | t5 `:254` |
| 25 | two-variable condition → `False` | route.py | yes | t5 `:318` |
| 26 | delete the fallback-has-a-row rule | route.py | yes | t5 `:329` |
| 27 | delete the class enum check | route.py | yes | t5 `:349` |
| 28 | delete `_valid_rung` *(outside named)* | route.py | yes | t5 `:361` |

### Two of mine, outside the named set

| # | mutant | file | died? | on |
| - | - | - | - | - |
| OM1 | bash `--class` arm sets `cls=any` | factory-lib.sh:501-504 | yes | t6 `:379`, t7 `:413` |
| OM2 | delete `and (rclass == cls or rclass == "any")` | route.py:265 | **no** | survives 84, 80, 82 and `render.test.mjs` |

## Checks

| check | command | result |
| - | - | - |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass, 616 `ok`; ladder tests 308–317, test 315 (`the committed table …`) runs, not skipped |
| factory-unit | `… .factory-unit … --rebuild` | pass (`render.test.mjs` + `plan.test.mjs`, scenario 27 green) |
| lint | `… .lint … --rebuild` | pass |
| lint gate | `nix develop -c githooks/pre-commit` | rc 1 on pass 1 with `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; `git add docs/OPERATIONS.md`, pass 2 → rc 0. Derived from the live `~/factory/runs` state, not from the branch; the one regeneration is allowed by Global Constraints and the board is **not** in the commit. |
| ruff | `ruff check tools/factory/route.py` / `ruff format --check` | `All checks passed!` / `1 file already formatted` |
| shellcheck | `nix develop -c shellcheck tools/factory/seat/factory-lib.sh` | rc 0 |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc 0 (already regenerated in the commit: `tests/unit — 21 files` → `22`) |
| graph | `python3 pkgs/evidence/tasks.py --root . check` | silent, rc 0 |
| claims | `python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-08` | silent, rc 0 |
| node | `node --test tests/factory/render.test.mjs` | rc 0, 0 skipped |
| counts | `nix develop -c bats --count 84 80 82` | 106 = 10 + 81 + 15 — the two existing files unchanged |

No check is red.

## Touches and commit

Diff `78d2601..7024f29`, six files, +1027 −53:
`tools/factory/seat/factory-lib.sh`, `tools/factory/route.py`,
`docs/ledger/routing.toml`, `docs/ledger/claims.toml`,
`tests/unit/84-routing-ladder.bats` — all five inside the section's `touches` —
plus `docs/MAP.md` (the one-line `tests/unit` count), mandatory for the lint
gate's MAP diff and exempt by rule. Nothing outside; `docs/OPERATIONS.md` is not
in the commit; `docs/superpowers/plans/2026-09-06-seat-driver.md` is untouched.

Exactly one commit, `7024f29`. Subject byte-identical to the section's
(317 bytes, compared programmatically: `IDENTICAL: True`). Body: the why, the
red block, the green block, the A–H table; then a blank line and the two
trailers in the WORKSPACE RULES order (`Generated-By:` then
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`).

The driver's record (`~/factory/runs/sd1f/SD1b.result`) is confirmed:
`checks_verified: unit=pass factory-unit=pass lint=pass`,
`checks_verified_src: unit=run factory-unit=run lint=run`, `touches_extra: 0`,
`touches_disclosed: 0`, `exit_code: 0`, `error_class: none`, one commit
`7024f29`, `head:`/`base:` matching this branch.

## Findings

**MINOR-1 — two of test (10)'s four assertion pairs are satisfied by the
fixture's missing `claude` route, not by the class rule.**
`tests/unit/84-routing-ladder.bats:149-158` — `ladder-classdefault.toml` holds a
single `openrouter` row and no `claude` row, so `factory_route_check`'s second
probe and `route.py check`'s second `resolve` refuse it for a reason unrelated to
the class. Proof: mutant F's first failing line is `:497`, not `:493` — under F
the assertions at `:492-494` still pass. The discriminating assertions are `:496-498`
(bash) and `:503-507` (python), both present, so both F and G die; the pair at
`:492-494` and `:500-501` simply carries no weight. Adding a `claude` default row
to the fixture would make all four discriminate — I measured that it does (see
Contract items, item 4).

**MINOR-2 — the python half of "a requested class of `any` matches only `any`
rows" is untested.** `tools/factory/route.py:265`
(`and (rclass == cls or rclass == "any")`). Deleting it leaves
`84-routing-ladder.bats`, `80-seat-driver.bats`, `82-factory-dispatch.bats` and
`render.test.mjs` all `rc=0` (mutant OM2). The mutant is not equivalent — the two
readers then disagree on the section's own class fixture:

```
unmutated: bash default (cls=any): m/a medium   py default (cls=any): m/a medium
with OM2 : bash default (cls=any): m/a medium   py default (cls=any): m/c xhigh
```

Test (6) at `:381-387` runs the "`any` never matches a class row" case through
bash only, and test (7)'s class tuple at `:409-413` uses `--class bash-driver`,
where both readers agree with or without the rule. One line in test (7)'s loop
(`lookup openrouter implement code S` on `class.toml`) closes it. The code is
correct; the pin is missing. Not named by this section.

**MINOR-3 — `route.py lookup`'s new usage arms have no test.** Interface 3 says
"usage stays exit 2"; the option walk at `tools/factory/route.py:372-392` adds
three new exit-2 paths (an unknown option, `--rung` with no value, `--class` with
no value). Measured on the committed table:

```
[lookup openrouter implement code S --bogus] rc=2  usage: route.py [--file PATH] models
[lookup openrouter implement code S --rung ] rc=2  usage: route.py [--file PATH] models
[lookup openrouter implement code S --class] rc=2  usage: route.py [--file PATH] models
```

Correct, and pinned by nothing in `tests/unit/84-routing-ladder.bats` or
`80-seat-driver.bats`.

**MINOR-4 — the section's item 7 asks for a red that cannot exist for three of
its four items.** `docs/superpowers/plans/2026-09-06-seat-driver.md:368` ("the red
of (9), (10), the amended (5) assertions and (3)'s python half against the carried
implementation"). Items 1, 2, 3 and 5 add tests for behaviour SD1 already
implemented correctly — the section says so itself ("Both readers already evaluate
the missing-rung-1 rule before the gap rule … the only gap is the assertion",
`:363`). Against `af19c5e`'s implementation only test (10) can fail, and that is
exactly what I measured and what the body pastes. The seat pasted the honest run
rather than a fabricated red; the wording is the plan's defect, not the seat's.
The red that does exist for those tests is mutants A, B, C, D, E and H, all
reproduced above.

**MINOR-5 — (carried, the plan's) the section's stated first red line is a wrong
fact.** `docs/superpowers/plans/2026-09-06-seat-driver.md:115` — measured again on
the base: `factory_route: no routing table: code` (rc 3), not `row 3: unknown key
rung`. Raised as MINOR-1 by the previous gate; it is plan text, so it stays.

**MINOR-6 — (carried, the plan's) the Global Constraint about `docs/MAP.md` is a
wrong fact for this plan.** `docs/superpowers/plans/2026-09-06-seat-driver.md:31`
says no task here regenerates the MAP; the new `tests/unit/84-routing-ladder.bats`
moves the `tests/unit` count and the lint gate's MAP diff is red without the
regeneration. The seat regenerated it correctly (one line). Previous gate's
MINOR-6; stays.

**MINOR-7 — (carried, the plan's) the Tests block miscounts its own rule
mutants.** `docs/superpowers/plans/2026-09-06-seat-driver.md:118` says "six named
mutants, one per rule" while test (5) enumerates seven refusal fixtures
(`unknown class` and `bad rung` are separate fixtures for one rule, and `bad rung`
is itself two: `0` and `x`). Previous gate's MINOR-7; stays. All of them die.

### The previous gate's items, one by one

| item | status |
| - | - |
| MAJOR-1 the rung-1 filter untested in both readers | **closed** — `ladder-reversed.toml` + test (9); mutants A and B die at `:482`/`:486` |
| MAJOR-2 the orchestrate row invisible to any lookup | **closed** — the `tomllib` probe at `:453-456`; mutant C dies at `:456` |
| MAJOR-3 a class-carrying default row breaks both readers | **closed** — `have_default` requires `class = any` in both; test (10); mutants F and G die at `:497`/`:506`; measured with a `claude` row present |
| MAJOR-4 the unreachable-rung message subsumed by the gap rule | **closed** — full-message assertions plus the gap case's `!= *"for its key"*`; mutants D and E die at `:273`/`:276` |
| MINOR-1 the stated red line is a wrong fact | stays (plan text) — MINOR-5 above |
| MINOR-2 the body pastes neither red nor green | **closed** — the body pastes both and the A–H table |
| MINOR-3 `FACTORY-CHECKS`/`FACTORY-COMMITS` as prose | **closed** — the `.result` carries `FACTORY-CHECKS unit=pass factory-unit=pass lint=pass` and `FACTORY-COMMITS 1` in the grammar |
| MINOR-4 python `--fallback` no-fallback untested | **closed** — `:215-218`; mutant H dies at `:216` |
| MINOR-5 `fr` not `local` | **closed** — `tools/factory/seat/factory-lib.sh:615` |
| MINOR-6 the MAP Global Constraint is a wrong fact | stays (plan text) — MINOR-6 above |
| MINOR-7 the Tests block miscounts its rule mutants | stays (plan text) — MINOR-7 above |

## Verdict

**APPROVED.** No MAJOR. Four of the previous gate's four MAJORs are closed by
discriminating tests, each proved by the mutant it targets; the eight named
mutants A–H all die on the named tests at the claimed lines; SD1's 23 kills all
still hold; every acceptance check is green under `--rebuild`; the touches, the
single commit, the byte-identical subject, the trailers and the body's red/green/
table all conform. Seven MINORs, three of them the plan's own text, none
load-bearing. The two new gaps worth carrying into SD2 (which is the task that
first writes a `class` row) are MINOR-2 — python's `any`-never-matches-a-class-row
rule is unpinned and the readers diverge under the mutant — and MINOR-1's weak
half of test (10)'s fixture.
