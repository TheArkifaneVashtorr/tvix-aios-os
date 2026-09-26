"""Helm API route module — the patch queue and task queue records.

GET /v1/patches — docs/ledger/patches.toml read at cfg["repo"]'s HEAD (git show
  HEAD:docs/ledger/patches.toml), each row joined with the running generation:
  carried_by_next_switch is true when a row has no landed_generation or landed
  after the running generation. A row with no generation is carried, never
  hidden (U4's fallback).
GET /v1/tasks   — python3 pkgs/evidence/tasks.py --root <repo> json, passed
  through unchanged except for a top-level "source" marker: Helm never parses
  plan prose (decision 50a).

Both routes are GET only. Neither shells out to anything but git, readlink and
python3 pkgs/evidence/tasks.py, and none of that through a direct `import
subprocess` — the runner is api's allowlisted `run()` seam (cfg["_run"] in
tests, subprocess.run in production), reached by a deferred import so this
module never imports api at load time (api's discover() imports api_record). A
failing subprocess degrades to 200 with an "error" field naming the command,
never a 500 — the same shape read_state's journal degradation uses.
"""

from __future__ import annotations

import json
import os
import re

import tomllib

_LEDGER = "docs/ledger/patches.toml"
_TASKS_SOURCE = "pkgs/evidence/tasks.py"
_PROFILE = "/nix/var/nix/profiles/system"
_GEN_RE = re.compile(r"-(\d+)-link$")


def _executor(cfg):
    """The subprocess seam: cfg["_run"] in tests, api's allowlisted run() in
    production. Deferred so api_record never imports api at module load."""
    executor = cfg.get("_run")
    if executor is not None:
        return executor
    import api

    return api.run


def running_generation(cfg=None):
    """The live system generation as an int, or None when unreadable.

    os.readlink("/nix/var/nix/profiles/system") names the current generation
    link (e.g. ``system-55-link``); the trailing integer is the generation.
    cfg["_readlink"] replaces the readlink for tests.
    """
    readlink = (cfg or {}).get("_readlink") or os.readlink
    try:
        target = readlink(_PROFILE)
    except OSError:
        return None
    match = _GEN_RE.search(os.path.basename(target))
    if match is None:
        return None
    return int(match.group(1))


class _GitShowError(Exception):
    """git show failed for a cause other than a missing ledger path."""


def _missing_ledger_path(stderr):
    """True when git show's stderr names the ledger path as absent."""
    return any(
        marker in stderr
        for marker in ("does not exist", "exists on disk", "path not found")
    )


def read_patches(repo, run):
    """docs/ledger/patches.toml at HEAD as a list of rows.

    Returns the row list on success; None when the ledger path is missing from
    HEAD (the handler degrades to ``{"patches": [], "missing": ...}``); raises
    _GitShowError when git show fails for any other reason, and lets a
    TOMLDecodeError propagate for a committed-but-malformed ledger. The handler
    maps each cause to its own "error" body (interface 6).
    """
    cp = run(
        ["git", "-C", repo, "show", f"HEAD:{_LEDGER}"], capture_output=True, text=True
    )
    if cp.returncode != 0:
        if _missing_ledger_path(cp.stderr):
            return None
        raise _GitShowError()
    return tomllib.loads(cp.stdout).get("patch", [])


def _carried(landed_generation, running):
    return landed_generation is None or (
        running is not None and landed_generation > running
    )


def _patches_handler(cfg, request):
    """GET /v1/patches — nothing raised leaves it: every failure is a 200
    "error" body (interface 3: never 500, never no response)."""
    try:
        run = _executor(cfg)
        return _patches(cfg, run)
    except _GitShowError:
        return 200, {"error": f"git show HEAD:{_LEDGER}"}
    except tomllib.TOMLDecodeError as exc:
        return 200, {"error": f"{_LEDGER}: {exc}"}
    except Exception as exc:  # noqa: BLE001 - interface 3: any failure is a 200 error body, never 500
        return 200, {"error": f"{type(exc).__name__}: {exc}"}


def _patches(cfg, run):
    rows = read_patches(cfg["repo"], run)
    if rows is None:
        return 200, {"patches": [], "missing": _LEDGER}
    running = running_generation(cfg)
    head_cp = run(
        ["git", "-C", cfg["repo"], "rev-parse", "HEAD"], capture_output=True, text=True
    )
    if head_cp.returncode != 0:
        return 200, {"error": "git rev-parse HEAD"}
    head = head_cp.stdout.strip()
    patches = []
    for row in rows:
        landed = row.get("landed_generation")
        patches.append(
            {
                **row,
                "landed_generation": landed,
                "carried_by_next_switch": _carried(landed, running),
            }
        )
    return 200, {"running_generation": running, "head": head, "patches": patches}


def read_tasks(repo, run):
    """python3 <repo>/pkgs/evidence/tasks.py --root <repo> json, parsed.

    The producer is addressed by an absolute path joined to repo and run with
    cwd=repo, so a service whose cwd is / still reaches it (MAJOR-2). None on
    failure.
    """
    tasks_path = os.path.join(repo, _TASKS_SOURCE)
    cp = run(
        ["python3", tasks_path, "--root", repo, "json"],
        capture_output=True,
        text=True,
        cwd=repo,
    )
    if cp.returncode != 0:
        return None
    return json.loads(cp.stdout)


def _tasks_handler(cfg, request):
    """GET /v1/tasks — nothing raised leaves it (interface 3)."""
    try:
        run = _executor(cfg)
        return _tasks(cfg, run)
    except Exception as exc:  # noqa: BLE001 - interface 3: any failure is a 200 error body, never 500
        return 200, {"error": f"{type(exc).__name__}: {exc}"}


def _tasks(cfg, run):
    doc = read_tasks(cfg["repo"], run)
    if doc is None:
        return 200, {"error": f"python3 {_TASKS_SOURCE}"}
    doc["source"] = _TASKS_SOURCE
    return 200, doc


def routes():
    return [
        ("GET", "/v1/patches", _patches_handler),
        ("GET", "/v1/tasks", _tasks_handler),
    ]
