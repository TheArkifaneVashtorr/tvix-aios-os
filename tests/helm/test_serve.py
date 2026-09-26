"""Helm v1 control backend: the serve.py contract (plan Task 1 + D3/D8/D9/D10).

D-H1 made helm-serve a read-only page: no token, no forms, no switch or
open actions. The matrix still covers the Host allowlist (DNS-rebinding),
per-request state reads, route-level enforcement, the render.py integration
seam, and an end-to-end pass over a live ThreadingHTTPServer with
http.client -- but the actions are gone: every POST is 405 read-only (or
403 on a bad Host), and run_switch/spawn_open/validate_post/switch_lock/
write_token_file/_audit must not even exist as entry points.

These tests never assert on render.py's OUTPUT -- T1's own tests own that
surface. The integration is pinned by monkeypatching render_control and
asserting what serve passes THROUGH it.
"""

import copy
import datetime as dt
import http.client
import importlib.util
import json
import pathlib
import subprocess
import sys
import threading

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

GOOD = {"Host": "localhost:7700", "Sec-Fetch-Site": "same-origin"}

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
    """Every test gets a configured APP: a tmp out_dir and marker, and an
    empty journal seam so no test ever runs a real journalctl."""
    cfg = copy.deepcopy(BASE_CFG)
    cfg["out_dir"] = str(tmp_path)
    cfg["control"]["marker"] = str(tmp_path / "profile")
    (tmp_path / "profile").write_text("base\n")
    (tmp_path / "index.html").write_text(PAGE)
    monkeypatch.setattr(serve.APP, "cfg", cfg)
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
        body = "&".join(f"{k}={v}" for k, v in form.items()).encode()
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


# ---------------------------------------------------------------------------
# U2 review fix: anti-framing headers on every response
# ---------------------------------------------------------------------------


def test_send_carries_anti_framing_headers():
    # U2: every response -- a 200 page and a 405 read-only reply alike --
    # must refuse framing and caching. The page is read-only now, but the
    # framing defense stays: an attacker must not embed the switch state on
    # their origin.
    with Server() as srv:
        _, ok_hdrs, _ = http_response(srv.port, "GET", "/", GOOD)
        _, deny_hdrs, _ = http_response(
            srv.port,
            "POST",
            "/action/switch",
            GOOD,
            {"profile": "gaming"},
        )
    for hdrs in (ok_hdrs, deny_hdrs):
        assert hdrs.get("Content-Security-Policy") == "frame-ancestors 'none'"
        assert hdrs.get("X-Frame-Options") == "DENY"
        assert hdrs.get("Referrer-Policy") == "same-origin"
        assert hdrs.get("Cache-Control") == "no-store"
        assert hdrs.get("X-Content-Type-Options") == "nosniff"


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


def test_accepted_hosts_folds_api_listen():
    # HM7: the API listen and its localhost alias are accepted too, so a
    # browser's Host: 127.0.0.1:7710 (or localhost:7710) on the API port is
    # answered rather than refused; a Host on neither listen stays refused.
    cfg = copy.deepcopy(BASE_CFG)
    cfg["api"] = {"listen": "127.0.0.1:7710", "links": {}}
    assert serve.accepted_hosts(cfg) == {
        "localhost:7700",
        "127.0.0.1:7700",
        "127.0.0.1:7710",
        "localhost:7710",
    }
    assert serve.accepted_origins(cfg) == {
        "http://localhost:7700",
        "http://127.0.0.1:7700",
        "http://127.0.0.1:7710",
        "http://localhost:7710",
    }
    assert "evil.example:7710" not in serve.accepted_hosts(cfg)


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


def test_load_config_reads_json(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps(BASE_CFG))
    assert serve.load_config(p) == BASE_CFG


# ---------------------------------------------------------------------------
# D-H1: no switch/open/validate entry points remain
# ---------------------------------------------------------------------------


def test_no_switch_open_or_validate_entry_points_remain():
    # D-H1: the action surface is gone. A stale unit line or a revert that
    # leaves run_switch defined must fail loudly here.
    for name in (
        "run_switch",
        "spawn_open",
        "validate_post",
        "switch_lock",
        "write_token_file",
        "_audit",
    ):
        assert not hasattr(serve, name), name


# ---------------------------------------------------------------------------
# D-H1: every POST is 405 read-only (or 403 on a bad Host)
# ---------------------------------------------------------------------------


def test_post_is_405_read_only_after_the_host_check():
    with Server() as srv:
        # Accepted Host: 405 with the plain-text body and an Allow header.
        code, hdrs, body = http_response(
            srv.port, "POST", "/action/switch", {"Host": "localhost:7700"}
        )
        assert code == 405
        assert body == b"read-only"
        assert hdrs.get("Allow") == "GET"
        # The Host check runs first: a rebound POST is 403, not 405.
        code, _, _ = http_response(
            srv.port, "POST", "/action/switch", {"Host": "evil.example:7700"}
        )
        assert code == 403
        # Every path, / included, is read-only.
        code, _, body = http_response(srv.port, "POST", "/", {"Host": "localhost:7700"})
        assert code == 405
        assert body == b"read-only"


# ---------------------------------------------------------------------------
# D-H1: main takes no token or lock arguments
# ---------------------------------------------------------------------------


def test_main_takes_no_token_or_lock_arguments():
    # The stale unit line carried --token-file/--lock-file; argparse must
    # reject them loudly (exit 2) rather than mint a token or a lock file.
    with pytest.raises(SystemExit) as exc:
        serve.main(["--token-file", "x", "--lock-file", "y"])
    assert exc.value.code == 2
    # --listen is the only way to reach the loopback gate, and it still
    # refuses a non-loopback bind before any state is written.
    with pytest.raises(SystemExit) as exc2:
        serve.main(["--listen", "0.0.0.0:7700"])
    assert exc2.value.code == 2


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


def test_read_state_sorts_reverse_journal_order(monkeypatch, tmp_path):
    # journalctl --grep emits matching records newest-first; read_state must
    # re-sort by __REALTIME_TIMESTAMP or the reverse order leaves last_switch
    # as the FIRST switch and a stuck switching state (caught in the D-H1 VM).
    control = {"marker": str(tmp_path / "profile")}
    t0 = 1_000_000_000.0
    msgs = [
        ("helm-switch: begin base -> alt root=/run/booted-system", t0 + 1),
        ("helm-switch: end alt exit=0", t0 + 2),
        ("helm-switch: begin alt -> base root=/run/booted-system", t0 + 3),
        ("helm-switch: end base exit=0", t0 + 4),
    ]
    lines = "\n".join(
        json.dumps({"MESSAGE": msg, "__REALTIME_TIMESTAMP": str(int(ts * 1e6))})
        for msg, ts in reversed(msgs)
    )
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(
            argv, 0, lines + "\n", ""
        ),
    )
    state = serve.read_state(control)
    assert state["last_switch"] == {
        "from": "alt",
        "to": "base",
        "result": "ok",
        "at": iso(1_000_000_004),
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

    def fake_render_control(status_html, control, state, banner=None):
        calls["status_html"] = status_html
        calls["control"] = control
        calls["state"] = state
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


# ---------------------------------------------------------------------------
# route-level enforcement (the Handler, not just the pure function)
# ---------------------------------------------------------------------------


def test_control_json_serves_live_state():
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/control.json", GOOD)
    assert status == 200
    data = json.loads(body)
    assert data["active_profile"] == "base"
    assert data["last_switch"] is None
    assert "switching" in data


def test_control_json_requires_accepted_host():
    with Server() as srv:
        status, _ = http_request(
            srv.port, "GET", "/control.json", {"Host": "evil.example:7700"}
        )
    assert status == 403


def test_control_json_is_the_state_and_status_json_is_the_collector_document(tmp_path):
    # R2: the two names now mean different things for Helm Home. /control.json
    # is the serve-time state; /status.json is the collector's document
    # verbatim.
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
    # synthetic document).
    with Server() as srv:
        status, _ = http_request(srv.port, "GET", "/status.json", GOOD)
    assert status == 404


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
        # GET on an action route is not a GET route (design spec).
        assert http_request(srv.port, "GET", "/action/switch", GOOD)[0] == 404


# ---------------------------------------------------------------------------
# end-to-end: a live server, http.client, get-only matrix
# ---------------------------------------------------------------------------


def test_end_to_end_get_only_matrix(tmp_path):
    with Server() as srv:
        # GET / : 200, and the page carries no form (read-only, D-H1).
        code, _, body = http_response(srv.port, "GET", "/", GOOD)
        assert code == 200
        assert b"<form" not in body
        # /control.json : 200.
        assert http_response(srv.port, "GET", "/control.json", GOOD)[0] == 200
        # /status.json : 404 before the collector documents anything.
        assert http_response(srv.port, "GET", "/status.json", GOOD)[0] == 404
        # /nope : 404.
        assert http_response(srv.port, "GET", "/nope", GOOD)[0] == 404
        # a bad Host : 403, without the page body (nothing rendered).
        code, _, body = http_response(
            srv.port, "GET", "/", {"Host": "evil.example:7700"}
        )
        assert code == 403
        assert b"gpu" not in body
        # no POST route exists: even /action/switch is read-only.
        code, _, body = http_response(
            srv.port, "POST", "/action/switch", {"Host": "localhost:7700"}
        )
        assert code == 405
        assert body == b"read-only"
    # with a status document, /status.json returns it verbatim.
    (tmp_path / "status.json").write_text(json.dumps({"schema": 1, "tiles": []}))
    with Server() as srv:
        code, _, body = http_response(srv.port, "GET", "/status.json", GOOD)
    assert code == 200 and b'"tiles"' in body


# ---------------------------------------------------------------------------
# main: loopback-only bind, no token file
# ---------------------------------------------------------------------------


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
    rc = serve.main(["--config", str(cfg_path), "--listen", "[::1]:7778"])
    assert rc == 0
    assert servers == [("::1", 7778)]
    assert serve.APP.cfg["control"]["profiles"] == ["base", "gaming"]


def test_main_refuses_non_loopback_listen(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(BASE_CFG))
    with pytest.raises(SystemExit) as exc:
        serve.main(["--config", str(cfg_path), "--listen", "0.0.0.0:7777"])
    assert exc.value.code == 2
