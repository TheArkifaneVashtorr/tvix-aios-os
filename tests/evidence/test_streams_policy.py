"""The fence: `streams.py` declares every kind and validates every row before
the lock (plan 2026-09-05-evidence-store, T1).

One test per fence rule, each with a discriminating fixture and a named
one-line mutant that would turn it red. `streams`, `evidence` and `judgements`
are loaded the way `test_evidence.py` loads `evidence`: from `pkgs/evidence`,
never from the host's packaged modules.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()


def _load(name):
    candidates = [
        HERE.parents[2] / "pkgs" / "evidence" / f"{name}.py",
        pathlib.Path("pkgs") / "evidence" / f"{name}.py",
    ]
    src = next(p for p in candidates if p.exists())
    if str(src.parent) not in sys.path:
        sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location(name, src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


streams = _load("streams")
evidence = _load("evidence")
judgements = _load("judgements")

REV_A = "a" * 40
REV_B = "b" * 40
HASH64 = "a" * 64


@pytest.fixture
def t_kind(monkeypatch):
    monkeypatch.setitem(
        streams.KINDS,
        "t",
        {
            "stream": "runs",
            "v": 1,
            "key": ("i", "j"),
            "fields": {
                "i": "int",
                "j": "int",
                "pad": ("text", 20000),
                "deep": ("obj", {"a": ("obj", {"b": "int"})}),
            },
        },
    )


def check_row(**over):
    row = {
        "kind": "check",
        "name": "lint",
        "rev": REV_A,
        "ok": True,
        "class": "unit",
        "src": "x",
        "duration_s": 3,
        "log_tail": "t",
    }
    row.update(over)
    return row


SHAPE_A = {
    "kind": "factory-run",
    "run_id": None,
    "plan": "docs/superpowers/plans/x.md",
    "prefix": "ev",
    "baseline": REV_A,
    "integration_branch": "factory/ev-integration",
    "tasks": [{"key": "E1", "status": "landed", "commit": REV_B, "fixRounds": 0}],
    "verify": "pass",
    "delivered": 1,
    "agents": 3,
    "output_tokens": 12,
}

SHAPE_B = {
    "kind": "factory-run",
    "run_id": "r1",
    "driver": "seat",
    "event": "start",
    "repo": "repo1",
    "plan": None,
    "base": None,
    "groups": [],
    "pid": None,
    "status": "done",
    "tasks": [],
}

PLAN_JUDGEMENT = {
    "kind": "plan-judgement",
    "plan": "docs/superpowers/plans/x.md",
    "spec": "docs/superpowers/specs/y.md",
    "author": "fable",
    "effort": "max",
    "words": 6140,
    "tasks": 9,
    "judges": ["sonnet", "opus"],
    "judges_dropped": [],
    "scores": [3, 2, 3, 3, 2, 3, 3, 3, 3, 3, 2, 2, 3, 3],
    "total": 38,
    "self_score": 40,
    "threshold": 34,
    "decision": "dispatch",
    "revision": 0,
    "judged_ts": "2026-09-06T05:39:00Z",
    "judgement_path": "docs/reviews/plan-judgements/good.md",
}

TASK_RESULT = {
    "kind": "task-result",
    "run_id": "r1",
    "key": "T1",
    "repo": "repo1",
    "plan": "docs/superpowers/plans/x.md",
    "task_kind": "code",
    "size": "M",
    "model": "deepseek/deepseek-v4-pro-0813",
    "effort": "high",
    "route": "explicit",
    "status": "done",
    "exit_code": 0,
    "wall_s": 12,
    "commits": 1,
    "commits_declared": None,
    "checks": {"unit": "pass"},
    "checks_parse": "ok",
    "head": REV_A,
    "base": REV_B,
    "files_changed": 3,
    "insertions": 10,
    "deletions": 2,
    "usage": {
        "in": 100,
        "out": 200,
        "cache_read": 300,
        "reasoning": 400,
        "events": 5,
        "duration_s": 12.5,
    },
    "error_class": "none",
    "seat_unit": None,
    "result_path": os.path.expanduser("~/factory/runs/r/K.result"),
    "result_mtime": "2026-09-06T05:39:00Z",
}

GATE_VERDICT = {
    "kind": "gate-verdict",
    "run_id": "r1",
    "key": "T1",
    "chain_root": "T1",
    "round_kind": "first",
    "round": 0,
    "reviewer": "opus",
    "route": "claude",
    "model": None,
    "verdict": "approved",
    "majors": None,
    "minors": None,
    "mutants_total": None,
    "mutants_killed": None,
    "mutants_outside_named": None,
    "plan_defect": None,
    "plan_defect_secondary": None,
    "gate_tokens": None,
    "wall_s": None,
    "review_path": "docs/reviews/x.md",
    "review_sha256": HASH64,
    "review_commit": REV_A,
    "review_commit_ts": "2026-09-06T05:39:00Z",
}

# Every enum-classed field of `task-result` and `gate-verdict`, copied from the
# plan's Interfaces table (2026-09-06-telemetry-store-1.md), never derived from
# `streams.KINDS`. A deleted, added or renamed arm must turn row 13 red.
ENUM_ARMS = {
    ("task-result", "task_kind"): ("code", "docs", "unknown"),
    ("task-result", "size"): ("XS", "S", "M", "L", "unknown"),
    ("task-result", "effort"): ("off", "low", "medium", "high", "xhigh", "unknown"),
    ("task-result", "status"): (
        "done",
        "partial",
        "failed",
        "skipped",
        "unreported",
        "unknown",
    ),
    ("task-result", "checks_parse"): ("ok", "refused", "missing"),
    ("task-result", "error_class"): (
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
        "probe-env",
        "none",
    ),
    ("task-result", "checks_scope"): ("clean", "dirty"),
    ("gate-verdict", "round_kind"): ("first", "fix", "replan", "unknown"),
    ("gate-verdict", "reviewer"): (
        "opus",
        "sonnet",
        "deepseek",
        "fable",
        "glm",
        "kimi",
        "unknown",
    ),
    ("gate-verdict", "route"): ("claude", "openrouter"),
    ("gate-verdict", "verdict"): ("approved", "rejected", "unknown", "none"),
    ("gate-verdict", "plan_defect"): (
        "none",
        "vacuous",
        "missing-case",
        "underspecified",
        "wrong-fact",
        "implementer",
        "process",
    ),
    ("gate-verdict", "plan_defect_secondary"): (
        "none",
        "vacuous",
        "missing-case",
        "underspecified",
        "wrong-fact",
        "implementer",
        "process",
    ),
}

ACTIVITY_DAY = {
    "kind": "activity-day",
    "date": "2026-09-06",
    "model": "deepseek/deepseek-v4-pro-0813",
    "requests": 1,
    "cost_usd": 0.5,
    "tokens_prompt": 1,
    "tokens_completion": 1,
    "tokens_reasoning": 1,
    "tokens_cached": 1,
    "cancelled": 0,
    "finish": {"tool_calls": 1, "stop": 1, "length": 1, "other": 1},
    "generation_ms_mean": None,
    "providers": 1,
}

FACTORY_RUN_USAGE = {
    "kind": "factory-run-usage",
    "src": "factory",
    "run_id": "r1",
    "started": None,
    "ended": None,
    "plan": None,
    "prefix": None,
    "repo": None,
    "tasks": [],
    "agents": 2,
    "output_tokens": 10,
    "input_tokens": 20,
    "cache_read": 30,
    "cache_write": 40,
    "thinking": 50,
    "wall_s": 1.5,
}

FACTORY_AGENT = {
    "kind": "factory-agent",
    "src": "factory",
    "run_id": "r1",
    "agent_id": "a1",
    "label": None,
    "role_model": None,
    "model_id": None,
    "tokens": {"in": 1, "out": 2, "cache_read": 3, "cache_write": 4, "thinking": 5},
    "wall_s": 1.0,
    "tool_uses": 2,
}

FACTORY_FINDING = {
    "kind": "factory-finding",
    "src": "factory",
    "run_id": "r1",
    "task": None,
    "round": None,
    "label": None,
    "severity": "major",
    "file": "pkgs/x.py",
    "title_sha256": HASH64,
    "class": None,
}

DSH_SESSION = {
    "kind": "dsh-session",
    "src": "dsh",
    "session_id": "s1",
    "role": None,
    "model": None,
    "started": None,
    "turns": 1,
    "steps": 2,
    "tools": 3,
    "in": 10,
    "out": 20,
    "cache_read": 30,
    "reasoning": 40,
    "wall_s": 1.0,
}

LANE_JOB = {
    "kind": "lane-job",
    "src": "lane",
    "lane": "openrouter",
    "job_id": "j1",
    "model": None,
    "provider": None,
    "ts_epoch": 1788546900.0,
    "cost_usd": None,
}

OPENROUTER_USAGE = {
    "kind": "openrouter-usage",
    "src": "broker",
    "instance": "openrouter",
    "request_id": "a" * 32,
    "ts_epoch": 1788546900.0,
    "streamed": True,
    "http_status": 200,
    "status": "ok",
    "gen_id": None,
    "model": "deepseek/deepseek-v4-flash",
    "provider": "DeepInfra",
    "cost_usd": 9.9e-07,
    "upstream_cost_usd": 9.9e-07,
    "is_byok": False,
    "prompt_tokens": 7,
    "completion_tokens": 2,
    "total_tokens": 9,
    "cached_tokens": 0,
    "cache_write_tokens": 0,
    "reasoning_tokens": 0,
}

LIMIT_EVENT = {
    "kind": "limit-event",
    "src": "transcript",
    "session_id": "sess_1",
    "request_id": "req_1",
    "at": "2026-09-08T17:37:00.123Z",
    "api_error_status": 429,
    "error_kind": "rate_limit",
    "rate_limit_type": "five_hour",
    "limit_status": "rejected",
    "resets_at": 1788680400,
    "overage_status": "rejected",
    "overage_disabled_reason": "org_level_disabled",
    "is_using_overage": False,
    "fallback_available": False,
    "origin": "agent",
}

MAIN_SESSION = {
    "kind": "main-session",
    "src": "transcript",
    "session_id": "sess_main",
    "harness_version": None,
    "started": None,
    "ended": None,
    "message_count": 3,
    "tool_uses": 2,
    "limit_events": 1,
    "tokens": {"in": 1, "out": 2, "cache_read": 3, "cache_write": 4, "thinking": 5},
    "by_model": [
        {
            "model": "claude-opus-5",
            "model_suffix": "1m",
            "message_count": 3,
            "in": 1,
            "out": 2,
            "cache_read": 3,
            "cache_write": 4,
            "thinking": 5,
        }
    ],
    "wall_s": 1.0,
}

OTEL_CLAUDE_TOKENS = {
    "kind": "otel-claude",
    "src": "otel",
    "session_id": "sess-fixture",
    "sample_id": "tokens:input:claude-opus-5:1m:1788906253213778862",
    "sample": "tokens",
    "at": "2026-09-08T22:24:13.213778Z",
    "model": "claude-opus-5",
    "model_suffix": "1m",
    "harness_version": "2.1.258",
    "terminal_type": "probe",
    "query_source": None,
    "speed": None,
    "effort": None,
    "agent_name": None,
    "skill_name": None,
    "request_id": None,
    "cost_usd": None,
    "duration_ms": None,
    "input_tokens": None,
    "output_tokens": None,
    "cache_read_tokens": None,
    "cache_creation_tokens": None,
    "token_type": "input",
    "value": 10.0,
}

OTEL_CLAUDE_REQUEST = {
    "kind": "otel-claude",
    "src": "otel",
    "session_id": "sess-fixture",
    "sample_id": "req_fixture",
    "sample": "request",
    "at": "2026-09-08T22:24:13.213778Z",
    "model": "claude-opus-5",
    "model_suffix": None,
    "harness_version": "2.1.258",
    "terminal_type": "probe",
    "query_source": "main",
    "speed": "medium",
    "effort": "high",
    "agent_name": "gate-reviewer",
    "skill_name": "code-review",
    "request_id": "req_fixture",
    "cost_usd": 0.0123,
    "duration_ms": 1200,
    "input_tokens": 2,
    "output_tokens": 77,
    "cache_read_tokens": 1000,
    "cache_creation_tokens": 500,
    "token_type": None,
    "value": None,
}

# --- DS2: the debug-usage kind, what a sweep run cost ---

DEBUG_USAGE = {
    "batch": "2026-09-24T0210",
    "item": "item-01",
    "rung": 1,
    "model": "sonnet",
    "status": "done",
    "confidence": "probable",
    "wall_s": 412,
    "signature": "seat:no-result-line:EV21",
    "cost_usd": 1.37,
    "input_tokens": 120000,
    "output_tokens": 9000,
    "cache_read_tokens": 400000,
    "cache_creation_tokens": 20000,
    "num_turns": 31,
    "session_id": "ab12cd34",
}

# --- OC1: the operator-ask kind, attribution, rung, area, the widened fence ---

OPERATOR_ASK = {
    "kind": "operator-ask",
    "session": "0123456789abcdef",
    "ask_id": "fedcba9876543210",
    "phase": "answer",
    "header": "Scope",
    "options": 3,
    "recommended_index": 0,
    "chosen_index": 1,
    "took_recommended": False,
    "latency_s": 42,
    "key": "OC4",
    "surface": "chat",
    "src": "hook",
}

VALID_ROWS = [
    ("check", check_row()),
    (
        "helm-status",
        {"kind": "helm-status", "tiles": {"drift": "ok"}, "reason": "change"},
    ),
    ("factory-run", SHAPE_A),
    ("factory-run", SHAPE_B),
    ("plan-judgement", PLAN_JUDGEMENT),
    ("task-result", TASK_RESULT),
    ("gate-verdict", GATE_VERDICT),
    ("operator-ask", OPERATOR_ASK),
    ("activity-day", ACTIVITY_DAY),
    ("factory-run-usage", FACTORY_RUN_USAGE),
    ("factory-agent", FACTORY_AGENT),
    ("factory-finding", FACTORY_FINDING),
    ("dsh-session", DSH_SESSION),
    ("lane-job", LANE_JOB),
    ("openrouter-usage", OPENROUTER_USAGE),
    ("limit-event", LIMIT_EVENT),
    ("main-session", MAIN_SESSION),
    ("otel-claude", OTEL_CLAUDE_TOKENS),
    ("otel-claude", OTEL_CLAUDE_REQUEST),
]


@pytest.mark.parametrize("kind,row", VALID_ROWS)
def test_one_valid_row_per_kind_and_shape(kind, row):
    # mutant: remove any one field from its KINDS entry -> `undeclared field`.
    assert streams.validate(kind, row) == []


def test_openrouter_usage_refusals():
    # mutant: declare `cost_usd` as `("null", "id")` -> the string passes;
    # declare `model` as `("null", "id")` -> "Bad Model" passes; drop an arm
    # from `status` -> "weird" is refused by enum membership instead of range.
    assert streams.validate(
        "openrouter-usage", {**OPENROUTER_USAGE, "cost_usd": "9.9e-07"}
    ) == ["cost_usd: not a num"]
    assert streams.validate(
        "openrouter-usage", {**OPENROUTER_USAGE, "model": "Bad Model"}
    ) == ["model: not a model-id"]
    assert streams.validate(
        "openrouter-usage", {**OPENROUTER_USAGE, "status": "weird"}
    ) == ["status: not in enum (ok|no-usage|unparsed)"]


def test_openrouter_usage_request_id_regex_is_hex():
    # mutant: widen `request_id`'s class to plain "id" -> the 32-char non-hex
    # id passes instead of being refused by the regex.
    assert streams.validate(
        "openrouter-usage", {**OPENROUTER_USAGE, "request_id": "g" * 32}
    ) == ["request_id: not a re"]


def test_openrouter_usage_key_discriminates_request_id(tmp_path):
    # mutant: reduce `key` to ("instance",) -> the two rows sharing an
    # instance collapse to one on the same-instance write.
    rows = [
        {**OPENROUTER_USAGE, "request_id": "a" * 32},
        {**OPENROUTER_USAGE, "request_id": "b" * 32},
    ]
    evidence.replace_stream(str(tmp_path), "ledger/openrouter-usage", rows)
    assert len(evidence.read(str(tmp_path), "ledger/openrouter-usage")) == 2


def test_openrouter_usage_fixture_validates_and_is_terminated():
    # mutant: drop the trailing newline again -> the last-byte assertion fails,
    # the missing sigil being indistinguishable from a torn last line.
    p = HERE.parent / "fixtures" / "openrouter-usage" / "usage.jsonl"
    assert p.read_bytes().endswith(b"\n")
    rows = [json.loads(line) for line in p.read_text().splitlines()]
    assert len(rows) == 4
    assert [streams.validate("openrouter-usage", r) for r in rows[:3]] == [[], [], []]
    assert streams.validate("openrouter-usage", rows[3]) == ["model: not a model-id"]


def test_limit_event_and_main_session_are_declared():
    # mutant: drop either kind from KINDS (or the factory-agent additions)
    # -> KeyError before a single row is validated.
    assert streams.KINDS["limit-event"]["stream"] == "ledger/limit-events"
    assert streams.KINDS["limit-event"]["key"] == ("session_id", "request_id")
    assert streams.KINDS["main-session"]["stream"] == "ledger/main-sessions"
    assert streams.KINDS["main-session"]["key"] == ("session_id",)
    assert streams.KINDS["factory-agent"]["fields"]["message_count"] == "int"
    assert streams.KINDS["factory-agent"]["fields"]["model_suffix"] == ("null", "id")


def test_limit_event_and_factory_agent_refusals():
    # mutant: declare `origin` as a plain "id" -> "other" passes instead of
    # being refused; declare `factory-agent.message_count` as anything but
    # "int" -> the string passes instead of `not a int`.
    assert streams.validate("limit-event", {**LIMIT_EVENT, "origin": "other"}) == [
        "origin: not in enum (main|agent)"
    ]
    assert streams.validate(
        "factory-agent", {**FACTORY_AGENT, "message_count": "3"}
    ) == ["message_count: not a int"]


def test_otel_claude_sample_enum_and_identity_fields():
    # The `sample` field is the two-arm enum `request|tokens`. Mutant: widen
    # `sample` to a plain "id" -> "metric" passes instead of being refused.
    assert streams.validate(
        "otel-claude", {**OTEL_CLAUDE_TOKENS, "sample": "metric"}
    ) == ["sample: not in enum (request|tokens)"]


def test_debug_usage_fixture_row_validates():
    # mutant: delete the KINDS entry -> ["undeclared kind 'debug-usage'"].
    assert streams.validate("debug-usage", DEBUG_USAGE) == []


def test_debug_usage_nullable_fields_accept_none():
    # mutants, one per field: cost_usd bare "num" / num_turns bare "int" /
    # session_id bare "id" -> the None row is refused on that field.
    row = {**DEBUG_USAGE, "cost_usd": None, "num_turns": None, "session_id": None}
    assert streams.validate("debug-usage", row) == []


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("rung", 3, "rung: not a int"),
        ("status", "partial", "status: not in enum (done|failed|timeout)"),
        (
            "confidence",
            "maybe",
            "confidence: not in enum (confirmed|probable|unknown|none)",
        ),
        ("signature", "gate:x", "signature: not a re"),
        ("wall_s", 86_401, "wall_s: not a int"),
        ("session_id", "bad id!", "session_id: not a id"),
    ],
)
def test_debug_usage_refuses_out_of_class_values(field, value, message):
    # one mutant per row: widen rung to "int"; drop "timeout" from status; add
    # "maybe" to confidence; loosen the signature regex to ".+"; raise wall_s's
    # bound; make session_id ("null", "text") -> that row's refusal vanishes.
    assert streams.validate("debug-usage", {**DEBUG_USAGE, field: value}) == [message]


def test_debug_usage_refuses_an_undeclared_text_field():
    # mutant: declare "symptom": ("text", 200) -> the refusal vanishes.
    assert streams.validate("debug-usage", {**DEBUG_USAGE, "symptom": "x"}) == [
        "symptom: undeclared field"
    ]


def test_debug_usage_note_hits_the_name_fence_and_the_undeclared_rule():
    # mutant: declare "note": ("text", 200) -> only "note: forbidden name" is
    # left (the fence still fires; the undeclared line vanishes).
    assert streams.validate("debug-usage", {**DEBUG_USAGE, "note": "x"}) == [
        "note: forbidden name",
        "note: undeclared field",
    ]


def test_factory_finding_accepts_null_severity_and_file():
    # A string finding builds a row with severity/file/class = None; the kind
    # must admit the null severity and null file (class is already nullable).
    # mutant: revert `severity` to bare "id" and `file` to ("path", ("",), 200)
    # -> the null row is refused by _check_cls's null branch.
    assert (
        streams.validate(
            "factory-finding", {**FACTORY_FINDING, "severity": None, "file": None}
        )
        == []
    )


@pytest.mark.parametrize(
    "route",
    ("codex/docs/M", "codex/code/XS", "implement/code/S", "explicit", "unknown"),
)
def test_route_accepts_every_supported_family_and_arm(route):
    # mutant: leave the regex -> `["route: not a re"]`.
    assert streams.validate("task-result", {**TASK_RESULT, "route": route}) == []


@pytest.mark.parametrize(
    "route",
    ("codex/any/any", "codex", "Codex/code/XS", "codex/code/XL"),
)
def test_route_refuses_outside_the_fence(route):
    # mutant: `codex/[a-z]+/[a-z]+` -> `codex/any/any` passes.
    assert streams.validate("task-result", {**TASK_RESULT, "route": route}) == [
        "route: not a re"
    ]


def test_route_regex_is_the_literal_pin():
    # mutant: any drift of the pattern.
    assert streams.KINDS["task-result"]["fields"]["route"][1] == (
        r"^(explicit|unknown|(implement|codex)/(code|docs)/(XS|S|M|L))$"
    )


def test_one_invalid_row_per_kind_reports_exact_enum_reason():
    assert streams.validate("check", check_row(**{"class": "guess"})) == [
        "class: not in enum (unit|eval|vm|nix-check|curl|browser|operator|unmeasured)"
    ]
    # the one stray `status=pass` in the corpus
    assert (
        "status: not in enum (done|partial|failed|skipped|unreported|unknown)"
        in streams.validate("task-result", {**TASK_RESULT, "status": "pass"})
    )
    assert streams.validate("gate-verdict", {**GATE_VERDICT, "verdict": "rework"}) == [
        "verdict: not in enum (approved|rejected|unknown|none)"
    ]
    assert streams.validate("factory-run", {**SHAPE_A, "driver": "dark-factory"}) == [
        "driver: not in enum (seat)"
    ]


def test_unknown_kind_is_undeclared():
    assert streams.validate("nope", {"kind": "nope"}) == ["undeclared kind 'nope'"]


def _walk_fields(fields, check):
    for name, cls in fields.items():
        check(name, cls)
        if isinstance(cls, tuple) and cls[0] == "obj":
            _walk_fields(cls[1], check)


def test_declared_field_walk_none_forbidden_but_path():
    # mutant: drop the path exemption -> `file` refuses; add `output` to any
    # entry -> the walk refuses it.
    assert streams._name_fence("file", "id") is True
    assert streams._name_fence("file", ("path", ("",), 200)) is False
    visited = set()

    def check(name, cls):
        visited.add(name)
        assert not streams._name_fence(name, cls), name

    for entry in streams.KINDS.values():
        if "fields" in entry:
            _walk_fields(entry["fields"], check)
        for shape in entry.get("shapes", {}).values():
            _walk_fields(shape, check)
    assert "file" in visited


def test_name_fence_exempts_path_only_not_enum():
    # mutant: put `enum` back in `_name_fence`'s exemption -> the `host` arm
    # goes red (`assert True is False`) and the map-site guard dies again.
    assert streams._name_fence("host", ("enum", ("ok",))) is True
    assert streams._name_fence("file", ("path", ("docs",), 200)) is False


def _declared_field_names(entry):
    names = []

    def walk(fields):
        for name, cls in fields.items():
            names.append(name)
            if isinstance(cls, tuple) and cls[0] == "obj":
                walk(cls[1])

    if "fields" in entry:
        walk(entry["fields"])
    for shape in entry.get("shapes", {}).values():
        walk(shape)
    return names


def test_no_declared_field_is_named_envelope():
    # mutant: declare `"kind"` (or `v`/`ts`) again on any kind -> red.
    for kind, entry in streams.KINDS.items():
        for name in _declared_field_names(entry):
            assert name not in streams.ENVELOPE, (kind, name)


def test_undeclared_forbidden_field_reports_both():
    errs = streams.validate("check", {"kind": "check", "name": "lint", "prompt": "x"})
    assert "prompt: undeclared field" in errs
    assert "prompt: forbidden name" in errs


def test_answer_and_name_fences_are_independent(monkeypatch):
    row = {"kind": "check", "name": "lint", "prompt": "x"}
    monkeypatch.setattr(streams, "FORBIDDEN", frozenset())
    assert "prompt: undeclared field" in streams.validate("check", row)
    monkeypatch.undo()
    monkeypatch.setitem(streams.KINDS["check"]["fields"], "prompt", "id")
    errs = streams.validate("check", row)
    assert "prompt: forbidden name" in errs
    assert "prompt: undeclared field" not in errs


def test_name_fence_at_depth_and_enum_key_exemption():
    errs = streams.validate("task-result", {**TASK_RESULT, "usage": {"output": 1}})
    assert "usage.output: forbidden name" in errs
    assert "usage.output: undeclared field" in errs
    assert (
        streams.validate(
            "helm-status",
            {"kind": "helm-status", "tiles": {"host": "ok"}, "reason": "change"},
        )
        == []
    )


def test_id_class_boundaries():
    assert streams.validate("check", check_row(src="a" * 120)) == []
    assert "src: not a id" in streams.validate("check", check_row(src="a" * 121))
    assert "src: not a id" in streams.validate("check", check_row(src="two words"))
    assert "src: not a id" in streams.validate(
        "check", check_row(src="/home/x/baskets/a.md")
    )
    assert "src: not a id" in streams.validate("check", check_row(src="a@b.c"))


def test_secret_scan_in_values_and_map_keys():
    assert streams.validate("check", check_row(src="sk-or-v1-abc")) == [
        "src: secret shape sk-or-v1-"
    ]
    assert streams.validate("check", check_row(src="skor-v1-abc")) == []
    assert streams.validate("check", check_row(src="age1qxyz")) == [
        "src: secret shape age1"
    ]
    assert streams.validate("check", check_row(src="stage1qxyz")) == []
    assert streams.validate("check", check_row(src="eyJabc")) == [
        "src: secret shape eyJ"
    ]
    assert streams.validate("check", check_row(src="keyJabc")) == []
    errs = streams.validate("task-result", {**TASK_RESULT, "checks": {"ghp_x": "pass"}})
    assert "checks.ghp_x: secret shape ghp_" in errs


def test_log_tail_cap_and_allowlist_is_load_bearing(monkeypatch):
    assert streams.validate("check", check_row(log_tail="t" * 4000)) == []
    assert streams.validate("check", check_row(log_tail="t" * 4001)) == [
        "log_tail: over cap 4000"
    ]
    monkeypatch.delitem(streams.KINDS["check"]["fields"], "log_tail")
    assert "log_tail: undeclared field" in streams.validate(
        "check", check_row(log_tail="t" * 4000)
    )


def test_check_first_failure_is_capped_text_or_absent():
    # ER7: the derivation name the nightly's FAIL row carries, 200 chars or
    # absent. mutants: widen the cap -> a 201-char name validates; drop the
    # null arm -> an explicit None is refused as `not a string`.
    assert streams.validate("check", check_row(first_failure="publish-gate")) == []
    assert streams.validate("check", check_row(first_failure=None)) == []
    assert streams.validate("check", check_row(first_failure="x" * 201)) == [
        "first_failure: over cap 200"
    ]
    assert streams.validate("check", check_row(first_failure=7)) == [
        "first_failure: not a string"
    ]


def _dumps(row):
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def test_row_cap_exact_16384(t_kind):
    overhead = len(_dumps({"kind": "t", "i": 1, "j": 1, "pad": ""}))
    pad = 16384 - overhead
    assert len(_dumps({"kind": "t", "i": 1, "j": 1, "pad": "x" * pad})) == 16384
    assert streams.validate("t", {"kind": "t", "i": 1, "j": 1, "pad": "x" * pad}) == []
    assert streams.validate(
        "t", {"kind": "t", "i": 1, "j": 1, "pad": "x" * (pad + 1)}
    ) == ["row over 16384 bytes (16385)"]


def _nested(n):
    d = {}
    cur = d
    for _ in range(n):
        cur["a"] = {}
        cur = cur["a"]
    return d


def test_depth_cap_and_undeclared_short_circuit(t_kind, monkeypatch):
    # a 1,000-deep payload under an UNdeclared key -> exactly one `undeclared field`
    assert streams.validate(
        "t", {"kind": "t", "i": 1, "j": 1, "unknown": _nested(1000)}
    ) == ["unknown: undeclared field"]
    # a 1,000-deep payload under a DECLARED (recursive) obj -> `depth over 8`
    rec = ("obj", {})
    rec[1]["a"] = rec
    monkeypatch.setitem(streams.KINDS["t"]["fields"], "deep", rec)
    errs = streams.validate("t", {"kind": "t", "i": 1, "j": 1, "deep": _nested(1000)})
    assert any(e.startswith("depth over 8 at deep.") for e in errs)


def _enum_arms(cls):
    if isinstance(cls, tuple) and cls[0] == "null":
        cls = cls[1]
    assert isinstance(cls, tuple) and cls[0] == "enum", cls
    return cls[1]


def test_enum_arms_literal_matches_declared():
    # mutant: delete an arm, add one, or re-add it under another spelling in
    # streams.py -> the equality fails here.
    for (kind, field), arms in ENUM_ARMS.items():
        assert _enum_arms(streams.KINDS[kind]["fields"][field]) == arms


def test_derived_field_is_a_capped_list_of_two_enum_words():
    # `derived` labels which result lines the driver derived for a completed
    # unreported block: a nullable list of at most two of (checks|commits).
    # mutant: declare derived as `id` (or a plain enum) -> the list is refused
    # as `not a id` instead of validating.
    assert (
        streams.validate(
            "task-result", {**TASK_RESULT, "derived": ["checks", "commits"]}
        )
        == []
    )
    assert streams.validate("task-result", {**TASK_RESULT, "derived": None}) == []
    assert streams.validate("task-result", {**TASK_RESULT, "derived": ["bogus"]}) == [
        "derived[0]: not in enum (checks|commits)"
    ]
    assert streams.validate(
        "task-result", {**TASK_RESULT, "derived": ["checks", "commits", "checks"]}
    ) == ["derived: over cap 2"]
    assert streams.validate("task-result", {**TASK_RESULT, "derived": "checks"}) == [
        "derived: not a list"
    ]


# --- OC1: the operator-ask kind, attribution, rung, area, the widened fence ---


def test_operator_ask_valid_row_and_key():
    # mutant: drop `surface` from the entry -> `surface: undeclared field`;
    # key without `phase` -> the ask and answer rows share one key.
    assert streams.validate("operator-ask", OPERATOR_ASK) == []
    assert streams.stream_of("operator-ask", OPERATOR_ASK) == "ledger/operator"
    assert streams.key_of("operator-ask", OPERATOR_ASK) == (
        "0123456789abcdef",
        "fedcba9876543210",
        "answer",
    )
    ask = {**OPERATOR_ASK, "phase": "ask", "chosen_index": None}
    ask.update(took_recommended=None, latency_s=None, key=None)
    assert streams.validate("operator-ask", ask) == []


def test_operator_ask_refuses_question_text_as_forbidden_and_undeclared():
    # mutant: remove `question` from FORBIDDEN -> only the undeclared line.
    errs = streams.validate("operator-ask", {**OPERATOR_ASK, "question": "x"})
    assert "question: forbidden name" in errs
    assert "question: undeclared field" in errs


def test_operator_ask_header_cap_is_twelve():
    # mutant: ("text", 13) -> the 13-character chip passes.
    assert streams.validate("operator-ask", {**OPERATOR_ASK, "header": "A" * 12}) == []
    assert streams.validate("operator-ask", {**OPERATOR_ASK, "header": "A" * 13}) == [
        "header: over cap 12"
    ]


def test_operator_ask_ids_are_sixteen_hex():
    # mutant: {16} -> {15,16}: the 15-hex session passes.
    for bad in ("0123456789abcde", "0123456789ABCDEF", "sess-1"):
        assert streams.validate("operator-ask", {**OPERATOR_ASK, "session": bad}) == [
            "session: not a re"
        ]
    assert streams.validate("operator-ask", {**OPERATOR_ASK, "ask_id": "x" * 16}) == [
        "ask_id: not a re"
    ]


def test_operator_ask_enum_arms_and_bounds():
    # mutant: add "seat" to `src` -> the third assertion passes.
    assert streams.validate("operator-ask", {**OPERATOR_ASK, "phase": "asked"}) == [
        "phase: not in enum (ask|answer)"
    ]
    assert streams.validate("operator-ask", {**OPERATOR_ASK, "surface": "email"}) == [
        "surface: not in enum (chat|run-button|helm)"
    ]
    assert streams.validate("operator-ask", {**OPERATOR_ASK, "src": "seat"}) == [
        "src: not in enum (hook|orchestrator)"
    ]
    assert streams.validate("operator-ask", {**OPERATOR_ASK, "options": 65}) == [
        "options: not a int"
    ]
    assert streams.validate("operator-ask", {**OPERATOR_ASK, "latency_s": -1}) == [
        "latency_s: not a int"
    ]


def test_openrouter_usage_attribution_fields():
    # mutant: `run_id` declared "id" (not null) -> the null row is refused;
    # drop "window" from the enum -> the second assertion fails.
    nulls = {**OPENROUTER_USAGE, "run_id": None, "key": None, "attribution": "none"}
    assert streams.validate("openrouter-usage", nulls) == []
    joined = {
        **OPENROUTER_USAGE,
        "run_id": "ocw2",
        "key": "OC5",
        "attribution": "window",
    }
    assert streams.validate("openrouter-usage", joined) == []
    assert streams.validate(
        "openrouter-usage", {**OPENROUTER_USAGE, "attribution": "guess"}
    ) == ["attribution: not in enum (header|window|none)"]
    assert streams.validate("openrouter-usage", OPENROUTER_USAGE) == []


def test_gate_verdict_rung_and_reviewer_glm_kimi():
    # mutant: drop "glm" -> `reviewer: not in enum`; `rung` ("int", 1, 9) -> "int":
    # rung 0 passes.
    for reviewer in ("glm", "kimi", "unknown"):
        assert (
            streams.validate("gate-verdict", {**GATE_VERDICT, "reviewer": reviewer})
            == []
        )
    assert streams.validate("gate-verdict", {**GATE_VERDICT, "rung": 2}) == []
    assert streams.validate("gate-verdict", {**GATE_VERDICT, "rung": None}) == []
    assert streams.validate("gate-verdict", {**GATE_VERDICT, "rung": 0}) == [
        "rung: not a int"
    ]


def test_task_result_area_enum_equals_the_manifest_plus_unknown():
    # mutant: drop "program" from AREAS -> the tuple comparison fails; declare
    # `area` as "id" -> "media" passes.
    import tomllib

    manifest = next(
        p
        for p in (
            HERE.parents[2] / "docs" / "ledger" / "subsystems.toml",
            pathlib.Path("docs/ledger/subsystems.toml"),
        )
        if p.exists()
    )
    with open(manifest, "rb") as fh:
        rows = tomllib.load(fh)["subsystem"]
    assert streams.AREAS == tuple(r["area"] for r in rows)
    assert streams.validate("task-result", {**TASK_RESULT, "area": "evidence"}) == []
    assert streams.validate("task-result", {**TASK_RESULT, "area": "unknown"}) == []
    assert streams.validate("task-result", {**TASK_RESULT, "area": "media"}) == [
        "area: not in enum (" + "|".join(streams.AREAS + ("unknown",)) + ")"
    ]


def test_forbidden_answer_names():
    # mutant: remove any one of the four -> that name is not forbidden.
    for name in ("question", "questions", "answer", "answers"):
        assert streams._forbidden_name(name)
    assert not streams._forbidden_name("options")


def test_append_dispatch_without_module_exits_two(monkeypatch, capsys):
    # mutant: drop the try/except -> ImportError propagates instead of rc 2;
    # drop the target check -> `append bogus` reaches the import.
    monkeypatch.setitem(sys.modules, "operator_ask", None)
    assert evidence.main(["append", "operator", "--hook"]) == 2
    assert (
        "evidence: append operator: not available in this tree"
        in capsys.readouterr().err
    )
    assert evidence.main(["append", "bogus"]) == 2
    assert (
        "evidence: append: unknown target bogus (operator)" in capsys.readouterr().err
    )


def test_touches_extra_and_disclosed_are_nullable_ints():
    # `touches_extra`/`touches_disclosed` count files outside this task's
    # `touches` (and how many were disclosed in the commit body). Nullable int.
    # mutant: declare either as `id` (or a string class) -> the "1" row
    # validates instead of refusing `not a int`.
    assert streams.validate("task-result", {**TASK_RESULT, "touches_extra": 1}) == []
    assert streams.validate("task-result", {**TASK_RESULT, "touches_extra": None}) == []
    assert streams.validate("task-result", {**TASK_RESULT, "touches_extra": "1"}) == [
        "touches_extra: not a int"
    ]
    assert (
        streams.validate("task-result", {**TASK_RESULT, "touches_disclosed": 1}) == []
    )
    assert (
        streams.validate("task-result", {**TASK_RESULT, "touches_disclosed": None})
        == []
    )
    assert streams.validate(
        "task-result", {**TASK_RESULT, "touches_disclosed": "1"}
    ) == ["touches_disclosed: not a int"]


def test_checks_verified_map_and_scope_fields():
    # `checks_verified` is a nullable map name -> five-arm verdict, never the
    # seat's three-arm enum; `checks_scope` is clean|dirty. Mutant: copy the
    # seat's three-arm enum -> the bare `not-run` - value validates; the
    # forbidden key row and the cap row go red on a weaker map class.
    assert (
        streams.validate(
            "task-result",
            {**TASK_RESULT, "checks_verified": {"unit": "not-run:cache-miss"}},
        )
        == []
    )
    errs = streams.validate(
        "task-result", {**TASK_RESULT, "checks_verified": {"unit": "not-run"}}
    )
    assert "checks_verified.unit: not in enum" in errs[0]
    over = {f"c{i}": "pass" for i in range(65)}
    assert "checks_verified: over cap 64" in streams.validate(
        "task-result", {**TASK_RESULT, "checks_verified": over}
    )
    errs = streams.validate(
        "task-result", {**TASK_RESULT, "checks_verified": {"log": "pass"}}
    )
    assert "checks_verified.log: forbidden name" in errs
    assert (
        streams.validate("task-result", {**TASK_RESULT, "checks_scope": "dirty"}) == []
    )
    assert streams.validate("task-result", {**TASK_RESULT, "checks_scope": None}) == []
    errs = streams.validate("task-result", {**TASK_RESULT, "checks_scope": "partial"})
    assert "checks_scope: not in enum (clean|dirty)" in errs
    assert (
        streams.validate("task-result", {**TASK_RESULT, "checks_scope_files": 2}) == []
    )
    assert streams.validate("task-result", {**TASK_RESULT, "verify_s": 41}) == []
    assert streams.validate(
        "task-result", {**TASK_RESULT, "checks_scope_files": "two"}
    ) == ["checks_scope_files: not a int"]
    assert (
        streams.validate("task-result", {**TASK_RESULT, "checks_scope_files": None})
        == []
    )
    assert streams.validate("task-result", {**TASK_RESULT, "verify_s": None}) == []


def test_probes_verified_map_and_cap():
    # `probes_verified` is a nullable map probe-name -> five-arm verdict (the
    # driver's outcomes, distinct from the seat's three-arm checks enum), capped
    # at 32. Mutant: reuse the 64-cap checks map -> the 33-key row passes.
    assert (
        streams.validate(
            "task-result", {**TASK_RESULT, "probes_verified": {"readme-bytes": "drift"}}
        )
        == []
    )
    assert (
        streams.validate("task-result", {**TASK_RESULT, "probes_verified": None}) == []
    )
    errs = streams.validate(
        "task-result", {**TASK_RESULT, "probes_verified": {"readme-bytes": "pass!"}}
    )
    assert "probes_verified.readme-bytes: not in enum" in errs[0]
    over = {f"p{i}": "pass" for i in range(33)}
    assert "probes_verified: over cap 32" in streams.validate(
        "task-result", {**TASK_RESULT, "probes_verified": over}
    )
    errs = streams.validate(
        "task-result", {**TASK_RESULT, "probes_verified": {"cmd": "pass"}}
    )
    assert "probes_verified.cmd: forbidden name" in errs


def test_task_result_accepts_probe_env_and_retry_fields():
    # ER4: the probe outcome `env`, the error class `probe-env`, and the two
    # nullable retry counters ER3/ER14 write into `.result`. Mutants: drop
    # "probe-env" from ERROR_CLASSES -> `error_class: not in enum`; drop
    # "env" from the map's arms -> `probes_verified.x: not in enum`; declare
    # either counter as non-null "int" -> the None row is refused
    # (`null not allowed`).
    row = {
        **TASK_RESULT,
        "error_class": "probe-env",
        "probes_verified": {"x": "env"},
        "retries": 1,
        "provider_errors": 2,
    }
    assert streams.validate("task-result", row) == []
    assert streams.validate("task-result", {**row, "retries": None}) == []
    assert streams.validate("task-result", {**row, "provider_errors": None}) == []
    assert streams.validate("task-result", {**row, "retries": "1"}) == [
        "retries: not a int"
    ]
    assert streams.validate("task-result", {**row, "provider_errors": "2"}) == [
        "provider_errors: not a int"
    ]
    errs = streams.validate("task-result", {**row, "probes_verified": {"x": "envy"}})
    assert "probes_verified.x: not in enum" in errs[0]


_ENUM_CASES = [
    (kind, TASK_RESULT if kind == "task-result" else GATE_VERDICT, field, arm)
    for (kind, field), arms in ENUM_ARMS.items()
    for arm in arms
]


@pytest.mark.parametrize("kind,row,field,arm", _ENUM_CASES)
def test_every_enum_arm_accepted(kind, row, field, arm):
    assert streams.validate(kind, {**row, field: arm}) == []


@pytest.mark.parametrize("kind,row,field,arm", _ENUM_CASES)
def test_enum_arm_misspelling_refused(kind, row, field, arm):
    bad = arm[:-1] + ("z" if arm[-1] != "z" else "a")
    joined = "|".join(ENUM_ARMS[(kind, field)])
    assert streams.validate(kind, {**row, field: bad}) == [
        f"{field}: not in enum ({joined})"
    ]


def test_map_cap_key_pattern_and_value_enum(t_kind):
    checks = {f"c{i}": "pass" for i in range(64)}
    assert streams.validate("task-result", {**TASK_RESULT, "checks": checks}) == []
    checks["c64"] = "pass"
    assert "checks: over cap 64" in streams.validate(
        "task-result", {**TASK_RESULT, "checks": checks}
    )
    errs = streams.validate("task-result", {**TASK_RESULT, "checks": {"Unit": "pass"}})
    assert "checks.Unit: not a re" in errs
    errs = streams.validate("task-result", {**TASK_RESULT, "checks": {"unit": "ok"}})
    assert "checks.unit: not in enum (pass|fail|not-run)" in errs


def test_path_class_rules(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    home = str(tmp_path)
    base = {k: v for k, v in TASK_RESULT.items() if k != "result_path"}
    assert (
        streams.validate("task-result", {**base, "plan": "docs/superpowers/plans/x.md"})
        == []
    )
    assert streams.validate(
        "task-result", {**base, "plan": "docs/superpowers/plans/../x.md"}
    ) == ["plan: '..' segment"]
    assert streams.validate("task-result", {**base, "plan": "/etc/passwd"}) == [
        "plan: outside root docs/superpowers/plans/"
    ]
    good = os.path.join(home, "factory", "runs", "r", "K.result")
    assert streams.validate("task-result", {**base, "result_path": good}) == []
    assert streams.validate("task-result", {**base, "result_path": "/tmp/x"}) == [
        "result_path: outside root ~/factory/runs/"
    ]
    assert streams.validate(
        "task-result", {**base, "plan": "docs/superpowers/plans/x\n.md"}
    ) == ["plan: newline"]
    long_val = os.path.join(home, "factory", "runs") + "/" + "x" * 200
    assert streams.validate("task-result", {**base, "result_path": long_val}) == [
        "result_path: over cap 200"
    ]


def test_null_class_allows_none_and_refuses_non_null():
    assert streams.validate("task-result", {**TASK_RESULT, "exit_code": None}) == []
    errs = streams.validate("task-result", {**TASK_RESULT, "model": None})
    assert "model: null not allowed" in errs


def test_append_refuses_before_writing(tmp_path, t_kind):
    with pytest.raises(streams.StreamRefused) as exc:
        evidence.append(
            tmp_path, "checks", {"kind": "check", "name": "lint", "prompt": "x"}
        )
    assert "prompt: forbidden name" in exc.value.errors
    assert not (tmp_path / "checks.jsonl").exists()
    with pytest.raises(streams.StreamRefused) as exc:
        evidence.append(tmp_path, "runs", {"kind": "check", "name": "lint"})
    assert exc.value.errors == ["kind check does not write stream runs"]


def test_append_still_writes_envelope(tmp_path):
    row = evidence.append(
        str(tmp_path),
        "checks",
        {"kind": "check", "v": 99, "ts": "1970-01-01T00:00:00Z"},
        ts="2026-09-05T12:00:00Z",
    )
    assert row["v"] == 1
    assert row["ts"] == "2026-09-05T12:00:00Z"


def test_stream_re_allows_subdirectories(tmp_path):
    assert str(evidence.stream_path(tmp_path, "derived/tasks")).endswith(
        "derived/tasks.jsonl"
    )
    assert str(evidence.stream_path(tmp_path, "ledger/factory-runs")).endswith(
        "ledger/factory-runs.jsonl"
    )
    for bad in ("other/tasks", "derived/../x", "derived/Tasks"):
        with pytest.raises(ValueError):
            evidence.stream_path(tmp_path, bad)


def test_replace_stream_replaces_by_key_preserving_ts(tmp_path, t_kind, monkeypatch):
    monkeypatch.setattr(evidence, "now_iso", lambda: "2026-09-05T12:00:00Z")
    evidence.append(str(tmp_path), "runs", {"kind": "t", "i": 1, "j": 1, "pad": "a"})
    evidence.append(str(tmp_path), "runs", {"kind": "t", "i": 1, "j": 2, "pad": "b"})
    monkeypatch.setattr(evidence, "now_iso", lambda: "2026-09-06T00:00:00Z")
    n = evidence.replace_stream(
        str(tmp_path),
        "runs",
        [
            {"kind": "t", "i": 1, "j": 1, "pad": "a"},
            {"kind": "t", "i": 1, "j": 2, "pad": "B"},
            {"kind": "t", "i": 2, "j": 1, "pad": "c"},
        ],
    )
    assert n == 3
    rows = evidence.read(str(tmp_path), "runs")
    assert [(r["i"], r["j"], r["pad"]) for r in rows] == [
        (1, 1, "a"),
        (1, 2, "B"),
        (2, 1, "c"),
    ]
    # the carried-over equal row keeps its old ts byte-for-byte; the changed
    # and new rows carry the replacement's now.
    assert [r["ts"] for r in rows] == [
        "2026-09-05T12:00:00Z",
        "2026-09-06T00:00:00Z",
        "2026-09-06T00:00:00Z",
    ]


def test_replace_stream_idempotent(tmp_path, t_kind, monkeypatch):
    monkeypatch.setattr(evidence, "now_iso", lambda: "2026-09-05T12:00:00Z")
    evidence.replace_stream(
        str(tmp_path),
        "runs",
        [
            {"kind": "t", "i": 1, "j": 1, "pad": "a"},
            {"kind": "t", "i": 2, "j": 1, "pad": "b"},
        ],
    )
    first = (tmp_path / "runs.jsonl").read_bytes()
    monkeypatch.setattr(evidence, "now_iso", lambda: "2026-09-06T00:00:00Z")
    evidence.replace_stream(
        str(tmp_path),
        "runs",
        [
            {"kind": "t", "i": 1, "j": 1, "pad": "a"},
            {"kind": "t", "i": 2, "j": 1, "pad": "b"},
        ],
    )
    assert (tmp_path / "runs.jsonl").read_bytes() == first


def test_replace_stream_all_or_nothing(tmp_path, t_kind):
    evidence.append(str(tmp_path), "runs", {"kind": "t", "i": 1, "j": 1, "pad": "a"})
    before = (tmp_path / "runs.jsonl").read_bytes()
    with pytest.raises(streams.StreamRefused) as exc:
        evidence.replace_stream(
            str(tmp_path),
            "runs",
            [
                {"kind": "t", "i": 2, "j": 1, "pad": "b"},
                {"kind": "t", "i": 1, "j": 1, "prompt": "x"},
            ],
        )
    assert str(exc.value).startswith("row 1: prompt: forbidden name")
    assert (tmp_path / "runs.jsonl").read_bytes() == before


def test_replace_stream_atomic(tmp_path, t_kind, monkeypatch):
    evidence.append(str(tmp_path), "runs", {"kind": "t", "i": 1, "j": 1, "pad": "a"})
    before = (tmp_path / "runs.jsonl").read_bytes()

    def boom(*a, **k):
        raise OSError("no replace")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        evidence.replace_stream(
            str(tmp_path), "runs", [{"kind": "t", "i": 2, "j": 1, "pad": "b"}]
        )
    assert (tmp_path / "runs.jsonl").read_bytes() == before
    assert [r["i"] for r in evidence.read(str(tmp_path), "runs")] == [1]


def test_replace_stream_drops_torn_line_and_creates_derived(tmp_path, t_kind):
    import stat as stat_mod

    store = tmp_path / "store"
    evidence.append(str(store), "runs", {"kind": "t", "i": 1, "j": 1, "pad": "a"})
    with open(store / "runs.jsonl", "a") as fh:
        fh.write('{"v":1,"ts":"x","kind":"t","i":')
    evidence.replace_stream(
        str(store), "runs", [{"kind": "t", "i": 2, "j": 1, "pad": "b"}]
    )
    rows = evidence.read(str(store), "runs")
    assert len(rows) == 2
    evidence.replace_stream(
        str(store),
        "derived/tasks",
        [{"kind": "task-result", "run_id": "r1", "key": "T1"}],
    )
    assert stat_mod.S_IMODE((store / "derived").stat().st_mode) == 0o750


def test_replace_stream_no_key_kind_refused(tmp_path):
    with pytest.raises(streams.StreamRefused) as exc:
        evidence.replace_stream(str(tmp_path), "checks", [check_row()])
    assert exc.value.errors == ["kind check: no key; use append"]


def test_cli_record_refuses_and_exits_2(tmp_path):
    env = dict(os.environ, EVIDENCE_STORE=str(tmp_path))
    r = subprocess.run(
        [
            sys.executable,
            str(evidence.__file__),
            "record",
            "checks",
            "--json",
            '{"kind":"check","name":"lint","prompt":"x"}',
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert r.returncode == 2
    assert "evidence: refused: prompt: forbidden name" in r.stderr
    assert not (tmp_path / "checks.jsonl").exists()
    r = subprocess.run(
        [
            sys.executable,
            str(evidence.__file__),
            "record",
            "runs",
            "--json",
            '{"kind":"factory-run","prefix":"p"}',
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert r.returncode == 0
    assert json.loads(r.stdout)["prefix"] == "p"


def test_cli_record_check_refused_on_secret(tmp_path):
    env = dict(os.environ, EVIDENCE_STORE=str(tmp_path))
    r = subprocess.run(
        [
            sys.executable,
            str(evidence.__file__),
            "record-check",
            "--name",
            "lint",
            "--rev",
            REV_A,
            "--ok",
            "--class",
            "unit",
            "--src",
            "sk-or-v1-abc",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert r.returncode == 2
    assert "secret shape" in r.stderr
    assert not (tmp_path / "checks.jsonl").exists()


def test_ingest_table(tmp_path, monkeypatch, capsys):
    store = tmp_path / "store"
    r = subprocess.run(
        [
            sys.executable,
            str(evidence.__file__),
            "--store",
            str(store),
            "ingest",
            "bogus",
            "x",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 2
    assert (
        f"evidence: ingest: unknown target bogus ({'|'.join(evidence.INGEST_MODULES)})"
        in r.stderr
    )

    monkeypatch.setitem(evidence.INGEST_MODULES, "zz", "ingest_zz")
    assert evidence.main(["--store", str(store), "ingest", "zz"]) == 2
    assert "evidence: ingest zz: not available in this tree" in capsys.readouterr().err

    repo = tmp_path / "repo"
    repo.mkdir()
    r = subprocess.run(
        [
            sys.executable,
            str(evidence.__file__),
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
    assert r.returncode == 0, r.stderr
    assert f"no judgements under {repo}" in r.stdout


GOOD = {
    "plan": "docs/superpowers/plans/x.md",
    "spec": "docs/superpowers/specs/y.md",
    "author": "fable",
    "effort": "max",
    "words": "6140",
    "tasks": "9",
    "judges": "[sonnet, sonnet, opus]",
    "judges_dropped": "[]",
    "scores": "[3,2,3,3,2,3,3,3,3,3,2,2,3,3]",
    "total": "38",
    "self_score": "40",
    "threshold": "34",
    "decision": "dispatch",
    "revision": "0",
}


def test_judgements_delegate(monkeypatch):
    assert judgements.FIELDS == streams.judgement_fields()
    src = pathlib.Path(judgements.__file__).read_text()
    assert '    "judges_dropped",' not in src

    monkeypatch.setattr(streams, "validate", lambda k, r: ["boom"])
    assert judgements.validate_judgement(GOOD) == ["boom"]
    assert judgements.validate_judgement({**GOOD, "decision": "maybe"}) == [
        "decision: invalid (dispatch|revise|revise-exhausted|panel-short)"
    ]


def test_shape_a_literal_and_shape_b_refusal():
    assert streams.validate("factory-run", SHAPE_A) == []
    errs = streams.validate("factory-run", {**SHAPE_A, "driver": "seat"})
    assert "prefix: undeclared field" in errs


def test_collector_status_is_refused_by_name_and_shape():
    status = {
        "schema": 1,
        "generated_at": "2026-09-06T05:39:00Z",
        "hostname": "core",
        "tiles": [
            {
                "name": "broker",
                "status": "ok",
                "detail": {"stderr": "x"},
                "top_denied": ["h"],
            }
        ],
    }
    errs = streams.validate("helm-status", {"kind": "helm-status", **status})
    assert "hostname: forbidden name" in errs
    assert "tiles: not a map" in errs


def test_concurrent_appends_declare_kind(tmp_path, t_kind):
    pkg = str(pathlib.Path(streams.__file__).parent) + "/"
    prog = (
        "import sys;"
        "sys.path.insert(0, sys.argv[1]);"
        "import streams as s;"
        "s.KINDS['t']={'stream':'runs','v':1,'key':('i','j'),"
        "'fields':{'i':'int','j':'int','pad':('text',20000)}};"
        "import evidence as ev;"
        "i=int(sys.argv[3]);"
        "[ev.append(sys.argv[2], 'runs', {'kind':'t','i':i,'j':j,'pad':'x'*2000}) for j in range(50)]"
    )
    procs = [
        subprocess.Popen([sys.executable, "-c", prog, pkg, str(tmp_path), str(i)])
        for i in range(8)
    ]
    for p in procs:
        assert p.wait() == 0
    rows = evidence.read(str(tmp_path), "runs")
    assert len(rows) == 400
    assert {(r["i"], r["j"]) for r in rows} == {
        (i, j) for i in range(8) for j in range(50)
    }
