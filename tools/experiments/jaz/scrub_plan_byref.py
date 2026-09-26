#!/usr/bin/env python3
"""scrub_plan_byref.py <input> <output> -- write a fixture copy of
plan-byref.js with every trace of the experiment's own name/spec path
removed from comments and meta strings, so a by-reference drafter browsing
the fixture tree cannot read "this is a JAZ experiment arm being measured"
off the workflow file it is about to run.

What it does, in order:
1. Drops the leading `//`-only header comment block, replacing it with one
   neutral line.
2. Replaces `meta.description` and `meta.whenToUse` (single-quoted string
   literals) with neutral text.
3. Drops any OTHER whole-line `//` comment anywhere in the file that still
   names the experiment/arm/spec (case-insensitive match on
   JAZ|arm B|experiment|2026-09-25-jaz) -- these are pure documentation
   comments; removing a line does not change behaviour.

Never touches code lines (only `//`-prefixed comment lines and the two named
string literals), so the drafter logic is byte-identical apart from prose.
"""

import re
import sys

TRIGGER = re.compile(r"JAZ|arm B|experiment|2026-09-25-jaz", re.IGNORECASE)

src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as f:
    lines = f.read().splitlines()

# 1. leading header comment block -> one neutral line.
i = 0
while i < len(lines) and lines[i].startswith("//"):
    i += 1
out = [
    "// .claude/workflows/plan-byref.js — a planning drafter that queries the tree and evidence store directly, pinned."
] + lines[i:]

# 2. meta.description / meta.whenToUse string values.
text = "\n".join(out)
text = re.sub(
    r"(description:\s*\n?\s*)'[^']*'",
    r"\1'Planning agent: draft a typed plan from a spec by querying the tree "
    r"and the evidence store, judge it, revise, ship'",
    text,
    count=1,
)
text = re.sub(
    r"(whenToUse:\s*\n?\s*)'[^']*'",
    r"\1'A spec is approved and a plan should be drafted by querying the tree "
    r"and the evidence store directly instead of a pre-gathered packet'",
    text,
    count=1,
)

# 3. any other // comment BLOCK (a run of consecutive whole-line comments)
# still naming the experiment anywhere in it -- drop the whole block, not
# just the matching line, so no half-sentence is left behind.
body_lines = text.splitlines()
final_lines = []
i = 0
while i < len(body_lines):
    ln = body_lines[i]
    if ln.strip().startswith("//"):
        j = i
        while j < len(body_lines) and body_lines[j].strip().startswith("//"):
            j += 1
        block = body_lines[i:j]
        if any(TRIGGER.search(b) for b in block):
            i = j
            continue
        final_lines.extend(block)
        i = j
        continue
    final_lines.append(ln)
    i += 1

with open(dst, "w", encoding="utf-8") as f:
    f.write("\n".join(final_lines) + "\n")
