# Decision — the Helm workspace buttons leave the live page until Helm Home (2026-09-04)

**Question (operator):** what should the Helm v1 page ("the switch") do about its
**Workspaces** section and "Open" buttons while Helm Home — the real home-screen
action surface — is still pending? A / B / C.

**Decision: C — remove the workspace buttons from the live page until Helm Home
ships.** `core` declares an empty workspace map, so the page renders no Workspaces
section at all (no heading, no open forms).

**Why:** a Console is not the user-friendly home-screen action. Popping a terminal
from the switch page is an operator's tool, not the home-screen flow a person
understanding the machine needs; the Helm Home verbs replace it when that phase
lands. Shipping the buttons now would bake a dead-end into exactly the surface Helm
Home exists to redesign.

**What stays:** the module capability — `services.helm.control.workspaces` — the
`helm-open-workspace` launcher, and their tests are untouched. The VM test still
declares a demo workspace (`tests/integration/helm-control-vm.nix:59`) and asserts
the open form renders, so the capability stays exercised and can simply be
re-declared on the host when Helm Home lands.

**Not recorded as coverage gaps:** none — the removal is a host-wiring and pinning
change only; `helm-unit`, `helm-control-eval`, `host-core`, and the VM test still
cover the module capability end to end.