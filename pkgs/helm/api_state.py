"""Helm API route module — the three read-only state documents.

GET /v1/status  — the collector's status.json, parsed from cfg["out_dir"].
GET /v1/control — read_state(cfg["control"]), re-read on every call.
GET /v1/home    — /etc/helm/home.json parsed, or {"flakes": []} when absent.

Read-only: no handler here spawns a process (read_state's journal read is
serve.py's own seam) and none writes a file.
"""

from __future__ import annotations

import json
import pathlib

from serve import read_state

_HOME_PATH = "/etc/helm/home.json"


def _status_handler(cfg, request):
    out_dir = cfg.get("out_dir", "/var/lib/helm")
    try:
        doc = json.loads(pathlib.Path(out_dir, "status.json").read_text())
    except (OSError, json.JSONDecodeError):
        return 404, {"error": "no status document yet"}
    return 200, doc


def _control_handler(cfg, _):
    return 200, read_state(cfg["control"])


def _home_handler(cfg, _):
    try:
        doc = json.loads(pathlib.Path(_HOME_PATH).read_text())
    except (OSError, json.JSONDecodeError):
        return 200, {"flakes": []}
    return 200, doc


def routes():
    return [
        ("GET", "/v1/status", _status_handler),
        ("GET", "/v1/control", _control_handler),
        ("GET", "/v1/home", _home_handler),
    ]
