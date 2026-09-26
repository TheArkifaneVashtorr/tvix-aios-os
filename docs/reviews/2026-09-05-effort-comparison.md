# Reasoning effort medium vs xhigh — two real XS tasks, same Opus gates (n = 2 per arm)

Plan `docs/superpowers/plans/2026-09-05-effort-comparison.md`; runs `em` (medium) and `ex` (xhigh), DeepSeek V4 Pro, same base `9083845`, the effort confirmed from each per-task home's `settings.yaml`. Prices: Pro $0.55 in / $2.19 out per million (`docs/ledger/openrouter-prices.csv`, 2026-09-04). Reviews: `docs/reviews/2026-09-05-opus-review-{em-X1med,ex-X1xhigh,em-X2med,ex-X2xhigh}.md`.

## Per task

| task | effort | gate | mutants killed | input | output | s | model cost | Opus gate tokens | transcript |
|---|---|---|---|---|---|---|---|---|---|
| X1 parity-tile summary (helm) | medium | APPROVED, 5 deviations | 5 / 5 | 298,340 | 3,799 | 137 | $0.172 | 64,589 | 73 lines, 0 reversals |
| X1 | xhigh | APPROVED, 5 deviations | 4 / 4 | 316,895 | 7,803 | 204 | $0.191 | 74,606 | 262 lines, 1 reversal |
| X2 bundle "equal to live" (evidence) | medium | APPROVED, none material | 4 / 4 | 189,122 | 5,243 | 117 | $0.116 | 72,048 | 192 lines, 0 reversals |
| X2 | xhigh | APPROVED, none material | 4 / 5 (the survivor is a plan gap shared by both arms) | 197,370 | 8,228 | 219 | $0.127 | 76,724 | 337 lines, 3 self-caught reversals |

## Per arm

| arm | approved | fix rounds | model cost | wall clock | Opus gate tokens | output tokens |
|---|---|---|---|---|---|---|
| medium | 2 / 2 | 0 | $0.288 | 254 s | 136,637 | 9,042 |
| xhigh | 2 / 2 | 0 | $0.318 | 423 s | 151,330 | 16,031 |

## What the gates saw

- **Identical code changes in both arms**, both tasks: the one-line f-string (X1) and the `live != head` guard plus a three-way render branch (X2). The xhigh X2 arm additionally guarded `b["head"]` before the compare, closing a `None`-equals-`None` edge the medium arm's reviewer flagged as a minor; that is the only substantive difference found, and it is small.
- **Same mutation outcomes** where the plan's tests were the same; the one surviving mutant (X2's untested `else` branch) survives in both arms because the plan's test spec did not name it.
- **Where xhigh spent its extra output:** longer deliberation on trivia (skill selection, test placement, whether an unstaged file dirties the flake), 3.6× the transcript on X1 and 1.8× on X2, with more self-caught reversals. No dead ends in either arm.
- Reasoning tokens are reported as 0 by the route in both arms; the output delta is where the reasoning is billed.

## Conclusion

At n = 2 per arm on XS tasks: **xhigh produced no gate-visible quality gain, for +10 % model cost, +67 % wall clock, +11 % Opus gate tokens and 1.8× the output tokens.** Medium stays the seat's default and the routing table's row for code; xhigh is not evidenced for any role yet. The saved level in the shared home is already `medium`; the backup file `settings.yaml.bak-2026-09-04-xhigh` is deleted with this measurement. Gaps: XS tasks only (a task with a genuine design decision might separate the arms); n = 2.

Integrated per the plan's rule (medium when both are approved): X1med, X2med (`integ/em`). The xhigh branches stay in their workspaces as the record.
