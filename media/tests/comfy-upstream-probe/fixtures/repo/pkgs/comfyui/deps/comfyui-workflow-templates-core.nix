# Fixture copy of pkgs/comfyui/deps/comfyui-workflow-templates-core.nix at its pre-W1 state.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_workflow_templates_core";
  version = "0.3.331";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
  };
}
