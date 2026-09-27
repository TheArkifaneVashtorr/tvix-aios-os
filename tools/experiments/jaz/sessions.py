#!/usr/bin/env python3
"""tools/experiments/jaz/sessions.py -- pure message-list -> gateway-request
logic for arm C's Claude-subscription backend (claude_llm.py). Stdlib only,
no `jaz` import: this module is exercised directly by
tests/unit/99-jaz-armc.bats without jaz-lang installed (deliverable 3 of
the arm-C build task).

Spec: docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md
§6b ("The backend"): "The first call opens [a session] with
--system-prompt... Later calls --resume it and send only the new turn...
If JAZ ever rewrites earlier turns rather than appending, the backend
opens a fresh session with the transcript and records that it did."

REVISION (2026-09-27, Opus review of the first cut): the first cut keyed a
"conversation" on a hash of the leading (system) message. That is wrong. The
real jaz-lang v0.2.0a4 source builds each call's messages as
[{"role": "system", ...}, {"role": "user", ...}] via
jaz/protocol/code_only.py's `render_messages` (~line 623-640): the SYSTEM
message is built from depth/recursion/repl-description/scoped-names -- NOT
the task -- while the task-specific content lives in the USER message. A
parent (depth=1) and its depth-1 child, or two sibling children invoked with
identical inputs, can therefore render byte-identical (or near-identical)
system prompts; keying on the system message alone collapses them into one
conversation, which is exactly backwards.

Fixed shape: no key/hash at all. `SessionStore` keeps a flat list of live
conversations, each `{"session_id": str, "sent": list[dict]}` (`sent` is the
full message list -- system included -- as it stood right after the
LAST SUCCESSFUL call for that conversation, with the model's reply
appended). A new call's `messages` matches conversation C iff `C.sent` is an
exact prefix of `messages` AND every message after that prefix has
role == "user" (a non-empty tail: an exact-length match with no new turn
does not count as this conversation's next turn). Among all matches, the
LONGEST `C.sent` wins (a longer commitment is a more specific, more
recently-extended match). No match -> a brand-new session, unconditionally
-- including when two conversations share an identical opening (two
siblings with identical inputs): neither is "extended" by messages whose
own length does not exceed theirs, so both correctly stay separate.

`sent` is committed only in `record()`, and only for the exact `session_id`
`plan()` returned -- never speculatively in `plan()` itself. This is what
gives a retry its right behaviour: if a "first" call fails, nothing was
committed, so `plan()` on a retry with the SAME `messages` finds no match
again and proposes ANOTHER fresh session id (opens, never resumes) -- and if
an "append" call fails, the matched conversation's `sent` is untouched, so a
retry naturally resumes the SAME session again.

Claude Code session ids must be dashed UUIDs (`claude` rejects a bare
`.hex`: "Invalid session ID. Must be a valid UUID.") -- `plan()` mints
`str(uuid.uuid4())`, never `.hex`.

ContextWindowWarning (jaz/hooks/builtin/context_window.py:144,
`on_llm_query_enter`) injects its `warning_text` as a TRANSIENT
`AddMessages([{"role": "user", "content": warning_text}])` at Enter time --
composed onto that one call's `messages` for display, never persisted into
the agent's own history. If `record()` committed it into `sent`, the NEXT
real call's `messages` (which never carries the transient line) would no
longer have `sent` as a prefix, and every subsequent turn on that agent
would misfire as a "new session". `SessionStore` is therefore constructed
with the exact `warning_text` strings to strip: both `plan()` and `record()`
drop a trailing run of such messages before doing anything else.

REVISION (2026-09-27, second Opus review): stripping is for MATCHING and
RECORDING only -- the warning itself still has to reach the model, or the
hook does nothing. `plan()` matches against the STRIPPED list (so a call
whose own tail is the warning still recognises its own conversation), but
slices the TAIL it actually SENDS out of the ORIGINAL, unstripped list at
that same prefix length -- so a call whose `messages` end in the warning
sends the real turn AND the warning text, never just the real turn with
the warning silently dropped.
"""

from __future__ import annotations

import uuid


def _strip_trailing(messages: list[dict], strip_texts: frozenset[str]) -> list[dict]:
    """Drop a trailing run of user-role messages whose content is exactly
    one of `strip_texts` (a hook's transient warning_text, never persisted
    into JAZ's own history -- see the module docstring)."""
    if not strip_texts:
        return list(messages)
    end = len(messages)
    while (
        end > 0
        and messages[end - 1].get("role") == "user"
        and messages[end - 1].get("content") in strip_texts
    ):
        end -= 1
    return list(messages[:end])


def serialize_transcript(body: list[dict]) -> str:
    """Render a message list as one plain-text transcript -- used whenever
    a Claude Code session needs the WHOLE history handed over as one
    prompt (a brand-new session whose messages already number more than
    one)."""
    lines = []
    for m in body:
        role = m.get("role", "user")
        content = m.get("content", "")
        lines.append(f"{role.upper()}: {content}")
    return "\n\n".join(lines)


class SessionStore:
    """A flat table of live JAZ-agent conversations -> Claude Code
    sessions, matched by exact-prefix + all-user-tail (see the module
    docstring). Not thread-safe and not persisted across process restarts;
    run_arm_c.py keeps exactly one instance for the life of one run.
    """

    def __init__(self, strip_texts: list[str] | None = None) -> None:
        self._conversations: list[
            dict
        ] = []  # [{"session_id": str, "sent": list[dict]}]
        self._strip_texts: frozenset[str] = frozenset(strip_texts or ())

    def _find_match(self, messages: list[dict]) -> dict | None:
        best = None
        for conv in self._conversations:
            sent = conv["sent"]
            n = len(sent)
            if n == 0 or n >= len(messages):
                continue
            if messages[:n] != sent:
                continue
            tail = messages[n:]
            if not all(m.get("role") == "user" for m in tail):
                continue
            if best is None or n > len(best["sent"]):
                best = conv
        return best

    def plan(self, messages: list[dict]) -> dict:
        """Return the gateway request fields for `messages` (JAZ's current,
        full OpenAI-format message list for one agent's next LLM call).

        Returns {"session_id": str, "first": bool, "system": str | None,
        "message": str}. Call `record(messages, reply, session_id)` with
        the SAME `messages` and the returned `session_id` once the gateway
        call returns ok; call nothing on failure (see the module docstring
        on retries).
        """
        stripped = _strip_trailing(messages, self._strip_texts)
        system = (
            stripped[0].get("content")
            if stripped and stripped[0].get("role") == "system"
            else None
        )

        # Matching happens on the STRIPPED list (a call whose own tail IS
        # the transient warning must still recognise its own
        # conversation); the text actually sent is sliced out of the
        # ORIGINAL, unstripped `messages` at that same prefix length, so
        # the warning itself is delivered rather than silently dropped.
        match = self._find_match(stripped)
        if match is not None:
            prefix_len = len(match["sent"])
            tail = messages[prefix_len:]
            message = (
                tail[0]["content"] if len(tail) == 1 else serialize_transcript(tail)
            )
            return {
                "session_id": match["session_id"],
                "first": False,
                "system": system,
                "message": message,
            }

        session_id = str(uuid.uuid4())
        body = (
            messages[1:]
            if messages and messages[0].get("role") == "system"
            else list(messages)
        )
        message = body[0]["content"] if len(body) == 1 else serialize_transcript(body)
        return {
            "session_id": session_id,
            "first": True,
            "system": system,
            "message": message,
        }

    def record(self, messages: list[dict], reply_text: str, session_id: str) -> None:
        """Commit `messages` (plus the model's `reply_text`) as the new
        `sent` for `session_id` -- the exact id `plan()` returned for this
        call. If `session_id` already names a live conversation (an
        "append"/resume match), its `sent` is updated in place; otherwise a
        new conversation entry is appended (the "first"/new-session case).
        Call only after an OK gateway response -- never on failure."""
        messages = _strip_trailing(messages, self._strip_texts)
        sent = messages + [{"role": "assistant", "content": reply_text}]
        for conv in self._conversations:
            if conv["session_id"] == session_id:
                conv["sent"] = sent
                return
        self._conversations.append({"session_id": session_id, "sent": sent})
