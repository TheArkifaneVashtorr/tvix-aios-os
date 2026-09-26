"""Helm v2 API server — the JSON state/action API on its own loopback port.

Python 3 stdlib only. A ThreadingHTTPServer that mounts route modules
(api_*.py, discovered at start) behind a discoverable route table and answers
JSON on every response. HM2 ships exactly one read-only route module
(api_state.py) and no action route: the Host/Origin allowlists are reused from
serve.py, and run() is the allowlisted subprocess seam later modules build on.

Security posture (every check fails closed):
  - Host allowlist on every route (DNS-rebinding defense) -> 400.
  - Origin allowlist when an Origin header is present -> 403.
  - A POST whose Content-Length is over 256 bytes is refused 413 before the
    body is read and before any handler runs.
  - Every response is application/json with X-Content-Type-Options: nosniff
    and Cache-Control: no-store, and never a Set-Cookie.

There is deliberately no action route here: the control port's page stays
read-only, and nothing in this module binds a host port (HM03 owns the system
unit and the option).
"""

from __future__ import annotations

import argparse
import http.server
import importlib
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass, field

from serve import accepted_hosts, accepted_origins, parse_listen

PROGRAMS = ("systemctl", "seat-submit", "git", "python3")
VERBS = ("start", "stop")
READ_VERBS = ("list-units", "show")
_SEAT_UNIT_RE = re.compile(r"^seat@[^/]+\.service$")
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_DEFAULT_LISTEN = "127.0.0.1:7710"
_CAPTURE_RE = re.compile(r"^<[^>]+>$")

# HM7: the home page (api_home) is the one HTML route; its
# Content-Security-Policy is set here at discover time when api_home registers
# its route. The HTML responder below reads this global.
HTML_CSP: str = ""

ThreadingHTTPServer = http.server.ThreadingHTTPServer


class _App:
    """Process-wide server state, set by main() (or a test) before serving."""

    def __init__(self) -> None:
        self.cfg: dict = {}


APP = _App()

_ROUTES: list[tuple[str, str, object]] = []
_ROUTE_KEYS: set[tuple[str, str]] = set()


@dataclass
class Request:
    """One parsed request, constructible without a socket (tests build these).

    ``headers`` carries lower-cased header names; ``params`` carries the path
    captures from the matched route pattern.
    """

    method: str
    path: str
    params: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    origin: str | None = None


def register(method: str, path_pattern: str, handler) -> None:
    """Add one route; two registrations of the same (method, pattern) refuse."""
    key = (method, path_pattern)
    if key in _ROUTE_KEYS:
        raise RuntimeError(f"duplicate route: {method} {path_pattern}")
    _ROUTE_KEYS.add(key)
    _ROUTES.append((method, path_pattern, handler))


def route_table() -> list[tuple[str, str, object]]:
    """The merged route table, what tests and HM10's contract read."""
    return list(_ROUTES)


def discover(directory: pathlib.Path | None = None) -> list[tuple[str, str, object]]:
    """Import every api_*.py beside this file and merge each module's routes().

    Two modules registering the same (method, path_pattern) raise RuntimeError.
    """
    if directory is None:
        directory = pathlib.Path(__file__).resolve().parent
    _ROUTES.clear()
    _ROUTE_KEYS.clear()
    for path in sorted(directory.glob("api_[a-z]*.py")):
        module = importlib.import_module(path.stem)
        for method, path_pattern, handler in module.routes():
            register(method, path_pattern, handler)
    return list(_ROUTES)


def match(pattern: str, path: str) -> dict[str, str] | None:
    """Match a /-separated literal-or-``<name>`` pattern against a path.

    A ``<name>`` segment captures exactly one non-empty, slash-free segment;
    segment counts must be equal. Returns the captures, or None on no match.
    """
    pattern_parts = pattern.split("/")
    path_parts = path.split("/")
    if len(pattern_parts) != len(path_parts):
        return None
    params: dict[str, str] = {}
    for p_part, q_part in zip(pattern_parts, path_parts):
        cap = _CAPTURE_RE.match(p_part)
        if cap:
            if not q_part:
                return None
            params[p_part[1:-1]] = q_part
        elif p_part != q_part:
            return None
    return params


def run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    """The allowlisted subprocess seam route modules call.

    Refuses any program outside PROGRAMS, and systemctl whose verb is neither
    start/stop on a seat@*.service unit nor a read verb in its restricted form
    (``list-units`` with ``--output=json``, ``show`` on a seat@*.service unit),
    before anything executes. Applies ``capture_output=True``, ``text=True``
    and ``timeout=APP.cfg["_timeout"]`` (default 10.0) unless the caller
    overrides them, then converts its own failures to a CompletedProcess with a
    non-zero returncode and the message in ``stderr`` — 126 refusal, 124
    timeout, 127 absent program — so a route reads returncode/stdout/stderr and
    never reaches ``subprocess``. The executor is ``APP.cfg["_run"]`` in tests
    and ``subprocess.run`` in production.
    """
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("timeout", APP.cfg.get("_timeout", 10.0))
    try:
        return _execute(argv, **kw)
    except PermissionError as exc:
        return subprocess.CompletedProcess(argv, 126, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            argv, 124, "", f"timed out after {exc.timeout}s"
        )
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", str(exc))


def _execute(argv: list[str], **kw):
    """The allowlist gate and executor dispatch behind ``run``; its permission
    refusals become ``run``'s returncode 126."""
    if not argv or argv[0] not in PROGRAMS:
        raise PermissionError(f"api.run refuses program {argv[0]!r}")
    if argv[0] == "systemctl":
        verb = argv[1] if len(argv) > 1 else ""
        unit = argv[2] if len(argv) > 2 else ""
        admitted = False
        if verb in VERBS:  # start/stop on a seat@*.service unit
            admitted = _SEAT_UNIT_RE.fullmatch(unit) is not None
        elif verb == "list-units":  # read: the --output=json argv only
            admitted = "--output=json" in argv
        elif verb == "show":  # read: a seat@*.service unit only
            admitted = _SEAT_UNIT_RE.fullmatch(unit) is not None
        if not admitted:
            raise PermissionError(f"api.run refuses systemctl {argv!r}")
    executor = APP.cfg.get("_run")
    if executor is None:
        executor = subprocess.run
    return executor(argv, **kw)


class Handler(http.server.BaseHTTPRequestHandler):
    """Dispatch GET/POST through the merged route table."""

    timeout = 60

    def log_message(self, format, *args):
        # No per-request noise; the host/origin and route decisions are the
        # audit surface, not the access log.
        return

    def _send_json(self, status: int, obj, allow: str | None = None) -> None:
        data = json.dumps(obj, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        if allow is not None:
            self.send_header("Allow", allow)
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, status: int, body: str) -> None:
        """The one non-JSON response: the home page (HM7). Same nosniff/
        no-store framing as JSON, plus the Content-Security-Policy the route
        module computed at discover time."""
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        if HTML_CSP:
            self.send_header("Content-Security-Policy", HTML_CSP)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        path = urllib.parse.urlsplit(self.path).path
        cfg = APP.cfg
        if self.headers.get("Host", "") not in accepted_hosts(cfg):
            self._send_json(400, {"error": "bad host"})
            return
        origin = self.headers.get("Origin")
        if origin is not None and origin not in accepted_origins(cfg):
            self._send_json(403, {"error": "bad origin"})
            return
        if method == "POST":
            length = self.headers.get("Content-Length")
            if length is not None:
                try:
                    if int(length) > 256:
                        self._send_json(413, {"error": "body"})
                        return
                except ValueError:
                    pass
        matched = []
        for m, pattern, handler in route_table():
            params = match(pattern, path)
            if params is not None:
                matched.append((m, handler, params))
        if not matched:
            self._send_json(404, {"error": "no such route"})
            return
        for m, handler, params in matched:
            if m == method:
                request = Request(
                    method=method,
                    path=path,
                    params=params,
                    headers={k.lower(): v for k, v in self.headers.items()},
                    body=b"",
                    origin=origin,
                )
                if method == "POST":
                    length = int(self.headers.get("Content-Length", "0") or "0")
                    if length:
                        request.body = self.rfile.read(length)
                try:
                    status, body = handler(cfg, request)
                except Exception as exc:  # noqa: BLE001 - no request goes unanswered
                    # Last resort: no request goes unanswered. A handler that
                    # returns is untouched; this only turns a raised exception
                    # into a 500 with the error body.
                    print(
                        f"helm-api: handler error: {type(exc).__name__}: {exc}",
                        file=sys.stderr,
                    )
                    status, body = 500, {"error": f"{type(exc).__name__}: {exc}"}
                if isinstance(body, str):
                    self._send_html(status, body)
                else:
                    self._send_json(status, body)
                return
        allowed = ", ".join(sorted({m for m, _, _ in matched}))
        self._send_json(405, {"error": "method not allowed"}, allow=allowed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="helm-api")
    parser.add_argument("--config", default="/etc/helm/config.json")
    parser.add_argument("--listen", default=_DEFAULT_LISTEN)
    args = parser.parse_args(argv)

    host, port = parse_listen(args.listen)
    # Loopback-only, fail closed: Helm is a single-seat instrument.
    if host.strip("[]") not in _LOOPBACK_HOSTS:
        parser.error(
            f"--listen must be loopback (127.0.0.1 / [::1] / localhost), got {args.listen!r}"
        )

    APP.cfg = json.loads(pathlib.Path(args.config).read_text())

    httpd = ThreadingHTTPServer((host.strip("[]"), port), Handler)
    print(f"helm-api: serving on {args.listen}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


discover()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
