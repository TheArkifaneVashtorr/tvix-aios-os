"""Derived task graph tests (plan 2026-09-05-session-context, G1)."""

import datetime
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import pytest

HERE = pathlib.Path(__file__).resolve()
FIXTURES = HERE.parent / "fixtures" / "plans"


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "tasks.py",
        pathlib.Path("pkgs/evidence/tasks.py"),
    ]
    src = next(p for p in candidates if p.exists())
    sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location("tasks", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tasks"] = mod
    spec.loader.exec_module(mod)
    return mod, src


tk, SRC = load()


def test_parse_typed_plan_reads_every_field():
    plan = tk.parse_plan(FIXTURES / "typed.md")
    assert plan["typed"] is True and plan["file"] == "typed.md"
    by = {t["key"]: t for t in plan["tasks"]}
    assert list(by) == ["E1", "E3", "E5", "E7", "D1"]
    assert (by["E1"]["kind"], by["E1"]["size"], by["E1"]["title"]) == (
        "code",
        "M",
        "the store",
    )
    assert by["E1"]["depends_on"] == [] and by["E3"]["depends_on"] == []
    assert by["E5"]["depends_on"] == ["E1", "R4"]  # parenthetical stripped
    assert by["E5"]["touches"] == [
        "nixosModules/helm.nix",
        "pkgs/helm/collect.py",
    ]  # backticks stripped
    assert by["E1"]["acceptance"] == ["evidence-unit", "lint"]
    assert (
        by["E1"]["commit_subject"] == "evidence: the store (test: evidence-unit, lint)"
    )
    assert by["D1"]["acceptance"] == [] and by["D1"]["kind"] == "docs"
    assert (
        "Body text for E1." in by["E1"]["body"]
        and "attribution" not in by["E1"]["body"]
    )
    assert "Operator" not in by["D1"]["body"]


def test_parse_legacy_plan_has_no_tasks():
    plan = tk.parse_plan(FIXTURES / "legacy.md")
    assert plan["typed"] is False and plan["tasks"] == []


def test_parse_plan_reads_probes_and_probe_env(tmp_path):
    # The `**probes:**` block yields one dict per bullet (name/cmd/op/value/by),
    # `**probe_env:**` its raw token value, and the bullets stay in `body` (the
    # brief prints them). The command is text between the first and last backtick
    # -- a pipe/redirect inside it is literal, and a `::` inside it must not
    # split the line (the parser extracts the command before splitting on `::`).
    plan = tmp_path / "probes.md"
    plan.write_text(
        "### K1 (code, M) — probes\n\n"
        "**probes:**\n"
        "- brief-chars: `bash tools/session-start.sh </dev/null \\| wc -c` :: le 8000 :: P4b gate 2026-09-05, devShell on core\n"
        "- checks-current: `git status --porcelain docs/MAP.md` :: empty :: the lint gate\n"
        "- colon-cmd: `printf 'a::b'` :: nonempty :: a command containing :: stays whole\n"
        "**probe_env:** FOO=bar BAZ=1\n\n"
        "body prose.\n"
    )
    parsed = tk.parse_plan(plan)
    by = {t["key"]: t for t in parsed["tasks"]}
    task = by["K1"]
    assert task["probes"] == [
        {
            "name": "brief-chars",
            "cmd": "bash tools/session-start.sh </dev/null \\| wc -c",
            "op": "le",
            "value": "8000",
            "by": "P4b gate 2026-09-05, devShell on core",
        },
        {
            "name": "checks-current",
            "cmd": "git status --porcelain docs/MAP.md",
            "op": "empty",
            "value": None,
            "by": "the lint gate",
        },
        {
            "name": "colon-cmd",
            "cmd": "printf 'a::b'",
            "op": "nonempty",
            "value": None,
            "by": "a command containing :: stays whole",
        },
    ]
    assert task["probe_env"] == "FOO=bar BAZ=1"
    assert "brief-chars" in task["body"]
    assert "checks-current" in task["body"]
    assert "colon-cmd" in task["body"]


def test_chain_root():
    assert tk.chain_root("E7b") == "E7"
    assert tk.chain_root("E7r") == "E7"
    assert tk.chain_root("E7") == "E7"
    assert tk.chain_root("A10T3") == "A10T3"
    assert tk.chain_root("W2-N10c") == "W2-N10"
    assert tk.chain_root("R3rb") == "R3"
    assert tk.chain_root("P1pro") == "P1pro"
    # A root may end in a capital letter (a task-name fragment like "W" for
    # writers or "M" for migration) as well as a digit, so its fix round
    # (…b/…c/…d) or re-plan (…r…) still links back to it.
    assert tk.chain_root("T1Wb") == "T1W"
    assert tk.chain_root("T3Mb") == "T3M"
    # Pinned: existing behaviour is unchanged by that widening.
    assert tk.chain_root("SP1") == "SP1"
    assert tk.chain_root("T1W") == "T1W"
    assert tk.chain_root("CR2r3b") == "CR2r3"
    assert tk.chain_root("PW1glm") == "PW1glm"
    assert tk.chain_root("T10a") == "T10"
    assert tk.chain_root("SD11c") == "SD11"


def test_parse_keys_and_list():
    assert tk.parse_keys("E1, R4 (both edit `flake.nix`)") == ["E1", "R4"]
    assert tk.parse_keys("none (integrates in the same wave)") == []
    assert tk.parse_list("`a/b.py`, c/d.nix") == ["a/b.py", "c/d.nix"]


def _run_touches(plan, key):
    return subprocess.run(
        [sys.executable, str(SRC), "touches", str(plan), key],
        capture_output=True,
        text=True,
        check=False,
    )


def test_touches_subcommand_unions_touches_over_the_chain_root(tmp_path):
    # Union over every section whose chain_root matches the key's, in first-seen
    # order, deduplicated, trailing slash stripped -- a sibling prefix (T10 vs
    # T1) is not the chain root, and the T1b chain contributes `c` from `c/`.
    plan = tmp_path / "plan.md"
    plan.write_text(
        "### T1 (code, M) — one\n\n"
        "**touches:** a, b\n\n"
        "### T1b (code, M) — one-b\n\n"
        "**touches:** b, c/\n\n"
        "### T2 (code, M) — two\n\n"
        "**touches:** d\n\n"
        "### T10 (code, M) — ten\n\n"
        "**touches:** e\n"
    )
    r = _run_touches(plan, "T1b")
    assert r.returncode == 0
    assert r.stdout == "a\nb\nc\n"
    assert r.stderr == ""
    r = _run_touches(plan, "T1")
    assert r.returncode == 0
    assert r.stdout == "a\nb\nc\n"
    r = _run_touches(plan, "T2")
    assert r.returncode == 0
    assert r.stdout == "d\n"


def test_touches_subcommand_missing_section_and_unreadable_plan(tmp_path):
    plan = tmp_path / "plan2.md"
    plan.write_text(
        "### T8 (code, M) — eight\n\n"
        "no touches line here.\n\n"
        "### T1 (code, M) — one\n\n"
        "**touches:** a\n"
    )
    # A section without a touches line carries no contract: empty stdout, exit 0.
    r = _run_touches(plan, "T8")
    assert r.returncode == 0
    assert r.stdout == ""
    # No section for the key -> exit 3, nothing on stdout.
    r = _run_touches(plan, "T9")
    assert r.returncode == 3
    assert r.stdout == ""
    assert f"tasks: touches: no section T9 in {plan}" in r.stderr
    # An unreadable plan -> exit 2.
    missing = tmp_path / "nonexistent.md"
    r = _run_touches(missing, "T1")
    assert r.returncode == 2
    assert f"tasks: touches: cannot read {missing}" in r.stderr


def _run_probes(plan, key):
    return subprocess.run(
        [sys.executable, str(SRC), "probes", str(plan), key],
        capture_output=True,
        text=True,
        check=False,
    )


def test_probes_subcommand_unions_nothing_and_prints_tab_rows(tmp_path):
    # `probes <plan> <KEY>`: an `env\t…` line then one tab-separated row per
    # probe with the command LAST (the bash consumer splits on tabs and reads
    # the command as the final field). A section without `**probes:**` yields
    # the env line only, exit 0; no section -> exit 3; unreadable -> exit 2.
    plan = tmp_path / "plan.md"
    plan.write_text(
        "### K1 (code, M) — one\n\n"
        "**probe_env:** FOO=bar BAZ=1\n"
        "**probes:**\n"
        "- a: `cmd one` :: le 8000 :: by who\n"
        "- b: `cmd two` :: empty :: by whom\n\n"
        "### K2 (code, M) — two\n\n"
        "no probes here.\n"
    )
    r = _run_probes(plan, "K1")
    assert r.returncode == 0
    assert r.stdout == (
        "env\tFOO=bar BAZ=1\n"
        "a\tle\t8000\tby who\tcmd one\n"
        "b\tempty\t\tby whom\tcmd two\n"
    )
    r = _run_probes(plan, "K2")
    assert r.returncode == 0
    assert r.stdout == "env\t\n"
    r = _run_probes(plan, "K9")
    assert r.returncode == 3
    assert r.stdout == ""
    assert f"tasks: probes: no section K9 in {plan}" in r.stderr
    r = _run_probes(tmp_path / "nonexistent.md", "K1")
    assert r.returncode == 2
    assert r.stdout == ""


def write_review(repo, name, first_line):
    d = repo / "docs" / "reviews"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(first_line + "\n\nbody\n")


def write_result(runs_dir, run, key, status, workspace):
    d = runs_dir / run
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{key}.result").write_text(
        f"FACTORY-RESULT status={status}\nFACTORY-CHECKS lint=pass\n\nrun: {run}\nkey: {key}\nworkspace: {workspace}\nbranch: task/{key}\n"
    )


def make_workspace(tmp_path, name, repo_name):
    ws = tmp_path / "ws" / name
    (ws / ".git").mkdir(parents=True)
    (ws / ".git" / "config").write_text(
        f'[remote "origin"]\n\turl = /home/dalhaka/factory/base/{repo_name}\n'
    )
    return ws


NOW = 1_800_000_000


def _seat_result(model, status, wall_s, usage):
    """A `.result` in the seat's emitted shape: one line per field, in the
    declared order (model, wall_s, usage); a field is dropped when its argument
    is None. `status` may be a `FACTORY-RESULT status=` block (multi-line)."""
    lines = [status, "FACTORY-CHECKS lint=pass", "", "run: r", "key: K"]
    if model is not None:
        lines.append(f"model: {model}")
    if wall_s is not None:
        lines.append(f"wall_s: {wall_s}")
    lines.append("workspace: /gone")
    if usage is not None:
        lines.append("")
        lines.append(f"usage: {usage}")
    return "\n".join(lines) + "\n"


def _write_aged(runs, run, key, text, age_days, now):
    """Write `<runs>/<run>/<key>.result` aged `age_days` days before `now`."""
    d = runs / run
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{key}.result"
    p.write_text(text)
    os.utime(p, (now - age_days * 86400, now - age_days * 86400))


def test_read_results_attributes_by_workspace_origin(tmp_path):
    runs = tmp_path / "runs"
    write_result(
        runs,
        "ev3",
        "E7b",
        "done",
        make_workspace(tmp_path, "ev3-E7b", "nixos-agent-env"),
    )
    write_result(runs, "cw1", "W1", "done", make_workspace(tmp_path, "cw1-W1", "media"))
    write_result(
        runs, "old", "Z9", "done", tmp_path / "gone"
    )  # workspace deleted -> not evidence
    res = tk.read_results(runs)
    assert res[("nixos-agent-env", "E7b")]["status"] == "done"
    assert res[("media", "W1")]["run"] == "cw1"
    assert not any(k[1] == "Z9" for k in res)


def test_read_results_newest_run_wins(tmp_path):
    runs = tmp_path / "runs"
    ws = make_workspace(tmp_path, "ev-E7b", "nixos-agent-env")
    write_result(runs, "ev2", "E7b", "done", ws)
    write_result(runs, "ev3", "E7b", "done", ws)
    os.utime(runs / "ev2", (1_600_000_000, 1_600_000_000))
    os.utime(runs / "ev3", (1_600_000_000 + 10, 1_600_000_000 + 10))
    res = tk.read_results(runs)
    assert res[("nixos-agent-env", "E7b")]["run"] == "ev3"


def test_read_reviews_matches_only_the_gate_header(tmp_path):
    write_review(
        tmp_path, "opus-review-a.md", "# Opus gate — seat run ev3, task E8 — APPROVED"
    )
    write_review(
        tmp_path, "opus-review-b.md", "# Opus gate — seat run ev2, task E7b — REJECTED"
    )
    write_review(
        tmp_path,
        "opus-review-c.md",
        "# dsh + dark factory: 24-hour review\n"
        "# Opus gate — seat run ev3, task E8b — REJECTED",
    )
    rv = tk.read_reviews(tmp_path)
    assert (
        rv["E8"]["verdict"] == "APPROVED"
        and rv["E7b"]["verdict"] == "REJECTED"
        and len(rv) == 2
    )


def fake_git(subjects):
    def run(argv, timeout=20.0):
        class R:
            returncode = 0
            stdout = "\n".join(subjects) + "\n"
            stderr = ""

        return R()

    return run


def test_derive_status_precedence(tmp_path):
    plan = tk.parse_plan(FIXTURES / "typed.md")
    by = {t["key"]: t for t in plan["tasks"]}
    landed = {"evidence: the store (test: evidence-unit, lint)"}
    reviews = {
        "E1": {"verdict": "REJECTED", "run": "ev1", "file": "q"},
        "E7": {"verdict": "REJECTED", "run": "ev2", "file": "x"},
        "E7b": {"verdict": "REJECTED", "run": "ev2", "file": "y"},
        "E7r": {"verdict": "APPROVED", "run": "ev2", "file": "z"},
    }
    results = {
        "E3": {"status": "done", "run": "ev1", "file": "r"}
    }  # already filtered to this repo, keyed by task key
    recorded = {"D1": "done"}  # already filtered to this plan
    landed_keys = {"E1"}
    assert (
        tk.derive_status(by["E1"], landed, reviews, results, recorded, landed_keys)[0]
        == "landed"
    )
    st, detail = tk.derive_status(
        by["E7"], landed, reviews, results, recorded, landed_keys
    )
    assert st == "approved" and "E7r" in detail  # newest chain member decides
    assert (
        tk.derive_status(by["E3"], landed, reviews, results, recorded, landed_keys)[0]
        == "ran"
    )
    assert (
        tk.derive_status(by["D1"], landed, reviews, results, recorded, landed_keys)[0]
        == "recorded"
    )
    st, detail = tk.derive_status(
        by["E5"], landed, reviews, results, recorded, landed_keys
    )
    assert st == "blocked" and "R4" in detail and "E1" not in detail


def test_derive_status_ready_when_deps_landed():
    plan = tk.parse_plan(FIXTURES / "typed.md")
    by = {t["key"]: t for t in plan["tasks"]}
    assert tk.derive_status(by["E7"], set(), {}, {}, {}, {"E1"})[0] == "ready"


def test_derive_status_chain_review_with_landed_root():
    # rule 1's second clause: a chain member reviewed AND the chain root's
    # subject landed -> landed, even though this task's own subject is not.
    plan = tk.parse_plan(FIXTURES / "typed.md")
    by = {t["key"]: t for t in plan["tasks"]}
    reviews = {"E7b": {"verdict": "REJECTED", "run": "ev2", "file": "y"}}
    st, detail = tk.derive_status(by["E7"], set(), reviews, {}, {}, {"E7"})
    assert st == "landed" and detail == "E7"


def test_scan_repo_and_build(tmp_path, monkeypatch):
    monkeypatch.setattr(
        tk,
        "read_recorded",
        lambda store: {("other.md", "D1"): "done", ("typed.md", "E7"): "done"},
    )
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "typed.md").write_text((FIXTURES / "typed.md").read_text())
    (plans / "legacy.md").write_text((FIXTURES / "legacy.md").read_text())
    (plans / "orphan.md").write_text("# no typed headings, no status row\n")
    write_review(
        repo, "opus-review-r.md", "# Opus gate — seat run ev1, task E3 — APPROVED"
    )
    status = {("nixos-agent-env", "legacy.md"): {"status": "done", "note": "phase 1"}}
    g = tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        status,
        tmp_path / "no-runs",
        str(tmp_path / "no-store"),
        run=fake_git(["evidence: the store (test: evidence-unit, lint)"]),
    )
    states = {t["key"]: t["state"] for t in g["tasks"]}
    assert states == {
        "E1": "landed",
        "E3": "approved",
        "E5": "blocked",
        "E7": "recorded",
        "D1": "blocked",
    }
    assert g["legacy"] == [{"file": "legacy.md", "status": "done", "note": "phase 1"}]
    assert g["untracked_plans"] == ["orphan.md"]
    assert g["chains"]["E1"] == ["E1"]


def test_landed_keys_use_chain_root(tmp_path):
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "typed.md").write_text(
        "### R3r (code, S) — the fix round\n\n"
        "**dependsOn:** none\n"
        "**commit subject:** `helm: re-key (test: helm-unit, lint)`\n\n"
        "### R7 (code, S) — the dependant\n\n"
        "**dependsOn:** R3\n"
        "**commit subject:** `helm: next (test: helm-unit, lint)`\n"
    )
    g = tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        {},
        tmp_path / "no-runs",
        str(tmp_path / "no-store"),
        run=fake_git(["helm: re-key (test: helm-unit, lint)"]),
    )
    states = {t["key"]: t["state"] for t in g["tasks"]}
    assert states == {"R3r": "landed", "R7": "ready"}


def test_read_recorded_returns_empty_on_malformed_row(tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    (store / "runs.jsonl").write_text("[1, 2, 3]\n")  # a JSON list, not an object
    assert tk.read_recorded(str(store)) == {}


def test_load_repos_and_plan_status(tmp_path):
    (tmp_path / "repos.toml").write_text(
        '[[repo]]\nname = "nixos-agent-env"\npath = "~/nixos-agent-env"\n\n[[repo]]\nname = "media"\npath = "~/flakes/media"\nplans = "docs/superpowers/plans/*.md"\n'
    )
    repos = tk.load_repos(tmp_path / "repos.toml")
    assert [r["name"] for r in repos] == ["nixos-agent-env", "media"]
    assert repos[0]["plans"] == "docs/superpowers/plans/*.md" and repos[0][
        "path"
    ] == os.path.expanduser("~/nixos-agent-env")
    (tmp_path / "status.toml").write_text(
        '[[plan]]\nrepo = "media"\nfile = "2026-09-02-media-flake.md"\nstatus = "superseded"\nnote = "by nix-native"\n'
    )
    ps = tk.load_plan_status(tmp_path / "status.toml")
    assert ps[("media", "2026-09-02-media-flake.md")] == {
        "status": "superseded",
        "note": "by nix-native",
    }
    assert tk.load_repos(tmp_path / "missing.toml") == []


def test_landed_subjects_uses_git(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
    }
    subprocess.run(
        ["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True, env=env
    )
    (repo / "f").write_text("x")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, env=env)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "commit",
            "-q",
            "-m",
            "evidence: the store (test: evidence-unit, lint)",
        ],
        check=True,
        env=env,
    )
    assert "evidence: the store (test: evidence-unit, lint)" in tk.landed_subjects(
        str(repo)
    )
    assert tk.landed_subjects(str(tmp_path / "not-a-repo")) == set()


def repo_with(tmp_path, files, landed=(), reviews=(), runs_dir=None):
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    for f in files:
        (plans / f).write_text((FIXTURES / f).read_text())
    for name, line in reviews:
        write_review(repo, name, line)
    if runs_dir is None:
        runs_dir = tmp_path / "no-runs"
    return tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        {},
        runs_dir,
        str(tmp_path / "no-store"),
        run=fake_git(list(landed)),
    )


def test_touches_overlap():
    assert tk.touches_overlap("flake.nix", "flake.nix")
    assert tk.touches_overlap("pkgs/x/*.sh", "pkgs/x/a.sh")
    assert tk.touches_overlap("pkgs/x/a.sh", "pkgs/x/*.sh")
    assert tk.touches_overlap("docs/board", "docs/board/log.md")
    assert not tk.touches_overlap("pkgs/x/a.sh", "pkgs/y/a.sh")


def test_waves_follow_dependencies_and_skip_landed(tmp_path):
    g = repo_with(
        tmp_path,
        ["typed.md"],
        landed=["evidence: the store (test: evidence-unit, lint)"],
    )
    # E1 landed; E5 needs R4 (unknown -> stays blocked, never scheduled); E7
    # ready; D1 after E7; E3 ready.
    assert tk.waves(g, plan="typed.md") == [["E3", "E7"], ["D1"]]


def test_seat_groups_merge_overlapping_touches(tmp_path):
    g = repo_with(
        tmp_path,
        ["typed.md", "second.md"],
        landed=["evidence: the store (test: evidence-unit, lint)"],
    )
    by = {t["key"]: t for t in g["tasks"]}
    by["E5"]["depends_on"] = ["E1"]  # make E5 ready for this test
    by["E5"]["state"] = "ready"
    groups = tk.seat_groups(g, ["E3", "E5", "X1"])
    assert groups == ['"E3"', '"E5 X1"']  # E5 and X1 both touch nixosModules/helm.nix


def test_factory_args_shape(tmp_path):
    g = repo_with(tmp_path, ["typed.md", "second.md"])
    args = tk.factory_args(g, "typed.md")
    e1 = next(a for a in args if a["key"] == "E1")
    assert e1 == {
        "key": "E1",
        "title": "the store",
        "kind": "code",
        "checks": ["evidence-unit", "lint"],
        "spec": e1["spec"],
        "dependsOn": [],
        "touches": ["pkgs/evidence/evidence.py", "flake.nix"],
        "class": "any",
    }
    assert "Body text for E1." in e1["spec"]
    assert {a["key"] for a in args} & {"X1", "X2", "X3"} == set()  # plan filter
    assert {a["key"] for a in tk.factory_args(g, "second.md")} == {"X1", "X2", "X3"}
    assert json.dumps(args)  # serialisable


def test_task_class_majority_tie_and_first_rule():
    rules = [
        ("nix-module", "nixosModules/*"),
        ("bats-test", "tests/unit/*"),
        ("python-evidence", "tests/*"),
        ("docs-plan", "docs/superpowers/*"),
    ]
    # majority: two bats files beat one nix file
    assert (
        tk.task_class(
            ["nixosModules/a.nix", "tests/unit/b.bats", "tests/unit/c.bats"], rules
        )
        == "bats-test"
    )
    # 1:1 tie -> the class whose rule comes FIRST in the file wins
    assert (
        tk.task_class(["nixosModules/a.nix", "tests/unit/b.bats"], rules)
        == "nix-module"
    )
    # a later rule matches where the earlier `tests/unit/*` does not
    assert tk.task_class(["tests/evidence/x.py"], rules) == "python-evidence"
    # `tests/unit/*` wins over the later `tests/*` for the same file
    assert tk.task_class(["tests/unit/x.bats"], rules) == "bats-test"
    # no touches, and touches matching no rule, are `any`
    assert tk.task_class([], rules) == "any"
    assert tk.task_class(["nowhere/x"], rules) == "any"


VALID_RULES = """# task-classes fixture
[[rule]]
class = "python-evidence"
glob = "pkgs/evidence/*"

[[rule]]
class = "bash-driver"
glob = "tools/factory/seat/*"

[[rule]]
class = "js-workflow"
glob = "tools/factory/dark-factory.js"

[[rule]]
class = "nix-module"
glob = "nixosModules/*"
"""


def test_class_rules_file_validation(tmp_path):
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "typed.md").write_text((FIXTURES / "typed.md").read_text())
    ledger = repo / "docs" / "ledger"
    ledger.mkdir(parents=True)
    rules_file = ledger / "task-classes.toml"

    def errs_for(text):
        rules_file.write_text(text)
        g = tk.scan_repo(
            {
                "name": "nixos-agent-env",
                "path": str(repo),
                "plans": "docs/superpowers/plans/*.md",
            },
            {},
            tmp_path / "no-runs",
            str(tmp_path / "no-store"),
            run=fake_git([]),
        )
        return tk.check({"generated": "t", "repos": [g]})

    assert any(
        "unknown class typo" in e
        for e in errs_for('[[rule]]\nclass = "typo"\nglob = "x/*"\n')
    )
    assert any(
        "is not a plain pattern" in e
        for e in errs_for('[[rule]]\nclass = "nix-module"\nglob = "docs/[a]"\n')
    )
    assert any(
        "missing glob" in e for e in errs_for('[[rule]]\nclass = "nix-module"\n')
    )
    assert any("missing class" in e for e in errs_for('[[rule]]\nglob = "x/*"\n'))
    assert any(
        "not a [[rule]] table" in e
        for e in errs_for('[rule]\nclass = "nix-module"\nglob = "x/*"\n')
    )
    # a well-formed rules file contributes no task-classes error (the fixture's
    # E5->R4 unknown key is unrelated)
    assert not any("task-classes" in e for e in errs_for(VALID_RULES))


def test_json_and_factory_args_carry_class(tmp_path):
    ledger = tmp_path / "nixos-agent-env" / "docs" / "ledger"
    ledger.mkdir(parents=True)
    (ledger / "task-classes.toml").write_text(VALID_RULES)
    g = repo_with(tmp_path, ["typed.md"])
    by = {t["key"]: t for t in g["tasks"]}
    assert by["E7"]["class"] == "bash-driver"  # tools/factory/seat/factory-integrate
    assert by["E3"]["class"] == "js-workflow"  # tools/factory/dark-factory.js
    assert by["D1"]["class"] == "any"  # docs/runbooks/x.md matches nothing here
    args = tk.factory_args(g, "typed.md")
    assert next(a for a in args if a["key"] == "E7")["class"] == "bash-driver"
    assert json.dumps(g["tasks"])  # class serialises on the graph


def test_brief_next_wave_prints_class(tmp_path):
    ledger = tmp_path / "nixos-agent-env" / "docs" / "ledger"
    ledger.mkdir(parents=True)
    (ledger / "task-classes.toml").write_text(VALID_RULES)
    g = repo_with(
        tmp_path,
        ["typed.md"],
        landed=["evidence: the store (test: evidence-unit, lint)"],
    )
    graph = {"generated": "t", "repos": [g], "runs_dir": None}
    brief = tk.render_brief(graph)
    assert "**Next wave** — nixos-agent-env: E3(js-workflow) E7(bash-driver)" in brief


def test_conflicts_across_plans(tmp_path):
    g = repo_with(tmp_path, ["typed.md", "second.md"])
    c = tk.conflicts(g)
    assert {
        "a": "E5",
        "plan_a": "typed.md",
        "b": "X1",
        "plan_b": "second.md",
        "path_a": "nixosModules/helm.nix",
        "path_b": "nixosModules/helm.nix",
    } in c
    assert not any(
        x["a"] == "X2" or x["b"] == "X2" for x in c
    )  # a.py/b.py do not overlap


def test_check_reports_unknown_dep_cycle_and_missing_acceptance(tmp_path):
    g = repo_with(tmp_path, ["typed.md", "second.md"])
    graph = {"generated": "t", "repos": [g]}
    errs = tk.check(graph)
    assert "tasks: nixos-agent-env/E5 dependsOn R4: unknown key" in errs
    assert any(
        e.startswith("tasks: cycle in nixos-agent-env: ") and "X2" in e and "X3" in e
        for e in errs
    )
    assert not any(
        "no acceptance" in e for e in errs
    )  # D1 is docs; every code task names a check
    next(t for t in g["tasks"] if t["key"] == "E1")["acceptance"] = []
    assert "tasks: nixos-agent-env/E1 (code) has no acceptance" in tk.check(graph)


def test_check_reports_duplicate_key(tmp_path):
    g = repo_with(tmp_path, ["typed.md"])
    dup = dict(next(t for t in g["tasks"] if t["key"] == "E1"), plan="other.md")
    g["tasks"].append(dup)
    assert "tasks: nixos-agent-env/E1 defined in typed.md and other.md" in tk.check(
        {"generated": "t", "repos": [g]}
    )


def test_brief_lists_counts_next_wave_and_operator_items(tmp_path):
    g = repo_with(
        tmp_path,
        ["typed.md"],
        landed=["evidence: the store (test: evidence-unit, lint)"],
        reviews=[
            ("opus-review-r.md", "# Opus gate — seat run ev1, task E3 — REJECTED")
        ],
    )
    claims = [
        {
            "id": "o4-framing-test",
            "status": "gap",
            "owner": "operator",
            "review_by": "2026-09-12",
        },
        {"id": "orch-only", "status": "gap", "owner": "orchestrator"},
    ]
    md = tk.render_brief({"generated": "2026-09-05T18:00:00Z", "repos": [g]}, claims)
    assert md.startswith("# Task brief (generated 2026-09-05T18:00:00Z)")
    assert "| nixos-agent-env | 1 | 0 | 1 |" in md
    assert "**Next wave** — nixos-agent-env: E7(any)" in md
    assert "**Rejected, fix round owed:** nixos-agent-env/E3" in md
    assert "o4-framing-test" in md and "orch-only" not in md
    assert len(md.splitlines()) <= 40


def test_brief_lists_escalations(tmp_path):
    # SD3: a `.escalate` record (no workspace, no `.result`) is listed after the
    # rejected-fix line; its derived state is untouched (still ready) because an
    # escalation is not a run. Two run dirs carry an `.escalate` for the same
    # key; the newest run's record wins (read_escalations).
    runs = tmp_path / "runs"
    (runs / "r1").mkdir(parents=True)
    (runs / "r9").mkdir(parents=True)
    for name, rung in (("r1", "3"), ("r9", "2")):
        (runs / name / "E7.escalate").write_text(
            f"run: {name}\nkey: E7\nrole: implement\nrung: {rung}\n"
            "escalate: claude/implement\nmodel: sonnet\neffort: high\n"
            "launch: Workflow({ scriptPath: 'tools/factory/dark-factory.js' })\n"
        )
    # r9 must win regardless of glob order: pin the run-directory mtimes.
    os.utime(runs / "r1", (1_600_000_000.0, 1_600_000_000.0))
    os.utime(runs / "r9", (1_700_000_000.0, 1_700_000_000.0))
    g = repo_with(
        tmp_path,
        ["typed.md"],
        landed=["evidence: the store (test: evidence-unit, lint)"],
        runs_dir=runs,
    )
    md = tk.render_brief({"generated": "t", "repos": [g], "runs_dir": str(runs)})
    assert "**Escalated:** E7 (claude/implement, rung 2, run r9)" in md
    # the newest run's record wins
    esc = tk.read_escalations(runs)["E7"]
    assert esc["rung"] == "2"
    assert esc["run"] == "r9"
    # the escalated key's derived state is untouched: an escalation is not a run
    e7 = next(t for t in g["tasks"] if t["key"] == "E7")
    assert e7["state"] == "ready"
    # no runs dir -> the line says none
    md2 = tk.render_brief({"generated": "t", "repos": [g]})
    assert "**Escalated:** none" in md2


def test_seats_line_sums_per_model_ordering_and_last_status(tmp_path):
    runs = tmp_path / "runs"
    now = NOW
    # `zeta-model` carries the 2 runs (so it must sort FIRST — runs descending),
    # yet sorts LAST by name (z > a): the fixture discriminates the `-runs` key
    # from a plain name sort, which would put `alpha-model` (the 1-run model)
    # first.
    _write_aged(
        runs,
        "r1",
        "K",
        _seat_result(
            "alpha-model",
            "FACTORY-RESULT status=done",
            2400,
            '{"input": 68620, "output": 13584}',
        ),
        1,
        now,
    )
    _write_aged(
        runs,
        "r2",
        "K",
        _seat_result(
            "zeta-model",
            "FACTORY-RESULT status=done",
            600,
            '{"input": 100, "output": 50}',
        ),
        6,
        now,
    )
    _write_aged(
        runs,
        "r3",
        "K",
        _seat_result(
            "zeta-model",
            "FACTORY-RESULT status=failed",
            1200,
            '{"input": 10, "output": 5}',
        ),
        2,
        now,
    )
    # the driver's demotion-rewrite shape: the block holds `failed` first, then
    # `done` — the LAST status line wins, and no wall/usage fields are present.
    _write_aged(
        runs,
        "r4",
        "K",
        _seat_result(
            "two-status-model",
            "FACTORY-RESULT status=failed\nFACTORY-RESULT status=done",
            None,
            None,
        ),
        1,
        now,
    )
    line = tk.render_seats_line(tk.seat_stats(runs, now=now))
    assert line == (
        "**Seats (7 d):** zeta-model: 2 runs, 1 done, 10 min, 165 billed · "
        "alpha-model: 1 run, 1 done, 40 min, 82204 billed · two-status-model: "
        "1 run, 1 done, ? min, 0 billed"
    )


def test_seats_ignores_aged_logs_and_dotfiles(tmp_path):
    runs = tmp_path / "runs"
    now = NOW
    _write_aged(
        runs,
        "r6",
        "K",
        _seat_result("inside-model", "FACTORY-RESULT status=done", 60, '{"input": 1}'),
        1,
        now,
    )
    # `.log`, `.pid` and dot-files whose text is a perfectly valid result: each
    # is written inside the seven-day window (aged 1 d) so only the `*.result`
    # glob — never the cutoff — keeps them out of the count.
    for name, model, path in (
        ("K2.log", "log-model", runs / "rlog" / "K2.log"),
        ("K2.pid", "pid-model", runs / "rpid" / "K2.pid"),
        (".marker-K3.x", "dot-model", runs / "rdot" / ".marker-K3.x"),
    ):
        p = path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            _seat_result(model, "FACTORY-RESULT status=done", 60, '{"input": 1}')
        )
        os.utime(p, (now - 86400, now - 86400))
    logs = [p for p in (runs / "rlog").iterdir()]
    pids = [p for p in (runs / "rpid").iterdir()]
    dots = [p for p in (runs / "rdot").iterdir()]
    stats = tk.seat_stats(runs, now=now)
    assert len(logs) == 1 and len(pids) == 1 and len(dots) == 1
    assert len(stats) == 1
    assert [r["model"] for r in stats] == ["inside-model"]


def test_seats_absent_fields_and_unreadable(tmp_path):
    runs = tmp_path / "runs"
    now = NOW
    # an empty runs dir renders `none`
    assert tk.render_seats_line(tk.seat_stats(tmp_path / "empty", now=now)) == (
        "**Seats (7 d):** none"
    )
    # a graph without `runs_dir` renders `none`
    g = repo_with(tmp_path, ["typed.md"])
    md = tk.render_brief({"generated": "t", "repos": [g]})
    assert "**Seats (7 d):** none" in md
    # no model: -> unknown; no wall_s: -> ? min; no usage: -> 0 billed
    _write_aged(
        runs,
        "r1",
        "K",
        _seat_result(None, "FACTORY-RESULT status=done", None, None),
        1,
        now,
    )
    _write_aged(
        runs,
        "r2",
        "K",
        _seat_result(
            "m",
            "FACTORY-RESULT status=done",
            None,
            '{"input": true, "output": "5"}',
        ),
        1,
        now,
    )
    _write_aged(
        runs,
        "r3",
        "K",
        _seat_result("m2", "FACTORY-RESULT status=done", None, "not-json"),
        1,
        now,
    )
    md = tk.render_seats_line(tk.seat_stats(runs, now=now))
    assert "unknown: 1 run, 1 done, ? min, 0 billed" in md
    assert "m: 1 run, 1 done, ? min, 0 billed" in md
    assert "m2: 1 run, 1 done, ? min, 0 billed" in md
    # a file with FACTORY-CHECKS but no FACTORY-RESULT line is not counted
    noresult = tmp_path / "nones"
    d = noresult / "r"
    d.mkdir(parents=True)
    (d / "K.result").write_text("FACTORY-CHECKS lint=pass\n")
    assert tk.seat_stats(noresult, now=now) == []


def test_seats_unreadable_file_and_file_shaped_run(tmp_path):
    runs = tmp_path / "runs"
    now = NOW
    _write_aged(
        runs,
        "r1",
        "K",
        _seat_result(
            "readable-model", "FACTORY-RESULT status=done", 60, '{"input": 1}'
        ),
        1,
        now,
    )
    # a result file that cannot be read: skipped, not fatal, and the run dir's
    # other results still count.
    d = runs / "r2"
    d.mkdir(parents=True, exist_ok=True)
    unreadable = d / "K.result"
    unreadable.write_text(
        _seat_result("no-read", "FACTORY-RESULT status=done", 60, '{"input": 1}')
    )
    os.utime(unreadable, (now - 86400, now - 86400))
    if os.geteuid() == 0:  # chmod 000 cannot hurt root; the nix sandbox is not root
        pytest.skip("cannot make an unreadable file as root")
    unreadable.chmod(0)
    # a `<runs>/<run>` entry that is a regular file, not a directory: ignored.
    (runs / "file-shaped-run").write_text("not a run dir")
    md = tk.render_seats_line(tk.seat_stats(runs, now=now))
    assert md == "**Seats (7 d):** readable-model: 1 run, 1 done, 1 min, 1 billed"


def test_seats_rounds_wall_s_to_the_nearest_minute(tmp_path):
    runs = tmp_path / "runs"
    now = NOW
    _write_aged(
        runs,
        "r1",
        "K",
        _seat_result("half-model", "FACTORY-RESULT status=done", 570, '{"input": 0}'),
        1,
        now,
    )
    _write_aged(
        runs,
        "r2",
        "K",
        _seat_result(
            "under-half-model", "FACTORY-RESULT status=done", 569, '{"input": 0}'
        ),
        1,
        now,
    )
    md = tk.render_seats_line(tk.seat_stats(runs, now=now))
    assert "half-model: 1 run, 1 done, 10 min, 0 billed" in md
    assert "under-half-model: 1 run, 1 done, 9 min, 0 billed" in md


def test_seats_takes_the_first_model_line(tmp_path):
    runs = tmp_path / "runs"
    now = NOW
    # the header carries `model: first-model`; a second `model:` line appears
    # only after the diffstat — the FIRST one wins.
    text = (
        "FACTORY-RESULT status=done\n"
        "FACTORY-CHECKS lint=pass\n"
        "\n"
        "model: first-model\n"
        "wall_s: 60\n"
        'usage: {"input": 1}\n'
        "diffstat: 12 files changed\n"
        "model: second-model\n"
    )
    _write_aged(runs, "r1", "K", text, 1, now)
    stats = tk.seat_stats(runs, now=now)
    assert [r["model"] for r in stats] == ["first-model"]


def test_seats_missing_usage_key_contributes_zero(tmp_path):
    runs = tmp_path / "runs"
    now = NOW
    _write_aged(
        runs,
        "r1",
        "K",
        _seat_result("input-model", "FACTORY-RESULT status=done", 60, '{"input": 1}'),
        1,
        now,
    )
    _write_aged(
        runs,
        "r2",
        "K",
        _seat_result("output-model", "FACTORY-RESULT status=done", 60, '{"output": 2}'),
        1,
        now,
    )
    md = tk.render_seats_line(tk.seat_stats(runs, now=now))
    assert "input-model: 1 run, 1 done, 1 min, 1 billed" in md
    assert "output-model: 1 run, 1 done, 1 min, 2 billed" in md


def test_seats_line_in_the_cli_brief(tmp_path):
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "second.md").write_text(
        (FIXTURES / "second.md").read_text()
    )
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "nixos-agent-env"\npath = "{repo}"\n'
    )
    runs = tmp_path / "runs"
    make_workspace(tmp_path, "r-s", "nixos-agent-env")
    # a real `now` keeps the aged files inside the seven-day window the CLI uses
    now = time.time()
    _write_aged(
        runs,
        "r1",
        "K",
        _seat_result(
            "gpt-6-astra",
            "FACTORY-RESULT status=done",
            2400,
            '{"input": 68620, "output": 13584}',
        ),
        1,
        now,
    )
    _write_aged(
        runs,
        "r2",
        "K",
        _seat_result(
            "deepseek/deepseek-v4-pro-0813",
            "FACTORY-RESULT status=done",
            600,
            '{"input": 100, "output": 50}',
        ),
        6,
        now,
    )
    _write_aged(
        runs,
        "r3",
        "K",
        _seat_result(
            "deepseek/deepseek-v4-pro-0813",
            "FACTORY-RESULT status=failed",
            1200,
            '{"input": 10, "output": 5}',
        ),
        2,
        now,
    )
    _write_aged(
        runs,
        "r4",
        "K",
        _seat_result(
            "two-status-model",
            "FACTORY-RESULT status=failed\nFACTORY-RESULT status=done",
            None,
            None,
        ),
        1,
        now,
    )
    r = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--root",
            str(root),
            "--runs-dir",
            str(runs),
            "--store",
            str(tmp_path / "none"),
            "brief",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    lines = r.stdout.splitlines()
    seats_line = (
        "**Seats (7 d):** deepseek/deepseek-v4-pro-0813: 2 runs, 1 done, "
        "10 min, 165 billed · gpt-6-astra: 1 run, 1 done, "
        "40 min, 82204 billed · two-status-model: 1 run, 1 done, ? min, 0 billed"
    )
    assert seats_line in lines
    i = next(i for i, l in enumerate(lines) if l.startswith("**Record"))
    assert lines[i + 1] == seats_line
    # a /nonexistent runs root renders `none`
    r = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--root",
            str(root),
            "--runs-dir",
            "/nonexistent",
            "--store",
            str(tmp_path / "none"),
            "brief",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "**Seats (7 d):** none" in r.stdout


def test_seats_never_touches_the_board_block(tmp_path):
    g = repo_with(tmp_path, ["typed.md"])
    assert "Seats" not in tk.render_board_block({"generated": "t", "repos": [g]})
    md = tk.render_brief({"generated": "t", "repos": [g]})
    assert len(md.splitlines()) <= 40


def test_cli_check_and_json(tmp_path):
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "second.md").write_text(
        (FIXTURES / "second.md").read_text()
    )
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "nixos-agent-env"\npath = "{repo}"\n'
    )
    r = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "none"),
            "--store",
            str(tmp_path / "none"),
            "check",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1 and "cycle" in r.stderr
    r = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "none"),
            "--store",
            str(tmp_path / "none"),
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (
        r.returncode == 0
        and json.loads(r.stdout)["repos"][0]["name"] == "nixos-agent-env"
    )
    data = json.loads(r.stdout)
    assert data["repos"][0]["tasks"][0]["state"] in tk.STATES
    r = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "none"),
            "--store",
            str(tmp_path / "none"),
            "waves",
            "--repo",
            "nixos-agent-env",
            "--plan",
            "second.md",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0 and r.stdout.splitlines()[0] == '"X1"'


CHAIN_PLAN = """# Chain fixture plan (a chain: root G1 + fix round G1b)

### G1 (code, S) — the root task

**dependsOn:** none

**touches:** pkgs/evidence/tasks.py
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: chain root (test: evidence-unit, lint)`

### G1b (code, S) — the fix round

**dependsOn:** G1

**touches:** pkgs/evidence/tasks.py
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: chain fix round (test: evidence-unit, lint)`
"""


def chain_graph(tmp_path, reviews, result_key="G1b"):
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "chain.md").write_text(CHAIN_PLAN)
    for name, line in reviews:
        write_review(repo, name, line)
    runs = tmp_path / "runs"
    if result_key:
        write_result(
            runs,
            "ev1",
            result_key,
            "done",
            make_workspace(tmp_path, "ev1-" + result_key, "nixos-agent-env"),
        )
    return tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        {},
        runs,
        str(tmp_path / "no-store"),
        run=fake_git([]),
    )


def test_chain_last_member_result_beats_root_review(tmp_path):
    # The last chain member is G1b: its own result wins over G1's rejected
    # review. Today this reports "rejected" (the newest review across the
    # whole chain), which is wrong — G1b's result has no review of its own.
    g = chain_graph(
        tmp_path,
        [("opus-review-a.md", "# Opus gate — seat run ev1, task G1 — REJECTED")],
    )
    by = {t["key"]: t for t in g["tasks"]}
    assert by["G1"]["state"] == "ran"
    assert "G1b" in by["G1"]["detail"]


def test_chain_last_member_approved_review(tmp_path):
    g = chain_graph(
        tmp_path,
        [
            ("opus-review-a.md", "# Opus gate — seat run ev1, task G1 — REJECTED"),
            ("opus-review-b.md", "# Opus gate — seat run ev1, task G1b — APPROVED"),
        ],
    )
    by = {t["key"]: t for t in g["tasks"]}
    assert by["G1"]["state"] == "approved"
    assert "G1b" in by["G1"]["detail"]


def test_chain_last_member_rejected_review_newest(tmp_path):
    g = chain_graph(
        tmp_path,
        [
            ("opus-review-a.md", "# Opus gate — seat run ev1, task G1 — REJECTED"),
            ("opus-review-b.md", "# Opus gate — seat run ev1, task G1b — APPROVED"),
            ("opus-review-c.md", "# Opus gate — seat run ev1, task G1b — REJECTED"),
        ],
    )
    by = {t["key"]: t for t in g["tasks"]}
    assert by["G1"]["state"] == "rejected"
    assert "G1b" in by["G1"]["detail"]


def test_brief_lists_chain_once_by_root(tmp_path):
    g = chain_graph(
        tmp_path,
        [
            ("opus-review-a.md", "# Opus gate — seat run ev1, task G1 — REJECTED"),
            ("opus-review-b.md", "# Opus gate — seat run ev1, task G1b — APPROVED"),
            ("opus-review-c.md", "# Opus gate — seat run ev1, task G1b — REJECTED"),
        ],
    )
    md = tk.render_brief({"generated": "t", "repos": [g]})
    line = next(
        l for l in md.splitlines() if l.startswith("**Rejected, fix round owed:**")
    )
    assert "nixos-agent-env/G1b" not in line  # never lists the suffix alone
    assert "nixos-agent-env/G1 " in line  # the root, once
    assert "G1b" in line  # the last member is named in the detail


def _fix_round_repo(
    root_state, successor_state, root_plan="p.md", successor_plan="p.md"
):
    """A minimal repo graph (no scan_repo) isolating the brief's rejected-list
    rendering: a rejected-looking root K1 and its fix-round successor K1b,
    whose own derived states are given directly."""
    return {
        "name": "nixos-agent-env",
        "tasks": [
            {
                "key": "K1",
                "state": root_state,
                "detail": "K1 by rev1",
                "plan": root_plan,
            },
            {
                "key": "K1b",
                "state": successor_state,
                "detail": "K1b by rev2",
                "plan": successor_plan,
            },
        ],
        "legacy": [],
        "untracked_plans": [],
    }


def test_brief_drops_rejected_root_whose_fix_round_landed(tmp_path):
    # K1 was rejected; its fix round K1b later landed in the same plan. The
    # root no longer owes a fix round. Mutant: drop the successor check -> K1
    # is listed again -> this test goes red.
    g = _fix_round_repo("rejected", "landed")
    md = tk.render_brief({"generated": "t", "repos": [g]})
    line = next(
        l for l in md.splitlines() if l.startswith("**Rejected, fix round owed:**")
    )
    assert line == "**Rejected, fix round owed:** none"


def test_brief_drops_rejected_root_whose_fix_round_approved(tmp_path):
    # Same as above, but the successor's own gate is merely "approved" (not
    # yet landed) — that also closes the root's obligation.
    g = _fix_round_repo("rejected", "approved")
    md = tk.render_brief({"generated": "t", "repos": [g]})
    line = next(
        l for l in md.splitlines() if l.startswith("**Rejected, fix round owed:**")
    )
    assert line == "**Rejected, fix round owed:** none"


def test_brief_keeps_rejected_root_when_successor_in_other_plan(tmp_path):
    # A same-named successor typed in a DIFFERENT plan is not this root's fix
    # round; the root still owes one.
    g = _fix_round_repo(
        "rejected", "landed", root_plan="p.md", successor_plan="other.md"
    )
    md = tk.render_brief({"generated": "t", "repos": [g]})
    line = next(
        l for l in md.splitlines() if l.startswith("**Rejected, fix round owed:**")
    )
    assert "nixos-agent-env/K1" in line


def test_conflicts_same_plan_not_reported(tmp_path):
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "chain.md").write_text(CHAIN_PLAN)
    g = tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        {},
        tmp_path / "no-runs",
        str(tmp_path / "no-store"),
        run=fake_git([]),
    )
    c = tk.conflicts(g)
    assert not any(
        {x["a"], x["b"]} == {"G1", "G1b"} for x in c
    )  # same plan, overlapping touches


def test_main_waves_factory_args_requires_plan(tmp_path, capsys):
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "second.md").write_text(
        (FIXTURES / "second.md").read_text()
    )
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "r"\npath = "{repo}"\n'
    )
    rc = tk.main(
        [
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "none"),
            "--store",
            str(tmp_path / "none"),
            "waves",
            "--repo",
            "r",
            "--factory-args",
        ]
    )
    assert rc == 2
    assert "usage" in capsys.readouterr().err


def test_brief_legacy_open_counts_only_open(tmp_path):
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "a.md").write_text("# no typed headings\n")
    (plans / "b.md").write_text("# no typed headings\n")
    status = {
        ("nixos-agent-env", "a.md"): {"status": "open", "note": ""},
        ("nixos-agent-env", "b.md"): {"status": "done", "note": ""},
    }
    g = tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        status,
        tmp_path / "no-runs",
        str(tmp_path / "no-store"),
        run=fake_git([]),
    )
    md = tk.render_brief({"generated": "t", "repos": [g]})
    row = next(l for l in md.splitlines() if l.startswith("| nixos-agent-env |"))
    cols = [c.strip() for c in row.strip("|").split("|")]
    assert cols[-2] == "1"  # legacy open: only the "open" row, not "done"


def test_board_block_roundtrip_and_drift(tmp_path):
    g = repo_with(
        tmp_path,
        ["typed.md"],
        landed=["evidence: the store (test: evidence-unit, lint)"],
    )
    graph = {"generated": "t", "repos": [g]}
    board = tmp_path / "OPERATIONS.md"
    board.write_text(
        "# Board\n\n## START HERE (x)\n\n<!-- tasks:begin -->\nstale\n"
        "<!-- tasks:end -->\n\n**Now.** words\n"
    )
    assert tk.board_drift(board, graph) is not None
    assert tk.write_board(board, graph) is True
    text = board.read_text()
    assert (
        "**Queued (derived from this tree; tasks whose dependencies run in other "
        "repos, and in-flight state, are in the session brief).** E3 E7 (typed.md)"
        in text
        and "stale" not in text
        and "**Now.** words" in text
    )
    assert tk.board_drift(board, graph) is None
    assert tk.write_board(board, graph) is False


def test_board_without_markers_is_an_error(tmp_path):
    board = tmp_path / "OPERATIONS.md"
    board.write_text("# Board\n")
    try:
        tk.write_board(board, {"generated": "t", "repos": []})
    except SystemExit as e:
        assert e.code == 1
    else:
        raise AssertionError("expected SystemExit")


def test_write_board_queue_ignores_run_results(tmp_path, monkeypatch):
    # A "ran" result lives in ~/factory, not the commit, so the board's queue
    # is derived from git landed + reviews only; write-board must agree with
    # the pre-commit hook, which derives from THIS tree with no runs/store.
    monkeypatch.setattr(tk, "run", fake_git([]))  # nothing landed in git history
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans" / "typed.md").write_text(
        (FIXTURES / "typed.md").read_text()
    )
    # a repos.toml names a repo elsewhere; the board never reads it
    (root / "docs" / "ledger" / "repos.toml").write_text(
        '[[repo]]\nname = "elsewhere"\npath = "~/elsewhere"\n'
    )
    ws = tmp_path / "ws"
    (ws / ".git").mkdir(parents=True)
    (ws / ".git" / "config").write_text(
        '[remote "origin"]\n\turl = /base/nixos-agent-env\n'
    )
    runs = tmp_path / "runs" / "r1"
    runs.mkdir(parents=True)
    (runs / "E1.result").write_text(
        f"FACTORY-RESULT status=done\nrun: r1\nkey: E1\nworkspace: {ws}\n"
    )
    board = root / "OPERATIONS.md"
    board.write_text("# Board\n\n<!-- tasks:begin -->\nstale\n<!-- tasks:end -->\n")
    rc = tk.main(
        [
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "runs"),
            "--store",
            str(tmp_path / "no-store"),
            "write-board",
            "--board",
            "OPERATIONS.md",
        ]
    )
    assert rc == 0
    assert "E1 E3 (typed.md)" in board.read_text()


BOARD_PLAN = """# Board fixture plan (this tree is its own repo)

### T1 (code, S) — first

**dependsOn:** none

**touches:** a.py
**acceptance:** unit
**commit subject:** `x: first (test: unit)`

### T2 (code, S) — second

**dependsOn:** T1

**touches:** b.py
**acceptance:** unit
**commit subject:** `x: second (test: unit)`
"""


def make_board_tree(tmp_path, repos=None):
    """A `--root` that is its own repo (this tree): plans live under the root.
    A repos.toml is written so a board_graph that wrongly read it would drift."""
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans" / "board.md").write_text(BOARD_PLAN)
    if repos is None:
        repos = f'[[repo]]\nname = "root"\npath = "{root}"\n'
    (root / "docs" / "ledger" / "repos.toml").write_text(repos)
    return root


def test_board_graph_derives_this_tree_ignoring_repos_toml(tmp_path, monkeypatch):
    # board_graph(root) scans THIS tree only. A repos.toml naming ~/elsewhere
    # (whose expansion depends on HOME) must not change the block, so a clean
    # clone / second machine derives the identical queue.
    monkeypatch.setattr(tk, "run", fake_git([]))  # nothing landed anywhere
    root = make_board_tree(
        tmp_path, repos='[[repo]]\nname = "elsewhere"\npath = "~/elsewhere"\n'
    )
    real_home = os.environ.get("HOME")
    empty_home = tmp_path / "empty-home"
    empty_home.mkdir()
    monkeypatch.setenv("HOME", str(empty_home))
    under_empty_home = tk.render_board_block(tk.board_graph(str(root)))
    assert real_home is not None
    monkeypatch.setenv("HOME", real_home)
    under_real_home = tk.render_board_block(tk.board_graph(str(root)))
    assert under_empty_home == under_real_home
    assert "T1 (board.md)" in under_empty_home
    assert "nothing queued" not in under_empty_home


def test_main_check_board_stale_current_and_runs_free(tmp_path, monkeypatch, capsys):
    # M5: the --board flag is honoured (stale -> 1, current -> 0).  M8: the
    # drift is compared against board_graph, not the live graph, so a "ran"
    # result that changes only the live graph causes no drift.
    monkeypatch.setattr(tk, "run", fake_git([]))  # nothing landed
    root = make_board_tree(tmp_path)
    board = root / "OPERATIONS.md"
    args = ["--root", str(root), "check", "--board", "OPERATIONS.md"]
    # stale
    board.write_text("# Board\n\n<!-- tasks:begin -->\nstale\n<!-- tasks:end -->\n")
    assert tk.main(args) == 1
    assert "OPERATIONS.md queue block is stale" in capsys.readouterr().err
    # current
    current = tk.render_board_block(tk.board_graph(str(root)))
    board.write_text(f"# Board\n\n<!-- tasks:begin -->\n{current}<!-- tasks:end -->\n")
    assert tk.main(args) == 0
    # a "ran" result for T1 changes only the live graph; board_graph ignores it
    runs = tmp_path / "runs"
    write_result(runs, "r1", "T1", "done", make_workspace(tmp_path, "r1-T1", "root"))
    assert (
        tk.main(
            [
                "--root",
                str(root),
                "--runs-dir",
                str(runs),
                "--store",
                str(tmp_path / "store"),
                "check",
                "--board",
                "OPERATIONS.md",
            ]
        )
        == 0
    )


def test_render_board_block_header_and_ready_blocked_only(tmp_path):
    # Header names the tree, and only ready/blocked chains appear: a landed
    # task and an approved (in-flight) task are not queued.
    g = repo_with(
        tmp_path,
        ["typed.md"],
        landed=["evidence: the store (test: evidence-unit, lint)"],
        reviews=[
            ("opus-review-r.md", "# Opus gate — seat run ev1, task E3 — APPROVED")
        ],
    )
    block = tk.render_board_block({"generated": "t", "repos": [g]})
    assert block.startswith(
        "**Queued (derived from this tree; tasks whose dependencies run in other "
        "repos, and in-flight state, are in the session brief).** "
    )
    assert "E7" in block and "E1" not in block and "E3" not in block


def _two_repos(tmp_path):
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    for r in (repo_a, repo_b):
        (r / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo_a / "docs" / "superpowers" / "plans" / "a.md").write_text(
        "### T1 (code, S) — runs elsewhere\n\n"
        "**dependsOn:** none\n"
        "**repo:** repo-b\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: cross (test: unit)`\n\n"
        "### TA (code, S) — stays here\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** a2.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: own-a (test: unit)`\n"
    )
    (repo_b / "docs" / "superpowers" / "plans" / "b.md").write_text(
        "### TB (code, S) — own b\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** b.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: own-b (test: unit)`\n"
    )
    return repo_a, repo_b


def test_repo_field_attributes_cross_repo_task(tmp_path):
    repo_a, repo_b = _two_repos(tmp_path)
    repos = [
        {"name": "repo-a", "path": str(repo_a), "plans": "docs/superpowers/plans/*.md"},
        {"name": "repo-b", "path": str(repo_b), "plans": "docs/superpowers/plans/*.md"},
    ]
    ga = tk.scan_repo(
        repos[0],
        {},
        tmp_path / "runs",
        str(tmp_path / "store"),
        run=fake_git([]),
        repos=repos,
    )
    gb = tk.scan_repo(
        repos[1],
        {},
        tmp_path / "runs",
        str(tmp_path / "store"),
        run=fake_git(["x: cross (test: unit)"]),
        repos=repos,
    )
    assert {t["key"] for t in ga["tasks"]} == {"TA"}
    assert {t["key"] for t in gb["tasks"]} == {"TB", "T1"}
    by = {t["key"]: t for t in gb["tasks"]}
    assert by["T1"]["state"] == "landed"  # landed by B's own git log
    assert by["TB"]["state"] == "ready"


def test_board_graph_excludes_cross_repo_task(tmp_path, monkeypatch):
    monkeypatch.setattr(tk, "run", fake_git([]))
    root = tmp_path / "root"
    (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans" / "board.md").write_text(
        "### T1 (code, S) — elsewhere\n\n"
        "**dependsOn:** none\n"
        "**repo:** otherrepo\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: cross (test: unit)`\n\n"
        "### TA (code, S) — here\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** a2.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: own (test: unit)`\n"
    )
    block = tk.render_board_block(tk.board_graph(str(root)))
    assert "T1" not in block and "TA" in block


def test_board_graph_defers_cross_repo_dependent(tmp_path, monkeypatch):
    # The board is tree-only: a task whose dependsOn names a key attributed to
    # another repo can't be scheduled here, so it is deferred to the session
    # brief (never scheduled) and the header says so.
    monkeypatch.setattr(tk, "run", fake_git([]))
    root = tmp_path / "root"
    (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans" / "board.md").write_text(
        "### PB0 (code, S) — runs in gaming\n\n"
        "**dependsOn:** none\n"
        "**repo:** gaming\n"
        "**touches:** flake.nix\n"
        "**acceptance:** flake-check\n"
        "**commit subject:** `gaming: relock (test: flake-check)`\n\n"
        "### PB1 (code, S) — depends on it\n\n"
        "**dependsOn:** PB0\n"
        "**touches:** flake.nix\n"
        "**acceptance:** flake-check\n"
        "**commit subject:** `host: bump (test: flake-check)`\n\n"
        "### TA (code, S) — here and ready\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: own (test: unit)`\n"
    )
    g = tk.board_graph(str(root))
    by = {t["key"]: t for t in g["repos"][0]["tasks"]}
    assert by["PB1"]["state"] == "deferred-to-brief"
    block = tk.render_board_block(g)
    assert "PB1" not in block and "TA" in block
    assert block.startswith(
        "**Queued (derived from this tree; tasks whose dependencies run in other "
        "repos, and in-flight state, are in the session brief).** "
    )


def test_task_status_withdrawn_and_unknown_key(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "p.md").write_text(
        "### T1 (code, S) — withdrawn\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t1 (test: unit)`\n\n"
        "### T2 (code, S) — stays\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** b.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t2 (test: unit)`\n"
    )
    # A second plan whose ready T3 shares T1's touch path: the withdrawn T1 must
    # be excluded from conflicts even across plans (MINOR 5 — the old single-plan
    # fixture made `conflicts == []` vacuous).
    (repo / "docs" / "superpowers" / "plans" / "q.md").write_text(
        "### T3 (code, S) — ready, shares T1's touch\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t3 (test: unit)`\n"
    )
    task_status = {
        ("repo", "p.md", "T1"): {
            "status": "withdrawn",
            "note": "by decision",
            "decided": "2026-09-05",
        }
    }
    g = tk.scan_repo(
        {"name": "repo", "path": str(repo), "plans": "docs/superpowers/plans/*.md"},
        {},
        tmp_path / "runs",
        str(tmp_path / "store"),
        run=fake_git([]),
        task_status=task_status,
    )
    by = {t["key"]: t for t in g["tasks"]}
    assert by["T1"]["state"] == "withdrawn"
    assert by["T2"]["state"] == "ready"
    assert by["T3"]["state"] == "ready"
    assert tk.waves(g) == [["T2", "T3"]]
    assert tk.conflicts(g) == []  # T1 (withdrawn) shares a.py with T3 but is excluded
    md = tk.render_brief({"generated": "t", "repos": [g]})
    assert "**Withdrawn/parked:** repo/T1" in md
    assert md.count("repo/T1") == 1
    graph = {
        "generated": "t",
        "repos": [g],
        "task_status": {
            ("repo", "p.md", "T1"): {"status": "withdrawn"},
            ("repo", "p.md", "NOPE"): {"status": "withdrawn"},
        },
    }
    errs = tk.check(graph)
    assert "tasks: task-status names unknown key repo/p.md/NOPE" in errs
    assert not any("repo/p.md/T1" in e for e in errs)


def _fake_git_by_repo(mapping):
    """A fake `run` that returns per-repo `git log` subjects keyed by the repo
    directory's basename (the `-C` argument), so a cross-repo dependency can be
    resolved against the attributed repo's own history."""

    def run(argv, timeout=30.0):
        repo_path = None
        for i, arg in enumerate(argv):
            if arg == "-C":
                repo_path = argv[i + 1]
                break
        name = pathlib.Path(repo_path).name if repo_path else ""
        subjects = mapping.get(name, [])

        class R:
            returncode = 0
            stdout = "\n".join(subjects) + "\n"
            stderr = ""

        return R()

    return run


def _cross_dep_fixture(tmp_path):
    """repo-a's plan defines T9 (attributed to repo-b) and AA1 (dependsOn T9);
    repo-b's plan defines its own ZZ9."""
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    for r in (repo_a, repo_b):
        (r / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo_a / "docs" / "superpowers" / "plans" / "a.md").write_text(
        "### T9 (code, S) — runs in B\n\n"
        "**dependsOn:** none\n"
        "**repo:** repo-b\n"
        "**touches:** b.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t9 (test: unit)`\n\n"
        "### AA1 (code, S) — depends on the cross-repo task\n\n"
        "**dependsOn:** T9\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: aa1 (test: unit)`\n"
    )
    (repo_b / "docs" / "superpowers" / "plans" / "b.md").write_text(
        "### ZZ9 (code, S) — own b\n\n"
        "**dependsOn:** none\n"
        "**touches:** z.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: zz9 (test: unit)`\n"
    )
    return [
        {"name": "repo-a", "path": str(repo_a), "plans": "docs/superpowers/plans/*.md"},
        {"name": "repo-b", "path": str(repo_b), "plans": "docs/superpowers/plans/*.md"},
    ]


def test_cross_repo_dep_resolves_via_attributed_repo(tmp_path):
    repos = _cross_dep_fixture(tmp_path)
    runs = tmp_path / "runs"
    store = str(tmp_path / "store")

    landed = _fake_git_by_repo({"repo-a": [], "repo-b": ["x: t9 (test: unit)"]})
    ga = tk.scan_repo(repos[0], {}, runs, store, run=landed, repos=repos)
    by = {t["key"]: t for t in ga["tasks"]}
    assert by["AA1"]["state"] == "ready"  # T9 is landed in its attributed repo

    not_landed = _fake_git_by_repo({"repo-a": [], "repo-b": []})
    ga2 = tk.scan_repo(repos[0], {}, runs, store, run=not_landed, repos=repos)
    by2 = {t["key"]: t for t in ga2["tasks"]}
    assert by2["AA1"]["state"] == "blocked"
    assert by2["AA1"]["detail"] == "T9"


def test_resolved_elsewhere_feeds_waves_and_brief(tmp_path):
    # The G11b defect: derive_status calls PB1 ready once gaming lands PB0, but
    # waves recomputes satisfaction from this repo's own landed set and drops
    # PB1, so "PB1 ready" and "nothing queued" are true at once. resolved_elsewhere
    # must be published and consumed by the scheduler.
    nixos = tmp_path / "nixos-agent-env"
    gaming = tmp_path / "gaming"
    for r in (nixos, gaming):
        (r / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (nixos / "docs" / "superpowers" / "plans" / "operator-items.md").write_text(
        "### PB0 (code, S) — gaming relock\n\n"
        "**dependsOn:** none\n"
        "**repo:** gaming\n"
        "**touches:** flake.nix\n"
        "**acceptance:** flake-check\n"
        "**commit subject:** `gaming: relock (test: flake-check)`\n\n"
        "### PB1 (code, S) — host follows\n\n"
        "**dependsOn:** PB0\n"
        "**touches:** flake.nix\n"
        "**acceptance:** flake-check\n"
        "**commit subject:** `host: bump (test: flake-check)`\n"
    )
    (gaming / "docs" / "superpowers" / "plans" / "g.md").write_text(
        "# no typed headings here\n"
    )
    repos = [
        {
            "name": "nixos-agent-env",
            "path": str(nixos),
            "plans": "docs/superpowers/plans/*.md",
        },
        {"name": "gaming", "path": str(gaming), "plans": "docs/superpowers/plans/*.md"},
    ]
    run = _fake_git_by_repo(
        {"nixos-agent-env": [], "gaming": ["gaming: relock (test: flake-check)"]}
    )
    gn = tk.scan_repo(
        repos[0], {}, tmp_path / "runs", str(tmp_path / "store"), run=run, repos=repos
    )
    by = {t["key"]: t for t in gn["tasks"]}
    assert by["PB1"]["state"] == "ready"  # the state half
    assert tk.waves(gn) == [["PB1"]]  # the scheduling half (the defect)
    md = tk.render_brief({"generated": "t", "repos": [gn]})
    assert "**Next wave** — nixos-agent-env: PB1(any)" in md
    assert gn["resolved_elsewhere"] == [("gaming", "PB0")]  # (repo, root) pairs
    assert tk.seat_groups(gn, tk.waves(gn)[0]) == ['"PB1"']
    assert {a["key"] for a in tk.factory_args(gn, "operator-items.md")} == {"PB1"}


def test_check_rejects_unconfigured_repo_value(tmp_path):
    # MINOR 2: a `**repo:**` value repos.toml does not configure is a silent
    # black hole — the task vanishes from every graph and its dependent blocks
    # forever. `check` must refuse it.
    repo_a = tmp_path / "repo-a"
    (repo_a / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo_a / "docs" / "superpowers" / "plans" / "a.md").write_text(
        "### T1 (code, S) — typo repo\n\n"
        "**dependsOn:** none\n"
        "**repo:** dsh-harnes\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t1 (test: unit)`\n"
    )
    repos = [
        {"name": "repo-a", "path": str(repo_a), "plans": "docs/superpowers/plans/*.md"}
    ]
    ga = tk.scan_repo(
        repos[0],
        {},
        tmp_path / "runs",
        str(tmp_path / "store"),
        run=fake_git([]),
        repos=repos,
    )
    errs = tk.check({"generated": "t", "repos": [ga]})
    assert any(
        "tasks: repo-a/T1 repo: dsh-harnes not in docs/ledger/repos.toml" in e
        for e in errs
    )


def test_check_rejects_dep_defined_only_in_other_repo(tmp_path):
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    for r in (repo_a, repo_b):
        (r / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo_a / "docs" / "superpowers" / "plans" / "a.md").write_text(
        "### AA2 (code, S) — depends on a key only B defines\n\n"
        "**dependsOn:** ZZ9\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: aa2 (test: unit)`\n"
    )
    (repo_b / "docs" / "superpowers" / "plans" / "b.md").write_text(
        "### ZZ9 (code, S) — own b\n\n"
        "**dependsOn:** none\n"
        "**touches:** z.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: zz9 (test: unit)`\n"
    )
    repos = [
        {"name": "repo-a", "path": str(repo_a), "plans": "docs/superpowers/plans/*.md"},
        {"name": "repo-b", "path": str(repo_b), "plans": "docs/superpowers/plans/*.md"},
    ]
    ga = tk.scan_repo(
        repos[0],
        {},
        tmp_path / "runs",
        str(tmp_path / "store"),
        run=fake_git([]),
        repos=repos,
    )
    gb = tk.scan_repo(
        repos[1],
        {},
        tmp_path / "runs",
        str(tmp_path / "store"),
        run=fake_git([]),
        repos=repos,
    )
    errs = tk.check({"generated": "t", "repos": [ga, gb]})
    # ZZ9 lives only in repo-b's own plan files and was never redirected here:
    # the unknown-key rule stays per repo, so AA2's edge is refused.
    assert any("repo-a/AA2 dependsOn ZZ9: unknown key" in e for e in errs)


def test_check_accepts_dep_redirected_to_other_repo(tmp_path):
    # The M7b regression: a dependsOn naming a key that is typed in THIS repo's
    # plan but `**repo:**`-redirected elsewhere must pass `check`, and resolve
    # against the attributed repo's landing (live-shaped PB1 -> PB0).
    nixos = tmp_path / "nixos-agent-env"
    gaming = tmp_path / "gaming"
    for r in (nixos, gaming):
        (r / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (nixos / "docs" / "superpowers" / "plans" / "operator-items.md").write_text(
        "### PB0 (code, S) — gaming relock\n\n"
        "**dependsOn:** none\n"
        "**repo:** gaming\n"
        "**touches:** flake.nix\n"
        "**acceptance:** flake-check\n"
        "**commit subject:** `gaming: relock (test: flake-check)`\n\n"
        "### PB1 (code, S) — host follows\n\n"
        "**dependsOn:** PB0\n"
        "**touches:** flake.nix\n"
        "**acceptance:** flake-check\n"
        "**commit subject:** `host: bump (test: flake-check)`\n"
    )
    (gaming / "docs" / "superpowers" / "plans" / "g.md").write_text(
        "# no typed headings here\n"
    )
    repos = [
        {
            "name": "nixos-agent-env",
            "path": str(nixos),
            "plans": "docs/superpowers/plans/*.md",
        },
        {"name": "gaming", "path": str(gaming), "plans": "docs/superpowers/plans/*.md"},
    ]
    run = _fake_git_by_repo(
        {"nixos-agent-env": [], "gaming": ["gaming: relock (test: flake-check)"]}
    )
    gn = tk.scan_repo(
        repos[0], {}, tmp_path / "runs", str(tmp_path / "store"), run=run, repos=repos
    )
    gg = tk.scan_repo(
        repos[1], {}, tmp_path / "runs", str(tmp_path / "store"), run=run, repos=repos
    )
    errs = tk.check({"generated": "t", "repos": [gn, gg]})
    assert not any("dependsOn PB0" in e for e in errs)
    by = {t["key"]: t for t in gn["tasks"]}
    assert by["PB1"]["state"] == "ready"  # PB0 landed under gaming


def test_check_rejects_unknown_status_value(tmp_path):
    repo = tmp_path / "repo"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "p.md").write_text(
        "### T1 (code, S) — a task\n\n"
        "**dependsOn:** none\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t1 (test: unit)`\n"
    )
    g = tk.scan_repo(
        {"name": "repo", "path": str(repo), "plans": "docs/superpowers/plans/*.md"},
        {},
        tmp_path / "runs",
        str(tmp_path / "store"),
        run=fake_git([]),
    )
    graph = {
        "generated": "t",
        "repos": [g],
        "task_status": {("repo", "p.md", "T1"): {"status": "withdrawnn"}},
    }
    errs = tk.check(graph)
    assert any("unknown status withdrawnn" in e for e in errs)


def test_states_include_withdrawn_and_parked_in_brief(tmp_path):
    assert "withdrawn" in tk.STATES and "parked" in tk.STATES
    assert tk.STATES.index("withdrawn") > tk.STATES.index("blocked")
    assert tk.STATES.index("parked") > tk.STATES.index("withdrawn")

    repo = tmp_path / "repo"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "p.md").write_text(
        "### T1 (code, S) — withdrawn\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t1 (test: unit)`\n\n"
        "### T2 (code, S) — parked\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** b.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t2 (test: unit)`\n\n"
        "### T3 (code, S) — ready\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** c.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t3 (test: unit)`\n"
    )
    task_status = {
        ("repo", "p.md", "T1"): {"status": "withdrawn", "note": "", "decided": ""},
        ("repo", "p.md", "T2"): {"status": "parked", "note": "", "decided": ""},
    }
    g = tk.scan_repo(
        {"name": "repo", "path": str(repo), "plans": "docs/superpowers/plans/*.md"},
        {},
        tmp_path / "runs",
        str(tmp_path / "store"),
        run=fake_git([]),
        task_status=task_status,
    )
    md = tk.render_brief({"generated": "t", "repos": [g]})
    header, row = [l for l in md.splitlines() if l.startswith("| repo |")]
    assert "| withdrawn |" in header and "| parked |" in header
    assert "| deferred-to-brief |" in header
    assert row == "| repo | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |"


def test_board_graph_exposes_task_status_and_omits_withdrawn(tmp_path, monkeypatch):
    monkeypatch.setattr(tk, "run", fake_git([]))
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans" / "board.md").write_text(
        "### W1 (code, S) — withdrawn\n\n"
        "**dependsOn:** none\n"
        "**touches:** w.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: w1 (test: unit)`\n\n"
        "### K1 (code, S) — kept\n\n"
        "**dependsOn:** none\n"
        "**touches:** k.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: k1 (test: unit)`\n"
    )
    (root / "docs" / "ledger" / "task-status.toml").write_text(
        '[[task]]\nrepo = "root"\nplan = "board.md"\nkey = "W1"\n'
        'status = "withdrawn"\nnote = "n/a"\ndecided = "2026-09-05"\n'
    )
    g = tk.board_graph(str(root))
    assert ("root", "board.md", "W1") in g["task_status"]
    block = tk.render_board_block(g)
    assert "W1" not in block and "K1" in block


RUNNING_PLAN = """# Running fixture plan (a task with a live seat log reads running)

### K1 (code, S) — a task with a live seat log

**dependsOn:** none

**touches:** a.py
**acceptance:** unit
**commit subject:** `x: k1 (test: unit)`
"""


def write_log(runs_dir, run, key):
    d = runs_dir / run
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{key}.log").write_text(
        "dsh-openrouter: deepseek/deepseek-v4-pro-0813 … workspace /some/where\n"
    )


def test_read_results_detects_running_log(tmp_path):
    runs = tmp_path / "runs"
    make_workspace(tmp_path, "r1/K1", "nixos-agent-env")
    write_log(runs, "r1", "K1")
    res = tk.read_results(runs)
    assert res[("nixos-agent-env", "K1")]["status"] == "running"
    assert res[("nixos-agent-env", "K1")]["run"] == "r1"


def test_read_results_ignores_running_log_without_workspace(tmp_path):
    runs = tmp_path / "runs"
    write_log(runs, "r1", "K2")  # no workspace clone -> not evidence
    assert not any(k[1] == "K2" for k in tk.read_results(runs))


def test_running_log_with_result_is_ran(tmp_path):
    runs = tmp_path / "runs"
    ws = make_workspace(tmp_path, "r1/K1", "nixos-agent-env")
    write_result(runs, "r1", "K1", "done", ws)
    write_log(runs, "r1", "K1")  # the seat finished: result wins over the log
    res = tk.read_results(runs)
    assert res[("nixos-agent-env", "K1")]["status"] == "done"


def running_graph(tmp_path):
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "p.md").write_text(RUNNING_PLAN)
    runs = tmp_path / "runs"
    make_workspace(tmp_path, "r1/K1", "nixos-agent-env")
    write_log(runs, "r1", "K1")
    return tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        {},
        runs,
        str(tmp_path / "store"),
        run=fake_git([]),
    )


def test_running_task_not_scheduled_and_counted(tmp_path):
    g = running_graph(tmp_path)
    by = {t["key"]: t for t in g["tasks"]}
    assert by["K1"]["state"] == "running"
    assert "run=r1" in by["K1"]["detail"]
    assert tk.waves(g) == []  # never scheduled
    assert tk.conflicts(g) == []  # never conflicting
    md = tk.render_brief({"generated": "t", "repos": [g]})
    assert "**Running:** nixos-agent-env/K1" in md
    header = next(l for l in md.splitlines() if l.startswith("| repo |"))
    assert "| running |" in header
    row = next(l for l in md.splitlines() if l.startswith("| nixos-agent-env |"))
    assert "| 0 | 0 | 0 | 0 | 1 | 0 |" in row  # running == 1


def test_derive_status_running_between_review_and_result():
    plan = tk.parse_plan(FIXTURES / "typed.md")
    by = {t["key"]: t for t in plan["tasks"]}
    running = {"E3": {"status": "running", "run": "r1"}}
    # running beats a result (rule 3) and ready
    st, detail = tk.derive_status(by["E3"], set(), {}, {}, {}, set(), running=running)
    assert st == "running" and "run=r1" in detail
    # a review (rule 2) still outranks running
    reviews = {"E3": {"verdict": "APPROVED", "run": "ev1", "file": "q"}}
    st2, _ = tk.derive_status(by["E3"], set(), reviews, {}, {}, set(), running=running)
    assert st2 == "approved"


def test_wave_lines_one_per_wave(tmp_path):
    g = repo_with(
        tmp_path,
        ["typed.md"],
        landed=["evidence: the store (test: evidence-unit, lint)"],
    )
    assert tk.wave_lines(g, plan="typed.md") == ['"E3" "E7"', '"D1"']


def test_wave_structure_json_shape(tmp_path):
    g = repo_with(
        tmp_path,
        ["typed.md"],
        landed=["evidence: the store (test: evidence-unit, lint)"],
    )
    assert tk.wave_structure(g, plan="typed.md") == [[["E3"], ["E7"]], [["D1"]]]


def test_main_waves_next_json_and_default(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        tk, "run", fake_git(["evidence: the store (test: evidence-unit, lint)"])
    )
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "typed.md").write_text(
        (FIXTURES / "typed.md").read_text()
    )
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "nixos-agent-env"\npath = "{repo}"\n'
    )
    base = [
        "--root",
        str(root),
        "--runs-dir",
        str(tmp_path / "none"),
        "--store",
        str(tmp_path / "none"),
        "waves",
        "--repo",
        "nixos-agent-env",
        "--plan",
        "typed.md",
    ]
    rc = tk.main(base + ["--next"])
    assert rc == 0 and capsys.readouterr().out == '"E3" "E7"\n'
    rc = tk.main(base + ["--json"])
    assert rc == 0 and json.loads(capsys.readouterr().out) == [
        [["E3"], ["E7"]],
        [["D1"]],
    ]
    rc = tk.main(base)
    assert rc == 0 and capsys.readouterr().out == '"E3" "E7"\n"D1"\n'


# --- G12b: per-key liveness, stale logs, imported-task deps, deferred-to-brief ---


def _set_mtime(path, epoch):
    os.utime(path, (epoch, epoch))


def test_read_results_newer_result_beats_older_log(tmp_path):
    # (a) r1/K1.log (old run) + r2/K1.result (newer run) -> the newer run's
    # result wins: the key reads `ran`, never `running` (G12's defect).
    runs = tmp_path / "runs"
    make_workspace(tmp_path, "r1/K1", "nixos-agent-env")
    write_log(runs, "r1", "K1")
    ws = make_workspace(tmp_path, "r2/K1", "nixos-agent-env")
    write_result(runs, "r2", "K1", "done", ws)
    _set_mtime(runs / "r1", 1_600_000_000)
    _set_mtime(runs / "r2", 1_600_000_000 + 10)
    res = tk.read_results(runs)
    assert res[("nixos-agent-env", "K1")]["status"] == "done"
    assert res[("nixos-agent-env", "K1")]["run"] == "r2"


def test_read_results_stale_log_is_not_running(tmp_path):
    # (c) a log older than `stale-after` seconds is not evidence of liveness:
    # read_results returns no entry, so the key falls through to rules 3-5.
    runs = tmp_path / "runs"
    make_workspace(tmp_path, "r1/K1", "nixos-agent-env")
    write_log(runs, "r1", "K1")
    old = 1_600_000_000  # ~2020: far older than any live session's clock
    _set_mtime(runs / "r1" / "K1.log", old)
    _set_mtime(runs / "r1", old)
    assert not any(k[1] == "K1" for k in tk.read_results(runs))


def test_stale_log_key_reads_ready(tmp_path):
    # (c) at the graph level: the killed run is schedulable again (ready),
    # never `running`.
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "p.md").write_text(RUNNING_PLAN)
    runs = tmp_path / "runs"
    make_workspace(tmp_path, "r1/K1", "nixos-agent-env")
    write_log(runs, "r1", "K1")
    old = 1_600_000_000
    _set_mtime(runs / "r1" / "K1.log", old)
    _set_mtime(runs / "r1", old)
    g = tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        {},
        runs,
        str(tmp_path / "store"),
        run=fake_git([]),
    )
    by = {t["key"]: t for t in g["tasks"]}
    assert by["K1"]["state"] == "ready"


def test_running_task_absent_from_conflicts_across_plans(tmp_path):
    # (d) a running task whose touches overlap another plan's ready task is
    # never scheduled and never conflicting: two plans, non-vacuous.
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "p.md").write_text(RUNNING_PLAN)  # K1 touches a.py
    (plans / "q.md").write_text(
        "### T2 (code, S) — ready, shares a.py\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: t2 (test: unit)`\n"
    )
    runs = tmp_path / "runs"
    make_workspace(tmp_path, "r1/K1", "nixos-agent-env")
    write_log(runs, "r1", "K1")
    g = tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        {},
        runs,
        str(tmp_path / "store"),
        run=fake_git([]),
    )
    by = {t["key"]: t for t in g["tasks"]}
    assert by["K1"]["state"] == "running"
    assert by["T2"]["state"] == "ready"
    assert tk.conflicts(g) == []  # K1 (running) overlaps T2's a.py but is excluded
    assert tk.waves(g) == [["T2"]]  # K1 never scheduled


def test_chain_running_member_outranks_root_review(tmp_path):
    # (e) the last chain member's live log outranks the ROOT's rejected review:
    # the root reads `running`, not `rejected`.
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "chain.md").write_text(CHAIN_PLAN)
    write_review(
        repo, "opus-review-a.md", "# Opus gate — seat run ev1, task G1 — REJECTED"
    )
    runs = tmp_path / "runs"
    make_workspace(tmp_path, "r1/G1b", "nixos-agent-env")
    write_log(runs, "r1", "G1b")
    g = tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        {},
        runs,
        str(tmp_path / "store"),
        run=fake_git([]),
    )
    by = {t["key"]: t for t in g["tasks"]}
    assert by["G1"]["state"] == "running"
    assert "G1b" in by["G1"]["detail"]


def test_waves_next_nothing_schedulable_prints_zero_bytes(
    tmp_path, monkeypatch, capsys
):
    # (f) `--next` with nothing schedulable prints exactly zero bytes (no
    # trailing blank line), so a dispatcher sees an empty stdout.
    monkeypatch.setattr(tk, "run", fake_git(["x: k1 (test: unit)"]))  # K1 landed
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "p.md").write_text(RUNNING_PLAN)
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "nixos-agent-env"\npath = "{repo}"\n'
    )
    rc = tk.main(
        [
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "none"),
            "--store",
            str(tmp_path / "none"),
            "waves",
            "--repo",
            "nixos-agent-env",
            "--next",
        ]
    )
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_running_elsewhere_dependency_not_satisfied(tmp_path):
    # (g) a dependency that is `running` (not landed) in its attributed repo is
    # NOT satisfied: the dependent stays blocked and never enters a wave.
    nixos = tmp_path / "nixos-agent-env"
    gaming = tmp_path / "gaming"
    for r in (nixos, gaming):
        (r / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (nixos / "docs" / "superpowers" / "plans" / "operator-items.md").write_text(
        "### PB0 (code, S) — gaming relock\n\n"
        "**dependsOn:** none\n"
        "**repo:** gaming\n"
        "**touches:** flake.nix\n"
        "**acceptance:** flake-check\n"
        "**commit subject:** `gaming: relock (test: flake-check)`\n\n"
        "### PB1 (code, S) — host follows\n\n"
        "**dependsOn:** PB0\n"
        "**touches:** flake.nix\n"
        "**acceptance:** flake-check\n"
        "**commit subject:** `host: bump (test: flake-check)`\n"
    )
    (gaming / "docs" / "superpowers" / "plans" / "g.md").write_text(
        "### PB0 (code, S) — gaming relock\n\n"
        "**dependsOn:** none\n"
        "**touches:** flake.nix\n"
        "**acceptance:** flake-check\n"
        "**commit subject:** `gaming: relock (test: flake-check)`\n"
    )
    repos = [
        {
            "name": "nixos-agent-env",
            "path": str(nixos),
            "plans": "docs/superpowers/plans/*.md",
        },
        {"name": "gaming", "path": str(gaming), "plans": "docs/superpowers/plans/*.md"},
    ]
    runs = tmp_path / "runs"
    make_workspace(tmp_path, "r1/PB0", "gaming")
    write_log(runs, "r1", "PB0")  # PB0 running in gaming, not landed
    not_landed = _fake_git_by_repo({"nixos-agent-env": [], "gaming": []})
    gn = tk.scan_repo(
        repos[0], {}, runs, str(tmp_path / "store"), run=not_landed, repos=repos
    )
    by = {t["key"]: t for t in gn["tasks"]}
    assert by["PB1"]["state"] == "blocked"
    assert "PB0" in by["PB1"]["detail"]
    assert tk.waves(gn) == []
    assert gn["resolved_elsewhere"] == []


def _import_fixture(tmp_path):
    """repo-a defines L1 (local, landed) and X1 (attributed to repo-b, dependsOn
    L1); repo-b defines its own ZB. X1 is imported into repo-b's graph."""
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    for r in (repo_a, repo_b):
        (r / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo_a / "docs" / "superpowers" / "plans" / "a.md").write_text(
        "### L1 (code, S) — local to A\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: l1 (test: unit)`\n\n"
        "### X1 (code, S) — runs in B, depends on A's L1\n\n"
        "**dependsOn:** L1\n"
        "**repo:** repo-b\n"
        "**touches:** b.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: x1 (test: unit)`\n"
    )
    (repo_b / "docs" / "superpowers" / "plans" / "b.md").write_text(
        "### ZB (code, S) — own b\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** z.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: zb (test: unit)`\n"
    )
    return [
        {"name": "repo-a", "path": str(repo_a), "plans": "docs/superpowers/plans/*.md"},
        {"name": "repo-b", "path": str(repo_b), "plans": "docs/superpowers/plans/*.md"},
    ]


def test_imported_task_dep_resolves_against_defining_repo(tmp_path):
    # MAJOR 2 (G11r gate): an imported task's dependsOn resolves against its
    # DEFINING repo's resolvable roots, and its landing is judged where the dep
    # is attributed — X1 (repo-b) dependsOn L1 (local to repo-a, landed) -> ready,
    # and `check` is clean (no spurious "unknown key").
    repos = _import_fixture(tmp_path)
    run = _fake_git_by_repo({"repo-a": ["x: l1 (test: unit)"], "repo-b": []})
    ga = tk.scan_repo(
        repos[0], {}, tmp_path / "runs", str(tmp_path / "store"), run=run, repos=repos
    )
    gb = tk.scan_repo(
        repos[1], {}, tmp_path / "runs", str(tmp_path / "store"), run=run, repos=repos
    )
    assert {t["key"] for t in gb["tasks"]} == {"ZB", "X1"}
    by = {t["key"]: t for t in gb["tasks"]}
    assert by["X1"]["state"] == "ready"
    errs = tk.check({"generated": "t", "repos": [ga, gb]})
    assert not any("dependsOn L1" in e for e in errs)


def test_imported_task_dep_blocked_when_foreign_local_not_landed(tmp_path):
    # The mirror: same fixture but L1 not landed -> X1 blocked (the edge is still
    # resolved, so `check` stays clean; only the landing differs).
    repos = _import_fixture(tmp_path)
    run = _fake_git_by_repo({"repo-a": [], "repo-b": []})
    ga = tk.scan_repo(
        repos[0], {}, tmp_path / "runs", str(tmp_path / "store"), run=run, repos=repos
    )
    gb = tk.scan_repo(
        repos[1], {}, tmp_path / "runs", str(tmp_path / "store"), run=run, repos=repos
    )
    by = {t["key"]: t for t in gb["tasks"]}
    assert by["X1"]["state"] == "blocked"
    assert by["X1"]["detail"] == "L1"
    errs = tk.check({"generated": "t", "repos": [ga, gb]})
    assert not any("dependsOn L1" in e for e in errs)


def test_states_include_deferred_to_brief(tmp_path):
    assert "deferred-to-brief" in tk.STATES
    # It is a board-only vocabulary word, listed after the schedulable states and
    # before the withdrawn/parked terminal states.
    assert tk.STATES.index("deferred-to-brief") > tk.STATES.index("blocked")
    assert tk.STATES.index("deferred-to-brief") < tk.STATES.index("withdrawn")


# --- G12r: satisfaction keyed by (repo, root); minors folded ---


def test_satisfaction_keyed_by_repo_not_bare_root(tmp_path):
    # MAJOR 1 (G12b gate): the satisfied set is (repo, chain root) pairs, never a
    # bare root. repo-a lands its own L1 and defines X1 (repo-b, dependsOn L1);
    # repo-b defines its OWN unrelated L1 (not landed) and BL (dependsOn L1).
    # A's landed L1 must satisfy X1 but not B's L1: BL stays blocked, and B's
    # waves put B's L1 first, then BL, with X1 (whose dep is A's landed L1) right
    # after. Mutation: fold the resolution back into one flat set -> BL reads
    # `ready` and shares a wave with L1 -> this test fails.
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    for r in (repo_a, repo_b):
        (r / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo_a / "docs" / "superpowers" / "plans" / "a.md").write_text(
        "### L1 (code, S) — A's own, landed\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** a.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: l1 (test: unit)`\n\n"
        "### X1 (code, S) — runs in B, depends on A's L1\n\n"
        "**dependsOn:** L1\n"
        "**repo:** repo-b\n"
        "**touches:** b.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: x1 (test: unit)`\n"
    )
    (repo_b / "docs" / "superpowers" / "plans" / "b.md").write_text(
        "### L1 (code, S) — B's own, distinct, not landed\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** b2.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: b-l1 (test: unit)`\n\n"
        "### BL (code, S) — depends on B's L1\n\n"
        "**dependsOn:** L1\n"
        "**touches:** b3.py\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: bl (test: unit)`\n"
    )
    repos = [
        {"name": "repo-a", "path": str(repo_a), "plans": "docs/superpowers/plans/*.md"},
        {"name": "repo-b", "path": str(repo_b), "plans": "docs/superpowers/plans/*.md"},
    ]
    run = _fake_git_by_repo({"repo-a": ["x: l1 (test: unit)"], "repo-b": []})
    ga = tk.scan_repo(
        repos[0], {}, tmp_path / "runs", str(tmp_path / "store"), run=run, repos=repos
    )
    gb = tk.scan_repo(
        repos[1], {}, tmp_path / "runs", str(tmp_path / "store"), run=run, repos=repos
    )
    by = {t["key"]: t for t in gb["tasks"]}
    assert by["BL"]["state"] == "blocked"
    assert "L1" in by["BL"]["detail"]
    assert by["X1"]["state"] == "ready"
    assert tk.waves(gb) == [["L1", "X1"], ["BL"]]
    # resolved_elsewhere is keyed by (repo, root); A's L1 never leaks to B's L1.
    assert gb["resolved_elsewhere"] == [("repo-a", "L1")]
    errs = tk.check({"generated": "t", "repos": [ga, gb]})
    assert errs == []


def test_stale_newest_log_does_not_discard_older_result(tmp_path):
    # MINOR 2: a stale log in the NEWEST run dir must not discard a genuine
    # .result from an older run — rule 3 stays reachable, the newest .result wins.
    runs = tmp_path / "runs"
    ws = make_workspace(tmp_path, "r1/K1", "nixos-agent-env")
    write_result(runs, "r1", "K1", "done", ws)
    make_workspace(tmp_path, "r2/K1", "nixos-agent-env")
    write_log(runs, "r2", "K1")
    _set_mtime(runs / "r1", 1_600_000_000)
    _set_mtime(runs / "r2", 1_600_000_000 + 10)  # newer run dir
    _set_mtime(runs / "r2" / "K1.log", 1_600_000_000)  # back-dated past stale_after
    res = tk.read_results(runs)
    assert res[("nixos-agent-env", "K1")]["status"] == "done"
    assert res[("nixos-agent-env", "K1")]["run"] == "r1"


def test_result_with_running_status_is_ran(tmp_path):
    # MINOR 5: a .result whose block says `status=running` is the seat's final
    # result (`ran`), never a live log.
    repo = tmp_path / "nixos-agent-env"
    plans = repo / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True)
    (plans / "p.md").write_text(RUNNING_PLAN)
    runs = tmp_path / "runs"
    ws = make_workspace(tmp_path, "r1/K1", "nixos-agent-env")
    write_result(runs, "r1", "K1", "running", ws)
    g = tk.scan_repo(
        {
            "name": "nixos-agent-env",
            "path": str(repo),
            "plans": "docs/superpowers/plans/*.md",
        },
        {},
        runs,
        str(tmp_path / "store"),
        run=fake_git([]),
    )
    by = {t["key"]: t for t in g["tasks"]}
    assert by["K1"]["state"] == "ran"


def test_malformed_tasks_stale_after_warns_not_crashes(tmp_path, monkeypatch, capsys):
    # MINOR 3: a malformed TASKS_STALE_AFTER falls back to the default with a
    # one-line warning instead of a bare ValueError traceback (including inside
    # `check`).
    monkeypatch.setenv("TASKS_STALE_AFTER", "abc")
    monkeypatch.setattr(tk, "run", fake_git([]))
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "p.md").write_text(RUNNING_PLAN)
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "nixos-agent-env"\npath = "{repo}"\n'
    )
    rc = tk.main(
        [
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "none"),
            "--store",
            str(tmp_path / "none"),
            "check",
        ]
    )
    assert rc == 0
    err = capsys.readouterr().err
    assert "TASKS_STALE_AFTER" in err and "ValueError" not in err


# --- P1: check --draft judges a plan outside the plans directory ---

DRAFTS = HERE.parent / "fixtures" / "drafts"

BASE_PLAN = """### B1 (code, S) — the root

**dependsOn:** none

**touches:** tools/b1.sh
**acceptance:** unit
**commit subject:** `x: b1 (test: unit)`

### B2 (code, S) — the open dependent

**dependsOn:** B1

**touches:** tools/x.sh
**acceptance:** unit
**commit subject:** `x: b2 (test: unit)`
"""

DRAFT_HEADER = """## Global Constraints

Build-only.

## Assumptions

None beyond the house rules.

## Waves

(derived by `evidence tasks`)

## Operator

Nothing to switch.

"""


def draft_root(tmp_path):
    """A `--root` that is itself the repo (this tree): base.md with landed B1
    and open B2, a repos.toml naming it, and a MAP.md whose Checks section lists
    evidence-unit, unit and lint."""
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (root / "docs" / "superpowers" / "plans" / "base.md").write_text(BASE_PLAN)
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "root"\npath = "{root}"\n'
    )
    (root / "docs" / "MAP.md").write_text(
        "# Map\n\n## Checks\n\n- evidence-unit\n- unit\n- lint\n\n## Elsewhere\n"
    )
    return root


def draft_cmd(root, draft_path):
    return [
        "--root",
        str(root),
        "--runs-dir",
        str(root / "no-runs"),
        "--store",
        str(root / "no-store"),
        "check",
        "--draft",
        str(draft_path),
    ]


def test_draft_duplicate_key_across_plans(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "dup-key.md"
    d.write_text((DRAFTS / "dup-key.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "defined in base.md and dup-key.md" in err


def test_draft_unknown_dependency(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "dangling-dep.md"
    d.write_text((DRAFTS / "dangling-dep.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "dependsOn Q9: unknown key" in err


def test_draft_acceptance_name_not_in_map(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "fake-check.md"
    d.write_text((DRAFTS / "fake-check.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "acceptance unit-tests not in docs/MAP.md" in err


def test_draft_glob_touch_is_not_explicit(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "glob-touch.md"
    d.write_text((DRAFTS / "glob-touch.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "touches pkgs/*: glob is not an explicit path" in err


def test_draft_size_l_refused(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "size-l.md"
    d.write_text((DRAFTS / "size-l.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "size L is refused" in err


def test_draft_subject_names_compared_as_a_set(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "subject-mismatch.md"
    d.write_text((DRAFTS / "subject-mismatch.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "differs from acceptance" in err
    # ZA's (test: lint, unit) is the same set as (unit, lint): not an error.
    assert "ZA commit subject" not in err


def test_draft_missing_assumptions_header(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "no-assumptions.md"
    d.write_text((DRAFTS / "no-assumptions.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "draft lacks section Assumptions" in err


def test_draft_sound_prints_waves_and_conflicts(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "sound.md"
    d.write_text((DRAFTS / "sound.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    out, err = capsys.readouterr()
    assert rc == 0 and err == ""
    assert out == f"waves: {json.dumps([[['Z1']], [['Z2']]])}\nconflicts: none\n"


def test_check_reports_probe_grammar_errors(tmp_path, monkeypatch, capsys):
    # A draft whose `**probes:**` block names the malformed shapes turns each
    # into a one-line check error: a bullet without backticks, a duplicate name,
    # a non-numeric bound on a numeric op, a value on a no-value op, an `eq` on a
    # number, a tab in the command, and a lowercase `probe_env` token.
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "probes.md"
    d.write_text(
        "## Global Constraints\n\nBuild-only.\n\n"
        "## Assumptions\n\nNone.\n\n"
        "## Waves\n\n(derived)\n\n"
        "## Operator\n\nNothing.\n\n"
        "### K1 (code, M) — probes\n\n"
        "**touches:** tools/x.sh\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: k1 (test: unit)`\n"
        "**probes:**\n"
        "- nob: just prose :: le 1 :: x\n"
        "- brief: `wc -c` :: le abc :: x\n"
        "- dup: `wc -c` :: le 8000 :: x\n"
        "- dup: `wc -c` :: le 8000 :: x\n"
        "- emptyval: `wc -c` :: empty 3 :: x\n"
        "- eqnum: `wc -c` :: eq 42 :: x\n"
        "- tabbed: `a\tb` :: le 2 :: x\n"
        "**probe_env:** foo=bar\n"
        "\nbody.\n"
    )
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "probes: malformed: - nob: just prose :: le 1 :: x" in err
    assert "probes: duplicate dup" in err
    assert "brief: op le needs a numeric value" in err
    assert "emptyval: op empty takes no value" in err
    assert "eqnum: eq/ne on a number — state a bound (le, ge)" in err
    assert "probe_env: malformed token foo=bar" in err
    assert "probes: malformed: - tabbed:" in err


def test_draft_content_printed_on_draft_conflict(tmp_path, monkeypatch, capsys):
    # A draft whose Z1 touches tools/x.sh conflicts with the open B2 that also
    # touches tools/x.sh; the row is printed with the draft's plan name.
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "sound.md"
    d.write_text(
        DRAFT_HEADER + "### Z1 (code, S) — overlaps the open dependent\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** tools/x.sh\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: z1-overlap (test: unit)`\n"
    )
    rc = tk.main(draft_cmd(root, d))
    out = capsys.readouterr().out
    assert rc == 0
    assert "conflicts: B2 (base.md) × Z1 (sound.md): tools/x.sh ~ tools/x.sh" in out
    assert "conflicts: none" not in out


def test_conflicts_ignore_cross_repo_flake_nix_collision(tmp_path, monkeypatch, capsys):
    # OL1 and SP1 both touch flake.nix as bare strings, but OL1 is attributed
    # to a sibling repo ("other", a second [[repo]] row) with its own
    # flake.nix — a task in ~/flakes/openai-lab writing its flake.nix never
    # collides with a task in ~/nixos-agent-env writing this repo's. Two plan
    # files land in the same scanned repo (the draft is stitched onto it the
    # way `load_draft` really does it): the tracked sp.md (SP1, this repo) and
    # the draft ol.md (OL1, **repo:** other).
    root = draft_root(tmp_path)
    (tmp_path / "other-repo").mkdir()
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "root"\npath = "{root}"\n\n'
        f'[[repo]]\nname = "other"\npath = "{tmp_path / "other-repo"}"\n'
    )
    (root / "docs" / "superpowers" / "plans" / "sp.md").write_text(
        "### SP1 (code, S) — this repo's own flake\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** flake.nix\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: sp1 (test: unit)`\n"
    )
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "ol.md"
    d.write_text(
        DRAFT_HEADER + "### OL1 (code, S) — runs in a sibling flake\n\n"
        "**dependsOn:** none\n\n"
        "**repo:** other\n\n"
        "**touches:** flake.nix\n"
        "**acceptance:** unit\n"
        "**commit subject:** `other: ol1 (test: unit)`\n"
    )
    rc = tk.main(draft_cmd(root, d))
    out = capsys.readouterr().out
    assert rc == 0
    assert out == f"waves: {json.dumps([[['OL1']]])}\nconflicts: none\n"


def test_conflicts_same_repo_flake_nix_still_reported(tmp_path, monkeypatch, capsys):
    # The same fixture minus the cross-repo attribution: OL1 now runs in this
    # same repo as SP1, so their shared flake.nix is a real conflict and the
    # row must still be printed.
    root = draft_root(tmp_path)
    (root / "docs" / "superpowers" / "plans" / "sp.md").write_text(
        "### SP1 (code, S) — this repo's own flake\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** flake.nix\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: sp1 (test: unit)`\n"
    )
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "ol.md"
    d.write_text(
        DRAFT_HEADER + "### OL1 (code, S) — runs in this repo\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** flake.nix\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: ol1 (test: unit)`\n"
    )
    rc = tk.main(draft_cmd(root, d))
    out = capsys.readouterr().out
    assert rc == 0
    assert "conflicts: OL1 (ol.md) × SP1 (sp.md): flake.nix ~ flake.nix" in out
    assert "conflicts: none" not in out


def test_draft_inside_plans_dir_is_a_usage_error(tmp_path, capsys):
    root = draft_root(tmp_path)
    d = root / "docs" / "superpowers" / "plans" / "field.md"
    d.write_text("### Z1 (code, S) — already inside\n\n")
    try:
        tk.main(draft_cmd(root, d))
    except SystemExit as e:
        rc = e.code
    else:
        rc = 0
    err = capsys.readouterr().err
    assert rc == 2
    assert "already under the plans directory" in err


def test_draft_unreadable_is_a_usage_error(tmp_path, capsys):
    root = draft_root(tmp_path)
    missing = tmp_path / "missing.md"
    try:
        tk.main(draft_cmd(root, missing))
    except SystemExit as e:
        rc = e.code
    else:
        rc = 0
    assert rc == 2
    assert "cannot read" in capsys.readouterr().err


def test_draft_no_configured_repo_for_root(tmp_path, capsys):
    root = tmp_path / "orphan"
    (root / "docs" / "ledger").mkdir(parents=True)
    d = tmp_path / "x.md"
    d.write_text("### Z1 (code, S) — a task\n")
    try:
        tk.main(draft_cmd(root, d))
    except SystemExit as e:
        rc = e.code
    else:
        rc = 0
    assert rc == 2
    assert "no configured repo has path" in capsys.readouterr().err


def test_draft_replan_drops_heading(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "base.md"
    d.write_text((DRAFTS / "replan-drops-heading.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "draft drops heading: ### B1 (code, S) — the root" in err


def test_draft_replan_keeps_headings(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(
        tk, "run", fake_git(["x: b1 (test: unit)", "x: b2 (test: unit)"])
    )
    d = tmp_path / "base.md"
    d.write_text((DRAFTS / "replan-keeps-headings.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    out, err = capsys.readouterr()
    assert rc == 0 and err == ""
    assert out == f"waves: {json.dumps([[['B2r']]])}\nconflicts: none\n"


def test_draft_already_landed_same_root_and_different_root(
    tmp_path, monkeypatch, capsys
):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    # a fix round (root B1) reusing B1's landed subject is allowed
    d1 = tmp_path / "b1b.md"
    d1.write_text(
        DRAFT_HEADER + "### B1b (code, S) — the fix round\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** tools/b1b.sh\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: b1 (test: unit)`\n"
    )
    assert tk.main(draft_cmd(root, d1)) == 0
    # the same landed subject on a different chain root is refused
    d2 = tmp_path / "z1.md"
    d2.write_text(
        DRAFT_HEADER + "### Z1 (code, S) — reuses a landed subject\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** tools/zb.sh\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: b1 (test: unit)`\n"
    )
    rc = tk.main(draft_cmd(root, d2))
    err = capsys.readouterr().err
    assert rc == 1
    assert "commit subject already landed: x: b1 (test: unit)" in err


def test_draft_attributed_task_exempt_from_acceptance(tmp_path, capsys):
    root = draft_root(tmp_path)
    d = tmp_path / "media.md"
    d.write_text(
        DRAFT_HEADER + "### M1 (code, S) — runs in another repo\n\n"
        "**dependsOn:** none\n\n"
        "**repo:** media\n\n"
        "**touches:** media.py\n"
        "**acceptance:** comfy-worlds-unit\n"
        "**commit subject:** `media: m1 (test: comfy-worlds-unit)`\n"
    )
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 0
    assert "not in docs/MAP.md" not in err


def test_draft_replan_all_landed_same_root_and_fake_consulted(
    tmp_path, monkeypatch, capsys
):
    # A controlled multi-task house plan re-planned byte-identically: every task's
    # subject is landed (via the fake git), and the same-root exemption saves
    # every one. A fresh Z9 reusing one of those subjects is refused; with the
    # fake returning nothing the same Z9 passes, proving the fake is consulted.
    root = draft_root(tmp_path)
    house = (
        DRAFT_HEADER + "### H1 (code, S) — one\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** h1.sh\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: h-one (test: unit)`\n\n"
        "### H2 (docs, XS) — two\n\n"
        "**dependsOn:** H1\n\n"
        "**touches:** h2.sh\n"
        "**acceptance:** lint\n"
        "**commit subject:** `docs: h-two (test: lint)`\n"
    )
    subjects = ["x: h-one (test: unit)", "docs: h-two (test: lint)"]
    monkeypatch.setattr(tk, "run", fake_git(subjects))
    (root / "docs" / "superpowers" / "plans" / "house.md").write_text(house)
    d = tmp_path / "house.md"
    d.write_text(house)
    rc = tk.main(draft_cmd(root, d))
    assert rc == 0
    z9 = tmp_path / "z9.md"
    z9.write_text(
        DRAFT_HEADER + "### Z9 (code, S) — reuses a landed subject\n\n"
        "**dependsOn:** none\n\n"
        "**touches:** z9.sh\n"
        "**acceptance:** unit\n"
        "**commit subject:** `x: h-one (test: unit)`\n"
    )
    assert tk.main(draft_cmd(root, z9)) == 1
    assert "already landed" in capsys.readouterr().err
    monkeypatch.setattr(tk, "run", fake_git([]))
    assert tk.main(draft_cmd(root, z9)) == 0


def test_draft_duplicate_key_within_one_file(tmp_path, monkeypatch, capsys):
    root = draft_root(tmp_path)
    monkeypatch.setattr(tk, "run", fake_git(["x: b1 (test: unit)"]))
    d = tmp_path / "dup-in-draft.md"
    d.write_text((DRAFTS / "dup-in-draft.md").read_text())
    rc = tk.main(draft_cmd(root, d))
    err = capsys.readouterr().err
    assert rc == 1
    assert "Z1 defined twice in dup-in-draft.md" in err


# --- P3A: the plan-defect ledger, review front-matter blocks, the record line ---

RFIX = HERE.parent / "fixtures" / "reviews"

FMF_LEDGER = "[meta]\nfront_matter_from = 2026-09-07\n"

# The FROZEN 48-row seed (byte-identical to `git show 3937d98:docs/ledger/
# plan-defects.toml`) that the record test asserts exact counts over; the LIVE
# ledger is asserted by SHAPE only, so it may grow without turning the check red.
FROZEN_SEED = HERE.parent / "fixtures" / "ledger" / "plan-defects-seed.toml"
LIVE_LEDGER = HERE.parents[2] / "docs" / "ledger" / "plan-defects.toml"

# The Record line's SHAPE: every tally is `[0-9]+`, no literal count is pinned.
RECORD_SHAPE = re.compile(
    r"^\*\*Record \(7 d\):\*\* ([0-9]+) rej, [0-9]+ plan "
    r"\(vac [0-9]+, miss [0-9]+, under [0-9]+, fact [0-9]+\)$"
)


def _review_fixture(name):
    return (RFIX / name).read_text()


def _defect_repo(tmp_path, ledger_text, reviews=()):
    """A repo dir with a plan-defects.toml and the given (name, text) reviews."""
    repo = tmp_path / "repo"
    (repo / "docs" / "ledger").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "ledger" / "plan-defects.toml").write_text(ledger_text)
    for name, text in reviews:
        d = repo / "docs" / "reviews"
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text)
    return repo


def _defect_graph(repo):
    return {
        "generated": "t",
        "repos": [
            {
                "name": "repo",
                "path": str(repo),
                "tasks": [],
                "legacy": [],
                "untracked_plans": [],
            }
        ],
    }


def _record_line(md):
    return next(l for l in md.splitlines() if l.startswith("**Record"))


def test_read_reviews_reads_line_after_front_matter_block(tmp_path):
    # A leading `---` block is skipped; the first line AFTER it is the H1.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            ("2026-09-06-opus-review-wb.md", _review_fixture("with-block-approved.md")),
        ],
    )
    rv = tk.read_reviews(str(repo))
    assert rv["W1"]["verdict"] == "APPROVED"


def test_read_reviews_no_block_still_parses(tmp_path):
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[("2026-09-06-opus-review-nb.md", _review_fixture("no-block-old.md"))],
    )
    rv = tk.read_reviews(str(repo))
    assert rv["W1"]["verdict"] == "APPROVED"


def test_check_requires_block_on_or_after_front_matter_from(tmp_path):
    # On the date `front_matter_from` (inclusive) a block is required; the day
    # before it is not. Mutant: `>` for `>=` lets the on-date file pass.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            ("2026-09-07-opus-review-new.md", _review_fixture("no-block-new.md")),
            ("2026-09-06-opus-review-old.md", _review_fixture("no-block-old.md")),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any(
        "2026-09-07-opus-review-new.md" in e and "no front-matter block" in e
        for e in errs
    )
    assert not any("old" in e or "2026-09-06" in e for e in errs)


def test_check_validates_enum_on_early_file_block(tmp_path):
    # A file dated before `front_matter_from` that carries a block is still
    # enum-validated. Mutant: skip blocks on early files -> no "not in" error.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            ("2026-09-05-opus-review-early.md", _review_fixture("early-bad-enum.md")),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any("early" in e and "not in" in e for e in errs)


def test_check_rejects_unknown_plan_defect_value(tmp_path):
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[("2026-09-07-opus-review-bad.md", _review_fixture("bad-enum.md"))],
    )
    errs = tk.check(_defect_graph(repo))
    assert any("bad" in e and "not in" in e for e in errs)


def test_check_rejects_plan_defect_none_on_rejection(tmp_path):
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[("2026-09-07-opus-review-rn.md", _review_fixture("rejected-none.md"))],
    )
    errs = tk.check(_defect_graph(repo))
    assert any("rn" in e and "a rejection names its cause" in e for e in errs)


def test_check_ledger_row_review_must_exist(tmp_path):
    ledger = (
        FMF_LEDGER
        + '[[rejection]]\nreview = "docs/reviews/2026-09-08-opus-review-gone.md"\n'
        + 'run = "ev1"\nkey = "R9"\ndate = 2026-09-08\nplan_defect = "vacuous"\n'
    )
    repo = _defect_repo(tmp_path, ledger)
    errs = tk.check(_defect_graph(repo))
    assert any("plan-defects row ev1/R9" in e and "no such review" in e for e in errs)


def test_plan_defect_enum_arms_by_verdict(tmp_path):
    assert tuple(tk.PLAN_DEFECT_ENUM) == (
        "none",
        "vacuous",
        "missing-case",
        "underspecified",
        "wrong-fact",
        "implementer",
        "process",
    )
    repo = _defect_repo(tmp_path, FMF_LEDGER)
    d = repo / "docs" / "reviews"
    d.mkdir(parents=True, exist_ok=True)
    i = 0
    for value in tk.PLAN_DEFECT_ENUM:
        for verdict in ("APPROVED", "REJECTED"):
            i += 1
            (d / f"2026-09-07-opus-review-{i}.md").write_text(
                f"---\nplan_defect: {value}\n---\n"
                f"# Opus gate \u2014 seat run ev1, task W{i} \u2014 {verdict}\n\nbody\n"
            )
    errs = tk.check(_defect_graph(repo))
    # Only `none` with a REJECTED verdict is refused; every enum arm is valid
    # under APPROVED and every real cause is valid under REJECTED.
    assert len(errs) == 1
    assert "opus-review-2.md" in errs[0] and "names its cause" in errs[0]


def test_check_rejects_secondary_equal_to_primary(tmp_path):
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[("2026-09-07-opus-review-sec.md", _review_fixture("secondary.md"))],
    )
    errs = tk.check(_defect_graph(repo))
    assert any(
        "sec" in e and "plan_defect_secondary equals plan_defect" in e for e in errs
    )


def test_brief_record_line_counts_and_classifies(tmp_path):
    # today=2026-09-12 -> window [09-05, 09-12]. Six plan-caused rows (vacuous 3,
    # missing-case 1, underspecified 2) of which two carry a plan-class
    # secondary, one in-window implementer row, and one implementer row dated
    # 09-04 (eight days before today -> not counted).
    rows = [
        ("2026-09-05", "vacuous", None),
        ("2026-09-06", "vacuous", None),
        ("2026-09-07", "vacuous", None),
        ("2026-09-08", "missing-case", "vacuous"),
        ("2026-09-09", "underspecified", None),
        ("2026-09-10", "underspecified", "missing-case"),
        ("2026-09-11", "implementer", "missing-case"),
        ("2026-09-04", "implementer", None),
    ]
    ledger = FMF_LEDGER
    for i, (date, primary, secondary) in enumerate(rows):
        sec = f'\nplan_defect_secondary = "{secondary}"' if secondary else ""
        ledger += (
            f'[[rejection]]\nreview = "docs/reviews/{date}-opus-review-{i}.md"\n'
            f'run = "ev1"\nkey = "K{i}"\ndate = {date}\nplan_defect = "{primary}"{sec}\n'
        )
    repo = _defect_repo(tmp_path, ledger)
    md = tk.render_brief(_defect_graph(repo), today=datetime.date(2026, 9, 12))
    line = _record_line(md)
    assert "7 rej, 6 plan" in line
    assert "(vac 3, miss 1, under 2, fact 0)" in line


def test_record_window_is_inclusive(tmp_path):
    # Exactly seven days before today counts; eight days before does not.
    # Mutant: `<` instead of `<=` on the window edge drops the on-edge row.
    ledger = (
        FMF_LEDGER
        + '[[rejection]]\nreview = "docs/reviews/2026-09-05-opus-review-a.md"\n'
        + 'run = "ev1"\nkey = "A"\ndate = 2026-09-05\nplan_defect = "vacuous"\n'
        + '[[rejection]]\nreview = "docs/reviews/2026-09-04-opus-review-b.md"\n'
        + 'run = "ev1"\nkey = "B"\ndate = 2026-09-04\nplan_defect = "vacuous"\n'
    )
    repo = _defect_repo(tmp_path, ledger)
    md = tk.render_brief(_defect_graph(repo), today=datetime.date(2026, 9, 12))
    line = _record_line(md)
    assert "1 rej" in line and "vac 1" in line


def test_brief_record_dedups_ledger_row_with_block(tmp_path):
    # A file both in the ledger and carrying a block counts once, the block
    # winning. Mutant: count both -> 2 rejections.
    ledger = (
        FMF_LEDGER
        + '[[rejection]]\nreview = "docs/reviews/2026-09-08-opus-review-r.md"\n'
        + 'run = "ev1"\nkey = "R1"\ndate = 2026-09-08\nplan_defect = "missing-case"\n'
    )
    repo = _defect_repo(
        tmp_path,
        ledger,
        reviews=[
            (
                "2026-09-08-opus-review-r.md",
                (
                    "---\nplan_defect: vacuous\n---\n"
                    "# Opus gate \u2014 seat run ev1, task R1 \u2014 REJECTED\n\nbody\n"
                ),
            ),
        ],
    )
    md = tk.render_brief(_defect_graph(repo), today=datetime.date(2026, 9, 12))
    line = _record_line(md)
    assert "1 rej" in line
    assert "vac 1" in line and "miss 0" in line


def test_brief_record_line_over_seeded_ledger(tmp_path):
    # The FROZEN 48-row seed copied into the fixture: the window 2026-08-30..
    # 09-06 holds every review date, so all 48 rows count (45 plan-caused).
    # Mutant: a row's class typo changes one of the four counts -> the exact
    # string fails. The live ledger is never opened here, so a later row filed
    # against it cannot turn this assertion red.
    repo = tmp_path / "repo"
    (repo / "docs" / "ledger").mkdir(parents=True)
    (repo / "docs" / "ledger" / "plan-defects.toml").write_bytes(
        FROZEN_SEED.read_bytes()
    )
    md = tk.render_brief(
        {
            "generated": "t",
            "repos": [
                {
                    "name": "repo",
                    "path": str(repo),
                    "tasks": [],
                    "legacy": [],
                    "untracked_plans": [],
                }
            ],
        },
        today=datetime.date(2026, 9, 6),
    )
    line = _record_line(md)
    assert "48 rej, 45 plan (vac 15, miss 16, under 8, fact 6)" in line


def test_live_record_line_shape_only(tmp_path):
    # The LIVE ledger is asserted by SHAPE only: the Record line must match
    # RECORD_SHAPE with `rej >= 48` (the seed never shrinks) — no literal count
    # is pinned, so the ledger may grow without turning this check red. A line
    # that carries no tally at all — "**Record: unavailable**" — must NOT satisfy
    # the shape, or a `.*` loosening of RECORD_SHAPE would slip through. Mutant:
    # RECORD_SHAPE loosened to `.*` -> the negative case below fails.
    repo = tmp_path / "repo"
    (repo / "docs" / "ledger").mkdir(parents=True)
    (repo / "docs" / "ledger" / "plan-defects.toml").write_bytes(
        LIVE_LEDGER.read_bytes()
    )
    md = tk.render_brief(_defect_graph(repo), today=datetime.date(2026, 9, 6))
    line = _record_line(md)
    m = RECORD_SHAPE.match(line)
    assert m is not None, f"Record line does not match shape: {line!r}"
    assert RECORD_SHAPE.match("**Record: unavailable**") is None
    assert int(m.group(1)) >= 48


def test_sandbox_ledger_is_the_frozen_seed():
    # The evidence-unit sandbox pins `docs/ledger/plan-defects.toml` to the
    # frozen seed (flake.nix copies the fixture over the live ledger and sets
    # EVIDENCE_UNIT_SANDBOX=1), so the check never sees the live, growing
    # ledger. The pinned copy must be byte-identical to the seed. Outside the
    # sandbox the assertion is meaningless — the devShell sees the live ledger —
    # so the test is skipped with a stated reason. Mutant: drop the flake.nix
    # copy line -> the sandbox still copies the live ledger and this fails.
    if os.environ.get("EVIDENCE_UNIT_SANDBOX") != "1":
        pytest.skip("the sandbox-pin assertion runs only in the evidence-unit sandbox")
    root = HERE.parents[2]
    ledger = root / "docs" / "ledger" / "plan-defects.toml"
    assert ledger.read_bytes() == FROZEN_SEED.read_bytes()


def test_main_brief_accepts_today_option(tmp_path, monkeypatch, capsys):
    # `brief --today YYYY-MM-DD` feeds the record window. Mutant: leave `--today`
    # off the brief subparser -> argparse rejects the flag.
    monkeypatch.setattr(tk, "run", fake_git([]))
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "p.md").write_text(RUNNING_PLAN)
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "nixos-agent-env"\npath = "{repo}"\n'
    )
    rc = tk.main(
        [
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "none"),
            "--store",
            str(tmp_path / "none"),
            "brief",
            "--today",
            "2026-09-06",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "**Record (7 d):** 0 rej, 0 plan" in out


def test_main_accepts_today_global(tmp_path, monkeypatch, capsys):
    # `--today` before the subcommand (a global) also feeds the record window;
    # the subcommand form stays. Mutant: attach `--today` only to the brief
    # subparser -> the global form exits 2 (invalid choice) and rc == 0 fails.
    monkeypatch.setattr(tk, "run", fake_git([]))
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "p.md").write_text(RUNNING_PLAN)
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "nixos-agent-env"\npath = "{repo}"\n'
    )
    rc = tk.main(
        [
            "--today",
            "2026-09-06",
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "none"),
            "--store",
            str(tmp_path / "none"),
            "brief",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "**Record (7 d):** 0 rej, 0 plan" in out


def test_record_ignores_approved_block(tmp_path):
    # An APPROVED review's in-window block never counts as a rejection. Mutant:
    # drop the verdict test (count every in-window block) -> the APPROVED block
    # inflates the count to "1 rej" and the "0 rej" assertion fails.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-08-opus-review-ap.md",
                _review_fixture("approved-block-in-window.md"),
            ),
        ],
    )
    md = tk.render_brief(_defect_graph(repo), today=datetime.date(2026, 9, 12))
    line = _record_line(md)
    assert "0 rej, 0 plan" in line


def test_check_shape_h1_must_follow_block(tmp_path):
    # A block not immediately followed by the H1 is a shape error, never
    # silence. Mutant: drop the shape check -> the blank-line fixture emits no
    # "must follow the block" error and the assertion fails.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-bl.md",
                _review_fixture("blank-after-block.md"),
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any(
        "opus-review-bl.md" in e and "the H1 must follow the block" in e for e in errs
    )


def test_read_reviews_finds_verdict_within_three_lines(tmp_path):
    # The verdict is read within the next three lines after the block, so a
    # blank line never silently deletes the review from the graph. Mutant: keep
    # matching only `lines[i + 1]` -> read_reviews returns {} and fails.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-bl.md",
                _review_fixture("blank-after-block.md"),
            ),
        ],
    )
    rv = tk.read_reviews(str(repo))
    assert rv["W1"]["verdict"] == "REJECTED"


def test_check_rejects_non_integer_mutant_counts(tmp_path):
    # The three mutant-count keys parse as non-negative integers; anything else
    # errors. Mutant: drop the parse -> `banana` is accepted silently and the
    # "must be an integer" assertion fails.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-bn.md",
                _review_fixture("banana-mutants.md"),
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any("bn" in e and "mutants_total must be an integer" in e for e in errs)


def test_check_plan_defect_missing(tmp_path):
    # A block without a `plan_defect` key errors. Mutant: remove the
    # "plan_defect missing" error -> check is silent and the assertion fails.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-missing.md",
                "---\nmutants_total: 1\n---\n# Opus gate — seat run ev1, task W1 — APPROVED\n\nbody\n",
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any("missing" in e and "plan_defect missing" in e for e in errs)


def test_check_secondary_outside_enum(tmp_path):
    # A secondary outside the enum errors. Mutant: remove the secondary-outside-
    # enum arm -> check is silent and the assertion fails.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-sec2.md",
                "---\nplan_defect: vacuous\nplan_defect_secondary: maybe\n---\n# Opus gate — seat run ev1, task W1 — REJECTED\n\nbody\n",
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any("sec2" in e and "plan_defect_secondary maybe not in" in e for e in errs)


def test_unreadable_ledger_errors_and_record_unavailable(tmp_path):
    # An unparseable ledger makes `check` error and the brief print
    # `Record: unavailable`. Mutant: degrade to (None, []) instead of None ->
    # both vanish and the assertions fail.
    repo = _defect_repo(tmp_path, "[meta\nfront_matter_from = 2026-09-07")
    errs = tk.check(_defect_graph(repo))
    assert any("unreadable" in e for e in errs)
    md = tk.render_brief(_defect_graph(repo), today=datetime.date(2026, 9, 12))
    assert "**Record: unavailable**" in md


def test_record_default_today_is_utc(tmp_path, monkeypatch):
    # The `--today` default is the UTC clock; freeze it and the window follows.
    # Mutant: hard-code `_today_utc` to a fixed date -> the frozen-clock window
    # is ignored and the on-edge row drops -> "1 rej" fails.
    class Clock(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 6, 0, 0, 0, tzinfo=tz)

    monkeypatch.setattr(tk.datetime, "datetime", Clock)
    ledger = (
        FMF_LEDGER
        + '[[rejection]]\nreview = "docs/reviews/2026-08-30-opus-review-a.md"\n'
        + 'run = "ev1"\nkey = "A"\ndate = 2026-08-30\nplan_defect = "vacuous"\n'
    )
    repo = _defect_repo(tmp_path, ledger)
    md = tk.render_brief(_defect_graph(repo))
    line = _record_line(md)
    assert "1 rej" in line and "vac 1" in line


def test_check_ignores_non_opus_review(tmp_path):
    # Only `*opus-review*.md` is under the front-matter rule; a same-dated
    # review whose basename lacks "opus" is ignored. Mutant: widen the glob to
    # `*.md` -> the file is read and the "names its cause" error fires -> the
    # no-error assertion fails.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-review-notnamed.md",
                "---\nplan_defect: none\n---\n# Opus gate — seat run ev1, task W1 — REJECTED\n\nbody\n",
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert not any("review-notnamed.md" in e for e in errs)


def test_check_rejects_signed_and_underscore_mutant_counts(tmp_path):
    # The mutant-count rule is `^[0-9]+$` — ASCII digits only, no sign, no
    # underscore. Each of `-1`, `+5`, `1_0` and `\u0663` is refused. Mutant:
    # restore `int(raw)` + `n < 0` -> `+5`, `1_0` and `\u0663` parse cleanly
    # (and `n < -1` accepts `-1`), so the "must be an integer" error vanishes
    # and the assertion fails.
    for bad in ("-1", "+5", "1_0", "\u0663"):
        repo = _defect_repo(
            tmp_path,
            FMF_LEDGER,
            reviews=[
                (
                    "2026-09-07-opus-review-sgn.md",
                    (
                        f"---\nplan_defect: vacuous\nmutants_total: {bad}\n---\n"
                        "# Opus gate \u2014 seat run ev1, task W1 \u2014 REJECTED\n\nbody\n"
                    ),
                ),
            ],
        )
        errs = tk.check(_defect_graph(repo))
        assert any(
            "sgn" in e and "mutants_total must be an integer" in e for e in errs
        ), bad


def test_check_rejects_row_with_approved_block_contradiction(tmp_path):
    # A ledger row and an APPROVED block on the same file contradict each
    # other, and `check` names the disagreement. Mutant: drop the contradiction
    # arm -> `check` is silent and the assertion fails.
    ledger = (
        FMF_LEDGER
        + '[[rejection]]\nreview = "docs/reviews/2026-09-08-opus-review-ap2.md"\n'
        + 'run = "ev1"\nkey = "R1"\ndate = 2026-09-08\nplan_defect = "missing-case"\n'
    )
    repo = _defect_repo(
        tmp_path,
        ledger,
        reviews=[
            (
                "2026-09-08-opus-review-ap2.md",
                _review_fixture("row-and-approved-block.md"),
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any(
        "opus-review-ap2.md" in e and "a ledger row contradicts an APPROVED block" in e
        for e in errs
    )


def test_record_out_of_reach_h1_counts_by_row_only(tmp_path):
    # A block whose `# Opus gate` H1 is beyond the three-line tolerance yields
    # no verdict, so the file is counted only by its ledger row, not by the
    # block. Mutant: change the record's verdict skip to
    # `if m is not None and m["verdict"] == "APPROVED"` -> the out-of-reach
    # block is counted as `vacuous` and shadows the row, so "miss 1" fails.
    ledger = (
        FMF_LEDGER
        + '[[rejection]]\nreview = "docs/reviews/2026-09-08-opus-review-or.md"\n'
        + 'run = "ev1"\nkey = "X1"\ndate = 2026-09-08\nplan_defect = "missing-case"\n'
    )
    repo = _defect_repo(
        tmp_path,
        ledger,
        reviews=[
            (
                "2026-09-08-opus-review-or.md",
                (
                    "---\nplan_defect: vacuous\n---\n\n\n\n"
                    "# Opus gate \u2014 seat run ev1, task X1 \u2014 REJECTED\n\nbody\n"
                ),
            ),
        ],
    )
    md = tk.render_brief(_defect_graph(repo), today=datetime.date(2026, 9, 12))
    line = _record_line(md)
    assert "1 rej" in line
    assert "miss 1" in line and "vac 0" in line


def test_h1_four_lines_down_is_shape_error_and_absent_from_graph(tmp_path):
    # A block whose H1 is four lines below it is out of the three-line reach:
    # `check` reports the shape error and `read_reviews` reads no verdict, so
    # the review is never silently in the graph. Mutant: widen the lookahead to
    # six lines -> `read_reviews` finds the H1, "W1" appears and the assertion
    # fails (the shape error also vanishes when the H1 is made reachable).
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            ("2026-09-07-opus-review-d4.md", _review_fixture("h1-four-lines-down.md")),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any(
        "opus-review-d4.md" in e and "the H1 must follow the block" in e for e in errs
    )
    rv = tk.read_reviews(str(repo))
    assert "W1" not in rv


def test_read_reviews_ignores_non_opus_review(tmp_path):
    # `read_reviews` globs `*opus-review*.md` like the block rule, so a
    # non-opus review with a block supplies no verdict to the task graph.
    # Mutant: restore the `*.md` glob -> the bad block's REJECTED verdict is
    # read and "W1" appears, so the absence assertion fails.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-review-notnamed.md",
                _review_fixture("not-opus-review.md"),
            ),
        ],
    )
    rv = tk.read_reviews(str(repo))
    assert "W1" not in rv


# --- T3: the review block completed (D9), the gate lint's new arms ---


def test_check_rejects_rework_verdict(tmp_path):
    # A block review whose H1 word is outside APPROVED|REJECTED (REWORK) is
    # refused by name. Mutant: admit REWORK in the shape regex -> the specific
    # error vanishes (the review silently passes the verdict lint).
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-rew.md",
                (
                    "---\nplan_defect: vacuous\n---\n"
                    "# Opus gate \u2014 seat run ev1, task W1 \u2014 REWORK\n\nbody\n"
                ),
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any(
        "rew" in e and "H1 verdict REWORK not in APPROVED | REJECTED" in e for e in errs
    )


def test_check_counts_must_be_integer_or_null(tmp_path):
    # majors/minors (and the mutant keys) parse as a non-negative integer or
    # the literal `null`; anything else is refused with the exact key. Mutant:
    # accept any string -> the "must be an integer or null" error vanishes;
    # mutant: refuse `null` -> the ok-file no-error assertion fails.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-cnt-ok.md",
                (
                    "---\nplan_defect: vacuous\nmajors: 3\nminors: null\n---\n"
                    "# Opus gate \u2014 seat run ev1, task W1 \u2014 REJECTED\n\nbody\n"
                ),
            ),
            (
                "2026-09-07-opus-review-cnt-bad.md",
                (
                    "---\nplan_defect: vacuous\nmajors: three\nminors: -1\n---\n"
                    "# Opus gate \u2014 seat run ev1, task W2 \u2014 REJECTED\n\nbody\n"
                ),
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert not any("cnt-ok" in e for e in errs)
    assert any(
        "cnt-bad" in e and "majors must be an integer or null" in e for e in errs
    )
    assert any(
        "cnt-bad" in e and "minors must be an integer or null" in e for e in errs
    )


def test_check_reviewer_enum(tmp_path):
    # reviewer must be one of opus|sonnet|deepseek|fable|unknown. Mutant:
    # accept any -> the "reviewer … not in" error vanishes.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-rok.md",
                (
                    "---\nplan_defect: vacuous\nreviewer: opus\n---\n"
                    "# Opus gate \u2014 seat run ev1, task W1 \u2014 REJECTED\n\nbody\n"
                ),
            ),
            (
                "2026-09-07-opus-review-ru.md",
                (
                    "---\nplan_defect: vacuous\nreviewer: unknown\n---\n"
                    "# Opus gate \u2014 seat run ev1, task W2 \u2014 REJECTED\n\nbody\n"
                ),
            ),
            (
                "2026-09-07-opus-review-rbad.md",
                (
                    "---\nplan_defect: vacuous\nreviewer: claude\n---\n"
                    "# Opus gate \u2014 seat run ev1, task W3 \u2014 REJECTED\n\nbody\n"
                ),
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert not any("rok" in e or "ru" in e for e in errs)
    assert any("rbad" in e and "reviewer claude not in" in e for e in errs)


def test_check_duplicate_key(tmp_path):
    # A block that repeats a key is refused by name. Mutant: keep last-wins ->
    # the "duplicate key" error vanishes.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-dup.md",
                (
                    "---\nplan_defect: vacuous\nplan_defect: missing-case\n---\n"
                    "# Opus gate \u2014 seat run ev1, task W1 \u2014 REJECTED\n\nbody\n"
                ),
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any("dup" in e and "duplicate key plan_defect" in e for e in errs)


def test_check_unknown_key(tmp_path):
    # A block key outside the allowlist is refused by name. Mutant: accept any
    # key -> the "unknown key" error vanishes.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-unk.md",
                (
                    "---\nplan_defect: vacuous\nverdict: rejected\n---\n"
                    "# Opus gate \u2014 seat run ev1, task W1 \u2014 REJECTED\n\nbody\n"
                ),
            ),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert any("unk" in e and "unknown key verdict" in e for e in errs)


def test_check_plan_defect_scope(tmp_path):
    # D9: plan_defect is required only on or after front_matter_from. A block
    # before fmf without plan_defect is silent; the same block on fmf or later
    # errors. Mutant: drop the date condition -> the early file also errors and
    # the no-error assertion fails.
    block = (
        "---\nreviewer: opus\nmajors: 1\nminors: 0\n---\n"
        "# Opus gate \u2014 seat run ev1, task W1 \u2014 REJECTED\n\nbody\n"
    )
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            ("2026-09-05-opus-review-early.md", block),
            ("2026-09-08-opus-review-late.md", block.replace("W1", "W2")),
        ],
    )
    errs = tk.check(_defect_graph(repo))
    assert not any("early" in e for e in errs)
    assert any("late" in e and "plan_defect missing" in e for e in errs)


def test_read_reviews_five_line_block(tmp_path):
    # read_reviews still parses the H1 after a five-line block. Regression pin:
    # the completed block (reviewer/majors/minors/mutants_total/mutants_killed)
    # must not break the block-aware tuple parsing.
    repo = _defect_repo(
        tmp_path,
        FMF_LEDGER,
        reviews=[
            (
                "2026-09-07-opus-review-five.md",
                (
                    "---\nreviewer: opus\nmajors: 1\nminors: 2\nmutants_total: 4\n"
                    "mutants_killed: 3\n---\n"
                    "# Opus gate \u2014 seat run ev1, task W1 \u2014 APPROVED\n\nbody\n"
                ),
            ),
        ],
    )
    rv = tk.read_reviews(str(repo))
    assert rv["W1"]["verdict"] == "APPROVED"


def _write_rich_result(tmp_path, name, body):
    d = tmp_path / "runs" / "r1"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.result"
    p.write_text(body)
    return p


def test_read_result_fields(tmp_path):
    # A fully-populated metadata block: status, every named key, commits and
    # output_tokens.
    full = _write_rich_result(
        tmp_path,
        "K1",
        "FACTORY-RESULT status=done\nFACTORY-CHECKS lint=pass\n\n"
        "run: r1\nkey: K1\nmodel: m/a\neffort: medium\nrung: 2\n"
        "route: implement/code/S\nclass: bash-driver\nfallback: fb\nprior: pr\n"
        "seat: unit seat@abc\nworkspace: /w\nhead: h\nbase: b\nwall_s: 300\n"
        "exit_code: 0\n\ncommits (base..task/K1):\n"
        "abc1 one\nabc2 two\n\ndiffstat:\n1 file changed\n\n"
        'usage: {"input": 100, "output": 3000}\n',
    )
    f = tk.read_result_fields(full)
    assert f["status"] == "done" and f["run"] == "r1" and f["key"] == "K1"
    assert f["model"] == "m/a" and f["effort"] == "medium"
    assert f["rung"] == "2" and f["route"] == "implement/code/S"
    assert f["class"] == "bash-driver" and f["wall_s"] == "300"
    assert f["commits"] == 2 and f["output_tokens"] == 3000

    # `(none)` is not a commit; a missing usage never yields an output token.
    none = _write_rich_result(
        tmp_path,
        "K2",
        "FACTORY-RESULT status=done\n\nrun: r1\nkey: K2\n\n"
        "commits (base..task/K2):\n(none)\n\ndiffstat:\n\n",
    )
    n = tk.read_result_fields(none)
    assert n["commits"] == 0 and n["output_tokens"] is None
    assert "model" not in n and "usage" not in n  # missing lines are absent keys

    # A torn `usage:` (not JSON / no int output) reads output_tokens None, and a
    # `(no commits)` marker is not a commit.
    torn = _write_rich_result(
        tmp_path,
        "K3",
        "FACTORY-RESULT status=done\n\nrun: r1\nkey: K3\n"
        'usage: {"output": "lots"}\n\ncommits (base..task/K3):\n(no commits)\n',
    )
    t = tk.read_result_fields(torn)
    assert t["output_tokens"] is None and t["commits"] == 0


def test_cli_json_serialises_task_status_rows(tmp_path):
    # The graph keeps task-status rows keyed by the (repo, plan, key) tuple
    # (`check` and the board read it that way); `json` must still print — a
    # tuple key is not JSON, and the planning packet's M3 step writes graph.json
    # from this command. Mutant: print the graph as built -> TypeError, exit 1.
    root = tmp_path / "root"
    (root / "docs" / "ledger").mkdir(parents=True)
    repo = tmp_path / "nixos-agent-env"
    (repo / "docs" / "superpowers" / "plans").mkdir(parents=True)
    (repo / "docs" / "superpowers" / "plans" / "typed.md").write_text(
        (FIXTURES / "typed.md").read_text()
    )
    (root / "docs" / "ledger" / "repos.toml").write_text(
        f'[[repo]]\nname = "nixos-agent-env"\npath = "{repo}"\n'
    )
    (root / "docs" / "ledger" / "task-status.toml").write_text(
        '[[task]]\nrepo = "nixos-agent-env"\nplan = "typed.md"\nkey = "E3"\n'
        'status = "parked"\nnote = "held"\ndecided = "2026-09-08"\n'
    )
    r = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--root",
            str(root),
            "--runs-dir",
            str(tmp_path / "none"),
            "--store",
            str(tmp_path / "none"),
            "json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["task_status"] == [
        {
            "repo": "nixos-agent-env",
            "plan": "typed.md",
            "key": "E3",
            "status": "parked",
            "note": "held",
            "decided": "2026-09-08",
        }
    ]
    # the parked task is still a task of the graph, in its parked state
    by_key = {t["key"]: t for t in data["repos"][0]["tasks"]}
    assert by_key["E3"]["state"] == "parked"
