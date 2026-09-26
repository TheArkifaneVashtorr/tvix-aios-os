# Host Wiring Round 2 — the media profile

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Executor: `tools/factory/dark-factory.js` in nixos-agent-env (host `core`), launched only AFTER the operator has passed the round-1 gate (docs/runbooks/switch-helm-gaming.md).

**Goal:** `core` gains the `media` profile as a NixOS specialisation running the nix-native ComfyUI service from `~/flakes/media` inside a new egress-broker instance `media`, proven in a NixOS VM with the real broker module; backups cover ComfyUI's outputs and workflows.

**Architecture:** one `git+file://` input (`media`), `hosts/core/media.nix` imported only by `specialisation.media.configuration` with the marker `lib.mkForce "media"`, the broker instance declared there with Hugging Face hosts only, restic paths extended; a VM test in this repo composes `self.nixosModules.egressBroker` + `media.nixosModules.default`.

**Specs:** docs/superpowers/specs/2026-09-02-media-flake-design-rev3.md (rev 3.1), 2026-09-02-helm-v1-switch-design.md (Profiles), docs/decisions/2026-09-02-media-nix-native-no-container.md.

## Global Constraints

- Build-only; the operator switches once after this round (a second switch, after round 1's).
- `inputs.media.url = "git+file:///home/dalhaka/flakes/media?ref=main"`, locked rev; the media flake's nixpkgs is the host pin rev (lock guard as in round 1, extended to the `media` node).
- Base profile keeps `services.comfyui.enable = false` and no `media` broker instance (asserted). The broker instance's `allow` list is the Hugging Face host set only — no Docker registry, no GitHub, no PyPI (nothing is fetched at runtime).
- AMENDMENT 2026-09-03 evening (operator placed /var/lib/secrets/civitai-key, 32 bytes root 0400; Proton Pass = vault): when this round lands, the `media` instance ALSO gets Civitai — add `civitai.com` to `allow` plus the CDN host(s) its download redirects actually land on (capture them at wiring time from the broker's own deny lines during a test fetch — do not guess; they are believed to be Cloudflare-fronted), and inject `Authorization: Bearer` from that key file for `civitai.com` ONLY (never for the CDN hosts — the redirect target is a signed URL). The fetch tool's `--token-file civitai=...` path (media repo, landed 2026-09-03) is for MANUAL runs as the operator; under the broker the injection replaces it, same as the HF token.
- The profile marker in the specialisation uses `lib.mkForce` (round-1 lesson: `environment.etc` text merges).
- Commit subjects `wiring: … (test: …)` / `docs: …`.

---

### Task 1: input, media profile, broker instance, backups

**Files:** `flake.nix` (input `media`; `nixosConfigurations.core.modules` += `media.nixosModules.default`; check `core-media-wiring`), `hosts/core/media.nix`, `hosts/core/default.nix` (specialisation block), `hosts/core/proton-backup.nix` (paths).

- [ ] `hosts/core/media.nix`:
```nix
_: {
  # Media profile (~/flakes/media): ComfyUI v0.22.3 nix-native, as user comfyui inside the
  # broker namespace "media"; loopback http://localhost:8188 via the socket proxy. Active only
  # in the `media` specialisation — Helm switches profiles.
  services.egress-broker.instances.media = {
    hostAddress = "10.100.2.1";
    namespaceAddress = "10.100.2.2";
    listenPort = 3130;
    # Hugging Face host set from https://huggingface.co/.well-known/meta.json, fetched <DATE>
    # by the wiring factory (re-fetch and date it). Weights only: nothing else is ever fetched.
    allow = [
      "huggingface.co"
      "cas-server.xethub.hf.co"
      "transfer.xethub.hf.co"
      "cdn-lfs-us-1.hf.co"
      "us.aws.cdn.hf.co"
      "us.gcp.cdn.hf.co"
    ];
  };
  services.comfyui = {
    enable = true;
    # models.hfTokenFile = "/var/lib/secrets/hf-token";  # operator: 0440 root:egress-broker, outside every repo; uncomment for gated models
  };
}
```
- [ ] `hosts/core/default.nix`: add `specialisation.media.configuration = { imports = [ ./media.nix ]; environment.etc."helm/profile".text = lib.mkForce "media"; };` next to the gaming one (the file takes `lib` — adjust the header if it is `_:`).
- [ ] `hosts/core/proton-backup.nix` paths += `"/var/lib/comfyui/output"`, `"/var/lib/comfyui/user"` (the models directory is NOT backed up: re-fetchable by manifest; say so in a comment) and tmpfiles are NOT needed (the media module creates the directories).
- [ ] `checks.core-media-wiring` (eval on `nixosConfigurations.core`): base `services.comfyui.enable == false`, base has no `services.egress-broker.instances.media`; `config.specialisation.media.configuration.services.comfyui.enable == true`, its `environment.etc."helm/profile".text == "media"`, its broker instance exists with exactly the six hosts above and `inject == {}` (no token by default), its `systemd.services.comfyui.serviceConfig.NetworkNamespacePath == "/run/netns/egress-media"`; backup paths contain the two comfyui dirs; the lock guard from round 1 also covers the `media` input's nixpkgs.
- [ ] `nix flake lock`, `host-core`, `core-media-wiring`, toplevel build; report `nix store diff-closures <result> <result>/specialisation/media` (torch, CUDA libs, ComfyUI, av; no podman) in the summary. Commit `wiring: media profile as a specialisation, ~/flakes/media pinned, broker instance media, backups (test: host-core, core-media-wiring)`.

---

### Task 2: VM test with the real broker and the real service

**Files:** `tests/integration/media-vm.nix`, `flake.nix` (`checks.media-vm`).

- [ ] Two nodes. `machine`: imports `self.nixosModules.egressBroker`, `media.nixosModules.default`, `./hosts/core/media.nix`-equivalent inline config (instance + `services.comfyui = { enable = true; gpu.enable = false; }`), `virtualisation.diskSize = 20480`, `memorySize = 6144`, `environment.systemPackages = [ curl jq ]`. `other`: plain node on the same virtual LAN. testScript: `machine.wait_for_unit("egress-broker-media.service")`; `machine.wait_for_unit("comfyui.service")`; `machine.wait_until_succeeds("curl -fsS http://127.0.0.1:8188/system_stats | jq -e '.system.comfyui_version==\"0.22.3\"'", timeout=900)`; `ss -ltn` on machine shows 8188 on 127.0.0.1 only; `other.fail("curl -m 3 http://machine:8188/")` and `other.fail("curl -m 3 http://10.100.2.2:8188/")`; **the real broker's verdicts**: `machine.fail("ip netns exec egress-media curl -m 8 -x http://10.100.2.1:3130 https://example.com")` and then the audit log has a `deny` line for `example.com` (`grep -q '"host": *"example.com".*"verdict": *"deny"' /var/lib/egress-broker/media/audit.jsonl` — match the actual JSON shape); `machine.fail("ip netns exec egress-media curl -m 5 https://example.com")` (no proxy → no route); the fetch unit's `ExecStart` contains `--cafile /var/lib/egress-broker/media/ca/ca-bundle.crt`; the unit environment has no `TOKEN`.
- [ ] Run to green (long); commit `wiring: media VM test — real broker namespace, loopback only, deny audited, fail-closed (test: media-vm)`.

---

### Task 3 (docs): runbook, board, README, concept

**Files:** `docs/runbooks/switch-media.md` (second switch; `sudo /run/current-system/specialisation/media/bin/switch-to-configuration test`; first start compiles CUDA kernels — minutes — watch `journalctl -fu comfyui`; `sudo systemctl start comfyui-fetch-models` and watch `/var/lib/egress-broker/media/audit.jsonl` for `allow` lines on Hugging Face hosts; `~/flakes/media/tests/acceptance/media.sh`; the comfy-kitchen note: optimized kernels off with CUDA 12.8 torch until a driver-580 bump; leaving the profile), `README.md`, `docs/OPERATIONS.md` Lane I → OPERATOR GATE, one concept file.

- [ ] Lint; commit `docs: the media switch — runbook, board (test: lint)`.

## Self-review (orchestrator)

Coverage: input + profile + instance + backups (T1), the spec's VM proofs with the real broker (T2), runbook (T3). Helm's profile list auto-derives from declared specialisations (v1 spec), so no Helm change is needed here. Type consistency: addresses 10.100.2.1/2, port 3130, unit names, marker `media`, paths match the media spec and the v1 spec.
