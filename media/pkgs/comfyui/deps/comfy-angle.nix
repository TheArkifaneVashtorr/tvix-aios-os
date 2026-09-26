# comfy-angle — ships ANGLE's libEGL.so / libGLESv2.so for ComfyUI's GLSL
# nodes (`comfy_extras/nodes_glsl.py` imports `comfy_angle`). Compiled-only:
# no py3-none-any wheel is published, so this is the second compiled
# exception to the py3-none-any discipline after `av`. requirements.txt
# names it unpinned under "non essential dependencies", so the version is
# PyPI's own 0.1.1.
#
# The wheel's only two libraries link glibc and libgcc (no libGL, no
# libstdc++), so `autoPatchelfHook` resolves them with no extra
# `buildInputs`. Its absence at start is the `IMPORT FAILED: nodes_glsl.py`
# + `Traceback … No module named 'comfy_angle'` that
# checks.comfyui-startup-clean forbids.
{
  buildPythonPackage,
  fetchPypi,
  autoPatchelfHook,
}:
buildPythonPackage rec {
  pname = "comfy_angle";
  version = "0.1.1";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    abi = "none";
    platform = "manylinux_2_28_x86_64";
    hash = "sha256-PS/KuThuu7VlPWZpb6i8rTKcHRhS6kth8obqmUhahAo=";
  };
  nativeBuildInputs = [ autoPatchelfHook ];
  doCheck = false;
  pythonImportsCheck = [ "comfy_angle" ];
}
