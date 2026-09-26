"""Helm API server (HM2): the api.py contract and the api_state.py reads.

HM2 gives Helm a JSON state/action API on a second loopback port with no
switch route. These tests load api.py by path (the A3 pattern), drive a real
ThreadingHTTPServer on an ephemeral port through http.client, and hold the
route-table contract: api_state.routes() is pinned to EXPECTED_ROUTES and the
merged api.route_table() must be a superset, so later api_*.py modules extend
the table without editing this file (HM10 owns the whole-table contract).

The mutant column in the plan is reproduced here as test names; each test is
written to fail on exactly the mutation its name targets (M1..M13 plus the
status round-trip negative control), not to rubber-stamp the current code.
"""

import ast
import copy
import http.client
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import threading

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC_DIR = HERE.parents[2] / "pkgs" / "helm"
# api.py does `from serve import ...` at load (serve does `import render`), so
# serve and render resolve from their own directory; here we put it on
# sys.path before loading api by path, exactly as test_serve.py does.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_SPEC = importlib.util.spec_from_file_location("api", SRC_DIR / "api.py")
api = importlib.util.module_from_spec(_SPEC)
# api.py defines a dataclass (Request); @dataclass resolves cls.__module__ via
# sys.modules, so the module must be registered before exec_module.
sys.modules["api"] = api
_SPEC.loader.exec_module(api)

# api.py's `from serve import ...` put serve (and its render dependency) into
# sys.modules, and api.discover() imported api_state; reach both the same way
# the code under test does so monkeypatching serve.run lands in the right
# module.
serve = sys.modules["serve"]
api_state = sys.modules["api_state"]

EXPECTED_ROUTES = {
    ("GET", "/v1/status"),
    ("GET", "/v1/control"),
    ("GET", "/v1/home"),
}

TILE_NAMES = [
    "backup-snapshot",
    "backup-parity",
    "timers",
    "basket-doctor",
    "broker",
    "gpu",
    "host",
    "drift",
    "flake-check",
]

GOOD = {"Host": "localhost:7700"}

BASE_CFG = {
    "operator_user": "alice",
    "interval_s": 300,
    "out_dir": "/var/lib/helm",
    "control": {
        "profiles": ["base", "gaming"],
        "workspaces": {},
        "host_aliases": ["localhost", "127.0.0.1"],
        "listen": "127.0.0.1:7700",
        "marker": "/etc/helm/profile",
        "kgx_bin": "/run/current-system/sw/bin/kgx",
        "helm_open_workspace_bin": "/run/current-system/sw/bin/helm-open-workspace",
    },
}


@pytest.fixture(autouse=True)
def app(tmp_path, monkeypatch):
    """Every test gets a configured api.APP: a tmp out_dir and marker, and an
    empty journal seam so /v1/control's read_state never runs a real journalctl."""
    cfg = copy.deepcopy(BASE_CFG)
    cfg["out_dir"] = str(tmp_path)
    cfg["control"]["marker"] = str(tmp_path / "profile")
    (tmp_path / "profile").write_text("base\n")
    monkeypatch.setattr(api.APP, "cfg", cfg)
    monkeypatch.setattr(
        serve,
        "run",
        lambda argv, timeout=10.0: subprocess.CompletedProcess(argv, 0, "", ""),
    )
    return api.APP


class Server:
    """A live Handler on an ephemeral loopback port, in a thread."""

    def __init__(self):
        self.httpd = api.ThreadingHTTPServer(("127.0.0.1", 0), api.Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


def http_response(port, method, path, headers, body=None):
    """One live request: (status, response headers, body)."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, body=body, headers=dict(headers))
    resp = conn.getresponse()
    resp_headers = dict(resp.getheaders())
    data = resp.read()
    conn.close()
    return resp.status, resp_headers, data


def http_request(port, method, path, headers, body=None):
    status, _, data = http_response(port, method, path, headers, body)
    return status, data


# ---------------------------------------------------------------------------
# route table == contract (M1: a switch route or any drift breaks this)
# ---------------------------------------------------------------------------


def test_route_table_matches_contract():
    assert {(m, p) for m, p, _ in api_state.routes()} == EXPECTED_ROUTES
    assert EXPECTED_ROUTES <= {(m, p) for m, p, _ in api.route_table()}


def test_no_switch_strings():
    # M1: a switch route smuggled into either module would name its target;
    # the grep probes are the second layer, this test is the first.
    forbidden = re.compile(
        r"helm-switch|switch-to-configuration|nixos-rebuild|/v1/switch"
    )
    for name in ("api.py", "api_state.py"):
        text = (SRC_DIR / name).read_text()
        assert not forbidden.search(text), f"{name} contains a switch string"


# ---------------------------------------------------------------------------
# read-only dispatch (M2: POST dispatched like GET)
# ---------------------------------------------------------------------------


def test_post_on_read_route_is_405():
    with Server() as srv:
        status, hdrs, _ = http_response(srv.port, "POST", "/v1/status", GOOD)
    assert status == 405
    assert hdrs.get("Allow") == "GET"


# ---------------------------------------------------------------------------
# Host / Origin allowlists (M3, M4)
# ---------------------------------------------------------------------------


def test_bad_host_is_400():
    with Server() as srv:
        status, _ = http_request(
            srv.port, "GET", "/v1/control", {"Host": "evil.example:7700"}
        )
    assert status == 400


def test_foreign_origin_is_403():
    with Server() as srv:
        ok, _ = http_request(
            srv.port,
            "GET",
            "/v1/control",
            {"Host": "localhost:7700", "Origin": "http://localhost:7700"},
        )
        bad, _ = http_request(
            srv.port,
            "GET",
            "/v1/control",
            {"Host": "localhost:7700", "Origin": "http://evil.example"},
        )
    assert ok == 200
    assert bad == 403


# ---------------------------------------------------------------------------
# per-request re-reads (M5: memoized read_state; M6: home.json required)
# ---------------------------------------------------------------------------


def test_control_rereads_marker(tmp_path):
    marker = tmp_path / "profile"
    marker.write_text("base\n")
    with Server() as srv:
        first = http_request(srv.port, "GET", "/v1/control", GOOD)
        marker.write_text("gaming\n")
        second = http_request(srv.port, "GET", "/v1/control", GOOD)
    assert json.loads(first[1])["active_profile"] == "base"
    assert json.loads(second[1])["active_profile"] == "gaming"


def test_home_absent_is_empty_list():
    # /etc/helm/home.json is absent in this environment (helmHome is inert).
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/v1/home", GOOD)
    assert status == 200
    assert json.loads(body) == {"flakes": []}


# ---------------------------------------------------------------------------
# duplicate route refusal (M7)
# ---------------------------------------------------------------------------


def test_duplicate_route_raises():
    # /v1/status is already registered by discover(); registering it again
    # must refuse, not silently overwrite.
    with pytest.raises(RuntimeError):
        api.register("GET", "/v1/status", lambda c, r: (200, {}))


# ---------------------------------------------------------------------------
# response headers (M8, M8b, M8c)
# ---------------------------------------------------------------------------


def test_nosniff_on_every_response():
    with Server() as srv:
        _, ok, _ = http_response(srv.port, "GET", "/v1/control", GOOD)
        _, nf, _ = http_response(srv.port, "GET", "/nope", GOOD)
    assert ok.get("X-Content-Type-Options") == "nosniff"
    assert nf.get("X-Content-Type-Options") == "nosniff"


def test_no_set_cookie():
    with Server() as srv:
        _, hdrs, _ = http_response(srv.port, "GET", "/v1/control", GOOD)
    assert "Set-Cookie" not in hdrs


def test_no_store_on_every_response():
    with Server() as srv:
        _, ok, _ = http_response(srv.port, "GET", "/v1/control", GOOD)
        _, nf, _ = http_response(srv.port, "GET", "/nope", GOOD)
    assert ok.get("Cache-Control") == "no-store"
    assert nf.get("Cache-Control") == "no-store"


# ---------------------------------------------------------------------------
# IPv6 listen (M9: naive split instead of parse_listen)
# ---------------------------------------------------------------------------


def test_ipv6_listen_parses(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(BASE_CFG))
    servers = []

    class FakeServer:
        def __init__(self, addr, handler):
            servers.append(addr)

        def serve_forever(self):
            pass

        def server_close(self):
            pass

    monkeypatch.setattr(api, "ThreadingHTTPServer", FakeServer)
    rc = api.main(["--config", str(cfg_path), "--listen", "[::1]:7710"])
    assert rc == 0
    assert servers == [("::1", 7710)]


def test_main_refuses_non_loopback_listen(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(BASE_CFG))
    with pytest.raises(SystemExit) as exc:
        api.main(["--config", str(cfg_path), "--listen", "0.0.0.0:7777"])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# body cap (M10) and one-segment capture (M11)
# ---------------------------------------------------------------------------


def test_oversize_post_is_413(monkeypatch):
    extra = [("POST", "/v1/test-post", lambda c, r: (200, {"ok": True}))]
    monkeypatch.setattr(api, "_ROUTES", api._ROUTES + extra)
    with Server() as srv:
        status, _ = http_request(srv.port, "POST", "/v1/test-post", GOOD, b"x" * 300)
    assert status == 413


def test_capture_is_one_segment(monkeypatch):
    def handler(cfg, request):
        return 200, {"id": request.params.get("id")}

    extra = [("GET", "/v1/x/<id>", handler)]
    monkeypatch.setattr(api, "_ROUTES", api._ROUTES + extra)
    with Server() as srv:
        status, _ = http_request(srv.port, "GET", "/v1/x/a/b", GOOD)
    assert status == 404


def test_capture_populates_params(monkeypatch):
    captured = {}

    def handler(cfg, request):
        captured["id"] = request.params.get("id")
        return 200, {"id": request.params.get("id")}

    extra = [("GET", "/v1/x/<id>", handler)]
    monkeypatch.setattr(api, "_ROUTES", api._ROUTES + extra)
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/v1/x/abc", GOOD)
    assert status == 200
    assert json.loads(body) == {"id": "abc"}
    assert captured["id"] == "abc"


def test_dispatch_never_unanswered(monkeypatch):
    # HM4b (MAJOR-1): a handler that raises must still answer — a 500 with the
    # error body — and the server keeps serving the next request.
    def boom(cfg, request):
        raise RuntimeError("kaboom")

    extra = [("GET", "/v1/boom", boom)]
    monkeypatch.setattr(api, "_ROUTES", api._ROUTES + extra)
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/v1/boom", GOOD)
    assert status == 500
    assert json.loads(body)["error"].startswith("RuntimeError")
    with Server() as srv2:
        ok, _ = http_request(srv2.port, "GET", "/v1/control", GOOD)
    assert ok == 200


# ---------------------------------------------------------------------------
# the subprocess seam (M12, M13)
# ---------------------------------------------------------------------------


def test_no_direct_subprocess_in_route_modules():
    for path in sorted(SRC_DIR.glob("api_[a-z]*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "subprocess", f"{path.name} imports subprocess"
            elif isinstance(node, ast.ImportFrom):
                assert node.module != "subprocess", f"{path.name} imports subprocess"


def test_run_refuses_unlisted_program(monkeypatch):
    calls = []
    monkeypatch.setitem(api.APP.cfg, "_run", lambda argv, **kw: calls.append(argv))
    cp = api.run(["nixos-rebuild", "switch"])
    assert cp.returncode == 126
    assert "api.run refuses" in cp.stderr
    assert calls == []


def test_run_refuses_systemctl_restart(monkeypatch):
    calls = []
    monkeypatch.setitem(api.APP.cfg, "_run", lambda argv, **kw: calls.append(argv))
    cp = api.run(["systemctl", "restart", "seat@x.service"])
    assert cp.returncode == 126
    assert "api.run refuses" in cp.stderr
    assert calls == []


def test_run_allows_allowlisted_programs(monkeypatch):
    calls = []
    monkeypatch.setitem(api.APP.cfg, "_run", lambda argv, **kw: calls.append(argv))
    api.run(["python3", "-c", "print(1)"])
    api.run(["systemctl", "start", "seat@alice.service"])
    assert calls == [
        ["python3", "-c", "print(1)"],
        ["systemctl", "start", "seat@alice.service"],
    ]


def test_run_admits_read_verbs(monkeypatch):
    # HM4b/HM4c: the read-only systemctl verbs (list-units, show) are admitted;
    # every other verb is refused — reported as returncode 126 with HM2's
    # message rather than raised.
    calls = []
    monkeypatch.setitem(api.APP.cfg, "_run", lambda argv, **kw: calls.append(argv))
    api.run(
        ["systemctl", "list-units", "seat@*", "--all", "--output=json", "--no-pager"]
    )
    api.run(["systemctl", "show", "seat@a.service"])
    assert api.run(["systemctl", "restart", "seat@x.service"]).returncode == 126
    assert api.run(["systemctl", "daemon-reload"]).returncode == 126
    assert calls == [
        ["systemctl", "list-units", "seat@*", "--all", "--output=json", "--no-pager"],
        ["systemctl", "show", "seat@a.service"],
    ]


# ---------------------------------------------------------------------------
# negative control: the status document is read, not echoed (empty-dict mutant)
# ---------------------------------------------------------------------------


def test_status_round_trips(tmp_path):
    fixture = {name: {"status": "ok"} for name in TILE_NAMES}
    (tmp_path / "status.json").write_text(json.dumps(fixture))
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/v1/status", GOOD)
    assert status == 200
    assert set(json.loads(body).keys()) == set(TILE_NAMES)


# ---------------------------------------------------------------------------
# HM4c fix round: the read verbs are pinned, show is seat-only, and run()'s
# capture/text/timeout defaults plus failure returncodes are the contract
# ---------------------------------------------------------------------------


def test_read_verbs_pinned():
    # M5 (read-verbs-widened): widening the tuple past list-units/show admits
    # a write verb through the read arm.
    assert api.READ_VERBS == ("list-units", "show")


def test_show_restricted_to_seat_units(monkeypatch):
    # M4 (show-any-unit): with the wider arm, show sshd.service is admitted.
    calls = []
    monkeypatch.setitem(api.APP.cfg, "_run", lambda argv, **kw: calls.append(argv))
    api.run(["systemctl", "show", "seat@x.service"])
    refused_show = api.run(["systemctl", "show", "sshd.service"])
    refused_kill = api.run(["systemctl", "kill", "seat@x.service"])
    assert refused_show.returncode == 126
    assert refused_kill.returncode == 126
    assert calls == [["systemctl", "show", "seat@x.service"]]


def test_run_defaults_capture_and_timeout(monkeypatch):
    # M1/M2 (no-capture/no-timeout): the defaults are what make stdout come
    # back as text and the timeout bounded.
    cp = api.run(["python3", "-c", "print('hi')"])
    assert cp.returncode == 0
    assert cp.stdout == "hi\n"
    assert isinstance(cp.stdout, str)

    monkeypatch.setitem(api.APP.cfg, "_timeout", 0.5)
    cp = api.run(["python3", "-c", "import time; time.sleep(3)"])
    assert cp.returncode == 124

    def missing(argv, **kw):
        raise FileNotFoundError(2, "No such file or directory", argv[0])

    monkeypatch.setitem(api.APP.cfg, "_run", missing)
    cp = api.run(["git", "status"])
    assert cp.returncode == 127


# ---------------------------------------------------------------------------
# HM10: the API contract document (pkgs/helm/API.md)
# ---------------------------------------------------------------------------

# The status codes each route can answer, typed from HM2-HM8's interfaces: the
# handler's own outcome codes plus the framework's universal refusals — 400 bad
# Host, 403 foreign Origin, 405 unregistered method (with Allow), and 413
# oversize POST body. The seam-failure 502 is an internal degradation, not part
# of the public contract a patched dsh web UI codes against.
EXPECTED_CODES = {
    ("GET", "/"): {200, 400, 403, 405},
    ("GET", "/v1/status"): {200, 400, 403, 404, 405},
    ("GET", "/v1/control"): {200, 400, 403, 405},
    ("GET", "/v1/home"): {200, 400, 403, 405},
    ("GET", "/v1/seats"): {200, 400, 403, 405},
    ("POST", "/v1/seats"): {202, 400, 403, 405, 413},
    ("POST", "/v1/seats/<id>/stop"): {202, 400, 403, 405, 413},
    ("POST", "/v1/seats/<id>/attach"): {200, 400, 403, 404, 405, 409, 413},
    ("GET", "/v1/patches"): {200, 400, 403, 405},
    ("GET", "/v1/tasks"): {200, 400, 403, 405},
    ("POST", "/v1/engage"): {204, 400, 403, 405, 413},
}

API_MD = SRC_DIR / "API.md"


def _api_md_headings():
    """Every ``### METHOD path`` heading in API.md, as ``(method, path)``."""
    headings = []
    for line in API_MD.read_text().splitlines():
        if line.startswith("### "):
            method, _, path = line[4:].partition(" ")
            headings.append((method, path))
    return headings


def _api_md_sections():
    """``{(method, path): [int, ...]}`` — the `` `NNN` `` status-code tokens
    under each ``### `` heading."""
    sections = {}
    current = None
    for line in API_MD.read_text().splitlines():
        if line.startswith("### "):
            method, _, path = line[4:].partition(" ")
            current = (method, path)
            sections[current] = []
        elif current is not None:
            for code in re.findall(r"`(\d{3})`", line):
                sections[current].append(int(code))
    return sections


def test_contract_document_names_every_route():
    # M1 (route-undocumented) and M2 (heading-stale): the document's headings
    # and api.route_table()'s pairs are the same set, in both directions, so a
    # route without a heading and a heading without a route both fail.
    table = {(m, p) for m, p, _ in api.route_table()}
    headings = set(_api_md_headings())
    missing = table - headings
    assert not missing, f"routes missing from API.md: {missing}"
    stale = headings - table
    assert not stale, f"headings in API.md not in the route table: {stale}"


def test_contract_status_codes_documented():
    # M5 (code-undocumented) and M6 (code-invented): each route's section lists
    # exactly EXPECTED_CODES[route] as `NNN` tokens — no missing, no surplus.
    sections = _api_md_sections()
    for route, expected in EXPECTED_CODES.items():
        assert route in sections, f"API.md has no section for {route}"
        documented = set(sections[route])
        missing = expected - documented
        assert not missing, f"{route}: status codes missing from API.md: {missing}"
        surplus = documented - expected
        assert not surplus, f"{route}: status codes not in EXPECTED_CODES: {surplus}"
    for route in sections:
        assert route in EXPECTED_CODES, (
            f"API.md section without EXPECTED_CODES: {route}"
        )
