# Opus gate round 3 — `integ/b3` @ 990cbab (BFIX3 + F7B)

**Verdict: rework.** 84/84 green. All five round-2 items reverse-apply to a red
test (table). But the major is closed on only one of the two code paths that
feed `entries`, and the same one-line defect is live on the default-on judge
path. Refs: `factory/dark-factory.js`.

## Major

**M1 — a judge-supplied leading glob still runs beside a `parallelSafe: true`
peer.** `:348` got `overlapsAll: entries.some((e) => !literalPrefix(e))`; `:350`
(`judgeAnswers`) still hard-codes `overlapsAll: false`. The judge prompt (`:446`)
invites globs ("use a glob like `src/**`"), so `["**"]` / `["*.md"]` is expected
output. Measured on the branch (scratch clone):

| unannotated task B, judge answers | peer A | lanes |
|---|---|---|
| `['**']` | `parallelSafe:true` | `[[['A'],['B']]]` — **concurrent**, no note |
| `['*.md']` | `parallelSafe:true` | `[[['A'],['B']]]` — **concurrent** |
| `['**']` | `touches:['README.md']` | serialised (correct) |

Fix (verified: flips both rows to serialised, suite stays green, so the current
suite does not discriminate it) — at `:350` use the same expression on
`judgeAnswers.get(t.key)`; add the case to `f9-parallel-safety.test.mjs`.
`README.md:127-129` ("never runs concurrently") is true only of `touches`.

## Minors

- `:238` — the regex admits `..` and `.`; the comment above it says "no `..`".
  A `..` key yields `rm -rf "$HOME/factory/ws/<run-id>/.."` (`:528`), wiping the
  run: every sibling workspace and the integration clone. Add `!/^\.+$/`.
- `:85` — `INTEG_CLONE = wsPath('integration')`; a task keyed `integration` is
  accepted, clones into the integration clone, and its retry `rm -rf`s it.
  Reserve the name in `validateTasks`.
- `AGENTS.md` was not touched at all, though c4518bc's subject claims it was;
  `AGENTS.md:33-36` still prints the check surface without the `XDG_CACHE_HOME`
  prefix `CHECK_CMD` (`:92`) carries — the H4 failure it exists to prevent.
- `README.md:92-95` enumerates entry validation but omits the new key-charset
  rule landed two commits earlier.
- `README.md:132-133` gives the note format as `(touches overlap)` only; `:396`
  now also emits `writes everything`.
- `:636` — `envError` still short-circuits the fix task (round 2, unchanged;
  logged, defensible as M-e).

Otherwise the docs are true of the code: role→model rows (`:416-750`), the five
roles / four kinds, `deepseekFlash` never dispatched by a built-in step, all
arg defaults, the baseline gate, guard command, gating, and return shape.
Scope is clean: 7 files, every hunk maps to a round-2 finding or to F7B;
`skills/` and `factory/dark-factory.js` carry no other change.

## Mutations (scratch clone, deleted)

| # | mutation | result |
|---|---|---|
| M1 | `overlapsAll: entries.some(...)` → `false` | caught (f9 leading-glob vs parallelSafe) |
| M2 | key-charset check → `if (false)` | caught (x0; asserts 0 dispatches) |
| M3 | `/\bfatal:/` → `/^fatal:/` | caught (f2-tree-guard) |
| M4 | drop the reviewer's own model id | caught (f8-integration) |
| M5 | unquote the retry `rm -rf` path | caught (f2-implementer-retry) |
| M6 | *(no mutation)* judge answers `['**']` beside a parallelSafe peer | **survives — M1** |
