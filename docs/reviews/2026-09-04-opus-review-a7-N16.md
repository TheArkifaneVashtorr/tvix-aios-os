# Opus gate — N16 (branch `task/N16`, 1 commit `598c870` on main)

**Verdict: rework.** Both acceptance checks green at head (`ledger-unit`,
`lint`, via `nix build .#checks.x86_64-linux.<name> -L --no-link`); red-before-green
is real (reverse-applying the `factory.py` hunks: **10 failed, 16 passed**).
Scope is exactly the four spec paths; subject and both trailers conform.
Two majors block.

## Majors

**A · Reported cost double counts the lane.** The OpenRouter activity export is
account-wide, so a `(date, model)` bucket already contains the lane's requests;
`factory.py:711-718` adds every lane `cost_usd` and `:730-733` adds the whole
matching bucket. Probe — lane job flash/2026-09-04 at 0.000025, export row
flash/2026-09-04 at 0.004000 — prints `reported cost: 0.004025 USD (lane
0.000025 + activity 0.004000)`; the truth is 0.004000. Undocumented, untested,
and hit on the first real export (O2), since seat and lane share the account
and the models.

**B · An export bucket that joins to no session vanishes.** Same loop: a bucket
with no session is neither added nor named. Probe — a `openai/gpt-9,5.000000`
row — prints `reported cost: 0.001000` and an `unpriced:` line that never
mentions it. `$5.00` of operator-supplied reported spend silently gone, against
the module's own promise (`schema.md:112-115`).

## Minors

1. `--week` lane windowing is unpinned — deleting `factory.py:800` keeps 26/26
   green. Same class as round-1's headline major on the session path.
2. Lane jobs all unpriced with no `--costs`/`--activity` → `factory.py:807-809`
   prints `cost: unknown (no price table)`, never naming them.
3. A blank `cost` cell raises a bare `ValueError`, not `ActivityExportError`
   (`factory.py:452`).
4. `schema.md:166-169`'s example is not producible: the code emits *no start
   time* first (`factory.py:759-771`), and "1 of 4" lists three gaps.
5. **Export shape assumed, not verified.** `date,model,cost` required, extras
   tolerated (`factory.py:400,445`); "per request" (`:435`) is unverified. No
   `docs/research-*.md` re-verifies it. Mitigated: wrong columns fail loudly.

Otherwise `schema.md` matches the code, and the N6 `--week` no-start minor is
folded in and pinned (`test_rollup_week_costs_names_no_start_session`).

## Mutations

| # | mutation | outcome |
|---|---|---|
| red | reverse-apply the `factory.py` hunks | red — 10 failed, 16 passed |
| MU1 | price table wins over reported (`:730-736` swapped) | caught — `test_rollup_activity_export_is_preferred_over_price_table` |
| MU2 | drop one session from the cost join (`:728`) | caught — 8 failed |
| MU3 | unpriced session costs 0 silently (`:738-741`) | caught — 2 failed |
| MU4 | delete the `--week` lane-job filter (`:800`) | **survived** — 26 passed |
| MU5 | activity rows overwrite, not sum (`:452`) | caught — 2 failed |
| MU6 | lane refusal costs 0 silently (`:715-718`) | caught — 1 failed |

6 mutations, 5 caught on distinct tests, 1 survivor (minor 1).
