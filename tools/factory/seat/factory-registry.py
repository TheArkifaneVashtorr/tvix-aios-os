"""factory-registry.py -- the pinned agent registry and its generated shims.

One registry (tools/factory/agents.toml) pins each agent role to a routing
row (route/role/kind/size/class/rung/variant), the tools its shim advertises,
the artifact kind its output must satisfy (``schema``, an FA14 kind) and its
prompt file. ``render`` derives the .claude/agents/<name>.md shims from the
registry and the routing table; ``check`` refuses a registry whose rows do
not resolve, whose prompt or schema is bad, or whose shims have drifted;
``resolve NAME`` prints ``MODEL EFFORT`` for one row by shelling out to
tools/factory/route.py. Stdlib only (tomllib, subprocess); route.py's key
enums are imported so the registry stays pinned to one source.

A row may carry ``variant`` (FA32): a free-form discriminator (default
``any``) passed to route.py's lookup as --variant, so several rows may share
one (route, role, kind, size, class) key and resolve to different models --
the plan graph's three judge seats differ only by it. A variant no routing
row carries falls back to the any-variant row (route.py's class rule), never
an error.

Subcommands (each takes an optional leading ``--registry PATH``, default
tools/factory/agents.toml; paths resolve against the repo root this script
sits in):

  check [--shims DIR]           exit 0 silently when every row resolves, every
                                prompt exists, every schema names a kind and
                                every .claude/agents/<name>.md byte-equals
                                render's output; else one
                                ``registry: <role>: <fault>`` line per fault
                                (unresolvable | prompt missing | unknown
                                schema | drift | shim missing), exit 2.
  render [--out DIR]            write one shim per [[agent]] row into DIR
                                (default .claude/agents), deterministically
                                (sorted frontmatter keys, LF, trailing newline).
  resolve ROLE                  print ``MODEL EFFORT`` for one row, exiting
                                with route.py's code (4 on an escalate row).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_REGISTRY = "tools/factory/agents.toml"
DEFAULT_SHIMS = ".claude/agents"
ROUTE_PY = "tools/factory/route.py"

# FA14's artifact kinds (tools/factory/seat/factory-artifact.py KINDS).
KINDS = frozenset({"input", "attempt", "verdict", "reresolve", "escalation"})

# route.py sits in tools/factory/, one directory up from this script; import
# its key enums so a registry typo is refused against the same source the
# routing ladder reads rather than a hand-kept copy.
sys.path.insert(0, str(REPO_ROOT / "tools" / "factory"))
from route import CLASSES, ROLES, ROUTES, SIZES
from route import KINDS as ROUTE_KINDS


class ResolveError(Exception):
    """A row does not resolve; the message is route.py's or the key fault."""


def _repo_path(p):
    path = Path(p)
    return path if path.is_absolute() else REPO_ROOT / path


def load_registry(path):
    """The [[agent]] rows, or raise ResolveError on an unreadable file."""
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        raise ResolveError(f"registry: unreadable: {exc.strerror or exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ResolveError(f"registry: unreadable: {exc}") from exc
    rows = data.get("agent", [])
    if isinstance(rows, dict):
        rows = [rows]
    return rows


def _key_fault(row):
    """The first invalid routing key, or None when all five are route.py keys."""
    route = row.get("route", "openrouter")
    if route not in ROUTES:
        return f"unknown route {route!r}"
    if row.get("role") not in ROLES:
        return f"unknown role {row.get('role')!r}"
    if row.get("kind") not in ROUTE_KINDS:
        return f"unknown kind {row.get('kind')!r}"
    if row.get("size") not in SIZES:
        return f"unknown size {row.get('size')!r}"
    if row.get("class", "any") not in CLASSES:
        return f"unknown class {row.get('class', 'any')!r}"
    return None


def lookup_row(row):
    """Run route.py lookup for one row; ``(returncode, stdout, stderr)``."""
    fault = _key_fault(row)
    if fault is not None:
        return 2, "", fault
    cmd = [
        sys.executable,
        str(REPO_ROOT / ROUTE_PY),
        "lookup",
        row.get("route", "openrouter"),
        row["role"],
        row["kind"],
        row["size"],
        "--class",
        row.get("class", "any"),
        "--variant",
        row.get("variant", "any"),
        "--rung",
        str(row.get("rung", 1)),
    ]
    proc = subprocess.run(
        cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def resolve_row(row):
    """``(model, effort)`` for a row; ResolveError when it does not resolve.

    route.py prints ``MODEL EFFORT`` on stdout for both a resolved row (exit 0)
    and an EscalateError (exit 4, a class-scoped claude row won the search); a
    LadderError leaves stdout empty at the same exit 4. A parseable pair is a
    resolution regardless of exit code, so an escalate row resolves instead of
    being faulted ``unresolvable``.
    """
    _, out, err = lookup_row(row)
    parts = out.split()
    if len(parts) < 2:
        raise ResolveError(err or out or "no output")
    return parts[0], parts[1]


def render_shim(row, model, effort):
    """The deterministic shim text for one resolved row."""
    tools = ", ".join(row.get("tools", []))
    lines = [
        "---",
        f"name: {row['name']}",
        f"model: {model}",
        f"effort: {effort}",
        f"tools: {tools}",
        "---",
        "",
        (
            f"{row['name']} — {row.get('kind', '?')} {row.get('role', '?')} work "
            f"on the {row.get('route', 'openrouter')} lane."
        ),
        "",
        "<!-- generated by factory-registry.py; do not edit -->",
        "",
    ]
    return "\n".join(lines)


def check(rows, shims_dir):
    """The list of ``registry: <role>: <fault>`` lines for the registry."""
    faults = []
    for row in rows:
        name = row.get("name", "?")
        try:
            model, effort = resolve_row(row)
        except ResolveError:
            faults.append(f"registry: {name}: unresolvable")
            continue
        if not (REPO_ROOT / row.get("prompt", "")).is_file():
            faults.append(f"registry: {name}: prompt missing")
        if row.get("schema") not in KINDS:
            faults.append(f"registry: {name}: unknown schema")
        shim = shims_dir / f"{name}.md"
        if not shim.is_file():
            faults.append(f"registry: {name}: shim missing")
        elif shim.read_text() != render_shim(row, model, effort):
            faults.append(f"registry: {name}: drift")
    return faults


def find_row(rows, name):
    for row in rows:
        if row.get("name") == name:
            return row
    return None


def main(argv):
    parser = argparse.ArgumentParser(prog="factory-registry.py")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY)
    sub = parser.add_subparsers(dest="cmd", required=True)

    check_p = sub.add_parser("check")
    check_p.add_argument("--shims", default=DEFAULT_SHIMS)

    render_p = sub.add_parser("render")
    render_p.add_argument("--out", default=DEFAULT_SHIMS)

    resolve_p = sub.add_parser("resolve")
    resolve_p.add_argument("role")

    args = parser.parse_args(argv)

    if args.cmd == "check":
        try:
            rows = load_registry(_repo_path(args.registry))
        except ResolveError as exc:
            print(f"registry: {exc}", file=sys.stderr)
            return 2
        faults = check(rows, _repo_path(args.shims))
        if faults:
            print("\n".join(faults))
            return 2
        return 0

    if args.cmd == "render":
        try:
            rows = load_registry(_repo_path(args.registry))
        except ResolveError as exc:
            print(f"registry: {exc}", file=sys.stderr)
            return 2
        out_dir = _repo_path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for row in rows:
            name = row.get("name", "?")
            try:
                model, effort = resolve_row(row)
            except ResolveError:
                print(f"registry: {name}: unresolvable", file=sys.stderr)
                return 2
            (out_dir / f"{name}.md").write_text(render_shim(row, model, effort))
        return 0

    if args.cmd == "resolve":
        try:
            rows = load_registry(_repo_path(args.registry))
        except ResolveError as exc:
            print(f"registry: {exc}", file=sys.stderr)
            return 2
        row = find_row(rows, args.role)
        if row is None:
            print(f"registry: {args.role}: no such role", file=sys.stderr)
            return 2
        code, out, err = lookup_row(row)
        if out:
            print(out)
        else:
            print(err, file=sys.stderr)
        return code

    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
