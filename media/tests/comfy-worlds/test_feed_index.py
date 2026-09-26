"""Unit tests for pkgs/comfy-worlds/feed_index.py.

Loaded by path (like tests/comfy-worlds/test_feed_placeholder.py) so this test
file works both under `pytest tests/comfy-worlds` from the repo root and inside
checks.comfy-worlds-unit, which copies pkgs/comfy-worlds and tests/comfy-worlds
into a fresh tree without installing anything.
"""

import hashlib
import importlib.util
import json
import os
import pathlib
import struct
import zlib

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "comfy-worlds" / "feed_index.py"
spec = importlib.util.spec_from_file_location("feed_index", SRC)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)

# The prompt and workflow chunks ComfyUI writes. The prompt carries the
# class_type graph — the source of truth for what produced an image — and the
# workflow is ComfyUI's UI-editor export (nodes/links, no class_type). The
# prompt is tests/acceptance/workflows/sdxl.json's base-plus-refiner shape
# trimmed to nodes 3, 6, 7 plus a second KSampler node "10": node 3 (the base
# sampler, numerically lowest id) has inputs.seed = 42, node 10 (the refiner)
# has 99.
PROMPT = json.dumps(
    {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 42,
                "sampler_name": "euler",
                "positive": ["6", 0],
                "negative": ["7", 0],
            },
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red apple"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry"}},
        "10": {
            "class_type": "KSampler",
            "inputs": {"seed": 99, "positive": ["6", 0]},
        },
    }
)
WORKFLOW = json.dumps(
    {
        "nodes": [
            {
                "id": 3,
                "type": "KSampler",
                "widgets_values": [42, "fixed", 20, 7.5, "euler", "normal", 1.0],
            },
            {"id": 6, "type": "CLIPTextEncode", "widgets_values": ["a red apple"]},
        ],
        "links": [],
        "version": 0.4,
    }
)

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(ctype, payload):
    return (
        struct.pack(">I", len(payload))
        + ctype
        + payload
        + struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF)
    )


def _text_chunk(keyword, text, itxt):
    if itxt:
        payload = keyword + b"\x00\x00\x00\x00\x00" + text.encode("utf-8")
        return _chunk(b"iTXt", payload)
    return _chunk(b"tEXt", keyword + b"\x00" + text.encode("latin-1"))


def png_with_chunks(path, prompt_json, workflow_json, itxt=False):
    """Write a minimal valid PNG carrying `prompt` and `workflow` chunks.

    `prompt_json` and `workflow_json` are the raw string values ComfyUI embeds
    (JSON text); the seed comes from parsing `prompt_json` (the class_type
    graph), never `workflow_json`.
    """
    png = pathlib.Path(path)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    png.write_bytes(
        SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _text_chunk(b"prompt", prompt_json, itxt)
        + _text_chunk(b"workflow", workflow_json, itxt)
        + _chunk(b"IEND", b"")
    )


def make_world(tmp_path, world="sfw"):
    out = tmp_path / "worlds" / world / "output"
    out.mkdir(parents=True)
    return out


def test_rebuild_reads_prompt(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)
    assert feed.rebuild(str(tmp_path), "sfw") == 1
    conn = feed.open_db(str(tmp_path), "sfw")
    row = conn.execute("SELECT * FROM renders WHERE name = 'a.png'").fetchone()
    assert row["prompt"] == PROMPT


def test_rebuild_reads_workflow(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)
    feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    row = conn.execute("SELECT * FROM renders WHERE name = 'a.png'").fetchone()
    assert row["workflow"] == WORKFLOW


def test_rebuild_reads_seed(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)
    feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    row = conn.execute("SELECT * FROM renders WHERE name = 'a.png'").fetchone()
    # The seed is node 3's inputs.seed in the prompt's class_type graph, not
    # node 10's 99: the base sampler is the numerically lowest-id KSampler.
    assert row["seed"] == 42


def test_rebuild_reads_seed_ignores_workflow_chunk(tmp_path):
    out = make_world(tmp_path)
    # The workflow chunk is itself a valid node graph whose KSampler carries a
    # different seed; the seed column must still read the prompt's 42, proving
    # the seed's source chunk, not just its value.
    other_workflow = json.dumps(
        {
            "3": {
                "class_type": "KSampler",
                "inputs": {"seed": 7, "positive": ["6", 0]},
            },
        }
    )
    png_with_chunks(out / "a.png", PROMPT, other_workflow)
    feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    row = conn.execute("SELECT * FROM renders WHERE name = 'a.png'").fetchone()
    assert row["seed"] == 42


def test_reads_itxt_chunks(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW, itxt=True)
    feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    row = conn.execute("SELECT * FROM renders WHERE name = 'a.png'").fetchone()
    assert row["prompt"] == PROMPT
    assert row["workflow"] == WORKFLOW


def test_rebuild_is_idempotent(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)
    first = feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    before = [tuple(r) for r in conn.execute("SELECT * FROM renders ORDER BY name")]
    second = feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    after = [tuple(r) for r in conn.execute("SELECT * FROM renders ORDER BY name")]
    assert first == second
    assert before == after


def test_rebuild_drops_deleted_files_keeps_likes(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)
    png_with_chunks(out / "b.png", PROMPT, WORKFLOW)
    assert feed.rebuild(str(tmp_path), "sfw") == 2
    conn = feed.open_db(str(tmp_path), "sfw")
    conn.execute("INSERT INTO likes(name, liked_at) VALUES('a.png', 1.0)")
    conn.commit()
    (out / "b.png").unlink()
    assert feed.rebuild(str(tmp_path), "sfw") == 1
    conn = feed.open_db(str(tmp_path), "sfw")
    assert conn.execute("SELECT COUNT(*) FROM likes").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM renders").fetchone()[0] == 1


def test_non_png_refused(tmp_path):
    out = make_world(tmp_path)
    (out / "bad.png").write_bytes(b"not a png file")
    with pytest.raises(ValueError, match="not a PNG: bad.png"):
        feed.read_chunks(out / "bad.png")


def test_missing_output_dir_is_zero(tmp_path):
    assert feed.rebuild(str(tmp_path), "sfw") == 0


def test_newest_orders_by_mtime(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)
    png_with_chunks(out / "b.png", PROMPT, WORKFLOW)
    os.utime(out / "a.png", (1000, 1000))
    os.utime(out / "b.png", (2000, 2000))
    feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    assert [r["name"] for r in feed.newest(conn)] == ["b.png", "a.png"]


def test_newest_respects_limit(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)
    png_with_chunks(out / "b.png", PROMPT, WORKFLOW)
    png_with_chunks(out / "c.png", PROMPT, WORKFLOW)
    os.utime(out / "a.png", (1000, 1000))
    os.utime(out / "b.png", (2000, 2000))
    os.utime(out / "c.png", (3000, 3000))
    feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    assert [r["name"] for r in feed.newest(conn, limit=2)] == ["c.png", "b.png"]


def test_main_rebuild_subcommand_prints_count(tmp_path, capsys):
    out = tmp_path / "worlds" / "w" / "output"
    out.mkdir(parents=True)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)
    feed.main(["--root", str(tmp_path), "--world", "w", "rebuild"])
    captured = capsys.readouterr()
    assert captured.out.strip() == "1"
    assert (tmp_path / "worlds" / "w" / "feed.sqlite").exists()


def test_rebuild_leaves_the_output_dir_byte_identical(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)

    def snapshot():
        listing = sorted(p.name for p in out.iterdir())
        files = {}
        for p in out.iterdir():
            st = p.stat()
            files[p.name] = (st.st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest())
        return listing, files

    before = snapshot()
    feed.rebuild(str(tmp_path), "sfw")
    after = snapshot()
    assert before == after
    assert set(p.name for p in out.iterdir()) == {"a.png"}


# A power cut on 2026-09-19 left seven zero-byte PNGs in a live world's output
# directory. rebuild() raised on the first of them, and because build_server()
# rebuilds every world before it binds, the whole feed server for every world
# failed to start. An unreadable file is data the index has no row for; it is
# not a reason for the feed to be unreachable.


def test_rebuild_skips_a_zero_byte_file(tmp_path, capsys):
    out = make_world(tmp_path)
    png_with_chunks(out / "good.png", PROMPT, WORKFLOW)
    (out / "half-written.png").write_bytes(b"")
    assert feed.rebuild(str(tmp_path), "sfw") == 1


def test_rebuild_is_silent_about_a_zero_byte_file(tmp_path, capsys):
    # A generator mid-write produces one transiently and the next rebuild
    # picks it up once complete -- warning every rebuild would be noise on a
    # healthy system.
    out = make_world(tmp_path)
    png_with_chunks(out / "good.png", PROMPT, WORKFLOW)
    (out / "half-written.png").write_bytes(b"")
    feed.rebuild(str(tmp_path), "sfw")
    assert capsys.readouterr().err == ""


def test_rebuild_names_a_corrupt_file_on_stderr(tmp_path, capsys):
    # Bytes that are not a PNG and are not empty are genuinely corrupt, not
    # transient: say so once, naming the file, and carry on.
    out = make_world(tmp_path)
    png_with_chunks(out / "good.png", PROMPT, WORKFLOW)
    (out / "corrupt.png").write_bytes(b"not a png file")
    assert feed.rebuild(str(tmp_path), "sfw") == 1
    assert "corrupt.png" in capsys.readouterr().err


def test_rebuild_skips_a_png_whose_chunk_stream_is_malformed(tmp_path, capsys):
    # The signature is valid, so the failure lands inside the chunk walk
    # rather than on the "not a PNG" check -- and it raises IndexError, not
    # ValueError (an iTXt payload that ends right after its keyword leaves
    # `rest` empty, and the parser indexes rest[0] for the compression flag).
    # A guard that catches only the ValueError from the observed traceback
    # still crashes here, which is why this fixture exists.
    out = make_world(tmp_path)
    png_with_chunks(out / "good.png", PROMPT, WORKFLOW)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    (out / "malformed.png").write_bytes(
        SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"iTXt", b"prompt\x00")
    )
    with pytest.raises(IndexError):
        feed.read_chunks(out / "malformed.png")  # the parser's own contract
    assert feed.rebuild(str(tmp_path), "sfw") == 1
    assert "malformed.png" in capsys.readouterr().err


def test_rebuild_skips_a_file_that_vanishes_midway(tmp_path, capsys):
    # A dislike unlinks a PNG while a rebuild walks the directory: glob has
    # already yielded the name when read_bytes finds it gone.
    out = make_world(tmp_path)
    png_with_chunks(out / "good.png", PROMPT, WORKFLOW)
    ghost = out / "ghost.png"
    png_with_chunks(ghost, PROMPT, WORKFLOW)
    real_read = pathlib.Path.read_bytes

    def vanishing(self):
        if self.name == "ghost.png":
            raise FileNotFoundError(2, "No such file or directory", str(self))
        return real_read(self)

    pathlib.Path.read_bytes = vanishing
    try:
        assert feed.rebuild(str(tmp_path), "sfw") == 1
    finally:
        pathlib.Path.read_bytes = real_read


# A cap on stored renders (operator, 2026-09-20). Liked renders are exempt:
# they are the search's whole signal, and _scaffold reads the newest of them,
# so deleting one would silently re-point the scaffold -- the same class of
# failure as the liking race that made the scaffold unsettable by hand.


def test_prune_keeps_the_newest_up_to_the_cap(tmp_path):
    out = make_world(tmp_path)
    for i in range(6):
        png = out / f"r{i}.png"
        png_with_chunks(png, PROMPT, WORKFLOW)
        os.utime(png, (1000 + i, 1000 + i))
    feed.rebuild(str(tmp_path), "sfw")
    assert feed.prune(str(tmp_path), "sfw", keep=4) == 2
    left = sorted(p.name for p in out.glob("*.png"))
    assert left == ["r2.png", "r3.png", "r4.png", "r5.png"]


def test_prune_never_deletes_a_liked_render(tmp_path):
    out = make_world(tmp_path)
    for i in range(6):
        png = out / f"r{i}.png"
        png_with_chunks(png, PROMPT, WORKFLOW)
        os.utime(png, (1000 + i, 1000 + i))
    feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    with conn:
        conn.execute("INSERT INTO likes(name, liked_at) VALUES('r0.png', 1)")
    feed.prune(str(tmp_path), "sfw", keep=4)
    left = sorted(p.name for p in out.glob("*.png"))
    assert "r0.png" in left, "the oldest render was liked and must survive"


def test_prune_may_exceed_the_cap_when_likes_do(tmp_path):
    # The cap bounds unliked renders; it never forces a liked one out.
    out = make_world(tmp_path)
    for i in range(5):
        png = out / f"r{i}.png"
        png_with_chunks(png, PROMPT, WORKFLOW)
        os.utime(png, (1000 + i, 1000 + i))
    feed.rebuild(str(tmp_path), "sfw")
    conn = feed.open_db(str(tmp_path), "sfw")
    with conn:
        conn.executemany(
            "INSERT INTO likes(name, liked_at) VALUES(?, 1)",
            [(f"r{i}.png",) for i in range(5)],
        )
    assert feed.prune(str(tmp_path), "sfw", keep=2) == 0
    assert len(list(out.glob("*.png"))) == 5


def test_prune_under_the_cap_deletes_nothing(tmp_path):
    out = make_world(tmp_path)
    png_with_chunks(out / "a.png", PROMPT, WORKFLOW)
    feed.rebuild(str(tmp_path), "sfw")
    assert feed.prune(str(tmp_path), "sfw", keep=500) == 0
    assert len(list(out.glob("*.png"))) == 1


def test_prune_drops_the_rows_of_what_it_deleted(tmp_path):
    out = make_world(tmp_path)
    for i in range(3):
        png = out / f"r{i}.png"
        png_with_chunks(png, PROMPT, WORKFLOW)
        os.utime(png, (1000 + i, 1000 + i))
    feed.rebuild(str(tmp_path), "sfw")
    feed.prune(str(tmp_path), "sfw", keep=1)
    conn = feed.open_db(str(tmp_path), "sfw")
    names = [r[0] for r in conn.execute("SELECT name FROM renders")]
    assert names == ["r2.png"]
