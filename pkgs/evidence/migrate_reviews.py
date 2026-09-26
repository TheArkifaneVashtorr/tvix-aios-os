"""Review migration (plan 2026-09-06-telemetry-store-1, T3).

``migrate_reviews <repo> [--check]`` walks ``docs/reviews/*opus-review*.md`` in
name order and completes each file's block: a blockless REVIEW_RE H1 gets a
block prepended (``reviewer: opus``, the parsed ``majors``/``minors`` counts and
the two mutation keys only when they parse); an existing block gains its missing
keys just before the closing fence. A legacy H1 (neither ``---`` nor REVIEW_RE)
is left untouched and counted. The script never writes ``plan_defect`` or
``plan_defect_secondary``.
"""

from __future__ import annotations

import argparse
import pathlib
import re

import tasks

# A marker is MAJOR/MINOR at the start of a line (≤3 spaces, an optional list
# decoration, an optional -N / N suffix) and never runs into a following letter
# (so `## Majors` or an inline "six minors" do not count). Case-insensitive: a
# lowercase `major (reject)` is a MAJOR marker.
_MARKER_RE = re.compile(
    r"^\s{0,3}(?:\*+|#+|-|\d+[.)])?\s*(MAJOR|MINOR)"
    r"(?:(?:-\d+)|(?:\s+\d+))?(?![A-Za-z])",
    re.IGNORECASE,
)
# Mutation forms: `12/14 mutants killed` (killed, total) and the fallback
# `12 killed` (killed only).
_MUTATION_RE = re.compile(
    r"(\d+)\s*(?:/|of)\s*(\d+)\s*(?:named\s+)?(?:mutants?\s+)?"
    r"(?:killed|mutants?|mutations)"
)
_FALLBACK_MUTATION_RE = re.compile(r"(\d+)\s+killed")
_NONE_FORMS = ("none", "(none)", "none.")
# A `Major(s)` / `Minor(s)` heading: 1-6 hashes, the word, nothing after it
# (trailing whitespace allowed), case-insensitive (item 5: the corpus's
# `### Minors` is a heading too, and the word may be capitalised).
_HEADING_RE = re.compile(r"^#{1,6}\s+(major|majors|minor|minors)\s*$", re.IGNORECASE)


def _marker_counts(lines):
    majors = minors = 0
    for ln in lines:
        m = _MARKER_RE.match(ln)
        if m is None:
            continue
        if m.group(1).upper() == "MAJOR":
            majors += 1
        else:
            minors += 1
    return majors, minors


def _class_count(lines, count, cls):
    """The majors (or minors) count: the marker count, else 0 when a
    `#..## Major(s)` / `#..## Minor(s)` heading (1-6 hashes, case-insensitive)
    is followed (within two lines) by `none`, else None."""
    if count > 0:
        return count
    want = ("major", "majors") if cls == "major" else ("minor", "minors")
    for i, ln in enumerate(lines):
        m = _HEADING_RE.match(ln)
        if m is None or m.group(1).lower() not in want:
            continue
        for nxt in lines[i + 1 : i + 3]:
            if nxt.strip().lower() in _NONE_FORMS:
                return 0
        return None
    return None


def _mutation(text):
    m = _MUTATION_RE.search(text)
    if m is not None:
        return int(m.group(1)), int(m.group(2))
    m = _FALLBACK_MUTATION_RE.search(text)
    if m is not None:
        return int(m.group(1)), None
    return None, None


def _fmt(value):
    return "null" if value is None else str(value)


def _prepend_block(text):
    """A blockless REVIEW_RE H1 becomes a block + the original text verbatim."""
    lines = text.splitlines()
    majors, minors = _marker_counts(lines)
    killed, total = _mutation(text)
    additions = ["reviewer: opus"]
    additions.append(f"majors: {_fmt(_class_count(lines, majors, 'major'))}")
    additions.append(f"minors: {_fmt(_class_count(lines, minors, 'minor'))}")
    if total is not None:
        additions.append(f"mutants_total: {total}")
    if killed is not None:
        additions.append(f"mutants_killed: {killed}")
    return "---\n" + "\n".join(additions) + "\n---\n" + text


def _line_offset(text, index):
    """The byte offset where ``text.splitlines()[index]`` begins."""
    pos = 0
    for _ in range(index):
        nl = text.find("\n", pos)
        if nl == -1:
            return len(text)
        pos = nl + 1
    return pos


def _migrate_block(text):
    """Append the missing keys of an existing block before its closing fence."""
    lines = text.splitlines()
    close = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close = i
            break
    if close is None:
        return text, "legacy", 0
    block_keys = {}
    for ln in lines[1:close]:
        if ":" in ln:
            key, _, value = ln.partition(":")
            block_keys[key.strip()] = value.strip()
    body_lines = lines[close + 1 :]
    majors, minors = _marker_counts(body_lines)
    killed, total = _mutation("\n".join(body_lines))
    additions = []
    if "reviewer" not in block_keys:
        additions.append("reviewer: opus")
    if "majors" not in block_keys:
        additions.append(f"majors: {_fmt(_class_count(body_lines, majors, 'major'))}")
    if "minors" not in block_keys:
        additions.append(f"minors: {_fmt(_class_count(body_lines, minors, 'minor'))}")
    if "mutants_total" not in block_keys and total is not None:
        additions.append(f"mutants_total: {total}")
    if "mutants_killed" not in block_keys and killed is not None:
        additions.append(f"mutants_killed: {killed}")
    if not additions:
        return text, "unchanged", 0
    # Splice the additions into the original string just before the closing
    # fence line: every byte after the fence (the body and its trailing
    # newline) is returned unchanged, and a file without one stays without one.
    fence = _line_offset(text, close)
    return (
        text[:fence] + "\n".join(additions) + "\n" + text[fence:],
        "keys",
        len(additions),
    )


def migrate_file(text):
    """``(new_text, action, keys_added)``; action is one of block|keys|unchanged|legacy."""
    if not text:
        return text, "legacy", 0
    first = text.splitlines()[0].strip()
    if first == "---":
        return _migrate_block(text)
    if tasks.REVIEW_RE.match(text.splitlines()[0]) is not None:
        new_text = _prepend_block(text)
        return new_text, "block", 0
    return text, "legacy", 0


def _walk(repo):
    reviews_dir = pathlib.Path(repo) / "docs" / "reviews"
    if not reviews_dir.is_dir():
        return []
    return sorted(reviews_dir.glob("*opus-review*.md"))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="migrate_reviews")
    parser.add_argument("repo")
    parser.add_argument(
        "--check", action="store_true", help="report what would change without writing"
    )
    args = parser.parse_args(argv)

    would_change = []
    total = blocks = keys = unchanged = legacy = 0
    for path in _walk(args.repo):
        text = path.read_text()
        new_text, action, added = migrate_file(text)
        total += 1
        if action == "block":
            blocks += 1
            would_change.append(path)
        elif action == "keys":
            keys += added
            would_change.append(path)
        elif action == "legacy":
            legacy += 1
        else:
            unchanged += 1
        if not args.check and action in ("block", "keys"):
            path.write_text(new_text)

    if args.check:
        for path in would_change:
            rel = path.relative_to(pathlib.Path(args.repo)).as_posix()
            print(f"would change: {rel}")
        print(f"checked: {total}; would change: {len(would_change)}")
        return 1 if would_change else 0
    print(
        f"migrated: blocks added {blocks}, keys added {keys}, "
        f"unchanged {unchanged}, skipped legacy {legacy}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
