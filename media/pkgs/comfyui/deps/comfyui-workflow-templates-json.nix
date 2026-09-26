# comfyui-workflow-templates-json — one of the seven sibling packages
# comfyui-workflow-templates 0.11.55's own METADATA requires unconditionally
# (its `Requires-Dist` pins `comfyui-workflow-templates-json==0.1.68`; see
# comfyui-workflow-templates.nix's header for why these siblings are pinned
# outside the plan's own pins table). Pure py3-none-any data wheel, no
# compiled code. Hash derived fresh from PyPI's own JSON, the same way as
# spandrel's.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates_json";
  version = "0.1.68";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-w/IkucxibIQ19jmjlOK6lasWzlTiQoIm1+58rc0AQEk=";
  };
  doCheck = false;
  pythonImportsCheck = [ "comfyui_workflow_templates_json" ];
}
