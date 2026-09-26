---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run em, task X2med — APPROVED

Task `X2med` of `docs/superpowers/plans/2026-09-05-effort-comparison.md` (the
medium arm of the effort comparison). Model `deepseek/deepseek-v4-pro-0813`,
effort actually sent: `reasoningEffort: medium`
(`/home/dalhaka/factory/runs/em/X2med.dsh-home/settings.yaml`). Reviewed from a
throwaway local clone of `/home/dalhaka/factory/ws/em/X2med` at branch
`task/X2med`, head `80eec580123ae1614c845685118396561e815f06`, base
`90838458eb7d65d1a5c7b876abae5549e6d41c05`. The workspace was not touched.

## Summary

One commit on base, touching exactly the two files the section names, with a
commit subject byte-identical to the section's and both trailers
(`Generated-By:` plus `Co-Authored-By: Claude Fable 5.1`). The change is the
minimal correct one and matches the stated interface.

`bundle()`'s `docs_only` computation, **before**:

```python
docs_only = bool(head and live and _docs_equivalent(repo, live, head))
```

`_docs_equivalent(repo, a, b)` short-circuits `return True` on `a == b`, so the
equal case (`live == head`) satisfied the predicate and `docs_only_ahead` came
back `True` — the board follow-up's bug. **After**:

```python
docs_only = bool(
    head and live and live != head and _docs_equivalent(repo, live, head)
)
```

The added `live != head` conjunct makes "ahead" mean strictly ahead; the
docs-equivalence branch is otherwise untouched, so the existing docs-only-ahead
case is unchanged.

`render_bundle_markdown()` previously appended
`" (docs-only ahead of live)" if b["docs_only_ahead"] else ""` inline. It now
computes a three-way `ahead` string ahead of the f-string: `" (equal to live)"`
when `b["live"]["rev"] == b["head"]`, `elif b["docs_only_ahead"]`
`" (docs-only ahead of live)"`, `else` `""`. Position in the line, the
`— WORKING TREE DIRTY` suffix and the trailing `.` are unchanged, so the
rendered line matches the section's interface exactly.

The new test `test_bundle_says_equal_to_live_when_head_is_live` reuses
`make_repo` and `fake_nixos_version`, checks the repo out at `live` so the
repo's HEAD *is* the live rev, points the fake `nixos-version` at that rev, and
asserts all three things the section names: `b["docs_only_ahead"] is False`,
`"(equal to live)" in md`, `"docs-only" not in md`. The existing
docs-only-ahead test (`test_bundle_reports_live_head_docs_only_checks_gaps_and_helm`,
which asserts `docs_only_ahead is True` and `"docs-only ahead" in md`) still
passes.

## Usage

Effort actually sent: `reasoningEffort: medium`. Wall clock 117 s, exit 0.

```json
{"model": "deepseek/deepseek-v4-pro-0813", "events": 408, "input": 189122, "output": 5243, "cacheRead": 286720, "reasoning": 0, "duration_s": 117.04}
```

Diffstat: `pkgs/evidence/evidence.py` +12/-2, `tests/evidence/test_evidence.py`
+17, 2 files, 27 insertions, 2 deletions.

## Checks

All run in the throwaway clone at `task/X2med`, tooling only via
`nix develop -c`, `XDG_CACHE_HOME` pinned to a scratch dir.

| check | command | result |
| --- | --- | --- |
| commit shape | `git show --stat HEAD` | 1 commit on base; exactly `pkgs/evidence/evidence.py`, `tests/evidence/test_evidence.py` |
| commit subject | byte compare against the section's `**commit subject:**` | identical |
| trailers | `git log -1 --format=%B` | `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run em)` and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` |
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | exit 0 |
| lint (check) | `nix build .#checks.x86_64-linux.lint -L --no-link` | exit 0 |
| lint gate | `nix develop -c githooks/pre-commit` | exit 0 ("All checks passed!", 0 files changed) |
| pytest | `nix develop -c pytest tests/evidence -q -p no:cacheprovider` | 56 passed |

## Red before green

`git checkout HEAD~1 -- pkgs/evidence/evidence.py` (base implementation, HEAD's
tests), then
`nix develop -c pytest tests/evidence -q -p no:cacheprovider -k "equal or docs_only or bundle"`:

```
FAILED tests/evidence/test_evidence.py::test_bundle_says_equal_to_live_when_head_is_live
>       assert b["docs_only_ahead"] is False
E       assert True is False
1 failed, 6 passed, 49 deselected
```

The new test is load-bearing: it fails on the base implementation with exactly
the failure the section's Step 2 predicts. `evidence.py` restored; working tree
verified clean afterwards.

## Mutation table

Four mutations, each applied to `pkgs/evidence/evidence.py` alone and reverted
after; full `tests/evidence` run each time (56 tests).

| # | mutation | outcome | killed by |
| --- | --- | --- | --- |
| M1 | `docs_only = False` always | killed | `test_bundle_reports_live_head_docs_only_checks_gaps_and_helm` (`… and False is True`) |
| M2 | print `(equal to live)` also when ahead (`if equal or b["docs_only_ahead"]`, no `docs-only` branch) | killed | `test_bundle_reports_live_head_docs_only_checks_gaps_and_helm` (`'docs-only ahead' in md` fails) |
| M3 | drop the equal branch (render reverted to the one-line `docs_only_ahead` conditional) | killed | `test_bundle_says_equal_to_live_when_head_is_live` (`'(equal to live)' in md` fails) |
| M4 | drop the `live != head` guard in `bundle()`, keep the render change | killed | `test_bundle_says_equal_to_live_when_head_is_live` (`assert True is False`) |

Both halves of the change are independently pinned (M4 pins the `bundle()`
guard, M3 pins the render branch), and the pre-existing docs-only-ahead
behaviour is pinned in both directions (M1, M2).

## Findings

1. **Minor — the equality branch fires when both revs are unknown.** The render
   test is `b["live"]["rev"] == b["head"]`, which is also true when both are
   `None` (live rev unparseable *and* `git rev-parse` failed). Verified in the
   devShell: a bundle with `live.rev = None`, `head = None` now renders
   `**Live:** unknown generation at none. **HEAD:** none (equal to live).`,
   where the base code correctly rendered nothing extra — so the section's
   "nothing extra otherwise" is violated in that degenerate case. The suite
   already builds such a bundle
   (`test_bundle_run_failure_is_not_fatal`, which asserts `live["rev"] is None`
   and `head is None`) but never renders it, so nothing catches it. A guard of
   the shape `b["head"] and b["live"]["rev"] == b["head"]` would close it. Not
   grounds for rejection: it is a degenerate off-host case, outside the
   section's stated interface, and the pre-existing `short()` helper already
   prints `none` for both revs there, so the line is visibly a no-data line.
   Worth a one-line follow-up.
2. **Positive — the `_docs_equivalent` short-circuit was diagnosed, not
   patched around.** The commit body names the exact cause (`return True` on
   `a == b`) rather than special-casing the symptom in the renderer, and the
   fix keeps `docs_only_ahead` semantically honest for every other consumer of
   the dict, not just the markdown line.
3. **Positive — the test builds the equal case honestly.** It checks the repo
   out at `live` rather than stubbing `_git`, so `head` is genuinely the live
   rev and `_docs_equivalent` is genuinely exercised on the equal input; that
   is what lets M4 be killed.
4. No formatting, ruff, or statix debt: the lint gate reports 0 files changed.

## Deviations

- **From the section text: none material.** Files, commit subject, trailers,
  the three asserted facts, the helper reuse, and the acceptance set
  (`evidence-unit`, `lint`) all match. Step order (failing test → red → implement
  → green → commit) is followed and visible in the transcript.
- **Transcript economy.** 192 lines, five reasoning blocks, no reversals and no
  dead ends. Roughly the first 145 lines are a single up-front analysis block
  that reads the code, works out the `_docs_equivalent` short-circuit, drafts
  the exact test and the exact patch, and checks the fake `nixos-version` stub's
  argument handling before touching anything; the remaining blocks are red,
  implement/green, and commit. It briefly weighed adding a new bundle field for
  equality and correctly discarded it as beyond the interface, and it paused
  once over the trailer conflict between `AGENTS.md` ("no `Co-Authored-By`")
  and the task text (both trailers) and followed the task text — the right
  call.
- **Nothing beyond the ask.** No extra files, no refactors, no docs edits, no
  board update. The workspace is clean (`git status --porcelain` empty), so the
  scratch directory the transcript mentions was not left behind.
- **One report-only inaccuracy** (not in the code): the final agent message
  claims "20/20 pytest tests" where `pytest tests/evidence` is 56 tests; the
  `.result` line and the checks themselves are accurate.
