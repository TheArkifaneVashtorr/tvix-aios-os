# Upstream Bump Runbook

## When

A bump only when a typed task needs an upstream change, at most one per increment (A26). One paragraph the seat rewrites if the operator vetoes A26 for (b) or (c). (this runbook is Platform's PL7, docs/superpowers/plans/2026-09-11-platform.md)

## The task's shape

A typed `PL` task per bump: `touches` = `flake.lock`, `patches/<pkg>/*`, and `flake.nix` only if the `inputs` line changes; `acceptance` = `patch-series-apply, patch-series-eval, host-core, lint` plus `core-patches-wiring` and the package's own checks; the commit-subject grammar.

## Procedure

Edit the rev in `flake.nix`'s `<input>.url` — every input in this tree names
its commit in the URL (e.g. `github:numtide/llm-agents.nix/<rev>`), so `nix
flake lock --update-input <input>` (the deprecated alias for `nix flake
update <input>`) is a no-op: the lock has nothing to move for an input whose
spec already pins the commit. Measured 2026-09-23, `--update-input llm-agents`
left `flake.lock` unchanged. Then `nix build
.#checks.x86_64-linux.patch-series-apply -L --no-link` — the edited rev
pulls the lock forward on this build, no separate lock-update step needed,
and the check is red if any patch no longer applies; that red *is* the bump
task's Step 1. Per failing patch, re-port with `diff -u` against the new
upstream source, keeping its number; the re-port changes
`/etc/helm/patches.json`'s sha256 values, so `core-patches-wiring` is
re-run.

Once the check set is green, build the toplevel and diff the closure against
the live system to prove only the intended package moved: `nix build
.#nixosConfigurations.core.config.system.build.toplevel` then `nix store
diff-closures /run/current-system ./result`. Worked examples on main:
`d3c92068` (claude-code 2.1.258 → 2.1.280, the llm-agents input) and
`a8b52446` (claude-desktop 1.40609.1 → 2.2553.13) — read their commit
messages for the closure-diff shape and what "only the intended package"
looks like in practice.

**Verifying the running version is a separate step from switching.** A
switch does not restart an already-running GUI app: the app's GNOME scope
holds onto its old process, so the old store path stays live until the app
is genuinely quit and relaunched (measured 2026-09-23 after the switch that
carried `a8b52446`: `/run/current-system/sw/bin/claude-desktop` already
resolved to 2.2553.13 while PID 36238 kept running 1.40609.1, and closing the
window did not end it). Confirm the new version is
actually running by quitting and relaunching the app (or restarting the
service) after the switch — reading the closure or the store path only
proves what *would* run next time.

### The failure a non-applying patch prints

```
Hunk #1 FAILED at line 42.
can't find file to patch at line 1
```

## What must not happen

No `|| true`, no deleting a patch to make the build pass without a row in `docs/ledger/patches.toml` — `EV6`.

## Rollback

`git checkout flake.lock` before the commit; after landing, a plain revert; the closure changes only at the operator's switch, G1.