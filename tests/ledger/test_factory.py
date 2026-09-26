"""Ledger extractor unit tests.

Three surfaces in one check, per the N6 spec (which extends T1 of the lane-L
round-1 plan) and N16 (OpenRouter-reported cost first, price table as the
fallback):

1. T1 -- the factory workflow-transcript extractor (``extract``), keyed by
   ``run_id``/``agent_id``, with exact token totals from a two-agent fixture.
2. N6 -- the dsh session extractor (``extract-dsh``), keyed by ``session_id``,
   with exact input/output/cache-read/reasoning totals, role+model joined from
   ``manifest.json``, wall clock from first/last event, and tool-call count.
3. N16 -- the lane-result extractor (``extract-lane``) recording
   ``cost_usd`` from ``usage.cost``, and ``rollup --costs``/``--activity``
   printing OpenRouter-reported cost (lane results + activity export) and the
   price-table estimate separately, preferring the reported dollar and naming
   every unpriced unit. No dollar is invented anywhere in the extractors.

The extractor lives at ``tools/ledger/factory.py``. These tests load it the
same way ``tests/broker`` loads ``pkgs/broker/policy.py`` -- by module path
from the source tree, falling back to the flat copy the flake check builds.
"""

import builtins
import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import sys

import pytest

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
DSH_FIXTURES = FIXTURES / "dsh-sessions"
WORKFLOW_FIXTURE = FIXTURES / "workflow"
LANE_FIXTURE = FIXTURES / "lane" / "openrouter" / "results"
ACTIVITY_FIXTURE = FIXTURES / "activity.csv"
ACTIVITY_EXPORT_FIXTURE = FIXTURES / "activity-export.csv"


def load_factory():
    root = pathlib.Path(__file__).resolve().parents[2]
    candidates = [
        root / "tools" / "ledger" / "factory.py",
        pathlib.Path("ledger/factory.py"),
    ]
    src = next(p for p in candidates if p.exists())
    spec = importlib.util.spec_from_file_location("factory", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["factory"] = mod
    spec.loader.exec_module(mod)
    return mod


factory = load_factory()


def read_jsonl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _record_openers(monkeypatch, store):
    """Wrap os.open and builtins.open so any write-mode open of a path under
    `store` records the (module, name) of the function that performed it.
    Returns the set of recorded (module, name) tuples."""
    openers = set()

    def _opener():
        # frame 0 = this helper, frame 1 = the wrapper, frame 2 = the opener.
        frame = sys._getframe(2)
        return (frame.f_globals.get("__name__"), frame.f_code.co_name)

    def _wrap_os_open(orig):
        def wrapper(file, flags, *args, **kwargs):
            if str(file).startswith(str(store)) and flags & (
                os.O_WRONLY | os.O_RDWR | os.O_APPEND
            ):
                openers.add(_opener())
            return orig(file, flags, *args, **kwargs)

        return wrapper

    def _wrap_open(orig):
        def wrapper(file, mode="r", *args, **kwargs):
            if str(file).startswith(str(store)) and any(c in mode for c in "wax+"):
                openers.add(_opener())
            return orig(file, mode, *args, **kwargs)

        return wrapper

    monkeypatch.setattr(os, "open", _wrap_os_open(os.open))
    monkeypatch.setattr(builtins, "open", _wrap_open(builtins.open))
    return openers


# ---------------------------------------------------------------------------
# N6: dsh session usage rollup
# ---------------------------------------------------------------------------


def test_dsh_session_usage_rollup(tmp_path):
    out = tmp_path / "ledger"
    out.mkdir()
    records = factory.extract_dsh(DSH_FIXTURES, out)
    assert len(records) == 2

    written = read_jsonl(out / "dsh-sessions.jsonl")
    assert len(written) == 2

    by_id = {r["session_id"]: r for r in written}

    session_a = by_id["session-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]
    session_a.pop("ts")  # replace_stream stamps the envelope ts (now-dependent)
    assert session_a == {
        "v": 1,
        "kind": "dsh-session",
        "src": "dsh",
        "session_id": "session-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "role": "deepseekPro",
        "model": "deepseek/deepseek-v4-pro-0813",
        "started": 1788546865000,
        "turns": 1,
        "steps": 3,
        "tools": 3,
        "in": 600,
        "out": 90,
        "cache_read": 180,
        "reasoning": 60,
        "wall_s": 14.0,
    }

    session_b = by_id["session-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"]
    session_b.pop("ts")
    assert session_b == {
        "v": 1,
        "kind": "dsh-session",
        "src": "dsh",
        "session_id": "session-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "role": "deepseekFlash",
        "model": "deepseek/deepseek-v4-flash",
        "started": 1788546900000,
        "turns": 1,
        "steps": 3,
        "tools": 4,
        "in": 6000,
        "out": 900,
        "cache_read": 1800,
        "reasoning": 600,
        "wall_s": 15.0,
    }


def test_extract_is_idempotent(tmp_path):
    """Re-running extract-dsh must not duplicate lines -- keyed by session id."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)
    factory.extract_dsh(DSH_FIXTURES, out)

    written = read_jsonl(out / "dsh-sessions.jsonl")
    assert len(written) == 2
    assert sorted(r["session_id"] for r in written) == [
        "session-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "session-bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    ]


def test_no_cost_field_is_invented(tmp_path):
    """dsh's TokenUsage carries token counts only; no cost field may appear."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)
    for record in read_jsonl(out / "dsh-sessions.jsonl"):
        assert "cost" not in record
        for value in record.values():
            if isinstance(value, dict):
                assert "cost" not in value


def test_rollup_without_costs_prints_unknown(tmp_path):
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)
    text = factory.rollup(out)
    assert "cost: unknown (no price table)" in text


def test_rollup_with_costs_joins_by_date_and_model(tmp_path):
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    # Both sessions fall on 2026-09-04 (see fixture timestamps). Rates are
    # USD per 1M tokens, keyed by date+model -- the price table shape.
    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,model,in_per_1m,out_per_1m,cache_read_per_1m\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1\n"
        "2026-09-04,deepseek/deepseek-v4-flash,0.5,1.0,0.05\n"
    )

    text = factory.rollup(out, costs_csv=prices)

    # pro: 600/1e6*1.0 + 90/1e6*2.0 + 180/1e6*0.1 = 0.000798
    # flash: 6000/1e6*0.5 + 900/1e6*1.0 + 1800/1e6*0.05 = 0.00399
    # estimated = 0.004788; every session is priced, so no unpriced line.
    lines = text.splitlines()
    assert ("reported cost: 0.000000 USD (lane 0.000000 + activity 0.000000)") in lines
    assert "estimated cost: 0.004788 USD (price table, 2 session(s))" in lines


def test_rollup_costs_partial_price_table_names_unpriced(tmp_path):
    """A price table covering one of two sessions must name the gap, not a bare total."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    # Only the pro session has a rate row; the flash session is unpriced.
    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,model,in_per_1m,out_per_1m,cache_read_per_1m\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1\n"
    )

    text = factory.rollup(out, costs_csv=prices)
    lines = text.splitlines()

    assert ("reported cost: 0.000000 USD (lane 0.000000 + activity 0.000000)") in lines
    assert "estimated cost: 0.000798 USD (price table, 1 session(s))" in lines
    assert (
        "unpriced: 1 of 2 unit(s): no cost row for "
        "(2026-09-04, deepseek/deepseek-v4-flash)"
    ) in lines
    assert "estimated cost: 0.004788 USD" not in lines


def test_rollup_costs_rejects_activity_export_shape(tmp_path):
    """An activity-export-shaped CSV (date,model,tokens,cost) is not a price
    table and must raise a named error listing the columns found."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    activity = tmp_path / "activity.csv"
    activity.write_text(
        "date,model,tokens,cost\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,10000,0.0123\n"
    )

    with pytest.raises(factory.PriceTableError) as excinfo:
        factory.rollup(out, costs_csv=activity)

    message = str(excinfo.value)
    assert "in_per_1m" in message
    assert "date, model, tokens, cost" in message


def test_openrouter_prices_csv_loads_through_price_reader():
    """The committed price table's header is the one `rollup --costs` parses."""
    root = pathlib.Path(__file__).resolve().parents[2]
    candidates = [
        root / "docs" / "ledger" / "openrouter-prices.csv",
        pathlib.Path("docs-ledger") / "openrouter-prices.csv",
    ]
    prices = factory._load_prices(next(p for p in candidates if p.exists()))
    assert prices[("2026-09-04", "deepseek/deepseek-v4-pro-0813")] == {
        "in": 0.55,
        "out": 2.19,
        "cache_read": 0.0,
    }
    assert prices[("2026-09-03", "deepseek/deepseek-v4-pro-0813")] == {
        "in": 1.02,
        "out": 2.05,
        "cache_read": 0.0,
    }
    assert prices[("2026-09-03", "deepseek/deepseek-v4-flash")] == {
        "in": 0.08,
        "out": 0.16,
        "cache_read": 0.0,
    }


# ---------------------------------------------------------------------------
# T1: factory workflow-transcript extractor
# ---------------------------------------------------------------------------


def test_factory_extract_rollup(tmp_path):
    out = tmp_path / "ledger"
    out.mkdir()
    run, agents, findings = factory.extract(
        WORKFLOW_FIXTURE,
        out,
        plan="docs/superpowers/plans/example.md",
        prefix="example",
        repo="example",
    )

    assert run["run_id"] == "workflow"
    assert run["plan"] == "docs/superpowers/plans/example.md"
    assert run["prefix"] == "example"
    assert run["repo"] == "example"
    assert run["agents"] == 2
    assert run["input_tokens"] == 2800
    assert run["output_tokens"] == 330
    assert run["cache_read"] == 14000
    assert run["cache_write"] == 3000
    assert run["thinking"] == 165
    assert run["wall_s"] == 105.0
    assert run["started"] == "2026-09-03T10:00:00.000Z"
    assert run["ended"] == "2026-09-03T10:01:45.000Z"

    by_agent = {a["agent_id"]: a for a in agents}
    assert len(agents) == 2
    assert by_agent["a1111111111111111"]["role_model"] == "claude-fable-5"
    assert by_agent["a1111111111111111"]["model_id"] == "claude-fable-5"
    assert by_agent["a1111111111111111"]["tokens"] == {
        "in": 1100,
        "out": 120,
        "cache_read": 5000,
        "cache_write": 1000,
        "thinking": 60,
    }
    assert by_agent["a1111111111111111"]["wall_s"] == 30.0
    assert by_agent["a1111111111111111"]["tool_uses"] == 2

    assert by_agent["a2222222222222222"]["role_model"] == "claude-opus-4-1"
    assert by_agent["a2222222222222222"]["tokens"]["in"] == 1700
    assert by_agent["a2222222222222222"]["tokens"]["thinking"] == 105
    assert by_agent["a2222222222222222"]["tool_uses"] == 1
    assert by_agent["a2222222222222222"]["wall_s"] == 45.0

    assert len(findings) == 3
    by_file_title = {(f["file"], f["title_sha256"]): f for f in findings}
    assert (
        by_file_title[("pkgs/x.py", hashlib.sha256(b"X does Y").hexdigest())][
            "severity"
        ]
        == "major"
    )
    assert (
        by_file_title[("pkgs/y.py", hashlib.sha256(b"X does Y").hexdigest())][
            "severity"
        ]
        == "minor"
    )
    assert (
        by_file_title[("pkgs/z.py", hashlib.sha256(b"Z is W").hexdigest())]["severity"]
        == "minor"
    )

    # Persisted files match the in-memory records.
    runs_written = read_jsonl(out / "factory-runs.jsonl")
    assert len(runs_written) == 1
    assert runs_written[0]["run_id"] == "workflow"


def test_factory_extract_is_idempotent(tmp_path):
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract(WORKFLOW_FIXTURE, out)
    factory.extract(WORKFLOW_FIXTURE, out)

    assert len(read_jsonl(out / "factory-runs.jsonl")) == 1
    assert len(read_jsonl(out / "factory-agents.jsonl")) == 2
    assert len(read_jsonl(out / "factory-findings.jsonl")) == 3


def test_findings_idempotency_key_includes_file(tmp_path):
    """Two findings with one title on different files must not collide."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract(WORKFLOW_FIXTURE, out)
    factory.extract(WORKFLOW_FIXTURE, out)

    written = read_jsonl(out / "factory-findings.jsonl")
    x = hashlib.sha256(b"X does Y").hexdigest()
    z = hashlib.sha256(b"Z is W").hexdigest()
    keys = {(f["file"], f["title_sha256"]) for f in written}
    assert ("pkgs/x.py", x) in keys
    assert ("pkgs/y.py", x) in keys
    assert ("pkgs/z.py", z) in keys
    assert len(written) == 3


def test_extract_writes_only_through_replace_stream(monkeypatch, tmp_path):
    # The ledger files must be opened only by evidence.replace_stream (the
    # evidence module's keyed-stream writer), never by tools/ledger/factory.py
    # itself: a direct `os.open`/`open` in _write_jsonl would record a factory
    # frame here and fail.
    out = tmp_path / "ledger"
    out.mkdir()
    openers = _record_openers(monkeypatch, tmp_path)
    factory.extract(WORKFLOW_FIXTURE, out)
    names = {name for _, name in openers}
    modules = {module for module, _ in openers}
    assert names == {"replace_stream"}
    assert names <= {"append", "replace_stream", "_write_atomic"}
    assert not ({"collect", "factory"} & modules)


def test_records_carry_kind_and_title_sha256(tmp_path):
    """Every ledger row gains `kind`; findings carry `title_sha256` (not
    `title`); dsh sessions lose `slug`."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract(WORKFLOW_FIXTURE, out)
    factory.extract_dsh(DSH_FIXTURES, out)
    factory.extract_lane(LANE_FIXTURE, out)

    for name in (
        "factory-runs.jsonl",
        "factory-agents.jsonl",
        "factory-findings.jsonl",
        "dsh-sessions.jsonl",
        "lane-jobs.jsonl",
    ):
        for row in read_jsonl(out / name):
            assert "kind" in row, (name, row)

    for finding in read_jsonl(out / "factory-findings.jsonl"):
        assert "title_sha256" in finding and "title" not in finding

    for session in read_jsonl(out / "dsh-sessions.jsonl"):
        assert "slug" not in session


def test_ledger_dir_must_be_named_ledger(tmp_path):
    out = tmp_path / "x"
    with pytest.raises(SystemExit) as excinfo:
        factory.extract(WORKFLOW_FIXTURE, out)
    assert excinfo.value.code == 2


def test_dsh_session_fixture_dates(tmp_path):
    """The price-join test's hard-coded 2026-09-04 stays honest."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)
    for record in read_jsonl(out / "dsh-sessions.jsonl"):
        day = dt.datetime.fromtimestamp(record["started"] / 1000, dt.timezone.utc)
        assert day.date().isoformat() == "2026-09-04"


# ---------------------------------------------------------------------------
# E4: findings carry task/round/label; the ledger lives under the evidence store
# ---------------------------------------------------------------------------


def test_findings_carry_task_round_and_label_when_the_result_has_them(tmp_path):
    journal = tmp_path / "journal.jsonl"
    journal.write_text(
        json.dumps(
            {
                "type": "result",
                "key": "k1",
                "agentId": "a1",
                "result": {
                    "task_key": "N9",
                    "round": 1,
                    "label": "review:N9:r2",
                    "approved": False,
                    "findings": [
                        {
                            "severity": "major",
                            "file": "x.py",
                            "issue": "bad",
                            "fix": "fix",
                        }
                    ],
                    "summary": "",
                },
            }
        )
        + "\n"
        + json.dumps(
            {
                "type": "result",
                "key": "k2",
                "agentId": "a2",
                "result": {
                    "approved": True,
                    "findings": [
                        {
                            "severity": "minor",
                            "file": "y.py",
                            "issue": "meh",
                            "fix": "fix",
                        }
                    ],
                    "summary": "",
                },
            }
        )
        + "\n"
    )
    rows = factory._read_findings(journal, "run")
    assert (rows[0]["task"], rows[0]["round"], rows[0]["label"]) == (
        "N9",
        1,
        "review:N9:r2",
    )
    assert (rows[1]["task"], rows[1]["round"], rows[1]["label"]) == (None, None, None)


def test_default_ledger_is_under_the_evidence_store(monkeypatch):
    monkeypatch.setenv("EVIDENCE_STORE", "/tmp/ev")
    assert load_factory().DEFAULT_LEDGER == "/tmp/ev/ledger"
    monkeypatch.delenv("EVIDENCE_STORE")
    assert load_factory().DEFAULT_LEDGER == "/var/lib/evidence/ledger"


# ---------------------------------------------------------------------------
# rollup --week: both sources, per role and lane, fix rounds, wall clock
# ---------------------------------------------------------------------------


def test_rollup_week_covers_factory_and_dsh(tmp_path):
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract(
        WORKFLOW_FIXTURE,
        out,
        tasks=[
            {
                "key": "T1",
                "status": "done",
                "commit": "a" * 40,
                "fix_rounds": 2,
            },
            {
                "key": "T2",
                "status": "done",
                "commit": "b" * 40,
                "fix_rounds": 1,
            },
        ],
    )
    factory.extract_dsh(DSH_FIXTURES, out)

    text = factory.rollup(out, week=True, since="2026-08-28", until="2026-09-05")

    # Per lane: the Claude factory transcripts vs the dsh seat sessions.
    assert "tokens per lane:" in text
    assert (
        "factory: 2 agent(s), in=2800, out=330, cache_read=14000, "
        "cache_write=3000, thinking=165, wall_s=75.0"
    ) in text
    assert (
        "dsh: 2 session(s), in=6600, out=990, cache_read=1980, "
        "reasoning=660, wall_s=29.0"
    ) in text

    # Per role, across both lanes (factory roles are model names; dsh roles
    # are the manifest's role key).
    assert "tokens per role:" in text
    assert (
        "claude-fable-5: 1 unit(s), in=1100, out=120, cache_read=5000, wall_s=30.0"
        in text
    )
    assert (
        "claude-opus-4-1: 1 unit(s), in=1700, out=210, cache_read=9000, wall_s=45.0"
        in text
    )
    assert "deepseekPro: 1 unit(s), in=600, out=90, cache_read=180, wall_s=14.0" in text
    assert (
        "deepseekFlash: 1 unit(s), in=6000, out=900, cache_read=1800, wall_s=15.0"
        in text
    )

    # Fix rounds per task, from the task records.
    assert "fix rounds per task:" in text
    assert "T1: 2 round(s)" in text
    assert "T2: 1 round(s)" in text


def test_rollup_week_fix_rounds_from_findings(tmp_path):
    """Fix rounds per task come from findings' task/round, not only task records."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    findings = [
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf",
            "task": "T1",
            "round": 1,
            "severity": "major",
            "file": "a.py",
            "title": "a",
            "class": None,
        },
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf",
            "task": "T1",
            "round": 2,
            "severity": "minor",
            "file": "b.py",
            "title": "b",
            "class": None,
        },
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf",
            "task": "T2",
            "round": 3,
            "severity": "minor",
            "file": "c.py",
            "title": "c",
            "class": None,
        },
    ]
    with open(out / "factory-findings.jsonl", "w") as fh:
        fh.writelines(
            json.dumps(finding, sort_keys=True) + "\n" for finding in findings
        )

    # Findings carry no timestamp; they window by joining to their run via
    # run_id. Give "wf" an in-window run so the findings stay in scope.
    runs = [
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf",
            "started": "2026-09-03T10:00:00.000Z",
            "tasks": [],
        }
    ]
    with open(out / "factory-runs.jsonl", "w") as fh:
        fh.writelines(json.dumps(run, sort_keys=True) + "\n" for run in runs)

    text = factory.rollup(out, week=True, since="2026-08-28", until="2026-09-05")
    assert "fix rounds per task:" in text
    assert "T1: 2 round(s)" in text
    assert "T2: 3 round(s)" in text


def test_rollup_week_windows_records(tmp_path):
    """--since/--until confine every lane, role and fix-round total to the window.

    One in-window and one out-of-window dsh session, plus one out-of-window
    factory run (with an agent and a finding), must not leak into any total;
    the first output line names the window bounds.
    """
    out = tmp_path / "ledger"
    out.mkdir()

    sessions = [
        {
            "v": 1,
            "src": "dsh",
            "session_id": "in",
            "slug": "slug-a",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "started": 1788546865000,  # 2026-09-04, in window
            "turns": 1,
            "steps": 1,
            "tools": 1,
            "in": 600,
            "out": 90,
            "cache_read": 180,
            "reasoning": 60,
            "wall_s": 14.0,
        },
        {
            "v": 1,
            "src": "dsh",
            "session_id": "out",
            "slug": "slug-b",
            "role": "deepseekFlash",
            "model": "deepseek/deepseek-v4-flash",
            "started": 1705276800000,  # 2024-01-15, out of window
            "turns": 1,
            "steps": 1,
            "tools": 1,
            "in": 9999,
            "out": 999,
            "cache_read": 999,
            "reasoning": 99,
            "wall_s": 99.0,
        },
    ]
    with open(out / "dsh-sessions.jsonl", "w") as fh:
        fh.writelines(json.dumps(s, sort_keys=True) + "\n" for s in sessions)

    runs = [
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf-in",
            "started": "2026-09-03T10:00:00.000Z",
            "tasks": [{"key": "T1", "fix_rounds": 2}],
        },
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf-out",
            "started": "2024-01-15T00:00:00.000Z",
            "tasks": [{"key": "T2", "fix_rounds": 7}],
        },
    ]
    with open(out / "factory-runs.jsonl", "w") as fh:
        fh.writelines(json.dumps(r, sort_keys=True) + "\n" for r in runs)

    agents = [
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf-in",
            "agent_id": "a-in",
            "label": None,
            "role_model": "claude-fable-5",
            "model_id": "claude-fable-5",
            "tokens": {
                "in": 1000,
                "out": 100,
                "cache_read": 500,
                "cache_write": 50,
                "thinking": 25,
            },
            "wall_s": 10.0,
            "tool_uses": 1,
        },
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf-out",
            "agent_id": "a-out",
            "label": None,
            "role_model": "claude-opus-4-1",
            "model_id": "claude-opus-4-1",
            "tokens": {
                "in": 9999,
                "out": 999,
                "cache_read": 999,
                "cache_write": 99,
                "thinking": 9,
            },
            "wall_s": 99.0,
            "tool_uses": 1,
        },
    ]
    with open(out / "factory-agents.jsonl", "w") as fh:
        fh.writelines(json.dumps(a, sort_keys=True) + "\n" for a in agents)

    findings = [
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf-in",
            "task": "T3",
            "round": 4,
            "severity": "major",
            "file": "in.py",
            "title": "in",
            "class": None,
        },
        {
            "v": 1,
            "src": "factory",
            "run_id": "wf-out",
            "task": "T4",
            "round": 9,
            "severity": "minor",
            "file": "out.py",
            "title": "out",
            "class": None,
        },
    ]
    with open(out / "factory-findings.jsonl", "w") as fh:
        fh.writelines(json.dumps(f, sort_keys=True) + "\n" for f in findings)

    text = factory.rollup(out, week=True, since="2026-08-28", until="2026-09-05")

    first = text.splitlines()[0]
    assert first == "window: 2026-08-28T00:00:00Z .. 2026-09-05T00:00:00Z"

    # Lane totals: only the in-window record of each lane.
    assert (
        "factory: 1 agent(s), in=1000, out=100, cache_read=500, "
        "cache_write=50, thinking=25, wall_s=10.0"
    ) in text
    assert (
        "dsh: 1 session(s), in=600, out=90, cache_read=180, reasoning=60, wall_s=14.0"
    ) in text

    # Role totals: in-window roles present, out-of-window roles absent.
    assert "tokens per role:" in text
    assert (
        "claude-fable-5: 1 unit(s), in=1000, out=100, cache_read=500, wall_s=10.0"
    ) in text
    assert (
        "deepseekPro: 1 unit(s), in=600, out=90, cache_read=180, wall_s=14.0"
    ) in text
    assert "claude-opus-4-1" not in text
    assert "deepseekFlash" not in text

    # Fix rounds: in-window tasks/findings present, out-of-window absent.
    assert "fix rounds per task:" in text
    assert "T1: 2 round(s)" in text
    assert "T3: 4 round(s)" in text
    assert "T2" not in text
    assert "T4" not in text


def test_rollup_week_defaults_to_trailing_seven_days_utc(tmp_path):
    """Without --since/--until the window is the trailing 7 days in UTC."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    text = factory.rollup(out, week=True, now=now)
    first = text.splitlines()[0]
    assert first.startswith("window: ")

    bounds = first[len("window: ") :].split(" .. ")
    since = dt.datetime.strptime(bounds[0], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.timezone.utc
    )
    until = dt.datetime.strptime(bounds[1], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.timezone.utc
    )
    assert until - since == dt.timedelta(days=7)
    assert abs((until - now).total_seconds()) < 60


def test_rollup_week_costs_are_windowed(tmp_path):
    """--week must window the cost total too, not just the lane/role lines.

    One in-window and one out-of-window dsh session, both priced. The cost line
    must sum only the in-window session: the out-of-window priced session may
    not leak a lifetime dollar total under the window header.
    """
    out = tmp_path / "ledger"
    out.mkdir()

    sessions = [
        {
            "v": 1,
            "src": "dsh",
            "session_id": "in",
            "slug": "a",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "started": 1788546865000,  # 2026-09-04, in window
            "in": 600,
            "out": 90,
            "cache_read": 180,
            "reasoning": 60,
            "wall_s": 14.0,
        },
        {
            "v": 1,
            "src": "dsh",
            "session_id": "out",
            "slug": "b",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "started": 1705276800000,  # 2024-01-15, out of window
            "in": 1000000,
            "out": 0,
            "cache_read": 0,
            "reasoning": 0,
            "wall_s": 0.0,
        },
    ]
    with open(out / "dsh-sessions.jsonl", "w") as fh:
        fh.writelines(json.dumps(s, sort_keys=True) + "\n" for s in sessions)

    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,model,in_per_1m,out_per_1m,cache_read_per_1m\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1\n"
        "2024-01-15,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1\n"
    )

    text = factory.rollup(
        out, week=True, costs_csv=prices, since="2026-08-28", until="2026-09-05"
    )
    lines = text.splitlines()
    assert lines[0] == "window: 2026-08-28T00:00:00Z .. 2026-09-05T00:00:00Z"
    assert "estimated cost: 0.000798 USD (price table, 1 session(s))" in lines
    assert "estimated cost: 1.000798 USD" not in lines


def test_rollup_week_single_bound_derivation(tmp_path):
    """A missing bound derives from the other: --since ends at now, --until starts 7d back."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    now = dt.datetime(2026, 9, 11, 10, 0, 0, tzinfo=dt.timezone.utc)

    text = factory.rollup(out, week=True, since="2026-09-04", now=now)
    assert (
        text.splitlines()[0] == "window: 2026-09-04T00:00:00Z .. 2026-09-11T10:00:00Z"
    )

    text = factory.rollup(out, week=True, until="2026-09-11", now=now)
    assert (
        text.splitlines()[0] == "window: 2026-09-04T00:00:00Z .. 2026-09-11T00:00:00Z"
    )


def test_rollup_week_half_open_boundary(tmp_path):
    """The window is half-open [since, until): a session at exactly `until` is out."""
    out = tmp_path / "ledger"
    out.mkdir()

    since_dt = dt.datetime(2026, 8, 28, tzinfo=dt.timezone.utc)
    until_dt = dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc)
    at_since_ms = int(since_dt.timestamp() * 1000)
    at_until_ms = int(until_dt.timestamp() * 1000)

    sessions = [
        {
            "v": 1,
            "src": "dsh",
            "session_id": "at-since",
            "slug": "a",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "started": at_since_ms,  # exactly since -> in
            "in": 100,
            "out": 0,
            "cache_read": 0,
            "reasoning": 0,
            "wall_s": 0.0,
        },
        {
            "v": 1,
            "src": "dsh",
            "session_id": "at-until",
            "slug": "b",
            "role": "deepseekFlash",
            "model": "deepseek/deepseek-v4-flash",
            "started": at_until_ms,  # exactly until -> out
            "in": 9999,
            "out": 999,
            "cache_read": 999,
            "reasoning": 99,
            "wall_s": 99.0,
        },
    ]
    with open(out / "dsh-sessions.jsonl", "w") as fh:
        fh.writelines(json.dumps(s, sort_keys=True) + "\n" for s in sessions)

    text = factory.rollup(out, week=True, since="2026-08-28", until="2026-09-05")
    lines = text.splitlines()
    assert lines[0] == "window: 2026-08-28T00:00:00Z .. 2026-09-05T00:00:00Z"
    assert (
        "dsh: 1 session(s), in=100, out=0, cache_read=0, reasoning=0, wall_s=0.0"
    ) in text
    assert "deepseekFlash" not in text


def test_rollup_cli_since_until_require_week():
    """--since/--until are only meaningful with --week; without it they are an error."""
    for flags in (["--since", "2026-09-04"], ["--until", "2026-09-04"]):
        with pytest.raises(SystemExit) as excinfo:
            factory.main(["rollup", *flags])
        assert excinfo.value.code == 2


def test_rollup_costs_no_start_time_is_distinct(tmp_path):
    """A session with no `started` is named 'no start time', not a (None, model) miss."""
    out = tmp_path / "ledger"
    out.mkdir()

    sessions = [
        {
            "v": 1,
            "src": "dsh",
            "session_id": "priced",
            "slug": "a",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "started": 1788546865000,  # 2026-09-04
            "in": 600,
            "out": 90,
            "cache_read": 180,
            "reasoning": 60,
            "wall_s": 14.0,
        },
        {
            "v": 1,
            "src": "dsh",
            "session_id": "nostart",
            "slug": "b",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "in": 100,
            "out": 10,
            "cache_read": 20,
            "reasoning": 5,
            "wall_s": 0.0,
        },
    ]
    with open(out / "dsh-sessions.jsonl", "w") as fh:
        fh.writelines(json.dumps(s, sort_keys=True) + "\n" for s in sessions)

    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,model,in_per_1m,out_per_1m,cache_read_per_1m\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1\n"
    )

    text = factory.rollup(out, costs_csv=prices)
    lines = text.splitlines()
    assert "no start time" in text
    assert "no cost row for (None," not in text
    assert "estimated cost: 0.000798 USD (price table, 1 session(s))" in lines
    assert "unpriced: 1 of 2 unit(s): no start time for 1 session(s)" in lines


# ---------------------------------------------------------------------------
# N16: lane results and the OpenRouter activity export (reported cost first)
# ---------------------------------------------------------------------------


def test_extract_lane_records_cost_usd(tmp_path):
    """A lane result with `usage.cost` records `cost_usd`; a refused job does not.

    The lane result is the OpenRouter-reported cost source that needs no
    price table. A result without a `usage` object (a refusal/error result)
    records `cost_usd: null` rather than inventing a dollar.
    """
    out = tmp_path / "ledger"
    out.mkdir()
    records = factory.extract_lane(LANE_FIXTURE, out)
    assert len(records) == 2

    # Idempotent by (lane, job_id): re-extracting never duplicates a line.
    factory.extract_lane(LANE_FIXTURE, out)
    written = read_jsonl(out / "lane-jobs.jsonl")
    assert len(written) == 2

    by_job = {r["job_id"]: r for r in written}
    with_cost = by_job["3f9a1c7e2b04"]
    with_cost.pop("ts")
    assert with_cost == {
        "v": 1,
        "kind": "lane-job",
        "src": "lane",
        "lane": "openrouter",
        "job_id": "3f9a1c7e2b04",
        "model": "deepseek/deepseek-v4-flash",
        "provider": "DeepInfra",
        "ts_epoch": 1788546900.0,
        "cost_usd": 2.5e-05,
    }

    refused = by_job["5e7b8c9d0001"]
    assert refused["cost_usd"] is None
    assert refused["model"] is None
    assert refused["provider"] is None


def test_rollup_activity_export_is_preferred_over_price_table(tmp_path):
    """A reported (activity) cost wins over the price table for a session's date+model.

    The activity export keys by date+model and its `cost` column is summed
    across request rows. The pro session has both an activity row and a price
    row: it must be reported, not re-estimated, so the estimated total covers
    only the flash session (price-table fallback).
    """
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,model,in_per_1m,out_per_1m,cache_read_per_1m\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1\n"
        "2026-09-04,deepseek/deepseek-v4-flash,0.5,1.0,0.05\n"
    )

    text = factory.rollup(out, costs_csv=prices, activity_csv=ACTIVITY_FIXTURE)
    lines = text.splitlines()

    # Two activity rows for the pro model sum to 0.001000 reported.
    assert ("reported cost: 0.001000 USD (lane 0.000000 + activity 0.001000)") in lines
    # The pro session is reported, not estimated; only flash falls back to
    # the price table (0.00399).
    assert "estimated cost: 0.003990 USD (price table, 1 session(s))" in lines
    assert "0.000798 USD" not in text
    # Every session is reported or estimated -- no unpriced line.
    assert not any(line.startswith("unpriced:") for line in lines)


def test_rollup_names_session_with_neither_reported_nor_priced(tmp_path):
    """A session whose date+model has no activity row and no price row is named."""
    out = tmp_path / "ledger"
    out.mkdir()

    sessions = [
        {
            "v": 1,
            "src": "dsh",
            "session_id": "reported",
            "slug": "a",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "started": 1788546865000,  # 2026-09-04
            "in": 600,
            "out": 90,
            "cache_read": 180,
            "reasoning": 60,
            "wall_s": 14.0,
        },
        {
            "v": 1,
            "src": "dsh",
            "session_id": "estimated",
            "slug": "b",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "started": 1788633265000,  # 2026-09-05
            "in": 1000,
            "out": 100,
            "cache_read": 0,
            "reasoning": 0,
            "wall_s": 1.0,
        },
        {
            "v": 1,
            "src": "dsh",
            "session_id": "neither",
            "slug": "c",
            "role": "deepseekFlash",
            "model": "deepseek/deepseek-v4-flash",
            "started": 1788633265000,  # 2026-09-05
            "in": 6000,
            "out": 900,
            "cache_read": 1800,
            "reasoning": 600,
            "wall_s": 1.0,
        },
    ]
    with open(out / "dsh-sessions.jsonl", "w") as fh:
        fh.writelines(json.dumps(s, sort_keys=True) + "\n" for s in sessions)

    activity = tmp_path / "activity.csv"
    activity.write_text(
        "date,model,cost\n2026-09-04,deepseek/deepseek-v4-pro-0813,0.001000\n"
    )
    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,model,in_per_1m,out_per_1m,cache_read_per_1m\n"
        "2026-09-05,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1\n"
    )

    text = factory.rollup(out, costs_csv=prices, activity_csv=activity)
    lines = text.splitlines()

    assert ("reported cost: 0.001000 USD (lane 0.000000 + activity 0.001000)") in lines
    # 1000/1e6*1.0 + 100/1e6*2.0 = 0.0012 for the price-table fallback on 09-05.
    assert "estimated cost: 0.001200 USD (price table, 1 session(s))" in lines
    assert (
        "unpriced: 1 of 3 unit(s): no cost row for "
        "(2026-09-05, deepseek/deepseek-v4-flash)"
    ) in lines


def test_rollup_reported_total_includes_lane_jobs(tmp_path):
    """Reported cost is lane results (exact) plus the activity export (per date+model)."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)
    factory.extract_lane(LANE_FIXTURE, out)

    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,model,in_per_1m,out_per_1m,cache_read_per_1m\n"
        "2026-09-04,deepseek/deepseek-v4-flash,0.5,1.0,0.05\n"
    )

    text = factory.rollup(out, costs_csv=prices, activity_csv=ACTIVITY_FIXTURE)
    lines = text.splitlines()

    # Lane 0.000025 (one job) + activity 0.001000 (pro, two summed rows).
    assert ("reported cost: 0.001025 USD (lane 0.000025 + activity 0.001000)") in lines
    assert "estimated cost: 0.003990 USD (price table, 1 session(s))" in lines
    # The refused lane job recorded cost_usd null and is named unpriced, not
    # silently dropped from the denominator (2 sessions + 2 lane jobs = 4).
    assert ("unpriced: 1 of 4 unit(s): no reported cost for 1 lane job(s)") in lines


def test_rollup_week_costs_names_no_start_session(tmp_path):
    """--week --costs must name a no-start session, not silently window it away."""
    out = tmp_path / "ledger"
    out.mkdir()

    sessions = [
        {
            "v": 1,
            "src": "dsh",
            "session_id": "in",
            "slug": "a",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "started": 1788546865000,  # 2026-09-04, in window
            "in": 600,
            "out": 90,
            "cache_read": 180,
            "reasoning": 60,
            "wall_s": 14.0,
        },
        {
            "v": 1,
            "src": "dsh",
            "session_id": "nostart",
            "slug": "b",
            "role": "deepseekPro",
            "model": "deepseek/deepseek-v4-pro-0813",
            "in": 100,
            "out": 10,
            "cache_read": 20,
            "reasoning": 5,
            "wall_s": 0.0,
        },
    ]
    with open(out / "dsh-sessions.jsonl", "w") as fh:
        fh.writelines(json.dumps(s, sort_keys=True) + "\n" for s in sessions)

    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,model,in_per_1m,out_per_1m,cache_read_per_1m\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1\n"
    )

    text = factory.rollup(
        out, week=True, costs_csv=prices, since="2026-08-28", until="2026-09-05"
    )
    lines = text.splitlines()

    assert "estimated cost: 0.000798 USD (price table, 1 session(s))" in lines
    assert "no start time" in text
    assert "unpriced: 1 of 2 unit(s): no start time for 1 session(s)" in lines


def test_rollup_activity_rejects_price_table_shape(tmp_path):
    """--activity must reject a price-table-shaped CSV with a named error."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    prices_shaped = tmp_path / "prices.csv"
    prices_shaped.write_text(
        "date,model,in_per_1m,out_per_1m,cache_read_per_1m\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,1.0,2.0,0.1\n"
    )

    with pytest.raises(factory.ActivityExportError) as excinfo:
        factory.rollup(out, activity_csv=prices_shaped)

    message = str(excinfo.value)
    assert "cost" in message
    assert "date, model, in_per_1m, out_per_1m, cache_read_per_1m" in message


def test_rollup_activity_export_supersedes_lane_job_on_same_bucket(tmp_path):
    """The activity export is the single source of truth per (date, model).

    The export is account-wide, so a (date, model) bucket already contains the
    lane's requests. A lane job and an export row sharing date+model must not
    both count: the lane job's 0.000025 is inside the export's 0.004000 bucket,
    so the reported total is 0.004000, not 0.004025.
    """
    out = tmp_path / "ledger"
    out.mkdir()

    jobs = [
        {
            "v": 1,
            "src": "lane",
            "lane": "lr",
            "job_id": "covered",
            "model": "deepseek/deepseek-v4-flash",
            "provider": "DeepInfra",
            "ts_epoch": 1788546900.0,  # 2026-09-04
            "cost_usd": 0.000025,
        },
    ]
    with open(out / "lane-jobs.jsonl", "w") as fh:
        fh.writelines(json.dumps(j, sort_keys=True) + "\n" for j in jobs)

    activity = tmp_path / "activity.csv"
    activity.write_text(
        "date,model,cost\n2026-09-04,deepseek/deepseek-v4-flash,0.004000\n"
    )

    text = factory.rollup(out, activity_csv=activity)
    lines = text.splitlines()
    assert "reported cost: 0.004000 USD (lane 0.000000 + activity 0.004000)" in lines
    assert "0.004025" not in text


def test_rollup_activity_unattributed_bucket_is_reported_and_named(tmp_path):
    """An export bucket joined to no session contributes and is named, not dropped."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    activity = tmp_path / "activity.csv"
    activity.write_text(
        "date,model,cost\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,0.000500\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,0.000500\n"
        "2026-09-04,openai/gpt-9,5.000000\n"
    )

    text = factory.rollup(out, activity_csv=activity)
    lines = text.splitlines()
    assert "reported cost: 5.001000 USD (lane 0.000000 + activity 5.001000)" in lines
    assert "unattributed activity: (2026-09-04, openai/gpt-9) 5.000000 USD" in lines


def test_rollup_week_windows_lane_jobs(tmp_path):
    """--week must confine the reported cost to in-window lane jobs.

    Deleting the lane-job window filter would leak the out-of-window 9.0 job
    into the reported total (9.000025 instead of 0.000025).
    """
    out = tmp_path / "ledger"
    out.mkdir()

    jobs = [
        {
            "v": 1,
            "src": "lane",
            "lane": "lr",
            "job_id": "in",
            "model": "deepseek/deepseek-v4-flash",
            "provider": "DeepInfra",
            "ts_epoch": 1788546900.0,  # 2026-09-04, in window
            "cost_usd": 0.000025,
        },
        {
            "v": 1,
            "src": "lane",
            "lane": "lr",
            "job_id": "out",
            "model": "deepseek/deepseek-v4-flash",
            "provider": "DeepInfra",
            "ts_epoch": 1705276800.0,  # 2024-01-15, out of window
            "cost_usd": 9.0,
        },
    ]
    with open(out / "lane-jobs.jsonl", "w") as fh:
        fh.writelines(json.dumps(j, sort_keys=True) + "\n" for j in jobs)

    text = factory.rollup(out, week=True, since="2026-08-28", until="2026-09-05")
    lines = text.splitlines()
    assert "reported cost: 0.000025 USD (lane 0.000025 + activity 0.000000)" in lines
    assert "9.000025" not in text


def test_rollup_unpriced_lane_jobs_are_named_without_costs(tmp_path):
    """All-unpriced lane jobs with no --costs/--activity must be named (count and ids)."""
    out = tmp_path / "ledger"
    out.mkdir()

    jobs = [
        {
            "v": 1,
            "src": "lane",
            "lane": "lr",
            "job_id": "aaa",
            "model": None,
            "provider": None,
            "ts_epoch": 1788546900.0,
            "cost_usd": None,
        },
        {
            "v": 1,
            "src": "lane",
            "lane": "lr",
            "job_id": "bbb",
            "model": None,
            "provider": None,
            "ts_epoch": 1788546900.0,
            "cost_usd": None,
        },
    ]
    with open(out / "lane-jobs.jsonl", "w") as fh:
        fh.writelines(json.dumps(j, sort_keys=True) + "\n" for j in jobs)

    text = factory.rollup(out)
    assert "cost: unknown (no price table); 2 unpriced lane job(s): aaa, bbb" in text


def test_rollup_activity_blank_cost_raises_named_error(tmp_path):
    """A blank cost cell is an ActivityExportError naming the row, not a ValueError."""
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)

    activity = tmp_path / "activity.csv"
    activity.write_text(
        "date,model,cost\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,0.000500\n"
        "2026-09-04,openai/gpt-9,\n"
    )

    with pytest.raises(factory.ActivityExportError) as excinfo:
        factory.rollup(out, activity_csv=activity)

    assert "row 3" in str(excinfo.value)


def test_rollup_week_windows_activity_export(tmp_path):
    """--week must filter export buckets to the window before summing or naming.

    An out-of-window export row (2024-01-15, openai/gpt-9, 9.0) must not leak
    into the weekly reported total nor into the unattributed list; without
    --week the same row is included and named.
    """
    out = tmp_path / "ledger"
    out.mkdir()
    factory.extract_dsh(DSH_FIXTURES, out)
    factory.extract_lane(LANE_FIXTURE, out)

    activity = tmp_path / "activity.csv"
    activity.write_text(
        "date,model,cost\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,0.000500\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,0.000500\n"
        "2024-01-15,openai/gpt-9,9.000000\n"
    )

    text = factory.rollup(
        out, week=True, activity_csv=activity, since="2026-08-28", until="2026-09-05"
    )
    lines = text.splitlines()
    # In-window pro rows sum to 0.001000; the in-window lane job adds 0.000025.
    assert "reported cost: 0.001025 USD (lane 0.000025 + activity 0.001000)" in lines
    assert "unattributed activity: (2024-01-15, openai/gpt-9)" not in text
    assert "9.001025" not in text

    # Without --week the same export row is included and named unattributed.
    text = factory.rollup(out, activity_csv=activity)
    lines = text.splitlines()
    assert "reported cost: 9.001025 USD (lane 0.000025 + activity 9.001000)" in lines
    assert "unattributed activity: (2024-01-15, openai/gpt-9) 9.000000 USD" in lines


def test_load_activity_reads_the_real_openrouter_export():
    """The real export parses: created_at -> date (date part only), model_permaslug -> model, cost_total -> cost.

    Two dates and two models across four rows; the cancelled row still counts
    its cost. Every row's cost is summed into its (date, model) bucket.
    """
    result = factory._load_activity(ACTIVITY_EXPORT_FIXTURE)
    assert result == {
        ("2026-09-04", "deepseek/deepseek-v4-pro-0813"): 0.001000,
        ("2026-09-05", "deepseek/deepseek-v4-flash"): 0.000500,
    }


def test_load_activity_legacy_shape_still_parses(tmp_path):
    """The legacy date,model,cost shape parses alongside the real export."""
    legacy = tmp_path / "legacy.csv"
    legacy.write_text(
        "date,model,cost\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,0.000500\n"
        "2026-09-04,deepseek/deepseek-v4-pro-0813,0.000500\n"
    )
    assert factory._load_activity(legacy) == {
        ("2026-09-04", "deepseek/deepseek-v4-pro-0813"): 0.001000,
    }


def test_load_activity_unknown_shape_names_both_shapes(tmp_path):
    """An unrelated header raises ActivityExportError naming BOTH accepted column sets."""
    bad = tmp_path / "bad.csv"
    bad.write_text("foo,bar,baz\n1,2,3\n")
    with pytest.raises(factory.ActivityExportError) as excinfo:
        factory._load_activity(bad)
    message = str(excinfo.value)
    # The full joined phrase -- both column sets with the " or " separator --
    # must appear, so the message cannot silently run the two sets together.
    assert "date, model, cost or created_at, model_permaslug, cost_total" in message


def test_rollup_activity_bucket_covered_by_lane_job_is_not_unattributed(tmp_path):
    """A bucket covered by a lane job but no session is attributed to the lane.

    Major A's exact case: a lane flash job (0.000025) shares its date+model
    bucket with an export row (0.004000). The export is the single source of
    truth, and the bucket is attributed to the lane job, so it must not also be
    named 'unattributed activity'.
    """
    out = tmp_path / "ledger"
    out.mkdir()

    jobs = [
        {
            "v": 1,
            "src": "lane",
            "lane": "lr",
            "job_id": "covered",
            "model": "deepseek/deepseek-v4-flash",
            "provider": "DeepInfra",
            "ts_epoch": 1788546900.0,  # 2026-09-04
            "cost_usd": 0.000025,
        },
    ]
    with open(out / "lane-jobs.jsonl", "w") as fh:
        fh.writelines(json.dumps(j, sort_keys=True) + "\n" for j in jobs)

    activity = tmp_path / "activity.csv"
    activity.write_text(
        "date,model,cost\n2026-09-04,deepseek/deepseek-v4-flash,0.004000\n"
    )

    text = factory.rollup(out, activity_csv=activity)
    lines = text.splitlines()
    assert "reported cost: 0.004000 USD (lane 0.000000 + activity 0.004000)" in lines
    assert not any(line.startswith("unattributed activity:") for line in lines)
    assert "0.004025" not in text
