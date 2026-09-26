---
name: nixos
description: >-
  NixOS and Nix knowledge pinned to this machine's build (nixpkgs ac62194c,
  nix 2.28.5) — options, modules, systemd units and hardening, packaging,
  activation semantics, debugging — loaded on demand by task shape, never
  all at once.
---

## Pin

- nixpkgs `ac62194c3917d5f474c1a844b6fd6da2db95077d` (NixOS 25.05), nix
  `2.28.5`, systemd `257.10`, kernel `6.12.63`.
- If `nix --version` or the flake's nixpkgs rev differs, trust the store
  over this skill and say so.

## What doc-tests prove, and what they don't

- Every example in these references is executed at the pin. That proves
  option names, types, merges, and buildability — nothing more.
- Claims about runtime and activation behaviour (units, timers, switch
  semantics, hardening) are Opus-reviewed prose plus VM-graded evals, not
  doc-tested: verify them on the machine before relying on them.

## Five rules that always apply

1. Verify an option before using it:
   `nix eval .#nixosConfigurations.<host>.options.<path>.type --offline`,
   or `nixos-option <path>`.
2. Read the module source at the pin before overriding its behaviour —
   `nixos/modules/...` under the pinned nixpkgs source.
3. Flakes see only tracked files: `git add` new or changed files before
   `nix build` or `nix flake check`.
4. Prefer build-time assertions (the `assertions` list) to runtime checks.
5. Never guess a hash — obtain it: the fake-hash build loop,
   `nix hash path`, or `nix-prefetch-url`.

## Task → files

| task shape | files | read when |
| --- | --- | --- |
| reading or writing any Nix expression | `nix-language` | syntax, laziness, scoping, eval errors |
| touching flake inputs/outputs/lock | `flakes` | `follows`, lock semantics, tracked-files gotcha |
| writing or reviewing a module | `module-system`, `nix-language` | options, priorities, merges |
| invoking `nix` (build/eval/store/GC) | `nix-cli` | flags, `nix develop -c`, roots |
| starting a flake/module from scratch | `flakes`, `module-system`, `nix-language` | full picture |
| adding a unit, timer, or drop-in | `systemd-units`, `module-system` | PATH, templates, tmpfiles |
| hardened service, new options | `module-system`, `systemd-units`, `systemd-hardening` | sandbox |
| service in a netns or with a polkit rule | `systemd-hardening`, `security` | netns, polkit |
| reasoning about a switch or specialisation | `activation-and-switch` | restart/reload, snapshots |
| firewall, wrapper, or user/group change | `security` | chains, wrappers, uids |
| packaging or overriding software | `packaging` | phases, hashes, override forms |
| package a Python tool with CUDA | `packaging`, `python-and-cuda` | torch-bin, driver, 32-bit |
| VM test with a negative proof | `vm-tests`, `module-system` | testScript, node config |
| any eval/build/exec failure | `debugging` | traces, sandbox, IFD, nix-ld |
| looking for "the option for X" | `nixos-options-map` | subsystem → prefix → module |
| before committing anything | `gotchas` | traps spanning more than one reference |
| reviewing a NixOS change (Opus gate) | `review-checklist` | ordered defect checklist |
| verifying a build or switch | `verify` | build, closure diff, activation diff |
| the pin moved | `refresh` | bump lock, fix failures, re-stamp, re-eval |

## Role entries

- **Implementing a plan task:** read this router, then the task's
  `skillRefs` files; with no `skillRefs`, pick from the table above using
  the task's title and spec text. Name the files you read in your report.
- **Reviewing code (Opus gate):** `review-checklist` + `gotchas`.
- **Reviewing a runbook or plan:** `nix-cli` + `activation-and-switch`.
- **Verifying:** `verify`.
