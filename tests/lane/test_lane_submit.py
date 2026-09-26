"""Tests for pkgs/lane/lane-submit.py's `cmd_submit` (Lane L round 1 plan,
Task 3).

Drives `cmd_submit` in-process (import by path -- lane-submit.py is a
hyphenated filename, not an importable module, so `importlib.util` loads it
the same way tests/helm/test_collect.py loads pkgs/helm/collect.py) rather
than as a subprocess: `subprocess.run` (the `systemctl start` call at the
end of a submit) is monkeypatched out, and `LANE_STATE_DIR` points at
tmp_path, so no real /var/lib/lanes or systemd unit is ever touched. The
grp module's "lane" lookup is monkeypatched too -- this sandbox almost
certainly has no such group -- to the caller's own primary gid, which
os.chown always permits a non-root owner to set on their own file, so the
group-hardening assertions below exercise the real chown/chmod calls
lane-submit.py makes, not a mocked-out no-op.
"""

import importlib.util
import io
import json
import os
import subprocess
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
SRC = HERE.parents[2] / "pkgs" / "lane" / "lane-submit.py"
spec = importlib.util.spec_from_file_location("lane_submit", SRC)
lane_submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lane_submit)


@pytest.fixture(autouse=True)
def _state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LANE_STATE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def _fake_lane_group(monkeypatch):
    """Fakes grp.getgrnam("lane") to resolve to the test runner's own
    primary gid -- see the module docstring above for why this is a real
    chown, not a stub."""
    gid = os.getgid()
    monkeypatch.setattr(
        lane_submit.grp,
        "getgrnam",
        lambda name: (
            types.SimpleNamespace(gr_gid=gid)
            if name == "lane"
            else (_ for _ in ()).throw(KeyError(name))
        ),
    )
    return gid


@pytest.fixture
def no_systemctl(monkeypatch):
    """Replaces subprocess.run (the `systemctl start` call at the end of
    cmd_submit) with a stub that records its argv and returns a
    caller-chosen exit code, instead of ever touching a real unit."""
    calls = []

    def make(returncode=0):
        def _run(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, returncode)

        monkeypatch.setattr(lane_submit.subprocess, "run", _run)
        return calls

    return make


def _submit(argv, stdin_text, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
    return lane_submit.cmd_submit(argv)


def _chat_job_argv(lane="openrouter", model="m"):
    return [lane, "--kind", "chat", "--class", "permitted", "--model", model]


def _agent_job_argv(repo, lane="openrouter", model="m", extra=()):
    return [
        lane,
        "--kind",
        "agent",
        "--class",
        "permitted",
        "--model",
        model,
        "--repo",
        str(repo),
        *extra,
    ]


# --- forbidden repo prefixes -------------------------------------------------

FORBIDDEN_ABS = [
    "/run/baskets",
    "/var/lib/baskets",
    "/var/lib/helm",
    "/var/lib/egress-broker",
    "/var/lib/lanes",
    "/var/lib/secrets",
]


@pytest.mark.parametrize("prefix", FORBIDDEN_ABS)
def test_forbidden_prefix_refused_at_equality(
    prefix, no_systemctl, monkeypatch, capsys
):
    calls = no_systemctl()
    rc = _submit(_agent_job_argv(prefix), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "refusing" in err
    assert prefix in err


@pytest.mark.parametrize("prefix", FORBIDDEN_ABS)
def test_forbidden_prefix_refused_when_under(prefix, no_systemctl, monkeypatch, capsys):
    calls = no_systemctl()
    rc = _submit(
        _agent_job_argv(f"{prefix}/some/nested/repo"), "do the thing", monkeypatch
    )
    assert rc == 1
    assert calls == []
    assert "refusing" in capsys.readouterr().err


def test_forbidden_prefix_home_claude_and_strategy(
    no_systemctl, monkeypatch, capsys, tmp_path
):
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    calls = no_systemctl()

    rc = _submit(_agent_job_argv("~/.claude"), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []

    rc = _submit(_agent_job_argv("~/.claude/projects/x"), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []

    rc = _submit(_agent_job_argv("~/strategy"), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []

    err = capsys.readouterr().err
    assert "refusing" in err


def test_forbidden_prefix_home_codex(no_systemctl, monkeypatch, capsys, tmp_path):
    """SB7: ~/.codex is the codex operator home -- auth.json (a ChatGPT
    credential at rest), history.jsonl, sessions/, memories/ and its sqlite
    state -- the same local-only class as ~/.claude. Refuse a lane job's
    --repo under (or equal to) ~/.codex before any systemctl call. SB7b: the
    .codex dirs are created so a missing directory ("not a directory") cannot
    be the cause of the refusal, and the stderr names the prefix, so the rc
    and no-systemctl assertions discriminate the prefix rule too."""
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    # SB7b: ~/.codex and ~/.codex/sessions must EXIST, otherwise the refusal
    # on the base tree is the "is not a directory" branch, not the prefix rule.
    (fake_home / ".codex").mkdir()
    (fake_home / ".codex" / "sessions").mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    calls = no_systemctl()

    rc = _submit(_agent_job_argv("~/.codex"), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []

    rc = _submit(_agent_job_argv("~/.codex/sessions"), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []

    err = capsys.readouterr().err
    assert "refusing" in err
    assert ".codex" in err


def test_permitted_repo_outside_any_forbidden_prefix_is_not_refused_by_prefix_check(
    tmp_path,
):
    repo = tmp_path / "permitted-repo"
    repo.mkdir()
    assert lane_submit._refused_repo_prefix(repo) is None


# --- symlink escape -----------------------------------------------------------


def test_symlink_resolving_outside_repo_is_refused(
    no_systemctl, monkeypatch, capsys, tmp_path
):
    repo = tmp_path / "permitted-repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("not for the lane")
    (repo / "escape-link").symlink_to(secret)

    calls = no_systemctl()
    rc = _submit(_agent_job_argv(repo), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "symlink" in err
    assert "escape-link" in err
    # Nothing was ever copied for a refused job.
    job_root = tmp_path / "openrouter" / "jobs"
    assert not any(job_root.glob("*/repo")) if job_root.exists() else True


def test_relative_symlink_resolving_outside_repo_is_refused(
    no_systemctl, monkeypatch, capsys, tmp_path
):
    """A RELATIVE link whose target resolves outside the repo -- distinct
    from test_symlink_resolving_outside_repo_is_refused above, whose link
    is built from an absolute `secret` Path and so is itself absolute: that
    one is refused by _escaping_symlink's `os.path.isabs(raw_target)` guard
    (lane-submit.py:177-178) before ever reaching the target-resolution
    check, the same branch test_absolute_symlink_inside_repo_is_refused
    already covers. This test is the only one that reaches the
    `candidate.resolve()` / `target.relative_to(repo_root)` branch at
    lane-submit.py:179-186 (T3 review: without a test on that branch,
    deleting it leaves the whole suite green -- a mutation survivor for the
    exact security property this function exists to enforce: a planted
    relative link reaching e.g. ~/.claude out of an otherwise-permitted
    repo)."""
    repo = tmp_path / "permitted-repo"
    (repo / "sub").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("not for the lane")
    os.symlink("../../outside/secret.txt", repo / "sub" / "rel-escape")

    calls = no_systemctl()
    rc = _submit(_agent_job_argv(repo), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "symlink" in err
    assert "rel-escape" in err
    job_root = tmp_path / "openrouter" / "jobs"
    assert not any(job_root.glob("*/repo")) if job_root.exists() else True


def test_symlink_resolving_inside_repo_is_permitted(
    no_systemctl, monkeypatch, tmp_path
):
    repo = tmp_path / "permitted-repo"
    (repo / "sub").mkdir(parents=True)
    (repo / "sub" / "real.txt").write_text("hi")
    # A RELATIVE link (a plain string target, not repo / "sub" / ...,
    # which would be absolute) -- this is the shape that must survive the
    # copy: copytree(symlinks=True) copies the link's raw relative text
    # verbatim, so it still resolves under the snapshot root wherever the
    # snapshot ends up, unlike an absolute link (T3 review: see
    # test_absolute_symlink_inside_repo_is_refused below for that case).
    (repo / "link-to-real").symlink_to("sub/real.txt")

    calls = no_systemctl()
    rc = _submit(_agent_job_argv(repo), "do the thing", monkeypatch)
    assert rc == 0
    assert len(calls) == 1

    job_root = next(
        p for p in (tmp_path / "openrouter" / "jobs").iterdir() if p.is_dir()
    )
    snap = job_root / "repo"
    link = snap / "link-to-real"
    # Kills the symlinks=True -> False mutation too: if copytree
    # dereferenced the link instead of copying it as a link, this would
    # be a plain file, not a symlink.
    assert link.is_symlink()
    resolved = Path(os.path.realpath(link))
    assert resolved.is_relative_to(snap)
    assert resolved.read_text() == "hi"


def test_absolute_symlink_inside_repo_is_refused(
    no_systemctl, monkeypatch, capsys, tmp_path
):
    """A link whose target currently resolves INSIDE the repo is not
    automatically safe -- if the link itself is absolute, copytree copies
    its raw (absolute) text verbatim, so the copied link in the snapshot
    still points at the SOURCE tree, not the snapshot (T3 review: this is
    what let a copied "permitted" repo read/write the live operator tree
    through what looked like an isolated snapshot)."""
    repo = tmp_path / "permitted-repo"
    (repo / "sub").mkdir(parents=True)
    (repo / "sub" / "real.txt").write_text("hi")
    (repo / "link-to-real").symlink_to((repo / "sub" / "real.txt").resolve())

    calls = no_systemctl()
    rc = _submit(_agent_job_argv(repo), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "symlink" in err
    assert "link-to-real" in err
    job_root = tmp_path / "openrouter" / "jobs"
    assert not any(job_root.glob("*/repo")) if job_root.exists() else True


# --- job file mode / group ----------------------------------------------------


def test_chat_job_file_is_0660_group_lane(
    no_systemctl, monkeypatch, tmp_path, _fake_lane_group
):
    no_systemctl()
    rc = _submit(
        _chat_job_argv(),
        json.dumps([{"role": "user", "content": "hi"}]),
        monkeypatch,
    )
    assert rc == 0
    job_files = list((tmp_path / "openrouter" / "jobs").glob("*.json"))
    assert len(job_files) == 1
    st = job_files[0].stat()
    assert (st.st_mode & 0o777) == 0o660
    assert st.st_gid == _fake_lane_group


# --- agent job dir / snapshot permissions -------------------------------------


def _assert_hardened_dir(path, gid):
    """Every hardened directory must be at least rwxrws--- (0770); the
    SGID bit (the extra 2000) is best-effort -- lane-submit.py's
    _chmod_dir_setgid falls back to plain 0770 when the environment
    outright refuses SGID (this repo's own `nix build` sandbox does,
    seccomp-filtering chmod calls that would set it -- see
    _chmod_dir_setgid's docstring), so a strict `== 0o2770` here would
    make this test environment-dependent rather than testing the real
    contract (group-writable, group "lane")."""
    st = path.stat()
    assert (st.st_mode & 0o777) == 0o770, f"{path}: {oct(st.st_mode)}"
    assert st.st_gid == gid, f"{path}: gid {st.st_gid} != {gid}"


def test_agent_job_dir_and_snapshot_permissions(
    no_systemctl, monkeypatch, tmp_path, _fake_lane_group
):
    repo = tmp_path / "permitted-repo"
    (repo / "sub").mkdir(parents=True)
    (repo / "sub" / "file.py").write_text("x = 1\n")
    (repo / "top.txt").write_text("hi\n")

    no_systemctl()
    rc = _submit(_agent_job_argv(repo), "do the thing", monkeypatch)
    assert rc == 0

    jobs_dir = tmp_path / "openrouter" / "jobs"
    job_dirs = [p for p in jobs_dir.iterdir() if p.is_dir()]
    assert len(job_dirs) == 1
    job_root = job_dirs[0]

    _assert_hardened_dir(job_root, _fake_lane_group)

    repo_dst = job_root / "repo"
    assert repo_dst.is_dir()
    for path in [repo_dst, repo_dst / "sub"]:
        _assert_hardened_dir(path, _fake_lane_group)
    for path in [repo_dst / "sub" / "file.py", repo_dst / "top.txt"]:
        st = path.stat()
        assert (st.st_mode & 0o777) == 0o660, f"{path}: {oct(st.st_mode)}"
        assert st.st_gid == _fake_lane_group


# --- chat vs agent stdin shapes -----------------------------------------------


def test_chat_stdin_list_of_messages(no_systemctl, monkeypatch, tmp_path):
    no_systemctl()
    rc = _submit(
        _chat_job_argv(),
        json.dumps([{"role": "user", "content": "hi"}]),
        monkeypatch,
    )
    assert rc == 0
    job = json.loads(
        next((tmp_path / "openrouter" / "jobs").glob("*.json")).read_text()
    )
    assert job["kind"] == "chat"
    assert job["messages"] == [{"role": "user", "content": "hi"}]
    assert "prompt" not in job


def test_chat_stdin_messages_object(no_systemctl, monkeypatch, tmp_path):
    no_systemctl()
    rc = _submit(
        _chat_job_argv(),
        json.dumps({"messages": [{"role": "user", "content": "hi"}]}),
        monkeypatch,
    )
    assert rc == 0
    job = json.loads(
        next((tmp_path / "openrouter" / "jobs").glob("*.json")).read_text()
    )
    assert job["messages"] == [{"role": "user", "content": "hi"}]


def test_chat_stdin_not_json_or_wrong_shape_is_refused(
    no_systemctl, monkeypatch, capsys
):
    calls = no_systemctl()
    rc = _submit(_chat_job_argv(), "not json at all", monkeypatch)
    assert rc == 1
    assert calls == []
    assert "chat" in capsys.readouterr().err


def test_agent_stdin_prompt_object(no_systemctl, monkeypatch, tmp_path):
    repo = tmp_path / "permitted-repo"
    repo.mkdir()
    no_systemctl()
    rc = _submit(
        _agent_job_argv(repo),
        json.dumps({"prompt": "do the thing please"}),
        monkeypatch,
    )
    assert rc == 0
    job_root = next(
        p for p in (tmp_path / "openrouter" / "jobs").iterdir() if p.is_dir()
    )
    job = json.loads((job_root.parent / f"{job_root.name}.json").read_text())
    assert job["kind"] == "agent"
    assert job["prompt"] == "do the thing please"
    assert "messages" not in job


def test_agent_stdin_raw_text_fallback(no_systemctl, monkeypatch, tmp_path):
    repo = tmp_path / "permitted-repo"
    repo.mkdir()
    no_systemctl()
    rc = _submit(_agent_job_argv(repo), "  raw prompt text  \n", monkeypatch)
    assert rc == 0
    job_root = next(
        p for p in (tmp_path / "openrouter" / "jobs").iterdir() if p.is_dir()
    )
    job = json.loads((job_root.parent / f"{job_root.name}.json").read_text())
    assert job["prompt"] == "raw prompt text"


def test_agent_stdin_empty_is_refused(no_systemctl, monkeypatch, tmp_path, capsys):
    repo = tmp_path / "permitted-repo"
    repo.mkdir()
    calls = no_systemctl()
    rc = _submit(_agent_job_argv(repo), "   \n", monkeypatch)
    assert rc == 1
    assert calls == []
    assert "prompt" in capsys.readouterr().err


# --- keep-snapshot flag --------------------------------------------------------


def test_default_keep_snapshot_is_false(no_systemctl, monkeypatch, tmp_path):
    repo = tmp_path / "permitted-repo"
    repo.mkdir()
    no_systemctl()
    rc = _submit(_agent_job_argv(repo), "do the thing", monkeypatch)
    assert rc == 0
    job_root = next(
        p for p in (tmp_path / "openrouter" / "jobs").iterdir() if p.is_dir()
    )
    job = json.loads((job_root.parent / f"{job_root.name}.json").read_text())
    assert job["keep_snapshot"] is False


def test_keep_snapshot_flag_sets_job_field(no_systemctl, monkeypatch, tmp_path):
    repo = tmp_path / "permitted-repo"
    repo.mkdir()
    no_systemctl()
    rc = _submit(
        _agent_job_argv(repo, extra=["--keep-snapshot"]), "do the thing", monkeypatch
    )
    assert rc == 0
    job_root = next(
        p for p in (tmp_path / "openrouter" / "jobs").iterdir() if p.is_dir()
    )
    job = json.loads((job_root.parent / f"{job_root.name}.json").read_text())
    assert job["keep_snapshot"] is True


# --- systemctl start return-code handling -------------------------------------


def test_systemctl_start_success_prints_id_no_warning(
    no_systemctl, monkeypatch, capsys
):
    no_systemctl(returncode=0)
    rc = _submit(
        _chat_job_argv(),
        json.dumps([{"role": "user", "content": "hi"}]),
        monkeypatch,
    )
    assert rc == 0
    out = capsys.readouterr()
    assert out.out.strip()
    assert "warning" not in out.err


def test_systemctl_start_refused_exit_3_prints_id_no_warning(
    no_systemctl, monkeypatch, capsys
):
    no_systemctl(returncode=3)
    rc = _submit(
        _chat_job_argv(),
        json.dumps([{"role": "user", "content": "hi"}]),
        monkeypatch,
    )
    assert rc == 0
    out = capsys.readouterr()
    assert out.out.strip()
    assert "warning" not in out.err


def test_systemctl_start_other_nonzero_warns_but_still_prints_id(
    no_systemctl, monkeypatch, capsys
):
    no_systemctl(returncode=1)
    rc = _submit(
        _chat_job_argv(),
        json.dumps([{"role": "user", "content": "hi"}]),
        monkeypatch,
    )
    assert rc == 0
    out = capsys.readouterr()
    job_id = out.out.strip()
    assert job_id
    assert "warning" in out.err
    unit = f"lane-openrouter@{job_id}.service"
    assert unit in out.err
    assert f"journalctl -u {unit}" in out.err


# --- group-chown failure (T3 review: blocker B follow-up) ---------------------


def test_group_chown_failure_on_job_root_refuses_submit(
    no_systemctl, monkeypatch, tmp_path, _fake_lane_group, capsys
):
    """The "lane" group EXISTS (per _fake_lane_group) but os.chown fails --
    e.g. the operator isn't a member of it yet in this login session.
    cmd_submit must refuse the agent submit (which chowns job_root before
    doing anything else) rather than silently write a job the unit can
    never run."""
    repo = tmp_path / "permitted-repo"
    repo.mkdir()

    def failing_chown(_path, _uid, _gid):
        raise PermissionError("not a member of group lane")

    monkeypatch.setattr(lane_submit.os, "chown", failing_chown)

    calls = no_systemctl()
    rc = _submit(_agent_job_argv(repo), "do the thing", monkeypatch)
    assert rc == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "lane" in err
    assert "not in group lane" in err
    # Nothing was ever copied or started for a refused job.
    jobs_dir = tmp_path / "openrouter" / "jobs"
    assert not any(jobs_dir.glob("*/repo")) if jobs_dir.exists() else True


def test_group_chown_failure_on_job_file_refuses_submit(
    no_systemctl, monkeypatch, tmp_path, _fake_lane_group, capsys
):
    """Same failure, but on the plain chat path where there's no job_root
    to chown first -- the job FILE's own chown is the only gate, and it
    must refuse rather than write and start an unrunnable job."""

    def failing_chown(_path, _uid, _gid):
        raise PermissionError("not a member of group lane")

    monkeypatch.setattr(lane_submit.os, "chown", failing_chown)

    calls = no_systemctl()
    rc = _submit(
        _chat_job_argv(),
        json.dumps([{"role": "user", "content": "hi"}]),
        monkeypatch,
    )
    assert rc == 1
    assert calls == []
    err = capsys.readouterr().err
    assert "lane" in err
    assert "not in group lane" in err
    job_files = list((tmp_path / "openrouter" / "jobs").glob("*.json"))
    assert job_files == []


# --- executable-bit preservation in snapshots ---------------------------------


def test_executable_files_get_0770_in_snapshot(
    no_systemctl, monkeypatch, tmp_path, _fake_lane_group
):
    """A file whose source mode has any execute bit must get 0770 in the
    snapshot, not 0660 (which strips the executable bit). A non-executable
    file must stay 0660. Regression for the original _harden_snapshot that
    unconditionally chmod'd to 0660, stripping githooks, shell scripts,
    etc. of their executable bits."""
    repo = tmp_path / "permitted-repo"
    (repo / "sub").mkdir(parents=True)

    # 0755 script (executable)
    script = repo / "sub" / "script.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o755)

    # 0644 plain file (not executable)
    data = repo / "sub" / "data.txt"
    data.write_text("hello\n")
    data.chmod(0o644)

    no_systemctl()
    rc = _submit(_agent_job_argv(repo), "do the thing", monkeypatch)
    assert rc == 0

    jobs_dir = tmp_path / "openrouter" / "jobs"
    job_root = next(p for p in jobs_dir.iterdir() if p.is_dir())
    snap = job_root / "repo"

    snap_script = snap / "sub" / "script.sh"
    snap_data = snap / "sub" / "data.txt"

    assert snap_script.exists()
    assert snap_data.exists()

    st_script = snap_script.stat()
    st_data = snap_data.stat()

    assert (st_script.st_mode & 0o777) == 0o770, (
        f"executable script expected 0770, got {oct(st_script.st_mode & 0o777)}"
    )
    assert (st_data.st_mode & 0o777) == 0o660, (
        f"non-executable file expected 0660, got {oct(st_data.st_mode & 0o660)}"
    )
