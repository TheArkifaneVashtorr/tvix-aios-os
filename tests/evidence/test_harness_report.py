"""`evidence report harness` tests (plan 2026-09-07-seat-harness-redesign, SH1).

The report windows `derived/tasks` rows by `result_mtime[:10]`, joins each to
its newest gate through `join_tasks_gates`, n-gates each group (`all`, then
every `task_kind/size` pair), and prints the fractions, medians, error-class
and plan-defect tallies. No tree is read: the store is the only input.
"""

import importlib.util
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "evidence" / "evidence.py"

HARNESS_HEADER = (
    "# evidence report harness — proxies for "
    "docs/superpowers/specs/2026-09-07-seat-harness-redesign-design.md §6; "
    "n printed with every figure"
)

TAGS_LINE = (
    "tags: unmeasured — the §2 corpus tags live in "
    "docs/reviews/harness-study/2026-09-07-deepseek-failure-corpus.md, not in "
    "the store; plan_defect above is the proxy (gap: one primary class per "
    "gate, many tags per run)"
)

RUNG_LINE = (
    "rung/class: unmeasured until the seat-driver plan's rung (SD1, SD3) and "
    "class (SD2) fields are declared"
)


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


def trow(
    run,
    key,
    *,
    kind="code",
    size="S",
    status="done",
    out=100,
    wall=600,
    mtime="2026-09-07T10:00:00Z",
    error_class="none",
    touches=None,
    checks_verified=None,
    probes_verified=None,
):
    row = {
        "kind": "task-result",
        "run_id": run,
        "key": key,
        "model": "m/a",
        "task_kind": kind,
        "size": size,
        "status": status,
        "wall_s": wall,
        "usage": {"out": out},
        "error_class": error_class,
        "result_mtime": mtime,
    }
    if touches is not None:
        extra, disclosed = touches
        row["touches_extra"] = extra
        row["touches_disclosed"] = disclosed
    if checks_verified is not None:
        row["checks_verified"] = checks_verified
    if probes_verified is not None:
        row["probes_verified"] = probes_verified
    return row


def grow(
    run,
    key,
    verdict,
    round_kind="first",
    plan_defect=None,
    mutants_outside_named=None,
):
    row = {
        "kind": "gate-verdict",
        "run_id": run,
        "key": key,
        "chain_root": key,
        "round_kind": round_kind,
        "round": 0,
        "reviewer": "opus",
        "route": "claude",
        "verdict": verdict,
        "plan_defect": plan_defect,
        "review_path": f"docs/reviews/{run}-{key}-{round_kind}.md",
    }
    if mutants_outside_named is not None:
        row["mutants_outside_named"] = mutants_outside_named
    return row


def write(store, tasks, gates):
    s = str(store)
    if tasks:
        ev.replace_stream(s, "derived/tasks", tasks)
    if gates:
        ev.replace_stream(s, "derived/gates", gates)


def test_window_bounds_before_and_since(tmp_path):
    # Three rows dated 09-01, 09-07 and the 09-08 boundary day. Mutant: `<=`
    # on `before` counts the boundary row.
    store = tmp_path / "store"
    write(
        store,
        [
            trow("r", "A1", mtime="2026-09-01T00:00:00Z"),
            trow("r", "A2", mtime="2026-09-07T00:00:00Z"),
            trow("r", "A3", mtime="2026-09-08T00:00:00Z"),
        ],
        [],
    )
    lines = rp.harness_report(str(store), before="2026-09-08")
    assert "population: 2 task rows, 0 with a gate verdict" in lines

    lines = rp.harness_report(str(store), since="2026-09-07")
    assert "population: 2 task rows, 0 with a gate verdict" in lines

    lines = rp.harness_report(str(store))
    assert "population: 3 task rows, 0 with a gate verdict" in lines


def test_first_gate_fractions_separate_round_kinds(tmp_path):
    # 5 first-round (3 approved, 2 rejected) + 1 approved fix + 1 rejected
    # re-plan. Mutant: counting every approved gate as first-gate -> 4/5.
    store = tmp_path / "store"
    rows = [trow("r", f"K{i}") for i in range(1, 8)]
    gates = []
    for i in range(1, 4):
        gates.append(grow("r", f"K{i}", "approved", "first"))
    for i in range(4, 6):
        gates.append(grow("r", f"K{i}", "rejected", "first"))
    gates.append(grow("r", "K6", "approved", "fix"))
    gates.append(grow("r", "K7", "rejected", "replan"))
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert (
        "all: first-gate approved 3/5 (60%); fix-round approved 1/1; "
        "re-plan approved 0/1" in lines
    )


def test_min_n_boundary_four_vs_five(tmp_path):
    # Four gated rows refuse; the fifth un-refuses. Mutant: `>` for `>=` ->
    # five rows still refuse.
    store4 = tmp_path / "s4"
    write(
        store4,
        [trow("r", f"K{i}") for i in range(1, 5)],
        [grow("r", f"K{i}", "approved") for i in range(1, 5)],
    )
    lines = rp.harness_report(str(store4))
    assert "all: insufficient (n=4)" in lines
    assert not any(l.startswith("all: first-gate approved") for l in lines)

    store5 = tmp_path / "s5"
    write(
        store5,
        [trow("r", f"K{i}") for i in range(1, 6)],
        [grow("r", f"K{i}", "approved") for i in range(1, 6)],
    )
    lines = rp.harness_report(str(store5))
    assert (
        "all: first-gate approved 5/5 (100%); fix-round approved 0/0; re-plan approved 0/0"
        in lines
    )


def test_median_output_tokens_even_count(tmp_path):
    # Approved outputs [10,20,30,40] -> median 25 (lower-median of the even
    # pair); rejected [5,100,7] -> 7. Mutant: upper median -> 30.
    store = tmp_path / "store"
    rows = [trow("r", f"A{i}") for i in range(1, 5)]
    rows += [trow("r", f"B{i}") for i in range(1, 4)]
    gates = [grow("r", f"A{i}", "approved") for i in range(1, 5)]
    gates += [grow("r", f"B{i}", "rejected") for i in range(1, 4)]
    for i, r in enumerate([10, 20, 30, 40]):
        rows[i]["usage"]["out"] = r
    for i, r in enumerate([5, 100, 7]):
        rows[4 + i]["usage"]["out"] = r
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert (
        "all: median output tokens approved 25 / rejected 7; "
        "median wall_s approved 600 / rejected 600" in lines
    )


def test_gateless_row_in_population_not_fractions(tmp_path):
    # Six task rows, five gated: the gateless row counts in population but no
    # fraction. Mutant: counting a gateless row as rejected -> 3/6.
    store = tmp_path / "store"
    rows = [trow("r", f"K{i}") for i in range(1, 7)]
    gates = []
    for i in (1, 2, 3):
        gates.append(grow("r", f"K{i}", "approved"))
    for i in (4, 5):
        gates.append(grow("r", f"K{i}", "rejected"))
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert "population: 6 task rows, 5 with a gate verdict" in lines
    assert (
        "all: first-gate approved 3/5 (60%); fix-round approved 0/0; "
        "re-plan approved 0/0" in lines
    )
    assert not any("3/6" in l for l in lines)


def test_error_class_sorted_by_count_then_name(tmp_path):
    # none×2, no-result-line×1, template-echo×1. Mutant: sort by name alone ->
    # "none" drops below "no-result-line".
    store = tmp_path / "store"
    write(
        store,
        [
            trow("r", "K1", error_class="none"),
            trow("r", "K2", error_class="none"),
            trow("r", "K3", error_class="no-result-line"),
            trow("r", "K4", error_class="template-echo"),
        ],
        [],
    )
    lines = rp.harness_report(str(store))
    assert "error_class: none 2, no-result-line 1, template-echo 1" in lines


def test_plan_defect_counts_rejected_only(tmp_path):
    # Rejected gates: missing-case×2, vacuous×1, None×1 (->unclassified); one
    # approved gate carrying `none` does not count. Mutant: counting approved
    # gates -> `none 1` appears.
    store = tmp_path / "store"
    rows = [trow("r", f"K{i}") for i in range(1, 6)]
    gates = [
        grow("r", "K1", "rejected", plan_defect="missing-case"),
        grow("r", "K2", "rejected", plan_defect="missing-case"),
        grow("r", "K3", "rejected", plan_defect="vacuous"),
        grow("r", "K4", "rejected", plan_defect=None),
        grow("r", "K5", "approved", plan_defect="none"),
    ]
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert "plan_defect: missing-case 2, unclassified 1, vacuous 1" in lines


def test_groups_are_all_then_present_pairs_only(tmp_path):
    # Five gated code/S rows + one gated docs/S row: `code/S` reaches n=5,
    # `docs/S` refuses, and no absent pair like `docs/XS` prints. Mutant:
    # emitting every enum pair -> a `docs/XS: insufficient (n=0)` line.
    store = tmp_path / "store"
    rows = [trow("r", f"K{i}") for i in range(1, 6)]
    rows.append(trow("r", "D1", kind="docs", size="S"))
    gates = [grow("r", f"K{i}", "approved") for i in range(1, 6)]
    gates.append(grow("r", "D1", "approved"))
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert any(l.startswith("code/S: first-gate approved") for l in lines)
    assert "docs/S: insufficient (n=1)" in lines
    assert not any("docs/XS" in l for l in lines)


def test_tags_and_rung_lines_verbatim(tmp_path):
    store = tmp_path / "store"
    write(store, [trow("r", "K1")], [grow("r", "K1", "approved")])
    lines = rp.harness_report(str(store))
    assert TAGS_LINE in lines
    assert RUNG_LINE in lines


def test_cli_malformed_date_and_empty_store(tmp_path, capsys):
    store = tmp_path / "store"
    store.mkdir()
    rc = rp.main(["--store", str(store), "harness", "--before", "2026-13-01"])
    assert rc == 2
    assert "report: --before 2026-13-01: invalid date (YYYY-MM-DD)" in (
        capsys.readouterr().err
    )

    rc = rp.main(["--store", str(store), "harness"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "population: 0 task rows, 0 with a gate verdict" in out
    assert "all: insufficient (n=0)" in out
    assert "error_class: none 0" in out
    assert "plan_defect: unclassified 0" in out


def test_cli_store_forwarded(tmp_path):
    store = tmp_path / "store"
    write(store, [trow("r", "K1")], [grow("r", "K1", "approved")])
    proc = subprocess.run(
        [sys.executable, str(SRC), "--store", str(store), "report", "harness"],
        capture_output=True,
        text=True,
        check=False,
        env=dict(os.environ),
    )
    assert proc.returncode == 0
    assert HARNESS_HEADER in proc.stdout


def test_split_window_and_malformed_date(tmp_path, capsys):
    # The split day (2026-09-08) is in the after window; 2026-09-07 is in the
    # before. Mutant: `>` for `>=` -> the split day lands before.
    store = tmp_path / "store"
    write(
        store,
        [
            trow("r", "A1", mtime="2026-09-07T00:00:00Z"),
            trow("r", "A2", mtime="2026-09-08T00:00:00Z"),
            trow("r", "A3", mtime="2026-09-09T00:00:00Z"),
        ],
        [],
    )
    lines = rp.harness_report(str(store), split="2026-09-08")
    assert "population: 1 task rows, 0 with a gate verdict" in lines
    assert (
        "after: since 2026-09-08 before open; 2 task rows, 0 with a gate "
        "verdict, 0 approved" in lines
    )

    rc = rp.main(["--store", str(store), "harness", "--split", "2026-13-01"])
    assert rc == 2
    assert "report: --split 2026-13-01: invalid date (YYYY-MM-DD)" in (
        capsys.readouterr().err
    )


def test_touches_change_line_and_verdict(tmp_path):
    # Five touches-violation rows, gates rejected, rejected, approved,
    # rejected, approved (by result_mtime). Mutant: `>` for `>=` on the
    # overruled threshold -> keep at exactly 2.
    counter = 0

    def build(verdicts):
        nonlocal counter
        store = tmp_path / f"store{counter}"
        counter += 1
        rows = []
        gates = []
        for i, v in enumerate(verdicts):
            mtime = f"2026-09-07T{i:02d}:00:00Z"
            rows.append(
                trow(
                    "r",
                    f"K{i}",
                    mtime=mtime,
                    error_class="touches-violation",
                    touches=(1, 1),
                )
            )
            gates.append(grow("r", f"K{i}", v))
        write(store, rows, gates)
        return rp.harness_report(str(store))

    lines = build(["rejected", "rejected", "approved", "rejected", "approved"])
    assert (
        "touches: n=5; demotions 5 (touches-violation); agreed 3 (gate "
        "rejected); overruled 2 (gate approved); ungated 0; undisclosed extras "
        "0 rows" in lines
    )
    assert "verdict touches: revert (overruled 2 of 5)" in lines

    lines = build(["rejected", "rejected", "approved", "rejected", "rejected"])
    assert "verdict touches: keep (overruled 1 of 5)" in lines

    lines = build(["rejected", "rejected", "approved", "rejected"])
    assert "verdict touches: insufficient (n=4)" in lines


def test_verdict_first_five_only(tmp_path):
    # Seven gated demotions; the overruled ones are the 6th and 7th by
    # result_mtime. Mutant: counting every overruled row -> revert.
    store = tmp_path / "store"
    verdicts = ["rejected"] * 5 + ["approved", "approved"]
    rows = []
    gates = []
    for i, v in enumerate(verdicts):
        mtime = f"2026-09-07T{i:02d}:00:00Z"
        rows.append(
            trow(
                "r",
                f"K{i}",
                mtime=mtime,
                error_class="touches-violation",
                touches=(1, 1),
            )
        )
        gates.append(grow("r", f"K{i}", v))
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert "verdict touches: keep (overruled 0 of 5)" in lines


def test_verdict_zero_demotions_suffix(tmp_path):
    # Ten rows with touches_extra not None and no demotion -> the zero
    # demotions suffix; nine -> no suffix. Mutant: `>` for `>=`.
    def build(n, name):
        store = tmp_path / name
        rows = [trow("r", f"K{i}", touches=(1, 1)) for i in range(n)]
        write(store, rows, [])
        return rp.harness_report(str(store))

    lines = build(10, "s10")
    assert (
        "verdict touches: insufficient (n=0); zero demotions in 10 tasks — "
        "keep only if the target tag fell to zero (tags unmeasured)" in lines
    )
    lines = build(9, "s9")
    assert "verdict touches: insufficient (n=0)" in lines
    assert not any("zero demotions" in l for l in lines)


def test_checks_change_line_verify_timeout_not_demotion(tmp_path):
    # Two checks-misreported, one checks-unverifiable, one verify-timeout.
    # Mutant: counting verify-timeout as a demotion -> agreed/overruled/ungated
    # sum to 4.
    store = tmp_path / "store"
    rows = [
        trow(
            "r", "C0", error_class="checks-misreported", checks_verified={"u": "fail"}
        ),
        trow(
            "r", "C1", error_class="checks-misreported", checks_verified={"u": "fail"}
        ),
        trow(
            "r", "C2", error_class="checks-unverifiable", checks_verified={"u": "fail"}
        ),
        trow("r", "C3", error_class="verify-timeout", checks_verified={"u": "fail"}),
    ]
    gates = [
        grow("r", "C0", "rejected"),
        grow("r", "C1", "rejected"),
        grow("r", "C2", "approved"),
        grow("r", "C3", "approved"),
    ]
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert (
        "checks: n=4; demotions checks-misreported 2, checks-unverifiable 1; "
        "agreed 2; overruled 1; ungated 0; verify-timeout 1" in lines
    )


def test_probes_change_line(tmp_path):
    # probe-mismatch (approved), probe-missing (no gate), and a pass row whose
    # map carries a drift value. Mutant: counting drift as a demotion.
    store = tmp_path / "store"
    rows = [
        trow("r", "P0", error_class="probe-mismatch", probes_verified={"p": "fail"}),
        trow("r", "P1", error_class="probe-missing", probes_verified={"p": "missing"}),
        trow("r", "P2", probes_verified={"p": "pass", "q": "drift"}),
    ]
    gates = [grow("r", "P0", "approved")]
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert (
        "probes: n=3; demotions probe-mismatch 1, probe-missing 1; agreed 0; "
        "overruled 1; ungated 1; drift 1" in lines
    )


def test_unreported_change_line(tmp_path):
    # Three unreported rows, two gated, one approved (the ungated one carries
    # neither).
    store = tmp_path / "store"
    rows = [
        trow("r", "U0", status="unreported"),
        trow("r", "U1", status="unreported"),
        trow("r", "U2", status="unreported"),
    ]
    gates = [grow("r", "U0", "approved"), grow("r", "U1", "rejected")]
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert "unreported: n=3; gated 2; approved 1" in lines


def test_control_false_positives(tmp_path):
    # Two touches-overruled + one probes-overruled over eight approved rows.
    # Mutant: counting over every row -> 3 of 12.
    store = tmp_path / "store"
    rows = [
        trow("r", "T0", error_class="touches-violation", touches=(1, 1)),
        trow("r", "T1", error_class="touches-violation", touches=(1, 1)),
        trow("r", "P0", error_class="probe-mismatch", probes_verified={"p": "fail"}),
    ]
    gates = [
        grow("r", "T0", "approved"),
        grow("r", "T1", "approved"),
        grow("r", "P0", "approved"),
    ]
    for i in range(5):
        rows.append(trow("r", f"A{i}"))
        gates.append(grow("r", f"A{i}", "approved"))
    for i in range(4):
        rows.append(trow("r", f"R{i}"))
        gates.append(grow("r", f"R{i}", "rejected"))
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert "control false positives: 3 of 8 approved rows" in lines


def test_success_line_before_after(tmp_path):
    # Before 3/5 approved with five out=100 (bound 150); after 4/5 approved.
    # Mutant: `<` for `<=` -> no at exactly 150.
    split = "2026-09-08"
    counter = 0

    def build(after_outs, after_fix=True):
        nonlocal counter
        store = tmp_path / f"store{counter}"
        counter += 1
        rows = []
        gates = []
        for i in range(5):
            v = "approved" if i < 3 else "rejected"
            rows.append(trow("b", f"B{i}", mtime="2026-09-01T00:00:00Z", out=100))
            gates.append(grow("b", f"B{i}", v, "first"))
        for i in range(2):
            rows.append(trow("b", f"BF{i}", mtime="2026-09-01T00:00:00Z", out=100))
            gates.append(grow("b", f"BF{i}", "approved", "fix"))
        for i in range(5):
            v = "approved" if i < 4 else "rejected"
            rows.append(
                trow("a", f"A{i}", mtime="2026-09-08T00:00:00Z", out=after_outs[i])
            )
            gates.append(grow("a", f"A{i}", v, "first"))
        if after_fix:
            rows.append(
                trow("a", "AF", mtime="2026-09-08T00:00:00Z", out=after_outs[0])
            )
            gates.append(grow("a", "AF", "approved", "fix"))
        write(store, rows, gates)
        return rp.harness_report(str(store), split=split)

    lines = build([140] * 5)
    assert (
        "success: first-gate approved before 3/5 (60%) → after 4/5 (80%); "
        "output tokens per landing after 140 against control median × 1.5 = "
        "150: yes" in lines
    )
    lines = build([160] * 5)
    assert any("median × 1.5 = 150: no" in l for l in lines)
    lines = build([150] * 5)
    assert any("median × 1.5 = 150: yes" in l for l in lines)
    lines = build([140] * 5, after_fix=False)
    assert any("insufficient (n=4)" in l for l in lines)


def test_untargeted_line_sums_non_none(tmp_path):
    # Gates carrying mutants_outside_named 2, 0 and None -> 2 over 2 gates.
    # Mutant: counting None as a carrying gate -> over 3.
    store = tmp_path / "store"
    rows = [trow("r", f"K{i}") for i in range(3)]
    gates = [
        grow("r", "K0", "approved", mutants_outside_named=2),
        grow("r", "K1", "rejected", mutants_outside_named=0),
        grow("r", "K2", "approved"),
    ]
    write(store, rows, gates)
    lines = rp.harness_report(str(store))
    assert (
        "untargeted: never-ran-named-mutants, one-arm-per-enum, "
        "ignored-section-item — unmeasured in the store; proxy: "
        "mutants_outside_named summed over the after window's gates = 2 over "
        "2 gates carrying the field" in lines
    )


def test_no_split_before_figures_dash(tmp_path):
    # Without --split the before figures print `-` and the change lines cover
    # the whole window.
    store = tmp_path / "store"
    rows = [
        trow("r", "A0", mtime="2026-09-01T00:00:00Z", touches=(1, 1)),
        trow("r", "A1", mtime="2026-09-15T00:00:00Z", touches=(1, 1)),
    ]
    write(store, rows, [])
    lines = rp.harness_report(str(store))
    assert any(l.startswith("after: since open before open;") for l in lines)
    assert any(l.startswith("touches: n=2; demotions 0") for l in lines)
    assert any(l.startswith("success: first-gate approved before -") for l in lines)
