"""operator_ask — the ledger/operator writer (plan 2026-09-21-operator-and-collection, OC4).

Hook mode reads one AskUserQuestion hook payload on stdin and writes one row
per question: the ask row at PreToolUse, the answer row at PostToolUse. The
orchestrator mode writes an answer row by hand. Nothing textual is stored:
ids are hashed, options counted, labels reduced to an index, the chip capped
at twelve characters by the schema (streams.py). Stdout is empty in hook mode.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

import evidence
import streams

ASK_RE = re.compile(r"^[0-9a-f]{16}$")
RECOMMENDED = "(recommended)"
STREAM = "ledger/operator"


def _h16(*parts):
    return hashlib.sha256("\x00".join(parts).encode()).hexdigest()[:16]


def _now_iso(now):
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(ts):
    return datetime.datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(
        tzinfo=datetime.timezone.utc
    )


def _recommended(options):
    for i, opt in enumerate(options):
        if isinstance(opt, dict) and RECOMMENDED in str(opt.get("label", "")).lower():
            return i
    return None


def _chosen_label(response, question, index):
    """The chosen label for question `index`, or None (Other, or no answer)."""
    if not isinstance(response, dict):
        return None
    answers = response.get("answers")
    if isinstance(answers, dict):
        value = answers.get(str(question.get("question", "")))
    else:
        items = response.get("questions")
        value = None
        if (
            isinstance(items, list)
            and index < len(items)
            and isinstance(items[index], dict)
        ):
            for name in ("answer", "selected", "chosen"):
                if items[index].get(name) is not None:
                    value = items[index][name]
                    break
    if isinstance(value, list):
        value = value[0] if value else None
    return value if isinstance(value, str) else None


def _chosen_index(label, options):
    if label is None:
        return None
    labels = [str(o.get("label", "")) if isinstance(o, dict) else "" for o in options]
    if label in labels:
        return labels.index(label)
    folded = [x.strip().lower() for x in labels]
    key = label.strip().lower()
    return folded.index(key) if key in folded else None


def _ask_row(store, session, ask_id):
    found = None
    for r in evidence.read(store, STREAM):
        if (
            r.get("kind") == "operator-ask"
            and r.get("phase") == "ask"
            and r.get("session") == session
            and r.get("ask_id") == ask_id
        ):
            found = r
    return found


def _base(session, ask_id, phase, header, options, recommended, src):
    return {
        "kind": "operator-ask",
        "session": session,
        "ask_id": ask_id,
        "phase": phase,
        "header": str(header)[:12],
        "options": int(options),
        "recommended_index": recommended,
        "chosen_index": None,
        "took_recommended": None,
        "latency_s": None,
        "key": None,
        "surface": "chat",
        "src": src,
    }


def _finish_answer(store, row, chosen, now):
    row["chosen_index"] = chosen
    rec = row["recommended_index"]
    row["took_recommended"] = (
        (chosen == rec) if (chosen is not None and rec is not None) else None
    )
    ask = _ask_row(store, row["session"], row["ask_id"])
    if ask is not None:
        row["latency_s"] = max(0, int((now - _parse_ts(ask["ts"])).total_seconds()))
    return row


def _write(store, row, now):
    errors = streams.validate("operator-ask", row)
    if errors:
        for e in errors:
            print(f"evidence: append operator: refused: {e}", file=sys.stderr)
        return 1
    evidence.append(store, STREAM, row, ts=_now_iso(now))
    return 0


def _skip(reason):
    print(f"evidence: append operator: skipped: {reason}", file=sys.stderr)
    return 0


def hook_mode(store, stdin, now):
    if not stdin.strip():
        return _skip("empty payload")
    try:
        payload = json.loads(stdin)
    except ValueError:
        return _skip("not JSON")
    if not isinstance(payload, dict) or payload.get("tool_name") != "AskUserQuestion":
        return _skip("not AskUserQuestion")
    event = payload.get("hook_event_name")
    if event not in ("PreToolUse", "PostToolUse"):
        return _skip(f"event {event}")
    tool_input = payload.get("tool_input")
    questions = tool_input.get("questions") if isinstance(tool_input, dict) else None
    if not isinstance(questions, list) or not questions:
        return _skip("no questions")
    session_id = str(payload.get("session_id", ""))
    session = _h16(session_id)
    tool_use_id = payload.get("tool_use_id")
    phase = "ask" if event == "PreToolUse" else "answer"
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue
        if isinstance(tool_use_id, str) and tool_use_id:
            ask_id = _h16(session_id, tool_use_id, str(i))
        else:
            ask_id = _h16(session_id, json.dumps(q, sort_keys=True), str(i))
        options = q.get("options") if isinstance(q.get("options"), list) else []
        row = _base(
            session,
            ask_id,
            phase,
            q.get("header", ""),
            len(options),
            _recommended(options),
            "hook",
        )
        if phase == "answer":
            _finish_answer(
                store,
                row,
                _chosen_index(
                    _chosen_label(payload.get("tool_response"), q, i), options
                ),
                now,
            )
        rc = _write(store, row, now)
        if rc:
            return rc
    return 0


def orchestrator_mode(store, args, now):
    if args.phase != "answer":
        print("evidence: append operator: ask rows come from the hook", file=sys.stderr)
        return 2
    ask = _ask_row(store, args.session, args.ask_id)
    if ask is None:
        print(
            f"evidence: append operator: no ask row for {args.session}/{args.ask_id}",
            file=sys.stderr,
        )
        return 1
    row = _base(
        args.session,
        args.ask_id,
        "answer",
        ask["header"],
        ask["options"],
        ask.get("recommended_index"),
        "orchestrator",
    )
    row["key"] = args.key
    row["surface"] = args.surface
    chosen = None if args.chosen == "other" else int(args.chosen)
    _finish_answer(store, row, chosen, now)
    rc = _write(store, row, now)
    if rc == 0:
        print(json.dumps(row, sort_keys=True))
    return rc


def main(argv=None, stdin=None, now=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = argparse.ArgumentParser(prog="evidence append operator")
    parser.add_argument(
        "--store", default=os.environ.get("EVIDENCE_STORE") or evidence.DEFAULT_STORE
    )
    parser.add_argument("target", nargs="?", choices=("operator",))
    parser.add_argument("--hook", action="store_true")
    parser.add_argument("--phase", choices=("ask", "answer"))
    parser.add_argument("--session")
    parser.add_argument("--ask-id", dest="ask_id")
    parser.add_argument("--chosen")
    parser.add_argument("--key", default=None)
    parser.add_argument(
        "--surface", choices=("chat", "run-button", "helm"), default="chat"
    )
    args = parser.parse_args(argv)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if args.hook:
        if args.phase or args.session or args.ask_id or args.chosen:
            parser.error("--hook takes no other argument")
        return hook_mode(args.store, sys.stdin.read() if stdin is None else stdin, now)
    for name, value in (
        ("--phase", args.phase),
        ("--session", args.session),
        ("--ask-id", args.ask_id),
        ("--chosen", args.chosen),
    ):
        if value is None:
            parser.error(f"{name} is required without --hook")
    if not ASK_RE.fullmatch(args.session) or not ASK_RE.fullmatch(args.ask_id):
        parser.error("--session and --ask-id are 16 hex characters")
    if args.chosen != "other" and not args.chosen.isdigit():
        parser.error("--chosen is an option index or 'other'")
    return orchestrator_mode(args.store, args, now)


if __name__ == "__main__":
    raise SystemExit(main())
