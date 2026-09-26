---
plan_defect: none
mutants_total: 5
mutants_killed: 5
mutants_outside_named: 0
model: sonnet
---
# Opus gate — seat run sd11c, task SD11c — APPROVED

## Summary

Fresh clone of `task/SD11c` at `e36b962` (base `81c5925`) in
`/tmp/.../scratch/SD11c/gate-sd11c-SD11c` (dsh-harness, no flake — the gate
is the section's literal commands). One commit, carrying SD11b's `70aed01`
uncommitted with no further content edit — `git diff FETCH_HEAD..HEAD`
against `70aed01` (fetched from
`/home/dalhaka/factory/ws/sd11b/SD11b task/SD11b`) is **empty**, confirming
"the carried commit's content unchanged" exactly as the section and the
orchestrator state.

SD11c's whole and only job is gate (6)'s correction: SD11b's review
(`docs/reviews/2026-09-08-opus-review-sd11b-SD11b.md`) rejected on a plan
defect — the whole-file count `grep -c -E '^- \`[0-4]\` — '
skills/driving/references/verbs.md` printed `12`, not `5`, because
`factory-review`'s and `factory-dispatch`'s own exit-code bullet lists share
the same `` - `N` — `` format. SD11c's section scopes the count to the
`## factory-task` section with an `awk` filter; I measured it at `5` on HEAD
and confirmed by direct measurement that it is unchanged from SD11's
original text at `c25e71f` (also `5` when scoped) — so, as the section
states, no implementation content was owed, only the corrected gate. All
five named mutants (A, B, B2, C, D) kill under the corrected gate; the three
`-q` greps reproduce their reds against `c25e71f` and their greens on HEAD;
`grep-gate` and `node-test` (98/98) are both green. One commit, subject
byte-identical, touches exact, body pastes the reds/greens and the mutant
table. No MAJORs, no MINORs found. Approved.

## Contract items

1. **Gate (6), corrected — met.**
   `awk '/^## factory-task$/{f=1;next} /^## /{f=0} f'
   skills/driving/references/verbs.md | grep -c -E '^- \`[0-4]\` — '`
   measured `5` on HEAD. Measured the same scoped command against
   `c25e71f` (the carried SD11 text, fetched from
   `/home/dalhaka/factory/ws/sd11/SD11 task/SD11`): also `5` — confirming
   the section's claim that the count is the section's five codes and does
   not move between `c25e71f` and this commit. The three `-q` greps are
   unchanged and green on HEAD:
   `grep -q '^- \`2\` — \`failed\`'` → exit 0;
   `grep -q '^- \`3\` — an unrecognised status word'` → exit 0;
   `grep -q '^- \`0\` — \`done\`, and \`unreported\`'` → exit 0.
   Their reds are shown on `c25e71f` exactly as the section specifies —
   all three exit `1` there (measured directly via
   `git show c25e71f:skills/driving/references/verbs.md | grep -q …`).
2. **Nothing else changes — met.** `git diff FETCH_HEAD..HEAD` (`FETCH_HEAD`
   = SD11b's `70aed01`) is empty: the file content, `SKILL.md`, `README.md`,
   `AGENTS.md`, `CHANGELOG.md` are byte-for-byte the same as the
   already-verified-correct SD11b commit. Gates (1)–(5), (7), (8) reconfirmed
   green (see Checks); items 1–4 of SD11b (the exit-code table, the
   integrate paragraph, the usage line, the CHANGELOG clause) stand
   unchanged, as the prior review already verified them line for line.

## Red before green

**Gate (6)'s three `-q` greps**, against `c25e71f` (before) and HEAD
(after):
```
$ git show c25e71f:skills/driving/references/verbs.md | grep -q '^- `2` — `failed`'; echo $?
1
$ git show c25e71f:skills/driving/references/verbs.md | grep -q '^- `3` — an unrecognised status word'; echo $?
1
$ git show c25e71f:skills/driving/references/verbs.md | grep -q '^- `0` — `done`, and `unreported`'; echo $?
1
$ grep -q '^- `2` — `failed`' skills/driving/references/verbs.md; echo $?      # HEAD
0
$ grep -q '^- `3` — an unrecognised status word' skills/driving/references/verbs.md; echo $?  # HEAD
0
$ grep -q '^- `0` — `done`, and `unreported`' skills/driving/references/verbs.md; echo $?  # HEAD
0
```
**Gate (6)'s corrected count**, unchanged between `c25e71f` and HEAD (as the
section claims — no red/green pair to show since the fix is scoping, not
content):
```
$ awk '/^## factory-task$/{f=1;next} /^## /{f=0} f' skills/driving/references/verbs.md | grep -c -E '^- `[0-4]` — '
5   # both on c25e71f and on HEAD
```
Gates (1)–(5), (7), (8) were already shown red-before-green by the SD11 and
SD11b reviews and are unaffected by this task's empty content diff; I
reconfirmed all green on HEAD (see Checks).

## Mutants

| # | mutant | died? | evidence |
|---|---|---|---|
| A | `2`/`3` lines swapped back to the old wording | **yes** | both `-q` greps exit 1 |
| B | a sixth line `` - `3` — a second meaning `` appended inside `## factory-task` | **yes** | scoped count prints `6` |
| B2 | the `` - `4` — … `` line deleted | **yes** | scoped count prints `4` |
| C | old inverted integrate sentence restored | **yes** | `grep -c 'runs the gate only when it sees'` prints `1`; `-q` grep for the correct sentence exits `1` |
| D | `[--fallback]` dropped from the usage line | **yes** | `grep -qF '[--prior <run>/<KEY>] [--rung N] [--fallback]'` exits `1` |

Each mutant applied via `sed`/`perl -0777` in the working clone against the
scoped or literal gate command, the failing output pasted above, then
`skills/driving/references/verbs.md` restored from a saved copy
(`git status --short` clean before and after each). `mutants_total: 5`,
`mutants_killed: 5`, `mutants_outside_named: 0` — B (a `` - `3` `` duplicate)
and B2 (deleting the `4` line) are the two mutants this section names as
new; A, C, D are SD11b's, re-verified unaffected by the scoping fix.

## Checks

Both acceptance names run as the section's literal commands (no flake in
this repo — Orchestrator note):

- **grep-gate** — (1) `test -f skills/driving/SKILL.md` → exit 0. (2) the
  whole-tree model-choice grep → prints nothing. (3) the tier-word grep
  under `skills/driving` → prints nothing. (4)
  `grep -c '^name: driving$' skills/driving/SKILL.md` → `1`. (6) the
  corrected scoped count → `5`; the three `-q` greps → all exit 0. (7)
  `grep -c 'runs the gate only when it sees'` → `0`;
  `grep -q 'runs \`factory-integrate\` only after'` → exit 0. (8)
  `grep -qF '[--prior <run>/<KEY>] [--rung N] [--fallback]'` → exit 0. All
  green.
- **node-test** — `nix develop /home/dalhaka/nixos-agent-env -c node --test
  archive/2026-09-05-planning-factory/tests/*.test.mjs` →
  `tests 98 / pass 98 / fail 0`. Green.

No `githooks/pre-commit`, `ruff`, `repomap.py write`, or `tasks.py check`
run: this repo ships no `flake.nix` or `githooks/` (confirmed —
`ls flake.nix` and `ls githooks/pre-commit` both fail), and this task
touches no file inside `~/nixos-agent-env` (`git status --short` there is
clean before and after this review; only the review file itself is
written), matching the SD11/SD11b Orchestrator scoping.

## Touches and commit

`git diff --name-only 81c5925..HEAD`:
```
AGENTS.md
CHANGELOG.md
README.md
skills/driving/SKILL.md
skills/driving/references/verbs.md
```
Exactly the section's touches list, five files, no file outside it.

One commit, `e36b962` on `81c5925`. Subject diffed byte-for-byte against
the section's `**commit subject:**` (identical to SD11's and SD11b's,
unchanged): `docs: the driving skill — brief, dispatch, gate and integrate
as calls to the seat driver, what the driver decides alone, the rung read
from the key; the model-choice gate still prints nothing (test: grep-gate,
node-test)` — matches exactly (`diff` of the two strings, zero output).
Body states the why (SD11b's MAJOR in one line: the whole-file count was
the plan's error; the section count is `5`), pastes gate (6)'s three reds
and the scoped-count green, gate (7)'s and gate (8)'s counts, and the
mutant table A/B/B2/C/D with each killing line. Trailers after a blank
line, in order: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813
(seat headless, factory run sd11c)` then `Co-Authored-By: Claude Fable 5.1
<noreply@anthropic.com>`. No board commit; the plan file
(`docs/superpowers/plans/2026-09-06-seat-driver.md`) untouched by this task
(it exists only in `~/nixos-agent-env`, never copied into this dsh-harness
clone).

## Findings

None. No MAJORs, no MINORs.

## Verdict

APPROVED. SD11c's section correctly diagnosed and fixed the prior round's
plan defect — gate (6)'s count was a whole-file assertion that could never
print `5` because two other, already-approved sections of the same file
share the exact bullet format; scoping the count to the `## factory-task`
section with `awk` makes it `5`, unchanged between `c25e71f` and HEAD as
claimed, and both new mutants (B: a duplicate `3` line inside the class; B2:
deleting the `4` line) discriminate correctly where the old whole-file
mutant B could not. The carried content is verified byte-identical to
SD11b's already-reviewed `70aed01` (`git diff FETCH_HEAD..HEAD` empty) —
SD11b's four fix items (the exit-code table, the integrate paragraph, the
usage line, the CHANGELOG clause) stand as previously verified. Both
acceptance checks (`grep-gate`, `node-test`) are green; the commit is
singular, subject byte-identical, touches exact, body complete.
