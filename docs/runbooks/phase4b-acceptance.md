# Phase 4b acceptance — what you run

You need: the YubiKey for the `cowork-workspace` basket, a logged-in GNOME
desktop session, and sudo. One command from the repo root:

    nix develop -c tests/acceptance/phase4b.sh

Unlike Phases 1-3, this one drives a real GUI app and talks to Anthropic's
real API — it can't be a throwaway sandboxed test. The script does what it
can on its own and pauses with a `[y/N]` prompt whenever only you, watching
the screen, can judge the result. Answer honestly; a `n` records a FAIL and
the script keeps going so you see everything, but still exits non-zero at
the end.

## What it proves, in order

1. **`cowork-up` works.** The workspace basket decrypts and mounts (touch
   the YubiKey when it blinks), `cowork.service` becomes active, the waypipe
   socket appears, and — this is the one no script can check — the Cowork
   window actually shows up on your screen.
2. **The first session boots the VM.** You connect the workspace inside the
   Cowork UI (it appears there as `/data/cowork`) and send the first message
   ("write hello.txt with a short note"). This is the session that triggers
   the VM image download — see "First boot downloads the VM image" below.
   The script polls for up to 15 minutes, printing the audit log's allow
   count every 30 seconds (expect it to sit flat for a while, see below),
   and fails this step only if `qemu-system` never appears inside that
   window. On that failure the script does **not** stop — it keeps
   recording FAILs through the remaining steps (most will fail, since there
   is no VM to check) so you see the full picture, then still runs step 8's
   teardown so the basket and service don't stay up.
3. **The VM boots.** A `qemu-system` process is owned by the dedicated
   `claude-app` user, and its logs land under
   `/var/lib/claude-app/.config/Claude/logs/` (Electron's standard log
   location, confirmed against the app's own `app.getPath('logs')` call at
   this pin — not a guess). See "VM logs" below.
4. **Confinement holds.** The VM's `qemu-system` process is confirmed to sit
   inside the broker's netns (`ip netns identify`), and a direct request from
   inside that netns — bypassing the broker entirely — fails. This is the
   same proof Phase 2 ran against a throwaway netns; here it's the netns your
   real Cowork session uses.
5. **The basket is the only workspace.** The script confirms the file the
   agent wrote in step 2 landed on the host under
   `/run/baskets/cowork-workspace/`. Then you try a write outside the
   workspace and confirm it's refused — the managed read-path lock plus
   ordinary filesystem permissions catch it.
6. **Traffic is audited.** The broker's audit log
   (`/var/lib/egress-broker/cowork/audit.jsonl`) shows at least one `allow`
   entry to `api.anthropic.com` from the session you just ran. Any `deny`
   entries are not a failure by themselves — see "Expected denies" below.
7. **The user-scope lockdown can't be overridden from project scope.** As of
   the Phase 4b rescope, the lockdown is no longer written machine-wide to
   `/etc/claude-code/managed-settings.json` — that would confine every
   Claude Code session on the host, including the operator's orchestrator
   session, so `hosts/core/default.nix` keeps
   `services.claude-managed-settings.enable = false`. Cowork instead gets
   the identical rendered JSON at claude-app's **user scope**
   (`/var/lib/claude-app/.claude/settings.json`, provisioned by
   `nixosModules/cowork.nix` via `services.claude-managed-settings.settingsFile`).
   The script drops a `.claude/settings.json` *inside the workspace* — a
   **project-scope** file from Cowork's point of view — that tries to widen
   the domain allowlist and disable permission locking. This is the brief's
   explicit test, now run at the scope that actually matters: per
   `docs/research-2026-09-02-phase4.md` and the derisk managed-settings
   research, the security-relevant keys (`allowManagedDomainsOnly`,
   `sandbox.filesystem.allowManagedReadPathsOnly`,
   `allowManagedPermissionRulesOnly`, `disableBypassPermissionsMode:
   "disable"`) are honored only from user/managed/CLI scope (verified upstream for credential masking; acceptance step 7 tests the rest empirically) — a project-level
   settings file can never override them, regardless of what claude-app's
   own user-scope file says. You start a fresh session and confirm the
   override did nothing.
8. **`cowork-down` cleans up.** The service stops, the basket unmounts, and
   `basket doctor` is all-green again — no plaintext left anywhere outside
   the encrypted store.

Expected final line: `PHASE 4B ACCEPTANCE: PASS`.

## First boot downloads the VM image

Cowork on Linux doesn't ship its VM's root filesystem in the app — it
downloads it the first time a session starts, from `downloads.claude.ai`
through the broker: `rootfs.img` (~1.3 GB), plus `vmlinuz`, `initrd`, and the
Claude Code harness bundle. Until that finishes, the window shows nothing but
"Sending…" — that is normal, not a hang.

Expect this to take **several minutes** on a home connection.

**Important: the audit log does not show progress mid-download.** The
broker only writes an `allow` record once a response has been fully relayed
(`pkgs/broker/policy.py`'s `response()` hook — this didn't change when
streaming was added; streaming controls when *bytes* move, not when the
*audit line* is written). `vmlinuz`, `initrd`, and the harness bundle are
small and show up fairly quickly; `rootfs.img` is one ~1.3 GB HTTP response,
so it produces **one late jump**, not a climbing counter. The acceptance
script's step 2 prints this same allow-count/`bytes_in` figure every 30
seconds and it will normally sit flat — sometimes for several minutes —
right up until the download completes. **That flat count is not a failure
signal.** Do not abort on it.

The only thing that means "stop and look" is the acceptance script's
15-minute `qemu-system` timeout, or a *new* `deny` entry for
`downloads.claude.ai` from this run (see "Expected denies" below and the
note on stale entries just after it — do not treat any
`downloads.claude.ai` deny already sitting in the log from an earlier run as
today's signal).

**There is no live in-flight signal to watch, on purpose.** It's tempting to
reach for `journalctl -u egress-broker-cowork -f` for something to watch
while you wait, but it will not show you the download happening: mitmproxy's
request-logging addon (the `dumper`, which is what writes to that journal)
only prints a flow's summary from its `response()` hook — the same moment
the audit line for it is written, once the whole response has already been
relayed. So the journal is exactly as silent as the audit log until
`rootfs.img` finishes, then both print at once. Don't take a quiet journal
as a bad sign either; the acceptance script's step-2 timeout is the only
real "something's wrong" signal here. The audit log itself is
world-readable if you want to tail it directly:

    tail -f /var/lib/egress-broker/cowork/audit.jsonl | jq -c 'select(.host=="downloads.claude.ai")'

## Expected denies

These hosts are denied by design — Cowork works fine without them. Seeing
them in the audit log is not a bug:

| Host | Why it's denied |
| --- | --- |
| `browser-intake-us5-datadoghq.com` | telemetry |
| `o1158394.ingest.us.sentry.io` | crash telemetry |
| `redirector.gvt1.com` | Chrome component updater |
| `bridge.claudeusercontent.com` | Claude-in-Chrome bridge; retries every 30s |
| `js.hcaptcha.com` | sign-in page extra |
| `accounts.google.com` | sign-in page extra |
| `widget.intercom.io` | sign-in page extra |
| `a.claude.ai` | CDN / analytics |
| `a-cdn.anthropic.com` | CDN / analytics |
| `s-cdn.anthropic.com` | CDN / analytics |
| `assets.claude.ai` | CDN / analytics |

**The audit log is append-only and never rotated or truncated** — the
acceptance script only ever tails/summarises it, never clears it — so a
`downloads.claude.ai` deny (or any deny above) sitting in the log from a
*previous* run is not evidence of anything happening right now. The
acceptance script's own deny counts (step 2 and step 6) are already scoped
to `ts >= run_start`, i.e. this run only, so you don't need to think about
this when reading its output. If you're reading the log by hand instead,
filter by time the same way, e.g. `jq -c --argjson since
"$(date -d '10 minutes ago' +%s)" 'select(.ts >= $since and
.verdict=="deny")' /var/lib/egress-broker/cowork/audit.jsonl`.

**Likely next legitimate denies**, if you keep using Cowork past this
acceptance run: `platform.claude.com` (expected to be needed for OAuth
token refresh — not yet confirmed against a deny in this session) and
`*.frame.claudeusercontent.com` (artifacts). If you see either,
treat it the same as any other deny — grow the allowlist from it (see
"Growing the allowlist" below), don't add it speculatively ahead of time.

## VM logs

The Cowork VM's own boot/session logs (Electron's standard log location for
this app):

    sudo ls /var/lib/claude-app/.config/Claude/logs/

(sudo is needed — it's the dedicated `claude-app` user's home, not yours.)

## Growing the allowlist (expect to do this at least once)

Cowork's allowlist starts minimal and is deliberately grown one domain at a
time, only from what the broker's audit log actually denies (see "Expected
denies" above for the ones already known and accepted). A real session may
turn up more (a new telemetry endpoint, a new CDN host, a product feature).
The procedure, every time:

1. Read the deny entries (no sudo needed — the audit log is world-readable):
   `jq -c 'select(.verdict=="deny")' /var/lib/egress-broker/cowork/audit.jsonl`
2. Check the denied host against the "Expected denies" table above. If it's
   not there and it's a legitimate Cowork dependency (not something you
   don't recognize), add it to BOTH
   `services.egress-broker.instances.cowork.allow` and
   `services.claude-managed-settings.allowedDomains` — set in
   `nixosModules/cowork.nix` / `nixosModules/claudeManagedSettings.nix`, and
   both overridable from host config (the broker instance's `allow` is set
   with `lib.mkDefault`; `allowedDomains` is a plain option default, also
   overridable) — with a one-line comment saying why. There is no
   `services.cowork.allowedDomains` option; the allowlist lives in those two
   module options.
3. `nix build .#nixosConfigurations.core.config.system.build.toplevel` to
   confirm it still builds, then `sudo nixos-rebuild switch --flake
   ~/nixos-agent-env#core` when you're ready to apply it (that switch is
   your call, same as Phase 4a — never run it automatically).
4. Re-run `cowork-up` and retry.

Never widen the allowlist speculatively, and never add a domain you don't
recognize without checking what it is first — a deny is the broker doing its
job.

## If a step fails

- **cowork-up fails / no window appears:** `journalctl -u cowork -e`. Common
  causes: basket not encrypted yet (`basket encrypt` first), YubiKey not
  touched in time, `/dev/kvm` or `vhost_vsock` missing (`basket doctor`
  checks the latter).
- **VM doesn't boot / no qemu-system:** check
  `/var/lib/claude-app/.config/Claude/logs/` (sudo needed — it's the
  dedicated user's home) for the helper's own error; the app's capability
  probe wants firmware and virtiofsd at hardcoded `/usr/...` paths, which
  `programs.claude-desktop.cowork.enable` symlinks in from the Nix store —
  confirm those symlinks exist if this is a fresh switch.
- **Confinement check fails:** this is the layer that must never be worked
  around. Do not proceed to using Cowork until `ip netns identify` on the
  VM's process reports the broker's netns and direct egress from it fails.
- **Managed-settings override "worked":** stop and treat this as a real
  finding, not a script bug — it means claude-app's user-scope lockdown
  (`/var/lib/claude-app/.claude/settings.json`) has a hole. Don't use Cowork
  with real data until it's understood and fixed.
