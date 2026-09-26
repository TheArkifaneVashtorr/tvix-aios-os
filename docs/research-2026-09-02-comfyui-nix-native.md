# Research digest 2026-09-02 — nix-native ComfyUI packaging routes (community flake vs nixpkgs vs own)

*Read-only research by a Sonnet agent, 2026-09-02 late, against the host pin nixpkgs ac62194c. Feeds the media flake design rev 3 (nix-native, no container).*

## Findings 1-5

### 1. `github:utensils/comfyui-nix` (flake pinned at rev `9c0c693afe7e355b69fdc73dc0b28a628426a814`, lastModified 2026-08-... just before "today")
- `nix flake metadata` shows its own `nixpkgs` input is `nixos-unstable` at rev `c0b0e0fddf73fd517c3471e546c0df87a42d53f4` (lastModified 1766902085) — a *different, newer* nixpkgs than the host's `ac62194c…` pin.
- `nix flake show` (x86_64-linux): `packages` = `comfyui, cuda, rocm, xpu, default, dockerImage*` ; `nixosModules.default` exists; `overlays.default` exists; `apps` include `default, update, cuda, rocm, xpu, buildDocker*`. `default` and `comfyui` both resolve to the same derivation, name `comfy-ui-0.34.0`.
- Torch: **prebuilt wheels fetched by hash at build time**, not compiled. `nix/versions.nix` pins Linux x86_64 to **CUDA 13.0**: `torch 2.10.0+cu130`, `torchvision 0.25.0+cu130`, `torchaudio 2.10.0+cu130`. Dry-run derivations confirm nvcc 13.0.88, cublas 13.1.0.3, cudnn 9.13.0.50_cuda13. README states architecture coverage "Turing through Blackwell (RTX 50 series)" — Blackwell covers sm_120 but the string "sm_120" itself is not used verbatim.
- ComfyUI pinned rev `12d5279438bfefc058a269eae805ceab6047777f`, version **0.34.0** (versions.nix, dated 2026-08-26). Note: the flake's own `description` field says "ComfyUI v0.30.0" — that field is stale; trust `versions.nix`, not the metadata description.
- Runtime network: custom nodes are fetched via `fetchFromGitHub` pinned by rev+hash at **build time** (`nix/custom-nodes.nix`, e.g. impact-pack, rgthree-comfy, kjnodes, wanvideo, pulid, etc. — all copied into `$out`, no runtime clone). ComfyUI-Manager is bundled but gated: it "requires the `--enable-manager` flag to activate" — off by default. One caveat: a bundled custom node, `src/custom_nodes/model_downloader`, registers HTTP API endpoints (`/model-downloader/download`) that *do* make outbound requests — only when a client hits that endpoint (UI-triggered), not on a background timer — but since the operator wants zero runtime network reach, this node should be disabled via `COMFY_SKIP_BUNDLED_NODES=1` or the module's `bundledCustomNodes = false`.
- CLI/module: package accepts `--base-directory PATH` (models/output/input/custom_nodes live under it, default `~/.config/comfy-ui`), `--listen` (default localhost-only), `--port` (default 8188), `--open` for auto-launch (omit to stay headless). It ships a full **NixOS module** (`nixosModules.default`) with `services.comfyui.{enable, port, listenAddress, dataDir, gpuSupport(cuda/rocm/xpu/none), package, cudaCapabilities, extraPythonPackages, user, group, createUser, customNodes, bundledCustomNodes, enableManager, extraArgs, environment, requiresMounts, openFirewall}`, plus built-in systemd hardening (ProtectSystem, ProtectHome, namespace isolation, GPU device groups) — directly usable for the operator's hardened-service goal.
- Binary cache: `flake.nix` declares `nixConfig.extra-substituters = [https://comfyui.cachix.org, https://nix-community.cachix.org, https://cuda-maintainers.cachix.org]`. Because our sandbox does not trust untrusted flake config, `nix build --dry-run github:utensils/comfyui-nix#cuda` (not accepting flake config) reported **870 derivations to build locally** and **1291 paths fetched (2.2GB download / 10GB unpacked)** — i.e. without opting into those cachix caches, this is a large local build (full CUDA 13 toolkit pieces included). With `--accept-flake-config` and the caches trusted, most of that would likely be substituted instead — unverified here (would require accepting a third-party cache, out of scope for a read-only check).
- License/unfree: no `allowUnfree` mentioned in README; CUDA builds normally need `nixpkgs.config.cudaSupport`/`allowUnfree = true` as usual on NixOS. Bundled custom nodes carry GPL-3.0/AGPL-3.0 licenses; the flake itself is MIT.

### 2. nixpkgs `comfyui`
- **It now exists.** `nix eval --raw github:NixOS/nixpkgs/nixos-unstable#comfyui.version` → `0.34.1`, `src.url` = `Comfy-Org/ComfyUI` tag `v0.34.1`, `meta.license` = GPL-3.0-only.
- Package (`pkgs/by-name/co/comfyui/package.nix`): torch obtained via `prev.torch.override { cudaPackages = cudaPackages_13; }` — this is nixpkgs's regular (source-buildable) `torch`, not `torch-bin`, overridden onto CUDA 13; it does **not** wire in model-path or custom-node config (`extra_model_paths.yaml` is left to the user/module), and the wrapper only unsets `NIX_PYTHONPATH`/`PYTHONPATH` — no base-dir/listen/port defaults baked in.
- A **NixOS module does exist**: `nixos/modules/module-list.nix` → `./services/misc/comfyui.nix`. Options: `services.comfyui.{enable, package, dataDir, listen, port, extraArgs}`. Hardening: static `User/Group = comfyui`, `ProtectSystem=strict`, `PrivateHome=tmpfs`, `PrivateUsers=true`, `PrivateTmp=true`, `ProtectProc=invisible`, `PrivateDevices=false` (needed for GPU), `RestrictAddressFamilies=[AF_INET AF_INET6 AF_UNIX]`, `NoNewPrivileges`, `RestrictNamespaces`, `SystemCallFilter=@system-service`. **PrivateNetwork is not set** — compatible with putting the unit in an external network namespace via systemd's `NetworkNamespacePath=`/slice, but the module itself doesn't isolate networking.
- Cost of a second pin: nixos-unstable here is on CUDA 13 (cudnn 9.13, cublas 13.1) — a second, newer nixpkgs closure would duplicate a full CUDA 13 toolkit + torch build next to the host's existing cu128 torch-bin closure (large disk, and torch here is a source build unless Hydra already cached this exact `cudaPackages_13` override, which is unverified).

### 3. Own packaging at host pin `ac62194c…`
- ComfyUI `v0.34.1` `requirements.txt` (fetched raw, same tag nixpkgs pins) lists: `torch, torchsde, torchvision, torchaudio, numpy, einops, transformers, tokenizers, sentencepiece, safetensors, aiohttp, yarl, pyyaml, Pillow, scipy, tqdm, psutil, alembic, SQLAlchemy, filelock, av, comfy-kitchen, comfy-aimdo, requests, simpleeval, blake3, kornia, spandrel, pydantic, pydantic-settings, PyOpenGL, comfy-angle`, plus `comfyui-frontend-package`, `comfyui-workflow-templates`, `comfyui-embedded-docs`.
- Checked against host pin's `python3Packages`: **present** — `torchvision-bin, torchaudio-bin, einops, transformers, safetensors, aiohttp, kornia, av, soundfile, alembic, sqlalchemy, pydantic, yarl, psutil, tqdm, scipy, pillow, sentencepiece, tokenizers`. **missing** — `spandrel, comfyui-frontend-package, comfyui-workflow-templates, comfyui-embedded-docs` (all 4 are ComfyUI-specific PyPI packages; none are exotic/compiled, all pure-Python wheels).
- Also unverified at host pin: `torchsde`, `comfy-kitchen`, `comfy-aimdo`, `comfy-angle`, `simpleeval`, `blake3`, `filelock`, `pydantic-settings`, `PyOpenGL` (not checked in this pass — likely present for the common ones like `filelock`/`PyOpenGL`/`blake3`, but `comfy-kitchen`/`comfy-aimdo`/`comfy-angle` are new/obscure Comfy-Org packages worth a follow-up check).
- **Effort estimate: small-to-medium.** The bulk of requirements.txt already resolves at the host pin; the gap is ~4-8 pure-Python `fetchPypi`-able packages (comfyui-frontend-package etc. are prebuilt wheels on PyPI, no compilation) plus writing the ComfyUI package derivation itself (source fetch + wrapper + a `--base-directory`-oriented systemd unit). This is materially less work than standing up a second CUDA-13 nixpkgs closure.

### 4. Native support versions
- **Wan 2.2**: "Day-0" native ComfyUI support announced (blog.comfy.org, "Wan2.2 Day-0 Support in ComfyUI") around the model's July 2025 release; later native FLF2V and WAN2.2-Animate support added in subsequent releases. No extra packages beyond ComfyUI's own `requirements.txt` (torch/torchvision/torchaudio cover it).
- **Z-Image**: native ("Day-0") support per blog.comfy.org "Z-Image Day-0 support in ComfyUI"; per a third-party changelog summary this landed around **ComfyUI v0.3.75** (Nov 2025). No extra dependencies noted.
- **ACE-Step**: native support exists (comfyui.org: "ComfyUI Now Supports ACE-Step!"), but neither the announcement nor docs.comfy.org's ACE-Step tutorial states an exact version number — it just says "make sure ComfyUI is updated." No additional Python packages are documented beyond the standard requirements (`torchaudio`, `av` are already in requirements.txt, which covers ACE-Step's audio I/O).

### 5. Headless systemd operation
- Bind/port: `--listen <addr>` / `--port <n>` (default listen is localhost-only, port 8188).
- Base dir: `--base-directory PATH` is the single flag that relocates models/input/output/user/custom_nodes together (comfyui-nix README); nixpkgs's module exposes this as `services.comfyui.dataDir`.
- Auto-launch: simply omit `--open` (no flag needed to suppress it; it's opt-in, not opt-out).
- Files outside base dir: not fully enumerated in the sources fetched — flag as **unknown**: verify empirically whether ComfyUI (or its dependencies, e.g. `~/.cache/huggingface`, `~/.triton`, matplotlib cache, or `/tmp`) writes outside `--base-directory` before finalizing `ProtectSystem=strict` + `ReadWritePaths=`. Both the comfyui-nix and nixpkgs NixOS modules already encode close approximations of the hardening the operator wants (static user, ProtectSystem=strict, etc.), which is a strong starting point.

## Recommendation
Given the operator's constraints, start with **`github:utensils/comfyui-nix` pinned at rev `9c0c693afe7e355b69fdc73dc0b28a628426a814`** (ComfyUI 0.34.0, rev `12d5279…`) and its `nixosModules.default`, rather than nixpkgs' own `comfyui` (which would need a second, CUDA-13, largely-uncached nixpkgs closure just for this one package) or a from-scratch package (small-medium effort, but duplicates work this flake already did, including its 20+ pinned custom nodes). Before adopting it as-is: (a) resolve the CUDA-13/driver-570 mismatch — CUDA 13.0 wheels need driver ≥580.65.06 per NVIDIA docs, while the host runs 570.195.03, so the RTX 5090 will not initialize until the driver is upgraded or an alternate cu128 build path is confirmed to exist in the flake; (b) explicitly disable Manager (leave off `--enable-manager`) and the bundled `model_downloader` node (`COMFY_SKIP_BUNDLED_NODES=1` or `bundledCustomNodes = false`) to close its runtime HTTP download endpoints; (c) decide whether to trust `comfyui.cachix.org`/`nix-community.cachix.org` (large local build otherwise: 870 derivations / 2.2GB+ in this environment's dry run) — a supply-chain tradeoff to make deliberately, not by default; (d) wrap the module's unit with the operator's egress-broker network namespace since the module itself does not set `PrivateNetwork`.

## Risks / unknowns
- CUDA 13.0 driver-version requirement (≥580.65.06) vs host driver 570.195.03 — **not yet confirmed compatible or incompatible on real hardware**, only checked against NVIDIA's published minimums.
- Whether the flake exposes any cu128/older-CUDA build path (only cu130 was found in `versions.nix` for Linux x86_64) — if not, upgrading the host driver becomes a hard prerequisite.
- Full write-path audit for `ProtectSystem=strict`/`ReadWritePaths` (item 5) was not completed — needs an actual run with `strace`/`systemd-analyze security` or file-access logging.
- `comfy-kitchen`, `comfy-aimdo`, `comfy-angle`, `torchsde` availability at the host pin unchecked.
- Cachix trust/availability not verified (no `--accept-flake-config` run performed, per read-only scope).
- ACE-Step's exact "since version X" was not found in a single authoritative changelog entry.

## Commands to verify the top 3 claims
```
# 1. CUDA13/driver mismatch — check current driver + what the flake actually requires
nvidia-smi --query-gpu=driver_version --format=csv
nix eval github:utensils/comfyui-nix#cuda.passthru.cudaPackages.cudaVersion 2>&1 || true

# 2. Manager off by default / bundled model_downloader disable path
nix run github:utensils/comfyui-nix#cuda -- --help 2>&1 | grep -iE "manager|skip-bundled"

# 3. Cachix substitution actually avoids the 870-derivation local build
nix build github:utensils/comfyui-nix#cuda --dry-run --accept-flake-config 2>&1 | grep -E "will be (built|fetched)"
```
