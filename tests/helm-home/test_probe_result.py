"""The probe_result.py contract (HH1): bind parsing, the verdict, the record.

probe_result.py is pure (no gi, no dbus, no I/O) so the unit tests load it by
path from the source tree, exactly like tests/helm/test_serve.py loads
serve.py. Each test names the one-line mutant that turns it red.
"""

import datetime as dt
import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve()
SRC_DIR = HERE.parents[2] / "pkgs" / "helm-home"

_SPEC = importlib.util.spec_from_file_location(
    "probe_result", SRC_DIR / "probe_result.py"
)
probe_result = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(probe_result)


def test_parse_bind_response_bound_with_trigger():
    # Mutant: `bound = response == 0` (ignore the list) -> row 2's empty subset
    # would stay bound and this fixture's trigger_description would be dropped.
    result = probe_result.parse_bind_response(
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
    assert result.bound is True
    assert result.trigger_description == "Super+Return"


def test_parse_bind_response_empty_subset_not_bound():
    # The empty subset the interface explicitly allows: response 0 with no
    # shortcuts is NOT a bind.
    result = probe_result.parse_bind_response(0, {"shortcuts": []})
    assert result.bound is False


def test_parse_bind_response_cancelled_not_bound():
    # Mutant: drop the `response == 0` gate -> a cancelled response (1) with a
    # non-empty list would read bound.
    result = probe_result.parse_bind_response(
        1, {"shortcuts": [("raise", {"description": "Raise Helm Home"})]}
    )
    assert result.bound is False
    assert result.response == 1


def test_parse_bind_response_other_id_not_bound():
    # Mutant: `any(True for _ in shortcuts)` (any entry counts) -> an "other"
    # id only would read bound.
    result = probe_result.parse_bind_response(
        0, {"shortcuts": [("other", {"description": "Not the raise key"})]}
    )
    assert result.bound is False


def test_parse_bind_response_list_shaped_entries():
    # Mutant: `isinstance(entry, tuple)` only -> GLib's list-of-lists shape
    # (JSON-ish variants unpack to lists) would be rejected.
    result = probe_result.parse_bind_response(
        0, {"shortcuts": [["raise", {"trigger_description": "x"}]]}
    )
    assert result.bound is True


def test_verdict_portal():
    assert probe_result.verdict(True, 2, 2) == "portal"


def test_verdict_fallback_focus_short():
    # Mutant: `focus_regained >= 1` instead of `== activations` -> (2, 1)
    # would read portal.
    assert probe_result.verdict(True, 2, 1) == "fallback"


def test_verdict_fallback_no_activations():
    # Mutant: `activations >= 0` -> (0, 0) would read portal.
    assert probe_result.verdict(True, 0, 0) == "fallback"


def test_verdict_unbound():
    # Mutant: drop the bound gate -> (False, 3, 3) would read portal.
    assert probe_result.verdict(False, 3, 3) == "unbound"


def test_record_key_set_and_ts():
    result = probe_result.parse_bind_response(
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
    now = dt.datetime(2026, 9, 10, 12, 0, 0, tzinfo=dt.timezone.utc)
    record = probe_result.record(result, 2, 2, now)
    # Mutant: drop `verdict` from the dict -> the key set loses a member.
    assert set(record.keys()) == {
        "schema",
        "ts",
        "bind_response",
        "bound",
        "trigger_description",
        "activations",
        "focus_regained",
        "verdict",
    }
    # Mutant: `now.isoformat()` without the "Z" -> ts no longer ends with Z.
    assert record["ts"].endswith("Z")
