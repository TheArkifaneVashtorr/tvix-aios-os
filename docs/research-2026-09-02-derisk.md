# De-risk research digest — 2026-09-02 (Phases 3-5, 7)

Four research agents, live-web verified. Full raw output in session workflow
wf_b37dae73-a80. Decisions distilled:

## Phase 4 — Claude managed settings (schema acquired)

Complete field-verified schema + locked-down example JSON captured for
`claudeManagedSettings.nix`. Load-bearing details: `tlsTerminate` is an
**object**, `{}` for ephemeral CA or `{caCertPath, caKeyPath}` — meaning the
inner sandbox can be handed the **broker's own CA**, unifying the two TLS layers'
trust. Array-type settings merge across scopes, so the three lock keys are
mandatory: `allowManagedDomainsOnly`, `sandbox.filesystem.allowManagedReadPathsOnly`,
`allowManagedPermissionRulesOnly`. `disableBypassPermissionsMode: "disable"`
(string enum, not bool). Version floor rises: **pin Claude Code ≥ 2.1.246**
(managed-only credentials enforcement; was 2.1.224). managed-settings.d/*.json
fragments merge alphabetically (lists union, nested deep-merge). Fail-closed
behaviors verified for invalid managed entries.

## Phase 5 — Bifrost: declarative governance VERIFIED, fallback not needed

`config_store: {enabled: false}` gives pure file-into-memory mode — config.json
fully authoritative, no DB, no UI/API mutation path, restart to change. Combined
with `client.enforce_auth_on_inference: true` and `governance.virtual_keys/
budgets/rate_limits` declared in the file, invariant 4 is satisfied. **LiteLLM
fallback stays dormant.** Caveats accepted: embedded admin UI is always served
(no off switch — mitigate: bind localhost + nftables/reverse-proxy exposing only
/v1 to agents); budget usage is in-memory in file mode (fine — the broker holds
the real spend ceiling per decision Q5); Nix build is two-stage (buildNpmPackage
UI → buildGoModule CGO+sqlite_static, GOWORK=off, sourceRoot transports/, Go
1.27). **Pin: tag `transports/v2.0.0`** (2026-08-26). Secrets via `env.` prefix.

## Phase 5 — local inference on the 5090: llama.cpp, not vLLM

nixpkgs python vLLM is v0.24.0 with **`broken = cudaSupport`** — a Nix-native
CUDA vLLM does not exist today. Primary engine: **llama.cpp**
(`pkgs.llama-cpp.override { cudaSupport = true; }`) with **cudaPackages_12_8+**
and `cudaCapabilities = ["12.0"]` (sm_120/Blackwell), NVIDIA driver 570+, behind
**llama-swap v252** (`services.llama-swap`, DynamicUser-hardened, localhost
default, free-form YAML settings, `peers.<node>` federation ready for node3).
Model reality on 32GB: 70B Q4 does NOT fit; sweet spot is 32B-class —
DeepSeek-R1-Distill-Qwen-32B Q4_K_M (~20GB, 32k ctx) + Hermes-4-14B Q6. Avoid
MXFP4 quants on Blackwell (ggml #19662). This amends brief §5.4's "vLLM or
llama.cpp" to llama.cpp-first; revisit vLLM if nixpkgs unbreaks it.

## Phase 7 — microvm.nix: pin main, and a spec delta on netns

Tags are stale (v0.5.0 is 455 commits behind). **Pin main rev
`974d315e504e666eac4920d712e3ff6804dc1502`** (2026-09-01). cloud-hypervisor:
virtiofs shares confirmed (`--memory shared=on` forced), vsock cid enables
Type=notify readiness, but interfaces are **tap/macvtap only** and there is **no
netns support** in the module — tap devices are created in the root namespace.

**Spec delta to decide (flagged, not applied):** design §2.1 says tier B/C
guests get "own netns". Upstream-supported equivalent: the documented
routed-network pattern — per-VM tap, /32 host route, no shared L2, host nftables
allowing that VM's IP to reach ONLY its broker port. Same chokepoint property
("no route off-box except the broker"), no bespoke unit surgery that upstream
bumps would break. Recommendation: adopt routed-tap for microvm tiers; keep
netns for tier D (bubblewrap/ad-hoc) and Cowork (tier A) where we control the
processes directly. Phase 3's local-only assertion keys off the declared egress
policy of the agent, whichever attachment style it uses. Costs if we insisted on
netns instead: NetworkNamespacePath= overrides on microvm@ templated units —
fragile against upstream changes. Decide at Phase 7 planning; egressBroker
module grows an `attach` mode (veth-netns | tap-routed) then.
