"""The one feed app for every ComfyUI world (sub-project 2, GN3+GN4; GN22; GN23).

A stdlib-only `http.server` that fronts EVERY configured world over one
`feed.sqlite` per world (feed_index.py rebuilds each from the PNGs' prompt
chunks). One process binds `(listen, port)` — `127.0.0.1` and the one
feedPort — and every route is world-scoped:

- `GET /` — a 302 to the world whose generator is `active` (else the head of
  worldsOrder, the sorted world names).
- `GET /assets/app.js` / `GET /assets/app.css` — the deck client's mounts
  (GN25): the file at `FEED_APP_JS` / `FEED_APP_CSS` (env read at request
  time — the wrapper exports the store paths the way it exports
  FEED_INDEX_PY), `text/javascript` / `text/css`, both `charset=utf-8`.
  Unset or unreadable is a 404, never an empty 200. Top-level routes: one
  app serves every world.
- `GET /w/<world>/` — the world's page: the world name, the generator's
  `systemctl --user is-active` state (or `unknown`), and the 50 newest
  index rows, each one `<article>` with the render, its positive prompt
  text, `seed <n>`, its mtime, and the like/dislike/regenerate/edit forms —
  all posting to the world-scoped paths. GN25: the page also mounts the
  client — the stylesheet and the deferred script follow the `<main>` open,
  and the main carries `id="feed"`, `data-world`, `data-worlds`
  (worldsOrder, comma-joined) and `data-generator` (the world target's
  `is-active`, the same state every deck response carries) — while the
  article list stays below the mounts: the shell is one page for the
  no-JavaScript path too.
- `POST /w/<world>/{like,dislike,regenerate,edit,dwell}` — the five verbs
  with today's semantics (GN13's dislike records then deletes; dwell counts
  seconds), each answering JSON when the request's Accept names
  `application/json` (comma-split, `;`-params stripped, case-insensitive):
  `{"ok": true, …}` at 200, every error `{"ok": false, "error": …}` at the
  same status. Without the token the answers are unchanged: the 303s, the
  plain texts, the dwell 204. A successful regenerate/edit enqueue is
  submitted at once (GN23 Decision 5: the interactive `queue.run_once`
  against the world's own ComfyUI address, loopback-only by construction).
- `GET /w/<world>/deck?n=&cursor=` — the deck (GN23), the client's route:
  JSON always, even on errors. `n` cards (int 1–50, default 10) in the
  deck's order — unseen first, newest first within each group — each
  `{name, img, prompt, seed, mtime, liked}`; `cursor` (base64 of
  `u:<0|1>:<mtime>:<name>`) serves what follows that keyset, `null` at the
  end. Every successful page also carries `"generator"` (GN25, operator
  decision 2026-09-19): the world target's `is-active` state, the same
  read the shell's `data-generator` renders — the top bar's dot refreshes
  on the deck fetch the client makes anyway; no state route and no
  polling loop exist. When the world's unseen count sits below its
  `deckLowWater` the GET starts the world's `comfy-run-<w>.service`
  oneshot — the demand
  signal, spec §5; the start is best effort (one stderr line on failure,
  the page still goes out).
- `POST /w/<world>/seen` — consume: upserts every repeated `names` form
  value into the `seen` table (cards are marked seen when consumed, never
  when served), answering `{"ok": true, "count": <n>}` on the JSON arm, a
  303 to the world's page otherwise. No engagement counter increments.
- `POST /w/<world>/activate` — the GPU handover (GN24, spec §7): the
  switch changes the deck at once and separately hands the GPU over, and
  the handler asks systemd for the whole trade. `is-active
  comfy-world-<w>.target` first: `active` is the no-op answer
  (`{"ok": true, "world": w, "started": false}` / a 303 to the world's
  page — a double-tap must not thrash the card). Otherwise the flip
  guard: one process-global timestamp behind a lock, 0 at boot, global
  across worlds — a second flip inside `flipGuardSeconds` (30 by
  default, the worlds file's top level) is a 429
  (`{"ok": false, "error": "flip guard", "retry_after": <s>}` / `flip
  guard: <n>s since the last flip`) and nothing starts. Past the guard
  the handler starts ONLY the world's target — never a `comfyui-*` unit
  itself, never a stop (the target's wants plus the generators'
  `Conflicts=` do the trading) — then stamps the clock; a failed start
  is a named 503 (`systemctl start failed for comfy-world-<w>.target`,
  one stderr line), never a silent 200, and never counts as a flip.
- `POST /w/<world>/generation` — the generation switch (GN44): a JSON
  body `{"on": false}` runs `systemctl --user stop
  comfy-run-<w>.service`, `{"on": true}` starts it again — the same
  invocation path as activate, only ever naming the supervisor: the
  generator (`comfyui-<w>.service`), the feed and the shared
  `comfy-author-model.service` are untouched, so a world can drop its
  authoring loop without dropping the world. The deck's payload (and
  the shell's `data-generation` mount) carry `"generation": "on" |
  "off"` — the supervisor unit's systemd state, read fresh on every
  request. GN45: the same payload (and the shell's `data-phase` mount)
  also carries `"phase"` — the supervisor's current word from the
  status cell its loop writes (`authoring`, `mutating`, `rendering`,
  `waiting`, `halted`), read ONLY while that same systemd state says
  the unit is live (a cell from a dead supervisor is a liar), `stale`
  when the cell's stamp is older than `4 x` the world's tick, and null
  when the unit is not live. No new route and no new systemctl
  invocation; the feed never writes the cell.
- `GET /w/<world>/jobs` — a plain-text list of that world's `jobs` rows.
- `GET /w/<world>/out/<name>` — the file of that basename (no `/`, no `..`).
- `GET /healthz` — `ok <worlds>` (worldsOrder, comma-joined).

Before the shell and deck GETs read any row, the stamp gate compares the
output directory's `(name, st_mtime_ns, st_size)` fingerprint against a
per-process cache and rebuilds the index on a difference — a render
dropped (or overwritten in place) after start appears without a restart.

An unknown world in any `/w/<x>/…` path is a 404 before any db open, any
unlink and any systemctl argv: the name is matched against the configured
list, never interpolated.

The page never calls ComfyUI itself outside the interactive run_once
above: submission and polling otherwise stay with `queue.run_once`, driven
by `comfy-feed queue --run-once` (per-world, like `index --rebuild`). The
process opens no socket except to `127.0.0.1:<comfyPort>` when those run,
and to the loopback `--engage-url` (`http://127.0.0.1:7710/v1/engage` by
default) when the periodic flush posts engagement counts — opens, dwell
seconds and likes as bare counters, never content. Everything is
HTML-escaped and there is no script and no external URL — the zero-outbound
rule. `serve` (the default, and the module's ExecStart) rebuilds every
world's index once before it binds, so a fresh world has an index.
"""

import argparse
import base64
import datetime
import html
import http.client
import importlib.util
import json
import math
import os
import pathlib
import secrets
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse, urlsplit

# feed_index.py is a sibling in the source tree but a separate store path once
# packaged: the wrapper sets FEED_INDEX_PY to that path (the FETCH_PY pattern of
# comfy-worlds-init), and the sibling is the fallback for the in-tree unit test.
_HERE = pathlib.Path(__file__).resolve().parent
_index_path = os.environ.get("FEED_INDEX_PY") or str(_HERE / "feed_index.py")
_index_spec = importlib.util.spec_from_file_location("feed_index", _index_path)
feed_index = importlib.util.module_from_spec(_index_spec)
_index_spec.loader.exec_module(feed_index)


def _queue():
    """`queue.py` by path, loaded lazily.

    The packaged `comfy-feed` wrapper sets both `FEED_INDEX_PY` and
    `FEED_QUEUE_PY` (and `queue.py` reads `FEED_INDEX_PY` the same way), so
    this resolves through the environment, with the sibling as the in-tree
    fallback for the unit tests; it is only touched by the POST verbs and the
    `queue --run-once` subcommand, never by `--help` or a plain `serve`.
    """
    queue_path = os.environ.get("FEED_QUEUE_PY") or str(_HERE / "queue.py")
    spec = importlib.util.spec_from_file_location("queue", queue_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _parse_graph(text):
    """The class_type graph of a `renders.prompt` value, or `None` when absent
    or not a JSON object (a PNG without the `prompt` chunk)."""
    if not text:
        return None
    try:
        graph = json.loads(text)
    except (ValueError, TypeError):
        return None
    return graph if isinstance(graph, dict) else None


def _lowest_sampler(graph):
    """`(id, node)` of the KSampler node with the numerically lowest id."""
    best = None
    for node_id, node in graph.items():
        if not isinstance(node, dict) or node.get("class_type") != "KSampler":
            continue
        try:
            key = int(node_id)
        except (ValueError, TypeError):
            continue
        if best is None or key < best[0]:
            best = (key, node)
    return best


def _positive_text(graph):
    """The stored positive prompt: `inputs.text` of the CLIPTextEncode node the
    base (lowest-id) KSampler's `inputs.positive` points at."""
    best = _lowest_sampler(graph)
    if best is None:
        return None
    positive = best[1].get("inputs", {}).get("positive")
    if not isinstance(positive, (list, tuple)) or not positive:
        return None
    target = graph.get(str(positive[0]))
    if not isinstance(target, dict):
        return None
    text = target.get("inputs", {}).get("text")
    return text if isinstance(text, str) else None


def _fresh_seed(old):
    """A 32-bit seed that is not `old` (regenerate/edit never reuse the render's
    seed — the page's answer is always a genuinely new draw)."""
    seed = secrets.randbelow(2**32)
    while seed == old:
        seed = secrets.randbelow(2**32)
    return seed


# GN23 — the stamp gate (Decision 4): the output directory's fingerprint and
# its per-process cache. A deck or shell GET that sees a difference rebuilds
# the index before any row is read; an unchanged directory rebuilds nothing.
# The tuple carries (name, st_mtime_ns, st_size) per PNG — a count-only
# stamp would miss an in-place overwrite at a constant entry count.
_stamp_cache = {}


def _stamp(root, world):
    """The sorted `(name, st_mtime_ns, st_size)` of every `output/*.png`."""
    out = pathlib.Path(root) / "worlds" / world / "output"
    entries = []
    if out.is_dir():
        for png in out.glob("*.png"):
            if png.is_file():
                st = png.stat()
                entries.append((png.name, st.st_mtime_ns, st.st_size))
    entries.sort()
    return entries


def _refresh(root, world):
    """Rebuild the index when the stamp changed since the last look."""
    key = (str(root), world)
    stamp = _stamp(root, world)
    if _stamp_cache.get(key) != stamp:
        feed_index.rebuild(root, world)
        _stamp_cache[key] = stamp


def _encode_cursor(unseen, mtime, name):
    """The base64 of `u:<0|1>:<mtime>:<name>` — the keyset the next page
    asks to follow (`unseen DESC, mtime DESC, name ASC`)."""
    key = 1 if unseen else 0
    return base64.b64encode(f"u:{key}:{mtime}:{name}".encode("utf-8")).decode("ascii")


def _decode_cursor(raw):
    """`(unseen, mtime, name)` from a cursor value, or `None` when it is not
    the shape `_encode_cursor` writes."""
    try:
        text = base64.b64decode(raw, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    parts = text.split(":", 3)
    if len(parts) != 4 or parts[0] != "u" or parts[1] not in ("0", "1"):
        return None
    try:
        mtime = float(parts[2])
    except ValueError:
        return None
    return (int(parts[1]), mtime, parts[3])


def _start_run_unit(systemctl, world):
    """`systemctl --user start --no-block comfy-run-<w>.service` — best
    effort, and never a wait.

    `--no-block` is load-bearing, not tidiness: the unit is `Type=oneshot`
    running a supervisor that loops for hours, so while it runs it sits in
    `activating (start)` and a plain `start` blocks until that run ends
    (measured on core 2026-09-22 — every deck page paid the 5 s timeout
    below and logged a failure, because the demand signal fires whenever
    unseen is under the water line and it was 0 of 92). Enqueuing the job
    and returning is the whole contract here: an inactive unit still
    starts, a running one is still left alone. Any failure (a refusal, an
    exit, a hang past the timeout) is exactly one stderr line: a stuck
    systemctl must not break browsing.
    """
    unit = "comfy-run-" + world + ".service"
    try:
        proc = subprocess.run(
            [systemctl, "--user", "start", "--no-block", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception as exc:
        print(f"deck: starting {unit} failed: {exc}", file=sys.stderr)
        return
    if proc.returncode != 0:
        print(
            f"deck: starting {unit} failed with exit {proc.returncode}",
            file=sys.stderr,
        )


def _parse_generation_body(body):
    """The request's `on` boolean (GN44 Interfaces 1), or None when the
    body is not a JSON object carrying one."""
    try:
        doc = json.loads(body)
    except ValueError:
        return None
    if isinstance(doc, dict) and isinstance(doc.get("on"), bool):
        return doc["on"]
    return None


def generation_state(world, systemctl):
    """`on`/`off` from `is-active comfy-run-<w>.service` (GN44
    Interfaces 3): `active` or `activating` is on, anything else is
    off — read fresh from systemd on every call.
    """
    try:
        proc = subprocess.run(
            [systemctl, "--user", "is-active", "comfy-run-" + world + ".service"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return "off"
    out = (proc.stdout or "").strip()
    return "on" if out in ("active", "activating") else "off"


def _generation_off_path(root, world):
    """The world's generation-off marker (GN58): an empty file beside
    `feed.sqlite`, `run-status.json` and `lab/` — binary presence, zero
    bytes, so it survives a feed restart and a reboot by being a file and
    travels with the world folder."""
    return pathlib.Path(root) / "worlds" / world / "generation-off"


def _generation_is_off(root, world):
    """True while the operator's generation-off marker exists — the
    deck's demand signal asks this before starting the supervisor, so
    browsing the feed cannot undo an explicit `{"on": false}`."""
    return _generation_off_path(root, world).exists()


# GN45 — the supervisor's phase vocabulary: run.py's closed writer enum
# plus the one derived value only the reader can answer. A value outside
# the set is absent, never displayed raw.
_RUN_PHASES = frozenset(("authoring", "mutating", "rendering", "waiting", "halted"))


def _status_ts(text):
    """A status cell's `ts` (the writer's RFC3339 UTC stamp) as a unix
    time, or None when it is not the shape the writer writes."""
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return moment.replace(tzinfo=datetime.timezone.utc).timestamp()


def supervisor_phase(root, world, unit_on, tick):
    """The supervisor's current phase (GN45), or None — never a guess.

    The unit's liveness is the authority, not the file: a status cell
    written by a process that is gone is a liar, so the cell is read
    only while the same `is-active` answer `generation_state` already
    fetched for this payload says the supervisor is live (`unit_on`).
    A phase outside the closed enum, a torn file or an unparseable
    stamp reads as absent. Freshness (Interfaces 5): a stamp older than
    `4 * tick` while the unit is live reads `stale`, never the recorded
    phase — the writer may be wedged mid-phase. The feed never writes
    the cell; this is the read path only.
    """
    if not unit_on:
        return None
    path = pathlib.Path(root) / "worlds" / world / "run-status.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or doc.get("phase") not in _RUN_PHASES:
        return None
    ts = _status_ts(doc.get("ts"))
    if ts is None:
        return None
    if time.time() - ts > 4 * tick:
        return "stale"
    return doc["phase"]


def unit_state(unit, systemctl):
    """A unit's `is-active` answer, or `unknown` when it errors."""
    try:
        proc = subprocess.run(
            [systemctl, "--user", "is-active", unit],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return "unknown"
    if proc.returncode != 0:
        return "unknown"
    out = proc.stdout.strip()
    return out or "unknown"


def generator_state(world, systemctl):
    """The generator's `is-active` answer, or `unknown` when it errors."""
    return unit_state("comfyui-" + world, systemctl)


def world_state(world, systemctl):
    """`is-active comfy-world-<w>.target` — the world's up state (GN25,
    operator decision 2026-09-19: the dot reads the target, the unit the
    activate route starts, so a completed handover reads `active` on the
    deck fetch that follows it).

    Real `systemctl is-active` prints `inactive` and exits 3 — the
    printed state wins over the exit code (`unknown` is for a run that
    says nothing or fails outright), unlike `unit_state`, whose callers
    treat any non-zero exit as no answer.
    """
    try:
        proc = subprocess.run(
            [systemctl, "--user", "is-active", "comfy-world-" + world + ".target"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return "unknown"
    out = (proc.stdout or "").strip()
    return out or "unknown"


# GN24 — the flip clock (Decision 6): one process-global timestamp behind a
# lock. It starts at 0 (the first flip after boot never waits) and is global
# across worlds — flipping sfw then immediately nsfw inside the window gets
# the 429. A failed start never moves it.
_flip_lock = threading.Lock()
_last_flip = 0.0


def _article(row, world):
    """One `<article>` for an index row: the render, its positive prompt text
    (never the raw class_type graph), seed, mtime and the verb forms — every
    action and href world-scoped under `/w/<world>/`."""
    name = row["name"]
    safe = html.escape(name)
    quoted = quote(name, safe="")
    base = "/w/" + world + "/out/"
    href = base + quoted
    graph = _parse_graph(row["prompt"])
    positive = _positive_text(graph) if graph else None
    prompt = html.escape(positive) if positive is not None else "no prompt"
    edit_value = html.escape(positive) if positive is not None else ""
    seed = row["seed"]
    seed_text = f"seed {seed}" if seed is not None else "seed unknown"
    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row["mtime"]))
    verbs = "/w/" + world + "/"
    return (
        "<article>"
        f'<a href="{href}"><img src="{href}" alt="{safe}"></a>'
        f"<p>{prompt}</p>"
        f"<span>{seed_text}</span>"
        f"<time>{mtime}</time>"
        f'<form method="post" action="{verbs}like">'
        f'<input type="hidden" name="name" value="{safe}">'
        '<button type="submit">like</button>'
        "</form>"
        f'<form method="post" action="{verbs}dislike">'
        f'<input type="hidden" name="name" value="{safe}">'
        '<button type="submit">dislike</button>'
        "</form>"
        f'<form method="post" action="{verbs}regenerate">'
        f'<input type="hidden" name="name" value="{safe}">'
        '<button type="submit">regenerate</button>'
        "</form>"
        f'<form method="post" action="{verbs}edit">'
        f'<input type="hidden" name="name" value="{safe}">'
        f'<input type="text" name="prompt" value="{edit_value}">'
        '<button type="submit">edit</button>'
        "</form>"
        "</article>"
    )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect: the beacon posts to its configured loopback
    engage URL only, and a `302` off that host must never be followed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Engagement:
    """In-memory engagement counters, posted as bare counts to Helm's
    `/v1/engage` (never content). `flush()` posts one body per non-zero
    counter, and each counter is cleared only after its own 204 — a counter
    whose post fails or is refused keeps its full pending amount for the next
    tick, and no counter's fate depends on any other's."""

    COUNTERS = ("opens", "dwell_s", "feed_likes")

    def __init__(self, engage_url):
        self.engage_url = engage_url
        self._lock = threading.Lock()
        self._counters = {"opens": 0, "dwell_s": 0, "feed_likes": 0}
        self._opener = urllib.request.build_opener(_NoRedirect())

    def increment(self, counter, n=1):
        with self._lock:
            self._counters[counter] += n

    def flush(self):
        if not self.engage_url:
            with self._lock:
                for counter in self._counters:
                    self._counters[counter] = 0
            return
        posted = 0
        for counter in self.COUNTERS:
            with self._lock:
                n = self._counters[counter]
            if n <= 0:
                continue
            data = json.dumps({"counter": counter, "n": n, "surface": "feed"}).encode(
                "utf-8"
            )
            req = urllib.request.Request(
                self.engage_url,
                data=data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            try:
                with self._opener.open(req, timeout=5) as resp:
                    if resp.status != 204:
                        raise urllib.error.URLError(f"unexpected status {resp.status}")
            except (
                urllib.error.URLError,
                http.client.HTTPException,
                ConnectionError,
                TimeoutError,
                OSError,
            ):
                print(
                    f"engage: {counter} post to {self.engage_url} failed — "
                    f"{n} kept for retry",
                    file=sys.stderr,
                )
                continue
            with self._lock:
                self._counters[counter] -= n
            posted += 1
        if posted:
            print(
                f"engage: posted {posted} bodies to {self.engage_url}", file=sys.stderr
            )


def _arm_flush_timer(engage, flush_interval):
    def tick():
        engage.flush()
        _arm_flush_timer(engage, flush_interval)

    timer = threading.Timer(flush_interval, tick)
    timer.daemon = True
    timer.start()


def _sigterm(server):
    def handler(signum, frame):
        server.engage.flush()
        # `serve_forever` runs on this (main) thread, so `server.shutdown()`
        # would deadlock waiting on `__is_shut_down` that only that loop can
        # set. `SystemExit` unwinds it instead: the loop's `finally` closes the
        # socket, and the process exits 0.
        raise SystemExit(0)

    return handler


def _wants_json(handler):
    """The Accept rule: any token (comma-split, `;`-params stripped,
    case-insensitive) equal to `application/json` selects the JSON arm —
    `text/plain; charset=utf-8` and `text/json` never do."""
    accept = handler.headers.get("Accept") or ""
    for token in accept.split(","):
        mime = token.split(";")[0].strip().lower()
        if mime == "application/json":
            return True
    return False


def _split_world_path(path):
    """`(world, rest)` for a `/w/<world>/<rest…>` path, or `(None, None)`.

    `rest` is everything after the world's `/` (empty for the shell), so
    `/w/sfw/` -> `("sfw", "")`, `/w/sfw/like` -> `("sfw", "like")` and
    `/w/sfw` (no trailing slash) -> `(None, None)`.
    """
    tail = path[len("/w/") :]
    if "/" not in tail:
        return (None, None)
    world, _, rest = tail.partition("/")
    if not world:
        return (None, None)
    return (world, rest)


def make_handler(root, worlds, systemctl, engage, flip_guard_seconds):
    root = pathlib.Path(root)
    worlds_order = sorted(worlds)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence stderr access-log spam
            pass

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if path == "/healthz":
                self._text(200, "ok " + ",".join(worlds_order))
            elif path == "/":
                self._root_redirect()
            elif path == "/assets/app.js":
                self._asset("FEED_APP_JS", "text/javascript; charset=utf-8")
            elif path == "/assets/app.css":
                self._asset("FEED_APP_CSS", "text/css; charset=utf-8")
            elif path.startswith("/w/"):
                world, rest = _split_world_path(path)
                if world is None or world not in worlds:
                    self._text(404, "not found")
                elif rest == "":
                    self._index(world)
                elif rest == "jobs":
                    self._jobs(world)
                elif rest == "deck":
                    self._deck(world, parsed.query)
                elif rest.startswith("out/"):
                    self._out(world, rest[len("out/") :])
                else:
                    self._text(404, "not found")
            else:
                self._text(404, "not found")

        def do_POST(self):
            path = urlparse(self.path).path
            raw_length = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_length)
            except ValueError:
                self._answer(400, "bad Content-Length")
                return
            if length > 65536:
                self._answer(413, "body too large")
                return
            body = self.rfile.read(length).decode("utf-8", "replace")
            form = parse_qs(body, keep_blank_values=True, max_num_fields=64)
            world, verb = _split_world_path(path)
            if world is None or world not in worlds:
                # Before any db open, any unlink, any systemctl argv.
                self._answer(404, "not found")
                return
            if verb == "like":
                self._like(world, form)
            elif verb == "dislike":
                self._dislike(world, form)
            elif verb == "regenerate":
                self._regenerate(world, form)
            elif verb == "edit":
                self._edit(world, form)
            elif verb == "dwell":
                self._dwell(form)
            elif verb == "seen":
                self._seen(world, form)
            elif verb == "activate":
                self._activate(world)
            elif verb == "generation":
                self._generation(world, body)
            else:
                self._answer(404, "not found")

        @staticmethod
        def _field(form, key):
            values = form.get(key)
            return values[0] if values else ""

        def _like(self, world, form):
            name = self._field(form, "name")
            conn = feed_index.open_db(root, world)
            row = conn.execute(
                "SELECT 1 FROM renders WHERE name = ?", (name,)
            ).fetchone()
            if row is None:
                self._answer(404, "not found")
                return
            with conn:
                conn.execute(
                    "INSERT INTO likes(name, liked_at) VALUES(?, ?)"
                    " ON CONFLICT(name) DO UPDATE SET liked_at = excluded.liked_at",
                    (name, time.time()),
                )
            engage.increment("feed_likes")
            if _wants_json(self):
                self._json(200, {"ok": True, "name": name})
            else:
                self._redirect("/#" + quote(name, safe=""))

        def _dislike(self, world, form):
            name = self._field(form, "name")
            conn = feed_index.open_db(root, world)
            row = conn.execute(
                "SELECT prompt FROM renders WHERE name = ?", (name,)
            ).fetchone()
            if row is None:
                self._answer(404, "not found")
                return
            # Record before delete: the verdict must survive a stuck file.
            # The prompt is the render's positive text extracted exactly as
            # `_article` extracts it; a render with no extractable text
            # stores the empty string — recorded, never skipped.
            graph = _parse_graph(row["prompt"])
            positive = _positive_text(graph) if graph else None
            prompt = positive if positive is not None else ""
            with conn:
                conn.execute(
                    "INSERT INTO dislikes(name, prompt, disliked_at)"
                    " VALUES(?, ?, ?)"
                    " ON CONFLICT(name) DO UPDATE SET prompt = excluded.prompt,"
                    " disliked_at = excluded.disliked_at",
                    (name, prompt, time.time()),
                )
            target = root / "worlds" / world / "output" / name
            try:
                target.unlink(missing_ok=True)
            except OSError as exc:
                print(
                    f"dislike: could not delete {target}: {exc}",
                    file=sys.stderr,
                )
            if _wants_json(self):
                self._json(200, {"ok": True, "name": name, "deleted": True})
            else:
                self._redirect("/#" + quote(name, safe=""))

        def _regenerate(self, world, form):
            name = self._field(form, "name")
            queue_mod = _queue()
            conn = queue_mod.open_db(root, world)
            row = conn.execute(
                "SELECT prompt, seed FROM renders WHERE name = ?", (name,)
            ).fetchone()
            if row is None:
                self._answer(404, "not found")
                return
            graph = _parse_graph(row["prompt"])
            if graph is None:
                self._answer(409, "no workflow recorded for " + name)
                return
            seed = _fresh_seed(row["seed"])
            best = _lowest_sampler(graph)
            if best is not None:
                best[1].setdefault("inputs", {})["seed"] = seed
            job_id = queue_mod.enqueue(
                conn, "regenerate", name, json.dumps(graph), seed
            )
            # Decision 5: the interactive run_once — the user asked for this
            # render now, so the enqueue is submitted at once (the queue's
            # loopback-only rule holds: the world's own comfyPort).
            queue_mod.run_once(
                conn, "http://127.0.0.1:" + str(worlds[world]["comfyPort"])
            )
            if _wants_json(self):
                self._json(200, {"ok": True, "job": job_id})
            else:
                self._redirect("/?job=" + job_id)

        def _edit(self, world, form):
            name = self._field(form, "name")
            prompt = self._field(form, "prompt")
            if prompt == "":
                self._answer(400, "empty prompt")
                return
            queue_mod = _queue()
            conn = queue_mod.open_db(root, world)
            row = conn.execute(
                "SELECT prompt, seed FROM renders WHERE name = ?", (name,)
            ).fetchone()
            if row is None:
                self._answer(404, "not found")
                return
            graph = _parse_graph(row["prompt"])
            if graph is None:
                self._answer(409, "no workflow recorded for " + name)
                return
            positive = _positive_text(graph)
            for node in graph.values():
                if (
                    not isinstance(node, dict)
                    or node.get("class_type") != "CLIPTextEncode"
                ):
                    continue
                inputs = node.get("inputs", {})
                if positive is not None and inputs.get("text") == positive:
                    inputs["text"] = prompt
            seed = _fresh_seed(row["seed"])
            best = _lowest_sampler(graph)
            if best is not None:
                best[1].setdefault("inputs", {})["seed"] = seed
            job_id = queue_mod.enqueue(conn, "edit", name, json.dumps(graph), seed)
            # Decision 5 (the regenerate arm above): submit the enqueue at
            # once, interactively.
            queue_mod.run_once(
                conn, "http://127.0.0.1:" + str(worlds[world]["comfyPort"])
            )
            if _wants_json(self):
                self._json(200, {"ok": True, "job": job_id})
            else:
                self._redirect("/?job=" + job_id)

        def _dwell(self, form):
            raw = self._field(form, "seconds")
            try:
                seconds = int(raw)
            except ValueError:
                self._answer(400, "bad seconds")
                return
            if seconds < 0 or seconds > 86400:
                self._answer(400, "bad seconds")
                return
            engage.increment("dwell_s", seconds)
            if _wants_json(self):
                self._json(200, {"ok": True, "seconds": seconds})
            else:
                self._empty(204)

        def _seen(self, world, form):
            """Consume: upsert every repeated `names` value (Decision 3), no
            engagement counter."""
            names = form.get("names") or []
            conn = feed_index.open_db(root, world)
            feed_index.mark_seen(conn, names)
            if _wants_json(self):
                self._json(200, {"ok": True, "count": len(names)})
            else:
                self._redirect("/w/" + world + "/")

        def _activate(self, world):
            """POST /w/<world>/activate — the GPU handover (GN24, spec §7).

            The unit names come from the matched world (the dispatch's
            404 already proved membership), never from the request path.
            The handler starts only `comfy-world-<w>.target`: the target's
            `wants` plus the generators' `Conflicts=` do the whole trade,
            so no `comfyui-*` unit and no stop is ever named here.
            """
            unit = "comfy-world-" + world + ".target"
            if unit_state(unit, systemctl) == "active":
                if _wants_json(self):
                    self._json(200, {"ok": True, "world": world, "started": False})
                else:
                    self._redirect("/w/" + world + "/")
                return
            global _last_flip
            now = time.time()
            with _flip_lock:
                since = now - _last_flip
            if since < flip_guard_seconds:
                if _wants_json(self):
                    self._json(
                        429,
                        {
                            "ok": False,
                            "error": "flip guard",
                            "retry_after": max(
                                1, math.ceil(flip_guard_seconds - since)
                            ),
                        },
                    )
                else:
                    self._text(429, f"flip guard: {int(since)}s since the last flip")
                return
            try:
                proc = subprocess.run(
                    [systemctl, "--user", "start", unit],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except Exception as exc:
                print(f"activate: starting {unit} failed: {exc}", file=sys.stderr)
                self._answer(503, "systemctl start failed for " + unit)
                return
            if proc.returncode != 0:
                print(
                    f"activate: starting {unit} failed with exit"
                    f" {proc.returncode}: {proc.stderr.strip()}",
                    file=sys.stderr,
                )
                self._answer(503, "systemctl start failed for " + unit)
                return
            # Only a successful handover is a flip: a refused start leaves
            # the clock alone, so the retry is not eaten by the guard.
            with _flip_lock:
                _last_flip = now
            if _wants_json(self):
                self._json(200, {"ok": True, "world": world, "started": True})
            else:
                self._redirect("/w/" + world + "/")

        def _generation(self, world, body):
            """POST /w/<world>/generation — the generation switch (GN44):
            `{"on": false}` stops the supervisor, `{"on": true}` starts it
            (the dispatch's membership 404 already ran)."""
            on = _parse_generation_body(body)
            if on is None:
                self._answer(400, "bad body")
                return
            unit = "comfy-run-" + world + ".service"
            action = "start" if on else "stop"
            # GN58: the marker is written BEFORE the stop is attempted,
            # so a transient systemctl failure cannot leave the deck
            # free to fight the operator's decision, and removed BEFORE
            # an explicit start, so a failed start still lets the
            # ordinary demand signal self-heal. Only {"on": true}
            # clears it — nothing else does, reboot included.
            marker = _generation_off_path(root, world)
            try:
                if on:
                    marker.unlink(missing_ok=True)
                else:
                    marker.touch()
            except OSError as exc:
                print(
                    f"generation: marker {action} {marker} failed: {exc}",
                    file=sys.stderr,
                )
                self._answer(503, f"generation-off marker failed for {world}")
                return
            try:
                proc = subprocess.run(
                    [systemctl, "--user", action, unit],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except Exception as exc:
                print(
                    f"generation: {action} {unit} failed: {exc}",
                    file=sys.stderr,
                )
                self._answer(503, f"systemctl {action} failed for {unit}")
                return
            if proc.returncode != 0:
                print(
                    f"generation: {action} {unit} failed with exit"
                    f" {proc.returncode}: {proc.stderr.strip()}",
                    file=sys.stderr,
                )
                self._answer(503, f"systemctl {action} failed for {unit}")
                return
            if _wants_json(self):
                self._json(
                    200,
                    {
                        "ok": True,
                        "world": world,
                        "generation": "on" if on else "off",
                    },
                )
            else:
                self._redirect("/w/" + world + "/")

        def _deck(self, world, query):
            """The deck — the client's route: JSON always, even on errors
            (Decision 14). The stamp gate runs first; the low-water start
            runs after the page is built."""
            _refresh(root, world)
            params = parse_qs(query, keep_blank_values=True, max_num_fields=64)
            try:
                n = int((params.get("n") or ["10"])[0])
            except ValueError:
                self._json(400, {"ok": False, "error": "bad n"})
                return
            if not 1 <= n <= 50:
                self._json(400, {"ok": False, "error": "bad n"})
                return
            raw_cursor = (params.get("cursor") or [""])[0]
            after = None
            if raw_cursor:
                after = _decode_cursor(raw_cursor)
                if after is None:
                    self._json(400, {"ok": False, "error": "bad cursor"})
                    return
            conn = feed_index.open_db(root, world)
            rows = feed_index.deck_page(conn, after=after, limit=n + 1)
            more = len(rows) > n
            rows = rows[:n]
            cards = []
            for row in rows:
                graph = _parse_graph(row["prompt"])
                positive = _positive_text(graph) if graph else None
                cards.append(
                    {
                        "name": row["name"],
                        "img": "/w/" + world + "/out/" + quote(row["name"], safe=""),
                        "prompt": positive,
                        "seed": row["seed"],
                        "mtime": row["mtime"],
                        "liked": bool(row["liked"]),
                    }
                )
            nxt = None
            if more and rows:
                last = rows[-1]
                nxt = _encode_cursor(last["unseen"], last["mtime"], last["name"])
            # The demand signal (spec §5): unseen below the world's
            # deckLowWater starts the comfy-run oneshot — the unit name
            # from the matched world, never the request path. GN58: an
            # existing generation-off marker suppresses the signal —
            # the deck must not fight an explicit switch-off.
            if not _generation_is_off(root, world) and (
                feed_index.unseen_count(conn) < worlds[world].get("deckLowWater", 5)
            ):
                _start_run_unit(systemctl, world)
            # GN25 (operator decision 2026-09-19): the carried generator
            # state — the dot refreshes on this fetch, not a state route.
            gen = world_state(world, systemctl)
            # GN44: the generation state rides every page beside it —
            # the chrome's status word refreshes on the same fetch, read
            # fresh from systemd every time.
            gen_on = generation_state(world, systemctl)
            # GN45: the supervisor's phase rides the same payload — no
            # new route and no new systemctl invocation (Interfaces 7):
            # the cell is read only while the is-active answer above says
            # the unit is live, and freshness is judged against 4 x the
            # world's tick from the same worlds config (Interfaces 4+5).
            phase = supervisor_phase(
                root, world, gen_on == "on", worlds[world].get("tickSeconds", 120)
            )
            self._json(
                200,
                {
                    "world": world,
                    "cards": cards,
                    "cursor": nxt,
                    "generator": gen,
                    "generation": gen_on,
                    "phase": phase,
                },
            )

        def _jobs(self, world):
            queue_mod = _queue()
            conn = queue_mod.open_db(root, world)
            rows = conn.execute(
                "SELECT id, state, kind, source, seed, output"
                " FROM jobs ORDER BY created DESC, id DESC"
            ).fetchall()
            lines = [
                " ".join(
                    [
                        row["id"],
                        row["state"],
                        row["kind"],
                        row["source"] or "-",
                        str(row["seed"]),
                        row["output"] or "-",
                    ]
                )
                for row in rows
            ]
            self._text(200, "\n".join(lines) + ("\n" if lines else ""))

        def _root_redirect(self):
            target = None
            for world in worlds_order:
                if generator_state(world, systemctl) == "active":
                    target = world
                    break
            if target is None:
                target = worlds_order[0]
            self.send_response(302)
            self.send_header("Location", "/w/" + target + "/")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _redirect(self, location):
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _text(self, code, body):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, payload):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _answer(self, code, message):
            """An error body: JSON `{"ok": false, "error": …}` when the
            request asked for JSON, today's plain text otherwise."""
            if _wants_json(self):
                self._json(code, {"ok": False, "error": message})
            else:
                self._text(code, message)

        def _index(self, world):
            engage.increment("opens")
            state = generator_state(world, systemctl)
            # GN25: the target state (not the generator unit's) — the dot's
            # source, identical to every deck response's `generator`.
            target = world_state(world, systemctl)
            # GN44: the supervisor's on/off — the chrome's status word
            # paints from this mount before the first deck fetch.
            generation = generation_state(world, systemctl)
            # GN45: the phase word rides the same mount, read under the
            # same liveness answer (Interfaces 4) so the chrome paints
            # both words from load on; the empty word when not live.
            phase = supervisor_phase(
                root, world, generation == "on", worlds[world].get("tickSeconds", 120)
            )
            phase_word = phase or ""
            _refresh(root, world)
            conn = feed_index.open_db(root, world)
            rows = feed_index.newest(conn, 50)
            articles = (
                "".join(_article(row, world) for row in rows) or "<p>no renders yet</p>"
            )
            # The mounts follow the main open — the stylesheet, the
            # deferred script — and the article list stays BELOW them:
            # the shell is one page for the no-JavaScript path too. Every
            # world name is escaped, data attributes included.
            body = (
                '<!doctype html><html><head><meta charset="utf-8">'
                f"<title>{html.escape(world)}</title></head>"
                f'<body><main id="feed" data-world="{html.escape(world)}"'
                f' data-worlds="{html.escape(",".join(worlds_order))}"'
                f' data-generator="{html.escape(target)}"'
                f' data-generation="{generation}"'
                f' data-phase="{phase_word}">'
                '<link rel="stylesheet" href="/assets/app.css">'
                '<script src="/assets/app.js" defer></script>'
                f"<h1>{html.escape(world)}</h1>"
                f"<p>generator {html.escape(state)}</p>"
                f"{articles}</main></body></html>"
            )
            self._html(body)

        def _html(self, body):
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _out(self, world, raw):
            name = unquote(raw)
            if not name or "/" in name or ".." in name:
                self._empty(404)
                return
            target = root / "worlds" / world / "output" / name
            try:
                data = target.read_bytes()
            except OSError:
                self._empty(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _empty(self, code):
            self.send_response(code)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _asset(self, env_var, content_type):
            """A mounted client asset: the file at the env path (read at
            request time — the wrapper exports the store path), 404 when
            unset or unreadable — never an empty 200."""
            path = os.environ.get(env_var)
            if not path:
                self._empty(404)
                return
            try:
                data = pathlib.Path(path).read_bytes()
            except OSError:
                self._empty(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def build_server(
    root,
    worlds,
    systemctl,
    port=0,
    engage_url=None,
    flush_interval=3600,
    listen="127.0.0.1",
    flip_guard_seconds=30,
):
    if engage_url and urlsplit(engage_url).hostname != "127.0.0.1":
        raise ValueError("feed: engage-url is loopback-only")
    if not isinstance(worlds, dict) or not worlds:
        raise ValueError("feed: at least one world is required")
    for name, member in worlds.items():
        low = member.get("deckLowWater", 5) if isinstance(member, dict) else None
        if isinstance(low, bool) or not isinstance(low, int) or low < 0:
            raise ValueError(
                f"feed: worlds.{name} deckLowWater must be an integer >= 0"
            )
        # GN45: the phase cell's freshness window is 4 x this tick (the
        # supervisor's own --tick knob; 120 is both sides' default).
        tick = member.get("tickSeconds", 120) if isinstance(member, dict) else None
        if isinstance(tick, bool) or not isinstance(tick, int) or tick < 1:
            raise ValueError(f"feed: worlds.{name} tickSeconds must be an integer >= 1")
    # GN24 — the flip guard window (the module renders it into the worlds
    # file's top level as flipGuardSeconds; 0 = the guard never holds).
    if (
        isinstance(flip_guard_seconds, bool)
        or not isinstance(flip_guard_seconds, int)
        or flip_guard_seconds < 0
    ):
        raise ValueError("feed: flipGuardSeconds must be an integer >= 0")
    engage = Engagement(engage_url)
    for world in sorted(worlds):
        feed_index.rebuild(root, world)
        # Prime the stamp gate (Decision 4): the start's rebuild is the
        # baseline, so an unchanged directory rebuilds never again.
        _stamp_cache[(str(root), world)] = _stamp(root, world)
    server = ThreadingHTTPServer(
        (listen, port),
        make_handler(root, worlds, systemctl, engage, flip_guard_seconds),
    )
    server.engage = engage
    if engage_url:
        _arm_flush_timer(engage, flush_interval)
    return server


def _load_worlds(path):
    """The validated worlds dict and the flip guard from the worlds file, or
    SystemExit(2).

    One refusal per shape, each naming the file (and the offending member):
    unreadable/not an object, a missing or empty `worlds` object, and a member
    whose `comfyPort` is not an integer 1..65535. GN24: the top-level
    `flipGuardSeconds` rides along (30 when absent; build_server validates
    the value).
    """
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        print(f"comfy-feed: {path}: unreadable worlds file: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    if not isinstance(doc, dict):
        print(
            f"comfy-feed: {path}: the worlds file must be a JSON object",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    raw = doc.get("worlds")
    if not isinstance(raw, dict) or not raw:
        print(
            f"comfy-feed: {path}: the worlds file must carry a non-empty"
            ' "worlds" object',
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    worlds = {}
    for name, member in raw.items():
        port = member.get("comfyPort") if isinstance(member, dict) else None
        if (
            isinstance(port, bool)
            or not isinstance(port, int)
            or not 1 <= port <= 65535
        ):
            print(
                f"comfy-feed: {path}: worlds.{name} must carry comfyPort"
                " as an integer 1..65535",
                file=sys.stderr,
            )
            raise SystemExit(2) from None
        worlds[name] = {
            "comfyPort": port,
            # GN23: the deck's low-water knob rides the worlds file (the
            # module renders it per world); absent means the default 5.
            # build_server validates the value.
            "deckLowWater": member.get("deckLowWater", 5),
            # GN45: the supervisor's tick, the phase cell's freshness
            # window (4 x this); absent means the 120 both the module's
            # tickSeconds and run.py's --tick default to. build_server
            # validates the value.
            "tickSeconds": member.get("tickSeconds", 120),
        }
    return worlds, doc.get("flipGuardSeconds", 30)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="comfy-feed")
    sub = parser.add_subparsers(dest="command")

    serve_p = sub.add_parser(
        "serve", help="serve every world's feed over HTTP (the default)"
    )
    index_p = sub.add_parser("index", help="rebuild the feed.sqlite index")
    prune_p = sub.add_parser(
        "prune", help="cap stored renders, deleting the oldest UNLIKED ones"
    )
    queue_p = sub.add_parser(
        "queue", help="drive the job queue against ComfyUI on loopback"
    )

    def add_serve_flags(p, required):
        p.add_argument("--root", required=required)
        p.add_argument("--port", type=int, required=required)
        p.add_argument("--listen", required=required)
        p.add_argument("--worlds-file", required=required)
        p.add_argument("--systemctl", default="systemctl")
        p.add_argument("--engage-url", default="http://127.0.0.1:7710/v1/engage")

    add_serve_flags(parser, False)  # the module's ExecStart passes no subcommand
    add_serve_flags(serve_p, True)

    index_p.add_argument("--world", required=True)
    index_p.add_argument("--root", required=True)
    index_p.add_argument("--rebuild", action="store_true")

    prune_p.add_argument("--world", required=True)
    prune_p.add_argument("--root", required=True)
    prune_p.add_argument(
        "--keep",
        type=int,
        required=True,
        help="the most renders to store; liked renders are never deleted, so a"
        " world whose likes exceed this keeps them all and stays above it",
    )

    queue_p.add_argument("--world", required=True)
    queue_p.add_argument("--root", required=True)
    queue_p.add_argument("--run-once", action="store_true")
    queue_p.add_argument("--base-url", required=True)

    args = parser.parse_args(argv)

    if args.command == "index":
        if not args.rebuild:
            parser.error("index: --rebuild is required")
        print(feed_index.rebuild(args.root, args.world))
        return 0

    if args.command == "prune":
        if args.keep < 0:
            parser.error("prune: --keep must not be negative")
        print(feed_index.prune(args.root, args.world, args.keep))
        return 0

    if args.command == "queue":
        if not args.run_once:
            parser.error("queue: --run-once is required")
        queue_mod = _queue()
        conn = queue_mod.open_db(args.root, args.world)
        result = queue_mod.run_once(conn, args.base_url)
        print(
            f"submitted={result['submitted']} unreachable={result['unreachable']}"
            f" changed={result['changed']}"
        )
        return 0

    # command is None (bare, the module's ExecStart) or "serve".
    if not args.root or args.port is None or not args.listen or not args.worlds_file:
        parser.error("serve requires --root, --port, --listen and --worlds-file")
    worlds, flip_guard_seconds = _load_worlds(args.worlds_file)
    server = build_server(
        args.root,
        worlds,
        args.systemctl,
        args.port,
        args.engage_url,
        listen=args.listen,
        flip_guard_seconds=flip_guard_seconds,
    )
    if args.engage_url:
        signal.signal(signal.SIGTERM, _sigterm(server))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    main()
