# Operator model (derived; the board holds pauses and open items — this file never lists them)

## Preferences, ranked

- terse, no preamble (§8)
- privacy outranks everything, nothing leaves the machine (`2026-09-05-telemetry-store-decisions.md`)
- tool names read literally, plain words for a softkey (`2026-09-02-amendment-softkey.md`)
- tell me when the brief is wrong rather than route around it (§8)
- prefer failing the build over a runtime check (§8)
- one phase at a time, the operator says "test passed" (§7)
- deterministic first, isolated workspaces second, judgement last; never design parallelism out (`2026-09-04-parallel-agent-workflows.md`)
- falsifiable, not merely tested; unmeasured is debt; proxies declared (`2026-09-03-test-based-reality-amendments.md`)
- no secrets in the repo, placeholders out of band (§8)
- recommendations welcome, each with a measurable acceptance and an effort class (`docs/superpowers/specs/2026-09-05-planning-agent-design.md`)

## What the operator owns, by type

- switches and reboots
- credentials and their homes
- DNS names and password files
- spend and top-ups
- physical file moves
- pauses and their lifting
- A/B/C decisions
- spec reviews
- "test passed"

## The six invariants

(docs/brief.md §3 verbatim)

1. Decrypted basket contents exist only for the lifetime of the agent that mounted them,
   and only in tmpfs.
2. No agent process holds a provider credential on disk or in its environment in
   plaintext. Credentials are injected at an egress proxy.
3. Every byte leaving the machine crosses one chokepoint that can log the request and
   refuse it.
4. An environment is reproducible from `flake.lock` + `baskets.lock` + one YubiKey.
   Nothing else. If a step requires imperative setup, it is a bug in the design.
5. Policy — which data class may reach which model — is Nix configuration, reviewable in
   a diff. Not a runtime setting, not a dotfile an agent can edit.
6. Agent-authored code (Hermes skills, dsh plugins, OpenClaw automations) is never
   promoted from the basket it was written in to any other basket without my review.

## Where the live items are

- the board's START HERE, the "Operator owns:" sentence and every "paused" sentence; `evidence bundle`'s gap list
