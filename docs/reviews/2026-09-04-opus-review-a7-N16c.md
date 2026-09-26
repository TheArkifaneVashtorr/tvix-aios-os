# Opus gate — N16 round 3 (`task/N16c`, fix `640ccff` on `8382b6e`)

**Verdict: approve.** Major C and minors 6-7 are genuinely closed, each pinned
by a test that goes red for the right reason. `ledger-unit` 33 passed, `lint`
green; scope is 3 files; subject and both trailers conform.

## Round-2 items — closed

- **C fixed.** `factory.py:577-591` windows an export bucket by its date's UTC
  midnight; `:860-865` applies it on the `--week` path only. Probe C (window
  `2026-08-28..2026-09-05`, row `2024-01-15,openai/gpt-9,9.0`) prints
  `reported cost: 0.001025 USD (lane 0.000025 + activity 0.001000)` with no
  unattributed line; without `--week`, `9.001025` and
  `unattributed activity: (2024-01-15, openai/gpt-9) 9.000000 USD`.
  `schema.md:214-218` is true again.
- **6 fixed.** `factory.py:767,770` excludes lane-covered buckets from
  `unattributed`; docstring `:748-752` matches. Probe: lane flash 0.000025 +
  export 0.004000 → `0.004000`, no unattributed line.
- **7 fixed.** `schema.md:192` restores "(and no lane `cost_usd`)".

## Mutations

| # | mutation | outcome |
|---|---|---|
| red | reverse-apply the `factory.py`+`schema.md` hunks | red — 2 failed, 31 passed: `:1237` got the unwindowed total, `:1282` saw the unattributed line |
| M9 | delete the `--week` export filter (`:860-865`) | caught — `test_rollup_week_windows_activity_export` (`:1212`) |
| M10 | revert `and key not in lane_job_keys` (`:770`) | caught — `…covered_by_lane_job_is_not_unattributed` (`:1248`) |

## New minors (follow-up, not blocking)

8. An unparseable export date is *silently* dropped under `--week`
   (`:587-589` returns False): probe `not-a-date,m/x,7.0` → weekly
   `activity 0.000000`, unnamed; without `--week` it is named. Same class as
   round-2 minor 3 — `_load_activity` should raise on the date too.
9. Day-atomic windowing under-reports the oldest partial day of the default
   `--week`: session at `2026-08-28T16:00Z`, `since=14:00Z`, export row
   `2026-08-28,m/x,1.234` → `reported cost 0.000000` + `no cost row for
   (2026-08-28, m/x)`. Named, not silent, but `schema.md:208-212` lists three
   windowing rules and never says how an export bucket is windowed.
