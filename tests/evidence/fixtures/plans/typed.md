# Typed fixture plan

## Waves

| wave | tasks |
|---|---|
| 1 | E1, E3 |

## Tasks

### E1 (code, M) — the store

**dependsOn:** none

Body text for E1.

**touches:** pkgs/evidence/evidence.py, flake.nix
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the store (test: evidence-unit, lint)`

### E3 (code, S) — attribution

**dependsOn:** none (integrates in the same wave as E1; prompt text only)

**touches:** tools/factory/dark-factory.js
**acceptance:** factory-unit, lint
**commit subject:** `factory: attribution (test: factory-unit, lint)`

### E5 (code, M) — tiles

**dependsOn:** E1, R4 (both edit `nixosModules/helm.nix`)

**touches:** nixosModules/helm.nix, `pkgs/helm/collect.py`
**acceptance:** helm-unit, lint
**commit subject:** `helm: tiles (test: helm-unit, lint)`

### E7 (code, S) — the integrator records

**dependsOn:** E1

**touches:** tools/factory/seat/factory-integrate
**acceptance:** unit, lint
**commit subject:** `factory: the integrator records (test: unit, lint)`

### D1 (docs, XS) — a note

**dependsOn:** E7

**touches:** docs/runbooks/x.md
**commit subject:** `docs: a note (test: lint)`

## Operator

Nothing to switch. The text below is a quoted example and must not become tasks:

```markdown
### Z9 (code, S) — phantom inside a fence

**dependsOn:** D1
```
