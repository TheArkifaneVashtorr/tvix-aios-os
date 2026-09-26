# Fixture copy of pkgs/comfyui/deps/comfyui-frontend-package.nix at its pre-W1 state.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_frontend_package";
  version = "1.49.6";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
  };
}
