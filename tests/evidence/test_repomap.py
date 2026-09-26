"""Repo map tests (plan 2026-09-05-session-context, G2)."""

import importlib.util
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()


def load():
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / "repomap.py",
        pathlib.Path("pkgs/evidence/repomap.py"),
    ]
    src = next(p for p in candidates if p.exists())
    spec = importlib.util.spec_from_file_location("repomap", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, src


rm, SRC = load()

FLAKE = """{
  outputs = { self, nixpkgs }:
    let x = 1; in {
      packages.${system} = { a = 1; };
      checks.${system} = {
        # a comment at eight spaces
        host-core = 1;
        lint =
          pkgs.runCommand "lint" { } "touch $out";
        nested = {
          inner-child = 1;
        };
        helm-control-assertion-negative-profiles = 2;
      };
      other-block = {
        zzz = 1;
      };
    };
}
"""


def make_repo(tmp_path):
    (tmp_path / "flake.nix").write_text(FLAKE)
    (tmp_path / "nixosModules").mkdir()
    (tmp_path / "nixosModules" / "helm.nix").write_text(
        "# Helm: the status dashboard module.\n{ config, ... }: { }\n"
    )
    (tmp_path / "nixosModules" / "bare.nix").write_text("{ }\n")
    (tmp_path / "pkgs" / "basket").mkdir(parents=True)
    (tmp_path / "pkgs" / "basket" / "basket.sh").write_text(
        "#!/usr/bin/env bash\n# basket: pack, encrypt, mount, teardown.\nset -e\n"
    )
    (tmp_path / "pkgs" / "broker").mkdir()
    (tmp_path / "pkgs" / "broker" / "broker.sh").write_text(
        "#!/usr/bin/env bash\n# A: broker.sh wins over default.nix.\nset -e\n"
    )
    (tmp_path / "pkgs" / "broker" / "default.nix").write_text(
        "# B: default.nix is the second tier.\n{ }\n"
    )
    (tmp_path / "pkgs" / "evidence").mkdir()
    (tmp_path / "pkgs" / "evidence" / "evidence.py").write_text(
        '"""The evidence store CLI."""\nimport sys\n'
    )
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "a.bats").write_text("")
    (tmp_path / "tests" / "unit" / "b.bats").write_text("")
    (tmp_path / "hosts" / "core").mkdir(parents=True)
    (tmp_path / "hosts" / "core" / "default.nix").write_text(
        "# core: one file per concern.\n{ }\n"
    )
    (tmp_path / "tools" / "factory" / "seat").mkdir(parents=True)
    (tmp_path / "tools" / "factory" / "seat" / "README.md").write_text(
        "# The seat driver\n\ntext\n"
    )
    (tmp_path / "tools" / "factory" / "dark-factory.js").write_text(
        "// Dark factory — reusable Workflow script.\n"
    )
    return tmp_path


def test_flake_check_names_reads_the_checks_block_only():
    assert rm.flake_check_names(FLAKE) == [
        "host-core",
        "lint",
        "nested",
        "helm-control-assertion-negative-profiles",
    ]


def test_first_comment_handles_shebang_docstring_and_bare(tmp_path):
    make_repo(tmp_path)
    assert (
        rm.first_comment(tmp_path / "pkgs" / "basket" / "basket.sh")
        == "basket: pack, encrypt, mount, teardown."
    )
    assert (
        rm.first_comment(tmp_path / "pkgs" / "evidence" / "evidence.py")
        == "The evidence store CLI."
    )
    assert (
        rm.first_comment(tmp_path / "nixosModules" / "bare.nix") == "(no description)"
    )


def test_build_and_render(tmp_path):
    m = rm.build_map(make_repo(tmp_path))
    assert m["checks"] == [
        "host-core",
        "lint",
        "nested",
        "helm-control-assertion-negative-profiles",
    ]
    assert "inner-child" not in m["checks"]
    assert "zzz" not in m["checks"]
    assert {
        "path": "nixosModules/helm.nix",
        "desc": "Helm: the status dashboard module.",
    } in m["modules"]
    assert {
        "path": "pkgs/basket",
        "desc": "basket: pack, encrypt, mount, teardown.",
    } in m["packages"]
    assert {
        "path": "pkgs/broker",
        "desc": "A: broker.sh wins over default.nix.",
    } in m["packages"]
    assert {"path": "tests/unit", "files": 2} in m["tests"]
    assert {
        "path": "hosts/core/default.nix",
        "desc": "core: one file per concern.",
    } in m["hosts"]
    assert {
        "path": "tools/factory",
        "desc": "Dark factory — reusable Workflow script.",
    } in m["tools"]  # no README at tools/factory: first script recursively, sorted
    md = rm.render_map(m)
    assert md.startswith(rm.HEADER)
    assert "`nixosModules/helm.nix` — Helm: the status dashboard module." in md
    assert "## NixOS modules\n" in md
    assert "## Packages\n" in md
    assert "## Checks (nix build .#checks.x86_64-linux.<name>)\n" in md
    assert "## Tests\n" in md
    assert "## Hosts\n" in md
    assert "## Tools\n" in md
    assert "- `tests/unit` — 2 files\n" in md
    assert "- host-core\n" in md and "\n- nested\n" in md


def test_cli_write_then_check_then_drift(tmp_path):
    make_repo(tmp_path)
    (tmp_path / "docs").mkdir()
    r = subprocess.run(
        [sys.executable, str(SRC), "--root", str(tmp_path), "write"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0 and (tmp_path / "docs" / "MAP.md").read_text().startswith(
        rm.HEADER
    )
    r = subprocess.run(
        [sys.executable, str(SRC), "--root", str(tmp_path), "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    (tmp_path / "docs" / "MAP.md").write_text(
        (tmp_path / "docs" / "MAP.md").read_text() + "stale\n"
    )
    r = subprocess.run(
        [sys.executable, str(SRC), "--root", str(tmp_path), "check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 1
    assert (
        r.stderr.strip()
        == "repomap: docs/MAP.md is stale — run: python3 pkgs/evidence/repomap.py write"
    )


def test_count_files_git_tracked_and_ruff_cache_fallback(tmp_path):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
    }
    # git mode: only tracked files count (b.bats is untracked)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = make_repo(repo_dir)
    subprocess.run(
        ["git", "-C", str(repo), "init", "-q", "-b", "main"], check=True, env=env
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", "tests/unit/a.bats"], check=True, env=env
    )
    assert rm._count_files(repo / "tests" / "unit") == 1

    # fallback walk: a non-repo dir ignores a nested .ruff_cache
    d = tmp_path / "nonrepo" / "tests" / "unit"
    d.mkdir(parents=True)
    (d / "x.py").write_text("")
    (d / ".ruff_cache").mkdir()
    (d / ".ruff_cache" / "entry").write_text("")
    assert rm._count_files(d) == 1
