---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run sc3, task G9 — APPROVED

Branch head `45cfa25bf84b` (`~/factory/ws/sc3/G9`, `task/G9`, parent `2867b983e2f1` = the base named in `G9.result`). Reviewer: Opus, high effort, throwaway clone at `…/scratchpad/gate-sc3-G9`; every check re-run by ref with a forced rebuild. Baselines read: the plan's `### G9`, `### G1`, `### G4`, `### G4b`, Global Constraints, and the reviews `2026-09-05-opus-review-sc1-G4b.md` (the G1/G1b "both listed rejected" finding) and `2026-09-05-opus-review-sc1-G2b.md` (the `.ruff_cache` / `git ls-files` carry-forwards). The sibling `~/factory/ws/sc3/G8` was never read or written.

## Summary

APPROVED. All seven behaviours the plan names are implemented, and every one of them is load-bearing under a mutation: chain state now comes from the last member's *own* review/result/record (`derive_status` rules 2–4 read `last = members[-1]` instead of scanning the whole chain), `render_brief` collapses a rejected chain to its root once while keeping the last member in the detail, `conflicts`' pre-existing cross-plan restriction and `legacy open`'s `status == "open"` filter are pinned for the first time, `waves --factory-args` without `--plan` prints the argparse usage to stderr and returns 2 instead of a silent `[]`, `repomap._IGNORED_PARTS` gains `.ruff_cache`, `_count_files` counts `git ls-files` output with the directory walk as fallback, and `docs/ledger/repos.toml` gains its terminating newline (1 insertion, 1 deletion, nothing else). Red before green is real for the four behaviours that actually changed: with `tasks.py` and `repomap.py` reverted to base and HEAD's tests kept, four tests fail with exactly the stated reasons (`assert 'rejected' == 'ran'`; `'nixos-agent-env/G1b' is contained here`; `assert 0 == 2` with `[]` on stdout; `assert 2 == 1` for the untracked `b.bats`). The three remaining items pin code that was already correct but untested — the plan itself specifies them as mutations, not reds, and each mutation kills. Nineteen mutations were applied, run and reverted: seventeen die, two survive and are recorded as minors (the CLI's `--factory-args` **happy** path is untested, and `_git_tracked_files`' `OSError` arm is untested). G1b's single-key precedence tests are byte-unchanged and green, and G1b's own chain test still reads correctly under the new rule (`E7`'s chain ends at `E7r`, APPROVED). `evidence-unit` (65 passed, `--rebuild`), `lint` (`--rebuild`) and `githooks/pre-commit` are green by ref; one commit on base; exactly the five files `touches` names; subject byte-identical to the plan's `### G9` subject by `cmp`; both trailers; stdlib only; no writes outside the workspace. On real data the "Rejected" line now reads `nixos-agent-env/G7 (G7 by sc3) · media/W3 · media/W5` — no fix-round key whose own result is done and ungated, each chain once — and `repomap check` on the live repo exits **0**: the tracked-files rule changes no count today because nothing untracked sits under `tests/`, so `docs/MAP.md` needs no regeneration. Three findings, all minor, none blocking.

## Checks

- green — `evidence-unit` (`nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild`): exit 0, `evidence-unit> 65 passed in 3.55s`, out path `/nix/store/rvgaapn59fs8805a6mpav1085x2k0qxz-evidence-unit`. Forced with `--rebuild` so the derivation really re-executed. (G4b's branch was 51; wave 2 and G9's fourteen new assertions bring it to 65.)
- green — `lint` (`nix build .#checks.x86_64-linux.lint -L --no-link --rebuild`): exit 0, out path `/nix/store/fghwksz3pswds69y2q566qp1bcj5m4k4-lint`. Decisive lines: `lint> traversed 344 files`, `lint> formatted 84 files (0 changed) in 1.069s`, `lint> All checks passed!`, `lint> 33 files already formatted`.
- green — `nix develop -c githooks/pre-commit`: exit 0. `traversed 344 files`, `formatted 84 files (0 changed) in 229ms`, `All checks passed!`, `33 files already formatted`, `render.test.mjs: all assertions passed`. Note this gate runs `python3 pkgs/evidence/repomap.py --root . check` (line 50) in the worktree — i.e. through the new git path — and passes.
- green — devShell suite (`nix develop -c pytest tests/evidence -q -p no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`): `65 passed in 3.61s`.
- green — one commit on base: `git rev-list --count 2867b98..HEAD` = 1; `git rev-parse HEAD^` = `2867b983e2f1744e2597818e1f106108ad56a446`, the `base:` line of `G9.result`. No amend, no merge.
- green — touches contract: `git show --name-only --format= HEAD` = exactly `docs/ledger/repos.toml`, `pkgs/evidence/repomap.py`, `pkgs/evidence/tasks.py`, `tests/evidence/test_repomap.py`, `tests/evidence/test_tasks.py` — the plan's five, nothing else. `--numstat`: `1 1`, `23 1`, `30 25`, `30 0`, `187 0`. `repos.toml`'s 1/1 is the missing terminating newline and nothing else (the diff shows only the `\ No newline at end of file` marker disappearing).
- green — subject: the plan's `### G9` **commit subject** extracted from line 1449 and `cmp`'d against `git log -1 --format=%s` → identical, byte for byte, including the em dash-free wording and the `(test: evidence-unit, lint)` suffix.
- green — trailers: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sc3)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- green — interfaces roll-call against `### G9`:
  - `derive_status`: `last = members[-1]` with `_chain_members` ordering `sorted(members, key=lambda k: (k != root, k))` (root first, then suffix ascending); rules 2/3/4 all read `last`; rule 1's two clauses (own subject landed; any member reviewed/resulted AND root in `landed_keys`) untouched; rule 5 unchanged.
  - `render_brief`: a per-repo `seen` set keyed by `chain_root(t["key"])`, item rendered as `<repo>/<root> (<detail>)`.
  - `conflicts`: `if a["plan"] == b["plan"]: continue` present at line 440 (unchanged code, now pinned).
  - `main`: `if args.factory_args and not args.plan: waves_p.print_usage(sys.stderr); return 2`.
  - `render_brief`: `legacy_open = sum(1 for r in repo["legacy"] if r["status"] == "open")` (unchanged code, now pinned).
  - `repomap._IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".git"}`; `_count_files` calls `_git_tracked_files(d)` first and falls back to the walk when it returns `None` (non-zero rc, or `OSError`/`SubprocessError`).
- green — G1b's precedence tests unchanged: the test-file diff is exactly two hunks — `@@ -524,6 +524,8` adds the two `data["repos"][0]["tasks"][0]["state"] in tk.STATES` lines *inside* `test_cli_check_and_json`, and `@@ -545,3 +547,188` appends. `test_derive_status_precedence`, `test_derive_status_ready_when_deps_landed` and `test_derive_status_chain_review_with_landed_root` (lines 162–215) are byte-identical to base and green. The first still asserts `st == "approved" and "E7r" in detail`, which under the new rule is the *last member* of `E7`'s chain — the same answer for the right reason.
- green — hard-rule scan: `git show HEAD | grep -E 'sudo|nixos-rebuild|systemctl|--no-verify|--no-gpg-sign|2>/dev/null|mount --'` → no hits (exit 1). `repomap.py` imports `argparse pathlib re subprocess sys`; `tasks.py`'s imports are unchanged from G4b (`argparse datetime fnmatch glob json os pathlib re subprocess sys tomllib` plus the lazy `import evidence`). Stdlib only. No file in `pkgs/evidence` opens anything for writing on these paths. No secrets. Nothing outside the repo is written by the tests (`tmp_path` only).
- green — workspace hygiene: `git --no-optional-locks -C ~/factory/ws/sc3/G9 status --porcelain` shows only `?? scratch/` (the run's own scratch directory, uncommitted). The sibling `~/factory/ws/sc3/G8` was not touched. My clone's `git status --porcelain` is empty after every mutation batch.

## Red before green

`git checkout 2867b98 -- pkgs/evidence/tasks.py pkgs/evidence/repomap.py` with HEAD's tests, then `nix develop -c pytest tests/evidence -q -p no:cacheprovider` → **`4 failed, 61 passed in 3.62s`**, then restored (`git status --porcelain` empty, suite back to `65 passed`).

- `test_chain_last_member_result_beats_root_review` — `assert by["G1"]["state"] == "ran"` → `AssertionError: assert 'rejected' == 'ran'`. Exactly the plan's stated red: base takes the newest review across the chain, so `G1b`'s own `done` result is masked by `G1`'s REJECTED gate.
- `test_brief_lists_chain_once_by_root` — `assert "nixos-agent-env/G1b" not in line` → `'nixos-agent-env/G1b' is contained here: by ev1) · nixos-agent-env/G1b (G1b by ev1)`. The chain was listed twice on base.
- `test_main_waves_factory_args_requires_plan` — `assert rc == 2` → `assert 0 == 2`, with `Captured stdout call: []`. The exact "silently prints `[]`" behaviour the G4 review flagged.
- `test_count_files_git_tracked_and_ruff_cache_fallback` — `assert rm._count_files(repo / "tests" / "unit") == 1` → `AssertionError: assert 2 == 1`, i.e. the untracked `b.bats` counted on base.

**Not red, and correctly so:** `test_conflicts_same_plan_not_reported`, `test_brief_legacy_open_counts_only_open` and the added `STATES` assertion in `test_cli_check_and_json` pass against base, because `conflicts`' cross-plan `continue`, the `status == "open"` filter and the `state` field already existed and were merely unpinned (the G4/G4b reviews' M16, M19 and M26). The plan specifies these three as mutations ("mutation: drop the different-plan condition → fails", "mutation: count all legacy rows → 2, fails"), not as reds, and each is killed below (M3, M5). The gate brief's expectation of a "legacy count 2" red therefore does not apply to this codebase; nothing was weakened to produce it.

The implementer's transcript (`~/factory/runs/sc3/G9.log:412-423, 1162`) reasons to the same conclusion explicitly before writing the tests, rather than silently skipping the red step.

## Mutation table

Nineteen single-site edits, each applied to the clone, run against `pytest tests/evidence -q -p no:cacheprovider`, then reverted with a byte-comparison of the file afterwards; the tree was `git status --porcelain`-clean after every batch. Twelve are new (the behaviours G9 introduces or pins), seven re-run mutants that the G1b and G4b gates killed.

| # | mutation | file | killed | by |
|---|---|---|---|---|
| M1 | rule 2 restored to "newest review across all members" (the base loop) | tasks.py | yes | `test_chain_last_member_result_beats_root_review` (1 failed, 64 passed) |
| M2 | rule 2 falls back to an earlier member's review when the last member has none (`next((m for m in members if m in reviews), None)`) | tasks.py | yes | `test_chain_last_member_result_beats_root_review` |
| M3 | `conflicts` drops the same-plan `continue` (cross-plan restriction gone) | tasks.py | yes | `test_conflicts_same_plan_not_reported` |
| M4 | the `--factory-args`/`--plan` guard disabled (`if False:`) — back to printing `[]` | tasks.py | yes | `test_main_waves_factory_args_requires_plan` |
| M5 | `legacy_open` counts every legacy row | tasks.py | yes | `test_brief_legacy_open_counts_only_open` |
| M6 | `.ruff_cache` removed from `_IGNORED_PARTS` | repomap.py | yes | `test_count_files_git_tracked_and_ruff_cache_fallback` |
| M7 | `_count_files` never consults git (walk always) | repomap.py | yes | `test_count_files_git_tracked_and_ruff_cache_fallback` |
| M8 | `render_brief` dedupes by `t["key"]` instead of `chain_root(t["key"])` | tasks.py | yes | `test_brief_lists_chain_once_by_root` |
| M9 | `last = members[0]` — the **root** owns rules 2–4 | tasks.py | yes | 5 failed: `test_derive_status_precedence`, the three chain tests, `test_brief_lists_chain_once_by_root` |
| M10 | the guard becomes unconditional (`if args.factory_args:`) — exit 2 even **with** `--plan` | tasks.py | **no** | 65 passed — see Findings |
| M11 | `_git_tracked_files` returns `[]` instead of `None` on non-zero rc (fallback unreachable) | repomap.py | yes | `test_count_files_git_tracked_and_ruff_cache_fallback` + `test_build_and_render` |
| M12 | `_git_tracked_files` returns `[]` instead of `None` on `OSError`/`SubprocessError` | repomap.py | **no** | 65 passed — see Findings |
| R-G1b-R7 | chain member order reversed (`sorted(..., reverse=True)`) | tasks.py | yes | 5 failed, incl. `test_derive_status_precedence` |
| R-G1b-M15 | rule 1's second clause deleted (chain review/result + landed root ⇒ landed) | tasks.py | yes | `test_derive_status_chain_review_with_landed_root` |
| R-G1b-C1 | `CHAIN_RE` suffix narrowed back to `[a-z]` | tasks.py | yes | `test_chain_root` |
| R-G4b-R1 | `waves` ignores dependencies (`deps[k] = set()`) | tasks.py | yes | `test_waves_follow_dependencies_and_skip_landed` + `test_brief_lists_counts_next_wave_and_operator_items` |
| R-G4b-R3 | `touches_overlap` loses the directory-prefix rule | tasks.py | yes | `test_touches_overlap` |
| R-G4b-R9 | `open_tasks` returns every state | tasks.py | yes | `test_waves_follow_dependencies_and_skip_landed` + `test_brief_…` |
| R-G4b-R15 | `factory_args` emits an empty `spec` | tasks.py | yes | `test_factory_args_shape` |

Seventeen of nineteen die. R-G1b-R7 and M9 together prove the chain **ordering** is load-bearing in both directions, which is the heart of this task. Note that the G4/G4b survivor S1 (`conflicts`' cross-plan restriction) is now dead (M3), and G4's M19 (`legacy open`) and M26 (the `json` payload's `state`) are closed — three of the carried-forward minors retired.

## Real data

Read-only, run from the clone against `/home/dalhaka/nixos-agent-env` with `--runs-dir /home/dalhaka/factory/runs`. Nothing was written to the live repo, to `~/factory/runs` or to any workspace.

`nix develop -c python3 pkgs/evidence/tasks.py --root /home/dalhaka/nixos-agent-env --runs-dir /home/dalhaka/factory/runs brief` → exit 0, verbatim:

```
# Task brief (generated 2026-09-05T19:24:13Z)

| repo | landed | approved | rejected | ran | recorded | ready | blocked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 49 | 0 | 1 | 5 | 0 | 4 | 2 | 1 | 0 |
| media | 3 | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0 |
| gaming | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nixos-skill | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dsh-harness | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Next wave** — nixos-agent-env: B1 G7b G8 PB0
**Rejected, fix round owed:** nixos-agent-env/G7 (G7 by sc3) · media/W3 (W3 by cw2) · media/W5 (W5 by cw2)
**Operator owns:** nixpkgs-host-pin-age (review by 2026-10-05)
**Untracked plans (no typed headings, no plan-status row):** none
```

The two conditions the gate brief names both hold. **No fix-round key whose own result is done and ungated appears:** `G7` is listed because `G7`'s own gate rejected it and `G7b` has neither a review nor a result yet (it is correctly on the *Next wave* line as an open task instead); the `G1`/`G1b` double-listing that the G4b gate found is gone, both because `G1` has since landed and because the rule that produced it is gone. **Each chain is listed at most once**, by root — no `…b` suffix appears anywhere on the line.

- `… check` → **no output, exit 0**: across all five repos, no unknown `dependsOn`, no cycle, no code task without acceptance, no key defined in two typed plans.
- `… conflicts` → exit 0, five rows, all cross-plan on `flake.nix` (`B1 × PB0`, `B1 × PB1`, `B1 × G8`, `G8 × PB0`, `G8 × PB1`). No same-plan pair is reported — the pin is visible on real data as well as in the fixture.
- `nix develop -c python3 pkgs/evidence/repomap.py --root /home/dalhaka/nixos-agent-env check; echo rc=$?` → **`rc=0`**, no output. `docs/MAP.md` is **not** stale.

On the count change: I measured both rules side by side on the live tree (`_count_files` vs. the base walk) for all twelve directories under `tests/` — `acceptance 9/9, broker 1/1, evidence 7/7, factory 3/3, fixtures 1/1, helm 3/3, integration 5/5, lane 4/4, ledger 12/12, lint 2/2, mocks 2/2, unit 12/12`. Identical, because nothing untracked currently sits under `tests/`. So the tracked-files rule is live (M7 proves the code path is taken) but changes no number today, and there is nothing for G8 or the next regeneration to absorb. The two rules also stay consistent inside the `lint` sandbox by construction: `lint` runs `repomap check` on a store copy with no `.git`, so it takes the walk, and a flake source contains exactly the tracked files.

## Findings

- **minor (new, no test)** `pkgs/evidence/tasks.py:650-652` — the CLI's `--factory-args` **happy** path is unpinned. M10 (`if args.factory_args and not args.plan:` → `if args.factory_args:`) makes `waves --repo R --plan P --factory-args` exit 2 and print usage instead of emitting the JSON task list, and **all 65 tests still pass**. `factory_args()` the function is well covered (R-G4b-R15, and G4b's plan filter), but nothing exercises the CLI branch that prints it. No consumer in-tree calls it yet (only the orchestrator does, by hand), so this is a coverage gap and not a live breakage — but it is a branch G9 itself created. **Fix:** in `test_main_waves_factory_args_requires_plan`, add the positive half — `main([..., "waves", "--repo", "r", "--plan", "second.md", "--factory-args"])` returns 0 and stdout parses as a JSON array whose keys are `X1 X2 X3`. One assertion; fold into G8 or a G9 follow-up.
- **minor (new, no test)** `pkgs/evidence/repomap.py:107-118` — the `except (OSError, subprocess.SubprocessError): return None` arm is unreachable in the test environment (git is always present), and M12 (`return []` there) survives with 65 passed. The plan's interface says the walk is the fallback "when `git` is unavailable **or** the root is not a repo"; only the second half is pinned (M11 kills it). **Fix:** monkeypatch `subprocess.run` in `repomap` to raise `FileNotFoundError` and assert the walk count. Two lines.
- **minor (new, latent)** `pkgs/evidence/repomap.py:157-159` — `build_map` enumerates test directories with `tests_dir.glob("*")` and filters nothing: `_IGNORED_PARTS` is consulted only *inside* `_count_files`, and the git-tracked rule only affects the *count*. I verified on a scratch fixture that a `.ruff_cache` sitting **directly under `tests/`** still produces a map row `{'path': 'tests/.ruff_cache', 'files': 0}` and would therefore trip the hook's drift check — the very scenario the plan's Step-1 bullet words as "`.ruff_cache/` under `tests/` is ignored in the fallback walk". The implementer read that bullet as the nested case (`tests/unit/.ruff_cache/`, which *is* handled and pinned by M6) and reasoned about the ambiguity explicitly in the transcript (`G9.log:597-641`). The normative Interfaces line — "`_IGNORED_PARTS` gains `.ruff_cache`" — is satisfied literally, and real exposure is low because treefmt/ruff run from the repo root, so `.ruff_cache` lands where `build_map` never enumerates it. Recording it because the same hole admits any stray untracked directory under `tests/` (e.g. a `tests/scratch/`). **Fix:** skip `d.name in _IGNORED_PARTS` (and, when git is available, directories with no tracked files) in that loop. Fold into G8.
- **observation** `pkgs/evidence/tasks.py:222-228` — `_chain_members` pools chain keys from `reviews` and `results` only, never from `recorded`. So a fix round known only to `runs.jsonl` is not a chain member: I measured `derive_status(E7, …, recorded={"E7b": "done"})` → `('rejected', 'E7 by ev2')` with `members(E7) == ['E7']`. The plan's interface gives rules 2–**4** to the last member, so strictly a recorded-only fix round should win. Harmless today (the store has no `runs` rows for this plan) and arguably the safer reading — a record is weaker evidence than a result — but the asymmetry is undocumented. **Fix or decide:** either add `recorded`'s keys to `_chain_members` (it would need the plan-filtered dict passed in) or write the narrower rule into the spec.
- **observation** `pkgs/evidence/tasks.py:244-247` + `read_reviews:151` — `test_chain_last_member_rejected_review_newest` is named for recency but actually pins *last filename wins*: `read_reviews` iterates `sorted(d.glob("*.md"))` and overwrites, so `c.md` (REJECTED) beats `b.md` (APPROVED) alphabetically, not chronologically. Correct in practice because review filenames are date-prefixed, and it is G1's design, not G9's. Noted so a future reader does not infer an mtime comparison that does not exist.
- **nit** `tests/evidence/test_repomap.py:210-216` — the fallback half of the new test assumes `tmp_path` is not inside a git repository. True under `nix build` and under the devShell's `TMPDIR`, but a developer with `TMPDIR` inside a checkout would see `_count_files` take the git path and return 0, failing the assertion for an environment reason. A `git -C … rev-parse` guard, or asserting via a monkeypatched `subprocess.run`, would make it hermetic.
- **nit** `~/factory/ws/sc3/G9` carries an untracked `scratch/` directory. Not committed, not in `.gitignore`; it will show in the integrator's `git status`. Harmless, and it sits at the workspace root so it does not perturb the repo map's `tests/` rows.

## Deviations

- **Deviation from the letter of Step 1, accepted:** the plan's repomap bullet reads "`.ruff_cache/` under `tests/`"; the test places `.ruff_cache/` under `tests/unit/` (i.e. inside the counted directory) rather than as a sibling of it. That is the case `_IGNORED_PARTS` actually governs, and it is proven load-bearing (M6). The sibling case is the third finding above.
- The three "pin" items (`conflicts` cross-plan, `legacy open`, the CLI `state` field) could not be red — the code was already correct; the plan words them as mutations and they are killed as such (M3, M5; the `state` assertion is a shape pin with no behaviour to mutate). Recorded so the absence of four more reds is not mistaken for a skipped TDD step.
- The commit **body** goes beyond the subject in describing all four behaviours. Expected; only the subject must be byte-identical, and it is.
- Both trailers are present (`Generated-By` then `Co-Authored-By`), as in every task of this plan. Global Constraints name only the second; the seat's own rules add the first.
- The plan's Step 4 writes the real-data commands as bare `python3`; `python3` is not on this host's PATH by design (CLAUDE.md), so the implementer and I both ran them through `nix develop -c`. Same program.
- The implementer's FACTORY-NOTES quote `landed=47 rejected=2 ran=1`; my run of the same command shows `49 / 1 / 5`. Not a discrepancy — the brief reads the *live* repo's landed subjects and the live `~/factory/runs`, both of which advanced between their run and mine (G7's gate rejected in the interval, G8 is in flight). The claim that mattered — no ungated fix round on the Rejected line, each chain once — holds in both.
- Reviewer's own hygiene: every gated command was run with stderr visible. I used `2>/dev/null` exactly once, on a non-gated `nix build --print-out-paths` issued *after* both checks had already passed with full output, purely to capture the store paths quoted above.
- I added two mutations beyond the gate brief's seven-plus-six (M11, M12, probing the fallback's two arms separately) and one scratch-fixture probe of `build_map` for the third finding. Additive evidence only; nothing outside the clone, the nix cache directory and this review file was written.
