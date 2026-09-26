"""Helm API route module — the web home page on `GET /`.

One screen for every datum the API exposes: the declared flakes, the session
list (with the seat Start/Stop/Attach buttons), the patch queue, the
collector's status tiles and the operator's links. Rendered in-process — each
section calls its own route handler with an `api.Request`, never a socket —
so the page answers even when one domain is down (that section renders
``unavailable: <error>`` and the page still answers ``200``).

Security posture: no form element, no profile-change action, no credential;
the single inline script posts to the three seat routes (start, stop, attach)
with ``credentials: "omit"`` and reloads, and to HM8's engagement route with
the two counts-only beacons (opens on load, dwell_s on pagehide, never
feed_likes), and the Content-Security-Policy pins the script's sha256 so an
edit without a hash update fails the header check. Every dynamic value is escaped through
``html.escape``, and ``render_home`` is pure — same inputs, same bytes, no
timestamp — so the CSP hash is computed once at import.
"""

from __future__ import annotations

import base64
import hashlib
import html

# The one inline script (interface 1). It posts to HM5's three seat routes —
# start (POST /v1/seats), stop (POST /v1/seats/<id>/stop) and attach
# (POST /v1/seats/<id>/attach) — with credentials omitted, then reloads, and
# it posts HM8's two engagement beacons (opens on load, dwell_s on pagehide)
# to POST /v1/engage via `navigator.sendBeacon` (which sends text/plain).
# Kept ES5-safe; `test_only_seat_routes_in_script` admits exactly these four
# paths and nothing else.
SCRIPT = """\
(function () {
  function post(path, body) {
    fetch(path, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {})
    }).then(function () {
      window.location.reload();
    });
  }
  function engage(counter, n) {
    navigator.sendBeacon("/v1/engage", JSON.stringify({
      counter: counter, n: n, surface: "home"
    }));
  }
  document.addEventListener("click", function (event) {
    var el = event.target;
    var action = el && el.getAttribute ? el.getAttribute("data-action") : null;
    var id = el && el.getAttribute ? el.getAttribute("data-seat-id") : null;
    if (action === "stop") {
      post("/v1/seats/" + id + "/stop");
    } else if (action === "attach") {
      post("/v1/seats/" + id + "/attach");
    }
  });
  document.addEventListener("change", function (event) {
    var el = event.target;
    if (el && el.getAttribute && el.getAttribute("data-action") === "start") {
      post("/v1/seats", { mode: el.value });
    }
  });
  engage("opens", 1);
  var helmStarted = Date.now();
  window.addEventListener("pagehide", function () {
    var dwell = Math.floor((Date.now() - helmStarted) / 1000);
    if (dwell >= 1) {
      engage("dwell_s", dwell);
    }
  });
})();
"""

# The CSP's script-src hash is the base64 sha256 of the exact script bytes
# (interface 5: computed once at import; render_home never re-hashes).
SCRIPT_HASH = base64.b64encode(hashlib.sha256(SCRIPT.encode("utf-8")).digest()).decode(
    "ascii"
)

CSP = (
    "default-src 'none'; "
    f"script-src 'sha256-{SCRIPT_HASH}'; "
    "style-src 'unsafe-inline'; "
    "connect-src 'self'; "
    "form-action 'none'"
)

# HM6's carried flag on each patch row, written whole: api_record.py emits
# carried_by_next_switch (interface 1 impl) and the sort key below reuses it.
_CARRIED_KEY = "carried_by_next_switch"


def routes():
    # Deferred: api.py's discover() imports this module during its own import,
    # so a top-level `import api` would be circular. Setting HTML_CSP here is
    # how the generic HTML responder (api.py) learns the header this page
    # must carry.
    import api

    api.HTML_CSP = CSP
    return [("GET", "/", home)]


def _read(handler, path, cfg):
    """Call one route handler in-process; ``(body, error)``.

    The handler is invoked exactly as the dispatcher would — with an
    ``api.Request`` for that route's path — never over a socket (interface 6).
    A raised exception or a non-200 status becomes the ``error`` string the
    section renders as ``unavailable: <error>``.
    """
    import api

    request = api.Request(
        method="GET", path=path, params={}, headers={}, body=b"", origin=None
    )
    try:
        status, body = handler(cfg, request)
    except Exception as exc:  # noqa: BLE001 - a domain failure is a section, never a 500
        return None, f"{type(exc).__name__}: {exc}"
    if status != 200:
        if isinstance(body, dict):
            err = body.get("error", body)
        else:
            err = body
        return None, str(err)
    return body, None


def home(cfg, request):
    """GET / — read the four domains in-process and render the page."""
    import api_record
    import api_seats
    import api_state

    home_doc, home_err = _read(api_state._home_handler, "/v1/home", cfg)
    seats, seats_err = _read(api_seats.list_seats, "/v1/seats", cfg)
    patches, patches_err = _read(api_record._patches_handler, "/v1/patches", cfg)
    status, status_err = _read(api_state._status_handler, "/v1/status", cfg)

    links = ((cfg.get("api") or {}).get("links")) or {}

    return 200, render_home(
        cfg,
        home_doc if home_err is None else home_err,
        seats if seats_err is None else seats_err,
        patches if patches_err is None else patches_err,
        status if status_err is None else status_err,
        links,
    )


def _esc(value):
    return html.escape(str(value), quote=True)


def _unavailable(reason):
    return f'<p class="unavailable">unavailable: {_esc(reason)}</p>'


def _section(section_id, title, body):
    return f'<section id="{section_id}"><h2>{title}</h2>{body}</section>'


def _flakes_section(home_doc):
    if isinstance(home_doc, str):
        return _section("flakes", "Flakes", _unavailable(home_doc))
    flakes = home_doc.get("flakes", []) if isinstance(home_doc, dict) else []
    if not flakes:
        return _section("flakes", "Flakes", "<p>No flakes declared</p>")
    cards = "".join(
        f'<article class="flake"><code>{_esc(f.get("path", ""))}</code> '
        f"<span>{_esc(f.get('declaration', ''))}</span></article>"
        for f in flakes
    )
    return _section("flakes", "Flakes", cards)


def _seats_section(seats):
    if isinstance(seats, str):
        return _section("seats", "Sessions", _unavailable(seats))
    rows = seats.get("seats", []) if isinstance(seats, dict) else []
    html_rows = []
    for seat in rows:
        sid = _esc(seat.get("id", ""))
        state = _esc(seat.get("state", "unknown"))
        url = seat.get("url")
        url_cell = (
            f'<td><a href="{_esc(url)}">{_esc(url)}</a></td>' if url else "<td></td>"
        )
        html_rows.append(
            "<tr>"
            f"<td>{sid}</td><td>{state}</td>{url_cell}"
            "<td>"
            f'<select data-action="start" data-seat-id="{sid}">'
            '<option value="web">web</option>'
            '<option value="drive">drive</option>'
            "</select>"
            f'<button type="button" data-action="stop" data-seat-id="{sid}">Stop</button>'
            f'<button type="button" data-action="attach" data-seat-id="{sid}">Attach</button>'
            "</td>"
            "</tr>"
        )
    body = (
        "".join(html_rows) if html_rows else '<tr><td colspan="4">No sessions</td></tr>'
    )
    return _section("seats", "Sessions", f"<table>{body}</table>")


def _patches_section(patches):
    if isinstance(patches, str):
        return _section("patches", "Patch queue", _unavailable(patches))
    rows = patches.get("patches", []) if isinstance(patches, dict) else []
    if not rows:
        return _section("patches", "Patch queue", "<p>No patches</p>")
    ordered = sorted(rows, key=lambda r: not r.get(_CARRIED_KEY, False))
    html_rows = "".join(
        f"<tr><td>{_esc(r.get('file', ''))}</td>"
        f"<td>{'carried' if r.get(_CARRIED_KEY) else 'landed'}</td></tr>"
        for r in ordered
    )
    return _section("patches", "Patch queue", f"<table>{html_rows}</table>")


def _status_section(status):
    if isinstance(status, str):
        return _section("status", "Status", _unavailable(status))
    tiles = status.get("tiles", []) if isinstance(status, dict) else []
    if not tiles:
        return _section("status", "Status", "<p>No status tiles</p>")
    lines = "".join(
        f'<div class="tile">{_esc(t.get("name", ""))}: {_esc(t.get("status", ""))}</div>'
        for t in tiles
    )
    return _section("status", "Status", lines)


def _links_section(links):
    if isinstance(links, str):
        return _section("links", "Links", _unavailable(links))
    items = links if isinstance(links, dict) else {}
    if not items:
        return _section("links", "Links", "<p>No links</p>")
    lis = "".join(
        f'<li><a href="{_esc(url)}">{_esc(label)}</a></li>'
        for label, url in items.items()
    )
    return _section("links", "Links", f"<ul>{lis}</ul>")


def render_home(cfg, home_doc, seats, patches, status, links):
    """Render the whole page (interface 2): sections in order — flakes, the
    session list, the patch queue (carried rows first), one status line per
    tile, and the links list — then the single inline script. Pure: the same
    six inputs yield the same bytes, so the caller may cache the result."""
    return "".join(
        [
            "<!doctype html>",
            '<html lang="en"><head><meta charset="utf-8"><title>Helm</title></head><body>',
            "<header><h1>Helm</h1></header><main>",
            _flakes_section(home_doc),
            _seats_section(seats),
            _patches_section(patches),
            _status_section(status),
            _links_section(links),
            "</main>",
            "<script>",
            SCRIPT,
            "</script>",
            "</body></html>",
        ]
    )
