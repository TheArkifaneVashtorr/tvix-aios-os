---
plan_defect: implementer
mutants_total: 4
mutants_killed: 4
mutants_outside_named: 0
model: sonnet
---
# Opus gate — seat run sd11, task SD11 — REJECTED

## Summary

Fresh clone of `task/SD11` at `c25e71f` (base `81c5925`) in
`~/flakes/dsh-harness` (no flake, no hooks — the gate is the five literal
commands the section prints). One commit, five files, `+186/-1`. Four of the
section's five gates and all four named mutants check out clean: the file
exists, the whole-tree model-choice grep prints nothing before and after, the
skill's own tier-word grep prints nothing, the frontmatter name count is `1`,
and the archive suite is 98/98. But `skills/driving/references/verbs.md`
states a wrong meaning for two of `factory-task`'s five documented exit
codes — verified directly against `tools/factory/seat/factory-task`'s own
case statement — which is exactly the kind of interface fact this skill
exists to get right for an automated driving seat reading exit codes to
route. That is a MAJOR; I reject on it alone. Nothing else in the diff, the
mutants, the checks or the commit convention is wrong.

The seat's own `.result` shows `checks_verified: grep-gate=fail node-test=fail`
with `checks_verified_src=eval`, `verify_s: 3`. That is the driver's
`factory_verify_checks` evaluating `.#checks.x86_64-linux.grep-gate` against
a flake that does not exist in this dsh-harness clone (Orchestrator note) —
not evidence bearing on the seat's claim. I judged the two acceptance names
by running the literal commands the section prints, not by the `.result`.

## Contract items

1. `skills/driving/SKILL.md` frontmatter `name: driving` — met.
   `skills/driving/SKILL.md:2` — `name: driving`. `grep -c '^name: driving$'`
   → `1`.
2. Frontmatter `description:` byte-identical to the section's text — met.
   `skills/driving/SKILL.md:3` diffed byte-for-byte against the section's
   quoted sentence: identical.
3. Body, in the skill's own words, the four verbs each as one command and
   nothing hand-written — met. `SKILL.md:30-74` gives `brief`, `dispatch`,
   `gate`, `integrate` each as the exact command line the section names,
   including the fix-round `factory-task … --prior <run>/<KEY>` line and the
   `--dry-run`-first rule for dispatch.
4. "What the driver decides alone" as the spec's Design 7 verbatim list —
   met. `SKILL.md:76-91` lists the five items (rung-1 dispatch, the
   `error_class:`-gated sideways fallback, the rung-2 climb, printing-never-
   running a claude launch line, `write-board`) word for word against the
   section's own list, plus "Everything else is the operator's."
5. Rules: never `--model`/`OPENROUTER_MODEL`/a model id in a prompt; every
   job through `seat-submit --no-start`; no transcript/log/store body opened;
   the `FACTORY-RESULT` grammar is the driver's — met, `SKILL.md:93-100`.
   The `--no-start` claim is accurate for this skill's actual seat: it runs
   *inside* a drive seat unit (SD7), so `SEAT_JOB_ID` is exported and
   `factory-task`'s `spool_flags=(--no-start --wait)` branch is the one it
   always takes (`tools/factory/seat/factory-task:387-392` in
   `~/nixos-agent-env`, read-only).
6. `references/verbs.md`: the four commands with their exit codes and the
   one line each driver reads — **partially met, one code wrong** (see
   MAJOR-1 below). `factory-review`'s 0/1/2/3/4 and the escalate line match
   `tools/factory/seat/factory-review`'s header exactly. `factory-dispatch`'s
   2/5/6/7 and the `would run: …` line match its header exactly.
   `factory-integrate`'s "non-zero on conflict/refusal/skip/failed check"
   matches its header and its `refused`/`skipped`/`overall_rc` logic.
   `factory-task`'s exit-code table (0/1/2/3, 4=escalated) is wrong for 2
   and 3 — see MAJOR-1.
7. README/AGENTS/CHANGELOG one-line/one-paragraph additions — met (see
   Touches and commit).
8. "The harness's whole-tree gate keeps printing nothing" — met, gate (2)
   verified silent both before and after in Red before green below.

## Red before green

**Gate (1)** `test -f skills/driving/SKILL.md`:
- Base `81c5925`: `exit=1` (file absent). Matches the section's stated red.
- HEAD `c25e71f`: `exit=0`.

**Gate (2)** the whole-tree model-choice grep (must print nothing before AND
after — the spec's T6):
- Base `81c5925`: prints nothing, `exit=1` (grep's no-match code).
- HEAD `c25e71f`: prints nothing, `exit=1`.
Both green, as the section requires (this gate is not a red/green pair — it
is a standing invariant checked at both ends).

**Gate (4)** `grep -c '^name: driving$' skills/driving/SKILL.md`:
- Base `81c5925`:
  ```
  grep: skills/driving/SKILL.md: No such file or directory
  ```
  exit=2. Matches the section's stated red exactly ("gate (4) prints `grep:
  skills/driving/SKILL.md: No such file`").
- HEAD `c25e71f`: prints `1`, exit=0.

**Gate (3)** (tier-word grep in `skills/driving`) has no stated red — the
directory does not exist at base, so the grep itself would error, not print
a false negative; not a red/green pair by the section's own Step 1 list.
Confirmed green at HEAD (see Checks).

**Gate (5)** (node-test) is not claimed red at base — the archive suite is
untouched by this task and passes at both revisions; confirmed 98/98 at
HEAD (see Checks).

Every test the section names as red-before-green is real: gate (1) and gate
(4) genuinely fail at base and genuinely pass at HEAD.

## Mutants

| # | mutant | file | died? | on |
|---|---|---|---|---|
| 1 | `SKILL.md` renamed away (existence check) | `skills/driving/SKILL.md` | **yes** — `test -f` exit 1 | gate (1) |
| 2 | append "escalate to a more capable model" to `SKILL.md` | `skills/driving/SKILL.md` | **yes** — grep prints `./skills/driving/SKILL.md:105:…escalate to a more capable model` | gate (2) |
| 3 | append "a stronger model" to `SKILL.md` | `skills/driving/SKILL.md` | **yes** — grep prints `skills/driving/SKILL.md:105:…a stronger model` | gate (3) |
| 4 | frontmatter `name: driving-wrong` | `skills/driving/SKILL.md` | **yes** — `grep -c` prints `0` | gate (4) |

`mutants_total: 4`, `mutants_killed: 4`, `mutants_outside_named: 0`. Each
mutant was applied in the working clone (`git status --short` confirmed
clean before and after each), the killing gate run and pasted, then reverted
with `git checkout -- skills/driving/SKILL.md`; the tree matched HEAD after
every revert. No named mutant survives.

## Checks

Both acceptance names run as the section's literal commands (Orchestrator
note — this repo has no flake, so these are not `nix build .#checks…`):

- **grep-gate** — gates (1)-(4) run individually, all green at HEAD: (1)
  `exit=0`; (2) prints nothing, `exit=1`; (3) `nix develop
  /home/dalhaka/nixos-agent-env -c grep -rn -i 'stronger model\|weaker
  model\|better model\|upgrade the model' skills/driving` prints nothing,
  `exit=1`; (4) prints `1`, `exit=0`.
- **node-test** — `nix develop /home/dalhaka/nixos-agent-env -c node --test
  archive/2026-09-05-planning-factory/tests/*.test.mjs` → `tests 98`,
  `pass 98`, `fail 0`.

The `.result`'s `checks_verified: grep-gate=fail node-test=fail` is the
driver's `factory_verify_checks` trying `nix build
.#checks.x86_64-linux.grep-gate` against a flake-less clone
(`checks_verified_src=eval`, `verify_s: 3`) — a tooling gap in the driver for
a cross-repo task, not a finding against the seat's claim (Orchestrator
note). `status=partial` and the NOTES line ("grep-gate claimed pass, driver
fail; node-test claimed pass, driver fail") in the `.result` record exactly
this gap; the seat's own claim ("all five gates green") is correct, as
confirmed above by running the gates myself.

No `githooks/pre-commit`, `ruff`, `repomap.py write` or `tasks.py check` run:
this task changes no file inside `~/nixos-agent-env`, so none of those
checks apply (Required matrix item 4 is scoped to the plan repo; SD11's repo
is `dsh-harness`, which has none of that tooling — Orchestrator note).
`docs/superpowers/plans/2026-09-06-seat-driver.md` and `docs/MAP.md` in
`~/nixos-agent-env` are untouched (`git status` there shows nothing from
this task — the clone under review is entirely in `/tmp`).

## Touches and commit

`git diff --name-only 81c5925..HEAD`:
```
AGENTS.md
CHANGELOG.md
README.md
skills/driving/SKILL.md
skills/driving/references/verbs.md
```
Exactly the section's touches list, five files, no `archive/` hit
(`grep -c '^archive/'` → `0`).

One commit, `c25e71f` on `81c5925`. Subject diffed byte-for-byte against the
section's `**commit subject:**` — identical:
`docs: the driving skill — brief, dispatch, gate and integrate as calls to
the seat driver, what the driver decides alone, the rung read from the key;
the model-choice gate still prints nothing (test: grep-gate, node-test)`.
Body states the why (one paragraph); trailers, after a blank line and in the
WORKSPACE RULES order (confirmed against `factory-brief:79-80`'s template):
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless,
factory run sd11)` then `Co-Authored-By: Claude Fable 5.1
<noreply@anthropic.com>`. No board commit (this repo has none). The body
does not paste the red/green output inline — the same shape as the accepted
precedent `2f9e8d1` (P13, `docs/reviews/2026-09-06-opus-review-pa11-P13.md`,
APPROVED), so not flagged here.

## Findings

**MAJOR-1 — `verbs.md`'s `factory-task` exit-code table swaps the real
meanings of codes 2 and 3.**

`skills/driving/references/verbs.md:13-19`:
```
- `2` — usage or a refused input (a missing `FACTORY_PLAN`, a bad argument).
- `3` — the run itself failed outright.
```

`tools/factory/seat/factory-task` (in `~/nixos-agent-env`, read-only,
unchanged by this task) has no header exit-code list for this script (unlike
`factory-review` and `factory-dispatch`, which do) — the meanings had to be
read off its body. The terminal mapping, verbatim:

```
tools/factory/seat/factory-task:856-864
case $status in
  done) task_rc=0 ;;
  partial) task_rc=1 ;;
  failed) task_rc=2 ;;
  unreported) task_rc=0 ;;
  *)
    status=${status:-unknown}
    task_rc=3
    ;;
esac
```

`status=failed` is a routine, frequently-hit outcome — it is the value
written for a failed `seat-submit`, a near-miss `FACTORY-RESULT` line with no
commits, no usable result line at all, or the agent's own literal
`status=failed` — and every one of those maps to **exit 2**, the same code
the early usage-error paths (`factory-task:40,89`, missing `FACTORY_PLAN` at
`factory-task:99`) also use. Exit **3** is reached only by the fallthrough
`*)` arm — an unrecognized/malformed status word, not "the run itself failed
outright." `verbs.md`'s table has this backwards: it tells a driving seat
that exit 2 means only a usage mistake and exit 3 means the task failed,
when in fact a failed task run is indistinguishable from a bad argument at
exit 2, and exit 3 is the rare unparseable-status case. A driving seat
routing on this table (SKILL.md's own words: "Only `done` advances the task;
a `partial` or `failed` status routes the driver to the gate and the
operator" — correct, because that text keys on the `FACTORY-RESULT` line,
not the exit code) would, if it instead trusted `verbs.md`'s numeric claim,
misdiagnose a real task failure (exit 2) as a usage error needing different
arguments. This is exactly the interface fact the section asked `verbs.md`
to carry accurately ("the four commands with their exit codes (from the
scripts' headers…)"), and it is wrong, checked directly against the script
the doc describes — a MAJOR.

**MINOR-1 — `verbs.md`'s `factory-integrate` paragraph inverts cause and
effect.**

`skills/driving/references/verbs.md:52-54`:
```
The lines the driver reads: `CHECK <name> pass|fail` and `CONFLICT <KEY>`
from stdout. The driver runs the gate only when it sees `approved`; it never
runs the pull after a `CHECK … fail` line.
```

This sentence sits under the `factory-integrate` heading but says "the
driver runs the gate" — the gate (`factory-review`) already ran, before
`integrate` is ever reached (`SKILL.md`'s own "integrate" verb: "only after
the gate approved"). The intended point — the driver only invokes
`integrate`'s pull step once the review verdict is `approve` and never after
a failed check — is directionally right but stated backwards, confusing
which command's outcome gates which. No test exercises this prose (it is not
a gate command), so it stays a MINOR rather than a MAJOR; it would read
correctly if "runs the gate" were "runs integrate."

## Verdict

REJECTED on MAJOR-1. Four of five gates, all four named mutants, red-before-
green, the touches list and the commit convention are all clean — but the
one substantive fact `verbs.md` adds beyond the plan's own text (what each
`factory-task` exit code means) is wrong in a way that would mislead the very
automated driving seat this skill exists to guide. Fix: correct
`verbs.md:13-19` to state that exit 2 covers both a usage refusal and
`status=failed`, and exit 3 is the unrecognized-status fallthrough, not "the
run itself failed outright" — then re-gate.
