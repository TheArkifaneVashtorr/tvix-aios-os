# Helm — what the status page shows

Helm is a page on this machine that answers one question at a glance: is
everything healthy right now, without you running any acceptance script by
hand. Open **http://localhost:7700** in Firefox. `helm-status` on the
command line prints the same nine health tiles plus the Profile card as text,
if you'd rather not open a browser.

Its two user timers (`helm-collect.timer`, `helm-flake-check.timer`) are
installed and enabled by the switch, but a switch does not *start* a timer
newly enabled inside a session that was already logged in — start them once
by hand after the first switch (`docs/runbooks/switch-helm-gaming.md`
§3: `systemctl --user start helm-collect.timer helm-flake-check.timer`).
After that one-time start, both run on their own: `helm-collect.timer`
regenerates the page every 5 minutes, `helm-flake-check.timer` refreshes the
**flake-check** tile at 03:00.

Nobody outside this machine can see this page — it only answers on
127.0.0.1 (loopback), and Helm itself never makes an outbound network call.
The only exception is the optional nightly flake check, and that runs with
`--offline`, so it can't either.

## Reading the page

Each tile is one thing Helm checked, colour-coded:

- **green (ok)** — healthy, nothing to do.
- **amber (warn)** — degraded but not broken; worth a look when convenient.
- **red (fail)** — needs attention.
- **grey (unknown)** — Helm couldn't check this (a missing binary, a
  timeout, a parse error). Grey is not itself an emergency, but it means
  Helm has no opinion on that tile — treat it as "unverified", not "fine".

Each tile prints its verdict word and says since when it has shown it; the
history lives in the evidence store (`helm-status.jsonl`), one line per
change plus one an hour. Times on the page are local (CDT); the collector's
own file stays UTC.

Click a tile's "detail" line to expand the raw data Helm based its verdict
on (also escaped and safe to read even if it contains attacker-influenced
text, like a denied hostname).

The page carries no separate "collector stale" indicator — the header's
generated timestamp is the check. If it's more than a couple of collection
intervals old (normally 10 minutes), the collector isn't running; confirm
with `systemctl --user status helm-collect.timer` before trusting any of
the tiles below it.

## The Profile card

Above the nine tiles sits the **Profile** section — the read-only switch
page. It shows which profile is running and the last switch; the switch
itself now happens behind your password (details and guarantees are in
`docs/runbooks/helm-v1.md`).

The switch asks for your password — the page no longer carries a form or a
token, so nothing that runs as you (the DeepSeek seat, the desktop app's
Claude Code) can flip the machine without the desktop password (polkit
`auth_admin_keep`, claim `uid1000-can-switch-profile`). The seat guard's
port rule is a tripwire (`dsh-openrouter --denials`), not a wall.

## The nine health tiles, and what to do on red

**backup-snapshot** — age of the newest local restic snapshot
(`/var/lib/restic/core`). Red means no snapshot in the last ~50 hours, or
none at all. Check `systemctl status restic-backups-core-local` and
`docs/runbooks/backup.md`.

**backup-parity** — whether the last Proton Drive push reported `OK` and
how long ago. Red means the last push failed or none has run recently.
The tile also reads the unit's own last result, so a push that failed shows
red even when the last log line was a success. Check
`systemctl --user status proton-drive-push` and
`journalctl --user -u proton-drive-push`.

**timers** — whether every timer Helm is told to audit
(`services.helm.timers.system` / `.user` in `nixosModules/helm.nix`, today
`restic-backups-core-local.timer`, `proton-drive-push.timer`,
`helm-collect.timer`, `helm-flake-check.timer`) is armed: active, with a
next run time. Red names the offender under one of two prefixes:
`not armed: <timer>` when a timer is unarmed — usually one that got
`enabled` by a switch but never `start`ed inside an already-logged-in
session (see `docs/concepts/2026-09-02k-post-switch-activation-audit.md`);
and `failed: <service>: <result>` when a timer is armed but its matching
service's own last result is a failure — so a nightly check that was killed
(OOM, timeout) shows red even when the timer itself is armed.
Fix: `systemctl --user start <timer>` (or `sudo systemctl start <timer>`
for a system-scope one).

**basket-doctor** — `basket doctor`'s own PASS/WARN/FAIL lines (swap,
pcscd, age-plugin, kvm, vsock, stale mounts — see
`docs/runbooks/*basket*` or Phase 3's acceptance drill). Red means at
least one FAIL; fix whatever `basket doctor` names, then re-run it
yourself to confirm before trusting the tile again.

**broker** — allow/deny counts and the top 5 denied hosts per egress-broker
instance, over the last 24 hours. This tile is informational — it does not
turn red on denies (a deny is often the broker doing its job). **Green with
the 24 h allow/deny counts is the normal reading** now that the `openrouter`
instance exists. **Grey means Helm could not read the instance's
`audit.jsonl`** (permissions, or a fresh instance with no traffic yet) — it
is a fault, not "nothing to check".

**gpu** — `nvidia-smi`'s own numbers: utilisation, memory, temperature,
power draw. Amber at ≥85 °C or ≥95% memory used. Grey if `nvidia-smi`
itself fails (driver issue, or you're not near the GPU host).

**host** — load average, memory, disk free on `/`, and whether any swap
device is active (an invariant this environment relies on — see Phase 3).
Red on <5% disk free or any swap present; amber on 5-15% disk free. Fix
disk pressure with `nix-collect-garbage` (see the flake-check note below
first) or investigate why swap turned on.

**drift** — whether the live system matches this repo's `HEAD`, and
whether either the live system or the working tree is dirty. Green: live
equals `HEAD`, nothing dirty. Green also when `HEAD` is ahead of the live
system only in `docs/` or `*.md` files: a switch would activate the same
system. Amber: they match but something's dirty (switched from an uncommitted
tree, or the tree has uncommitted changes since). Red: the live system is
running a different revision than `HEAD` — you have unswitched changes, or
you switched to something you haven't pushed to `HEAD` yet. Fix by
committing/switching so the two line up, or by treating it as an intentional
lag if you know why.

**flake-check** — the newest recorded full `nix flake check` observation
(`helm-flake-check.timer` records its nightly run at 03:00; the seat
integrator and the factory verifier also record checks). Green: a recorded
full flake check covers a revision that differs from `HEAD` only in docs (or
equals `HEAD`), and is recent. Amber: the check covers the live system but
not `HEAD` — so `HEAD` is unchecked — or the covering check is older than
48 h. Red: the newest covering check failed, or nothing has ever been
recorded and the nightly `flake-check.json` file is also missing. Run
`systemctl --user start helm-flake-check.service` once to force a fresh
covering check sooner than the nightly timer. Expand the tile's detail to
see the last 40 lines of output.

## Why the nightly flake check can go red after `nix-collect-garbage`

The nightly check runs `--offline`: it refuses to fetch anything from the
network, including from the binary cache. If you've recently run
`nix-collect-garbage` and something the check needs (a store path that
wasn't kept alive by a live `nixosConfiguration.core` or a GC root) got
swept, the offline check fails to substitute it and the tile turns red with
a real error in its detail, even though nothing about the repo itself is
broken. That's expected, not a bug: run the check again without `--offline`
by hand (`nix flake check --no-update-lock-file`) once you have a moment
and are back online, to re-populate the store, then let tomorrow's offline
run go green on its own. If it stays red after that, treat it like any
other `nix flake check` failure.

## Acceptance drill

    nix develop -c tests/acceptance/helm.sh

Proves: the page loads and says "Helm"; `helm-status` exits 0 and lists all
nine tiles; `helm-collect.timer` is active; the port is reachable on
127.0.0.1 only (not on any other interface); and — the negative proof —
stopping `proton-drive-push.timer` and running a fresh collection turns the
**timers** tile red, restarting the timer and collecting again turns it
green. No `sudo`: everything the script does is a user-scope systemd action
or a read against the already-running system. It leaves
`proton-drive-push.timer` running when it's done.
