# Opus gate — seat run sc1, task G4 — APPROVED

Branch head `e3f101e3eafe` (`~/factory/ws/sc1/G4`, `task/G4`, parent `68181b60ea37` = task/G1, base `f1180c3`). Reviewer: Opus, high effort, throwaway clone; checks re-run by ref.

## Summary

APPROVED. G4 appends exactly the ten interfaces its plan section names — `touches_overlap`, `open_tasks`, `waves`, `seat_groups`, `factory_args`, `conflicts`, `check`, `render_brief`, `main` (plus the private `_find_cycles`) — to G1's `tasks.py`, and the behaviour matches the plan rather than merely compiling. `open_tasks` covers only `ready` and `blocked` as the Interfaces comment demands (`pkgs/evidence/tasks.py:350`); `waves` is a real Kahn layering whose landed-dep shortcut is proven both ways. The one place the implementer departed from the plan's literal skeleton — dropping the plan's unused `known` variable and collapsing the two-clause `ready` predicate to `all(d in done for d in deps[k])` — is provably equivalent: `deps[k]` already excludes landed roots and `done` only ever holds node keys, so "every dep done" and the plan's "(done or not a node) and (a node or landed)" accept exactly the same set; I checked all four dep cases (landed / node-and-done / node-not-done / not-a-node-not-landed) and they agree. Red before green is shown by ref: with HEAD's tests and G1's `tasks.py`, 9 of the new 9 tests fail with the predicted `AttributeError: module 'tasks' has no attribute 'touches_overlap'` and friends. Twenty-six mutations were run; all seven behaviours the gate names as load-bearing (Kahn ordering, seat-group merging, the directory-prefix rule, cycles, unknown keys, the rejected line, `open_tasks` scope) were killed, along with thirteen more (landed-dep handling, wave sort, group sort, CLI exit code, CLI seat-group rendering, brief counts, brief Next-wave line, `factory_args` spec/touches, `conflicts` emptiness). Subject is byte-identical to the plan's `commit subject`, `touches` is respected exactly (3 files, no strays), both trailers present, no bypass flags, no new `2>/dev/null`, stdlib only, no writes outside the workspace, no secrets, implementer tree clean. The real-data probe is clean: `check` exits 0 and `brief` renders with no traceback; `docs/ledger/repos.toml` does **not** exist yet (G3 adds it), so the graph has zero repos and the table is empty — the plan's stated expected output, not a failure. Nothing was loosened to get there. Seven mutants survived, all of them coverage gaps in tests the plan dictated verbatim (the implementer copied the plan's Step-2 block byte-for-byte, so none is an implementer deviation) and none of them a behaviour defect — the most consequential, the claims `owner == "operator"` filter, is proven correct against live data: `docs/ledger/claims.toml` holds 20 `gap` rows, 14 of them `owner = "orchestrator"`, and the rendered brief lists exactly the 6 operator ones. Minors only; fold them into G5/G8, which touch the same module.

## Checks

- green — `evidence-unit` (`nix build .#checks.x86_64-linux.evidence-unit -L --no-link`): exit 0, out path `/nix/store/2nlrps68yqy4y9bb9yc514zj62k59ib9-evidence-unit`. First run was a store hit, so I forced it: `--rebuild` re-executed the derivation — `evidence-unit> 47 passed in 3.24s`, exit 0. The check copies `pkgs/evidence` and `tests/evidence` wholesale (`flake.nix:951-971`), so the new tests are genuinely inside it.
- green — `lint` (`nix build .#checks.x86_64-linux.lint -L --no-link`): exit 0, out path `/nix/store/08gk2z4yj50snn7psxl5adrkddlpzks2-lint`. Decisive lines: `lint> formatted 80 files (0 changed)`, `lint> All checks passed!`, `lint> 31 files already formatted`.
- green — `githooks/pre-commit` (`nix develop -c githooks/pre-commit`): exit 0. `traversed 304 files`, `formatted 80 files (0 changed)`, `All checks passed!`, `31 files already formatted`, `render.test.mjs: all assertions passed`.
- green — devShell suite (`nix develop -c pytest tests/evidence -q`): `47 passed in 4.36s`.
- green — touches contract: `git show --name-only --format= HEAD` = exactly `pkgs/evidence/tasks.py`, `tests/evidence/fixtures/plans/second.md`, `tests/evidence/test_tasks.py` — the plan's three `touches` entries, nothing else. 586 insertions, 0 deletions (the plan says "append").
- green — commit subject + trailers: subject `cmp`-identical to the plan's `commit subject` line (`SUBJECT-IDENTICAL`). `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present, preceded by the expected machine-set `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sc1)`.
- green — Interfaces roll-call: `touches_overlap:334`, `open_tasks:347`, `waves:353`, `seat_groups:378`, `factory_args:411`, `conflicts:432`, `check:486`, `render_brief:518`, `main:590`, `if __name__ == "__main__": raise SystemExit(main())` at the end. `main`'s argparse offers `brief | json | waves --repo [--plan] [--factory-args] | conflicts [--repo] | check` with `--root/--repos/--plan-status/--runs-dir/--store/--claims` defaults exactly as specified.
- green — Decision 3 / `open_tasks` scope: `pkgs/evidence/tasks.py:350` filters to `("ready", "blocked")` only; approved/rejected/ran/recorded are excluded. Mutation M9 proves the test pins it.
- green — `check` message formats: all four rules present and all four strings match the plan's wording verbatim (`unknown key`, `cycle in <repo>: A -> B -> A`, `(code) has no acceptance`, `defined in a.md and b.md`).
- green — tests are the plan's, unweakened: the appended block is the plan's Step-2 code with `ruff format` line wrapping only; no assertion was dropped or softened. Verified line by line against the plan section.
- green — hard-rule scan: `git show HEAD | grep` for `sudo|nixos-rebuild|systemctl|--no-verify|2>/dev/null` → no hits. Imports in `tasks.py` are stdlib only (`argparse datetime fnmatch glob json os pathlib re subprocess sys tomllib`) plus the lazy `import evidence` inside the function, as G1 specified. No file writes anywhere in the module (only `open(..., "rb")` reads). No secrets. `git -C ~/factory/ws/sc1/G4 status --porcelain` empty.
- green — prompt-garble handling (worth recording): the seat's task text had the factory's WORKSPACE RULES block substituted into the plan's Step-1 fixture code block. The implementer identified it as an injection/transcription artefact, refused to treat it as fixture content, and used the repo plan file's real `second.md` (`~/factory/runs/sc1/G4.log:167,1186`). The committed fixture matches the plan's block byte-for-byte apart from the missing final newline. Correct handling.

## Red before green

By ref, in the throwaway clone: `git checkout HEAD~1 -- pkgs/evidence/tasks.py` (G1's module, HEAD's tests), then `nix develop -c pytest tests/evidence/test_tasks.py -q` → exit 1, `9 failed, 11 passed in 0.12s`. Decisive lines: `FAILED tests/evidence/test_tasks.py::test_touches_overlap - AttributeError: m...` — the exact `AttributeError` the plan's Step 3 predicts — plus `test_waves_follow_dependencies_and_skip_landed`, `test_seat_groups_merge_overlapping_touches`, `test_factory_args_shape`, `test_conflicts_across_plans`, `test_check_reports_unknown_dep_cycle_and_missing_acceptance`, `test_check_reports_duplicate_key`, `test_brief_lists_counts_next_wave_and_operator_items`, and `test_cli_check_and_json`. The last one fails differently and instructively: `assert (0 == 1)` — with no `main()` and no `__main__` guard in G1's file, running `tasks.py check` as a script imports and exits 0 with empty stderr, so the CLI test's `returncode == 1 and "cycle" in r.stderr` is a real assertion about the CLI existing, not a smoke test. Restored with `git checkout HEAD -- pkgs/evidence/tasks.py`; `git status --porcelain` clean afterwards. The implementer's own transcript shows the same red (`~/factory/runs/sc1/G4.log:1212`, "9 failed").

## Mutation table

Twenty-six mutations, each a single-site edit to `pkgs/evidence/tasks.py`, run against `nix develop -c pytest tests/evidence/test_tasks.py -q` and reverted.

| mutation | killed | by |
|---|---|---|
| M1 — `waves` ignores dependencies (`deps[k] = set()` for every node) | yes | `test_waves_follow_dependencies_and_skip_landed` (1 failed, 12 passed) |
| M2 — `seat_groups` stops merging (union guarded by `False and ...`) | yes | `test_seat_groups_merge_overlapping_touches` |
| M3 — `touches_overlap` loses the directory-prefix rule (both `startswith` clauses removed) | yes | `test_touches_overlap` — `AssertionError` on `docs/board` vs `docs/board/log.md` |
| M4 — `check` stops reporting cycles (`for cycle in []`) | yes | `test_check_reports_unknown_dep_cycle_and_missing_acceptance` |
| M5 — `check` stops reporting unknown keys | yes | `test_check_reports_unknown_dep_cycle_and_missing_acceptance` |
| M6 — `check` stops reporting duplicate keys | yes | `test_check_reports_duplicate_key` |
| M7 — `check` stops reporting missing acceptance | yes | `test_check_reports_duplicate_key` |
| M8 — `render_brief` drops the "Rejected, fix round owed" line | yes | `test_brief_lists_counts_next_wave_and_operator_items` |
| M9 — `open_tasks` also returns rejected/approved/ran/recorded | yes | `test_brief_lists_counts_next_wave_and_operator_items` |
| M10 — `conflicts` returns nothing (every pair skipped) | yes | `test_conflicts_across_plans` |
| M11 — `factory_args` emits `"touches": []` | yes | `test_factory_args_shape` |
| M12 — `render_brief` drops the "Untracked plans" line entirely | **no** | 20 passed — no test asserts the line (minor 4) |
| M13 — `render_brief` drops the `owner == "operator"` filter (any `gap` row is listed) | **no** | 20 passed — the test asserts `"orchestrator" not in md`, but the mutant emits the row's `id` (`"x"`), never the word `orchestrator` (minor 1) |
| M14 — `waves` loses the sort inside a wave (reversed) | yes | `test_waves_follow_dependencies_and_skip_landed` |
| M15 — `factory_args` ignores the `plan` filter | **no** | 20 passed — only one plan is loaded in that fixture (minor 2) |
| M16 — `conflicts` also pairs tasks within one plan (cross-plan restriction dropped) | **no** | 20 passed — no two tasks inside one fixture plan share a touch (minor 3) |
| M17 — `waves` counts a landed dep as unsatisfied (`if True` in the deps comprehension) | yes | `test_waves_follow_dependencies_and_skip_landed` |
| M18 — brief counts every task in the `landed` column | yes | `test_brief_lists_counts_next_wave_and_operator_items` |
| M19 — brief's `legacy open` counts every legacy row, not `status == "open"` | **no** | 20 passed — the fixtures carry no legacy rows (minor 5) |
| M20 — CLI `check` always exits 0 | yes | `test_cli_check_and_json` |
| M21 — CLI `waves` prints raw keys instead of `seat_groups` | yes | `test_cli_check_and_json` (`'"X1"'` vs `X1`) |
| M22 — `render_brief` drops the "Next wave" line | yes | `test_brief_lists_counts_next_wave_and_operator_items` |
| M23 — `conflicts` swaps `path_a`/`path_b` | **no** | 20 passed — both paths are the same string in the fixture (minor 6) |
| M24 — `seat_groups` no longer sorts groups by first key (reversed) | yes | `test_seat_groups_merge_overlapping_touches` |
| M25 — `factory_args` emits an empty `spec` | yes | `test_factory_args_shape` |
| M26 — CLI `json` prints only repo names instead of the graph | **no** | 20 passed — the test only reads `["repos"][0]["name"]` (minor 7) |

## Real-data probe

Read-only, against `/home/dalhaka/nixos-agent-env` with `--runs-dir /home/dalhaka/factory/runs`.

- `check` → exit 0, no output, no traceback.
- `docs/ledger/repos.toml` does **not** exist yet (`docs/ledger/` today holds only `claims.toml` and `openrouter-prices.csv`); G3 adds it. So `load_repos` returns `[]` and the graph has zero repos — the plan's Step 6 names this exact outcome as expected, not a failure.
- `brief` → exit 0, verbatim:

```
# Task brief (generated 2026-09-05T17:48:09Z)

| repo | landed | approved | rejected | ran | recorded | ready | blocked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|

**Next wave** — none
**Rejected, fix round owed:** none
**Operator owns:** o4-framing-test (review by 2026-09-12) · d5-activity-export (review by 2026-09-12) · s12-commit-metadata-decision (review by 2026-09-12) · xhigh-restore-or-keep-medium (review by 2026-09-12) · seat-key-exception-undecided (review by 2026-09-12) · nixpkgs-host-pin-age (review by 2026-10-05)
**Untracked plans (no typed headings, no plan-status row):** none
```

- No checker was loosened. `check`'s four rules are all present and all four message strings are the plan's verbatim; the reason it is silent is that there are no repos to check, not that a rule was weakened. Nothing in the diff relaxes a parser or swallows an error.
- The live claims data is also the strongest evidence against M13 being a defect rather than a coverage gap: `docs/ledger/claims.toml` has 28 claims, 20 with `status = "gap"`, of which 14 are `owner = "orchestrator"` and 6 `owner = "operator"`. The brief lists exactly the 6 operator ones and none of the 14 orchestrator ones, so the filter demonstrably works today.

## Findings

- **minor** `pkgs/evidence/tasks.py:569` (test at `tests/evidence/test_tasks.py:404`) — The `owner == "operator"` filter on `claims_rows` is not pinned. The test's intent is visible in `assert "o4-framing-test" in md and "orchestrator" not in md`, but the brief never prints an owner, only an `id`, so dropping the owner clause leaves the assertion true (M13 survived). The behaviour is correct today (proven on live claims above); the test is vacuous on it. **Fix:** give the non-operator claim a recognisable id and assert on that — change the second claims row to `{"id": "orch-only", "status": "gap", "owner": "orchestrator"}` and assert `"orch-only" not in md`. Wording inherited from the plan's Step 2, so it is the plan's gap, not the implementer's. Fold into G5 or G8.
- **minor** `pkgs/evidence/tasks.py:416` — `factory_args`'s `plan` filter is unpinned (M15): the fixture graph in `test_factory_args_shape` loads only `typed.md`, so a `factory_args` that ignores `plan` passes. This one has teeth downstream — `waves --factory-args` without the filter would hand `dark-factory.js` tasks from a different plan. **Fix:** build the graph from `["typed.md", "second.md"]` in that test and assert `{a["key"] for a in args} == {"E3", "E5", "E7", "D1"}` (no `X*`).
- **minor** `pkgs/evidence/tasks.py:438` — The cross-plan restriction in `conflicts` is unpinned (M16): no two tasks inside one fixture plan share a touch, so pairing same-plan tasks changes nothing. **Fix:** add a task to `second.md` (or `typed.md`) that overlaps a sibling in the *same* plan and assert no row names that pair.
- **minor** `pkgs/evidence/tasks.py:584` — The "Untracked plans" line can be deleted with every test still green (M12). It is part of the brief's stated contract and G8's board block will consume the brief's shape. **Fix:** assert `"**Untracked plans (no typed headings, no plan-status row):** none"` in `test_brief_lists_counts_next_wave_and_operator_items`, and add a case with one untracked plan.
- **minor** `pkgs/evidence/tasks.py:532` — `legacy open` counting (`status == "open"` vs all rows) is unpinned because no fixture repo has legacy plans (M19). **Fix:** cover it when G3's `plan-status.toml` lands — one legacy row with `status = "done"` and one with `"open"`, asserting the column reads 1.
- **minor** `pkgs/evidence/tasks.py:450` — `path_a`/`path_b` orientation is unpinned (M23) because the only asserted conflict has the same path on both sides. **Fix:** add an overlapping-but-different pair (e.g. `docs/board` vs `docs/board/log.md`) and assert which side each lands on.
- **minor** `pkgs/evidence/tasks.py:638` — The CLI `json` payload is asserted only via `["repos"][0]["name"]` (M26); replacing the whole graph with a name list still passes. **Fix:** also assert `"generated" in doc` and that a task carries `state`/`touches`.
- **minor** `pkgs/evidence/tasks.py:601-608` — `waves --factory-args` without `--plan` silently prints `[]` (`factory_args(repo, None)` matches no task) rather than erroring or defaulting. Easy to mistake for "no open tasks". **Fix:** make `--factory-args` require `--plan`, or treat `--plan None` as "all plans".
- **minor** `tests/evidence/fixtures/plans/second.md:25` — No terminating newline (`\ No newline at end of file`). Cosmetic, but every future diff of the fixture re-touches its last line. **Fix:** `printf '\n' >> tests/evidence/fixtures/plans/second.md`.
- **nit** `pkgs/evidence/tasks.py:437` — `conflicts` calls `open_tasks(repo_graph)` inside the inner loop, rebuilding the list once per outer task. Harmless at five repos; a one-line hoist to a local.

## Deviations

- `waves` (`pkgs/evidence/tasks.py:353-376`) does not reproduce the plan's Step-4 skeleton literally: the unused `known = {chain_root(k) for k in repo_graph["chains"]} | set(nodes)` line is dropped, and the two-clause readiness predicate `all(d in done or d not in nodes for d in deps[k]) and all(d in nodes or d in landed for d in deps[k])` is written as `all(d in done for d in deps[k])`. Both are correct: `known` is dead (statix/deadnix's Python analogue would not catch it, but ruff's F841 would have, had it been assigned and unused in a way ruff flags), and the predicates are equivalent because `deps[k]` is already filtered to non-landed roots and `done ⊆ nodes` — checked case by case above, and pinned by M1/M14/M17 all being killed. Recorded, not held against the task.
- `check`'s duplicate-key message joins the full plan list with `" and "`, so three plans would read `a.md and b.md and c.md`. The plan only specifies the two-plan wording. Harmless generalisation.
- Both trailers (`Generated-By` then `Co-Authored-By`) are present. The plan's Global Constraints name only `Co-Authored-By`; the seat's own rules name only `Generated-By`. The implementer reasoned about the conflict explicitly (`~/factory/runs/sc1/G4.log:1367-1393`) and matched G1's established pattern. Expected per the gate brief.
