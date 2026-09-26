# Opus gate — F6 (dsh-harness, integ/b2 @ fc9e809, commit 4a5f77f)

**Verdict: REWORK.** The `superpowers:` strip is right; the path rewrite is a regression.

## Blocking — the plugin-relative rewrite inverts dsh's own resolution rule

dsh resolves a skill's relative paths against **the skill's own directory**, not the
skills root: `dsh-skill-filesystem/lib/index.js:586-589` sets
`resourceBase = { kind:"directory", path: locator.directory }` where `directory =
<root>/<skill-name>`, and `dsh-skill/lib/index.js:75` renders "Resolve relative paths
mentioned by this skill against the base directory."

So from `skills/subagent-driven-development/`, the *old* `../requesting-code-review/code-reviewer.md`
resolved correctly; the new bare `requesting-code-review/code-reviewer.md` misses.
7 occurrences across 3 files are now unresolvable: `skills/executing-plans/SKILL.md:14`,
`skills/subagent-driven-development/SKILL.md:88,117,118,454`,
`skills/writing-skills/SKILL.md:12` (×2). All three probe paths MISS from their own base dir.
`factory/tests/skill-catalog.test.mjs:76-92` asserts existence relative to the repo
`skills/` root, so it certifies the regression instead of catching it.
`README.md:12-16`'s rationale ("does not ship the Claude plugin's directory layout") is
false — the vendored layout is the same sibling layout `../` assumes.

## Verified good

- **Prefix strip correct**: `SKILL_NAME = /^[a-z0-9]+(?:-[a-z0-9]+)*$/` at
  `dsh-skill/lib/index.js:17`. `superpowers:` 26 → 0.
- **Re-sync**: `diff -r skills/nixos /home/dalhaka/flakes/nixos-skill/skills/nixos` → exit 0, identical.
- **No body edits**: normalized diff vs upstream v6.3.0 empty but for the pre-existing
  `dsh-tools.md` line (`using-superpowers/SKILL.md:60`, present at `4a5f77f^`).
- **README recipe** (`README.md:41-42`) accurate; subject + `Co-Authored-By` trailer conform.
- 91/91 pass.

## Mutation table

| # | Mutation | Caught |
|---|---|---|
| M1 | restore `superpowers:` (`writing-plans/SKILL.md:16`) | yes (1 fail) |
| M2 | restore `../` (`writing-skills/SKILL.md:12`) | yes |
| M3 | delete `requesting-code-review/code-reviewer.md` | yes |
| M4 | revert S1 gotchas marker | yes |
| M5 | bare ref to non-existent skill | **no** |
| M6 | bare path to non-existent file | **no** |

## Fix

Revert the 7 path rewrites to `../<skill>/…`; keep the prefix strip; retarget test 2 to
resolve each cross-skill path against its own SKILL.md's directory (that also closes M5/M6).
