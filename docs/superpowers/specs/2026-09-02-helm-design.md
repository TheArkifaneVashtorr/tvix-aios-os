# Helm — status dashboard (design, 2026-09-02, rev 2)

**Decision basis:** operator chose "localhost static status page" (2026-09-02
evening). Research: docs/research-2026-09-02-helm-dashboard.md. Rev 2 folds
in the adversarial review (9 Sonnet reviewers, 2026-09-02 evening): drift
algorithm, offline flake check, scoped timer audit, file modes, escaping.
Absorbs concepts 2026-09-02j (backup parity self-test) and 2026-09-02k
(post-switch activation audit); 2026-09-02h (proving grounds tile) lands later.

## Goal

One page on the host that answers "is the environment healthy right now"
without running any acceptance script: backups, invariants, broker traffic,
GPU, disk, and whether the live system is behind the repo. Helm itself makes
no outbound network call; its optional nightly flake check runs with
`--offline` so it cannot either. Loopback only — unreachable off the host.
Nothing runs as root.

## Non-goals (v0)

LAN access, authentication, history/graphs, alerts, JavaScript. Phase 10
adds LAN + WebAuthn.

## Architecture

Two user-scoped systemd units declared by a NixOS module, plus the pinned
static-web-server system service:

1. `helm-collect.timer` / `.service` (user units, `ConditionUser=
   <operatorUser>`, `OnUnitActiveSec=<interval>`, default 5 min): runs
   `helm-collect`, which writes `/var/lib/helm/status.json` and
   `/var/lib/helm/index.html` atomically (tmp + rename). Runs as the
   operator because the restic repository, the restic password file and
   the user journal belong to that user.
2. `helm-flake-check.timer` / `.service` (user units, daily 03:00,
   `flakeCheck.enable` default true): runs `nix flake check --offline
   --no-update-lock-file` in `repo` and writes `/var/lib/helm/flake-check.json`
   = `{rev, ok, exit, started, duration_s, log_tail}` (last 40 lines of
   output). An offline failure (missing store paths) is recorded as
   `ok=false` with the log tail — the tile turns red and says why; the
   timer keeps running. Separate from collect so a slow check never delays
   tiles.
3. `services.static-web-server` (system unit at the pin: options `listen`,
   `root`, `configuration`; socket-activated; hardened with DynamicUser,
   ProtectSystem=strict, BindReadOnlyPaths=root — cited from
   nixos/modules/services/web-servers/static-web-server.nix at ac62194c):
   `listen = "127.0.0.1:<port>"`, `root = "/var/lib/helm"`, plus
   `SupplementaryGroups = [ "helm" ]` so it can read the group-readable
   files. The module asserts at eval time that `listen` starts with
   `127.0.0.1:` or `[::1]:`.

File modes: group `helm` (system group); `/var/lib/helm` `0750
<operatorUser>:helm` (tmpfiles); `status.json`, `index.html`,
`flake-check.json` written `0640`; `/etc/helm/config.json` `0640 root:helm`
(the operator is added to `helm`). No local UID outside the group can read
broker instance names, paths or audit summaries.

Why `/var/lib/helm` and not `~/.local/state`: the pinned module sets
`ProtectHome=tmpfs` when `root` is under /home.

Both user units carry `NoNewPrivileges=true`, `ProtectSystem=strict`,
`ProtectHome=read-only` (collect needs `~/.config/restic/password` read
only), `ReadWritePaths=/var/lib/helm`, `PrivateTmp=true`,
`CapabilityBoundingSet=`, `Nice=10`, `TimeoutStartSec=5min` (collect) /
`2h` (flake check).

## Components

`pkgs/helm/collect.py` — Python 3 stdlib only (`json`, `subprocess`,
`pathlib`, `datetime`, `html`, `argparse`, `re`). CLI: `helm-collect [--out
DIR] [--config FILE] [--print]`. `--print` renders the tiles as text to
stdout (`helm-status` in the devShell and systemPackages is this).
`--config` is the JSON the module generates (below), so the script has no
hard-coded paths. Rendering lives in the same file (one module, one test
file).

One function per tile, each returning `{"name", "status":
"ok"|"warn"|"fail"|"unknown", "summary", "detail": {...}, "checked_at"}`.
Every collector is wrapped: a missing binary, a timeout (10 s default, 60 s
for restic, 20 s for `basket doctor`) or a parse error yields `unknown`
with the exception text in `detail`, never a crash. A *semantic* non-zero
exit that the tile understands (see drift, doctor) maps to that tile's own
rule, not to `unknown`. Subprocesses use explicit argv, no shell.

**Every string that reaches the page — summaries, detail values, host
names from audit lines, journal MESSAGE text, doctor output — passes
through `html.escape(s, quote=True)` at render time.** Audit `host`/`sni`
values are attacker-influenced (client-supplied SNI); the test suite has an
adversarial fixture (`<script>` and `"` in a denied host name) and asserts
the rendered page contains the escaped form only.

Tiles (v0), status rule in brackets:

| tile | source | ok / warn / fail |
|---|---|---|
| backup: local snapshot | `restic snapshots --json --latest 1` with `RESTIC_REPOSITORY`, `RESTIC_PASSWORD_FILE` from config | age < 26 h / < 50 h / else or no snapshot |
| backup: Proton parity | last MESSAGE matching `^proton-backup-push: (OK\|FAIL) .*` from `journalctl --user -u proton-drive-push -o json` (`__REALTIME_TIMESTAMP` µs) | OK and age < 26 h / OK but older / FAIL or none |
| timers armed | each timer in `timers.system` via `systemctl show -p ActiveState,NextElapseUSecRealtime,NextElapseUSecMonotonic <t>`, each in `timers.user` via `systemctl --user show …` | all `active` with a non-empty `NextElapseUSecRealtime` or a non-empty, non-zero `NextElapseUSecMonotonic` (monotonic timers such as `OnUnitActiveSec=` never populate the realtime field) / — / any other |
| basket doctor | `basket doctor` (package path from config); parse `^(PASS\|WARN\|FAIL)\s+(\S+)\s*(.*)$`; exit 1 is expected when any FAIL | no FAIL, no WARN / any WARN / any FAIL, or exit ≠ 0 with no parsable line |
| egress broker | per instance `audit.jsonl` (path from config), lines with `ts` in the last 24 h: allow/deny counts, top 5 denied hosts | informational: `ok`; `unknown` if unreadable |
| GPU | `nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw --format=csv,noheader,nounits` | ok / temp ≥ 85 °C or mem ≥ 95 % / nvidia-smi fails |
| host | `/proc/loadavg`, `/proc/meminfo`, `os.statvfs("/")`, `/proc/swaps` | disk ≥ 15 % free and no swap / disk 5–15 % / disk < 5 % or any swap device (brief invariant) |
| drift | see algorithm below | equal, clean / dirty / behind or unknown |
| flake check | `/var/lib/helm/flake-check.json` | `ok` and `rev` == repo HEAD and age < 26 h / `ok` but stale or rev ≠ HEAD / `ok=false` or file missing |

Drift algorithm (exact):

1. `live = nixos-version --configuration-revision`. Exit ≠ 0 (the pinned
   script prints "configuration revision is unknown" to stderr and exits 1
   when `system.configurationRevision` is unset) → `fail`, summary "live
   system has no configuration revision — set system.configurationRevision".
2. `dirty_live = live.endswith("-dirty") or live == "dirty"`; `base =
   live.removesuffix("-dirty")`.
3. `head = git -C <repo> rev-parse HEAD`; `tree_dirty = git -C <repo>
   status --porcelain` non-empty. Git failure → `unknown`.
4. `base == head` and not `dirty_live` and not `tree_dirty` → `ok`
   ("live = HEAD <short>").
   `base == head` and (`dirty_live` or `tree_dirty`) → `warn` ("switched
   from a dirty tree" / "working tree has uncommitted changes").
   `live == "dirty"` (no rev at all) → `warn` ("switched from a tree with
   no commit").
   else → `fail` ("live <short-base> ≠ HEAD <short-head>").

hosts/core sets `system.configurationRevision = self.rev or self.dirtyRev
or "dirty"` in `nixosConfigurations.core`. The VM test sets a fixed value.

Page: one `<html>` with inline `<style>`, `<meta http-equiv="refresh"
content="60">`, `prefers-color-scheme` light/dark, header "Helm ·
<hostname> · generated <time> · next <time>", a grid of tiles coloured by
status, each with its summary and a `<details>` holding the escaped detail
JSON. No `<script>`, no external `href`/`src` (test enforces: the document
contains no `<script`, no `src=`, no `href="http`). If `status.json` is
older than 2 × interval the header turns amber ("collector stale").

## Configuration (NixOS module `services.helm`)

`enable`; `operatorUser` (default "dalhaka"); `port` (default 7700);
`listen` (default "127.0.0.1:${port}", asserted loopback); `interval`
(default "5min"); `repo` (default "/home/${operatorUser}/nixos-agent-env");
`restic.repository` ("/var/lib/restic/core"), `restic.passwordFile`
("/home/${operatorUser}/.config/restic/password"); `flakeCheck.enable`
(true), `flakeCheck.onCalendar` ("*-*-* 03:00:00"); `basketPackage`;
`brokerAuditPaths` (default derived from
`config.services.egress-broker.instances` names →
`/var/lib/egress-broker/<name>/audit.jsonl`); `timers.system` (default
`[ "restic-backups-core-local.timer" ]` when `services.proton-backup` is
enabled, else `[]`) and `timers.user` (default `[ "proton-drive-push.timer"
"helm-collect.timer" "helm-flake-check.timer" ]`, the last only when
`flakeCheck.enable`). The defaults are named lists on purpose: auditing
every declared timer would make `fstrim`, `nix-gc` and the like block the
tile. Adding a timer to the environment means adding it here — the
concept-2026-09-02k ideal (derive from declarations) is deferred until the
modules that own timers export them.

The module writes the resolved values to `/etc/helm/config.json` (mode
0640 root:helm, no secrets — the password file is referenced by path only)
and registers itself as `nixosModules.helm` in flake.nix; `nixosConfigurations.
core` adds `self.nixosModules.helm` to its module list (the same pattern as
egressBroker/basketStore/cowork/protonBackup — the module is *not* wired
through hosts/core/default.nix imports). hosts/core: `services.helm.enable
= true;` plus `system.configurationRevision`; `helm-status` in
`environment.systemPackages`.

## Data flow

timer → collect.py reads sources → status.json (tmp+rename) → render →
index.html (tmp+rename) → static-web-server serves both on
127.0.0.1:7700 → operator opens **http://localhost:7700** in the hardened
Firefox. hosts/core/firefox.nix has `HttpsOnlyMode = "enabled"`; Firefox
exempts loopback from upgrades by default and the plan additionally pins
the preference `dom.security.https_only_mode.upgrade_local = false` in
firefox.nix (documenting the default); the runbook uses the `localhost`
form. The acceptance script opens the page for real.

## Error handling

Collector failures are per-tile (`unknown`), never page-wide. If rendering
itself fails, the previous index.html stays in place (rename is atomic)
and the journal gets the traceback. The flake-check unit records a
non-zero exit as `ok=false` rather than failing the unit.

## Security

Loopback only (asserted at build time): unreachable from the LAN or the
internet. Within the host, file modes are the only confidentiality
boundary, and they gate *filesystem* access, not the page: `status.json`
and the generated HTML are group-readable by `helm` only (or, where a file
holds paths and no secrets, world-readable — `/etc/helm/config.json`), but
static-web-server itself serves both the page and `status.json` over
127.0.0.1:7700 to **any local process, of any UID, with no authentication**
— a mode of 0640 restricts who can `cat` the file directly, not who can
`curl` it through the server. Authentication for the page itself arrives
with the LAN portal phase (Phase 10). The restic cache directory
(`/var/lib/helm-cache`) lives outside the served document root, so it is
never reachable over HTTP regardless of its own mode. No secrets in
status.json (restic reads the password, Helm never does); audit lines are
summarised (hosts and counts only) and escaped. Page has no scripts and no
external references (tested). The flake check runs offline. User units are
hardened as listed. Nothing runs as root.

## Testing

- `tests/helm/test_collect.py` (pytest, `checks.helm-unit`): fixtures with
  canned `restic snapshots --json`, journal JSON lines (OK / FAIL / none),
  `systemctl show` output (active+next / inactive), `basket doctor` text
  (PASS / WARN / FAIL / exit 1 with no output), audit.jsonl (allow / deny /
  out-of-window / adversarial host string), nvidia-smi CSV, missing binary
  → `unknown`, drift (all branches of the algorithm incl. exit-1 and
  `-dirty`), flake-check fresh / stale / behind / missing; render test:
  every tile name present, status class present, no `<script`, no `src=`,
  no `href="http`, adversarial string appears escaped; staleness test.
- `checks.helm-eval`: the module evaluates on the repo's standard eval
  harness (the stub used by `checks.cowork-eval`) with defaults;
  `checks.helm-assertion-negative` (custom output): `listen =
  "0.0.0.0:7700"` fails with the loopback message.
- `checks.helm-vm` (NixOS VM): `services.helm.enable`, a fake operator
  user, `system.configurationRevision = "deadbeef"`, no restic/nvidia;
  runs `helm-collect.service` as that user; asserts `curl
  127.0.0.1:7700/` is 200 with "Helm" in the body, `status.json` has every
  tile, `ss -ltn` shows the port only on 127.0.0.1, the page has no
  `<script`, `/var/lib/helm/status.json` is mode 0640 and unreadable by an
  unrelated user (`su nobody -s /bin/sh -c cat` fails).
- Operator acceptance `tests/acceptance/helm.sh`: page loads at
  http://localhost:7700 in Firefox (operator judgment), backup tiles green
  the morning after a real nightly run, "timers armed" green, drift tile
  green right after a switch, `helm-status` prints the same verdicts.
  Negative proof: `systemctl --user stop proton-drive-push.timer` → within
  one interval "timers armed" is red → start it → green.

## Lint

Python: ruff (existing gate); add `pkgs/helm` and `tests/helm` to the ruff
paths in the flake's lint check and githooks/pre-commit.

## Verify-first items for the plan

1. `journalctl --user -o json` field names as used above (MESSAGE,
   `__REALTIME_TIMESTAMP`) — confirmed by research; re-check in the VM.
2. `SupplementaryGroups` on the pinned static-web-server unit composes
   with its `DynamicUser=true` (expected yes).
3. `dom.security.https_only_mode.upgrade_local` is accepted by the Firefox
   policy `Preferences` block at the pinned Firefox version.

## Later

Proving-grounds matrix tile; broker deny summary written by a local model
(Phase 5); LAN + WebAuthn (Phase 10); deriving `timers.*` from the owning
modules; history if ever wanted.
