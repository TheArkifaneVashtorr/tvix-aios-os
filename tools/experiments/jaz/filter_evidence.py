#!/usr/bin/env python3
"""filter_evidence.py -- cut one JSONL evidence stream at a fixture's cutoff.

Used by build-fixtures.sh (tools/experiments/jaz/). Not a repo CLI: a small,
stdlib-only helper invoked once per stream per fixture. Reads NDJSON on
stdin, drops identity keys, drops rows whose real event time is after (or
unknowable relative to) the cutoff, writes the kept rows to stdout.

Argv: <ts-field> <ts-kind> <cutoff-epoch> [--exists-root DIR --exists-field FIELD]
  ts-field   the key holding the row's real event time (never the generic
             ingest "ts" envelope field unless that stream's "ts" IS the
             live event time -- see STREAM_TS_FIELD in build-fixtures.sh).
  ts-kind    "iso" (Z-suffixed timestamp) or "epoch" (numeric seconds).
  cutoff-epoch  seconds; rows strictly after this are dropped. A row whose
             ts-field is null/missing is dropped too (unknowable is treated
             as "after the cutoff", never as "before") -- UNLESS --exists-root
             is given: a null-ts row is kept anyway when row[exists-field] is
             a path that exists under DIR. Used for derived/gates.jsonl:
             review_commit_ts is null on ~36% of rows (an early ungated
             verdict with no commit timestamp attached), but the row's own
             review_path is a file inside the archived tree by construction
             only when it landed by the cutoff -- the tree itself is then
             stronger evidence than the missing timestamp field.

A malformed JSON line is not caught here: it raises and exits non-zero,
which build-fixtures.sh treats as a build failure (never silently dropped).

Prints one summary line to stderr: kept/total.
"""

import datetime
import json
import math
import os
import sys

# Matched after normalizing a key to lowercase with "." -> "_", so
# "user.email" and "user_email" both match "email" and a dotted "user.id"
# matches the same rule as "user_id". `session_id` / `session.id` is
# deliberately NOT here: for every stream that carries it (otel-claude,
# debug-usage), it is that stream's own row-identity field -- evidence.py's
# `merge()` dedupes/upserts on the stream's declared `key` tuple, which for
# otel-claude is exactly `("session_id", "sample_id")` (streams.py). It is a
# per-run hash, never an account identifier, and stripping it would break
# row identity for anyone re-processing the snapshot (a duckdb join, a
# future re-ingestion). Measured, not assumed: pkgs/evidence/evidence.py's
# `keyed()`/`merge()` and pkgs/evidence/streams.py's `KINDS[...]["key"]`.
IDENTITY_SUBSTRINGS = (
    "email",
    "account_uuid",
    "organization_id",
    "user_id",
)


def parse_iso(s):
    # All timestamps here are "%Y-%m-%dT%H:%M:%S(.ffffff)?Z" -- but a row's
    # ts-field is JSON-typed, not schema-checked, and json.loads accepts the
    # bare NaN/Infinity extension: an "iso" field can still arrive as a
    # float. Not a string at all is exactly as unparseable as a bad string.
    if not isinstance(s, str):
        raise TypeError(f"not a string: {s!r}")
    s = s.rstrip("Z")
    fmt = "%Y-%m-%dT%H:%M:%S.%f" if "." in s else "%Y-%m-%dT%H:%M:%S"
    dt = datetime.datetime.strptime(s, fmt).replace(tzinfo=datetime.timezone.utc)
    return dt.timestamp()


def strip_identity(obj, stripped):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = k.lower().replace(".", "_")
            if any(s in lk for s in IDENTITY_SUBSTRINGS):
                stripped.add(k)
                continue
            out[k] = strip_identity(v, stripped)
        return out
    if isinstance(obj, list):
        return [strip_identity(v, stripped) for v in obj]
    return obj


def _is_safe_relpath(root, candidate):
    """A row's `exists-field` value is untrusted input from the live
    evidence store: an absolute path or a `../` escape must never let the
    existence check reach outside `root` (the archived fixture tree) to
    answer "does this file exist" about the wider filesystem instead."""
    if os.path.isabs(candidate):
        return False
    root_real = os.path.realpath(root)
    path_real = os.path.realpath(os.path.join(root, candidate))
    return path_real == root_real or path_real.startswith(root_real + os.sep)


def parse_args(argv):
    positional = [a for a in argv if not a.startswith("--")]
    ts_field, ts_kind, cutoff_s = positional[0], positional[1], positional[2]
    exists_root = exists_field = None
    if "--exists-root" in argv:
        exists_root = argv[argv.index("--exists-root") + 1]
    if "--exists-field" in argv:
        exists_field = argv[argv.index("--exists-field") + 1]
    if bool(exists_root) != bool(exists_field):
        raise SystemExit("--exists-root and --exists-field must be given together")
    return ts_field, ts_kind, float(cutoff_s), exists_root, exists_field


def main():
    ts_field, ts_kind, cutoff, exists_root, exists_field = parse_args(sys.argv[1:])
    kept = 0
    total = 0
    kept_by_existence = 0
    stripped = set()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        total += 1
        row = json.loads(line)
        raw = row.get(ts_field)
        if raw is None:
            if (
                exists_root
                and row.get(exists_field)
                and _is_safe_relpath(exists_root, row[exists_field])
            ):
                path = os.path.join(exists_root, row[exists_field])
                if os.path.isfile(path):
                    row = strip_identity(row, stripped)
                    kept += 1
                    kept_by_existence += 1
                    sys.stdout.write(json.dumps(row, sort_keys=True) + "\n")
            continue  # unknowable event time, no existence override -> excluded
        try:
            event_epoch = parse_iso(raw) if ts_kind == "iso" else float(raw)
        except (ValueError, TypeError):
            continue
        if not math.isfinite(event_epoch):
            continue  # NaN/inf: unparseable as a real time, never "before"
        if event_epoch > cutoff:
            continue
        row = strip_identity(row, stripped)
        kept += 1
        sys.stdout.write(json.dumps(row, sort_keys=True) + "\n")
    print(
        f"kept={kept} total={total} kept_by_existence={kept_by_existence} "
        f"stripped_keys={sorted(stripped)}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
