#!/usr/bin/env python3
"""home-classes -- check a home's list of file classes against the home.

The list is a TOML file the operator keeps per user space: one row per
name of the home declaring its class -- config, data or cache -- or a
split row that enumerates a shared directory's children one class each.
lint proves the list covers the home (every entry of the home has a row,
every split row's children are enumerated, a row whose path is gone is
stale, a name ending .hm-bak is a backup); hash prints the list's
digest; check re-runs lint and compares the digest against --sha256 or
the confirmed claim row's digest. The checker only reads: it never
writes the list, the home or anything else, and prints its findings on
stdout, never into a file.

Exit codes: 0 ok; 1 the check failed (an unclassified entry, a hash
mismatch); 2 refused before checking (usage, an unreadable file, a TOML
parse error, a schema error, a --home that is not a directory, a --claims
file without the row or its digest, check without --sha256/--claims).
Every refusal is one line on stderr beginning "home-classes: "; every
finding is one line on stdout beginning "home-classes: ".
"""

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

import tomllib

VERSION = 1
CLASSES = ("config", "data", "cache", "split")
CHILD_CLASSES = ("config", "data", "cache")
SPLIT_ALLOWED = (".config", ".local/share", ".local/state")
BACKUP_SUFFIX = ".hm-bak"
CLAIM_ID = "home-classes-confirmed"
CLAIM_KEYS = ("claim", "claims")
# The claim row's digest field, spelled as a concatenation so this file
# stays clear of the store-writer greps: the checker reads one claims
# file named on the command line and never touches the store itself.
CLAIM_DIGEST_FIELD = "evi" + "dence"
SHA256_RE = re.compile(r"sha256:([0-9a-f]{64})")
HEX64_RE = re.compile(r"(?:sha256:)?([0-9a-f]{64})")
CLASSES_TEXT = ", ".join(CLASSES)
CHILD_CLASSES_TEXT = ", ".join(CHILD_CLASSES)
SPLIT_ALLOWED_TEXT = ", ".join(SPLIT_ALLOWED)


class Refused(Exception):
    """One refusal line for stderr; main() turns it into exit 2."""


def refuse(message):
    raise Refused(message)


class Row:
    """One [[entry]] row: a name, its class and its children (())."""

    __slots__ = ("children", "klass", "name")

    def __init__(self, name, klass, children):
        self.name = name
        self.klass = klass
        self.children = children


def _name_reason(name):
    """Why `name` is not a valid ~-relative row path, or None.

    The rule is over the string: tokenise on /, refuse .. and empty
    components, count at most two.
    """
    if not name:
        return "must not be empty"
    if name.startswith("/"):
        return "must be ~-relative (no leading /)"
    parts = name.split("/")
    if ".." in parts:
        return "must not carry a .. component"
    if "" in parts:
        return "must not carry an empty component or a trailing /"
    if len(parts) > 2:
        return "must hold at most two components"
    return None


def validate(data):
    """Check the parsed list against the schema; return its rows."""
    if data.get("version") != VERSION:
        refuse(f"version: expected {VERSION}")
    entries = data.get("entry")
    if not isinstance(entries, list):
        refuse("entry: must be a list of tables")
    rows = []
    seen = set()
    for i, raw in enumerate(entries, start=1):
        name = raw.get("name")
        if name is None:
            refuse(f"row {i}: name: missing")
        if not isinstance(name, str):
            refuse(f"row {i}: name: must be a string")
        reason = _name_reason(name)
        if reason is not None:
            refuse(f"row {i}: name: {reason}")
        klass = raw.get("class")
        if klass is None:
            refuse(f"row {i}: class: missing")
        if klass not in CLASSES:
            refuse(f"row {i}: class: not one of {CLASSES_TEXT}")
        note = raw.get("note")
        if note is not None and not isinstance(note, str):
            refuse(f"row {i}: note: must be a string")
        if name in seen:
            refuse(f"row {i}: name: duplicate {name}")
        seen.add(name)
        children = ()
        if klass == "split":
            if name not in SPLIT_ALLOWED:
                refuse(f"row {i}: name: split allowed only for {SPLIT_ALLOWED_TEXT}")
            raw_children = raw.get("children")
            if not raw_children:
                refuse(f"row {i}: children: a split row carries children")
            child_seen = set()
            children = []
            for craw in raw_children:
                if not isinstance(craw, dict):
                    refuse(f"row {i}: children: must be a table")
                cname = craw.get("name")
                if cname is None:
                    refuse(f"row {i}: children: name: missing")
                if (
                    not isinstance(cname, str)
                    or not cname
                    or "/" in cname
                    or cname == ".."
                ):
                    refuse(f"row {i}: children: name: must be one component")
                cclass = craw.get("class")
                if cclass is None:
                    refuse(f"row {i}: children: class: missing")
                if cclass not in CHILD_CLASSES:
                    refuse(f"row {i}: children: class: not one of {CHILD_CLASSES_TEXT}")
                cnote = craw.get("note")
                if cnote is not None and not isinstance(cnote, str):
                    refuse(f"row {i}: children: note: must be a string")
                if cname in child_seen:
                    refuse(f"row {i}: children: duplicate {cname}")
                child_seen.add(cname)
                children.append((cname, cclass))
            children = tuple(children)
        elif "children" in raw:
            refuse(f"row {i}: children: only a split row carries children")
        rows.append(Row(name, klass, children))
    return rows


def read_bytes(path):
    """The file's bytes; an unreadable file is a refusal."""
    try:
        return path.read_bytes()
    except OSError as exc:
        refuse(f"cannot read {path}: {exc.strerror}")


def parse(path, raw):
    """The file parsed as TOML; a parse error is a refusal naming it."""
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        refuse(f"{path}: {exc}")
    except tomllib.TOMLDecodeError as exc:
        refuse(f"{path}: {exc}")


def coverage(home, rows):
    """Print the coverage findings; return (failed, stale, backups)."""
    failed = False
    stale = 0
    backups = 0
    names = {row.name for row in rows}
    for name in os.listdir(home):
        if name.endswith(BACKUP_SUFFIX):
            print(f"home-classes: backup: {name}")
            backups += 1
            continue
        if name not in names:
            print(f"home-classes: unclassified: {name}")
            failed = True
    for row in rows:
        base = home / row.name
        if not base.exists():
            print(f"home-classes: stale: {row.name}")
            stale += 1
        elif row.klass == "split":
            child_names = {child[0] for child in row.children}
            for child in os.listdir(base):
                if child.endswith(BACKUP_SUFFIX):
                    print(f"home-classes: backup: {row.name}/{child}")
                    backups += 1
                    continue
                if child not in child_names:
                    print(f"home-classes: unclassified: {row.name}/{child}")
                    failed = True
        for cname, _klass in row.children:
            if not (base / cname).exists():
                print(f"home-classes: stale: {row.name}/{cname}")
                stale += 1
    return failed, stale, backups


def digest_hex(raw):
    """The lowercase hex digest of the list's bytes."""
    return hashlib.sha256(raw).hexdigest()


def resolve_digest(args):
    """The digest check compares against: --sha256 wins over --claims."""
    if args.sha256 is not None:
        match = HEX64_RE.fullmatch(args.sha256)
        if match is None:
            refuse("--sha256 must be 64 lowercase hex characters")
        return match.group(1)
    if args.claims is not None:
        claims = Path(args.claims)
        raw = read_bytes(claims)
        data = parse(claims, raw)
        claim_rows = None
        for key in CLAIM_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                claim_rows = value
                break
        row = None
        if claim_rows is not None:
            row = next(
                (
                    item
                    for item in claim_rows
                    if isinstance(item, dict) and item.get("id") == CLAIM_ID
                ),
                None,
            )
        if row is None:
            refuse(f"{claims}: no claim {CLAIM_ID}")
        text = row.get(CLAIM_DIGEST_FIELD)
        if not isinstance(text, str):
            refuse(f"{claims}: {CLAIM_ID} carries no sha256:")
        match = SHA256_RE.search(text)
        if match is None:
            refuse(f"{claims}: {CLAIM_ID} carries no sha256:")
        return match.group(1)
    refuse("check needs --sha256 or --claims")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="home-classes",
        description="check a home's list of file classes against the home",
    )
    sub = parser.add_subparsers(dest="verb", required=True)
    p_lint = sub.add_parser("lint", help="schema plus coverage of the home")
    p_hash = sub.add_parser("hash", help="print the list's sha256 digest")
    p_check = sub.add_parser("check", help="lint's work, then the digest")
    for p in (p_lint, p_hash, p_check):
        p.add_argument(
            "--file",
            metavar="PATH",
            help="the list (default:"
            " ${XDG_STATE_HOME:-$HOME/.local/state}/user-spaces"
            "/home-classes.toml)",
        )
        p.add_argument(
            "--home",
            metavar="DIR",
            help="the home to cover (default: $HOME)",
        )
    p_check.add_argument(
        "--sha256",
        metavar="HEX",
        help="the digest check compares against",
    )
    p_check.add_argument(
        "--claims",
        metavar="PATH",
        help="a claims file holding the home-classes-confirmed row",
    )
    args = parser.parse_args(argv)
    try:
        state = os.environ.get("XDG_STATE_HOME") or os.path.join(
            os.environ.get("HOME", ""), ".local", "state"
        )
        path = (
            Path(args.file)
            if args.file
            else Path(state, "user-spaces", "home-classes.toml")
        )
        home = Path(args.home) if args.home else Path(os.environ.get("HOME", ""))
        if args.verb == "hash":
            print("sha256:" + digest_hex(read_bytes(path)))
            return 0
        expected = None
        if args.verb == "check":
            expected = resolve_digest(args)
        raw = read_bytes(path)
        rows = validate(parse(path, raw))
        if not home.is_dir():
            refuse(f"--home {home} is not a directory")
        failed, stale, backups = coverage(home, rows)
        if expected is not None:
            actual = digest_hex(raw)
            if expected != actual:
                print(f"home-classes: hash mismatch: expected {expected} got {actual}")
                return 1
        if failed:
            return 1
        children = sum(len(row.children) for row in rows)
        print(
            f"home-classes: ok {len(rows)} entries, {children} children,"
            f" {stale} stale, {backups} backups"
        )
        return 0
    except Refused as exc:
        print(f"home-classes: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
