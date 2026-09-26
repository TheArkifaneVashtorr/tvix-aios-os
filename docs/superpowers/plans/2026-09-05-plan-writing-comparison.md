# Plan-writing compared: three models write the seat-behind-broker plan from the same spec (plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox syntax. The seat driver reads the `### KEY (kind, size) — title` sections below.

**Goal (operator, 2026-09-05 evening, a side project):** measure plan-writing as a factory role. Three arms write the implementation plan for `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md` blind to the orchestrator's plan: DeepSeek V4 Pro at effort high (run `pwp`, `OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 OPENROUTER_REASONING_EFFORT=high`), GLM 5.3 at xhigh (run `pwg`, `OPENROUTER_MODEL=z-ai/glm-5.3 OPENROUTER_REASONING_EFFORT=xhigh`), Kimi K3 at xhigh (run `pwk`, `OPENROUTER_MODEL=moonshotai/kimi-k3 OPENROUTER_REASONING_EFFORT=xhigh`). Each writes to its own file under `docs/reviews/plan-comparison/`. Then one **Fable** judge (Claude side; operator's instruction 2026-09-05 evening: "I want a fable instance for that … for the judge") scores the four plans (the three arms plus `docs/superpowers/plans/2026-09-05-seat-behind-broker.md`) on one rubric and writes `docs/reviews/2026-09-05-plan-writing-comparison.md`, with the usage lines from each `.result`. Outcome feeds `docs/ledger/routing.toml` (a `plan`/`research` row needs a measurement to exist). None of the three plans is executed.

**Data note:** the spec and the modules named below are repo content the operator has already permitted on the OpenRouter route (GLM and Kimi ran the 2026-09-04 fix rounds through the harness).

## Global Constraints

- Build-only; never `sudo`, `nixos-rebuild`, `systemctl`. The lint gate is `nix develop -c githooks/pre-commit`; commits via `nix develop -c git commit -F <msgfile>` with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer.
- Write nothing outside your one output file (and the board block the hook regenerates). Do not edit any plan or module.

### PW1pro (docs, M) — write the implementation plan for the seat-behind-broker spec (DeepSeek V4 Pro, effort high)

**dependsOn:** none

**Files:**
- Create: `docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-pro.md`

**Interfaces:** none. This is a measured comparison of plan-writing (operator, 2026-09-05 evening): three models write the same plan from the same spec, blind, and a Fable judge scores them against the spec and against the orchestrator's plan. Your output is the record; nothing here is executed.

**Rules that decide the score:** the plan must be complete and self-contained for an implementer with zero context — every file named with its exact path, every interface with names and signatures, every step an action with its command, red-before-green for every task, mutation targets named for the reviewer, waves derived from dependencies with file conflicts called out, the operator's steps (switch, acceptance, rollback) separated from the factory's. House format: the header block, Global Constraints, a Waves table, then `### KEY (kind, size) — title` sections each ending with `**touches:**`, `**acceptance:**` (real check names from `docs/MAP.md`), `**commit subject:**`. Read `docs/superpowers/plans/2026-09-05-evidence-store.md` (header, Waves, and its E1 and E8 sections) as the format reference and `docs/superpowers/plans/2026-09-05-session-context.md` (G1) as a second.

- [ ] **Step 1: Read**, in this order and nothing else from `docs/superpowers/plans/`: the spec `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md`; `nixosModules/modelLane.nix` and `nixosModules/egressBroker.nix` in full; `pkgs/lane/lane-submit.py`, `pkgs/lane/lane-run.py` (skim), `tests/integration/lane-vm.nix`; `pkgs/dsh-openrouter/dsh-openrouter.sh` (the key block ~218–242, the exec lines ~560–580); `tools/factory/seat/factory-task`; `hosts/core/lanes.nix`; `docs/MAP.md` for check names; CLAUDE.md. **Do NOT open `docs/superpowers/plans/2026-09-05-seat-behind-broker.md`** — it is the plan you are being compared against; the judge reads your transcript and a read of that file voids your arm.
- [ ] **Step 2: Write** the plan to the one file above. Facts you cite about the tree (option names, line numbers, check names, address blocks) must come from commands you ran (paste the command beside each fact). Every task section must be complete: no "TBD", no "similar to", no step without its command or code.
- [ ] **Step 3: Verify** — `nix develop -c githooks/pre-commit` green (the hook may regenerate the board block once: `git add docs/OPERATIONS.md` and commit again — that is expected); `wc -w` of your file in FACTORY-NOTES together with the list of commands you ran for facts.
- [ ] **Step 4: Commit** — exactly the one file (plus the regenerated board if the hook asks), subject below.

**touches:** docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-pro.md
**acceptance:** lint
**commit subject:** `docs: plan-writing comparison — the seat-behind-broker plan as written by DeepSeek V4 Pro, effort high (test: lint)`

### PW1glm (docs, M) — write the implementation plan for the seat-behind-broker spec (GLM 5.3, effort xhigh)

**dependsOn:** none

**Files:**
- Create: `docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-glm.md`

**Interfaces:** none. This is a measured comparison of plan-writing (operator, 2026-09-05 evening): three models write the same plan from the same spec, blind, and a Fable judge scores them against the spec and against the orchestrator's plan. Your output is the record; nothing here is executed.

**Rules that decide the score:** the plan must be complete and self-contained for an implementer with zero context — every file named with its exact path, every interface with names and signatures, every step an action with its command, red-before-green for every task, mutation targets named for the reviewer, waves derived from dependencies with file conflicts called out, the operator's steps (switch, acceptance, rollback) separated from the factory's. House format: the header block, Global Constraints, a Waves table, then `### KEY (kind, size) — title` sections each ending with `**touches:**`, `**acceptance:**` (real check names from `docs/MAP.md`), `**commit subject:**`. Read `docs/superpowers/plans/2026-09-05-evidence-store.md` (header, Waves, and its E1 and E8 sections) as the format reference and `docs/superpowers/plans/2026-09-05-session-context.md` (G1) as a second.

- [ ] **Step 1: Read**, in this order and nothing else from `docs/superpowers/plans/`: the spec `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md`; `nixosModules/modelLane.nix` and `nixosModules/egressBroker.nix` in full; `pkgs/lane/lane-submit.py`, `pkgs/lane/lane-run.py` (skim), `tests/integration/lane-vm.nix`; `pkgs/dsh-openrouter/dsh-openrouter.sh` (the key block ~218–242, the exec lines ~560–580); `tools/factory/seat/factory-task`; `hosts/core/lanes.nix`; `docs/MAP.md` for check names; CLAUDE.md. **Do NOT open `docs/superpowers/plans/2026-09-05-seat-behind-broker.md`** — it is the plan you are being compared against; the judge reads your transcript and a read of that file voids your arm.
- [ ] **Step 2: Write** the plan to the one file above. Facts you cite about the tree (option names, line numbers, check names, address blocks) must come from commands you ran (paste the command beside each fact). Every task section must be complete: no "TBD", no "similar to", no step without its command or code.
- [ ] **Step 3: Verify** — `nix develop -c githooks/pre-commit` green (the hook may regenerate the board block once: `git add docs/OPERATIONS.md` and commit again — that is expected); `wc -w` of your file in FACTORY-NOTES together with the list of commands you ran for facts.
- [ ] **Step 4: Commit** — exactly the one file (plus the regenerated board if the hook asks), subject below.

**touches:** docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-glm.md
**acceptance:** lint
**commit subject:** `docs: plan-writing comparison — the seat-behind-broker plan as written by GLM 5.3, effort xhigh (test: lint)`

### PW1kimi (docs, M) — write the implementation plan for the seat-behind-broker spec (Kimi K3, effort xhigh)

**dependsOn:** none

**Files:**
- Create: `docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-kimi.md`

**Interfaces:** none. This is a measured comparison of plan-writing (operator, 2026-09-05 evening): three models write the same plan from the same spec, blind, and a Fable judge scores them against the spec and against the orchestrator's plan. Your output is the record; nothing here is executed.

**Rules that decide the score:** the plan must be complete and self-contained for an implementer with zero context — every file named with its exact path, every interface with names and signatures, every step an action with its command, red-before-green for every task, mutation targets named for the reviewer, waves derived from dependencies with file conflicts called out, the operator's steps (switch, acceptance, rollback) separated from the factory's. House format: the header block, Global Constraints, a Waves table, then `### KEY (kind, size) — title` sections each ending with `**touches:**`, `**acceptance:**` (real check names from `docs/MAP.md`), `**commit subject:**`. Read `docs/superpowers/plans/2026-09-05-evidence-store.md` (header, Waves, and its E1 and E8 sections) as the format reference and `docs/superpowers/plans/2026-09-05-session-context.md` (G1) as a second.

- [ ] **Step 1: Read**, in this order and nothing else from `docs/superpowers/plans/`: the spec `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md`; `nixosModules/modelLane.nix` and `nixosModules/egressBroker.nix` in full; `pkgs/lane/lane-submit.py`, `pkgs/lane/lane-run.py` (skim), `tests/integration/lane-vm.nix`; `pkgs/dsh-openrouter/dsh-openrouter.sh` (the key block ~218–242, the exec lines ~560–580); `tools/factory/seat/factory-task`; `hosts/core/lanes.nix`; `docs/MAP.md` for check names; CLAUDE.md. **Do NOT open `docs/superpowers/plans/2026-09-05-seat-behind-broker.md`** — it is the plan you are being compared against; the judge reads your transcript and a read of that file voids your arm.
- [ ] **Step 2: Write** the plan to the one file above. Facts you cite about the tree (option names, line numbers, check names, address blocks) must come from commands you ran (paste the command beside each fact). Every task section must be complete: no "TBD", no "similar to", no step without its command or code.
- [ ] **Step 3: Verify** — `nix develop -c githooks/pre-commit` green (the hook may regenerate the board block once: `git add docs/OPERATIONS.md` and commit again — that is expected); `wc -w` of your file in FACTORY-NOTES together with the list of commands you ran for facts.
- [ ] **Step 4: Commit** — exactly the one file (plus the regenerated board if the hook asks), subject below.

**touches:** docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-kimi.md
**acceptance:** lint
**commit subject:** `docs: plan-writing comparison — the seat-behind-broker plan as written by Kimi K3, effort xhigh (test: lint)`
