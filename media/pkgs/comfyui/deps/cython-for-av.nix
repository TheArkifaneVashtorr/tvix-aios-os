# A standalone Cython 3.2.4, used ONLY as a build-time tool for the `av`
# override (deps/av.nix) — never installed into ComfyUI's runtime
# environment (python.nix does not list it in `py.withPackages`), so it is
# not a "compiled dependency beyond the av override" under the plan's
# global constraint: it never reaches `site-packages` of the environment
# ComfyUI actually runs in, only the sandbox that compiles av's .pyx
# sources.
#
# Deviation from the plan: av 15.1.0's pyproject.toml declares
# `cython>=3.1.0a1,<4`, but the host pin's own `python3Packages.cython` is
# 3.0.12 (there is no 3.1.x at this nixpkgs pin — confirmed by evaluating
# `python3Packages.cython.version` and finding only `cython` 3.0.12 and
# the legacy `cython_0` 0.29.37.1). Building av against 3.0.12 was tried
# first (see deps/av.nix's original comment) and failed for real: Cython
# 3.0.12 cannot parse `av/filter/loudnorm.py`'s `cython.p_const_char`
# annotation ("Unknown type declaration 'cython.p_const_char' in
# annotation" — a real Cython 3.1 pure-Python-mode grammar addition, not a
# paper-only version-bound mismatch).
#
# Pinned at 3.2.4, NOT the latest 3.3.0: Cython 3.3.0 added the rule
# "Cython did not reject code with multiple contradicting type annotations
# on the same variable" (its CHANGES.rst), which now hard-errors on
# av 17.x's `container/pyio.py` — `__cinit__` annotates the local
# `seek_func: seek_func_t = NULL` and then, in a later `if` block,
# `seek_func: seek_func_t = pyio_seek`, i.e. the same type on the same
# local twice. av 17.0.1 (2026-04-18) predates Cython 3.2.5 (2026-05-23)
# and 3.3.0, so 3.2.4 (2026-01-04) is the newest Cython release av 17.0.1
# was built and tested against; it compiles pyio.py cleanly. This is a
# prebuilt manylinux wheel (no compiler needed to obtain Cython itself),
# fetched the same way as every other wheel dependency here: `fetchPypi`,
# SRI hash derived from PyPI's own JSON the same way as spandrel's.
{
  buildPythonPackage,
  fetchPypi,
}:
buildPythonPackage rec {
  pname = "cython";
  version = "3.2.4";
  format = "wheel";
  src = fetchPypi {
    pname = "cython";
    inherit version format;
    dist = "cp312";
    python = "cp312";
    abi = "cp312";
    platform = "manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64";
    hash = "sha256-VbbETNMIIfCyUiDOum/mNu3kiYHSpBubv+PHkCzkTqc=";
  };
  doCheck = false;
  pythonImportsCheck = [ "Cython" ];
}
