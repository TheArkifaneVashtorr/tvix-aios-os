# Opus gate — F6 round 2 (dsh-harness, integ/b2 @ 5333679, F6FIX 0e8789a)

**Verdict: APPROVE.** Round-1 blocker closed; all three claims hold.

## The references

They take the `../<skill>/…` form again — the parent's zero-hit grep was a
mislocated glob, not a missing fix. All seven, restored:
`skills/executing-plans/SKILL.md:14`,
`skills/subagent-driven-development/SKILL.md:88,117,118,454`,
`skills/writing-skills/SKILL.md:12` (×2).

dsh resolves them correctly. `dsh-skill-filesystem/lib/index.js:588` sets
`directory: entry.path` (= `<root>/<skill-name>`), fed to
`resourceBase {kind:"directory", path: locator.directory}` at `:605-608`;
`dsh-skill/lib/index.js:75` renders "Resolve relative paths mentioned by this
skill against the base directory." So `../` walks into the sibling skill.
Probed from each own base dir: 4/4 HIT; F6's bare form: MISS.

## Mutation table (`factory/tests/skill-catalog.test.mjs`, 6 tests)

| # | Mutation | Result |
|---|---|---|
| — | baseline | 6 pass / 0 fail |
| M1 | drop `../` → bare (`subagent-driven-development:454`) | **RED** 5/1 |
| M2 | ref non-existent file (`writing-skills:12`) | **RED** 5/1 |
| M3 | restore `superpowers:` (`writing-plans:61`) | **RED** 5/1 |
| M4 | `../no-such-skill/` (`subagent-driven-development:454`) | **RED** 5/1 |
| M5 | break directory ref (`executing-plans:14`) | **RED** 5/1 |
| — | restored | 6 pass / 0 fail |

Round-1's uncaught M5/M6 are now M4/M2 — both red. 93/93 node tests pass.

## Verified

- `diff -r skills/nixos /home/dalhaka/flakes/nixos-skill/skills/nixos` (master
  `e76d2ef`) → exit 0, identical.
- `superpowers:` 26 → 0. Every non-nixos hunk in `git diff c7e6fe7 HEAD --
  skills/` is a prefix strip; no body prose altered.
- Test's SKILL.md-only scope is sound (dsh's base is the skill dir) and no
  non-SKILL.md file carries a cross-skill relative ref.
- `README.md:12-16` rationale now correct.

## Nit (non-blocking)

F6FIX carries only `Generated-By:`; F6 (`4a5f77f`) carried
`Co-Authored-By: Claude Fable 5.1` too. Master is mixed (13 vs 7), so this is
convention drift, not a violation.
