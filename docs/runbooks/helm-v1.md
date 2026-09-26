# Helm v1 — the switch page

Helm's page at **http://localhost:7700** still opens with the nine health
tiles you know from `docs/runbooks/helm.md` — and above them now sits one
live section: **Profile**. The page is no longer just a dashboard: you can
click a profile and the machine switches to it at runtime. No password, no
code, loopback only, and still no JavaScript — every button is a plain HTML
form.

> **Note (2026-09-04):** the **Workspaces** section and its "Open" buttons
> have been removed from the live page by operator decision until Helm Home
> ships (`docs/superpowers/specs/2026-09-04-helm-home-design.md`). `core`
> declares an empty workspace map, so the page renders no Workspaces section
> at all. The module capability — `services.helm.control.workspaces`, the
> `helm-open-workspace` launcher, and their tests — is untouched and can be
> re-declared when that work lands.

The mental model, once, because it makes everything else make sense:
**now, not forever.** A click changes the *running* machine in
seconds-to-a-minute. A reboot always lands back on `base`. Nothing here
touches the boot menu; nothing here asks for a password, because the page
can only ever ask for the few things it was built to allow.

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

## What each button does

**A profile button (base, gaming, …)** submits a form to the page's own
server, `helm-serve`, which — as you, through a polkit rule written for
exactly this — starts one allowlisted root unit,
`helm-switch@<name>.service`. That unit runs `switch-to-configuration
test` against the chosen profile and nothing else. Your tab blocks while
it runs (up to a few minutes; the tab's own loading spinner is the
progress signal — there is deliberately no JavaScript spinner). When it
finishes, the page returns with a banner under the header:

- **"Now running: gaming"** — done. The Profile section below the banner
  already shows the new active profile, because it re-reads
  `/etc/helm/profile` when the page is served.
- **"Switch to gaming did not finish — the machine is still on base.
  Details: journalctl -u helm-switch@gaming.service"** — the switch
  failed and the machine is untouched. Run that `journalctl` command; the
  raw story is in the journal.
- **"A switch is already in progress. Wait for it to finish, then
  reload."** — you clicked while a switch was still running (a second
  click while one is in flight gets a polite refusal, not a queue). Wait,
  reload, look again.

The button of the profile you are *already on* is shown disabled with
`● active` — switching to where you are is a no-op, so the page simply
doesn't offer it. (The server still accepts it if asked directly; it
just re-runs the same `test` and changes nothing.)

**An Open button (nixos-agent-env, gaming, media, strategy)** asks
`helm-serve` to open a GNOME Console window on your desktop, detached
from the server, already `cd`' into that workspace's flake directory,
entering its dev shell (when one is declared) and leaving you at an
interactive shell — no `claude` by default. It returns immediately with
"Opening gaming — a terminal window should appear on your desktop." If
the workspace's flake isn't cached, the shell build can take a moment
inside the new window. The window is a normal terminal in your session:
close it like any other. (A workspace that opts in with `command =
"claude"` or `command = "dsh-openrouter"` runs that program instead of
the shell.)

> **Removed 2026-09-04:** these Open buttons (and the whole Workspaces
> section) left the live page until Helm Home ships; `core` now declares
> no workspaces. The paragraphs that follow describe the launcher's
> behaviour — still present in the module and its tests — for when the
> workspaces are re-declared.

**What the Open button never does is mount your data.** If a workspace is
basket-gated and its basket isn't mounted, the terminal opens and prints
the exact `sudo basket mount …` command, then waits for you to press
Enter — the YubiKey ceremony stays yours, in the terminal, in front of
you (today no workspace is basket-gated, so you won't see this yet).

## What the page never does

- **It never changes the boot menu.** Every switch runs
  `switch-to-configuration` with the `test` action — activate and restart
  changed units, bootloader untouched — so an unattended reboot always
  comes back up in `base`, and the page shows that neutrally as
  `base — active`: the system keeping a promise, not losing state.
- **It never mounts baskets.** The launcher only prints the mount
  command and waits; the YubiKey touch is a human ceremony by design.
- **It never restarts the agent, broker, basket or backup services.** A
  build-time assertion ("profiles never touch agent units") fails the
  *build* if any future profile ever changes a unit in those namespaces —
  Helm's timers, restic, the egress broker, the lane, nothing a switch
  touches. The acceptance drill re-proves it live across every switch it
  runs (no agent unit restarted, in both the system and your user
  manager).

## Two clocks, on purpose

The Profile and Workspaces sections are read live when the page is
served. The health tiles are collected every five minutes; the header
shows when. After a switch, believe the banner and the Profile section
immediately; the tiles catch up on the next collection.

And one standing rule about trust:

> If the page and `journalctl` ever disagree about a switch, believe the
> journal — and file it, because that is a bug.

The page's "last switch" line is rendered from the same journal lines the
`helm-switch@` units write (`helm-switch: begin/end`), so they should
never disagree; the acceptance drill checks that the marker, the banner
and `/control.json` all tell the same story, and that every switch closed
its journal pair. The dashboard is the safety case
for the switch, and the journal is the court of appeal.

## If something goes wrong

- **Every button answers "Request rejected — …"** in the real browser: do
  not fix anything by guesswork; this is the one failure mode that only
  a real browser can produce (a header the page's rules require, missing
  or stripped). The acceptance drill's curl steps still working while
  Firefox fails would prove the server side is fine and the browser path
  is what broke — that evidence decides where to look. D5's named
  first-run risk is now explained, and fixed: N2's hardening set
  `Referrer-Policy: no-referrer`, which makes Firefox send `Origin: null`
  on same-origin form POSTs (the Fetch standard governs the Origin header
  by the referrer policy for non-GET requests); the server's origin check
  then, correctly, declined the post as foreign-origin. The server now
  sends `Referrer-Policy: same-origin`, which keeps referrers inside the
  origin and leaves the Origin header intact — `Origin: null` is still
  refused, deliberately, so this exact failure should not recur. If every
  button 403s again while curl works, suspect a *new* header difference,
  not this one.
- **A switch failed**: the banner's `journalctl -u helm-switch@gaming.service`
  line is the whole diagnosis. `helm-switch: begin`/`end` pairs tell you
  what ran; `end exit=` non-zero is the activation's own refusal (an
  evaluation error lands here too — the page cannot switch to a profile
  that doesn't build).
- **The page itself is gone** (`:7700` refuses): `systemctl --user status
  helm-serve` — after a reboot it starts on login; after the first
  enabling switch it needs the manual start above.
- **A terminal window never appeared** when you clicked Open: the spawn
  path (`systemd-run --user` launching GNOME Console) is one of the
  operator-verified parts of the design — if it misbehaves, what you saw
  (window, no window, wrong directory, wrong shell) is exactly the bug
  report to file.

## The honest limits (what the token is and is not)

The page embeds a per-boot token in its forms, and every POST checks it —
but the token is **not** a security boundary between you and anything
else running as your user. Anything already running as you can read the
page (and its token) and can call `systemctl start helm-switch@…` the
same way — polkit would allow it, because it *is* you. The real boundary
is what those units can do: an allowlisted, fixed set of profiles, the
`test` action only, and the agent-unit assertion above. Blast radius of a
leak: "the listed profile switches" — not "your processes". That is
accepted for a single-seat, loopback-only page; LAN and real
authentication are a later phase's work.

## Acceptance drill

    cd ~/nixos-agent-env && nix develop -c tests/acceptance/helm-v1.sh

Run it after the enabling switch and the manual `helm-serve` start above,
from a live desktop session (it opens Firefox). It proves, in order: the
page serves the Profile section with `base` active and one form per
profile (and none per workspace — `core` declares none since the buttons
left the live page, so the drill passes "no workspaces declared" and the
Open step prints SKIP); the
curl-with-token click-equivalents switch to `gaming` (marker flips, Steam
arrives on the system path within a minute) and back to `base` (Steam
gone); the dashboard under the switch stays green; a **real Firefox form
submit** switches the machine (the browser's own headers, the one thing
curl cannot stand in for); and across
every switch the boot default is unchanged, no
agent-prefixed unit restarted (system or user manager), every switch
closed its journal begin/end pair, and the same per-boot token still
serves the page (helm-serve itself was never restarted).

Four steps print **SKIP**, deliberately, and a SKIP is not a failure and
not a silent pass — it is a step whose precondition does not exist yet:
the Open step and its open-audit (no workspaces declared while the
buttons are off the live page), the `media` round trip (until wiring
round 2 creates the media specialisation), and the cowork broker audit
(cowork is parked off; the drill watches `restic-backups-core-local` and
the whole agent-prefix namespace in its place). When Helm Home (or wiring
round 2) re-declares workspaces and media, the same script runs those
steps without an edit.

No `sudo`: everything the drill does is a loopback request, a user-scope
systemd action, or a read against the running system. It leaves the
machine on `base`.
