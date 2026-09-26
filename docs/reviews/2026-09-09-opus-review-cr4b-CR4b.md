---
plan_defect: none
mutants_total: 8
mutants_killed: 7
mutants_outside_named: 4
model: opus
---
# Opus gate — seat run cr4b, task CR4b — APPROVED

## Summary

The one thing that mattered is verified, by mutation and in both directions.
The Now-paragraph rule can now fail, and both named acceptance checks observe
the failure. Mutant A (`-gt` → `-ge`, the boundary the CR4 review showed
nothing could see) turns `checks.lint` red *and* `checks.unit` row 672 red.
Mutant B (the fold pipeline replaced by CR4's own raw `wc -l`) is killed by the
same two, on the 794-`x` single-physical-line fixture that is the shipped bug
reproduced. Dropping the new `cp docs/OPERATIONS.md` line from the `unit`
derivation makes bats row 673 FAIL on a missing file rather than pass
vacuously. And beyond the named set I restored the base's real, untrimmed
4,167-character Now paragraph into the committed tree: `checks.lint` prints
`53 wrapped lines at 80 columns` and refuses, `checks.unit` row 673 fails, and
`nix develop -c githooks/pre-commit` refuses — the exact content that read
`now_lines=1` and passed under CR4. The board trim is truthful, not merely
short: gen 48, `/run/current-system` stamped 2026-09-08 22:56 CDT, the
collector listening on 127.0.0.1:4318, `seat-spool.path` enabled, and
`system-47-link` present as the rollback — each checked against the live
filesystem. The runbook now matches `.claude/settings.json`, which I read
myself. Both MAJORs of the CR4 review are closed. Eight MINORs recorded, none
gating; the largest is that mutant C (the runbook sentence) is killed only by
a manual grep that is not committed anywhere. APPROVED.

## Contract items

Section `### CR4b (code, S)` of
`docs/superpowers/plans/2026-09-05-context-reset-ritual.md:329`, item by item.

1. **The measure is wrapped width, not physical newlines.** MET.
   `tests/lint/now-paragraph.sh` exists in the shape of its two named siblings
   (`[--self-test | FILE]`, `set -euo pipefail` at :17, project mode defaulting
   to `docs/OPERATIONS.md` at :105, fixture mode at :103). The extraction is
   the hook's `**OPEN`-to-blank-line walk (`:37-51`); the measure is
   `tests/lint/now-paragraph.sh:57`

   ```
   extract_now "$1" | LC_ALL=C fold -w 80 | wc -l
   ```

   which is the section's `printf '%s' "$text" | LC_ALL=C fold -w 80 | wc -l`
   with the `printf` inside `extract_now` (`:50`). Cap 10 at `:19`, boundary
   `[ "$n" -gt "$CAP" ]` at `:67`. The message at `:68` is byte-for-byte the
   section's:

   ```
   lint: START HERE's Now paragraph is $n wrapped lines at 80 columns (allowed at most 10) — rewrite it in ten wrapped lines or fewer (the Now paragraph opens **OPEN)
   ```

   The hook's block is a two-line comment plus two calls, self-test first, each
   on its own line, never joined by `&&`
   (`githooks/pre-commit:51-54`); `flake.nix:1053-1057` carries the identical
   two calls beside its board-shape block. `nix develop -c shellcheck
   tests/lint/now-paragraph.sh githooks/pre-commit` → exit 0, and the script is
   swept by both files' shellcheck passes (both `lint` builds green).
   File mode is 100644, matching the sibling `tests/lint/store-writers.sh`
   (also 100644); it is invoked via `bash`, so the bit is not load-bearing.

2. **Fixtures pin the boundary and reproduce CR4's exact bug.** MET.
   `tests/lint/now-paragraph.sh:74-101`: `printf '**OPEN %s\n'` with 793 and
   794 `x`'s — 7 + 793 = 800 bytes = exactly 10 folded lines (must pass) and
   801 bytes = 11 (must fail), each ONE physical line. `self_check` names which
   fixture misbehaved and how, and exits non-zero — both messages observed
   verbatim under mutants A and B below. The section says "returns non-zero";
   the implementation uses `exit 1` rather than `return`, which produces the
   same script exit status.

3. **A bats row under `unit` runs the rule against fixtures and the real
   board.** MET, and mutation-verified. `tests/unit/96-now-paragraph.bats:10`
   (self-test) and `:15` (the real board at
   `$BATS_TEST_DIRNAME/../../docs/OPERATIONS.md`), both via `bash`, in
   `92-ritual.bats`'s idiom. `flake.nix:2300-2302` adds
   `cp ${self}/docs/OPERATIONS.md docs/OPERATIONS.md` beside the ledger copy.
   Rows land as 672 and 673 and are green on the committed tree. Row (b) is RED
   against the carried, untrimmed board and against a dropped `cp` — both shown
   under "Mutants".

4. **The real Now paragraph is trimmed under the cap, same commit.** MET, and
   the four required facts are TRUE of the live system, not merely present.
   `docs/OPERATIONS.md:40` is 426 bytes / 6 wrapped lines (the base's was 4,167
   bytes / 53 wrapped lines). Checked against the host, read-only:

   ```
   $ readlink -f /run/current-system
   /nix/store/96wbiijw7fb1n4pqc8lw191i5cggdxzv-nixos-system-core-26.05.20260903.a5cc6f2
   $ ls -l /nix/var/nix/profiles/system-48-link
   ... -> /nix/store/96wbiijw7fb1n4pqc8lw191i5cggdxzv-...     # live gen = 48 ✓
   $ stat -c '%y' /run/current-system
   2026-09-08 22:56:42 -0500                                   # SWITCH #23 time ✓
   $ grep ':10DE' /proc/net/tcp
   1: 0100007F:10DE 00000000:0000 0A ...                       # 127.0.0.1:4318 LISTEN ✓
   $ ls /run/current-system/etc/systemd/system/ | grep -E 'seat-spool|opentelemetry'
   opentelemetry-collector.service
   seat-spool.path                                             # both in the live closure ✓
   $ ls -l /nix/var/nix/profiles/system-47-link
   ... -> /nix/store/3x0scfdk...                               # rollback target exists ✓
   ```

   The trim preserves the live generation and switch number, what is running,
   what the operator owns next (SD12b, then SWITCH #24, then
   `seat-drive.sh --port 43210`) and the rollback line. Only the Now paragraph
   changed; the derived Queued block is untouched by the commit.

5. **The runbook's self-contradiction.** MET, verified against
   `.claude/settings.json` read directly rather than against the section's
   three lines. settings.json registers
   `bash "$CLAUDE_PROJECT_DIR/tools/session-start.sh"` for `SessionStart`,
   `bash "$CLAUDE_PROJECT_DIR/tools/ritual.sh" precompact` for `PreCompact`,
   and `bash "$CLAUDE_PROJECT_DIR/tools/ritual.sh" stop` for `Stop`.
   `docs/runbooks/session.md:158-161` now reads "Two of the three hooks share
   one script, `tools/ritual.sh <subcommand> <repo>` — Stop and PreCompact;
   SessionStart is the separate `tools/session-start.sh`, which calls the
   ritual script's `inflight` subcommand as one internal step … a helper call,
   not a hook registration." That matches command for command, and `:176`
   ("**SessionStart** (`tools/session-start.sh`)") is now the sentence's
   agreement rather than its contradiction.
   `grep -c 'All three are one script' docs/runbooks/session.md` → `0`;
   `grep -q 'Two of the three hooks share one script' …` → exit 0.

6. **The commit body.** MET on every listed paste: row 3(b) red with the exact
   `53 wrapped lines` line and green after the trim; mutants A and B on the
   self-test, one at a time, each red then reverted; `lint` and `unit` red
   under mutant A on the committed script then green after revert; item 5's two
   greps red then green; the final green run of `lint`, `unit` and
   `githooks/pre-commit`; `FACTORY-CHECKS lint=pass unit=pass` and
   `FACTORY-COMMITS 1` in the stated grammar. Every red I could re-run
   reproduced (see below). The single unreproducible line is
   `githooks/pre-commit -> exit 0`, for the structural reason in MINOR-6.

**The CR4 review's items, one by one**
(`docs/reviews/2026-09-08-opus-review-cr4-CR4.md`):

- **MAJOR-1** (the rule counts raw newlines, is a no-op on the real board, and
  `checks.lint` cannot observe a boundary mutation): **CLOSED**, and closed at
  all three points — the measure (mutant B dies), the board (the real 4,167-byte
  paragraph now refuses in both checks and in the hook), and the observability
  (mutant A dies in `lint` and in `unit`).
- **MAJOR-2** (`session.md:158` self-contradiction): **CLOSED**, verified
  against `.claude/settings.json` itself.
- **MINOR-1** (`RITUAL_BOARD_DEBT`·6 middot): **NOT closed** — still at
  `docs/runbooks/session.md:173`. The CR4b section does not carry it. Recorded
  again as MINOR-1 below.
- **MINOR-2** (the body narrates red/green instead of pasting it): **CLOSED** —
  the body pastes literal command output for every required red and green.

## Red before green

The base has no implementation file at all (CR4 never landed on `main`), so the
section's stated reds are the discriminating ones and I ran each myself in the
fresh clone.

**The real board, untrimmed (the section's red-before-green for content):**

```
$ git show 3a461b1:docs/OPERATIONS.md > /tmp/.../base-OPERATIONS.md
$ bash tests/lint/now-paragraph.sh /tmp/.../base-OPERATIONS.md
lint: START HERE's Now paragraph is 53 wrapped lines at 80 columns (allowed at most 10) — rewrite it in ten wrapped lines or fewer (the Now paragraph opens **OPEN)
RED_EXIT=1
$ git show 3a461b1:docs/OPERATIONS.md | grep '^\*\*OPEN' | wc -c
4167
```

Green on the committed board:

```
$ bash tests/lint/now-paragraph.sh docs/OPERATIONS.md
check exit=0            # 6 wrapped lines
```

**The same content through both callers** (I substituted the base's Now
paragraph into the committed tree, line count unchanged at 57):

```
$ nix build .#checks.x86_64-linux.lint -L --no-link
lint> lint: START HERE's Now paragraph is 53 wrapped lines at 80 columns (allowed at most 10) — …
error: Cannot build '/nix/store/9akmqq9d5zpk368nc63pflrmyvyc4p6k-lint.drv'.
BLOAT_LINT=1

$ nix build .#checks.x86_64-linux.unit -L --no-link
unit-tests> ok 672 now-paragraph self-test passes against its boundary fixtures
unit-tests> not ok 673 now-paragraph accepts the real board's Now paragraph
BLOAT_UNIT=1

$ nix develop -c githooks/pre-commit
lint: START HERE's Now paragraph is 53 wrapped lines at 80 columns (allowed at most 10) — …
HOOK_EXIT=1
```

Reverted; tree byte-identical to HEAD afterwards (`git status --short` empty,
HEAD `667edcc8`).

**Item 5's greps** — red on CR4's wording (mutant C below), green on the
committed text.

## Mutants

Named by the section: **A**, **B**, the **dropped-`cp`** mutant of item 3, and
**C**. Each applied in the fresh clone, `git add` before every `nix build`,
reverted before the next.

**A — `tests/lint/now-paragraph.sh:67`, `-gt "$CAP"` → `-ge "$CAP"`. KILLED,
in both named acceptance checks.** This is the mutant the CR4 review showed
nothing could observe.

```
$ bash tests/lint/now-paragraph.sh --self-test
lint: START HERE's Now paragraph is 10 wrapped lines at 80 columns (allowed at most 10) — …
now-paragraph: self-test: the 793-x fixture (10 folded lines) was rejected
SELFTEST_EXIT=1

$ nix build .#checks.x86_64-linux.lint -L --no-link
lint> now-paragraph: self-test: the 793-x fixture (10 folded lines) was rejected
error: Cannot build '/nix/store/81h101c2k02za3682m0wia0qa4m8r4hk-lint.drv'.
MUTANT_A_LINT_EXIT=1

$ nix build .#checks.x86_64-linux.unit -L --no-link
unit-tests> not ok 672 now-paragraph self-test passes against its boundary fixtures
unit-tests> # (in test file tests/unit/96-now-paragraph.bats, line 12)
error: Cannot build '/nix/store/0q5sbz2vl95p5gylzl0lcpzcrhljyayd-unit-tests.drv'.
MUTANT_A_UNIT_EXIT=1
```

(`--rebuild` cannot be used on a mutated tree — the mutated derivation has
never been built, and nix answers `--rebuild and --check error if the
derivation was not previously built`. The unmutated branch was run with
`--rebuild`; see "Checks".)

**B — `:57`, the fold pipeline replaced by CR4's own algorithm
(`extract_now "$1" | wc -l`, raw physical newlines). KILLED, in both.** The
794-`x` single-physical-line fixture is the shipped bug and mutant B does not
survive it.

```
$ bash tests/lint/now-paragraph.sh --self-test
now-paragraph: self-test: the 794-x fixture (11 folded lines) passed; the cap is vacuous
SELFTEST_EXIT=1

$ nix build .#checks.x86_64-linux.lint -L --no-link
lint> now-paragraph: self-test: the 794-x fixture (11 folded lines) passed; the cap is vacuous
error: Cannot build '/nix/store/wxid25sdr195n1cac45pbcyn7ankcgrf-lint.drv'.
MB_LINT=1

$ nix build .#checks.x86_64-linux.unit -L --no-link
unit-tests> not ok 672 now-paragraph self-test passes against its boundary fixtures
error: Cannot build '/nix/store/pxczfyapfikzc5dvvp6fbhj6hywv9ki6-unit-tests.drv'.
MB_UNIT=1
```

**Dropped `cp` — `flake.nix:2302`, the `cp ${self}/docs/OPERATIONS.md
docs/OPERATIONS.md` line deleted. KILLED.** Row 673 fails on the missing file;
it does not skip and it does not pass vacuously.

```
$ nix build .#checks.x86_64-linux.unit -L --no-link
unit-tests> ok 672 now-paragraph self-test passes against its boundary fixtures
unit-tests> not ok 673 now-paragraph accepts the real board's Now paragraph
error: Cannot build '/nix/store/ys57xpyblii0x131nqxiizmbb0d4xb92-unit-tests.drv'.
MC_UNIT=1

$ nix log …-unit-tests.drv | grep -A3 'not ok 673'
not ok 673 now-paragraph accepts the real board's Now paragraph
# (in test file tests/unit/96-now-paragraph.bats, line 17)
#   `[ "$status" -eq 0 ]' failed
```

(The script's own missing-file guard, `tests/lint/now-paragraph.sh:61-64`, is
what returns 1 there.)

**C — `docs/runbooks/session.md:158` reverted to CR4's "All three are one
script". KILLED by its named test only.**

```
$ grep -c 'All three are one script' docs/runbooks/session.md
1                                          # was 0
$ grep -q 'Two of the three hooks share one script' docs/runbooks/session.md
grep-new exit=1                            # was 0
$ nix build .#checks.x86_64-linux.lint -L --no-link
MC_LINT=0                                  # no acceptance check observes it
```

The greps flip exactly as the section says, so the mutant dies against the test
the section names — but that test lives only in the commit body, not in the
tree. See MINOR-5.

**Outside the named set (4):**

- **D — `:19`, `CAP=10` → `CAP=11`. KILLED.**
  `now-paragraph: self-test: the 794-x fixture (11 folded lines) passed; the
  cap is vacuous` (exit 1).
- **E — `:42`, the anchor `^\*\*OPEN` → `^\*\*OPENX`. KILLED.** Extraction
  yields nothing, both fixtures read 0, and the self-test refuses:
  `the 794-x fixture (11 folded lines) passed; the cap is vacuous` (exit 1).
- **F — the real, untrimmed 4,167-byte Now paragraph restored into the
  committed tree. KILLED, three times over**: `checks.lint` red, `checks.unit`
  row 673 red, `githooks/pre-commit` red (output pasted under "Red before
  green"). This is the mutant that matters most: the exact content that passed
  under CR4 now refuses at every caller.
- **G — `:57`, `LC_ALL=C` removed. SURVIVED.** `--self-test` exit 0 and
  `docs/OPERATIONS.md` exit 0 with the flag gone. Recorded as MINOR-3; not
  named by the section and not a behaviour change on ASCII fixtures.

mutants_total: 8; mutants_killed: 7; mutants_outside_named: 4.

## Checks

In the fresh clone `/tmp/…/gate-cr4b-CR4b`, `XDG_CACHE_HOME` under the
scratch dir, every command through `nix develop`.

- `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` → **exit 0**.
- `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` → **exit 0** on
  the third run, with `ok 672` and `ok 673`. Two earlier sandbox runs failed on
  an unrelated, timing-sensitive row —
  `not ok 645 a timed-out probe reads not-run with verify-timeout, and D5
  precedence holds` (`tests/unit/94-seat-harness.bats:2118`). I proved it is
  not this commit's: the same row fails at the base `3a461b1` in the same
  sandbox, passes in `nix develop -c bats -f 'timed-out probe'`, and passed in
  four of the six sandbox builds of this tree. MINOR-7.
- `nix develop -c githooks/pre-commit` → exit 1 in a fresh clone, on the
  derived queue block only:
  `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated —
  git add docs/OPERATIONS.md and commit again`. The regeneration's whole diff is
  the removal of `CR4b` from the Queued list, which is caused by this very
  commit being in the log (`pkgs/evidence/tasks.py:832`, `landed_subjects`).
  The base is clean (`BASE_PRECOMMIT=0`). MINOR-6, and the Global Constraints'
  documented recipe applies at integration.
- `nix develop -c shellcheck tests/lint/now-paragraph.sh githooks/pre-commit` →
  exit 0.
- `nix develop -c bats tests/unit/96-now-paragraph.bats tests/unit/92-ritual.bats`
  → exit 0.
- `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then
  `git diff --exit-code docs/MAP.md` → **exit 0**, no drift (the commit already
  carries `tests/lint — 12 files` / `tests/unit — 27 files`).
- `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → silent,
  exit 0.
- No Python touched; `ruff` not applicable.

## Touches and commit

- `git diff 3a461b1..HEAD --stat`: `CLAUDE.md`, `docs/MAP.md`,
  `docs/OPERATIONS.md`, `docs/runbooks/session.md`, `flake.nix`,
  `githooks/pre-commit`, `tests/lint/now-paragraph.sh`,
  `tests/unit/96-now-paragraph.bats`. Every file is in the section's list
  (`docs/MAP.md` by rule). No stray file.
- Exactly one commit, `667edcc8`.
- Subject byte-identical to the section's — compared with `cmp` against the
  string extracted from the plan file, not by eye: `SUBJECT_IDENTICAL`.
- Trailers present after a blank line:
  `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless,
  factory run cr4b)` and
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- No board-only commit; the plan file is untouched (0 lines in its diff against
  the base).

## Findings

**MINOR-1** — `docs/runbooks/session.md:173`: the CR4 review's MINOR-1 is not
closed. "board debt (≥ `RITUAL_BOARD_DEBT`·6 landings/gates since the board was
written)" still uses a middot where the next line uses the parenthetical
default (`RITUAL_MAX_BLOCKS` (2)); the real threshold is
`${RITUAL_BOARD_DEBT:-6}`. The CR4b section does not carry this item, so it is
recorded, not charged to the seat.

**MINOR-2** — `docs/runbooks/session.md:187` (and `:144`): the runbook still
says the lint "keeps the Now paragraph to ten lines (`githooks/pre-commit`)"
and step 7 still says "(≤10 lines)". After this commit the measure is ten
*wrapped* lines at 80 columns and the rule lives in
`tests/lint/now-paragraph.sh`, called from `githooks/pre-commit:53-54` **and**
`flake.nix:1056-1057`. A reader of the runbook — the file this task exists to
write — is told the rule runs in one place when it runs in two, and is given
the superseded unit of measure. Not gating; the section did not ask for these
two lines.

**MINOR-3** — `tests/lint/now-paragraph.sh:57`: `LC_ALL=C` is a stated contract
of item 1 ("pins the count to bytes so it never depends on the caller's
`LANG`") with no test. Removing it leaves both `--self-test` (exit 0) and the
real board (exit 0) green — mutant G survives. The fixtures are pure ASCII, so
nothing in the tree distinguishes byte counting from character counting; the
real board's em dashes would count differently but stay far under the cap.

**MINOR-4** — `tests/lint/now-paragraph.sh:21-27`: the documented exit code 2
("a measuring tool is missing from PATH") is never exercised. A stated error
contract with no test.

**MINOR-5** — item 5's "new test" is not in the tree.
`grep -c 'All three are one script' docs/runbooks/session.md` → 0 and the
positive grep are named by the section as the test for MAJOR-2, and they do
discriminate (mutant C flips both), but they are committed only as prose in the
commit body. No bats row, no `tests/lint/` rule and no acceptance check
observes mutant C — `checks.lint` stayed exit 0 with CR4's false sentence
restored. The correction is real and verified; nothing stops it regressing.

**MINOR-6** — `docs/OPERATIONS.md:22` (the derived Queued block): the branch as
committed leaves the block stale, so `nix develop -c githooks/pre-commit` is
exit 1 in a fresh clone while the base is exit 0. The cause is structural, not
carelessness: `pkgs/evidence/tasks.py:832` judges a task landed by its commit
subject appearing in the git log, so CR4b drops out of the queue the instant
its own commit exists — regenerating before committing would have produced a
block stale in the other direction, and the section demands exactly one commit.
The Global Constraints' recipe ("it may regenerate the board block once:
`git add docs/OPERATIONS.md` and commit again") applies at integration. The
commit body's `githooks/pre-commit -> exit 0` was true when the seat ran it and
is not reproducible afterwards.

**MINOR-7** (process, not this task's) —
`tests/unit/94-seat-harness.bats:2118`: row 645, "a timed-out probe reads
not-run with verify-timeout, and D5 precedence holds", is flaky in the
`checks.unit` sandbox on this host. It failed at HEAD, failed identically at
the base `3a461b1`, passed in `nix develop -c bats -f 'timed-out probe'`, and
passed in four of six sandbox builds of this same tree. It uses
`FACTORY_VERIFY_TIMEOUT=1` against a `sleep 60` probe, so it is load-sensitive
by construction. Not caused by CR4b; worth its own task, because it makes the
`unit` acceptance check non-deterministic for every gate that follows.

**MINOR-8** — `tests/lint/now-paragraph.sh:37-51`: the cap is evadable by two
edits the rule cannot see, both inherited from the extraction the section
explicitly mandates ("keeps the exact `**OPEN`-to-blank-line extraction the
hook already does"). Measured on the base's real 4,167-character paragraph:

```
# split by one blank line into two paragraphs
$ bash tests/lint/now-paragraph.sh /tmp/.../evade.md
SPLIT_EVASION_EXIT=0
# the same text under a different heading (**NOW. instead of **OPEN)
$ bash tests/lint/now-paragraph.sh /tmp/.../rename.md
RENAME_EXIT=0
```

Plan-level residual, not implementer: the section chose the extraction. Worth a
line in a future task if the cap is meant to bind the whole Now section rather
than its first paragraph.

## Verdict

**APPROVED.** No MAJORs. The section's four named mutants all die — three of
them inside the two named acceptance checks, and the fourth (C) against the
grep test the section names. The question this round existed to answer is
answered in the affirmative and by mutation, not by reading: the rule can fail,
and `checks.lint`, `checks.unit` and `githooks/pre-commit` all observe the
failure, including on the real 4,167-character board content that defeated
CR4. The board trim is truthful against the live host, the runbook matches
`.claude/settings.json` command for command, the touches are exactly the
section's list, and the commit is one commit with a byte-identical subject and
both trailers. `plan_defect: none`.
