# comfyui-workflow-templates-media-other — bundled media for the
# remaining ("other") template category; see
# comfyui-workflow-templates-core.nix for why this sibling package is
# pinned outside the plan's own pins table. Pure py3-none-any data wheel,
# no compiled code.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates_media_other";
  version = "0.3.229";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-zj2Y+p2EuRTDNf5cm8kDz+++GTKxvDy2uu9/NxtL1DU=";
  };
  doCheck = false;
  pythonImportsCheck = [ "comfyui_workflow_templates_media_other" ];
}
