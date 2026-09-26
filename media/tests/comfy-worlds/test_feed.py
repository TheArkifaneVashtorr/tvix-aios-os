"""Unit tests for pkgs/comfy-worlds/feed.py.

Loaded by path (like tests/comfy-worlds/test_feed_placeholder.py) so this test
file works both under `pytest tests/comfy-worlds` from the repo root and inside
checks.comfy-worlds-unit, which copies pkgs/comfy-worlds and tests/comfy-worlds
into a fresh tree without installing anything.

GN22: one server serves every configured world — the routes are world-scoped
(`/w/<world>/…`), every POST answers JSON when the request's Accept names
`application/json`, and `build_server` takes a `worlds` dict.
"""

import base64
import http.client
import importlib.util
import json
import os
import pathlib
import re
import signal
import socket
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zlib
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, urlencode

import pytest

# GN2's in-file mirror of tests/mocks/comfy-api-fake.py (test_queue.py already
# asserts it is byte-identical to the canonical file); the comfy-worlds-unit
# check copies tests/comfy-worlds wholesale, so this import resolves identically
# in-tree and inside the check.
from test_queue import FakeComfy

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "comfy-worlds" / "feed.py"
spec = importlib.util.spec_from_file_location("feed", SRC)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)

# The prompt chunk the fixture writes: node 3 (the base sampler) has
# inputs.seed = 42, and node 6's text carries a `<b>` so the page must escape
# it to `<b>` — the prompt is the raw chunk value, not extracted text.
PROMPT = json.dumps(
    {
        "3": {
            "class_type": "KSampler",
            "inputs": {"seed": 42, "positive": ["6", 0], "negative": ["7", 0]},
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "<b>a red apple</b>"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry"}},
    }
)

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def free_port():
    """A loopback port that is free right now (bound then released).

    GN23: the module-level WORLDS fixture claims dead ports per import —
    the interactive run_once (Decision 5) dials each world's comfyPort on
    every regenerate/edit POST, so a fixture pinned to 8188/8189 would
    submit unit-test jobs to the operator's LIVE generator when it runs.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


# GN22: the two-world harness — one server, both worlds configured. GN23:
# the comfyPorts are claimed dead (free_port above) because regenerate and
# edit now run the queue against the world's own ComfyUI address.
WORLDS = {
    "sfw": {"comfyPort": free_port()},
    "nsfw": {"comfyPort": free_port()},
}


def _chunk(ctype, payload):
    return (
        struct.pack(">I", len(payload))
        + ctype
        + payload
        + struct.pack(">I", zlib.crc32(ctype + payload) & 0xFFFFFFFF)
    )


def png_with_prompt(path, prompt_json):
    """Write a minimal valid PNG carrying a `prompt` tEXt chunk."""
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    payload = b"prompt\x00" + prompt_json.encode("latin-1")
    pathlib.Path(path).write_bytes(
        SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"tEXt", payload)
        + _chunk(b"IEND", b"")
    )


def make_world(tmp_path, world="sfw"):
    out = tmp_path / "worlds" / world / "output"
    out.mkdir(parents=True)
    return out


def systemctl_stub(tmp_path, answer, mapping=None, log=None):
    """A stub systemctl that answers `is-active` and exits 0.

    With `mapping` (unit name -> state) the answer is per unit ($3 carries
    the unit name generator_state asks about); with `log` every argv is
    appended to that file, so a test can prove the server never invoked
    systemctl (the unknown-world refusal happens before any argv).
    """
    stub = tmp_path / ("stub-systemctl-" + answer + ("-map" if mapping else ""))
    lines = ["#!/bin/sh"]
    if log is not None:
        lines.append(f"printf '%s\\n' \"$*\" >>{log}")
    lines.append('if [ "$2" = "is-active" ]; then')
    if mapping:
        for unit, state in sorted(mapping.items()):
            lines.append(f'  if [ "$3" = "{unit}" ]; then echo {state}; exit 0; fi')
        lines.append("  echo unknown")
    else:
        lines.append("  echo " + answer)
    lines.append("fi")
    lines.append("exit 0")
    stub.write_text("\n".join(lines) + "\n")
    stub.chmod(0o755)
    return str(stub)


def start(root, systemctl_bin, worlds=None, flip_guard_seconds=30):
    srv = feed.build_server(
        root=root,
        worlds=worlds or WORLDS,
        systemctl=systemctl_bin,
        flip_guard_seconds=flip_guard_seconds,
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    return srv


def _url(srv, path):
    return f"http://127.0.0.1:{srv.server_address[1]}{path}"


def get(srv, path):
    with urllib.request.urlopen(_url(srv, path)) as resp:
        return resp.read().decode()


def get_bytes(srv, path):
    with urllib.request.urlopen(_url(srv, path)) as resp:
        return resp.read()


def status(srv, path):
    try:
        urllib.request.urlopen(_url(srv, path))
    except urllib.error.HTTPError as exc:
        return exc.code
    return 200


def test_index_lists_newest_first_and_escapes(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    os.utime(out / "a.png", (1, 1))
    png_with_prompt(out / "b<x>.png", PROMPT)
    os.utime(out / "b<x>.png", (2, 2))
    srv = start(tmp_path, systemctl_stub(tmp_path, "active"))
    body = get(srv, "/w/sfw/")
    assert body.index("b&lt;x&gt;.png") < body.index("a.png")
    assert "<x>" not in body
    assert "generator active" in body
    assert get(srv, "/healthz") == "ok nsfw,sfw"


def test_out_serves_only_basenames(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    (out / "sub").mkdir()
    png_with_prompt(out / "sub" / "a.png", PROMPT)
    # A name carrying `..` is refused even without a `/`: the `/` guard already
    # blocks the slashed traversal below, so this file is the `..`-guard-only
    # case (dropping the `..` check would serve it with 200).
    png_with_prompt(out / "a..b.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    assert get_bytes(srv, "/w/sfw/out/a.png").startswith(SIGNATURE)
    assert (
        status(srv, "/w/sfw/out/../lab/README.md") == 404
        and status(srv, "/w/sfw/out/%2e%2e/x") == 404
    )
    assert status(srv, "/w/sfw/out/sub/a.png") == 404
    assert status(srv, "/w/sfw/out/a..b.png") == 404
    assert "generator inactive" in get(srv, "/w/sfw/")


def test_page_lists_prompt_and_seed_from_index(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "active"))
    body = get(srv, "/w/sfw/")
    assert "seed 42" in body
    assert "&lt;b&gt;" in body


def test_page_empty_index_200(tmp_path):
    # A fresh world with no renders: the page still renders, status 200.
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    body = get(srv, "/w/sfw/")
    assert "<p>no renders yet</p>" in body


ALLOWED_TAGS = {
    "html",
    "head",
    "meta",
    "title",
    "body",
    "main",
    "article",
    "img",
    "p",
    "span",
    "form",
    "button",
    "input",
    "a",
    "h1",
    "time",
    # GN25: the client's mounts — the stylesheet and the deferred script,
    # both relative-URL'd (the SCHEME check below still forbids any
    # external href/src), the article list staying below them.
    "link",
    "script",
}
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class PageAuditor(HTMLParser):
    """Parses a page and records every zero-outbound rule it violates."""

    def __init__(self):
        super().__init__()
        self.violations = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            self.violations.append(f"tag not allowed: {tag}")
        names = {name for name, _ in attrs}
        if tag == "meta":
            if "http-equiv" in names:
                self.violations.append("meta http-equiv")
            if names != {"charset"}:
                self.violations.append(f"meta attrs: {sorted(names)}")
        for name, value in attrs:
            if name.startswith("on"):
                self.violations.append(f"on-attribute: {name}")
            if name in ("srcset", "style", "ping"):
                self.violations.append(f"forbidden attribute: {name}")
            if value is not None and (SCHEME.match(value) or value.startswith("//")):
                self.violations.append(f"url in {name}={value!r}")


def test_page_is_zero_outbound(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "active"))
    body = get(srv, "/w/sfw/")
    auditor = PageAuditor()
    auditor.feed(body)
    auditor.close()
    assert auditor.violations == []


def test_serve_rebuilds_index_on_start(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    # No explicit rebuild: build_server must rebuild once before serving.
    start(tmp_path, systemctl_stub(tmp_path, "active"))
    conn = sqlite3.connect(tmp_path / "worlds" / "sfw" / "feed.sqlite")
    assert conn.execute("SELECT COUNT(*) FROM renders").fetchone()[0] == 1


def test_index_rebuild_subcommand_prints_count(tmp_path, capsys):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    feed.main(["index", "--rebuild", "--world", "sfw", "--root", str(tmp_path)])
    captured = capsys.readouterr()
    assert captured.out.strip() == "1"
    assert (tmp_path / "worlds" / "sfw" / "feed.sqlite").exists()


# SDXL base-plus-refiner shape: the base sampler (node 3, lowest id, seed 42)
# points its positive input at node 6 and its negative at node 7; the refiner
# sampler (node 10) points its positive at node 8. Nodes 6 and 8 are two
# positive CLIPTextEncode nodes carrying the SAME text ("a red apple"), so
# /edit must rewrite BOTH of them (a first-only replace leaves node 8 stale);
# node 7 is the negative ("blurry") and stays untouched.
EDIT_PROMPT = json.dumps(
    {
        "3": {
            "class_type": "KSampler",
            "inputs": {"seed": 42, "positive": ["6", 0], "negative": ["7", 0]},
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red apple"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry"}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red apple"}},
        "10": {
            "class_type": "KSampler",
            "inputs": {"seed": 99, "positive": ["8", 0]},
        },
    }
)


def png_without_prompt(path):
    """Write a minimal valid PNG carrying no `prompt` chunk (prompt is NULL)."""
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    pathlib.Path(path).write_bytes(
        SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"IEND", b"")
    )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect())


def post(srv, path, data):
    """POST form-encoded `data` and return (status, headers, body) without
    following the 303 redirect."""
    body = urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        _url(srv, path),
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with _OPENER.open(req) as resp:
            return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode()


def post_accept(srv, path, data, accept=None):
    """POST form-encoded `data` with an explicit Accept header, returning
    (status, body)."""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if accept is not None:
        headers["Accept"] = accept
    body = urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        _url(srv, path), data=body, method="POST", headers=headers
    )
    try:
        with _OPENER.open(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def post_json(srv, path, data):
    """POST with `Accept: application/json` — the JSON arm of every verb."""
    return post_accept(srv, path, data, "application/json")


def get_nofollow(srv, path):
    """GET without following a redirect, returning (status, headers, body)."""
    req = urllib.request.Request(_url(srv, path))
    try:
        with _OPENER.open(req) as resp:
            return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read().decode()


def _db(tmp_path, world="sfw"):
    conn = sqlite3.connect(tmp_path / "worlds" / world / "feed.sqlite")
    conn.row_factory = sqlite3.Row
    return conn


def _jobs(tmp_path, kind, world="sfw"):
    return (
        _db(tmp_path, world)
        .execute(
            "SELECT * FROM jobs WHERE kind = ? ORDER BY created DESC, id DESC",
            (kind,),
        )
        .fetchall()
    )


def test_like_writes_one_row_idempotent(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = post(srv, "/w/sfw/like", {"name": "a.png"})
    assert code == 303 and headers.get("Location") == "/#a.png"
    code, _, _ = post(srv, "/w/sfw/like", {"name": "a.png"})
    assert code == 303
    count = _db(tmp_path).execute("SELECT COUNT(*) FROM likes").fetchone()[0]
    assert count == 1


def test_like_unknown_name_404(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, _, _ = post(srv, "/w/sfw/like", {"name": "nope.png"})
    assert code == 404
    count = _db(tmp_path).execute("SELECT COUNT(*) FROM likes").fetchone()[0]
    assert count == 0


def test_regenerate_enqueues_with_different_seed(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = post(srv, "/w/sfw/regenerate", {"name": "a.png"})
    assert code == 303 and "job=" in headers.get("Location", "")
    job = _jobs(tmp_path, "regenerate")[0]
    assert job["state"] == "queued"
    assert job["source"] == "a.png"
    assert job["seed"] != 42


def test_regenerate_without_workflow_409(tmp_path):
    out = make_world(tmp_path)
    png_without_prompt(out / "a.png")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, _, body = post(srv, "/w/sfw/regenerate", {"name": "a.png"})
    assert code == 409
    assert "no workflow recorded for a.png" in body


def test_edit_replaces_prompt_text_and_enqueues(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", EDIT_PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = post(
        srv, "/w/sfw/edit", {"name": "a.png", "prompt": "a new prompt"}
    )
    assert code == 303 and "job=" in headers.get("Location", "")
    job = _jobs(tmp_path, "edit")[0]
    graph = json.loads(job["prompt"])
    assert graph["6"]["inputs"]["text"] == "a new prompt"
    assert graph["8"]["inputs"]["text"] == "a new prompt"
    assert graph["7"]["inputs"]["text"] == "blurry"
    assert job["seed"] != 42


def test_edit_empty_prompt_400(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, _, _ = post(srv, "/w/sfw/edit", {"name": "a.png", "prompt": ""})
    assert code == 400


def test_jobs_lists_rows(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    _, h1, _ = post(srv, "/w/sfw/regenerate", {"name": "a.png"})
    time.sleep(0.02)
    _, h2, _ = post(srv, "/w/sfw/regenerate", {"name": "a.png"})
    job1 = h1["Location"].split("job=")[1]
    job2 = h2["Location"].split("job=")[1]
    body = get(srv, "/w/sfw/jobs")
    lines = body.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].startswith(job2) and lines[1].startswith(job1)  # newest first
    for line in lines:
        fields = line.split()
        assert fields[1] == "queued"
        assert fields[2] == "regenerate"
        assert fields[3] == "a.png"
        assert int(fields[4]) != 42


def test_queue_run_once_reaches_only_loopback(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, _, _ = post(srv, "/w/sfw/regenerate", {"name": "a.png"})
    assert code == 303
    fake = FakeComfy()
    fake.start()
    try:
        feed.main(
            [
                "queue",
                "--run-once",
                "--world",
                "sfw",
                "--root",
                str(tmp_path),
                "--base-url",
                fake.url,
            ]
        )
        assert fake.prompts, "run_once submitted nothing to the fake ComfyUI"
        assert fake.prompts[-1]["prompt"]["3"]["inputs"]["seed"] != 42
    finally:
        fake.stop()


def _raw_post(srv, path, content_length, body=b""):
    """POST with a raw (possibly bogus) `Content-Length` header, returning the
    status. `body` is sent as-is, so a declared length over the cap is answered
    from the header alone while the full body is still transmitted."""
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1])
    conn.request(
        "POST",
        path,
        body=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": content_length,
        },
    )
    resp = conn.getresponse()
    status = resp.status
    resp.read()
    conn.close()
    return status


# A graph whose base KSampler points its `positive` input nowhere: node 3 is a
# KSampler with no `positive`/`negative` inputs, so `_positive_text` returns
# `None`, while node 6 is a text-less CLIPTextEncode node.
NO_POSITIVE_PROMPT = json.dumps(
    {
        "3": {"class_type": "KSampler", "inputs": {"seed": 42}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {}},
    }
)


def test_page_shows_positive_text_not_raw_graph(tmp_path):
    # Addendum item 1: the `<p>` renders the extracted positive text, never the
    # raw class_type graph. The render's `prompt` chunk is the graph; the page
    # must show only its positive text (escaped), so `class_type` never leaks.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "active"))
    body = get(srv, "/w/sfw/")
    assert "&lt;b&gt;" in body
    assert "class_type" not in body


def test_routes_quote_names_with_query_and_fragment_chars(tmp_path):
    # Addendum item 2: a render name carrying `?` and `#` round-trips — the
    # <a>/<img> href percent-quotes the name, so /w/sfw/out/a%3Fb%23c.png
    # serves the file, and /w/sfw/like with the raw name upserts the right
    # `likes` row.
    out = make_world(tmp_path)
    png_with_prompt(out / "a?b#c.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    # The page must emit the percent-quoted href: a raw `?`/`#` would break the
    # link (the browser drops the query/fragment, requesting /w/sfw/out/a).
    body = get(srv, "/w/sfw/")
    assert 'href="/w/sfw/out/a%3Fb%23c.png"' in body
    # The quoted path serves the file and like upserts the right likes row.
    assert get_bytes(srv, "/w/sfw/out/a%3Fb%23c.png").startswith(SIGNATURE)
    code, headers, _ = post(srv, "/w/sfw/like", {"name": "a?b#c.png"})
    assert code == 303
    row = _db(tmp_path).execute("SELECT name FROM likes").fetchone()
    assert row["name"] == "a?b#c.png"


def test_post_body_over_cap_is_413(tmp_path):
    # MINOR-5: a declared Content-Length over the cap (64 KiB) is refused with
    # 413 before the handler reads the body — the write surface Caddy fronts
    # once the LAN flip lands. No job may be written for the refused POST.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    body = b"name=" + b"x" * 70000
    code = _raw_post(srv, "/w/sfw/regenerate", str(len(body)), body)
    assert code == 413
    # The refusal happens before the handler reads the body or touches the
    # queue, so no `jobs` table is ever created (nothing was enqueued).
    conn = _db(tmp_path)
    assert (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='jobs'"
        ).fetchone()
        is None
    )


def test_post_non_integer_content_length_400(tmp_path):
    # Interface 8: a non-integer Content-Length answers 400 instead of raising
    # out of the handler (which would reset the connection).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code = _raw_post(srv, "/w/sfw/regenerate", "abc", b"name=a.png")
    assert code == 400


def test_edit_with_no_positive_text_leaves_graph_unchanged_and_enqueues(tmp_path):
    # MINOR-4: with no stored positive text (`_positive_text` returns None)
    # there is nothing for the equality check to match, so `_edit` must leave
    # every CLIPTextEncode node unchanged (the old `inputs.get("text") ==
    # positive` matched every text-less node) and still enqueue kind `edit`.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", NO_POSITIVE_PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = post(srv, "/w/sfw/edit", {"name": "a.png", "prompt": "new text"})
    assert code == 303 and "job=" in headers.get("Location", "")
    job = _jobs(tmp_path, "edit")[0]
    graph = json.loads(job["prompt"])
    assert graph["6"]["inputs"] == {}
    assert job["seed"] != 42


# --- GN22: one server, every world ------------------------------------------


def test_root_redirects_to_active_world(tmp_path):
    # GN22 Interfaces 2: GET / is a 302 to the world whose generator is
    # active — sfw here, NOT worldsOrder[0] (nsfw sorts first), so a mutant
    # that ignores generator_state and always answers the head goes red.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    stub = systemctl_stub(
        tmp_path,
        "",
        mapping={"comfyui-sfw": "active", "comfyui-nsfw": "inactive"},
    )
    srv = start(tmp_path, stub)
    code, headers, _ = get_nofollow(srv, "/")
    assert code == 302
    assert headers.get("Location") == "/w/sfw/"


def test_root_redirects_to_worldsorder_head_when_none_active(tmp_path):
    # No generator active: the head of worldsOrder (sorted names) — nsfw.
    make_world(tmp_path)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = get_nofollow(srv, "/")
    assert code == 302
    assert headers.get("Location") == "/w/nsfw/"


def test_unknown_world_404_on_every_verb(tmp_path):
    # GN22 Interfaces 3: an unknown world is a 404 before any db open, any
    # unlink and any systemctl argv — the name is matched against the
    # configured list, never interpolated.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    log = tmp_path / "systemctl.log"
    log.write_text("")  # pre-created: absent argv must leave it empty
    srv = start(tmp_path, systemctl_stub(tmp_path, "active", log=log))
    assert get_nofollow(srv, "/w/nope/")[0] == 404
    assert get_nofollow(srv, "/w/nope/out/a.png")[0] == 404
    assert get_nofollow(srv, "/w/nope/jobs")[0] == 404
    for verb, data in (
        ("like", {"name": "a.png"}),
        ("dislike", {"name": "a.png"}),
        ("regenerate", {"name": "a.png"}),
        ("edit", {"name": "a.png", "prompt": "x"}),
        ("dwell", {"seconds": "1"}),
    ):
        assert post(srv, f"/w/nope/{verb}", data)[0] == 404
    assert log.read_text() == ""
    count = _db(tmp_path).execute("SELECT COUNT(*) FROM likes").fetchone()[0]
    assert count == 0


def test_healthz_names_every_world(tmp_path):
    # Decision 10: healthz names every configured world (worldsOrder), not
    # one.
    make_world(tmp_path)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    assert get(srv, "/healthz") == "ok nsfw,sfw"


def test_out_is_world_scoped(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    assert get_bytes(srv, "/w/sfw/out/a.png").startswith(SIGNATURE)
    assert status(srv, "/w/nsfw/out/a.png") == 404


def test_post_json_arm_per_verb(tmp_path):
    # GN22 Interfaces 4: with Accept: application/json every verb answers
    # JSON — like/dislike carry the name, regenerate/edit the job id, dwell
    # the seconds.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    png_with_prompt(out / "b.png", PROMPT)
    png_with_prompt(out / "c.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, body = post_json(srv, "/w/sfw/like", {"name": "a.png"})
    assert code == 200
    assert json.loads(body) == {"ok": True, "name": "a.png"}
    code, body = post_json(srv, "/w/sfw/dislike", {"name": "b.png"})
    assert code == 200
    assert json.loads(body) == {"ok": True, "name": "b.png", "deleted": True}
    assert not (out / "b.png").exists()
    code, body = post_json(srv, "/w/sfw/regenerate", {"name": "c.png"})
    doc = json.loads(body)
    assert code == 200 and doc["ok"] is True and doc["job"]
    assert _jobs(tmp_path, "regenerate")[0]["id"] == doc["job"]
    code, body = post_json(srv, "/w/sfw/edit", {"name": "c.png", "prompt": "a new one"})
    doc = json.loads(body)
    assert code == 200 and doc["ok"] is True and doc["job"]
    code, body = post_json(srv, "/w/sfw/dwell", {"seconds": "30"})
    assert code == 200
    assert json.loads(body) == {"ok": True, "seconds": 30}


def test_post_303_arm_unchanged(tmp_path):
    # GN22 Interfaces 4: without the Accept token, today's answers hold —
    # the 303 Locations and the dwell 204, byte-for-byte.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    png_with_prompt(out / "b.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = post(srv, "/w/sfw/like", {"name": "a.png"})
    assert code == 303 and headers.get("Location") == "/#a.png"
    code, headers, _ = post(srv, "/w/sfw/dislike", {"name": "b.png"})
    assert code == 303 and headers.get("Location") == "/#b.png"
    code, headers, _ = post(srv, "/w/sfw/regenerate", {"name": "a.png"})
    assert code == 303 and headers.get("Location", "").startswith("/?job=")
    code, headers, _ = post(srv, "/w/sfw/edit", {"name": "a.png", "prompt": "x"})
    assert code == 303 and headers.get("Location", "").startswith("/?job=")
    assert post(srv, "/w/sfw/dwell", {"seconds": "1"})[0] == 204


def test_json_error_bodies(tmp_path):
    # GN22 Interfaces 4: on the JSON arm every error body is
    # {"ok": false, "error": <message>} at the same status — never a 200.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, body = post_json(srv, "/w/sfw/like", {"name": "nope.png"})
    assert code == 404
    assert json.loads(body) == {"ok": False, "error": "not found"}
    code, body = post_json(srv, "/w/sfw/edit", {"name": "a.png", "prompt": ""})
    assert code == 400
    assert json.loads(body) == {"ok": False, "error": "empty prompt"}
    code, body = post_json(srv, "/w/sfw/dwell", {"seconds": "-1"})
    assert code == 400
    assert json.loads(body) == {"ok": False, "error": "bad seconds"}
    code, body = post_json(srv, "/w/nope/like", {"name": "a.png"})
    assert code == 404
    assert json.loads(body) == {"ok": False, "error": "not found"}


def test_accept_token_rule(tmp_path):
    # GN22 Interfaces 4: the Accept rule is token equality after stripping
    # `;`-params — comma-split, case-insensitive. `text/json` is NOT
    # application/json; `application/json; q=0.9` IS.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    for accept in ("text/plain; charset=utf-8", "application/xml", "text/json"):
        code, _ = post_accept(srv, "/w/sfw/like", {"name": "a.png"}, accept)
        assert code == 303, (accept, code)
    for accept in ("application/json", "APPLICATION/JSON", "application/json; q=0.9"):
        code, body = post_accept(srv, "/w/sfw/like", {"name": "a.png"}, accept)
        assert code == 200 and json.loads(body)["ok"] is True, (accept, code)
    # A comma list selects on the second token, after the first token's
    # params are stripped.
    code, body = post_accept(
        srv,
        "/w/sfw/like",
        {"name": "a.png"},
        "text/plain; charset=utf-8, application/json",
    )
    assert code == 200 and json.loads(body)["ok"] is True


def test_shell_forms_post_world_scoped(tmp_path):
    # GN22 Interfaces 2: the article shell's forms post to the world-scoped
    # paths, and the img href is world-scoped too.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    body = get(srv, "/w/sfw/")
    for verb in ("like", "dislike", "regenerate", "edit"):
        assert f'<form method="post" action="/w/sfw/{verb}">' in body
    assert 'src="/w/sfw/out/a.png"' in body
    assert 'href="/w/sfw/out/a.png"' in body


def test_jobs_is_world_scoped(tmp_path):
    sfw_out = make_world(tmp_path, "sfw")
    nsfw_out = make_world(tmp_path, "nsfw")
    png_with_prompt(sfw_out / "a.png", PROMPT)
    png_with_prompt(nsfw_out / "b.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    assert post(srv, "/w/sfw/regenerate", {"name": "a.png"})[0] == 303
    assert post(srv, "/w/nsfw/regenerate", {"name": "b.png"})[0] == 303
    time.sleep(0.02)
    assert post(srv, "/w/sfw/regenerate", {"name": "a.png"})[0] == 303
    sfw_lines = get(srv, "/w/sfw/jobs").strip().splitlines()
    nsfw_lines = get(srv, "/w/nsfw/jobs").strip().splitlines()
    assert len(sfw_lines) == 2
    assert all(line.split()[3] == "a.png" for line in sfw_lines)
    assert len(nsfw_lines) == 1
    assert nsfw_lines[0].split()[3] == "b.png"
    # The unscoped /jobs of the per-world server is gone.
    assert status(srv, "/jobs") == 404


def _worlds_file(tmp_path, doc):
    f = tmp_path / "worlds.json"
    f.write_text(json.dumps(doc))
    return f


def _serve_argv(tmp_path, f):
    return [
        "serve",
        "--root",
        str(tmp_path),
        "--port",
        "0",
        "--listen",
        "127.0.0.1",
        "--worlds-file",
        str(f),
    ]


def test_serve_refuses_empty_worlds_file(tmp_path, capsys):
    # GN22 Interfaces 1 and 5: an empty worlds dict is refused before any
    # socket — ValueError from build_server, exit 2 from main.
    with pytest.raises(ValueError, match="feed: at least one world is required"):
        feed.build_server(str(tmp_path), {}, "systemctl")
    f = _worlds_file(tmp_path, {"worlds": {}})
    with pytest.raises(SystemExit) as exc:
        feed.main(_serve_argv(tmp_path, f))
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert str(f) in err
    assert 'must carry a non-empty "worlds" object' in err


def test_serve_refuses_bad_port_worlds_file(tmp_path, capsys):
    f = _worlds_file(tmp_path, {"worlds": {"sfw": {"comfyPort": 0}}})
    with pytest.raises(SystemExit) as exc:
        feed.main(_serve_argv(tmp_path, f))
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert str(f) in err
    assert "sfw" in err
    assert "comfyPort" in err


def test_serve_refuses_missing_worlds_key(tmp_path, capsys):
    f = _worlds_file(tmp_path, {"root": "/x"})
    with pytest.raises(SystemExit) as exc:
        feed.main(_serve_argv(tmp_path, f))
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert str(f) in err
    assert 'must carry a non-empty "worlds" object' in err


# --- GN8: engagement counts posted to Helm's /v1/engage on loopback ---------


class FakeEngage:
    """A loopback HTTP server mirroring Helm's landed HM8 route
    (`pkgs/helm/api_engage.py` in nixos-agent-env): a JSON body with exactly
    the `counter`/`n`/`surface` keys, a known counter and surface and a
    positive integer `n` answers 204 and is recorded in `accepted`; anything
    else answers 400 with `{"error": "<field>"}`. Every JSON body received is
    recorded in `bodies` (so the privacy test sees a leaked key even when the
    route would refuse it). `refuse` names extra counters to refuse with 400
    even when valid, `redirect_to` answers a 302 with that Location instead
    of folding, and `malformed` sends a non-HTTP status line (the
    restarting-helm-api case: a `BadStatusLine`, an HTTPException not an
    OSError)."""

    COUNTERS = ("opens", "dwell_s", "feed_likes")
    SURFACES = ("home", "feed", "seats")

    def __init__(self, refuse=(), redirect_to=None, malformed=False):
        self.refuse = set(refuse)
        self.redirect_to = redirect_to
        self.malformed = malformed
        self.bodies = []
        self.accepted = []
        self.connections = 0
        self.last_headers = None

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle(self):
            self.server._fake.connections += 1
            super().handle()

        def do_POST(self):
            fake = self.server._fake
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            fake.last_headers = {k.lower(): v for k, v in self.headers.items()}
            if fake.malformed:
                self.wfile.write(b"not a status line\r\n")
                self.wfile.flush()
                self.close_connection = True
                return
            body = json.loads(raw.decode("utf-8"))
            fake.bodies.append(body)
            if fake.redirect_to is not None:
                self.send_response(302)
                self.send_header("Location", fake.redirect_to)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            # The landed route's checks, verbatim in shape (api_engage.py).
            if not isinstance(body, dict) or set(body) != {"counter", "n", "surface"}:
                self._answer(400, {"error": "body"})
                return
            counter = body["counter"]
            if counter not in fake.COUNTERS:
                self._answer(400, {"error": "counter"})
                return
            surface = body["surface"]
            if surface not in fake.SURFACES:
                self._answer(400, {"error": "surface"})
                return
            n = body["n"]
            if isinstance(n, bool) or not isinstance(n, int) or n < 1:
                self._answer(400, {"error": "n"})
                return
            if counter in fake.refuse:
                self._answer(400, {"error": "counter"})
                return
            fake.accepted.append(body)
            self._answer(204)

        def _answer(self, code, payload=None):
            data = json.dumps(payload).encode("utf-8") if payload is not None else b""
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if data:
                self.wfile.write(data)

    def start(self):
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._Handler)
        self._server._fake = self
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self._server.server_address[1]}/v1/engage"

    def stop(self):
        self._server.shutdown()
        self._server.server_close()


def start_engage(tmp_path, systemctl_bin, engage_url, flush_interval=3600):
    srv = feed.build_server(
        root=str(tmp_path),
        worlds={"sfw": {"comfyPort": 8188}},
        systemctl=systemctl_bin,
        engage_url=engage_url,
        flush_interval=flush_interval,
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    return srv


def _wait_healthz(port, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/healthz", timeout=0.5
            ) as resp:
                if resp.status == 200:
                    return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("healthz never answered")


def test_open_and_like_increment_counters(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage()
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        get(srv, "/w/sfw/")
        get(srv, "/w/sfw/")
        post(srv, "/w/sfw/like", {"name": "a.png"})
        srv.engage.flush()
        counts = {body["counter"]: body["n"] for body in fake.bodies}
        assert counts["opens"] == 2
        assert counts["feed_likes"] == 1
    finally:
        fake.stop()


def test_dwell_boundaries(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage()
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        assert post(srv, "/w/sfw/dwell", {"seconds": "0"})[0] == 204
        assert post(srv, "/w/sfw/dwell", {"seconds": "86400"})[0] == 204
        assert post(srv, "/w/sfw/dwell", {"seconds": "-1"})[0] == 400
        assert post(srv, "/w/sfw/dwell", {"seconds": "86401"})[0] == 400
        assert post(srv, "/w/sfw/dwell", {"seconds": "x"})[0] == 400
    finally:
        fake.stop()


def test_flush_posts_one_body_per_counter_and_resets(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage()
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        get(srv, "/w/sfw/")
        post(srv, "/w/sfw/like", {"name": "a.png"})
        post(srv, "/w/sfw/dwell", {"seconds": "30"})
        srv.engage.flush()
        assert len(fake.bodies) == 3
        assert {body["counter"] for body in fake.bodies} == {
            "opens",
            "dwell_s",
            "feed_likes",
        }
        srv.engage.flush()
        assert len(fake.bodies) == 3
    finally:
        fake.stop()


def test_engage_body_carries_no_content(tmp_path):
    out = make_world(tmp_path)
    marker = "MARKER-secret-prompt-text"
    marker_prompt = json.dumps(
        {
            "3": {
                "class_type": "KSampler",
                "inputs": {"seed": 42, "positive": ["6", 0], "negative": ["7", 0]},
            },
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": marker}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry"}},
        }
    )
    png_with_prompt(out / "secret.png", marker_prompt)
    fake = FakeEngage()
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        get(srv, "/w/sfw/")
        get(srv, "/w/sfw/")
        post(srv, "/w/sfw/like", {"name": "secret.png"})
        post(srv, "/w/sfw/dwell", {"seconds": "12"})
        srv.engage.flush()
        for body in fake.bodies:
            assert set(body) == {"counter", "n", "surface"}
            assert body["surface"] == "feed"
            dumped = json.dumps(body)
            assert marker not in dumped
            assert "secret.png" not in dumped
            assert "sfw" not in dumped
    finally:
        fake.stop()


def test_flush_unreachable_keeps_count_for_retry(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    url = f"http://127.0.0.1:{free_port()}/v1/engage"
    srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), url)
    get(srv, "/w/sfw/")
    srv.engage.flush()
    # Unreachable: the counter is kept for the next tick, not dropped.
    assert srv.engage._counters["opens"] == 1
    srv.engage.flush()
    assert srv.engage._counters["opens"] == 1


def test_flush_non_204_keeps_count_for_retry(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage(refuse={"opens"})
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        get(srv, "/w/sfw/")
        srv.engage.flush()
        # Refused with 400: the counter is kept for the next tick, not dropped.
        assert srv.engage._counters["opens"] == 1
    finally:
        fake.stop()


def test_periodic_flush_fires(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage()
    fake.start()
    try:
        srv = start_engage(
            tmp_path,
            systemctl_stub(tmp_path, "inactive"),
            fake.url,
            flush_interval=0.2,
        )
        get(srv, "/w/sfw/")
        time.sleep(0.6)
        assert any(body["counter"] == "opens" for body in fake.bodies)
    finally:
        fake.stop()


def test_sigterm_flushes(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage()
    fake.start()
    try:
        port = free_port()
        worlds_file = _worlds_file(tmp_path, {"worlds": {"sfw": {"comfyPort": 8188}}})
        proc = subprocess.Popen(
            [
                sys.executable,
                str(SRC),
                "serve",
                "--root",
                str(tmp_path),
                "--port",
                str(port),
                "--listen",
                "127.0.0.1",
                "--worlds-file",
                str(worlds_file),
                "--engage-url",
                fake.url,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            _wait_healthz(port)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/w/sfw/") as resp:
                resp.read()
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=5)
            assert proc.returncode == 0
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
    finally:
        fake.stop()
    assert any(body["counter"] == "opens" for body in fake.bodies)


def test_engage_url_non_loopback_refused(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    with pytest.raises(ValueError):
        feed.build_server(
            str(tmp_path),
            {"sfw": {"comfyPort": 8188}},
            systemctl_stub(tmp_path, "inactive"),
            engage_url="http://example.com/v1/engage",
        )


# --- GN8b: the beacon speaks HM8's landed enum, per-counter posts -----------


def test_counter_enum_matches_landed_helm_route():
    # pkgs/helm/api_engage.py:24 in nixos-agent-env
    fixture = ("opens", "dwell_s", "feed_likes")
    assert feed.Engagement.COUNTERS == fixture


def test_dwell_400_still_posts_opens_and_feed_likes(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage(refuse={"dwell_s"})
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        get(srv, "/w/sfw/")  # opens = 1
        post(srv, "/w/sfw/dwell", {"seconds": "30"})  # dwell_s = 30
        post(srv, "/w/sfw/like", {"name": "a.png"})  # feed_likes = 1
        srv.engage.flush()
        # The refused dwell_s never blocks its neighbours: opens and
        # feed_likes are posted, dwell_s keeps its count for the next tick.
        assert {body["counter"] for body in fake.accepted} == {"opens", "feed_likes"}
        assert srv.engage._counters["dwell_s"] == 30
        fake.refuse.clear()
        srv.engage.flush()
        assert any(
            body["counter"] == "dwell_s" and body["n"] == 30 for body in fake.accepted
        )
        assert srv.engage._counters["dwell_s"] == 0
    finally:
        fake.stop()


def test_engage_url_userinfo_trick_refused(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    # The parsed-host guard sees hostname `example.com`, not the `127.0.0.1`
    # userinfo the string prefix would have accepted.
    with pytest.raises(ValueError, match="feed: engage-url is loopback-only"):
        feed.build_server(
            str(tmp_path),
            {"sfw": {"comfyPort": 8188}},
            systemctl_stub(tmp_path, "inactive"),
            engage_url="http://127.0.0.1:7710@example.com/v1/engage",
        )


def test_beacon_does_not_follow_redirect(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage()
    fake.start()
    try:
        # Point the 302 back at the fake's own loopback address: a redirect-
        # following opener would open a second connection to it, which the
        # fake counts. The beacon's opener refuses the redirect, so exactly
        # one connection is ever accepted and no second host is contacted.
        fake.redirect_to = fake.url + "?collect"
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        get(srv, "/w/sfw/")
        srv.engage.flush()
        assert fake.connections == 1
        assert srv.engage._counters["opens"] == 1  # refused, kept for retry
    finally:
        fake.stop()


def test_beacon_survives_malformed_response(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage(malformed=True)
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        get(srv, "/w/sfw/")
        srv.engage.flush()  # BadStatusLine must not propagate out of flush()
        assert srv.engage._counters["opens"] == 1
        fake.malformed = False
        srv.engage.flush()
        assert any(body["counter"] == "opens" for body in fake.bodies)
    finally:
        fake.stop()


def test_beacon_sets_json_content_type_and_logs_success(tmp_path, capsys):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage()
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        get(srv, "/w/sfw/")
        post(srv, "/w/sfw/dwell", {"seconds": "30"})
        post(srv, "/w/sfw/like", {"name": "a.png"})
        srv.engage.flush()
        assert fake.last_headers["content-type"] == "application/json"
        err = capsys.readouterr().err
        assert f"engage: posted 3 bodies to {fake.url}" in err
    finally:
        fake.stop()


# --- GN13: POST /dislike — the negative verdict, then the PNG gone -------


def test_dislike_records_prompt_text_and_deletes_png(tmp_path):
    # GN13 Interfaces 2: on a hit, the row is upserted with the render's
    # positive text (extracted as `_article` extracts it — the raw text,
    # never the graph), the PNG is deleted, and the answer is the same 303
    # redirect shape `_like` uses.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = post(srv, "/w/sfw/dislike", {"name": "a.png"})
    assert code == 303 and headers.get("Location") == "/#a.png"
    rows = _db(tmp_path).execute("SELECT name, prompt FROM dislikes").fetchall()
    assert len(rows) == 1
    assert rows[0]["name"] == "a.png"
    assert rows[0]["prompt"] == "<b>a red apple</b>"
    assert not (out / "a.png").exists()


def test_dislike_idempotent_before_rebuild(tmp_path):
    # GN13 Interfaces 3: a repeated POST finds the `renders` row still
    # present (only the PNG was deleted), upserts ONE row, answers 303.
    # After a rebuild the row is gone and the repeat answers 404 — the
    # recorded dislike survives either way.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, _, _ = post(srv, "/w/sfw/dislike", {"name": "a.png"})
    assert code == 303
    code, _, _ = post(srv, "/w/sfw/dislike", {"name": "a.png"})
    assert code == 303
    count = _db(tmp_path).execute("SELECT COUNT(*) FROM dislikes").fetchone()[0]
    assert count == 1
    feed.feed_index.rebuild(tmp_path, "sfw")
    code, _, _ = post(srv, "/w/sfw/dislike", {"name": "a.png"})
    assert code == 404
    count = _db(tmp_path).execute("SELECT COUNT(*) FROM dislikes").fetchone()[0]
    assert count == 1


def test_dislike_unknown_name_404(tmp_path):
    # GN13 Interfaces 2: an unknown name is a 404 — nothing written, nothing
    # deleted.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, _, _ = post(srv, "/w/sfw/dislike", {"name": "nope.png"})
    assert code == 404
    count = _db(tmp_path).execute("SELECT COUNT(*) FROM dislikes").fetchone()[0]
    assert count == 0
    assert (out / "a.png").exists()


def test_dislike_percent_encoded_name(tmp_path):
    # GN13 Interfaces 2c: the 303 redirects to `/#<quote(name, safe="")>` —
    # a name carrying `?` and `#` round-trips through the redirect and the
    # row records the raw name.
    out = make_world(tmp_path)
    png_with_prompt(out / "a?b#c.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = post(srv, "/w/sfw/dislike", {"name": "a?b#c.png"})
    assert code == 303
    assert headers.get("Location") == "/#a%3Fb%23c.png"
    row = _db(tmp_path).execute("SELECT name, prompt FROM dislikes").fetchone()
    assert row["name"] == "a?b#c.png"
    assert not (out / "a?b#c.png").exists()


def test_dislike_record_survives_failed_delete(tmp_path, monkeypatch, capsys):
    # GN13 Interfaces 2: record-before-delete, in that exact order — a stuck
    # file must not lose the verdict. The stub records whether the `dislikes`
    # row was already durable at the moment the delete was attempted, then
    # raises; the handler catches, names the file on stderr, still sends 303.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    recorded_when_delete_tried = {}

    def stuck_unlink(self, missing_ok=False):
        conn = sqlite3.connect(tmp_path / "worlds" / "sfw" / "feed.sqlite")
        recorded_when_delete_tried["dislikes"] = conn.execute(
            "SELECT COUNT(*) FROM dislikes"
        ).fetchone()[0]
        conn.close()
        raise OSError(f"stuck file: {self}")

    monkeypatch.setattr(pathlib.Path, "unlink", stuck_unlink)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = post(srv, "/w/sfw/dislike", {"name": "a.png"})
    assert code == 303 and headers.get("Location") == "/#a.png"
    assert recorded_when_delete_tried["dislikes"] == 1
    rows = _db(tmp_path).execute("SELECT name, prompt FROM dislikes").fetchall()
    assert len(rows) == 1
    assert rows[0]["prompt"] == "<b>a red apple</b>"
    assert "a.png" in capsys.readouterr().err


def test_dislike_without_graph_still_records(tmp_path):
    # GN13 Interfaces 2a: a render with no extractable text stores the empty
    # string — recorded, never skipped.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", "not a graph")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, _, _ = post(srv, "/w/sfw/dislike", {"name": "a.png"})
    assert code == 303
    row = _db(tmp_path).execute("SELECT prompt FROM dislikes").fetchone()
    assert row["prompt"] == ""


def test_dislike_posts_no_engagement_counter(tmp_path):
    # GN13 Interfaces 5: the engagement beacon is untouched — no counter
    # increments on a dislike (the counts-only contract, spec §5).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage()
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        code, _, _ = post(srv, "/w/sfw/dislike", {"name": "a.png"})
        assert code == 303
        srv.engage.flush()
        assert fake.bodies == []
        assert srv.engage._counters == {
            "opens": 0,
            "dwell_s": 0,
            "feed_likes": 0,
        }
    finally:
        fake.stop()


def test_dislike_button_rendered(tmp_path):
    # GN13 Interfaces 4: `_article` renders a dislike form with the same
    # hidden `name` field, beside the like form, both world-scoped. Every
    # other test POSTs the route directly, so without this one the buttons
    # could be deleted from `_article` and nothing would go red.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    body = get(srv, "/w/sfw/")
    start_idx = body.index('<form method="post" action="/w/sfw/dislike">')
    form_html = body[start_idx : body.index("</form>", start_idx)]
    assert '<input type="hidden" name="name" value="a.png">' in form_html
    assert "<button" in form_html


# --- GN23: the deck — unseen-first cards, seen on consume, low water ------


def get_json(srv, path):
    """GET a route that answers JSON, parsed."""
    return json.loads(get(srv, path))


def post_pairs(srv, path, pairs, accept=None):
    """POST urlencoded `pairs` (a list, so repeated fields survive) with an
    optional Accept header, returning (status, body)."""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if accept is not None:
        headers["Accept"] = accept
    body = urlencode(pairs).encode("utf-8")
    req = urllib.request.Request(
        _url(srv, path), data=body, method="POST", headers=headers
    )
    try:
        with _OPENER.open(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


# A second prompt graph: seed 77, a different positive text — the in-place
# overwrite in test_new_render_appears_in_deck must reach the index.
OTHER_PROMPT = json.dumps(
    {
        "3": {
            "class_type": "KSampler",
            "inputs": {"seed": 77, "positive": ["6", 0]},
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "another apple"}},
    }
)


def _deck(srv, path="/w/sfw/deck"):
    return get_json(srv, path)


def test_deck_serves_unseen_before_history(tmp_path):
    # GN23 Interfaces 2: the unseen lead — a seen card NEWER than an unseen
    # one still sorts after it (the unseen key precedes mtime), and within
    # each group the newest leads (mtime DESC, name ASC as the last key).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    os.utime(out / "a.png", (10, 10))
    png_with_prompt(out / "b.png", PROMPT)
    os.utime(out / "b.png", (20, 20))
    png_with_prompt(out / "c.png", PROMPT)
    os.utime(out / "c.png", (30, 30))
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, body = post_pairs(srv, "/w/sfw/seen", [("names", "b.png")])
    assert code == 303
    doc = _deck(srv)
    assert [card["name"] for card in doc["cards"]] == ["c.png", "a.png", "b.png"]


def test_deck_cursor_advances(tmp_path):
    # Interfaces 3: the cursor carries the keyset (unseen-key, mtime, name)
    # so a page asks for what follows its last row — no overlap, no skip.
    out = make_world(tmp_path)
    for name, mtime in (("a.png", 1), ("b.png", 2), ("c.png", 3)):
        png_with_prompt(out / name, PROMPT)
        os.utime(out / name, (mtime, mtime))
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    page1 = _deck(srv, "/w/sfw/deck?n=2")
    assert [card["name"] for card in page1["cards"]] == ["c.png", "b.png"]
    assert page1["cursor"] is not None
    page2 = _deck(srv, "/w/sfw/deck?n=2&cursor=" + quote(page1["cursor"]))
    assert [card["name"] for card in page2["cards"]] == ["a.png"]
    assert not (
        {c["name"] for c in page1["cards"]} & {c["name"] for c in page2["cards"]}
    )
    assert page2["cursor"] is None


def test_deck_n_capped_400(tmp_path):
    # Interfaces 3 / Decision 14: n is an int 1–50 (default 10); outside
    # that the deck answers 400 — JSON, like every deck answer.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    for n in ("51", "0", "abc"):
        code, _, body = get_nofollow(srv, f"/w/sfw/deck?n={n}")
        assert code == 400, (n, code)
        assert json.loads(body) == {"ok": False, "error": "bad n"}
    for n in ("1", "50"):
        code, _, _ = get_nofollow(srv, f"/w/sfw/deck?n={n}")
        assert code == 200, (n, code)


def test_deck_bad_cursor_400(tmp_path):
    # Interfaces 3: a cursor that is not the base64 of
    # `u:<0|1>:<mtime>:<name>` is a 400, and a well-formed cursor past
    # every row serves an empty page.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    for cursor in ("garbage", base64.b64encode(b"not a cursor").decode()):
        code, _, body = get_nofollow(srv, "/w/sfw/deck?cursor=" + quote(cursor))
        assert code == 400
        assert json.loads(body) == {"ok": False, "error": "bad cursor"}
    past_end = base64.b64encode(b"u:1:99.0:zz.png").decode()
    code, _, body = get_nofollow(srv, "/w/sfw/deck?cursor=" + quote(past_end))
    assert code == 200
    assert json.loads(body)["cards"] == []


def test_deck_card_shape(tmp_path):
    # Interfaces 3: the card keys — name, img (the percent-quoted /out/ path,
    # the same quoting discipline as the page's hrefs), prompt (the extracted
    # positive text, null when the graph yields none), seed, mtime, liked.
    out = make_world(tmp_path)
    png_with_prompt(out / "a?b.png", PROMPT)
    os.utime(out / "a?b.png", (2, 2))
    png_without_prompt(out / "plain.png")
    os.utime(out / "plain.png", (1, 1))
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    doc = _deck(srv)
    assert doc["world"] == "sfw"
    cards = {card["name"]: card for card in doc["cards"]}
    assert set(cards) == {"a?b.png", "plain.png"}
    card = cards["a?b.png"]
    assert card["img"] == "/w/sfw/out/a%3Fb.png"
    assert card["prompt"] == "<b>a red apple</b>"
    assert card["seed"] == 42
    assert card["mtime"] == 2.0
    assert card["liked"] is False
    plain = cards["plain.png"]
    assert plain["prompt"] is None
    assert plain["seed"] is None
    # liked arrives through the likes join
    assert post(srv, "/w/sfw/like", {"name": "a?b.png"})[0] == 303
    cards = {card["name"]: card for card in _deck(srv)["cards"]}
    assert cards["a?b.png"]["liked"] is True


def test_seen_records_only_on_consume(tmp_path):
    # Interfaces 4: a deck GET SERVES cards — it never marks them seen;
    # only the POST /w/<w>/seen route writes the table.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    doc = _deck(srv)
    assert [card["name"] for card in doc["cards"]] == ["a.png"]
    count = _db(tmp_path).execute("SELECT COUNT(*) FROM seen").fetchone()[0]
    assert count == 0


def test_seen_upserts_and_counts(tmp_path):
    # Interfaces 4 / Decision 3: every `names` form value (repeated field)
    # upserts — a repeat POST leaves one row per name — and the JSON arm
    # answers the count; the plain arm 303s to the world's page.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    png_with_prompt(out / "b.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, headers, _ = post(srv, "/w/sfw/seen", {"names": "a.png"})
    assert code == 303 and headers.get("Location") == "/w/sfw/"
    code, body = post_pairs(
        srv, "/w/sfw/seen", [("names", "a.png")], accept="application/json"
    )
    assert code == 200
    assert json.loads(body) == {"ok": True, "count": 1}
    code, body = post_pairs(
        srv,
        "/w/sfw/seen",
        [("names", "a.png"), ("names", "b.png")],
        accept="application/json",
    )
    assert code == 200
    assert json.loads(body) == {"ok": True, "count": 2}
    assert code == 200
    assert json.loads(body) == {"ok": True, "count": 2}
    rows = _db(tmp_path).execute("SELECT name FROM seen ORDER BY name").fetchall()
    assert [row["name"] for row in rows] == ["a.png", "b.png"]


def test_seen_tolerates_deleted_card(tmp_path):
    # Interfaces 1: `seen` carries no foreign key — a name whose renders row
    # is gone (the PNG deleted, the rebuild dropped it) still upserts.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, body = post_pairs(
        srv, "/w/sfw/seen", [("names", "gone.png")], accept="application/json"
    )
    assert code == 200
    assert json.loads(body) == {"ok": True, "count": 1}
    row = _db(tmp_path).execute("SELECT name FROM seen").fetchone()
    assert row["name"] == "gone.png"


def test_seen_posts_no_engagement_counter(tmp_path):
    # Interfaces 4: consuming cards increments no engagement counter (and
    # neither does polling the deck) — the counts-only contract holds.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeEngage()
    fake.start()
    try:
        srv = start_engage(tmp_path, systemctl_stub(tmp_path, "inactive"), fake.url)
        get(srv, "/w/sfw/deck")
        post(srv, "/w/sfw/seen", {"names": "a.png"})
        srv.engage.flush()
        assert fake.bodies == []
    finally:
        fake.stop()


def test_new_render_appears_in_deck(tmp_path):
    # Interfaces 5: the stamp gate — a deck GET compares the output
    # directory's (name, st_mtime_ns, st_size) fingerprint and rebuilds on
    # a difference: a new PNG appears, and an in-place overwrite at an
    # unchanged entry count appears too (a count-only stamp would miss it).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    os.utime(out / "a.png", ns=(1_000_000_000, 1_000_000_000))
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    assert [card["name"] for card in _deck(srv)["cards"]] == ["a.png"]
    png_with_prompt(out / "b.png", PROMPT)
    os.utime(out / "b.png", ns=(2_000_000_000, 2_000_000_000))
    doc = _deck(srv)
    assert {card["name"] for card in doc["cards"]} == {"a.png", "b.png"}
    # Overwrite a.png in place — same entry count, different bytes.
    png_with_prompt(out / "a.png", OTHER_PROMPT)
    os.utime(out / "a.png", ns=(3_000_000_000, 3_000_000_000))
    cards = {card["name"]: card for card in _deck(srv)["cards"]}
    assert cards["a.png"]["seed"] == 77


def test_shell_shows_new_render(tmp_path):
    # Interfaces 6: the shell (the no-JS path) is stamp-refreshed too — a
    # render dropped after start appears on the page without a restart.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    png_with_prompt(out / "late.png", PROMPT)
    body = get(srv, "/w/sfw/")
    assert "late.png" in body


def test_unchanged_directory_rebuilds_once(tmp_path, monkeypatch):
    # Interfaces 5: the per-process stamp cache — an unchanged directory
    # rebuilds once (at start), never per GET.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    calls = []
    real = feed.feed_index.rebuild

    def counting(root, world):
        calls.append(world)
        return real(root, world)

    monkeypatch.setattr(feed.feed_index, "rebuild", counting)
    srv = start(
        tmp_path,
        systemctl_stub(tmp_path, "inactive"),
        worlds={"sfw": {"comfyPort": free_port()}},
    )
    get(srv, "/w/sfw/deck")
    get(srv, "/w/sfw/deck")
    assert calls == ["sfw"]


def test_deck_below_low_water_starts_run_unit(tmp_path):
    # Interfaces 3: the demand signal — a deck GET that leaves the unseen
    # count below the world's deckLowWater starts the world's comfy-run
    # oneshot (default water 5, one unseen render here).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    get(srv, "/w/sfw/deck")
    assert "--user start --no-block comfy-run-sfw.service" in log.read_text()


def test_deck_above_low_water_skips_run_unit(tmp_path):
    # ...and at or above the water line nothing starts: one unseen render
    # against deckLowWater 1 (1 < 1 is false).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(
        tmp_path,
        systemctl_stub(tmp_path, "inactive", log=log),
        worlds={"sfw": {"comfyPort": free_port(), "deckLowWater": 1}},
    )
    get(srv, "/w/sfw/deck")
    assert "--user start --no-block comfy-run-sfw.service" not in log.read_text()


def test_deck_does_not_wait_for_an_already_running_supervisor(tmp_path):
    # Measured on core 2026-09-22: comfy-run-<w>.service is Type=oneshot
    # with TimeoutStartUSec=infinity and the supervisor loops for hours, so
    # while it runs the unit sits in `activating (start)` and a plain
    # `systemctl start` BLOCKS until that run ends -- it is not the no-op
    # _start_run_unit's docstring claims. With unseen 0 of 92 renders the
    # demand signal fired on every deck GET, so every page on the phone
    # paid the whole 5 s subprocess timeout and logged one failure
    # (9 x "timed out after 5 seconds" during an 8-request probe). The
    # signal is fire-and-forget by contract: it must not wait for the job.
    #
    # The stub is systemd's own semantics: `start` waits for the job unless
    # --no-block is passed. Without the flag this test spends the stub's
    # full sleep before the deck answers.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    stub = tmp_path / "stub-systemctl-blocking-start"
    stub.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >>{log}\n"
        'if [ "$2" = "is-active" ]; then echo inactive; fi\n'
        'if [ "$2" = "start" ]; then\n'
        '  for a in "$@"; do\n'
        '    if [ "$a" = "--no-block" ]; then exit 0; fi\n'
        "  done\n"
        "  sleep 3\n"
        "fi\n"
        "exit 0\n"
    )
    stub.chmod(0o755)
    srv = start(tmp_path, str(stub))
    began = time.monotonic()
    get(srv, "/w/sfw/deck")
    waited = time.monotonic() - began
    assert waited < 1.0, f"the deck waited {waited:.1f}s on the supervisor's start"
    assert "--no-block" in log.read_text()


def test_deck_run_unit_start_failure_does_not_break_page(tmp_path):
    # Interfaces 3: a failed start is one stderr line — the deck still
    # answers 200 with its page.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    stub = tmp_path / "stub-systemctl-fail"
    stub.write_text(
        '#!/bin/sh\nif [ "$2" = "is-active" ]; then echo inactive; exit 0; fi\nexit 1\n'
    )
    stub.chmod(0o755)
    srv = start(tmp_path, str(stub))
    doc = _deck(srv)
    assert doc["world"] == "sfw"
    assert [card["name"] for card in doc["cards"]] == ["a.png"]


def test_build_server_refuses_bad_deck_water(tmp_path):
    # Interfaces 7: the knob is validated where the worlds dict enters —
    # an int >= 0, bools excluded (the module asserts the same at eval and
    # renders the file; this is the runtime refusal).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    for bad in (-1, "x", True, 1.5):
        with pytest.raises(ValueError, match="deckLowWater"):
            feed.build_server(
                str(tmp_path),
                {"sfw": {"comfyPort": 8188, "deckLowWater": bad}},
                "systemctl",
            )


def test_regenerate_and_edit_run_queue_once(tmp_path):
    # Decision 5: the interactive run_once — a successful regenerate/edit
    # enqueue is submitted to the world's ComfyUI at once, from those
    # handlers (never the deck).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    fake = FakeComfy()
    fake.start()
    try:
        port = int(fake.url.rsplit(":", 1)[1])
        srv = start(
            tmp_path,
            systemctl_stub(tmp_path, "inactive"),
            worlds={"sfw": {"comfyPort": port}},
        )
        code, body = post_json(srv, "/w/sfw/regenerate", {"name": "a.png"})
        assert code == 200 and json.loads(body)["ok"] is True
        assert fake.prompts, "the interactive run_once submitted nothing"
        job = _jobs(tmp_path, "regenerate")[0]
        assert job["state"] == "submitted"
        code, body = post_json(srv, "/w/sfw/edit", {"name": "a.png", "prompt": "x"})
        assert code == 200
        assert len(fake.prompts) == 2
        assert _jobs(tmp_path, "edit")[0]["state"] == "submitted"
    finally:
        fake.stop()


# GN24 — POST /w/<world>/activate: the GPU handover through systemd. The
# flip clock is one process-global timestamp in the server (Decision 6);
# these tests run many servers inside one pytest process, so each test
# resets the clock to the first-flip-after-boot state (0).
@pytest.fixture(autouse=True)
def _reset_flip_clock():
    feed._last_flip = 0.0
    yield


def _starts(log):
    """The `start` argvs the stub systemctl logged, in order."""
    return [line for line in log.read_text().splitlines() if " start " in line]


def test_activate_unknown_world_404_no_systemctl(tmp_path):
    # Interfaces 1: an unknown world is the 404 BEFORE any systemctl argv
    # — the name is matched against the configured list, never built from
    # the raw path (M7's guard).
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    code, body = post_json(srv, "/w/nope/activate", {})
    assert code == 404
    assert log.read_text() == ""


def test_activate_starts_world_target(tmp_path):
    # Interfaces 1+3: the handover starts only the world's target — never
    # a comfyui-* unit, never a stop (the target's wants plus the
    # generators' Conflicts= do the whole trade) — and answers the JSON
    # arm's `started: true`.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    code, body = post_json(srv, "/w/sfw/activate", {})
    assert code == 200
    assert json.loads(body) == {"ok": True, "world": "sfw", "started": True}
    assert log.read_text().splitlines() == [
        "--user is-active comfy-world-sfw.target",
        "--user start comfy-world-sfw.target",
    ]


def test_activate_already_active_is_noop(tmp_path):
    # Interfaces 1: `is-active` answers active — no start argv, the JSON
    # arm's `started: false`, the form arm a 303 to the world's page.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(
        tmp_path,
        systemctl_stub(
            tmp_path,
            "inactive",
            mapping={"comfy-world-sfw.target": "active"},
            log=log,
        ),
    )
    code, body = post_json(srv, "/w/sfw/activate", {})
    assert code == 200
    assert json.loads(body) == {"ok": True, "world": "sfw", "started": False}
    code, headers, _ = post(srv, "/w/sfw/activate", {})
    assert code == 303
    assert headers["Location"] == "/w/sfw/"
    assert _starts(log) == []


def test_activate_second_flip_within_guard_429(tmp_path):
    # Interfaces 1+2: two different worlds, both inactive, the default
    # guard — the second flip is a 429 and no start argv runs for it.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    code, _ = post_json(srv, "/w/sfw/activate", {})
    assert code == 200
    code, body = post_json(srv, "/w/nsfw/activate", {})
    assert code == 429
    doc = json.loads(body)
    assert doc["ok"] is False
    assert doc["error"] == "flip guard"
    assert isinstance(doc["retry_after"], int) and 1 <= doc["retry_after"] <= 30
    # the plain arm carries the same refusal
    code, _, body = post(srv, "/w/nsfw/activate", {})
    assert code == 429
    assert body.startswith("flip guard: ")
    assert _starts(log) == ["--user start comfy-world-sfw.target"]


def test_activate_guard_expires(tmp_path):
    # Interfaces 2: flip_guard_seconds=0 — the window never holds, so the
    # second flip starts too.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(
        tmp_path,
        systemctl_stub(tmp_path, "inactive", log=log),
        flip_guard_seconds=0,
    )
    code, body = post_json(srv, "/w/sfw/activate", {})
    assert code == 200 and json.loads(body)["started"] is True
    code, body = post_json(srv, "/w/nsfw/activate", {})
    assert code == 200 and json.loads(body)["started"] is True
    assert _starts(log) == [
        "--user start comfy-world-sfw.target",
        "--user start comfy-world-nsfw.target",
    ]


def test_activate_cross_world_guard(tmp_path):
    # Interfaces 2: the clock is global across worlds — the same pair as
    # the 429 row, reversed (nsfw flips first, sfw's immediate flip gets
    # the 429): a per-world clock would let sfw through.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    code, _ = post_json(srv, "/w/nsfw/activate", {})
    assert code == 200
    code, body = post_json(srv, "/w/sfw/activate", {})
    assert code == 429
    assert json.loads(body)["error"] == "flip guard"
    assert _starts(log) == ["--user start comfy-world-nsfw.target"]


def test_activate_systemctl_failure_503(tmp_path):
    # Interfaces 4: a failed start is a named 503, never a silent 200 —
    # and the failure is not a flip: the immediate retry tries the start
    # again instead of eating a 429.
    make_world(tmp_path)
    stub = tmp_path / "stub-systemctl-refuse"
    stub.write_text(
        "#!/bin/sh\n"
        'if [ "$2" = "is-active" ]; then echo inactive; exit 0; fi\n'
        'echo "start refused" >&2\n'
        "exit 1\n"
    )
    stub.chmod(0o755)
    srv = start(tmp_path, str(stub))
    code, body = post_json(srv, "/w/sfw/activate", {})
    assert code == 503
    assert json.loads(body) == {
        "ok": False,
        "error": "systemctl start failed for comfy-world-sfw.target",
    }
    code, body = post_json(srv, "/w/sfw/activate", {})
    assert code == 503


def test_build_server_refuses_bad_flip_guard(tmp_path):
    # Interfaces 2: the knob is validated where it enters — an int >= 0,
    # bools excluded (the module asserts the same at eval and renders
    # the file; this is the runtime refusal).
    make_world(tmp_path)
    for bad in (-1, "x", True, 1.5):
        with pytest.raises(ValueError, match="flipGuardSeconds"):
            feed.build_server(
                str(tmp_path),
                {"sfw": {"comfyPort": 8188}},
                "systemctl",
                flip_guard_seconds=bad,
            )


def test_load_worlds_reads_flip_guard(tmp_path):
    # Interfaces 5: flipGuardSeconds rides the worlds file's top level —
    # the file's value carries through to build_server, 30 when absent.
    f = _worlds_file(tmp_path, {"worlds": {"sfw": {"comfyPort": 8188}}})
    assert feed._load_worlds(f) == (
        {"sfw": {"comfyPort": 8188, "deckLowWater": 5, "tickSeconds": 120}},
        30,
    )
    f = _worlds_file(
        tmp_path, {"flipGuardSeconds": 7, "worlds": {"sfw": {"comfyPort": 8188}}}
    )
    assert feed._load_worlds(f)[1] == 7


def test_load_worlds_reads_tick_seconds(tmp_path):
    # GN45 Interfaces 5: the freshness window's tick rides the worlds
    # file per world — the file's value carries through to build_server,
    # the 120 default matching the supervisor's own --tick default.
    f = _worlds_file(
        tmp_path,
        {
            "worlds": {
                "sfw": {"comfyPort": 8188, "tickSeconds": 5},
                "nsfw": {"comfyPort": 8189},
            }
        },
    )
    assert feed._load_worlds(f)[0] == {
        "sfw": {"comfyPort": 8188, "deckLowWater": 5, "tickSeconds": 5},
        "nsfw": {"comfyPort": 8189, "deckLowWater": 5, "tickSeconds": 120},
    }


def test_build_server_refuses_bad_tick_seconds(tmp_path):
    # GN45 Interfaces 5: the knob is validated where the worlds dict
    # enters — an int >= 1, bools excluded (deckLowWater's own refusal
    # shape; the freshness window collapses at tick 0).
    make_world(tmp_path)
    for bad in (0, -3, "x", True, 1.5):
        with pytest.raises(ValueError, match="tickSeconds"):
            feed.build_server(
                str(tmp_path),
                {"sfw": {"comfyPort": 8188, "tickSeconds": bad}},
                "systemctl",
            )


# GN25 — the interface: the mounted assets, the shell's mounts and the
# deck's carried generator state.


def get_with_type(srv, path):
    """GET returning (status, Content-Type, body bytes)."""
    req = urllib.request.Request(_url(srv, path))
    try:
        with _OPENER.open(req) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read()


def test_assets_served_from_env_paths(tmp_path, monkeypatch):
    # Interfaces 1: the assets are read from FEED_APP_JS / FEED_APP_CSS at
    # REQUEST time (the wrapper exports the store paths; the in-tree run
    # sets them by hand) — the bytes and the content types, and the routes
    # are top-level: one app serves every world.
    make_world(tmp_path)
    js = tmp_path / "app.js"
    js.write_text("var deck = 1\n")
    css = tmp_path / "app.css"
    css.write_text(".card {\n  height: 100dvh;\n}\n")
    monkeypatch.setenv("FEED_APP_JS", str(js))
    monkeypatch.setenv("FEED_APP_CSS", str(css))
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    code, ctype, body = get_with_type(srv, "/assets/app.js")
    assert code == 200
    assert ctype == "text/javascript; charset=utf-8"
    assert body == js.read_bytes()
    code, ctype, body = get_with_type(srv, "/assets/app.css")
    assert code == 200
    assert ctype == "text/css; charset=utf-8"
    assert body == css.read_bytes()


def test_assets_unset_404(tmp_path, monkeypatch):
    # Interfaces 1: unset (or unreadable) → 404, never an empty 200 — an
    # asset seam that quietly serves nothing is the failure this catches.
    # The 200 arm runs first so the 404s below are the unset seam's own
    # answer, never a missing route's (a route that does not exist would
    # 404 too, and the test would be vacuous).
    make_world(tmp_path)
    js = tmp_path / "app.js"
    js.write_text("var deck = 1\n")
    css = tmp_path / "app.css"
    css.write_text(".card {\n  height: 100dvh;\n}\n")
    monkeypatch.setenv("FEED_APP_JS", str(js))
    monkeypatch.setenv("FEED_APP_CSS", str(css))
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    assert get_with_type(srv, "/assets/app.js")[0] == 200
    assert get_with_type(srv, "/assets/app.css")[0] == 200
    monkeypatch.delenv("FEED_APP_JS", raising=False)
    monkeypatch.delenv("FEED_APP_CSS", raising=False)
    for path in ("/assets/app.js", "/assets/app.css"):
        code, ctype, body = get_with_type(srv, path)
        assert code == 404, (path, code, body)
    # Set but unreadable is the same refusal.
    monkeypatch.setenv("FEED_APP_JS", str(tmp_path / "gone.js"))
    monkeypatch.setenv("FEED_APP_CSS", str(tmp_path / "gone.css"))
    code, _, _ = get_with_type(srv, "/assets/app.js")
    assert code == 404
    code, _, _ = get_with_type(srv, "/assets/app.css")
    assert code == 404


def test_shell_carries_mounts_and_world_data(tmp_path):
    # Interfaces 2: the mounts follow the main open — the stylesheet, the
    # deferred script — and the main carries data-world, data-worlds
    # (worldsOrder joined) and data-generator; every world name is escaped
    # (the page's HTML-escape discipline, data attributes included).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    worlds = {"sfw": {"comfyPort": free_port()}, "x<y": {"comfyPort": free_port()}}
    srv = start(tmp_path, systemctl_stub(tmp_path, "active"), worlds=worlds)
    body = get(srv, "/w/sfw/")
    assert '<link rel="stylesheet" href="/assets/app.css">' in body
    assert '<script src="/assets/app.js" defer></script>' in body
    assert 'data-world="sfw"' in body
    assert 'data-worlds="sfw,x&lt;y"' in body
    assert 'data-generator="active"' in body
    assert "<x>" not in body
    # The no-JS path (the negative control): the article list still renders
    # BELOW the mounts — the shell is one page for both paths, and M8's
    # discriminating row (the list dropped when JS mounts) fails here.
    assert body.index('<script src="/assets/app.js" defer></script>') < body.index(
        "<article>"
    )
    assert "a.png" in body


def test_deck_carries_generator_state(tmp_path):
    # Interfaces 2 (operator decision 2026-09-19): the deck carries the
    # world's target state — `is-active comfy-world-<w>.target`, the unit
    # the activate route starts — so the top bar's dot refreshes on the
    # deck fetch the page was making anyway; no state route exists. The
    # field rides every page, not only the first.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    png_with_prompt(out / "b.png", PROMPT)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "active", log=log))
    doc = _deck(srv, "/w/sfw/deck?n=1")
    assert doc["generator"] == "active"
    assert "--user is-active comfy-world-sfw.target" in log.read_text()
    page2 = _deck(srv, "/w/sfw/deck?n=1&cursor=" + quote(doc["cursor"]))
    assert page2["generator"] == "active"
    # Real `systemctl is-active` prints `inactive` and exits 3 — the
    # printed state wins over the exit code (the shell's `unknown` is for
    # a run that says nothing), so the dot reads inactive, never unknown.
    stub = tmp_path / "stub-systemctl-inactive3"
    stub.write_text(
        '#!/bin/sh\nif [ "$2" = "is-active" ]; then echo inactive; exit 3; fi\nexit 0\n'
    )
    stub.chmod(0o755)
    srv = start(tmp_path, str(stub))
    assert _deck(srv)["generator"] == "inactive"


# The 2026-09-19 power cut: seven zero-byte PNGs in one world's output
# directory stopped the feed server for EVERY world from binding, because
# build_server rebuilds each world's index before it opens its socket.


def test_build_server_binds_with_a_bad_png_present(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    (out / "half-written.png").write_bytes(b"")
    srv = start(tmp_path, systemctl_stub(tmp_path, "active"))
    assert get(srv, "/healthz").startswith("ok")


def test_a_bad_png_does_not_hide_the_good_ones(tmp_path):
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    (out / "half-written.png").write_bytes(b"")
    srv = start(tmp_path, systemctl_stub(tmp_path, "active"))
    doc = json.loads(get(srv, "/w/sfw/deck?n=10"))
    assert [card["name"] for card in doc["cards"]] == ["a.png"]


def test_a_bad_png_appearing_at_runtime_does_not_500_the_deck(tmp_path):
    # The stamp gate rebuilds per request, so a file written after the server
    # bound reaches the same code path -- and a raise there is a 500 on every
    # deck and shell GET, not merely a failed start.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(tmp_path, systemctl_stub(tmp_path, "active"))
    assert status(srv, "/w/sfw/deck?n=10") == 200
    (out / "half-written.png").write_bytes(b"")
    assert status(srv, "/w/sfw/deck?n=10") == 200
    assert status(srv, "/w/sfw/") == 200


# prune reached the tree first as feed_index.main's `feed-index prune`, which
# no wrapper exposes -- comfy-feed and comfy-mutate are the only binaries. The
# reachable CLI is this one.


def test_prune_subcommand_caps_and_prints_the_count(tmp_path, capsys):
    out = make_world(tmp_path)
    for i in range(5):
        png = out / f"r{i}.png"
        png_with_prompt(png, PROMPT)
        os.utime(png, (1000 + i, 1000 + i))
    rc = feed.main(["prune", "--world", "sfw", "--root", str(tmp_path), "--keep", "2"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "3"
    assert len(list(out.glob("*.png"))) == 2


def test_prune_subcommand_spares_liked_renders(tmp_path, capsys):
    out = make_world(tmp_path)
    for i in range(4):
        png = out / f"r{i}.png"
        png_with_prompt(png, PROMPT)
        os.utime(png, (1000 + i, 1000 + i))
    feed.feed_index.rebuild(str(tmp_path), "sfw")
    conn = feed.feed_index.open_db(str(tmp_path), "sfw")
    with conn:
        conn.execute("INSERT INTO likes(name, liked_at) VALUES('r0.png', 1)")
    feed.main(["prune", "--world", "sfw", "--root", str(tmp_path), "--keep", "2"])
    assert "r0.png" in [p.name for p in out.glob("*.png")]


def test_prune_subcommand_refuses_a_negative_keep(tmp_path):
    make_world(tmp_path)
    with pytest.raises(SystemExit):
        feed.main(["prune", "--world", "sfw", "--root", str(tmp_path), "--keep", "-1"])


# GN44 — POST /w/<world>/generation: drop the authoring loop without
# dropping the world, and the generation state the deck carries.


def post_gen_raw(srv, path, body):
    """POST `body` (raw text) with the JSON arm's headers — the
    generation route's request shape: a JSON body, the Accept that
    selects the JSON answer."""
    req = urllib.request.Request(
        _url(srv, path),
        data=body.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with _OPENER.open(req) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def post_gen(srv, path, payload):
    return post_gen_raw(srv, path, json.dumps(payload))


def test_generation_stop_stops_run_unit(tmp_path):
    # Interfaces 1: {"on": false} runs `systemctl --user stop
    # comfy-run-<w>.service` and answers the JSON arm with the state.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    code, body = post_gen(srv, "/w/sfw/generation", {"on": False})
    assert code == 200
    assert json.loads(body) == {"ok": True, "world": "sfw", "generation": "off"}
    assert "--user stop comfy-run-sfw.service" in log.read_text().splitlines()


def test_generation_start_starts_run_unit(tmp_path):
    # Interfaces 1: {"on": true} starts the same unit back.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    code, body = post_gen(srv, "/w/sfw/generation", {"on": True})
    assert code == 200
    assert json.loads(body) == {"ok": True, "world": "sfw", "generation": "on"}
    assert "--user start comfy-run-sfw.service" in log.read_text().splitlines()


def test_generation_unknown_world_404_no_systemctl(tmp_path):
    # Interfaces 1: an unknown world is the 404 BEFORE any systemctl
    # argv — the name is matched against the configured list, never
    # built from the raw path.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    code, body = post_gen(srv, "/w/nope/generation", {"on": False})
    assert code == 404
    assert json.loads(body) == {"ok": False, "error": "not found"}
    assert log.read_text() == ""


def test_generation_spares_generator_feed_and_model(tmp_path):
    # Interfaces 2+5: both directions of the switch name ONLY the
    # supervisor — never `comfyui-<w>.service`, never `comfy-feed`,
    # never the shared `comfy-author-model.service` — so dropping
    # generation leaves the generator serving and the feed readable.
    # The exact log is the strongest form: anything else the route
    # touched would appear here.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    post_gen(srv, "/w/sfw/generation", {"on": False})
    post_gen(srv, "/w/sfw/generation", {"on": True})
    assert log.read_text().splitlines() == [
        "--user stop comfy-run-sfw.service",
        "--user start comfy-run-sfw.service",
    ]


def test_generation_bad_body_400(tmp_path):
    # Interfaces 1: the body must be a JSON object carrying an "on"
    # boolean — anything else is a 400 before any subprocess runs.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    for bad in ("not json", '{"on": "yes"}', '{"other": true}', "{}", ""):
        code, _ = post_gen_raw(srv, "/w/sfw/generation", bad)
        assert code == 400, bad
    assert log.read_text() == ""


def test_generation_form_arm_303(tmp_path):
    # The no-Accept arm answers like every other verb: the action runs,
    # the answer is a 303 to the world's page.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    req = urllib.request.Request(
        _url(srv, "/w/sfw/generation"),
        data=b'{"on": false}',
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with _OPENER.open(req) as resp:
            code, headers = resp.status, dict(resp.headers)
    except urllib.error.HTTPError as exc:
        code, headers = exc.code, dict(exc.headers)
    assert code == 303
    assert headers["Location"] == "/w/sfw/"
    assert "--user stop comfy-run-sfw.service" in log.read_text().splitlines()


def test_generation_systemctl_failure_503(tmp_path):
    # A failed action is a named 503, never a silent 200.
    make_world(tmp_path)
    stub = tmp_path / "stub-systemctl-refuse"
    stub.write_text(
        "#!/bin/sh\n"
        'if [ "$2" = "is-active" ]; then echo inactive; exit 0; fi\n'
        'echo "stop refused" >&2\n'
        "exit 1\n"
    )
    stub.chmod(0o755)
    srv = start(tmp_path, str(stub))
    code, body = post_gen(srv, "/w/sfw/generation", {"on": False})
    assert code == 503
    assert json.loads(body) == {
        "ok": False,
        "error": "systemctl stop failed for comfy-run-sfw.service",
    }


# GN58 — the switch that stays off: `{"on": false}` leaves a marker in
# the world folder (`<root>/worlds/<w>/generation-off`, an empty file
# beside feed.sqlite), the deck's demand signal is suppressed while the
# marker exists, and only an explicit `{"on": true}` clears it. The
# systemctl log is cleared between steps so each assertion sees exactly
# its own deck GET's argv.


def test_deck_skips_demand_signal_when_generation_is_off(tmp_path):
    # The load-bearing case: below the water line the deck's GET normally
    # starts comfy-run-<w> (test_deck_below_low_water_starts_run_unit) —
    # once the operator switched generation off, the same GET must not.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    post_gen(srv, "/w/sfw/generation", {"on": False})
    log.write_text("")
    get(srv, "/w/sfw/deck")
    assert "--user start --no-block comfy-run-sfw.service" not in log.read_text()


def test_generation_on_clears_the_off_marker(tmp_path):
    # "off" is not permanent: only an explicit {"on": true} clears the
    # marker, and the deck's demand signal is back on the next GET.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    post_gen(srv, "/w/sfw/generation", {"on": False})
    post_gen(srv, "/w/sfw/generation", {"on": True})
    log.write_text("")
    get(srv, "/w/sfw/deck")
    assert "--user start --no-block comfy-run-sfw.service" in log.read_text()


def test_generation_off_survives_a_feed_restart(tmp_path):
    # The flag lives on disk, not in the process: off on one server, a
    # second server over the same root, one deck GET below the water line
    # → still suppressed.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    post_gen(srv, "/w/sfw/generation", {"on": False})
    log.write_text("")
    srv2 = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    get(srv2, "/w/sfw/deck")
    assert "--user start --no-block comfy-run-sfw.service" not in log.read_text()


def test_generation_marker_failure_503_no_systemctl(tmp_path):
    # The marker is written before the stop is attempted: a write that
    # cannot happen (the world folder is read-only) is a named 503
    # BEFORE any systemctl argv — the unit is not stopped behind the
    # operator's back while the switch failed to record the decision.
    make_world(tmp_path)
    log = tmp_path / "systemctl.log"
    log.write_text("")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive", log=log))
    world_dir = tmp_path / "worlds" / "sfw"
    world_dir.chmod(0o555)
    try:
        code, body = post_gen(srv, "/w/sfw/generation", {"on": False})
        assert code == 503
        assert json.loads(body) == {
            "ok": False,
            "error": "generation-off marker failed for sfw",
        }
        assert log.read_text() == ""
    finally:
        world_dir.chmod(0o755)


def test_deck_carries_generation_state(tmp_path):
    # Interfaces 3: every deck page carries the supervisor's on/off —
    # `active` or `activating` is on, anything else is off.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    png_with_prompt(out / "b.png", PROMPT)
    srv = start(
        tmp_path,
        systemctl_stub(
            tmp_path,
            "inactive",
            mapping={"comfy-run-sfw.service": "active"},
        ),
    )
    doc = _deck(srv, "/w/sfw/deck?n=1")
    assert doc["generation"] == "on"
    page2 = _deck(srv, "/w/sfw/deck?n=1&cursor=" + quote(doc["cursor"]))
    assert page2["generation"] == "on"
    srv = start(
        tmp_path,
        systemctl_stub(
            tmp_path,
            "inactive",
            mapping={"comfy-run-sfw.service": "activating"},
        ),
    )
    assert _deck(srv)["generation"] == "on"
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    assert _deck(srv)["generation"] == "off"


def test_generation_state_read_fresh_per_request(tmp_path):
    # Interfaces 3: the state is never held between requests — a stub
    # whose answer changes between two deck GETs is reflected at once.
    out = make_world(tmp_path)
    for name in "abcdef":
        png_with_prompt(out / (name + ".png"), PROMPT)
    answer = tmp_path / "gen-answer"
    answer.write_text("inactive\n")
    stub = tmp_path / "stub-systemctl-flip"
    stub.write_text(
        "#!/bin/sh\n"
        'if [ "$2" = "is-active" ]; then cat ' + str(answer) + "; exit 0; fi\n"
        "exit 0\n"
    )
    stub.chmod(0o755)
    srv = start(tmp_path, str(stub))
    assert _deck(srv)["generation"] == "off"
    answer.write_text("active\n")
    assert _deck(srv)["generation"] == "on"


def test_shell_carries_data_generation(tmp_path):
    # Interfaces 3+6: the shell's mount carries the supervisor's on/off
    # so the chrome's status word paints before the first deck fetch.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    srv = start(
        tmp_path,
        systemctl_stub(
            tmp_path,
            "inactive",
            mapping={"comfy-run-sfw.service": "active"},
        ),
    )
    assert 'data-generation="on"' in get(srv, "/w/sfw/")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    assert 'data-generation="off"' in get(srv, "/w/sfw/")


# GN45 — the supervisor's phase: the deck's world payload (and the
# shell's mount) carry the status word, but only while the unit is live
# and the cell is fresh — a file from a dead or wedged supervisor is a
# liar, and the reader never repeats one.


def _write_run_status(root, world, phase, ts=None, queued=0, batch=1):
    """A status cell exactly as run.py's writer leaves it (a fresh stamp
    unless `ts` overrides)."""
    doc = {
        "phase": phase,
        "queued": queued,
        "batch": batch,
        "ts": ts or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (pathlib.Path(root) / "worlds" / world / "run-status.json").write_text(
        json.dumps(doc)
    )


def _run_active_stub(tmp_path, state="active"):
    """The stub whose supervisor unit answers `state` on is-active."""
    return systemctl_stub(
        tmp_path, "inactive", mapping={"comfy-run-sfw.service": state}
    )


def test_phase_held_back_when_unit_not_active(tmp_path):
    # Interfaces 4 (M1's guard): the unit's liveness is the authority,
    # not the file — a cell left by a killed supervisor reads as no phase
    # at all beside the payload's `off`, however fresh it is.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    _write_run_status(tmp_path, "sfw", "authoring")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    doc = _deck(srv)
    assert doc["generation"] == "off"
    assert doc["phase"] is None


def test_phase_rides_the_deck_when_unit_active(tmp_path):
    # Interfaces 4: active (or activating) plus a fresh cell carries the
    # recorded phase in the same world payload GN44 extended.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    _write_run_status(tmp_path, "sfw", "mutating")
    srv = start(tmp_path, _run_active_stub(tmp_path))
    doc = _deck(srv)
    assert doc["generation"] == "on"
    assert doc["phase"] == "mutating"
    srv = start(tmp_path, _run_active_stub(tmp_path, "activating"))
    assert _deck(srv)["phase"] == "mutating"


def test_phase_stale_past_four_ticks(tmp_path):
    # Interfaces 5 (M2's guard): while the unit is live, a stamp older
    # than 4 x the world's tick (the 120 default here) reads `stale`,
    # never the recorded phase — the writer may be wedged mid-phase.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 4 * 120 - 1))
    _write_run_status(tmp_path, "sfw", "rendering", ts=old)
    srv = start(tmp_path, _run_active_stub(tmp_path))
    assert _deck(srv)["phase"] == "stale"


def test_phase_freshness_reads_the_worlds_tick(tmp_path):
    # Interfaces 5: the window is 4 x the world's OWN tick, read from the
    # same worlds config the feed already has — 30s is fresh at the 120
    # default and stale at tick 5.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 30))
    _write_run_status(tmp_path, "sfw", "waiting", ts=ts)
    worlds = {
        "sfw": {"comfyPort": free_port(), "tickSeconds": 5},
        "nsfw": {"comfyPort": free_port()},
    }
    srv = start(tmp_path, _run_active_stub(tmp_path), worlds=worlds)
    assert _deck(srv)["phase"] == "stale"


def test_phase_outside_the_enum_is_absent(tmp_path):
    # Interfaces 2: a value the writer never writes is treated as absent,
    # never displayed raw.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    _write_run_status(tmp_path, "sfw", "banana")
    srv = start(tmp_path, _run_active_stub(tmp_path))
    assert _deck(srv)["phase"] is None


def test_phase_absent_when_the_cell_is_torn(tmp_path):
    # Interfaces 1+2: a partial or unparseable cell reads as absent (the
    # writer's atomic replace makes this a should-never, not a never).
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    (tmp_path / "worlds" / "sfw" / "run-status.json").write_text('{"phase": "auth')
    srv = start(tmp_path, _run_active_stub(tmp_path))
    assert _deck(srv)["phase"] is None


def test_shell_carries_data_phase(tmp_path):
    # Interfaces 4+6: the shell mounts the phase beside data-generation
    # so the chrome's word paints before the first deck fetch — and
    # mounts the empty word when the unit is not live.
    out = make_world(tmp_path)
    png_with_prompt(out / "a.png", PROMPT)
    _write_run_status(tmp_path, "sfw", "authoring")
    srv = start(tmp_path, _run_active_stub(tmp_path))
    assert 'data-phase="authoring"' in get(srv, "/w/sfw/")
    srv = start(tmp_path, systemctl_stub(tmp_path, "inactive"))
    assert 'data-phase=""' in get(srv, "/w/sfw/")
