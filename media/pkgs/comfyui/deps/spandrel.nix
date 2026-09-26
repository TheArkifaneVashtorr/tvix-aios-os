# spandrel — model-architecture auto-loader for upscalers/restorers, one of
# v0.22.3's "non essential" requirements. Not present at the host pin, and
# unpinned upstream (bare `spandrel` in requirements.txt) — 0.4.2 is the
# latest release on PyPI as of packaging (2026-09-02). Ships only a
# py3-none-any wheel (and an sdist), no compiled variant. Per this task's
# instructions the hash was NOT copied from the design digest (which left
# it unresolved) but derived fresh from PyPI's own JSON:
#   curl -s https://pypi.org/pypi/spandrel/0.4.2/json
#     | <the py3-none-any file's digests.sha256>
#     = 6c93e3ecbeb0e548fd2df45a605472b34c1614287c56b51bb33cdef7ae5235b5
#   nix hash convert --hash-algo sha256 --to sri <that hex>
#
# propagatedBuildInputs mirrors this wheel's own `Requires-Dist` (read
# directly from its METADATA): torch, torchvision, safetensors, numpy,
# einops, typing-extensions — without these, pythonImportsCheck below
# (which runs against this derivation's own isolated closure) fails.
{
  buildPythonPackage,
  fetchPypi,
  torch,
  torchvision,
  safetensors,
  numpy,
  einops,
  typing-extensions,
}:
buildPythonPackage rec {
  pname = "spandrel";
  version = "0.4.2";
  format = "wheel";
  src = fetchPypi {
    inherit pname version format;
    dist = "py3";
    python = "py3";
    hash = "sha256-bJPj7L6w5Uj9LfRaYFRys0wWFCh8VrUbszze965SNbU=";
  };
  propagatedBuildInputs = [
    torch
    torchvision
    safetensors
    numpy
    einops
    typing-extensions
  ];
  doCheck = false;
  pythonImportsCheck = [ "spandrel" ];
}
