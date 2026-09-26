"""Pure helpers for the helm-home raise-key probe verdict (HH1).

No gi, no dbus, no I/O: the unit tests own every branch here, which is why the
verdict logic lives in this file rather than inside the GTK probe itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class BindResult:
    """The outcome of a BindShortcuts response.

    ``bound`` is True only when the response code is 0 *and* the returned
    ``shortcuts`` subset holds an entry whose id is ``raise``.
    """

    bound: bool
    trigger_description: str | None
    response: int


def parse_bind_response(response: int, results: dict) -> BindResult:
    """Parse a BindShortcuts ``Response(code, results)`` into a BindResult.

    The portal's response ``shortcuts`` is "a subset of the shortcuts which
    were passed in (this includes the set of all shortcuts and the empty
    set)". Each entry is ``(id, {description, trigger_description})``; GLib's
    JSON-ish variants unpack to lists, so a two-item list is accepted too.
    """
    shortcuts = results.get("shortcuts") or []
    trigger_description = None
    found = None
    for entry in shortcuts:
        if entry[0] == "raise":
            found = entry
            break
    bound = response == 0 and found is not None
    if bound:
        trigger_description = found[1].get("trigger_description")
    return BindResult(
        bound=bound,
        trigger_description=trigger_description,
        response=response,
    )


def verdict(bound: bool, activations: int, focus_regained: int) -> str:
    """Reduce the probe's three facts to one of portal|fallback|unbound.

    ``portal`` means the shortcut was bound and every activation regained
    focus; ``fallback`` means bound but not every activation regained focus
    (or no activation happened); ``unbound`` means the portal refused or the
    session never bound.
    """
    if not bound:
        return "unbound"
    if activations >= 1 and focus_regained == activations:
        return "portal"
    return "fallback"


def _rfc3339(now: datetime) -> str:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def record(
    bound_result: BindResult,
    activations: int,
    focus_regained: int,
    now: datetime,
) -> dict:
    """Build the probe's verdict record with exactly the contract's keys."""
    return {
        "schema": 1,
        "ts": _rfc3339(now),
        "bind_response": bound_result.response,
        "bound": bound_result.bound,
        "trigger_description": bound_result.trigger_description,
        "activations": activations,
        "focus_regained": focus_regained,
        "verdict": verdict(bound_result.bound, activations, focus_regained),
    }
