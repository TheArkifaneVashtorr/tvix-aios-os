"""Egress broker policy addon for mitmproxy.

Default-deny allowlist, JSONL audit log, credential injection at egress.
All policy comes from the JSON file named by $BROKER_POLICY; this file is
mechanism only. See docs/superpowers/specs 2.3 and brief 5.3.
"""

import json
import os
import posixpath
import re
import sys
import time
import urllib.parse
import uuid

from mitmproxy import http
from mitmproxy.net.http.http1 import expected_http_body_size

DENY_BODY = b"egress-broker: denied\n"

# Must match the "1m" in egressBroker.nix's --set stream_large_bodies=1m --
# mitmproxy's "m" suffix means MiB (utils/human.py:SIZE_UNITS), not 10**6.
# Used only to predict whether mitmproxy's own body-size machinery might
# still flip flow.request.stream = True for a request we're about to deny;
# see _deny_request.
STREAM_THRESHOLD_BYTES = 1024 * 1024

# How many tail bytes of a streamed SSE response the usage tee keeps, so the
# last usage frame survives without buffering the whole completion (the seat's
# latency). The tee trims to the LAST this-many bytes; the usage frame is the
# last `data:` frame carrying a `usage` object before `[DONE]`.
USAGE_TAIL_BYTES = 65536

# The seat's task address (sent as the x-factory-task request header, OC9):
# `<run>/<key>`, each half the evidence store's KEY_RE shape (streams.py) and
# the same length bound. The value is one address, validated as one -- never
# a shape, so "ocw2/../OC5" is refused whole, not split (D9).
FACTORY_TASK_RE = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9_-]{0,31})/([A-Za-z0-9][A-Za-z0-9_-]{0,31})$"
)


def _normalized_path(raw):
    """Path without query/fragment, percent-decoded once, dots and duplicate
    slashes resolved, casefolded. None when the result still carries an escape
    (double encoding) or does not start with '/'."""
    path = raw.split("?", 1)[0].split("#", 1)[0]
    decoded = urllib.parse.unquote(path)
    if "%" in decoded or not decoded.startswith("/"):
        return None
    norm = posixpath.normpath(decoded)
    # posixpath.normpath preserves a leading "//" (a POSIX implementation-
    # defined path); collapse any leading slash run to a single "/" so
    # "//api/..." and "/api/..." normalise identically.
    norm = "/" + norm.lstrip("/")
    if decoded.endswith("/") and not norm.endswith("/"):
        norm += "/"
    return norm.casefold()


def _prefix_match(path, prefixes):
    norm = _normalized_path(path)
    if norm is None:
        return None  # caller decides: deny for deny_paths, no-match for inject
    return any(norm.startswith(_normalized_path(p) or "\0") for p in prefixes)


def _last_usage_frame(tail):
    """The last SSE `data:` frame whose decoded payload is an object carrying a
    `usage` dict, walking the buffered tail from the end; None when there is no
    such frame. `[DONE]` and unparseable frames are skipped, and a parse failure
    on one frame never aborts the walk."""
    for line in reversed(tail.split(b"\n")):
        line = line.strip()
        if not line.startswith(b"data:"):
            continue
        payload = line[len(b"data:") :].strip()
        if payload == b"[DONE]":
            continue
        try:
            obj = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(obj, dict) and isinstance(obj.get("usage"), dict):
            return obj
    return None


class EgressPolicy:
    def __init__(self):
        with open(os.environ["BROKER_POLICY"], encoding="utf-8") as f:
            policy = json.load(f)
        self.instance = policy["instance"]
        self.allow = set(policy["allow"])
        self.inject = policy.get("inject", {})
        # host -> {"path_prefixes": [str], "merge": dict}: JSON request bodies
        # to that host on any of those path prefixes get the dict merged in
        # (policy keys win). This is how the data policy (e.g. OpenRouter
        # zero-data-retention routing) is enforced for every client of an
        # instance, whatever it sends.
        self.body_patch = policy.get("body_patch", {})
        # host -> {"path_prefixes": [str]}: paths this instance never
        # forwards, denied before credential injection (audit reason
        # path-not-permitted). This is the fail-closed denylist for endpoints
        # no client of this instance may use -- e.g. OpenRouter's
        # Anthropic-style /api/v1/messages, which nothing consumes (the seat
        # and the lane both use chat completions; O3 resolved: fail closed).
        self.deny_paths = policy.get("deny_paths", {})
        # host -> {"allow_websocket": bool}: hosts whose policy admits a
        # WebSocket upgrade. Absent defaults to deny (fail closed), so a
        # rendered policy is unchanged by this task's new code path.
        self.allow_websocket = policy.get("allow_websocket", {})
        self.audit_log = policy["audit_log"]
        self.usage_log = policy.get(
            "usage_log", os.path.join(os.path.dirname(self.audit_log), "usage.jsonl")
        )
        self.usage_path_prefixes = policy.get(
            "usage_path_prefixes", ["/api/v1/chat/completions"]
        )
        self.secrets = {}
        for host, spec in self.inject.items():
            with open(spec["value_file"], encoding="utf-8") as f:
                self.secrets[host] = f.read().strip()

    def _body_bytes(self, message):
        """len(raw_content), falling back to the declared Content-Length when
        the body was streamed (responseheaders set .stream = True, or
        stream_large_bodies kicked in on either side) so raw_content was
        never buffered. 0 if there's no message or no length was declared
        (e.g. chunked SSE)."""
        if message is None:
            return 0
        if message.raw_content is not None:
            return len(message.raw_content)
        content_length = message.headers.get("content-length")
        return int(content_length) if content_length is not None else 0

    def _audit(self, flow, verdict, reason):
        if flow.metadata.get("egress_audited"):
            return
        flow.metadata["egress_audited"] = True
        peer = getattr(flow.client_conn, "peername", None)
        rec = {
            "ts": time.time(),
            "instance": self.instance,
            "request_id": self._request_id(flow),
            "client": peer[0] if peer else None,
            "method": flow.request.method,
            "host": flow.request.host,
            "host_header": flow.request.pretty_host,
            "sni": getattr(flow.client_conn, "sni", None),
            "path": flow.request.path,
            "bytes_out": self._body_bytes(flow.request),
            "bytes_in": self._body_bytes(flow.response),
            "verdict": verdict,
            "reason": reason,
        }
        with open(self.audit_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def _audit_exception(self, flow, model):
        """One JSONL line recording a per-model body-patch exception: when a
        request's top-level `model` exactly matches a body_patch host's
        except_models entry, the patch is skipped and this line proves it
        after the fact -- naming the host, the path and the model, never the
        injected key. Distinct from _audit (which is guarded by the
        egress_audited flag and written once per flow on response/error/deny):
        the skip fires during request(), before the response-side allow line,
        and is a separate, deliberate record."""
        rec = {
            "ts": time.time(),
            "instance": self.instance,
            "request_id": self._request_id(flow),
            "host": flow.request.host,
            "path": flow.request.path,
            "model": model,
            "reason": "zdr-exception",
        }
        with open(self.audit_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def _request_id(self, flow):
        """A 32-hex request id minted once per flow, whichever hook asks first.
        Shared by the audit and usage records so they join on the same id."""
        return flow.metadata.setdefault("egress_request_id", uuid.uuid4().hex)

    def _take_factory_task(self, flow):
        """Pop the client's x-factory-task header into the flow's metadata.

        The header (``<run>/<key>``, the task address the seat sends with
        OC9) is removed from every flow -- allowed or denied, well-formed or
        not -- before _inject and before any upstream write: a client header
        may reach the usage record, never the upstream. A well-formed value
        is recorded as (run, key) in the flow's metadata, which _usage_record
        reads later; a malformed value is dropped like a well-formed one and
        the request always proceeds (D9). Called as the first statement of
        requestheaders and of request: several unit tests call request()
        directly without requestheaders, and the second call finds no header
        and leaves the metadata alone (idempotent)."""
        raw = flow.request.headers.pop("x-factory-task", None)
        m = FACTORY_TASK_RE.match(raw or "")
        if m:
            flow.metadata["egress_factory_task"] = (m.group(1), m.group(2))

    def _usage_path(self, flow):
        """True when this flow's request path is inside the usage path prefixes
        -- the completions path whose response usage is worth recording."""
        return bool(_prefix_match(flow.request.path, self.usage_path_prefixes))

    def _usage_tee(self, flow):
        """A tee for a streamed SSE response: forwards every byte unchanged
        while buffering only the last USAGE_TAIL_BYTES into the flow's metadata
        so `_record_usage` can find the last usage frame. Never decodes, never
        raises; the trailing b"" end-of-stream call passes straight through."""

        def tee(data):
            tail = flow.metadata.setdefault("egress_usage_tail", bytearray())
            tail.extend(data)
            if len(tail) > USAGE_TAIL_BYTES:
                del tail[: len(tail) - USAGE_TAIL_BYTES]
            return data

        return tee

    def _record_usage(self, flow):
        """One JSONL line beside the audit line for a completions response,
        carrying the parsed usage frame's cost/cache-split/provider/generation
        id -- never the content. A no-op off the usage path; status `ok`,
        `no-usage` or `unparsed`; a write failure is printed to stderr and the
        flow still completes (the audit line is already written)."""
        if flow.metadata.get("egress_denied"):
            return  # the response is the broker's own 403, never upstream's
        if not self._usage_path(flow):
            return
        streamed = "egress_usage_tail" in flow.metadata
        if streamed:
            frame = _last_usage_frame(flow.metadata["egress_usage_tail"])
            status = "ok" if frame is not None else "unparsed"
        else:
            raw = flow.response.raw_content
            frame = None
            if raw is not None:
                try:
                    frame = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    frame = None
            if isinstance(frame, dict):
                status = "ok" if isinstance(frame.get("usage"), dict) else "no-usage"
            else:
                frame = None
                status = "unparsed"
        rec = self._usage_record(flow, streamed, status, frame)
        try:
            with open(self.usage_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError as exc:
            print(f"egress-broker: usage log write failed: {exc}", file=sys.stderr)

    def _usage_record(self, flow, streamed, status, frame):
        """The usage record, one null per absent field, keys in the stream order.
        run_id/key come from the flow's metadata (the x-factory-task address
        _take_factory_task popped); the audit record carries no task field."""
        run, key = flow.metadata.get("egress_factory_task", (None, None))
        if isinstance(frame, dict):
            gen_id = frame.get("id")
            model = frame.get("model")
            provider = frame.get("provider")
            usage = frame.get("usage")
            usage = usage if isinstance(usage, dict) else {}
        else:
            gen_id = model = provider = None
            usage = {}
        prompt_details = usage.get("prompt_tokens_details")
        prompt_details = prompt_details if isinstance(prompt_details, dict) else {}
        completion_details = usage.get("completion_tokens_details")
        completion_details = (
            completion_details if isinstance(completion_details, dict) else {}
        )
        cost_details = usage.get("cost_details")
        cost_details = cost_details if isinstance(cost_details, dict) else {}
        return {
            "ts_epoch": time.time(),
            "instance": self.instance,
            "request_id": self._request_id(flow),
            "streamed": streamed,
            "http_status": flow.response.status_code,
            "status": status,
            "run_id": run,
            "key": key,
            "gen_id": gen_id,
            "model": model,
            "provider": provider,
            "cost_usd": usage.get("cost"),
            "upstream_cost_usd": cost_details.get("upstream_inference_cost"),
            "is_byok": usage.get("is_byok"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "cached_tokens": prompt_details.get("cached_tokens"),
            "cache_write_tokens": prompt_details.get("cache_write_tokens"),
            "reasoning_tokens": completion_details.get("reasoning_tokens"),
        }

    def _request_body_might_stream(self, flow):
        """True if mitmproxy's check_body_size() (proxy/layers/http/
        __init__.py in mitmproxy 12.2.3, the flake-pinned pkgs.mitmproxy --
        the host's 12.1.1 has identical logic under different line numbers)
        has already started streaming this request's body, or could still.
        Decides, in _deny_request, whether a synthetic 403 response is safe
        to hand back or whether the flow has to be killed instead.

        Delegates the "how big is this body" question to mitmproxy's own
        expected_http_body_size() -- the same function check_body_size()
        itself calls -- rather than reimplementing it: a bodiless GET has
        no Content-Length header at all, same as a chunked POST with an
        unbounded body, and only expected_http_body_size() knows that the
        former is defined as zero-length (RFC 7230 3.3 rule 6) while the
        latter returns None (true size unknown until it has already
        arrived, so it can't be ruled out safe)."""
        if flow.request.stream:
            return True
        try:
            expected_size = expected_http_body_size(flow.request)
        except ValueError:
            # Malformed Content-Length/Transfer-Encoding: check_body_size()
            # gives up identically ("we just don't stream/kill malformed
            # content-length headers") and never streams it either.
            return False
        if expected_size is None:
            return True
        return expected_size > STREAM_THRESHOLD_BYTES

    def _deny(self, flow, reason):
        """Deny with a synthetic 403 response. Only safe when the flow has
        no request body mitmproxy could still be streaming: CONNECT
        (http_connect()) has no body at all, and handle_connect() branches
        off state_wait_for_request_headers before check_body_size() or
        start_request_stream() ever run, so it's unconditionally fine here.
        Anything with a body -- requestheaders()/request() -- goes through
        _deny_request instead, which picks this or a kill depending on
        whether that body is safe to buffer."""
        flow.metadata["egress_denied"] = True
        flow.response = http.Response.make(
            403, DENY_BODY, {"content-type": "text/plain"}
        )
        self._audit(flow, "deny", reason)

    def _deny_request(self, flow, reason):
        """Deny a request that has (or might yet get) a body. mitmproxy
        cannot both set flow.response and stream/buffer-then-restream that
        body, so which mechanism is safe depends on
        _request_body_might_stream:

        - Body bounded and <= STREAM_THRESHOLD_BYTES: a plain 403 (via
          _deny) is always safe. mitmproxy's state_consume_request_body
          re-runs check_body_size() on every chunk it buffers (the "late"
          case, using len(request_body_buf)), but that running total can
          never exceed the Content-Length already checked here, so it can
          never cross the threshold and flip .stream after the fact.

        - Body already streaming, or its size is unknown/over the
          threshold: flow.kill() instead. requestheaders() fires from
          state_wait_for_request_headers before any body byte is consumed;
          mitmproxy's check_killed() runs immediately after the hook
          returns and, seeing the kill, sends the client
          ResponseProtocolError(code=KILL) and jumps straight to
          state_errored -- start_request_stream() (which raises
          NotImplementedError: "Can't set a response and enable streaming
          at the same time" whenever flow.response is set) and
          state_consume_request_body's own per-chunk re-check never run, so
          no body byte reaches upstream and mitmproxy never crashes.
          Tradeoff: ErrorCode.KILL has no HTTP status
          (proxy/layers/http/_events.py), so the client sees the connection
          close rather than our 403 body -- there is no way to hand back an
          application-level response here without risking the same crash.
        """
        if self._request_body_might_stream(flow):
            flow.kill()
            self._audit(flow, "deny", reason)
        else:
            self._deny(flow, reason)

    def _check(self, flow):
        """Allowlist + SNI-mismatch check, shared by requestheaders (runs
        before any body streams upstream -- the path that matters in
        production) and request (defense in depth: several existing unit
        tests call request() directly without going through requestheaders
        first, and mitmproxy itself still fires this hook for every real
        flow so a second, redundant pass here is cheap and harmless).
        _audit's egress_audited guard means whichever hook denies first wins
        and the second is a no-op, never overwriting the 403 (or the
        kill)."""
        host = flow.request.host  # the destination mitmproxy connects to (D8)
        claimed = flow.request.pretty_host  # the Host header, client-controlled
        sni = getattr(flow.client_conn, "sni", None)
        # Hostnames are case-insensitive (RFC 3986 3.2.2, RFC 9110 4.2.3) and
        # may carry a trailing dot, so compare the casefolded names with any
        # trailing dot stripped -- while keeping the raw values for the audit
        # row and the reason string below.
        if claimed.rstrip(".").casefold() != host.rstrip(".").casefold():
            # A Host header disagreeing with the routed destination is always
            # a mismatch, on allowlisted and denied hosts alike: an attacker
            # who routes to a denied host while claiming an allowlisted Host
            # header (r2-1-1) must be flagged before the allowlist can even
            # be consulted, never silently lumped in with "not-allowlisted".
            self._deny_request(
                flow, f"host-header-mismatch: host={host} header={claimed}"
            )
            return False
        if host not in self.allow:
            reason = "not-allowlisted"
            if sni and sni != host:
                reason = f"host/sni mismatch: sni={sni} host={host}"
            self._deny_request(flow, reason)
            return False
        if sni and sni != host:
            self._deny_request(flow, f"host/sni mismatch: sni={sni} host={host}")
            return False
        return True

    def _denied_path(self, flow):
        """Reason string when this flow's host has a deny_paths entry whose
        any path_prefixes matches the (normalised) request path, else None.
        Runs before credential injection so a refused request never carries
        the injected credential (fail closed, O3)."""
        spec = self.deny_paths.get(flow.request.host)
        if not spec:
            return None
        m = _prefix_match(flow.request.path, spec.get("path_prefixes", []))
        if m is None:
            return "path-not-normalizable"
        if m:
            return "path-not-permitted"
        return None

    def _is_websocket_upgrade(self, flow):
        """True when this request is a WebSocket upgrade: an `Upgrade` header
        whose comma-split, lower-cased tokens contain `websocket` (RFC 7230
        6.7 permits a list, so `Upgrade: websocket, h2c` still offers the
        WebSocket protocol) AND a `Connection` header whose comma-split,
        lower-cased tokens contain `upgrade`. This is only the early
        request-side refusal: mitmproxy itself switches to WebsocketLayer on
        the RESPONSE (status 101 + the response's `Upgrade: websocket` + the
        request's `Sec-WebSocket-Version: 13`), never consulting
        `Connection`, and upstreams rewrite that header anyway -- so the
        definitive gate is the 101 check in `response()`."""
        upgrade = (flow.request.headers.get("Upgrade") or "").lower()
        connection = (flow.request.headers.get("Connection") or "").lower()
        upgrade_tokens = [t.strip() for t in upgrade.split(",")]
        connection_tokens = [t.strip() for t in connection.split(",")]
        return "websocket" in upgrade_tokens and "upgrade" in connection_tokens

    def _websocket_allowed(self, host):
        """Whether this host's policy carries `allow_websocket: true`. Absent
        defaults to deny (fail closed), so no rendered policy changes."""
        return bool(self.allow_websocket.get(host, {}).get("allow_websocket", False))

    def _inject(self, flow):
        """Write the configured credential header, if this host has one and
        the request path is inside that host's own path allowlist
        (inject.<host>.paths, default ["/"] = every path, the pre-N3
        back-compatible behaviour). The inject allowlist is independent of
        bodyPatch's: the credential must not be scoped to the patched path
        only -- that would strip the header from the agent lane's other
        calls and break it. Must run from requestheaders(), not just
        request(): with stream_large_bodies set, mitmproxy sends the request
        headers upstream immediately after the requestheaders hook returns
        (see start_request_stream() in proxy/layers/http/__init__.py)
        whenever the body exceeds the streaming threshold -- request() only
        fires later, at end-of-body, by which point the headers already left
        without whatever it set. Calling this again from request() is a
        harmless no-op re-set for hosts requestheaders already handled, and
        the only path that matters for direct-call unit tests."""
        host = flow.request.host
        if host in self.secrets:
            spec = self.inject[host]
            paths = spec.get("paths", ["/"])
            if not _prefix_match(flow.request.path, paths):
                return
            flow.request.headers[spec.get("header", "Authorization")] = (
                spec.get("prefix", "Bearer ") + self.secrets[host]
            )

    def http_connect(self, flow):
        if flow.request.host not in self.allow:
            self._deny(flow, "connect-not-allowlisted")
            return
        if flow.request.port != 443:
            # A CONNECT to an allow-listed host on any other port would
            # tunnel to mitmproxy's raw-TCP path: no requestheaders/request
            # hook ever fires for it (only http_connect does), so nothing
            # downstream could log or refuse it (docs/brief.md sec 3
            # invariant 3). Reject it here instead, before the tunnel opens.
            self._deny(flow, "connect-port-not-permitted")
            return
        self._audit(flow, "allow", "ok")

    def _patch_spec(self, flow):
        """The body-patch spec matching this flow's host and path, or None.
        A spec matches when any of its path_prefixes (a list, default
        ["/"]) matches the normalised request path. A body_patch host whose
        path cannot be normalised fails closed (path-not-normalizable),
        mirroring _denied_path: forwarding the body without the ZDR merge --
        and without the credential -- would let the data policy silently
        escape."""
        spec = self.body_patch.get(flow.request.host)
        if not spec:
            return None
        prefixes = spec.get("path_prefixes", ["/"])
        m = _prefix_match(flow.request.path, prefixes)
        if m is None:
            self._deny_request(flow, "path-not-normalizable")
            return None
        if not m:
            return None
        return spec

    def _patch_body(self, flow):
        """Merge the instance's body patch into a JSON request body, or fail
        closed when this flow's body cannot be patched (content type not
        application/json, no body, not JSON, or not an object). A body whose
        top-level `model` exactly equals one of the host's except_models
        entries skips the merge -- an exact-string match, audited, never a
        prefix or glob -- while every other case (no `model`, a non-string
        `model`, an unparseable body) is patched or denied as before."""
        spec = self._patch_spec(flow)
        if not spec:
            return
        media = (
            flow.request.headers.get("content-type", "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )
        try:
            body = json.loads(flow.request.get_content(strict=False) or b"")
        except (ValueError, UnicodeDecodeError):
            body = None
        if media != "application/json" or not isinstance(body, dict):
            self._deny_request(flow, "zdr-unpatchable-body")
            return

        model = body.get("model")
        if isinstance(model, str) and model in spec.get("except_models", []):
            self._audit_exception(flow, model)
            return

        def merge(dst, src):
            for k, v in src.items():
                if isinstance(v, dict) and isinstance(dst.get(k), dict):
                    merge(dst[k], v)
                else:
                    dst[k] = v

        merge(body, spec.get("merge", {}))
        flow.request.content = json.dumps(body).encode("utf-8")

    def requestheaders(self, flow):
        self._take_factory_task(flow)
        if not self._check(flow):
            return
        reason = self._denied_path(flow)
        if reason:
            self._deny_request(flow, reason)
            return
        if self._is_websocket_upgrade(flow):
            # A WebSocket upgrade is a stream the ordinary SSE/body paths
            # cannot audit; it must be refused or audited here, before it
            # opens. Unlisted hosts are denied; an admitted host is audited
            # allow/websocket-upgrade and the flow proceeds (invariant 3:
            # every byte leaving crosses a chokepoint that logs or refuses).
            if not self._websocket_allowed(flow.request.host):
                self._deny_request(flow, "websocket-upgrade-unlisted")
                return
            self._audit(flow, "allow", "websocket-upgrade")
        if self._patch_spec(flow) is not None and self._request_body_might_stream(flow):
            # A request body on a bodyPatch host/path that mitmproxy is about
            # to stream (stream_large_bodies marks it before this hook runs)
            # can no longer be rewritten: _patch_body runs only from
            # request(), at end-of-body, after every chunk is already on the
            # wire, and raw_content stays None for a streamed body so even
            # the audit record's body would be corrupt. The data policy
            # fails closed: kill the flow before a byte streams upstream and
            # audit the denial. flow.kill() is the only correct mechanism --
            # never flow.request.stream = False: state_consume_request_body
            # re-runs check_body_size() per chunk and flips .stream back on
            # (see _deny_request's docstring for the same reasoning on the
            # allowlist path).
            flow.kill()
            self._audit(flow, "deny", "zdr-unpatchable-streamed-body")
            return
        if flow.response is not None or flow.error is not None:
            # _patch_spec may have denied a body_patch host whose path could
            # not be normalised (path-not-normalizable): never write the
            # injected credential onto a refused request (fail closed, O3).
            return
        self._inject(flow)

    def request(self, flow):
        self._take_factory_task(flow)
        if flow.response is not None or flow.error is not None:
            # Already denied by requestheaders (whether via a 403 response
            # or a kill -- see _deny_request), or answered/errored some
            # other way; do not re-check, re-audit, or call flow.kill() on
            # an already-killed (and so no longer killable()) flow.
            return
        if not self._check(flow):
            return
        reason = self._denied_path(flow)
        if reason:
            self._deny_request(flow, reason)
            return
        self._patch_body(flow)
        # _patch_body may have denied (and audited) the flow: never write the
        # injected credential onto a request whose body could not carry the
        # data policy -- that header must not leak alongside an unpatched
        # body (fail closed, O3).
        if flow.response is not None or flow.error is not None:
            return
        self._inject(flow)

    def responseheaders(self, flow):
        content_type = flow.response.headers.get("content-type", "")
        if content_type.startswith("text/event-stream"):
            flow.response.stream = (
                self._usage_tee(flow) if self._usage_path(flow) else True
            )

    def _deny_websocket_upgrade(self, flow):
        """Refuse a WebSocket upgrade at the 101 response -- the definitive
        gate. The request-side sniff in requestheaders() only catches an
        upgrade whose request carries the RFC 6455 `Connection: upgrade`
        token; mitmproxy switches to WebsocketLayer on the response instead
        (status 101 + `Upgrade: websocket` + `Sec-WebSocket-Version: 13`),
        so an upgrade that omitted that token still reaches a 101 and must be
        refused here, before the 101 is forwarded to the client and the
        layers switch. The flow is killed -- there is no 403 body to hand
        back for an upgrade mitmproxy is about to hand to WebsocketLayer --
        and the denial is audited with a websocket- reason: the same `_deny`
        shape (egress_denied + a deny row), a kill instead of a 403."""
        flow.metadata["egress_denied"] = True
        flow.kill()
        self._audit(flow, "deny", "websocket-upgrade-unlisted")

    def response(self, flow):
        if flow.response.status_code == 101 and not self._websocket_allowed(
            flow.request.host
        ):
            self._deny_websocket_upgrade(flow)
            return
        self._audit(flow, "allow", "ok")
        self._record_usage(flow)

    def error(self, flow):
        self._audit(flow, "error", "upstream or client error")


addons = [EgressPolicy()]
