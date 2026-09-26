# Replan drops heading draft (rewrites B1's heading: the original is dropped)

## Global Constraints

Build-only.

## Assumptions

None beyond the house rules.

## Waves

(derived by `evidence tasks`)

## Operator

Nothing to switch.

### B1 (code, S) — rewritten heading

**dependsOn:** none

**touches:** tools/b1.sh
**acceptance:** unit
**commit subject:** `x: b1 (test: unit)`

### B2 (code, S) — the open dependent

**dependsOn:** B1

**touches:** tools/x.sh
**acceptance:** unit
**commit subject:** `x: b2 (test: unit)`