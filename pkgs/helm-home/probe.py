"""The helm-home raise-key probe (HH1): a GTK4 window asks the shortcuts portal.

Entry points: ``helm-home-probe --self-check`` prints the Gtk 4 / Adw 1
versions headless (the package's installCheckPhase); ``helm-home-probe
--self-test`` builds the CreateSession and BindShortcuts payloads as
GLib.Variant values against a recording fake connection (no bus) and prints one
type string per method. Otherwise one Adw window ("Helm Home probe") asks the
org.freedesktop.portal.GlobalShortcuts interface to bind the raise key, prints
one line per event, and writes a verdict record on window close or --timeout.

``gi`` is imported at module scope here: probe.py is the only gi consumer (no
unit test imports it), and the boxer / PortalBus need ``GLib`` and the pure
``portal`` module in scope. portal.py / probe_result.py stay stdlib-only and
importable in a stdlib-only test sandbox.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import gi
import portal
import probe_result

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, Gio, GLib, Gtk

PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_OBJECT = "/org/freedesktop/portal/desktop"


def _utc_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _default_out() -> str:
    state_home = os.environ.get("XDG_STATE_HOME")
    if not state_home:
        state_home = os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(state_home, "helm-home", "probe.json")


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="helm-home-probe")
    parser.add_argument(
        "--out",
        default=None,
        help="record path (default $XDG_STATE_HOME/helm-home/probe.json)",
    )
    parser.add_argument(
        "--preferred-trigger",
        default="<Super>Return",
        help="preferred raise-key trigger passed to the portal",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="seconds to run before writing the record and exiting",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="print the GI/GTK/Adw versions and exit 0 (no display needed)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="box both portal calls against a fake connection and exit 0",
    )
    return parser.parse_args(argv)


def self_check() -> int:
    print(
        f"Gtk {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()} "
        f"Adw {Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()} "
        f"portal org.freedesktop.portal.GlobalShortcuts"
    )
    return 0


def _unpack_variant(variant):
    """Recursively convert a GLib.Variant tree to plain Python values."""
    type_str = variant.get_type_string()
    if type_str.startswith("a{"):
        return {key: _unpack_variant(value) for key, value in variant}
    if type_str.startswith("a"):
        return [_unpack_variant(value) for value in variant]
    if type_str.startswith("("):
        return tuple(_unpack_variant(value) for value in variant)
    if type_str == "v":
        return _unpack_variant(variant.get_variant())
    return variant.unpack()


def _box(value, method, where):
    """Box ``value`` for its slot inside a portal ``method``'s payload.

    ``where`` names the failing slot (e.g. ``argument 0``) for the fail-closed
    TypeError. A ``GLib.Variant`` passes through; a ``str``/``bool``/``int``
    becomes a ``"s"``/``"b"``/``"i"`` variant; a ``dict`` (an ``a{sv}``) is the
    plain dict with each value boxed — the caller's outer signature wraps the
    dict itself; a ``list`` of ``(name, dict)`` pairs (the ``a(sa{sv})``
    shortcuts shape) is the plain list with each entry's dict boxed. Anything
    else raises TypeError naming ``method`` and ``where``.
    """
    if isinstance(value, GLib.Variant):
        return value
    if isinstance(value, bool):
        return GLib.Variant("b", value)
    if isinstance(value, int):
        return GLib.Variant("i", value)
    if isinstance(value, str):
        return GLib.Variant("s", value)
    if isinstance(value, dict):
        return {
            key: _box(val, method, f"{where}[{key!r}]") for key, val in value.items()
        }
    if isinstance(value, list):
        boxed = []
        for name, entry in value:
            if not isinstance(entry, dict):
                raise TypeError(f"{method}: shortcut {name!r} at {where} is not a dict")
            boxed.append(
                (
                    name,
                    {
                        key: _box(val, method, f"{where}<{name!r}>[{key!r}]")
                        for key, val in entry.items()
                    },
                )
            )
        return boxed
    raise TypeError(
        f"{method}: cannot box {type(value).__name__} at {where}: {value!r}"
    )


def _box_arg(value, method, arg_index):
    """Box one top-level argument for ``method``'s variant.

    A ``dict``/``list`` argument is handed to ``_box`` (leaves boxed, the outer
    signature wraps the container). Plain strings (object paths and the
    parent-window string) are left as-is — the outer signature types ``o``/``s``
    itself.
    """
    if isinstance(value, dict):
        return _box(value, method, f"argument {arg_index}")
    if isinstance(value, list):
        return _box(value, method, f"argument {arg_index}")
    return value


class PortalBus:
    """Gio.DBusConnection adapter exposing call/subscribe to portal.py."""

    def __init__(self, connection):
        self._conn = connection

    def call(self, interface, method, args):
        result = self._conn.call_sync(
            PORTAL_BUS,
            PORTAL_OBJECT,
            interface,
            method,
            GLib.Variant(
                portal.dbus_signature_for(method),
                tuple(_box_arg(arg, method, index) for index, arg in enumerate(args)),
            ),
            GLib.VariantType.new("(o)"),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
        return result[0]

    def subscribe(self, interface, signal, path, handler):
        def on_signal(
            connection,
            sender,
            object_path,
            iface,
            signal_name,
            parameters,
            user_data,
        ):
            handler(*_unpack_variant(parameters))

        self._conn.signal_subscribe(
            PORTAL_BUS,
            interface,
            signal,
            path,
            None,
            Gio.DBusSignalFlags.NONE,
            on_signal,
            None,
        )


class FakeConnection:
    """A recording stand-in for Gio.DBusConnection (bus-free self-test).

    ``call_sync`` stores the built parameters variant per call, returns a canned
    ``(o)`` reply so PortalBus.call hands back an object-path string, and never
    touches a real bus.
    """

    def __init__(self):
        self.calls = []

    def call_sync(
        self,
        bus_name,
        object_path,
        interface_name,
        method_name,
        parameters,
        reply_type,
        flags,
        timeout_msec,
        cancellable,
    ):
        self.calls.append((method_name, parameters))
        return GLib.Variant("(o)", ("/org/freedesktop/portal/desktop/self_test",))


def self_test() -> int:
    """Build both portal calls against FakeConnection; print one type string each.

    Mirrors request_raise's argument shapes (portal.py) through the same
    PortalBus.call path the live probe uses, so a broken payload fails here.
    Exit 0 only if both methods' variants build.
    """
    connection = FakeConnection()
    bus = PortalBus(connection)
    handle_token, session_handle_token = portal.request_tokens(0)
    session_handle = bus.call(
        portal.INTERFACE,
        "CreateSession",
        [{"handle_token": handle_token, "session_handle_token": session_handle_token}],
    )
    bus.call(
        portal.INTERFACE,
        "BindShortcuts",
        [
            session_handle,
            portal.shortcut_request("<Super>Return"),
            "",
            {"handle_token": handle_token},
        ],
    )
    for method, parameters in connection.calls:
        print(f"{method} {parameters.get_type_string()}")
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.self_check:
        return self_check()
    if args.self_test:
        return self_test()

    APP_ID = "org.nixos_agent_env.HelmHome"

    out = args.out or _default_out()
    state = {
        "bound": None,
        "activations": 0,
        "focus_regained": 0,
        "written": False,
    }

    app = Adw.Application(application_id=APP_ID)
    window = None
    label = None

    def show(text):
        print(text, flush=True)
        if label is not None:
            label.set_text(text)

    def on_bound(bind_result):
        state["bound"] = bind_result
        trigger = bind_result.trigger_description or "-"
        show(
            f"probe: bind response={bind_result.response} "
            f'bound={"true" if bind_result.bound else "false"} trigger="{trigger}"'
        )

    def on_session(session_handle):
        show(f"probe: session {session_handle}")

    def on_activated(shortcut_id):
        state["activations"] += 1
        start = time.monotonic()

        def watch_active():
            active = (
                bool(window.get_property("is-active")) if window is not None else False
            )
            if active:
                state["focus_regained"] += 1
                show(f"probe: activated {shortcut_id} focus=true")
                return GLib.SOURCE_REMOVE
            if time.monotonic() - start >= 2.0:
                show(f"probe: activated {shortcut_id} focus=false")
                return GLib.SOURCE_REMOVE
            return GLib.SOURCE_CONTINUE

        GLib.timeout_add(50, watch_active)

    def write_record():
        if state["written"]:
            return
        state["written"] = True
        bound_result = state["bound"] or probe_result.BindResult(
            bound=False, trigger_description=None, response=-1
        )
        record = probe_result.record(
            bound_result, state["activations"], state["focus_regained"], _utc_now()
        )
        parent = os.path.dirname(out) or "."
        os.makedirs(parent, mode=0o700, exist_ok=True)
        with open(out, "w") as fh:
            json.dump(record, fh, sort_keys=True, indent=2)
            fh.write("\n")
        show(
            f"probe: verdict={record['verdict']} "
            f"bound={'true' if record['bound'] else 'false'} "
            f"activations={record['activations']} focus_regained={record['focus_regained']}"
        )

    def on_close_request(*_args):
        write_record()
        app.quit()
        return True

    def on_activate(_app):
        nonlocal window, label
        if window is None:
            window = Adw.ApplicationWindow(application=app)
            window.set_title("Helm Home probe")
            window.update_property([Gtk.AccessibleProperty.LABEL], ["Helm Home probe"])
            window.set_default_size(420, 180)
            label = Gtk.Label(label="waiting for the raise key…")
            window.set_content(label)
            window.connect("close-request", on_close_request)
        window.present()

        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus = PortalBus(connection)
        try:
            portal.request_raise(
                bus,
                APP_ID,
                on_bound,
                on_activated,
                preferred_trigger=args.preferred_trigger,
                on_session=on_session,
            )
        except Gio.DBusError as exc:
            first_line = str(exc).splitlines()[0]
            print(f"probe: portal unreachable: {first_line}", file=sys.stderr)
            sys.exit(3)

    def on_timeout():
        write_record()
        app.quit()
        return GLib.SOURCE_REMOVE

    app.connect("activate", on_activate)
    GLib.timeout_add_seconds(args.timeout, on_timeout)
    return app.run(None)


if __name__ == "__main__":
    sys.exit(main())
