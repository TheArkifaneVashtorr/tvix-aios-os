# comfyui-workflow-templates — bundled example workflow JSON files, shipped
# as a pure-Python wheel. Not present at the host pin; pinned per
# docs/superpowers/plans/2026-09-02-media-nix-native.md's pins table. Hash
# cross-checked against https://pypi.org/pypi/comfyui-workflow-templates/0.11.55/json
# (v0.34.5 requirements.txt pins ==0.11.55).
#
# Deviation from the plan: this package's own dist-info (`Requires-Dist`,
# read directly from the wheel's METADATA / PyPI JSON — not optional/extras)
# hard-requires seven sibling packages the plan's pins table does not name —
# `comfyui-workflow-templates-{core,json,media-api,media-video,media-image,media-other,media-assets-01}`
# — split out of what used to be one wheel (0.9.85 needed only five; 0.11.55
# adds `json` and `media-assets-01`). `checks.comfyui-package` proved the
# gap historically: it failed with `ModuleNotFoundError:
# comfyui_workflow_templates_core` until the siblings were added. Each is
# its own hash-pinned py3-none-any `fetchPypi` wheel under this directory
# (comfyui-workflow-templates-core.nix etc.), derived fresh from PyPI's own
# JSON the same way as spandrel's hash, and propagated here so
# `py.withPackages` pulls them in without needing to be listed by name in
# python.nix.
{
  buildPythonPackage,
  fetchPypi,
  comfyui-workflow-templates-core,
  comfyui-workflow-templates-json,
  comfyui-workflow-templates-media-api,
  comfyui-workflow-templates-media-video,
  comfyui-workflow-templates-media-image,
  comfyui-workflow-templates-media-other,
  comfyui-workflow-templates-media-assets-01,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates";
  version = "0.11.55";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-8w+wNIH+pK2nkswj1S5TdnJl8aoPp5kNJf7tVYx8iIA=";
  };
  propagatedBuildInputs = [
    comfyui-workflow-templates-core
    comfyui-workflow-templates-json
    comfyui-workflow-templates-media-api
    comfyui-workflow-templates-media-video
    comfyui-workflow-templates-media-image
    comfyui-workflow-templates-media-other
    comfyui-workflow-templates-media-assets-01
  ];
  doCheck = false;
  pythonImportsCheck = [ "comfyui_workflow_templates" ];
}
