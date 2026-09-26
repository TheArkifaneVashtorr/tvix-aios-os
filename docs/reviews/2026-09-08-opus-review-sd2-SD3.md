---
plan_defect: missing-case
plan_defect_secondary: implementer
mutants_total: 20
mutants_killed: 16
mutants_outside_named: 6
---
# Opus gate — seat run sd2, task SD3 — REJECTED

## Summary

SD3's contract is met, item by item, in the code: `factory_rung_of_key` is the
CHAIN_RE rule in pure bash; `factory-task` and `factory-review` climb the ladder
at the key's rung, write a `<KEY>.escalate` and exit 4 before any workspace, log,
pid file or `.result`; `factory-wave` prints `status=escalated` and `driver:`;
`tasks.py` grows `read_escalations` and the brief's `**Escalated:**` line;
`factory-task` spools with `--no-start --wait` inside a seat unit. All nine of
the section's tests are red against the base implementation and green on the
branch, and all fourteen mutants the Tests block names die.

It is rejected on one thing, and it is the acceptance check: **`unit` is red.**
`tests/unit/87-prior-attempt.bats` (SD4b, landed on main after this section was
typed) test "factory-task --prior composes the block into the brief and records
prior:" now fails, because SD3's own rule turns its key `K1b` into rung 2 while
87's routing fixture has only a rung-1 row — the lookup exhausts and
`factory-task` escalates with exit 4 where the test asserts 0. The section's
Step 3 green list names five bats files and does not name 87; all 155 of those
tests pass. The seat ran the list and not the acceptance check, and ended its
reply with no FACTORY-RESULT block at all, so the red was never disclosed.

Diagnosis confirmed (below, with the driver's own stderr). The minimal, correct
resolution is a **rung-2 row in 87's fixture**, not `--rung 1` in the test and
nothing in SD3's rule: the row keeps the test exercising the natural
(non-explicit) climb, matches the shape of the live table, and does not put
`rung: … (explicit)` into a `.result` whose adjacency SD4b's assertions read.
Measured: with the six-line row added, 87 goes 10/10 green and no other test
moves. That is SD3b's one item.

Everything else here is MINORs — five stated contract clauses with no
discriminating assertion, and the commit body's missing red/green paste.

## Contract items

Judged against `### SD3 (` of `docs/superpowers/plans/2026-09-06-seat-driver.md`
(plan lines 147–170), on `git diff 6010cb1..HEAD`.

**1. `factory_rung_of_key KEY` — MET.** `tools/factory/seat/factory-lib.sh:799-818`.
Pure bash, two `case` blocks: the trailing one or two `[a-z]` after a digit is
the suffix, an `r` in it is rung 3, any other suffix rung 2, no suffix rung 1.
All seven keys of the section resolve as specified, plus `CR2r3b` → 2
(`tests/unit/86-rung-and-escalate.bats:135-142`, green). Agrees with `tasks.py`'s
`CHAIN_RE` on each (`P3Ar2` ends in a digit → its own root → 1; `SD3rb` → suffix
`rb` → 3).

**2. `factory-task … [--rung N] [--fallback]` — MET.**
- rung from the key, `--rung` wins: `factory-task:222-224`
  (`rung=${rung:-$(factory_rung_of_key "$key")}`, `rung_label="$rung (explicit)"`).
- `--rung` validation `die 2`: `factory-task:65-73` — `'' | *[!0-9]* | 0` refuses
  (so `x`, empty, `0` and `-1` all die 2). Test asserts status 2 at `:250-251`.
- the lookup `factory_route --rung … --class … [--fallback] implement …`:
  `factory-task:261-264`.
- exit 0 → today's path, `rung: N` after `effort:`: `factory-task:945-946`
  (`effort:` then `rung:` then `route:`); asserted as an adjacency at
  `86-rung-and-escalate.bats:173,185`.
- `fallback: <model>` after `class:` when `--fallback` chose it:
  `factory-task:225,272-274,948-951`.
- exit 3 → warning + built-in default with `rung: N`: `factory-task:277-281`.
- **exit 4 → escalation**: `factory-task:152-193` (`factory_task_escalate`). All
  eleven lines are written (`run: key: role: rung: escalate: model: effort:
  route: class: plan: launch:`, `:178-188`); the `claude` implement row is
  resolved at `:155`; `<TASKS>` comes from `waves --factory-args` with the
  literal placeholder on a non-zero query (`:164-167`); the stderr sentence is
  `factory-task: <KEY> at rung N is a claude rung — the launch line is in <path>`
  (`:190`, measured verbatim below); the `launch:` line alone on stdout (`:191`);
  `exit 4` (`:192`), reached from `:286` — i.e. **before** the `factory-ws` call
  at `:326`, before the log, the pid file and the `.result`. Test 3
  (`86…:188-216`) pins exit 4, the single stdout line, the `.escalate` fields and
  the absence of `.result`, `.log`, `.pid` and of any `factory-ws` call.
- `--fallback` + exit 4 → `die 2 "no fallback for <key> at rung N"`, nothing
  written: `factory-task:283-285`; test at `86…:284-291`.
- explicit `--model`/`OPENROUTER_MODEL` still wins, `route: explicit` with
  `rung: N`: `factory-task:249-258` (the lookup there is lenient, `|| true`, no
  escalation). Code correct; **no assertion** — MINOR-6.

**3. `factory-review` — MET.** `factory-review:88` derives the rung from the key;
`:107` (explicit arm) and `:113` (ladder arm) pass `--rung`/`--class`; `:122`
routes exit 4 to `factory_review_escalate` (`:35-59`), which writes `run: key:
role: review rung: escalate: claude/review model: effort: launch:` and the
launch sentence `opus-gate task/<KEY> ~/factory/ws/<run>/<KEY>` (`:44`), then
exits 4. The whole block is moved **above** `factory_need_dir "$task_ws"`, the
`runs_dir` mkdir and the `.gate` marker (`:106-134` vs the base's `:55-68`), so
no review workspace, no `.review.md` and no `.gate` exist. Test 6
(`86…:294-315`) pins exit 4, `role: review`, `escalate: claude/review`,
`model: opus`, and the absence of `.review.md` and `.gate`; that last assertion
is live (outside-mutant O5 killed it).

**4. `factory-wave` — MET.** `factory-wave:216-228`: a key with `<KEY>.escalate`
and no `.result` prints
`KEY status=escalated checks=- commits=- minutes=- tokens=- escalate=<role>` and
sets `overall_rc=1`. `run.meta` gains `driver: <SEAT_JOB_ID>` immediately after
`plan:` and only when the variable is non-empty (`:155-159`). `tools/ritual.sh`
ignores it (test 7's third block runs `ritual.sh inflight` and gets exit 0).
Test 7 (`86…:317-361`) pins the summary line, the `plan:`/`driver:` adjacency and
the no-`driver:` row.

**5. `tasks.py` — MET (one clause untested).** `read_escalations(runs_dir)`
(`pkgs/evidence/tasks.py:664-694`) returns `{key: {run, role, escalate, rung,
launch}}`, newest run directory wins by `getmtime`. `render_brief` appends
`**Escalated:** <key> (<escalate>, rung N, run <run>) · …`, else
`**Escalated:** none`, immediately after the `Rejected, fix round owed` line
(`:1905-1913`). The queue block is untouched (`render_board_block` unchanged in
the diff). The "keeps its derived state" clause is asserted, but on a key that
is not the escalated one and through a graph whose `runs_dir` is not the
escalations dir — MINOR-5.

**6. `factory-task` inside a seat unit — MET.** `factory-task:386-395`:
`spool_flags=(--no-start --wait)` when `SEAT_JOB_ID` is non-empty, `()` on the
host; expanded into the `seat-submit headless` argv at `:394`; the `seat:` line
is unchanged (`:958-964`). Test 8 (`86…:363-398`) pins both rows.

## Red before green

Method: a fresh clone at `task/SD3`, then a scratch copy in which the base's five
implementation files are restored (`git checkout 6010cb1 -- factory-lib.sh
factory-task factory-review factory-wave tasks.py`) while the branch's tests
stay. `nix develop -c bats tests/unit/86-rung-and-escalate.bats`:

```
1..8
not ok 1 factory_rung_of_key classifies the chain suffix: root 1, fix 2, replan 3
#   `got=$("$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_rung_of_key '$key'")' failed with status 127
#   bash: line 1: factory_rung_of_key: command not found
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
#   `[[ "$output" == *"K2r status=escalated … escalate=claude/implement"* ]]' failed
not ok 8 factory-task spools (--no-start --wait) inside a seat unit, not on the host
#   `[[ "$output" == *"--no-start --wait"* ]]' failed
```

and the pytest:

```
>       assert "**Escalated:** K2r (claude/implement, rung 3, run r3)" in md
E       AssertionError
tests/evidence/test_tasks.py:809: AssertionError
1 failed in 0.21s
```

Eight of eight bats tests and the one pytest are red at the base; all nine are
green on the branch (`bats tests/unit/86-rung-and-escalate.bats` → `1..8`, eight
`ok`; `pytest tests/evidence -q` → 478 passed). No test in this section is
vacuous.

## Mutants

Each applied in a scratch copy of the clone, run, reverted. 20 total, 16 killed.

| # | mutant | file | died? | on |
|---|---|---|---|---|
| 1 | `r` anywhere in the KEY counts (not the suffix) | factory-lib.sh:806-818 | yes | 86 test 1, line 140 (`[ "$got" = "$want" ]`), on `CR2r3b` |
| 2 | rung not passed to the lookup | factory-task:261 | yes | 86 tests 2/3/4/5; test 2 line 182 `[[ "$output" == *"effort=high"* ]]` |
| 3 | write a `.result` with `status=failed` on exit 4 | factory-task:191 | yes | 86 test 3 line 212 `[ ! -e "$FACTORY_RUNS/r3/K2r.result" ]` |
| 4 | create the workspace before the lookup | factory-task:218 | yes | 86 test 3 line 215 `[ ! -e "$BATS_TEST_TMPDIR/ws-calls" ]` |
| 5 | escalation exits 3, not 4 | factory-task:192 | yes | 86 test 3 line 197 `[ "$status" -eq 4 ]` |
| 6 | `--rung` accepted without validation | factory-task:65-73 | yes | 86 test 4 line 251 `[ "$status" -eq 2 ]` |
| 7 | `--fallback` ignored | factory-task:262 | yes | 86 test 5 line 279 `[[ "$output" == *"model=m/f"* ]]` |
| 8 | the no-fallback arm writes an `.escalate` | factory-task:283-286 | yes | 86 test 5 line 290 `[ "$status" -eq 2 ]` |
| 9 | `factory-review` keeps the rung-1 lookup | factory-review:113 | yes | 86 test 6 line 305 `[ "$status" -eq 4 ]` |
| 10 | the wave summary reads `status=unknown` | factory-wave:219 | yes | 86 test 7 line 343 |
| 11 | `driver:` written when `SEAT_JOB_ID` is unset (empty value) | factory-wave:155-159 | yes | 86 test 7 line 355 `[[ "$output" != *"driver:"* ]]` |
| 12 | always pass `--no-start --wait` | factory-task:389-392 | yes | 86 test 8 line 396 `[[ "$output" != *"--no-start"* ]]` |
| 13 | never pass them | factory-task:389-392 | yes | 86 test 8 line 388 |
| 14 | drop the `**Escalated:**` line from the brief | tasks.py:1905-1913 | yes | `test_brief_lists_escalations` line 809 |
| O1 | `rung:` printed after `route:` instead of after `effort:` | factory-task:945-947 | yes | 86 test 2 line 173 (the `effort: medium\nrung: 1` adjacency) |
| O2 | `fallback:` printed **before** `class:` | factory-task:948-951 | **no** | 86, 80, 85, 87 all unchanged — MINOR-1 |
| O3 | the `.escalate` drops its `route:`, `class:` and `plan:` lines | factory-task:185-187 | **no** | 86 test 3 green — MINOR-2 |
| O4 | `read_escalations` keeps the **oldest** run (`<` for `>`) | tasks.py:689 | **no** | `pytest tests/evidence -q` → 478 passed — MINOR-3 |
| O5 | the review escalation leaves a `.gate` marker behind | factory-review:41 | yes | 86 test 6 line 314 `[ ! -e "$FACTORY_RUNS/r6/K2b.gate" ]` |
| O6 | the review `.escalate`'s `launch:` becomes the literal `MUTANT` | factory-review:40 | **no** | 86 test 6 green — MINOR-4 |

mutants_total 20 · mutants_killed 16 · mutants_outside_named 6 (O1–O6).

## Checks

Every command run from inside the fresh clone
`…/scratchpad/SD3/gate-sd2-SD3`, tools through `nix develop -c`.

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link` | **FAIL** (`--rebuild` refused: the derivation has no valid output to check, so a full fresh build was run instead). `1..639`, exactly one `not ok`: 336. |
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | pass — `479 passed in 13.47s` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | pass |
| lint gate | `nix develop -c githooks/pre-commit` | pass on the documented flow: the first run regenerates the board queue block (`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`, rc 1); after `git add docs/OPERATIONS.md` the second run is rc 0. The staleness is the gate clone's own doing — this clone already contains SD3's commit, so the derived queue drops SD3 and adds SD9. Exempt hunk; not a finding. |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | clean (rc 0) |
| graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent (rc 0) |
| section Step 3 bats | `bats 86 84 85 80 92` | 155 tests, zero `not ok` |

The `unit` red, in full:

```
not ok 336 factory-task --prior composes the block into the brief and records prior:
# (in test file tests/unit/87-prior-attempt.bats, line 390)
#   `[ "$status" -eq 0 ]' failed
```

Reproduced outside the sandbox with the status and stderr printed
(`bats tests/unit/87-prior-attempt.bats`, one injected `echo … >&3`):

```
DBGSTATUS=4
factory_route: ladder exhausted at rung 2 for openrouter/any/any/any/any
factory_route: …/toolbox/docs/ledger/routing.toml: no default (any/any/any) row
factory-task: K1b at rung 2 is a claude rung — the launch line is in …/factory/runs/r2/K1b.escalate
launch: Workflow({ scriptPath: 'tools/factory/dark-factory.js', args: { plan: '../plan.md', prefix: 'k1', tasks: [ /* tasks.py waves --factory-args failed: run it by hand */ ], scratch: '…/runs/r2/K1b-scratch' } })
```

The diagnosis is exactly as put to me. `tests/unit/87-prior-attempt.bats:295-302`
writes a one-row routing fixture (`role/kind/size = any`, no `rung`, so rung 1
only); `:389` drives `factory-task r2 <repo> K1b --prior r1/K1`; under
`factory_rung_of_key` the key `K1b` is rung 2; `factory_route --rung 2` finds no
rung-2 row for the winning key and returns 4; `factory-task:286` escalates and
exits 4 where `:390` asserts 0. (The second `factory_route` line is the `claude`
lookup inside `factory_task_escalate` — 87's fixture has no `claude` rows, so the
`.escalate` would carry an empty `model:`/`effort:`; harmless here, but it shows
the escalation path is being taken for real.)

**The resolution (SD3b's item).** Add a rung-2 row to 87's fixture — the same
`(route, role, kind, size, class)` key, the same model, a different effort, which
is what SD1's ladder validator requires (a rung may change model or effort, never
both, and no rung may exist without its predecessor):

```
[[route]]
role = "any"
kind = "any"
size = "any"
rung = 2
model = "m/a"
effort = "high"
```

Measured in a scratch copy: `nix develop -c bats tests/unit/87-prior-attempt.bats`
→ `1..10`, ten `ok`. Nothing else in 87 moves: its only order assertion is
`grep -A2 '^route:'` → `route:`/`class:`/`prior:` (`:401-406`), and SD3 inserts
`rung:` *before* `route:`, so that triple is untouched; the test asserts no model
and no effort. The two alternatives are worse: `--rung 1` in that call would put
`rung: 1 (explicit)` in the `.result` and would test the override arm rather than
the climb SD4b's fix-round key actually takes, and nothing in SD3's rule should
move — the rule is the contract, and `K1b` *is* a rung-2 key.

## Touches and commit

**Touches — clean.** The section's list is `factory-lib.sh, factory-task,
factory-review, factory-wave, pkgs/evidence/tasks.py, tests/evidence/test_tasks.py,
tests/unit/86-rung-and-escalate.bats`. `git diff 6010cb1..HEAD --stat` names
exactly those seven plus `docs/MAP.md` (regenerated for the new
`tests/unit — 25 files` count; exempt by rule, and the lint gate's MAP diff
requires it) and `docs/OPERATIONS.md` (`1	1`, a single line, entirely inside
`<!-- tasks:begin -->…<!-- tasks:end -->`; exempt by rule). Nothing outside.

**Commit — clean but for the body.** Exactly one commit,
`139a40b4c9e0124c25d5d7ef528d69352116879d`. Subject byte-identical to the
section's `**commit subject:**` (`diff` of the two files → no output). The body
states the why (rule A1, why a `claude` rung must not run, what each script does)
in eleven lines; the two trailers follow a blank line in the WORKSPACE RULES
order — `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat
headless, factory run sd2)` then `Co-Authored-By: Claude Fable 5.1
<noreply@anthropic.com>` (`tools/factory/seat/factory-brief:79-80`). No second
commit, no board commit, the plan file untouched. The body does **not** paste
the red command and its output or the green check by name — MINOR-7.

## Findings

**MAJOR-1 — the acceptance check `unit` is red: SD3's rung rule escalates SD4b's
fix-round test key.** `tests/unit/87-prior-attempt.bats:390`, against
`tools/factory/seat/factory-task:222` and `:286`.

```
not ok 336 factory-task --prior composes the block into the brief and records prior:
# (in test file tests/unit/87-prior-attempt.bats, line 390)
#   `[ "$status" -eq 0 ]' failed
```

`nix build .#checks.x86_64-linux.unit -L --no-link` fails with this one test of
639. A red acceptance check is a MAJOR by rule. The section's Step 3 green list
(86, 84, 85, 80, 92 — 155 tests) is entirely green, so the seat could pass its
own list while the check it must run was red; it ran neither the check nor a
FACTORY-RESULT block, so nothing was disclosed. Cause and minimal fix are in
**## Checks** above; the fix is one six-line row in 87's fixture at
`tests/unit/87-prior-attempt.bats:295-302`, measured green.

Ownership: **missing-case** in the plan (SD3's section names `tests/unit/86-…`
in `touches` and lists five bats files in Step 3, none of them 87; Assumption 24
was re-measured on 2026-09-08 — after SD4b landed — and re-checked the `.result`
line order without noticing that 87's routing fixture cannot serve a rung-2 key;
the Waves note foresaw only SD2×SD3 on the shared files). Secondary
**implementer**: the section's `**acceptance:** unit` is a stated contract, and
SD2 in this very chain handled the identical kind of interaction by a
*disclosed* edit of 87 — the path was available and the seat took neither it nor
the report.

---
**MINOR-1 — `fallback:`'s stated position ("after `class:`") has no assertion.**
`tools/factory/seat/factory-task:948-951`. Outside-mutant O2 moved the
`fallback:` block above `printf 'class: %s\n'` and `86`, `80`, `85` and `87` all
stayed exactly as they were (the one pre-existing red aside). Test 5 asserts only
that `fallback: m/f` occurs somewhere in the `.result`
(`tests/unit/86-rung-and-escalate.bats:281`), unlike `rung:`, which is pinned as
an adjacency at `:173` and `:185`. The adjacency matters: with `--fallback` set,
`fallback:` lands between `class:` and `prior:`, which is where SD4b's reader
looks.

**MINOR-2 — three of the `.escalate`'s eleven stated lines have no assertion.**
`tools/factory/seat/factory-task:185-187` (`route: implement/<kind>/<size>`,
`class:`, `plan:`). Outside-mutant O3 deleted all three and
`86-rung-and-escalate.bats` test 3 stayed green — it checks `run:`, `key:`,
`role:`, `rung:`, `escalate:`, `model:`, `effort:` and the `launch:` prefix only
(`:204-211`).

**MINOR-3 — `read_escalations`' "the newest run directory's record wins" has no
assertion.** `pkgs/evidence/tasks.py:689`. Outside-mutant O4 flipped `>` to `<`
(oldest wins) and the whole evidence suite stayed green (`478 passed`); the
fixture in `tests/evidence/test_tasks.py:792-813` holds one run directory only,
so no second `.escalate` for the same key exists to discriminate.

**MINOR-4 — the review `.escalate`'s `launch:` line is untested.**
`tools/factory/seat/factory-review:40`. Outside-mutant O6 replaced
`opus-gate task/$key ~/factory/ws/$run/$key` with the literal `MUTANT` and test 6
stayed green; it asserts `role:`, `escalate:` and `model:` only
(`tests/unit/86-rung-and-escalate.bats:310-312`). The `rung:` line of that record
(`factory-review:46`) is likewise unasserted, though the interface states it.

**MINOR-5 — contract item 5's "keeps its derived state" clause is asserted on the
wrong key, through the wrong runs dir.** `tests/evidence/test_tasks.py:811`
(`assert e7["state"] == "ready"`). The `.escalate` written at `:797` is for key
`K2r`, which is not in the fixture plan at all, and the graph `g` is built by
`repo_with` (`:531-549`), which passes `tmp_path / "no-runs"` to `scan_repo` —
not the `runs` directory the escalation lives in. So no implementation that
disturbed an *escalated* task's state could be caught here. The discriminating
fixture would be an escalated key that is in the plan, with the graph scanned
against the same runs dir.

**MINOR-6 — two stated arms of interface 2 have no assertion.**
`tools/factory/seat/factory-task:249-258` (an explicit `--model`/`OPENROUTER_MODEL`
records `route: explicit` *with* `rung: N`) and `:277-281` (the exit-3 arm keeps
today's warning and the built-in default *with* `rung: N`). Both are implemented
correctly; neither appears in `tests/unit/86-rung-and-escalate.bats`. Related and
smaller: the `<TASKS>` array's success path (`factory-task:164-167`) is never
exercised — every escalation in the suite falls to the literal
`[ /* tasks.py waves --factory-args failed: run it by hand */ ]` placeholder,
which is also never asserted.

**MINOR-7 — the commit body pastes neither the red nor the green.** The house
rule is "Paste the red command and its output, then the change, then the green
check by name" (plan `## Global Constraints`, line 25) and the gate's own
convention item. `git log -1` on `139a40b` has the why and the two trailers, and
no command output of either colour. The seat's reply also ended with no
FACTORY-RESULT block (`error_class: no-result-line`, `status=unreported`), so the
driver's re-run is the only record of the run.

## Verdict

**REJECTED** on MAJOR-1: the section's own acceptance check `unit` is red.
Everything the section contracts for is implemented and every mutant it names
dies; the failure is one landed sibling test whose routing fixture SD3's rule
outgrows, and the fix is six lines in that fixture, measured green. SD3b: apply
the rung-2 row of **## Checks**, re-run `nix build
.#checks.x86_64-linux.unit -L --no-link` and paste it green, and close as many
of MINOR-1 … MINOR-6 as the round can carry — MINOR-1 (the `fallback:`/`class:`
adjacency) and MINOR-5 (a discriminating escalated key in the graph) first, since
both guard lines other tasks read.
