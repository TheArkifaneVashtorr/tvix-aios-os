---
plan_defect: none
mutants_total: 8
mutants_killed: 7
mutants_outside_named: 5
model: opus
---
# Opus gate — seat run sd12c, task SD12c — APPROVED

## Summary

The defect that killed SD12 and SD12b is dead, and I killed it with the evidence
the orchestrator named rather than with an exit status. Fresh clone of
`task/SD12c` at `e5f2f4a`, `chmod -x tools/factory/seat/seat-drive.sh`,
`git add -A`, `nix build .#checks.x86_64-linux.unit -L --no-link` — the real
acceptance check, not a bare `bats` run:

```
unit-tests> not ok 353 every *.sh and extensionless script in the seat dir ships executable
unit-tests> # (from function `check_executable_sh' in file tests/unit/88-seat-drive.bats, line 241,
unit-tests> #  in test file tests/unit/88-seat-drive.bats, line 263)
unit-tests> #   `check_executable_sh "$SEAT"' failed
unit-tests> # not executable: /build/tests/unit/../../tools/factory/seat/seat-drive.sh
unit-tests> ok 354 the executable-bit check names the file it rejects
```

`grep -c 'not executable'` over the whole build log → **1**, and the line names
`tools/factory/seat/seat-drive.sh`. SD12's round was 127/no file; SD12b's round
was a line number/no file with a grep count of **0**. This round names the file
inside the derivation the operator actually runs. The bit was restored; the clone
is `git status --porcelain` empty.

The same discriminator, applied to mutant A (the `run` form SD12b shipped,
restored on top of the same `chmod -x`, through the same real check), gives grep
count **0** — so the assertion is not merely present, it is discriminating: the
two forms are separated by the message, exactly as the section says the exit
status cannot separate them.

Everything the switch #24 surface rests on was re-measured, not taken on trust.
The SD12 carry is byte-identical to SD12b's tip `79eb641` for all four files
(`git diff 79eb641:<f> HEAD:<f>` empty), the only difference between the two
commits being the eleven lines of interfaces 1 and 3 in the bats file.
`seat-eval`, `seat-vm`, `host-core`, `unit` and `lint` are all `EXIT=0` under
`--rebuild`, `seat-vm` over the SHIPPED unit with `PrivateTmp = true;` live and
no `ReadWritePaths` `/tmp` override anywhere. One commit, subject byte-identical
(165 bytes, `cmp` clean), both trailers, no board commit, plan file untouched.
Interface 3 closes the previous gate's MINOR-2: deleting both `>&2` redirects now
kills a row, and I proved it was a real hole first by re-running that mutant
against SD12b's tree, where all twelve rows stay green.

No trace of `scratch-probe.py` anywhere — not in the diff, the committed tree,
the object history, or the source workspace.

**APPROVED.**

## Contract items

Taken literally, item by item.

**Interface 1 — the four `run`/status lines become two direct calls; nothing else
in the row, the two helpers, or any other row changes.** MET.
`tests/unit/88-seat-drive.bats:263-264`:

```
  check_executable_sh "$SEAT"
  check_executable_ext "$SEAT"
```

`git diff 79eb641:tests/unit/88-seat-drive.bats HEAD:…` shows the four lines
(`run check_executable_sh "$SEAT"` / `[ "$status" -eq 0 ]` ×2) removed and these
two added, and nothing else in that row but the comment. The two helpers
(`:238-243`, `:244-253`) are untouched — `check_executable_sh`'s body is still
`[ -x "$f" ] || { printf 'not executable: %s\n' "$f" >&2; return 1; }` at `:241`
and `check_executable_ext`'s at `:251`. Rows 1–10 are untouched. The row's
explanatory comment grew by four lines (`:259-262`, "Called directly (not through
`run`) …"); that is the only text in the row beyond the two calls that moved, and
it is documentation of the change itself — recorded as MINOR-2, nothing owed.

The claim in that comment is measured true: under bats' errexit the non-zero
return fails the row on the spot and bats prints the helper's stderr as a `#`
comment, which the plan's pasted expectation predicted line for line. Note the
line numbers shifted by the comment: the section predicted `line 260`, the
shipped row is `line 263`. The shape is identical.

**Interface 2 — the fixture row keeps `run` (it asserts on captured output), keeps
asserting the fixture's `b.sh` and `runner` paths, and both rows still exist.**
MET. `tests/unit/88-seat-drive.bats:267-284` is still a separate row, still uses
`run` (now `run --separate-stderr`, which interface 3 requires), and still
asserts both paths — `:279` `[[ "$stderr" == *"$fixture/b.sh"* ]]`, `:283`
`[[ "$stderr" == *"$fixture/runner"* ]]`. The two rows were not collapsed: the
`unit` log shows both, `ok 353` and `ok 354`. No tracked file is chmod'ed by the
fixture; it builds `a.sh` (executable), `b.sh` and `runner` under
`$BATS_TEST_TMPDIR` at `:268-273`.

**Interface 3 — the `>&2` redirect gains an assertion; `run --separate-stderr` (or
a `2>` capture), stating which and why; the deleted-redirect mutant dies.** MET,
and this is the item that closes the previous gate's MINOR-2.
`tests/unit/88-seat-drive.bats:277` and `:281` are
`run --separate-stderr check_executable_sh "$fixture"` /
`run --separate-stderr check_executable_ext "$fixture"`, with the assertions moved
from `$output` to `$stderr` at `:279` and `:283`. The choice and the reason are
stated in the file at `:275-276`:

```
  # --separate-stderr: the message must land on stderr specifically (not
  # merged into $output), so deleting the helpers' >&2 redirects is caught.
```

The mutant dies — see mutant E below. I also verified the hole was real rather
than assumed: SD12b's fixture row restored (plain `run`) plus mutant E gives
`EXIT=0`, `ok 1` … `ok 12`. That is interface 3's red, measured.

**Files / touches — modify `tests/unit/88-seat-drive.bats`.** MET for the delta.
`git diff 79eb641..HEAD --stat` is that file alone. The four carry files appear
only against the `main` base — see ## Touches and commit.

**Steps 1–5.** Step 1's regression red, Step 3's green and both grep counts are in
the commit body and reproduce here. Step 1's second half (mutant E on the
pre-change tree, every row green) is not pasted in the body — MINOR-3; I ran it
myself and it holds. Step 4's three mutants all die (below). Step 5: exactly one
commit.

### The previous gate's items, one by one

`docs/reviews/2026-09-09-opus-review-sd12b-SD12b.md`:

| item | status |
|---|---|
| **MAJOR-1** — the shipped row routes through `run`, message discarded, grep count 0 | **CLOSED.** Direct calls at `:263-264`; grep count **1** over the real `unit` build log, naming `tools/factory/seat/seat-drive.sh` |
| MINOR-1 — the lint gate exits 1 once on the board's queue block | recurs, structural, not owed (see ## Checks) |
| **MINOR-2** — `>&2` asserted by nothing; mutant E survives | **CLOSED** by interface 3; mutant E now fails `:279` |
| MINOR-3 — the body does not say why four files sit outside `touches` | **still open**, carried; re-recorded as MINOR-1 |
| MINOR-4 — `check_executable_sh` has no empty-glob guard | unchanged (helpers byte-identical); robustness note, nothing owed, SD12c did not ask |
| MINOR-5 — SB4b's "-"-prefix proof narrowed to three paths | carried unchanged in `tests/integration/seat-vm.nix`; nothing owed |

### The SD12 carry (this is the landing candidate)

`git diff 79eb641:<f> HEAD:<f>` is EMPTY for `flake.nix`,
`nixosModules/seatLane.nix`, `tests/integration/seat-vm.nix` and
`tools/factory/seat/seat-drive.sh`. Re-verified live rather than assumed:

1. **`seat@` gets its own `/tmp`** — `nixosModules/seatLane.nix:231`
   `PrivateTmp = true;`.
2. **`seat-eval` pins it** — `flake.nix:1753-1754`,
   `assert nixpkgs.lib.assertMsg ((sc.PrivateTmp or false) == true)` with the
   section's message; also `flake.nix:1534` `&& sc.PrivateTmp == true`.
   `seat-eval` `EXIT=0` on `--rebuild`.
3. **The VM asserts the SHIPPED unit** — `grep -n '/tmp' tests/integration/seat-vm.nix`
   → `:173`, `:174`, `:175`, all inside the comment that says the unit "is
   otherwise the SHIPPED one -- no ReadWritePaths override, no /tmp admission".
   `grep -n 'ReadWritePaths'` → `:172`, `:233`, `:243`, `:261`, `:378`, `:382`,
   `:400`; the only executable one is the SB6b negative probe at `:382`
   (`ReadWritePaths=/nonexistent-seat-negative`, which forces 226/NAMESPACE and is
   removed again). No test-only escape. `seat-vm` `EXIT=0` on `--rebuild`,
   `test script finished in 37.46s`.
4. **`seat-drive` never prints a URL for a dead job** — rows 9 and 10
   (`tests/unit/88-seat-drive.bats:205`, `:222`) both `ok` in `unit`
   (`ok 351`, `ok 352`).
5. **The executable bit is pinned, naming the file in the failure** — MET at last,
   measured in the real check (## Summary).

The `fail` helper is gone tree-wide:
`grep -rn 'bats_load_library|^load |BATS_LIB_PATH|bats-support|bats-assert' tests/ flake.nix githooks/`
prints nothing; `grep -rn '\bfail "' tests/` prints nothing. And the fix was made
in the test, not by widening the runner:
`grep -n 'print-output-on-failure' flake.nix` prints nothing, `flake.nix:2330` is
still bare `bats tests/unit`.

## Red before green

* **The regression this row exists for — RED, and it names the file.** Fresh copy
  of the branch, `chmod -x tools/factory/seat/seat-drive.sh`, `git add -A`,
  `nix build .#checks.x86_64-linux.unit -L --no-link` → `EXIT=1`, the block
  pasted in ## Summary, **`grep -c 'not executable'` = 1** at log line 364,
  naming `…/tools/factory/seat/seat-drive.sh`. Bit restored.

* **GREEN.** Clean clone: `nix develop -c bats tests/unit/88-seat-drive.bats` →
  `1..12`, `ok 1` … `ok 12`, `EXIT=0`. And the whole check:
  `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` → `EXIT=0`,
  675 rows, `grep -c 'not ok'` = **0**, with `ok 353` / `ok 354` the two rows in
  question.

* **Interface 3's red, measured (the plan's Step 1 second half).** SD12b's fixture
  row restored (`git checkout 79eb641 -- tests/unit/88-seat-drive.bats`) plus
  mutant E (both `>&2` deleted): `EXIT=0`, `ok 11`, `ok 12` — every row green with
  the redirect gone. That is the hole the previous gate filed as MINOR-2, and it
  was real. On the shipped tree the same mutant fails `:279`. Red before green,
  demonstrated for the new assertion and not merely asserted.

* **The extensionless arm, red on the real directory.** `chmod -x
  tools/factory/seat/factory-brief` (an extensionless script, so only
  `check_executable_ext` can see it):

  ```
  not ok 11 every *.sh and extensionless script in the seat dir ships executable
  # (from function `check_executable_ext' in file tests/unit/88-seat-drive.bats, line 251,
  #  in test file tests/unit/88-seat-drive.bats, line 264)
  #   `check_executable_ext "$SEAT"' failed
  # not executable: …/tools/factory/seat/factory-brief
  ```

  Both arms of the guard row name their file, not just the `*.sh` one.

The commit body's pasted red and green match what I measured, line for line and
grep count for grep count, at the bats-file level; I extended both to the real
`unit` derivation, where the previous two rounds died.

## Mutants

Each applied in its own scratch copy of the clone, run, then discarded.

| # | mutant | named? | test that must kill it | outcome |
|---|---|---|---|---|
| **A** | restore the `run check_executable_sh "$SEAT"` / `[ "$status" -eq 0 ]` form in the guard row, on top of `chmod -x seat-drive.sh` | yes (Step 4 A) | the guard row, discriminated by the grep count over the real check's log | **KILLED** — `not ok 353 …` / `# (in test file tests/unit/88-seat-drive.bats, line 264)` / `#   \`[ "$status" -eq 0 ]' failed`, and **`grep -c 'not executable'` = 0** over the whole build log, against **1** for the shipped form. The discriminator separates them exactly as the section requires |
| **B** | `check_executable_ext` body replaced by `:` | yes (Step 4 B) | the fixture row's `runner` assertion | **KILLED** — `not ok 12 … (in test file tests/unit/88-seat-drive.bats, line 275)` / `#   \`[ "$status" -eq 1 ]' failed` |
| **E** | both `>&2` redirects deleted from the helpers | yes (Step 4 E) | interface 3's `$stderr` assertion | **KILLED** — `not ok 12 … line 279` / `#   \`[[ "$stderr" == *"$fixture/b.sh"* ]]' failed`. (Against SD12b's fixture row the same mutant is green in all twelve rows — the hole, closed) |
| D | `chmod -x tools/factory/seat/seat-drive.sh` (the real 2026-09-08 production regression), shipped code | OUTSIDE | the guard row, in `unit` | **KILLED, and usefully** — `not ok 353`, grep count 1, the file named |
| F | `return 1` dropped from both failure paths, `printf` kept | OUTSIDE | the fixture row | **KILLED** — `not ok 12 … line 278` / `#   \`[ "$status" -eq 1 ]' failed` |
| G | `run --separate-stderr` reverted to plain `run` in the fixture row (interface 3 undone, `>&2` kept) | OUTSIDE | the fixture row | **KILLED** — `not ok 12 … line 279` / `#   \`[[ "$stderr" == *"$fixture/b.sh"* ]]' failed`. Interface 3 is load-bearing in both directions |
| I | `chmod -x tools/factory/seat/factory-brief` (an extensionless script in the real dir) | OUTSIDE | the guard row's `check_executable_ext` arm | **KILLED** — `not ok 11 … from function \`check_executable_ext' … line 251`, `# not executable: …/factory-brief` |
| H | the fixture row's `[[ "$stderr" == *"$fixture/b.sh"* ]]` deleted | OUTSIDE | — | **SURVIVES** — a degenerate mutant: deleting an assertion cannot be caught by the suite that contains it. Recorded for honesty, not a hole; the `runner` assertion at `:283` still covers the same helper family |

`mutants_total` 8, `mutants_killed` 7 (A, B, D, E, F, G, I), `mutants_outside_named` 5
(D, F, G, H, I). All three named mutants die. Mutant C of the previous section
(the "weaken to `-ne 0`" designed survivor) is not named by SD12c and was not
re-run; its lesson is now embodied in mutant A's grep-count discriminator.

## Checks

Fresh clone at `e5f2f4a`, `XDG_CACHE_HOME` under the gate scratch dir. The three
checks beyond the section's `acceptance` line were run because the section's
`acceptance` does not cover the carried boot fix.

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | `EXIT=0`, 675 rows, 0 `not ok` |
| lint | `… lint -L --no-link --rebuild` | `EXIT=0` |
| seat-eval | `… seat-eval -L --no-link --rebuild` | `EXIT=0` |
| seat-vm | `… seat-vm -L --no-link --rebuild` | `EXIT=0`, `test script finished in 37.46s`, over the SHIPPED unit |
| host-core | `… host-core -L --no-link` then `--rebuild` | `EXIT=0` both. The first `--rebuild` errored only because the drv had never been built on this machine (`some outputs … are not valid, so checking is not possible`); after the plain build, `--rebuild` is `EXIT=0` |
| lint gate | `nix develop -c githooks/pre-commit` | `EXIT=1` on the first run — board queue block only (MINOR-4); `EXIT=0` on the re-run with `docs/OPERATIONS.md` staged, every formatter and linter arm green on the first pass too |
| bats file | `nix develop -c bats tests/unit/88-seat-drive.bats` | `1..12`, 12/12 `ok` |
| MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | `EXIT=0`, no change — correct, no package/module/check/tool entry added |
| task graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, `EXIT=0` |

No python is touched by this commit, so there is no separate `ruff` arm beyond
the lint gate's own (green). The board file was restored after the gate re-run;
the clone ends `git status --porcelain` empty.

## Touches and commit

`git diff 79eb641..HEAD --stat` — the delta this task owns:

```
 tests/unit/88-seat-drive.bats | 11 ++++++-----
```

Exactly the section's `touches`, nothing else. Against the `main` base
`9c4bbee` the diff is the whole chain:

```
 flake.nix                        |  9 +++++
 nixosModules/seatLane.nix        | 11 ++++++
 tests/integration/seat-vm.nix    | 71 ++++++++++++++--------
 tests/unit/88-seat-drive.bats    | 83 +++++++++++++++++++++++++++-
 tools/factory/seat/seat-drive.sh | 18 ++++++++-
```

The four extra files are SD12's approved carry, byte-identical to `79eb641`
(measured above) and the entire point of this landing; the section's Files line
names only the bats file because it types the delta, and it says in so many words
that the carry "stays exactly as it is". The commit body still does not say this
— MINOR-1, carried from the previous gate.

`docs/OPERATIONS.md` is NOT in the diff. The plan file is untouched. Exactly one
commit (`git rev-list --count 9c4bbee..HEAD` → 1). Subject compared with `cmp`
against the section's `**commit subject:**` — identical, 165 bytes both. Body
states the why and pastes the Step 1 red and the Step 3 green with their grep
counts (0 and 1). Both trailers, after a blank line, in the WORKSPACE RULES
order:

```
Generated-By: Claude Sonnet 5 (escalation rung, claude/implement/any/any high, factory run sd12c)
Co-Authored-By: Claude Sonnet <noreply@anthropic.com>
```

The file ends with a trailing newline (`tail -c 3 … | od -c` → `\n } \n`).

**The `scratch-probe.py` anomaly — nothing found.** `git diff 9c4bbee..HEAD |
grep -ci 'scratch-probe'` → 0. `git log --all -- scratch-probe.py` → empty.
`git ls-files | grep -i scratch` → empty. `find` over the whole clone for
`*scratch*` / `*probe*` returns only the tracked fixture
`tests/evidence/fixtures/results/probes.result`, which predates this branch and is
unrelated. The source workspace
`/home/dalhaka/factory/ws/sd12c/SD12c` is clean but for one untracked
`.commit-msg-sd12c.txt` (the `git commit -F` message file) and a gitignored
`.ruff_cache/`. No trace of the reported file in the diff, the tree, the history
or the workspace. I did not modify anything under `/home/dalhaka/factory`.

## Findings

**MINOR-1 — commit `e5f2f4a` body: four files outside `touches` with no sentence
saying why.** `flake.nix`, `nixosModules/seatLane.nix`,
`tests/integration/seat-vm.nix` and `tools/factory/seat/seat-drive.sh` are in the
diff against `main`; the section's Files and `touches` name only
`tests/unit/88-seat-drive.bats`. The carry is correct, byte-identical to the
approved SD12b tip, and is the reason this branch exists — but the Global
Constraints make `touches` a contract whose deviation is reported, and the body
reports nothing. Identical to the previous gate's MINOR-3, not closed. Recorded,
not gating, and no fix is owed on this commit: opening it to re-word the body
would risk the byte-identical carry for a sentence.

**MINOR-2 — `tests/unit/88-seat-drive.bats:259-262`: interface 1 said "nothing
else in the row … changes", and the row's comment changed.**

```
  # cannot see a missing bit). Called directly (not through `run`) so a
  # non-zero return fails this row on the spot and bats prints the helper's
  # stderr, naming the file -- routing it through `run` would capture that
  # message into $output and bats prints neither on a bare status assertion.
```

A literal reading of interface 1 forbids it; every word of it is true, it
documents precisely the trap two rounds fell into, and it shifts the row's line
number from the section's predicted 260 to 263. Recorded so the ledger sees the
deviation; nothing owed — the plan should have said "nothing else *executable*".

**MINOR-3 — commit `e5f2f4a` body: Step 1's second half is not pasted.** Step 1
asks for the `chmod -x` red *and* "apply mutant E (delete both `>&2`) and show
every row still green — that is interface 3's red". The body pastes the first and
not the second, so the commit does not itself carry the proof that the new stderr
assertion could ever have failed. Step 5's own wording asks only for "the Step 1
red and the Step 3 green", so this is a seam in the plan's own instructions, not
a contract broken. I measured it (## Red before green): on SD12b's tree with
mutant E, `EXIT=0`, all twelve rows green. The assertion is genuinely new
coverage. Recorded, not gating.

**MINOR-4 — `docs/OPERATIONS.md` (not in the diff): the branch's lint gate exits 1
on its first run.**

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
```

The regenerated block drops `SD12c` from the queue, because `landed_subjects`
reads commit subjects and the branch's own subject makes SD12c look landed.
Structural for every task branch here, anticipated verbatim by the plan's Global
Constraints, and handled downstream (no landed task commit carries the board).
The re-run with the file staged is `EXIT=0`. Recorded, not gating. Third
occurrence in this chain.

**MINOR-5 — `tests/unit/88-seat-drive.bats:238-243`: `check_executable_sh` has no
empty-glob guard.** With `nullglob` off (bats' default) a directory holding no
`*.sh` yields the literal `<dir>/*.sh`, which is not executable, so the helper
reports `not executable: <dir>/*.sh` for a directory that is fine. Unreachable
for `$SEAT` (which holds `seat-drive.sh`, `factory-lib.sh` and three more) and
for the fixture as written. Carried unchanged from SD12b, where it was MINOR-4.
Robustness note; nothing owed.

**MINOR-6 — `tests/integration/seat-vm.nix:243-261`: SB4b's "-"-prefix proof is
still narrowed from four absent home paths to three.** Carried unchanged from
SD12 and documented in the file's own comment. Re-recorded once on the landing
commit; nothing owed.

No MAJORs.

## Verdict

**APPROVED.**

The one thing this task existed to do is done, and I proved it with the evidence
the last two rounds could not produce: over the real `unit` derivation, with the
production regression re-applied, `grep -c 'not executable'` is **1** and the
line names `tools/factory/seat/seat-drive.sh`. The same measurement against the
form SD12b shipped is **0**. Exit status could not tell those two apart — that is
precisely why both earlier rounds passed a red-before-green check while shipping
a guard that told the operator nothing — and the count does.

The section's three interfaces are met literally, the three named mutants all die,
five more outside the named set were tried and four of those die too (the fifth is
a deleted assertion, which no suite can catch). Interface 3 is not decoration: I
reproduced the hole it fills on SD12b's tree, where deleting both `>&2` redirects
left every row green, and it now fails at `:279`.

The carry that makes this the landing candidate for switch #24 is byte-identical
to the approved SD12b tip for all four files, and I rebuilt rather than trusted
it: `seat-eval`, `seat-vm` and `host-core` are green, `seat-vm` over the shipped
unit with `PrivateTmp = true;` at `nixosModules/seatLane.nix:231` and no
`ReadWritePaths` `/tmp` override anywhere — the only `/tmp` mentions in the VM
test are three comment lines. `unit` and `lint` are green on `--rebuild`, the MAP
and the task graph are unchanged and silent, one commit, subject byte-identical,
both trailers, no board commit, the plan untouched.

Six MINORs, none gating and none owed on this commit: two are the plan's own
seams (a `touches` list that omits a carry it mandates, and a "nothing else
changes" that forbids a comment it should have welcomed), one is the structural
board-block re-generation that has fired on every branch in this chain, and three
are carried notes already on the ledger.

`plan_defect: none`. The reported `scratch-probe.py` leaves no trace in the diff,
the tree, the history or the workspace; I found nothing.
