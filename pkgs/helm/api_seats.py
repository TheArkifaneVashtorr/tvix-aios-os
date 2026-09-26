"""Helm API route module — the session list and the three seat writes.

Reads the seat job spool (SA9's job-directory contract, U5: each
``<spool>/<id>/job.json`` with an optional ``exit_code.txt``) and joins it with
the live ``systemctl list-units 'seat@*'`` state. Helm never allocates a port
(SA3's seat-spool does): ``port`` comes only from ``job.json``, a non-int port
answers null, and a null port renders a null ``url``.

HM5 adds the three writes decision 12c admits — seat start, stop, attach (never
spend or switches): ``POST /v1/seats`` runs ``seat-submit``, ``POST
/v1/seats/<id>/stop`` runs ``systemctl stop seat@<id>.service``, and ``POST
/v1/seats/<id>/attach`` answers the loopback url from HM4's record. Every write
goes through ``api.run`` — HM2's allowlisted seam — so exactly two programs are
ever named here, ``seat-submit`` and ``systemctl`` (the latter only with a verb
in ``VERBS`` and a ``seat@*.service`` unit); this module never reaches a process
runner directly and never names the profile-switch unit, the activation tool or
an escalation tool.
The runner is injectable (``cfg["_run"]`` in tests); production runs through
``api.run``, which admits the read-only ``systemctl list-units``/``show`` verbs
and the start/stop writes, applies capture and a timeout, and turns its own
failures (a refusal, a timeout, an absent program) into a non-zero
``returncode`` with the message in ``stderr``. The read route reads only
``returncode``/``stdout``/``stderr`` and degrades every unit state to
``"unknown"`` on any non-zero returncode (interface 4).
"""

from __future__ import annotations

import json
import pathlib
import re

_SEAT_UNIT_RE = re.compile(r"^seat@(.+)\.service$")
_STATES = {"active", "inactive", "failed"}
_DEFAULT_SPOOL_DIR = "/var/lib/seat/jobs"
_SYSTEMCTL_LIST = [
    "systemctl",
    "list-units",
    "seat@*",
    "--all",
    "--output=json",
    "--no-pager",
]
# HM5 interface 2: the closed verb set for the seat writes — start and stop
# only, never restart (M3). The unit name is always ``seat@`` + id + ``.service``
# where id matches the strict pattern below (never a traversal path, M2).
VERBS = ("start", "stop")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _refused_error(program, cp):
    """The write route's error body when the seam's returncode is non-zero: a
    502 with one "error" string carrying the code and the seam's stderr, so a
    refused/absent/timed-out start or stop is never answered 202 (HM4c's house
    rule: a refusal is an error body, never swallowed)."""
    lines = (cp.stderr or "").strip().splitlines()
    detail = lines[0] if lines else ""
    message = f"{program} failed: returncode {cp.returncode}"
    if detail:
        message += f": {detail}"
    return 502, {"error": message}


def _unit_name(seat_id):
    """The systemd unit name for a seat id, or None when the id fails the
    strict pattern (interface 2). A bad id must 400 before any runner is
    reached, so a traversal id can never name the profile-switch unit."""
    if _ID_RE.fullmatch(seat_id) is None:
        return None
    return f"seat@{seat_id}.service"


def _executor(cfg):
    """The process seam: ``cfg["_run"]`` in tests, ``api.run`` in
    production. Deferred so api_seats never imports api at module load (api's
    discover() imports api_seats)."""
    executor = cfg.get("_run")
    if executor is not None:
        return executor
    import api

    return api.run


def routes():
    return [
        ("GET", "/v1/seats", list_seats),
        ("POST", "/v1/seats", start_seat),
        ("POST", "/v1/seats/<id>/stop", stop_seat),
        ("POST", "/v1/seats/<id>/attach", attach_seat),
    ]


def read_jobs(spool_dir):
    """{job_id: {"port": int|None, "exit_code": int|None}} for every job
    directory under ``spool_dir``. A missing directory or a malformed/unreadable
    ``job.json`` is skipped, never a failure (interface 2); a non-int ``port``
    is null, never a string or float."""
    jobs: dict[str, dict] = {}
    root = pathlib.Path(spool_dir)
    try:
        entries = list(root.iterdir())
    except OSError:
        return jobs
    for entry in entries:
        if not entry.is_dir():
            continue
        try:
            job = json.loads((entry / "job.json").read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(job, dict):
            continue
        exit_code = None
        try:
            exit_code = int((entry / "exit_code.txt").read_text().strip())
        except (OSError, ValueError):
            exit_code = None
        port = job.get("port")
        jobs[entry.name] = {
            "port": port if isinstance(port, int) else None,
            "exit_code": exit_code,
        }
    return jobs


def _map_state(active):
    """systemd's ActiveState -> active|inactive|failed|unknown."""
    return active if active in _STATES else "unknown"


def unit_states(run):
    """(states, error) — {seat_id: state} from ``systemctl list-units 'seat@*'
    --all --output=json --no-pager``, plus an error string on a non-zero
    returncode. The seam (``api.run``) already turned a refusal, a timeout and
    an absent program into returncodes 126/124/127 with the message in
    ``stderr``, so this reads only ``returncode``/``stdout``/``stderr`` and
    degrades every state to ``unknown`` (interface 4), naming the command and
    carrying ``stderr``'s first line."""
    states: dict[str, str] = {}
    if run is None:
        return states, None
    cp = run(_SYSTEMCTL_LIST)
    if cp.returncode != 0:
        lines = (cp.stderr or "").strip().splitlines()
        detail = lines[0] if lines else f"returncode {cp.returncode}"
        return states, f"systemctl list-units failed: {detail}"
    try:
        units = json.loads(cp.stdout or "")
    except (json.JSONDecodeError, ValueError):
        return states, None
    if not isinstance(units, list):
        return states, None
    for entry in units:
        if not isinstance(entry, dict):
            continue
        match = _SEAT_UNIT_RE.match(entry.get("unit") or "")
        if match is None:
            continue
        states[match.group(1)] = _map_state(entry.get("active"))
    return states, None


def list_seats(cfg, request):
    """The handler: join the spool's jobs with the live unit states, sorted by
    id. ``port`` and ``url`` come only from ``job.json``; the url's host is the
    loopback address, never the seat's netns address (interface 5). The config
    arms follow interface 2: a missing or null ``seats`` section defaults to
    ``spool_dir = /var/lib/seat/jobs``, and a missing directory yields an
    empty list, never a 500; a relative ``spool_dir`` is answered with an
    ``error``, never read from the process cwd."""
    seats = cfg.get("seats") or {}
    spool_dir = seats.get("spool_dir", _DEFAULT_SPOOL_DIR)
    spool_dir = str(spool_dir)
    if not pathlib.Path(spool_dir).is_absolute():
        return 200, {"seats": [], "error": "seats.spool_dir must be absolute"}
    jobs = read_jobs(spool_dir)
    # Deferred: api.py discovers this module during its own import, and the
    # test loads this module before api, so a top-level `import api` would be
    # circular. api.run is the production executor underneath _run.
    import api

    run = cfg.get("_run") or api.run
    states, unit_err = unit_states(run)
    rows = []
    for job_id in sorted(jobs):
        port = jobs[job_id]["port"]
        rows.append(
            {
                "id": job_id,
                "unit": f"seat@{job_id}.service",
                "state": states.get(job_id, "unknown"),
                "port": port,
                "url": f"http://127.0.0.1:{port}/" if port is not None else None,
                "exit_code": jobs[job_id]["exit_code"],
            }
        )
    body = {"seats": rows}
    if unit_err is not None:
        body["error"] = unit_err
    return 200, body


def start_seat(cfg, request):
    """POST /v1/seats — run ``seat-submit <mode> --workspace <path>
    --dsh-home <cfg> --model <cfg> --effort <cfg>`` and answer ``202 {"id":…}``
    with seat-submit's printed job id (interface 1). The body admits exactly
    ``{"mode","workspace"}``: any other key, a relative workspace or an unknown
    mode → 400. A non-zero seam returncode (a refusal 126, a timeout 124, an
    absent program 127, or seat-submit's exit 2) → 502 with an "error" body
    carrying the code and stderr — never 202 (HM5b). Never ``--port`` (SA3
    allocates); the three operator flags come from ``cfg["seats"]`` — never the
    request body — and are never omitted (interface 1/M9)."""
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 400, {"error": "body"}
    if not isinstance(body, dict) or set(body) != {"mode", "workspace"}:
        return 400, {"error": "body"}
    mode = body["mode"]
    workspace = body["workspace"]
    if mode not in ("web", "drive"):
        return 400, {"error": "mode"}
    if not isinstance(workspace, str) or not pathlib.Path(workspace).is_absolute():
        return 400, {"error": "workspace"}
    seats = cfg.get("seats") or {}
    argv = [
        "seat-submit",
        mode,
        "--workspace",
        workspace,
        "--dsh-home",
        seats.get("dsh_home", ""),
        "--model",
        seats.get("model", ""),
        "--effort",
        seats.get("effort", ""),
    ]
    cp = _executor(cfg)(argv)
    if cp.returncode != 0:
        return _refused_error("seat-submit", cp)
    return 202, {
        "id": (cp.stdout or "").strip().splitlines()[0]
        if (cp.stdout or "").strip()
        else ""
    }


def stop_seat(cfg, request):
    """POST /v1/seats/<id>/stop — ``systemctl stop seat@<id>.service`` through
    the seam (interface 2). The id must match the strict pattern (else 400) so
    the unit name is always ``seat@`` + id + ``.service`` and a traversal id
    can never name the profile-switch unit (M2). A non-zero seam returncode →
    502 with an "error" body carrying the code and stderr, never 202 (HM5b)."""
    seat_id = request.params.get("id", "")
    unit = _unit_name(seat_id)
    if unit is None:
        return 400, {"error": "id"}
    cp = _executor(cfg)(["systemctl", "stop", unit])
    if cp.returncode != 0:
        return _refused_error("systemctl stop", cp)
    return 202, {"id": seat_id, "unit": unit}


def attach_seat(cfg, request):
    """POST /v1/seats/<id>/attach — the loopback url from HM4's record
    (interface 3): ``200 {"url":"http://127.0.0.1:<port>/"}`` when the job has
    a port, ``409`` when it has none yet, ``404`` when there is no such job
    (M4). No process call: the port is read from the spool's ``job.json``. A
    relative ``spool_dir`` is a refusal, so it answers the same error shape as
    ``_refused_error`` — ``502 {"error": "seats.spool_dir must be absolute"}``,
    never a 200 without a ``url`` (HM5c), and is never read from the process
    cwd."""
    seat_id = request.params.get("id", "")
    if _unit_name(seat_id) is None:
        return 400, {"error": "id"}
    seats = cfg.get("seats") or {}
    spool_dir = str(seats.get("spool_dir", _DEFAULT_SPOOL_DIR))
    if not pathlib.Path(spool_dir).is_absolute():
        return 502, {"error": "seats.spool_dir must be absolute"}
    jobs = read_jobs(spool_dir)
    if seat_id not in jobs:
        return 404, {"error": "no such seat"}
    port = jobs[seat_id]["port"]
    if port is None:
        return 409, {"error": "no port"}
    return 200, {"url": f"http://127.0.0.1:{port}/"}
