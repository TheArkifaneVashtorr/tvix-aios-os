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
import csv
import datetime
import fnmatch
import json
import math
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
    """The judgement rows, one per plan: the row with the latest `judged_ts`
    wins, ordered by plan basename. `revision` does not decide this -- a plan
    re-drafted after a `revise` verdict and re-judged carries `revision: 0` on
    BOTH rounds (a full re-draft, not an in-place bump), so ranking by
    revision cannot tell the rounds apart at all; `judged_ts` (the judgement
    file's own first-commit time) can, EXCEPT when git's one-second commit
    resolution collapses two real rounds into the same instant: the corpus
    carries two such pairs (2026-09-11-factory.md, 2026-09-11-generation.md),
    each judged twice within one commit whose "revise (row 2) ... dispatch
    after a second revision" message (57a52bd) makes the true order explicit,
    but whose two `judgement_path`s alone sort the WRONG way (plain
    lexicographic order puts `...-factory.md` after `...-factory-r2.md`,
    since `-` < `.`). A same-`judged_ts` tie therefore breaks first toward
    `decision == "dispatch"` -- once a plan is dispatched no further round is
    judged in the same sitting, so a same-second dispatch is never the EARLIER
    of a same-second pair -- and only then toward the lexicographically
    greatest `judgement_path`, for full determinism when even the decision
    ties. A plan judged twice prints one line and counts once toward j and
    the ten-plan threshold."""
    latest = {}
    for r in rows:
        name = os.path.basename(r.get("plan", ""))
        rank = (
            r.get("judged_ts") or "",
            1 if r.get("decision") == "dispatch" else 0,
            r.get("judgement_path") or "",
        )
        if name not in latest or rank >= latest[name][1]:
            latest[name] = (r, rank)
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


def _seat_usage_rows(store):
    """The store's seat usage rows — `ledger/openrouter-usage` with
    `instance == "seat"` and `status == "ok"` — in file order; [] without a
    store. `cost_usd` null reads as 0.0 (the health-line convention: the
    null-cost count is part of the share line, never a refusal)."""
    if not store:
        return []
    return [
        row
        for row in evidence.read(store, "ledger/openrouter-usage")
        if row.get("instance") == "seat" and row.get("status") == "ok"
    ]


def _attributed_usage(store):
    """`{(run_id, key): cost_usd sum}` over the store's attributed seat usage
    rows — OC5's ingest sets `attribution` to `header` or `window` exactly
    when it could name the task the request served. {} without a store, so
    every join reads as unattributed."""
    out = {}
    for row in _seat_usage_rows(store):
        if row.get("attribution") in ("header", "window"):
            k = (row.get("run_id"), row.get("key"))
            out[k] = math.fsum([out.get(k, 0.0), row.get("cost_usd") or 0.0])
    return out


def _seat_usage_totals(store):
    """`(total_usd, attributed_usd, n_rows, n_attributed)` over the same rows
    the join reads — the whole model-level sum beside the attributed part, so
    the reader sees what the join excludes (spec §3.4)."""
    total = 0.0
    attributed = 0.0
    n = k = 0
    for row in _seat_usage_rows(store):
        cost = row.get("cost_usd") or 0.0
        total = math.fsum([total, cost])
        n += 1
        if row.get("attribution") in ("header", "window"):
            attributed = math.fsum([attributed, cost])
            k += 1
    return total, attributed, n, k


def ladder_report(repo, runs_dir, jobs_dir, min_n=5, plan=None, store=None):
    """The report's lines. Every `.result` under `<runs-dir>/*/` that carries a
    parseable `run:` and `key:` is a row, grouped by (route, role, kind, size,
    class, model, effort, rung) — route/role are fixed to openrouter/implement —
    and each group prints n, the first-gate approved fraction, landed commits
    per attempt, fix rounds per approved root, median wall and output tokens,
    and `usd/approved`: the attributed dollars (OC5) summed over the group's
    approved rows, divided by the approved count — `-` when no approved row
    carries attributed dollars. Line two carries the attribution share: seat
    rows, attributed rows and dollars (`no store` when `store` is None or the
    stream has no seat rows). A group under `min_n` prints only `insufficient`.
    Then the orchestrate section joins `run.meta driver:` ids to their drive
    `job.json`. Raises `ReportUnreadable` when the repo cannot be read; exit
    status is 0 otherwise. (SD9; the join moves onto `join_tasks_gates` when
    T10a lands — these output lines stay.)"""
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

    total_usd, attributed_usd, n_rows, n_attributed = _seat_usage_totals(store)
    if store and n_rows:
        lines.append(
            f"attribution: seat rows {n_rows}, attributed {n_attributed} "
            f"({round(n_attributed * 100 / n_rows)}%), ${attributed_usd:.2f} "
            f"of ${total_usd:.2f} attributed"
        )
    else:
        lines.append("attribution: no store")
    attributed = _attributed_usage(store)

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
        approved_rows = [r for r in gr if r["review"] == "approved"]
        a = len(approved_rows)
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
        approved_usd = math.fsum(
            attributed.get((r["run"], r["key"]), 0.0) for r in approved_rows
        )
        if a and any((r["run"], r["key"]) in attributed for r in approved_rows):
            usd_piece = f" usd/approved {approved_usd / a:.2f}"
        else:
            usd_piece = " usd/approved -"
        lines.append(
            f"{tuple_disp}: n={n} first-gate {a}/{g} ({pct}%) landed-commits "
            f"{commits_mean:.2f} fix-rounds {f}/{l} wall-median "
            f"{_median_field(walls)}s out-tokens-median {_median_field(outs)}"
            f"{usd_piece}"
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


SPEND_HEADER = (
    "# evidence report spend — dollars and tokens per UTC day, service, source "
    "and role (concept 2026-09-08e); claude appears twice (transcript rows "
    "priced at list, otel rows at Claude Code's own estimate) and the two are "
    "never added; n = rows in the window; refused under {min_n}"
)

_PRICED_UNITS = ("in", "out", "cache_read", "cache_write")

_ROLE_WORDS = {
    "review": "gate",
    "reviewer": "gate",
    "gate": "gate",
    "plan": "plan",
    "planner": "plan",
    "judge": "plan",
    "judges": "plan",
    "draft": "plan",
    "drafter": "plan",
    "implement": "implement",
    "implementer": "implement",
    "seat": "implement",
    "orchestrate": "orchestrate",
    "orchestrator": "orchestrate",
}

_PRICE_COLUMNS = {
    "in": "in_per_1m",
    "out": "out_per_1m",
    "cache_read": "cache_read_per_1m",
    "cache_write": "cache_write_per_1m",
}


def role_of_words(text):
    """The first word in `text` that a role knows, else `unknown`."""
    for token in re.split(r"[^a-z0-9]+", (text or "").lower()):
        if token in _ROLE_WORDS:
            return _ROLE_WORDS[token]
    return "unknown"


def _load_prices(path):
    """`{model: sorted [(date, {unit: float | None})]}` — an empty cell marks an
    unpriced unit (None)."""
    table = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            model = row["model"]
            rates = {
                unit: (float(row[col]) if row[col] != "" else None)
                for unit, col in _PRICE_COLUMNS.items()
            }
            table.setdefault(model, []).append((row["date"], rates))
    for entries in table.values():
        entries.sort(key=lambda entry: entry[0])
    return table


def _rate_for_day(rows, day):
    """The rates of the row with the greatest date <= day, else None."""
    best = None
    for date, rates in rows:
        if date <= day:
            best = rates
        else:
            break
    return best


def _price_row(table, model, day, tin, tout, tcr, tcw):
    """Price one claude row's token counts to `(usd, basis, unpriced)` where
    `unpriced` maps unit -> tokens for units carrying tokens but no rate."""
    unit_tokens = {"in": tin, "out": tout, "cache_read": tcr, "cache_write": tcw}
    if table is None:
        return (
            0.0,
            "unpriced",
            {u: t for u, t in unit_tokens.items() if t > 0},
        )
    rates = _rate_for_day(table.get(model, []), day)
    if rates is None:
        return (
            0.0,
            "unpriced",
            {u: t for u, t in unit_tokens.items() if t > 0},
        )
    terms = []
    unpriced = {}
    for unit in _PRICED_UNITS:
        rate = rates[unit]
        if rate is None:
            if unit_tokens[unit] > 0:
                unpriced[unit] = unit_tokens[unit]
        else:
            terms.append(unit_tokens[unit] * rate / 1e6)
    usd = math.fsum(terms)
    basis = "list" if not unpriced else "partial"
    return usd, basis, unpriced


def _utc_day_from_epoch(ts_epoch):
    return datetime.datetime.fromtimestamp(ts_epoch, datetime.timezone.utc).strftime(
        "%Y-%m-%d"
    )


def _utc_day_from_ts(ts):
    # every stream timestamp is an RFC3339 UTC "YYYY-MM-DDTHH:MM:SS…Z"
    return ts[:10]


def spend_report(store, since, until, prices, min_n=5):
    """The `evidence report spend` report; see the module docstring's spend
    concept and the byte-string tests for the exact shape."""
    orows = evidence.read(store, "ledger/openrouter-usage")
    fruns = {r.get("run_id"): r for r in evidence.read(store, "ledger/factory-runs")}
    fagents = evidence.read(store, "ledger/factory-agents")
    msessions = evidence.read(store, "ledger/main-sessions")
    otels = evidence.read(store, "ledger/otel-claude")
    levents = evidence.read(store, "ledger/limit-events")

    table = _load_prices(prices) if prices else None

    # (day, service, source, role) -> accumulator
    acc = {}

    def acc_get(key):
        if key not in acc:
            acc[key] = {
                "vendor": 0.0,  # source `vendor` (openrouter) and `otel` usd
                "transcript_usd": 0.0,  # priced claude-transcript usd
                "price_basis": None,
                "tokens": {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0},
                "reasoning": 0,
                "n": 0,
                "otel_max": {},
            }
        return acc[key]

    days = set()

    def is_day(d):
        return d != "undated"

    for r in orows:
        day = _utc_day_from_epoch(r["ts_epoch"])
        days.add(day)
        role = {"seat": "seat", "openrouter": "lane"}.get(r["instance"], "unknown")
        a = acc_get((day, "openrouter", "vendor", role))
        if r.get("status") == "ok" and r.get("cost_usd") is not None:
            a["vendor"] += r["cost_usd"]
        a["tokens"]["in"] += r.get("prompt_tokens") or 0
        a["tokens"]["out"] += r.get("completion_tokens") or 0
        a["tokens"]["cache_read"] += r.get("cached_tokens") or 0
        a["tokens"]["cache_write"] += r.get("cache_write_tokens") or 0
        a["reasoning"] += r.get("reasoning_tokens") or 0
        a["n"] += 1

    unpriced_total = {}

    def record_pricing(a, usd, basis, model, unpriced):
        if basis != "unpriced":
            a["transcript_usd"] = math.fsum([a["transcript_usd"], usd])
        order = {"list": 0, "partial": 1, "unpriced": 2}
        cur = a["price_basis"]
        if cur is None or order[basis] > order[cur]:
            a["price_basis"] = basis
        for unit, tokens in unpriced.items():
            key = (model, unit)
            unpriced_total[key] = unpriced_total.get(key, 0) + tokens

    for r in fagents:
        run = fruns.get(r.get("run_id"))
        started = run.get("started") if run else None
        day = _utc_day_from_ts(started) if started else "undated"
        if is_day(day):
            days.add(day)
        role = role_of_words(r.get("label")) if r.get("label") else "unknown"
        a = acc_get((day, "claude", "transcript", role))
        t = r.get("tokens") or {}
        tin = t.get("in") or 0
        tout = t.get("out") or 0
        tcr = t.get("cache_read") or 0
        tcw = t.get("cache_write") or 0
        a["tokens"]["in"] += tin
        a["tokens"]["out"] += tout
        a["tokens"]["cache_read"] += tcr
        a["tokens"]["cache_write"] += tcw
        a["reasoning"] += t.get("thinking") or 0
        a["n"] += 1
        usd, basis, unpriced = _price_row(
            table, r.get("model_id"), day, tin, tout, tcr, tcw
        )
        record_pricing(a, usd, basis, r.get("model_id"), unpriced)

    for r in msessions:
        started = r.get("started")
        day = _utc_day_from_ts(started) if started else "undated"
        if is_day(day):
            days.add(day)
        a = acc_get((day, "claude", "transcript", "orchestrate"))
        t = r.get("tokens") or {}
        a["tokens"]["in"] += t.get("in") or 0
        a["tokens"]["out"] += t.get("out") or 0
        a["tokens"]["cache_read"] += t.get("cache_read") or 0
        a["tokens"]["cache_write"] += t.get("cache_write") or 0
        a["reasoning"] += t.get("thinking") or 0
        a["n"] += 1
        for entry in r.get("by_model") or []:
            model = entry.get("model")
            usd, basis, unpriced = _price_row(
                table,
                model,
                day,
                entry.get("in") or 0,
                entry.get("out") or 0,
                entry.get("cache_read") or 0,
                entry.get("cache_write") or 0,
            )
            record_pricing(a, usd, basis, model, unpriced)

    for r in otels:
        day = _utc_day_from_ts(r.get("at"))
        days.add(day)
        role = (
            role_of_words(r.get("agent_name")) if r.get("agent_name") else "orchestrate"
        )
        a = acc_get((day, "claude", "otel", role))
        a["n"] += 1
        if r.get("sample") == "request":
            if r.get("cost_usd") is not None:
                a["vendor"] = math.fsum([a["vendor"], r["cost_usd"]])
        else:
            mkey = (
                r.get("session_id"),
                r.get("model"),
                r.get("model_suffix"),
                r.get("token_type"),
            )
            value = r.get("value")
            if value is not None:
                a["otel_max"][mkey] = max(a["otel_max"].get(mkey, value), value)

    if since is None:
        dated = sorted(d for d in days if d != "undated")
        since = (
            dated[0]
            if dated
            else datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        )
    if until is None:
        until = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    def in_window(day):
        return day != "undated" and since <= day <= until

    n = sum(a["n"] for (day, _s, _src, _r), a in acc.items() if in_window(day))

    header = SPEND_HEADER.format(min_n=min_n)
    if n < min_n:
        return [header, f"refused: n={n} < {min_n} (no conclusion under {min_n})"]

    lines = [header, f"window: {since}..{until}"]
    for (day, service, source, role), a in sorted(acc.items()):
        if not in_window(day):
            continue
        if source == "vendor":
            basis = "vendor"
            usd_s = f"{a['vendor']:.4f}"
            tk = a["tokens"]
            tk_r = a["reasoning"]
        elif source == "otel":
            basis = "estimate"
            usd_s = f"{a['vendor']:.4f}"
            tk = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}
            for (_sid, _m, _suffix, token_type), value in a["otel_max"].items():
                unit = {
                    "input": "in",
                    "output": "out",
                    "cacheRead": "cache_read",
                    "cacheCreation": "cache_write",
                }.get(token_type)
                if unit:
                    tk[unit] += value
            tk_r = 0
        else:  # claude transcript
            basis = a["price_basis"]
            usd_s = "-" if basis == "unpriced" else f"{a['transcript_usd']:.4f}"
            tk = a["tokens"]
            tk_r = a["reasoning"]
        fields = [
            day,
            service,
            source,
            role,
            basis,
            usd_s,
            str(tk["in"]),
            str(tk["out"]),
            str(tk["cache_read"]),
            str(tk["cache_write"]),
            str(tk_r),
            str(a["n"]),
        ]
        lines.append("  ".join(fields))

    total_openrouter = 0.0
    total_transcript = 0.0
    total_otel = 0.0
    for (day, _s, source, _r), a in acc.items():
        if not in_window(day):
            continue
        if source == "vendor":
            total_openrouter = math.fsum([total_openrouter, a["vendor"]])
        elif source == "otel":
            total_otel = math.fsum([total_otel, a["vendor"]])
        elif a["price_basis"] != "unpriced":
            total_transcript = math.fsum([total_transcript, a["transcript_usd"]])
    lines.append(
        f"total {since}..{until}: openrouter {total_openrouter:.4f} vendor · "
        f"claude transcripts {total_transcript:.4f} list · "
        f"claude otel {total_otel:.4f} estimate"
    )

    if unpriced_total:
        items = [
            f"{model} {unit} {tokens} tokens"
            for (model, unit), tokens in sorted(unpriced_total.items())
        ]
        lines.append("unpriced: " + "; ".join(items))
    else:
        lines.append("unpriced: none")

    counts = collections.Counter(
        r.get("rate_limit_type") for r in levents if r.get("rate_limit_type")
    )
    if counts:
        parts = ", ".join(f"{t}: {counts[t]}" for t in sorted(counts))
        lines.append(f"limits: {sum(counts.values())} rate-limit events ({parts})")
    else:
        lines.append("limits: 0 rate-limit events")
    return lines


# ---------------------------------------------------------------------------
# `evidence report operator` (OC3)
# ---------------------------------------------------------------------------

OPERATOR_HEADER = (
    "# evidence report operator — switch latency (helm-status change rows, "
    "the drift tile fail → ok), held keys (docs/ledger/task-status.toml), "
    "asks (ledger/operator, {days} d)"
)


def _parse_ts(ts):
    """One stream timestamp (RFC3339 UTC) as an aware datetime."""
    return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def _ledger_status(repo):
    """The graph's own task-status reader (D7) over `<repo>`'s ledger."""
    return tasks.load_task_status(
        os.path.join(repo, "docs", "ledger", "task-status.toml")
    ).items()


def _held_entry(key, p, end_date):
    """One ledger row as {"key", "since", "released", "days"}, or None when
    its `since` does not parse (the `check` arm refuses such rows; the report
    never crashes on the ledger). `days` runs to `end_date` while open."""
    try:
        since = datetime.date.fromisoformat(p["since"])
    except ValueError:
        return None
    released = p["released"] or None
    end = None
    if released is not None:
        try:
            end = datetime.date.fromisoformat(released)
        except ValueError:
            released = None
    return {
        "key": key,
        "since": p["since"],
        "released": released,
        "days": ((end or end_date) - since).days,
    }


def switch_pairs(rows):
    """D8: the drift tile's fail → ok pairs among helm-status rows.

    `rows` arrive in file order (the reader already sorts by ts within a
    file and reads monthly siblings in order); only `reason == "change"`
    rows are read — a heartbeat repeats the last tiles, so it never carries
    a transition. A `fail` opens a pair when nothing is open, an `ok` closes
    the open pair; `warn`, `unknown` and a missing drift tile do nothing. A
    pair still open at the end is `(fail_ts, None)`.
    """
    pairs: list[tuple[str, str | None]] = []
    open_fail = None
    for row in rows:
        if row.get("reason") != "change":
            continue
        drift = row.get("tiles", {}).get("drift")
        if drift == "fail" and open_fail is None:
            open_fail = row.get("ts")
        elif drift == "ok" and open_fail is not None:
            pairs.append((open_fail, row.get("ts")))
            open_fail = None
    if open_fail is not None:
        pairs.append((open_fail, None))
    return pairs


def held_rows(repo, today):
    """The ledger's `held` and `released` rows, sorted by key: one
    {"key", "since", "released", "days"} each, `days` = released − since or
    today − while open. `today` is a `datetime.date`."""
    rows = []
    for (_repo, _plan, key), p in _ledger_status(repo):
        if p["status"] not in ("held", "released"):
            continue
        entry = _held_entry(key, p, today)
        if entry is not None:
            rows.append(entry)
    rows.sort(key=lambda r: r["key"])
    return rows


def asks_summary(store, now, days):
    """The operator-ask window over `ledger/operator`, or None when the
    stream carries no such row at all. `median_min` is None when no answer
    row in the window carries a latency."""
    rows = [
        r
        for r in evidence.read(store, "ledger/operator")
        if r.get("kind") == "operator-ask"
    ]
    if not rows:
        return None
    cutoff = now - datetime.timedelta(days=days)
    window = []
    for r in rows:
        try:
            ts = _parse_ts(r["ts"])
        except ValueError:
            continue
        if cutoff < ts <= now:
            window.append(r)
    lats = [
        r["latency_s"]
        for r in window
        if r.get("phase") == "answer" and r.get("latency_s") is not None
    ]
    return {
        "asks": sum(1 for r in window if r.get("phase") == "ask"),
        "answered": sum(1 for r in window if r.get("phase") == "answer"),
        "median_min": round(statistics.median(lats) / 60) if lats else None,
    }


def operator_summary(store, repo, now, days=7):
    """The bundle's Operator facts: the newest closed switch's seconds, the
    open switch, the held keys, and the asks window."""
    rows = [
        r for r in evidence.read(store, "helm-status") if r.get("kind") == "helm-status"
    ]
    pairs = switch_pairs(rows)
    closed = [p for p in pairs if p[1] is not None]
    last_switch_s = None
    if closed:
        fail_ts, ok_ts = closed[-1]
        last_switch_s = int((_parse_ts(ok_ts) - _parse_ts(fail_ts)).total_seconds())
    open_since = next((f for f, o in pairs if o is None), None)
    held = []
    for (_repo, _plan, key), p in _ledger_status(repo):
        if p["status"] != "held":
            continue
        entry = _held_entry(key, p, now.date())
        if entry is not None:
            held.append(
                {"key": entry["key"], "since": entry["since"], "days": entry["days"]}
            )
    held.sort(key=lambda r: r["key"])
    return {
        "last_switch_s": last_switch_s,
        "open_switch": open_since is not None,
        "open_since": open_since,
        "held": held,
        "asks": asks_summary(store, now, days),
        "days": days,
    }


def operator_report(store, repo, today=None, days=7):
    """The `evidence report operator` report's lines. Raises
    `ReportUnreadable` when the repo cannot be read or `--today` is not
    YYYY-MM-DD; exit status is 0 otherwise."""
    if not pathlib.Path(repo).is_dir():
        raise ReportUnreadable(f"cannot read repo {os.path.abspath(repo)}")
    if today is None:
        now = datetime.datetime.now(datetime.timezone.utc)
        today_d = now.date()
    else:
        try:
            today_d = datetime.date.fromisoformat(today)
        except ValueError:
            raise ReportUnreadable("--today must be YYYY-MM-DD")
        now = datetime.datetime.combine(
            today_d, datetime.time.max, tzinfo=datetime.timezone.utc
        )
    lines = [OPERATOR_HEADER.format(days=days)]
    rows = [
        r for r in evidence.read(store, "helm-status") if r.get("kind") == "helm-status"
    ]
    pairs = switch_pairs(rows)
    if not pairs:
        lines.append("switch none")
    for fail_ts, ok_ts in pairs:
        if ok_ts is None:
            lines.append(f"switch {fail_ts} open -")
        else:
            hours = (_parse_ts(ok_ts) - _parse_ts(fail_ts)).total_seconds() / 3600
            lines.append(f"switch {fail_ts} {ok_ts} {hours:.2f}")
    held = held_rows(repo, today_d)
    if not held:
        lines.append("held none")
    for h in held:
        lines.append(
            f"held {h['key']} {h['since']} {h['released'] or 'open'} {h['days']}"
        )
    summary = asks_summary(store, now, days)
    if summary is None:
        lines.append(f"asks {days} d: n/a (ledger/operator absent)")
    else:
        median = "-" if summary["median_min"] is None else str(summary["median_min"])
        lines.append(
            f"asks {days} d: {summary['asks']}, answered {summary['answered']}, "
            f"median {median} min"
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
    s = sub.add_parser("spend", help="spend per UTC day (see report.py)")
    s.add_argument("--since", default=None)
    s.add_argument("--until", default=None)
    s.add_argument("--prices", default=None)
    s.add_argument("--min-n", type=int, default=5)
    o = sub.add_parser("operator", help="the operator's latency (see report.py)")
    o.add_argument("--repo", required=True)
    o.add_argument("--today", default=None)
    o.add_argument("--days", type=_positive_int, default=7)
    args = parser.parse_args(argv)
    try:
        if args.command == "spend":
            lines = spend_report(
                args.store,
                args.since,
                args.until,
                args.prices,
                min_n=args.min_n,
            )
        elif args.command == "ladder":
            lines = ladder_report(
                args.repo,
                args.runs_dir,
                args.jobs_dir,
                min_n=args.min_n,
                plan=args.plan,
                store=args.store,
            )
        elif args.command == "harness":
            lines = harness_report(
                args.store,
                before=args.before,
                since=args.since,
                split=args.split,
                min_n=args.min_n,
            )
        elif args.command == "operator":
            lines = operator_report(
                args.store, args.repo, today=args.today, days=args.days
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
