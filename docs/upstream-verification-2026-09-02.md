# Upstream verification — 2026-09-02

Brief §4 verified against live sources by 11 parallel research agents (9 verifiers, 2
candidate evaluators; ~130 web fetches). Statuses: **confirmed** = brief holds;
**partially-confirmed** = holds with deltas listed; **changed** = brief is stale on
that point. Per brief §8, every delta below is reported here *before* any dependent
code exists.

## Claude Desktop / Cowork — partially-confirmed

Confirmed: official Linux beta 2026-06-30, .deb from Anthropic's apt repo
(`downloads.claude.ai/claude-desktop/apt/stable`); Cowork runs tasks in a QEMU/KVM VM;
hard requirements /dev/kvm + vhost_vsock + qemu/OVMF/virtiofsd, no software fallback;
patrickjaja backend deprecated.

**Deltas:** (1) `johnzfitch/claude-cowork-linux` is *not* deprecated — actively
maintained unofficial research preview. Irrelevant to us (we build on the official
backend), but brief §4 is wrong on it. (2) `Mowerick/claude-desktop-nix` was archived
2026-08-20 and redirects to `numtide/llm-agents.nix`. (3) The names
`cowork-linux-helper` / `smol-bin` / vsock-RPC come from reverse-engineering
write-ups, not official docs (which confirm QEMU/OVMF/virtiofsd/vsock generically).

**Design impact:** the "evaluate both, pick one" packaging question collapses —
**pick `nmcbride/claude-desktop-nix`** (currently 1.40609.1, daily auto-bump CI, has a
NixOS module handling Cowork VM deps). Pin an exact rev; upstream bumps ~5×/month, so
bumps are deliberate diffs. Watch its Cowork KVM/virtiofsd probing on NixOS
(anthropics/claude-code#74605, #73568).

## Claude Code sandboxing — confirmed (all claims)

bubblewrap + socat-relayed proxy + optional seccomp; `mode: "mask"` with sentinel
substitution at the proxy for `injectHosts`, requires `network.tlsTerminate`
(fails safe without it); `strictAllowlist`, `failIfUnavailable`,
`allowUnsandboxedCommands: false`, `allowManagedDomainsOnly`,
`allowManagedReadPathsOnly`, `httpProxyPort`/`socksProxyPort`; domain-fronting
limitation documented, custom TLS-terminating proxy recommended — all as briefed.

**Additions:** `tlsTerminate` is labeled *experimental*; mask features are
version-gated (envVars mask ≥ v2.1.199, files mask ≥ v2.1.221, extract fields
≥ v2.1.224); `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` exists and also forces filesystem
isolation on; managed settings live at `/etc/claude-code/managed-settings.json` plus
`managed-settings.d/*.json` merged alphabetically, overriding all lower scopes.
Mask entries are honored only from user/managed/`--settings` scopes — never from repo
`.claude/settings*` (good: agents can't grant themselves injection).

**Design impact:** pin Claude Code ≥ 2.1.224. Two-layer egress design stands.

## DeepSeek Harness (dsh) — partially-confirmed

Confirmed: MIT, TS/Node monorepo, developer preview (Aug 13 2026), Cordis
meta-framework, everything-is-a-plugin (models, tools, skills, sessions, sandboxes,
storage, loops, scheduling, UI), append-only session log, breaking-changes warning,
no external PRs (community plugins via `dsh-plugin` topic). Current:
**v0.1.2-alpha.5** (released 2026-09-02; ~daily alpha cadence).

**Deltas:** ACP support is an automation-only ACP *server*, not generic client
support; a generic MCP client is not confirmed in docs (only a Memory MCP
integration); runtime reading of `AGENTS.md`/`CLAUDE.md` from user projects is
unverified; there are **no docs for writing filesystem/sandbox plugins** — only the
general plugin guide plus in-repo `fs/` (policy-based filesystem), `e2b/`,
`subprocess/` packages as reference implementations; official sandbox story leans on
E2B (cloud) — unacceptable here, so ours stays local.

**Design impact:** Phase 6 risk up, plan unchanged: pin exact version, write the
basket-mount and egress plugins following the in-repo `fs/` package conventions,
budget a re-port per version bump. Do not design around dsh's MCP or
AGENTS.md-reading until verified on the pinned version.

## Hermes Agent — partially-confirmed

Confirmed: MIT, launched 2026-02-25, profiles (`~/.hermes`,
`~/.hermes/profiles/<name>/`) each with config.yaml, .env, SOUL.md, skills, cron, own
gateway process; SQLite + FTS5; writes skills to `<HERMES_HOME>/skills/`.

**Deltas:** brief's v0.19.0 is stale — current is **v0.21.0 "Pantheon"**
(2026-08-31). Memory is the per-profile `state.db` (sessions+memory+state in one
SQLite file) plus a curated `MEMORY.md`, not a dedicated memory store.

**Security surface found (for Phase 7 module defaults):** profiles do NOT sandbox —
isolation is `HERMES_HOME` only, so our microvm is the real boundary, as designed.
Set: `approvals.mode: manual` (never `--yolo`/unattended-approve), `approvals.deny`
globs, `HERMES_WRITE_SAFE_ROOT`, gateway user allowlists + DM pairing,
`security.tirith_enabled`, `security.allow_private_urls: false`. Skills dir maps to
the review region per invariant 6.

## OpenClaw — confirmed

Current **2026.8.2** (2026-09-01). Gateway daemon, port 18789 confirmed — and it
serves **both** the admin Control UI and channel webhook ingress. Memory is plaintext
Markdown under `~/.openclaw/workspace` ("no hidden state"). Channel list broader than
briefed (adds Signal, iMessage, Google Chat). Rich policy surface confirmed:
`gateway.bind` loopback default, token auth, `dmPolicy: pairing` default,
`tools.deny`, `tools.fs.workspaceOnly`, `agents.defaults.sandbox.*`, `plugins.allow`,
`openclaw security audit`.

**Design impact:** tier C unchanged and validated — one exposed port is chat + config
+ exec-approval, so it stays loopback inside its microvm; its Markdown memory
inherits basket encryption at rest; Phase 8 module sets the full deny-first policy
surface explicitly.

## numtide/llm-agents.nix — confirmed

Maintained, daily-updated, ~150 packages. **Packages all four harnesses**:
`claude-code` (unfree binary), `dsh`, `hermes-agent`, `openclaw` (source, MIT).
Binary cache `https://cache.numtide.com`, public key
`niks3.numtide.com-1:DTx8wZduET09hRmMtKdQDxNNthLQETkc/yaX7M4qK0g=` (key name differs
from cache hostname — use the string exactly).

**Design impact:** single pinned source for all four harness packages.

## kissgyorgy/coding-agents — brief materially wrong; **dropped from the design**

Repo exists, but: there is no `openclaw` anywhere in it (only an `openclaude` package,
no Home Manager module); the `hermes-agent` module is install-only and sets **zero**
permission/safety options; "yolo by default" applies only to zsh *aliases* for
claude/crush/gemini (`--dangerously-skip-permissions`, `-y`, `--yolo`), with no
systemd units. Its claude settings also bake a broad allowlist and a bypassable
regex PreToolUse validator.

**Design impact:** it offers nothing llm-agents.nix doesn't do better, and its
defaults are exactly the yolo posture the brief warns about. Dropped; the brief's
"use the derivations; override every default" instruction is moot.

## microvm.nix — partially-confirmed

Repo move to `microvm-nix/microvm.nix` confirmed. Share matrix confirmed exactly:
firecracker no 9p/virtiofs; cloud-hypervisor virtiofs-yes/9p-no; qemu both. →
Baskets need virtiofs → **cloud-hypervisor or qemu**, as briefed.

**Deltas:** documented host-AF_VSOCK wiring covers only qemu/crosvm/kvmtool — *not*
cloud-hypervisor; do not assume guest vsock on cloud-hypervisor (we don't need it —
guests use virtiofs + netns routing). virtiofsd host wiring is being restructured on
unreleased main (moving from host systemd units into package `bin/`).

**Design impact:** pin a tagged release, not main; re-check virtiofsd wiring at the
pin.

## age / age-plugin-yubikey / impermanence — confirmed

Multi-recipient encryption to three YubiKeys with any-single-key decrypt: exactly how
age works (`-r` repeated). age v1.3.2 (post-quantum recipients since 1.3.0 — future
option), age-plugin-yubikey v0.5.1, both in nixpkgs. Identities live in retired PIV
slots 0x82–0x95; `--pin-policy {never,once,always}`, `--touch-policy
{never,cached,always}`. Known NixOS failure mode: the plugin must be on `age`'s PATH
for every invoker (systemd units, agenix, stage-1) — the basketStore module wires
this explicitly. Impermanence actively maintained; `environment.persistence.<path>`
interface as expected.

**Phase 1 consequences:** acceptance test extends to decrypting with *each* of the
three keys (recipient mistakes fail only at decrypt time); touch-policy is an operator
knob in the module (recommendation: `cached`; `always` if per-mount touch is wanted).

## Egress broker selection (Section 9 Q4 input) — decided: mitmproxy

Only two candidates can MITM arbitrary allowlisted hosts with a dynamically-forging
local CA: mitmproxy and Squid ssl-bump. Envoy has the perfect filter set
(credential_injector, RBAC, JSON logs) but cannot forge per-host certs on the fly —
pre-minting per allowlisted host makes it a contraption. smokescreen never terminates
TLS (fails the domain-fronting requirement by design). google/martian is archived
(2026-02-20); a bespoke goproxy binary means owning MITM crypto code forever.
mitmproxy 12.2.3 is in nixpkgs (no NixOS module — one netns-scoped systemd unit to
write); the entire policy (default-deny allowlist, JSONL audit with
agent/destination/bytes/verdict, sentinel→real credential swap per host) is one short
Nix-rendered, pinned addon. Runner-up: Squid ssl-bump (NixOS module exists, but
secrets become squid.conf literals, no sentinel match-and-replace, fail-open
peek/splice footguns).

## Model router selection (Section 9 Q5 input) — decided: Bifrost + llama-swap

- **LiteLLM** (my prior draft pick) is disqualified as primary: its virtual keys
  *require Postgres* with keys minted imperatively via `/key/generate`/admin UI —
  precisely the imperative setup invariant 4 calls a design bug; telemetry on by
  default; large Python surface. It remains the documented fallback (it is in nixpkgs
  with a `services.litellm` module) if Bifrost's declarative governance proves
  immature.
- **Bifrost** (maximhq, Apache 2.0, single Go binary): OSS virtual keys with per-key
  model allowlists, per-key rate limits and budgets, declarable in `config.json` at
  startup (documented GitOps pattern) — no database. Custom OpenAI-compatible
  providers (`base_url`) front vLLM/llama.cpp today and node3 later. Costs accepted:
  custom `buildGoModule` derivation (not in nixpkgs); young project — Phase 5 must
  verify config-file authority across restarts, disable/firewall runtime
  UI/API mutation paths, and audit/disable telemetry.
- **llama-swap** (nixpkgs + `services.llama-swap` module + upstream NixOS VM test)
  sits under Bifrost managing model hot-swap on the 5090; its `peers` federation is
  the clean node3 path. Its flat global `apiKeys` disqualify it as the enforcement
  point itself.
- **TensorZero**: auth requires Postgres + imperative key provisioning — same
  invariant 4 problem. **vLLM routers**: Kubernetes-shaped. **Helicone gateway**:
  reported maintenance mode.
- **Enforcement stance confirmed:** router = first-line fine-grained enforcement
  (client separation, model scoping, limits); the broker holds the only real frontier
  credential and a hard spend ceiling as backstop; netns topology + Phase 3 assertion
  + broker log remain the guarantees.

## Evidence

Full per-topic evidence URLs and raw agent outputs: session workflow journal
(`wf_807c000f-8e5`). Load-bearing sources: code.claude.com/docs/en/{sandboxing,
managed-settings,desktop-linux}; github repos nmcbride/claude-desktop-nix,
deepseek-ai/deepseek-harness, NousResearch/hermes-agent, openclaw/openclaw,
numtide/llm-agents.nix, kissgyorgy/coding-agents, microvm-nix/microvm.nix,
str4d/age-plugin-yubikey, nix-community/impermanence; docs.mitmproxy.org;
docs.getbifrost.ai; docs.litellm.ai; wiki.squid-cache.org.
