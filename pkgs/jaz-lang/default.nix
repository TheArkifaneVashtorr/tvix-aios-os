# pkgs/jaz-lang: the JAZ framework (PyPI distribution `jaz-lang`, import name
# `jaz`), pinned to v0.2.0a4 exactly -- the version arm C of
# docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md (§6b)
# replicates against. "What stays stock" there is the whole point: this
# derivation packages the real, unmodified upstream sdist rather than
# vendoring or patching it.
#
# Verified against the real PyPI metadata (2026-09-27, `pypi.org/pypi/jaz-lang/json`):
# the sdist's own `pyproject.toml` declares `name = "jaz-lang"`, `version =
# "0.2.0a4"` and `build-backend = "setuptools.build_meta"` (`requires =
# ["setuptools>=77.0"]`) -- pyproject.toml's own dependency list matches the
# six runtime deps below exactly (jinja2, httpx, tenacity, beartype,
# typing-extensions, pathspec, litellm), all satisfied by this repo's pinned
# nixpkgs per the measuring agent's fact sheet (jaz-armc-facts.md §B). No
# optional extra (tracing/tokens/copilot) is needed: arm C's backend is a
# hand-written BaseLLM subclass (tools/experiments/jaz/claude_llm.py) that
# talks to `claude` through a host-side gateway, never litellm itself, even
# though litellm is an unconditional (non-extra) dependency of the package
# (facts sheet §B addendum) and therefore always pulled in and left inert.
{
  lib,
  buildPythonPackage,
  fetchurl,
  setuptools,
  jinja2,
  httpx,
  tenacity,
  beartype,
  typing-extensions,
  pathspec,
  litellm,
}:
buildPythonPackage rec {
  pname = "jaz-lang";
  version = "0.2.0a4";
  pyproject = true;

  # fetchPypi's default URL shape (pythonhosted.org's legacy
  # packages/source/<letter>/<name>/... path) 404s for this upload --
  # PyPI's real JSON metadata (pypi.org/pypi/jaz-lang/json, 2026-09-27) gives
  # the sdist at the hashed path below. fetchurl with that literal URL,
  # verified against the same metadata's sha256 digest, sidesteps the
  # mismatch rather than fighting fetchPypi's URL guesser.
  src = fetchurl {
    url = "https://files.pythonhosted.org/packages/9a/7e/56fe0f4bf079d5f333a2f9cecba3e47a990a478d59b4556e04d03487f59f/jaz_lang-${version}.tar.gz";
    hash = "sha256-40mqbcGHxr6mRhc9krY8uJosSIWVBMeu8y04NcH6uSw=";
  };

  build-system = [ setuptools ];

  dependencies = [
    jinja2
    httpx
    tenacity
    beartype
    typing-extensions
    pathspec
    litellm
  ];

  # A network/subprocess-heavy suite (its own pyproject.toml gates
  # `integration`-marked tests off by default, but plenty of the rest still
  # want optional heavy deps -- mem0/letta/datasets/docker -- that are out of
  # scope here); the import check below is this derivation's own acceptance,
  # per the spec's deliverable 1 ("Build it... and import-test jaz in the
  # env").
  doCheck = false;

  pythonImportsCheck = [
    "jaz"
    "jaz.llm.llm"
    "jaz.hooks"
    "jaz.config"
  ];

  meta = {
    description = "JAZ: the language of building and optimizing LLM agents (code-mode REPL, invoke/recursion, hooks)";
    homepage = "https://github.com/jaz-lang/jaz";
    license = lib.licenses.asl20;
    platforms = lib.platforms.unix;
  };
}
