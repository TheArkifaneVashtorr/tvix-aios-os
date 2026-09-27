#!/usr/bin/env python3
"""check-truncation.py -- proof that .claude/workflows/draft-packet.js and
draft-byref.js are byte-identical truncations of plan.js and plan-byref.js
on the constructs they share (RULES, the reader prompts, the JSON schemas,
the drafter prompt), per docs/superpowers/specs/
2026-09-25-jaz-planning-experiment-design.md §6a "Revision 2": "Both are
derived by truncation into two new workflow scripts, so plan.js and
plan-byref.js stay untouched."

Extracts each named construct with a JS-string/template-literal-aware
bracket matcher (never a naive whole-file regex or diff, which a brace
inside a template literal's ${...} interpolation -- READERS' prompts are
full of them -- would desync) and asserts the extracted text is identical,
byte for byte, between:
  .claude/workflows/plan.js        <-> .claude/workflows/draft-packet.js
      (RULES, PACKET_SCHEMA, DRAFT_SCHEMA, READERS,
       functions draftPrompt, refuseDroppedHeadings)
  .claude/workflows/plan-byref.js  <-> .claude/workflows/draft-byref.js
      (RULES, DRAFT_SCHEMA, function draftPrompt)

A construct absent from BOTH files of a pair is not a failure (plan-byref.js
and draft-byref.js have no packet phase, so PACKET_SCHEMA/READERS never
exist there, and neither defines refuseDroppedHeadings -- arm B has no
replan mode) -- only "present in one, missing or different in the other"
fails. Constructs that belong only to the Judge/Revise/Ship phases (CRITERIA,
FLOOR_ROWS, RECORD_FIELDS, SCORE_SCHEMA, LENSES, judgePrompt, tally) are
checked for absence from the two truncated files: a byte-identical Draft
phase this script proves nothing about a script that quietly kept the judge
panel's machinery too.

Two coverage gaps in an earlier version (Opus review, 2026-09-26): a mutant
inside the CONTROL FLOW around the shared constructs (e.g. the Packet
reader's own `model: 'sonnet'`, which lives in the agent() call wrapping
READERS, not in READERS itself; or the soundness gate `if (mech.checkEmpty
!== true)`) passed silently, because nothing walked that code. And a mutant
to a HEADER CONST's default (e.g. STORE's `/var/lib/evidence`) passed
silently too, because nothing read those lines at all. Both are covered now:
- normalize_control_flow_block() slices the literal Packet+Draft (arm A) or
  Draft-only (arm B) control flow -- from `phase('Packet')`/`phase('Draft')`
  through the draft phase's closing `log(...operator questions`)` line --
  dedents plan.js's `if (!A.judgeOnly) { ... }` wrapper (draft-packet.js has
  no such wrapper), drops every `budget.spent()` line (per-phase token
  bookkeeping that exists on one side or both but is not part of the
  compared behaviour) and plan.js's post-draft `draft =`/`questions =`/
  `selfScore =` assignment lines (draft-packet.js inlines `d.path` instead),
  and normalizes every `'plan: '`/`'plan-byref: '`/`'draft-packet: '`/
  `'draft-byref: '` error-message prefix to `'X: '` (an arm-specific prefix
  is expected, not a divergence) -- then diffs the two normalized line
  lists.
- HEADER_CONST_NAMES asserts the `const A|REPO|SCRATCH|SINCE|STORE|REPLAN =`
  lines are byte-identical (as a set, so an arg a source file omits raises
  no false failure) between each pair.

Usage: check-truncation.py [--root ROOT]
  ROOT   repo root holding .claude/workflows/{plan,plan-byref,draft-packet,
         draft-byref}.js; default: two directories up from this script's own
         location (tools/experiments/jaz/check-truncation.py -> repo root).

Exit 0: every shared construct in both pairs is byte-identical, and no
        Judge/Revise/Ship-only name leaked into the truncated pair.
Exit 1: at least one construct differs, is missing, or a Judge-only name
        survived truncation.
Exit 2: usage error (a required file is missing).
"""

import argparse
import difflib
import re
import sys
from pathlib import Path


def consume_string(s, i):
    """s[i] is a ' or " -- return the index just past the matching close."""
    quote = s[i]
    i += 1
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            return i + 1
        i += 1
    raise ValueError(f"unterminated string starting near offset {i}")


def consume_balanced(s, i):
    """s[i] is one of '{[(`' -- return the index just past its match.

    A minimal JS-syntax-aware scanner: treats single/double-quoted strings
    and backtick template literals as opaque except for a template's
    ${...} interpolations, which re-enter code mode (so a literal '{' or
    '}' inside prompt TEXT is never mistaken for a code brace, while a
    real one inside an interpolated expression still balances correctly).
    Line comments (//) are skipped outside of strings/templates.
    """
    open_ch = s[i]
    closers = {"{": "}", "[": "]", "(": ")", "`": "`"}
    close_ch = closers[open_ch]
    n = len(s)
    if open_ch == "`":
        i += 1
        while i < n:
            c = s[i]
            if c == "\\":
                i += 2
                continue
            if c == "`":
                return i + 1
            if c == "$" and s[i + 1 : i + 2] == "{":
                i = consume_balanced(s, i + 1)
                continue
            i += 1
        raise ValueError("unterminated template literal")
    else:
        i += 1
        while i < n:
            c = s[i]
            if c in "\"'":
                i = consume_string(s, i)
                continue
            if c == "`":
                i = consume_balanced(s, i)
                continue
            if c == "/" and s[i + 1 : i + 2] == "/":
                nl = s.find("\n", i)
                i = n if nl == -1 else nl + 1
                continue
            if c in "{[(":
                i = consume_balanced(s, i)
                continue
            if c == close_ch:
                return i + 1
            i += 1
        raise ValueError(f"unterminated {open_ch!r} starting near offset {i}")


def extract_const(text, name):
    """Return the value text of a top-level `const NAME = <value>`
    (the value only, trimmed of nothing -- byte-exact), or None if the
    file has no such declaration."""
    m = re.search(rf"(?m)^const {re.escape(name)} = ", text)
    if not m:
        return None
    i = m.end()
    while text[i] in " \t":
        i += 1
    if text[i] not in "{[`":
        raise ValueError(f"const {name}: unsupported value start {text[i]!r}")
    end = consume_balanced(text, i)
    return text[i:end]


def extract_function(text, name):
    """Return the full `function NAME(...) { ... }` text (signature and
    body), or None if the file has no such top-level function."""
    m = re.search(rf"(?m)^function {re.escape(name)}\(", text)
    if not m:
        return None
    start = m.start()
    paren = m.end() - 1
    after_params = consume_balanced(text, paren)
    i = after_params
    while text[i] in " \t\n":
        i += 1
    if text[i] != "{":
        raise ValueError(f"function {name}: expected '{{' after the parameter list")
    end = consume_balanced(text, i)
    return text[start:end]


def normalize_control_flow_block(text, start, end, dedent):
    """Return the lines of text[start..end] (end included), normalized so
    the two arms' control flow compares like for like:
    - dedent: strip one leading 2-space indent from every line (plan.js's
      Packet+Draft body sits inside `if (!A.judgeOnly) { ... }`; the
      truncated file has no such wrapper, so its lines are already flat).
    - every `'plan: '`/`'plan-byref: '`/`'draft-packet: '`/`'draft-byref: '`
      error-message prefix is rewritten to `'X: '` -- an arm-specific
      prefix is expected, not a divergence.
    - lines that only exist because of the wrapper or the per-phase token
      bookkeeping (CONTROL_FLOW_DROP) are dropped from both sides equally.
    Raises ValueError if either marker is not found (a genuine structural
    difference the caller should report, not silently skip).
    """
    i = text.index(start)
    j = text.index(end, i) + len(end)
    out = []
    for ln in text[i:j].splitlines():
        s = ln[2:] if dedent and ln.startswith("  ") else ln
        s = ERROR_PREFIX.sub("'X: ", s)
        if CONTROL_FLOW_DROP.search(s.strip()):
            continue
        out.append(s.rstrip())
    return out


# The constructs a truncated Draft-only script must carry byte-identical
# from its source, when the source has them at all.
CONST_NAMES = ["RULES", "PACKET_SCHEMA", "DRAFT_SCHEMA", "READERS"]
FUNCTION_NAMES = ["draftPrompt", "refuseDroppedHeadings"]

# Lines a truncated script must carry byte-identical too, even though they
# are single-line arg defaults rather than a bracket-balanced construct
# (STORE's default `/var/lib/evidence` has no other check watching it).
HEADER_CONST_NAMES = ["A", "REPO", "SCRATCH", "SINCE", "STORE", "REPLAN"]
HEADER_CONST_RE = re.compile(
    rf"^const ({'|'.join(HEADER_CONST_NAMES)}) = .*$", re.MULTILINE
)

# The literal control-flow slice each pair shares: arm A's spans Packet
# through the Draft phase's own log line; arm B has no Packet phase, so its
# slice starts at Draft directly. Both end at the same log() call text,
# which is byte-identical across all four files.
CONTROL_FLOW_END = "operator questions`)"
CONTROL_FLOW_START = {"arm A": "phase('Packet')", "arm B": "phase('Draft')"}

CONTROL_FLOW_DROP = re.compile(
    r"budget\.spent\(\)|^(draft|questions|selfScore) = d0?\.|^if \(!A\.judgeOnly\) \{$|^\}$"
)
ERROR_PREFIX = re.compile(r"'(plan|plan-byref|draft-packet|draft-byref): ")

# Names that belong only to the Judge/Revise/Ship phases (plan.js and
# plan-byref.js both define all of these): a truncated Draft-only script
# must never carry them, since the spec's truncation removes Judge, Revise
# and Ship "and everything only they use".
JUDGE_ONLY_NAMES = [
    "CRITERIA",
    "FLOOR_ROWS",
    "RECORD_FIELDS",
    "SCORE_SCHEMA",
    "LENSES",
    "judgePrompt",
    "tally",
]


def compare_pair(label, full_path, truncated_path):
    full = full_path.read_text(encoding="utf-8")
    trunc = truncated_path.read_text(encoding="utf-8")
    ok = True
    checked = []

    for name in CONST_NAMES:
        a = extract_const(full, name)
        if a is None:
            continue  # this pair's source never had it (e.g. no PACKET_SCHEMA in plan-byref.js)
        b = extract_const(trunc, name)
        checked.append(name)
        if b is None:
            print(
                f"FAIL {label}: const {name} is in {full_path.name} but missing from {truncated_path.name}"
            )
            ok = False
        elif a != b:
            print(
                f"FAIL {label}: const {name} differs between {full_path.name} and {truncated_path.name}"
            )
            ok = False

    for name in FUNCTION_NAMES:
        a = extract_function(full, name)
        if a is None:
            continue
        b = extract_function(trunc, name)
        checked.append(f"function {name}")
        if b is None:
            print(
                f"FAIL {label}: function {name} is in {full_path.name} but missing from {truncated_path.name}"
            )
            ok = False
        # the error-message prefix ('plan: ' vs 'draft-packet: ', etc.) is
        # expected to differ by arm -- normalize it before comparing, same
        # as the control-flow block below.
        elif ERROR_PREFIX.sub("'X: ", a) != ERROR_PREFIX.sub("'X: ", b):
            print(
                f"FAIL {label}: function {name} differs between {full_path.name} and {truncated_path.name}"
            )
            ok = False

    arm = "arm A" if label.startswith("arm A") else "arm B"
    cf_start = CONTROL_FLOW_START[arm]
    dedent = (
        arm == "arm A"
    )  # only plan.js wraps Packet+Draft in `if (!A.judgeOnly) { ... }`
    try:
        cf_a = normalize_control_flow_block(full, cf_start, CONTROL_FLOW_END, dedent)
        cf_b = normalize_control_flow_block(trunc, cf_start, CONTROL_FLOW_END, False)
    except ValueError as e:
        print(
            f"FAIL {label}: control flow ({full_path.name} vs {truncated_path.name}): {e}"
        )
        ok = False
    else:
        checked.append("control flow")
        if cf_a != cf_b:
            print(
                f"FAIL {label}: control flow differs between {full_path.name} and {truncated_path.name}:"
            )
            for dl in difflib.unified_diff(
                cf_a, cf_b, full_path.name, truncated_path.name, lineterm=""
            ):
                print(f"  {dl}")
            ok = False

    a_header = {m.group(0) for m in HEADER_CONST_RE.finditer(full)}
    b_header = {m.group(0) for m in HEADER_CONST_RE.finditer(trunc)}
    only_full = sorted(a_header - b_header)
    only_trunc = sorted(b_header - a_header)
    checked.append("header consts")
    if only_full or only_trunc:
        print(
            f"FAIL {label}: header consts differ -- only in {full_path.name}: {only_full}; only in {truncated_path.name}: {only_trunc}"
        )
        ok = False

    for name in JUDGE_ONLY_NAMES:
        if (
            extract_const(trunc, name) is not None
            or extract_function(trunc, name) is not None
        ):
            print(
                f"FAIL {label}: Judge/Revise/Ship-only name {name} survives in {truncated_path.name}"
            )
            ok = False
        elif re.search(rf"\b{re.escape(name)}\b", trunc):
            print(
                f"FAIL {label}: Judge/Revise/Ship-only name {name} is referenced in {truncated_path.name}"
            )
            ok = False

    if ok:
        print(
            f"PASS {label}: {', '.join(checked)} byte-identical; no Judge-only name present"
        )
    return ok


def main(argv):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    default_root = Path(__file__).resolve().parents[3]
    ap.add_argument(
        "--root",
        type=Path,
        default=default_root,
        help="repo root (default: %(default)s)",
    )
    args = ap.parse_args(argv)

    wf = args.root / ".claude" / "workflows"
    pairs = [
        ("arm A (plan.js -> draft-packet.js)", wf / "plan.js", wf / "draft-packet.js"),
        (
            "arm B (plan-byref.js -> draft-byref.js)",
            wf / "plan-byref.js",
            wf / "draft-byref.js",
        ),
    ]

    missing = [p for _, a, b in pairs for p in (a, b) if not p.is_file()]
    if missing:
        for p in missing:
            print(f"check-truncation: missing file: {p}", file=sys.stderr)
        return 2

    ok = True
    for label, full_path, truncated_path in pairs:
        try:
            if not compare_pair(label, full_path, truncated_path):
                ok = False
        except ValueError as e:
            print(f"FAIL {label}: {e}", file=sys.stderr)
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
