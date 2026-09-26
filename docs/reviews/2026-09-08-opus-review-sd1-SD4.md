---
plan_defect: missing-case
plan_defect_secondary: implementer
mutants_total: 15
mutants_killed: 9
mutants_outside_named: 6
---
# Opus gate — seat run sd1, task SD4 — REJECTED

## Summary

Fresh clone of `task/SD4` at `39eb8cb`, base `af19c5e` (SD1's commit, not main — SD4 was the
second key of the chain "SD1 SD4"). Six files, one commit, subject byte-identical to the
section's. The mechanism is real and works end to end: `factory_prior_block` composes the
`## Prior attempt` block from the prior `.result`, the newest rejecting Opus review and the seat
review, `factory-task --prior` refuses a bad shape and a missing result before anything is
created, records `prior:` immediately after `route:`, and `factory-brief` prints the block only
when the env var is set. Red is real (6 of the 7 tests fail against the base's three scripts),
all **nine** mutants the section names die, and `unit` (609 tests) and `lint` are green under
`--rebuild`.

It is rejected on two MAJORs, both about what the block *contains*:

* **MAJOR-1** — the survivors rule extracts nothing from the review it was built to carry. Run
  against the real prior attempt of this very run (`factory_prior_block ~/factory/runs
  ~/nixos-agent-env sd1 SD1`), the block prints `**Mutation-table survivors:** (none)` while
  `docs/reviews/2026-09-08-opus-review-sd1-SD1.md` has **six** surviving rows — they are written
  `| **no** |`, and neither the `surviv` arm nor the "exact cell `no`" arm sees them. SD1b is on
  the seat now; this is its brief. The section's own words ("the exact cell `no`") caused it —
  `missing-case`.
* **MAJOR-2** — the whole-block cap is a *character* cap, not the stated 8,000-**byte** cap.
  Measured: 21,641 bytes emitted for a multibyte block (`${#line}` counts characters under the
  devShell's `LANG=en_US.UTF-8`; the same fixture under `LC_ALL=C` gives 7,591). One line.

Twelve MINORs. Six of them are mutants the section did not name and that no assertion kills: the
seat-review severity filter, the `--prior` shape refusal, the `prior:` position, the bare
brief's "nothing extra", the diffstat's blank-line terminator, and the byte cap itself.

## Contract items

**Interface 1 — `factory_prior_block <runs-dir> <repo-path> <run> <KEY>`.**

| clause | verdict | evidence |
|---|---|---|
| prints the block to stdout, exit 0 | met | `factory-lib.sh:1143`, `:1272`; test 1 `[ "$status" -eq 0 ]` |
| exit 2 + `factory_prior_block: no prior result <runs-dir>/<run>/<KEY>.result` on a missing file | met | `:1152-1155`; test 4 asserts both, and the same message reaches `factory-task`'s stderr (test 6) |
| heading `## Prior attempt (<run>/<KEY>)` first | met | `:1246`; test 1 `[[ "$output" == "## Prior attempt (r1/K1)"* ]]` |
| `**Result:**` then the first four lines and every line keyed `model effort route class rung fallback seat exit_code wall_s error_class usage`, in file order | met | `:1173-1179`; test 1 asserts each key present and `run:`/`key:`/`workspace:`/`branch:`/`head:`/`base:` absent; mutant M1 (copy the whole `.result`) dies |
| `**Diffstat:**` then `diffstat:` → next blank line | met (terminator untested — MINOR-5) | `:1181`; the real sd1/SD1 probe emits exactly the six stat lines, no `commits (…)` header, no `usage:` |
| newest `*opus-review*-<KEY>.md` by name whose H1 ends `— REJECTED` | met | `:1160-1169` (`sort -r`, break on the first `*REJECTED`); mutant M4 dies; the fixture's later-sorting APPROVED review is skipped |
| then the seat review `<runs-dir>/<run>/<KEY>.review.md` when it exists | met | `:1234-1243` |
| the Opus front-matter lines `plan_defect`, `mutants_total`, `mutants_killed`, `mutants_outside_named` verbatim | met | `:1186-1194`; test 1 asserts all four; the real probe prints `plan_defect: wrong-fact / 29 / 23 / 2` |
| findings numbered, a line qualifying when the leading `#*_. 0-9-` strip leaves `MAJOR`/`MINOR` | met literally (false positives on real files — MINOR-8) | `:1195-1201`; mutant M3 dies; on the real CX1 review four wrapped prose lines (`   MAJOR-9), so the hardening …`) become findings 1, 17, 19, 20 |
| for the seat review, every line starting `blocker `, `major `, `minor ` | met (filter untested — MINOR-1) | `:1237` |
| `**Mutation-table survivors:**` — `|` lines containing `surviv` (any case) or an exact `no` cell — or `(none)` | **NOT met in substance — MAJOR-1** | `:1205-1231`; on `docs/reviews/2026-09-08-opus-review-sd1-SD1.md` (6 rows `| **no** |`) the block prints `(none)` |
| `**Review:** none filed` when neither review exists | met (over-fires — MINOR-12) | `:1268-1270`; also fires when a seat review exists with no severity line, or when only an APPROVED Opus review exists |
| each list capped at 60 lines, a cut marked `… (N more lines)` | met | `:1090-1111`; test 5 (`60. **MAJOR-60 …`, `… (140 more lines)`, no `61.`); mutant M7 dies |
| the whole block capped at 8,000 **bytes** | **NOT met — MAJOR-2** | `:1122` `[ $((bytes + ${#line} + 1)) -gt 8000 ]` counts characters; measured 21,641 bytes |
| reads exactly `<KEY>.result`, `<KEY>.review.md`, `docs/reviews/*opus-review*-<KEY>.md` — never `<KEY>.log`, a transcript, `.dsh-home` | met | the only reads in `:1143-1272` are those three; the `CANARY-LOG-LINE` fixture never appears (tests 1 and 6); mutant M2 (append the log's last 20 lines) dies at `87-prior-attempt.bats:101` |

**Interface 2 — `factory-task … --prior <run>/<KEY>`.**

| clause | verdict | evidence |
|---|---|---|
| value must match `^[A-Za-z0-9._-]+/[A-Za-z][A-Za-z0-9-]*$`, else `die 2` | met (untested as such — MINOR-2) | `factory-task:68-69` |
| the block composed before the brief; a missing prior result → `die 2`, nothing created | met | `:200-206` sits before `mkdir -p -- "$runs_dir"` (`:210`), `factory-ws` (`:224`) and `factory-brief` (`:243`); test 6 asserts status 2 and `[ ! -e "$root/runs/r3" ]` |
| passed to `factory-brief` as `FACTORY_BRIEF_PRIOR` | met | `:204-205` (`export`); test 6 reads the recorded brief |
| the new `.result` carries `prior: <run>/<KEY>` after `class:`, or after `route:` when no class line exists | met | `factory-task:836-838`; no `class:` line exists in the `.result` (the only `*class*` printf is `error_class:` at `:853`), so `prior:` belongs after `route:` — it is emitted between `route:` (`:835`) and `plan:` (`:839`). The seat's `FACTORY-NOTES` ("`--prior` records `prior:` after `route:`") is accurate, and Assumption 24's `plan:`-after-`route:` order is preserved. |
| `--prior` does not derive the fix-round key | met | the key is argv's; `:201-202` only splits the prior pair |

**Interface 3 — `factory-brief`.** Met. `factory-brief:138-143` prints the block between the task
section (`:137`) and `$rules` (`:144`), preceded by a blank line, only when the variable is set
and non-empty; test 7 (bare `factory-brief plan.md K1b`) shows no `## Prior attempt`, and mutant
M9 (print it from an unset variable) kills that test through `set -u`. Under-pinned — MINOR-4.

## Red before green

Base implementation files (`git checkout af19c5e -- tools/factory/seat/factory-{lib.sh,task,brief}`)
against the branch's `tests/unit/87-prior-attempt.bats`:

```
1..7
not ok 1 factory_prior_block composes result, findings and survivors, never the log
#   `[ "$status" -eq 0 ]' failed
not ok 2 … not ok 3 … not ok 4 … not ok 5 …
not ok 6 factory-task --prior composes the block into the brief and records prior:
#   (in test file tests/unit/87-prior-attempt.bats, line 371)
#   `[ "$status" -eq 0 ]' failed
ok 7 factory-brief run bare prints no prior block
BW01: … `factory_prior_block …` exited with code 127, indicating 'Command not found'
```

Six of seven red, exactly as the section's Step 1 predicts (`factory_prior_block: command not
found`; `factory-task` exit 2 on the unknown `--prior`). Test 7 is a negative guard and is green
at the base by construction — it is not vacuous: mutant M9 turns it red. Restored, all seven
pass (`nix develop -c bats tests/unit/87-prior-attempt.bats` → `ok 1 … ok 7`).

## Mutants

Nine named, all killed. Six unnamed tried, all six survive.

| # | mutant | named | died? | killing assertion |
|---|---|---|---|---|
| 1 | the result section copies the whole `.result` | yes | yes | `87:114` `[[ "$output" != *"run: r1"* ]]` |
| 2 | append the log's last 20 lines to the block | yes | yes | `87:101` `[[ "$output" != *CANARY* ]]` (and `87:378`) |
| 3 | a finding is any line containing `MAJOR`/`MINOR` | yes | yes | `87:131` `[[ "$output" == *"1. **MAJOR-1 — the unit check is red**"* ]]` (the prose row "One MAJOR stops it" takes number 1) |
| 4 | take the newest review regardless of verdict | yes | yes | `87:127` `[[ "$output" == *"plan_defect: implementer"* ]]` |
| 5 | drop the `no`-cell arm | yes | yes | `87:139` `… "| 5 | drop x | factory-lib.sh | no | t1 |"` |
| 6 | drop the `surviv` arm | yes | yes | `87:188` `… "| a typed heading | **SURVIVED** |"` |
| 7 | no 60-line cap | yes | yes | `87:260` `[[ "$output" == *"… (140 more lines)"* ]]` |
| 8 | omit the `prior:` line from the `.result` | yes | yes | `87:383` `… "route: implement/code/S"*"prior: r1/K1"*` |
| 9 | print the block from an unset variable (bare brief) | yes | yes | `87:412` `[ "$status" -eq 0 ]` (set -u) |
| 10 | `factory-brief` prints `"${FACTORY_BRIEF_PRIOR:-}"` unconditionally | no | **no** | all 7 green; every bare brief gains two blank lines |
| 11 | the seat-review filter `blocker \|major \|minor ` → `*)` | no | **no** | all 7 green; the fixture's `FACTORY-REVIEW verdict=rework` line is not asserted absent |
| 12 | `prior:` printed after `plan:` instead of after `route:` | no | **no** | all 7 green; `87:383` only pins "somewhere after `route:`" |
| 13 | the 8,000-byte cap removed entirely | no | **no** | all 7 green — the whole-block cap has no assertion |
| 14 | the diffstat section runs to EOF (no blank-line stop) | no | **no** | all 7 green |
| 15 | the `--prior` shape regex dropped | no | **no** | all 7 green — `--prior bad` still exits 2 via the missing-result path (`runs/bad/bad.result`) |

`mutants_total: 15`, `mutants_killed: 9`, `mutants_outside_named: 6`.

## Checks

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass, rc 0, 609 `ok`, no `not ok`; tests 316–322 are the new file |
| lint | `… .lint … --rebuild` | pass, rc 0 |
| lint gate | `nix develop -c githooks/pre-commit` | rc 1 on pass 1 — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; `git add docs/OPERATIONS.md` → pass 2 rc 0. Systemic, not SD4's: the same happens at `af19c5e` (SD1's commit) and not at the landed `55753ba`; a task's own commit makes its key "landed" in the tree so the derived queue drops it. Allowed by Global Constraints ("may regenerate the board's queue block once"). MINOR-11. |
| shellcheck | `nix develop -c shellcheck tools/factory/seat/factory-{lib.sh,task,brief}` | rc 0 |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc 0 — already regenerated in the commit |
| graph | `python3 pkgs/evidence/tasks.py --root . check` | silent, rc 0 |
| counts | `nix develop -c bats --count tests/unit/87-prior-attempt.bats tests/unit/80-seat-driver.bats` | 88 = 7 + 81; `80-seat-driver.bats` unchanged at Assumption 24's 81 |
| ruff | — | n/a, no python in the diff |

End-to-end probe on the real prior attempt (read-only, `~/factory/runs` + the live repo's
`docs/reviews`): `factory_prior_block /home/dalhaka/factory/runs /home/dalhaka/nixos-agent-env
sd1 SD1` → a 3,126-byte, 40-line block carrying the four `FACTORY-*` lines, the keyed metadata,
the six-line diffstat, `plan_defect: wrong-fact / 29 / 23 / 2` and twelve numbered findings —
and `**Mutation-table survivors:** (none)` (MAJOR-1).

## Touches and commit

Diff `af19c5e..39eb8cb` — six files:

```
 docs/MAP.md                       |   2 +-
 docs/OPERATIONS.md                |   2 +-
 tests/unit/87-prior-attempt.bats  | 414 ++++++
 tools/factory/seat/factory-brief  |   9 +
 tools/factory/seat/factory-lib.sh | 188 +++++
 tools/factory/seat/factory-task   |  29 ++-
```

Four are the section's `touches` exactly. `docs/MAP.md` is the one-line tests count (`tests/unit
— 21 files` → `22 files`), mandatory for the lint gate's repomap check and exempt (MINOR-10:
Global Constraints still say no task in this plan regenerates MAP — the same wrong fact SD1's
gate recorded). `docs/OPERATIONS.md` is a single line inside the `<!-- tasks:begin -->…<!--
tasks:end -->` fence (`… SD1 SD4 …` → `… SD2 SD3 SD4 …`), exempt by rule; nothing outside the
fence changed, so it is not a board commit. No file outside the list is unexplained; the plan
file is untouched.

Commit: exactly one (`39eb8cb`). Subject byte-identical to the section's `**commit subject:**`
(`diff` of `git log -1 --format=%s` against the section's line → no output). Body states the why
in eleven lines; the two trailers follow one blank line in the WORKSPACE RULES order
(`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sd1)`
then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`). The body pastes neither the red
nor the green — MINOR-6.

Driver record (`~/factory/runs/sd1/SD4.result`), confirmed: `FACTORY-RESULT status=done`,
`FACTORY-CHECKS unit=pass lint=pass`, `FACTORY-COMMITS 1`, `checks_verified: unit=pass lint=pass`
with `checks_verified_src: unit=run lint=run`, `touches_extra: 0`, `touches_disclosed: 0`,
`exit_code: 0`, `error_class: none`, `wall_s: 3116`, one commit in `commits (base..task/SD4)`.

**Rebase onto main after SD1b lands:** clean. SD1's hunks in `factory-lib.sh` end at new-file
line 792 (`@@ -467,30 +467,57 @@` … `@@ -624,11 +729,64 @@`, all inside `factory_task_kind_size`
/ `factory_route`); SD4's single hunk is `@@ -1083,3 +1083,191 @@ factory_disclosed()` — a pure
append at EOF whose context (`git show 55753ba:…| tail -20` vs `git show af19c5e:…| tail -20`)
is byte-identical. No overlapping line. `factory-task` and `factory-brief` are not in SD1's diff
at all (`git diff 55753ba..af19c5e --stat`: MAP, claims.toml, routing.toml,
84-routing-ladder.bats, route.py, factory-lib.sh).

## Findings

**MAJOR-1 — the mutation-table survivors are dropped from the one review this feature exists to
carry.** `tools/factory/seat/factory-lib.sh:1205-1231`. A `|` row is kept when it contains
`surviv` (case-insensitive) or when one of its `|`-split, whitespace-stripped cells is exactly
`no` (`:1219` `if [ "$cell" = "no" ]`). A large minority of the corpus writes the `died?` cell in
bold. Measured against the live tree:

```
$ factory_prior_block /home/dalhaka/factory/runs /home/dalhaka/nixos-agent-env sd1 SD1
…
**Mutation-table survivors:**
(none)

$ grep -c '| \*\*no\*\* |' docs/reviews/2026-09-08-opus-review-sd1-SD1.md
6
$ grep -n '^|' docs/reviews/2026-09-08-opus-review-sd1-SD1.md | sed -n '3p;9p'
135:| 3 | **drop `[ "$wrung" = "1" ] || continue` (:742)** | factory-lib.sh | **no** | — |
141:| 9 | **delete the unreachable rule (:641-644)** | factory-lib.sh | **no** | — |
```

Corpus scan of the 202 `docs/reviews/*opus-review*.md` files: 18 carry `| **no** |` rows; for
**10** of them no row carries `surviv` either, so the survivors section is `(none)` outright —
`sd1-SD1` (6), `sc1-G1` (7), `sc1-G4` (7), `sc1-G1b` (3), `sc5-G12` (3), `pb11r-P11r` (3),
`pa3-P11` (2), `sc3-G9` (2), `sc4-G8b` (2), `dsh-harness-F6` (2). In the other 8 (e.g.
`cx1-CX1`, `cx1b-CX1b`) the bold rows are dropped and only the prose-matched ones survive. For
the ten, `(none)` is not an omission but an affirmative false statement to the fix round that no
mutant survived. SD1b is on the seat now and `--prior sd1/SD1` is exactly its brief.

The code is faithful to the section, which says "whose cells (split on `|`, stripped) include
the exact cell `no`" and whose Facts point at Assumption 17 ("a mutation table … with `yes`/`no`
cells", "`**SURVIVED**`"). Assumption 17 is true of the two files it cites and false of the
corpus: the case of an emphasized cell is missing. Hence `plan_defect: missing-case`. The fix is
one line — strip `*`/`_` from the cell before the comparison (the finding rule at `:1196`
already does exactly this strip for headings) — plus a fixture row `| 7 | … | **no** | … |` in
test 1 and its mutant.

**MAJOR-2 — the "8,000 bytes" cap is 8,000 characters, and nothing tests it.**
`tools/factory/seat/factory-lib.sh:1113-1131`; the contract is "the whole block at 8,000 bytes"
and the function's own comment says "Cap the whole block (stdin) at 8,000 bytes on complete
lines". `:1122` is `if [ $((bytes + ${#line} + 1)) -gt 8000 ]` — in bash `${#s}` is a *character*
count in a multibyte locale, and the devShell's locale is UTF-8 (`nix develop -c bash -c 'echo
$LANG; s="————"; echo ${#s}'` → `en_US.UTF-8`, `4`). Measured on a block of sixty 190-character
em-dash findings (Opus reviews are em-dash-dense by house style):

```
block bytes: 21641
block chars: 7883
block lines: 51
cut marker present: 1          # the cap fired — at 7,883 chars = 21,641 bytes

# same fixture, same code, C locale:
block bytes: 7591   chars: 7591   lines: 26
```

2.7× the stated bound; on ordinary review text the overrun is small (the real sd1/SD1 block is
3,126 bytes for 3,096 characters), but the bound is the plan's only defense against an oversized
brief and it is stated in bytes. Compounding it, mutant 13 shows the cap is pinned by no
assertion at all: deleting `factory_prior_byte_cap`'s comparison entirely leaves all seven tests
green. Fix: `LC_ALL=C` around the length, or `bytes=$(printf '%s\n' "$line" | wc -c)`, plus a
test that feeds > 8,000 bytes of multibyte content and asserts `wc -c` ≤ 8,000.

**MINOR-1 — the seat review's severity filter is untested.** `factory-lib.sh:1237`. Replacing
`blocker\ * | major\ * | minor\ *)` with `*)` keeps all seven tests green: the fixture's third
line (`FACTORY-REVIEW verdict=rework`) is never asserted absent, and the two asserted lines keep
their numbers 3 and 4.

**MINOR-2 — `--prior`'s shape refusal is untested as such.** `factory-task:68-69`. Deleting the
regex leaves test 6's `--prior bad` case green: `prior_run=bad`, `prior_key=bad`, and the
composer's own missing-result path gives the same exit 2 with no run dir. The test would
discriminate if it asserted the message `--prior bad is not a <run>/<KEY> pair`.

**MINOR-3 — `prior:`'s position is pinned only as "somewhere after `route:`".**
`87-prior-attempt.bats:383` is `[[ "$output" == *"route: …"*"prior: r1/K1"* ]]`; moving the
printf below `plan:` keeps it green. The placement is correct as written (`factory-task:836-838`),
but a `prior:` that drifted below `workspace:` or `seat:` would not be caught.

**MINOR-4 — "a bare `factory-brief` prints nothing extra" is under-pinned.**
`factory-brief:138-143`. An unconditional `printf '%s\n\n' "${FACTORY_BRIEF_PRIOR:-}"` adds two
blank lines to every brief the driver composes and all seven tests stay green; only the `set -u`
form of the mutant dies.

**MINOR-5 — the diffstat's blank-line terminator is untested.** `factory-lib.sh:1181`. Letting
the awk run to EOF (dropping `f && /^$/ { exit }`) keeps all seven green — the `usage:` line it
would then swallow is asserted present anyway, from the result section.

**MINOR-6 — the commit body pastes neither the red nor the green**, which Global Constraints
require ("Paste the red command and its output, then the change, then the green check by name").
The body is a prose account only. Same MINOR as SD1's.

**MINOR-7 — the section's Step 1 fixture contradicts its own Tests row.** Step 1 names
`2026-09-06-opus-review-r1-K1.md` (REJECTED) and "a second review
`2026-09-05-opus-review-r0-K1.md` that is APPROVED" — with the APPROVED one sorting *earlier*,
which cannot discriminate "newest REJECTED" from "newest". The Tests row demands the opposite
("the discriminating row is the APPROVED review with the LATER-sorting date"). The seat followed
the Tests row (`87-prior-attempt.bats:66-94`: APPROVED at 09-06, REJECTED at 09-05) and mutant 4
dies — the right call, recorded because the section's two halves disagree.

**MINOR-8 — the finding rule produces false findings on real reviews.** Contract-faithful
(`factory-lib.sh:1195-1201`), but on `docs/reviews/2026-09-07-opus-review-cx1-CX1.md` four
wrapped continuation lines qualify, e.g. finding 1 is `   MAJOR-9), so the hardening is
unenforced against exactly the file the brief` and finding 19 is `MAJOR-7 or MAJOR-9.` — noise
ahead of the real MAJOR-1. Worth a `- ` / `**`-anchored rule in a later round.

**MINOR-9 — the numbering is continuous across the two reviews.** `factory-lib.sh:1198` and
`:1238` share `n`, so the seat review's defects are numbered 3, 4 after the Opus findings. The
section attaches "numbered `1.`, `2.`, …" to the Opus clause and says nothing about numbering the
seat lines; the test (`87:135-136`) enshrines the continuous reading. Under-specified, not wrong.

**MINOR-10 — the MAP.md Global Constraint is a wrong fact for this plan.** It says no task here
regenerates `docs/MAP.md`; the new `tests/unit/87-prior-attempt.bats` forces the tests count
21 → 22 and the lint gate refuses without it. Already recorded at SD1's gate (its MINOR-6).

**MINOR-11 — the lint gate is rc 1 on the first run in a fresh clone of the branch.** The queue
block regenerates (`… SD2 SD3 SD4 SD5 SD8` → `… SD2 SD3 SD5 SD8`) because SD4's own commit makes
SD4 landed in this tree. Identical at `af19c5e`, absent at the landed `55753ba` — systemic to
task branches and explicitly allowed by Global Constraints; recorded so the integrator expects it.

**MINOR-12 — `**Review:** none filed` over-fires.** `factory-lib.sh:1268` tests `[ -z
"$opus_file" ] && [ -z "$seat_findings" ]`, so it prints when a seat review *exists* but carries
no `blocker `/`major `/`minor ` line, and when the only Opus review is APPROVED. Harmless today
(both readings mean "no rejecting finding"), but the marker claims more than it knows.

## Verdict

**REJECTED.** Two MAJORs: the survivors rule extracts nothing from a review whose survivors are
written `| **no** |` — measured on `sd1/SD1`, the exact prior attempt this feature's first
customer will pass — and the whole-block cap counts characters where the contract says bytes,
with no test on it either way. Everything else in the section is met: nine named mutants dead,
red reproduced on six of seven tests, `unit` and `lint` green under `--rebuild`, one commit with
a byte-identical subject, touches clean, and a clean append-at-EOF rebase onto main after SD1b.

A fix round (SD4b) is small: strip emphasis from the survivor cell (and add a `| **no** |`
fixture row plus its mutant), make the byte cap count bytes (and test it with multibyte content),
and pick up MINORs 1–5 by tightening five assertions the section already implies. `plan_defect:
missing-case` (the survivors rule's missing case is the section's own words), secondary
`implementer` (bytes vs characters).
