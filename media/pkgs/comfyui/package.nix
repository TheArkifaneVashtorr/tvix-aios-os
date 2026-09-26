# ComfyUI, packaged nix-native against the host's own CUDA 12.8 torch-bin
# pin (pkgs/comfyui/python.nix) — no container, nothing fetched at
# runtime. Design: docs/superpowers/specs/2026-09-02-media-flake-design-rev3.md
# (rev 3.1). Tag selection and every wheel's pin:
# docs/research-2026-09-02-comfyui-tag-selection.md.
#
# Tag: Comfy-Org/ComfyUI v0.34.5, rev 7fd919f0caff66a52289ea5b19cb6eaca0da04ef
# (tagged 2026-09-05, lightweight tag → commit "ComfyUI v0.34.5").
# v0.34.3 first carried the `krea2` CLIPLoader type in nodes.py (CLIPLoader
# INPUT_TYPES lists `krea2` alongside qwen_image etc.) — still present, and
# load-bearing for checks.comfyui-cliploader-krea2 (red at 0.22.3, green
# only from v0.34.3). v0.34.5 is the tag whose requirements.txt this flake's
# wheel pins now track exactly; the pin-by-pin reconciliation is
# docs/research-2026-09-05-comfyui-0.34.5-bump.md.
# requirements.txt pins this flake honours:
#   - av>=17.0.0 (PyAV's FFmpeg floor is now 8.0) → deps/av.nix 17.0.1
#     linked against deps/ffmpeg-8-headless.nix (FFmpeg 8.1.2 via the pin's
#     own generic.nix), since the pin only ships ffmpeg 7.1.1;
#   - comfy-kitchen==0.2.31, comfy-aimdo==0.4.15 (exact pins; aimdo now the
#     compiled cp39-abi3 wheel — see deps/comfy-aimdo.nix);
#   - comfyui-frontend-package==1.49.6, comfyui-workflow-templates==0.11.55
#     (+ the seven sibling wheels its METADATA hard-requires, three of which
#     moved with it), comfyui-embedded-docs==0.5.10.
# The torch-bin/cu128 (2.7.0) overrides are untouched: v0.34.3's README
# *recommends* cu130+ for optimal Blackwell ops and says torch 2.7 is
# "minimally supported", but the pin's cu128 torch satisfies every
# torch_version_numeric gate (<2.10) and this flake's own CUDA-12.8 driver
# contract — kept per instructions. `comfy-angle` 0.1.1 is added
# (deps/comfy-angle.nix, the `py3-none-manylinux_2_28_x86_64` wheel —
# compiled-only, the second exception to the py3-none-any discipline after
# `av`) because `comfy_extras/nodes_glsl.py` imports it and its absence is
# an `IMPORT FAILED` at start, which `checks.comfyui-startup-clean`
# forbids.
#
# fetchFromGitHub hash: re-derived independently via
# `nix-prefetch-url --unpack https://github.com/Comfy-Org/ComfyUI/archive/<rev>.tar.gz`
# → nix32 06f7alvx8…, converted with `nix hash convert --hash-algo sha256
# --to sri`; the rev was read from GitHub's /tags API (lightweight tag →
# commit 7fd919f0caff…).
#
# GPU runpath: the pin's torch-bin derivation
# (pkgs/development/python-modules/torch/bin/default.nix) carries
# addDriverRunpath/autoAddDriverRunpath/autoPatchelfHook, so its compiled
# extensions already patch in the Nvidia driver runpath themselves; no
# manual LD_LIBRARY_PATH is added here (confirmed by reading that file at
# the pin, not just asserted from the design digest).
#
# Verify-first item 0 (download-capable core routes in server.py/app/,
# beyond custom_nodes/ which --disable-all-custom-nodes already closes):
# re-audited server.py and every module under app/ at v0.34.3; the four
# route-bearing files verified byte-identical at v0.34.5 (server.py,
# comfy/cli_args.py, app/frontend_management.py, app/assets/api/routes.py),
# so the closure below is unchanged at this rev.
#   - app/assets/api/routes.py still defines the asset-download routes
#     (`resolve_asset_for_download` / `download_asset_content`), every
#     handler still wrapped in `_require_assets_feature_enabled`, which
#     answers 503 while `_ASSETS_ENABLED` is False (module-level False,
#     flipped only by the `--enable-assets` startup path —
#     comfy/cli_args.py: `action="store_true"`, off by default). server.py
#     now registers them under `if args.enable_assets: … else:
#     register_assets_routes(self.app)` — still closed because the flag is
#     never passed, and the asset store has no network-fetch code path
#     regardless (it serves files already on disk).
#   - app/frontend_management.py's `download_release_asset_zip` (fetches a
#     dist.zip from a GitHub release) is only reachable from
#     `init_frontend_unsafe` AFTER the `version_string == DEFAULT_VERSION_STRING`
#     short-circuit — and this rev's DEFAULT_VERSION_STRING is the literal
#     "comfyanonymous/ComfyUI@latest" default, so with no `--front-end-version`
#     flag (this wrapper/module never pass one) `init_frontend` returns
#     `default_frontend_path()` (the bundled comfyui-frontend-package) and
#     never reaches the `get_release`/`download_release_asset_zip` branch.
#   checks.comfyui-vm still pins the assets route's closure with a
#   differential machine.fail probe on GET /api/assets so a future
#   ExecStart edit that adds the flag fails that check. No source patch was
#   needed here — the closure is structural (no flag path this wrapper
#   exposes reaches either route), not something a downstream flag could
#   reopen through this package alone.
{
  pkgs,
}:
let
  python = import ./python.nix { inherit pkgs; };
  version = "0.34.5";
  src = pkgs.fetchFromGitHub {
    owner = "Comfy-Org";
    repo = "ComfyUI";
    rev = "7fd919f0caff66a52289ea5b19cb6eaca0da04ef";
    hash = "sha256-P5vmQcvz+RlHW65LKtQ979c+DEadf2do3d0z1DdVxxk=";
  };
in
pkgs.stdenvNoCC.mkDerivation {
  pname = "comfyui";
  inherit version src;

  nativeBuildInputs = [ pkgs.makeWrapper ];

  dontConfigure = true;
  dontBuild = true;

  # makeWrapper's --add-flags places main.py *before* the caller's own
  # "$@" in the generated wrapper (exec python3 main.py "$@"), never
  # after — so a caller's flags always win over nothing here (there is
  # nothing else to conflict with): no LD_LIBRARY_PATH is set (see the
  # autoAddDriverRunpath note in the file header).
  installPhase = ''
    runHook preInstall

    mkdir -p "$out/share"
    cp -r . "$out/share/comfyui"

    makeWrapper ${python}/bin/python3 "$out/bin/comfyui" \
      --add-flags "$out/share/comfyui/main.py"

    runHook postInstall
  '';

  passthru = {
    inherit python src version;
  };

  meta = {
    description = "ComfyUI (node-based generative media UI), packaged nix-native against the host's CUDA 12.8 torch-bin pin";
    homepage = "https://github.com/Comfy-Org/ComfyUI";
    license = pkgs.lib.licenses.gpl3Only;
    platforms = [ "x86_64-linux" ];
    mainProgram = "comfyui";
  };
}
