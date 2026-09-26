# Decision 2026-09-02 — the egress invariant binds agents, not the operator's apps

**Operator, 2026-09-02 evening, at the spec gate for the gaming flake:**
"I don't care if apps talk to the internet, I just want better safeguards
for Agents."

**Reading recorded:** brief §3 invariant 3 ("every byte leaving the
machine passes a chokepoint I control") and invariant 2 (credentials
injected at the proxy) bind the AI-agent harnesses and anything that runs
on their behalf (Cowork bubble, dsh, Hermes, OpenClaw, the media
container because it executes third-party code with GPU access). The
operator's own desktop software — Firefox, the Proton apps, the Claude
desktop app's operator instance, Steam and the launchers in the gaming
flake — talks to the internet directly, as it does today.

**Consequences:** the gaming flake opens nothing inbound and adds no
privilege, but does not broker Steam. The media flake stays brokered (it
is closer to an agent than to an app). Any future request to broker an
operator app is a separate design, not a retrofit of this reading.

**Also approved at the same gate:** all three specs
(docs/superpowers/specs/2026-09-02-{helm,gaming-flake,media-flake}-design.md)
as the basis for plans and factories.
