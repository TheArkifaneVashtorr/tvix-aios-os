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
- Private self-hosted git remote configured. This repo goes there and nowhere else.
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

- Code lives on self-hosted git only. Nothing goes to GitHub, Google, or Microsoft services.
- I have run NixOS before but this is a from-scratch flake. Assume competence, not
  familiarity with any specific module in use here.

---

## 2. Objective

A declarative NixOS environment where multiple AI agent harnesses run in graded isolation,
each seeing only an explicitly declared, encrypted subset of my data, with all outbound
traffic passing a chokepoint I control. The same project environment must reproduce
identically on any node from the flake plus one YubiKey.

Harnesses in scope: **Claude Cowork**, **DeepSeek Harness (dsh)**, **Hermes Agent**,
**OpenClaw**.

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

---

## 4. Upstream facts as of 2026-09-02 — verify before relying on

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

Each phase ends with a test I can run. Do not start the next phase until the previous
phase's test passes and I have said so.

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

## 10. Out of scope for now

Multi-user. Remote access from outside the LAN. Anything touching the Pixel. Attestation
or measured boot. Raise them if a Phase 1–9 decision would foreclose them later, otherwise
leave them alone.
