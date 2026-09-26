# Phase 3 acceptance — what you run

One command from the repo root (no sudo, no hardware needed):

    nix develop -c tests/acceptance/phase3.sh

It proves the system refuses to even build a configuration that would let
private data reach anything with network access; then health-checks this
machine's invariants.

Concretely, in order:

1. A known-good configuration (a `local-only` basket mounted only into an
   agent with no network route) evaluates and builds normally.
2. A deliberately-wrong configuration (that same kind of basket mounted into
   an agent that *does* have network access) is attempted, and the build
   **fails** — Nix's module system catches it at evaluation time, before
   anything runs. The script shows you the actual error text the operator
   would see, and it names the agent, the basket, and the rule that was
   broken, so no repo documentation is needed to understand it.
3. `basket doctor` runs against this real machine and prints a PASS/FAIL/WARN
   line for each host invariant (no active swap, smartcard daemon reachable,
   YubiKey plugin on PATH, `/dev/kvm` present, `vhost_vsock` loaded, no
   leftover basket mounts under `/run/baskets`). WARNs are fine — they mark
   optional hardware/features that this run doesn't need; only a FAIL fails
   the acceptance step.

Expected final line: `PHASE 3 ACCEPTANCE: PASS`.
