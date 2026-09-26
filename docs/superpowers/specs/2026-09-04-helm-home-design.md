# Helm Home — design (approved in brainstorm, 2026-09-04; no plan yet)

Sub-project 1 of the operator's vision: **Helm as the home screen** of the
machine, the front end for the whole system, extremely plain. Sub-project 2
(making things from Helm: factories, custom agents and roles) and sub-project 3
(the flake knowledge base with vector search) are deliberately later. The
operator asked for no implementation plan yet: this document records the
design as approved, section by section, so it can be planned when wanted.

## Decisions taken in the brainstorm

- Helm **is the session**: fullscreen after GNOME login, one key brings it
  back over other windows. GNOME stays underneath as the window manager.
- Terminals and journal views render **inside Helm as tiles**; anything that
  cannot be embedded (desktop app, Firefox, ComfyUI's page) opens **over**
  Helm as a normal window (the fallback).
- **Native GNOME app**: Python, GTK4, libadwaita, VTE terminals, the system's
  own password dialog. The existing web page on 7700 remains the phone view
  — read-only once Helm Home lands (no Switch, no token; decision D-H1
  below) — and the collector remains the single data source.
- The home is **a list of names, pick one, a card**. Nothing else on screen.
- A flake **declares itself** (`helm` output): why, created, owner, offers,
  card layout; git supplies the measured facts beside it; a build-time check
  refuses a declaration that claims a profile or program the flake does not
  export.
- Three verbs only, each shown only if offered: **Run** (a program, in a
  terminal tile), **Work here with Claude / with DeepSeek** (a seat with this
  flake as its folder), **Switch** (the flake's NixOS profile becomes the
  running system, after the password dialog).
- "Wire a new flake into the host" is **out**: sub-project 1 only toggles
  services of flakes already wired. New wiring stays a factory job.
- Card text is **agent-written, proposed then accepted**: a refresh button
  submits a confined lane job; the proposal is a diff to the declaration; accept
  commits it. The button shows the last-accepted stamp and a marker when the
  flake's code changed since (HEAD past `writtenAgainst`).
- Nothing in GNOME's settings changes (the raise key is a portal grant the
  operator approves once, D-H3); in NixOS the module is additive — one polkit
  rule and one option — and disabling it returns today's machine (proved by
  the reversibility check, D-H4).

## 1. Pieces

- **`helm` declaration** per flake (Nix attribute set, a flake output):
  `name`, `summary`, `why`, `created`, `owner`, `writtenAgainst`, `state`,
  `updated`, `offers = { profiles, run = [{label, command}], seats }`,
  `card = { blocks = [...]; notes }`. Blocks: `why state do notes cost lastRun
  terminal`.
- **`helm-home`** (package + `services.helm.home` module): one window; left
  the registered flakes (declared in `services.helm.home.flakes`, D-H4; the
  parked `control.workspaces` option is untouched); right the card; top the collector's status strip
  read from `/var/lib/helm/status.json`; bottom a drawer of tiles.
- **Actions**: Switch → the existing `helm-switch@<profile>` allowlisted root
  unit via polkit; Run → VTE tile as the operator; Work-here → Console with
  Claude, or `dsh-openrouter`, in a tile or window.
- **Card refresh**: `lane-submit openrouter --kind chat` with the flake's git
  log, last checks and ledger lines; fixed length caps; proposal shown as a
  diff; accept commits into the flake with a `Generated-By` trailer and
  updates `updated` and `writtenAgainst`.

## 2. Declaration rules

Additive; a flake without one still appears, with a card of proven facts only
and a "write this card" button. `why`/`state` change only by accepted refresh
or by the operator. The build-time check compares `offers` with real outputs
and fails the flake's checks on a mismatch; it is exported from this repo as
`lib.checkHelmDeclaration` and adopted by each declaring flake in its own
checks (D-H2) — the app itself reads declarations at run time.

## 3. Screens

Boot fullscreen, no title bar; one shortcut, granted through GNOME's shortcuts portal at first run, raises it (D-H3; Super+Home is GNOME's own "workspace 1" and is not used). Left column: names, a
coloured dot when something needs the operator. Card: blocks in declared
order; `do` shows only offered buttons; refresh button, stamp and
"changed since" marker top right. Status strip: drift, backup, GPU, seat,
lane, generation, active profile; a click opens the detail as a tile. Drawer:
VTE terminals, journal views, a switch in progress; tiles pop out to windows.
Apply flow for Switch: press → sheet (what changes from the prebuilt closure
diff, last check, rollback target) → system password dialog → progress tile →
new generation, rollback command, audit line. Run and Work-here go straight to
a tile. Refresh: spinner → side-by-side diff → accept/reject.

## 4. Apply path and privilege

As the operator: the app, tiles, Run, Work-here, refresh submission, accept
commit. As root: only `helm-switch@<profile>` as today. Polkit rule changes
from silent allow to `auth_admin_keep` for that action only. Refusals are
inactive buttons with the reason (unknown profile, red checks, dirty tree),
not prompts that fail later. Audit line as today.

## 5. Failure faces

Stale or missing status file → grey strip with its age. Missing flake path →
crossed out with the reason. Failed refresh → card unchanged, job id on the
button. Failed switch → journal tail and a rollback button through the same
prompt. Declaration check red → Switch and Run inactive with the check's
message. Nothing silent.

## 6. Proof

Unit: declaration reader, card model (block order, "changed since",
stamp), apply sheet from a fixture status file, polkit rule rendered
`auth_admin_keep` for exactly the switch action. Eval: declaration check red
on a false offer; host-core asserts autostart, the flakes option and the
polkit change (the key is a portal grant, not a host setting); the
reversibility check (D-H4). VM: GNOME
session, app autostarted, driven through accessibility: pick, Switch, the
dialog appears, the unit starts only after it, audit line; negative: red
checks → inactive Switch. Acceptance drill with three operator-judgment
steps: first thing after login; the raise shortcut over a focused Firefox; refresh proposes and
accept commits.

## Out of scope for sub-project 1

Wiring new flakes into the host; launching factories from a card; custom
agents and roles; the flake knowledge base; a phone version of the home.

## Falsifiable acceptance (when planned)

After one switch: the app is the first window after login; the switch unit
started only after the password dialog (journal order); the audit line names
the profile; a refresh proposal for `media` lands as a commit in
`~/flakes/media` with `writtenAgainst` = its HEAD at accept time; disabling
`services.helm.home` and switching returns the machine to today's state.

## Decisions taken 2026-09-05 (brainstorm, operator approved; each answers a question the environment review raised)

**D-H1 — Switch lives only in the native app, behind the password.** The
polkit rule for `helm-switch@<profile>` changes from `polkit.Result.YES` to
`polkit.Result.AUTH_ADMIN_KEEP` for the start verb alone; the system dialog
appears, and a repeat inside polkit's grace window does not ask again. The web
page on 7700 loses its switch forms and its per-boot token and becomes a
read-only status page, so no process running as the operator — the DeepSeek
seat, the desktop app's Claude Code — can drive a switch through it. The v1
contract line "no prompt for the allowed start" is inverted: the control VM
test proves the refusal without an agent (`systemctl start` reports interactive
authentication required, the unit does not start); the dialog itself is an
operator-judged drill step. Closes claim `uid1000-can-switch-profile` when this
lands; until then the seat guard's tripwire (plan R8) stands. Rejected: a
password everywhere (a phone press would hang the page for six minutes waiting
on a desktop dialog); keeping the page's silent switch (leaves the hole open).

**D-H2 — the checker is exported, declarations are read at run time.** This
repo exports `lib.checkHelmDeclaration :: declaration -> flakeOutputs ->
derivation`, failing when an offered profile, program or seat is not a real
output, with negative fixtures here. Sibling flakes adopt it in their own
`checks`, one reviewed diff each, outside sub-project 1; `~/flakes/dsh-harness`
has no flake and appears as a facts-only card. The app reads a declaration with
`nix eval <path>#helm --json` (about 45 ms for a cached flake) and renders a
flake without one as a facts-only card with a "write this card" button.
Rejected: declarations centralised in `hosts/core` (the flakes would no longer
declare themselves); pinning the siblings as inputs (every sibling commit would
churn this lock, and dsh-harness would first need a flake).

**D-H3 — the raise key comes from GNOME's shortcuts portal first.** The app
requests one shortcut through `org.freedesktop.portal.GlobalShortcuts`
(implemented by `xdg-desktop-portal-gnome` 48 on the host pin); the operator
approves it once in GNOME's own dialog and the grant persists. Nix writes no
GNOME setting. First task of the plan is a measurement on this pin: a
throwaway GTK4 window requests a shortcut through the portal; record whether it
binds and whether the raise wins focus over a focused Firefox. Fallback if
either fails: a declared custom keybinding on Super+Return (unbound today),
and this section is amended to say GNOME changes through one declared setting.
Super+Home is dropped: `gsettings` shows it bound to `switch-to-workspace-1`.
Rejected: a GNOME Shell extension (heaviest, pinned to the exact Shell).

**D-H4 — the home's list is `services.helm.home.flakes`.** One entry per
flake: `path` (absolute), `declaration` (default `"<path>#helm"`), `profile`
(`null` or a member of `services.helm.control.profiles`), `seats` (a subset
of `claude`, `deepseek`). Module assertions for each rule with one negative
check per assertion in the repo's style
(`helm-home-assertion-negative-<rule>`), plus a reversibility check: the
toplevel with `services.helm.home.enable = false` evaluates to the same
derivation as the host without the module. `services.helm.control.workspaces`
stays parked and untouched (decision 2026-09-04). Rejected: extending the
workspaces option (revives what was parked and mixes two models); a file the
app reads (not declared, not checked).

**Unknowns the plan must measure before the GTK work:** the portal's shortcut
grant and focus behaviour (D-H3); driving a GTK4 app over AT-SPI in a NixOS
VM (no VM test here boots a graphical session yet); polkit's fallback to the
display session's agent when a session-less caller asks (documented, not yet
seen on this host).
