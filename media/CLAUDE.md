# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`media/` is the Generation subsystem's subtree of this repo, absorbed by
`git subtree add --prefix=media` on 2026-09-17 (GN11/GN12; `docs/board/log-2026-09.md`).
It is **not** a flake: there is no `media/flake.nix` or lock, the `media` input
is gone from the root `flake.lock`, and its five packages (`media/packages.nix`)
and 26 checks (`media/checks.nix`) are outputs of the root flake, built against
`nixpkgs-host` (`flake.nix:6`, `flake.nix:4781-4794`). Ownership is the
Generation row of `docs/ledger/subsystems.toml` (`prefix = "GN"`,
`owns = [ "media/*" ]`). The sibling `~/flakes/media` is the pre-absorption
working copy, kept only until the operator retires it — never build or edit
there.

The host `core` runs LIVE from this repo. Build-only: never `sudo`,
`nixos-rebuild`, `systemctl start/stop/restart`, `podman`, or writes outside the
repo — the operator switches and runs the acceptance scripts.

Design: `media/docs/superpowers/specs/2026-09-02-media-flake-design-rev3.md`
(rev 3.1, nix-native, no container) supersedes the architecture of
`docs/superpowers/specs/2026-09-02-media-flake-design.md` (rev 2, container);
the worlds are `media/docs/superpowers/specs/2026-09-05-comfy-worlds-design.md`.
Plans: the Generation row's `plans` list — most under `docs/superpowers/plans/`,
plus `media/docs/superpowers/plans/2026-09-05-comfy-worlds.md`. Board of record:
the repo root's `docs/OPERATIONS.md`, and it is **derived**
(`evidence tasks write-board`; its own header reads "nothing here is typed") —
the narrative goes in `docs/board/log-2026-09.md`.
`media/docs/OPERATIONS.md` is the pre-absorption board, frozen history.

## Commands

Run every command from the repo root. `media/githooks/pre-commit` is a
pre-absorption leftover — it lints only this subtree and is not wired to
`.git/hooks`; it survives as an input `media-lint` shellchecks.

```bash
nix develop -c githooks/pre-commit                              # the lint gate; its treefmt/statix/deadnix sweeps cover media/
nix build .#checks.x86_64-linux.media-lint -L --no-link         # this subtree's sandboxed lint arm (media/treefmt.toml + oxlint)
nix build .#checks.x86_64-linux.comfy-worlds-unit -L --no-link  # one media check (all 26 names: docs/MAP.md)
nix develop -c git commit -F <msgfile>                          # commits go through the devShell so the hook has its tools
```

`git add` new files before any `nix build` (flakes only see tracked files);
statix rejects `{ ... }:` module headers — write `_:`; `media/packages.nix` and
`media/checks.nix` are both functions of the consuming flake's `pkgs`
(`pkgsHost`) — the subtree has no nixpkgs and no pin of its own to keep. Every
privileged or network-opening behaviour is a named switch, off by default
(`mkEnableOption` / `default = false`), with a build-time assertion and a
negative check (`media/checks.nix`: `comfyui-assertion-negative-*`,
`comfy-worlds-assertion-negative-*`, `local-model-assertion-negative-*`).
This file is published (`docs/ledger/publish.toml`): keep home paths and the
operator's name out of it.

## How work is done

The root `CLAUDE.md`'s house rules, unchanged — nothing about `media/` differs.
Models per role are fixed in `docs/ledger/routing.toml` and the subsystem's
`gate` field, not named here.
