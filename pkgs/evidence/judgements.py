"""Plan-judgement ingest: a field allowlist that refuses free text (plan 2026-09-06-planning-agent, P6).

A judgement file is ``docs/reviews/plan-judgements/<date>-<name>.md``: line 1
``---``, then one ``key: value`` per line, then a closing ``---``, prose after.
The block may hold only the 14 allowlisted fields, every string value ≤ 200
bytes, and each value must match its class; the prose is never read, so a
body, an erratum, a reason or a note cannot ride a field into the stream.
``ingest judgements <repo>`` appends one row per ``(plan, revision)`` to the
``plans`` stream; ``validate_judgement(fields) -> list[str]`` is the fence.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import subprocess
import sys

import evidence

MAX_BYTES = 200
PLAN_PATH_RE = re.compile(r"^docs/[A-Za-z0-9._/-]{1,190}$")
JUDGEMENT_PATH_RE = re.compile(
    r"^docs/reviews/plan-judgements/[A-Za-z0-9._-]{1,150}\.md$"
)
AUTHOR_RE = re.compile(r"^(fable|hand|dsh:[a-z0-9./-]{1,64})$")
EFFORTS = {"off", "low", "medium", "high", "xhigh", "max", "unknown"}
DECISIONS = {"dispatch", "revise", "revise-exhausted", "panel-short"}
JUDGES = {"sonnet", "opus", "deepseek", "fable"}
DROPPED = {"implementer", "reviewer", "whole"}
FIELDS = (
    "plan",
    "spec",
    "author",
    "effort",
    "words",
    "tasks",
    "judges",
    "judges_dropped",
    "scores",
    "total",
    "self_score",
    "threshold",
    "decision",
    "revision",
)
# The assembled row `validate_judgement` sees: the 14 fields plus the transport
# fields the ingest adds before appending.
ROW_KEYS = set(FIELDS) | {"kind", "judged_ts", "judgement_path"}


class DuplicateKey(Exception):
    """A front-matter key appeared twice in one block."""

    def __init__(self, key):
        super().__init__(key)
        self.key = key


def run(argv, timeout=20.0):
    """The subprocess seam (mirrors the sibling modules)."""
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_list(value):
    """``[a, b, c]`` -> ``["a", "b", "c"]``, ``[]`` -> ``[]``, else None."""
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [t.strip() for t in inner.split(",")]


def parse_front_matter(text):
    """The block's fields as a str->str dict, or None when there is no block.
    Raises `DuplicateKey` when a key appears twice in one block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if not line.strip():
            continue
        if ":" not in line:
            return None  # a malformed line inside the block is not a block
        key, _, value = line.partition(":")
        key = key.strip()
        if key in fields:
            raise DuplicateKey(key)
        fields[key] = value.strip()
    return None  # opened fence, never closed


def _path_ok(value):
    """A repo-relative `plan`/`spec` path: rooted under `docs/`, no `..` segment."""
    return (
        isinstance(value, str)
        and PLAN_PATH_RE.match(value)
        and all(seg != ".." for seg in value.split("/"))
    )


def validate_judgement(fields):
    """Every reason the row is refused; [] means it ingests. `fields` is the
    assembled row: the raw str->str block fields plus `kind`, `judged_ts` and
    `judgement_path`, so no field can bypass the fence."""
    errors = []

    # the fence: only the allowlisted names may appear at all.
    for key in fields:
        if key not in ROW_KEYS:
            errors.append(f"unknown field {key}")

    # every string value is bounded, so free text cannot ride in a field.
    for key, value in fields.items():
        if isinstance(value, str):
            n = len(value.encode("utf-8"))
            if n > MAX_BYTES:
                errors.append(f"{key}: {n} bytes (limit {MAX_BYTES})")

    for key in FIELDS:
        if key not in fields:
            errors.append(f"missing {key}")

    for key in ("plan", "spec"):
        value = fields.get(key)
        if value is not None and not _path_ok(value):
            errors.append(f"{key}: invalid path")

    value = fields.get("judgement_path")
    if value is not None and (
        not isinstance(value, str) or not JUDGEMENT_PATH_RE.match(value)
    ):
        errors.append("judgement_path: invalid path")

    value = fields.get("author")
    if value is not None and (not isinstance(value, str) or not AUTHOR_RE.match(value)):
        errors.append("author: invalid (fable | hand | dsh:<model>)")

    value = fields.get("effort")
    if value is not None and value not in EFFORTS:
        errors.append("effort: invalid (off|low|medium|high|xhigh|max|unknown)")

    for key in ("words", "tasks", "revision"):
        value = fields.get(key)
        n = _as_int(value)
        if value is not None and (n is None or n < 0):
            errors.append(f"{key}: invalid integer (>= 0)")

    for key in ("threshold", "total"):
        value = fields.get(key)
        if value is not None and _as_int(value) is None:
            errors.append(f"{key}: invalid integer")

    value = fields.get("self_score")
    if value is not None and value != "null":
        n = _as_int(value)
        if n is None or not 0 <= n <= 42:
            errors.append("self_score: invalid (0-42 or null)")

    value = fields.get("decision")
    if value is not None and value not in DECISIONS:
        errors.append(
            "decision: invalid (dispatch|revise|revise-exhausted|panel-short)"
        )

    value = fields.get("judges")
    if value is not None:
        ls = parse_list(value)
        if ls is None or len(ls) > 3 or any(j not in JUDGES for j in ls):
            errors.append("judges: invalid (0-3 of sonnet|opus|deepseek|fable)")

    value = fields.get("judges_dropped")
    if value is not None:
        ls = parse_list(value)
        if ls is None or any(j not in DROPPED for j in ls):
            errors.append("judges_dropped: invalid (implementer|reviewer|whole)")

    scores = None
    value = fields.get("scores")
    if value is not None:
        ls = parse_list(value)
        if ls is None:
            errors.append("scores: invalid list")
        elif len(ls) != 14:
            errors.append(f"scores: must be exactly 14 entries (got {len(ls)})")
        else:
            vals = []
            for t in ls:
                n = _as_int(t)
                if n is None or not 0 <= n <= 3:
                    vals = None
                    break
                vals.append(n)
            if vals is None:
                errors.append("scores: entries must be integers 0-3")
            else:
                scores = vals

    total = fields.get("total")
    if total is not None and scores is not None:
        tn = _as_int(total)
        if tn is not None and tn != sum(scores):
            errors.append(f"total {tn} does not equal scores sum {sum(scores)}")

    return errors


def _row_fields(fields):
    """The 14 typed fields, assuming `validate_judgement(fields) == []`."""
    out = {}
    for key in ("plan", "spec", "author", "effort", "decision"):
        out[key] = fields[key]
    for key in ("words", "tasks", "threshold", "revision", "total"):
        out[key] = int(fields[key])
    out["self_score"] = (
        None if fields["self_score"] == "null" else int(fields["self_score"])
    )
    out["judges"] = parse_list(fields["judges"])
    out["judges_dropped"] = parse_list(fields["judges_dropped"])
    out["scores"] = [int(t) for t in parse_list(fields["scores"])]
    return out


def judged_ts(repo, rel_path):
    """The file's first git commit time in RFC3339 Z, or its mtime when git says
    nothing (the file is uncommitted or the tree is not a repository)."""
    try:
        cp = run(
            [
                "git",
                "-C",
                repo,
                "log",
                "--diff-filter=A",
                "--format=%cI",
                "--",
                rel_path,
            ]
        )
    except (OSError, subprocess.SubprocessError):
        cp = None
    if cp is not None and cp.returncode == 0 and cp.stdout.strip():
        return cp.stdout.strip().splitlines()[-1]
    mtime = os.path.getmtime(os.path.join(repo, rel_path))
    return datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def ingest_judgements(store, repo):
    """Ingest every judgement file under `<repo>/docs/reviews/plan-judgements/`,
    appending one `plans` row per `(plan, revision)`. Returns 1 when any file is
    refused, 0 otherwise (a missing directory is 0)."""
    repo_arg = str(repo)
    repo = pathlib.Path(repo)
    jdir = repo / "docs" / "reviews" / "plan-judgements"
    if not jdir.is_dir():
        print(f"no judgements under {repo_arg}")
        return 0
    existing = {
        (r.get("plan"), r.get("revision"))
        for r in evidence.read(store, "plans")
        if r.get("kind") == "plan-judgement"
    }
    failed = False
    for path in sorted(jdir.glob("*.md")):
        rel = path.relative_to(repo).as_posix()
        try:
            text = path.read_text()
        except OSError:
            continue
        try:
            fields = parse_front_matter(text)
        except DuplicateKey as dup:
            print(f"refused {rel}: duplicate key {dup.key}", file=sys.stderr)
            failed = True
            continue
        if fields is None:
            print(f"refused {rel}: no front-matter block", file=sys.stderr)
            failed = True
            continue
        judged = judged_ts(str(repo), rel)
        row = {
            "kind": "plan-judgement",
            **fields,
            "judged_ts": judged,
            "judgement_path": rel,
        }
        errors = validate_judgement(row)
        if errors:
            print(f"refused {rel}: {'; '.join(errors)}", file=sys.stderr)
            failed = True
            continue
        row_fields = _row_fields(fields)
        key = (row_fields["plan"], row_fields["revision"])
        if key in existing:
            print(f"skipped {rel} (present)")
            continue
        evidence.append(
            store,
            "plans",
            {
                "kind": "plan-judgement",
                **row_fields,
                "judged_ts": judged,
                "judgement_path": rel,
            },
        )
        existing.add(key)
        print(f"ingested {rel}")
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="judgements")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE", "/var/lib/evidence")
    )
    parser.add_argument(
        "--fields",
        action="store_true",
        help="print the 14 allowlisted field names, one per line",
    )
    sub = parser.add_subparsers(dest="command")
    jp = sub.add_parser(
        "judgements", help="ingest plan-judgement files into the plans stream"
    )
    jp.add_argument("repo")
    args = parser.parse_args(argv)
    if args.fields:
        for name in FIELDS:
            print(name)
        return 0
    if args.command != "judgements":
        parser.error("a command is required (judgements), or --fields")
    return ingest_judgements(args.store, args.repo)


if __name__ == "__main__":
    raise SystemExit(main())
