---
plan_defect: implementer
plan_defect_secondary: vacuous
mutants_total: 1
mutants_killed: 0
mutants_outside_named: 1
model: sonnet
---
# Opus gate — seat run cr4, task CR4 — REJECTED

## Summary

The seat's three touched files match the section's list exactly, the commit
is a single byte-identical-subject commit with both trailers, `docs/MAP.md`
does not drift, and the full `nix develop -c githooks/pre-commit` gate passes
clean on the branch. But the delivered mechanism does not do what the section
and the seat's own commit body claim: the "Now paragraph ≤ 10 lines" check
counts raw physical newlines in `docs/OPERATIONS.md`, and this repository's
own Now paragraph — the very content the rule exists to police — is written
as a single unwrapped physical line. Run against the real board at this
commit, the new rule reports `now_lines=1` and passes, regardless of how many
thousands of characters the paragraph holds. This is the "lint rule that
cannot fail" defect class the orchestrator named, demonstrated directly, not
hypothetically. Separately, the new runbook section contradicts itself:
`docs/runbooks/session.md:158` says all three hooks are "one script,
`tools/ritual.sh <subcommand> <repo>`," but `docs/runbooks/session.md:176`
(same section) correctly names `tools/session-start.sh` as the SessionStart
hook's script, and `.claude/settings.json` confirms it. Both are MAJORs;
REJECTED.

## Contract items

Section: `### CR4 (code, XS)` — files, in the section's own wording.

1. **`githooks/pre-commit`: Now paragraph ≤ 10 lines, message names the
   rule.** Present as a real check (`githooks/pre-commit:51-76`) and the
   error message names "Now paragraph" and the 10-line cap
   (`githooks/pre-commit:74`). Mechanically correct as a line-counter. **Not
   met** as a check that enforces the stated purpose ("so the next session
   can read it at a glance," `githooks/pre-commit:54`) — see MAJOR-1: it
   never fires against this repo's actual Now-paragraph convention.
2. **`docs/runbooks/session.md`, section "The reset ritual": the ten steps,
   the three hooks and their reasons, the override, when to `/new`.** All
   five sub-sections present (`docs/runbooks/session.md:112-208`): "The ten
   ordered steps" (10 numbered items, lines 122-146), "The three hooks and
   their reasons" (lines 148-181), "The override" (lines 183-190), "When to
   `/new`" (lines 192-207). **Not met** on command-for-command accuracy — see
   MAJOR-2.
3. **`CLAUDE.md`: one line under "How work is done here," text given
   verbatim in the section.** Present verbatim at `CLAUDE.md:69-70`: "Before
   any reset — compaction, `/new`, a pause — run the ritual:
   `docs/runbooks/session.md`; the Stop hook enforces the derived half." Met.
4. **Lint test red on an 11-line fixture first.** The mechanism itself does
   discriminate 10 vs. 11 *physical* lines when I built the fixtures by
   hand (below, "Red before green") — but no fixture or test survives in the
   tree, so this is unverifiable from the repo and, per MAJOR-1, is not the
   test that matters (a physical-line fixture is not what the real board
   looks like).

## Red before green

The section names no fixture file; I built the fixtures myself in a scratch
copy of `docs/OPERATIONS.md` (11 hard-wrapped physical lines in the `**OPEN`
paragraph, then 10) and ran the actual `nix develop -c githooks/pre-commit`
gate against each:

```
=== 11-line fixture ===
lint: START HERE's Now paragraph is 11 lines (allowed at most 10) — rewrite it
in ten lines or fewer (the Now paragraph opens **OPEN)
exit 1

=== 10-line fixture ===
(no Now-paragraph line printed) — passes
```

So the counting mechanism itself is not broken: given content that is
actually broken into 11 physical lines, it blocks; at 10, it allows. The
defect is that real board content is never broken into physical lines this
way. Running the *unmodified*, real `docs/OPERATIONS.md` from this exact
commit through the identical check:

```
$ bash run_check.sh docs/OPERATIONS.md
now_lines=1
PASS
```

The real `**OPEN` paragraph (`docs/OPERATIONS.md:40`) is one physical line
of roughly 4,000 characters — the entire Now paragraph, unwrapped — and the
check reports exactly 1 line. There is no line count at which this
paragraph, as actually written by this repo's own convention, would ever
trip the rule.

## Mutants

The section names no mutants for CR4 (unlike CR1b's `(mutation: …)`
annotations elsewhere in the plan file). I applied one boundary mutant to
probe whether the named acceptance check (`lint`) would catch a regression
in the rule's own logic:

- **Mutant: `githooks/pre-commit:73`, `-gt "$now_now_max"` → `-ge
  "$now_now_max"`** (off-by-one: blocks at 10 lines instead of 11). Applied
  in the scratch copy, then ran the section's named acceptance check:

  ```
  $ nix build .#checks.x86_64-linux.lint -L --no-link   # mutant applied
  ...
  Found 0 warnings and 0 errors.
  ... (all files pass) ...
  LINT_EXIT=0
  ```

  The mutant survives. Reason: `checks.lint` (`flake.nix:1007`) is a
  `runCommand` that shellchecks/treefmt/eslints the tree — it never executes
  `githooks/pre-commit` against real repo content, so it cannot observe any
  behavior change in the Now-paragraph rule at all, on top of the rule
  itself being a no-op against the real board (above). Reverted; working
  tree confirmed byte-identical to `HEAD` afterward.

mutants_total: 1, mutants_killed: 0, mutants_outside_named: 1 (the section
named none).

## Checks

- `nix develop -c githooks/pre-commit` (full gate, in the devShell, in the
  clone): pass on the second run (first run regenerated the pre-existing,
  unrelated stale queue block in `docs/OPERATIONS.md`, per the repo's own
  documented gotcha; reverted before further testing).
- `nix build .#checks.x86_64-linux.lint -L --no-link`: pass (`LINT_EXIT=0`
  on the unmodified branch).
- `python3 pkgs/evidence/repomap.py --root . write` then `git diff
  --exit-code docs/MAP.md`: no drift (`MAP diff exit=0`).
- `nix develop -c python3 pkgs/evidence/tasks.py --root . check`: silent,
  exit 0.
- No Python files touched; ruff not applicable.

## Touches and commit

- Touches: `CLAUDE.md`, `docs/runbooks/session.md`, `githooks/pre-commit` —
  exactly the section's list, confirmed by `git diff --stat` against the
  merge-base. No stray files.
- Exactly one commit (`5b375aa`). Subject byte-identical to the section's
  (`docs: the reset ritual runbook; START HERE's Now paragraph is capped at
  ten lines; CLAUDE.md points at the ritual (test: lint)` — verified with a
  string-equality check, not eyeballing).
- Trailers present after a blank line: `Generated-By: dsh 0.1.2-rc.1 /
  deepseek/deepseek-v4-flash …` and `Co-Authored-By: Claude Fable 5.1
  <noreply@anthropic.com>`.
- No board commit; `docs/superpowers/plans/2026-09-05-context-reset-ritual.md`
  untouched (0 lines in its diff against the base).
- Body states the "why" at length but does not literally paste red/green
  command output — it narrates ("It is red on an 11-line Now fixture and
  green on a 10-line one (TDD)") rather than including the actual failing
  and passing text. See MINOR-1.

## Findings

**MAJOR-1** — `githooks/pre-commit:51-76`: the Now-paragraph check counts
physical newlines in the file, which is not a meaningful proxy for the
prose length the rule exists to bound, and is demonstrably a no-op against
this repository's actual convention.

Failure scenario: `docs/OPERATIONS.md:40` (the real board, unmodified, at
this commit) holds the entire Now paragraph as one physical line of ~4,000
characters — far more than "the next session can read at a glance"
(`githooks/pre-commit:54`, the rule's own stated purpose) — yet the check
computes `now_lines=1` and allows the commit. Conversely, a legitimately
short Now paragraph that a human or an editor happens to hard-wrap across 11
physical lines blocks the commit with no escape hatch: `.claude/
ritual-override` (the escape hatch the runbook documents, `docs/runbooks/
session.md:183-190`) is read only by `tools/ritual.sh`'s Stop/PreCompact
paths and by `tools/session-start.sh`; `githooks/pre-commit` never checks
for it (`grep -n override githooks/pre-commit` is empty). So the only
recourse for a legitimate 11th line is to manually rejoin lines (undocumented)
or bypass the lint gate outright, which `CLAUDE.md`'s own house rules forbid
("never skip hooks"). The mutant in "Mutants" above shows the situation is
worse than an edge case: the section's one named acceptance check (`lint`)
cannot observe any change to this rule's behavior at all, because it never
runs the hook against real content.

**MAJOR-2** — `docs/runbooks/session.md:158`: "All three are one script,
`tools/ritual.sh <subcommand> <repo>`" is false for SessionStart.

Failure scenario: a future session reads this runbook — which is exactly
what `CLAUDE.md`'s new line (`CLAUDE.md:69-70`) and the SessionStart hook
itself (`tools/session-start.sh:1-4`, "Where everything is: docs/runbooks/
session.md") point it at — to understand which script implements which
hook, and is told all three hooks live in `tools/ritual.sh`. In fact
`.claude/settings.json` registers `tools/session-start.sh` for
`SessionStart` and `tools/ritual.sh precompact`/`tools/ritual.sh stop` for
the other two; `tools/session-start.sh` merely *calls* `bash "$ritual"
inflight` as one internal helper. The very next bullet in the same
subsection, `docs/runbooks/session.md:176`, correctly says "**SessionStart**
(`tools/session-start.sh`)" — so the section contradicts itself four lines
of prose apart. This is precisely the class of error the orchestrator asked
to be checked for (item c: "does the runbook section describe what the hook
actually does, command for command").

**MINOR-1** — `docs/runbooks/session.md:170`: "`RITUAL_BOARD_DEBT`·6
landings/gates since the board was written" uses a middot where the
sibling item one line below uses parenthetical-default notation
(`RITUAL_MAX_BLOCKS` (2)`, line 171). The actual threshold is
`${RITUAL_BOARD_DEBT:-6}` (default 6, not `RITUAL_BOARD_DEBT × 6`); the
middot notation is ambiguous enough to be misread as multiplication. Record,
not gating.

**MINOR-2** — commit body: states the why at length but does not paste the
actual red/green output (it narrates "It is red on an 11-line Now fixture
and green on a 10-line one (TDD)" rather than including literal command
output), and no fixture or test for this survives in the tree, so the claim
is unverifiable from the repository alone. I reproduced red/green myself
(see "Red before green") and it holds for the counting mechanism, but this
is not what the commit body itself provides.

## Verdict

REJECTED — two MAJORs. MAJOR-1 (`githooks/pre-commit:51-76`) is the
substantive one: the delivered check does not perform the function the
section, the code comment, and the commit body all claim, is demonstrably a
no-op against the actual board content in this very commit, and the
section's own named acceptance check (`lint`) cannot detect a mutation of
its boundary condition either. MAJOR-2 (`docs/runbooks/session.md:158`) is a
direct, self-contradicted factual error in the exact runbook section this
task exists to write, in a file every future session is now pointed at from
`CLAUDE.md`. `plan_defect: implementer` (the CR4 section specifies a plain
line cap and a message that names the rule; nothing in the section requires
counting raw physical newlines or forecloses validating the rule against the
board it will govern, and the seat had that board open in the same repo);
secondary `vacuous`, since the resulting check is the specific "cannot fail"
defect class this record tracks.
