# comfy-aimdo — ComfyUI's memory/device orchestration helper. Ships a
# py3-none-any fallback wheel alongside compiled manylinux wheels; this
# derivation picks the compiled cp39-abi3 x86_64 wheel so the real native
# `aimdo.so` ships (media M3), not the pure-Python fallback. v0.34.5 pins
# comfy-aimdo==0.4.15 exactly (requirements.txt); same version as v0.34.3,
# only the wheel selection changed. Hash cross-checked against
# https://pypi.org/pypi/comfy-aimdo/0.4.15/json (the x86_64 manylinux
# wheel's digests.sha256).
#
# The compiled wheel's `aimdo.so` links `libcuda.so.1`, so this needs BOTH
# `autoPatchelfHook` (patches the wheel's ELF libraries) and
# `autoAddDriverRunpath` (the hook that patches a driver runpath into the
# ELF so libcuda.so.1 resolves at run time) — the same pair the pin's
# torch-bin uses. No `autoPatchelfIgnoreMissingDeps`: the driver runpath
# hook is what resolves libcuda.so.1, which is never present in the build
# sandbox.
{
  buildPythonPackage,
  fetchPypi,
  autoPatchelfHook,
  autoAddDriverRunpath,
}:
buildPythonPackage rec {
  pname = "comfy_aimdo";
  version = "0.4.15";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "cp39";
    python = "cp39";
    abi = "abi3";
    platform = "manylinux2010_x86_64.manylinux2014_x86_64.manylinux_2_12_x86_64.manylinux_2_17_x86_64";
    hash = "sha256-8GRxNWVrizsmTjxKDJn3gV4OyLZ6DPzk90o9EFMlDd0=";
  };
  nativeBuildInputs = [
    autoPatchelfHook
    autoAddDriverRunpath
  ];
  doCheck = false;
  pythonImportsCheck = [ "comfy_aimdo" ];
}
