# comfyui-workflow-templates-media-video — bundled media for the
# "video"-category templates; see comfyui-workflow-templates-core.nix for
# why this sibling package is pinned outside the plan's own pins table.
# Pure py3-none-any data wheel, no compiled code.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates_media_video";
  version = "0.3.101";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-YnD9YcjDkxtvADGrrH1MkM7WJN5seRi/+FuJ5sPXSTw=";
  };
  doCheck = false;
  pythonImportsCheck = [ "comfyui_workflow_templates_media_video" ];
}
