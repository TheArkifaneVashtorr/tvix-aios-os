"""Helm v1 control renderer — the serve-time injection behind the page.

Consumed by serve.py (plan Task 1, consolidated D10): render_control reads
the marker and the journal state fresh on every call (the caller re-reads
them per request; nothing is cached here) and injects the two control
sections into the v0 page before </main>; render_banner is the
action-response banner (K12).

Every string that reaches the output passes through the same escaping as
collect.py's page renderer — including "=" (escaped as &#61;), so no
escaped value can ever reintroduce the "src=" substring the zero-outbound
invariant (no <script, no src=, no href="http) forbids, even inside
escaped free text.

Visual language (Kimi, docs/superpowers/specs/2026-09-03-helm-v1-product-ux-
decisions.md): strict inheritance of v0's palette and tile grammar, no
fifth color (K9); the injection seam is before </main> but the reading
order is verb order — banner, Profile, Workspaces, then the v0 grid — via
CSS grid order (K7); two tiers of action, filled profile buttons and
outlined open buttons (K8); the active profile's button is render-disabled
while the backend allowlist stays complete (K11); the copy deck verbatim,
flat, present tense (K15).
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
  .helm-workspaces { order:-1; }
  .helm-live { color: #555; font-size: 0.8rem; margin: 0 0 0.4rem 0; }
  .helm-active { font-weight: 600; }
  .helm-actions { display: flex; flex-wrap: wrap; gap: 0.5rem;
                  margin: 0 0 0.6rem 0; }
  .helm-btn { font: inherit; font-size: 0.95rem; border: none;
              cursor: pointer; border-radius: 0.3rem; padding: 0.35rem 0.9rem;
              background: #2e7d32; color: #fff; }
  .helm-btn[disabled] { opacity: 0.55; cursor: default; }
  .helm-btn-open { font: inherit; font-size: 0.9rem; cursor: pointer;
                   border-radius: 0.3rem; padding: 0.25rem 0.7rem;
                   background: transparent; color: inherit;
                   border: 0.1rem solid #616161; }
  .helm-ws { margin: 0 0 0.5rem 0; }
  .helm-ws-name { font-weight: 600; }
  .helm-ws-path { color: #555; font-size: 0.8rem; margin-left: 0.4rem; }
  .helm-ws form { display: inline-block; margin-left: 0.6rem; }
  .helm-last { margin: 0 0 0.5rem 0; }
  .helm-note { color: #555; font-size: 0.85rem; margin: 0; }
  .helm-on { font-weight: 400; opacity: 0.8; }
  @media (prefers-color-scheme: dark) {
    .helm-banner { background: #1e1e1e; box-shadow: none; }
    .helm-banner code { background: #2a2a2a; }
    .helm-live, .helm-ws-path, .helm-note { color: #aaa; }
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


def _profile_forms(profiles, active, esc_token):
    """One form per profile, whatever the active one is (K11: the backend
    allowlist stays complete; only the button is render-disabled)."""
    forms = []
    for name in profiles:
        esc_name = _esc(name)
        if name == active:
            button = (
                f'<button type="submit" class="helm-btn" name="profile" '
                f'value="{esc_name}" disabled>{esc_name}'
                f'<span class="helm-on"> ● active</span></button>'
            )
        else:
            button = (
                f'<button type="submit" class="helm-btn" name="profile" '
                f'value="{esc_name}">{esc_name}</button>'
            )
        forms.append(
            f'<form method="post" action="/action/switch">'
            f'<input type="hidden" name="token" value="{esc_token}">'
            f"{button}</form>"
        )
    return "".join(forms)


def _workspace_rows(workspaces, esc_token):
    rows = []
    for name, ws in workspaces.items():
        esc_name = _esc(name)
        esc_path = _esc((ws or {}).get("path", ""))
        rows.append(
            f'<div class="helm-ws">'
            f'<span class="helm-ws-name">{esc_name}</span>'
            f'<span class="helm-ws-path">{esc_path}</span>'
            f'<form method="post" action="/action/open">'
            f'<input type="hidden" name="token" value="{esc_token}">'
            f'<button type="submit" class="helm-btn-open" name="flake" '
            f'value="{esc_name}">Open</button>'
            f"</form></div>"
        )
    return "".join(rows)


def render_control(status_html, control, state, token, banner=None) -> str:
    """Inject the control sections — and, on action-response pages, the
    banner — into the v0 page before </main> (falling back to </body>, then
    to a plain append, so a page without the seam degrades instead of
    crashing). The active profile and the last switch come from `state`,
    which serve.py re-reads on every request (D10)."""
    control = control or {}
    state = state or {}
    esc_token = _esc(token)
    profiles = control.get("profiles") or []
    workspaces = control.get("workspaces") or {}
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

    profile_section = (
        f'<section class="tile {status_class} helm-profile">'
        f'<h2>Profile <span class="verdict">{status_class.upper()}</span></h2>'
        f'<p class="helm-live">live · {_hm(state.get("now", ""))}</p>'
        f'<p class="helm-active">● {_esc(active)} — active</p>'
        f'<div class="helm-actions">{_profile_forms(profiles, active, esc_token)}</div>'
        f'<p class="helm-last">{last_line}</p>'
        '<p class="helm-note">Switches apply to the running machine only. '
        "A restart always returns to base.</p>"
        "</section>"
    )

    # K13/K9: the basket ceremony stays in the terminal; the page only
    # forewarns, and no workspace carries basket state into this renderer
    # yet — so the Workspaces border reads ok today. When basket state
    # reaches the state dict, a not-mounted basket flips this to warn.
    #
    # H4: operator decision 2026-09-04 — the workspace buttons leave the
    # live page until Helm Home ships. An empty workspaces map must hide the
    # section entirely (no heading, no open forms), not render an empty
    # section — the module capability (the launcher, its tests) stays intact;
    # only the rendered page changes.
    if workspaces:
        workspaces_section = (
            '<section class="tile ok helm-workspaces">'
            "<h2>Workspaces</h2>"
            f'<p class="helm-live">live · {_hm(state.get("now", ""))}</p>'
            f"{_workspace_rows(workspaces, esc_token)}"
            "</section>"
        )
    else:
        workspaces_section = ""

    injected = (
        f"<style>{_STYLE}</style>"
        f"{render_banner(banner)}"
        f"{profile_section}"
        f"{workspaces_section}"
    )
    if "</main>" in status_html:
        return status_html.replace("</main>", injected + "</main>", 1)
    if "</body>" in status_html:
        return status_html.replace("</body>", injected + "</body>", 1)
    return status_html + injected
