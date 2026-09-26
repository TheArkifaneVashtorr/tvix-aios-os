"""Tests for pkgs/seat/seat-submit.py (plan 2026-09-05-seat-behind-broker,
SB3).

Drives the script in-process (imported by path -- seat-submit.py is a
hyphenated filename, not an importable module, so importlib.util loads it the
way tests/lane/test_lane_submit.py loads pkgs/lane/lane-submit.py) rather than
as a subprocess. Every test passes --jobs-dir pointing at tmp_path and
--no-start, so no real /var/lib/seat spool or systemd unit is touched; the
`systemctl start` call is monkeypatched out anyway so a regression that drops
--no-start cannot reach a real unit.

The script refuses a --workspace that is not a directory and a --brief that is
unreadable (exit 2), writes <id>/job.json + brief.txt inside a 0700 job dir,
prints the job id, and -- under --no-start -- does nothing further.
"""

import datetime
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "seat" / "seat-submit.py"
spec = importlib.util.spec_from_file_location("seat_submit", SRC)
seat_submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seat_submit)

ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")


@pytest.fixture(autouse=True)
def _no_systemctl(monkeypatch):
    """Replaces subprocess.run so `systemctl start` can never touch a real
    unit; records the argv it would have run."""
    calls = []

    def _run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(seat_submit.subprocess, "run", _run)
    return calls


def _submit(argv, monkeypatch):
    """Runs cmd_submit, capturing stdout (the printed job id + streamed unit
    stdout) and stderr separately."""
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    rc = seat_submit.cmd_submit(argv)
    return rc, out.getvalue(), err.getvalue()


def _job_dir(jobs_dir, printed_id):
    return Path(jobs_dir) / printed_id.strip()


@pytest.fixture
def ws(tmp_path):
    d = tmp_path / "ws"
    d.mkdir()
    return d


@pytest.fixture
def dsh(tmp_path):
    d = tmp_path / "dsh"
    d.mkdir()
    return d


def test_no_start_headless_writes_job_dir_files_and_prints_id(
    ws, dsh, tmp_path, monkeypatch
):
    jobs = tmp_path / "jobs"
    argv = [
        "--jobs-dir",
        str(jobs),
        "--no-start",
        "headless",
        "--workspace",
        str(ws),
        "--dsh-home",
        str(dsh),
        "--model",
        "deepseek/deepseek-v4-pro-0813",
        "--effort",
        "medium",
        "--brief",
        str(tmp_path / "brief.txt"),
    ]
    (tmp_path / "brief.txt").write_text("do the task\n")

    rc, printed, _ = _submit(argv, monkeypatch)

    assert rc == 0
    job_id = printed.strip()
    assert ID_RE.match(job_id), f"bad id format: {job_id!r}"
    job_dir = _job_dir(jobs, job_id)

    # The job dir is 0700 and owned by the invoking user.
    st = job_dir.stat()
    assert st.st_mode & 0o777 == 0o700
    assert st.st_uid == os.getuid()

    # job.json has exactly the shape the unit (SB1) reads.
    job_path = job_dir / "job.json"
    assert job_path.is_file()
    job = json.loads(job_path.read_text())
    submitted = job.pop("submitted")
    assert datetime.datetime.fromisoformat(submitted)
    assert job == {
        "mode": "headless",
        "workspace": str(ws),
        "dsh_home": str(dsh),
        "model": "deepseek/deepseek-v4-pro-0813",
        "effort": "medium",
        "brief": "brief.txt",
        "port": None,
    }

    # The brief is copied to brief.txt with the source's content.
    assert (job_dir / "brief.txt").read_text() == "do the task\n"

    # --no-start: nothing further is created (no result/stdout/exit files).
    assert not (job_dir / "result.txt").exists()
    assert not (job_dir / "stdout.txt").exists()
    assert not (job_dir / "exit_code.txt").exists()


def test_web_mode_records_port_and_null_brief(ws, dsh, tmp_path, monkeypatch):
    jobs = tmp_path / "jobs"
    argv = [
        "--jobs-dir",
        str(jobs),
        "--no-start",
        "web",
        "--workspace",
        str(ws),
        "--dsh-home",
        str(dsh),
        "--model",
        "x/y",
        "--effort",
        "low",
        "--port",
        "43210",
    ]

    rc, printed, _ = _submit(argv, monkeypatch)
    assert rc == 0
    job_dir = _job_dir(jobs, printed)
    job = json.loads((job_dir / "job.json").read_text())
    assert job["mode"] == "web"
    assert job["port"] == 43210
    assert job["brief"] is None
    assert not (job_dir / "brief.txt").exists()


def test_missing_workspace_exits_2(tmp_path, monkeypatch):
    argv = [
        "--jobs-dir",
        str(tmp_path / "jobs"),
        "--no-start",
        "headless",
        "--workspace",
        str(tmp_path / "nope"),
        "--dsh-home",
        str(tmp_path / "dsh"),
        "--model",
        "m",
        "--effort",
        "off",
    ]
    rc, _, _ = _submit(argv, monkeypatch)
    assert rc == 2


def test_unreadable_brief_exits_2(ws, dsh, tmp_path, monkeypatch):
    brief = tmp_path / "brief.txt"
    brief.write_text("x")
    brief.chmod(0o000)
    argv = [
        "--jobs-dir",
        str(tmp_path / "jobs"),
        "--no-start",
        "headless",
        "--workspace",
        str(ws),
        "--dsh-home",
        str(dsh),
        "--model",
        "m",
        "--effort",
        "off",
        "--brief",
        str(brief),
    ]
    try:
        rc, _, err = _submit(argv, monkeypatch)
        assert rc == 2
        assert f"--brief {brief}" in err
        assert "not readable" in err
    finally:
        brief.chmod(0o600)


def test_no_start_never_calls_systemctl(ws, dsh, tmp_path, monkeypatch, _no_systemctl):
    argv = [
        "--jobs-dir",
        str(tmp_path / "jobs"),
        "--no-start",
        "headless",
        "--workspace",
        str(ws),
        "--dsh-home",
        str(dsh),
        "--model",
        "m",
        "--effort",
        "off",
    ]
    rc, _, _ = _submit(argv, monkeypatch)
    assert rc == 0
    # --no-start must return before the systemctl start: the recorded calls
    # list (what subprocess.run would have run) is empty.
    assert _no_systemctl == []


@pytest.mark.parametrize("exit_code", ["0", "3"])
def test_headless_waits_streams_and_propagates_exit_code(
    ws, dsh, tmp_path, monkeypatch, _no_systemctl, exit_code
):
    jobs = tmp_path / "jobs"
    argv = [
        "--jobs-dir",
        str(jobs),
        "headless",
        "--workspace",
        str(ws),
        "--dsh-home",
        str(dsh),
        "--model",
        "m",
        "--effort",
        "off",
    ]
    monkeypatch.setattr(seat_submit, "POLL_INTERVAL", 0)

    def _sleep(_seconds):
        # Stand in for the unit's seat-run(SB1): on the poll loop's first
        # sleep, populate the job dir with the unit's results.
        job_id = _no_systemctl[0][2][len("seat@") :]
        jd = jobs / job_id
        (jd / "result.txt").write_text("done\n")
        (jd / "stdout.txt").write_text("unit-stdout-content\n")
        (jd / "exit_code.txt").write_text(exit_code + "\n")

    monkeypatch.setattr(seat_submit.time, "sleep", _sleep)

    rc, out, _ = _submit(argv, monkeypatch)

    # headless waits for result.txt, then copies stdout.txt to its own stdout
    # (after the job id it prints up front) and exits with exit_code.txt.
    printed_id = out.splitlines()[0]
    assert ID_RE.match(printed_id)
    assert out.endswith("unit-stdout-content\n")
    assert rc == int(exit_code)
    assert _no_systemctl == [["systemctl", "start", f"seat@{printed_id}"]]


def test_timeout_exits_124_and_stops_the_unit(
    ws, dsh, tmp_path, monkeypatch, _no_systemctl
):
    jobs = tmp_path / "jobs"
    argv = [
        "--jobs-dir",
        str(jobs),
        "headless",
        "--workspace",
        str(ws),
        "--dsh-home",
        str(dsh),
        "--model",
        "m",
        "--effort",
        "off",
        "--timeout",
        "1",
    ]
    # The unit never writes result.txt; make the poll loop burn through the
    # tiny timeout immediately (no 2 s sleeps) and without touching the wall
    # clock.
    clock = {"t": 0.0}
    monkeypatch.setattr(
        seat_submit.time,
        "time",
        lambda: clock.__setitem__("t", clock["t"] + 1000.0) or clock["t"],
    )
    monkeypatch.setattr(seat_submit.time, "sleep", lambda _s: None)

    rc, out, err = _submit(argv, monkeypatch)

    # A timed-out job must not be orphaned: exit 124, and the unit is stopped.
    printed_id = out.strip()
    assert ID_RE.match(printed_id)
    assert rc == 124
    assert "timed out" in err
    assert _no_systemctl == [
        ["systemctl", "start", f"seat@{printed_id}"],
        ["systemctl", "stop", f"seat@{printed_id}"],
    ]


def test_permission_error_on_jobs_dir_exits_2(ws, dsh, tmp_path, monkeypatch):
    argv = [
        "--jobs-dir",
        str(tmp_path / "jobs"),
        "--no-start",
        "headless",
        "--workspace",
        str(ws),
        "--dsh-home",
        str(dsh),
        "--model",
        "m",
        "--effort",
        "off",
    ]

    def _denied(*_args, **_kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(seat_submit.os, "makedirs", _denied)

    rc, _, err = _submit(argv, monkeypatch)

    # A job-dir creation failure is a clean exit 2 with a message, not an
    # uncaught traceback.
    assert rc == 2
    assert "could not create job directory" in err
