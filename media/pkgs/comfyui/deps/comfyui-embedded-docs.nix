# comfyui-embedded-docs — in-app node documentation, shipped as a
# pure-Python wheel. Not present at the host pin; pinned per
# docs/superpowers/plans/2026-09-02-media-nix-native.md's pins table. Hash
# cross-checked against https://pypi.org/pypi/comfyui-embedded-docs/0.5.10/json
# (v0.34.3 requirements.txt pins ==0.5.10).
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "comfyui_embedded_docs";
  version = "0.5.10";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-VPm7IVennc56aMl17pi+AyFPli1BcA4XzhlBGehj67Y=";
  };
  doCheck = false;
  pythonImportsCheck = [ "comfyui_embedded_docs" ];
}
