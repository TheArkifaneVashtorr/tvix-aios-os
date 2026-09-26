# av — PyAV bindings for FFmpeg. The host pin ships av 14.1.0, built from a
# GitHub source tag against ffmpeg-headless (7.1.1); v0.22.3 required
# av>=14.2.0, which the 15.1.0 override satisfied. v0.34.3 requires
# av>=17.0.0, whose installation docs moved the FFmpeg floor to "8.0 or
# higher" (av 17 bootstraps FFmpeg 8.1 in its binary wheels) — so this
# override now also re-points `buildInputs` at deps/ffmpeg-8-headless.nix
# (FFmpeg 8.1.2 built by the pin's own generic.nix), while keeping the
# pin's `nativeBuildInputs` (pkg-config) untouched. Only version, src,
# build-system and buildInputs move; the compiled-extension shape
# (sdist + Cython linked against a system ffmpeg) is unchanged from the
# 15.1.0 override — this is the same single compiled dependency (`av`),
# re-pointed at the FFmpeg major its requirement demands, not a new one.
# Source for the FFmpeg-8 floor: PyAV docs/overview/installation.rst
# "Bring your own FFmpeg (version 8.0 or higher)".
#
# `doCheck`/`preCheck`/`nativeCheckInputs` are dropped: the pin's own
# preCheck string-interpolates a `linkFarm` of `fetchurl`'d PyAV test media
# samples (`test-samples.toml`) into the derivation regardless of doCheck —
# that interpolation alone pulls the sample files in as a build input of
# the derivation, an unrelated multi-file network fetch this package has
# no use for. `pythonImportsCheck` (kept from the pin) is the real proof
# here: it imports the compiled `av` extension modules after install,
# which only succeeds if the Cython build actually produced working
# bindings against the linked ffmpeg.
#
# build-system stays deps/cython-for-av.nix (Cython 3.2.4): av 17.0.1's
# pyproject.toml declares `cython>=3.1.0a1,<4`, exactly as 15.1.0 did, and
# the host pin's own `cython` is still 3.0.12 — the same Cython-3.1
# pure-Python grammar gap documented for the 15.1.0 override applies.
# Pinned at 3.2.4 (not 3.3.0, which hard-errors on av 17.x's
# `container/pyio.py` duplicate local annotation — see cython-for-av.nix
# for the pin/hash record).
{
  av,
  fetchPypi,
  cythonForAv,
  setuptools,
  ffmpeg-8-headless,
}:
av.overridePythonAttrs (old: {
  version = "17.0.1";
  src = fetchPypi {
    pname = "av";
    version = "17.0.1";
    hash = "sha256-+8vUqkO8pqhpGBYoMRLRZZon9Ae762bROXAjaRM59dQ=";
  };
  build-system = [
    cythonForAv
    setuptools
  ];
  buildInputs = [ ffmpeg-8-headless ];
  # Measured: av 15.1.0 (the previous override) still ships `av.bytesource`,
  # but av 17.0.1 (this override) does not — so the pin's pythonImportsCheck
  # (which still probes it) would fail the import step here.
  pythonImportsCheck = builtins.filter (m: m != "av.bytesource") old.pythonImportsCheck;
  doCheck = false;
  preCheck = "";
  nativeCheckInputs = [ ];
})
