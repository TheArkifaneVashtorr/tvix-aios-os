# Generative-Media Flake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Executor: `tools/factory/dark-factory.js` from nixos-agent-env with `bootstrap: true`, `repo: /home/dalhaka/flakes/media`.

**Goal:** A standalone flake `~/flakes/media` exporting `nixosModules.default` (`services.comfyui`) that runs ComfyUI as a rootless, digest-pinned podman container inside the egress broker's `egress-media` network namespace with GPU access, reachable only via a loopback socket proxy, plus a hash-verified model fetch tool that downloads through the same chokepoint.

**Architecture:** One module file declares: the `comfyui` system user (subuid range), `/var/lib/comfyui`, a system service that enters `/run/netns/egress-media` via `NetworkNamespacePath` and runs `podman run --network host` as that user (rootless podman cannot `setns` into a root-owned namespace, so the unit enters it before dropping privileges — this amends the spec's `--network ns:` wording; `--network host` inside the unit IS the broker namespace), a socket-activated `systemd-socket-proxyd` on `127.0.0.1:8188` → `10.100.2.2:8188`, a oneshot fetch service confined the same way, and the broker `inject."huggingface.co"` default. Tests: eval checks on the generated argv, four negative assertion checks, pytest + bats for the fetch tool. VM tests that need the real broker module live in nixos-agent-env (host-wiring plan).

**Tech Stack:** Nix flakes, NixOS module system at pin `ac62194c…` (`virtualisation.podman`, `hardware.nvidia-container-toolkit`, `users.users.<n>.autoSubUidGidRange`, `systemd.sockets`, `systemd-socket-proxyd`), Python 3.12 stdlib (`tomllib`, `urllib`, `hashlib`), pytest, bats, skopeo (via `nix run github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d#skopeo`) for the digest.

**Spec:** `/home/dalhaka/nixos-agent-env/docs/superpowers/specs/2026-09-02-media-flake-design.md` (rev 2.1). Read it first. Amendment carried by this plan: unit-level `NetworkNamespacePath` + `podman --network host` replaces `--network ns:` (same isolation, feasible rootless); record it in the spec text in Task 4.

## Global Constraints

- New repo `/home/dalhaka/flakes/media`, plain git, `main`, no remote; hooks copied verbatim from nixos-agent-env.
- `inputs.nixpkgs.url = "github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d"`; the module uses the host's `pkgs` only.
- Image always `<name>@sha256:<64 hex>`; assertion rejects anything else. Never a tag at runtime.
- Loopback only: `proxy.listen` must start with `127.0.0.1:` (assertion). Nothing binds a host interface.
- Credential: `models.hfTokenFile` is `lib.types.str`, must not start with `/nix/store` (assertion); it is consumed ONLY by `services.egress-broker.instances.<i>.inject."huggingface.co".valueFile`. No `HF_TOKEN` anywhere in unit environments (eval check).
- No ComfyUI-Manager, no custom-node fetching, no option for it.
- Python: stdlib only; ruff gate on `pkgs/media-fetch tests/media-fetch`.
- Commit subjects `media: <summary> (test: …)`; docs-only `docs: …`. Nix style as in nixos-agent-env (statix `_:` headers, deadnix, nixfmt).
- Build-only. Never run podman, never pull the image, never start units.

---

### Task 1 (bootstrap): skeleton, lint gate with ruff, stub broker option, empty module, harness

**Files (new):** `flake.nix`, `.gitignore`, `treefmt.toml` (nix, shell, python/ruff formatters — copy nixos-agent-env's three blocks), `githooks/{pre-commit,pre-push,allowed-remotes.txt}`, `nixosModules/comfyui.nix` (enable option only), `checks/eval-harness.nix`, `checks/stub-broker.nix`, `README.md`, `docs/OPERATIONS.md`.

- [ ] **Step 1: `checks/stub-broker.nix`** — declares the broker option shape for eval checks only (the real module in nixos-agent-env provides it on the host). Copy the `options.services.egress-broker.instances` block from `/home/dalhaka/nixos-agent-env/nixosModules/egressBroker.nix:22-63` verbatim (hostAddress, namespaceAddress, prefixLength, listenPort, allow, inject with header/prefix/valueFile), with an empty `config = { };`.
- [ ] **Step 2: `checks/eval-harness.nix`** — like the gaming plan's harness, plus `stubBroker` in modules and:
```nix
services.egress-broker.instances.media = {
  hostAddress = "10.100.2.1";
  namespaceAddress = "10.100.2.2";
  listenPort = 3130;
  allow = [ "huggingface.co" ];
};
```
- [ ] **Step 3: `flake.nix`** — as the gaming flake's, with `lintTools` including `ruff`, `pyEnv = pkgs.python3.withPackages (ps: [ ps.pytest ])`, `checks.lint` (add `ruff check pkgs/media-fetch tests/media-fetch` and `ruff format --check …`), `checks.comfyui-eval` evaluating the harness with `services.comfyui.enable = true` (passes trivially now), devShell packages `lintTools ++ [ pyEnv pkgs.bats ]` and the hooksPath shellHook.
- [ ] **Step 4:** README (what/why, security notes from the spec verbatim), board, `.gitignore` = `result*`. `git add -A`, `nix develop -c true`, `nix flake check -L` green, commit through the devShell: `media: bootstrap — flake, lint gate with ruff, stub broker option, harness (test: lint, comfyui-eval)`.

---

### Task 2: model manifest and `media-fetch-models`

**Files:** `models/manifest.toml`, `pkgs/media-fetch/fetch.py`, `tests/media-fetch/test_fetch.py`, `tests/media-fetch/fetch.bats`, `tests/mocks/serve-dir.py` (stdlib `http.server` on 127.0.0.1, port from argv), `flake.nix` (`packages.media-fetch-models`, `checks.media-fetch-unit`, `checks.media-fetch-bats`).

**Interfaces (Produces):**
```python
# fetch.py
def load_manifest(path: pathlib.Path) -> list[dict]      # each: name,url,sha256,dest,size(int),license,gated(bool),enabled(bool)
def open_url(url: str, cafile: str | None) -> BinaryIO   # urllib with ProxyHandler from env; tests monkeypatch
def fetch_one(m: dict, dest_root: pathlib.Path, cafile: str | None, log=print) -> str   # returns "OK"|"SKIP"|"FAIL"
def main(argv) -> int   # --manifest PATH --dest DIR [--only NAME…] [--cafile PATH]; exit 1 if any FAIL
```
Log lines exactly: `media-fetch: OK <name> <sha256[:12]>`, `media-fetch: SKIP <name> present`, `media-fetch: FAIL <name> <reason>`.

- [ ] **Step 1: failing pytest** (`tests/media-fetch/test_fetch.py`, load by path like the Helm tests):
```python
def test_manifest_parses(tmp_path):
    p = tmp_path / "m.toml"
    p.write_text('[[model]]\nname="a"\nurl="https://x/a.bin"\nsha256="' + "0" * 64 + '"\ndest="ckpt/a.bin"\nsize=3\nlicense="MIT"\ngated=false\nenabled=true\n')
    assert fetch.load_manifest(p)[0]["dest"] == "ckpt/a.bin"

def test_fetch_ok_and_skip(monkeypatch, tmp_path):
    data = b"abc"
    sha = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(fetch, "open_url", lambda url, cafile: io.BytesIO(data))
    m = {"name": "a", "url": "https://x/a", "sha256": sha, "dest": "ckpt/a.bin", "size": 3, "gated": False, "enabled": True}
    assert fetch.fetch_one(m, tmp_path, None, log=lambda s: None) == "OK"
    assert (tmp_path / "ckpt/a.bin").read_bytes() == data
    assert fetch.fetch_one(m, tmp_path, None, log=lambda s: None) == "SKIP"

def test_fetch_wrong_hash_fails_and_leaves_no_file(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch, "open_url", lambda url, cafile: io.BytesIO(b"abc"))
    m = {"name": "a", "url": "u", "sha256": "f" * 64, "dest": "a.bin", "size": 3, "gated": False, "enabled": True}
    assert fetch.fetch_one(m, tmp_path, None, log=lambda s: None) == "FAIL"
    assert not (tmp_path / "a.bin").exists() and not list(tmp_path.glob("*.part"))

def test_refuses_to_overwrite_different_existing(monkeypatch, tmp_path):
    (tmp_path / "a.bin").write_bytes(b"other")
    monkeypatch.setattr(fetch, "open_url", lambda url, cafile: io.BytesIO(b"abc"))
    m = {"name": "a", "url": "u", "sha256": hashlib.sha256(b"abc").hexdigest(), "dest": "a.bin", "size": 3, "gated": False, "enabled": True}
    assert fetch.fetch_one(m, tmp_path, None, log=lambda s: None) == "FAIL"
    assert (tmp_path / "a.bin").read_bytes() == b"other"

def test_401_is_clear_fail(monkeypatch, tmp_path):
    def boom(url, cafile):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)
    monkeypatch.setattr(fetch, "open_url", boom)
    logs = []
    m = {"name": "g", "url": "u", "sha256": "0" * 64, "dest": "g.bin", "size": 1, "gated": True, "enabled": True}
    assert fetch.fetch_one(m, tmp_path, None, log=logs.append) == "FAIL"
    assert any("401" in l and "gated" in l for l in logs)

def test_proxy_env_reaches_opener(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://10.100.2.1:3130")
    seen = {}
    class FakeOpener:
        def open(self, url, timeout=None):
            seen["url"] = url
            return io.BytesIO(b"")
    monkeypatch.setattr(fetch, "build_opener", lambda cafile: (seen.__setitem__("proxy", fetch.proxy_from_env()), FakeOpener())[1])
    fetch.open_url("https://huggingface.co/x", None)
    assert seen["proxy"] == {"https": "http://10.100.2.1:3130"} and seen["url"] == "https://huggingface.co/x"
```
- [ ] **Step 2: implement** `fetch.py` (stream in 1 MiB chunks to `<dest>.part`, hash while streaming, compare, `os.replace`; `proxy_from_env()` uses `urllib.request.getproxies()`; `build_opener(cafile)` = `urllib.request.build_opener(ProxyHandler(proxies), HTTPSHandler(context=ssl.create_default_context(cafile=cafile)))`; skip `enabled=false` entries; `--only` filter). Run pytest → green.
- [ ] **Step 3: bats** (`tests/media-fetch/fetch.bats`): `setup` starts `python3 tests/mocks/serve-dir.py <port>` in the background serving a temp dir containing `a.bin`, writes a manifest with `http://127.0.0.1:<port>/a.bin` and the right hash plus a second entry with a wrong hash; tests: `run media-fetch-models --manifest m.toml --dest out` → status 1, output has `OK a` and `FAIL b`, `out/a.bin` exists, no `*.part`. `teardown` kills the server.
- [ ] **Step 4: packages + checks** — `media-fetch-models` via `pkgs.writeShellApplication { runtimeInputs = [ pkgs.python3 ]; text = ''exec python3 ${./pkgs/media-fetch/fetch.py} "$@"''; }`; `checks.media-fetch-unit` (runCommand + pytest, layout `pkgs/media-fetch` + `tests/media-fetch`), `checks.media-fetch-bats` (runCommand with bats, python3, the package; `patchShebangs tests/mocks`).
- [ ] **Step 5: starter manifest** — entries for SDXL base 1.0, Z-Image Turbo (fp8), ACE-Step v1 checkpoint (+ its text encoder/VAE if separate), Wan 2.2 TI2V-5B (fp8) + text encoder + VAE, Flux.1-dev (`gated=true`, `enabled=false`), LTX-2 (`enabled=false`). For each, fetch the model card / file page (WebFetch or `curl -sI` for size) and record the sha256 from the Hugging Face file page ("SHA256" shown for LFS files) — **never guess a hash; if a page cannot be read, set `enabled=false`, `sha256="UNVERIFIED"` and list it in deviations**. The tool must reject `UNVERIFIED` entries with a FAIL (test it).
- [ ] **Step 6:** lint gate; commit `media: manifest + media-fetch-models (stream, verify, refuse-overwrite, proxy-aware) (test: media-fetch-unit, media-fetch-bats, lint)`.

---

### Task 3: module `services.comfyui`

**Files:** `nixosModules/comfyui.nix`, `flake.nix` (checks `comfyui-eval`, `comfyui-assertion-negative-{listen,digest,broker,token}`).

**Interfaces (Produces):** options per the spec table (`enable, image.name, image.digest, user, group, dataDir, listen.address, proxy.listen, gpu.enable, brokerInstance, models.manifest, models.hfTokenFile, models.civitai.enable, extraEnv, resources.memoryMax`, plus `readOnlyRoot` default false and `wantedUid` default 0 from the UID decision). Units: `comfyui.service`, `comfyui-proxy.socket`/`.service`, `comfyui-fetch-models.service`.

- [ ] **Step 1: resolve the image digest.** `nix run github:NixOS/nixpkgs/ac62194c3917d5f474c1a844b6fd6da2db95077d#skopeo -- list-tags docker://docker.io/mmartial/comfyui-nvidia-docker` → pick the newest `ubuntu24_cuda12.8*` (or 12.9/13.x) tag; `skopeo inspect --override-os linux --override-arch amd64 docker://docker.io/mmartial/comfyui-nvidia-docker:<tag>` → `.Digest`. Record tag, digest, inspect date and the image's ComfyUI version (from its labels/README) in the module default's comment and README. Read the image README (github.com/mmartial/ComfyUI-Nvidia-Docker) for `WANTED_UID/GID`, `BASE_DIRECTORY`, `COMFY_CMDLINE_EXTRA`, `/comfy/mnt` vs `/basedir` mount names, and whether root fs must be writable — set `readOnlyRoot` default accordingly and say why.
- [ ] **Step 2: failing checks** (in `flake.nix`, harness with `services.comfyui = { enable = true; models.hfTokenFile = "/var/lib/secrets/hf"; }`):
```nix
comfyui-eval =
  let
    c = (harness { services.comfyui = { enable = true; models.hfTokenFile = "/var/lib/secrets/hf"; }; }).config;
    svc = c.systemd.services.comfyui.serviceConfig;
    start = toString svc.ExecStart;
    envs = lib.concatStringsSep " " (lib.mapAttrsToList (k: v: "${k}=${toString v}") (c.systemd.services.comfyui.environment or { }));
    has = s: lib.hasInfix s start;
  in
  assert lib.assertMsg (has "@sha256:") "eval: image not digest-pinned";
  assert lib.assertMsg (has "--device nvidia.com/gpu=all") "eval: no CDI device";
  assert lib.assertMsg (has "--network host") "eval: container must share the unit's (broker) netns";
  assert lib.assertMsg (svc.NetworkNamespacePath == "/run/netns/egress-media") "eval: unit not in the broker netns";
  assert lib.assertMsg (svc.User == "comfyui") "eval: not the comfyui user";
  assert lib.assertMsg (has "--cap-drop=ALL" && has "no-new-privileges") "eval: caps";
  assert lib.assertMsg (!(has "-p ") && !(has "--publish")) "eval: no port publishing";
  assert lib.assertMsg (!(lib.hasInfix "HF_TOKEN" (start + envs))) "eval: token leaked into the container unit";
  assert lib.assertMsg (lib.elem "127.0.0.1:8188" c.systemd.sockets.comfyui-proxy.listenStreams) "eval: proxy socket";
  assert lib.assertMsg (c.services.egress-broker.instances.media.inject ? "huggingface.co") "eval: inject key must be the host";
  assert lib.assertMsg (c.services.egress-broker.instances.media.inject."huggingface.co".valueFile == "/var/lib/secrets/hf") "eval: inject valueFile";
  assert lib.assertMsg (c.systemd.services.comfyui-fetch-models.serviceConfig.NetworkNamespacePath == "/run/netns/egress-media") "eval: fetch not confined";
  assert lib.assertMsg (c.users.users.comfyui.autoSubUidGidRange) "eval: subuid range";
  builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "comfyui-eval-ok" { } "touch $out");
```
and four negatives with the gaming plan's `mkNegative`: `listen` (`proxy.listen = "0.0.0.0:8188"`), `digest` (`image.digest = "latest"`), `broker` (`brokerInstance = "nope"`), `token` (`models.hfTokenFile = "/nix/store/abc-hf"`).
- [ ] **Step 3: implement the module.** Skeleton:
```nix
{ config, lib, pkgs, ... }:
let
  cfg = config.services.comfyui;
  broker = config.services.egress-broker.instances.${cfg.brokerInstance};
  netns = "/run/netns/egress-${cfg.brokerInstance}";
  proxyUrl = "http://${broker.hostAddress}:${toString broker.listenPort}";
  caBundle = "/var/lib/egress-broker/${cfg.brokerInstance}/ca/ca-bundle.crt";
  image = "${cfg.image.name}@${cfg.image.digest}";
  podman = "${pkgs.podman}/bin/podman";
  runArgs = [
    "run" "--rm" "--replace" "--name" "comfyui" "--network" "host"
    "--cap-drop=ALL" "--security-opt=no-new-privileges"
  ]
  ++ lib.optionals cfg.gpu.enable [ "--device" "nvidia.com/gpu=all" ]
  ++ lib.optionals cfg.readOnlyRoot [ "--read-only" "--tmpfs" "/tmp" ]
  ++ [ "-v" "${cfg.dataDir}:/basedir" "-v" "${caBundle}:/etc/ssl/certs/ca-bundle.crt:ro" ]
  ++ lib.concatLists (lib.mapAttrsToList (k: v: [ "-e" "${k}=${v}" ]) containerEnv)
  ++ [ image ];
  containerEnv = {
    WANTED_UID = toString cfg.wantedUid; WANTED_GID = toString cfg.wantedUid;
    BASE_DIRECTORY = "/basedir";
    COMFY_CMDLINE_EXTRA = "--listen ${cfg.listen.address} --port 8188";
    HTTP_PROXY = proxyUrl; HTTPS_PROXY = proxyUrl; NO_PROXY = "${broker.namespaceAddress},127.0.0.1,localhost";
    SSL_CERT_FILE = "/etc/ssl/certs/ca-bundle.crt"; REQUESTS_CA_BUNDLE = "/etc/ssl/certs/ca-bundle.crt"; CURL_CA_BUNDLE = "/etc/ssl/certs/ca-bundle.crt";
  } // cfg.extraEnv;
in
{
  options.services.comfyui = { /* per spec; image.digest default = the resolved digest with a dated comment; listen.address default = broker.namespaceAddress (use lib.mkDefault via config, not in the option default, because broker may not exist at option-eval time — default the option to null and resolve `cfg.listen.address or broker.namespaceAddress` in `let`) */ };
  config = lib.mkIf cfg.enable {
    assertions = [
      { assertion = config.services.egress-broker.instances ? ${cfg.brokerInstance}; message = "services.comfyui.brokerInstance '${cfg.brokerInstance}' has no services.egress-broker.instances entry"; }
      { assertion = builtins.match "sha256:[0-9a-f]{64}" cfg.image.digest != null; message = "services.comfyui.image.digest must be sha256:<64 hex>, got '${cfg.image.digest}'"; }
      { assertion = lib.hasPrefix "127.0.0.1:" cfg.proxy.listen; message = "services.comfyui.proxy.listen must be loopback"; }
      { assertion = cfg.models.hfTokenFile == null || !(lib.hasPrefix "/nix/store" cfg.models.hfTokenFile); message = "services.comfyui.models.hfTokenFile must be a path outside the Nix store (a path literal would copy the secret into the store)"; }
    ];
    virtualisation.podman.enable = true;
    hardware.nvidia-container-toolkit.enable = lib.mkIf cfg.gpu.enable true;
    users.groups.${cfg.group} = { };
    users.users.${cfg.user} = { isSystemUser = true; group = cfg.group; home = cfg.dataDir; autoSubUidGidRange = true; };
    systemd.tmpfiles.rules = [
      "d ${cfg.dataDir} 0750 ${cfg.user} ${cfg.group} -"
    ] ++ map (d: "d ${cfg.dataDir}/${d} 0750 ${cfg.user} ${cfg.group} -") [ "models" "input" "output" "user" ];
    services.egress-broker.instances.${cfg.brokerInstance}.inject = lib.mkIf (cfg.models.hfTokenFile != null) (lib.mkDefault {
      "huggingface.co" = { header = "Authorization"; prefix = "Bearer "; valueFile = cfg.models.hfTokenFile; };
    });
    systemd.services.comfyui = {
      description = "ComfyUI (rootless podman, broker netns, digest-pinned)";
      wantedBy = [ "multi-user.target" ];
      requires = [ "egress-netns-${cfg.brokerInstance}.service" "egress-broker-${cfg.brokerInstance}.service" ];
      after = [ "egress-netns-${cfg.brokerInstance}.service" "egress-broker-${cfg.brokerInstance}.service" "systemd-tmpfiles-setup.service" ];
      environment = { HOME = cfg.dataDir; XDG_RUNTIME_DIR = "/run/comfyui"; };
      serviceConfig = {
        User = cfg.user; Group = cfg.group;
        NetworkNamespacePath = netns;
        RuntimeDirectory = "comfyui";
        ExecStart = lib.escapeShellArgs ([ podman ] ++ runArgs);
        ExecStop = "${podman} stop -t 30 comfyui";
        Restart = "on-failure"; RestartSec = 10;
        MemoryMax = cfg.resources.memoryMax; Nice = 5;
        NoNewPrivileges = true; PrivateTmp = true;
        Delegate = true; # rootless podman needs its cgroup
      };
    };
    systemd.sockets.comfyui-proxy = { wantedBy = [ "sockets.target" ]; listenStreams = [ cfg.proxy.listen ]; };
    systemd.services.comfyui-proxy = {
      description = "Loopback proxy to ComfyUI inside the broker namespace";
      requires = [ "comfyui-proxy.socket" ]; after = [ "comfyui-proxy.socket" ];
      serviceConfig = { ExecStart = "${pkgs.systemd}/lib/systemd/systemd-socket-proxyd ${cfg.listen.address}:8188"; DynamicUser = true; PrivateTmp = true; NoNewPrivileges = true; };
    };
    systemd.services.comfyui-fetch-models = {
      description = "Fetch models from the manifest through the egress broker (run by hand)";
      requires = [ "egress-netns-${cfg.brokerInstance}.service" "egress-broker-${cfg.brokerInstance}.service" ];
      after = [ "egress-broker-${cfg.brokerInstance}.service" ];
      environment = { HTTPS_PROXY = proxyUrl; HTTP_PROXY = proxyUrl; };
      serviceConfig = {
        Type = "oneshot"; User = cfg.user; Group = cfg.group;
        NetworkNamespacePath = netns;
        ExecStart = "${mediaFetch}/bin/media-fetch-models --manifest ${cfg.models.manifest} --dest ${cfg.dataDir}/models --cafile ${caBundle}";
        NoNewPrivileges = true; ProtectSystem = "strict"; ReadWritePaths = [ "${cfg.dataDir}/models" ]; PrivateTmp = true;
      };
    };
    environment.systemPackages = [ mediaFetch ];
  };
}
```
**Also required (found by the wiring plan's self-review):** the `podman` process itself pulls the image from Docker Hub and must do so through the broker: set `environment = { HOME = …; XDG_RUNTIME_DIR = …; HTTPS_PROXY = proxyUrl; HTTP_PROXY = proxyUrl; SSL_CERT_FILE = caBundle; }` on `comfyui.service` (podman/containers-image honour `HTTPS_PROXY` and `SSL_CERT_FILE`), and add to the eval check: `assert (c.systemd.services.comfyui.environment.HTTPS_PROXY == "http://10.100.2.1:3130")`. The registry hosts (`registry-1.docker.io`, `auth.docker.io`, `production.cloudflare.docker.com`, `docker.io`) go into the instance allow list in nixos-agent-env's `hosts/core/media.nix` (wiring plan), and the harness's stub instance here gets them too so the intent is visible.

Verify at the pin before committing: `users.users.<n>.autoSubUidGidRange` (exists in NixOS 25.05 — confirm), `virtualisation.podman` options, that `hardware.nvidia-container-toolkit.enable` is the canonical name (alias confirmed by research), the `Delegate=` requirement for rootless podman under a system unit, and that `RuntimeDirectory` gives the user a writable `XDG_RUNTIME_DIR` (rootless podman needs it). Record any deviation.
- [ ] **Step 4:** run `comfyui-eval` + the four negatives + lint → green. Commit `media: services.comfyui — rootless podman in the broker netns, loopback socket proxy, confined fetch, broker-injected credential (test: comfyui-eval, comfyui-assertion-negative-listen/digest/broker/token, lint)`.

---

### Task 4 (docs): acceptance drill, runbook, README, spec amendment note, board

**Files:** `tests/acceptance/media.sh` (runs on core after the wiring switch; the checks listed in the spec's acceptance section, incl. the fail-closed proof `podman exec comfyui curl -m 5 https://example.com` run via `sudo -u comfyui` inside the unit's namespace with `nsenter --net=/run/netns/egress-media`, the ownership stat, the audit `allow` lines, the three generation proofs using bundled minimal workflows `tests/acceptance/workflows/{sdxl,ace-step,video}.json` posted to `http://localhost:8188/prompt`), `docs/runbooks/media.md` (plain language: first start pulls ~10 GB through the broker — watch `/var/lib/egress-broker/media/audit.jsonl`; how to add a model to the manifest; how to give the broker a Hugging Face token file (`chmod 0400`, outside any repo) for gated models; what the digest is and how to bump it), `README.md`, `docs/OPERATIONS.md`, and a one-paragraph note appended to the nixos-agent-env spec? — NO: do not write outside this repo; instead put the amendment text in `docs/decisions/2026-09-02-netns-entry-amendment.md` here; the wiring plan copies it into nixos-agent-env.

- [ ] `nix develop -c bash -n tests/acceptance/media.sh`; lint; commit `docs: media — acceptance drill with generation proofs, runbook, netns amendment (test: lint)`.

---

## Self-review (orchestrator)

Spec coverage: repo + stub broker (T1), manifest/fetch/tests (T2), module + assertions + inject + proxy + fetch confinement + eval/negatives (T3), acceptance/runbook (T4). VM tests, host wiring, backup paths → `2026-09-02-host-wiring.md`. Amendment (unit-level netns entry) recorded in T4 and carried to the spec by the wiring plan. Type consistency: option names in T3 module = T3 checks; log lines in T2 tests = T2 tool = T4 acceptance greps.
