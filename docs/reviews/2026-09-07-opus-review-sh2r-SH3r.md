---
plan_defect: none
mutants_total: 17
mutants_killed: 14
mutants_outside_named: 6
---
# Opus gate — seat run sh2r, task SH3r — APPROVED

## Summary

The chain's third round closes the hole the sh2f gate rejected on, and closes it at every
site the section names. `factory-task:378` and the hook's four loops are now pinned by a
fixture whose extra file is literally named `x*.txt` while the consumer's cwd (the driver's
cwd for rows 19/20, the worktree root for rows 21/22) holds `xy.txt` and `xz.txt`: reverting
either site to the SH3 idiom is red, loudly and by the assertion the plan predicted. I applied
all eleven named mutants myself, one at a time, reverted each with `git checkout --`, and
every one died; every `not ok` line and every `` #   `…' failed `` line in the commit body
reproduced byte for byte, test numbers included. Eight new rows (bats 35–42) are all red
against the base's implementation files and all green restored. `unit` (537 tests),
`evidence-unit` (421 passed) and `lint` are green at `--rebuild`; `githooks/pre-commit` is
green after the standing queue-block `git add`; `ruff check`/`ruff format --check`,
`shellcheck` over the five driver scripts, and `repomap write` + `git diff --exit-code
docs/MAP.md` are clean. One commit, subject byte-identical, two trailers, no board commit, the
plan file untouched, all 16 diffed files inside `touches` plus `docs/MAP.md` by the standing
rule.

I tried six mutants the section does not name, looking for the same shape one level out. Three
died — including the SH3b gate's "equivalent" N1 (now caught structurally by row 24's grep
proxy) and a grep-invisible `set -- $extra` rewrite of the driver loop (caught behaviourally
by rows 19/20, exactly as the section's proxy caveat claims). Three survived, none of them
reachable through a plan the toolbox accepts: two are the *touches-entry* side of the same
equality question (`factory_touches_covers` pattern-matching an entry), and one is the
withdrawn `set -f`-alone sentence the sh2f gate already ruled equivalent.

No MAJOR. Five MINORs, none owed by this task: one is main's own red `tasks check`, one is a
plan-text prediction that fires on a different assertion than the table says, one is a stated
SH3 contract (`never a glob` in `factory_touches_covers`) that still has no test, one is the
store rule carried to SH4, one is cosmetic.

## Contract items

The section's six numbered rejection items, taken literally.

| # | contract | file:line | verdict |
|---|---|---|---|
| 1 | MAJOR-1 closed by rows 19, 21, 24 and mutants M3, M4a–M4d | `tests/unit/94-seat-harness.bats:1075-1097` (row 19), `:1118-1151` (row 21), `:1206-1211` (row 24); sites `tools/factory/seat/factory-task:378-395`, `tools/factory/seat/factory-commit-msg.sh:44,56,62,67` | **met** — M3 and each of M4a–M4d red; evidence in ## Mutants |
| 2 | MINOR-1 closed: the body carries one block per mutant id; the gate counts eleven | `git log -1 --format=%B \| grep -c '^mutant M'` → `11` | **met** |
| 3 | MINOR-2 closed: the two withdrawn sentences replaced by M1 (the pair) and M2 | `tools/factory/seat/factory-lib.sh:628-634` | **met** — M1 red on six rows, M2 red on row 18 |
| 4 | MINOR-3 closed: row 18 pins `local -` | test `:1061-1073`; code `factory-lib.sh:628` | **met** — M2 kills it |
| 5 | MINOR-4 closed: row 22 pins the newline join for two files | test `:1153-1175`; code `factory-commit-msg.sh:47` | **met** — M5 kills it |
| 6 | the two plan-owned items: the corrected comment line 35, the allow line's wording, row 23, mutants M6/M7 | `factory-commit-msg.sh:35` (comment), `:29` (unreadable line), `:36-39` (the allow branch); test `:1177-1204` | **met** — comment byte-identical to the section (`cmp`, 182 bytes both); M6 and M7 both red |

The comment line, `cmp`-identical to the section's item 6 string:

```
# A git failure (the cwd outside a work tree, GIT_DIR naming no repository, a corrupt index) -> allow; a repo with no commits diffs against the empty tree and takes the normal path.
```

The corrected unreadable-message line (SH3 gate's MINOR-2, restated in the Interfaces) is at
`factory-commit-msg.sh:29` and reads `commit-msg: message file unreadable; allowing (the
driver recomputes touches after the seat exits)` — the section's words exactly, pinned by
SH3's row 7(g) (`ok 21`, which does **not** skip here: the gate runs as uid 1000).

**Step 1 (the carry).** `git fetch` of `task/SH3b` gives `2915c77f7a71ed23f95c6dbcd276c6a53298e4c2`;
`git diff FETCH_HEAD..HEAD` over source is exactly two files — `tests/unit/94-seat-harness.bats`
(+187) and `tools/factory/seat/factory-commit-msg.sh` (1 line, the comment). The other
thirteen `touches` files are byte-identical to SH3b:

```
$ git diff --stat FETCH_HEAD..HEAD -- tools/factory/seat/factory-lib.sh \
    tools/factory/seat/factory-task tools/factory/seat/factory-ws \
    tools/factory/seat/factory-integrate pkgs/evidence tests/evidence
(no output)
```

That satisfies "changes one comment line and, unless a red of Step 3 demands it, no other
source line", and "Nothing new in the store" (no `streams.py`, `ingest_result.py` or
`SCHEMA.md` change).

**The sh2f review's items, one by one.**

- **MAJOR-1 (`factory-task:378`, `factory-commit-msg.sh:44,56,62,67`) — closed.** The review's
  own probe is now a landed row. Row 19 (`ok 37`) runs the driver from a cwd holding `xy.txt`
  and `xz.txt` against a branch whose extra file is `x*.txt` and asserts `touches_files: x*.txt`,
  `touches_extra: 1`, the notes clause naming `x*.txt`, and `[[ "$output" != *"xy.txt"* ]]`.
  Reverting the driver loop (M3) makes it red; reverting any hook loop (M4a–M4d) makes row 21
  red. The review's exact demonstration is reproduced below under M3.
- **MINOR-1 — closed.** Eleven `mutant M…` blocks in the body; I re-ran all eleven and every
  paste matched.
- **MINOR-2 — closed.** The two sentences are withdrawn in the section text; M1 (both halves)
  and M2 (the options restore) replace them and both die.
- **MINOR-3 — closed.** Row 18 (`ok 36`) asserts `set +o noglob` after the disclosed,
  undisclosed and unreadable-file calls; M2 kills it.
- **MINOR-4 — closed.** Row 22 (`ok 40`) stages two undisclosed files; M5 (space join) kills it.
- **The sh2 gate's MINOR-2 / MINOR-3 (plan-owned, carried here) — closed.** The comment is
  corrected (above) and row 23 reaches the allow branch by a trigger that works
  (`GIT_DIR=<nonexistent>`), plus (h′) proving a commit-less repo is *not* a trigger.

## Red before green

**(a) The base's implementation files against the branch's tests.** `factory-lib.sh`,
`factory-task`, `factory-ws`, `factory-integrate`, `tasks.py`, `streams.py`,
`ingest_result.py` checked out at `fc345d0`, `factory-commit-msg.sh` deleted:

```
bats tests/unit/94-seat-harness.bats -> 34 of 42 not ok, the eight new rows among them:
  not ok 35 factory_disclosed treats a glob path as a literal token from a cwd with matches
  not ok 36 factory_disclosed restores the caller's noglob on every return path
  not ok 37 a glob-spelled path: the driver records x*.txt byte for byte from any cwd
  not ok 38 a glob-spelled path can be disclosed and landed
  not ok 39 the commit-msg hook treats a glob-spelled staged path as one literal name
  not ok 40 the commit-msg hook lists each undisclosed file on its own line
  not ok 41 the hook allows when git diff fails but refuses a first commit in an empty repo
  not ok 42 no path-list consumer uses an unquoted for-in-$ loop
pytest tests/evidence -q -> 17 failed, 403 passed, 1 skipped
```

Files put back (`git checkout HEAD -- tools pkgs tests`): `bats tests/unit/94-seat-harness.bats`
→ 42 ok, 0 not ok; `pytest tests/evidence -q` → `420 passed, 1 skipped`. Both figures are the
commit body's.

**(b) Per-row, by the section's own mutants.** Every one of the eight new rows is red under at
least one mutant below (35←M1,M8; 36←M2; 37←M3,O6; 38←M1,M3,O6; 39←M4a–M4d,M8; 40←M5;
41←M6,M7,O3; 42←M3,M4a–M4d,O1). No new row is vacuous.

## Mutants

**Named by the section: 11 applied, 11 killed.** Each applied on the clean tree and reverted
with `git checkout HEAD -- <file>` before the next.

| id | edit | red I got |
|---|---|---|
| M1 | `factory-lib.sh`: delete `set -f` **and** `read -r -a` + `for token in "${tokens[@]}"` → `for token in $line` | `not ok 12` (`:489`), `15` (`:551`), `27` (`:861`), `35` (`:1050`), `38` (`:1111`), `42` (`:1210`) |
| M2 | `factory-lib.sh:628`: delete `local -` | `not ok 36` (`:1067`) `` `[ "$output" = "set +o noglob" ]' failed `` |
| M3 | `factory-task:378`: `while IFS= read -r p … done <<<"$extra"` → `for p in $extra … done` | `not ok 37` (`:1089`), `38` (`:1111`), `42` (`:1210`) |
| M4a | `factory-commit-msg.sh:44` collect loop → `for path in $extra` | `not ok 39` (`:1135`) `` `[[ "$output" == *"commit-msg: 1 file(s) outside this task's touches:"* ]]' failed ``; `42` |
| M4b | `:56` count loop → `for path in $undisclosed` | `not ok 39` (`:1135`); `42` |
| M4c | `:62` list loop → `for path in $undisclosed` | `not ok 39` (`:1138`) `` `[[ "$output" != *"xy.txt"* ]]' failed ``; `42` |
| M4d | `:67` `Deviation:` loop → `for path in $undisclosed` | `not ok 39` (`:1138`); `42` |
| M5 | `factory-commit-msg.sh:47`: `$'\n'` → `' '` | `not ok 40` (`:1165`) `` `[[ "$output" == *"commit-msg: 2 file(s) outside this task's touches:"* ]]' failed `` |
| M6 | `:36-39` `if ! … fi` → bare `git diff --cached --name-only >"$changed" 2>/dev/null` | `not ok 41` (`:1187`) `` `[ "$status" -eq 0 ]' failed `` |
| M7 | insert `git rev-parse -q --verify HEAD >/dev/null 2>&1 \|\| exit 0` before `:36` | `not ok 41` (`:1188`) `` `[[ "$output" == *"commit-msg: git diff failed; allowing …"* ]]' failed `` |
| M8 | `factory-lib.sh:636`: `[ "$token" = "$path" ]` → `[[ $token == $path ]]` | `not ok 35` (`:1055`), `39` (`:1150`) |

M3 is the sh2f gate's MAJOR-1 mutant, the one that survived last round. Its red now:

```
not ok 37 a glob-spelled path: the driver records x*.txt byte for byte from any cwd
# (in test file tests/unit/94-seat-harness.bats, line 1089)
#   `[ "${lines[3]}" = "FACTORY-NOTES finished; 1 file(s) outside touches undisclosed: x*.txt" ]' failed
not ok 38 a glob-spelled path can be disclosed and landed
# (in test file tests/unit/94-seat-harness.bats, line 1111)
#   `[ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]' failed
not ok 42 no path-list consumer uses an unquoted for-in-$ loop
```

Every one of the eleven pastes in the commit body reproduced byte for byte — same `not ok`
numbers, same names, same failing assertion text.

**Outside the named set: 6 applied, 3 killed.**

- **O1 — `for token in $line` alone, `set -f` kept** (the sh2f gate's N1, ruled equivalent):
  **killed** — `not ok 42` (`:1210`). Behaviourally still equivalent, but row 24's grep proxy
  now catches the shape. A genuine gain over last round.
- **O2 — drop `set -f` alone, `read -r -a` kept** (N2): **survived**, 42/42 ok. Equivalent:
  `read -a` splits on IFS and never globs, `${token%[;,.:)]}` and `[ = ]` are unaffected by
  `noglob`. Not a finding; the section withdrew this sentence for exactly this reason.
- **O3 — M7's edit moved *after* the git-diff guard** (so the first case of row 23 passes and
  (h′) is the one under test): **killed** — `not ok 41` (`:1202`) `` `[ "$status" -eq 1 ]' failed ``.
  This proves the (h′) half of row 23 is itself pinned; see MINOR-2.
- **O4 — `factory_touches_covers`: `[ "$path" = "$entry" ]` → `[[ $path == $entry ]]`**:
  **survived**, 42/42 ok. See MINOR-3.
- **O5 — `factory-task:371`: `printf '%s\n' "$touches"` → unquoted `$touches`**: **survived**,
  42/42 ok. Same root as O4 (the touches-entry side). See MINOR-3.
- **O6 — the driver loop rewritten grep-invisibly**: `set -- $extra` + `for p in "$@"`,
  which row 24's regex cannot see: **killed** by the behavioural rows —
  `not ok 37` (`:1089`), `not ok 38` (`:1111`), row 42 green. The section's own caveat ("a
  consumer written another way is caught by rows 17–22, not here") is true as written.

## Checks

Run in a fresh clone of `task/SH3r` at `6f62da5`, `XDG_CACHE_HOME` under the session scratch.

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass, rc 0 — `ok 537 no path-list consumer uses an unquoted for-in-$ loop` |
| evidence-unit | `… evidence-unit …` | pass — `421 passed in 11.08s` |
| lint | `… lint …` | pass — `Found 0 warnings and 0 errors.` |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| shellcheck | `nix develop -c shellcheck …/factory-lib.sh …/factory-task …/factory-commit-msg.sh …/factory-ws …/factory-integrate` | rc 0 |
| bats (tree) | `nix develop -c bats tests/unit/94-seat-harness.bats` | 42 ok, 0 not ok (+ `80-seat-driver.bats` 80 ok = the body's 122) |
| pytest (tree) | `nix develop -c pytest tests/evidence -q` | `420 passed, 1 skipped` |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | clean, rc 0 |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | rc 1, one line: `tasks: nixos-agent-env/CX2 repo: codex not in docs/ledger/repos.toml` — **identical at the base `fc345d0`** (MINOR-1) |
| pre-commit | `nix develop -c githooks/pre-commit` | rc 1 only on `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again` (one line inside the markers: `… SH3r (…)` → `… SH4 (…)`); after `git add docs/OPERATIONS.md`, rc 0. The standing queue-block exemption, as in sh2 and sh2f. |

**Store rule.** Every driver test is synthetic: `fake_seat` writes a `printf` stub named
`dsh-openrouter` onto `PATH` (`94-seat-harness.bats:81-88`) and `FACTORY_ROOT` is
`$BATS_TEST_TMPDIR/factory` (`:47`); no test reads a real seat log. `~/factory/runs` gained no
`r1` entry, and `/var/lib/evidence` is untouched (its mtime is unchanged from before this
review's runs). The file still sets neither `FACTORY_EVIDENCE_CMD` nor `EVIDENCE_STORE` — see
MINOR-4.

## Touches and commit

`git diff fc345d0..HEAD --stat` names 16 files. Fifteen are the section's `touches` list —
verified against the tool itself, `tasks.py touches <plan> SH3r`, which prints exactly those
fifteen — and the sixteenth is `docs/MAP.md` (one line, `tests/evidence — 84 files` → `85`),
in by the standing rule. Nothing outside, so no `Deviation:` line is owed and none is present.
`docs/OPERATIONS.md` is not in the diff (no board commit); the plan file
`docs/superpowers/plans/2026-09-07-seat-harness-redesign.md` is not in the diff.

One commit, `6f62da5`, `git rev-list --count fc345d0..HEAD` = 1. `cmp` of `git log -1
--format=%s` against the section's `commit subject` line (plan line 798): identical, byte for
byte. The two trailers follow a blank line:
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sh2r)`
and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

Body shape as Step 5 requires: `Baseline:` (the two Step 1 lines), `Mutants, shown red then
reverted:` with eleven `mutant M…` blocks, `Greens:`. `grep -c '^mutant M'` → `11`.

## Findings

### MINOR-1 — `tasks.py --root . check` is red on this tree, inherited from main

`pkgs/evidence/tasks.py` (the check), triggered by a plan section outside this task.

```
$ nix develop -c python3 pkgs/evidence/tasks.py --root . check
tasks: nixos-agent-env/CX2 repo: codex not in docs/ledger/repos.toml   (rc 1)
```

The same command at the task's base `fc345d0`, in a worktree of the base, prints the same one
line with rc 1. It arrived with main's codex spec, not with this commit, and `githooks/pre-commit`
is green over it. Not owed by SH3r; it is owed by whoever adds `codex` to
`docs/ledger/repos.toml` (or by the CX plan's own section).

### MINOR-2 — M7's predicted red is not the assertion that fires

`tests/unit/94-seat-harness.bats:1177-1204`, plan Mutants table row M7.

The section predicts "row 23 (h′): exit 0". In fact M7's `git rev-parse … || exit 0` inserted
before line 36 also short-circuits the *first* case (`GIT_DIR=<nonexistent>` has no HEAD
either), so bats aborts at `:1188` on the missing `allowing` line and never reaches (h′):

```
not ok 41 the hook allows when git diff fails but refuses a first commit in an empty repo
# (in test file tests/unit/94-seat-harness.bats, line 1188)
#   `[[ "$output" == *"commit-msg: git diff failed; allowing (the driver recomputes touches after the seat exits)"* ]]' failed
```

The commit body pastes this actual red, honestly, rather than the predicted one — so the
implementer did not paper over it. And (h′) is not left unpinned: moving the same edit after
the git-diff guard (my O3) kills it at the (h′) assertion, `:1202`. A plan-text prediction
inaccuracy, no code or test change owed.

### MINOR-3 — `factory_touches_covers`'s stated "never a glob" still has no test

`tools/factory/seat/factory-lib.sh:565` (`[ "$path" = "$entry" ]`), `tools/factory/seat/factory-task:371`.

SH3's Interfaces state `factory_touches_covers` matches "never a substring, never a glob". Two
mutants on that sentence survive the whole suite:

- O4: `[ "$path" = "$entry" ]` → `[[ $path == $entry ]]` → 42/42 ok.
- O5: `factory-task:371` `printf '%s\n' "$touches" >"$touches_file"` → unquoted `$touches` → 42/42 ok.

Both need a *touches entry* spelled with a glob to discriminate, and `tasks.py check` rejects
a glob in `touches` (`tasks.py:1428-1434`), so neither is reachable through a validated plan —
defense in depth only, the mirror image of the path side that SH3r pins. Worth one row
(`touches` entry `sr*`, changed path `src/a` → still extra) whenever `factory_touches_covers`
is next opened; not owed by this section, which restates the `factory_disclosed` equality and
not this one.

### MINOR-4 — the store rule is still unset in `94-seat-harness.bats` (carry to SH4)

`tests/unit/94-seat-harness.bats` sets neither `FACTORY_EVIDENCE_CMD` nor `EVIDENCE_STORE`, so
the driver's `factory_ingest_result` aims at the `/var/lib/evidence` default and the failure is
swallowed into the log by design (the sh2f gate measured this and found no store write; I
re-confirmed `/var/lib/evidence` is untouched by these runs). SH3r's section does not mention
it, so it is not owed here — recorded for SH4's section, which is the task that starts writing
`checks_verified` through the same path.

### MINOR-5 — `tests/unit/94-seat-harness.bats` ends without a trailing newline

`tests/unit/94-seat-harness.bats:1211`. Carried from SH3b (`git show FETCH_HEAD:… | tail -c 3`
→ `] \n }`, same as HEAD), not introduced here, and `lint`/`treefmt` accept it. This commit
appends to that last line's region and could have fixed it in passing. Cosmetic.

## Verdict

**APPROVED.** The re-plan's one job was to make the chain's surviving mutant die and to leave
nothing behind that a one-line revert could undo silently. It does: all eleven named mutants
are red under my own hands and every body paste reproduces; the two sites that were unpinned
last round are held both behaviourally (rows 19–22, which also catch a grep-invisible rewrite)
and structurally (row 24); the two stated contracts the sh2f gate found untested — the `local -`
restore and the newline join — now have mutants that die; the `git diff failed; allowing`
branch is reachable by a trigger that works and its comment names that trigger truthfully.
Acceptance checks green at `--rebuild`, one commit, byte-identical subject, touches clean, no
board commit, plan untouched. The three surviving mutants are outside the section's set: one
the plan itself withdrew as equivalent, two on the touches-entry side that no validated plan
can reach. Nothing rises to a MAJOR.
