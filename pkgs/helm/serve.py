"""Helm v1 control backend — the loopback server behind the (read-only) page.

Python 3 stdlib only. A ThreadingHTTPServer that serves the v0 page with the
read-only Profile section injected at serve time, answers /control.json from
the live marker + journal, and serves /status.json (the collector's document)
verbatim. D-H1 removed the actions: the switch now happens in Helm Home
behind the desktop password (polkit auth_admin_keep on the helm-switch@ start
verb), so this server no longer mints a per-boot token, holds a switch lock,
or runs `systemctl start` / `systemd-run`. Every POST is 405 read-only.

Security posture (every check fails closed):
  - Host allowlist on EVERY route, GET included (DNS-rebinding defense).
    Responses to a non-accepted Host are minimal pages — the point of the
    Host check is to not serve the switch state to a rebound origin.
  - Forms only gone: the page composes no <script, no src=, no href="http;
    the injected sections come from render.py (T1), held to the same
    invariant by its own tests.

Module state: APP (config) is set once by main() before serving; tests set
it directly. There is no token, no lock, no per-action state.

Cross-module contract with render.py (T1, D-H1):
  render_control(status_html, control, state, banner=None) -> str
  render_banner(banner) -> str
  banner is {"kind": "ok" | "fail", "text": str, "command": str?}
    (command: a copyable journalctl line, present on some banners)
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
import datetime
import html
import http.server
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse

import render

_BEGIN_RE = re.compile(r"^helm-switch: begin (\S+) -> (\S+) root=(\S+)$")
_END_RE = re.compile(r"^helm-switch: end (\S+) exit=(\d+)$")
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_DEFAULT_LISTEN = "127.0.0.1:7700"
_DEFAULT_ALIASES = ["localhost", "127.0.0.1"]

# The boot-fresh fallback shell: the collector's first run may not have
# landed yet, but GET / must still render (with the live Profile section
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

ThreadingHTTPServer = http.server.ThreadingHTTPServer


class _App:
    """Process-wide server state, set by main() (or a test) before serving."""

    def __init__(self) -> None:
        self.cfg: dict = {}


APP = _App()


def run(argv: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess:
    """The journalctl seam. Tests monkeypatch this."""
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
    from the parsed listen, IPv6 bracketed form preserved).

    HM7 also folds in the v2 API listen (`cfg["api"]["listen"]`) and its
    `localhost:<port>` alias: the same allowlist answers both ports, so a
    browser's `Host: 127.0.0.1:7710` on the API port is accepted rather than
    refused (the API listen is loopback-asserted, so this widens the loopback
    set only)."""
    control = cfg.get("control", {})
    host, port = parse_listen(control.get("listen", _DEFAULT_LISTEN))
    hosts = {f"{host}:{port}"}
    for alias in control.get("host_aliases", _DEFAULT_ALIASES):
        # An IPv6 alias must carry brackets to ever match a real Host header.
        if ":" in alias and not alias.startswith("["):
            alias = f"[{alias}]"
        hosts.add(f"{alias}:{port}")
    api = cfg.get("api", {})
    api_listen = api.get("listen")
    if api_listen:
        api_host, api_port = parse_listen(api_listen)
        hosts.add(f"{api_host}:{api_port}")
        hosts.add(f"localhost:{api_port}")
    return hosts


def accepted_origins(cfg: dict) -> set[str]:
    """{'http://' + host} for every accepted host, brackets preserved."""
    return {f"http://{h}" for h in accepted_hosts(cfg)}


def _journal_switch_records():
    """(message, iso-ts) pairs for helm-switch@* journal records, in
    chronological order (oldest first).

    journalctl --grep walks the journal newest-first, so the matching records
    arrive reverse-chronological; they are re-sorted by __REALTIME_TIMESTAMP
    here because read_state's begin/end state machine needs a begin before its
    end.
    """
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
    records: list[tuple[float, str, str]] = []
    if cp.returncode != 0:
        return [], (cp.stderr or "").strip()[-200:]
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
        when = 0.0
        ts = ""
        try:
            when = float(rec.get("__REALTIME_TIMESTAMP")) / 1e6
            ts = datetime.datetime.fromtimestamp(
                when, tz=datetime.timezone.utc
            ).isoformat()
        except (TypeError, ValueError, OSError, OverflowError):
            pass
        records.append((when, str(msg), ts))
    records.sort(key=lambda record: record[0])
    return [(msg, ts) for _, msg, ts in records], None


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


class Handler(http.server.BaseHTTPRequestHandler):
    """GET /, /control.json and /status.json; every POST is 405 read-only
    (403 on a non-accepted Host); any other GET is 404.

    The Host allowlist runs on every route. Responses to a non-accepted Host
    are minimal pages that never carry the switch state (the rebinding
    defense). D-H1: there is no form, no token, no action route.
    """

    timeout = 60

    def log_message(self, format, *args):
        # No per-request noise (the actions are gone; nothing to audit).
        return

    # -- responses ---------------------------------------------------------

    def _send(self, code: int, body: str, ctype: str, allow: str | None = None) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if allow is not None:
            self.send_header("Allow", allow)
        # The page is read-only now, but the framing defense stays: an
        # attacker must not embed the switch state on their origin.
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _plain(self, code: int, message: str) -> None:
        """Minimal page for a non-accepted Host and unknown routes. Flat
        text, no state, no forms."""
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
        return render.render_control(status_html, control, state, banner=banner)

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
        # D-H1: the page is read-only. The Host check runs first (a rebound
        # POST is a 403 minimal page, not the read-only reply); everything
        # else is 405 with a plain "read-only" body and an Allow: GET header.
        host = self.headers.get("Host", "")
        if host not in accepted_hosts(APP.cfg):
            self._plain(403, "not an accepted address")
            return
        self._send(405, "read-only", "text/plain; charset=utf-8", allow="GET")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="helm-serve")
    parser.add_argument("--config", default="/etc/helm/config.json")
    parser.add_argument("--listen", default=_DEFAULT_LISTEN)
    args = parser.parse_args(argv)

    host, port = parse_listen(args.listen)
    # Loopback-only, fail closed: Helm is a single-seat instrument (Phase
    # 10 is where LAN + auth arrive). Refused before any state is read.
    if host.strip("[]") not in _LOOPBACK_HOSTS:
        parser.error(
            f"--listen must be loopback (127.0.0.1 / [::1] / localhost), got {args.listen!r}"
        )

    APP.cfg = load_config(args.config)

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
