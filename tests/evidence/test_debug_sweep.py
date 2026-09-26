"""The debug sweep's investigator half: harvest the four bug signals, fold
by signature, print the dry run and write the batch record (plan
2026-09-23-debug-sweep, DS3).

One test per named assertion, each with a discriminating fixture and named
one-line mutants (in the comments) that would turn it red. `evidence` and
`debug_sweep` are loaded the way `test_streams_policy.py` loads `streams`:
from `pkgs/evidence`, never from the host's packaged modules.
"""

from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import types

import pytest
import tomllib

HERE = pathlib.Path(__file__).resolve()


def _load(name):
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / f"{name}.py",
        pathlib.Path("pkgs") / "evidence" / f"{name}.py",
    ]
    src = next(p for p in candidates if p.exists())
    if str(src.parent) not in sys.path:
        sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location(name, src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ev = _load("evidence")
ds = _load("debug_sweep")

ROW = {  # one complete derived/tasks row (kind task-result); validates today (F15)
    "kind": "task-result",
    "run_id": "s37ev",
    "key": "EV21",
    "repo": "nixos-agent-env",
    "plan": "docs/superpowers/plans/2026-09-11-evidence.md",
    "task_kind": "code",
    "size": "S",
    "area": "evidence",
    "model": "z-ai/glm-5.3",
    "effort": "high",
    "route": "implement/code/S",
    "status": "failed",
    "exit_code": 4,
    "wall_s": 3060,
    "commits": 0,
    "commits_declared": None,
    "checks": {},
    "checks_parse": "missing",
    "derived": None,
    "checks_verified": None,
    "checks_scope": None,
    "checks_scope_files": None,
    "verify_s": None,
    "probes_verified": None,
    "head": None,
    "base": None,
    "files_changed": 0,
    "insertions": 0,
    "deletions": 0,
    "touches_extra": None,
    "touches_disclosed": None,
    "usage": {
        "in": 0,
        "out": 0,
        "cache_read": 0,
        "reasoning": 0,
        "events": 0,
        "duration_s": None,
    },
    "error_class": "no-result-line",
    "seat_unit": None,
    "result_path": "~/factory/runs/s37ev/EV21.result",
    "result_mtime": "2026-09-23T20:00:00Z",
}


def seat_row(run, key, status, error_class, wall_s=100, mtime="2026-09-23T20:00:00Z"):
    return {
        **ROW,
        "run_id": run,
        "key": key,
        "status": status,
        "error_class": error_class,
        "wall_s": wall_s,
        "result_path": f"~/factory/runs/{run}/{key}.result",
        "result_mtime": mtime,
    }


def store(tmp_path, seat_rows, check_rows=()):
    s = tmp_path / "store"
    s.mkdir()
    ev.replace_stream(str(s), "derived/tasks", list(seat_rows))
    for r in check_rows:
        r = dict(r)
        ts = r.pop("_ts", None)
        ev.append(
            str(s),
            "checks",
            {"kind": "check", "class": "nix-check", "src": "seat-integrate", **r},
            ts=ts,
        )
    return s


def repo(tmp_path, bug_rows):
    """The fixture repo: two commits (a the file commit, b an empty child on
    top) over a tree that carries the bug ledger, a one-name docs/MAP.md, an
    empty plans directory and a copy of the sandbox's own pkgs/evidence —
    F11's shape, the minimum `tasks.py check --draft` accepts on a clone."""
    r = tmp_path / "repo"
    (r / "docs" / "ledger").mkdir(parents=True)
    (r / "docs" / "diagnoses").mkdir()
    (r / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (r / "docs" / "superpowers" / "plans" / ".keep").write_text("")
    (r / "docs" / "MAP.md").write_text("## Checks\n- unit\n")
    (r / "README.md").write_text("readme\n")
    (r / "pkgs" / "evidence").mkdir(parents=True)
    for src in pathlib.Path(ds.__file__).parent.glob("*.py"):
        shutil.copy(src, r / "pkgs" / "evidence" / src.name)
    (r / "docs" / "ledger" / "bugs.toml").write_text(bug_rows)

    def git(*a):
        return subprocess.run(
            ["git", "-C", str(r), *a], check=True, capture_output=True, text=True
        )

    git("init", "-q", "-b", "main")
    git("add", "-A")
    git(
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "A",
    )
    a = git("rev-parse", "HEAD").stdout.strip()
    git(
        "-c",
        "user.email=t@t",
        "-c",
        "user.name=t",
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "B",
    )
    b = git("rev-parse", "HEAD").stdout.strip()
    return r, a, b


# BUG-fixed carries task = "" so it is the discriminating row for the status
# condition (with a task set, the row is excluded by either condition and the
# section's drop-the-status mutant could never change the harvest).
BUGS = """[[bug]]
id = "BUG-open-no-task"
found = 2026-09-20
symptom = "EV22 died with no result line"
repro = "false"
status = "open"
closing_check = ""
task = ""
evidence = "docs/x.md"

[[bug]]
id = "BUG-open-tasked"
found = 2026-09-20
symptom = "EV23 probe-missing every run"
repro = "false"
status = "open"
closing_check = ""
task = "FA30"
evidence = "docs/x.md"

[[bug]]
id = "BUG-fixed"
found = 2026-09-20
symptom = "EV24 probe-missing"
repro = "false"
status = "fixed"
closing_check = "unit"
task = ""
evidence = "docs/x.md"
"""


def inbox_line(ts, symptom, reporter="operator"):
    return json.dumps(
        {"v": 1, "ts": ts, "reporter": reporter, "symptom": symptom, "evidence": None}
    )


def write_inbox(home, lines):
    home.mkdir(parents=True, exist_ok=True)
    (home / "inbox.jsonl").write_text("".join(line + "\n" for line in lines))
    return home


def seat_item(key, occ=1, wall=0):
    return {
        "id": None,
        "kind": "seat",
        "signatures": [f"seat:probe-missing:{key}"],
        "evidence": [],
        "occurrences": occ,
        "wall_s": wall,
        "sink": None,
    }


def empty_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return home


def test_normalise_symptom_folds_numbers_and_hashes():
    # Mutant: skip the `#` replacement in normalise -> the first two differ.
    a = "EV21 died after 51 minutes in run s37ev"
    b = "EV22 died after 8 minutes in run s38ev"
    assert ds.normalise(a) == ds.normalise(b)
    assert ds.h12(ds.normalise(a)) == ds.h12(ds.normalise(b))
    assert ds.normalise("deadbeefcafe died") == ds.normalise("abcdefabcdef died")
    assert ds.normalise("the guard refused a cp") not in (
        ds.normalise(a),
        ds.normalise(b),
    )


def test_failing_line_prefers_producer_lines_then_last_line():
    # Mutant: drop the `not ok <digits>` normalisation -> the two TAP tails
    # hash differently.
    tail_a = (
        "building '.#checks'\n"
        "copying path '/nix/store/x'\n"
        "\x1b[31mnot ok 12 the case\x1b[0m\n"
        "and then more output\n"
    )
    tail_b = "building '.#checks'\nnot ok 13 the case\n"
    assert ds.failing_line(tail_a) == "not ok the case"
    assert ds.failing_line(tail_b) == "not ok the case"
    assert ds.h12(ds.failing_line(tail_a)) == ds.h12(ds.failing_line(tail_b))
    # a store path and a full rev fold inside the chosen line
    p1 = "error: build of /nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkg-1.2 failed"
    p2 = "error: build of /nix/store/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-pkg-1.2 failed"
    assert ds.failing_line(p1) == ds.failing_line(p2)
    assert ds.failing_line(p1) == "error: build of /nix/store/*-pkg-1.2 failed"
    r1 = "FAILED test_x at " + "a" * 40
    r2 = "FAILED test_x at " + "b" * 40
    assert ds.failing_line(r1) == ds.failing_line(r2) == "FAILED test_x at <rev>"
    # prose only -> the last non-empty line; nothing -> ""
    assert ds.failing_line("some prose\n\nmore prose\n") == "more prose"
    assert ds.failing_line("") == ""


def test_harvest_groups_seat_rows_by_error_class(tmp_path):
    # Mutants: group by key -> seven items; include done rows -> three items;
    # include "none" -> three items.
    r, _, _ = repo(tmp_path, "")
    s = store(
        tmp_path,
        [
            seat_row("s37ev", f"EV3{i}", "partial", "probe-missing", wall_s=10 + i)
            for i in range(1, 8)
        ]
        + [
            seat_row("s38ev", "EV40", "failed", "no-result-line", wall_s=5),
            seat_row("s39ev", "EV41", "done", "probe-missing", wall_s=99),
            seat_row("s40ev", "EV42", "failed", "none", wall_s=99),
        ],
    )
    items = ds.harvest(
        str(r),
        str(s),
        str(tmp_path / "runs"),
        str(empty_home(tmp_path)),
        "2026-09-23T00:00:00Z",
        set(),
    )
    assert len(items) == 2
    pm = next(it for it in items if "seat:probe-missing:EV31" in it["signatures"])
    assert pm["kind"] == "seat"
    assert pm["signatures"] == [f"seat:probe-missing:EV3{i}" for i in range(1, 8)]
    assert pm["occurrences"] == 7
    assert pm["wall_s"] == sum(10 + i for i in range(1, 8))
    assert len(pm["evidence"]) == 7
    assert all(e["src"] == "seat" for e in pm["evidence"])
    nr = next(it for it in items if "seat:no-result-line:EV40" in it["signatures"])
    assert nr["signatures"] == ["seat:no-result-line:EV40"]
    assert nr["occurrences"] == 1
    assert nr["wall_s"] == 5


def test_since_window_excludes_older_rows(tmp_path):
    # Mutants: drop the inbox `ts > since` filter -> two notes; drop the seat
    # `result_mtime > since` filter -> two signatures; `>=` instead of `>`
    # with the third row at exactly since -> it is harvested.
    r, _, _ = repo(tmp_path, "")
    home = write_inbox(
        tmp_path / "home",
        [
            inbox_line("2026-09-23T11:59:59Z", "one note"),
            inbox_line("2026-09-23T12:00:01Z", "another note"),
        ],
    )
    s = store(
        tmp_path,
        [
            seat_row(
                "s37ev", "EV51", "failed", "probe-missing", mtime="2026-09-23T11:59:59Z"
            ),
            seat_row(
                "s37ev", "EV52", "failed", "probe-missing", mtime="2026-09-23T12:00:00Z"
            ),
            seat_row(
                "s37ev", "EV53", "failed", "probe-missing", mtime="2026-09-23T12:00:01Z"
            ),
        ],
    )
    items = ds.harvest(
        str(r), str(s), str(tmp_path / "runs"), str(home), "2026-09-23T12:00:00Z", set()
    )
    notes = [it for it in items if it["kind"] == "note"]
    seats = [it for it in items if it["kind"] == "seat"]
    assert len(notes) == 1
    assert len(seats) == 1
    assert seats[0]["signatures"] == ["seat:probe-missing:EV53"]


def test_default_since_is_the_newest_finished_batch_or_14_days(tmp_path):
    # Mutants: take the unfinished batch's start -> wrong; 7 days -> wrong.
    now = datetime.datetime(2026, 9, 24, 12, 0, 0, tzinfo=datetime.timezone.utc)
    empty = tmp_path / "empty"
    empty.mkdir()
    assert ds.default_since(empty, now) == "2026-09-10T12:00:00Z"
    home = tmp_path / "home"
    (home / "2026-09-20T1000").mkdir(parents=True)
    (home / "2026-09-20T1000" / "batch.meta").write_text(
        "start=2026-09-20T10:00:00Z\nend=2026-09-20T11:00:00Z\n"
    )
    (home / "2026-09-22T1000").mkdir()
    (home / "2026-09-22T1000" / "batch.meta").write_text("start=2026-09-22T10:00:00Z\n")
    assert ds.default_since(home, now) == "2026-09-20T10:00:00Z"


def test_harvest_checks_take_the_newest_ancestor_row(tmp_path):
    # Mutants: take the oldest row -> `unit` is harvested; skip the ancestor
    # test -> `map` is harvested.
    r, a, b = repo(tmp_path, "")
    s = store(
        tmp_path,
        [],
        [
            {
                "name": "unit",
                "rev": a,
                "ok": False,
                "log_tail": "not ok 1 unit",
                "_ts": "2026-09-23T10:00:00Z",
            },
            {"name": "unit", "rev": b, "ok": True, "_ts": "2026-09-23T11:00:00Z"},
            {"name": "lint", "rev": a, "ok": True, "_ts": "2026-09-23T10:00:00Z"},
            {
                "name": "lint",
                "rev": b,
                "ok": False,
                "log_tail": "building\nnot ok 7 the case\n",
                "_ts": "2026-09-23T11:00:00Z",
            },
            {
                "name": "map",
                "rev": "c" * 40,
                "ok": False,
                "_ts": "2026-09-23T12:00:00Z",
            },
        ],
    )
    items = ds.harvest(
        str(r),
        str(s),
        str(tmp_path / "runs"),
        str(empty_home(tmp_path)),
        "2026-09-23T00:00:00Z",
        set(),
    )
    checks = [it for it in items if it["kind"] == "check"]
    assert len(checks) == 1
    want = "check:lint:" + hashlib.sha256(b"not ok the case").hexdigest()[:12]
    assert checks[0]["signatures"] == [want]
    assert checks[0]["occurrences"] == 1
    assert checks[0]["evidence"][0]["ref"] == f"lint@{b}"


def test_harvest_bugs_needs_open_and_no_task(tmp_path):
    # Mutants: drop the `task == ""` condition -> two items; drop the
    # `status` condition -> two items (the fixed row).
    r, _, _ = repo(tmp_path, BUGS)
    s = store(tmp_path, [])
    items = ds.harvest(
        str(r),
        str(s),
        str(tmp_path / "runs"),
        str(empty_home(tmp_path)),
        "2026-09-23T00:00:00Z",
        set(),
    )
    bugs = [it for it in items if it["kind"] == "bug"]
    assert [it["signatures"] for it in bugs] == [["bug:BUG-open-no-task"]]
    assert bugs[0]["evidence"][0]["ref"] == "BUG-open-no-task"


def test_fold_sinks_diagnosed_and_open_tasked_bug_signatures_unless_rechecked(tmp_path):
    # Mutants: ignore the diagnosis sinks -> EV21 kept; ignore recheck ->
    # three kept; substring match instead of whole word -> EV2 folds; sink
    # every open row -> the added EV22 row folds wrongly; sink fixed rows ->
    # EV24 folds.
    r, _, _ = repo(tmp_path, BUGS)
    (r / "docs" / "diagnoses" / "2026-09-23-d.md").write_text(
        '+++\n[[item]]\nid = "D1"\n'
        'signatures = ["seat:probe-missing:EV21"]\n'
        'decision = "pending"\n+++\n\nbody\n'
    )
    keys = ["EV21", "EV22", "EV23", "EV24", "EV2", "EV25"]
    sigs = [f"seat:probe-missing:{k}" for k in keys]
    sinks = ds.build_sinks(r, sigs)
    assert sinks["seat:probe-missing:EV21"] == "diagnosis:2026-09-23-d.md:D1"
    assert sinks["seat:probe-missing:EV23"] == "bug:BUG-open-tasked"
    assert "seat:probe-missing:EV24" not in sinks  # the fixed row is no sink
    assert "seat:probe-missing:EV2" not in sinks  # whole word only
    assert "seat:probe-missing:EV22" not in sinks  # open with no task
    items = [seat_item(k) for k in ["EV21", "EV23", "EV24", "EV2", "EV25"]]
    kept, folded = ds.fold(items, sinks, set())
    assert sorted(s for it in kept for s in it["signatures"]) == [
        "seat:probe-missing:EV2",
        "seat:probe-missing:EV24",
        "seat:probe-missing:EV25",
    ]
    assert set(folded) == {
        "seat:probe-missing:EV21 -> diagnosis:2026-09-23-d.md:D1",
        "seat:probe-missing:EV23 -> bug:BUG-open-tasked",
    }
    kept2, folded2 = ds.fold(items, sinks, {"seat:probe-missing:EV21"})
    assert len(kept2) == 4
    assert len(folded2) == 1
    # the added EV22 row: an open row with no task is never a sink
    kept3, folded3 = ds.fold([seat_item("EV22")], sinks, set())
    assert len(kept3) == 1
    assert folded3 == []


def test_impact_order_and_limit():
    # Mutant: sort by wall_s first -> the order changes.
    def item(occ, wall, tag):
        return {
            "id": None,
            "kind": "note",
            "signatures": [f"note:{tag}"],
            "evidence": [],
            "occurrences": occ,
            "wall_s": wall,
            "sink": None,
        }

    items = [item(7, 10, "a"), item(7, 900, "b"), item(2, 5000, "c")]
    kept, folded = ds.fold(items, {}, set())
    assert folded == []
    assert [it["signatures"][0] for it in kept] == ["note:b", "note:a", "note:c"]
    kept2, _ = ds.fold(items, {}, set(), limit=2)
    assert [it["signatures"][0] for it in kept2] == ["note:b", "note:a"]


def test_dry_run_prints_and_writes_nothing(tmp_path, capsys):
    # Mutant: open the batch on a dry run -> the directory exists.
    r, _, _ = repo(tmp_path, "")
    home = write_inbox(
        tmp_path / "home", [inbox_line("2026-09-23T12:30:00Z", "a symptom")]
    )
    s = store(tmp_path, [seat_row("s37ev", "EV61", "failed", "probe-missing")])
    rc = ds.main(
        [
            "--dry-run",
            "--since",
            "2026-09-23T12:00:00Z",
            "--home",
            str(home),
            "--store",
            str(s),
            "--repo",
            str(r),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("since:")
    assert "harvested: 2 items (1 seat, 0 check, 0 bug, 1 note)" in out
    assert sorted(p.name for p in home.iterdir()) == ["inbox.jsonl"]


def test_batch_meta_and_resume(tmp_path):
    # Mutants: write end= at open -> resume returns None; ignore the
    # collision -> the same directory is reused.
    home = tmp_path / "home"
    home.mkdir()
    items = [seat_item("EV21")]
    items[0]["signatures"].append("seat:probe-missing:EV23")
    b1 = ds.batch_open(
        home, "2026-09-23T00:00:00Z", items, ["investigate", "--dry-run"], "a" * 40
    )
    meta = (b1 / "batch.meta").read_text()
    lines = meta.splitlines()
    fields = dict(line.split("=", 1) for line in lines if not line.startswith("item="))
    assert fields["since"] == "2026-09-23T00:00:00Z"
    assert fields["head"] == "a" * 40
    assert fields["items"] == "1"
    assert fields["limit"] == "10"
    assert fields["confined"] == "1"
    assert fields["command"] == "investigate --dry-run"
    assert fields["start"].startswith("20")
    assert "end=" not in meta
    assert [line for line in lines if line.startswith("item=")] == [
        "item=item-01 seat:probe-missing:EV21 seat:probe-missing:EV23"
    ]
    b2 = ds.batch_open(home, "2026-09-23T00:00:00Z", items, ["investigate"], "a" * 40)
    assert b2.name == b1.name + "-2"
    assert ds.batch_resume(home) == b2
    ds.batch_close(b2)
    assert "end=" in (b2 / "batch.meta").read_text()
    assert ds.batch_resume(home) == b1
    ds.batch_close(b1)
    assert ds.batch_resume(home) is None


def test_limit_zero_is_a_usage_error(tmp_path, capsys):
    # Mutant: weaken the bound from < 1 to < 0 -> exit 0.
    r, _, _ = repo(tmp_path, "")
    s = store(tmp_path, [])
    rc = ds.main(
        [
            "--dry-run",
            "--limit",
            "0",
            "--home",
            str(empty_home(tmp_path)),
            "--store",
            str(s),
            "--repo",
            str(r),
        ]
    )
    assert rc == 2
    assert capsys.readouterr().err.startswith("investigate:")


def test_since_not_a_date_is_a_usage_error(capsys):
    # Mutant: drop the parse's try/except -> a traceback, exit 1.
    rc = ds.main(["--dry-run", "--since", "nope"])
    assert rc == 2
    assert capsys.readouterr().err == "investigate: --since: not a date\n"


def test_recheck_must_be_a_signature(tmp_path, capsys):
    # Mutant: skip the regex test -> exit 0.
    r, _, _ = repo(tmp_path, "")
    s = store(tmp_path, [])
    rc = ds.main(
        [
            "--dry-run",
            "--recheck",
            "gate:x",
            "--home",
            str(empty_home(tmp_path)),
            "--store",
            str(s),
            "--repo",
            str(r),
        ]
    )
    assert rc == 2
    assert (
        capsys.readouterr().err == "investigate: --recheck: not a signature: gate:x\n"
    )


def test_unreadable_store_is_exit_3(tmp_path, capsys):
    # Mutant: skip the directory test -> exit 0 with zero items.
    r, _, _ = repo(tmp_path, "")
    rc = ds.main(
        [
            "--dry-run",
            "--store",
            str(tmp_path / "absent"),
            "--home",
            str(empty_home(tmp_path)),
            "--repo",
            str(r),
        ]
    )
    assert rc == 3
    assert capsys.readouterr().err.startswith("investigate: store unreadable:")


def test_non_git_repo_is_exit_3(tmp_path, capsys):
    # Mutant: ignore rev-parse's exit -> exit 0 with zero check items.
    plain = tmp_path / "plain"
    (plain / "docs" / "ledger").mkdir(parents=True)
    (plain / "docs" / "ledger" / "bugs.toml").write_text("")
    s = store(tmp_path, [])
    rc = ds.main(
        [
            "--dry-run",
            "--home",
            str(empty_home(tmp_path)),
            "--store",
            str(s),
            "--repo",
            str(plain),
        ]
    )
    assert rc == 3
    assert capsys.readouterr().err.startswith("investigate: not a git repository:")


VALID_DIAG = {
    "symptom": "the guard refused a cp",
    "signatures": ["seat:probe-missing:EV21", "note:abc123def456"],
    "repro": "bash -c 'false'",
    "root_cause": "the guard's fallback deny",
    "evidence": [{"file": "tools/guard.sh", "line": 12, "note": "the deny"}],
    "confidence": "confirmed",
    "fix": "allow the path",
    "draft_section": "### XY1 (code, XS) — allow",
}


def test_diagnosis_validate():
    # Mutants: require an extra `title` key -> the valid object fails; drop
    # the confirmed-needs-repro check -> []; require repro for every
    # confidence -> the unknown object is refused; accept any confidence
    # string -> []; skip the regex on each signature -> [].
    assert ds.diagnosis_validate(VALID_DIAG) == []
    no_repro = {**VALID_DIAG, "repro": ""}
    assert ds.diagnosis_validate(no_repro) == ["repro: required for confirmed"]
    unknown = {**VALID_DIAG, "repro": "", "evidence": [], "confidence": "unknown"}
    assert ds.diagnosis_validate(unknown) == []
    bad_conf = {**VALID_DIAG, "confidence": "sure"}
    errs = ds.diagnosis_validate(bad_conf)
    assert len(errs) == 1
    assert errs[0].startswith("confidence:")
    bad_sig = {**VALID_DIAG, "signatures": ["seat:probe-missing:EV21", "gate:x"]}
    errs = ds.diagnosis_validate(bad_sig)
    assert len(errs) == 1
    assert errs[0].startswith("signatures:")


# The old exit-4 stub test (DS3 Interface 8) was voided by DS7 landing the
# batch loop; its main-level replacement lives in the DS7 section below.


# --- DS4: the confined runner, one Sonnet diagnosis per item ----------------
#
# The argvs are pinned by full-list equality, never by substring. The proxy
# named here: the fake claude and the fake bwrap stand in for the real binary
# and the real confinement (the evidence-unit sandbox has no user namespaces,
# Facts F14) — they pin the argv the real pair would run, and the gap (no
# mount namespace is created in the test) is the operator's §Operator step 9.

BLOB = {
    "result": "done",
    "usage": {
        "input_tokens": 120000,
        "output_tokens": 9000,
        "cache_read_input_tokens": 400000,
        "cache_creation_input_tokens": 20000,
    },
    "total_cost_usd": 1.37,
    "duration_ms": 412000,
    "num_turns": 31,
    "session_id": "ab12cd34",
}

DIAG = {
    "symptom": "the guard refused a cp",
    "signatures": ["note:abc123def456"],
    "repro": "test -f README.md",
    "root_cause": "the guard's fallback deny fires before the allow rule",
    "evidence": [{"file": "README.md", "line": None, "note": "the fixture commits it"}],
    "confidence": "confirmed",
    "fix": "allow the path before the deny",
    "draft_section": "",
}

BAD_SECTION = (
    "### ZK8 (code, XS) — the bad one\n"
    "\n"
    "**dependsOn:** none\n"
    "**touches:** pkgs/evidence/debug_sweep.py\n"
    "**acceptance:** nope\n"
    "**commit subject:** `debug: the bad one (test: nope)`\n"
)

GOOD_SECTION = (
    "### ZK9 (code, XS) — the good one\n"
    "\n"
    "**dependsOn:** none\n"
    "**touches:** pkgs/evidence/debug_sweep.py\n"
    "**acceptance:** unit\n"
    "**commit subject:** `debug: the good one (test: unit)`\n"
)

RESULT_KEYS = (
    "status",
    "confidence",
    "rung",
    "model",
    "wall_s",
    "exit_code",
    "repro_rc",
    "draft",
    "evidence_modified",
    "repo_modified",
    "confined",
    "cost_usd",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "num_turns",
    "session_id",
    "diagnosis",
)


def fake_claude(
    tmp_path,
    *,
    blob,
    diagnosis=None,
    exit_code=0,
    sleep=0,
    shell="",
    report_body="auto",
):
    """A fake `claude` (F8's shape) under tmp_path/bin: records argv, cwd and
    stdin to capture.json, runs `shell` in its own cwd (the clone), writes
    `diagnosis` to the directory after the first --add-dir (the item dir),
    sleeps, prints the blob and exits. The report pass (no --add-dir in argv):
    writes `report_body` to report-body.md in its cwd — "auto" writes one
    `## <id> — t` section per batch.meta item line, None writes nothing."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "claude"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, subprocess, sys, time\n"
        f"capture = {str(tmp_path / 'capture.json')!r}\n"
        f"blob = {blob!r}\n"
        f"diagnosis = {diagnosis!r}\n"
        f"exit_code = {exit_code!r}\n"
        f"sleep_s = {sleep!r}\n"
        f"shell = {shell!r}\n"
        f"report_body = {report_body!r}\n"
        "argv = sys.argv[1:]\n"
        "with open(capture, 'w') as fh:\n"
        "    json.dump(\n"
        "        {\n"
        "            'argv': argv,\n"
        "            'cwd': os.path.realpath(os.getcwd()),\n"
        "            'stdin': sys.stdin.read(),\n"
        "        },\n"
        "        fh,\n"
        "    )\n"
        "if shell:\n"
        "    subprocess.run(shell, shell=True)\n"
        "item_dir = None\n"
        "if '--add-dir' in argv:\n"
        "    item_dir = argv[argv.index('--add-dir') + 1]\n"
        "if item_dir is not None and diagnosis is not None:\n"
        "    with open(os.path.join(item_dir, 'diagnosis.json'), 'w') as fh:\n"
        "        json.dump(diagnosis, fh)\n"
        "if item_dir is None:\n"
        "    if report_body == 'auto':\n"
        "        parts = []\n"
        "        try:\n"
        "            meta = open('batch.meta')\n"
        "        except OSError:\n"
        "            meta = []\n"
        "        for ln in meta:\n"
        "            if ln.startswith('item='):\n"
        "                parts.append('## ' + ln[5:].split()[0] + ' — t\\n\\ntext\\n')\n"
        "        report_body = ''.join(parts)\n"
        "    if report_body is not None:\n"
        "        with open('report-body.md', 'w') as fh:\n"
        "            fh.write(report_body)\n"
        "if sleep_s:\n"
        "    time.sleep(sleep_s)\n"
        "print(json.dumps(blob))\n"
        "sys.exit(exit_code)\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def fake_bwrap(tmp_path):
    """A fake `bwrap`: appends its arguments up to `--` as one JSON array to
    bwrap.json, then execs the rest. The shebang pins the resolved bash (the
    evidence-unit sandbox has no /usr/bin/env, so `#!/usr/bin/env bash` would
    die on ENOENT there). The real mount namespace is the operator's to
    measure (F14); the test pins the argv alone."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "bwrap"
    script.write_text(
        f"#!{shutil.which('bash')}\n"
        "# fake bwrap: record args up to -- as JSON, then exec the rest\n"
        f"out={str(tmp_path / 'bwrap.json')!r}\n"
        "before=()\n"
        "after=()\n"
        "seen=0\n"
        'for arg in "$@"; do\n'
        '  if [ "$seen" = 0 ]; then\n'
        '    if [ "$arg" = "--" ]; then seen=1; else before+=("$arg"); fi\n'
        "  else\n"
        '    after+=("$arg")\n'
        "  fi\n"
        "done\n"
        'json="["\n'
        "i=0\n"
        'for arg in "${before[@]}"; do\n'
        '  if [ "$i" -gt 0 ]; then json+=", "; fi\n'
        '  json+="\\"$arg\\""\n'
        "  i=$((i+1))\n"
        "done\n"
        'json+="]"\n'
        'printf "%s\\n" "$json" >> "$out"\n'
        'exec "${after[@]}"\n'
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def note_item():
    return {
        "id": "item-01",
        "kind": "note",
        "signatures": ["note:abc123def456"],
        "evidence": [
            {
                "src": "inbox",
                "ref": "2026-09-24T10:00:00Z+operator",
                "ts": "2026-09-24T10:00:00Z",
            }
        ],
        "occurrences": 1,
        "wall_s": 0,
        "sink": None,
    }


def seat_cite_item(key="K1"):
    it = seat_item(key)
    it["id"] = "item-01"
    it["evidence"] = [
        {
            "src": "seat",
            "ref": f"~/factory/runs/s1/{key}.result",
            "ts": "2026-09-24T10:00:00Z",
        }
    ]
    return it


def case(
    tmp_path,
    monkeypatch,
    name="c1",
    *,
    item=None,
    blob=BLOB,
    diagnosis=DIAG,
    exit_code=0,
    sleep=0,
    shell="",
    bwrap="fake",
    claude=None,
    timeout_s=60,
    runs_files=(),
):
    """One item run end to end under the fakes: the fixture repo, a store, a
    runs root (with the named <run>/<KEY> result and log files when asked), a
    batch, a HOME holding .claude/, .cache/ and .config/openrouter/ but no
    .ssh, the fake claude and (unless overridden) the fake bwrap."""
    base = tmp_path / name
    base.mkdir()
    r, _, head = repo(base, "")
    store = base / "store"
    store.mkdir()
    runs = base / "runs"
    runs.mkdir()
    for stem in runs_files:
        pure = pathlib.PurePosixPath(stem)
        (runs / pure.parent).mkdir(parents=True, exist_ok=True)
        (runs / pure.parent / f"{pure.name}.result").write_text("status: failed\n")
        (runs / pure.parent / f"{pure.name}.log").write_text("a log\n")
    batch = base / "batch"
    batch.mkdir()
    home = base / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".cache").mkdir()
    (home / ".config" / "openrouter").mkdir(parents=True)
    fake = fake_claude(
        base,
        blob=blob,
        diagnosis=diagnosis,
        exit_code=exit_code,
        sleep=sleep,
        shell=shell,
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("DEBUG_SWEEP_CLAUDE", claude or str(fake))
    if bwrap == "fake":
        monkeypatch.setenv("DEBUG_SWEEP_BWRAP", str(fake_bwrap(base)))
    else:
        monkeypatch.setenv("DEBUG_SWEEP_BWRAP", bwrap)
    it = item or note_item()
    result = ds.run_item(
        batch, it, 1, "sonnet", r, runs, store, 5.0, head, timeout_s=timeout_s
    )
    return {
        "result": result,
        "batch": batch,
        "repo": r,
        "runs": runs,
        "store": store,
        "item": it,
        "head": head,
        "home": home,
        "base": base,
    }


def read_result(batch, iid, suffix=""):
    text = (pathlib.Path(batch) / f"{iid}{suffix}.result").read_text()
    return {
        ln.split(": ", 1)[0]: ln.split(": ", 1)[1]
        for ln in text.splitlines()
        if ": " in ln
    }


def test_run_claude_argv_stdin_cwd_and_blob(tmp_path, monkeypatch):
    # Mutants: pass the prompt as argv -> stdin empty; drop --allowedTools
    # Bash -> argv differs; drop --no-session-persistence -> argv differs.
    base = tmp_path / "c"
    base.mkdir()
    runs, store = base / "runs", base / "store"
    runs.mkdir()
    store.mkdir()
    item_dir, clone = base / "item", base / "clone"
    item_dir.mkdir()
    clone.mkdir()
    fake = fake_claude(base, blob=BLOB)
    monkeypatch.setenv("DEBUG_SWEEP_CLAUDE", str(fake))
    prompt = "the rung-1 prompt"
    with open(base / "log", "w") as log:
        rr = ds.run_claude(
            prompt,
            "sonnet",
            clone,
            [item_dir, runs, store],
            "Bash,Read,Edit,Write,Grep,Glob",
            5.0,
            60,
            log,
            60,
            None,
            runs=runs,
            store=store,
        )
    cap = json.loads((base / "capture.json").read_text())
    deny = (
        "Bash(git commit*) Bash(git push*) Bash(sudo*) Bash(nixos-rebuild*) "
        "Bash(systemctl*) Bash(nix-collect-garbage*) "
        f"Edit({runs}/**) Write({runs}/**) Edit({store}/**) Write({store}/**)"
    )
    assert cap["argv"] == [
        "-p",
        "--model",
        "sonnet",
        "--output-format",
        "json",
        "--permission-mode",
        "acceptEdits",
        "--permission-prompts",
        "none",
        "--allowedTools",
        "Bash",
        "--no-session-persistence",
        "--restricted",
        "--tools",
        "Bash,Read,Edit,Write,Grep,Glob",
        "--max-budget-usd",
        "5.0",
        "--max-turns",
        "60",
        "--disallowedTools",
        deny,
        "--add-dir",
        str(item_dir),
        "--add-dir",
        str(runs),
        "--add-dir",
        str(store),
    ]
    assert cap["stdin"] == prompt
    assert cap["cwd"] == os.path.realpath(clone)
    assert rr["exit_code"] == 0
    assert rr["timed_out"] is False
    assert rr["blob"] == BLOB
    assert rr["wall_s"] == 0 or rr["wall_s"] > 0
    assert rr["cost_usd"] == 1.37
    assert rr["input_tokens"] == 120000
    assert rr["output_tokens"] == 9000
    assert rr["cache_read_tokens"] == 400000
    assert rr["cache_creation_tokens"] == 20000
    assert rr["num_turns"] == 31
    assert rr["session_id"] == "ab12cd34"


def test_run_claude_is_confined_by_bwrap(tmp_path, monkeypatch):
    # Mutants: drop --ro-bind / / -> differs; move --tmpfs /tmp after the
    # binds -> differs; emit --tmpfs for the absent .ssh -> differs.
    base = tmp_path / "c"
    base.mkdir()
    r, _, _ = repo(base, "")
    runs, store = base / "runs", base / "store"
    runs.mkdir()
    store.mkdir()
    home = base / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".cache").mkdir()
    (home / ".config" / "openrouter").mkdir(parents=True)  # and no .ssh
    ws, item_dir = base / "ws", base / "item"
    ws.mkdir()
    item_dir.mkdir()
    monkeypatch.setenv("HOME", str(home))
    fake = fake_claude(base, blob=BLOB)
    monkeypatch.setenv("DEBUG_SWEEP_CLAUDE", str(fake))
    bw = fake_bwrap(base)
    monkeypatch.setenv("DEBUG_SWEEP_BWRAP", str(bw))
    confine = ds.confinement(r, runs, store, rw=[ws, item_dir])
    with open(base / "log", "w") as log:
        rr = ds.run_claude(
            "p",
            "sonnet",
            ws,
            [item_dir, runs, store],
            "Bash,Read,Edit,Write,Grep,Glob",
            5.0,
            60,
            log,
            60,
            confine,
            runs=runs,
            store=store,
        )
    assert rr["exit_code"] == 0
    # the fake records its arguments only ($0 is the bwrap path itself)
    recorded = json.loads((base / "bwrap.json").read_text())
    expected = [
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
        "--tmpfs",
        str(home / ".config" / "openrouter"),
    ]
    if pathlib.Path("/var/lib/secrets").is_dir():
        expected += ["--tmpfs", "/var/lib/secrets"]
    expected += [
        "--ro-bind",
        str(r),
        str(r),
        "--ro-bind",
        str(runs),
        str(runs),
        "--ro-bind",
        str(store),
        str(store),
        "--bind",
        str(ws),
        str(ws),
        "--bind",
        str(item_dir),
        str(item_dir),
        "--bind",
        str(home / ".claude"),
        str(home / ".claude"),
        "--bind",
        str(home / ".cache"),
        str(home / ".cache"),
        "--die-with-parent",
        "--new-session",
    ]
    assert recorded == expected
    assert confine == [str(bw)] + expected + ["--"]
    # --tmpfs /tmp precedes every --bind (F14)
    assert recorded.index("/tmp") < min(
        i for i, a in enumerate(recorded) if a == "--bind"
    )
    assert f"{home}/.ssh" not in " ".join(recorded)


def test_unconfined_switch_is_recorded(tmp_path, monkeypatch):
    # Mutant: treat "none" as a binary name -> ConfinementMissing.
    out = case(tmp_path, monkeypatch, bwrap="none")
    res = read_result(out["batch"], "item-01")
    assert res["status"] == "done"
    assert res["confined"] == "0"
    assert not (out["base"] / "bwrap.json").exists()
    assert ds.confinement(out["repo"], out["runs"], out["store"], rw=[]) is None


def test_missing_bwrap_raises_before_any_run(tmp_path, monkeypatch):
    # Mutant: fall back to unconfined -> the fake ran.
    with pytest.raises(ds.ConfinementMissing):
        case(tmp_path, monkeypatch, bwrap="/nonexistent/bwrap")
    assert not (tmp_path / "c1" / "capture.json").exists()


def test_missing_claude_binary_is_exit_127(tmp_path, monkeypatch):
    # Mutant: let FileNotFoundError propagate -> the test sees the exception.
    out = case(tmp_path, monkeypatch, bwrap="none", claude="/nonexistent/claude")
    res = read_result(out["batch"], "item-01")
    assert res["status"] == "failed"
    assert res["exit_code"] == "127"
    log = (out["batch"] / "item-01.log").read_text()
    assert "not found: /nonexistent/claude" in log


def test_prompt_rung1_phases_in_order(tmp_path):
    # Mutants: swap phases 2 and 3 in the constant -> the order fails; drop
    # the bug-note sentence -> fails.
    item = seat_cite_item()
    runs, store = tmp_path / "runs", tmp_path / "store"
    p = ds.render_prompt(item, tmp_path / "item", runs, store)
    assert (
        p.index("1. Reproduce")
        < p.index("2. Compare")
        < p.index("3. One hypothesis")
        < p.index("4. Propose")
    )
    assert "tools/debug/bug-note" in p
    assert "diagnosis.json" in p
    assert "never push" in p
    for sig in item["signatures"]:
        assert sig in p
    assert f"{runs}/s1/K1.result" in p
    assert f"{runs}/s1/K1.log" in p
    assert str(runs) in p
    assert str(store) in p


def test_run_item_done_confirmed_writes_result_diagnosis_and_usage_row(
    tmp_path, monkeypatch
):
    # Mutants: monkeypatch record_usage to raise -> no .result exists (the
    # order); drop rung from the copied diagnosis -> the file assertion fails.
    out = case(tmp_path, monkeypatch)
    batch = out["batch"]
    lines = (batch / "item-01.result").read_text().splitlines()
    assert [ln.split(":", 1)[0] for ln in lines] == list(RESULT_KEYS)
    res = read_result(batch, "item-01")
    assert res["status"] == "done"
    assert res["confidence"] == "confirmed"
    assert res["repro_rc"] == "0"
    assert res["rung"] == "1"
    assert res["model"] == "sonnet"
    assert res["confined"] == "1"
    assert res["repo_modified"] == "0"
    assert res["evidence_modified"] == "0"
    assert res["diagnosis"] == "item-01.diagnosis.json"
    assert res["cost_usd"] == "1.37"
    assert res["session_id"] == "ab12cd34"
    diag = json.loads((batch / "item-01.diagnosis.json").read_text())
    assert diag["rung"] == 1
    assert diag["model"] == "sonnet"
    rows = ev.read(str(out["store"]), "ledger/debug-usage")
    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 1.37
    assert rows[0]["signature"] == out["item"]["signatures"][0]
    assert rows[0]["batch"] == batch.name
    assert rows[0]["item"] == "item-01"

    # the order: a record_usage that raises leaves no .result behind
    def boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(ds, "record_usage", boom)
    it2 = dict(out["item"], id="item-02")
    with pytest.raises(RuntimeError):
        ds.run_item(
            batch,
            it2,
            1,
            "sonnet",
            out["repo"],
            out["runs"],
            out["store"],
            5.0,
            out["head"],
            timeout_s=60,
        )
    assert not (batch / "item-02.result").exists()


def test_clone_has_no_remote_so_a_push_cannot_reach_the_checkout(tmp_path, monkeypatch):
    # Mutant: skip remote remove origin -> the checkout gains
    # refs/heads/injected (and the item is failed).
    out = case(
        tmp_path,
        monkeypatch,
        shell="git push origin HEAD:refs/heads/injected || true",
    )
    res = read_result(out["batch"], "item-01")
    assert res["status"] == "done"
    assert res["repo_modified"] == "0"
    refs = subprocess.run(
        ["git", "-C", str(out["repo"]), "for-each-ref", "--format=%(refname)"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "refs/heads/injected" not in refs


def test_a_change_to_the_checkout_fails_the_item(tmp_path, monkeypatch):
    # Mutants: skip the before-snapshot -> 0; compare HEAD only -> the stray
    # case reads 0.
    repo1 = tmp_path / "c1" / "repo"
    out = case(
        tmp_path,
        monkeypatch,
        "c1",
        shell=(
            f"git -C '{repo1}' -c user.email=t@t -c user.name=t commit -q "
            "--allow-empty -m injected"
        ),
    )
    res = read_result(out["batch"], "item-01")
    assert res["repo_modified"] == "1"
    assert res["status"] == "failed"
    repo2 = tmp_path / "c2" / "repo"
    out2 = case(tmp_path, monkeypatch, "c2", shell=f"touch '{repo2}/stray'")
    res2 = read_result(out2["batch"], "item-01")
    assert res2["repo_modified"] == "1"
    assert res2["status"] == "failed"


def test_confirmed_is_demoted_when_the_repro_fails(tmp_path, monkeypatch):
    # Mutant: trust the model's confidence -> stays confirmed.
    out = case(tmp_path, monkeypatch, diagnosis={**DIAG, "repro": "false"})
    res = read_result(out["batch"], "item-01")
    assert res["confidence"] == "probable"
    assert res["repro_rc"] == "1"
    assert res["status"] == "done"
    copied = json.loads((out["batch"] / "item-01.diagnosis.json").read_text())
    assert copied["confidence"] == "probable"


def test_repro_runs_in_a_pristine_clone_not_the_models(tmp_path, monkeypatch):
    # Mutant: run the repro in ws -> confirmed.
    out = case(
        tmp_path,
        monkeypatch,
        diagnosis={**DIAG, "repro": "test -f marker"},
        shell="touch marker",
    )
    res = read_result(out["batch"], "item-01")
    assert res["repro_rc"] == "1"
    assert res["confidence"] == "probable"
    assert (out["batch"] / "item-01" / "ws" / "marker").is_file()


def test_missing_or_invalid_diagnosis_fails_the_item(tmp_path, monkeypatch):
    # Mutant: treat an absent file as unknown -> status: done.
    out = case(tmp_path, monkeypatch, diagnosis=None)
    res = read_result(out["batch"], "item-01")
    assert res["status"] == "failed"
    assert res["confidence"] == "none"
    assert res["diagnosis"] == "-"
    assert not (out["batch"] / "item-01.diagnosis.json").exists()
    out2 = case(
        tmp_path,
        monkeypatch,
        "c2",
        diagnosis={**DIAG, "confidence": "sure"},
    )
    res2 = read_result(out2["batch"], "item-01")
    assert res2["status"] == "failed"
    assert res2["confidence"] == "none"
    log = (out2["batch"] / "item-01.log").read_text()
    assert "confidence: must be confirmed, probable or unknown" in log


def test_evidence_modified_fails_a_seat_item_and_not_a_check_item(
    tmp_path, monkeypatch
):
    # Mutants: snapshot after the run -> 0 for the seat item; snapshot every
    # file under <runs> for every item -> the check item fails.
    seat_target = tmp_path / "c1" / "runs" / "s1" / "K1.result"
    out = case(
        tmp_path,
        monkeypatch,
        "c1",
        item=seat_cite_item(),
        runs_files=("s1/K1",),
        shell=f"printf x >> '{seat_target}'",
    )
    res = read_result(out["batch"], "item-01")
    assert res["evidence_modified"] == "1"
    assert res["status"] == "failed"
    check_target = tmp_path / "c2" / "runs" / "s1" / "K1.result"
    check_item = {
        "id": "item-01",
        "kind": "check",
        "signatures": ["check:unit:abc123def456"],
        "evidence": [{"src": "check", "ref": "unit@abc", "ts": "2026-09-24T10:00:00Z"}],
        "occurrences": 1,
        "wall_s": 0,
        "sink": None,
    }
    out2 = case(
        tmp_path,
        monkeypatch,
        "c2",
        item=check_item,
        runs_files=("s1/K1",),
        shell=f"printf x >> '{check_target}'",
    )
    res2 = read_result(out2["batch"], "item-01")
    assert res2["evidence_modified"] == "0"
    assert res2["status"] == "done"


def test_draft_check_marks_invalid_and_keeps_the_file(tmp_path, monkeypatch):
    # Mutant: invert the exit-code test -> valid for the bad section.
    out = case(
        tmp_path,
        monkeypatch,
        "c1",
        diagnosis={**DIAG, "draft_section": BAD_SECTION},
    )
    res = read_result(out["batch"], "item-01")
    assert res["draft"] == "draft-invalid"
    text = (out["batch"] / "item-01.result").read_text()
    assert "draft_reason: tasks: ZK8 acceptance nope not in docs/MAP.md" in text
    assert (out["batch"] / "item-01" / "draft.md").is_file()
    out2 = case(
        tmp_path,
        monkeypatch,
        "c2",
        diagnosis={**DIAG, "draft_section": GOOD_SECTION},
    )
    res2 = read_result(out2["batch"], "item-01")
    assert res2["draft"] == "valid"
    out3 = case(tmp_path, monkeypatch, "c3")
    res3 = read_result(out3["batch"], "item-01")
    assert res3["draft"] == "none"
    assert not (out3["batch"] / "item-01" / "draft.md").exists()


def test_timeout_and_nonzero_exit_are_recorded(tmp_path, monkeypatch):
    # Mutant: swallow the exit code -> done.
    out = case(tmp_path, monkeypatch, "c1", exit_code=3)
    res = read_result(out["batch"], "item-01")
    assert res["status"] == "failed"
    assert res["exit_code"] == "3"
    assert res["confidence"] == "none"
    out2 = case(tmp_path, monkeypatch, "c2", sleep=3, timeout_s=1)
    res2 = read_result(out2["batch"], "item-01")
    assert res2["status"] == "timeout"
    assert res2["exit_code"] == "124"
    assert res2["confidence"] == "none"


def test_usage_refusal_is_logged_not_fatal(tmp_path, monkeypatch):
    # Mutant: let StreamRefused propagate -> the item fails.
    out = case(tmp_path, monkeypatch, blob={**BLOB, "session_id": "bad id!"})
    res = read_result(out["batch"], "item-01")
    assert res["status"] == "done"
    log = (out["batch"] / "item-01.log").read_text()
    assert "usage refused:" in log
    assert ev.read(str(out["store"]), "ledger/debug-usage") == []


# --- DS7: the batch loop — three at once, Opus once, resume -----------------
#
# The batch-capable fake records one JSON line per run (argv, stdin, the
# item id and start/finish timestamps). The timestamps are the concurrency
# proxy: they stand in for the pool's own scheduling, which no in-process
# double can observe — the declared gap is timing on a loaded sandbox, so
# the bounds are generous (0.5 s of sleep, a 0.25 s window).

DIAG_PROBABLE = {**DIAG, "confidence": "probable"}
DIAG_UNKNOWN = {**DIAG, "confidence": "unknown", "repro": ""}


def fake_claude_runs(
    tmp_path,
    *,
    blob=BLOB,
    diagnosis_map=None,
    sleep=0,
    shell_map=None,
    report_body="auto",
):
    """The DS4 fake, extended for a batch: one JSON line appended per run to
    runs-capture.jsonl — argv, stdin, the item id (the first --add-dir's
    basename; an r2 directory names its parent) and start/finish timestamps —
    a per-item diagnosis map and shell map keyed by that id. The report pass
    (no --add-dir) writes its argv and stdin to report-capture.json instead
    and writes `report_body` to report-body.md in its cwd ("auto": one
    `## <id> — t` section per batch.meta item line; None: nothing)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "claude"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, subprocess, sys, time\n"
        f"capture = {str(tmp_path / 'runs-capture.jsonl')!r}\n"
        f"report_capture = {str(tmp_path / 'report-capture.json')!r}\n"
        f"blob = {blob!r}\n"
        f"diagnosis_map = {diagnosis_map!r}\n"
        f"shell_map = {shell_map!r}\n"
        f"sleep_s = {sleep!r}\n"
        f"report_body = {report_body!r}\n"
        "argv = sys.argv[1:]\n"
        "t0 = time.time()\n"
        "stdin = sys.stdin.read()\n"
        "item_dir = None\n"
        "if '--add-dir' in argv:\n"
        "    item_dir = argv[argv.index('--add-dir') + 1]\n"
        "iid = os.path.basename(item_dir) if item_dir else None\n"
        "if iid == 'r2':\n"
        "    iid = os.path.basename(os.path.dirname(item_dir))\n"
        "if shell_map and iid in shell_map:\n"
        "    subprocess.run(shell_map[iid], shell=True)\n"
        "if diagnosis_map is not None and item_dir is not None:\n"
        "    if iid in diagnosis_map:\n"
        "        with open(os.path.join(item_dir, 'diagnosis.json'), 'w') as fh:\n"
        "            json.dump(diagnosis_map[iid], fh)\n"
        "if item_dir is None:\n"
        "    if report_body == 'auto':\n"
        "        parts = []\n"
        "        try:\n"
        "            meta = open('batch.meta')\n"
        "        except OSError:\n"
        "            meta = []\n"
        "        for ln in meta:\n"
        "            if ln.startswith('item='):\n"
        "                parts.append('## ' + ln[5:].split()[0] + ' — t\\n\\ntext\\n')\n"
        "        report_body = ''.join(parts)\n"
        "    if report_body is not None:\n"
        "        with open('report-body.md', 'w') as fh:\n"
        "            fh.write(report_body)\n"
        "if sleep_s:\n"
        "    time.sleep(sleep_s)\n"
        "t1 = time.time()\n"
        "if item_dir is None:\n"
        "    with open(report_capture, 'w') as fh:\n"
        "        json.dump({'argv': argv, 'stdin': stdin}, fh)\n"
        "else:\n"
        "    with open(capture, 'a') as fh:\n"
        "        fh.write(json.dumps({'argv': argv, 'stdin': stdin, 'id': iid,\n"
        "                              't0': t0, 't1': t1}) + chr(10))\n"
        "print(json.dumps(blob))\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def note_items(n):
    return [
        {
            "id": None,
            "kind": "note",
            "signatures": [f"note:item{i:02d}aaaaaaaaaaaa"],
            "evidence": [],
            "occurrences": 1,
            "wall_s": 0,
            "sink": None,
        }
        for i in range(1, n + 1)
    ]


def batch_args(repo, runs, store, budget=5.0):
    return types.SimpleNamespace(
        budget=budget, repo=str(repo), runs=str(runs), store=str(store)
    )


def batch_setup(
    tmp_path,
    monkeypatch,
    name,
    *,
    n,
    blob=BLOB,
    diagnosis_map=None,
    sleep=0,
    shell_map=None,
    stray=None,
    bwrap="fake",
    report_body="auto",
):
    """The shared batch fixture: the fixture repo, a store, a runs root, a
    HOME with the confinement directories, the batch-capable fakes, and one
    open batch of n note items. `stray` names the item whose fake touches
    `<repo>/stray` (the checkout guard must trip on it); `report_body` is
    what the report pass's call writes as report-body.md ("auto": one
    section per item; None: nothing)."""
    base = tmp_path / name
    base.mkdir()
    r, _, head = repo(base, "")
    runs, store = base / "runs", base / "store"
    runs.mkdir()
    store.mkdir()
    home = base / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".cache").mkdir()
    (home / ".config" / "openrouter").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    if stray is not None:
        shell_map = {**(shell_map or {}), stray: f"touch '{r / 'stray'}'"}
    monkeypatch.setenv(
        "DEBUG_SWEEP_CLAUDE",
        str(
            fake_claude_runs(
                base,
                blob=blob,
                diagnosis_map=diagnosis_map,
                sleep=sleep,
                shell_map=shell_map,
                report_body=report_body,
            )
        ),
    )
    if bwrap == "fake":
        monkeypatch.setenv("DEBUG_SWEEP_BWRAP", str(fake_bwrap(base)))
    else:
        monkeypatch.setenv("DEBUG_SWEEP_BWRAP", bwrap)
    batch = ds.batch_open(
        base / "debug", "2026-09-24T00:00:00Z", note_items(n), ["investigate"], head
    )
    return batch, r, runs, store, head


def strip_end(batch):
    """Drop the end= line: the re-run simulates a batch interrupted mid-run."""
    meta = pathlib.Path(batch) / "batch.meta"
    lines = [ln for ln in meta.read_text().splitlines() if not ln.startswith("end=")]
    meta.write_text("".join(ln + "\n" for ln in lines))


def test_batch_runs_three_at_once_and_resumes(tmp_path, monkeypatch, capsys):
    # Mutants: max_workers=1 -> the third start is >= 1 s after the first;
    # ignore an existing .result -> five runs on the re-run.
    batch, r, runs, store, _ = batch_setup(
        tmp_path,
        monkeypatch,
        "b1",
        n=5,
        diagnosis_map={f"item-{i:02d}": dict(DIAG) for i in range(1, 6)},
        sleep=0.5,
    )
    rc = ds.run_batch(batch_args(r, runs, store), batch)
    assert rc == 0
    cap = tmp_path / "b1" / "runs-capture.jsonl"
    caps = [json.loads(ln) for ln in cap.read_text().splitlines()]
    assert len(caps) == 5
    caps.sort(key=lambda c: c["t0"])
    starts = [c["t0"] for c in caps]
    assert max(starts[:3]) - min(starts[:3]) <= 0.25
    assert starts[3] >= min(c["t1"] for c in caps[:3])
    # resume: two results gone -> only those two re-run, the rest skipped
    (batch / "item-02.result").unlink()
    (batch / "item-03.result").unlink()
    strip_end(batch)
    cap.unlink()
    rc2 = ds.run_batch(batch_args(r, runs, store), batch)
    assert rc2 == 0
    caps2 = [json.loads(ln) for ln in cap.read_text().splitlines()]
    assert sorted(c["id"] for c in caps2) == ["item-02", "item-03"]
    assert "skip item-01: result exists" in capsys.readouterr().out


def test_rung2_for_unknown_and_top_third_probable_only(tmp_path, monkeypatch):
    # Mutants: climb every probable -> four .r2.result files; drop the prior
    # -> the stdin assertion fails; never climb -> zero.
    dmap = {
        "item-01": DIAG_PROBABLE,  # rank 1 of six: ceil(6/3) = 2, climbs
        "item-02": DIAG_UNKNOWN,  # unknown always climbs
        "item-03": DIAG,  # confirmed never climbs
        "item-04": DIAG_PROBABLE,  # rank 4: outside the top third
        "item-05": DIAG,  # confirmed never climbs
        "item-06": DIAG_PROBABLE,  # rank 6: outside the top third
    }
    batch, r, runs, store, _ = batch_setup(
        tmp_path, monkeypatch, "b2", n=6, diagnosis_map=dmap
    )
    rc = ds.run_batch(batch_args(r, runs, store), batch)
    assert rc == 0
    assert sorted(p.name for p in batch.glob("*.r2.result")) == [
        "item-01.r2.result",
        "item-02.r2.result",
    ]
    caps = [
        json.loads(ln)
        for ln in (tmp_path / "b2" / "runs-capture.jsonl").read_text().splitlines()
    ]
    climbs = [c for c in caps if c["argv"][c["argv"].index("--model") + 1] == "opus"]
    assert sorted(c["id"] for c in climbs) == ["item-01", "item-02"]
    for c in climbs:
        assert "rung 1 could not show: " in c["stdin"]
        # rung 1's diagnosis JSON, verbatim (the copy carries rung and model)
        assert '"rung": 1' in c["stdin"]
        assert "the guard's fallback deny fires before the allow rule" in c["stdin"]


def test_prior_block_names_the_gaps():
    # Mutants: drop the repro gap -> differs; drop the exit-code gap ->
    # differs.
    unknown = {
        "repro": "",
        "root_cause": "a cause was named",
        "evidence": [],
        "confidence": "unknown",
    }
    block = ds.prior_block(unknown, "status: done\nconfidence: unknown\nrepro_rc: -\n")
    assert 'Rung 1 ended with confidence "unknown".' in block
    assert "repro_rc: -" in block  # its record, verbatim
    assert (
        "rung 1 could not show: repro (empty), evidence (none), confidence (unknown)"
        in block
    )
    probable = {
        "repro": "false",
        "root_cause": "a cause was named",
        "evidence": [{"file": "x", "line": 1, "note": "n"}],
        "confidence": "probable",
    }
    assert "rung 1 could not show: repro exited 1" in ds.prior_block(
        probable, "status: done\nrepro_rc: 1\n"
    )
    assert "rung 1 could not show: nothing named" in ds.prior_block(
        probable, "status: done\nrepro_rc: -\n"
    )


def test_missing_bwrap_refuses_the_batch(tmp_path, monkeypatch, capsys):
    # Mutant: fall back to unconfined -> the fake ran.
    batch, r, runs, store, _ = batch_setup(
        tmp_path,
        monkeypatch,
        "b4",
        n=2,
        diagnosis_map={"item-01": dict(DIAG), "item-02": dict(DIAG)},
        bwrap="/nonexistent/bwrap",
    )
    rc = ds.run_batch(batch_args(r, runs, store), batch)
    assert rc == 8
    err = capsys.readouterr().err
    assert "bwrap" in err
    assert (
        "investigate: bwrap not on PATH — the investigator runs confined or "
        "not at all (DEBUG_SWEEP_BWRAP=none to override)" in err
    )
    assert {p.name for p in batch.iterdir()} == {"batch.meta"}
    assert not (tmp_path / "b4" / "runs-capture.jsonl").exists()


def test_repo_modified_stops_the_batch(tmp_path, monkeypatch):
    # Mutant: treat repo_modified as an ordinary failure -> exit 5 and rung 2
    # ran for the unknown item.
    batch, r, runs, store, _ = batch_setup(
        tmp_path,
        monkeypatch,
        "b5",
        n=3,
        diagnosis_map={
            "item-01": DIAG_UNKNOWN,  # the rung 2 that must never start
            "item-02": DIAG,
            "item-03": DIAG,
        },
        stray="item-02",
    )
    rc = ds.run_batch(batch_args(r, runs, store), batch)
    assert rc == 7
    assert (r / "stray").is_file()  # the fake ran and tripped the guard
    assert list(batch.glob("*.r2.result")) == []
    assert "end=" in (batch / "batch.meta").read_text()


def test_interrupt_leaves_the_batch_open(tmp_path, monkeypatch):
    # Mutant: close the batch in a finally -> end= present.
    batch, r, runs, store, _ = batch_setup(
        tmp_path, monkeypatch, "b6", n=2, bwrap="none"
    )

    def boom(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(ds, "run_item", boom)
    rc = ds.run_batch(batch_args(r, runs, store), batch)
    assert rc == 130
    assert "end=" not in (batch / "batch.meta").read_text()


def test_non_dry_run_opens_or_resumes_and_closes_the_batch(
    tmp_path, monkeypatch, capsys
):
    # Mutants: return the exit-4 stub -> rc fails; open a new batch on resume
    # -> two batch directories under home.
    r, _, _ = repo(tmp_path, "")
    s = store(tmp_path, [seat_row("s37ev", "EV71", "failed", "probe-missing")])
    home = empty_home(tmp_path)
    monkeypatch.setenv("DEBUG_SWEEP_BWRAP", "none")
    monkeypatch.setenv(
        "DEBUG_SWEEP_CLAUDE", str(fake_claude(tmp_path, blob=BLOB, diagnosis=DIAG))
    )
    rc = ds.main(
        [
            "--since",
            "2026-09-23T00:00:00Z",
            "--home",
            str(home),
            "--store",
            str(s),
            "--repo",
            str(r),
        ]
    )
    assert rc == 0
    assert capsys.readouterr().out.startswith("batch: ")
    metas = list(home.glob("*/batch.meta"))
    assert len(metas) == 1
    meta = metas[0].read_text()
    assert "confined=0" in meta
    assert "end=" in meta
    batch = metas[0].parent
    res = read_result(batch, "item-01")
    assert res["status"] == "done"
    # the next run resumes the same batch, not a new one
    (batch / "item-01.result").unlink()
    strip_end(batch)
    rc2 = ds.main(
        [
            "--since",
            "2026-09-23T00:00:00Z",
            "--home",
            str(home),
            "--store",
            str(s),
            "--repo",
            str(r),
        ]
    )
    assert rc2 == 0
    err2 = capsys.readouterr().err
    assert f"resume {batch.name}" in err2
    assert len(list(home.glob("*/batch.meta"))) == 1
    assert read_result(batch, "item-01")["status"] == "done"
    assert "end=" in (batch / "batch.meta").read_text()


# --- DS5: the batch report — one Opus pass, the script's front matter -------
#
# The report pass's fake is the batch-capable fake in report mode (no
# --add-dir): it stands in for the real `claude -p --model opus` the way the
# item fakes stand in for the diagnosis runs — same argv shape, no model; the
# gap (no Opus judgement is exercised) is §Operator step 6's to measure.

BODY = (
    "## item-01 — the guard refuses a cp\n"
    "\n"
    "The fallback deny fires before the allow rule (item-01.diagnosis.json).\n"
    "\n"
    "merged: item-02\n"
    "\n"
    "## item-02 — the same deny, one cause\n"
    "\n"
    "Merged into item-01 above (item-01.diagnosis.json).\n"
)

BAD_BODY = (  # item-02's heading is missing -> exactly one defect
    "## item-01 — the guard refuses a cp\n"
    "\n"
    "The fallback deny fires before the allow rule (item-01.diagnosis.json).\n"
)


def result_text(**over):
    """One .result file's text: the 19 keys in order, overridable."""
    fields = {
        "status": "done",
        "confidence": "confirmed",
        "rung": 1,
        "model": "sonnet",
        "wall_s": 412,
        "exit_code": 0,
        "repro_rc": 0,
        "draft": "none",
        "evidence_modified": 0,
        "repo_modified": 0,
        "confined": 1,
        "cost_usd": 1.37,
        "input_tokens": 120000,
        "output_tokens": 9000,
        "cache_read_tokens": 400000,
        "cache_creation_tokens": 20000,
        "num_turns": 31,
        "session_id": "ab12cd34",
        "diagnosis": "item-01.diagnosis.json",
    }
    fields.update(over)
    return "".join(f"{k}: {fields[k]}\n" for k in RESULT_KEYS)


def report_batch(tmp_path, name="2026-09-24T0900"):
    """A finished two-item batch on disk: batch.meta (the seven fields, end=
    included), item-01's .result and .r2.result, item-02's .result, and the
    diagnosis copies a body may cite."""
    batch = tmp_path / name
    batch.mkdir()
    (batch / "batch.meta").write_text(
        "start=2026-09-24T09:00:00Z\n"
        "since=2026-09-23T00:00:00Z\n"
        f"head={'a' * 40}\n"
        "items=2\n"
        "limit=10\n"
        "confined=1\n"
        "command=investigate\n"
        "item=item-01 seat:probe-missing:EV21 seat:probe-missing:EV22\n"
        "item=item-02 note:abc123def456\n"
        "end=2026-09-24T10:00:00Z\n"
    )
    (batch / "item-01.result").write_text(result_text())
    (batch / "item-01.r2.result").write_text(
        result_text(
            rung=2,
            model="opus",
            confidence="probable",
            wall_s=300,
            diagnosis="item-01.r2.diagnosis.json",
        )
    )
    (batch / "item-02.result").write_text(
        result_text(
            status="done",
            confidence="unknown",
            cost_usd="-",
            wall_s=100,
            diagnosis="item-02.diagnosis.json",
        )
    )
    for diag_name in (
        "item-01.diagnosis.json",
        "item-01.r2.diagnosis.json",
        "item-02.diagnosis.json",
    ):
        (batch / diag_name).write_text("{}\n")
    return batch


def git_status(repo):
    return sorted(
        subprocess.run(
            ["git", "-C", str(repo), "status", "--short", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )


def front_matter_toml(text: str) -> dict:
    lines = text.splitlines()
    assert lines[0] == "+++"
    return tomllib.loads("\n".join(lines[1 : lines.index("+++", 1)]))


def test_front_matter_parses_and_lists_items_in_impact_order(tmp_path):
    # Mutants: sum only rung 1 -> cost_usd 1.37; write decision = "launch" ->
    # the equality fails; omit confined -> KeyError.
    fm = ds.front_matter(report_batch(tmp_path))
    data = front_matter_toml(fm)
    assert fm.startswith("+++\n")
    assert data["batch"] == "2026-09-24T0900"
    assert data["start"] == "2026-09-24T09:00:00Z"
    assert data["end"] == "2026-09-24T10:00:00Z"
    assert data["since"] == "2026-09-23T00:00:00Z"
    assert data["head"] == "a" * 40
    assert data["limit"] == 10
    assert data["confined"] is True
    assert [it["id"] for it in data["item"]] == ["item-01", "item-02"]
    item0 = data["item"][0]
    assert item0["signatures"] == [
        "seat:probe-missing:EV21",
        "seat:probe-missing:EV22",
    ]
    assert item0["confidence"] == "probable"
    assert item0["rung"] == 2
    assert item0["status"] == "done"
    assert item0["occurrences"] == 2  # the signature count (declared proxy)
    assert item0["wall_s"] == 712  # the rungs' wall times, summed
    assert item0["cost_usd"] == 2.74  # 1.37 x 2, the sum over rungs
    assert item0["diagnosis"] == "item-01.r2.diagnosis.json"  # highest rung
    assert item0["merged_into"] == ""
    assert item0["decision"] == "pending"
    item1 = data["item"][1]
    assert item1["rung"] == 1
    assert item1["confidence"] == "unknown"
    assert item1["cost_usd"] == 0.0  # unknown -> 0.0
    assert item1["diagnosis"] == "item-02.diagnosis.json"
    assert item1["decision"] == "pending"


def test_body_check_finds_missing_heading_bad_citation_and_stray_section(tmp_path):
    # Mutants: drop the file-exists test -> two messages; drop the heading
    # count -> two; drop the stray-id rule -> two.
    batch = tmp_path / "b"
    batch.mkdir()
    (batch / "item-01.diagnosis.json").write_text("{}\n")
    body = (
        "## item-01 — the guard refuses a cp\n"
        "\n"
        "The fallback deny fires before the allow rule (item-01.diagnosis.json).\n"
        "\n"
        "A citation of nothing (nope.diagnosis.json).\n"
        "\n"
        "## item-09 — x\n"
        "\n"
        "A section for an id the batch does not hold.\n"
    )
    errs = ds.body_check(batch, body, ["item-01", "item-02"])
    assert len(errs) == 3
    assert "item-02: no section" in errs
    assert "nope.diagnosis.json: not a file in the batch" in errs
    assert "item-09: not in the batch" in errs
    assert (
        ds.body_check(
            batch,
            "## item-01 — t\n\none (item-01.diagnosis.json)\n\n## item-02 — t\n\ntwo\n",
            ["item-01", "item-02"],
        )
        == []
    )


def test_write_report_copies_once_and_names_a_second_file_for_a_second_batch(
    tmp_path, capsys
):
    # Mutants: overwrite instead of suffixing -> the first file's content
    # changes; copy before the body check -> the invalid case below writes
    # into the repo.
    r, _, _ = repo(tmp_path, "")
    b1 = report_batch(tmp_path, "2026-09-24T0900")
    (b1 / "report-body.md").write_text(BODY)
    p = ds.write_report(b1, r)
    assert p is not None
    dest = r / "docs" / "diagnoses" / "2026-09-24-batch.md"
    assert dest.is_file()
    text = dest.read_text()
    assert text == (b1 / "report.md").read_text()
    assert text.startswith("+++\n")
    assert "## Decisions" in text
    assert (
        'item-01: pending — edit decision = "pending" in the front matter '
        "to launch, hold or drop" in text
    )
    assert git_status(r) == ["?? docs/diagnoses/2026-09-24-batch.md"]
    assert capsys.readouterr().out == "report: docs/diagnoses/2026-09-24-batch.md\n"
    # a second batch the same day names a second file; the first is untouched
    first = dest.read_text()
    b2 = report_batch(tmp_path, "2026-09-24T1000")
    (b2 / "report-body.md").write_text(BODY)
    p2 = ds.write_report(b2, r)
    assert p2 is not None
    assert (r / "docs" / "diagnoses" / "2026-09-24-batch-2.md").is_file()
    assert dest.read_text() == first


def test_invalid_body_writes_nothing_into_the_repo_and_exits_6(tmp_path, monkeypatch):
    # Mutant: return the path anyway -> the repo has the file.
    r, _, _ = repo(tmp_path, "")
    b = report_batch(tmp_path, "2026-09-24T1100")
    (b / "report-body.md").write_text(BAD_BODY)
    assert ds.write_report(b, r) is None
    assert (b / "report.log").read_text() == "item-02: no section\n"
    assert (
        (b / "report.md")
        .read_text()
        .startswith("<!-- report-invalid: 1 defects, see report.log -->")
    )
    assert git_status(r) == []
    # through the batch loop: the report pass's body fails the check -> exit 6
    batch, r2, runs, store, _ = batch_setup(
        tmp_path,
        monkeypatch,
        "ib",
        n=2,
        diagnosis_map={"item-01": dict(DIAG), "item-02": dict(DIAG)},
        report_body=BAD_BODY,
    )
    rc = ds.run_batch(batch_args(r2, runs, store), batch)
    assert rc == 6
    assert (batch / "report.log").read_text() == "item-02: no section\n"
    assert (
        (batch / "report.md")
        .read_text()
        .startswith("<!-- report-invalid: 1 defects, see report.log -->")
    )
    assert git_status(r2) == []


def test_missing_body_is_reported_not_crashed(tmp_path, monkeypatch):
    # Mutant: open the body without the existence test -> FileNotFoundError
    # propagates.
    r, _, _ = repo(tmp_path, "")
    b = report_batch(tmp_path, "2026-09-24T1200")
    assert ds.write_report(b, r) is None
    assert (b / "report.log").read_text() == "report-body.md: not written\n"
    assert (
        (b / "report.md")
        .read_text()
        .startswith("<!-- report-invalid: 1 defects, see report.log -->")
    )
    assert git_status(r) == []
    # through the batch loop: the report pass writes nothing -> exit 6
    batch, r2, runs, store, _ = batch_setup(
        tmp_path,
        monkeypatch,
        "mb",
        n=1,
        diagnosis_map={"item-01": dict(DIAG)},
        report_body=None,
    )
    rc = ds.run_batch(batch_args(r2, runs, store), batch)
    assert rc == 6
    assert (batch / "report.log").read_text() == "report-body.md: not written\n"
    assert (
        (batch / "report.md")
        .read_text()
        .startswith("<!-- report-invalid: 1 defects, see report.log -->")
    )
    assert git_status(r2) == []


def test_merged_lines_fill_merged_into(tmp_path):
    # Mutant: ignore merged: -> "".
    r, _, _ = repo(tmp_path, "")
    b = report_batch(tmp_path, "2026-09-24T1300")
    (b / "report-body.md").write_text(BODY)  # merged: item-02 under item-01
    assert ds.write_report(b, r) is not None
    data = front_matter_toml((b / "report.md").read_text())
    assert data["item"][1]["merged_into"] == "item-01"
    assert data["item"][0]["merged_into"] == ""
    # the copy in the repo carries the same front matter
    data2 = front_matter_toml(
        (r / "docs" / "diagnoses" / "2026-09-24-batch.md").read_text()
    )
    assert data2["item"][1]["merged_into"] == "item-01"


def test_diagnoses_are_sinks_for_the_next_batch(tmp_path):
    # Mutant: treat only drop/hold as sinks -> the launch row is re-harvested.
    r, _, _ = repo(tmp_path, "")
    b = report_batch(tmp_path, "2026-09-24T1400")
    (b / "report-body.md").write_text(BODY)
    assert ds.write_report(b, r) is not None
    dest = r / "docs" / "diagnoses" / "2026-09-24-batch.md"
    entries = front_matter_toml(dest.read_text())["item"]
    items = [
        {
            "id": e["id"],
            "kind": "note",
            "signatures": list(e["signatures"]),
            "evidence": [],
            "occurrences": 1,
            "wall_s": 0,
            "sink": None,
        }
        for e in entries
    ]
    sigs = [s for it in items for s in it["signatures"]]
    # the operator marks the rows: item-01 drop, item-02 launch
    marked = dest.read_text().replace('decision = "pending"', 'decision = "drop"', 1)
    marked = marked.replace('decision = "pending"', 'decision = "launch"', 1)
    dest.write_text(marked)
    sinks = ds.build_sinks(r, sigs)
    assert sinks["seat:probe-missing:EV21"] == "diagnosis:2026-09-24-batch.md:item-01"
    assert sinks["note:abc123def456"] == "diagnosis:2026-09-24-batch.md:item-02"
    kept, folded = ds.fold(items, sinks, set())
    assert kept == []  # pending, launch and drop are all sinks
    assert set(folded) == {
        "seat:probe-missing:EV21 -> diagnosis:2026-09-24-batch.md:item-01",
        "seat:probe-missing:EV22 -> diagnosis:2026-09-24-batch.md:item-01",
        "note:abc123def456 -> diagnosis:2026-09-24-batch.md:item-02",
    }
