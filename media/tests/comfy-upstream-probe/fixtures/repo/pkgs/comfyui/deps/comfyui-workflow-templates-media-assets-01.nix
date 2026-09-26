# Fixture copy of pkgs/comfyui/deps/comfyui-workflow-templates-media-assets-01.nix at its pre-W1 state.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates_media_assets_01";
  version = "0.1.38";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
  };
}
