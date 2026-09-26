# Operator items turned into factory tasks (2026-09-05) — plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox syntax. The seat driver reads the `### KEY (kind, size) — title` sections below.

**Goal:** the operator's open items that are factory work, not decisions: the ledger reads the real OpenRouter activity export (claim `d5-activity-export`), and the host's nixpkgs pin moves to the current 25.05 head with the full flake check, the VM tests and a closure diff (claim `nixpkgs-host-pin-age`; operator: "if it can be VM tested just do it now").

**Facts (2026-09-05 ~16:30):** `nixpkgs-host` = `ac62194c3917d5f474c1a844b6fd6da2db95077d` (2026-01-02). `~/flakes/gaming` pins its own `nixpkgs` to the same rev and `checks.core-gaming-wiring` asserts equality with the host pin, so gaming relocks first (PB0, in the gaming repo), then the host (PB1). Current `refs/heads/nixos-25.05`: `ac62194c3917d5f474c1a844b6fd6da2db95077d` (read with `git ls-remote` at planning time; PB0 re-reads it and PB1 uses PB0's rev). The activity export at `~/strategy/ledger/openrouter-activity.csv` has columns `generation_id,created_at,cost_total,cost_web_search,cost_cache,cost_file_processing,byok_usage_inference,tokens_prompt,tokens_completion,tokens_reasoning,tokens_cached,model_permaslug,provider_name,variant,cancelled,streamed,user,finish_reason_raw,finish_reason_normalized,generation_time_ms,time_to_first_token_ms,api_key_disabled,api_key_name,app_name`; `tools/ledger/factory.py rollup --activity` refuses it (`activity export must have columns date, model, cost`). The file is the operator's data: never copy rows into the repo; fixtures are synthetic.

## Global Constraints

- Build-only; never `sudo`, `nixos-rebuild`, `systemctl`. Checks via `nix build .#checks.x86_64-linux.<name> -L --no-link`; lint gate `nix develop -c githooks/pre-commit`; commits via `nix develop -c git commit -F <msgfile>` with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer. TDD, red first.
- PB0 runs in `~/flakes/gaming` (its own hooks: `githooks/pre-commit`, `pre-push`); PB1 runs here.

## Tasks

### DA1 (code, S) — the ledger reads the real OpenRouter activity export

**dependsOn:** none

**Files:** `tools/ledger/factory.py` (`_load_activity`, the column check), `tools/ledger/schema.md`, `tests/ledger/test_factory.py` (append), `tests/ledger/fixtures/activity-export.csv` (synthetic, ≤ 5 rows, the real header verbatim)

**Interfaces:** `_load_activity` accepts BOTH shapes: the old `date,model,cost` and the real export, mapping `created_at` (ISO timestamp, keep the date part `YYYY-MM-DD`) → date, `model_permaslug` → model, `cost_total` → cost (float; `cancelled == "true"` rows still count their cost). The error message on an unknown shape lists both accepted column sets. `schema.md` documents the mapping.

- [ ] **Step 1: Failing tests** — fixture with the real header and 4 synthetic rows (two dates, two models, one cancelled); test `_load_activity(fixture) == {("2026-09-04","deepseek/deepseek-v4-pro-0813"): <sum>, …}`; the old shape still parses (existing test); an unrelated header still raises `ActivityExportError` naming both shapes.
- [ ] **Step 2: Red** — `nix develop -c pytest tests/ledger -q -k activity` → `ActivityExportError` on the new fixture. **Step 3: Implement.** **Step 4: Green** — ruff; pytest; `nix build .#checks.x86_64-linux.ledger-unit -L --no-link`; lint gate; then, read-only against the operator's file: `nix develop -c python3 tools/ledger/factory.py rollup --activity ~/strategy/ledger/openrouter-activity.csv | tail -5` prints dollars without a traceback (paste the last 3 lines, no user or key names, into FACTORY-NOTES). **Step 5: Commit.**

**touches:** tools/ledger/factory.py, tools/ledger/schema.md, tests/ledger/test_factory.py, tests/ledger/fixtures/activity-export.csv
**acceptance:** ledger-unit, lint
**commit subject:** `ledger: rollup --activity reads the real OpenRouter export (created_at, model_permaslug, cost_total) as well as date,model,cost (test: ledger-unit, lint)`

### Withdrawn 2026-09-05 (was PB0, code, S): gaming relocks nixpkgs to the current 25.05 head

**dependsOn:** none (runs in `~/flakes/gaming`)

**Files (in ~/flakes/gaming):** `flake.nix` (`inputs.nixpkgs.url` rev), `flake.lock`

- [ ] **Step 1** `rev=$(git ls-remote https://github.com/NixOS/nixpkgs refs/heads/nixos-25.05 | cut -f1)`; record it in FACTORY-NOTES. Edit `inputs.nixpkgs.url = "github:NixOS/nixpkgs/<rev>"`; `nix flake lock`; confirm `flake.lock`'s `nixpkgs` node is that rev.
- [ ] **Step 2** `nix flake check -L` in the gaming repo (all its checks, including any VM test) — green, or STOP and report the failing check verbatim (do not patch around a nixpkgs change; report it as blocked).
- [ ] **Step 3** the repo's own lint gate (`githooks/pre-commit` there), then one commit: `gaming: nixpkgs → nixos-25.05 <rev-short> (2026-09-05); flake check green (test: flake-check)` with the trailer.

**touches:** flake.nix, flake.lock
**acceptance:** flake-check
**commit subject:** `gaming: nixpkgs → nixos-25.05 head (2026-09-05); flake check green (test: flake-check)`

### Withdrawn 2026-09-05 (was PB1, code, M): nixpkgs-host moves to the same rev; full flake check, VM tests, toplevel, closure diff

**dependsOn:** PB0 (landed on gaming's `main`: `checks.core-gaming-wiring` asserts the gaming lock equals the host pin)

**Files:** `flake.nix` (`nixpkgs-host.url` rev), `flake.lock` (`nixpkgs-host` and `gaming` nodes), `docs/reviews/2026-09-05-pin-bump.md` (new: the rev, every check's verdict, the closure diff verbatim, upstream drift observed)

- [ ] **Step 1** read PB0's rev from `~/flakes/gaming/flake.lock` (read-only); set `nixpkgs-host.url` to it; `nix flake lock --update-input nixpkgs-host --update-input gaming`; confirm both lock nodes.
- [ ] **Step 2** `nix flake check -L` — every check including the VM tests (`integration`, `helm-vm`, `helm-control-vm`, `lane-vm`, `proton-backup-vm`); on a failure caused by the nixpkgs move (an option renamed, a package gone), fix the minimal thing in the module it names, record the drift in the review doc (CLAUDE.md: report upstream drift before adapting), and re-run; if a fix is not minimal, STOP and report blocked.
- [ ] **Step 3** `nix build .#nixosConfigurations.core.config.system.build.toplevel --no-link --print-out-paths` then `nix store diff-closures /run/current-system <toplevel>` — paste verbatim into the review doc.
- [ ] **Step 4** lint gate; one commit: subject below. The operator switches (not you).

**touches:** flake.nix, flake.lock, docs/reviews/2026-09-05-pin-bump.md
**acceptance:** host-core, core-gaming-wiring, lint
**commit subject:** `host: nixpkgs-host → nixos-25.05 head (2026-09-05); full flake check and VM tests green; closure diff recorded (test: host-core, core-gaming-wiring, lint)`

## PB0/PB1 re-instated (2026-09-05 evening): the target is the current release, nixos-26.05

The withdrawal above misread the operator: "update to the most recent version" means the newest NixOS release, not the newest commit on the finished 25.05 branch. Target: `refs/heads/nixos-26.05` = `a5cc6f2c37bf518436dc8d1c288ccd0c43c2f4c4` (read at planning time; PB0 re-reads it and PB1 uses PB0's rev). Two releases forward (25.05 → 25.11 → 26.05): option renames and package changes are expected; the full flake check with the five VM tests is the gate; the operator switches. The tools pin `nixpkgs` (nixos-unstable) is unchanged.

### PB0 (code, S) — gaming relocks nixpkgs to the nixos-26.05 head

**dependsOn:** none (runs in `~/flakes/gaming`)
**repo:** gaming

**Files (in ~/flakes/gaming):** `flake.nix` (`inputs.nixpkgs.url` rev), `flake.lock`; any module fix the release move forces (record each as upstream drift in the commit body)

- [ ] **Step 1** `rev=$(git ls-remote https://github.com/NixOS/nixpkgs refs/heads/nixos-26.05 | cut -f1)`; record it. Edit `inputs.nixpkgs.url = "github:NixOS/nixpkgs/<rev>"`; `nix flake lock`; confirm the lock node.
- [ ] **Step 2** `nix flake check -L` in the gaming repo. On a failure caused by the release move (an option renamed or removed, a package gone), fix the minimal thing in the module the error names and record the drift (what changed upstream, what you changed) in the commit body; if the fix is not minimal, STOP and report blocked with the error verbatim.
- [ ] **Step 3** the repo's own lint gate; one commit, subject below, with the trailer.

**touches:** flake.nix, flake.lock, modules
**acceptance:** flake-check
**commit subject:** `gaming: nixpkgs → nixos-26.05 head (2026-09-05); flake check green; upstream drift recorded (test: flake-check)`

### PB1 (code, M) — nixpkgs-host moves to nixos-26.05; full flake check, VM tests, toplevel, closure diff

**dependsOn:** PB0 (landed on gaming's `main`: `checks.core-gaming-wiring` asserts the gaming lock equals the host pin)

**Files:** `flake.nix` (`nixpkgs-host.url` rev), `flake.lock` (`nixpkgs-host` and `gaming` nodes), `docs/reviews/2026-09-05-release-upgrade-26.05.md` (new: the rev, every check's verdict, the closure diff verbatim, every upstream drift and the module change it forced), plus the minimal module fixes the release forces (`hosts/core/*.nix`, `nixosModules/*.nix`) — each named in the review doc

- [ ] **Step 1** read PB0's rev from `~/flakes/gaming/flake.lock` (read-only); set `nixpkgs-host.url` to it; `nix flake lock --update-input nixpkgs-host --update-input gaming`; confirm both lock nodes.
- [ ] **Step 2** `nix flake check -L` — every check including `integration`, `helm-vm`, `helm-control-vm`, `lane-vm`, `proton-backup-vm`. Per failure: if the release move caused it (renamed option, removed package, changed default), make the minimal change in the module named, record it, re-run; if a fix would not be minimal or touches brief §3 invariants (baskets, broker, managed settings, firewall), STOP and report blocked with the error verbatim — the orchestrator decides.
- [ ] **Step 3** `nix build .#nixosConfigurations.core.config.system.build.toplevel --no-link --print-out-paths`, then `nix store diff-closures /run/current-system <toplevel>` — verbatim into the review doc (expect a long list: kernel, glibc, NVIDIA driver, mitmproxy, python, node — name anything surprising).
- [ ] **Step 4** lint gate; one commit, subject below. The operator switches; rollback is the previous generation.

**touches:** flake.nix, flake.lock, docs/reviews/2026-09-05-release-upgrade-26.05.md, hosts/core, nixosModules
**acceptance:** host-core, core-gaming-wiring, lint
**commit subject:** `host: nixpkgs-host → nixos-26.05 head (2026-09-05); full flake check and VM tests green; closure diff and upstream drift recorded (test: host-core, core-gaming-wiring, lint)`
