# Generative-media flake — design (2026-09-02, rev 2)

**Decision basis (operator, 2026-09-02 evening):** separate repo
`~/flakes/media`; isolated container runtime. Research:
docs/research-2026-09-02-genai-media-stack.md. Rev 2 folds in the
adversarial review: broker-injected Hugging Face credential (brief
invariant 2), the real netns name, no podman port publishing across a
foreign namespace (loopback via a socket proxy), the fetch step confined
like the container, honest VM tests, UID mapping decided.

## Goal

Local image, video and music generation on the RTX 5090 through ComfyUI
(the node-based generation app), reachable only on loopback, running as a
dedicated unprivileged user inside a rootless, digest-pinned container,
with all outbound traffic forced through an egress-broker instance whose
allowlist is the model hosts and which injects the Hugging Face
credential itself. Models are declared in a manifest with hashes and
fetched through that same chokepoint.

## Non-goals (v0)

ComfyUI-Manager / custom nodes from the internet (off, no option);
nix-native packaging of ComfyUI (revisit later); LAN access; multi-GPU;
training.

## Architecture

```
operator browser ── http://localhost:8188 ──▶ systemd socket proxy (127.0.0.1:8188 → 10.100.2.2:8188)
                                                │  (systemd-socket-proxyd, socket-activated, host side of the veth)
                                                ▼
   netns egress-media (created by egress-netns-media.service, persistent, /run/netns/egress-media)
     ├─ ComfyUI container: podman rootless as user `comfyui`, --network ns:/run/netns/egress-media
     │    image mmartial/comfyui-nvidia-docker@sha256:… (pinned digest), GPU via CDI nvidia.com/gpu=all
     │    listens on 10.100.2.2:8188 (the namespace address) — never on a host interface
     │    /data ← /var/lib/comfyui (models, input, output, user)
     │    HTTPS_PROXY → 10.100.2.1:3130 (broker), CA bundle mounted; no other route exists
     └─ comfyui-fetch-models.service (oneshot, User=comfyui, NetworkNamespacePath=/run/netns/egress-media)
                                                │
                                                ▼
   egress-broker instance "media" (Phase 2 module): allow = Hugging Face hosts (+ civitai opt-in)
     inject."huggingface.co" = Authorization: Bearer <token from valueFile> (map key = exact host)
     audit = /var/lib/egress-broker/media/audit.jsonl
```

The namespace is the one the broker module already creates per instance
(`egress-netns-<name>.service`, `RemainAfterExit`, `ip netns add
egress-<name>`, veth `veb-<name>`/`ven-<name>` with `hostAddress` /
`namespaceAddress` — nixosModules/egressBroker.nix:99-122; cowork.nix joins
it via `NetworkNamespacePath=/var/run/netns/egress-<name>`). Everything in
it has no route except to the broker; anything that ignores the proxy
fails closed — the property Phase 2 proved.

Loopback reachability: podman's `-p` publishing is implemented by podman's
own network stack and is not honoured with `--network ns:<path>`, so the
container binds the namespace address and a `systemd-socket-proxyd`
unit (`comfyui-proxy.socket` on `127.0.0.1:8188`, `comfyui-proxy.service`
forwarding to `10.100.2.2:8188`) gives the operator `localhost:8188`. The
namespace address is link-local to the host (veth, no forwarding; the
broker's nftables accept only the broker port from the namespace) — the
VM test proves it is unreachable from outside.

## Repository `~/flakes/media`

Same skeleton as the gaming flake (pinned `nixpkgs` = host pin, module
uses the host's `pkgs`, githooks, treefmt with ruff for the Python fetch
tool, checks incl. the shared eval harness with `allowUnfree` for the
NVIDIA bits, README, small board). Contents: `nixosModules/comfyui.nix`,
`pkgs/media-fetch/fetch.py` (stdlib: manifest → download via proxy →
sha256 verify → atomic move), `models/manifest.toml`, `tests/`, `checks/`.

## Module `services.comfyui`

| option | default | notes |
|---|---|---|
| `enable` | false | |
| `image.name` / `image.digest` | mmartial/comfyui-nvidia-docker + the digest the factory records at implementation time | assertion: digest matches `^sha256:[0-9a-f]{64}$`; the unit runs `<name>@<digest>`, never a tag |
| `user` / `group` | comfyui | system user, `autoSubUidGidRange = true`, no shell, home = `dataDir` |
| `dataDir` | /var/lib/comfyui | subdirs models/ input/ output/ user/ (tmpfiles, `user`, 0750) |
| `listen.address` | `namespaceAddress` of the broker instance | the in-namespace bind; assertion: equals the instance's `namespaceAddress` |
| `proxy.listen` | 127.0.0.1:8188 | the host-side socket-proxy listener; assertion: loopback only |
| `gpu.enable` | true | `hardware.nvidia-container-toolkit.enable = true` (canonical name at the pin; `virtualisation.containers.cdi.dynamic.nvidia.enable` is the alias) and `--device nvidia.com/gpu=all`; assertion: `hardware.nvidia.package` is set when `gpu.enable` |
| `brokerInstance` | "media" | assertion: `services.egress-broker.instances` has it |
| `models.manifest` | the flake's `models/manifest.toml` | |
| `models.hfTokenFile` | null | **type `lib.types.str`, never `path`** (a path literal would copy the secret into the Nix store); assertion: value does not start with `/nix/store`. Consumed ONLY by the broker's `inject` (below); the fetch tool and the container never see the token |
| `models.civitai.enable` | false | adds `civitai.com` to the allowlist |
| `extraEnv` | {} | passthrough |
| `resources.memoryMax` | "96G" | `MemoryMax` on the container unit |

Credential handling (brief §3 invariant 2: no process holds a provider
credential; credentials are injected at the egress proxy): the module
sets, with `mkDefault` when `hfTokenFile != null`,
`services.egress-broker.instances.media.inject."huggingface.co" = { header
= "Authorization"; prefix = "Bearer "; valueFile = cfg.models.hfTokenFile; }`.
**The attribute name is the exact host the broker matches** — the broker
module passes `inject` through as a host-keyed map
(nixosModules/egressBroker.nix:14-17) and policy.py looks up
`flow.request.pretty_host` in it (pkgs/broker/policy.py:31-36, 181-186);
a label like `hf` would silently never match and every gated download
would fail closed as if no token were set. Only `huggingface.co` needs the
header: the Hub answers gated downloads with signed redirects to the CDN
hosts, which need no credential. Without a token file, gated models fail
with the broker's 401 passthrough and a clear `media-fetch: FAIL` line.

Container unit: `virtualisation.oci-containers.containers.comfyui` with
`podman.user = "comfyui"` (rootless support exists at the pin: `podman.user`,
`sdnotify`), `Requires=`/`After=` `egress-netns-media.service` and
`egress-broker-media.service`. `extraOptions`: `--network
ns:/run/netns/egress-media`, `--device nvidia.com/gpu=all`, `--cap-drop=ALL`,
`--security-opt=no-new-privileges`, `--read-only` with `--tmpfs /tmp`
(verify-first item 3; drop `--read-only` if the image needs a writable
root, recorded as a deviation). **No `--userns=keep-id`.** UID mapping
decision: rootless podman maps in-container root to host `comfyui`; the
image's entrypoint runs as in-container root and switches to
`WANTED_UID`/`WANTED_GID`; v0 sets both to `0` so the ComfyUI process is
in-container root = host `comfyui`, and files under `/data` land on the
host as `comfyui` (verify-first item 4: a file written by the container
must `stat` as `comfyui` on the host; if the image refuses `WANTED_UID=0`,
fall back to `WANTED_UID=1000` with `dataDir` ownership adjusted to the
mapped sub-uid via `podman unshare chown`, recorded as a deviation).
Environment: `HTTP_PROXY`/`HTTPS_PROXY=http://<hostAddress>:<listenPort>`,
`NO_PROXY=<namespaceAddress>,127.0.0.1`, `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`,
`CURL_CA_BUNDLE` → the mounted `ca-bundle.crt`, `COMFY_CMDLINE_EXTRA=
"--listen <namespaceAddress> --port 8188"`, `BASE_DIRECTORY=/data`.

`media-fetch-models` (systemPackages + devShell) reads the manifest,
downloads each missing model via `HTTPS_PROXY` with the broker CA,
verifies sha256, moves into `dataDir/models/<dest>`, refuses to overwrite
a differing existing file, logs `media-fetch: OK <name> <sha256[:12]>` /
`SKIP present` / `FAIL <reason>`, exits non-zero on any FAIL. It runs as
`comfyui-fetch-models.service`: oneshot, `User=comfyui`,
`NetworkNamespacePath=/run/netns/egress-media`, hardened
(`NoNewPrivileges`, `ProtectSystem=strict`, `ReadWritePaths=<dataDir>/models`),
started by the operator by hand (downloads are tens of GB and deliberate).

Broker instance (declared in `hosts/core/media.nix`, `mkDefault` from the
module like cowork.nix): `hostAddress 10.100.2.1`, `namespaceAddress
10.100.2.2`, `listenPort 3130`, `allow` = the Hugging Face host set from
`https://huggingface.co/.well-known/meta.json` at implementation time
(currently huggingface.co, cas-server.xethub.hf.co, transfer.xethub.hf.co,
cdn-lfs-us-1.hf.co, us.aws.cdn.hf.co, us.gcp.cdn.hf.co) plus `civitai.com`
when enabled.

## Starter manifest (v0)

Chosen to prove each modality on 32 GB with a short download: image —
SDXL base 1.0 (fp16) and Z-Image Turbo (fp8); music — ACE-Step v1
(Apache-2.0, native ComfyUI nodes, confirmed); video — Wan 2.2 TI2V-5B
(fp8) with its text encoder and VAE — **included only if verify-first item
5 confirms native (non-custom-node) support in the image's ComfyUI
version; otherwise it moves to the opt-in list and the acceptance video
proof uses whatever native video model the image supports**. Flux.1-dev
and LTX-2 are listed but `gated`/large and off by default. URLs and
sha256 values are recorded from the model cards; the plan forbids guessing
hashes — an implementer that cannot fetch a model card records it as
blocked.

## Host wiring (nixos-agent-env, after the flake exists)

`inputs.media.url = "git+file:///home/dalhaka/flakes/media?ref=main"`;
`nixosConfigurations.core` imports `media.nixosModules.default`;
`hosts/core/media.nix` enables it and declares the broker instance (with
`inject.hf` when a token file is configured). Phase 3 classification: the
model store is public weights (`permitted`), outputs are local; no basket.
Backup: `dataDir/output` and `dataDir/user` added to restic paths;
`models/` excluded (re-fetchable by manifest).

## Testing

- `checks.comfyui-eval`: module evaluates on the harness with a stub
  broker instance; the generated podman argv contains `@sha256:`,
  `--device nvidia.com/gpu=all`, `--network ns:/run/netns/egress-media`,
  `--cap-drop=ALL`, and does NOT contain `-p ` or `--publish`; the
  container env contains no `HF_TOKEN`; the socket unit listens on
  `127.0.0.1:8188`.
- `checks.comfyui-assertion-negative-*` (custom outputs): `proxy.listen =
  "0.0.0.0:8188"`; `image.digest = "latest"`; missing broker instance;
  `models.hfTokenFile = "/nix/store/abc"`.
- `checks.media-fetch-unit` (pytest): manifest parsing, sha256 pass/fail,
  refuse-overwrite, proxy env propagation (mocked opener), a gated model
  that returns 401 → FAIL with a clear message (no token logic in the
  tool).
- `checks.media-fetch-bats`: the tool against a local HTTP mock, incl. a
  wrong-hash case.
- `checks.comfyui-netns-vm` (NixOS VM, no GPU, no network, no image): the
  broker instance + a stand-in listener (`busybox httpd` on
  `10.100.2.2:8188` started inside `egress-media` via
  `NetworkNamespacePath`) + the socket proxy; asserts `curl
  127.0.0.1:8188` reaches it, `ss -ltn` on the host shows 8188 only on
  127.0.0.1, a second VM node on the same virtual LAN cannot reach
  10.100.2.2 or the host's 8188, and from inside the namespace `curl
  https://example.com` fails without the proxy. This is the real
  isolation test; it does not need the image.
- `checks.comfyui-unit-vm` (NixOS VM): with `gpu.enable = false`, the
  container unit starts and fails at `podman pull` (asserted from the
  journal: the failure is the pull, nothing earlier — argv/netns/user
  setup succeeded).
- Operator acceptance `tests/acceptance/media.sh` (GPU, network):
  `comfyui.service` active; `curl localhost:8188/system_stats` names the
  RTX 5090 and a CUDA torch; a file written by the container stats as
  `comfyui` on the host; `media-fetch-models` for the starter set ends
  with only OK/SKIP lines and every fetch appears as `allow` in the broker
  audit with no `HF_TOKEN` in `podman exec comfyui env`; **fail-closed
  proof:** `podman exec comfyui curl -m 5 https://example.com` fails and
  the audit shows a `deny`; **generation proofs:** POST a bundled minimal
  SDXL workflow to `/prompt`, poll `/history`, assert a PNG appears under
  `dataDir/output` within 5 min; a 2-second ACE-Step clip (audio file
  appears); a short clip from the native video model (file appears).

## Security

Rootless container as a dedicated user, capabilities dropped; loopback
only via the socket proxy; digest-pinned image; no route except the
broker; allowlist = model hosts; credential injected by the broker, never
present in any process or file the container can read; models
hash-verified; no custom-node fetching; `MemoryMax`; `Nice=5`. The image
is third-party software with GPU access — the container boundary and the
chokepoint are the controls; bump the digest deliberately.

## Verify-first items for the plan

1. Rootless podman as `comfyui` can open `/run/netns/egress-media`
   (root-created; if the file mode blocks it, the unit adds
   `AmbientCapabilities=` nothing — instead set the netns file readable by
   group `comfyui` from `egress-netns-media.service`'s `ExecStartPost`).
2. RESOLVED 2026-09-02 (round-2 review): inject is per-host — the map key
   is matched against `flow.request.pretty_host`; no broker change needed.
   The eval check asserts the generated policy JSON has an `inject` key
   equal to `huggingface.co` when a token file is set.
3. The image tolerates `--read-only` + `--tmpfs /tmp` and `--cap-drop=ALL`.
4. `WANTED_UID=0` behaviour of the image entrypoint under rootless podman.
5. The image's ComfyUI version supports ACE-Step, Z-Image and Wan 2.2
   TI2V-5B natively.
6. Current Hugging Face host list from `.well-known/meta.json`.
7. `hardware.nvidia-container-toolkit` CDI spec is readable by a rootless
   user (`nvidia-ctk cdi generate` output at `/var/run/cdi`, mode).
8. `systemd-socket-proxyd` package/unit pattern at the pin
   (`systemd.sockets` + `ExecStart=${pkgs.systemd}/lib/systemd/systemd-socket-proxyd`).

## Amendment 2026-09-02 — no container (rev 3 pending)

The pinned image turned out to bootstrap ComfyUI from GitHub and PyPI on
first start (docs/decisions/2026-09-02-media-nix-native-no-container.md).
The operator dropped the container requirement. Rev 3 of this spec replaces
the Architecture, Module and Testing sections with a nix-native ComfyUI
service — same user, namespace, socket proxy, manifest, fetch confinement and
credential injection; ComfyUI itself pinned in the Nix store; no Manager —
once docs/research-2026-09-02-comfyui-nix-native.md settles the packaging
route. Until then the factory's T3 module (commits 20b5c97..83bd48d in
~/flakes/media) is superseded, not wired.
