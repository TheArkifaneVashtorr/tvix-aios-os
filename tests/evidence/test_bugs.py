"""Bug ledger validator tests (plan 2026-09-09-program, EV4)."""

import datetime
import importlib.util
import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()


def _load(name, filename):
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / filename,
        pathlib.Path(f"pkgs/evidence/{filename}"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location(name, src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod, src


# tasks first: bugs.py does `import tasks`, which must find this module.
tk, TASKS_SRC = _load("tasks", "tasks.py")
bugs, SRC = _load("bugs", "bugs.py")


def row(**overrides):
    base = {
        "id": "BUG-anything",
        "found": datetime.date(2026, 9, 10),
        "symptom": "something is broken",
        "repro": "python3 -c 'pass'",
        "status": "open",
        "closing_check": "",
        "task": "",
        "evidence": "docs/board/log-2026-09.md",
    }
    base.update(overrides)
    return base


def test_validate_rejects_duplicate_id():
    # Mutant A: a duplicated id must fail.
    r = row()
    errs = bugs.validate([r, dict(r)])
    assert any("duplicate id" in e for e in errs)


def test_validate_rejects_unknown_closing_check():
    # Mutant B: a closed row naming a check that does not exist must fail.
    r = row(status="closed", closing_check="nonesuch", task="")
    errs = bugs.validate([r], check_names={"unit", "lint"})
    assert any("nonesuch" in e for e in errs)


def test_validate_accepts_fixed_row_with_known_task():
    # Fixture: a fixed row naming a task the graph knows passes unchanged.
    r = row(
        id="BUG-w6-review-model",
        status="fixed",
        closing_check="factory-unit",
        task="FIX7",
    )
    errs = bugs.validate([r], check_names={"factory-unit"}, known_tasks={"FIX7"})
    assert errs == []


def test_validate_rejects_missing_field():
    for field in (
        "id",
        "found",
        "symptom",
        "repro",
        "status",
        "closing_check",
        "task",
        "evidence",
    ):
        r = row()
        del r[field]
        errs = bugs.validate([r])
        assert any("missing" in e and field in e for e in errs), field


def test_validate_rejects_malformed_id():
    errs = bugs.validate([row(id="bug-1")])
    assert any("id" in e for e in errs)


def test_validate_rejects_bad_status():
    errs = bugs.validate([row(status="pending")])
    assert any("status" in e for e in errs)


def _dump(rows):
    """Serialize a list of row dicts to a TOML `[[bug]]` ledger."""
    parts = []
    for r in rows:
        parts.append("[[bug]]")
        for k in (
            "id",
            "found",
            "symptom",
            "repro",
            "status",
            "closing_check",
            "task",
            "evidence",
        ):
            v = r[k]
            if k == "found":
                parts.append(f"found = {v.isoformat()}")
            else:
                parts.append(f"{k} = {json.dumps(v)}")
        parts.append("")
    return "\n".join(parts) + "\n"


def test_repro_verdict_table():
    # Six cases: each status (open/fixed/closed) x rc 0/1.
    assert bugs._repro_verdict(row(id="BUG-a", status="open"), 0) is None
    assert (
        bugs._repro_verdict(row(id="BUG-a", status="open"), 1)
        == "BUG-a: status open but repro exited 1 (does not reproduce)"
    )
    assert (
        bugs._repro_verdict(row(id="BUG-a", status="fixed"), 0)
        == "BUG-a: status fixed but repro exited 0 (still reproduces)"
    )
    assert bugs._repro_verdict(row(id="BUG-a", status="fixed"), 1) is None
    assert (
        bugs._repro_verdict(row(id="BUG-a", status="closed"), 0)
        == "BUG-a: status closed but repro exited 0 (still reproduces)"
    )
    assert bugs._repro_verdict(row(id="BUG-a", status="closed"), 1) is None
    with pytest.raises(ValueError):
        bugs._repro_verdict(row(id="BUG-a", status="pending"), 0)


def test_repro_cli_disagreement(tmp_path, capsys, monkeypatch):
    # BUG-a open repro "false" disagrees; BUG-b fixed repro "true" disagrees;
    # BUG-c fixed repro "false" agrees and must be absent.
    rows = [
        row(id="BUG-a", status="open", repro="false", task="DF1"),
        row(id="BUG-b", status="fixed", repro="true", task="DF1"),
        row(id="BUG-c", status="fixed", repro="false", task="DF2"),
    ]
    ledger = tmp_path / "bugs.toml"
    ledger.write_text(_dump(rows))
    monkeypatch.setattr(bugs, "known_tasks", lambda root: {"DF1", "DF2"})
    rc = bugs.main(["repro", str(ledger), "--root", str(tmp_path)])
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert rc == 1
    assert lines == [
        "BUG-a: status open but repro exited 1 (does not reproduce)",
        "BUG-b: status fixed but repro exited 0 (still reproduces)",
    ]
    assert "BUG-c" not in out


def test_repro_cli_all_agree(tmp_path, capsys, monkeypatch):
    rows = [
        row(id="BUG-a", status="open", repro="true", task="DF1"),
        row(id="BUG-b", status="fixed", repro="false", task="DF1"),
        row(id="BUG-c", status="fixed", repro="false", task="DF2"),
    ]
    ledger = tmp_path / "bugs.toml"
    ledger.write_text(_dump(rows))
    monkeypatch.setattr(bugs, "known_tasks", lambda root: {"DF1", "DF2"})
    rc = bugs.main(["repro", str(ledger), "--root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""


def test_repro_timeout(tmp_path, capsys, monkeypatch):
    rows = [row(id="BUG-a", status="open", repro="sleep 5", task="DF1")]
    ledger = tmp_path / "bugs.toml"
    ledger.write_text(_dump(rows))
    monkeypatch.setattr(bugs, "known_tasks", lambda root: {"DF1"})
    rc = bugs.main(["repro", str(ledger), "--root", str(tmp_path), "--timeout", "1"])
    out = capsys.readouterr().out
    assert rc == 1
    assert out.strip() == "BUG-a: status open but repro timed out after 1s"


def test_repro_untyped_row(tmp_path, capsys):
    # An open row with task = "" is refused before its command runs: the
    # sleep-5 variant must finish at once with the same single line.
    for repro in ("true", "sleep 5"):
        rows = [row(id="BUG-d", status="open", repro=repro, task="")]
        ledger = tmp_path / "bugs.toml"
        ledger.write_text(_dump(rows))
        rc = bugs.main(["repro", str(ledger), "--root", str(tmp_path)])
        out = capsys.readouterr().out
        assert rc == 1
        assert out.strip() == "BUG-d: status open but task is empty (unowned)"


def test_repro_bad_root(tmp_path, capsys, monkeypatch):
    rows = [
        row(id="BUG-a", status="open", repro="true", task="DF1"),
        row(id="BUG-b", status="fixed", repro="false", task="DF1"),
    ]
    ledger = tmp_path / "bugs.toml"
    ledger.write_text(_dump(rows))
    monkeypatch.setattr(bugs, "known_tasks", lambda root: {"DF1"})
    bad_root = tmp_path / "nonesuch"
    rc = bugs.main(["repro", str(ledger), "--root", str(bad_root)])
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert captured.err.strip() == f"repro: --root {bad_root} is not a directory"


def _escalate_text(key, run, model="opus", rung="2"):
    return (
        f"run: {run}\nkey: {key}\nrole: review\nrung: {rung}\n"
        f"escalate: claude/review\nmodel: {model}\neffort: high\n"
        f"launch: opus-gate task/{key}\n"
    )


def _graph_json(tasks=(), status_rows=()):
    """A minimal `tasks.py json`-shaped graph: repos with `key`/`state` tasks and
    a `task_status` list of `{key, status}` rows."""
    return {
        "repos": [{"name": "r", "tasks": [{"key": k, "state": s} for k, s in tasks]}],
        "task_status": [{"key": k, "status": s} for k, s in status_rows],
    }


def _write_escalations(runs, specs):
    for key, run, model in specs:
        d = runs / run
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{key}.escalate").write_text(_escalate_text(key, run, model=model))


def test_closure_integrated():
    # A later key of the same CHAIN_RE root that landed closes the escalation.
    graph = _graph_json(tasks=[("E7", "ready"), ("E7b", "landed")])
    assert bugs._closure("E7", graph) == "integrated-by E7b"


def test_closure_withdrawn():
    # A task-status row that withdraws the key closes it as withdrawn.
    graph = _graph_json(tasks=[("E9", "ready")], status_rows=[("E9", "withdrawn")])
    assert bugs._closure("E9", graph) == "withdrawn"


def test_closure_open():
    # A key the graph does not define has nothing to close it: it stays open.
    graph = _graph_json(
        tasks=[("E7", "ready"), ("E7b", "landed")],
        status_rows=[("E9", "withdrawn")],
    )
    assert bugs._closure("E10", graph) == "open"


def test_escalations_cli_table(tmp_path, capsys, monkeypatch):
    # Three rows, tab-separated, sorted by key; the closure column flows from
    # the graph (integrated-by / withdrawn / open) and `model` from the payload.
    # The `tasks.py json` subprocess is the seam: faked here, exercised live by
    # the acceptance probe.
    runs = tmp_path / "runs"
    _write_escalations(
        runs,
        [("E7", "r7", "opus"), ("E9", "r9", "sonnet"), ("E10", "r10", "haiku")],
    )
    graph = _graph_json(
        tasks=[("E7", "ready"), ("E7b", "landed"), ("E9", "ready")],
        status_rows=[("E9", "withdrawn")],
    )
    monkeypatch.setattr(
        bugs.subprocess,
        "run",
        lambda argv, **kw: type(
            "R", (), {"returncode": 0, "stdout": json.dumps(graph), "stderr": ""}
        )(),
    )
    rc = bugs.main(["escalations", "--runs-dir", str(runs), "--root", "x"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.splitlines() == [
        "E10\tr10\treview\t2\tclaude/review\thaiku\topen",
        "E7\tr7\treview\t2\tclaude/review\topus\tintegrated-by E7b",
        "E9\tr9\treview\t2\tclaude/review\tsonnet\twithdrawn",
    ]


def test_escalations_drops_deleted_payload(tmp_path):
    # Interface 4: the record is derived only — a payload deleted from the runs
    # dir drops its row on the next call in the same process (no cache).
    runs = tmp_path / "runs"
    _write_escalations(
        runs, [("E7", "r7", "opus"), ("E9", "r9", "sonnet"), ("E10", "r10", "haiku")]
    )
    graph = _graph_json(
        tasks=[("E7", "ready"), ("E7b", "landed"), ("E9", "ready")],
        status_rows=[("E9", "withdrawn")],
    )
    first = bugs.design_failures(runs, graph)
    assert [r["key"] for r in first] == ["E10", "E7", "E9"]
    (runs / "r9" / "E9.escalate").unlink()
    second = bugs.design_failures(runs, graph)
    assert [r["key"] for r in second] == ["E10", "E7"]


PLAN = """# DF6 fixture plan

## Tasks

### E7 (code, S) — seven

**dependsOn:** none

Body E7.

**touches:** a.py
**acceptance:** unit
**commit subject:** `x: seven (test: unit)`

### E7b (code, S) — seven b

**dependsOn:** none

Body E7b.

**touches:** b.py
**acceptance:** unit
**commit subject:** `x: seven b (test: unit)`

### E9 (code, S) — nine

**dependsOn:** none

Body E9.

**touches:** c.py
**acceptance:** unit
**commit subject:** `x: nine (test: unit)`
"""


def _fake_git(subjects):
    def run(argv, timeout=20.0):
        class R:
            returncode = 0
            stdout = "\n".join(subjects) + "\n"
            stderr = ""

        return R()

    return run


def test_brief_design_failures_line(tmp_path):
    # The brief's counting line: 3 escalations, 1 open (E10 absent from the
    # graph; E7 closed by the later landed E7b; E9 withdrawn by a status row).
    runs = tmp_path / "runs"
    _write_escalations(
        runs, [("E7", "r7", "opus"), ("E9", "r9", "sonnet"), ("E10", "r10", "haiku")]
    )
    repo = tmp_path / "repo"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "df6.md").write_text(PLAN)
    task_status = {("repo", "df6.md", "E9"): {"status": "withdrawn", "note": ""}}
    g = tk.scan_repo(
        {"name": "repo", "path": str(repo), "plans": "docs/superpowers/plans/*.md"},
        {},
        str(runs),
        str(tmp_path / "no-store"),
        run=_fake_git(["x: seven b (test: unit)"]),
        task_status=task_status,
    )
    md = tk.render_brief(
        {
            "generated": "t",
            "repos": [g],
            "runs_dir": str(runs),
            "task_status": task_status,
        }
    )
    assert "**Design failures:** 3 (1 open)" in md
    # Negative control: no escalations renders 0 (0 open).
    empty = tk.render_brief({"generated": "t", "repos": [g]})
    assert "**Design failures:** 0 (0 open)" in empty
