# Opus gate — a6/H1 (`task/H1` @ ef4b459)

**Verdict: rework** — implementation is correct and live-verified; the new test
is red-first but does not discriminate the fix from `snaps[-1]`. Test-only fix,
patch verified below.

## Implementation — correct

`pkgs/helm/collect.py:131` `snap = max(snaps, key=lambda s: _parse_iso(s["time"]))`
replaces `snaps[0]`; `collect.py:139` adds `"groups": len(snaps)`; thresholds at
`collect.py:141-145` untouched. Detail is dumped generically
(`collect.py:619`), so `groups` surfaces with no render change; no golden asserts
detail keys (`tests/integration/helm-vm.nix:54`, `tests/acceptance/helm.sh:105`
check tile names only). Scope: the two allowed files.

**Nanoseconds**: `_parse_iso` (`collect.py:60-67`) → `fromisoformat`; on devShell
3.14.7 and host `pkgs.python3` 3.12.12, 9 fractional digits truncate to µs
(3.11+ behaviour). No gap.

**Live** (real repo, `--no-lock`, temp cache, read-only): 4 groups.
Branch → `ok`, `snapshot 6033584d 18.7h ago`, `groups: 4`, time
`2026-09-04T00:00:02.675507414-05:00`. main → `warn`, `16e29ff5 46.8h ago`.
Defect and fix reproduced exactly.

**Red-first**: `git checkout main -- pkgs/helm/collect.py`, then
`nix build .#checks.x86_64-linux.helm-unit` → `1 failed, 114 passed`,
`AssertionError: assert '6033584d' in 'snapshot 16e29ff5 8.1h ago'` at
test_collect.py:96. Right test, right reason. Restored: helm-unit + lint green
(115 pass).

## Mutations

| mutant | caught | why |
|---|---|---|
| `snaps[-1]` | **no** (40 pass) | fixture's newest `6033584d` is the **last** entry (test_collect.py:87-91), not the middle |
| naive sort key `s["time"][:19]` | **no** (40 pass) | all four fixture times share offset `-05:00`; naive order == true order |
| strip offset inside `_parse_iso` | yes | age assertion test_collect.py:100 (1.0h → 6.0h) |
| `min` instead of `max` | yes | test_collect.py:96 |
| drop `"groups"` | yes | KeyError, test_collect.py:99 |

Both survivors matter: the live list also has the newest last, so `snaps[-1]`
would pass the suite *and* look right on `core`.

## Required rework (test file only)

Reorder the fixture so the newest is index 1, and give one entry a different
offset whose *naive* time is later than the newest's:

- keep `16e29ff5 … -05:00` at index 0
- move `6033584d 2026-09-03T02:00:00.123456789-05:00` to index 1
- `59cd359e` → `2026-09-03T05:00:00.123456789+00:00` at index 2
- `c8b82c94 2026-09-02T20:00:00.123456789-05:00` last

Verified: unmutated impl passes (40); `snaps[-1]` fails; naive key fails. Update
the "newest last" comment at test_collect.py:66-67.

## Convention

Subject `helm: … (test: helm-unit, lint)` matches repo practice; `Generated-By:
dsh …` and `Co-Authored-By: Claude Fable 5.1` present; body's red/green claims
(8.1h, 115 tests) both reproduce.
