---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run sc1, task G1 — REJECTED

Branch head `68181b60ea37` (`~/factory/ws/sc1/G1`, `task/G1`, base `f1180c3`). Reviewer: Opus, high effort, throwaway clone; checks re-run by ref.

## Summary

REJECTED — not because anything is broken on the surface (both acceptance checks and the lint gate are green, the subject is byte-identical, `touches` is exact, red is shown as predicted), but because the load-bearing half of the module is not defended by a single test. G1's whole reason for existing is the six-level status precedence and the chain algebra; I mutated seven behaviours the plan writes down as contract and only three died. Swapping precedence rules 1 and 2 — making a gate review outrank a landed commit — passes all 38 tests. Deleting rule 1's second clause entirely (`chain has a review/result AND the root's subject is landed ⇒ landed`) passes all 38 tests. Reversing `read_results`' newest-run-wins ordering, keying `landed_keys` by raw key instead of chain root, dropping `scan_repo`'s per-plan re-key of `recorded`, and letting `read_reviews` match the gate header anywhere in a file instead of on line 1 all pass all 38 tests. The tests are verbatim from the plan, so this is a plan gap the implementer inherited rather than sloppiness — but the gate rule is the gate rule: a surviving mutant on a load-bearing behaviour is a vacuous test, and six of them are.

Separately, the real-data probe found a concrete defect the plan's Step 6 expectation did not anticipate. `parse_plan` does not track fenced code blocks, so the fixture markdown quoted inside G1's and G4's own sections is parsed as real tasks: scanning `~/nixos-agent-env` yields eight phantom tasks (`E1 E3 E5 E7 D1 X1 X2 X3`) out of the session-context plan, four of which collide with real keys from the evidence-store plan in the same repo, and two of which (`X2`/`X3`) are a deliberate dependency cycle fixture. G4's `waves()` Kahn sort and G5's seat dispatch both consume exactly this structure, so the pollution has to go before wave 2. This is one guard clause in `parse_plan` plus one fixture line.

Everything else is clean: stdlib only (`datetime glob os pathlib re subprocess tomllib`), no writes outside `tmp_path`, no `sudo`/`nixos-rebuild`/`systemctl`/`--no-verify`/new `2>/dev/null`, no secrets, implementer workspace clean, exactly the four files the section names. Three minors and one equivalent mutant round it out.

## Checks

- green — `evidence-unit` (`nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild`): exit 0; decisive line `evidence-unit> 38 passed in 3.56s`.
- green — `lint` (`nix build .#checks.x86_64-linux.lint -L --no-link --rebuild`): exit 0; decisive lines `lint> formatted 80 files (0 changed)`, `lint> All checks passed!`, `lint> 30 files already formatted`.
- green — lint gate (`nix develop -c githooks/pre-commit`): exit 0; `All checks passed!` / `render.test.mjs: all assertions passed`.
- green — local suite (`nix develop -c pytest tests/evidence -q`): `38 passed in 2.95s`, i.e. E1/E2's existing tests still pass beside the ten new ones.
- pass — spec compliance: `git show --stat HEAD` lists exactly `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `tests/evidence/fixtures/plans/typed.md`, `tests/evidence/fixtures/plans/legacy.md` — no strays. Subject byte-identical to the section's **commit subject**. Trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present, plus the expected machine-set `Generated-By: dsh ...`.
- pass — Interfaces: all 7 module constants and all 13 functions exist with the stated names and signatures (`parse_keys`, `parse_list`, `chain_root`, `parse_plan`, `load_repos`, `load_plan_status`, `landed_subjects`, `read_reviews`, `read_results`, `read_recorded`, `derive_status`, `scan_repo`, `build`), plus the `run` seam and `DEFAULT_RUNS_DIR`/`PLANS_GLOB`.
- pass — hard rules: no `sudo`/`nixos-rebuild`/`systemctl`, no `--no-verify`, no new `2>/dev/null`, stdlib-only imports in `pkgs/evidence/tasks.py`, every test write under `tmp_path`, no secrets in the diff.

## Red before green

`mv pkgs/evidence/tasks.py <scratch>` (tests kept), then `nix develop -c pytest tests/evidence/test_tasks.py -q` → exit 2:

```
tests/evidence/test_tasks.py:18: in load
    src = next(p for p in candidates if p.exists())
E   StopIteration
ERROR tests/evidence/test_tasks.py - StopIteration
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

Exactly the failure Step 3 predicts (`StopIteration` from `load()`). File restored; `git status --porcelain` clean afterwards.

## Mutation table

15 mutations of `pkgs/evidence/tasks.py`, each run against the whole `tests/evidence` suite in the clone.

| mutation | killed | by |
|---|---|---|
| M1 `chain_root` returns `key` (suffix rule dropped) | yes | `test_chain_root`, `test_derive_status_precedence` |
| M2 precedence swapped: newest review outranks a landed subject | **no** | 38 passed — no test has a task that is both landed and reviewed |
| M3 `parse_keys` drops the `(...)` strip | yes | `test_parse_keys_and_list`, `test_parse_typed_plan_reads_every_field` |
| M4 `read_results` ignores workspace origin (hard-codes the repo name) | yes | `test_read_results_attributes_by_workspace_origin` (`KeyError: ('media','W1')`) |
| M5 `parse_list` stops stripping backticks | yes | `test_parse_keys_and_list`, `test_parse_typed_plan_reads_every_field` |
| M6 blocked detail lists every dep, not only the missing ones | yes | `test_derive_status_precedence` (`'E1' not in 'E1, R4'`) |
| M7 chain member order reversed (oldest review wins) | yes | `test_derive_status_precedence` (`rejected != approved`) |
| M8 `read_reviews` matches the gate header anywhere in the file, not line 1 | **no** | 38 passed — the negative fixture `c.md`'s body never matches either |
| M9 `scan_repo` drops the per-plan re-key of `recorded` | **no** | 38 passed — `recorded_all` is empty in the only `scan_repo` test |
| M10 `read_results` reverses the mtime order (oldest run wins) | **no** | 38 passed — no test has one key in two runs |
| M11 `landed_keys` keyed by raw key instead of `chain_root` | **no** | 38 passed — no fixture task key is itself a fix round |
| M12 untyped plans always land in `untracked_plans` (status row ignored) | yes | `test_scan_repo_and_build` (`legacy` empty) |
| M13 `parse_plan` never ends a task at a `## ` / untyped `### ` heading | **no** | 38 passed — `typed.md` ends on the last task, so the reset is never reached |
| M14 `landed_subjects` ignores a non-zero git returncode | no (equivalent) | git prints nothing on stdout when it fails, so the guard is unobservable — not a finding |
| M15 rule 1's second clause removed (chain review/result + landed root ⇒ landed) | **no** | 38 passed — never exercised |

## Findings

- **major** — `tests/evidence/test_tasks.py:142` (`test_derive_status_precedence`): rule 1 does not outrank rule 2 in any assertion (M2 survives). The precedence table is the module's contract and a review currently *could* be made to beat a landed commit with no test noticing. Fix: in the existing test give `E1` a review row (e.g. `"E1": {"verdict": "REJECTED", "run": "ev1", "file": "q"}`) and keep asserting `landed`.
- **major** — `pkgs/evidence/tasks.py:230` (M15 survives): rule 1's second clause — "any key in the task's chain has a review/result AND the chain root's `commit_subject` is landed" — has no test at all. This is the clause that stops a landed task from reporting `rejected` forever after a failed first round. Fix: assert a task whose own subject is *not* in `landed` but whose root is in `landed_keys` and which has a chain review derives `landed`.
- **major** — `pkgs/evidence/tasks.py:57-96` (`parse_plan`): fenced code blocks are not skipped, so quoted fixture markdown becomes real tasks. Demonstrated: `parse_plan("docs/superpowers/plans/2026-09-05-session-context.md")` on the live repo returns `['G1','E1','E3','E5','E7','D1','G4','X1','X2','X3','G2','G3','G5','G6','G7','G8']` — eight phantoms, four colliding with the evidence-store plan's real `E1/E3/E5/E7` inside the same `scan_repo` result, and `X2`/`X3` a dependency cycle. Fix: track ` ``` ` fences in the line loop and skip lines inside them; add a fixture case (a fenced `### Z9 (code, S) — quoted` block in `typed.md`) asserting `Z9` is not a task.
- **major** — `pkgs/evidence/tasks.py:299` (M9 survives): `scan_repo`'s `recorded` re-key per plan (`if f == t["plan"]`) is untested, and cross-plan key collision is *already real* in this repo (`E1`, `E3`, `E5`, `E7` occur in two plan files today). Dropping the filter silently cross-contaminates. Fix: in `test_scan_repo_and_build`, seed a `runs.jsonl` (or monkeypatch `tasks.read_recorded`) with a row for a different plan file and assert it does not colour this plan's task.
- **major** — `pkgs/evidence/tasks.py:164-167` (M10 survives): "newer run directories overwrite" is untested. Fix rounds legitimately produce the same key in two runs (`E7b` in `ev2` and `ev3`), so a silent reversal would pin stale results. Fix: write the same key in two run dirs with different mtimes and assert the newer `run` wins.
- **major** — `pkgs/evidence/tasks.py:288` (M11 survives): `landed_keys` must hold chain *roots*, not raw keys — the repo already has a plan task keyed `R3r`, so the distinction is live. Fix: one assertion that a dependency on `R3` is satisfied when only `R3r`'s subject is landed.
- **major** — `pkgs/evidence/tasks.py:146-147` (M8 survives): `test_read_reviews_matches_only_the_gate_header` does not verify the "first line only" half — its negative fixture `c.md` would not match on any line. No review file in the repo trips this today (70 checked), but a review that quotes the mandated header format in its body would misattribute a verdict. Fix: make `c.md` contain the exact gate header on line 3 with a different first line, and keep `len(rv) == 2`.
- **minor** — `pkgs/evidence/tasks.py:61-64` (M13 survives): the "a section that is not a typed task ends the current one" reset has no test, because `typed.md`'s last task runs to EOF. Consequence: the last task's `body` swallows every following non-task section — and `body` is what G4's brief renders. Fix: append a `## Operator` section after `D1` in `typed.md` and assert its text is not in `by["D1"]["body"]`.
- **minor** — `pkgs/evidence/tasks.py:21` (`CHAIN_RE`): a second fix round is not chained. `chain_root("R3rb") == "R3rb"`, because the root must end in a digit; `docs/reviews/2026-09-05-opus-review-ev3-R3rb.md` exists today, so its APPROVED verdict is invisible to `R3`'s chain. The plan's stated examples are all satisfied, so this is a spec gap, not a violation — flag it for G1b or for the plan.
- **minor** — `tests/evidence/fixtures/plans/typed.md:50`: no trailing newline (`\ No newline at end of file`). treefmt does not sweep `.md`, so the gate stayed green. One-character fix.
- **minor** — `pkgs/evidence/tasks.py:194-202` (`read_recorded`): the plan says `try/except Exception: return {}`; the code narrows to `ImportError` and `(OSError, ValueError)`. A malformed `runs.jsonl` row (`row.get` on a non-dict, a `KeyError`/`TypeError` out of `evidence.read`) would propagate out of `scan_repo` instead of degrading to `{}`. Widen the except, or state why the narrow set is complete.

## Deviations

- `FACTORY-NOTES` claims the smoke showed "E8 approved, R3/R3r rejected, G1 ready, G2/G3 ran, G4-G8 blocked". At my run (12:5x) the live repo has moved: `R3` and `R3r` both derive `landed` (R3rb was approved and integrated at 11:59–12:00), `G1`/`G2`/`G4` derive `ran`, `G3` derives `approved`. `E8 approved` and `G5–G8 blocked` still hold. Time-based drift on a read-only probe, not a misreport.
- `FACTORY-NOTES` claims "24 untracked plans" — confirmed exactly (`24 untracked`), matching the plan's Step 6 expectation.
- `FACTORY-NOTES` does not mention the phantom tasks the same smoke must have printed (`X1`, `X2`, `X3`, and a second `E1/E3/E5/E7/D1`). Step 6 asked for the printed map in the notes; the notes summarise it instead, and the summary drops the anomaly. Not a false claim, but it is the one thing the smoke was for.
- `_chain_members` computes members against `chain_root(key)` where the plan's skeleton says `chain_root(k) == task["key"]`. The implementation is the more correct of the two (a plan task keyed `R3r` still chains to `R3`); recording it as a deliberate, benign deviation from the plan text.
- Result file claims `evidence-unit=pass lint=pass`; both re-run green by ref at HEAD with `--rebuild`, so the claim holds.
