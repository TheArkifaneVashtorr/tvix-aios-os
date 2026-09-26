# Opus gate — W2-N10a → W2-N10b (branch task/W2-N10b, c5c013c + 4dc6468 on 3e48ba6)

**Verdict: rework.** No blockers. All four re-gate findings are fixed in the
implementation and three are pinned red-before-green; four majors remain — three
are test-strength gaps of the exact class this chain was chartered to close, one
is a wrong operator-facing message in new code. Each fix is small.

Checks on branch head: `factory-unit` pass (`render.test.mjs: all assertions passed`),
`lint` pass. Both commits are individually green. Subjects follow
`<area>: summary (test: factory-unit, lint)`; `Generated-By:` + `Co-Authored-By:`
trailers present. Diff touches only the two named files — no scope creep.

## Red-before-green (reverse-applied in a throwaway worktree, factory-unit each time)

| reversed hunk | result |
|---|---|
| merge-list `.filter(status === 'approved')` (`:373`) | RED — "wave-1 merge list is exactly B, C" |
| `unreported` push in the null-slice branch (`:500`) | RED — "every task still appears in the returned tasks[]" |
| `results.every(status === 'approved')` in `allOk` (`:527`) | RED — "not delivered while A is unapproved" |
| `RULES_ORCH` closing clause (`:113`) | RED — "integfix prompt no longer forbids editing tracked files by hand" |
| `KEY_RE` guard (`:220`) | RED — "Missing expected rejection" |
| `extraRules` moved back off the end of the block | RED — "extraRules are appended after the single-writer paragraph" |
| verify-skip guard (`:517`) | RED — "no verifier is spawned when nothing was integrated" |
| **`results.length === A.tasks.length` (`:527`)** | **GREEN — untested** |

## Majors

1. `tools/factory/dark-factory.js:527` — the new `results.length === A.tasks.length`
   term is untested; deleting it leaves the suite green. It is load-bearing and
   reachable: with `parallel` stubbed `async (t)=>{const r=await Promise.all(t.map(f=>f())); r.pop(); return r}`
   I measured `tasks[]` = A, C only (B, D vanish, no `unreported`) and `delivered`
   flips `false → true` when the term is removed. Same defect as N10-3.
   *Fix*: that stub as a scenario; assert `result.tasks.length < args.tasks.length`
   and `delivered === false`.
2. `tools/factory/dark-factory.js:373` — mutation `=== 'approved'` → `!== 'unapproved'`
   survives (suite green). Only the `unapproved` verdict is pinned; `unreviewed`
   — the API-529 case N10-1's evidence led with, and the one status that still
   carries a branch in `branchOf` — is untested.
   *Fix*: in the existing `makeStubs('null')` scenario (`render.test.mjs:311`)
   assert `byLabel(stubs.calls, 'integrate:w1') === undefined` and `delivered === false`.
3. `tests/factory/render.test.mjs:573-574` — the positive assertion is a fragment
   match. Mutating the clause to "NEVER edit a tracked file, not even to resolve
   a merge conflict your instructions name; abort and report instead." keeps the
   suite green — a maximally contradictory clause still passes, which is verbatim
   the N10-4 complaint.
   *Fix*: `assert.match` the whole permissive sentence ("Do not edit a tracked
   file except to resolve…") plus a negative for `/NEVER edit a tracked file/i`.
4. `tools/factory/dark-factory.js:539` — `notApproved` reads `results[].status`,
   which the integration-failure downgrade at `:396` never touches (it writes
   `statusOf` only). Measured: single wave, both tasks approved, integrate+integfix
   red → `NOT delivered — no tasks approved` (both were approved; returned statuses
   are `integration-failed`). Two waves → `NOT delivered — D not approved`, hiding
   A/B/C's integration failure. The line the spec asked to improve now misstates
   the reason on the commonest failure path.
   *Fix*: derive from `statusOf` and name the status; when nothing is non-approved,
   say integration/verify failed.

## Minors

- `:206` `KEY_RE` accepts git-invalid refs (`A..B`, `x.lock`, trailing `/`) — fine as a shell guard, but say so in the comment or tighten.
- `render.test.mjs:632` asserts `l.includes('A')` — a single letter; use an exact-line assertion.
- The header comment block and `meta.phases` still describe Verify as unconditional; `verify: {verdict:'skipped'}` is an undocumented new return shape.
- The `unreported` result literal (`:501`) duplicates runTask's shape by hand; a shared constructor would stop the two drifting.

## Mutations run

R1/R2/R3-approval/R4/R5/R6/verify-skip reversals → all RED (above).
`notApproved = []` → RED. `withheld = []` → RED. `'unreported'` → `'approved'` → RED.
`KEY_RE` → `/^.*$/` → RED. `integrations.some` → `every` → RED.
`=== 'approved'` → `!== 'unapproved'` → **GREEN** (major 2).
`results.length` term deleted → **GREEN** (major 1).
Contradictory-clause rewrite → **GREEN** (major 3).
