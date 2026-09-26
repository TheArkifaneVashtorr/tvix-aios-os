# comfyui-workflow-templates-core — the workflow-template JSON/manifest
# data. comfyui-workflow-templates split its payload across seven sibling
# packages (0.11.55's own METADATA pins `comfyui-workflow-templates-core==0.3.333`
# as a hard, non-optional `Requires-Dist`; see
# comfyui-workflow-templates.nix for why) — none of the plan's pins table
# names it, so this hash was derived fresh from PyPI's own JSON, the same
# way as spandrel's:
#   curl -s https://pypi.org/pypi/comfyui-workflow-templates-core/0.3.333/json
#     | <the py3-none-any file's digests.sha256>
#   nix hash convert --hash-algo sha256 --to sri <that hex>
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates_core";
  version = "0.3.333";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-3/FH/hcjnbIqOIPlKt48l29Tf8OVvxWyvFIlx8nTzFQ=";
  };
  doCheck = false;
  pythonImportsCheck = [ "comfyui_workflow_templates_core" ];
}
