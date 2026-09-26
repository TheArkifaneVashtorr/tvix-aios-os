# Decision 2026-09-02 — tier-A Cowork bubble parked; the desktop app's Code tab is the operator's builder

**Operator (evening, after the first working Cowork session):** "I never really
wanted claude to be in a VM, the environment is already really controlled … I
prefer building in claude co-work and I had intended for it to replace using
base claude code … save this as a flake that we will keep since maybe it has
uses later."

**What was built (kept):** `nixosModules/cowork.nix` + `egressBroker` +
`basketStore` + `claudeManagedSettings`: Claude Desktop running as a dedicated
user inside a network namespace whose only exit is the audited TLS-terminating
broker, one encrypted basket as its workspace, locked settings, display over
waypipe. Twenty field bugs fixed the same day; `nix flake check` covers it
(`cowork-eval`, `managed-settings*`, `integration`), so it does not rot.
Anthropic's Linux Cowork always executes tasks in a QEMU VM that has no Nix,
no host tooling and, in the bubble, no network beyond the broker — it cannot
build this machine's flakes. That was tier A by design (brief §5.1), not the
operator's goal for day-to-day work.

**Decision:**
1. `services.cowork.enable = false` on `core`; the module and its checks stay
   in the flake ("the flake we keep"). Re-enable = one line + `cowork-up`.
2. The operator's primary interface is the desktop app on the host, as the
   operator, unconfined (`hosts/core/claude-desktop.nix`): the **Code tab**
   (Claude Code with a GUI, sessions on `~/nixos-agent-env`, builds and sudo
   in its terminal) replaces the bare CLI. The **Cowork tab** remains
   available there for VM-sandboxed document/browsing/scheduled work.
3. No broker or netns for the operator's instance (machine is single-purpose
   and controlled). Auditing the operator's own traffic can be added later by
   pointing that instance at a broker with the CA in the operator's keyring.

**Consequences:** Phase 4b gate is closed as "built, verified, parked" (no
live acceptance required). The workspaces mini-phase (per-flake Claude homes)
now targets the desktop's Code tab sessions. The operator should tear down
the leftover bubble state at the next switch: `nix develop -c bash -c 'sudo "$(command -v basket)" teardown
cowork-workspace --runtime-dir /run/baskets'` (basket lives in the dev shell, not on the system PATH) (the tmpfs workspace is not
written back — copy anything wanted out first) and optionally
`sudo rm -rf /var/lib/claude-app` (10 GB sparse VM image + app state).
