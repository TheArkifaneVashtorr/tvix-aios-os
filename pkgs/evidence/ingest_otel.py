"""Otel ingest (plan 2026-09-08-spend-telemetry, SP7).

``evidence ingest otel [--root DIR] <path>…`` turns the collector's OTLP-JSON
files into ``ledger/otel-claude`` rows keyed ``(session_id, sample_id)``: one
``tokens`` row per ``claude_code.token.usage`` data point and one ``request``
row per ``api_request`` log record. Every other metric/event is skipped. Every
path is realpath-fenced under ``--root`` before anything is read or written; a
torn (unterminated) last line is reported and skipped — never refused — because
the collector is still writing it.

No attribute key whose first ``.``-token is ``user`` or ``organization`` ever
reaches the store (an identity attribute refuses the whole row), and a missing
``session.id`` or a non-numeric ``timeUnixNano`` is refused rather than skipped,
because both are required to key and stamp a row.
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

TOKEN_METRIC = "claude_code.token.usage"
_UNSUPPORTED = object()


class OutsideRoot(Exception):
    """A path resolved outside the declared collector root."""

    def __init__(self, path, root):
        super().__init__(path)
        self.path = path
        self.root = root


def _unwrap(value):
    """The Python value of one OTLP attribute-value wrapper, or `_UNSUPPORTED`
    for any other wrapper (a bare scalar, a missing wrapper, or an array)."""
    if not isinstance(value, dict):
        return _UNSUPPORTED
    keys = value.keys() & {"stringValue", "intValue", "doubleValue", "boolValue"}
    if len(keys) != 1:
        return _UNSUPPORTED
    if "stringValue" in value:
        return value["stringValue"]
    if "intValue" in value:
        return int(value["intValue"])
    if "doubleValue" in value:
        return value["doubleValue"]
    return value["boolValue"]


def _is_identity(key):
    """True when the key's first ``.``-token is ``user`` or ``organization``."""
    return key.split(".", 1)[0] in ("user", "organization")


def _parse_attrs(attrs_raw):
    """(values, refusals) for a data point / record's attribute list. Identity
    attributes and unsupported value wrappers are refused here; everything else
    is unwrapped into `values` keyed by the attribute key."""
    values = {}
    reasons = []
    for item in attrs_raw or []:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        if not isinstance(key, str):
            continue
        if _is_identity(key):
            reasons.append(
                f"{key}: identity attribute present "
                "(the collector's allowlist is broken)"
            )
            continue
        v = _unwrap(item.get("value"))
        if v is _UNSUPPORTED:
            reasons.append(f"attribute {key}: unsupported value type")
            continue
        values[key] = v
    return values, reasons


def _model_split(model_id):
    """Split a model id at the first ``[`` into ``(head, suffix)`` (SP2's rule,
    applied identically): the head must match ``MODEL_ID_RE``; the bracketed
    tail without its brackets is the suffix, ``None`` when there is no ``[``."""
    if model_id is None:
        return None, None
    if "[" not in model_id:
        return model_id, None
    head, rest = model_id.split("[", 1)
    suffix = rest.split("]", 1)[0] if "]" in rest else rest
    return head, suffix


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _at(ns):
    """RFC3339 ``Z`` timestamp from an integer nanosecond count — integer
    arithmetic only (float division here would truncate the last microsecond
    digit differently than ``fromtimestamp``)."""
    secs, rem = divmod(ns, 10**9)
    stamp = datetime.datetime.fromtimestamp(secs, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    return f"{stamp}.{rem // 1000:06d}Z"


def _harness(resource):
    """The resource's ``service.version``, or ``None``."""
    if not isinstance(resource, dict):
        return None
    for item in resource.get("attributes", []):
        if isinstance(item, dict) and item.get("key") == "service.version":
            v = _unwrap(item.get("value"))
            return v if v is not _UNSUPPORTED else None
    return None


def _data_point_row(dp, harness):
    """(row, refusals) for one token.usage data point: `row` when accepted."""
    if not isinstance(dp, dict):
        return None, []
    values, reasons = _parse_attrs(dp.get("attributes"))
    if reasons:
        return None, reasons
    session_id = values.get("session.id")
    if session_id is None:
        reasons.append("session_id: missing")
    ns_raw = dp.get("timeUnixNano")
    ns = _as_int(ns_raw)
    if ns is None:
        reasons.append("timeUnixNano: missing")
    token_type = values.get("type")
    head, suffix = _model_split(values.get("model"))
    if head is not None and not streams.MODEL_ID_RE.fullmatch(head):
        reasons.append("model: not a model-id")
    if reasons:
        return None, reasons
    if "asDouble" in dp:
        value = dp["asDouble"]
    elif "asInt" in dp:
        value = int(dp["asInt"])
    else:
        value = None
    sample_id = f"tokens:{token_type}:{head}:{suffix or '-'}:{ns_raw}"
    row = {
        "kind": "otel-claude",
        "src": "otel",
        "session_id": session_id,
        "sample_id": sample_id,
        "sample": "tokens",
        "at": _at(ns),
        "model": head,
        "model_suffix": suffix,
        "harness_version": harness,
        "terminal_type": values.get("terminal.type"),
        "query_source": None,
        "speed": None,
        "effort": None,
        "agent_name": None,
        "skill_name": None,
        "request_id": None,
        "cost_usd": None,
        "duration_ms": None,
        "input_tokens": None,
        "output_tokens": None,
        "cache_read_tokens": None,
        "cache_creation_tokens": None,
        "token_type": token_type,
        "value": value,
    }
    errors = streams.validate("otel-claude", row)
    if errors:
        return None, errors
    return row, []


def _event_name(record):
    if not isinstance(record, dict):
        return None
    for item in record.get("attributes", []):
        if isinstance(item, dict) and item.get("key") == "event.name":
            v = _unwrap(item.get("value"))
            return v if isinstance(v, str) else None
    return None


def _log_record_row(record, harness):
    """(row, refusals, skipped) for one log record: skipped when its event is
    not ``api_request``."""
    if _event_name(record) != "api_request":
        return None, [], True
    values, reasons = _parse_attrs(record.get("attributes"))
    if reasons:
        return None, reasons, False
    session_id = values.get("session.id")
    if session_id is None:
        reasons.append("session_id: missing")
    ns = _as_int(record.get("timeUnixNano"))
    if ns is None:
        reasons.append("timeUnixNano: missing")
    request_id = values.get("request_id")
    if request_id is None:
        reasons.append("request_id: missing")
    head, suffix = _model_split(values.get("model"))
    if head is not None and not streams.MODEL_ID_RE.fullmatch(head):
        reasons.append("model: not a model-id")
    if reasons:
        return None, reasons, False
    row = {
        "kind": "otel-claude",
        "src": "otel",
        "session_id": session_id,
        "sample_id": request_id,
        "sample": "request",
        "at": _at(ns),
        "model": head,
        "model_suffix": suffix,
        "harness_version": harness,
        "terminal_type": values.get("terminal.type"),
        "query_source": values.get("query_source"),
        "speed": values.get("speed"),
        "effort": values.get("effort"),
        "agent_name": values.get("agent.name"),
        "skill_name": values.get("skill.name"),
        "request_id": request_id,
        "cost_usd": values.get("cost_usd"),
        "duration_ms": values.get("duration_ms"),
        "input_tokens": values.get("input_tokens"),
        "output_tokens": values.get("output_tokens"),
        "cache_read_tokens": values.get("cache_read_tokens"),
        "cache_creation_tokens": values.get("cache_creation_tokens"),
        "token_type": None,
        "value": None,
    }
    errors = streams.validate("otel-claude", row)
    if errors:
        return None, errors, False
    return row, [], False


def _export_outcomes(obj):
    """The ``(row, refusals, skipped)`` triples for one export line, in order:
    every metric's data points (skipping non-token metrics) and every log record
    (skipping non-``api_request`` events)."""
    out = []
    for rm in obj.get("resourceMetrics", []):
        if not isinstance(rm, dict):
            continue
        harness = _harness(rm.get("resource"))
        for sm in rm.get("scopeMetrics", []):
            if not isinstance(sm, dict):
                continue
            for m in sm.get("metrics", []):
                if not isinstance(m, dict) or m.get("name") != TOKEN_METRIC:
                    out.append((None, [], True))
                    continue
                for dp in m.get("sum", {}).get("dataPoints", []):
                    row, reasons = _data_point_row(dp, harness)
                    out.append((row, reasons, False))
    for rl in obj.get("resourceLogs", []):
        if not isinstance(rl, dict):
            continue
        harness = _harness(rl.get("resource"))
        for sl in rl.get("scopeLogs", []):
            if not isinstance(sl, dict):
                continue
            for rec in sl.get("logRecords", []):
                out.append(_log_record_row(rec, harness))
    return out


def ingest(store, paths, root):
    """Fence every path to the root, then write one row per valid point/record.

    Returns ``(n, refused, skipped)``; raises ``OutsideRoot`` before any write
    when a path is outside the root.
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
    skipped = 0
    for p, rp in real_paths:
        try:
            raw = pathlib.Path(rp).read_text()
        except OSError:
            print(f"evidence: ingest otel: {p}: not an otel file", file=sys.stderr)
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
            if not isinstance(obj, dict) or not (
                "resourceMetrics" in obj or "resourceLogs" in obj
            ):
                print(
                    f"evidence: ingest otel: {p}:{lineno}: not an OTLP export line",
                    file=sys.stderr,
                )
                refused += 1
                continue
            for row, reasons, is_skip in _export_outcomes(obj):
                if is_skip:
                    skipped += 1
                elif reasons:
                    for reason in reasons:
                        print(
                            f"evidence: ingest otel: {p}:{lineno}: {reason}",
                            file=sys.stderr,
                        )
                    refused += 1
                else:
                    rows.append(row)
        if torn_last:
            print(
                f"evidence: ingest otel: {p}: last line torn "
                "(the collector is writing); skipped",
                file=sys.stderr,
            )

    if rows:
        evidence.replace_stream(store, "ledger/otel-claude", rows)
    return len(rows), refused, skipped


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = argparse.ArgumentParser(prog="evidence ingest")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    )
    sub = parser.add_subparsers(dest="command")
    ot = sub.add_parser(
        "otel", help="ingest the collector's OTLP-JSON files into ledger/otel-claude"
    )
    ot.add_argument("--root", default="/var/lib/opentelemetry-collector")
    ot.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    if args.command != "otel":
        parser.error("a command is required (otel)")
    try:
        n, refused, skipped = ingest(args.store, args.paths, args.root)
    except OutsideRoot as exc:
        print(
            f"evidence: ingest otel: {exc.path} is outside {exc.root}",
            file=sys.stderr,
        )
        return 2
    print(
        f"ingested {n} rows into ledger/otel-claude "
        f"({refused} refused, {skipped} skipped)"
    )
    return 0 if refused == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
