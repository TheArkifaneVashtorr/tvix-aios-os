# Opus gate round 2 — W2-N10c (branch task/W2-N10c, d1dcadf on 3e48ba6)

**Verdict: approve.** All four round-1 majors are closed, each pinned
red-before-green; the four minors are addressed. No new majors. Four minors
remain, all one-line test or comment work.

Checks at branch head: `factory-unit` pass (`render.test.mjs: all assertions
passed`), `lint` pass. Diff touches only `tools/factory/dark-factory.js` and
`tests/factory/render.test.mjs`. Subject follows `<area>: summary (test:
factory-unit, lint)`; `Generated-By:` + `Co-Authored-By:` trailers present on
all three commits. Worktree clean.

## Round-1 majors — closed

1. **length term** — new scenario 19 (`render.test.mjs:734`) stubs a `parallel()`
   that pops a group's results. Deleting `results.length === A.tasks.length`
   (`dark-factory.js:568`) is now RED ("the run is not delivered while tasks are
   missing"), confirmed under `nix build .#checks.x86_64-linux.factory-unit`.
2. **`unreviewed` merge exclusion** — scenario 3 now asserts no `integrate:w1`
   spawn and `delivered === false`. `=== 'approved'` → `!== 'unapproved'`
   (`:383`) is RED.
3. **fragment match** — whole permissive sentence + `doesNotMatch(/NEVER edit a
   tracked file/i)`. Round-1's contradictory clause is RED, and so is a reworded
   contradiction that dodges the negative ("Do not edit a tracked file under any
   circumstances…"), so the positive is carrying the weight, not the negative.
4. **not-delivered summary** — implementation now derives from `statusOf`
   (`:586-592`), pinned by three exact-line assertions (two-wave scenario 13,
   single-wave 14, verify-failed 15). The two-wave line reads
   `A (integration-failed), B (integration-failed), C (integration-failed),
   D (blocked)` — the right status, the round-1 defect inverted. Reversing the
   hunk is RED; so is swapping `statusOf` for a `results[]` lookup.

Round-1 minors: KEY_RE comment scoped; `l.includes('A')` → exact-line equality;
Verify's conditional skip and `{verdict:'skipped'}` documented in the header
Returns block and `meta.phases`; `unreported` literal now shares `taskResult`.
Reversing the `taskResult` refactor is GREEN — expected, it is behaviour-
preserving (verified field-by-field), a drift fix not a behaviour fix.

## Minors

- `dark-factory.js:587` + `:586` — scenario 19 asserts `delivered` and
  `tasks.length` but not its log line, so two mutations survive there:
  `|| 'unreported'` → `|| 'approved'`, and `A.tasks` → `results`. Both make a
  dropped-group run print `NOT delivered — verify failed` when verify passed.
  One `assert.equal` on `NOT delivered — B (unreported); …` closes both.
- `dark-factory.js:590` — dropping `.sort()` survives; fixture keys are already
  ordered. Cosmetic.
- `dark-factory.js:416` — the comment calls `taskResult` "the per-task shape
  returned in `tasks`"; it is the internal `results` record — `tasks[]` is a
  different projection (adds `deviations`/`blocked_reason`/`findings`).
- `dark-factory.js:568` — `===` → `>=` survives; an equivalent mutant for the
  tested scenario, not actionable.

## Mutations run

| mutation | round 1 | round 2 |
|---|---|---|
| delete `results.length === A.tasks.length` | GREEN | **RED** |
| `=== 'approved'` → `!== 'unapproved'` (:383) | GREEN | **RED** |
| contradictory RULES_ORCH clause | GREEN | **RED** |
| reworded contradiction (dodges the negative) | — | RED |
| reverse not-delivered hunk (results[].status) | — | RED |
| `statusOf.get` → `results.find(...).status` | — | RED |
| `'verify failed'` → `'no tasks approved'` | — | RED |
| reverse `taskResult` refactor | — | GREEN (equivalent) |
| `|| 'unreported'` → `|| 'approved'` | — | GREEN (minor 1) |
| `A.tasks` → `results` in summary | — | GREEN (minor 1) |
| drop `.sort()` | — | GREEN (minor 2) |
| `===` → `>=` on the length term | — | GREEN (equivalent) |
