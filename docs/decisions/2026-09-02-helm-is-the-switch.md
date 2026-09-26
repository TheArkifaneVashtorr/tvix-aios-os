# Decision 2026-09-02 — Helm is the switch

**Operator, 2026-09-02 late:** "It's supposed to be a no-code way to switch
between flakes." Asked which mechanism: "Both, on one page."

**Recorded:** Helm v0 (the status page, built the same evening) is the base
surface. Helm v1 adds, on the same loopback page, (1) a profile switch — the
host flake declares NixOS specialisations `gaming` and `media` beside the
`base` (builder/agents) profile, switched at runtime with the `test` action
by a root unit with a fixed allowlist and a polkit grant scoped to `start`;
(2) a workspace launcher — a terminal in a flake's dev shell running `claude`
with that flake's own memory; baskets stay a YubiKey step. Spec:
docs/superpowers/specs/2026-09-02-helm-v1-switch-design.md (rev 2, reviewed
by four Sonnet agents, **approved by the operator 2026-09-02 ~22:20**).

**Consequences:** the host wiring enables gaming and media inside
specialisations, not the base profile; every profile writes
`/etc/helm/profile`; the v1 plan is written after v0 and the wiring land.
