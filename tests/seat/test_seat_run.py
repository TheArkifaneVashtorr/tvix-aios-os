"""Tests for pkgs/seat/seat-run.py (plan 2026-09-05-seat-behind-broker, SB1).

Drives the script in-process (imported by path, the same way
test_seat_submit.py loads seat-submit.py -- a hyphenated filename is not an
importable module). No real /var/lib/seat spool or dsh-openrouter is touched:
the JOBS_DIR constant is redirected at tmp_path, os.chdir and subprocess.Popen
are monkeypatched, and the subprocess is a fake Popen whose stdout is an
iterable of lines and whose wait() returns a fixed code (recording whether
url.txt already existed when it ran -- so a test can tell streamed from
buffered publication).

Asserts the modes' command lines, the DSH_HOME/effort environment the unit
exports, and that stdout.txt/stderr.txt/exit_code.txt/result.txt (headless) and
url.txt + the printed URL (web/drive) land in the job dir exactly as the caller
(seat-submit) and the operator expect: url.txt carries dsh's token URL on the
namespace address, written while the harness is still running, and stdout.txt
is streamed (flushed per line) rather than buffered to exit.
"""

import importlib.util
import io
import json
import os
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


def _popen_fake(lines, returncode=0, seen=None, job_dir=None):
    """A Popen stand-in. `lines` is an iterable of stdout lines (a generator for
    tests that observe the mid-stream state between two yielded lines); `.wait()`
    returns `returncode` and records whether url.txt already existed by then."""

    class _FakePopen:
        def __init__(self):
            self.stdout = iter(lines)

        def wait(self):
            if seen is not None and job_dir is not None:
                seen["url_at_wait"] = (job_dir / "url.txt").exists()
            return returncode

    def _popen(cmd, **kwargs):
        if seen is not None:
            seen["cmd"] = cmd
        return _FakePopen()

    return _popen


# dsh's printed URL line in a seat is always loopback (findings doc); the token
# is 43 base64url chars drawn fresh per process. The fake uses a short stand-in
# that still exercises the rewrite.
DSH_URL_LINE = "dsh web: http://127.0.0.1:43210/?token=abc123"


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

    # The first FACTORY-RESULT line is a decoy: _extract_result keeps the LAST
    # usable match per label (matches[-1]), so result.txt must pick the second.
    stdout_text = (
        "thinking out loud\n"
        "FACTORY-RESULT status=partial\n"
        "FACTORY-RESULT status=done\n"
        "FACTORY-CHECKS unit=pass\n"
        "FACTORY-COMMITS 2\n"
        "FACTORY-NOTES ok\n"
    )
    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess,
        "Popen",
        _popen_fake(stdout_text.splitlines(keepends=True), returncode=3, seen=seen),
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


def test_exports_seat_job_id(jobs, monkeypatch):
    """SD5: the unit exports SEAT_JOB_ID=<job id> before the harness starts —
    the environment fact factory-task (SD6) and factory-wave (SD3) read."""
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
    monkeypatch.setattr(seat_run.subprocess, "Popen", _popen_fake(["done\n"]))
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    seat_run.run([JOB_ID])

    assert os.environ["SEAT_JOB_ID"] == JOB_ID


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
    monkeypatch.setattr(
        seat_run.subprocess, "Popen", _popen_fake(["no result block here\n"])
    )
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
    job_dir = jobs / JOB_ID

    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess,
        "Popen",
        _popen_fake(
            [DSH_URL_LINE + "\n", "web ui\n"],
            seen=seen,
            job_dir=job_dir,
        ),
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
    # W1: url.txt is dsh's token URL with 127.0.0.1 rewritten to the namespace
    # address -- never the loopback line, never the old constructed string.
    assert (
        job_dir / "url.txt"
    ).read_text() == "http://10.100.4.2:43210/?token=abc123\n"
    # W2: url.txt already existed while the child was still running -- the
    # fake's wait() saw it (a buffered-to-EOF implementation would write it
    # only after wait()).
    assert seen["url_at_wait"] is True
    # The journal prints the rewritten (reachable) URL exactly once, then the
    # harness's own stdout teed through.
    assert out.getvalue() == "http://10.100.4.2:43210/?token=abc123\nweb ui\n"
    # stdout.txt holds the VERBATIM harness stdout (dsh's loopback line), both
    # lines.
    assert (job_dir / "stdout.txt").read_text() == (
        "dsh web: http://127.0.0.1:43210/?token=abc123\nweb ui\n"
    )


def test_web_streams_stdout_line_by_line(jobs, monkeypatch):
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
    job_dir = jobs / JOB_ID

    state = {}

    def lines():
        yield DSH_URL_LINE + "\n"
        # seat-run has consumed the first line by now: stdout.txt must already
        # hold it (flush-per-line), and url.txt must already be written -- so
        # the yield boundary observes the stream, not a buffered tail.
        state["stdout_after_first"] = (job_dir / "stdout.txt").read_text()
        state["url_after_first"] = (job_dir / "url.txt").exists()
        yield "web ui\n"

    monkeypatch.setattr(seat_run.subprocess, "Popen", _popen_fake(lines()))
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    seat_run.run([JOB_ID])

    # W3: the first line reached stdout.txt before the second line was even
    # yielded, and url.txt was written live too.
    assert state["stdout_after_first"] == DSH_URL_LINE + "\n"
    assert state["url_after_first"] is True
    assert (job_dir / "stdout.txt").read_text() == (
        "dsh web: http://127.0.0.1:43210/?token=abc123\nweb ui\n"
    )


def test_drive_passes_the_model_before_the_dashes(jobs, monkeypatch):
    job = {
        "mode": "drive",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": None,
        "port": 43202,
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job)
    job_dir = jobs / JOB_ID

    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess,
        "Popen",
        _popen_fake(
            ["dsh web: http://127.0.0.1:43202/?token=abc123\n", "web ui\n"],
            seen=seen,
            job_dir=job_dir,
        ),
    )
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    out, _ = _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    assert rc == 0
    # SD7: drive is the web command PLUS --model <model> BEFORE the `--`
    # (the wrapper's explicit model wins over the home's saved selection).
    assert seen["cmd"] == [
        "dsh-openrouter",
        "--broker",
        "--bind-namespace",
        "10.100.4.2",
        "--model",
        "m",
        "--",
        "--no-open",
        "--port",
        "43202",
    ]
    # drive shares the web code path: the token URL on the namespace address.
    assert (
        job_dir / "url.txt"
    ).read_text() == "http://10.100.4.2:43202/?token=abc123\n"
    assert seen["url_at_wait"] is True
    assert out.getvalue() == "http://10.100.4.2:43202/?token=abc123\nweb ui\n"


def test_missing_job_id_exits_2(jobs, monkeypatch):
    out, err = _capture(monkeypatch)
    rc = seat_run.run([])
    assert rc == 2
    assert "job id" in err.getvalue()
    assert out.getvalue() == ""
