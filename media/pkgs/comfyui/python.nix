# The Python environment ComfyUI runs in: the host's own nixpkgs python3
# with packageOverrides swapping torch/torchvision/torchaudio for their
# `-bin` variants (the pin's prebuilt CUDA 12.8 wheels, sm_120-capable,
# matching driver 570.195.03 — see
# docs/research-2026-09-02-comfyui-tag-selection.md "Why this route"),
# the plan's seven hash-pinned wheels the pin lacks (plus seven more
# comfyui-workflow-templates now hard-requires in its own dist-info — see
# deps/comfyui-workflow-templates.nix's header for why those weren't in
# the plan's own pins table), and an `av` override to 17.0.1. Every
# dependent (torchsde, kornia, spandrel, comfy-kitchen…) resolves
# through this one overridden package set, so the source (CPU-only) torch
# never enters the environment: two `torch` derivations would otherwise
# collide on `site-packages/torch`, and whichever won would silently
# decide whether CUDA works. `checks.comfyui-package` is the proof this
# rule held: `torch.version.cuda == "12.8"` (the pin's source torch
# reports `None`, since it is CPU-only there).
#
# Every non-torch addition here is a `py3-none-any` wheel except three
# compiled exceptions — `av` (the plan's one accepted sdist-with-cython
# override, linked against FFmpeg 8.1.2 from deps/ffmpeg-8-headless.nix —
# av>=17.0.0 moved the PyAV FFmpeg floor to 8.0, see deps/av.nix),
# `comfy-angle` (ANGLE's libEGL/libGLESv2 for nodes_glsl.py), and
# `comfy-aimdo` (the native aimdo.so cp39-abi3 wheel) — see those
# deps/*.nix files. Nothing here fetches at runtime; every source is
# `fetchPypi` with an SRI hash pinned in the corresponding deps/*.nix file.
{ pkgs }:
let
  py = pkgs.python3.override {
    packageOverrides = self: super: {
      torch = super.torch-bin;
      torchvision = super.torchvision-bin;
      torchaudio = super.torchaudio-bin;
      # Build-time-only Cython for the av override below (av 15.1.0 needs
      # >=3.1, the pin only has 3.0.12 — see deps/cython-for-av.nix). Not
      # listed in py.withPackages: it never enters the runtime environment.
      cythonForAv = self.callPackage ./deps/cython-for-av.nix { };
      # av 17.0.1 links FFmpeg 8.1.2 (the pin only ships 7.1.1, below
      # PyAV 17's "8.0 or higher" floor) — deps/ffmpeg-8-headless.nix
      # builds it with the pin's own generic.nix, passed here explicitly
      # because it is a system package, not a python one, so callPackage
      # cannot resolve it from the overridden python set.
      av = self.callPackage ./deps/av.nix {
        inherit (super) av;
        inherit (self) cythonForAv;
        ffmpeg-8-headless = pkgs.callPackage ./deps/ffmpeg-8-headless.nix { };
      };
      comfyui-frontend-package = self.callPackage ./deps/comfyui-frontend-package.nix { };
      comfyui-workflow-templates = self.callPackage ./deps/comfyui-workflow-templates.nix { };
      # Sibling data wheels comfyui-workflow-templates 0.11.54 hard-requires
      # (its own METADATA, not the plan's pins table) — see that file's
      # header comment.
      comfyui-workflow-templates-core = self.callPackage ./deps/comfyui-workflow-templates-core.nix { };
      comfyui-workflow-templates-media-api =
        self.callPackage ./deps/comfyui-workflow-templates-media-api.nix
          { };
      comfyui-workflow-templates-media-video =
        self.callPackage ./deps/comfyui-workflow-templates-media-video.nix
          { };
      comfyui-workflow-templates-media-image =
        self.callPackage ./deps/comfyui-workflow-templates-media-image.nix
          { };
      comfyui-workflow-templates-media-other =
        self.callPackage ./deps/comfyui-workflow-templates-media-other.nix
          { };
      comfyui-workflow-templates-json = self.callPackage ./deps/comfyui-workflow-templates-json.nix { };
      comfyui-workflow-templates-media-assets-01 =
        self.callPackage ./deps/comfyui-workflow-templates-media-assets-01.nix
          { };
      comfyui-embedded-docs = self.callPackage ./deps/comfyui-embedded-docs.nix { };
      comfy-kitchen = self.callPackage ./deps/comfy-kitchen.nix { };
      comfy-aimdo = self.callPackage ./deps/comfy-aimdo.nix { };
      comfy-angle = self.callPackage ./deps/comfy-angle.nix { };
      spandrel = self.callPackage ./deps/spandrel.nix { };
    };
  };
in
py.withPackages (
  ps: with ps; [
    torch
    torchvision
    torchaudio
    torchsde
    numpy
    einops
    transformers
    tokenizers
    sentencepiece
    safetensors
    aiohttp
    yarl
    pyyaml
    pillow
    scipy
    tqdm
    psutil
    alembic
    sqlalchemy
    filelock
    av
    comfy-kitchen
    comfy-aimdo
    comfy-angle
    requests
    simpleeval
    blake3
    kornia
    spandrel
    pydantic
    pydantic-settings
    pyopengl
    soundfile
    comfyui-frontend-package
    comfyui-workflow-templates
    comfyui-embedded-docs
  ]
)
