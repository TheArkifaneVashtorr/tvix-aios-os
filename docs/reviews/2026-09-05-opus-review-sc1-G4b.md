---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run sc1, task G4b — APPROVED

Branch head `265c043b2382` (`~/factory/ws/sc1/G4b`, `task/G4b`, parent `8d4bc7f8d6af` = task/G1b tip). Reviewer: Opus, high effort, throwaway clone; checks re-run by ref. Baseline: `docs/reviews/2026-09-05-opus-review-sc1-G4.md` (26 mutations, nine minors, two with teeth).

## Summary

APPROVED. G4b is a faithful re-application of G4 onto G1b plus exactly the two pins the plan asked for. The strongest evidence is mechanical: the lines G4b adds to `pkgs/evidence/tasks.py` are **byte-identical** to the lines G4's `e3f101e` adds — same four imports (`argparse`, `fnmatch`, `json`, `sys`) in the same hunk, same 352-line append after `build` — so there is *no* behavioural difference to adjudicate between the two branches' scheduling code; the merge with G1b's parser and status changes was pure context (G1b's file is six lines longer before the append point, hence `@@ -331,3 +335,352 @@` here against `@@ -325,3 +329,352 @@` there), and G1b's `parse_plan`/`derive_status` are untouched. The test-file diff against G4 is exactly three edits, all of them the plan's Step 2: the non-operator claim becomes `id = "orch-only"` with `assert "orch-only" not in md`; `test_factory_args_shape` loads `typed.md` **and** `second.md` and asserts both that `factory_args(g, "typed.md")` excludes every `X*` key and that `factory_args(g, "second.md") == {"X1","X2","X3"}`; and `second.md` gains its terminating newline. Both pins are load-bearing under the exact mutations the plan names — dropping `owner == "operator"` makes the brief test fail with `'orch-only' is contained here`, and neutering the `plan` filter makes `test_factory_args_shape` fail with `Extra items in the left set: 'X2' 'X1' 'X3'` — and both revert to green. Fifteen of G4's killed mutations were re-run against this branch and all fifteen still die; the one G4 survivor I re-tested (the cross-plan restriction in `conflicts`, G4's M16) still survives, unchanged and out of G4b's scope. `evidence-unit` (51 passed, forced rebuild), `lint` and the pre-commit gate are all green by ref, one commit on base, three files exactly as `touches` names, subject byte-identical to G4's plan subject, to G4b's plan subject and to `e3f101e`'s own subject, both trailers present, stdlib only, no writes outside the workspace, sibling workspaces untouched. The real-data probe is stronger than G4's could be: with G3's `repos.toml` and `plan-status.toml` supplied read-only from its workspace, `check` sees all five repos and still exits 0 — no unknown keys, no cycles, no code task without acceptance, no duplicate keys across real plan text — and `brief`/`conflicts`/`waves` all render. Two findings for the orchestrator come out of that run, neither caused by G4b.

## Checks

- green — `evidence-unit` (`nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild`): exit 0, `evidence-unit> 51 passed in 3.07s`, out path `/nix/store/qmkafpm8kf6idx3bq212lh231qb0jlpg-evidence-unit`. Forced with `--rebuild` so the derivation really re-executed rather than hitting the store. G1b's tests and G4's tests pass together (G1b alone was 27; G4 alone was 47; 51 here).
- green — `lint` (`nix build .#checks.x86_64-linux.lint -L --no-link`): exit 0, out path `/nix/store/77rsq0xnsmsk07kmaj4jm0pnv45b9lmw-lint`. Decisive lines: `lint> traversed 315 files`, `lint> formatted 80 files (0 changed) in 552ms`, `lint> All checks passed!`, `lint> 31 files already formatted`.
- green — `githooks/pre-commit` (`nix develop -c githooks/pre-commit`): exit 0. `traversed 315 files`, `formatted 80 files (0 changed)`, `All checks passed!`, `31 files already formatted`, `render.test.mjs: all assertions passed`.
- green — devShell suite (`nix develop -c pytest tests/evidence -q -p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`): `51 passed in 4.16s`.
- green — one commit on base: `git rev-list --count 8d4bc7f..HEAD` = 1; `HEAD^` = `8d4bc7f8d6afdea7d19268b32ca1b0786de1bcdc` (task/G1b tip, as `G4b.result`'s `base:` line says). No amend of the base, no merge commit.
- green — touches contract: `git show --name-only --format= HEAD` = exactly `pkgs/evidence/tasks.py`, `tests/evidence/fixtures/plans/second.md`, `tests/evidence/test_tasks.py` — the plan's three entries, nothing else. `--numstat`: `353 0`, `25 0`, `210 0` — 588 insertions, **0 deletions**, so nothing of G1b's was removed.
- green — subject: `cmp` against the plan's `### G4` `commit subject` (`G4-PLAN-SUBJECT-IDENTICAL`), against the plan's `### G4b` `commit subject` (`G4B-SUBJECT-IDENTICAL`), and against `git -C ~/factory/ws/sc1/G4 log -1 --format=%s e3f101e` (`G4-COMMIT-SUBJECT-IDENTICAL`). All three byte-identical. This is what marks the G4 chain landed.
- green — trailers: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sc1)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`, matching G1's and G1b's pattern.
- green — **cherry-pick fidelity (the core of step 2)**: `git show e3f101e -- pkgs/evidence/tasks.py` and `git show HEAD -- pkgs/evidence/tasks.py`, reduced to their added lines, are identical (`diff -u` → no output, 353 lines each). Every one of the ten interfaces — `touches_overlap`, `open_tasks`, `waves`, `seat_groups`, `factory_args`, `conflicts`, `_find_cycles`, `check`, `render_brief`, `main` — is character-for-character G4's, including the simplified Kahn predicate `all(d in done for d in deps[k])` that G4's review analysed and cleared. **Zero differences to report.** The only structural difference between the two commits' diffs is the append offset (`-331,3 +335,352` vs `-325,3 +329,352`), which is G1b's six extra lines of parser/status code, not a code change.
- green — G1b preserved: the pre-append region of `pkgs/evidence/tasks.py` differs from `HEAD^`'s only in the four added imports (hunk `@@ -2,12 +2,16 @@`); `parse_plan`, the fence toggle, `CHAIN_RE`, `derive_status` and `read_recorded` are untouched by this commit (0 deletions).
- green — test-file diff vs G4: three edits, all the plan's (`repo_with(tmp_path, ["typed.md", "second.md"])` in `test_factory_args_shape`; two new assertions there; the `orch-only` claim id and its assertion). No assertion softened or removed apart from the vacuous `"orchestrator" not in md` that the plan replaces.
- green — `second.md`: identical to G4's fixture apart from the added terminating newline (`od -c` last byte `\n`).
- green — hard-rule scan: `git show HEAD | grep -E 'sudo|nixos-rebuild|systemctl|--no-verify|--no-gpg-sign|2>/dev/null|mount --'` → no hits. Imports in `tasks.py` are stdlib only (`argparse datetime fnmatch glob json os pathlib re subprocess sys tomllib`) plus the lazy `import evidence` at line 206; the test file imports `importlib.util json os pathlib subprocess sys`. Every `open()` in the module is `"rb"` — no writes anywhere. No secrets.
- green — workspace hygiene: `git -C ~/factory/ws/sc1/G4b status --porcelain` empty (only ignored caches and `.factory-meta` under `--ignored`). `git -C ~/factory/ws/sc1/G4 status --porcelain` empty — the sibling workspace was fetched from, never written. Nothing in the transcript writes outside the workspace.

## Red before green (the mutation reds)

The two pins, each applied to `pkgs/evidence/tasks.py` in the clone, run against the single test that pins it, then reverted.

- **(a) drop `owner == "operator"`** — `if c.get("status") == "gap" and c.get("owner") == "operator":` → `if c.get("status") == "gap":`. `pytest -k test_brief_lists_counts_next_wave_and_operator_items` → exit 1, `1 failed, 23 deselected`:

```
>       assert "o4-framing-test" in md and "orch-only" not in md
E       AssertionError: assert ('o4-framing-test' in '# Task brief ... · orch-only\n...' and 'orch-only' not in ...)
E         'orch-only' is contained here:
E           -09-12) · orch-only
tests/evidence/test_tasks.py:475: AssertionError
```

  This is the assertion G4's M13 could not reach: under G4's fixture the mutant emitted the id `"x"` and the test only looked for the word `orchestrator`, which the brief never prints. Renaming the row to `orch-only` puts the id itself in the assertion, and the mutant now dies.

- **(b) `factory_args` ignores its `plan` argument** — `if t["plan"] != plan:` → `if False and t["plan"] != plan:`. `pytest -k test_factory_args_shape` → exit 1, `1 failed, 23 deselected`:

```
>       assert {a["key"] for a in args} & {"X1", "X2", "X3"} == set()  # plan filter
E       AssertionError: assert {'X1', 'X2', 'X3'} == set()
E         Extra items in the left set:
E         'X2'  'X1'  'X3'
tests/evidence/test_tasks.py:408: AssertionError
```

  G4's M15 survived because that fixture loaded only `typed.md`; loading `second.md` too makes the filter observable. The second added assertion (`factory_args(g, "second.md")` returns exactly `{"X1","X2","X3"}`) pins the same behaviour from the other side and also fails under the mutant. This was the "with teeth" finding: without the filter, `waves --factory-args` would hand `dark-factory.js` tasks from a different plan.

- Both reverted; `pkgs/evidence/tasks.py` restored byte-for-byte, `git status --porcelain` clean, full suite back to `51 passed in 3.09s`. `second.md` ends with a newline (verified by `od -c`, and by the `\ No newline at end of file` marker disappearing from the diff against G4's fixture).

The implementer's own transcript shows the same two reds and the same revert (`~/factory/runs/sc1/G4b.log:129,189-192`).

## Mutation table

Eighteen single-site edits to `pkgs/evidence/tasks.py`, each applied, run against `pytest tests/evidence/test_tasks.py -q`, then reverted; the file was compared to the original after every batch. Fifteen are re-runs of mutations G4's review killed (regression), one is a re-run of a G4 survivor, two are the new pins.

| mutation | G4 table | killed | by |
|---|---|---|---|
| P1 — `render_brief` drops the claims `owner == "operator"` filter | M13 (survived in G4) | **yes** | `test_brief_lists_counts_next_wave_and_operator_items` (1 failed, 23 passed) |
| P2 — `factory_args` ignores its `plan` argument | M15 (survived in G4) | **yes** | `test_factory_args_shape` (1 failed, 23 passed) |
| R1 — `waves` ignores dependencies (`deps[k] = set()`) | M1 | yes | `test_waves_follow_dependencies_and_skip_landed` + `test_brief_...` (2 failed) |
| R2 — `seat_groups` stops merging (union guarded by `False and`) | M2 | yes | `test_seat_groups_merge_overlapping_touches` |
| R3 — `touches_overlap` loses the directory-prefix rule (both `startswith` → `False`) | M3 | yes | `test_touches_overlap` (`AssertionError`) |
| R4 — `check` stops reporting cycles (`for cycle in []`) | M4 | yes | `test_check_reports_unknown_dep_cycle_and_missing_acceptance` + `test_cli_check_and_json` |
| R5 — `check` stops reporting unknown keys | M5 | yes | `test_check_reports_unknown_dep_cycle_and_missing_acceptance` |
| R6 — `check` stops reporting duplicate keys | M6 | yes | `test_check_reports_duplicate_key` |
| R7 — `check` stops reporting missing acceptance | M7 | yes | `test_check_reports_unknown_dep_cycle_and_missing_acceptance` |
| R8 — `render_brief` drops the "Rejected, fix round owed" line | M8 | yes | `test_brief_lists_counts_next_wave_and_operator_items` |
| R9 — `open_tasks` returns every state in `STATES` | M9 | yes | `test_waves_follow_dependencies_and_skip_landed` + `test_brief_...` |
| R10 — `waves` loses the sort inside a wave (`reverse=True`) | M14 | yes | `test_waves_follow_dependencies_and_skip_landed` |
| R11 — `waves` counts a landed dep as unsatisfied (`if True` in the deps comprehension) | M17 | yes | `test_waves_follow_dependencies_and_skip_landed` + `test_brief_...` |
| R12 — CLI `check` always exits 0 | M20 | yes | `test_cli_check_and_json` |
| R13 — `render_brief` drops the "Next wave" line | M22 | yes | `test_brief_lists_counts_next_wave_and_operator_items` |
| R14 — `seat_groups` no longer sorts groups by first key (`reverse=True`) | M24 | yes | `test_seat_groups_merge_overlapping_touches` |
| R15 — `factory_args` emits an empty `spec` | M25 | yes | `test_factory_args_shape` |
| S1 — `conflicts` also pairs tasks within one plan (cross-plan restriction dropped) | M16 (survived in G4) | **no** | 24 passed — unchanged G4 minor, out of G4b's scope (see Findings) |

All fifteen regressions still die. The two pins the plan ordered now die. The one survivor re-tested is the same one G4's review recorded, still a coverage gap and still not a behaviour defect.

## Real data

Read-only, from the clone, against `/home/dalhaka/nixos-agent-env` with `--runs-dir /home/dalhaka/factory/runs`. Nothing was written to the live repo, to `~/factory/runs`, or to any sibling workspace.

**A — the plan's own probe (no `repos.toml` on main yet; G3 not integrated).**

- `python3 pkgs/evidence/tasks.py --root /home/dalhaka/nixos-agent-env --runs-dir /home/dalhaka/factory/runs check; echo exit=$?` → **no output, `exit=0`**, no traceback. Zero repos, so nothing to check — the plan's stated expected outcome.
- `... brief` → exit 0, verbatim:

```
# Task brief (generated 2026-09-05T18:15:15Z)

| repo | landed | approved | rejected | ran | recorded | ready | blocked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|

**Next wave** — none
**Rejected, fix round owed:** none
**Operator owns:** o4-framing-test (review by 2026-09-12) · d5-activity-export (review by 2026-09-12) · s12-commit-metadata-decision (review by 2026-09-12) · xhigh-restore-or-keep-medium (review by 2026-09-12) · seat-key-exception-undecided (review by 2026-09-12) · nixpkgs-host-pin-age (review by 2026-10-05)
**Untracked plans (no typed headings, no plan-status row):** none
```

**B — all five repos, with G3's ledger supplied read-only** (`--repos ~/factory/ws/sc1/G3/docs/ledger/repos.toml --plan-status ~/factory/ws/sc1/G3/docs/ledger/plan-status.toml`). This is the first time the scheduler has been exercised on the real graph.

- `check` → **no output, `exit=0`**. On real plan text across five repos there is not one unknown `dependsOn` key, not one cycle, not one code task with empty acceptance and not one key defined in two typed plans. No checker was loosened to get there: all four rules are present and their message strings are the plan's verbatim (mutations R4–R7 above prove each rule is live and pinned).
- `brief` → exit 0, verbatim:

```
# Task brief (generated 2026-09-05T18:15:29Z)

| repo | landed | approved | rejected | ran | recorded | ready | blocked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 28 | 9 | 3 | 0 | 0 | 1 | 4 | 1 | 0 |
| media | 3 | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0 |
| gaming | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nixos-skill | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dsh-harness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Next wave** — nixos-agent-env: B1 (plan 2026-09-05-backup-audit-paths.md)
**Rejected, fix round owed:** nixos-agent-env/P1flash (P1flash by mcf2) · nixos-agent-env/G1 (G1 by sc1) · nixos-agent-env/G1b (G1 by sc1) · media/W3 (W3 by cw2) · media/W5 (W5 by cw2)
**Operator owns:** o4-framing-test (review by 2026-09-12) · d5-activity-export (review by 2026-09-12) · s12-commit-metadata-decision (review by 2026-09-12) · xhigh-restore-or-keep-medium (review by 2026-09-12) · seat-key-exception-undecided (review by 2026-09-12) · nixpkgs-host-pin-age (review by 2026-10-05)
**Untracked plans (no typed headings, no plan-status row):** none
```

- `conflicts` → exit 0, verbatim:

```
nixos-agent-env: B1 (2026-09-05-backup-audit-paths.md) × G5 (2026-09-05-session-context.md): flake.nix ~ flake.nix
nixos-agent-env: B1 (2026-09-05-backup-audit-paths.md) × G8 (2026-09-05-session-context.md): flake.nix ~ flake.nix
```

- `waves --repo nixos-agent-env` → exit 0, one line: `"B1"`.

No errors anywhere on real data, so there is nothing here to attribute to a G4b bug. Two observations are recorded as findings below for the orchestrator, both about G1b's status derivation and the brief's reading, not about anything this commit changed.

## Findings

- **finding (orchestrator, not a defect in G4b)** `pkgs/evidence/tasks.py:232-249` (`derive_status`, G1b's code) — on real data the brief lists **both** `nixos-agent-env/G1` and `nixos-agent-env/G1b` under "Rejected, fix round owed", each with detail `G1 by sc1`. `_chain_members` pools the chain's keys and rule 2 returns the newest review among them, so the fix-round key `G1b` inherits the root's REJECTED verdict even though `~/factory/runs/sc1/G1b.result` says `status=done` and no gate has run on `G1b` yet. Reading the line literally, the board says a fix round is owed for the fix round. `render_brief` merely lists `state == "rejected"` tasks, so this is not G4's or G4b's code. **Fix (G5/G8, or a note in the plan):** collapse the "Rejected, fix round owed" list to chain roots, or have `derive_status` prefer a chain member's own `result` over an ancestor's review when the member has no review of its own. Worth a decision either way — the current behaviour is arguably right at the *chain* level and only misleading at the *key* level. Same pattern on `P1flash`.
- **minor (carried from G4, unchanged)** `pkgs/evidence/tasks.py:441` — the cross-plan restriction in `conflicts` is still unpinned (S1 above survived on this branch, exactly as G4's M16 did): no two tasks inside one fixture plan share a touch, so dropping `if a["plan"] == b["plan"]: continue` changes nothing. Out of G4b's scope (the plan named only the two findings with teeth). **Fix:** add a task to `second.md` that overlaps a sibling in the same plan and assert no row names that pair. Fold into G5 or G8.
- **minor (carried from G4, unchanged)** the other five G4 minors are untouched and remain open: the "Untracked plans" line is deletable with every test green (G4 M12); `legacy open` counting is unpinned for want of a legacy fixture row (M19); `path_a`/`path_b` orientation is unpinned because the only asserted conflict has the same path on both sides (M23); the CLI `json` payload is asserted only via `["repos"][0]["name"]` (M26); and `waves --factory-args` without `--plan` silently prints `[]` rather than erroring or defaulting. All were explicitly deferred by the fix-round plan; none is a behaviour defect. Fold into G5/G8, which touch this module.
- **minor** `tests/evidence/test_tasks.py:475` — the pin replaced `"orchestrator" not in md` with `"orch-only" not in md` rather than keeping both. Nothing is lost (the brief never prints an owner, so the old clause was vacuous — that is precisely why G4's M13 survived), and the plan's Step 2 dictates the replacement. Recorded only so a future reader does not mistake it for a dropped assertion.
- **nit (carried from G4)** `pkgs/evidence/tasks.py:440` — `conflicts` calls `open_tasks(repo_graph)` inside the inner loop, rebuilding the list once per outer task. Harmless at five repos; a one-line hoist.
- **nit** `~/factory/ws/sc1/G3/docs/ledger/repos.toml` has no terminating newline. G3's file, noted here only because I read it; not G4b's to fix.

## Deviations

- **None in `tasks.py`.** The gate brief asked for every difference between HEAD's scheduling code and `e3f101e`'s; there are none. The added lines are byte-identical and the merge with G1b was pure context. G4's own two recorded deviations (the dropped `known` variable and the collapsed readiness predicate) therefore carry over verbatim, already analysed and cleared in the G4 review; mutations R1/R10/R11 re-confirm the predicate on this branch.
- The commit **body** differs from G4's (it describes the re-application and the two pins). Expected: the plan requires only the *subject* to be byte-identical, and it is.
- The implementer added one assertion beyond the plan's letter — `{a["key"] for a in args} & {"X1","X2","X3"} == set()` on `factory_args(g, "typed.md")`, alongside the plan's `factory_args(g, "second.md")` assertion. A strengthening: it pins the filter from both directions, and both clauses fail under the mutation.
- Both trailers are present (`Generated-By` then `Co-Authored-By`), as in G1, G1b and G4. The plan's Global Constraints name only `Co-Authored-By`; the seat's own rules name only `Generated-By`. Expected per the gate brief.
- The plan's Step 3 real-data command is written without `nix develop`; `python3` is not on this host's PATH by design (CLAUDE.md), so both the implementer and I ran it as `nix develop -c python3 …`. Same program, same result.
- I extended the real-data probe beyond the plan's Step 3 with G3's ledger files (read-only) so the scheduler was exercised on all five repos rather than an empty graph. Additive evidence only; nothing was written to G3's workspace, whose `git status --porcelain` is unchanged.
