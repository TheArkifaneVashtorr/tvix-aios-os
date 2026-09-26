"""Helm API record routes (HM6): the patch queue and task queue documents.

GET /v1/patches — docs/ledger/patches.toml read at cfg["repo"]'s HEAD, each row
  joined with the running generation: carried_by_next_switch is true when a row
  has no landed_generation or landed after the running generation (a null
  generation is carried, never hidden — U4's fallback).
GET /v1/tasks   — python3 pkgs/evidence/tasks.py --root <repo> json, passed
  through with a top-level "source" marker (Helm never parses plan prose).

These tests load api_record.py by path (the A3 pattern) and drive its handlers
directly with an injected runner (cfg["_run"]) and readlink (cfg["_readlink"]):
no real git, tasks.py or /nix/var/nix/profiles/system is touched, so the
helm-unit check needs no git in its sandbox. The fixture "commits" a three-row
patches.toml and the fake runner stands in for git show/rev-parse; an
uncommitted fourth row is written to disk only where the HEAD-vs-worktree
mutant must be killed.

The mutant column in the plan is reproduced as test names; each test is written
to fail on exactly the mutation its name targets (M1..M8 plus the three-row
negative control).

HM6c: the fake git runner answers only for the exact committed blob
HEAD:docs/ledger/patches.toml and returns rc 128 with git's real "does not
exist in 'HEAD'" stderr for any other path, so M4 (a worktree read) serves an
empty patch list and dies inside the git-less helm-unit sandbox rather than
surviving behind the devShell-only git fixture. Four more tests pin the gate's
four minors: the landed == running boundary, interface 3's catch-all arm, the
top-level repo key (M8), and the missing-ledger discriminator on git's real
stderr text.
"""

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()
SRC_DIR = HERE.parents[2] / "pkgs" / "helm"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_SPEC = importlib.util.spec_from_file_location("api_record", SRC_DIR / "api_record.py")
api_record = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(api_record)

# The committed ledger: three rows — landed at 54 (below the running 55), at 56
# (above), and a third with no landed_generation at all.
COMMITTED_TOML = """\
[[patch]]
file = "patches/dsh/0001-one.patch"
package = "dsh"
landed_generation = 54

[[patch]]
file = "patches/dsh/0002-two.patch"
package = "dsh"
landed_generation = 56

[[patch]]
file = "patches/dsh/0003-three.patch"
package = "dsh"
"""

FOURTH_ROW = """
[[patch]]
file = "patches/dsh/0004-four.patch"
package = "dsh"
"""

TASKS_JSON = json.dumps({"generated": "x", "repos": [], "task_status": []})


def handler_for(path):
    for method, pattern, handler in api_record.routes():
        if pattern == path:
            return handler
    raise AssertionError(f"no route {path}")


def cp(argv, rc=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, rc, stdout, stderr)


def make_run(
    committed=COMMITTED_TOML, tasks=TASKS_JSON, git_rc=0, tasks_rc=0, head="deadbeef"
):
    """A fake runner standing in for git show/rev-parse and tasks.py.

    Returns (run, calls): run records every argv it is handed, so a mutant that
    reads prose directly leaves calls empty (M5). git show answers only for the
    exact committed blob HEAD:docs/ledger/patches.toml; any other path is rc
    128 with git's "does not exist in 'HEAD'" stderr, so the worktree-read
    mutant (M4) serves an empty patch list inside the git-less helm-unit
    sandbox."""
    calls = []

    def _run(argv, **kw):
        calls.append(list(argv))
        if argv[:2] == ["git", "-C"] and "rev-parse" in argv:
            return cp(argv, git_rc, head + "\n", "")
        if argv[:2] == ["git", "-C"] and "show" in argv:
            if argv[-1] != "HEAD:docs/ledger/patches.toml":
                return cp(
                    argv,
                    128,
                    "",
                    "fatal: path 'docs/ledger/patches.toml' does not exist in 'HEAD'",
                )
            if git_rc:
                return cp(argv, git_rc, "", "fatal: path not found")
            return cp(argv, 0, committed, "")
        if argv[:1] == ["python3"] and argv[1].endswith("pkgs/evidence/tasks.py"):
            if tasks_rc:
                return cp(argv, tasks_rc, "", "boom")
            return cp(argv, 0, tasks, "")
        return cp(argv, 0, "", "")

    return _run, calls


def make_cfg(repo, run, readlink="system-55-link"):
    """A config with only the top-level repo and the injected seams; the
    running generation is 55."""
    return {
        "repo": str(repo),
        "_run": run,
        "_readlink": lambda path: readlink,
    }


# ---------------------------------------------------------------------------
# route table (M6: /v1/tasks dropped from routes())
# ---------------------------------------------------------------------------


def test_record_routes_registered():
    routes = {(m, p) for m, p, _ in api_record.routes()}
    assert routes == {("GET", "/v1/patches"), ("GET", "/v1/tasks")}


# ---------------------------------------------------------------------------
# the patch queue
# ---------------------------------------------------------------------------


def test_patches_read_at_head_not_worktree(tmp_path):
    # HEAD carries three rows; an uncommitted fourth row sits on disk. Reading
    # the worktree would see four; reading HEAD (git show) sees three.
    (tmp_path / "docs" / "ledger").mkdir(parents=True)
    (tmp_path / "docs" / "ledger" / "patches.toml").write_text(
        COMMITTED_TOML + FOURTH_ROW
    )
    run, _ = make_run(committed=COMMITTED_TOML)
    cfg = make_cfg(tmp_path, run)
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert len(body["patches"]) == 3


def test_null_generation_is_carried(tmp_path):
    run, _ = make_run()
    cfg = make_cfg(tmp_path, run)
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    patches = body["patches"]
    assert patches[2]["landed_generation"] is None
    assert patches[2]["carried_by_next_switch"] is True


def test_carried_iff_landed_after_running(tmp_path):
    run, _ = make_run()
    cfg = make_cfg(tmp_path, run)
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    patches = body["patches"]
    assert patches[0]["landed_generation"] == 54
    assert patches[0]["carried_by_next_switch"] is False
    assert patches[1]["landed_generation"] == 56
    assert patches[1]["carried_by_next_switch"] is True


def test_missing_ledger_is_empty_with_marker(tmp_path):
    run, _ = make_run(git_rc=1)
    cfg = make_cfg(tmp_path, run)
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert body["patches"] == []
    assert body["missing"] == "docs/ledger/patches.toml"


def test_repo_is_top_level_key(tmp_path):
    # The repo is read from the top-level cfg["repo"] key, never from
    # cfg["control"] (M8). A top-level repo serves the committed document; a
    # mutant that reads cfg["control"]["repo"] KeyErrors into the interface-3
    # error body and fails this document assertion instead of degrading.
    run, _ = make_run()
    cfg = make_cfg(tmp_path, run)
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert "error" not in body
    assert len(body["patches"]) == 3


def test_repo_under_control_is_error_body(tmp_path):
    # A repo nested under cfg["control"] is not the top-level repo; reading the
    # top-level key KeyErrors into the interface-3 error body, never a 500.
    run, _ = make_run()
    cfg = {
        "control": {"repo": str(tmp_path)},
        "_run": run,
        "_readlink": lambda p: "system-55-link",
    }
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert body == {"error": "KeyError: 'repo'"}


# ---------------------------------------------------------------------------
# the task queue
# ---------------------------------------------------------------------------


def test_tasks_passes_through_json(tmp_path):
    run, calls = make_run()
    cfg = make_cfg(tmp_path, run)
    status, body = handler_for("/v1/tasks")(cfg, None)
    assert status == 200
    assert calls, "the tasks.py runner must be called (never read prose directly)"
    argv = calls[0]
    assert argv[0] == "python3"
    assert argv[1] == os.path.join(str(tmp_path), "pkgs", "evidence", "tasks.py")
    assert body["generated"] == "x"
    assert body["repos"] == []
    assert body["task_status"] == []
    assert body["source"] == "pkgs/evidence/tasks.py"


def test_tasks_subprocess_failure_degrades_to_200(tmp_path):
    run, _ = make_run(tasks_rc=1)
    cfg = make_cfg(tmp_path, run)
    status, body = handler_for("/v1/tasks")(cfg, None)
    assert status == 200
    assert "tasks.py" in body["error"]


# ---------------------------------------------------------------------------
# negative control: the three-row queue computes carried, never defaults
# ---------------------------------------------------------------------------


def test_patch_queue_round_trips(tmp_path):
    run, _ = make_run()
    cfg = make_cfg(tmp_path, run)  # running generation 55
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert body["running_generation"] == 55
    assert body["head"] == "deadbeef"
    carried = [p["carried_by_next_switch"] for p in body["patches"]]
    assert carried == [False, True, True]


# ---------------------------------------------------------------------------
# the fix round (HM6b): null running generation, absolute producer path, the
# error arm, a real git fixture for HEAD-vs-worktree, and the executor seam
# ---------------------------------------------------------------------------


def test_patches_null_running(tmp_path):
    # A readlink that raises OSError -> running_generation None. A null running
    # generation must not crash _carried: a row landed at 54 is not carried
    # (it is below every generation), an unlanded row is carried.
    run, _ = make_run()
    cfg = make_cfg(tmp_path, run)

    def boom(path):
        raise OSError("unreadable profile")

    cfg["_readlink"] = boom
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert body["running_generation"] is None
    patches = body["patches"]
    assert patches[0]["landed_generation"] == 54
    assert patches[0]["carried_by_next_switch"] is False
    assert patches[2]["landed_generation"] is None
    assert patches[2]["carried_by_next_switch"] is True


def test_tasks_argv_absolute_and_cwd(tmp_path):
    # The producer must be addressed by an absolute path joined to repo, and the
    # runner handed cwd=repo, so a systemd service whose cwd is / still reaches
    # pkgs/evidence/tasks.py (MAJOR-2).
    seen = {}

    def _run(argv, **kw):
        seen["argv"] = list(argv)
        seen["cwd"] = kw.get("cwd")
        return cp(argv, 0, TASKS_JSON, "")

    cfg = {"repo": str(tmp_path), "_run": _run}
    status, _ = handler_for("/v1/tasks")(cfg, None)
    assert status == 200
    assert seen["argv"][0] == "python3"
    assert seen["argv"][1] == os.path.join(
        str(tmp_path), "pkgs", "evidence", "tasks.py"
    )
    assert seen["cwd"] == str(tmp_path)


def test_patches_git_show_error_arm(tmp_path):
    # A git show failure whose stderr does NOT name a missing path is an error,
    # not a missing ledger (MINOR-2).
    def _run(argv, **kw):
        if argv[:2] == ["git", "-C"] and "show" in argv:
            return cp(argv, 1, "", "fatal: corrupt object")
        return cp(argv, 0, "", "")

    cfg = {"repo": str(tmp_path), "_run": _run, "_readlink": lambda p: "system-55-link"}
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert body == {"error": "git show HEAD:docs/ledger/patches.toml"}


def test_patches_rev_parse_error(tmp_path):
    # A failing git rev-parse HEAD is an error naming the command, never a
    # silent "head": null (MINOR-2).
    def _run(argv, **kw):
        if argv[:2] == ["git", "-C"] and "show" in argv:
            return cp(argv, 0, COMMITTED_TOML, "")
        if argv[:2] == ["git", "-C"] and "rev-parse" in argv:
            return cp(argv, 1, "", "fatal: not a git repository")
        return cp(argv, 0, "", "")

    cfg = {"repo": str(tmp_path), "_run": _run, "_readlink": lambda p: "system-55-link"}
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert body == {"error": "git rev-parse HEAD"}


def test_patches_malformed_ledger(tmp_path):
    # A committed-but-malformed ledger is an "error" body, never a raised
    # TOMLDecodeError out of the handler (MINOR-3).
    def _run(argv, **kw):
        if argv[:2] == ["git", "-C"] and "show" in argv:
            return cp(argv, 0, "[[patch\n", "")
        return cp(argv, 0, "", "")

    cfg = {"repo": str(tmp_path), "_run": _run, "_readlink": lambda p: "system-55-link"}
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert body["error"].startswith("docs/ledger/patches.toml: ")


def test_patches_reads_head_not_worktree(tmp_path):
    # The real-git fixture the section asked for: commit a two-row ledger, then
    # grow the worktree copy to three rows. Reading HEAD must serve the two
    # committed rows, never the worktree (MINOR-1). Skips in the helm-unit
    # nix sandbox, which has no git on PATH.
    if shutil.which("git") is None:
        pytest.skip("git not on PATH (the helm-unit nix sandbox)")

    repo = tmp_path
    ledger = repo / "docs" / "ledger"
    ledger.mkdir(parents=True)
    two_rows = (
        '[[patch]]\nfile = "patches/dsh/0001.patch"\npackage = "dsh"\n\n'
        '[[patch]]\nfile = "patches/dsh/0002.patch"\npackage = "dsh"\n'
    )
    third_row = '[[patch]]\nfile = "patches/dsh/0003.patch"\npackage = "dsh"\n'
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
    }
    (ledger / "patches.toml").write_text(two_rows)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, env=env)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True, env=env)
    (ledger / "patches.toml").write_text(two_rows + third_row)

    cfg = {
        "repo": str(repo),
        "_run": subprocess.run,
        "_readlink": lambda p: "system-55-link",
    }
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert len(body["patches"]) == 2


def test_production_runner_seam(tmp_path, monkeypatch):
    # No cfg["_run"]: the handler must fall back to api's allowlisted run()
    # seam (MINOR-4). Monkeypatching api.run records the call.
    import api

    seen = {}

    def fake_run(argv, **kw):
        seen["argv"] = list(argv)
        seen["cwd"] = kw.get("cwd")
        return cp(argv, 0, TASKS_JSON, "")

    monkeypatch.setattr(api, "run", fake_run)
    cfg = {"repo": str(tmp_path)}
    status, _ = handler_for("/v1/tasks")(cfg, None)
    assert status == 200
    assert seen, "the production executor (api.run) must be exercised"
    assert seen["argv"][0] == "python3"
    assert seen["argv"][1] == os.path.join(
        str(tmp_path), "pkgs", "evidence", "tasks.py"
    )
    assert seen["cwd"] == str(tmp_path)


# ---------------------------------------------------------------------------
# the fix round (HM6c): the landed == running boundary, interface 3's catch-all
# arm, and the missing-ledger discriminator pinned on git's real stderr
# ---------------------------------------------------------------------------


def test_carried_boundary_landed_equals_running(tmp_path):
    # The boundary is strict >: a row landed exactly at the running generation
    # is not carried; one landed just after it is. X5 (>=) flips the first.
    committed = """\
[[patch]]
file = "patches/dsh/0001-one.patch"
package = "dsh"
landed_generation = 56

[[patch]]
file = "patches/dsh/0002-two.patch"
package = "dsh"
landed_generation = 57
"""
    run, _ = make_run(committed=committed)
    cfg = make_cfg(tmp_path, run, readlink="system-56-link")
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert body["running_generation"] == 56
    patches = body["patches"]
    assert patches[0]["landed_generation"] == 56
    assert patches[0]["carried_by_next_switch"] is False
    assert patches[1]["landed_generation"] == 57
    assert patches[1]["carried_by_next_switch"] is True


def test_unexpected_exception_is_error_body(tmp_path):
    # Any exception that leaves the handler body is the interface-3 error body,
    # never a raised exception out of the handler (MINOR-2: the catch-all arm).
    def _run(argv, **kw):
        raise RuntimeError("boom")

    cfg = {
        "repo": str(tmp_path),
        "_run": _run,
        "_readlink": lambda p: "system-55-link",
    }
    status, body = handler_for("/v1/patches")(cfg, None)
    assert status == 200
    assert body == {"error": "RuntimeError: boom"}


def test_missing_ledger_uses_git_stderr(tmp_path):
    # The discriminator pins git's real stderr, not English guesses: both real
    # phrasings of an absent ledger are "missing", and an unrelated git failure
    # is the error body (MINOR-4).
    def show_runner(stderr):
        def _run(argv, **kw):
            if argv[:2] == ["git", "-C"] and "show" in argv:
                return cp(argv, 128, "", stderr)
            return cp(argv, 0, "", "")

        return _run

    cases = [
        (
            "fatal: path 'docs/ledger/patches.toml' does not exist in 'HEAD'",
            {"patches": [], "missing": "docs/ledger/patches.toml"},
        ),
        (
            "fatal: path 'docs/ledger/patches.toml' exists on disk, but not in 'HEAD'",
            {"patches": [], "missing": "docs/ledger/patches.toml"},
        ),
        (
            "fatal: corrupt object",
            {"error": "git show HEAD:docs/ledger/patches.toml"},
        ),
    ]
    for stderr, expected in cases:
        cfg = {
            "repo": str(tmp_path),
            "_run": show_runner(stderr),
            "_readlink": lambda p: "system-55-link",
        }
        status, body = handler_for("/v1/patches")(cfg, None)
        assert status == 200
        assert body == expected
