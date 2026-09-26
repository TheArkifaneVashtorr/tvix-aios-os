# Phase 3 — Classification Assertions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Basket classifications become Nix-declared, single-source-of-truth; a config that mounts a `local-only` basket into any network-capable agent **fails to evaluate** with a clear error; `basket doctor` turns the host-invariant probes into a runnable PASS/FAIL table.

**Architecture:** `nixosModules/basketStore.nix` declares `services.baskets.definitions.<id>` (classification/mount/access — the runtime manifest JSONs are *generated* from these, so Nix is the source of truth and the Phase 1 CLI schema is the contract) and `services.baskets.agents.<name>` (baskets + egress + placement). Module-system assertions enforce the invariant at eval time. `lib/mkAgent.nix` is a thin constructor over the agents option. Negative testing uses `builtins.tryEval` around a deliberately-bad `nixosSystem` (NixOS assertions surface as `throw`, which `tryEval` catches); the operator acceptance additionally proves the error *message* is clear via the CLI. `basket doctor` probes take an overridable root prefix so bats can fabricate failing hosts.

**Tech Stack:** NixOS module system assertions, `pkgs.formats.json`, bats, existing basket CLI.

**Spec:** design doc §2.2 + §3, brief §5.2 + §7 Phase 3, concepts `2026-09-02-invariant-preflight` and `2026-09-02d-environment-parity-ladder`.

## Global Constraints

- All Phase 1 and Phase 2 Global Constraints apply unchanged (pins, no secrets, lint gates, `nix develop -c git commit`, trailers, set -e discipline, never push).
- Commit messages: `phase3: <task summary>`.
- Classification values exactly `local-only`, `redacted`, `permitted`; access `ro`/`rw` — identical to the Phase 1 manifest schema, enforced by generating manifests and validating them with the existing `basket validate-manifest`.
- Assertion error messages must name the agent, the basket, and the rule — an operator reading the error must not need this repo's docs to understand it.
- `basket doctor` never requires root; probes that need root-only data degrade to `WARN unknown`, never fake a PASS.

---

### Task 1: basketStore module — definitions, agents, generated manifests, assertions

**Files:**
- Create: `nixosModules/basketStore.nix`
- Modify: `flake.nix` (export `nixosModules.basketStore`; add checks `assertion-positive`, `assertion-negative`, `manifests-validate`; add `nixosConfigurations.phase3-negative-demo`)

**Interfaces:**
- Produces: options `services.baskets.definitions.<id> = { classification (enum local-only|redacted|permitted); mount (str, absolute); access (enum ro|rw, default "ro"); }` and `services.baskets.agents.<name> = { baskets (listOf str); egress (str, "none" or "broker:<instance>", default "none"); placement (enum host|microvm|bubblewrap, default "bubblewrap"); }`. Read-only output `config.services.baskets.manifestsPackage` — a derivation containing `<id>.json` per definition in exactly the Phase 1 manifest schema. Assertions (eval-time failures): (A1) every agent basket id exists in definitions; (A2) **an agent whose egress is not "none" must not list any `local-only` basket** — message format below; (A3) egress "broker:<x>" requires `services.egress-broker.instances.<x>` to exist; (A4) one agent's baskets must have pairwise-distinct mount paths. Tasks 2–4 consume these option paths verbatim.

- [ ] **Step 1: Write the failing checks first** — in `flake.nix` add (they fail to evaluate until the module exists):

```nix
        assertion-positive =
          (nixpkgs.lib.nixosSystem {
            inherit system;
            modules = [
              self.nixosModules.basketStore
              self.nixosModules.egressBroker
              (
                _: {
                  boot.loader.grub.enable = false;
                  fileSystems."/".device = "none";
                  fileSystems."/".fsType = "tmpfs";
                  system.stateVersion = "25.11";
                  services.egress-broker.instances.work = {
                    hostAddress = "10.100.0.1";
                    namespaceAddress = "10.100.0.2";
                    allow = [ "example.com" ];
                  };
                  services.baskets.definitions = {
                    notes-local = {
                      classification = "local-only";
                      mount = "/data/notes";
                    };
                    workspace = {
                      classification = "permitted";
                      mount = "/data/workspace";
                      access = "rw";
                    };
                  };
                  services.baskets.agents = {
                    offline-agent = {
                      baskets = [
                        "notes-local"
                        "workspace"
                      ];
                      egress = "none";
                    };
                    online-agent = {
                      baskets = [ "workspace" ];
                      egress = "broker:work";
                    };
                  };
                }
              )
            ];
          }).config.system.build.toplevel;

        assertion-negative =
          let
            bad = nixpkgs.lib.nixosSystem {
              inherit system;
              modules = [
                self.nixosModules.basketStore
                self.nixosModules.egressBroker
                (
                  _: {
                    boot.loader.grub.enable = false;
                    fileSystems."/".device = "none";
                    fileSystems."/".fsType = "tmpfs";
                    system.stateVersion = "25.11";
                    services.egress-broker.instances.work = {
                      hostAddress = "10.100.0.1";
                      namespaceAddress = "10.100.0.2";
                      allow = [ "example.com" ];
                    };
                    services.baskets.definitions.notes-local = {
                      classification = "local-only";
                      mount = "/data/notes";
                    };
                    services.baskets.agents.leaky = {
                      baskets = [ "notes-local" ];
                      egress = "broker:work";
                    };
                  }
                )
              ];
            };
            attempt = builtins.tryEval (bad.config.system.build.toplevel.drvPath);
          in
          if attempt.success then
            throw "assertion-negative: a local-only basket reached a network-capable agent and the build DID NOT FAIL"
          else
            pkgs.runCommand "assertion-negative-ok" { } "touch $out";

        manifests-validate =
          let
            demo =
              (nixpkgs.lib.nixosSystem {
                inherit system;
                modules = [
                  self.nixosModules.basketStore
                  (
                    _: {
                      boot.loader.grub.enable = false;
                      fileSystems."/".device = "none";
                      fileSystems."/".fsType = "tmpfs";
                      system.stateVersion = "25.11";
                      services.baskets.definitions.demo = {
                        classification = "redacted";
                        mount = "/data/demo";
                      };
                    }
                  )
                ];
              }).config.services.baskets.manifestsPackage;
          in
          pkgs.runCommand "manifests-validate" { nativeBuildInputs = [ basket ]; } ''
            for f in ${demo}/*.json; do
              basket validate-manifest "$f"
            done
            touch $out
          '';
```

Also expose the bad system for the operator, but **NOT under `nixosConfigurations`** — `nix flake check` force-evaluates every nixosConfiguration's toplevel, so a deliberately-throwing one there would fail every future check run. Instead: factor the bad `nixosSystem` call into a `let` binding (`phase3BadSystem`) used by BOTH the `assertion-negative` check and a custom top-level output `phase3NegativeDemo = phase3BadSystem;` (unknown flake outputs only produce a warning and are not deep-evaluated). The acceptance script builds `.#phase3NegativeDemo.config.system.build.toplevel` to show the operator the real error text.

- [ ] **Step 2: Run to verify red** — `nix flake check` → fails (no `nixosModules.basketStore`).

- [ ] **Step 3: Implement the module** — `nixosModules/basketStore.nix`:

```nix
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.baskets;
  jsonFormat = pkgs.formats.json { };
  agentBasketPairs = lib.flatten (
    lib.mapAttrsToList (agent: a: map (b: { inherit agent; basket = b; }) a.baskets) cfg.agents
  );
in
{
  options.services.baskets = {
    definitions = lib.mkOption {
      default = { };
      description = "Basket declarations — the single source of truth for classification.";
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            classification = lib.mkOption {
              type = lib.types.enum [
                "local-only"
                "redacted"
                "permitted"
              ];
            };
            mount = lib.mkOption { type = lib.types.str; };
            access = lib.mkOption {
              type = lib.types.enum [
                "ro"
                "rw"
              ];
              default = "ro";
            };
          };
        }
      );
    };
    agents = lib.mkOption {
      default = { };
      description = "Agent declarations: which baskets they mount and how they egress.";
      type = lib.types.attrsOf (
        lib.types.submodule {
          options = {
            baskets = lib.mkOption {
              type = lib.types.listOf lib.types.str;
              default = [ ];
            };
            egress = lib.mkOption {
              type = lib.types.str;
              default = "none";
              description = ''"none", or "broker:<instance>" naming a services.egress-broker instance.'';
            };
            placement = lib.mkOption {
              type = lib.types.enum [
                "host"
                "microvm"
                "bubblewrap"
              ];
              default = "bubblewrap";
            };
          };
        }
      );
    };
    manifestsPackage = lib.mkOption {
      type = lib.types.package;
      readOnly = true;
      description = "Generated Phase 1 manifest JSONs, one per basket definition.";
    };
  };

  config = {
    services.baskets.manifestsPackage = pkgs.linkFarm "basket-manifests" (
      lib.mapAttrsToList (id: d: {
        name = "${id}.json";
        path = jsonFormat.generate "${id}.json" {
          inherit id;
          inherit (d) classification mount access;
        };
      }) cfg.definitions
    );

    assertions =
      # A1: referenced baskets exist
      map (p: {
        assertion = cfg.definitions ? ${p.basket};
        message = "basket agent '${p.agent}' references basket '${p.basket}', which has no services.baskets.definitions entry";
      }) agentBasketPairs
      # A2: the invariant — local-only never reaches a network-capable agent
      ++ map (p: {
        assertion =
          (cfg.agents.${p.agent}.egress == "none")
          || !(cfg.definitions ? ${p.basket})
          || cfg.definitions.${p.basket}.classification != "local-only";
        message = "agent '${p.agent}' has egress '${cfg.agents.${p.agent}.egress}' but mounts local-only basket '${p.basket}' — local-only baskets may only be mounted into agents with no off-box route (invariant: brief section 3.1/5.2)";
      }) agentBasketPairs
      # A3: named broker instances exist
      ++ lib.mapAttrsToList (agent: a: {
        assertion =
          a.egress == "none"
          || (
            lib.hasPrefix "broker:" a.egress
            && config.services.egress-broker.instances ? ${lib.removePrefix "broker:" a.egress}
          );
        message = "agent '${agent}' egress '${a.egress}' is neither \"none\" nor \"broker:<instance>\" naming an existing services.egress-broker instance";
      }) cfg.agents
      # A4: mount paths unique within one agent
      ++ lib.mapAttrsToList (agent: a: {
        assertion =
          let
            mounts = map (b: cfg.definitions.${b}.mount) (
              lib.filter (b: cfg.definitions ? ${b}) a.baskets
            );
          in
          lib.length mounts == lib.length (lib.unique mounts);
        message = "agent '${agent}' mounts two baskets at the same path — mount points must be unique per agent";
      }) cfg.agents;
  };
}
```

- [ ] **Step 4: Green + lint** — `nix flake check` → all checks green including the three new ones. `nix develop -c treefmt`, statix/deadnix clean.

- [ ] **Step 5: Commit** — `phase3: basketStore module — Nix-declared classifications + eval-time invariant assertions`

---

### Task 2: lib/mkAgent.nix constructor

**Files:**
- Create: `lib/mkAgent.nix`
- Modify: `flake.nix` (expose `lib.mkAgent`; rewrite the `assertion-positive` check's agents via mkAgent to prove the path)

**Interfaces:**
- Produces: `mkAgent { name, baskets, egress ? "none", placement ? "bubblewrap" }` → an attrset `{ services.baskets.agents.<name> = {...}; }` mergeable as a NixOS module fragment. Later phases extend it per harness; nothing else changes.

- [ ] **Step 1: Write it**

```nix
{
  name,
  baskets,
  egress ? "none",
  placement ? "bubblewrap",
}:
{
  services.baskets.agents.${name} = {
    inherit baskets egress placement;
  };
}
```

Expose in `flake.nix` outputs: `lib.mkAgent = import ./lib/mkAgent.nix;`.

- [ ] **Step 2: Prove it** — change `assertion-positive`'s two agent declarations to use `(self.lib.mkAgent { name = "offline-agent"; baskets = [ "notes-local" "workspace" ]; })` and `(self.lib.mkAgent { name = "online-agent"; baskets = [ "workspace" ]; egress = "broker:work"; })` as extra modules in its module list (drop the inline `services.baskets.agents` block). `nix flake check` stays green — mkAgent output is a working module.

- [ ] **Step 3: Lint + commit** — `phase3: lib/mkAgent constructor`

---

### Task 3: basket doctor

**Files:**
- Modify: `pkgs/basket/basket.sh` (add `cmd_doctor`, wire `doctor)` case arm; extend `usage`)
- Create: `tests/unit/50-doctor.bats`

**Interfaces:**
- Produces: `basket doctor [--root <prefix>]` — probes host invariants, prints one `PASS`/`FAIL`/`WARN` line each, exits 1 iff any FAIL. `--root` (default `/`) prefixes every probed path so tests fabricate hosts. Probes: `swap` (FAIL if `<root>/proc/swaps` lists any swap device), `pcscd` (socket `<root>/run/pcscd/pcscd.comm` exists; WARN if absent), `age-plugin` (age-plugin-yubikey on PATH), `kvm` (`<root>/dev/kvm` exists), `vsock` (`<root>/sys/module/vhost_vsock` exists), `stale-mounts` (any entry under `<root>/run/baskets/`; FAIL — decrypted material may be lingering).

- [ ] **Step 1: Write the failing tests** — `tests/unit/50-doctor.bats`:

```bash
#!/usr/bin/env bats

setup() {
  cd "$BATS_TEST_TMPDIR"
  mkdir -p root/proc root/run root/dev root/sys
  printf 'Filename\tType\tSize\tUsed\tPriority\n' >root/proc/swaps
}

@test "doctor passes on a clean fabricated host" {
  mkdir -p root/run/pcscd root/sys/module/vhost_vsock
  touch root/run/pcscd/pcscd.comm root/dev/kvm
  run basket doctor --root root
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS"* ]]
  [[ "$output" != *"FAIL"* ]]
}

@test "doctor fails when swap is active" {
  mkdir -p root/run/pcscd root/sys/module/vhost_vsock
  touch root/run/pcscd/pcscd.comm root/dev/kvm
  printf '/dev/sda2\tpartition\t8388604\t0\t-2\n' >>root/proc/swaps
  run basket doctor --root root
  [ "$status" -eq 1 ]
  [[ "$output" == *"FAIL"*"swap"* ]]
}

@test "doctor fails on stale basket mounts" {
  mkdir -p root/run/pcscd root/sys/module/vhost_vsock root/run/baskets/leftover
  touch root/run/pcscd/pcscd.comm root/dev/kvm
  run basket doctor --root root
  [ "$status" -eq 1 ]
  [[ "$output" == *"FAIL"*"stale"* ]]
}

@test "doctor warns but does not fail when pcscd is absent" {
  mkdir -p root/sys/module/vhost_vsock
  touch root/dev/kvm
  run basket doctor --root root
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARN"*"pcscd"* ]]
}
```

- [ ] **Step 2: Red** — `nix develop -c bats tests/unit/50-doctor.bats` → FAIL (unknown command).

- [ ] **Step 3: Implement** — add to `basket.sh`:

```bash
cmd_doctor() {
  local root="/"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --root)
        root="$2"
        shift 2
        ;;
      *) die "doctor: unknown arg $1" ;;
    esac
  done
  root="${root%/}"
  local failed=0
  probe() {
    local verdict="$1" name="$2" detail="$3"
    printf '%-4s %-12s %s\n' "$verdict" "$name" "$detail"
    if [[ "$verdict" == "FAIL" ]]; then
      failed=1
    fi
  }
  if [[ -f "$root/proc/swaps" ]] && [[ "$(wc -l <"$root/proc/swaps")" -gt 1 ]]; then
    probe FAIL swap "swap is active — tmpfs pages could reach disk (invariant 1)"
  else
    probe PASS swap "no active swap"
  fi
  if [[ -e "$root/run/pcscd/pcscd.comm" ]]; then
    probe PASS pcscd "smartcard daemon socket present"
  else
    probe WARN pcscd "pcscd socket absent — YubiKey decryption will fail"
  fi
  if command -v age-plugin-yubikey >/dev/null; then
    probe PASS age-plugin "age-plugin-yubikey on PATH"
  else
    probe WARN age-plugin "age-plugin-yubikey not on PATH for this process"
  fi
  if [[ -e "$root/dev/kvm" ]]; then
    probe PASS kvm "/dev/kvm present"
  else
    probe WARN kvm "/dev/kvm absent — Cowork and microvms unavailable"
  fi
  if [[ -d "$root/sys/module/vhost_vsock" ]]; then
    probe PASS vsock "vhost_vsock loaded"
  else
    probe WARN vsock "vhost_vsock not loaded"
  fi
  if [[ -d "$root/run/baskets" ]] && [[ -n "$(ls -A "$root/run/baskets" 2>/dev/null)" ]]; then
    probe FAIL stale-mounts "entries under /run/baskets — decrypted material may linger (run basket teardown)"
  else
    probe PASS stale-mounts "no leftover basket mounts"
  fi
  [[ "$failed" -eq 0 ]] || exit 1
}
```

Wire `doctor)` in `main` (shift, `cmd_doctor "$@"`), add the line `  doctor [--root <prefix>]` to `usage`.

- [ ] **Step 4: Green** — bats file passes; full `nix flake check` green (new bats file runs in the sandboxed unit check — probes read only fabricated roots, and PATH/WARN probes never FAIL there).

- [ ] **Step 5: Lint + commit** — `phase3: basket doctor — host invariant probes`

---

### Task 4: Acceptance script + runbook

**Files:**
- Create: `tests/acceptance/phase3.sh`
- Create: `docs/runbooks/phase3-acceptance.md`
- Modify: `README.md` (status), `docs/OPERATIONS.md` (Lane A → Phase 3 rows)

**Interfaces:**
- Consumes: `phase3NegativeDemo` (custom output), `checks.assertion-positive`, `basket doctor`.
- Produces: brief §7 Phase 3 acceptance — no sudo, no hardware.

- [ ] **Step 1: Write `tests/acceptance/phase3.sh`**

```bash
#!/usr/bin/env bash
# Phase 3 acceptance (brief §7): a config mounting a local-only basket into a
# network-capable agent fails the build with a clear error; a correct config
# builds; basket doctor reports live host invariants.
# Run from the repo root: nix develop -c tests/acceptance/phase3.sh
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

echo "== 1. a correct config builds"
if nix build --no-link .#checks.x86_64-linux.assertion-positive; then
  ok "config with local-only basket on an offline agent evaluates and builds"
else
  bad "the known-good config failed to build"
fi

echo
echo "== 2. the forbidden config REFUSES to build, with a clear error"
set +e
err=$(nix build --no-link \
  .#phase3NegativeDemo.config.system.build.toplevel 2>&1)
status=$?
set -e
if [[ "$status" -ne 0 && "$err" == *"local-only"* && "$err" == *"leaky"* && "$err" == *"notes-local"* ]]; then
  ok "build failed and the error names the agent, the basket, and the rule"
  echo "--- the error an operator sees:"
  grep -A2 "local-only" <<<"$err" | head -5
else
  bad "expected a failing build naming agent/basket/rule; status=$status"
  echo "$err" | tail -5
fi

echo
echo "== 3. basket doctor on this host"
if basket doctor; then
  ok "doctor probes all green (WARNs acceptable)"
else
  bad "doctor reports a FAILing invariant on this host"
fi

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "PHASE 3 ACCEPTANCE: PASS"
else
  echo "PHASE 3 ACCEPTANCE: FAIL"
  exit 1
fi
```

- [ ] **Step 2: Static-verify + live-run** — shellcheck clean, then actually run it (`nix develop -c tests/acceptance/phase3.sh`) — unlike Phases 1–2 it needs no sudo/hardware, so the factory itself must see it PASS before handing it over.

- [ ] **Step 3: Runbook** — `docs/runbooks/phase3-acceptance.md`: one command, plain-language: "proves the system refuses to even build a configuration that would let private data reach anything with network access; then health-checks this machine's invariants."

- [ ] **Step 4: README status + OPERATIONS.md Lane A** — Phase 3 implemented, awaiting operator acceptance.

- [ ] **Step 5: Full verification + commit** — `nix flake check` all green; Phase 1+2 suites untouched-green; commit `phase3: operator acceptance (test: brief §7 Phase 3)`.

---

## Verification (whole phase)

1. `nix flake check` → all checks green (lint, unit incl. doctor, addon, module-eval, integration, assertion-positive, assertion-negative, manifests-validate).
2. `nix develop -c tests/acceptance/phase3.sh` → PASS (factory runs this one itself).
3. Phase 1+2 regression: `bats tests/unit`, `tests/run-mount-tests.sh`, `pytest tests/broker -q` all green.
4. Operator re-runs the acceptance script and confirms the error text reads clearly.
