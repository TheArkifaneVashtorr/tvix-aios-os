# Design spec — NixOS agent environment with encrypted data baskets

Date: 2026-09-02. Status: **pre-Phase-1, awaiting operator confirmation of
`docs/decisions/2026-09-02-section-9-answers.md`.**

Sources: `docs/brief.md` (the governing spec) plus the operator's cover instructions,
which add requirements the brief does not contain (§4 below). Where this document and
the brief conflict, the brief wins unless a flag in §6 says otherwise and the operator
confirms.

## 1. Objective (restated)

Multiple AI agent harnesses (Claude Cowork, dsh, Hermes Agent, OpenClaw) run in graded
isolation on NixOS. Each sees only an explicitly declared, encrypted subset of operator
data. All egress crosses a logging, refusing chokepoint. Any project environment
reproduces on any node from `flake.lock` + `baskets.lock` + one YubiKey. The brief's six
invariants (brief §3) are binding and restated nowhere — read them there.

## 2. Architecture

### 2.1 Placement tiers (per brief §5.1, confirmed)

| Tier | What | Boundary |
|---|---|---|
| A | Claude Cowork | Host process, dedicated UID, own netns, virtiofs basket mount; Cowork's own VM is the inner boundary. Never nested in a microvm. |
| B | dsh, Hermes | microvm.nix guest, cloud-hypervisor, virtiofs basket, own netns |
| C | OpenClaw | microvm.nix guest, hardest policy, no shared state with anything |
| D | Ad-hoc shells | bubblewrap |

### 2.2 Data baskets

A basket is the unit of **classification, encryption, and mounting** — one
classification per basket, never mixed (see decision Q1).

- Encrypted at rest with `age` + `age-plugin-yubikey`, all enrolled YubiKeys as
  recipients (two exist — `keys.toml` is the ledger; brief §1's "three" was
  wrong); any single key decrypts.
- Host decrypts into tmpfs; guests see plaintext only over virtiofs; the key never
  enters a guest.
- A **project** declares its baskets in `projects/<name>/baskets.lock` (content hashes +
  load order). Agents mount explicit subsets via `lib/mkAgent.nix`.
- `local-only` baskets mount only into agents whose netns has no off-box route —
  enforced as a module-system assertion; violating configs fail `nixos-rebuild build`.
- Agent-authored code (skills, plugins, automations) lands in a write-only review
  region inside the authoring basket. Promotion out of it is a reviewed git commit
  (invariant 6); the web portal (§4.1) later fronts this queue.

### 2.3 Egress: two layers

- **Inner** — Claude Code / Cowork built-in sandbox, driven entirely by
  NixOS-generated managed settings (`claudeManagedSettings.nix`): `strictAllowlist`,
  `failIfUnavailable: true`, `allowUnsandboxedCommands: false`,
  `allowManagedDomainsOnly`, `allowManagedReadPathsOnly`, masked credentials.
- **Outer** — the broker: one instance per netns, default-deny, TLS-terminating (local
  CA installed into each environment's trust store), allowlist per agent class,
  structured JSON audit log per request (agent, basket set, destination, bytes,
  verdict), and credential injection: agents hold per-session sentinels; the broker
  substitutes real values only on egress to the specific provider hosts. Real
  credentials rest age-encrypted to the YubiKeys and are decrypted into the broker's
  memory at service start — never onto disk in plaintext, never into an agent
  environment. Implementation choice: decision Q4.

### 2.4 Model router

One OpenAI-compatible endpoint on `core`; all harnesses point at it; none talks to a
provider directly. Classification table lives in Nix: `local-only` → local weights on
the 5090; `redacted` and `permitted` → frontier endpoint (no scrub pass for now —
decision Q2). Per-agent router keys. The router **applies** policy; the broker and the
netns topology **enforce and verify** it — Phase 5's acceptance test reads the broker
log, not the router's claims. Implementation choice: decision Q5.

`local-only` is defined precisely as: plaintext never leaves hosts the operator
controls, and inter-host legs (router → a future node3 backend) ride a WireGuard mesh.
This definition is fixed now so node3 can join without rework (decision Q6).

### 2.5 GPU

Inference runs on the host, outside all sandbox tiers. The router is the boundary. No
GPU passthrough into microvms.

## 3. Persistence matrix — what survives, where, and what never does

The operator requires this to be explicit. "Project environment" = one entry under
`projects/<name>/`.

**Persisted and shared across all nodes (via git on the self-hosted remote):**

- All Nix sources: modules, hosts, `lib/`, per-project `agents.nix`, injected-context
  files, `flake.lock`, every `baskets.lock`.
- All policy: classification table, egress allowlists, managed settings. Policy changes
  are diffs, nothing else.
- **Promoted** skills/plugins/automations — only after operator review.

**Persisted per project, never crossing project boundaries:**

- Encrypted baskets (ciphertext, content-addressed; may sync to any node — plaintext
  may not).
- Agent memory: Hermes SQLite store, OpenClaw Markdown memory, dsh event log — each
  lives *inside* that project's basket, encrypted at rest, mounted only into its own
  project's agents. No memory is ever shared between projects, between harnesses, or
  between tiers.
- Unpromoted agent-authored code — stays in the authoring basket's review region.
- Injected context (`CLAUDE.md`, `AGENTS.md`, `SOUL.md`, dsh context) — in git, but
  injected only into its own project's environments.

**Persisted on the host, outside every agent environment:**

- Broker audit logs (declared impermanence path on `core`/`node2`; append-only; agents
  cannot read or write them).
- The age-encrypted credential blobs the broker consumes.

**Cache class — persisted, never backed up, never secret (added 2026-09-02):**

- Model weights (`/var/lib/models`; interim `~/models`): public immutable
  artifacts, root-owned, read-only to the inference service, invisible to every
  agent tier (agents reach models only through the router over HTTP). Identity
  and integrity come from SHA-256 pins in the flake — the serving stack refuses
  a mismatched file, and re-provisioning any node is a verified re-download,
  not a restore. Excluded from restic paths.

**Never persisted anywhere:**

- Decrypted basket contents — tmpfs, gone with the mounting agent (invariant 1).
- Plaintext credentials — exist only in broker process memory during a session.
- Guest VM state — microvms are stateless; no writable disks beyond declared mounts.
- Anything undeclared — `impermanence` wipes it at reboot; undeclared state surviving
  is a bug.

**Orchestrator note:** Claude Code's own session memory (`~/.claude/.../memory/`)
belongs to the operator's host account, is global across projects, and is never mounted
into any agent environment.

## 4. Additions beyond the brief (operator cover instructions)

### 4.1 Web portal

All operator interaction with the *agent environments* moves to a custom, self-hosted,
LAN-only web portal: chat surfaces to the harnesses, the skill-promotion review queue,
broker audit log views, basket/policy diffs, and phase acceptance dashboards.
Authentication: WebAuthn against the three enrolled YubiKeys. Proposed as **Phase 10**
— it consumes interfaces Phases 2–8 produce (audit log schema, promotion queue,
router). Until it exists, interaction stays in this terminal. Flag §6.2 covers the
scope tension.

### 4.2 Per-environment injected context

Each project carries its own context set under `projects/<name>/`, generated per
harness by `mkAgent` (managed settings + `CLAUDE.md` for Claude-family, `AGENTS.md`
for dsh, `SOUL.md`/profile for Hermes). No context file is shared across projects
unless it is a reviewed copy in git.

### 4.3 Autolinting

`nixfmt-rfc-style` + `statix` + `deadnix` (Nix), `shellcheck` (shell), wired as a
`treefmt`/pre-commit flake check from Phase 1's repo bootstrap onward. Linting runs
every working turn and before every commit; `git config core.hooksPath githooks` is
set by the devShell so the pre-push local-only guard and pre-commit lint are not
optional. CI is the flake check itself (`nix flake check`) — no external CI service.

### 4.4 Planning/implementation split

Plans are authored at high effort by the orchestrator model; implementation is
delegated to cheaper subagents executing those plans task-by-task with review
checkpoints (superpowers executing-plans / subagent-driven-development). High-cost
model tokens go to planning, review, and verification, not mechanical edits.

## 5. Section 9 decisions

Full argumentation in `docs/decisions/2026-09-02-section-9-answers.md`. One line each:

1. **Granularity:** basket = one classification within one project; project = the
   flake-level environment unit; Cowork mounts a broad single-classification
   `workspace` basket.
2. **Scrub pass:** not built now; `redacted` class kept in schema and router table;
   revisit after Phase 5 audit-log review.
3. **Hermes vs OpenClaw:** both designed for, different trust tiers; Hermes deploys in
   Phase 7; OpenClaw activates only when a messaging channel is actually wanted.
4. **Broker:** mitmproxy (pinned; Nix-rendered addon carries allowlist/audit/
   credential-injection); runner-up Squid ssl-bump.
5. **Router:** Bifrost (declarative virtual keys, custom derivation) over llama-swap
   (nixpkgs) on the 5090; runner-up LiteLLM; broker holds the real frontier key.
6. **node3:** only two decisions land now — the `local-only` WireGuard definition and
   a multi-backend-capable router; all else defers cleanly.

## 6. Flags — inconsistencies and deltas the operator must see

1. **Brief §0 gate vs autonomy instruction.** The cover instruction says act
   autonomously; the brief says twice not to start Phase 1 before Section 9 is
   confirmed. Resolution applied: autonomy governs *within* a turn; the Phase 1 gate
   holds. This turn ends at the gate.
2. **"All interactions through the web portal"** conflicts with the brief's
   terminal-centric §8 and touches §10's "remote access" exclusion. Resolution
   proposed: portal is LAN-only (not remote access), added as Phase 10, and covers
   agent-environment interaction; orchestrating Claude Code itself through the portal
   (via the Agent SDK) is a separate later decision, raised here so Phases 1–9 don't
   foreclose it (they don't — the portal only consumes declared interfaces).
3. **"Fable 5.1" does not exist.** This session runs Claude Fable 5 — treated as the
   intended model.
4. **numtide binary cache** (`cache.numtide.com`) is a third-party trust decision. For
   security-critical closures the default here is source builds; enabling the cache is
   an explicit, reviewable flake change if build times hurt.
5. Upstream deltas found by the verification sweep are recorded in
   `docs/upstream-verification-2026-09-02.md`; anything marked **changed** supersedes
   brief §4 and was flagged to the operator before any dependent code.
6. **`kissgyorgy/coding-agents` is dropped**, deviating from brief §4/§8 (which
   assumed taking its derivations and overriding defaults). Verification found it
   materially misdescribed: no openclaw at all, an install-only hermes module with
   zero safety options, yolo only in shell aliases. `numtide/llm-agents.nix` packages
   all four harnesses and replaces it outright — nothing to inherit, nothing to
   override.

## 7. Roadmap

Phases 1–9 exactly as brief §7, unchanged, each ending at its acceptance test and a
commit naming that test. Phase 0 (this commit): repo bootstrap, spec, decisions,
verification, local-only git controls. Phase 10 (proposed): web portal. Lint tooling
lands with Phase 1's flake bootstrap.

## 8. Working agreements (how each turn runs)

Terse output. Plans before code; subagents implement. Lint every turn. No secrets in
the repo, placeholders only. Every flake input pinned to an exact rev, `follows`
chains checked. Upstream drift reported before adapting. Build-time assertions
preferred over runtime checks. One phase at a time; commits at phase boundaries name
the acceptance test. Push only to the allowlisted self-hosted remote — the pre-push
hook refuses everything else, including all public forges.
