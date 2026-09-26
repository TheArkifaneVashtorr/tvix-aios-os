# The brief blind spot

Class: process defect, observed. Status: recorded 2026-09-22 from the
`2026-09-22-aios-daemon-dispatch` judge panel (errata 1, 3, 6, 12); no task
types a fix — it is a pattern to watch for in future drafts and judge passes,
not a tool to build yet.

## The pattern

`factory-brief <plan> <KEY>` hands a seat exactly one section's text. The
judge panel scored "self-contained sections" a 2/3 on this plan because four
separate findings, across three different tasks (OS6, OS8, OS9), share one
root cause: a task's Interfaces or Steps block names a fact — an algorithm,
a struct signature, a reference file's line range — that is fully and
correctly written down in the plan, but written down under a *different*
`### KEY` heading than the one being briefed. `factory-brief` reads one
heading; a seat working from its output alone has the pointer ("OS6's
lookup", "the process, in factory-task's order") but not the referent.

This is invisible to a skim of the whole plan file, because the fact really
is there — a human reading top to bottom never notices the gap. It only
shows up when a task is read the way a dispatched seat reads it: through
`factory-brief`, one KEY at a time. Two tasks in the same plan (OS5, OS7)
show the alternative already works: they paste the full body (Python CLI,
pytest file, corpus generator) inline in their own section, so nothing is
lost when `factory-brief` slices it out. OS10 and OS11 do the same and
scored fully self-contained.

## Why it recurs

A plan author drafting sequentially writes the algorithm once, in the
section where it's first needed, and later sections that call into it write
the short form — "call OS6's lookup" — because from the author's read-the-
whole-file vantage point that's unambiguous and non-repetitive (the same
instinct errata 13 flags on the other side, where restating something twice
costs the economy score). The failure mode is symmetric to over-restatement,
not opposite to it: the drafter is choosing, per fact, between "state it
here" and "point at where it's stated," and the pointer is only safe when
the reader's context includes both sections. `factory-brief`'s reader never
does.

## The check this suggests

Not yet a task. A candidate for a future OS-plan-quality task or a judge
rubric addition: for each `### KEY` in a drafted plan, run
`factory-brief <plan> <KEY>` and grep its output for a bare reference to
another KEY's name unaccompanied by the fact itself (a cheap heuristic:
`grep -oE '\bOS[0-9]+\b'` inside a briefed section's Interfaces/Facts/Steps
blocks, outside its own heading and the Files/Waves/Sibling-plans
boilerplate that legitimately names siblings). A nonzero count is not
automatically wrong — Files/Waves sections naming a sibling KEY for
sequencing are fine — but an Interfaces or Steps block citing another KEY's
algorithm or signature is the errata-1/3/6/12 shape and should route to a
human check before the section briefs out.

## Dependencies

None landed yet. Would sit naturally as a `plan` skill judge-rubric note
(criterion 3, "self-contained sections") or a `tasks.py` subcommand
alongside `check`/`conflicts`/`waves`. Either lands after an operator
decides this is worth automating rather than relying on the judge panel to
keep catching it by hand, as it did here.

## Earliest landing

Not scheduled. Surfaces the next time a judge panel scores "self-contained
sections" below 3 for the same reason, or when an operator asks for a
plan-authoring lint pass.
