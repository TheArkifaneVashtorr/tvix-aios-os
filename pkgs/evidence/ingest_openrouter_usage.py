"""Openrouter-usage ingest (plan 2026-09-08-spend-telemetry, SP8).

``evidence ingest openrouter-usage [--root DIR] <path>…`` turns the egress
broker's ``usage.jsonl`` files into one ``ledger/openrouter-usage`` row per
line, keyed ``(instance, request_id)``. Every path is realpath-fenced under
``--root`` before anything is read or written; a torn (unterminated) last line
is reported and skipped — never refused — because the broker is still writing
it. The row is the broker's object plus ``kind``, ``v`` and ``src: "broker"``.
"""

from __future__ import annotations

import argparse
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


def ingest(store, paths, root):
    """Fence every path to the root, then write one row per valid usage line.

    Returns ``(n, refused, torn)``; raises ``OutsideRoot`` before any write when
    a path is outside the root.
    """
    real_root = os.path.realpath(root)
    real_paths = []
    for p in paths:
        rp = os.path.realpath(p)
        if rp != real_root and not rp.startswith(real_root + os.sep):
            raise OutsideRoot(p, root)
        real_paths.append((p, rp))

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
        if torn_last:
            print(
                f"evidence: ingest openrouter-usage: {p}: last line torn "
                "(the broker is writing); skipped",
                file=sys.stderr,
            )
            torn += 1

    if rows:
        evidence.replace_stream(store, "ledger/openrouter-usage", rows)
    return len(rows), refused, torn


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
        n, refused, _torn = ingest(args.store, args.paths, args.root)
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
    print(f"ingested {n} rows into ledger/openrouter-usage ({refused} refused)")
    return 0 if refused == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
