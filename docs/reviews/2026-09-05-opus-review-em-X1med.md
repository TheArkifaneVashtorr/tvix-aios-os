# Opus gate — seat run em, task X1med — APPROVED

Reviewer: Opus gate (effort-comparison arm `em`, DeepSeek V4 Pro at effort **medium**).
Workspace (read-only): `/home/dalhaka/factory/ws/em/X1med`, branch `task/X1med`.
Head `58e28c6451100654660942b306503da6f3114b4f` on base `90838458eb7d65d1a5c7b876abae5549e6d41c05`.
Effort actually sent (`/home/dalhaka/factory/runs/em/X1med.dsh-home/settings.yaml`): `reasoningEffort: medium`.
Gate ran in a throwaway local clone; the workspace was not touched.

## Summary

The task is done, correctly and minimally. One commit on base touches exactly the two files
the section names. `tile_backup_parity`'s early-return summary is now
`f"proton-drive-push.service last result {result}, status {status}"` — a one-line f-string
change, exactly the "one f-string change" Step 3 asked for. The detail dict is byte-identical
to base (`{"unit_result": result, "exec_main_status": status}`). Two new tests stub
`_unit_result` and assert the two exact strings the section specifies. The commit subject is
byte-identical to the section's, and carries the `Co-Authored-By: Claude Fable 5.1` trailer
(plus a permitted `Generated-By` line) and a genuinely informative body.

All four acceptance commands pass in the clone. Red-before-green reproduces: with `collect.py`
reverted to base and HEAD's tests in place, both new tests fail precisely on the missing
`, status 1` / `, status 0`, while the seven pre-existing parity tests stay green. Five
mutations, all killed.

Two deviations, both cosmetic and neither load-bearing: the tests were inserted next to the
existing parity tests rather than appended at end of file, and they stub `_unit_result`
directly (a lambda) rather than through the file's `systemctl_fake` + `monkeypatch.setattr(collect, "run", …)`
convention. The second is what the section's Step 1 text literally described, and the
implementer's transcript shows it noticed the divergence and chose the section's wording. No
extra edits, no scope creep, clean working tree.

## Usage

```json
{"model": "deepseek/deepseek-v4-pro-0813", "events": 326, "input": 298340, "output": 3799, "cacheRead": 343040, "reasoning": 0, "duration_s": 136.653}
```

Wall clock from the `.result` line: `wall_s: 138`, `exit_code: 0`. Note for the comparison:
the provider reported `reasoning: 0` tokens even though five reasoning blocks appear in the
transcript — at medium, reasoning is not billed out separately here. Diffstat: 2 files,
27 insertions, 1 deletion.

## Checks

Run in `/tmp/.../scratchpad/gate-em-X1med` (throwaway clone of the workspace, `task/X1med`
checked out), `XDG_CACHE_HOME` pinned under the scratchpad, tooling only via `nix develop -c`.

| Command | Result |
| --- | --- |
| `git show --stat HEAD` | exactly `pkgs/helm/collect.py` (2 ±) and `tests/helm/test_collect.py` (+26); one commit; parent == base `9083845` |
| commit subject byte-compare vs section | identical (`cat -A` on both, no trailing whitespace) |
| `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` | present (with an extra `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813` line, allowed) |
| `nix build .#checks.x86_64-linux.helm-unit -L --no-link` | pass — 148 passed in 13.28s |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | pass — all checks passed, 0 files changed by treefmt |
| `nix develop -c githooks/pre-commit` | pass — treefmt 0 changed, shellcheck/statix/deadnix/ruff clean, `render.test.mjs` assertions passed |
| `nix develop -c pytest tests/helm -q -p no:cacheprovider` | pass — 148 passed in 13.30s |
| `git status --porcelain` after checkout | clean (no stray commit-msg file left behind) |

Behaviour, verified by reading `pkgs/helm/collect.py:165-170` and the diff:

- early-return summary is `f"proton-drive-push.service last result {result}, status {status}"` — matches the interface exactly;
- the guard `if result != "success" or status != "0":` is unchanged;
- the detail dict `{"unit_result": result, "exec_main_status": status}` is unchanged from base;
- `("success", "1")` → `proton-drive-push.service last result success, status 1`, tile `fail` — asserted by `test_parity_red_summary_names_result_and_status`;
- `("failed", "0")` → `proton-drive-push.service last result failed, status 0`, tile `fail` — asserted by `test_parity_red_summary_names_failed_result_with_zero_status`.

Both tests assert on `==`, not `in`, so the exact string is pinned.

## Red before green

`git checkout <base> -- pkgs/helm/collect.py` (HEAD's tests kept), then
`nix develop -c pytest tests/helm -q -p no:cacheprovider -k parity`:

```
FAILED tests/helm/test_collect.py::test_parity_red_summary_names_result_and_status
FAILED tests/helm/test_collect.py::test_parity_red_summary_names_failed_result_with_zero_status
2 failed, 7 passed, 139 deselected
```

The failure text is the right failure, not an incidental one:

```
E       AssertionError: assert 'proton-drive...result success' == 'proton-dri...ess, status 1'
E         - ult success, status 1
E         + ult success
```

and for the second test `- sult failed, status 0` / `+ sult failed`. The seven pre-existing
parity tests (including `test_parity_nonzero_exit_status_is_fail`) stay green under the
revert, so the new tests are the only thing the change makes pass. `collect.py` restored
afterwards; tree clean.

## Mutation table

Each mutation applied to `pkgs/helm/collect.py` alone, full `tests/helm` suite run, file
restored with `git checkout HEAD --` after each. Baseline is 148 passed.

| # | Mutation | Outcome | Killed by |
| --- | --- | --- | --- |
| M1 | drop `, status {status}` from the summary f-string (revert to base wording) | **killed** — 2 failed, 146 passed | `test_parity_red_summary_names_result_and_status`, `test_parity_red_summary_names_failed_result_with_zero_status` |
| M2 | swap the two interpolations: `last result {status}, status {result}` | **killed** — 2 failed, 146 passed | `test_parity_red_summary_names_result_and_status`, `test_parity_red_summary_names_failed_result_with_zero_status` |
| M3 | make the early return not fire on a non-zero status: `if result != "success":` | **killed** — 2 failed, 146 passed | `test_parity_nonzero_exit_status_is_fail` (pre-existing), `test_parity_red_summary_names_result_and_status` (new) |
| M4 | drop the comma separator: `last result {result} status {status}` | **killed** — 2 failed, 146 passed | both new tests |
| M5 | rename the detail key `exec_main_status` → `exit_status` (detail-dict-unchanged guard) | **killed** — 1 failed, 147 passed | `test_parity_nonzero_exit_status_is_fail` |

M3 is the important one for the comparison: the new `("success", "1")` test kills the guard
mutant on its own, so the summary test is not merely a string echo — it re-proves the branch
condition. M5 shows the "detail dict unchanged" half of the interface is guarded, though by a
pre-existing test rather than a new one (the new tests do not assert on `detail`; see
Findings).

## Findings

1. **Correct and minimal.** The production change is one line, exactly as scoped. Nothing in
   `collect.py` outside the f-string moved. No helper was introduced, no signature changed,
   no other tile touched.
2. **The new tests are load-bearing, not decorative.** They fail red on the right assertion,
   and they kill three distinct mutants including the guard-condition mutant M3. The `==`
   assertions pin the exact interface string rather than a substring.
3. **Minor, not blocking — the new tests do not assert the detail dict.** The section says
   "the detail dict is unchanged"; that half of the interface is protected only by the
   pre-existing `test_parity_nonzero_exit_status_is_fail` (M5 confirms it holds). Adding
   `assert t["detail"] == {"unit_result": "success", "exec_main_status": "1"}` to the new test
   would have pinned both halves in one place. Not worth a rejection: the guard exists and is
   proven.
4. **Minor, not blocking — stubbing `_unit_result` skips a layer.** Patching `_unit_result`
   with a lambda bypasses the `systemctl show` output → tuple parsing that the file's other
   parity tests exercise via `systemctl_fake`. Under this stub the tests would still pass if
   `_unit_result`'s parsing broke. That path is separately covered by
   `test_parity_nonzero_exit_status_is_fail`, and the section's Step 1 explicitly framed the
   test in terms of "`_unit_result` returns", so this is a faithful reading, not a shortcut.
   Worth noting because a future refactor of `_unit_result`'s signature would silently
   desync these two lambdas (`lambda scope_args, unit:` is positional-compatible today).
5. **Commit hygiene is good.** Subject byte-identical; a three-sentence body that states the
   actual bug (a red tile reading `last result success`, "indistinguishable from healthy")
   rather than restating the diff; both trailers present; the temporary commit-message file
   was removed, leaving a clean tree.
6. **No scope creep.** Nothing edited beyond the two named files. No README, no board update,
   no opportunistic refactor, no new helper, no test-suite reorganisation.

## Deviations

Deviations from the `### X1med (code, XS)` section text, counted exhaustively:

1. **Test placement (cosmetic).** The section's Files line says `tests/helm/test_collect.py`
   **(append)**. The two tests were *inserted* at line 393, immediately after
   `test_parity_nonzero_exit_status_is_fail`, not appended to the end of the 1339-line file.
   Thematically the better placement; still not what the section said.
2. **Monkeypatch style (substantive but sanctioned).** Step 1 says "find how existing tests
   stub `_unit_result` (monkeypatch)". No existing test stubs `_unit_result` at all — the
   file's convention is `systemctl_fake(...)` plus `monkeypatch.setattr(collect, "run", _run)`.
   The implementer stubbed `collect._unit_result` directly with a lambda instead. The
   transcript shows it spotted the mismatch explicitly ("the existing tests stub `run`, not
   `_unit_result` … the task placeholder says to monkeypatch `_unit_result` directly") and
   followed the section's literal wording. Defensible; see Finding 4.
3. **Test names are the implementer's own** (`test_parity_red_summary_names_result_and_status`,
   `test_parity_red_summary_names_failed_result_with_zero_status`). The section named no
   tests, so this is free choice, recorded only for cross-arm comparison.
4. **Commit body beyond the subject.** The section fixes only the subject; the implementer
   added a five-line body and a `Generated-By` trailer. Permitted, and an improvement.
5. **One reversal in the run.** The lint gate initially reported that `treefmt` had
   reformatted `test_collect.py` (the new test's `monkeypatch.setattr(...)` call was
   re-wrapped); the implementer re-ran the gate, inspected the reformat, and continued. One
   extra gate invocation; no incorrect work was done and nothing was reverted.

**Extra work beyond the ask:** none, other than the commit body (4) and removing the
temporary commit-message file to leave a clean tree.

**Transcript economy** (`/home/dalhaka/factory/runs/em/X1med.log`, 73 lines): five reasoning
blocks — orient/plan, write the tests, confirm red, handle the treefmt reformat, commit and
tidy — then a five-point summary and the FACTORY block. Steps map one-to-one onto the
section's Steps 1-5 with a single extra lint re-run. No dead ends, no abandoned approaches, no
files created and deleted, no re-reading of the same file. 326 events, 138s wall, 3799 output
tokens. The first reasoning block spends a few sentences deciding whether to load the TDD
skill before concluding the task is concrete enough to proceed — the only visible
deliberation overhead in the run, and it is small.
