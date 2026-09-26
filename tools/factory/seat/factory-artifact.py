#!/usr/bin/env python3
"""factory-artifact.py -- the node artifact and its checker.

A machine-readable artifact between graph nodes (decision 32a): JSON with a
``kind`` enum, a ``key``, the producing ``node`` and its ``rung``, ``claims[]``
(each ``text``/``command``/``citation``), ``repro`` (command/expected/observed
or null), ``errata[]``, a ``verdict``, ``inputs`` (a name -> repository-relative
path object) and ``scores`` (null or exactly 14 integers 0-3 in rubric-row
order) / ``wrong_facts``. ``write`` validates only ``verdict`` (FA14b) -- a
bad ``kind``, a claim without a ``command`` or a wrong-length ``scores`` still
reach stdout and ``check`` refuses the result (FA14b's Opus gate, minor 3:
carried from FA14 and closed this round for ``verdict`` alone); ``check``
refuses an unsound artifact with ``artifact <file>: <field>: <fault>`` and
exit 2; an absent or non-JSON file is ``artifact <file>: unreadable: <message>``.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys

KINDS = frozenset({"input", "attempt", "verdict", "reresolve", "escalation"})
VERDICTS = frozenset({"ok", "broken", "rework", "reject", "exhausted"})
CITATION_RE = re.compile(r"^$|^[^:\s]+:\d+(-\d+)?$")
# plan.js's floor rows, 0-based (rows 2, 3, 5, 6, 7, 13) -- the six rows that
# account for the plan-caused rejections. Assumption 25 / .claude/workflows/plan.js.
FLOOR_ROWS = (1, 2, 4, 5, 6, 12)
TALLY_THRESHOLD = 34
REQUIRED = (
    "kind",
    "key",
    "node",
    "rung",
    "claims",
    "repro",
    "errata",
    "verdict",
    "inputs",
    "scores",
    "wrong_facts",
)


def _fault(path, field, msg):
    return f"artifact {path}: {field}: {msg}"


def _good_inputs(val):
    if not isinstance(val, dict):
        return False
    return all(isinstance(v, str) for v in val.values())


def check_artifact(path):
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except OSError as exc:
        return [_fault(path, "unreadable", f"{exc.strerror or exc}")]
    except json.JSONDecodeError as exc:
        return [_fault(path, "unreadable", f"{exc}")]

    if not isinstance(doc, dict):
        return [_fault(path, "unreadable", "not an object")]

    faults = []
    for field in REQUIRED:
        if field not in doc:
            faults.append(_fault(path, field, "missing"))

    if "kind" in doc and doc.get("kind") not in KINDS:
        faults.append(_fault(path, "kind", "bad kind"))

    verdict = doc.get("verdict")
    if verdict is not None and verdict not in VERDICTS:
        faults.append(_fault(path, "verdict", "bad verdict"))

    repro = doc.get("repro")
    if repro is not None and not isinstance(repro, dict):
        faults.append(_fault(path, "repro", "bad repro"))

    claims = doc.get("claims")
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            command = claim.get("command")
            if not isinstance(command, str) or command == "":
                faults.append(_fault(path, "claims", "claim without command"))
            citation = claim.get("citation")
            if not isinstance(citation, str) or not CITATION_RE.match(citation):
                faults.append(_fault(path, "citation", "bad citation"))

    inputs = doc.get("inputs")
    if "inputs" in doc and not _good_inputs(inputs):
        faults.append(_fault(path, "inputs", "bad inputs"))

    scores = doc.get("scores")
    if scores is not None:
        if not isinstance(scores, list):
            faults.append(_fault(path, "scores", "bad score"))
        elif len(scores) != 14:
            faults.append(_fault(path, "scores", "wrong row count"))
        else:
            for score in scores:
                if not isinstance(score, int) or isinstance(score, bool):
                    faults.append(_fault(path, "scores", "bad score"))
                elif score < 0 or score > 3:
                    faults.append(_fault(path, "scores", "score out of range"))

    wrong_facts = doc.get("wrong_facts")
    if wrong_facts is not None and (
        not isinstance(wrong_facts, int)
        or isinstance(wrong_facts, bool)
        or wrong_facts < 0
    ):
        faults.append(_fault(path, "wrong_facts", "bad score"))

    if doc.get("kind") == "escalation":
        if "attempts" not in doc or doc.get("attempts") is None:
            faults.append(_fault(path, "attempts", "missing"))
        if "design_failure" not in doc:
            faults.append(_fault(path, "design_failure", "missing"))
        elif doc.get("design_failure") is not True:
            faults.append(_fault(path, "design_failure", "must be true"))

    return faults


def write_artifact(args):
    if args.verdict is not None and args.verdict not in VERDICTS:
        print(
            f"artifact write: verdict: bad verdict: {args.verdict}",
            file=sys.stderr,
        )
        return 2
    claims = []
    for claim in args.claim:
        text, command, citation = claim.split("::")
        claims.append({"text": text, "command": command, "citation": citation})
    repro = None
    if args.repro is not None:
        command, expected, observed = args.repro.split("::")
        repro = {"command": command, "expected": expected, "observed": observed}
    inputs = {}
    for item in args.input:
        name, _, value = item.partition("=")
        inputs[name] = value
    scores = None
    if args.scores is not None:
        scores = [int(x) for x in args.scores.split(",")]
    wrong_facts = None
    if args.wrong_facts is not None:
        wrong_facts = int(args.wrong_facts)
    doc = {
        "kind": args.kind,
        "key": args.key,
        "node": args.node,
        "rung": args.rung,
        "claims": claims,
        "repro": repro,
        "errata": [],
        "verdict": args.verdict,
        "inputs": inputs,
        "scores": scores,
        "wrong_facts": wrong_facts,
    }
    if args.kind == "escalation":
        doc["attempts"] = args.attempts
        doc["design_failure"] = True
    print(json.dumps(doc, sort_keys=True))
    return 0


def get_field(args):
    try:
        with open(args.file, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"artifact {args.file}: unreadable: {getattr(exc, 'strerror', exc)}",
            file=sys.stderr,
        )
        return 2
    if args.field not in doc:
        print(f"{args.file}: no field {args.field}", file=sys.stderr)
        return 1
    print(json.dumps(doc.get(args.field)))
    return 0


def tally(paths):
    """The plan panel's mechanical tally (decision 31a; plan.js's rule, no other).

    Reads three scored `verdict` artifacts, takes the median of the three per
    row, sums the fourteen medians, and prints a `verdict` artifact: `scores`
    is the medians, `errata` the three `errata[]` concatenated, `inputs` the
    first judge's (so `inputs.draft` travels to the revision), and `verdict`
    is `reject` when any judge's row 2 (correct facts, `scores[1]`) is 0; else
    `ok` when the total is >= 34 and every floor row (2, 3, 5, 6, 7, 13) has a
    median >= 2; else `rework`. Exit 2 with `tally: need 3 scored artifacts,
    got N` on fewer than three paths, on one `check` refuses, or on one whose
    `scores` is null.
    """
    if len(paths) != 3:
        print(f"tally: need 3 scored artifacts, got {len(paths)}", file=sys.stderr)
        return 2
    docs = []
    for path in paths:
        faults = check_artifact(path)
        if faults:
            print(f"tally: {path}: {faults[0]}", file=sys.stderr)
            return 2
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if doc.get("scores") is None:
            print(f"tally: {path}: no scores", file=sys.stderr)
            return 2
        docs.append(doc)

    medians = []
    for i in range(14):
        vals = sorted(d["scores"][i] for d in docs)
        medians.append(vals[1])
    total = sum(medians)

    if any(d["scores"][1] == 0 for d in docs):
        verdict = "reject"
    elif total >= TALLY_THRESHOLD and all(medians[i] >= 2 for i in FLOOR_ROWS):
        verdict = "ok"
    else:
        verdict = "rework"

    errata = []
    for d in docs:
        e = d.get("errata")
        if isinstance(e, list):
            errata.extend(e)

    out = {
        "kind": "verdict",
        "key": docs[0].get("key"),
        "node": os.environ.get("FACTORY_NODE", "tally"),
        "rung": int(os.environ.get("FACTORY_RUNG", "1")),
        "claims": [],
        "repro": None,
        "errata": errata,
        "verdict": verdict,
        "inputs": docs[0].get("inputs") or {},
        "scores": medians,
        "wrong_facts": sum(d.get("wrong_facts") or 0 for d in docs),
    }
    print(json.dumps(out, sort_keys=True))
    return 0


def stage(args):
    """The staging copy (decision 64a/65a): copy the draft to the plan-drafts tree.

    Copies the file the input's `inputs.draft` names to
    `DIR/<YYYY-MM-DD>-<key>.md` and prints a `verdict` artifact `ok` whose
    `inputs.staged` names that path. `--under` must normalise to
    `docs/reviews/plan-drafts` (the rule factory-plan-brief.sh applies to its
    `out`), so nothing here can write `docs/superpowers/plans/`; a different
    directory exits 2 with `stage: --under must be docs/reviews/plan-drafts`,
    and a missing `inputs.draft` exits 2 with `stage: no draft in inputs`.
    """
    under = os.path.realpath(args.under)
    expected = os.path.realpath(
        os.path.join(os.getcwd(), "docs", "reviews", "plan-drafts")
    )
    if under != expected:
        print("stage: --under must be docs/reviews/plan-drafts", file=sys.stderr)
        return 2
    try:
        with open(args.input, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"artifact {args.input}: unreadable: {getattr(exc, 'strerror', exc)}",
            file=sys.stderr,
        )
        return 2
    draft = (doc.get("inputs") or {}).get("draft")
    if not draft:
        print("stage: no draft in inputs", file=sys.stderr)
        return 2
    key = doc.get("key", "plan")
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    dest = os.path.join(under, f"{today}-{key}.md")
    shutil.copy(draft, dest)
    out = {
        "kind": "verdict",
        "key": key,
        "node": os.environ.get("FACTORY_NODE", "stage"),
        "rung": int(os.environ.get("FACTORY_RUNG", "1")),
        "claims": [],
        "repro": None,
        "errata": [],
        "verdict": "ok",
        "inputs": {"staged": dest},
        "scores": None,
        "wrong_facts": None,
    }
    print(json.dumps(out, sort_keys=True))
    return 0


def main(argv):
    parser = argparse.ArgumentParser(prog="factory-artifact.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    check_p = sub.add_parser("check")
    check_p.add_argument("file")

    write_p = sub.add_parser("write")
    write_p.add_argument("kind")
    write_p.add_argument("--key", required=True)
    write_p.add_argument("--node", required=True)
    write_p.add_argument("--rung", required=True, type=int)
    write_p.add_argument("--claim", action="append", default=[])
    write_p.add_argument("--verdict", default=None)
    write_p.add_argument("--input", action="append", default=[])
    write_p.add_argument("--scores", default=None)
    write_p.add_argument("--wrong-facts", default=None)
    write_p.add_argument("--attempts", type=int, default=None)
    write_p.add_argument("--repro", default=None)

    get_p = sub.add_parser("get")
    get_p.add_argument("file")
    get_p.add_argument("field")

    tally_p = sub.add_parser("tally")
    tally_p.add_argument("files", nargs="+")

    stage_p = sub.add_parser("stage")
    stage_p.add_argument("--under", required=True)
    stage_p.add_argument("input")

    args = parser.parse_args(argv)

    if args.cmd == "check":
        faults = check_artifact(args.file)
        if faults:
            print("\n".join(faults))
            return 2
        return 0
    if args.cmd == "write":
        return write_artifact(args)
    if args.cmd == "get":
        return get_field(args)
    if args.cmd == "tally":
        return tally(args.files)
    if args.cmd == "stage":
        return stage(args)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
