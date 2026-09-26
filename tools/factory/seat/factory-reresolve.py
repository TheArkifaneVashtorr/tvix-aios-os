#!/usr/bin/env python3
"""factory-reresolve.py -- the mechanical re-resolver node (FA18, decision 27c).

Before any paid gate, re-run every claim in an artifact against the checkout,
with no model and no network: each claim's ``citation`` must name a file under
``--repo`` with its ``path:line`` (or ``path:A-B``) range inside ``wc -l``,
each claim's ``command`` must exit 0 (run with ``subprocess.run(shell=True,
cwd=<repo>, capture_output=True, timeout=...)``), and every backticked literal
in the claim's ``text`` must occur within the cited range. A claim whose
``text`` carries no backticked literal is held or broken by its command alone.

The input must first pass ``factory-artifact.py check``; anything it refuses is
refused here too (exit 2). The output is a ``reresolve`` artifact: the same
claims, whose ``errata`` holds exactly one entry per claim -- ``held:<i>`` for
a claim that reproduces, ``broken:<i>: <reason>`` otherwise, the reason one of
``missing file``, ``line out of range``, ``command exit <N>``,
``literal not on cited line`` or ``timeout`` -- with ``repro`` copied through
and ``verdict`` ``ok`` when every claim held else ``broken``. Exit 0 either
way; a per-command timeout (default 60 s) marks that claim ``timeout`` rather
than aborting the run.
"""

import argparse
import json
import os
import re
import subprocess
import sys

SEAT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(SEAT_DIR, "factory-artifact.py")

CITATION_RE = re.compile(r"^([^:\s]+):(\d+)(?:-(\d+))?$")
BACKTICK_RE = re.compile(r"`([^`]+)`")


def _run_check(artifact):
    res = subprocess.run(
        [sys.executable, CHECKER, "check", artifact],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        sys.stderr.write(res.stdout)
        if res.stderr:
            sys.stderr.write(res.stderr)
        sys.exit(2)


def _count_lines(path):
    with open(path, "rb") as fh:
        return fh.read().count(b"\n")


def _read_lines(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read().splitlines()


def _resolve_claim(claim, repo, timeout):
    """Return None when the claim is held, else the broken reason."""
    citation = claim.get("citation", "")
    command = claim.get("command", "")

    start = end = None
    cited = None
    if citation:
        match = CITATION_RE.match(citation)
        if not match:
            return "missing citation"  # unreachable: `check` already refused it
        cited = match.group(1)
        start = int(match.group(2))
        end = int(match.group(3)) if match.group(3) else start
        path = os.path.join(repo, cited)
        if not os.path.isfile(path):
            return "missing file"
        total = _count_lines(path)
        if start < 1 or start > end or end > total:
            return "line out of range"

    try:
        res = subprocess.run(
            command,
            shell=True,
            cwd=repo,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "timeout"

    if res.returncode != 0:
        return f"command exit {res.returncode}"

    if cited is not None:
        lines = _read_lines(os.path.join(repo, cited))[start - 1 : end]
        joined = "\n".join(lines)
        for literal in BACKTICK_RE.findall(claim.get("text", "")):
            if literal not in joined:
                return "literal not on cited line"

    return None


def main(argv):
    parser = argparse.ArgumentParser(prog="factory-reresolve.py")
    parser.add_argument("artifact")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", default=None)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(argv)

    _run_check(args.artifact)

    with open(args.artifact, encoding="utf-8") as fh:
        doc = json.load(fh)

    claims = doc.get("claims") or []
    errata = []
    held = True
    for i, claim in enumerate(claims):
        reason = _resolve_claim(claim, args.repo, args.timeout)
        if reason is None:
            errata.append(f"held:{i}")
        else:
            held = False
            errata.append(f"broken:{i}: {reason}")

    out = dict(doc)
    out["kind"] = "reresolve"
    out["errata"] = errata
    out["verdict"] = "ok" if held else "broken"

    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
