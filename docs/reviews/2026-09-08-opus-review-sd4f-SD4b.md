---
plan_defect: none
mutants_total: 25
mutants_killed: 22
mutants_outside_named: 6
---
# Opus gate — seat run sd4f, task SD4b — APPROVED

## Summary

Fresh clone of `task/SD4b` at `54b57fe`, base `e6fc498` (main). Five files, one commit, subject
byte-identical to the section's (249 bytes, `diff` of `git log -1 --format=%s` against the plan's
line 391 → identical). SD4's commit `39eb8cb` is carried by cherry-pick and corrected in place;
the diff against main is the whole feature plus SD4b's nine code/test corrections.

Both of the prior gate's MAJORs are closed, measured on the real case the gate named:

```
$ factory_prior_block /home/dalhaka/factory/runs /home/dalhaka/nixos-agent-env sd1 SD1
…
**Mutation-table survivors:**
| 3 | **drop `[ "$wrung" = "1" ] || continue` (:742)** | factory-lib.sh | **no** | — |
| 9 | **delete the unreachable rule (:641-644)** | factory-lib.sh | **no** | — |
| 17 | **drop `and rrung == "1"` (:255)** | route.py | **no** | — |
| 19 | **no-fallback returns `("", effort)`** | route.py | **no** | — |
| 24 | **delete the unreachable rule (:162-164)** | route.py | **no** | — |
| 29 | **drop the `orchestrate/any/any` row** | routing.toml | **no** | — |

$ wc -c -l block          #  3499 bytes, 44 lines  (≤ 8,000)
```

All six `| **no** |` rows of `docs/reviews/2026-09-08-opus-review-sd1-SD1.md` are listed where the
prior round printed `(none)`, and the block is 3,499 bytes. The byte cap is now a byte cap: an
end-to-end block of sixty 190-em-dash findings under the devShell's `LANG=en_US.UTF-8` comes out
at **7,981 bytes** (26 lines, cut marked `… (49 more lines)`) where the carried code emitted
21,641.

Ten items, all met. Nineteen named mutants (SD4b's A–J, SD4's nine) all die. Red is real and is
the section's red — against the *carried* implementation tests 1, 8, 9 and 10 fail, exactly the
four the commit body pastes. `unit` (616 `ok`, 0 `not ok`) and `lint` are green under
`--rebuild`; shellcheck, `repomap write`, `tasks check` and the bats counts (10 + 81 = 91) all
clean. Six MINORs, none gating: three are unpinned SD4 clauses I found by mutants outside the
named set, one is the plan's own impossible red list in item 10, two are carried from the prior
round (the plan-text ones and the queue-block regeneration).

## Contract items

Item numbers are the SD4b section's.

| # | item | verdict | evidence |
|---|---|---|---|
| 1 | survivors through emphasis; the `surviv` arm stays; fixture row `\| 7 \| … \| **no** \| — \|`; new test (8) | met | `tools/factory/seat/factory-lib.sh:1074-1085` — `cell=$(printf '%s\n' "$cell" \| sed -E 's/^[[:space:]*_`]+//; s/[[:space:]*_`]+$//')` then `[ "${cell,,}" = "no" ]`; fixture `tests/unit/87-prior-attempt.bats:101`, assertions `:157-158`; test (8) `:462-499`; the `surviv` arm `:1068-1071`, still killed by mutant M6 |
| 2 | `factory_prior_byte_cap` counts bytes (`LC_ALL=C`), the marker charged; new test (9) | met | `factory-lib.sh:958` `local -x LC_ALL=C`; the reserve `:967-976`; test `87-prior-attempt.bats:501-527`. Measured: em-dash 60×190 → 14 lines / **7,443 bytes**; ASCII 60×190 → **41 lines / 7,851 bytes** (the section's "at most 41" is exact); end-to-end block 7,981 bytes |
| 3 | the finding rule anchored at the raw line's start; two prose fixture lines | met | `factory-lib.sh:1049-1052` `case $line in [\#*0-9-]*) ;; *) continue ;; esac`; fixture `:93,:95`, assertions `:147-148`. On the real sd1/SD1 review the numbered findings drop 12 → 11: the wrapped prose line is gone |
| 4 | the severity filter | met (code unchanged, now pinned) | `factory-lib.sh:1099`; fixture `87:61-62` (`note …`, `info: …`), assertions `:153-154`; mutant E dies |
| 5 | `--prior r1/K1/extra` refused with the message | met | `tools/factory/seat/factory-task:68-69`; test `87:427-433` asserts status 2, `--prior r1/K1/extra is not a <run>/<KEY> pair`, `[ ! -e "$root/runs/r5" ]`; mutant F dies |
| 6 | `prior:` immediately after `class:`, else after `route:`; one `grep -A1` | met, as far as observable | `factory-task:836-838` sits between `route:` (`:835`) and `plan:` (`:839`); no `class:` line exists in the `.result` today (the only `*class*` printf is `error_class:` at `:853`); test `87:402-405` `run grep -A1 '^route:'` → `lines[0]`/`lines[1]`; mutant G dies. The `class:` arm is dead code-path until SD2 lands — MINOR-2 |
| 7 | the diffstat ends at the blank line; `extra: line` in the fixture | met | `factory-lib.sh:1033` `awk '/^diffstat:$/ { f = 1; next } f && /^$/ { exit } f { print }'`; fixture `87:52`, assertion `:135`; mutant H dies |
| 8 | the bare brief byte-identical unset vs empty; one blank line before the rules | met | `tools/factory/seat/factory-brief:138-143`; test `87:436-460` (`env -u` vs `FACTORY_BRIEF_PRIOR=`, `cmp`, then `*$'\n\n'"## WORKSPACE RULES"*` and `!= *$'\n\n\n'…`); mutant I dies |
| 9 | `none filed` only when no seat review FILE exists; new test (10) | met | `factory-lib.sh:1130` `if [ -z "$opus_file" ] && [ ! -f "$seat_file" ]; then`; test `87:529-557`; mutant J dies |
| 10 | the body's pastes and the grammar-exact result block | met in substance | the body pastes the four reds, five greens and the A–J table with a killing line each; `~/factory/runs/sd4f/SD4b.result` carries `FACTORY-RESULT status=done`, `FACTORY-CHECKS unit=pass lint=pass`, `FACTORY-COMMITS 1`. The item also demands the reds of the *amended* (6) and (7) — those cannot be red (see MINOR-1) |

**The prior review's twelve MINORs, item by item.** MINOR-1 → item 4, closed (mutant E). MINOR-2
→ item 5, closed (F). MINOR-3 → item 6, closed (G). MINOR-4 → item 8, closed (I). MINOR-5 → item
7, closed (H). MINOR-6 (no red/green in the body) → item 10, closed — the body pastes both.
MINOR-7 (Step 1's fixture vs the Tests row) → plan text, left open by the section's own words.
MINOR-8 → item 3, closed (D). MINOR-9 (continuous numbering) → left as SD4 built it, per the
section. MINOR-10 (the MAP Global Constraint) → plan text, open. MINOR-11 (the lint gate's first
pass) → still reproduces, see MINOR-6 below. MINOR-12 → item 9, closed (J).

**SD4's interfaces, re-checked.** Interface 1's clause list is unchanged and still met (the block
order heading → `**Result:**` → `**Diffstat:**` → `**Review findings (…)**` → survivors →
`none filed` is what the real sd1/SD1 probe prints); exit 2 and the exact message on a missing
result (test 4, and through `factory-task` at `87:414`); the composer reads only `<KEY>.result`,
`<KEY>.review.md` and `docs/reviews/*opus-review*-<KEY>.md` — the `CANARY-LOG-LINE` fixture is
asserted absent at `87:109` and `87:397`, mutant M2 dies on both. Interface 2's regex is byte-for-byte
the section's `^[A-Za-z0-9._-]+/[A-Za-z][A-Za-z0-9-]*$`. Interface 3 is unchanged and now pinned
by `cmp`.

**Corpus check of the emphasis rule** (read-only, `~/factory/runs` + the live repo's reviews):
`sd1/SD1` 6 survivor rows, `sd1/SD4` 9, `sc1/G1` 7, `sc5/G12` 3, `pa3/P11` 2, `sc4/G8b` 2 — every
one of the prior gate's "prints `(none)` outright" cases that has a REJECTED review now yields its
rows. `sc1/G4`, `pb11r/P11r` and `sc3/G9` yield no findings block at all because their newest
review is **APPROVED** — correct behaviour, not a regression (`# Opus gate — … — APPROVED`).

## Red before green

**Against the carried implementation** (HEAD's `factory-lib.sh` with SD4's `39eb8cb` version of the
appended block spliced back in — `factory-task` and `factory-brief` are byte-identical between
`39eb8cb` and HEAD, so the whole correction is in one file):

```
1..10
not ok 1 factory_prior_block composes result, findings and survivors, never the log
# (in test file tests/unit/87-prior-attempt.bats, line 147)
#   `[[ "$output" != *"MAJOR-1's evidence is pasted below"* ]]' failed
ok 2 … ok 3 … ok 4 … ok 5 … ok 6 … ok 7
not ok 8 factory_prior_block lists a bold-survivor review's rows, never (none)
#   `[[ "$output" == *"| 3 | drop the guard | f.sh | **no** | — |"* ]]' failed
not ok 9 factory_prior_byte_cap caps at 8,000 bytes, counting bytes
#   `[ "$byte_count" -le 8000 ]' failed
not ok 10 factory_prior_block prints no none-filed marker when a seat review file exists
#   `[[ "$output" != *"**Review:** none filed"* ]]' failed
```

Exactly the four reds the commit body pastes, at the same assertions. Tests 6 and 7 are green
against the carried code by construction — their new assertions pin code SD4 already had right;
their discrimination is shown by mutants F, G and I instead (see MINOR-1).

**Against the true base** (`git checkout e6fc498 -- tools/factory/seat/factory-{lib.sh,task,brief}`):
9 of 10 red (`[ "$status" -eq 0 ]' failed` — `factory_prior_block: command not found`); test 7 is a
negative guard, green at the base by construction and killed by mutant I.

Restored: `nix develop -c bats tests/unit/87-prior-attempt.bats` → `ok 1 … ok 10`; the clone's
`git status --porcelain` is empty.

## Mutants

25 tried, 22 killed. All 19 the two sections name die.

| # | mutant | named | died? | killing line |
|---|---|---|---|---|
| A | restore the exact `"no"` cell comparison | yes | yes | `87:158` `[[ "$output" == *"\| 7 \| **drop the guard** \| f.sh \| **no** \| — \|"* ]]` and `87:496` |
| B | delete the byte-cap comparison | yes | yes | `87:512` `[ "$byte_count" -le 8000 ]` |
| C | drop `local -x LC_ALL=C` | yes | yes | `87:512` `[ "$byte_count" -le 8000 ]` |
| D | drop the raw-line anchor | yes | yes | `87:147` `[[ "$output" != *"MAJOR-1's evidence is pasted below"* ]]` |
| E | widen the severity arm to `*)` | yes | yes | `87:153` `[[ "$output" != *"note tools/z:3 -- not a defect"* ]]` (and `87:556`) |
| F | delete the `--prior` shape regex | yes | yes | `87:423` `[[ "$output" == *"--prior bad is not a <run>/<KEY> pair"* ]]` |
| G | print `prior:` after `plan:` | yes | yes | `87:405` `[ "${lines[1]}" = "prior: r1/K1" ]` |
| H | let the diffstat awk run to EOF | yes | yes | `87:135` `[[ "$output" != *"extra: line"* ]]` |
| I | unconditional `FACTORY_BRIEF_PRIOR` printf | yes | yes | `87:459` `[[ "$output" != *$'\n\n\n'"## WORKSPACE RULES"* ]]` |
| J | test `seat_findings` instead of the file | yes | yes | `87:555` `[[ "$output" != *"**Review:** none filed"* ]]` |
| M1 | the result section copies the whole `.result` | yes (SD4) | yes | `87:122` `[[ "$output" != *"run: r1"* ]]` |
| M2 | append the log's last 20 lines | yes (SD4) | yes | `87:109` and `87:397` `[[ "$output" != *CANARY* ]]` |
| M3 | a finding is any line containing MAJOR/MINOR | yes (SD4) | yes | `87:142` `[[ "$output" == *"1. **MAJOR-1 — the unit check is red**"* ]]` |
| M4 | newest review regardless of verdict | yes (SD4) | yes | `87:138` `[[ "$output" == *"plan_defect: implementer"* ]]` |
| M5 | drop the `no`-cell arm | yes (SD4) | yes | `87:157` and `87:496` |
| M6 | drop the `surviv` arm | yes (SD4) | yes | `87:207` `[[ "$output" == *"\| a typed heading \| **SURVIVED** \|"* ]]` |
| M7 | no 60-line cap | yes (SD4) | yes | `87:279` `[[ "$output" == *"… (140 more lines)"* ]]` |
| M8 | omit the `prior:` line | yes (SD4) | yes | `87:405` `[ "${lines[1]}" = "prior: r1/K1" ]` |
| M9 | print the block from an unset variable | yes (SD4) | yes | `87:446` the bare `factory-brief` call fails under `set -u` |
| X1 | drop the cut marker's reserve | no | yes | `87:512` — without it the em-dash block is 8,014 bytes |
| X5 | anchor findings on `*` only (drop `#`, digit, `-`) | no | yes | `87:203` `[[ "$output" == *"1. ### MAJOR 1 — …"* ]]` |
| X6 | an empty cell also counts as `no` | no | yes | `87:159` `[[ "$output" != *"\| 6 \| drop y"* ]]` (and `87:208`) |
| X2 | `sort` instead of `sort -r` (oldest REJECTED wins) | no | **no** | all 10 green — MINOR-3 |
| X3 | no 60-line cap on the diffstat list | no | **no** | all 10 green — MINOR-4 |
| X4 | no 60-line cap on the survivors list | no | **no** | all 10 green — MINOR-4 |

`mutants_total: 25`, `mutants_killed: 22`, `mutants_outside_named: 6`.

## Checks

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass**, rc 0 — `1..616`, 616 `ok`, 0 `not ok`; tests 308–317 are the new file |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass**, rc 0 |
| lint gate | `nix develop -c githooks/pre-commit` | rc 1 on pass 1 — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` (the block drops `SD4b`, which this commit makes landed in this tree); `git add docs/OPERATIONS.md` → pass 2 **rc 0**. Systemic to task branches, allowed by Global Constraints — MINOR-6 |
| shellcheck | `nix develop -c shellcheck tools/factory/seat/factory-{lib.sh,task,brief}` | rc 0 |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc 0 — already regenerated in the commit (`tests/unit — 21 files` → `22 files`) |
| graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, rc 0 |
| counts | `nix develop -c bats --count tests/unit/87-prior-attempt.bats tests/unit/80-seat-driver.bats` | **91** = 10 + 81, the section's number; `80-seat-driver.bats` untouched and 81/81 green |
| ruff | — | n/a, no python in the diff |

## Touches and commit

Diff `e6fc498..54b57fe` — five files:

```
 docs/MAP.md                       |   2 +-
 tests/unit/87-prior-attempt.bats  | 557 ++++++++++++++++++++++++++++++++++++++
 tools/factory/seat/factory-brief  |   9 +
 tools/factory/seat/factory-lib.sh | 208 ++++++++++++++
 tools/factory/seat/factory-task   |  29 +-
 5 files changed, 802 insertions(+), 3 deletions(-)
```

Four are the section's `touches` exactly; `docs/MAP.md` is the mandatory one-line tests count and
exempt by rule. Nothing outside. The plan file is untouched; `docs/OPERATIONS.md` is not in the
commit (no board commit).

Commit: exactly one (`54b57fe`). Subject byte-identical to the section's `**commit subject:**`
(249 bytes both sides, compared programmatically against plan line 391 → `identical: True`). The
body states the why, pastes the four reds with their failing assertions, five greens by name, and
the A–J mutant table with a killing line each. The two trailers follow one blank line in the
WORKSPACE RULES order (`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat
headless, factory run sd4f)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`).

Driver record (`~/factory/runs/sd4f/SD4b.result`), confirmed as the orchestrator states:
`FACTORY-RESULT status=done`, `FACTORY-CHECKS unit=pass lint=pass`, `FACTORY-COMMITS 1`,
`checks_verified: unit=pass lint=pass` with `checks_verified_src: unit=run lint=run`,
`touches_extra: 0`, `touches_disclosed: 0`, `exit_code: 0`, `error_class: none`, `wall_s: 3419`,
one commit `54b57fe` in `commits (base..task/SD4b)`.

## Findings

No MAJORs.

**MINOR-1 — item 10 asks for reds that cannot exist.** The section's item 10 requires the body to
paste "the reds of (8), (9), (10) and the amended (1), (6), (7) against the carried
implementation". Measured: against the carried implementation tests **6 and 7 pass** — their new
assertions (`--prior r1/K1/extra`, the `grep -A1` adjacency, the `cmp` of unset vs empty) pin code
SD4 already had correct, which is exactly why items 5, 6 and 8 are described as "code-correct but
pinned by new assertions". The seat did the right thing: it pasted the four reds that exist and
carried F, G and I in the mutant table with their killing lines. Plan text, no action owed.

**MINOR-2 — the `class:` arm of item 6 is unreachable and untested.**
`tools/factory/seat/factory-task:836-838`. The rule is "`prior:` sits IMMEDIATELY after `class:`
when that line exists, else immediately after `route:`"; the `.result` has no `class:` line today
(`grep -n "class:" tools/factory/seat/factory-task` → only `error_class:` at `:853`), so the code
prints `prior:` after `route:` unconditionally and no test can exercise the first arm. The layout
is forward-compatible — SD2's `class:` printf must land between `route:` and this `if` block — but
SD2's author has no test to catch it if it does not.

**MINOR-3 — which of two REJECTED reviews wins is unpinned.** `factory-lib.sh:1011-1022`. Replacing
`| sort -r` with `| sort` (oldest REJECTED wins instead of newest) leaves all ten tests green: the
fixtures never carry two REJECTED reviews for the same key, so only the verdict filter (mutant M4)
is discriminated, not the ordering the SD4 contract states ("the newest … sorted by name").

**MINOR-4 — the 60-line cap is pinned on one list of four.** `factory-lib.sh:1030`, `:1033`, `:1092`.
SD4's contract says "Each list is capped at 60 lines"; only the findings list has an assertion
(test 5). Dropping `| factory_prior_cap 60` from the diffstat list (X3) or from the survivors list
(X4) keeps all ten tests green.

**MINOR-5 — two of the four stated cell spellings are untested.** `factory-lib.sh:1074-1085`. Item
1 names `| **no** |`, `| *no* |`, `` | `no` | `` and `| no |`, and "case-insensitively"; the
fixtures carry only `| **no** |` (tests 1 and 8) and `| no |` (test 1). The underscore, backtick
and mixed-case spellings ride on the sed class and `${cell,,}` with no assertion. The strip is one
expression, so the risk is small; recorded because the item enumerates the cases.

**MINOR-6 — the lint gate is rc 1 on the first run in a fresh clone of the branch.** The queue
block regenerates (`… PW1pro SD4b SD6` → `… PW1pro SD6`) because SD4b's own commit makes SD4b
landed in this tree; the seat could not have committed the regenerated block, since the staleness
only exists once the commit does. `git add docs/OPERATIONS.md` → pass 2 rc 0. Identical to the
prior round's MINOR-11 and explicitly allowed by Global Constraints; recorded so the integrator
expects it.

## Verdict

**APPROVED.** Both MAJORs of `docs/reviews/2026-09-08-opus-review-sd1-SD4.md` are closed and
measured on the case the gate named: `factory_prior_block ~/factory/runs ~/nixos-agent-env sd1
SD1` now lists all six `| **no** |` survivor rows in a 3,499-byte block, and the whole-block cap
counts bytes (`LC_ALL=C`, the cut marker charged) — an em-dash block that measured 21,641 bytes
comes out at 7,981. Seven further MINORs of that review are closed by discriminating tests
(mutants D, E, F, G, H, I, J each die at a named line), and the two plan-text ones stay open by
the section's own words. All ten items met, 19 of 19 named mutants dead, three of six unnamed
mutants survive on SD4 clauses the section did not reopen, `unit` (616) and `lint` green under
`--rebuild`, one commit with a byte-identical subject, touches clean, the plan file untouched.
`plan_defect: none`.
