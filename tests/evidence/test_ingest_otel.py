"""The otel ingest (plan 2026-09-08-spend-telemetry, SP7).

`evidence ingest otel [--root DIR] <path>…` turns the collector's OTLP-JSON
files into `ledger/otel-claude` rows keyed `(session_id, sample_id)`: one
`tokens` row per `claude_code.token.usage` data point and one `request` row per
`api_request` log record. Every other metric/event is skipped; a line carrying
a `user.*`/`organization.*` attribute, a non-numeric `timeUnixNano`, a missing
`session.id`, a missing `request_id` or a non-model-id `model` is refused. Every
path is realpath-fenced under `--root` before any read; a torn (unterminated)
last line is reported and skipped — never refused — because the collector is
still writing it.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
FIXTURES = HERE.parent / "fixtures" / "otel"


def _load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "ingest_otel.py",
        pathlib.Path("pkgs/evidence/ingest_otel.py"),
    ]
    src = next(p for p in candidates if p.exists())
    if str(src.parent) not in sys.path:
        sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("ingest_otel", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ingest_otel"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load()
import evidence as ev


def _run_ingest(store, paths, root=None):
    argv = ["--store", str(store), "otel"]
    if root is not None:
        argv += ["--root", str(root)]
    argv += [str(p) for p in paths]
    return mod.main(argv)


def test_metrics_two_tokens_rows(tmp_path, capsys):
    # Line 1's two token.usage points become two `tokens` rows (asDouble 10.0
    # and the string asInt "17584" -> int 17584); the cost.usage metric is
    # skipped; lines 2-5 (identity x2, missing session, missing timeUnixNano)
    # are refused. Mutants: `int(float(...))` for asInt (or float) -> value is
    # a float; split at `]` -> `model: not a model-id`; float division in `at`
    # -> `…779Z`; dropping the missing-field arm silently instead of refusing.
    store = tmp_path / "ev"
    assert _run_ingest(store, [FIXTURES / "metrics.jsonl"], root=FIXTURES) == 1
    captured = capsys.readouterr()
    assert (
        "ingested 2 rows into ledger/otel-claude (4 refused, 1 skipped)" in captured.out
    )
    rows = ev.read(str(store), "ledger/otel-claude")
    assert len(rows) == 2
    by_type = {r["token_type"]: r for r in rows}
    assert by_type["input"]["value"] == 10.0
    assert by_type["cacheRead"]["value"] == 17584
    assert type(by_type["cacheRead"]["value"]) is int
    for r in rows:
        assert r["model"] == "claude-opus-5"
        assert r["model_suffix"] == "1m"
        assert r["harness_version"] == "2.1.258"
        assert r["terminal_type"] == "probe"
        assert r["at"] == "2026-09-08T22:24:13.213778Z"
        assert r["sample"] == "tokens"


def test_identity_attributes_refused(tmp_path, capsys):
    # Both the `user.email` point (line 2) and the `user.name` point (line 3)
    # are refused by the first-`.token` identity rule. Mutant: an exact-match
    # list of the four known keys -> `user.name` lands.
    store = tmp_path / "ev"
    assert _run_ingest(store, [FIXTURES / "metrics.jsonl"], root=FIXTURES) == 1
    captured = capsys.readouterr()
    assert (
        "user.email: identity attribute present (the collector's allowlist is broken)"
        in captured.err
    )
    assert (
        "user.name: identity attribute present (the collector's allowlist is broken)"
        in captured.err
    )


def test_logs_one_request_row(tmp_path, capsys):
    # The first api_request becomes one `request` row; the user_prompt is
    # skipped; the Claude-X model, the missing request_id, missing session.id
    # and missing timeUnixNano records are refused. Mutants: `intValue` kept as
    # a string -> `input_tokens: not a int`; `user_prompt` mapped; the two
    # missing-field arms skipped instead of refused.
    store = tmp_path / "ev"
    assert _run_ingest(store, [FIXTURES / "logs.jsonl"], root=FIXTURES) == 1
    captured = capsys.readouterr()
    assert (
        "ingested 1 rows into ledger/otel-claude (4 refused, 1 skipped)" in captured.out
    )
    rows = ev.read(str(store), "ledger/otel-claude")
    assert len(rows) == 1
    r = rows[0]
    assert r["sample"] == "request"
    assert r["sample_id"] == "req_fixture"
    assert r["request_id"] == "req_fixture"
    assert r["session_id"] == "sess-fixture"
    assert r["cost_usd"] == 0.0123
    assert r["input_tokens"] == 2
    assert r["output_tokens"] == 77
    assert r["cache_read_tokens"] == 1000
    assert r["cache_creation_tokens"] == 500
    assert r["duration_ms"] == 1200
    assert r["query_source"] == "main"
    assert r["agent_name"] == "gate-reviewer"
    assert r["skill_name"] == "code-review"
    assert r["speed"] == "medium"
    assert r["effort"] == "high"
    assert r["model"] == "claude-opus-5"
    assert r["model_suffix"] is None
    assert r["harness_version"] == "2.1.258"
    assert r["terminal_type"] == "probe"
    assert r["at"] == "2026-09-08T22:24:13.213778Z"
    assert r["token_type"] is None
    assert r["value"] is None
    assert "model: not a model-id" in captured.err
    assert "request_id: missing" in captured.err
    assert "session_id: missing" in captured.err
    assert "timeUnixNano: missing" in captured.err


def test_two_runs_same_rows(tmp_path):
    # replace_stream merges by (session_id, sample_id), so a re-ingest keeps the
    # two rows unchanged. Mutant: append -> four rows.
    store = tmp_path / "ev"
    assert _run_ingest(store, [FIXTURES / "metrics.jsonl"], root=FIXTURES) == 1
    first = ev.read(str(store), "ledger/otel-claude")
    assert _run_ingest(store, [FIXTURES / "metrics.jsonl"], root=FIXTURES) == 1
    second = ev.read(str(store), "ledger/otel-claude")
    assert len(second) == 2
    assert second == first


def test_unsupported_wrapper_refused(tmp_path, capsys):
    # A planted `arrayValue` attribute value wrapper is refused. Mutant: ignore
    # the wrapper (treat as absent) -> the point lands.
    store = tmp_path / "ev"
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        json.dumps(
            {
                "resourceMetrics": [
                    {
                        "resource": {"attributes": []},
                        "scopeMetrics": [
                            {
                                "scope": {"name": "x"},
                                "metrics": [
                                    {
                                        "name": "claude_code.token.usage",
                                        "sum": {
                                            "dataPoints": [
                                                {
                                                    "attributes": [
                                                        {
                                                            "key": "type",
                                                            "value": {
                                                                "stringValue": "input"
                                                            },
                                                        },
                                                        {
                                                            "key": "model",
                                                            "value": {
                                                                "stringValue": "claude-opus-5"
                                                            },
                                                        },
                                                        {
                                                            "key": "session.id",
                                                            "value": {
                                                                "stringValue": "sess-fixture"
                                                            },
                                                        },
                                                        {
                                                            "key": "terminal.type",
                                                            "value": {
                                                                "stringValue": "probe"
                                                            },
                                                        },
                                                        {
                                                            "key": "speed",
                                                            "value": {"arrayValue": []},
                                                        },
                                                    ],
                                                    "timeUnixNano": "1788906253213778862",
                                                    "asDouble": 1.0,
                                                }
                                            ]
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        )
        + "\n"
    )
    assert _run_ingest(store, [bad], root=tmp_path) == 1
    captured = capsys.readouterr()
    assert "attribute speed: unsupported value type" in captured.err
    assert ev.read(str(store), "ledger/otel-claude") == []


def test_fence_torn_help_bogus(tmp_path, capsys):
    # A path outside --root is fenced (exit 2, nothing written); a torn last
    # line is reported and skipped, not refused (exit 0); the subcommand help
    # exits 0; an unknown target's stderr ends with the otel list tail. Mutant:
    # drop the fence -> the outside file is written; treat torn as not-JSON.
    store = tmp_path / "ev"
    outside = tmp_path / "outside.jsonl"
    outside.write_text('{"resourceMetrics":[]}\n')
    assert _run_ingest(store, [outside], root=tmp_path / "root") == 2
    assert not (store / "ledger" / "otel-claude.jsonl").exists()

    torn = tmp_path / "torn.jsonl"
    torn.write_text('{"resourceLogs":[{"resource":{"attributes":[]},"scopeLogs":[]}]}')
    assert _run_ingest(store, [torn], root=tmp_path) == 0
    assert "last line torn" in capsys.readouterr().err

    r = subprocess.run(
        [sys.executable, str(ev.__file__), "ingest", "otel", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr

    r = subprocess.run(
        [sys.executable, str(ev.__file__), "ingest", "bogus", "x"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 2
    assert r.stderr.rstrip().endswith("|otel)")


def test_missing_required_fields_refused(tmp_path, capsys):
    # The no-session.id point (metrics line 4) and the no-timeUnixNano record
    # (logs record 6) are refused with their exact reasons. Mutant: omit either
    # arm -> the row is silently skipped, not refused.
    store = tmp_path / "ev"
    _run_ingest(store, [FIXTURES / "metrics.jsonl"], root=FIXTURES)
    assert "session_id: missing" in capsys.readouterr().err
    _run_ingest(store, [FIXTURES / "logs.jsonl"], root=FIXTURES)
    assert "timeUnixNano: missing" in capsys.readouterr().err
