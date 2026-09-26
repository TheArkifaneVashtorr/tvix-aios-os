"""bugs — validate docs/ledger/bugs.toml, the typed bug ledger (plan 2026-09-09-program, EV4).

A row names one defect and what closes it. A `fixed` row names the `task` key
that fixed it (empty when fixed by something that is not a typed task, e.g. a
re-integration); a `closed` row names the `closing_check` that now passes. The
validator reads the flake's check set from the same source `lint`'s MAP.md step
compares against (`repomap.flake_check_names`, no `nix flake show`), and the
known task keys from the `### KEY` headings of the plan files.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import pathlib
import re
import subprocess
import sys

import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import repomap
import tasks

ID_RE = re.compile(r"^BUG-[a-z0-9][a-z0-9-]*$")
STATUSES = ("open", "fixed", "closed")
FIELDS = (
    "id",
    "found",
    "symptom",
    "repro",
    "status",
    "closing_check",
    "task",
    "evidence",
)
KEY_RE = re.compile(r"^### ([A-Za-z][A-Za-z0-9-]*) \(")


def load(path) -> list[dict]:
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("bug", [])


def known_tasks(root) -> set[str]:
    """The `### KEY` headings of every plan file under the tree, or the empty set
    when the plans directory cannot be read."""
    keys: set[str] = set()
    plans_dir = pathlib.Path(root) / "docs" / "superpowers" / "plans"
    if not plans_dir.is_dir():
        return keys
    for p in sorted(plans_dir.glob("*.md")):
        try:
            lines = p.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            m = KEY_RE.match(line)
            if m:
                keys.add(m.group(1))
    return keys


def validate(rows, check_names=None, known_tasks=None) -> list[str]:
    """One error line per defect. `check_names` and `known_tasks`, when given,
    gate the `closed`/`fixed` rows; when None the corresponding rule is skipped
    (the CLI always supplies both)."""
    errs: list[str] = []
    seen: set[str] = set()
    for r in rows:
        bid = str(r.get("id", "<no id>"))

        def say(msg, bid=bid):
            errs.append(f"bugs: {bid}: {msg}")

        for key in FIELDS:
            if key not in r:
                say(f"missing {key}")
        if not ID_RE.match(bid):
            say("id must match ^BUG-[a-z0-9][a-z0-9-]*$")
        if bid in seen:
            say("duplicate id")
        seen.add(bid)
        status = r.get("status")
        if status not in STATUSES:
            say(f"status must be one of {', '.join(STATUSES)}")
        if not isinstance(r.get("found"), datetime.date):
            say("found must be a TOML date")
        if status == "fixed":
            task = r.get("task") or ""
            if task and known_tasks is not None and task not in known_tasks:
                say(f"task {task} is not a key the graph knows")
        if status == "closed":
            cc = r.get("closing_check") or ""
            if not cc:
                say("closed row needs a closing_check")
            elif check_names is not None and cc not in check_names:
                say(f"closing_check {cc} is not a flake check")
    return errs


def _repro_verdict(row, returncode):
    """None when the row's status agrees with the command's exit; otherwise the
    one-line disagreement. Exit 0 means the defect reproduces; any non-zero
    exit means it does not. Raises ValueError on a status outside the enum."""
    bid = row["id"]
    status = row["status"]
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    if status == "open":
        if returncode == 0:
            return None
        return f"{bid}: status open but repro exited {returncode} (does not reproduce)"
    if returncode != 0:
        return None
    return f"{bid}: status {status} but repro exited {returncode} (still reproduces)"


def _run_repro(row, root, timeout):
    """Run one row's `repro` as `bash -c` with cwd = root; return the exit code.
    A timeout raises `subprocess.TimeoutExpired`."""
    return subprocess.run(
        ["bash", "-c", row["repro"]],
        cwd=root,
        timeout=timeout,
        capture_output=True,
        check=False,
    ).returncode


def repro_main(args) -> int:
    root = args.root
    if not os.path.isdir(root):
        print(f"repro: --root {root} is not a directory", file=sys.stderr)
        return 1
    rows = load(args.file)
    try:
        flake = pathlib.Path(root, "flake.nix").read_text()
    except OSError:
        flake = ""
    check_names = set(repomap.flake_check_names(flake))
    errs = validate(rows, check_names=check_names, known_tasks=known_tasks(root))
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1
    lines = []
    for row in rows:
        bid = row["id"]
        status = row["status"]
        if status in ("open", "fixed") and not (row.get("task") or ""):
            lines.append(f"{bid}: status {status} but task is empty (unowned)")
            continue
        try:
            rc = _run_repro(row, root, args.timeout)
        except subprocess.TimeoutExpired:
            lines.append(
                f"{bid}: status {status} but repro timed out after {args.timeout:g}s"
            )
            continue
        verdict = _repro_verdict(row, rc)
        if verdict is not None:
            lines.append(verdict)
    for line in lines:
        print(line)
    return 1 if lines else 0


def _read_escalations(runs_dir):
    """`tasks.read_escalations` plus the `model` field the reader drops. Re-globs
    the runs dir on every call — no module-level cache, no memo — so a payload
    deleted from the tree drops its row on the next run (derived only)."""
    out = {}
    newest = {}
    for p in glob.glob(os.path.join(str(runs_dir), "*", "*.escalate")):
        try:
            text = pathlib.Path(p).read_text()
        except OSError:
            continue
        key = tasks._field(text, r"^key:\s*(.+)$")
        run_name = tasks._field(text, r"^run:\s*(.+)$")
        if not (key and run_name):
            continue
        mtime = os.path.getmtime(os.path.dirname(p))
        payload = {
            "run": run_name,
            "role": tasks._field(text, r"^role:\s*(.+)$"),
            "escalate": tasks._field(text, r"^escalate:\s*(.+)$"),
            "rung": tasks._field(text, r"^rung:\s*(\d+)\s*$"),
            "launch": tasks._field(text, r"^launch:\s*(.+)$"),
            "model": tasks._field(text, r"^model:\s*(.+)$"),
        }
        if key not in newest or mtime > newest[key][0]:
            newest[key] = (mtime, payload)
    for key, (_mtime, payload) in newest.items():
        out[key] = payload
    return out


def _closure(key, graph):
    """`integrated-by <KEY>` when a later key of the same `CHAIN_RE` root has
    state `landed`/`integrated`; `withdrawn` when a task-status row withdraws the
    key; else `open`. Derived from the `tasks.py json` graph — never from prose.
    """
    root = tasks.chain_root(key)
    successors = []
    for repo in graph.get("repos", ()):
        for t in repo.get("tasks", ()):
            k = t.get("key")
            if not k or k == key:
                continue
            if tasks.chain_root(k) != root:
                continue
            if t.get("state") not in ("landed", "integrated"):
                continue
            # "later": sorts after `key` in the chain (root first, then suffix).
            if (k != root, k) > (key != root, key):
                successors.append(k)
    if successors:
        return f"integrated-by {min(successors)}"
    for row in graph.get("task_status", ()):
        if row.get("key") == key and row.get("status") == "withdrawn":
            return "withdrawn"
    return "open"


def design_failures(runs_dir, graph_json):
    """One row per escalation, sorted by key: the record derived from the payloads
    and the graph's states — never typed by hand, never cached."""
    escalations = _read_escalations(runs_dir)
    rows = []
    for key in sorted(escalations):
        e = escalations[key]
        rows.append(
            {
                "key": key,
                "run": e["run"],
                "role": e["role"],
                "rung": e["rung"],
                "escalate": e["escalate"],
                "model": e["model"],
                "launch": e["launch"],
                "closure": _closure(key, graph_json),
            }
        )
    return rows


def escalations_main(args) -> int:
    runs_dir = args.runs_dir
    if not os.path.isdir(runs_dir):
        print(f"escalations: --runs-dir {runs_dir} is not a directory", file=sys.stderr)
        return 1
    tasks_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.py")
    proc = subprocess.run(
        [sys.executable, tasks_py, "--root", args.root, "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return 1
    graph_json = json.loads(proc.stdout)
    for r in design_failures(runs_dir, graph_json):
        cols = (
            r["key"],
            r["run"],
            r["role"],
            r["rung"],
            r["escalate"],
            r["model"],
            r["closure"],
        )
        print("\t".join("-" if c is None else str(c) for c in cols))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bugs")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("file")
    v.add_argument("--root", default=None)
    r = sub.add_parser("repro")
    r.add_argument("file")
    r.add_argument("--root", default=".")
    r.add_argument("--timeout", type=float, default=60.0)
    e = sub.add_parser("escalations")
    e.add_argument("--runs-dir", required=True)
    e.add_argument("--root", required=True)
    args = p.parse_args(argv)

    if args.cmd == "repro":
        return repro_main(args)
    if args.cmd == "escalations":
        return escalations_main(args)

    root = args.root or str(pathlib.Path(args.file).resolve().parents[2])
    rows = load(args.file)
    try:
        flake = pathlib.Path(root, "flake.nix").read_text()
    except OSError:
        flake = ""
    check_names = set(repomap.flake_check_names(flake))
    errs = validate(rows, check_names=check_names, known_tasks=known_tasks(root))
    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
