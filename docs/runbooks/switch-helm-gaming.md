# The switch — Helm v0 fixes + the gaming profile + the OpenRouter lane

Wiring round 1 (`docs/superpowers/plans/2026-09-02-host-wiring.md`) plus the
pre-switch fix round (`docs/superpowers/plans/2026-09-03-preswitch-fixes.md`)
land as one operator switch. After it, Helm's drift/GPU tiles work, restic
has a writable cache outside the served page root, the config file it reads
is readable in the session you're already in, and `core` has a `gaming`
specialisation. Helm v1 (the click-to-switch page) doesn't exist yet — until
it does, you enter and leave the gaming profile by hand with
`switch-to-configuration test`.

The board (`docs/OPERATIONS.md`) pulled Lane L tasks T2 and T3 — the
`openrouter` broker instance and the `lane-submit`/`lane-wait`/`lane-run`
client — forward into this same switch (operator: "we are kinda forced").
This switch starts the lane's two broker units on its own — same as Helm's
timers, whether or not you ever submit a job — `egress-netns-openrouter.
service` and `egress-broker-openrouter.service`; the per-job template unit,
`lane-openrouter@.service`, is `wantedBy` nothing, so **no lane job runs
until you submit one**. §7 below covers that piece in full; everything else
in this runbook is unchanged by its presence. See `docs/runbooks/lanes.md`
for what a lane is, the key file, and how to submit a job — this section
only covers what to check right after the switch.

## 1. Before you switch

    cd ~/nixos-agent-env && git status --short

Must print nothing. A dirty tree gets baked into the build as a `-dirty`
revision, and the **drift** tile reads amber for it even though nothing is
actually behind — commit or stash first.

    readlink /nix/var/nix/profiles/system

Write the number down. That is today's generation — the one you'd roll back
*to* if anything looks wrong (see §6, Rollback).

## 2. The one switch

    sudo nixos-rebuild switch --flake ~/nixos-agent-env#core

This installs the base profile (unchanged behaviour, plus the Helm gate
fixes) *and* builds the `gaming` specialisation alongside it — one switch
covers both. `/etc/helm/profile` should now read `base`.

## 3. Helm drill

A switch installs and enables Helm's user timers but does not *start* one
newly enabled inside a session that was already logged in (the same gap
concept `2026-09-02k` found for `proton-drive-push.timer`) — start them by
hand once:

    systemctl --user start helm-collect.timer helm-flake-check.timer

The page 404s until the first collection has run, so collect once
synchronously and confirm the file landed before opening a browser:

    systemctl --user start helm-collect.service && ls -l /var/lib/helm/index.html

Now open **http://localhost:7700** — the page should load and list nine
tiles. Then run the acceptance script:

    cd ~/nixos-agent-env && nix develop -c tests/acceptance/helm.sh

**Expected tiles right after this switch** (see "What `helm-status` shows"
below for why):

- **flake-check** — **amber until a covering check is recorded**. No full
  `nix flake check` observation covers this revision yet, so the tile reads
  amber — not red — and clears once tonight's run (or a hand run:
  `systemctl --user start helm-flake-check.service`, a couple of minutes)
  records a covering check.
- **broker** — **green**, with the 24 h allow/deny counts, now that the
  `openrouter` instance is live to audit.
- **backup-snapshot** — **green**. Restic is read with `--no-lock`, so the
  read-only sandbox `helm-collect.service` runs in no longer blocks it.
- **drift** — **green**, assuming step 1's tree was clean: the live
  revision (`self.rev`) matches `git rev-parse HEAD`.

See `docs/runbooks/helm.md` for what every tile means and what to do on red
for any of the other five.

## 4. Entering the gaming profile by hand

Helm v1 will make this a click on the page
(`docs/superpowers/specs/2026-09-02-helm-v1-switch-design.md`); until it
lands, run the specialisation's own `switch-to-configuration` with the
`test` action — it activates and restarts changed units but **never
touches the bootloader**, so an unattended reboot always comes back up in
`base`:

    sudo /run/current-system/specialisation/gaming/bin/switch-to-configuration test

Confirm the profile flipped:

    cat /etc/helm/profile          # -> gaming

`gamemoded.service` is a user unit `programs.gaming` enables but a `test`
activation does not start on its own (same class of gap as Helm's timers in
§3) — start it once per session before you rely on gamemode:

    systemctl --user start gamemoded.service

## 5. Gaming drill

Run from the gaming flake's own repo (it has its own devShell):

    cd ~/flakes/gaming && nix develop -c tests/acceptance/gaming.sh

This is the operator-judged drill from `~/flakes/gaming`'s own README:
Steam launches, a Proton-GE compatibility tool is selectable, and the
gamescope smoke test (`gamescope -- glxgears`) runs without a coredump —
see that repo's runbook for the NVIDIA/gamescope caveat before relying on
it daily.

## 6. Leaving the gaming profile

Quit Steam and every game first — leaving the profile removes
`/run/opengl-driver-32`, and anything still holding the 32-bit driver open
will crash or hang rather than exit cleanly.

Same mechanism, run against the **base** toplevel's own script:

    sudo /nix/var/nix/profiles/system/bin/switch-to-configuration test

    cat /etc/helm/profile          # -> base

Entering or leaving gaming only restarts units whose generated text differs
between the two profiles. This isn't a promise read off `hosts/core/gaming.nix`
touching `programs.gaming` alone — it's a fact the pre-switch audit measured
directly: it diffed the actual activation output of the two built profiles
(concept `2026-09-03a`) and found no unit named `egress-*`, `cowork*`,
`basket*`, `restic-*` or `helm-*` differs between `base` and `gaming` — so
neither direction touches Helm's timers, the restic units, or the broker.
Helm v1 turns that measurement into a standing guarantee: its
"profiles never touch agent units" eval-time assertion
(`docs/superpowers/specs/2026-09-02-helm-v1-switch-design.md`) will fail the
build if a future profile ever adds a unit in one of those namespaces.

## 7. The OpenRouter lane

Two units come up on their own with this switch, same as Helm's timers,
whether or not you ever submit a job: `egress-netns-openrouter.service`
and `egress-broker-openrouter.service`, both `wantedBy multi-user.target`
(`nixosModules/egressBroker.nix`). They exist because `hosts/core/lanes.nix`
sets `services.model-lanes.openrouter` — that's a NixOS *option*, not a
unit; it never shows up in `systemctl`. The lane module
(`nixosModules/modelLane.nix`) reads it to render the broker instance
below and the per-job template unit further down. Confirm the two real
units:

    systemctl status egress-netns-openrouter egress-broker-openrouter

Both should read **active**: `egress-netns-openrouter.service` (the
persistent named netns, `/run/netns/egress-openrouter`) and
`egress-broker-openrouter.service` (the mitmproxy instance listening on
`10.100.3.1:3131` inside it, allowlisting only `openrouter.ai`). The
per-job template unit, `lane-openrouter@.service`, is **not** meant to be
active here — it's a oneshot, per job (`lane-openrouter@<job-id>.service`),
`wantedBy` nothing, started only when `lane-submit` runs `systemctl start`
on one instance, gated by the polkit rule the module renders.

Then run one real job — the first request this lane has ever made:

    echo '[{"role":"user","content":"Reply with the single word OK."}]' \
      | lane-submit openrouter --kind chat --class permitted \
          --model deepseek/deepseek-v4-flash

This prints a job id and blocks until the unit finishes (`lane-submit`
runs `systemctl start` on the oneshot, which waits for it). Then:

    lane-wait openrouter <id>

should print a result with `"output": "OK"` (or close to it — a model is
not a compiler) and exit 0. If it instead prints an `error` key, do **not**
treat this as a Tier B success under any of the job templates in
`tools/lane/jobs/` — see `docs/runbooks/lanes.md`'s shadow-period section
before trusting or reusing anything this lane returns.

**What the closure diff shows for the lane** (compare against the
pre-switch closure diff the audit already ran, `docs/OPERATIONS.md`
Pre-switch audit section): a new mitmproxy instance unit pair (`egress-
netns-openrouter.service`, `egress-broker-openrouter.service`) alongside
the veth pair `veb-openrouter`/`ven-openrouter` and the nftables rule that
makes the broker the lane's only route out; the `lane-run` and `lane-
submit`/`lane-wait` packages (`pkgs/lane/lane-run.nix`, wrapping `pkgs/
lane/lane-run.py` and `pkgs/lane/lane-submit.py`) newly present in
`environment.systemPackages`; the `lane-openrouter@.service` template
unit; the `lane` group and its polkit rule; and the tmpfiles lines for
`/var/lib/secrets/openrouter-key` (reset to `0440 root:egress-broker`) and
`/var/lib/lanes/openrouter/{,jobs,results}` (`2770 root lane`). Nothing
here touches an existing Helm, restic, or gaming unit — same "closure diff
proves the change is only what you meant" discipline as §1's
`nix store diff-closures`.

**The firewall backend changes underneath this, too.** Declaring a broker
instance sets `networking.nftables.enable = true`
(`nixosModules/egressBroker.nix`) — the same thing generations ≤ 21 had
while the Cowork broker was live, and the same thing gen 22 lost when
Cowork was parked (`nftables.enable` is gated on
`services.egress-broker.instances != {}`, and Cowork's own instance is
`mkIf cfg.enable`, so with Cowork off there was nothing to turn it back
on until this lane). NixOS's `networking.firewall` module is implemented
either way, so this switch replaces `firewall.service` (iptables backend)
with `nftables.service`, same rules, one brief restart during activation
— not a new capability, a different backend for the one that was already
there. The closure diff confirms it: `firewall: ε → ∅` (the unit is gone),
`nftables*: ∅ → ε` (`nftables.service` plus its `.socket`/timer arrive),
`iptables: -94 KiB` (the legacy backend's package drops out of the
closure now that nothing references it). One consequence for §5: the
gaming drill's step 6 (the inbound-exposure check) prefers `nft list
ruleset` over `iptables-save` when `nft` is on `PATH`
(`~/flakes/gaming/tests/acceptance/gaming.sh`) — it fell back to
`iptables-save` on gen 22 because `nft` wasn't there; after this switch it
is, so step 6 reads the ruleset the way it was designed to.

## Rollback

**Never `sudo nixos-rebuild switch --rollback`.** It steps back exactly one
generation, blindly — on this host that can land you on generation 21,
which re-enables Cowork, the broker, and the nftables rules that route
traffic through it. That is not "the previous good state", it's a different
configuration you may not want live.

Instead, switch to the specific generation you wrote down in §1 by running
*that generation's own* `switch-to-configuration` directly:

    sudo /nix/var/nix/profiles/system-<N>-link/bin/switch-to-configuration switch

with `<N>` replaced by the number from §1. This is idempotent and safe to
re-run.

A boot-menu pick of an older generation (instead of the command above) is
**one-shot** — it boots that generation once, but the default boot entry
stays the newest generation, so an unattended reboot after that lands you
back on the generation you were trying to roll back from.

Either way, a rollback does not touch the systemd user session you're
already in: Helm's user timers (`helm-collect.timer`,
`helm-flake-check.timer`) stay loaded and armed until you either stop them
or log out —

    systemctl --user stop helm-collect.timer helm-flake-check.timer

— otherwise Helm keeps collecting and serving a page for units that may no
longer exist on the rolled-back system.

## What `helm-status` shows, before and after

**Before the switch** (today): `nixos-version --configuration-revision`
returns "configuration revision is unknown" — the live system predates
`system.configurationRevision` being set, so the **drift** tile would read
`fail` with that text in its detail if you ran the collector by hand right
now.

**Right after the switch**: the **drift** tile reads `ok` — the live
revision (`self.rev`, baked in at build time) matches `git rev-parse HEAD`
in this repo, and the tree was clean when you built (§1). The **gpu** tile
reports real numbers from its very first collection, never `unknown` for
PATH reasons — this is the first time Helm has run live at all, so there's
no "before" to compare against on this host, but it's the reason the Helm
gate fixes existed: the audit found the user unit's PATH couldn't see
`nixos-version`/`nvidia-smi` at all, which would otherwise have kept both
tiles `unknown` forever. The fix (absolute paths in `/etc/helm/config.json`)
is already baked into what you're switching to.

**While inside the gaming specialisation**: `helm-status` shows the exact
same nine tiles, unchanged. Helm v0 has no profile tile — nothing on the
page or in `helm-status --print` tells you which profile is active; `cat
/etc/helm/profile` is the only way to check until Helm v1 lands. The drift
tile in particular does **not** change when you enter or leave gaming: both
profiles were built from the same flake evaluation, so they carry the
identical `system.configurationRevision`. A drift tile reading `ok` is not
evidence you're in `base` — it only ever compares the *base* system's
baked-in revision against `git rev-parse HEAD`, regardless of which
specialisation's `switch-to-configuration` you last ran.

## Round 2

Media stays deferred (`docs/decisions/2026-09-02-media-nix-native-no-container.md`)
until the nix-native rework lands — it is not part of this switch.
