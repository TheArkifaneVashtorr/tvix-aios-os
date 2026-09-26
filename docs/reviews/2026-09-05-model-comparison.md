# DeepSeek V4 Pro vs V4 Flash — two real tasks, same Opus gates (n = 2 per arm)

Plan `docs/superpowers/plans/2026-09-05-model-comparison.md`. Seat runs `mcp` (Pro) and `mcf2` (Flash; the first Flash launch `mcf` died at boot on the seed bug fixed by P0). Effort `medium` in both arms. Same base for both arms apart from docs commits and P0's seat-seed change, which neither task touches. Prices from `docs/ledger/openrouter-prices.csv` (2026-09-04 row for Pro, 2026-09-03 for Flash; cache reads are recorded but the sheet prices them at 0, so they are shown, not costed).

## Per task

| task | model | rounds | gate | input | output | cacheRead | s | model cost | Opus gate tokens |
|---|---|---|---|---|---|---|---|---|---|
| P1 launch-today.sh tidy (code, XS) | Pro | 1 | APPROVED, 5 deviations, header line 86 cols (plan said ≤ 80) | 146,168 | 9,230 | 171,264 | 120 | $0.101 | 82,751 |
| P1 | Flash | 2 | round 1 REJECTED (kept the prose, left the grep red); round 2 APPROVED, wrap compliant, branch marginally the better | 200,480 | 45,973 | 1,283,584 | 527 | $0.023 | 181,844 |
| P2 bats `] && [` lint guard (code, S) | Pro | 1 | APPROVED, 4 deviations, 4 of 5 mutants killed | 157,761 | 11,454 | 614,144 | 231 | $0.112 | 89,335 |
| P2 | Flash | 1 | APPROVED, 6 deviations, same 4 of 5 mutants killed; commented the `bash` prefix (the remediation Pro's review asked for); one staging blunder caught and amended by itself | 105,110 | 20,048 | 1,195,776 | 374 | $0.012 | 94,498 |

## Per arm

| arm | tasks approved | fix rounds | model cost | wall clock | Opus gate tokens (Claude side) | transcript lines |
|---|---|---|---|---|---|---|
| Pro | 2 / 2 | 0 | $0.213 | 351 s | 172,086 | 697 |
| Flash | 2 / 2 | 1 | $0.035 | 901 s | 276,342 | 2,092 |

## What the gates saw (from the five review files)

- **Both arms hit the same two plan defects** — P1's header wording contained the string P1's green forbids, and P2's flake parenthetical about the sandbox was wrong. Pro resolved both in one round by preferring the machine check. Flash diagnosed both just as clearly but on P1 chose the prose and accepted a red grep, costing a round; on P2 it anticipated the shebang trap before building and reached the fix in a quarter of Pro's lines with no reversals.
- **Artifacts:** after its fix round Flash's P1 is the more compliant file (every header line ≤ 80 columns; Pro's line 4 is 86). Flash's P2 is the only one documenting the `bash` prefix at the point of use and the only one whose commit body carries no false claim. Pro's P2 body repeats the plan's inaccurate `file:line` claim.
- **Process:** Pro is cleaner and faster (no staging error, 38 % fewer lines on P2, 62 % of the wall clock). Flash self-interrupts more (28 turns on P2), amended once after committing only two of four files, and read the Pro workspace read-only during its fix round.
- **Reasoning tokens** are not itemised by either model on this route (claim `reasoning-tokens-not-itemised` still open); `output` includes whatever reasoning was billed.

## Conclusion

At n = 2 per arm: **Flash's model cost is 6× lower per task even after a fix round, and the delivered branches are at least as good at the gate, but Flash needed one round more in two tasks, took 2.6× the wall clock, and consumed 1.6× the Opus gate tokens** — the gate spend on the Claude side is the larger cost of the two and is where Flash's extra round actually shows up. Quality at the gate was equal after the fix round. The decisive skill difference was one judgement call (machine check over prose), which the fix-round text taught Flash in one line.

Recommendation: keep Pro as the seat default for code tasks until n ≥ 5 per arm; run docs and XS tasks on Flash at effort `off` (M2b) and watch the fix-round rate — a Flash round that needs an Opus re-gate costs more in Claude tokens than the Pro premium it saved. Claim `pro-vs-flash-unmeasured` is closed by this document. Gap: Opus gate cost is in tokens only (no in/out split from the harness), and cache-read pricing is unrecorded in the price sheet.

Integrated per the plan's predeclared rule (Pro's branch when both arms are approved): P1pro, P2pro. The Flash branches `task/P1flashb`, `task/P2flash` stay in their workspaces as the record.
