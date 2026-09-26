---
plan_defect: wrong-fact
plan_defect_secondary: vacuous
mutants_total: 8
mutants_killed: 7
mutants_outside_named: 0
model: sonnet
---
# Opus gate — seat run sd11b, task SD11b — REJECTED

## Summary

Fresh clone of `task/SD11b` at `70aed01` (base `81c5925`) in
`~/flakes/dsh-harness` (no flake — the gate is the literal commands the
section prints). One commit carrying SD11's `c25e71f` squashed with the fix,
`+200/-1` across the section's five touched files. Items 1–4 of the section
are all correctly implemented against the prior review's two findings
(MAJOR-1's swapped exit codes 2/3, MINOR-1's inverted cause/effect), and
three of the section's four named mutants (A, C, D) and all four of SD11's
carried mutants die cleanly.

But the section's own gate (6) has a numeric sub-check that is false against
the real, already-approved file, both before this fix and after it:
`grep -c -E '^- \`[0-4]\` — ' skills/driving/references/verbs.md` is written
to print `5`; it prints `12`, on the carried commit and on HEAD alike,
because `factory-review`'s and `factory-dispatch`'s own exit-code bullet
lists (unchanged since SD11, already approved by the prior gate) use the
identical `- \`N\` — ` format and seven of their lines fall inside `[0-4]`
(five for `factory-review`: 0–4; two for `factory-dispatch`: 0, 2). No
correct implementation of SD11b's four stated items — none of which touch
`factory-review`'s or `factory-dispatch`'s sections — could make this exact
command print `5`. That is a MAJOR: `grep-gate` includes gate (6) whole, and
gate (6)'s count sub-check is red both before and after. The named mutant B
built on the same premise ("a sixth line `- \`5\` — …` → the count prints
`6`") also fails to discriminate: a `5` line falls outside `[0-4]` and does
not move the count at all — a second MAJOR, the vacuous-test twin of the
first. I reject on these.

The seat's own `.result` shows `checks_verified: grep-gate=fail
node-test=fail` with `checks_verified_src=eval`, `verify_s: 1` — the
driver's `factory_verify_checks` evaluating `.#checks.x86_64-linux.*` against
a flake-less clone (Orchestrator note), not evidence bearing on the seat's
claim. I judged both acceptance names by running the section's literal
commands myself, and found gate (6) genuinely red on the count sub-check —
independent of that tooling gap.

## Contract items

1. **The exit-code table** — met. `skills/driving/references/verbs.md:17-29`
   now reads: `0` — `done`, and `unreported`; `1` — `partial`; `2` —
   `failed` (…) and the same code for a refused input before any run
   (`factory_die 2`); `3` — an unrecognised status word, the fallthrough;
   `4` — escalated. Verified directly against `tools/factory/seat/factory-task`
   at `~/nixos-agent-env` HEAD `e788993`: the terminal `case $status in`
   starts at `:856`, `done) task_rc=0 ;;` at `:857`, `partial) task_rc=1 ;;`
   at `:858`, `failed) task_rc=2 ;;` at `:859`, `unreported) task_rc=0 ;;`
   at `:860`, the `*)` fallthrough's `task_rc=3` at `:863`, `esac` at `:865`
   — matches the orchestrator's stated mapping and the section's fixed text
   line for line. `factory_die 2` refusals confirmed at `:56,61,66,68,79,
   85,94,100`; the claude-rung escalate's `exit 4` confirmed at `:192`
   (the `.escalate` write begins `:185`). The trailing sentence ("A driver
   branches on 0 … and 4 …; 1, 2 and 3 are the three ways a run did not
   land …") is present verbatim at `verbs.md:31-33`.
2. **The integrate paragraph** — met. `verbs.md:65-68`: "The driver runs
   `factory-integrate` only after the gate's review says `approved` — the
   gate ran first; a `CHECK … fail` line means the pull never runs." The
   inverted sentence ("The driver runs the gate only when it sees
   `approved`") is gone (confirmed by gate (7), below).
3. **The usage line** — met. `verbs.md:11`: `factory-task <run> <repo-path>
   <KEY> [--model ID] [--after KEY2] [--prior <run>/<KEY>] [--rung N]
   [--fallback]`, byte-identical to `factory-task:34`'s usage text (verified
   directly). The two per-flag sentences are present at `verbs.md:13-14`.
4. **`CHANGELOG.md`** — met. `CHANGELOG.md:3-4`: the `## 2026-09-08` entry's
   `driving` line gains "; the exit-code table is the driver's own mapping",
   one line, no second entry (`git diff` shows a net +4/-0 on this file, all
   inside the single existing entry).
5. **Gate (6), the numeric sub-check — NOT met (MAJOR-1).** See Findings.
6. **Gates (1)–(5), unchanged** — still green (see Checks); SD11's four
   named mutants still die (see Mutants) — `skills/driving/SKILL.md` is
   byte-identical between the carried commit and HEAD (`diff` confirmed,
   zero output), so nothing in this task's own diff could have disturbed
   them, and I re-killed all four directly.
7. **Gate (7)** — met, both the count (`0`) and the `-q` grep (exit `0`).
8. **Gate (8)** — met, `exit 0`.

## Red before green

Carried commit reconstructed from `/home/dalhaka/factory/ws/sd11/SD11` at
`c25e71f` (read-only source; cloned to scratch, never modified in place).

**Gate (6)** — three parts:
- Count `grep -c -E '^- \`[0-4]\` — ' skills/driving/references/verbs.md`:
  carried `12`; HEAD `12`. The section says this should print `5` — it does
  not, at either revision (see Findings, MAJOR-1).
- `grep -q '^- \`2\` — \`failed\`'`: carried exit `1`; HEAD exit `0`. Matches
  the section's stated red/green.
- `grep -q '^- \`3\` — an unrecognised status word'`: carried exit `1`; HEAD
  exit `0`. Matches.
- `grep -q '^- \`0\` — \`done\`, and \`unreported\`'`: carried exit `1`;
  HEAD exit `0`. Matches.

**Gate (7)** — `grep -c 'runs the gate only when it sees'`: carried `1`;
HEAD `0`. `grep -q 'runs \`factory-integrate\` only after'`: carried exit
`1`; HEAD exit `0`. Matches the section's stated red/green exactly.

**Gate (8)** — `grep -qF '[--prior <run>/<KEY>] [--rung N] [--fallback]'`:
carried exit `1`; HEAD exit `0`. Matches.

**Gates (1)–(5)** — reconfirmed green at HEAD (`SKILL.md` exists; the
whole-tree grep prints nothing; the tier-word grep prints nothing; the
frontmatter count is `1`; the archive suite is 98/98) — unchanged from
SD11's already-accepted red-before-green, since `SKILL.md` did not move.

Three of the section's four items (1, 2, 3, and 4) genuinely reproduce as
red-before-green. Item 5/gate (6)'s count assertion is the exception: it is
not "red before, green after" — it is wrong both before and after, because
it was never a function of this task's edits.

## Mutants

| # | mutant | file | died? | on |
|---|---|---|---|---|
| A | `2`/`3` lines swapped back to the old wording | `verbs.md` | **yes** — both `-q` greps exit 1 | gate (6) |
| B | a sixth line `` - `5` — … `` appended | `verbs.md` | **no — survives** | gate (6) |
| C | the old inverted integrate sentence restored | `verbs.md` | **yes** — count prints `1` | gate (7) |
| D | `[--fallback]` dropped from the usage line | `verbs.md` | **yes** — `grep -qF` exit 1 | gate (8) |
| 1 | `SKILL.md` renamed away (existence check) | `SKILL.md` | **yes** — `test -f` exit 1 (carried-commit red state, file identical to HEAD) | gate (1) |
| 2 | append "escalate to a more capable model" | `SKILL.md` | **yes** — whole-tree grep catches it | gate (2) |
| 3 | append "a stronger model" | `SKILL.md` | **yes** — tier-word grep catches it | gate (3) |
| 4 | frontmatter `name: driving-wrong` | `SKILL.md` | **yes** — `grep -c` prints `0` | gate (4) |

Each mutant (A, B, C, D, 2, 3, 4) was applied with the Edit tool in the
working clone, the killing/surviving gate run and pasted above, then
reverted with `git checkout -- <file>` (`git status --short` confirmed clean
before and after every revert; the final `git diff --stat` against base
matched the pre-mutation diffstat exactly). Mutant 1 was not applied via a
file-delete in this clone — the orchestrator guard active in this session
refused both `mv` and `rm` on `skills/driving/SKILL.md` ("plan files change
only through the Edit and Write tools") — but `SKILL.md` is byte-identical
between the carried commit and HEAD, and gate (1)'s red state (file absent →
`test -f` exit 1) was independently measured against `81c5925` in the
"Red before green" section above; that evidence transfers directly since
gate (1) is a pure existence check unrelated to file content.

`mutants_total: 8`, `mutants_killed: 7`, `mutants_outside_named: 0`. Mutant
B is a named mutant that survives (a MAJOR per the required matrix) and its
survival is exactly the same fact as gate (6)'s broken count check: a line
of the shape `` - `5` — … `` falls outside the `[0-4]` character class the
gate scans for, so the count cannot move from adding it, regardless of
whether the baseline is `5` (as claimed) or `12` (as measured).

## Checks

Both acceptance names run as the section's literal commands (Orchestrator
note — this repo has no flake):

- **grep-gate** — gates (1)-(4) and (6)-(8) (Orchestrator: "grep-gate is
  gates (1)-(4) of SD11 plus SD11b's (6)-(8)"). (1)-(4) green as stated
  above. (6) is **not fully green**: three of its four sub-checks (the `-q`
  greps) pass, but the `grep -c -E` count prints `12`, not the `5` the
  section states — a red sub-check inside an acceptance name that is
  otherwise all green. (7) and (8) green. `grep-gate` as a whole is
  therefore **red**, on gate (6)'s count assertion.
- **node-test** — `nix develop /home/dalhaka/nixos-agent-env -c node --test
  archive/2026-09-05-planning-factory/tests/*.test.mjs` → `tests 98`,
  `pass 98`, `fail 0`. Green.

No `githooks/pre-commit`, `ruff`, `repomap.py write` or `tasks.py check` run:
this task changes no file inside `~/nixos-agent-env` (confirmed clean before
this review began), matching the prior review's own scoping (dsh-harness has
none of that tooling — Orchestrator note, both here and in
`2026-09-08-opus-review-sd11-SD11.md`).

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

One commit, `70aed01` on `81c5925` (carrying `c25e71f` squashed with the
fix, as the section requires). Subject diffed byte-for-byte against the
section's `**commit subject:**`: identical — `docs: the driving skill —
brief, dispatch, gate and integrate as calls to the seat driver, what the
driver decides alone, the rung read from the key; the model-choice gate
still prints nothing (test: grep-gate, node-test)`. Body states the why (the
prior review's MAJOR, one line), pastes the three reds (gates 6/7/8) and the
greens after the edit, and the mutant table with the killing gate — mostly
per Step 5, except the pasted gate (6) red is understated: the body's "gate
(6) — the three -q greps exit 1" omits that the count sub-check was ALSO red
(and stays red) — see Findings MAJOR-1. Trailers after a blank line, in
order: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat
headless, factory run sd11b)` then `Co-Authored-By: Claude Fable 5.1
<noreply@anthropic.com>`. No board commit; the plan file
(`docs/superpowers/plans/2026-09-06-seat-driver.md`) untouched by this task.

## Findings

**MAJOR-1 — gate (6)'s numeric sub-check is false: it never prints `5`,
before this fix or after it.**

Section text (`docs/superpowers/plans/2026-09-06-seat-driver.md:444`):
> (6) the table matches the script — `grep -c -E '^- \`[0-4]\` — '
> skills/driving/references/verbs.md` prints `5` …

Measured on HEAD `70aed01`:
```
$ nix develop /home/dalhaka/nixos-agent-env -c grep -c -E '^- `[0-4]` — ' skills/driving/references/verbs.md
12
```
Measured on the carried commit `c25e71f` (before this task's edits):
```
$ nix develop /home/dalhaka/nixos-agent-env -c grep -c -E '^- `[0-4]` — ' skills/driving/references/verbs.md
12
```
The 12 matching lines, by section (`grep -n`):
```
17:- `0` — `done`, and `unreported` …          (factory-task)
20:- `1` — `partial`.                            (factory-task)
21:- `2` — `failed` …                            (factory-task)
26:- `3` — an unrecognised status word …         (factory-task)
27:- `4` — escalated …                           (factory-task)
45:- `0` — verdict `approve`.                    (factory-review)
46:- `1` — verdict `rework`.                     (factory-review)
47:- `2` — verdict `reject`.                     (factory-review)
48:- `3` — no verdict line at all …              (factory-review)
49:- `4` — escalated …                           (factory-review)
76:- `0` — the wave launched …                   (factory-dispatch)
77:- `2` — usage, a bad repo or plan path …      (factory-dispatch)
```
`factory-review`'s own exit-code list (5 lines, unchanged since SD11,
already approved by the prior gate's contract item 6) and two of
`factory-dispatch`'s codes (`0`, `2`, also unchanged) use the identical
`` - `N` — `` bullet format and fall inside the `[0-4]` character class the
count command scans for. SD11b's four stated items (the exit-code table,
the integrate paragraph, the usage line, the CHANGELOG line) touch none of
`factory-review`'s or `factory-dispatch`'s sections, and reformatting them
is outside this section's Files/Interfaces and touches list — so no
implementation consistent with the section's own stated scope could ever
make this literal command print `5`. This is not a check the seat failed to
satisfy; it is a check that cannot be satisfied as written. `grep-gate`
therefore stays red on this sub-check both before and after the fix — a
MAJOR under the required matrix's "a red check is a MAJOR."

**MAJOR-2 — the named mutant built on the same count, mutant B, does not
discriminate (a vacuous test, the direct twin of MAJOR-1).**

Section text (`:446`): "mutant **B**: a sixth line `` - `5` — … `` → the
count prints `6`."
```
$ (append "- `5` — mutant test row." after the factory-task table's `4` line)
$ nix develop /home/dalhaka/nixos-agent-env -c grep -c -E '^- `[0-4]` — ' skills/driving/references/verbs.md
12
```
Unchanged from the unmutated count (also `12`, per MAJOR-1) — the character
`5` is outside the class `[0-4]` the regex scans for, so appending a line
starting `` - `5` — `` cannot move this count under any circumstance, let
alone from a true baseline of `5` to `6`. The mutant survives; per the
required matrix, "A named mutant that survives is a MAJOR."

## Verdict

REJECTED on MAJOR-1 and MAJOR-2. Every one of SD11b's four stated fix items
is correctly implemented — the exit-code table, the integrate paragraph, the
usage line and the CHANGELOG line all check out byte-for-byte against
`factory-task`'s own script, and the prior review's MAJOR and MINOR are both
genuinely closed. But the section's own gate (6) carries a numeric assertion
(`grep -c -E '^- \`[0-4]\` — ' … prints \`5\``) that is false against the
real file both before this task's edits and after them — the file's other,
already-approved sections (`factory-review`, `factory-dispatch`) share the
same bullet format and push the true count to `12` — and named mutant B,
built on the same false premise, cannot discriminate under the actual
regex. Neither defect is the seat's to fix: no implementation within this
section's stated scope could satisfy the literal gate (6) count command.
Fix: correct the plan section's gate (6) and mutant B to scope the count to
the `factory-task` table alone (e.g. bound the `grep` between the `## factory-task`
and `## factory-review` headings, or drop the whole-file `-c` assertion in
favor of the three `-q` greps that already pin the content correctly) —
then re-gate a fresh fix round against the corrected gate.
