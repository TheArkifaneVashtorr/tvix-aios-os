"""Evidence store unit tests (plan 2026-09-05-evidence-store, E1)."""

import datetime as dt
import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "evidence.py",
        pathlib.Path("pkgs/evidence/evidence.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))  # bundle() imports the sibling claims.py
    spec = importlib.util.spec_from_file_location("evidence", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["evidence"] = mod
    spec.loader.exec_module(mod)
    return mod, src


ev, SRC = load()
REV_A = "a" * 40
REV_B = "b" * 40


def test_append_creates_stream_with_envelope_and_mode(tmp_path):
    row = ev.append(
        str(tmp_path),
        "checks",
        {"kind": "check", "name": "lint"},
        ts="2026-09-05T12:00:00Z",
    )
    path = tmp_path / "checks.jsonl"
    assert row == {
        "v": 1,
        "ts": "2026-09-05T12:00:00Z",
        "kind": "check",
        "name": "lint",
    }
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    lines = path.read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0]) == row


def test_append_is_append_only_and_ordered(tmp_path):
    ev.append(
        str(tmp_path),
        "runs",
        {"kind": "factory-run", "n": 1},
        ts="2026-09-05T12:00:00Z",
    )
    ev.append(
        str(tmp_path),
        "runs",
        {"kind": "factory-run", "n": 2},
        ts="2026-09-05T12:00:01Z",
    )
    assert [r["n"] for r in ev.read(str(tmp_path), "runs")] == [1, 2]


def test_bad_stream_name_is_refused(tmp_path):
    with pytest.raises(ValueError):
        ev.append(str(tmp_path), "../etc", {"kind": "x"})
    with pytest.raises(ValueError):
        ev.append(str(tmp_path), "Checks", {"kind": "x"})


def test_read_missing_stream_is_empty(tmp_path):
    assert ev.read(str(tmp_path), "checks") == []


def test_read_skips_a_torn_line(tmp_path):
    ev.append(
        str(tmp_path),
        "checks",
        {"kind": "check", "name": "a"},
        ts="2026-09-05T12:00:00Z",
    )
    with open(tmp_path / "checks.jsonl", "a") as fh:
        fh.write('{"v":1,"ts":"2026-09-05T12:00:01Z","kind":"che')
    assert [r["name"] for r in ev.read(str(tmp_path), "checks")] == ["a"]


def test_latest_check_picks_newest_for_name_and_rev(tmp_path):
    s = str(tmp_path)
    ev.append(
        s,
        "checks",
        {"kind": "check", "name": "flake-check", "rev": REV_A, "ok": False},
        ts="2026-09-05T01:00:00Z",
    )
    ev.append(
        s,
        "checks",
        {"kind": "check", "name": "flake-check", "rev": REV_A, "ok": True},
        ts="2026-09-05T03:00:00Z",
    )
    ev.append(
        s,
        "checks",
        {"kind": "check", "name": "flake-check", "rev": REV_B, "ok": False},
        ts="2026-09-05T04:00:00Z",
    )
    ev.append(
        s,
        "checks",
        {"kind": "check", "name": "lint", "rev": REV_A, "ok": False},
        ts="2026-09-05T05:00:00Z",
    )
    assert ev.latest_check(s, "flake-check", REV_A)["ok"] is True
    assert ev.latest_check(s, "flake-check", REV_B)["ok"] is False
    assert ev.latest_check(s, "unit", REV_A) is None


def test_envelope_wins_over_row_v_and_ts(tmp_path):
    row = ev.append(
        str(tmp_path),
        "checks",
        {"kind": "check", "v": 99, "ts": "1970-01-01T00:00:00Z"},
        ts="2026-09-05T12:00:00Z",
    )
    assert row["v"] == 1
    assert row["ts"] == "2026-09-05T12:00:00Z"
    r = cli(
        tmp_path,
        "record",
        "checks",
        "--json",
        '{"kind":"check","v":99,"ts":"1970-01-01T00:00:00Z"}',
    )
    assert r.returncode == 0, r.stderr
    printed = json.loads(r.stdout)
    assert printed["v"] == 1
    assert printed["ts"] != "1970-01-01T00:00:00Z"


def test_latest_check_same_ts_prefers_later_row(tmp_path):
    s = str(tmp_path)
    ts = "2026-09-05T12:00:00Z"
    ev.append(
        s,
        "checks",
        {"kind": "check", "name": "flake-check", "rev": REV_A, "ok": True},
        ts=ts,
    )
    ev.append(
        s,
        "checks",
        {"kind": "check", "name": "flake-check", "rev": REV_A, "ok": False},
        ts=ts,
    )
    assert ev.latest_check(s, "flake-check", REV_A)["ok"] is False
    ev.append(
        s, "checks", {"kind": "check", "name": "lint", "rev": REV_A, "ok": False}, ts=ts
    )
    ev.append(
        s, "checks", {"kind": "check", "name": "lint", "rev": REV_A, "ok": True}, ts=ts
    )
    assert ev.latest_check(s, "lint", REV_A)["ok"] is True


def cli(tmp_path, *args):
    env = dict(os.environ, EVIDENCE_STORE=str(tmp_path))
    return subprocess.run(
        [sys.executable, str(SRC), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_cli_record_check_ok_and_fail(tmp_path):
    tail = tmp_path / "tail.txt"
    tail.write_text("last lines\n")
    r = cli(
        tmp_path,
        "record-check",
        "--name",
        "flake-check",
        "--rev",
        REV_A,
        "--ok",
        "--class",
        "nix-check",
        "--src",
        "helm-nightly",
        "--duration",
        "105",
        "--log-tail-file",
        str(tail),
    )
    assert r.returncode == 0, r.stderr
    printed = json.loads(r.stdout)
    assert (
        printed["ok"] is True
        and printed["duration_s"] == 105
        and printed["log_tail"] == "last lines\n"
    )
    r = cli(
        tmp_path,
        "record-check",
        "--name",
        "flake-check",
        "--rev",
        REV_A,
        "--fail",
        "--class",
        "nix-check",
        "--src",
        "seat-integrate",
    )
    assert r.returncode == 0 and json.loads(r.stdout)["ok"] is False
    assert [row["ok"] for row in ev.read(str(tmp_path), "checks")] == [True, False]


def test_cli_record_check_rejects_short_rev_and_unknown_class(tmp_path):
    r = cli(
        tmp_path,
        "record-check",
        "--name",
        "lint",
        "--rev",
        "abc1234",
        "--ok",
        "--class",
        "nix-check",
        "--src",
        "x",
    )
    assert r.returncode == 2 and not (tmp_path / "checks.jsonl").exists()
    r = cli(
        tmp_path,
        "record-check",
        "--name",
        "lint",
        "--rev",
        REV_A,
        "--ok",
        "--class",
        "guess",
        "--src",
        "x",
    )
    assert r.returncode == 2


def test_cli_record_requires_kind(tmp_path):
    r = cli(tmp_path, "record", "runs", "--json", '{"plan": "p"}')
    assert r.returncode == 2 and not (tmp_path / "runs.jsonl").exists()
    r = cli(
        tmp_path, "record", "runs", "--json", '{"kind": "factory-run", "plan": "p"}'
    )
    assert r.returncode == 0 and json.loads(r.stdout)["plan"] == "p"


def test_cli_latest_check_exit_codes(tmp_path):
    assert (
        cli(tmp_path, "latest-check", "--name", "lint", "--rev", REV_A).returncode == 1
    )
    cli(
        tmp_path,
        "record-check",
        "--name",
        "lint",
        "--rev",
        REV_A,
        "--ok",
        "--class",
        "nix-check",
        "--src",
        "x",
    )
    r = cli(tmp_path, "latest-check", "--name", "lint", "--rev", REV_A)
    assert r.returncode == 0 and json.loads(r.stdout)["name"] == "lint"


def test_concurrent_appends_keep_every_line_parseable(tmp_path):
    # PROXY, stated per the amendments: Linux serialises O_APPEND writes of
    # this size on a local filesystem even without the flock, so this test
    # cannot turn red by removing the lock. It proves N processes leave
    # N*M parseable rows; the lock's own effect is a recorded gap
    # (claims.toml: evidence-flock-effect-unmeasured, E2).
    # Subprocesses, not multiprocessing: Python 3.14 defaults to forkserver
    # on Linux, which pickles the target and cannot carry a function defined
    # inside a test.
    prog = (
        "import sys;"
        "sys.path.insert(0, sys.argv[1]);"
        "import evidence as ev;"
        "i = int(sys.argv[3]);"
        "[ev.append(sys.argv[2], 'runs', {'kind': 't', 'i': i, 'j': j, 'pad': 'x' * 2000}) for j in range(50)]"
    )
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", prog, str(SRC.parent), str(tmp_path), str(i)]
        )
        for i in range(8)
    ]
    for p in procs:
        assert p.wait() == 0
    rows = ev.read(str(tmp_path), "runs")
    assert len(rows) == 400
    assert {(r["i"], r["j"]) for r in rows} == {
        (i, j) for i in range(8) for j in range(50)
    }


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
    }

    def g(*a):
        return subprocess.run(
            ["git", "-C", str(repo), *a],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, **env},
        ).stdout.strip()

    g("init", "-q", "-b", "main")
    (repo / "flake.nix").write_text("{}\n")
    g("add", ".")
    g("commit", "-q", "-m", "code")
    live = g("rev-parse", "HEAD")
    (repo / "docs").mkdir()
    (repo / "docs" / "OPERATIONS.md").write_text("board\n")
    g("add", ".")
    g("commit", "-q", "-m", "docs")
    head = g("rev-parse", "HEAD")
    (repo / "flake.nix").write_text("{}  # code change\n")
    g("add", ".")
    g("commit", "-q", "-m", "code change")
    code_head = g("rev-parse", "HEAD")
    g("checkout", "-q", head)  # leave the repo at the docs-only head
    return repo, live, head, code_head


CLAIMS = """
[[claim]]
id = "a-verified-thing"
text = "x"
status = "verified"
class = "unit"
evidence = "check:unit@abc1234 t"
owner = "orchestrator"
opened = 2026-09-04

[[claim]]
id = "an-open-gap"
text = "y"
status = "gap"
class = "unmeasured"
owner = "operator"
opened = 2026-09-01
review_by = 2026-09-02
closes_by = "do y"
"""


def fake_nixos_version(tmp_path, rev):
    p = tmp_path / "nixos-version"
    p.write_text(f"#!{sys.executable}\nprint({rev!r})\n")
    p.chmod(0o755)
    return str(p)


def test_bundle_reports_live_head_docs_only_checks_gaps_and_helm(tmp_path):
    repo, live, head, _code_head = make_repo(tmp_path)
    store = tmp_path / "store"
    store.mkdir()
    ev.append(
        str(store),
        "checks",
        {
            "kind": "check",
            "name": "flake-check",
            "rev": live,
            "ok": True,
            "class": "nix-check",
            "src": "helm-nightly",
        },
        ts="2026-09-05T08:00:00Z",
    )
    ev.append(
        str(store),
        "checks",
        {
            "kind": "check",
            "name": "flake-check",
            "rev": head,
            "ok": False,
            "class": "nix-check",
            "src": "helm-nightly",
        },
        ts="2026-09-05T08:00:00Z",
    )
    ev.append(
        str(store),
        "checks",
        {
            "kind": "check",
            "name": "flake-check",
            "rev": head,
            "ok": True,
            "class": "nix-check",
            "src": "helm-nightly",
        },
        ts="2026-09-05T09:00:00Z",
    )
    for status, ts in [
        ("ok", "2026-09-05T07:00:00Z"),
        ("fail", "2026-09-05T08:00:00Z"),
        ("fail", "2026-09-05T09:00:00Z"),
    ]:
        ev.append(
            str(store),
            "helm-status",
            {"kind": "helm-status", "tiles": {"drift": status}, "reason": "change"},
            ts=ts,
        )
    claims_file = tmp_path / "claims.toml"
    claims_file.write_text(CLAIMS)
    now = dt.datetime(2026, 9, 5, 12, 0, tzinfo=dt.timezone.utc)
    b = ev.bundle(
        str(store),
        str(repo),
        str(claims_file),
        [str(repo)],
        fake_nixos_version(tmp_path, live),
        now=now,
    )
    assert (
        b["live"]["rev"] == live
        and b["head"] == head
        and b["docs_only_ahead"] is True
        and b["dirty"] is False
    )
    assert b["checks"]["flake-check"]["live"]["ok"] is True
    assert b["checks"]["flake-check"]["head"]["ok"] is True  # docs-equivalent coverage
    assert b["checks"]["flake-check"]["head"]["ts"] == "2026-09-05T09:00:00Z"
    assert (
        b["claims"]["verified"] == 1
        and b["claims"]["gaps"][0]["id"] == "an-open-gap"
        and b["claims"]["gaps"][0]["stale"] is True
    )
    assert b["helm"]["tiles"]["drift"] == {
        "status": "fail",
        "since": "2026-09-05T08:00:00Z",
    }
    assert "repo" in b["siblings"]
    md = ev.render_bundle_markdown(b)
    assert (
        "an-open-gap" in md
        and "docs-only ahead" in md
        and "flake-check" in md
        and "drift" in md
    )


def test_bundle_code_change_is_not_covered(tmp_path):
    repo, live, _head, code_head = make_repo(tmp_path)
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", code_head], check=True)
    store = tmp_path / "store"
    store.mkdir()
    ev.append(
        str(store),
        "checks",
        {
            "kind": "check",
            "name": "flake-check",
            "rev": live,
            "ok": True,
            "class": "nix-check",
            "src": "helm-nightly",
        },
        ts="2026-09-05T08:00:00Z",
    )
    b = ev.bundle(
        str(store),
        str(repo),
        str(tmp_path / "none.toml"),
        [str(repo)],
        fake_nixos_version(tmp_path, live),
        now=dt.datetime(2026, 9, 5, 12, 0, tzinfo=dt.timezone.utc),
    )
    assert b["docs_only_ahead"] is False
    assert b["checks"]["flake-check"]["head"] is None
    assert b["checks"]["flake-check"]["live"]["ok"] is True


def test_bundle_says_equal_to_live_when_head_is_live(tmp_path):
    repo, live, _head, _code_head = make_repo(tmp_path)
    subprocess.run(["git", "-C", str(repo), "checkout", "-q", live], check=True)
    b = ev.bundle(
        str(tmp_path / "store"),
        str(repo),
        str(tmp_path / "none.toml"),
        [str(repo)],
        fake_nixos_version(tmp_path, live),
        now=dt.datetime(2026, 9, 5, 12, 0, tzinfo=dt.timezone.utc),
    )
    assert b["docs_only_ahead"] is False
    md = ev.render_bundle_markdown(b)
    assert "(equal to live)" in md
    assert "docs-only" not in md


def test_bundle_strips_dirty_suffix_from_live_rev(tmp_path):
    repo, live, _head, _code_head = make_repo(tmp_path)
    b = ev.bundle(
        str(tmp_path / "store"),
        str(repo),
        str(tmp_path / "none.toml"),
        [],
        fake_nixos_version(tmp_path, live + "-dirty"),
        now=None,
    )
    assert b["live"]["rev"] == live


def test_bundle_hung_git_degrades_to_unreadable(tmp_path, monkeypatch):
    repo, live, _head, _code_head = make_repo(tmp_path)

    def boom(argv, timeout=20.0):
        raise subprocess.TimeoutExpired(argv[0], timeout)

    monkeypatch.setattr(ev, "run", boom)
    b = ev.bundle(
        str(tmp_path / "store"),
        str(repo),
        str(tmp_path / "none.toml"),
        [],
        fake_nixos_version(tmp_path, live),
        now=None,
    )
    assert b["live"]["rev"] is None
    assert b["dirty"] is None
    assert b["head"] is None


def test_bundle_without_store_or_claims_still_renders(tmp_path):
    repo, _live, _head, _code_head = make_repo(tmp_path)
    b = ev.bundle(
        str(tmp_path / "nostore"),
        str(repo),
        str(tmp_path / "none.toml"),
        [],
        fake_nixos_version(tmp_path, "unknown"),
        now=None,
    )
    assert (
        b["live"]["rev"] is None
        and b["checks"] == {}
        and b["claims"] == {"verified": 0, "parked": 0, "gaps": []}
    )
    assert "no observations" in ev.render_bundle_markdown(b)


def test_cli_bundle_markdown(tmp_path):
    repo, live, head, _code_head = make_repo(tmp_path)
    r = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--store",
            str(tmp_path / "s"),
            "bundle",
            "--markdown",
            "--repo",
            str(repo),
            "--claims",
            str(tmp_path / "none.toml"),
            "--nixos-version-bin",
            fake_nixos_version(tmp_path, live),
            "--sibling",
            str(repo),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (
        r.returncode == 0
        and r.stdout.startswith("# Evidence bundle")
        and head[:12] in r.stdout
    )


def test_cli_tasks_and_repomap_pass_through(tmp_path):
    r = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--store",
            str(tmp_path / "s"),
            "tasks",
            "--root",
            str(tmp_path),
            "--runs-dir",
            str(tmp_path / "none"),
            "brief",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0 and r.stdout.startswith("# Task brief")
    r = subprocess.run(
        [sys.executable, str(SRC), "repomap", "--root", str(tmp_path), "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1 and "docs/MAP.md is stale" in r.stderr


def test_cli_tasks_store_forwarded_to_tasks_main(tmp_path):
    # A typed task in a fixture plan (scanned via a one-repo `repos.toml`)
    # plus a store with one runs.jsonl row naming that task: its derived state
    # is "recorded" only when --store is forwarded to tasks.main.
    plan_dir = tmp_path / "docs" / "superpowers" / "plans"
    plan_dir.mkdir(parents=True)
    (plan_dir / "proof.md").write_text(
        "### T1 (code, S) — proof task\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** proof.txt\n\n"
        "**acceptance:** proof\n\n"
        "**commit subject:** proof: a typed task (test: proof)\n"
    )
    ledger = tmp_path / "docs" / "ledger"
    ledger.mkdir(parents=True)
    (ledger / "repos.toml").write_text(
        '[[repo]]\nname = "proof"\npath = "' + str(tmp_path) + '"\n'
    )
    store = tmp_path / "store"
    store.mkdir()
    (store / "runs.jsonl").write_text(
        json.dumps({"plan": str(plan_dir / "proof.md"), "tasks": [{"key": "T1"}]})
        + "\n"
    )

    def state_of_t1(extra):
        r = subprocess.run(
            [
                sys.executable,
                str(SRC),
                *extra,
                "tasks",
                "--root",
                str(tmp_path),
                "--runs-dir",
                str(tmp_path / "none"),
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0, r.stderr
        graph = json.loads(r.stdout)
        tasks = graph["repos"][0]["tasks"]
        return next(t["state"] for t in tasks if t["key"] == "T1")

    assert state_of_t1(["--store", str(store)]) == "recorded"
    assert state_of_t1([]) == "ready"
