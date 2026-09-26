"""Evidence status tests (plan 2026-09-11-evidence, EV13)."""

import datetime as dt
import pathlib
import sys
from collections import Counter

import tomllib

HERE = pathlib.Path(__file__).resolve()
EVIDENCE_DIR = HERE.parents[2] / "pkgs" / "evidence"
if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))

import evidence as ev
import status
import tasks
from test_evidence import CLAIMS, fake_nixos_version, make_repo


def _short(x):
    return (x or "none")[:12]


BUGS_TOML = """\
[[bug]]
id = "BUG-open-typed"
found = 2026-09-10
symptom = "typed open row"
repro = "true"
status = "open"
closing_check = ""
task = "FIX1"
evidence = "docs/bugs/typed.md"

[[bug]]
id = "BUG-open-untyped"
found = 2026-09-10
symptom = "untyped open row"
repro = "true"
status = "open"
closing_check = ""
task = ""
evidence = "docs/bugs/untyped.md"

[[bug]]
id = "BUG-fixed"
found = 2026-09-10
symptom = "fixed row"
repro = "true"
status = "fixed"
closing_check = "factory-unit"
task = "FIX2"
evidence = "docs/bugs/fixed.md"

[[bug]]
id = "BUG-closed"
found = 2026-09-10
symptom = "closed row"
repro = "true"
status = "closed"
closing_check = "lint"
task = ""
evidence = "docs/bugs/closed.md"
"""


def build_bundle(tmp_path):
    """A real bundle from a throwaway repo: docs-only head ahead of the fake
    live rev, a clean tree, no checks, one verified claim and one open gap."""
    repo, live, head, _code_head = make_repo(tmp_path)
    store = tmp_path / "store"
    store.mkdir()
    claims_file = tmp_path / "claims.toml"
    claims_file.write_text(CLAIMS)
    b = ev.bundle(
        str(store),
        str(repo),
        str(claims_file),
        [],
        fake_nixos_version(tmp_path, live),
        now=dt.datetime(2026, 9, 11, 12, 0, tzinfo=dt.timezone.utc),
    )
    return repo, b, live, head


def build_graph():
    """A board_graph-shaped graph with one empty repo."""
    return {
        "generated": "2026-09-11T12:00:00Z",
        "repos": [{"name": "repo", "tasks": [], "manifest": []}],
        "bugs": [],
    }


def bug_rows():
    return tomllib.loads(BUGS_TOML)["bug"]


def _checks_lines(b):
    md = ev.render_bundle_markdown(b)
    out = []
    in_checks = False
    for line in md.split("\n"):
        if line == "## Checks covering HEAD and the live system":
            in_checks = True
            out.append(line)
            continue
        if in_checks:
            if line.startswith("## "):
                break
            out.append(line)
    return [l for l in out if l.strip()]


def _board_lines(graph):
    lines = ["## Queue", "<!-- tasks:begin -->"]
    lines.extend([l for l in tasks.render_board_block(graph).split("\n") if l.strip()])
    lines.append("<!-- tasks:end -->")
    return lines


def test_status_writes_whole_page_with_sections(tmp_path):
    _repo, b, _live, _head = build_bundle(tmp_path)
    graph = build_graph()
    page = status.render_status(b, graph, bug_rows(), dt.date(2026, 9, 11))
    headings = [l for l in page.split("\n") if l.startswith("## ")]
    assert headings == [
        "## Checks covering HEAD and the live system",
        "## Queue",
        "## Claims",
        "## Open bugs",
    ]
    assert page.startswith("# Status — repo\n")


def test_queue_block_equals_board_block(tmp_path):
    _repo, b, _live, _head = build_bundle(tmp_path)
    graph = build_graph()
    page = status.render_status(b, graph, bug_rows(), dt.date(2026, 9, 11))
    text = page
    ib = text.find("<!-- tasks:begin -->")
    ie = text.find("<!-- tasks:end -->")
    assert 0 <= ib < ie
    inner = text[ib + len("<!-- tasks:begin -->") : ie]
    assert inner == "\n" + tasks.render_board_block(graph)


def test_bugs_section_renders_open_rows_only(tmp_path):
    _repo, b, _live, _head = build_bundle(tmp_path)
    graph = build_graph()
    page = status.render_status(b, graph, bug_rows(), dt.date(2026, 9, 11))
    lines = page.split("\n")
    idx = lines.index("## Open bugs")
    tail = lines[idx:]
    assert "BUG-open-typed — FIX1" in tail
    assert "BUG-open-untyped — (untyped)" in tail
    assert not any("BUG-fixed" in l for l in tail)
    assert not any("BUG-closed" in l for l in tail)


def test_bugs_placeholder_when_ledger_absent(tmp_path):
    p = tmp_path / "status.md"
    missing = tmp_path / "none" / "bugs.toml"
    r = status.main(
        [
            "--out",
            str(p),
            "--bugs",
            str(missing),
            "--sibling",
            str(tmp_path),
            "--store",
            str(tmp_path / "store"),
        ]
    )
    assert r == 0
    page = p.read_text()
    assert "_(no bug ledger)_" in page
    idx = page.index("## Open bugs")
    assert page.index("_(no bug ledger)_") > idx


def test_page_is_the_union_of_its_parts(tmp_path):
    _repo, b, _live, _head = build_bundle(tmp_path)
    graph = build_graph()
    rows = bug_rows()
    c = b["claims"]
    parts = [
        f"# Status — {graph['repos'][0]['name']}",
        (
            f"Generated {b['generated']}; live {_short(b['live']['rev'])}; "
            f"HEAD {_short(b['head'])} — {'dirty' if b['dirty'] else 'clean'}."
        ),
    ]
    parts += _checks_lines(b)
    parts += _board_lines(graph)
    parts += [
        "## Claims",
        f"**verified: {c['verified']}, parked: {c['parked']}, gaps: {len(c['gaps'])}**",
    ]
    parts += [f"- {g['id']}" for g in c["gaps"]]
    parts += ["## Open bugs"]
    parts += [
        f"{r['id']} — {r['task']}" if r.get("task") else f"{r['id']} — (untyped)"
        for r in rows
        if r.get("status") == "open"
    ]
    page = status.render_status(b, graph, rows, dt.date(2026, 9, 11))
    page_lines = [l for l in page.split("\n") if l.strip()]
    assert Counter(page_lines) == Counter(parts)


def test_status_out_is_atomic_and_touches_nothing_else(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    p = out_dir / "status.md"
    before = sorted(x.name for x in out_dir.iterdir())
    r = status.main(
        [
            "--out",
            str(p),
            "--sibling",
            str(tmp_path),
            "--store",
            str(tmp_path / "store"),
        ]
    )
    assert r == 0
    after = sorted(x.name for x in out_dir.iterdir())
    assert before == []
    assert after == ["status.md"]
    assert p.read_text().startswith("# Status —")


def test_out_dir_missing_exits_1(tmp_path, capsys):
    p = tmp_path / "nonesuch" / "status.md"
    r = status.main(
        [
            "--out",
            str(p),
            "--sibling",
            str(tmp_path),
            "--store",
            str(tmp_path / "store"),
        ]
    )
    assert r == 1
    err = capsys.readouterr().err
    assert "status: no such directory" in err
    assert not p.exists()


def test_cli_forwards_status(tmp_path):
    p = tmp_path / "status.md"
    r = ev.main(["status", "--out", str(p), "--sibling", str(tmp_path)])
    assert r == 0
    assert p.exists()
