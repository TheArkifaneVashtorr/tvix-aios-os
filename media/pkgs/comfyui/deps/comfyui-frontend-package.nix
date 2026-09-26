# comfyui-frontend-package — ComfyUI's own web UI, shipped as a pure-Python
# wheel (no compiled ABI). Not present at the host pin; pinned here per
# docs/superpowers/plans/2026-09-02-media-nix-native.md's pins table. The
# hash was cross-checked against https://pypi.org/pypi/comfyui-frontend-package/1.49.6/json
# (v0.34.3 requirements.txt pins ==1.49.6; bdist_wheel digests.sha256),
# converted with `nix hash convert`.
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
    hash = "sha256-ac735n8ihUhS0de+aP+C8nvU/0sz3pxkPX6xM5dpxCE=";
  };
  doCheck = false;
  pythonImportsCheck = [ "comfyui_frontend_package" ];
}
