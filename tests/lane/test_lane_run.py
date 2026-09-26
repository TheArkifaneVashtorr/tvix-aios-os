"""Tests for pkgs/lane/lane-run.py (Lane L round 1 plan, Task 3).

Runs the script as a real subprocess exactly the way
nixosModules/modelLane.nix's unit invokes it (`lane-run <lane> <job-id>`) --
lane-run.py is a standalone script (hyphenated filename, not an importable
module) so black-box subprocess testing is also the natural choice here, not
just a workaround.

A local plain-HTTP server stands in for the broker-fronted upstream
(LANE_SCHEME=http, set only by tests -- see the module docstring in
lane-run.py). This proves the request lane-run.py builds: the provider
block, the absence of any Authorization header, schema passthrough, and the
retry policy. It does NOT prove the broker actually injects the credential
over the real HTTPS_PROXY + CA path -- that is checks.lane-vm
(tests/integration/lane-vm.nix).
"""

import http.server
import importlib.util
import json
import os
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "pkgs" / "lane" / "lane-run.py",
    Path("pkgs/lane/lane-run.py"),
]
LANE_RUN = next(p for p in _CANDIDATES if p.exists())

DEFAULT_RESPONSE_BODY = {
    "id": "gen-1",
    "model": "test/model-flash",
    "provider": "TestProvider",
    "choices": [{"message": {"role": "assistant", "content": "hello"}}],
    "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
}


class _Capture:
    def __init__(self):
        self.requests = []


def _make_handler(capture, status_sequence, response_body):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            capture.requests.append(
                {
                    "path": self.path,
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body": json.loads(raw.decode("utf-8")) if raw else None,
                }
            )
            idx = len(capture.requests) - 1
            status = status_sequence[min(idx, len(status_sequence) - 1)]
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if status == 200:
                self.wfile.write(json.dumps(response_body).encode("utf-8"))
            else:
                self.wfile.write(b'{"error": {"message": "boom"}}')

    return Handler


@pytest.fixture
def fake_server():
    servers = []

    def start(status_sequence=(200,), response_body=None):
        capture = _Capture()
        handler = _make_handler(
            capture, list(status_sequence), response_body or DEFAULT_RESPONSE_BODY
        )
        httpd = http.server.HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        servers.append(httpd)
        return httpd, capture

    yield start
    for httpd in servers:
        httpd.shutdown()
        httpd.server_close()


def _write_job(base, lane, job_id, job):
    jobs_dir = base / lane / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    (jobs_dir / f"{job_id}.json").write_text(json.dumps(job))


def _run(base, lane, job_id, host, classes="permitted", extra_env=None):
    env = dict(os.environ)
    # Strip proxy variables that would redirect the runner's HTTP requests
    # through a proxy (inherited from the test process environment), causing
    # the fake-server tests to fail with an opaque HTTP 403. Tests that
    # deliberately need a proxy variable set in the runner's environment
    # can pass it via extra_env, which is applied after the strip.
    for var in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "http_proxy",
        "https_proxy",
        "ALL_PROXY",
        "NO_PROXY",
    ):
        env.pop(var, None)
    env["LANE_STATE_DIR"] = str(base)
    env["LANE_HOST"] = host
    env["LANE_SCHEME"] = "http"
    env["LANE_CLASSES"] = classes
    env["LANE_RETRY_BACKOFF_S"] = "0,0,0"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(LANE_RUN), lane, job_id],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _result(base, lane, job_id):
    return json.loads((base / lane / "results" / f"{job_id}.json").read_text())


def _ledger_lines(base, lane):
    path = base / lane / "ledger.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


# --- chat kind -------------------------------------------------------------


def test_chat_sends_provider_block_and_no_authorization_header(tmp_path, fake_server):
    httpd, capture = fake_server()
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "deepseek/deepseek-v4-flash",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 100,
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 0, proc.stderr

    assert len(capture.requests) == 1
    req = capture.requests[0]
    assert req["path"] == "/api/v1/chat/completions"
    assert "authorization" not in req["headers"]
    assert req["body"]["model"] == "deepseek/deepseek-v4-flash"
    assert req["body"]["messages"] == [{"role": "user", "content": "hi"}]
    assert req["body"]["provider"] == {"zdr": True, "data_collection": "deny"}

    result = _result(tmp_path, "openrouter", "job1")
    assert result["output"] == "hello"
    assert result["provider"] == "TestProvider"
    assert result["usage"]["total_tokens"] == 5


def test_chat_provider_order_from_job_providers(tmp_path, fake_server):
    httpd, capture = fake_server()
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
            "providers": ["deepseek", "fallback-provider"],
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 0, proc.stderr
    assert capture.requests[0]["body"]["provider"]["order"] == [
        "deepseek",
        "fallback-provider",
    ]


def test_chat_schema_becomes_json_schema_response_format(tmp_path, fake_server):
    httpd, capture = fake_server()
    schema = {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    }
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
            "schema": schema,
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 0, proc.stderr
    assert capture.requests[0]["body"]["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "lane_job_schema",
            "strict": True,
            "schema": schema,
        },
    }


def test_chat_retries_5xx_then_succeeds(tmp_path, fake_server):
    httpd, capture = fake_server(status_sequence=[500, 500, 200])
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 0, proc.stderr
    assert len(capture.requests) == 3
    assert _result(tmp_path, "openrouter", "job1")["output"] == "hello"


def test_chat_retries_429_then_succeeds(tmp_path, fake_server):
    httpd, capture = fake_server(status_sequence=[429, 200])
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 0, proc.stderr
    assert len(capture.requests) == 2
    assert _result(tmp_path, "openrouter", "job1")["output"] == "hello"


def test_chat_retry_exhaustion_fails_with_error_result(tmp_path, fake_server):
    httpd, capture = fake_server(status_sequence=[500, 500, 500])
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 1, proc.stdout
    assert len(capture.requests) == 3
    result = _result(tmp_path, "openrouter", "job1")
    assert "error" in result
    assert not _ledger_lines(tmp_path, "openrouter")


def test_chat_does_not_retry_on_400(tmp_path, fake_server):
    httpd, capture = fake_server(status_sequence=[400])
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 1
    assert len(capture.requests) == 1


def test_chat_writes_one_ledger_line(tmp_path, fake_server):
    httpd, _capture = fake_server()
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 0, proc.stderr
    lines = _ledger_lines(tmp_path, "openrouter")
    assert len(lines) == 1
    line = lines[0]
    assert line["job"] == "job1"
    assert line["kind"] == "chat"
    assert line["model"] == "test/model-flash"
    assert line["provider"] == "TestProvider"
    assert line["usage"]["total_tokens"] == 5
    assert isinstance(line["wall_s"], (int, float))
    assert isinstance(line["ts"], (int, float))


def test_chat_job_timeout_s_reaches_urlopen(tmp_path, monkeypatch):
    """A chat job's integer "timeout_s" must reach urlopen(timeout=...),
    overriding LANE_HTTP_TIMEOUT_S (default 600). Load the hyphenated
    standalone script in-process (importlib, same LANE_RUN path the
    subprocess tests use) to monkeypatch urllib.request.urlopen."""
    spec = importlib.util.spec_from_file_location("lane_run", LANE_RUN)
    lane_run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lane_run)

    calls = []

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            pass

        def read(self):
            return json.dumps(DEFAULT_RESPONSE_BODY).encode("utf-8")

    def fake_urlopen(*_args, **_kwargs):
        calls.append(_kwargs)
        return _FakeResp()

    monkeypatch.setattr(lane_run.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("LANE_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("LANE_HOST", "127.0.0.1")
    paths = lane_run._lane_paths("openrouter")
    job = {
        "kind": "chat",
        "class": "permitted",
        "model": "m",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10,
        "timeout_s": 7,
    }
    rc = lane_run.run_chat(job, "job1", paths)
    assert rc == lane_run.EXIT_OK
    assert calls and calls[0]["timeout"] == 7


# --- refusals ---------------------------------------------------------------


def test_local_only_job_is_refused_and_never_sent(tmp_path, fake_server):
    httpd, capture = fake_server()
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "local-only",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 3, proc.stdout
    assert capture.requests == []
    result = _result(tmp_path, "openrouter", "job1")
    assert "local-only" in result["error"]
    assert not _ledger_lines(tmp_path, "openrouter")


def test_job_class_not_in_lane_classes_is_refused(tmp_path, fake_server):
    httpd, capture = fake_server()
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "m",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 10,
        },
    )
    proc = _run(
        tmp_path,
        "openrouter",
        "job1",
        f"127.0.0.1:{httpd.server_port}",
        classes="",
    )
    assert proc.returncode == 3, proc.stdout
    assert capture.requests == []


# --- agent kind --------------------------------------------------------------


def _write_fake_claude(bin_dir, capture_path, exit_code=0, result_body=None):
    """A fake `claude` on PATH: records its own argv/cwd/env, then prints a
    Claude-Code-`--output-format json`-shaped blob and exits."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "claude"
    body = result_body or {
        "result": "agent done",
        "usage": {"input_tokens": 3, "output_tokens": 5},
    }
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        f"capture_path = {str(capture_path)!r}\n"
        "data = {\n"
        "    'argv': sys.argv[1:],\n"
        "    'cwd': os.path.realpath(os.getcwd()),\n"
        "    'env': {k: os.environ.get(k) for k in "
        "['ANTHROPIC_BASE_URL', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_API_KEY', "
        "'CLAUDE_CONFIG_DIR']},\n"
        "}\n"
        "with open(capture_path, 'w') as f:\n"
        "    json.dump(data, f)\n"
        f"print(json.dumps({body!r}))\n"
        f"sys.exit({exit_code})\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script


def test_agent_kind_env_and_argv(tmp_path):
    bin_dir = tmp_path / "fakebin"
    capture_path = tmp_path / "claude_capture.json"
    _write_fake_claude(bin_dir, capture_path)

    repo_dir = tmp_path / "openrouter" / "jobs" / "job1" / "repo"
    repo_dir.mkdir(parents=True)
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "agent",
            "class": "permitted",
            "model": "test/model",
            "prompt": "do the thing",
            "repo": str(repo_dir),
            "max_turns": 7,
        },
    )
    extra_env = {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = _run(tmp_path, "openrouter", "job1", "lane-host.test", extra_env=extra_env)
    assert proc.returncode == 0, proc.stderr

    capture = json.loads(capture_path.read_text())
    assert capture["argv"] == [
        "-p",
        "do the thing",
        "--model",
        "test/model",
        "--output-format",
        "json",
        "--max-turns",
        "7",
        "--permission-mode",
        "acceptEdits",
    ]
    assert capture["env"]["ANTHROPIC_BASE_URL"] == "https://lane-host.test/api"
    assert capture["env"]["ANTHROPIC_AUTH_TOKEN"] == "lane-dummy-token"
    assert capture["env"]["ANTHROPIC_API_KEY"] is None
    assert os.path.realpath(capture["env"]["CLAUDE_CONFIG_DIR"]) == os.path.realpath(
        repo_dir.parent / "config"
    )
    assert capture["cwd"] == os.path.realpath(repo_dir)

    result = _result(tmp_path, "openrouter", "job1")
    assert result["output"] == "agent done"
    assert result["usage"] == {"input_tokens": 3, "output_tokens": 5}
    assert result["provider"] == "lane-host.test"

    lines = _ledger_lines(tmp_path, "openrouter")
    assert len(lines) == 1
    assert lines[0]["kind"] == "agent"
    assert lines[0]["model"] == "test/model"


def test_agent_kind_defaults_max_turns_to_40(tmp_path):
    bin_dir = tmp_path / "fakebin"
    capture_path = tmp_path / "claude_capture.json"
    _write_fake_claude(bin_dir, capture_path)

    repo_dir = tmp_path / "openrouter" / "jobs" / "job1" / "repo"
    repo_dir.mkdir(parents=True)
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "agent",
            "class": "permitted",
            "model": "test/model",
            "prompt": "do the thing",
            "repo": str(repo_dir),
        },
    )
    extra_env = {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = _run(tmp_path, "openrouter", "job1", "lane-host.test", extra_env=extra_env)
    assert proc.returncode == 0, proc.stderr
    capture = json.loads(capture_path.read_text())
    assert "--max-turns" in capture["argv"]
    assert capture["argv"][capture["argv"].index("--max-turns") + 1] == "40"


# --- snapshot lifecycle (T3 review: no test anywhere exercised either
# branch of the default-delete / --keep-snapshot behaviour) -------------------


def _write_fake_claude_that_edits_cwd(bin_dir, touch_name="edited.txt", exit_code=0):
    """A fake `claude` that writes a file into its own cwd before exiting
    -- the only way a test can tell, after the fact, whether lane-run.py
    kept or deleted the agent job's repo snapshot (checks.lane-vm's
    fakeClaude does the same thing, for the same reason)."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "claude"
    body = {"result": "agent done", "usage": {}}
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        f"open({touch_name!r}, 'w').write('edited')\n"
        f"print(json.dumps({body!r}))\n"
        f"sys.exit({exit_code})\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script


def test_agent_default_deletes_snapshot_after_result(tmp_path):
    """No "keep_snapshot" key on the job at all (the shape lane-submit.py
    itself never actually writes, but a belt-and-braces case for anything
    that writes a job file by hand) -- must still default to deleting the
    snapshot, same as an explicit false."""
    bin_dir = tmp_path / "fakebin"
    _write_fake_claude_that_edits_cwd(bin_dir)

    repo_dir = tmp_path / "openrouter" / "jobs" / "job1" / "repo"
    repo_dir.mkdir(parents=True)
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "agent",
            "class": "permitted",
            "model": "test/model",
            "prompt": "do the thing",
            "repo": str(repo_dir),
        },
    )
    extra_env = {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = _run(tmp_path, "openrouter", "job1", "lane-host.test", extra_env=extra_env)
    assert proc.returncode == 0, proc.stderr
    assert not repo_dir.exists()
    result = _result(tmp_path, "openrouter", "job1")
    assert result["output"] == "agent done"


def test_agent_keep_snapshot_true_preserves_edited_snapshot(tmp_path):
    bin_dir = tmp_path / "fakebin"
    _write_fake_claude_that_edits_cwd(bin_dir)

    repo_dir = tmp_path / "openrouter" / "jobs" / "job1" / "repo"
    repo_dir.mkdir(parents=True)
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "agent",
            "class": "permitted",
            "model": "test/model",
            "prompt": "do the thing",
            "repo": str(repo_dir),
            "keep_snapshot": True,
        },
    )
    extra_env = {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = _run(tmp_path, "openrouter", "job1", "lane-host.test", extra_env=extra_env)
    assert proc.returncode == 0, proc.stderr
    assert repo_dir.is_dir()
    assert (repo_dir / "edited.txt").read_text() == "edited"


def test_agent_default_deletes_snapshot_even_on_claude_failure(tmp_path):
    """finally: covers the failure paths too -- deliberately, per
    run_agent's own comment -- but that means a crashed agent job's
    snapshot is gone by default just as much as a successful one's. Pin
    that here so a future change doesn't silently start keeping failed
    snapshots (or deleting successful ones) without a test noticing
    either way."""
    bin_dir = tmp_path / "fakebin"
    _write_fake_claude_that_edits_cwd(bin_dir, exit_code=1)

    repo_dir = tmp_path / "openrouter" / "jobs" / "job1" / "repo"
    repo_dir.mkdir(parents=True)
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "agent",
            "class": "permitted",
            "model": "test/model",
            "prompt": "do the thing",
            "repo": str(repo_dir),
        },
    )
    extra_env = {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = _run(tmp_path, "openrouter", "job1", "lane-host.test", extra_env=extra_env)
    assert proc.returncode == 1
    assert not repo_dir.exists()
    result = _result(tmp_path, "openrouter", "job1")
    assert "error" in result


# --- crash backstop / retry edge cases ---------------------------------------


def test_crash_inside_dispatch_still_writes_error_result(tmp_path, fake_server):
    """A chat job missing "messages" raises a bare KeyError inside
    run_chat, before the retry loop even starts -- main()'s try/except
    around dispatch must still turn that into a result file, not a bare
    traceback and no result (plan Task 3: "every outcome writes a
    result")."""
    httpd, capture = fake_server()
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "chat",
            "class": "permitted",
            "model": "m",
            "max_tokens": 10,
            # "messages" deliberately omitted.
        },
    )
    proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
    assert proc.returncode == 1, proc.stdout
    assert capture.requests == []
    result = _result(tmp_path, "openrouter", "job1")
    assert "error" in result
    assert not _ledger_lines(tmp_path, "openrouter")


def _make_stalling_handler(capture, delay_s):
    """Sends response headers (with a promised Content-Length) right away,
    then stalls before writing any body -- the client's urlopen() call has
    already returned by the time this matters, so the timeout fires inside
    resp.read() as a raw, un-wrapped socket.timeout (urllib only wraps
    OSErrors raised during the connect/header phase into URLError).
    Records one entry in `capture.requests` per POST received, so the
    retry itself (not just the eventual failure) can be asserted on."""

    body = json.dumps(DEFAULT_RESPONSE_BODY).encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            capture.requests.append(True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            time.sleep(delay_s)
            self.wfile.write(body)

    return Handler


def test_chat_stalled_read_is_retried_then_fails_with_result(tmp_path):
    """A body that never finishes arriving within LANE_HTTP_TIMEOUT_S
    raises socket.timeout from resp.read() -- must be caught, treated as
    retryable (same as a connection error), and ultimately leave a result
    file after exhausting retries, not crash bare.

    Mutation-survivor fix (T3 review): asserting only "an error result"
    here is byte-identical to what main()'s crash backstop alone would
    also produce, so deleting the `except TimeoutError` clause left this
    test green. Discriminate the retry itself the way the sibling
    non-JSON test already does (capture.requests == 3), and pin the error
    text to the TimeoutError branch specifically ("read timed out") so
    removing that except clause -- which would instead surface as an
    uncaught exception / different error text -- turns this red."""
    capture = _Capture()
    # ThreadingHTTPServer, not the plain HTTPServer the other fixtures use:
    # a single-threaded server can't accept attempt 2's connection until
    # attempt 1's do_POST returns (it's still sleeping through delay_s),
    # so by the time it gets there the client has long since abandoned
    # that connection on its own 0.15s timeout -- the retry would then
    # race the server's backlog instead of reliably producing 3 clean
    # request/response cycles. A thread per connection means every
    # attempt's headers are sent immediately, so each one times out the
    # same way (resp.read() on the stalled body), which is the behaviour
    # this test means to pin.
    httpd = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), _make_stalling_handler(capture, 1.0)
    )
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        _write_job(
            tmp_path,
            "openrouter",
            "job1",
            {
                "kind": "chat",
                "class": "permitted",
                "model": "m",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 10,
            },
        )
        proc = _run(
            tmp_path,
            "openrouter",
            "job1",
            f"127.0.0.1:{httpd.server_port}",
            extra_env={"LANE_HTTP_TIMEOUT_S": "0.15"},
        )
        assert proc.returncode == 1, proc.stdout
        assert len(capture.requests) == 3
        result = _result(tmp_path, "openrouter", "job1")
        assert "read timed out" in result["error"]
        assert not _ledger_lines(tmp_path, "openrouter")
    finally:
        httpd.shutdown()
        httpd.server_close()


def _make_non_json_handler(capture):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            capture.requests.append(True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"this is not json{{{")

    return Handler


def test_chat_non_json_200_is_retried_then_fails_with_result(tmp_path):
    """A 200 whose body isn't valid JSON must not crash json.loads()
    uncaught -- treated as retryable, and the retries are exhausted into a
    normal error result, same shape as an HTTP-error exhaustion."""
    capture = _Capture()
    httpd = http.server.HTTPServer(("127.0.0.1", 0), _make_non_json_handler(capture))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        _write_job(
            tmp_path,
            "openrouter",
            "job1",
            {
                "kind": "chat",
                "class": "permitted",
                "model": "m",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 10,
            },
        )
        proc = _run(tmp_path, "openrouter", "job1", f"127.0.0.1:{httpd.server_port}")
        assert proc.returncode == 1, proc.stdout
        assert len(capture.requests) == 3
        result = _result(tmp_path, "openrouter", "job1")
        assert "error" in result
        assert not _ledger_lines(tmp_path, "openrouter")
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_agent_kind_claude_failure_writes_error_result(tmp_path):
    bin_dir = tmp_path / "fakebin"
    capture_path = tmp_path / "claude_capture.json"
    _write_fake_claude(bin_dir, capture_path, exit_code=1)

    repo_dir = tmp_path / "openrouter" / "jobs" / "job1" / "repo"
    repo_dir.mkdir(parents=True)
    _write_job(
        tmp_path,
        "openrouter",
        "job1",
        {
            "kind": "agent",
            "class": "permitted",
            "model": "test/model",
            "prompt": "do the thing",
            "repo": str(repo_dir),
        },
    )
    extra_env = {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = _run(tmp_path, "openrouter", "job1", "lane-host.test", extra_env=extra_env)
    assert proc.returncode == 1
    result = _result(tmp_path, "openrouter", "job1")
    assert "error" in result
    assert not _ledger_lines(tmp_path, "openrouter")


def _write_fake_dsh(bin_dir, capture_path, touch_name="made-by-dsh.txt", exit_code=0):
    """A fake `dsh` on PATH: records argv/cwd/env, writes a file into its
    cwd (so the diff capture has something to show), prints a final
    answer on stdout and reasoning on stderr, exits."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "dsh"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        f"capture_path = {str(capture_path)!r}\n"
        "data = {\n"
        "    'argv': sys.argv[1:],\n"
        "    'cwd': os.path.realpath(os.getcwd()),\n"
        "    'env': {k: os.environ.get(k) for k in "
        "['DSH_HOME', 'DSH_TELEMETRY_MODE', 'DSH_PERMISSION_MODE', 'OPENROUTER_API_KEY']},\n"
        "}\n"
        "with open(capture_path, 'w') as f:\n"
        "    json.dump(data, f)\n"
        f"open({touch_name!r}, 'w').write('hello')\n"
        "print('reasoning...', file=sys.stderr)\n"
        "print('dsh done')\n"
        f"sys.exit({exit_code})\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script


def test_dsh_kind_overlay_env_argv_diff_and_ledger(tmp_path):
    bin_dir = tmp_path / "fakebin"
    capture = tmp_path / "capture.json"
    _write_fake_dsh(bin_dir, capture)
    repo_dir = tmp_path / "openrouter" / "jobs" / "job9" / "repo"
    repo_dir.mkdir(parents=True)
    subprocess.run(["git", "-C", str(repo_dir), "init", "-q"], check=True)
    _write_job(
        tmp_path,
        "openrouter",
        "job9",
        {
            "kind": "dsh",
            "class": "permitted",
            "model": "deepseek/deepseek-v4-flash",
            "prompt": "make a file",
            "repo": str(repo_dir),
            "keep_snapshot": True,
        },
    )
    extra_env = {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = _run(tmp_path, "openrouter", "job9", "lane-host.test", extra_env=extra_env)
    assert proc.returncode == 0, proc.stderr
    seen = json.loads(capture.read_text())
    jobdir = repo_dir.parent
    overlay = jobdir / "lane-provider.yml"
    assert seen["argv"][:4] == ["--profile", "headless", "--patch", str(overlay)]
    assert seen["argv"][4] == "make a file"
    assert seen["cwd"] == os.path.realpath(str(repo_dir))
    assert seen["env"]["DSH_HOME"] == str(jobdir / "dsh-home")
    assert seen["env"]["DSH_TELEMETRY_MODE"] == "DISABLED"
    assert seen["env"]["DSH_PERMISSION_MODE"] == "danger-full-access"
    assert seen["env"]["OPENROUTER_API_KEY"] == "lane-dummy-key"
    text = overlay.read_text()
    assert "baseURL: https://lane-host.test/api/v1" in text
    assert "apiKeyEnv: OPENROUTER_API_KEY" in text
    assert "provider: lane" in text and "model: deepseek/deepseek-v4-flash" in text
    assert "id: tool-web\n  disabled: true" in text
    result = _result(tmp_path, "openrouter", "job9")
    assert result["output"] == "dsh done\n" and result["exit"] == 0
    assert "made-by-dsh.txt" in result["diff"] and "## untracked" in result["diff"]
    assert "reasoning..." in result["log"]
    ledger = (tmp_path / "openrouter" / "ledger.jsonl").read_text().strip().splitlines()
    assert json.loads(ledger[-1])["kind"] == "dsh"


def test_dsh_kind_nonzero_exit_records_error(tmp_path):
    bin_dir = tmp_path / "fakebin"
    capture = tmp_path / "capture.json"
    _write_fake_dsh(bin_dir, capture, exit_code=3)
    repo_dir = tmp_path / "openrouter" / "jobs" / "job8" / "repo"
    repo_dir.mkdir(parents=True)
    subprocess.run(["git", "-C", str(repo_dir), "init", "-q"], check=True)
    _write_job(
        tmp_path,
        "openrouter",
        "job8",
        {
            "kind": "dsh",
            "class": "permitted",
            "model": "m",
            "prompt": "p",
            "repo": str(repo_dir),
        },
    )
    extra_env = {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = _run(tmp_path, "openrouter", "job8", "lane-host.test", extra_env=extra_env)
    assert proc.returncode != 0
    result = _result(tmp_path, "openrouter", "job8")
    assert result["error"] == "dsh exited 3" and result["exit"] == 3
    assert not repo_dir.exists()


def test_dsh_kind_home_git_config_and_shared_outputs(tmp_path):
    bin_dir = tmp_path / "fakebin"
    capture = tmp_path / "capture.json"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "dsh"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        f"capture_path = {str(capture)!r}\n"
        "data = {'env': {k: os.environ.get(k) for k in "
        "['HOME', 'GIT_CONFIG_COUNT', 'GIT_CONFIG_KEY_0', 'GIT_CONFIG_VALUE_0']}}\n"
        "with open(capture_path, 'w') as f:\n"
        "    json.dump(data, f)\n"
        "fd = os.open('SECRET.md', os.O_WRONLY | os.O_CREAT, 0o600)\n"
        "os.write(fd, b'x'); os.close(fd)\n"
        "print('dsh done')\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    repo_dir = tmp_path / "openrouter" / "jobs" / "job7" / "repo"
    repo_dir.mkdir(parents=True)
    subprocess.run(["git", "-C", str(repo_dir), "init", "-q"], check=True)
    _write_job(
        tmp_path,
        "openrouter",
        "job7",
        {
            "kind": "dsh",
            "class": "permitted",
            "model": "m",
            "prompt": "p",
            "repo": str(repo_dir),
            "keep_snapshot": True,
        },
    )
    extra_env = {"PATH": f"{bin_dir}:{os.environ['PATH']}"}
    proc = _run(tmp_path, "openrouter", "job7", "lane-host.test", extra_env=extra_env)
    assert proc.returncode == 0, proc.stderr
    seen = json.loads(capture.read_text())["env"]
    assert seen["HOME"] == str(repo_dir.parent / "home")
    assert (
        seen["GIT_CONFIG_COUNT"],
        seen["GIT_CONFIG_KEY_0"],
        seen["GIT_CONFIG_VALUE_0"],
    ) == (
        "1",
        "safe.directory",
        "*",
    )
    assert (repo_dir / "SECRET.md").stat().st_mode & 0o777 == 0o660
    result = _result(tmp_path, "openrouter", "job7")
    assert "SECRET.md" in result["diff"]
