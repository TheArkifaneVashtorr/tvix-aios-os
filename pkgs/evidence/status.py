"""status — the generated front-door page (plan 2026-09-11-evidence, EV13).

Python 3 stdlib only: this file runs beside evidence.py in the seat driver
and in dark-factory agents. `render_status` composes the whole page from the
facts evidence already holds — the bundle's live/HEAD/checks table, the
board's derived queue block, the claims tally and the open bug rows — so the
file it writes carries no prose of its own.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import sys
import tempfile

import evidence
import tasks
import tomllib


def _short(x):
    return (x or "none")[:12]


def _header_lines(bundle, repo_name):
    dirty = "dirty" if bundle["dirty"] else "clean"
    return [
        f"# Status — {repo_name}",
        "",
        (
            f"Generated {bundle['generated']}; "
            f"live {_short(bundle['live']['rev'])}; "
            f"HEAD {_short(bundle['head'])} — {dirty}."
        ),
    ]


def _checks_lines(bundle):
    """The bundle's checks table, byte-identical to `render_bundle_markdown`'s
    own section: slice from its `## Checks …` heading to the next `## `."""
    md = evidence.render_bundle_markdown(bundle)
    lines = md.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line == "## Checks covering HEAD and the live system":
            start = i
            break
    if start is None:
        return []
    out = []
    for line in lines[start:]:
        if (
            line.startswith("## ")
            and line != "## Checks covering HEAD and the live system"
        ):
            break
        out.append(line)
    return out


def _queue_lines(graph):
    block = tasks.render_board_block(graph).rstrip("\n")
    lines = ["## Queue", "", "<!-- tasks:begin -->"]
    if block:
        lines.extend(block.split("\n"))
    lines.append("<!-- tasks:end -->")
    return lines


def _claims_lines(bundle):
    c = bundle["claims"]
    lines = [
        "## Claims",
        "",
        f"**verified: {c['verified']}, parked: {c['parked']}, gaps: {len(c['gaps'])}**",
    ]
    lines.extend(f"- {g['id']}" for g in c["gaps"])
    return lines


def _bugs_lines(bugs_rows):
    lines = ["## Open bugs", ""]
    if bugs_rows is None:
        lines.append("_(no bug ledger)_")
        return lines
    for b in bugs_rows:
        if b.get("status") != "open":
            continue
        bid = b.get("id", "?")
        task = b.get("task") or ""
        lines.append(f"{bid} — {task}" if task else f"{bid} — (untyped)")
    return lines


def render_status(bundle, graph, bugs_rows, today) -> str:
    """The whole front-door page. `bugs_rows` is the parsed `[[bug]]` list, or
    `None` when the ledger is absent (the `_(no bug ledger)_` placeholder).
    `today` is accepted for callers that compute staleness themselves; the
    bundle already carries the generated timestamp and the claims' stale flags,
    so nothing here re-derives a date."""
    repos = graph.get("repos") or []
    repo_name = repos[0].get("name") if repos and repos[0].get("name") else "repo"
    parts = []
    parts += _header_lines(bundle, repo_name)
    parts += _checks_lines(bundle)
    parts += _queue_lines(graph)
    parts += _claims_lines(bundle)
    parts += _bugs_lines(bugs_rows)
    return "\n".join(parts) + "\n"


def _load_bugs(path):
    if not pathlib.Path(path).is_file():
        return None
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh).get("bug", [])
    except tomllib.TOMLDecodeError:
        return []


def _write_atomic(path, content):
    d = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(d):
        print(f"status: no such directory {d}", file=sys.stderr)
        return 1
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".status-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = argparse.ArgumentParser(prog="evidence status")
    parser.add_argument("--out", required=True, help="the page file to write")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--claims", default=None)
    parser.add_argument("--sibling", action="append", default=None)
    parser.add_argument("--bugs", default=None)
    parser.add_argument(
        "--nixos-version-bin", default="/run/current-system/sw/bin/nixos-version"
    )
    args = parser.parse_args(argv)

    claims = args.claims or os.path.join(args.repo, "docs", "ledger", "claims.toml")
    siblings = args.sibling if args.sibling is not None else evidence.default_siblings()
    bundle = evidence.bundle(
        args.store, args.repo, claims, siblings, args.nixos_version_bin
    )
    graph = tasks.board_graph(args.repo)
    bugs_path = args.bugs or os.path.join(args.repo, "docs", "ledger", "bugs.toml")
    today = datetime.datetime.now(datetime.timezone.utc).date()
    page = render_status(bundle, graph, _load_bugs(bugs_path), today)
    return _write_atomic(args.out, page)


if __name__ == "__main__":
    sys.exit(main())
