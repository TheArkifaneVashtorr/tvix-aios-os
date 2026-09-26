"""The xdg-desktop-portal GlobalShortcuts client (HH1).

Stdlib only except for the injected ``bus`` object, which exposes
``call(interface, method, args) -> object path`` and
``subscribe(interface, signal, path, handler)``. probe.py (and app.py, later)
pass a ``Gio.DBusConnection`` adapter; the unit tests pass a recording fake.

The flow matches the portal's GlobalShortcuts interface: CreateSession returns
an object handle and fires ``Response(u, a{sv})`` on it; BindShortcuts does the
same on its own handle; ``Activated(o session_handle, s shortcut_id, t, a{sv})``
fires on the session object.

The arguments this module hands to ``bus.call`` are plain Python values; the
caller's D-Bus adapter is responsible for boxing them to the method's GVariant
signature (``dbus_signature_for``) first — every ``a{sv}`` value must already
be a ``GLib.Variant`` (probe.py's ``_box`` does this), because a raw
str/bool/int inside ``a{sv}`` raises ``TypeError: Expected GLib.Variant``.
"""

from __future__ import annotations

from probe_result import BindResult, parse_bind_response

INTERFACE = "org.freedesktop.portal.GlobalShortcuts"

_counter = 0


def request_tokens(counter: int) -> tuple[str, str]:
    """Return the (handle_token, session_handle_token) pair for ``counter``.

    Both are valid D-Bus object-path elements (``[A-Za-z0-9_]+``).
    """
    return (f"helm_home_{counter}", f"helm_home_{counter}_s")


def shortcut_request(preferred_trigger: str | None = None) -> list[tuple[str, dict]]:
    """Return the single raise shortcut request.

    With ``preferred_trigger=None`` the entry carries ``description`` only.
    """
    entry: dict = {"description": "Raise Helm Home"}
    if preferred_trigger is not None:
        entry["preferred_trigger"] = preferred_trigger
    return [("raise", entry)]


def dbus_signature_for(method: str) -> str:
    """Return the GVariant type string for a portal method's arguments.

    ``CreateSession`` takes one ``a{sv}`` of options; ``BindShortcuts`` takes
    the session object handle, an ``a(sa{sv})`` of shortcut requests, the
    parent window string and an ``a{sv}`` of options. Any other method raises
    KeyError (fail closed: a caller asking for an unknown method's signature
    must not silently get CreateSession's).
    """
    if method == "CreateSession":
        return "(a{sv})"
    if method == "BindShortcuts":
        return "(oa(sa{sv})sa{sv})"
    raise KeyError(method)


def _next_counter() -> int:
    global _counter
    _counter += 1
    return _counter


def request_raise(
    bus,
    app_id,
    on_bound,
    on_activated,
    preferred_trigger=None,
    on_session=None,
):
    """Ask the portal to bind the raise shortcut and relay its events.

    ``app_id`` is accepted for the caller's own records; the portal derives the
    real app id from the D-Bus sender. A non-zero Response code at either step
    calls ``on_bound(BindResult(False, None, code))`` and subscribes nothing.
    """
    handle_token, session_handle_token = request_tokens(_next_counter())
    session_handle: list = [None]

    def on_activated_signal(signal_session, shortcut_id, timestamp, options):
        if signal_session == session_handle[0]:
            on_activated(shortcut_id)

    def on_bind_response(response, results):
        result = parse_bind_response(response, results)
        on_bound(result)
        if result.bound:
            bus.subscribe(
                INTERFACE, "Activated", session_handle[0], on_activated_signal
            )

    def on_create_response(response, results):
        if response != 0:
            on_bound(
                BindResult(bound=False, trigger_description=None, response=response)
            )
            return
        session = results.get("session_handle")
        if session is None:
            on_bound(
                BindResult(bound=False, trigger_description=None, response=response)
            )
            return
        session_handle[0] = session
        if on_session is not None:
            on_session(session)
        bind_handle = bus.call(
            INTERFACE,
            "BindShortcuts",
            [
                session,
                shortcut_request(preferred_trigger),
                "",
                {"handle_token": handle_token},
            ],
        )
        bus.subscribe(INTERFACE, "Response", bind_handle, on_bind_response)

    create_handle = bus.call(
        INTERFACE,
        "CreateSession",
        [{"handle_token": handle_token, "session_handle_token": session_handle_token}],
    )
    bus.subscribe(INTERFACE, "Response", create_handle, on_create_response)
