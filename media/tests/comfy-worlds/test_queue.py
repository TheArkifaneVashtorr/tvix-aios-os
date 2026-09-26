"""Unit tests for pkgs/comfy-worlds/queue.py.

Loaded by path (like tests/comfy-worlds/test_feed_index.py) so this test file
works both under `pytest tests/comfy-worlds` from the repo root and inside
checks.comfy-worlds-unit, which copies pkgs/comfy-worlds and tests/comfy-worlds
into a fresh tree without installing anything.

The check copies only pkgs/comfy-worlds, pkgs/media-fetch and
tests/comfy-worlds — not tests/mocks — so the fake ComfyUI (which GN3's VM
test and GN4 reuse) lives in tests/mocks/comfy-api-fake.py and is mirrored
verbatim here (see MIRROR and test_fake_mirror_is_current). The functional
tests use the mirror, so they run identically from the repo root and inside
the check; test_fake_mirror_is_current is the one permitted skip, taken only
inside the check where tests/mocks/ is absent.
"""

import http.server
import importlib.util
import json
import pathlib
import socket
import sqlite3
import sys
import time
import uuid

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "comfy-worlds" / "queue.py"

# mirror of tests/mocks/comfy-api-fake.py
MIRROR = '''"""A stdlib HTTP fake of ComfyUI's API for the comfy-worlds queue tests.

Runs the smallest surface `pkgs/comfy-worlds/queue.py` drives:

- `POST /prompt` — records the body and answers `{"prompt_id": "<id>"}`.
- `GET /history/<id>` — `{}` (absent) until `tick()` or `fail()` records a
  result for that id.
- `GET /system_stats` — a fixed JSON answer so a client can health-check.

`FakeComfy(port=0)` binds an ephemeral loopback port, is `.start()`-ed in a
thread, and answers on `.url`. `tick(filename)` makes every submitted prompt
id report one done image with that filename; `fail(prompt_id, msg)` makes one
id report `status.status_str == "error"`. `.prompts` holds the parsed
`POST /prompt` bodies in arrival order, for asserting the seed the queue
pinned. Importable (the queue tests start it in a thread) and runnable
(`python tests/mocks/comfy-api-fake.py --port 8188`).
"""

import argparse
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeComfy:
    """An in-process ComfyUI API fake on `127.0.0.1:<port>`."""

    def __init__(self, port=0):
        self._tick_filename = None
        self._failures = {}
        self.prompts = []
        handler = _make_handler(self)
        self._server = ThreadingHTTPServer(("127.0.0.1", port), handler)
        self._thread = None

    def start(self):
        """Serve in a daemon thread; `.url` is valid immediately after."""
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self):
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def tick(self, filename):
        """Report every submitted prompt id as done with this filename."""
        self._tick_filename = filename

    def fail(self, prompt_id, msg):
        """Report one prompt id as `status_str == "error"` with `msg`."""
        self._failures[prompt_id] = msg

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()

    def _history(self, pid):
        if pid in self._failures:
            return {
                pid: {
                    "status": {
                        "status_str": "error",
                        "messages": [[self._failures[pid]]],
                    }
                }
            }
        if self._tick_filename is not None:
            return {
                pid: {
                    "outputs": {
                        "9": {
                            "images": [
                                {
                                    "filename": self._tick_filename,
                                    "subfolder": "",
                                    "type": "output",
                                }
                            ]
                        }
                    },
                    "status": {"status_str": "success"},
                }
            }
        return {}


def _make_handler(fake):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence stderr access-log spam
            pass

        def _json(self, code, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            fake.prompts.append(json.loads(body))
            self._json(200, {"prompt_id": str(uuid.uuid4())})

        def do_GET(self):
            if self.path == "/system_stats":
                self._json(200, {"system": {"comfyui_version": "fake"}})
                return
            prefix = "/history/"
            if self.path.startswith(prefix):
                self._json(200, fake._history(self.path[len(prefix) :]))
                return
            self._json(404, {"error": "not found"})

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(prog="comfy-api-fake")
    parser.add_argument("--port", type=int, default=8188)
    args = parser.parse_args(argv)
    fake = FakeComfy(args.port)
    fake.start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        fake.stop()


if __name__ == "__main__":
    main()
'''

_fake_ns = {"__name__": "comfy_api_fake_mirror"}
exec(compile(MIRROR, "<comfy-api-fake-mirror>", "exec"), _fake_ns)
FakeComfy = _fake_ns["FakeComfy"]


def _make_restartable_handler(fake):
    """The mirror's handler plus `GET /queue` and prompt-id bookkeeping:
    a POSTed prompt is one this process holds until `.restart()` forgets
    it -- exactly the in-process state a ComfyUI restart wipes."""
    base = _fake_ns["_make_handler"](fake)

    class Handler(base):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            fake.prompts.append(json.loads(self.rfile.read(length)))
            prompt_id = str(uuid.uuid4())
            fake._prompt_ids.append(prompt_id)
            self._json(200, {"prompt_id": prompt_id})

        def do_GET(self):
            if self.path == "/queue":
                self._json(200, fake._queue_answer())
                return
            base.do_GET(self)

    return Handler


class _RestartableFake(FakeComfy):
    """The shared fake plus what a ComfyUI restart loses.

    `GET /queue` answers the prompt ids this process still holds (index 1
    of each entry, the shape ComfyUI's own /queue handler writes), and
    `.restart()` forgets every one of them -- so a job submitted before
    the restart is in neither `/history` nor `/queue` after it, the one
    signal that separates "lost" from "slow" (all three collections are
    in-process memory that resets on process start).
    """

    def __init__(self, port=0):
        self._tick_filename = None
        self._failures = {}
        self._prompt_ids = []
        self.prompts = []
        self._server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", port), _make_restartable_handler(self)
        )
        self._thread = None

    def restart(self):
        """Forget every prompt id this process knew: its whole queue and
        history, which is what a ComfyUI restart does to them."""
        self._prompt_ids.clear()
        self._failures.clear()
        self._tick_filename = None

    def _queue_answer(self):
        return {
            "queue_running": [[str(i), pid] for i, pid in enumerate(self._prompt_ids)],
            "queue_pending": [],
        }


# The prompt and workflow chunks ComfyUI writes. The prompt carries the
# class_type graph — the source of truth for what produced an image. This is
# tests/acceptance/workflows/sdxl.json's base-plus-refiner shape trimmed to
# nodes 3, 6, 7 plus a second KSampler node "10": node 3 (the base sampler,
# numerically lowest id) has inputs.seed = 42, node 10 (the refiner) has 99.
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


def _insert_job(conn, state, prompt_id=None, output=None):
    """A jobs row in `state`, written directly -- the shape the pre-change
    code left behind, never known to any fake (the live backlog)."""
    job_id = str(uuid.uuid4())
    now = time.time()
    with conn:
        conn.execute(
            "INSERT INTO jobs(id, kind, source, prompt, seed, state,"
            " prompt_id, output, created, updated)"
            " VALUES(?, 'regenerate', 'test', ?, 1, ?, ?, ?, ?, ?)",
            (job_id, PROMPT, state, prompt_id, output, now, now),
        )
    return job_id


@pytest.fixture(scope="module")
def queue():
    spec = importlib.util.spec_from_file_location("queue", SRC)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_fake_mirror_is_current():
    mock_path = HERE.parents[1] / "mocks" / "comfy-api-fake.py"
    if not mock_path.exists():
        pytest.skip("tests/mocks/ not present inside comfy-worlds-unit")
    assert mock_path.read_text() == MIRROR


def test_enqueue_pins_the_seed_in_every_sampler(queue, tmp_path):
    fake = FakeComfy()
    fake.start()
    try:
        conn = queue.open_db(str(tmp_path), "sfw")
        job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1234)
        assert queue.submit(conn, job_id, fake.url) is True
        body = fake.prompts[-1]
        assert body["client_id"] == job_id
        assert body["prompt"]["3"]["inputs"]["seed"] == 1234
        assert body["prompt"]["10"]["inputs"]["seed"] == 1234
    finally:
        fake.stop()


def test_enqueue_refuses_non_int_seed(queue, tmp_path):
    conn = queue.open_db(str(tmp_path), "sfw")
    with pytest.raises(TypeError):
        queue.enqueue(conn, "regenerate", "test", PROMPT, seed="42")


def test_enqueue_refuses_workflow_without_sampler(queue, tmp_path):
    conn = queue.open_db(str(tmp_path), "sfw")
    no_sampler = json.dumps(
        {"3": {"class_type": "CLIPTextEncode", "inputs": {"text": "x"}}}
    )
    with pytest.raises(ValueError, match="no KSampler node in workflow"):
        queue.enqueue(conn, "regenerate", "test", no_sampler, seed=1)


def test_enqueue_refuses_unknown_kind(queue, tmp_path):
    conn = queue.open_db(str(tmp_path), "sfw")
    with pytest.raises(sqlite3.IntegrityError):
        queue.enqueue(conn, "bogus", "test", PROMPT, seed=1)


def test_state_check_refuses_unknown_state(queue, tmp_path):
    conn = queue.open_db(str(tmp_path), "sfw")
    job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE jobs SET state = 'bogus' WHERE id = ?", (job_id,))


def test_submit_refuses_non_loopback(queue, tmp_path):
    conn = queue.open_db(str(tmp_path), "sfw")
    job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
    with pytest.raises(ValueError, match="loopback-only"):
        queue.submit(conn, job_id, "http://example.com:8188")


def test_submit_then_poll_records_output(queue, tmp_path):
    fake = FakeComfy()
    fake.start()
    try:
        conn = queue.open_db(str(tmp_path), "sfw")
        job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
        assert queue.submit(conn, job_id, fake.url) is True
        fake.tick("out.png")
        assert queue.poll(conn, fake.url) == 1
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        assert row["state"] == "done"
        assert row["output"] == "out.png"
    finally:
        fake.stop()


def test_poll_records_failure(queue, tmp_path):
    fake = FakeComfy()
    fake.start()
    try:
        conn = queue.open_db(str(tmp_path), "sfw")
        job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
        queue.submit(conn, job_id, fake.url)
        prompt_id = conn.execute(
            "SELECT prompt_id FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()["prompt_id"]
        fake.fail(prompt_id, "boom")
        assert queue.poll(conn, fake.url) == 1
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        assert row["state"] == "failed"
        assert row["error"] == "boom"
    finally:
        fake.stop()


def test_run_once_submits_queued_then_polls(queue, tmp_path):
    fake = FakeComfy()
    fake.start()
    try:
        fake.tick("done.png")
        conn = queue.open_db(str(tmp_path), "sfw")
        job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
        result = queue.run_once(conn, fake.url)
        assert result == {"submitted": 1, "unreachable": 0, "changed": 1}
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        assert row["state"] == "done"
    finally:
        fake.stop()


def test_submit_unreachable_leaves_job_queued(queue, tmp_path):
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    dead_port = probe.getsockname()[1]
    probe.close()
    conn = queue.open_db(str(tmp_path), "sfw")
    queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
    queue.enqueue(conn, "mutate", "test", PROMPT, seed=2)
    result = queue.run_once(conn, f"http://127.0.0.1:{dead_port}")
    assert result == {"submitted": 0, "unreachable": 2, "changed": 0}
    rows = conn.execute("SELECT * FROM jobs ORDER BY created").fetchall()
    assert [r["state"] for r in rows] == ["queued", "queued"]
    assert all(r["error"] for r in rows)


def test_module_import_of_feed_index_honors_feed_index_py_env(tmp_path, monkeypatch):
    # queue.py's own feed_index import is sibling-relative, so loading it from a
    # directory that does NOT contain feed_index.py raises FileNotFoundError.
    # The packaged wrapper ships queue.py and feed_index.py as two single-file
    # store paths whose parent is /nix/store, so the sibling fallback can never
    # resolve there; the import must honor FEED_INDEX_PY the way feed.py does
    # (feed.py:35-36).
    scratch = tmp_path / "standalone"
    scratch.mkdir()
    (scratch / "queue.py").write_bytes(SRC.read_bytes())
    monkeypatch.setenv("FEED_INDEX_PY", str(SRC.parent / "feed_index.py"))
    spec = importlib.util.spec_from_file_location(
        "queue_standalone", scratch / "queue.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.open_db)


def test_poll_leaves_a_still_running_job_alone(queue, tmp_path):
    # The slow half of the lost-vs-slow signal: the job is absent from
    # /history (it has not finished) but present in /queue, so poll must
    # leave the row exactly as it is.
    fake = _RestartableFake()
    fake.start()
    try:
        conn = queue.open_db(str(tmp_path), "sfw")
        queue.settle_stale_submitted(conn, "test: plant the marker")
        job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
        assert queue.submit(conn, job_id, fake.url) is True
        assert queue.poll(conn, fake.url) == 0
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        assert row["state"] == "submitted"
        assert row["prompt_id"] is not None
        assert row["error"] is None
    finally:
        fake.stop()


def test_poll_requeues_a_job_orphaned_by_a_restart(queue, tmp_path):
    # The lost half: after a restart the id is in neither /history nor
    # /queue, and the job comes back as queued for the next run_once.
    fake = _RestartableFake()
    fake.start()
    try:
        conn = queue.open_db(str(tmp_path), "sfw")
        queue.settle_stale_submitted(conn, "test: plant the marker")
        job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
        assert queue.submit(conn, job_id, fake.url) is True
        fake.restart()
        assert queue.poll(conn, fake.url) == 1
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        assert row["state"] == "queued"
        assert row["prompt_id"] is None
        assert "restart" in row["error"]
        assert [job["id"] for job in queue.pending(conn)] == [job_id]
    finally:
        fake.stop()


def test_poll_ignores_an_unreachable_queue_endpoint(queue, tmp_path):
    # An unreadable /queue means "unknown", never "lost": requeueing on a
    # 404 could resubmit a job the generator may still be rendering.
    fake = FakeComfy()  # the shared fake 404s every /queue request
    fake.start()
    try:
        conn = queue.open_db(str(tmp_path), "sfw")
        queue.settle_stale_submitted(conn, "test: plant the marker")
        job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
        assert queue.submit(conn, job_id, fake.url) is True
        assert queue.poll(conn, fake.url) == 0
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        assert row["state"] == "submitted"
        assert row["prompt_id"] is not None
    finally:
        fake.stop()


def test_first_poll_settles_the_backlog_instead_of_requeuing_it(queue, tmp_path):
    # The live nsfw world's shape: a jobs table created before this
    # change, hence no settlement marker (open_db plants one only in a
    # database whose jobs table it creates itself), holding the backlog
    # the old poll left `submitted` plus rows that were never submitted.
    # The first poll must settle the backlog to failed -- never requeue
    # it, which would render 10,838 unasked-for images -- and must not
    # touch the rows that already finished.
    fake = _RestartableFake()
    fake.start()
    try:
        conn = queue.open_db(str(tmp_path), "nsfw")
        conn.execute("PRAGMA user_version = 0")  # strip the fresh marker
        stuck = [
            _insert_job(conn, "submitted", prompt_id=f"lost-{i}") for i in range(3)
        ]
        kept = _insert_job(conn, "done", output="kept.png")
        assert queue.poll(conn, fake.url) == 0
        rows = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM jobs")}
        for job_id in stuck:
            assert rows[job_id]["state"] == "failed"
            assert "backlog" in rows[job_id]["error"]
        assert rows[kept]["state"] == "done"
        assert rows[kept]["output"] == "kept.png"
        assert rows[kept]["error"] is None
        assert not any(r["state"] == "queued" for r in rows.values())
        # the marker the settlement wrote: a second poll changes nothing
        assert queue.poll(conn, fake.url) == 0
        after = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM jobs")}
        assert after == rows
    finally:
        fake.stop()


def test_orphans_after_the_settlement_are_requeued(queue, tmp_path):
    # The marker is what keeps the two dispositions apart: after the
    # one-time settlement, a genuine new orphan is requeued, not failed.
    fake = _RestartableFake()
    fake.start()
    try:
        conn = queue.open_db(str(tmp_path), "nsfw")
        conn.execute("PRAGMA user_version = 0")  # the pre-change database
        _insert_job(conn, "submitted", prompt_id="lost-backlog")
        queue.poll(conn, fake.url)  # settles the backlog, writes the marker
        job_id = queue.enqueue(conn, "regenerate", "test", PROMPT, seed=1)
        assert queue.submit(conn, job_id, fake.url) is True
        fake.restart()
        assert queue.poll(conn, fake.url) == 1
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        assert row["state"] == "queued"
        assert row["prompt_id"] is None
        assert "restart" in row["error"]
    finally:
        fake.stop()
