# Generative-media flake — design rev 3.1 (2026-09-02 late): nix-native, no container

*Rev 3.1 folds in the adversarial review of rev 3 (2 Sonnet lenses, 2 blockers
+ 7 majors): device-group names for `DeviceAllow`, the torch override rule,
`/dev/shm` and Unix sockets hidden, the model directory read-only to the
serving process, `extraArgs` dropped, token-file permissions in the drill,
the VM test's closure cost stated, core download endpoints audited.*

**Supersedes** the Architecture, Module and Testing sections of rev 2.1
(docs/superpowers/specs/2026-09-02-media-flake-design.md); the Goal, the
model manifest, `media-fetch-models`, the broker credential injection, the
socket proxy and the fetch-unit confinement carry over unchanged. Decision:
docs/decisions/2026-09-02-media-nix-native-no-container.md. Research:
docs/research-2026-09-02-comfyui-nix-native.md (route) and the tag-selection
digest that follows it.

## Why this route

Both community options (utensils/comfyui-nix, nixpkgs' new `comfyui`) build
on CUDA 13, whose wheels need driver ≥ 580; `core` runs 570.195.03 at its
pin. The host pin already carries torch-bin 2.7.0+cu128 (sm_120-capable,
matches the driver), torchvision/torchaudio-bin, and every ComfyUI
requirement except six pure-Python Comfy packages, `spandrel` and a newer
`av`. Own packaging therefore means: one nixpkgs, no second CUDA closure, no
third-party binary cache, no bundled custom nodes, nothing fetched at
runtime.

## Architecture

```
operator browser ── http://localhost:8188 ──▶ comfyui-proxy.socket (127.0.0.1:8188, systemd-socket-proxyd)
                                                    │
                                                    ▼  10.100.2.2:8188 (namespace address)
   netns egress-media (egress-netns-media.service, persistent)
     ├─ comfyui.service — User=comfyui, NetworkNamespacePath, ProtectSystem=strict, DeviceAllow /dev/nvidia*,
     │    ExecStart = <store>/bin/comfyui --base-directory /var/lib/comfyui --listen 10.100.2.2 --port 8188
     │                --disable-all-custom-nodes   (flags verified at the chosen tag)
     │    HTTPS_PROXY → broker (defence in depth: nothing is expected to call out)
     └─ comfyui-fetch-models.service (unchanged from rev 2.1)
                                                    │
                                                    ▼
   egress-broker instance "media": allow = Hugging Face hosts only (no registry, no GitHub, no PyPI)
     inject."huggingface.co" (unchanged)
```

## Package `packages.comfyui` (in this flake, built with the host's `pkgs`)

- `pkgs/comfyui/package.nix`: `python3.withPackages` from the consuming
  host's nixpkgs **with `packageOverrides` mapping `torch`, `torchvision`
  and `torchaudio` to their `-bin` variants**, so every dependent (torchsde,
  kornia, spandrel, comfy-kitchen…) resolves to the prebuilt CUDA 12.8
  wheels and the source `torch` never enters the environment (two `torch`
  derivations collide on `site-packages/torch`). The proof is
  `checks.comfyui-package`: `torch.version.cuda == "12.8"` (the pin's
  source torch is CPU-only, so a leaked source torch reports `None`).
  Packages: (torch-bin, torchvision-bin, torchaudio-bin, torchsde,
  einops, transformers, tokenizers, sentencepiece, safetensors, aiohttp,
  yarl, pyyaml, pillow, scipy, tqdm, psutil, alembic, sqlalchemy, filelock,
  requests, simpleeval, blake3, kornia, pydantic, pydantic-settings,
  pyopengl, soundfile, numpy) plus the packages the pin lacks, each a
  `buildPythonPackage` from a **hash-pinned PyPI wheel or sdist**
  (`pkgs/comfyui/deps/<name>.nix`): `comfyui-frontend-package`,
  `comfyui-workflow-templates`, `comfyui-embedded-docs`, `spandrel`, and,
  only if the chosen tag needs them and they are pure Python,
  `comfy-kitchen` / `comfy-aimdo` / `comfy-angle`; and an `av` override to
  the lowest version the tag accepts that builds against the pin's ffmpeg
  (sdist + sha256, `cython` from the pin).
- ComfyUI source: `fetchFromGitHub` Comfy-Org/ComfyUI at tag **T** — the
  newest tag whose requirements are satisfiable from the pin plus the
  pure-Python wheels plus one `av` override, and which carries native
  Z-Image, Wan 2.2 and ACE-Step nodes. T, its rev and hash, and the reason
  it was chosen, are recorded at the top of `package.nix`. Compiled
  dependencies beyond `av` are not accepted — if a tag needs one, take the
  previous tag.
- Wrapper `bin/comfyui`: `exec <python> <src>/main.py "$@"` with
  `PYTHONPATH` set to the environment, no network, no downloads. No
  ComfyUI-Manager, no custom nodes directory populated; `--disable-all-custom-nodes`
  is always passed (option `allowCustomNodes` does not exist in v0).
- GPU: torch-bin at the pin resolves the driver's `libcuda` through the
  standard NixOS driver runpath (`/run/opengl-driver/lib`, provided by
  `hardware.graphics`); the plan verifies whether the derivation carries
  `autoAddDriverRunpath` and adds `LD_LIBRARY_PATH=/run/opengl-driver/lib`
  in the wrapper only if it does not.
- `checks.comfyui-package` builds the package and runs
  `comfyui --help` plus `python -c "import torch, comfy; print(torch.version.cuda)"`
  inside the build sandbox (CPU only).

## Module `services.comfyui` (rev 3)

| option | default | notes |
|---|---|---|
| `enable` | false | |
| `package` | `packages.comfyui` | |
| `user` / `group` | comfyui | system user, no shell, home = `dataDir`; **no** subuid range, no podman |
| `dataDir` | /var/lib/comfyui | `models/ input/ output/ user/ temp/ cache/` (tmpfiles, `user`, 0750) |
| `listen.address` | the broker instance's `namespaceAddress` | in-namespace bind (assertion: equals it) |
| `proxy.listen` | 127.0.0.1:8188 | host-side socket-proxy listener; assertion: loopback |
| `gpu.enable` | true | `DevicePolicy=closed` + `DeviceAllow` by **device-group name** (path globs are invalid in `DeviceAllow`): `char-nvidiactl rw`, `char-nvidia-frontend rw` (the numbered `/dev/nvidia0…`), `char-nvidia-uvm rw`, `char-nvidia-caps rw` — the set nixpkgs' own `services.ollama` uses; no modeset (compute only); asserts `hardware.nvidia.package` is set; `false` adds `--cpu` (VM tests) |
| `brokerInstance` | "media" | assertion as before |
| `models.manifest`, `models.hfTokenFile` (`str`, not store), `models.civitai.enable` | unchanged | |
| `resources.memoryMax` | "96G" | |

Unit `comfyui.service`: `User/Group`, `NetworkNamespacePath=/run/netns/egress-<i>`,
`Requires/After` the broker units, `WorkingDirectory=dataDir`,
`Environment`: `HOME=dataDir`, `XDG_CACHE_HOME=dataDir/cache`,
`TMPDIR=dataDir/temp`, `HTTPS_PROXY`/`HTTP_PROXY`=broker, `NO_PROXY`,
`SSL_CERT_FILE`=broker `ca-bundle.crt`; hardening: `ProtectSystem=strict`,
`ProtectHome=yes`, `ReadWritePaths=[ dataDir ]`, `PrivateTmp=yes`,
`NoNewPrivileges=yes`, `CapabilityBoundingSet=`, `AmbientCapabilities=`,
`RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`, `RestrictNamespaces=yes`,
`SystemCallFilter=@system-service`, `LockPersonality=yes`,
`MemoryDenyWriteExecute=no` (CUDA JIT needs it off — stated), `PrivateDevices=no`
+ `DevicePolicy=closed` + the `DeviceAllow` groups above,
`InaccessiblePaths=/dev/shm /run/dbus /run/user` (the shared `/dev` tree
and host Unix sockets are otherwise reachable under `ProtectSystem=strict`;
ComfyUI single-GPU has no use for them — the VM test proves generation
works with them hidden), `RestrictAddressFamilies=AF_INET AF_INET6` (no
AF_UNIX; if the VM test shows torch needs a local socket, re-add AF_UNIX and
record the deviation), **`ReadOnlyPaths=<dataDir>/models`** (the serving
process can read weights but never replace them — only the fetch unit
writes there; the more specific path wins over `ReadWritePaths`),
`MemoryMax`, `Nice=5`, `Restart=on-failure`, `TimeoutStartSec=10min` (first
start compiles kernels). ExecStart as in the diagram; `--cpu` when
`gpu.enable = false`. There is no `extraArgs` option in v0 (an open list
appended to ExecStart could re-enable CORS or listeners).

Removed from rev 2.1: `image.*`, `readOnlyRoot`, `wantedUid`, `extraArgs`,
`virtualisation.podman`, `hardware.nvidia-container-toolkit`,
`autoSubUidGidRange`, every podman argv assertion.

The fetch unit keeps `ReadWritePaths=<dataDir>/models` and gains
`--reverify` support in `media-fetch-models` (re-hash present files against
the manifest instead of `SKIP present`; the acceptance drill runs it).
The Hugging Face token file is read by the broker (user `egress-broker`),
never by `comfyui`: the runbook requires `0440 root:egress-broker` (or
`0400 egress-broker`), and the acceptance drill asserts the mode.

## Testing

- `checks.comfyui-package` (above).
- `checks.comfyui-eval`: ExecStart contains `--base-directory /var/lib/comfyui`,
  `--listen 10.100.2.2`, `--port 8188`, `--disable-all-custom-nodes`;
  `NetworkNamespacePath == /run/netns/egress-media`; `User == comfyui`;
  `ProtectSystem == "strict"`; the environment has `HTTPS_PROXY` and no
  `HF_TOKEN`; `DeviceAllow` lists the nvidia nodes when `gpu.enable`; the
  socket unit listens on `127.0.0.1:8188`; the inject key is
  `huggingface.co`; `virtualisation.podman.enable == false`.
- `checks.comfyui-assertion-negative-{listen,broker,token}`.
- `checks.comfyui-vm` (NixOS VM, no GPU — **note: it still ships the full
  CUDA 12.8 torch closure into the VM image, several GB; `virtualisation.
  diskSize` ≥ 16 GB and a long first run are the accepted cost**; the code
  under test is the real package, only the device is CPU): the node creates a stand-in
  namespace itself (`ip netns add egress-media`, a veth with 10.100.2.1/2 —
  no broker module needed), enables `services.comfyui` with `gpu.enable =
  false`, waits for the unit, then `curl http://127.0.0.1:8188/system_stats`
  through the socket proxy returns JSON naming the ComfyUI version and
  `cpu`; `ss -ltn` shows 8188 only on 127.0.0.1 in the host namespace; from
  inside the namespace `curl -m 5 https://example.com` fails; a POST of a
  minimal CPU-only workflow (two nodes: `EmptyImage` → `SaveImage`) to
  `/prompt` produces a PNG under `dataDir/output` — the real end-to-end
  proof without any model or GPU.
- `media-fetch-unit`, `media-fetch-bats`: unchanged.
- Operator acceptance `tests/acceptance/media.sh`: as rev 2.1 minus the
  container lines: unit active, `system_stats` names the RTX 5090 and CUDA
  12.8 torch, ownership of an output file is `comfyui`, fetch OK/SKIP with
  audit `allow` lines and no `HF_TOKEN` in `systemctl show -p Environment`,
  fail-closed proof via `nsenter --net=/run/netns/egress-media curl -m 5
  https://example.com` as `comfyui`, generation proofs (SDXL PNG, ACE-Step
  clip, Wan 2.2 5B clip).

## Security

Same user, namespace, proxy, credential injection and manifest as rev 2.1;
the container boundary is replaced by systemd hardening on a service whose
code is entirely in the read-only Nix store; no Manager, no custom nodes,
no runtime fetch of any kind; `MemoryMax`; audit lines in the broker log.
Residual: ComfyUI's own web UI runs as `comfyui` with write access to
`dataDir` only.

## Verify-first items for the plan

0. ComfyUI **core** routes at v0.22.3 with download capability (model
   library, template or example downloaders in `server.py` / `app/`):
   `--disable-all-custom-nodes` only stops `custom_nodes/`. Any such route
   can only reach the broker's Hugging Face allowlist (weights, never code)
   and is logged in the audit — but if one exists, disable it (flag or a
   one-line patch in the package) and add the route to the VM test as a
   `fail` probe.
1. The chosen tag's flags (`cli_args.py`) and its torch floor.
2. `av` override builds against the pin's ffmpeg (a `nix build` of the
   override alone, in the factory).
3. torch-bin runpath handling at the pin (`autoAddDriverRunpath`).
4. Writes outside `--base-directory` during startup (VM test with
   `ProtectSystem=strict` is the measurement; add `ReadWritePaths` only
   for paths inside `dataDir`).
5. `/dev/nvidia*` modes at the pin (0666 by udev rule) and the exact
   `DeviceAllow` set.
