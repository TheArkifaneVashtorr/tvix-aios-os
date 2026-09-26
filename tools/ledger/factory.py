"""Ledger extractor: factory workflow transcripts, dsh session usage, lane results.

Three readers, one append-only JSONL ledger per source:

* ``extract <transcript-dir>`` walks a Workflow-tool transcript dir
  (``journal.jsonl`` + ``agent-*.jsonl`` + ``agent-*.meta.json``) and writes
  ``factory-runs.jsonl``, ``factory-agents.jsonl`` and ``factory-findings.jsonl``.
* ``extract-dsh <sessions-dir>`` walks ``<dir>/<slug>/<uuid>/session.jsonl[.zstd]``
  and writes ``dsh-sessions.jsonl``, joining ``role``/``model`` from a
  ``manifest.json`` at the sessions-dir root.
* ``extract-lane <results-dir>`` walks one lane's ``<job-id>.json`` result files
  and writes ``lane-jobs.jsonl``, recording ``usage.cost`` as ``cost_usd``.

Token counts leave the extractors; OpenRouter-reported dollars leave the lane
extractor (``usage.cost`` -> ``cost_usd``). dsh's ``TokenUsage`` declares no
cost field, so the rollup prefers reported cost wherever it exists -- lane
results plus the OpenRouter activity export (``--activity``, keyed by
date+model) -- and treats ``rollup --costs <price-table.csv>`` as the fallback
estimate. A rate table goes stale and is wrong for any session on another
provider, so the rollup prints reported and estimated totals separately and
refuses to name a confident total when any unit is unpriced: it names the
unpriced count and the missing keys.

Schema: ``tools/ledger/schema.md``. Ledger files are data, not source (the
store's ``ledger/`` directory, ``evidence.DEFAULT_STORE``); this module is the
source of truth for their shape.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# The extractor runs from two layouts: the repo (`tools/ledger/factory.py`
# beside `pkgs/evidence`) and the `ledger-unit` sandbox (`ledger/factory.py`
# beside `pkgs/evidence`). Try the repo shape first, then the sandbox shape.
for _evidence_dir in (
    Path(__file__).resolve().parents[2] / "pkgs" / "evidence",
    Path(__file__).resolve().parents[1] / "pkgs" / "evidence",
):
    if str(_evidence_dir) not in sys.path:
        sys.path.insert(0, str(_evidence_dir))
try:
    import evidence
except ImportError as exc:
    raise ImportError(
        "tools/ledger/factory.py needs pkgs/evidence on sys.path"
    ) from exc

VERSION = 1
DEFAULT_LEDGER = os.path.join(
    os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE, "ledger"
)


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------


def _read_lines(path: Path) -> list[str]:
    with open(path) as fh:
        return [line for line in fh if line.strip()]


def _read_session_lines(path: Path) -> list[str]:
    """Read a dsh session transcript, decompressing zstd frames with `zstd -dc`."""
    if str(path).endswith(".zstd"):
        proc = subprocess.run(
            ["zstd", "-dc", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line for line in proc.stdout.splitlines() if line.strip()]
    return _read_lines(path)


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in _read_lines(path)]


def _stream_of(path: Path) -> tuple[str, str]:
    """The (store, stream) a ledger file writes to, derived from its path.

    ``path.parent`` must be named ``ledger`` (the ``ledger/*`` streams own the
    ``ledger/`` directory under the store); anything else exits 2 before any
    write, so a scribble outside the declared root never reaches the store.
    """
    if path.parent.name != "ledger":
        print(f"ledger dir must be named ledger: {path}", file=sys.stderr)
        raise SystemExit(2)
    store = path.parent.parent
    return str(store), f"ledger/{path.stem}"


def _merge_jsonl(path: Path, records: list[dict]) -> None:
    """Replace a keyed ledger stream by key, via the evidence fence."""
    store, stream = _stream_of(path)
    evidence.replace_stream(store, stream, records)


def _parse_ts(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# T1: factory workflow transcripts
# ---------------------------------------------------------------------------


def _read_agent(
    agent_file: Path, run_id: str
) -> tuple[dict, list[tuple[datetime, str]]]:
    agent_id = agent_file.name[len("agent-") : -len(".jsonl")]
    model = None
    tokens = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0, "thinking": 0}
    tool_uses = 0
    stamps: list[tuple[datetime, str]] = []
    for line in _read_lines(agent_file):
        event = json.loads(line)
        if event.get("type") != "assistant":
            continue
        message = event.get("message") or {}
        model = model or message.get("model")
        usage = message.get("usage") or {}
        tokens["in"] += usage.get("input_tokens", 0)
        tokens["out"] += usage.get("output_tokens", 0)
        tokens["cache_read"] += usage.get("cache_read_input_tokens", 0)
        tokens["cache_write"] += usage.get("cache_creation_input_tokens", 0)
        details = usage.get("output_tokens_details") or {}
        tokens["thinking"] += details.get("thinking_tokens", 0)
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_uses += 1
        stamp = event.get("timestamp")
        if stamp:
            stamps.append((_parse_ts(stamp), stamp))

    dts = [dt for dt, _ in stamps]
    wall_s = (max(dts) - min(dts)).total_seconds() if dts else 0.0
    agent = {
        "kind": "factory-agent",
        "v": VERSION,
        "src": "factory",
        "run_id": run_id,
        "agent_id": agent_id,
        "label": None,
        "role_model": model,
        "model_id": model,
        "tokens": tokens,
        "wall_s": wall_s,
        "tool_uses": tool_uses,
    }
    return agent, stamps


def _read_findings(journal_file: Path, run_id: str) -> list[dict]:
    findings: list[dict] = []
    for line in _read_lines(journal_file):
        event = json.loads(line)
        if event.get("type") != "result":
            continue
        result = event.get("result") or {}
        for finding in result.get("findings") or []:
            title = finding.get("issue") or finding.get("title")
            findings.append(
                {
                    "kind": "factory-finding",
                    "v": VERSION,
                    "src": "factory",
                    "run_id": run_id,
                    "task": result.get("task_key"),
                    "round": result.get("round"),
                    "label": result.get("label"),
                    "severity": finding.get("severity"),
                    "file": finding.get("file"),
                    "title_sha256": hashlib.sha256(title.encode()).hexdigest(),
                    "class": finding.get("class"),
                }
            )
    return findings


def extract_run(
    transcript_dir,
    run_id: str | None = None,
    plan: str | None = None,
    prefix: str | None = None,
    repo: str | None = None,
    tasks=None,
) -> tuple[dict, list[dict], list[dict]]:
    td = Path(transcript_dir)
    run_id = run_id or td.name
    agents: list[dict] = []
    all_stamps: list[tuple[datetime, str]] = []
    for agent_file in sorted(td.glob("agent-*.jsonl")):
        agent, stamps = _read_agent(agent_file, run_id)
        agents.append(agent)
        all_stamps.extend(stamps)
    agents.sort(key=lambda a: a["agent_id"])

    started = min(all_stamps)[1] if all_stamps else None
    ended = max(all_stamps)[1] if all_stamps else None
    wall_s = (
        (
            max(dt for dt, _ in all_stamps) - min(dt for dt, _ in all_stamps)
        ).total_seconds()
        if all_stamps
        else 0.0
    )

    run = {
        "kind": "factory-run-usage",
        "v": VERSION,
        "src": "factory",
        "run_id": run_id,
        "started": started,
        "ended": ended,
        "plan": plan,
        "prefix": prefix,
        "repo": repo,
        "tasks": tasks or [],
        "agents": len(agents),
        "output_tokens": sum(a["tokens"]["out"] for a in agents),
        "input_tokens": sum(a["tokens"]["in"] for a in agents),
        "cache_read": sum(a["tokens"]["cache_read"] for a in agents),
        "cache_write": sum(a["tokens"]["cache_write"] for a in agents),
        "thinking": sum(a["tokens"]["thinking"] for a in agents),
        "wall_s": wall_s,
    }
    findings = _read_findings(td / "journal.jsonl", run_id)
    return run, agents, findings


def extract(transcript_dir, ledger_dir, **meta) -> tuple[dict, list[dict], list[dict]]:
    run, agents, findings = extract_run(transcript_dir, **meta)
    out = Path(ledger_dir)
    _merge_jsonl(out / "factory-runs.jsonl", [run])
    _merge_jsonl(out / "factory-agents.jsonl", agents)
    _merge_jsonl(out / "factory-findings.jsonl", findings)
    return run, agents, findings


def backfill(projects_dir, ledger_dir) -> int:
    projects = Path(projects_dir)
    wf_dirs = sorted(
        p for p in projects.glob("**/subagents/workflows/wf_*") if p.is_dir()
    )
    for wf in wf_dirs:
        extract(wf, ledger_dir)
    return len(wf_dirs)


# ---------------------------------------------------------------------------
# N6: dsh session usage
# ---------------------------------------------------------------------------


def _load_manifest(manifest_file: Path) -> dict:
    if not manifest_file.exists():
        return {}
    return json.loads(manifest_file.read_text())


def _iter_dsh_sessions(sessions_dir: Path):
    for slug_dir in sorted(p for p in sessions_dir.iterdir() if p.is_dir()):
        for uuid_dir in sorted(p for p in slug_dir.iterdir() if p.is_dir()):
            zstd = uuid_dir / "session.jsonl.zstd"
            plain = uuid_dir / "session.jsonl"
            if zstd.exists():
                yield slug_dir.name, uuid_dir.name, zstd
            elif plain.exists():
                yield slug_dir.name, uuid_dir.name, plain


def _extract_dsh_session(path: Path, slug: str, uuid_dir: str, manifest: dict) -> dict:
    session_id = uuid_dir
    tokens = {"in": 0, "out": 0, "cache_read": 0, "reasoning": 0}
    turns = 0
    steps = 0
    tools = 0
    created_at: int | None = None
    times: list[int] = []
    for line in _read_session_lines(path):
        event = json.loads(line)
        kind = event.get("type")
        if kind == "session":
            session_id = event.get("id") or uuid_dir
            created_at = event.get("createdAt")
        elif kind == "turn/start":
            turns += 1
        elif kind == "step/start":
            steps += 1
        elif kind == "tool/call":
            tools += 1
        elif kind == "assistant/message":
            usage = (event.get("data") or {}).get("usage") or {}
            tokens["in"] += usage.get("inputTokens", 0)
            tokens["out"] += usage.get("outputTokens", 0)
            tokens["cache_read"] += usage.get("cacheReadTokens", 0)
            tokens["reasoning"] += usage.get("reasoningTokens", 0)
        time = event.get("time")
        if time is not None:
            times.append(time)

    # The leading `session` event carries `createdAt` but no `time`; every
    # later event carries `time`. Start the wall clock at whichever is earlier.
    first_time = min(times) if times else None
    last_time = max(times) if times else None
    if created_at is not None and (first_time is None or created_at < first_time):
        started = created_at
    else:
        started = first_time if first_time is not None else 0
    wall_s = (last_time - started) / 1000.0 if last_time is not None else 0.0
    meta = manifest.get(session_id) or {}
    return {
        "kind": "dsh-session",
        "v": VERSION,
        "src": "dsh",
        "session_id": session_id,
        "role": meta.get("role"),
        "model": meta.get("model"),
        "started": started,
        "turns": turns,
        "steps": steps,
        "tools": tools,
        "in": tokens["in"],
        "out": tokens["out"],
        "cache_read": tokens["cache_read"],
        "reasoning": tokens["reasoning"],
        "wall_s": wall_s,
    }


def extract_dsh(sessions_dir, ledger_dir) -> list[dict]:
    sessions = Path(sessions_dir)
    manifest = _load_manifest(sessions / "manifest.json")
    records = [
        _extract_dsh_session(path, slug, uuid_dir, manifest)
        for slug, uuid_dir, path in _iter_dsh_sessions(sessions)
    ]
    records.sort(key=lambda r: r["session_id"])
    _merge_jsonl(Path(ledger_dir) / "dsh-sessions.jsonl", records)
    return records


# ---------------------------------------------------------------------------
# N16: lane job results (the OpenRouter-reported cost that needs no price table)
# ---------------------------------------------------------------------------


def _lane_job_record(lane: str, result_file: Path) -> dict:
    """One lane result file -> one record; ``cost_usd`` from ``usage.cost`` only.

    A success result is ``{output, usage, model, provider, ts}``; a refusal or
    failure is ``{error, ts}`` with no ``usage``. ``cost_usd`` is ``usage.cost``
    when present and ``null`` otherwise -- never invented, never estimated.
    """
    data = json.loads(result_file.read_text())
    usage = data.get("usage") or {}
    return {
        "kind": "lane-job",
        "v": VERSION,
        "src": "lane",
        "lane": lane,
        "job_id": result_file.stem,
        "model": data.get("model"),
        "provider": data.get("provider"),
        "ts_epoch": data.get("ts"),
        "cost_usd": usage.get("cost"),
    }


def extract_lane(results_dir, ledger_dir, lane: str | None = None) -> list[dict]:
    results = Path(results_dir)
    lane = lane or results.parent.name
    records = [
        _lane_job_record(lane, result_file)
        for result_file in sorted(results.glob("*.json"))
    ]
    _merge_jsonl(Path(ledger_dir) / "lane-jobs.jsonl", records)
    return records


# ---------------------------------------------------------------------------
# Rollup (tokens always; reported dollars preferred, price table as fallback)
# ---------------------------------------------------------------------------


class PriceTableError(ValueError):
    """The --costs CSV is not a ``date,model`` rate table."""


class ActivityExportError(ValueError):
    """The --activity CSV is neither ``date,model,cost`` nor the real OpenRouter
    export (``created_at,model_permaslug,cost_total``)."""


REQUIRED_PRICE_COLUMNS = (
    "date",
    "model",
    "in_per_1m",
    "out_per_1m",
    "cache_read_per_1m",
)

REQUIRED_ACTIVITY_COLUMNS = ("date", "model", "cost")
REQUIRED_ACTIVITY_EXPORT_COLUMNS = ("created_at", "model_permaslug", "cost_total")


def _load_prices(costs_csv) -> dict:
    prices = {}
    with open(costs_csv) as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        if any(column not in fieldnames for column in REQUIRED_PRICE_COLUMNS):
            raise PriceTableError(
                "price table must have columns "
                f"{', '.join(REQUIRED_PRICE_COLUMNS)}; found: {', '.join(fieldnames)}"
            )
        for row in reader:
            prices[(row["date"], row["model"])] = {
                "in": float(row["in_per_1m"]),
                "out": float(row["out_per_1m"]),
                "cache_read": float(row["cache_read_per_1m"]),
            }
    return prices


def _session_price_key(session: dict) -> tuple[str | None, str | None]:
    """The ``(date, model)`` key a price-table row must match for this session."""
    started = session.get("started")
    if started is None:
        date = None
    else:
        date = datetime.fromtimestamp(started / 1000, timezone.utc).date().isoformat()
    return date, session.get("model")


def _lane_job_price_key(job: dict) -> tuple[str | None, str | None]:
    """The ``(date, model)`` bucket a lane job belongs to, from its ``ts_epoch`` and ``model``.

    This is the granularity at which the account-wide activity export is the
    single source of truth: a lane job's own ``cost_usd`` may only be added when
    its bucket has no export row, otherwise it would double count.
    """
    ts = job.get("ts_epoch")
    if ts is None:
        date = None
    else:
        date = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
    return date, job.get("model")


def _load_activity(activity_csv) -> dict:
    """Sum the OpenRouter activity export's cost column into ``(date, model)``.

    Two column sets are accepted:

    * the legacy ``date,model,cost`` shape, and
    * the real OpenRouter export ``created_at,model_permaslug,cost_total``,
      mapping ``created_at`` (ISO timestamp) to its ``YYYY-MM-DD`` date part,
      ``model_permaslug`` to model, and ``cost_total`` to cost. A cancelled
      row (``cancelled == "true"``) still counts its cost.

    The export is per request, but seat sessions can only be joined at the
    ``(date, model)`` granularity (dsh records no cost, only token counts), so
    every row's cost is summed into its date+model bucket. When several
    sessions share a bucket, the reported dollar is attributed to the bucket,
    not to any one session -- the residual the rollup documents.
    """
    by_key: dict[tuple[str, str], float] = {}
    with open(activity_csv) as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        has_legacy = all(c in fieldnames for c in REQUIRED_ACTIVITY_COLUMNS)
        has_export = all(c in fieldnames for c in REQUIRED_ACTIVITY_EXPORT_COLUMNS)
        if not has_legacy and not has_export:
            raise ActivityExportError(
                "activity export must have columns "
                f"{', '.join(REQUIRED_ACTIVITY_COLUMNS)} or "
                f"{', '.join(REQUIRED_ACTIVITY_EXPORT_COLUMNS)}; "
                f"found: {', '.join(fieldnames)}"
            )
        cost_field = "cost" if has_legacy else "cost_total"
        for row in reader:
            if has_legacy:
                date = row["date"]
                model = row["model"]
            else:
                date = row["created_at"][:10]
                model = row["model_permaslug"]
            try:
                cost = float(row[cost_field])
            except (TypeError, ValueError) as exc:
                raise ActivityExportError(
                    f"activity export row {reader.line_num} has a non-numeric "
                    f"cost: {row[cost_field]!r}"
                ) from exc
            by_key[(date, model)] = by_key.get((date, model), 0.0) + cost
    return by_key


def _cost_for(session: dict, prices: dict) -> float | None:
    date, model = _session_price_key(session)
    if date is None:
        return None
    rate = prices.get((date, model))
    if rate is None:
        return None
    return (
        session.get("in", 0) / 1e6 * rate["in"]
        + session.get("out", 0) / 1e6 * rate["out"]
        + session.get("cache_read", 0) / 1e6 * rate["cache_read"]
    )


def _rollup_dsh_roles(sessions: list[dict]) -> list[str]:
    """Per-role token totals for the dsh seat/lane sessions (the default view)."""
    by_role: dict[str, dict] = {}
    for session in sessions:
        role = session.get("role") or "unknown"
        bucket = by_role.setdefault(
            role,
            {
                "sessions": 0,
                "in": 0,
                "out": 0,
                "cache_read": 0,
                "reasoning": 0,
                "wall_s": 0.0,
            },
        )
        bucket["sessions"] += 1
        bucket["in"] += session.get("in", 0)
        bucket["out"] += session.get("out", 0)
        bucket["cache_read"] += session.get("cache_read", 0)
        bucket["reasoning"] += session.get("reasoning", 0)
        bucket["wall_s"] += session.get("wall_s", 0.0)

    if not sessions:
        return []
    lines = ["tokens per role:"]
    for role in sorted(by_role):
        b = by_role[role]
        lines.append(
            f"  {role}: {b['sessions']} session(s), in={b['in']}, out={b['out']}, "
            f"cache_read={b['cache_read']}, reasoning={b['reasoning']}, wall_s={b['wall_s']}"
        )
    return lines


def _as_utc(value: datetime) -> datetime:
    """Normalize a datetime to an aware UTC value (naive means UTC)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _resolve_window(since, until, now=None) -> tuple[datetime, datetime]:
    """Resolve --since/--until to an aware UTC half-open window ``[since, until)``.

    The default is the trailing 7 days: ``until`` is now (truncated to the
    second) and ``since`` is 7 days earlier. A missing bound derives from the
    other, so ``--since`` alone ends at now and ``--until`` alone starts 7 days
    back.
    """
    now = (now or datetime.now(timezone.utc)).replace(microsecond=0)
    until_dt = _as_utc(_parse_ts(until)).replace(microsecond=0) if until else now
    since_dt = (
        _as_utc(_parse_ts(since)).replace(microsecond=0)
        if since
        else until_dt - timedelta(days=7)
    )
    return since_dt, until_dt


def _session_in_window(session: dict, since: datetime, until: datetime) -> bool:
    """A dsh session is in-window iff its epoch-ms ``started`` falls inside."""
    started = session.get("started")
    if started is None:
        return False
    stamp = datetime.fromtimestamp(started / 1000, timezone.utc)
    return since <= stamp < until


def _run_in_window(run: dict, since: datetime, until: datetime) -> bool:
    """A factory run is in-window iff its ISO-8601 ``started`` falls inside."""
    started = run.get("started")
    if not started:
        return False
    return since <= _as_utc(_parse_ts(started)) < until


def _lane_job_in_window(job: dict, since: datetime, until: datetime) -> bool:
    """A lane job is in-window iff its epoch-seconds ``ts_epoch`` falls inside."""
    ts = job.get("ts_epoch")
    if ts is None:
        return False
    return since <= datetime.fromtimestamp(ts, timezone.utc) < until


def _activity_in_window(key: tuple, since: datetime, until: datetime) -> bool:
    """An activity-export ``(date, model)`` bucket is in-window iff its date's
    UTC midnight falls inside ``[since, until)``.

    The export carries only a date (no time of day), so the whole day is
    bucketed at midnight and compared like a session or lane-job timestamp:
    the day is atomic, the same residual as ``(date, model)`` attribution.
    """
    date = key[0]
    if date is None:
        return False
    try:
        start = _as_utc(datetime.fromisoformat(date))
    except ValueError:
        return False
    return since <= start < until


def _window_line(since: datetime, until: datetime) -> str:
    return (
        f"window: {since.strftime('%Y-%m-%dT%H:%M:%SZ')} .. "
        f"{until.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )


def _rollup_week(
    out: Path, sessions: list[dict], since: datetime, until: datetime
) -> list[str]:
    """The weekly rollup: tokens per lane and per role, fix rounds, wall clock."""
    sessions = [s for s in sessions if _session_in_window(s, since, until)]

    agents = _read_jsonl(out / "factory-agents.jsonl")
    runs = _read_jsonl(out / "factory-runs.jsonl")
    findings = _read_jsonl(out / "factory-findings.jsonl")

    # Factory agents and findings carry no timestamp; they join to their run by
    # run_id, and the run's ISO-8601 ``started`` decides the window. (dsh
    # sessions carry epoch-ms ``started`` directly.)
    runs = [run for run in runs if _run_in_window(run, since, until)]
    run_ids = {run["run_id"] for run in runs}
    agents = [a for a in agents if a.get("run_id") in run_ids]
    findings = [f for f in findings if f.get("run_id") in run_ids]

    factory = {
        "units": 0,
        "in": 0,
        "out": 0,
        "cache_read": 0,
        "cache_write": 0,
        "thinking": 0,
        "wall_s": 0.0,
    }
    for agent in agents:
        tokens = agent.get("tokens") or {}
        factory["units"] += 1
        factory["in"] += tokens.get("in", 0)
        factory["out"] += tokens.get("out", 0)
        factory["cache_read"] += tokens.get("cache_read", 0)
        factory["cache_write"] += tokens.get("cache_write", 0)
        factory["thinking"] += tokens.get("thinking", 0)
        factory["wall_s"] += agent.get("wall_s", 0.0)

    dsh = {
        "units": 0,
        "in": 0,
        "out": 0,
        "cache_read": 0,
        "reasoning": 0,
        "wall_s": 0.0,
    }
    for session in sessions:
        dsh["units"] += 1
        dsh["in"] += session.get("in", 0)
        dsh["out"] += session.get("out", 0)
        dsh["cache_read"] += session.get("cache_read", 0)
        dsh["reasoning"] += session.get("reasoning", 0)
        dsh["wall_s"] += session.get("wall_s", 0.0)

    lines = [
        _window_line(since, until),
        "tokens per lane:",
        (
            f"  factory: {factory['units']} agent(s), in={factory['in']}, "
            f"out={factory['out']}, cache_read={factory['cache_read']}, "
            f"cache_write={factory['cache_write']}, thinking={factory['thinking']}, "
            f"wall_s={factory['wall_s']}"
        ),
        (
            f"  dsh: {dsh['units']} session(s), in={dsh['in']}, out={dsh['out']}, "
            f"cache_read={dsh['cache_read']}, reasoning={dsh['reasoning']}, "
            f"wall_s={dsh['wall_s']}"
        ),
    ]

    by_role: dict[str, dict] = {}

    def add_role(
        role: str, in_t: int, out_t: int, cache_read_t: int, wall_s_t: float
    ) -> None:
        bucket = by_role.setdefault(
            role,
            {"units": 0, "in": 0, "out": 0, "cache_read": 0, "wall_s": 0.0},
        )
        bucket["units"] += 1
        bucket["in"] += in_t
        bucket["out"] += out_t
        bucket["cache_read"] += cache_read_t
        bucket["wall_s"] += wall_s_t

    for agent in agents:
        tokens = agent.get("tokens") or {}
        add_role(
            agent.get("role_model") or "unknown",
            tokens.get("in", 0),
            tokens.get("out", 0),
            tokens.get("cache_read", 0),
            agent.get("wall_s", 0.0),
        )
    for session in sessions:
        add_role(
            session.get("role") or "unknown",
            session.get("in", 0),
            session.get("out", 0),
            session.get("cache_read", 0),
            session.get("wall_s", 0.0),
        )

    lines.append("tokens per role:")
    for role in sorted(by_role):
        b = by_role[role]
        lines.append(
            f"  {role}: {b['units']} unit(s), in={b['in']}, out={b['out']}, "
            f"cache_read={b['cache_read']}, wall_s={b['wall_s']}"
        )

    fix_rounds: dict[str, int] = {}
    for run in runs:
        for task in run.get("tasks") or []:
            key = task.get("key") or "unknown"
            rounds = task.get("fix_rounds") or 0
            fix_rounds[key] = max(fix_rounds.get(key, 0), rounds)
    for finding in findings:
        task = finding.get("task")
        if task:
            rounds = finding.get("round") or 0
            fix_rounds[task] = max(fix_rounds.get(task, 0), rounds)

    lines.append("fix rounds per task:")
    if fix_rounds:
        for task in sorted(fix_rounds):
            lines.append(f"  {task}: {fix_rounds[task]} round(s)")
    else:
        lines.append("  none recorded")

    return lines


def _cost_block(
    sessions: list[dict],
    lane_jobs: list[dict],
    no_start: list[dict],
    prices: dict,
    activity: dict,
    price_table_given: bool,
) -> list[str]:
    """Reported vs estimated dollars, and the named unpriced count.

    Reported cost is the OpenRouter activity export summed once per
    ``(date, model)`` bucket. The export is account-wide, so a bucket already
    contains the lane's requests for that date+model; a lane job's own
    ``cost_usd`` is added only when its bucket has no export row (or no export
    was given), never double-counting. An export bucket covered by neither a
    session nor a lane job contributes as 'unattributed' and is named. The
    price table stays the fallback estimate for a session whose date+model
    bucket has no activity row. A session with no ``started`` and a lane job
    with no reported cost are both unpriced and named, never silently dropped.
    """
    lane_total = 0.0
    lane_unpriced = 0
    activity_keys = set(activity)
    for job in lane_jobs:
        cost = job.get("cost_usd")
        if cost is None:
            lane_unpriced += 1
        elif _lane_job_price_key(job) not in activity_keys:
            lane_total += float(cost)

    activity_total = 0.0
    unattributed: list[tuple[tuple, float]] = []
    session_keys = {_session_price_key(session) for session in sessions}
    lane_job_keys = {_lane_job_price_key(job) for job in lane_jobs}
    for key, cost in sorted(activity.items()):
        activity_total += float(cost)
        if key not in session_keys and key not in lane_job_keys:
            unattributed.append((key, float(cost)))

    estimated_total = 0.0
    estimated_count = 0
    sessions_unpriced = 0
    unpriced_keys_seen: set[tuple] = set()
    unpriced_keys: list[tuple] = []

    for session in sessions:
        key = _session_price_key(session)
        if key in activity_keys:
            continue
        if key in prices:
            estimated_total += _cost_for(session, prices)
            estimated_count += 1
        else:
            sessions_unpriced += 1
            if key not in unpriced_keys_seen:
                unpriced_keys_seen.add(key)
                unpriced_keys.append(key)

    unpriced_count = len(no_start) + sessions_unpriced + lane_unpriced
    lines = [
        (
            f"reported cost: {lane_total + activity_total:.6f} USD "
            f"(lane {lane_total:.6f} + activity {activity_total:.6f})"
        )
    ]
    for (date, model), cost in unattributed:
        lines.append(f"unattributed activity: ({date}, {model}) {cost:.6f} USD")
    if price_table_given:
        lines.append(
            f"estimated cost: {estimated_total:.6f} USD "
            f"(price table, {estimated_count} session(s))"
        )
    else:
        lines.append("estimated cost: 0.000000 USD (no price table)")

    if unpriced_count:
        detail = []
        if no_start:
            detail.append(f"no start time for {len(no_start)} session(s)")
        if unpriced_keys:
            keys = ", ".join(
                f"({date}, {model})"
                for date, model in sorted(
                    unpriced_keys, key=lambda key: (str(key[0]), str(key[1]))
                )
            )
            detail.append(f"no cost row for {keys}")
        if lane_unpriced:
            detail.append(f"no reported cost for {lane_unpriced} lane job(s)")
        total_units = len(sessions) + len(no_start) + len(lane_jobs)
        lines.append(
            f"unpriced: {unpriced_count} of {total_units} unit(s): " + "; ".join(detail)
        )
    return lines


def rollup(
    ledger_dir,
    week: bool = False,
    costs_csv=None,
    activity_csv=None,
    since=None,
    until=None,
    now=None,
) -> str:
    out = Path(ledger_dir)
    all_sessions = _read_jsonl(out / "dsh-sessions.jsonl")
    lane_jobs = _read_jsonl(out / "lane-jobs.jsonl")
    # A session with no ``started`` cannot be windowed or priced; it is carried
    # separately so the cost block names it as "no start time" even on the
    # --week path (N6 minor) instead of silently dropping it.
    priceable = [s for s in all_sessions if s.get("started") is not None]
    no_start = [s for s in all_sessions if s.get("started") is None]
    if week:
        since_dt, until_dt = _resolve_window(since, until, now=now)
        lines = _rollup_week(out, all_sessions, since_dt, until_dt)
        sessions = [s for s in priceable if _session_in_window(s, since_dt, until_dt)]
        lane_jobs = [j for j in lane_jobs if _lane_job_in_window(j, since_dt, until_dt)]
    else:
        lines = _rollup_dsh_roles(all_sessions)
        sessions = priceable
        since_dt = None
        until_dt = None

    prices = _load_prices(costs_csv) if costs_csv else {}
    activity = _load_activity(activity_csv) if activity_csv else {}
    if week:
        activity = {
            key: cost
            for key, cost in activity.items()
            if _activity_in_window(key, since_dt, until_dt)
        }
    reported_lane = any(j.get("cost_usd") is not None for j in lane_jobs)
    if costs_csv is None and activity_csv is None and not reported_lane:
        if lane_jobs:
            ids = ", ".join(sorted(str(j.get("job_id") or "?") for j in lane_jobs))
            lines.append(
                f"cost: unknown (no price table); {len(lane_jobs)} unpriced "
                f"lane job(s): {ids}"
            )
        else:
            lines.append("cost: unknown (no price table)")
    else:
        lines.extend(
            _cost_block(
                sessions,
                lane_jobs,
                no_start,
                prices,
                activity,
                price_table_given=costs_csv is not None,
            )
        )

    return "\n".join(lines)


def board_line(ledger_dir, run_id: str) -> str:
    runs = _read_jsonl(Path(ledger_dir) / "factory-runs.jsonl")
    for run in runs:
        if run.get("run_id") != run_id:
            continue
        tokens = (
            run.get("input_tokens", 0)
            + run.get("output_tokens", 0)
            + run.get("cache_read", 0)
            + run.get("cache_write", 0)
        )
        return f"{run.get('agents', 0)} agents, ~{tokens} tokens, {run.get('wall_s', 0.0)}s wall"
    return ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="factory.py")
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="extract one workflow transcript dir")
    p_extract.add_argument("transcript_dir")
    p_extract.add_argument("--ledger-dir", default=DEFAULT_LEDGER)
    p_extract.add_argument("--plan")
    p_extract.add_argument("--prefix")
    p_extract.add_argument("--repo")
    p_extract.add_argument("--tasks")

    p_dsh = sub.add_parser("extract-dsh", help="extract dsh session usage")
    p_dsh.add_argument("sessions_dir")
    p_dsh.add_argument("--ledger-dir", default=DEFAULT_LEDGER)

    p_lane = sub.add_parser(
        "extract-lane", help="extract one lane's result files (usage.cost -> cost_usd)"
    )
    p_lane.add_argument("results_dir")
    p_lane.add_argument("--ledger-dir", default=DEFAULT_LEDGER)
    p_lane.add_argument("--lane", help="lane name (defaults to the results dir parent)")

    p_backfill = sub.add_parser("backfill", help="backfill every past workflow dir")
    p_backfill.add_argument("projects_dir")
    p_backfill.add_argument("--ledger-dir", default=DEFAULT_LEDGER)

    p_rollup = sub.add_parser(
        "rollup", help="print token rollup and, with --costs/--activity, dollars"
    )
    p_rollup.add_argument("--ledger-dir", default=DEFAULT_LEDGER)
    p_rollup.add_argument("--week", action="store_true")
    p_rollup.add_argument("--since")
    p_rollup.add_argument("--until")
    p_rollup.add_argument("--costs", help="path to a date,model price-table CSV")
    p_rollup.add_argument(
        "--activity", help="path to an OpenRouter activity export CSV"
    )

    p_board = sub.add_parser("board-line", help="print a run's economics line")
    p_board.add_argument("run_id")
    p_board.add_argument("--ledger-dir", default=DEFAULT_LEDGER)

    args = parser.parse_args(argv)
    if args.command == "extract":
        meta = {}
        if args.plan is not None:
            meta["plan"] = args.plan
        if args.prefix is not None:
            meta["prefix"] = args.prefix
        if args.repo is not None:
            meta["repo"] = args.repo
        if args.tasks is not None:
            meta["tasks"] = json.loads(args.tasks)
        extract(args.transcript_dir, args.ledger_dir, **meta)
    elif args.command == "extract-dsh":
        extract_dsh(args.sessions_dir, args.ledger_dir)
    elif args.command == "extract-lane":
        extract_lane(args.results_dir, args.ledger_dir, lane=args.lane)
    elif args.command == "backfill":
        backfill(args.projects_dir, args.ledger_dir)
    elif args.command == "rollup":
        if (args.since or args.until) and not args.week:
            parser.error("--since/--until require --week")
        print(
            rollup(
                args.ledger_dir,
                week=args.week,
                costs_csv=args.costs,
                activity_csv=args.activity,
                since=args.since,
                until=args.until,
            )
        )
    elif args.command == "board-line":
        print(board_line(args.ledger_dir, args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
