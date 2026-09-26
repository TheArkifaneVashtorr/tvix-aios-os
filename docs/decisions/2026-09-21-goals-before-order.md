# Goals before dependency order — the operator's rule of 2026-09-16, written down (2026-09-21)

Decided by the operator on 2026-09-16, in-session, as the root cause of a run of
choices that had gone wrong; recorded then only as spoken word in the
orchestrator's memory, and cited from there by
`docs/decisions/2026-09-17-data-streams-surface-on-helm.md` ("the failure the
operator named as the root cause on 2026-09-16, choices without measurable
goals"). This file is the document that citation lacked (loose-ends
`docs/research-2026-09-21-tvix-aios-loose-ends.md`, item 13, answer a).

## The rule

A choice is made against a goal that can be measured, and the goal comes first.
Rigor — tests, gates, mutants, waves — is downstream of the decision it serves;
a wave table substitutes ordering for direction when nobody has said what
number the wave moves. Before a plan is written, the planner asks what single
observable counts as success, and the plan names it; a task whose section
cannot say which number it serves is not ready to be typed.

## Origin

The operator's words, as the orchestrator recorded them the same day: choices
without measurable goals were the root cause; rigor is all downstream of
decisions; `waves` substitutes ordering for direction; ask what number a wave
serves. No transcript is on the tree; the memory record is the source and this
file names it as such.

## First application

The public-repository program (`docs/superpowers/specs/2026-09-21-publish-gate-design.md`
§2) is the first program scoped by this rule: its number is loose-ends item 2's
default — one person outside this host takes a task from the public list and it
lands — and phase 1 is measured by two commands whose result the operator can
read, `publish-gate` and `publish-gate-negative` both green, the second because a
planted private string failed the validator.

## What it asks of a plan

- name the number the plan serves before the spec-to-task map;
- state, per wave, which number the wave moves, or say that it moves none;
- refuse a task that cannot name its number, and say so in the plan's questions
  rather than route around it (brief §8: "If something in this brief is wrong or
  internally inconsistent, say so").
