"""dsh-denials -- list the seat's PreToolUse hook denial records.

hook-guard.py (next to this file) denies dangerous bash/edit/write calls and
prints one compact JSON record per denial to stderr. dsh's own hook bridge
(@deepseek-ai/dsh-hook-protocol) captures that stderr and stores it verbatim
as ``stderrSummary`` on the denying call's ``hook/result`` event, inside the
session transcript at
``$DSH_HOME/sessions/<cwd-key>/<session-id>/session.jsonl.zstd`` -- a root
the audited model cannot write to (see dsh-openrouter.sh and hook-guard.py
for the full account of why that transcript, not a workspace file, is the
audit of record).

This is the reader half: walk every transcript under ``$DSH_HOME/sessions``,
decompress it with the ``zstd`` binary (present on the host; not a Python
dependency), pull out each ``hook/result`` event with ``decision == "deny"``,
and print its timestamp, the guard's stderr record, and -- when the
transcript's neighbouring ``tool/result`` event carries a ``sourceEventSeqs``
back-reference -- the denied command or path from the matching ``tool/call``
event. No secrets are printed: the guard's record only ever names the
command or path it refused, never a credential value.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
import sys

DEFAULT_LIMIT = 20


def _dsh_home() -> str:
    home = os.environ.get("DSH_HOME")
    if home:
        return home
    xdg_data = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.environ.get("HOME", ""), ".local", "share"
    )
    return os.path.join(xdg_data, "dsh-openrouter")


def _read_events(path: str) -> list[dict]:
    proc = subprocess.run(
        ["zstd", "-dc", path],
        check=True,
        capture_output=True,
        text=True,
    )
    events = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


def _tool_call_subject(event: dict) -> str | None:
    """The command or file_path a tool/call event names, or None."""
    arguments = event.get("data", {}).get("arguments")
    if not isinstance(arguments, str):
        return None
    try:
        parsed = json.loads(arguments)
    except ValueError:
        return None
    if not isinstance(parsed, dict):
        return None
    subject = parsed.get("command")
    if subject is None:
        subject = parsed.get("file_path")
    return subject if isinstance(subject, str) else None


def _denials_in_transcript(path: str) -> list[dict]:
    events = _read_events(path)
    by_seq = {event["seq"]: event for event in events if "seq" in event}
    records = []
    for index, event in enumerate(events):
        if event.get("type") != "hook/result":
            continue
        data = event.get("data", {})
        if data.get("decision") != "deny":
            continue
        command = None
        # The tool/result event immediately following in the transcript
        # carries sourceEventSeqs pointing back at the tool/call this
        # PreToolUse hook guarded; the next hook/invoked (a later, unrelated
        # call) bounds the search.
        rest_start = index + 1
        for later in events[rest_start:]:
            later_type = later.get("type")
            if later_type == "hook/invoked":
                break
            if later_type == "tool/result":
                for seq in later.get("sourceEventSeqs") or []:
                    source = by_seq.get(seq)
                    if source is not None and source.get("type") == "tool/call":
                        command = _tool_call_subject(source)
                break
        records.append(
            {
                "ts": event.get("time"),
                "stderrSummary": data.get("stderrSummary"),
                "command": command,
                "session": path,
            }
        )
    return records


def _all_denials(dsh_home: str) -> list[dict]:
    pattern = os.path.join(dsh_home, "sessions", "**", "session.jsonl.zstd")
    records = []
    for path in sorted(glob.glob(pattern, recursive=True)):
        try:
            records.extend(_denials_in_transcript(path))
        except (subprocess.CalledProcessError, OSError) as exc:
            # An audit reader must never look clean because it failed to
            # read something: a transcript this cannot decompress or parse
            # is skipped (not fatal -- other sessions still get read), but
            # never silently, or a corrupt tree would print the same "no
            # denial records found" as a genuinely clean one.
            print(f"warning: skipped {path}: {exc}", file=sys.stderr)
            continue
    records.sort(key=lambda r: (r["ts"] is None, r["ts"]))
    return records


def _format(record: dict) -> str:
    ts = record["ts"]
    when = f"{ts / 1000:.3f}" if isinstance(ts, (int, float)) else "?"
    summary = record["stderrSummary"] or "(no stderrSummary recorded)"
    line = f"{when}  {summary}"
    if record["command"]:
        line += f"  <- {record['command']}"
    return line


def main(argv: list[str]) -> int:
    limit = DEFAULT_LIMIT
    if argv:
        try:
            limit = int(argv[0])
        except ValueError:
            print(
                f"dsh-denials: N must be an integer, got {argv[0]!r}", file=sys.stderr
            )
            return 2
        if limit < 0:
            print("dsh-denials: N must not be negative", file=sys.stderr)
            return 2
    dsh_home = _dsh_home()
    records = _all_denials(dsh_home)
    if not records:
        print(
            f"dsh-denials: no denial records found under {dsh_home}/sessions",
            file=sys.stderr,
        )
        return 0
    for record in records[-limit:] if limit else []:
        print(_format(record))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
