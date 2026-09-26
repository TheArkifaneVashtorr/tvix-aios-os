# Opus gate — N16 round 2 (`task/N16b`, fix `8382b6e` on `598c870`)

**Verdict: rework.** Both round-1 majors are genuinely fixed and all five
minors are closed, but the fix for B introduces a new major. `ledger-unit` and
`lint` green at head (31 passed); scope is 3 files, subject and both trailers
conform.

## Round-1 items — closed

- **A fixed.** `factory.py:743` adds a lane job's `cost_usd` only when its
  bucket has no export row. Probe A (lane flash/2026-09-04 0.000025 + export
  row 0.004000) now prints `reported cost: 0.004000 USD (lane 0.000000 +
  activity 0.004000)`; `0.004025` is gone.
- **B fixed.** `factory.py:749-752,780-781` sum every bucket and name the
  unjoined ones. Probe B prints `5.001000` and `unattributed activity:
  (2026-09-04, openai/gpt-9) 5.000000 USD`.
- **Minors 1-5 closed:** MU4 now caught; unpriced lane ids named
  (`factory.py:841-846`); blank cost → `ActivityExportError` naming the row
  (`:468-474`); `schema.md:179-181`'s "3 of 5" example reproduced verbatim;
  unverified-shape statement at `schema.md:149-154`.

## New major C — `--week` no longer windows the export

`rollup` loads the whole export (`factory.py:838`) and `_cost_block` now sums
*every* bucket (`:749-750`), where the old code summed only session-joined
buckets. Probe: window `2026-08-28..2026-09-05`, export row
`2024-01-15,openai/gpt-9,9.000000` → `reported cost: 9.001025`; parent
`598c870` on identical input printed `0.001025`. A regression, and it
contradicts `schema.md:214-218` ("Records whose timestamp falls outside the
window … are excluded from every lane, role, fix-round and cost total").
Untested.

## New minors

6. A bucket covered by a *lane job* but no session is suppressed as covered
   (`:743`) yet named `unattributed activity` (`:751`) — the report contradicts
   itself on exactly major A's case.
7. `schema.md:192` dropped the parent's "(and no lane `cost_usd`)" qualifier;
   `factory.py:840` still requires `not reported_lane`.

## Mutations

| # | mutation | outcome |
|---|---|---|
| red | reverse-apply the `factory.py` hunks | red — 4 failed, 27 passed |
| MU4 | delete the `--week` lane filter (`:832`) | caught — `test_rollup_week_windows_lane_jobs` |
| MU7 | ms/s slip in `_lane_job_price_key` (`:443`) | caught — `…supersedes_lane_job_on_same_bucket` |
| MU8 | suppress lane cost whenever any export row exists (`:743`) | caught — `test_rollup_reported_total_includes_lane_jobs` |
