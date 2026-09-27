#!/usr/bin/env python3
"""tools/experiments/jaz/claude_llm.py -- the jaz BaseLLM subclass that
routes every completion call through gateway.py over a Unix socket, using
sessions.py to decide whether a call opens a fresh Claude Code session or
resumes an existing one.

Spec: docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md
§6b, item 1 ("The backend"). Real signatures verified against the built
jaz-lang v0.2.0a4 package (pkgs/jaz-lang):

    class BaseLLM(ABC):
        def complete(self, model: str, messages: list[Any], **kwargs) -> LLMResponse: ...
        def get_model_info(self) -> dict[str, Any]: ...          # llm.py:790, overridable
        @property
        def non_retryable_exceptions(self) -> tuple[type[BaseException], ...]: ...  # llm.py:546

and jaz/_agent.py's one call site, `complete_fn(model=self.model,
messages=shown, **self.llm_client.request_defaults)` -- no session id is
ever passed in, which is why sessions.py matches on the message list
itself (see its module docstring).

`get_model_info()` is overridden here because `ContextWindowWarning`
(jaz/hooks/builtin/context_window.py:163) reads
`config.llm.get_model_info().get("max_input_tokens")` to compute its
fraction-of-window ratio; the base implementation looks the CONFIGURED
MODEL STRING up in jaz's bundled LiteLLM pricing table
(jaz/llm/pricing.py:_PRICING_DATA), which has no entry for an internal id
like "claude-fable-5-1" -- so without an override the hook silently never
fires (ratio stays None). The override reports the real subscription
window/output cap from the probe's own init/result events (2026-09-27,
`claude` 2.1.280: `contextWindow: 1000000`, `maxOutputTokens: 64000`).

`non_retryable_exceptions` is overridden to add `GatewayRefused`: the base
class retries anything else up to 10x (llm.py's default `max_retries`),
which is wrong for a refusal this backend raises on purpose (a rate-limit
stop, a bad `apiKeySource`, a malformed gateway response) -- retrying that
just re-asks a gateway that already said no.

This module imports `jaz` and is therefore NOT exercised by the bats
suite (tests/unit/99-jaz-armc.bats runs in a sandbox with no jaz-lang);
it is covered by a pytest file run in the devShell against the real
jaz-lang package (see the build report for the exact invocation).
"""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sessions  # noqa: E402 -- path insert above must run first

from jaz.llm.llm import BaseLLM, LLMResponse  # noqa: E402

DEFAULT_TIMEOUT = 900.0

# The probe's own init/result events (2026-09-27, claude 2.1.280): see the
# module docstring's get_model_info note.
DEFAULT_MAX_INPUT_TOKENS = 1_000_000
DEFAULT_MAX_OUTPUT_TOKENS = 64_000


class GatewayRefused(Exception):
    """Raised by `ClaudeGatewayLLM.complete` when gateway.py reports
    {"ok": false, ...} -- a refusal (rate-limit stop, a non-`none`
    `apiKeySource`, a malformed request) or an error the `result` event
    itself carried (`is_error`/a non-success `subtype`). Listed in
    `non_retryable_exceptions` below so tenacity never retries it."""


def call_gateway(
    socket_path: str, request: dict, timeout: float = DEFAULT_TIMEOUT
) -> dict:
    """Send one JSON-lines request to gateway.py over `socket_path` and
    return its JSON response. Raises OSError/json.JSONDecodeError on a
    transport-level failure (an error the gateway itself reported comes
    back as a normal {"ok": False, ...} dict, not an exception)."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect(socket_path)
        sock.sendall((json.dumps(request) + "\n").encode("utf-8"))
        try:
            sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
    line = b"".join(chunks).split(b"\n", 1)[0]
    return json.loads(line.decode("utf-8"))


class ClaudeGatewayLLM(BaseLLM):
    """A jaz BaseLLM backend that never talks to Anthropic directly: every
    `complete()` call is relayed to gateway.py, the one process that holds
    `claude` and the operator's subscription login.
    """

    def __init__(
        self,
        *,
        socket_path: str,
        model: str | None = None,
        effort: str = "high",
        timeout: float = DEFAULT_TIMEOUT,
        max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        warning_texts: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, **kwargs)
        self.socket_path = socket_path
        self.effort = effort
        self.timeout = timeout
        self.max_input_tokens = max_input_tokens
        self.max_output_tokens = max_output_tokens
        self._sessions = sessions.SessionStore(strip_texts=warning_texts)
        self.calls: list[dict] = []  # one usage/rate_limit record per call

    def get_model_info(self) -> dict[str, Any]:
        return {
            "max_input_tokens": self.max_input_tokens,
            "max_output_tokens": self.max_output_tokens,
        }

    @property
    def non_retryable_exceptions(self) -> tuple[type[BaseException], ...]:
        return (*super().non_retryable_exceptions, GatewayRefused)

    def usage_summary(self) -> dict:
        """Aggregate token/cost totals and the most recent rate-limit
        reading across every call this backend has made -- what
        run_arm_c.py's --smoke mode prints."""
        totals = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
        cost = 0.0
        last_rate_limit = None
        for record in self.calls:
            usage = record.get("usage") or {}
            for field in totals:
                totals[field] += usage.get(field) or 0
            cost += record.get("cost_estimate") or 0.0
            if record.get("rate_limit"):
                last_rate_limit = record["rate_limit"]
        return {
            "calls": len(self.calls),
            "usage": totals,
            "cost_estimate": cost,
            "rate_limit": last_rate_limit,
        }

    def complete(self, model: str, messages: list[Any], **kwargs: Any) -> LLMResponse:
        plan = self._sessions.plan(messages)
        request = {
            "session_id": plan["session_id"],
            "first": plan["first"],
            "system": plan["system"],
            "model": model,
            "effort": self.effort,
            "message": plan["message"],
        }
        response = call_gateway(self.socket_path, request, timeout=self.timeout)

        if not response.get("ok"):
            raise GatewayRefused(
                f"ClaudeGatewayLLM: gateway refused/failed: {response.get('error')}"
            )

        text = response.get("text") or ""
        self._sessions.record(messages, text, plan["session_id"])

        usage = response.get("usage") or {}
        rate_limit = response.get("rate_limit") or {}
        self.calls.append(
            {
                "usage": usage,
                "cost_estimate": response.get("cost_estimate"),
                "rate_limit": rate_limit,
            }
        )

        input_tokens = usage.get("input") or 0
        cache_read = usage.get("cache_read") or 0
        cache_creation = usage.get("cache_creation") or 0
        return LLMResponse(
            content=text,
            prompt_tokens=input_tokens + cache_read + cache_creation,
            completion_tokens=usage.get("output"),
            cached_tokens=cache_read,
            cost_usd=response.get("cost_estimate"),
            extra={
                "rate_limit": rate_limit,
                "cache_creation_input_tokens": cache_creation,
                "session_id": plan["session_id"],
            },
        )
