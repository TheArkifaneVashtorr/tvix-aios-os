# Helm v1 — the switch page

Helm's page at **http://localhost:7700** still opens with the nine health
tiles you know from `docs/runbooks/helm.md` — and above them now sits one
live section: **Profile**. The page is read-only: it shows which profile is
running, it does not switch anything itself. The switch moved behind the
desktop password — it happens in a terminal (and, when Helm Home ships, in
Helm Home), not by clicking the page.

> **Note (2026-09-04):** the **Workspaces** section and its "Open" buttons
> have been removed from the live page by operator decision until Helm Home
> ships (`docs/superpowers/specs/2026-09-04-helm-home-design.md`). `core`
> declares an empty workspace map, so the page renders no Workspaces section
> at all. The module capability — `services.helm.control.workspaces`, the
> `helm-open-workspace` launcher, and their tests — is untouched and can be
> re-declared when that work lands.

The mental model, once, because it makes everything else make sense:
**now, not forever.** A switch changes the *running* machine in
seconds-to-a-minute. A reboot always lands back on `base`. Nothing here
touches the boot menu; and the switch now also asks for your password, so
the page can tell you what is running without ever being able to change it.

## First start after the enabling switch

Two things to know the first time `services.helm.control` goes live (it
replaces the old static file server on `:7700`):

1. A switch does not *start* a newly enabled **user** unit in a session
   that was already logged in. After the switch that enables Helm v1,
   start the server by hand once (or log out and back in):

       systemctl --user start helm-serve.service

2. The page is briefly down between the old `static-web-server` stopping
   and `helm-serve` starting — a moment, not an outage. From the next
   login on, `helm-serve` starts on its own.

## What the page shows

The **Profile** section sits under the header and shows three things,
re-read from the live system every time the page is served (nothing is
cached):

- **`● <profile> — active`** — the profile the running system is on, read
  from `/etc/helm/profile`. After a reboot it reads `base` (the boot
  default, shown neutrally — a promise kept, not state lost).
- **one plain line per profile** — the declared profiles (base, gaming,
  …), the active one marked `● active`.
- **the last switch** — `Last switch: base → gaming · ok · 21:03`, or
  `failed — see journal`, or `No switches since boot.`. This is rendered
  from the same journal lines the `helm-switch@` units write, so the page
  and `journalctl` should never disagree.

There is no form, no button, no token, and no script on the page. The
`/control.json` route serves the same live state as JSON
(`active_profile`, `last_switch`, `switching`, `now`) for Helm Home to
consume; `/status.json` is the collector's document.

## The switch, until Helm Home lands

The page is read-only, so the switch is a terminal line (or the same call
Helm Home will make). It runs as you, and the system asks for your password:

    systemctl start helm-switch@<profile>.service

`helm-switch@<profile>.service` runs `switch-to-configuration test` against
the chosen profile and nothing else. The password prompt is the desktop's
own (polkit `auth_admin_keep`): a repeat start inside the grace window does
not ask again. A switch to the profile you are *already on* re-runs the same
`test` and changes nothing — the page shows that profile as `● active`.

Watch the result in the journal:

    journalctl -u helm-switch@gaming.service

`helm-switch: begin`/`end` pairs tell you what ran; `end exit=` non-zero is
the activation's own refusal (an evaluation error lands here too — the
machine cannot switch to a profile that doesn't build).

## What the page never does

- **It never changes the boot menu.** The switch runs
  `switch-to-configuration` with the `test` action — activate and restart
  changed units, bootloader untouched — so an unattended reboot always
  comes back up in `base`.
- **It never switches anything itself.** The page has no form and no
  token; it only reports. The switch is the terminal line above, behind
  the password.
- **It never restarts the agent, broker, basket or backup services.** A
  build-time assertion ("profiles never touch agent units") fails the
  *build* if any future profile ever changes a unit in those namespaces —
  Helm's timers, restic, the egress broker, the lane, nothing a switch
  touches. The acceptance drill re-proves it live across every switch it
  runs (no agent unit restarted, in both the system and your user
  manager).

## Two clocks, on purpose

The Profile section is read live when the page is served. The health tiles
are collected every five minutes; the header shows when. After a switch,
believe `/control.json` and the Profile section immediately; the tiles catch
up on the next collection.

And one standing rule about trust:

> If the page and `journalctl` ever disagree about a switch, believe the
> journal — and file it, because that is a bug.

The page's "last switch" line is rendered from the same journal lines the
`helm-switch@` units write (`helm-switch: begin/end`), so they should never
disagree; the acceptance drill checks that the marker, `/control.json` and
the journal all tell the same story, and that every switch closed its
journal pair. The dashboard is the safety case for the switch, and the
journal is the court of appeal.

## If something goes wrong

- **`systemctl start helm-switch@…` asks for the password in a context
  where none can be given** (a script, cron, a session-less shell): the
  refusal is systemd's — "requires interactive authentication". Run it from
  your desktop terminal instead; the password prompt is what authorizes the
  switch.
- **A switch failed**: `journalctl -u helm-switch@gaming.service` is the
  whole diagnosis. `helm-switch: begin`/`end` pairs tell you what ran;
  `end exit=` non-zero is the activation's own refusal.
- **The page itself is gone** (`:7700` refuses): `systemctl --user status
  helm-serve` — after a reboot it starts on login; after the first
  enabling switch it needs the manual start above.

## The honest limits (the password, not a token)

The page no longer carries a token or a form, and the switch is the
`systemctl start helm-switch@<profile>.service` line behind the desktop
password (polkit `auth_admin_keep`). The password is **not** a change in
the blast radius: anything that runs as you — the DeepSeek seat, the
desktop app's Claude Code — could switch the machine the same way if it
asked for (and was granted) the password; the boundary was never the token,
it was always what those units can do. Blast radius of a switch: "the listed
profile switches" — not "your processes" — because of the allowlisted,
fixed set of profiles, the `test` action only, and the agent-unit assertion
above. That is accepted for a single-seat, loopback-only page; LAN and
stronger, per-action authentication are a later phase's work.

## Acceptance drill

    cd ~/nixos-agent-env && nix develop -c tests/acceptance/helm-v1.sh

Run it after the enabling switch and the manual `helm-serve` start above,
from a live desktop session. It proves, in order: the page serves the
Profile section with `base — active`, no form and no token; the
password-gated switch to `gaming` (the script prints the
`systemctl start helm-switch@gaming.service` line, waits for Enter, then
checks the marker flips and Steam arrives on the system path within a
minute) and back to `base` (Steam gone); the dashboard under the switch
stays green; a **real Firefox load** of the page shows `base — active` with
no form; and across every switch the boot default is unchanged, no
agent-prefixed unit restarted (system or user manager), every switch closed
its journal begin/end pair.

Four steps print **SKIP**, deliberately, and a SKIP is not a failure and
not a silent pass — it is a step whose precondition does not exist yet:
the Open step and its open-audit (no workspaces declared while the page is
read-only), the `media` round trip (until wiring round 2 creates the media
specialisation), and the cowork broker audit (cowork is parked off; the
drill watches `restic-backups-core-local` and the whole agent-prefix
namespace in its place). When Helm Home (or wiring round 2) re-declares
workspaces and media, the same script runs those steps without an edit.

No `sudo`: everything the drill does is a loopback request, a user-scope
systemd action run by the operator in the session, or a read against the
running system. It leaves the machine on `base`.