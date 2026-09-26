"""Helm API home route (HM7): the web home page on `GET /`.

HM7 gives Helm the one screen that puts every JSON route's datum together:
the declared flakes, the HM4 session list (with the three HM5 seat buttons),
the HM6 patch queue, the collector's status tiles, and the `api.links` list —
rendered to HTML, served with a Content-Security-Policy whose `script-src`
names the sha256 of the single inline script, and read in-process (each
section calls its own route handler with an `api.Request`, never a socket).

The mutant column in the plan (M1..M9 plus the full-page negative control) is
reproduced here as test names; each test is written to fail on exactly the
mutation its name targets, not to rubber-stamp the current code.
"""

import ast
import base64
import hashlib
import http.client
import importlib.util
import pathlib
import re
import subprocess
import sys
import threading

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC_DIR = HERE.parents[2] / "pkgs" / "helm"
# api_home.py is an api_*.py route module discovered at api.py import, and
# api.py does `from serve import ...`; both resolve from their own directory,
# so put it on sys.path before loading them by path, exactly as test_api.py
# and test_api_seats.py do.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Load api_home.py by path first (the FileNotFoundError red when it does not
# yet exist), registering it so api.py's discover() reuses this exact object.
_home_spec = importlib.util.spec_from_file_location("api_home", SRC_DIR / "api_home.py")
api_home = importlib.util.module_from_spec(_home_spec)
sys.modules["api_home"] = api_home
_home_spec.loader.exec_module(api_home)

# api.py's discover() imports api_home (above) and the other route modules;
# reach the dispatcher and the Request dataclass the same way the code under
# test does.
_spec = importlib.util.spec_from_file_location("api", SRC_DIR / "api.py")
api = importlib.util.module_from_spec(_spec)
sys.modules["api"] = api
_spec.loader.exec_module(api)

serve = sys.modules["serve"]
api_state = sys.modules["api_state"]
api_seats = sys.modules["api_seats"]
api_record = sys.modules["api_record"]

GOOD = {"Host": "localhost:7700"}

# A cfg the pure renderer reads only for `api.links`; the route handlers the
# live server calls read the rest (out_dir, seats, repo, _run) from APP.cfg.
CFG = {"api": {"listen": "127.0.0.1:7710", "links": {}}}


@pytest.fixture(autouse=True)
def app(tmp_path, monkeypatch):
    """Every live-server test gets a configured api.APP whose route handlers
    degrade gracefully: an empty spool (no seats), a git show that answers an
    empty blob (patches -> the handler's error body), and no status.json yet
    (status -> 404 -> the home page's "unavailable" line)."""
    cfg = {
        "out_dir": str(tmp_path),
        "api": {"listen": "127.0.0.1:7710", "links": {}},
        "seats": {"spool_dir": str(tmp_path / "spool")},
        "repo": str(tmp_path / "repo"),
        "_run": lambda argv, **kw: subprocess.CompletedProcess(argv, 0, "", ""),
        "_readlink": lambda path: "system-55-link",
    }
    (tmp_path / "spool").mkdir()
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


def http_response(port, method, path, headers):
    """One live request: (status, response headers, body)."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, headers=dict(headers))
    resp = conn.getresponse()
    resp_headers = dict(resp.getheaders())
    data = resp.read()
    conn.close()
    return resp.status, resp_headers, data


def http_request(port, method, path, headers):
    status, _, data = http_response(port, method, path, headers)
    return status, data


def home(cfg, request=None):
    """Run the route handler directly; (status, body)."""
    if request is None:
        request = api.Request(
            method="GET", path="/", params={}, headers={}, body=b"", origin=None
        )
    return api_home.home(cfg, request)


def render(**overrides):
    """render_home with sensible empty fixtures; override any section."""
    args = {
        "cfg": CFG,
        "home_doc": {"flakes": []},
        "seats": {"seats": []},
        "patches": {"patches": [], "running_generation": 55, "head": "deadbeef"},
        "status": {"tiles": []},
        "links": {},
    }
    args.update(overrides)
    return api_home.render_home(**args)


# ---------------------------------------------------------------------------
# M1: no <form> element anywhere on the page
# ---------------------------------------------------------------------------


def test_no_form_element():
    # Render a seat row so the Start/Stop/Attach controls (the only place a
    # form could sneak in) are present.
    page = render(
        seats={
            "seats": [
                {
                    "id": "a",
                    "unit": "seat@a.service",
                    "state": "active",
                    "port": 43210,
                    "url": "http://127.0.0.1:43210/",
                    "exit_code": None,
                }
            ]
        }
    )
    assert "<form" not in page
    assert "<form" not in api_home.SCRIPT


# ---------------------------------------------------------------------------
# M2: no `switch` string; the script names only the three seat routes
# ---------------------------------------------------------------------------


def test_no_switch_string():
    page = render(
        seats={
            "seats": [
                {
                    "id": "a",
                    "unit": "seat@a.service",
                    "state": "active",
                    "port": 43210,
                    "url": "http://127.0.0.1:43210/",
                    "exit_code": None,
                }
            ]
        }
    )
    assert "switch" not in page.lower()
    assert "switch" not in api_home.SCRIPT.lower()


def test_only_seat_routes_in_script():
    # Every "/v1/..." path the script names must be one of HM5's three seat
    # routes (start, stop, attach) — all under /v1/seats — or HM8's single
    # engagement route. A `/v1/switch` smuggled in fails the prefix check.
    paths = set(re.findall(r"/v1/[A-Za-z0-9/_-]*", api_home.SCRIPT))
    assert paths, "the inline script names no /v1/ route"
    for path in paths:
        assert path.startswith("/v1/seats") or path == "/v1/engage", path


# ---------------------------------------------------------------------------
# M3: every dynamic value is html.escape'd
# ---------------------------------------------------------------------------


def test_html_escaped():
    page = render(
        seats={
            "seats": [
                {
                    "id": "<b>x</b>",
                    "unit": "seat@<b>x</b>.service",
                    "state": "active",
                    "port": None,
                    "url": None,
                    "exit_code": None,
                }
            ]
        }
    )
    assert "<b>" not in page
    assert "&lt;b&gt;x&lt;/b&gt;" in page


# ---------------------------------------------------------------------------
# M4: the CSP header carries the script hash (and a script edit without a hash
# update reddens it too)
# ---------------------------------------------------------------------------


def test_csp_header_present_and_hash_matches(app):
    expected_hash = base64.b64encode(
        hashlib.sha256(api_home.SCRIPT.encode("utf-8")).digest()
    ).decode("ascii")
    assert api_home.SCRIPT_HASH == expected_hash
    with Server() as srv:
        status, headers, _ = http_response(srv.port, "GET", "/", GOOD)
    assert status == 200
    assert headers.get("Content-Type", "").startswith("text/html")
    csp = headers.get("Content-Security-Policy")
    assert csp is not None
    assert f"script-src 'sha256-{expected_hash}'" in csp


# ---------------------------------------------------------------------------
# M5: an empty flakes list renders "No flakes declared", never a 500
# ---------------------------------------------------------------------------


def test_empty_home_renders_no_flakes_text():
    page = render(home_doc={"flakes": []})
    assert "No flakes declared" in page


# ---------------------------------------------------------------------------
# M6: a failing domain renders "unavailable:" and the page still answers 200
# ---------------------------------------------------------------------------


def test_failing_domain_renders_unavailable(app, monkeypatch):
    def boom(cfg, request):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(api_record, "_patches_handler", boom)
    with Server() as srv:
        status, body = http_request(srv.port, "GET", "/", GOOD)
    assert status == 200
    assert "unavailable:" in body.decode("utf-8")


# ---------------------------------------------------------------------------
# M7: the Links section renders `api.links`
# ---------------------------------------------------------------------------


def test_feed_link_rendered():
    page = render(links={"feed": "http://127.0.0.1:8080/"})
    assert 'href="http://127.0.0.1:8080/"' in page


# ---------------------------------------------------------------------------
# M8: render_home is deterministic (no timestamp in the body)
# ---------------------------------------------------------------------------


def test_render_is_deterministic():
    home_doc = {
        "flakes": [
            {
                "path": "/home/a/flake",
                "declaration": "/home/a/flake#helm",
                "profile": None,
                "seats": [],
            }
        ]
    }
    first = render(home_doc=home_doc)
    second = render(home_doc=home_doc)
    assert first == second


# ---------------------------------------------------------------------------
# M9: the route reads in-process, never over HTTP; no network import
# ---------------------------------------------------------------------------


def test_home_renders_with_no_server_bound(app):
    # Nothing is listening on cfg["api"]["listen"]; the route still answers
    # because it calls the other handlers in-process (an HTTP fetch would
    # raise a connection error here).
    status, body = home(api.APP.cfg)
    assert status == 200
    assert isinstance(body, str)


def test_home_no_network_imports():
    tree = ast.parse((SRC_DIR / "api_home.py").read_text())
    forbidden = {"urllib", "http", "socket", "subprocess"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in forbidden, f"api_home.py imports {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            root = node.module.split(".")[0]
            assert root not in forbidden, f"api_home.py imports {node.module}"


# ---------------------------------------------------------------------------
# negative control: the full page carries every name once, in section order
# ---------------------------------------------------------------------------


def test_full_page_round_trips():
    home_doc = {
        "flakes": [
            {
                "path": "/home/a/flake-one",
                "declaration": "/home/a/flake-one#helm",
                "profile": None,
                "seats": [],
            },
            {
                "path": "/home/b/flake-two",
                "declaration": "/home/b/flake-two#helm",
                "profile": None,
                "seats": [],
            },
        ]
    }
    seats = {
        "seats": [
            {
                "id": "seat-abc",
                "unit": "seat@seat-abc.service",
                "state": "active",
                "port": 43210,
                "url": "http://127.0.0.1:43210/",
                "exit_code": None,
            }
        ]
    }
    patches = {
        "patches": [
            {
                "file": "patches/dsh/0001-one.patch",
                "package": "dsh",
                "landed_generation": 99,
                "carried_by_next_switch": True,
            }
        ],
        "running_generation": 55,
        "head": "deadbeef",
    }
    status = {"tiles": [{"name": f"tile-{i}", "status": "ok"} for i in range(9)]}
    links = {"feed": "http://127.0.0.1:8080/"}

    page = render(
        home_doc=home_doc, seats=seats, patches=patches, status=status, links=links
    )

    names = (
        ["/home/a/flake-one", "/home/b/flake-two"]
        + ["seat-abc"]
        + ["patches/dsh/0001-one.patch"]
        + [f"tile-{i}" for i in range(9)]
        + ["feed"]
    )
    for name in names:
        assert name in page, name
    positions = [page.index(name) for name in names]
    assert positions == sorted(positions), "sections render out of order"
    assert len(set(positions)) == len(positions), "a name renders more than once"


# ---------------------------------------------------------------------------
# HM7b fix round: carried-first ordering, credentials: "omit", the API host
# ---------------------------------------------------------------------------


def test_carried_row_precedes_landed_row():
    # Interface 1 (HM7b): carried rows come before landed rows. The landed row
    # is listed FIRST in the input, so a render that does not reorder (the
    # gate's mutant `ordered = rows`) leaves landed first and fails the index
    # comparison -- every single-row fixture the gate saw had 0 or 1 rows and
    # could not tell the difference. The generations are swapped: the carried
    # row carries the LOWER landed_generation (10) and the landed row the
    # higher (99), so a sort on generation cannot reproduce carried-first --
    # it would list the 99-generation landed row before the 10-generation
    # carried row and fail the comparison (HM7c's surviving mutant, M7).
    patches = {
        "patches": [
            {
                "file": "landed-patch.patch",
                "package": "dsh",
                "landed_generation": 99,
                "carried_by_next_switch": False,
            },
            {
                "file": "carried-patch.patch",
                "package": "dsh",
                "landed_generation": 10,
                "carried_by_next_switch": True,
            },
        ],
        "running_generation": 55,
        "head": "deadbeef",
    }
    page = render(patches=patches)
    assert page.index("carried-patch.patch") < page.index("landed-patch.patch")


def test_script_requests_with_credentials_omit():
    # Interface 2 (HM7b): the inline script must request `credentials: "omit"`
    # verbatim. The CSP hash cannot pin it -- SCRIPT_HASH is derived from the
    # same SCRIPT, so a test recomputing the expectation the same way passes
    # regardless -- so the guard is the literal string. Mutant "include" fails.
    assert 'credentials: "omit"' in api_home.SCRIPT


def test_get_on_api_port_host_accepted(app):
    # Interface 3 (HM7b): a browser's Host: 127.0.0.1:7710 on the API port is
    # accepted and the home page answers 200 -- the Correction's live
    # interface, exercised nowhere before this test.
    with Server() as srv:
        status, _, _ = http_response(srv.port, "GET", "/", {"Host": "127.0.0.1:7710"})
    assert status == 200
