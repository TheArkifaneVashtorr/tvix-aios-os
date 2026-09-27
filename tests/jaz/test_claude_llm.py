"""tests/jaz/test_claude_llm.py -- exercises
tools/experiments/jaz/claude_llm.py's ClaudeGatewayLLM against the REAL
jaz-lang package (pkgs/jaz-lang), which the devShell's own python3 does not
carry (see flake.nix: jazLangPython is a separate env on purpose, kept off
devPython/devShellPackages). tests/unit/99-jaz-armc.bats deliberately never
imports jaz for this reason (per the build task: "if a test needs jaz-lang
itself, keep it out of bats and put it in a pytest file run in the devShell
instead").

Run: `nix develop -c pytest tests/jaz -q`

Each test resolves an interpreter that DOES have jaz-lang installed (either
$JAZ_LANG_PYTHON, or `nix build .#jaz-lang-python` -- cached after the
first run) and runs the jaz-importing code as a SUBPROCESS under that
interpreter; this file's own test bodies (under plain pytest/devPython)
never import `jaz` or `claude_llm` directly. gateway.py itself is
stdlib-only and runs fine under devPython, with a fake `claude` on PATH --
never the real binary.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import textwrap
import time

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
JAZ_DIR = REPO_ROOT / "tools" / "experiments" / "jaz"

FAKE_CLAUDE_TEMPLATE = """#!/usr/bin/env bash
printf '%s\\n' "$@" >>"{argv_log}"
cat <<EOF
{{"type":"system","subtype":"init","cwd":".","session_id":"fake","apiKeySource":"none"}}
{{"type":"rate_limit_event","rate_limit_info":{{"status":"allowed","unifiedWindows":{{"five_hour":{{"utilization":0.05}},"seven_day":{{"utilization":0.2}}}}}}}}
{{"total_cost_usd":0.01,"usage":{{"input_tokens":10,"output_tokens":5,"cache_read_input_tokens":0,"cache_creation_input_tokens":100}},"result":"{reply}","type":"result"}}
EOF
"""


def _resolve_jaz_lang_python() -> str:
    override = os.environ.get("JAZ_LANG_PYTHON")
    if override:
        return override
    try:
        out = subprocess.run(
            [
                "nix",
                "build",
                f"{REPO_ROOT}#jaz-lang-python",
                "--no-link",
                "--print-out-paths",
            ],
            capture_output=True,
            text=True,
            timeout=1200,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"could not resolve jaz-lang-python via `nix build`: {exc}")
    path = out.stdout.strip().splitlines()[-1]
    return f"{path}/bin/python3"


@pytest.fixture(scope="module")
def jaz_python() -> str:
    return _resolve_jaz_lang_python()


def _write_fake_claude(
    bin_dir: pathlib.Path, argv_log: pathlib.Path, reply: str
) -> None:
    fake = bin_dir / "claude"
    fake.write_text(FAKE_CLAUDE_TEMPLATE.format(argv_log=argv_log, reply=reply))
    fake.chmod(0o755)


def _start_gateway(
    tmp_path: pathlib.Path, bin_dir: pathlib.Path, stop_at: float = 0.90
):
    socket_path = tmp_path / "gw.sock"
    log_path = tmp_path / "gw.jsonl"
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    proc = subprocess.Popen(
        [
            sys.executable,
            str(JAZ_DIR / "gateway.py"),
            "--socket",
            str(socket_path),
            "--log",
            str(log_path),
            "--stop-at-utilization",
            str(stop_at),
        ],
        env=env,
    )
    for _ in range(100):
        if socket_path.exists():
            break
        time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("gateway never created its socket")
    return proc, socket_path, log_path


def test_jaz_lang_imports_the_real_backend_contract(jaz_python: str) -> None:
    """Deliverable 1's own acceptance ("import-test jaz in the env"),
    repeated here against the exact classes claude_llm.py subclasses."""
    script = "from jaz.llm.llm import BaseLLM, LLMResponse; print(BaseLLM.__abstractmethods__)"
    result = subprocess.run(
        [jaz_python, "-c", script], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert "complete" in result.stdout


def test_claude_gateway_llm_complete_returns_a_real_llmresponse(
    tmp_path, jaz_python: str
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_log = tmp_path / "argv.log"
    _write_fake_claude(bin_dir, argv_log, reply="pong")

    proc, socket_path, _log_path = _start_gateway(tmp_path, bin_dir)
    try:
        script = textwrap.dedent(
            f"""
            import sys, json
            sys.path.insert(0, {str(JAZ_DIR)!r})
            from claude_llm import ClaudeGatewayLLM
            from jaz.llm.llm import LLMResponse

            llm = ClaudeGatewayLLM(socket_path={str(socket_path)!r}, model="claude-fable-5-1", effort="high")
            resp = llm.complete(
                "claude-fable-5-1",
                [
                    {{"role": "system", "content": "sys"}},
                    {{"role": "user", "content": "ping"}},
                ],
            )
            assert isinstance(resp, LLMResponse)
            info = llm.get_model_info()
            print(json.dumps({{
                "content": resp.content,
                "prompt_tokens": resp.prompt_tokens,
                "completion_tokens": resp.completion_tokens,
                "cached_tokens": resp.cached_tokens,
                "cost_usd": resp.cost_usd,
                "session_id": resp.extra.get("session_id"),
                "max_input_tokens": info.get("max_input_tokens"),
                "non_retryable_names": [c.__name__ for c in llm.non_retryable_exceptions],
            }}))
            """
        )
        result = subprocess.run(
            [jaz_python, "-c", script], capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        assert payload["content"] == "pong"
        assert payload["prompt_tokens"] == 10 + 0 + 100
        assert payload["completion_tokens"] == 5
        assert payload["cached_tokens"] == 0
        assert payload["cost_usd"] == 0.01
        # a dashed UUID (BLOCKER 1), not a bare .hex string
        assert "-" in payload["session_id"] and len(payload["session_id"]) == 36
        # ContextWindowWarning reads this; without the override it is None
        # for an internal model id like claude-fable-5-1 (see
        # claude_llm.py's module docstring).
        assert payload["max_input_tokens"] == 1_000_000
        assert "GatewayRefused" in payload["non_retryable_names"]
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_claude_gateway_llm_raises_gateway_refused_never_a_bare_runtimeerror(
    tmp_path, jaz_python: str
) -> None:
    """A refused/failed gateway call must raise GatewayRefused specifically
    (listed in non_retryable_exceptions), not a bare RuntimeError tenacity
    would retry up to 10x."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # apiKeySource != "none" -- the gateway aborts and reports ok:false.
    fake = bin_dir / "claude"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "cat >/dev/null\n"
        'echo \'{"type":"system","subtype":"init","cwd":".","session_id":"fake","apiKeySource":"config"}\'\n'
        "sleep 30\n"
    )
    fake.chmod(0o755)

    proc, socket_path, _log_path = _start_gateway(tmp_path, bin_dir)
    try:
        script = textwrap.dedent(
            f"""
            import sys
            sys.path.insert(0, {str(JAZ_DIR)!r})
            from claude_llm import ClaudeGatewayLLM, GatewayRefused

            llm = ClaudeGatewayLLM(socket_path={str(socket_path)!r}, model="claude-fable-5-1", effort="high")
            try:
                llm.complete("claude-fable-5-1", [{{"role": "user", "content": "hi"}}])
                print("NO_EXCEPTION_RAISED")
            except GatewayRefused as exc:
                print(f"GatewayRefused: {{exc}}")
            """
        )
        result = subprocess.run(
            [jaz_python, "-c", script], capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0, result.stderr
        assert "GatewayRefused:" in result.stdout
        assert "NO_EXCEPTION_RAISED" not in result.stdout
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_claude_gateway_llm_second_call_resumes_the_session(
    tmp_path, jaz_python: str
) -> None:
    """Two complete() calls with an appended message list: the first opens
    a session (--session-id/--system-prompt), the second resumes it
    (--resume) and sends only the new tail -- proving sessions.py and
    claude_llm.py agree end to end, not just in isolation."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_log = tmp_path / "argv.log"
    _write_fake_claude(bin_dir, argv_log, reply="first-reply")

    proc, socket_path, _log_path = _start_gateway(tmp_path, bin_dir)
    try:
        script = textwrap.dedent(
            f"""
            import sys, json
            sys.path.insert(0, {str(JAZ_DIR)!r})
            from claude_llm import ClaudeGatewayLLM

            llm = ClaudeGatewayLLM(socket_path={str(socket_path)!r}, model="claude-fable-5-1", effort="high")
            m1 = [
                {{"role": "system", "content": "sys"}},
                {{"role": "user", "content": "turn one"}},
            ]
            r1 = llm.complete("claude-fable-5-1", m1)
            m2 = m1 + [
                {{"role": "assistant", "content": r1.content}},
                {{"role": "user", "content": "turn two"}},
            ]
            r2 = llm.complete("claude-fable-5-1", m2)
            print(json.dumps({{
                "session_1": r1.extra["session_id"],
                "session_2": r2.extra["session_id"],
                "calls": len(llm.calls),
            }}))
            """
        )
        result = subprocess.run(
            [jaz_python, "-c", script], capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        assert payload["session_1"] == payload["session_2"]
        assert payload["calls"] == 2

        argv_lines = argv_log.read_text().splitlines()
        joined = "\n".join(argv_lines)
        assert "--session-id" in joined
        assert "--resume" in joined
    finally:
        proc.terminate()
        proc.wait(timeout=5)
