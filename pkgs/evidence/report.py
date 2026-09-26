"""`evidence report plans` — the planning-agent metrics joined to first-gate outcomes (plan 2026-09-06-planning-agent, P10).

Every line here is a proxy for one design §7 goal; each number prints its n and
no conclusion is offered below five chains. The report reads the P6 `plans`
stream, the repo's typed plan graph through `tasks.read_reviews` /
`tasks.parse_plan` / `tasks.chain_root`, and the P3A plan-defect ledger
(`docs/ledger/plan-defects.toml`) for the plan-caused share over all rejection
rows. When telemetry T10a/T10b land, the rubric join moves onto their reader
layer; these output lines stay.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import fnmatch
import json
import os
import pathlib
import re
import statistics
import sys

import evidence
import tasks

HEADER = (
    "# evidence report plans — proxies for "
    "docs/superpowers/specs/2026-09-05-planning-agent-design.md §7; "
    "n printed with every figure"
)

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

LADDER_HEADER = (
    "# evidence report ladder — the seat driver's ladder "
    "(spec 2026-09-06-operator-seat-driver-design.md §6); n printed with every "
    "line; refused under {min_n}"
)

ORCHESTRATE_HEADER = "# orchestrate — drive sessions (run.meta driver: ⋈ job.json)"


class ReportUnreadable(Exception):
    """The store or repo named on the command line cannot be read."""


def _members(reviews, root):
    """The ordered members of a chain: the root first, then any reviewed key
    whose `chain_root` is this root."""
    ms = {root}
    for k in reviews:
        if tasks.chain_root(k) == root:
            ms.add(k)
    return sorted(ms, key=lambda k: (k != root, k))


def _first_try(reviews, roots):
    """(a, n) over the given chain roots: `a` approved at their own first
    gate, `n` gated (at least one review among members)."""
    a = n = 0
    for root in roots:
        ms = _members(reviews, root)
        if any(m in reviews for m in ms):
            n += 1
            if root in reviews and reviews[root]["verdict"] == "APPROVED":
                a += 1
    return a, n


def _pct(num, den):
    if den == 0:
        return 0
    return round(num * 100 / den)


def _survivors(repo):
    """(sum, gates) of `mutants_outside_named` across every review front-matter
    block; unreadable or non-integer values are skipped, not errors."""
    reviews_dir = pathlib.Path(repo) / "docs" / "reviews"
    total = 0
    gates = 0
    if not reviews_dir.is_dir():
        return total, gates
    for path in sorted(reviews_dir.glob("*.md")):
        _, block, _, _ = tasks._read_review(path)
        value = block.get("mutants_outside_named")
        if value is None:
            continue
        try:
            total += int(value)
        except (TypeError, ValueError):
            continue
        gates += 1
    return total, gates


def _all_rows_record(repo):
    """(total, counts) of every rejection row over all rows (no window): every
    ledger row plus every block on a file dated >= `front_matter_from` whose H1
    verdict is REJECTED. A file in both counts once (the block wins); an
    APPROVED block never counts. Returns None when the ledger is unreadable."""
    loaded = tasks._plan_defects_for(repo)
    if loaded is None:
        return None
    fmf, rows = loaded
    block_primary = {}
    reviews_dir = pathlib.Path(repo) / "docs" / "reviews"
    if fmf is not None and reviews_dir.is_dir():
        for path in sorted(reviews_dir.glob("*opus-review*.md")):
            date = tasks._review_date(path.name)
            if date is None or date < fmf:
                continue
            has_block, block, first, lookahead = tasks._read_review(path)
            if not has_block:
                continue
            m = tasks._review_h1(first, lookahead)
            if m is None or m["verdict"] != "REJECTED":
                continue
            pd = block.get("plan_defect")
            if pd is not None:
                block_primary["docs/reviews/" + path.name] = pd
    total = 0
    counts = {}
    for pd in block_primary.values():
        total += 1
        counts[pd] = counts.get(pd, 0) + 1
    for row in rows:
        pd = row.get("plan_defect")
        date = row.get("date")
        review = row.get("review")
        if pd is None or date is None:
            continue
        if review in block_primary:
            continue
        total += 1
        counts[pd] = counts.get(pd, 0) + 1
    return (total, counts)


def _latest_by_plan(rows):
    """The judgement rows, one per plan: the highest `revision` wins (ties keep
    the later row), ordered by plan basename. A plan judged twice prints one
    line and counts once toward j and the ten-plan threshold."""
    latest = {}
    for r in rows:
        name = os.path.basename(r.get("plan", ""))
        rev = r.get("revision") or 0
        if name not in latest or rev >= latest[name][1]:
            latest[name] = (r, rev)
    return {name: row for name, (row, _) in sorted(latest.items())}


def plans_report(store, repo, today=None, min_n=5, plan=None):
    """The report's lines. Raises `ReportUnreadable` when the store, repo or
    `--today` is unusable; exit status is always 0 otherwise."""
    if not pathlib.Path(repo).is_dir():
        raise ReportUnreadable(f"cannot read repo {os.path.abspath(repo)}")
    try:
        rows = [
            r
            for r in evidence.read(store, "plans")
            if r.get("kind") == "plan-judgement"
        ]
    except OSError as exc:
        raise ReportUnreadable(f"cannot read store {store}: {exc}")

    if today is not None:
        try:
            datetime.date.fromisoformat(today)
        except ValueError:
            raise ReportUnreadable(f"--today {today}: invalid date (YYYY-MM-DD)")

    reviews = tasks.read_reviews(repo)
    root_plan = {}
    plans_dir = pathlib.Path(repo) / "docs" / "superpowers" / "plans"
    if plans_dir.is_dir():
        for path in sorted(plans_dir.glob("*.md")):
            for t in tasks.parse_plan(path)["tasks"]:
                root_plan.setdefault(tasks.chain_root(t["key"]), path.name)
    roots = list(root_plan)
    if plan is not None:
        roots = [r for r in roots if fnmatch.fnmatch(root_plan[r], plan)]

    lines = [HEADER]

    # Lines 1–4 — gated on the number of chains that went through a gate.
    gated = [r for r in roots if any(m in reviews for m in _members(reviews, r))]
    n = len(gated)
    if n < min_n:
        lines.append(f"refused: n={n} < {min_n} (no conclusion under {min_n})")
    else:
        a, _ = _first_try(reviews, gated)
        lines.append(f"first-try landing rate: {a}/{n} chains ({_pct(a, n)}%)")

        record = _all_rows_record(repo)
        if record is None:
            total, counts = 0, {}
        else:
            total, counts = record
        m = sum(counts.get(c, 0) for c in tasks.PLAN_DEFECT_CAUSED)
        if total == 0:
            lines.append("plan-caused share of rejections: unmeasured (n=0)")
        else:
            lines.append(
                f"plan-caused share of rejections: {m}/{total} ({_pct(m, total)}%)"
            )

        replan = 0
        for root in gated:
            if any("r" in k[len(root) :] for k in _members(reviews, root) if k != root):
                replan += 1
        lines.append(f"re-plan rate: {replan}/{n} chains")

        # Rounds over landed chains only: members beyond the root across chains
        # whose last member approved.
        landed = 0
        landed_set = set()
        for root in gated:
            ms = _members(reviews, root)
            if ms and ms[-1] in reviews and reviews[ms[-1]]["verdict"] == "APPROVED":
                landed += 1
                landed_set.add(root)
        rounds = sum(
            1
            for k in reviews
            if k != tasks.chain_root(k) and tasks.chain_root(k) in landed_set
        )
        if landed == 0:
            lines.append("rework rounds per landed task: unmeasured (n=0)")
        else:
            lines.append(
                f"rework rounds per landed task: {rounds}/{landed} = {rounds / landed:.2f}"
            )

    # Line 5 — the rubric join, gated on the number of judged plans.
    latest = _latest_by_plan(rows)
    j = len(latest)
    if j < 5:
        lines.append(f"rubric score before dispatch: n={j}, refused")
    else:
        lines.append(f"rubric score before dispatch: n={j}")
        for plan_name, r in latest.items():
            p_roots = [root for root in root_plan if root_plan[root] == plan_name]
            a, pn = _first_try(reviews, p_roots)
            lines.append(
                f"{plan_name} total {r.get('total')} decision {r.get('decision')} "
                f"first-try {f'{a}/{pn}' if pn else '—/0'}"
            )
        surv_sum, surv_gates = _survivors(repo)
        if surv_gates:
            lines.append(f"survivors outside the named set: {surv_sum}/{surv_gates}")
        else:
            lines.append("unmeasured (no review carries mutants_outside_named)")
        lines.append("operator interventions per plan: unmeasured")

    # Line 6 — the threshold proposal, once ten dispatched plans are judged.
    dispatched = [r for r in latest.values() if r.get("decision") == "dispatch"]
    if len(dispatched) >= 10:
        candidates = []
        for r in dispatched:
            plan_name = os.path.basename(r.get("plan", ""))
            p_roots = [root for root in root_plan if root_plan[root] == plan_name]
            a, pn = _first_try(reviews, p_roots)
            if pn and a / pn >= 0.70:
                candidates.append(r.get("total"))
        if candidates:
            lines.append(f"threshold proposal: {min(candidates)}")
        else:
            lines.append("no score separates ≥ 70% first-try plans yet")

    return lines


def _window(rows, since, before):
    """The window: `since <= result_mtime[:10] < before`, `since` inclusive,
    `before` exclusive, an absent bound open. Rows with no `result_mtime` are
    out of every bounded window and in the open one."""
    out = []
    for r in rows:
        mt = r["task"].get("result_mtime")
        if mt is None:
            if since is None and before is None:
                out.append(r)
            continue
        d = mt[:10]
        if since is not None and d < since:
            continue
        if before is not None and not (d < before):
            continue
        out.append(r)
    return out


def _median_or_dash(values):
    if not values:
        return "-"
    return str(round(statistics.median(values)))


def _by_verdict(rows, verdict):
    return [r for r in rows if r["gate"].get("verdict") == verdict]


def _first_gate(gated):
    """(approved, n) over first-round gates: the first-gate landing fraction."""
    first = [r for r in gated if r["gate"].get("round_kind") == "first"]
    a = sum(1 for r in first if r["gate"].get("verdict") == "approved")
    return a, len(first)


def _median_out(gated):
    """The rounded median `usage.out` over approved gated rows; None when no
    approved row carries an `out` value."""
    values = [
        v
        for r in gated
        if r["gate"].get("verdict") == "approved"
        if (v := (r["task"].get("usage") or {}).get("out")) is not None
    ]
    if not values:
        return None
    return round(statistics.median(values))


def _fmt_num(value):
    """A number with a whole float's trailing `.0` stripped; `-` for None."""
    if value is None:
        return "-"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


_DEMOTION_ARMS = {
    "touches": ("touches-violation",),
    "checks": ("checks-misreported", "checks-unverifiable"),
    "probes": ("probe-mismatch", "probe-missing"),
    "unreported": (),
}


def _demotions(rows, arms):
    """The rows whose `error_class` is one of `arms` (the demotions)."""
    return [r for r in rows if r["task"].get("error_class") in arms]


def _agreed_overruled_ungated(demotions):
    """(agreed, overruled, ungated) of demotion rows by gate verdict: agreed =
    rejected, overruled = approved, ungated = no gate."""
    agreed = sum(
        1
        for r in demotions
        if r["gate"] is not None and r["gate"].get("verdict") == "rejected"
    )
    overruled = sum(
        1
        for r in demotions
        if r["gate"] is not None and r["gate"].get("verdict") == "approved"
    )
    ungated = sum(1 for r in demotions if r["gate"] is None)
    return agreed, overruled, ungated


def _verdict_line(name, rows, demotions, n):
    """The `verdict <change>:` line: the first five gated demotions ordered by
    `result_mtime` (ties by `run_id`, `key`) decide revert vs keep."""
    gated = [r for r in demotions if r["gate"] is not None]
    gated.sort(
        key=lambda r: (r["task"].get("result_mtime") or "", r["run_id"], r["key"])
    )
    if len(gated) < 5:
        verdict = f"insufficient (n={len(gated)})"
    else:
        o = sum(1 for r in gated[:5] if r["gate"].get("verdict") == "approved")
        verdict = (
            f"revert (overruled {o} of 5)" if o >= 2 else f"keep (overruled {o} of 5)"
        )
    line = f"verdict {name}: {verdict}"
    if n >= 10 and not demotions:
        line += (
            f"; zero demotions in {n} tasks — keep only if the target tag "
            "fell to zero (tags unmeasured)"
        )
    return line


def _harness_after_block(after_rows, after_gated, baseline_gated, split, before, min_n):
    """The after-window block (SH6 lines 9–14): the change lines, the control
    false positives, the per-change verdicts, the success line and the
    untargeted proxy."""
    approved = _by_verdict(after_gated, "approved")
    lines = [
        (
            f"after: since {split or 'open'} before {before or 'open'}; "
            f"{len(after_rows)} task rows, {len(after_gated)} with a gate "
            f"verdict, {len(approved)} approved"
        )
    ]

    overruled_total = 0
    verdict_lines = []
    for name, crows in [
        (
            "touches",
            [r for r in after_rows if r["task"].get("touches_extra") is not None],
        ),
        (
            "checks",
            [r for r in after_rows if r["task"].get("checks_verified") is not None],
        ),
        (
            "probes",
            [r for r in after_rows if r["task"].get("probes_verified") is not None],
        ),
        (
            "unreported",
            [r for r in after_rows if r["task"].get("status") == "unreported"],
        ),
    ]:
        n = len(crows)
        arms = _DEMOTION_ARMS[name]
        demotions = _demotions(crows, arms)
        agreed, overruled, ungated = _agreed_overruled_ungated(demotions)
        overruled_total += overruled
        if name == "touches":
            x = sum(
                1
                for r in crows
                if (r["task"].get("touches_extra") or 0)
                > (r["task"].get("touches_disclosed") or 0)
            )
            lines.append(
                f"touches: n={n}; demotions {len(demotions)} (touches-violation); "
                f"agreed {agreed} (gate rejected); overruled {overruled} "
                f"(gate approved); ungated {ungated}; undisclosed extras {x} rows"
            )
        elif name == "checks":
            d1 = sum(
                1
                for r in demotions
                if r["task"].get("error_class") == "checks-misreported"
            )
            d2 = sum(
                1
                for r in demotions
                if r["task"].get("error_class") == "checks-unverifiable"
            )
            t = sum(
                1 for r in crows if r["task"].get("error_class") == "verify-timeout"
            )
            lines.append(
                f"checks: n={n}; demotions checks-misreported {d1}, "
                f"checks-unverifiable {d2}; agreed {agreed}; overruled {overruled}; "
                f"ungated {ungated}; verify-timeout {t}"
            )
        elif name == "probes":
            d1 = sum(
                1 for r in demotions if r["task"].get("error_class") == "probe-mismatch"
            )
            d2 = sum(
                1 for r in demotions if r["task"].get("error_class") == "probe-missing"
            )
            drift = sum(
                1
                for r in crows
                if any(
                    v == "drift"
                    for v in (r["task"].get("probes_verified") or {}).values()
                )
            )
            lines.append(
                f"probes: n={n}; demotions probe-mismatch {d1}, probe-missing {d2}; "
                f"agreed {agreed}; overruled {overruled}; ungated {ungated}; drift {drift}"
            )
        else:
            gated = sum(1 for r in crows if r["gate"] is not None)
            approved_n = sum(
                1
                for r in crows
                if r["gate"] is not None and r["gate"].get("verdict") == "approved"
            )
            lines.append(f"unreported: n={n}; gated {gated}; approved {approved_n}")
        verdict_lines.append(_verdict_line(name, crows, demotions, n))

    lines.append(
        f"control false positives: {overruled_total} of {len(approved)} approved rows"
    )
    lines.extend(verdict_lines)

    if split is None:
        before_part = "-"
        control = None
        bound = None
        before_approved = []
    else:
        a, n = _first_gate(baseline_gated)
        before_part = f"{a}/{n} ({_pct(a, n)}%)"
        control = _median_out(baseline_gated)
        bound = control * 1.5 if control is not None else None
        before_approved = _by_verdict(baseline_gated, "approved")
    a2, n2 = _first_gate(after_gated)
    after_part = f"{a2}/{n2} ({_pct(a2, n2)}%)"
    after_median = _median_out(after_gated)
    after_approved = _by_verdict(after_gated, "approved")
    if len(before_approved) < min_n:
        result = f"insufficient (n={len(before_approved)})"
    elif len(after_approved) < min_n:
        result = f"insufficient (n={len(after_approved)})"
    elif after_median is None or bound is None:
        result = "insufficient (n=0)"
    else:
        result = "yes" if after_median <= bound else "no"
    lines.append(
        f"success: first-gate approved before {before_part} → after {after_part}; "
        f"output tokens per landing after {_fmt_num(after_median)} against control "
        f"median × 1.5 = {_fmt_num(bound)}: {result}"
    )

    s = 0
    carrying = 0
    for r in after_gated:
        v = r["gate"].get("mutants_outside_named")
        if v is not None:
            s += v
            carrying += 1
    lines.append(
        "untargeted: never-ran-named-mutants, one-arm-per-enum, "
        "ignored-section-item — unmeasured in the store; proxy: "
        "mutants_outside_named summed over the after window's gates = "
        f"{s} over {carrying} gates carrying the field"
    )
    return lines


def harness_report(store, before=None, since=None, split=None, min_n=5):
    """The report's lines. Raises `ReportUnreadable` when the store or a date
    bound is unusable; exit status is always 0 otherwise."""
    for name, value in (("--before", before), ("--since", since), ("--split", split)):
        if value is None:
            continue
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            raise ReportUnreadable(f"{name} {value}: invalid date (YYYY-MM-DD)")

    try:
        rows = evidence.join_tasks_gates(store)
    except OSError as exc:
        raise ReportUnreadable(f"cannot read store {store}: {exc}")

    if split is not None:
        baseline_rows = _window(rows, since, split)
        after_rows = _window(rows, split, before)
    else:
        baseline_rows = _window(rows, since, before)
        after_rows = baseline_rows
    baseline_gated = [r for r in baseline_rows if r["gate"] is not None]
    after_gated = [r for r in after_rows if r["gate"] is not None]

    lines = [HARNESS_HEADER]
    sh_before = split if split is not None else before
    lines.append(f"window: since {since or 'open'} before {sh_before or 'open'}")
    lines.append(
        f"population: {len(baseline_rows)} task rows, {len(baseline_gated)} "
        "with a gate verdict"
    )

    groups = ["all"] + sorted(
        {f"{r['task'].get('task_kind')}/{r['task'].get('size')}" for r in baseline_rows}
    )
    for group in groups:
        if group == "all":
            gr = baseline_gated
        else:
            kind, size = group.split("/")
            gr = [
                r
                for r in baseline_gated
                if r["task"].get("task_kind") == kind and r["task"].get("size") == size
            ]
        if len(gr) < min_n:
            lines.append(f"{group}: insufficient (n={len(gr)})")
            continue
        first = [r for r in gr if r["gate"].get("round_kind") == "first"]
        fix = [r for r in gr if r["gate"].get("round_kind") == "fix"]
        replan = [r for r in gr if r["gate"].get("round_kind") == "replan"]
        a = sum(1 for r in first if r["gate"].get("verdict") == "approved")
        b = sum(1 for r in fix if r["gate"].get("verdict") == "approved")
        c = sum(1 for r in replan if r["gate"].get("verdict") == "approved")
        n = len(first)
        p = round(a * 100 / n) if n else 0
        lines.append(
            f"{group}: first-gate approved {a}/{n} ({p}%); "
            f"fix-round approved {b}/{len(fix)}; re-plan approved {c}/{len(replan)}"
        )
        app = _by_verdict(gr, "approved")
        rej = _by_verdict(gr, "rejected")
        app_out = [
            v
            for r in app
            if (v := (r["task"].get("usage") or {}).get("out")) is not None
        ]
        rej_out = [
            v
            for r in rej
            if (v := (r["task"].get("usage") or {}).get("out")) is not None
        ]
        app_wall = [v for r in app if (v := r["task"].get("wall_s")) is not None]
        rej_wall = [v for r in rej if (v := r["task"].get("wall_s")) is not None]
        lines.append(
            f"{group}: median output tokens approved {_median_or_dash(app_out)} "
            f"/ rejected {_median_or_dash(rej_out)}; median wall_s approved "
            f"{_median_or_dash(app_wall)} / rejected {_median_or_dash(rej_wall)}"
        )

    error_classes = collections.Counter(
        r["task"].get("error_class") for r in baseline_rows
    )
    if error_classes:
        items = sorted(error_classes.items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append("error_class: " + ", ".join(f"{k} {v}" for k, v in items))
    else:
        lines.append("error_class: none 0")

    plan_defects = collections.Counter(
        r["gate"].get("plan_defect") or "unclassified"
        for r in baseline_gated
        if r["gate"].get("verdict") == "rejected"
    )
    if plan_defects:
        items = sorted(plan_defects.items(), key=lambda kv: (-kv[1], kv[0]))
        lines.append("plan_defect: " + ", ".join(f"{k} {v}" for k, v in items))
    else:
        lines.append("plan_defect: unclassified 0")

    lines.append(TAGS_LINE)
    lines.append(RUNG_LINE)
    lines.extend(
        _harness_after_block(
            after_rows, after_gated, baseline_gated, split, before, min_n
        )
    )
    return lines


def _route_kind_size(route):
    """kind/size from a `route:` value (`implement/<kind>/<size>`), else
    `unknown` for both (an `explicit`, a torn or an absent route never raises)."""
    m = re.fullmatch(r"implement/([^/]+)/([^/]+)", (route or "").strip())
    if m is not None:
        return m.group(1), m.group(2)
    return "unknown", "unknown"


def _rung(value):
    """The leading integer of a `rung:` value; absent/non-numeric reads 1."""
    m = re.match(r"(\d+)", (value or "").strip())
    return int(m.group(1)) if m is not None else 1


def _as_int(value):
    """`value` as an int, else None (a `wall_s` that is not a number is skipped
    by the median, not an error)."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_review(repo, runs_dir, run, key):
    """A row's gate verdict: the Opus review `*opus-review*-<run>-<key>.md` H1
    (APPROVED/REJECTED), else the run directory's `<key>.review.md`
    `FACTORY-REVIEW verdict=` line (approve -> approved, rework/reject ->
    rejected), else None. Each run's own review is read — never a key-wide
    collapse."""
    d = pathlib.Path(repo) / "docs" / "reviews"
    if d.is_dir():
        for path in sorted(d.glob(f"*opus-review*-{run}-{key}.md")):
            _, _, first, lookahead = tasks._read_review(path)
            m = tasks._review_h1(first, lookahead)
            if m is not None:
                return "approved" if m["verdict"] == "APPROVED" else "rejected"
    p = pathlib.Path(runs_dir) / run / f"{key}.review.md"
    try:
        text = p.read_text()
    except OSError:
        return None
    m = re.search(r"FACTORY-REVIEW verdict=(\S+)", text)
    if m is None:
        return None
    verdict = m.group(1)
    if verdict == "approve":
        return "approved"
    if verdict in ("rework", "reject"):
        return "rejected"
    return None


def _median_field(values):
    """The rounded median, or '-' when nothing carries the field."""
    return str(round(statistics.median(values))) if values else "-"


def _read_job(jobs_dir, job_id):
    """`<jobs-dir>/<id>/job.json` as a dict, else None (unreadable, torn or a
    non-object reads None — never an error)."""
    p = pathlib.Path(jobs_dir) / job_id / "job.json"
    try:
        data = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _group_keys(text):
    """The task keys from a run.meta's `group:` lines (each `%q`-quoted, one
    double-quoted key list per wave group)."""
    keys = []
    for m in re.finditer(r"^group:\s*(.+)$", text, re.MULTILINE):
        keys.extend(re.findall(r"[A-Za-z][A-Za-z0-9-]*", m.group(1)))
    return keys


def ladder_report(repo, runs_dir, jobs_dir, min_n=5, plan=None):
    """The report's lines. Every `.result` under `<runs-dir>/*/` that carries a
    parseable `run:` and `key:` is a row, grouped by (route, role, kind, size,
    class, model, effort, rung) — route/role are fixed to openrouter/implement —
    and each group prints n, the first-gate approved fraction, landed commits
    per attempt, fix rounds per approved root, median wall and output tokens.
    A group under `min_n` prints only `insufficient`. Then the orchestrate
    section joins `run.meta driver:` ids to their drive `job.json`. Raises
    `ReportUnreadable` when the repo cannot be read; exit status is 0 otherwise.
    (SD9; the join moves onto `join_tasks_gates` when T10a lands — these output
    lines stay.)"""
    if not pathlib.Path(repo).is_dir():
        raise ReportUnreadable(f"cannot read repo {os.path.abspath(repo)}")

    rows = []
    for p in sorted(pathlib.Path(runs_dir).glob("*/*.result")):
        fields = tasks.read_result_fields(p)
        run = fields.get("run")
        key = fields.get("key")
        if not (run and key):
            continue
        if plan is not None:
            try:
                text = p.read_text()
            except OSError:
                continue
            plan_line = tasks._field(text, r"^plan:[ \t]*(.+)$")
            if plan_line is None or not fnmatch.fnmatch(
                os.path.basename(plan_line), plan
            ):
                continue
        kind, size = _route_kind_size(fields.get("route"))
        rows.append(
            {
                "run": run,
                "key": key,
                "model": fields.get("model", "unknown"),
                "effort": fields.get("effort", "unknown"),
                "kind": kind,
                "size": size,
                "class": fields.get("class", "any"),
                "rung": _rung(fields.get("rung")),
                "commits": fields.get("commits", 0),
                "wall_s": _as_int(fields.get("wall_s")),
                "output_tokens": fields.get("output_tokens"),
                "review": _row_review(repo, runs_dir, run, key),
            }
        )

    lines = [LADDER_HEADER.format(min_n=min_n)]

    groups = collections.defaultdict(list)
    for r in rows:
        groups[
            (r["kind"], r["size"], r["class"], r["model"], r["effort"], r["rung"])
        ].append(r)

    for gkey in sorted(groups):
        gr = groups[gkey]
        kind, size, klass, model, effort, rung = gkey
        tuple_disp = (
            f"openrouter/implement/{kind}/{size}/{klass} {model} {effort} rung {rung}"
        )
        n = len(gr)
        if n < min_n:
            lines.append(f"{tuple_disp}: insufficient (n={n})")
            continue
        g = sum(1 for r in gr if r["review"] is not None)
        a = sum(1 for r in gr if r["review"] == "approved")
        pct = round(a * 100 / g) if g else 0
        commits_mean = sum(r["commits"] for r in gr) / n
        approved_roots = {
            r["key"]
            for r in gr
            if tasks.chain_root(r["key"]) == r["key"] and r["review"] == "approved"
        }
        l = len(approved_roots)
        f = sum(
            1
            for r in rows
            if tasks.chain_root(r["key"]) != r["key"]
            and tasks.chain_root(r["key"]) in approved_roots
        )
        walls = [r["wall_s"] for r in gr if r["wall_s"] is not None]
        outs = [r["output_tokens"] for r in gr if r["output_tokens"] is not None]
        lines.append(
            f"{tuple_disp}: n={n} first-gate {a}/{g} ({pct}%) landed-commits "
            f"{commits_mean:.2f} fix-rounds {f}/{l} wall-median "
            f"{_median_field(walls)}s out-tokens-median {_median_field(outs)}"
        )

    lines.append(ORCHESTRATE_HEADER)
    # driver id -> (model, effort) for the drive jobs only; one run.meta per
    # run directory, so `runs` is the number of run directories driven.
    per_pair = collections.defaultdict(lambda: {"sessions": set(), "runs": []})
    for p in sorted(pathlib.Path(runs_dir).glob("*/run.meta")):
        try:
            text = p.read_text()
        except OSError:
            continue
        driver = tasks._field(text, r"^driver:[ \t]*(\S+)$")
        if driver is None:
            continue
        job = _read_job(jobs_dir, driver)
        if job is None or job.get("mode") != "drive":
            continue
        pair = (
            job.get("model") or "unknown",
            job.get("effort") or "unknown",
        )
        per_pair[pair]["sessions"].add(driver)
        per_pair[pair]["runs"].append(p.parent.name)

    if not per_pair:
        lines.append("orchestrate: no drive session recorded")
    else:
        for model, effort in sorted(per_pair):
            info = per_pair[(model, effort)]
            sessions = len(info["sessions"])
            runs = len(info["runs"])
            if sessions < min_n:
                lines.append(
                    f"orchestrate {model} {effort}: sessions={sessions} runs={runs} "
                    f"insufficient (n={sessions})"
                )
                continue
            tasks_seen = set()
            reported = approved = 0
            for run_name in info["runs"]:
                p = pathlib.Path(runs_dir) / run_name / "run.meta"
                try:
                    text = p.read_text()
                except OSError:
                    continue
                for key in _group_keys(text):
                    if key in tasks_seen:
                        continue
                    tasks_seen.add(key)
                    verdict = _row_review(repo, runs_dir, run_name, key)
                    if verdict is not None:
                        reported += 1
                        if verdict == "approved":
                            approved += 1
            lines.append(
                f"orchestrate {model} {effort}: sessions={sessions} runs={runs} "
                f"tasks={' '.join(sorted(tasks_seen))} first-gate "
                f"{approved}/{reported}"
            )
    return lines


def _positive_int(value):
    iv = int(value)
    if iv < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return iv


def main(argv=None):
    parser = argparse.ArgumentParser(prog="report")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plans", help="the planning-agent metrics (see report.py)")
    p.add_argument("--repo", required=True)
    p.add_argument("--today", default=None)
    p.add_argument("--min-n", type=int, default=5)
    p.add_argument("--plan", default=None)
    h = sub.add_parser("harness", help="the seat-harness metrics (see report.py)")
    h.add_argument("--before", default=None)
    h.add_argument("--since", default=None)
    h.add_argument("--split", default=None)
    h.add_argument("--min-n", type=_positive_int, default=5)
    l = sub.add_parser("ladder", help="the seat driver's ladder (see report.py)")
    l.add_argument("--repo", required=True)
    l.add_argument("--runs-dir", default=os.path.expanduser("~/factory/runs"))
    l.add_argument("--jobs-dir", default="/var/lib/seat/jobs")
    l.add_argument("--min-n", type=int, default=5)
    l.add_argument("--plan", default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "ladder":
            lines = ladder_report(
                args.repo,
                args.runs_dir,
                args.jobs_dir,
                min_n=args.min_n,
                plan=args.plan,
            )
        elif args.command == "harness":
            lines = harness_report(
                args.store,
                before=args.before,
                since=args.since,
                split=args.split,
                min_n=args.min_n,
            )
        else:
            lines = plans_report(
                args.store,
                args.repo,
                today=args.today,
                min_n=args.min_n,
                plan=args.plan,
            )
    except ReportUnreadable as exc:
        print(f"report: {exc}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
