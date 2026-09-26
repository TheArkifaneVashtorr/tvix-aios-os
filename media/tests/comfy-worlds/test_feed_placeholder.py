"""Unit test for pkgs/comfy-worlds/feed_placeholder.py (the GN3 shim).

Loaded by path (like tests/comfy-worlds/test_feed.py) so this test file works
both under `pytest tests/comfy-worlds` from the repo root and inside
checks.comfy-worlds-unit, which copies pkgs/comfy-worlds and tests/comfy-worlds
into a fresh tree without installing anything.
"""

import importlib.util
import pathlib

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "comfy-worlds" / "feed_placeholder.py"
spec = importlib.util.spec_from_file_location("feed_placeholder", SRC)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)


def test_shim_exits_2(capsys):
    code = feed.main([])
    captured = capsys.readouterr()
    assert code == 2
    assert (
        captured.err.strip()
        == "comfy-feed: the placeholder was replaced by feed.py (GN3)"
    )
