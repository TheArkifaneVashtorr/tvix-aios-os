"""A fail-open SessionStart/PreCompact/Stop hook for the DeepSeek Harness seat.

The wrapper (pkgs/dsh-openrouter/dsh-openrouter.sh) points hooks.json's
SessionStart, PreCompact and Stop events at this one packaged command, beside
the deny-only PreToolUse hook-guard (hook-guard.py next to this file). Decision
58a wants those three events "running the same scripts" as the workspace's
session-start and reset ritual; 60a scopes them to the driver session; 21c
forbids self-nudges.

The discriminator is ``SEAT_MODE`` (SA5): only ``drive`` runs the workspace
scripts. A drive seat runs ``tools/session-start.sh`` for SessionStart and
``tools/ritual.sh`` for PreCompact and Stop, from the current directory (the
workspace ``seat-run.py`` cd'd into), with a 60 s timeout. A job seat (any
other ``SEAT_MODE``, or unset) passes through with empty stdout.

This hook never blocks a turn. It emits no ``decision`` /
``permissionDecision`` field and always exits 0, so a Stop can never re-prompt
the seat (21c). A terminal on stdin, an empty read, non-JSON, a non-object, or
a missing ``hook_event_name`` is one stderr line and exit 0 -- it never waits
on a terminal and never tracebacks. A missing or failing script is one stderr
line and exit 0 (the guard's fail-open-on-exit contract). A Stop payload's
``stop_hook_active`` (the harness's loop-guard field, true when the turn
already continued from a Stop hook) is logged to stderr and changes nothing,
because this hook never blocks.
"""

import json
import os
import subprocess
import sys

# Which workspace script each event rituals. PreCompact and Stop share the
# reset ritual (tools/ritual.sh); SessionStart uses tools/session-start.sh.
_SCRIPT_BY_EVENT = {
    "SessionStart": "tools/session-start.sh",
    "PreCompact": "tools/ritual.sh",
    "Stop": "tools/ritual.sh",
}

_TIMEOUT_SECONDS = 60
_STDIN_BYTE_BOUND = 1 << 20  # 1 MiB, matching the plan's read bound


def _fail(variant):
    print(f"seat-hooks: no hook payload on stdin ({variant})", file=sys.stderr)


def main():
    if sys.stdin.isatty():
        _fail("terminal")
        return 0
    raw = sys.stdin.read(_STDIN_BYTE_BOUND)
    if not raw:
        _fail("empty")
        return 0
    try:
        payload = json.loads(raw)
    except ValueError:
        _fail("not JSON")
        return 0
    if not isinstance(payload, dict):
        _fail("no hook_event_name")
        return 0
    if "hook_event_name" not in payload:
        _fail("no hook_event_name")
        return 0
    event = payload["hook_event_name"]
    if event not in _SCRIPT_BY_EVENT:
        # hooks.json registers this command for SessionStart/PreCompact/Stop
        # only; any other event passes through untouched.
        return 0
    if os.environ.get("SEAT_MODE", "") != "drive":
        return 0
    if event == "Stop" and "stop_hook_active" in payload:
        print(
            f"seat-hooks: stop_hook_active={payload['stop_hook_active']} "
            "(never blocks)",
            file=sys.stderr,
        )
    script = _SCRIPT_BY_EVENT[event]
    try:
        proc = subprocess.run(
            [script],
            timeout=_TIMEOUT_SECONDS,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"seat-hooks: could not run {script}: {exc}", file=sys.stderr)
        return 0
    if proc.returncode != 0:
        print(f"seat-hooks: {script} exited {proc.returncode}", file=sys.stderr)
        return 0
    stdout = proc.stdout
    if event == "Stop":
        # Plain stdout, no structured field: a Stop can never re-prompt the
        # seat (21c).
        sys.stdout.write(stdout)
    else:
        output = {
            "hookSpecificOutput": {
                "hookEventName": event,
                "additionalContext": stdout,
            }
        }
        sys.stdout.write(json.dumps(output) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
