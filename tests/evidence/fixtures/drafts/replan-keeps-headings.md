# Replan keeps headings draft (both headings intact, a B2r section appended)

## Global Constraints

Build-only.

## Assumptions

None beyond the house rules.

## Waves

(derived by `evidence tasks`)

## Operator

Nothing to switch.

### B1 (code, S) — the root

**dependsOn:** none

**touches:** tools/b1.sh
**acceptance:** unit
**commit subject:** `x: b1 (test: unit)`

### B2 (code, S) — the open dependent

**dependsOn:** B1

**touches:** tools/x.sh
**acceptance:** unit
**commit subject:** `x: b2 (test: unit)`

### B2r (code, S) — the fix round

**dependsOn:** B1

**touches:** tools/b2r.sh
**acceptance:** unit
**commit subject:** `x: b2r (test: unit)`