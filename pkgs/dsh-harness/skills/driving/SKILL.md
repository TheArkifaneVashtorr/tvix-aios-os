---
name: driving
description: Drive the house's factory from the operator's seat — brief, dispatch, gate and integrate a typed plan's tasks through tools/factory/seat, climbing the routing table's ladder only when a rung fails; use when the operator asks the seat to run, gate or land a task
---

# Driving

## Overview

Driving is what the operator's seat does when it runs, gates or lands a typed
plan's tasks: four verbs, each one command and nothing hand-written. The
driver scripts under `tools/factory/seat` in the house repo are the only hands
that touch the plan graph, the routing table or the seat jobs; this skill is
their manual, not a replacement for them. Every task enters through
`factory-brief` and leaves through `factory-integrate`; in between the driver
scripts decide the little that the spec lets them decide alone, and the seat
keeps its hands off everything that is the operator's.

The driver never inspects a job it runs: no transcript, no seat log, no store
body is opened. The `FACTORY-RESULT` grammar (its label, one space, `status=`,
and one of `done|partial|failed`) is the driver's, not this skill's — the
skill never writes it and never invents a value.

## The four verbs

Each verb is one command. The seat's own reasoning never substitutes for the
command the verb names; if a step needs hand-written plumbing, that is a
missing driver script, not a gap for the seat to fill.

### brief

    tools/factory/seat/factory-brief <plan> <KEY>

Read-only. It prints the whole contract a seat will see for `<KEY>` —
Global Constraints, Assumptions, the one task section. Paste exactly what it
prints; nothing else about the task reaches the seat.

### dispatch

    tools/factory/seat/factory-dispatch <run> <repo> <plan> --dry-run

first, then the same line without `--dry-run`. The dry run prints the next
wave and touches nothing — read it before committing a run to it. The plan is
named on the dispatch line; the dispatcher asks the derived graph for the next
wave itself and never re-reads `dependsOn`.

The driver never runs `factory-task` by hand except a fix round:

    FACTORY_PLAN=<plan> tools/factory/seat/factory-task <run>b <repo> <KEY>b --prior <run>/<KEY>

after the `<KEY>b` section was appended to the plan with the `edit` tool,
carrying every finding the prior block lists. `<run>b` is a fresh run for the
fix round and `--prior <run>/<KEY>` points the brief at the rejection it
answers.

### gate

    tools/factory/seat/factory-review <run> <repo> <KEY>

Rung 1. An exit 4 means the review wants a `claude` rung: paste the `launch:`
line of `~/factory/runs/<run>/<KEY>.escalate` to the operator and stop. The
seat runs the gate — it does not run the launch line it prints.

### integrate

    tools/factory/seat/factory-integrate <run> <repo> <KEY> && git -C <repo> pull --ff-only ~/factory/base/<repo-name> integ/<run>

only after the gate approved, then

    nix develop -c python3 pkgs/evidence/tasks.py --root . write-board

and one commit carrying the board's queue block. The integrate verb resolves
the merged branch against the real repo (`~/factory/base/<repo-name>`); the
`git pull --ff-only` is the merge, never a rewrite.

## What the driver decides alone

From the spec's Design 7, the verbatim list — this is the whole of what the
driver scripts may decide without the operator:

- Dispatch of a ready task at rung 1.
- A sideways fallback in the three relaunch classes — only when the `.result`
  carries `error_class: budget-402|provider-error|boot-failure`. That line is
  written by the telemetry T2 task; until it exists the driver relaunches on
  the operator's word alone.
- A climb to rung 2 on a rejection — that is the fix round.
- Printing, never running, a `claude` rung's launch line.
- The board's queue block through `write-board`.

Everything else is the operator's: pauses, spend, switches, spec approval, the
dispatch of a rung 3 re-plan, and any change to a routing-table row.

## Rules

- Never `--model`, never `OPENROUTER_MODEL`, never a model id in a prompt.
  The rung is read from the key by the driver scripts, not chosen by the seat.
- Every seat job goes through `seat-submit --no-start`; the spool starts it.
  That is the only path — the seat never starts a job itself.
- No transcript, log or store body is opened.
- The `FACTORY-RESULT` grammar is the driver's, not the skill's.

## References

- `references/verbs.md` — the four commands with their exit codes and the one
  line each prints that the driver reads.