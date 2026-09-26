---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run sc3, task G10b — APPROVED

Workspace `/home/dalhaka/factory/ws/sc3/G10b`, branch `task/G10b`, head
`efb48aa63a96`, base `2867b983`. Reviewed from a throwaway clone; neither
workspace was touched (`ws/sc3/G10b` HEAD `efb48aa`, working tree carries only
its own pre-existing untracked `scratch/commit-msg.txt` from the run;
`ws/sc1/G10` HEAD `aada4f2`, tree clean).

## Summary

The fix round does exactly what it was asked to do and nothing else. Against
G10's tip the script and the runbook are **byte-identical** (`git diff` empty
for both); the only change is +29/−1 lines in `tests/unit/90-session-start.bats`
— one new test plus the missing trailing newline. That single test kills all
three survivors: M3 (pointer printed before the brief), M8 (brief cap deleted)
and M10 (total cap reverted to 6000), each failing on the same assertion, the
`tail -n1` pointer-last check at bats line 138. Nothing regressed: fifteen G6/G10
mutants that died before still die, the suite is 10/10, `unit` is 143/143 green
with the new test named in the builder log, and the live run still ends with the
pointer at 5,912 chars. Four extra mutants of my own also die. One carried minor
remains (`brief=""` blank line, explicitly optional in the section) and one
pre-existing untested guard (`unavailable: docs/OPERATIONS.md not readable`),
neither in scope here.

## Checks

| command | result |
|---|---|
| `nix develop -c bats tests/unit/90-session-start.bats` | 10/10 ok |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | pass |
| — new test in the sandbox log | yes: `1..143`, `ok 143 with defaults the brief and the pointer print last even when all three parts overflow` (134–143 are the whole session-start file, all ok) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass (84 formatted, 0 changed; 33 already formatted) |
| `nix develop -c githooks/pre-commit` | pass, exit 0 |
| `nix develop -c shellcheck tools/session-start.sh` | exit 0, no output |

Commit hygiene:

- exactly one commit on base `2867b983` (`git rev-parse HEAD^` == base);
- `git show --stat HEAD` = `docs/runbooks/session.md`,
  `tests/unit/90-session-start.bats`, `tools/session-start.sh` (128 insertions,
  15 deletions). The docs file is present because the fix round starts from a
  fresh `main` workspace and cherry-picks G10 uncommitted — see Deviations;
- subject byte-identical to G10's commit `aada4f2` **and** to the plan section's
  `commit subject` (`cmp` on both, exit 0);
- `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present, plus a
  `Generated-By:` line (allowed);
- `tools/session-start.sh` still mode `100755`;
- `tests/unit/90-session-start.bats` now ends `]\n}\n` — trailing newline fixed
  (`od -c` tail: `t   "       ]  \n   }  \n`), which is the −1/+1 in the diff.

Diff vs G10's tip `aada4f2` (fetched read-only from `/home/dalhaka/factory/ws/sc1/G10`):

| file | diff vs G10 |
|---|---|
| `tools/session-start.sh` | **empty** |
| `docs/runbooks/session.md` | **empty** |
| `tests/unit/90-session-start.bats` | 29 insertions, 1 deletion (the new test + the newline) |

So this is a genuinely test-only round. The optional `brief=""` script tidy was
not taken; that is allowed by the section ("only if … optional, one line").

Hard-rules scan of the diff: no `sudo`, `nixos-rebuild`, `systemctl`, mount or
teardown, no `2>/dev/null`. Nothing was written outside the clone, the scratch
nix cache and this file.

## Red before green

The round's proof is mutation, and the honest form of it is *the same script,
two bats files*. I checked out G10's bats file (the pre-fix-round one) over
HEAD's tree, left HEAD's script in place, and applied the three mutants; then
did it again with HEAD's bats file. Same script, same mutations, both directions:

```
### G10's bats file (pre-fix-round)
   baseline (unmutated script): 1..9, failures=0
   M3 pointer before brief        *** SURVIVED ***  (1..9; killers: -)
   M8 brief cap deleted           *** SURVIVED ***  (1..9; killers: -)
   M10 total cap 8000 -> 6000     *** SURVIVED ***  (1..9; killers: -)
### HEAD's bats file (fix round)
   baseline (unmutated script): 1..10, failures=0
   M3 pointer before brief        KILLED  (1..10; killers: T10)
   M8 brief cap deleted           KILLED  (1..10; killers: T10)
   M10 total cap 8000 -> 6000     KILLED  (1..10; killers: T10)
```

That is the round's red: the three defects the G10 gate named ship silently
under the old suite and are caught by the new one. Script and bats file restored
afterwards; `git status --porcelain` empty.

All three die on the same line, and it is the right line:

```
not ok 10 with defaults the brief and the pointer print last even when all three parts overflow
# (in test file tests/unit/90-session-start.bats, line 138)
#   `[ "$(printf '%s\n' "$output" | tail -n1)" = "Where everything is: docs/runbooks/session.md" ]' failed
```

The fixture is the section's: a 400-line board, a 4,000-char bundle, a 3,000-char
brief, default caps. I replayed it by hand outside bats — output **7,222 chars,
778 short of the 8,000 ceiling**, last line the pointer, and all three
per-part truncation lines present. That is the same arithmetic the G10 gate
computed and could not test; it is now pinned by `[ "${#output}" -le 8000 ]`
plus the three `…<part> truncated at N chars` assertions.

## Mutation table

Twenty-two mutations, each an exact-text replacement that aborts if its anchor
is absent and refuses a no-op, bats run, then reverted; `git status --porcelain`
empty after every batch. Mutation names follow the G10 review's numbering.

The three the gate demanded:

| # | mutation | outcome | killed by |
|---|---|---|---|
| M3 | pointer echo moved above the brief | **killed** | T10 |
| M8 | `cap_part BRIEF …` → plain `printf` (brief cap deleted) | **killed** | T10 |
| M10 | total cap default `8000` → `6000` | **killed** | T10 |

The G6/G10 mutants that died before — all still die:

| # | mutation | outcome | killed by |
|---|---|---|---|
| M1 | remove the board cap | **killed** | T7, T10 |
| M2 | remove the bundle cap | **killed** | T6, T10 |
| M4 | `chars` → `bytes` everywhere | **killed** | T6, T7, T8, T10 |
| M5 | remove the `\|\| echo "unavailable: evidence bundle failed"` guard | **killed** | T9 |
| M6 | remove the total cap (unconditional `printf`) | **killed** | T5, T8 |
| M7 | remove the `\|\| echo "unavailable: evidence tasks failed"` guard | **killed** | T9 |
| M9 | board cap `3000` → `30000` | **killed** | T7, T10 |
| M9b | bundle cap `2500` → `25000` | **killed** | T6, T10 |
| M11 | final `exit 0` → `exit 3` | **killed** | T1, T2, T5–T10 |
| G6-a | remove the `FACTORY_RUN` early exit | **killed** | T3 |
| G6-b | remove the linked-worktree check | **killed** | T4 |
| G6-c | awk → `cat` (whole board file) | **killed** | T1 |
| G6-d | drop the `unavailable: evidence not on PATH` text | **killed** | T2 |
| G6-e | reorder: brief printed before bundle | **killed** | T1 |
| G6-f | `cap_part` never truncates (`if false`) | **killed** | T6, T7, T10 |

Fifteen re-runs, fifteen kills — more than the eight the gate required. Note how
many now name T10 as an additional killer: the new test tightens M1, M2, M4, M9,
M9b and G6-f as well.

Four of my own, to look for a new blind spot:

| # | mutation | outcome | killed by |
|---|---|---|---|
| X1 | brief cap `1500` → `15000` | **killed** | T10 |
| X2 | total cap `8000` → `7000` (inside the 778 headroom) | **killed** | T10 |
| X3 | pointer echo removed entirely | **killed** | T1, T6, T10 |
| X4 | pointer path `session.md` → `sessions.md` | **killed** | T1, T6, T10 |
| X5 | remove the `\|\| echo "unavailable: docs/OPERATIONS.md not readable"` guard | **SURVIVED** | — (Finding 2) |

X2 matters: it shows the new test is not merely asserting "under 8000" against a
huge margin — a 7,000 ceiling, well inside the arithmetic, already eats the
pointer and is caught.

## Real run

From the clone, read-only,
`bash tools/session-start.sh /home/dalhaka/nixos-agent-env`:

- exit 0, **5,912 chars / 5,992 bytes**;
- two truncation lines fire, at output lines 37 and 84:
  `…board truncated at 3000 chars (SESSION_START_CAP_BOARD)` and
  `…bundle truncated at 2500 chars (SESSION_START_CAP_BUNDLE)`;
- the total cap does not fire; the pointer is last.

`tail -6`:

```
usage: evidence [-h] [--store STORE]
                {record,record-check,latest-check,bundle} ...
evidence: error: argument cmd: invalid choice: 'tasks' (choose from record, record-check, latest-check, bundle)
unavailable: evidence tasks failed

Where everything is: docs/runbooks/session.md
```

Unchanged in shape from the G10 gate's run (the live `evidence` still has no
`tasks` subcommand until G5b lands, so the `unavailable: evidence tasks failed`
guard fires — the guard M7 proves is tested). Size moved 5,986 → 5,992 bytes
only because the live board grew since yesterday; the script is identical.

## Findings

1. **MINOR (carried, deliberate) — the no-evidence branch still emits a blank
   brief.** `brief=""` in the final `else`, so `cap_part BRIEF ""` prints one
   empty line where the sibling branches print an `unavailable:` sentence. The
   section made this fix optional and the implementer declined it; the round
   stays strictly test-only as a result, which is the better trade. Worth one
   line in a later touch of the file.

2. **MINOR (pre-existing, out of scope) — the board-unreadable guard is still
   untested.** X5 survives: deleting
   `|| echo "unavailable: docs/OPERATIONS.md not readable"` leaves 10/10 green.
   The G10 review's Finding 7 named this as the third of G6's three untested
   guards and explicitly did not ask for it here; the other two (M5, M7) are
   pinned. Low value — awk's own error still reaches stdout through `2>&1` — but
   it is the one guard in this script with no test.

3. **NIT — a leftover untracked `scratch/commit-msg.txt` in the workspace.**
   `git status` in `ws/sc3/G10b` shows `?? scratch/` (the seat's commit-message
   file, 1,336 B, written 14:07). Not in the commit, not in the diff, harmless
   for integration; noted only so the integrator does not mistake it for work.

4. **Not a defect — the new test's redundant ordering assertion.** T10 asserts
   pointer-last via `tail -n1` *and* separately that `# Task brief`'s line number
   is lower than the pointer's. The second is subsumed by the first; it costs
   nothing and documents intent. Left alone.

No MAJORs. All four MAJOR findings of the G10 review (pointer-last untested,
no three-part fixture, `SESSION_START_CAP_BRIEF` uncovered, the `8000` default
unpinned) are closed by the one test, as the review predicted they would be.

## Deviations

- **The commit carries three files, not the two in the section's `touches`.**
  `docs/runbooks/session.md` appears because the common fix-round rule builds on
  a fresh `main` workspace and cherry-picks G10's whole diff uncommitted — G10
  was never integrated, so its runbook hunk has to travel with the fix round.
  Verified benign: the runbook and the script are byte-identical to G10's
  `aada4f2` (`git diff` empty for both), so the *round's* change really is
  test-only, exactly as the section says. Recorded, not held against the
  implementer.
- The section's optional `brief=""` script fix was not taken (see Finding 1).
  Allowed by its own wording.
- Everything else matches the section: one commit, G10's exact subject, the
  fixture the section specifies (400-line board, 4,000-char bundle, 3,000-char
  brief, default caps), all four assertions it lists, the trailing newline, and
  the three named mutations each proven load-bearing.
