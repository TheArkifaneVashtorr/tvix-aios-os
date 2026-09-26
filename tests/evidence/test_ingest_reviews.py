"""The reviews ingest (plan 2026-09-06-telemetry-store-1, T3).

`evidence ingest reviews [--runs-root DIR] <repo> <runs-dir>` writes one
`gate-verdict` row per `docs/reviews/*opus-review*.md` and per
`<runs-dir>/*/*.review.md` into `derived/gates`, keyed by `review_path`. Only
the block, the H1, the file name, the file hash and `git log` are read; the
body never enters the store.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
RUNS_DIR = HERE.parent / "fixtures" / "runs"  # r1/K1..K4.review.md
RUNS_ROOT = HERE.parent / "fixtures"


def _load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "ingest_reviews.py",
        pathlib.Path("pkgs/evidence/ingest_reviews.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("ingest_reviews", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ingest_reviews"] = mod
    spec.loader.exec_module(mod)
    return mod, src


ing, SRC = _load()
import evidence as ev
import tasks as tk

COMMIT_DATE = "2026-09-06T12:00:00Z"


def _git_repo(root, reviews):
    """A temp git repo whose given docs/reviews files are committed (with a
    fixed committer date) so `git log --diff-filter=A` has an add commit."""
    repo = root / "repo"
    (repo / "docs" / "reviews").mkdir(parents=True, exist_ok=True)
    for name, text in reviews.items():
        (repo / "docs" / "reviews" / name).write_text(text)

    def git(*args, env=None):
        subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            env=env,
        )

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    git("add", ".")
    env = dict(os.environ, GIT_AUTHOR_DATE=COMMIT_DATE, GIT_COMMITTER_DATE=COMMIT_DATE)
    git("commit", "-q", "-m", "add reviews", env=env)
    return repo


ORIGINAL_ADD_DATE = "2026-09-04T09:00:00Z"
READD_DATE = "2026-09-06T12:00:00Z"


def _git_repo_readd(root, name, text):
    """A temp repo whose `docs/reviews/<name>` is added, deleted, then re-added
    across three commits, so `git log --diff-filter=A` lists two add commits
    (the re-add first, the original add last)."""
    repo = root / "repo"
    (repo / "docs" / "reviews").mkdir(parents=True, exist_ok=True)

    def git(*args, env=None):
        subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            env=env,
        )

    def commit(date, msg):
        env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        git("commit", "-q", "-m", msg, env=env)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    path = repo / "docs" / "reviews" / name
    path.write_text(text)
    git("add", ".")
    commit(ORIGINAL_ADD_DATE, "add review (original)")
    path.unlink()
    git("add", "-A")
    commit("2026-09-05T09:00:00Z", "delete review")
    path.write_text(text)
    git("add", ".")
    commit(READD_DATE, "re-add review")
    return repo


def _add_shas(repo, name):
    """The add commits of `docs/reviews/<name>`, newest first."""
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "log",
            "--diff-filter=A",
            "--format=%H",
            "--",
            f"docs/reviews/{name}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()


def _run_ingest(store, repo, runs_dir, runs_root=None):
    argv = ["--store", str(store), "reviews"]
    if runs_root is not None:
        argv += ["--runs-root", str(runs_root)]
    argv += [str(repo), str(runs_dir)]
    return ing.main(argv)


def _rows(store):
    return ev.read(str(store), "derived/gates")


def _empty_runs(tmp_path):
    d = tmp_path / "runs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_round_of():
    # D7's key tokeniser (mutants: any weight -> N7c becomes round 2; strip `a`
    # -> T10a becomes first-with-a-stripped-base; treat `b` unconditionally ->
    # T10b becomes a fix round). chain_root is the graph's separate rule.
    cases = {
        "SB4b": ("fix", 2),
        "CR2r": ("replan", 2),
        "RT5rb": ("replan", 3),
        "CR2r3b": ("replan", 5),
        "OG1r2": ("replan", 3),
        "N7c": ("fix", 3),
        "BFIX4": ("first", 1),
        "T10a": ("first", 1),
        "W2-N6b": ("fix", 2),
        "T10b": ("first", 1),
    }
    for key, expected in cases.items():
        assert ing.round_of(key) == expected, key
    assert tk.chain_root("T10b") == "T10"
    assert tk.chain_root("OG1r2") == "OG1r2"


def test_block_review_row(tmp_path):
    # A block review produces a fully-populated row: identity from the H1,
    # block fields, the add commit, and the UTC commit timestamp. The review
    # file is added, deleted, then re-added, so `git log --diff-filter=A` lists
    # two add commits; `review_commit` must be the ORIGINAL add (the last line),
    # not the re-add. Mutant: any wrong producer for a field changes that field;
    # `lines[0]` -> the re-add's sha -> red.
    text = (
        "---\nplan_defect: vacuous\nreviewer: opus\nmajors: 1\nminors: null\n"
        "mutants_total: 4\nmutants_killed: 3\n---\n"
        "# Opus gate \u2014 seat run r1, task K1 \u2014 REJECTED\n\nbody\n"
    )
    name = "2026-09-06-opus-review-r1-K1.md"
    repo = _git_repo_readd(tmp_path, name, text)
    readd_sha, original_sha = _add_shas(repo, name)
    store = tmp_path / "ev"
    assert _run_ingest(store, repo, _empty_runs(tmp_path), tmp_path) == 0
    rows = _rows(store)
    assert len(rows) == 1
    row = rows[0]
    assert row["run_id"] == "r1"
    assert row["key"] == "K1"
    assert row["chain_root"] == "K1"
    assert row["round_kind"] == "first"
    assert row["round"] == 1
    assert row["reviewer"] == "opus"
    assert row["route"] == "claude"
    assert row["verdict"] == "rejected"
    assert row["majors"] == 1
    assert row["minors"] is None
    assert row["mutants_total"] == 4
    assert row["mutants_killed"] == 3
    assert row["mutants_outside_named"] is None
    assert row["plan_defect"] == "vacuous"
    assert row["plan_defect_secondary"] is None
    assert row["gate_tokens"] is None
    assert row["wall_s"] is None
    assert row["review_path"] == f"docs/reviews/{name}"
    assert row["review_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert row["review_commit"] == original_sha
    assert row["review_commit"] != readd_sha
    assert row["review_commit_ts"] == ORIGINAL_ADD_DATE


def test_blockless_and_legacy_reviews(tmp_path):
    # A blockless review defaults reviewer to unknown and the counts to None; a
    # legacy H1 derives run_id/key from the file name and verdict unknown.
    # Mutant: use the H1 only -> the legacy file yields no run_id/key.
    blockless = "# Opus gate \u2014 seat run r3, task K3 \u2014 APPROVED\n\nbody\n"
    legacy = "# Opus gate round 2 \u2014 W2-N10c (older)\n\nbody\n"
    repo = _git_repo(
        tmp_path,
        {
            "2026-09-06-opus-review-r3-K3.md": blockless,
            "2026-09-05-opus-review-r2-K2b.md": legacy,
        },
    )
    store = tmp_path / "ev"
    assert _run_ingest(store, repo, _empty_runs(tmp_path), tmp_path) == 0
    by_key = {r["key"]: r for r in _rows(store)}
    assert by_key["K3"]["reviewer"] == "unknown"
    assert by_key["K3"]["majors"] is None
    assert by_key["K3"]["minors"] is None
    assert by_key["K3"]["mutants_total"] is None
    assert by_key["K3"]["mutants_killed"] is None
    assert by_key["K2b"]["run_id"] == "r2"
    assert by_key["K2b"]["verdict"] == "unknown"
    assert by_key["K2b"]["round_kind"] == "fix"
    assert by_key["K2b"]["round"] == 2
    assert by_key["K2b"]["chain_root"] == "K2"


def test_seat_review_rows(tmp_path):
    # Each .review.md yields a deepseek/openrouter row with the last verdict
    # line mapped (rework -> rejected), and round/chain computed from the stem
    # key. Mutant: map rework to unknown; skip the round/chain computation.
    repo = _git_repo(
        tmp_path,
        {
            "2026-09-06-opus-review-r1-K1.md": "# Opus gate \u2014 seat run r1, task K1 \u2014 APPROVED\n\nbody\n"
        },
    )
    store = tmp_path / "ev"
    assert _run_ingest(store, repo, RUNS_DIR, RUNS_ROOT) == 0
    seats = {r["key"]: r for r in _rows(store) if r["route"] == "openrouter"}
    assert seats["K1"]["verdict"] == "approved"
    assert seats["K2"]["verdict"] == "rejected"
    assert seats["K3"]["verdict"] == "rejected"
    assert seats["K4"]["verdict"] == "none"
    for k in ("K1", "K2", "K3", "K4"):
        assert seats[k]["reviewer"] == "deepseek"
        assert seats[k]["route"] == "openrouter"
        assert seats[k]["model"] is None
        assert seats[k]["review_path"] == f"~/factory/runs/r1/{k}.review.md"
        assert seats[k]["round_kind"] == "first"
        assert seats[k]["round"] == 1
        assert seats[k]["chain_root"] == k


def test_runs_root_fence(tmp_path):
    # A runs-dir outside --runs-root exits 2 before any write. A repo without
    # docs/reviews also exits 2.
    repo = _git_repo(
        tmp_path,
        {
            "2026-09-06-opus-review-r1-K1.md": "# Opus gate \u2014 seat run r1, task K1 \u2014 APPROVED\n\nbody\n"
        },
    )
    store = tmp_path / "ev"
    runs_root = tmp_path / "root"
    runs_root.mkdir()
    outside = tmp_path / "outside"
    (outside / "r1").mkdir(parents=True)
    (outside / "r1" / "K1.review.md").write_text("FACTORY-REVIEW verdict=approve\n")
    assert _run_ingest(store, repo, outside, runs_root) == 2
    assert not (store / "derived" / "gates.jsonl").exists()

    no_reviews = tmp_path / "noreviews"
    no_reviews.mkdir()
    assert _run_ingest(store, no_reviews, _empty_runs(tmp_path), tmp_path) == 2


def test_ingest_idempotent(tmp_path):
    # Two runs are byte-identical; a changed review (its sha changes) replaces
    # one row. A docs review for (r1, K1) and a seat runs/r1/K1.review.md for
    # the same (r1, K1) yield two rows, one per review_path; the K1/K1b docs
    # pair yields two docs rows. Mutant: key on (run_id, key) -> the docs K1
    # row is dropped, so only one row for (r1, K1) survives.
    text1 = (
        "---\nplan_defect: vacuous\nreviewer: opus\nmajors: 1\nminors: null\n---\n"
        "# Opus gate \u2014 seat run r1, task K1 \u2014 REJECTED\n\nbody\n"
    )
    text1b = (
        "---\nplan_defect: vacuous\nreviewer: opus\nmajors: 1\nminors: 1\n---\n"
        "# Opus gate \u2014 seat run r1, task K1b \u2014 REJECTED\n\nbody\n"
    )
    repo = _git_repo(
        tmp_path,
        {
            "2026-09-06-opus-review-r1-K1.md": text1,
            "2026-09-06-opus-review-r1-K1b.md": text1b,
        },
    )
    store = tmp_path / "ev"
    assert _run_ingest(store, repo, RUNS_DIR, RUNS_ROOT) == 0
    first = (store / "derived" / "gates.jsonl").read_bytes()
    rows = _rows(store)
    k1_rows = [r for r in rows if r["run_id"] == "r1" and r["key"] == "K1"]
    assert {r["review_path"] for r in k1_rows} == {
        "docs/reviews/2026-09-06-opus-review-r1-K1.md",
        "~/factory/runs/r1/K1.review.md",
    }
    docs_paths = [
        r["review_path"] for r in rows if r["review_path"].startswith("docs/reviews/")
    ]
    assert docs_paths == [
        "docs/reviews/2026-09-06-opus-review-r1-K1.md",
        "docs/reviews/2026-09-06-opus-review-r1-K1b.md",
    ]
    assert _run_ingest(store, repo, RUNS_DIR, RUNS_ROOT) == 0
    assert (store / "derived" / "gates.jsonl").read_bytes() == first

    # Change one review body (its sha changes); one docs row is replaced.
    (repo / "docs" / "reviews" / "2026-09-06-opus-review-r1-K1.md").write_text(
        text1.replace("body", "changed body")
    )
    assert _run_ingest(store, repo, RUNS_DIR, RUNS_ROOT) == 0
    rows = _rows(store)
    k1_docs = next(
        r
        for r in rows
        if r["review_path"] == "docs/reviews/2026-09-06-opus-review-r1-K1.md"
    )
    assert (
        k1_docs["review_sha256"]
        == hashlib.sha256(text1.replace("body", "changed body").encode()).hexdigest()
    )


def test_ingest_counts_and_body_fence(tmp_path, capsys):
    # The stdout line carries the five counts; a review whose body holds a
    # secret shape still ingests and no row value equals any body line.
    block = (
        "---\nplan_defect: vacuous\nreviewer: opus\nmajors: 1\nminors: 1\n---\n"
        "# Opus gate \u2014 seat run r1, task K1 \u2014 APPROVED\n\nbody\n"
    )
    block2 = (
        "---\nplan_defect: none\nreviewer: opus\nmajors: 1\nminors: 1\n---\n"
        "# Opus gate \u2014 seat run r1, task K1b \u2014 APPROVED\n\nbody\n"
    )
    blockless = "# Opus gate \u2014 seat run r3, task K3 \u2014 APPROVED\n\nbody\n"
    legacy = "# Opus gate round 2 \u2014 W2-N10c (older)\n\nbody\n"
    repo = _git_repo(
        tmp_path,
        {
            "2026-09-06-opus-review-r1-K1.md": block,
            "2026-09-06-opus-review-r1-K1b.md": block2,
            "2026-09-06-opus-review-r3-K3.md": blockless,
            "2026-09-05-opus-review-r2-K2b.md": legacy,
        },
    )
    store = tmp_path / "ev"
    assert _run_ingest(store, repo, RUNS_DIR, RUNS_ROOT) == 0
    out = capsys.readouterr().out
    assert "docs/reviews: 4" in out
    assert "H1 parsed 3" in out
    assert "blocks 2" in out
    assert "legacy 1" in out
    assert "runs: 4" in out

    secret_repo = _git_repo(
        tmp_path / "b",
        {
            "2026-09-06-opus-review-r1-K1.md": (
                "# Opus gate \u2014 seat run r1, task K1 \u2014 APPROVED\n\n"
                "the body line holds sk-or-v1-abc but is never read\n"
            )
        },
    )
    store2 = tmp_path / "ev2"
    assert _run_ingest(store2, secret_repo, _empty_runs(tmp_path), tmp_path) == 0
    rows = _rows(store2)
    assert len(rows) == 1
    for r in rows:
        for v in r.values():
            if isinstance(v, str):
                assert "sk-or-v1-abc" not in v
