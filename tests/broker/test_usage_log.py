"""The usage log: one JSONL line beside the audit line for every OpenRouter
completion, carrying the parsed usage frame's cost, cache split, provider and
generation id -- never the response content.

Each test drives a flow the way mitmproxy does: requestheaders, request, a
response, responseheaders (which, for a completions SSE, replaces
`flow.response.stream` with the tee), the tee's per-chunk calls, then
response. `usage_lines` reads the usage log exactly like `audit_lines` reads
the audit log.
"""

import importlib.util
import json
import os
import pathlib
import re
import stat
import sys

import pytest
from mitmproxy import flow, http
from mitmproxy.test import tflow


def load_addon(tmp_path, monkeypatch, policy):
    policy_file = tmp_path / "policy.json"
    policy.setdefault("audit_log", str(tmp_path / "audit.jsonl"))
    policy_file.write_text(json.dumps(policy))
    monkeypatch.setenv("BROKER_POLICY", str(policy_file))
    root = pathlib.Path(__file__).resolve().parents[2]
    candidates = [
        root / "pkgs" / "broker" / "policy.py",
        pathlib.Path("broker/policy.py"),
    ]
    src = next(p for p in candidates if p.exists())
    spec = importlib.util.spec_from_file_location("usage_policy", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["usage_policy"] = mod
    spec.loader.exec_module(mod)
    return mod.EgressPolicy(), policy["audit_log"]


def https_flow(host, path="/api/v1/chat/completions", sni=None):
    f = tflow.tflow()
    f.request.scheme = "https"
    f.request.host = host
    f.request.port = 443
    f.request.path = path
    f.client_conn.sni = sni if sni is not None else host
    return f


def usage_lines(usage_path):
    p = pathlib.Path(usage_path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines()]


def audit_lines(audit_path):
    p = pathlib.Path(audit_path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines()]


POLICY = {"instance": "openrouter", "allow": ["openrouter.test"]}

# Assumption 4's OpenRouter usage object, exactly the wire shape the broker
# sees: the top-level `id` is NULL and the usage block carries cost, the cache
# split and token counts under nested details objects.
OK_USAGE = {
    "id": None,
    "provider": "DeepInfra",
    "model": "deepseek/deepseek-v4-flash",
    "usage": {
        "prompt_tokens": 7,
        "completion_tokens": 2,
        "total_tokens": 9,
        "cost": 9.9e-07,
        "is_byok": False,
        "prompt_tokens_details": {
            "cached_tokens": 0,
            "cache_write_tokens": 0,
        },
        "cost_details": {
            "upstream_inference_cost": 9.9e-07,
        },
        "completion_tokens_details": {
            "reasoning_tokens": 0,
        },
    },
}


def drive_ok_usage_flow(addon):
    """Drive a buffered JSON completion carrying OK_USAGE and return the flow."""
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(
        200, json.dumps(OK_USAGE).encode(), {"content-type": "application/json"}
    )
    addon.responseheaders(f)
    addon.response(f)
    return f


def drive_streamed(addon, chunks):
    """Drive an SSE completion; returns (flow, tee_return_values)."""
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(200, b"", {"content-type": "text/event-stream"})
    addon.responseheaders(f)
    tee = f.response.stream
    returned = [tee(c) for c in chunks]
    returned.append(tee(b""))
    addon.response(f)
    return f, returned


def test_sse_completion_records_one_ok_line(tmp_path, monkeypatch):
    # mutant (A): the tee returns without buffering -> no tail -> `unparsed`;
    # mutant (B): the FIRST `data:` frame is parsed (the content frame, which
    # has no usage) -> `no-usage`; mutant (C): the tail keeps only the last
    # chunk -> the usage frame (split across two calls) is never whole ->
    # `unparsed`.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    content = 'data: {"id":"c1","choices":[]}\n\n'
    usage_frame = "data: " + json.dumps(OK_USAGE) + "\n\n"
    cut = len(usage_frame) // 2
    chunks = [
        b": OPENROUTER PROCESSING\n\n",
        content.encode(),
        usage_frame[:cut].encode(),
        usage_frame[cut:].encode(),
        b"data: [DONE]\n\n",
    ]
    drive_streamed(addon, chunks)
    (rec,) = usage_lines(addon.usage_log)
    assert rec["status"] == "ok"
    assert rec["streamed"] is True
    assert rec["http_status"] == 200
    assert rec["cost_usd"] == 9.9e-07
    assert rec["gen_id"] is None
    assert rec["provider"] == "DeepInfra"
    assert rec["model"] == "deepseek/deepseek-v4-flash"
    assert rec["prompt_tokens"] == 7
    assert rec["completion_tokens"] == 2
    assert rec["total_tokens"] == 9
    assert rec["cached_tokens"] == 0
    assert rec["cache_write_tokens"] == 0
    assert rec["reasoning_tokens"] == 0


def test_tee_forwards_bytes_unchanged_and_end_returns_empty(tmp_path, monkeypatch):
    # mutant: the tee returns b"" for a chunk -> the reassembled stream differs.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    chunks = [
        b": OPENROUTER PROCESSING\n\n",
        b'data: {"id":"c1","choices":[]}\n\n',
        b"data: [DONE]\n\n",
    ]
    _, returned = drive_streamed(addon, chunks)
    assert returned[:-1] == chunks
    assert returned[-1] == b""


def test_buffered_completion_ok_gen_id_from_top_level(tmp_path, monkeypatch):
    # mutant: gen_id read from usage.id -> "usage-id-ignored" not "gen-fixture-1".
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    body = {
        "id": "gen-fixture-1",
        "provider": "DeepInfra",
        "model": "deepseek/deepseek-v4-flash",
        "usage": {
            "id": "usage-id-ignored",
            "cost": 1.0,
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
            "prompt_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "completion_tokens_details": {"reasoning_tokens": 0},
        },
    }
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(
        200, json.dumps(body).encode(), {"content-type": "application/json"}
    )
    assert not callable(f.response.stream)
    addon.responseheaders(f)
    assert not callable(f.response.stream)
    addon.response(f)
    (rec,) = usage_lines(addon.usage_log)
    assert rec["status"] == "ok"
    assert rec["streamed"] is False
    assert rec["gen_id"] == "gen-fixture-1"


def test_completions_object_without_usage_is_no_usage(tmp_path, monkeypatch):
    # mutant: the branch reads `frame["usage"]` directly -> KeyError propagates.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(
        200,
        json.dumps({"id": "gen-2", "choices": []}).encode(),
        {"content-type": "application/json"},
    )
    addon.responseheaders(f)
    addon.response(f)
    (rec,) = usage_lines(addon.usage_log)
    assert rec["status"] == "no-usage"
    for field in (
        "cost_usd",
        "upstream_cost_usd",
        "is_byok",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "cached_tokens",
        "cache_write_tokens",
        "reasoning_tokens",
    ):
        assert rec[field] is None


def test_unparseable_bodies_and_frameless_sse_are_unparsed(tmp_path, monkeypatch):
    # mutant: a parse exception propagates -> the flow raises instead of
    # writing a `unparsed` line.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f1 = https_flow("openrouter.test")
    addon.requestheaders(f1)
    addon.request(f1)
    f1.response = http.Response.make(200, b"<html>", {"content-type": "text/html"})
    addon.responseheaders(f1)
    addon.response(f1)

    f2 = https_flow("openrouter.test")
    addon.requestheaders(f2)
    addon.request(f2)
    f2.response = http.Response.make(200, b"", {"content-type": "text/event-stream"})
    addon.responseheaders(f2)
    tee = f2.response.stream
    tee(b": only a comment, no data frame\n\n")
    tee(b"")
    addon.response(f2)

    lines = usage_lines(addon.usage_log)
    assert [r["status"] for r in lines] == ["unparsed", "unparsed"]


def test_non_completions_path_writes_no_usage_line(tmp_path, monkeypatch):
    # mutant (D): the path rule removed -> /api/v1/models writes a line; the
    # `True` arm dropped -> the SSE variant's stream is the tee, not True.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f = https_flow("openrouter.test", "/api/v1/models")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(
        200,
        json.dumps({"data": [], "usage": {"cost": 1}}).encode(),
        {"content-type": "application/json"},
    )
    addon.responseheaders(f)
    addon.response(f)
    assert usage_lines(addon.usage_log) == []

    f2 = https_flow("openrouter.test", "/api/v1/models")
    f2.response = http.Response.make(200, b"", {"content-type": "text/event-stream"})
    addon.responseheaders(f2)
    assert f2.response.stream is True


def test_completions_sse_path_makes_stream_callable(tmp_path, monkeypatch):
    # mutant: `stream = True` for every SSE -> a completions SSE's stream is the
    # bool True, not a callable.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f = https_flow("openrouter.test")
    f.response = http.Response.make(200, b"", {"content-type": "text/event-stream"})
    addon.responseheaders(f)
    assert callable(f.response.stream)


def test_audit_and_usage_share_request_id_across_flows(tmp_path, monkeypatch):
    # mutant: _request_id mints per call -> audit and usage ids differ; the
    # field dropped from _audit -> the audit line has no request_id.
    addon, audit = load_addon(tmp_path, monkeypatch, dict(POLICY))
    for _ in range(2):
        drive_ok_usage_flow(addon)
    aud = audit_lines(audit)
    usages = usage_lines(addon.usage_log)
    assert len(aud) == 2
    assert len(usages) == 2
    assert [a["request_id"] for a in aud] == [u["request_id"] for u in usages]
    assert aud[0]["request_id"] != aud[1]["request_id"]
    for rid in [a["request_id"] for a in aud]:
        assert re.fullmatch(r"[0-9a-f]{32}", rid)


def test_usage_log_defaults_beside_audit_and_honours_key(tmp_path, monkeypatch):
    # mutant: policy["usage_log"] (no default) -> KeyError when the key is absent.
    addon, audit = load_addon(tmp_path, monkeypatch, dict(POLICY))
    assert addon.usage_log == str(pathlib.Path(audit).parent / "usage.jsonl")
    explicit = str(tmp_path / "custom-usage.jsonl")
    addon2, _ = load_addon(tmp_path, monkeypatch, {**POLICY, "usage_log": explicit})
    assert addon2.usage_log == explicit


def test_usage_file_mode_follows_umask(tmp_path, monkeypatch):
    # mutant: an os.chmod(path, 0o600) after the write -> mode 0o600, not 0o644.
    old = os.umask(0o022)
    try:
        addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
        drive_ok_usage_flow(addon)
    finally:
        os.umask(old)
    assert stat.S_IMODE(pathlib.Path(addon.usage_log).stat().st_mode) == 0o644


def test_error_flow_writes_no_usage_line(tmp_path, monkeypatch):
    # mutant: error calls _record_usage -> a usage line appears.
    addon, audit = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.error = flow.Error("upstream error")
    addon.error(f)
    assert usage_lines(addon.usage_log) == []
    assert len(audit_lines(audit)) == 1


def test_nested_token_fields_come_from_nested_objects(tmp_path, monkeypatch):
    # mutant: cached_tokens read from usage.cached_tokens (absent) -> None.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    body = json.loads(json.dumps(OK_USAGE))
    body["usage"]["prompt_tokens_details"]["cached_tokens"] = 5
    body["usage"]["completion_tokens_details"]["reasoning_tokens"] = 7
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(
        200, json.dumps(body).encode(), {"content-type": "application/json"}
    )
    addon.responseheaders(f)
    addon.response(f)
    (rec,) = usage_lines(addon.usage_log)
    assert rec["cached_tokens"] == 5
    assert rec["reasoning_tokens"] == 7


def test_response_preserves_headers_and_raw_content(tmp_path, monkeypatch):
    # mutant: response assigns flow.response.content -> raw_content changes.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    raw = json.dumps(OK_USAGE).encode()
    headers = {"content-type": "application/json", "x-extra": "keep"}
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(200, raw, headers)
    before_headers = dict(f.response.headers)
    addon.responseheaders(f)
    addon.response(f)
    assert f.response.raw_content == raw
    assert dict(f.response.headers) == before_headers


def test_unwritable_usage_dir_does_not_break_flow(tmp_path, monkeypatch, capsys):
    # mutant (I): the exception propagates out of response -> no audit line and
    # the flow raises.
    usage_dir = tmp_path / "sub"
    usage_dir.mkdir()
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {**POLICY, "usage_log": str(usage_dir / "usage.jsonl")},
    )
    usage_dir.chmod(0o000)
    try:
        f = https_flow("openrouter.test")
        addon.requestheaders(f)
        addon.request(f)
        f.response = http.Response.make(
            200, json.dumps(OK_USAGE).encode(), {"content-type": "application/json"}
        )
        addon.responseheaders(f)
        addon.response(f)
    finally:
        usage_dir.chmod(0o755)
    assert len(audit_lines(audit)) == 1
    assert "usage log write failed" in capsys.readouterr().err
    assert usage_lines(addon.usage_log) == []


def test_usage_tail_caps_at_last_64k(tmp_path, monkeypatch):
    # mutant (J): USAGE_TAIL_BYTES = 64 -> the real usage frame is dropped from
    # the tail -> `unparsed`; the trim keeps the FIRST 64 KiB -> the usage frame
    # (at the end) is dropped -> `unparsed`.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    big = b"data: " + (b"x" * 65536) + b"\n\n"
    usage_frame = ("data: " + json.dumps(OK_USAGE) + "\n\n").encode()
    drive_streamed(addon, [big, usage_frame])

    oversized = json.loads(json.dumps(OK_USAGE))
    oversized["usage"]["pad"] = "x" * 70000
    frame = ("data: " + json.dumps(oversized) + "\n\n").encode()
    assert len(frame) > 65536
    drive_streamed(addon, [frame])

    lines = usage_lines(addon.usage_log)
    assert [r["status"] for r in lines] == ["ok", "unparsed"]
    assert lines[0]["cost_usd"] == 9.9e-07


# --- SP1b fix round ----------------------------------------------------------
# A non-object usage detail (MAJOR-1) must degrade to null fields under the
# outer object's own status, never raise out of the response hook; a
# broker-minted deny (MINOR-1) writes no usage row; the cost source, instance
# and http_status are pinned (MINORs 2-4).

HOSTILE_DETAILS = [
    ("prompt_tokens_details", [1, 2], ("cached_tokens", "cache_write_tokens")),
    ("completion_tokens_details", 5, ("reasoning_tokens",)),
    ("cost_details", "x", ("upstream_cost_usd",)),
]


def _hostile_body(key, value):
    body = json.loads(json.dumps(OK_USAGE))
    body["usage"][key] = value
    return body


@pytest.mark.parametrize("key,value,nulled", HOSTILE_DETAILS)
def test_nested_detail_buffered_degrades_to_nulls(
    tmp_path, monkeypatch, key, value, nulled
):
    # mutant: drop the isinstance guard on this one detail -> AttributeError
    # out of response(), zero usage lines.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    body = _hostile_body(key, value)
    raw = json.dumps(body).encode()
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(200, raw, {"content-type": "application/json"})
    addon.responseheaders(f)
    addon.response(f)
    (rec,) = usage_lines(addon.usage_log)
    assert rec["status"] == "ok"
    assert rec["cost_usd"] == 9.9e-07
    assert rec["prompt_tokens"] == 7
    for field in nulled:
        assert rec[field] is None
    assert f.response.raw_content == raw


@pytest.mark.parametrize("key,value,nulled", HOSTILE_DETAILS)
def test_nested_detail_streamed_degrades_to_nulls(
    tmp_path, monkeypatch, key, value, nulled
):
    # mutant: drop the isinstance guard on this one detail -> AttributeError
    # out of response(), zero usage lines, on the SSE path too.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    body = _hostile_body(key, value)
    content = b'data: {"id":"c1","choices":[]}\n\n'
    usage_frame = ("data: " + json.dumps(body) + "\n\n").encode()
    chunks = [content, usage_frame, b"data: [DONE]\n\n"]
    _, returned = drive_streamed(addon, chunks)
    (rec,) = usage_lines(addon.usage_log)
    assert rec["status"] == "ok"
    assert rec["streamed"] is True
    for field in nulled:
        assert rec[field] is None
    assert returned[:-1] == chunks
    assert returned[-1] == b""


def test_broker_minted_deny_writes_no_usage_line(tmp_path, monkeypatch):
    # mutant: drop the egress_denied guard from _record_usage -> the broker's
    # own 403 still writes a `unparsed` usage row.
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "openrouter", "allow": ["openrouter.test"]}
    )
    f = https_flow("evil.test")
    addon.requestheaders(f)
    addon.response(f)
    assert usage_lines(addon.usage_log) == []
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"


def test_upstream_cost_usd_reads_nested_upstream_inference_cost(tmp_path, monkeypatch):
    # mutant: read `usage.get("upstream_inference_cost")` flat -> the field
    # goes null instead of the deliberately differing 0.5.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    body = json.loads(json.dumps(OK_USAGE))
    body["usage"]["cost"] = 1.0
    body["usage"]["cost_details"]["upstream_inference_cost"] = 0.5
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(
        200, json.dumps(body).encode(), {"content-type": "application/json"}
    )
    addon.responseheaders(f)
    addon.response(f)
    (rec,) = usage_lines(addon.usage_log)
    assert rec["cost_usd"] == 1.0
    assert rec["upstream_cost_usd"] == 0.5


def test_usage_record_pins_instance(tmp_path, monkeypatch):
    # mutant: drop "instance" from the returned dict -> KeyError on the read.
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {"instance": "openrouter-fixture", "allow": ["openrouter.test"]},
    )
    assert addon.instance == "openrouter-fixture"
    drive_ok_usage_flow(addon)
    (rec,) = usage_lines(addon.usage_log)
    assert rec["instance"] == "openrouter-fixture"


def test_http_status_pinned_for_429_no_usage(tmp_path, monkeypatch):
    # mutant: hardcode 200 -> the 429 fixture fails.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f = https_flow("openrouter.test")
    addon.requestheaders(f)
    addon.request(f)
    f.response = http.Response.make(
        429,
        b'{"error": {"message": "Rate limit exceeded", "code": 429}}',
        {"content-type": "application/json"},
    )
    addon.responseheaders(f)
    addon.response(f)
    (rec,) = usage_lines(addon.usage_log)
    assert rec["status"] == "no-usage"
    assert rec["http_status"] == 429


# --- OC5: the x-factory-task header (run/key address) -------------------------
# The seat will send `x-factory-task: <run>/<key>` with every completion
# (OC9). The broker records the pair in the usage row and removes the header
# before the request leaves the machine -- allowed or denied, well-formed or
# not. A malformed value is dropped like a well-formed one; the request
# always proceeds (D9).


def _flow_with_task(value):
    f = https_flow("openrouter.test")
    if value is not None:
        f.request.headers["x-factory-task"] = value
    return f


def _complete(addon, f):
    f.response = http.Response.make(
        200, json.dumps(OK_USAGE).encode(), {"content-type": "application/json"}
    )
    addon.responseheaders(f)
    addon.response(f)


def test_factory_task_header_is_recorded_and_dropped_at_requestheaders(
    tmp_path, monkeypatch
):
    # mutants: `headers.get` instead of `pop` -> the header survives; record
    # from the header at response time -> nothing (already popped) -> nulls.
    addon, audit = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f = _flow_with_task("ocw2/OC5")
    addon.requestheaders(f)
    assert "x-factory-task" not in f.request.headers
    addon.request(f)
    _complete(addon, f)
    (line,) = usage_lines(os.path.join(tmp_path, "usage.jsonl"))
    assert line["run_id"] == "ocw2" and line["key"] == "OC5"
    assert list(line)[list(line).index("status") + 1 :][:2] == ["run_id", "key"]
    assert all("run_id" not in a and "key" not in a for a in audit_lines(audit))


def test_factory_task_header_is_taken_on_the_request_hook_alone(tmp_path, monkeypatch):
    # mutant: take the header in requestheaders only -> nulls here.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f = _flow_with_task("ocw2/OC5")
    addon.request(f)
    assert "x-factory-task" not in f.request.headers
    _complete(addon, f)
    (line,) = usage_lines(os.path.join(tmp_path, "usage.jsonl"))
    assert (line["run_id"], line["key"]) == ("ocw2", "OC5")


@pytest.mark.parametrize(
    "value",
    [
        "ocw2",
        "ocw2/../OC5",
        "ocw2/OC5/x",
        "a" * 33 + "/OC5",
        "ocw2/",
        "/OC5",
        "ocw2/OC 5",
        "",
    ],
)
def test_hostile_task_values_are_dropped_and_recorded_as_nulls(
    tmp_path, monkeypatch, value
):
    # mutant: `split("/")` instead of the regex -> "ocw2/../OC5" records "..".
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f = _flow_with_task(value)
    addon.requestheaders(f)
    assert "x-factory-task" not in f.request.headers
    addon.request(f)
    _complete(addon, f)
    (line,) = usage_lines(os.path.join(tmp_path, "usage.jsonl"))
    assert line["run_id"] is None and line["key"] is None


def test_no_header_records_nulls_and_denied_flows_still_drop_it(tmp_path, monkeypatch):
    # mutant: pop only on the allowed path -> a denied flow keeps the header.
    addon, _ = load_addon(tmp_path, monkeypatch, dict(POLICY))
    f = _flow_with_task(None)
    addon.requestheaders(f)
    addon.request(f)
    _complete(addon, f)
    (line,) = usage_lines(os.path.join(tmp_path, "usage.jsonl"))
    assert line["run_id"] is None and line["key"] is None
    g = _flow_with_task("ocw2/OC5")
    g.request.host = "evil.test"
    g.client_conn.sni = "evil.test"
    addon.requestheaders(g)
    assert "x-factory-task" not in g.request.headers
    assert g.response is not None and g.response.status_code == 403
