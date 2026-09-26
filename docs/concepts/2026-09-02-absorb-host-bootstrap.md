# Concept 2026-09-02b — Absorb the host bootstrap into the flake

**Class:** infrastructure (hosts/core module). **Status:** proposed.

**Origin data (today):** the YubiKey "missing driver" incident. The key needs
`services.pcscd.enable = true`, which lived nowhere — the host's project
prerequisites sit in a hand-edited `/etc/nixos/ai-bootstrap.nix` that also imports
`<nixos-unstable>` via an **unpinned channel** for claude-code. Two consequences:
a required service was silently absent until hardware failed at runtime, and the
host's claude-code version floats outside any lock file — both against invariant 4
(reproducible from flake.lock + baskets.lock + YubiKey) and against "if you cannot
test it, it isn't real."

**Idea:** when `hosts/core/` lands (Phase 4 needs managed settings on the host;
Phase 9 formalizes it), it absorbs and retires `ai-bootstrap.nix`:

- pcscd, vhost_vsock, kvm group, bubblewrap/socat — declared in the repo, pinned.
- claude-code from the pinned `llm-agents.nix` input (already decided), floor
  asserted at ≥ 2.1.224 (mask features) as a module assertion, not a hope.
- Every host prerequisite gets a `basket doctor` probe (see
  [invariant-preflight](2026-09-02-invariant-preflight.md)): pcscd socket present,
  plugin answers over PC/SC, /dev/kvm, vhost_vsock — so the next missing-service
  failure is a named FAIL line before any phase test, not a mystery at the YubiKey.

**Earliest landing:** Phase 4 (host already needs repo-managed config then);
interim: the one-line pcscd fix stays in `ai-bootstrap.nix`.
