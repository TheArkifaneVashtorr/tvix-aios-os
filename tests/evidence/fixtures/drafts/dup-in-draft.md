# Dup in draft (the same key typed twice in one file)

## Global Constraints

Build-only.

## Assumptions

None beyond the house rules.

## Waves

(derived by `evidence tasks`)

## Operator

Nothing to switch.

### Z1 (code, S) — the first section

**dependsOn:** none

**touches:** tools/za.sh
**acceptance:** unit
**commit subject:** `x: z1a (test: unit)`

### Z1 (code, S) — the second section, same key

**dependsOn:** none

**touches:** tools/zb.sh
**acceptance:** unit
**commit subject:** `x: z1b (test: unit)`