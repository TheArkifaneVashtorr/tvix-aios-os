# comfyui-workflow-templates-media-image — bundled media for the
# "image"-category templates; see comfyui-workflow-templates-core.nix for
# why this sibling package is pinned outside the plan's own pins table.
# Pure py3-none-any data wheel, no compiled code.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates_media_image";
  version = "0.3.160";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-1KXFVBxwiPatscfaQfXXwcFKA37aamHNi0t2wlH6qpM=";
  };
  doCheck = false;
  pythonImportsCheck = [ "comfyui_workflow_templates_media_image" ];
}
