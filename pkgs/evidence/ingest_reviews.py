"""Reviews ingest (plan 2026-09-06-telemetry-store-1, T3).

``ingest reviews [--runs-root DIR] <repo> <runs-dir>`` writes one ``gate-verdict``
row per ``docs/reviews/*opus-review*.md`` (the completed block and the H1) and
per ``<runs-dir>/<run>/<KEY>.review.md`` (the seat's review log) into the
``derived/gates`` stream, keyed by ``review_path``. Only the block, the H1, the
file name, the file hash and ``git log`` are read; a review body never enters
the store.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import pathlib
import re
import subprocess
import sys

import evidence
import streams
import tasks

_VERDICT_RE = re.compile(r"^FACTORY-REVIEW verdict=(approve|rework|reject)$")
# The legacy name fallback: when a review's H1 does not match REVIEW_RE, its
# run_id/key come from a dated ``*opus-review-<run>-<key>.md`` basename.
_LEGACY_NAME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}-opus-review-(?P<run>[a-z0-9]+)-(?P<key>[A-Za-z0-9-]+)\.md$"
)
_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
_REPLAN_RE = re.compile(r"r(\d*)$")
_FIX_RE = re.compile(r"(?:(?<!\d)\d|r)[bcd]$")
_LETTER_W = {"b": 1, "c": 2, "d": 3}

DEFAULT_RUNS_ROOT = os.path.expanduser("~/factory/runs")


def round_of(key):
    """The D7 key tokeniser: ``(round_kind, round)``.

    Strip trailing round tokens repeatedly: a replan token ``r`` or ``r<n>``
    (weights 1 and n) and a fix letter b/c/d (weights 1/2/3) recognised only at
    the very end after a single digit or the letter ``r`` (so ``T10b`` keeps its
    base and stays first). replan dominates fix; ``round = 1 + sum(weights)``.
    """
    has_r = False
    has_fix = False
    total = 0
    s = key
    while s:
        m = _REPLAN_RE.search(s)
        if m is not None:
            has_r = True
            digits = m.group(1)
            total += int(digits) if digits else 1
            s = s[: m.start()]
            continue
        m = _FIX_RE.search(s)
        if m is not None:
            has_fix = True
            total += _LETTER_W[s[-1]]
            s = s[:-1]
            continue
        break
    if has_r:
        kind = "replan"
    elif has_fix:
        kind = "fix"
    else:
        kind = "first"
    return kind, 1 + total


def _utc_z(value):
    """A ``git %cI`` stamp rendered as a ``YYYY-MM-DDTHH:MM:SSZ`` ts."""
    if not value:
        return None
    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_count(raw):
    """A block count as an int, or None for ``null``/absent (never raises)."""
    if raw is None or raw == "null":
        return None
    if re.fullmatch(r"[0-9]+", raw) is None:
        return None
    return int(raw)


def _add_commit(repo, rel):
    """The earliest add commit of ``docs/reviews/<rel>`` as ``(sha, ts)``, or
    ``(None, None)`` when git has nothing to say."""
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "log",
            "--diff-filter=A",
            "--format=%H%x09%cI",
            "--",
            f"docs/reviews/{rel}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        return None, None
    sha, _, ts = lines[-1].partition("\t")
    return sha, _utc_z(ts)


def _base_row(key, run_id, reviewer, route, verdict):
    kind, n = round_of(key)
    return {
        "kind": "gate-verdict",
        "run_id": run_id,
        "key": key,
        "chain_root": tasks.chain_root(key),
        "round_kind": kind,
        "round": n,
        "reviewer": reviewer,
        "route": route,
        "model": None,
        "verdict": verdict,
        "majors": None,
        "minors": None,
        "mutants_total": None,
        "mutants_killed": None,
        "mutants_outside_named": None,
        "plan_defect": None,
        "plan_defect_secondary": None,
        "gate_tokens": None,
        "wall_s": None,
    }


def _doc_row(repo, name, lines, has_block, block, first, lookahead):
    """One gate-verdict row for a docs/reviews file (None when unidentified)."""
    m = tasks._review_h1(first, lookahead)
    if m is not None:
        verdict = m["verdict"].lower()
        run_id = m["run"]
        key = m["key"]
    else:
        lm = _LEGACY_NAME_RE.match(name)
        if lm is None:
            return None
        verdict = "unknown"
        run_id = lm.group("run")
        key = lm.group("key")
    reviewer = (
        block.get("reviewer") if (has_block and block.get("reviewer")) else "unknown"
    )
    row = _base_row(key, run_id, reviewer, "claude", verdict)
    if has_block:
        row["majors"] = _as_count(block.get("majors"))
        row["minors"] = _as_count(block.get("minors"))
        row["mutants_total"] = _as_count(block.get("mutants_total"))
        row["mutants_killed"] = _as_count(block.get("mutants_killed"))
        row["mutants_outside_named"] = _as_count(block.get("mutants_outside_named"))
        row["plan_defect"] = block.get("plan_defect")
        row["plan_defect_secondary"] = block.get("plan_defect_secondary")
        if block.get("model"):
            row["model"] = block["model"]
    row["review_path"] = f"docs/reviews/{name}"
    row["review_sha256"] = hashlib.sha256(
        (repo / "docs" / "reviews" / name).read_bytes()
    ).hexdigest()
    commit, ts = _add_commit(repo, name)
    row["review_commit"] = commit
    row["review_commit_ts"] = ts
    return row


def _seat_verdict(text):
    """The last ``FACTORY-REVIEW verdict=`` line; rework maps to rejected and a
    missing line reads as none."""
    last = None
    for ln in text.splitlines():
        m = _VERDICT_RE.match(ln)
        if m is not None:
            last = m.group(1)
    if last == "approve":
        return "approved"
    if last in ("reject", "rework"):
        return "rejected"
    return "none"


def _runs_under(root, runs_dir):
    rr = os.path.realpath(os.path.expanduser(root))
    rd = os.path.realpath(runs_dir)
    return rd == rr or rd.startswith(rr + os.sep)


def _build_rows(repo, runs_dir):
    """All gate rows and the ``(docs_total, h1, blocks, legacy, runs_total)``
    counts. A fence violation raises ``ValueError`` with the reason."""
    repo = pathlib.Path(repo)
    reviews_dir = repo / "docs" / "reviews"
    if not reviews_dir.is_dir():
        raise ValueError(f"no docs/reviews in {repo}")
    rows = []
    docs_total = h1 = blocks = legacy = 0
    for path in sorted(reviews_dir.glob("*opus-review*.md")):
        docs_total += 1
        lines = path.read_text().splitlines()
        has_block, block, first, lookahead = tasks._split_front_matter(lines)
        if tasks._review_h1(first, lookahead) is not None:
            h1 += 1
        elif _LEGACY_NAME_RE.match(path.name) is not None:
            legacy += 1
        if has_block:
            blocks += 1
        row = _doc_row(repo, path.name, lines, has_block, block, first, lookahead)
        if row is not None:
            rows.append(row)

    runs_total = 0
    runs_path = pathlib.Path(runs_dir)
    if runs_path.is_dir():
        for path in sorted(runs_path.glob("*/*.review.md")):
            run = path.parent.name
            key = path.stem.removesuffix(".review")
            if not _KEY_RE.fullmatch(run) or not _KEY_RE.fullmatch(key):
                continue
            runs_total += 1
            text = path.read_text()
            row = _base_row(key, run, "deepseek", "openrouter", _seat_verdict(text))
            row["review_path"] = f"~/factory/runs/{run}/{key}.review.md"
            row["review_sha256"] = hashlib.sha256(text.encode()).hexdigest()
            rows.append(row)

    return rows, (docs_total, h1, blocks, legacy, runs_total)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ingest-reviews")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    )
    sub = parser.add_subparsers(dest="command")
    rp = sub.add_parser("reviews", help="ingest review files into derived/gates")
    rp.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)
    rp.add_argument("repo")
    rp.add_argument("runs_dir")
    args = parser.parse_args(argv)
    if args.command != "reviews":
        parser.error("a command is required (reviews)")

    if not _runs_under(args.runs_root, args.runs_dir):
        print(
            f"refused: runs-dir {args.runs_dir} outside --runs-root {args.runs_root}",
            file=sys.stderr,
        )
        return 2
    try:
        rows, counts = _build_rows(args.repo, args.runs_dir)
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2

    if rows:
        try:
            evidence.replace_stream(args.store, "derived/gates", rows)
        except streams.StreamRefused as exc:
            for msg in exc.errors:
                print(f"refused: {msg}", file=sys.stderr)
            return 1

    docs_total, h1, blocks, legacy, runs_total = counts
    print(
        f"ingested {len(rows)} gate rows (docs/reviews: {docs_total}, "
        f"H1 parsed {h1}, blocks {blocks}, legacy {legacy}; runs: {runs_total})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
