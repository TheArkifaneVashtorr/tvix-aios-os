---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run ex, task X2xhigh — APPROVED

## Summary

Task `X2xhigh` (plan `docs/superpowers/plans/2026-09-05-effort-comparison.md`, section
`### X2xhigh (code, XS)`), DeepSeek V4 Pro, effort actually sent: `reasoningEffort: xhigh`
(`/home/dalhaka/factory/runs/ex/X2xhigh.dsh-home/settings.yaml`).

One commit `bb94450` on base `9083845`, touching exactly the two named files.
Subject byte-identical to the section's (`cmp` against a file holding the plan text: identical).
Both trailers present (`Generated-By:` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`).

What `bundle()`'s `docs_only` computation did **before**:

```python
docs_only = bool(head and live and _docs_equivalent(repo, live, head))
```

`_docs_equivalent(repo, a, b)` short-circuits `if a == b: return True` (evidence.py:124),
so when the live revision equalled HEAD the flag came out `True` — the bundle claimed
"docs-only ahead of live" about a revision that was not ahead at all.

**After**:

```python
docs_only = bool(
    head and live and live != head and _docs_equivalent(repo, live, head)
)
```

The `live != head` guard is placed at the call site in `bundle()`, **not** inside
`_docs_equivalent`. That is the correct choice: the same helper is used by the
per-check `cover()` closure (evidence.py:176), where `a == b → True` is exactly the
wanted semantics ("this check ran on this very revision"). Tightening the helper
would have silently broken check coverage. Good judgement, and it is the reason the
existing `test_bundle_reports_live_head_docs_only_checks_gaps_and_helm` coverage
assertions stay green.

`render_bundle_markdown` replaced the inline ternary with a three-way branch
(`docs_only_ahead` → `" (docs-only ahead of live)"`; `b["head"] and b["live"]["rev"] == b["head"]`
→ `" (equal to live)"`; else `""`), leaving the `— WORKING TREE DIRTY` suffix and the
trailing `.` untouched. `b["head"]` is guarded before the dict compare, and a `None`
live rev compares unequal rather than raising, so no new crash path.

Rendered lines verified directly against the section's interface text:

```
equal            | **Live:** system-42-link at 3abfedf787aa. **HEAD:** 3abfedf787aa (equal to live).
docs-only ahead  | **Live:** system-42-link at 049c6c9cee5d. **HEAD:** 3abfedf787aa (docs-only ahead of live).
```

The new test `test_bundle_equal_live_head_says_equal` reuses `make_repo` and
`fake_nixos_version(tmp_path, head)` as the section requires, and asserts all three
named things: `b["docs_only_ahead"] is False`, `"(equal to live)" in md`,
`"docs-only" not in md`.

## Usage

Effort actually sent: `reasoningEffort: xhigh`.

```json
{"model": "deepseek/deepseek-v4-pro-0813", "events": 812, "input": 197370, "output": 8228, "cacheRead": 367616, "reasoning": 0, "duration_s": 219.082}
```

`wall_s: 219`, `exit_code: 0`, `FACTORY-COMMITS 1`.

## Checks

Run in a throwaway clone of the workspace at `task/X2xhigh`, tooling via `nix develop -c`.

| Command | Result |
| --- | --- |
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | pass |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass (`All checks passed!`, 33 files already formatted) |
| `nix develop -c githooks/pre-commit` | pass (`All checks passed!`, `render.test.mjs: all assertions passed`) |
| `nix develop -c pytest tests/evidence -q -p no:cacheprovider` | 56 passed |
| `git show --stat HEAD` | exactly `pkgs/evidence/evidence.py`, `tests/evidence/test_evidence.py` (26 insertions, 2 deletions) |
| commit count on base | 1 |
| subject vs section | byte-identical |

## Red before green

`git checkout <base> -- pkgs/evidence/evidence.py` (HEAD's tests kept), then
`nix develop -c pytest tests/evidence -q -p no:cacheprovider`:

```
1 failed, 55 passed
FAILED tests/evidence/test_evidence.py::test_bundle_equal_live_head_says_equal
>       assert b["docs_only_ahead"] is False
E       assert True is False
```

Exactly the new test fails, for exactly the reason the section names
(`docs_only_ahead` True when live == head). No other test moves. Implementation restored;
clone verified clean afterwards.

## Mutation table

Each mutation applied to `pkgs/evidence/evidence.py` alone, full `tests/evidence` run, then reverted.

| # | Mutation | Result | Killed by |
| --- | --- | --- | --- |
| M1 | `docs_only = False` (always False) | killed | `test_bundle_reports_live_head_docs_only_checks_gaps_and_helm` |
| M2 | first branch prints `" (equal to live)"` — i.e. say "equal" also when docs-only ahead | killed | `test_bundle_reports_live_head_docs_only_checks_gaps_and_helm` |
| M3 | drop the equal branch (`elif False: ahead = ""`) | killed | `test_bundle_equal_live_head_says_equal` |
| M4 | drop the `live != head` guard only, keep the markdown change | killed | `test_bundle_equal_live_head_says_equal` |
| M5 | `else: ahead = " (equal to live)"` — the "nothing extra otherwise" branch | **survived** | — |

M1–M4 are the three the gate asked for plus one; all killed, each by a single named test,
with no collateral failures. M5 is recorded under Findings.

## Findings

1. **Minor (pre-existing, not a regression): the "nothing extra otherwise" branch is
   untested.** M5 makes the `else` arm print `" (equal to live)"` and the whole suite
   still passes — `tests/evidence/test_evidence.py::test_bundle_code_change_is_not_covered`
   builds the only genuinely-diverged case but never inspects the Live/HEAD suffix. The
   section's Step 1 names three assertions and the implementer wrote all three, so this is
   an omission in the plan's test spec rather than in the work; and the `else` arm's
   behaviour ("") is unchanged from base, so nothing regressed. Cheap follow-up: one
   `assert "(equal to live)" not in md and "docs-only" not in md` inside
   `test_bundle_code_change_is_not_covered`.

2. **No scope creep.** Nothing beyond the two named files; no refactor of
   `_docs_equivalent`, no touching of `cover()`, no drive-by doc edits, no new helper
   module. The markdown change is the minimal shape (a local `ahead` string) rather than
   a new function.

3. **Claim hygiene is honest.** The transcript reports "20 passed" for
   `tests/evidence/test_evidence.py` (that file has exactly 20 tests) and "56 passed" for
   `evidence-unit` (the whole `tests/evidence` tree). Both numbers reproduce here. No
   inflated or unverified claims.

4. **Trailer conflict handled correctly.** The transcript records the seat noticing that
   `AGENTS.md` asks for one machine trailer and no `Co-Authored-By`, and deciding the
   task's explicit instruction (both trailers, that order) wins. That is the right
   precedence and the commit matches.

## Deviations

- **From the section text: none material.** Steps 1–5 were executed in order; the red run
  used the section's `-k equal` form on `tests/evidence/test_evidence.py`, then the fix,
  then ruff + pytest + `evidence-unit` + lint gate, then one commit via
  `nix develop -c git commit -F`.
- **Test placement:** inserted between the existing docs-only-ahead test and
  `test_bundle_code_change_is_not_covered` rather than at end-of-file; the section says
  "append". Harmless — arguably better, since it sits next to its sibling case.
- **Transcript economy:** 337 lines / 22.4 KB, 15 reasoning blocks, 219 s wall, 8 228
  output tokens with `reasoning: 0` reported. Three small reversals, all self-caught and
  recovered without operator help: (a) `ruff format` wanted the widened `docs_only`
  condition wrapped, so the line was rewrapped; (b) the first `git commit -F` failed with
  nothing staged, so the two files were `git add`ed and the commit retried; (c) the scratch
  `.commit-msg.txt` was removed afterwards to leave the tree clean. No dead ends, no
  abandoned approaches, no re-reading of files already read. The reasoning does show
  visible over-deliberation on trivia (which skills to load, where exactly to place the
  test, whether an untracked scratch file affects the flake) — a lot of tokens spent on
  a two-line change, which is the datum the effort comparison is after.
- Workspace and live host untouched; all work in a throwaway clone.
