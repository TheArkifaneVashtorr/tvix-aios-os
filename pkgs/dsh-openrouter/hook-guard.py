"""A deny-only PreToolUse hook for the DeepSeek Harness seat.

The bridge dsh ships (@deepseek-ai/dsh-hooks-claude-code) runs Claude Code
command hooks on dsh's interception seams. This process is the command it
runs: a pure stdin->stdout guard that denies dangerous bash, edit and write
calls by emitting Claude Code's structured deny output on stdout, and (review
2026-09-04, round 2) a compact JSON denial record on **stderr** -- never a
file. dsh's own hook bridge (@deepseek-ai/dsh-hook-protocol,
``appendHookResult``) captures a hook's stderr and stores it verbatim as
``stderrSummary`` on the ``hook/result`` event in the session transcript
(``$DSH_HOME/sessions/<cwd-key>/<session>/session.jsonl.zstd``), capped at
500 chars there; stderr at exit 0 never affects the decision. That transcript
is the audit of record: it lives outside every root the audited model can
write to (workspace-write's writable roots are the workspace and a
per-process tmpfs `/tmp` that never survives the hook invocation -- see the
wrapper for the measurement), so, unlike a log file inside the workspace, it
cannot be edited or deleted by the party it audits. `dsh-openrouter --denials`
(pkgs/dsh-openrouter/dsh-denials.py) reads it back.

It is deny-only on purpose (see the wrapper next to this file and
docs/reviews/2026-09-04-dsh-harness-review.md): ``{"continue": false}`` is
recorded but not applied, ``updatedInput`` is logged but not honoured, a
top-level ``{"decision":"deny"}`` is ignored, and ``allow`` does not
pre-approve -- only ``hookSpecificOutput.permissionDecision`` works.

A deny-list over shell command strings is a heuristic and an audit trail,
NOT a boundary. The real boundaries are file mode, PAM, the wrapper's
refusal list and the lane's netns.

Error contract (RT5r, gate 2026-09-05-opus-review-rt5-RT5). The harness
reads a hook that exits non-zero with empty stdout as a non-blocking error
and runs the tool, so a guard crash is an ALLOW. Therefore:

* ``main()`` returns 0 on every path -- deny is expressed only through the
  JSON on stdout, never through the exit code, and a top-level
  ``try/except BaseException`` around the rule evaluation guarantees it.
* The MODEL rule fails closed: any unexpected exception while evaluating it
  (walking ``tool_input``, reading or parsing the routing table -- including
  ``UnicodeDecodeError``, ``RecursionError``, ``MemoryError``) is a DENY
  with reason ``model rule could not be evaluated: <ExceptionName>``.
* A sub-agent tool (``subagent`` / ``subagent_fork`` / ``workflow``) whose
  ``tool_input`` is not a JSON object is a DENY with reason
  ``model rule could not be evaluated: tool_input is not an object`` (RT5rb);
  bash/edit/write keep the old coercion of a non-object ``tool_input`` to ``{}``.
* The bash string-scan and edit/write path rules keep today's allow-on-error:
  they are pure string/path checks that cannot raise, and the asymmetry
  (model = fail closed, deny-only heuristic = allow on error) is deliberate.

Parse contract (RT5rb, gate 2026-09-05-opus-review-rt7-RT5r). The payload
parse itself is now fail-closed: stdin is read with a 4 MiB bound, its
maximum bracket nesting is pre-scanned (string-aware, so a bracket inside a
JSON string is not counted) before the decoder is handed the bytes, and
``json.loads`` runs inside ``main()``'s ``BaseException`` region. A read over
the bound, nesting past the parse guard, or any parse failure
(``RecursionError``, ``MemoryError``, ``ValueError``, or a top level that is
not an object) is a DENY with reason ``payload could not be parsed:
<too large|too deep|ExceptionName>`` -- never a crash, because a non-zero
exit with empty stdout is what the harness reads as ALLOW. The tool name is
not yet known when the payload does not parse, so the denial applies to every
tool: an accepted over-denial (see docs/runbooks/lanes.md).
"""

import json
import os
import re
import sys
import time

import tomllib

HOOK_EVENT = "PreToolUse"

# dsh's hook-protocol caps stderrSummary at 500 chars (server default); stay
# well under that so the record is never itself the thing that gets cut --
# dsh's own truncation marker must never collide with ours.
_STDERR_RECORD_MAX_CHARS = 400

# Paths edit/write must never target, in addition to the HOME-relative
# prefixes built below (~/.claude, ~/.config/openrouter, ~/strategy).
# This set must stay identical to pkgs/lane/lane-submit.py's
# FORBIDDEN_REPO_PREFIXES and the `forbidden=(…)` array in
# dsh-openrouter.sh; tests/lane/test_forbidden_lists_agree.py proves the
# three agree. Generating the list from a single Nix source is still a gap
# (claim `forbidden-list-single-source`).
PROTECTED_ABSOLUTE = [
    "/run/baskets",
    "/var/lib/baskets",
    "/var/lib/helm",
    "/var/lib/egress-broker",
    "/var/lib/lanes",
    "/var/lib/secrets",
]

# A "command word" begins a simple command: at string start or after a shell
# separator. Matching sudo/nixos-rebuild only here (not after any old space)
# keeps `echo sudo` from firing while `x; sudo y` still does.
_SUDO = re.compile(r"(?:^|[;&|\n()])\s*sudo(?=\s|$)")
_NIXOS_REBUILD = re.compile(r"(?:^|[;&|\n()])\s*nixos-rebuild(?=\s|$)")
# systemctl with a mutating verb, tolerating intervening flags (--user,
# --system, --now, ...). `systemctl status` and `--user show-environment`
# are read-only and pass.
_SYSTEMCTL = re.compile(
    r"\bsystemctl\b(?:\s+--?[A-Za-z0-9][A-Za-z0-9=-]*)*\s+"
    r"(start|stop|restart|reload|enable|disable)\b"
)
# The Helm control listener and its per-boot token: a POST there starts a
# root profile switch, and every process running as the operator can read the
# token. A tripwire with an audit record, not a boundary (plan
# 2026-09-05-evidence-store R8; the boundary is Helm Home's password prompt).
_HELM_CONTROL = re.compile(
    r"(?:127\.0\.0\.1|localhost|\[::1\]|0\.0\.0\.0):7700(?:\b|/)"
    r"|/run/user/\d+/helm/token"
    r"|\$\{?XDG_RUNTIME_DIR\}?/helm/token"
)

# RT5r: the model walk is iterative and bounded so a hostile ``tool_input``
# (nesting depth, or a key-count blowup) cannot exhaust the guard's own call
# stack or CPU -- either would crash the guard and, under the harness's
# non-zero-exit-means-allow rule, run the tool. Exceeding a budget raises
# _ToolInputBudgetExceeded, which the model rule turns into a DENY.
# RT5rb: _DEPTH_BUDGET is EXACTLY 64 -- a model at depth 64 is reached by the
# model rule (named in the reason), depth 65 is the budget overrun; the
# header and docs/runbooks/lanes.md both say 64.
_NODE_BUDGET = 10_000
_DEPTH_BUDGET = 64

# RT5rb (contract item 1): stdin is read with a 4 MiB bound; larger is denied
# as "too large". Separately, the JSON bracket nesting is pre-scanned and a
# document nested past _MAX_PARSE_NESTING is denied as "too deep" before
# json.loads is ever asked to decode it -- this sits far above the model
# rule's 64-deep reach (the deepest model the walk names is ~2 brackets inside
# the payload) and far below the ~52,000 nesting at which the decoder itself
# raises RecursionError, so it rejects the hostile-input regime cheaply.
_STDIN_BYTE_BOUND = 4 * 1024 * 1024
_MAX_PARSE_NESTING = 10_000


class _ToolInputBudgetExceeded(Exception):
    """Raised by _walk_model_ids when a node or depth budget is exceeded."""


def _max_bracket_nesting(text):
    """Return the deepest bracket nesting in a JSON document.

    Linear and string-aware: a single pass tracks the number of open ``{``
    and ``[`` brackets, ignoring brackets that sit inside a JSON string
    literal (including ``\\``-escaped quotes and backslashes), so a ``{`` in a
    model id or prompt is never miscounted as structure. RT5rb (contract item
    1): this pre-scan runs before ``json.loads`` so the decoder is never fed a
    hostile depth.
    """
    depth = 0
    max_depth = 0
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch in "}]":
            depth -= 1
    return max_depth


# RT5: the tools whose launch carries a model the routing table must authorise.
# dsh's sub-agent tools are subagent, subagent_fork and workflow; a launch of
# any of them with an explicit `model` (or provider+model) that is not the
# `model` of an OpenRouter row is refused, so the table is applied by the OS
# rather than followed by prose.
_MODEL_TOOLS = ("subagent", "subagent_fork", "workflow")

# A bash command may name a model two ways, both of which a nested
# dsh-openrouter launch uses to dodge the sub-agent tools above: `--model ID`
# and `OPENROUTER_MODEL=ID`. The captured id is constrained to the same
# charset the wrapper validates ([A-Za-z0-9._:/-]+), so a shell-metachar
# payload is never misread as a model and wildcarded into a denial.
#
# RT5b (gate 2026-09-05-opus-review-rt5-RT5): the two most ordinary
# spellings the shell then executes are a quoted id (`--model "ID"`,
# `--model 'ID'`, `--model=ID`, `OPENROUTER_MODEL="ID"`) and a
# `\`-newline continuation, and a quote or backslash sits outside the old
# capture charset so the capture never started. Each pattern now allows an
# optional quote around the id, matched by a backreference to the same close
# quote; the caller strips a `\`+newline continuation before scanning.
# `OPENROUTER_MODEL=` is matched unanchored, so a leading `env ` is simply
# skipped, and the flag's `\s+` already matches a tab separator -- no separate
# `env ` prefix or tab-normalisation pass is needed (RT5r dropped those two
# no-op fragments the RT5b gate flagged as equivalent mutants).
# Group layout: flag = (separator, quote, id); env = (quote, id).
_MODEL_FLAG = re.compile(r"--model(=|\s+)(['\"]?)([A-Za-z0-9._:/-]+)\2")
_OPENROUTER_MODEL_ENV = re.compile(r"OPENROUTER_MODEL=(['\"]?)([A-Za-z0-9._:/-]+)\1")


def _key_file_spellings():
    home = os.environ.get("HOME", "")
    xdg = os.environ.get("XDG_CONFIG_HOME", "") or os.path.join(home, ".config")
    return {
        "~/.config/openrouter/key",
        "$HOME/.config/openrouter/key",
        "${HOME}/.config/openrouter/key",
        "$XDG_CONFIG_HOME/openrouter/key",
        "${XDG_CONFIG_HOME}/openrouter/key",
        os.path.join(xdg, "openrouter", "key"),
    }


def _bash_verdict(command):
    if _SUDO.search(command):
        return "sudo is refused (an operator action)"
    if _NIXOS_REBUILD.search(command):
        return "nixos-rebuild is refused (an operator action)"
    match = _SYSTEMCTL.search(command)
    if match:
        return f"systemctl {match.group(1)} is refused (an operator action)"
    if _HELM_CONTROL.search(command):
        return "the Helm control port and its token are refused (an operator action)"
    if any(spelling in command for spelling in _key_file_spellings()):
        return "reading the OpenRouter key file is refused"
    return None


def _routing_table_path(argv):
    """Resolve the routing-table path the guard reads for the model rule.

    The wrapper always passes `--routing-table <path>`; driving the guard
    bare (tests) falls back to ``$FACTORY_ROUTING_TABLE`` and then to the
    seat default under ``$HOME/nixos-agent-env``, mirroring the wrapper's own
    resolution so one guard sees one table either way.
    """
    for i, arg in enumerate(argv):
        if arg == "--routing-table" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--routing-table="):
            return arg.removeprefix("--routing-table=")
    home = os.environ.get("HOME", "")
    # RT5b (MINOR-3, gate 2026-09-05-opus-review-rt5-RT5): an EMPTY env var
    # must fall back to the default path exactly as the wrapper's ``:-`` does;
    # ``os.environ.get(..., default)`` returns ``""`` for ``FACTORY_ROUTING_TABLE=``,
    # which would fail-closed every explicit model as unreadable at ``""``.
    return os.environ.get("FACTORY_ROUTING_TABLE") or os.path.join(
        home, "nixos-agent-env", "docs", "ledger", "routing.toml"
    )


def _load_openrouter_models(path):
    """Return the set of OpenRouter model ids, or None when the table is
    missing or unparsable (the caller fails closed for an explicit model).

    A row with ``route = "claude"`` is never reachable from this seat and is
    excluded; every other row (no ``route`` key, or ``route = "openrouter"``)
    contributes its ``model``. A missing/unreadable table raises ``OSError``;
    malformed TOML raises ``tomllib.TOMLDecodeError`` (a ``ValueError``
    subclass); either way the table cannot be trusted, so the caller denies
    any explicit model (fail closed). A table that is not valid UTF-8 raises
    ``UnicodeDecodeError`` -- deliberately NOT caught here, so it propagates
    to main()'s fail-closed handler and becomes
    "model rule could not be evaluated", rather than "unreadable" (RT5r).
    """
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    models = set()
    rows = data.get("route")
    if not isinstance(rows, list):
        return set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("route") == "claude":
            continue
        model = row.get("model")
        if isinstance(model, str) and model:
            models.add(model)
    return models


def _model_deny_reason(model, table_path):
    return (
        f"sub-agent model {model} is not a row of {table_path} "
        f"(route openrouter); pick a role and let the table choose"
    )


def _walk_model_ids(node):
    """Yield every non-empty string under a key named ``model``, at any depth.

    RT5b (gate 2026-09-05-opus-review-rt5-RT5): the guard previously read
    only a flat ``tool_input["model"]``. A ``workflow`` launch carries its
    per-step models under ``steps[*].model`` (and could carry a
    ``config.model``), so the same table gate must apply to every nested
    spelling, not just the top level.

    RT5r: the walk is iterative (an explicit stack of ``(value, depth)``
    pairs) rather than recursive, bounded by _NODE_BUDGET nodes and
    _DEPTH_BUDGET nesting depth. Exceeding either raises
    _ToolInputBudgetExceeded, which the model rule turns into a deny -- a
    hostile ``tool_input`` must neither crash the guard (a crash is how the
    harness reads non-zero exit as "allow") nor walk without bound.
    """
    stack = [(node, 0)]
    visited = 0
    while stack:
        current, depth = stack.pop()
        visited += 1
        if visited > _NODE_BUDGET or depth > _DEPTH_BUDGET:
            raise _ToolInputBudgetExceeded()
        if isinstance(current, dict):
            for key, value in current.items():
                if key == "model" and isinstance(value, str) and value:
                    yield value
                # A dict/list value nests one level deeper; a scalar stays at
                # the same depth. RT5rb (contract item 4): without this, the
                # walk pushed the model's own string at depth d+1 and tripped
                # the budget, so a model at depth 64 was reported as a budget
                # overrun (effective budget 63) and its id never reached the
                # model rule.
                if isinstance(value, (dict, list)):
                    stack.append((value, depth + 1))
                else:
                    stack.append((value, depth))
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))
                else:
                    stack.append((item, depth))


def _model_verdict(tool_input, table_path):
    """Deny a sub-agent launch whose explicit model is not an OpenRouter row.

    Returns ``(reason, subject)`` for a deny, or ``None`` to allow. ``subject``
    is the OFFENDING model id (the one not in the table), so the audit record
    names the id that actually violated the rule, not the first id the walk
    happened to find (RT5b MINOR-1).

    RT5r: the walk is iterative and budget-bounded (see _walk_model_ids); a
    budget overrun is a deny with reason "tool_input too deep/large to
    inspect". Any OTHER exception while evaluating the rule -- an undecodable
    routing table raising ``UnicodeDecodeError``, or any unforeseen failure --
    propagates to main()'s fail-closed handler, which turns it into
    ``model rule could not be evaluated: <ExceptionName>``.

    RT5rb (contract item 3): a sub-agent launch whose ``tool_input`` is not a
    JSON object (null, a list, a string, a number) is exactly the unexpected
    shape the model rule fails closed on, so it is denied rather than coerced
    to an empty dict (the coercion is what let a list ``tool_input`` carrying
    a model sail through).
    """
    if not isinstance(tool_input, dict):
        return "model rule could not be evaluated: tool_input is not an object", ""
    try:
        model_ids = list(_walk_model_ids(tool_input))
    except _ToolInputBudgetExceeded:
        return "tool_input too deep/large to inspect", ""
    if not model_ids:
        return None
    models = _load_openrouter_models(table_path)
    if models is None:
        return f"routing table unreadable at {table_path}", model_ids[0]
    for model in model_ids:
        if model not in models:
            return _model_deny_reason(model, table_path), model
    return None


def _bash_model_verdict(command, table_path):
    """Deny a command naming a model that is not an OpenRouter row.

    This is the nested-seat path: a `dsh-openrouter --model ID` or
    `OPENROUTER_MODEL=ID ...` shell command is how a launch would bypass the
    sub-agent tools, so the same table gate applies to the ids a bash command
    names. RT5b: the command is normalised first (a backslash-newline
    continuation is collapsed), so the ordinary quoted/continued spellings
    the shell executes are seen by the two patterns below; a tab separator is
    already matched by the flag's whitespace class directly (RT5r dropped the
    no-op tab-normalisation pass).
    """
    command = command.replace("\\\n", "")
    ids = [m.group(3) for m in _MODEL_FLAG.finditer(command)]
    ids += [m.group(2) for m in _OPENROUTER_MODEL_ENV.finditer(command)]
    if not ids:
        return None
    models = _load_openrouter_models(table_path)
    if models is None:
        return f"routing table unreadable at {table_path}"
    for model in ids:
        if model not in models:
            return _model_deny_reason(model, table_path)
    return None


def _protected_prefixes():
    home = os.environ.get("HOME", "")
    prefixes = []
    if home:
        prefixes.extend(
            [
                os.path.join(home, ".claude"),
                os.path.join(home, ".config", "openrouter"),
                os.path.join(home, "strategy"),
            ]
        )
    prefixes.extend(PROTECTED_ABSOLUTE)
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg:
        prefixes.append(os.path.join(xdg, "openrouter"))
    return prefixes


def _is_within(path, prefix):
    target = os.path.normpath(path)
    root = os.path.normpath(prefix)
    return target == root or target.startswith(root + os.sep)


def _resolve(raw, project_dir):
    expanded = os.path.expanduser(raw)
    if not os.path.isabs(expanded):
        expanded = os.path.join(project_dir, expanded)
    return os.path.normpath(expanded)


def _edit_verdict(file_path, project_dir):
    lex = _resolve(file_path, project_dir)
    for prefix in _protected_prefixes():
        if _is_within(lex, prefix):
            return f"refusing to edit/write {file_path}: under protected path {prefix}"
    real = os.path.realpath(lex)
    real_project = os.path.realpath(project_dir)
    if not _is_within(real, real_project):
        if _is_within(lex, real_project):
            return (
                f"refusing to edit/write {file_path}: a symlink resolves "
                f"outside the workspace"
            )
        return f"refusing to edit/write {file_path}: outside the project directory"
    return None


def _truncated(text, budget):
    if len(text) <= budget:
        return text
    return text[: max(budget - 3, 0)] + "..."


def _record_json(tool, reason, subject):
    return json.dumps(
        {
            "ts": time.time(),
            "event": HOOK_EVENT,
            "tool": tool,
            "reason": reason,
            "subject": subject,
        },
        separators=(",", ":"),
    )


def _denial_record(tool, reason, subject):
    """Build the JSON denial record for stderr, capped under 400 chars.

    ``reason`` for an edit/write denial already embeds ``subject`` (the
    ``file_path``) once or twice, so a long path can blow the budget from
    either field, and JSON string-escaping (quotes, backslashes) can inflate
    a field's encoded length past its raw character count. Never slice the
    serialized JSON itself to force the cap (that can land inside an escape
    sequence and hand the reader invalid JSON) -- shrink the two free-text
    fields and re-serialize on each pass until the whole record fits, or
    both are empty.
    """
    text = _record_json(tool, reason, subject)
    reason_budget = len(reason)
    subject_budget = len(subject)
    while len(text) > _STDERR_RECORD_MAX_CHARS and (
        reason_budget > 0 or subject_budget > 0
    ):
        step = max((reason_budget + subject_budget) // 10, 1)
        if reason_budget >= subject_budget:
            reason_budget = max(reason_budget - step, 0)
        else:
            subject_budget = max(subject_budget - step, 0)
        text = _record_json(
            tool, _truncated(reason, reason_budget), _truncated(subject, subject_budget)
        )
    return text


def _deny(tool, reason, subject):
    output = {
        "hookSpecificOutput": {
            "hookEventName": HOOK_EVENT,
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(output) + "\n")
    # Every denial gets one JSON record on stderr, unconditionally -- no
    # file, nothing that can fail to write. dsh's hook bridge stores this
    # verbatim as `stderrSummary` on the transcript's `hook/result` event
    # (see the module docstring); stderr at exit 0 never changes the
    # decision already written to stdout above.
    print(_denial_record(tool, reason, subject), file=sys.stderr)


def main(argv):
    subject = ""
    tool = ""
    # RT5rb (contract item 1): read and parse the payload fail-closed. stdin is
    # read with a 4 MiB bound, its bracket nesting is pre-scanned (see
    # _max_bracket_nesting) so the JSON decoder is never fed a hostile depth,
    # and json.loads runs inside the BaseException region so RecursionError /
    # MemoryError / ValueError become a deny rather than a traceback. The tool
    # name is not yet known when the payload does not parse, so a parse denial
    # applies to every tool -- an accepted over-denial (see the runbook).
    try:
        raw = sys.stdin.buffer.read(_STDIN_BYTE_BOUND + 1)
        if len(raw) > _STDIN_BYTE_BOUND:
            _deny(tool, "payload could not be parsed: too large", subject)
            return 0
        text = raw.decode("utf-8")
        if _max_bracket_nesting(text) > _MAX_PARSE_NESTING:
            _deny(tool, "payload could not be parsed: too deep", subject)
            return 0
        payload = json.loads(text)
        if not isinstance(payload, dict):
            _deny(tool, "payload could not be parsed: ValueError", subject)
            return 0
    except BaseException as exc:  # noqa: BLE001 -- the contract demands the widest catch so main() returns 0 on every path
        _deny(
            tool,
            f"payload could not be parsed: {type(exc).__name__}",
            subject,
        )
        return 0
    if payload.get("hook_event_name") != HOOK_EVENT:
        return 0
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    # bash/edit/write keep today's coercion of a non-object tool_input to {};
    # the sub-agent tools fail closed on one inside _model_verdict (RT5rb).
    if tool not in _MODEL_TOOLS and not isinstance(tool_input, dict):
        tool_input = {}
    table_path = _routing_table_path(argv)
    # RT5r error contract. `subject` is the audit record's `subject`: for a
    # bash launch it is the command (set below); for the structured model rule
    # it is the offending id (_model_verdict returns it); for a "could not be
    # evaluated" deny of a structured launch there is no single offending id,
    # so it stays "".
    try:
        if tool == "bash":
            command = tool_input.get("command")
            if isinstance(command, str):
                subject = command
                reason = _bash_verdict(command)
                if reason is None:
                    reason = _bash_model_verdict(command, table_path)
                if reason:
                    _deny(tool, reason, command)
        elif tool in ("edit", "write"):
            file_path = tool_input.get("file_path")
            if isinstance(file_path, str):
                project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "") or os.getcwd()
                reason = _edit_verdict(file_path, project_dir)
                if reason:
                    _deny(tool, reason, file_path)
        elif tool in _MODEL_TOOLS:
            result = _model_verdict(tool_input, table_path)
            if result:
                reason, subject = result
                _deny(tool, reason, subject)
        return 0
    except BaseException as exc:  # noqa: BLE001 -- the contract demands the widest catch so main() returns 0 on every path
        # Fail closed: only the model rule can raise here (the bash string-scan
        # and edit/write path checks are pure and cannot), so any exception
        # reaching this point is a model-rule evaluation failure and must DENY,
        # never crash -- a crash is what the harness reads as "allow". This is
        # the guard that also guarantees main() never exits non-zero.
        _deny(
            tool,
            f"model rule could not be evaluated: {type(exc).__name__}",
            subject,
        )
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
