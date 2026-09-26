# Opus gate — fix chain W2-N6a → W2-N6b (branch `task/W2-N6b`, 2 commits on 3e48ba6)

**Verdict: rework.** Both re-gate findings are closed for the commands the specs
name, red-before-green is real (7 mutations, 5 caught), and scope is exactly the
three specified files. Two majors block approval: the composed command
`rollup --week --costs` still prints a lifetime dollar total under a window
header, and the check self-expires on 2026-09-10.

Checks at branch head: `ledger-unit` **pass**, `lint` **pass** (both via
`nix build .#checks.x86_64-linux.<name> -L --no-link`).

## Majors

**A · `rollup --week --costs` prints a lifetime total under a window line**
`tools/ledger/factory.py:615-630` — `_rollup_week` rebinds its own local
`sessions` (`:483`), but `rollup`'s `sessions` (`:613`) is never filtered, so the
cost block at `:621` sums every session ever recorded, and the unpriced
denominator `len(sessions)` (`:637`) is lifetime too.
*Evidence*: ledger with one 2026-09-04 session (600/90/180) and one 2024-01-15
session (1,000,000 in), both priced. `rollup(week=True, costs_csv=…,
since="2026-08-28", until="2026-09-05")` →
`window: 2026-08-28T00:00:00Z .. 2026-09-05T00:00:00Z` … `cost: 1.000798 USD`.
The window line makes the wrong number *more* credible than before the fix.
This is the exact defect the pair was commissioned to kill (N6-1 evidence:
"The `--costs` total inherits the same lifetime scope"; N6-2 title: confident
wrong dollars). No test pins it in either direction — mutation M10 (adding the
correct filter) leaves 15/15 green.
*Fix*: filter `sessions` in `rollup` before the cost block when `week` is set
(or return the windowed list from `_rollup_week`); assert an exact cost line
from a `week=True, costs_csv=…` call with an out-of-window priced session; say
in `schema.md` that the cost line is windowed.

**B · The check goes red on 2026-09-10 with no code change**
`tests/ledger/test_factory.py:314` (`test_rollup_week_covers_factory_and_dsh`)
and `:363` (`test_rollup_week_fix_rounds_from_findings`) call
`rollup(out, week=True)` with the **default** trailing-7-day window while the
fixtures are frozen at 2026-09-03T10:00:00Z (workflow) and 2026-09-04 (dsh).
*Evidence*: with the clock stubbed to 2026-09-11 (single-line edit to
`:444`), `2 failed, 13 passed`; the lane line becomes
`factory: 0 agent(s), in=0 …`. Real red date: 2026-09-10T10:00Z.
*Fix*: pass explicit `since`/`until` in both tests (as
`test_rollup_week_windows_records` already does), or thread the existing
`_resolve_window(now=…)` hook through `rollup` and inject a fixed clock.

## Minors (one line each)

- `_resolve_window`'s `now=` parameter (`:436`) has no caller — the injection
  point that would fix B is present but unused.
- Half-open boundary (`since <= t < until`) unpinned: flipping both to `<=`
  leaves 15/15 green (M9).
- Single-bound derivation documented in `schema.md` is unpinned: making
  `--since` alone silently ignored leaves 15/15 green (M12).
- `--since`/`--until` are silently ignored without `--week`; argparse neither
  warns nor errors.
- A session with no `started` is reported as `no row for (None, <model>)` —
  `schema.md:118` promises that case is named, but it renders like a date miss.
- `test_rollup_week_defaults_to_trailing_seven_days_utc:598` asserts only that
  the span is 7 days, not that `until` ≈ now.
- Orchestrator follow-up, not the implementer's to make: the rename to
  `<price-table.csv>` (authorised by W2-N6b) contradicts the governing plan at
  `docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md:140,:181,:809` and
  operator action O2 (`:885`), which still produce an activity export for
  `rollup --costs`. That file now correctly raises `PriceTableError`.
- The known N6 minors (findings `task: None`, `wall_s` summing concurrent
  spans, `backfill` crash on a missing journal) are untouched — correct, out of
  scope, no creep.

## Mutations

| # | mutation | outcome |
|---|---|---|
| M1 | drop both window filters in `_rollup_week` (`:483`, `:494-497`) | **caught** — `ledger-unit` red via `nix build`, `test_rollup_week_windows_records:571` |
| M2 | `_cost_for` returns `0.0` instead of `None` on a price miss (unpriced session silently costs 0) | **caught** — `ledger-unit` red via `nix build`, `test_rollup_costs_partial_price_table_names_unpriced:183` |
| M3 | delete the `REQUIRED_PRICE_COLUMNS` guard | caught — `KeyError` at `:358`, activity-export test red |
| M4 | default window `days=7` → `days=30` | caught — defaults test red |
| M5 | drop only the agents/findings `run_id` join | caught — windows test red |
| M6 | window dsh `started` as seconds, not ms | caught — 4 failed |
| M7 | drop the `window:` first line | caught — 2 failed |
| M9 | half-open → closed on both bounds | **survives** (minor) |
| M10 | window the cost block correctly | **survives** — proves major A is untested |
| M11 | naive `--since` parsed as local time | caught — windows test red |
| M12 | `--since` alone silently ignored | **survives** (minor) |

Control: the suite is alive (5 distinct mutations each fail a distinct test).
M1 and M2 were confirmed through the real check
(`nix build .#checks.x86_64-linux.ledger-unit -L --no-link`, exit 1); the rest
through the same pytest invocation the check runs.

## What is correct

Window semantics match the spec: half-open `[since, until)` UTC, default
trailing 7 days, `--since`/`--until` each deriving the missing bound, dsh
`started` read as epoch ms (`:459`), factory runs as ISO-8601 (`:466`), and
agents/findings joined to their run by `run_id` (`:495-497`) since they carry no
timestamp. The window line is the first line. `schema.md:100-140` matches the
code on every claim I checked except the cost line's scope (major A). Commit
subjects follow `<area>: summary (test: ledger-unit, lint)` and both carry
`Co-Authored-By` and `Generated-By`. Neither commit edits its governing plan —
the previous round's minor is not repeated.
