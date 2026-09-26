"""Helm v1 control renderer: the render.py contract (plan Task 1, K4–K16).

render_control injects the Profile section -- plus, on action-response pages,
the banner -- before </main> of the v0 page, ordered visually ahead of the
v0 grid (K7). D-H1 removed the forms: the page is read-only, so there is no
token, no <form>, no action=, and no Workspaces section. The Profile section
lists each profile as a plain text line (the active one marked), shows the
last switch, and points the operator at the terminal line that performs the
switch behind the desktop password.

The zero-outbound invariant (no <script, no src=, no href="http) is asserted
against adversarial dynamic values too, for the same reason collect.py
escapes "=" as well: escaped text must not be able to reintroduce the
forbidden substring either.
"""

import importlib.util
import inspect
import pathlib
import time

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC_DIR = HERE.parents[2] / "pkgs" / "helm"
_SPEC = importlib.util.spec_from_file_location(
    "render_under_test", SRC_DIR / "render.py"
)
render = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(render)

V0_PAGE = (
    "<!doctype html>"
    '<html lang="en"><head><meta charset="utf-8">'
    '<meta http-equiv="refresh" content="60">'
    "<title>Helm · machine</title></head><body>"
    "<header><h1>Helm · machine</h1></header>"
    '<main class="grid">'
    '<section class="tile ok"><h2>gpu</h2><p>fine</p></section>'
    '<section class="tile fail"><h2>drift</h2><p>≠</p></section>'
    "</main>"
    "</body></html>"
)

CONTROL = {
    "profiles": ["base", "gaming"],
    # D-H1: the workspaces map may still be non-empty (the option is parked,
    # not removed) -- the renderer must ignore it entirely.
    "workspaces": {
        "gaming": {
            "path": "/home/x/flakes/gaming",
            "devShell": "default",
            "basket": None,
        },
        "strategy": {"path": "/home/x/strategy", "devShell": None, "basket": None},
    },
}


@pytest.fixture(autouse=True)
def _pin_local_tz(monkeypatch):
    # _hm now renders LOCAL time (R2), so the serve-time stamp and last-switch
    # lines depend on the process's local zone. Pin it to UTC0 so those
    # literals stay deterministic on the devShell host (America/Chicago) and in
    # the build sandbox (no zoneinfo -> UTC) alike; test_hm_prints_local_time
    # overrides with a POSIX DST string to prove the local-time conversion.
    monkeypatch.setenv("TZ", "UTC0")
    time.tzset()
    yield
    monkeypatch.delenv("TZ", raising=False)
    time.tzset()


def state(**overrides):
    s = {
        "now": "2026-09-03T21:44:00+00:00",
        "active_profile": "base",
        "last_switch": None,
        "switching": None,
    }
    s.update(overrides)
    return s


def render_page(banner=None, st=None, control=None, page=V0_PAGE):
    return render.render_control(
        page,
        control if control is not None else CONTROL,
        st or state(),
        banner=banner,
    )


# ---------------------------------------------------------------------------
# the injection seam: before </main>, v0 page intact, visual order K7
# ---------------------------------------------------------------------------


def test_injects_profile_section_before_closing_main():
    out = render_page()
    assert "gpu" in out and "drift" in out  # the v0 page is intact
    assert out.count("</section>") == 3  # two v0 tiles + the profile section
    assert 0 <= out.find("helm-profile") < out.find("</main>")


def test_visual_order_banner_profile_then_grid():
    # K7: reading order = verb order. The injected <style> carries the grid
    # order that puts the banner (-3) and the Profile (-2) ahead of the v0
    # tiles (which keep the default order 0), and the source order matches
    # within the injected block: banner, then Profile.
    out = render_page(banner={"kind": "ok", "text": "Now running: gaming"})
    assert "order:-3" in out
    assert "order:-2" in out
    assert (
        0
        <= out.find('<div class="helm-banner ok">')
        < out.find('<section class="tile unknown helm-profile">')
    )
    assert "<h2>Profile" in out


def test_fallback_injection_without_a_main_element():
    # Defensive seam: serve.py guarantees </main> (the fallback shell has
    # it), but a missing one must degrade to a valid page, not a crash.
    page = "<!doctype html><html><body><header><h1>Helm</h1></header>x</body></html>"
    out = render_page(page=page)
    assert "helm-profile" in out
    assert ">x<" in out  # the original page content is preserved


# ---------------------------------------------------------------------------
# the page is read-only: no form, no action=, no token, nothing executable
# ---------------------------------------------------------------------------


def test_page_carries_no_form_no_action_no_token():
    # D-H1: whatever control/state hold -- a NON-empty workspaces map and an
    # adversarial active name included -- the output carries no <form, no
    # action=, no token, no <script.
    out = render_page(
        control={"profiles": ["base", "alt"], "workspaces": {"demo": {"path": "/x"}}},
        st=state(active_profile="tok<script>"),
    )
    assert "<form" not in out
    assert "action=" not in out
    assert "token" not in out
    assert "<script" not in out


def test_no_script_src_or_http_href_even_with_adversarial_values():
    control = {
        "profiles": ["base", "<img src=x onerror=y>"],
        "workspaces": {
            "bad": {
                # An escaped value must not reintroduce "src=" either --
                # the same "=" escaping collect.py applies.
                "path": "/x?a=b&c=d<img src=y onerror=z>",
                "devShell": None,
                "basket": None,
            }
        },
    }
    out = render_page(
        control=control, st=state(active_profile='"><script>alert(1)</script>')
    )
    assert "<script" not in out
    assert "src=" not in out
    assert 'href="http' not in out
    assert "<img" not in out


# ---------------------------------------------------------------------------
# the active profile: a plain text list, the active one marked
# ---------------------------------------------------------------------------


def test_profiles_listed_as_text_with_the_active_marked():
    out = render_page()  # active_profile = base
    assert '<span class="helm-profile-name">base</span> ● active' in out
    assert '<span class="helm-profile-name">gaming</span>' in out
    assert '<span class="helm-profile-name">gaming</span> ● active' not in out


def test_workspaces_never_render():
    # D-H1: the workspaces option is parked, not removed -- a NON-empty map
    # must still render nothing (no section marker, no workspace path).
    out = render_page(
        control={"profiles": ["base"], "workspaces": {"demo": {"path": "/x"}}}
    )
    assert "helm-workspaces" not in out
    assert "/x" not in out


def test_unknown_active_profile_renders_neutrally():
    # K14: the reboot/unknown case reads neutrally -- the marker value is
    # printed verbatim, never as a warning or an error.
    out = render_page(st=state(active_profile="unknown"))
    assert "● unknown — active" in out
    assert '<div class="helm-banner' not in out


# ---------------------------------------------------------------------------
# the copy deck, verbatim (K15); the two-clock stamp (K6)
# ---------------------------------------------------------------------------


def test_active_indicator_and_serve_time_stamp():
    out = render_page()
    assert "● base — active" in out
    assert "live · 21:44" in out


def test_last_switch_lines():
    ok = state(
        last_switch={
            "from": "base",
            "to": "gaming",
            "result": "ok",
            "at": "2026-09-03T21:03:00+00:00",
        }
    )
    assert "Last switch: base → gaming · ok · 21:03" in render_page(st=ok)
    fail = state(
        last_switch={
            "from": "base",
            "to": "gaming",
            "result": "fail",
            "at": "2026-09-03T21:03:00+00:00",
        }
    )
    assert "Last switch: base → gaming · failed — see journal" in render_page(st=fail)
    switching = state(
        switching={
            "from": "base",
            "to": "gaming",
            "started": "2026-09-03T21:44:00+00:00",
        }
    )
    assert "Switching to gaming… (started 21:44)" in render_page(st=switching)
    assert "No switches since boot." in render_page()


def test_note_names_the_terminal_line():
    out = render_page()
    assert "systemctl start helm-switch@<profile>.service" in out


def test_names_verbatim_lowercase():
    out = render_page()
    assert "base" in out and "gaming" in out
    assert "Base" not in out and "Gaming" not in out
    assert "Strategy" not in out


# ---------------------------------------------------------------------------
# palette inheritance (K8/K9)
# ---------------------------------------------------------------------------


def test_profile_section_border_follows_last_switch_state():
    assert '<section class="tile unknown helm-profile">' in render_page()
    ok = state(
        last_switch={
            "from": "base",
            "to": "gaming",
            "result": "ok",
            "at": "2026-09-03T21:03:00+00:00",
        }
    )
    assert '<section class="tile ok helm-profile">' in render_page(st=ok)
    fail = state(
        last_switch={
            "from": "base",
            "to": "gaming",
            "result": "fail",
            "at": "2026-09-03T21:03:00+00:00",
        }
    )
    assert '<section class="tile fail helm-profile">' in render_page(st=fail)
    switching = state(
        switching={
            "from": "base",
            "to": "gaming",
            "started": "2026-09-03T21:44:00+00:00",
        }
    )
    assert '<section class="tile warn helm-profile">' in render_page(st=switching)


# ---------------------------------------------------------------------------
# the banner component (K12)
# ---------------------------------------------------------------------------


def test_banner_absent_on_the_passive_page():
    # The banner is action-response-only (K12): the passive dashboard
    # carries no banner element (the <style> may still define the class).
    assert '<div class="helm-banner' not in render_page()


def test_banner_renders_kind_and_text():
    out = render_page(banner={"kind": "ok", "text": "Now running: gaming"})
    assert "helm-banner ok" in out
    assert "Now running: gaming" in out
    assert "dismiss" not in out.lower()  # K12: no dismiss control


def test_banner_failure_carries_the_command_as_inline_code():
    out = render.render_banner(
        {
            "kind": "fail",
            "text": "Switch to gaming did not finish — the machine is still on base.",
            "command": "journalctl -u helm-switch@gaming.service",
        }
    )
    assert "<code>journalctl -u helm-switch@gaming.service</code>" in out
    assert "<a " not in out and 'href="http' not in out  # code text, never a link
    assert "<script" not in out and "src=" not in out


def test_banner_busy_kind_and_empty_banner():
    out = render.render_banner(
        {
            "kind": "busy",
            "text": "A switch is already in progress. Wait for it to finish, then reload.",
        }
    )
    assert "helm-banner busy" in out
    assert "A switch is already in progress" in out
    assert render.render_banner(None) == ""


# ---------------------------------------------------------------------------
# the signature (D-H1) and R2: the Profile header names its verdict in text
# ---------------------------------------------------------------------------


def test_render_control_takes_no_token_argument():
    # D-H1: no token flows into the renderer any more -- the page is
    # read-only. Leaving the parameter would let a stale caller keep passing
    # one, so the signature itself is the contract.
    params = list(inspect.signature(render.render_control).parameters)
    assert params == ["status_html", "control", "state", "banner"]


def test_profile_header_names_its_verdict_in_text():
    state = {
        "active_profile": "base",
        "now": "2026-09-03T21:44:00+00:00",
        "last_switch": {
            "from": "gaming",
            "to": "base",
            "result": "ok",
            "at": "2026-09-03T20:00:00+00:00",
        },
        "switching": None,
    }
    out = render.render_control(V0_PAGE, CONTROL, state)
    assert '<h2>Profile <span class="verdict">OK</span></h2>' in out


def test_hm_prints_local_time(monkeypatch):
    monkeypatch.setenv("TZ", "CST6CDT,M3.2.0,M11.1.0")
    time.tzset()
    try:
        assert render._hm("2026-09-03T21:44:00+00:00") == "16:44"
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()
