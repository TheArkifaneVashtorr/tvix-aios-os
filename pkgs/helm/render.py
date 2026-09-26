"""Helm v1 control renderer — the serve-time injection behind the page.

Consumed by serve.py (plan Task 1, consolidated D10; D-H1): render_control
reads the marker and the journal state fresh on every call (the caller
re-reads them per request; nothing is cached here) and injects the Profile
section into the v0 page before </main>; render_banner is the
action-response banner (K12).

D-H1 (the switch moves behind the desktop password): the page is read-only.
There is no token, no <form, no action=, and no Workspaces section -- the
Profile section lists each profile as a plain text line (the active one
marked), shows the last switch, and points the operator at the terminal
line that performs the switch behind the password. control.workspaces is
ignored entirely (the option stays parked in the module, its launcher and
tests intact).

Every string that reaches the output passes through the same escaping as
collect.py's page renderer -- including "=" (escaped as &#61;), so no
escaped value can ever reintroduce the "src=" substring the zero-outbound
invariant (no <script, no src=, no href="http) forbids, even inside
escaped free text.

Visual language (Kimi, docs/superpowers/specs/2026-09-03-helm-v1-product-ux-
decisions.md): strict inheritance of v0's palette and tile grammar, no
fifth color (K9); the injection seam is before </main> but the reading
order is verb order -- banner, Profile, then the v0 grid -- via CSS grid
order (K7); the copy deck verbatim, flat, present tense (K15).
"""

from __future__ import annotations

import datetime
import html

# K9: v0's palette exactly — ok #2e7d32, warn #ed6c02, fail #c62828,
# unknown #616161 — and its tile grammar (left status border, radius,
# shadow, dark variants). No fifth color.
_STYLE = """
  .helm-banner { order:-3; grid-column: 1 / -1; border-radius: 0.5rem;
                 padding: 0.8rem 1rem; border-left: 0.4rem solid #616161;
                 background: #fff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15); }
  .helm-banner.ok { border-left-color: #2e7d32; }
  .helm-banner.fail { border-left-color: #c62828; }
  .helm-banner.busy { border-left-color: #ed6c02; }
  .helm-banner p { margin: 0; }
  .helm-banner code { display: inline-block; margin-top: 0.3rem;
                      font-size: 0.8rem; background: #f0f0f0;
                      padding: 0.25rem 0.4rem; border-radius: 0.3rem; }
  .helm-profile { order:-2; }
  .helm-live { color: #555; font-size: 0.8rem; margin: 0 0 0.4rem 0; }
  .helm-active { font-weight: 600; }
  .helm-profiles { margin: 0 0 0.5rem 0; }
  .helm-profile-name { font-weight: 600; }
  .helm-last { margin: 0 0 0.5rem 0; }
  .helm-note { color: #555; font-size: 0.85rem; margin: 0; }
  @media (prefers-color-scheme: dark) {
    .helm-banner { background: #1e1e1e; box-shadow: none; }
    .helm-banner code { background: #2a2a2a; }
    .helm-live, .helm-note { color: #aaa; }
  }
""".strip()


def _esc(s) -> str:
    """collect.py's escaping convention: html.escape with quotes, plus "="
    escaped so no escaped value can reintroduce the "src=" substring."""
    return html.escape(str(s), quote=True).replace("=", "&#61;")


def _hm(iso) -> str:
    """'16:44' LOCAL time from an iso timestamp — the K6 live· stamp and
    K15's last-switch lines. Anything unparsable passes through as-is."""
    try:
        return datetime.datetime.fromisoformat(str(iso)).astimezone().strftime("%H:%M")
    except (ValueError, TypeError):
        return str(iso)


def render_banner(banner) -> str:
    """The K12 banner: full-width, directly under the header, color =
    outcome, flat statement text, no dismiss control. The command string
    (when present) is copyable inline code — the page is not a terminal,
    and it is never a link (no href anywhere in the page)."""
    if not banner:
        return ""
    kind = str(banner.get("kind", "fail"))
    if kind not in ("ok", "fail", "busy"):
        kind = "fail"
    parts = [
        f'<div class="helm-banner {kind}">',
        f"<p>{_esc(banner.get('text', ''))}</p>",
    ]
    if banner.get("command"):
        parts.append(f"<code>{_esc(banner['command'])}</code>")
    parts.append("</div>")
    return "".join(parts)


def _profile_lines(profiles, active):
    """One plain text line per profile (D-H1): a
    <span class="helm-profile-name">name</span>, the active one carrying a
    trailing ● active marker."""
    return [
        f'<span class="helm-profile-name">{_esc(name)}</span>'
        f"{' ● active' if name == active else ''}"
        for name in profiles
    ]


def render_control(status_html, control, state, banner=None) -> str:
    """Inject the Profile section -- and, on action-response pages, the
    banner -- into the v0 page before </main> (falling back to </body>, then
    to a plain append, so a page without the seam degrades instead of
    crashing). The active profile and the last switch come from `state`,
    which serve.py re-reads on every request (D10). D-H1: no token argument,
    no forms, and control.workspaces is ignored."""
    control = control or {}
    state = state or {}
    profiles = control.get("profiles") or []
    active = str(state.get("active_profile", "unknown"))
    switching = state.get("switching") or None
    last = state.get("last_switch") or None

    # K9: the Profile section's status border is the last-switch state —
    # warn while a switch is running, ok/fail from the last result,
    # unknown before any switch this boot.
    if switching:
        status_class = "warn"
        last_line = (
            f"Switching to {_esc(switching.get('to', ''))}… "
            f"(started {_hm(switching.get('started', ''))})"
        )
    elif last:
        status_class = "ok" if last.get("result") == "ok" else "fail"
        head = f"Last switch: {_esc(last.get('from', ''))} → {_esc(last.get('to', ''))}"
        if last.get("result") == "ok":
            last_line = f"{head} · ok · {_hm(last.get('at', ''))}"
        else:
            last_line = f"{head} · failed — see journal"
    else:
        status_class = "unknown"
        last_line = "No switches since boot."

    # D-H1 copy deck: the switch happens in Helm Home behind the desktop
    # password; until it lands, the operator runs the terminal line under
    # the system's own password prompt. Written verbatim (the <profile>
    # placeholder is literal, not escaped, so R6's terminal line matches).
    profile_lines_html = "<br>".join(_profile_lines(profiles, active))
    profile_section = (
        f'<section class="tile {status_class} helm-profile">'
        f'<h2>Profile <span class="verdict">{status_class.upper()}</span></h2>'
        f'<p class="helm-live">live · {_hm(state.get("now", ""))}</p>'
        f'<p class="helm-active">● {_esc(active)} — active</p>'
        f'<p class="helm-profiles">{profile_lines_html}</p>'
        f'<p class="helm-last">{last_line}</p>'
        '<p class="helm-note">Switching happens in Helm Home behind your '
        "password. Until it lands: systemctl start helm-switch@<profile>.service "
        "in a terminal (the system asks for your password).</p>"
        "</section>"
    )

    injected = f"<style>{_STYLE}</style>{render_banner(banner)}{profile_section}"
    if "</main>" in status_html:
        return status_html.replace("</main>", injected + "</main>", 1)
    if "</body>" in status_html:
        return status_html.replace("</body>", injected + "</body>", 1)
    return status_html + injected
