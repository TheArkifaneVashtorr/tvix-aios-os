#!/usr/bin/env python3
"""factory-graph.py -- a declarative workflow graph and its soundness checker.

A graph is TOML with a ``[graph]`` table (``name``, ``start``, ``input_kind``)
and ``[[node]]``/``[[edge]]`` rows. ``check`` exits 0 silently on a sound
graph and 2 after printing one line per fault as
``graph <file>: <node or edge>: <fault>``; an absent or unparseable file is
``graph <file>: unreadable: <message>`` before any other rule. ``dump`` prints
the checked graph as ``{nodes, edges, start}`` for the runner and the bats
stubs. The per-type key set is closed: a node row carries only
``name``/``type``/``rung``/``input_from``/``terminal`` plus its type's fields,
so a vendor-spelling key such as ``model`` is refused as ``unknown key`` and
never reaches the runner (decision 24a; assumption 17). ``terminal`` is an
optional bool on any node type: a ``terminal = true`` node is the graph's real
success terminus, exempt from the ``no exit to refusal`` soundness rule; a
non-bool value is a ``bad terminal`` fault.
"""

import argparse
import json
import sys

import tomllib

COMMON_KEYS = {"name", "type", "rung", "input_from", "terminal"}
TYPE_KEYS = {
    "agent": {"role"},
    "tool": {"command"},
    "gate": {"reviewer", "probes"},
    "refusal": set(),
}
TYPES = frozenset(TYPE_KEYS)
WHENS = frozenset({"ok", "broken", "rework", "reject", "exhausted", "any"})
EDGE_KEYS = {"from", "to", "when", "budget"}


def _fault(path, loc, msg):
    return f"graph {path}: {loc}: {msg}"


def _reachable(starts, adj):
    seen = set()
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for nxt in adj.get(cur, []):
            if nxt not in seen:
                stack.append(nxt)
    return seen


def _as_list(data, key):
    rows = data.get(key, [])
    if isinstance(rows, dict):
        return [rows]
    if isinstance(rows, list):
        return rows
    return []


def check_graph(path):
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        return [f"graph {path}: unreadable: {exc.strerror or exc}"]
    except tomllib.TOMLDecodeError as exc:
        return [f"graph {path}: unreadable: {exc}"]

    if not isinstance(data, dict):
        return [f"graph {path}: unreadable: not a table"]

    nodes = _as_list(data, "node")
    edges = _as_list(data, "edge")

    graph_tbl = data.get("graph", {})
    if not isinstance(graph_tbl, dict):
        graph_tbl = {}
    start = graph_tbl.get("start")

    names = [n.get("name") for n in nodes]
    name_set = {n for n in names if isinstance(n, str)}

    order = []
    for n in names:
        if isinstance(n, str) and n not in order:
            order.append(n)

    name_type = {}
    node_terminal = {}
    for n in nodes:
        nm = n.get("name")
        if nm in name_set and nm not in name_type:
            name_type[nm] = n.get("type")
            node_terminal[nm] = n.get("terminal")

    faults = []

    start_ok = start in name_set
    if not start_ok:
        faults.append(_fault(path, "start", "bad start"))

    seen = set()
    for nm in names:
        if nm in name_set and nm in seen:
            faults.append(_fault(path, nm, "duplicate node"))
        seen.add(nm)

    for node in nodes:
        nm = node.get("name", "?")
        typ = node.get("type")
        if typ not in TYPES:
            faults.append(_fault(path, nm, "bad type"))
        allowed = set(COMMON_KEYS)
        if typ in TYPES:
            allowed |= TYPE_KEYS[typ]
        for key in node:
            if key not in allowed:
                faults.append(_fault(path, nm, "unknown key"))
        if "rung" not in node:
            faults.append(_fault(path, nm, "undeclared rung"))
        if "terminal" in node and not isinstance(node["terminal"], bool):
            faults.append(_fault(path, nm, "bad terminal"))
        if "input_from" in node:
            val = node["input_from"]
            if typ == "tool" and isinstance(val, list):
                vals = val
            elif typ != "tool" and isinstance(val, list):
                faults.append(_fault(path, nm, "bad input_from"))
                vals = []
            else:
                vals = [val]
            for v in vals:
                if v not in name_set:
                    faults.append(_fault(path, nm, "bad input_from"))

    for edge in edges:
        fr = edge.get("from", "?")
        to = edge.get("to", "?")
        loc = f"edge {fr}->{to}"
        if edge.get("when") not in WHENS:
            faults.append(_fault(path, loc, "bad when"))
        for key in edge:
            if key not in EDGE_KEYS:
                faults.append(_fault(path, loc, "unknown key"))
        if fr not in name_set:
            faults.append(_fault(path, loc, "dangling edge"))
        if to not in name_set:
            faults.append(_fault(path, loc, "dangling edge"))
        budget = edge.get("budget")
        if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
            faults.append(_fault(path, loc, "zero budget"))

    adj = {n: [] for n in name_set}
    rev = {n: [] for n in name_set}
    for edge in edges:
        fr = edge.get("from")
        to = edge.get("to")
        if fr in adj and to in adj:
            adj[fr].append(to)
            rev[to].append(fr)

    if start_ok:
        for nm in order:
            if nm not in _reachable([start], adj):
                faults.append(_fault(path, nm, "unreachable"))

    refusal = {nm for nm in order if name_type.get(nm) == "refusal"}
    terminal = {nm for nm in order if node_terminal.get(nm) is True}
    can_exit = _reachable(refusal, rev)
    for nm in order:
        if name_type.get(nm) != "refusal" and nm not in can_exit and nm not in terminal:
            faults.append(_fault(path, nm, "no exit to refusal"))

    return faults


def dump_graph(path):
    faults = check_graph(path)
    if faults:
        return "\n".join(faults), 1
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    nodes = [
        {
            "name": n.get("name"),
            "type": n.get("type"),
            "rung": n.get("rung"),
            "role": n.get("role"),
            "command": n.get("command"),
            "input_from": n.get("input_from"),
        }
        for n in _as_list(data, "node")
    ]
    edges = [
        {
            "from": e.get("from"),
            "to": e.get("to"),
            "when": e.get("when"),
            "budget": e.get("budget"),
        }
        for e in _as_list(data, "edge")
    ]
    start = data.get("graph", {}).get("start")
    return json.dumps(
        {"nodes": nodes, "edges": edges, "start": start}, sort_keys=True
    ), 0


def main(argv):
    parser = argparse.ArgumentParser(prog="factory-graph.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    check_p = sub.add_parser("check")
    check_p.add_argument("files", nargs="+")
    dump_p = sub.add_parser("dump")
    dump_p.add_argument("file")
    args = parser.parse_args(argv)

    if args.cmd == "check":
        faults = []
        for path in args.files:
            faults.extend(check_graph(path))
        if faults:
            print("\n".join(faults))
            return 2
        return 0
    if args.cmd == "dump":
        out, code = dump_graph(args.file)
        if out:
            print(out)
        return code
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
