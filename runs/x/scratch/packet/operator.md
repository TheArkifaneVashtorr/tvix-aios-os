# Operator packet

## brief.md §3 — Invariants (verbatim)

These are not negotiable. If a design decision would violate one, stop and raise it.

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

## brief.md §7 — phase-gate sentence

"Each phase ends with a test I can run. Do not start the next phase until the previous
phase's test passes and I have said so."

## brief.md §8 — how to work (in full)

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

## OPERATIONS.md START HERE block

"Operator owns:" sentence — literal text is not present verbatim in the current START HERE
block (2026-09-14 18:40 CDT, session 23). The board's own derived model file
(`docs/board/operator-model.md`) states it points to the board's START HERE for the live
"Operator owns:" sentence, but the current START HERE paragraph is a status/handoff report
and contains no line beginning "Operator owns:". Treated as MISSING from the live board;
the static list from `operator-model.md` is captured separately below.

Pause/hold sentences found in the current START HERE block:

- "HELD: `flake-check` FAIL at HEAD — `seat-vm` (`tests/integration/seat-vm.nix:170`
  `maxUnits = 2` vs `waveJobs` default 8; IS10 fixes it); 13 rung-2 escalations await
  `claude/review` (FIX5d HH1b HH1c HH4b IS1b IS1c IS3b KN1b PR1b PR1c PR1d W6b W6c); the
  Claude spend ledgers were never ingested (no measured headroom; the 5-hour window is the
  binding limit — nine parallel Fable revisers burned it in 45 min; sequential is the
  rule); 486 stale run logs, no reaper; `batch-plan.js` still carries the fill defects
  until the chip lands."
- "NEXT (operator's word): land the nine in the order above, or name which first; then the
  rung-2 escalations and switch #30 planning."

No other sentence in the current START HERE block begins "paused" or is phrased as a pause.

## docs/board/operator-model.md (in full — exists)

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

[... six invariants, identical to brief.md §3 above ...]

## Where the live items are

- the board's START HERE, the "Operator owns:" sentence and every "paused" sentence; `evidence bundle`'s gap list
```

## Operator's verbatim words — decision files

### 2026-09-04-parallel-agent-workflows.md

Operator, decided 2026-09-04, overruling a plan's sequential-only judgement call, quoted
verbatim in the decision:

> "I think perhaps adding either a deterministic scheduler based on dependency
> to allow for parallel agents, removing the isolation by generating persistent
> isolated or virtual flakes for the agents to work in during development or
> even LLM as judge to deploy the agents based on what it can note to be capable
> of parallel development. Discarding parallel agent workflows is a poor design
> choice."

### 2026-09-02-invariants-bind-agents-not-operator-apps.md

Operator, 2026-09-02 evening, at the spec gate for the gaming flake, verbatim:

> "I don't care if apps talk to the internet, I just want better safeguards
> for Agents."

### 2026-09-02-amendment-softkey.md

Operator directive, quoted in the (retracted) amendment: "It doesn't need to be age
locked" — later clarified by the operator as a terminology collision (the operator meant
age/identity verification, not the `age` encryption tool); the operator wants the YubiKey.
No other operator quotation appears in this file; the rest of the document is the
orchestrator's applied reading and retraction.

## Decisions the spec leaves to the operator

Section 9 of brief.md ("Resolve before Phase 1") is explicitly unresolved and requires
operator answers before Phase 1 begins:

1. Basket granularity — per project, per data class, or per agent (fights Cowork's need for
   broad filesystem scope).
2. Whether to build a scrub pass at all, given classification-based routing is the real
   control (argue both sides — unresolved).
3. Hermes vs OpenClaw overlap — run both or treat one as fallback, and if both, how to
   prevent memory drift between them.
4. Broker implementation — existing TLS-terminating proxy vs purpose-built; name candidates
   and pick one.
5. Router choice — which OpenAI-compatible router, and whether it (vs the broker) is the
   right enforcement point for per-key scoping/rate limits.
6. node3 — what in the design needs rework when the 16GB card rejoins, vs what can be
   deferred.

Additional operator-reserved categories, per `docs/board/operator-model.md` ("What the
operator owns, by type"):

- switches and reboots
- credentials and their homes
- DNS names and password files
- spend and top-ups
- physical file moves
- pauses and their lifting
- A/B/C decisions
- spec reviews
- "test passed" (phase-gate sign-off, brief §7)

Also reserved per brief.md:
- §3: any change that would violate one of the six invariants ("stop and raise it").
- §5.1/5.2: isolation-grade placement decisions (basket classification: local-only /
  redacted / permitted; tier assignment A/B/C/D) are Nix-config-encoded per invariant 5,
  but the classification of a given data set and the tier a given agent runs at are
  operator calls, not something an agent infers.
- Naming: basket `id`s, project names (`projects/<name>/`) — not specified by the spec,
  operator-assigned.
- §8: spend/budget is never mentioned as agent-decidable; §5.4 model router keys and rate
  limits are policy the operator sets in Nix.
- Credential homes: invariant 2 and §5.3 require credentials be injected at the egress
  proxy — where each provider credential physically lives (which secret store, which
  YubiKey-gated path) is an operator decision, not specified by the brief.
- Widening of an agent's reach: any change to a basket's `access` (ro/rw), a basket's
  classification, an agent's placement tier, or its allowlisted egress hosts is, per
  invariant 5 and §8 ("no secret material," "prefer failing the build"), reviewable-in-diff
  Nix config the operator must approve — the spec never delegates this to an agent.
