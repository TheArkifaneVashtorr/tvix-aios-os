# smoke skill fixture (SA8b, PL27) — this directory deliberately carries no
# AGENTS.md: the "skills/ present, AGENTS.md absent" negative payload. It was
# Nix-built (harnessPayloadNoAgents) until PL27 moved it to a tracked fixture
# so the dsh-openrouter assert reads a plain path, not a derivation output
# (the eval-time IFD the allow-import-from-derivation guard refuses).
