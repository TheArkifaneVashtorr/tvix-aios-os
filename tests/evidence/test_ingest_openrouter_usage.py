"""The openrouter-usage ingest (plan 2026-09-08-spend-telemetry, SP8).

`evidence ingest openrouter-usage [--root DIR] <path>…` turns each of the
egress broker's `usage.jsonl` files into `ledger/openrouter-usage` rows keyed
`(instance, request_id)`, one row per line. Every path is realpath-fenced
under `--root` before any read; a torn (unterminated) last line is reported
and skipped — never refused — because the broker is still writing it.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
FIXTURES = HERE.parent / "fixtures" / "openrouter-usage"


def _load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "ingest_openrouter_usage.py",
        pathlib.Path("pkgs/evidence/ingest_openrouter_usage.py"),
    ]
    src = next(p for p in candidates if p.exists())
    if str(src.parent) not in sys.path:
        sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("ingest_openrouter_usage", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ingest_openrouter_usage"] = mod
    spec.loader.exec_module(mod)
    return mod


mod = _load()
import evidence as ev

iou = mod


def _run_ingest(store, paths, root=None):
    argv = ["--store", str(store), "openrouter-usage"]
    if root is not None:
        argv += ["--root", str(root)]
    argv += [str(p) for p in paths]
    return mod.main(argv)


def test_four_line_file_three_rows_one_refused(tmp_path, capsys):
    # The Bad Model line is refused (model: not a model-id at :4:), so the
    # four-line fixture yields three rows and exit 1. Mutant: forget `src` ->
    # every row misses `src`; always return 0 -> the exit code never turns 1.
    store = tmp_path / "ev"
    code = _run_ingest(store, [FIXTURES / "usage.jsonl"], root=FIXTURES)
    assert code == 1
    captured = capsys.readouterr()
    assert "model: not a model-id" in captured.err
    assert "usage.jsonl:4:" in captured.err
    assert (
        "ingested 3 rows into ledger/openrouter-usage "
        "(1 refused; attributed header 0, window 0, none 3)" in captured.out
    )
    rows = ev.read(str(store), "ledger/openrouter-usage")
    assert len(rows) == 3
    assert all(
        r["src"] == "broker"
        and r["attribution"] == "none"
        and r["run_id"] is None
        and r["key"] is None
        for r in rows
    )


def test_second_run_same_three_rows(tmp_path, capsys):
    # replace_stream merges by (instance, request_id), so a re-ingest of the
    # same file stays at three rows. Mutant: append instead of replace_stream
    # -> six rows.
    store = tmp_path / "ev"
    assert _run_ingest(store, [FIXTURES / "usage.jsonl"], root=FIXTURES) == 1
    capsys.readouterr()
    assert _run_ingest(store, [FIXTURES / "usage.jsonl"], root=FIXTURES) == 1
    assert len(ev.read(str(store), "ledger/openrouter-usage")) == 3


def test_torn_last_line_reported_not_refused(tmp_path, capsys):
    # The truncated last line is skipped and reported, not refused, so the two
    # good lines still land and the exit is 0. Mutant: drop the torn rule ->
    # the fragment is "not JSON", refused, exit 1.
    store = tmp_path / "ev"
    assert _run_ingest(store, [FIXTURES / "torn.jsonl"], root=FIXTURES) == 0
    captured = capsys.readouterr()
    assert "last line torn" in captured.err
    assert len(ev.read(str(store), "ledger/openrouter-usage")) == 2


def test_outside_root_exits_two_and_symlink_root_accepted(tmp_path):
    # A path outside --root is fenced (exit 2, nothing written); the same file
    # reached through a symlinked root resolves inside and is accepted.
    # Mutant: drop the fence -> the outside file is written.
    store = tmp_path / "ev"
    outside = tmp_path / "outside.jsonl"
    outside.write_text('{"instance": "openrouter", "request_id": "' + "a" * 32 + '"}\n')
    assert _run_ingest(store, [outside], root=tmp_path / "root") == 2
    assert not (store / "ledger" / "openrouter-usage.jsonl").exists()

    link = tmp_path / "link"
    link.symlink_to(FIXTURES)
    store2 = tmp_path / "ev2"
    assert _run_ingest(store2, [link / "usage.jsonl"], root=link) == 1
    assert len(ev.read(str(store2), "ledger/openrouter-usage")) == 3


def test_help_and_bogus(tmp_path):
    # The subcommand help exits 0; an unknown target's stderr ends with the
    # full parenthesised target list. Mutant: leave openrouter-usage out of
    # INGEST_MODULES -> the help fails and the list ends at reviews).
    r = subprocess.run(
        [sys.executable, str(ev.__file__), "ingest", "openrouter-usage", "--help"],
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
    assert r.stderr.rstrip().endswith("otel)")


def test_empty_file_zero_rows(tmp_path, capsys):
    # An empty file yields zero rows and exit 0. Mutant: call replace_stream on
    # the empty batch in a way that raises on the missing stream path.
    store = tmp_path / "ev"
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    assert _run_ingest(store, [empty], root=tmp_path) == 0
    assert (
        "ingested 0 rows into ledger/openrouter-usage "
        "(0 refused; attributed header 0, window 0, none 0)" in capsys.readouterr().out
    )


def test_unwritable_store_exits_nonzero(tmp_path, capsys):
    # A 0500 store directory cannot be written: the mkdir of ledger/ under it
    # fails with an OSError, which the CLI must surface as a non-zero exit and
    # a message on stderr -- never swallow it into a quiet success. The torn
    # fixture has no refused rows, so a writable store would exit 0. Mutant:
    # catch OSError around the store write and keep going -> exit 0 -> fails.
    store = tmp_path / "ev"
    store.mkdir()
    store.chmod(0o500)
    code = _run_ingest(store, [FIXTURES / "torn.jsonl"], root=FIXTURES)
    assert code != 0
    assert "cannot write to the store" in capsys.readouterr().err


def _usage_row(request_id, provider, instance="openrouter", model=None):
    row = {
        "ts_epoch": 1788546900.0,
        "instance": instance,
        "request_id": request_id,
        "streamed": True,
        "http_status": 200,
        "status": "ok",
        "gen_id": None,
        "model": model or "deepseek/deepseek-v4-flash",
        "provider": provider,
        "cost_usd": 1.5e-06,
        "upstream_cost_usd": 1.5e-06,
        "is_byok": False,
        "prompt_tokens": 10,
        "completion_tokens": 3,
        "total_tokens": 13,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "reasoning_tokens": 0,
    }
    return json.dumps(row)


def test_provider_is_a_label_with_internal_spaces(tmp_path, capsys):
    # The broker writes the provider's display name, so a provider with an
    # internal space (`Sail Research` — the 15 rows the live backfill refused)
    # is a legal `label` and ingests, exit 0. Mutant A: retype provider back to
    # `id` -> the space fails, exit 1.
    store = tmp_path / "ev"
    f = tmp_path / "labels.jsonl"
    f.write_text(_usage_row("a" * 32, "Sail Research") + "\n")
    assert _run_ingest(store, [f], root=tmp_path) == 0
    captured = capsys.readouterr()
    assert (
        "ingested 1 rows into ledger/openrouter-usage "
        "(0 refused; attributed header 0, window 0, none 1)" in captured.out
    )
    rows = ev.read(str(store), "ledger/openrouter-usage")
    assert rows[0]["provider"] == "Sail Research"


def test_label_rejects_edge_spaces(tmp_path, capsys):
    # A label may not begin or end with a space, and stays under 120 chars.
    # Mutant B: LABEL_RE accepts a leading space -> the leading-space row
    # ingests instead of refusing.
    store = tmp_path / "ev"
    long = "a" * 121
    f = tmp_path / "edge.jsonl"
    f.write_text(
        "\n".join(
            [
                _usage_row("b" * 32, " Sail"),
                _usage_row("c" * 32, "Sail "),
                _usage_row("d" * 32, long),
            ]
        )
        + "\n"
    )
    assert _run_ingest(store, [f], root=tmp_path) == 1
    captured = capsys.readouterr()
    assert "provider: not a label" in captured.err
    assert captured.err.count("provider: not a label") == 3


def test_ids_still_refuse_an_embedded_space(tmp_path, capsys):
    # `instance` is still an `id` field; an embedded space in it must still
    # refuse. Mutant C: widen ID_RE instead of adding LABEL_RE -> the spaced
    # instance ingests.
    store = tmp_path / "ev"
    f = tmp_path / "ids.jsonl"
    f.write_text(
        "\n".join(
            [
                _usage_row("e" + "f" * 31, "Sail Research"),
                _usage_row("g" * 32, "Sail Research", instance="open router"),
            ]
        )
        + "\n"
    )
    assert _run_ingest(store, [f], root=tmp_path) == 1
    captured = capsys.readouterr()
    assert "instance: not a id" in captured.err


# --- OC5: attribution — header, window or none ------------------------------
# Every row lands with run_id/key/attribution: `header` when the broker
# recorded both halves of the x-factory-task address; else `window` when
# exactly one seat task's [mtime - wall_s, mtime] window contains the row;
# else `none` — ambiguity is printed, never guessed (D9-D11). r4 below sits
# at B's exact end bound: window B is [10:01:00, 10:02:40] and window A is
# [10:00:00, 10:01:40], so t+100 (A's end) would fall inside BOTH windows
# and print none; t+160 pins the inclusive end bound on B alone.

TASK_BASE = {"kind": "task-result", "seat_unit": "20260921-100000-abcdef"}


def _windows(store, rows):
    ev.replace_stream(str(store), "derived/tasks", [{**TASK_BASE, **r} for r in rows])


def _usage(ts, request_id, instance="seat", **extra):
    return {
        "ts_epoch": ts,
        "instance": instance,
        "request_id": request_id,
        "streamed": False,
        "http_status": 200,
        "status": "ok",
        "gen_id": None,
        "model": "z-ai/glm-5.3",
        "provider": "Z",
        "cost_usd": 0.5,
        "upstream_cost_usd": None,
        "is_byok": False,
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "total_tokens": 2,
        "cached_tokens": 0,
        "cache_write_tokens": 0,
        "reasoning_tokens": 0,
        **extra,
    }


def _write_usage(root, rows):
    p = root / "seat" / "usage.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def _rows(store):
    return {r["request_id"]: r for r in ev.read(str(store), "ledger/openrouter-usage")}


def test_attribution_header_window_none(tmp_path, capsys):
    # mutants: window before header -> r1 becomes "window"; strict bounds ->
    # r4 (ts == B's end) becomes "none"; drop the instance check -> r5
    # "window"; count candidates >= 1 as a match -> r3 "window".
    store, root = tmp_path / "store", tmp_path / "broker"
    _windows(
        store,
        [
            {  # 10:00:00-10:01:40
                "run_id": "r1",
                "key": "A",
                "wall_s": 100,
                "result_mtime": "2026-09-21T10:01:40Z",
            },
            {  # 10:01:00-10:02:40
                "run_id": "r1",
                "key": "B",
                "wall_s": 100,
                "result_mtime": "2026-09-21T10:02:40Z",
            },
            {
                "run_id": "r1",
                "key": "C",
                "wall_s": 50,
                "result_mtime": "2026-09-21T10:05:00Z",
                "seat_unit": None,
            },
        ],
    )
    t = int(dt.datetime(2026, 9, 21, 10, 0, tzinfo=dt.timezone.utc).timestamp())
    p = _write_usage(
        root,
        [
            _usage(
                t + 30, "0" * 31 + "1", run_id="r9", key="Z"
            ),  # header wins inside A's window
            _usage(t + 30, "0" * 31 + "2"),  # A alone -> window
            _usage(t + 90, "0" * 31 + "3"),  # A and B -> none
            _usage(t + 160, "0" * 31 + "4"),  # ts == B's end -> window
            _usage(
                t + 30, "0" * 31 + "5", instance="openrouter"
            ),  # not the seat -> none
            _usage(t + 275, "0" * 31 + "6"),  # C has no seat_unit -> none
            _usage(t + 500, "0" * 31 + "7"),  # nothing -> none
        ],
    )
    assert (
        iou.main(
            ["--store", str(store), "openrouter-usage", "--root", str(root), str(p)]
        )
        == 0
    )
    got = _rows(store)
    assert (got["0" * 31 + "1"]["attribution"], got["0" * 31 + "1"]["run_id"]) == (
        "header",
        "r9",
    )
    assert (got["0" * 31 + "2"]["attribution"], got["0" * 31 + "2"]["key"]) == (
        "window",
        "A",
    )
    assert got["0" * 31 + "3"]["attribution"] == "none"
    assert got["0" * 31 + "3"]["run_id"] is None
    assert got["0" * 31 + "4"]["attribution"] == "window"
    assert got["0" * 31 + "5"]["attribution"] == "none"
    assert got["0" * 31 + "6"]["attribution"] == "none"
    assert got["0" * 31 + "7"]["attribution"] == "none"
    assert capsys.readouterr().out.strip() == (
        "ingested 7 rows into ledger/openrouter-usage "
        "(0 refused; attributed header 1, window 2, none 4)"
    )


def test_attribution_is_recomputed_on_the_next_ingest(tmp_path):
    # mutant: keep the first pass's attribution by key -> still "none".
    store, root = tmp_path / "store", tmp_path / "broker"
    t = int(dt.datetime(2026, 9, 21, 10, 0, tzinfo=dt.timezone.utc).timestamp())
    p = _write_usage(root, [_usage(t + 30, "0" * 31 + "2")])
    assert (
        iou.main(
            ["--store", str(store), "openrouter-usage", "--root", str(root), str(p)]
        )
        == 0
    )
    assert _rows(store)["0" * 31 + "2"]["attribution"] == "none"
    _windows(
        store,
        [
            {
                "run_id": "r1",
                "key": "A",
                "wall_s": 100,
                "result_mtime": "2026-09-21T10:01:40Z",
            }
        ],
    )
    assert (
        iou.main(
            ["--store", str(store), "openrouter-usage", "--root", str(root), str(p)]
        )
        == 0
    )
    assert _rows(store)["0" * 31 + "2"]["attribution"] == "window"


def test_header_rows_with_one_half_are_not_header(tmp_path):
    # mutant: `run_id or key` -> the half-row is "header".
    store, root = tmp_path / "store", tmp_path / "broker"
    p = _write_usage(root, [_usage(1.0, "0" * 31 + "8", run_id="r1", key=None)])
    assert (
        iou.main(
            ["--store", str(store), "openrouter-usage", "--root", str(root), str(p)]
        )
        == 0
    )
    r = _rows(store)["0" * 31 + "8"]
    assert r["attribution"] == "none" and r["run_id"] is None
