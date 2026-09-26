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

A row may carry ``variant`` (FA32): a free-form discriminator, defaulting to
``any``, that lets several rows share one (route, role, kind, size, class,
area) key -- the plan graph's three judge seats differ only by it. It is the
least-specific discriminator (a row matching more of role/kind/size/class/
area always wins; variant only breaks ties), a requested variant matches rows
carrying it or ``any``-variant rows (a requested ``any`` matches only ``any``
rows, exactly like class), and an unknown requested variant falls back to the
``any`` row rather than failing. The bash reader tolerates the key but never
matches a variant row (it has no --variant flag), so a variant row is visible
only to callers that ask for it.

stdlib only; run via the toolbox devShell's python3.
"""

import json
import os
import sys

# Default table when no --file is given: FACTORY_ROUTING_TABLE names the table
# (an explicit --file still wins over the env var), falling back to the repo
# path. Relative paths resolve against the current directory.
DEFAULT_FILE = os.environ.get("FACTORY_ROUTING_TABLE", "docs/ledger/routing.toml")

ROUTES = ("openrouter", "openrouter-batch", "claude")
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
    "docs-spec",
    "docs-plan-run",
    "rust",
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

# Models whose OpenRouter endpoint refuses effort "off": a request with
# reasoning disabled 400s ("Reasoning is mandatory for this endpoint and
# cannot be disabled"), measured 2026-09-21 landing the publish-gate plan
# (docs/board/log-2026-09.md, the "THE PUBLISH GATE LANDED" entry) when the
# implement/docs rung-2 row paired z-ai/glm-5.3 with effort "off" and the
# seat died in two seconds (/var/lib/seat/jobs/20260921-112923-a7859a). Data,
# not a special case, so a future reasoning-mandatory model is one line here.
REASONING_MANDATORY_MODELS = frozenset(
    {
        "z-ai/glm-5.3",
    }
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


class EscalateError(Exception):
    """A class-scoped claude row won the cross-route search: escalate.

    Carries the winning row's (model, effort) so the lookup subcommand can
    print it on stdout (the bash factory_route prints the same and returns 4),
    distinct from LadderError which prints to stderr.
    """

    def __init__(self, model, effort):
        super().__init__(f"{model} {effort}")
        self.model = model
        self.effort = effort


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

    A ladder is the rows sharing one (route, role, kind, size, class, area,
    variant) key, ordered by rung. Refused: a duplicate rung within a key, a
    gapped ladder (rung N present with rung N-1 absent), a rung above 1 whose key has
    no rung-1 row, two adjacent rungs changing model AND effort, two adjacent
    rungs changing NEITHER (a degenerate climb a fix round could relaunch
    forever with no different outcome), an openrouter implement key with a
    rung 1 and no rung 2 (a fix round would exhaust on its first retry), and a
    fallback naming a model with no row of its own route. A class-scoped
    claude key is the operator terminus (its single rung feeds the cross-route
    escalation), so it is exempt from the rung-1 and gap requirements. FA32:
    variant joins the ladder key so rows that differ only by it (the plan
    graph's three judge seats) are separate ladders, not a duplicate rung;
    fault messages keep the six-part key spelling they had before the axis.
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
            row.get("area", "any"),
            row.get("variant", "any"),
        )
        rrung = int(row.get("rung", "1"))
        by_key.setdefault(key, []).append((rrung, idx, row))
    for key, entries in by_key.items():
        rungs = {}
        rung_idx = {}
        terminus = key[0] == "claude" and key[4] != "any"
        for rrung, idx, row in entries:
            if rrung in rungs:
                raise RowError(idx, f"ladder {'/'.join(key[:6])}: rung {rrung} twice")
            rungs[rrung] = row
            rung_idx[rrung] = idx
        present = set(rungs)
        if not terminus:
            if 1 not in present and present:
                low = min(present)
                raise RowError(rung_idx[low], f"rung {low} without rung 1 for its key")
            for rrung in sorted(present):
                if rrung > 1 and (rrung - 1) not in present:
                    raise RowError(
                        rung_idx[rrung],
                        f"rung {rrung} without rung {rrung - 1}",
                    )
        # An openrouter implement key with a rung 1 and no rung 2 cannot take
        # a fix round: factory-task's fix round defaults to the prior rung +
        # 1, so it would hit "ladder exhausted" on its very first retry and
        # escalate to the plan graph as though the plan were wrong -- exactly
        # what implement/code did (measured 2026-09-21, docs/board/log-2026-09.md)
        # after GLM1b (2026-09-19) deleted its rung-2 row outright. route.py
        # only (factory-lib.sh's factory_route_check does not carry this rule).
        if (
            key[0] == "openrouter"
            and key[1] == "implement"
            and 1 in present
            and 2 not in present
        ):
            raise RowError(
                rung_idx[1],
                f"implement/{key[2]} at rung 1 has no rung 2 -- a fix round "
                "would exhaust immediately",
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
                if a["model"] == b["model"] and a["effort"] == b["effort"]:
                    raise RowError(
                        rung_idx[rrung],
                        f"rungs {rrung}→{rrung + 1} change neither model nor effort",
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


def resolve(
    rows, route, role, kind, size, cls="any", rung="1", fallback=False, variant="any"
):
    """Return (model, effort) -- or (fallback, effort) -- for a ladder lookup.

    Mirrors factory_route: every row is validated, then every ladder, then the
    lookup. The rung-1 winner has the highest specificity (role/kind/size/class
    fields not "any"); ties go to the earliest row; a requested class matches
    its own rows or "any" rows (a requested "any" matches only "any" rows).
    A higher --rung N climbs to the row sharing the rung-1 winner's key, else
    LadderError ("ladder exhausted"); --fallback without one is LadderError
    ("no fallback"). The requested route must have a default (any/any/any) row.

    FA32: a requested variant matches rows carrying it or "any"-variant rows
    (a requested "any" matches only "any" rows, exactly like class), and it is
    the least-specific discriminator -- specificity is compared on
    role/kind/size/class/area first, with variant breaking ties -- so a row
    matching more of the five ordinary axes always wins and no existing row or
    call resolves differently. Variant-keyed rows never reach the cross-route
    claude search: the terminus is a plain-call mechanism.
    """
    best_row = None
    best_key = None
    best_spec = (-1, -1)
    have_default = False
    for idx, row in enumerate(rows, start=1):
        rroute = row.get("route", "openrouter")
        for key in ("role", "kind", "size", "model", "effort"):
            if key not in row:
                raise RowError(idx, "missing one of role/kind/size/model/effort")
        rclass = row.get("class", "any")
        rarea = row.get("area", "any")
        rvariant = row.get("variant", "any")
        rrung = row.get("rung", "1")
        vals = (
            rroute,
            row["role"],
            row["kind"],
            row["size"],
            row["model"],
            row["effort"],
            rclass,
            rarea,
            rvariant,
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
        if (
            rroute == "openrouter"
            and row["model"] in REASONING_MANDATORY_MODELS
            and reffort == "off"
        ):
            raise RowError(
                idx,
                f"model {row['model']!r} requires reasoning: effort 'off' is "
                'refused (OpenRouter 400s "Reasoning is mandatory for this '
                'endpoint and cannot be disabled")',
            )
        spec = (
            (rrole != "any")
            + (rkind != "any")
            + (rsize != "any")
            + (rclass != "any")
            + (rarea != "any"),
            rvariant != "any",
        )
        if (
            rroute == route
            and rrole == "any"
            and rkind == "any"
            and rsize == "any"
            and rclass == "any"
            and rarea == "any"
            and rvariant == "any"
        ):
            have_default = True
        if (
            rroute == route
            and rrung == "1"
            and rrole in (role, "any")
            and rkind in (kind, "any")
            and rsize in (size, "any")
            and (rclass == cls or rclass == "any")
            and (rvariant == variant or rvariant == "any")
            and spec > best_spec
        ):
            best_spec = spec
            best_row = row
            best_key = (rroute, rrole, rkind, rsize, rclass, rarea, rvariant)
    check_ladders(rows)
    if not have_default:
        raise SchemaError(f"no default (any/any/any) row for route {route!r}")
    # Cross-route winner: a class-scoped claude row at the requested rung beats
    # the openrouter ladder and escalates (decision 28's operator terminus). An
    # explicit --route claude keeps its own meaning, so this fires only for the
    # default openrouter lookup.
    if route != "claude":
        cross_row = None
        cross_spec = -1
        for row in rows:
            if row.get("route", "openrouter") != "claude":
                continue
            if row.get("variant", "any") != "any":
                # FA32: a variant-keyed row never captures the cross-route
                # search -- the terminus is a plain-call mechanism, and no
                # --variant flag exists on the escalation path.
                continue
            cclass = row.get("class", "any")
            if cclass == "any":
                continue
            if row.get("rung", "1") != rung:
                continue
            crole, ckind, csize = row["role"], row["kind"], row["size"]
            if crole not in (role, "any"):
                continue
            if ckind not in (kind, "any"):
                continue
            if csize not in (size, "any"):
                continue
            if cclass != cls:
                continue
            carea = row.get("area", "any")
            cspez = (
                (crole != "any")
                + (ckind != "any")
                + (csize != "any")
                + (cclass != "any")
                + (carea != "any")
            )
            if cspez > cross_spec:
                cross_spec = cspez
                cross_row = row
        if cross_row is not None:
            raise EscalateError(cross_row["model"], cross_row["effort"])
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
                row.get("area", "any"),
                row.get("variant", "any"),
            )
            if key == best_key and row.get("rung", "1") == rung:
                target = row
                break
        if target is None:
            raise LadderError(
                f"ladder exhausted at rung {rung} for {'/'.join(best_key[:6])}"
            )
    if fallback:
        if "fallback" not in target or not target["fallback"]:
            raise LadderError(
                f"no fallback at rung {rung} for {'/'.join(best_key[:6])}"
            )
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
        " [--class C] [--rung N] [--variant V] [--fallback]\n"
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
        variant = "any"
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
            elif opt == "--variant":
                if i + 1 >= len(opts):
                    usage(sys.stderr)
                    return 2
                variant = opts[i + 1]
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
                variant=variant,
            )
        except EscalateError as exc:
            print(f"{exc.model} {exc.effort}")
            return 4
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
