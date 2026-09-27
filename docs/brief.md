# Build brief — NixOS agent environment with encrypted data baskets

You are working with me in Claude Code on a NixOS host. This is a build brief, not a
conversation starter. Read all of it before proposing anything.

---

## 0. How to use this brief

- Sections 1–6 are the spec. Section 7 is the work plan. Section 8 is how I want you to
  operate. Section 9 lists things I have not decided.
- Section 4 contains upstream facts gathered on 2026-09-02. Several of the projects
  involved are in developer preview and change weekly. **Verify anything in Section 4
  against the actual repo or docs before you write code that depends on it.** If you find
  it is stale, say so explicitly and tell me what changed before continuing.
- Do not begin Phase 1 until you have answered Section 9 back to me and I have confirmed.

---

## 1. Context and assumptions

**Already done by me, before you start. Do not redo it.**

- NixOS installed on `core`, flakes and `nix-command` enabled.
- Claude Code installed and running (this session).
- `bubblewrap` and `socat` present in the system closure; `@anthropic-ai/sandbox-runtime`
  installed for the optional seccomp filter. (The Ubuntu 24.04 AppArmor `userns`
  workaround in Anthropic's docs is not applicable on NixOS — do not add it.)
- `/dev/kvm` present and the `vhost_vsock` kernel module loaded.
- Private self-hosted git remote configured. This repo goes there, and — since
  2026-09-22 — to the public remote through the publish gate (invariant 7).
- Three YubiKeys enrolled for hardware auth.

**Hardware.**

| Host | GPU | CPU | RAM | Status |
|---|---|---|---|---|
| `core` | RTX 5090 32GB | Ryzen 9 7900X | 124GB | primary, has local registry |
| `node2` | RTX 3060 12GB | 5800X3D | 31GB | up |
| `node3` | RTX 4080 Super 16GB | — | ~32GB | **offline**, OS reinstall outstanding |

Flat 2.5GbE LAN, no VLANs today. Assume `node3` stays offline for the duration of
Phases 1–5 and design so it can be brought in later without rework.

**Constraints.**

- Removed 2026-09-22 (decision `docs/decisions/2026-09-22-public-project.md`): the
  constraint read "Code lives on self-hosted git only. Nothing goes to GitHub, Google,
  or Microsoft services." The project is public; what stays private is named in
  `docs/ledger/publish.toml`, not by a blanket rule.
- I have run NixOS before but this is a from-scratch flake. Assume competence, not
  familiarity with any specific module in use here.

---

## 2. Objective

> Rewritten 2026-09-22 (decision `docs/decisions/2026-09-22-freeze-and-triage.md`). The
> 2026-08 objective is kept below for the record.

**tvix-aios** is an AI-native operating system: NixOS as the declarative model, tvix as
its Rust evaluator and store, and the infrastructure to run VMs and agent workflows as
part of the base system rather than as tooling installed on top. The OS owns the agent
runtime the way a conventional OS owns processes: VM lifecycle, workflow scheduling,
egress policy, credential injection, evidence and telemetry, and build-time
classification of what may leave the machine.

The lab on `core` is the reference deployment, not the product. A subsystem in this
repository earns its place by becoming part of the OS image, or by being a test of it.
Anything that only serves the lab is scaffolding and is removed when the OS no longer
needs it.

Public from the start: **this repository is the OS's repository of record** and goes
public from a cleaned snapshot under GPL-3.0 through the publish gate (invariant 7), as
decided 2026-09-21 (`docs/decisions/2026-09-21-public-repo-answers.md`) and confirmed
2026-09-22 after a contradictory sentence stood here for a day. The fork
`TheArkifaneVashtorr/tvix-aios` stays an untouched mirror of upstream tvix, consumed as a
flake input for the tvix crates. tvix is a library first (evaluator and nix-compat); it
becomes the system evaluator and store when the fork carries those components.

**The project, since 2026-09-22 (decision `docs/decisions/2026-09-22-public-project.md`).**
tvix-aios is an open-source, easy-to-use, memory-safe (Rust) NixOS-based AI-native
operating system that ships generation as OS functions — image, video, audio, text and
code — and ships the factory as a feature. Contributors install the OS on their own
hardware; a VM on their machine runs an agent seat logged in with their own subscription
LLM, takes tasks they accept from the project's public queue, and sends the result back
as a reviewed contribution. "Donating tokens" is letting that seat take project tasks. The
project owns three things: **the plan** (what the tasks are, decided by vote), **the
distribution** (who gets which task) and **the ledger** (the public account of what each
contributor's tokens produced). A seat runs only on the contributor's own hardware, under
their own login, on tasks they accepted; no contributor's allowance is ever routed through
anyone else's broker. Roadmap decisions are proposals with a vote and a public decision
file; the operator is the maintainer of last resort and the only one who touches the live
host `core`.

**Measurable goals.** Every wave names which of these it moves; a wave that moves none
is not dispatched.

1. **It builds in public.** This repository's flake evaluates and its Rust workspace
   (the daemon) compiles against the fork's tvix crates, in CI, from a clean
   clone of the public snapshot. Amended 2026-09-26 on the operator's word: the guard
   crate (IS23r, parked) leaves this goal and returns with goal 2. Goal 1 is done at the
   first green CI run on the public repository. Status 2026-09-26: a clean clone of the
   export passes `nix flake check --no-build`, and `aios-public-build` builds; CI (PL25)
   and the export writer (PL24) remain. The next focus is goal 2, guest first
   (`docs/planning/2026-09-26-next-goal.md`).
2. **One agent workflow runs on the OS image end to end.** Boot a VM from the image, run
   a seat, land a reviewed change, with every byte crossing the broker; the evidence
   store records it.
3. **A contributor's seat lands a task.** The public task list exists, and one task has
   been completed by someone who is not the operator, from a seat on their own machine
   under their own LLM subscription, reviewed and merged by the project and credited in
   the public ledger.
4. **A world runs as an OS function.** A generative world (the ComfyUI worlds on `core`
   are the first) boots as a service of the image, is driven by its search loop
   unattended, and its picks land in the evidence store. Added 2026-09-22 on the
   operator's word that the worlds are a functional part of the operating system.
5. **The surface area shrinks.** Operator decisions are taken on the Helm with the
   recommended default preselected, and the count of chat questions per landed task
   falls; both derived from the `ledger/operator` stream, never typed. Added
   2026-09-22 (`docs/concepts/2026-09-22b-surface-area-of-control.md`).
6. **No AI on user data, by construction.** No model, local or remote, reads a byte of
   a user's data the user did not declare for it (invariant 8); the declaration is Nix
   and the default is none. Measured: every world and seat input is covered by the
   classification assertion, a negative control that binds an undeclared path into a
   world fails the build, and a world's learning loop (the telemetry it learns from:
   dwell, saves, ratings) is itself a declared, on-box data class. Added 2026-09-22 on
   the operator's word: "nobody is gonna trust a system like that" without it.

**Product direction: the Helm is a catalog of apps, and AI helps everyone maintain it.**
Added 2026-09-25 on the operator's word. Profile switching on the Helm (abandoned
2026-09-21, `docs/decisions/2026-09-21-profile-switching-abandoned.md`) was one attempt
at the idea recorded here. An **app** is a public flake that declares an isolated space
(a microVM, a lane or a sandboxed user unit), with its inputs, permissions and egress
pinned. The **Helm** lists apps and installs one in one click. An install switches that
one space, never the whole system, so it cannot break anything else. Because NixOS
composes, the **compatibility layer** (keeping every app working as nixpkgs and the image
move) is maintained by everyone: each app flake carries checks (it boots, it launches, it
stays inside its egress policy). A breakage becomes a task on the public queue, and any
contributor's seat can land the fix through review (goal 3). The evidence store shows,
per app, whether it works today. The goals serve this direction: public app flakes must
build in public (goal 1), a world is an app that generates (goal 4), and "repair app X
after the bump" is the typical contributor task (goal 3). The first catalog entry is
planned as gaming (Steam and Discord) in its own space, after goal 1. The module is
absorbed into this repository unwired on 2026-09-25. Known hard parts:
- GPU apps may need a namespace sandbox rather than a VM, so an app declares its kind of
  space.
- One-click install runs someone else's code, so apps pass review, pin their revisions
  and carry build-time classification of what they may reach.
- The first version is one app end to end, not a store.

<details><summary>Objective as written 2026-08 (superseded)</summary>

A declarative NixOS environment where multiple AI agent harnesses run in graded isolation,
each seeing only an explicitly declared, encrypted subset of my data, with all outbound
traffic passing a chokepoint I control. The same project environment must reproduce
identically on any node from the flake plus one YubiKey.

Harnesses in scope: **Claude Cowork**, **DeepSeek Harness (dsh)**, **Hermes Agent**,
**OpenClaw**.

</details>

---

## 3. Invariants

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
7. Nothing tracked in this repository reaches a public remote except through the publish
   gate: every tracked path is classified in `docs/ledger/publish.toml`, and a published
   path carrying a private literal fails the build.
8. No model — local or remote, a seat's or a world's — reads user data the user did not
   declare for it. The declaration is Nix (invariant 5), the default is none, and a
   world's own learning signal (what the user dwelt on, saved, rated) is user data under
   this rule. Added 2026-09-22 (operator: "No AI on any user data should also be an
   underlying goal of the operating system").

Re-ratified 2026-09-21 after the rules audit (decision 55a, docs/decisions/2026-09-09-redesign-answers.md:68; verdicts docs/ledger/rules.toml, KN14): all seven kept verbatim.

---

## 4. Upstream facts as of 2026-09-02 — verify before relying on

> Superseded in place 2026-09-21 (55a). §4 → `docs/upstream-verification-2026-09-02.md` and each subsystem's context block. The text below is kept for the record.

### Claude Cowork

- Anthropic shipped an official Claude Desktop Linux beta on 2026-06-30, distributed as a
  `.deb` from their own apt repo.
- The official build ships its own native Cowork VM backend: `cowork-linux-helper`,
  `virtiofsd`, a `smol-bin` guest image, and QEMU/OVMF, speaking a vsock RPC protocol.
- It **hard-requires `/dev/kvm` and `vhost_vsock`, with no software-emulation fallback.**
- Per Anthropic, Cowork runs the Claude Code agent harness inside a Linux VM with
  additional sandboxing, network controls, and filesystem mounts.
- The earlier reverse-engineered Linux backends (`patrickjaja/claude-cowork-service`,
  `johnzfitch/claude-cowork-linux`) are deprecated or superseded. **Do not build on them.**
- Nix packaging: `github:nmcbride/claude-desktop-nix` repackages the official `.deb`,
  pinned in `package.nix` and auto-bumped from Anthropic's apt index.
  Also `github:Mowerick/claude-desktop-nix` (buildFHSEnv). Evaluate both; pick one; pin it.

**Design consequence: do not nest Cowork inside a microvm.** It already runs its own VM.
Nesting means nested KVM on the 7900X for zero added isolation. Cowork runs on the host
under a dedicated UID in its own network namespace with a virtiofs mount pointed at a
decrypted basket.

### Claude Code sandbox — reuse it, do not reimplement it

Source: `https://code.claude.com/docs/en/sandboxing`. Relevant because Cowork runs this
harness, so these settings apply inside Cowork too.

- Linux enforcement is bubblewrap for filesystem isolation plus a proxy for network,
  relayed by socat. Optional seccomp filter adds Unix-socket blocking.
- `sandbox.credentials.files` and `.envVars` support `"mode": "mask"`: the sandboxed
  command sees a per-session sentinel, and the proxy substitutes the real value on egress
  to hosts named in `injectHosts`. **This is the credential-injection design I specced,
  already implemented.** Requires `network.tlsTerminate` so the proxy can see request
  contents.
- `network.strictAllowlist` denies non-allowlisted hosts instead of prompting.
  `allowManagedDomainsOnly` and `allowManagedReadPathsOnly` in managed settings prevent
  local widening. `failIfUnavailable: true` makes a missing sandbox a hard failure.
  `allowUnsandboxedCommands: false` kills the `dangerouslyDisableSandbox` escape hatch.
- `sandbox.network.httpProxyPort` / `socksProxyPort` point Claude Code at a custom proxy.
- **Documented limitation:** by default the built-in proxy does not terminate or inspect
  TLS, so it makes allow decisions from the client-supplied hostname. Anthropic
  explicitly notes domain fronting can reach hosts outside the allowlist, and recommends a
  custom TLS-terminating proxy where the threat model requires it.

**Design consequence:** two layers, not one. Claude Code's built-in sandbox is the inner
layer, configured through NixOS-generated **managed settings** so the policy is declarative
and locally unmodifiable. My broker is the outer layer, terminating TLS, and is what
`httpProxyPort` points at.

### DeepSeek Harness (dsh)

- MIT, Node.js, developer preview, built on the Cordis meta-framework with a micro-kernel
  design where model adapters, tool registries, **sandboxing environments**, session state
  handlers, filesystems, the agent loop, and the UI are all replaceable plugins.
- Ships an append-only event log. Has an MCP client, Agent Client Protocol support, and
  reads `AGENTS.md` / `CLAUDE.md`.
- DeepSeek warns of compatibility-breaking changes and **is not accepting external pull
  requests**, directing contributors to build plugins instead.

**Design consequence:** implement basket mounting and egress policy as dsh plugins rather
than wrapping dsh externally. Pin to an exact commit; assume plugin re-ports each bump.

### Hermes Agent

- Nous Research, MIT, launched February 2026. v0.19.0 as of July 2026 — check current.
- Profiles system: each profile has `config.yaml`, a `SOUL.md` identity file, a
  SQLite-backed memory store, its own gateway process, and cron definitions. Memory is
  local SQLite with FTS5.
- Writes reusable skills after completing tasks — i.e. it generates executable code that
  persists.

**Design consequence:** a Hermes profile maps cleanly onto one basket (config + SOUL.md +
memory store + skills dir). Skills go in a write-only region subject to invariant 6.

### OpenClaw

- Formerly Clawdbot / Moltbot. MIT, long-running Node.js gateway process. Routes messaging
  platforms (WhatsApp, Telegram, Discord, Slack) to an agent that runs shell commands,
  drives browsers, and manages local files. Memory stored as Markdown on disk.
  Dashboard defaults to port 18789.

**Design consequence:** this is the untrusted-input tier. Attacker-authored text arrives
over a messaging adapter and reaches a shell-capable agent. Own microvm, no shared
baskets, no `local-only` data ever, tightest allowlist, dedicated router key.

### Nix packaging and isolation substrate

- `github:numtide/llm-agents.nix` — daily-updated agent package set with a binary cache at
  `cache.numtide.com`. Preferred source for CLI agents.
- `github:kissgyorgy/coding-agents` — packages `hermes-agent` and `openclaude` with Home
  Manager modules, but **configures everything in yolo mode by default**
  (`--dangerously-skip-permissions`). Use the derivations; override every default.
- `github:microvm-nix/microvm.nix` (note: moved from `astro/`). Hypervisor share support
  differs: firecracker supports no 9p or virtiofs shares; cloud-hypervisor supports
  virtiofs but not 9p. **Baskets need virtiofs → cloud-hypervisor or qemu only.**

---

## 5. Architecture

### 5.1 Placement tiers

| Tier | What | Isolation |
|---|---|---|
| A | Claude Cowork | Host, dedicated UID, own netns, virtiofs basket mount. Cowork's own VM is the inner boundary. |
| B | dsh, Hermes | microvm.nix guest, cloud-hypervisor, virtiofs basket, own netns |
| C | OpenClaw | microvm.nix guest, hardest policy, no shared state with anything |
| D | Ad-hoc shells | bubblewrap |

### 5.2 Data baskets

A basket is a content-addressed encrypted archive plus a manifest:

```
id:             work-notes
classification: local-only | redacted | permitted
mount:          /data/notes
access:         ro | rw
```

- Encryption with `age` + `age-plugin-yubikey`, all three keys as recipients.
- Host decrypts into tmpfs and exposes it to the guest over virtiofs. **The key never
  enters the guest.**
- `local-only` baskets are mountable only into agents whose netns has no route off-box.
  Enforce this in the NixOS module as an assertion, not by convention — a config that
  violates it must fail to build.
- `baskets.lock` pins content hashes and load order so environments are identical across
  nodes.

### 5.3 Egress, two layers

- **Inner:** Claude Code / Cowork built-in sandbox, configured via NixOS-generated managed
  settings. `strictAllowlist`, `failIfUnavailable`, `allowUnsandboxedCommands: false`,
  `allowManagedDomainsOnly`, `allowManagedReadPathsOnly`, plus `credentials` entries for
  every provider key. Consider `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`.
- **Outer:** my broker. One per netns, default-deny, TLS-terminating, allowlist by agent
  class, structured audit log per request: agent, basket set, destination, bytes, verdict.
  Claude Code's `httpProxyPort` points at it.

### 5.4 Model router

A single OpenAI-compatible endpoint on `core`. All four harnesses point at it; none talks
to a provider directly. The classification table lives in Nix:

- `local-only` → local weights on `core`'s 5090 (Hermes / DeepSeek open weights via vLLM
  or llama.cpp)
- `redacted` → frontier endpoint, after a scrub pass
- `permitted` → frontier endpoint

Per-agent router keys with independent scope and rate limits. Treat the scrub pass as
defense in depth only — routing by classification is the actual control.

### 5.5 GPU

Inference lives **outside** the sandbox tiers, on the host. The router is the boundary.
Do not attempt GPU passthrough into microvms.

---

## 6. Repo layout

```
flake.nix
  nixosModules/
    basketStore.nix        # decrypt, tmpfs, virtiofs export, classification assertions
    egressBroker.nix       # per-netns TLS-terminating proxy + audit log
    modelRouter.nix        # endpoint + classification policy
    agentSandbox.nix       # microvm/bubblewrap generator
    claudeManagedSettings.nix
  lib/mkAgent.nix          # { harness, baskets, egress, placement }
  homeManagerModules/
    familiar.nix           # shell, editor, keybinds — the cross-instance UX layer
  hosts/{core,node2,node3}/
  projects/<name>/{agents.nix,baskets.lock}
```

Use `impermanence` so undeclared state cannot survive a reboot.

---

## 7. Phases and acceptance tests

> Superseded in place 2026-09-21 (55a). §7 → the charter's increments (`docs/concepts/2026-09-09a-redesign-charter.md` §6) and `docs/superpowers/plans/`. The text below is kept for the record.

Each phase ends with a test I can run. Do not start the next phase until the previous
phase's test passes and I have said so.

**Phase 1 — closeout.** The mechanical closeout (increment 0): UI1 fast-forwarded, SD11b
and SD11c integrated, the broker-secret row closed on one command's evidence, the PW1 keys
closed with rows, the usage backfill run; the usage-ingest timer plus backfill, the W6 fix
round, HH1's fix round then HH2–HH4 typed.
*Test:* the derived brief shows no legacy-open row, no approved-not-integrated key, and the
store's dollar line covers the whole broker log.

**Phase 2 — the frame.** The subsystem manifest and its assertion, the rules audit, the
reserved namespace, the routing `area` column and the runner's rung declaration, the
`integrated` state and refusal, the bug ledger and the patches ledger validator, the unit
cap in `seat-submit`, the OAuth/Proton Pass/router spike (increment 1). Specs written for
the trio of increment 2.
*Test:* the manifest asserts its paths, the audit's verdicts are applied, and the reserved
namespace is asserted.

**Phase 3 — Platform, Seat/Harness, Factory.** The patch series and ledger, the Nix-built
harness payload, the dsh-harness absorption; the drive launch at `danger-full-access`, the
three hooks, the off-tree memory store, N seats with allocated ports; the graph runner, the
agent registry with generated shims, the bash executor, the bug workflow's rungs and its
re-resolver node, the batch-API draft node (increment 2). Specs written for the trio of
increment 3.
*Test:* a seat launches through the harness, the graph runner executes its rungs, and the
patch ledger records the series.

**Phase 4 — Helm, Evidence, Generation.** Helm's state-and-action API on a second port,
web-first, seat lifecycle writes only, the engagement stream, the patch queue view; the
`area` field everywhere, the generated status page, the engagement store and its
counts-only data class, the ingest under a timer; comfy-worlds sub-projects 2 and 3, the
on-demand units and Caddy on core, the rules mutator, media absorbed (increment 3). Specs
written for the pair of increment 4.
*Test:* the status page renders from the generated sources, and the engagement store
counts-only read holds.

**Phase 5 — Isolation, Knowledge, and the remaining absorptions.** LAN access with per-site
auth and the amended brief §10 and loopback assertion, the private-overlay phase typed but
not built, the OAuth/router outcome, the re-ratified invariants; the generated CLAUDE.md
and AGENTS.md from the one rules source, the handoff-only narrative, the renumbered phases;
gaming, nixos-skill, codex, openai-lab and chatgpt-work absorbed by subtree merge with
prefixed live keys (increment 4).
*Test:* nothing on this machine is reachable from beyond the LAN, and every absorbed
project's live keys carry their prefixed names.

Original phases (superseded)

**Phase 1 — basket crypto.** CLI only, no agents. Encrypt, decrypt, manifest schema,
`baskets.lock`.
*Test:* encrypt a basket, decrypt with YubiKey A, confirm the tmpfs mount disappears on
teardown, confirm decryption fails with no key present.

**Phase 2 — egress broker.** Per-netns, default-deny, TLS-terminating, audit log.
*Test:* from inside a netns, `curl` an allowlisted host succeeds, a non-allowlisted host
fails, and both appear in the audit log with correct verdicts. Attempt a domain-fronted
request and confirm the TLS-terminating layer catches what a hostname-only allowlist
would not.

**Phase 3 — classification assertion.** Wire the `local-only` rule into the module system.
*Test:* a config mounting a `local-only` basket into a network-capable agent **fails
`nixos-rebuild build`** with a clear error.

**Phase 4 — Cowork.** Flake input, dedicated UID, netns, virtiofs basket, managed settings
generated from Nix.
*Test:* Cowork starts, its VM boots, it can read and write the basket and nothing outside
it, and its traffic appears in the broker's audit log. Confirm managed settings are not
overridable from the project directory.

**Phase 5 — model router.** Local Hermes weights + one frontier endpoint, classification
table in Nix.
*Test:* a `local-only` prompt never appears in outbound traffic to any frontier host,
verified from the broker log, not from the router's own claims.

**Phase 6 — dsh.** Basket-mount plugin and egress-policy plugin. Exact commit pinned.
*Test:* dsh runs a task using only its declared basket; the append-only event log
reconciles with the broker log.

**Phase 7 — Hermes.** microvm guest, profile mapped to a basket, skill-promotion gate.
*Test:* a skill Hermes writes lands in the review region and cannot be executed by any
other agent until I promote it.

**Phase 8 — OpenClaw.** Most isolated. One messaging channel only to start.
*Test:* a crafted hostile message over the channel cannot reach any basket other than
OpenClaw's own, and cannot reach a non-allowlisted host.

**Phase 9 — portability.** Rebuild `node2` from flake + YubiKey.
*Test:* the environment is byte-identical where it should be, and I cannot tell which node
I am on from inside a project shell.

**Phase 10 — publication.** The publish gate: every tracked path is classified in
`docs/ledger/publish.toml`, a build-time check refuses a published path that carries a
private literal, and a negative control proves the check can fail. Nothing is pushed.
*Test:* `nix build .#checks.x86_64-linux.publish-gate -L --no-link` and
`nix build .#checks.x86_64-linux.publish-gate-negative -L --no-link` both succeed, the
second only because a planted private string in `tests/fixtures/publish/` made the
validator FAIL, and `nix flake check -L` stays green.

---

## 8. How I want you to work

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

---

## 9. Resolve before Phase 1

> Superseded in place 2026-09-21 (55a). §9 → `docs/decisions/`. The text below is kept for the record.

1. **Basket granularity.** Per project, per data class, or per agent? Cowork is only useful
   with reasonably broad filesystem scope, which fights fine-grained baskets. Propose a
   concrete definition of "project scope" and defend it.
2. **Scrub pass.** Do we build one at all, given that classification-based routing is the
   real control and a scrub pass creates false confidence? Argue both sides.
3. **Hermes vs OpenClaw overlap.** They are near-identical in shape: persistent gateway,
   messaging adapters, local memory, self-generated skills. Is there a reason to run both,
   or is one a fallback? If both, how do we prevent memory drift between them?
4. **Broker implementation.** Existing TLS-terminating proxy configured declaratively, or
   purpose-built? Name candidates and pick one.
5. **Router.** Which OpenAI-compatible router, and does it support per-key scoping and
   per-key rate limits well enough to be the enforcement point, or does that belong in the
   broker instead?
6. **node3.** Anything in the design that would need rework when a 16GB card rejoins,
   versus what can be deferred cleanly.

---

## 10. LAN access, and what stays out of scope

The LAN reaches this machine only through sites declared in `services.lan-access`. Each
site fronts one loopback upstream, serves TLS from Caddy's internal CA — whose root I
install by hand on each client that may see it — and asks for one credential of its own, a
password hash kept outside the Nix store, or WebAuthn the day a site needs it. What is not
declared is not reachable: the build refuses any other bind off loopback.

A private overlay — WireGuard declared in Nix, keys outside the store, no coordinator — is
its own later phase with its own acceptance drill and 'test passed' gate; until it passes,
nothing on this machine is reachable from beyond the LAN. Its shape is typed at
`docs/concepts/2026-09-11-private-overlay.md`.

Multi-user. Access from outside the LAN except through the overlay once gated. The Pixel.
Attestation or measured boot. Raise them if a Phase 1–9 decision would foreclose them later,
otherwise leave them alone.
