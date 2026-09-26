"""Derived task graph: plans are the nodes and edges, status is a derivation (plan 2026-09-05-session-context, G1/G4).

The dependency-satisfaction set handed to `derive_status` and `waves` is a set
of `(repo, chain_root)` pairs, never a bare root: a task's `depends_on` keys are
resolved in the namespace of the repo that DEFINES the task (a local task ->
this repo; an imported task -> its defining repo), and "landed" is judged in the
repo the resolved dependency is ATTRIBUTED to. Each task carries a `dep_repo`
map (`chain root -> attributed repo`) so `derive_status` and `waves` can key
satisfaction without leaking one repo's landed root into another repo's
same-named local key.

`scan_repo` publishes two namespace maps consumed by `check` and by the
scheduler: `imported` (`task key -> defining repo`, for tasks another repo's
plan files attribute here) and `resolved_elsewhere` (the `(repo, chain_root)`
pairs this repo's tasks depend on that are landed in another repo — never a
root this repo itself defines locally).

`read_results` returns ONE entry per `(repo, key)`: a live `.log` counts as
`running` only while it is stale-free and newer than any `.result`; otherwise
the newest `.result` wins (rule 3 stays reachable — a stale newest log does not
discard an older run's `.result`)."""

from __future__ import annotations

import argparse
import datetime
import difflib
import fnmatch
import glob
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import tomllib

HEADING_RE = re.compile(
    r"^### (?P<key>[A-Za-z][A-Za-z0-9-]*) \((?P<kind>code|docs), (?P<size>XS|S|M|L)\) [—-] (?P<title>.+)$"
)
FIELD_RE = re.compile(
    r"^\*\*(?P<name>dependsOn|touches|acceptance|repo|commit subject):\*\*\s*(?P<value>.*)$"
)
KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
CHAIN_RE = re.compile(r"^(?P<root>.*\d)(?P<suffix>[a-z]{1,2})$")
STATES = (
    "landed",
    "approved",
    "rejected",
    "ran",
    "running",
    "recorded",
    "ready",
    "blocked",
    "deferred-to-brief",
    "withdrawn",
    "parked",
)
LEGACY_STATES = ("done", "superseded", "parked", "open")
REVIEW_RE = re.compile(
    r"^# Opus gate — seat run (?P<run>\S+), task (?P<key>\S+) — (?P<verdict>APPROVED|REJECTED)"
)
PLAN_DEFECT_ENUM = (
    "none",
    "vacuous",
    "missing-case",
    "underspecified",
    "wrong-fact",
    "implementer",
    "process",
)
PLAN_DEFECT_CAUSED = ("vacuous", "missing-case", "underspecified", "wrong-fact")
PLAN_DEFECT_SHORT = {
    "vacuous": "vac",
    "missing-case": "miss",
    "underspecified": "under",
    "wrong-fact": "fact",
}
DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")

DEFAULT_RUNS_DIR = os.path.expanduser("~/factory/runs")
DEFAULT_STALE_AFTER = 7200
PLANS_GLOB = "docs/superpowers/plans/*.md"
BEGIN, END = "<!-- tasks:begin -->", "<!-- tasks:end -->"


def run(argv, timeout=20.0):
    """The one subprocess seam (tests pass a fake)."""
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


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
    in_fence = False
    for line in path.read_text().splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## ") or (
            line.startswith("### ") and not HEADING_RE.match(line)
        ):
            cur = None  # a section that is not a typed task ends the current one
        m = HEADING_RE.match(line)
        if m:
            cur = {
                "key": m["key"],
                "kind": m["kind"],
                "size": m["size"],
                "title": m["title"].strip(),
                "depends_on": [],
                "touches": [],
                "acceptance": [],
                "repo": None,
                "commit_subject": None,
                "body": "",
                "plan": path.name,
            }
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
            elif name == "repo":
                cur["repo"] = value.strip("`").strip() or None
            else:
                cur["commit_subject"] = value.strip("`").strip()
            continue
        cur["body"] += line + "\n"
    return {"file": path.name, "path": str(path), "typed": bool(tasks), "tasks": tasks}


def load_repos(path):
    if not pathlib.Path(path).exists():
        return []
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return [
        {
            "name": r["name"],
            "path": os.path.expanduser(r["path"]),
            "plans": r.get("plans", PLANS_GLOB),
        }
        for r in data.get("repo", [])
    ]


def load_plan_status(path):
    if not pathlib.Path(path).exists():
        return {}
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return {
        (p["repo"], p["file"]): {"status": p["status"], "note": p.get("note", "")}
        for p in data.get("plan", [])
    }


def load_task_status(path):
    if not pathlib.Path(path).exists():
        return {}
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return {
        (p["repo"], p["plan"], p["key"]): {
            "status": p["status"],
            "note": p.get("note", ""),
            "decided": p.get("decided", ""),
        }
        for p in data.get("task", [])
    }


def landed_subjects(repo_path, run=None):
    runner = run or globals()["run"]
    try:
        r = runner(["git", "-C", repo_path, "log", "--format=%s"], timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    if r.returncode != 0:
        return set()
    return {line for line in r.stdout.splitlines() if line.strip()}


def _split_front_matter(lines):
    """Split a review file's lines into (has_block, block, first, lookahead).
    A block is a leading `---` line closed by a later `---`; `block` maps its
    keys to values, `first` is the line immediately after the block ("" if
    none) and `lookahead` the next two lines (the H1 may follow within three
    lines of the block). A file without a block reads `first = lines[0]` and
    `lookahead = ()` — its H1 is `first`."""
    if not lines:
        return False, {}, "", ()
    if lines[0].strip() != "---":
        return False, {}, lines[0], ()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            block = {}
            for ln in lines[1:i]:
                if ":" in ln:
                    key, _, value = ln.partition(":")
                    block[key.strip()] = value.strip()
            first = lines[i + 1] if i + 1 < len(lines) else ""
            lookahead = tuple(lines[i + 2 : i + 4])
            return True, block, first, lookahead
    return False, {}, lines[0], ()


def _read_review(path):
    """Read a review file into the 4-tuple (has_block, block, first, lookahead):
    `has_block` is a bool, `block` a dict of the front-matter key/value lines,
    `first` the line immediately after the block (or the file's first line when
    it has no block), and `lookahead` the two lines after `first` (the H1 may
    fall within three lines of the block). An unreadable file reads as no-block:
    (False, {}, "", ())."""
    try:
        lines = pathlib.Path(path).read_text().splitlines()
    except OSError:
        return False, {}, "", ()
    return _split_front_matter(lines)


def _review_h1(first, lookahead):
    """The `# Opus gate …` H1 match over `first` then the two lookahead lines
    (a block's H1 may fall within three lines), or None."""
    m = REVIEW_RE.match(first)
    if m is not None:
        return m
    for ln in lookahead:
        m = REVIEW_RE.match(ln)
        if m is not None:
            return m
    return None


def _review_date(name):
    """The YYYY-MM-DD prefix of a review basename as a datetime.date, or None
    when the basename has no valid date prefix."""
    m = DATE_PREFIX_RE.match(name)
    if m is None:
        return None
    try:
        return datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def read_reviews(repo_path):
    out = {}
    d = pathlib.Path(repo_path) / "docs" / "reviews"
    if not d.is_dir():
        return out
    for path in sorted(d.glob("*opus-review*.md")):
        _, _, first, lookahead = _read_review(path)
        m = _review_h1(first, lookahead)
        if m:
            out[m["key"]] = {
                "verdict": m["verdict"],
                "run": m["run"],
                "file": path.name,
            }
    return out


def _field(text, pattern):
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _repo_from_workspace(workspace):
    """The repo name a workspace clone's origin points at (…/base/<name>), or
    None when the workspace is gone or its origin does not match that shape."""
    cfg = pathlib.Path(workspace) / ".git" / "config"
    try:
        ctext = cfg.read_text()
    except OSError:
        return None
    um = re.search(r"url\s*=\s*(.+)", ctext)
    if not um:
        return None
    m = re.search(r"/base/([^/\s]+)$", um.group(1).strip())
    return m.group(1) if m else None


def read_results(runs_dir, stale_after=DEFAULT_STALE_AFTER):
    """ONE entry per (repo, key): a `.log` counts as `running` only when a newer
    run holds no `.result` for that key AND the log's own mtime is younger than
    `stale_after` seconds. A stale (dead) log is ignored, so the key falls
    through to rules 3-5 — the newest `.result` still wins, even from an older
    run dir (rule 3 stays reachable). A `.log` beside a `.result` in the same
    run is the result (the seat finished)."""
    out = {}
    runs_root = str(runs_dir)
    now = time.time()
    # (repo, key) -> (run_dir_mtime, payload): the newest result and the newest
    # log, tracked separately so a stale newer log never discards an older one's
    # genuine result.
    newest_result = {}
    newest_log = {}

    def keep(target, key, run_mtime, payload):
        if key not in target or run_mtime > target[key][0]:
            target[key] = (run_mtime, payload)

    for p in glob.glob(os.path.join(runs_root, "*", "*.result")):
        try:
            text = pathlib.Path(p).read_text()
        except OSError:
            continue
        status = _field(text, r"FACTORY-RESULT status=(\S+)")
        run_name = _field(text, r"^run:\s*(.+)$")
        key = _field(text, r"^key:\s*(.+)$")
        workspace = _field(text, r"^workspace:\s*(.+)$")
        if not (status and key and workspace):
            continue
        repo = _repo_from_workspace(workspace)
        if not repo:
            continue
        run_mtime = os.path.getmtime(os.path.dirname(p))
        keep(
            newest_result,
            (repo, key),
            run_mtime,
            {"status": status, "run": run_name, "file": p},
        )

    for p in glob.glob(os.path.join(runs_root, "*", "*.log")):
        run_dir = os.path.dirname(p)
        key = os.path.basename(p)[: -len(".log")]
        run_name = os.path.basename(run_dir)
        # the seat logs under <ws>/<run>/<key>; its workspace clone's origin
        # attributes the repo, exactly as for results. A missing workspace makes
        # the log non-evidence.
        workspace = os.path.join(os.path.dirname(runs_root), "ws", run_name, key)
        repo = _repo_from_workspace(workspace)
        if not repo:
            continue
        run_mtime = os.path.getmtime(run_dir)
        payload = {"run": run_name, "log_mtime": os.path.getmtime(p)}
        keep(newest_log, (repo, key), run_mtime, payload)

    for key in set(newest_result) | set(newest_log):
        result = newest_result.get(key)
        log = newest_log.get(key)
        log_fresh = log is not None and now - log[1]["log_mtime"] < stale_after
        log_newer = log is not None and (result is None or log[0] > result[0])
        if log is not None and log_newer and log_fresh:
            out[key] = {"status": "running", "run": log[1]["run"]}
        elif result is not None:
            out[key] = result[1]
        elif log_fresh:
            out[key] = {"status": "running", "run": log[1]["run"]}
        # else: stale log, no result — no entry; the key falls to rules 3-5.
    return out


def read_recorded(store):
    try:
        import evidence
    except ImportError:
        return {}
    try:
        rows = evidence.read(store, "runs")
        out = {}
        for row in rows:
            plan = os.path.basename(row.get("plan", "") or "")
            for t in row.get("tasks", []) or []:
                key = t.get("key")
                if key:
                    out[(plan, key)] = t.get("status", "recorded")
        return out
    except Exception:  # noqa: BLE001 - a malformed external run row degrades to {}
        return {}


def _chain_members(key, reviews, results, running=None):
    root = chain_root(key)
    running = running or {}
    members = {key}
    for k in set(reviews) | set(results) | set(running):
        if chain_root(k) == root:
            members.add(k)
    return sorted(members, key=lambda k: (k != root, k))


def derive_status(
    task,
    landed,
    reviews,
    results,
    recorded,
    landed_keys,
    extra_landed=None,
    running=None,
    repo=None,
):
    key = task["key"]
    root = chain_root(key)
    running = running or {}
    members = _chain_members(key, reviews, results, running)
    last = members[-1]  # root first, then by suffix: the last member owns rules 2-4

    # 1. landed
    if task["commit_subject"] in landed:
        return ("landed", task["commit_subject"])
    if (
        any(k in reviews or k in results or k in running for k in members)
        and root in landed_keys
    ):
        return ("landed", root)

    # 2. approved / rejected — the last member's own review
    if last in reviews:
        info = reviews[last]
        return (info["verdict"].lower(), f"{last} by {info['run']}")

    # 2.5 running — the last member's live seat log (outranks a stale result,
    # never outranks its own review)
    if last in running:
        info = running[last]
        return ("running", f"{last} run={info['run']}")

    # 3. ran — the last member's own result
    if last in results:
        info = results[last]
        return ("ran", f"{last} status={info['status']} run={info['run']}")

    # 4. recorded — the last member's own record
    if last in recorded:
        return ("recorded", recorded[last])

    # 5. ready / blocked — by the root's dependencies. Satisfaction is keyed by
    # (repo, chain root): a dependency whose chain root resolves locally (to
    # this repo) is satisfied iff it is in `landed_keys`; one attributed to
    # another repo is satisfied iff that (repo, root) pair is in `extra_landed`.
    # `dep_repo` maps each dependency's chain root to the repo it is attributed
    # to in the task's defining namespace; when absent (direct callers) fall
    # back to the bare-root sets, exactly as before.
    dep_repo = task.get("dep_repo") or {}
    resolved_elsewhere = extra_landed or set()
    missing = []
    for d in task["depends_on"]:
        root = chain_root(d)
        if repo is not None:
            target = dep_repo.get(root, repo)
            if target == repo:
                satisfied = root in landed_keys
            else:
                satisfied = (target, root) in resolved_elsewhere
        else:
            satisfied = root in (set(landed_keys) | resolved_elsewhere)
        if not satisfied:
            missing.append(d)
    if missing:
        return ("blocked", ", ".join(missing))
    return ("ready", "")


def scan_repo(
    repo,
    plan_status,
    runs_dir,
    store,
    run=None,
    repos=None,
    task_status=None,
    stale_after=DEFAULT_STALE_AFTER,
):
    repos = repos or [repo]
    task_status = task_status or {}
    repo_path = repo["path"]
    plans_glob = os.path.join(repo_path, repo["plans"])
    tasks, legacy, untracked = [], [], []
    # chain root -> the repo its task runs in (None means this repo), for every
    # typed key in this repo's own plan files. Kept whole (including `repo:`
    # redirects) because a `dependsOn` may only name keys defined in this
    # repo's own plans, whatever repo they are attributed to.
    defined = {}
    # chain root -> the set of commit subjects of every member, so a cross-repo
    # dependency resolves "landed in its attributed repo" against that repo's
    # git log rather than this one's.
    root_subjects = {}
    repo_by_name = {r["name"]: r for r in repos}
    # (task key, `repo:` value) for every task this repo's plans attribute to a
    # different repo, so `check` can refuse a value `repos.toml` does not
    # configure (a typo) instead of letting the task vanish from every graph.
    attributed = []

    def own_plan_tasks(plan):
        return [t for t in plan["tasks"] if t["repo"] in (None, repo["name"])]

    for path in sorted(glob.glob(plans_glob)):
        plan = parse_plan(path)
        if plan["typed"]:
            for t in plan["tasks"]:
                root = chain_root(t["key"])
                defined.setdefault(root, t["repo"])
                root_subjects.setdefault(root, set()).add(t["commit_subject"])
                if t["repo"] not in (None, repo["name"]):
                    attributed.append((t["key"], t["repo"]))
            tasks.extend(own_plan_tasks(plan))
        else:
            row = plan_status.get((repo["name"], plan["file"]))
            if row:
                legacy.append(
                    {
                        "file": plan["file"],
                        "status": row["status"],
                        "note": row.get("note", ""),
                    }
                )
            else:
                untracked.append(plan["file"])

    # tasks defined in OTHER configured repos' plans whose `repo` field names
    # this one run here and land here (cross-repo attribution). Each imported
    # task remembers its DEFINING repo (so `check` can resolve its `dependsOn`
    # against that repo's resolvable roots) and the defining repo's definitions
    # are kept for cross-repo landing resolution (MAJOR 2).
    imported = {}
    foreign_defined = {}
    foreign_subjects = {}
    for other in repos:
        if other["name"] == repo["name"]:
            continue
        od, osub = {}, {}
        other_glob = os.path.join(other["path"], other["plans"])
        for path in sorted(glob.glob(other_glob)):
            plan = parse_plan(path)
            if plan["typed"]:
                for t in plan["tasks"]:
                    root = chain_root(t["key"])
                    od.setdefault(root, t["repo"])
                    osub.setdefault(root, set()).add(t["commit_subject"])
                    if t["repo"] == repo["name"]:
                        tasks.append(t)
                        imported[t["key"]] = other["name"]
        foreign_defined[other["name"]] = od
        foreign_subjects[other["name"]] = osub

    landed = landed_subjects(repo_path, run=run)
    reviews = read_reviews(repo_path)
    results = {}
    running = {}
    for (name, k), v in read_results(runs_dir, stale_after).items():
        if name != repo["name"]:
            continue
        # a live log is the entries read_results synthesises without a `file`;
        # a `.result` (including one whose block says `status=running`) always
        # carries `file` and is the seat's final result (`ran`).
        if "file" in v:
            results[k] = v
        else:
            running[k] = v
    recorded_all = read_recorded(store)

    # first pass: chain roots whose subject is landed
    landed_keys = {chain_root(t["key"]) for t in tasks if t["commit_subject"] in landed}

    # cross-repo resolution: a dependency whose chain root is attributed to
    # another repo is satisfied iff that repo's graph has it landed. Resolved
    # through that repo's own git log (results attributed by its base clone),
    # never by mere existence, so the edge never stays blocked once the
    # attributed repo lands the target. Keyed by (repo, chain root) — never a
    # bare root — so one repo's landed root cannot satisfy another repo's
    # same-named local key.
    extra_landed = set()
    landed_cache = {}

    def cached_landed(path):
        if path not in landed_cache:
            landed_cache[path] = landed_subjects(path, run=run)
        return landed_cache[path]

    for root, target in defined.items():
        if target is None or target == repo["name"]:
            continue
        tgt = repo_by_name.get(target)
        if tgt is None:
            continue  # names an unconfigured repo: stays blocked, not satisfied
        if root_subjects[root] & cached_landed(tgt["path"]):
            extra_landed.add((target, root))

    # imported tasks: a `dependsOn` resolves against the DEFINING repo's
    # definitions, and landing is judged where the dependency is attributed
    # there (its `repo:` in the defining repo, defaulting to the defining repo).
    # A dependency attributed back to THIS repo is judged locally (landed_keys),
    # so it is never published in `resolved_elsewhere`.
    for t in tasks:
        defining = imported.get(t["key"])
        if defining is None:
            continue
        od = foreign_defined.get(defining, {})
        osub = foreign_subjects.get(defining, {})
        for d in t["depends_on"]:
            droot = chain_root(d)
            target = od.get(droot)
            if target is None:
                target = defining
            if target == repo["name"]:
                continue  # judged locally, never "elsewhere"
            tgt = repo_by_name.get(target)
            if tgt is None:
                continue
            if osub.get(droot, set()) & cached_landed(tgt["path"]):
                extra_landed.add((target, droot))

    # Per-task dependency attribution: resolve each task's `depends_on` in its
    # DEFINING repo's namespace (a local task -> this repo; an imported task ->
    # its defining repo), mapping each chain root to the repo it is attributed
    # to. `derive_status` and `waves` use this to key satisfaction by
    # (repo, chain root).
    for t in tasks:
        defining = imported.get(t["key"], repo["name"])
        namespace = (
            defined if defining == repo["name"] else foreign_defined.get(defining, {})
        )
        dep_repo = {}
        for d in t["depends_on"]:
            root = chain_root(d)
            target = namespace.get(root)
            dep_repo[root] = defining if target is None else target
        t["dep_repo"] = dep_repo

    # chains: root -> ordered member keys
    chains = {}
    for t in tasks:
        root = chain_root(t["key"])
        if root not in chains:
            chains[root] = _chain_members(t["key"], reviews, results, running)

    # second pass: derive each task's state
    for t in tasks:
        recorded = {k: v for (f, k), v in recorded_all.items() if f == t["plan"]}
        state, detail = derive_status(
            t,
            landed,
            reviews,
            results,
            recorded,
            landed_keys,
            extra_landed,
            running,
            repo["name"],
        )
        t["state"] = state
        t["detail"] = detail
        t["chain"] = chains[chain_root(t["key"])]

    # a task-status row withdraws/parks a key regardless of derived state:
    # never scheduled, never conflicting, shown once in the brief.
    for t in tasks:
        row = task_status.get((repo["name"], t["plan"], t["key"]))
        if row and row["status"] in ("withdrawn", "parked"):
            t["state"] = row["status"]
            t["detail"] = row.get("note", "")

    attributed_elsewhere = sorted(
        root for root, target in defined.items() if target not in (None, repo["name"])
    )
    return {
        "name": repo["name"],
        "path": repo_path,
        "tasks": tasks,
        "chains": chains,
        "resolvable_roots": sorted(defined),
        "resolved_elsewhere": sorted(extra_landed),
        "attributed_elsewhere": attributed_elsewhere,
        "attributed": sorted(attributed),
        "imported": imported,
        "legacy": legacy,
        "untracked_plans": untracked,
    }


def build(root, runs_dir, store, run=None, stale_after=DEFAULT_STALE_AFTER):
    repos_path = os.path.join(root, "docs", "ledger", "repos.toml")
    status_path = os.path.join(root, "docs", "ledger", "plan-status.toml")
    task_status_path = os.path.join(root, "docs", "ledger", "task-status.toml")
    repos = load_repos(repos_path)
    plan_status = load_plan_status(status_path)
    task_status = load_task_status(task_status_path)
    return {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "repos": [
            scan_repo(
                r,
                plan_status,
                runs_dir,
                store,
                run=run,
                repos=repos,
                task_status=task_status,
                stale_after=stale_after,
            )
            for r in repos
        ],
        "configured_repos": [r["name"] for r in repos],
        "task_status": task_status,
    }


def board_graph(root, run=None):
    """The board's queue graph: THIS repo, THIS tree only. No repos.toml (home
    paths differ per machine), no runs dir, no store — so `write-board` and
    `check --board` derive the block identically anywhere, including a clean
    clone. The one repo's name is the tree's basename; the rendered block
    omits it (the header already says "this tree")."""
    root = os.path.abspath(root)
    repo = {
        "name": os.path.basename(root) or "repo",
        "path": root,
        "plans": PLANS_GLOB,
    }
    task_status = load_task_status(
        os.path.join(root, "docs", "ledger", "task-status.toml")
    )
    repo_graph = scan_repo(
        repo, {}, None, None, run=run, repos=[repo], task_status=task_status
    )
    # Tree-only: a task whose dependsOn names a key attributed to another repo
    # can't be scheduled here (this tree never sees that repo's landing), so it
    # is deferred to the session brief rather than left `blocked` forever.
    attributed_elsewhere = set(repo_graph.get("attributed_elsewhere", ()))
    for t in repo_graph["tasks"]:
        if t["state"] in ("ready", "blocked") and any(
            chain_root(d) in attributed_elsewhere for d in t["depends_on"]
        ):
            t["state"] = "deferred-to-brief"
            t["detail"] = ""
    return {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "repos": [repo_graph],
        "task_status": task_status,
    }


def touches_overlap(a, b):
    """Two touches conflict when equal, glob-matching either way, or one is
    a directory prefix of the other."""
    a, b = a.rstrip("/"), b.rstrip("/")
    return (
        a == b
        or fnmatch.fnmatch(a, b)
        or fnmatch.fnmatch(b, a)
        or a.startswith(b + "/")
        or b.startswith(a + "/")
    )


def open_tasks(repo_graph):
    """Tasks not yet dispatched: ready or blocked. Approved/rejected/ran/
    recorded tasks are in flight and are never re-scheduled."""
    return [t for t in repo_graph["tasks"] if t["state"] in ("ready", "blocked")]


def waves(repo_graph, plan=None):
    """Kahn layers of the open tasks. Deps outside the filter count as
    satisfied only when landed; an unknown or blocked dep never schedules."""
    name = repo_graph["name"]
    local_landed = {
        chain_root(t["key"]) for t in repo_graph["tasks"] if t["state"] == "landed"
    }
    # The SAME (repo, chain root) set derive_status used: chain roots landed in
    # the repo they are attributed to (cross-repo resolution), so a dependent
    # whose edge resolved to `ready` also enters a wave instead of silently
    # dropping out. Each task's `dep_repo` maps a dep's chain root to the repo
    # it is attributed to, so one repo's landed root never satisfies another
    # repo's same-named local key.
    resolved_elsewhere = {
        (repo, root) for repo, root in repo_graph.get("resolved_elsewhere", ())
    }
    nodes = {
        t["key"]: t for t in open_tasks(repo_graph) if plan is None or t["plan"] == plan
    }
    deps = {}
    for k, t in nodes.items():
        pending = set()
        dep_repo = t.get("dep_repo") or {}
        for d in t["depends_on"]:
            root = chain_root(d)
            target = dep_repo.get(root, name)
            if target == name:
                satisfied = root in local_landed
            else:
                satisfied = (target, root) in resolved_elsewhere
            if not satisfied:
                pending.add(root)
        deps[k] = pending
    out, done = [], set()
    while True:
        ready = sorted(
            k for k in nodes if k not in done and all(d in done for d in deps[k])
        )
        if not ready:
            break
        out.append(ready)
        done.update(ready)
    return out


def seat_group_lists(repo_graph, wave):
    """Merge a wave's keys whose touches overlap into lists of keys, groups
    sorted by first key. Shared by seat_groups (quoted) and wave_structure."""
    keys = sorted(wave)
    by_key = {t["key"]: t for t in repo_graph["tasks"]}
    parent = list(range(len(keys)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ti, tj = by_key[keys[i]]["touches"], by_key[keys[j]]["touches"]
            if any(touches_overlap(pi, pj) for pi in ti for pj in tj):
                union(i, j)

    merged = {}
    for i, key in enumerate(keys):
        merged.setdefault(find(i), []).append(key)
    return sorted((sorted(m) for m in merged.values()), key=lambda m: m[0])


def seat_groups(repo_graph, wave):
    """Merge a wave's keys whose touches overlap; render each group as a
    double-quoted, space-joined string, groups sorted by first key."""
    return [
        '"' + " ".join(members) + '"' for members in seat_group_lists(repo_graph, wave)
    ]


def wave_lines(repo_graph, plan=None):
    """One shell-quoted line per wave (the waves command's default, and the
    source of its --next line)."""
    return [" ".join(seat_groups(repo_graph, w)) for w in waves(repo_graph, plan=plan)]


def wave_structure(repo_graph, plan=None):
    """waves -> groups -> keys (unquoted): the waves command's --json shape."""
    return [seat_group_lists(repo_graph, w) for w in waves(repo_graph, plan=plan)]


def factory_args(repo_graph, plan):
    """The tasks[] JSON `tools/factory/dark-factory.js` takes for the open
    tasks of one plan."""
    out = []
    for t in open_tasks(repo_graph):
        if t["plan"] != plan:
            continue
        out.append(
            {
                "key": t["key"],
                "title": t["title"],
                "kind": t["kind"],
                "checks": t["acceptance"],
                "spec": t["body"].strip(),
                "dependsOn": t["depends_on"],
                "touches": t["touches"],
            }
        )
    return out


def conflicts(repo_graph):
    """Open tasks in different plans of one repo whose touches overlap;
    one row per overlapping path pair."""
    rows = []
    for i, a in enumerate(open_tasks(repo_graph)):
        for b in open_tasks(repo_graph)[i + 1 :]:
            if a["plan"] == b["plan"]:
                continue
            for pa in a["touches"]:
                for pb in b["touches"]:
                    if touches_overlap(pa, pb):
                        first, second = (a, b) if a["key"] < b["key"] else (b, a)
                        rows.append(
                            {
                                "a": first["key"],
                                "plan_a": first["plan"],
                                "b": second["key"],
                                "plan_b": second["plan"],
                                "path_a": pa if first is a else pb,
                                "path_b": pb if first is a else pa,
                            }
                        )
    return rows


def _find_cycles(repo):
    roots = {chain_root(t["key"]) for t in repo["tasks"]}
    edges = {}
    for t in repo["tasks"]:
        r = chain_root(t["key"])
        for d in t["depends_on"]:
            dr = chain_root(d)
            if dr in roots and dr != r:
                edges.setdefault(r, set()).add(dr)
    color = {r: 0 for r in roots}  # 0 white, 1 gray, 2 black
    cycles, stack = [], []

    def dfs(u):
        color[u] = 1
        stack.append(u)
        for v in sorted(edges.get(u, ())):
            if color[v] == 1:
                cycles.append(stack[stack.index(v) :] + [v])
            elif color[v] == 0:
                dfs(v)
        stack.pop()
        color[u] = 2

    for r in sorted(roots):
        if color[r] == 0:
            dfs(r)
    return cycles


def _plan_defects_for(repo_path):
    """Load a repo's plan-defect ledger. (front_matter_from, rows) where
    front_matter_from is a datetime.date or None and rows the `[[rejection]]`
    list; (None, []) when the file is absent; None when the file is present
    but unreadable or unparseable."""
    path = pathlib.Path(repo_path) / "docs" / "ledger" / "plan-defects.toml"
    if not path.is_file():
        return (None, [])
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    meta = data.get("meta", {})
    return (meta.get("front_matter_from"), data.get("rejection", []))


def _review_defect_errors(repo_path):
    """The check rule over one repo's reviews and plan-defect ledger."""
    errors = []
    rp = pathlib.Path(repo_path)
    loaded = _plan_defects_for(str(rp))
    if loaded is None:
        errors.append(
            f"tasks: plan-defects: {rp / 'docs' / 'ledger' / 'plan-defects.toml'} "
            "unreadable"
        )
        return errors
    fmf, rows = loaded
    enum_str = " | ".join(PLAN_DEFECT_ENUM)
    reviews_dir = rp / "docs" / "reviews"
    if reviews_dir.is_dir():
        for path in sorted(reviews_dir.glob("*opus-review*.md")):
            name = path.name
            date = _review_date(name)
            has_block, block, first, lookahead = _read_review(path)
            if not has_block and fmf is not None and date is not None and date >= fmf:
                errors.append(
                    f"tasks: review {name}: no front-matter block "
                    f"(plan_defect is required from {fmf.isoformat()})"
                )
            if has_block:
                if REVIEW_RE.match(first) is None:
                    errors.append(f"tasks: review {name}: the H1 must follow the block")
                for key in ("mutants_total", "mutants_killed", "mutants_outside_named"):
                    raw = block.get(key)
                    if raw is None:
                        continue
                    if re.fullmatch(r"[0-9]+", raw) is None:
                        errors.append(f"tasks: review {name}: {key} must be an integer")
                pd = block.get("plan_defect")
                pds = block.get("plan_defect_secondary")
                if pd is None:
                    errors.append(f"tasks: review {name}: plan_defect missing")
                elif pd not in PLAN_DEFECT_ENUM:
                    errors.append(
                        f"tasks: review {name}: plan_defect {pd} not in {enum_str}"
                    )
                else:
                    m = _review_h1(first, lookahead)
                    if m is not None and m["verdict"] == "REJECTED" and pd == "none":
                        errors.append(
                            f"tasks: review {name}: a rejection names its cause"
                        )
                if pds is not None:
                    if pds not in PLAN_DEFECT_ENUM:
                        errors.append(
                            f"tasks: review {name}: plan_defect_secondary {pds} "
                            f"not in {enum_str}"
                        )
                    elif pds == pd:
                        errors.append(
                            f"tasks: review {name}: plan_defect_secondary equals plan_defect"
                        )
                m = _review_h1(first, lookahead)
                if m is not None and m["verdict"] == "APPROVED":
                    review_ref = "docs/reviews/" + name
                    if any(row.get("review") == review_ref for row in rows):
                        errors.append(
                            f"tasks: review {name}: a ledger row contradicts an APPROVED block"
                        )
    for row in rows:
        review = row.get("review")
        if review is None:
            errors.append(
                f"tasks: plan-defects row {row.get('run')}/{row.get('key')}: review missing"
            )
            continue
        if not (rp / review).is_file():
            errors.append(
                f"tasks: plan-defects row {row.get('run')}/{row.get('key')}: "
                f"no such review {review}"
            )
    return errors


def _today_utc():
    return datetime.datetime.now(datetime.timezone.utc).date()


def plan_defect_record(repos, today):
    """The seven-day rejection record aggregated over repos: (total, counts)
    where counts maps a primary plan_defect to its tally. A file both in the
    ledger and carrying a block counts once (the block wins). Returns None when
    any repo's ledger is unreadable."""
    start = today - datetime.timedelta(days=7)
    total = 0
    counts = {}
    for repo in repos:
        repo_path = repo.get("path")
        if repo_path is None:
            continue
        loaded = _plan_defects_for(repo_path)
        if loaded is None:
            return None
        fmf, rows = loaded
        # Blocks on files dated >= front_matter_from, within the window.
        block_primary = {}
        reviews_dir = pathlib.Path(repo_path) / "docs" / "reviews"
        if fmf is not None and reviews_dir.is_dir():
            for path in sorted(reviews_dir.glob("*opus-review*.md")):
                date = _review_date(path.name)
                if date is None or date < fmf or not (start <= date <= today):
                    continue
                has_block, block, first, lookahead = _read_review(path)
                if not has_block:
                    continue
                m = _review_h1(first, lookahead)
                if m is None or m["verdict"] != "REJECTED":
                    continue
                pd = block.get("plan_defect")
                if pd is not None:
                    block_primary["docs/reviews/" + path.name] = pd
        for pd in block_primary.values():
            total += 1
            counts[pd] = counts.get(pd, 0) + 1
        # Ledger rows in the window that a block does not shadow.
        for row in rows:
            pd = row.get("plan_defect")
            date = row.get("date")
            review = row.get("review")
            if pd is None or date is None:
                continue
            if not (start <= date <= today):
                continue
            if review in block_primary:
                continue
            total += 1
            counts[pd] = counts.get(pd, 0) + 1
    return (total, counts)


def check(graph):
    """Error strings; empty means the graph is sound."""
    errors = []
    # Repos `repos.toml` configures: the valid targets for a `**repo:**` value.
    # `build`/`main` carry the real ledger's names even when the graph itself was
    # scanned against a `--repos` override; a hand-built test graph falls back to
    # the repos it scanned.
    configured = set(graph.get("configured_repos", [r["name"] for r in graph["repos"]]))
    # Per-repo resolvable sets, so an imported task's `dependsOn` resolves against
    # the repo that DEFINES it (whose plan files name the key) rather than the
    # repo it runs in (MAJOR 2).
    resolvable_by_repo = {
        repo["name"]: set(repo.get("resolvable_roots", ()))
        | {chain_root(t["key"]) for t in repo["tasks"]}
        for repo in graph["repos"]
    }
    for repo in graph["repos"]:
        name = repo["name"]
        # Resolvable keys for THIS repo = every typed key in its own plan files
        # (whatever `repo:` they name) plus the chain roots of its retained and
        # attributed tasks. No global namespace: a key defined only in another
        # repo's own plan files is unknown here.
        resolvable = resolvable_by_repo[name]
        imported = repo.get("imported", {})

        # a `**repo:**` naming a repo repos.toml does not configure is a silent
        # disappearance (the task leaves every graph); refuse it here.
        for key, value in repo.get("attributed", []):
            if value not in configured:
                errors.append(
                    f"tasks: {name}/{key} repo: {value} not in docs/ledger/repos.toml"
                )

        # the same key defined in more than one typed plan
        plan_order = {}
        for t in repo["tasks"]:
            plan_order.setdefault(t["key"], [])
            if t["plan"] not in plan_order[t["key"]]:
                plan_order[t["key"]].append(t["plan"])
        for key, plans in plan_order.items():
            if len(plans) > 1:
                errors.append(f"tasks: {name}/{key} defined in {' and '.join(plans)}")

        for t in repo["tasks"]:
            defining = imported.get(t["key"])
            rset = resolvable_by_repo.get(defining, resolvable)
            for d in t["depends_on"]:
                if chain_root(d) not in rset:
                    errors.append(
                        f"tasks: {name}/{t['key']} dependsOn {d}: unknown key"
                    )
            if t["kind"] == "code" and not t["acceptance"]:
                errors.append(f"tasks: {name}/{t['key']} (code) has no acceptance")

        for cycle in _find_cycles(repo):
            errors.append(f"tasks: cycle in {name}: {' -> '.join(cycle)}")

    # a task-status row must name a key some plan actually defines, and its
    # status must be exactly one of the withdrawn/parked values — never a
    # silently-scheduled mistype.
    defined_rows = {
        (repo["name"], t["plan"], t["key"])
        for repo in graph["repos"]
        for t in repo["tasks"]
    }
    for (repo, plan, key), row in graph.get("task_status", {}).items():
        if (repo, plan, key) not in defined_rows:
            errors.append(f"tasks: task-status names unknown key {repo}/{plan}/{key}")
        if row.get("status") not in ("withdrawn", "parked"):
            errors.append(
                f"tasks: task-status row {repo}/{plan}/{key}: "
                f"unknown status {row.get('status')}"
            )
    # the plan-defect ledger and each gate review's front-matter block
    for repo in graph["repos"]:
        if repo.get("path"):
            errors.extend(_review_defect_errors(repo["path"]))
    return errors


def map_check_names(root):
    """The check names listed under docs/MAP.md's `## Checks` heading — the same
    awk as the lint block (lines starting `- ` beneath that heading, stopping at
    the next `## `). None when the file cannot be read."""
    path = os.path.join(root, "docs", "MAP.md")
    try:
        lines = pathlib.Path(path).read_text().splitlines()
    except OSError:
        return None
    names = set()
    in_checks = False
    for line in lines:
        if line.startswith("## Checks"):
            in_checks = True
            continue
        if line.startswith("## "):
            in_checks = False
            continue
        if in_checks and line.startswith("- "):
            names.add(line[2:].strip())
    return names


def load_draft(file, root, repos, scanned):
    """Read a draft plan outside the plans directory and attach it to the repo
    whose configured `path` realpath-equals `root`. Usage errors (unreadable
    file, file already under the plans directory, root with no matching repo)
    exit 2. A basename that collides with an existing plan REPLACES that plan's
    tasks (replan: every `### ` line of the existing file must appear
    byte-identical) and otherwise the draft's tasks are ADDED; in either case
    the draft's tasks are given state `ready`. Returns the info `draft_rules`
    consumes, including any replan heading-drop errors."""
    # (1) readable
    try:
        text = pathlib.Path(file).read_text()
    except OSError:
        print(f"tasks: --draft: cannot read {file}", file=sys.stderr)
        raise SystemExit(2)

    root_real = os.path.realpath(root)
    # (3) the configured repo whose path realpath-equals root
    repo = None
    for r in repos:
        if os.path.realpath(r["path"]) == root_real:
            repo = r
            break
    if repo is None:
        print(f"tasks: --draft: no configured repo has path {root}", file=sys.stderr)
        raise SystemExit(2)

    # (2) the draft may not already live in the plans directory
    plans_dir = os.path.join(repo["path"], os.path.dirname(repo["plans"]))
    plans_real = os.path.realpath(plans_dir)
    real = os.path.realpath(file)
    if real == plans_real or real.startswith(plans_real + os.sep):
        print(
            f"tasks: --draft: {file} is already under the plans directory; "
            "run check without --draft",
            file=sys.stderr,
        )
        raise SystemExit(2)

    scanned_repo = next(r for r in scanned if r["name"] == repo["name"])
    landed = landed_subjects(scanned_repo["path"])
    draft = parse_plan(file)
    plan_name = draft["file"]
    # chain-root -> {existing tasks' chain roots} per commit subject, so the
    # "already landed" rule can exempt a fix round / re-plan reusing its root's
    # subject (task → its own root), judged before the draft is attached.
    existing_subject_roots = {}
    for t in scanned_repo["tasks"]:
        existing_subject_roots.setdefault(t["commit_subject"], set()).add(
            chain_root(t["key"])
        )

    errors = []
    existing_plan_file = os.path.join(plans_dir, plan_name)
    replan = os.path.isfile(existing_plan_file)
    if replan:
        try:
            existing_lines = pathlib.Path(existing_plan_file).read_text().splitlines()
        except OSError:
            existing_lines = []
        draft_lines = set(text.splitlines())
        for ln in existing_lines:
            if ln.startswith("### ") and ln not in draft_lines:
                errors.append(f"tasks: draft drops heading: {ln}")
        scanned_repo["tasks"] = [
            t for t in scanned_repo["tasks"] if t["plan"] != plan_name
        ]
    for t in draft["tasks"]:
        t["state"] = "landed" if t["commit_subject"] in landed else "ready"
    scanned_repo["tasks"].extend(draft["tasks"])

    return {
        "tasks": draft["tasks"],
        "plan_name": plan_name,
        "lines": text.splitlines(),
        "existing_subject_roots": existing_subject_roots,
        "landed": landed,
        "errors": errors,
        "replan": replan,
        "scanned": scanned_repo,
    }


REQUIRED_SECTIONS = (
    "## Global Constraints",
    "## Assumptions",
    "## Waves",
    "## Operator",
)


def draft_rules(draft, repo, map_names, landed):
    """The draft-only rules (never applied to landed plans, so no existing plan
    can turn red): acceptance names from docs/MAP.md, explicit touches, the
    commit-subject shape and its (test: …) names, size, the four house sections,
    and one section per key."""
    errors = []
    name = repo["name"]
    tasks = draft["tasks"]
    plan_name = draft["plan_name"]
    existing_subject_roots = draft["existing_subject_roots"]

    # (e) headers: the four house sections must be present (prefix match).
    lines = draft["lines"]
    for req in REQUIRED_SECTIONS:
        if not any(ln.startswith(req) for ln in lines):
            errors.append(f"tasks: draft lacks section {req[3:]}")

    # (f) one section per key, keyed by the draft's basename (check()'s
    # duplicate rule only counts distinct plan names, so it cannot see two
    # sections of one file).
    seen = set()
    for t in tasks:
        if t["key"] in seen:
            errors.append(f"tasks: {t['key']} defined twice in {plan_name}")
        seen.add(t["key"])

    for t in tasks:
        key = t["key"]
        attributed_elsewhere = t["repo"] not in (None, name)
        # (a) acceptance names — exempt for tasks attributed to another repo
        # (that repo's checks are not in this MAP).
        if not attributed_elsewhere:
            if map_names is None:
                errors.append(
                    f"tasks: {key}: docs/MAP.md unreadable; cannot verify acceptance"
                )
            else:
                for entry in t["acceptance"]:
                    if entry != "lint" and entry not in map_names:
                        errors.append(
                            f"tasks: {key} acceptance {entry} not in docs/MAP.md"
                        )
        # (b) touches — explicit paths only; a code task must touch something.
        if not t["touches"] and t["kind"] == "code":
            errors.append(f"tasks: {key} touches: empty")
        else:
            for entry in t["touches"]:
                if any(ch in entry for ch in "*?["):
                    errors.append(
                        f"tasks: {key} touches {entry}: glob is not an explicit path"
                    )
        # (d) size — L is refused and asked to split.
        if t["size"] == "L":
            errors.append(f"tasks: {key}: size L is refused; split it")
        # (c) commit subject — exempt for tasks attributed to another repo.
        if not attributed_elsewhere:
            subject = t["commit_subject"] or ""
            m = re.fullmatch(r"[a-z][a-z0-9-]*: .+ \(test: ([^)]+)\)", subject)
            if m is None:
                errors.append(
                    f"tasks: {key} commit subject (test: ?) differs from acceptance"
                )
            else:
                names = {x.strip() for x in m.group(1).split(",") if x.strip()}
                if names != set(t["acceptance"]):
                    errors.append(
                        f"tasks: {key} commit subject (test: {m.group(1)}) "
                        "differs from acceptance"
                    )
            if subject in landed and chain_root(key) not in existing_subject_roots.get(
                subject, set()
            ):
                errors.append(f"tasks: {key} commit subject already landed: {subject}")

    # two draft tasks with different chain roots may not share a subject
    root_by_subject = {}
    for t in tasks:
        subj = t["commit_subject"]
        root = chain_root(t["key"])
        if subj in root_by_subject and root_by_subject[subj] != root:
            errors.append(
                f"tasks: {t['key']} commit subject {subj} shared by a different "
                "chain root"
            )
        root_by_subject.setdefault(subj, root)

    return errors


def render_brief(graph, claims_rows=None, today=None):
    """One-screen markdown board brief: per-repo state counts, the next wave,
    the seven-day plan-defect record, rejected fixes owed, operator-owned gaps
    and untracked plans."""
    today = today if today is not None else _today_utc()
    lines = [f"# Task brief (generated {graph['generated']})", ""]
    lines.append(
        "| repo | landed | approved | rejected | ran | running | recorded | ready | "
        "blocked | deferred-to-brief | withdrawn | parked | legacy open | untracked |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for repo in graph["repos"]:
        counts = {s: 0 for s in STATES}
        for t in repo["tasks"]:
            if t["state"] in counts:
                counts[t["state"]] += 1
        legacy_open = sum(1 for r in repo["legacy"] if r["status"] == "open")
        cols = [counts[s] for s in STATES] + [legacy_open, len(repo["untracked_plans"])]
        lines.append(f"| {repo['name']} | " + " | ".join(str(c) for c in cols) + " |")
    lines.append("")

    next_wave = []
    for repo in graph["repos"]:
        ws = waves(repo)
        if not ws:
            continue
        keys = ws[0]
        open_plans = {t["plan"] for t in open_tasks(repo)}
        wave_plans = {t["plan"] for t in open_tasks(repo) if t["key"] in keys}
        label = " ".join(keys)
        if len(wave_plans) == 1 and len(open_plans) > 1:
            label += f" (plan {next(iter(wave_plans))})"
        next_wave.append(f"{repo['name']}: {label}")
    lines.append("**Next wave** — " + (" · ".join(next_wave) if next_wave else "none"))

    record = plan_defect_record(graph["repos"], today)
    if record is None:
        lines.append("**Record: unavailable**")
    else:
        total, counts = record
        caused = sum(counts.get(c, 0) for c in PLAN_DEFECT_CAUSED)
        parts = ", ".join(
            f"{PLAN_DEFECT_SHORT[c]} {counts.get(c, 0)}" for c in PLAN_DEFECT_CAUSED
        )
        lines.append(f"**Record (7 d):** {total} rej, {caused} plan ({parts})")

    running = []
    for repo in graph["repos"]:
        seen = set()
        for t in repo["tasks"]:
            if t["state"] != "running":
                continue
            root = chain_root(t["key"])
            if root in seen:
                continue
            seen.add(root)
            item = f"{repo['name']}/{root}"
            if t["detail"]:
                item += f" ({t['detail']})"
            running.append(item)
    lines.append("**Running:** " + (" · ".join(running) if running else "none"))

    rejected = []
    for repo in graph["repos"]:
        seen = set()
        for t in repo["tasks"]:
            if t["state"] != "rejected":
                continue
            root = chain_root(t["key"])
            if root in seen:
                continue
            seen.add(root)
            item = f"{repo['name']}/{root}"
            if t["detail"]:
                item += f" ({t['detail']})"
            rejected.append(item)
    lines.append(
        "**Rejected, fix round owed:** "
        + (" · ".join(rejected) if rejected else "none")
    )

    withdrawn = [
        f"{repo['name']}/{t['key']}"
        for repo in graph["repos"]
        for t in repo["tasks"]
        if t["state"] in ("withdrawn", "parked")
    ]
    lines.append(
        "**Withdrawn/parked:** " + (" · ".join(withdrawn) if withdrawn else "none")
    )

    if claims_rows is None:
        lines.append("**Operator owns:** (claims file not read)")
    else:
        owned = []
        for c in claims_rows:
            if c.get("status") == "gap" and c.get("owner") == "operator":
                item = c["id"]
                if c.get("review_by"):
                    item += f" (review by {c['review_by']})"
                elif c.get("note"):
                    item += f" ({c['note']})"
                owned.append(item)
        lines.append("**Operator owns:** " + (" · ".join(owned) if owned else "none"))

    untracked = [
        f"{repo['name']}/{f}"
        for repo in graph["repos"]
        for f in repo["untracked_plans"]
    ]
    lines.append(
        "**Untracked plans (no typed headings, no plan-status row):** "
        + (" · ".join(untracked) if untracked else "none")
    )
    return "\n".join(lines) + "\n"


def render_board_block(graph):
    """The queue's next wave-1 keys and the plan(s) they come from, one line;
    "nothing queued" when every repo is settled. The board covers this tree
    only, so the single repo's name is omitted (the header says "this tree"),
    which keeps the block identical across clones that rename the directory."""
    parts = []
    for repo in graph["repos"]:
        ws = waves(repo)
        if not ws:
            continue
        wave_plans = sorted({t["plan"] for t in open_tasks(repo) if t["key"] in ws[0]})
        parts.append(f"{' '.join(ws[0])} ({' '.join(wave_plans)})")
    body = " · ".join(parts) if parts else "nothing queued"
    return (
        "**Queued (derived from this tree; tasks whose dependencies run in other "
        f"repos, and in-flight state, are in the session brief).** {body}\n"
    )


def _splice_board(text, content):
    """Return the text with the marked block replaced by `content`, or None
    when either marker is missing (or in the wrong order)."""
    ib = text.find(BEGIN)
    ie = text.find(END)
    if ib < 0 or ie < 0 or ie < ib:
        return None
    return text[:ib] + BEGIN + "\n" + content + END + text[ie + len(END) :]


def write_board(path, graph):
    """Replace the marked block; True when the file changed, False when already
    current. Missing markers raise SystemExit(1)."""
    path = pathlib.Path(path)
    text = path.read_text()
    new = _splice_board(text, render_board_block(graph))
    if new is None:
        print(f"tasks: {path} is missing the {BEGIN} … {END} markers", file=sys.stderr)
        raise SystemExit(1)
    if new == text:
        return False
    path.write_text(new)
    return True


def board_drift(path, graph):
    """None when the marked block is current, else a unified diff of the drift."""
    path = pathlib.Path(path)
    text = path.read_text()
    new = _splice_board(text, render_board_block(graph))
    if new is None:
        return f"{path}: board block markers missing\n"
    if new == text:
        return None
    return "".join(
        difflib.unified_diff(
            text.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=str(path),
            tofile=str(path),
        )
    )


def _stale_after_default():
    """The `--stale-after` default, parsed defensively: a malformed
    TASKS_STALE_AFTER falls back to DEFAULT_STALE_AFTER with a one-line warning
    instead of crashing every subcommand while the parser is built."""
    raw = os.environ.get("TASKS_STALE_AFTER")
    if raw is None:
        return DEFAULT_STALE_AFTER
    try:
        return int(raw)
    except (TypeError, ValueError):
        print(
            f"tasks: TASKS_STALE_AFTER={raw!r} is not an integer; "
            f"using {DEFAULT_STALE_AFTER}",
            file=sys.stderr,
        )
        return DEFAULT_STALE_AFTER


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tasks")
    parser.add_argument("--root", default=".")
    parser.add_argument("--repos", default=None)
    parser.add_argument("--plan-status", default=None)
    parser.add_argument("--runs-dir", default=DEFAULT_RUNS_DIR)
    parser.add_argument(
        "--stale-after",
        type=int,
        default=_stale_after_default(),
    )
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE", "/var/lib/evidence")
    )
    parser.add_argument("--claims", default=None)
    parser.add_argument("--today", type=datetime.date.fromisoformat, default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("brief").add_argument(
        "--today", type=datetime.date.fromisoformat, default=argparse.SUPPRESS
    )
    sub.add_parser("json")
    waves_p = sub.add_parser("waves")
    waves_p.add_argument("--repo", required=True)
    waves_p.add_argument("--plan")
    waves_p.add_argument("--factory-args", action="store_true")
    waves_p.add_argument("--next", action="store_true")
    waves_p.add_argument("--json", action="store_true")
    conflicts_p = sub.add_parser("conflicts")
    conflicts_p.add_argument("--repo")
    check_p = sub.add_parser("check")
    check_p.add_argument("--board", default=None)
    check_p.add_argument("--draft", default=None)
    write_board_p = sub.add_parser("write-board")
    write_board_p.add_argument("--board", default="docs/OPERATIONS.md")
    write_board_p.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    repos_path = args.repos or os.path.join(args.root, "docs", "ledger", "repos.toml")
    status_path = args.plan_status or os.path.join(
        args.root, "docs", "ledger", "plan-status.toml"
    )
    claims_path = args.claims or os.path.join(
        args.root, "docs", "ledger", "claims.toml"
    )

    repos = load_repos(repos_path)
    plan_status = load_plan_status(status_path)
    task_status_path = os.path.join(args.root, "docs", "ledger", "task-status.toml")
    task_status = load_task_status(task_status_path)
    # The valid `**repo:**` targets come from the ledger under `--root`, even when
    # the graph itself was scanned against a `--repos` override (the lint check
    # points this tree at itself with a one-repo file); see `check`.
    configured_repos = [
        r["name"]
        for r in load_repos(os.path.join(args.root, "docs", "ledger", "repos.toml"))
    ]
    graph = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "repos": [
            scan_repo(
                r,
                plan_status,
                args.runs_dir,
                args.store,
                repos=repos,
                task_status=task_status,
                stale_after=args.stale_after,
            )
            for r in repos
        ],
        "configured_repos": configured_repos,
        "task_status": task_status,
    }

    if args.command == "brief":
        claims = None
        if pathlib.Path(claims_path).exists():
            with open(claims_path, "rb") as fh:
                claims = tomllib.load(fh).get("claim", [])
        print(render_brief(graph, claims, today=args.today), end="")
        return 0

    if args.command == "json":
        print(json.dumps(graph))
        return 0

    if args.command == "waves":
        if args.factory_args and not args.plan:
            waves_p.print_usage(sys.stderr)
            return 2
        repo = next((r for r in graph["repos"] if r["name"] == args.repo), None)
        if repo is None:
            print(f"tasks: unknown repo {args.repo}", file=sys.stderr)
            return 1
        if args.factory_args:
            print(json.dumps(factory_args(repo, args.plan)))
            return 0
        if args.json:
            print(json.dumps(wave_structure(repo, plan=args.plan)))
            return 0
        lines = wave_lines(repo, plan=args.plan)
        if args.next:
            if lines:
                print(lines[0])
            return 0
        for line in lines:
            print(line)
        return 0

    if args.command == "conflicts":
        repos = [
            r for r in graph["repos"] if args.repo is None or r["name"] == args.repo
        ]
        found = False
        for repo in repos:
            for c in conflicts(repo):
                found = True
                print(
                    f"{repo['name']}: {c['a']} ({c['plan_a']}) × {c['b']} "
                    f"({c['plan_b']}): {c['path_a']} ~ {c['path_b']}"
                )
        if not found:
            print("none")
        return 0

    if args.command == "check":
        draft = None
        if args.draft:
            draft = load_draft(args.draft, args.root, repos, graph["repos"])
        errors = check(graph)
        if args.board:
            board = os.path.join(args.root, args.board)
            if board_drift(board, board_graph(args.root)) is not None:
                errors.append(
                    f"tasks: {args.board} queue block is stale — "
                    "run: evidence tasks write-board"
                )
        if draft is not None:
            repo = draft["scanned"]
            landed = draft["landed"]
            map_names = map_check_names(args.root)
            errors += draft["errors"]
            errors += draft_rules(draft, repo, map_names, landed)
            if not errors:
                print(
                    f"waves: {json.dumps(wave_structure(repo, plan=draft['plan_name']))}"
                )
                rows = [
                    c
                    for c in conflicts(repo)
                    if c["plan_a"] == draft["plan_name"]
                    or c["plan_b"] == draft["plan_name"]
                ]
                if not rows:
                    print("conflicts: none")
                else:
                    for c in rows:
                        print(
                            f"conflicts: {c['a']} ({c['plan_a']}) × {c['b']} "
                            f"({c['plan_b']}): {c['path_a']} ~ {c['path_b']}"
                        )
                return 0
        for e in errors:
            print(e, file=sys.stderr)
        return 1 if errors else 0

    if args.command == "write-board":
        board = (
            args.board
            if os.path.isabs(args.board)
            else os.path.join(args.root, args.board)
        )
        write_board(board, board_graph(args.root))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
