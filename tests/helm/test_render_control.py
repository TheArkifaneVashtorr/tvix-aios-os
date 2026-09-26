"""Helm v1 control renderer: the render.py contract (plan Task 1, K4–K16).

render_control injects two sections -- Profile and Workspaces -- plus, on
action-response pages, the banner -- before </main> of the v0 page, ordered
visually ahead of the v0 grid (K7). The tests pin Kimi's product decisions
(docs/superpowers/specs/2026-09-03-helm-v1-product-ux-decisions.md): the
forms-only page with the token embedded (K4), strict palette/tile-grammar
inheritance (K9), verbatim lowercase names (K10), the render-disabled
active button over a complete allowlist (K11), the banner component (K12),
the two-clock disclosure (K6) and the copy deck verbatim (K15).

The zero-outbound invariant (no <script, no src=, no href="http) is asserted
against adversarial dynamic values too, for the same reason collect.py
escapes "=" as well: escaped text must not be able to reintroduce the
forbidden substring either.
"""

import importlib.util
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

TOKEN = "t" * 64

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
        TOKEN,
        banner=banner,
    )


def forms_of(out, value, action):
    """The <form> chunks posting to `action` whose control carries `value`.

    Scoped by action: a workspace named like a profile would otherwise
    match the profile's forms too.
    """
    return [
        f
        for f in out.split("<form")[1:]
        if f'action="{action}"' in f and f'value="{value}"' in f
    ]


# ---------------------------------------------------------------------------
# the injection seam: before </main>, v0 page intact, visual order K7
# ---------------------------------------------------------------------------


def test_injects_both_sections_before_closing_main():
    out = render_page()
    assert "gpu" in out and "drift" in out  # the v0 page is intact
    assert out.count("</section>") == 4  # two v0 tiles + two sections
    assert 0 <= out.find("helm-profile") < out.find("</main>")
    assert 0 <= out.find("helm-workspaces") < out.find("</main>")


def test_visual_order_banner_profile_workspaces_then_grid():
    # K7: reading order = verb order. The injected <style> carries the grid
    # order that puts banner (-3), Profile (-2), Workspaces (-1) ahead of
    # the v0 tiles, and the source order matches within the injected block.
    out = render_page(banner={"kind": "ok", "text": "Now running: gaming"})
    assert "order:-3" in out
    assert "order:-2" in out
    assert "order:-1" in out
    assert (
        out.find("helm-banner") < out.find("helm-profile") < out.find("helm-workspaces")
    )
    assert "<h2>Profile" in out and "<h2>Workspaces</h2>" in out


def test_fallback_injection_without_a_main_element():
    # Defensive seam: serve.py guarantees </main> (the fallback shell has
    # it), but a missing one must degrade to a valid page, not a crash.
    page = "<!doctype html><html><body><header><h1>Helm</h1></header>x</body></html>"
    out = render_page(page=page)
    assert "helm-profile" in out and "helm-workspaces" in out
    assert ">x<" in out  # the original page content is preserved


# ---------------------------------------------------------------------------
# the forms: one per profile, one per workspace, token embedded (K4)
# ---------------------------------------------------------------------------


def test_one_form_per_profile_and_workspace():
    out = render_page()
    assert out.count('action="/action/switch"') == 2
    assert out.count('action="/action/open"') == 2
    assert out.count('method="post"') == 4


def test_token_embedded_in_every_form():
    out = render_page()
    assert out.count(f'value="{TOKEN}"') == 4


def test_no_script_src_or_http_href_even_with_adversarial_values():
    control = {
        "profiles": ["base"],
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
    out = render_page(control=control)
    assert "<script" not in out
    assert "src=" not in out
    assert 'href="http' not in out
    assert "<img" not in out


# ---------------------------------------------------------------------------
# the active profile: render-disabled button over a complete allowlist (K11)
# ---------------------------------------------------------------------------


def test_active_profile_button_disabled_others_not():
    out = render_page()  # active_profile = base
    base_form = forms_of(out, "base", "/action/switch")
    assert len(base_form) == 1
    assert "disabled" in base_form[0]
    assert "● active" in base_form[0]
    gaming_form = forms_of(out, "gaming", "/action/switch")
    assert len(gaming_form) == 1
    assert "disabled" not in gaming_form[0]


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


def test_note_under_profiles():
    out = render_page()
    assert (
        "Switches apply to the running machine only. A restart always returns to base."
        in out
    )


def test_names_verbatim_lowercase():
    out = render_page()
    assert "gaming" in out and "strategy" in out
    assert "Gaming" not in out and "Strategy" not in out


def test_workspace_rows_show_paths():
    out = render_page()
    assert "/home/x/flakes/gaming" in out
    assert "/home/x/strategy" in out


def test_empty_workspaces_hides_the_workspaces_section():
    # H4: operator decision 2026-09-04 -- the workspace buttons leave the
    # live page until Helm Home ships. An empty workspaces map must hide the
    # heading and forms entirely, not render an empty section (the Profile
    # section still renders; only Workspaces disappears).
    control = {"profiles": ["base"], "workspaces": {}}
    out = render_page(control=control)
    assert "<h2>Workspaces</h2>" not in out
    assert '<section class="tile ok helm-workspaces">' not in out
    assert 'action="/action/open"' not in out
    # The Profile section is unchanged -- only the Workspaces heading/forms go.
    assert "<h2>Profile" in out


# ---------------------------------------------------------------------------
# palette inheritance and the two button tiers (K8/K9)
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


def test_two_button_tiers_filled_switch_outline_open():
    out = render_page()
    assert out.count('class="helm-btn"') == 2  # profile buttons: filled (K8)
    assert out.count('class="helm-btn-open"') == 2  # open buttons: outline (K8)


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
# R2: the Profile header names its verdict in text; local time (two-clock K6)
# ---------------------------------------------------------------------------


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
    out = render.render_control(V0_PAGE, CONTROL, state, TOKEN)
    assert '<h2>Profile <span class="verdict">OK</span></h2>' in out


def test_hm_prints_local_time(monkeypatch):
    monkeypatch.setenv("TZ", "CST6CDT,M3.2.0,M11.1.0")
    time.tzset()
    try:
        assert render._hm("2026-09-03T21:44:00+00:00") == "16:44"
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()
