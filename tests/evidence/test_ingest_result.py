"""Task-result ingest tests (plan 2026-09-06-telemetry-store-1, T2).

``evidence ingest result`` turns a ``.result`` file as ``factory-task`` writes
it into one ``derived/tasks`` row keyed ``(run_id, key)``. Every field is
produced from one line of the file; free text never reaches the stream, the
log beside the result is never opened, and every path is fenced to the runs
root before anything is written.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
FIXTURES = HERE.parent / "fixtures" / "results"
PKG = HERE.parents[2] / "pkgs" / "evidence"

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")


def _first_existing(*names):
    for name in names:
        for cand in (PKG / name, pathlib.Path("pkgs") / "evidence" / name):
            if cand.exists():
                return cand
    raise FileNotFoundError(names)


def _load_ingest():
    candidates = [
        PKG / "ingest_result.py",
        pathlib.Path("pkgs/evidence/ingest_result.py"),
    ]
    src = next(p for p in candidates if p.exists())  # StopIteration when absent
    sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("ingest_result", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ingest_result"] = mod
    spec.loader.exec_module(mod)
    return mod, src


ir, IRSRC = _load_ingest()
import evidence as ev

EVSRC = _first_existing("evidence.py")

REV_A = "a" * 40
REV_B = "b" * 40


def result_text(
    *,
    status="done",
    checks="unit=pass",
    commits_line="1",
    notes="ok",
    run="tel9",
    key="T2",
    model="deepseek/deepseek-v4-pro-0813",
    effort="medium",
    route="implement/code/S",
    plan=None,
    workspace="/gone/base/ws/tel9/T2",
    seat=None,
    head=REV_A,
    base=REV_B,
    wall_s="100",
    exit_code="0",
    error_class=None,
    derived=None,
    commit_lines="abc1234 subject",
    diffstat=" 1 file changed",
    usage='{"input":1,"output":1,"cacheRead":0,"reasoning":0,"events":1,"duration_s":1.0}',
):
    lines = [
        f"FACTORY-RESULT status={status}",
        f"FACTORY-CHECKS {checks}",
        f"FACTORY-COMMITS {commits_line}",
        f"FACTORY-NOTES {notes}",
        "",
        f"run: {run}",
        f"key: {key}",
        f"model: {model}",
        f"effort: {effort}",
        f"route: {route}",
    ]
    if plan is not None:
        lines.append(f"plan: {plan}")
    lines.append(f"workspace: {workspace}")
    if seat is not None:
        lines.append(seat)
    lines += [
        f"head: {head}",
        f"base: {base}",
        f"wall_s: {wall_s}",
        f"exit_code: {exit_code}",
    ]
    if error_class is not None:
        lines.append(f"error_class: {error_class}")
    if derived is not None:
        lines.append(f"derived: {derived}")
    lines += [
        "",
        f"commits (base..task/{key}):",
        commit_lines,
        "",
        "diffstat:",
        diffstat,
        "",
        f"usage: {usage}",
    ]
    return "\n".join(lines) + "\n"


def _runs_root(tmp_path):
    return tmp_path / "factory" / "runs"


def _write(tmp_path, run, key, text, fixture=None):
    d = _runs_root(tmp_path) / run
    d.mkdir(parents=True, exist_ok=True)
    out = d / (key + ".result")
    if fixture is not None:
        out.write_bytes((FIXTURES / fixture).read_bytes())
    else:
        out.write_text(text)
    return out


_store_counter = 0


def _store(tmp_path):
    global _store_counter
    _store_counter += 1
    s = tmp_path / f"store{_store_counter}"
    s.mkdir()
    return s


def run_cli(store, runs_root, *paths, home=None):
    env = dict(os.environ)
    env["HOME"] = str(home)
    return subprocess.run(
        [
            sys.executable,
            str(EVSRC),
            "--store",
            str(store),
            "ingest",
            "result",
            "--runs-root",
            str(runs_root),
            *[str(p) for p in paths],
        ],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def rows_of(store):
    return [
        r
        for r in ev.read(str(store), "derived/tasks")
        if r.get("kind") == "task-result"
    ]


def test_done_result_produces_one_full_row(tmp_path):
    out = _write(tmp_path, "tel2", "T2", None, fixture="done.result")
    store = _store(tmp_path)
    runs_root = _runs_root(tmp_path)
    r = run_cli(store, runs_root, out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    rows = rows_of(store)
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "task-result"
    assert row["run_id"] == "tel2"
    assert row["key"] == "T2"
    assert row["task_kind"] == "code"
    assert row["size"] == "S"
    assert row["route"] == "implement/code/S"
    assert row["model"] == "deepseek/deepseek-v4-pro-0813"
    assert row["effort"] == "medium"
    assert row["status"] == "done"
    assert row["exit_code"] == 0
    assert row["wall_s"] == 123
    assert row["commits"] == 1
    assert row["commits_declared"] == 1
    assert row["checks"] == {"unit": "pass", "lint": "pass"}
    assert row["checks_parse"] == "ok"
    assert row["head"] == REV_A
    assert row["base"] == REV_B
    assert row["files_changed"] == 2
    assert row["insertions"] == 10
    assert row["deletions"] == 3
    assert row["usage"] == {
        "in": 10,
        "out": 5,
        "cache_read": 1,
        "reasoning": 2,
        "events": 40,
        "duration_s": 12.5,
    }
    assert row["error_class"] == "none"
    assert row["seat_unit"] is None
    assert row["plan"] is None
    assert row["result_path"] == os.path.realpath(str(out))
    assert TS_RE.match(row["result_mtime"])


def test_codex_result_ingests_one_full_row(tmp_path):
    # CX1b-shaped result: route `codex/code/XS` names the kind/size, the
    # `seat: codex <uuid>` line matches neither the unit nor the submit regex
    # and is ignored, and a gone workspace yields repo None.
    # mutant: ROUTE_IMPL_RE unchanged -> `route == "unknown"`; a capturing
    # family group -> `task_kind == "codex"`; SEAT_UNIT_RE widened to
    # `seat: (unit seat@|codex )…` -> `seat_unit` is not None.
    out = _write(tmp_path, "cx1b", "CX1b", None, fixture="codex.result")
    store = _store(tmp_path)
    runs_root = _runs_root(tmp_path)
    r = run_cli(store, runs_root, out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    assert "ingested 1 rows into derived/tasks (0 refused)" in r.stdout
    rows = rows_of(store)
    assert len(rows) == 1
    row = rows[0]
    assert row["route"] == "codex/code/XS"
    assert row["task_kind"] == "code"
    assert row["size"] == "XS"
    assert row["model"] == "gpt-6-astra"
    assert row["effort"] == "medium"
    assert row["commits"] == 5
    assert row["commits_declared"] == 5
    assert row["usage"] == {
        "in": 68620,
        "out": 13584,
        "cache_read": 1642368,
        "reasoning": 3631,
        "events": 239,
        "duration_s": 2400.0,
    }
    assert row["seat_unit"] is None
    assert row["error_class"] == "none"
    assert row["repo"] is None
    assert row["files_changed"] == 15


def test_codex_route_family_arms(tmp_path):
    # One payload per fence arm: a non-codex/<kind>/<size> value is unknown (the
    # unknown arm, never a refusal); the valid docs arm parses through.
    # mutant: `[a-z]+` for the kind -> `codex/any/any` accepted; `re.match`
    # instead of `fullmatch` -> the `/x` suffix accepted; `re.IGNORECASE` ->
    # `Codex/code/XS` accepted.
    for route in (
        "codex/any/any",
        "codex/code/XL",
        "Codex/code/XS",
        "codex/code/XS/x",
    ):
        out = _write(tmp_path, "cx1b", "CX2", result_text(route=route))
        store = _store(tmp_path)
        r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
        assert r.returncode == 0, r.stderr
        row = rows_of(store)[0]
        assert row["route"] == "unknown"
        assert row["task_kind"] == "unknown"
        assert row["size"] == "unknown"

    out = _write(tmp_path, "cx1b", "CX3", result_text(route="codex/docs/M"))
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["route"] == "codex/docs/M"
    assert row["task_kind"] == "docs"
    assert row["size"] == "M"


def test_touches_result_ingests_touches_counts(tmp_path):
    # touches.result carries both lines and a touches-violation error_class; the
    # counts reach the row but the not-a-field touches_files line never does.
    out = _write(tmp_path, "tel2", "T2", None, fixture="touches.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["touches_extra"] == 1
    assert row["touches_disclosed"] == 0
    assert row["error_class"] == "touches-violation"
    assert "touches_files" not in row

    # done.result carries neither line -> both None, never a default 0.
    out2 = _write(tmp_path, "tel9", "T9", None, fixture="done.result")
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    row2 = rows_of(store2)[0]
    assert row2["touches_extra"] is None
    assert row2["touches_disclosed"] is None

    # A non-integer count reads None and the row still lands.
    text = result_text() + "touches_extra: many\n"
    out3 = _write(tmp_path, "tel9", "T9", text)
    store3 = _store(tmp_path)
    r3 = run_cli(store3, _runs_root(tmp_path), out3, home=tmp_path)
    assert r3.returncode == 0, r3.stderr
    assert rows_of(store3)[0]["touches_extra"] is None


def test_status_pass_is_unknown_and_missing_result_line_is_refused(tmp_path):
    # status=pass is not in the done|partial|failed|skipped enum -> unknown.
    out = _write(tmp_path, "tel2", "T2", None, fixture="status-pass.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    assert rows_of(store)[0]["status"] == "unknown"

    # A file with run:/key: but no FACTORY-RESULT status= line is refused.
    bad = _write(tmp_path, "tel2", "T3", "run: tel2\nkey: T3\nmodel: m/a\n")
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), bad, home=tmp_path)
    assert r2.returncode == 1
    assert f"evidence: ingest result: {bad}: not a result file" in r2.stderr
    assert rows_of(store2) == []


def test_last_status_line_wins(tmp_path):
    # Two FACTORY-RESULT status= lines (failed first, done last) -> the last
    # word wins, so the row lands with status done.
    out = _write(tmp_path, "tel2", "T2", None, fixture="two-status-lines.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    assert rows_of(store)[0]["status"] == "done"


def test_missing_run_or_key_line_refused(tmp_path):
    # A file with a status line but no run: line -> refused, nothing written.
    out = _write(tmp_path, "tel2", "T2", None, fixture="no-run-line.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 1
    assert f"evidence: ingest result: {out}: not a result file" in r.stderr
    assert rows_of(store) == []

    # A file with a status line but no key: line -> refused, nothing written.
    out2 = _write(tmp_path, "tel2", "T3", None, fixture="no-key-line.result")
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 1
    assert f"evidence: ingest result: {out2}: not a result file" in r2.stderr
    assert rows_of(store2) == []


def test_hostile_checks_refused_and_never_stored(tmp_path):
    # A 4096-char key (over the 63-char name fence) -> refused parse, row lands.
    out = _write(tmp_path, "tel3", "T2", None, fixture="hostile-checks.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["checks"] == {}
    assert row["checks_parse"] == "refused"
    # No key over 64 chars survived into the store.
    assert all(len(k) <= 64 for rr in rows_of(store) for k in rr["checks"])

    # A forbidden name ("log") -> refused parse, row lands.
    out2 = _write(tmp_path, "tel3", "T3", result_text(checks="log=pass unit=pass"))
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    row2 = rows_of(store2)[0]
    assert row2["checks"] == {}
    assert row2["checks_parse"] == "refused"

    # Bare FACTORY-CHECKS none -> refused.
    out3 = _write(tmp_path, "tel3", "T4", result_text(checks="none"))
    store3 = _store(tmp_path)
    r3 = run_cli(store3, _runs_root(tmp_path), out3, home=tmp_path)
    assert r3.returncode == 0, r3.stderr
    assert rows_of(store3)[0]["checks_parse"] == "refused"

    # No FACTORY-CHECKS line at all -> missing.
    out4 = _write(
        tmp_path,
        "tel3",
        "T5",
        result_text().replace("FACTORY-CHECKS unit=pass\n", ""),
    )
    store4 = _store(tmp_path)
    r4 = run_cli(store4, _runs_root(tmp_path), out4, home=tmp_path)
    assert r4.returncode == 0, r4.stderr
    assert rows_of(store4)[0]["checks_parse"] == "missing"

    # 64 good tokens -> ok.
    good = " ".join(f"c{i}=pass" for i in range(64))
    out5 = _write(tmp_path, "tel3", "T6", result_text(checks=good))
    store5 = _store(tmp_path)
    r5 = run_cli(store5, _runs_root(tmp_path), out5, home=tmp_path)
    assert r5.returncode == 0, r5.stderr
    assert rows_of(store5)[0]["checks_parse"] == "ok"

    # 65 tokens -> refused (over the 64-token cap).
    over = " ".join(f"c{i}=pass" for i in range(65))
    out6 = _write(tmp_path, "tel3", "T7", result_text(checks=over))
    store6 = _store(tmp_path)
    r6 = run_cli(store6, _runs_root(tmp_path), out6, home=tmp_path)
    assert r6.returncode == 0, r6.stderr
    assert rows_of(store6)[0]["checks_parse"] == "refused"


def test_template_echo_error_class(tmp_path):
    # status done with (no commits) -> template-echo, commits 0.
    out = _write(tmp_path, "tel4", "T2", None, fixture="template-echo.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["error_class"] == "template-echo"
    assert row["commits"] == 0

    # A CR3r-demoted result: status failed, notes "status=done but the branch
    # has no commits" -> template-echo (the notes arm, not the zero-commit arm).
    txt = result_text(
        status="failed",
        notes="status=done but the branch has no commits",
        commits_line="0",
        commit_lines="(no commits)",
    )
    out2 = _write(tmp_path, "tel4", "T3", txt)
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert rows_of(store2)[0]["error_class"] == "template-echo"


def test_timeout_and_submit_precedence(tmp_path):
    # exit_code 124 -> timeout.
    out = _write(tmp_path, "tel5", "T2", None, fixture="timeout.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    assert rows_of(store)[0]["error_class"] == "timeout"

    # exit_code 124 plus "seat: submit failed" -> submit-failed wins.
    txt = result_text(
        status="failed",
        checks="none=not-run",
        notes="seat-submit produced no valid job id; see /gone/log",
        seat="seat: submit failed (no job id)",
        exit_code="124",
        commit_lines="(no commits)",
    )
    out2 = _write(tmp_path, "tel5", "T3", txt)
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert rows_of(store2)[0]["error_class"] == "submit-failed"


def test_submit_failed_no_result_boot_failure(tmp_path):
    out = _write(tmp_path, "tel6", "T2", None, fixture="submit-failed.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["error_class"] == "submit-failed"
    assert row["seat_unit"] is None

    out2 = _write(tmp_path, "tel7", "T2", None, fixture="no-result-line.result")
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert rows_of(store2)[0]["error_class"] == "no-result-line"

    # wall_s 3, events 10, status failed -> boot-failure.
    txt = result_text(
        status="failed",
        checks="none=not-run",
        notes="x",
        wall_s="3",
        commit_lines="(no commits)",
        usage='{"input":1,"output":1,"cacheRead":0,"reasoning":0,"events":10,"duration_s":1.0}',
    )
    out3 = _write(tmp_path, "tel7", "T3", txt)
    store3 = _store(tmp_path)
    r3 = run_cli(store3, _runs_root(tmp_path), out3, home=tmp_path)
    assert r3.returncode == 0, r3.stderr
    assert rows_of(store3)[0]["error_class"] == "boot-failure"

    # Same timing but status done -> none.
    txt4 = result_text(
        wall_s="3",
        commit_lines="abc1234 subject",
        usage='{"input":1,"output":1,"cacheRead":0,"reasoning":0,"events":10,"duration_s":1.0}',
    )
    out4 = _write(tmp_path, "tel7", "T4", txt4)
    store4 = _store(tmp_path)
    r4 = run_cli(store4, _runs_root(tmp_path), out4, home=tmp_path)
    assert r4.returncode == 0, r4.stderr
    assert rows_of(store4)[0]["error_class"] == "none"


def test_classified_line_wins_over_fallback(tmp_path):
    out = _write(tmp_path, "tel8", "T2", None, fixture="classified.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    assert rows_of(store)[0]["error_class"] == "provider-error"


def test_plan_mapping_and_seat_unit(tmp_path):
    # A plan path under docs/superpowers/plans/ is mapped to its repo-relative
    # form (the fence refuses the absolute form, so the row only lands mapped).
    txt = result_text(
        plan="/home/x/nixos-agent-env/docs/superpowers/plans/p.md",
        seat="seat: unit seat@20260906-101010-abcdef",
    )
    out = _write(tmp_path, "tel9", "T2", txt)
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["plan"] == "docs/superpowers/plans/p.md"
    assert row["seat_unit"] == "20260906-101010-abcdef"

    # A plan path outside docs/superpowers/plans/ -> None.
    out2 = _write(tmp_path, "tel9", "T3", result_text(plan="/tmp/p.md"))
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert rows_of(store2)[0]["plan"] is None


def test_outside_root_and_missing_file(tmp_path):
    store = _store(tmp_path)
    runs_root = _runs_root(tmp_path)
    # A path outside the runs root -> exit 2, nothing written.
    r = run_cli(store, runs_root, "/etc/passwd", home=tmp_path)
    assert r.returncode == 2
    assert "is outside" in r.stderr
    assert not (store / "derived" / "tasks.jsonl").exists()

    # All paths are checked before any write: good + outside -> exit 2, nothing.
    good = _write(tmp_path, "tel9", "T2", result_text())
    store2 = _store(tmp_path)
    r2 = run_cli(store2, runs_root, good, "/etc/passwd", home=tmp_path)
    assert r2.returncode == 2
    assert not (store2 / "derived" / "tasks.jsonl").exists()

    # A path inside the root but missing on disk -> not a result file, refused.
    missing = runs_root / "tel9" / "nope.result"
    store3 = _store(tmp_path)
    r3 = run_cli(store3, runs_root, missing, home=tmp_path)
    assert r3.returncode == 1
    assert f"evidence: ingest result: {missing}: not a result file" in r3.stderr
    assert "Traceback" not in r3.stderr


def test_reingest_idempotent_and_same_key_later_replaces(tmp_path):
    out = _write(tmp_path, "tel9", "T2", result_text())
    store = _store(tmp_path)
    runs_root = _runs_root(tmp_path)
    r = run_cli(store, runs_root, out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    first = (store / "derived" / "tasks.jsonl").read_bytes()
    assert len(rows_of(store)) == 1

    # Re-ingesting the identical file leaves one row, bytes identical.
    r2 = run_cli(store, runs_root, out, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert (store / "derived" / "tasks.jsonl").read_bytes() == first
    assert len(rows_of(store)) == 1

    # Two files with the same (run, key) in different dirs: the later replaces.
    txt = result_text(run="tel9", key="T2", effort="off")
    out_a = _write(tmp_path, "tel9a", "T2", txt)
    out_b = _write(tmp_path, "tel9b", "T2", txt.replace("effort: off", "effort: high"))
    store2 = _store(tmp_path)
    r3 = run_cli(store2, runs_root, out_a, out_b, home=tmp_path)
    assert r3.returncode == 0, r3.stderr
    rows = rows_of(store2)
    assert len(rows) == 1
    assert rows[0]["effort"] == "high"
    assert rows[0]["result_path"] == os.path.realpath(str(out_b))


def test_unknown_effort_route_and_refused_model(tmp_path):
    # effort: max is outside the enum -> unknown.
    out = _write(tmp_path, "tel9", "T2", result_text(effort="max"))
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["effort"] == "unknown"

    # route: bogus -> route/kind/size all unknown; a missing route is the same.
    out2 = _write(tmp_path, "tel9", "T3", result_text(route="bogus"))
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    row2 = rows_of(store2)[0]
    assert row2["route"] == "unknown"
    assert row2["task_kind"] == "unknown"
    assert row2["size"] == "unknown"

    out3 = _write(
        tmp_path, "tel9", "T4", result_text().replace("route: implement/code/S\n", "")
    )
    store3 = _store(tmp_path)
    r3 = run_cli(store3, _runs_root(tmp_path), out3, home=tmp_path)
    assert r3.returncode == 0, r3.stderr
    row3 = rows_of(store3)[0]
    assert row3["route"] == "unknown"
    assert row3["task_kind"] == "unknown"
    assert row3["size"] == "unknown"

    # A model that is not a model-id refuses the row (others still land), exit 1.
    good = _write(tmp_path, "tel9", "T5", result_text(key="T5"))
    bad = _write(tmp_path, "tel9", "T6", result_text(key="T6", model="Bad/Model"))
    store4 = _store(tmp_path)
    r4 = run_cli(store4, _runs_root(tmp_path), good, bad, home=tmp_path)
    assert r4.returncode == 1
    assert "model: not a model-id" in r4.stderr
    rows = rows_of(store4)
    assert [row["key"] for row in rows] == ["T5"]
    assert "ingested 1 rows into derived/tasks (1 refused)" in r4.stdout


def test_repo_from_workspace(tmp_path):
    # A workspace clone whose origin is .../base/<name> -> repo <name>.
    ws = tmp_path / "ws" / "tel9" / "T2"
    (ws / ".git").mkdir(parents=True)
    (ws / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = /x/base/nixos-agent-env\n'
    )
    out = _write(tmp_path, "tel9", "T2", result_text(workspace=str(ws)))
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    assert rows_of(store)[0]["repo"] == "nixos-agent-env"

    # No clone -> repo None.
    out2 = _write(tmp_path, "tel9", "T3", result_text(workspace="/gone/ws"))
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert rows_of(store2)[0]["repo"] is None


def test_log_beside_result_is_never_opened(tmp_path):
    # A 000-mode log beside the result must not stop the ingest: the log is
    # never opened for the metadata-only fallback. Skipped as root (root can
    # read anything); otherwise the ingest succeeds despite the unreadable log.
    out = _write(tmp_path, "tel9", "T2", result_text())
    log = out.with_suffix(".log")
    log.write_text("provider: DeepInfra\n")
    log.chmod(0)
    if os.geteuid() == 0:
        # Root ignores mode bits; still prove the ingest does not touch the log
        # by removing it entirely (the parse needs only the .result).
        log.unlink()
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    assert rows_of(store)[0]["error_class"] == "none"


def test_unreported_result_row_and_derived_field(tmp_path):
    # status=unreported is the driver's own "a result block was completed from
    # the git facts after the seat's block was lost" word; `derived` labels
    # which lines the driver derived. mutant: leave `unreported` out of
    # STATUS_WORDS -> the status collapses to `unknown`; or default `derived`
    # to [] -> the done.result None assertion goes red.
    out = _write(tmp_path, "sh1", "SH2", None, fixture="unreported.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["status"] == "unreported"
    assert row["commits"] == 1
    assert row["commits_declared"] == 1
    assert row["derived"] == ["checks", "commits"]
    assert row["error_class"] == "no-result-line"

    # done.result carries no derived: line -> derived None.
    out2 = _write(tmp_path, "tel9", "T9", None, fixture="done.result")
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert rows_of(store2)[0]["derived"] is None

    # a derived: token outside the enum refuses the row (counted refused, exit 1).
    txt = result_text(status="unreported", derived="bogus")
    out3 = _write(tmp_path, "sh1", "SH3", txt)
    store3 = _store(tmp_path)
    r3 = run_cli(store3, _runs_root(tmp_path), out3, home=tmp_path)
    assert r3.returncode == 1
    assert "derived[0]: not in enum" in r3.stderr
    assert rows_of(store3) == []


def test_checks_verified_ingest(tmp_path):
    # checks.result carries checks_verified/checks_scope/checks_scope_files/verify_s
    # and the never-ingested checks_verified_src/checks_scope_list lines. mutant:
    # store a partial map -> checks_verified None; ingest checks_scope_list -> the
    # row is refused by the fence (assert the row still lands).
    out = _write(tmp_path, "tel2", "T2", None, fixture="checks.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["checks_verified"] == {"unit": "pass", "lint": "not-run:cache-miss"}
    assert row["checks_scope"] == "dirty"
    assert row["checks_scope_files"] == 2
    assert row["verify_s"] == 41
    assert "checks_verified_src" not in row
    assert "checks_scope_list" not in row

    # a verdict outside the five-arm enum -> checks_verified None (never partial).
    txt = result_text() + "checks_verified: unit=maybe\n"
    out2 = _write(tmp_path, "tel9", "T9", txt)
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert rows_of(store2)[0]["checks_verified"] is None

    # done.result carries none of the four -> all None.
    out3 = _write(tmp_path, "tel9", "T9", None, fixture="done.result")
    store3 = _store(tmp_path)
    r3 = run_cli(store3, _runs_root(tmp_path), out3, home=tmp_path)
    assert r3.returncode == 0, r3.stderr
    row3 = rows_of(store3)[0]
    assert row3["checks_verified"] is None
    assert row3["checks_scope"] is None
    assert row3["checks_scope_files"] is None
    assert row3["verify_s"] is None


def test_probes_verified_ingest(tmp_path):
    # probes.result carries probes_verified + the never-ingested probe_values /
    # probe_env lines and a probe-mismatch error_class. mutant: store probe_values
    # -> the fence refuses the row (assert the row lands); parse a partial map ->
    # probes_verified None.
    out = _write(tmp_path, "tel2", "T2", None, fixture="probes.result")
    store = _store(tmp_path)
    r = run_cli(store, _runs_root(tmp_path), out, home=tmp_path)
    assert r.returncode == 0, r.stderr
    row = rows_of(store)[0]
    assert row["probes_verified"] == {"readme-bytes": "fail"}
    assert row["error_class"] == "probe-mismatch"
    assert "probe_values" not in row
    assert "probe_env" not in row

    # a verdict outside the five-arm enum -> probes_verified None (never partial).
    txt = result_text() + "probes_verified: readme-bytes=maybe\n"
    out2 = _write(tmp_path, "tel9", "T9", txt)
    store2 = _store(tmp_path)
    r2 = run_cli(store2, _runs_root(tmp_path), out2, home=tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert rows_of(store2)[0]["probes_verified"] is None

    # done.result carries no probes_verified line -> None.
    out3 = _write(tmp_path, "tel9", "T9", None, fixture="done.result")
    store3 = _store(tmp_path)
    r3 = run_cli(store3, _runs_root(tmp_path), out3, home=tmp_path)
    assert r3.returncode == 0, r3.stderr
    assert rows_of(store3)[0]["probes_verified"] is None
