---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run oi1, task DA1 — REJECTED

## Summary

The code is right and the tests are load-bearing: `_load_activity` accepts both
column sets, maps `created_at` → `YYYY-MM-DD`, `model_permaslug` → model,
`cost_total` → cost, still counts a cancelled row, and names both accepted sets
on an unknown header. Every acceptance check is green, red-before-green
reproduces, and four of five mutations die. It reads the operator's live export
end to end with no traceback.

It is rejected on the privacy rule, not on behaviour. The synthetic fixture
carries a **real API key name** in its `api_key_name` column — the same value on
all four rows, byte-identical to one of the three distinct `api_key_name` values
in `~/strategy/ledger/openrouter-activity.csv`, and new to this repo (0
occurrences at base `9083845`, 4 at `395aa89`). The fixture was supposed to be
invented apart from the header. One cell, one fix round.

## Checks

Throwaway clone of `/home/dalhaka/factory/ws/oi1/DA1` at `task/DA1`
(`395aa8950deba0095bab5bd100e45606cc981f81`), base
`90838458eb7d65d1a5c7b876abae5549e6d41c05`.

| Item | Result |
| --- | --- |
| Commits on base | 1 |
| Files touched | exactly `tools/ledger/factory.py`, `tools/ledger/schema.md`, `tests/ledger/test_factory.py`, `tests/ledger/fixtures/activity-export.csv` |
| Commit subject | byte-identical to the plan's (verified with `cat -A`) |
| Trailers | `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present; `Generated-By: dsh …` extra (allowed) |
| `nix build .#checks.x86_64-linux.ledger-unit -L --no-link` | pass |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| `nix develop -c githooks/pre-commit` | pass |
| `nix develop -c pytest tests/ledger -q -p no:cacheprovider` | 39 passed |
| `nix develop -c ruff check tools/ledger tests/ledger` | All checks passed |
| Working tree after every experiment | clean |

Behaviour, verified against the code and the tests:

- both shapes accepted (`has_legacy` / `has_export`, `all(...)` over each set);
- `created_at[:10]` → date; the real file's `created_at` is 23 chars,
  `YYYY-MM-DD HH:MM:SS.mmm`, so the slice is the date part;
- `model_permaslug` → model, `cost_total` → cost via `float()`;
- `cancelled` is never consulted, so a cancelled row's cost is counted — and the
  fixture's cancelled row is half of one asserted bucket, so the property is
  actually pinned (see M3);
- unknown header raises `ActivityExportError` naming both sets and the columns
  found;
- `schema.md` documents the mapping, the cancelled rule, and the new error text
  in both places the old wording appeared.

Fixture: 4 data rows (≤ 5), two dates, two models, one cancelled; header
byte-identical to the real export's header line (`diff` of the two first lines
is empty, 24 columns).

Real data, read-only:
`nix develop -c python3 tools/ledger/factory.py rollup --activity /home/dalhaka/strategy/ledger/openrouter-activity.csv`
→ exit 0, 22 output lines, zero `Traceback`, all 22 lines carry a `USD` dollar
figure. Shape only; no user, key or row content is reproduced here. The
operator's CSV was opened read-only and never written.

## Red before green

`git checkout <base> -- tools/ledger/factory.py` with HEAD's tests:

```
FAILED test_load_activity_reads_the_real_openrouter_export
  factory.ActivityExportError: activity export must have columns date, model, cost; found: generation_id, created_at, ...
FAILED test_load_activity_unknown_shape_names_both_shapes
  AssertionError: assert 'created_at, model_permaslug, cost_total' in 'activity export must have columns date, model, cost; found: foo, bar, baz'
2 failed, 9 passed, 28 deselected
```

Exactly the failure the plan's Step 2 demands. `factory.py` restored; the
legacy-shape test passes at base, as it should.

## Mutation table

| # | Mutation | Verdict | Killed by |
| --- | --- | --- | --- |
| M1 | `date = row["created_at"]` (keep the full timestamp) | killed | `test_load_activity_reads_the_real_openrouter_export` (1 failed, 38 passed) |
| M2 | `model = row["provider_name"]` | killed | `test_load_activity_reads_the_real_openrouter_export` |
| M3 | `continue` on `cancelled == "true"` | killed | `test_load_activity_reads_the_real_openrouter_export` |
| M4 | `if not has_export:` (reject the legacy shape) | killed | 9 tests, incl. `test_load_activity_legacy_shape_still_parses`, `test_rollup_week_windows_activity_export`, `test_rollup_activity_export_is_preferred_over_price_table` |
| M5 | drop the `" or "` separator between the two column sets in the error message | **survived** | — the test asserts each set as a substring, not the joined phrasing |

M5 is cosmetic: deleting either column set from the message is still killed by
`test_load_activity_unknown_shape_names_both_shapes`. Recorded, not a blocker.

## Privacy

Method: parsed both files with `csv.DictReader` and compared **exact field
values** (substring greps are useless here — the real `generation_id` values all
contain `gen-1`). The real export has 8833 data rows, 2 distinct `user` values,
3 distinct `api_key_name` values, 3 distinct `app_name` values.

| Fixture column | All four rows | Verdict |
| --- | --- | --- |
| `generation_id` | not in the real value set | clean |
| `created_at` | not in the real value set | clean |
| `cost_total` | not in the real value set | clean |
| `model_permaslug` | not in the real value set (public model names only) | clean |
| `user` | empty | clean |
| `provider_name` | matches real values, but these are public provider names, not operator data | acceptable |
| `app_name` | matches a real value — **already present in the repo 22× at base**, so nothing new is disclosed | acceptable |
| `api_key_name` | **exact match of one of the operator's three real key names; 0 occurrences in the repo at base, 4 at HEAD** | **LEAK — rejection** |

Nothing from the operator's CSV was copied into the repo, the review file, or the
report beyond this finding; the file was read only to compare.

## Findings

1. **(blocker) Real API key name in the fixture.** All four rows of
   `tests/ledger/fixtures/activity-export.csv` put a real `api_key_name` value in
   the second-to-last column. The fixture was specified as synthetic apart from
   the header. Fix: replace that cell on all four rows with an invented name
   (e.g. `fixture-key`); nothing else in the fixture or the tests depends on it —
   no test reads the column, so `ledger-unit` stays green. Re-verify with the
   exact-value comparison, not a grep.
2. **(minor) The fixture has no trailing newline** (`\ No newline at end of
   file`). treefmt does not police CSV so lint is green, but every other fixture
   in the tree ends with one. Add it in the fix round.
3. **(minor) M5 survivor.** `test_load_activity_unknown_shape_names_both_shapes`
   asserts two substrings and would accept the two column sets run together. A
   one-line tightening (assert the full `"… cost or created_at …"` phrase) closes
   it. Optional.
4. **(observation, pre-existing, out of scope)** `rollup --activity` on a CSV of
   an unknown shape still exits with a Python traceback rather than a clean
   message; the same was true at base. Worth a separate item if the operator
   cares about the CLI surface.

## Deviations

- The plan's Step 1 asked for "4 synthetic rows (two dates, two models, one
  cancelled)" — delivered exactly, but "synthetic" was honoured for every column
  except `api_key_name`. That is finding 1.
- FACTORY-NOTES pastes three real result lines with model names and dollar
  figures, as the plan's Step 4 instructed ("no user or key names") — compliant;
  no key or user name appears there.
- No other deviation. The commit subject, the file list, the trailers and the
  acceptance set all match the plan.
