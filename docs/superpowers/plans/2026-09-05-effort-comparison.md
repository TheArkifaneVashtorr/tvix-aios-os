# Reasoning effort medium vs xhigh — a measured comparison (plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox syntax. The seat driver reads the `### KEY (kind, size) — title` sections below.

**Goal:** the seat's saved reasoning level (medium today; an xhigh backup file from 2026-09-04 still sits in the shared home) is decided by measurement, not opinion (operator, 2026-09-05; claim `xhigh-restore-or-keep-medium`). Same method as `docs/reviews/2026-09-05-model-comparison.md`: two real XS tasks, one run per effort on DeepSeek V4 Pro, the same Opus gate, tokens and wall clock from the `.result` usage line, one review doc `docs/reviews/2026-09-05-effort-comparison.md`. Runs `em` (`OPENROUTER_REASONING_EFFORT=medium`) and `ex` (`=xhigh`). Only one arm of each pair integrates (the approved one; medium's when both are approved). Texts within a pair are identical except the key.

## Global Constraints

- Build-only; never `sudo`, `nixos-rebuild`, `systemctl`. Checks via `nix build .#checks.x86_64-linux.<name> -L --no-link`; lint gate `nix develop -c githooks/pre-commit`; commits via `nix develop -c git commit -F <msgfile>` with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer. TDD, red first. Python via ruff.

## Tasks

### X1med (code, XS) — the parity tile names the exit status when the unit result is success but the status is not 0

**dependsOn:** none

**Files:** `pkgs/helm/collect.py` (`tile_backup_parity`, the early-return message), `tests/helm/test_collect.py` (append)

**Interfaces:** the red tile's summary reads `proton-drive-push.service last result <result>, status <status>` (e.g. `last result success, status 1`) whenever the early return fires; the detail dict is unchanged. Origin: the R3rb gate minor — a red tile whose summary said `last result success` when only `ExecMainStatus` was non-zero.

- [ ] **Step 1: Failing test** — in `tests/helm/test_collect.py`, find how existing tests stub `_unit_result` (monkeypatch) and add: `_unit_result` returns `("success", "1")` → the tile is `fail` and its summary equals `proton-drive-push.service last result success, status 1`; and `("failed", "0")` → summary `… last result failed, status 0`.
- [ ] **Step 2: Red** — `nix develop -c pytest tests/helm -q -k parity` → the summary lacks `, status 1`.
- [ ] **Step 3: Implement** the one f-string change. **Step 4: Green** — ruff; pytest; `nix build .#checks.x86_64-linux.helm-unit -L --no-link`; lint gate. **Step 5: Commit.**

**touches:** pkgs/helm/collect.py, tests/helm/test_collect.py
**acceptance:** helm-unit, lint
**commit subject:** `helm: the parity tile's red summary names both the unit result and the exit status (test: helm-unit, lint)`

### X1xhigh (code, XS) — the parity tile names the exit status when the unit result is success but the status is not 0

**dependsOn:** none

**Files:** `pkgs/helm/collect.py` (`tile_backup_parity`, the early-return message), `tests/helm/test_collect.py` (append)

**Interfaces:** the red tile's summary reads `proton-drive-push.service last result <result>, status <status>` (e.g. `last result success, status 1`) whenever the early return fires; the detail dict is unchanged. Origin: the R3rb gate minor — a red tile whose summary said `last result success` when only `ExecMainStatus` was non-zero.

- [ ] **Step 1: Failing test** — in `tests/helm/test_collect.py`, find how existing tests stub `_unit_result` (monkeypatch) and add: `_unit_result` returns `("success", "1")` → the tile is `fail` and its summary equals `proton-drive-push.service last result success, status 1`; and `("failed", "0")` → summary `… last result failed, status 0`.
- [ ] **Step 2: Red** — `nix develop -c pytest tests/helm -q -k parity` → the summary lacks `, status 1`.
- [ ] **Step 3: Implement** the one f-string change. **Step 4: Green** — ruff; pytest; `nix build .#checks.x86_64-linux.helm-unit -L --no-link`; lint gate. **Step 5: Commit.**

**touches:** pkgs/helm/collect.py, tests/helm/test_collect.py
**acceptance:** helm-unit, lint
**commit subject:** `helm: the parity tile's red summary names both the unit result and the exit status (test: helm-unit, lint)`

### X2med (code, XS) — the bundle says "equal to live" when HEAD is the live revision

**dependsOn:** none

**Files:** `pkgs/evidence/evidence.py` (`bundle`: `docs_only` computation; `render_bundle_markdown`: the Live/HEAD line), `tests/evidence/test_evidence.py` (append)

**Interfaces:** `docs_only_ahead` is `False` when `live == head`; the rendered line reads `**Live:** <gen> at <rev>. **HEAD:** <rev> (equal to live).` when equal, `(docs-only ahead of live)` when ahead in docs only, and nothing extra otherwise. Origin: the board follow-up "it says docs-only ahead of live when live equals HEAD (say equal)".

- [ ] **Step 1: Failing test** — reuse `make_repo`/`fake_nixos_version` from the existing bundle tests: build a repo, point the fake `nixos-version` at HEAD itself → `b["docs_only_ahead"] is False` and `"(equal to live)" in ev.render_bundle_markdown(b)` and `"docs-only" not in …`; keep the existing docs-only-ahead test green.
- [ ] **Step 2: Red** — `nix develop -c pytest tests/evidence/test_evidence.py -q -k equal` → `docs_only_ahead` is `True` (or `(equal to live)` missing).
- [ ] **Step 3: Implement**; **Step 4: Green** — ruff; pytest; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; lint gate. **Step 5: Commit.**

**touches:** pkgs/evidence/evidence.py, tests/evidence/test_evidence.py
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the bundle says equal to live when HEAD is the live revision, docs-only ahead only when it is (test: evidence-unit, lint)`

### X2xhigh (code, XS) — the bundle says "equal to live" when HEAD is the live revision

**dependsOn:** none

**Files:** `pkgs/evidence/evidence.py` (`bundle`: `docs_only` computation; `render_bundle_markdown`: the Live/HEAD line), `tests/evidence/test_evidence.py` (append)

**Interfaces:** `docs_only_ahead` is `False` when `live == head`; the rendered line reads `**Live:** <gen> at <rev>. **HEAD:** <rev> (equal to live).` when equal, `(docs-only ahead of live)` when ahead in docs only, and nothing extra otherwise. Origin: the board follow-up "it says docs-only ahead of live when live equals HEAD (say equal)".

- [ ] **Step 1: Failing test** — reuse `make_repo`/`fake_nixos_version` from the existing bundle tests: build a repo, point the fake `nixos-version` at HEAD itself → `b["docs_only_ahead"] is False` and `"(equal to live)" in ev.render_bundle_markdown(b)` and `"docs-only" not in …`; keep the existing docs-only-ahead test green.
- [ ] **Step 2: Red** — `nix develop -c pytest tests/evidence/test_evidence.py -q -k equal` → `docs_only_ahead` is `True` (or `(equal to live)` missing).
- [ ] **Step 3: Implement**; **Step 4: Green** — ruff; pytest; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; lint gate. **Step 5: Commit.**

**touches:** pkgs/evidence/evidence.py, tests/evidence/test_evidence.py
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the bundle says equal to live when HEAD is the live revision, docs-only ahead only when it is (test: evidence-unit, lint)`
