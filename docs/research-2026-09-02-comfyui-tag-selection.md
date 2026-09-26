# Research digest 2026-09-02 — ComfyUI tag selection and pins for packaging at the host pin

*Read-only research by a Sonnet agent, 2026-09-02 late, against the host pin nixpkgs ac62194c. Feeds the media flake design rev 3 (nix-native, no container).*

## Chosen tag T and why

**T = ComfyUI v0.22.3** (tag commit `7c47f4db5b9bc8c8cc0923c74392a111c858d539`, tagged 2026-05-27).

Candidate table (newest→oldest examined, `requirements.txt` per tag):

| Tag | Date | av | comfy-kitchen | comfy-aimdo |
|---|---|---|---|---|
| v0.34.1 | 2026-08-26 | `>=17.0.0` | `==0.2.31` | `==0.4.15` |
| v0.30.0–v0.33.4 | 2026-08-03…08-26 | `>=16.0.0` | `0.2.26–0.2.31` | `0.4.11–0.4.13` |
| v0.23.0–v0.29.2 | 2026-06-01…07-28 | `>=16.0.0` | `==0.2.10–0.2.22` | `0.4.7–0.4.10` |
| **v0.22.3** | **2026-05-27** | **`>=14.2.0`** | **`>=0.2.8`** | **`==0.3.0`** |
| v0.20.0–v0.22.0 | 2026-04-27…05-20 | `>=14.2.0` | `>=0.2.8` | `0.2.14 / 0.3.0` |

v0.23.0 is the break point: it jumps `av` to `>=16.0.0` in the same commit that pins `comfy-kitchen==0.2.10` exactly and `comfy-aimdo==0.4.7` (from `0.3.0` — a real API bump). So v0.22.3 is the newest tag on the `av<15` / `aimdo==0.3.0` side of that line.

- **(a) av:** host ffmpeg at the pin is `7.1.1` (`nix eval --raw github:NixOS/nixpkgs/ac62194c…#ffmpeg.version` → `7.1.1`). PyAV's own changelog for **v14.3.0** says "Uses ffmpeg 7.1.1, fixes deadlocks" (its bundled-wheel build target), and **v15.1.0**'s changelog adds "Support FFmpeg 8" as a new *feature* (additive, not a floor change) — so ffmpeg 7.1.1 is inside PyAV 14.x/15.x's supported range. `av==15.1.0` satisfies T's `av>=14.2.0` and should build from source against the pin's ffmpeg 7.1.1.
- **(b) comfy-kitchen / comfy-aimdo:** Both packages publish a `py3-none-any` wheel **for every release**, alongside compiled `cp3xx-manylinux` wheels (verified via PyPI's per-file listing for both). comfy-kitchen's PyPI summary is "Fast Kernel Library for ComfyUI with multiple compute backends" — the pure wheel is almost certainly a Python/torch-dispatch fallback path, not a stub. This means nix packaging can select `py3-none-any` and avoid a compiled-CUDA-kernel dependency entirely (see Risks).
- **(c) torch floor:** T's `README.md` states "torch 2.4 and above is supported"; `comfy/model_management.py` gates optimizations with `torch_version_numeric >= (2,7)`, `>= (2,5)`, `< (2,10)`, `< (2,3)` — torch 2.7.0 satisfies every gate cleanly (hits the `>=2.7` fast paths).
- **(d) native nodes at T:** `comfy_extras/nodes_ace.py` (ACE-Step, `TextEncodeAceStepAudio` confirmed), `comfy_extras/nodes_wan.py` + `comfy/ldm/wan/`, `comfy_extras/nodes_zimage.py` + `comfy/ldm/lumina/` (Z-Image appears to reuse/extend the Lumina2 backbone — `nodes_lumina2.py` sits alongside it), SDXL support is long-standing and untouched. **Caveat:** I could not string-match "2.2"/"TI2V"/"5B" inside `nodes_wan.py` itself — Wan variant selection is likely driven generically by the checkpoint's own config rather than hardcoded node names, but this is inferred, not directly confirmed (see Risks).
- **(e) av not needed above 15:** confirmed — only v0.20.0 through v0.22.3 sit in the `av>=14.2.0` band; v0.23.0 onward requires `av>=16.0.0`, which is >15.x and would force `av==16.x`/`17.x` (no 15.x satisfies it).

## Pins for the plan

**ComfyUI**
- Tag: `v0.22.3`, git rev: `7c47f4db5b9bc8c8cc0923c74392a111c858d539`
- `fetchFromGitHub` unpacked hash (via `nix-prefetch-url --unpack https://github.com/Comfy-Org/ComfyUI/archive/refs/tags/v0.22.3.tar.gz`): `1wf1c82f1fhimrk1kqy8gs44gqf47x703j6rdcjhn5396ia57rqa` (nix32 form — convert with `nix hash to-sri --type sha256 <hash>` for the `hash = "sha256-..."` attribute).

**Missing pure-Python packages (all `py3-none-any`)**

| Package | Version (from T) | Wheel | sha256 |
|---|---|---|---|
| comfyui-frontend-package | 1.43.18 | `comfyui_frontend_package-1.43.18-py3-none-any.whl` | `bb2727f129ccaac2f44552ae538519e2c865a4ccc1a4bd7133467a5628153b0a` |
| comfyui-workflow-templates | 0.9.85 | `comfyui_workflow_templates-0.9.85-py3-none-any.whl` | `777e13488e730ea0e57c59b9a63af19e5a7dc41000ae5d9876e74f4ac8c4fb42` |
| comfyui-embedded-docs | 0.5.0 | `comfyui_embedded_docs-0.5.0-py3-none-any.whl` | `87d831bb39f99a9dacc546f8ad9504634d026ec90759919bc843eecfefde877f` |
| spandrel | 0.4.2 (latest on PyPI; T leaves it unpinned under "non essential") | — | (grab per pip; not version-critical) |

**comfy-kitchen / comfy-aimdo (pick `py3-none-any` to dodge the compiled-CUDA-ABI question)**

| Package | Version | Wheel | sha256 |
|---|---|---|---|
| comfy-kitchen | **0.2.10** (T's floor is `>=0.2.8`; I recommend 0.2.10 because v0.23.0 — the very next release — pins `==0.2.10` exactly, i.e. upstream itself validated 0.2.8→0.2.10 as compatible) | `comfy_kitchen-0.2.10-py3-none-any.whl` | `c242afd18d120e28fc949c423fa28cbb22cb4d70d627d8cc7cdf6bad54dd272c` |
| comfy-aimdo | **0.3.0** (T pins this exactly) | `comfy_aimdo-0.3.0-py3-none-any.whl` | `cecf7bfa38a5929027d8d9abb3f0d0fa21aec47c6c97f4539a7365f72e54819e` |

**av**
- Version: `av==15.1.0` (latest 15.x; satisfies T's `av>=14.2.0`)
- sdist: `av-15.1.0.tar.gz`, sha256 `39cda2dc810e11c1938f8cb5759c41d6b630550236b3365790e67a313660ec85`
- Build deps (`pyproject.toml [build-system]`): `setuptools>=77.0`, `cython>=3.1.0a1,<4`
- Needs to link against nixpkgs' `ffmpeg` (7.1.1 at the pin) plus its `-dev` outputs (libavcodec/format/util/swscale/swresample).

## Flags and write paths at T

Confirmed present in `comfy/cli_args.py`: `--base-directory`, `--listen`, `--port`, `--disable-all-custom-nodes`, `--cpu`, `--dont-print-server`, `--disable-auto-launch`, plus `--user-directory`, `--output-directory`, `--input-directory`, `--temp-directory` (each documented as "Overrides --base-directory").

Auto-launch is **opt-in**: `main.py` only calls `webbrowser.open(...)` `if args.auto_launch:` — default is off, no flag needed to suppress it.

Write paths: `--database-url` defaults to `sqlite:///<repo>/../user/comfyui.db`, i.e. inside the standard `user/` dir under `--base-directory` — no escape. Grepping `folder_paths.py`/`main.py` for `expanduser`/`.cache`/`tempfile`/`Path.home()` found nothing — no direct writes outside the base-directory tree from those two files. (Not exhaustively checked across every module — e.g. HF/torch hub caches used by model downloads are governed by `HF_HOME`/`XDG_CACHE_HOME` env vars, not ComfyUI code, so set those explicitly in the service unit.)

## GPU access facts

- ffmpeg at the pin: `7.1.1`.
- `pkgs/development/python-modules/torch/bin/default.nix` at the pin lists `addDriverRunpath`, `autoAddDriverRunpath`, and `autoPatchelfHook` in its build inputs — torch-bin patches its own ELF binaries to add the driver runpath. **No manual `LD_LIBRARY_PATH` is needed**, provided `hardware.graphics.enable = true;` is set (populates `/run/opengl-driver/lib`).
- `nixos/modules/hardware/video/nvidia.nix` creates `/dev/nvidiactl`, `/dev/nvidia$i`, `/dev/nvidia-modeset`, `/dev/nvidia-uvm`, `/dev/nvidia-uvm-tools` via udev `mknod -m 666 ...` — **mode 0666**, so a service user needs no special group membership.
- For a hardened systemd unit with `PrivateDevices=false`, add `DeviceAllow=char-nvidia rw` (or explicit `/dev/nvidia*`, `/dev/nvidiactl`, `/dev/nvidia-uvm*` entries) to keep the 0666 nodes reachable under the cgroup device filter.

## Risks / unknowns

1. **comfy-kitchen/aimdo `py3-none-any` functional completeness unverified.** I confirmed the wheel exists for both packages at every version but did not install/import it to confirm it doesn't hard-fail without the compiled backend (e.g. via a runtime `ImportError` gate). Treat as "very likely functional but performance-degraded fallback" until smoke-tested.
2. **Wan 2.2 5B TI2V support at T not string-confirmed** — `nodes_wan.py` had no literal "2.2"/"TI2V"/"5B" text; variant handling is likely config-driven from the checkpoint, but this needs a manual read of `comfy/ldm/wan/model.py` or a live test with a Wan 2.2 checkpoint.
3. **comfy-kitchen `>=0.2.8` is an open floor** — I recommend 0.2.10 (validated by upstream's own next pin) rather than the bare 0.2.8 minimum, but neither is what T's CI actually ran against at release time (unknown, since it's a floor not a lock).
4. **av 15.1.0 built from source against ffmpeg 7.1.1 is inferred compatible from changelog text, not build-tested.**
5. T is roughly 3 months and ~12 tags behind `v0.34.1` — missing frontend/workflow-template UI features and any node additions/fixes landed since (e.g. later Wan/Z-Image refinements) in exchange for the simpler dependency story.

## Commands the operator could run to verify the top 3 claims

```bash
# 1. av<=15 satisfies T's floor, and ffmpeg matches PyAV's stated build target
curl -s https://raw.githubusercontent.com/Comfy-Org/ComfyUI/v0.22.3/requirements.txt | grep '^av'
nix eval --raw github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d#ffmpeg.version

# 2. comfy-kitchen / comfy-aimdo ship a pure-Python wheel at the pinned versions
curl -s https://pypi.org/pypi/comfy-kitchen/0.2.10/json | grep -o '"filename":"[^"]*py3-none-any[^"]*"'
curl -s https://pypi.org/pypi/comfy-aimdo/0.3.0/json   | grep -o '"filename":"[^"]*py3-none-any[^"]*"'

# 3. torch-bin at the pin self-wires the Nvidia driver runpath (no manual LD_LIBRARY_PATH)
curl -s https://raw.githubusercontent.com/NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d/pkgs/development/python-modules/torch/bin/default.nix \
  | grep -E 'addDriverRunpath|autoAddDriverRunpath'
```
