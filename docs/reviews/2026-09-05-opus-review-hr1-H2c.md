---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run hr1, task H2c — APPROVED

Reviewer: Sonnet (docs gate)

## Summary

H2c (`1bf41f1`) clears both majors from the H2b gate. `re-review-prompt.md:105` no longer prices a
scoped re-review at "a cheap-to-mid tier" and no longer dangles a cross-reference to a concept
`SKILL.md` dropped — it now states the fix-loop rule directly ("a re-review is a fix-loop round, so
it keeps the same routed row"). `implementer-prompt.md:89` no longer offers a stuck implementer
"re-dispatch with a more capable model" — it now offers "re-dispatch on the same routed row" with the
same escalation-is-a-row-change language. `SKILL.md:186`'s opening imperative ("Use the least powerful
model…") is replaced with the heading-to-table mechanism itself, and the "Review tasks" bullet no
longer claims `size` "carries the scaling." The model-choice gate is widened to the whole tree minus
`archive/` and documented in README's "Model routing" section. One commit on base, subject
byte-identical, trailer present, grep gate red on base (5 hits / 4 files) and green at HEAD, archive
suite 98/98.

Two things keep this from a clean pass-through. First, the commit touches five files, not the plan's
declared four — `skills/using-superpowers/references/codex-tools.md` also changed. This is not scope
creep for its own sake: that file's `"<a mid-tier model from your spawn allowlist>"` line matches the
plan's own widened gate pattern (`mid-tier`), so leaving it alone would have made the whole-tree gate
fail on HEAD, contradicting the plan's Step 2 acceptance test. The implementer made the minimal edit
("mid-tier" → "cheaper") rather than over-reaching into a file H2b's finding 6 called out-of-scope for
a different reason (it documents a harness not routed by `factory_route`). Recorded as a deviation, not
a defect. Second, README's "Model routing" section describes the gate's shape (`grep -rn`, excludes)
and what it matches, but does not reproduce the runnable command with its pattern list — it points a
reader at "the commit that introduced it" for "the exact alternation," which is the same
git-archaeology shape H2b flagged as a dangling cross-reference, just in a new spot. Minor, not a
blocker: the mechanism is fully documented in prose and the gate itself is real and passing.

## Checks

Throwaway clone of the implementer workspace at `…/scratchpad/gate-hr1-H2c`; tooling via
`nix develop /home/dalhaka/nixos-agent-env -c` with `XDG_CACHE_HOME` under the scratchpad. Nothing
written to `~/nixos-agent-env` (clean), nothing to the workspace, nothing to `~/flakes/dsh-harness`; no
seat launched; no `sudo`.

| # | Check | Result |
| --- | --- | --- |
| 1 | Exactly one commit on base `41b8986` | `git rev-list --count 41b8986..HEAD` → 1 |
| 2 | `git show --stat HEAD` = the plan's four files | **5 files**: `README.md`, `SKILL.md`, `implementer-prompt.md`, `re-review-prompt.md`, plus `skills/using-superpowers/references/codex-tools.md` (not in `touches`) — see Deviations |
| 3 | Subject byte-identical to the plan's / H2's string | `diff` against the plan string: identical |
| 4 | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer | present (plus `Generated-By`) |
| 5 | Whole-tree grep gate (11 patterns, whole tree minus `.git`/`archive`) on HEAD | silent, rc=1 — green |
| 6 | Same gate on base `41b8986` | 5 hits, rc=0 — red: `implementer-prompt.md:89`, `re-review-prompt.md:105`, `SKILL.md:186` and `:226`, `codex-tools.md:77` |
| 7 | `re-review-prompt.md:105` restated as the rule, cross-reference fixed | yes — now points at the fix-loop rule that `SKILL.md`'s "Fix-loop escalation" bullet actually states |
| 8 | `implementer-prompt.md:89` restated as the rule | yes — "re-dispatch on the same routed row … escalation is a row change in the routing table, never a per-dispatch model choice" |
| 9 | `SKILL.md:186` no longer opens with "Use the least powerful model…" | confirmed — replaced with "Read each sub-agent's model off the task's `### KEY (kind, size)` heading and take it from the routing table — never a per-dispatch choice." |
| 10 | "Review tasks" bullet no longer claims `size` carries scaling | confirmed — the "(a small mechanical diff is a small `size`…)" clause is deleted; bullet now just says "read off the heading, never chosen by hand" |
| 11 | README "Model routing" mentions the gate | present, but describes the gate's shape rather than reproducing the runnable command — see Findings |
| 12 | Archive suite on HEAD | `node --test archive/2026-09-05-planning-factory/tests/*.test.mjs` → `tests 98 / pass 98 / fail 0` |
| 13 | `H2c.result` check names match the commit's `(test: …)` label | `grep-gate=pass node-test=pass`, subject says `(test: grep-gate)` — consistent, unlike H2b's inherited `pre-commit` mismatch (H2b finding 5) |

## Red before green

| tree | whole-tree grep gate (11 patterns) |
| --- | --- |
| base `41b8986` (main + H1 + H2b) | **5 hits, rc=0 — red**: `skills/subagent-driven-development/implementer-prompt.md:89` ("more capable model"), `re-review-prompt.md:105` ("cheap-to-mid tier"), `SKILL.md:186` ("least powerful"), `SKILL.md:226` ("most capable"), `skills/using-superpowers/references/codex-tools.md:77` ("mid-tier") |
| HEAD `1bf41f1` | **silent, rc=1 — green** |

Re-run independently from this checkout (not taken from the commit message): matches the commit body's
own claim of "five matches across four files" (5 hits, 4 distinct files — `SKILL.md` contributes two).

## Findings

1. **Minor.** README's "Model routing" section states that a whole-tree gate exists and describes what
   it matches ("a case-insensitive `grep -rn` over the tree minus `.git` and the archive … the exact
   alternation ships in the commit that introduced it") but does not show the runnable command itself.
   A maintainer who wants to actually run the gate has to find it via `git log`/`git show` on this
   commit rather than copy-pasting from the doc — the same shape of indirection H2b flagged as a
   dangling cross-reference (finding 1), now in README instead of a prompt template. Suggest inlining
   the literal `grep -rn -i '...' --exclude-dir=.git --exclude-dir=archive .` command in README so it is
   self-contained.

2. **Observation, no action.** The fix to `codex-tools.md:77` ("mid-tier" → "cheaper") is a one-line,
   same-class edit and does not touch that file's larger claim (a different, non-`factory_route`-routed
   harness) that H2b's finding 6 already deemed out of scope. Nothing further needed here.

## Deviations

- **Five files changed, not the plan's declared four.** `skills/using-superpowers/references/codex-tools.md`
  is outside `touches`, but its `"<a mid-tier model from your spawn allowlist>"` line matches the plan's
  own Step 2 gate pattern (`mid-tier`). Since the plan's acceptance test requires the whole-tree gate to
  print nothing, leaving that line in place would have made HEAD fail the plan's own check. Fixing it
  was the only way to satisfy the plan as written; the edit is minimal and does not exceed what H2b's
  finding 6 called out. Not held against the task.
- **Neither of the two majors from H2b's findings 1 or 2 survives**, and both minors (3 and 4) are
  cleared as instructed. Finding 6 (codex-tools.md, out of scope) is addressed only incidentally, as
  above, and not because it was in scope.
