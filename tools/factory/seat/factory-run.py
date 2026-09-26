"""factory-run.py -- the repo-side declarative-graph runner.

One runner walks a sound graph (decision 22a), handing each node exactly the
artifact the runner chooses for it (decision 21c) and spending the attempt
budgets the edges declare (decision 24a). This task ships only the dry-run
``stub`` executor and the dispatch scaffold FA16/FA17 fill: a non-dry-run
``agent``/``tool``/``gate`` raises ``NotImplementedError``, while a ``refusal``
always writes the ``exhausted`` artifact.

Preflight refuses without writing anything under ``DIR``: an unsound or
``unreadable`` graph, a registry that fails ``check``, an input artifact that
fails ``check``, an input artifact whose ``kind`` is not the graph's
``input_kind``, or a ``--start`` naming no node. The walk then advances from
``graph.start`` (or ``--start``), running each node's executor, checking each
produced artifact, recording one journal line per step, and choosing the next
edge by the artifact's verdict (the first ``when`` or ``any`` with budget
remaining). A ``gate`` that answers ``ok`` ends the run; a node with no
takeable edge follows its ``exhausted`` edge or the nearest ``refusal``.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import tomllib

SEAT_DIR = Path(__file__).resolve().parent

# FA15b: a hard step cap. Sound graphs terminate (every transition but the BFS
# fallback spends a budget and a refusal node has no outgoing edges), but a
# mutation that breaks that invariant would otherwise loop forever and wedge
# `unit`; this turns the loop into a red line within a bounded time.
MAX_STEPS = 50


def _artifact(name, rung, verdict):
    """A minimal artifact factory-artifact.py check accepts."""
    return {
        "kind": "attempt",
        "key": name,
        "node": name,
        "rung": rung,
        "claims": [],
        "repro": None,
        "errata": [],
        "verdict": verdict,
        "inputs": {},
        "scores": None,
        "wrong_facts": None,
    }


def _broken(name, rung, errata):
    """The tool/seat failure artifact: verdict broken with the given errata."""
    artifact = _artifact(name, rung, "broken")
    artifact["errata"] = list(errata)
    return artifact


class _SeatUnavailable(Exception):
    """The runner turns factory-task --node's exit 2 into a seat-unavailable exit 3."""


def run_stub(node, rung, verdict, _input, _run_dir):
    """Dry-run executor: verdict from --stub-verdicts, no model, no command."""
    if os.environ.get("FACTORY_STUB_BAD") == "1":
        verdict = "maybe"
    return _artifact(node["name"], rung, verdict)


def run_refusal(node, rung, _verdict, input_field, run_dir):
    """The refusal node escalates (FA12's writer, decision 73 / FA17 Interface 5):
    write <KEY>.escalation.json (the `escalation` artifact) and <KEY>.escalate
    (one paragraph plus one `launch:` line), then return the exhausted artifact.
    attempts is the node's rung -- the ladder rung reached IS the attempt count,
    so a multi-attempt escalation never misreports a hard-coded 1 (FA17b MINOR-3).
    """
    name = node["name"]
    run_dir = Path(run_dir)
    with open(input_field, encoding="utf-8") as fh:
        doc = json.load(fh)
    with open(run_dir / "run.json", encoding="utf-8") as fh:
        run_json = json.load(fh)
        graph = run_json.get("graph", ".claude/workflows/plan.toml")
    run_name = _run_name(run_dir)

    # The escalation is named by the TASK key (the seed input's key), not by
    # the intermediate node whose artifact is this refusal's input (whose
    # `key` is that node's name). Read the seed from run.json["input"].
    seed_input = run_json.get("input")
    key = doc.get("key")
    if seed_input:
        try:
            with open(seed_input, encoding="utf-8") as fh:
                key = json.load(fh).get("key", key)
        except (OSError, json.JSONDecodeError):
            key = doc.get("key", key)

    paragraph = (
        f"{key}: the graph run ended at the refusal node after verdict "
        f"{doc.get('verdict')!r} at rung {rung} after {rung} attempts"
    )
    launch = (
        f"nix develop -c python3 tools/factory/seat/factory-run.py"
        f" {graph} --input {run_name}/{key}.escalation.json --run {run_name}"
    )
    code, out = _tool(
        "factory-artifact.py",
        "write",
        "escalation",
        "--key",
        key,
        "--node",
        name,
        "--rung",
        str(rung),
        "--attempts",
        str(rung),
        "--verdict",
        "exhausted",
        "--claim",
        f"{paragraph}::{launch}::{graph}:1",
    )
    if code != 0:
        return _broken(name, rung, [out.strip()])
    (run_dir / f"{key}.escalation.json").write_text(out)
    (run_dir / f"{key}.escalate").write_text(f"{paragraph}\nlaunch: {launch}\n")
    return _artifact(name, rung, "exhausted")


def _repo():
    """The repo the runner was invoked in (the graph path is repo-relative)."""
    return os.getcwd()


def _run_name(run_dir):
    """The factory run name: the basename of the --run directory."""
    return Path(run_dir).name


def run_agent(node, rung, verdict, input_field, run_dir):
    """One seat job for an agent node (decision 33a): shell out to factory-task
    --node, which resolves the registry row, composes the brief and submits.
    Model and effort come from the registry (factory-task resolves them), never
    from the graph or this runner."""
    role = node["role"]
    name = node["name"]
    with open(input_field, encoding="utf-8") as fh:
        key = json.load(fh)["key"]

    out = run_dir / f".agent-{name}.json"
    env = os.environ.copy()
    env["FACTORY_NODE"] = name
    env["FACTORY_RUNG"] = str(rung)
    env["FACTORY_RUN_DIR"] = str(run_dir)

    cmd = [
        "bash",
        str(SEAT_DIR / "factory-task"),
        _run_name(run_dir),
        _repo(),
        key,
        "--node",
        str(input_field),
        "--role",
        role,
        "--rung",
        str(rung),
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    if proc.returncode == 2:
        # factory-task --node refused (no seat-submit reachable): the runner
        # reports it as a seat-unavailable exit 3, never an ok artifact (M2).
        raise _SeatUnavailable()
    if proc.returncode != 0:
        raise RuntimeError(
            f"factory-task --node exited {proc.returncode}: {proc.stderr.strip()}"
        )
    with open(out, encoding="utf-8") as fh:
        return json.load(fh)


def run_tool(node, rung, verdict, input_field, run_dir):
    """Run a tool node's `command` (argv[0] under tools/factory/seat/) with the
    input path(s) appended, cwd the repo, no shell, FACTORY_NODE/RUNG/RUN_DIR in
    the environment. Exit 0's stdout is the artifact; a non-zero exit is broken
    with the stderr tail (20 lines)."""
    name = node["name"]
    command = node["command"]
    paths = input_field if isinstance(input_field, list) else [input_field]
    env = os.environ.copy()
    env["FACTORY_NODE"] = name
    env["FACTORY_RUNG"] = str(rung)
    env["FACTORY_RUN_DIR"] = str(run_dir)

    proc = subprocess.run(
        [str(command[0]), *[str(p) for p in command[1:]], *[str(p) for p in paths]],
        cwd=_repo(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return _broken(name, rung, proc.stderr.splitlines()[-20:])
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return _broken(name, rung, ["tool stdout is not a JSON artifact"])


def _not_implemented(_node, _rung, _verdict, _input, _run_dir):
    raise NotImplementedError("unknown node type")


class _GatePlanError(Exception):
    """The gate's plan is absent, unreadable, or carries no section for the key."""

    def __init__(self, code, plan, key):
        self.code = code
        self.plan = plan
        self.key = key
        if code == 3:
            self.message = f"plan {plan} has no section for {key}"
        else:
            self.message = f"plan {plan} unreadable (key {key})"
        super().__init__(self.message)


def _factory_fn(name, *args):
    """Run one bash function from factory-lib.sh.

    Returns (rc, stdout, stderr) with stderr captured separately from stdout --
    a failure's stderr text is never folded into stdout, so it cannot be
    mistaken for probe rows or acceptance check names (FA17b MAJOR-1).
    """
    lib = SEAT_DIR / "factory-lib.sh"
    argv = " ".join(shlex.quote(a) for a in args)
    script = f'source "{lib}"\n{name} {argv}\n'
    proc = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        check=False,
        cwd=_repo(),
    )
    return proc.returncode, proc.stdout, proc.stderr


def _probe_contract(plan, key):
    """The probe contract for (plan, key) as (env_tokens, [(name, op, value, by, cmd)]).

    Raises _GatePlanError on a non-zero `factory_task_probes` exit -- which is
    exactly the absent-plan / unreadable-plan / no-section case -- instead of
    silently returning an empty contract (FA17b MAJOR-1).
    """
    rc, out, _err = _factory_fn("factory_task_probes", plan, key)
    if rc != 0:
        raise _GatePlanError(rc, plan, key)
    lines = out.splitlines()
    env = ""
    probes = []
    if lines:
        if "\t" in lines[0]:
            env = lines[0].split("\t", 1)[1]
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) >= 5:
                probes.append(tuple(parts[:5]))
    return env, probes


def _acceptance_names(plan, key):
    """The section's acceptance check names, one per line from factory_acceptance_names.

    Surface a non-zero rc rather than discarding it (FA17b MAJOR-1): the plan's
    own contract came back unreadable, so the gate must not proceed to run
    fabricated check rows.
    """
    rc, out, _err = _factory_fn("factory_acceptance_names", plan, key)
    if rc != 0:
        raise _GatePlanError(rc, plan, key)
    return [n for n in out.split() if n]


def _probe_compare(op, bound, value):
    """The `tasks.py probes` op comparison, mirrored from factory_probe_compare."""
    value = value.strip()
    if op in ("le", "lt", "ge", "gt"):
        try:
            vnum = float(value)
            bnum = float(bound)
        except ValueError:
            return False
        return {
            "le": vnum <= bnum,
            "lt": vnum < bnum,
            "ge": vnum >= bnum,
            "gt": vnum > bnum,
        }[op]
    if op in ("eq", "ne"):
        eq = value == bound.strip()
        return eq if op == "eq" else not eq
    if op == "empty":
        return value == ""
    if op == "nonempty":
        return value != ""
    return False


def _run_probe(env_tokens, cmd, timeout=60):
    """Run one probe command; the last non-empty stdout line, trimmed to 200 bytes."""
    env = os.environ.copy()
    env.pop("FACTORY_RUN", None)
    for tok in env_tokens.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            env[k] = v
    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            cwd=_repo(),
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ""
    last = ""
    for line in proc.stdout.splitlines():
        s = line.strip()
        if s:
            last = s
    return last[:200]


def _broken_plan(name, rung, exc):
    """The gate's broken:plan artifact -- one claim row, no fabricated rows, no model."""
    art = _artifact(name, rung, "broken")
    art["kind"] = "verdict"
    art["claims"] = [
        {
            "text": exc.message,
            "command": f"python3 pkgs/evidence/tasks.py probes {exc.plan} {exc.key}",
            "citation": "factory-run.py:1",
            "name": "plan",
            "held": False,
        }
    ]
    art["errata"] = ["broken:plan"]
    return art


def run_gate(node, rung, verdict, input_field, run_dir):
    """The gate node (decision 25b): re-run probes, acceptance checks and claims
    mechanically -- no model -- then, only if every row held, call factory-review
    to file and map the reviewer's verdict. Any broken row means verdict broken
    with no model; an absent/unreadable plan section is broken:plan; a reviewer
    with no verdict line is broken with the `no verdict line` erratum (FA17b).
    """
    name = node["name"]
    run_dir = Path(run_dir)
    with open(input_field, encoding="utf-8") as fh:
        key = json.load(fh)["key"]
    with open(run_dir / "run.json", encoding="utf-8") as fh:
        plan = json.load(fh)["plan"]
    reviewer = node.get("reviewer", "review")

    # mechanical rows first, no model. claims[] = one row per probe/check/claim,
    # errata[] carries held:<name> / broken:<name> (FA17 Interface 1).
    try:
        env_tokens, probes = _probe_contract(plan, key)
    except _GatePlanError as exc:
        return _broken_plan(name, rung, exc)

    claims = []
    errata = []
    broken = False

    if node.get("probes"):
        for pname, op, value, _by, cmd in probes:
            observed = _run_probe(env_tokens, cmd)
            held = _probe_compare(op, value, observed)
            claims.append(
                {
                    "text": f"probe {pname}",
                    "command": cmd,
                    "citation": f"{plan}:1",
                    "name": pname,
                    "held": held,
                }
            )
            errata.append(f"{'held' if held else 'broken'}:{pname}")
            broken = broken or not held

    try:
        names = _acceptance_names(plan, key)
    except _GatePlanError as exc:
        return _broken_plan(name, rung, exc)
    for cname in names:
        cmd = f"{os.environ.get('FACTORY_NIX', 'nix')} build .#checks.x86_64-linux.{cname} --no-link"
        proc = subprocess.run(
            cmd, shell=True, cwd=_repo(), capture_output=True, text=True, check=False
        )
        held = proc.returncode == 0
        claims.append(
            {
                "text": f"check {cname}",
                "command": cmd,
                "citation": f"{plan}:1",
                "name": cname,
                "held": held,
            }
        )
        errata.append(f"{'held' if held else 'broken'}:{cname}")
        broken = broken or not held

    with open(input_field, encoding="utf-8") as fh:
        doc = json.load(fh)
    for i, claim in enumerate(doc.get("claims", [])):
        ccmd = claim.get("command", "")
        proc = subprocess.run(
            ccmd, shell=True, cwd=_repo(), capture_output=True, text=True, check=False
        )
        held = proc.returncode == 0
        claims.append(
            {
                "text": claim.get("text", ""),
                "command": ccmd,
                "citation": claim.get("citation", ""),
                "name": f"claim{i}",
                "held": held,
            }
        )
        errata.append(f"{'held' if held else 'broken'}:claim{i}")
        broken = broken or not held

    art = _artifact(name, rung, None)
    art["kind"] = "verdict"
    art["claims"] = claims
    art["errata"] = errata

    if broken:
        art["verdict"] = "broken"
        return art

    # Every mechanical row held: file the verdict artifact and call the reviewer.
    verdict_path = run_dir / f".verdict-{name}.json"
    verdict_path.write_text(json.dumps(art, sort_keys=True) + "\n")
    run_name = _run_name(run_dir)
    proc = subprocess.run(
        [
            "bash",
            str(SEAT_DIR / "factory-review"),
            run_name,
            _repo(),
            key,
            "--reviewer-role",
            reviewer,
            "--verdict-artifact",
            str(verdict_path),
            "--file-under",
            str(Path(_repo()) / "docs" / "reviews"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    rc = proc.returncode
    try:
        reloaded = json.loads(verdict_path.read_text())
    except (OSError, json.JSONDecodeError):
        reloaded = {}
    mapped = reloaded.get("verdict")
    if mapped in ("ok", "rework", "reject", "broken"):
        art = reloaded
    else:
        # factory-review wrote no verdict record (it died before its mapping
        # block, e.g. the unguarded no-verdict-line case this round fixed). The
        # `no verdict line` erratum itself is authored in factory-review's parse;
        # here the gate falls back to a bare broken rather than approving a
        # verdict it never got (FA17b MAJOR-2).
        art["verdict"] = "broken"
    _ = rc  # read back; the reloaded artifact's verdict is authoritative
    return art


def executor_for(node_type, dry_run):
    if node_type == "refusal":
        return run_refusal
    if dry_run:
        return run_stub
    if node_type == "agent":
        return run_agent
    if node_type == "tool":
        return run_tool
    if node_type == "gate":
        return run_gate
    return _not_implemented


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------


def _tool(*argv):
    proc = subprocess.run(
        [sys.executable, str(SEAT_DIR / argv[0]), *argv[1:]],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout


def _load_graph(path):
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    nodes = data.get("node", [])
    if isinstance(nodes, dict):
        nodes = [nodes]
    edges = data.get("edge", [])
    if isinstance(edges, dict):
        edges = [edges]
    return data.get("graph", {}), nodes, edges


def preflight(args):
    """All refusals before anything is written under --run.

    Returns None (proceed) or the message to print verbatim (exit 2).
    """
    code, out = _tool("factory-graph.py", "check", args.graph)
    if code != 0:
        return out
    code, out = _tool("factory-registry.py", "check")
    if code != 0:
        return out
    code, out = _tool("factory-artifact.py", "check", args.input)
    if code != 0:
        return out

    graph_tbl, nodes, _edges = _load_graph(args.graph)
    names = {n.get("name") for n in nodes}

    # FA16: a tool node's command argv[0] must be a path under tools/factory/seat/
    # (FA14 Interface 1). factory-graph.py's closed fault list names no command
    # fault, so the runner refuses it here — exit 2, before anything is written.
    # --dry-run never executes a command, so the check is skipped for the stub.
    if not args.dry_run:
        for node in nodes:
            if node.get("type") != "tool":
                continue
            command = node.get("command")
            if not isinstance(command, list) or not command:
                continue
            argv0 = command[0]
            if isinstance(argv0, str) and not argv0.startswith("tools/factory/seat/"):
                return (
                    f"run: tool {node.get('name')}: command argv[0] not under "
                    "tools/factory/seat/\n"
                )

    if args.start is not None and args.start not in names:
        return f"run: --start {args.start}: no such node\n"

    # FA17: a gate node re-reads its plan from `--plan`, so a non-dry-run graph
    # carrying a gate without a `--plan` is refused before anything is written.
    if not args.dry_run and args.plan is None:
        for node in nodes:
            if node.get("type") == "gate":
                return f"run: gate {node.get('name')}: --plan required\n"

    with open(args.input, encoding="utf-8") as fh:
        doc = json.load(fh)
    ik = graph_tbl.get("input_kind")
    if isinstance(ik, str):
        allowed = {ik}
    elif isinstance(ik, list):
        allowed = set(ik)
    else:
        allowed = None
    if allowed is not None and doc.get("kind") not in allowed:
        return f"run: input kind {doc.get('kind')!r} not in graph.input_kind\n"

    return None


# ---------------------------------------------------------------------------
# the walk
# ---------------------------------------------------------------------------


def _exhausted_edge(edges, current):
    for e in edges:
        if e.get("from") == current and e.get("when") == "exhausted":
            return e
    return None


def _nearest_refusal(edges, current, types):
    adjacency = {}
    for e in edges:
        adjacency.setdefault(e.get("from"), []).append(e.get("to"))
    seen = set()
    queue = [current]
    while queue:
        cur = queue.pop(0)
        if cur in seen:
            continue
        seen.add(cur)
        if cur != current and types.get(cur) == "refusal":
            return cur
        for nxt in adjacency.get(cur, []):
            if nxt not in seen:
                queue.append(nxt)
    return None


class _Run:
    """One walk's mutable state."""

    def __init__(self, args):
        self.args = args
        self.run_dir = Path(args.run)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.graph_tbl, self.nodes, self.edges = _load_graph(args.graph)
        self.by_name = {n.get("name"): n for n in self.nodes}
        self.types = {n.get("name"): n.get("type") for n in self.nodes}
        self.rungs = {n.get("name"): n.get("rung") for n in self.nodes}

        self.budget = {}
        for e in self.edges:
            self.budget[f"{e.get('from')}->{e.get('to')}"] = e.get("budget")

        self.stub_verdicts = []
        if args.stub_verdicts:
            self.stub_verdicts = args.stub_verdicts.split(",")
        self.stub_index = 0

        with open(self.run_dir / "run.json", "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "plan": args.plan,
                    "graph": args.graph,
                    "input": args.input,
                    "start": args.start
                    if args.start is not None
                    else self.graph_tbl.get("start"),
                },
                fh,
                sort_keys=True,
            )
            fh.write("\n")
        self.write_budgets()

        self.journal_path = self.run_dir / "journal.jsonl"
        self.journal_entries = []
        self.path = []
        self.step = 1
        self.last_artifact = {}

    def journal_line(self, entry):
        self.journal_entries.append(json.dumps(entry, sort_keys=True) + "\n")

    def flush_journal(self):
        with open(self.journal_path, "w", encoding="utf-8") as fh:
            fh.writelines(self.journal_entries)

    def write_budgets(self):
        with open(self.run_dir / "budgets.json", "w", encoding="utf-8") as fh:
            json.dump(self.budget, fh, sort_keys=True)
            fh.write("\n")

    def next_stub(self):
        if self.stub_index < len(self.stub_verdicts):
            v = self.stub_verdicts[self.stub_index]
            self.stub_index += 1
            return v
        return "ok"

    def write_artifact(self, node, artifact):
        art_path = self.run_dir / f"{self.step}-{node}.json"
        art_path.write_text(json.dumps(artifact, sort_keys=True) + "\n")
        return art_path

    def input_field(self, current, current_input):
        node = self.by_name[current]
        if "input_from" not in node:
            return current_input
        val = node["input_from"]
        if isinstance(val, list):
            return [self.last_artifact.get(v, "") for v in val]
        return self.last_artifact.get(val, current_input)


def run(args):
    r = _Run(args)
    current = args.start if args.start is not None else r.graph_tbl.get("start")
    current_input = args.input
    edge_into = None
    edge_when = None
    budget_left = None

    while True:
        # the hard step cap: exceeding it flushes the (partial) journal, prints
        # the step-limit message and exits 3, grouped with the other mid-run
        # refusals (DIR and a partial journal already exist by now).
        if r.step > MAX_STEPS:
            r.journal_line(
                {
                    "step": r.step,
                    "node": current,
                    "type": r.types[current],
                    "rung": r.rungs[current],
                    "edge": edge_into,
                    "when": edge_when,
                    "budget_left": budget_left,
                    "input": None,
                    "artifact": (
                        f"run: step limit ({MAX_STEPS}) exceeded — "
                        "the graph is not terminating"
                    ),
                }
            )
            r.flush_journal()
            print(
                f"run: step limit ({MAX_STEPS}) exceeded — the graph is not terminating"
            )
            return 3

        node_type = r.types[current]
        node_rung = r.rungs[current]

        # --max-rung refuses the node: skip it and treat the input as exhausted.
        # A refusal is always runnable (it writes the terminal "exhausted"
        # artifact), so the cap only applies to agent/tool/gate nodes.
        if (
            args.max_rung is not None
            and node_rung > args.max_rung
            and node_type != "refusal"
        ):
            target = _exhausted_edge(r.edges, current)
            if target is not None:
                key = f"{current}->{target.get('to')}"
                r.budget[key] -= 1
                r.write_budgets()
                edge_into = key
                edge_when = target.get("when")
                budget_left = r.budget[key]
                current = target.get("to")
            else:
                target = _nearest_refusal(r.edges, current, r.types)
                edge_into = None
                edge_when = None
                budget_left = None
                if target is None:
                    r.flush_journal()
                    print(" → ".join(r.path))
                    return 0
                current = target
            continue

        input_field = r.input_field(current, current_input)

        verdict = None
        if node_type != "refusal":
            verdict = r.next_stub()
        executor = executor_for(node_type, args.dry_run)
        try:
            artifact = executor(
                r.by_name[current], node_rung, verdict, input_field, r.run_dir
            )
        except _SeatUnavailable:
            # factory-task --node refused (exit 2): a seat-less run is a mid-run
            # refusal, reported as exit 3 with the journal line below.
            r.journal_line(
                {
                    "step": r.step,
                    "node": current,
                    "type": node_type,
                    "rung": node_rung,
                    "edge": edge_into,
                    "when": edge_when,
                    "budget_left": budget_left,
                    "input": input_field,
                    "artifact": f"run: {current}: seat unavailable",
                }
            )
            r.flush_journal()
            print(" → ".join(r.path + [current]))
            return 3

        art_path = r.write_artifact(current, artifact)

        code, out = _tool("factory-artifact.py", "check", str(art_path))
        if code != 0:
            entry = {
                "step": r.step,
                "node": current,
                "type": node_type,
                "rung": node_rung,
                "edge": edge_into,
                "when": edge_when,
                "budget_left": budget_left,
                "input": input_field,
                "artifact": f"run: {current}: artifact refused: {out.strip()}",
            }
            r.journal_line(entry)
            r.flush_journal()
            print(" → ".join(r.path + [current]))
            return 3

        entry = {
            "step": r.step,
            "node": current,
            "type": node_type,
            "rung": node_rung,
            "edge": edge_into,
            "when": edge_when,
            "budget_left": budget_left,
            "input": input_field,
            "artifact": str(art_path),
        }
        r.journal_line(entry)
        r.path.append(current)
        r.last_artifact[current] = str(art_path)

        # a refusal node's real (non-dry-run) escalation appends its paragraph
        # and launch line raw after its JSON event, so a real refusal's journal
        # ends on the launch: line (Interface 5). The dry-run stub keeps one
        # JSON line per node (90-graph-runner (f)), and a refusal does NOT end
        # the walk here -- a cyclic refusal graph still runs to the step cap
        # (90-graph-runner (q)).
        if node_type == "refusal" and not r.args.dry_run:
            key = artifact.get("key")
            seed_path = Path(r.args.input) if r.args.input else None
            if seed_path is not None:
                try:
                    with open(seed_path, encoding="utf-8") as fh:
                        key = json.load(fh).get("key", key)
                except (OSError, json.JSONDecodeError):
                    pass
            escalate = Path(r.run_dir) / f"{key}.escalate"
            if escalate.exists():
                for line in escalate.read_text().splitlines():
                    r.journal_entries.append(line + "\n")

        # a gate that approves is terminal ("ok at a gate is terminal"); a
        # node marked terminal = true ends the walk on ok exactly the same way
        # (the graph's real success terminus, e.g. plan.toml's stage).
        if (node_type == "gate" or r.by_name[current].get("terminal")) and artifact.get(
            "verdict"
        ) == "ok":
            r.flush_journal()
            print(" → ".join(r.path))
            return 0

        # choose the outgoing edge by the artifact's verdict, in file order.
        take = None
        for e in r.edges:
            if e.get("from") != current:
                continue
            when = e.get("when")
            if when != "any" and when != artifact.get("verdict"):
                continue
            key = f"{current}->{e.get('to')}"
            if r.budget.get(key, 0) > 0:
                take = e
                break
        if take is not None:
            key = f"{current}->{take.get('to')}"
            r.budget[key] -= 1
            r.write_budgets()
            edge_into = key
            edge_when = take.get("when")
            budget_left = r.budget[key]
            current_input = str(art_path)
            current = take.get("to")
            r.step += 1
            continue

        # exhaustion: the node's exhausted edge, else the nearest refusal.
        exhausted = _exhausted_edge(r.edges, current)
        if exhausted is not None:
            key = f"{current}->{exhausted.get('to')}"
            r.budget[key] -= 1
            r.write_budgets()
            edge_into = key
            edge_when = exhausted.get("when")
            budget_left = r.budget[key]
            current_input = str(art_path)
            current = exhausted.get("to")
            r.step += 1
            continue
        target = _nearest_refusal(r.edges, current, r.types)
        if target is not None and target != current:
            edge_into = None
            edge_when = None
            budget_left = None
            current_input = str(art_path)
            current = target
            r.step += 1
            continue
        # no refusal reachable: terminal at this node.
        r.flush_journal()
        print(" → ".join(r.path))
        return 0


def main(argv):
    parser = argparse.ArgumentParser(prog="factory-run.py")
    parser.add_argument("graph")
    parser.add_argument("--input", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stub-verdicts", default=None)
    parser.add_argument("--max-rung", type=int, default=None)
    parser.add_argument("--start", default=None)
    parser.add_argument("--plan", default=None)
    parse = parser.parse_args(argv)

    refusal = preflight(parse)
    if refusal is not None:
        sys.stdout.write(refusal)
        return 2

    return run(parse)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
