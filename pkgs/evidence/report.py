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
import datetime
import fnmatch
import os
import pathlib
import sys

import evidence
import tasks

HEADER = (
    "# evidence report plans — proxies for "
    "docs/superpowers/specs/2026-09-05-planning-agent-design.md §7; "
    "n printed with every figure"
)


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


def main(argv=None):
    parser = argparse.ArgumentParser(prog="report")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE", "/var/lib/evidence")
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plans", help="the planning-agent metrics (see report.py)")
    p.add_argument("--repo", required=True)
    p.add_argument("--today", default=None)
    p.add_argument("--min-n", type=int, default=5)
    p.add_argument("--plan", default=None)
    args = parser.parse_args(argv)
    try:
        lines = plans_report(
            args.store, args.repo, today=args.today, min_n=args.min_n, plan=args.plan
        )
    except ReportUnreadable as exc:
        print(f"report: {exc}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
