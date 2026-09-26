"""Helm API route module — the counts-only engagement stream (HM8).

Decision 18b's local-only engagement stream: `POST /v1/engage` folds one
counter increment into today's `(day, surface)` row and writes the row back
through `evidence.replace_stream(store, "ledger/engagement", rows)` — keyed
`(day, surface)`, all-or-nothing under the store's flock, the verb EV14's
schema names as the writer's (`pkgs/evidence/SCHEMA.md`, term 1). The fields
are exactly EV15's `engagement` kind — `day`, `surface`, `opens`, `dwell_s`,
`feed_likes`, every one an integer — and the route refuses everything else in
code: a closed counter enum, a closed surface enum, a positive integer `n`,
and a closed body key set. Nothing is sent anywhere and nothing is written
under `/var/lib/helm`; the row lives only in the evidence store's ledger,
never ingested from or exported to any path outside the store (term 6).

The evidence module is imported lazily so `api.py`'s `discover()` never needs
it on `sys.path` at import time; only an actual POST reaches it.
"""

from __future__ import annotations

import datetime
import json

COUNTERS = ("opens", "dwell_s", "feed_likes")
SURFACES = ("home", "feed", "seats")


def routes():
    return [("POST", "/v1/engage", engage)]


def _today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _store(cfg):
    import evidence

    return cfg.get("evidence_dir") or evidence.DEFAULT_STORE


def engage(cfg, request):
    """POST /v1/engage — fold one counter increment into today's row.

    The body is parsed as JSON whatever its Content-Type (`sendBeacon` posts
    `text/plain`): `{"counter": <one of COUNTERS>, "n": <int >= 1>,
    "surface": <one of SURFACES>}` -> 204. Anything else -> 400 with
    `{"error": "<field>"}` and nothing written.
    """
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 400, {"error": "body"}
    if not isinstance(body, dict) or set(body) != {"counter", "n", "surface"}:
        return 400, {"error": "body"}
    counter = body["counter"]
    if counter not in COUNTERS:
        return 400, {"error": "counter"}
    surface = body["surface"]
    if surface not in SURFACES:
        return 400, {"error": "surface"}
    n = body["n"]
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        return 400, {"error": "n"}

    import evidence

    store = _store(cfg)
    day = _today()
    rows = evidence.read(store, "ledger/engagement")
    target = None
    for row in rows:
        # the surface half of the key is load-bearing: test_two_surfaces_fold_to_separate_rows
        if row.get("day") == day and row.get("surface") == surface:
            target = row
            break
    if target is None:
        target = {
            "kind": "engagement",
            "day": day,
            "surface": surface,
            "opens": 0,
            "dwell_s": 0,
            "feed_likes": 0,
        }
        rows.append(target)
    target[counter] = target.get(counter, 0) + n
    evidence.replace_stream(store, "ledger/engagement", rows)
    return 204, {}
