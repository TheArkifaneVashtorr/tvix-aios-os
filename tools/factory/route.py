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
CLASSES = (
    "nix-module",
    "nix-check",
    "bash-driver",
    "python-evidence",
    "js-workflow",
    "bats-test",
    "vm-test",
    "docs-runbook",
    "docs-plan",
    "docs-board",
    "any",
)

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


class LadderError(Exception):
    """The ladder ran off its end: an exhausted rung or a missing fallback."""


def _valid_rung(val):
    """A rung is a positive integer, held as a digit string."""
    return val.isdigit() and int(val) >= 1


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


def check_ladders(rows):
    """Validate every ladder's cross-row rules; raise RowError on the first.

    A ladder is the rows sharing one (route, role, kind, size, class) key,
    ordered by rung. Refused: a duplicate rung within a key, a gapped ladder
    (rung N present with rung N-1 absent), a rung above 1 whose key has no
    rung-1 row, two adjacent rungs changing model AND effort, and a fallback
    naming a model with no row of its own route.
    """
    by_key = {}
    for idx, row in enumerate(rows, start=1):
        rroute = row.get("route", "openrouter")
        key = (
            rroute,
            row.get("role"),
            row.get("kind"),
            row.get("size"),
            row.get("class", "any"),
        )
        rrung = int(row.get("rung", "1"))
        by_key.setdefault(key, []).append((rrung, idx, row))
    for key, entries in by_key.items():
        rungs = {}
        rung_idx = {}
        for rrung, idx, row in entries:
            if rrung in rungs:
                raise RowError(idx, f"ladder {'/'.join(key)}: rung {rrung} twice")
            rungs[rrung] = row
            rung_idx[rrung] = idx
        present = set(rungs)
        if 1 not in present and present:
            low = min(present)
            raise RowError(rung_idx[low], f"rung {low} without rung 1 for its key")
        for rrung in sorted(present):
            if rrung > 1 and (rrung - 1) not in present:
                raise RowError(
                    rung_idx[rrung],
                    f"rung {rrung} without rung {rrung - 1}",
                )
        for rrung in sorted(present):
            if rrung + 1 in present:
                a = rungs[rrung]
                b = rungs[rrung + 1]
                if a["model"] != b["model"] and a["effort"] != b["effort"]:
                    raise RowError(
                        rung_idx[rrung],
                        f"rungs {rrung}→{rrung + 1} change model and effort",
                    )
    models_by_route = {}
    for row in rows:
        rroute = row.get("route", "openrouter")
        models_by_route.setdefault(rroute, set()).add(row.get("model"))
    for idx, row in enumerate(rows, start=1):
        if row.get("fallback"):
            rroute = row.get("route", "openrouter")
            if row["fallback"] not in models_by_route.get(rroute, set()):
                raise RowError(idx, f"fallback {row['fallback']} has no row of its own")


def resolve(rows, route, role, kind, size, cls="any", rung="1", fallback=False):
    """Return (model, effort) -- or (fallback, effort) -- for a ladder lookup.

    Mirrors factory_route: every row is validated, then every ladder, then the
    lookup. The rung-1 winner has the highest specificity (role/kind/size/class
    fields not "any"); ties go to the earliest row; a requested class matches
    its own rows or "any" rows (a requested "any" matches only "any" rows).
    A higher --rung N climbs to the row sharing the rung-1 winner's key, else
    LadderError ("ladder exhausted"); --fallback without one is LadderError
    ("no fallback"). The requested route must have a default (any/any/any) row.
    """
    best_row = None
    best_key = None
    best_spec = -1
    have_default = False
    for idx, row in enumerate(rows, start=1):
        rroute = row.get("route", "openrouter")
        for key in ("role", "kind", "size", "model", "effort"):
            if key not in row:
                raise RowError(idx, "missing one of role/kind/size/model/effort")
        rclass = row.get("class", "any")
        rrung = row.get("rung", "1")
        vals = (
            rroute,
            row["role"],
            row["kind"],
            row["size"],
            row["model"],
            row["effort"],
            rclass,
        )
        if "fallback" in row:
            vals = vals + (row["fallback"],)
        for val in vals:
            if not val or not all(c in _VALUE_CHARS for c in val):
                raise RowError(idx, f"bad value {val!r}")
        rrole, rkind, rsize, _, reffort = (
            row["role"],
            row["kind"],
            row["size"],
            row["model"],
            row["effort"],
        )
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
        if rclass not in CLASSES:
            raise RowError(idx, f"unknown class {rclass!r}")
        if not _valid_rung(rrung):
            raise RowError(idx, f"bad rung {rrung!r}")
        spec = (
            (rrole != "any") + (rkind != "any") + (rsize != "any") + (rclass != "any")
        )
        if (
            rroute == route
            and rrole == "any"
            and rkind == "any"
            and rsize == "any"
            and rclass == "any"
        ):
            have_default = True
        if (
            rroute == route
            and rrung == "1"
            and rrole in (role, "any")
            and rkind in (kind, "any")
            and rsize in (size, "any")
            and (rclass == cls or rclass == "any")
            and spec > best_spec
        ):
            best_spec = spec
            best_row = row
            best_key = (rroute, rrole, rkind, rsize, rclass)
    check_ladders(rows)
    if not have_default:
        raise SchemaError(f"no default (any/any/any) row for route {route!r}")
    if rung == "1":
        target = best_row
    else:
        target = None
        for row in rows:
            rr = row.get("route", "openrouter")
            key = (
                rr,
                row.get("role"),
                row.get("kind"),
                row.get("size"),
                row.get("class", "any"),
            )
            if key == best_key and row.get("rung", "1") == rung:
                target = row
                break
        if target is None:
            raise LadderError(
                f"ladder exhausted at rung {rung} for {'/'.join(best_key)}"
            )
    if fallback:
        if "fallback" not in target or not target["fallback"]:
            raise LadderError(f"no fallback at rung {rung} for {'/'.join(best_key)}")
        return (target["fallback"], target["effort"])
    return (target["model"], target["effort"])


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
        "       route.py [--file PATH] lookup ROUTE ROLE KIND SIZE"
        " [--class C] [--rung N] [--fallback]\n"
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
        if len(rest) < 4:
            usage(sys.stderr)
            return 2
        route, role, kind, size = rest[:4]
        opts = rest[4:]
        cls = "any"
        rung = "1"
        fallback = False
        i = 0
        while i < len(opts):
            opt = opts[i]
            if opt == "--class":
                if i + 1 >= len(opts):
                    usage(sys.stderr)
                    return 2
                cls = opts[i + 1]
                i += 2
            elif opt == "--rung":
                if i + 1 >= len(opts):
                    usage(sys.stderr)
                    return 2
                rung = opts[i + 1]
                i += 2
            elif opt == "--fallback":
                fallback = True
                i += 1
            else:
                usage(sys.stderr)
                return 2
        try:
            model, effort = resolve(
                rows,
                route,
                role,
                kind,
                size,
                cls=cls,
                rung=rung,
                fallback=fallback,
            )
        except LadderError as exc:
            print(f"route.py: {exc}", file=sys.stderr)
            return 4
        except (RowError, SchemaError) as exc:
            print(f"route.py: {exc}", file=sys.stderr)
            return 1
        print(f"{model} {effort}")
        return 0
    usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
