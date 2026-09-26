# Opus gate — seat run ev1, task E4 — APPROVED

Branch head `cb8e0ac7b738` (`~/factory/ws/ev1/E4`, `task/E4`). Reviewer: Opus, high effort, throwaway clone; checks re-run by ref.

## Summary

E4 is correct and complete; I could not break it. The diff is one commit (cb8e0ac) touching exactly the four files the plan's `touches` names, with the plan's commit subject byte-identical and the required Co-Authored-By trailer exact. Both Interfaces items are implemented as specified: `_read_findings` now fills `task`/`round`/`label` from the result's `task_key`/`round`/`label` (null for older journals, verified by the second journal row in the test), and `DEFAULT_LEDGER = os.path.join(os.environ.get(\"EVIDENCE_STORE\", \"/var/lib/evidence\"), \"ledger\")`. The forbidden fixture tests/ledger/fixtures/workflow/journal.jsonl is untouched, and its finding-count pins at :270/:290 still pass. schema.md's location paragraph, the `factory-findings.jsonl` example (`\"label\":null` in the same position as the code's dict order) and the table row all match the plan's dictated wording; the `factory-agents.jsonl` `label` row correctly stays `null` with its reason; docs/runbooks/lanes.md lines 199-200 carry the new phrase at 73/74 columns, in keeping with the surrounding wrap. Red-before-green proved: reverse-applying only the implementation yields the plan's exact predicted failures (KeyError: 'label' and /home/dalhaka/strategy/ledger). Five mutations aimed where a vacuous test would hide — wrong source key, restored `None` constant, finding-vs-result confusion, dropped env override, wrong default root — were all killed, each by the named new test, with the other 34 tests still passing (so the kills are specific, not collateral). Acceptance checks re-run with --rebuild to defeat cache echo: ledger-unit exit 0 (35 passed), lint exit 0, plus the pre-commit gate exit 0. No bypass flags, no `2>/dev/null` on a gated command, no sudo/rebuild/systemctl in the transcript, no secrets, stdlib-only Python, no placeholder text. Blast radius checked: the findings merge key is `(run_id, file, title)`, unchanged by the three new fields, so idempotency holds; `rollup --costs/--activity` take explicit CSV paths, so moving DEFAULT_LEDGER does not strand the operator's `~/strategy/ledger/openrouter-activity.csv`. The one forward reference — schema.md calling /var/lib/evidence/ledger \"a restic path\" — is E1's job (hosts/core/proton-backup.nix) and is dictated by the plan, not an E4 defect. Approved.

## Checks

- green — ledger-unit: nix build .#checks.x86_64-linux.ledger-unit -L --no-link --rebuild → exit 0; 'ledger-unit> 35 passed in 0.11s' (forced --rebuild so the result is not a cache echo)
- green — lint: nix build .#checks.x86_64-linux.lint -L --no-link --rebuild → exit 0; 'lint> formatted 72 files (0 changed)', 'lint> All checks passed!', 'lint> 20 files already formatted'
- green — githooks/pre-commit (lint gate): nix develop -c githooks/pre-commit → exit 0; treefmt 0 changed, ruff 'All checks passed!', shellcheck/statix/deadnix clean, 'render.test.mjs: all assertions passed'
- green — pytest tests/ledger -q (in devShell): 35 passed in 0.08s at HEAD
- green — spec/touches compliance: diff touches exactly tools/ledger/factory.py, tools/ledger/schema.md, tests/ledger/test_factory.py, docs/runbooks/lanes.md — the plan's 'touches' list, nothing more; tests/ledger/fixtures/workflow/journal.jsonl untouched as the plan demands
- green — commit subject + trailer: subject byte-identical to the plan's 'commit subject'; trailer 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>' exact (preceded by the seat's standard Generated-By: dsh … trailer, the harness convention, not a plan deviation)
- green — hard rules scan: grep of /home/dalhaka/factory/runs/ev1/E4.log for '2>/dev/null', '--no-verify', 'sudo ', 'nixos-rebuild', 'systemctl' → no hits; no secrets added; Python change is stdlib only (os.environ/os.path.join); implementer's workspace tree is clean (scratch commit-msg.txt removed, not committed)

## Red before green

Reverse-applied the implementation only, keeping tests at HEAD, in a throwaway clone: `git checkout HEAD~1 -- tools/ledger/factory.py` then `nix develop -c pytest tests/ledger -q -k "label or default_ledger"`. Result: `2 failed, 33 deselected in 0.09s`. Decisive lines — `tests/ledger/test_factory.py:371: KeyError: 'label'` and `tests/ledger/test_factory.py:381: AssertionError: assert '/home/dalhak...rategy/ledger' == '/tmp/ev/ledger'` (diff `- /tmp/ev/ledger  + /home/dalhaka/strategy/ledger`). This is exactly the red the plan's Step 2 predicts ("KeyError: 'label' and ~/strategy/ledger"). Restored with `git checkout HEAD -- tools/ledger/factory.py`; baseline green re-confirmed at 35 passed.

## Mutation table

| mutation | killed | by |
|---|---|---|
| tools/ledger/factory.py:156 `"task": result.get("task_key")` → `result.get("task")` (plausible wrong source key; a vacuous test that only checked the key exists would survive) | yes | tests/ledger/test_factory.py::test_findings_carry_task_round_and_label_when_the_result_has_them — 1 failed, 34 passed; AssertionError at :371 |
| tools/ledger/factory.py:157 `"round": result.get("round")` → `"round": None` (restores the pre-change constant; a test asserting only 'the key is present' would survive) | yes | test_findings_carry_task_round_and_label_when_the_result_has_them — 1 failed, 34 passed; AssertionError at :371 |
| tools/ledger/factory.py:158 `"label": result.get("label")` → `finding.get("label")` (reads the finding instead of the result — the exact confusion the task is about) | yes | test_findings_carry_task_round_and_label_when_the_result_has_them — 1 failed, 34 passed; AssertionError at :371 |
| tools/ledger/factory.py:40-42 whole expression → `DEFAULT_LEDGER = "/var/lib/evidence/ledger"` (drops the EVIDENCE_STORE override; a test that only pinned the default path would survive) | yes | test_default_ledger_is_under_the_evidence_store — 1 failed, 34 passed; `- /tmp/ev/ledger  + /var/lib/evidence/ledger` at :381 |
| tools/ledger/factory.py:41 default root constant `"/var/lib/evidence"` → `"/var/lib/evidence-x"` (a test that only exercised the env-set branch would survive) | yes | test_default_ledger_is_under_the_evidence_store — 1 failed, 34 passed; `- /var/lib/evidence/ledger  + /var/lib/evidence-x/ledger` at :383 |

## Findings

none

## Deviations

The FACTORY-RESULT declares no deviations ("TDD red→green observed (KeyError 'label' then DEFAULT_LEDGER default), all acceptance checks pass") and I found none to add. Two things worth naming, both accepted: (1) the implementer also updated the module docstring of tools/ledger/factory.py (``~/strategy/ledger/`` → ``/var/lib/evidence/ledger/``, overridable via ``EVIDENCE_STORE``); the plan's Step 3 does not list it, but the file is inside `touches` and leaving the docstring would have made it a lie — accepted as in-scope truth maintenance. (2) The commit carries the seat's `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run ev1)` trailer above the required Co-Authored-By line; that is the seat harness's own convention, the plan's required trailer is present verbatim, so not a deviation. The test bodies differ from the plan text only by `ruff format` re-wrapping of the `json.dumps` literals — explicitly declared a non-deviation by the plan's Global Constraints ("The Python blocks below are specifications, not byte-exact files"), and it explains the +68-line diffstat against ~24 lines of authored test.
