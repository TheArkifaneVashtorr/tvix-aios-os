"""Tests for cards.py — comfy-cards' offline arm (GN48, spec §3.2/§4) and
its network lookup arm (GN49, spec §3.2/§6).

The one-shot header pass over a world's installed LoRA rows, never at
generation time: the three typed decisions (`trigger` from
`modelspec.title`, `requires` from the `ss_tag_frequency` vocabularies on
a position or act row, `unmatched` for a bare row) land in
`lab/manifest.toml` through `rewrite_rows`, and the strangers' free text
never does — it goes to the `lab/cards/<name>.json` sidecar. The
operator's own values always win, and every scalar that crosses is judged
by GN47's validators in mutate.py.

The lookup arm (GN49) is tested against a loopback fake — never a live
fetch — whose one good response is the recorded-shape fixture beside
this file (`fixtures/cards/by-hash.json`, hand-written to Assumption 12's
shape and saying so in its first key).

Every fixture here is synthetic: the container is the format's own header
rule (Assumption 11 — 8-byte little-endian length, JSON, payload), written
by `_safetensors`, never a live weight file.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import struct
import sys
import threading
import time
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "comfy-worlds" / "cards.py"
if not SRC.exists():
    raise ModuleNotFoundError(f"cards.py not found at {SRC}")

# The sibling fallback must be the one that resolves here: none of the
# three seams is set in a test run (the wrapper, not the tree, sets them).
for _seam in ("FEED_MUTATE_PY", "FEED_INDEX_PY", "FEED_QUEUE_PY"):
    os.environ.pop(_seam, None)

spec = importlib.util.spec_from_file_location("cards", SRC)
cards = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = cards
spec.loader.exec_module(cards)

# A container with no `__metadata__` key at all (the 4-of-55 shape the
# spec measured): readable and empty — not the same as an unreadable
# header, and the distinction is load-bearing for `unmatched`.
NO_METADATA = object()

_TENSOR = {"w": {"dtype": "F16", "shape": [1], "data_offsets": [0, 2]}}


def _safetensors(path, metadata):
    """One synthetic LoRA file: the measured container layout."""
    header = dict(_TENSOR)
    header["__metadata__"] = metadata
    blob = json.dumps(header).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<Q", len(blob)) + blob + b"\x00\x00")


def _world(tmp_path, manifest_text, files=()):
    """A world under tmp_path: the manifest plus one synthetic LoRA per
    (filename, metadata) pair. NO_METADATA writes a container with no
    `__metadata__` key at all."""
    lab = tmp_path / "worlds" / "sfw" / "lab"
    lab.mkdir(parents=True, exist_ok=True)
    (lab / "manifest.toml").write_text(manifest_text)
    loras = tmp_path / "worlds" / "sfw" / "models" / "loras"
    for filename, metadata in files:
        if metadata is NO_METADATA:
            blob = json.dumps(_TENSOR).encode()
            (loras / filename).parent.mkdir(parents=True, exist_ok=True)
            (loras / filename).write_bytes(
                struct.pack("<Q", len(blob)) + blob + b"\x00\x00"
            )
        else:
            _safetensors(loras / filename, metadata)
    return tmp_path


def _manifest_of(tmp_path):
    return tmp_path / "worlds" / "sfw" / "lab" / "manifest.toml"


def _sidecar_of(tmp_path, name):
    return tmp_path / "worlds" / "sfw" / "lab" / "cards" / f"{name}.json"


def _rows(*specs):
    """Each spec: (name, [extra lines]) — comments allowed in the extras."""
    blocks = []
    for name, extra in specs:
        blocks.append(
            "\n".join(
                [
                    "[[model]]",
                    f'name = "{name}"',
                    f'dest = "loras/{name}.safetensors"',
                    "enabled = true",
                    *extra,
                ]
            )
            + "\n"
        )
    return "\n".join(blocks)


def _manifest(body):
    """The plan's fixture shape: a leading comment, the rows, a disabled
    row, then the `[mutate]` table AFTER the rows."""
    return (
        "# models of world sfw\n\n" + body + "[[model]]\n"
        'name = "parked"\n'
        'dest = "loras/parked.safetensors"\n'
        "enabled = false\n"
        '\n[mutate]\nseed = "keep"\n'
    )


def _run(root, *extra):
    """cards.main the way the wrapper calls it; (exit, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cards.main(["--world", "sfw", "--root", str(root), *extra])
    return code, out.getvalue(), err.getvalue()


def test_header_reader_reads_metadata(tmp_path):
    path = tmp_path / "a.safetensors"
    _safetensors(path, {"modelspec.title": "n3lson,", "modelspec.author": "stranger"})
    assert cards.read_safetensors_metadata(path) == {
        "modelspec.title": "n3lson,",
        "modelspec.author": "stranger",
    }
    # non-string values are dropped, never coerced
    _safetensors(
        tmp_path / "b.safetensors", {"keep": "yes", "drop-int": 3, "drop-null": None}
    )
    assert cards.read_safetensors_metadata(tmp_path / "b.safetensors") == {
        "keep": "yes"
    }


def test_header_reader_refuses_short_bad_and_missing(tmp_path):
    short = tmp_path / "short.safetensors"
    short.write_bytes(b"12345")  # five bytes: not even a length prefix
    assert cards.read_safetensors_metadata(short) is None

    garbage = tmp_path / "garbage.safetensors"
    garbage.write_bytes(struct.pack("<Q", 5) + b"{oops")  # not JSON
    assert cards.read_safetensors_metadata(garbage) is None

    listy = tmp_path / "listy.safetensors"
    blob = b"[1, 2]"  # JSON, but not an object
    listy.write_bytes(struct.pack("<Q", len(blob)) + blob)
    assert cards.read_safetensors_metadata(listy) is None

    huge = tmp_path / "huge.safetensors"
    huge.write_bytes(struct.pack("<Q", 9 * 1024**3))  # a 9 GiB length prefix
    meta, reason = cards._read_header(huge)
    assert meta is None
    assert "too large" in reason  # the cap fires, never a 9 GiB read

    absent = tmp_path / "absent.safetensors"
    assert cards.read_safetensors_metadata(absent) is None

    nometa = tmp_path / "nometa.safetensors"
    blob = json.dumps(_TENSOR).encode()  # no `__metadata__` key at all
    nometa.write_bytes(struct.pack("<Q", len(blob)) + blob + b"\x00\x00")
    assert cards.read_safetensors_metadata(nometa) == {}


def test_title_token_becomes_trigger(tmp_path):
    text = _manifest(
        _rows(("n3lson", []), ("facedet", ["# adopted 2026-09", 'category = "detail"']))
    )
    root = _world(
        tmp_path,
        text,
        [
            ("n3lson.safetensors", {"modelspec.title": "n3lson,"}),
            ("facedet.safetensors", {"modelspec.title": "Face Details"}),
        ],
    )
    code, out, err = _run(root)
    assert code == 0
    rewritten = _manifest_of(tmp_path).read_text()
    assert 'trigger = "n3lson,"' in rewritten
    data = tomllib.loads(rewritten)
    rows = {row["name"]: row for row in data["model"]}
    assert rows["n3lson"]["trigger"] == "n3lson,"
    assert "trigger" not in rows["facedet"]  # a title with a space is a title
    sidecar = json.loads(_sidecar_of(tmp_path, "facedet").read_text())
    assert sidecar["title"] == "Face Details"
    assert sidecar["decided"]["trigger"] is None
    # the disabled row is not considered: no card line, no sidecar
    assert "card parked" not in out
    assert not _sidecar_of(tmp_path, "parked").exists()


def test_requires_seeded_only_on_position_and_act(tmp_path):
    vocab = json.dumps(
        {"ds": {"bent over": 9, "1girl": 40, "anal*": 7, "looking back": 3, "solo": 1}}
    )
    meta = {"modelspec.title": "k_bend,", "ss_tag_frequency": vocab}
    text = _manifest(
        _rows(("kbend", ['category = "act"']), ("fd", ['category = "detail"']))
    )
    root = _world(
        tmp_path, text, [("kbend.safetensors", meta), ("fd.safetensors", meta)]
    )
    code, out, err = _run(root)
    assert code == 0
    rewritten = _manifest_of(tmp_path).read_text()
    # count order, the illegal `anal*` skipped, the count-1 `solo` skipped
    assert 'requires = [ "1girl", "bent over", "looking back" ]' in rewritten
    data = tomllib.loads(rewritten)
    rows = {row["name"]: row for row in data["model"]}
    assert rows["kbend"]["requires"] == ["1girl", "bent over", "looking back"]
    assert "requires" not in rows["fd"]  # a detail row carries none


def test_never_overwrites_operator_values(tmp_path):
    text = _manifest(
        _rows(
            ("mine", ['category = "act"', 'trigger = "keep,"', 'requires = [ "mine" ]'])
        )
    )
    root = _world(
        tmp_path, text, [("mine.safetensors", {"modelspec.title": "n3lson,"})]
    )
    code, out, err = _run(root)
    assert code == 0
    rewritten = _manifest_of(tmp_path).read_text()
    assert 'trigger = "keep,"' in rewritten
    assert 'trigger = "n3lson,"' not in rewritten
    assert 'requires = [ "mine" ]' in rewritten
    data = tomllib.loads(rewritten)
    row = {row["name"]: row for row in data["model"]}["mine"]
    assert row["trigger"] == "keep,"
    assert row["requires"] == ["mine"]


def test_unmatched_marks_only_bare_rows(tmp_path):
    text = _manifest(_rows(("bare", []), ("bod", ['category = "body"']), ("trig", [])))
    root = _world(
        tmp_path,
        text,
        [
            ("bare.safetensors", NO_METADATA),
            ("bod.safetensors", NO_METADATA),
            ("trig.safetensors", {"modelspec.title": "n3lson,"}),
        ],
    )
    code, out, err = _run(root)
    assert code == 0
    data = tomllib.loads(_manifest_of(tmp_path).read_text())
    rows = {row["name"]: row for row in data["model"]}
    assert rows["bare"]["unmatched"] is True
    assert "unmatched" not in rows["bod"]  # a row with a category is never marked
    assert "unmatched" not in rows["trig"]  # a resolved row never is
    assert rows["trig"]["trigger"] == "n3lson,"
    # readable-but-empty headers are not read failures
    assert "unreadable" not in err


def test_free_text_never_reaches_the_manifest(tmp_path):
    pitch = "Buy my <b>LoRA</b> http://x"
    text = _manifest(_rows(("ad", [])))
    root = _world(
        tmp_path,
        text,
        [
            (
                "ad.safetensors",
                {"modelspec.title": pitch, "modelspec.description": "…"},
            )
        ],
    )
    code, out, err = _run(root)
    assert code == 0
    rewritten = _manifest_of(tmp_path).read_text()
    assert "Buy my" not in rewritten
    assert "description" not in rewritten
    sidecar = json.loads(_sidecar_of(tmp_path, "ad").read_text())
    assert sidecar["title"] == pitch
    assert sidecar["metadata"]["modelspec.description"] == "…"
    assert sidecar["readable"] is True


def test_write_back_preserves_every_other_byte():
    text = (
        "# leading comment\n"
        "[[model]]\n"
        'name = "a"\n'
        'dest = "loras/a.safetensors"\n'
        "enabled = true\n"
        'trigger = "old,"\n'
        "\n"
        "[[model]]\n"
        "# a comment inside the second block\n"
        'name = "b"\n'
        'dest = "loras/b.safetensors"\n'
        "enabled = true\n"
        'category = "act"\n'
        "\n"
        "[[model]]\n"
        'name = "parked"\n'
        'dest = "loras/parked.safetensors"\n'
        "enabled = false\n"
        "\n"
        "[mutate]\n"
        'seed = "keep"\n'
    )
    # a replace in place, then two insertions after the second block's
    # last key line, in the updates' own order
    updated = cards.rewrite_rows(
        text,
        {
            "a": {"trigger": "new2,"},
            "b": {"trigger": "k_bend,", "requires": ["1girl", "solo"]},
        },
    )
    expected = (
        "# leading comment\n"
        "[[model]]\n"
        'name = "a"\n'
        'dest = "loras/a.safetensors"\n'
        "enabled = true\n"
        'trigger = "new2,"\n'
        "\n"
        "[[model]]\n"
        "# a comment inside the second block\n"
        'name = "b"\n'
        'dest = "loras/b.safetensors"\n'
        "enabled = true\n"
        'category = "act"\n'
        'trigger = "k_bend,"\n'
        'requires = [ "1girl", "solo" ]\n'
        "\n"
        "[[model]]\n"
        'name = "parked"\n'
        'dest = "loras/parked.safetensors"\n'
        "enabled = false\n"
        "\n"
        "[mutate]\n"
        'seed = "keep"\n'
    )
    assert updated == expected
    # bools render as TOML's true/false
    flagged = cards.rewrite_rows(text, {"parked": {"unmatched": True}})
    assert "unmatched = true\n" in flagged
    # quotes and backslashes escape in a basic string
    tricky = cards.rewrite_rows(text, {"a": {"trigger": 'sa"fe\\x,'}})
    assert 'trigger = "sa\\"fe\\\\x,"' in tricky
    assert tomllib.loads(tricky)["model"][0]["trigger"] == 'sa"fe\\x,'


def test_round_trip_failure_restores_original(tmp_path, monkeypatch):
    text = _manifest(_rows(("n3lson", [])))
    root = _world(
        tmp_path, text, [("n3lson.safetensors", {"modelspec.title": "n3lson,"})]
    )
    before = _manifest_of(tmp_path).read_bytes()
    monkeypatch.setattr(
        cards.tomllib, "loads", lambda *_: (_ for _ in ()).throw(ValueError("x"))
    )
    code, out, err = _run(root)
    assert code == 1
    assert _manifest_of(tmp_path).read_bytes() == before
    assert str(_manifest_of(tmp_path)) in err
    assert "round-trip" in err
    lab = tmp_path / "worlds" / "sfw" / "lab"
    assert not list(lab.glob("*.tmp"))  # no .tmp left


def test_dry_run_writes_nothing(tmp_path):
    text = _manifest(_rows(("n3lson", [])))
    root = _world(
        tmp_path, text, [("n3lson.safetensors", {"modelspec.title": "n3lson,"})]
    )
    before = _manifest_of(tmp_path).read_bytes()
    code, out, err = _run(root, "--dry-run")
    assert code == 0
    assert _manifest_of(tmp_path).read_bytes() == before
    assert not (tmp_path / "worlds" / "sfw" / "lab" / "cards").exists()
    assert "card n3lson trigger=n3lson, requires=0 unmatched=no" in out
    # no category on the row: a trigger, but not carded
    assert (
        "carded 0 of 1 rows in sfw: 1 triggers, 0 requires seeded, 0 unmatched" in out
    )


def test_summary_line_counts(tmp_path):
    vocab = json.dumps({"ds": {"1girl": 5}})
    text = _manifest(
        _rows(("actrow", ['category = "act"']), ("bodrow", []), ("barerow", []))
    )
    root = _world(
        tmp_path,
        text,
        [
            (
                "actrow.safetensors",
                {"modelspec.title": "k_bend,", "ss_tag_frequency": vocab},
            ),
            ("bodrow.safetensors", {"modelspec.title": "n3lson,"}),
            ("barerow.safetensors", NO_METADATA),
        ],
    )
    code, out, err = _run(root)
    assert code == 0
    lines = [line for line in out.splitlines() if line]
    assert "card actrow trigger=k_bend, requires=1 unmatched=no" in lines
    assert "card barerow trigger=- requires=0 unmatched=yes" in lines
    assert (
        lines[-1]
        == "carded 1 of 3 rows in sfw: 2 triggers, 1 requires seeded, 1 unmatched"
    )


def test_missing_manifest_exits_2(tmp_path):
    (tmp_path / "worlds" / "sfw" / "lab").mkdir(parents=True)
    code, out, err = _run(tmp_path)
    assert code == 2
    assert "manifest.toml" in err


# --- GN49: the network lookup arm (spec §3.2/§6) -------------------------
#
# The lookup is by the sha256 the row already carries, exact and immune
# to the filename, tested against a loopback fake (invariant 3: never a
# live fetch). The arm's opener honours the environment's proxies — the
# broker in production — so every request here names the loopback in
# no_proxy first: the fake must never be routed through a proxy.


_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64
_SHA_D = "d" * 64
_SHA_E = "e" * 64
_SHA_F = "f" * 64

FIXTURE = HERE.parent / "fixtures" / "cards" / "by-hash.json"


def _make_lookup_handler(fake):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            fake.paths.append(self.path)
            status, body, delay = fake.routes.get(self.path, (404, b"", 0.0))
            if delay:
                # the answer is not coming within the client's timeout
                time.sleep(delay)
            try:
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                # the timed-out client is gone; the handler thread dies
                # quietly instead of spewing a traceback into the stderr
                pass

        def log_message(self, *args):
            pass

    return Handler


class FakeLookup:
    """An in-process lookup fake on `127.0.0.1:<ephemeral port>`: one route
    per response shape the arm must judge (the fixture's bytes, a 404, a
    500, a slow 200, a non-JSON body, an oversized one)."""

    def __init__(self):
        self.paths = []
        self.routes = {
            f"/by-hash/{_SHA_A}": (200, FIXTURE.read_bytes(), 0.0),
            f"/by-hash/{_SHA_B}": (404, b"", 0.0),
            f"/by-hash/{_SHA_C}": (500, b"", 0.0),
            f"/by-hash/{_SHA_D}": (200, b"{}", 3.0),
            f"/by-hash/{_SHA_E}": (200, b"not json", 0.0),
            f"/by-hash/{_SHA_F}": (200, b"x" * (2 * 1024 * 1024), 0.0),
        }
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _make_lookup_handler(self))
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()


@pytest.fixture
def lookup():
    srv = FakeLookup()
    yield srv
    srv.stop()


@pytest.fixture
def loopback(monkeypatch):
    """The lookup opener honours the environment: its proxy (the broker
    in production) must never swallow a loopback fake, and its CA bundle
    (`SSL_CERT_FILE` — the host's seat path, absent inside the build
    sandbox) has nothing to verify on plain loopback http, so the tests
    pin the environment the arm reads to the one their fake needs."""
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)


def _lrow(name, sha, extra=()):
    """A considered row that carries a sha256 — the lookup's key."""
    return (name, [f'sha256 = "{sha}"', *extra])


def _run_lookup(root, template, *extra):
    """cards.main with the lookup arm on."""
    return _run(root, "--lookup-url", template, *extra)


def test_lookup_writes_version_and_trigger(tmp_path, lookup, loopback):
    text = _manifest(_rows(_lrow("rowa", _SHA_A)))
    root = _world(tmp_path, text, [("rowa.safetensors", NO_METADATA)])
    code, out, err = _run_lookup(root, f"{lookup.url}/by-hash/{{sha256}}")
    assert code == 0
    assert lookup.paths == [f"/by-hash/{_SHA_A}"]
    rewritten = _manifest_of(tmp_path).read_text()
    # the strangers' free text never reaches the manifest
    assert "free text from a stranger" not in rewritten
    data = tomllib.loads(rewritten)
    rows = {row["name"]: row for row in data["model"]}
    assert rows["rowa"]["version"] == "123456"
    assert rows["rowa"]["trigger"] == "n3lson,"  # the illegal <bad> is skipped
    sidecar = json.loads(_sidecar_of(tmp_path, "rowa").read_text())
    assert sidecar["lookup"]["status"] == 200
    assert sidecar["lookup"]["host"] == "127.0.0.1"
    assert "free text from a stranger" in sidecar["lookup"]["body"]


def test_resolved_row_loses_unmatched(tmp_path, lookup, loopback):
    text = _manifest(_rows(_lrow("rowa", _SHA_A, ["unmatched = true"])))
    root = _world(tmp_path, text, [("rowa.safetensors", NO_METADATA)])
    code, out, err = _run_lookup(root, f"{lookup.url}/by-hash/{{sha256}}")
    assert code == 0
    rewritten = _manifest_of(tmp_path).read_text()
    assert "unmatched = true" not in rewritten  # the delete arm fired
    data = tomllib.loads(rewritten)
    rows = {row["name"]: row for row in data["model"]}
    assert "unmatched" not in rows["rowa"]
    assert rows["rowa"]["version"] == "123456"  # what resolved the row


def test_offline_trigger_wins_over_lookup(tmp_path, lookup, loopback):
    text = _manifest(_rows(_lrow("rowa", _SHA_A)))
    root = _world(
        tmp_path, text, [("rowa.safetensors", {"modelspec.title": "k_keep,"})]
    )
    code, out, err = _run_lookup(root, f"{lookup.url}/by-hash/{{sha256}}")
    assert code == 0
    data = tomllib.loads(_manifest_of(tmp_path).read_text())
    rows = {row["name"]: row for row in data["model"]}
    assert rows["rowa"]["trigger"] == "k_keep,"  # the offline value wins
    assert rows["rowa"]["version"] == "123456"


def test_404_marks_unmatched_only_bare_rows(tmp_path, lookup, loopback):
    text = _manifest(
        _rows(
            _lrow("rowb1", _SHA_B),
            _lrow("rowb2", _SHA_B, ['category = "act"']),
        )
    )
    root = _world(
        tmp_path,
        text,
        [
            # a title that is not a token: the offline pass alone leaves the
            # row unmarked — only the 404 answer marks it
            ("rowb1.safetensors", {"modelspec.title": "Face Details"}),
            ("rowb2.safetensors", {"modelspec.title": "Face Details"}),
        ],
    )
    code, out, err = _run_lookup(root, f"{lookup.url}/by-hash/{{sha256}}")
    assert code == 0  # a 404 is an answer, not a failure
    data = tomllib.loads(_manifest_of(tmp_path).read_text())
    rows = {row["name"]: row for row in data["model"]}
    assert rows["rowb1"]["unmatched"] is True
    assert "unmatched" not in rows["rowb2"]  # a category is never bare
    sidecar = json.loads(_sidecar_of(tmp_path, "rowb1").read_text())
    assert sidecar["lookup"] == {"status": 404}
    assert out.splitlines()[-1].endswith(", 0 lookups failed")


def test_500_timeout_nonjson_and_oversize_count_failed(tmp_path, lookup, loopback):
    text = _manifest(
        _rows(
            _lrow("rowc", _SHA_C),
            _lrow("rowd", _SHA_D),
            _lrow("rowe", _SHA_E),
            _lrow("rowf", _SHA_F),
        )
    )
    root = _world(
        tmp_path,
        text,
        [(f"row{name}.safetensors", NO_METADATA) for name in "cdef"],
    )
    code, out, err = _run_lookup(
        root, f"{lookup.url}/by-hash/{{sha256}}", "--timeout", "1"
    )
    assert code == 1
    lines = [line for line in err.splitlines() if "lookup failed" in line]
    assert len(lines) == 4
    assert "rowc: lookup failed (HTTP 500)" in err
    assert "rowd: lookup failed (timed out)" in err
    assert "rowe: lookup failed (not JSON)" in err
    assert "rowf: lookup failed (too large)" in err
    data = tomllib.loads(_manifest_of(tmp_path).read_text())
    rows = {row["name"]: row for row in data["model"]}
    side = {}
    for name in ("rowc", "rowd", "rowe", "rowf"):
        assert "version" not in rows[name]  # the row is unchanged
        assert "trigger" not in rows[name]
        side[name] = json.loads(_sidecar_of(tmp_path, name).read_text())["lookup"]
    assert side["rowc"] == {"status": 500, "reason": "HTTP 500"}
    assert side["rowd"]["status"] == "error"
    assert "timed out" in side["rowd"]["reason"]
    assert side["rowe"] == {"status": 200, "reason": "not JSON"}
    assert side["rowf"] == {"status": 200, "reason": "too large"}
    assert out.splitlines()[-1].endswith(", 4 lookups failed")


def test_template_rules(tmp_path, loopback):
    text = _manifest(_rows(_lrow("rowa", _SHA_A)))
    root = _world(tmp_path, text, [("rowa.safetensors", NO_METADATA)])
    # not https: the scheme rule
    code, out, err = _run_lookup(root, "http://example.invalid/{sha256}")
    assert code == 2
    assert "https" in err
    # no {sha256} placeholder
    code, out, err = _run_lookup(root, "https://example.invalid/x")
    assert code == 2
    assert "sha256" in err
    assert "exactly once" in err
    # the placeholder twice
    code, out, err = _run_lookup(root, "https://e/{sha256}/{sha256}")
    assert code == 2
    assert "exactly once" in err
    # http on the loopback is the carve-out: accepted, then the connection
    # itself fails and is counted
    code, out, err = _run_lookup(root, "http://127.0.0.1:1/{sha256}")
    assert code == 1
    assert "rowa: lookup failed" in err


def test_bad_sha256_row_is_skipped(tmp_path, lookup, loopback):
    text = _manifest(_rows(_lrow("badrow", "abc"), _lrow("rowa", _SHA_A)))
    root = _world(
        tmp_path,
        text,
        [("badrow.safetensors", NO_METADATA), ("rowa.safetensors", NO_METADATA)],
    )
    code, out, err = _run_lookup(root, f"{lookup.url}/by-hash/{{sha256}}")
    assert code == 0
    assert lookup.paths == [f"/by-hash/{_SHA_A}"]  # no request for badrow
    assert "badrow" in err
    assert "lookup failed" not in err  # a skip is not a failure


def test_no_flag_no_request(tmp_path, lookup, loopback):
    text = _manifest(_rows(_lrow("rowa", _SHA_A)))
    root = _world(tmp_path, text, [("rowa.safetensors", NO_METADATA)])
    code, out, err = _run(root, "--timeout", "5")
    assert code == 0
    assert lookup.paths == []  # no socket is opened
    # GN48's summary, byte-identical: no lookup suffix without the flag
    assert (
        out.splitlines()[-1]
        == "carded 0 of 1 rows in sfw: 0 triggers, 0 requires seeded, 1 unmatched"
    )
    sidecar = json.loads(_sidecar_of(tmp_path, "rowa").read_text())
    assert "lookup" not in sidecar
    data = tomllib.loads(_manifest_of(tmp_path).read_text())
    rows = {row["name"]: row for row in data["model"]}
    assert "version" not in rows["rowa"]


def test_dry_run_requests_but_writes_nothing(tmp_path, lookup, loopback):
    text = _manifest(_rows(_lrow("rowa", _SHA_A)))
    root = _world(tmp_path, text, [("rowa.safetensors", NO_METADATA)])
    before = _manifest_of(tmp_path).read_bytes()
    code, out, err = _run_lookup(root, f"{lookup.url}/by-hash/{{sha256}}", "--dry-run")
    assert code == 0
    assert lookup.paths == [f"/by-hash/{_SHA_A}"]  # the request was made
    assert _manifest_of(tmp_path).read_bytes() == before
    assert not (tmp_path / "worlds" / "sfw" / "lab" / "cards").exists()
