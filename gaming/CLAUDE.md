# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A standalone NixOS library flake (`~/flakes/gaming`) consumed by the operator's
host flake `~/nixos-agent-env` as a pinned `git+file://` input. This
folder is a **builder**: sessions opened here get their own Claude memory
(separate from every other flake, never shared or linked —
`~/nixos-agent-env/docs/decisions/2026-09-02-memory-per-flake.md`). The
host itself runs live from `~/nixos-agent-env`; nothing here is ever
activated directly. Build-only: never `sudo`, `nixos-rebuild`, `systemctl
start/stop`, `podman`, or writes outside this repo.

Design: `~/nixos-agent-env/docs/superpowers/specs/2026-09-02-gaming-flake-design.md`
(read-only from here). Board: `docs/OPERATIONS.md` in this repo — update it
every turn. Plans: `docs/superpowers/plans/`.

## Commands

```bash
nix develop -c githooks/pre-commit      # the lint gate (treefmt, shellcheck, statix, deadnix)
nix flake check -L                      # every check
nix build .#checks.x86_64-linux.<name> -L --no-link   # one check (list: nix flake show)
nix develop -c git commit -F <msgfile>  # commits go through the devShell so the hook has its tools
```

`git add` new files before any `nix build` (flakes only see tracked
files); statix rejects `{ ... }:` module headers — write `_:`; the module
must use the consuming host's `pkgs`, never this flake's own nixpkgs;
`inputs.nixpkgs` stays at the host pin `ac62194c…`. Every privileged or
network-opening behaviour is a named switch, off by default, with a
build-time assertion and a negative check.

## How work is done

The same house rules as the base flake (`~/nixos-agent-env/CLAUDE.md`):
phase gates the operator passes by running acceptance scripts; agents write
and review code through `~/nixos-agent-env/tools/factory/dark-factory.js`
(Fable plans, Sonnet builds, Opus gates); TDD, autolint every turn, exact
pins, no secrets in the repo, one concept per turn in `docs/concepts/`.
Terse reports; gloss tool names in plain words; decisions and risks at the
end of a turn.
