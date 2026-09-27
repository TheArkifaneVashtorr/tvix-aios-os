#!/usr/bin/env python3
"""scrub_plan_byref.py <input> <output> -- write a fixture copy of one of the
four JAZ workflow scripts (plan.js, plan-byref.js, draft-packet.js,
draft-byref.js) with every trace of the experiment's own name/spec path
removed from comments and meta strings, so a by-reference drafter browsing
the fixture tree cannot read "this is a JAZ experiment arm being measured"
off the workflow file it is about to run.

What it does, in order:
1. Drops the leading `//`-only header comment block, replacing it with one
   neutral line -- chosen from the input file's own meta.name (plan,
   plan-byref, draft-packet or draft-byref), so each of the four gets a
   header describing what IT is, not a copy of another file's.
2. Replaces `meta.description` and `meta.whenToUse` (single-quoted string
   literals) with ONE fixed neutral string each, THE SAME for all four
   files (Opus review, 2026-09-26: a per-file description/whenToUse -- even
   a neutral one -- contrasts "gathers a packet" against "queries the tree
   directly", which tells a by-reference drafter reading its own workflow
   file that two differently-shaped drafters exist to be compared, without
   ever needing the word "JAZ"; identical text carries no such contrast).
3. Drops any OTHER whole-line `//` comment block anywhere in the file that
   still names the experiment/arm/spec (case-insensitive match on
   JAZ|arm B|experiment|2026-09-25-jaz) -- these are pure documentation
   comments; removing a block does not change behaviour.

Never touches code lines (only `//`-prefixed comment lines and the two named
string literals), so the drafter logic is byte-identical apart from prose --
this is what tools/experiments/jaz/check-truncation.py proves for the pairs
(plan.js, draft-packet.js) and (plan-byref.js, draft-byref.js).

A file whose meta.name is not one of the four still gets the identical
neutral description/whenToUse (they never varied by key) and a generic
neutral header, rather than failing outright, so this script degrades
instead of crashing on an unrecognised input.
"""

import re
import sys

TRIGGER = re.compile(r"JAZ|arm B|experiment|2026-09-25-jaz", re.IGNORECASE)

NEUTRAL_HEADER = {
    "plan": "// .claude/workflows/plan.js — the planning agent, pinned.",
    "plan-byref": "// .claude/workflows/plan-byref.js — a planning drafter that queries the tree and evidence store directly, pinned.",
    "draft-packet": "// .claude/workflows/draft-packet.js — a planning drafter: gather a five-reader packet, then draft one plan from it, pinned.",
    "draft-byref": "// .claude/workflows/draft-byref.js — a planning drafter that queries the tree and evidence store directly as it drafts, pinned.",
}
FALLBACK_HEADER = "// a planning workflow script, pinned."

# One shared string each, deliberately identical across all four files --
# see point 2 above. Neither may itself trip build-fixtures.sh's broader
# post-build gate (jaz|experiment|arm [ab]\b|by-reference|2026-09-25).
NEUTRAL_DESCRIPTION = "'Planning agent: draft a typed plan from a spec'"
NEUTRAL_WHEN_TO_USE = "'A spec is approved and needs a draft'"

src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as f:
    original = f.read()
lines = original.splitlines()

# meta.name picks which of the four neutral vocabularies to use -- each file
# gets a header/description/whenToUse describing itself, never another
# file's borrowed text.
name_match = re.search(r"name:\s*'([^']+)'", original)
key = name_match.group(1) if name_match else None

# 1. leading header comment block -> one neutral line, keyed by meta.name.
i = 0
while i < len(lines) and lines[i].startswith("//"):
    i += 1
header_line = NEUTRAL_HEADER.get(key, FALLBACK_HEADER)
out = [header_line] + lines[i:]

# 2. meta.description / meta.whenToUse string values -- the SAME neutral
# text on every file (see the module docstring, point 2): no per-file
# lookup here, on purpose.
text = "\n".join(out)
text = re.sub(
    r"(description:\s*\n?\s*)'[^']*'",
    lambda m: m.group(1) + NEUTRAL_DESCRIPTION,
    text,
    count=1,
)
text = re.sub(
    r"(whenToUse:\s*\n?\s*)'[^']*'",
    lambda m: m.group(1) + NEUTRAL_WHEN_TO_USE,
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
