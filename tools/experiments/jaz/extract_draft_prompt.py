#!/usr/bin/env python3
"""tools/experiments/jaz/extract_draft_prompt.py -- derives arm C's task
text from `.claude/workflows/draft-byref.js`'s own `draftPrompt`, rather
than hand-copying it, per the spec's deliverable 6: "generate this text by
a small extractor from draft-byref.js at build time... everything but that
paragraph is byte-identical [to draft-byref.js]." check-armc-prompt.py
(next to this file) is the byte-identity check.

What gets replaced: draft-byref.js's own tool-recipe paragraph (the shell
commands under "Query recipes" plus the "You MAY spawn sub-agents..."
paragraph that hands a sub-question to a fresh agent via a
`${SCRATCH}/q/<n>.md` file) is arm B's mechanism -- shell commands and a
file-handoff for sub-questions. Arm C has neither: the drafter's access to
the tree is the confined_tools.py functions bound as REPL variables, and a
sub-question goes through jaz's own `invoke()` recursion (by reference, in
the REPL, not a file). Only that one paragraph differs; everything else in
draftPrompt -- RULES, the plan-format instructions, the schema description
-- is reused unchanged, so any future edit to draft-byref.js's shared prose
is picked up here automatically (and check-armc-prompt.py fails loudly if
either marker string it anchors on ever moves).

This module resolves draft-byref.js's `prior`/`errata` ternaries down to
their "no prior draft" branch, matching that file's one real call site,
`draftPrompt(null, null)` -- arm C only ever writes one draft, never a
revision round.

The result still carries `${REPO}`, `${SCRATCH}`, `${STORE}` and
`${A.spec}` as literal markers (JS template-literal spelling, kept
on purpose rather than converted to Python str.format placeholders, so a
stray `{`/`}` elsewhere in the prose -- there is none today, but this way
a future one would not need escaping -- can never break the substitution).
`render_arm_c_prompt` below turns them into real strings with plain
`.replace()` calls.
"""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_DRAFT_BYREF_PATH = ".claude/workflows/draft-byref.js"

START_MARKER = "Query recipes — run these yourself, on demand"
END_MARKER = "since there is no persistent REPL here and a subagent receives only the prompt string you give it."

# The exact, fixed substrings draft-byref.js uses for its prior/errata
# ternaries (verified against the live file, 2026-09-27) -- resolved to the
# "no prior draft" branch, arm C's only case.
_TERNARY_SUBS = [
    (
        "${prior ? `; also your prior draft ${prior} and the judges' errata:\\n"
        "${JSON.stringify(errata, null, 1)}` : ''}",
        "",
    ),
    ("${prior ? 'the revised' : 'the'}", "the"),
    ("${prior ? 'next' : '0'}", "0"),
]

CONFINED_TOOLS_PARAGRAPH = (
    "Tool functions bound as REPL variables (not shell commands, not a "
    'packet): read_file(path), list_dir(path="."), grep(pattern, '
    'path="."), tasks_py(*args) (runs `python3 ${REPO}/pkgs/evidence/'
    "tasks.py --root ${REPO} <check|brief|json|waves --repo "
    "nixos-agent-env --json|conflicts>`), duckdb_query(sql) (over the "
    "evidence snapshot at ${REPO}/evidence, as seen inside this basket -- "
    "never /var/lib/evidence, which is not mounted here), git_log(*args) "
    "(`git -C ${REPO} log <args>`, a small read-only flag allowlist -- no "
    "--output/-o), and write_scratch(name, text) (the only write access "
    "you have; confined to ${SCRATCH}, never ${REPO}). Each read-side tool "
    "is confined to ${REPO} -- a path outside it is refused, not served -- "
    "and every call, read or write, appends one line to "
    "${SCRATCH}/queries.log (the tool, its arguments, its exit code); a "
    "Facts line in the plan with no matching entry in that log is a "
    "defect, exactly as for arm B. Write your draft yourself with "
    'write_scratch("draft-0.md", ...) -- your `invoke()` return value is '
    "NOT written to the draft file for you. For a sub-question that would "
    "cost you the same context to chase yourself, call "
    'invoke(ReturnType(str), instructions="<the sub-question>", ...) '
    "directly -- JAZ's own recursion, bounded to depth 2 -- rather than "
    "handing it to a file: its return value is the answer, by reference, "
    "in your own REPL. There is no per-question scratch-file handoff in "
    "this arm."
)


def _extract_template(js_source: str, const_pattern: str) -> str:
    """Return the raw text between the backticks of a `const NAME = \\`...\\`` or
    `function ...() {\\n  return \\`...\\`\\n}` construct, matched by
    `const_pattern` (a regex whose sole capture group is the template body).
    Raises ValueError (never silently returns a wrong slice) if the pattern
    does not match exactly once."""
    matches = re.findall(const_pattern, js_source, re.DOTALL)
    if len(matches) != 1:
        raise ValueError(
            f"extract_draft_prompt: pattern {const_pattern!r} matched {len(matches)} times, expected 1"
        )
    return matches[0]


def extract_rules(js_source: str) -> str:
    return _extract_template(js_source, r"const RULES = `(.*?)`\n")


def extract_draft_prompt_raw(js_source: str) -> str:
    """The raw text draft-byref.js's `draftPrompt` returns, BEFORE the
    prior/errata ternaries are resolved and before `${RULES}` is inlined."""
    return _extract_template(
        js_source, r"function draftPrompt\(prior, errata\) \{\n  return `(.*?)`\n\}"
    )


def resolve_no_prior(text: str) -> str:
    """Resolve the prior/errata ternaries to their no-prior-draft branch."""
    resolved = text
    for needle, replacement in _TERNARY_SUBS:
        if needle not in resolved:
            raise ValueError(
                f"extract_draft_prompt: expected ternary substring not found: {needle!r}"
            )
        resolved = resolved.replace(needle, replacement, 1)
    return resolved


def split_recipe_paragraph(text: str) -> tuple[str, str, str]:
    """Return (before, recipe_paragraph, after), split at START_MARKER /
    END_MARKER. Raises ValueError if either marker is missing (rather than
    silently producing an unchanged or truncated text)."""
    start = text.find(START_MARKER)
    if start == -1:
        raise ValueError(
            f"extract_draft_prompt: START_MARKER not found: {START_MARKER!r}"
        )
    end_marker_pos = text.find(END_MARKER, start)
    if end_marker_pos == -1:
        raise ValueError(
            f"extract_draft_prompt: END_MARKER not found after start: {END_MARKER!r}"
        )
    end = end_marker_pos + len(END_MARKER)
    return text[:start], text[start:end], text[end:]


def build_arm_c_prompt_template(js_source: str) -> str:
    """The whole derivation, from draft-byref.js's source text to arm C's
    task template (still carrying ${REPO}/${SCRATCH}/${STORE}/${A.spec}
    markers -- see render_arm_c_prompt)."""
    rules = extract_rules(js_source)
    raw = extract_draft_prompt_raw(js_source)
    resolved = resolve_no_prior(raw)
    before, _recipe, after = split_recipe_paragraph(resolved)
    merged = before + CONFINED_TOOLS_PARAGRAPH + after
    return merged.replace("${RULES}", rules)


def non_paragraph_text(js_source: str) -> str:
    """draft-byref.js's own draftPrompt, no-prior-resolved, WITHOUT the
    tool-recipe paragraph and WITHOUT ${RULES} inlined -- the slice
    check-armc-prompt.py compares its own generated output against, so the
    comparison is meaningful even though CONFINED_TOOLS_PARAGRAPH itself
    necessarily differs."""
    raw = extract_draft_prompt_raw(js_source)
    resolved = resolve_no_prior(raw)
    before, _recipe, after = split_recipe_paragraph(resolved)
    return before + after


def render_arm_c_prompt(
    template: str, *, repo: str, scratch: str, store: str, spec: str
) -> str:
    """Turn `build_arm_c_prompt_template`'s output into the literal prompt
    text run_arm_c.py hands to `invoke(task=...)`."""
    return (
        template.replace("${REPO}", repo)
        .replace("${SCRATCH}", scratch)
        .replace("${STORE}", store)
        .replace("${A.spec}", spec)
    )


def build_arm_c_prompt(repo_root: str, *, scratch: str, store: str, spec: str) -> str:
    """Convenience: read draft-byref.js under `repo_root`, build the
    template, and render it for one run."""
    js_path = Path(repo_root) / DEFAULT_DRAFT_BYREF_PATH
    js_source = js_path.read_text(encoding="utf-8")
    template = build_arm_c_prompt_template(js_source)
    return render_arm_c_prompt(
        template, repo=repo_root, scratch=scratch, store=store, spec=spec
    )


if __name__ == "__main__":
    import sys

    root = sys.argv[1] if len(sys.argv) > 1 else "."
    print(
        build_arm_c_prompt(
            root, scratch="/tmp/scratch", store="/var/lib/evidence", spec="docs/x.md"
        )
    )
