"""streams — the declared stream/kind schema and the row fence (plan 2026-09-05-evidence-store, T1).

This module is stdlib-only and imports nothing from its siblings (`evidence.py`,
`judgements.py` import it). `KINDS` names every stream and the class each field
belongs to; `validate(kind, row)` walks a row against that class grammar and
returns *every* refusal reason without raising. The name fence (`FORBIDDEN`)
refuses prompt-shaped field names anywhere in the tree unless the field is a
`path` (the declared exception: `factory-finding.file`) or a closed-enum map key
(`helm-status`'s `host` tile). The secret scan (`SECRET_RE`) refuses key-shaped
tokens in every string value and every map key.
"""

from __future__ import annotations

import json
import os
import re

# --- the class grammar -------------------------------------------------------

ID_RE = re.compile(r"^[A-Za-z0-9._:+-]{1,120}$")
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}(/[a-z0-9][a-z0-9._-]{0,63})?$")
KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
REV_RE = re.compile(r"^[0-9a-f]{40}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")

ENVELOPE = ("v", "ts", "kind")
MAX_BYTES = 16384
MAX_DEPTH = 8

# design §3.5 fence 2, verbatim.
FORBIDDEN = frozenset(
    [
        "prompt",
        "prompts",
        "completion",
        "response",
        "content",
        "text",
        "message",
        "messages",
        "body",
        "transcript",
        "reasoning_text",
        "stdout",
        "stderr",
        "log",
        "output",
        "brief",
        "diff",
        "patch",
        "note",
        "notes",
        "title",
        "summary",
        "snippet",
        "excerpt",
        "path",
        "file",
        "file_path",
        "log_path",
        "cwd",
        "host",
        "hostname",
        "host_header",
        "sni",
        "url",
        "query",
        "client",
        "ip",
        "addr",
        "peer",
        "top_denied",
        "subject",
        "command",
        "cmd",
        "argv",
        "args",
        "env",
        "basket",
        "recipient",
        "user",
        "api_key",
        "key_name",
        "token",
        "secret",
        "password",
        "email",
        "slug",
    ]
)

SECRET_RE = re.compile(
    r"sk-or-v1-|sk-ant-|Bearer |-----BEGIN|AKIA[0-9A-Z]{16}|ghp_|xox[bp]-|"
    r"AGE-SECRET-KEY-|\bage1|\beyJ"
)

CLASSES_CHECK = (
    "unit",
    "eval",
    "vm",
    "nix-check",
    "curl",
    "browser",
    "operator",
    "unmeasured",
)
TILES = (
    "backup-parity",
    "backup-snapshot",
    "basket-doctor",
    "broker",
    "drift",
    "flake-check",
    "gpu",
    "host",
    "timers",
)
ERROR_CLASSES = (
    "budget-402",
    "provider-error",
    "unknown-model",
    "boot-failure",
    "no-result-line",
    "template-echo",
    "timeout",
    "submit-failed",
    "killed",
    "touches-violation",
    "checks-misreported",
    "checks-unverifiable",
    "verify-timeout",
    "probe-mismatch",
    "probe-missing",
    "none",
)
PLAN_DEFECTS = (
    "none",
    "vacuous",
    "missing-case",
    "underspecified",
    "wrong-fact",
    "implementer",
    "process",
)
REF = (
    "re",
    r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,119}$",
)  # a git ref; no '..' by the path rule
PLAN = ("path", ("docs/superpowers/plans/",), 120)

KINDS = {
    "check": {
        "stream": "checks",
        "v": 1,
        "key": None,
        "fields": {
            "name": "id",
            "rev": "rev",
            "ok": "bool",
            "class": ("enum", CLASSES_CHECK),
            "src": "id",
            "duration_s": "int",
            "log_tail": ("text", 4000),
        },
    },
    "helm-status": {
        "stream": "helm-status",
        "v": 1,
        "key": None,
        "fields": {
            "tiles": (
                "map",
                ("enum", TILES),
                16,
                ("enum", ("ok", "warn", "fail", "unknown")),
            ),
            "reason": ("enum", ("change", "heartbeat")),
        },
    },
    "factory-run": {
        "stream": "runs",
        "v": 1,
        "key": None,
        "shapes": {
            "A": {
                "run_id": ("null", "id"),
                "plan": PLAN,
                "prefix": "id",
                "baseline": "rev",
                "integration_branch": REF,
                "tasks": (
                    "list",
                    (
                        "obj",
                        {
                            "key": "key",
                            "status": "id",
                            "commit": ("null", "rev"),
                            "fixRounds": "int",
                        },
                    ),
                    64,
                ),
                "verify": ("enum", ("pass", "fail", "skipped", "none")),
                "delivered": "int",
                "agents": "int",
                "output_tokens": "int",
            },
            "B": {
                "run_id": "id",
                "driver": ("enum", ("seat",)),
                "event": ("enum", ("start", "end")),
                "repo": "id",
                "plan": ("null", PLAN),
                "base": ("null", "rev"),
                "groups": ("list", ("list", "key", 32), 32),
                "pid": ("null", "int"),
                "status": ("enum", ("done", "partial", "failed", "killed", "unknown")),
                "tasks": (
                    "list",
                    (
                        "obj",
                        {
                            "key": "key",
                            "status": (
                                "enum",
                                ("done", "partial", "failed", "skipped", "unknown"),
                            ),
                            "commit": ("null", "rev"),
                            "fix_rounds": "int",
                        },
                    ),
                    64,
                ),
            },
        },
    },
    "plan-judgement": {
        "stream": "plans",
        "v": 1,
        "key": ("plan", "revision"),
        "fields": {
            "plan": ("path", ("docs/",), 190),
            "spec": ("path", ("docs/",), 190),
            "author": ("re", r"^(fable|hand|dsh:[a-z0-9./-]{1,64})$"),
            "effort": (
                "enum",
                ("off", "low", "medium", "high", "xhigh", "max", "unknown"),
            ),
            "words": "int",
            "tasks": "int",
            "judges": ("list", ("enum", ("sonnet", "opus", "deepseek", "fable")), 3),
            "judges_dropped": (
                "list",
                ("enum", ("implementer", "reviewer", "whole")),
                3,
            ),
            "scores": ("list", ("int", 0, 3), 14),
            "total": "int",
            "self_score": ("null", ("int", 0, 42)),
            "threshold": "int",
            "decision": (
                "enum",
                ("dispatch", "revise", "revise-exhausted", "panel-short"),
            ),
            "revision": "int",
            "judged_ts": "ts",
            "judgement_path": ("path", ("docs/reviews/plan-judgements/",), 200),
        },
    },
    "task-result": {
        "stream": "derived/tasks",
        "v": 1,
        "key": ("run_id", "key"),
        "fields": {
            "run_id": "id",
            "key": "key",
            "repo": ("null", "id"),
            "plan": ("null", PLAN),
            "task_kind": ("enum", ("code", "docs", "unknown")),
            "size": ("enum", ("XS", "S", "M", "L", "unknown")),
            "model": "model-id",
            "effort": ("enum", ("off", "low", "medium", "high", "xhigh", "unknown")),
            "route": (
                "re",
                r"^(explicit|unknown|(implement|codex)/(code|docs)/(XS|S|M|L))$",
            ),
            "status": (
                "enum",
                ("done", "partial", "failed", "skipped", "unreported", "unknown"),
            ),
            "exit_code": ("null", "int"),
            "wall_s": ("null", "int"),
            "commits": "int",
            "commits_declared": ("null", "int"),
            "checks": (
                "map",
                ("re", r"^[a-z][a-z0-9-]{0,63}$"),
                64,
                ("enum", ("pass", "fail", "not-run")),
            ),
            "checks_parse": ("enum", ("ok", "refused", "missing")),
            "derived": ("null", ("list", ("enum", ("checks", "commits")), 2)),
            "checks_verified": (
                "null",
                (
                    "map",
                    ("re", r"^[a-z][a-z0-9-]{0,63}$"),
                    64,
                    (
                        "enum",
                        (
                            "pass",
                            "fail",
                            "not-run:absent",
                            "not-run:cache-miss",
                            "not-run:verify-timeout",
                        ),
                    ),
                ),
            ),
            "checks_scope": ("null", ("enum", ("clean", "dirty"))),
            "checks_scope_files": ("null", "int"),
            "verify_s": ("null", "int"),
            "probes_verified": (
                "null",
                (
                    "map",
                    ("re", r"^[a-z][a-z0-9-]{0,31}$"),
                    32,
                    ("enum", ("pass", "fail", "missing", "not-run", "drift")),
                ),
            ),
            "head": ("null", "rev"),
            "base": ("null", "rev"),
            "files_changed": "int",
            "insertions": "int",
            "deletions": "int",
            "touches_extra": ("null", "int"),
            "touches_disclosed": ("null", "int"),
            "usage": (
                "obj",
                {
                    "in": "int",
                    "out": "int",
                    "cache_read": "int",
                    "reasoning": "int",
                    "events": "int",
                    "duration_s": ("null", "num"),
                },
            ),
            "error_class": ("enum", ERROR_CLASSES),
            "seat_unit": ("null", ("re", r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")),
            "result_path": ("path", ("~/factory/runs/",), 200),
            "result_mtime": "ts",
        },
    },
    "gate-verdict": {
        "stream": "derived/gates",
        "v": 1,
        "key": ("review_path",),
        "fields": {
            "run_id": "id",
            "key": "key",
            "chain_root": "key",
            "round_kind": ("enum", ("first", "fix", "replan", "unknown")),
            "round": "int",
            "reviewer": ("enum", ("opus", "sonnet", "deepseek", "fable", "unknown")),
            "route": ("enum", ("claude", "openrouter")),
            "model": ("null", "model-id"),
            "verdict": ("enum", ("approved", "rejected", "unknown", "none")),
            "majors": ("null", "int"),
            "minors": ("null", "int"),
            "mutants_total": ("null", "int"),
            "mutants_killed": ("null", "int"),
            "mutants_outside_named": ("null", "int"),
            "plan_defect": ("null", ("enum", PLAN_DEFECTS)),
            "plan_defect_secondary": ("null", ("enum", PLAN_DEFECTS)),
            "gate_tokens": ("null", "int"),
            "wall_s": ("null", "int"),
            "review_path": ("path", ("docs/reviews/", "~/factory/runs/"), 200),
            "review_sha256": "hash",
            "review_commit": ("null", "rev"),
            "review_commit_ts": ("null", "ts"),
        },
    },
    "activity-day": {
        "stream": "ledger/activity-days",
        "v": 1,
        "key": ("date", "model"),
        "fields": {
            "date": ("re", r"^\d{4}-\d{2}-\d{2}$"),
            "model": "model-id",
            "requests": "int",
            "cost_usd": "num",
            "tokens_prompt": "int",
            "tokens_completion": "int",
            "tokens_reasoning": "int",
            "tokens_cached": "int",
            "cancelled": "int",
            "finish": (
                "obj",
                {"tool_calls": "int", "stop": "int", "length": "int", "other": "int"},
            ),
            "generation_ms_mean": ("null", "num"),
            "providers": "int",
        },
    },
    "factory-run-usage": {
        "stream": "ledger/factory-runs",
        "v": 1,
        "key": ("run_id",),
        "fields": {
            "src": ("enum", ("factory",)),
            "run_id": "id",
            "started": ("null", "ts"),
            "ended": ("null", "ts"),
            "plan": ("null", PLAN),
            "prefix": ("null", "id"),
            "repo": ("null", "id"),
            "tasks": (
                "list",
                (
                    "obj",
                    {
                        "key": "key",
                        "status": ("null", "id"),
                        "commit": ("null", "rev"),
                        "fix_rounds": "int",
                    },
                ),
                64,
            ),
            "agents": "int",
            "output_tokens": "int",
            "input_tokens": "int",
            "cache_read": "int",
            "cache_write": "int",
            "thinking": "int",
            "wall_s": "num",
        },
    },
    "factory-agent": {
        "stream": "ledger/factory-agents",
        "v": 1,
        "key": ("run_id", "agent_id"),
        "fields": {
            "src": ("enum", ("factory",)),
            "run_id": "id",
            "agent_id": "id",
            "label": ("null", "id"),
            "role_model": ("null", "model-id"),
            "model_id": ("null", "model-id"),
            "tokens": (
                "obj",
                {
                    "in": "int",
                    "out": "int",
                    "cache_read": "int",
                    "cache_write": "int",
                    "thinking": "int",
                },
            ),
            "wall_s": "num",
            "tool_uses": "int",
        },
    },
    "factory-finding": {
        "stream": "ledger/factory-findings",
        "v": 1,
        "key": ("run_id", "file", "title_sha256"),
        "fields": {
            "src": ("enum", ("factory",)),
            "run_id": "id",
            "task": ("null", "key"),
            "round": ("null", "int"),
            "label": ("null", "id"),
            "severity": "id",
            "file": ("path", ("",), 200),
            "title_sha256": "hash",
            "class": ("null", "id"),
        },
    },
    "dsh-session": {
        "stream": "ledger/dsh-sessions",
        "v": 1,
        "key": ("session_id",),
        "fields": {
            "src": ("enum", ("dsh",)),
            "session_id": "id",
            "role": ("null", "id"),
            "model": ("null", "model-id"),
            "started": ("null", "int"),
            "turns": "int",
            "steps": "int",
            "tools": "int",
            "in": "int",
            "out": "int",
            "cache_read": "int",
            "reasoning": "int",
            "wall_s": "num",
        },
    },
    "lane-job": {
        "stream": "ledger/lane-jobs",
        "v": 1,
        "key": ("lane", "job_id"),
        "fields": {
            "src": ("enum", ("lane",)),
            "lane": "id",
            "job_id": "id",
            "model": ("null", "model-id"),
            "provider": ("null", "id"),
            "ts_epoch": "num",
            "cost_usd": ("null", "num"),
        },
    },
    "openrouter-usage": {
        "stream": "ledger/openrouter-usage",
        "v": 1,
        "key": ("instance", "request_id"),
        "fields": {
            "src": ("enum", ("broker",)),
            "instance": "id",
            "request_id": ("re", r"^[0-9a-f]{32}$"),
            "ts_epoch": "num",
            "streamed": "bool",
            "http_status": "int",
            "status": ("enum", ("ok", "no-usage", "unparsed")),
            "gen_id": ("null", "id"),
            "model": ("null", "model-id"),
            "provider": ("null", "id"),
            "cost_usd": ("null", "num"),
            "upstream_cost_usd": ("null", "num"),
            "is_byok": ("null", "bool"),
            "prompt_tokens": ("null", "int"),
            "completion_tokens": ("null", "int"),
            "total_tokens": ("null", "int"),
            "cached_tokens": ("null", "int"),
            "cache_write_tokens": ("null", "int"),
            "reasoning_tokens": ("null", "int"),
        },
    },
}


class StreamRefused(ValueError):
    """A row (or a `replace_stream` batch) was refused; `.errors` lists every
    reason and `str()` joins them with `"; "`."""

    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


# --- name fence and secret scan ----------------------------------------------


def _forbidden_name(name):
    return name.lower().replace("-", "_") in FORBIDDEN


def _name_fence(name, cls=None):
    """True when `name` is a forbidden field name. A declared field of class
    `path` is the one exemption (`factory-finding.file`); a closed-enum map key
    is exempt at the map site alone (`helm-status`'s `host` tile), not here."""
    if isinstance(cls, tuple) and cls[0] == "path":
        return False
    return _forbidden_name(name)


def _scan_secret(value, path, errors):
    if not isinstance(value, str):
        return
    m = SECRET_RE.search(value)
    if m:
        errors.append(f"{path}: secret shape {m.group(0)}")


# --- the recursive class walk ------------------------------------------------


def _is_path(cls):
    return isinstance(cls, tuple) and cls[0] == "path"


def _check_path(cls, value, path, errors):
    roots, cap = cls[1], cls[2]
    if not isinstance(value, str):
        errors.append(f"{path}: not a string")
        return
    if "\n" in value:
        errors.append(f"{path}: newline")
    if len(value) > cap:
        errors.append(f"{path}: over cap {cap}")
    for root in roots:
        if root.startswith(("~/", "/")):
            expanded = os.path.expanduser(root)
            if os.path.realpath(os.path.expanduser(value)).startswith(expanded):
                return
        else:
            if value.startswith(root):
                if value.startswith("/"):
                    continue
                if ".." in value.split("/"):
                    errors.append(f"{path}: '..' segment")
                    return
                return
    errors.append(f"{path}: outside root {roots[0]}")


def _check_cls(cls, value, path, depth, errors):
    """The class dispatch; the secret scan and depth cap happen in `_check`
    before this runs (so a `null` wrapper re-enters here without double work)."""
    if value is None:
        if not (isinstance(cls, tuple) and cls[0] == "null"):
            errors.append(f"{path}: null not allowed")
        return
    if cls == "id":
        if not (isinstance(value, str) and ID_RE.fullmatch(value)):
            errors.append(f"{path}: not a id")
    elif cls == "model-id":
        if not (isinstance(value, str) and MODEL_ID_RE.fullmatch(value)):
            errors.append(f"{path}: not a model-id")
    elif cls == "key":
        if not (isinstance(value, str) and KEY_RE.fullmatch(value)):
            errors.append(f"{path}: not a key")
    elif cls == "rev":
        if not (isinstance(value, str) and REV_RE.fullmatch(value)):
            errors.append(f"{path}: not a rev")
    elif cls == "ts":
        if not (isinstance(value, str) and TS_RE.fullmatch(value)):
            errors.append(f"{path}: not a ts")
    elif cls == "hash":
        if not (isinstance(value, str) and HASH_RE.fullmatch(value)):
            errors.append(f"{path}: not a hash")
    elif cls == "int":
        if not (isinstance(value, int) and not isinstance(value, bool)):
            errors.append(f"{path}: not a int")
    elif isinstance(cls, tuple) and cls[0] == "int":
        lo, hi = cls[1], cls[2]
        if not (
            isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi
        ):
            errors.append(f"{path}: not a int")
    elif cls == "num":
        if not (isinstance(value, (int, float)) and not isinstance(value, bool)):
            errors.append(f"{path}: not a num")
    elif cls == "bool":
        if not isinstance(value, bool):
            errors.append(f"{path}: not a bool")
    elif isinstance(cls, tuple) and cls[0] == "enum":
        if value not in cls[1]:
            errors.append(f"{path}: not in enum ({'|'.join(cls[1])})")
    elif isinstance(cls, tuple) and cls[0] == "path":
        _check_path(cls, value, path, errors)
    elif isinstance(cls, tuple) and cls[0] == "text":
        if not isinstance(value, str):
            errors.append(f"{path}: not a string")
        elif len(value) > cls[1]:
            errors.append(f"{path}: over cap {cls[1]}")
    elif isinstance(cls, tuple) and cls[0] == "re":
        if not (isinstance(value, str) and re.fullmatch(cls[1], value)):
            errors.append(f"{path}: not a re")
    elif isinstance(cls, tuple) and cls[0] == "null":
        if value is not None:
            _check_cls(cls[1], value, path, depth, errors)
    elif isinstance(cls, tuple) and cls[0] == "obj":
        _check_obj(cls[1], value, path, depth, errors)
    elif isinstance(cls, tuple) and cls[0] == "list":
        _check_list(cls, value, path, depth, errors)
    elif isinstance(cls, tuple) and cls[0] == "map":
        _check_map(cls, value, path, depth, errors)


def _check_obj(fields, value, path, depth, errors):
    if not isinstance(value, dict):
        errors.append(f"{path}: not a object")
        return
    for key, sub in value.items():
        p = f"{path}.{key}"
        subcls = fields.get(key)
        if subcls is None:
            if _name_fence(key):
                errors.append(f"{p}: forbidden name")
            errors.append(f"{p}: undeclared field")
            continue
        if _name_fence(key, subcls):
            errors.append(f"{p}: forbidden name")
        _check(subcls, sub, p, depth + 1, errors)


def _check_list(cls, value, path, depth, errors):
    elem_cls, cap = cls[1], cls[2]
    if not isinstance(value, (list, tuple)):
        errors.append(f"{path}: not a list")
        return
    if len(value) > cap:
        errors.append(f"{path}: over cap {cap}")
    for i, item in enumerate(value):
        _check(elem_cls, item, f"{path}[{i}]", depth + 1, errors)


def _check_map(cls, value, path, depth, errors):
    kcls, cap, vcls = cls[1], cls[2], cls[3]
    if not isinstance(value, dict):
        errors.append(f"{path}: not a map")
        return
    if len(value) > cap:
        errors.append(f"{path}: over cap {cap}")
    enum_keys = isinstance(kcls, tuple) and kcls[0] == "enum"
    for k, v in value.items():
        p = f"{path}.{k}"
        if not enum_keys and _name_fence(k, kcls):
            errors.append(f"{p}: forbidden name")
        _check(kcls, k, p, depth + 1, errors)
        _check(vcls, v, p, depth + 1, errors)


def _check(cls, value, path, depth, errors):
    if depth > MAX_DEPTH:
        errors.append(f"depth over 8 at {path}")
        return
    if isinstance(value, str):
        _scan_secret(value, path, errors)
    _check_cls(cls, value, path, depth, errors)


# --- the public fence --------------------------------------------------------


def _row_bytes(row):
    try:
        return len(json.dumps(row, sort_keys=True, separators=(",", ":")))
    except (RecursionError, ValueError, TypeError):
        return 0


def _fields_for(entry, row):
    shapes = entry.get("shapes")
    if shapes is None:
        return entry["fields"]
    driver = row.get("driver")
    if driver is None:
        return shapes["A"]
    if driver == "seat":
        return shapes["B"]
    return None


def _check_row(fields, row, errors):
    for key, value in row.items():
        if key in ENVELOPE:
            continue
        cls = fields.get(key)
        if cls is None:
            if _name_fence(key):
                errors.append(f"{key}: forbidden name")
            errors.append(f"{key}: undeclared field")
            continue
        if _name_fence(key, cls):
            errors.append(f"{key}: forbidden name")
        _check(cls, value, key, 0, errors)


def validate(kind, row):
    """Every refusal reason for `row` as a `kind` entry; `[]` means it is
    accepted. Never raises."""
    if kind not in KINDS:
        return [f"undeclared kind {kind!r}"]
    entry = KINDS[kind]
    fields = _fields_for(entry, row)
    if fields is None:
        return ["driver: not in enum (seat)"]
    errors = []
    n = _row_bytes(row)
    if n > MAX_BYTES:
        errors.append(f"row over {MAX_BYTES} bytes ({n})")
    _check_row(fields, row, errors)
    return errors


def stream_of(kind, row):
    """The declared stream name for a (known) kind."""
    return KINDS[kind]["stream"]


def key_of(kind, row):
    """The key-field values for a (known) kind, an empty tuple when keyless."""
    key = KINDS[kind]["key"]
    if key is None:
        return ()
    return tuple(row[f] for f in key)


def judgement_fields():
    """The 14 `plan-judgement` field names in entry order, minus `judged_ts`
    and `judgement_path`."""
    return tuple(
        f
        for f in KINDS["plan-judgement"]["fields"]
        if f not in ("judged_ts", "judgement_path")
    )
