# OAuth / Proton Pass / router spike

A privacy-screened docs spike in answer to the operator's question (the
session's "answer 44"): *can we add the oauth keys to Proton Pass and do a
redirect so everything can go to the router?* Nothing stored, nothing
redirected: this document gathers what the sign-ins are, where their tokens
sit, what the router (egress broker) can and cannot do for an OAuth-bearing
client, and what Proton Pass offers on this host — then screens each
candidate flow against "would this help an adversary" (decision 2,
`docs/decisions/2026-09-09-seat-driving-authority.md`) and the six
invariants of `docs/brief.md` §3.

Every claim is labelled **measured** (the command that produced it is cited),
**inferred** (a reading of the source, no live probe), or **UNMEASURED** (no
command in this session; flagged for the operator). No credential value,
hash or fragment appears anywhere in this document — the store's own secret
detector (`pkgs/evidence/streams.py:94`, applied to every stream row at
`:678`) is the gate over this file. Measurement labels and numbers are
re-run at commit time.

---

## 1. The sign-ins that exist

### 1.1 The `chatgpt-work` flake's isolated device sign-in (commit `eaf4b82`)

- **Repo and commit.** `~/flakes/chatgpt-work`, commit `eaf4b82`, subject
  "auth: provide isolated operator device sign-in (test: oauth-entry, lint)"
  — **measured** with `git -C ~/flakes/chatgpt-work show -s --format='%h %s' eaf4b82`.
- **What it is.** A dedicated operator sign-in console for a lab VM
  (nixosConfigurations.lab). It uses the pinned Codex 0.146.0 *only* for
  device login and login status — it starts no coding agents and releases no
  model-runtime gate (contract `contracts/oauth-provisioning-v1.json`: the
  console is `operator_login_only`, `sign_in_is_model_runtime_readiness` is
  `false`).
- **The flow.** The operator runs `nix run --offline --no-write-lock-file
  ~/flakes/chatgpt-work#lab-vm` from a private state directory
  `/home/dalhaka/.local/state/chatgpt-work/operator-vm`, enters `1` to
  request a device login, opens the displayed verification URL in their own
  browser, enters the one-time code, then `2` to check status
  (`docs/runbooks/oauth-entry.md`).
- **Token storage path.** The Codex auth store is a file (the fixed config
  argument `cli_auth_credentials_store="file"`), written under
  `CODEX_HOME = /run/chatgpt-oauth/codex` — **measured** from
  `contracts/oauth-provisioning-v1.json` `private_state` (`codex_home =
  /run/chatgpt-oauth/codex`, `root = /run/chatgpt-oauth`). The directory is a
  guest tmpfs (`filesystem: guest_tmpfs`, `owner_uid: 41010`,
  `directory_mode: 0700`, 64 MiB). Nothing is persisted across a VM exit:
  `lifetime: keep_guest_running_after_sign_in; VM exit_or_restart_requires_new_sign_in`.
- **Storage path measured on the module.** `modules/oauth-provisioning.nix`
  — **measured** — renders a tmpfs mount at `/run/chatgpt-oauth`
  (`mode=0700,uid=41010,gid=41010,nosuid,nodev,size=64M`), runs the
  provisioner as `lab-oauthProvisioner` (UID 41010) with
  `RuntimeDirectory = chatgpt-oauth`, `InaccessiblePaths = [ state ]` for
  nix-daemon, and `ReadWritePaths = [ state ]` for the unit. The bounded
  login (`pkgs/oauth-provisioning/bounded-login.py`, **measured**)
  sets `HOME=/run/chatgpt-oauth/home`, `CODEX_HOME=/run/chatgpt-oauth/codex`,
  and the other XDG dirs under the root, with `stdin=null`, no inherited
  auth descriptor, and no browser fallback.
- **Adversary-relevant facts.** It is a *separate, isolated* sign-in: no host
  home, no host auth store, no predecessor session is imported; the token
  never enters nixpkgs, ordinary backups, or test evidence
  (`docs/runbooks/oauth-entry.md`; contract `ordinary_backup_inclusion:
  false`, `host_home_or_auth_mount: false`). The actual account sign-in is
  the operator's; the synthetic AUTH0 check makes no real OAuth call
  (`real_auth_calls_by_executor: 0`).

### 1.2 The Codex arm's OAuth (the host Codex CLI, `~/flakes/codex`)

- **Repo and binary.** `~/flakes/codex` wraps a pinned Codex CLI; on the host
  `command -v codex` resolves to `/home/dalhaka/.local/bin/codex` →
  `/home/dalhaka/.codex/packages/standalone/current/bin/codex` — **measured**
  (`ls -l /home/dalhaka/.local/bin/codex`). The Codex arm of the seat driver
  (`docs/superpowers/plans/2026-09-08-codex-driver-arm.md:60`) explicitly
  never reads `~/.codex/auth.json`.
- **Storage path.** The Codex CLI holds its ChatGPT/OpenAI OAuth session in
  `~/.codex/auth.json` on this host — **measured**:
  `~/.codex/auth.json` exists, mode `0600`, and its JSON keys are
  `auth_mode`, `OPENAI_API_KEY`, `tokens` (with `id_token`,
  `access_token`, `refresh_token`, `account_id`), and `last_refresh`
  (**structural keys only; no value read, printed or redirected**). The token
  store is the same `cli_auth_credentials_store="file"` mechanism as §1.1.
- **The plan it cites.** `docs/superpowers/plans/2026-09-08-codex-driver-arm.md`
  — the Codex CLI authenticates to OpenAI over `wss://api.openai.com/...`;
  the driver and its tests never touch the credential file, and no test may
  launch the real `codex` (the fake on `PATH` is the only reachable binary).
  The runtime routing also never dials a *credential*-bearing provider by
  accident: the tests redirect the provider base URL to a closed loopback
  port and assert the upstream host name is absent from the report (D10/x;
  README "No check dials api.openai.com").
- **Adversary-relevant facts.** This is the operator's primary Agentic sign-in,
  running with `--sandbox danger-full-access` on the host **outside** the seat
  lane and broker (accepted by decision 2026-09-07, point 4, cited in the
  plan). Its token is the most valuable OAuth material on the box.

### 1.3 The OpenRouter key (broker-injected, not OAuth)

- **What it is.** The lanes and the seat egress to OpenRouter through egress
  brokers that inject an `Authorization` header from
  `/var/lib/secrets/openrouter-key` (`hosts/core/lanes.nix`,
  `hosts/core/seat.nix`). This is a static API key, not an interactive OAuth
  flow.
- **Storage path / handling.** `docs/runbooks/lanes.md` — **measured** — the
  tmpfiles rule `z /var/lib/secrets/openrouter-key 0440 root egress-broker -`,
  keyed to the broker user only; the module asserts the key file is never a
  `/nix/store` path; "vault of record: Proton Pass". No process path on the
  host holds the value in its environment (the seat unit's placeholder is
  "injected-by-broker", `nixosModules/seatLane.nix`).

### 1.4 Any other sign-ins

- **Proton Drive CLI.** `proton-drive auth login` opens a browser sign-in and
  saves the session in the GNOME Keyring (`docs/runbooks/backup.md:50-51`,
  **measured**); its per-user state is `~/.local/share/proton-drive-cli/`
  (`clientUid.json`, `events.json`; **measured** by `ls`). This is the one
  non-Agentic Proton credential already on the box.
- **Proton Mail / Proton Pass.** `protonmail-bridge` (IMAP/SMTP bridge,
  `--cli` flag available) and the `proton-pass` desktop app hold their own
  logins (see §3). Their sessions are in a logged-in desktop, not reachable
  headlessly.

---

## 2. What "the router" is here, and what a redirect would require

The phrase "the router" in the operator's question maps onto two artefacts in
this repo, and this spike reads them together:

1. **The routing table** — `docs/superpowers/plans/2026-09-05-harness-router.md`
   is the plan under which the harness's agents choose sub-agent models
   through `docs/ledger/routing.toml` (pure-bash `factory_route`, OpenRouter
   route only). **Measured**: the plan's Goal names routing.toml and
   model choice; it is a *model* router, not a network redirector.
2. **The egress broker** — `nixosModules/egressBroker.nix` plus the seat/lane
   modules, **measured** in full. This is the network chokepoint a redirect
   would pass through (brief §3 invariant 3).

For "a redirect through the router", the meaningful interpreter is the
**egress broker**: a client whose traffic we want "to go to the router" is
pointed at a broker instance, which logs, optionally patches, and injects
credentials at egress.

### 2.1 What the egress broker is (`nixosModules/egressBroker.nix`)

- One `mitmproxy` instance per `services.egress-broker.instances.<name>`, in
  a persistent netns (`/run/netns/egress-<name>`), veth
  `veb-<name>`/`ven-<name>`, `--mode regular` proxy at
  `hostAddress:listenPort`, `--set connection_strategy=lazy`, `--set
  ssl_verify_upstream_trusted_ca=/etc/ssl/certs/ca-certificates.crt`
  (upstream TLS verified), `--set stream_large_bodies=1m`, audit and usage
  JSONL under `/var/lib/egress-broker/<name>/`.
- **Credential injection.** Per destination host, an `inject.<host>`
  submodule with `header` (default `Authorization`), `prefix` (a bearer
  prefix), `paths` (default `/`), and `valueFile` (the on-disk credential
  the broker reads into memory and adds at requestheaders time). The Nix→wire
  mapping is `valueFile -> value_file` (`renderPolicy`, **measured**).
- **Allowlist / deny / body-patch.** `allow` is the set of hostnames the
  instance forwards; `denyPaths.<host>` refuses before injection (audit
  reason `path-not-permitted`); `bodyPatch.<host>` merges data-policy fields
  into request bodies (e.g. OpenRouter zero-data-retention routing, brief §3
  invariant 5).
- **Enforced invariants.** The broker key file is never a `/nix/store` path
  (assertion, `nixosModules/seatLane.nix`); any process that can complete the
  TCP handshake to the broker address could spend the injected credential,
  so an nftables input chain accepts only the netns's own source on
  `veb-<name>` (`iifname "veb-<name>" … ip saddr ${namespaceAddress} accept`);
  consumer units run with `InaccessiblePaths = [ "/var/lib/secrets" ]` so no
  network-capable agent ever stat's the key (brief §3 invariant 2).

### 2.2 The existing "redirect" pattern (how a client already goes to the broker)

**Measured** from `nixosModules/seatLane.nix` and `modelLane.nix`: a client
in the broker's namespace is redirected by environment:

- `HTTPS_PROXY` / `HTTP_PROXY` = `http://<hostAddress>:<listenPort>`
  (the broker is `--mode regular`, an HTTP CONNECT proxy); `NO_PROXY` for
  loopback.
- `NODE_EXTRA_CA_CERTS` / `SSL_CERT_FILE` / `NIX_SSL_CERT_FILE` =
  the broker's public CA bundle at
  `/var/lib/egress-broker-ca-bundle/<name>/ca-bundle.crt` — the client must
  trust the broker's CA or TLS to the proxy fails.
- The unit is moved into the broker's netns
  (`NetworkNamespacePath = /run/netns/egress-<name>`), and for the seat the
  unit's `OPENROUTER_API_KEY` is the placeholder `injected-by-broker`; the
  broker replaces the header at egress. The operator starts jobs one at a
  time (nothing is `wantedBy` anything).

**So a redirect that "goes to the router" for an OAuth-bearing client
already has a working pattern to copy** — it needs:

1. **Hosts.** An `services.egress-broker.instances.<name>` whose `allow`
   names the OAuth destination host(s) the client talks to. Today instances
   allow exactly one host (`seat`: `openrouter.ai`; the lane:
   `openrouter.ai`; `cowork`, `media` have their own). An OpenAI/Codex
   redirect would need an instance whose `allow` includes the resolveable
   OpenAI endpoints (auth + API), or the client routed only at the API layer.
2. **Headers.** An `inject.<host>` entry with the header the OAuth provider
   expects and a `valueFile` holding the credential. But `inject` only ever
   sets one **static** header per host from a key file — it does not and
   cannot complete an interactive OAuth/device-code flow, rotate a refresh
   token, or select among per-session tokens. This is the crux: **the broker
   injects a static bearer credential, it is not an OAuth client**.
3. **TLS termination.** The broker already terminates TLS toward the client
   (it must, to read/inject the header) and verifies upstream TLS. But a
   Codex client uses `wss://` (WebSocket) for responses — `mitmproxy` in
   `--mode regular` proxies CONNECT tunnelling, and an SSE/WebSocket flow is
   already handled (policy addon forces SSE streaming past the 1 MiB buffer
   threshold, `egressBroker.nix` comment), but whether the broker's
   WebSocket support for the Codex `responses` endpoint works end-to-end is
   **UNMEASURED** here.
4. **Netns + CA trust.** The client must run in (or be proxied to) the
   broker's netns and trust the broker CA.

### 2.3 The mismatch the spike found

**Inferred** from the above. The question "put the oauth keys in Proton Pass
and redirect so everything goes to the router" conflates two things the
current machinery separates:

- The broker injects credentials that already live in **root-only key files**
  (`/var/lib/secrets/...`) specified by `inject.<host>.valueFile` in Nix.
  "The router" never reads Proton Pass today, and there is no mechanism to
  make a static broker inject read a Proton Pass secret (Proton Pass has no
  on-host CLI/API to expose one; see §3).
- OAuth material is not a static key: it is a token + refresh flow. The
  broker's `inject` model fits a static API key (OpenRouter), not an OAuth
  session. Directing Codex's OAuth *through* the broker would either require
  the broker to store/rotate tokens (a new, high-value attack surface) or a
  reduction to a static injected bearer that cannot refresh on its own.

---

## 3. What Proton Pass offers on this host (without a browser extension)

### 3.1 The `proton-pass` package is a desktop Electron app, no CLI

- **Measured.** `readlink -f /run/current-system/sw/bin/proton-pass` →
  `/nix/store/lzbsdvadb2ih3idnfd59cyvhjkln9n29-proton-pass-1.36.1/bin/proton-pass`.
  The wrapper is an Electron launcher:
  `exec …/electron …/app.asar "$@"` (**measured** by `cat` of the wrapper).
  The package is built from the Proton `.deb` (`proton-pass_1.36.1_amd64.deb.drv`
  is in the store), i.e. `python3 …` of the `.drv` shows `has .deb source: True`,
  `electron referenced: True`).
- **Measured.** Running `proton-pass --help` headless fails: it needs an X
  server / `$DISPLAY` and D-Bus ("Missing X server or $DISPLAY"; "Failed to
  connect to socket /run/dbus/system_bus_socket"). There is no `--cli`,
  no headless mode, no stdout command surface.
- **Measured.** The local config `~/.config/Proton Pass/config.json` holds
  only app/window state — keys `__internal__` (migrations) and `windowConfig`
  (x/y/width/height/maximized/zoomLevel). **No secret material is stored in
  that file.**
- **Measured (structure only).** Under
  `~/.config/Proton Pass/Partitions/app/`, Proton Pass keeps a Chromium
  profile (`Local Storage/` leveldb, `IndexedDB/`, `Session Storage/`,
  Service Worker cache; ~3.1 MiB total). This is a *logged-in browser
  session cache*, not a usable store: the pass vault plaintext lives in
  Proton's cloud and is reached through the desktop app's TLS session, not in
  a readable local DB.
- **Inferred / UNMEASURED.** Proton has no *standalone Pass CLI/API* shipped
  in this nixpkgs pin that exposes vault items to a headless unit. There is
  a community/third-party Pass CLI ecosystem, but none is installed here and
  none would work without a session plus the same keyring the app uses
  (UNMEASURED: not attempted, by design — see §4).

### 3.2 What Proton does ship on this host

- **`proton-drive` (the official Drive CLI)** — **measured** on PATH
  (`command -v proton-drive` → `/run/current-system/sw/bin/proton-drive`),
  packaged from `pkgs/proton-drive-cli` (v0.8.0). It talks to Proton Drive,
  not the Pass vault. Auth = `proton-drive auth login` (browser) + GNOME
  Keyring session (`docs/runbooks/backup.md:50-51`). `clientUid.json` +
  `events.json` in `~/.local/share/proton-drive-cli/`.
- **`protonmail-bridge`** — **measured** on PATH, an IMAP/SMTP bridge with a
  `--cli`/`--noninteractive` flag, but it serves *e-mail*, not pass
  credentials.
- **`proton-pass`** — the desktop vault app only (§3.1).

### 3.3 Can a secret be read back by a unit without a human?

**No — measured and inferred.** Every Proton path on this host terminates in
a human's logged-in desktop:

- Proton Pass: the only surface is the Electron GUI, which needs X + D-Bus +
  a logged-in session; the vault lives in the cloud, not a readable local
  file, and there is no CLI/API to dump an item headlessly.
- Proton Drive: its session depends on the gnome-keyring / libsecret, which a
  `systemd --user` unit can only use in a logged-in desktop session (the
  push timer's known limit, `docs/runbooks/backup.md` §Known limits, **measured**).

So the operator's idea "put the oauth keys in Proton Pass and read them back
into a unit" has no headless read-back path today on this host: a unit cannot
retrieve a Proton Pass secret without either the desktop app humanly
unlocked or a (nonexistent) Pass CLI/API. This directly constrains any
redesign that wants Proton Pass as a machine-readable store (§4 decision 2,
§5).

---

## 4. The privacy screen

Screen every candidate flow against decision 2 — *"would this help an
adversary"* (`docs/decisions/2026-09-09-seat-driving-authority.md`, decision
2, `data sharing is case-by-case, never to enemies`) — and name the brief §3
invariant each touches. The standing invariant: *privacy outranks everything;
nothing leaves the machine* (already binding via brief §3 invariants 1–6,
G8).

| Candidate flow | Would it help an adversary? | Invariant(s) touched | Verdict |
|---|---|---|---|
| **Import the chatgpt-work VM device token into Proton Pass, then store/redirect it.** The token lives in a disposable guest tmpfs and is bound to a one-time device sign-in with a browser step; copying it into a cloud-synced vault copies agentic credential material out of its isolated tmpfs into a third-party cloud store. | **Yes.** It moves the most isolated sign-in (guest tmpfs, no host/backup exposure) into a form reachable by an attacker who compromises the Proton account or a machine-readable Proton reader; it also breaks the §3 (invariant 1) "tmpfs only" and (2) "no plaintext credential outside egress" posture, and gives an adversary the *copy* plus the human-reachable vault copy. | 1, 2, 3, 5 | **Reject.** Keep the device login in its guest tmpfs; its whole design point is that it *cannot* be recovered into a vault. |
| **Store the host Codex OAuth (`~/.codex/auth.json`) in Proton Pass and inject via the broker.** The broker injects one static bearer from a root-only key file; OAuth is a token+refresh flow the broker cannot complete, and the token is the operator's primary Agentic credential. | **Yes.** If a broker instance ever held the full OAuth token set, the broker becomes the single richest credential target on the box; a static bearer that cannot refresh would either stale out (breaking the seat) or be the whole login leaked at the chokepoint. Mitigation (keep broker as root-only valueFile, never Proton) reduces the exposure but keeps an OAuth token in a static file the broker rewrites — a bigger value than today's OpenRouter key. | 2, 3, 5 | **Reject for now.** Do not route OAuth through a static-inject broker. Revisit only if a real OAuth-capable egress is ever scoped, and even then keep credentials root-only (invariant 2), never Proton-sourced (§3.3). |
| **A unit reads a Proton Pass secret back headlessly.** | **Yes.** If such a path existed it would be a new headless reader of an entire cloud vault from a network-capable process, the opposite of the current "only a human in a logged-in desktop" boundary | 2, 3, 4 | **Reject.** And it does not exist today on this host (§3.3). |
| **OpenRouter key already handled today (direct injection from `/var/lib/secrets`)** | **No.** Already minimised: root-only file, broker-injected at egress, never in a process environment; Proton Pass is the human-only vault of record for the paste-back path. | 2, 3, 5 | **Keep as-is.** This is the pattern a future change should copy, not rewrite. |
| **Proton Drive CLI (backup push) reading the vault** | **No.** It only ever reads the restic ciphertext repo path; it authenticates to Drive via keyring and never touches Pass or broker keys. | 2, 3 (backup), 4 | **Keep as-is.** |

**Summary of the screen.** Every flow that would move OAuth/device material
into Proton Pass and *then* make the router inject or read it fails the
adversary question on invariants 1, 2, 3, and 5, and is also technically
blocked: the broker injects static credentials from root-only value files and
cannot run an OAuth flow, and Proton Pass exposes no headless read-back. The
only flow that keeps the current design's strength is the existing
OpenRouter key injection — root-only value file, egress-injected, human-only
vault of record.

---

## 5. Questions for the operator (each with a recommendation and a default)

1. **Q: Should we put any *new* credential in Proton Pass for machine use?**
   Recommendation: **no** — Proton Pass today holds the human copies (the
   OpenRouter key and the restic password, both only pasted by hand into
   root-only key files or a device console) and exposes no headless read-back
   (§3.3). **Default:** no machine read from Proton Pass; Proton Pass stays
   the human-only vault of record; `docs/runbooks/lanes.md` and
   `docs/runbooks/backup.md` already say so.
2. **Q: Should OAuth (Codex/OpenAI, chatgpt-work) go through the broker
   at all?** Recommendation: **not through a static-inject broker**, because
   the broker can hold only a static bearer (`inject.<host>.valueFile`) and
   cannot refresh an OAuth token (§2.3). If the goal is "everything's egress
   through one chokepoint", the realistic subset is *static-key providers
   (OpenRouter)*, which already are; an OAuth client like Codex would need a
   genuine OAuth-aware egress, which does not exist here. **Default:** no new
   OAuth routing.
3. **Q: Is the operator's "redirect so everything can go to the router"**
   satisfied by the existing per-instance proxy pattern (env
   `HTTPS_PROXY`/`HTTP_PROXY` + broker CA + netns)? Recommendation: **yes for
   static-key clients**, which is what is wired today; anything else requires
   scoping a broker instance per new upstream host. **Default:** keep the
   OpenRouter + seat/lane instances; add an instance only for a concrete
   new static-key upstream the operator names.
4. **Q: Should the isolation of the `chatgpt-work` device sign-in be relaxed
   (recovery into a vault, transfer to a future broker)?** Recommendation:
   **no** — its entire value is that it is unrecoverable and tmpfs-bound
   (§1.1, §4). **Default:** leave the guest tmpfs design untouched.
5. **Q: Is a broker WebSocket/SSE + OAuth pass-through (e.g. Codex
   `wss://` responses through the broker) in scope?** Recommendation:
   **defer** — the SSE streaming path is proven, the WebSocket+CONNECT
   handling for a long-lived `wss://` responses flow is UNMEASURED and would
   need a VM/integration test before any decision. **Default:** no work now;
   this spike records the open question.

---

## 6. Commands run (all read-only; nothing stored, nothing redirected)

- `git -C ~/flakes/chatgpt-work show -s --format='%h %s' eaf4b82`
- `cat ~/flakes/chatgpt-work/docs/runbooks/oauth-entry.md`
- `python3 -c "… json.load(open('~/flakes/chatgpt-work/contracts/oauth-provisioning-v1.json')) …"` (fields read: `private_state`, `native`, `console`)
- `grep -n … modules/oauth-provisioning.nix` (tmpfs mount, uid, RuntimeDirectory, InaccessiblePaths, ReadWritePaths)
- `sed -n '40,130p' pkgs/oauth-provisioning/bounded-login.py`
- `ls -l ~/.codex/auth.json`, `~/.codex/` (metadata); `python3 … json.load(open('~/.codex/auth.json'))` **keys only**
- `grep -n 'never `~/.codex/auth.json`' docs/superpowers/plans/2026-09-08-codex-driver-arm.md`
- `command -v codex; ls -l /home/dalhaka/.local/bin/codex`
- `cat nixosModules/egressBroker.nix nixosModules/seatLane.nix nixosModules/modelLane.nix`
- `grep -rn 'hostAddress\|namespaceAddress\|listenPort\|valueFile' hosts/core/*.nix nixosModules/seatLane.nix nixosModules/modelLane.nix`
- `readlink -f /run/current-system/sw/bin/proton-pass; cat …/bin/proton-pass`
- `proton-pass --help` (headless, expected to fail: no X/D-Bus)
- `python3 -c "… json.load(open('~/.config/Proton Pass/config.json')) …"` **keys only**
- `ls -la ~/.config/Proton Pass/; find …/Partitions -maxdepth 2 -type d`
- `command -v proton-drive; command -v protonmail-bridge`
- `protonmail-bridge --help`
- `grep -n 'auth login\|Keyring\|login keyring' docs/runbooks/backup.md`
- `nix search nixpkgs proton-pass` and `nix search nixpkgs 'proton'` (**UNMEASURED** — the pinned channel extends no headless Pass CLI; the search reached no network and returned an empty candidate set; flagged)

---

*A note on scope.* This is a gather-and-screen spike only, in answer to the
operator's question. Nothing here stores, holds, moves or redirects any
credential; the five questions in §5 are the output. G8 binds throughout: no
credential value, hash or fragment is quoted, and every storage path is
measured rather than every value. The secret detector over this file is the
gate.