# Opus gate — seat run sc1, task G1b — APPROVED

Branch head `8d4bc7f8d6af` (`~/factory/ws/sc1/G1b`, `task/G1b`, base `7b23aa1`). Reviewer: Opus, high effort, throwaway clone; checks re-run by ref with `--rebuild`; pytest with `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`.

## Summary

APPROVED. Every one of G1's seven majors and four minors is closed, and each is proven load-bearing by its own mutation: I re-applied all six surviving precedence mutants from the G1 review (M2, M15, M9, M10, M11, M8) plus the M13 section reset and the fence removal, and all eight now die — each on the test the plan named for it. The two CHAIN_RE directions are both pinned (narrowing to one suffix letter and widening to three each kill `test_chain_root`), and `read_recorded`'s widened `except Exception` is pinned by a malformed-row test that goes red the moment the except is narrowed back to `(OSError, ValueError)`. Eleven of the G1 review's already-killed mutants were re-run as regression; all eleven still die.

The fenced-code defect is gone at the source of the complaint: `parse_plan` on the LIVE `docs/superpowers/plans/2026-09-05-session-context.md` returns exactly `['G1','G4','G2','G3','G5','G6','G7','G8','G1b','G4b','G2b']` — the eleven real G-keys and nothing else. No `E1/E3/E5/E7/D1`, no `X1/X2/X3` cycle fixture, no `Z9`. The fixture pins it: deleting the fence toggle resurrects `Z9` and fails two tests.

Spec compliance is exact — one commit on base, byte-identical subject, the four named files and nothing else, the `Co-Authored-By` trailer present, module still stdlib-only, every test write under `tmp_path`. The delta against `task/G1` is 26 lines of `tasks.py` and 12 of `typed.md`: the fence toggle, `CHAIN_RE`, the widened except, and the fixture's `## Operator` section — no scope creep.

Three surviving mutants remain, but none is a rejection finding and none is anything the plan's G1b section asked for: `ran` hoisted above `landed`, `recorded` hoisted above `approved/rejected`, and `read_recorded`'s happy path (the only `scan_repo` test monkeypatches it away). They are the same *family* as M2, so I record them as minors for the plan rather than re-opening a bounded fix round under rule A1 — closing all three is two assertions and one small test.

## Checks

- green — `evidence-unit` (`nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild`): exit 0; decisive line `evidence-unit> 42 passed in 3.00s`.
- green — `lint` (`nix build .#checks.x86_64-linux.lint -L --no-link --rebuild`): exit 0; decisive lines `lint> formatted 80 files (0 changed)`, `lint> All checks passed!`, `lint> 30 files already formatted`.
- green — lint gate (`nix develop -c githooks/pre-commit`): exit 0; `All checks passed!` / `render.test.mjs: all assertions passed`.
- green — local suite (`nix develop -c pytest tests/evidence -q -p no:cacheprovider`): `42 passed in 2.93s` (G1's 38 plus the four new test functions).
- pass — spec compliance: `git rev-list --count 7b23aa1..task/G1b` = 1. `git show --stat HEAD` lists exactly `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `tests/evidence/fixtures/plans/typed.md`, `tests/evidence/fixtures/plans/legacy.md`. Subject `cmp`-identical to the plan's **commit subject** for G1/G1b. Trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present plus the machine-set `Generated-By: dsh ...`.
- pass — bounded delta: `git diff task/G1 task/G1b -- pkgs/evidence tests/evidence` is `tasks.py |26 +--`, `typed.md |12 +-`, `test_tasks.py |75 +-` and nothing else (`pkgs/helm` and `tests/helm` differ only because G1b's base is newer than G1's).
- pass — hard rules: no `sudo`/`nixos-rebuild`/`systemctl`, no `--no-verify`, no new `2>/dev/null`, no secrets; `tasks.py` imports only `datetime glob os pathlib re subprocess tomllib`; every test write is under `tmp_path` (the `/home/dalhaka/factory/base/...` string appears only as *content* written into a fake `.git/config` inside `tmp_path`).
- pass — implementer workspace `~/factory/ws/sc1/G1b` clean, `HEAD == task/G1b == 8d4bc7f`. Sibling `ws/sc1/G4b` untouched. No writes outside my clone, the nixcache and this file.

## Red before green

`mv pkgs/evidence/tasks.py <scratch>` (tests kept), then `nix develop -c pytest tests/evidence/test_tasks.py -q -p no:cacheprovider` → exit 2:

```
tests/evidence/test_tasks.py:18: in load
    src = next(p for p in candidates if p.exists())
E   StopIteration
ERROR tests/evidence/test_tasks.py - StopIteration
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

File restored; `git status --porcelain` empty afterwards; suite back to `42 passed`.

The transcript (`~/factory/runs/sc1/G1b.log`) shows the same red-first discipline per finding, and its claims check out independently: the fence red was the `list(by) == ["E1","E3","E5","E7","D1"]` assertion failing with `Z9` present (log:694-697), and the real-data probe result at log:2980 matches mine byte for byte.

## Mutation table

Every mutation applied to `pkgs/evidence/tasks.py` in the clone and run against the whole `tests/evidence` suite (42 tests), reverting to a green baseline between each. 18 of 18 die.

| # | mutation | killed | by |
|---|---|---|---|
| M2 | rule 2 hoisted above rule 1 — a review outranks a landed subject | yes | `test_derive_status_precedence`, `test_derive_status_chain_review_with_landed_root` |
| M15 | rule 1's second clause deleted (chain review/result + landed root ⇒ landed) | yes | `test_derive_status_chain_review_with_landed_root` |
| M9 | `scan_repo` drops the per-plan re-key of `recorded` | yes | `test_scan_repo_and_build` (`other.md`'s `D1` row bleeds in) |
| M10 | `read_results` mtime sort reversed (oldest run wins) | yes | `test_read_results_newest_run_wins` |
| M11 | `landed_keys` keyed by raw key instead of `chain_root` | yes | `test_landed_keys_use_chain_root` (`R3r` landed no longer satisfies `R7`'s dep on `R3`) |
| M8 | `read_reviews` matches the gate header on any line, not line 1 | yes | `test_read_reviews_matches_only_the_gate_header` (`c.md` line 2 now matches ⇒ `len(rv) == 3`) |
| M13 | the "non-task section ends the current task" reset removed | yes | `test_parse_typed_plan_reads_every_field` (`"Operator" in by["D1"]["body"]`) |
| F1 | fence tracking removed from `parse_plan` | yes | `test_parse_typed_plan_reads_every_field`, `test_scan_repo_and_build` (`Z9` returns) |
| F2 | fence lines kept but body-suppression dropped | yes | same two |
| C1 | `CHAIN_RE` back to `[a-z]` (one suffix letter) | yes | `test_chain_root` (`chain_root("R3rb") != "R3"`) |
| C2 | `CHAIN_RE` widened to `[a-z]{1,3}` | yes | `test_chain_root` (`chain_root("P1pro")` collapses to `P1`) |
| E1 | `read_recorded`'s `except Exception` narrowed to `(OSError, ValueError)` | yes | `test_read_recorded_returns_empty_on_malformed_row` (`AttributeError` escapes) |
| R1 | `chain_root` returns `key` (G1 M1) | yes | 4 tests |
| R3 | `parse_keys` drops the `(...)` strip (G1 M3) | yes | 2 tests |
| R4 | `read_results` hard-codes the repo name (G1 M4) | yes | `test_read_results_attributes_by_workspace_origin` |
| R5 | `parse_list` stops stripping backticks (G1 M5) | yes | 2 tests |
| R6 | blocked detail lists every dep, not only the missing (G1 M6) | yes | 3 tests |
| R7 | chain member order reversed (G1 M7) | yes | `test_derive_status_precedence` |
| R12 | untyped plans always land in `untracked_plans` (G1 M12) | yes | `test_scan_repo_and_build` |

Three further probes of my own, beyond the rejection's list, survive — recorded as minors below, not as re-opened findings:

| # | mutation | killed | why not |
|---|---|---|---|
| X1 | rule 3 (`ran`) hoisted above rule 1 (`landed`) | **no** | 42 passed — no fixture task is both landed and has a chain result |
| X2 | rule 4 (`recorded`) hoisted above rule 2 (`approved`/`rejected`) | **no** | 42 passed — no fixture task is both recorded and reviewed |
| X3 | `read_recorded` always returns `{}` (happy path gutted) | **no** | 42 passed — the only `scan_repo` test monkeypatches `read_recorded` away; the sole direct test covers the failure path |

## Findings

Every G1 rejection finding, with its evidence:

- **closed** — M2 (precedence 1 vs 2): `test_tasks.py:166` now gives `E1` a `REJECTED` review while still asserting `landed`. Mutation M2 kills it.
- **closed** — M15 (rule 1's second clause): new `test_derive_status_chain_review_with_landed_root` (`test_tasks.py:204-211`) — `E7`'s own subject is not landed, `E7b` has a review, `landed_keys = {"E7"}` ⇒ `("landed", "E7")`. Mutation M15 kills it.
- **closed** — fenced code blocks: `parse_plan` toggles on a flush-left ` ``` ` and skips the interior (`tasks.py:62-66`); `typed.md` gained a `## Operator` section quoting a fenced `### Z9 (code, S)` heading with a `**dependsOn:**` line. Live-plan probe returns the eleven G-keys only. Both fence mutations kill.
- **closed** — M9 (per-plan re-key of `recorded`): `test_scan_repo_and_build` monkeypatches `read_recorded` to `{("other.md","D1"):"done", ("typed.md","E7"):"done"}` and asserts `E7 == "recorded"` while `D1 == "blocked"`. Dropping the `if f == t["plan"]` filter kills it.
- **closed** — M10 (newest run wins): new `test_read_results_newest_run_wins` writes `E7b` into `ev2` and `ev3` and `os.utime`s the run dirs ten seconds apart. `reverse=True` kills it.
- **closed** — M11 (`landed_keys` holds chain roots): new `test_landed_keys_use_chain_root` builds a two-task plan where `R3r`'s subject is landed and `R7` depends on `R3`; asserts `{"R3r": "landed", "R7": "ready"}`. Raw-key mutation kills it.
- **closed** — M8 (gate header on line 1 only): `c.md` is now two lines, an unrelated `# dsh + dark factory: 24-hour review` first and the exact gate header for `E8b` second; `len(rv) == 2` holds. Matching anywhere kills it.
- **closed** — M13 (section reset, minor): pinned by the same `assert "Operator" not in by["D1"]["body"]` the fence work needed.
- **closed** — CHAIN_RE second fix round (minor): `CHAIN_RE` is `[a-z]{1,2}`; `test_chain_root` asserts both `chain_root("R3rb") == "R3"` and `chain_root("P1pro") == "P1pro"`, and both the narrowing and the widening mutation die. Confirmed on real data: the live `R3` chain is now `['R3','R3b','R3r','R3rb']` and `P1pro` remains its own root.
- **closed** — trailing newline (minor): `typed.md` ends with a newline (`\ No newline at end of file` gone from its diff).
- **closed** — `read_recorded` except (minor): now `except Exception:` with a `# noqa: BLE001` and a reason, wrapping the whole parse; `test_read_recorded_returns_empty_on_malformed_row` feeds `runs.jsonl` a JSON list and asserts `{}`. Narrowing the except kills it (the row's `AttributeError` escapes).

New, not blocking:

- **minor** — `pkgs/evidence/tasks.py:248-252` (X1 survives): rule 3 (`ran`) may be hoisted above rule 1 (`landed`) with all 42 tests green — no fixture task is both landed and has a chain result, though the live board has several. Same family as M2, which the plan asked to pin; nobody asked for this adjacency. Fix: in `test_derive_status_precedence`, add `"E1": {...}` to `results` and keep asserting `landed`. One line.
- **minor** — `pkgs/evidence/tasks.py:254-256` (X2 survives): rule 4 (`recorded`) may be hoisted above rule 2 with all 42 tests green. Fix: add `"E7": "done"` to `recorded` in the same test and keep asserting `approved`. One line.
- **minor** — `pkgs/evidence/tasks.py:206-214` (X3 survives): `read_recorded`'s happy path has no test — gutting it to return `{}` passes, because the only `scan_repo` test monkeypatches it and the only direct test covers the failure path. This is the sole producer of the `recorded` state on real data. Fix: one test writing a valid `runs.jsonl` row with `plan` and `tasks[]` and asserting the `(plan_file, key) -> status` mapping.
- **minor** — `tests/evidence/fixtures/plans/legacy.md` still has no trailing newline. G1's review named `typed.md:50` and the plan's Step 3 names `typed.md`, so this is untouched-by-contract rather than missed; treefmt does not sweep `.md`, so nothing is red. One character.
- **observation** — `CHAIN_RE` still requires the root to end in a digit, so a key whose root ends in letters does not chain: the live model-comparison plan has `P1flash` (rejected) and `P1flashb` (ran) as two separate roots. No misreport today (no review exists on `P1flashb`), but it is the same class of gap the G1 review flagged for `R3rb` and it is now visible on real data. Plan-level decision, not a code defect.
- **observation** — a fenced block inside a *task* body is dropped from `body` entirely rather than kept as plain text. The G1b section says fenced content is "body text at most", so dropping is within spec; G4's brief renders `body`, so the operator should know quoted blocks will not appear there.

## Deviations

- Real-data probe, `scan_repo` against `/home/dalhaka/nixos-agent-env` with runs dir `/home/dalhaka/factory/runs` (read-only, no store): no traceback, 45 tasks, 24 untracked plans. `E1–E9` and `R1–R10` (and `R3r`) all derive `landed`. `N13–N18` landed. `P0` landed; `P1pro`/`P2pro`/`P2flash`/`P3`/`P3b` approved; `P1flash` rejected; `P1flashb` ran; `B1` ready. `G1` derives **rejected**, detail `G1 by sc1` — correct per the precedence table: `G1`'s subject is not landed, `landed_keys` has no `G1`, and the newest review among the chain `['G1','G1b']` is `G1`'s own rejection because this G1b review did not yet exist at probe time. `G1b` derives the same, by the same chain. `G4`/`G4b` approved by `G4`'s review, `G2`/`G2b` approved by `G2b`'s review, `G3` approved, `G5–G8` blocked on their unlanded deps. All as the table predicts.
- `FACTORY-NOTES` — "fence skipping, chain re-key (R3rb/P1pro), and the six precedence-table mutants each pinned red-then-green" — verified independently; all eight mutations die in my own harness. `FACTORY-CHECKS evidence-unit=pass lint=pass` re-run green by ref with `--rebuild`.
- The transcript's mid-run "38 passed" (log:789) predates the four new test functions; the final count is 42 and the result file does not claim otherwise. Not a misreport.
- The plan's Step 4 asked for the live-plan probe; the transcript records it verbatim at log:2980 and it matches my run exactly. `FACTORY-NOTES` summarises rather than quotes it — acceptable here since the log carries the raw output.
- `_chain_members` still computes members against `chain_root(key)` rather than the plan skeleton's `chain_root(k) == task["key"]`; carried forward from G1 and recorded there as a deliberate, more-correct deviation. Unchanged in G1b, and now demonstrably right on the live `R3` chain.
