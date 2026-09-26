"""Tests for pkgs/seat/seat-spool.py (plan 2026-09-06-seat-driver, SD6).

Drives the script in-process (imported by path, the same way
test_seat_submit.py loads seat-submit.py -- a hyphenated filename is not an
importable module). `subprocess.run` is replaced by a recorder so `systemctl
start` can never touch a real unit, and every test passes --jobs-dir and
--spool-dir pointing at tmp_path (no real /var/lib/seat spool).

`seat-spool` is the one host-side actor the seat may reach: it validates a job
directory against the contract seat-submit wrote, unlinks the marker (always,
valid or not), starts exactly one `seat@<id>` per marker, and records the start
in `<id>/.spooled` (the id inside). A refusal is not a failure: the spool exits
0, prints `seat-spool: refused <id>: <code>` to stderr, and starts nothing. An
unreadable spool dir is exit 1.
"""

import importlib.util
import io
import json
import os
import pwd
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "seat" / "seat-spool.py"
spec = importlib.util.spec_from_file_location("seat_spool", SRC)
seat_spool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seat_spool)

GOOD_ID = "20260906-000000-abcdef"
CURRENT_USER = pwd.getpwuid(os.getuid()).pw_name


@pytest.fixture
def _run(monkeypatch):
    """Replaces subprocess.run with a recorder so `systemctl start` can never
    touch a real unit; returns the recorded argv list. The IS1c cap count
    (`systemctl list-units`) is answered with zero units (below the cap) and
    not recorded -- a read, not a start/stop the tests below pin."""
    calls = []

    def _fake_run(argv, **kwargs):
        if argv[:2] == ["systemctl", "list-units"]:
            return subprocess.CompletedProcess(argv, 0, stdout="")
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(seat_spool.subprocess, "run", _fake_run)
    return calls


def _base(tmp_path):
    """A jobs dir, a spool dir, and the two absolute directories a valid
    headless job references (workspace, dsh_home)."""
    jobs = tmp_path / "jobs"
    spool = tmp_path / "spool"
    jobs.mkdir()
    spool.mkdir()
    ws = tmp_path / "ws"
    dsh = tmp_path / "dsh"
    ws.mkdir()
    dsh.mkdir()
    return jobs, spool, ws, dsh


def _job_dict(ws, dsh, **overrides):
    """The valid headless job.json, one field broken per refusal test."""
    job = {
        "mode": "headless",
        "workspace": str(ws),
        "dsh_home": str(dsh),
        "model": "deepseek/deepseek-v4-flash",
        "effort": "off",
        "brief": "brief.txt",
        "port": None,
    }
    job.update(overrides)
    return job


def _write_job(jobs, mid, js, mode=0o700, brief=True):
    d = jobs / mid
    d.mkdir(mode=mode)
    (d / "job.json").write_text(json.dumps(js))
    if brief:
        (d / "brief.txt").write_text("do the task\n")
    return d


def _marker(spool, mid):
    (spool / mid).write_text("")


def _run_spool(monkeypatch, jobs, spool, owner=None):
    argv = [
        "--jobs-dir",
        str(jobs),
        "--spool-dir",
        str(spool),
        "--owner",
        owner or CURRENT_USER,
    ]
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    rc = seat_spool.main(argv)
    return rc, out.getvalue(), err.getvalue()


def _refused(monkeypatch, _run, jobs, spool, mid, code, owner=None):
    """Runs the spool and asserts the one refusal code, an empty recorder, and
    that the marker is gone."""
    rc, _, err = _run_spool(monkeypatch, jobs, spool, owner=owner)
    assert rc == 0
    assert _run == []
    assert not (spool / mid).exists()
    assert f"seat-spool: refused {mid}: {code}" in err


def test_happy_path_starts_and_writes_spooled(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh))
    _marker(spool, GOOD_ID)

    rc, out, err = _run_spool(monkeypatch, jobs, spool)

    assert rc == 0
    assert err == ""
    assert _run == [["systemctl", "start", "--no-block", f"seat@{GOOD_ID}"]]
    assert f"seat-spool: started seat@{GOOD_ID}" in out
    # The marker is consumed, and .spooled records the id (0600).
    assert not (spool / GOOD_ID).exists()
    spooled = jobs / GOOD_ID / ".spooled"
    assert spooled.is_file()
    assert spooled.stat().st_mode & 0o777 == 0o600
    assert spooled.read_text() == GOOD_ID


def test_two_markers_start_in_sorted_order(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    a = "20260906-000000-aaaaaa"
    b = "20260906-000000-bbbbbb"
    for mid in (b, a):  # created out of order: the spool sorts
        _write_job(jobs, mid, _job_dict(ws, dsh))
        _marker(spool, mid)

    rc, out, _ = _run_spool(monkeypatch, jobs, spool)

    assert rc == 0
    assert _run == [
        ["systemctl", "start", "--no-block", f"seat@{a}"],
        ["systemctl", "start", "--no-block", f"seat@{b}"],
    ]
    assert f"seat-spool: started seat@{a}" in out
    assert f"seat-spool: started seat@{b}" in out


def test_unreadable_spool_dir_exits_1(monkeypatch, tmp_path, _run):
    jobs, _, _, _ = _base(tmp_path)

    rc, _, err = _run_spool(monkeypatch, jobs, tmp_path / "nope")

    assert rc == 1
    assert _run == []
    assert f"seat-spool: cannot read {tmp_path / 'nope'}" in err


def test_start_failed_still_unlinks_the_marker(monkeypatch, tmp_path):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh))
    _marker(spool, GOOD_ID)

    calls = []

    def _fail(argv, **kwargs):
        if argv[:2] == ["systemctl", "list-units"]:
            # below the cap, so the start is reached and made to fail
            return subprocess.CompletedProcess(argv, 0, stdout="")
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 1)

    monkeypatch.setattr(seat_spool.subprocess, "run", _fail)

    rc, out, _ = _run_spool(monkeypatch, jobs, spool)

    assert rc == 0
    assert calls == [["systemctl", "start", "--no-block", f"seat@{GOOD_ID}"]]
    # The marker is unlinked before the start, so a failed start never re-fires.
    assert not (spool / GOOD_ID).exists()
    assert f"seat-spool: start failed for {GOOD_ID}: rc=1" in out


def test_refuses_bad_id(monkeypatch, tmp_path, _run):
    jobs, spool, _, _ = _base(tmp_path)
    _marker(spool, "evil")
    _refused(monkeypatch, _run, jobs, spool, "evil", "bad-id")


def test_refuses_no_job_dir(monkeypatch, tmp_path, _run):
    jobs, spool, _, _ = _base(tmp_path)
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "no-job-dir")


def test_refuses_job_dir_symlink(monkeypatch, tmp_path, _run):
    jobs, spool, _, _ = _base(tmp_path)
    (jobs / GOOD_ID).symlink_to(tmp_path / "ws")
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "job-dir-symlink")


def test_refuses_job_dir_owner(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh))
    _marker(spool, GOOD_ID)
    # The job dir is owned by os.getuid(); ask for root (uid 0) instead.
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "job-dir-owner", owner="root")


def test_refuses_job_dir_mode(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh), mode=0o755)
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "job-dir-mode")


def test_refuses_no_job_json(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh))
    (jobs / GOOD_ID / "job.json").unlink()
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "no-job-json")


def test_refuses_bad_json(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh))
    (jobs / GOOD_ID / "job.json").write_text("not json")
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "bad-json")


def test_refuses_bad_mode(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh, mode="evil"))
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "bad-mode")


def test_refuses_bad_workspace(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    js = _job_dict(ws, dsh, workspace=str(tmp_path / "nope"))
    _write_job(jobs, GOOD_ID, js)
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "bad-workspace")


def test_refuses_bad_dsh_home(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    js = _job_dict(ws, dsh, dsh_home=str(tmp_path / "nope"))
    _write_job(jobs, GOOD_ID, js)
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "bad-dsh-home")


def test_refuses_bad_model(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh, model="m x"))
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "bad-model")


def test_refuses_bad_effort(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh, effort="extreme"))
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "bad-effort")


def test_refuses_bad_port_headless(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    # A headless job must carry port = null; an int is bad-port (the row that
    # kills a `port in 1024..65535` shortcut).
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh, port=43201))
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "bad-port")


def test_refuses_bad_port_web(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    js = _job_dict(ws, dsh, mode="web", brief=None, port=70000)
    _write_job(jobs, GOOD_ID, js, brief=False)
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "bad-port")


def test_refuses_no_brief(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    # headless with brief = "brief.txt" but the file itself is missing.
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh), brief=False)
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "no-brief")


def test_refuses_already_started(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh))
    (jobs / GOOD_ID / ".spooled").write_text(GOOD_ID)
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "already-started")


def test_refuses_finished(monkeypatch, tmp_path, _run):
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh))
    (jobs / GOOD_ID / "exit_code.txt").write_text("0\n")
    _marker(spool, GOOD_ID)
    _refused(monkeypatch, _run, jobs, spool, GOOD_ID, "finished")


def test_refuses_above_cap_writes_failed_result(monkeypatch, tmp_path):
    # IS1c: the spool enforces the running-unit cap. At (or above) the cap it
    # does not start the unit and does not silently drop the marker -- it writes
    # result.txt carrying FACTORY-RESULT status=failed and the cap/count, removes
    # the marker, and logs one line, so a waiting --wait returns with a result.
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh))
    _marker(spool, GOOD_ID)

    calls = []

    def _fake_run(argv, **kwargs):
        if argv[:2] == ["systemctl", "list-units"]:
            # the cap defaults to 5; report five running so the marker is refused
            return subprocess.CompletedProcess(argv, 0, stdout="u\n" * 5)
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(seat_spool.subprocess, "run", _fake_run)

    rc, _, err = _run_spool(monkeypatch, jobs, spool)

    assert rc == 0
    assert calls == []  # the refused job was never started
    assert not (spool / GOOD_ID).exists()
    result = jobs / GOOD_ID / "result.txt"
    assert result.is_file()
    body = result.read_text()
    assert "FACTORY-RESULT status=failed" in body
    assert "5 seat units running, cap 5" in body
    assert f"seat-spool: refused {GOOD_ID}" in err
    assert not (jobs / GOOD_ID / ".spooled").exists()


def test_spool_reads_the_declared_max_units_file(monkeypatch, tmp_path):
    # IS3: the running-unit cap is declared by the seatLane module (maxUnits =
    # waveJobs + 1, default 9) and written to /etc/seat-lane/max-units; the
    # spool reads that declared file, never a private literal. A file holding 9
    # is honored -- nine running units meet a cap of 9 (not the DEFAULT 5) -- so
    # a mutant that ignores the file and falls back to 5 would wrongly refuse.
    jobs, spool, ws, dsh = _base(tmp_path)
    _write_job(jobs, GOOD_ID, _job_dict(ws, dsh))
    _marker(spool, GOOD_ID)

    declared = tmp_path / "max-units"
    declared.write_text("9\n")
    monkeypatch.setattr(seat_spool, "MAX_UNITS_FILE", str(declared))

    calls = []

    def _fake_run(argv, **kwargs):
        if argv[:2] == ["systemctl", "list-units"]:
            # nine running meets (not exceeds) a cap of nine read from the file
            return subprocess.CompletedProcess(argv, 0, stdout="u\n" * 9)
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(seat_spool.subprocess, "run", _fake_run)

    rc, _, err = _run_spool(monkeypatch, jobs, spool)

    assert rc == 0
    assert calls == []  # the refused job was never started
    assert not (spool / GOOD_ID).exists()
    result = jobs / GOOD_ID / "result.txt"
    assert result.is_file()
    assert "9 seat units running, cap 9" in result.read_text()
    assert f"seat-spool: refused {GOOD_ID}" in err
    assert not (jobs / GOOD_ID / ".spooled").exists()
