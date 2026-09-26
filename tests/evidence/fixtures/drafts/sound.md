# Sound draft (Z2 depends on Z1; disjoint touches)

## Global Constraints

Build-only.

## Assumptions

None beyond the house rules.

## Waves

| wave | tasks |
|---|---|
| 1 | Z1 |
| 2 | Z2 |

## Operator

Nothing to switch.

### Z1 (code, S) — the root of the draft

**dependsOn:** none

**touches:** z1.py
**acceptance:** evidence-unit, lint
**commit subject:** `x: z1 (test: evidence-unit, lint)`

### Z2 (docs, XS) — follows Z1

**dependsOn:** Z1

**touches:** z2.py
**acceptance:** lint
**commit subject:** `docs: z2 (test: lint)`