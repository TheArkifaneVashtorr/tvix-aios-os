"""claims — validate docs/ledger/claims.toml, the claims file (plan 2026-09-05-evidence-store, E2).

A claim is verified only by a named check at a revision (check:<name>@<rev>) or an
operator-judged drill (operator:<date>) with an evidence class; a gap names its
owner, a review date and what closes it; a parked claim names its decision.
Structure is checked in the flake (no clock in the sandbox); staleness (--today)
in the pre-commit hook and by `evidence bundle`, where a real clock exists.
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import sys

import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evidence import CLASSES

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
EVIDENCE_RE = re.compile(
    r"^(check:[a-z][a-z0-9-]{0,31}@[0-9a-f]{7,40}\b|operator:\d{4}-\d{2}-\d{2}\b)"
)
STATUSES = ("verified", "gap", "parked")


def load(path, repo_root=None) -> list[dict]:
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("claim", [])


def validate(
    rows: list[dict], today: datetime.date | None = None, repo_root=None
) -> list[str]:
    errs: list[str] = []
    seen: set[str] = set()
    root = pathlib.Path(repo_root) if repo_root else None
    for r in rows:
        cid = str(r.get("id", "<no id>"))

        def say(msg, cid=cid):
            errs.append(f"claims: {cid}: {msg}")

        if not ID_RE.match(cid):
            say("id must match ^[a-z0-9][a-z0-9-]{2,63}$")
        if cid in seen:
            say("duplicate id")
        seen.add(cid)
        for key in ("text", "status", "class", "owner", "opened"):
            if key not in r:
                say(f"missing {key}")
        status = r.get("status")
        if status not in STATUSES:
            say(f"status must be one of {', '.join(STATUSES)}")
        if r.get("class") not in CLASSES:
            say(f"class must be one of {', '.join(CLASSES)}")
        if not isinstance(r.get("opened"), datetime.date):
            say("opened must be a TOML date")
        if status == "verified":
            ev = r.get("evidence")
            if not ev:
                say(
                    "verified claim needs evidence (check:<name>@<rev> … or operator:<date> …)"
                )
            elif not EVIDENCE_RE.match(str(ev)):
                say(
                    f"evidence must start with 'check:<name>@<rev>' or 'operator:<date>', got {ev!r}"
                )
            if r.get("class") == "unmeasured":
                say("verified claim cannot have class unmeasured")
        if status == "gap":
            for key in ("owner", "review_by", "closes_by"):
                if not r.get(key):
                    say(f"gap needs {key}")
            rb = r.get("review_by")
            if rb is not None and not isinstance(rb, datetime.date):
                say("review_by must be a TOML date")
            if today is not None and isinstance(rb, datetime.date) and rb < today:
                say(
                    f"gap past review_by {rb} (today {today}) — extend it with a reason or close it"
                )
        if status == "parked":
            dec = r.get("decision")
            if not dec:
                say("parked claim needs decision")
            elif root is not None and not (root / dec).exists():
                say(f"decision file does not exist: {dec}")
    return errs


def open_gaps(rows: list[dict]) -> list[dict]:
    return sorted(
        (r for r in rows if r.get("status") == "gap"),
        key=lambda r: (r.get("opened"), r.get("id")),
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="claims")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("file")
    v.add_argument("--today", help="YYYY-MM-DD; enables the staleness rule")
    v.add_argument("--repo-root", default=None)
    a = p.parse_args(argv)
    root = a.repo_root or str(pathlib.Path(a.file).resolve().parents[2])
    today = datetime.date.fromisoformat(a.today) if a.today else None
    errs = validate(load(a.file, repo_root=root), today=today, repo_root=root)
    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
