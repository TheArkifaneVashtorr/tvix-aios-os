# comfy-kitchen — ComfyUI's kernel-dispatch library. Ships both compiled
# manylinux wheels and a py3-none-any wheel for every release (verified
# against PyPI's per-file listing); the py3 wheel carries real eager/triton
# backend modules (not a stub), so it is chosen here to dodge the compiled
# CUDA-ABI question entirely — see
# docs/research-2026-09-02-comfyui-tag-selection.md. v0.34.3 pins
# comfy-kitchen==0.2.31 exactly (requirements.txt). Hash cross-checked
# against https://pypi.org/pypi/comfy-kitchen/0.2.31/json.
#
# `torch` and `packaging` are a `propagatedBuildInputs` deviation from
# this wheel's own METADATA: comfy_kitchen's dist-info declares neither as
# a `Requires-Dist` (verified by reading it directly from the wheel), yet
# `comfy_kitchen/__init__.py` does `import torch` unconditionally and
# `comfy_kitchen/scaled_mm_v2.py` (imported transitively through the
# eager backend) does `from packaging import version` unconditionally —
# `checks.comfyui-package` proved both gaps in turn: `pythonImportsCheck`
# (run against this derivation's own isolated closure, not the full
# `py.withPackages` environment) failed first with
# `ModuleNotFoundError: No module named 'torch'`, then, after adding
# torch, with `No module named 'packaging'`. Scanning every `import`/
# `from` at the top of every `comfy_kitchen/**/*.py` in the wheel found no
# further third-party name beyond these two (plus `triton`, which
# backends/triton/__init__.py already try/except-guards upstream —
# confirmed by reading it — so it needs no fix here).
{
  buildPythonPackage,
  fetchPypi,
  torch,
  packaging,
}:
buildPythonPackage rec {
  pname = "comfy_kitchen";
  version = "0.2.31";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-UReUbDDzCM/HO5wm9yOuORgwi9CQ5XqOrimEBpNKq9Y=";
  };
  propagatedBuildInputs = [
    torch
    packaging
  ];
  doCheck = false;
  pythonImportsCheck = [ "comfy_kitchen" ];
}
