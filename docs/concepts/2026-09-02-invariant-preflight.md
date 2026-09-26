# Concept 2026-09-02 — Invariant preflight (`basket doctor`)

**Class:** infrastructure (NixOS module + CLI subcommand). **Status:** proposed.

**Origin data (today):** age-plugin-yubikey's recurring NixOS failure mode is PATH
discovery (works in your shell, fails inside a systemd unit or stage-1); tmpfs pages
can reach swap, silently violating invariant 1's "plaintext only in tmpfs" intent;
Cowork's KVM/virtiofsd probing misdetects on NixOS (anthropics/claude-code#74605).
All three are invariants that hold *by luck* until measured.

**Idea:** every brief §3 invariant gets a machine-checkable probe, run at three
times:

1. **Build time** — module assertions (already planned for classification routing;
   extend to: swap must be absent or encrypted on any host with a basketStore;
   every systemd unit that invokes `age` must have the plugin in its `path`).
2. **Boot time** — a `preflight.service` that probes /dev/kvm, vhost_vsock,
   hooksPath, git-remote allowlist, broker CA presence, and refuses to start agent
   targets when a probe fails (hard dependency, not a warning).
3. **On demand** — `basket doctor`: runs the same probe set plus leak detection
   (any mounted `basket-*` tmpfs whose owning agent scope is dead = invariant 1
   violation) and prints PASS/FAIL per invariant.

**Why it fits the directives:** "if you cannot measure or test something it isn't
real" — this turns the six invariants from prose into tests that run forever, and
the buffer role means the operator only ever sees `basket doctor` → green.

**Earliest landing:** probes 1–2 belong to Phase 3 (assertions) and Phase 4
(Cowork deps); `basket doctor` can land with Phase 3. Revisit then.
