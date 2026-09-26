#!/usr/bin/env python3
"""factory-codex-usage.py -- best-effort token-usage summary for one Codex rollout.

Reads one Codex CLI rollout (~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<session
id>.jsonl) on stdin and prints one JSON object on stdout in the shape
factory-usage.py prints for a dsh session, so factory-task's `usage:` line and
the ingest read both alike: {"model","events","input","output","cacheRead",
"reasoning","duration_s"}. Never raises: a line that is not a JSON object is
skipped; a field that never appears stays 0 (model, duration_s stay null).

Rollout lines (Codex 0.153.4, measured 2026-09-07): every line is
{"timestamp": "<RFC3339>", "type": "<kind>", "payload": {...}}. A `turn_context`
payload carries model and effort. An `event_msg` payload whose `type` is
"token_count" carries info.total_token_usage with the CUMULATIVE input_tokens,
cached_input_tokens, output_tokens and reasoning_output_tokens -- and `info`
may be null (the last such event often is). The totals reported are the last
non-null ones; `input` is net of the cache, which is what is billed. A line the
decoder cannot parse -- torn, or nested past the recursion limit -- is skipped.
Plan: docs/superpowers/plans/2026-09-08-codex-driver-arm.md (CA1).
"""

import datetime
import json
import re
import sys

FRACTION_RE = re.compile(r"\.(\d{6})\d+")


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _ts(value):
    if not isinstance(value, str):
        return None
    value = FRACTION_RE.sub(r".\1", value).replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        return None


def main() -> int:
    model = None
    events = 0
    first_ts = None
    last_ts = None
    totals = None
    for raw in sys.stdin.buffer:
        # Decode binary-safe: a rollout is text, but stdin may be arbitrary
        # bytes (e.g. the /dev/urandom probe); 'replace' never raises.
        line = raw.decode("utf-8", "replace").strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except (json.JSONDecodeError, ValueError, RecursionError):
            # RecursionError: the C decoder's answer to a line nested deeper
            # than the interpreter's limit; the line is skipped like a torn one.
            continue
        if not isinstance(ev, dict):
            continue
        events += 1
        ts = _ts(ev.get("timestamp"))
        if ts is not None:
            if first_ts is None:
                first_ts = ts
            last_ts = ts
        payload = ev.get("payload")
        if not isinstance(payload, dict):
            continue
        if ev.get("type") == "turn_context":
            m = payload.get("model")
            if isinstance(m, str) and m:
                model = m
        elif ev.get("type") == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            if isinstance(info, dict) and isinstance(
                info.get("total_token_usage"), dict
            ):
                totals = info["total_token_usage"]
    totals = totals or {}
    cached = _int(totals.get("cached_input_tokens"))
    duration_s = None
    if first_ts is not None and last_ts is not None:
        duration_s = (last_ts - first_ts).total_seconds()
    print(
        json.dumps(
            {
                "model": model,
                "events": events,
                "input": _int(totals.get("input_tokens")) - cached,
                "output": _int(totals.get("output_tokens")),
                "cacheRead": cached,
                "reasoning": _int(totals.get("reasoning_output_tokens")),
                "duration_s": duration_s,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
