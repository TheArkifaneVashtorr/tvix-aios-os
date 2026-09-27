#!/usr/bin/env python3
"""tools/experiments/jaz/gateway.py -- the ONLY process in arm C that holds
`claude`. A stdlib-only Unix-socket, JSON-lines server: run_arm_c.py's
sandboxed ClaudeGatewayLLM backend (claude_llm.py) connects to this socket
and never sees the subscription login or the `claude` binary itself.

Spec: docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md
§6b ("The gateway") and
docs/decisions/2026-09-27-claude-subscription-for-operator-launched-work.md
(the rules this process exists to satisfy: ANTHROPIC_API_KEY/
ANTHROPIC_AUTH_TOKEN unset, no `apiKeyHelper` configured, the login never
enters a sandboxed process, one call at a time, stop on the usage-limit
signal, every call logged).

Protocol: one connection per call. The client writes ONE JSON line (see
`main`'s docstring for the request/response shape) and the server writes
ONE JSON line back, then both sides close. Requests are processed strictly
one at a time -- `Server` below is a plain (non-threading)
`socketserver.UnixStreamServer`, so one call's `claude -p` subprocess
finishes before the next connection is even accepted (design §6b:
"Serial: one call at a time").

Request:  {"session_id": str, "first": bool, "system": str | None,
           "model": str, "effort": str, "message": str}
Response (ok):    {"ok": true, "text": str,
                    "usage": {"input": int|None, "output": int|None,
                              "cache_read": int|None, "cache_creation": int|None},
                    "cost_estimate": float | None,
                    "rate_limit": {"five_hour": float | None, "seven_day": float | None}}
Response (error): {"ok": false, "error": str}

2026-09-27 Opus review revisions:
  - the message goes over the subprocess's STDIN, never argv (a leading
    "-" in an argv-passed prompt is parsed as an option by some CLIs, and
    argv has an OS-level size limit -- E2BIG -- stdin has neither problem);
  - the system prompt is written to a file and passed via
    `--system-prompt-file` on EVERY call, first or resumed (the probe
    re-passed it on the resumed turn too);
  - each session gets ONE stable cwd, reused for every call on that
    session (the probe resumed `claude` from the same directory); a
    `--resume` naming a session this gateway never opened is refused
    rather than guessed at;
  - a per-call watchdog kills a hung `claude` on a timer, rather than
    relying on the unbounded `for line in proc.stdout` loop plus an
    uncaught `TimeoutExpired` from a bare `proc.wait(timeout=...)`;
  - the `result` event's own `is_error`/`subtype` is honored: an error
    result is reported as `{"ok": false, ...}`, never laundered into a
    successful model turn;
  - the child's environment is built from an ALLOWLIST (PATH, HOME, LANG/
    LC_*, TERM, XDG_*, TMPDIR, USER, SHELL), not a blocklist -- this is
    what actually keeps ANTHROPIC_*, CLAUDE_CONFIG_DIR, cloud-provider
    credential variables (AWS_*/GOOGLE_*, the Bedrock/Vertex routes) and
    OTEL_* out, rather than naming each one;
  - before the socket is even opened, the gateway refuses to start if
    `apiKeyHelper` is set in any Claude Code settings file it can read
    (`~/.claude/settings.json`, `~/.claude/settings.local.json`, the
    machine-wide `/etc/claude-code/managed-settings.json`) -- the per-call
    `apiKeySource` check from the init event is the second, redundant
    line of defense, not the only one;
  - a stop (utilisation at/above the threshold, or a non-"allowed" status
    that is not "allowed_warning") writes `<run>/stopped.json` (reason,
    the observed utilisation, and the session map) so the operator can
    see why a run halted and what to resume; `allowed_warning` is logged
    but never stops a run.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

DEFAULT_STOP_AT = 0.90
DEFAULT_CALL_TIMEOUT = 600.0
KILL_GRACE_SECONDS = 2.0

# Allowlist, not a blocklist (Opus review item 9): only these survive into
# the `claude` child's environment. Everything else -- ANTHROPIC_API_KEY/
# ANTHROPIC_AUTH_TOKEN, CLAUDE_CONFIG_DIR, AWS_*/GOOGLE_* (the Bedrock/
# Vertex routes LiteLLM-less `claude` itself still honors), OTEL_* -- is
# simply never copied, rather than named one at a time in an ever-growing
# strip list.
ENV_ALLOW_EXACT = {"PATH", "HOME", "LANG", "TERM", "TMPDIR", "USER", "SHELL"}
ENV_ALLOW_PREFIXES = ("LC_", "XDG_")

REQUIRED_FIELDS = ("session_id", "first", "model", "effort", "message")

# User/machine settings files that can carry `apiKeyHelper` -- checked once
# at startup (main), independent of the per-call `apiKeySource` check.
SETTINGS_FILES = (
    os.path.expanduser("~/.claude/settings.json"),
    os.path.expanduser("~/.claude/settings.local.json"),
    "/etc/claude-code/managed-settings.json",
)


def find_api_key_helper(paths: tuple[str, ...] = SETTINGS_FILES) -> str | None:
    """Return the first settings file that sets `apiKeyHelper`, or None.
    A missing or unparseable file is silently skipped -- absence is not a
    violation; only an explicit `apiKeyHelper` key is."""
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("apiKeyHelper"):
            return path
    return None


class GatewayState:
    def __init__(
        self,
        claude_bin: str,
        log_path: str,
        stop_at: float,
        run_tmp_base: str,
        call_timeout: float = DEFAULT_CALL_TIMEOUT,
        stopped_file: str | None = None,
    ) -> None:
        self.claude_bin = claude_bin
        self.log_path = log_path
        self.stop_at = stop_at
        self.run_tmp_base = run_tmp_base
        self.call_timeout = call_timeout
        self.stopped_file = stopped_file
        self.lock = threading.Lock()
        self.last_rate_limit: dict | None = None
        self.last_status = "allowed"
        # session_id -> its one stable cwd, so a --resume reuses the same
        # directory `claude` first ran in for that session (never
        # reused across sessions, never deleted until gateway shutdown).
        self.session_cwds: dict[str, str] = {}

    def refusal(self) -> str | None:
        """None if the next call may proceed; otherwise the refusal reason,
        checked BEFORE running a call, against the PREVIOUS call's observed
        signal (a call already in flight when the limit is crossed is not
        retroactively cancelled). `allowed_warning` is a status jaz-armc
        logs but never stops on -- only `allowed` proceeds silently and
        every OTHER status (including `allowed_warning`) stops, per the
        review's "stop only on seven_day >= 0.90 or a rejected status" read
        as "any status other than allowed is grounds to stop except the
        warning tier, which merely logs": treated here as: stop on
        anything that is not `allowed`/`allowed_warning`, OR on
        `allowed_warning` itself once utilisation has also crossed the
        threshold, OR on `allowed` once utilisation crosses the threshold.
        """
        if self.last_status not in ("allowed", "allowed_warning"):
            return f"gateway: last rate_limit_event status was {self.last_status!r}, refusing further calls"
        if self.last_rate_limit is not None:
            seven_day = self.last_rate_limit.get("seven_day")
            if seven_day is not None and seven_day >= self.stop_at:
                return (
                    f"gateway: seven_day utilisation {seven_day:.3f} >= stop threshold "
                    f"{self.stop_at:.3f}, refusing further calls"
                )
        return None

    def write_stopped_file(self, reason: str) -> None:
        if not self.stopped_file:
            return
        payload = {
            "ts": time.time(),
            "reason": reason,
            "last_status": self.last_status,
            "last_rate_limit": self.last_rate_limit,
            "sessions": sorted(self.session_cwds),
        }
        try:
            with open(self.stopped_file, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
        except OSError:
            pass


def build_argv(claude_bin: str, req: dict, system_prompt_file: str) -> list[str]:
    argv = [
        claude_bin,
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--tools",
        "",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--settings",
        json.dumps({"autoCompactEnabled": False}),
        "--model",
        req["model"],
        "--effort",
        req["effort"],
        "--system-prompt-file",
        system_prompt_file,
    ]
    if req.get("first"):
        argv += ["--session-id", req["session_id"]]
    else:
        argv += ["--resume", req["session_id"]]
    return argv


def scrubbed_env() -> dict:
    env = {}
    for key, value in os.environ.items():
        if key in ENV_ALLOW_EXACT or key.startswith(ENV_ALLOW_PREFIXES):
            env[key] = value
    return env


def _log(log_path: str, record: dict) -> None:
    record = dict(record)
    record.setdefault("ts", time.time())
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def run_claude_call(state: GatewayState, req: dict) -> dict:
    """Run one `claude -p` call, parse its stream-json lines, return the
    response dict. Never raises: every failure mode reports
    {"ok": False, "error": ...} instead."""
    refusal = state.refusal()
    if refusal is not None:
        _log(
            state.log_path,
            {
                "session_id": req.get("session_id"),
                "event": "refused",
                "reason": refusal,
            },
        )
        state.write_stopped_file(refusal)
        return {"ok": False, "error": refusal}

    session_id = req["session_id"]
    if req.get("first"):
        cwd = tempfile.mkdtemp(prefix="jaz-armc-session-", dir=state.run_tmp_base)
        state.session_cwds[session_id] = cwd
    else:
        cwd = state.session_cwds.get(session_id)
        if cwd is None:
            _log(
                state.log_path,
                {
                    "session_id": session_id,
                    "event": "unknown_resume",
                    "reason": "no cwd for this session_id",
                },
            )
            return {
                "ok": False,
                "error": f"gateway: --resume named session_id {session_id!r}, which this gateway never opened",
            }

    before = dict(state.last_rate_limit) if state.last_rate_limit else None
    system_prompt_file = os.path.join(cwd, "system-prompt.txt")
    with open(system_prompt_file, "w", encoding="utf-8") as fh:
        fh.write(req.get("system") or "")
    argv = build_argv(state.claude_bin, req, system_prompt_file)
    env = scrubbed_env()

    # stderr goes to a per-call FILE, not a pipe read after stdout closes:
    # a pipe fills its kernel buffer if claude writes enough to stderr
    # while this process is only draining stdout, which can stall claude
    # (and so this call) the same way an unread stdin pipe can -- a file
    # has no such limit, and its tail is read back below once the process
    # has actually exited.
    stderr_path = os.path.join(cwd, "stderr.log")
    stderr_fh = open(stderr_path, "w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_fh,
            text=True,
            # New session/process group (proc.pid becomes the pgid too):
            # `claude` (a node process) or, in tests, the fake's `sleep`
            # can leave a grandchild holding the stdout pipe's write end
            # open after the direct child is killed -- without this,
            # killing only `proc` never gets `for line in proc.stdout` to
            # EOF, and the call hangs until the CLIENT's own timeout fires
            # (a real bug, not the timing flake it first looked like --
            # see _terminate_process_group).
            start_new_session=True,
        )
    except OSError as exc:
        stderr_fh.close()
        _log(
            state.log_path,
            {"session_id": session_id, "event": "spawn_error", "error": str(exc)},
        )
        return {"ok": False, "error": f"gateway: could not run claude: {exc}"}

    # Written from a thread, concurrently with reading stdout below --
    # never synchronously before it. A message large enough to fill the
    # stdin pipe's kernel buffer, written synchronously before any stdout
    # is drained, can deadlock against a `claude` that starts emitting
    # output before it has fully consumed stdin (the classic
    # write-then-read subprocess pipe deadlock `Popen.communicate()`
    # exists to avoid).
    stdin_error: list[BaseException] = []

    def _write_stdin() -> None:
        try:
            proc.stdin.write(req["message"])
            proc.stdin.close()
        except (OSError, BrokenPipeError) as exc:
            stdin_error.append(exc)

    stdin_thread = threading.Thread(target=_write_stdin, daemon=True)
    stdin_thread.start()

    # A per-call watchdog: nothing else here bounds how long a hung
    # `claude` can block the (unbounded) `for line in proc.stdout` read
    # loop below, and a bare `proc.wait(timeout=...)` after that loop
    # would raise TimeoutExpired UNCAUGHT -- crashing this whole
    # long-running server process on one bad call.
    timed_out = threading.Event()
    timer = threading.Timer(
        state.call_timeout, _kill_on_timeout, args=(proc, timed_out)
    )
    timer.start()

    init_checked = False
    result_event = None
    rate_limit_info = None
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            etype = event.get("type")
            if (
                etype == "system"
                and event.get("subtype") == "init"
                and not init_checked
            ):
                init_checked = True
                api_key_source = event.get("apiKeySource")
                if api_key_source != "none":
                    _terminate_process_group(proc)
                    _log(
                        state.log_path,
                        {
                            "session_id": session_id,
                            "event": "aborted_api_key_source",
                            "apiKeySource": api_key_source,
                        },
                    )
                    return {
                        "ok": False,
                        "error": (
                            f"gateway: apiKeySource is {api_key_source!r}, expected 'none' "
                            "(an apiKeyHelper or API key is configured); aborted"
                        ),
                    }
            elif etype == "rate_limit_event":
                rate_limit_info = event.get("rate_limit_info")
            elif etype == "result":
                result_event = event
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _terminate_process_group(proc)
    finally:
        timer.cancel()
        stdin_thread.join(timeout=5)
        try:
            stderr_fh.close()
        except OSError:
            pass
        stderr_tail = ""
        try:
            with open(stderr_path, encoding="utf-8", errors="replace") as fh:
                stderr_tail = fh.read()
        except OSError:
            pass

    if stdin_error:
        _log(
            state.log_path,
            {
                "session_id": session_id,
                "event": "stdin_error",
                "error": str(stdin_error[0]),
            },
        )
        return {
            "ok": False,
            "error": f"gateway: could not write the message to claude's stdin: {stdin_error[0]}",
        }

    if timed_out.is_set():
        _log(
            state.log_path,
            {
                "session_id": session_id,
                "event": "call_timeout",
                "timeout_s": state.call_timeout,
            },
        )
        return {
            "ok": False,
            "error": f"gateway: claude exceeded the {state.call_timeout}s call timeout, killed",
        }

    if not init_checked:
        _log(
            state.log_path,
            {
                "session_id": session_id,
                "event": "no_init_event",
                "stderr": stderr_tail[-2000:],
            },
        )
        return {"ok": False, "error": "gateway: claude never emitted an init event"}

    if result_event is None:
        _log(
            state.log_path,
            {
                "session_id": session_id,
                "event": "no_result_event",
                "stderr": stderr_tail[-2000:],
            },
        )
        return {"ok": False, "error": "gateway: claude never emitted a result event"}

    if result_event.get("is_error") or result_event.get("subtype") not in (
        None,
        "success",
    ):
        _log(
            state.log_path,
            {
                "session_id": session_id,
                "event": "result_is_error",
                "subtype": result_event.get("subtype"),
                "is_error": result_event.get("is_error"),
                "result": result_event.get("result"),
            },
        )
        return {
            "ok": False,
            "error": (
                f"gateway: claude's result was an error (subtype={result_event.get('subtype')!r}, "
                f"is_error={result_event.get('is_error')!r}): {result_event.get('result')!r}"
            ),
        }

    usage = result_event.get("usage") or {}
    rate_limit = {"five_hour": None, "seven_day": None}
    status = "allowed"
    if rate_limit_info:
        status = rate_limit_info.get("status", "allowed")
        windows = rate_limit_info.get("unifiedWindows") or {}
        rate_limit["five_hour"] = (windows.get("five_hour") or {}).get("utilization")
        rate_limit["seven_day"] = (windows.get("seven_day") or {}).get("utilization")
        state.last_rate_limit = dict(rate_limit)
        state.last_status = status

    response = {
        "ok": True,
        "text": result_event.get("result") or "",
        "usage": {
            "input": usage.get("input_tokens"),
            "output": usage.get("output_tokens"),
            "cache_read": usage.get("cache_read_input_tokens"),
            "cache_creation": usage.get("cache_creation_input_tokens"),
        },
        "cost_estimate": result_event.get("total_cost_usd"),
        "rate_limit": rate_limit,
    }
    _log(
        state.log_path,
        {
            "session_id": session_id,
            "event": "call",
            "first": bool(req.get("first")),
            "model": req.get("model"),
            "effort": req.get("effort"),
            "usage": response["usage"],
            "cost_estimate": response["cost_estimate"],
            "rate_limit_before": before,
            "rate_limit_after": rate_limit,
            "status": status,
        },
    )
    if status == "allowed_warning":
        _log(
            state.log_path,
            {
                "session_id": session_id,
                "event": "allowed_warning",
                "rate_limit": rate_limit,
            },
        )
    return response


def _terminate_process_group(
    proc: subprocess.Popen, grace: float = KILL_GRACE_SECONDS
) -> None:
    """Kill `proc`'s WHOLE process group, not just the direct child --
    `claude` (a node process) can spawn children of its own, and (in
    tests) the fake's `sleep` runs as a plain, non-exec'd child of the
    fake's own bash: either way, a grandchild inherits and keeps holding
    the stdout pipe's write end open after `proc` itself dies, so `for
    line in proc.stdout` never reaches EOF and the call hangs until the
    far end (the gateway's own client) times out instead.

    Requires `start_new_session=True` at Popen time, which makes `proc`
    its own session/process-group leader -- `proc.pid` doubles as the
    process group id `os.killpg` needs. SIGTERM first; SIGKILL after
    `grace` seconds if the group is still alive. Safe to call from any
    thread; never raises."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            proc.terminate()
        except OSError:
            pass
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.05)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        try:
            proc.kill()
        except OSError:
            pass


def _kill_on_timeout(proc: subprocess.Popen, timed_out: threading.Event) -> None:
    timed_out.set()
    _terminate_process_group(proc)


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        line = self.rfile.readline()
        if not line:
            return
        try:
            req = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._respond({"ok": False, "error": f"gateway: bad request json: {exc}"})
            return
        missing = [k for k in REQUIRED_FIELDS if k not in req]
        if missing:
            self._respond(
                {"ok": False, "error": f"gateway: request missing fields {missing}"}
            )
            return
        response = run_claude_call(self.server.state, req)  # type: ignore[attr-defined]
        self._respond(response)

    def _respond(self, response: dict) -> None:
        self.wfile.write((json.dumps(response) + "\n").encode("utf-8"))


class Server(socketserver.UnixStreamServer):
    # Deliberately NOT socketserver.ThreadingMixIn: calls must be serial.
    allow_reuse_address = True

    def __init__(self, socket_path: str, state: GatewayState) -> None:
        if os.path.exists(socket_path):
            os.unlink(socket_path)
        super().__init__(socket_path, Handler)
        self.state = state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--socket", required=True, help="path of the Unix socket to listen on"
    )
    parser.add_argument("--log", required=True, help="JSONL log path (append)")
    parser.add_argument(
        "--claude-bin",
        default="claude",
        help="the claude executable (PATH-resolved by default)",
    )
    parser.add_argument("--stop-at-utilization", type=float, default=DEFAULT_STOP_AT)
    parser.add_argument("--call-timeout", type=float, default=DEFAULT_CALL_TIMEOUT)
    parser.add_argument(
        "--stopped-file",
        default=None,
        help="written (reason, utilisation, sessions) on any stop",
    )
    parser.add_argument(
        "--run-tmp-base",
        default=None,
        help="base dir for each session's stable cwd (default: a fresh tempdir)",
    )
    parser.add_argument(
        "--skip-api-key-helper-check",
        action="store_true",
        help="test-only: skip the startup apiKeyHelper preflight (never pass this for a real run)",
    )
    args = parser.parse_args(argv)

    if not args.skip_api_key_helper_check:
        offending = find_api_key_helper()
        if offending is not None:
            print(
                f"gateway: refusing to start: {offending} sets apiKeyHelper "
                "(this would let a call fall back to API billing); unset it first",
                file=sys.stderr,
            )
            return 1

    run_tmp_base = args.run_tmp_base or tempfile.mkdtemp(prefix="jaz-armc-gateway-")
    os.makedirs(run_tmp_base, exist_ok=True)
    state = GatewayState(
        args.claude_bin,
        args.log,
        args.stop_at_utilization,
        run_tmp_base,
        call_timeout=args.call_timeout,
        stopped_file=args.stopped_file,
    )
    server = Server(args.socket, state)
    print(f"gateway: listening on {args.socket}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        try:
            os.unlink(args.socket)
        except OSError:
            pass
        if not args.run_tmp_base:
            shutil.rmtree(run_tmp_base, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
