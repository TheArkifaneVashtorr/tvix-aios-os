# Opus gate — seat run oi1, task DA1b — APPROVED

## Summary

The leak is gone and the round is provable. Every private column of
`tests/ledger/fixtures/activity-export.csv` is now an invented value
(`gen-fixture-1..4`, `fixture-user`, `fixture-key`, `fixture-app`), and an
exact-field comparison against the operator's live export — parsed with
`csv.DictReader`, value-set equality per column, never a substring grep — finds
no private cell shared with it. The branch is a fresh single commit off `main`;
DA1's commit is **not** an ancestor, and a scan of the whole reachable history's
patch text for the operator's three real `api_key_name` values, both real
`app_name` values and the one real `user` value returns zero for every private
value that was new to the repo. The same scan run against DA1's branch as a
control finds the leaked key name 4×, so the scan is sensitive.

`tools/ledger/factory.py` and `tools/ledger/schema.md` are carried from DA1
byte-for-byte (`git diff --quiet da1 HEAD -- <path>` on both). The fixture now
ends with a newline. The cosmetic M5 survivor from DA1 is closed: the
unknown-shape test asserts the full joined phrase, and dropping the ` or `
separator from the message now fails it. All four of DA1's killed mutants still
die. Every acceptance check is green.

One justified deviation: a fifth file, `docs/MAP.md`. It is generated, and I
proved the lint gate forces it (below).

## Privacy

Method: both files parsed with `csv.DictReader`; for each fixture column, the
set of its four cell values compared for **exact equality** against the set of
all 8833 real values in that column. Substring matching is not used anywhere.
The operator's CSV was opened read-only and never written. No real value is
reproduced here or anywhere in this file.

Headers: 24 columns, fixture header byte-identical to the real export's first
line (`cmp` of the two header lines — identical). That is the header only, as
the plan specifies; column *names* are not operator data.

| Fixture column | Class | Verdict | Evidence |
| --- | --- | --- | --- |
| `generation_id` | private | clean | `gen-fixture-1..4`, exactly the plan's pattern; no value in the real column's 8833-value set |
| `created_at` | private | clean | four invented round timestamps; no value in the real set |
| `cost_total` | numeric | clean | no value in the real set (exempt anyway) |
| `cost_web_search` | — | clean | empty in all four rows |
| `cost_cache` | — | clean | empty in all four rows |
| `cost_file_processing` | numeric | clean | no value in the real set (see finding 2) |
| `byok_usage_inference` | numeric | exempt | shares 1 value (`0`) — numeric |
| `tokens_prompt` | numeric | clean | no value in the real set |
| `tokens_completion` | numeric | exempt | shares 4 values — numeric |
| `tokens_reasoning` | numeric | exempt | shares 2 values — numeric |
| `tokens_cached` | numeric | clean | no value in the real set |
| `model_permaslug` | public | clean | public model names; no value in the real set |
| `provider_name` | public | exempt | shares 2 values — public provider names |
| `variant` | public | exempt | shares 1 value |
| `cancelled` | public | exempt | shares 2 values |
| `streamed` | public | exempt | shares 1 value |
| `user` | private | clean | all four rows `fixture-user`; not in the real set (2 distinct real values) |
| `finish_reason_raw` | public | exempt | shares 1 value |
| `finish_reason_normalized` | public | exempt | shares 1 value |
| `generation_time_ms` | numeric | clean | no value in the real set |
| `time_to_first_token_ms` | numeric | clean | no value in the real set |
| `api_key_disabled` | boolean flag | clean (see finding 1) | fixture is `false` in all four rows; the real column's only two values are `false`/`true` |
| `api_key_name` | private | **clean — the blocker is fixed** | all four rows `fixture-key`; not in the real set (3 distinct real values) |
| `app_name` | private | clean | all four rows `fixture-app`; not in the real set (3 distinct real values) |

History, `git log -p` over everything reachable from `task/DA1b`
(6 140 876 characters of patch text), counting exact occurrences of each real
value:

| Value under test | `task/DA1b` | `task/DA1` (control) |
| --- | --- | --- |
| real `api_key_name` #1 (the leaked one) | **0** | 4 |
| real `api_key_name` #2, #3 | 0 | 0 |
| real `user` (only non-empty value) | 0 | 0 |
| real `app_name` #1 | 129 | 129 |
| real `app_name` #2 | 40 | 44 |

The control column proves the scan would have caught the leak. The `app_name`
counts are pre-existing repo content unrelated to this fixture (DA1's review
recorded the same values at base); the 44 → 40 drop is exactly DA1's four
fixture rows, now synthetic. Restricting the scan to `71b21aa..task/DA1b`
(11 073 characters — this commit alone) gives **0 occurrences of every one of
those six real values**: the new commit introduces no operator data at all.

`git merge-base --is-ancestor da1 task/DA1b` → false. DA1's leaking commit is
not in this branch's history; the branch is one commit on `main`.

## Checks

Throwaway clone of `/home/dalhaka/factory/ws/oi1/DA1b` at `task/DA1b`
(`7d9f2345988e2c7f009b7658bd67f7e81d27d9e7`), base
`71b21aa1c2c0142a6afe1d9b75bc2dda9bb04024`.

| Item | Result |
| --- | --- |
| Commits on base | 1 |
| Files touched | `tests/ledger/fixtures/activity-export.csv`, `tests/ledger/test_factory.py`, `tools/ledger/factory.py`, `tools/ledger/schema.md`, **`docs/MAP.md`** (fifth file — generated; see Deviations) |
| `factory.py` vs DA1 | identical (`git diff --quiet da1 HEAD -- tools/ledger/factory.py`) |
| `schema.md` vs DA1 | identical |
| Diff vs DA1 limited to fixture + test | yes — the only other change is the generated `docs/MAP.md` |
| Commit subject | byte-identical to DA1's and to the plan's (`cat -A`, trailing `$` only) |
| Trailers | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present; `Generated-By: dsh …` extra (allowed) |
| Fixture trailing newline | present (`od -c` → `\n`; DA1's ended in `s`); no `\ No newline` marker in the diff |
| `nix build .#checks.x86_64-linux.ledger-unit -L --no-link` | pass — 39 passed |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | pass — treefmt 84 files 0 changed, shellcheck, `render.test.mjs` all assertions passed |
| `nix develop -c pytest tests/ledger -q -p no:cacheprovider` | 39 passed |
| `nix develop -c ruff check tools/ledger tests/ledger` | All checks passed |
| Working tree after every experiment | clean |
| Operator's CSV | opened read-only, never written; no real value copied into the repo or this review |

`docs/MAP.md` is load-bearing, not gratuitous: with it reverted to the base
version, `nix build .#checks.x86_64-linux.lint` **fails** with
`repomap: docs/MAP.md is stale — run: python3 pkgs/evidence/repomap.py write`.
The reason DA1 passed lint with a stale map is that the repomap stale-check was
wired into `githooks/pre-commit` and `flake.nix` in a commit landed *between*
DA1's base (`9083845`) and DA1b's base (`71b21aa`). The new fixture takes
`tests/ledger` from 12 to 13 files, so the one-line regeneration is forced.

## Red before green

Base `factory.py` with HEAD's tests (`git checkout 71b21aa -- tools/ledger/factory.py`):

```
FAILED test_load_activity_reads_the_real_openrouter_export
FAILED test_load_activity_unknown_shape_names_both_shapes
  AssertionError: assert 'date, model, cost or created_at, model_permaslug, cost_total' in
    'activity export must have columns date, model, cost; found: foo, bar, baz'
2 failed, 37 passed
```

DA1's red reproduces, and the tightened assertion is red at base for the right
reason. `factory.py` restored; tree clean.

The privacy fix itself has no red-before-green and cannot have one: no test
reads `api_key_name`, `user`, `app_name` or `generation_id`. I made that
explicit rather than assumed it — control M6 below. The load-bearing evidence
for this round is the exact-field comparison and the history scan, not a test,
and that is the right shape for the fix.

## Mutation table

| # | Mutation | Verdict | Killed by |
| --- | --- | --- | --- |
| M1 | `date = row["created_at"]` (keep the full timestamp) | killed | `test_load_activity_reads_the_real_openrouter_export` (1 failed, 38 passed) |
| M2 | `model = row["provider_name"]` | killed | same test — buckets keyed on `CoreWeave`/`DeepInfra` |
| M3 | `continue` on `cancelled == "true"` | killed | same test — the 2026-09-05 flash bucket drops 0.0005 → 0.00025 |
| M4 | `if not has_export:` (reject the legacy shape) | killed | 9 tests, incl. `test_load_activity_legacy_shape_still_parses`, `test_rollup_week_windows_activity_export` |
| M5 | drop the `" or "` separator between the two column sets | **killed (was the DA1 survivor)** | `test_load_activity_unknown_shape_names_both_shapes` — message reads `…cost created_at…`, phrase absent |
| M6 | control: replace the fixture's synthetic private cells with *different* invented placeholders | **survives by design** | nothing — 39 passed, confirming no test reads those columns and the privacy fix is behaviour-neutral |

All four of DA1's killed mutants still die; the fifth is now closed.

## Findings

1. **(observation) `api_key_disabled` shares its value with the real export.**
   The fixture's `false` also occurs there, and the column is not on the gate's
   named public list. It is a two-valued boolean flag (`false`/`true` are the
   only values in the real column) in the same class as `cancelled` and
   `streamed`: it carries no operator data and cannot identify a key. Recorded
   as a documented exception, not a leak.
2. **(minor, carried from DA1, out of DA1b's scope) `cost_file_processing` is a
   single space** `" "` in all four fixture rows, where the real export has an
   empty cell. Nothing reads the column and `float()` is never applied to it, so
   it is inert, but a fixture that advertises the real export's shape should
   carry `""`. DA1b correctly touched only the four id/user/key/app columns, so
   this is not a defect of this round. Worth one character in whatever next
   touches the fixture.
3. **(observation, pre-existing) A real `app_name` value occurs 40× in the
   repo's history** outside this fixture (129× for a second value), unchanged by
   this round and present long before DA1. If the operator considers those
   values sensitive, that is a separate cleanup item; they look like tool
   identifiers rather than personal data, and this gate takes no position.
4. **(observation, pre-existing, out of scope, carried from DA1 finding 4)**
   `rollup --activity` on a CSV of an unknown shape still exits with a Python
   traceback rather than the clean `ActivityExportError` message. Same at base.

## Deviations

- **`docs/MAP.md` is a fifth file**, outside the plan's declared `touches`
  (`tests/ledger/fixtures/activity-export.csv`, `tests/ledger/test_factory.py`).
  Accepted: it is machine-generated, the change is one line (`12 files` →
  `13 files`), and I proved the lint gate refuses the commit without it. The
  commit body names the regeneration. The plan's `touches` for DA1b was written
  before the repomap check existed on `main`; the plan is what is stale here,
  not the commit.
- **The plan's Step 2 red was performed by the implementer as a mutation**
  (drop ` or `, see the test fail, revert) rather than as a base-state red. I
  reproduced both: the mutation (M5) and the base-state red. Both are red for
  the right reason. No deviation in substance.
- The plan's PRIVACY line says "never open the operator's export in this round"
  — that binds the implementer, and the transcript shows they did not. This gate
  must open it to verify, and did so read-only.
- No other deviation. The commit subject, the trailers, the carried files, the
  synthetic values and the acceptance set all match the plan.
