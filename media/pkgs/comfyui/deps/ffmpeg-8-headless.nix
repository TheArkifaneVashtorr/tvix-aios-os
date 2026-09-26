# ffmpeg 8.1.2 (headless), built with the host pin's own ffmpeg build
# recipe (pkgs/development/libraries/ffmpeg/generic.nix). ComfyUI v0.34.3
# requires `av>=17.0.0`, and PyAV 17's installation docs state its
# FFmpeg floor moved to "version 8.0 or higher" (av 17 bootstraps FFmpeg
# 8.1 in its binary wheels) — the host pin only ships ffmpeg 7.1.1, which
# av 17 can no longer link. This is NOT a new Python dependency: it is
# only the FFmpeg whose libav{codec,format,util,filter,device} av links,
# i.e. the same single compiled dependency (av) as before, re-pointed at
# the FFmpeg major its requirement demands. Built by `callPackage` on the
# pin's own generic.nix (parameterised by `version`/`hash`, which is how
# upstream nixpkgs builds every ffmpeg major), so the only changes from
# the pin's ffmpeg_7-headless are the version, the git source hash, and
# the variant string.
#
# Version/hash are nixpkgs' own v8 record (version 8.1.2, hash
# `sha256-wJ3c8VVo/tK84K7bKYs/UWcln4mSO+tf/w5NLNjKhiI=`), re-derived
# independently: `git ls-remote https://git.ffmpeg.org/ffmpeg.git
# refs/tags/n8.1.2` resolves to 1c2c67c0…, and the release tarball
# https://ffmpeg.org/releases/ffmpeg-8.1.2.tar.xz is 11 710 924 bytes —
# the git checkout hash is what fetchgit (the pin generic.nix's `source`
# default) pins, so that hash is what is recorded here.
#
# FFmpeg 8.0 removed libpostproc, but the pin's generic.nix (ffmpeg-7 era)
# still emits `enableFeature (buildPostproc && withGPL) "postproc"` — i.e.
# `--enable-postproc` or `--disable-postproc` — unconditionally, which
# FFmpeg 8's configure rejects ("Unknown option --enable/--disable-postproc").
# nixpkgs gates this flag behind `lib.versionOlder version "8.0"` in its
# own newer generic.nix; rather than vendor/patch that whole file, this
# sets `buildPostproc = false` (so `optional buildPostproc "libpostproc"`
# in the checkPhase/meta lists correctly drops the ghost library) and then
# strips the leftover `--disable-postproc` token from `configureFlags` via
# overrideAttrs — reproducing nixpkgs' gate exactly with three lines.
# libavresample (`buildAvresample`) is already gated `<5` in the pin, so it
# needs no such treatment.
#
# Hardware-acceleration features are disabled (withAmf/Nvcodec/CudaLLVM/Opencl/
# Vulkan/Vaapi = false): PyAV only links libav{codec,format,util,filter,device}
# + swscale/swresample — it never uses AMD AMF, NVENC/NVDEC/CUVID, CUDA-LLVM,
# OpenCL, Vulkan or VA-API — and these are exactly the ffmpeg-7→8 binding
# surfaces whose dependency versions skew at the pin (AMF 1.4.36 is the bare
# minimum ffmpeg 8.1's configure accepts and fails its `>=` probe here;
# nv-codec-headers-12 predates ffmpeg 8's headers-13 features). Keeping them
# would mean pinning newer GPU-SDK headers too — out of scope for a link
# target. Every software codec (aom/dav1d/x264/x265/svtav1/theora/vorbis/vpx/
# opus/…) stays enabled, so PyAV's built-in codecs/formats are intact.
{
  pkgs,
  lib,
}:
let
  v8 = {
    version = "8.1.2";
    hash = "sha256-wJ3c8VVo/tK84K7bKYs/UWcln4mSO+tf/w5NLNjKhiI=";
  };
  ffmpeg8 = pkgs.callPackage (pkgs.path + "/pkgs/development/libraries/ffmpeg/generic.nix") (
    {
      inherit (pkgs.darwin) xcode;
      inherit (pkgs.cudaPackages) cuda_cudart cuda_nvcc libnpp;
      buildPostproc = false;
      withAmf = false;
      withNvcodec = false;
      withCudaLLVM = false;
      withOpencl = false;
      withVulkan = false;
      withVaapi = false;
    }
    // (
      v8
      // {
        ffmpegVariant = "headless";
      }
    )
  );
in
ffmpeg8.overrideAttrs (old: {
  configureFlags = builtins.filter (f: !(lib.hasInfix "postproc" f)) old.configureFlags;
  # FFmpeg 8 dropped yasm for x86 assembly and requires nasm; the pin's
  # generic.nix (ffmpeg-7 era) still puts yasm in nativeBuildInputs.
  nativeBuildInputs =
    builtins.filter (p: !(lib.hasInfix "yasm" (p.pname or p.name or ""))) old.nativeBuildInputs
    ++ [ pkgs.nasm ];
})
