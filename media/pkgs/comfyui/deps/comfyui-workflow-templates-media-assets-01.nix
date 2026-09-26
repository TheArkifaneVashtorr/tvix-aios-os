# comfyui-workflow-templates-media-assets-01 — bundled media asset data,
# one of the seven sibling packages comfyui-workflow-templates 0.11.55's
# own METADATA requires unconditionally (its `Requires-Dist` pins
# `comfyui-workflow-templates-media-assets-01==0.1.39`; see
# comfyui-workflow-templates.nix's header for why these siblings are pinned
# outside the plan's own pins table). Pure py3-none-any data wheel, no
# compiled code. Hash derived fresh from PyPI's own JSON, the same way as
# spandrel's.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates_media_assets_01";
  version = "0.1.39";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-FstzT40Isv2cRI13GQqytSB3dQtylL5ViRH8ZmHDsQY=";
  };
  doCheck = false;
  pythonImportsCheck = [ "comfyui_workflow_templates_media_assets_01" ];
}
