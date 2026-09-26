---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run sc1, task G10 — REJECTED

Workspace `/home/dalhaka/factory/ws/sc1/G10`, branch `task/G10`, head `aada4f2ead8b`,
base `0879294`. Reviewed from a throwaway clone; the workspace was not touched
(its HEAD and working tree are unchanged).

## Summary

The code is right and every acceptance command is green: per-part caps land as
specified, the wording is `chars` everywhere, the runbook path is fixed, the G6
rules are all intact, and the live run finally ends with the pointer line. But
the central promise of the section — *the brief and the pointer always print* —
is not pinned by any test. Three mutations survive, and each one, applied alone,
reproduces exactly the defect G10 exists to fix: printing the pointer before the
brief (the gate's own named mutation M3), deleting the brief cap, and reverting
`SESSION_START_CAP` to 6000. The suite stays 9/9 green through all three. One
fix-round test kills all three.

## Checks

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass |
| — new bats tests ran in the sandbox | yes: build log `ok 139`–`ok 142`, all four new test names |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass (84 formatted, 0 changed; 33 already formatted) |
| `nix develop -c githooks/pre-commit` | pass, exit 0 |
| `nix develop -c shellcheck tools/session-start.sh` | exit 0, no output |
| `nix develop -c bats tests/unit/90-session-start.bats` | 9/9 ok |

Commit hygiene: exactly one commit on base `0879294`; `git show --stat HEAD` is
exactly `docs/runbooks/session.md`, `tests/unit/90-session-start.bats`,
`tools/session-start.sh` — no fourth file. Subject byte-identical to the
section's `commit subject` (verified by `diff` against the section's text).
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present, plus a
`Generated-By:` line (allowed). `tools/session-start.sh` still mode `100755`.

Behaviour against the section's Interfaces:

- caps `SESSION_START_CAP_BOARD` 3000, `SESSION_START_CAP_BUNDLE` 2500,
  `SESSION_START_CAP_BRIEF` 1500, total `SESSION_START_CAP` 8000 — all present
  with those defaults, the total applied to the assembled `out` after the parts;
- the truncation line is exactly `…<part> truncated at N chars
  (SESSION_START_CAP_<PART>)`, `<part>` lowercased from `<PART>` by `tr`;
- the word is `chars` in all four truncation lines; no `bytes` remains;
- worst case measured: with all three parts over their caps the assembled output
  is **7222 chars**, 778 short of the 8000 total ceiling — so with defaults the
  total cap never fires and the pointer is genuinely last. The arithmetic holds;
  it is only untested (Finding 3);
- runbook: `docs/superpowers/reviews` → `docs/reviews` (no occurrence of the old
  path remains in the file), and a new "Budgets (per-part caps)" section
  documents all four caps with their defaults and the `chars` wording;
- G6 rules unchanged: order board → bundle → brief → pointer, every fallible
  command still carries a `||` guard, `FACTORY_RUN` early exit, linked-worktree
  exit, `exit 0` always, `set -u` only (no `-e`), and the script never invokes
  `nix`. Verified by mutation (table below): all six G6 mutants still die.

Hard-rules scan of the diff and of the whole script: no `sudo`,
`nixos-rebuild`, `systemctl`, mount or teardown, and no `2>/dev/null` (the
script uses `2>&1` throughout). Nothing was written outside the clone, the
scratch nix cache and this file.

## Red before green

HEAD~1's `tools/session-start.sh` with HEAD's bats file:

```
1..9
ok 1 prints START HERE, bundle, brief and the runbook pointer, in order
ok 2 without evidence on PATH the board still prints and each missing part says unavailable
ok 3 silent when FACTORY_RUN is set
ok 4 silent in a linked worktree
ok 5 output over the cap ends with a truncation line
not ok 6 a bundle over its cap (2500) is cut and the brief and pointer still print
#   `[[ "$output" == *"…bundle truncated at 2500 chars (SESSION_START_CAP_BUNDLE)"* ]]' failed
not ok 7 a board over its cap (3000) is cut and the bundle still follows
#   `[[ "$output" == *"…board truncated at 3000 chars (SESSION_START_CAP_BOARD)"* ]]' failed
not ok 8 the total cap applies after the parts and ends the output
#   `[ "$last" = "…truncated at 1000 chars (SESSION_START_CAP)" ]' failed
ok 9 a failing evidence bundle and a failing tasks each say unavailable and the board still prints
```

Three of the four new tests are genuinely red-first. Test 9 is green at HEAD~1
and at HEAD — the implementer says so in FACTORY-NOTES, and that is honest: it is
a **pin** of two pre-existing G6 guards, not a behaviour change, so the proof is
mutation, not redness. I ran that proof: M5 and M7 below both kill it. The pin is
real. Restored; `git status --porcelain` clean.

One caveat on test 6. Under the old script the *reason* it fails is only the
missing `…bundle truncated` line. I ran the same fixture against HEAD~1 directly:
the brief **and** the pointer both still printed (total 4,100 chars, under the old
6000 cap, because the fixture's board is the tiny four-line setup board). So the
second half of test 6's name — "the brief and pointer still print" — asserts
nothing that the old code failed. See Finding 1.

## Mutation table

Seventeen mutations, each applied to `tools/session-start.sh` by an exact-text
Python replacement that aborts if its anchor is absent (and the harness refuses a
no-op edit, so a silent non-match cannot be reported as a survivor), bats run,
then reverted. `git status --porcelain` clean at the end.

The six the gate demanded are M1–M6.

| # | mutation | outcome | killed by |
|---|---|---|---|
| M1 | remove the board cap (`cap_part BOARD` → plain `printf`) | **killed** | T7 |
| M2 | remove the bundle cap | **killed** | T6 |
| M3 | **drop the pointer-last guarantee (pointer printed before the brief)** | **SURVIVED** | — (Finding 2) |
| M4 | `chars` → `bytes` in every message | **killed** | T6, T7, T8 |
| M5 | remove the `\|\| echo "unavailable: evidence bundle failed"` guard | **killed** | T9 |
| M6 | remove the total cap (`printf '%s\n' "$out"` unconditionally) | **killed** | T5, T8 |
| M7 | remove the `\|\| echo "unavailable: evidence tasks failed"` guard | **killed** | T9 |
| M8 | **remove the brief cap** | **SURVIVED** | — (Finding 3) |
| M9 | caps raised 10× (`3000`→`30000`, `2500`→`25000`) | **killed** | T6, T7 |
| M10 | **total-cap default `8000` → `6000` (the pre-G10 value)** | **SURVIVED** | — (Finding 4) |
| M11 | final `exit 0` → `exit 3` | **killed** | T1, T2, T5–T9 |
| G6-a | remove the `FACTORY_RUN` early exit | **killed** | T3 |
| G6-b | remove the linked-worktree check | **killed** | T4 |
| G6-c | awk → `cat` (whole board file, log included) | **killed** | T1 |
| G6-d | drop the `unavailable: evidence not on PATH` fallback | **killed** | T2 |
| G6-e | reorder: brief printed before bundle | **killed** | T1 |
| G6-f | drop both truncation branches | **killed** | T5–T8 |

All six G6 mutants still die. Of the six this gate named, **five die and M3
survives.**

M3 is not an equivalent mutant. Diff applied (swap the two blocks), and the
resulting output ends:

```
…bundle truncated at 2500 chars (SESSION_START_CAP_BUNDLE)

Where everything is: docs/runbooks/session.md

# Task brief
| repo |
```

The pointer is no longer last, and all nine tests pass.

M8 and M10 were verified the same way, on a fixture with a live-sized board, a
6,000-char bundle and a 6,000-char brief:

| script | output | last line |
|---|---|---|
| HEAD | 7222 chars | `Where everything is: docs/runbooks/session.md` |
| M8 (no brief cap) | 8041 chars | `…truncated at 8000 chars (SESSION_START_CAP)` — pointer gone |
| M10 (total 6000) | 6039 chars | `…truncated at 6000 chars (SESSION_START_CAP)` — pointer gone |

Both mutants reproduce the exact G6 defect this task exists to remove, and the
suite stays green.

## Real run

From the clone, read-only, `bash tools/session-start.sh /home/dalhaka/nixos-agent-env`:

- exit 0, **5912 chars / 5986 bytes**.
- `evidence` is on PATH (`/run/current-system/sw/bin/evidence`, gen 42) and
  `bundle --markdown` works; `python3` is **not** on the bare host PATH.
- Two truncation lines fire, at output lines 37 and 85:
  `…board truncated at 3000 chars (SESSION_START_CAP_BOARD)` and
  `…bundle truncated at 2500 chars (SESSION_START_CAP_BUNDLE)`.
- The total cap does not fire. The last line is the pointer.

`tail -12`:

```
- d5-activity-export (owner operator, opened 2026-09-04, review by 2026-09-12): ~/strategy/ledger/openrouter-activity.csv exists and rollup --activity parses it
- s12-commit-metadata-decision (owner operator, opened 2026-09-04, review by 2026-09-12): a decision file on mixed trailers and non-check subjects (nixos-skill round 2 report)
- xhigh-restore-or-keep-medium (owner operator, opened 2026-09-04, review by 2026-09-12): the seat's saved level is set on purpose and the backup file is deleted
- aimdo-native-load-unmeasured (owner orchestrator, opened 2026-09-05, review by 2026-09-19): the media acceptance drill on core imports comfy_aimdo's native module and repor
…bundle truncated at 2500 chars (SESSION_START_CAP_BUNDLE)

usage: evidence [-h] [--store STORE]
                {record,record-check,latest-check,bundle} ...
evidence: error: argument cmd: invalid choice: 'tasks' (choose from record, record-check, latest-check, bundle)
unavailable: evidence tasks failed

Where everything is: docs/runbooks/session.md
```

This is the intended shape: G5b has not landed, so the live `evidence` has no
`tasks` subcommand; the argparse usage error reaches stdout through `2>&1` and
the `unavailable: evidence tasks failed` guard fires — the guard M7 proves is
tested. The pointer prints last, which it never did under G6. The behavioural
goal of the task is achieved; only its test coverage is short.

Down from G6's 6115 bytes to 5986 bytes, with the brief slot and the pointer now
present instead of a mid-bundle cut.

## Findings

1. **MAJOR — no test asserts the pointer prints last.** The section's Interfaces
   say "the pointer line always prints last". Nothing checks it. T1 only asserts
   the pointer string appears somewhere; T6 the same; T8 checks the last line only
   under an explicit `SESSION_START_CAP=1000`, which is the *total-cap* path, not
   the default path. Consequence: M3 survives.

2. **MAJOR (same root) — no test stresses all three parts at once.** T6 makes the
   bundle big with a tiny board; T7 makes the board big with a tiny bundle; the
   brief is small in every test. So no fixture ever approaches the 8000 total, and
   the whole point of the budget — that the sum of the caps *fits* — is unmeasured.
   This is why T6's "the brief and pointer still print" half is vacuous (it passes
   against HEAD~1 too), and why M8 and M10 survive.

3. **MAJOR — `SESSION_START_CAP_BRIEF` has zero coverage.** It is one of the three
   caps the section declares, and it is load-bearing: with it removed a 5,000-char
   brief pushes the output to 8041 chars and the total cap eats the pointer. M8
   survives.

4. **MAJOR — the `8000` default is unpinned, and reverting it restores the bug.**
   M10 (`8000` → `6000`, the pre-G10 value) leaves all nine tests green while the
   pointer is again lost on a realistic three-part payload. A regression that undid
   this whole task would ship silently.

   All four findings are one fix. **One test kills M3, M8 and M10 together:** with
   the default caps and a fixture whose board, bundle *and* brief each exceed their
   cap, assert `[ "$(printf '%s\n' "$output" | tail -1)" = "Where everything is:
   docs/runbooks/session.md" ]` and that `# Task brief` appears before it. (A
   second line asserting the total is under 8000 would document the headroom;
   measured today it is 7222, i.e. 778 spare.)

5. **MINOR — the no-evidence branch emits a blank brief.** `brief=""` in the final
   `else`, so `cap_part BRIEF ""` prints one empty line where the other branches
   print an `unavailable:` sentence. Cosmetic; the board and the
   `unavailable: evidence not on PATH` line still print (T2, G6-d).

6. **MINOR — `tests/unit/90-session-start.bats` has no trailing newline.** The
   file ends `]]\n}` with no final newline. treefmt does not cover `.bats`, so no
   gate catches it. One byte.

7. **Not a defect — the pins are real.** The two guard tests the section asked for
   are green at HEAD~1, which the implementer disclosed rather than dressed up as
   red. Judged on the correct standard (mutation, not redness) they hold: M5 and M7
   both die, closing two of the three untested guards Finding 4 of the G6 review
   named. The third (`unavailable: docs/OPERATIONS.md not readable`) is still
   untested; not asked for here, worth folding into the fix round.

No other MAJORs. The implementation itself needs no change — findings 1–4 are all
satisfied by adding one bats test (and, if the fix round wants it, the two
one-byte tidies in 5 and 6).

## Deviations

- The section's Step 1 predicted the failing bundle test would show "brief absent"
  under HEAD~1. It does not, because the fixture keeps the board small; the test
  is still red-first on its truncation-line assertion. Recorded, not held against
  the implementer — but it is the same blind spot as Findings 1–4.
- Everything else matches the section: three files, the four caps and their
  defaults, the message format, the runbook path fix and the four documented caps,
  and no change to any G6 rule.
