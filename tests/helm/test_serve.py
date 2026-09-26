"""Helm v1 control backend: the serve.py contract (plan Task 1 + D3/D8/D9/D10).

The matrix, per the task spec: the validate_post security table (Host
aliases + IPv6 + Fetch-Metadata/Origin fallback + token + allowlist +
regex), the exact subprocess argv of run_switch/spawn_open, the flock 409,
per-request state reads, route-level enforcement, the render.py integration
seam, and an end-to-end pass over a live ThreadingHTTPServer with
http.client (403/409/200, the fake runner called exactly once).

These tests never assert on render.py's OUTPUT -- T1's own tests own that
surface. The integration is pinned by monkeypatching render_control and
asserting what serve passes THROUGH it, so this file is green against
T1's red-phase stub and against the real renderer alike.
"""

import copy
import datetime as dt
import http.client
import importlib.util
import json
import os
import pathlib
import socket
import subprocess
import sys
import threading
import urllib.parse

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC_DIR = HERE.parents[2] / "pkgs" / "helm"
# serve.py does `import render` (T1) and runs with its own directory on
# sys.path -- the helm-serve wrapper gets that from
# `python3 <store-dir>/serve.py`; here we get it by inserting the directory
# before loading serve by path.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
_SPEC = importlib.util.spec_from_file_location("serve", SRC_DIR / "serve.py")
serve = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(serve)

# collect.py owns the meta-refresh string in production (render_html writes
# index.html); the collector-page half of the refresh test renders through
# it so a revert of collect.py alone fails that phase. Loaded by path like
# serve above, not via a package import.
_COLLECT_SPEC = importlib.util.spec_from_file_location(
    "collect", SRC_DIR / "collect.py"
)
collect = importlib.util.module_from_spec(_COLLECT_SPEC)
_COLLECT_SPEC.loader.exec_module(collect)

GOOD = {"Host": "localhost:7700", "Sec-Fetch-Site": "same-origin"}
ALLOW = {"base", "gaming"}

PAGE = (
    "<!doctype html>"
    '<html lang="en"><head><meta charset="utf-8">'
    '<meta http-equiv="refresh" content="60">'
    "<title>Helm</title></head><body>"
    "<header><h1>Helm · test</h1></header>"
    '<main class="grid"><section class="tile ok"><h2>gpu</h2></section></main>'
    "</body></html>"
)

BASE_CFG = {
    "operator_user": "alice",
    "interval_s": 300,
    "out_dir": "/var/lib/helm",
    "control": {
        # D1: a fixed literal. "media" is round 2 and stays out.
        "profiles": ["base", "gaming"],
        "workspaces": {
            "gaming": {
                "path": "/home/x/flakes/gaming",
                "devShell": "default",
                "basket": None,
            },
            "strategy": {
                "path": "/home/x/strategy",
                "devShell": None,
                "basket": None,
            },
        },
        "host_aliases": ["localhost", "127.0.0.1"],
        "listen": "127.0.0.1:7700",
        "marker": "/etc/helm/profile",
        "kgx_bin": "/run/current-system/sw/bin/kgx",
        "helm_open_workspace_bin": "/run/current-system/sw/bin/helm-open-workspace",
    },
}


@pytest.fixture(autouse=True)
def app(tmp_path, monkeypatch):
    """Every test gets a configured APP: a tmp out_dir and marker, a token,
    and an empty journal seam so no test ever runs a real journalctl."""
    cfg = copy.deepcopy(BASE_CFG)
    cfg["out_dir"] = str(tmp_path)
    cfg["control"]["marker"] = str(tmp_path / "profile")
    (tmp_path / "profile").write_text("base\n")
    (tmp_path / "index.html").write_text(PAGE)
    monkeypatch.setattr(serve.APP, "cfg", cfg)
    monkeypatch.setattr(serve.APP, "token", "t")
    monkeypatch.setattr(serve.APP, "lock_file", str(tmp_path / "switch.lock"))
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(argv, 0, "", ""),
    )
    return serve.APP


def journal(*messages, t0=1_000_000_000.0):
    """journalctl -o json output, one record per message, 1 s apart."""
    lines = [
        json.dumps(
            {
                "MESSAGE": msg,
                "_SYSTEMD_UNIT": "helm-switch@x.service",
                "__REALTIME_TIMESTAMP": str(int((t0 + i) * 1e6)),
            }
        )
        for i, msg in enumerate(messages)
    ]
    return "\n".join(lines) + "\n"


def iso(t):
    return dt.datetime.fromtimestamp(t, tz=dt.timezone.utc).isoformat()


class Server:
    """A live Handler on an ephemeral loopback port, in a thread."""

    def __init__(self):
        self.httpd = serve.ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


def http_response(port, method, path, headers, form=None):
    """One live request: (status, response headers, body)."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    body = None
    headers = dict(headers)
    if form is not None:
        body = urllib.parse.urlencode(form)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    conn.request(method, path, body=body, headers=headers)
    resp = conn.getresponse()
    resp_headers = dict(resp.getheaders())
    data = resp.read()
    conn.close()
    return resp.status, resp_headers, data


def http_request(port, method, path, headers, form=None):
    status, _, data = http_response(port, method, path, headers, form)
    return status, data


def post_action(port, path, headers, form):
    return http_request(port, "POST", path, headers, form)


def raw_request(port, text: bytes) -> bytes:
    """A raw socket round-trip for the body guards: send bytes verbatim and
    read until EOF. Bypasses http.client so a malformed Content-Length (or a
    huge one) reaches the server exactly as a non-conforming client sends it."""
    with socket.create_connection(("127.0.0.1", port), timeout=5) as s:
        s.sendall(text)
        s.shutdown(socket.SHUT_WR)
        out = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            out += chunk
    return out


# ---------------------------------------------------------------------------
# U2/U3 review fixes: anti-framing headers, a refresh that targets "/",
# and the open argv asserted against the configured path
# ---------------------------------------------------------------------------


def test_send_carries_anti_framing_headers():
    # U2: every response -- a 200 page and a denial page alike -- must
    # refuse framing and caching. The framed document *is* localhost:7700
    # and its form carries the real token, so every CSRF layer (Host
    # allowlist, foreign-Origin rejection, Sec-Fetch-Site, per-boot token)
    # passes inside a frame -- clickjacking is the remaining browser-side
    # path, not the last path to root.
    with Server() as srv:
        _, ok_hdrs, _ = http_response(srv.port, "GET", "/", GOOD)
        _, deny_hdrs, _ = http_response(
            srv.port,
            "POST",
            "/action/switch",
            GOOD,
            {"profile": "gaming", "token": "wrong"},
        )
    for hdrs in (ok_hdrs, deny_hdrs):
        assert hdrs.get("Content-Security-Policy") == "frame-ancestors 'none'"
        assert hdrs.get("X-Frame-Options") == "DENY"
        assert hdrs.get("Referrer-Policy") == "same-origin"
        assert hdrs.get("Cache-Control") == "no-store"
        assert hdrs.get("X-Content-Type-Options") == "nosniff"


def test_action_response_refresh_has_a_target(tmp_path):
    # U2: an action response is the FULL page (K5), whose meta refresh must
    # target "/" -- a bare content="60" refreshes to the action URL, which
    # do_GET 404s, so the operator lands on a bare "not found" after a
    # minute. Both the collector page and the boot-fresh fallback carry the
    # target.
    # The collector-page half renders through collect.render_html -- the real
    # producer of the refresh string -- not the PAGE fixture (which is
    # deliberately bare content="60" and must not supply the asserted value).
    # Reverting collect.py to a bare content="60" therefore fails this phase.
    collector_status = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "hostname": "core",
        "interval_s": 300,
        "tiles": [],
    }
    (tmp_path / "index.html").write_text(
        collect.render_html(collector_status, dt.datetime.now(dt.timezone.utc))
    )
    with Server() as srv:
        status, body = post_action(
            srv.port, "/action/switch", GOOD, {"profile": "gaming", "token": "wrong"}
        )
    assert status == 403
    assert '<meta http-equiv="refresh" content="60; url=/"' in body.decode()
    # Boot-fresh: no index.html yet -> _FALLBACK_PAGE is the status page.
    (tmp_path / "index.html").unlink()
    with Server() as srv:
        status, body = post_action(
            srv.port, "/action/switch", GOOD, {"profile": "gaming", "token": "wrong"}
        )
    assert status == 403
    assert '<meta http-equiv="refresh" content="60; url=/"' in body.decode()


def test_open_argv_matches_the_configured_path(monkeypatch):
    # U3's surviving kernel: the open argv must come from the config the
    # server was fed, not a literal -- a literal and the config were free
    # to diverge (and did: the unit test pinned a bare name while the
    # module pinned the absolute path).
    cfg = copy.deepcopy(BASE_CFG)
    # A value distinct from BASE_CFG's default proves the assertion tracks
    # the config, not a hardcoded path.
    cfg["control"]["helm_open_workspace_bin"] = "/configured/helm-open-workspace"
    monkeypatch.setattr(serve.APP, "cfg", cfg)
    for var in ("WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
        monkeypatch.delenv(var, raising=False)
    seen = {}

    def fake_popen(argv, **kw):
        seen["argv"] = argv

    monkeypatch.setattr(serve.subprocess, "Popen", fake_popen)
    serve.spawn_open("gaming")
    control = cfg["control"]
    assert seen["argv"] == [
        "systemd-run",
        "--user",
        "--collect",
        control["kgx_bin"],
        "-e",
        f"{control['helm_open_workspace_bin']} gaming",
    ]


# ---------------------------------------------------------------------------
# validate_post: the security table
# ---------------------------------------------------------------------------


def test_validate_happy():
    assert serve.validate_post(
        GOOD, {"profile": "gaming", "token": "t"}, "t", ALLOW, "profile"
    ) == (0, "")


def test_validate_rejects_wrong_host():
    code, _ = serve.validate_post(
        {"Host": "evil.example:7700", "Sec-Fetch-Site": "same-origin"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    )
    assert code == 403


def test_validate_accepts_ip_host_alias():
    assert serve.validate_post(
        {"Host": "127.0.0.1:7700", "Sec-Fetch-Site": "same-origin"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    ) == (0, "")


def test_validate_rejects_cross_site():
    code, _ = serve.validate_post(
        {"Host": "localhost:7700", "Sec-Fetch-Site": "cross-site"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    )
    assert code == 403


def test_validate_origin_fallback():
    # Origin accepted when Sec-Fetch-Site is absent (legacy browsers, D5)...
    assert serve.validate_post(
        {"Host": "localhost:7700", "Origin": "http://localhost:7700"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    ) == (0, "")
    # ...a foreign Origin is rejected...
    code, _ = serve.validate_post(
        {"Host": "localhost:7700", "Origin": "http://evil.example"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    )
    assert code == 403
    # ...and neither header is rejected outright.
    code, _ = serve.validate_post(
        {"Host": "localhost:7700"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    )
    assert code == 403


def test_validate_rejects_null_origin_as_foreign():
    # H3: Referrer-Policy: no-referrer made Firefox send `Origin: null` on
    # same-origin form POSTs (the Fetch standard governs the Origin header
    # by the referrer policy for non-GET requests), and validate_post
    # deliberately rejects any Origin outside the accepted set — so the
    # switch failed with reason=foreign-origin even though the browser was
    # genuinely same-origin. The fix is the `same-origin` policy (which
    # keeps the Origin header intact); it is NOT to accept `Origin: null`.
    # `null` must stay refused under both shapes a browser could emit it.
    assert serve.validate_post(
        {"Host": "localhost:7700", "Origin": "null", "Sec-Fetch-Site": "same-origin"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    ) == (403, "foreign-origin")
    assert serve.validate_post(
        {"Host": "localhost:7700", "Origin": "null"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    ) == (403, "foreign-origin")


def test_validate_rejects_bad_token_and_unknown_target():
    code, _ = serve.validate_post(
        GOOD, {"profile": "gaming", "token": "x"}, "t", ALLOW, "profile"
    )
    assert code == 403
    code, _ = serve.validate_post(
        GOOD, {"profile": "nope", "token": "t"}, "t", ALLOW, "profile"
    )
    assert code == 403
    code, _ = serve.validate_post(
        GOOD, {"profile": "../x", "token": "t"}, "t", ALLOW, "profile"
    )
    assert code == 403


def test_validate_same_origin_site_with_foreign_origin_is_403():
    # Defense in depth: a real browser never sends Sec-Fetch-Site:
    # same-origin together with a foreign Origin; the forged combination
    # must not pass.
    code, _ = serve.validate_post(
        {
            "Host": "localhost:7700",
            "Sec-Fetch-Site": "same-origin",
            "Origin": "http://evil.example",
        },
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    )
    assert code == 403


def test_validate_missing_form_key_is_400():
    code, reason = serve.validate_post(GOOD, {"token": "t"}, "t", ALLOW, "profile")
    assert code == 400
    assert reason


def test_validate_headers_are_case_insensitive():
    assert serve.validate_post(
        {"host": "localhost:7700", "sec-fetch-site": "same-origin"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    ) == (0, "")


def test_validate_rejects_missing_token_field():
    code, _ = serve.validate_post(GOOD, {"profile": "gaming"}, "t", ALLOW, "profile")
    assert code == 403


# ---------------------------------------------------------------------------
# accepted hosts / origins (D9: parsed listen, IPv6 brackets preserved)
# ---------------------------------------------------------------------------


def test_parse_listen_forms():
    assert serve.parse_listen("127.0.0.1:7700") == ("127.0.0.1", 7700)
    assert serve.parse_listen("[::1]:7700") == ("[::1]", 7700)


def test_accepted_hosts_aliases_and_bound():
    assert serve.accepted_hosts(BASE_CFG) == {"localhost:7700", "127.0.0.1:7700"}
    assert serve.accepted_origins(BASE_CFG) == {
        "http://localhost:7700",
        "http://127.0.0.1:7700",
    }


def test_accepted_hosts_ipv6_bracketed():
    cfg = copy.deepcopy(BASE_CFG)
    cfg["control"]["listen"] = "[::1]:7700"
    cfg["control"]["host_aliases"] = ["localhost", "127.0.0.1", "::1"]
    hosts = serve.accepted_hosts(cfg)
    # The bound address keeps its bracketed form (D9) and an IPv6 alias is
    # bracketed too -- that is the form a browser puts in Host/Origin.
    assert hosts == {"[::1]:7700", "localhost:7700", "127.0.0.1:7700"}
    assert serve.accepted_origins(cfg) == {
        "http://[::1]:7700",
        "http://localhost:7700",
        "http://127.0.0.1:7700",
    }


def test_validate_accepts_ipv6_bound_host(monkeypatch):
    cfg = copy.deepcopy(BASE_CFG)
    cfg["control"]["listen"] = "[::1]:7700"
    cfg["control"]["host_aliases"] = ["::1"]
    monkeypatch.setattr(serve.APP, "cfg", cfg)
    assert serve.validate_post(
        {"Host": "[::1]:7700", "Sec-Fetch-Site": "same-origin"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    ) == (0, "")
    # localhost is no longer aliased in this config: it must now 403,
    # proving the host set comes from the app config, not a hardcoded list.
    code, _ = serve.validate_post(
        {"Host": "localhost:7700", "Sec-Fetch-Site": "same-origin"},
        {"profile": "gaming", "token": "t"},
        "t",
        ALLOW,
        "profile",
    )
    assert code == 403


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


def test_load_config_reads_json(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(BASE_CFG))
    assert serve.load_config(p) == BASE_CFG


# ---------------------------------------------------------------------------
# run_switch / spawn_open: exact argv
# ---------------------------------------------------------------------------


def test_switch_calls_systemctl_exactly(monkeypatch):
    seen = {}

    def fake_run(argv, **kw):
        seen["argv"] = argv
        seen["kw"] = kw
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(serve.subprocess, "run", fake_run)
    cp = serve.run_switch("gaming")
    assert seen.get("argv") == ["systemctl", "start", "helm-switch@gaming.service"]
    # D8: the client timeout (360 s) is deliberately longer than the unit's
    # TimeoutStartSec (300 s) -- a slow-but-legitimate switch must not
    # surface as an HTTP error while the unit is still running.
    assert seen.get("kw", {}).get("timeout") == 360
    assert cp.returncode == 0


def test_spawn_open_argv_exact(monkeypatch):
    for var in ("WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
    seen = {}

    def fake_popen(argv, **kw):
        seen["argv"] = argv
        seen["kw"] = kw

    monkeypatch.setattr(serve.subprocess, "Popen", fake_popen)
    serve.spawn_open("gaming")
    # D3: systemd-run --user (the terminal escapes the sandbox); the session
    # variables forwarded explicitly; the absolute kgx_bin; kgx -e takes
    # ONE command string, never command+args.
    assert seen.get("argv") == [
        "systemd-run",
        "--user",
        "--collect",
        "--setenv=WAYLAND_DISPLAY=wayland-0",
        "--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus",
        "/run/current-system/sw/bin/kgx",
        "-e",
        "/run/current-system/sw/bin/helm-open-workspace gaming",
    ]
    assert seen.get("kw", {}).get("start_new_session") is True


def test_spawn_open_omits_absent_session_vars(monkeypatch):
    for var in ("WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
        monkeypatch.delenv(var, raising=False)
    seen = {}

    def fake_popen(argv, **kw):
        seen["argv"] = argv

    monkeypatch.setattr(serve.subprocess, "Popen", fake_popen)
    serve.spawn_open("strategy")
    assert seen.get("argv") == [
        "systemd-run",
        "--user",
        "--collect",
        "/run/current-system/sw/bin/kgx",
        "-e",
        "/run/current-system/sw/bin/helm-open-workspace strategy",
    ]


# ---------------------------------------------------------------------------
# switch_lock: the held flock
# ---------------------------------------------------------------------------


def test_lock_gives_409_on_reentry(tmp_path):
    lock = tmp_path / "l"
    with serve.switch_lock(lock) as ok:
        assert ok
        with serve.switch_lock(lock) as ok2:
            assert not ok2


def test_lock_released_after_block(tmp_path):
    lock = tmp_path / "l"
    with serve.switch_lock(lock):
        pass
    with serve.switch_lock(lock) as ok:
        assert ok


def test_lock_self_releases_on_crash(tmp_path):
    # Crash => unlock, never deadlock (D8): the fd closes on every exit
    # path, and flock locks live on the open file description.
    lock = tmp_path / "l"
    with pytest.raises(RuntimeError), serve.switch_lock(lock):
        raise RuntimeError("crash mid-switch")
    with serve.switch_lock(lock) as ok:
        assert ok


# ---------------------------------------------------------------------------
# read_state: marker + journal, re-read every request
# ---------------------------------------------------------------------------


def test_read_state_marker(tmp_path):
    control = {"marker": str(tmp_path / "profile")}
    state = serve.read_state(control)
    assert state["active_profile"] == "base"
    (tmp_path / "profile").write_text("gaming\n")
    state = serve.read_state(control)
    assert state["active_profile"] == "gaming"


def test_read_state_missing_marker_is_unknown():
    state = serve.read_state({"marker": "/nonexistent/profile"})
    assert state["active_profile"] == "unknown"
    assert state.get("marker_error")


def test_read_state_last_switch_from_begin_end_pairs(monkeypatch, tmp_path):
    control = {"marker": str(tmp_path / "profile")}
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(
            argv,
            0,
            journal(
                "helm-switch: begin base -> gaming root=/run/booted-system",
                "helm-switch: end gaming exit=0",
            ),
            "",
        ),
    )
    state = serve.read_state(control)
    assert state["last_switch"] == {
        "from": "base",
        "to": "gaming",
        "result": "ok",
        "at": iso(1_000_000_001),
    }
    assert state["switching"] is None


def test_read_state_failed_switch_is_fail(monkeypatch, tmp_path):
    control = {"marker": str(tmp_path / "profile")}
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(
            argv,
            0,
            journal(
                "helm-switch: begin base -> gaming root=/run/booted-system",
                "helm-switch: end gaming exit=1",
            ),
            "",
        ),
    )
    state = serve.read_state(control)
    assert state["last_switch"]["result"] == "fail"
    assert state["last_switch"]["to"] == "gaming"


def test_read_state_inflight_begin_is_switching(monkeypatch, tmp_path):
    control = {"marker": str(tmp_path / "profile")}
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(
            argv,
            0,
            journal("helm-switch: begin base -> gaming root=/run/booted-system"),
            "",
        ),
    )
    state = serve.read_state(control)
    assert state["switching"] == {
        "from": "base",
        "to": "gaming",
        "started": iso(1_000_000_000),
    }
    assert state["last_switch"] is None


def test_read_state_end_without_begin_leaves_from_unknown(monkeypatch, tmp_path):
    control = {"marker": str(tmp_path / "profile")}
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(
            argv,
            0,
            journal("helm-switch: end gaming exit=0"),
            "",
        ),
    )
    state = serve.read_state(control)
    assert state["last_switch"]["from"] == "unknown"
    assert state["switching"] is None


def test_read_state_journalctl_failure_degrades(monkeypatch, tmp_path):
    control = {"marker": str(tmp_path / "profile")}
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(
            argv, 1, "", "no journal"
        ),
    )
    state = serve.read_state(control)
    assert state["last_switch"] is None
    assert state["switching"] is None
    assert state["active_profile"] == "base"
    assert state.get("journal_error")


def test_read_state_ignores_unparsable_journal_lines(monkeypatch, tmp_path):
    control = {"marker": str(tmp_path / "profile")}
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(
            argv,
            0,
            "not json\n"
            + journal(
                "helm-switch: begin base -> gaming root=/r",
                "helm-switch: end gaming exit=0",
            ),
            "",
        ),
    )
    state = serve.read_state(control)
    assert state["last_switch"]["to"] == "gaming"


def test_read_state_rereads_marker_and_journal_every_call(monkeypatch, tmp_path):
    # D10: nothing here may be cached -- a fresh read sees a new marker and
    # a closed begin/end pair on the very next call.
    marker = tmp_path / "profile"
    marker.write_text("base\n")
    control = {"marker": str(marker)}
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(
            argv,
            0,
            journal("helm-switch: begin base -> gaming root=/r"),
            "",
        ),
    )
    s1 = serve.read_state(control)
    assert s1["active_profile"] == "base"
    assert s1["switching"]["to"] == "gaming"
    marker.write_text("gaming\n")
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(
            argv,
            0,
            journal(
                "helm-switch: begin base -> gaming root=/r",
                "helm-switch: end gaming exit=0",
            ),
            "",
        ),
    )
    s2 = serve.read_state(control)
    assert s2["active_profile"] == "gaming"
    assert s2["switching"] is None
    assert s2["last_switch"]["to"] == "gaming"


# ---------------------------------------------------------------------------
# render.py integration (what serve passes through; T1 owns the output)
# ---------------------------------------------------------------------------


def _capture_render(monkeypatch):
    calls = {}

    def fake_render_control(status_html, control, state, token, banner=None):
        calls["status_html"] = status_html
        calls["control"] = control
        calls["state"] = state
        calls["token"] = token
        calls["banner"] = banner
        return "<html>RENDERED</html>"

    monkeypatch.setattr(serve.render, "render_control", fake_render_control)
    return calls


def test_get_root_flows_through_render(monkeypatch):
    calls = _capture_render(monkeypatch)
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/", GOOD)
    assert status == 200
    assert body == b"<html>RENDERED</html>"
    assert calls.get("status_html") == PAGE
    assert calls.get("token") == "t"
    assert calls.get("banner") is None
    assert calls.get("control") == serve.APP.cfg["control"]
    assert calls.get("state", {}).get("active_profile") == "base"


def test_get_root_survives_missing_index_html(monkeypatch, tmp_path):
    # Boot-fresh system: the collector has not landed yet; the page still
    # renders (with a fallback shell), it does not 500.
    calls = _capture_render(monkeypatch)
    (tmp_path / "index.html").unlink()
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/", GOOD)
    assert status == 200
    assert body == b"<html>RENDERED</html>"
    assert "</main>" in calls.get("status_html", "")


def test_switch_success_passes_banner_to_render(monkeypatch):
    calls = _capture_render(monkeypatch)
    monkeypatch.setattr(
        serve,
        "run_switch",
        lambda name: subprocess.CompletedProcess(
            ["systemctl", "start", name], 0, "", ""
        ),
    )
    with Server() as srv:
        status, _ = post_action(
            srv.port, "/action/switch", GOOD, {"profile": "gaming", "token": "t"}
        )
    assert status == 200
    assert calls.get("banner") == {"kind": "ok", "text": "Now running: gaming"}


def test_switch_failure_passes_fail_banner_to_render(monkeypatch):
    calls = _capture_render(monkeypatch)
    monkeypatch.setattr(
        serve,
        "run_switch",
        lambda name: subprocess.CompletedProcess(
            ["systemctl", "start", name], 3, "", "boom"
        ),
    )
    with Server() as srv:
        status, _ = post_action(
            srv.port, "/action/switch", GOOD, {"profile": "gaming", "token": "t"}
        )
    assert status == 500
    banner = calls.get("banner", {})
    assert banner.get("kind") == "fail"
    assert banner.get("text") == (
        "Switch to gaming did not finish — the machine is still on base. "
        "Details: journalctl -u helm-switch@gaming.service"
    )
    assert banner.get("command") == "journalctl -u helm-switch@gaming.service"


def test_open_success_passes_banner_to_render(monkeypatch):
    calls = _capture_render(monkeypatch)
    monkeypatch.setattr(serve, "spawn_open", lambda name: None)
    with Server() as srv:
        status, _ = post_action(
            srv.port, "/action/open", GOOD, {"flake": "gaming", "token": "t"}
        )
    assert status == 200
    assert calls.get("banner") == {
        "kind": "ok",
        "text": "Opening gaming — a terminal window should appear on your desktop.",
    }


# ---------------------------------------------------------------------------
# route-level enforcement (the Handler, not just the pure function)
# ---------------------------------------------------------------------------


def test_get_with_foreign_host_is_403_without_token(monkeypatch):
    monkeypatch.setattr(serve.APP, "token", "sekrit-per-boot-token")
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/", {"Host": "evil.example:7700"})
    assert status == 403
    # The rebinding defense: nothing served to a non-accepted Host may
    # carry the per-boot token or any form.
    assert b"sekrit-per-boot-token" not in body
    assert b"<form" not in body


def test_get_bad_host_never_leaks_a_distinct_token(monkeypatch):
    monkeypatch.setattr(serve.APP, "token", "sekrit-per-boot-token")
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/", {"Host": "evil.example:7700"})
        status2, body2 = post_action(
            srv.port,
            "/action/switch",
            {"Host": "evil.example:7700", "Sec-Fetch-Site": "same-origin"},
            {"profile": "gaming", "token": "sekrit-per-boot-token"},
        )
    assert status == 403 and status2 == 403
    assert b"sekrit-per-boot-token" not in body
    assert b"sekrit-per-boot-token" not in body2


def test_control_json_serves_live_state(monkeypatch):
    monkeypatch.setattr(serve.APP, "token", "sekrit-per-boot-token")
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/control.json", GOOD)
    assert status == 200
    data = json.loads(body)
    assert data["active_profile"] == "base"
    assert data["last_switch"] is None
    assert "switching" in data
    # control.json is the switch state only -- never the token.
    assert b"sekrit-per-boot-token" not in body


def test_control_json_requires_accepted_host():
    with Server() as srv:
        status, _ = http_request(
            srv.port, "GET", "/control.json", {"Host": "evil.example:7700"}
        )
    assert status == 403


def test_control_json_is_the_state_and_status_json_is_the_collector_document(tmp_path):
    # R2: the two names now mean different things for Helm Home. /control.json
    # is the serve-time state (what /status.json used to return); /status.json
    # is the collector's document verbatim, so Helm Home's "status" is the
    # collector's, not the switch's.
    (tmp_path / "status.json").write_text(
        json.dumps({"schema": 1, "tiles": [{"name": "drift", "status": "ok"}]})
    )
    with Server() as srv:
        c_code, _, c_body = http_response(srv.port, "GET", "/control.json", GOOD)
        s_code, s_hdrs, s_body = http_response(srv.port, "GET", "/status.json", GOOD)
    assert c_code == 200 and json.loads(c_body)["active_profile"] == "base"
    assert s_code == 200 and json.loads(s_body)["tiles"][0]["name"] == "drift"
    assert s_hdrs.get("Content-Type", "").startswith("application/json")


def test_status_json_missing_document_is_404(tmp_path):
    # R2: /status.json is the collector's document; before the collector's
    # first run the file does not exist, so the route answers 404 (never a
    # synthetic document) and Helm Home distinguishes "not collected yet".
    with Server() as srv:
        status, _ = http_request(srv.port, "GET", "/status.json", GOOD)
    assert status == 404


def test_body_guards_reject_before_run_switch(monkeypatch):
    calls = []
    monkeypatch.setattr(serve, "run_switch", lambda name: calls.append(name))
    with Server() as srv:
        big = raw_request(
            srv.port,
            b"POST /action/switch HTTP/1.1\r\n"
            b"Host: localhost:7700\r\n"
            b"Sec-Fetch-Site: same-origin\r\n"
            b"Content-Length: 999999\r\n"
            b"Content-Type: application/x-www-form-urlencoded\r\n\r\n"
            b"profile=gaming&token=t",
        )
        bad = raw_request(
            srv.port,
            b"POST /action/switch HTTP/1.1\r\n"
            b"Host: localhost:7700\r\n"
            b"Sec-Fetch-Site: same-origin\r\n"
            b"Content-Length: abc\r\n\r\n",
        )
    big_status = big.split(b"\r\n", 1)[0]
    bad_status = bad.split(b"\r\n", 1)[0]
    assert b" 400 " in big_status
    assert b" 400 " in bad_status
    assert calls == []


def test_journal_read_is_boot_scoped_and_filtered(monkeypatch, tmp_path):
    seen = []

    def fake_run(argv, timeout=10.0):
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(serve, "run", fake_run)
    serve.read_state({"marker": str(tmp_path / "profile")})
    argv = seen[0]
    assert "-b" in argv and argv[argv.index("-g") + 1] == "^helm-switch: (begin|end) "


def test_stale_status_document_shows_an_age_banner(tmp_path):
    old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=900)).isoformat()
    (tmp_path / "status.json").write_text(
        json.dumps({"generated_at": old, "interval_s": 300, "tiles": []})
    )
    with Server() as srv:
        code, _, body = http_response(srv.port, "GET", "/", GOOD)
    assert code == 200 and b"status tiles are 15 min old" in body
    (tmp_path / "status.json").write_text(
        json.dumps(
            {
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "interval_s": 300,
                "tiles": [],
            }
        )
    )
    with Server() as srv:
        code, _, body = http_response(srv.port, "GET", "/", GOOD)
    assert code == 200 and b"min old" not in body


def test_unknown_routes_404():
    with Server() as srv:
        assert http_request(srv.port, "GET", "/nope", GOOD)[0] == 404
        assert (
            post_action(
                srv.port, "/action/nope", GOOD, {"profile": "gaming", "token": "t"}
            )[0]
            == 404
        )
        # GET on an action route is not a GET route (design spec).
        assert http_request(srv.port, "GET", "/action/switch", GOOD)[0] == 404


def test_open_route_spawns_once_and_rejects_unknown(monkeypatch):
    seen = []

    def fake_spawn(name):
        seen.append(name)

    monkeypatch.setattr(serve, "spawn_open", fake_spawn)
    with Server() as srv:
        status, _ = post_action(
            srv.port, "/action/open", GOOD, {"flake": "gaming", "token": "t"}
        )
        assert status == 200
        status, _ = post_action(
            srv.port, "/action/open", GOOD, {"flake": "nope", "token": "t"}
        )
        assert status == 403
        # ../x is not a workspace name either.
        status, _ = post_action(
            srv.port, "/action/open", GOOD, {"flake": "../x", "token": "t"}
        )
        assert status == 403
    assert seen == ["gaming"]


def test_open_needs_the_free_lock_too(monkeypatch):
    # "Every POST needs ... the free flock": an open during a running
    # switch answers 409, it does not spawn.
    monkeypatch.setattr(serve, "spawn_open", lambda name: None)
    with Server() as srv:
        with serve.switch_lock(serve.APP.lock_file):
            status, _ = post_action(
                srv.port, "/action/open", GOOD, {"flake": "gaming", "token": "t"}
            )
        assert status == 409


def test_switch_timeout_is_504(monkeypatch):
    def slow(name):
        raise subprocess.TimeoutExpired(["systemctl", "start", name], 360)

    monkeypatch.setattr(serve, "run_switch", slow)
    with Server() as srv:
        status, _ = post_action(
            srv.port, "/action/switch", GOOD, {"profile": "gaming", "token": "t"}
        )
    assert status == 504


def test_post_denial_with_good_host_is_full_page():
    # K5: a non-2xx action response is the FULL rendered page, never a bare
    # status line -- the operator (whose Host is always accepted) must see
    # Helm, not a white page with a number.
    with Server() as srv:
        status, body = post_action(
            srv.port, "/action/switch", GOOD, {"profile": "gaming", "token": "wrong"}
        )
    assert status == 403
    assert b"<!doctype html>" in body
    assert b"gpu" in body  # the v0 page is in there


def test_post_bad_host_is_403_and_runs_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(serve, "run_switch", lambda name: calls.append(name))
    with Server() as srv:
        status, _ = post_action(
            srv.port,
            "/action/switch",
            {"Host": "evil.example:7700", "Sec-Fetch-Site": "same-origin"},
            {"profile": "gaming", "token": "t"},
        )
    assert status == 403
    assert calls == []


def test_post_missing_both_headers_is_403(monkeypatch):
    calls = []
    monkeypatch.setattr(serve, "run_switch", lambda name: calls.append(name))
    with Server() as srv:
        status, _ = post_action(
            srv.port,
            "/action/switch",
            {"Host": "localhost:7700"},
            {"profile": "gaming", "token": "t"},
        )
    assert status == 403
    assert calls == []


# ---------------------------------------------------------------------------
# end-to-end: a live server, http.client, the fake runner
# ---------------------------------------------------------------------------


def test_end_to_end_matrix(capsys, monkeypatch):
    calls = []

    def fake_switch(name):
        calls.append(name)
        return subprocess.CompletedProcess(
            ["systemctl", "start", f"helm-switch@{name}.service"], 0, "", ""
        )

    monkeypatch.setattr(serve, "run_switch", fake_switch)
    with Server() as srv:
        # Happy: 200, full page, runner called exactly once.
        status, body = post_action(
            srv.port, "/action/switch", GOOD, {"profile": "gaming", "token": "t"}
        )
        assert status == 200
        assert b"<!doctype html>" in body
        assert calls == ["gaming"]
        # Wrong Host: 403, nothing run.
        status, body = post_action(
            srv.port,
            "/action/switch",
            {"Host": "evil.example:7700", "Sec-Fetch-Site": "same-origin"},
            {"profile": "gaming", "token": "t"},
        )
        assert status == 403
        assert calls == ["gaming"]
        # Cross-site fetch metadata: 403.
        status, _ = post_action(
            srv.port,
            "/action/switch",
            {"Host": "localhost:7700", "Sec-Fetch-Site": "cross-site"},
            {"profile": "gaming", "token": "t"},
        )
        assert status == 403
        # Bad token: 403.
        status, _ = post_action(
            srv.port, "/action/switch", GOOD, {"profile": "gaming", "token": "x"}
        )
        assert status == 403
        # Unknown profile: 403.
        status, _ = post_action(
            srv.port, "/action/switch", GOOD, {"profile": "nope", "token": "t"}
        )
        assert status == 403
        # Busy: the lock held elsewhere answers 409 and runs nothing.
        with serve.switch_lock(serve.APP.lock_file):
            status, body = post_action(
                srv.port, "/action/switch", GOOD, {"profile": "gaming", "token": "t"}
            )
            assert status == 409
            assert b"<!doctype html>" in body  # 409 is a full page too (K5)
        assert calls == ["gaming"]  # still exactly one run, never a re-run
    err = capsys.readouterr().err
    lines = [ln for ln in err.splitlines() if ln.startswith("helm-serve: ")]
    # One audit line per action, verdicts observably distinct (D8).
    assert lines == [
        "helm-serve: switch gaming http=200 unit_exit=0 from=localhost:7700",
        "helm-serve: switch gaming http=403 reason=bad-host from=evil.example:7700",
        "helm-serve: switch gaming http=403 reason=cross-site from=localhost:7700",
        "helm-serve: switch gaming http=403 reason=bad-token from=localhost:7700",
        "helm-serve: switch nope http=403 reason=target-not-allowed from=localhost:7700",
        "helm-serve: switch gaming http=409 reason=busy from=localhost:7700",
    ]


def test_two_concurrent_switches_one_runs_one_409(monkeypatch):
    started = threading.Event()
    release = threading.Event()
    calls = []

    def slow_switch(name):
        calls.append(name)
        started.set()
        assert release.wait(timeout=10)
        return subprocess.CompletedProcess(
            ["systemctl", "start", f"helm-switch@{name}.service"], 0, "", ""
        )

    monkeypatch.setattr(serve, "run_switch", slow_switch)
    results = {}

    def post(tag, port):
        results[tag] = post_action(
            port, "/action/switch", GOOD, {"profile": "gaming", "token": "t"}
        )

    with Server() as srv:
        t1 = threading.Thread(target=post, args=("first", srv.port))
        t1.start()
        assert started.wait(timeout=5)  # first request holds the lock inside run_switch
        t2 = threading.Thread(target=post, args=("second", srv.port))
        t2.start()
        t2.join(timeout=5)
        assert not t2.is_alive()
        assert results["second"][0] == 409  # the design-spec concurrency case
        release.set()
        t1.join(timeout=5)
        assert not t1.is_alive()
        assert results["first"][0] == 200
    assert calls == ["gaming"]  # exactly one switch ran


# ---------------------------------------------------------------------------
# main: token file, loopback-only bind, APP wiring
# ---------------------------------------------------------------------------


def test_write_token_file_mode_and_content(tmp_path):
    tok = tmp_path / "token"
    serve.write_token_file(tok, "a" * 64)
    assert tok.exists()
    assert tok.read_text() == "a" * 64
    assert (tok.stat().st_mode & 0o777) == 0o600
    assert not list(tmp_path.glob("*.tmp"))  # atomic: no leftovers


def test_write_token_file_survives_restrictive_umask(tmp_path):
    old = os.umask(0o077)
    try:
        serve.write_token_file(tmp_path / "token", "b" * 64)
    finally:
        os.umask(old)
    assert ((tmp_path / "token").stat().st_mode & 0o777) == 0o600


def test_main_writes_token_binds_loopback_and_serves(monkeypatch, tmp_path):
    cfg = copy.deepcopy(BASE_CFG)
    cfg["out_dir"] = str(tmp_path)
    cfg["control"]["marker"] = str(tmp_path / "profile")
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    tok = tmp_path / "helm" / "token"
    servers = []

    class FakeServer:
        def __init__(self, addr, handler):
            servers.append((addr, handler))

        def serve_forever(self):
            pass

        def server_close(self):
            pass

    monkeypatch.setattr(serve, "ThreadingHTTPServer", FakeServer)
    rc = serve.main(
        [
            "--config",
            str(cfg_path),
            "--token-file",
            str(tok),
            "--lock-file",
            str(tmp_path / "switch.lock"),
            "--listen",
            "127.0.0.1:7777",
        ]
    )
    assert rc == 0
    assert servers and servers[0][0] == ("127.0.0.1", 7777)
    assert servers[0][1] is serve.Handler
    assert serve.APP.cfg["control"]["profiles"] == ["base", "gaming"]
    assert serve.APP.lock_file == str(tmp_path / "switch.lock")
    # Per-boot token: 32 random bytes hex, written 0600.
    assert tok.exists()
    assert len(serve.APP.token) == 64
    assert tok.read_text() == serve.APP.token
    assert (tok.stat().st_mode & 0o777) == 0o600


def test_main_binds_ipv6_loopback_in_brackets(monkeypatch, tmp_path):
    cfg = copy.deepcopy(BASE_CFG)
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    servers = []

    class FakeServer:
        def __init__(self, addr, handler):
            servers.append(addr)

        def serve_forever(self):
            pass

        def server_close(self):
            pass

    monkeypatch.setattr(serve, "ThreadingHTTPServer", FakeServer)
    rc = serve.main(
        [
            "--config",
            str(cfg_path),
            "--token-file",
            str(tmp_path / "t"),
            "--lock-file",
            str(tmp_path / "l"),
            "--listen",
            "[::1]:7778",
        ]
    )
    assert rc == 0
    assert servers == [("::1", 7778)]


def test_main_refuses_non_loopback_listen(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(BASE_CFG))
    tok = tmp_path / "token"
    with pytest.raises(SystemExit) as exc:
        serve.main(
            [
                "--config",
                str(cfg_path),
                "--token-file",
                str(tok),
                "--lock-file",
                str(tmp_path / "l"),
                "--listen",
                "0.0.0.0:7777",
            ]
        )
    assert exc.value.code == 2
    # Refused before any state was written.
    assert not tok.exists()
