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

# IS1: the running-unit cap tests exercise a real subprocess against a fake
# `systemctl` put on PATH, so they must undo the autouse `_no_systemctl` patch.
# Capture the real `subprocess.run` before any fixture repatches it.
_REAL_SUBPROCESS_RUN = subprocess.run


@pytest.fixture
def answers():
    """Mutable dict the `_no_systemctl` fixture's `_run` reads for the
    `systemctl show` (`show`) and `journalctl` (`journal`) stdout -- so a test
    can override the unit state seat-submit observes. `show_rc` (default 0) is
    the `CompletedProcess` return code for `show` calls; `show_raise` (when
    set) makes `show` raise an `OSError` instead."""
    return {
        "show": "ActiveState=active\nResult=success\n",
        "journal": "",
        "show_rc": 0,
    }


@pytest.fixture(autouse=True)
def _no_systemctl(monkeypatch, answers):
    """Replaces subprocess.run so `systemctl start` can never touch a real
    unit; records the argv it would have run. `systemctl show` (seat-submit's
    SB6b unit-state probe) and `journalctl` are answered from `answers`."""
    calls = []

    def _run(argv, **kwargs):
        # IS1: the running-unit count probe (`systemctl list-units`) is issued
        # on every submit now. Answer it with an empty list (zero units, so
        # the cap never trips here) and do not record it -- a read, not a
        # start/stop/show the tests below pin.
        if argv[:2] == ["systemctl", "list-units"]:
            return subprocess.CompletedProcess(argv, 0, stdout="")
        calls.append(argv)
        if argv[:2] == ["systemctl", "show"]:
            if answers.get("show_raise"):
                raise OSError("systemctl missing")
            return subprocess.CompletedProcess(
                argv, answers.get("show_rc", 0), stdout=answers["show"]
            )
        if argv and argv[0] == "journalctl":
            return subprocess.CompletedProcess(argv, 0, stdout=answers["journal"])
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
    # SB6b: seat-submit now additionally probes the unit state (`systemctl
    # show`) each poll; that probe is not part of the start/stop contract
    # this test pins, so filter it (and journalctl) out before the exact-
    # argv comparison.
    assert [
        c
        for c in _no_systemctl
        if c[:2] != ["systemctl", "show"] and c[0] != "journalctl"
    ] == [["systemctl", "start", f"seat@{printed_id}"]]


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
    # SB6b: filter out the `systemctl show` probe (and any journalctl) so the
    # exact-argv comparison still pins only the start/stop contract.
    assert [
        c
        for c in _no_systemctl
        if c[:2] != ["systemctl", "show"] and c[0] != "journalctl"
    ] == [
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


def test_failed_unit_ends_the_wait_at_once_exit_4(
    ws, dsh, tmp_path, monkeypatch, _no_systemctl, answers
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
    # The unit fails at once (ActiveState=failed, Result=exit-code); the result
    # file is never written. seat-submit must end its wait immediately with
    # exit 4 (exit 3 is reserved for the running-unit cap, IS1), dump the
    # journalctl tail to stderr, and NOT stop the unit.
    answers["show"] = "ActiveState=failed\nResult=exit-code\n"
    answers["journal"] = "line-1\nline-2\n"

    # A broken poll (one that keeps sleeping instead of ending) is a failing
    # test, never a hang: raise once the sleep is called enough times.
    sleeps = {"n": 0}

    def _sleep(_seconds):
        sleeps["n"] += 1
        if sleeps["n"] >= 5:
            raise RuntimeError("polled too long")

    monkeypatch.setattr(seat_submit.time, "sleep", _sleep)

    rc, out, err = _submit(argv, monkeypatch)

    printed_id = out.strip()
    assert ID_RE.match(printed_id)
    assert rc == 4
    assert "Result=exit-code" in err
    assert "line-1" in err
    assert [
        "journalctl",
        "-u",
        f"seat@{printed_id}",
        "-n",
        "10",
        "--no-pager",
    ] in _no_systemctl
    assert ["systemctl", "stop", f"seat@{printed_id}"] not in _no_systemctl


def test_inactive_success_without_result_keeps_polling(
    ws, dsh, tmp_path, monkeypatch, _no_systemctl, answers
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
    # The unit reached inactive with Result=success but result.txt has not
    # appeared yet: seat-submit must keep polling (the timeout owns this
    # case), not report "ended without a result".
    answers["show"] = "ActiveState=inactive\nResult=success\n"

    sleeps = {"n": 0}

    def _sleep(_seconds):
        sleeps["n"] += 1
        if sleeps["n"] == 2:
            job_id = _no_systemctl[0][2][len("seat@") :]
            jd = jobs / job_id
            (jd / "result.txt").write_text("done\n")
            (jd / "stdout.txt").write_text("unit-stdout-content\n")
            (jd / "exit_code.txt").write_text("7\n")

    monkeypatch.setattr(seat_submit.time, "sleep", _sleep)

    rc, _, err = _submit(argv, monkeypatch)

    assert rc == 7
    assert "ended without a result" not in err


def test_unit_state_unreadable_keeps_polling(
    ws, dsh, tmp_path, monkeypatch, _no_systemctl, answers
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
    # `systemctl show` fails (returncode 1) even though its stdout looks like a
    # failed unit: seat-submit must treat that as an unreadable state and keep
    # polling, never a false early exit -- an unreadable unit state never ends
    # the wait.
    answers["show"] = "ActiveState=failed\nResult=exit-code\n"
    answers["show_rc"] = 1

    sleeps = {"n": 0}

    def _sleep(_seconds):
        sleeps["n"] += 1
        if sleeps["n"] >= 5:
            raise RuntimeError("polled too long")
        if sleeps["n"] == 2:
            job_id = _no_systemctl[0][2][len("seat@") :]
            jd = jobs / job_id
            (jd / "result.txt").write_text("done\n")
            (jd / "stdout.txt").write_text("unit-stdout-content\n")
            (jd / "exit_code.txt").write_text("5\n")

    monkeypatch.setattr(seat_submit.time, "sleep", _sleep)

    rc, _, err = _submit(argv, monkeypatch)

    assert rc == 5
    assert "ended without a result" not in err


def test_unit_state_oserror_keeps_polling(
    ws, dsh, tmp_path, monkeypatch, _no_systemctl, answers
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
    # `systemctl` itself is missing (OSError): seat-submit must treat that as an
    # unreadable state and keep polling, never let the exception escape.
    answers["show_raise"] = True

    sleeps = {"n": 0}

    def _sleep(_seconds):
        sleeps["n"] += 1
        if sleeps["n"] >= 5:
            raise RuntimeError("polled too long")
        if sleeps["n"] == 2:
            job_id = _no_systemctl[0][2][len("seat@") :]
            jd = jobs / job_id
            (jd / "result.txt").write_text("done\n")
            (jd / "stdout.txt").write_text("unit-stdout-content\n")
            (jd / "exit_code.txt").write_text("5\n")

    monkeypatch.setattr(seat_submit.time, "sleep", _sleep)

    rc, _, err = _submit(argv, monkeypatch)

    assert rc == 5
    assert "ended without a result" not in err


def test_no_start_writes_the_spool_marker(
    ws, dsh, tmp_path, monkeypatch, _no_systemctl
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
        "m",
        "--effort",
        "off",
    ]

    rc, out, _ = _submit(argv, monkeypatch)

    assert rc == 0
    job_id = out.strip()
    # --no-start spools: an empty 0600 marker at <spool-dir>/<id> (the default
    # spool is the sibling of the jobs dir), and still no systemctl call.
    marker = tmp_path / "spool" / job_id
    assert marker.exists()
    assert marker.stat().st_size == 0
    assert marker.stat().st_mode & 0o777 == 0o600
    assert _no_systemctl == []


def test_started_path_writes_no_marker(ws, dsh, tmp_path, monkeypatch, _no_systemctl):
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
        job_id = _no_systemctl[0][2][len("seat@") :]
        jd = jobs / job_id
        (jd / "result.txt").write_text("done\n")
        (jd / "stdout.txt").write_text("unit-stdout-content\n")
        (jd / "exit_code.txt").write_text("0\n")

    monkeypatch.setattr(seat_submit.time, "sleep", _sleep)

    rc, out, _ = _submit(argv, monkeypatch)

    assert rc == 0
    printed_id = out.splitlines()[0]
    # The started path (no --no-start) writes NO marker: the spool is only
    # reached by --no-start. This is the discriminator for the "write the
    # marker on the started path too" mutant (the start/stop recorder alone
    # would still pass).
    assert not (tmp_path / "spool" / printed_id).exists()


def test_wait_streams_without_systemctl(ws, dsh, tmp_path, monkeypatch, _no_systemctl):
    jobs = tmp_path / "jobs"
    argv = [
        "--jobs-dir",
        str(jobs),
        "--no-start",
        "--wait",
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
        # Stand in for the spool unit's seat-run: wait for the (single) job dir
        # and write its results, exactly as the started path's test does.
        (job_dir,) = jobs.iterdir()
        (job_dir / "result.txt").write_text("done\n")
        (job_dir / "stdout.txt").write_text("unit-stdout-content\n")
        (job_dir / "exit_code.txt").write_text("0\n")

    monkeypatch.setattr(seat_submit.time, "sleep", _sleep)

    rc, out, _ = _submit(argv, monkeypatch)

    assert rc == 0
    assert out.endswith("unit-stdout-content\n")
    # --no-start --wait streams and exits without ever calling systemctl.
    assert _no_systemctl == []


def test_wait_timeout_names_the_unit_and_never_stops_it(
    ws, dsh, tmp_path, monkeypatch, _no_systemctl
):
    jobs = tmp_path / "jobs"
    argv = [
        "--jobs-dir",
        str(jobs),
        "--no-start",
        "--wait",
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
    clock = {"t": 0.0}
    monkeypatch.setattr(
        seat_submit.time,
        "time",
        lambda: clock.__setitem__("t", clock["t"] + 1000.0) or clock["t"],
    )
    monkeypatch.setattr(seat_submit.time, "sleep", lambda _s: None)

    rc, out, err = _submit(argv, monkeypatch)

    assert rc == 124
    printed_id = out.strip()
    assert "timed out" in err
    # The message names the still-running unit (so the operator can stop it),
    # and --no-start never stops it: the recorder stays empty.
    assert f"seat@{printed_id}" in err
    assert _no_systemctl == []


def _drive_home(tmp_path):
    """A dsh-home carrying the full driver's skill set (SD7's three required
    entries), separated out so each drive test can name the missing file."""
    d = tmp_path / "drive-home"
    (d / "skills" / "driving").mkdir(parents=True)
    (d / "skills" / "planning").mkdir(parents=True)
    (d / "skills" / "driving" / "SKILL.md").write_text("driving\n")
    (d / "skills" / "planning" / "SKILL.md").write_text("planning\n")
    (d / "AGENTS.md").write_text("agents\n")
    return d


def test_drive_requires_port(ws, tmp_path, monkeypatch):
    jobs = tmp_path / "jobs"
    home = _drive_home(tmp_path)

    # drive without --port is a usage error.
    rc, _, err = _submit(
        [
            "--jobs-dir",
            str(jobs),
            "--no-start",
            "drive",
            "--workspace",
            str(ws),
            "--dsh-home",
            str(home),
            "--model",
            "m",
            "--effort",
            "off",
        ],
        monkeypatch,
    )
    assert rc == 2
    assert "drive needs --port" in err


@pytest.mark.parametrize(
    "missing",
    ["skills/driving/SKILL.md", "skills/planning/SKILL.md", "AGENTS.md"],
)
def test_drive_lacks_one_skill_is_refused(ws, tmp_path, monkeypatch, missing):
    jobs = tmp_path / "jobs"
    home = _drive_home(tmp_path)
    (home / missing).unlink()

    # A home lacking exactly one of the driver's three required entries names
    # that missing one and is refused before any job directory is created.
    rc, _, err = _submit(
        [
            "--jobs-dir",
            str(jobs),
            "--no-start",
            "drive",
            "--workspace",
            str(ws),
            "--dsh-home",
            str(home),
            "--model",
            "m",
            "--effort",
            "off",
            "--port",
            "43202",
        ],
        monkeypatch,
    )
    assert rc == 2
    assert f"lacks {missing}" in err


def test_drive_writes_job_with_full_skill_set(ws, tmp_path, monkeypatch):
    jobs = tmp_path / "jobs"
    home = _drive_home(tmp_path)

    # With the three files, the job is written with mode drive and no brief.
    rc, printed, _ = _submit(
        [
            "--jobs-dir",
            str(jobs),
            "--no-start",
            "drive",
            "--workspace",
            str(ws),
            "--dsh-home",
            str(home),
            "--model",
            "m",
            "--effort",
            "off",
            "--port",
            "43202",
        ],
        monkeypatch,
    )
    assert rc == 0
    job_dir = _job_dir(jobs, printed)
    job = json.loads((job_dir / "job.json").read_text())
    assert job["mode"] == "drive"
    assert job["brief"] is None
    assert job["port"] == 43202
    assert not (job_dir / "brief.txt").exists()


def test_drive_refuses_brief(ws, tmp_path, monkeypatch):
    jobs = tmp_path / "jobs"
    home = _drive_home(tmp_path)
    brief = tmp_path / "brief.txt"
    brief.write_text("x\n")
    rc, _, err = _submit(
        [
            "--jobs-dir",
            str(jobs),
            "--no-start",
            "drive",
            "--workspace",
            str(ws),
            "--dsh-home",
            str(home),
            "--model",
            "m",
            "--effort",
            "off",
            "--port",
            "43202",
            "--brief",
            str(brief),
        ],
        monkeypatch,
    )
    assert rc == 2
    assert "drive refuses --brief" in err


def test_wait_requires_no_start_and_headless(ws, dsh, tmp_path, monkeypatch):
    base = [
        "--jobs-dir",
        str(tmp_path / "jobs"),
        "--workspace",
        str(ws),
        "--dsh-home",
        str(dsh),
        "--model",
        "m",
        "--effort",
        "off",
    ]

    # --wait alone (headless but no --no-start) is a usage error.
    rc, _, _ = _submit(argv=base + ["--wait", "headless"], monkeypatch=monkeypatch)
    assert rc == 2
    # --wait with a web job (even with --no-start) is a usage error.
    rc, _, _ = _submit(
        argv=base + ["--no-start", "--wait", "web", "--port", "43210"],
        monkeypatch=monkeypatch,
    )
    assert rc == 2


# --- IS1: the running-unit cap (services.seat-lane.maxUnits) ---


def _install_fake_systemctl(tmp_path, body):
    """Writes an executable `systemctl` into tmp_path/bin and returns that
    directory for prepending to PATH, so the IS1 cap tests run a real
    subprocess against it (a `list-units` emitted line is one running unit)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "systemctl"
    script.write_text("#!/bin/sh\n" + body + "\n")
    script.chmod(0o755)
    return bin_dir


def _cap_args(tmp_path):
    """The argv common to the IS1 cap tests: a headless started-path submit
    (no --no-start, so the cap is enforced) that would start were the cap not
    tripped."""
    return [
        "--jobs-dir",
        str(tmp_path / "jobs"),
        "headless",
        "--workspace",
        str(tmp_path / "ws"),
        "--dsh-home",
        str(tmp_path / "dsh"),
        "--model",
        "m",
        "--effort",
        "off",
    ]


def _cap_env(monkeypatch, tmp_path, script_body, max_units=None):
    """Prepares a real-subprocess environment for one cap test: creates the
    workspace/dsh dirs, installs the fake `systemctl`, undoes the autouse
    `_no_systemctl` patch, and (optionally) overrides SEAT_MAX_UNITS."""
    (tmp_path / "ws").mkdir(exist_ok=True)
    (tmp_path / "dsh").mkdir(exist_ok=True)
    bin_dir = _install_fake_systemctl(tmp_path, script_body)
    monkeypatch.setattr(seat_submit.subprocess, "run", _REAL_SUBPROCESS_RUN)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    if max_units is not None:
        monkeypatch.setenv("SEAT_MAX_UNITS", max_units)


def test_cap_refuses_at_max_counting_activating(tmp_path, monkeypatch):
    # The fake lists one unit only while `--state` still mentions "activating"
    # -- a mutant that counts only `active` sees zero units and would wrongly
    # accept at the cap (the `>=` boundary is also exercised here: n == max).
    _cap_env(
        monkeypatch,
        tmp_path,
        'case "$*" in *activating*) echo "seat@x.service loaded activating start" ;; esac\n'
        "exit 0",
        max_units="1",
    )
    rc, _, err = _submit(_cap_args(tmp_path), monkeypatch)
    assert rc == 3
    assert "1 seat units running, cap 1" in err


def test_cap_accepts_below_max(ws, dsh, tmp_path, monkeypatch, _no_systemctl):
    # n = max - 1 (zero units, cap 1): the started path proceeds past the cap
    # check to the `systemctl start` call -- the discriminating row, showing a
    # below-cap count is not refused.
    monkeypatch.setenv("SEAT_MAX_UNITS", "1")
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
        job_id = _no_systemctl[0][2][len("seat@") :]
        jd = jobs / job_id
        (jd / "result.txt").write_text("done\n")
        (jd / "stdout.txt").write_text("unit-stdout-content\n")
        (jd / "exit_code.txt").write_text("0\n")

    monkeypatch.setattr(seat_submit.time, "sleep", _sleep)

    rc, out, _ = _submit(argv, monkeypatch)

    assert rc == 0
    printed_id = out.splitlines()[0]
    assert ID_RE.match(printed_id)
    assert [
        c
        for c in _no_systemctl
        if c[:2] != ["systemctl", "show"] and c[0] != "journalctl"
    ] == [["systemctl", "start", f"seat@{printed_id}"]]


def test_cap_zero_refuses_even_with_no_units(tmp_path, monkeypatch):
    # SEAT_MAX_UNITS=0 makes even an empty count reach the cap: refuse always.
    _cap_env(monkeypatch, tmp_path, "exit 0", max_units="0")
    rc, _, err = _submit(_cap_args(tmp_path), monkeypatch)
    assert rc == 3
    assert "0 seat units running, cap 0" in err


def test_cap_fails_closed_when_systemctl_exits_nonzero(tmp_path, monkeypatch):
    # A non-zero `systemctl list-units` must refuse (fail closed), never be
    # swallowed as "zero units" -- a mutant that swallows it would accept and
    # this test would get exit 3 (fail closed) instead of 0.
    _cap_env(monkeypatch, tmp_path, "exit 1")
    rc, _, err = _submit(_cap_args(tmp_path), monkeypatch)
    assert rc == 3
    assert "cannot count seat units" in err


def test_cap_fails_closed_when_systemctl_absent(tmp_path, monkeypatch):
    (tmp_path / "ws").mkdir(exist_ok=True)
    (tmp_path / "dsh").mkdir(exist_ok=True)
    empty = tmp_path / "no-systemctl"
    empty.mkdir()
    monkeypatch.setattr(seat_submit.subprocess, "run", _REAL_SUBPROCESS_RUN)
    monkeypatch.setenv("PATH", str(empty))
    rc, _, err = _submit(_cap_args(tmp_path), monkeypatch)
    assert rc == 3
    assert "cannot count seat units" in err


def test_no_start_writes_marker_with_systemctl_absent_from_path(
    ws, dsh, tmp_path, monkeypatch
):
    # IS1c Interface 1: the --no-start path never counts units and never
    # refuses -- with systemctl gone from PATH entirely it still writes its
    # marker and returns 0 (inside a seat@ unit systemctl is denied by design,
    # so a count there would refuse every seat-dispatched task).
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
        "m",
        "--effort",
        "off",
    ]
    empty = tmp_path / "no-systemctl"
    empty.mkdir()
    monkeypatch.setattr(seat_submit.subprocess, "run", _REAL_SUBPROCESS_RUN)
    monkeypatch.setenv("PATH", str(empty))

    rc, out, _ = _submit(argv, monkeypatch)

    assert rc == 0
    job_id = out.strip()
    assert ID_RE.match(job_id), f"bad id format: {job_id!r}"
    marker = tmp_path / "spool" / job_id
    assert marker.exists()
    assert marker.stat().st_size == 0


def _complete_started_job(monkeypatch, _no_systemctl, jobs):
    """Lets a started-path submit that reaches the poll loop finish on its first
    sleep (writing the unit's results). The malformed-cap tests use this so a
    mutant that wrongly falls back to the default cap fails with `assert 3 == 0`
    instead of hanging in the poll loop."""
    monkeypatch.setattr(seat_submit, "POLL_INTERVAL", 0)

    def _sleep(_seconds):
        job_id = _no_systemctl[0][2][len("seat@") :]
        jd = jobs / job_id
        (jd / "result.txt").write_text("done\n")
        (jd / "stdout.txt").write_text("unit-stdout-content\n")
        (jd / "exit_code.txt").write_text("0\n")

    monkeypatch.setattr(seat_submit.time, "sleep", _sleep)


def _start_args(ws, dsh, tmp_path):
    """A headless started-path argv (the cap is enforced on the started path)."""
    return [
        "--jobs-dir",
        str(tmp_path / "jobs"),
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


def test_cap_non_numeric_env_exits_3(ws, dsh, tmp_path, monkeypatch, _no_systemctl):
    # IS1c Interface 4: a non-numeric SEAT_MAX_UNITS refuses with exit 3 naming
    # the value -- never an uncaught ValueError, never a silent fallback to 5.
    monkeypatch.setenv("SEAT_MAX_UNITS", "x")
    _complete_started_job(monkeypatch, _no_systemctl, tmp_path / "jobs")

    rc, _, err = _submit(_start_args(ws, dsh, tmp_path), monkeypatch)

    assert rc == 3
    assert "SEAT_MAX_UNITS" in err
    assert "x" in err


def test_cap_empty_env_exits_3(ws, dsh, tmp_path, monkeypatch, _no_systemctl):
    # IS1c Interface 4: a set-but-empty SEAT_MAX_UNITS refuses with exit 3
    # (absent-but-required), never silently falling through to the file/5.
    monkeypatch.setenv("SEAT_MAX_UNITS", "")
    _complete_started_job(monkeypatch, _no_systemctl, tmp_path / "jobs")

    rc, _, err = _submit(_start_args(ws, dsh, tmp_path), monkeypatch)

    assert rc == 3
    assert "SEAT_MAX_UNITS" in err


def test_cap_malformed_file_exits_3(ws, dsh, tmp_path, monkeypatch, _no_systemctl):
    # IS1c Interface 4: a malformed /etc/seat-lane/max-units refuses with exit 3
    # naming the value, never silently reverting to the default 5.
    monkeypatch.delenv("SEAT_MAX_UNITS", raising=False)
    bad = tmp_path / "max-units"
    bad.write_text("garbage\n")
    monkeypatch.setattr(seat_submit, "MAX_UNITS_FILE", str(bad))
    _complete_started_job(monkeypatch, _no_systemctl, tmp_path / "jobs")

    rc, _, err = _submit(_start_args(ws, dsh, tmp_path), monkeypatch)

    assert rc == 3
    assert "garbage" in err
