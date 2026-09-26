# Session context and the derived task graph — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) and `tools/factory/dark-factory.js` both read the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and `commit subject`.

**Goal:** a fresh session receives the board's one START HERE, the evidence bundle and a one-screen task brief automatically; one dependency-aware queue across five repos is derived from files, never typed.

**Architecture:** two stdlib Python modules beside `pkgs/evidence/evidence.py` — `tasks.py` (plan parser, status precedence, graph, waves, conflicts, checks, brief) and `repomap.py` (a generated `docs/MAP.md`) — tested under the existing `evidence-unit` check; then the `evidence` CLI, the pre-commit hook and a SessionStart hook wire them in; then CLAUDE.md and the board shrink to what the generators do not produce.

**Tech Stack:** Python 3 stdlib (`re`, `tomllib`, `fnmatch`, `json`, `subprocess`), pytest, bash + bats for the hook, Nix `runCommand` checks.

**Spec:** `docs/superpowers/specs/2026-09-05-session-context-and-task-graph-design.md` (approved 2026-09-05).

## Decisions (amendments to the spec, recorded here and appended to the spec)

1. **Legacy plan status lives in `docs/ledger/plan-status.toml` for every repo**, not in front matter. The 31 legacy plans are historical documents and sibling repos are read-only; one override table in this repo is uniform and needs no edit outside it. Allowed statuses: `done | superseded | parked | open`.
2. **The repo-map generator is `pkgs/evidence/repomap.py`**, not `tools/docs/repo-map.py`, so its tests run under `evidence-unit` today (the check copies `pkgs/evidence` and `tests/evidence` wholesale) and wave 1 never touches `flake.nix`.
3. **Wave 1 touches no file the evidence plan's wave 3 touches** (`flake.nix`, `pkgs/evidence/evidence.py`, `githooks/pre-commit`, `CLAUDE.md`, `README.md`, `docs/OPERATIONS.md`). It runs beside that wave now.

## Global Constraints

- Build-only: never `sudo`, `nixos-rebuild`, `systemctl`, basket mount or teardown. The host runs live from this repo.
- Every check named in a task's acceptance is run as `nix build .#checks.x86_64-linux.<name> -L --no-link`; the lint gate is `nix develop -c githooks/pre-commit`; commits go through `nix develop -c git commit -F <msgfile>` (message file in the scratch directory, never `-m`).
- TDD: the failing test first; a test counts only once it has been shown to fail (red before the change).
- Python: stdlib only in `pkgs/evidence/`; `ruff format` + `ruff check` clean (`nix develop -c ruff format pkgs/evidence tests/evidence`).
- Bash: shellcheck clean; scripts under `tools/` are swept by the pre-commit hook.
- Never `2>/dev/null` a gated command. `git add` new files before any `nix build`.
- Sibling repos (`~/flakes/*`) are read-only for every task here. Nothing writes outside this repo, the scratch directory and (tests) `tmp_path`.
- Commit subjects: `<area>: summary (test: <checks>)` with the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Test files under `tests/evidence/` load modules by path (see `tests/evidence/test_evidence.py:16-27`); copy that helper, do not `import pkgs.evidence`.

## Waves

| wave | groups (seat driver) | dependsOn | starts |
|---|---|---|---|
| 1 | `"G1 G4"` `"G2"` `"G3"` | G4: [G1] | now — disjoint from evidence-plan wave 3 |
| 2 | `"G5"` `"G6"` | G5: [G4, G2, G3]; G6: [G4] | after wave 1 integrates (the evidence plan's wave 3 was already on main at 11:34 on 2026-09-05, before this plan was committed) |
| 3 | `"G9 G8"` `"G7"` `"G10"` | G9: [G5]; G8: [G5, G9] (both edit tasks.py: chained); G7: [G5, G2]; G10: [G6] | after wave 2 integrates |

Dispatch (wave 1): `FACTORY_PLAN=$HOME/nixos-agent-env/docs/superpowers/plans/2026-09-05-session-context.md OPENROUTER_REASONING_EFFORT=medium nohup tools/factory/seat/factory-wave sc1 "$HOME/nixos-agent-env" "G1 G4" "G2" "G3" >"$HOME/factory/runs/sc1.wave.log" 2>&1 &`. Gate: Opus review per task (`tools/factory/seat/factory-review sc1 ~/nixos-agent-env <KEY>`), one bounded fix round (`<KEY>b`), then re-plan (rule A1). Integrate: `factory-integrate sc1 ~/nixos-agent-env G1 G4 G2 G3`, then `git pull --ff-only ~/factory/base/nixos-agent-env integ/sc1`.

## Operator

Nothing to switch in waves 1–2. After wave 2 lands, the next `/new` in the desktop app's Code tab on `~/nixos-agent-env` shows the hook output; if it does not, the runbook `docs/runbooks/session.md` (G6) names the one check to run. Wave 3's memory deletion is the orchestrator's, not the factory's.

---

## Tasks

### G1 (code, M) — `tasks.py`: plan parser, chains, status precedence

**dependsOn:** none

**Files:**
- Create: `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `tests/evidence/fixtures/plans/typed.md`, `tests/evidence/fixtures/plans/legacy.md`

**Interfaces:**
- Consumes nothing from other tasks. Reads (at run time, all optional): plan files, `docs/ledger/repos.toml` and `docs/ledger/plan-status.toml` (formats fixed in G3 and repeated below), `<repo>/docs/reviews/*.md`, `~/factory/runs/*/<KEY>.result`, the evidence store's `runs` stream via `evidence.read(store, "runs")` (import `evidence` lazily inside the function; the test helper puts `pkgs/evidence` on `sys.path`).
- Produces (G4 and G5 rely on these exact names):

```python
HEADING_RE = re.compile(r"^### (?P<key>[A-Za-z][A-Za-z0-9-]*) \((?P<kind>code|docs), (?P<size>XS|S|M|L)\) [—-] (?P<title>.+)$")
FIELD_RE = re.compile(r"^\*\*(?P<name>dependsOn|touches|acceptance|commit subject):\*\*\s*(?P<value>.*)$")
KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
CHAIN_RE = re.compile(r"^(?P<root>.*\d)(?P<suffix>[a-z])$")
STATES = ("landed", "approved", "rejected", "ran", "recorded", "ready", "blocked")
LEGACY_STATES = ("done", "superseded", "parked", "open")
REVIEW_RE = re.compile(r"^# Opus gate — seat run (?P<run>\S+), task (?P<key>\S+) — (?P<verdict>APPROVED|REJECTED)")

def parse_keys(value: str) -> list[str]        # strips "(...)" parentheticals, splits on commas/whitespace, keeps KEY_RE tokens, drops "none"
def parse_list(value: str) -> list[str]        # strips backticks, splits on commas/whitespace
def chain_root(key: str) -> str                # "E7b" -> "E7", "E7r" -> "E7", "A10T3" -> "A10T3", "E7" -> "E7"
def parse_plan(path) -> dict                   # {"file": basename, "path": str, "typed": bool, "tasks": [task, ...]}
   # task = {"key","kind","size","title","depends_on": [...],"touches": [...],"acceptance": [...],
   #         "commit_subject": str|None, "body": str, "plan": basename}
def load_repos(path) -> list[dict]             # [{"name","path","plans"}] ; missing file -> []
def load_plan_status(path) -> dict[tuple[str, str], dict]   # (repo, file) -> {"status","note"}
def landed_subjects(repo_path, run=None) -> set[str]        # git -C repo_path log --format=%s ; run seam like evidence.run
def read_reviews(repo_path) -> dict[str, dict]              # key -> {"verdict","run","file"} (first line matches REVIEW_RE)
def read_results(runs_dir) -> dict[tuple[str, str], dict]   # (repo_name, key) -> {"status","run","file"}; scan_repo filters to its repo and re-keys by key before derive_status
def read_recorded(store) -> dict[tuple[str, str], str]      # (plan_file, key) -> status from runs.jsonl tasks[]; scan_repo re-keys by key per plan before derive_status
def derive_status(task, landed, reviews, results, recorded, landed_keys) -> tuple[str, str]   # (state, detail); results: {key: info} for this repo, recorded: {key: status} for this plan
def scan_repo(repo, plan_status, runs_dir, store, run=None) -> dict
   # {"name","path","tasks": [task + "state","detail","chain": [keys]], "chains": {root: [keys]}, "legacy": [{"file","status","note"}], "untracked_plans": [files without typed headings and without a plan-status row]}
def build(root, runs_dir, store, run=None) -> dict          # {"generated": iso, "repos": [scan_repo(...)]}
```

Result attribution: a `.result` file's `workspace:` line names a clone; `<workspace>/.git/config` contains `url = /home/dalhaka/factory/base/<repo_name>`; `repo_name` is the basename of that url. A result whose workspace is gone or whose url does not end in `/base/<name>` is dropped (counted in `detail` nowhere; it is simply not evidence).

Status precedence (highest wins), where `landed` is the set of commit subjects on the repo's current branch and `landed_keys` is the set of chain roots any of whose members' `commit_subject` is in `landed`:
1. `landed` — `task["commit_subject"] in landed`, or any key in the task's chain has a review/result AND the chain root's `commit_subject` is landed (fix rounds keep the plan's subject).
2. `approved` / `rejected` — the newest review among the chain's keys (order: root, then suffix letters ascending) decides; detail = `"<KEY> by <run>"`.
3. `ran` — a result for any chain key; detail = `"<KEY> status=<status> run=<run>"`.
4. `recorded` — a `runs.jsonl` row for `(plan_file, key)`.
5. `ready` if every `depends_on` root is in `landed_keys`, else `blocked` (detail lists the missing roots).

- [ ] **Step 1: Fixtures.** `tests/evidence/fixtures/plans/typed.md`:

```markdown
# Typed fixture plan

## Waves

| wave | tasks |
|---|---|
| 1 | E1, E3 |

## Tasks

### E1 (code, M) — the store

**dependsOn:** none

Body text for E1.

**touches:** pkgs/evidence/evidence.py, flake.nix
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the store (test: evidence-unit, lint)`

### E3 (code, S) — attribution

**dependsOn:** none (integrates in the same wave as E1; prompt text only)

**touches:** tools/factory/dark-factory.js
**acceptance:** factory-unit, lint
**commit subject:** `factory: attribution (test: factory-unit, lint)`

### E5 (code, M) — tiles

**dependsOn:** E1, R4 (both edit `nixosModules/helm.nix`)

**touches:** nixosModules/helm.nix, `pkgs/helm/collect.py`
**acceptance:** helm-unit, lint
**commit subject:** `helm: tiles (test: helm-unit, lint)`

### E7 (code, S) — the integrator records

**dependsOn:** E1

**touches:** tools/factory/seat/factory-integrate
**acceptance:** unit, lint
**commit subject:** `factory: the integrator records (test: unit, lint)`

### D1 (docs, XS) — a note

**dependsOn:** E7

**touches:** docs/runbooks/x.md
**commit subject:** `docs: a note (test: lint)`
```

`tests/evidence/fixtures/plans/legacy.md`:

```markdown
# Legacy fixture plan

### Task 1: bootstrap

- [ ] Step 1: do the thing

### Task 2: docs

- [ ] Step 1: write it
```

- [ ] **Step 2: Failing tests** — `tests/evidence/test_tasks.py`:

```python
"""Derived task graph tests (plan 2026-09-05-session-context, G1)."""

import importlib.util
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
FIXTURES = HERE.parent / "fixtures" / "plans"


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "tasks.py",
        pathlib.Path("pkgs/evidence/tasks.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("tasks", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tasks"] = mod
    spec.loader.exec_module(mod)
    return mod, src


tk, SRC = load()


def test_parse_typed_plan_reads_every_field():
    plan = tk.parse_plan(FIXTURES / "typed.md")
    assert plan["typed"] is True and plan["file"] == "typed.md"
    by = {t["key"]: t for t in plan["tasks"]}
    assert list(by) == ["E1", "E3", "E5", "E7", "D1"]
    assert (by["E1"]["kind"], by["E1"]["size"], by["E1"]["title"]) == ("code", "M", "the store")
    assert by["E1"]["depends_on"] == [] and by["E3"]["depends_on"] == []
    assert by["E5"]["depends_on"] == ["E1", "R4"]  # parenthetical stripped
    assert by["E5"]["touches"] == ["nixosModules/helm.nix", "pkgs/helm/collect.py"]  # backticks stripped
    assert by["E1"]["acceptance"] == ["evidence-unit", "lint"]
    assert by["E1"]["commit_subject"] == "evidence: the store (test: evidence-unit, lint)"
    assert by["D1"]["acceptance"] == [] and by["D1"]["kind"] == "docs"
    assert "Body text for E1." in by["E1"]["body"] and "attribution" not in by["E1"]["body"]


def test_parse_legacy_plan_has_no_tasks():
    plan = tk.parse_plan(FIXTURES / "legacy.md")
    assert plan["typed"] is False and plan["tasks"] == []


def test_chain_root():
    assert tk.chain_root("E7b") == "E7"
    assert tk.chain_root("E7r") == "E7"
    assert tk.chain_root("E7") == "E7"
    assert tk.chain_root("A10T3") == "A10T3"
    assert tk.chain_root("W2-N10c") == "W2-N10"


def test_parse_keys_and_list():
    assert tk.parse_keys("E1, R4 (both edit `flake.nix`)") == ["E1", "R4"]
    assert tk.parse_keys("none (integrates in the same wave)") == []
    assert tk.parse_list("`a/b.py`, c/d.nix") == ["a/b.py", "c/d.nix"]


def write_review(repo, name, first_line):
    d = repo / "docs" / "reviews"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(first_line + "\n\nbody\n")


def write_result(runs_dir, run, key, status, workspace):
    d = runs_dir / run
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{key}.result").write_text(
        f"FACTORY-RESULT status={status}\nFACTORY-CHECKS lint=pass\n\nrun: {run}\nkey: {key}\nworkspace: {workspace}\nbranch: task/{key}\n"
    )


def make_workspace(tmp_path, name, repo_name):
    ws = tmp_path / "ws" / name
    (ws / ".git").mkdir(parents=True)
    (ws / ".git" / "config").write_text(f'[remote "origin"]\n\turl = /home/dalhaka/factory/base/{repo_name}\n')
    return ws


def test_read_results_attributes_by_workspace_origin(tmp_path):
    runs = tmp_path / "runs"
    write_result(runs, "ev3", "E7b", "done", make_workspace(tmp_path, "ev3-E7b", "nixos-agent-env"))
    write_result(runs, "cw1", "W1", "done", make_workspace(tmp_path, "cw1-W1", "media"))
    write_result(runs, "old", "Z9", "done", tmp_path / "gone")  # workspace deleted -> not evidence
    res = tk.read_results(runs)
    assert res[("nixos-agent-env", "E7b")]["status"] == "done"
    assert res[("media", "W1")]["run"] == "cw1"
    assert not any(k[1] == "Z9" for k in res)


def test_read_reviews_matches_only_the_gate_header(tmp_path):
    write_review(tmp_path, "a.md", "# Opus gate — seat run ev3, task E8 — APPROVED")
    write_review(tmp_path, "b.md", "# Opus gate — seat run ev2, task E7b — REJECTED")
    write_review(tmp_path, "c.md", "# dsh + dark factory: 24-hour review")
    rv = tk.read_reviews(tmp_path)
    assert rv["E8"]["verdict"] == "APPROVED" and rv["E7b"]["verdict"] == "REJECTED" and len(rv) == 2


def fake_git(subjects):
    def run(argv, timeout=20.0):
        class R:
            returncode = 0
            stdout = "\n".join(subjects) + "\n"
            stderr = ""

        return R()

    return run


def test_derive_status_precedence(tmp_path):
    plan = tk.parse_plan(FIXTURES / "typed.md")
    by = {t["key"]: t for t in plan["tasks"]}
    landed = {"evidence: the store (test: evidence-unit, lint)"}
    reviews = {"E7": {"verdict": "REJECTED", "run": "ev2", "file": "x"}, "E7b": {"verdict": "REJECTED", "run": "ev2", "file": "y"}, "E7r": {"verdict": "APPROVED", "run": "ev2", "file": "z"}}
    results = {"E3": {"status": "done", "run": "ev1", "file": "r"}}  # already filtered to this repo, keyed by task key
    recorded = {"D1": "done"}  # already filtered to this plan
    landed_keys = {"E1"}
    assert tk.derive_status(by["E1"], landed, reviews, results, recorded, landed_keys)[0] == "landed"
    st, detail = tk.derive_status(by["E7"], landed, reviews, results, recorded, landed_keys)
    assert st == "approved" and "E7r" in detail  # newest chain member decides
    assert tk.derive_status(by["E3"], landed, reviews, results, recorded, landed_keys)[0] == "ran"
    assert tk.derive_status(by["D1"], landed, reviews, results, recorded, landed_keys)[0] == "recorded"
    st, detail = tk.derive_status(by["E5"], landed, reviews, results, recorded, landed_keys)
    assert st == "blocked" and "R4" in detail and "E1" not in detail


def test_derive_status_ready_when_deps_landed():
    plan = tk.parse_plan(FIXTURES / "typed.md")
    by = {t["key"]: t for t in plan["tasks"]}
    assert tk.derive_status(by["E7"], set(), {}, {}, {}, {"E1"})[0] == "ready"


def test_scan_repo_and_build(tmp_path):
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "typed.md").write_text((FIXTURES / "typed.md").read_text())
    (plans / "legacy.md").write_text((FIXTURES / "legacy.md").read_text())
    (plans / "orphan.md").write_text("# no typed headings, no status row\n")
    write_review(repo, "r.md", "# Opus gate — seat run ev1, task E3 — APPROVED")
    status = {("nixos-agent-env", "legacy.md"): {"status": "done", "note": "phase 1"}}
    g = tk.scan_repo({"name": "nixos-agent-env", "path": str(repo), "plans": "docs/superpowers/plans/*.md"}, status, tmp_path / "no-runs", str(tmp_path / "no-store"), run=fake_git(["evidence: the store (test: evidence-unit, lint)"]))
    states = {t["key"]: t["state"] for t in g["tasks"]}
    assert states == {"E1": "landed", "E3": "approved", "E5": "blocked", "E7": "ready", "D1": "blocked"}
    assert g["legacy"] == [{"file": "legacy.md", "status": "done", "note": "phase 1"}]
    assert g["untracked_plans"] == ["orphan.md"]
    assert g["chains"]["E1"] == ["E1"]


def test_load_repos_and_plan_status(tmp_path):
    (tmp_path / "repos.toml").write_text('[[repo]]\nname = "nixos-agent-env"\npath = "~/nixos-agent-env"\n\n[[repo]]\nname = "media"\npath = "~/flakes/media"\nplans = "docs/superpowers/plans/*.md"\n')
    repos = tk.load_repos(tmp_path / "repos.toml")
    assert [r["name"] for r in repos] == ["nixos-agent-env", "media"]
    assert repos[0]["plans"] == "docs/superpowers/plans/*.md" and repos[0]["path"] == os.path.expanduser("~/nixos-agent-env")
    (tmp_path / "status.toml").write_text('[[plan]]\nrepo = "media"\nfile = "2026-09-02-media-flake.md"\nstatus = "superseded"\nnote = "by nix-native"\n')
    ps = tk.load_plan_status(tmp_path / "status.toml")
    assert ps[("media", "2026-09-02-media-flake.md")] == {"status": "superseded", "note": "by nix-native"}
    assert tk.load_repos(tmp_path / "missing.toml") == []


def test_landed_subjects_uses_git(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x"}
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True, env=env)
    (repo / "f").write_text("x")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "evidence: the store (test: evidence-unit, lint)"], check=True, env=env)
    assert "evidence: the store (test: evidence-unit, lint)" in tk.landed_subjects(str(repo))
    assert tk.landed_subjects(str(tmp_path / "not-a-repo")) == set()
```

- [ ] **Step 3: Red** — `git add tests/evidence pkgs/evidence` (fixtures are new files), then `nix develop -c pytest tests/evidence/test_tasks.py -q` → `StopIteration` from `load()` (no `tasks.py` yet). Record the line.
- [ ] **Step 4: Implement `pkgs/evidence/tasks.py`.** Module docstring: `"""Derived task graph: plans are the nodes and edges, status is a derivation (plan 2026-09-05-session-context, G1/G4)."""`. Skeleton (fill every function; keep stdlib only):

```python
from __future__ import annotations

import datetime
import glob
import os
import pathlib
import re
import subprocess
import tomllib

HEADING_RE = ...  # as in Interfaces
FIELD_RE = ...
KEY_RE = ...
CHAIN_RE = ...
REVIEW_RE = ...
STATES = (...)
LEGACY_STATES = (...)
DEFAULT_RUNS_DIR = os.path.expanduser("~/factory/runs")
PLANS_GLOB = "docs/superpowers/plans/*.md"


def run(argv, timeout=20.0):
    """The one subprocess seam (tests pass a fake)."""
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)


def chain_root(key):
    m = CHAIN_RE.match(key)
    return m.group("root") if m else key


def parse_keys(value):
    value = re.sub(r"\([^)]*\)", " ", value)
    out = []
    for tok in re.split(r"[,\s]+", value.replace("`", "")):
        if tok and tok.lower() != "none" and KEY_RE.match(tok):
            out.append(tok)
    return out


def parse_list(value):
    return [t for t in re.split(r"[,\s]+", value.replace("`", "").strip()) if t]


def parse_plan(path):
    path = pathlib.Path(path)
    tasks, cur = [], None
    for line in path.read_text().splitlines():
        if line.startswith("## ") or (line.startswith("### ") and not HEADING_RE.match(line)):
            cur = None  # a section that is not a typed task ends the current one
        m = HEADING_RE.match(line)
        if m:
            cur = {"key": m["key"], "kind": m["kind"], "size": m["size"], "title": m["title"].strip(), "depends_on": [], "touches": [], "acceptance": [], "commit_subject": None, "body": "", "plan": path.name}
            tasks.append(cur)
            continue
        if cur is None:
            continue
        f = FIELD_RE.match(line)
        if f:
            name, value = f["name"], f["value"].strip()
            if name == "dependsOn":
                cur["depends_on"] = parse_keys(value)
            elif name == "touches":
                cur["touches"] = parse_list(value)
            elif name == "acceptance":
                cur["acceptance"] = parse_list(value)
            else:
                cur["commit_subject"] = value.strip("`").strip()
            continue
        cur["body"] += line + "\n"
    return {"file": path.name, "path": str(path), "typed": bool(tasks), "tasks": tasks}
```

`load_repos`: `tomllib.loads` → `[{"name": r["name"], "path": os.path.expanduser(r["path"]), "plans": r.get("plans", PLANS_GLOB)} ...]`; missing file → `[]`. `load_plan_status`: `{(p["repo"], p["file"]): {"status": p["status"], "note": p.get("note", "")}}`, missing file → `{}`. `landed_subjects`: `r = (run or globals()["run"])(["git", "-C", repo_path, "log", "--format=%s"], timeout=30)`; on `returncode != 0` or any exception return `set()`; else the set of non-empty lines. `read_reviews`: for each `docs/reviews/*.md`, read the first line, match `REVIEW_RE`, later files (sorted by name) overwrite earlier for the same key. `read_results`: `glob(runs_dir/*/*.result)`; parse `FACTORY-RESULT status=(\S+)`, `run:`, `key:`, `workspace:`; read `<workspace>/.git/config`, regex `url = (.+)`; `m = re.search(r"/base/([^/\s]+)$", url)`; skip when missing; key `(m.group(1), key)`; newer run directories (sorted by mtime) overwrite. `read_recorded`: `import evidence` lazily; `evidence.read(store, "runs")` inside `try/except Exception: return {}`; for each row, for each `t in row.get("tasks", [])` → `(os.path.basename(row.get("plan", "")), t["key"]) = t.get("status", "recorded")`. `derive_status` per the precedence above; chain members = `[k for k in set(reviews) | {k for _, k in results} if chain_root(k) == task["key"]] + [task["key"]]`, ordered root first then suffix letter ascending. `scan_repo`: glob plans; typed plans → tasks; untyped → legacy row from `plan_status` or `untracked_plans`; then `landed = landed_subjects(...)`, `reviews = read_reviews(...)`, `results = {k: v for (name, k), v in read_results(runs_dir).items() if name == repo["name"]}`, `recorded_all = read_recorded(store)` re-keyed per task as `{k: v for (f, k), v in recorded_all.items() if f == task["plan"]}`; first pass computes `landed_keys` (roots whose subject is landed), second pass derives each state; `chains[root] = ordered member keys`. `build`: `{"generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "repos": [...]}` reading `repos.toml` and `plan-status.toml` under `root/docs/ledger/`.

- [ ] **Step 5: Green** — `nix develop -c ruff format pkgs/evidence tests/evidence && nix develop -c ruff check pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q` (all of `tests/evidence`, so E1/E2's tests still pass); `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`.
- [ ] **Step 6: Real data smoke (report, do not fix here)** — `nix develop -c python3 -c 'import sys; sys.path.insert(0,"pkgs/evidence"); import tasks, json; g=tasks.scan_repo({"name":"nixos-agent-env","path":".","plans":"docs/superpowers/plans/*.md"}, {}, tasks.DEFAULT_RUNS_DIR, "/var/lib/evidence"); print(json.dumps({t["key"]:t["state"] for t in g["tasks"]}, indent=0)); print(len(g["untracked_plans"]), "untracked")'`. Expected: E1–E9 and R1–R10 mostly `landed`/`approved`, `24 untracked` (no plan-status file yet — G3 adds it; 27 plan files, 3 typed). Put the printed map in FACTORY-NOTES.
- [ ] **Step 7: Commit** (subject below; message file in scratch; `nix develop -c git commit -F`).

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, tests/evidence/fixtures/plans/typed.md, tests/evidence/fixtures/plans/legacy.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: tasks.py parses typed plans, chains fix rounds and derives task status from landed subjects, gate reviews, seat results and run records (test: evidence-unit, lint)`

### G4 (code, M) — `tasks.py`: waves, conflicts, seat and factory outputs, `check`, the brief, the CLI

**dependsOn:** G1

**Files:**
- Modify: `pkgs/evidence/tasks.py` (append), `tests/evidence/test_tasks.py` (append)
- Create: `tests/evidence/fixtures/plans/second.md`

**Interfaces:**
- Consumes G1's `build`, `scan_repo`, `parse_plan`, `chain_root`, `STATES`.
- Produces (G5 and G8 rely on these names):

```python
def touches_overlap(a: str, b: str) -> bool          # equal, fnmatch either way, or directory prefix either way
def open_tasks(repo_graph) -> list[dict]             # state in ("ready", "blocked"): not yet dispatched; approved/rejected/ran/recorded tasks are in flight and never re-scheduled
def waves(repo_graph, plan: str | None = None) -> list[list[str]]   # Kahn; keys sorted inside a wave; deps outside the filter count as satisfied only if landed
def seat_groups(repo_graph, wave: list[str]) -> list[str]           # ['"E1 R4 R5"', '"E3"']: overlapping touches merge into one group, key order
def factory_args(repo_graph, plan: str) -> list[dict]               # [{"key","title","kind","checks","spec","dependsOn","touches"}] for open tasks of that plan
def conflicts(repo_graph) -> list[dict]              # [{"a","plan_a","b","plan_b","path_a","path_b"}] open (ready/blocked) tasks in different plans with overlapping touches
def check(graph) -> list[str]                        # error strings; empty = ok
def render_brief(graph, claims_rows: list[dict] | None) -> str
def main(argv=None) -> int                           # argparse: brief | json | waves --repo NAME [--plan FILE] [--factory-args] | conflicts [--repo NAME] | check
```

`check` rules (each message starts with `tasks: `): a `depends_on` key whose chain root is not a task in any typed plan of the same repo (`tasks: nixos-agent-env/E5 dependsOn R4: unknown key`); a cycle (`tasks: cycle in nixos-agent-env: A -> B -> A`); a code task with empty acceptance (`tasks: nixos-agent-env/E1 (code) has no acceptance`); the same key in two typed plans of one repo (`tasks: nixos-agent-env/T1 defined in a.md and b.md`). Board drift is added in G8, not here.

`render_brief` (markdown, ≤ 40 lines for five repos):

```
# Task brief (generated 2026-09-05T18:00:00Z)

| repo | landed | approved | rejected | ran | recorded | ready | blocked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 12 | 3 | 1 | 0 | 0 | 2 | 4 | 1 | 0 |

**Next wave** — nixos-agent-env: E6 E8 (plan 2026-09-05-evidence-store.md) · media: W3
**Rejected, fix round owed:** nixos-agent-env/R3 (R3b ran, no gate yet)
**Operator owns:** o4-framing-test (review by 2026-09-12) · d5-activity-export (…)
**Untracked plans (no typed headings, no plan-status row):** none
```

"Operator owns" comes from `claims_rows` where `status == "gap"` and `owner == "operator"`; `None` → the line reads `(claims file not read)`.

- [ ] **Step 1: Fixture** `tests/evidence/fixtures/plans/second.md`:

```markdown
# Second fixture plan (a different plan in the same repo)

### X1 (code, S) — edits the helm module too

**dependsOn:** none

**touches:** nixosModules/helm.nix
**acceptance:** helm-unit
**commit subject:** `helm: x1 (test: helm-unit)`

### X2 (code, S) — cycle a

**dependsOn:** X3

**touches:** a.py
**acceptance:** unit
**commit subject:** `x: a (test: unit)`

### X3 (code, S) — cycle b

**dependsOn:** X2

**touches:** b.py
**acceptance:** unit
**commit subject:** `x: b (test: unit)`
```

- [ ] **Step 2: Failing tests** (append to `tests/evidence/test_tasks.py`):

```python
import json


def repo_with(tmp_path, files, landed=(), reviews=()):
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    for f in files:
        (plans / f).write_text((FIXTURES / f).read_text())
    for name, line in reviews:
        write_review(repo, name, line)
    return tk.scan_repo({"name": "nixos-agent-env", "path": str(repo), "plans": "docs/superpowers/plans/*.md"}, {}, tmp_path / "no-runs", str(tmp_path / "no-store"), run=fake_git(list(landed)))


def test_touches_overlap():
    assert tk.touches_overlap("flake.nix", "flake.nix")
    assert tk.touches_overlap("pkgs/x/*.sh", "pkgs/x/a.sh")
    assert tk.touches_overlap("pkgs/x/a.sh", "pkgs/x/*.sh")
    assert tk.touches_overlap("docs/board", "docs/board/log.md")
    assert not tk.touches_overlap("pkgs/x/a.sh", "pkgs/y/a.sh")


def test_waves_follow_dependencies_and_skip_landed(tmp_path):
    g = repo_with(tmp_path, ["typed.md"], landed=["evidence: the store (test: evidence-unit, lint)"])
    # E1 landed; E5 needs R4 (unknown -> stays blocked, never scheduled); E7 ready; D1 after E7; E3 ready
    assert tk.waves(g, plan="typed.md") == [["E3", "E7"], ["D1"]]


def test_seat_groups_merge_overlapping_touches(tmp_path):
    g = repo_with(tmp_path, ["typed.md", "second.md"], landed=["evidence: the store (test: evidence-unit, lint)"])
    by = {t["key"]: t for t in g["tasks"]}
    by["E5"]["depends_on"] = ["E1"]  # make E5 ready for this test
    by["E5"]["state"] = "ready"
    groups = tk.seat_groups(g, ["E3", "E5", "X1"])
    assert groups == ['"E3"', '"E5 X1"']  # E5 and X1 both touch nixosModules/helm.nix


def test_factory_args_shape(tmp_path):
    g = repo_with(tmp_path, ["typed.md"])
    args = tk.factory_args(g, "typed.md")
    e1 = next(a for a in args if a["key"] == "E1")
    assert e1 == {"key": "E1", "title": "the store", "kind": "code", "checks": ["evidence-unit", "lint"], "spec": e1["spec"], "dependsOn": [], "touches": ["pkgs/evidence/evidence.py", "flake.nix"]}
    assert "Body text for E1." in e1["spec"]
    assert json.dumps(args)  # serialisable


def test_conflicts_across_plans(tmp_path):
    g = repo_with(tmp_path, ["typed.md", "second.md"])
    c = tk.conflicts(g)
    assert {"a": "E5", "plan_a": "typed.md", "b": "X1", "plan_b": "second.md", "path_a": "nixosModules/helm.nix", "path_b": "nixosModules/helm.nix"} in c
    assert not any(x["a"] == "X2" or x["b"] == "X2" for x in c)  # a.py/b.py do not overlap


def test_check_reports_unknown_dep_cycle_and_missing_acceptance(tmp_path):
    g = repo_with(tmp_path, ["typed.md", "second.md"])
    graph = {"generated": "t", "repos": [g]}
    errs = tk.check(graph)
    assert "tasks: nixos-agent-env/E5 dependsOn R4: unknown key" in errs
    assert any(e.startswith("tasks: cycle in nixos-agent-env: ") and "X2" in e and "X3" in e for e in errs)
    assert not any("no acceptance" in e for e in errs)  # D1 is docs; every code task names a check
    next(t for t in g["tasks"] if t["key"] == "E1")["acceptance"] = []  # plans glob in name order: second.md before typed.md
    assert "tasks: nixos-agent-env/E1 (code) has no acceptance" in tk.check(graph)


def test_check_reports_duplicate_key(tmp_path):
    g = repo_with(tmp_path, ["typed.md"])
    dup = dict(next(t for t in g["tasks"] if t["key"] == "E1"), plan="other.md")
    g["tasks"].append(dup)
    assert "tasks: nixos-agent-env/E1 defined in typed.md and other.md" in tk.check({"generated": "t", "repos": [g]})


def test_brief_lists_counts_next_wave_and_operator_items(tmp_path):
    g = repo_with(tmp_path, ["typed.md"], landed=["evidence: the store (test: evidence-unit, lint)"], reviews=[("r.md", "# Opus gate — seat run ev1, task E3 — REJECTED")])
    claims = [{"id": "o4-framing-test", "status": "gap", "owner": "operator", "review_by": "2026-09-12"}, {"id": "x", "status": "gap", "owner": "orchestrator"}]
    md = tk.render_brief({"generated": "2026-09-05T18:00:00Z", "repos": [g]}, claims)
    assert md.startswith("# Task brief (generated 2026-09-05T18:00:00Z)")
    assert "| nixos-agent-env | 1 | 0 | 1 |" in md
    assert "**Next wave** — nixos-agent-env: E7" in md
    assert "**Rejected, fix round owed:** nixos-agent-env/E3" in md
    assert "o4-framing-test" in md and "orchestrator" not in md
    assert len(md.splitlines()) <= 40


def test_cli_check_and_json(tmp_path):
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "second.md").write_text((FIXTURES / "second.md").read_text())
    (root / "docs" / "ledger" / "repos.toml").write_text(f'[[repo]]\nname = "nixos-agent-env"\npath = "{repo}"\n')
    r = subprocess.run([sys.executable, str(SRC), "--root", str(root), "--runs-dir", str(tmp_path / "none"), "--store", str(tmp_path / "none"), "check"], capture_output=True, text=True, check=False)
    assert r.returncode == 1 and "cycle" in r.stderr
    r = subprocess.run([sys.executable, str(SRC), "--root", str(root), "--runs-dir", str(tmp_path / "none"), "--store", str(tmp_path / "none"), "json"], capture_output=True, text=True, check=False)
    assert r.returncode == 0 and json.loads(r.stdout)["repos"][0]["name"] == "nixos-agent-env"
    r = subprocess.run([sys.executable, str(SRC), "--root", str(root), "--runs-dir", str(tmp_path / "none"), "--store", str(tmp_path / "none"), "waves", "--repo", "nixos-agent-env", "--plan", "second.md"], capture_output=True, text=True, check=False)
    assert r.returncode == 0 and r.stdout.splitlines()[0] == '"X1"'
```

- [ ] **Step 3: Red** — `nix develop -c pytest tests/evidence/test_tasks.py -q` → `AttributeError: module 'tasks' has no attribute 'touches_overlap'` (and friends).
- [ ] **Step 4: Implement** (append to `tasks.py`):

```python
import fnmatch


def touches_overlap(a, b):
    a, b = a.rstrip("/"), b.rstrip("/")
    return a == b or fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a) or a.startswith(b + "/") or b.startswith(a + "/")


def open_tasks(repo_graph):
    return [t for t in repo_graph["tasks"] if t["state"] in ("ready", "blocked")]


def waves(repo_graph, plan=None):
    landed = {chain_root(t["key"]) for t in repo_graph["tasks"] if t["state"] == "landed"}
    nodes = {t["key"]: t for t in open_tasks(repo_graph) if plan is None or t["plan"] == plan}
    known = {chain_root(k) for k in repo_graph["chains"]} | set(nodes)
    deps = {}
    for k, t in nodes.items():
        deps[k] = {chain_root(d) for d in t["depends_on"] if chain_root(d) not in landed}
    out, done = [], set()
    while True:
        ready = sorted(k for k in nodes if k not in done and all(d in done or d not in nodes for d in deps[k]) and all(d in nodes or d in landed for d in deps[k]))
        if not ready:
            break
        out.append(ready)
        done.update(ready)
    return out
```

(A task whose dependency is unknown or blocked outside the filter never becomes ready; `check` reports the unknown key.) `seat_groups`: union-find over the wave's keys joined when any pair of their `touches` overlap; each group's keys sorted; render `'"' + " ".join(keys) + '"'`; groups sorted by first key. `factory_args`: for open tasks of `plan`: `{"key","title","kind","checks": acceptance,"spec": body.strip(),"dependsOn": depends_on,"touches": touches}`. `conflicts`: all pairs of open tasks with different `plan`, any overlapping touch pair → one row per overlapping pair. `check`: iterate repos; keys = set of task keys; for each dep, `chain_root(dep) not in keys` → unknown; DFS cycle detection over `depends_on` edges restricted to known keys, message lists the cycle path; code tasks with `acceptance == []`; duplicate keys across plans. `render_brief`: build the table from `STATES` counts per repo plus `legacy open` (rows with `status == "open"`) and `untracked` (`len(untracked_plans)`); "Next wave" = first wave per repo (skip repos with none); "Rejected, fix round owed" = tasks with state `rejected`; "Operator owns" from claims; "Untracked plans" listing `repo/file` or `none`. `main`: `--root` (default `.`), `--repos` (default `<root>/docs/ledger/repos.toml`), `--plan-status` (default `<root>/docs/ledger/plan-status.toml`), `--runs-dir` (default `DEFAULT_RUNS_DIR`), `--store` (default `os.environ.get("EVIDENCE_STORE", "/var/lib/evidence")`), `--claims` (default `<root>/docs/ledger/claims.toml`; read with `tomllib` → `data.get("claim", [])`, `None` when missing); subcommands as in Interfaces; `check` prints errors to stderr and returns 1 when any; `waves` prints one seat-group line per wave (`--factory-args` prints the JSON array instead); `conflicts` prints one line per row `repo: A (plan_a) × B (plan_b): path_a ~ path_b`, and `none`. `if __name__ == "__main__": raise SystemExit(main())`.

- [ ] **Step 5: Green** — ruff format/check; `nix develop -c pytest tests/evidence -q`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`.
- [ ] **Step 6: Real data** — `nix develop -c python3 pkgs/evidence/tasks.py --root . check; echo exit=$?` and `nix develop -c python3 pkgs/evidence/tasks.py --root . brief`. Both must run without a traceback (repos.toml may still be absent if G3 has not integrated: then the graph has zero repos and `brief` prints an empty table — that is the expected output, not a failure). Paste the brief into FACTORY-NOTES. If `check` reports errors on the real plans, list them verbatim in the notes; do not loosen the parser to hide them.
- [ ] **Step 7: Commit.**

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, tests/evidence/fixtures/plans/second.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: tasks.py schedules Kahn waves, merges overlapping touches into seat groups, emits dark-factory task lists, finds cross-plan conflicts, checks the graph and renders the brief (test: evidence-unit, lint)`

### G2 (code, S) — `repomap.py` and the generated `docs/MAP.md`

**dependsOn:** none

**Files:**
- Create: `pkgs/evidence/repomap.py`, `tests/evidence/test_repomap.py`, `docs/MAP.md` (generated output, committed)

**Interfaces:**
- Consumes nothing. Reads the repo tree and `flake.nix` text.
- Produces (G5 wires `check` into the hook and asserts the check list in `lint`; G7 points CLAUDE.md at `docs/MAP.md`):

```python
HEADER = "# Repo map — generated by pkgs/evidence/repomap.py, do not edit (regenerate: python3 pkgs/evidence/repomap.py write)"
def first_comment(path) -> str                 # first "# text" line in the first 12 lines that is not a shebang; for .py the first docstring line; else "(no description)"
def flake_check_names(flake_text: str) -> list[str]   # names at 8-space indent between "      checks.${system} = {" and the first "      };"
def build_map(root) -> dict                    # {"modules","packages","checks","tests","hosts","tools"}; each list of {"path","desc"} (checks: list[str]; tests: {"path","files"})
def render_map(m) -> str                       # markdown starting with HEADER
def main(argv=None) -> int                     # write | check | print ; --root .
```

Sections and sources: **modules** = `nixosModules/*.nix`; **packages** = `pkgs/*/` (desc = first_comment of the first of `<name>.sh`, `<name>.py`, `default.nix`, or any `*.py`/`*.sh`, sorted); **checks** = `flake_check_names`; **tests** = each directory under `tests/` (and `tests/*.nix` files) with a file count; **hosts** = `hosts/*/*.nix`; **tools** = `tools/*` (files) and `tools/*/` (directories one level deep; desc from that directory's own `README.md` first heading if present, else `first_comment` of the first `*.sh`/`*.py`/`*.js`/extensionless script found recursively, sorted by path). Paths are repo-relative; lists sorted by path.

- [ ] **Step 1: Failing tests** — `tests/evidence/test_repomap.py`:

```python
"""Repo map tests (plan 2026-09-05-session-context, G2)."""

import importlib.util
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()


def load():
    candidates = [HERE.parents[2] / "pkgs" / "evidence" / "repomap.py", pathlib.Path("pkgs/evidence/repomap.py")]
    src = next(p for p in candidates if p.exists())
    spec = importlib.util.spec_from_file_location("repomap", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, src


rm, SRC = load()

FLAKE = """{
  outputs = { self, nixpkgs }:
    let x = 1; in {
      packages.${system} = { a = 1; };
      checks.${system} = {
        # a comment at eight spaces
        host-core = 1;
        lint =
          pkgs.runCommand "lint" { } "touch $out";
        helm-control-assertion-negative-profiles = 2;
      };
      other = 3;
    };
}
"""


def make_repo(tmp_path):
    (tmp_path / "flake.nix").write_text(FLAKE)
    (tmp_path / "nixosModules").mkdir()
    (tmp_path / "nixosModules" / "helm.nix").write_text("# Helm: the status dashboard module.\n{ config, ... }: { }\n")
    (tmp_path / "nixosModules" / "bare.nix").write_text("{ }\n")
    (tmp_path / "pkgs" / "basket").mkdir(parents=True)
    (tmp_path / "pkgs" / "basket" / "basket.sh").write_text("#!/usr/bin/env bash\n# basket: pack, encrypt, mount, teardown.\nset -e\n")
    (tmp_path / "pkgs" / "evidence").mkdir()
    (tmp_path / "pkgs" / "evidence" / "evidence.py").write_text('"""The evidence store CLI."""\nimport sys\n')
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "a.bats").write_text("")
    (tmp_path / "tests" / "unit" / "b.bats").write_text("")
    (tmp_path / "hosts" / "core").mkdir(parents=True)
    (tmp_path / "hosts" / "core" / "default.nix").write_text("# core: one file per concern.\n{ }\n")
    (tmp_path / "tools" / "factory" / "seat").mkdir(parents=True)
    (tmp_path / "tools" / "factory" / "seat" / "README.md").write_text("# The seat driver\n\ntext\n")
    (tmp_path / "tools" / "factory" / "dark-factory.js").write_text("// Dark factory — reusable Workflow script.\n")
    return tmp_path


def test_flake_check_names_reads_the_checks_block_only():
    assert rm.flake_check_names(FLAKE) == ["host-core", "lint", "helm-control-assertion-negative-profiles"]


def test_first_comment_handles_shebang_docstring_and_bare(tmp_path):
    make_repo(tmp_path)
    assert rm.first_comment(tmp_path / "pkgs" / "basket" / "basket.sh") == "basket: pack, encrypt, mount, teardown."
    assert rm.first_comment(tmp_path / "pkgs" / "evidence" / "evidence.py") == "The evidence store CLI."
    assert rm.first_comment(tmp_path / "nixosModules" / "bare.nix") == "(no description)"


def test_build_and_render(tmp_path):
    m = rm.build_map(make_repo(tmp_path))
    assert m["checks"] == ["host-core", "lint", "helm-control-assertion-negative-profiles"]
    assert {"path": "nixosModules/helm.nix", "desc": "Helm: the status dashboard module."} in m["modules"]
    assert {"path": "pkgs/basket", "desc": "basket: pack, encrypt, mount, teardown."} in m["packages"]
    assert {"path": "tests/unit", "files": 2} in m["tests"]
    assert {"path": "hosts/core/default.nix", "desc": "core: one file per concern."} in m["hosts"]
    assert {"path": "tools/factory", "desc": "Dark factory — reusable Workflow script."} in m["tools"]  # no README at tools/factory: first script recursively, sorted
    md = rm.render_map(m)
    assert md.startswith(rm.HEADER)
    assert "`nixosModules/helm.nix` — Helm: the status dashboard module." in md
    assert "## Checks" in md and "- host-core\n" in md


def test_cli_write_then_check_then_drift(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    r = subprocess.run([sys.executable, str(SRC), "--root", str(tmp_path), "write"], capture_output=True, text=True, check=False)
    assert r.returncode == 0 and (tmp_path / "docs" / "MAP.md").read_text().startswith(rm.HEADER)
    r = subprocess.run([sys.executable, str(SRC), "--root", str(tmp_path), "check"], capture_output=True, text=True, check=False)
    assert r.returncode == 0
    (tmp_path / "docs" / "MAP.md").write_text((tmp_path / "docs" / "MAP.md").read_text() + "stale\n")
    r = subprocess.run([sys.executable, str(SRC), "--root", str(tmp_path), "check"], capture_output=True, text=True, check=False)
    assert r.returncode == 1 and "docs/MAP.md is stale" in r.stderr
```

- [ ] **Step 2: Red** — `git add tests/evidence/test_repomap.py`; `nix develop -c pytest tests/evidence/test_repomap.py -q` → `StopIteration` from `load()`.
- [ ] **Step 3: Implement `pkgs/evidence/repomap.py`.** `flake_check_names`: iterate lines; start at the first line equal (after `rstrip`) to `      checks.${system} = {`; stop at the first line `      };`; collect `re.match(r"^ {8}([a-z][a-z0-9-]*) =", line)`. `first_comment`: read up to 12 lines; if the first line starts with `"""` return its text after the quotes up to a closing `"""` or end of line; else the first line matching `^\s*(#|//)\s*(.+)$` that does not start with `#!`; return group 2 stripped; else `"(no description)"`. `build_map` as specified; `render_map`:

```
{HEADER}

Paths are repo-relative. Descriptions are each file's first comment line.

## NixOS modules
- `nixosModules/helm.nix` — Helm: the status dashboard module.

## Packages
- `pkgs/basket` — basket: pack, encrypt, mount, teardown.

## Checks (nix build .#checks.x86_64-linux.<name>)
- host-core
- lint

## Tests
- `tests/unit` — 2 files

## Hosts
- `hosts/core/default.nix` — core: one file per concern.

## Tools
- `tools/factory` — The seat driver
```

`main`: `write` writes `<root>/docs/MAP.md`; `check` compares the rendered text to the file and on difference prints `repomap: docs/MAP.md is stale — run: python3 pkgs/evidence/repomap.py write` to stderr and returns 1 (missing file is also stale); `print` prints to stdout.

- [ ] **Step 4: Green** — ruff format/check; `nix develop -c pytest tests/evidence -q`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`.
- [ ] **Step 5: Generate the real map** — `nix develop -c python3 pkgs/evidence/repomap.py --root . write`; `git add docs/MAP.md`; confirm `grep -c '^- ' docs/MAP.md` ≥ 60 and that the Checks section has exactly 38 lines (`awk '/^## Checks/{s=1;next} /^## /{s=0} s&&/^- /' docs/MAP.md | wc -l` → 38, matching CLAUDE.md's check list today). `python3 pkgs/evidence/repomap.py --root . check` → exit 0.
- [ ] **Step 6: Commit.**

**touches:** pkgs/evidence/repomap.py, tests/evidence/test_repomap.py, docs/MAP.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: repomap.py generates docs/MAP.md (modules, packages, checks, tests, hosts, tools) and refuses a stale map (test: evidence-unit, lint)`

### G3 (docs, XS) — `repos.toml` and `plan-status.toml`

**dependsOn:** none

**Files:**
- Create: `docs/ledger/repos.toml`, `docs/ledger/plan-status.toml`

**Interfaces:**
- Produces the two files G1's `load_repos` / `load_plan_status` read (formats below, exact). No code.

- [ ] **Step 1: Write `docs/ledger/repos.toml`** verbatim:

```toml
# Repos the derived task graph reads (plan 2026-09-05-session-context, G3).
# Read-only: nothing here writes to a sibling. `plans` defaults to
# docs/superpowers/plans/*.md. Order = display order in the brief.

[[repo]]
name = "nixos-agent-env"
path = "~/nixos-agent-env"

[[repo]]
name = "media"
path = "~/flakes/media"

[[repo]]
name = "gaming"
path = "~/flakes/gaming"

[[repo]]
name = "nixos-skill"
path = "~/flakes/nixos-skill"

[[repo]]
name = "dsh-harness"
path = "~/flakes/dsh-harness"
```

- [ ] **Step 2: Write `docs/ledger/plan-status.toml`** verbatim (statuses decided by the orchestrator from the board archive, 2026-09-05; `open` means nobody has closed it, not that work is planned):

```toml
# Status of plans that predate typed `### KEY (kind, size)` headings
# (plan 2026-09-05-session-context, G3). One row per legacy plan file, any
# repo; status ∈ done | superseded | parked | open. Typed plans need no row:
# their status is derived per task. Edit this file when a legacy plan is
# closed or a decision parks it.

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-phase1-basket-crypto.md"
status = "done"
note = "Phase 1 accepted 2026-09-02"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-phase2-egress-broker.md"
status = "done"
note = "Phase 2 accepted 2026-09-02"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-phase3-classification-assertions.md"
status = "done"
note = "Phase 3 accepted 2026-09-02 (Lane A-prior)"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-phase4a-host-absorption.md"
status = "done"
note = "Phase 4a accepted 2026-09-02 (Lane A-prior)"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-phase4b-cowork.md"
status = "parked"
note = "built + verified, parked by decision 2026-09-02-cowork-tier-parked"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-phase4b-cowork-sending-hang.md"
status = "parked"
note = "with Lane A / Cowork tier A"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-proton-backup-rewire.md"
status = "done"
note = "Lane F accepted 2026-09-02, operator drill 7/7"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-helm.md"
status = "done"
note = "Helm v1 live; superseded in detail by 2026-09-03-helm-v1-switch-consolidated.md"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-helm-v1-switch.md"
status = "superseded"
note = "by 2026-09-03-helm-v1-switch-consolidated.md"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-helm-v1-switch-consolidated.md"
status = "done"
note = "Helm v1 switch landed (decision 2026-09-02-helm-is-the-switch)"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-host-wiring.md"
status = "done"
note = "gaming/media host wiring landed (Phase 4a lane)"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-host-wiring-round2-media.md"
status = "parked"
note = "wiring round 2's media service parked (board START HERE 2026-09-05)"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-gaming-flake.md"
status = "superseded"
note = "executed as ~/flakes/gaming's own plan copy"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-02-media-flake.md"
status = "superseded"
note = "executed as ~/flakes/media's own plan copy; media rework closed 2026-09-03"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-broker-secret-ownership.md"
status = "open"
note = "field bug L1 plan filed 2026-09-03; closure not recorded on the board"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-factory-falsifiability.md"
status = "done"
note = "D9 red-before-green measured (N8, 2026-09-04)"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-factory-skills-and-review-gate.md"
status = "done"
note = "skill injection by role + unskippable review gate landed (a-waves 2026-09-04)"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-lane-fix-round.md"
status = "done"
note = "lane fix round landed 2026-09-03"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-lane-l-round1.md"
status = "done"
note = "Lane L round 1 landed on the board 2026-09-03"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-preswitch-fixes.md"
status = "done"
note = "pre-switch audit CLOSED 2026-09-03"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-03-preswitch-fixes-round2.md"
status = "done"
note = "pre-switch audit CLOSED 2026-09-03"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-04-dsh-review-fix-round.md"
status = "done"
note = "dsh + dark factory 24 h review fix round landed 2026-09-04 (a1–a9)"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-04-opus-regate-fix-wave-a3.md"
status = "done"
note = "a3 re-gate wave landed 2026-09-04"

[[plan]]
repo = "nixos-agent-env"
file = "2026-09-05-night-plan.md"
status = "done"
note = "M1, M2/M2b, S15–S19, a10 all reviewed 2026-09-05 (docs/reviews)"

[[plan]]
repo = "media"
file = "2026-09-02-media-flake.md"
status = "superseded"
note = "by 2026-09-02-media-nix-native.md (media board)"

[[plan]]
repo = "media"
file = "2026-09-02-media-nix-native.md"
status = "done"
note = "four tasks ticked on the media board"

[[plan]]
repo = "gaming"
file = "2026-09-02-gaming-flake.md"
status = "done"
note = "four tasks landed (gaming board)"

[[plan]]
repo = "gaming"
file = "2026-09-03-preswitch-fixes.md"
status = "done"
note = "pre-switch audit CLOSED 2026-09-03"

[[plan]]
repo = "gaming"
file = "2026-09-03-preswitch-fixes-round2.md"
status = "done"
note = "pre-switch audit CLOSED 2026-09-03"

[[plan]]
repo = "nixos-skill"
file = "2026-09-03-nixos-skill.md"
status = "done"
note = "build phase closed (nixos-skill board 2026-09-04)"

[[plan]]
repo = "nixos-skill"
file = "2026-09-03-nixos-skill-fix-round-1.md"
status = "done"
note = "fix round 1 closed (docs/reviews/2026-09-04-fix-round-1-outcome.md there)"
```

- [ ] **Step 3: Validate shape** — `nix develop -c python3 -c 'import tomllib,sys; d=tomllib.load(open("docs/ledger/plan-status.toml","rb")); assert all(p["status"] in ("done","superseded","parked","open") for p in d["plan"]), "bad status"; print(len(d["plan"]), "rows"); r=tomllib.load(open("docs/ledger/repos.toml","rb")); print([x["name"] for x in r["repo"]])'` → `31 rows` and the five names. Then `git add docs/ledger`; lint gate (`nix develop -c githooks/pre-commit` — note `claims.py validate` reads only `claims.toml`, so these files are not validated there until G5).
- [ ] **Step 4: Commit.**

**touches:** docs/ledger/repos.toml, docs/ledger/plan-status.toml
**acceptance:** lint
**commit subject:** `docs: repos.toml names the five repos the task graph reads; plan-status.toml closes the 31 legacy plans (test: lint)`

### G5 (code, S) — the `evidence` CLI gains `tasks` and `repomap`; the hook and `lint` enforce them

**dependsOn:** G4, G2, G3

**Files:**
- Modify: `pkgs/evidence/evidence.py` (`main`: two pass-through subcommands), `tests/evidence/test_evidence.py` (append), `githooks/pre-commit` (after the `claims.py validate` line), `flake.nix` (`lint` runCommand: the same lines plus the check-name assertion; `evidence-unit`: nothing — it already copies `pkgs/evidence` and `tests/evidence`; `docs/ledger` is already copied)

**Interfaces:**
- Consumes `tasks.main(argv)` and `repomap.main(argv)`.
- Produces: `evidence tasks …` and `evidence repomap …` (argv after the subcommand passed through unchanged; `--store` from `evidence` is forwarded as `--store`), `githooks/pre-commit` runs `python3 pkgs/evidence/tasks.py --root . check` and `python3 pkgs/evidence/repomap.py --root . check`; the `lint` check additionally asserts that `docs/MAP.md`'s Checks section equals `builtins.attrNames checks` (computed in Nix, passed in as a file).

- [ ] **Step 1: Failing tests** (append to `tests/evidence/test_evidence.py`):

```python
def test_cli_tasks_and_repomap_pass_through(tmp_path):
    r = subprocess.run([sys.executable, str(SRC), "--store", str(tmp_path / "s"), "tasks", "--root", str(tmp_path), "--runs-dir", str(tmp_path / "none"), "brief"], capture_output=True, text=True, check=False)
    assert r.returncode == 0 and r.stdout.startswith("# Task brief")
    r = subprocess.run([sys.executable, str(SRC), "repomap", "--root", str(tmp_path), "check"], capture_output=True, text=True, check=False)
    assert r.returncode == 1 and "docs/MAP.md is stale" in r.stderr
```

- [ ] **Step 2: Red** — `nix develop -c pytest tests/evidence/test_evidence.py -q -k pass_through` → `argparse` error `invalid choice: 'tasks'` (exit 2, not 0).
- [ ] **Step 3: Implement** in `evidence.py` `main`: before `a = parser.parse_args(argv)`, intercept: `argv = sys.argv[1:] if argv is None else list(argv)`; find the first token in `("tasks", "repomap")` at the position right after the global options; simplest: `pre, rest = split_global(argv)` where `split_global` consumes `--store X` / `--store=X` pairs at the front; if `rest and rest[0] == "tasks"`: `import tasks; return tasks.main(["--store", store, *rest[1:]])` (only add `--store` when the user gave one); if `rest[0] == "repomap"`: `import repomap; return repomap.main(rest[1:])`. Register both names in the subparser too (`sub.add_parser("tasks", help="the derived task graph (see tasks.py --help)")`) so `evidence --help` lists them.
- [ ] **Step 4: Hook + flake.** In `githooks/pre-commit` after the `claims.py validate` line:

```bash
# G5: the derived task graph must be well-formed and the repo map current.
python3 pkgs/evidence/tasks.py --root . --runs-dir /nonexistent --store /nonexistent check
python3 pkgs/evidence/repomap.py --root . check
```

(`--runs-dir /nonexistent --store /nonexistent`: the hook checks shape, not status; status sources are host-local and must not influence whether a commit is allowed.) In `flake.nix`'s `lint` runCommand, before `touch $out`, add the same two lines (the sandbox has no `~/factory`; `python3` is already in the lint inputs — verify with `grep -n 'python3' flake.nix` near the lint definition; if not, add `pkgs.python3` to its `nativeBuildInputs`) plus the check-name assertion:

```nix
# G5: docs/MAP.md's Checks section must equal the flake's real check set.
checkNamesFile = pkgs.writeText "check-names" (nixpkgs.lib.concatMapStrings (n: n + "\n") (builtins.attrNames self.checks.${system}));
```

as a `let` binding in scope of the lint runCommand (or inline `${pkgs.writeText …}`), and in the script:

```bash
awk '/^## Checks/{s=1;next} /^## /{s=0} s&&/^- /{sub(/^- /,"");print}' docs/MAP.md | sort >map-checks
sort ${checkNamesFile} >flake-checks
diff -u flake-checks map-checks || { echo "lint: docs/MAP.md Checks section differs from the flake's checks (regenerate: python3 pkgs/evidence/repomap.py write)" >&2; exit 1; }
```

Red for this guard: temporarily delete one `- ` line from the Checks section of `docs/MAP.md`, run `nix build .#checks.x86_64-linux.lint -L --no-link` → the message above; restore with `git checkout -- docs/MAP.md`. Record both outputs in FACTORY-NOTES.
- [ ] **Step 5: Green** — ruff; `nix develop -c pytest tests/evidence -q`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix build .#checks.x86_64-linux.lint -L --no-link`; `nix develop -c githooks/pre-commit`. If `tasks.py check` fails on the real plans, fix the plan text it names (a stray dependsOn, a code task without acceptance) in the plan file it names — that is a legitimate part of this task; do not change the checker.
- [ ] **Step 6: Commit.**

**touches:** pkgs/evidence/evidence.py, tests/evidence/test_evidence.py, githooks/pre-commit, flake.nix
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the CLI gains tasks and repomap; the hook and lint check the task graph and the repo map, lint asserts MAP.md's checks equal the flake's (test: evidence-unit, lint)`

### G6 (code, S) — the session-start hook, its bats test and the session runbook

**dependsOn:** G4

**Files:**
- Create: `tools/session-start.sh`, `.claude/settings.json`, `tests/unit/90-session-start.bats`, `docs/runbooks/session.md`

**Interfaces:**
- Consumes `evidence bundle --markdown` (E9b) and `evidence tasks --root <repo> brief` (G4/G5) from PATH; falls back to `python3 pkgs/evidence/tasks.py` when `evidence` is absent but `python3` is present; else prints `unavailable`.
- Produces: stdout that Claude Code adds to the session context on `startup|clear|resume|compact`.

- [ ] **Step 1: Failing bats test** `tests/unit/90-session-start.bats` (pattern: `tests/unit/80-seat-driver.bats`; scripts invoked through bash; nothing touches the real host):

```bash
#!/usr/bin/env bats
# tools/session-start.sh is the SessionStart hook (.claude/settings.json):
# it prints the board's START HERE, the evidence bundle and the task brief.
# These tests run it against a fake repo and fake `evidence` binaries.

SCRIPT="$BATS_TEST_DIRNAME/../../tools/session-start.sh"

setup() {
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO/docs" "$BATS_TEST_TMPDIR/bin"
  git -C "$BATS_TEST_TMPDIR" init -q "$REPO"
  printf '# Operations board\n\n## START HERE (today)\n\nQueued: G5.\n\n## Log\n\nold\n' >"$REPO/docs/OPERATIONS.md"
  cat >"$BATS_TEST_TMPDIR/bin/evidence" <<'EOF'
#!/usr/bin/env bash
case "$1 $2" in
  "bundle --markdown") echo "# Evidence bundle"; echo "live gen 40" ;;
  "tasks --root") echo "# Task brief"; echo "| repo |" ;;
  *) echo "unexpected: $*" >&2; exit 9 ;;
esac
EOF
  chmod +x "$BATS_TEST_TMPDIR/bin/evidence"
}

@test "prints START HERE, bundle, brief and the runbook pointer, in order" {
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"## START HERE (today)"* ]]
  [[ "$output" == *"Queued: G5."* ]]
  [[ "$output" != *"old"* ]]
  [[ "$output" == *"# Evidence bundle"* ]]
  [[ "$output" == *"# Task brief"* ]]
  [[ "$output" == *"docs/runbooks/session.md"* ]]
  a=$(printf '%s' "$output" | grep -n 'START HERE' | head -1 | cut -d: -f1)
  b=$(printf '%s' "$output" | grep -n 'Evidence bundle' | cut -d: -f1)
  c=$(printf '%s' "$output" | grep -n 'Task brief' | cut -d: -f1)
  [ "$a" -lt "$b" ] && [ "$b" -lt "$c" ]
}

@test "without evidence on PATH the board still prints and each missing part says unavailable" {
  run env -i PATH="$PATH" HOME="$BATS_TEST_TMPDIR" SESSION_START_EVIDENCE=/nonexistent/evidence bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [[ "$output" == *"Queued: G5."* ]]
  [[ "$output" == *"unavailable: evidence not on PATH"* ]]
}

@test "silent when FACTORY_RUN is set" {
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" FACTORY_RUN=ev3 bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "silent in a linked worktree" {
  git -C "$REPO" -c user.name=t -c user.email=t@x commit -q --allow-empty -m init
  git -C "$REPO" worktree add -q "$BATS_TEST_TMPDIR/wt" -b wt
  mkdir -p "$BATS_TEST_TMPDIR/wt/docs" && cp "$REPO/docs/OPERATIONS.md" "$BATS_TEST_TMPDIR/wt/docs/"  # the empty commit carried no files
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" bash "$SCRIPT" "$BATS_TEST_TMPDIR/wt"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "output over the cap ends with a truncation line" {
  { echo '# Operations board'; echo; echo '## START HERE (big)'; yes 'a line of board text that repeats' | head -400; } >"$REPO/docs/OPERATIONS.md"
  run env -i PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$BATS_TEST_TMPDIR" SESSION_START_CAP=2000 bash "$SCRIPT" "$REPO"
  [ "$status" -eq 0 ]
  [ "${#output}" -le 2200 ]
  [[ "$output" == *"…truncated"* ]]
}
```

- [ ] **Step 2: Red** — `git add tests/unit/90-session-start.bats`; `nix develop -c bats tests/unit/90-session-start.bats` → every test fails with `No such file` for the script. Then `nix build .#checks.x86_64-linux.unit -L --no-link` (the `unit` check runs the whole `tests/unit` directory — confirm by reading its runCommand; if it enumerates files, add the new one there) → red the same way.
- [ ] **Step 3: Implement `tools/session-start.sh`**:

```bash
#!/usr/bin/env bash
# session-start.sh [repo] -- the SessionStart hook (.claude/settings.json).
# Prints what a fresh session needs: the board's one START HERE block, the
# evidence bundle, the task brief and one pointer. Never fails the session,
# never evaluates the flake, silent for factory agents and linked worktrees.
# Plan: docs/superpowers/plans/2026-09-05-session-context.md (G6).
set -u
repo=${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}
cap=${SESSION_START_CAP:-6000}
ev=${SESSION_START_EVIDENCE:-evidence} # tests point this at a missing binary
[ -n "${FACTORY_RUN:-}" ] && exit 0
common=$(git -C "$repo" rev-parse --git-common-dir 2>&1) || common=.git
case $common in .git | "$repo/.git") ;; *) exit 0 ;; esac
out=$(
  echo "## Board — START HERE (docs/OPERATIONS.md)"
  awk '/^## START HERE/{s=1;print;next} s&&/^## /{exit} s' "$repo/docs/OPERATIONS.md" 2>&1 || echo "unavailable: docs/OPERATIONS.md not readable"
  echo
  if command -v "$ev" >/dev/null; then
    "$ev" bundle --markdown 2>&1 || echo "unavailable: evidence bundle failed"
    echo
    "$ev" tasks --root "$repo" brief 2>&1 || echo "unavailable: evidence tasks failed"
  elif command -v python3 >/dev/null && [ -f "$repo/pkgs/evidence/tasks.py" ]; then
    echo "unavailable: evidence not on PATH (bundle skipped)"
    python3 "$repo/pkgs/evidence/tasks.py" --root "$repo" brief 2>&1 || echo "unavailable: tasks.py failed"
  else
    echo "unavailable: evidence not on PATH"
  fi
  echo
  echo "Where everything is: docs/runbooks/session.md"
)
if [ "${#out}" -gt "$cap" ]; then
  printf '%s\n…truncated at %s bytes (SESSION_START_CAP)\n' "${out:0:$cap}" "$cap"
else
  printf '%s\n' "$out"
fi
exit 0
```

Then `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|resume|compact",
        "hooks": [
          { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/tools/session-start.sh\" \"$CLAUDE_PROJECT_DIR\"", "timeout": 10 }
        ]
      }
    ]
  }
}
```

(`$CLAUDE_PROJECT_DIR` is set by Claude Code for project hooks; the superpowers plugin's own hook file at `~/.claude/plugins/cache/claude-plugins-official/superpowers/6.3.0/hooks/hooks.json` is the format reference on this install.) `chmod +x tools/session-start.sh`. Note: `.claude/worktrees/` already exists untracked; add `.claude/settings.json` only.
- [ ] **Step 4: Runbook `docs/runbooks/session.md`** (plain language, one command each): what a fresh session sees and where each part comes from (board block → `docs/OPERATIONS.md`; bundle → the evidence store, `docs/runbooks/evidence.md`; brief → plans + reviews + `~/factory/runs` + `runs.jsonl` + `docs/ledger/plan-status.toml`, `docs/ledger/repos.toml`); how to regenerate by hand (`bash tools/session-start.sh`); the one check when nothing shows at `/new` (`bash tools/session-start.sh | head`; then confirm `.claude/settings.json` is present and the checkout is not a linked worktree); where the queue's judgement lives (the START HERE "Now" paragraph); how to close a legacy plan (edit `plan-status.toml`); how to read the map (`docs/MAP.md`, regenerated by `python3 pkgs/evidence/repomap.py write`).
- [ ] **Step 5: Green** — `nix develop -c shellcheck tools/session-start.sh`; `nix develop -c bats tests/unit/90-session-start.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate. Real run: `bash tools/session-start.sh | head -40` in the checkout shows the board block and either the bundle or `unavailable:` lines; paste the first 10 lines into FACTORY-NOTES.
- [ ] **Step 6: Commit.**

**touches:** tools/session-start.sh, .claude/settings.json, tests/unit/90-session-start.bats, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: a SessionStart hook prints START HERE, the evidence bundle and the task brief at /new and after compaction; silent for factory agents; runbook (test: unit, lint)`

### G7 (docs, S) — CLAUDE.md shrinks to rules and pointers

**dependsOn:** G5, G2

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes `docs/MAP.md` (G2) and the hook (G6) being real.
- Produces a CLAUDE.md of at most 4500 bytes (`wc -c`), verified in the task.

- [ ] **Step 1: Rewrite.** Keep, tightened: the title; "What this is, and the one rule that matters most" (unchanged in substance); Commands (the block as E9b left it, plus `evidence tasks --root . brief` and `python3 pkgs/evidence/repomap.py write`); Gotchas (each one sentence); "How work is done here" (unchanged in substance, plus one sentence: "The queue is derived: `evidence tasks` — never type task status into the board"). Replace the Architecture section and the "Check names" paragraph with:

```markdown
## Where things are

`docs/MAP.md` (generated, always current: modules, packages, every check name,
tests, hosts, tools). Facts at session start come from the hook
(`tools/session-start.sh`, runbook `docs/runbooks/session.md`): the board's
START HERE, `evidence bundle`, `evidence tasks --brief`.
```

- [ ] **Step 2: Verify** — `wc -c CLAUDE.md` ≤ 4500; every path named in CLAUDE.md exists (`grep -o '`[a-zA-Z0-9_./-]*`' CLAUDE.md | tr -d '`' | while read -r p; do [ -e "$p" ] || echo "missing: $p"; done` prints nothing for paths; flags and commands are not paths and may be listed — judge by eye and note them); lint gate.
- [ ] **Step 3: Commit.**

**touches:** CLAUDE.md
**acceptance:** lint
**commit subject:** `docs: CLAUDE.md shrinks to rules, commands and pointers; the map and the hook carry the rest (test: lint)`

### G8 (code, S) — the board's queue block is generated; drift refused

**dependsOn:** G5

**Files:**
- Modify: `pkgs/evidence/tasks.py` (`render_board_block`, `write_board`, `board_drift`; `main` gains `write-board` and `check --board FILE`), `tests/evidence/test_tasks.py` (append), `docs/OPERATIONS.md` (E8's shape: insert the two markers around the Queued paragraph), `githooks/pre-commit` and `flake.nix` `lint` (the `check` line gains `--board docs/OPERATIONS.md`)

**Interfaces:**
- Consumes G4's `build`, `waves`.
- Produces:

```python
BEGIN, END = "<!-- tasks:begin -->", "<!-- tasks:end -->"
def render_board_block(graph) -> str          # "**Queued (derived).** <repo>: <wave-1 keys> (<plan>) · …\n" — one line per repo with open work; "nothing queued" when none
def write_board(path, graph) -> bool          # replaces text between the markers; returns True when the file changed; raises SystemExit(1) with a message when markers are missing
def board_drift(path, graph) -> str | None    # None when current, else the unified diff
```

- [ ] **Step 1: Failing tests** (append):

```python
def test_board_block_roundtrip_and_drift(tmp_path):
    g = repo_with(tmp_path, ["typed.md"], landed=["evidence: the store (test: evidence-unit, lint)"])
    graph = {"generated": "t", "repos": [g]}
    board = tmp_path / "OPERATIONS.md"
    board.write_text("# Board\n\n## START HERE (x)\n\n<!-- tasks:begin -->\nstale\n<!-- tasks:end -->\n\n**Now.** words\n")
    assert tk.board_drift(board, graph) is not None
    assert tk.write_board(board, graph) is True
    text = board.read_text()
    assert "**Queued (derived).** nixos-agent-env: E3 E7 (typed.md)" in text and "stale" not in text and "**Now.** words" in text
    assert tk.board_drift(board, graph) is None
    assert tk.write_board(board, graph) is False


def test_board_without_markers_is_an_error(tmp_path):
    board = tmp_path / "OPERATIONS.md"
    board.write_text("# Board\n")
    try:
        tk.write_board(board, {"generated": "t", "repos": []})
    except SystemExit as e:
        assert e.code == 1
    else:
        raise AssertionError("expected SystemExit")
```

- [ ] **Step 2: Red** — `nix develop -c pytest tests/evidence/test_tasks.py -q -k board` → `AttributeError: … 'board_drift'`.
- [ ] **Step 3: Implement**; `main`: `write-board [--board docs/OPERATIONS.md]` and `check --board FILE` (adds `tasks: docs/OPERATIONS.md queue block is stale — run: evidence tasks write-board` when `board_drift` is not None). Board: in `docs/OPERATIONS.md` (E8 shape) wrap the existing Queued paragraph in the markers, run `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board`, and move any hand-written queue sentences that the block does not derive into the **Now** paragraph (≤ 10 lines). Hook and `lint`: the `tasks.py … check` line gains `--board docs/OPERATIONS.md`. E8's shape guard (one START HERE, ≤ 160 lines) must still pass.
- [ ] **Step 4: Green** — ruff; pytest; `evidence-unit`; `lint`; lint gate. Red for the guard: change one character inside the block, `nix develop -c githooks/pre-commit` → the stale message; restore.
- [ ] **Step 5: Commit.** Orchestrator afterwards (not the factory): delete the memory file `project-status.md` and its index line, add the index line "session facts come from the hook output, not from memory" (spec §4).

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, docs/OPERATIONS.md, githooks/pre-commit, flake.nix
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the board's queue block is generated by evidence tasks write-board; the hook and lint refuse drift (test: evidence-unit, lint)`

## Fix round after the wave-1 gates (2026-09-05 ~13:10)

Gate outcomes: G3 approved; G4 approved (nine minors, two with teeth); G1 REJECTED (`docs/reviews/2026-09-05-opus-review-sc1-G1.md`: six surviving mutants on the precedence table, fenced code blocks parsed as tasks); G2 REJECTED (`docs/reviews/2026-09-05-opus-review-sc1-G2.md`: commit subject not the plan's; the 8-space indent anchor untested — relaxing it returns 86 names, not 38). One bounded fix round each (rule A1). G4 was built on task/G1, so it is re-applied on top of G1b as G4b. Dispatch: `factory-wave sc1 "G1b G4b" "G2b"`. The original task/G1, task/G2, task/G4 branches are never integrated.

Common rule for every fix round below: the workspace is fresh from `main` (factory-ws does this). First bring the original task's diff in **uncommitted**: `git fetch -q <workspace-of-original> task/<KEY> && git cherry-pick -n FETCH_HEAD` (read-only access to the sibling workspace; never write there). Then read the review file named above in full. Then fix red-first: a finding that says "untested" is fixed by adding the test AND proving it load-bearing — apply the mutation the review describes, run the test (must fail), revert the mutation (must pass); record each in FACTORY-NOTES. Finish with ONE commit whose subject is byte-identical to the original task's **commit subject** (fix rounds keep the plan's subject: that is how the graph marks the chain landed). Amend is forbidden — you are making the first commit on this branch.

### G1b (code, M) — G1 fix round: precedence pinned, fences skipped, chains and re-keys tested

**dependsOn:** none

**Files:** the same as G1 — `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `tests/evidence/fixtures/plans/typed.md`, `tests/evidence/fixtures/plans/legacy.md` (new fixture lines only). Original: `/home/dalhaka/factory/ws/sc1/G1`, branch `task/G1` (commit 68181b6).

**Interfaces:** unchanged from G1, plus: `CHAIN_RE = re.compile(r"^(?P<root>.*\d)(?P<suffix>[a-z]{1,2})$")` so a second fix round chains too (`chain_root("R3rb") == "R3"`; `chain_root("P1pro") == "P1pro"` still, three letters do not match); `parse_plan` ignores everything inside fenced code blocks (a line starting with ``` toggles a fence; headings and field lines inside a fence are body text at most, never tasks).

- [ ] **Step 1: Fence skipping, red first.** Append to `typed.md` (after `D1`'s section) a new section:

```markdown
## Operator

Nothing to switch. The text below is a quoted example and must not become tasks:

    ```markdown
    ### Z9 (code, S) — phantom inside a fence

    **dependsOn:** D1
    ```
```

(the fence lines in the fixture are indented by four spaces here only so this plan's own parser does not see them — in the fixture file write them flush-left). Test: `plan = tk.parse_plan(FIXTURES / "typed.md")`; `assert [t["key"] for t in plan["tasks"]] == ["E1", "E3", "E5", "E7", "D1"]`; `assert "Operator" not in by["D1"]["body"]` (this also pins the section-reset the review's M13 found untested). Run → red (`Z9` present; body swallows the section). Implement the fence toggle in `parse_plan`; green.
- [ ] **Step 2: Pin the precedence table** (each test first shown to fail under the named mutation from the review, then the mutation reverted): (a) M2 — in `test_derive_status_precedence` give `E1` a review `{"verdict": "REJECTED", ...}` and keep asserting `landed`; (b) M15 — a task whose own subject is not landed but whose chain root's subject is, with a review on `E7b`: assert `landed`; (c) M9 — in `test_scan_repo_and_build` monkeypatch `tk.read_recorded` to return `{("other.md", "D1"): "done", ("typed.md", "E7"): "done"}` and assert `E7` is `recorded` while `D1` is not; (d) M10 — `read_results` with the same key in two run dirs, older mtime first (`os.utime`), assert the newer run wins; (e) M11 — a plan task `R3` with a review on `R3r` whose subject... simpler: `landed_keys` built from a landed subject of `R3` while a dependant names `R3`: assert `ready`; and `chain_root("R3rb") == "R3"`; (f) M8 — make `c.md` in `test_read_reviews_matches_only_the_gate_header` contain the exact gate header on its second line and assert it is NOT matched.
- [ ] **Step 3: Minors.** `read_recorded` catches `Exception` (plan text) — add a test with a malformed `runs.jsonl` row (a JSON list, not an object) that must yield `{}`; `typed.md` ends with a newline.
- [ ] **Step 4: Green** — ruff format/check; `nix develop -c pytest tests/evidence -q`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; lint gate. Real-data probe: `parse_plan` on `docs/superpowers/plans/2026-09-05-session-context.md` returns exactly `G1 G4 G2 G3 G5 G6 G7 G8 G1b G4b G2b` (no E1/X1 phantoms).
- [ ] **Step 5: One commit**, subject byte-identical to G1's.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, tests/evidence/fixtures/plans/typed.md, tests/evidence/fixtures/plans/legacy.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: tasks.py parses typed plans, chains fix rounds and derives task status from landed subjects, gate reviews, seat results and run records (test: evidence-unit, lint)`

### G4b (code, M) — G4 re-applied on G1b, two vacuous tests made load-bearing

**dependsOn:** G1b (chained: the workspace is forked from task/G1b by `factory-wave`)

**Files:** the same as G4 — `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `tests/evidence/fixtures/plans/second.md`. Original: `/home/dalhaka/factory/ws/sc1/G4`, branch `task/G4` (its tip commit e3f101e only: `git fetch -q /home/dalhaka/factory/ws/sc1/G4 task/G4 && git cherry-pick -n FETCH_HEAD`). If `tasks.py` conflicts because G1b changed `parse_plan`/`derive_status`, resolve keeping G1b's parser and status code AND G4's scheduling code; run the whole test file before continuing.

- [ ] **Step 1** cherry-pick as above; `nix develop -c pytest tests/evidence -q` green (G1b's and G4's tests together).
- [ ] **Step 2** from `docs/reviews/2026-09-05-opus-review-sc1-G4.md`, the two findings with teeth, each red-first by mutation: (a) the claims owner filter — in `test_brief_lists_counts_next_wave_and_operator_items` give the non-operator claim `id = "orch-only"` and assert `"orch-only" not in md` (mutation: drop `owner == "operator"` → must fail); (b) `factory_args` plan filter — load `typed.md` and `second.md` and assert `factory_args(g, "second.md")` returns only `X1 X2 X3` keys (mutation: ignore `plan` → must fail). Also `second.md` ends with a newline.
- [ ] **Step 3: Green** — ruff; pytest; `evidence-unit`; lint gate. Real data: `python3 pkgs/evidence/tasks.py --root /home/dalhaka/nixos-agent-env check; echo exit=$?` (read-only; report the output verbatim — repos.toml may still be absent).
- [ ] **Step 4: One commit**, subject byte-identical to G4's.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, tests/evidence/fixtures/plans/second.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: tasks.py schedules Kahn waves, merges overlapping touches into seat groups, emits dark-factory task lists, finds cross-plan conflicts, checks the graph and renders the brief (test: evidence-unit, lint)`

### G2b (code, S) — G2 fix round: the exact subject, the indent anchor proven, the plan's layout

**dependsOn:** none

**Files:** the same as G2 — `pkgs/evidence/repomap.py`, `tests/evidence/test_repomap.py`, `docs/MAP.md`. Original: `/home/dalhaka/factory/ws/sc1/G2`, branch `task/G2` (commit cf75758).

- [ ] **Step 1** cherry-pick as in the common rule. Read `docs/reviews/2026-09-05-opus-review-sc1-G2.md`.
- [ ] **Step 2: Indent anchor, red by mutation.** Extend the `FLAKE` fixture's checks block with a nested attribute set and a deeper child, e.g. after `lint`: `        nested = {\n          inner-child = 1;\n        };` — `flake_check_names` must return `host-core, lint, nested, helm-control-assertion-negative-profiles` and never `inner-child`. Prove: relax the regex to any indent → test fails; restore. Also make the block-terminating `break` load-bearing: after the `      };` that closes checks add `      other-block = {\n        zzz = 1;\n      };` — `zzz` must not appear (today's fixture's `other = 3;` sits at 6 spaces and cannot catch it).
- [ ] **Step 3: Layout as the plan's Step 3 shows** — headings `## NixOS modules`, `## Packages`, `## Checks (nix build .#checks.x86_64-linux.<name>)`, `## Tests`, `## Hosts`, `## Tools`; test lines `` - `tests/unit` — 2 files ``; stale message exactly `repomap: docs/MAP.md is stale — run: python3 pkgs/evidence/repomap.py write`; pin each with an assertion (the existing tests assert only substrings). Pin the package-description precedence: a fixture package with both `broker.sh` (comment A) and `default.nix` (comment B) must describe as A; mutation: drop the first tier → fails.
- [ ] **Step 4** regenerate `docs/MAP.md` (`python3 pkgs/evidence/repomap.py --root . write`), confirm `check` exits 0 and the Checks section still has 38 lines; fixture files end with a newline.
- [ ] **Step 5: Green** — ruff; pytest; `evidence-unit`; lint gate.
- [ ] **Step 6: One commit**, subject byte-identical to G2's plan subject (below — NOT the original commit's).

**touches:** pkgs/evidence/repomap.py, tests/evidence/test_repomap.py, docs/MAP.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: repomap.py generates docs/MAP.md (modules, packages, checks, tests, hosts, tools) and refuses a stale map (test: evidence-unit, lint)`

## Wave 1 landed (2026-09-05 ~14:50) — amendments to G5 from the gates

> **Superseded 2026-09-05 ~15:05:** these amendments were appended outside `### G5`, and the seat brief carries only a task's own section, so G5 never saw them (G5 was built and gated against its section text). They are re-planned verbatim as task **G9** below; nothing in this block is a requirement on G5.

Landed on main: G1b, G4b, G2b, G3 (integ/sc1). The G4b gate ran the scheduler on the real five-repo graph: `check` clean, brief renders, `conflicts` already names B1 × G5/G8 on `flake.nix` (different blocks; B1 is the paused session's backup task).

**G5 gains these steps (same touches, same subject):**
- **Chain state is the last member's own state.** Today `derive_status` takes the newest review across the whole chain, so `G1b` (result done, no gate yet) inherits `G1`'s REJECTED and the brief says a fix round is owed for the fix round. Rule: order the chain root-first then by suffix; for the LAST member compute rules 2–4 from ITS OWN review/result/record (a member with none of those is `ready`/`blocked` by the root's dependencies); rule 1 (landed by the plan subject) still applies to the whole chain. Test, red first: G1 review REJECTED + `G1b` result `done` and no G1b review → state `ran`, detail names `G1b`; then add a G1b APPROVED review → `approved`, detail `G1b`. Also `render_brief` lists a chain once, by root, with the last member in the detail.
- **Pins from the G4/G4b minors:** `conflicts` restricted to different plans (same-plan overlap not reported) — test with two overlapping tasks in one plan; `waves --factory-args` without `--plan` exits 2 with a usage message instead of printing `[]`; `legacy open` counts rows with `status == "open"` — fixture with one open and one done row; the CLI `json` payload has `repos[0].tasks[*].state` asserted.
- **From the G2b gate:** `repomap._IGNORED_PARTS` gains `.ruff_cache`; `_count_files` counts `git ls-files`-tracked files only (fallback to the directory walk when `git` is unavailable), so a stray untracked file cannot trip the hook once `check` is wired in. Test: an untracked file under `tests/x/` does not change the count.
- `docs/ledger/repos.toml` ends with a newline (G3 nit; in G5's touches as a one-byte fix — add it to touches).

G5's **touches** becomes: pkgs/evidence/evidence.py, pkgs/evidence/tasks.py, pkgs/evidence/repomap.py, tests/evidence/test_evidence.py, tests/evidence/test_tasks.py, tests/evidence/test_repomap.py, docs/ledger/repos.toml, githooks/pre-commit, flake.nix. Commit subject unchanged.


### G9 (code, S) — chain state is the last member's own state; the gate pins from G4/G4b/G2b/G3

**dependsOn:** G5 (G5 edits `repomap.py`; G9 edits it too)

**Files:**
- Modify: `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `pkgs/evidence/repomap.py`, `tests/evidence/test_repomap.py`, `docs/ledger/repos.toml` (one trailing newline)

**Interfaces:**
- `derive_status` (G1b) changes for chains only: order the chain root-first then by suffix; the LAST member's own review / result / record decides rules 2–4 (a last member with none of those falls to rule 5 by the root's dependencies); rule 1 (landed by the plan subject) applies to the whole chain as before. `render_brief` lists a chain once, by root, naming the last member in the detail.
- `conflicts` reports only pairs from different plans. `main`: `waves --factory-args` without `--plan` exits 2 with a usage line. `render_brief`'s `legacy open` counts rows with `status == "open"`.
- `repomap._IGNORED_PARTS` gains `.ruff_cache`; `_count_files` counts `git ls-files`-tracked files (fallback: the directory walk when `git` is unavailable or the root is not a repo).

- [ ] **Step 1: Failing tests** (append to `tests/evidence/test_tasks.py` / `test_repomap.py`; the test helpers `fake_git`, `write_review`, `write_result`, `make_workspace`, `repo_with` exist):
  - chain: task `G1` in a fixture plan; `write_review` REJECTED for `G1`; a result for `G1b` (`write_result` + `make_workspace` with origin `nixos-agent-env`); `scan_repo` → `G1` state `ran`, detail contains `G1b`. Then add an APPROVED review for `G1b` → `approved`, detail `G1b`. Then a REJECTED review for `G1b` and nothing newer → `rejected`, detail `G1b`. Red today: the first case reports `rejected` (the newest review across the chain).
  - brief: with the same fixture, the "Rejected, fix round owed" line names `G1` at most once and never `G1b` alone.
  - conflicts: two tasks in ONE plan with overlapping touches → not reported (mutation: drop the different-plan condition → fails).
  - `main(["--root", root, "waves", "--repo", "r", "--factory-args"])` without `--plan` → returns 2 and prints `usage` to stderr (capture with capsys).
  - `legacy open`: plan-status rows `open` + `done` → the brief's `legacy open` column is 1 (mutation: count all legacy rows → 2, fails).
  - CLI json: `repos[0].tasks[0].state` present and in `STATES`.
  - repomap: a fixture repo initialised with `git init` + one tracked file under `tests/unit/` and one untracked → `tests/unit` counts 1; `.ruff_cache/` under `tests/` is ignored in the fallback walk.
- [ ] **Step 2: Red** — run the new tests; each fails for the reason stated (record the lines).
- [ ] **Step 3: Implement**; keep every existing test green (G1b's precedence tests pin rules 1–5 for single-key chains — they must not change).
- [ ] **Step 4: Green** — ruff; `nix develop -c pytest tests/evidence -q -p no:cacheprovider`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; lint gate. Real data (read-only): `python3 pkgs/evidence/tasks.py --root . brief` — the "Rejected" line no longer lists a fix-round key whose own result is done and ungated; paste the brief into FACTORY-NOTES.
- [ ] **Step 5: Commit.**

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, pkgs/evidence/repomap.py, tests/evidence/test_repomap.py, docs/ledger/repos.toml
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: a chain reports its last member's own state; conflicts are cross-plan only; factory-args needs --plan; repo map counts tracked files and ignores .ruff_cache (test: evidence-unit, lint)`

### G10 (code, XS) — the hook budgets each part, so the brief always prints

**dependsOn:** G6

Gate for G6 (`docs/reviews/2026-09-05-opus-review-sc1-G6.md`, APPROVED) measured the live output: START HERE 5,189 B + bundle 6,032 B against one 6,000 B cap, so the task brief and the runbook pointer never appear today. Also three minors from that gate.

**Files:**
- Modify: `tools/session-start.sh`, `tests/unit/90-session-start.bats`, `docs/runbooks/session.md`

**Interfaces:**
- Per-part caps, each an env var with a default: `SESSION_START_CAP_BOARD` (3000), `SESSION_START_CAP_BUNDLE` (2500), `SESSION_START_CAP_BRIEF` (1500); a part over its cap is cut at the cap and followed by one line `…<part> truncated at N chars (SESSION_START_CAP_<PART>)`; the pointer line always prints last. The old `SESSION_START_CAP` becomes the total ceiling (default 8000) applied after the parts. The word is `chars` everywhere (the cap slices characters).
- Runbook: `docs/superpowers/reviews` → `docs/reviews`; document the four caps.

- [ ] **Step 1: Failing tests** (append to the bats file; the fake `evidence` pattern is already there): a fake `evidence` whose `bundle` prints 4,000 chars → output still contains `# Task brief` and the pointer line, and contains `…bundle truncated at 2500 chars`; a 400-line board → `…board truncated at 3000 chars` and the bundle still follows; `SESSION_START_CAP=1000` → total ends with the total-cap line; a failing `evidence bundle` (exit 9) → `unavailable: evidence bundle failed` (this pins one of the three guards the gate found untested; add the same for `tasks` failing).
- [ ] **Step 2: Red** — run the bats file; the new tests fail (no per-part caps; brief absent).
- [ ] **Step 3: Implement** with a small `cap_part NAME TEXT LIMIT` bash function; keep the existing tests green; fix the runbook path and wording.
- [ ] **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/90-session-start.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate. Real run (read-only): `bash tools/session-start.sh | tail -8` shows the brief and the pointer.
- [ ] **Step 5: Commit.**

**touches:** tools/session-start.sh, tests/unit/90-session-start.bats, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: the hook budgets board, bundle and brief separately so the brief and the pointer always print; failing-evidence guards pinned (test: unit, lint)`

### G5b (code, S) — G5 fix round: the task-graph guard inspects the tree under test

**dependsOn:** none (G6 is already on main)

Gate: `docs/reviews/2026-09-05-opus-review-sc1-G5.md` — REJECTED. The `tasks.py check` line in `githooks/pre-commit` and in the `lint` runCommand resolved repos from `docs/ledger/repos.toml`'s absolute `~/nixos-agent-env` path, so in the sandbox (and in any clone) it validated the operator's live checkout, never the tree under test: a planted `**dependsOn:** ZZZ` left both gates green. The CLI pass-through, the `docs/MAP.md` check-name assertion and the two forced extra touches (`repomap.py` sparse-tree tolerance, regenerated `docs/MAP.md`) were accepted. Common fix-round rule applies (fresh workspace from main, `git fetch -q /home/dalhaka/factory/ws/sc1/G5 task/G5 && git cherry-pick -n FETCH_HEAD`, read the review in full, ONE commit with G5's subject). Note main now also carries G6 (`tools/session-start.sh`, three `unit`-block lines in `flake.nix`); resolve the cherry-pick's `flake.nix` context if it conflicts — the two edits are in different blocks.

**Files:** the same as G5 — `pkgs/evidence/evidence.py`, `tests/evidence/test_evidence.py`, `githooks/pre-commit`, `flake.nix`, plus `pkgs/evidence/repomap.py` and `docs/MAP.md` only as carried from G5 (no further change).

- [ ] **Step 1: The guard inspects `--root .`.** In both copies the line becomes: `python3 pkgs/evidence/tasks.py --root . --repos <(printf '[[repo]]\nname = "nixos-agent-env"\npath = "."\n') --runs-dir /nonexistent --store /nonexistent check` — if process substitution is unavailable in the `lint` runCommand's shell, write the two-line TOML to `$TMPDIR/repos.toml` first and pass that path. `load_repos` must expand a relative `path` against the TOML file's directory or the current directory — check `tasks.py` and, if it only does `os.path.expanduser`, make a relative path resolve against `--root` (a one-line change in `load_repos`/`build` counts as G5's file set? No — `tasks.py` is not in G5's touches; instead pass `path = "$PWD"` / `path = "'"$(pwd)"'"` from the shell so no `tasks.py` change is needed).
- [ ] **Step 2: Red, both gates, recorded verbatim.** Plant `**dependsOn:** ZZZ` on a typed task in `docs/superpowers/plans/2026-09-05-evidence-store.md` in the workspace: `nix develop -c githooks/pre-commit` → `tasks: nixos-agent-env/<KEY> dependsOn ZZZ: unknown key`, exit 1; `git add` the plan and `nix build .#checks.x86_64-linux.lint -L --no-link` → the same message in the builder log, exit 1. Revert the plant (`git checkout -- <plan>`). Both outputs go into FACTORY-NOTES.
- [ ] **Step 3: `--store` forwarding pinned.** In `tests/evidence/test_evidence.py` add a test that runs `evidence --store <dir> tasks --root <tmp> --runs-dir <none> json` and asserts the store path reaches `tasks.main` — simplest: a fixture store with one `runs.jsonl` row naming a task in a fixture plan, and assert that task's state is `recorded` only when `--store` is given (drop the forwarding → the test must fail; record the red).
- [ ] **Step 4: Green** — ruff; `nix develop -c pytest tests/evidence -q -p no:cacheprovider`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix build .#checks.x86_64-linux.lint -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: One commit**, subject byte-identical to G5's.

**touches:** pkgs/evidence/evidence.py, tests/evidence/test_evidence.py, githooks/pre-commit, flake.nix, pkgs/evidence/repomap.py, docs/MAP.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the CLI gains tasks and repomap; the hook and lint check the task graph and the repo map, lint asserts MAP.md's checks equal the flake's (test: evidence-unit, lint)`

### G10b (code, XS) — G10 fix round: pointer-last and the budget arithmetic pinned (test-only)

**dependsOn:** none

Gate: `docs/reviews/2026-09-05-opus-review-sc1-G10.md` — REJECTED on coverage only; the script is correct and live output is right. Three mutants survived: print the pointer before the brief (M3); remove `SESSION_START_CAP_BRIEF` (M8); revert the total cap to 6000 (M10) — each reproduces the G6 defect with the suite green. Common fix-round rule (fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/sc1/G10 task/G10 && git cherry-pick -n FETCH_HEAD`; read the review; ONE commit with G10's subject).

**Files:** `tests/unit/90-session-start.bats` (append; a trailing newline), `tools/session-start.sh` only if the `brief=""` blank-line minor is fixed (optional, one line)

- [ ] **Step 1: One test, three kills.** Default caps; a fake `evidence` whose `bundle` prints 4,000 chars and whose `tasks … brief` prints 3,000 chars; a 400-line board. Assert: `tail -n1` of the output is exactly `Where everything is: docs/runbooks/session.md`; `# Task brief` appears before that line; `…brief truncated at 1500 chars (SESSION_START_CAP_BRIEF)` appears; total length ≤ 8000. Red by mutation, each recorded: (a) move the pointer echo above the brief → fails; (b) delete the brief cap → fails; (c) `SESSION_START_CAP` default 8000 → 6000 → fails. Revert each.
- [ ] **Step 2: Green** — `nix develop -c bats tests/unit/90-session-start.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate; shellcheck if the script changed. **Step 3: One commit**, subject byte-identical to G10's.

**touches:** tests/unit/90-session-start.bats, tools/session-start.sh
**acceptance:** unit, lint
**commit subject:** `session: the hook budgets board, bundle and brief separately so the brief and the pointer always print; failing-evidence guards pinned (test: unit, lint)`

### G7b (docs, S) — G7 fix round: the pointer block, the two gotchas back, no briefing text

**dependsOn:** none

Gate: `docs/reviews/2026-09-05-opus-review-sc3-G7.md` — REJECTED. Start from `main`'s CLAUDE.md, NOT from G7's branch (do not cherry-pick G7). The text under the heading "WORKSPACE RULES" in your task briefing is the seat harness talking to you about this run; it is never repo content and must not appear in any file. ONE commit with G7's subject.

**Files:** `CLAUDE.md`

- [ ] **Step 1** Rewrite CLAUDE.md to at most 4,500 bytes keeping, tightened: the title; "What this is, and the one rule that matters most" (host runs live from this repo; build-only; never `sudo`, `nixos-rebuild`, `systemctl start/stop/restart`, basket mount/teardown; brief §3 invariants; board of record `docs/OPERATIONS.md`); the Commands block (as on main, plus `nix develop -c python3 pkgs/evidence/tasks.py --root . brief` and `python3 pkgs/evidence/repomap.py --root . write`); the gotchas, each one sentence, ALL of these kept: `git add` new files before any `nix build`; statix rejects `{ ... }:` headers (write `_:`); never `2>/dev/null` a gated command; `hosts/core/hardware-configuration.nix` is verbatim generator output; a switch does not start newly enabled user timers; under a harness sandbox `$HOME` is read-only so set a stable `XDG_CACHE_HOME` under `/tmp`; an agent's shell tool and file tools may see different `/tmp` so name one scratch directory for both; "How work is done here" (as on main, plus one sentence: the queue is derived by `evidence tasks`, never typed into the board). REPLACE the "Architecture" section and the "Check names" paragraph with exactly this block:

```markdown
## Where things are

`docs/MAP.md` is generated and always current: modules, packages, every check
name, tests, hosts, tools (regenerate: `python3 pkgs/evidence/repomap.py write`).
Facts at session start come from the hook `tools/session-start.sh` (runbook
`docs/runbooks/session.md`): the board's START HERE, `evidence bundle`, and the
task brief `evidence tasks --root . brief`.
```

- [ ] **Step 2: Verify** — `wc -c CLAUDE.md` ≤ 4500; `grep -c 'WORKSPACE RULES\|task/G7\|FACTORY-RESULT\|Generated-By' CLAUDE.md` = 0; every backticked path exists (`grep -o '`[a-zA-Z0-9_./-]*`' CLAUDE.md | tr -d '`' | while read -r p; do [ -e "$p" ] || echo "missing: $p"; done` prints only non-path tokens such as flags); `nix develop -c githooks/pre-commit`; `nix build .#checks.x86_64-linux.lint -L --no-link`.
- [ ] **Step 3: Commit.**

**touches:** CLAUDE.md
**acceptance:** lint
**commit subject:** `docs: CLAUDE.md shrinks to rules, commands and pointers; the map and the hook carry the rest (test: lint)`

### G8b (code, S) — G8 finished: the staged work committed; the drift check lives in the hook and the unit tests, not in lint

**dependsOn:** none (G9 is on main)

G8 ended with a provider error (`PI_AI_ERROR: finish_reason: error`) on its final turn, after the work was complete and staged in `/home/dalhaka/factory/ws/sc3/G8` and before the commit; no `.result` block, no commit. The implementer also found that `tasks.py check --board` cannot run in the flake's `lint` sandbox (no git history → every task reads `landed = 0` → false drift), so the board drift check belongs in `githooks/pre-commit` (real git) and in `evidence-unit` (fixtures), as the spec §3 says — G8's "flake.nix lint gains --board" line was a plan mistake and is withdrawn. Fresh workspace from `main` (G9 is there).

**Files:** `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `docs/OPERATIONS.md`, `githooks/pre-commit` — NOT `flake.nix`.

- [ ] **Step 1: Recover the staged work, read-only from the sibling workspace.** `git -C /home/dalhaka/factory/ws/sc3/G8 diff --cached > "$SCRATCH/g8.patch"` (write the patch under your own workspace's scratch dir, never into that sibling), then `git apply --index "$SCRATCH/g8.patch"` in your workspace. If `docs/OPERATIONS.md` conflicts (the board moved since G8's base), re-apply by hand: the two markers `<!-- tasks:begin -->` / `<!-- tasks:end -->` around the Queued block, then regenerate with `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board`. Read the diff you now hold in full before continuing.
- [ ] **Step 2: Verify against G8's contract** (`### G8 (code, S)` above): `render_board_block`, `write_board`, `board_drift`, `main` with `write-board` and `check --board FILE`; the two G8 tests present; `githooks/pre-commit`'s `tasks.py … check` line gains `--board docs/OPERATIONS.md`; `flake.nix` untouched (if the patch touches it, drop that hunk). E8's shape guard still passes (one START HERE, ≤ 160 lines). Red: change one character inside the generated block → `nix develop -c githooks/pre-commit` fails with `tasks: docs/OPERATIONS.md queue block is stale — run: evidence tasks write-board`; restore with `write-board`. Record it.
- [ ] **Step 3: Green** — ruff; `nix develop -c pytest tests/evidence -q -p no:cacheprovider`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix build .#checks.x86_64-linux.lint -L --no-link`; `nix develop -c githooks/pre-commit`. `bash tools/session-start.sh | head -30` shows the generated block inside START HERE.
- [ ] **Step 4: One commit**, subject byte-identical to G8's. FACTORY-NOTES names the recovered patch's stat and the drift red.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, docs/OPERATIONS.md, githooks/pre-commit
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the board's queue block is generated by evidence tasks write-board; the hook and lint refuse drift (test: evidence-unit, lint)`

### G8c (code, S) — G8 fix round 2: the block is this repo's, derived from this tree; the hook regenerates and asks for a re-add

**dependsOn:** none (G9 on main)

Gate: `docs/reviews/2026-09-05-opus-review-sc4-G8b.md` — REJECTED. Two design faults, fixed by rule here (spec §3 amended): (1) **the committed queue block covers THIS repo only and is derived from THIS tree only** — no `repos.toml` (home paths differ per machine), no runs dir, no store; `write-board` and `check --board` both build the graph from a one-repo list `{name: <basename of --root>, path: --root}` so they cannot disagree; cross-repo and in-flight state belong to the session brief the hook prints live, not to the board; (2) **landing invalidates the block by design** (a landed key leaves the queue), so the pre-commit hook runs `write-board` first and, when the file changed, exits 1 with `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`; when unchanged it proceeds. Fresh workspace from `main`; `git fetch -q /home/dalhaka/factory/ws/sc4/G8b task/G8b && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with G8's subject.

**Files:** `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `docs/OPERATIONS.md`, `githooks/pre-commit`.

- [ ] **Step 1: Tests first.** (a) `write_board`/`board_drift` take a graph built by a new `board_graph(root)` that uses ONLY `[{"name": basename(root), "path": root, "plans": PLANS_GLOB}]`, `runs_dir=None`, `store=None` — test: with `HOME` pointed at an empty dir and a `docs/ledger/repos.toml` naming `~/elsewhere`, the block is identical to the one computed with the real HOME (mutation: read repos.toml → differs → fails). (b) `main(["--root", r, "check", "--board", b])` returns 1 with the stale message when the block is stale and 0 when current (kills M5); the check compares against `board_graph`, never the live graph with runs/store (mutation M8: compare against `build(...)` with the runs dir → the test seeds a result file that would change the live graph and asserts no drift → fails). (c) `render_board_block` header line reads `**Queued (derived from this tree; in-flight state is in the session brief).**` and lists only ready/blocked chains of this repo. (d) the existing G8 tests stay green.
- [ ] **Step 2: Hook.** In `githooks/pre-commit` replace the `check --board` flag with: `python3 pkgs/evidence/tasks.py --root . write-board --board docs/OPERATIONS.md --quiet; if ! git diff --quiet -- docs/OPERATIONS.md; then echo "tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again" >&2; exit 1; fi` (keep the existing `check` line for the graph rules). Red: dirty the block → the hook exits 1 with that message and leaves the file regenerated; `git add` → hook green. Also Step 3 acceptance: `nix develop -c githooks/pre-commit` must be GREEN on the delivered tree — regenerate the block as the last step before committing so the commit is not self-stale (the block will not list G8c: a task whose plan subject is in `git log` is landed only once merged, so at commit time in the workspace G8c's own subject IS in the log → it drops out → consistent).
- [ ] **Step 3: Board text.** In the Now paragraph restore what G8b dropped: the model-comparison plan's two measurement tasks (the `] && [` bats lint guard and the `launch-today.sh` tidy, Pro arm landed), WH1/WH2 (media becomes an input; two worlds; Caddy on eno1; two lab backup paths; a `media-refresh` tile), and say B1 is running as seat run `bk1` (paused session). ≤ 10 lines. E8's shape guard holds.
- [ ] **Step 4: Green** — ruff; `nix develop -c pytest tests/evidence -q -p no:cacheprovider`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix build .#checks.x86_64-linux.lint -L --no-link`; `nix develop -c githooks/pre-commit` (green on the tree you commit). Clean-clone proof: `git clone -q . /tmp/g8c-clone && (cd /tmp/g8c-clone && HOME=/tmp/empty-home nix develop -c githooks/pre-commit)` — wait, the clone has no devShell cache; instead run `HOME=/tmp/empty-home nix develop -c python3 pkgs/evidence/tasks.py --root /tmp/g8c-clone check --board /tmp/g8c-clone/docs/OPERATIONS.md; echo rc=$?` → 0; record it.
- [ ] **Step 5: One commit**, subject byte-identical to G8's.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, docs/OPERATIONS.md, githooks/pre-commit
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the board's queue block is generated by evidence tasks write-board; the hook and lint refuse drift (test: evidence-unit, lint)`

### G11 (code, S) — a task names the repo it runs in; withdrawn tasks come from task-status.toml

**dependsOn:** none (OG1 creates the empty `docs/ledger/task-status.toml`; if it is not on main yet, create it with the documented header — same content — and note it)

Origin: the first generated block on main (28eaef7) lists `H1 H2b PB0` as this repo's ready tasks. Their sections live in this repo's plans but they run in `~/flakes/dsh-harness` and `~/flakes/gaming`, whose histories hold their landings, so the tree-only graph can never see them land. Also: withdrawing a task must be a status row, never a heading edit (operator, 2026-09-05).

**Files:** `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `docs/ledger/task-status.toml` (rows for the two withdrawn PB sections are NOT needed — their headings are already untyped; leave the file empty apart from its header unless OG1 wrote it), the plan sections of cross-repo tasks gain one field line each: `**repo:** dsh-harness` under `### H1`, `### H2`, `### H2b` in `docs/superpowers/plans/2026-09-05-harness-router.md` and `**repo:** gaming` under `### PB0` in `docs/superpowers/plans/2026-09-05-operator-items.md` (adding a field line is allowed; never touch a heading)

**Interfaces:**
- `FIELD_RE` accepts `repo`; `task["repo"]` = the value or `None`. `scan_repo` for repo R includes: typed tasks from R's own plans whose `repo` is `None` or equals R, PLUS typed tasks from every OTHER configured repo's plans whose `repo` equals R (so H1 counts as a `dsh-harness` task, landed by `dsh-harness`'s git log, result files attributed by workspace origin `…/base/dsh-harness`). `board_graph` (repo-only mode) excludes tasks whose `repo` names another repo and cannot pull tasks from elsewhere (it has one repo) — so the board block never lists them.
- `load_task_status(path)` reads `[[task]] repo, plan, key, status = "withdrawn" | "parked", note, decided`; a matching key is state `withdrawn`/`parked`: never scheduled, never in `conflicts`, shown once in the brief under `**Withdrawn/parked:**`; `check` refuses a row naming a key that no plan defines.

- [ ] **Step 1: Failing tests** — (a) a plan in repo A with `### T1 … **repo:** B` → A's scan has no T1, B's scan has T1 and marks it landed when B's fake git log carries T1's subject; (b) `board_graph` on A shows no T1; (c) task-status row `withdrawn` for a typed key → state `withdrawn`, absent from `waves`/`conflicts`, present once in the brief; row for an unknown key → `check` error `tasks: task-status names unknown key …`; (d) G1b's and G9's tests unchanged and green.
- [ ] **Step 2: Red.** **Step 3: Implement**; add the four `**repo:**` lines; regenerate the board block (`write-board`) so H1/H2b/PB0 leave it. **Step 4: Green** — ruff; pytest; `evidence-unit`; `lint`; hook (expect the one regenerate-and-re-add step). Real data: `tasks.py --root . brief` shows H1 under dsh-harness (landed) and PB0 under gaming (ran/approved), none under nixos-agent-env. **Step 5: Commit.**

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, docs/ledger/task-status.toml, docs/superpowers/plans/2026-09-05-harness-router.md, docs/superpowers/plans/2026-09-05-operator-items.md, docs/OPERATIONS.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: a task section names the repo it runs in and is attributed there; task-status.toml withdraws or parks a task without touching plan text (test: evidence-unit, lint)`

### G12 (code, S) — the graph knows a task is running; `waves --next` is one unambiguous line

**dependsOn:** G11 (both edit tasks.py)

Origin: the FD1 gate (`docs/reviews/2026-09-05-opus-review-fd1-FD1.md`). Two facts the dispatcher needs and the graph did not give: (1) a task with a seat run in progress (a `~/factory/runs/<run>/<KEY>.log` and no `<KEY>.result`, or a `.result` younger than the log's last write) reads `ready` and gets offered again; (2) `waves` prints one seat group per line across ALL waves, so "the first line" is not the next wave.

**Files:** `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`

**Interfaces:**
- New state `running` (added to `STATES` after `ran`): `read_results` also returns, per `(repo, key)`, `{"status": "running", "run": …}` when `<KEY>.log` exists and `<KEY>.result` does not (attribution by the run dir's workspace clone origin as for results; a `.log` whose workspace is gone is ignored). Precedence: `running` sits between rule 2 (reviews) and rule 3 (results) — a member with a live log outranks an older review. `running` is never scheduled and never in `conflicts`; the brief shows `running` in its own column.
- `waves` output: default prints ONE line per wave, each line the shell-quoted groups of that wave (as today); NEW `--next` prints exactly the first wave's line and nothing else (exit 0, empty output when nothing is schedulable); NEW `--json` prints `[[["E1","R4"],["E3"]], [["D1"]]]` (waves → groups → keys). `--factory-args` unchanged.
- `check` gains nothing.

- [ ] **Step 1: Failing tests** — a result-file fixture with `K.log` and no `K.result` → state `running`, absent from `waves` and `conflicts`, counted in the brief's `running` column; `K.log` + older `K.result` → `ran`; `waves --next` on the two-wave `typed.md` fixture (E1 landed) prints exactly `"E3" "E7"` and a trailing newline, nothing else; `--json` shape asserted; `render_brief` lists a running chain under `**Running:**`. G1b/G4b/G9/G11 tests unchanged and green.
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — ruff; pytest; `evidence-unit`; `lint`; hook (one regenerate step is normal). Real data: `tasks.py --root . brief` shows whatever is on the seat right now as `running`, not `ready`. **Step 5: Commit.**

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: a task with a live seat log is running, never re-offered; waves --next prints the one next wave, --json the structure (test: evidence-unit, lint)`

### G11b (code, S) — G11 fix round: cross-repo dependencies resolve by the repo the task runs in; states and rows made exact

**dependsOn:** none (OG1's landing decides who writes `docs/ledger/task-status.toml` first — see Step 0)

Gate: `docs/reviews/2026-09-05-opus-review-sc5-G11.md` — REJECTED on the improvised cross-repo `dependsOn` (never satisfiable; untested; `check`'s namespace widened silently). The declared body (repo field, attribution, board exclusion, task-status rows) was sound and is kept. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/sc5/G11 task/G11 && git cherry-pick -n FETCH_HEAD` (resolve `docs/ledger/task-status.toml` per Step 0 and re-add the `**repo:**` lines if main already has some); read the review in full; ONE commit with G11's subject.

**Files:** `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `docs/ledger/task-status.toml`, the two plan files (only `**repo:**` lines), `docs/OPERATIONS.md` (regenerated block)

**The rule, exactly:**
- **Resolvable keys** for a task in repo R's plan files = every typed key defined in R's plan files, whatever `repo:` they name. A key defined only in another repo's own plan files is unknown (`check` error, as G4 pinned). No global namespace.
- **Satisfied** when the dependency's chain root is `landed` in the repo it is ATTRIBUTED to (its `repo:` value, else R) — i.e. resolved through that repo's `scan_repo` (git log of that repo, results attributed by that repo's base clone). Never satisfied by mere existence; never permanently blocked when that repo has it landed. `check` accepts such an edge; a self-attributed dependency behaves as today.
- `STATES` gains `withdrawn`, `parked` (after `blocked`); the brief's table gains both columns; `json` emits only `STATES` values. A task-status row: `repo` (the repo the task RUNS in — the attributed repo), `plan` (basename), `key`, `status`, `note`, `decided`; a `status` outside `withdrawn|parked` → `check` error `tasks: task-status row <key>: unknown status …`; a row naming a key no plan defines → `check` error (kept). `board_graph` passes the task-status rows so `check --board` and `write-board` see withdrawals. File ends with a newline.

- [ ] **Step 0** If `docs/ledger/task-status.toml` already exists on main (OG1 landed), keep its header and append nothing; else create it with a header documenting the six row keys. Either way the file must parse and end with a newline.
- [ ] **Step 1: Failing tests** — (a) fixture repo A with `### T9 … **repo:** B` and `### AA1 … dependsOn T9`; fake git for B has T9's subject → in A's scan `AA1` is `ready`; without it → `blocked | T9`; (b) a dependsOn naming a key defined only in B's own plan files → `check` error unknown key (mutation: global namespace → passes → fails); (c) M7b from the review (restore per-repo `check` scoping without the attribution rule) → the live-shaped fixture `PB1 → PB0(repo gaming)` fails `check` → the test must catch it; (d) a mistyped status row → `check` error; (e) withdrawn/parked counted in the brief columns and present in `STATES`; (f) `board_graph(...)["task_status"]` populated → `write-board` omits a withdrawn key; (g) `defined_roots` dead code removed (no test; note it).
- [ ] **Step 2: Red.** **Step 3: Implement**; disclose every semantic in FACTORY-NOTES. **Step 4: Green** — ruff; pytest; `evidence-unit`; `lint`; hook (one regenerate step). Real data: with the clone named as `nixos-agent-env` in a temporary repos.toml, PB1 shows `ready` (PB0 landed under gaming); `check` clean. **Step 5: One commit**, G11's subject.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, docs/ledger/task-status.toml, docs/superpowers/plans/2026-09-05-harness-router.md, docs/superpowers/plans/2026-09-05-operator-items.md, docs/OPERATIONS.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: a task section names the repo it runs in and is attributed there; task-status.toml withdraws or parks a task without touching plan text (test: evidence-unit, lint)`

### G11r (code, S) — re-plan of G11 (rule A1): one notion of "landed" for status and scheduling; the board says what it omits

**dependsOn:** none

G11 and G11b were both rejected (`docs/reviews/2026-09-05-opus-review-sc5-G11.md`, `…-G11b.md`); G11b's body is correct and is kept verbatim — this re-plan adds the design the second gate named (spec amendment 6). Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/sc5/G11b task/G11b && git cherry-pick -n FETCH_HEAD` (G11b's single commit; if G12's commit is also in that workspace's history, take ONLY G11b's: `git cherry-pick -n f10636c`); resolve `docs/ledger/task-status.toml` by taking OG1b's header (in `/home/dalhaka/factory/ws/og1/OG1b`, read-only) plus one sentence: "for a task whose section names `repo:`, the row's `repo` is that attributed repo"; mode 0644, trailing newline. ONE commit with G11's subject.

**Files:** G11b's plus nothing new: `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `docs/ledger/task-status.toml`, the two plan files (`**repo:**` lines only), `docs/OPERATIONS.md`

**The contract (in addition to G11b's "rule, exactly"):**
1. `scan_repo(R)` returns `resolved_elsewhere`: the set of chain roots that R's tasks depend on, are attributed to another configured repo, and are `landed` there. `waves`, `seat_groups` and `factory_args` compute readiness against `landed_here ∪ resolved_elsewhere` — the SAME set `derive_status` used. Test, red first: live-shaped fixture `PB1 → PB0(repo gaming)` with gaming's log carrying PB0's subject → `derive_status(PB1) == ready` AND `waves(g) == [["PB1"]]` AND `render_brief` shows PB1 in Next wave; mutation: drop the union in `waves` → the waves assertion fails while the status one passes (the exact G11b defect).
2. `board_graph(root)` (tree-only) marks a task whose `depends_on` names a key attributed elsewhere as `deferred-to-brief` — never scheduled in the block; `render_board_block`'s header line becomes `**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).**`; test: such a task is absent from the block and the header says so; mutation: include it → fails.
3. `check` refuses a `**repo:**` value not in `repos.toml`: `tasks: nixos-agent-env/T1 repo: X not in docs/ledger/repos.toml`. Test + mutation.
4. G11b MINOR 5: the `conflicts` test uses two different plans (so it can fail); MINOR 4: the kept `defined_roots` is renamed to what it is or removed — state which; MINOR 3: the row-key sentence in task-status.toml (above).

- [ ] **Step 1** cherry-pick; resolve the file; `nix develop -c pytest tests/evidence -q -p no:cacheprovider` green (G11b's 81). **Step 2** the four tests above, red first (record). **Step 3** implement. **Step 4** ruff; pytest; `evidence-unit`; `lint`; hook (one regenerate). Real data with a temporary repos.toml naming the clone: PB1 `landed` (its subject is on main now); `write-board` on the clone omits any deferred task and the header carries the new sentence; `check` clean. **Step 5** ONE commit.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, docs/ledger/task-status.toml, docs/superpowers/plans/2026-09-05-harness-router.md, docs/superpowers/plans/2026-09-05-operator-items.md, docs/OPERATIONS.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: a task section names the repo it runs in and is attributed there; task-status.toml withdraws or parks a task without touching plan text (test: evidence-unit, lint)`

### G12b (code, S) — G12 fix round on top of G11r: running is per key and only while the log is live

**dependsOn:** G11r (chained: G12 was built on G11b, which G11r replaces)

Gate: `docs/reviews/2026-09-05-opus-review-sc5-G12.md` — REJECTED: (1) result suppression keyed by `(run_dir, key)`, so an older run's `.log` beats a newer run's `.result` and the key reads `running` forever; (2) the "absent from conflicts" assertion cannot fail; minors: the live-log-outranks-older-review chain rule unpinned; empty `--next` unpinned; no liveness notion (after the host rebooted, 11 dead keys read `running`). Fresh workspace from main WITH G11r landed; `git fetch -q /home/dalhaka/factory/ws/sc5/G12 task/G12 && git cherry-pick -n 9df4ef3` (G12's single commit; resolve tasks.py against G11r's changes keeping both); ONE commit with G12's subject.

**Files:** `pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`

**Contract (replaces G12's where they differ):**
- `read_results` returns ONE entry per `(repo, key)`: the newest by run-dir mtime across ALL runs; a `.log` without `.result` in run R counts as `running` ONLY if no newer run has a `.result` for that key AND the log's mtime is younger than `--stale-after` seconds (default 7200; CLI flag and env `TASKS_STALE_AFTER`); an older log is ignored (the key falls to rules 3–5 — a killed run is schedulable again). A `.log` with a `.result` in the same run → the result (`ran`).
- Tests, red first: (a) `r1/K1.log` (old mtime) + `r2/K1.result` → `ran`; (b) `r1/K1.log` fresh, no result anywhere → `running`; (c) `r1/K1.log` older than `stale_after` → not running (`ready`); (d) two-plan fixture with a running task whose `touches` overlap another's → absent from `conflicts` (mutation: schedule/conflict running → FAILS); (e) root REJECTED review + fix-round member with a fresh log → root `running` (mutation: rank running below reviews → fails); (f) `--next` with nothing schedulable prints zero bytes (mutation: blank line → fails); (g) G11r's `waves` union still honoured for a running-elsewhere dependency? — a dependency that is `running` in its attributed repo is NOT satisfied (test).
- Everything else from G12 kept (`STATES`, brief column, `--json`).

- [ ] **Step 1** cherry-pick + resolve; **Step 2** tests red; **Step 3** implement; **Step 4** ruff; pytest; `evidence-unit`; `lint`; hook (one regenerate). Real data: `brief` shows only the runs alive now as running (compare with `pgrep -af factory-task`); parked `.log.killed-by-reboot-*` files are not read (the glob is `<KEY>.log` exactly). **Step 5** ONE commit, G12's subject.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, docs/OPERATIONS.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: a task with a live seat log is running, never re-offered; waves --next prints the one next wave, --json the structure (test: evidence-unit, lint)`

Note for G12b (from the G11r gate, MAJOR 2 latent): an imported task (`**repo:** B` defined in A's plans) that `dependsOn` a key local to A currently reads `blocked` forever and `check` reports it unknown — resolve an imported task's `depends_on` against its DEFINING repo's `resolvable_roots` (landing still judged where the dependency is attributed). Add the fixture (`X1 repo B dependsOn L1; L1 landed in A → X1 ready; check clean`) and its mutation to G12b's Step 1; `deferred-to-brief` joins `STATES`.

### G12r (code, S) — re-plan of G12 (rule A1): satisfaction is keyed by (repo, chain root), never a bare key

**dependsOn:** none (G11r on main)

Gate `docs/reviews/2026-09-05-opus-review-sc8-G12b.md`: everything in G12b is correct except one regression — `extra_landed.add(droot)` with a BARE root lets repo A's landed `L1` satisfy repo B's unrelated `L1`. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/sc8/G12b task/G12b && git cherry-pick -n FETCH_HEAD`; keep everything else verbatim; ONE commit with G12's subject.

**Contract:** the satisfied set handed to `derive_status`, `waves`, `seat_groups`, `factory_args` is a set of `(repo, chain_root)` pairs. A task's `depends_on` keys are resolved in its DEFINING repo's namespace (an imported task `X1 (repo B)` defined in A resolves `L1` to A's `L1`); landing is judged in the ATTRIBUTED repo of the resolved dependency; `extra_landed`/`resolved_elsewhere` never receive a root the current repo defines locally. Test (red first on G12b): repo A lands its own `L1` and defines `X1 (**repo:** B, dependsOn L1)`; repo B defines its own unlanded `L1` and `BL (dependsOn L1)` → `BL blocked`, `waves(B) == [["L1"], ["BL", "X1"]]` (mutation: flat set → `BL ready` → fails). Minors folded: a malformed `TASKS_STALE_AFTER` → `check` error message, not a crash; a `.result` whose block says `status=running` is `ran`, not a live log; the `imported` map documented in the module docstring; rule 3 reachability stated (a stale newest log does not discard an older run's `.result` — the newest `.result` wins).

- [ ] **Step 1** cherry-pick; **Step 2** the test above red; **Step 3** implement; **Step 4** ruff; pytest; `evidence-unit`; `lint`; hook (one regenerate); real data: `brief` running column matches `pgrep -af factory-task`; `--next` on the plan-writing plan prints zero bytes; **Step 5** ONE commit, G12's subject.

**touches:** pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, docs/OPERATIONS.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: a task with a live seat log is running, never re-offered; waves --next prints the one next wave, --json the structure (test: evidence-unit, lint)`
