# Decision 2026-09-05 — commit metadata: mixed trailers are fine; subjects keep the `(test: …)` convention

Operator, 2026-09-05, closing claim `s12-commit-metadata-decision` (raised by the nixos-skill round-2 report): "Mixed trailers is fine."

1. A factory commit carries both `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` (the plan's required trailer) and the seat's machine-set `Generated-By: dsh <version> / <model> (seat headless, factory run <run>)`. Both are attribution; neither replaces the other. Reviews stop counting the second trailer as a deviation.
2. Subjects keep the house convention: `<area>: summary (test: <check names>)`, docs commits `(test: lint)`. The plan's `commit subject` line is the contract and is byte-identical in the commit — the derived task graph marks a chain landed by that string (`pkgs/evidence/tasks.py`).
3. Fix rounds keep the original task's subject (same rule, same reason).
