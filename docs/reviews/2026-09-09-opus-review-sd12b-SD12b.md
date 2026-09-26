---
plan_defect: implementer
plan_defect_secondary: underspecified
mutants_total: 6
mutants_killed: 4
mutants_outside_named: 3
model: opus
---
# Opus gate — seat run sd12b, task SD12b — REJECTED

## Summary

The carry is complete and faithful, the boot fix is green on this tree, and the
`fail` helper is gone. Four of the five files SD12 touched come across
byte-identical (`git diff 705a5d0:<f> HEAD:<f>` is empty for `flake.nix`,
`nixosModules/seatLane.nix`, `tests/integration/seat-vm.nix` and
`tools/factory/seat/seat-drive.sh`), so nothing the SD12 gate verified has moved.
I rebuilt the three checks the section did not name: `seat-eval`, `seat-vm` and
`host-core` are all `EXIT=0` on `--rebuild`, `seat-vm` over the SHIPPED unit —
`grep -n '/tmp' tests/integration/seat-vm.nix` returns three hits and all three
are comment lines (`:173–175`), `grep -n 'ReadWritePaths'` shows no `/tmp`
override anywhere, and `PrivateTmp = true;` is live at
`nixosModules/seatLane.nix:231`. `unit` and `lint` are green, the file ends with
a newline, one commit, subject byte-identical, no board change.

It still fails, and it fails on the same sentence it was sent back to fix.

SD12b's own commit subject promises "the executable-bit row names the file it
rejects". The row that ships does not. The seat extracted the two loops into
shared helpers — which interface 2 permits — but then rewrote the real row to
call them through bats' `run` (`tests/unit/88-seat-drive.bats:260–263`), which
captures the helper's stderr into `$output` and throws it away. `bats` is invoked
as a bare `bats tests/unit` (`flake.nix:2330`), with no
`--print-output-on-failure`, so `$output` is never printed on a failure. I put
the real regression back — `chmod -x tools/factory/seat/seat-drive.sh`, the 2026-09-08
production bug — and ran the actual acceptance check. `unit` reports:

```
unit-tests> not ok 353 every *.sh and extensionless script in the seat dir ships executable
unit-tests> #   `[ "$status" -eq 0 ]' failed
unit-tests> ok 354 the executable-bit check names the file it rejects
```

Zero occurrences of `not executable` in the whole build log. The operator is told
a line number and a loop, not one of the sixteen files in that directory —
exactly the harm MAJOR-1 of the SD12 gate named, re-created in a new shape while
row 354 passes claiming the opposite. Interface 1 said "the two loops and
everything else in the row are unchanged"; the row changed, and the change is the
defect.

The fix is again one line each: call the helpers directly instead of through
`run`. I measured that variant — it prints
`# not executable: …/tools/factory/seat/seat-drive.sh` in the failure. Nothing
else in this diff needs to move.

## Contract items

### SD12b's own interfaces

1. **Both failure paths lose `fail`, the message carries the expanded path; the
   two loops and everything else in the row are unchanged** — PARTLY MET, and the
   unmet half is MAJOR-1. The replacement text is exact at
   `tests/unit/88-seat-drive.bats:241` and `:251`:
   `[ -x "$f" ] || { printf 'not executable: %s\n' "$f" >&2; return 1; }`.
   No bats-support helper survives anywhere:
   `grep -rn 'bats_load_library|^load |BATS_LIB_PATH|bats-support|bats-assert' tests/ flake.nix githooks/`
   prints nothing and `grep -rn '\bfail "' tests/` prints nothing. But
   "everything else in the row" did change: the loops moved out of the row into
   `check_executable_sh` (`:238–243`) and `check_executable_ext` (`:244–253`),
   and the row now reaches them through `run` (`:260`, `:262`) with only
   `[ "$status" -eq 0 ]` (`:261`, `:263`) left in the body. That indirection is
   what swallows the message — MAJOR-1.

2. **A new row `the executable-bit check names the file it rejects`, fixture
   under `$BATS_TEST_TMPDIR`, one executable `a.sh`, one non-executable `b.sh`,
   one non-executable extensionless `runner`; asserts the run fails and the
   output contains the fixture path, then again for `runner`; helper extraction
   stated in the commit body** — MET as written.
   `tests/unit/88-seat-drive.bats:266–281`: `fixture="$BATS_TEST_TMPDIR/seat-fixture"`
   (`:267`), the three files at `:269–272`, `[ "$status" -eq 1 ]` +
   `[[ "$output" == *"$fixture/b.sh"* ]]` (`:275–276`), and the same pair for
   `runner` (`:279–280`). No tracked file is chmod'ed. The commit body states the
   choice: "extracted into the shared helpers `check_executable_sh` and
   `check_executable_ext` (interface 2, the 'extract the loop into a helper the
   two rows share' option)". The row is real — it kills mutants A, B and F below.
   What it does not do, and what nothing in the plan asked it to do, is assert
   anything about the SHIPPED row's own failure output; that gap is why MAJOR-1
   passed the seat's green run.

3. **The file ends with a trailing newline** — MET. `tail -c 3 … | od -c` →
   `\n } \n`. The SD12 gate's MINOR-4 is closed.

### SD12's interfaces, carried (this is the landing candidate)

`git diff --stat 705a5d0df28809273b8631be0e17e2b40d9307fc:<file> HEAD:<file>`
is EMPTY for all four of `flake.nix`, `nixosModules/seatLane.nix`,
`tests/integration/seat-vm.nix`, `tools/factory/seat/seat-drive.sh`. The carry is
complete and byte-identical; only the bats file differs (42 insertions, 10
deletions). Re-verified live on this tree rather than taken on trust:

1. **`seat@` gets its own `/tmp`** — MET. `nixosModules/seatLane.nix:231`
   `PrivateTmp = true;` under a comment (`:221–230`) naming
   `@deepseek-ai/dsh-spill-local`'s absolute `/tmp/dsh-spill-XXXXXX` prefix, why
   no environment variable can redirect it, and why a private instance beats
   widening `ReadWritePaths`. `DSH_CACHE_ROOT` untouched.
2. **`seat-eval` pins it** — MET. `flake.nix:1753–1754`,
   `assert nixpkgs.lib.assertMsg ((sc.PrivateTmp or false) == true)` with the
   section's message, immediately after the `KillMode` pin.
   `nix build .#checks.x86_64-linux.seat-eval -L --no-link --rebuild` → `EXIT=0`.
3. **The VM asserts the shipped unit** — MET, and this is the item the
   orchestrator flagged as the one that matters.
   `grep -n '/tmp' tests/integration/seat-vm.nix` → `:173`, `:174`, `:175`, all
   inside the comment that explains the unit "is otherwise the SHIPPED one -- no
   ReadWritePaths override, no /tmp admission" (`:172–176`).
   `grep -n 'ReadWritePaths'` → `:172`, `:233`, `:243`, `:261`, `:378`, `:382`,
   `:400`; the only executable one is the SB6b negative probe at `:382`
   (`ReadWritePaths=/nonexistent-seat-negative`, which *forces* 226/NAMESPACE and
   is removed again). No test-only escape.
   `nix build .#checks.x86_64-linux.seat-vm -L --no-link --rebuild` → `EXIT=0`,
   `test script finished in 36.46s`.
4. **`seat-drive` never prints a URL for a dead job** — MET.
   `tools/factory/seat/seat-drive.sh:147` `exit_file=…/exit_code.txt`,
   `:161–167` the stderr refusal and `exit 1`, `:168` `cat -- "$url_file"` moved
   past the guard. Rows 9 and 10 of the bats file (`:205`, `:222`) pin both
   directions and are `ok`.
5. **The executable bit is pinned, naming the file in the failure** — VIOLATED.
   The row exists and both arms are load-bearing (mutant D kills it), but it does
   not name the file. MAJOR-1.

## Red before green

* **Step 1 red, reproduced exactly as the seat reports it.** Mutant A applied to
  the branch tree (both failure paths back to `|| fail "not executable: $f"`,
  the new row present), `nix develop -c bats tests/unit/88-seat-drive.bats`:

  ```
  ok 11 every *.sh and extensionless script in the seat dir ships executable
  not ok 12 the executable-bit check names the file it rejects
  # (in test file tests/unit/88-seat-drive.bats, line 275)
  #   `[ "$status" -eq 1 ]' failed

  BW01: `run`'s command `check_executable_sh /tmp/nix-shell.kbDcB9/bats-run-gpBQIp/test/12/seat-fixture`
        exited with code 127, indicating 'Command not found'.
  ```

  Status 127, `command not found`, and the fixture's `b.sh` path nowhere in the
  output — the defect, reproduced. The seat's pasted red is truthful line for
  line (same line 275, same BW01 shape). Note row 11 stays `ok` under the mutant:
  the `fail` path never runs against a healthy tree, which is the whole reason
  the defect survived to the SD12 gate.

* **Green.** Branch HEAD, clean tree:
  `nix develop -c bats tests/unit/88-seat-drive.bats` → `1..12`, `ok 1` … `ok 12`,
  `BATS_EXIT=0`. Matches the body's paste.

* **The regression the row exists for — red, and it names nothing.** Fresh copy of
  the branch, `chmod -x tools/factory/seat/seat-drive.sh`, `git add -A`,
  `nix build .#checks.x86_64-linux.unit -L --no-link`:

  ```
  unit-tests> ok 352 seat-drive still prints the URL when exit_code.txt is zero
  unit-tests> not ok 353 every *.sh and extensionless script in the seat dir ships executable
  unit-tests> # (in test file tests/unit/88-seat-drive.bats, line 261)
  unit-tests> #   `[ "$status" -eq 0 ]' failed
  unit-tests> ok 354 the executable-bit check names the file it rejects
  ```

  `grep -c 'not executable' <the whole build log>` → `0`. MAJOR-1.

* **The one-line fix, measured.** Same `chmod -x`, row 11 rewritten to
  `check_executable_sh "$SEAT"` / `check_executable_ext "$SEAT"` (no `run`):

  ```
  not ok 11 every *.sh and extensionless script in the seat dir ships executable
  # (from function `check_executable_sh' in file tests/unit/88-seat-drive.bats, line 241,
  #  in test file tests/unit/88-seat-drive.bats, line 260)
  #   `check_executable_sh "$SEAT"' failed
  # not executable: …/tools/factory/seat/seat-drive.sh
  ```

  The file is named. Both bit restored afterwards; the clone is clean
  (`git status --porcelain` empty).

## Mutants

| # | mutant | named? | test that must kill it | outcome |
|---|---|---|---|---|
| A | both failure paths back to `\|\| fail "not executable: $f"` | yes (Step 4 A) | new row 12 | KILLED — `not ok 12 … line 275 \`[ "$status" -eq 1 ]' failed`, BW01 exit 127; no fixture path in the output |
| B | `check_executable_ext` body replaced by `:` (the extensionless loop dropped) | yes (Step 4 B) | new row 12's `runner` assertion | KILLED — `not ok 12 … line 272 \`[ "$status" -eq 1 ]' failed` |
| C | assertions weakened to `[ "$status" -ne 0 ]` alone, with A applied | yes (Step 4 C) | — | SURVIVES BY DESIGN — `ok 11`, `ok 12` with the `fail` defect present. This is the demonstration the section asks for and the commit body claims; measured true. It is why the path is asserted, not the exit status |
| D | `chmod -x tools/factory/seat/seat-drive.sh` (the real 2026-09-08 regression) | OUTSIDE | row 11, in `unit` | KILLED, but WRONGLY — `not ok 353 … \`[ "$status" -eq 0 ]' failed`, zero `not executable` lines in the log. See MAJOR-1 |
| E | `>&2` dropped from both failure paths | OUTSIDE | — | SURVIVES — `ok 11`, `ok 12`. Interface 1's stderr contract is asserted by nothing (row 12 uses plain `run`, which merges the streams). MINOR-2 |
| F | `return 1` dropped, `printf` kept | OUTSIDE | new row 12 | KILLED — `not ok 12 … line 275` |

mutants_total 6, mutants_killed 4 (A, B, D, F), mutants_outside_named 3 (D, E, F).
C is a designed survivor, not a hole.

## Checks

Fresh clone at `79eb641`, `XDG_CACHE_HOME` under the scratch dir. The three
checks beyond the section's `acceptance` line were run because the section's
Files/acceptance omitted the carry (the orchestrator's disclosed defect 2).

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | `EXIT=0`, `ok 675` last |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | `EXIT=0` |
| seat-eval | `nix build .#checks.x86_64-linux.seat-eval -L --no-link --rebuild` | `EXIT=0` |
| seat-vm | `nix build .#checks.x86_64-linux.seat-vm -L --no-link --rebuild` | `EXIT=0`, `test script finished in 36.46s` |
| host-core | `nix build .#checks.x86_64-linux.host-core -L --no-link` then `--rebuild` | `EXIT=0` both (the first `--rebuild` errored only because the drv had never been built here) |
| lint gate | `nix develop -c githooks/pre-commit` | `EXIT=1` — board queue block only, MINOR-1; `EXIT=0` on the re-run once `docs/OPERATIONS.md` is staged, every other arm green on the first pass |
| bats file | `nix develop -c bats tests/unit/88-seat-drive.bats` | 12/12 ok |
| shellcheck | `nix develop -c shellcheck tools/factory/seat/seat-drive.sh` | `EXIT=0` |
| MAP | `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | `EXIT=0`, no change (correct — no package/module/check/top-level entry added) |
| graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, `EXIT=0` |

No python touched, so no separate `ruff` arm beyond the gate's own (green).

## Touches and commit

`git diff 9bc3cf2..HEAD --stat`:

```
 flake.nix                        |  9 +++++
 nixosModules/seatLane.nix        | 11 ++++++
 tests/integration/seat-vm.nix    | 71 ++++++++++++-------------
 tests/unit/88-seat-drive.bats    | 80 +++++++++++++++++++++++++++++-
 tools/factory/seat/seat-drive.sh | 18 ++++++++-
```

The section's `touches` names `tests/unit/88-seat-drive.bats` alone. The other
four are SD12's approved carry — byte-identical to `705a5d0`, as measured above —
and the section's failure to name them is the orchestrator's disclosed plan
defect (1). Not penalised; recorded as MINOR-3 only because the commit body does
not say why they are there.

`docs/OPERATIONS.md` is NOT in the diff (0 files) — the seat's reported revert of
the queue-block regeneration is confirmed. The plan file is untouched. Exactly one
commit, `79eb641`. Subject compared with `cmp` against the section's
`**commit subject:**`: identical, 190 bytes both. Body states the why, and pastes
the Step 1 red and the Step 3 green literally (the SD12 gate's MINOR-2 is closed).
Both trailers present after a blank line, in WORKSPACE RULES order:
`Generated-By:` then `Co-Authored-By:`.

## Findings

**MAJOR-1 — `tests/unit/88-seat-drive.bats:260–263`: the shipped executable-bit
row calls its helpers through `run`, so the helper's message is captured and
discarded and the row still does not name the file it rejects. The SD12 gate's
MAJOR is not closed — it is re-created in a new form, under a commit subject that
claims it is fixed.**

```
  run check_executable_sh "$SEAT"
  [ "$status" -eq 0 ]
  run check_executable_ext "$SEAT"
  [ "$status" -eq 0 ]
```

`run` redirects the command's stdout and stderr into `$output`/`$stderr`. Bats
prints those on failure only under `--print-output-on-failure`, and the check
invokes it bare — `flake.nix:2330`: `bats tests/unit`. So the message the seat
carefully spelled with an expanded path never reaches anyone.

Measured against the real regression this row exists for (`chmod -x
tools/factory/seat/seat-drive.sh`, the 2026-09-08 production bug), in the
acceptance check itself:

```
unit-tests> not ok 353 every *.sh and extensionless script in the seat dir ships executable
unit-tests> # (in test file tests/unit/88-seat-drive.bats, line 261)
unit-tests> #   `[ "$status" -eq 0 ]' failed
unit-tests> ok 354 the executable-bit check names the file it rejects
```

`grep -c 'not executable'` over the entire build log: `0`. Sixteen files live in
`tools/factory/seat/`; the operator is told none of them. Compare the SD12 gate's
MAJOR-1, which rejected this task for
`not ok 11 … line 240 … failed with status 127` / no file named. The failure text
changed; the operator's position did not.

SD12 interface 5: "…is executable (`[ -x "$f" ]`), **naming the file in the
failure**." SD12b interface 1: "The two loops and everything else in the row are
unchanged." Both are violated by the same four lines. Interface 2's permission to
"extract the loop into a helper the two rows share" licenses the helpers — it
does not license routing the real row through `run`; the helpers can be called
directly, and interface 1 required exactly that.

The fix, measured on this tree: delete the four lines above and write

```
  check_executable_sh "$SEAT"
  check_executable_ext "$SEAT"
```

which under bats' errexit fails the row and prints
`# not executable: …/tools/factory/seat/seat-drive.sh` (pasted in full under
"Red before green"). Row 12 is unaffected — it must keep `run`, because it
asserts on the captured output. Nothing else in the diff needs to change.

**MINOR-1 — `docs/OPERATIONS.md` (not in the diff): the branch's lint gate exits
1 on its first run.**

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
```

The regenerated block drops `SD12b` from the queue, because `landed_subjects`
reads commit subjects and the branch's own byte-identical subject makes SD12b look
landed. Structural for every task branch here, anticipated verbatim by the plan's
Global Constraints, and handled downstream (no landed task commit carries the
board). The re-run with the file staged is `EXIT=0` with every formatter and
linter arm green. Recorded, not gating. Identical to the SD12 gate's MINOR-1.

**MINOR-2 — `tests/unit/88-seat-drive.bats:241,251`: the `>&2` in interface 1's
stated failure path is asserted by nothing.** Mutant E (both redirects deleted)
leaves `ok 11`, `ok 12`. Row 12 uses plain `run`, which merges stderr into
`$output`, so a message printed to stdout satisfies `:276` and `:280` equally.
Interface 1 states the stream; no test pins it. A `run --separate-stderr` with the
assertions moved to `$stderr` — the idiom this very file already uses at `:197`
and `:214` — would close it.

**MINOR-3 — commit `79eb641` body: four files outside `touches` with no sentence
saying why.** `flake.nix`, `nixosModules/seatLane.nix`,
`tests/integration/seat-vm.nix` and `tools/factory/seat/seat-drive.sh` are in the
diff; the section's Files and `touches` name only the bats file. The carry is
correct and is the point of this landing, and the omission originates in the plan
section (the orchestrator's disclosed defect 1) — but the Global Constraints make
`touches` a contract whose deviation is reported, and the body reports nothing.
Recorded, not gating; the seat's judgement to carry was right.

**MINOR-4 — `tests/unit/88-seat-drive.bats:238–243`: `check_executable_sh` has no
guard for an empty glob.** With `nullglob` off (bats' default), a directory
holding no `*.sh` yields the literal `<dir>/*.sh`, which is not executable, so the
helper reports `not executable: <dir>/*.sh` and returns 1 for a directory that is
in fact fine. Unreachable for `$SEAT` and for the fixture as written, so it is a
robustness note, not a defect in the shipped assertion.

**MINOR-5 — `tests/integration/seat-vm.nix:243–261`: SB4b's "-"-prefix proof is
still narrowed from four absent home paths to three.** Carried unchanged from
SD12, where it was recorded as MINOR-3, and correctly documented in the file's own
comment. Re-recorded so the ledger sees it once on the landing commit; nothing owed.

## Verdict

**REJECTED** on MAJOR-1.

Everything the switch #24 surface depends on is sound and was re-measured here,
not taken on trust: the carry is byte-identical to the approved SD12 work,
`seat-vm` is green over the shipped unit with no `/tmp` escape anywhere,
`seat-eval` pins `PrivateTmp` in the stated form, `host-core` builds, the dead-job
refusal holds in both directions, and the `fail` helper is gone from the tree. The
new fixture row is genuine — it kills three mutants including the `fail` restoration,
and it demonstrates mutant C's survival exactly as the section predicted.

What blocks it is that the row the operator will actually see go red still cannot
tell them which of sixteen scripts lost its bit, because the seat routed it
through `run` while fixing the message it prints. That is the SD12 gate's MAJOR,
unclosed, now shipping under a commit subject that asserts the opposite and beside
a green row named "the executable-bit check names the file it rejects". Two lines
close it, and I have pasted the measured output of those two lines above.

`plan_defect: implementer` — interface 1 said in so many words that the two loops
and everything else in the row are unchanged, and the seat changed the row in the
one way that reintroduces the defect. `plan_defect_secondary: underspecified` —
interface 2 offered helper extraction as an option without saying that the SHIPPED
row must still surface the helper's message, and the new row it specifies asserts
only on the helper, never on the row; a section written to fix a failure-output
contract left that contract untested for the artifact that ships.
