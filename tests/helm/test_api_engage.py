"""Helm API engage route (HM8): the counts-only engagement stream.

HM8 gives Helm decision 18b's local-only engagement stream: `POST /v1/engage`
folds one counter increment into today's `(day, surface)` row and writes the
row back through `evidence.replace_stream(store, "ledger/engagement", rows)` —
EV14's schema names that verb, EV15 declares the `engagement` kind, and this
route refuses everything the kind does not carry (a closed counter enum, a
closed surface enum, a positive integer `n`, a closed body key set). Nothing
leaves the machine and nothing is written under `/var/lib/helm`; the row lives
only in the evidence store's ledger.

The mutant column in the plan (M1..M13 plus the two-opens negative control) is
reproduced here as test names, each written to fail on exactly the mutation its
name targets, not to rubber-stamp the current code.
"""

import ast
import importlib.util
import json
import os
import pathlib
import stat
import sys
import types

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC_DIR = HERE.parents[2] / "pkgs" / "helm"
EVIDENCE_DIR = HERE.parents[2] / "pkgs" / "evidence"
# api_engage.py folds through evidence.replace_stream (evidence.py `import
# streams`), and the unit sandbox lays pkgs/helm and pkgs/evidence side by
# side; reproduce that shape by putting both on the path before loading, as
# test_collect.py does for collect.py's `import evidence`.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))

import evidence
import streams

# Load api_engage.py by path first (the FileNotFoundError red when it does not
# yet exist), registering it so api.py's discover() reuses this exact object.
_engage_spec = importlib.util.spec_from_file_location(
    "api_engage", SRC_DIR / "api_engage.py"
)
api_engage = importlib.util.module_from_spec(_engage_spec)
sys.modules["api_engage"] = api_engage
_engage_spec.loader.exec_module(api_engage)

# api.py's discover() imports api_engage (above) and the other route modules;
# reach the dispatcher and the Request dataclass the same way the code under
# test does, and api_home for the SCRIPT the beacon tests pin.
_spec = importlib.util.spec_from_file_location("api", SRC_DIR / "api.py")
api = importlib.util.module_from_spec(_spec)
sys.modules["api"] = api
_spec.loader.exec_module(api)

api_home = sys.modules["api_home"]


def make_cfg(tmp_path):
    """The config arm the handler reads: the evidence store root (the config
    key collect.py and api_engage share), pointed at a per-test tmp dir."""
    return {"evidence_dir": str(tmp_path / "evidence")}


def req(body):
    """A Request whose body is the JSON-encoded form, sent as the dispatcher
    would build it (whatever its Content-Type)."""
    return api.Request(
        method="POST", path="/v1/engage", body=json.dumps(body).encode("utf-8")
    )


def call(cfg, request):
    return api_engage.engage(cfg, request)


def ledger_path(cfg):
    return pathlib.Path(cfg["evidence_dir"]) / "ledger" / "engagement.jsonl"


# ---------------------------------------------------------------------------
# M8: api_engage.py imports no network module
# ---------------------------------------------------------------------------


def test_no_network_imports():
    tree = ast.parse((SRC_DIR / "api_engage.py").read_text())
    forbidden = {"urllib", "http", "socket", "subprocess"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in forbidden, f"api_engage.py imports {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            root = node.module.split(".")[0]
            assert root not in forbidden, f"api_engage.py imports {node.module}"


# ---------------------------------------------------------------------------
# the closed enums, pinned whole (M2/M11's free-text mutants widen them)
# ---------------------------------------------------------------------------


def test_counters_are_closed():
    assert api_engage.COUNTERS == ("opens", "dwell_s", "feed_likes")


def test_surfaces_are_closed():
    assert api_engage.SURFACES == ("home", "feed", "seats")


# ---------------------------------------------------------------------------
# M1/M2/M3/M4: the body's counter enum, key set, and positive integer n
# ---------------------------------------------------------------------------


def test_string_n_is_400_and_nothing_written(tmp_path):
    # M1: accept `"n": "1"` and this 400 becomes 204 and a file appears.
    cfg = make_cfg(tmp_path)
    status, body = call(cfg, req({"counter": "opens", "n": "1", "surface": "home"}))
    assert status == 400
    assert body == {"error": "n"}
    assert not ledger_path(cfg).exists()


def test_unknown_counter_is_400(tmp_path):
    # M2: accept any counter string and this 400 becomes 204.
    cfg = make_cfg(tmp_path)
    status, body = call(cfg, req({"counter": "note", "n": 1, "surface": "home"}))
    assert status == 400
    assert body == {"error": "counter"}
    assert not ledger_path(cfg).exists()


def test_extra_key_is_400(tmp_path):
    # M3: accept a fourth key and this 400 becomes 204.
    cfg = make_cfg(tmp_path)
    status, _ = call(
        cfg, req({"counter": "opens", "n": 1, "surface": "home", "text": "hi"})
    )
    assert status == 400
    assert not ledger_path(cfg).exists()


def test_nonpositive_n_is_400(tmp_path):
    # M4: accept n = -5 (or 0) and this 400 becomes 204.
    cfg = make_cfg(tmp_path)
    for bad in (-5, 0):
        status, _ = call(cfg, req({"counter": "opens", "n": bad, "surface": "home"}))
        assert status == 400
    assert not ledger_path(cfg).exists()


def test_float_n_is_400(tmp_path):
    # The schema refuses a float; the route must too, before the fold.
    cfg = make_cfg(tmp_path)
    status, _ = call(cfg, req({"counter": "opens", "n": 1.5, "surface": "home"}))
    assert status == 400


def test_non_json_body_is_400(tmp_path):
    cfg = make_cfg(tmp_path)
    request = api.Request(method="POST", path="/v1/engage", body=b"not json")
    status, body = call(cfg, request)
    assert status == 400
    assert body == {"error": "body"}


# ---------------------------------------------------------------------------
# M11: the surface enum is closed
# ---------------------------------------------------------------------------


def test_unknown_surface_is_400(tmp_path):
    # M11: accept any surface string and this 400 becomes 204 and the store
    # grows a row keyed on a surface the kind does not declare.
    cfg = make_cfg(tmp_path)
    status, body = call(cfg, req({"counter": "opens", "n": 1, "surface": "anything"}))
    assert status == 400
    assert body == {"error": "surface"}
    assert not ledger_path(cfg).exists()


# ---------------------------------------------------------------------------
# M10: the written row validates as EV15's engagement kind
# ---------------------------------------------------------------------------


def test_row_validates_as_evidence_kind(tmp_path):
    # M10: add a `note` leaf to the row and EV15's validator refuses the
    # string field, so this == [] assert fails.
    cfg = make_cfg(tmp_path)
    status, _ = call(cfg, req({"counter": "opens", "n": 1, "surface": "home"}))
    assert status == 204
    rows = evidence.read(cfg["evidence_dir"], "ledger/engagement")
    assert len(rows) == 1
    assert streams.validate("engagement", rows[0]) == []


# ---------------------------------------------------------------------------
# M13: the body is parsed whatever its Content-Type (sendBeacon -> text/plain)
# ---------------------------------------------------------------------------


def test_engage_accepts_text_plain_content_type(tmp_path):
    # M13: answer 400 unless Content-Type: application/json and this 204
    # becomes 400 for a valid body posted as text/plain.
    cfg = make_cfg(tmp_path)
    request = api.Request(
        method="POST",
        path="/v1/engage",
        headers={"content-type": "text/plain"},
        body=json.dumps({"counter": "opens", "n": 1, "surface": "home"}).encode(
            "utf-8"
        ),
    )
    status, _ = call(cfg, request)
    assert status == 204


# ---------------------------------------------------------------------------
# M12: Helm's script never posts feed_likes (the feed's own page does)
# ---------------------------------------------------------------------------


def test_home_script_never_posts_feed_likes():
    # M12: add a feed_likes beacon to Helm's inline script and this fails.
    assert "feed_likes" not in api_home.SCRIPT


# ---------------------------------------------------------------------------
# the home page's beacons: opens on load, dwell_s on pagehide
# ---------------------------------------------------------------------------


def test_home_script_beacons_opens_and_dwell():
    assert "opens" in api_home.SCRIPT
    assert "dwell_s" in api_home.SCRIPT


# ---------------------------------------------------------------------------
# negative control: two opens fold to two (overwrite-not-add is the mutant)
# ---------------------------------------------------------------------------


def test_two_opens_fold_to_two(tmp_path):
    cfg = make_cfg(tmp_path)
    assert call(cfg, req({"counter": "opens", "n": 1, "surface": "home"}))[0] == 204
    assert call(cfg, req({"counter": "opens", "n": 1, "surface": "home"}))[0] == 204
    rows = evidence.read(cfg["evidence_dir"], "ledger/engagement")
    assert len(rows) == 1
    row = rows[0]
    assert row["opens"] == 2
    assert row["dwell_s"] == 0
    assert row["feed_likes"] == 0
    assert row["surface"] == "home"


# ---------------------------------------------------------------------------
# HM8b: two different surfaces on one day fold to two rows, never one into the
# other (the review's MINOR-3 mutant dropped the surface half of the fold key)
# ---------------------------------------------------------------------------


def test_two_surfaces_fold_to_separate_rows(tmp_path):
    cfg = make_cfg(tmp_path)
    assert call(cfg, req({"counter": "opens", "n": 1, "surface": "home"}))[0] == 204
    assert call(cfg, req({"counter": "opens", "n": 1, "surface": "feed"}))[0] == 204
    rows = evidence.read(cfg["evidence_dir"], "ledger/engagement")
    assert len(rows) == 2
    by_surface = {row["surface"]: row for row in rows}
    assert by_surface["home"]["opens"] == 1
    assert by_surface["feed"]["opens"] == 1


# ---------------------------------------------------------------------------
# HM8b: a setgid, group-writable ledger directory (the 2770 HM8 ships) and the
# files under it survive a write untouched -- replace_stream must not chmod the
# parent to 0750 when it does not own it or it already carries the setgid bit
# ---------------------------------------------------------------------------


def test_replace_stream_preserves_setgid_ledger_across_a_write(tmp_path):
    cfg = make_cfg(tmp_path)
    ledger_dir = pathlib.Path(cfg["evidence_dir"]) / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(ledger_dir, 0o2770)
    except PermissionError:
        # The helm-unit nix sandbox seccomp-filters chmod calls that would
        # set S_ISUID/S_ISGID (see pkgs/lane/lane-submit.py's
        # _chmod_dir_setgid docstring), so this case cannot even set up the
        # 2770 fixture there; it runs in the dev shell and any unseccomp'd
        # runner instead.
        pytest.skip("sandbox seccomp-filters setgid chmod (the helm-unit nix sandbox)")
    status, _ = call(cfg, req({"counter": "opens", "n": 1, "surface": "home"}))
    assert status == 204
    assert stat.S_IMODE(os.stat(ledger_dir).st_mode) == 0o2770
    assert os.stat(ledger_path(cfg)).st_mode & 0o020 == 0o020


# ---------------------------------------------------------------------------
# HM8c: the same setgid guard, proved inside the helm-unit sandbox (the 2770
# fixture above skips there -- seccomp-filters a real setgid chmod). monkeypatch
# os.stat to report S_ISGID on the ledger dir and record every os.chmod/os.open
# call, so M-C (unconditional chmod) and M-D (a fixed 0o640) die in CI, not
# only in the dev shell.
# ---------------------------------------------------------------------------


def test_setgid_parent_skips_chmod_without_a_real_setgid_dir(tmp_path, monkeypatch):
    cfg = make_cfg(tmp_path)
    ledger_dir = pathlib.Path(cfg["evidence_dir"]) / "ledger"
    engagement = ledger_path(cfg)
    # engage() calls evidence.read before replace_stream, and read iterdir()s
    # the ledger dir it has to exist on disk; create it (0750, no setgid -- the
    # fake_stat below supplies the S_ISGID bit the sandbox cannot chmod).
    ledger_dir.mkdir(parents=True, exist_ok=True)

    real_stat = os.stat
    real_chmod = os.chmod
    real_open = os.open
    chmod_calls: list[tuple[str, int]] = []
    open_calls: list[tuple[str, int, int]] = []

    def fake_stat(p, *args, **kwargs):
        if os.fspath(p) == os.fspath(ledger_dir):
            # report the ledger as setgid (2770) owned by us, so the guard's
            # `_owned and not _setgid` is False and the chmod is skipped
            return types.SimpleNamespace(
                st_uid=os.geteuid(), st_mode=stat.S_IFDIR | 0o2770
            )
        return real_stat(p, *args, **kwargs)

    def fake_chmod(p, mode, *args, **kwargs):
        chmod_calls.append((os.fspath(p), mode))
        return real_chmod(p, mode, *args, **kwargs)

    def fake_open(p, flags, mode=0o777, *args, **kwargs):
        open_calls.append((os.fspath(p), flags, mode))
        return real_open(p, flags, mode, *args, **kwargs)

    monkeypatch.setattr(os, "stat", fake_stat)
    monkeypatch.setattr(os, "chmod", fake_chmod)
    monkeypatch.setattr(os, "open", fake_open)

    status, _ = call(cfg, req({"counter": "opens", "n": 1, "surface": "home"}))
    assert status == 204

    assert all(p != os.fspath(ledger_dir) for p, _ in chmod_calls), (
        "replace_stream chmodded the setgid ledger directory: " + repr(chmod_calls)
    )

    file_open = [
        (flags, mode)
        for p, flags, mode in open_calls
        if p == os.fspath(engagement) and flags & os.O_CREAT
    ]
    assert file_open, "engagement.jsonl was never opened O_CREAT"
    assert file_open[0][1] == 0o660, (
        "engagement.jsonl opened with mode "
        + oct(file_open[0][1])
        + ", want 0o660 under a setgid ledger"
    )
