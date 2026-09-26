"""Task-result ingest (plan 2026-09-06-telemetry-store-1, T2).

``evidence ingest result`` turns one ``.result`` file — the record
``factory-task`` writes beside a run's log — into one ``derived/tasks`` row
keyed ``(run_id, key)``. Every field is produced from one line of the file:
free text never reaches the stream, the log beside the result is never opened,
and every path is fenced to the runs root before anything is written.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import sys

import evidence
import streams
import tasks

STATUS_RE = re.compile(r"^FACTORY-RESULT[ \t]+status=(\S+)", re.MULTILINE)
COMMITS_RE = re.compile(r"^FACTORY-COMMITS[ \t]*(\d+)", re.MULTILINE)
COMMIT_LINE_RE = re.compile(r"^[0-9a-f]{7,40} ")
DIFFSTAT_RE = re.compile(
    r"^ (\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?$",
    re.MULTILINE,
)
USAGE_RE = re.compile(r"^usage:[ \t]*(.+)$", re.MULTILINE)
NOTES_RE = re.compile(r"^FACTORY-NOTES(?:[ \t]+(.*))?$", re.MULTILINE)
SEAT_UNIT_RE = re.compile(
    r"^seat: unit seat@([0-9]{8}-[0-9]{6}-[0-9a-f]{6})$", re.MULTILINE
)
SUBMIT_FAILED_RE = re.compile(r"^seat: submit failed", re.MULTILINE)
ROUTE_IMPL_RE = re.compile(r"^(?:implement|codex)/(code|docs)/(XS|S|M|L)$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
CHECK_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")

STATUS_WORDS = ("done", "partial", "failed", "skipped", "unreported")
EFFORTS = ("off", "low", "medium", "high", "xhigh")
CHECK_VERDICTS = ("pass", "fail", "not-run")
# The driver's five verification verdicts (SH4), distinct from the seat's
# three-word CHECK_VERDICTS grammar above.
VERIFIED_VERDICTS = (
    "pass",
    "fail",
    "not-run:absent",
    "not-run:cache-miss",
    "not-run:verify-timeout",
)
MAX_CHECK_TOKENS = 64
# The driver's probe name shape and five-arm probe verdict enum (SH5).
PROBE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
PROBE_VERDICTS = ("pass", "fail", "missing", "not-run", "drift")
MAX_PROBE_TOKENS = 32


class OutsideRoot(Exception):
    """A path resolved outside the declared runs root."""

    def __init__(self, path, root):
        super().__init__(path)
        self.path = path
        self.root = root


def _field(text, pattern):
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else None


def _as_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _forbidden_check_name(name):
    return name.lower().replace("-", "_") in streams.FORBIDDEN


def _route_fields(route_line):
    """(route, task_kind, size) from a ``route:`` line's value."""
    if route_line is None:
        return "unknown", "unknown", "unknown"
    if route_line == "explicit":
        return "explicit", "unknown", "unknown"
    m = ROUTE_IMPL_RE.fullmatch(route_line)
    if m:
        return route_line, m.group(1), m.group(2)
    return "unknown", "unknown", "unknown"


def _commits_count(text):
    """Lines between the ``commits (base..task/<key>):`` header and the next
    blank line that match the ``git log --oneline`` shape."""
    for i, line in enumerate(text.splitlines()):
        if line.startswith("commits ("):
            n = 0
            for nxt in text.splitlines()[i + 1 :]:
                if nxt.strip() == "":
                    break
                if COMMIT_LINE_RE.match(nxt):
                    n += 1
            return n
    return 0


def _parse_checks(line_body):
    """(map, parse) from the FACTORY-CHECKS token string (body after the label).

    Returns ``({}, "refused")`` on any violation, ``({}, "missing")`` when the
    label is absent, else the map and ``"ok"``.
    """
    if line_body is None:
        return {}, "missing"
    tokens = line_body.split()
    if not tokens or len(tokens) > MAX_CHECK_TOKENS:
        return {}, "refused"
    out = {}
    for token in tokens:
        name, sep, verdict = token.partition("=")
        if not sep or "=" in verdict:
            return {}, "refused"
        if not CHECK_NAME_RE.fullmatch(name) or verdict not in CHECK_VERDICTS:
            return {}, "refused"
        if _forbidden_check_name(name):
            return {}, "refused"
        out[name] = verdict
    return out, "ok"


def _parse_verified(line_body):
    """The ``checks_verified:`` map, or ``None`` on any violation (a bare
    token, an over-cap list, an unknown name, a seat-grammar verdict, or a
    forbidden name). A violation yields ``None`` — never a partial map."""
    if line_body is None:
        return None
    tokens = line_body.split()
    if not tokens or len(tokens) > MAX_CHECK_TOKENS:
        return None
    out = {}
    for token in tokens:
        name, sep, verdict = token.partition("=")
        if not sep or "=" in verdict:
            return None
        if not CHECK_NAME_RE.fullmatch(name) or verdict not in VERIFIED_VERDICTS:
            return None
        if _forbidden_check_name(name):
            return None
        out[name] = verdict
    return out


def _parse_probes_verified(line_body):
    """The ``probes_verified:`` map, or ``None`` on any violation (a bare token,
    an over-cap list, a malformed name, a verdict outside the five-arm enum, or
    a forbidden name) — never a partial map."""
    if line_body is None:
        return None
    tokens = line_body.split()
    if not tokens or len(tokens) > MAX_PROBE_TOKENS:
        return None
    out = {}
    for token in tokens:
        name, sep, verdict = token.partition("=")
        if not sep or "=" in verdict:
            return None
        if not PROBE_NAME_RE.fullmatch(name) or verdict not in PROBE_VERDICTS:
            return None
        if _forbidden_check_name(name):
            return None
        out[name] = verdict
    return out


def _diffstat(text):
    m = DIFFSTAT_RE.search(text)
    if not m:
        return 0, 0, 0
    return int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0)


def _usage(text):
    usage = {
        "in": 0,
        "out": 0,
        "cache_read": 0,
        "reasoning": 0,
        "events": 0,
        "duration_s": None,
    }
    m = USAGE_RE.search(text)
    if not m:
        return usage
    try:
        raw = json.loads(m.group(1))
    except (json.JSONDecodeError, ValueError):
        return usage
    if not isinstance(raw, dict):
        return usage
    for src, dst in (
        ("input", "in"),
        ("output", "out"),
        ("cacheRead", "cache_read"),
        ("reasoning", "reasoning"),
        ("events", "events"),
    ):
        v = raw.get(src)
        if isinstance(v, int) and not isinstance(v, bool):
            usage[dst] = v
    v = raw.get("duration_s")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        usage["duration_s"] = v
    return usage


def _notes_body(text):
    ms = list(NOTES_RE.finditer(text))
    if not ms:
        return None
    body = ms[-1].group(1)
    return body.strip() if body is not None else None


def _plan_field(plan_line):
    if plan_line is None:
        return None
    if "/docs/superpowers/plans/" in plan_line:
        return "docs/superpowers/plans/" + os.path.basename(plan_line)
    return None


def _mtime_ts(path):
    mtime = os.path.getmtime(path)
    return datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def fallback_error_class(fields):
    """The metadata-only error class, used when the file carries no
    ``error_class:`` line. The log beside the result is never read."""
    if fields["submit_failed"]:
        return "submit-failed"
    if fields["exit_code"] == 124:
        return "timeout"
    notes = fields.get("notes_body")
    if notes:
        if notes.startswith(
            (
                "result-misparse:",
                "the seat produced no usable FACTORY-RESULT line",
            )
        ):
            return "no-result-line"
        if notes in (
            "status=done but the branch has no commits",
            "a bare result was echoed, not a real completion",
        ):
            return "template-echo"
    if fields["status"] == "done" and fields["commits"] == 0:
        return "template-echo"
    if (
        (fields.get("wall_s") or 0) < 10
        and (fields.get("events") or 0) < 50
        and fields["status"] != "done"
    ):
        return "boot-failure"
    return "none"


def parse_result(text, path, runs_root):
    """One ``task-result`` row from a ``.result`` file's text, or ``None`` when
    the file is not a result (no ``FACTORY-RESULT status=`` line, or no
    ``run:``/``key:`` line). ``path`` is the file's real path; ``runs_root`` is
    the fence root already enforced by the caller."""
    status_matches = list(STATUS_RE.finditer(text))
    if not status_matches:
        return None
    run = _field(text, r"^run:[ \t]*(.+)$")
    key = _field(text, r"^key:[ \t]*(.+)$")
    if run is None or key is None:
        return None
    status_word = status_matches[-1].group(1)
    status = status_word if status_word in STATUS_WORDS else "unknown"

    route_line = _field(text, r"^route:[ \t]*(.+)$")
    route, task_kind, size = _route_fields(route_line)

    workspace = _field(text, r"^workspace:[ \t]*(.+)$")
    repo = tasks._repo_from_workspace(workspace) if workspace else None

    exit_code = _as_int(_field(text, r"^exit_code:[ \t]*(.+)$"))
    wall_s = _as_int(_field(text, r"^wall_s:[ \t]*(.+)$"))
    commits = _commits_count(text)

    checks_line = _checks_line(text)
    checks, checks_parse = _parse_checks(checks_line)

    usage = _usage(text)
    notes_body = _notes_body(text)
    submit_failed = bool(SUBMIT_FAILED_RE.search(text))

    error_class_line = _field(text, r"^error_class:[ \t]*(.+)$")
    if error_class_line is not None:
        error_class = error_class_line
    else:
        error_class = fallback_error_class(
            {
                "submit_failed": submit_failed,
                "exit_code": exit_code,
                "status": status,
                "notes_body": notes_body,
                "commits": commits,
                "wall_s": wall_s,
                "events": usage["events"],
            }
        )

    seat_unit = None
    m = SEAT_UNIT_RE.search(text)
    if m:
        seat_unit = m.group(1)

    commits_declared = None
    m = re.search(COMMITS_RE, text)
    if m:
        commits_declared = int(m.group(1))

    touches_extra = _as_int(_field(text, r"^touches_extra:[ \t]*(.+)$"))
    touches_disclosed = _as_int(_field(text, r"^touches_disclosed:[ \t]*(.+)$"))

    checks_verified = _parse_verified(_field(text, r"^checks_verified:[ \t]*(.+)$"))
    checks_scope_line = _field(text, r"^checks_scope:[ \t]*(.+)$")
    checks_scope = (
        checks_scope_line if checks_scope_line in ("clean", "dirty") else None
    )
    checks_scope_files = _as_int(_field(text, r"^checks_scope_files:[ \t]*(.+)$"))
    verify_s = _as_int(_field(text, r"^verify_s:[ \t]*(.+)$"))
    probes_verified = _parse_probes_verified(
        _field(text, r"^probes_verified:[ \t]*(.+)$")
    )

    # `derived` labels which result lines the driver derived itself (an
    # unreported block): the whitespace tokens of the `derived:` line, passed
    # through as a list. The fence refuses an arm outside its enum and the row
    # is then counted refused; no line -> None.
    derived = None
    derived_line = _field(text, r"^derived:[ \t]*(.+)$")
    if derived_line is not None:
        derived = derived_line.split()

    files_changed, insertions, deletions = _diffstat(text)

    head = _field(text, r"^head:[ \t]*(.+)$")
    base = _field(text, r"^base:[ \t]*(.+)$")
    head = head if head and REV_RE.fullmatch(head) else None
    base = base if base and REV_RE.fullmatch(base) else None

    effort = _field(text, r"^effort:[ \t]*(.+)$")
    effort = effort if effort in EFFORTS else "unknown"

    result_path = os.path.realpath(path)

    return {
        "kind": "task-result",
        "run_id": run,
        "key": key,
        "repo": repo,
        "plan": _plan_field(_field(text, r"^plan:[ \t]*(.+)$")),
        "task_kind": task_kind,
        "size": size,
        "model": _field(text, r"^model:[ \t]*(.+)$"),
        "effort": effort,
        "route": route,
        "status": status,
        "exit_code": exit_code,
        "wall_s": wall_s,
        "commits": commits,
        "commits_declared": commits_declared,
        "checks": checks,
        "checks_parse": checks_parse,
        "derived": derived,
        "head": head,
        "base": base,
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
        "touches_extra": touches_extra,
        "touches_disclosed": touches_disclosed,
        "checks_verified": checks_verified,
        "checks_scope": checks_scope,
        "checks_scope_files": checks_scope_files,
        "verify_s": verify_s,
        "probes_verified": probes_verified,
        "usage": usage,
        "error_class": error_class,
        "seat_unit": seat_unit,
        "result_path": result_path,
        "result_mtime": _mtime_ts(path),
    }


def _checks_line(text):
    """The FACTORY-CHECKS label's body (the token string), or ``None`` when the
    label is absent. A bare ``FACTORY-CHECKS`` line yields the empty string."""
    m = re.search(r"^FACTORY-CHECKS(?:[ \t]+(.+))?$", text, re.MULTILINE)
    if not m:
        return None
    return m.group(1) or ""


def ingest(store, paths, runs_root):
    """Fence every path to the runs root, then write one row per valid result.
    Returns ``(n, refused)``; raises ``OutsideRoot`` before any write when a
    path is outside the root."""
    real_root = os.path.realpath(runs_root)
    real_paths = []
    for p in paths:
        rp = os.path.realpath(p)
        if rp != real_root and not rp.startswith(real_root + os.sep):
            raise OutsideRoot(p, runs_root)
        real_paths.append((p, rp))

    rows = []
    refused = 0
    for p, rp in real_paths:
        try:
            text = pathlib.Path(rp).read_text()
        except OSError:
            print(f"evidence: ingest result: {p}: not a result file", file=sys.stderr)
            refused += 1
            continue
        row = parse_result(text, rp, runs_root)
        if row is None:
            print(f"evidence: ingest result: {p}: not a result file", file=sys.stderr)
            refused += 1
            continue
        errors = streams.validate("task-result", row)
        if errors:
            for reason in errors:
                print(f"evidence: ingest result: {p}: {reason}", file=sys.stderr)
            refused += 1
            continue
        rows.append(row)

    if rows:
        evidence.replace_stream(store, "derived/tasks", rows)
    return len(rows), refused


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = argparse.ArgumentParser(prog="evidence ingest")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    )
    sub = parser.add_subparsers(dest="command")
    rp = sub.add_parser("result", help="ingest .result files into derived/tasks")
    rp.add_argument("--runs-root", default=os.path.expanduser("~/factory/runs"))
    rp.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    if args.command != "result":
        parser.error("a command is required (result)")
    runs_root = os.path.expanduser(args.runs_root)
    try:
        n, refused = ingest(args.store, args.paths, runs_root)
    except OutsideRoot as exc:
        print(
            f"evidence: ingest result: {exc.path} is outside {exc.root}",
            file=sys.stderr,
        )
        return 2
    print(f"ingested {n} rows into derived/tasks ({refused} refused)")
    return 0 if refused == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
