# seat-plan.md — the planning seat's constraints

This file is the *plan* handed to a headless planning seat (`factory-plan`,
P8). It is not a plan file: it lives under `tools/factory/plan/`, not
`docs/superpowers/plans/`, and carries no typed `### KEY (kind, size) — ` task
heading, so the task graph never sees it. `factory-brief` composes its
`## Global Constraints` and `## Assumptions` sections, then appends the
planning packet (`factory-plan-brief`'s output, supplied as the ad-hoc task
text) as the task body. The seat's one commit lands the draft the brief named,
on branch `task/PLAN-<name>`.

## Global Constraints

- Write ONE output file — the draft the brief named, under
  `docs/reviews/plan-drafts/` — and nothing else in the tree.
- Write no typed `### <KEY> (code|docs, XS|S|M|L) — ` heading in any file:
  the draft is not a plan section until the panel judges it.
- Never open a transcript, a seat log, `dispatch.log`, a `.dsh-home`, or a
  store body.
- No network access.
- `factory-brief <draft> <KEY>` is the one seat tool you may run, and
  `factory-dispatch` only with `--dry-run`.

## Assumptions

1. The draft is a draft until the panel says otherwise — you write it, you do
   not judge it.
2. The packet supplied as the task text is the composed planning packet; its
   parts are facts read at planning time, beside their commands.
3. End with `FACTORY-RESULT status=done` and the draft's word count in
   `FACTORY-NOTES`.