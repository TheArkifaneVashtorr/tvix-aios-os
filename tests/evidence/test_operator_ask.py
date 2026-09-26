"""The operator-ask writer (plan 2026-09-21-operator-and-collection, OC4).

Two hook payloads (PreToolUse, PostToolUse on AskUserQuestion) and the
orchestrator arm; every test names the one-line mutant that turns it red and
asserts, on the stream's bytes, that no question, option, answer or session id
was written.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve()
PKG = HERE.parents[2] / "pkgs" / "evidence"


def _load(name):
    src = next(
        p
        for p in (PKG / f"{name}.py", pathlib.Path("pkgs/evidence") / f"{name}.py")
        if p.exists()
    )
    if str(src.parent) not in sys.path:
        sys.path.insert(0, str(src.parent))
    spec = importlib.util.spec_from_file_location(name, src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod, src


oa, OASRC = _load("operator_ask")
ev, EVSRC = _load("evidence")

Q = {
    "question": "Which scope?",
    "header": "Scope",
    "options": [
        {"label": "One spec (Recommended)", "description": "both halves"},
        {"label": "Two specs", "description": "one each"},
    ],
    "multiSelect": False,
}
PRE = {
    "session_id": "sess-1",
    "hook_event_name": "PreToolUse",
    "tool_name": "AskUserQuestion",
    "tool_use_id": "toolu_1",
    "tool_input": {"questions": [Q]},
}
POST_ANSWERS = {
    **PRE,
    "hook_event_name": "PostToolUse",
    "tool_response": {"answers": {"Which scope?": "Two specs"}},
}
POST_LIST = {
    **PRE,
    "hook_event_name": "PostToolUse",
    "tool_response": {
        "questions": [{"question": "Which scope?", "answer": "one spec (recommended)"}]
    },
}
POST_OTHER = {
    **PRE,
    "hook_event_name": "PostToolUse",
    "tool_response": {"answers": {"Which scope?": "something typed"}},
}
POST_ODD = {
    **PRE,
    "hook_event_name": "PostToolUse",
    "tool_response": "ok",
}
T0 = dt.datetime(2026, 9, 21, 12, 0, tzinfo=dt.timezone.utc)
SESSION = hashlib.sha256(b"sess-1").hexdigest()[:16]
ASK0 = hashlib.sha256(b"sess-1\x00toolu_1\x000").hexdigest()[:16]


def hook(store, payload, now=T0):
    return oa.main(
        ["--store", str(store), "--hook"],
        stdin=json.dumps(payload) if payload is not None else "",
        now=now,
    )


def rows(store):
    return [r for r in ev.read(str(store), "ledger/operator")]


def raw(store):
    return (pathlib.Path(store) / "ledger" / "operator.jsonl").read_text()


def test_pre_writes_the_ask_row_and_no_text(tmp_path, capsys):
    # mutants: store the label -> the bytes assertion; hash without [:16] ->
    # the validator refuses; drop the recommended scan -> None.
    store = tmp_path / "s"
    assert hook(store, PRE) == 0
    assert capsys.readouterr().out == ""
    (r,) = rows(store)
    assert r["phase"] == "ask" and r["src"] == "hook" and r["surface"] == "chat"
    assert r["session"] == SESSION and r["ask_id"] == ASK0
    assert r["header"] == "Scope" and r["options"] == 2 and r["recommended_index"] == 0
    assert r["chosen_index"] is None and r["latency_s"] is None and r["key"] is None
    text = raw(store)
    for forbidden in (
        "Which scope",
        "Two specs",
        "One spec",
        "sess-1",
        "toolu_1",
        "both halves",
    ):
        assert forbidden not in text


def test_post_writes_the_answer_row_with_latency_and_uptake(tmp_path):
    # mutants: compare descriptions instead of labels -> None; latency from
    # the answer's own ts -> 0; took_recommended when chosen is None -> False.
    store = tmp_path / "s"
    hook(store, PRE, now=T0)
    assert hook(store, POST_ANSWERS, now=T0 + dt.timedelta(seconds=90)) == 0
    ask, ans = rows(store)
    assert ans["phase"] == "answer" and ans["ask_id"] == ask["ask_id"]
    assert ans["chosen_index"] == 1 and ans["took_recommended"] is False
    assert ans["latency_s"] == 90
    store2 = tmp_path / "s2"
    hook(store2, PRE, now=T0)
    hook(store2, POST_LIST, now=T0 + dt.timedelta(seconds=5))
    assert rows(store2)[1]["chosen_index"] == 0
    assert rows(store2)[1]["took_recommended"] is True
    store3 = tmp_path / "s3"
    hook(store3, PRE, now=T0)
    hook(store3, POST_OTHER, now=T0 + dt.timedelta(seconds=5))
    assert rows(store3)[1]["chosen_index"] is None
    assert rows(store3)[1]["took_recommended"] is None
    store4 = tmp_path / "s4"
    hook(store4, PRE, now=T0)
    hook(store4, POST_ODD, now=T0 + dt.timedelta(seconds=5))
    assert rows(store4)[1]["chosen_index"] is None and rows(store4)[1]["latency_s"] == 5
    assert "something typed" not in raw(store3)


def test_answer_without_an_ask_row_has_null_latency(tmp_path):
    # mutant: raise or exit 1 when the ask row is missing -> rc != 0.
    store = tmp_path / "s"
    assert hook(store, POST_ANSWERS) == 0
    (r,) = rows(store)
    assert r["phase"] == "answer" and r["latency_s"] is None and r["chosen_index"] == 1


def test_two_questions_give_two_rows_with_distinct_ids(tmp_path):
    # mutant: drop the index from the hash -> equal ask_ids.
    store = tmp_path / "s"
    q2 = {
        **Q,
        "question": "Which key?",
        "header": "Key",
        "options": [{"label": "A"}, {"label": "B"}, {"label": "C"}],
    }
    assert hook(store, {**PRE, "tool_input": {"questions": [Q, q2]}}) == 0
    a, b = rows(store)
    assert a["ask_id"] != b["ask_id"] and b["options"] == 3
    assert b["recommended_index"] is None


def test_ask_id_is_stable_without_a_tool_use_id(tmp_path):
    # mutant: random or time-based id -> the two runs differ.
    pre = {k: v for k, v in PRE.items() if k != "tool_use_id"}
    hook(tmp_path / "a", pre)
    hook(tmp_path / "b", pre)
    assert rows(tmp_path / "a")[0]["ask_id"] == rows(tmp_path / "b")[0]["ask_id"]
    changed = {**pre, "tool_input": {"questions": [{**Q, "question": "Other?"}]}}
    hook(tmp_path / "c", changed)
    assert rows(tmp_path / "c")[0]["ask_id"] != rows(tmp_path / "a")[0]["ask_id"]


def test_other_payloads_are_skipped_silently(tmp_path, capsys):
    # mutant: exit 1 on empty stdin -> rc 1; write a row for Bash -> one row.
    store = tmp_path / "s"
    for payload, reason in [
        (None, "empty payload"),
        ({**PRE, "tool_name": "Bash"}, "not AskUserQuestion"),
        ({**PRE, "hook_event_name": "Stop"}, "event Stop"),
        ({**PRE, "tool_input": {}}, "no questions"),
    ]:
        assert hook(store, payload) == 0
        err = capsys.readouterr()
        assert err.out == "" and f"skipped: {reason}" in err.err
    assert oa.main(["--store", str(store), "--hook"], stdin="{not json", now=T0) == 0
    assert "skipped: not JSON" in capsys.readouterr().err
    assert rows(store) == []


def test_header_is_truncated_to_twelve(tmp_path):
    # mutant: no truncation -> the validator refuses and rc is 1.
    store = tmp_path / "s"
    long_q = {**Q, "header": "ThirteenChars!"}
    assert hook(store, {**PRE, "tool_input": {"questions": [long_q]}}) == 0
    assert rows(store)[0]["header"] == "ThirteenChar"


def test_orchestrator_arm_copies_the_ask_and_marks_its_source(tmp_path, capsys):
    # mutants: src hook -> the src assertion; no ask row accepted -> rc 0.
    store = tmp_path / "s"
    hook(store, PRE, now=T0)
    rc = oa.main(
        [
            "--store",
            str(store),
            "--phase",
            "answer",
            "--session",
            SESSION,
            "--ask-id",
            ASK0,
            "--chosen",
            "1",
            "--key",
            "OC4",
        ],
        now=T0 + dt.timedelta(seconds=30),
    )
    assert rc == 0
    printed = json.loads(capsys.readouterr().out)
    r = rows(store)[1]
    assert printed["ask_id"] == ASK0
    assert r["src"] == "orchestrator" and r["chosen_index"] == 1
    assert r["header"] == "Scope" and r["options"] == 2
    assert r["took_recommended"] is False
    assert r["latency_s"] == 30 and r["key"] == "OC4"
    rc = oa.main(
        [
            "--store",
            str(store),
            "--phase",
            "answer",
            "--session",
            SESSION,
            "--ask-id",
            "0" * 16,
            "--chosen",
            "other",
        ],
        now=T0,
    )
    assert rc == 1
    assert "no ask row for" in capsys.readouterr().err
    rc = oa.main(
        [
            "--store",
            str(store),
            "--phase",
            "ask",
            "--session",
            SESSION,
            "--ask-id",
            ASK0,
            "--chosen",
            "0",
        ],
        now=T0,
    )
    assert rc == 2


def test_cli_entry_through_evidence_append(tmp_path):
    # mutant: forget the dispatcher's forwarding of --store -> the row lands
    # in the default store (unwritable here) and rc != 0.
    env = dict(os.environ, EVIDENCE_STORE=str(tmp_path / "s"))
    r = subprocess.run(
        [sys.executable, str(EVSRC), "append", "operator", "--hook"],
        input=json.dumps(PRE),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert r.returncode == 0 and r.stdout == ""
    assert len(rows(tmp_path / "s")) == 1
