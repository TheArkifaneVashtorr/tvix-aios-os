#!/usr/bin/env python3
"""scrub_review.py <input> <output> -- replace a captured-secret review body
with a minimal stub that keeps only what tasks.py's `check` reads from a
review file: the front-matter block (plan_defect etc.) and the H1 verdict
line (`# Opus gate — seat run <run>, task <key> — APPROVED|REJECTED`,
tasks.py's REVIEW_RE). Everything else -- the body, where a captured secret
lives -- is replaced with one redaction line.

Rationale (measured on the JAZ fixture branches): a task whose ONLY landing
evidence in a git-less archived tree is its own review file's H1 verdict
loses that evidence on a flat `rm`, which flips tasks.py's cross-area
"touches span areas ... without an areas: declaration" rule from silent to
red for that key (state falls back to "ready"). The front matter and verdict
line carry no secret and were never the redaction target; scrubbing instead
of deleting keeps `check` green without restoring the leaked text.

Exit 1 (and prints why) if the file doesn't have the expected shape, so the
caller falls back to a full delete rather than guess.
"""

import re
import sys

REVIEW_RE = re.compile(
    r"^# Opus gate — seat run \S+, task \S+ — (APPROVED|REJECTED)\s*$"
)

src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as f:
    text = f.read()
lines = text.splitlines()

if not lines or lines[0].strip() != "---":
    print(f"scrub_review: {src}: no front-matter block", file=sys.stderr)
    sys.exit(1)
try:
    end = lines.index("---", 1)
except ValueError:
    print(f"scrub_review: {src}: unterminated front-matter block", file=sys.stderr)
    sys.exit(1)
front_matter = lines[: end + 1]

h1 = None
for ln in lines[end + 1 :]:
    if REVIEW_RE.match(ln):
        h1 = ln
        break
if h1 is None:
    print(f"scrub_review: {src}: no H1 verdict line found", file=sys.stderr)
    sys.exit(1)

stub = (
    "\n".join(front_matter)
    + "\n"
    + h1
    + "\n\n"
    + "[body redacted: contained a credential]\n"
)
with open(dst, "w", encoding="utf-8") as f:
    f.write(stub)
