# Opus gate round 2 — `integ/b3` after BFIX2 (10 commits on f2018e7)

**Verdict: rework** — one line of code and one test. B1 and all six majors
(M-a…M-f) and all eight minors are genuinely closed, each by a test that fails
when the fix is reverse-applied (14/14 mutations caught, table below). What
remains is a *residual of B1 itself*: the fix was applied pairwise instead of on
the code's own `overlapsAll` axis, so one variant of "writes everything" still
runs concurrently. Refs are `factory/dark-factory.js` on `239e72f`.

## Major

**M1 — a `**` task still runs concurrently with a `parallelSafe: true` peer.**
`:345` — `if (entries.length) m.set(t.key, { entries, overlapsAll: false })`.
BFIX2 fixed `touchesOverlap` (`:329`, `return true` on an empty prefix), which
only fires when *both* tasks have entries. A `parallelSafe: true` task resolves
to `{ entries: [], overlapsAll: false }` (`:346`), so the `.some()` at `:374`
compares nothing and no union happens. Measured on the branch:

| A | B | lanes |
|---|---|---|
| `touches:['**']` | `parallelSafe:true` | `[[['A'],['B']]]` — **concurrent** |
| `touches:['*.md']` | `parallelSafe:true` | `[[['A'],['B']]]` — **concurrent** |
| unannotated | `parallelSafe:true` | `[[['A','B']]]` — serialised (correct) |

The unannotated row is the tell: "conflicts with everything" is expressed by
`overlapsAll`, and the third row proves that flag *does* beat `parallelSafe`.
A leading-glob task never got the flag. The planner is told to emit `touches`
globs *and* to set `parallelSafe` (`:413`), so both sides are expected output.
**Fix** (verified: flips all four rows to serialised, suite stays 80/80, so the
current suite does not discriminate it):
`overlapsAll: entries.some((e) => !literalPrefix(e))` at `:345`. Add the
`['**']`-vs-`parallelSafe` case to `f9-parallel-safety.test.mjs`; the note text
at `:390` should then also say "writes everything", not "unannotated".

## Minors

- `:518` — `rm -rf ${wsPath(t.key)}` is a new destructive command built from an
  unvalidated, unquoted key; `validateTasks` (`:236`) only checks non-empty, so
  a key with a space or `..` deletes outside the workspace. Add
  `/^[A-Za-z0-9._-]+$/` to `validateTasks` and quote the path.
- `:491` — `/^fatal:/` only matches a reply that *starts* with it; a guard agent
  that prefixes any prose reports "dirty".
- The reviewers get the task→role→model table but never their own model id —
  the mapping "DeepSeek V4 Pro" → `deepseek/deepseek-v4-pro-0813` is left to
  inference. Interpolate the reviewer's own id.
- A model that misfiles a code failure into `envError` now skips the fix task
  entirely (`:625`) — a recoverable red becomes a hard stop. Logged, so visible.
- `factory/tests/f2-tree-guard.test.mjs` has no trailing newline.
- For F7B (not failures): `AGENTS.md:31-34` still gives the check surface
  without the `XDG_CACHE_HOME` prefix that `CHECK_CMD` (`:92`) now carries;
  `README.md:53` reads "the plan-mode return keep their size bounded".

No scope creep: 12 files, every hunk maps to a round-1 finding. README/AGENTS
are otherwise accurate for the new behaviour, including the AGENTS role-name
correction that was round 1's last minor.

## Mutations (scratch clone, deleted)

| # | mutation | result |
|---|---|---|
| M1 | empty literal prefix overlaps nothing again | caught |
| M2 | drop the path-boundary condition (round-1 survivor) | **caught** |
| M3 | retry re-dispatches `implPrompt` | caught |
| M4 | drop `rm -rf` from the retry preamble | caught |
| M5 | drop `mergeSteps` from the fix prompt | caught |
| M6 | guard reads the session cwd again | caught |
| M7 | `fatal:` treated as dirty | caught |
| M8 | drop `XDG_CACHE_HOME` from `CHECK_CMD` | caught |
| M9 | `envError` no longer short-circuits the fix | caught |
| M10 | reviewers lose the role table | caught |
| M11 | drop the dangling-`dependsOn` check | caught |
| M12 | drop the build-mode `args.tasks` refusal | caught |
| M13 | guard dispatched twice (per task) | caught |
| M14 | drop `cd` from the integrator prompt | caught |
