# comfyui-workflow-templates-media-api — bundled media (thumbnails etc.)
# for the "api"-category templates; one of seven sibling packages
# comfyui-workflow-templates 0.11.54's own METADATA requires unconditionally
# (see comfyui-workflow-templates-core.nix for why this is pinned outside
# the plan's own pins table, and how the hash was derived). Pure
# py3-none-any data wheel, no compiled code.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates_media_api";
  version = "0.3.84";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-wtalmZrDnk839HriMcklV97+Wt2yzGq1wRQQtNWikQo=";
  };
  doCheck = false;
  pythonImportsCheck = [ "comfyui_workflow_templates_media_api" ];
}
