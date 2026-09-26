# claude-code

Upstream: `numtide/llm-agents.nix` at `4ab625e16a6cc52fe3f606b95f1e2ac20dafa80b`
(the `llm-agents.url` pin). Series empty as of PL3.

Wired in `flake.nix`:

```nix
claude-code-pkg = self.lib.patchSeries.applyTo "claude-code" llm-agents.packages.x86_64-linux.claude-code;
```

A bump follows `docs/runbooks/upstream-bump.md` (PL7).
<!-- PL7 forward reference: docs/runbooks/upstream-bump.md does not exist yet; PL7 creates it -->
