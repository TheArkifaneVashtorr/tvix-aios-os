# Decision 2026-09-04 — parallel agent workflows are a requirement, not an option

**Decided by the operator, 2026-09-04**, overruling the orchestrator's
judgement call in `docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md`
that implementers must stay sequential because "no isolation survives the dsh
sandbox", verbatim:

> "I think perhaps adding either a deterministic scheduler based on dependency
> to allow for parallel agents, removing the isolation by generating persistent
> isolated or virtual flakes for the agents to work in during development or
> even LLM as judge to deploy the agents based on what it can note to be capable
> of parallel development. Discarding parallel agent workflows is a poor design
> choice."

Append-only; supersede with a dated entry if it changes.

## What was decided

Both dark factories — `tools/factory/dark-factory.js` in this repo and
`factory/dark-factory.js` in `~/flakes/dsh-harness` — get parallel implementers.
Sequential execution stops being the design and becomes a *fallback the
scheduler chooses* when the task graph or the file overlap says so.

The three mechanisms the operator named are all adopted, in this order of
authority — deterministic first, judgement last:

1. **A deterministic dependency scheduler.** The task graph is validated on
   entry (duplicate keys, unknown or dangling `dependsOn`, cycles, unknown
   `kind`/`role`, empty `spec`) and the run **refuses before any agent is
   spawned** if it is malformed. Waves come from Kahn's algorithm; each wave's
   tasks run concurrently under an explicit `args.concurrency` cap (not the
   host's CPU count, so the schedule is reproducible from the task list alone).
   A task whose dependency did not finish green is marked `blocked` and never
   run. The whole schedule is printed before dispatch.
2. **Persistent isolated workspaces per task.** Claude side: the Workflow
   tool's `agent(prompt, {isolation: 'worktree'})` — a fresh git worktree per
   agent, which the factory's `spawn()` already passes through verbatim. dsh
   side: a full `git clone --local` per task under a **declared factory root
   outside every git repo** — `~/factory`, created by the host config
   (nixos-agent-env, task N11) — never a gitignored path inside
   `~/flakes/dsh-harness`, because a *linked* worktree reproducibly fails
   under dsh's `workspace-write` sandbox (its `.git` pointer leaves the
   workspace — U1 vote 3). **Resolved 2026-09-04 (O11, option 1):** a clone
   *inside* a checkout is a nested repo git cannot track cleanly, flakes copy
   every tracked file into the store on each evaluation, and untracked files
   break the clean-tree assertion — hiding workspaces in a repo forces a
   `.gitignore` entry; a declared root removes all three and gives workspaces
   ownership and retention the operator controls. Each workspace is a
   complete flake checkout, is created from the integration branch's tip at
   the moment its wave starts, persists until the run ends, and is listed in
   the return value. Integration is deterministic: one branch per task key,
   merged `--no-ff` into an integration branch in topological order after
   each wave, with the task's declared checks plus lint re-run on the merged
   tree, and exactly **one** bounded fix task on a conflict or a red check
   before that chain stops.
3. **An LLM judge, bounded and visible.** Tasks carry `touches` (the paths or
   globs they will write) and optional `parallelSafe`. Overlap inside a wave is
   decided by a deterministic prefix check over `touches`; overlapping tasks are
   serialised in key order and the reason is printed as a schedule note. The
   judge (technical-authority model — Opus here, `deepseekPro` on the dsh side)
   is consulted **only** for tasks that carry no `touches` annotation, its
   answer is recorded in the schedule output next to the tasks it moved, and it
   is disabled by `args.judge = false`, in which case un-annotated tasks
   serialise. The judge never decides anything silently and never overrides an
   explicit `touches`.

Reviewers stay parallel and read-only, as they already were in the plan.

## What this overrules

- The plan's judgement call "implementers stay sequential (no isolation
  survives the dsh sandbox), only reviewers parallel". Its premise was too
  strong: U1 vote 3 refuted *linked worktrees* under dsh's sandbox and noted in
  the same breath that "an ordinary clone commits fine". A clone is the
  isolation that survives.
- `tools/factory/dark-factory.js:69` — "Do not create branches or worktrees" —
  which was written for a single writer in the live tree. It becomes: work only
  in the isolated workspace you were started in, on exactly the branch named by
  your task key.
- The plan's F3 as written ("keep implementers sequential; take the concurrency
  where it is free"). F3 is rewritten as the scheduler; F8 adds the workspaces
  and the integration; F9 adds the annotations and the judge.

Unchanged and still in force: the Claude/dsh separation
(`claude-dsh-separation` — separate gits, separate flakes, crossings are
reviewed diffs), the model policy
(`docs/decisions/2026-09-02-factory-model-policy.md`), and the amendment that a
load-bearing test counts only once it has been shown to fail
(`docs/decisions/2026-09-03-test-based-reality-amendments.md`).

## Falsifiable acceptance

Two runs settle this. Neither is an opinion.

1. **Wall clock.** A factory run whose task list contains at least two tasks
   with no `dependsOn` edge between them and no `touches` overlap completes the
   implement phase in **less than the sum** of those tasks' single-task
   wall-clocks, measured from the run journal's per-agent start and end stamps,
   **and** every declared check plus the lint gate is green on the merged
   integration tree. Both halves must hold: a fast run with a red merged tree
   fails this acceptance, and so does a green run that took the sequential time.
2. **Refusal.** A task list containing a `dependsOn` cycle (or a dangling
   reference, or a duplicate key) makes the run throw **before the first
   `agent()` call**, naming the cycle — measured by an agent count of zero in
   the journal, not by reading the error text alone.

Until run 1 has been measured, the wall-clock gain is dated debt on the board,
not a fact. Run 2 is exercised as a unit test in this repo (`factory-unit`) and
as a hand-run negative on the dsh side.

## Known cost, stated up front

Worktree isolation costs ~200–500 ms plus disk per agent, and a clone costs
more. A run whose tasks all touch one file — `~/flakes/dsh-harness`'s own
factory round is exactly that — gains no wall clock at all; what it gains is
the printed schedule, the refusal on a malformed graph, and the guarantee that
two writers never share a tree. That is the floor, not the pitch.
