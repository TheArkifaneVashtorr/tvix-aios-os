# Opus gate — M1 (media flake, ComfyUI v0.34.3 + Krea-2 manifest)

Branch `task/M1` @ `f699d37`, clone `/home/dalhaka/factory/ws/m1/M1`.
Verified in throwaway worktrees; clone and real repo untouched (`git status` clean, worktrees removed).

## Verdict: APPROVE — conditional on one amend-only fix (board line)

Every load-bearing claim in the commit message re-derived independently. No correctness defect found.

## Evidence

**1. Pin is really v0.34.3.** `pkgs/comfyui/package.nix:83` rev `87465b8f1f64a27a46f16f22b13b410494dca66d`.
GitHub `git/ref/tags/v0.34.3` → same sha (lightweight tag). Operator's venv `git -C ~/comfyui-krea2 rev-parse HEAD` = same sha, `git describe --tags` = `v0.34.3`. `comfyanonymous/ComfyUI` 301-redirects to `Comfy-Org/ComfyUI` (repo id 589831718) — the owner field is correct.

**2. Source hash is real.** Independent `nix-prefetch-url --unpack .../87465b8f….tar.gz` → `0lws2sn5dv6qpxvllqp90wlh6l30rxzi9j7dhkmrzr60yhhj1fsq` → SRI `sha256-WLsgIfTA5J/rhO3IFH/PYFADKQfpYkp3v9jsVqwWmlM=` = `package.nix:84` exactly.

**3. Manifest hashes — three-way match.** `models/manifest.toml:156,166`.
| file | HF LFS `oid` | manifest | operator sha256sum | size |
|---|---|---|---|---|
| `text_encoders/qwen3vl_4b_bf16.safetensors` | 36f3ff44…4e34 | = | = | 8875719384 = |
| `vae/qwen_image_vae.safetensors` | a70580f0…3d1f | = | = | 253806246 = |
Operator's copies hashed in place, never moved. HF API confirms `gated:false`, `license_name: krea-2-community-license` — matches the manifest verbatim. No dest/name collisions across the 12 entries.

**4. Torch overrides survive.** torch/torchvision/torchaudio `.drv` paths byte-identical base↔branch (`q234869n…-torch-2.7.0.drv`, `g80a0nii…`, `a49cn11l…`); wheel src is `download.pytorch.org/whl/cu128/torch-2.7.0+cu128-cp312-…whl`. Python-env input diff is exactly av 15.1.0→17.0.1 plus the comfy* wheel bumps and the two new template siblings — nothing else moved.

**5. All checks green.** `nix flake check -L` at branch head: "running 12 flake checks…", EXIT=0 (incl. `lint` and the VM test). VM log proves the real pin ran: `ComfyUI version: 0.34.3`, assets route still 503, `comfy_angle` GLSL node skips with a warning exactly as `package.nix:26-32` predicts.

**6. No new impurity.** Zero hits for `__noChroot`, `builtins.fetchurl`, `fetchTarball`, `builtins.getEnv`, `--impure`, `impureEnvVars` across `*.nix`. Every new source is a fixed-output `fetchPypi`/`fetchgit`/`fetchFromGitHub` with an SRI hash — and `nix build .#comfyui` succeeding is itself proof each of those hashes is correct (incl. the FFmpeg 8.1.2 fetchgit hash at `deps/ffmpeg-8-headless.nix:53`). `nix build .#comfyui` → `/nix/store/bqkhs10psk1wii4dsb3lh2jcvbnz11aj-comfyui-0.34.3`.

## Mutation table

| # | mutation | expected | observed |
|---|---|---|---|
| 1 | new check applied to the **pre-bump tree** (0.22.3, `HEAD~1`) | red | **RED**, exit 1 — `AssertionError: CLIPLoader type does not contain krea2: ['stable_diffusion', …, 'cogvideox']`. Imports and node graph loaded fine, so it failed for the right reason, not a collateral break. |
| 2 | branch head, assertion `"krea2"` → `"krea2ZZZ"` | red | **RED** — error dump shows the real list *does* contain `krea2` (`…'boogu', 'krea2', 'joyimage'…`). Assertion is live, not vacuous. |
| 3 | source hash re-derived from scratch (stronger than a wrong-hash rebuild) | match | exact SRI match |
| 4 | base vs branch python-env `.drv` reference diff | torch untouched | torch trio identical |

## Findings (non-blocking except F1)

- **F1 (must fix, amend-only).** `docs/OPERATIONS.md` is untouched. `CLAUDE.md` ("Board: docs/OPERATIONS.md — update it every turn") and `AGENTS.md` ("append a dated line when something works or fails") both require it. Append the dated line, `--amend`.
- **F2 (nit, judgement).** Commit carries `Generated-By: dsh 0.1.2-rc.1 / deepseek-v4-pro-0813` but no `Co-Authored-By:` trailer; the eight prior commits all carry `Co-Authored-By: Claude Fable 5.1`. For a dsh-authored commit `Generated-By` is arguably the honest analogue — orchestrator's call. Also `(test: …)` omits `lint`, which prior comparable commit `8d62a82` listed and which does cover the README/docs edits here.
- **F3 (comment inaccuracy).** `pkgs/comfyui/deps/av.nix:52` — "av >= 13 dropped the `av.bytesource` module" is wrong. Measured: `av-15.1.0` store path still ships `bytesource.cpython-312…so`; `av-17.0.1` does not. The filter on line 54 is necessary and correct; only the reason is misdated.
- **F4 (comment inconsistency).** `package.nix:8` says "annotated-tag object → commit", `package.nix:38` says "lightweight tag → commit". GitHub returns `object.type: "commit"` — line 38 is right, line 8 is wrong.
- **F5 (stale comment).** `pkgs/comfyui/python.nix:47` still reads "comfyui-workflow-templates 0.9.85 hard-requires"; it is 0.11.54 now (`deps/comfyui-workflow-templates.nix:33`).
- **F6 (style).** `av.nix:40` binds `_old` and then *uses* it at line 54; the `_` prefix now misreports it as unused. Lint doesn't catch this. Rename to `old`.
- **F7 (operator note, not a defect).** `krea2-text-encoder` lands `enabled = true` at 8.9 GB, so a bare `media-fetch-models` run (no `--only`) now pulls ~9 GB more than before. Consistent with the existing SDXL/Z-Image precedent, but worth a runbook line.

## Not done / limits

Nothing was started on port 8188; no sudo, nixos-rebuild or systemctl. GPU behaviour remains unverified by construction — the VM check proves the CPU path only, which is the pre-existing and correct division of labour.
