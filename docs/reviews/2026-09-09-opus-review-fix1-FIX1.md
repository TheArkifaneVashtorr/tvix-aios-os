---
plan_defect: none
mutants_total: 9
mutants_killed: 7
mutants_outside_named: 4
model: opus
---
# Opus gate — seat run fix1, task FIX1 — APPROVED

## Summary

The contract is met. `nixosModules/seatLane.nix:109` puts `seatSubmit` on
`environment.systemPackages` under `config = lib.mkIf cfg.enable` (`:73`),
copying `modelLane.nix:194-198`; `flake.nix:1769-1778` asserts a `-seat-submit`
path in `config.environment.systemPackages` with the message the section names;
`tools/factory/seat/factory-task:361-370` resolves `$SEAT_SUBMIT` then PATH in
exactly the shape of `seat-drive.sh:111-114` and with **no** `nix run` arm, and
refuses (exit 2, one stderr line naming all four tokens) before any harness
launches when neither resolves and `FACTORY_SEAT_UNIT` is not `0`; the direct
arm is now reachable only under `FACTORY_SEAT_UNIT=0` and writes
`FACTORY_SEAT_UNIT=0: direct arm, the operator's key outside the broker` into
the run log (`:457`); the codex arm at `:384` is byte-unchanged; README `:95`,
`:709`, `:718` are corrected.

Red reproduced twice against the base's implementation with the branch's tests:
the `seat-eval` assertion throws its message with `seatLane.nix` at base, and
bats A/B/D all fail with the base `factory-task`. All five named mutants die on
the test the section names. `seat-eval`, `unit` (680) and `lint` are green by
`--rebuild` in a fresh clone; `repomap.py write` leaves `docs/MAP.md` clean and
`tasks.py check` is silent. One commit, subject byte-identical (md5
`77bb20a6…` both sides), both trailers after a blank line, the plan file
untouched, no board commit.

The Fact 5 disclosure is complete and minimal: reverting only the three test
files to base while keeping the new implementation fails exactly the ten
disclosed tests and no others; every modification is a single
`FACTORY_SEAT_UNIT=0` added to a run line, with no assertion lost.

Seven MINORs, none gating. Operational consequence worth carrying to the board:
once this lands, on the host **before switch #25** `seat-submit` is not on PATH,
so every `factory-task` launch line that sets neither `SEAT_SUBMIT` nor
`FACTORY_SEAT_UNIT=0` will refuse with exit 2. That is the intended semantics
(the section's "After it lands" note), but it changes the launch recipe today.

## Contract items

**(a) The module exposes the CLI to the host.** MET.
`nixosModules/seatLane.nix:109` — `environment.systemPackages = [ seatSubmit ];`,
inside `config = lib.mkIf cfg.enable {` (`:73`), beside the unit, with
`seatSubmit` from `:22`. The sibling pattern it copies is
`nixosModules/modelLane.nix:194-198`
(`environment.systemPackages = [ laneSubmit laneWait pkgs.jq ];`).

**(b) `seat-eval` asserts it, with the section's message.** MET as behaviour;
one literal deviation (MINOR-1). `flake.nix:1769-1778`:

```
          assert nixpkgs.lib.assertMsg
            (nixpkgs.lib.any (
              p: nixpkgs.lib.hasSuffix "-seat-submit" (toString p)
            ) c.environment.systemPackages)
            "seat-eval: environment.systemPackages must carry seat-submit (the host's factory-task cannot reach the seat@ route without it)";
```

The message is the section's, byte for byte. Fact 3 said "Extend that check; do
not add a second one"; the seat added a second `assert` immediately after
`flake.nix:1763-1766`. The two instructions conflict — the existing assertion
carries its own message (`seat-eval: seat@ path must carry
/run/current-system/sw and seat-submit`) and cannot also carry the one the
section names — so a separate assert is the only way to satisfy the named
message. Recorded as MINOR-1, not a MAJOR, because the discriminating power is
identical (proved by the mutant below) and the deviation is not disclosed.

**(c) `factory-task` resolves and refuses.** MET, item by item.

- Resolution shape identical to `seat-drive.sh:111-114`, same array name,
  same order, no `nix run` arm — `grep -n 'nix run' tools/factory/seat/factory-task`
  returns only the comment at `:359`:
  ```
  361: if [ "$seat_arm" != codex ]; then
  362:   seat_cmd=()
  363:   if [ -n "${SEAT_SUBMIT:-}" ]; then
  364:     seat_cmd=("$SEAT_SUBMIT")
  365:   elif command -v seat-submit >/dev/null 2>&1; then
  366:     seat_cmd=(seat-submit)
  367:   elif [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then
  368:     printf '%s\n' "factory-task: refusing -- no seat-submit on PATH and SEAT_SUBMIT is unset; set FACTORY_SEAT_UNIT=0 for the direct arm (docs/brief.md invariants 2 and 3)" >&2
  369:     exit 2
  ```
- The refusal line names `seat-submit`, `SEAT_SUBMIT`, `FACTORY_SEAT_UNIT=0`
  and `docs/brief.md invariants 2 and 3`. All four present; only the first and
  third are asserted by a test (MINOR-3).
- Exit 2, one line, on stderr, nothing launched: bats A asserts
  `[ ! -e "$dsh_called" ]` (`80-seat-driver.bats:1440`) and
  `[ ! -e "$root/runs/r1/K1.result" ]` (`:1441`). Placement is after the
  workspace clone (MINOR-2), but no harness runs.
- The direct arm runs only under the seam: `factory-task:400` is
  `elif [ "${#seat_cmd[@]}" -gt 0 ] && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]`.
  The `else` at `:452` is reachable only when `seat_cmd` is empty (which by
  `:367` implies the seam is `0`) or when the seam is `0`. So the log line's
  claim is unconditionally true.
- The log substring is exact, at `:457`:
  `printf '%s\n' "FACTORY_SEAT_UNIT=0: direct arm, the operator's key outside the broker" >>"$log"`.
  Note the section's wording "its launch line in the log" cannot be met
  literally: `factory_log` writes to **stderr only**
  (`factory-lib.sh:29-32`), so the `launching dsh-openrouter …` line never
  enters `$log`. A separate appended line is the only way to put the substring
  in the log. `: >"$log"` (`:346`) precedes it and the arms use `tee -a`
  (`:395`, `:427`, `:461`), so the line survives. Not a finding.
- The codex arm is untouched: the diff has no hunk in `:384-399`; the preflight
  is guarded by `[ "$seat_arm" != codex ]`.

**(d) README `:95`, `:709`, `:718`.** MET. `:94-99` now documents the
resolution order and the refusal; `:710-711` and `:722-726` document the log
substring, the refusal and that `SEAT_SUBMIT` outranks PATH. One residual
staleness at `:100` (MINOR-6).

**Interfaces / error contracts.** `factory-task` gains exactly one refusal path
(exercised by bats A), honours `SEAT_SUBMIT` before PATH (bats D), the direct
arm's log gains one substring (bats B), `seat-eval` gains one assertion (its
mutant). `seat-submit`, `seat-run`, `seat-drive.sh`, the unit and the
`FACTORY-RESULT` contract are untouched — no diff hunk in any of them. The
existing unit-arm regression guard (bats C, the test at `80-seat-driver.bats`
that puts a fake `seat-submit` on PATH) is unmodified and passes (test 27/28 in
the file's numbering).

## Red before green

**(a) `seat-eval`.** `git checkout a9017da -- nixosModules/seatLane.nix` (the
branch's `flake.nix` kept), then
`nix build .#checks.x86_64-linux.seat-eval -L --no-link --rebuild`:

```
       … in the condition of the assert statement
         at …/flake.nix:1771:11:
       error: seat-eval: environment.systemPackages must carry seat-submit (the host's factory-task cannot reach the seat@ route without it)
```

Restored; the check is green (below). The assertion is therefore discriminating
against `seatLane.nix`'s line and not satisfied by some other module's package
set.

**(b) bats A (and B and D).**
`git checkout a9017da -- tools/factory/seat/factory-task`, then
`nix develop -c bats tests/unit/80-seat-driver.bats`:

```
not ok 29 factory-task refuses (exit 2) instead of falling into the direct arm when neither seat-submit nor SEAT_SUBMIT resolves
# (in test file tests/unit/80-seat-driver.bats, line 1437)
#   `[ "$status" -eq 2 ]' failed
not ok 30 factory-task still opts out through FACTORY_SEAT_UNIT=0 and records the direct arm in the log
# (in test file tests/unit/80-seat-driver.bats, line 1495)
#   `[[ "$output" == *"FACTORY_SEAT_UNIT=0: direct arm"* ]]' failed
not ok 31 factory-task honours SEAT_SUBMIT over PATH: the unit arm runs through the override
# (in test file tests/unit/80-seat-driver.bats, line 1559)
#   `[ ! -e "$dsh_called" ]' failed
```

Restored: `1..84`, zero `not ok`. All three new tests can fail; the section only
required A's red, and B's and D's are supplied here.

## Mutants

Named by the section — 5 applied, 5 killed.

| # | mutant | killing test | failing line |
|---|---|---|---|
| 1 | delete `environment.systemPackages` from `seatLane.nix:109` | `seat-eval` | `error: seat-eval: environment.systemPackages must carry seat-submit (the host's factory-task cannot reach the seat@ route without it)` |
| 2 | A's fall-through: delete `factory-task:367-369` (the refusal branch) | bats A | `not ok 29 … # (line 1437) \`[ "$status" -eq 2 ]' failed` |
| 3 | B(i): `factory-task:367` `elif [ … != "0" ]; then` → `else` (refuse regardless of the seam) | bats B | `not ok 30 … # (line 1492) \`[ "$status" -eq 0 ]' failed` |
| 4 | B(ii): delete `factory-task:457` (the log substring) | bats B | `not ok 30 … # (line 1495) \`[[ "$output" == *"FACTORY_SEAT_UNIT=0: direct arm"* ]]' failed` |
| 5 | D: delete `factory-task:363-364`, resolve PATH only | bats D | `not ok 31 … # (line 1558) \`[ "$status" -eq 0 ]' failed` |

Mutant 3 additionally fells 14 other tests in `80-seat-driver.bats` — the
pre-existing direct-arm tests that already carried `FACTORY_SEAT_UNIT=0`. That
is the evidence that the seam-only tests were correctly left alone.

Outside the named set — 4 applied, 2 killed, 2 survived.

| # | mutant | outcome |
|---|---|---|
| E5 | `factory-task:369` `exit 2` → `exit 1` | KILLED — bats A, `\`[ "$status" -eq 2 ]' failed` |
| E6 | `factory-task:419` `"${seat_cmd[@]}" headless` → `seat-submit headless` (resolve but launch the PATH name) | KILLED — bats D, `\`[ "$status" -eq 0 ]' failed` |
| E2 | `factory-task:361` `if [ "$seat_arm" != codex ]` → `if true` (apply the preflight to the codex arm too) | **SURVIVED** — MINOR-4 |
| E4b | `factory-task:368` message reduced to `factory-task: refusing -- no seat-submit; set FACTORY_SEAT_UNIT=0` (drops `SEAT_SUBMIT` and `docs/brief.md invariants 2 and 3`) | **SURVIVED** — MINOR-3 |

Neither survivor is a violation by the code: the code satisfies the contract in
both cases; only the assertions are narrower than the contract's words.

`mutants_total: 9`, `mutants_killed: 7`, `mutants_outside_named: 4`.

## Checks

All in a fresh clone of `task/FIX1` at `05a9434`, `--rebuild`.

| check | command | result |
|---|---|---|
| seat-eval | `nix build .#checks.x86_64-linux.seat-eval -L --no-link --rebuild` | exit 0 (`checking outputs of '…-seat-eval-ok.drv'`) |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | exit 0, `ok 680 now-paragraph accepts the real board's Now paragraph` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | exit 0, `Found 0 warnings and 0 errors.` |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 — see below (not a defect of this change) |
| repomap | `python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | clean |
| tasks | `python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |
| ruff | — | N/A, no python in the diff |

`githooks/pre-commit` exits 1 on its last step only:

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
```

The regeneration is a one-line diff removing `FIX1` from the derived queue —
i.e. the board on `main` still lists FIX1 as queued while this clone's HEAD
carries the landed commit. The block is idempotent (regenerated twice, byte
identical), every earlier step of the hook is green, and the board is the
orchestrator's to commit, never the seat's. In the seat's own workspace the hook
would have run before the commit existed and seen a current block. Recorded as
MINOR-7 only because the commit body pastes a green last line I could not
reproduce.

Observation, unrelated to FIX1: `80-seat-driver.bats` test 44
(`factory-review's trap-before-marker order survives a kill between the two`)
failed once in ~10 full-file runs and passed 3/3 when run alone. It exercises
`factory-review`, which this task does not touch — a pre-existing timing flake,
worth a chip.

## Touches and commit

Declared: `nixosModules/seatLane.nix, flake.nix, tools/factory/seat/factory-task,
tools/factory/seat/README.md, tests/unit/80-seat-driver.bats, docs/MAP.md`.

Diff (`git diff a9017da..HEAD --stat`), 7 files:

```
 flake.nix                            |   9 ++
 nixosModules/seatLane.nix            |   8 ++
 tests/unit/80-seat-driver.bats       | 192 +++++++++++++++++++++++++++++++++--
 tests/unit/85-task-class.bats        |   2 +-
 tests/unit/86-rung-and-escalate.bats |  12 +--
 tools/factory/seat/README.md         |  15 ++-
 tools/factory/seat/factory-task      |  45 ++++++--
```

Five inside `touches`; `docs/MAP.md` correctly needed no change. Two outside
(`85-task-class.bats`, `86-rung-and-escalate.bats`), both disclosed as a
Deviation line in the commit body under Fact 5's contingency — MINOR-5, recorded
per the rule.

**Fact 5 verification.** With the new `factory-task` kept and only the three
test files reverted to `a9017da`, exactly ten tests fail:

```
not ok 16 factory-task resolves model and effort through routing.toml and records the route
not ok 79 factory-task writes error_class and plan, and ingests the result once the file exists
not ok 80 factory-task records error_class=no-result-line for a near-miss FACTORY-RESULT
not ok 81 factory-task keeps its exit code when the evidence recorder fails
not ok 86 factory-task passes --class into factory_route and records class: in the .result
not ok 88 factory-task climbs the rung from the key and records rung: after effort:
not ok 90 factory-task --rung overrides the key (explicit) and rejects a bad value
not ok 91 factory-task --fallback chooses the sideways model and records fallback:
not ok 95 factory-task --model keeps route: explicit and still records rung:
not ok 96 factory-task exit-3 arm: an unroutable table warns, uses the built-in default, rung:
```

That set is exactly the ten the commit body names — the disclosure is complete
(no test needed the seam and missed it, since the unit check is green) and
minimal (no test gained the seam without needing it). Also confirmed: the devShell
PATH carries no `seat-submit` (`command -v seat-submit` → nothing), so those ten
really were running the direct arm. Every modification is one
`FACTORY_SEAT_UNIT=0` added to a run line; no assertion is removed or weakened
anywhere in the diff.

**Commit.** Exactly one (`git rev-list --count a9017da..HEAD` → 1). Subject
byte-identical to the section's (md5 of the subject and of the section's string
both `77bb20a6571bff7f9fe8af1ae602ef00`). Body states the why, pastes the
`seat-eval` red and bats A's red, the four greens, the five mutants and the Fact
5 disclosure. Trailers `Generated-By:` and `Co-Authored-By: Claude Fable 5.1`
follow a blank line. No board commit; `docs/superpowers/plans/2026-09-09-bugs.md`
untouched.

## Findings

**MINOR-1 — a second `seat-eval` assertion where Fact 3 said to extend the
existing one, undisclosed.** `flake.nix:1769-1778`. Fact 3: "Extend that check;
do not add a second one." The seat added a second `assert` after
`flake.nix:1763-1766`. The section elsewhere names a message the existing
assertion cannot carry (`seat-eval: environment.systemPackages must carry
seat-submit …` vs the existing `seat-eval: seat@ path must carry
/run/current-system/sw and seat-submit`), so a separate assert is the only way
to honour the named message — the plan text is self-contradictory here, not the
code. Not gating: the mutant proves the assertion is discriminating. The
deviation is nowhere in the commit body.

**MINOR-2 — the refusal sits after the workspace clone, and the commit body does
not say so.** `tools/factory/seat/factory-task:361`, after `factory-ws` at
`:324`, `mkdir -p "$runs_dir"` at `:313`, the pid file at `:320`, the seeded
`DSH_HOME` at `:335`, the brief at `:344` and `: >"$log"` at `:346`. The
section's own words ("before any harness launches", "nothing is launched") are
met, and bats A asserts both the absent harness marker and the absent `.result`.
But the refusal leaves a run dir, a log, a brief-less marker temp file and a
seeded `dsh-home` behind, unlike the neighbouring `FACTORY_PLAN` refusal which
exits "before creating a run dir" (`80-seat-driver.bats`, test 50). The section
left the placement to the seat on condition the commit body state it; the body
does not.

**MINOR-3 — two of the four tokens the refusal line must name are untested.**
`tools/factory/seat/factory-task:368` names `SEAT_SUBMIT` and `docs/brief.md
invariants 2 and 3` as the contract requires, but bats A
(`80-seat-driver.bats:1438-1439`) greps only for `seat-submit` and
`FACTORY_SEAT_UNIT=0`; `[[ … == *"seat-submit"* ]]` is case-sensitive and does
not cover `SEAT_SUBMIT`. Mutant E4b — message reduced to `factory-task: refusing
-- no seat-submit; set FACTORY_SEAT_UNIT=0` — survives the whole file. The
section's Tests block specified exactly these two greps, so this is the plan's
narrowness, not the seat's.

**MINOR-4 — the codex arm's exemption from the preflight is untested.**
`tools/factory/seat/factory-task:361`. Mutant E2 (`if true` in place of
`[ "$seat_arm" != codex ]`) survives `tests/unit/95-codex-arm.bats` in full,
because that file's `run_codex_task` helper sets `FACTORY_SEAT_UNIT=0` on every
launch (`95-codex-arm.bats:239`). The guard is correct and defensive; nothing
would catch its removal, which under a codex launch with the seam unset would
refuse a run that must proceed.

**MINOR-5 — two files outside `touches`, disclosed.**
`tests/unit/85-task-class.bats:182` and `tests/unit/86-rung-and-escalate.bats`
(6 run lines). Both are named in a Deviation line in the commit body under Fact
5's contingency, and both are proved necessary above. Recorded per the rule.

**MINOR-6 — one residual either/or sentence in the README.**
`tools/factory/seat/README.md:100`: "When `FACTORY_SEAT` is unset or empty the
seat is today's (seat-submit or `dsh-openrouter`)". After this change the two
are no longer alternatives resolved by a silent predicate — `dsh-openrouter` is
reachable only under `FACTORY_SEAT_UNIT=0`. The two sentences above it say so,
so the passage is not wrong, only stale in the exact shape the fix removed.

**MINOR-7 — a green `pre-commit` last line I could not reproduce.** The commit
body pastes `nix develop -c githooks/pre-commit → render.test.mjs: all
assertions passed`. In a fresh clone of the branch the hook exits 1 on `tasks:
docs/OPERATIONS.md queue block was stale and has been regenerated`. The cause is
entirely the derived board (FIX1 is landed in this tree but still queued in the
committed block) and the seat must not commit the board, so this is not a defect
of the change; every other step of the hook is green. Recorded because the
pasted line is not what the hook prints once the commit exists.

## Verdict

**APPROVED.** No MAJORs. The contract is met item by item, both reds reproduce
against the base's implementation with the branch's tests, all five named
mutants die on the tests the section names, and `seat-eval`, `unit` (680) and
`lint` are green by `--rebuild` in a fresh clone. Seven MINORs, none owed before
landing; MINOR-2 (placement) and MINOR-1 (the second assertion) are the two the
board should carry forward, and the launch-recipe consequence in the Summary is
the operational note for switch #25.
