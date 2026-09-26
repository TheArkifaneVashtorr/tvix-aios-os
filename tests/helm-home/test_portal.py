"""The portal.py contract (HH1): request_tokens, shortcut_request, request_raise.

portal.py is stdlib except for an injected bus object; the tests inject a
recording FakeBus so they can drive the portal's async Response/Activated
signals deterministically. Loaded by path (portal.py does
`from probe_result import ...`, so SRC_DIR is on sys.path).
"""

import importlib.util
import pathlib
import re
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC_DIR = HERE.parents[2] / "pkgs" / "helm-home"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_SPEC = importlib.util.spec_from_file_location("portal", SRC_DIR / "portal.py")
portal = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(portal)

import probe_result


class FakeBus:
    """Records calls/subscriptions and lets a test drive the portal's signals."""

    def __init__(self, events):
        self.events = events
        self.calls = []
        self.subscriptions = []

    def call(self, interface, method, args):
        self.calls.append((method, args))
        self.events.append(("call", method))
        return f"/handle/{len(self.calls)}"

    def subscribe(self, interface, signal, path, handler):
        self.subscriptions.append((signal, path, handler))
        self.events.append(("subscribe", signal, path))

    def response(self, path, response, results):
        for signal, sub_path, handler in self.subscriptions:
            if signal == "Response" and sub_path == path:
                handler(response, results)
                return
        raise AssertionError(f"no Response subscription on {path}")

    def emit(self, signal, path, *args):
        for sub_signal, sub_path, handler in self.subscriptions:
            if sub_signal == signal and sub_path == path:
                handler(*args)
                return
        raise AssertionError(f"no {signal} subscription on {path}")


def test_shortcut_request_with_trigger():
    assert portal.shortcut_request("<Super>Return") == [
        (
            "raise",
            {
                "description": "Raise Helm Home",
                "preferred_trigger": "<Super>Return",
            },
        )
    ]


def test_shortcut_request_without_trigger():
    # Mutant: always emit `preferred_trigger` (None) -> this assertion red.
    request = portal.shortcut_request(None)
    assert request == [("raise", {"description": "Raise Helm Home"})]
    assert "preferred_trigger" not in request[0][1]


def test_request_raise_happy_path():
    events = []
    bus = FakeBus(events)

    def on_bound(result):
        events.append(("bound", result.bound))

    def on_activated(shortcut_id):
        events.append(("activated", shortcut_id))

    portal.request_raise(bus, "org.test.App", on_bound, on_activated, "<Super>Return")

    # CreateSession first, then its Response carries the session handle.
    assert bus.calls[0][0] == "CreateSession"
    bus.response("/handle/1", 0, {"session_handle": "/s/1"})

    # BindShortcuts follows with the session and the raise shortcut request.
    assert bus.calls[1][0] == "BindShortcuts"
    bus.response(
        "/handle/2",
        0,
        {
            "shortcuts": [
                (
                    "raise",
                    {
                        "description": "Raise Helm Home",
                        "trigger_description": "Super+Return",
                    },
                )
            ]
        },
    )

    # on_bound fired exactly once, bound=True.
    bound_events = [e for e in events if e[0] == "bound"]
    assert len(bound_events) == 1
    assert bound_events[0][1] is True

    # Mutant: subscribe Activated before calling on_bound -> the Activated
    # subscription would precede the bound event in the ordered log.
    bound_index = events.index(("bound", True))
    activated_sub_index = events.index(("subscribe", "Activated", "/s/1"))
    assert bound_index < activated_sub_index

    # An Activated on the session with shortcut_id "raise" -> on_activated.
    bus.emit("Activated", "/s/1", "/s/1", "raise", 0, {})
    assert ("activated", "raise") in events


def test_request_raise_failed_session():
    events = []
    bus = FakeBus(events)

    def on_bound(result):
        events.append(("bound", result))

    portal.request_raise(bus, "org.test.App", on_bound, lambda sid: None)

    # CreateSession response 2 (error): on_bound with response=2, no bind.
    bus.response("/handle/1", 2, {})

    bound_events = [e for e in events if e[0] == "bound"]
    assert len(bound_events) == 1
    result = bound_events[0][1]
    assert result == probe_result.BindResult(
        bound=False, trigger_description=None, response=2
    )

    # Mutant: call BindShortcuts regardless of the session code -> the fake's
    # call log would contain it.
    assert all(method != "BindShortcuts" for method, _args in bus.calls)


def test_request_tokens():
    handle_token, session_handle_token = portal.request_tokens(7)
    assert handle_token == "helm_home_7"
    assert session_handle_token == "helm_home_7_s"
    # Mutant: use a hyphen in the token -> the object-path element regex fails.
    assert re.fullmatch(r"[A-Za-z0-9_]+", handle_token)
    assert re.fullmatch(r"[A-Za-z0-9_]+", session_handle_token)


def test_dbus_signature_for_create_session():
    # Mutant: hardcode one signature string for both methods -> whichever
    # method it wasn't tuned for goes red (Step 4a/4b).
    assert portal.dbus_signature_for("CreateSession") == "(a{sv})"


def test_dbus_signature_for_bind_shortcuts():
    # The four-argument BindShortcuts payload spelled per the GVariant grammar:
    # object handle, array of (id, a{sv}) structs, parent window, options.
    assert portal.dbus_signature_for("BindShortcuts") == "(oa(sa{sv})sa{sv})"


def test_dbus_signature_for_unknown_raises():
    # Mutant: return a default signature instead of raising -> this `raises` red.
    with pytest.raises(KeyError) as excinfo:
        portal.dbus_signature_for("NoSuchMethod")
    assert excinfo.value.args == ("NoSuchMethod",)
