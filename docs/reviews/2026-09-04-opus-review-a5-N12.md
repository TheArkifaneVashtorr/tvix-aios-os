# Opus gate — a5 / N12 (task/N12 @ b0f44f0) — **APPROVE**

Scope is exactly the two files asked for (`git diff --stat main..task/N12`: dark-factory.js +13,
render.test.mjs +56). `factory-unit` green, lint gate green (treefmt/statix/deadnix/shellcheck/ruff,
exit 0). No sudo/switch/service calls; work done in a throwaway worktree, clone untouched.

## What actually changed

**(1) The guard is new.** `tools/factory/dark-factory.js:249-250` — `t.kind !== 'docs' &&
(!Array.isArray(t.checks) || t.checks.length === 0)` throws naming the key, sitting inside
`validateGraph` (`:231`) which runs at `:325`, before the first `spawn` (judge `:333`, baseline
`:359`). Header rule documented at `:14-18`, citing board rule A1 and the digest §6 P4 residue.
`kind` undefined is treated as code — consistent with `:451`'s `kind === 'docs' ? 'docs' : 'code'`
(probed: refused).

**(2) The cap is NOT new — it is locked in.** `FIX_ROUNDS` (`:78`, default 2), `maxRounds`
(`:470`, docs 1), the exhaustion break (`:495`), `fixRounds: rounds` (`:518`) and its surfacing in
the return value (`:623`) all pre-date this branch, as the digest itself states (§2, correction (a)).
Scenario 22 (`tests/factory/render.test.mjs:792-813`) is therefore a characterization lock, not a
red-first test — it stays green with the impl hunks reverse-applied. This matches the digest's
acceptance ("a factory-unit case asserting no chain reports fixRounds > 2") and is proven load-bearing
by mutation M2 instead. The commit **subject** ("fix rounds are capped at two and recorded") reads as
if it implements this; the body is honest ("Lock in board rule A1's bounded-fix invariant"). Minor.

## Red before green

Reverse-applied the dark-factory.js hunks (`git apply -R`), then
`nix build .#checks.x86_64-linux.factory-unit -L --no-link`: **red** —
`Missing expected rejection ... expected: /task A names no checks/` at render.test.mjs:828.
Scenario 22 passed in that same run, confirming the split above.

## Mutation table

| # | Mutation | Result | Killed by |
|---|---|---|---|
| M1 | reverse-apply impl hunks (remove the guard) | **red** | `assert.rejects` @ test:828 |
| M2 | `FIX_ROUNDS` default 2 → 3 (`:78`) | **red** | `fixRounds` 3 !== 2 @ test:804 |
| M3 | drop the `kind !== 'docs'` carve-out | **red** | docs task D refused @ test:839 |
| M4 | reject only *absent* checks (drop `length === 0`) | **red** | `checks: []` leg @ test:828 |
| M5 | reject only *empty* checks (drop `!Array.isArray`) | **red** | absent-`checks` leg @ test:828 |
| M6 | error message drops `${t.key}` | **red** | regex `/task A names no checks/` |
| M7 | move `validateGraph(A.tasks)` below the baseline spawn | **red** | validation-ordering scenario @ test:444 |

Seven for seven. Both legs (empty / absent), the docs carve-out, the key in the message, the
before-dispatch position and the cap value are each independently protected.

## `checks: ['none']` — probed, and the branch does not special-case it

`['none']` is a non-empty array, so it passes the guard and dispatches (probe: 6 agents, approved
against stubs). **That is the right call, and the branch handles it correctly by not handling it.**
There is no `'none'` sentinel anywhere in the tree — `'(none named)'` (`:401`) and
`'(none named — the lint gate still applies)'` (`:452`) are fallbacks for an *empty* list, not values.
So `['none']` is just a check name that does not exist: the wave integrator is told to run
`nix build .#checks.x86_64-linux.none` (`:403`) and the reviewer's rule "blocker = a named check is
red" (`:476`) makes the task un-approvable. The failure is loud and downstream, which is precisely
what the guard exists to guarantee versus the silent degradation to the lint gate. Special-casing the
string would be a keyword nobody has defined.

One residual worth a sentence on the board, not a rework: the implementer prompt then reads
"Named checks for this task: none." (`:457`) — English identical to the old degraded case. A caller
who writes `checks: ['none']` to get past the guard gets an impl prompt that reads exactly like the
bug, and only the integrator catches it. Cheap follow-up if it ever bites.

## Other observations (none blocking)

- `docs` tasks with `checks: []` are accepted (probed → approved). Correct per the header text.
- Board rule A1's "`fixRounds` is never raised above 2" is still only a board rule: `args.fixRounds: 5`
  is accepted at `:78`, and scenario 22's `t.fixRounds <= 2` loop hardcodes 2 rather than reading
  FIX_ROUNDS. The digest explicitly scopes this ("the only residual is a human typing a bigger
  number") and asks for a rule, not code. Consistent.
- Scenario 22's `delivered === false` overlaps scenario 20 (`:765`); `delivered === true` is asserted
  at `:491`, so the assertion is not vacuous.
- Test scaffolding untouched: `rejectAlways` (`:159`) and `byLabel` (`:218`) pre-exist.
- Commit convention: `factory: … (test: factory-unit, lint)`; trailers
  `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run a5)` and
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` — matches the seat's convention on
  dd01dfb/f606690.

## Verdict

**APPROVE.** The one thing to carry to the board: part (2) landed as a regression lock over
pre-existing code, verified by mutation rather than by red-first, and the commit subject overstates
it. Optional tidy, not a fix round.
