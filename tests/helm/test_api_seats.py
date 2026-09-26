"""Helm API seats route (HM4): the session list on /v1/seats.

HM4 gives Helm the session-list read: `GET /v1/seats` joins the job directory
spool (SA9's contract read from `cfg["seats"]["spool_dir"]`, U5) with the live
`systemctl list-units 'seat@*'` state, degraded to "unknown" when systemctl
fails. Helm allocates nothing: `port` comes only from `job.json`, and the
route writes nothing, so the only method is GET (POST → 405 by HM2's
dispatcher).

The mutant column in the plan (M1..M6 plus the running-seat negative control)
is reproduced here as test names; each test is written to fail on exactly the
mutation its name targets, not to rubber-stamp the current code.
"""

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC_DIR = HERE.parents[2] / "pkgs" / "helm"
# api.py does `from serve import ...` and api_seats.py is an api_*.py route
# module discovered at api.py import; both resolve from their own directory,
# so put it on sys.path before loading them by path, exactly as test_api.py
# and test_serve.py do.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Load api_seats.py by path first (the FileNotFoundError red when it does not
# yet exist), registering it so api.py's discover() reuses this exact object.
_seats_spec = importlib.util.spec_from_file_location(
    "api_seats", SRC_DIR / "api_seats.py"
)
api_seats = importlib.util.module_from_spec(_seats_spec)
sys.modules["api_seats"] = api_seats
_seats_spec.loader.exec_module(api_seats)

# api.py's discover() imports api_seats (above) and api_state; reach the
# dispatcher and the Request dataclass the same way the code under test does.
_spec = importlib.util.spec_from_file_location("api", SRC_DIR / "api.py")
api = importlib.util.module_from_spec(_spec)
sys.modules["api"] = api
_spec.loader.exec_module(api)

serve = sys.modules["serve"]

# The looping-backs the route must always publish: a browser on the host
# reaches the seat through its published port, never its netns address (M5
# builds the url from the job's `address`, which this pins out).
LOOPBACK = "127.0.0.1"

# Canned `systemctl list-units 'seat@*' --all --output=json --no-pager` output.
# The `active` field is systemd's ActiveState; the route maps it to its own
# active|inactive|failed|unknown enum.
SYSTEMD_JSON = json.dumps(
    [
        {
            "unit": "seat@a.service",
            "load": "loaded",
            "active": "active",
            "sub": "running",
        },
        {
            "unit": "seat@b.service",
            "load": "loaded",
            "active": "failed",
            "sub": "failed",
        },
        {
            "unit": "seat@c.service",
            "load": "loaded",
            "active": "inactive",
            "sub": "dead",
        },
    ]
)


def fake_run(argv, **kw):
    return subprocess.CompletedProcess(argv, 0, SYSTEMD_JSON, "")


def failing_run(argv, **kw):
    return subprocess.CompletedProcess(argv, 1, "", "no such units")


def build_spool(root):
    """Three job directories: c (spooled, port null), a (running, port 43211,
    with an `address` the route must ignore), b (finished, exit_code.txt = 7).

    Directories are created in unsorted order so test_seats_sorted_by_id (M4)
    discriminates a dropped sort."""
    spool = root / "spool"
    jobs = {
        "c": {"mode": "web", "port": None},
        "a": {"mode": "web", "port": 43211, "address": "10.100.4.2"},
        "b": {"mode": "headless", "port": 43212, "address": "10.100.4.3"},
    }
    for job_id in ("c", "a", "b"):
        d = spool / job_id
        d.mkdir(parents=True)
        (d / "job.json").write_text(json.dumps(jobs[job_id]))
    (spool / "b" / "exit_code.txt").write_text("7\n")
    return spool


def make_cfg(spool, run):
    return {
        "seats": {"spool_dir": str(spool)},
        "_run": run,
    }


def call_seats(cfg):
    """Run the handler directly; (status, body)."""
    return api_seats.list_seats(cfg, api.Request(method="GET", path="/v1/seats"))


def rows_by_id(body):
    return {row["id"]: row for row in body["seats"]}


# ---------------------------------------------------------------------------
# M1: a null port must stay null (the route allocates nothing)
# ---------------------------------------------------------------------------


def test_spooled_seat_has_null_port(tmp_path):
    cfg = make_cfg(build_spool(tmp_path), fake_run)
    status, body = call_seats(cfg)
    assert status == 200
    assert rows_by_id(body)["c"]["port"] is None
    assert rows_by_id(body)["c"]["url"] is None


# ---------------------------------------------------------------------------
# M2: a missing spool directory is an empty list, never a 500
# ---------------------------------------------------------------------------


def test_missing_spool_is_empty_list(tmp_path):
    cfg = make_cfg(tmp_path / "does-not-exist", fake_run)
    status, body = call_seats(cfg)
    assert status == 200
    assert body["seats"] == []


# ---------------------------------------------------------------------------
# M3: a failing systemctl degrades every state to "unknown", route stays 200
# ---------------------------------------------------------------------------


def test_systemctl_failure_degrades_to_unknown(tmp_path):
    cfg = make_cfg(build_spool(tmp_path), failing_run)
    status, body = call_seats(cfg)
    assert status == 200
    rows = rows_by_id(body)
    assert {row["state"] for row in rows.values()} == {"unknown"}
    assert rows["a"]["port"] == 43211  # the job read still succeeds


# ---------------------------------------------------------------------------
# M4: seats are sorted by id (fixture created c, a, b)
# ---------------------------------------------------------------------------


def test_seats_sorted_by_id(tmp_path, monkeypatch):
    # read_jobs returns the three jobs in a deliberately unsorted order
    # (ids c, a, b); the route must sort by id (interface 1).
    monkeypatch.setattr(
        api_seats,
        "read_jobs",
        lambda spool_dir: {
            "c": {"port": None, "exit_code": None},
            "a": {"port": 43211, "exit_code": None},
            "b": {"port": 43212, "exit_code": 7},
        },
    )
    status, body = call_seats(make_cfg(tmp_path, fake_run))
    assert status == 200
    assert [row["id"] for row in body["seats"]] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# M5: url is loopback, never the netns address carried in job.json
# ---------------------------------------------------------------------------


def test_url_is_loopback(tmp_path):
    status, body = call_seats(make_cfg(build_spool(tmp_path), fake_run))
    assert status == 200
    rows = rows_by_id(body)
    # job "a" carries "address": "10.100.4.2"; the route must ignore it.
    assert rows["a"]["url"] == f"http://{LOOPBACK}:43211/"
    assert rows["b"]["url"] == f"http://{LOOPBACK}:43212/"
    assert rows["c"]["url"] is None


# ---------------------------------------------------------------------------
# M6: the route is registered in api.route_table()
# ---------------------------------------------------------------------------


def test_seats_route_registered():
    assert ("GET", "/v1/seats") in {(m, p) for m, p, _ in api.route_table()}


# ---------------------------------------------------------------------------
# negative control: the running seat round-trips (reads the runner's output)
# ---------------------------------------------------------------------------


def test_running_seat_round_trips(tmp_path):
    status, body = call_seats(make_cfg(build_spool(tmp_path), fake_run))
    assert status == 200
    assert rows_by_id(body)["a"] == {
        "id": "a",
        "unit": "seat@a.service",
        "state": "active",
        "port": 43211,
        "url": f"http://{LOOPBACK}:43211/",
        "exit_code": None,
    }


# ---------------------------------------------------------------------------
# exit_code: the finished job exposes its exit_code.txt
# ---------------------------------------------------------------------------


def test_finished_seat_has_exit_code(tmp_path):
    status, body = call_seats(make_cfg(build_spool(tmp_path), fake_run))
    assert status == 200
    rows = rows_by_id(body)
    assert rows["b"]["exit_code"] == 7
    assert rows["b"]["state"] == "failed"
    assert rows["a"]["exit_code"] is None
    assert rows["c"]["exit_code"] is None


# ---------------------------------------------------------------------------
# HM4b/HM4c: a failed seam degrades to "unknown" and names the command, never a
# 500 — the seam (api.run) turns a raise into a non-zero returncode, which the
# route reads as returncode/stdout/stderr only
# ---------------------------------------------------------------------------


def raising_run(argv, **kw):
    # The seam turns an absent program into returncode 127 with the message in
    # stderr; the route reads that returncode, never the exception itself.
    return subprocess.CompletedProcess(
        argv, 127, "", "FileNotFoundError: [Errno 2] No such file: 'systemctl'"
    )


def timeout_run(argv, **kw):
    # The seam turns a timeout into returncode 124 with the message in stderr.
    return subprocess.CompletedProcess(argv, 124, "", "timed out after 10.0s")


def test_systemctl_raises_is_unknown(tmp_path):
    # M1: with the returncode check dropped, the 127 result's empty stdout is
    # parsed as JSON and still degrades, but without naming the command. Here
    # every state is "unknown" and the 200 carries an error naming the command.
    cfg = make_cfg(build_spool(tmp_path), raising_run)
    status, body = call_seats(cfg)
    assert status == 200
    rows = rows_by_id(body)
    assert {row["state"] for row in rows.values()} == {"unknown"}
    assert "systemctl list-units" in body["error"]


def test_systemctl_timeout_is_unknown(tmp_path):
    cfg = make_cfg(build_spool(tmp_path), timeout_run)
    status, body = call_seats(cfg)
    assert status == 200
    rows = rows_by_id(body)
    assert {row["state"] for row in rows.values()} == {"unknown"}
    assert "systemctl list-units" in body["error"]


# ---------------------------------------------------------------------------
# HM4b fix round (MAJOR-2): the production runner is api.run, not serve.run
# ---------------------------------------------------------------------------


def test_production_runner_is_api_run(tmp_path, monkeypatch):
    # M2: restore `from serve import run` and the injected api.run is never
    # called, so `calls` stays empty. The production fallback must be api.run.
    calls = []
    # Patch the module the route's deferred `import api` resolves to
    # (sys.modules["api"], not this file's `api` name, which test_api.py may
    # have replaced with its own re-exec'd copy).
    monkeypatch.setattr(
        sys.modules["api"],
        "run",
        lambda argv, **kw: (
            calls.append(argv) or subprocess.CompletedProcess(argv, 0, "[]", "")
        ),
    )
    # No cfg["_run"]: this exercises the production fallback.
    cfg = {"seats": {"spool_dir": str(build_spool(tmp_path))}}
    status, body = call_seats(cfg)
    assert status == 200
    assert calls == [
        ["systemctl", "list-units", "seat@*", "--all", "--output=json", "--no-pager"]
    ]
    assert [row["id"] for row in body["seats"]] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# HM4b fix round (MINOR-2): an unmapped ActiveState answers "unknown"
# ---------------------------------------------------------------------------


def test_unmapped_state_is_unknown(tmp_path):
    # M6: return the raw ActiveState and "unloading" leaks into the enum.
    unmapped = json.dumps(
        [
            {
                "unit": "seat@a.service",
                "load": "loaded",
                "active": "unloading",
                "sub": "deactivating",
            }
        ]
    )

    def run(argv, **kw):
        return subprocess.CompletedProcess(argv, 0, unmapped, "")

    cfg = make_cfg(build_spool(tmp_path), run)
    status, body = call_seats(cfg)
    assert status == 200
    assert rows_by_id(body)["a"]["state"] == "unknown"


# ---------------------------------------------------------------------------
# HM4b fix round (MINOR-3): a malformed/unreadable/missing job.json is skipped
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "make_bad",
    [
        lambda d: (d / "job.json").write_text("{not json"),
        lambda d: (d / "job.json").mkdir(),
        lambda d: None,
    ],
    ids=["malformed", "unreadable", "missing"],
)
def test_malformed_job_json_skipped(tmp_path, make_bad):
    spool = tmp_path / "spool"
    (spool / "bad").mkdir(parents=True)
    make_bad(spool / "bad")
    (spool / "good").mkdir(parents=True)
    (spool / "good" / "job.json").write_text(json.dumps({"port": 43213}))
    cfg = make_cfg(spool, fake_run)
    status, body = call_seats(cfg)
    assert status == 200
    assert [row["id"] for row in body["seats"]] == ["good"]


# ---------------------------------------------------------------------------
# HM4b fix round (MINOR-4): a non-int port answers null, the url omitted
# ---------------------------------------------------------------------------


def test_port_string_is_null(tmp_path):
    # M5: drop the int check and the string port "43211" reaches the row.
    spool = tmp_path / "spool"
    d = spool / "a"
    d.mkdir(parents=True)
    (d / "job.json").write_text(json.dumps({"port": "43211"}))
    cfg = make_cfg(spool, fake_run)
    status, body = call_seats(cfg)
    assert status == 200
    assert rows_by_id(body)["a"]["port"] is None
    assert rows_by_id(body)["a"]["url"] is None


# ---------------------------------------------------------------------------
# HM4b fix round (MINOR-5): a null seats section and a relative spool_dir are
# answered, never raised (and never a silent process-cwd read)
# ---------------------------------------------------------------------------


def test_seats_null_config(tmp_path, monkeypatch):
    # MAJOR-2: a null seats section defaults to the spool (interface 2), not
    # "seats is not configured". read_jobs is stubbed empty so the assert tests
    # the default and the no-error answer, never the live /var/lib/seat/jobs
    # contents (which exist on this machine and would make a non-empty list).
    seen = []
    monkeypatch.setattr(
        api_seats, "read_jobs", lambda spool_dir: seen.append(spool_dir) or {}
    )
    cfg = {"seats": None, "_run": fake_run}
    status, body = call_seats(cfg)
    assert status == 200
    assert seen == ["/var/lib/seat/jobs"]
    assert body["seats"] == []
    assert "error" not in body


def test_relative_spool_dir_error(tmp_path):
    cfg = {"seats": {"spool_dir": "relative/spool"}, "_run": fake_run}
    status, body = call_seats(cfg)
    assert status == 200
    assert body["seats"] == []
    assert "error" in body


# ---------------------------------------------------------------------------
# HM4c fix round (MAJOR-1): the production seam captures and is bounded
# ---------------------------------------------------------------------------


def _stub_systemctl(tmp_path, body, sleep=None):
    """A PATH-installed `systemctl` stub that prints `body` after an optional
    sleep, so the production seam (api.run → subprocess.run) finds it."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "systemctl"
    lines = ["#!/bin/sh"]
    if sleep is not None:
        lines.append(f"sleep {sleep}")
    lines.append(f"echo '{body}'")
    stub.write_text("\n".join(lines) + "\n")
    stub.chmod(0o755)
    return bin_dir


def test_production_seam_parses_real_output(tmp_path, monkeypatch):
    # M1 (no-capture): without capture_output, cp.stdout is None, the JSON is
    # lost to the server's stdout, and every state degrades to "unknown".
    body = json.dumps(
        [
            {
                "unit": "seat@a.service",
                "load": "loaded",
                "active": "active",
                "sub": "running",
            }
        ]
    )
    bin_dir = _stub_systemctl(tmp_path, body)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    cfg = {"seats": {"spool_dir": str(build_spool(tmp_path))}}
    status, resp = call_seats(cfg)
    assert status == 200
    assert rows_by_id(resp)["a"]["state"] == "active"


def test_production_seam_timeout(tmp_path, monkeypatch):
    # M2 (no-timeout): without the seam's timeout default the sleep finishes
    # and the seat reports "active", so the route never names the timeout.
    body = json.dumps(
        [
            {
                "unit": "seat@a.service",
                "load": "loaded",
                "active": "active",
                "sub": "running",
            }
        ]
    )
    bin_dir = _stub_systemctl(tmp_path, body, sleep=3)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ.get('PATH', '')}")
    monkeypatch.setitem(api.APP.cfg, "_timeout", 1.0)
    cfg = {"seats": {"spool_dir": str(build_spool(tmp_path))}}
    status, body = call_seats(cfg)
    assert status == 200
    assert {row["state"] for row in rows_by_id(body).values()} == {"unknown"}
    assert "timed out" in body["error"]


# ---------------------------------------------------------------------------
# HM4c fix round (MAJOR-2): the default spool_dir is restored
# ---------------------------------------------------------------------------


def test_default_spool_dir(monkeypatch):
    # M3 (no-default-spool): without the default the empty config answers
    # "seats is not configured" and read_jobs is never called.
    seen = []
    monkeypatch.setattr(
        api_seats, "read_jobs", lambda spool_dir: seen.append(spool_dir) or {}
    )
    monkeypatch.setattr(
        api, "run", lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "[]", "")
    )
    status, body = call_seats({})
    assert status == 200
    assert seen == ["/var/lib/seat/jobs"]
    assert body["seats"] == []


def test_default_spool_dir_matches_helm_default():
    # HM5c: the module's DEFAULT_SPOOL_DIR must match the nix module's default
    # (nixosModules/helm.nix:577 and the helm-eval assertion, both
    # "/var/lib/seat/jobs"), never the stale "/var/lib/seat-lane/spool".
    assert api_seats._DEFAULT_SPOOL_DIR == "/var/lib/seat/jobs"


# ---------------------------------------------------------------------------
# HM4c fix round (MINOR-1): a refusal is an error body, never swallowed
# ---------------------------------------------------------------------------


def test_refused_verb_is_error_body(tmp_path, monkeypatch):
    # M6 (refusal-as-data): without the error body a refusal is
    # indistinguishable from a successful empty read.
    monkeypatch.setattr(
        api_seats, "_SYSTEMCTL_LIST", ["systemctl", "show", "sshd.service"]
    )
    cfg = {"seats": {"spool_dir": str(build_spool(tmp_path))}}
    status, body = call_seats(cfg)
    assert status == 200
    assert "api.run refuses" in body["error"]
    assert {row["state"] for row in rows_by_id(body).values()} == {"unknown"}


# ---------------------------------------------------------------------------
# HM5: the three writes — start, stop, attach — behind the seat-only polkit
# rule. Every handler runs through HM2's api.run seam (cfg["_run"] in tests),
# so the runner below records the exact argv each handler builds: the mutant
# column (M1..M9) is reproduced as test names, each written to fail on exactly
# the mutation its name targets, never to rubber-stamp the current code.
# ---------------------------------------------------------------------------

WRITE_SEATS = {
    "dsh_home": "~/.local/share/dsh-openrouter",
    "model": "deepseek/deepseek-v4-pro-0813",
    "effort": "medium",
}


class RecordingRunner:
    """A fake seam that records every argv and returns a canned result."""

    def __init__(self, stdout="job123\n", returncode=0, stderr=""):
        self.calls = []
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        return subprocess.CompletedProcess(
            argv, self.returncode, self.stdout, self.stderr
        )


def write_cfg(spool, run):
    """cfg with a spool_dir and a recording runner, the shape config.json's
    seats section supplies (spool_dir, submit, dsh_home, model, effort)."""
    seats = dict(WRITE_SEATS)
    seats["spool_dir"] = str(spool)
    return {"seats": seats, "_run": run}


def start_req(body):
    return api.Request(method="POST", path="/v1/seats", body=json.dumps(body).encode())


def stop_req(seat_id):
    return api.Request(
        method="POST",
        path=f"/v1/seats/{seat_id}/stop",
        params={"id": seat_id},
    )


def attach_req(seat_id):
    return api.Request(
        method="POST",
        path=f"/v1/seats/{seat_id}/attach",
        params={"id": seat_id},
    )


def write_spool(root):
    """A spool with one running seat (a, port 43211) and one spooled (c, no
    port) — the two arms attach discriminates (404/409/200)."""
    spool = root / "spool"
    (spool / "a").mkdir(parents=True)
    (spool / "a" / "job.json").write_text(json.dumps({"port": 43211}))
    (spool / "c").mkdir(parents=True)
    (spool / "c" / "job.json").write_text(json.dumps({"port": None}))
    return spool


# ---------------------------------------------------------------------------
# start: POST /v1/seats
# ---------------------------------------------------------------------------


def test_start_web_seat_round_trips(tmp_path):
    # Negative control: a web start emits the exact argv — the operator's
    # dsh-home/model/effort from cfg["seats"] (never the request body), the
    # mode from the body, and never --port (SA3 allocates). A discriminating
    # mutant emits "drive" instead of "web" and fails on the argv.
    run = RecordingRunner()
    cfg = write_cfg(write_spool(tmp_path), run)
    status, body = api_seats.start_seat(
        cfg, start_req({"mode": "web", "workspace": "/var/lib/w"})
    )
    assert status == 202
    assert body == {"id": "job123"}
    assert run.calls == [
        [
            "seat-submit",
            "web",
            "--workspace",
            "/var/lib/w",
            "--dsh-home",
            "~/.local/share/dsh-openrouter",
            "--model",
            "deepseek/deepseek-v4-pro-0813",
            "--effort",
            "medium",
        ]
    ]


def test_start_reads_only_the_first_stdout_line(tmp_path):
    # The started path's seat-submit prints the id then port=43210 (SA3's
    # second stdout line); start_seat must answer {"id": <first line>} only,
    # never carry the port= line into the id the UI later names the unit by.
    run = RecordingRunner(stdout="job123\nport=43210\n")
    cfg = write_cfg(write_spool(tmp_path), run)
    status, body = api_seats.start_seat(
        cfg, start_req({"mode": "web", "workspace": "/var/lib/w"})
    )
    assert status == 202
    assert body == {"id": "job123"}


def test_start_never_passes_port(tmp_path):
    # M1: append --port 43210 to the argv and this recorded-argv assert fails.
    run = RecordingRunner()
    cfg = write_cfg(write_spool(tmp_path), run)
    status, _ = api_seats.start_seat(
        cfg, start_req({"mode": "web", "workspace": "/var/lib/w"})
    )
    assert status == 202
    assert run.calls
    argv = run.calls[0]
    assert "--port" not in argv
    assert 43210 not in argv


def test_start_argv_carries_required_seat_submit_flags(tmp_path):
    # M9: drop --dsh-home/--model/--effort and the superset assert fails on the
    # missing keys.
    run = RecordingRunner()
    cfg = write_cfg(write_spool(tmp_path), run)
    status, _ = api_seats.start_seat(
        cfg, start_req({"mode": "drive", "workspace": "/var/lib/w"})
    )
    assert status == 202
    assert run.calls
    argv = run.calls[0]
    assert {"--dsh-home", "--model", "--effort"} <= set(argv)


def test_start_rejects_unknown_keys(tmp_path):
    # M7: accept {"mode","workspace","port"} and this 400 becomes 202.
    run = RecordingRunner()
    cfg = write_cfg(write_spool(tmp_path), run)
    status, _ = api_seats.start_seat(
        cfg, start_req({"mode": "web", "workspace": "/w", "port": 1})
    )
    assert status == 400
    assert run.calls == []


def test_start_rejects_relative_workspace(tmp_path):
    run = RecordingRunner()
    cfg = write_cfg(write_spool(tmp_path), run)
    status, _ = api_seats.start_seat(
        cfg, start_req({"mode": "web", "workspace": "relative/w"})
    )
    assert status == 400
    assert run.calls == []


def test_start_rejects_unknown_mode(tmp_path):
    run = RecordingRunner()
    cfg = write_cfg(write_spool(tmp_path), run)
    status, _ = api_seats.start_seat(
        cfg, start_req({"mode": "headless", "workspace": "/w"})
    )
    assert status == 400
    assert run.calls == []


# ---------------------------------------------------------------------------
# stop: POST /v1/seats/<id>/stop
# ---------------------------------------------------------------------------


def test_stop_seat_round_trips(tmp_path):
    run = RecordingRunner(stdout="")
    cfg = write_cfg(write_spool(tmp_path), run)
    status, body = api_seats.stop_seat(cfg, stop_req("a"))
    assert status == 202
    assert body["unit"] == "seat@a.service"
    assert run.calls == [["systemctl", "stop", "seat@a.service"]]


def test_stop_rejects_traversal_id(tmp_path):
    # M2: drop the id regex and the id "../helm-switch@gaming" reaches the
    # runner, returning 202 with an argv naming helm-switch — this 400 catches
    # it (and the runner is never called).
    run = RecordingRunner(stdout="")
    cfg = write_cfg(write_spool(tmp_path), run)
    status, _ = api_seats.stop_seat(cfg, stop_req("../helm-switch@gaming"))
    assert status == 400
    assert run.calls == []


def test_verbs_are_start_stop_only():
    # M3: widen VERBS to ("start","stop","restart") and this fails.
    assert api_seats.VERBS == ("start", "stop")


# ---------------------------------------------------------------------------
# attach: POST /v1/seats/<id>/attach
# ---------------------------------------------------------------------------


def test_attach_running_returns_url(tmp_path):
    status, body = api_seats.attach_seat(
        write_cfg(write_spool(tmp_path), RecordingRunner()), attach_req("a")
    )
    assert status == 200
    assert body == {"url": "http://127.0.0.1:43211/"}


def test_attach_spooled_is_409(tmp_path):
    # M4: return 200 with url:null for a spooled seat and this 409 fails.
    status, _ = api_seats.attach_seat(
        write_cfg(write_spool(tmp_path), RecordingRunner()), attach_req("c")
    )
    assert status == 409


def test_attach_missing_job_is_404(tmp_path):
    status, _ = api_seats.attach_seat(
        write_cfg(write_spool(tmp_path), RecordingRunner()), attach_req("nope")
    )
    assert status == 404


def test_attach_relative_spool_dir_is_error(tmp_path):
    # HM5c (the review's MAJOR): a relative spool_dir is a refusal, so it answers
    # the same error shape as _refused_error — 502 {"error": …}, never a 200
    # without a "url" key (M4: deleting the two guard lines lets the relative
    # path through and this 502 assert fails on the 200 that follows).
    cfg = {"seats": {"spool_dir": "relative/spool"}, "_run": RecordingRunner()}
    status, body = api_seats.attach_seat(cfg, attach_req("a"))
    assert status == 502
    assert body == {"error": "seats.spool_dir must be absolute"}


# ---------------------------------------------------------------------------
# route registration: the three writes join the read in route_table()
# ---------------------------------------------------------------------------


def test_seats_write_routes_registered():
    table = {(m, p) for m, p, _ in api.route_table()}
    assert ("POST", "/v1/seats") in table
    assert ("POST", "/v1/seats/<id>/stop") in table
    assert ("POST", "/v1/seats/<id>/attach") in table


# ---------------------------------------------------------------------------
# HM5b fix round: a refused/absent/timed-out seat write is an error body, never
# 202. api.run never raises — it converts a polkit refusal to returncode 126, a
# timeout to 124, an absent program to 127, and seat-submit's argparse exit 2
# passes straight through (HM4c's house rule: a refusal is an error body, never
# swallowed). The write handlers must read the returncode and answer the error
# body, never the 202 the gate's MAJOR found.
# ---------------------------------------------------------------------------

WRITE_REFUSALS = [
    # (route, returncode, program, stderr first line, id)
    pytest.param(
        "stop",
        126,
        "systemctl stop",
        "Interactive authentication required",
        "stop-polkit-126",
    ),
    pytest.param(
        "start",
        2,
        "seat-submit",
        "seat-submit: error: the following arguments are required: --dsh-home",
        "start-exit-2",
    ),
    pytest.param(
        "start",
        127,
        "seat-submit",
        "FileNotFoundError: No such file: 'seat-submit'",
        "start-absent-127",
    ),
    pytest.param(
        "stop", 124, "systemctl stop", "timed out after 10.0s", "stop-timeout-124"
    ),
]


@pytest.mark.parametrize("route,code,program,stderr,label", WRITE_REFUSALS)
def test_refused_write_is_error_body(tmp_path, route, code, program, stderr, label):
    # M (the review's MAJOR): read only the success path and a non-zero
    # returncode is swallowed as 202 {}. Here the error body carries the code
    # and the seam's stderr, and the status is 502 — never 202.
    run = RecordingRunner(returncode=code, stderr=stderr)
    cfg = write_cfg(write_spool(tmp_path), run)
    if route == "start":
        status, body = api_seats.start_seat(
            cfg, start_req({"mode": "web", "workspace": "/var/lib/w"})
        )
    else:
        status, body = api_seats.stop_seat(cfg, stop_req("a"))
    assert status == 502
    assert body == {"error": f"{program} failed: returncode {code}: {stderr}"}


def test_start_without_seat_submit_in_programs_is_error(tmp_path, monkeypatch):
    # The gate's unlisted mutant (M10): drop "seat-submit" from api.PROGRAMS and
    # the production seam (api.run, not the injected runner) refuses the program
    # with returncode 126. The start route must answer the error body, never
    # 202 {"id": ""}. No _run is injected, so this exercises production api.run;
    # the refusal raises before any subprocess is spawned.
    monkeypatch.setattr(
        api, "PROGRAMS", tuple(p for p in api.PROGRAMS if p != "seat-submit")
    )
    cfg = write_cfg(write_spool(tmp_path), None)
    status, body = api_seats.start_seat(
        cfg, start_req({"mode": "web", "workspace": "/var/lib/w"})
    )
    assert status == 502
    assert "returncode 126" in body["error"]
    assert "seat-submit" in body["error"]


# ---------------------------------------------------------------------------
# interface 7: seat-submit's own parser is the backstop — omitting the three
# required flags exits 2 before any unit starts. Run against the real parser
# (not the fake runner); skipped inside the helm-unit sandbox, which copies
# only pkgs/helm + pkgs/evidence + tests/helm, never pkgs/seat.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (HERE.parents[2] / "pkgs" / "seat" / "seat-submit.py").exists(),
    reason="pkgs/seat not present in the helm-unit sandbox",
)
def test_seat_submit_missing_required_flags_exits_2():
    cp = subprocess.run(
        [
            sys.executable,
            str(HERE.parents[2] / "pkgs" / "seat" / "seat-submit.py"),
            "web",
            "--workspace",
            "/tmp",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 2
    for flag in ("--dsh-home", "--model", "--effort"):
        assert flag in cp.stderr
