# Operator packet

## brief.md §3 — the six invariants (verbatim)

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

## brief.md §7 — the phase-gate sentence (verbatim)

> Each phase ends with a test I can run. Do not start the next phase until the previous
> phase's test passes and I have said so.

## brief.md §8 — how to work (verbatim)

- Terse. No preamble, no summaries of what you are about to do, no encouragement.
- Do not write code before Section 9 is resolved.
- Pin every flake input to an exact rev. No `follows` chains you have not checked.
- No secret material in the repo, ever — not in comments, not in test fixtures, not in
  example configs. Use placeholders and tell me what to populate out of band.
- When you take a package from `kissgyorgy/coding-agents` or any similar source, enumerate
  every permission-related default it sets and override them explicitly. Do not inherit
  yolo-mode defaults silently.
- If upstream has moved since Section 4, tell me before adapting. Do not silently work
  around a breaking change.
- Prefer failing the build over a runtime check. Assertions in the module system are worth
  more than documentation.
- One phase at a time. Commit at each phase boundary with a message that names the
  acceptance test.
- If something in this brief is wrong or internally inconsistent, say so. I would rather
  rewrite the spec than have you route around it.

## docs/OPERATIONS.md — START HERE block

### "Operator owns:" sentence

The START HERE block does not contain a literal sentence beginning "Operator owns:".
The equivalent list of what the operator owns lives in `docs/board/operator-model.md`
("What the operator owns, by type"):

- switches and reboots
- credentials and their homes
- DNS names and password files
- spend and top-ups
- physical file moves
- pauses and their lifting
- A/B/C decisions
- spec reviews
- "test passed"

### Every pause or hold in the START HERE block

- HELD: SB5 and SB6 (operator, 2026-09-06 08:55).
- HELD: Helm Home sub-project 1 (operator, same message: "will unfortunately need to wait").
- HELD: PW1glm/PW1kimi/PW1pro (the plan-writing measurement), by decision Q3, until five
  real plans have gone through the gate.
- "(4) HELD until you lift them: SB5, SB6, Helm Home sub-project 1."
- Switch #20 and the Helm Home run section: "Helm Home sub-project 1, HELD; when the
  operator lifts it: `Workflow({ name: 'plan', args: { spec:
  'docs/superpowers/specs/2026-09-04-helm-home-design.md', ... } })`."
- Parked by decision (`parked` rows): Cowork tier A; the Helm workspace buttons; wiring
  round 2's media service (superseded by the worlds plan); O7; device filters on
  user-scope units (unenforceable, recorded in the worlds plan).
- media W3b/W5b fix rounds paused at the operator's request (reviews cw2).

## docs/board/operator-model.md — in full

```
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
```

## docs/decisions — operator's verbatim words

### 2026-09-04-parallel-agent-workflows.md

> "I think perhaps adding either a deterministic scheduler based on dependency
> to allow for parallel agents, removing the isolation by generating persistent
> isolated or virtual flakes for the agents to work in during development or
> even LLM as judge to deploy the agents based on what it can note to be capable
> of parallel development. Discarding parallel agent workflows is a poor design
> choice."

### 2026-09-02-invariants-bind-agents-not-operator-apps.md

> "I don't care if apps talk to the internet, I just want better safeguards
> for Agents."

### 2026-09-02-amendment-softkey.md

> "It doesn't need to be age locked" — issued while the YubiKey was absent from USB and
> unprovisioned for age. **RETRACTED same day**: terminology collision (the operator read
> "age" as age/identity verification, not the `age` encryption tool). Clarified: the
> operator wants the YubiKey.

## Decisions the spec leaves to the operator

(anything under brief.md §3, an isolation grade, a name, spend, a credential's home, a
widening of an agent's reach)

- Whether to veto the seat lane's dsh-loopback-guard / unit-owned-socat-forwarder design
  (flagged explicitly in START HERE as "a DECISION the operator may still veto").
- Whether to veto the orchestrator guard's fail-closed-on-faults / fail-open-on-missing-
  evidence policy (also flagged as a decision to veto).
- Lifting the SB5/SB6 hold.
- Lifting the Helm Home sub-project 1 hold.
- Lifting the PW1glm/PW1kimi/PW1pro hold (decision Q3, five real plans through the gate).
- Answering the seat-driver spec's three open questions (the driver's own row,
  Anthropic-on-OpenRouter rungs, the class vocabulary) —
  `docs/superpowers/specs/2026-09-06-operator-seat-driver-design.md`.
- Answering the telemetry-1 plan's two open questions (T3M as its own typed task; T10a on
  the live rows without T6) — `docs/superpowers/plans/2026-09-06-telemetry-store-1.md` §Questions.
- Spend: OpenRouter top-ups above the current $32.23 / no-preload-above-$100 ceiling; the
  Claude weekly budget ceiling.
- Credential homes: the identity file location and backup (invariant 4 / the softkey
  amendment — `~/.config/basket/identity-core.txt` was a throwaway, deleted; the operator
  side of full-disk-encryption status on `core`).
- Basket classification grades (`local-only | redacted | permitted`) per basket — brief §5.2.
- Any widening of an agent's reach: promoting agent-authored code between baskets
  (invariant 6), brokering an operator app that currently talks to the internet directly
  (explicitly named as "a separate design, not a retrofit" in the egress-invariant
  decision), or granting Discord/other basket access beyond what's already decided.
- Physical file moves and DNS names / password files (operator-model.md, unconditional).
- "Test passed" sign-off at every phase boundary (brief §7).
- A/B/C design decisions and spec reviews generally (operator-model.md).
- Switches and reboots (build-only rule; the operator alone runs `nixos-rebuild`/switch).
- Section 9 of brief.md itself — six unresolved design questions (basket granularity,
  scrub pass, Hermes-vs-OpenClaw overlap, broker implementation, router choice, node3
  rework) that must be answered back to the operator before Phase 1 begins.
