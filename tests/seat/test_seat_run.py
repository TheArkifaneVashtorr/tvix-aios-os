"""Tests for pkgs/seat/seat-run.py (plan 2026-09-05-seat-behind-broker, SB1).

Drives the script in-process (imported by path, the same way
test_seat_submit.py loads seat-submit.py -- a hyphenated filename is not an
importable module). No real /var/lib/seat spool or dsh-openrouter is touched:
the JOBS_DIR constant is redirected at tmp_path, os.chdir and subprocess.run
are monkeypatched, and the subprocess is a fake CompletedProcess.

Asserts the two modes' command lines, the DSH_HOME/effort environment the unit
exports, and that stdout.txt/stderr.txt/exit_code.txt/result.txt (headless) and
url.txt + the printed URL (web) land in the job dir exactly as the caller
(seat-submit) and the operator expect.
"""

import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "seat" / "seat-run.py"
spec = importlib.util.spec_from_file_location("seat_run", SRC)
seat_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seat_run)

JOB_ID = "20260905-120000-abcdef"


@pytest.fixture
def jobs(tmp_path):
    d = tmp_path / "jobs"
    d.mkdir()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(seat_run, "JOBS_DIR", str(d))
    monkeypatch.setenv("SEAT_NAMESPACE_ADDRESS", "10.100.4.2")
    yield d
    monkeypatch.undo()


def _make_job(jobs, job, brief=None):
    job_dir = jobs / JOB_ID
    job_dir.mkdir()
    (job_dir / "job.json").write_text(json.dumps(job))
    if brief is not None:
        (job_dir / "brief.txt").write_text(brief)
    return job_dir


def _capture(monkeypatch):
    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    return out, err


def _run_fake(stdout_text, returncode=0, stderr_text="", seen=None):
    def _run(cmd, **kwargs):
        if seen is not None:
            seen["cmd"] = cmd
        return subprocess.CompletedProcess(
            cmd, returncode, stdout=stdout_text, stderr=stderr_text
        )

    return _run


def test_headless_runs_broker_and_writes_result_files(jobs, monkeypatch):
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "deepseek/deepseek-v4-pro-0813",
        "effort": "medium",
        "brief": "brief.txt",
        "port": None,
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="do the task\n")

    stdout_text = (
        "thinking out loud\n"
        "FACTORY-RESULT status=done\n"
        "FACTORY-CHECKS unit=pass\n"
        "FACTORY-COMMITS 2\n"
        "FACTORY-NOTES ok\n"
    )
    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess,
        "run",
        _run_fake(stdout_text, returncode=3, seen=seen),
    )
    cwd = {}
    monkeypatch.setattr(seat_run.os, "chdir", lambda p: cwd.__setitem__("wd", p))
    out, _ = _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    assert rc == 3
    # The headless command: broker + model + headless brief, with the brief's
    # content inlined (what seat-run read from brief.txt).
    assert seen["cmd"] == [
        "dsh-openrouter",
        "--broker",
        "--model",
        "deepseek/deepseek-v4-pro-0813",
        "--headless",
        "do the task\n",
    ]
    # DSH_HOME + effort exported, and the cwd is the job's workspace.
    assert os.environ["DSH_HOME"] == str(jobs / "dsh")
    assert os.environ["OPENROUTER_REASONING_EFFORT"] == "medium"
    assert cwd["wd"] == str(jobs / "ws")
    # Headless has no url.txt, and nothing is printed to the journal.
    assert "url.txt" not in {p.name for p in (jobs / JOB_ID).iterdir()}
    assert out.getvalue() == stdout_text
    # The result files: stdout teed through, exit code, and the FACTORY-RESULT
    # block (last usable line per label).
    assert (jobs / JOB_ID / "stdout.txt").read_text() == stdout_text
    assert (jobs / JOB_ID / "exit_code.txt").read_text() == "3\n"
    assert (jobs / JOB_ID / "result.txt").read_text() == (
        "FACTORY-RESULT status=done\n"
        "FACTORY-CHECKS unit=pass\n"
        "FACTORY-COMMITS 2\n"
        "FACTORY-NOTES ok\n"
    )


def test_no_factory_result_writes_status_failed(jobs, monkeypatch):
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt",
        "port": None,
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n")
    monkeypatch.setattr(seat_run.subprocess, "run", _run_fake("no result block here\n"))
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    assert rc == 0
    assert (jobs / JOB_ID / "result.txt").read_text() == "status=failed\n"


def test_web_binds_namespace_and_writes_url(jobs, monkeypatch):
    job = {
        "mode": "web",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": None,
        "port": 43210,
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job)

    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess,
        "run",
        _run_fake("web ui\n", seen=seen),
    )
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    out, _ = _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    assert rc == 0
    assert seen["cmd"] == [
        "dsh-openrouter",
        "--broker",
        "--bind-namespace",
        "10.100.4.2",
        "--",
        "--no-open",
        "--port",
        "43210",
    ]
    # The URL is printed to the journal first (then the harness's own stdout is
    # teed through), and filed to url.txt, naming the address and port the
    # operator opens.
    assert out.getvalue() == "http://10.100.4.2:43210\nweb ui\n"
    assert (jobs / JOB_ID / "url.txt").read_text() == "http://10.100.4.2:43210\n"


def test_missing_job_id_exits_2(jobs, monkeypatch):
    out, err = _capture(monkeypatch)
    rc = seat_run.run([])
    assert rc == 2
    assert "job id" in err.getvalue()
    assert out.getvalue() == ""
