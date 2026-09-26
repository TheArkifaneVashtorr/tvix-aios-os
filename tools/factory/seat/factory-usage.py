#!/usr/bin/env python3
"""factory-usage.py -- best-effort token-usage summary for one dsh session.

Reads a decompressed dsh session.jsonl on stdin (the caller pipes it through
`zstd -dc`) and prints one JSON object on stdout summing every
`assistant/message` event's `data.usage` object, plus the model named in
`data.message.source.model` and the wall clock between the first and last
`time` field (session-relative epoch milliseconds). Never raises: a line it
cannot parse is skipped, and a usage field that never appears stays 0. This
is a helper for factory-task's usage line, not a general dsh transcript
reader.

Field names below (inputTokens/outputTokens/cacheReadTokens/
reasoningTokens, event "time" in epoch ms) were read directly off a real
dsh 0.1.2-rc.1 session.jsonl.zstd on 2026-09-04 -- they are camelCase, not
the input/output/cacheRead names an earlier guess used, which silently
summed to zero against a real transcript. If the pin moves, re-check them
the same way: `zstd -dc <transcript> | python3 -m json.tool` on a few
`assistant/message` lines.
"""

import json
import sys

USAGE_FIELDS = {
    "inputTokens": "input",
    "outputTokens": "output",
    "cacheReadTokens": "cacheRead",
    "reasoningTokens": "reasoning",
}


def main() -> int:
    totals = {out_key: 0 for out_key in USAGE_FIELDS.values()}
    model = None
    first_ts = None
    last_ts = None
    events = 0

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        events += 1

        ts = ev.get("time")
        if isinstance(ts, (int, float)):
            first_ts = ts if first_ts is None else min(first_ts, ts)
            last_ts = ts if last_ts is None else max(last_ts, ts)

        data = ev.get("data")
        if not isinstance(data, dict):
            continue

        usage = data.get("usage")
        if isinstance(usage, dict):
            for src_key, out_key in USAGE_FIELDS.items():
                v = usage.get(src_key)
                if isinstance(v, (int, float)):
                    totals[out_key] += v

        message = data.get("message")
        if isinstance(message, dict):
            source = message.get("source")
            if isinstance(source, dict):
                m = source.get("model")
                if isinstance(m, str) and m:
                    model = m

    duration_s = None
    if first_ts is not None and last_ts is not None:
        duration_s = (last_ts - first_ts) / 1000.0

    print(
        json.dumps(
            {
                "model": model,
                "events": events,
                "input": totals["input"],
                "output": totals["output"],
                "cacheRead": totals["cacheRead"],
                "reasoning": totals["reasoning"],
                "duration_s": duration_s,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
