import importlib.util
import json
import pathlib
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
    spec = importlib.util.spec_from_file_location("policy", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["policy"] = mod
    spec.loader.exec_module(mod)
    return mod.EgressPolicy(), policy["audit_log"]


def https_flow(host, path="/x", sni=None):
    f = tflow.tflow()
    f.request.scheme = "https"
    f.request.host = host
    f.request.port = 443
    f.request.path = path
    f.client_conn.sni = sni if sni is not None else host
    return f


def http_flow(routed_host, host_header, path="/x"):
    f = tflow.tflow()
    f.request.scheme = "http"
    f.request.host = routed_host
    f.request.port = 80
    f.request.path = path
    f.request.headers["Host"] = host_header
    f.client_conn.sni = None
    return f


def audit_lines(audit_path):
    p = pathlib.Path(audit_path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines()]


def test_denies_non_allowlisted_host(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    addon.request(f)
    assert f.response is not None
    assert f.response.status_code == 403
    recs = audit_lines(audit)
    assert len(recs) == 1
    assert recs[0]["verdict"] == "deny"
    assert recs[0]["host"] == "evil.test"
    assert recs[0]["instance"] == "t"


def test_allowlisted_host_passes_and_audits_on_response(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("allowed.test")
    addon.request(f)
    assert f.response is None
    f.response = http.Response.make(200, b"ok")
    addon.response(f)
    recs = audit_lines(audit)
    assert len(recs) == 1
    assert recs[0]["verdict"] == "allow"
    assert recs[0]["bytes_in"] == len(b"ok")


def test_no_double_audit_on_denied_flow(tmp_path, monkeypatch):
    addon, audit = load_addon(tmp_path, monkeypatch, {"instance": "t", "allow": []})
    f = https_flow("evil.test")
    addon.request(f)
    addon.response(f)
    assert len(audit_lines(audit)) == 1


def test_audit_record_has_exact_fields(tmp_path, monkeypatch):
    addon, audit = load_addon(tmp_path, monkeypatch, {"instance": "t", "allow": []})
    addon.request(https_flow("evil.test"))
    (rec,) = audit_lines(audit)
    assert sorted(rec) == sorted(
        [
            "ts",
            "instance",
            "request_id",
            "client",
            "method",
            "host",
            "host_header",
            "sni",
            "path",
            "bytes_out",
            "bytes_in",
            "verdict",
            "reason",
        ]
    )


def test_injects_credential_on_allowlisted_host(tmp_path, monkeypatch):
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value\n")
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "inject": {
                "api.test": {
                    "header": "Authorization",
                    "prefix": "Bearer ",
                    "value_file": str(secret),
                }
            },
        },
    )
    f = https_flow("api.test")
    f.request.headers["Authorization"] = "Bearer BASKET-SENTINEL"
    addon.request(f)
    assert f.response is None
    assert f.request.headers["Authorization"] == "Bearer s3cr3t-value"


def test_never_injects_on_non_inject_host(tmp_path, monkeypatch):
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value")
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["a.test", "b.test"],
            "inject": {"a.test": {"value_file": str(secret)}},
        },
    )
    f = https_flow("b.test")
    f.request.headers["Authorization"] = "Bearer BASKET-SENTINEL"
    addon.request(f)
    assert f.request.headers["Authorization"] == "Bearer BASKET-SENTINEL"


def test_domain_fronting_denied_and_flagged(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("denied.test", sni="allowed.test")
    addon.request(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert "mismatch" in rec["reason"]
    assert rec["sni"] == "allowed.test"
    assert rec["host"] == "denied.test"


def test_allowlisted_host_with_mismatched_sni_is_denied(tmp_path, monkeypatch):
    # A CONNECT to an *allowlisted* host followed by a forged TLS SNI must be
    # denied too: the allowlist alone is not enough when the TLS handshake
    # then heads for an attacker-chosen name. The old code consulted the SNI
    # only inside the not-allowlisted arm, so this branch is the only thing
    # standing between a CONNECT to allowed.test and a handshake to evil.test.
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("allowed.test", sni="evil.test")
    addon.request(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert rec["reason"] == "host/sni mismatch: sni=evil.test host=allowed.test"


def test_connect_denied_and_audited(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    addon.http_connect(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert rec["reason"] == "connect-not-allowlisted"


def test_connect_gate_keys_on_the_authority_not_the_host_header(tmp_path, monkeypatch):
    # The CONNECT gate must key on the routed destination (the authority
    # mitmproxy actually dials), never the client-supplied Host header: a
    # client sending 'CONNECT denied.test:443' with 'Host: allowed.test'
    # must still be refused, or the r2-1-1 blocker reopens on the HTTPS
    # path (the tunnel is allowed on the strength of a spoofed header).
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("denied.test")
    f.request.headers["Host"] = "allowed.test"
    addon.http_connect(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["reason"] == "connect-not-allowlisted"


def test_responseheaders_streams_event_stream_content_type(tmp_path, monkeypatch):
    addon, _ = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("allowed.test")
    f.response = http.Response.make(
        200, b"", {"content-type": "text/event-stream; charset=utf-8"}
    )
    assert f.response.stream is False
    addon.responseheaders(f)
    assert f.response.stream is True


def test_responseheaders_leaves_other_content_types_unstreamed(tmp_path, monkeypatch):
    addon, _ = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("allowed.test")
    f.response = http.Response.make(200, b"", {"content-type": "application/json"})
    addon.responseheaders(f)
    assert f.response.stream is False


def test_audit_bytes_in_falls_back_to_content_length_when_streamed(
    tmp_path, monkeypatch
):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("allowed.test")
    addon.request(f)
    f.response = http.Response.make(200, b"")
    f.response.headers["content-length"] = "3145728"
    f.response.raw_content = None
    addon.response(f)
    (rec,) = audit_lines(audit)
    assert rec["bytes_in"] == 3145728


def test_audit_bytes_in_zero_when_streamed_without_content_length(
    tmp_path, monkeypatch
):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("allowed.test")
    addon.request(f)
    f.response = http.Response.make(200, b"")
    del f.response.headers["content-length"]
    f.response.raw_content = None
    addon.response(f)
    (rec,) = audit_lines(audit)
    assert rec["bytes_in"] == 0


def test_requestheaders_denies_non_allowlisted_host_before_body_streams(
    tmp_path, monkeypatch
):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    addon.requestheaders(f)
    assert f.response is not None
    assert f.response.status_code == 403
    recs = audit_lines(audit)
    assert len(recs) == 1
    assert recs[0]["verdict"] == "deny"
    assert recs[0]["host"] == "evil.test"


def test_requestheaders_denies_domain_fronting(tmp_path, monkeypatch):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("denied.test", sni="allowed.test")
    addon.requestheaders(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert "mismatch" in rec["reason"]


def test_request_does_not_double_audit_after_requestheaders_denied(
    tmp_path, monkeypatch
):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    addon.requestheaders(f)
    denied_response = f.response
    addon.request(f)
    assert len(audit_lines(audit)) == 1
    assert f.response is denied_response
    assert f.response.status_code == 403


def test_requestheaders_allowlisted_host_passes(tmp_path, monkeypatch):
    addon, _ = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("allowed.test")
    addon.requestheaders(f)
    assert f.response is None


def test_secret_never_appears_in_audit(tmp_path, monkeypatch):
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value")
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "inject": {"api.test": {"value_file": str(secret)}},
        },
    )
    f = https_flow("api.test")
    addon.request(f)
    f.response = http.Response.make(200, b"ok")
    addon.response(f)
    assert "s3cr3t-value" not in pathlib.Path(audit).read_text()


def test_deny_kills_flow_when_request_stream_already_true(tmp_path, monkeypatch):
    # mitmproxy's check_body_size() runs before requestheaders and, with
    # stream_large_bodies set, flips flow.request.stream = True whenever the
    # request body exceeds the threshold -- regardless of whether we go on
    # to deny the request. Setting flow.response here (the naive fix) does
    # NOT avoid the crash: mitmproxy's state_consume_request_body re-checks
    # the buffered size on every chunk and can flip .stream back on once
    # enough has arrived, again raising NotImplementedError with a response
    # already set. flow.kill() sidesteps the whole body-consuming state
    # machine instead -- requestheaders() fires before any body byte is
    # read, and mitmproxy's check_killed() aborts to state_errored right
    # after the hook returns, before start_request_stream() or
    # state_consume_request_body ever run.
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    f.request.stream = True
    assert f.killable
    addon.requestheaders(f)
    assert f.response is None
    assert f.error is not None
    assert f.error.msg == flow.Error.KILLED_MESSAGE
    assert f.killable is False
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"


def test_deny_kills_flow_when_content_length_exceeds_threshold(tmp_path, monkeypatch):
    # Even when mitmproxy hasn't flipped .stream yet, a declared
    # Content-Length over the streaming threshold means it will, the first
    # time state_consume_request_body's per-chunk check_body_size() sees
    # that many bytes buffered -- so this must be killed too, not answered.
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    f.request.headers["content-length"] = str(1024 * 1024 + 1)
    # Not yet buffered -- requestheaders() fires before any body byte is
    # consumed, real or simulated.
    f.request.raw_content = None
    addon.requestheaders(f)
    assert f.response is None
    assert f.error is not None
    assert f.error.msg == flow.Error.KILLED_MESSAGE
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert rec["bytes_out"] == 1024 * 1024 + 1


def test_deny_kills_flow_when_content_length_unknown(tmp_path, monkeypatch):
    # Chunked transfer encoding declares no Content-Length -- the true body
    # size isn't known until it has already arrived, so it can't be ruled
    # out as safe and has to be treated the same as "over the threshold":
    # kill, not a 403.
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    del f.request.headers["content-length"]
    f.request.headers["transfer-encoding"] = "chunked"
    addon.requestheaders(f)
    assert f.response is None
    assert f.error is not None
    assert f.error.msg == flow.Error.KILLED_MESSAGE
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"


def test_deny_returns_403_for_bodiless_request(tmp_path, monkeypatch):
    # A request with no declared body at all -- no Content-Length, no
    # chunked Transfer-Encoding, e.g. a plain GET -- can never be streamed
    # by mitmproxy (expected_http_body_size() defines this as exactly
    # zero-length, RFC 7230 3.3 rule 6, same as check_body_size() itself
    # would see), so the ordinary 403 is always safe here and must not be
    # confused with the chunked/unknown-size case above just because both
    # lack a Content-Length header.
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("denied.test", sni="allowed.test")
    del f.request.headers["content-length"]
    addon.requestheaders(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert "mismatch" in rec["reason"]


def test_deny_returns_403_when_content_length_at_threshold(tmp_path, monkeypatch):
    # mitmproxy only streams when expected_size > stream_large_bodies (a
    # strict `>`), so a body exactly at the threshold never gets streamed
    # and the ordinary 403 response is safe.
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    f.request.headers["content-length"] = str(1024 * 1024)
    addon.requestheaders(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"


def test_request_does_not_recheck_after_requestheaders_kill(tmp_path, monkeypatch):
    # request() must treat a killed flow the same as an already-denied one:
    # re-running _check()/_deny_request() would call flow.kill() on a flow
    # that is no longer killable() and raise ControlException.
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("evil.test")
    f.request.headers["content-length"] = str(1024 * 1024 + 1)
    addon.requestheaders(f)
    addon.request(f)  # must not raise, must not double-audit
    assert len(audit_lines(audit)) == 1


def test_requestheaders_injects_credential_before_request_hook(tmp_path, monkeypatch):
    # With stream_large_bodies set, mitmproxy forwards the request headers
    # upstream immediately after requestheaders returns for a streamed body
    # -- request() only fires later, at end-of-body, too late to add a
    # header. Injection has to happen in requestheaders() to reach a
    # streamed request at all.
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value\n")
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "inject": {
                "api.test": {
                    "header": "Authorization",
                    "prefix": "Bearer ",
                    "value_file": str(secret),
                }
            },
        },
    )
    f = https_flow("api.test")
    f.request.headers["Authorization"] = "Bearer BASKET-SENTINEL"
    addon.requestheaders(f)
    assert f.response is None
    assert f.request.headers["Authorization"] == "Bearer s3cr3t-value"


def test_audit_bytes_out_falls_back_to_content_length_when_streamed(
    tmp_path, monkeypatch
):
    addon, audit = load_addon(
        tmp_path, monkeypatch, {"instance": "t", "allow": ["allowed.test"]}
    )
    f = https_flow("allowed.test")
    f.request.headers["content-length"] = "2097152"
    f.request.raw_content = None
    addon.request(f)
    f.response = http.Response.make(200, b"ok")
    addon.response(f)
    (rec,) = audit_lines(audit)
    assert rec["bytes_out"] == 2097152


def test_body_patch_merges_policy_into_json_request(tmp_path, monkeypatch):
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "body_patch": {
                "api.test": {
                    "path_prefixes": ["/api/v1/chat/completions"],
                    "merge": {"provider": {"zdr": True, "data_collection": "deny"}},
                }
            },
        },
    )
    f = https_flow("api.test", path="/api/v1/chat/completions")
    f.request.headers["content-type"] = "application/json"
    f.request.content = json.dumps(
        {"model": "m", "messages": [], "provider": {"order": ["x"], "zdr": False}}
    ).encode()
    addon.request(f)
    body = json.loads(f.request.content)
    assert body["provider"] == {"order": ["x"], "zdr": True, "data_collection": "deny"}
    assert body["model"] == "m"
    assert f.request.headers["content-length"] == str(len(f.request.content))


def test_body_patch_leaves_other_paths_hosts_and_non_json_alone(tmp_path, monkeypatch):
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test", "other.test"],
            "body_patch": {
                "api.test": {
                    "path_prefixes": ["/api/v1/chat"],
                    "merge": {"provider": {"zdr": True}},
                }
            },
        },
    )
    raw = json.dumps({"model": "m"}).encode()
    f1 = https_flow("api.test", path="/api/v1/models")
    f1.request.headers["content-type"] = "application/json"
    f1.request.content = raw
    addon.request(f1)
    assert f1.request.content == raw
    f2 = https_flow("other.test", path="/api/v1/chat/completions")
    f2.request.headers["content-type"] = "application/json"
    f2.request.content = raw
    addon.request(f2)
    assert f2.request.content == raw
    f3 = https_flow("api.test", path="/api/v1/chat/completions")
    f3.request.headers["content-type"] = "text/plain"
    f3.request.content = b"not json"
    addon.request(f3)
    assert f3.response is not None and f3.response.status_code == 403


def test_body_patch_applies_to_every_configured_prefix(tmp_path, monkeypatch):
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "body_patch": {
                "api.test": {
                    "path_prefixes": [
                        "/api/v1/chat/completions",
                        "/api/v1/messages",
                    ],
                    "merge": {"provider": {"zdr": True}},
                }
            },
        },
    )
    for path in ["/api/v1/chat/completions", "/api/v1/messages"]:
        f = https_flow("api.test", path=path)
        f.request.headers["content-type"] = "application/json"
        f.request.content = json.dumps({"model": "m"}).encode()
        addon.request(f)
        body = json.loads(f.request.content)
        assert body["provider"] == {"zdr": True}
        assert body["model"] == "m"
    # A path not in the list is untouched -- the list is an allowlist of
    # prefixes, not a fallback that patches every path on the host.
    f = https_flow("api.test", path="/api/v1/models")
    f.request.headers["content-type"] = "application/json"
    f.request.content = json.dumps({"model": "m"}).encode()
    addon.request(f)
    assert json.loads(f.request.content) == {"model": "m"}


def test_streamed_body_on_a_patched_path_is_killed_and_audited(tmp_path, monkeypatch):
    # A >1 MiB request body to a bodyPatch host/path is exactly what
    # _patch_body can no longer rewrite: mitmproxy's stream_large_bodies has
    # already marked the body for streaming before requestheaders fires (and
    # _patch_body runs only from request(), at end-of-body, by which point
    # every chunk is on the wire). raw_content stays None for a streamed
    # body, so even the audit record's body would be corrupt -- the flow has
    # to be killed before a single byte streams upstream, and audited.
    #
    # W2-N3: this is a POST against a host with BOTH an inject spec and a
    # body_patch spec. The kill runs before _inject (requestheaders kills
    # and returns, never reaching _inject), so the injected credential must
    # NOT be written onto a flow whose unpatched body can no longer carry
    # the ZDR patch -- the header would otherwise leak alongside a body that
    # escaped the data policy.
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value\n")
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "inject": {"api.test": {"value_file": str(secret)}},
            "body_patch": {
                "api.test": {
                    "path_prefixes": ["/api/v1/chat/completions"],
                    "merge": {"provider": {"zdr": True, "data_collection": "deny"}},
                }
            },
        },
    )
    f = https_flow("api.test", path="/api/v1/chat/completions")
    f.request.method = "POST"
    f.request.headers["content-type"] = "application/json"
    f.request.headers["content-length"] = str(1024 * 1024 + 1)
    f.request.raw_content = None
    addon.requestheaders(f)
    assert f.response is None
    assert f.error is not None
    assert f.error.msg == flow.Error.KILLED_MESSAGE
    assert f.killable is False
    assert "Authorization" not in f.request.headers
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert rec["reason"] == "zdr-unpatchable-streamed-body"


def test_inject_honours_its_own_path_allowlist(tmp_path, monkeypatch):
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value\n")

    def load(paths="__unset__"):
        spec = {
            "header": "Authorization",
            "prefix": "Bearer ",
            "value_file": str(secret),
        }
        if paths != "__unset__":
            spec["paths"] = paths
        return load_addon(
            tmp_path,
            monkeypatch,
            {
                "instance": "t",
                "allow": ["api.test"],
                "inject": {"api.test": spec},
            },
        )

    # paths set: the credential is injected on a matching path and withheld
    # on any other path of the same host.
    addon, _ = load(paths=["/api/v1/messages"])
    f = https_flow("api.test", path="/api/v1/messages")
    addon.request(f)
    assert f.request.headers["Authorization"] == "Bearer s3cr3t-value"

    f2 = https_flow("api.test", path="/api/v1/chat/completions")
    addon.request(f2)
    assert "Authorization" not in f2.request.headers

    # paths unset: back-compatible default of injecting on every path.
    addon, _ = load()
    f3 = https_flow("api.test", path="/api/v1/anything")
    addon.request(f3)
    assert f3.request.headers["Authorization"] == "Bearer s3cr3t-value"


def test_denies_configured_path_before_injection(tmp_path, monkeypatch):
    # A path listed under deny_paths for a host is denied with audit reason
    # path-not-permitted, and it is denied BEFORE credential injection:
    # the injected Authorization header must never be written onto a flow
    # the policy refuses to forward (fail closed, O3 -- nothing consumes
    # OpenRouter's Anthropic-style /api/v1/messages path).
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value\n")
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "inject": {"api.test": {"value_file": str(secret)}},
            "deny_paths": {"api.test": {"path_prefixes": ["/api/v1/messages"]}},
        },
    )
    f = https_flow("api.test", path="/api/v1/messages")
    f.request.method = "POST"
    f.request.headers["content-type"] = "application/json"
    f.request.content = b'{"model":"m"}'
    addon.request(f)
    assert f.response is not None
    assert f.response.status_code == 403
    assert "Authorization" not in f.request.headers
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert rec["reason"] == "path-not-permitted"
    assert rec["path"] == "/api/v1/messages"


def test_requestheaders_denies_configured_path(tmp_path, monkeypatch):
    # The deny also runs from requestheaders() -- the hook that fires before
    # any body streams upstream and where credential injection happens -- so
    # a denied path is stopped (and the credential withheld) even for a body
    # that would otherwise stream.
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "deny_paths": {"api.test": {"path_prefixes": ["/api/v1/messages"]}},
        },
    )
    f = https_flow("api.test", path="/api/v1/messages")
    addon.requestheaders(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["verdict"] == "deny"
    assert rec["reason"] == "path-not-permitted"


def test_deny_paths_leave_other_paths_alone(tmp_path, monkeypatch):
    # The deny list is a denylist, not a host-wide gate: a sibling path on
    # the same host is still forwarded and injected as before.
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value\n")
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "inject": {"api.test": {"value_file": str(secret)}},
            "deny_paths": {"api.test": {"path_prefixes": ["/api/v1/messages"]}},
        },
    )
    f = https_flow("api.test", path="/api/v1/chat/completions")
    f.request.method = "POST"
    f.request.headers["content-type"] = "application/json"
    f.request.content = b'{"model":"m"}'
    addon.request(f)
    assert f.response is None
    assert f.request.headers["Authorization"] == "Bearer s3cr3t-value"


def test_host_header_cannot_redirect_the_credential(tmp_path, monkeypatch):
    secret = tmp_path / "s"
    secret.write_text("vm-test-secret\n")
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["allowed.test"],
            "inject": {"allowed.test": {"value_file": str(secret)}},
        },
    )
    f = http_flow("attacker.test", "allowed.test")
    addon.requestheaders(f)
    addon.request(f)
    assert f.response is not None and f.response.status_code == 403
    assert "Authorization" not in f.request.headers
    rec = audit_lines(audit)[-1]
    assert rec["verdict"] == "deny" and rec["reason"].startswith("host-header-mismatch")
    assert rec["host"] == "attacker.test" and rec["host_header"] == "allowed.test"


@pytest.mark.parametrize(
    "host_header",
    [
        "allowed.test",
        "Allowed.Test",
        "allowed.test:80",
        "ALLOWED.TEST",
        "allowed.test.",
    ],
)
def test_matching_host_header_is_allowed_and_injected(
    tmp_path, monkeypatch, host_header
):
    secret = tmp_path / "s"
    secret.write_text("vm-test-secret\n")
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["allowed.test"],
            "inject": {"allowed.test": {"value_file": str(secret)}},
        },
    )
    f = http_flow("allowed.test", host_header)
    addon.request(f)
    assert (
        f.response is None
        and f.request.headers["Authorization"] == "Bearer vm-test-secret"
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/%6dessages",
        "//api/v1/messages",
        "/api/v1/./messages",
        "/api/v1/x/../messages",
        "/API/v1/messages",
        "/api/v1/messages?x=1",
        "/api/v1/%252dmessages",
    ],
)
def test_deny_paths_survive_path_equivalence_tricks(tmp_path, monkeypatch, path):
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["allowed.test"],
            "deny_paths": {"allowed.test": {"path_prefixes": ["/api/v1/messages"]}},
        },
    )
    f = https_flow("allowed.test", path)
    addon.request(f)
    assert f.response is not None and f.response.status_code == 403
    assert audit_lines(audit)[-1]["reason"] in (
        "path-not-permitted",
        "path-not-normalizable",
    )


def test_other_paths_still_pass_after_normalisation(tmp_path, monkeypatch):
    addon, _ = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["allowed.test"],
            "deny_paths": {"allowed.test": {"path_prefixes": ["/api/v1/messages"]}},
        },
    )
    f = https_flow("allowed.test", "/api/v1/chat/completions?stream=true")
    addon.request(f)
    assert f.response is None


@pytest.mark.parametrize(
    "ctype,body,patched",
    [
        ("APPLICATION/JSON", b'{"a":1}', True),
        ("application/json; charset=utf-8", b'{"a":1}', True),
        ("text/plain", b'{"a":1}', False),
        ("application/json", b"[1,2]", False),
        ("application/json", b"not json", False),
        ("application/json", b"", False),
    ],
)
def test_body_patch_fails_closed_when_it_cannot_patch(
    tmp_path, monkeypatch, ctype, body, patched
):
    secret = tmp_path / "token"
    secret.write_text("s3cr3t-value\n")
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["allowed.test"],
            "inject": {"allowed.test": {"value_file": str(secret)}},
            "body_patch": {
                "allowed.test": {
                    "path_prefixes": ["/api/v1/chat/completions"],
                    "merge": {"provider": {"zdr": True}},
                }
            },
        },
    )
    f = https_flow("allowed.test", "/api/v1/chat/completions")
    f.request.headers["content-type"] = ctype
    f.request.content = body
    addon.request(f)
    if patched:
        assert (
            f.response is None
            and json.loads(f.request.content)["provider"]["zdr"] is True
        )
    else:
        assert f.response is not None and f.response.status_code == 403
        assert audit_lines(audit)[-1]["reason"] == "zdr-unpatchable-body"
        assert "Authorization" not in f.request.headers


def test_body_patch_fails_closed_on_unnormalizable_path(tmp_path, monkeypatch):
    # A body_patch host whose request path still carries a % after one decode
    # (double encoding) cannot be matched, and must be denied with reason
    # path-not-normalizable -- mirroring _denied_path's fail-closed handling --
    # rather than treated as "no match", which would forward the body without
    # the ZDR merge (and, when an inject entry exists, without the credential).
    addon, audit = load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["allowed.test"],
            "body_patch": {
                "allowed.test": {
                    "path_prefixes": ["/api/v1/chat/completions"],
                    "merge": {"provider": {"zdr": True}},
                }
            },
        },
    )
    f = https_flow("allowed.test", "/api/v1/chat/completions%252f")
    f.request.headers["content-type"] = "application/json"
    f.request.content = b'{"a":1}'
    addon.request(f)
    assert f.response is not None
    assert f.response.status_code == 403
    (rec,) = audit_lines(audit)
    assert rec["reason"] == "path-not-normalizable"


def _except_policy(tmp_path, monkeypatch, except_models):
    """A body_patch host whose merge is the ZDR patch and whose except_models
    is the value under test (the seat's single id, an empty list, etc.)."""
    return load_addon(
        tmp_path,
        monkeypatch,
        {
            "instance": "t",
            "allow": ["api.test"],
            "body_patch": {
                "api.test": {
                    "path_prefixes": ["/api/v1/chat/completions"],
                    "except_models": except_models,
                    "merge": {"provider": {"zdr": True, "data_collection": "deny"}},
                }
            },
        },
    )


def _json_flow(model=None, raw=None):
    f = https_flow("api.test", path="/api/v1/chat/completions")
    f.request.headers["content-type"] = "application/json"
    if raw is not None:
        f.request.content = raw
    else:
        body = {"messages": [], "provider": {"order": ["x"], "zdr": False}}
        if model is not None:
            body["model"] = model
        f.request.content = json.dumps(body).encode()
    return f


def test_excepted_model_skips_patch_and_is_audited(tmp_path, monkeypatch):
    # IS4: a request whose body names an except_models entry exactly is
    # forwarded with its body unpatched (the provider retains it), and the
    # skip is written to the audit log -- host, path and model, never the key.
    addon, audit = _except_policy(tmp_path, monkeypatch, ["anthropic/claude-fable-5.1"])
    f = _json_flow(model="anthropic/claude-fable-5.1")
    addon.request(f)
    body = json.loads(f.request.content)
    assert body["provider"] == {"order": ["x"], "zdr": False}  # untouched
    assert body["model"] == "anthropic/claude-fable-5.1"
    (rec,) = audit_lines(audit)
    assert rec["reason"] == "zdr-exception"
    assert rec["host"] == "api.test"
    assert rec["path"] == "/api/v1/chat/completions"
    assert rec["model"] == "anthropic/claude-fable-5.1"


def test_other_model_is_patched(tmp_path, monkeypatch):
    addon, _ = _except_policy(tmp_path, monkeypatch, ["anthropic/claude-fable-5.1"])
    f = _json_flow(model="deepseek/deepseek-v4-flash")
    addon.request(f)
    body = json.loads(f.request.content)
    assert body["provider"]["zdr"] is True
    assert body["provider"]["data_collection"] == "deny"


def test_absent_model_is_patched(tmp_path, monkeypatch):
    # Fail closed: a body with no top-level `model` is patched as before --
    # the exception keys only on an exact, present, string model.
    addon, _ = _except_policy(tmp_path, monkeypatch, ["anthropic/claude-fable-5.1"])
    f = _json_flow(model=None)
    addon.request(f)
    body = json.loads(f.request.content)
    assert body["provider"]["zdr"] is True
    assert body["provider"]["data_collection"] == "deny"


def test_malformed_body_still_fails_closed(tmp_path, monkeypatch):
    # Fail closed: a body that cannot be parsed to a JSON object is denied
    # exactly as before -- the exception never rescues an unpatchable body.
    addon, audit = _except_policy(tmp_path, monkeypatch, ["anthropic/claude-fable-5.1"])
    f = _json_flow(raw=b"not json")
    addon.request(f)
    assert f.response is not None and f.response.status_code == 403
    assert audit_lines(audit)[-1]["reason"] == "zdr-unpatchable-body"


def test_prefix_lookalike_model_is_patched(tmp_path, monkeypatch):
    # Exact match only: a model whose name merely starts with an excepted one
    # (anthropic/claude-fable-5.1-preview vs ...-5.1) is still patched.
    addon, _ = _except_policy(tmp_path, monkeypatch, ["anthropic/claude-fable-5.1"])
    f = _json_flow(model="anthropic/claude-fable-5.1-preview")
    addon.request(f)
    body = json.loads(f.request.content)
    assert body["provider"]["zdr"] is True
    assert body["provider"]["data_collection"] == "deny"


def test_empty_except_models_patches_everything(tmp_path, monkeypatch):
    # The default: an instance that opts no model out (except_models == [])
    # patches every request -- the negative control proving an empty list is
    # the unchanged behaviour, not a widening.
    addon, _ = _except_policy(tmp_path, monkeypatch, [])
    f = _json_flow(model="anthropic/claude-fable-5.1")
    addon.request(f)
    body = json.loads(f.request.content)
    assert body["provider"]["zdr"] is True
    assert body["provider"]["data_collection"] == "deny"
    assert body["model"] == "anthropic/claude-fable-5.1"
