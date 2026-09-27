#!/usr/bin/env bash
# The dispatcher's FACTORY_WAVES_CMD seam over the draft (not yet under the plans
# directory): the graph's own functions, no logic re-derived — prints the draft's
# next wave exactly as `waves --next` would.
set -euo pipefail
draft=${DRAFT:-/tmp/draft-scratch/draft-0.md}
root=${ROOT:-/home/user/tvix-aios-os}
exec python3 - "$draft" "$root" <<'PY'
import os, sys
draft, root = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(root, "pkgs", "evidence"))
import tasks
repos = tasks.load_repos(os.path.join(root, "docs", "ledger", "repos.toml"))
plan_status = tasks.load_plan_status(os.path.join(root, "docs", "ledger", "plan-status.toml"))
task_status = tasks.load_task_status(os.path.join(root, "docs", "ledger", "task-status.toml"))
scanned = [tasks.scan_repo(r, plan_status, "/nonexistent", "/nonexistent", repos=repos, task_status=task_status, stale_after=tasks._stale_after_default()) for r in repos]
d = tasks.load_draft(draft, root, repos, scanned)
lines = tasks.wave_lines(d["scanned"], plan=d["plan_name"])
if lines:
    print(lines[0])
PY
