# Second fixture plan (a different plan in the same repo)

### X1 (code, S) — edits the helm module too

**dependsOn:** none

**touches:** nixosModules/helm.nix
**acceptance:** helm-unit
**commit subject:** `helm: x1 (test: helm-unit)`

### X2 (code, S) — cycle a

**dependsOn:** X3

**touches:** a.py
**acceptance:** unit
**commit subject:** `x: a (test: unit)`

### X3 (code, S) — cycle b

**dependsOn:** X2

**touches:** b.py
**acceptance:** unit
**commit subject:** `x: b (test: unit)`
