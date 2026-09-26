"""patterns.py — check the planning-pattern docs against the outcomes ledger.

The grammar (C-DOC), the exemplar verdicts (C-OUTCOMES) and the mechanical
predicates' discrimination rates are checked per step of the six planning
patterns; slices of the plan sections are taken per C-SLICE.
"""

import argparse
import dataclasses
import json
import os
import re
import sys

import streams
import tasks

STEPS = ("facts", "interfaces", "steps", "tests", "graph", "operator-dispatch")

# fmt: off
SECTIONS = ("## Rules", "## Exemplars", "## Anti-patterns", "## Checklist", "## Predicates", "## Sources")
# fmt: on

GRAPH_FIELDS = (
    "**dependsOn:**",
    "**touches:**",
    "**areas:**",
    "**acceptance:**",
    "**repo:**",
)
REVIEW_PREFIX = "docs/reviews/"
PLAN_SECTIONS = {
    "graph": ("## Waves",),
    "operator-dispatch": ("## Operator", "## Dispatch"),
}
GAP_DEFAULT = 15
MIN_ROWS_DEFAULT = 10
DOC_CLASSES = tuple(c for c in streams.PLAN_DEFECTS if c != "none")
OUTCOME_FIELDS = (
    "gate_ts",
    "heading",
    "key",
    "kind",
    "plan",
    "plan_defect",
    "review_path",
    "size",
    "touches_n",
    "verdict",
)

LABEL_RE = re.compile(r"^\*\*([A-Z][A-Za-z]*)\b[^*]*\*\*")
LEGACY_STEP_RE = re.compile(r"^- \[ \] \*\*Step ")
TERMINATOR_RE = re.compile(r"^\*\*(probes|record):\*\*")
EXEMPLAR_RE = re.compile(r"^### exemplar (?P<key>\S+) [—-] (?P<plan>.+)$")
ANTI_RE = re.compile(
    r"^### anti-pattern (?P<key>\S+) \((?P<cls>[a-z-]+)\) [—-] (?P<plan>.+)$"
)
RULE_RE = re.compile(r"^\d+\. \*\*(?P<name>[^*]+)\*\* [—-] ")
PRED_RE = re.compile(r"^- (?P<name>[^:]+): predicate: (?P<body>.+)$")
ROW_RE = re.compile(r"^row: (.+)$")
AUTHOR_RE = re.compile(r"^author: (.+)$")
REVIEW_RE = re.compile(r"^review: (?P<path>\S+) [—-] (?P<quote>.+)$")
OP_RE = re.compile(r"(?P<field>\S+)\s+(?P<op>==|!=|<=|>=|<|>|in)\s+(?P<value>.+)$")


class PatternsError(Exception):
    """A refusal the CLI reports on stderr with exit 2."""


@dataclasses.dataclass
class Doc:
    rules: list
    exemplars: list
    anti_patterns: list
    predicates: list
    missing: list
    fences: dict


def _regions(body, head_re):
    """Split a section body into (match, text) regions at head_re lines."""
    lines = body.splitlines()
    starts = [
        (i, m) for i, line in enumerate(lines) for m in [head_re.match(line)] if m
    ]
    out = []
    for j, (i, m) in enumerate(starts):
        end = starts[j + 1][0] if j + 1 < len(starts) else len(lines)
        out.append((m, "\n".join(lines[i:end]) + "\n"))
    return out


def _region_parts(region):
    """(blocks, row_line, author, review) of one exemplar region, fence-aware."""
    blocks = []
    cur = None
    in_fence = False
    row_line = None
    author = None
    review = None
    for line in region.splitlines():
        if line.startswith("```"):
            if in_fence:
                blocks.append("\n".join(cur))
                cur = None
            in_fence = not in_fence
            if in_fence:
                cur = []
            continue
        if in_fence and cur is not None:
            cur.append(line)
            continue
        m = ROW_RE.match(line)
        if m:
            row_line = m.group(1)
            continue
        m = AUTHOR_RE.match(line)
        if m:
            author = m.group(1)
            continue
        m = REVIEW_RE.match(line)
        if m:
            review = (m.group("path"), m.group("quote"))
    if in_fence and cur is not None:
        blocks.append("\n".join(cur))
    return blocks, row_line, author, review


def parse_doc(text):
    """Parse a pattern doc: its rules, exemplars, anti-patterns and predicates."""
    heads = [(m.start(), m.group(0)) for m in re.finditer(r"(?m)^## .*$", text)]
    consumed = []
    missing = []
    e = 0
    for start, head in heads:
        if e < len(SECTIONS) and head == SECTIONS[e]:
            consumed.append((start, head))
            e += 1
        elif head in SECTIONS and SECTIONS.index(head) > e:
            missing.extend(SECTIONS[e : SECTIONS.index(head)])
            e = SECTIONS.index(head) + 1
            consumed.append((start, head))
    missing.extend(SECTIONS[e:])
    bodies = {}
    for i, (start, head) in enumerate(consumed):
        end = consumed[i + 1][0] if i + 1 < len(consumed) else len(text)
        bodies[head] = text[start:end]
    d = Doc(
        rules=[],
        exemplars=[],
        anti_patterns=[],
        predicates=[],
        missing=missing,
        fences={},
    )
    if "## Rules" in bodies:
        for line in bodies["## Rules"].splitlines():
            m = RULE_RE.match(line)
            if m:
                d.rules.append((m.group("name"), line))
    if "## Predicates" in bodies:
        for line in bodies["## Predicates"].splitlines():
            m = PRED_RE.match(line)
            if m:
                d.predicates.append((m.group("name"), m.group("body")))
    if "## Exemplars" in bodies:
        for m, region in _regions(bodies["## Exemplars"], EXEMPLAR_RE):
            blocks, row_line, author, _review = _region_parts(region)
            d.exemplars.append(
                (m.group("key"), m.group("plan"), blocks, row_line, author)
            )
            d.fences[m.group("key")] = len(blocks)
    if "## Anti-patterns" in bodies:
        for m, region in _regions(bodies["## Anti-patterns"], ANTI_RE):
            blocks, row_line, author, review = _region_parts(region)
            d.anti_patterns.append(
                (
                    m.group("key"),
                    m.group("plan"),
                    m.group("cls"),
                    blocks,
                    row_line,
                    author,
                    review,
                )
            )
            d.fences[m.group("key")] = len(blocks)
    return d


def section_text(plan_text, heading):
    """The section's lines, from the heading to the next heading at either level."""
    out = []
    on = False
    in_fence = False
    for line in plan_text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            if on:
                out.append(line)
            continue
        if line == heading:
            on = True
            continue
        if on and not in_fence and line.startswith(("### ", "## ")):
            break
        if on:
            out.append(line)
    return "\n".join(out)


def plan_section(plan_text, heading):
    """A plan-level section: from its heading to the next ## at column 0, or EOF."""
    out = []
    on = False
    in_fence = False
    for line in plan_text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            if on:
                out.append(line)
            continue
        if line == heading:
            on = True
            continue
        if on and not in_fence and line.startswith("## "):
            break
        if on:
            out.append(line)
    return "\n".join(out)


def _label_blocks(sec):
    """(label, lines, pos) per block label plus **probes:** runs, fence-aware."""
    lines = sec.splitlines()
    blocks = []
    probes = []
    cur = None
    in_fence = False
    probes_open = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            if cur is not None:
                cur[1].append(line)
            in_fence = not in_fence
            continue
        if not in_fence:
            m = LABEL_RE.search(line)
            if m:
                if cur is not None:
                    blocks.append(cur)
                cur = (m.group(1), [line], i)
                continue
            if TERMINATOR_RE.match(line):
                if cur is not None:
                    blocks.append(cur)
                    cur = None
                probes_open = line.startswith("**probes:**")
                if probes_open:
                    probes.append((i, [line]))
                continue
            if probes_open and line.startswith("- "):
                probes[-1][1].append(line)
                continue
            probes_open = False
        if cur is not None:
            cur[1].append(line)
    if cur is not None:
        blocks.append(cur)
    return blocks, probes


def _legacy_runs(sec):
    """(pos, lines) per run of lines beginning `- [ ] **Step `, fence-aware."""
    lines = sec.splitlines()
    runs = []
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            in_fence = not in_fence
            i += 1
            continue
        if not in_fence and LEGACY_STEP_RE.match(line):
            j = i
            run = []
            while j < len(lines):
                l = lines[j]
                if LEGACY_STEP_RE.match(l) or (run and l[:1] in (" ", "\t")):
                    run.append(l)
                    j += 1
                    continue
                if (
                    l == ""
                    and j + 1 < len(lines)
                    and LEGACY_STEP_RE.match(lines[j + 1])
                ):
                    run.append(l)
                    j += 1
                    continue
                break
            runs.append((i, run))
            i = j
        else:
            i += 1
    return runs


def _field_lines(sec):
    """The section's GRAPH_FIELDS lines at column 0, fence-aware."""
    out = []
    in_fence = False
    for line in sec.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith(GRAPH_FIELDS):
            out.append(line)
    return out


def _join(parts):
    """Concatenate (pos, lines) pieces in file order."""
    parts = sorted(parts, key=lambda t: t[0])
    return "\n".join(ln for _pos, ls in parts for ln in ls)


def _cat(*pieces):
    return "\n".join(p for p in pieces if p)


def _label_slice(sec, want):
    blocks, _probes = _label_blocks(sec)
    parts = [(b[2], b[1]) for b in blocks if b[0] == want]
    return _join(parts)


def _slice_facts(sec, plan_text):
    return _label_slice(sec, "Facts")


def _slice_interfaces(sec, plan_text):
    return _label_slice(sec, "Interfaces")


def _slice_steps(sec, plan_text):
    blocks, _probes = _label_blocks(sec)
    parts = [(b[2], b[1]) for b in blocks if b[0] == "Steps"] + _legacy_runs(sec)
    return _join(parts)


def _slice_tests(sec, plan_text):
    blocks, probes = _label_blocks(sec)
    parts = [(b[2], b[1]) for b in blocks if b[0] in ("Tests", "Mutants")] + probes
    return _join(parts)


def _slice_graph(sec, plan_text):
    waves = plan_section(plan_text, PLAN_SECTIONS["graph"][0])
    return _cat(*_field_lines(sec), waves)


def _slice_operator_dispatch(sec, plan_text):
    pieces = [plan_section(plan_text, h) for h in PLAN_SECTIONS["operator-dispatch"]]
    blocks, _probes = _label_blocks(sec)
    parts = [(b[2], b[1]) for b in blocks if b[0] in ("Relaunch", "Rollback")]
    return _cat(*[p for p in pieces if p], _join(parts))


SLICE_ARMS = {
    "facts": _slice_facts,
    "interfaces": _slice_interfaces,
    "steps": _slice_steps,
    "tests": _slice_tests,
    "graph": _slice_graph,
    "operator-dispatch": _slice_operator_dispatch,
}


def slice(sec, plan_text, step):
    """The section's slice for the step, per C-SLICE."""
    return SLICE_ARMS[step](sec, plan_text)


def _property_value(field, op, value):
    if op == "in":
        if not (value.startswith("{") and value.endswith("}")):
            raise ValueError(value)
        items = [s.strip() for s in value[1:-1].split(",")]
        if field == "touches_n":
            return {int(s) for s in items}
        return set(items)
    if field == "touches_n":
        return int(value)
    return value


def _cmp(a, op, b):
    if op == "==":
        fn = lambda x, y: x == y
    elif op == "!=":
        fn = lambda x, y: x != y
    elif op == "<=":
        fn = lambda x, y: x <= y
    elif op == ">=":
        fn = lambda x, y: x >= y
    elif op == "<":
        fn = lambda x, y: x < y
    elif op == ">":
        fn = lambda x, y: x > y
    else:
        fn = lambda x, y: x in b
    try:
        return fn(a, b)
    except TypeError:
        return False


def predicate_of(body):
    """('regex'|'property'|'none'|'error', payload) of a predicate line's body."""
    if body.startswith("regex:"):
        pat = body[len("regex:") :]
        try:
            rx = re.compile(pat, re.MULTILINE)
        except re.error as e:
            return ("error", f"regex invalid: {e}")
        return ("regex", lambda row, sl: rx.search(sl) is not None)
    if body.startswith("property:"):
        m = OP_RE.match(body[len("property:") :])
        if not m or m.group("field") not in ("touches_n", "size", "kind"):
            return ("error", f"body unparsed: {body}")
        field, op = m.group("field"), m.group("op")
        try:
            value = _property_value(field, op, m.group("value"))
        except ValueError:
            return ("error", f"body unparsed: {body}")

        def match(row, sl):
            val = row.get(field)
            return _cmp(val, op, value)

        return ("property", match)
    if body.startswith("none —") and body.strip() != "none —":
        return ("none", body.strip()[len("none —") :].strip())
    return ("error", f"body unparsed: {body}")


def rates(predicate, population):
    """(a, n, b, m) of a predicate over the landed and rejected sides."""
    landed = []
    rejected = []
    for r, sl in population:
        if not sl.strip():
            continue
        v = r.get("verdict")
        if v == "approved":
            landed.append((r, sl))
        elif v == "rejected":
            rejected.append((r, sl))
    a = sum(1 for r, sl in landed if predicate(r, sl))
    b = sum(1 for r, sl in rejected if predicate(r, sl))
    return a, len(landed), b, len(rejected)


def _pct(x, y):
    return round(100 * x / y) if y else 0


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _ledger_line(row):
    return json.dumps(row, sort_keys=True, ensure_ascii=False)


def _load(outcomes_path, plans_dir, plans):
    """Load the outcomes ledger; every malformation is a refusal (exit 2)."""
    text = _read(outcomes_path)
    rows = []
    rows_by = {}
    for i, line in enumerate(text.splitlines(), 1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            raise PatternsError(f"outcomes line {i}: not a JSON object")
        if not isinstance(obj, dict):
            raise PatternsError(f"outcomes line {i}: not a JSON object")
        for f in OUTCOME_FIELDS:
            if f not in obj:
                raise PatternsError(f"outcomes row {obj.get('key')}: missing field {f}")
        for f in sorted(obj):
            if f not in OUTCOME_FIELDS:
                raise PatternsError(f"outcomes row {obj['key']}: unexpected field {f}")
        k = (obj["plan"], obj["key"])
        if k in rows_by:
            raise PatternsError(f"outcomes row {obj['key']}: duplicate (plan, key)")
        if tasks.chain_root(obj["key"]) != obj["key"]:
            raise PatternsError(f"outcomes row {obj['key']}: not a chain root")
        if not os.path.isfile(os.path.join(plans_dir, obj["plan"])):
            raise PatternsError(
                f"outcomes row {obj['key']}: plan {obj['plan']} not under {plans}"
            )
        rows_by[k] = obj
        rows.append(obj)
    return rows, rows_by


def _require(refusals, cond, msg):
    if cond:
        refusals.append(msg)


def _occurs(block, sl):
    """Does the block occur verbatim (a contiguous run of lines) in the slice?"""
    bl = [ln.rstrip() for ln in block.splitlines()]
    sls = [ln.rstrip() for ln in sl.splitlines()]
    for i in range(len(sls) - len(bl) + 1):
        if sls[i : i + len(bl)] == bl:
            return True
    return False


def _check_fenced(step_refusals, kind, step, key, blocks, sl):
    n = len(blocks)
    if n == 0:
        step_refusals.append(f"{kind} {key} has no fenced block")
    if n > 1:
        step_refusals.append(f"{kind} {key} has {n} fenced blocks, need 1")
    for b in blocks:
        if not b.strip() or not _occurs(b, sl):
            step_refusals.append(f"{kind} {key} text not verbatim in its {step} slice")


def check(root, docs, outcomes, plans, reviews, only, gap, min_rows):
    """Check the pattern docs; returns (refusals, report), both lists of lines."""
    if only is not None:
        for name in only:
            if not name:
                raise PatternsError("--only: empty step name")
            if name not in STEPS:
                raise PatternsError(f"unknown step {name}")
        selected = [s for s in STEPS if s in set(only)]
    else:
        selected = list(STEPS)
    docs_dir = os.path.join(root, docs)
    outcomes_path = os.path.join(root, outcomes)
    plans_dir = os.path.join(root, plans)
    reviews_dir = os.path.join(root, reviews)
    if not os.path.isdir(docs_dir):
        raise PatternsError(f"docs {docs}: not a readable directory")
    if not os.path.isfile(outcomes_path):
        raise PatternsError(f"outcomes {outcomes}: not a readable file")
    if not os.path.isdir(plans_dir):
        raise PatternsError(f"plans {plans}: not a readable directory")
    if not os.path.isdir(reviews_dir):
        raise PatternsError(f"reviews {reviews}: not a readable directory")
    rows, rows_by = _load(outcomes_path, plans_dir, plans)

    # pass 1: populations, before opening any docs
    slices = {}
    populations = {step: [] for step in selected}
    plan_cache = {}
    for r in rows:
        ptext = plan_cache.get(r["plan"])
        if ptext is None:
            ptext = _read(os.path.join(plans_dir, r["plan"]))
            plan_cache[r["plan"]] = ptext
        sec = section_text(ptext, r["heading"])
        for step in selected:
            sl = slice(sec, ptext, step)
            slices[(step, r["plan"], r["key"])] = sl
            populations[step].append((r, sl))
    report = []
    refusals = []
    counts = {}
    for step in selected:
        landed = sum(
            1
            for r, sl in populations[step]
            if r.get("verdict") == "approved" and sl.strip()
        )
        rejected = sum(
            1
            for r, sl in populations[step]
            if r.get("verdict") == "rejected" and sl.strip()
        )
        counts[step] = (landed, rejected)
    for step in selected:
        landed, rejected = counts.get(step, (0, 0))
        report.append(f"{step}: population landed {landed} rejected {rejected}")

    # pass 2: the docs
    rate_lines = []
    none_lines = []
    warn_lines = []
    for step in selected:
        dpath = os.path.join(docs_dir, f"{step}.md")
        if not os.path.isfile(dpath):
            refusals.append(f"patterns: {step}: doc missing")
            continue
        pdoc = parse_doc(_read(dpath))
        step_refusals = []
        for name in pdoc.missing:
            step_refusals.append(f"missing section {name}")
        if len(pdoc.exemplars) < 3:
            step_refusals.append(f"{len(pdoc.exemplars)} exemplars, need 3")
        if len(pdoc.anti_patterns) < 3:
            step_refusals.append(f"{len(pdoc.anti_patterns)} anti-patterns, need 3")
        seen = set()
        for key, plan, blocks, row_line, author in pdoc.exemplars:
            if key in seen:
                step_refusals.append(f"{key} cited twice")
            seen.add(key)
            r = rows_by.get((plan, key))
            if r is None:
                step_refusals.append(f"{key} has no verdict")
                continue
            v = r.get("verdict")
            vr = "null" if v is None else str(v)
            if v != "approved":
                step_refusals.append(f"exemplar {key} verdict {vr}, not approved")
            _check_fenced(
                step_refusals,
                "exemplar",
                step,
                key,
                blocks,
                slices.get((step, plan, key), ""),
            )
            _require(
                step_refusals, row_line is None, f"exemplar {key} has no row: line"
            )
            if row_line is not None and row_line != _ledger_line(r):
                step_refusals.append(
                    f"exemplar {key} row: line differs from the ledger"
                )
            _require(
                step_refusals, author is None, f"exemplar {key} has no author: line"
            )
        for key, plan, cls, blocks, row_line, author, review in pdoc.anti_patterns:
            if key in seen:
                step_refusals.append(f"{key} cited twice")
            seen.add(key)
            r = rows_by.get((plan, key))
            if r is None:
                step_refusals.append(f"{key} has no verdict")
                continue
            v = r.get("verdict")
            vr = "null" if v is None else str(v)
            if v != "rejected":
                step_refusals.append(f"anti-pattern {key} verdict {vr}, not rejected")
            pd = r.get("plan_defect")
            if cls not in DOC_CLASSES:
                step_refusals.append(
                    f"anti-pattern {key} class {cls} not a defect class"
                )
            elif pd is not None and cls != pd:
                step_refusals.append(
                    f"anti-pattern {key} class {cls} differs from plan_defect {pd}"
                )
            elif pd is None:
                warn_lines.append(
                    f"{step} {key}: class {cls} unchecked — plan_defect null"
                )
            _check_fenced(
                step_refusals,
                "anti-pattern",
                step,
                key,
                blocks,
                slices.get((step, plan, key), ""),
            )
            _require(
                step_refusals, row_line is None, f"anti-pattern {key} has no row: line"
            )
            if row_line is not None and row_line != _ledger_line(r):
                step_refusals.append(
                    f"anti-pattern {key} row: line differs from the ledger"
                )
            _require(
                step_refusals, author is None, f"anti-pattern {key} has no author: line"
            )
            _require(
                step_refusals, review is None, f"anti-pattern {key} has no review: line"
            )
            if review is not None:
                v = r.get("review_path")
                rv = "null" if v is None else str(v)
                if not rv.startswith(REVIEW_PREFIX):
                    step_refusals.append(
                        f"anti-pattern {key} review {rv} not under docs/reviews/"
                    )
                else:
                    rel = rv[len(REVIEW_PREFIX) :]
                    full = os.path.realpath(os.path.join(reviews_dir, rel))
                    base = os.path.realpath(reviews_dir)
                    if full != base and not full.startswith(base + os.sep):
                        step_refusals.append(
                            f"anti-pattern {key} review {rv} not under docs/reviews/"
                        )
                    elif not os.path.exists(full):
                        step_refusals.append(f"anti-pattern {key} review {rv} missing")
        for i in range(max(len(pdoc.rules), len(pdoc.predicates))):
            if i >= len(pdoc.predicates):
                step_refusals.append(f"no predicate line for {pdoc.rules[i][0]}")
                continue
            if i >= len(pdoc.rules):
                step_refusals.append(
                    f"predicate line for unknown pattern {pdoc.predicates[i][0]}"
                )
                continue
            if pdoc.rules[i][0] != pdoc.predicates[i][0]:
                step_refusals.append(f"no predicate line for {pdoc.rules[i][0]}")
                step_refusals.append(
                    f"predicate line for unknown pattern {pdoc.predicates[i][0]}"
                )
                continue
            name, body = pdoc.predicates[i]
            p = predicate_of(body)
            if p is None:
                p = ("none", "")
            if p[0] == "error":
                step_refusals.append(f"predicate {name} {p[1]}")
                continue
            if p[0] == "none":
                none_lines.append(f"{step} {name}: predicate none — {p[1]}")
                continue
            a, n, b, m = rates(p[1], populations[step])
            pp = _pct(a, n)
            qq = _pct(b, m)
            d = abs(pp - qq)
            rate_lines.append(
                f"{step} {name}: landed {a}/{n} ({pp}%) "
                f"rejected {b}/{m} ({qq}%) gap {d}"
            )
            if d < gap:
                step_refusals.append(f"predicate {name} gap {d} under {gap}")
            if min(n, m) < min_rows:
                step_refusals.append(
                    f"predicate {name} smaller side {min(n, m)} under {min_rows}"
                )
        step_refusals.sort()
        refusals.extend(f"patterns: {step}: {reason}" for reason in step_refusals)
    report.extend(rate_lines)
    report.extend(none_lines)
    report.extend(warn_lines)
    return refusals, report


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="patterns", description="Check the planning-pattern docs."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser(
        "check", help="check the pattern docs against the outcomes ledger"
    )
    p.add_argument("--root", required=True)
    p.add_argument("--docs", default="docs/planning")
    p.add_argument("--outcomes", default="docs/ledger/plan-outcomes.jsonl")
    p.add_argument("--plans", default="docs/superpowers/plans")
    p.add_argument("--reviews", default="docs/reviews")
    p.add_argument("--only")
    p.add_argument("--gap", type=int, default=GAP_DEFAULT)
    p.add_argument("--min-rows", type=int, default=MIN_ROWS_DEFAULT)
    try:
        args = parser.parse_args(argv)
        only = None
        if args.only is not None:
            only = [s.strip() for s in args.only.split(",")]
        refusals, report = check(
            args.root,
            args.docs,
            args.outcomes,
            args.plans,
            args.reviews,
            only,
            args.gap,
            args.min_rows,
        )
        for line in report:
            print(line)
        for line in refusals:
            print(line)
        return 1 if refusals else 0
    except (PatternsError, OSError) as e:
        print(f"patterns: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
