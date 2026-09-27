import json, subprocess, sys
root = "/home/user/tvix-aios-os"
out = subprocess.run([sys.executable, f"{root}/pkgs/evidence/tasks.py", "--root", root, "json"], capture_output=True, text=True)
data = json.loads(out.stdout)
repos = data["repos"]
print("repos type:", type(repos).__name__, "keys:", list(repos.keys())[:6] if isinstance(repos, dict) else len(repos))
first = repos[list(repos.keys())[0]] if isinstance(repos, dict) else repos[0]
print("repo entry keys:", list(first.keys()) if isinstance(first, dict) else type(first))
items = []
for rname, r in (repos.items() if isinstance(repos, dict) else enumerate(repos)):
    ts = r.get("tasks", [])
    if isinstance(ts, dict):
        for k, t in ts.items():
            t = dict(t); t.setdefault("key", k); t["repo"] = rname; items.append(t)
    else:
        for t in ts:
            t = dict(t); t["repo"] = rname; items.append(t)
print("n tasks:", len(items))
print("task keys:", sorted(items[0].keys()))
from collections import Counter
print("states:", Counter(t.get("state") for t in items))
watch = ["tools/factory/seat", "docs/ledger/routing.toml", "tools/factory/route.py", "pkgs/seat", "nixosModules/seatLane.nix",
         "pkgs/evidence/tasks.py", "pkgs/evidence/evidence.py", "pkgs/evidence/report.py", "pkgs/evidence/SCHEMA.md", "tests/unit/80-seat-driver.bats", "tests/unit/91-orchestrator-guard", "tests/evidence/test_tasks.py", "tests/evidence/test_report.py",
         "tools/orchestrator-guard.sh", "flake.nix", "docs/ledger/claims.toml", "docs/ledger/task-classes.toml", "tests/seat", "hosts/core/seat.nix", "docs/MAP.md", "hook-guard", "pkgs/dsh-openrouter", "tests/unit/70-dsh-openrouter.bats", "docs/runbooks/lanes.md"]
print("--- non-landed tasks touching watched paths ---")
for t in items:
    st = t.get("state")
    if st == "landed":
        continue
    touches = t.get("touches") or []
    hits = sorted({w for w in watch if any(w in str(p) for p in touches)})
    if hits:
        print(f"{t['repo']}\t{t.get('key')}\t{st}\t{t.get('plan')}\tdeps={t.get('depends_on')}\thits={hits}")
print("--- all tasks in telemetry-store-1 and planning-agent plans ---")
for t in items:
    if t.get("plan") in ("2026-09-06-telemetry-store-1.md", "2026-09-06-planning-agent.md", "2026-09-05-seat-behind-broker.md", "2026-09-05-seat-routing.md", "2026-09-05-factory-dispatch.md"):
        print(f"{t.get('plan')}\t{t.get('key')}\t{t.get('kind')}\t{t.get('size')}\t{t.get('state')}\tdeps={t.get('depends_on')}")
