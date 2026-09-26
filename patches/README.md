# Patches

A vendored upstream gets its patches here as a numbered series, one directory
per package:

```
patches/<pkg>/NNNN-*.patch
```

`lib/patchSeries.nix` reads and applies them (decision 37a). The contract it
enforces, per directory:

- Only regular files matching `NNNN-*.patch` (a four-digit number, zero-padded)
  and a `README.md` may live here. Anything else — a stray file or a
  subdirectory — refuses evaluation (`stray file …`).
- No two patches may share a number (`duplicate number NNNN`).
- Patches apply in numeric order (`0001` before `0002`, …).

A package opts in with one call — `self.lib.patchSeries.applyTo "<pkg>"` is the
frozen directory (`patches/<pkg>`) partially applied, so a consumer writes:

```nix
thePackage = self.lib.patchSeries.applyTo "claude-code" llm-agents.packages.x86_64-linux.claude-code;
```

`applyTo` lives in `flake.nix` (it needs the flake's `self`) — the module
`lib/patchSeries.nix` itself exports only `readSeries`, `renderPostPatch` and
`applySeries`.

The audit that retires the old `pkgs/dsh/*` / `pkgs/dsh-openrouter/*` vendored
sources underlies this layout; the patch ledger lives with the EV6 record
(`docs/ledger/`).