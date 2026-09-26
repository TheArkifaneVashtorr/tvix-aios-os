import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def norm(p):
    return str(p).replace("$HOME", "/home/x").replace("~", "/home/x").rstrip("/")


def test_the_three_local_only_lists_agree(monkeypatch):
    monkeypatch.setenv("HOME", "/home/x")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    lane = load(ROOT / "pkgs" / "lane" / "lane-submit.py", "lane_submit")
    guard = load(ROOT / "pkgs" / "dsh-openrouter" / "hook-guard.py", "hook_guard")
    sh = (ROOT / "pkgs" / "dsh-openrouter" / "dsh-openrouter.sh").read_text()
    body = re.search(r"^forbidden=\((.*?)^\)", sh, re.DOTALL | re.MULTILINE).group(1)
    bash_list = {norm(tok.strip('"')) for tok in body.split() if tok.strip('"')}
    lane_list = {norm(p) for p in lane.FORBIDDEN_REPO_PREFIXES}
    guard_list = {norm(p) for p in guard._protected_prefixes()}
    assert lane_list == guard_list == bash_list, {
        "lane": sorted(lane_list),
        "guard": sorted(guard_list),
        "bash": sorted(bash_list),
    }
    # SB7: ~/.codex is a local-only tree (the codex operator home) beside
    # ~/.claude, and each refusal list must name it. This membership check is
    # what turns a `~/.codex` dropped from ALL THREE lists red rather than a
    # silently agreed regression.
    assert "/home/x/.codex" in lane_list
    assert "/home/x/.codex" in guard_list
    assert "/home/x/.codex" in bash_list
