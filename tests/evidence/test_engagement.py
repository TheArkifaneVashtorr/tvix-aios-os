"""The `engagement` kind (EV15): counts only, refused on content.

Decision 18b's privacy property is a validator refusal, not a convention: a
row whose only fields are the five declared counts (plus the envelope) is
accepted; any other field is refused, a fenced name twice. `streams`,
`evidence` are loaded the way `test_evidence.py` loads `evidence`: from
`pkgs/evidence`, never from the host's packaged modules.
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()


def _load(name):
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / f"{name}.py",
        pathlib.Path("pkgs") / "evidence" / f"{name}.py",
    ]
    src = next(p for p in candidates if p.exists())
    if str(src.parent) not in sys.path:
        sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location(name, src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


streams = _load("streams")
evidence = _load("evidence")

GOOD = {
    "kind": "engagement",
    "day": "2026-09-11",
    "surface": "home",
    "opens": 3,
    "dwell_s": 120,
    "feed_likes": 0,
}


def _schema_text():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "SCHEMA.md",
        pathlib.Path("pkgs/evidence/SCHEMA.md"),
    ]
    return next(p for p in candidates if p.exists()).read_text()


def _engagement_section():
    text = _schema_text()
    return text[text.index("## Engagement") :]


def test_engagement_is_declared():
    # mutant: drop the `engagement` entry from KINDS -> `in` fails, len 16.
    assert "engagement" in streams.KINDS and len(streams.KINDS) == 19


def test_good_row_validates():
    assert streams.validate("engagement", GOOD) == []


def test_refuses_any_undeclared_field():
    # mutant: declare `variant` as a plain string field -> `[]` instead.
    assert streams.validate("engagement", GOOD | {"variant": "x"}) == [
        "variant: undeclared field"
    ]
    assert streams.validate("engagement", GOOD | {"session_id": "abc"}) == [
        "session_id: undeclared field"
    ]
    assert streams.validate("engagement", GOOD | {"extra": {"a": 1}}) == [
        "extra: undeclared field"
    ]


def test_fenced_names_refused_twice():
    # mutant: declare `note` as a field -> the fence still fires but the
    # `undeclared field` line disappears, so the note list shrinks to one line.
    for name in ("title", "url", "note"):
        assert streams.validate("engagement", GOOD | {name: "x"}) == [
            f"{name}: forbidden name",
            f"{name}: undeclared field",
        ]


def test_missing_counter_accepted_missing_key_is_keyerror(tmp_path):
    # A counter absent from a row is accepted (no required-field arm); a row
    # missing a key field makes replace_stream raise KeyError before any write.
    dropped = {k: v for k, v in GOOD.items() if k != "feed_likes"}
    assert streams.validate("engagement", dropped) == []
    store = str(tmp_path)
    with pytest.raises(KeyError):
        evidence.replace_stream(
            store,
            "ledger/engagement",
            [{k: v for k, v in GOOD.items() if k != "day"}],
        )
    assert evidence.read(store, "ledger/engagement") == []


def test_refuses_negative_and_non_int():
    # mutant: declare `opens` as plain "int" -> -1 and 10_000_001 are accepted.
    for bad in (-1, 1.5, True, 10_000_001):
        assert streams.validate("engagement", GOOD | {"opens": bad}) == [
            "opens: not a int"
        ]


def test_refuses_undeclared_surface():
    # mutant: declare `surface` as "str" -> "chat" is accepted.
    assert streams.validate("engagement", GOOD | {"surface": "chat"}) == [
        "surface: not in enum (home|feed|seats)"
    ]


def test_stream_and_key():
    assert streams.stream_of("engagement", GOOD) == "ledger/engagement"
    assert streams.key_of("engagement", GOOD) == ("2026-09-11", "home")


def test_replace_stream_upserts_by_key(tmp_path):
    # mutant: set the entry's key to None -> StreamRefused "no key; use append".
    store = str(tmp_path)
    evidence.replace_stream(store, "ledger/engagement", [{**GOOD, "opens": 3}])
    evidence.replace_stream(store, "ledger/engagement", [{**GOOD, "opens": 4}])
    rows = evidence.read(store, "ledger/engagement")
    assert len(rows) == 1
    assert rows[0]["opens"] == 4
    evidence.append(store, "ledger/engagement", GOOD)
    evidence.append(store, "ledger/engagement", GOOD)
    assert len(evidence.read(store, "ledger/engagement")) == 3


def test_schema_declares_the_counts_only_rule():
    # mutant: remove the `## Engagement` section -> both asserts fail.
    text = _schema_text()
    assert "## Engagement" in text
    assert "No other field" in text


def test_schema_names_the_fence():
    # mutant: remove the `## Engagement` section -> `in` fails.
    assert "forbidden name" in _engagement_section()


def test_schema_enum_matches_kinds():
    # mutant: extend ENGAGEMENT_SURFACES without editing SCHEMA.md -> mismatch.
    section = _engagement_section()
    m = re.search(r'\("([^"]+)", "([^"]+)", "([^"]+)"\)', section)
    assert m is not None
    assert tuple(m.groups()) == streams.ENGAGEMENT_SURFACES
