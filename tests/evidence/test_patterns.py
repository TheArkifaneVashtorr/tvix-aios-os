"""patterns.py tests (plan 2026-09-22-planning-patterns, PT10)."""

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "patterns.py",
        pathlib.Path("pkgs/evidence/patterns.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))  # Facts 5: import streams / import tasks
    spec = importlib.util.spec_from_file_location("patterns", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["patterns"] = mod
    spec.loader.exec_module(mod)
    return mod, src


pt, SRC = load()

DOCS = "docs/planning"
OUTCOMES = "docs/ledger/plan-outcomes.jsonl"
PLANS = "docs/superpowers/plans"
REVIEWS = "docs/reviews"
RULES = ("p1", "p2", "p3")
PREDS = (
    ("p1", "regex:MARKER"),
    ("p2", "none — prose reason one"),
    ("p3", "none — prose reason two"),
)


def cli(root, *args, env=None):
    return subprocess.run(
        [sys.executable, str(SRC), "check", "--root", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def run_check(root, only=None, **over):
    kw = {
        "docs": DOCS,
        "outcomes": OUTCOMES,
        "plans": PLANS,
        "reviews": REVIEWS,
        "only": only,
        "gap": pt.GAP_DEFAULT,
        "min_rows": pt.MIN_ROWS_DEFAULT,
    }
    kw.update(over)
    return pt.check(str(root), **kw)


# --- fixture builders: one payload per rule, each defaulting to a passing shape


def block(step, marker):
    content = "MARKER" if marker else "plain"
    if step == "graph":
        return f"**touches:** {content}\n"
    if step == "operator-dispatch":
        return f"**Relaunch:**\n\n{content}\n"
    return f"**{step.capitalize()}.**\n\n{content}\n"


def section(key, step, marker=True):
    return f"### {key} (code, S) — t\n\n{block(step, marker)}"


def write_plan(root, name, *sections_, waves=None, operator=None, dispatch=None):
    p = root / PLANS / name
    p.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(s + "\n" for s in sections_)
    if waves is not None:
        text += f"## Waves\n\n{waves}\n"
    if operator is not None:
        text += f"## Operator\n\n{operator}\n"
    if dispatch is not None:
        text += f"## Dispatch\n\n{dispatch}\n"
    p.write_text(text, encoding="utf-8")


def row(key="K1", plan_="p.md", **over):
    r = {
        "key": key,
        "plan": plan_,
        "heading": f"### {key} (code, S) — t",
        "kind": "code",
        "size": "S",
        "touches_n": 2,
        "verdict": "approved",
        "plan_defect": None,
        "review_path": None,
        "gate_ts": "2026-09-05T00:00:00Z",
    }
    r.update(over)
    return r


def rline(r):
    return json.dumps(r, sort_keys=True, ensure_ascii=False)


def write_ledger(root, rows):
    p = root / OUTCOMES
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(rline(r) + "\n" for r in rows), encoding="utf-8")


def review(root, rel="docs/reviews/r.md"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# review\n", encoding="utf-8")


def corpus(root, step, landed=12, rejected=12, marker_of=None):
    rows = []
    for i in range(landed):
        key, name = f"L{i:02d}", f"{step}-{i:02d}.md"
        marker = marker_of(i) if marker_of else True
        write_plan(root, name, section(key, step, marker=marker))
        rows.append(row(key=key, plan_=name))
    for j in range(rejected):
        key, name = f"R{j:02d}", f"{step}-r{j:02d}.md"
        write_plan(root, name, section(key, step, marker=False))
        rows.append(
            row(
                key=key,
                plan_=name,
                verdict="rejected",
                plan_defect="vacuous",
                review_path="docs/reviews/r.md",
            )
        )
    review(root)
    return rows


def tree(tmp_path, step="facts", **kw):
    root = tmp_path / "t"
    (root / DOCS).mkdir(parents=True, exist_ok=True)
    rows = corpus(root, step, **kw)
    write_ledger(root, rows)
    return root, rows


def write_doc(root, step, text):
    (root / DOCS).mkdir(parents=True, exist_ok=True)
    (root / DOCS / f"{step}.md").write_text(text, encoding="utf-8")


def espec(r, **over):
    s = {"r": r}
    s.update(over)
    return s


def aspec(r, **over):
    s = {"r": r}
    s.update(over)
    return s


def _fences(s, step):
    nf = s.get("fences", 1)
    tag = s.get("tag", "text")
    block_text = s.get("block")
    if block_text is None:
        block_text = block(step, s["r"].get("verdict") == "approved")
    parts = []
    if nf >= 1:
        parts.append(f"```{tag}\n{block_text}```\n")
    if nf >= 2:
        parts.append(f"```{tag}\n{block_text}```\n")
    return "".join(parts)


def _region(step, s, kind):
    r = s["r"]
    key = s.get("key", r["key"])
    pname = s.get("plan_name", r["plan"])
    sep = "-" if s.get("dash") else "—"
    if kind == "exemplar":
        head = f"### exemplar {key} {sep} {pname}"
    else:
        cls = s.get("cls", r.get("plan_defect") or "vacuous")
        head = f"### anti-pattern {key} ({cls}) {sep} {pname}"
    lines = [head, ""]
    lines.append(_fences(s, step))
    if not s.get("omit_row"):
        lines.append(f"row: {s.get('row_line', rline(r))}")
    if not s.get("omit_author"):
        lines.append("author: fable")
    if kind == "anti" and not s.get("omit_review"):
        rp = s.get("review_path", r.get("review_path"))
        rp = "null" if rp is None else rp
        lines.append(f'review: {rp} — "one sentence"')
    return "\n".join(lines) + "\n"


def doc(
    step,
    rows,
    exemplars=None,
    antis=None,
    rule_names=RULES,
    preds=PREDS,
    secs=None,
    suffix="",
):
    if exemplars is None:
        exemplars = [espec(r) for r in rows[:3]]
    if antis is None:
        antis = [aspec(r) for r in rej(rows)[:3]]
    if secs is None:
        secs = list(pt.SECTIONS)
    out = []
    rules_text = "\n".join(
        f"{i}. **{name}** — rule {i}" for i, name in enumerate(rule_names, 1)
    )
    for name in secs:
        out.append(name)
        if name == "## Rules":
            out.append(rules_text)
        elif name == "## Exemplars":
            out.extend(_region(step, s, "exemplar") for s in exemplars)
        elif name == "## Anti-patterns":
            out.extend(_region(step, s, "anti") for s in antis)
        elif name == "## Checklist":
            out.append("- [ ] checked")
        elif name == "## Predicates":
            out.append("\n".join(f"- {n}: predicate: {b}" for n, b in preds))
        elif name == "## Sources":
            out.append("- the outcomes ledger")
        out.append("")
    return "\n".join(out) + suffix


def green(tmp_path):
    root = tmp_path / "g"
    (root / DOCS).mkdir(parents=True, exist_ok=True)
    allrows = []
    for step in pt.STEPS:
        rows = corpus(root, step)
        allrows.extend(rows)
        write_doc(root, step, doc(step, rows))
    write_ledger(root, allrows)
    return root


def rej(rows):
    """The rejected rows of a corpus, in ledger order."""
    return [r for r in rows if r.get("verdict") == "rejected"]


def refu(text):
    """The refusal lines of a stdout, in order."""
    return [ln for ln in text.splitlines() if ln.startswith("patterns: ")]


# --- Table 1: grammar (parse_doc, C-DOC 2-5, 9)


def test_a01_parse_doc_counts(tmp_path):
    _root, rows = tree(tmp_path)
    d = pt.parse_doc(doc("facts", rows))
    assert len(d.rules) == 3
    assert len(d.exemplars) == 3
    assert len(d.anti_patterns) == 3
    assert len(d.predicates) == 3
    assert list(d.missing) == []


def test_a02_missing_checklist_section(tmp_path):
    root, rows = tree(tmp_path)
    secs = [s for s in pt.SECTIONS if s != "## Checklist"]
    write_doc(root, "facts", doc("facts", rows, secs=secs))
    r = cli(root, "--only", "facts")
    assert r.returncode == 1
    assert refu(r.stdout) == ["patterns: facts: missing section ## Checklist"]
    assert r.stderr == ""


def test_a03_predicates_before_checklist(tmp_path):
    root, rows = tree(tmp_path)
    order = list(pt.SECTIONS)
    order[3], order[4] = order[4], order[3]  # Predicates before Checklist
    write_doc(root, "facts", doc("facts", rows, secs=order))
    r = cli(root, "--only", "facts")
    assert r.returncode == 1
    assert refu(r.stdout) == ["patterns: facts: missing section ## Checklist"]


def test_a04_second_rules_heading_is_prose(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(root, "facts", doc("facts", rows, suffix="## Rules\n\nsecond\n"))
    d = pt.parse_doc((root / DOCS / "facts.md").read_text(encoding="utf-8"))
    assert len(d.rules) == 3
    assert len(d.exemplars) == 3
    assert len(d.anti_patterns) == 3
    assert len(d.predicates) == 3
    assert list(d.missing) == []
    r = cli(root, "--only", "facts")
    assert r.returncode == 0


def test_a05_empty_doc(tmp_path):
    root, _rows = tree(tmp_path)
    write_doc(root, "facts", "")
    r = cli(root, "--only", "facts")
    assert r.returncode == 1
    expect = sorted(
        [
            "patterns: facts: 0 exemplars, need 3",
            "patterns: facts: 0 anti-patterns, need 3",
        ]
        + [f"patterns: facts: missing section {s}" for s in pt.SECTIONS]
    )
    assert refu(r.stdout) == expect


def test_a06_two_exemplars_two_antis(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(root, "facts", doc("facts", rows, exemplars=[espec(r) for r in rows[:2]]))
    r = cli(root, "--only", "facts")
    assert "patterns: facts: 2 exemplars, need 3" in refu(r.stdout)
    root, rows = tree(tmp_path)
    write_doc(root, "facts", doc("facts", rows, antis=[aspec(r) for r in rows[-2:]]))
    r = cli(root, "--only", "facts")
    assert "patterns: facts: 2 anti-patterns, need 3" in refu(r.stdout)


def test_a07_fence_counts(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], fences=0)] + [espec(r) for r in rows[1:3]],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == ["patterns: facts: exemplar L00 has no fenced block"]
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], fences=2)] + [espec(r) for r in rows[1:3]],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: exemplar L00 has 2 fenced blocks, need 1"
    ]


def test_a08_empty_block_is_not_a_quotation(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], block="")] + [espec(r) for r in rows[1:3]],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: exemplar L00 text not verbatim in its facts slice"
    ]
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], block="   \n")] + [espec(r) for r in rows[1:3]],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: exemplar L00 text not verbatim in its facts slice"
    ]


def _fenced_quote_tree(tmp_path, tag="text"):
    """E1's Interfaces block contains a fenced code block (T9's hazard)."""
    root = tmp_path / "t"
    (root / DOCS).mkdir(parents=True)
    interior = "**Interfaces.**\n\nL1\n```\nL2\n```\n"
    quote = "**Interfaces.**\n\nL1\n```\nL2\n"
    write_plan(root, "p.md", f"### E1 (code, S) — t\n\n{interior}")
    write_plan(root, "q1.md", section("L01", "interfaces", marker=True))
    write_plan(root, "q2.md", section("L02", "interfaces", marker=True))
    write_plan(root, "r0.md", section("R00", "interfaces", marker=False))
    write_plan(root, "r1.md", section("R01", "interfaces", marker=False))
    write_plan(root, "r2.md", section("R02", "interfaces", marker=False))
    rows = [
        row(key="E1", plan_="p.md"),
        row(key="L01", plan_="q1.md"),
        row(key="L02", plan_="q2.md"),
        row(
            key="R00",
            plan_="r0.md",
            verdict="rejected",
            plan_defect="vacuous",
            review_path="docs/reviews/r.md",
        ),
        row(
            key="R01",
            plan_="r1.md",
            verdict="rejected",
            plan_defect="vacuous",
            review_path="docs/reviews/r.md",
        ),
        row(
            key="R02",
            plan_="r2.md",
            verdict="rejected",
            plan_defect="vacuous",
            review_path="docs/reviews/r.md",
        ),
    ]
    review(root)
    write_ledger(root, rows)
    text = doc(
        "interfaces",
        rows,
        exemplars=[espec(rows[0], block=quote, tag=tag)]
        + [espec(r) for r in rows[1:3]],
        antis=[aspec(r) for r in rows[3:6]],
        preds=[("p1", "none — prose")],
    )
    write_doc(root, "interfaces", text)
    return cli(root, "--only", "interfaces")


def test_a09_quoted_slice_with_interior_fence(tmp_path):
    r = _fenced_quote_tree(tmp_path, tag="text")
    assert r.returncode == 1
    got = refu(r.stdout)
    assert "patterns: interfaces: exemplar E1 has no row: line" in got
    assert (
        "patterns: interfaces: exemplar E1 text not verbatim in its interfaces slice"
        in got
    )


def test_a10_bare_fence_opener_identical(tmp_path):
    r_text = _fenced_quote_tree(tmp_path / "one", tag="text")
    r_bare = _fenced_quote_tree(tmp_path / "two", tag="")
    assert refu(r_text.stdout) == refu(r_bare.stdout)
    assert r_text.returncode == r_bare.returncode


def test_a11_missing_row_author_review_lines(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], omit_row=True)] + [espec(r) for r in rows[1:3]],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == ["patterns: facts: exemplar L00 has no row: line"]
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], omit_author=True)]
            + [espec(r) for r in rows[1:3]],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == ["patterns: facts: exemplar L00 has no author: line"]
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            antis=[
                aspec(rej(rows)[0], omit_review=True),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == ["patterns: facts: anti-pattern R00 has no review: line"]


def test_a12_stale_row_line(tmp_path):
    root, rows = tree(tmp_path)
    stale = rline(rows[0]) + "X"
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], row_line=stale)] + [espec(r) for r in rows[1:3]],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: exemplar L00 row: line differs from the ledger"
    ]


def test_a13_pairing_surplus(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc("facts", rows, preds=[("p1", "none — a"), ("p2", "none — b")]),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == ["patterns: facts: no predicate line for p3"]
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            rule_names=("p1", "p2"),
            preds=[("p1", "none — a"), ("p2", "none — b"), ("p3", "none — c")],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == ["patterns: facts: predicate line for unknown pattern p3"]


def test_a14_pairing_name_mismatch(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            rule_names=("p1", "pX", "p3"),
            preds=[("p1", "none — a"), ("pY", "none — b"), ("p3", "none — c")],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: no predicate line for pX",
        "patterns: facts: predicate line for unknown pattern pY",
    ]
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            rule_names=("p1", "p2", "p3"),
            preds=[("p2", "none — a"), ("p1", "none — b"), ("p3", "none — c")],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: no predicate line for p1",
        "patterns: facts: no predicate line for p2",
        "patterns: facts: predicate line for unknown pattern p1",
        "patterns: facts: predicate line for unknown pattern p2",
    ]


def test_a15_invalid_regex(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc("facts", rows, rule_names=("p",), preds=[("p", "regex:[")]),
    )
    r = cli(root, "--only", "facts")
    assert r.returncode == 1
    assert r.stderr == ""
    assert any(
        ln.startswith("patterns: facts: predicate p regex invalid:")
        for ln in refu(r.stdout)
    )


def test_a16_unparsed_predicate_bodies(tmp_path):
    bodies = [
        "property:author == x",
        "property:size ~~ M",
        "property:touches_n == abc",
        "none —",
        "glob:*.md",
    ]
    root, rows = tree(tmp_path)
    names = ("p1", "p2", "p3", "p4", "p5")
    write_doc(
        root,
        "facts",
        doc("facts", rows, rule_names=names, preds=list(zip(names, bodies))),
    )
    r = cli(root, "--only", "facts")
    assert r.returncode == 1
    assert r.stderr == ""
    for name, body in zip(names, bodies):
        assert f"patterns: facts: predicate {name} body unparsed: {body}" in refu(
            r.stdout
        )


def test_a17_class_none_not_a_defect_class(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            antis=[
                aspec(rej(rows)[0], cls="none"),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: anti-pattern R00 class none not a defect class"
    ]


def test_a18_key_cited_twice(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc("facts", rows, antis=[aspec(rows[0])] + [aspec(r) for r in rows[-2:]]),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout).count("patterns: facts: L00 cited twice") == 1
    # the same key in two different docs is no refusal
    root = tmp_path / "g2"
    (root / DOCS).mkdir(parents=True)
    frows = corpus(root, "facts")
    irows = corpus(root, "interfaces")
    write_ledger(root, frows + irows)
    write_doc(root, "facts", doc("facts", frows))
    write_doc(root, "interfaces", doc("interfaces", irows))
    r = cli(root, "--only", "facts,interfaces")
    assert r.returncode == 0


def test_a19_hyphen_headings_and_slash_keys(tmp_path):
    root = tmp_path / "t"
    (root / DOCS).mkdir(parents=True)
    write_plan(root, "k.md", section("F9/BFIX", "facts", marker=True))
    rows = [row(key="F9/BFIX", plan_="k.md")]
    write_ledger(root, rows)
    text = doc(
        "facts",
        rows,
        exemplars=[espec(rows[0], dash=True)],
        antis=[aspec(rows[0], dash=True)],
        preds=[("p1", "none — prose")],
    )
    d = pt.parse_doc(text)
    assert len(d.exemplars) == 1
    assert d.exemplars[0][0] == "F9/BFIX"
    write_doc(root, "facts", text)
    r = cli(root, "--only", "facts")
    assert "patterns: facts: 0 exemplars, need 3" not in refu(r.stdout)


def test_a20_non_ascii_round_trip(tmp_path):
    def build(tmp):
        root = tmp / "t"
        (root / DOCS).mkdir(parents=True)
        rows = []
        for i in range(3):
            key, name = f"L{i:02d}", f"facts-{i:02d}.md"
            blk = f"**Facts.**\n\nmémorise — é {i}\n"
            heading = f"### {key} (code, S) — tâche é"
            write_plan(root, name, f"{heading}\n\n{blk}")
            rows.append(row(key=key, plan_=name, heading=heading))
        for j in range(3):
            key, name = f"R{j:02d}", f"facts-r{j:02d}.md"
            blk = "**Facts.**\n\nplain — é\n"
            heading = f"### {key} (code, S) — tâche é"
            write_plan(root, name, f"{heading}\n\n{blk}")
            rows.append(
                row(
                    key=key,
                    plan_=name,
                    verdict="rejected",
                    plan_defect="vacuous",
                    review_path="docs/reviews/r.md",
                    heading=heading,
                )
            )
        review(root)
        write_ledger(root, rows)
        text = doc(
            "facts",
            rows,
            exemplars=[
                espec(r, block=f"**Facts.**\n\nmémorise — é {i}\n")
                for i, r in enumerate(rows[:3])
            ],
            antis=[aspec(r, block="**Facts.**\n\nplain — é\n") for r in rows[3:6]],
            rule_names=("pé", "p2", "p3"),
            preds=[
                ("pé", "none — règle é"),
                ("p2", "none — prose"),
                ("p3", "none — prose"),
            ],
        )
        write_doc(root, "facts", text)
        return root

    root = build(tmp_path)
    r_plain = cli(root, "--only", "facts")
    r_c = cli(root, "--only", "facts", env={**os.environ, "LC_ALL": "C"})
    assert r_plain.returncode == 0
    assert r_c.returncode == 0
    assert r_plain.stdout == r_c.stdout
    assert "é" in r_plain.stdout


# --- Table 2: verdicts and the row lookup


def test_a21_exemplar_verdict_must_be_approved(tmp_path):
    root, rows = tree(tmp_path)
    antis = [aspec(r) for r in rej(rows)[:3]]
    rows[0]["verdict"] = "rejected"
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], block=block("facts", True))]
            + [espec(r) for r in rows[1:3]],
            antis=antis,
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: exemplar L00 verdict rejected, not approved"
    ]


def test_a22_verdict_null_rendered_as_null(tmp_path):
    root, rows = tree(tmp_path)
    antis = [aspec(r) for r in rej(rows)[:3]]
    rows[0]["verdict"] = None
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], block=block("facts", True))]
            + [espec(r) for r in rows[1:3]],
            antis=antis,
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: exemplar L00 verdict null, not approved"
    ]


def test_a23_cited_key_with_no_row(tmp_path):
    root, rows = tree(tmp_path)
    ghost = row(key="E9", plan_="ghost.md")
    write_doc(
        root,
        "facts",
        doc("facts", rows, exemplars=[espec(ghost)] + [espec(r) for r in rows[1:3]]),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == ["patterns: facts: E9 has no verdict"]


def test_a24_unknown_and_none_verdicts_excluded(tmp_path):
    root, rows = tree(tmp_path)
    write_plan(root, "x1.md", section("E1", "facts", marker=True))
    write_plan(root, "x2.md", section("E2", "facts", marker=True))
    rows.extend(
        [
            row(key="E1", plan_="x1.md", verdict="unknown"),
            row(key="E2", plan_="x2.md", verdict="none"),
        ]
    )
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(r, block=block("facts", True)) for r in rows[-2:]]
            + [espec(rows[0])],
        ),
    )
    r = cli(root, "--only", "facts")
    assert "patterns: facts: exemplar E1 verdict unknown, not approved" in refu(
        r.stdout
    )
    assert "patterns: facts: exemplar E2 verdict none, not approved" in refu(r.stdout)
    assert "facts: population landed 12 rejected 12" in r.stdout


def test_a25_anti_verdict_must_be_rejected(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(root, "facts", doc("facts", rows))  # rejected: no refusal
    r = cli(root, "--only", "facts")
    assert r.returncode == 0
    bad = rej(rows)[0]
    bad["verdict"] = "approved"
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            antis=[
                aspec(bad, block=block("facts", False)),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: anti-pattern R00 verdict approved, not rejected"
    ]


CLASSES = (
    "vacuous",
    "missing-case",
    "underspecified",
    "wrong-fact",
    "implementer",
    "process",
)


def _class_tree(tmp_path, name, flip=False):
    root = tmp_path / name
    (root / DOCS).mkdir(parents=True)
    antis = []
    for i, c in enumerate(CLASSES):
        key, fname = f"A{i}", f"facts-r{i}.md"
        write_plan(root, fname, section(key, "facts", marker=False))
        antis.append(
            row(
                key=key,
                plan_=fname,
                verdict="rejected",
                plan_defect=c,
                review_path="docs/reviews/r.md",
            )
        )
    landed = []
    for i in range(3):
        key, fname = f"L{i:02d}", f"facts-{i:02d}.md"
        write_plan(root, fname, section(key, "facts", marker=True))
        landed.append(row(key=key, plan_=fname))
    review(root)
    write_ledger(root, antis + landed)
    anti_specs = [aspec(r) for r in antis]
    if flip:
        anti_specs[1] = aspec(antis[1], cls="wrong-fact")
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            landed,
            antis=anti_specs,
            preds=[
                ("p1", "none — prose reason one"),
                ("p2", "none — prose reason two"),
                ("p3", "none — prose reason three"),
            ],
        ),
    )
    return root


def test_a26_class_matches_plan_defect(tmp_path):
    r = cli(_class_tree(tmp_path, "t1"), "--only", "facts")
    assert r.returncode == 0
    r = cli(_class_tree(tmp_path, "t2", flip=True), "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: anti-pattern A1 class wrong-fact differs from plan_defect missing-case"
    ]


def test_a27_plan_defect_null_warns_on_stdout(tmp_path):
    root, rows = tree(tmp_path)
    rej(rows)[0]["plan_defect"] = None
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            antis=[
                aspec(rej(rows)[0], cls="vacuous"),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert r.returncode == 0
    assert (
        "facts R00: class vacuous unchecked — plan_defect null" in r.stdout.splitlines()
    )


def test_a28_review_prefix_and_existence(tmp_path):
    root, rows = tree(tmp_path)
    rej(rows)[0]["review_path"] = "notes/r.md"
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            antis=[
                aspec(rej(rows)[0], review_path="notes/r.md"),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: anti-pattern R00 review notes/r.md not under docs/reviews/"
    ]
    root, rows = tree(tmp_path)
    rej(rows)[0]["review_path"] = "docs/reviews/gone.md"
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            antis=[
                aspec(rej(rows)[0], review_path="docs/reviews/gone.md"),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: anti-pattern R00 review docs/reviews/gone.md missing"
    ]
    root, rows = tree(tmp_path)
    write_doc(root, "facts", doc("facts", rows))
    r = cli(root, "--only", "facts")
    assert r.returncode == 0


def test_a29_review_path_null(tmp_path):
    root, rows = tree(tmp_path)
    rej(rows)[0]["review_path"] = None
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            antis=[
                aspec(rej(rows)[0], review_path=None),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: anti-pattern R00 review null not under docs/reviews/"
    ]


def test_a30_review_path_escapes(tmp_path):
    root, rows = tree(tmp_path)
    rej(rows)[0]["review_path"] = "docs/reviews/../../etc/hosts"
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            antis=[
                aspec(rej(rows)[0], review_path="docs/reviews/../../etc/hosts"),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: anti-pattern R00 review docs/reviews/../../etc/hosts not under docs/reviews/"
    ]
    root, rows = tree(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("# outside\n", encoding="utf-8")
    (root / "docs/reviews").mkdir(parents=True, exist_ok=True)
    os.symlink(outside, root / "docs/reviews" / "out.md")
    rej(rows)[0]["review_path"] = "docs/reviews/out.md"
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            antis=[
                aspec(rej(rows)[0], review_path="docs/reviews/out.md"),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == [
        "patterns: facts: anti-pattern R00 review docs/reviews/out.md not under docs/reviews/"
    ]


def test_a31_reviews_remap_and_default_branch(tmp_path):
    root, rows = tree(tmp_path)
    (root / "other/dir").mkdir(parents=True)
    (root / "other/dir/r.md").write_text("# r\n", encoding="utf-8")
    write_doc(root, "facts", doc("facts", rows))
    r = cli(root, "--only", "facts", "--reviews", "other/dir")
    assert r.returncode == 0
    (root / "other/dir/r.md").unlink()
    r = cli(root, "--only", "facts", "--reviews", "other/dir")
    assert "patterns: facts: anti-pattern R02 review docs/reviews/r.md missing" in refu(
        r.stdout
    )
    r = cli(root, "--only", "facts")  # the default branch, asserted separately
    assert r.returncode == 0


def test_a32_row_lookup_by_plan_and_key(tmp_path):
    root = tmp_path / "t"
    (root / DOCS).mkdir(parents=True)
    write_plan(root, "a.md", "### E1 (code, S) — t\n\n**Facts.**\n\nMARKER-a\n")
    write_plan(root, "b.md", "### E1 (code, S) — t\n\n**Facts.**\n\nMARKER-b\n")
    write_plan(
        root,
        "a2.md",
        section("L00", "facts", marker=True),
        section("L01", "facts", marker=True),
        section("L02", "facts", marker=True),
    )
    write_plan(root, "a3.md", section("R01", "facts", marker=False))
    write_plan(root, "a4.md", section("R02", "facts", marker=False))
    write_plan(root, "a5.md", section("R00", "facts", marker=False))
    rows = [
        row(key="E1", plan_="a.md"),
        row(
            key="E1",
            plan_="b.md",
            verdict="rejected",
            plan_defect="vacuous",
            review_path="docs/reviews/r.md",
        ),
        row(key="L00", plan_="a2.md"),
        row(key="L01", plan_="a2.md"),
        row(key="L02", plan_="a2.md"),
        row(
            key="R00",
            plan_="a5.md",
            verdict="rejected",
            plan_defect="vacuous",
            review_path="docs/reviews/r.md",
        ),
        row(
            key="R01",
            plan_="a3.md",
            verdict="rejected",
            plan_defect="vacuous",
            review_path="docs/reviews/r.md",
        ),
        row(
            key="R02",
            plan_="a4.md",
            verdict="rejected",
            plan_defect="vacuous",
            review_path="docs/reviews/r.md",
        ),
    ]
    review(root)
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[0], block="**Facts.**\n\nMARKER-a\n")]
            + [espec(r) for r in rows[2:5]],
            antis=[aspec(r) for r in rows[5:8]],
            preds=[
                ("p1", "none — prose reason one"),
                ("p2", "none — prose reason two"),
                ("p3", "none — prose reason three"),
            ],
        ),
    )
    r = cli(root, "--only", "facts")
    assert r.returncode == 0
    assert refu(r.stdout) == []


def test_a33_row_not_a_chain_root(tmp_path):
    root, rows = tree(tmp_path)
    write_plan(root, "bad.md", section("CR2", "facts", marker=True))
    rows.append(row(key="CR2r", plan_="bad.md"))
    write_ledger(root, rows)
    write_doc(root, "facts", doc("facts", rows))
    r = cli(root, "--only", "facts")
    assert r.returncode == 2
    assert r.stdout == ""
    assert r.stderr.strip() == "patterns: outcomes row CR2r: not a chain root"


# --- Table 3: the slice (C-SLICE)


def test_a34_section_boundaries():
    text = (
        "### K1 (code, S) — one\n\n**Facts.**\n\nA\n"
        "## Waves\n\nw\n"
        "### K2 (code, S) — two\n\n**Facts.**\n\nB\n"
        "### notes\n\nnot a task\n"
        "### K3 (code, S) — three\n\n**Facts.**\n\nC\n"
    )
    s1 = pt.section_text(text, "### K1 (code, S) — one")
    assert "A" in s1 and "B" not in s1 and "w" not in s1
    s2 = pt.section_text(text, "### K2 (code, S) — two")
    assert "B" in s2 and "not a task" not in s2 and "A" not in s2
    s3 = pt.section_text(text, "### K3 (code, S) — three")
    assert "C" in s3 and "not a task" not in s3


def test_a35_absent_heading_excludes_row(tmp_path):
    root, rows = tree(tmp_path)
    write_plan(root, "facts-00.md", section("Z9", "facts", marker=True))
    write_doc(root, "facts", doc("facts", rows))
    r = cli(root, "--only", "facts")
    assert "facts: population landed 11 rejected 12" in r.stdout.splitlines()


def test_a36_label_spellings_fold():
    spellings = ("**Facts.**", "**Facts:**", "**Facts (planning time):**", "**Facts**")
    for sp in spellings:
        sec = f"{sp}\n\nX\n"
        assert pt.slice(sec, "", "facts") != ""
    sec = "**Relaunch after a death (A6).**\n\nX\n"
    assert pt.slice(sec, "", "facts") == ""
    assert "Relaunch after a death (A6)." in pt.slice(sec, "", "operator-dispatch")


def test_a37_label_in_fence_is_text():
    sec = "**Steps.**\n\n```\n**Facts.**\n```\n"
    s = pt.slice(sec, "", "steps")
    assert "**Facts.**" in s
    assert pt.slice(sec, "", "facts") == ""


def test_a38_indented_label_and_field_lines():
    sec = "**Steps.**\n\n  **Facts.**\n"
    assert "  **Facts.**" in pt.slice(sec, "", "steps")
    assert pt.slice(sec, "", "facts") == ""
    sec2 = "**Facts.**\n\nX\n**dependsOn:** none\n"
    assert "**dependsOn:** none" in pt.slice(sec2, "", "facts")
    assert "**dependsOn:** none" in pt.slice(sec2, "", "graph")


def test_a39_repeated_interfaces_labels():
    sec = "**Interfaces (Produces):**\n\nP\n\n**Interfaces (Consumes):**\n\nC\n"
    assert pt.slice(sec, "", "interfaces") == (
        "**Interfaces (Produces):**\n\nP\n\n**Interfaces (Consumes):**\n\nC"
    )


def test_a40_probes_terminator():
    sec = "**Facts.**\n\nF\n**Tests.**\n\nT\n**probes:**\n- p1: probe\n"
    assert pt.slice(sec, "", "tests") == "**Tests.**\n\nT\n**probes:**\n- p1: probe"
    assert pt.slice(sec, "", "facts") == "**Facts.**\n\nF"


def test_a41_record_terminator():
    sec = "**Facts.**\n\nF\n**record:**\n- b1: cmd\n"
    assert pt.slice(sec, "", "facts") == "**Facts.**\n\nF"


def test_a42_legacy_steps_runs():
    sec = (
        "- [ ] **Step 1** one\n"
        "- [ ] **Step 2** two\n"
        "  cont\n"
        "- [ ] **Step 3** three\n"
        "\n"
        "- [ ] **Step 4** four\n"
        "\n"
        "Prose paragraph.\n"
    )
    s = pt.slice(sec, "", "steps")
    for ln in (
        "- [ ] **Step 1** one",
        "- [ ] **Step 2** two",
        "  cont",
        "- [ ] **Step 3** three",
        "- [ ] **Step 4** four",
    ):
        assert ln in s
    assert "Prose paragraph." not in s
    sec2 = "- [ ] **Step 5** five\n"
    assert "- [ ] **Step 5** five" in pt.slice(sec2, "", "steps")


def test_a43_bare_step_label_in_no_slice():
    sec = "**Facts.**\n\nF\n**Step 3**\n\nX\n"
    assert pt.slice(sec, "", "facts") == "**Facts.**\n\nF"
    assert pt.slice(sec, "", "steps") == ""


def test_a44_graph_field_lines():
    sec = (
        "**dependsOn:** none\n"
        "**touches:** a\n"
        "**areas:** x\n"
        "**acceptance:** y\n"
        "**repo:** z\n"
        "**commit subject:** s\n"
        "**probe_env:** E=1\n"
    )
    assert pt.slice(sec, "", "graph") == (
        "**dependsOn:** none\n**touches:** a\n**areas:** x\n**acceptance:** y\n**repo:** z"
    )


def test_a45_graph_appends_waves(tmp_path):
    sec = "**touches:** MARKER\n"
    plan_text = "## Waves\n\nthe waves text\n"
    assert "the waves text" in pt.slice(sec, plan_text, "graph")
    assert pt.slice(sec, "no waves here\n", "graph") == "**touches:** MARKER"
    # a typed plan without ## Waves still counts its rows (population)
    root, rows = tree(tmp_path, step="graph")
    write_doc(root, "graph", doc("graph", rows))
    r = cli(root, "--only", "graph")
    assert "graph: population landed 12 rejected 12" in r.stdout.splitlines()


def test_a46_operator_dispatch_slice():
    sec = "**Relaunch:**\n\nR\n\n**Rollback:**\n\nK\n"
    plan_text = "## Operator\n\nop text\n\n## Dispatch\n\ndi text\n"
    s = pt.slice(sec, plan_text, "operator-dispatch")
    assert (
        "op text" in s
        and "di text" in s
        and "**Relaunch:**" in s
        and "**Rollback:**" in s
    )
    assert s.index("op text") < s.index("di text") < s.index("**Relaunch:**")
    s2 = pt.slice(sec, "## Operator\n\nop text\n", "operator-dispatch")
    assert "op text" in s2 and "**Relaunch:**" in s2
    assert pt.slice("plain prose\n", "## Waves\n\nw\n", "operator-dispatch") == ""


def test_a47_plan_section_keeps_sub_headings():
    plan_text = "## Dispatch\n\n### Note\n\ndispatch text\n"
    s = pt.plan_section(plan_text, "## Dispatch")
    assert "### Note" in s and "dispatch text" in s


def test_a48_slice_keeps_bytes():
    sec = "**Facts.**\n\nline one\n\nline two\n"
    assert pt.slice(sec, "", "facts") == "**Facts.**\n\nline one\n\nline two"


def test_a49_plan_weighted_proxy(tmp_path):
    def build(tmp, one_plan):
        root = tmp / ("w1" if one_plan else "w2")
        (root / DOCS).mkdir(parents=True)
        rows = []
        if one_plan:
            sections = "".join(f"### W{i} (code, S) — t\n" for i in range(1, 6))
            write_plan(root, "w.md", sections, waves="plan waves text WAVESMARK")
            rows = [row(key=f"W{i}", plan_="w.md") for i in range(1, 6)]
        else:
            for i in range(1, 6):
                write_plan(
                    root,
                    f"v{i}.md",
                    f"### W{i} (code, S) — t\n",
                    waves="plan waves text WAVESMARK",
                )
                rows.append(row(key=f"W{i}", plan_=f"v{i}.md"))
        for j in range(1, 6):
            write_plan(
                root, f"u{j}.md", f"### X{j} (code, S) — t\n", waves="no mark here"
            )
            rows.append(
                row(
                    key=f"X{j}",
                    plan_=f"u{j}.md",
                    verdict="rejected",
                    plan_defect="vacuous",
                    review_path="docs/reviews/r.md",
                )
            )
        review(root)
        write_ledger(root, rows)
        quotes = [r for r in rows if r["verdict"] == "approved"][:3]
        text = doc(
            "graph",
            rows,
            exemplars=[espec(r, block="plan waves text WAVESMARK\n") for r in quotes],
            antis=[
                aspec(r, block="no mark here\n")
                for r in rows
                if r["verdict"] == "rejected"
            ],
            rule_names=("g",),
            preds=[("g", "regex:WAVESMARK")],
        )
        write_doc(root, "graph", text)
        return root

    for one_plan in (True, False):
        root = build(tmp_path, one_plan)
        _refusals, report = run_check(root, only=["graph"])
        rate = [ln for ln in report if ln.startswith("graph g:")]
        assert len(rate) == 1
        assert "landed 5/5 (100%)" in rate[0]


# --- Table 4: rates and thresholds


def test_a50_zero_sides_never_divide(tmp_path):
    m = pt.predicate_of("regex:MARKER")
    r_ok = row(verdict="approved")
    r_rej = row(key="R1", verdict="rejected")
    assert pt.rates(m[1], [(r_ok, "MARKER"), (r_rej, "MARKER")]) == (1, 1, 1, 1)
    assert pt.rates(m[1], [(r_rej, "MARKER")]) == (0, 0, 1, 1)
    assert pt.rates(m[1], [(r_ok, "MARKER")]) == (1, 1, 0, 0)
    assert pt.rates(m[1], [(r_ok, "")]) == (0, 0, 0, 0)
    # the report prints 0 for an empty side, never a traceback
    root, rows = tree(tmp_path, landed=0, rejected=12)
    write_doc(root, "facts", doc("facts", rows, exemplars=[espec(r) for r in rows[:3]]))
    r = cli(root, "--only", "facts")
    assert "facts p1: landed 0/0 (0%)" in r.stdout
    assert "Traceback" not in r.stderr


def test_a51_rounding_half_to_even(tmp_path):
    root, rows = tree(tmp_path, landed=8, rejected=8, marker_of=lambda i: i < 1)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[i], block=block("facts", i < 1)) for i in range(3)],
        ),
    )
    _refusals, report = run_check(root, only=["facts"])
    assert any("landed 1/8 (12%)" in ln for ln in report)
    root, rows = tree(tmp_path, landed=8, rejected=8, marker_of=lambda i: i < 3)
    write_doc(root, "facts", doc("facts", rows))
    _refusals, report = run_check(root, only=["facts"])
    assert any("landed 3/8 (38%)" in ln for ln in report)


def test_a52_gap_boundary(tmp_path):
    root, rows = tree(tmp_path, landed=20, rejected=20, marker_of=lambda i: i < 3)
    write_doc(root, "facts", doc("facts", rows))
    r = cli(root, "--only", "facts")
    assert r.returncode == 0  # d == 15 passes
    root, rows = tree(tmp_path, landed=50, rejected=50, marker_of=lambda i: i < 7)
    write_doc(root, "facts", doc("facts", rows))
    r = cli(root, "--only", "facts")
    assert "patterns: facts: predicate p1 gap 14 under 15" in refu(r.stdout)


def test_a53_min_rows_boundary(tmp_path):
    root, rows = tree(tmp_path, landed=10, rejected=10)
    write_doc(root, "facts", doc("facts", rows))
    r = cli(root, "--only", "facts")
    assert r.returncode == 0  # smaller side 10 passes
    root, rows = tree(tmp_path, landed=9, rejected=10)
    write_doc(root, "facts", doc("facts", rows))
    r = cli(root, "--only", "facts")
    assert "patterns: facts: predicate p1 smaller side 9 under 10" in refu(r.stdout)


def test_a54_flag_zero_vs_default(tmp_path):
    root, rows = tree(tmp_path, landed=3, rejected=3, marker_of=lambda i: i < 1)
    write_plan(root, "facts-r00.md", section("R00", "facts", marker=True))
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[i], block=block("facts", i < 1)) for i in range(3)],
            antis=[
                aspec(rej(rows)[0], block=block("facts", True)),
                aspec(rej(rows)[1]),
                aspec(rej(rows)[2]),
            ],
        ),
    )
    r = cli(root, "--only", "facts", "--gap", "0", "--min-rows", "0")
    assert r.returncode == 0
    r = cli(root, "--only", "facts")
    assert r.returncode == 1
    assert "patterns: facts: predicate p1 gap 0 under 15" in refu(r.stdout)
    assert "patterns: facts: predicate p1 smaller side 3 under 10" in refu(r.stdout)


def test_a55_regex_over_slice_property_over_row(tmp_path):
    root = tmp_path / "t"
    (root / DOCS).mkdir(parents=True)
    rows = []
    for i in range(12):
        key, name = f"L{i:02d}", f"facts-{i:02d}.md"
        write_plan(root, name, section(key, "facts", marker=True))
        rows.append(row(key=key, plan_=name, kind="docs" if i % 2 else "code"))
    for j in range(12):
        key, name = f"R{j:02d}", f"facts-r{j:02d}.md"
        write_plan(root, name, section(key, "facts", marker=False))
        rows.append(
            row(
                key=key,
                plan_=name,
                verdict="rejected",
                plan_defect="vacuous",
                review_path="docs/reviews/r.md",
                kind="docs" if j % 2 else "code",
            )
        )
    review(root)
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            rule_names=("re", "pr"),
            preds=[("re", "regex:MARKER"), ("pr", "property:kind == docs")],
        ),
    )
    _refusals, report = run_check(root, only=["facts"])
    assert any("facts re: landed 12/12" in ln for ln in report)
    assert any("facts pr: landed 6/12" in ln for ln in report)


def test_a56_every_op_arm(tmp_path):
    root = tmp_path / "t"
    (root / DOCS).mkdir(parents=True)
    rows = []
    for i, n in enumerate((0, 1, 2, 3)):
        key, name = f"L{i:02d}", f"facts-{i:02d}.md"
        write_plan(root, name, section(key, "facts", marker=True))
        rows.append(row(key=key, plan_=name, touches_n=n))
    for j in range(12):
        key, name = f"R{j:02d}", f"facts-r{j:02d}.md"
        write_plan(root, name, section(key, "facts", marker=False))
        rows.append(
            row(
                key=key,
                plan_=name,
                verdict="rejected",
                plan_defect="vacuous",
                review_path="docs/reviews/r.md",
            )
        )
    review(root)
    write_ledger(root, rows)
    ops = [
        ("property:touches_n == 2", 1),
        ("property:touches_n != 2", 3),
        ("property:touches_n <= 2", 3),
        ("property:touches_n >= 2", 2),
        ("property:touches_n < 2", 2),
        ("property:touches_n > 2", 1),
        ("property:touches_n in {0,1,2}", 3),
    ]
    names = [f"q{i}" for i in range(1, 8)]
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            rule_names=tuple(names),
            preds=list(zip(names, [b for b, _ in ops])),
        ),
    )
    _refusals, report = run_check(root, only=["facts"])
    for name, (_body, hits) in zip(names, ops):
        line = [ln for ln in report if ln.startswith(f"facts {name}:")]
        assert len(line) == 1, (name, report)
        assert f"landed {hits}/4" in line[0]


def test_a57_size_compares_lexically(tmp_path):
    root = tmp_path / "t"
    (root / DOCS).mkdir(parents=True)
    rows = []
    for i, (sz, kd) in enumerate(
        (("XS", "docs"), ("S", "docs"), ("M", "code"), ("L", "code"))
    ):
        key, name = f"L{i:02d}", f"facts-{i:02d}.md"
        write_plan(root, name, section(key, "facts", marker=True))
        rows.append(row(key=key, plan_=name, size=sz, kind=kd))
    for j in range(12):
        key, name = f"R{j:02d}", f"facts-r{j:02d}.md"
        write_plan(root, name, section(key, "facts", marker=False))
        rows.append(
            row(
                key=key,
                plan_=name,
                verdict="rejected",
                plan_defect="vacuous",
                review_path="docs/reviews/r.md",
                size="S",
            )
        )
    review(root)
    write_ledger(root, rows)
    bodies = [("size < M", 1), ("size in {XS,S}", 2), ("kind == docs", 2)]
    names = [f"q{i}" for i in range(1, 4)]
    preds = [(n, "property:" + b) for n, (b, _h) in zip(names, bodies)]
    write_doc(root, "facts", doc("facts", rows, rule_names=tuple(names), preds=preds))
    _refusals, report = run_check(root, only=["facts"])
    for name, (_b, hits) in zip(names, bodies):
        line = [ln for ln in report if ln.startswith(f"facts {name}:")]
        assert len(line) == 1, (name, report)
        assert f"landed {hits}/4" in line[0]


def test_a58_in_sets_strip_spaces(tmp_path):
    root, rows = tree(tmp_path, landed=4, rejected=4)
    for i, n in enumerate((0, 1, 2, 3)):
        rows[i]["touches_n"] = n
    write_ledger(root, rows)
    preds = [
        ("a", "property:touches_n in {0, 1}"),
        ("b", "property:touches_n in {0,1}"),
    ]
    write_doc(root, "facts", doc("facts", rows, rule_names=("a", "b"), preds=preds))
    _refusals, report = run_check(root, only=["facts"])
    assert "landed 2/4" in next(ln for ln in report if ln.startswith("facts a:"))
    assert "landed 2/4" in next(ln for ln in report if ln.startswith("facts b:"))
    rows[0]["size"], rows[1]["size"] = "XS", "S"
    rows[2]["size"], rows[3]["size"] = "M", "L"
    write_ledger(root, rows)
    preds2 = [("c", "property:size in {XS, S}"), ("d", "property:size in {XS,S}")]
    write_doc(root, "facts", doc("facts", rows, rule_names=("c", "d"), preds=preds2))
    _refusals, report = run_check(root, only=["facts"])
    assert "landed 2/4" in next(ln for ln in report if ln.startswith("facts c:"))
    assert "landed 2/4" in next(ln for ln in report if ln.startswith("facts d:"))


def test_a59_dead_predicate_refused(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(
        root,
        "facts",
        doc("facts", rows, rule_names=("p1",), preds=[("p1", "regex:NOSUCHMARKER")]),
    )
    r = cli(root, "--only", "facts")
    assert (
        "facts p1: landed 0/12 (0%) rejected 0/12 (0%) gap 0" in r.stdout.splitlines()
    )
    assert "patterns: facts: predicate p1 gap 0 under 15" in refu(r.stdout)


def test_a60_population_prints_for_missing_doc(tmp_path):
    root, _rows = tree(tmp_path)
    r = cli(root, "--only", "facts")
    assert r.returncode == 1
    assert r.stdout == (
        "facts: population landed 12 rejected 12\npatterns: facts: doc missing\n"
    )


def test_a61_only_computes_its_steps(tmp_path):
    root, _rows = tree(tmp_path, step="tests")
    r = cli(root, "--only", "tests")
    assert r.returncode == 1
    assert r.stdout == (
        "tests: population landed 12 rejected 12\npatterns: tests: doc missing\n"
    )


# --- Table 5: the CLI, exits and ordering


def test_a62_green_stdout_exact(tmp_path):
    root = green(tmp_path)
    r = cli(root)
    assert r.returncode == 0
    assert r.stderr == ""
    lines = []
    order = ("facts", "interfaces", "steps", "tests", "graph", "operator-dispatch")
    for step in order:
        lines.append(f"{step}: population landed 12 rejected 12")
    for step in order:
        lines.append(f"{step} p1: landed 12/12 (100%) rejected 0/12 (0%) gap 100")
    for step in order:
        lines.append(f"{step} p2: predicate none — prose reason one")
        lines.append(f"{step} p3: predicate none — prose reason two")
    assert r.stdout == "\n".join(lines) + "\n"


def test_a63_refusals_sorted_after_report(tmp_path):
    root = tmp_path / "g"
    (root / DOCS).mkdir(parents=True, exist_ok=True)
    allrows = []
    for step in pt.STEPS:
        rows = corpus(root, step)
        if step == "tests":
            rej(rows)[0]["review_path"] = "docs/reviews/gone.md"
        allrows.extend(rows)
        write_doc(root, step, doc(step, rows))
    write_ledger(root, allrows)
    frows = [row(key=f"L{i:02d}", plan_=f"facts-{i:02d}.md") for i in range(12)] + [
        row(
            key=f"R{j:02d}",
            plan_=f"facts-r{j:02d}.md",
            verdict="rejected",
            plan_defect="vacuous",
            review_path="docs/reviews/r.md",
        )
        for j in range(12)
    ]
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            frows,
            exemplars=[
                espec(frows[0], row_line=rline(frows[0]) + "X"),
                espec(frows[1], omit_author=True),
                espec(frows[2]),
            ],
        ),
    )
    trows = [row(key=f"L{i:02d}", plan_=f"tests-{i:02d}.md") for i in range(12)] + [
        row(
            key=f"R{j:02d}",
            plan_=f"tests-r{j:02d}.md",
            verdict="rejected",
            plan_defect="vacuous",
            review_path="docs/reviews/gone.md" if j == 0 else "docs/reviews/r.md",
        )
        for j in range(12)
    ]
    write_doc(
        root,
        "tests",
        doc(
            "tests",
            trows,
            antis=[
                aspec(rej(trows)[0], review_path="docs/reviews/gone.md"),
                aspec(rej(trows)[1]),
                aspec(rej(trows)[2]),
            ],
        ),
    )
    r = cli(root)
    assert r.returncode == 1
    assert r.stderr == ""
    lines = r.stdout.splitlines()
    pat = [i for i, ln in enumerate(lines) if ln.startswith("patterns: ")]
    assert pat == list(range(len(lines) - 3, len(lines)))
    assert lines[-3:] == [
        "patterns: facts: exemplar L00 row: line differs from the ledger",
        "patterns: facts: exemplar L01 has no author: line",
        "patterns: tests: anti-pattern R00 review docs/reviews/gone.md missing",
    ]


def test_a64_exit2_arms(tmp_path):
    def one_stderr_line(r, exact=None):
        assert r.returncode == 2
        assert r.stdout == ""
        assert len(r.stderr.strip().splitlines()) == 1, r.stderr
        assert r.stderr.strip().startswith("patterns: ")
        if exact is not None:
            assert r.stderr.strip() == exact, r.stderr

    # 1: missing outcomes file
    root = tmp_path / "e1"
    (root / DOCS).mkdir(parents=True)
    one_stderr_line(cli(root))
    # 2-8: malformed ledger rows
    root, rows = tree(tmp_path)
    write_doc(root, "facts", doc("facts", rows))
    p = root / OUTCOMES
    p.write_text("[1,2]\n", encoding="utf-8")
    one_stderr_line(cli(root), "patterns: outcomes line 1: not a JSON object")
    p.write_text("{not json\n", encoding="utf-8")
    one_stderr_line(cli(root), "patterns: outcomes line 1: not a JSON object")
    p.write_text(rline(rows[0]) + "\n\n" + rline(rows[1]) + "\n", encoding="utf-8")
    one_stderr_line(cli(root), "patterns: outcomes line 2: not a JSON object")
    bad = dict(rows[0])
    del bad["gate_ts"]
    p.write_text(rline(bad) + "\n", encoding="utf-8")
    one_stderr_line(cli(root), "patterns: outcomes row L00: missing field gate_ts")
    bad2 = dict(rows[0])
    bad2["note"] = "x"
    p.write_text(rline(bad2) + "\n", encoding="utf-8")
    one_stderr_line(cli(root), "patterns: outcomes row L00: unexpected field note")
    p.write_text(rline(rows[0]) + "\n" + rline(rows[0]) + "\n", encoding="utf-8")
    one_stderr_line(cli(root), "patterns: outcomes row L00: duplicate (plan, key)")
    bad3 = dict(rows[0])
    bad3["plan"] = "ghost.md"
    p.write_text(rline(bad3) + "\n", encoding="utf-8")
    one_stderr_line(
        cli(root),
        "patterns: outcomes row L00: plan ghost.md not under " + PLANS,
    )
    # 9: a --docs that is a file
    root, rows = tree(tmp_path)
    write_doc(root, "facts", doc("facts", rows))
    one_stderr_line(cli(root, "--docs", OUTCOMES))
    # 10: a --plans that does not exist
    one_stderr_line(cli(root, "--plans", "no/such/dir"))
    # 11: a --reviews that does not exist
    one_stderr_line(cli(root, "--reviews", "no/such/dir"))
    # 12: --only nosuchstep
    one_stderr_line(cli(root, "--only", "nosuchstep"))
    # 13: --only ""
    one_stderr_line(cli(root, "--only", ""))


def test_a65_argparse_arms(tmp_path):
    with pytest.raises(SystemExit) as e:
        pt.main([])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        pt.main(["bogus"])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        pt.main(["check", "--help"])
    assert e.value.code == 0


def test_a66_only_grammar(tmp_path):
    root = tmp_path / "t"
    (root / DOCS).mkdir(parents=True)
    frows = corpus(root, "facts")
    trows = corpus(root, "tests")
    write_ledger(root, frows + trows)
    write_doc(root, "facts", doc("facts", frows))
    write_doc(root, "tests", doc("tests", trows))
    r1 = cli(root, "--only", "facts,tests")
    r2 = cli(root, "--only", "facts, tests")
    r3 = cli(root, "--only", "facts,facts")
    assert r1.returncode == 0
    assert r1.stdout == r2.stdout
    r_facts = cli(root, "--only", "facts")
    assert r3.stdout == r_facts.stdout  # a repeated step name collapses
    r4 = cli(root, "--only", "tests,facts")
    assert r4.returncode == 0
    assert r4.stdout == r1.stdout  # STEPS order regardless of the flag's order


def test_a67_without_only_all_six_required(tmp_path):
    root, _rows = tree(tmp_path)
    r = cli(root)
    assert r.returncode == 1
    assert refu(r.stdout) == [f"patterns: {s}: doc missing" for s in pt.STEPS]
    r = cli(root, "--only", "facts")
    assert refu(r.stdout) == ["patterns: facts: doc missing"]


def test_a68_docs_directory_listing_ignored(tmp_path):
    root, rows = tree(tmp_path)
    write_doc(root, "facts", doc("facts", rows))
    (root / DOCS / "notes.md").write_text("garbage\n", encoding="utf-8")
    (root / DOCS / "facts.md.bak").write_text("garbage\n", encoding="utf-8")
    (root / DOCS / "old").mkdir()
    r = cli(root, "--only", "facts")
    assert r.returncode == 0
    assert "notes" not in r.stdout
    # a doc committed as test.md reads as tests: doc missing
    trows = corpus(root, "tests")
    write_ledger(root, rows + trows)
    write_doc(root, "tests", doc("tests", trows))
    shutil.move(root / DOCS / "tests.md", root / DOCS / "test.md")
    r = cli(root, "--only", "tests")
    assert refu(r.stdout) == ["patterns: tests: doc missing"]


def test_a69_absolute_docs_used_as_given(tmp_path):
    root = green(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    shutil.move(root / DOCS, elsewhere)
    r = cli(root, "--docs", str(elsewhere))
    assert r.returncode == 0
    assert r.stdout.count(": population landed 12 rejected 12\n") == 6


def test_a70_no_writes_no_locks(tmp_path):
    root = green(tmp_path)

    def snap():
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            for f in sorted(filenames):
                p = pathlib.Path(dirpath) / f
                st = p.stat()
                out.append((str(p.relative_to(root)), st.st_size, st.st_mtime_ns))
        return out

    before = snap()
    p1 = subprocess.Popen(
        [sys.executable, str(SRC), "check", "--root", str(root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    p2 = subprocess.Popen(
        [sys.executable, str(SRC), "check", "--root", str(root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    o1, _e1 = p1.communicate()
    o2, _e2 = p2.communicate()
    assert o1 == o2
    assert p1.returncode == p2.returncode
    assert snap() == before


def test_a71_gap_is_absolute_not_signed(tmp_path):
    # The gate 2026-09-23-glm-review-s37pt-PT10 fixture: the marker sits on
    # every rejected row's Facts slice and no landed one, so the signed
    # pp - qq understates the gap as -100 and the check refuses a predicate
    # that discriminates exactly as C-DOC 5's docs seats design them.
    # C-PATTERNS-CLI restates d = abs(p - q): the gap is a distance.
    root = tmp_path / "t"
    (root / DOCS).mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(10):
        key, name = f"L{i:02d}", f"facts-{i:02d}.md"
        write_plan(root, name, section(key, "facts", marker=False))
        rows.append(row(key=key, plan_=name))
    for j in range(10):
        key, name = f"R{j:02d}", f"facts-r{j:02d}.md"
        write_plan(root, name, section(key, "facts", marker=True))
        rows.append(
            row(
                key=key,
                plan_=name,
                verdict="rejected",
                plan_defect="wrong-fact",
                review_path="docs/reviews/r.md",
            )
        )
    review(root)
    write_ledger(root, rows)
    write_doc(
        root,
        "facts",
        doc(
            "facts",
            rows,
            exemplars=[espec(rows[i], block=block("facts", False)) for i in range(3)],
            antis=[aspec(r, block=block("facts", True)) for r in rej(rows)[:3]],
        ),
    )
    r = cli(root, "--only", "facts")
    assert r.returncode == 0
    assert "facts p1: landed 0/10 (0%) rejected 10/10 (100%) gap 100" in (
        r.stdout.splitlines()
    )
    assert not refu(r.stdout)
    assert "patterns:" not in r.stderr
