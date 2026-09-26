"""Plan-judgement ingest tests (plan 2026-09-06-planning-agent, P6).

The allowlist is the fence: a judgement file's front matter may hold only the
14 named fields, each value ≤ 200 bytes and matching its class, and the prose
below the closing fence is never read. `ingest judgements` appends one row per
(plan, revision) to the `plans` stream and refuses the rest.
"""

from __future__ import annotations

import os
import pathlib
import re
import stat
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
FIXTURES = HERE.parent / "fixtures" / "judgements"


def _evidence_src():
    for cand in (
        HERE.parents[2] / "pkgs" / "evidence" / "evidence.py",
        pathlib.Path("pkgs/evidence/evidence.py"),
    ):
        if cand.exists():
            return cand
    raise FileNotFoundError("evidence.py")


SRC = _evidence_src()
sys.path.insert(0, str(SRC.parent))

import evidence as ev
import judgements

FIELDS = [
    "plan",
    "spec",
    "author",
    "effort",
    "words",
    "tasks",
    "judges",
    "judges_dropped",
    "scores",
    "total",
    "self_score",
    "threshold",
    "decision",
    "revision",
]

SCORES = "[3,2,3,3,2,3,3,3,3,3,2,2,3,3]"


def base_fields(**over):
    f = {
        "plan": "docs/superpowers/plans/2026-09-06-helm-home.md",
        "spec": "docs/superpowers/specs/2026-09-04-helm-home-design.md",
        "author": "fable",
        "effort": "max",
        "words": "6140",
        "tasks": "9",
        "judges": "[sonnet, sonnet, opus]",
        "judges_dropped": "[]",
        "scores": SCORES,
        "total": "38",
        "self_score": "40",
        "threshold": "34",
        "decision": "dispatch",
        "revision": "0",
    }
    f.update(over)
    return f


def base_row(**over):
    """The assembled row `validate_judgement` sees: the 14 raw fields plus the
    transport fields the ingest adds before appending."""
    row = base_fields()
    row["kind"] = "plan-judgement"
    row["judged_ts"] = "2026-09-06T05:39:00Z"
    row["judgement_path"] = "docs/reviews/plan-judgements/good.md"
    row.update(over)
    return row


def git_env():
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
        "GIT_AUTHOR_DATE": "2026-09-06T05:39:00 +0000",
        "GIT_COMMITTER_DATE": "2026-09-06T05:39:00 +0000",
    }


def make_repo(tmp_path, files):
    return make_repo_files(
        tmp_path, {name: (FIXTURES / name).read_text() for name in files}
    )


def make_repo_files(tmp_path, files):
    repo = tmp_path / "repo"
    jdir = repo / "docs" / "reviews" / "plan-judgements"
    jdir.mkdir(parents=True)
    for name, content in files.items():
        (jdir / name).write_text(content)
    env = git_env()

    def g(*a):
        return subprocess.run(
            ["git", "-C", str(repo), *a],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        ).stdout.strip()

    g("init", "-q", "-b", "main")
    g("add", ".")
    g("commit", "-q", "-m", "judgements")
    # force the working-tree mtime far from the commit time, so judged_ts proves
    # the value came from git rather than the file mtime fallback.
    far = 946684800  # 2000-01-01T00:00:00Z
    for name in files:
        os.utime(jdir / name, (far, far))
    return repo


def git_added_time(repo, rel):
    return (
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "log",
                "--diff-filter=A",
                "--format=%cI",
                "--",
                rel,
            ],
            check=True,
            capture_output=True,
            text=True,
            env=git_env(),
        )
        .stdout.strip()
        .splitlines()[-1]
    )


def ingest(tmp_path, store, repo):
    return subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--store",
            str(store),
            "ingest",
            "judgements",
            str(repo),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_good_ingests_one_row_with_every_field_from_git(tmp_path):
    repo = make_repo(tmp_path, ["good.md"])
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 0, r.stderr
    assert "ingested docs/reviews/plan-judgements/good.md" in r.stdout
    rows = ev.read(str(store), "plans")
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "plan-judgement"
    assert row["plan"] == "docs/superpowers/plans/2026-09-06-helm-home.md"
    assert row["judgement_path"] == "docs/reviews/plan-judgements/good.md"
    assert row["judged_ts"] == git_added_time(
        repo, "docs/reviews/plan-judgements/good.md"
    )
    assert row["judges"] == ["sonnet", "sonnet", "opus"]
    assert row["scores"] == [3, 2, 3, 3, 2, 3, 3, 3, 3, 3, 2, 2, 3, 3]
    assert row["total"] == 38 and row["revision"] == 0 and row["words"] == 6140
    # the allowlist fence: exactly the envelope + kind + the 14 fields + the two
    # transport fields, nothing the prose smuggled in.
    assert set(row) == {
        "v",
        "ts",
        "kind",
        *FIELDS,
        "judged_ts",
        "judgement_path",
    }
    assert stat.S_IMODE((store / "plans.jsonl").stat().st_mode) == 0o640


def test_rerun_is_idempotent_and_prints_skipped(tmp_path):
    repo = make_repo(tmp_path, ["good.md"])
    store = tmp_path / "store"
    assert ingest(tmp_path, store, repo).returncode == 0
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 0, r.stderr
    assert "skipped docs/reviews/plan-judgements/good.md (present)" in r.stdout
    assert len(ev.read(str(store), "plans")) == 1


def test_same_plan_new_revision_appends_a_second_row(tmp_path):
    repo = make_repo(tmp_path, ["good.md", "second-revision.md"])
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 0, r.stderr
    rows = ev.read(str(store), "plans")
    assert sorted((row["plan"], row["revision"]) for row in rows) == [
        ("docs/superpowers/plans/2026-09-06-helm-home.md", 0),
        ("docs/superpowers/plans/2026-09-06-helm-home.md", 1),
    ]


def test_201_byte_string_is_refused_and_200_is_accepted(tmp_path):
    repo = make_repo(tmp_path, ["long-note.md"])
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 1
    assert "refused docs/reviews/plan-judgements/long-note.md:" in r.stderr
    assert "201 bytes" in r.stderr
    assert ev.read(str(store), "plans") == []
    # the fence is exclusive: exactly 200 bytes clears it (a > -> >= mutation
    # would refuse a 200-byte value here).
    errors_200 = judgements.validate_judgement(base_fields(spec="d" * 200))
    assert not any("bytes" in e for e in errors_200)
    errors_201 = judgements.validate_judgement(base_fields(spec="d" * 201))
    assert any("201 bytes" in e for e in errors_201)


def test_extra_field_is_refused_as_unknown(tmp_path):
    repo = make_repo(tmp_path, ["extra-field.md"])
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 1
    assert "unknown field errata" in r.stderr
    assert ev.read(str(store), "plans") == []


def test_bad_decision_is_refused(tmp_path):
    repo = make_repo(tmp_path, ["bad-decision.md"])
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 1
    assert "refused docs/reviews/plan-judgements/bad-decision.md:" in r.stderr
    assert ev.read(str(store), "plans") == []


def test_body_only_file_is_refused_as_no_block(tmp_path):
    repo = make_repo(tmp_path, ["body-only.md"])
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 1
    assert "no front-matter block" in r.stderr
    assert ev.read(str(store), "plans") == []


def test_every_refusal_isolates_its_reason():
    """Each row below differs from a valid row in exactly one way; the fence
    returns exactly the reason naming that class, never a second one."""
    thirteen = "[3,3,3,3,3,3,3,3,3,3,2,2,1]"  # sums to 35
    fifteen = "[3,3,3,3,3,3,3,3,3,3,3,3,3,3,3]"  # sums to 45
    cases = [
        ("unknown field", base_row(errata="text"), ["unknown field errata"]),
        (
            "missing key",
            {k: v for k, v in base_row().items() if k != "threshold"},
            ["missing threshold"],
        ),
        ("plan path", base_row(plan="not-a-path"), ["plan: invalid path"]),
        ("spec path", base_row(spec="not-a-path"), ["spec: invalid path"]),
        (
            "author",
            base_row(author="dsh:"),
            ["author: invalid (fable | hand | dsh:<model>)"],
        ),
        (
            "effort",
            base_row(effort="maybe"),
            ["effort: invalid (off|low|medium|high|xhigh|max|unknown)"],
        ),
        ("words int", base_row(words="x"), ["words: invalid integer (>= 0)"]),
        ("tasks int", base_row(tasks="-1"), ["tasks: invalid integer (>= 0)"]),
        ("revision int", base_row(revision="-1"), ["revision: invalid integer (>= 0)"]),
        ("threshold int", base_row(threshold="x"), ["threshold: invalid integer"]),
        ("total int", base_row(total="x"), ["total: invalid integer"]),
        (
            "self_score",
            base_row(self_score="43"),
            ["self_score: invalid (0-42 or null)"],
        ),
        (
            "decision",
            base_row(decision="maybe"),
            ["decision: invalid (dispatch|revise|revise-exhausted|panel-short)"],
        ),
        (
            "judges",
            base_row(judges="[sonnet, sonnet, sonnet, opus]"),
            ["judges: invalid (0-3 of sonnet|opus|deepseek|fable)"],
        ),
        (
            "judges_dropped",
            base_row(judges_dropped="[whatever]"),
            ["judges_dropped: invalid (implementer|reviewer|whole)"],
        ),
        ("scores list", base_row(scores="nope"), ["scores: invalid list"]),
        (
            "scores arity 13",
            base_row(scores=thirteen, total="35"),
            ["scores: must be exactly 14 entries (got 13)"],
        ),
        (
            "scores arity 15",
            base_row(scores=fifteen, total="45"),
            ["scores: must be exactly 14 entries (got 15)"],
        ),
        (
            "scores entries 0-3",
            base_row(scores="[3,2,3,3,2,3,3,3,3,3,2,2,3,4]"),
            ["scores: entries must be integers 0-3"],
        ),
        (
            "total vs sum",
            base_row(total="40"),
            ["total 40 does not equal scores sum 38"],
        ),
        (
            "judgement_path",
            base_row(judgement_path="docs/reviews/plan-judgements/bad name.md"),
            ["judgement_path: invalid path"],
        ),
    ]
    for label, row, expected in cases:
        errors = judgements.validate_judgement(row)
        assert errors == expected, (label, errors)


def test_scores_arity_is_isolated_from_the_sum_check(tmp_path):
    # Both fixtures sum to their own total, so the sum check accepts them and
    # only the exactly-14 count arm refuses (deleting that arm ingests both).
    repo = make_repo(tmp_path, ["thirteen-scores.md", "fifteen-scores.md"])
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 1
    assert "scores: must be exactly 14 entries (got 13)" in r.stderr
    assert "scores: must be exactly 14 entries (got 15)" in r.stderr
    assert ev.read(str(store), "plans") == []


def test_every_decision_arm_is_accepted():
    for d in ("dispatch", "revise", "revise-exhausted", "panel-short"):
        assert judgements.validate_judgement(base_fields(decision=d)) == [], d
    assert judgements.validate_judgement(base_fields(decision="maybe")) != []


def test_every_author_arm_is_accepted_and_empty_dsh_id_refused():
    for a in ("fable", "hand", "dsh:deepseek/deepseek-v4-pro-0813"):
        assert judgements.validate_judgement(base_fields(author=a)) == [], a
    # a `dsh:` prefix with an empty model id must not pass (a prefix-only regex
    # mutant would accept it).
    assert judgements.validate_judgement(base_fields(author="dsh:")) != []


def test_self_score_accepts_null():
    assert judgements.validate_judgement(base_fields(self_score="null")) == []
    assert judgements.validate_judgement(base_fields(self_score="43")) != []


def test_missing_directory_prints_no_judgements_and_exits_zero(tmp_path):
    repo = make_repo(tmp_path, ["good.md"])
    (repo / "docs" / "reviews" / "plan-judgements").rename(
        repo / "docs" / "reviews" / "elsewhere"
    )
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 0, r.stderr
    assert f"no judgements under {repo}" in r.stdout
    assert ev.read(str(store), "plans") == []


def test_judged_ts_falls_back_to_mtime_outside_git(tmp_path):
    # a plain directory (no .git) has no commit history; judged_ts is the mtime.
    repo = tmp_path / "repo"
    jdir = repo / "docs" / "reviews" / "plan-judgements"
    jdir.mkdir(parents=True)
    (jdir / "good.md").write_text((FIXTURES / "good.md").read_text())
    then = 946684800
    os.utime(jdir / "good.md", (then, then))
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 0, r.stderr
    (row,) = ev.read(str(store), "plans")
    assert row["judged_ts"] == "2000-01-01T00:00:00Z"


def test_no_free_text_key_is_interpreted():
    # the fence rejects every non-allowlisted name, not just `errata`.
    for name in ("reason", "note", "body", "prompt"):
        assert judgements.validate_judgement(base_fields(**{name: "text"})) != []


def test_plan_and_spec_refuse_dotdot_and_leading_slash():
    # A `..` segment or a leading `/` is refused for both repo-relative paths.
    for key in ("plan", "spec"):
        for bad in ("docs/../../etc/passwd", "/docs/x.md"):
            errors = judgements.validate_judgement(base_row(**{key: bad}))
            assert f"{key}: invalid path" in errors, (key, bad)


def test_dotdot_segment_fixture_is_refused(tmp_path):
    repo = make_repo(tmp_path, ["dotdot.md"])
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 1
    assert "plan: invalid path" in r.stderr
    assert ev.read(str(store), "plans") == []


def test_duplicate_key_is_refused(tmp_path):
    repo = make_repo(tmp_path, ["dup-key.md"])
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 1
    assert "duplicate key revision" in r.stderr
    assert ev.read(str(store), "plans") == []


def test_long_prose_filename_is_refused(tmp_path):
    # The filename itself is a judgement_path field; prose that long must be
    # refused by the row-level fence, never stored verbatim.
    name = (
        "the operator said the broker leaked and the reason is that the seat "
        "guard interpolated the agent supplied file path into a reason string "
        "which is exactly the free text this fence exists to keep out of the "
        "telemetry store forever"
    )
    repo = make_repo_files(tmp_path, {name + ".md": (FIXTURES / "good.md").read_text()})
    store = tmp_path / "store"
    r = ingest(tmp_path, store, repo)
    assert r.returncode == 1
    assert "refused" in r.stderr
    assert "judgement_path" in r.stderr
    assert ev.read(str(store), "plans") == []


def test_append_is_only_after_the_row_level_validate():
    # The writer must run once, and only after `validate_judgement` has seen the
    # assembled row (so judgement_path and judged_ts cannot bypass the fence).
    src = pathlib.Path(judgements.__file__).read_text()
    assert src.count("evidence.append(") == 1
    validate = re.search(r"= validate_judgement\(row\)", src)
    append = re.search(r"evidence\.append\(", src)
    assert validate is not None, "row-level validate_judgement(row) call missing"
    assert append is not None, "evidence.append writer missing"
    assert validate.start() < append.start()
