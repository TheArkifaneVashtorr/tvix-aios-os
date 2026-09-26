"""`evidence report plans` tests (plan 2026-09-06-planning-agent, P10b).

The report joins the P6 judgement stream to the first-gate outcome of every
typed plan chain (`read_reviews`, `parse_plan`, `chain_root`), reproduces the
design §7 corpus baseline from the plan-defect ledger over ALL rejection rows,
and refuses a conclusion when fewer than `--min-n` chains gate.
"""

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
FIXTURES = HERE.parent / "fixtures" / "report"
REPO = FIXTURES / "repo"
STORE = FIXTURES  # the directory that holds plans.jsonl

HEADER = (
    "# evidence report plans — proxies for "
    "docs/superpowers/specs/2026-09-05-planning-agent-design.md §7; "
    "n printed with every figure"
)

DATE = "2026-09-01"


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence",
        pathlib.Path("pkgs/evidence"),
    ]
    src_dir = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src_dir))

    def _load(name):
        spec = importlib.util.spec_from_file_location(name, src_dir / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod

    ev = _load("evidence")
    tk = _load("tasks")
    rp = _load("report")
    return ev, tk, rp


ev, tk, rp = load()
SRC = HERE.parents[2] / "pkgs" / "evidence" / "evidence.py"


def oname(stem):
    """A review filename both `read_reviews` (`*opus-review*`) and the block
    scan (`_review_date` date prefix) will read."""
    return f"{DATE}-opus-review-{stem}.md"


def write_plan(repo, fname, keys):
    d = repo / "docs" / "superpowers" / "plans"
    d.mkdir(parents=True, exist_ok=True)
    lines = ["# Fixture plan", ""]
    for key in keys:
        lines += [
            f"### {key} (code, S) — a task",
            "",
            "**dependsOn:** none",
            "",
            f"**touches:** {key.lower()}.py",
            "**acceptance:** unit",
            f"**commit subject:** `x: {key.lower()} (test: unit)`",
            "",
        ]
    (d / fname).write_text("\n".join(lines) + "\n")


def write_review(repo, name, key, verdict, front=None):
    d = repo / "docs" / "reviews"
    d.mkdir(parents=True, exist_ok=True)
    head = f"# Opus gate — seat run fx, task {key} — {verdict}\n\nbody\n"
    if front is None:
        (d / name).write_text(head)
    else:
        block = "---\n" + "\n".join(f"{k}: {v}" for k, v in front.items()) + "\n---\n"
        (d / name).write_text(block + head)


def write_ledger(repo, text):
    d = repo / "docs" / "ledger"
    d.mkdir(parents=True, exist_ok=True)
    (d / "plan-defects.toml").write_text(text)


def judge_row(plan, total, decision, revision=0):
    return {
        "v": 1,
        "ts": "2026-09-06T00:00:00Z",
        "kind": "plan-judgement",
        "plan": f"docs/superpowers/plans/{plan}",
        "total": total,
        "decision": decision,
        "revision": revision,
    }


def write_store(store_dir, rows):
    store_dir = pathlib.Path(store_dir)
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / "plans.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return store_dir


def test_corpus_lines_reproduce_by_hand():
    lines = rp.plans_report(str(STORE), str(REPO), today="2026-09-06")
    assert lines[0] == HEADER
    assert lines[1] == "first-try landing rate: 2/5 chains (40%)"
    assert lines[2] == "plan-caused share of rejections: 1/5 (20%)"
    assert lines[3] == "re-plan rate: 1/5 chains"
    assert lines[4] == "rework rounds per landed task: 2/4 = 0.50"


def test_line_two_is_all_rows_not_windowed():
    # `--today` far in the future must not empty the ledger: line 2 counts every
    # rejection row, whatever the date.
    lines = rp.plans_report(str(STORE), str(REPO), today="2026-09-20")
    assert lines[2] == "plan-caused share of rejections: 1/5 (20%)"


def test_line_two_never_counts_an_approved_block(tmp_path):
    repo = tmp_path / "repo"
    write_plan(repo, "one.md", ["X1", "X2"])
    write_ledger(
        repo,
        "[meta]\n"
        "front_matter_from = 2026-09-01\n"
        "\n"
        "[[rejection]]\n"
        'review = "docs/reviews/2026-09-05-opus-review-row.md"\n'
        'run = "fx"\n'
        'key = "X1"\n'
        "date = 2026-09-05\n"
        'plan_defect = "vacuous"\n',
    )
    # A REJECTED block in scope counts (missing-case).
    write_review(
        repo, oname("x1-rej"), "X1", "REJECTED", front={"plan_defect": "missing-case"}
    )
    # An APPROVED block carrying a plan_defect never counts.
    write_review(repo, oname("x2-app"), "X2", "APPROVED", front={"plan_defect": "none"})
    store = write_store(tmp_path / "store", [])
    lines = rp.plans_report(str(store), str(repo), today="2026-09-20", min_n=1)
    assert any(l == "plan-caused share of rejections: 2/2 (100%)" for l in lines)


def test_default_n_gate_is_five(tmp_path):
    repo = tmp_path / "repo"
    write_plan(repo, "four.md", ["A1", "B1", "C1", "D1"])
    for i, key in enumerate(["A1", "B1", "C1", "D1"]):
        write_review(repo, oname(f"r{i}"), key, "APPROVED")
    store = write_store(tmp_path / "store", [])
    # No `min_n` passed: the default gate (five) must refuse four chains.
    lines = rp.plans_report(str(store), str(repo), today="2026-09-06")
    assert any(l == "refused: n=4 < 5 (no conclusion under 5)" for l in lines)
    assert not any(l.startswith("first-try landing rate:") for l in lines)


def test_refusal_parenthetical_names_the_gate_in_force(tmp_path):
    repo = tmp_path / "repo"
    write_plan(repo, "four.md", ["A1", "B1", "C1", "D1"])
    for i, key in enumerate(["A1", "B1", "C1", "D1"]):
        write_review(repo, oname(f"r{i}"), key, "APPROVED")
    store = write_store(tmp_path / "store", [])
    lines = rp.plans_report(str(store), str(repo), today="2026-09-06", min_n=8)
    assert any(l == "refused: n=4 < 8 (no conclusion under 8)" for l in lines)


def test_zero_denominators_print_unmeasured(tmp_path):
    repo = tmp_path / "repo"
    # Five gated chains, none landed and no rejection rows at all.
    write_plan(repo, "five.md", ["A1", "B1", "C1", "D1", "E1"])
    for i, key in enumerate(["A1", "B1", "C1", "D1", "E1"]):
        write_review(repo, oname(f"r{i}"), key, "REJECTED")
    store = write_store(tmp_path / "store", [])
    lines = rp.plans_report(str(store), str(repo), today="2026-09-06")
    assert any(l == "plan-caused share of rejections: unmeasured (n=0)" for l in lines)
    assert any(l == "rework rounds per landed task: unmeasured (n=0)" for l in lines)


def test_rubric_refuses_under_five_and_joins_at_five(tmp_path):
    # One judgement refuses the join.
    store = write_store(tmp_path / "s1", [judge_row("fixture-plan.md", 38, "dispatch")])
    lines = rp.plans_report(str(store), str(REPO), today="2026-09-06")
    assert any(l == "rubric score before dispatch: n=1, refused" for l in lines)

    # Five judgements print one line per plan; a plan with no tasks is `—/0`.
    rows = [judge_row(f"plan{i}.md", 30 + i, "dispatch") for i in range(5)]
    rows.append(judge_row("fixture-plan.md", 38, "revise"))
    store = write_store(tmp_path / "s5", rows)
    lines = rp.plans_report(str(store), str(REPO), today="2026-09-06")
    assert any(l == "rubric score before dispatch: n=6" for l in lines)
    assert any(l == "plan0.md total 30 decision dispatch first-try —/0" for l in lines)
    assert any(
        l == "fixture-plan.md total 38 decision revise first-try 2/5" for l in lines
    )


def test_join_iterates_plans_latest_revision_only(tmp_path):
    # p0 judged twice; only the latest revision prints and counts toward j.
    rows = [
        judge_row("p0.md", 30, "dispatch"),
        judge_row("p0.md", 40, "revise", revision=1),
        judge_row("p1.md", 31, "dispatch"),
        judge_row("p2.md", 32, "dispatch"),
        judge_row("p3.md", 33, "dispatch"),
        judge_row("p4.md", 34, "dispatch"),
    ]
    store = write_store(tmp_path / "store", rows)
    lines = rp.plans_report(str(store), str(REPO), today="2026-09-06")
    assert any(l == "rubric score before dispatch: n=5" for l in lines)
    assert any(l == "p0.md total 40 decision revise first-try —/0" for l in lines)
    assert not any(l == "p0.md total 30 decision dispatch first-try —/0" for l in lines)


def test_threshold_proposal_is_the_minimum_clearing_total(tmp_path):
    repo = tmp_path / "repo"
    # Four dispatched plans at 100% first-try (totals 36, 38, 35, 41); six under.
    for name, total in [("p1", 36), ("p2", 38), ("p3", 35), ("p4", 41)]:
        write_plan(repo, f"{name}.md", [name.upper()])
        write_review(repo, oname(name), name.upper(), "APPROVED")
    for i in range(6):
        name = f"u{i}"
        write_plan(repo, f"{name}.md", [name.upper()])
        write_review(repo, oname(name), name.upper(), "REJECTED")
        write_review(repo, oname(f"{name}.b"), name.upper() + "b", "APPROVED")
    rows = []
    for name, total in [("p1", 36), ("p2", 38), ("p3", 35), ("p4", 41)]:
        rows.append(judge_row(f"{name}.md", total, "dispatch"))
    for i in range(6):
        rows.append(judge_row(f"u{i}.md", 30, "dispatch"))
    store = write_store(tmp_path / "store", rows)
    lines = rp.plans_report(str(store), str(repo), today="2026-09-06")
    assert any(l == "threshold proposal: 35" for l in lines)

    # Nine dispatched plans: no proposal line.
    store9 = write_store(tmp_path / "store9", rows[:9])
    lines9 = rp.plans_report(str(store9), str(repo), today="2026-09-06")
    assert not any(l.startswith("threshold proposal:") for l in lines9)
    assert not any(l.startswith("no score separates") for l in lines9)


def test_survivors_outside_named_set(tmp_path):
    repo = tmp_path / "repo"
    write_plan(repo, "one.md", ["A1"])
    write_review(
        repo,
        oname("r1"),
        "A1",
        "APPROVED",
        front={"plan_defect": "none", "mutants_outside_named": "7"},
    )
    write_review(
        repo,
        oname("r2"),
        "A1b",
        "APPROVED",
        front={"plan_defect": "none", "mutants_outside_named": "3"},
    )
    write_review(repo, oname("r3"), "A1r", "APPROVED", front={"plan_defect": "none"})
    write_review(repo, oname("r4"), "A1c", "APPROVED")
    rows = [judge_row(f"j{i}.md", 34, "dispatch") for i in range(5)]
    store = write_store(tmp_path / "store", rows)
    lines = rp.plans_report(str(store), str(repo), today="2026-09-06")
    assert any(l == "survivors outside the named set: 10/2" for l in lines)

    # Absent everywhere: unmeasured.
    repo2 = tmp_path / "repo2"
    write_plan(repo2, "one.md", ["A1"])
    write_review(repo2, oname("r1"), "A1", "APPROVED")
    lines2 = rp.plans_report(str(store), str(repo2), today="2026-09-06")
    assert any(
        l == "unmeasured (no review carries mutants_outside_named)" for l in lines2
    )


def test_plan_flag_restricts_line_one(tmp_path):
    repo = tmp_path / "repo"
    write_plan(repo, "keep.md", ["A1", "A2", "A3", "A4", "A5"])
    write_plan(repo, "drop.md", ["B1", "B2", "B3", "B4", "B5"])
    for key in ["A1", "A2", "A3", "A4", "A5"]:
        write_review(repo, oname(key.lower()), key, "APPROVED")
    for key in ["B1", "B2", "B3", "B4", "B5"]:
        write_review(repo, oname(key.lower()), key, "REJECTED")
    store = write_store(tmp_path / "store", [])
    keep = rp.plans_report(str(store), str(repo), today="2026-09-06", plan="keep.md")
    assert any(l == "first-try landing rate: 5/5 chains (100%)" for l in keep)
    drop = rp.plans_report(str(store), str(repo), today="2026-09-06", plan="drop.md")
    assert any(l == "first-try landing rate: 0/5 chains (0%)" for l in drop)
    # Without the flag the same repo gates ten chains.
    lines_all = rp.plans_report(str(store), str(repo), today="2026-09-06")
    assert any(l == "first-try landing rate: 5/10 chains (50%)" for l in lines_all)


def test_plan_flag_accepts_a_glob(tmp_path):
    repo = tmp_path / "repo"
    write_plan(repo, "2026-09-05-keep.md", ["A1", "A2", "A3", "A4", "A5"])
    write_plan(repo, "2026-09-05-drop.md", ["B1", "B2", "B3", "B4", "B5"])
    for key in ["A1", "A2", "A3", "A4", "A5"]:
        write_review(repo, oname(key.lower()), key, "APPROVED")
    for key in ["B1", "B2", "B3", "B4", "B5"]:
        write_review(repo, oname(key.lower()), key, "REJECTED")
    store = write_store(tmp_path / "store", [])
    lines = rp.plans_report(
        str(store), str(repo), today="2026-09-06", plan="2026-09-05-*.md"
    )
    assert any(l == "first-try landing rate: 5/10 chains (50%)" for l in lines)


def test_cli_end_to_end_dispatch_and_store_forwarding(tmp_path):
    store = write_store(tmp_path / "store", [judge_row("p0.md", 38, "dispatch")])
    proc = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--store",
            str(store),
            "report",
            "plans",
            "--repo",
            str(REPO),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=dict(os.environ),
    )
    assert proc.returncode == 0
    assert "first-try landing rate: 2/5 chains (40%)" in proc.stdout


def test_unreadable_repo_is_exit_two(tmp_path, capsys):
    rc = rp.main(["--store", str(STORE), "plans", "--repo", str(tmp_path / "gone")])
    assert rc == 2
    assert "gone" in capsys.readouterr().err


def test_malformed_today_is_exit_two(capsys):
    rc = rp.main(
        ["--store", str(STORE), "plans", "--repo", str(REPO), "--today", "notadate"]
    )
    assert rc == 2
    assert "notadate" in capsys.readouterr().err
