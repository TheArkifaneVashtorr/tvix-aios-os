# Research digest 2026-09-02 — Generative-media stack on the RTX 5090 (image / video / music)

*Read-only research by a Sonnet agent (factory model policy), 2026-09-02 evening, against the host pin nixpkgs ac62194c and the flake pin 34ab9907. Evidence lines are the agent's own command outputs and cited URLs; "unverified" means exactly that. Feeds the Lanes G/H/I design in docs/OPERATIONS.md.*

Confirmed: none of these are packaged in nixpkgs at the host pin. I now have sufficient evidence across all 7 questions. Compiling the final report.

## Findings by question (1-7)

**1. Nixpkgs pins — ComfyUI, torch, CUDA**
- `comfyui` does not exist as an attribute at either pin. `nix eval --raw github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d#comfyui.version` → `error: ... does not provide attribute`. Same result at the `34ab9907…` pin.
- Host pin (`ac62194c…`, 2026-01-02): `python3Packages.torch.version` = `2.7.0`; `torch.cudaSupport` default = `false` (`nix eval ...#python3Packages.torch --apply 'p: p.cudaSupport'` → `false`, i.e. the default `torch` build is CPU-only, matching general nixpkgs policy). `python3Packages.torch-bin.version` = `2.7.0`, source URL `https://download.pytorch.org/whl/cu128/torch-2.7.0%2Bcu128-...whl` — bundles CUDA 12.8. PyTorch 2.7/cu128 wheels do support Blackwell/sm_120 (confirmed via web: driver 570+ and CUDA 12.8 is the documented minimum for RTX 50-series). `cudaPackages.cudaMajorMinorVersion` = `12.8`.
- Second pin (`34ab9907…`): `torch.version` = `2.12.0`; `torch-bin.version` = `2.12.1`, source URL uses `cu130` (CUDA 13.0) wheel, cp314. `cudaPackages.cudaMajorMinorVersion` = `12.9`.
- `hardware.nvidia-container-toolkit.enable` exists at the host pin: found in `nixos/modules/services/hardware/nvidia-container-toolkit/default.nix`, where it is defined as an alias `["hardware" "nvidia-container-toolkit" "enable"] → ["virtualisation" "containers" "cdi" "dynamic" "nvidia" "enable"]`.
- `podman.version` at host pin = `5.4.1` (`nix eval --raw ...#podman.version`).
- Neither pin packages any of the specific generative-AI model repos checked (`python3Packages.audiocraft`, `stable-audio-tools`, `ace-step` — all "does not provide attribute" at the host pin); this matches nixpkgs' general practice of not vendoring individual inference-model repos.

**2. Community ComfyUI Nix packaging**
- `utensils/comfyui-nix` — actively maintained (~200 commits, updates through July 2026 per GitHub). Explicitly documents "Turing through Blackwell (RTX 50 series)" support, using pre-built PyTorch wheels from pytorch.org (implying cu128+ wheels, consistent with sm_120). Manages custom nodes via a bundled set (Impact Pack, rgthree-comfy, KJNodes) auto-linked at start, plus an optional `--enable-manager` path that installs into a PEP 405 venv at `<data-dir>/.venv` (outside the Nix store) rather than rebuilding the derivation. Models/output/custom_nodes live under a configurable data directory (default `~/.config/comfy-ui` on Linux).
- `nixified-ai/flake` (and fork `adrian-gierakowski/nixified-ai-flake`) — a broader "many AI projects" flake with a PR adding ComfyUI (#94).
- `dyscorv/nix-comfyui` and `edeetee/comfyui-shell-nix` — smaller/simpler flakes, less clearly maintained.
- I did not fetch exact HEAD revs/dates for the second and third repos given the tool budget — treat `utensils/comfyui-nix` as the strongest lead and re-verify its current HEAD rev before pinning.

**3. Container route**
- `mmartial/ComfyUI-Nvidia-Docker` — supports CUDA 12.2–13.3 with PyTorch auto-selected by detected CUDA (cu128 index used for CUDA 12.8+, meeting the sm_120 requirement). Explicitly runs as a non-root `comfy` user via `WANTED_UID`/`WANTED_GID` mapping ("The container is made to run as the comfy user, NOT as root"). Models/custom_nodes live in a separate `basedir` volume mounted with `-v`, decoupled from the `run` (install) volume. No explicit digest-pinning guidance in its docs — tags like `ubuntu24_cuda12.6.3` are used; digest pinning would need to be done manually (`docker pull ...@sha256:...`).
- Other candidates surfaced by search (`igork2580/comfyui-5090`, `clasyc/comfyui`, `ChiefNakor/comfyui-blackwell-docker`) look less established/reputable (personal Docker Hub images, no clear provenance) — I would not treat these as verified without deeper vetting.
- Comfy-Org's own guidance thread ("Nvidia 50 Series (Blackwell) support thread", GitHub Discussion #6643) confirms driver 570+ and CUDA 12.8 as the baseline for 50-series.

**4. Music generation (32 GB VRAM)**
- ACE-Step: Apache-2.0 (V1); ACE-Step 1.5 XL uses MIT-style terms. Has official native ComfyUI support (docs.comfy.org/tutorials/audio/ace-step). VRAM: base ACE-Step reportedly runs under 4 GB; ACE-Step 1.5 XL wants ~20 GB+ recommended (12 GB minimum with offload) — comfortably fits 32 GB.
- Stable Audio Open, MusicGen/AudioCraft, YuE, DiffRhythm: not packaged in nixpkgs (verified for AudioCraft/stable-audio-tools above); would run standalone via pip/venv or through community ComfyUI custom nodes rather than native ComfyUI support — I did not get time to verify each one's current ComfyUI node status individually; ACE-Step is the only one confirmed to have first-party ComfyUI integration.

**5. Video generation (32 GB VRAM)**
- Wan 2.2: 5B variant runs on 6–8 GB VRAM; 14B needs 24 GB+ at fp16 for 480p/720p, dropping to ~6–8 GB with fp8 + GGUF + T5 CPU-offload. ComfyUI support via native nodes and the `ComfyUI-WanVideoWrapper` custom node. Fits 32 GB easily, including higher-quality settings.
- LTX-2 (Lightricks, 22B): official baseline is 32 GB VRAM (i.e., right at your ceiling); FP8/GGUF quantization needed for headroom. LTX-2 does synced audio+video in one pass.
- HunyuanVideo 1.5 (Tencent, 8.3B, released Nov 2025): minimum ~14 GB with offloading; can drop from 47 GB to ~8 GB with fp8/GGUF/tiling. Fits well within 32 GB with margin for higher settings.

**6. Image generation (32 GB VRAM)**
- Flux.1 dev/schnell: well-supported in ComfyUI, fits comfortably (dev is ~24 GB fp16, less with fp8/GGUF).
- Flux.2 (released, per search results): dev variant needs ~64 GB BF16 / ~32 GB FP8 / ~19 GB GGUF Q4 — at 32 GB you're at the edge and should plan on FP8 or GGUF; Klein 9B/4B distilled variants fit in 12–16 GB.
- Qwen-Image: 40 GB BF16 / 16 GB FP8 / ~14 GB GGUF Q4_K_M — fits at fp8/GGUF.
- SDXL: trivially fits (well under 16 GB).
- Z-Image Turbo: 14–16 GB BF16, 8 GB FP8, down to 6 GB GGUF — easy fit.
- All have ComfyUI support per the searched guides (Thunder Compute / LocalAIMaster 2026 posts), though I relied on secondary blog sources rather than primary ComfyUI docs for exact VRAM figures.

**7. Model download hostname allowlist**
- Per Hugging Face's own docs/forum guidance: `huggingface.co` (Hub API/metadata), Xet-protocol hosts `cas-server.xethub.hf.co` / `cas-server.xethub-eu.hf.co`, `transfer.xethub.hf.co` / `transfer.xethub-eu.hf.co`, CDN edges `us.aws.cdn.hf.co` / `us.gcp.cdn.hf.co`, and LFS CDN `cdn-lfs-us-1.hf.co` / `cdn-lfs-eu-1.hf.co`. The authoritative, currently-accurate list is published as JSON at `https://huggingface.co/.well-known/meta.json` — HF recommends generating firewall rules from that endpoint rather than hardcoding, since edge hostnames change. Wildcard note: `*.xethub.hf.co` does not cover `-eu.hf.co` hosts, and `*.cdn.hf.co` doesn't cover the two-label `us.aws.cdn.hf.co`/`us.gcp.cdn.hf.co` — enumerate explicitly if your proxy lacks multi-label wildcard support. Add `civitai.com` (and its CDN, typically `*.civitai.com` / an R2/CloudFront-backed download host — not independently verified this session) if Civitai models are in scope.

## Recommended architecture

Given that ComfyUI itself is not in nixpkgs at either pin and both `torch`/`torch-bin` at the second (`34ab9907…`) pin have moved to CUDA 12.9/13.0 with a 2.12.x torch that's ahead of what most ComfyUI custom nodes currently test against, a **hybrid** approach is the pragmatic choice: use the NixOS host (pinned to `ac62194c…`, which gives a well-trodden CUDA 12.8/PyTorch 2.7 combination known to support sm_120) purely for the substrate — driver 570.195.03, `hardware.nvidia-container-toolkit.enable = true`, and `virtualisation.oci-containers.backend = "podman"` (podman 5.4.1 available at that pin) — then run ComfyUI itself as a rootless Podman container from `mmartial/ComfyUI-Nvidia-Docker`, pinned by digest (`docker pull mmartial/comfyui-nvidia-docker:<tag>` then resolve and pin `@sha256:...`), executed as the unprivileged `comfy` user via `WANTED_UID`/`WANTED_GID` mapped to a dedicated system user, with `basedir` (models/custom_nodes/input/output) bind-mounted to a dedicated directory outside the container's writable layer and outbound network restricted at the host firewall to the HF hostname set from `.well-known/meta.json` plus civitai.com if needed. This sidesteps the churn of tracking ComfyUI + its many custom-node Python dependencies as native Nix derivations while still keeping the OS layer, GPU driver, and container runtime fully pinned and reproducible via the flake. If avoiding containers entirely is a hard requirement, `utensils/comfyui-nix` (pin its current HEAD rev) is the strongest nix-native fallback, since it already claims Blackwell support and isolates node/package installs into a venv outside the store — but expect more maintenance burden keeping pace with new models (Flux.2, Wan 2.2, LTX-2) than the container route.

## Risks / unknowns

- I did not obtain exact current HEAD commit revs/dates for `nixified-ai/flake`, `dyscorv/nix-comfyui`, or `edeetee/comfyui-shell-nix` — only for `utensils/comfyui-nix` (qualitative "updates through July 2026, ~200 commits").
- `mmartial/ComfyUI-Nvidia-Docker` docs give no first-party digest-pinning workflow; digest must be captured manually at deploy time and re-verified periodically.
- VRAM figures for Flux.2, Qwen-Image, LTX-2, HunyuanVideo 1.5 come from secondary blog aggregators (Thunder Compute, LocalAIMaster, WillItRunAI), not primary model-card or ComfyUI documentation — treat as directional, verify against the actual model cards before sizing.
- ComfyUI native/custom-node support was confirmed primarily for ACE-Step; Stable Audio Open, MusicGen/AudioCraft, YuE, and DiffRhythm's current ComfyUI integration status (native vs. third-party node vs. standalone-only) was not individually verified.
- Civitai's exact CDN hostname(s) for the allowlist were not verified this session.
- Torch's `cudaSupport` default being `false` at the host pin means if any nix-native route is chosen, the derivation must explicitly override `config.cudaSupport = true` (or use `torch-bin`) — easy to silently get a CPU-only build otherwise.

## Commands to verify the top 3 claims

```bash
# 1. Confirm comfyui absent from nixpkgs at host pin
nix eval --raw github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d#comfyui.version

# 2. Confirm torch-bin bundles CUDA 12.8 at host pin (sm_120-capable)
NIXPKGS_ALLOW_UNFREE=1 nix eval --impure --raw --expr \
  '(import (fetchTarball "https://github.com/NixOS/nixpkgs/archive/ac62194c3917d5f474c1a844b6fd6da2db95077d.tar.gz") { config.allowUnfree = true; }).python3Packages.torch-bin.src.url'

# 3. Confirm hardware.nvidia-container-toolkit.enable module option exists at host pin
HOSTPATH=$(nix eval --raw github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d#path)
grep -n 'nvidia-container-toolkit' "$HOSTPATH/nixos/modules/services/hardware/nvidia-container-toolkit/default.nix"
```
