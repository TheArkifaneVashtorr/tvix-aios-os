# AGENTS.md — directions for the DeepSeek Harness (dsh) working here

You are DeepSeek, run by the operator through `dsh-openrouter` (the harness
on the host, see `~/nixos-agent-env/docs/runbooks/lanes.md`). Read
`CLAUDE.md` for the house rules; this file is your mission and the facts
you need. Written by the orchestrator on 2026-09-03.

## Mission

1. Get ComfyUI — `packages.comfyui`, packaged nix-native in this repo,
   built and checked but **never yet run on the GPU** — working on this
   machine for the operator: on loopback, using the RTX 5090, **without**
   any NixOS switch. The service module (`services.comfyui`) is parked;
   this is a manual run as the operator's own user.
2. Then generic automation on top of it: workflows submitted through
   ComfyUI's HTTP API (`POST /prompt`, `GET /history/<id>`, `GET /view`),
   small scripts under `tools/` here, model fetches from the manifest.

## Hard limits (same as CLAUDE.md)

- Never `sudo`, `nixos-rebuild`, `systemctl`, `podman`, or edit anything
  outside this repository. The host runs live from `~/nixos-agent-env`.
- Never fetch code at runtime; everything comes through `nix build`.
- Never commit unless asked. Before a commit: `nix develop -c
  githooks/pre-commit`; `git add` new files before any `nix build`.
- No secrets in the repo. The Hugging Face token, if ever needed, is not
  yours to read.

## Facts you will need

- `nix build .#comfyui` produces `result/bin/comfyui`, a wrapper that runs
  `python3 main.py "$@"` — every ComfyUI command-line flag works.
  `--base-directory DIR` relocates models/input/output/user (verified
  against the built 0.22.3); point it INSIDE this repo at `.local-run/`
  (gitignored), because your sandbox can write only here.
- Torch is the CUDA 12.8 prebuilt wheel; the host driver is 570. The first
  GPU run compiles kernels for minutes — that is normal.
- **Your tool sandbox has no GPU and no `/dev/nvidia*`** (measured). You
  cannot start the GPU server from a tool call. The operator starts it in
  a terminal:

      cd ~/flakes/media && nix build .#comfyui && ./result/bin/comfyui --listen 127.0.0.1 --port 8188 --disable-all-custom-nodes --base-directory "$PWD/.local-run"

  Your sandbox CAN reach loopback (measured): once the server is up, drive
  it over `http://127.0.0.1:8188`. Confirm with `curl -s
  http://127.0.0.1:8188/system_stats`.
- Models: `models/manifest.toml` (hash-verified starter set; SDXL base is
  6.9 GB). Fetch with `nix run .#media-fetch-models -- --manifest
  models/manifest.toml --dest .local-run/models --only <name>`; it verifies
  sha256 while streaming. Prefer the smallest model that proves a render.
- Minimal generation-proof workflows: `tests/acceptance/workflows/`. The
  acceptance drill `tests/acceptance/media.sh` was written for the
  service; adapt its checks for the manual run instead of running it.
- Runbook for the packaged app: `docs/runbooks/media.md`. Board:
  `docs/OPERATIONS.md` — append a dated line when something works or
  fails.

## How to report

Short. What you ran, what happened, the exact error text when something
failed, what you propose next. An unmeasured claim is not a result.
