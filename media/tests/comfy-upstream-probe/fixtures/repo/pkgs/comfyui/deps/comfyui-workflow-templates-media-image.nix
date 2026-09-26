# Fixture copy of pkgs/comfyui/deps/comfyui-workflow-templates-media-image.nix at its pre-W1 state.
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
    hash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
  };
}
