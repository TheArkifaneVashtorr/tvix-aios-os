# Section 9 answers — for operator confirmation before Phase 1

Date: 2026-09-02. Each answer is a recommendation with the reasoning the brief asked
for. Confirm, amend, or reject per item; Phase 1 starts only after confirmation.

## Q1 — Basket granularity

**Recommendation: basket = one classification's worth of data within one project.
Project = the environment unit.**

Concrete definitions:

- A **project** is one directory under `projects/<name>/`: one `agents.nix`, one
  `baskets.lock`, one injected-context set. It is the unit of reproducibility ("this
  environment on any node") and the unit of agent membership.
- A **basket** is the unit of classification, encryption, and mounting. One
  classification per basket — never mixed. A project typically declares:
  `workspace` (rw, `permitted` or `redacted`), `notes-local` (ro/rw, `local-only`),
  `reference` (ro, `permitted`), etc.
- An **agent** mounts an explicit subset of its project's baskets via `mkAgent`.

Why not the alternatives:

- *Per project only* (one basket per project) forces one classification per project,
  which either flattens everything to the most permissive class or makes `local-only`
  data unusable alongside frontier-capable agents. It also guts the Phase 3 assertion
  — there would be nothing fine-grained to assert over.
- *Per agent* duplicates shared data per agent and creates state drift between copies;
  two agents in one project could no longer collaborate through the filesystem.

The Cowork tension resolves cleanly: Cowork gets the project's single broad
`workspace` basket — wide filesystem scope, one classification. `local-only` material
lives in sibling baskets Cowork simply never mounts. Breadth and fine-grained
classification stop fighting because breadth is *within* a class, not across classes.

## Q2 — Scrub pass

**Recommendation: do not build one now. Keep the `redacted` class in the schema and
router table from day 1; route it like `permitted` but tagged in the broker audit log.
Revisit after Phase 5's log review.**

For building it: defense in depth; catches honest misclassification (a stray SSN in a
`permitted` basket); the audit tag alone doesn't stop a leak, only records it.

Against building it (and why this side wins):

- Classification-based routing is the actual control; the brief already says the scrub
  is defense in depth only. A control that is known-porous invites relying on it
  anyway — "it's fine, the scrubber will catch it" is exactly how `local-only` data
  ends up in a `redacted` basket.
- A scrubber is heuristic runtime code making policy decisions. Invariant 5 says
  policy is Nix configuration reviewable in a diff; a regex/NER pipeline is neither
  reviewable in that sense nor sound against adversarial content (prompt-injected
  exfiltration trivially encodes around scrubbing).
- It adds a TLS-visible middlebox that must parse every provider payload format,
  a maintenance tax paid forever for false confidence.

Middle path adopted: the `redacted` class exists and is enforceable end-to-end
(router table + broker tag), so adding a real scrub stage later is a drop-in broker
plugin, not a schema change. Decision trigger: if Phase 5+ audit review shows actual
misclassification incidents, build the stage then, as containment — not as permission
to classify sloppily.

## Q3 — Hermes vs OpenClaw overlap

**Recommendation: both stay in the design because they occupy different trust tiers,
but only Hermes deploys on the roadmap (Phase 7). OpenClaw activates in Phase 8 only
if a messaging channel is concretely wanted then.**

They look near-identical (persistent gateway, adapters, local memory, self-written
skills) but their *input provenance* differs categorically: Hermes works operator-
initiated tasks inside a workspace basket; OpenClaw exists to ingest attacker-
reachable text from messaging platforms. That difference is why the brief already
places them in different tiers (B vs C). Collapsing them — one harness doing both —
would put untrusted ingress in the same process as workspace access, which invariant-
level design forbids. So: not redundant, and not a fallback pair; one is the trusted
hands, the other the untrusted mailbox.

Memory drift prevention if both run: **no shared memory, full stop.** Each has its own
basket; nothing syncs. The only cross-pollination channel anywhere in the system is
the reviewed, one-way skill-promotion gate (invariant 6). OpenClaw's memory is treated
as tainted-by-design and is never promotion-eligible into any other basket; promotion
review applies to Hermes skills only. If the same fact must exist in both, the
operator writes it into each basket deliberately.

Attack-surface note: every persistent gateway is standing surface. Until a messaging
channel is genuinely needed, OpenClaw simply doesn't run — the cheapest hardening
available.

## Q4 — Broker implementation

**Recommendation: mitmproxy, pinned, run as one hardened systemd service per netns,
with a single short Nix-generated addon (allowlist + JSON audit log + sentinel→real
credential injection). Runner-up: Envoy.**

Verified against live docs 2026-09-02 (see `docs/upstream-verification-2026-09-02.md`).
Only two candidates can MITM arbitrary allowlisted hosts with a dynamically-forging
local CA — the non-negotiable capability that defeats domain fronting:

- **mitmproxy** (chosen) — TLS-terminating MITM with auto-generated local CA is its
  core competency; v12.2.3 in nixpkgs. The three custom behaviors we need
  (default-deny allowlist, JSONL per-request audit with agent/destination/bytes/
  verdict, sentinel→real credential swap scoped to specific hosts) are one short
  Python addon — pinned in git, readable in one screen. Cons accepted: no NixOS
  module (one netns-scoped systemd unit to write); Python in the trust path;
  modest throughput — irrelevant at single-user LAN scale.
- **Squid ssl-bump** (runner-up) — the only other native dynamic-cert MITM, and it
  has a NixOS module; but no sentinel match-and-replace (secrets would sit as
  literals in squid.conf), JSON audit must be hand-rolled logformat, and peek/bump
  staging is a known fail-open footgun. Acceptable fallback only.
- **Envoy** — credential_injector + RBAC + JSON logs are perfect on paper, but Envoy
  cannot forge per-host certificates on the fly; MITM-ing an allowlist means
  pre-minting certs per host at build time plus CONNECT re-dispatch machinery.
  Rejected as a contraption whose security diff nobody can review.
- **smokescreen** — never terminates TLS; blind to the inner request; fails the
  domain-fronting requirement by design. Also not in nixpkgs. Rejected.
- **Purpose-built Go proxy** — google/martian archived 2026-02-20; goproxy would mean
  owning a homegrown MITM proxy's security lifecycle forever. Rejected.

The addon script is code, but it is *pinned, reviewed policy-adjacent code* — the
actual policy (allowlists, inject hosts, key material references) is generated from
Nix and fed to the addon as data, preserving invariant 5.

## Q5 — Model router

**Recommendation: Bifrost (maximhq) as the gateway/enforcement layer, with llama-swap
underneath it managing model hot-swap on the 5090. Runner-up: LiteLLM proxy.
Enforcement stance: the router applies classification routing; the broker + netns
topology enforce and verify it.**

Verified against live docs 2026-09-02 (see the verification report). The deciding
test was invariant 4: "if a step requires imperative setup, it is a bug."

- **Bifrost** (chosen) — Apache 2.0 single Go binary. OSS virtual keys carry per-key
  model allowlists (403 outside the list), per-key rate limits, and budgets — all
  declarable in `config.json` at startup (documented GitOps pattern), no database.
  Custom OpenAI-compatible providers via `base_url` front vLLM/llama.cpp today and a
  node3 backend later; routing by model/provider name; Prometheus/OTel + request
  logging. Costs accepted: not in nixpkgs (one custom `buildGoModule` derivation);
  young project (2025), so Phase 5 must (a) verify `config.json` stays authoritative
  over the runtime config store across restarts, (b) disable/firewall the runtime
  UI/API mutation paths, (c) audit and disable telemetry. If (a) fails, fall back.
- **LiteLLM** (runner-up, and my pre-verification draft pick — overturned) —
  functionally complete and nixpkgs-packaged with a `services.litellm` module, but
  its virtual keys *require Postgres* and are minted imperatively via
  `/key/generate`/admin UI. That is imperative state a rebuild cannot reproduce from
  the flake — an invariant 4 violation as primary. Telemetry on by default; large
  Python surface. Documented fallback if Bifrost disqualifies itself.
- **TensorZero** — auth requires Postgres with imperatively provisioned keys; same
  invariant 4 problem; observability stack (ClickHouse) is overkill here. Rejected.
- **llama-swap** — stays in the stack *under* Bifrost: nixpkgs-packaged with a
  `services.llama-swap` NixOS module and upstream VM test; hot-swaps 5090 models by
  requested name; its `peers` federation is the cleanest node3 growth path. Its flat
  global `apiKeys` (no per-key scoping/limits — confirmed in config schema)
  disqualify it as the enforcement point itself.
- **vLLM ecosystem routers** — Kubernetes/Envoy-shaped; non-fits. **Helicone
  gateway** — reported maintenance mode. Rejected.

Where enforcement lives (the brief's real question): per-key scoping in the router is
first-line policy *application* and blast-radius limiting — necessary, not
sufficient, especially in a young codebase with runtime-mutable config. The
guarantees come from topology: `local-only` agents sit in netns with no off-box route
(build-time assertion, Phase 3); every frontier-bound byte crosses the broker, which
holds the only real provider credential and a hard spend ceiling, and whose log is
the verification record (Phase 5's test). The router is therefore allowed to be
imperfect; the system does not trust it.

## Q6 — node3 rejoin

**Recommendation: fix two things now; defer everything else with no rework risk.**

Now (cheap, foreclosure-avoiding):

1. **Define `local-only` as "plaintext never leaves operator-controlled hosts, and any
   inter-host leg rides the node WireGuard mesh."** The router→backend link is
   loopback today; when node3's 4080S joins as a second inference backend, that link
   becomes WireGuard without changing the classification's meaning or any assertion.
2. **Router must support multiple named local backends** (LiteLLM does) so adding
   `node3-vllm` is a config diff, not a migration.

Defers cleanly: `hosts/node3/` stub exists in the flake from Phase 1 (brief already
requires designing for its later arrival); baskets are content-addressed ciphertext —
syncing them to node3 is file copy, and all three YubiKeys already decrypt; microvm
definitions are host-agnostic modules; the broker is per-netns and stamps out
per-host identically. Nothing in Phases 1–9 assumes single-node topology except
loopback router→backend, covered by item 1.

16GB-card caveat recorded: models servable on the 5090 (32GB) may not fit node3;
the router's model list is per-backend, so `local-only` routing must map to
*models available on some local backend*, never silently to a frontier fallback —
that non-fallback rule goes into the router config as a hard requirement in Phase 5.
