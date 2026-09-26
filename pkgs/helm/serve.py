"""Helm v1 control backend — the loopback server behind the switch.

Python 3 stdlib only (plan Task 1, amended by the consolidated decisions
D3/D8/D9/D10 and the Kimi copy deck K5/K12): a ThreadingHTTPServer that
serves the v0 page with the control sections injected at serve time,
answers /status.json from the live marker + journal, and executes exactly
two actions — `systemctl start helm-switch@<name>.service` (blocking,
under the held flock) and a detached `systemd-run --user … kgx -e
"<absolute helm_open_workspace_bin> <name>"`.

Security posture (every check fails closed):
  - Host allowlist on EVERY route, GET included (DNS-rebinding defense).
    Responses to a non-accepted Host are minimal pages that never carry
    the per-boot token — the point of the Host check is to not serve the
    token-bearing page to a rebound origin.
  - POSTs additionally need Sec-Fetch-Site: same-origin (or, when that
    header is absent, an accepted Origin), the per-boot token, and an
    allowlisted, regex-clean target. Nothing about a rejected request is
    ever executed.
  - Every POST needs the free switch lock; busy -> 409.
  - Forms only: no <script, no src=, no href="http in anything this module
    composes itself; the injected sections come from render.py (T1), which
    is held to the same invariant by its own tests.

Module state: APP (config, per-boot token, lock path) is set once by
main() before serving; tests set it directly. validate_post stays the
pure decision point — it reads nothing but its arguments and APP.cfg.

Cross-module contract with render.py (T1):
  render_control(status_html, control, state, token, banner=None) -> str
  render_banner(banner) -> str
  banner is {"kind": "ok" | "fail" | "busy", "text": str, "command": str?}
    (command: the copyable journalctl line, present on switch failures)
  state (read_state output, re-read per request, never cached):
    {
      "now": <iso serve time>,
      "active_profile": str,      # marker, "unknown" when unreadable
      "last_switch": {"from", "to", "result": "ok"|"fail", "at": iso} | None,
      "switching": {"from", "to", "started": iso} | None,
      "marker_error": str?,       # present when the marker read failed
      "journal_error": str?,      # present when journalctl failed
    }
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import html
import http.server
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys
import urllib.parse

import render

_TARGET_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
_BEGIN_RE = re.compile(r"^helm-switch: begin (\S+) -> (\S+) root=(\S+)$")
_END_RE = re.compile(r"^helm-switch: end (\S+) exit=(\d+)$")
_SETENV_VARS = ("WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS")
_MAX_FORM_BYTES = 64 * 1024
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_DEFAULT_LISTEN = "127.0.0.1:7700"
_DEFAULT_ALIASES = ["localhost", "127.0.0.1"]

# The boot-fresh fallback shell: the collector's first run may not have
# landed yet, but GET / must still render (with the live control sections
# injected). It keeps the v0 page's structure so the injection seam
# (before </main>) exists.
_FALLBACK_PAGE = (
    "<!doctype html>"
    '<html lang="en"><head><meta charset="utf-8">'
    '<meta http-equiv="refresh" content="60; url=/">'
    "<title>Helm</title></head><body>"
    "<header><h1>Helm</h1></header>"
    '<main class="grid"></main>'
    "</body></html>"
)

# Kimi copy deck (K15) — banner text is verbatim final copy.
_BUSY_TEXT = "A switch is already in progress. Wait for it to finish, then reload."

# Machine-readable reason -> the operator-facing wording. Flat, present
# tense, no exclamation marks (K15 tone rule).
_REASON_TEXT = {
    "bad-host": "this page was not reached through an accepted address",
    "foreign-origin": "the request came from another origin",
    "missing-headers": "the request carried no same-origin evidence",
    "cross-site": "the request was not same-origin",
    "bad-token": "the form token did not match this server",
    "target-not-allowed": "that target is not one of the allowed ones",
    "missing-form-key": "the form was incomplete",
}

ThreadingHTTPServer = http.server.ThreadingHTTPServer


class _App:
    """Process-wide server state, set by main() (or a test) before serving."""

    def __init__(self) -> None:
        self.cfg: dict = {}
        self.token: str = ""
        self.lock_file: str = ""


APP = _App()


def run(argv: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess:
    """The journalctl seam. Tests monkeypatch this.

    run_switch and spawn_open deliberately bypass it: their exact argv is
    the frozen contract under test, so they go through subprocess.run /
    subprocess.Popen directly.
    """
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def load_config(path) -> dict:
    """Read /etc/helm/config.json (the `control` section is written by the
    module, plan Task 3; load once at startup — the marker and journal are
    what move, and those are re-read per request)."""
    return json.loads(pathlib.Path(path).read_text())


def parse_listen(listen: str) -> tuple[str, int]:
    """'127.0.0.1:7700' -> ('127.0.0.1', 7700); '[::1]:7700' -> ('[::1]', 7700).

    The bracketed IPv6 form is preserved: that is the form a browser puts
    in the Host header (D9).
    """
    if listen.startswith("["):
        host, _, rest = listen.partition("]")
        if not rest.startswith(":"):
            raise ValueError(f"listen must be '[<v6>]:<port>', got {listen!r}")
        return host + "]", int(rest[1:])
    host, _, port = listen.rpartition(":")
    if not host or not port.isdigit():
        raise ValueError(f"listen must be '<host>:<port>', got {listen!r}")
    return host, int(port)


def accepted_hosts(cfg: dict) -> set[str]:
    """{alias:port} for every host alias, plus the bound address (D9: built
    from the parsed listen, IPv6 bracketed form preserved)."""
    control = cfg.get("control", {})
    host, port = parse_listen(control.get("listen", _DEFAULT_LISTEN))
    hosts = {f"{host}:{port}"}
    for alias in control.get("host_aliases", _DEFAULT_ALIASES):
        # An IPv6 alias must carry brackets to ever match a real Host header.
        if ":" in alias and not alias.startswith("["):
            alias = f"[{alias}]"
        hosts.add(f"{alias}:{port}")
    return hosts


def accepted_origins(cfg: dict) -> set[str]:
    """{'http://' + host} for every accepted host, brackets preserved."""
    return {f"http://{h}" for h in accepted_hosts(cfg)}


def validate_post(headers, form, token, allow, key):
    """The pure security decision point for every POST.

    Returns (0, "") when the request may run; (403|400, reason) otherwise,
    with a stable machine-readable reason token. Order: Host, then Origin,
    then Sec-Fetch-Site, then token, then target — a request failing several
    checks reports the first. Nothing about a rejected request is executed.
    """
    h = {str(k).lower(): str(v) for k, v in headers.items()}
    if h.get("host", "") not in accepted_hosts(APP.cfg):
        return (403, "bad-host")
    origin = h.get("origin")
    if origin is not None and origin not in accepted_origins(APP.cfg):
        # A foreign Origin is rejected even alongside Sec-Fetch-Site:
        # same-origin — a real browser never sends that combination, and
        # the forged pair must not pass.
        return (403, "foreign-origin")
    fetch_site = h.get("sec-fetch-site")
    if fetch_site is None:
        if origin is None:
            # Neither same-origin proof: reject outright.
            return (403, "missing-headers")
        # Origin accepted above: the legacy fallback (D5).
    elif fetch_site != "same-origin":
        return (403, "cross-site")
    if not secrets.compare_digest(
        str(form.get("token", "")).encode("utf-8", "replace"),
        str(token).encode("utf-8", "replace"),
    ):
        return (403, "bad-token")
    target = form.get(key)
    if not target:
        return (400, "missing-form-key")
    if not _TARGET_RE.match(target) or target not in allow:
        return (403, "target-not-allowed")
    return (0, "")


def run_switch(name: str) -> subprocess.CompletedProcess:
    """Start the allowlisted root unit and block for its result.

    The 360 s client timeout is deliberately longer than the unit's 300 s
    TimeoutStartSec (D8): a slow-but-legitimate switch must not surface as
    an HTTP error while the unit is still running.
    """
    return subprocess.run(
        ["systemctl", "start", f"helm-switch@{name}.service"],
        timeout=360,
        check=False,
    )


def spawn_open(name: str) -> None:
    """Open a terminal in the workspace, detached from this server (D3).

    systemd-run --user puts the terminal in the user manager — outside
    helm-serve's mount namespace, fully writable — instead of inheriting
    this unit's sandbox; --collect reaps the transient unit when it exits.
    The session variables are forwarded explicitly because a --user unit
    does not inherit the server's environment. kgx -e takes ONE command
    string, never command+args (D3.3).
    """
    argv = ["systemd-run", "--user", "--collect"]
    for var in _SETENV_VARS:
        value = os.environ.get(var)
        if value:
            argv.append(f"--setenv={var}={value}")
    # The launcher must be the absolute path from config: the terminal that
    # systemd-run --user spawns inherits the user manager's PATH, which
    # lacks /run/current-system/sw/bin, so the bare name would be "command
    # not found" and the window closes before claude starts (field bug
    # 2026-09-04). kgx_bin is absolute for the same reason.
    launcher = APP.cfg.get("control", {}).get(
        "helm_open_workspace_bin", "helm-open-workspace"
    )
    argv += [
        APP.cfg.get("control", {}).get("kgx_bin", "kgx"),
        "-e",
        f"{launcher} {name}",
    ]
    subprocess.Popen(argv, start_new_session=True)


@contextlib.contextmanager
def switch_lock(lock):
    """Hold the switch lock for the duration of the block (D8).

    flock is per open file description, so a second acquire — another
    thread, another process — fails with EWOULDBLOCK instead of blocking;
    the context manager yields False and the route answers 409. The fd
    closes on every exit path (crash included), which releases the kernel
    lock: the server can never deadlock on its own switch.
    """
    fd = os.open(str(lock), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _journal_switch_records():
    """(message, iso-ts) pairs for helm-switch@* journal records, in order."""
    cp = run(
        [
            "journalctl",
            "-b",
            "-u",
            "helm-switch@*",
            "-g",
            "^helm-switch: (begin|end) ",
            "-o",
            "json",
            "--no-pager",
            "-n",
            "200",
        ]
    )
    records: list[tuple[str, str]] = []
    if cp.returncode != 0:
        return records, (cp.stderr or "").strip()[-200:]
    for line in cp.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = rec.get("MESSAGE", "")
        if isinstance(msg, list):
            # journalctl JSON-encodes non-UTF-8 messages as codepoints.
            msg = "".join(chr(c) for c in msg if isinstance(c, int))
        ts = ""
        try:
            ts = datetime.datetime.fromtimestamp(
                float(rec.get("__REALTIME_TIMESTAMP")) / 1e6,
                tz=datetime.timezone.utc,
            ).isoformat()
        except (TypeError, ValueError, OSError, OverflowError):
            ts = ""
        records.append((str(msg), ts))
    return records, None


def read_state(control: dict) -> dict:
    """Re-read the marker and the journal. Called on EVERY request — nothing
    here is ever cached (D10: the active profile is the marker on disk, and
    a server restart mid-switch must not forget the in-flight switch; D8:
    the journal begin/end pair IS the in-flight state, no sidecar file).
    """
    state: dict = {
        "now": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active_profile": "unknown",
        "last_switch": None,
        "switching": None,
    }
    marker_path = control.get("marker")
    if marker_path:
        try:
            state["active_profile"] = pathlib.Path(marker_path).read_text().strip()
        except OSError as e:
            state["marker_error"] = f"{type(e).__name__}: {e}"
    else:
        state["marker_error"] = "no marker configured"

    records, journal_error = _journal_switch_records()
    if journal_error:
        state["journal_error"] = journal_error
    inflight = None
    last = None
    for msg, ts in records:
        begin = _BEGIN_RE.match(msg)
        if begin:
            inflight = {
                "from": begin.group(1),
                "to": begin.group(2),
                "started": ts,
            }
            continue
        end = _END_RE.match(msg)
        if end:
            to, code = end.group(1), int(end.group(2))
            src = inflight if inflight and inflight["to"] == to else None
            last = {
                "from": src["from"] if src else "unknown",
                "to": to,
                "result": "ok" if code == 0 else "fail",
                "at": ts,
            }
            if src:
                inflight = None
    state["last_switch"] = last
    state["switching"] = inflight
    return state


def _status_age(cfg: dict) -> tuple[float | None, int | None, datetime.datetime | None]:
    """Age of the collector's `<out_dir>/status.json`, from its `generated_at`.

    Returns `(age_seconds, interval_s, generated_dt)`; `(None, None, None)` on
    any error — the document missing (the collector has not landed this boot),
    malformed JSON, or a missing/unparsable field. Never a failure: until the
    collector's first run the page simply has no age banner (E5's fallback).
    """
    try:
        doc = json.loads(
            pathlib.Path(cfg.get("out_dir", "/var/lib/helm"), "status.json").read_text()
        )
        generated = datetime.datetime.fromisoformat(doc["generated_at"])
        interval = int(doc["interval_s"])
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=datetime.timezone.utc)
        age = (datetime.datetime.now(datetime.timezone.utc) - generated).total_seconds()
        return age, interval, generated
    except (OSError, KeyError, TypeError, ValueError):
        return None, None, None


def write_token_file(path, token: str) -> None:
    """Write the per-boot token 0600, atomically. The mode is set with
    fchmod so a restrictive umask (e.g. 0o077) can neither widen nor
    narrow it — same belt-and-braces as collect.write_atomic."""
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(token)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(str(tmp), str(p))


def _deny_banner(reason: str) -> dict:
    return {
        "kind": "fail",
        "text": f"Request rejected — {_REASON_TEXT.get(reason, reason)}.",
    }


def _audit(verb: str, target: str, result: str, host: str) -> None:
    """One journal line per action, to stderr (-> the journal under systemd).
    The result string carries both the HTTP outcome and the eventual unit
    result so a timeout stays observably distinct from a denial (D8)."""
    clean = " ".join(str(target).split()) or "-"
    peer = " ".join(str(host).split()) or "-"
    print(f"helm-serve: {verb} {clean} {result} from={peer}", file=sys.stderr)


class Handler(http.server.BaseHTTPRequestHandler):
    """GET / and /status.json; POST /action/switch and /action/open; else 404.

    The Host allowlist runs on every route. Responses to a non-accepted Host
    are minimal pages that never carry the token (the rebinding defense);
    every action response to a good Host is the FULL rendered page with a
    banner, whatever the outcome (K5) — never a bare status line.
    """

    timeout = 60

    def log_message(self, format, *args):
        # One audit line per ACTION (see _audit); no per-request noise.
        return

    # -- responses ---------------------------------------------------------

    def _send(self, code: int, body: str, ctype: str) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        # U2: the framed document *is* localhost:7700 and its form carries
        # the real token, so every CSRF layer (Host allowlist, foreign-Origin
        # rejection, Sec-Fetch-Site, per-boot token) passes inside a frame --
        # clickjacking is the remaining browser-side path, not the last path
        # to root. These headers refuse framing and caching on every response.
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.send_header("X-Frame-Options", "DENY")
        # `same-origin`, not `no-referrer`: under a no-referrer policy Firefox
        # sends `Origin: null` on same-origin form POSTs (the Fetch standard
        # governs the Origin header by the referrer policy for non-GET
        # requests), and validate_post refuses any Origin outside the accepted
        # set as foreign-origin — so the real-browser switch broke. same-origin
        # keeps referrers inside the origin AND leaves the Origin header intact.
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _plain(self, code: int, message: str) -> None:
        """Minimal page for the cases that must not leak the per-boot token:
        a non-accepted Host, unknown routes. Flat text, no forms."""
        safe = html.escape(message, quote=True)
        self._send(
            code,
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"<title>Helm</title></head><body><h1>Helm</h1><p>{safe}</p>"
            "</body></html>",
            "text/html; charset=utf-8",
        )

    def _page(self, banner: dict | None = None) -> str:
        control = APP.cfg.get("control", {})
        if banner is None:
            age, interval, generated_dt = _status_age(APP.cfg)
            if age is not None and interval and age > 2 * interval:
                banner = {
                    "kind": "fail",
                    "text": (
                        f"status tiles are {int(age // 60)} min old — the collector "
                        f"last ran at {generated_dt.astimezone().strftime('%H:%M %Z')}; "
                        "check systemctl --user status helm-collect.timer"
                    ),
                }
        try:
            status_html = pathlib.Path(
                APP.cfg.get("out_dir", "/var/lib/helm"), "index.html"
            ).read_text()
        except OSError:
            status_html = _FALLBACK_PAGE
        state = read_state(control)
        return render.render_control(
            status_html, control, state, APP.token, banner=banner
        )

    def _respond(self, code: int, banner: dict) -> None:
        self._send(code, self._page(banner), "text/html; charset=utf-8")

    def _deny(self, code: int, reason: str) -> None:
        if reason == "bad-host":
            # Never hand the token-bearing page to a rebinding attacker.
            self._plain(403, "not an accepted address")
        else:
            self._respond(code, _deny_banner(reason))

    # -- routes ------------------------------------------------------------

    def do_GET(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        host = self.headers.get("Host", "")
        if host not in accepted_hosts(APP.cfg):
            self._plain(403, "not an accepted address")
            return
        if path == "/":
            self._send(200, self._page(None), "text/html; charset=utf-8")
        elif path == "/control.json":
            state = read_state(APP.cfg.get("control", {}))
            self._send(
                200, json.dumps(state, indent=2, sort_keys=True), "application/json"
            )
        elif path == "/status.json":
            # The collector's document, verbatim: "status" now means one thing
            # for Helm Home (the collector), while /control.json is the serve-
            # time switch state. Before the collector's first run the file
            # does not exist, so the route answers 404 — never a synthetic doc.
            out_dir = APP.cfg.get("out_dir", "/var/lib/helm")
            try:
                doc = pathlib.Path(out_dir, "status.json").read_text()
            except OSError:
                self._plain(404, "no status document yet")
                return
            self._send(200, doc, "application/json")
        else:
            self._plain(404, "not found")

    def do_POST(self) -> None:
        path = urllib.parse.urlsplit(self.path).path
        host = self.headers.get("Host", "")
        if path not in ("/action/switch", "/action/open"):
            if host not in accepted_hosts(APP.cfg):
                self._plain(403, "not an accepted address")
            else:
                self._plain(404, "not found")
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            self._plain(400, "bad content-length")
            return
        if length > _MAX_FORM_BYTES:
            self._plain(400, "form too large")
            return
        raw = self.rfile.read(length) if length > 0 else b""
        form = {
            k: v[0]
            for k, v in urllib.parse.parse_qs(
                raw.decode("utf-8", "replace"), keep_blank_values=True
            ).items()
            if v
        }
        if path == "/action/switch":
            self._do_switch(form, host)
        else:
            self._do_open(form, host)

    def _do_switch(self, form: dict, host: str) -> None:
        control = APP.cfg.get("control", {})
        name = form.get("profile", "")
        code, reason = validate_post(
            dict(self.headers),
            form,
            APP.token,
            set(control.get("profiles", [])),
            "profile",
        )
        if code:
            self._deny(code, reason)
            _audit("switch", name, f"http={code} reason={reason}", host)
            return
        with switch_lock(APP.lock_file) as held:
            if not held:
                self._respond(409, {"kind": "busy", "text": _BUSY_TEXT})
                _audit("switch", name, "http=409 reason=busy", host)
                return
            unit = f"helm-switch@{name}.service"
            journal_cmd = f"journalctl -u {unit}"
            try:
                cp = run_switch(name)
            except subprocess.TimeoutExpired:
                banner = {
                    "kind": "fail",
                    "text": (
                        f"Switch to {name} did not finish within the timeout — "
                        f"it may still be running. Details: {journal_cmd}"
                    ),
                    "command": journal_cmd,
                }
                _audit("switch", name, "http=504 reason=timeout", host)
                self._respond(504, banner)
                return
            except OSError as e:
                banner = {
                    "kind": "fail",
                    "text": (
                        f"Switch to {name} could not be started: "
                        f"{type(e).__name__}. Details: {journal_cmd}"
                    ),
                    "command": journal_cmd,
                }
                _audit(
                    "switch", name, f"http=500 reason=spawn:{type(e).__name__}", host
                )
                self._respond(500, banner)
                return
            if cp.returncode == 0:
                http, banner, result = (
                    200,
                    {"kind": "ok", "text": f"Now running: {name}"},
                    "unit_exit=0",
                )
            else:
                state = read_state(control)
                active = state.get("active_profile", "unknown")
                banner = {
                    "kind": "fail",
                    "text": (
                        f"Switch to {name} did not finish — the machine is still "
                        f"on {active}. Details: {journal_cmd}"
                    ),
                    "command": journal_cmd,
                }
                http, result = 500, f"unit_exit={cp.returncode}"
            _audit("switch", name, f"http={http} {result}", host)
            self._respond(http, banner)

    def _do_open(self, form: dict, host: str) -> None:
        control = APP.cfg.get("control", {})
        name = form.get("flake", "")
        code, reason = validate_post(
            dict(self.headers),
            form,
            APP.token,
            set(control.get("workspaces", {})),
            "flake",
        )
        if code:
            self._deny(code, reason)
            _audit("open", name, f"http={code} reason={reason}", host)
            return
        with switch_lock(APP.lock_file) as held:
            if not held:
                # Every POST needs the free lock — an open during a
                # running switch waits with the switch's busy copy.
                self._respond(409, {"kind": "busy", "text": _BUSY_TEXT})
                _audit("open", name, "http=409 reason=busy", host)
                return
            spawn_open(name)
            _audit("open", name, "http=200", host)
            self._respond(
                200,
                {
                    "kind": "ok",
                    "text": (
                        f"Opening {name} — a terminal window should appear on "
                        "your desktop."
                    ),
                },
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="helm-serve")
    parser.add_argument("--config", default="/etc/helm/config.json")
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--lock-file", required=True)
    parser.add_argument("--listen", default=_DEFAULT_LISTEN)
    args = parser.parse_args(argv)

    host, port = parse_listen(args.listen)
    # Loopback-only, fail closed: Helm is a single-seat instrument (Phase
    # 10 is where LAN + auth arrive). Refused before any state is written.
    if host.strip("[]") not in _LOOPBACK_HOSTS:
        parser.error(
            f"--listen must be loopback (127.0.0.1 / [::1] / localhost), got {args.listen!r}"
        )

    cfg = load_config(args.config)
    token = secrets.token_hex(32)
    write_token_file(args.token_file, token)

    APP.cfg = cfg
    APP.token = token
    APP.lock_file = args.lock_file

    httpd = ThreadingHTTPServer((host.strip("[]"), port), Handler)
    print(f"helm-serve: serving on {args.listen}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
