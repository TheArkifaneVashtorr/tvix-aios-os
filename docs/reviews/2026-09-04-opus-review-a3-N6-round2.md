# Opus gate round 2 — fix chain W2-N6a → W2-N6b → W2-N6c (branch `task/W2-N6c`, 3 commits on 3e48ba6)

**Verdict: approve.** Both majors from round 1 are closed, and closed with tests
that genuinely fail without the fix. Scope is still exactly the three files
(`tools/ledger/factory.py`, `tools/ledger/schema.md`,
`tests/ledger/test_factory.py`); no docs/plan files touched. Suite grew 15 → 20
tests, every new test load-bearing.

Checks at branch head: `ledger-unit` **pass**, `lint` **pass** (both via
`nix build .#checks.x86_64-linux.<name> -L --no-link`).

## Majors — both closed

**A · `rollup --week --costs` cost block is now windowed.** `factory.py:616-619`
filters `sessions` through `_session_in_window` after `_rollup_week`, so the
dollar total *and* the `len(sessions)` denominator use the window. Verified on
the round-1 reproducer (one in-window 2026-09-04 session, one priced 2024-01-15
session): `cost: 0.000798 USD`, not `1.000798`. Pinned by
`test_rollup_week_costs_are_windowed:663`, which asserts both the exact right
line and the absence of the wrong one. **M10 is now caught through the real
gate** — reverse-applying the three-line fix gives `ledger-unit` exit 1,
`1 failed, 19 passed`.

**B · The check no longer self-expires.** All eight `week=True` call sites now
pass explicit `since`/`until` or an injected `now=`; the `now=` hook on
`_resolve_window` is threaded through `rollup` (`:611,:616`), so round 1's
"injection point present but unused" minor is closed too. Verified by stubbing
*both* clocks (factory's `_resolve_window` default and the test's own
`dt.datetime.now`) to 2026-09-11T10:00Z and again to 2027-06-01: **20 passed**
each time. The two tests that self-expired (`:327`, `:423`) now pass
`since="2026-08-28", until="2026-09-05"`.

## Remaining majors

None.

## Minors

- `--week --costs` silently drops a session with no `started` (filtered by
  `_session_in_window`), so the new `no start time for N session(s)` note never
  appears on the windowed path — bare total instead. Documented by
  `schema.md:140-144` and no dollar is wrong, but the naming promise at
  `schema.md:118-121` holds only without `--week`.
- Round-1 minors now **fixed**: half-open boundary pinned (M9 caught),
  single-bound derivation pinned (M12 caught), `--since/--until` without
  `--week` is a `parser.error` exit 2, no-start distinct from a price miss,
  default-window test asserts `until` within 60 s of now, `now=` has a caller.
- Unchanged and correctly out of scope: findings `task: None`, `wall_s` summing
  concurrent spans, `backfill` crash on a missing journal.
- Orchestrator follow-up, not the implementer's: the `<price-table.csv>` rename
  still contradicts the governing plan
  (`docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md:140,:181,:809`)
  and operator action O2 (`:885`).

## Mutations

| # | mutation | outcome |
|---|---|---|
| M10r | remove the `--week` cost-block window filter (`:617-619`) — the round-1 defect | **caught** — `ledger-unit` red via `nix build` (exit 1), `test_rollup_week_costs_are_windowed:663` |
| H2r | revert no-start naming to the `(None, model)` lump | caught — `test_rollup_costs_no_start_time_is_distinct:803` |
| H3r | drop the `--since/--until require --week` guard | caught — `test_rollup_cli_since_until_require_week` |
| H4r | drop the `now=` clock-injection threading | caught — 2 failed (defaults + single-bound) |
| M9 | half-open `[since, until)` → closed on both bounds | **caught** (was survivor) — `test_rollup_week_half_open_boundary:730` |
| M12 | `--since` alone silently ignored | **caught** (was survivor) — 4 failed |
| M1 | drop the `_rollup_week` session window filter | caught — 2 failed |
| clock | stub factory + test clocks to 2026-09-11, then 2027-06-01 | **green (20 passed)** both — B closed |

Control: 7 distinct mutations, 7 caught, failures landing on distinct tests. The
two round-1 survivors (M9, M12) are now both caught, and the headline M10 was
confirmed through the real check, not just the local pytest harness.

## Convention

All three subjects follow `<area>: summary (test: ledger-unit, lint)`; each
carries `Co-Authored-By: Claude Fable 5.1` and
`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless,
factory run a3)`. `schema.md` matches the code on every claim checked, including
the newly documented windowed cost scope and the usage-error rule.
