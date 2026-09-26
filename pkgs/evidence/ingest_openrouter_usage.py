"""Openrouter-usage ingest (plan 2026-09-08-spend-telemetry, SP8).

``evidence ingest openrouter-usage [--root DIR] <path>…`` turns the egress
broker's ``usage.jsonl`` files into one ``ledger/openrouter-usage`` row per
line, keyed ``(instance, request_id)``. Every path is realpath-fenced under
``--root`` before anything is read or written; a torn (unterminated) last line
is reported and skipped — never refused — because the broker is still writing
it. The row is the broker's object plus ``kind``, ``v`` and ``src: "broker"``,
then attributed (OC5): ``run_id``/``key``/``attribution`` are set by
:func:`attribute` — by the recorded ``x-factory-task`` header, else by the
one seat task whose [mtime − wall_s, mtime] window contains the row, else
``none``; ambiguity is printed, never guessed (D9–D11).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import sys

import evidence
import streams


class OutsideRoot(Exception):
    """A path resolved outside the declared egress-broker root."""

    def __init__(self, path, root):
        super().__init__(path)
        self.path = path
        self.root = root


def _ts_epoch(value):
    """A ``ts`` string (``YYYY-MM-DDTHH:MM:SS[.f]Z``) as epoch seconds, or
    None when it is absent or unparseable."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.timestamp()


def _task_windows(store):
    """Every ``(run_id, key, start, end)`` window the store's ``derived/tasks``
    rows yield, read once per ingest run: each ``task-result`` row with a
    non-null ``seat_unit``, an int ``wall_s`` and a parseable ``result_mtime``
    contributes ``(run_id, key, mtime − wall_s, mtime)`` in epoch seconds. A
    store without the stream yields no windows."""
    windows = []
    for row in evidence.read(store, "derived/tasks"):
        if row.get("kind") != "task-result":
            continue
        seat_unit = row.get("seat_unit")
        wall_s = row.get("wall_s")
        if not isinstance(seat_unit, str) or not seat_unit:
            continue
        if not isinstance(wall_s, int) or isinstance(wall_s, bool):
            continue
        end = _ts_epoch(row.get("result_mtime"))
        if end is None:
            continue
        windows.append((row.get("run_id"), row.get("key"), end - wall_s, end))
    return windows


def attribute(row, windows):
    """``(attribution, run_id, key)`` for one usage row.

    ``header`` when the broker recorded both halves of the task address;
    else ``window`` when the row is the seat instance's and exactly one
    window contains its ``ts_epoch`` (bounds inclusive); else ``none`` —
    ambiguity is printed, never guessed (D10)."""
    run_id = row.get("run_id")
    key = row.get("key")
    if isinstance(run_id, str) and run_id and isinstance(key, str) and key:
        return "header", run_id, key
    if row.get("instance") == "seat":
        ts = row.get("ts_epoch")
        if isinstance(ts, (int, float)) and not isinstance(ts, bool):
            cands = [(r, k) for (r, k, start, end) in windows if start <= ts <= end]
            if len(cands) == 1:
                return "window", cands[0][0], cands[0][1]
    return "none", None, None


def ingest(store, paths, root):
    """Fence every path to the root, then write one attributed row per valid
    usage line.

    Returns ``(n, refused, torn, counts)`` where ``counts`` maps each
    attribution name to the ingested rows it landed on; raises ``OutsideRoot``
    before any write when a path is outside the root.
    """
    real_root = os.path.realpath(root)
    real_paths = []
    for p in paths:
        rp = os.path.realpath(p)
        if rp != real_root and not rp.startswith(real_root + os.sep):
            raise OutsideRoot(p, root)
        real_paths.append((p, rp))

    windows = _task_windows(store)
    counts = {"header": 0, "window": 0, "none": 0}
    rows = []
    refused = 0
    torn = 0
    for p, rp in real_paths:
        try:
            raw = pathlib.Path(rp).read_text()
        except OSError:
            print(
                f"evidence: ingest openrouter-usage: {p}: not a usage file",
                file=sys.stderr,
            )
            refused += 1
            continue
        torn_last = raw != "" and not raw.endswith("\n")
        lines = raw.split("\n")
        if torn_last:
            lines = lines[:-1]
        for lineno, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                obj = None
            if not isinstance(obj, dict):
                print(
                    f"evidence: ingest openrouter-usage: {p}:{lineno}: not JSON",
                    file=sys.stderr,
                )
                refused += 1
                continue
            row = {**obj, "kind": "openrouter-usage", "v": 1, "src": "broker"}
            attribution, run_id, key = attribute(row, windows)
            row["attribution"] = attribution
            row["run_id"] = run_id
            row["key"] = key
            errors = streams.validate("openrouter-usage", row)
            if errors:
                for reason in errors:
                    print(
                        f"evidence: ingest openrouter-usage: {p}:{lineno}: {reason}",
                        file=sys.stderr,
                    )
                refused += 1
                continue
            rows.append(row)
            counts[attribution] += 1
        if torn_last:
            print(
                f"evidence: ingest openrouter-usage: {p}: last line torn "
                "(the broker is writing); skipped",
                file=sys.stderr,
            )
            torn += 1

    if rows:
        evidence.replace_stream(store, "ledger/openrouter-usage", rows)
    return len(rows), refused, torn, counts


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = argparse.ArgumentParser(prog="evidence ingest")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    )
    sub = parser.add_subparsers(dest="command")
    ou = sub.add_parser(
        "openrouter-usage",
        help="ingest broker usage.jsonl into ledger/openrouter-usage",
    )
    ou.add_argument("--root", default="/var/lib/egress-broker")
    ou.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    if args.command != "openrouter-usage":
        parser.error("a command is required (openrouter-usage)")
    try:
        n, refused, _torn, counts = ingest(args.store, args.paths, args.root)
    except OutsideRoot as exc:
        print(
            f"evidence: ingest openrouter-usage: {exc.path} is outside {exc.root}",
            file=sys.stderr,
        )
        return 2
    except OSError as exc:
        # A store the writer cannot open (unwritable dir, missing parent) is a
        # failure, never a quiet success: surface it on stderr and exit non-zero.
        print(
            f"evidence: ingest openrouter-usage: cannot write to the store: {exc}",
            file=sys.stderr,
        )
        return 1
    print(
        f"ingested {n} rows into ledger/openrouter-usage ({refused} refused; "
        f"attributed header {counts['header']}, window {counts['window']}, "
        f"none {counts['none']})"
    )
    return 0 if refused == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
