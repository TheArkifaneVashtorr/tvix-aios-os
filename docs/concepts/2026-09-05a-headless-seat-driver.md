# Concept 2026-09-05a — the headless seat driver, a manual precursor of the in-factory schedulers

**Class:** operator tooling / build automation.
**Status:** landed (`tools/factory/seat/`, first real use 2026-09-04's fix
round).

**Origin (2026-09-04, the dsh review fix round):** the round had eleven
tasks and needed them to run against the `dsh-openrouter` seat (the headless
DeepSeek-via-OpenRouter tool the operator already has for day-to-day
editing, concept `2026-09-03b`) without the operator hand-launching each
one, hand-tracking its branch, and hand-merging the result. What existed
was the seat itself and nothing to run it at task granularity; the fix
round's `~/factory/bin/` scripts filled that gap and ran the whole thing,
unversioned, before landing here as `tools/factory/seat/` so they are
gated on shellcheck and ruff like everything else in this repo.

**Idea:** six small scripts, each doing one step, chained by the operator
or by a wrapping loop — never a scheduler of their own. `factory-brief
<plan.md> <KEY>` builds the exact prompt: the plan's Global Constraints and
Assumptions sections, the task's own `### KEY ...` section, and a fixed
WORKSPACE RULES block (work only in the current directory, TDD, commit
convention, the FACTORY-RESULT summary format the parser expects back).
`factory-ws` and `factory-task` give every task its own disposable clone —
one clone per task, branch `task/<KEY>` — off a declared factory root,
`~/factory{,/base,/ws}` (`hosts/core/agent-prereqs.nix`), so nothing under
this repo's own checkout is ever edited directly. `factory-task` launches
the seat headless in that clone, with an isolated `DSH_HOME` per task
(sharing one `DSH_HOME` across concurrent launches was tried and produced a
real race — two processes writing `openrouter-route.yml` at once left
invalid YAML; per-task homes fixed it, see the README) and a writable
`XDG_CACHE_HOME` (the sandbox makes `$HOME` read-only, and Nix's fetcher
needs somewhere to write). `factory-wave` runs several such chains
concurrently. Results are parsed from the seat's own `FACTORY-RESULT` /
`CHECKS` / `COMMITS` / `NOTES` lines — plain text the model is asked to
print, not anything read back from git.

**Integration and delivery:** `factory-integrate` merges the named task
branches into `integ/<run>`, in order, inside the base clone only —
`<repo-path>` is never touched. It then collects every merged commit's
`(test: ...)` list, adds `lint`, and builds each named check **from the
integration branch by ref** (`git+file://<base>?ref=integ/<run>#checks...`)
rather than from a local checkout, so what gets tested is exactly what was
merged. It prints, and never runs, the fast-forward recipe; the operator
or the orchestrator runs `git -C <repo> pull --ff-only <base> integ/<run>`
by hand once the checks are green. Reviews are separate seat sessions —
`factory-review` runs in a *fresh* clone of the task branch, not the
implementer's own workspace, and only writes a `.review.md`; it never
fixes anything itself.

**Lessons the day's run left on the board** (`docs/OPERATIONS.md`):
status is currently read from the model's own printed lines, not
cross-checked against git state — a known gap, not yet closed; concurrent
base-clone refreshes needed a lock (`factory-ws`/`factory-integrate` now
hold one); a repo with no flake needs `FACTORY_CHECK_CMD` to name its own
check command instead of `nix build .#checks...`; a wave built on top of an
already-integrated branch needs `FACTORY_BASE_BRANCH` to say so; and a
repo with conventions the fixed WORKSPACE RULES block doesn't cover gets
`FACTORY_BRIEF_EXTRA`, appended as a block that overrides the fixed rules
where they conflict.

**Why this is a precursor and not the destination:** every one of these
scripts is manual — the operator (or an orchestrator session) decides the
task list, calls `factory-wave`, watches the run, calls
`factory-integrate`, and fast-forwards by hand. **N10** and **F8** are
named, in this driver's own README, as the in-factory successors: N10
adds a dependency scheduler, isolated per-task worktrees, and deterministic
integration to this repo's own `tools/factory/dark-factory.js` (the
Claude-run factory); F8 gives the dsh-side factory the same shape — a
persistent isolated clone per task and deterministic integration — using
the same declared `~/factory` root this driver already established. Once
either scheduler exists, day-to-day task work runs through it; until then,
this driver is how tasks get run against the seat.

**Dependencies:** `dsh-openrouter` (concept `2026-09-03b`); the declared
factory root (`hosts/core/agent-prereqs.nix`, `docs/decisions/2026-09-04-
parallel-agent-workflows.md`); the plan the fix round ran from
(`docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md`).

**Earliest landing:** landed 2026-09-04 for the fix round's own eleven
tasks; versioned into the repo as `tools/factory/seat/` afterward; retired
in favour of N10/F8 once either scheduler lands.
