#!/usr/bin/env python3
"""tools/experiments/jaz/check-armc-prompt.py -- proves
extract_draft_prompt.py's arm-C task template differs from
`.claude/workflows/draft-byref.js`'s own `draftPrompt` ONLY in the one
tool-recipe paragraph the spec names (deliverable 6: "add a check... that
everything but that paragraph is byte-identical").

2026-09-27 Opus review fix: the first cut compared `non_paragraph_text()`
-- draftPrompt's "before"/"after" text with the literal, UNEXPANDED
`${RULES}` marker still in it, never RULES' own real text. A mutation to
RULES itself (a real, separately-extracted template) therefore never
showed up in that comparison at all, and neither did a bug in the
RULES-inlining step. This check now compares the FULL template
`extract_draft_prompt.build_arm_c_prompt_template()` actually produces
(RULES inlined, exactly what run_arm_c.py hands to `invoke()`), with the
CONFINED_TOOLS_PARAGRAPH sliced back out, against an INDEPENDENTLY
rebuilt "expected" text (this file's own regex/ternary-resolution/
RULES-inlining/marker-split, not reusing extract_draft_prompt.py's) --
so a bug in either the RULES-inlining or the paragraph-splitting has an
independent computation to disagree with, the same shape of guarantee
check-truncation.py gives arms A and B.

Usage: check-armc-prompt.py --root <repo>   (exit 0 PASS / 1 FAIL / 2 usage)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_draft_prompt as edp  # noqa: E402

DRAFT_BYREF_RELPATH = ".claude/workflows/draft-byref.js"

# Independent copies of the two literal markers -- typed here separately
# from extract_draft_prompt.py's module constants, on purpose. If either
# file's copy of a marker ever drifts from draft-byref.js's real text,
# BOTH this check and extract_draft_prompt.py's own split will raise
# ValueError (missing marker), which is exactly the loud failure wanted.
_START = "Query recipes — run these yourself, on demand"
_END = "since there is no persistent REPL here and a subagent receives only the prompt string you give it."

_TERNARIES = [
    (
        "${prior ? `; also your prior draft ${prior} and the judges' errata:\\n"
        "${JSON.stringify(errata, null, 1)}` : ''}",
        "",
    ),
    ("${prior ? 'the revised' : 'the'}", "the"),
    ("${prior ? 'next' : '0'}", "0"),
]


def independent_full_text_minus_paragraph(js_source: str) -> str:
    """Rebuild draftPrompt's full, RULES-inlined text (no-prior-resolved),
    then strip the tool-recipe paragraph out of it -- entirely independent
    of extract_draft_prompt.py's own regex/split functions."""
    rules_matches = re.findall(r"const RULES = `(.*?)`\n", js_source, re.DOTALL)
    if len(rules_matches) != 1:
        raise ValueError(
            f"check-armc-prompt: RULES matched {len(rules_matches)} times, expected 1"
        )
    rules = rules_matches[0]

    prompt_matches = re.findall(
        r"function draftPrompt\(prior, errata\) \{\n  return `(.*?)`\n\}",
        js_source,
        re.DOTALL,
    )
    if len(prompt_matches) != 1:
        raise ValueError(
            f"check-armc-prompt: draftPrompt template matched {len(prompt_matches)} times, expected 1"
        )
    text = prompt_matches[0]

    for needle, replacement in _TERNARIES:
        if needle not in text:
            raise ValueError(
                f"check-armc-prompt: expected ternary substring not found: {needle!r}"
            )
        text = text.replace(needle, replacement, 1)

    text = text.replace("${RULES}", rules)

    start = text.find(_START)
    if start == -1:
        raise ValueError(f"check-armc-prompt: START marker not found: {_START!r}")
    end_pos = text.find(_END, start)
    if end_pos == -1:
        raise ValueError(
            f"check-armc-prompt: END marker not found after start: {_END!r}"
        )
    end = end_pos + len(_END)
    return text[:start] + text[end:]


def actual_full_text_minus_paragraph(js_source: str) -> str:
    """extract_draft_prompt.py's real, RULES-inlined output (what
    run_arm_c.py actually renders) with CONFINED_TOOLS_PARAGRAPH sliced
    back out, located by its own exact text -- so this check exercises
    the REAL inlining/splitting code, not a second copy of it."""
    full = edp.build_arm_c_prompt_template(js_source)
    if edp.CONFINED_TOOLS_PARAGRAPH not in full:
        raise ValueError(
            "check-armc-prompt: CONFINED_TOOLS_PARAGRAPH is missing from the generated template"
        )
    before, after = full.split(edp.CONFINED_TOOLS_PARAGRAPH, 1)
    return before + after


def run(root: str) -> int:
    js_path = Path(root) / DRAFT_BYREF_RELPATH
    if not js_path.exists():
        print(f"FAIL: missing file {js_path}")
        return 2
    js_source = js_path.read_text(encoding="utf-8")

    try:
        expected = independent_full_text_minus_paragraph(js_source)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1

    try:
        actual = actual_full_text_minus_paragraph(js_source)
    except ValueError as exc:
        print(f"FAIL: {exc}")
        return 1

    if expected != actual:
        print(
            "FAIL: full (RULES-inlined) non-paragraph text differs between the independent check and extract_draft_prompt.py"
        )
        _print_diff(expected, actual)
        return 1

    try:
        rendered_template = edp.build_arm_c_prompt_template(js_source)
    except ValueError as exc:
        print(f"FAIL: extract_draft_prompt.build_arm_c_prompt_template raised: {exc}")
        return 1

    if "q/<n>.md" in rendered_template or _START in rendered_template:
        print(
            "FAIL: arm B's tool-recipe paragraph (or its q/<n>.md handoff) survived into the arm-C template"
        )
        return 1

    print(
        "PASS arm C (draft-byref.js -> extract_draft_prompt.py): full RULES-inlined non-paragraph text byte-identical"
    )
    return 0


def _print_diff(expected: str, actual: str) -> None:
    import difflib

    diff = difflib.unified_diff(expected.splitlines(), actual.splitlines(), lineterm="")
    for line in list(diff)[:80]:
        print(line)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args(argv)
    return run(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
