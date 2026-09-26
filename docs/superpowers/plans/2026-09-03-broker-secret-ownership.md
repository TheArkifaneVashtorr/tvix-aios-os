# Broker secret ownership at switch time (field bug L1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Executor: `tools/factory/dark-factory.js` in this repo (host `core`, build-only; the host is live on generation 23 — never restart units, the operator does that).

**Goal:** a broker instance whose `inject` reads a secret file comes up on the first attempt at a switch, with the file owned correctly before any unit starts, and survives a transient permission race instead of hitting the start limit.

**Spec:** field bug L1 (board, "Switch to generation 23"): at 14:49 `switch-to-configuration` started `egress-broker-openrouter.service` before `systemd-tmpfiles-resetup.service` ran the lane module's `z /var/lib/secrets/openrouter-key 0440 root egress-broker -` rule; `policy.py` line 35 raised `PermissionError` reading the file; `Restart=on-failure` retried 5× within 3 s and systemd gave up ("Start request repeated too quickly"). `After=systemd-tmpfiles-setup.service` orders boot only. Evidence: the unit's journal and `systemctl show -p After,NRestarts,Result`.

## Global Constraints
Build-only; never `systemctl restart` anything on the host; never read `/var/lib/secrets/*`; commits through the devShell with a blank line before the trailer; subjects `broker: … (test: …)` / `docs: …`. Load-bearing tests are shown to fail first (decision `docs/decisions/2026-09-03-test-based-reality-amendments.md`).

### Task 1 (code): ownership from an activation script; restart headroom; VM guard that reproduces the race
**Files:** `nixosModules/egressBroker.nix`, `nixosModules/modelLane.nix` (keep the tmpfiles `z` rule; add a comment that activation owns first), `tests/integration/broker-vm.nix` and/or `tests/integration/lane-vm.nix`, `flake.nix` (eval pins in `lane-eval`, `cowork-eval`, `host-core`).
- [ ] **Red first (VM):** in `lane-vm.nix`: `machine.succeed("systemctl stop egress-broker-openrouter; chown root:root /var/lib/secrets/openrouter-key; chmod 0400 /var/lib/secrets/openrouter-key")`, then `machine.succeed("/run/current-system/bin/switch-to-configuration test")` (re-runs activation; the unit itself is unchanged so activation does not restart it), then `machine.succeed("systemctl start egress-broker-openrouter")` and `machine.wait_for_unit("egress-broker-openrouter.service")`; assert `stat -c %U:%G:%a /var/lib/secrets/openrouter-key` is `root:egress-broker:440`. On the current code the start fails (permission) → red. Also assert the unit's rendered text carries `RestartSec=3` and `StartLimitBurst=20` (eval pins in `lane-eval` for the harness instance and in `host-core` for `openrouter`).
- [ ] **Fix:** `egressBroker.nix`: `system.activationScripts.egress-broker-secrets` (deps `[ "users" ]`, so the group exists) — for every instance and every `inject.<host>.valueFile`: `if [ -e "$f" ]; then chown root:egress-broker "$f"; chmod 0440 "$f"; fi` with a WHY comment (a switch starts new units before tmpfiles-resetup; activation scripts run before both); every broker instance unit gets `serviceConfig.RestartSec = 3;` and `unitConfig = { StartLimitIntervalSec = 120; StartLimitBurst = 20; }` with a comment. Keep the lane module's tmpfiles `z` line as the boot-time backstop. Checks: `integration`, `lane-vm`, `lane-eval`, `cowork-eval`, `host-core`, `lint`. Commit `broker: secret files are owned in the activation phase, before any unit starts; restart headroom for a transient race; VM guard reproduces the switch-time failure (test: integration, lane-vm, lane-eval, cowork-eval, host-core, lint)`.

### Task 2 (docs): runbook and board
- [ ] `docs/runbooks/switch-helm-gaming.md` §7: drop the manual restart once this lands (note that generation 23 needed it once); `docs/runbooks/lanes.md`: the ownership rule is applied at activation and at boot; board: L1 closed. Commit `docs: L1 closed — broker secret ownership at activation; runbooks (test: lint)`.

## Amendment (2026-09-03 15:00, live diagnosis)
The tmpfiles `z` rule DID apply at the switch (`systemd-tmpfiles-resetup` finished
without error). The broker still cannot open the key because the containing
directory `/var/lib/secrets` is `root:root 0750` (created by the operator on the
orchestrator's instruction, which was wrong): user `egress-broker` cannot
traverse it. Task 1 therefore also owns the DIRECTORY: tmpfiles
`d /var/lib/secrets 0750 root egress-broker -` (declared once by the broker
module, not per lane) and the activation script chgrps it too; the VM guard
starts from a `root:root 0750` directory. Operator fix today:
`sudo chgrp egress-broker /var/lib/secrets`, then reset-failed + restart.
