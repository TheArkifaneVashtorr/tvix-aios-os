"""The openrouter-usage ingest (plan 2026-09-08-spend-telemetry, SP8).

`evidence ingest openrouter-usage [--root DIR] <path>…` turns each of the
egress broker's `usage.jsonl` files into `ledger/openrouter-usage` rows keyed
`(instance, request_id)`, one row per line. Every path is realpath-fenced
under `--root` before any read; a torn (unterminated) last line is reported
and skipped — never refused — because the broker is still writing it.
"""

from __future__ import annotations

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
    assert "ingested 3 rows into ledger/openrouter-usage (1 refused)" in captured.out
    rows = ev.read(str(store), "ledger/openrouter-usage")
    assert len(rows) == 3
    assert all(r["src"] == "broker" for r in rows)


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
        "ingested 0 rows into ledger/openrouter-usage (0 refused)"
        in capsys.readouterr().out
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
    assert "ingested 1 rows into ledger/openrouter-usage (0 refused)" in captured.out
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
