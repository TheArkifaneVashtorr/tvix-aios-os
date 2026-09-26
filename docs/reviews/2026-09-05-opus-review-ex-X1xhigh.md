---
reviewer: opus
majors: null
minors: null
---
# Opus gate — seat run ex, task X1xhigh — APPROVED

## Summary

One commit on base, exactly the two files the section names, subject byte-identical
to the plan's, both trailers present. The behaviour is the one asked for: the
`tile_backup_parity` early return now reads
`proton-drive-push.service last result {result}, status {status}` and the detail
dict is untouched. Both Step 1 tests exist with the exact expected strings. All
four acceptance runs pass from a throwaway clone. Red was reproduced by reverting
`collect.py` to base with HEAD's tests: both new tests fail on the missing
`, status …` while the seven pre-existing parity tests stay green. Four mutations,
four kills.

Effort actually sent: `reasoningEffort: xhigh`
(`/home/dalhaka/factory/runs/ex/X1xhigh.dsh-home/settings.yaml`).

Two minors, neither blocking: the tests stub `collect._unit_result` directly
rather than the house `collect.run` + `systemctl_fake` seam the adjacent parity
test uses (documented in a comment, and the scope-pinning coverage it bypasses is
already held by `test_parity_nonzero_exit_status_is_fail`); and the implementer's
closing report claims "10 reformat-driven treefmt round-trips" where the
transcript shows exactly one.

## Usage

```json
{"model": "deepseek/deepseek-v4-pro-0813", "events": 594, "input": 316895, "output": 7803, "cacheRead": 517632, "reasoning": 0, "duration_s": 204.422}
```

Wall clock 205 s, exit 0. head `38ba615dc22b876e767647225ac5c627162d9a1d`,
base `90838458eb7d65d1a5c7b876abae5549e6d41c05`, one commit between them.

## Checks

Run in a throwaway clone of the workspace at `task/X1xhigh`, tooling via
`nix develop -c`, `XDG_CACHE_HOME` pinned under the session scratch.

| Gate | Result |
| --- | --- |
| `nix build .#checks.x86_64-linux.helm-unit -L --no-link` | pass (exit 0) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass — treefmt 84 files, 0 changed; statix/deadnix/ruff clean |
| `nix develop -c githooks/pre-commit` | pass — 0 changed, `render.test.mjs` assertions passed |
| `nix develop -c pytest tests/helm -q -p no:cacheprovider` | 148 passed in 13.30s |

Commit hygiene: `git show --stat HEAD` lists exactly `pkgs/helm/collect.py` (1
insertion, 1 deletion) and `tests/helm/test_collect.py` (30 insertions). Subject
md5 matches the plan section's subject md5 (`f13b6980f1dd387745e4598df8033a03`).
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present, with an extra
`Generated-By:` line (allowed). The workspace tree is clean — the scratch commit
message file was removed.

Behaviour by inspection: the early return is

```python
    if result != "success" or status != "0":
        return (
            "fail",
            f"proton-drive-push.service last result {result}, status {status}",
            {"unit_result": result, "exec_main_status": status},
        )
```

— the guard and the detail dict are unchanged from base; only the f-string moved.

## Red before green

`git checkout <base> -- pkgs/helm/collect.py` with HEAD's test file, then
`nix develop -c pytest tests/helm -q -p no:cacheprovider -k parity`:

```
FAILED tests/helm/test_collect.py::test_parity_success_nonzero_status_names_result_and_status
  assert 'proton-drive...esult success' == 'proton-drive...ess, status 1'
    - ult success, status 1
    + ult success
FAILED tests/helm/test_collect.py::test_parity_failed_result_zero_status_names_result_and_status
  assert 'proton-drive...result failed' == 'proton-drive...led, status 0'
2 failed, 7 passed, 139 deselected
```

Both new tests fail for exactly the reason the section predicts (the missing
`, status …` suffix), and no pre-existing parity test is disturbed. `collect.py`
restored; tree clean afterwards.

## Mutation table

Each mutation applied alone to `pkgs/helm/collect.py` on HEAD, full
`tests/helm` suite run, then reverted.

| # | Mutation | Outcome | Killed by |
| --- | --- | --- | --- |
| M1 | Drop `, status {status}` from the summary (revert the f-string to base) | killed — 2 failed, 146 passed | `test_parity_success_nonzero_status_names_result_and_status`, `test_parity_failed_result_zero_status_names_result_and_status` |
| M2 | Swap the two interpolations: `last result {status}, status {result}` | killed — 2 failed, 146 passed | same two (diff shows `last result 0, status failed`) |
| M3 | Weaken the guard to `if result != "success":` so the early return no longer fires on a non-zero status with a success result | killed — 2 failed, 146 passed | `test_parity_nonzero_exit_status_is_fail` (pre-existing), `test_parity_success_nonzero_status_names_result_and_status` |
| M4 | Hardcode the status: `…, status 0` | killed — 1 failed, 147 passed | `test_parity_success_nonzero_status_names_result_and_status` |

M4 is the one that separates the two new tests: the `("failed", "0")` case alone
cannot see a hardcoded `0`, so the `("success", "1")` case is load-bearing on its
own. M2 shows the ordering is pinned, not just the presence of both tokens.

## Findings

1. **Test seam differs from the house style (minor, not blocking).** Every other
   parity test stubs `collect.run` through `systemctl_fake` / `_unit_show`, which
   exercises `_unit_result`'s systemctl parsing and pins the systemd scope
   (`--user`). The two new tests monkeypatch `collect._unit_result` directly:
   `monkeypatch.setattr(collect, "_unit_result", lambda scope_args, unit: ("success", "1"))`.
   The section's Step 1 wording ("find how existing tests stub `_unit_result`
   (monkeypatch)") is ambiguous enough to justify either reading, and the
   implementer wrote a comment explaining the choice as deliberately scoping the
   assertion to the early-return branch. Consequence: a wrong-scope or
   parsing regression is invisible to these two tests — but
   `test_parity_nonzero_exit_status_is_fail`, immediately above them, still
   covers it with `scope="user"`, so no coverage is lost overall. M3 confirms
   that pre-existing test is doing its job.
2. **Overstated number in the closing report (minor, cosmetic).** The final
   message says the lint gate "passed (10 reformat-driven treefmt round-trips
   resolved before the gate went clean)". The transcript shows one: treefmt
   rewrapped the long `monkeypatch.setattr(...)` call and the second test's
   signature, the gate failed on `--fail-on-change`, and the next run was clean.
   No effect on the artefact; noted because an unmeasured count in a report is
   the kind of claim this project treats as debt.
3. **The second test asserts more than the section requires.** For the
   `("failed", "0")` case the section only asks for the summary; the test also
   asserts `t["status"] == "fail"` and the full detail dict. This is the
   "detail dict is unchanged" interface pinned rather than assumed — a small
   improvement, and it costs nothing.
4. No stray edits, no scope creep, no leftover files. The formatting the gate
   demanded was applied and re-verified with a second `helm-unit` build before
   the commit, which is the right instinct.

## Deviations

Counted against the `### X1xhigh` section text.

| # | Deviation | Severity |
| --- | --- | --- |
| 1 | Test placement: section says `tests/helm/test_collect.py` (append); the two tests were inserted mid-file directly after `test_parity_nonzero_exit_status_is_fail` rather than at the end | cosmetic — arguably better cohesion |
| 2 | Monkeypatch style: `collect._unit_result` stubbed directly instead of the `collect.run` + `systemctl_fake` seam used by every neighbouring parity test | minor (Finding 1) |
| 3 | Extra assertions in the second test (`status == "fail"`, full detail dict) beyond the summary the section asks for | cosmetic, favourable |
| 4 | Commit body: a four-line rationale paragraph the section does not ask for; `Generated-By:` trailer alongside `Co-Authored-By:` | none — allowed |
| 5 | Extra tooling beyond the listed Step 4 commands: a standalone `ruff check`, and a second `helm-unit` build after the formatter rewrote the test file | none — verification, not scope |

No deviation in files touched, commit count, subject bytes, behaviour, or the
ordering of the TDD steps (Step 2's `-k parity` red run was executed as written).

Transcript economy: 262 lines / 19.6 KB, 15 reasoning blocks, 594 events,
7803 output tokens, 204 s wall. One reversal — the treefmt line-length rewrap and
the re-run of the lint gate and `helm-unit` that followed it. No wrong turns of
substance: the file reads, the red run, the one-line change, the green run, the
gates, the commit. A short stretch of reasoning was spent second-guessing whether
`nix build` sees modified-but-unstaged tracked files (it does; the implementer
resolved it correctly from the evidence that the new tests had already run inside
the check).
