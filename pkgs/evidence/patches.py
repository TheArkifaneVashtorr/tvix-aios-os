"""patches — validate docs/ledger/patches.toml, the patch series ledger (decisions 46a/47a).

A [[patch]] row names one patch in the tree — its `file` (under
patches/<pkg>/NNNN-name.patch), the derivation attribute it applies to
(`package`), why it exists, its upstream state, and the dates that bound its
review. Structure is checked in the flake (no clock in the sandbox); the
`review_by` staleness rule runs with `--today`, where a real clock exists.

The validator never fetches or unpacks source on its own: a package's apply
recipe (`patches/<pkg>/unpack.sh`) is registered by the package that owns the
series (the Platform plan). A row whose package has no recipe is refused as
`no apply recipe for <pkg>`, so the first real row cannot land before the
Platform series lands the unpack step.
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import sys

import tomllib

FIELDS = ("file", "package", "reason", "upstream", "added", "review_by", "added_in")
UPSTREAMS = ("local", "submitted", "merged", "rejected")
NUM_RE = re.compile(r"^(\d{4})-")


def load(path) -> list[dict]:
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return data.get("patch", [])


def unpack_recipe(root: pathlib.Path, package: str) -> pathlib.Path | None:
    p = root / "patches" / package / "unpack.sh"
    return p if p.is_file() else None


def validate(rows, today=None, root=None) -> list[str]:
    errs: list[str] = []
    seen: dict[str, set[str]] = {}
    rroot = pathlib.Path(root) if root else None
    for r in rows:
        pkg = str(r.get("package", "<no package>"))

        def say(msg, pkg=pkg):
            errs.append(f"patches: {pkg}: {msg}")

        for key in FIELDS:
            if key not in r:
                say(f"missing {key}")
        if r.get("upstream") not in UPSTREAMS:
            say(f"upstream must be one of {', '.join(UPSTREAMS)}")
        if not isinstance(r.get("added"), datetime.date):
            say("added must be a TOML date")
        rb = r.get("review_by")
        if not isinstance(rb, datetime.date):
            say("review_by must be a TOML date")
        elif today is not None and rb < today:
            say(f"review_by {rb} is past --today {today}")
        if "package" in r and rroot is not None and unpack_recipe(rroot, pkg) is None:
            say(f"no apply recipe for {pkg}")
        filepath = r.get("file")
        if filepath:
            base = pathlib.Path(filepath).name
            m = NUM_RE.match(base)
            if not m:
                say(f"file basename must be numbered NNNN- (got {base!r})")
            else:
                num = m.group(1)
                if num in seen.setdefault(pkg, set()):
                    say(f"duplicate patch number {num}")
                seen[pkg].add(num)
            if rroot is not None and not (rroot / filepath).exists():
                say(f"file does not exist: {filepath}")
    return errs


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="patches")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("file")
    v.add_argument("--today", help="YYYY-MM-DD; enables the review_by staleness rule")
    v.add_argument("--root", default=None)
    a = p.parse_args(argv)
    root = a.root or str(pathlib.Path(a.file).resolve().parents[2])
    today = datetime.date.fromisoformat(a.today) if a.today else None
    errs = validate(load(a.file), today=today, root=root)
    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
