# Phase 4a — Host Absorption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `core`'s entire system configuration lives in this repo as `nixosConfigurations.core`, pinned and reproducible; the operator's first flake rebuild is a reviewed, near-zero-delta switch; `/etc/nixos` is preserved untouched as fallback.

**Architecture:** Translate the two hand-managed files (`/etc/nixos/configuration.nix`, `/etc/nixos/ai-bootstrap.nix`) plus the verbatim `hardware-configuration.nix` into `hosts/core/` modules. The host builds from a **separate pinned nixpkgs input at the exact rev the machine already runs** (`ac62194c3917`, per the running system's version string `25.05.813814.ac62194c3917`), so the absorption itself changes almost nothing — upgrades become deliberate pin bumps later. `claude-code` moves off the impure `<nixos-unstable>` channel import onto a pinned `numtide/llm-agents.nix` input. The repo's existing dev/check pin (`34ab9907`) is untouched. Acceptance shows the operator a closure diff between the running system and the flake build before any switch.

**Tech Stack:** flake inputs (`nixpkgs-host`, `llm-agents`), NixOS modules, `nix store diff-closures`.

**Spec:** design doc §6 + concept `2026-09-02-absorb-host-bootstrap`; operator decision 2026-09-02 "absorb first".

## Global Constraints

- All Phase 1–3 Global Constraints apply (lint gates, `nix develop -c git commit`, trailers, never push, no secrets).
- Commit messages: `phase4a: <task summary>`.
- **Behavior preservation is the acceptance bar:** the flake build must reproduce the running system with the smallest possible delta. `system.stateVersion = "25.05"` is kept VERBATIM. Every intentional delta is listed in Task 1 Step 2 — anything else appearing in the closure diff is a bug.
- `/etc/nixos/*` is read, never modified, never deleted.
- Source files for translation are read from disk at implementation time: `/etc/nixos/configuration.nix`, `/etc/nixos/ai-bootstrap.nix`, `/etc/nixos/hardware-configuration.nix` (all world-readable). Copy content faithfully; do not "improve" settings not named in the delta list.
- Pins resolved at implementation time and recorded in the task report: `nixpkgs-host` = full rev of `ac62194c3917` (resolve via `nix flake metadata github:NixOS/nixpkgs/ac62194c3917 --json | jq -r .revision`); `llm-agents` = current HEAD rev of `github:numtide/llm-agents.nix` (resolve via `nix flake metadata`).
- Do NOT enable the numtide binary cache (decision doc flag 4: source builds / default cache only). If `claude-code` from llm-agents.nix is an unfree binary requiring nonfree allowance, use `nixpkgs-host`'s existing global `allowUnfree = true` (already in configuration.nix).

---

### Task 1: hosts/core + pinned inputs + nixosConfigurations.core

**Files:**
- Create: `hosts/core/default.nix` (system: boot, networking, locale, GNOME, pipewire, printing, user, firefox, allowUnfree, stateVersion — translated from `/etc/nixos/configuration.nix`)
- Create: `hosts/core/hardware-configuration.nix` (byte-for-byte copy of `/etc/nixos/hardware-configuration.nix`)
- Create: `hosts/core/agent-prereqs.nix` (from ai-bootstrap: nix settings, bubblewrap/socat/git/nodejs, vhost_vsock, pcscd, kvm group, claude-code — now from the `llm-agents` input)
- Create: `hosts/core/graphics.nix` (the NVIDIA block from ai-bootstrap, verbatim)
- Create: `hosts/core/proton-backup.nix` (Proton packages + `services.restic.backups.proton-drive` block from ai-bootstrap, verbatim)
- Modify: `flake.nix` (inputs `nixpkgs-host`, `llm-agents`; `nixosConfigurations.core`; `checks.host-core`)

**Interfaces:**
- Produces: `nixosConfigurations.core` built from `nixpkgs-host` with modules `hosts/core/*` plus `self.nixosModules.basketStore` and `self.nixosModules.egressBroker` (imported with no instances — foundations only, zero runtime footprint). `checks.host-core` = `nixosConfigurations.core.config.system.build.toplevel`. Task 2 consumes both.

- [ ] **Step 1: Add inputs and resolve pins**

In `flake.nix`:

```nix
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/34ab99075ac4f7e40cf037eef32cb1c360bb85e9";
    nixpkgs-host.url = "github:NixOS/nixpkgs/<FULL-REV-OF-ac62194c3917>";
    llm-agents.url = "github:numtide/llm-agents.nix/<FULL-REV-OF-CURRENT-HEAD>";
    llm-agents.inputs.nixpkgs.follows = "nixpkgs-host";
  };
```

(Resolve both full revs with `nix flake metadata ... --json | jq -r .revision` first; substitute literally; update the outputs function args to `{ self, nixpkgs, nixpkgs-host, llm-agents }`. Verify the `follows` actually exists in llm-agents' inputs before relying on it; if its nixpkgs input is named differently, adjust and record the deviation.)

- [ ] **Step 2: Write the hosts/core modules** — faithful translation with EXACTLY these intentional deltas, nothing more:

1. `networking.hostName = "core"` (was `"nixos"`; the brief names this machine core).
2. `claude-code` comes from `llm-agents` packages for the host system (e.g. `inputs.llm-agents.packages.${pkgs.system}.claude-code`, passed via `specialArgs` or a module argument) — the `<nixos-unstable>` channel import and its `allowUnfreePredicate` wrapper are GONE from the flake world.
3. The three ai-bootstrap concerns split into the three files named above (content otherwise verbatim).
4. Everything else in `configuration.nix` — bootloader, networkmanager, timezone, locale block, X11+GDM+GNOME, xkb, printing, pipewire block, user `dalhaka` (groups networkmanager+wheel), firefox, `nixpkgs.config.allowUnfree = true`, `system.stateVersion = "25.05"` — copied faithfully into `hosts/core/default.nix`.

`hosts/core/default.nix` skeleton:

```nix
{ pkgs, ... }:
{
  imports = [
    ./hardware-configuration.nix
    ./agent-prereqs.nix
    ./graphics.nix
    ./proton-backup.nix
  ];
  # ... translated configuration.nix content, per the delta list ...
}
```

- [ ] **Step 3: Wire the system into `flake.nix`**

```nix
      nixosConfigurations.core = nixpkgs-host.lib.nixosSystem {
        system = "x86_64-linux";
        specialArgs = {
          claude-code-pkg = llm-agents.packages.x86_64-linux.claude-code;
        };
        modules = [
          ./hosts/core
          self.nixosModules.basketStore
          self.nixosModules.egressBroker
        ];
      };
```

and `checks.${system}.host-core = self.nixosConfigurations.core.config.system.build.toplevel;`

- [ ] **Step 4: Red→green** — `nix flake check` fails before the files exist, passes after. Expect a LONG first build (GNOME closure from the host pin). Lint clean.

- [ ] **Step 5: Commit** — `phase4a: hosts/core — system absorbed at running-rev pin`

---

### Task 2: Migration acceptance — closure diff + switch runbook

**Files:**
- Create: `tests/acceptance/phase4a.sh`
- Create: `docs/runbooks/phase4a-switch.md`
- Modify: `README.md` (status), `docs/OPERATIONS.md` (Lane A rows)

**Interfaces:**
- Consumes: `nixosConfigurations.core`, `checks.host-core`.
- Produces: an acceptance script that builds the flake system and shows the operator a reviewable delta versus the RUNNING system; the switch itself is an operator step in the runbook, never run by the factory.

- [ ] **Step 1: Write `tests/acceptance/phase4a.sh`**

```bash
#!/usr/bin/env bash
# Phase 4a acceptance: the machine's config builds from the repo, and the
# difference against the currently-running system is small and reviewable.
# The actual switch is YOUR step, in docs/runbooks/phase4a-switch.md.
# Run from the repo root: nix develop -c tests/acceptance/phase4a.sh
set -euo pipefail

pass=0
fail=0
ok() {
  echo "   PASS: $1"
  pass=$((pass + 1))
}
bad() {
  echo "   FAIL: $1"
  fail=$((fail + 1))
}

echo "== 1. the whole machine builds from the repo"
if out=$(nix build --no-link --print-out-paths .#nixosConfigurations.core.config.system.build.toplevel); then
  ok "nixosConfigurations.core builds ($out)"
else
  bad "flake build of the system failed"
  echo "== Result: $pass passed, $fail failed"
  echo "PHASE 4A ACCEPTANCE: FAIL"
  exit 1
fi

echo
echo "== 2. delta versus the system you are running right now"
nix store diff-closures /run/current-system "$out" | tee /tmp/phase4a-diff.txt
echo
lines=$(wc -l </tmp/phase4a-diff.txt)
echo "   ($lines change lines — review them above; hostname nixos->core and the"
echo "    claude-code source change are expected, big desktop-stack churn is NOT)"
ok "closure diff produced for operator review"

echo
echo "== 3. /etc/nixos untouched"
if [ -f /etc/nixos/configuration.nix ] && [ -f /etc/nixos/ai-bootstrap.nix ]; then
  ok "fallback config preserved at /etc/nixos"
else
  bad "/etc/nixos files missing"
fi

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "PHASE 4A ACCEPTANCE (build+diff): PASS — the switch itself is your call:"
  echo "  see docs/runbooks/phase4a-switch.md"
else
  echo "PHASE 4A ACCEPTANCE: FAIL"
  exit 1
fi
```

- [ ] **Step 2: Run it** — no sudo needed for build+diff; the factory runs it and requires PASS with a sane diff (record the diff line count and its highlights in the task report).

- [ ] **Step 3: Write `docs/runbooks/phase4a-switch.md`** — operator-facing:

```markdown
# Phase 4a — switching the machine onto the repo

After the acceptance script shows a clean diff, the switch is:

    sudo nixos-rebuild switch --flake ~/nixos-agent-env#core

From then on this repo IS the machine's configuration; /etc/nixos stays as a
frozen fallback. If anything is wrong after the switch: reboot and pick the
previous generation in the boot menu (nothing is deleted), or run
`sudo nixos-rebuild switch --rollback`, and tell Claude.

Sanity after switching: `basket doctor` all green, monitors still lit
(the NVIDIA config traveled into the repo), `systemctl status
restic-backups-proton-drive.timer` active, hostname now `core`.
```

- [ ] **Step 4: README status + board** — Phase 4a implemented; awaiting operator switch.

- [ ] **Step 5: Full verification + commit** — `nix flake check` green (now including host-core); Phase 1–3 suites green; commit `phase4a: migration acceptance + switch runbook (test: build + closure diff)`.

---

## Verification (whole phase)

1. `nix flake check` green including `host-core`.
2. `nix develop -c tests/acceptance/phase4a.sh` → PASS with a reviewed diff (factory runs this; the diff must not contain unexplained desktop-stack churn).
3. Phase 1–3 regressions green.
4. Operator: reviews the diff, runs the switch from the runbook, then `basket doctor` green and hostname `core` — that is the Phase 4a gate.
