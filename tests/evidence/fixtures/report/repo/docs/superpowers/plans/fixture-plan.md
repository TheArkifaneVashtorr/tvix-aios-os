# Fixture plan (report)

Six chains: two first-try, two one-fix-round, one re-plan, one open.

### A1 (code, S) — first-try alpha

**dependsOn:** none

**touches:** a.py
**acceptance:** unit
**commit subject:** `x: a1 (test: unit)`

### B1 (code, S) — first-try beta

**dependsOn:** none

**touches:** b.py
**acceptance:** unit
**commit subject:** `x: b1 (test: unit)`

### C1 (code, S) — one-fix-round gamma

**dependsOn:** none

**touches:** c.py
**acceptance:** unit
**commit subject:** `x: c1 (test: unit)`

### D1 (code, S) — one-fix-round delta

**dependsOn:** none

**touches:** d.py
**acceptance:** unit
**commit subject:** `x: d1 (test: unit)`

### E1 (code, S) — re-plan epsilon

**dependsOn:** none

**touches:** e.py
**acceptance:** unit
**commit subject:** `x: e1 (test: unit)`

### F1 (code, S) — open zeta

**dependsOn:** none

**touches:** f.py
**acceptance:** unit
**commit subject:** `x: f1 (test: unit)`