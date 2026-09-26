"""The reader's join (plan 2026-09-06-telemetry-store-1, T10a).

`read` learns the monthly ``<name>-YYYY-MM.jsonl`` siblings of a stream;
`join_tasks_gates` pairs every ``derived/tasks`` row with its newest gate on
``(run_id, key)`` and its ``ledger/activity-days`` row on
``(result_mtime[:10], model)``; `n_gate` is the small-n boundary; `bundle`
carries the join counts and the markdown prints the join line.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve()


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "evidence.py",
        pathlib.Path("pkgs/evidence/evidence.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("evidence", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["evidence"] = mod
    spec.loader.exec_module(mod)
    return mod, src


ev, SRC = load()


def task_row(run_id, key, model="m/a", result_mtime="2026-09-01T00:00:00Z"):
    return {
        "kind": "task-result",
        "run_id": run_id,
        "key": key,
        "model": model,
        "result_mtime": result_mtime,
    }


def gate_row(run_id, key, verdict, review_path, review_commit_ts=None):
    return {
        "kind": "gate-verdict",
        "run_id": run_id,
        "key": key,
        "verdict": verdict,
        "review_path": review_path,
        "review_commit_ts": review_commit_ts,
    }


def activity_row(date, model, requests=1):
    return {"kind": "activity-day", "date": date, "model": model, "requests": requests}


def test_join_two_runs_sharing_key_each_reads_its_own_gate(tmp_path):
    # Two runs issue the same key K1; each task's gate must come from its own
    # run, not the newest key-mate. Mutant: joining on `key` alone sees both
    # rows choose the newest (r2's approved) -> red.
    s = str(tmp_path)
    ev.append(s, "derived/tasks", task_row("r1", "K1"))
    ev.append(s, "derived/tasks", task_row("r2", "K1"))
    ev.append(
        s,
        "derived/gates",
        gate_row("r1", "K1", "rejected", "docs/reviews/r1.md", "2026-09-01T10:00:00Z"),
        ts="2026-09-01T10:00:00Z",
    )
    ev.append(
        s,
        "derived/gates",
        gate_row("r2", "K1", "approved", "docs/reviews/r2.md", "2026-09-01T12:00:00Z"),
        ts="2026-09-01T12:00:00Z",
    )
    joined = ev.join_tasks_gates(s)
    by_run = {j["run_id"]: j for j in joined}
    assert by_run["r1"]["gate"]["verdict"] == "rejected"
    assert by_run["r2"]["gate"]["verdict"] == "approved"


def test_join_newest_gate_by_commit_ts_then_ts(tmp_path):
    # Two gate rows for the same (run_id, key): the larger review_commit_ts
    # wins; on an equal review_commit_ts the later envelope ts wins. Mutant:
    # taking the first gate row -> red in both arms.
    s = str(tmp_path)
    ev.append(s, "derived/tasks", task_row("r1", "K1"))
    ev.append(
        s,
        "derived/gates",
        gate_row(
            "r1", "K1", "rejected", "docs/reviews/early.md", "2026-09-01T10:00:00Z"
        ),
        ts="2026-09-01T10:00:00Z",
    )
    ev.append(
        s,
        "derived/gates",
        gate_row(
            "r1", "K1", "approved", "docs/reviews/late.md", "2026-09-01T12:00:00Z"
        ),
        ts="2026-09-01T09:00:00Z",
    )
    assert ev.join_tasks_gates(s)[0]["gate"]["verdict"] == "approved"

    s2 = str(tmp_path / "s2")
    ev.append(s2, "derived/tasks", task_row("r1", "K1"))
    ev.append(
        s2,
        "derived/gates",
        gate_row(
            "r1", "K1", "rejected", "docs/reviews/tie-a.md", "2026-09-02T10:00:00Z"
        ),
        ts="2026-09-02T10:00:00Z",
    )
    ev.append(
        s2,
        "derived/gates",
        gate_row(
            "r1", "K1", "approved", "docs/reviews/tie-b.md", "2026-09-02T10:00:00Z"
        ),
        ts="2026-09-02T11:00:00Z",
    )
    assert ev.join_tasks_gates(s2)[0]["gate"]["verdict"] == "approved"


def test_join_missing_gate_orphan_gate_and_missing_activity(tmp_path):
    # A task with no gate -> gate None; a gate whose (run_id, key) matches no
    # task is absent from the output; an absent activity stream -> activity None
    # for every task without raising. Mutant: a missing stream raises KeyError.
    s = str(tmp_path)
    ev.append(s, "derived/tasks", task_row("r1", "K1"))
    ev.append(
        s,
        "derived/gates",
        gate_row(
            "r9", "K9", "approved", "docs/reviews/orphan.md", "2026-09-01T10:00:00Z"
        ),
    )
    joined = ev.join_tasks_gates(s)
    assert len(joined) == 1
    assert joined[0]["run_id"] == "r1" and joined[0]["key"] == "K1"
    assert joined[0]["gate"] is None
    assert joined[0]["activity"] is None


def test_join_activity_present(tmp_path):
    # A matching (result_mtime[:10], model) activity row joins; a wrong model
    # does not. Mutant: joining on the date alone -> the wrong-model task reads
    # a move.
    s = str(tmp_path)
    ev.append(s, "derived/tasks", task_row("r1", "K1"))
    ev.append(s, "derived/tasks", task_row("r2", "K2", model="m/b"))
    ev.append(s, "ledger/activity-days", activity_row("2026-09-01", "m/a", requests=5))
    joined = {j["key"]: j for j in ev.join_tasks_gates(s)}
    assert joined["K1"]["activity"] is not None
    assert joined["K1"]["activity"]["requests"] == 5
    assert joined["K2"]["activity"] is None


def test_read_includes_monthly_siblings_not_other_files(tmp_path):
    # The base file (2 rows, one torn line), the monthly sibling (1 row), and a
    # non-monthly sibling (ignored) -> 3 rows in file-then-month name order.
    # Mutant: dropping the monthly glob -> 2; admitting any sibling -> 4.
    s = str(tmp_path)
    ev.append(s, "derived/tasks", task_row("r1", "K1"))
    ev.append(s, "derived/tasks", task_row("r2", "K2"))
    with open(tmp_path / "derived" / "tasks.jsonl", "a") as fh:
        fh.write('{"v":1,"ts":"2026-09-01T09:00:00Z","kind":"tas')
    monthly = tmp_path / "derived" / "tasks-2026-09.jsonl"
    monthly.write_text(json.dumps(task_row("r3", "K3")) + "\n")
    (tmp_path / "derived" / "tasks-notamonth.jsonl").write_text(
        json.dumps(task_row("r4", "K4")) + "\n"
    )
    rows = ev.read(s, "derived/tasks")
    assert [r["key"] for r in rows] == ["K1", "K2", "K3"]


def test_n_gate_boundary():
    rows4 = [1, 2, 3, 4]
    assert ev.n_gate(rows4) == "insufficient (n=4)"
    rows5 = [1, 2, 3, 4, 5]
    assert ev.n_gate(rows5) is rows5
    assert ev.n_gate([1, 2, 3], n=3) == [1, 2, 3]


def test_bundle_join_counts_and_markdown(tmp_path):
    s = str(tmp_path)
    ev.append(s, "derived/tasks", task_row("r1", "K1"))
    ev.append(s, "derived/tasks", task_row("r2", "K2"))
    ev.append(s, "derived/tasks", task_row("r3", "K3"))
    ev.append(
        s,
        "derived/gates",
        gate_row("r1", "K1", "approved", "docs/reviews/a.md", "2026-09-01T10:00:00Z"),
    )
    ev.append(
        s,
        "derived/gates",
        gate_row("r2", "K2", "rejected", "docs/reviews/b.md", "2026-09-01T11:00:00Z"),
    )
    b = ev.bundle(
        s,
        str(tmp_path / "norepo"),
        str(tmp_path / "none.toml"),
        [],
        str(tmp_path / "nixos-version"),
        now=dt.datetime(2026, 9, 5, 12, 0, tzinfo=dt.timezone.utc),
    )
    assert b["join"] == {"tasks": 3, "with_gate": 2, "with_activity": 0}
    md = ev.render_bundle_markdown(b)
    assert "## Join: 3 task rows, 2 with a gate verdict, 0 with activity" in md

    b0 = ev.bundle(
        str(tmp_path / "nostore"),
        str(tmp_path / "norepo"),
        str(tmp_path / "none.toml"),
        [],
        str(tmp_path / "nixos-version"),
        now=dt.datetime(2026, 9, 5, 12, 0, tzinfo=dt.timezone.utc),
    )
    assert b0["join"] == {"tasks": 0, "with_gate": 0, "with_activity": 0}
    assert "## Join: 0 task rows, 0 with a gate verdict, 0 with activity" in (
        ev.render_bundle_markdown(b0)
    )
