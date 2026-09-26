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

import errno
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


# FA31 (BUG-seat-brief-argv-too-long): the kernel's per-argument cap,
# MAX_ARG_STRLEN = 131072 bytes with the terminating NUL counted, that
# execve enforces on every single argv element regardless of ARG_MAX's
# total headroom -- the cap OS5's 134383-byte brief died on (Errno 7,
# E2BIG). The fake Popen reproduces it for every launch: without it a
# faked launch would accept any length, and the over-cap case below could
# never be red on the base (a fake that accepts everything proves
# nothing). An element is over the cap exactly when its encoded bytes plus
# the NUL exceed 131072, the same arithmetic execve applies.
MAX_ARG_STRLEN = 131072


def _popen_fake(lines, returncode=0, seen=None, job_dir=None):
    """A Popen stand-in. `lines` is an iterable of stdout lines (a generator for
    tests that observe the mid-stream state between two yielded lines); `.wait()`
    returns `returncode` and records whether url.txt already existed by then.
    Every launch first reproduces execve's per-argument cap (MAX_ARG_STRLEN):
    an argv element at or past it raises OSError Errno 7 here, exactly where the
    real execve raises it, before any stdout exists."""

    class _FakePopen:
        def __init__(self):
            self.stdout = iter(lines)

        def wait(self):
            if seen is not None and job_dir is not None:
                seen["url_at_wait"] = (job_dir / "url.txt").exists()
            return returncode

    def _popen(cmd, **kwargs):
        for el in cmd:
            if len(el.encode("utf-8", "surrogateescape")) + 1 > MAX_ARG_STRLEN:
                raise OSError(errno.E2BIG, "Argument list too long")
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
    # FA31 (Interface 1): the headless command hands the job's own brief.txt
    # over by absolute path -- `--headless @<job dir>/brief.txt` -- and the
    # brief's text appears in NO argv element: the wrapper (FA30) reads the
    # file itself, so a brief of any size is a short pointer, never one
    # execve argument (the shape BUG-seat-brief-argv-too-long records).
    # Interface 5: the path is absolute, so FA30's @<absolute path> form
    # expands it -- a relative token would stay literal and run the model
    # on the pointer.
    assert seen["cmd"] == [
        "dsh-openrouter",
        "--broker",
        "--model",
        "deepseek/deepseek-v4-pro-0813",
        "--headless",
        "@" + str(jobs / JOB_ID / "brief.txt"),
    ]
    headless_token = seen["cmd"][-1]
    assert headless_token.startswith("@") and os.path.isabs(headless_token[1:])
    assert not any("do the task" in el for el in seen["cmd"])
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


def test_an_over_cap_brief_launches_by_path(jobs, monkeypatch):
    """FA31 (Interface 4, BUG-seat-brief-argv-too-long): a brief of 200000
    bytes -- well past the kernel's per-argument cap (MAX_ARG_STRLEN,
    131072), the size class that killed OS5 (134383 bytes) -- composes and
    launches without raising. Today the inlined brief IS the argv element
    and the real execve refuses it with `OSError: [Errno 7] Argument list
    too long`; the fake Popen reproduces that ceiling for every case (see
    MAX_ARG_STRLEN), so on the base this case dies with the same OSError
    before the harness starts rather than a fake accepting any length."""
    big = "x" * 200000
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
    _make_job(jobs, job, brief=big)
    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess,
        "Popen",
        _popen_fake(["FACTORY-RESULT status=done\n"], seen=seen),
    )
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    assert rc == 0
    # The only headless token is the @path (Interface 1), no argv element is
    # anywhere near the cap, and the run recorded its result: the launch
    # happened (Interface 4), it did not merely survive composition.
    assert seen["cmd"][-1] == "@" + str(jobs / JOB_ID / "brief.txt")
    assert max(len(el.encode("utf-8")) for el in seen["cmd"]) < MAX_ARG_STRLEN
    assert not any("x" * 40 in el for el in seen["cmd"])
    assert (jobs / JOB_ID / "result.txt").read_text() == "FACTORY-RESULT status=done\n"


def test_a_job_with_no_brief_is_unchanged(jobs, monkeypatch):
    """FA31 (Interface 2): a job with no brief keeps today's behaviour
    exactly. A headless job whose brief is null dies on os.path.join(None)
    before the harness starts, exactly as before FA31 -- the fix moves the
    token's composition, not this refusal, and must never turn the
    pre-launch traceback into a launch on a bogus `@` token (a relative or
    malformed pointer FA30 would read literally). The no-brief modes (web,
    drive) never carried a brief token and still compose today's command --
    that half is the existing web/drive cases' exact-cmd asserts, which
    stay byte-identical."""
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": None,
        "port": None,
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job)
    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess, "Popen", _popen_fake(["done\n"], seen=seen)
    )
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    with pytest.raises(TypeError):
        seat_run.run([JOB_ID])

    # The harness was never launched on a bogus pointer.
    assert "cmd" not in seen


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


def test_exports_seat_task_when_the_job_names_one(jobs, monkeypatch):
    """OC9: the unit exports SEAT_TASK=<run>/<key> from job.json's `task`
    beside SEAT_JOB_ID, so the wrapper can label every request
    x-factory-task behind the broker. A job without one must not inherit a
    stale SEAT_TASK from the enclosing environment: the variable is popped,
    never passed through."""
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt",
        "port": None,
        "task": "ocw3/OC9",
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n")
    monkeypatch.setattr(seat_run.subprocess, "Popen", _popen_fake(["done\n"]))
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    seat_run.run([JOB_ID])

    assert os.environ["SEAT_TASK"] == "ocw3/OC9"

    # A task-less job: a pre-set SEAT_TASK is removed, never inherited -- a
    # stale label would attribute this job's spend to another task.
    del job["task"]
    (jobs / JOB_ID / "job.json").write_text(json.dumps(job))
    monkeypatch.setenv("SEAT_TASK", "stale/from-the-enclosing-env")
    seat_run.run([JOB_ID])

    assert "SEAT_TASK" not in os.environ


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
        "--permission",
        "danger-full-access",
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


def test_drive_passes_danger_full_access_before_the_dashes(jobs, monkeypatch):
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
    _capture(monkeypatch)

    seat_run.run([JOB_ID])

    # 57a: drive runs at danger-full-access, and the preset must land BEFORE
    # the `--` (dsh's web-app flags would swallow anything after it).
    argv = seen["cmd"]
    idx = argv.index("--permission")
    assert idx < argv.index("--")
    assert argv[idx + 1] == "danger-full-access"


@pytest.mark.parametrize("mode", ["headless", "web"])
def test_headless_and_web_carry_no_permission(jobs, monkeypatch, mode):
    job = {
        "mode": mode,
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt" if mode == "headless" else None,
        "port": None if mode == "headless" else 43210,
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n" if mode == "headless" else None)
    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess, "Popen", _popen_fake(["done\n"], seen=seen)
    )
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    seat_run.run([JOB_ID])

    # The preset is drive-only: headless and web keep the wrapper's default.
    assert "--permission" not in seen["cmd"]


@pytest.mark.parametrize("mode", ["headless", "web", "drive"])
def test_exports_seat_mode(jobs, monkeypatch, mode):
    job = {
        "mode": mode,
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt" if mode == "headless" else None,
        "port": None if mode == "headless" else (43210 if mode == "web" else 43202),
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n" if mode == "headless" else None)
    monkeypatch.setattr(seat_run.subprocess, "Popen", _popen_fake(["done\n"]))
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    seat_run.run([JOB_ID])

    # SA6's discriminator: every job names its mode to the harness env.
    assert os.environ["SEAT_MODE"] == mode


def test_missing_job_id_exits_2(jobs, monkeypatch):
    out, err = _capture(monkeypatch)
    rc = seat_run.run([])
    assert rc == 2
    assert "job id" in err.getvalue()
    assert out.getvalue() == ""


def test_web_without_port_exits_2(jobs, monkeypatch):
    # SA3 Interface 6: a web job whose port is still null (seat-spool never
    # ran) is refused rather than inventing a port -- exit 2, and the harness
    # is never launched.
    job = {
        "mode": "web",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": None,
        "port": None,
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job)
    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess, "Popen", _popen_fake(["done\n"], seen=seen)
    )
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _, err = _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    assert rc == 2
    assert "no allocated port" in err.getvalue()
    assert "cmd" not in seen  # the harness was never launched


# --- PT3 (plan 2026-09-22-planning-patterns): the job's environment allow-list ---
#
# C-JOB-ENV: the `env` seat-submit records into job.json is exported before
# the harness starts, exactly the allow-listed names and no others. The rule
# every case obeys: run() writes the REAL process environment and no
# autouse fixture undoes it, so every case clears or sets the name first --
# except R3 and R7, whose pre-state is deliberately stale.


@pytest.mark.parametrize("mode", ["headless", "web", "drive"])
def test_exports_the_job_env_for_every_mode(jobs, monkeypatch, mode):
    # The allow-listed environment the submitting shell carried (job.json's
    # `env`) is exported in every mode: the block sits below the port
    # refusal and above chdir, so it is common to headless, web and drive.
    monkeypatch.delenv("OPENROUTER_CONTEXT_WINDOW", raising=False)
    job = {
        "mode": mode,
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt" if mode == "headless" else None,
        "port": None if mode == "headless" else 43210,
        "env": {"OPENROUTER_CONTEXT_WINDOW": "1048576"},
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n" if mode == "headless" else None)
    seen = {}
    inner = _popen_fake(["done\n"], seen=seen)

    def _recording_popen(cmd, **kwargs):
        # What the harness's own process environment holds at spawn time.
        seen["window"] = os.environ.get("OPENROUTER_CONTEXT_WINDOW")
        return inner(cmd, **kwargs)

    monkeypatch.setattr(seat_run.subprocess, "Popen", _recording_popen)
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    assert rc == 0
    # A19: exported into the unit's process environment, in every mode.
    assert os.environ["OPENROUTER_CONTEXT_WINDOW"] == "1048576"
    # A20: exported BEFORE the harness started, not after it.
    assert seen["window"] == "1048576"


def test_absent_name_is_popped_never_inherited(jobs, monkeypatch):
    # The wrapper's own default (262144) sitting in the enclosing
    # environment must not survive the job: an allow-listed name the job
    # does not carry is popped, never inherited from the template unit (the
    # SEAT_TASK rule).
    monkeypatch.setenv("OPENROUTER_CONTEXT_WINDOW", "262144")
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt",
        "port": None,
        "env": {},
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n")
    monkeypatch.setattr(seat_run.subprocess, "Popen", _popen_fake(["done\n"]))
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    assert rc == 0
    # A21: the stale 262144 does not survive the job.
    assert "OPENROUTER_CONTEXT_WINDOW" not in os.environ


@pytest.mark.parametrize("arm", ["absent", "null", "empty"])
def test_job_without_env_reads_as_empty(jobs, monkeypatch, arm):
    # A job.json an older seat-submit wrote (no `env` key at all -- arm (a),
    # the default branch of job.get), or one carrying null (arm (b)) or {}
    # (arm (c)), reads as {}: the harness runs and every allow-listed name
    # is popped. The stale pre-state (the wrapper's own default) is what
    # makes the pop an assertion the base runner fails.
    monkeypatch.setenv("OPENROUTER_CONTEXT_WINDOW", "262144")
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt",
        "port": None,
    }
    if arm == "null":
        job["env"] = None
    elif arm == "empty":
        job["env"] = {}
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n")
    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess, "Popen", _popen_fake(["done\n"], seen=seen)
    )
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    assert rc == 0
    # A22/A23: the harness ran, the result was written, and the name popped.
    assert "cmd" in seen
    assert (jobs / JOB_ID / "result.txt").exists()
    assert "OPENROUTER_CONTEXT_WINDOW" not in os.environ


def test_env_name_outside_the_allow_list_refuses_before_the_harness(jobs, monkeypatch):
    # A hand-edited job.json carrying an alien name is refused before the
    # harness starts -- exit 2, the SA3 port refusal's shape (no result.txt,
    # no stdout.txt, no exit_code.txt) -- and exports nothing, not even the
    # valid allow-listed name that rode along with the alien one.
    monkeypatch.delenv("OPENROUTER_CONTEXT_WINDOW", raising=False)
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt",
        "port": None,
        "env": {"OPENROUTER_MODEL": "zzz", "OPENROUTER_CONTEXT_WINDOW": "1048576"},
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n")
    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess, "Popen", _popen_fake(["done\n"], seen=seen)
    )
    chdir = []
    monkeypatch.setattr(seat_run.os, "chdir", lambda p: chdir.append(p))
    _, err = _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    # A24: exit 2 and exactly the one refusal line, naming the alien name.
    assert rc == 2
    assert err.getvalue() == (
        "seat-run: job 20260905-120000-abcdef env carries OPENROUTER_MODEL, "
        "not in the allow-list\n"
    )
    # A25: os.chdir was never called and the harness never started.
    assert chdir == []
    assert "cmd" not in seen
    # A26: the pre-harness refusal shape -- no result, stdout or exit file.
    jd = jobs / JOB_ID
    assert not (jd / "result.txt").exists()
    assert not (jd / "stdout.txt").exists()
    assert not (jd / "exit_code.txt").exists()
    # A27: a refused job exports nothing, not even the name that rode along.
    assert "OPENROUTER_CONTEXT_WINDOW" not in os.environ


def test_two_alien_names_name_the_lexically_first(jobs, monkeypatch):
    # The names are written into job.json in reverse order (json.load keeps
    # file order), so `sorted()` is the only thing that makes the refusal
    # name AA_FIRST -- the deterministic message a caller can match on.
    monkeypatch.delenv("OPENROUTER_CONTEXT_WINDOW", raising=False)
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt",
        "port": None,
        "env": {"ZZ_LAST": "1", "AA_FIRST": "1"},
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n")
    monkeypatch.setattr(seat_run.subprocess, "Popen", _popen_fake(["done\n"]))
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _, err = _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    # A28: the lexically first of the two, never the file's first.
    assert rc == 2
    assert err.getvalue() == (
        "seat-run: job 20260905-120000-abcdef env carries AA_FIRST, "
        "not in the allow-list\n"
    )


@pytest.mark.parametrize("value", [1048576, None, "", ["1048576"]])
def test_env_value_must_be_a_non_empty_string(jobs, monkeypatch, value):
    # A hand-edited job.json can carry a value that is not a non-empty
    # string: an int, null or list would raise TypeError inside the unit (a
    # traceback, no result.txt, the caller reading it as the generic
    # exit-4 "started unit produced no result"), and "" would export cleanly
    # and kill the wrapper at launch -- after the job has started. The
    # runner checks the TYPE only; the value's FORMAT is the submitter's
    # regex, never restated here.
    monkeypatch.delenv("OPENROUTER_CONTEXT_WINDOW", raising=False)
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt",
        "port": None,
        "env": {"OPENROUTER_CONTEXT_WINDOW": value},
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n")
    seen = {}
    monkeypatch.setattr(
        seat_run.subprocess, "Popen", _popen_fake(["done\n"], seen=seen)
    )
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _, err = _capture(monkeypatch)

    rc = seat_run.run([JOB_ID])

    # A29: refused before the harness with the one type-refusal line.
    assert rc == 2
    assert err.getvalue() == (
        "seat-run: job 20260905-120000-abcdef env value for "
        "OPENROUTER_CONTEXT_WINDOW is not a non-empty string\n"
    )
    assert "cmd" not in seen
    assert not (jobs / JOB_ID / "result.txt").exists()

    # A30: the boundary the other way -- a valid string is NOT refused by
    # this check (a fresh run with the good value runs the harness).
    job["env"] = {"OPENROUTER_CONTEXT_WINDOW": "1048576"}
    (jobs / JOB_ID / "job.json").write_text(json.dumps(job))
    rc = seat_run.run([JOB_ID])
    assert rc == 0
    assert os.environ["OPENROUTER_CONTEXT_WINDOW"] == "1048576"


def test_a_second_job_does_not_inherit_the_first_window(jobs, monkeypatch):
    # The concurrency proxy. Real isolation between two seats is systemd's
    # fresh process per unit (ExecStart per instance), which a build-only
    # task may not start; what this proves is the only half that lives in
    # this repo's code -- run() leaves no allow-listed name behind for the
    # next job. Gap: nothing here exercises two units at once.
    monkeypatch.delenv("OPENROUTER_CONTEXT_WINDOW", raising=False)
    job = {
        "mode": "headless",
        "workspace": str(jobs / "ws"),
        "dsh_home": str(jobs / "dsh"),
        "model": "m",
        "effort": "off",
        "brief": "brief.txt",
        "port": None,
        "env": {"OPENROUTER_CONTEXT_WINDOW": "1048576"},
    }
    (jobs / "ws").mkdir()
    _make_job(jobs, job, brief="x\n")
    monkeypatch.setattr(seat_run.subprocess, "Popen", _popen_fake(["done\n"]))
    monkeypatch.setattr(seat_run.os, "chdir", lambda _p: None)
    _capture(monkeypatch)

    rc_a = seat_run.run([JOB_ID])

    # A31, first clause: job A really exported the value (the base runner
    # exports nothing, so this is the half that is red before the change).
    assert rc_a == 0
    assert os.environ["OPENROUTER_CONTEXT_WINDOW"] == "1048576"

    # Job B: an older job.json with no `env` key at all.
    del job["env"]
    (jobs / JOB_ID / "job.json").write_text(json.dumps(job))
    rc_b = seat_run.run([JOB_ID])

    # A31, second clause: job B does not inherit job A's window.
    assert rc_b == 0
    assert "OPENROUTER_CONTEXT_WINDOW" not in os.environ
