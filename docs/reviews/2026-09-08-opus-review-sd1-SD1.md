---
plan_defect: wrong-fact
plan_defect_secondary: missing-case
mutants_total: 29
mutants_killed: 23
mutants_outside_named: 2
---
# Opus gate — seat run sd1, task SD1 — REJECTED

## Summary

The feature is built and the acceptance checks are green: three optional row keys, the
ladder key, both readers' ladder rules, `--rung/--class/--fallback`, exit 4 on
exhaustion, the first rungs and all seven claims. Every one of the eight tests fails on
the base implementation, so the red is real. `unit` (602 ok), `factory-unit`, `lint`
(all `--rebuild`), the hook, ruff, shellcheck, the MAP diff, `tasks check` and
`claims validate` are all green, and the counts of `80-seat-driver.bats` (81) and
`82-factory-dispatch.bats` (15) are unchanged.

It is rejected on the mutation table. Three mutants the section names by hand survive
the whole unit suite, and a fourth divergence between the two readers is reachable from
data alone:

- the rung-1 filter in the winner scan (the section's mutant (2)) survives in **both**
  readers — the fixture's rung-1 row precedes its rung-2 row, and the tie rule is
  "earliest wins", so counting rung-2 rows in the default lookup changes nothing the
  suite sees. I proved the mutant is not equivalent with a re-ordered table.
- dropping the `orchestrate/any/any` row from the committed table (mutant (8)) changes
  nothing: the openrouter default row is the *same model and the same effort*
  (`deepseek/deepseek-v4-pro-0813 medium`), so the section's "fails only if the test
  asserts the row's effort, which it does" is false. The required first row is unpinned.
- deleting the unreachable-rung rule (one of the six rule mutants) survives in both
  readers: the gap rule subsumes it and prints a message the assertion's substring still
  matches.
- a `[[route]]` row that is the route's `any/any/any` default **and** carries a `class`
  makes `factory_route` exit 0 printing an empty `MODEL EFFORT` pair (a caller reads an
  empty model) while `route.py` dies with an uncaught `TypeError` traceback —
  `factory_route_check` accepts that table.

Most of this traces to the plan: the section's Tests block names four discriminators
that cannot discriminate under the section's own fixture and tie rule, and the lookup's
`have_default` rule was never extended to the class it added to the key. The seat
implemented what it was told and did not re-derive the mutants.

## Contract items

Interface 1 — row keys. `class` (the ten words plus `any`), `rung` (positive integer,
default 1), `fallback` (`[A-Za-z0-9._:/-]+`); any other key still `unknown key`.
**Met.** `tools/factory/seat/factory-lib.sh:590-604` (the `class` and `rung` case arms),
`:711-718` (the key walk, unknown key at `:719`); `tools/factory/route.py:52-64`
(`CLASSES`), `:244-247` (`unknown class` / `bad rung`). Exercised by test 5.

Interface 2 — the ladder key and the six refusals. **Met in code, one refusal not
distinguished by a test.** `factory-lib.sh:612-704` (`_factory_route_check_ladders`) and
`route.py:132-186` (`check_ladders`); every message shape matches the section:
`ladder openrouter/implement/code/any/any: rung 2 twice`, `rung 3 without rung 2`,
`rung 2 without rung 1 for its key`, `rungs 1→2 change model and effort`,
`fallback m/zzz has no row of its own`, `unknown class`, `bad rung`. Cross-route steps
are not compared (the key carries the route). The unreachable rule's own message is not
pinned — see MAJOR-4.

Interface 3 — lookup. **Met, with one hole.** Option parsing
`factory-lib.sh:489-511`; the rung-1 winner with class in the specificity count
`:738-757`; the climb and exit 4 `:759-779`; `--fallback` and its exit 4 `:781-788`.
`route.py:189-292` mirrors it; `lookup`'s three options `:358-382`; `LadderError` → exit
4 `:384-386`. `route.py models` still reads rung-1 `claude` rows only (`resolve`'s
`and rrung == "1"`, `route.py:255`) — `factory-unit`'s scenario 27 is green. Measured:
`factory_route --rung 2 review code S docs/ledger/routing.toml` → rc 4,
`factory_route: ladder exhausted at rung 2 for openrouter/review/any/any/any`;
`route.py … lookup openrouter implement code S --fallback` → rc 4,
`route.py: no fallback at rung 1 for openrouter/implement/code/any/any`. The hole:
"Output stays MODEL EFFORT … every table fault stays exit 3 (bash) / exit 1 (python)
with today's messages" is violated for a class-carrying default row (MAJOR-3).

Interface 4 — the first rows. **Met.** `docs/ledger/routing.toml:14-18` (the header's two
sentences), `:28-46` (docs rungs 2 and 3), `:56-74` (XS rungs 2 and 3), `:84-92`
(code rung 2, Pro high), `:102-109` (the openrouter `orchestrate/any/any` row, Pro
`medium` — the default answer to question 1). Each new row carries
`# unmeasured: <claim id>`. No `class` row, no `fallback` value; the five existing
openrouter rows and all nine `claude` rows are untouched (20 rows total, was 14).

Interface 5 — the claims. **Met.** `docs/ledger/claims.toml:303-371`: all seven ids
present with `status = "gap"`, `class = "unmeasured"`, `owner = "orchestrator"`,
`opened = 2026-09-06`, `review_by = 2026-09-20` and the section's `closes_by` texts.
`claims.py validate … --today 2026-09-08` is silent.

Step 1 — the test file. **Met in shape**: setup as `80-seat-driver.bats`, every driver
call through `"$REAL_BASH"`, one `[ … ]` per line, fixtures under `BATS_FILE_TMPDIR`/
`BATS_TEST_TMPDIR`, the eight tests in the section's order, `bats --count` = 8.

## Red before green

Base implementation (`git checkout 55753ba -- tools/factory/seat/factory-lib.sh
tools/factory/route.py docs/ledger/routing.toml`), branch tests:

```
$ nix develop -c bats tests/unit/84-routing-ladder.bats
1..8
not ok 1 factory_route and route.py climb the implement/code ladder and exit 4 at exhaustion
#   `[ "$status" -eq 0 ]' failed                        (line 127)
not ok 2 the default lookup is unchanged: rung 1 wins by specificity, not by rung   (line 152)
not ok 3 --fallback prints the winning row's fallback and effort, exit 4 without one (line 164)
not ok 4 factory_route_check and route.py check accept the ladder fixture            (line 177)
not ok 5 both implementations refuse each ladder violation (one edit per fixture)
#   `[[ "$output" == *"ladder openrouter/implement/code/any/any: rung 2 twice"* ]]' failed
not ok 6 a requested class matches its own row, and any never matches a class row    (line 328)
not ok 7 factory_route and route.py agree across rungs, class, fallback and claude   (line 351)
not ok 8 the committed table carries the first rungs and both checks accept it       (line 389)
```

8/8 red for the missing feature; restored to HEAD, 8/8 `ok` in 2.9 s. The section's
stated first red line is wrong (MINOR-1): on the base, `factory_route` parses
positionally, so `--rung 2 implement code S ladder.toml` reads `code` as the FILE:

```
$ factory_route --rung 2 implement code S <table>     # base factory-lib.sh
factory_route: no routing table: code
status=3
```

not `row 3: unknown key rung`. The failing assertion is nonetheless the one the section
names (`[ "$status" -eq 0 ]`, line 127).

## Mutants

29 applied in the clone, one at a time, reverted after each; the killing run is
`bats tests/unit/84-routing-ladder.bats` unless noted. 23 killed, 6 survived,
2 outside the section's named set (`BR7`/`PR7`: the section counts `rung`/`class`
out-of-set as one rule, I split it into two deletions).

| # | mutant | file | died? | on |
| - | - | - | - | - |
| 1 | `--rung` arm assigns `rung=1` | factory-lib.sh | yes | t1 `[ "$output" = "m/a high" ]` |
| 2 | exhaustion falls back to the rung-1 row | factory-lib.sh | yes | t1 `[ "$status" -eq 4 ]` |
| 3 | **drop `[ "$wrung" = "1" ] || continue` (:742)** | factory-lib.sh | **no** | — |
| 4 | `--fallback` prints `out_model` | factory-lib.sh | yes | t3 `[ "$output" = "m/a off" ]` |
| 5 | no-fallback arm sets `out_fb=""` instead of exit 4 | factory-lib.sh | yes | t3 `[ "$status" -eq 4 ]` |
| 6 | `class` not counted in `spec_i` (:750) | factory-lib.sh | yes | t6 `[ "$output" = "m/c xhigh" ]` |
| 7 | delete the duplicate-rung rule | factory-lib.sh | yes | t5 `rung 2 twice` |
| 8 | delete the gap rule | factory-lib.sh | yes | t5 `rung 3 without rung 2` |
| 9 | **delete the unreachable rule (:641-644)** | factory-lib.sh | **no** | — |
| 10 | two-variable condition → `false` | factory-lib.sh | yes | t5 `[ "$status" -eq 3 ]` |
| 11 | delete the fallback-has-a-row rule | factory-lib.sh | yes | t5 `[ "$status" -eq 3 ]` |
| 12 | class enum arm accepts anything | factory-lib.sh | yes | t5 `[ "$status" -eq 3 ]` |
| 13 | bad-rung pattern never matches (outside named) | factory-lib.sh | yes | t5 `bad rung` |
| 14 | `lookup` ignores `--rung` | route.py | yes | t1 `[ "$output" = "m/a high" ]` |
| 15 | exhaustion assigns `target = best_row` | route.py | yes | t1 `[ "$status" -eq 4 ]` |
| 16 | `LadderError` → `return 3` | route.py | yes | t1 `[ "$status" -eq 4 ]` |
| 17 | **drop `and rrung == "1"` (:255)** | route.py | **no** | — |
| 18 | `--fallback` returns `target["model"]` | route.py | yes | t7 `[ "$b" = "$p" ]` |
| 19 | **no-fallback returns `("", effort)`** | route.py | **no** | — |
| 20 | `class` not in `spec` (:248) | route.py | yes | t7 `[ "$b" = "$p" ]` |
| 21 | `spec > best_spec` → `>=` | route.py | yes | **not by 84** — by `80-seat-driver.bats:22` |
| 22 | delete the duplicate-rung rule | route.py | yes | t5 `rung 2 twice` |
| 23 | delete the gap rule | route.py | yes | t5 `[ "$status" -eq 1 ]` |
| 24 | **delete the unreachable rule (:162-164)** | route.py | **no** | — |
| 25 | two-variable condition → `False` | route.py | yes | t5 `[ "$status" -eq 1 ]` |
| 26 | delete the fallback-has-a-row rule | route.py | yes | t5 `[ "$status" -eq 1 ]` |
| 27 | delete the class enum check | route.py | yes | t5 `[ "$status" -eq 1 ]` |
| 28 | delete `_valid_rung` (outside named) | route.py | yes | t5 `bad rung` |
| 29 | **drop the `orchestrate/any/any` row** | routing.toml | **no** | — |

Mutants 3, 17, 19, 24 and 29 were re-run against
`bats tests/unit/{80-seat-driver,82-factory-dispatch,84-routing-ladder}.bats` and
`node --test tests/factory/render.test.mjs`: all still `rc=0` except 21, which dies on
`80-seat-driver.bats`'s pre-existing test 22 ("factory_route and route.py agree on a
discriminating tie (earliest row wins)") — so the tie rule is still pinned, just not by
test 7 as the section claims.

## Checks

| check | command | result |
| - | - | - |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass, 602 `ok`, test 315 (`the committed table …`) runs, not skipped |
| factory-unit | `… .factory-unit … --rebuild` | pass (render + plan suites, scenario 27 green) |
| lint | `… .lint … --rebuild` | pass |
| lint gate | `nix develop -c githooks/pre-commit` | rc 1 on pass 1 with `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; `git add docs/OPERATIONS.md` then pass 2 → rc 0. The staleness is derived from the live `~/factory/runs` state (the queue drops SD1 and gains SD2 SD3), not from the branch's content; Global Constraints allow the one regeneration. |
| ruff | `ruff check tools/factory/route.py` / `ruff format --check` | `All checks passed!` / `1 file already formatted` |
| shellcheck | `nix develop -c shellcheck tools/factory/seat/factory-lib.sh` | rc 0 |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc 0 (already regenerated in the commit) |
| graph | `python3 pkgs/evidence/tasks.py --root . check` | silent, rc 0 |
| claims | `python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-08` | silent, rc 0 |
| counts | `bats --count` | 80: 81, 82: 15, 84: 8 — the two existing files unchanged |
| node | `node --test tests/factory/render.test.mjs` | rc 0 |

No check is red.

## Touches and commit

Diff `55753ba..af19c5e`, six files, +931 −51: `tools/factory/seat/factory-lib.sh`,
`tools/factory/route.py`, `docs/ledger/routing.toml`, `docs/ledger/claims.toml`,
`tests/unit/84-routing-ladder.bats` — all five inside the section's `touches` — plus
`docs/MAP.md` (one line, `tests/unit — 20 files` → `21`), mandatory for the lint gate's
MAP diff and exempt by the orchestrator's rule. Nothing outside. The plan file is
untouched; `docs/OPERATIONS.md` is not in the commit.

Exactly one commit, `af19c5e`. Subject byte-identical to the section's (317 bytes,
compared programmatically: `IDENTICAL: True`). Body states the why in six lines; both
trailers follow a blank line in the WORKSPACE RULES order (`Generated-By:` then
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`). The body does **not** paste
the red and the green as Step 1 requires (MINOR-2).

## Findings

**MAJOR-1 — the rung-1 filter in the default lookup is untested in both readers; the
section's named mutant (2) survives.** `tools/factory/seat/factory-lib.sh:742`
(`[ "$wrung" = "1" ] || continue`) and `tools/factory/route.py:255`
(`and rrung == "1"`). Deleting either leaves `bats tests/unit/84-routing-ladder.bats`,
`80-seat-driver.bats`, `82-factory-dispatch.bats` and `render.test.mjs` all `rc=0`. The
cause is the section's own fixture: `ladder.toml` writes rung 1 before rung 2 for
`implement/code/any`, all rungs share the key (equal specificity), and ties go to the
earliest row — so the rung-1 row wins with or without the filter. The plan's
"→ `m/a high` wins on rung, fails" (`docs/superpowers/plans/2026-09-06-seat-driver.md:118`)
is false. The mutant is **not** equivalent — with a table whose rung-2 row is written
first:

```
# order.toml: any/any/any m/d low; implement/code/any rung 2 m/a high; implement/code/any m/a medium
unmutated: bash default: m/a medium   py default: m/a medium
mutated  : bash default: m/a high     py default: m/a high
```

A discriminating fixture (the rung-2 row placed before its rung-1 row, or a rung-2 row
of higher specificity than the rung-1 winner) is needed in test 2 and in test 7's loop.

**MAJOR-2 — the `orchestrate/any/any` row that interface 4 requires is pinned by no
test; the section's named mutant (8) survives.** `docs/ledger/routing.toml:102-109`. The
row is `deepseek/deepseek-v4-pro-0813` / `medium`, and the openrouter default row
`any/any/any` at `:110-116` is the *same model and effort*, so
`factory_route orchestrate any any <table>` (test 8, `tests/unit/84-routing-ladder.bats:399-401`)
prints `deepseek/deepseek-v4-pro-0813 medium` whether the row exists or not. Deleting
the whole row and its comment: `bats tests/unit/84-routing-ladder.bats` → `rc=0`, no
failure. The section's "fails only if the test asserts the row's effort, which it does"
(`:118`) is false. Nothing in the tree would notice if the row were dropped, yet SD3's
climb and SD9's report group by exactly this key.

**MAJOR-3 — a class-carrying default row makes the two readers disagree, and
`factory_route_check` accepts it: bash prints an empty `MODEL EFFORT` pair at exit 0,
python raises.** `tools/factory/seat/factory-lib.sh:606` sets `have_default=1` from
role/kind/size alone while the winner scan at `:738-757` also requires the class to
match, so `best` can stay `-1` with `have_default=1`; `route.py:252` has the same split
against `:256` (`rclass == cls or rclass == "any"`). Measured on a two-row table whose
openrouter `any/any/any` row carries `class = "bash-driver"`:

```
$ factory_route implement code S edge.toml         ; rc=0 out=[ ]
$ factory_route_check edge.toml                    ; rc=0 out=[]
$ route.py --file edge.toml lookup openrouter implement code S
  TypeError: 'NoneType' object is not subscriptable   (route.py:292)   rc=1
$ route.py --file edge.toml check                   ; rc=1 (same traceback)
route_line=[ ] model=[] effort=[]     # what factory-task's ${line%% *} would read
```

This violates interface 3's "Output stays `MODEL EFFORT` (one line, two fields)" and
"every table fault stays exit 3 (bash) / exit 1 (python) with today's messages", and it
breaks the section's central parity promise. It is unreachable from today's table (no
`class` row yet) but reachable the moment SD2/SD3 add one, and the guard that exists to
protect the table (`factory_route_check`) passes it. The plan never extended
`have_default` to the class it added to the key.

**MAJOR-4 — the unreachable-rung rule is subsumed by the gap rule, so its named mutant
survives in both readers.** `tools/factory/seat/factory-lib.sh:641-644` and
`tools/factory/route.py:162-164`. Deleting either leaves
`bats tests/unit/84-routing-ladder.bats` at `rc=0`: for the fixture's
`implement/code/S rung = 2` key the gap loop then prints `rung 2 without rung 1`, and the
assertion at `tests/unit/84-routing-ladder.bats:223,226` matches only the substring
`rung 2 without rung 1`, which both messages satisfy. The section's contract names the
distinct message `rung N without rung 1 for its key`
(`docs/superpowers/plans/2026-09-06-seat-driver.md:108`) and its mutant prediction is
"delete that rule → status 0" (`:118`) — false, the refusal survives via the sibling
rule. Behaviour is preserved (every unreachable ladder is also gapped, so the verdict
never changes); what is unpinned is the message the contract specifies. Assert the full
string, or use a key whose lowest rung is 3 so the two rules print different text.

**MINOR-1 — the section's stated red line is a wrong fact.**
`docs/superpowers/plans/2026-09-06-seat-driver.md:115` says test 1's red shows
`factory_route: …/ladder.toml: row 3: unknown key rung`. Measured on the base:
`factory_route: no routing table: code` (rc 3) — today's `factory_route` parses
positionally, so `--rung 2` is consumed as role/kind and `code` becomes the FILE. The
failing assertion the section names is right; the message is not. The red is genuine
(8/8 tests fail on the base for the missing feature).

**MINOR-2 — the commit body pastes neither the red nor the green.**
`git log -1 --format=%B` at `af19c5e`: six prose lines and the two trailers, no `not ok`
and no check output. Step 1 ends "Paste the block into the commit body".

**MINOR-3 — the seat's `FACTORY-CHECKS` / `FACTORY-COMMITS` lines are prose, not the
grammar.** Reported by the driver; the record of substance is the driver's own
`checks_verified: unit=pass factory-unit=pass lint=pass` (all `run`), `touches_extra 0`
and the single commit `af19c5e`, and my own runs above confirm each. Process, not code.

**MINOR-4 — `route.py lookup --fallback` on a row without a fallback is a stated
contract with no test.** `tools/factory/route.py:290` raises `LadderError` → exit 4 with
`route.py: no fallback at rung 1 for openrouter/implement/code/any/any` (I measured it),
but test 3 exercises only the bash arm and test 7's `--fallback` tuple uses the row that
*has* one, so the python mutant `return ("", target["effort"])` survives the suite. One
line in test 7's loop closes it.

**MINOR-5 — `fr` is not declared `local`.** `tools/factory/seat/factory-lib.sh:668`
(`for fr in "${rows[@]}"; do`) inside `_factory_route_check_ladders`, whose other loop
variables are all localised at `:613-617`. Sourcing `factory-lib.sh` and calling
`factory_route` leaves `fr` set in the caller's shell. shellcheck does not flag it.

**MINOR-6 — the Global Constraint about `docs/MAP.md` is a wrong fact for this plan.**
`docs/superpowers/plans/2026-09-06-seat-driver.md:31` says a task regenerates the MAP
only when it adds a package, module, host file, check or top-level entry, "none here
does". SD1 adds `tests/unit/84-routing-ladder.bats`, which moves the MAP's
`tests/unit — 20 files` count; without the regeneration the lint gate's MAP diff is red.
The seat regenerated it correctly (one line).

**MINOR-7 — the Tests block miscounts its own rule mutants.**
`docs/superpowers/plans/2026-09-06-seat-driver.md:118` says "six named mutants, one per
rule" while Step 1's test 5 enumerates seven refusal fixtures (`unknown class` and
`bad rung` are separate fixtures for the one "a `rung`/`class` value outside its set"
rule). Both were run and both die.

## Verdict

**REJECTED.** Four MAJORs, seven MINORs. The code does what the section describes and
every acceptance check is green; the mutation table is what fails. Three of the four
MAJORs are discriminators the plan named that cannot discriminate (mutants 2, 8 and the
unreachable rule — `plan_defect: wrong-fact`), and the fourth is the class the plan
added to the ladder key but not to the default-row rule (`missing-case`). The fix round
is small and additive: a re-ordered rung fixture for the default lookup, an assertion
that pins the `orchestrate` row distinctly (a differing effort, or a table-text
assertion), the full unreachable message in test 5, a `--fallback` no-fallback tuple on
the python side, and a `have_default` that respects the class (with the matching refusal
in both readers and a test for it).
