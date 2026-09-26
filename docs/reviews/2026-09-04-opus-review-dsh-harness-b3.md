# Opus gate — `integ/b3`, dsh-harness factory (9 commits on f2018e7)

**Verdict: rework.** The scheduler — graph validation, Kahn waves, blocked
propagation, concurrency cap, integration control flow — is correct and
genuinely well tested (67/67; 6 of 7 mutations caught). But F9's overlap check
has a silent parallel-safety hole, its path-boundary rule is untested, and two
failure-path prompts instruct agents to run commands that cannot succeed. No
design flaw; these are bounded fixes. Line refs are `factory/dark-factory.js`.

## Blocker

**B1 — a leading-glob `touches` entry disables the overlap check entirely.**
`:302` — `if (!pa || !pb) return false`. `literalPrefix` (`:291`) returns `''`
for any entry starting with a metacharacter, so `touches: ['**']`, `['*.md']`
or `['**/*.mjs']` — a task declaring it writes *everything* — overlaps
*nothing* and runs fully concurrently. Measured: A `['**']` vs B
`['src/a.mjs']` → lanes `[[['A'],['B']]]`, `impl:A|impl:B` overlapping in
flight; same for `['*.md']` vs `['README.md']`. This is exactly the "two agents
writing one file" F9 exists to stop, and the planner prompt (`:386`) asks for
globs, so `**/*.mjs` is a likely planner output. **Fix:** `return true` when
either prefix is empty — an unbounded glob conflicts with everything — or set
`overlapsAll: true` in `resolveTouches` (`:314`) for such a task. Add the case
to `f9-parallel-safety.test.mjs`.

## Majors

**M-a — the path-boundary rule is load-bearing and untested.** Deleting
`&& (short.endsWith('/') || long[short.length] === '/')` from `:306` leaves
67/67 green. The test claiming to cover it uses equal-length siblings
`src/api.mjs` / `src/app.mjs`, where neither is a prefix of the other, so it
cannot discriminate. **Fix:** add `src/api` vs `src/apiv2/x.mjs` (must be
separate lanes) — verified to fail under the mutation.

**M-b — F2's retry re-clones into the workspace F8 already created.** `:549`
re-dispatches `implPrompt(t)` verbatim (verified byte-identical); its first
instruction is `git clone --local <base> <ws>` (`:467`). An implementer that
dies *during* implementation — the observed upstream-500 case — leaves `<ws>`
populated, so the retry's first command fails with "destination path already
exists and is not an empty directory", with no fallback. **Fix:** an idempotent
retry preamble: `rm -rf <ws>` before the clone, or `[ -d <ws>/.git ] || git
clone …` then `cd <ws> && git fetch integ <branch> && git checkout -B <key>
integ/<branch>`.

**M-c — the fix task is told to merge branches it may not have.** `:487-498`:
the fixer clones `INTEG_CLONE`, and step 3 says "merge the wave's branches
(A, B) in order", but the prompt never carries the workspace paths or the
`git fetch <wsPath(k)> <k>:<k>` lines `integratePrompt` builds at `:477`.
Verified: `fix:wave:1` contains neither `/ws/<runId>/A` nor any task-branch
fetch. A conflict on the *first* merge leaves the later branches absent from
`INTEG_CLONE`, so the instruction is unexecutable and the one bounded fix is
wasted. **Fix:** interpolate the same fetch steps into step 3.

**M-d — the tree guard watches a directory F8 requires not to be a checkout.**
`:459` asks for `git status --porcelain` "in the current workspace"; F8 requires
the session cwd to be under `$HOME/factory`, which is not a git repo.
`isTreeDirty` (`:460`) treats any non-empty, non-`clean` reply as dirty, so
`fatal: not a git repository` becomes a dirty WARNING on **every** task. F2's
premise ("where the operator and the seat still share a checkout") no longer
holds after F8. **Fix:** point the guard at
`git -C ~/flakes/dsh-harness status --porcelain`; treat `fatal:` as "could not
check", not dirty.

**M-e — the check surface is untested against the sandbox and a false red burns
the single fix budget.** `:77` runs
`nix develop /home/dalhaka/nixos-agent-env -c node --test …` — it reaches into
the other lane's repo and runs `nix develop` under a read-only `$HOME`, the H4
failure that hit 14 of 29 sessions ("attempt to write a readonly database"). An
environmental red is indistinguishable from a code red, consumes the one fix
task, and stops the chain. **Fix:** prefix
`XDG_CACHE_HOME=${XDG_CACHE_HOME:-/tmp/dsh-factory-cache-$(id -u)}` in
`CHECK_CMD` (existing assertions match on a substring, so they still pass), and
have the integrator report an environment failure distinctly.

**M-f — the reviewer's self-exclusion clause cannot be followed.** `DECISIONS`
rule 6 (`:86`) forbids a model approving its own work, yet `deepseekPro`
implements `deepseekPro`-role tasks, is the sole fix authority, and is the
technical reviewer (`:667`). "Mark as not-applicable anything you yourself
authored" is issued to a fresh session with no memory of authorship and no
task→role map — verified absent from the prompt. This is the
prompt-level-contradiction class the Claude-side factory had. **Fix:**
interpolate the task→role table, or route those tasks' technical review
elsewhere.

## Minors

- `:264` — a *planner*-emitted dangling `dependsOn` is misreported as
  `cycle among T1`; `validateTasks` runs only on `args.tasks` (`:371`).
- `:51` — a non-array or empty `args.tasks` silently falls back to full planning
  (6 agents) instead of refusing a mangled handoff.
- `:147-148, :446` — `baseHead` / `integrationTip` are demanded of the baseline
  agent and never read or returned; dead.
- `INTEGRATION_SCHEMA.merged` and `FIX_SCHEMA.detail` are requested and never
  used (`:575-583` ignores both).
- `:478` — integrator prompt says "In `<clone>`:" with no `cd`.
- One `guard:tree:` agent per task for a check that is per-run, not per-task.
- README's "stay inside the workflow tool's limits" is an unmeasured claim.
- `AGENTS.md:29-31` still says the factory's roles are `sonnet/opus/fable`;
  this branch appends a bullet beside it without disambiguating (F7's scope).

Otherwise README/AGENTS are accurate for what the script now does, and no scope
creep was found — every commit maps to its plan section.

## Mutations run (scratch clone, since deleted)

| # | mutation | result |
|---|---|---|
| M1 | `touchesOverlap`: drop the path-boundary condition | **survived, 67/67** (M-a) |
| M2 | Kahn: remove `.sort()` on the ready set | caught (sorted-waves test) |
| M3 | `resolveTouches`: unannotated → `overlapsAll: false` | caught (2 tests) |
| M4 | `blockedStatuses`: drop `'blocked'` | caught (transitive blocking) |
| M5 | delivery gate → `integratedOk` only | caught (nothing-integrated test) |
| M6 | remove `spec: t.spec` from the return projection | caught (X0 test) |
| M7 | remove the implementer retry dispatch | caught (2 F2 tests) |

Probed and sound: the blocked cascade reaches non-adjacent dependents after a
hard stop; the concurrency cap chunks lane heads correctly; the judge is
consulted only for unannotated tasks and is always logged and returned; plan
mode dispatches zero agents.
