# Subject mismatch draft (the (test: …) names are compared as a set)

## Global Constraints

Build-only.

## Assumptions

None beyond the house rules.

## Waves

(derived by `evidence tasks`)

## Operator

Nothing to switch.

### ZA (code, S) — same set, different order (must pass)

**dependsOn:** none

**touches:** tools/za.sh
**acceptance:** unit, lint
**commit subject:** `x: za (test: lint, unit)`

### ZB (code, S) — names do not match acceptance

**dependsOn:** none

**touches:** tools/zb.sh
**acceptance:** unit
**commit subject:** `x: zb (test: lint)`