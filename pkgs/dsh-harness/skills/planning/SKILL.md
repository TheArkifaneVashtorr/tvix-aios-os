---
name: planning
description: Write a typed implementation plan from an approved spec under docs/superpowers/specs for this house's dark factory; use when handed that spec path and an output path under docs/reviews/plan-drafts
---

# Planning

## Overview

Write one typed implementation plan from an approved spec. The spec lives
under `docs/superpowers/specs/` in the house repo and is already approved —
brainstorming and approval happened before this skill ran. The plan is a
draft until the panel says otherwise: the seat's blind judges score it
against the rubric before it is ever dispatched, and a draft that the panel
rejects is revised against their errata. You work from the packet (handed to
you, never computed by you), then follow the process in Steps 0–7.

The seat hands you two things on entry: the spec path and the output path under
`docs/reviews/plan-drafts`. The packet is composed for you by
`tools/factory/seat/factory-plan-brief.sh` (or the equivalent machine brief);
**you never compute the packet yourself** — its mechanical part and scripted
field part are the operator's tree, pasted by a script the factory tests.

## What the plan is

One output file. A typed implementation plan: every task typed
(`### KEY (kind, size)` with a size XS/S/M only — L is refused, split any L
into sub-project plans first), with `## Global Constraints`, `## Assumptions`,
the typed sections, the `## Operator` section and the `## Dispatch` section.
No typed heading outside that one file. The plan is a draft until the panel
says otherwise; nothing in it is a decision the seat has taken.

## The rules, in this skill's own words

- **One output file.** The whole plan is one file under
  `docs/reviews/plan-drafts/`. No typed heading exists outside it.
- **No read of transcripts, logs or store bodies.** You never read transcripts
  of other runs, seat logs, `dispatch.log`, `.dsh-home`, or any store body,
  and you never guess what they hold.
- **Every fact beside its command.** Every fact you state was produced by a
  command you ran at planning time, and that command is pasted beside it.
  Cite the anchor text, never a line number — a line number is stale the
  moment the file changes.
- **One seat tool, read-only.** `tools/factory/seat/factory-brief <draft>
  <KEY>` is the one seat tool you may run; it is read-only and prints the
  whole contract a seat will see. `factory-dispatch` you run only with
  `--dry-run`. The seat never computes the packet (see Overview).
- **The eight questions.** The eight questions of
  `references/section-checklist.md` are answered for every section before the
  draft is done; any "no" answer sends you back to that section.
- **A draft until the panel says otherwise.** You score, you do not dispatch.
  The panel's verdict — and only the panel's verdict — turns the draft into a
  plan.

## References

- `references/inputs.md` — §2 of the design as a command list, in order, with
  the "if missing" column. The mechanical inputs M1–M13 and the record M2.x's
  readers (record, field, operator, target).
- `references/rubric.md` — the 14-row rubric with 0–3 each (42 points), the
  §5.3 threshold (dispatch at 34 of 42 and no median below 2 on rows 2, 3, 5,
  6, 7 and 13). This is what the panel scores you against; self-judge against
  the same table in Step 6.
- `references/anticipation.md` — §4 as a checklist keyed by trigger. Prepare
  the artefact each row whose trigger applies.
- `references/section-checklist.md` — Appendix A, the eight questions every
  section answers before it ships.
- `judge-prompt.md` — the three lenses and the two fixed sentences of the
  judge prompt, one lens per call, quoted as prose.

## The process — Steps 0–7

A step whose check fails is repeated, not skipped. The session runs the whole
process in one turn and outputs one plan file, one judgement file and one
concept file.

### Step 0 — the packet

The packet is handed in, not computed. Read the mechanical part and the
scripted part exactly as composed for you. Check: the graph-soundness input
is empty; every fact you later state traces to a line in the packet; the
packet is dated.

### Step 1 — clarify

From the target, list every decision the spec leaves open and sort it: the
operator's (anything under the operator model, an isolation grade, a name,
spend, a credential's home, anything that widens an agent's reach) and the
plan's (a file layout, a test shape, an order). Ask at most three operator
questions, each decidable in one word, each with a recommendation and the
default that applies if unanswered. Check: every question names the invariant
or decision file it touches; a question without a recommendation is not asked.

### Step 2 — scope

Write the spec-to-task map: every numbered spec item maps to a task key or an
explicit `out: <reason>`. Anything the request implies but the spec does not
say goes under "Not in this plan". Check: the map is complete in both
directions; the "Not in this plan" list is non-empty or says "none".

### Step 3 — decompose

Typed sections, sizes XS/S/M only. `dependsOn` names keys that exist in the
graph or in this plan; a dependency in another repo carries `repo:`. `touches`
is explicit paths, never a leading glob. Waves come from peeling off every
task with no unmet dependency — what `tasks.py waves --json` emits — computed
for a scratch copy of the tree that contains the draft. Two tasks in one wave
that write the same file serialise in key order, and the plan says so.
Parallelism is designed in, not out. Check: the graph check is empty and
`conflicts` shows no new cross-plan hit for the scratch copy; every wave with
more than one group is a measured chance to run in parallel.

### Step 4 — specify each task

The seat sees exactly `## Global Constraints`, `## Assumptions` and the task's
own section; nothing else in the plan reaches it. Every section therefore
carries, in order: **Files**; **Interfaces** (names and signatures, every
producer of every field, every enum arm, the error contract, which tree or
file a derivation reads); **Facts** (each pasted from a command run at
planning time, the command beside it); **Steps** (the red command and its
expected red output pasted, the change, the green command, the checks by
name); **Tests** (per assertion the one-line mutant that turns it red; per
fixture the row that makes it discriminate); **touches**; **acceptance**
(names from the map); **commit subject** (byte-exact). For a fix round or a
re-plan, the section also carries every item of the rejection and, for every
deleted test, the assertion that replaces it. Check: `factory-brief <draft>
<KEY>` reproduces the section whole; the eight questions of
`references/section-checklist.md` have no "no" answer; the section names at
least one mutant per assertion and none of the mutants is "delete the test".

### Step 5 — operator steps and rollback

One command each, with its acceptance and expected output, in a `## Operator`
section a non-engineer can run top to bottom: the switch with the delta named
as a prediction, the user units to start by hand, the credentials, names and
top-ups, the acceptance drill, the rollback. Check: every command is pasted
from a run in dry form or quoted from the runbook it extends; nothing is a
sentence where a command would do.

### Step 6 — self-judge

Score the draft against `references/rubric.md` with reasons; any row below 2
is revised before the panel sees it. Check: the self-score is filed beside the
panel's; a self-score more than 6 points above the panel's median is recorded
as a calibration finding.

### Step 7 — record

The concept-per-turn file, the judgement file, and one board line. Check: the
concept file exists with the seven fields; the judgement file parses.

## Stopping

- **STOP and report the block** if the packet is missing or the graph check is
  non-empty — a plan written onto a broken graph inherits phantom states.
- **STOP** if the spec was not approved, or an input you need is refused.
- Remember: the plan is a draft until the panel says otherwise. You do not
  dispatch, you do not switch, you do not touch the operator's items.