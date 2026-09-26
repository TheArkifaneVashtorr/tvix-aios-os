# Helm v1 — the switch (design, 2026-09-02, rev 2 after adversarial review)

**Decision basis (operator, 2026-09-02 late):** "Helm is supposed to be a
no-code way to switch between flakes" — both mechanisms on one page: the
machine switches profile, and a flake's workspace opens. Research:
docs/research-2026-09-02-helm-v1-switch.md. Rev 2 folds in 16 review
findings (3 Sonnet lenses): `test` action instead of `switch`, profile-root
fallback for VMs, verb-scoped polkit, Host/Origin allowlists, a specified
lock, a "profiles cannot touch agent units" assertion, non-flake workspaces,
and the v0 → v1 serving hand-over; rev 2 confirmed by a second pass
(13/13 addressed, no new findings). Builds on Helm v0
(docs/superpowers/specs/2026-09-02-helm-design.md) and the workspaces design
(docs/superpowers/specs/2026-09-02-claude-workspaces-design.md).

## Goal

On http://localhost:7700 the operator clicks a profile (`base`, `gaming`,
`media`) and the live machine switches to it without a reboot; clicks a
flake and a terminal opens in that flake's dev shell with its own Claude
session (its own memory). No code, no editing Nix, no password prompt.
Everything privileged goes through one root unit with a fixed allowlist;
the page stays loopback-only and JavaScript-free.

## Non-goals (v1)

LAN access or authentication (Phase 10); changing the boot default (the
`test` action never writes boot entries; after a reboot the machine is on
`base`); mounting baskets from the page (root + YubiKey touch — stays an
operator step until the workspaces mini-phase); opening the Claude
*desktop* app on a folder (no supported flag or deep link — the launcher
opens the CLI `claude` in a terminal).

## Option hierarchy

`services.helm.control.enable` requires `services.helm.enable` (assertion).
Shared with v0: `listen`, `port`, `operatorUser`, `repo`. Under `control`:
`profiles` (list of names, default `[ "base" ]` plus every declared
`specialisation.<name>`), `workspaces.<name> = { path; devShell = "default"
| null; basket = null | "<basket-id>"; }`, `hostAliases` (default
`[ "localhost" "127.0.0.1" ]`).

When `control.enable`: `services.static-web-server` is off (assertion:
exactly one server serves the page); `helm-serve` (below) serves it. The
v0 `helm` group, `/var/lib/helm` `0750`, the `0640` files and
`/etc/helm/config.json 0640 root:helm` are kept unchanged — the collector
and the server are the same UID now, the group still gates the config file
and any future reader. v0's VM test (`helm-vm`) keeps testing the
static-web-server path with `control.enable = false`; v1 adds
`helm-control-vm`.

## Profiles

`hosts/core` declares NixOS specialisations (amended host-wiring plan):

```
specialisation.gaming.configuration = { imports = [ ./gaming.nix ]; environment.etc."helm/profile".text = "gaming"; };
specialisation.media.configuration  = { imports = [ ./media.nix ];  environment.etc."helm/profile".text = "media"; };
environment.etc."helm/profile".text = "base";
```

Each specialisation is a complete toplevel linked under the base system's
`specialisation/<name>`; one operator `nixos-rebuild switch` installs all
of them. `/etc/helm/profile` is the active-profile marker: every activation
atomically remounts `/etc` (nixpkgs `nixos/modules/system/etc/etc-activation.nix`),
so it is always right, in or out of a specialisation.

Switch commands (run by the root unit, never by the page), using the
`test` action — activate + restart changed units, **no bootloader write**:

| target | command |
|---|---|
| `base` | `$ROOT/bin/switch-to-configuration test` |
| `<name>` | `$ROOT/specialisation/<name>/bin/switch-to-configuration test` |

`$ROOT` = `/nix/var/nix/profiles/system` when that path has
`bin/switch-to-configuration`, else `/run/booted-system` (stage-2 populates
it on every boot, including NixOS test VMs, which never set the profile
link). The script logs which root it used. `test` restarts only units whose
files changed; kernel, initrd, GNOME and the NVIDIA driver are untouched.

**Profiles never touch agent units (eval-time assertion, per profile):**
the set of system units whose generated text differs between the base and
the specialisation must contain no unit named `egress-*`, `cowork*`,
`basket*`, `restic-backups-*` or `helm-*`, except units whose name ends in
`-<that profile>` (e.g. `egress-netns-media`, `egress-broker-media` are
*new* in `media`). `helm-serve` is a *user* unit: `switch-to-configuration`
manages system units only, so a profile switch cannot restart the server
that triggered it (confirmed in the pinned switch-to-configuration.pl); no
extra invariant is needed.

## Privilege path

`systemd.services."helm-switch@"` (root, `Type=oneshot`,
`TimeoutStartSec=5min`): `ExecStart` is a generated script that validates
`%i` (regex `^[a-z][a-z0-9-]{0,31}$` AND membership in `control.profiles`
— anything else exits 2 without running anything), logs
`helm-switch: begin <from> -> <to> root=<$ROOT>` (from = marker file),
runs the mapped command, logs `helm-switch: end <to> exit=<n>`. Hardening:
`ProtectHome=yes`, `PrivateTmp=yes`, no environment passthrough.

`security.polkit.extraConfig` (a `lines` option concatenated with other
modules' rules into `10-nixos.rules`; order-independent) grants the
operator `org.freedesktop.systemd1.manage-units` **only with
`action.lookup("verb") === "start"`** and only for the enumerated unit
names (`helm-switch@base.service`, `helm-switch@gaming.service`,
`helm-switch@media.service`), `subject.user === operatorUser`; the rule
returns `undefined` in every other case (never a bare NO that could shadow
another module's rule). ES5-only (polkit 126 = duktape). Generated from
`control.profiles`, so the allowlist cannot drift. No sudo, no setuid.
`stop`, `restart`, `kill`, `set-property` on those units stay
root-only (VM test proves it).

Eval-time assertions: every name in `control.profiles` other than `base` is
a declared `specialisation.<name>`; `base` present; the marker set in every
specialisation and the base; `control.enable → services.helm.enable`; the
polkit snippet contains exactly the allowed unit names and the verb guard
(the eval check greps the rendered rule).

## Backend (`helm-serve`)

A Python 3 stdlib server (`http.server.ThreadingHTTPServer`) as a **user**
unit of the operator (`helm-serve.service`, `WantedBy=default.target`,
`Restart=on-failure`), bound to `services.helm.listen` (loopback asserted).
User-scoped because the launcher must run in the operator's session (the
user manager's environment carries `WAYLAND_DISPLAY` and
`DBUS_SESSION_BUS_ADDRESS` — verified on core) and `systemctl start
helm-switch@…` must be called as the operator for the polkit rule to match.
The server reads `/var/lib/helm/index.html` (v0 renderer unchanged) and
injects the control section (one form per profile, one per workspace) and
the two v1 tiles at serve time.

Routes: `GET /` (page), `GET /status.json`, `POST /action/switch`
(`profile=<name>`), `POST /action/open` (`flake=<name>`). Everything else
404. Forms only — no JavaScript. Each form carries a hidden `token`.

Accepted `Host` values (every route, GET included — defeats DNS
rebinding): `<alias>:<port>` for each of `control.hostAliases` plus the
bound address, e.g. `{127.0.0.1:7700, localhost:7700}`. Accepted
`Origin` values: `http://` + each accepted Host.

Every POST must pass ALL of: accepted `Host`; `Sec-Fetch-Site` is
`same-origin`, or, when the header is absent, `Origin` is accepted (a
missing `Origin` on a POST is rejected); `token` equals the per-boot token;
the target is in the allowlist; the switch lock is free. Any failure →
`403`, one journal line, nothing executed. Per-boot token: 32 random bytes
hex, written `0600` to `$XDG_RUNTIME_DIR/helm/token` by the server at
start (regenerated on restart; the page always embeds the current one).

Cross-site request forgery is the threat: another origin can make the
browser POST to loopback but cannot read the token or forge
`Sec-Fetch-Site`. Residual risk, accepted and documented: any process
running as the operator can read the token or call `systemctl start` on
the allowed units directly — the same trust as the operator's shell.

`POST /action/switch`: acquire `$XDG_RUNTIME_DIR/helm/switch.lock` with
`flock(LOCK_EX|LOCK_NB)` (held by the server process → self-releasing on
crash; a second concurrent request gets `409`), run `systemctl start
helm-switch@<name>.service` blocking with a 6-minute client timeout, then
release; the response page shows the unit's result and the new marker.

`POST /action/open`: spawns the terminal detached (`kgx -e …`, argv form
verified at the pinned GNOME Console in the plan) running
`helm-open-workspace <name>`.

## Workspaces

`control.workspaces.<name>` — attribute names must match
`^[a-z][a-z0-9-]{0,31}$` and `path` must be absolute (assertions).
hosts/core lists nixos-agent-env, gaming, media (flakes) and strategy
(`devShell = null`: plain `cd`, no `nix develop`). `helm-open-workspace
<name>` (generated per host from the option, no runtime lookup of names):
refuses unknown names; if `basket` is set and `/run/baskets/<id>` is not
mounted, prints the exact `basket mount` command and waits for Enter (the
YubiKey step stays the operator's); then `cd <path> && exec nix develop
.#<devShell> -c bash -ic claude` (or `exec bash -ic claude` when `devShell
= null`). Claude's memory for that session is the folder's own memory dir
under `~/.claude/projects` — separate per flake by construction (operator
rule 2026-09-02). The workspaces mini-phase later swaps the last line for
`claude-in <name>`; the page does not change.

## New tiles

- **profile**: active marker, available profiles, last switch from
  `journalctl -u 'helm-switch@*'` (`begin`/`end` pairs): `ok` when the last
  pair ended with exit 0; `warn` "switching…" when a `begin` has no `end`
  and is younger than 10 min, or when the marker file is missing (system
  built before v1); `fail` when the last `end` is non-zero or a `begin` has
  no `end` after 10 min ("switch did not finish — see journal").
- **workspaces**: per entry: path, HEAD short rev (or "not a git repo"),
  dirty?, memory dir present?, basket state (`n/a`, `mounted`, `not
  mounted`).

## Testing

- pytest `tests/helm/test_serve.py`: the validation matrix — Host wrong /
  Host alias accepted / Sec-Fetch-Site `cross-site` / Origin foreign /
  Origin missing without Sec-Fetch-Site / token missing or wrong / unknown
  profile / GET on an action route / lock held → 403 (409 for the lock) and
  the fake runner NOT called; happy path calls exactly `["systemctl",
  "start", "helm-switch@gaming.service"]`; open path spawns the launcher
  argv; the served page has one form per profile and per workspace and no
  `<script`; two concurrent switch requests → one runs, one 409.
- bats `tests/unit/70-helm-switch.bats`: the generated switch script
  rejects `../x`, `gaming;reboot`, an unlisted name (exit 2, stubbed
  commands not run), picks `/nix/var/nix/profiles/system` when present else
  `/run/booted-system`, maps `base` and a name to the right binaries with
  the `test` action, writes the `begin`/`end` lines.
- `checks.helm-control-eval`: the polkit rule text contains exactly the
  three unit names, the verb guard and the operator user; `helm-switch@`
  exists; static-web-server is off; the profiles-never-touch-agent-units
  assertion holds for `gaming` and `media`.
  `checks.helm-control-assertion-negative-*`: `profiles = [ "base"
  "nope" ]`; `control.enable` without `services.helm.enable`; a
  specialisation that changes `egress-broker-cowork`.
- `checks.helm-control-vm` (NixOS VM): a system with a marker-only
  `specialisation.alt`, `control.enable`, operator `alice`, linger on. As
  alice: POST with `Host: localhost:7700`, `Sec-Fetch-Site: same-origin`
  and the token → `/etc/helm/profile` reads `alt` and `readlink
  /run/current-system` changed (root = `/run/booted-system`, logged); back
  to `base` the same way; the negative matrix over curl (foreign Origin,
  wrong Host, no token, missing Origin) → 403 and the marker unchanged;
  `systemctl start helm-switch@nope.service`, `systemctl kill
  helm-switch@alt.service` and `systemctl set-property …` as alice → polkit
  denies; `journalctl -u polkit` shows no prompt for the allowed start.
  This exercises the real specialisation switch inside the VM.
- Operator acceptance `tests/acceptance/helm-v1.sh` + runbook: click
  `gaming` → Steam in the app grid within a minute, marker `gaming`, drift
  tile still green; click `media` → `comfyui.service` active and
  `localhost:8188` answers; click `base` → both gone; click the gaming
  workspace → a Console window with `claude` in `~/flakes/gaming`; the
  broker audit log of the cowork instance shows no restart across the
  three switches.

## Security summary

One root unit, fixed allowlist generated from Nix, polkit grant enumerated
per name and scoped to `start`, no sudo; loopback + Host allowlist on every
route + Fetch-Metadata/Origin + per-boot token + form-only + no JavaScript;
a held `flock` for mutual exclusion; `test` action so nothing is written to
the boot partition; profiles provably cannot restart agent, broker, basket
or backup units; audit lines for every action; baskets never mounted by the
page; residual risk = the operator's own processes.

## Verify-first items for the plan

1. `kgx -e` argv form at the pinned GNOME Console (`kgx --help`).
2. `Sec-Fetch-Site` on same-origin form posts from the hardened Firefox
   (acceptance; the Origin fallback covers absence).
3. `switch-to-configuration test` from inside a specialisation back to
   `base` restarts exactly the expected units (VM test asserts the marker;
   the plan adds a unit-diff assertion from the journal).
