r"""The per-world job queue: submit, poll and record workflows on ComfyUI.

Sub-project 2 of the comfy-worlds design scopes "a job queue on ComfyUI's
API"; nothing implemented it until this module (`grep -rn '/prompt\|/history'
pkgs/` had 0 hits). Every render job is a `jobs` row in the world's
`feed.sqlite` (alongside `feed_index`'s `renders`/`likes`). A job carries the
workflow (GN1's class_type-graph prompt text) with an explicit seed pinned
into every `KSampler` node, and moves `queued → submitted → done`/`failed` as
ComfyUI answers on loopback.

The generator answers only on `127.0.0.1:<comfyPort>`, so `submit` refuses any
other base URL; an unreachable ComfyUI (the normal case when the generator is
stopped — `media-comfy stop`) leaves jobs `queued` for the next `run_once`,
while a 4xx answer is the job's fault and fails it. Stdlib only
(`urllib.request`, `json`, `sqlite3`, `time`, `uuid`); `feed_index` is
imported by path — `FEED_INDEX_PY` when set (the packaged wrapper), else the
sibling — for `open_db`.

ComfyUI's history and both its queues are in-process memory that resets on
process start, and the generator restarts on every authoring tick by design
(`Conflicts=` in the local-model module). So a `submitted` job whose
`prompt_id` is in neither `/history` nor `/queue` can only have been lost to
a restart — never merely slow, because `POST /prompt` puts the job on the
queue before returning the id — and `poll` requeues it for the next
`run_once`. The pre-fix backlog of such rows (10,838 in the live nsfw world)
settles to `failed` exactly once per database, never resubmitted: an
unreadable `/queue` means "unknown", never "lost".
"""

import importlib.util
import json
import os
import pathlib
import time
import urllib.error
import urllib.request
import uuid

_HERE = pathlib.Path(__file__).resolve().parent
# feed_index.py is a sibling in the source tree but a separate store path once
# packaged: the wrapper sets FEED_INDEX_PY to that path (the same seam feed.py
# reads, feed.py:35-36), and the sibling is the fallback for the in-tree unit
# tests.
_index_path = os.environ.get("FEED_INDEX_PY") or str(_HERE / "feed_index.py")
_SPEC = importlib.util.spec_from_file_location("feed_index", _index_path)
_feed_index = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_feed_index)

_JOBS_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY,
  kind TEXT CHECK(kind IN ('regenerate','edit','mutate')),
  source TEXT,
  prompt TEXT,
  seed INTEGER NOT NULL,
  state TEXT CHECK(state IN ('queued','submitted','done','failed')),
  prompt_id TEXT,
  output TEXT,
  error TEXT,
  created REAL,
  updated REAL
);
"""

# The once-marker for the backlog settlement: `PRAGMA user_version` is a
# free 4-byte header field SQLite itself never interprets, and feed_index
# (the other writer of feed.sqlite) keeps no schema-version migrations —
# no PRAGMA anywhere in it — so this module owns the whole field.
_SETTLED_USER_VERSION = 1

_BACKLOG_REASON = (
    "backlog: submitted before the restart-requeue change; a ComfyUI restart"
    " lost this render, and the pre-fix backlog is settled, not resubmitted"
)


def open_db(root, world):
    """A connection on `<root>/worlds/<world>/feed.sqlite` with the `jobs`
    table ensured alongside `feed_index`'s `renders`/`likes`."""
    conn = _feed_index.open_db(root, world)
    ensure_schema(conn)
    return conn


def ensure_schema(conn):
    """Create the `jobs` table when absent, and plant the settlement
    marker in a database whose `jobs` table this very call created.

    A brand-new database cannot carry the pre-fix backlog, so it must
    never settle (and so never fail) a job it submitted itself; only a
    database whose table predates the restart-requeue change — the live
    nsfw world's exact shape: table present, marker absent — settles, on
    its first `poll()`.
    """
    table_existed = (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
        ).fetchone()
        is not None
    )
    conn.execute(_JOBS_SCHEMA)
    if not table_existed:
        conn.execute(f"PRAGMA user_version = {_SETTLED_USER_VERSION}")
    conn.commit()


def enqueue(conn, kind, source, workflow, seed):
    """Create a `queued` job whose workflow carries `seed` in every KSampler.

    `workflow` is GN1's prompt text (the class_type graph as JSON); every
    `KSampler`-class node's `inputs.seed` is overwritten with `seed` (an
    explicit integer, never `"random"`). Returns the job id. A non-int `seed`
    raises `TypeError`; a workflow with no `KSampler` node raises `ValueError`
    before any row is written; a `kind` outside the enum raises
    `sqlite3.IntegrityError` from the CHECK.
    """
    if not isinstance(seed, int):
        raise TypeError(f"seed must be an int, got {type(seed).__name__}")
    graph = json.loads(workflow)
    samplers = 0
    for node in graph.values():
        if isinstance(node, dict) and node.get("class_type") == "KSampler":
            node.setdefault("inputs", {})["seed"] = seed
            samplers += 1
    if samplers == 0:
        raise ValueError("no KSampler node in workflow")
    job_id = str(uuid.uuid4())
    now = time.time()
    with conn:
        conn.execute(
            "INSERT INTO jobs(id, kind, source, prompt, seed, state, created, updated)"
            " VALUES(?, ?, ?, ?, ?, 'queued', ?, ?)",
            (job_id, kind, source, json.dumps(graph), seed, now, now),
        )
    return job_id


def submit(conn, job_id, base_url):
    """POST the job's workflow to `<base_url>/prompt` and record its id.

    Returns `True` when ComfyUI accepted the prompt (state `submitted`,
    `prompt_id` recorded); `False` when it is unreachable (state stays
    `queued`, `error` set) or answered 4xx (state `failed`). `base_url` must
    start with `http://127.0.0.1:` — the generator is loopback-only.
    """
    if not base_url.startswith("http://127.0.0.1:"):
        raise ValueError("queue: ComfyUI is loopback-only")
    row = conn.execute("SELECT prompt FROM jobs WHERE id = ?", (job_id,)).fetchone()
    body = json.dumps(
        {"prompt": json.loads(row["prompt"]), "client_id": job_id}
    ).encode("utf-8")
    request = urllib.request.Request(
        base_url + "/prompt",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        if exc.code >= 500:
            _mark_error(conn, job_id, f"HTTP {exc.code}")
            return False
        _mark_failed(conn, job_id, exc.read().decode("utf-8", "replace"))
        return False
    except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
        _mark_error(conn, job_id, str(exc))
        return False
    with conn:
        conn.execute(
            "UPDATE jobs SET prompt_id = ?, state = 'submitted', error = NULL,"
            " updated = ? WHERE id = ?",
            (payload.get("prompt_id"), time.time(), job_id),
        )
    return True


def poll(conn, base_url):
    """Check every `submitted` job against `/history/<prompt_id>`, and
    against `/queue` when the history has no entry for it.

    An entry whose `outputs.*.images[0].filename` is set moves the job to
    `done` with that filename; `status.status_str == "error"` moves it to
    `failed`. An absent entry is one of three things: the id is still in
    ComfyUI's `/queue` (rendering — left alone), `/queue` was unreadable
    (unknown — left alone, never requeued on a guess), or the id is in
    neither place, which only a ComfyUI restart can cause — its history
    and queues are in-process memory — and the job is requeued
    (`state='queued'`, `prompt_id` NULL, error naming the restart) for the
    next `run_once`. `/queue` is read at most once per call.

    The first poll on a database without the settlement marker (one whose
    `jobs` table predates this change) first settles every `submitted`
    row to `failed` — the pre-fix backlog, requeueing which would render
    thousands of unasked-for images — then writes the marker, so the
    settlement runs exactly once per database. An unreachable ComfyUI
    leaves the job `submitted` (error noted) and the remaining jobs are
    still polled. Returns the number of rows whose state changed; the
    one-time settlement is not part of the count.
    """
    if conn.execute("PRAGMA user_version").fetchone()[0] < _SETTLED_USER_VERSION:
        settle_stale_submitted(conn, _BACKLOG_REASON)
    submitted = conn.execute(
        "SELECT id, prompt_id FROM jobs WHERE state = 'submitted'"
    ).fetchall()
    changed = 0
    known_ids = None
    known_read = False
    for row in submitted:
        job_id = row["id"]
        prompt_id = row["prompt_id"]
        if not prompt_id:
            continue
        try:
            with urllib.request.urlopen(
                base_url + "/history/" + prompt_id, timeout=10
            ) as response:
                history = json.loads(response.read())
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            _mark_error(conn, job_id, str(exc))
            continue
        entry = history.get(prompt_id)
        if not isinstance(entry, dict):
            if not known_read:
                known_ids = _queue_prompt_ids(base_url)
                known_read = True
            if known_ids is not None and prompt_id not in known_ids:
                with conn:
                    conn.execute(
                        "UPDATE jobs SET state = 'queued', prompt_id = NULL,"
                        " error = ?, updated = ? WHERE id = ?",
                        (
                            f"requeued: prompt {prompt_id} is in neither"
                            " /history nor /queue -- a ComfyUI restart"
                            " lost it",
                            time.time(),
                            job_id,
                        ),
                    )
                changed += 1
            continue
        if entry.get("status", {}).get("status_str") == "error":
            _mark_failed(conn, job_id, _error_message(entry))
            changed += 1
            continue
        filename = _first_image(entry)
        if filename is not None:
            with conn:
                conn.execute(
                    "UPDATE jobs SET state = 'done', output = ?, error = NULL,"
                    " updated = ? WHERE id = ?",
                    (filename, time.time(), job_id),
                )
            changed += 1
    return changed


def settle_stale_submitted(conn, reason):
    """Move every `submitted` row to `failed` with `reason`, then write
    the settlement marker — one transaction, so a crash between the two
    can neither settle twice nor not at all. Returns the rows settled.

    This is the one-time disposition of the pre-fix backlog: rows stuck
    `submitted` because every poll before the restart-requeue change left
    them there silently. After the marker exists `poll()` never calls
    this again, and every orphan created after the upgrade is requeued
    instead.
    """
    with conn:
        settled = conn.execute(
            "UPDATE jobs SET state = 'failed', error = ?, updated = ?"
            " WHERE state = 'submitted'",
            (reason, time.time()),
        ).rowcount
        conn.execute(f"PRAGMA user_version = {_SETTLED_USER_VERSION}")
    return settled


def _queue_prompt_ids(base_url):
    """The `prompt_id`s ComfyUI still holds (`/queue`'s `queue_running`
    union `queue_pending`, index 1 of each entry), or `None` when the
    endpoint is unreachable, answers non-2xx, or carries a malformed
    body — `None` means "unknown", never "lost": a job whose id it holds
    may still be rendering, so a failed read must never read as an empty
    queue and requeue it.
    """
    try:
        with urllib.request.urlopen(base_url + "/queue", timeout=10) as response:
            payload = json.loads(response.read())
    except (urllib.error.URLError, ConnectionError, TimeoutError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    prompt_ids = set()
    for key in ("queue_running", "queue_pending"):
        entries = payload.get(key)
        if not isinstance(entries, list):
            return None
        for entry in entries:
            if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                return None
            prompt_ids.add(entry[1])
    return prompt_ids


def pending(conn):
    """The `queued` jobs, oldest first."""
    return conn.execute(
        "SELECT * FROM jobs WHERE state = 'queued' ORDER BY created, id"
    ).fetchall()


def run_once(conn, base_url):
    """Submit every `queued` job (one failure does not stop the next), then
    poll once. Returns `{"submitted", "unreachable", "changed"}` counts and
    never raises on a network error."""
    submitted = 0
    unreachable = 0
    for job in pending(conn):
        if submit(conn, job["id"], base_url):
            submitted += 1
        else:
            unreachable += 1
    changed = poll(conn, base_url)
    return {"submitted": submitted, "unreachable": unreachable, "changed": changed}


def _mark_error(conn, job_id, message):
    """Keep the job `queued`/`submitted` (an unreachable ComfyUI is normal),
    note the error and the time."""
    with conn:
        conn.execute(
            "UPDATE jobs SET error = ?, updated = ? WHERE id = ?",
            (message, time.time(), job_id),
        )


def _mark_failed(conn, job_id, message):
    with conn:
        conn.execute(
            "UPDATE jobs SET state = 'failed', error = ?, updated = ? WHERE id = ?",
            (message, time.time(), job_id),
        )


def _first_image(entry):
    for node in entry.get("outputs", {}).values():
        if not isinstance(node, dict):
            continue
        images = node.get("images")
        if isinstance(images, list) and images and images[0].get("filename"):
            return images[0]["filename"]
    return None


def _error_message(entry):
    messages = entry.get("status", {}).get("messages")
    if isinstance(messages, list) and messages and messages[0]:
        return str(messages[0][0])
    return "ComfyUI reported an error"
