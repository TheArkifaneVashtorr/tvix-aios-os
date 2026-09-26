#!/usr/bin/env python3
"""Read the factory's one routing table (docs/ledger/routing.toml).

tools/factory/dark-factory.js keeps a built-in default ``models`` map because
the Workflow harness cannot read files; this script is the single source that
map is derived from, so the two stay in sync or the factory-unit check fails.

Subcommands (each takes an optional leading ``--file PATH``, default
docs/ledger/routing.toml or ``FACTORY_ROUTING_TABLE`` when that env var is
set):

  models                        print the JSON object
                                ``{"baseline","impl","reviewCode","reviewDocs",
                                "verify","audit"}`` derived from the claude
                                rows (dark-factory.js's default map shape).
  check                         validate every row; exit 1 (printing the row
                                number) on the first malformed row, or when a
                                route present in the table has no default
                                (any/any/any) row.
  lookup ROUTE ROLE KIND SIZE   print ``MODEL EFFORT`` for the most specific
                                matching row, with the same specificity rule
                                as the bash ``factory_route`` in
                                tools/factory/seat/factory-lib.sh.

stdlib only; run via the toolbox devShell's python3.
"""

import json
import os
import sys

# Default table when no --file is given: FACTORY_ROUTING_TABLE names the table
# (an explicit --file still wins over the env var), falling back to the repo
# path. Relative paths resolve against the current directory.
DEFAULT_FILE = os.environ.get("FACTORY_ROUTING_TABLE", "docs/ledger/routing.toml")

ROUTES = ("openrouter", "claude")
ROLES = (
    "implement",
    "review",
    "verify",
    "baseline",
    "research",
    "audit",
    "orchestrate",
    "plan",
    "any",
)
KINDS = ("docs", "code", "any")
SIZES = ("XS", "S", "M", "L", "any")
EFFORTS = ("off", "low", "medium", "high", "xhigh")

# The models-map keys dark-factory.js uses, and the claude (role, kind, size)
# row each one derives its model from. Order is the output order.
MODEL_KEYS = (
    ("baseline", "baseline", "any", "any"),
    ("impl", "implement", "any", "any"),
    ("reviewCode", "review", "code", "any"),
    ("reviewDocs", "review", "docs", "any"),
    ("verify", "verify", "any", "any"),
    ("audit", "audit", "any", "any"),
)

# The characters factory_route allows in any value ([A-Za-z0-9._:/-]+).
_VALUE_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:/-"
)


class RowError(Exception):
    """A malformed row; .row is the 1-based [[route]] block number."""

    def __init__(self, row, message):
        super().__init__(f"row {row}: {message}")
        self.row = row


class SchemaError(Exception):
    """The table lacks a default row for the requested route."""


def parse_table(text):
    """Parse the [[route]] blocks into a list of dicts (one per row)."""
    rows = []
    cur = None
    row_num = 0
    for raw in text.splitlines():
        line = raw.strip()
        if line == "" or line.startswith("#"):
            continue
        if line.startswith("[[route]]"):
            cur = {}
            rows.append(cur)
            row_num += 1
            continue
        if "=" in line:
            if cur is None:
                raise RowError(1, f"key {raw!r} outside a [[route]] block")
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            cur[key] = val
            continue
        raise RowError(row_num, f"malformed line {raw!r}")
    return rows


def resolve(rows, route, role, kind, size):
    """Return (model, effort) for the most specific matching row.

    Mirrors factory_route: every row is validated regardless of the requested
    route; the winning row has the highest specificity (number of role/kind/
    size fields not "any"), ties go to the earliest row; the requested route
    must have a default (any/any/any) row.
    """
    best = None
    best_spec = -1
    have_default = False
    for idx, row in enumerate(rows, start=1):
        rroute = row.get("route", "openrouter")
        for key in ("role", "kind", "size", "model", "effort"):
            if key not in row:
                raise RowError(idx, "missing one of role/kind/size/model/effort")
        vals = (
            rroute,
            row["role"],
            row["kind"],
            row["size"],
            row["model"],
            row["effort"],
        )
        for val in vals:
            if not val or not all(c in _VALUE_CHARS for c in val):
                raise RowError(idx, f"bad value {val!r}")
        rrole, rkind, rsize, rmodel, reffort = vals[1:]
        if rroute not in ROUTES:
            raise RowError(idx, f"unknown route {rroute!r}")
        if rrole not in ROLES:
            raise RowError(idx, f"unknown role {rrole!r}")
        if rkind not in KINDS:
            raise RowError(idx, f"unknown kind {rkind!r}")
        if rsize not in SIZES:
            raise RowError(idx, f"unknown size {rsize!r}")
        if reffort not in EFFORTS:
            raise RowError(idx, f"bad effort {reffort!r}")
        spec = (rrole != "any") + (rkind != "any") + (rsize != "any")
        if rroute == route and rrole == "any" and rkind == "any" and rsize == "any":
            have_default = True
        if (
            rroute == route
            and rrole in (role, "any")
            and rkind in (kind, "any")
            and rsize in (size, "any")
            and spec > best_spec
        ):
            best_spec = spec
            best = (rmodel, reffort)
    if not have_default:
        raise SchemaError(f"no default (any/any/any) row for route {route!r}")
    return best


def load_rows(path):
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        raise SchemaError(f"cannot read {path}: {exc}") from exc
    return parse_table(text)


def usage(stream):
    stream.write(
        "usage: route.py [--file PATH] models\n"
        "       route.py [--file PATH] check\n"
        "       route.py [--file PATH] lookup ROUTE ROLE KIND SIZE\n"
    )


def main(argv):
    args = list(argv)
    path = DEFAULT_FILE
    if args and args[0] == "--file":
        if len(args) < 3:
            usage(sys.stderr)
            return 2
        path = args[1]
        args = args[2:]
    if not args:
        usage(sys.stderr)
        return 2
    command = args[0]
    rest = args[1:]
    try:
        rows = load_rows(path)
    except SchemaError as exc:
        print(f"route.py: {exc}", file=sys.stderr)
        return 1
    if command == "models":
        try:
            models = {}
            for key, role, kind, size in MODEL_KEYS:
                model, _effort = resolve(rows, "claude", role, kind, size)
                models[key] = model
        except RowError as exc:
            print(f"route.py: {exc}", file=sys.stderr)
            return 1
        except SchemaError as exc:
            print(f"route.py: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(models))
        return 0
    if command == "check":
        try:
            resolve(rows, "openrouter", "any", "any", "any")
            resolve(rows, "claude", "any", "any", "any")
        except RowError as exc:
            print(f"route.py: {exc}", file=sys.stderr)
            return 1
        except SchemaError as exc:
            print(f"route.py: {exc}", file=sys.stderr)
            return 1
        return 0
    if command == "lookup":
        if len(rest) != 4:
            usage(sys.stderr)
            return 2
        route, role, kind, size = rest
        try:
            model, effort = resolve(rows, route, role, kind, size)
        except (RowError, SchemaError) as exc:
            print(f"route.py: {exc}", file=sys.stderr)
            return 1
        print(f"{model} {effort}")
        return 0
    usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
