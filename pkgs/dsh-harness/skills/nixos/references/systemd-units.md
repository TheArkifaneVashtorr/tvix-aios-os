verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Adding a unit, timer, socket, template instance, drop-in, or tmpfiles rule.

## `systemd.services` fields vs raw `serviceConfig`

`systemd.services` gives each named unit typed top-level fields
(`wantedBy`, `after`, `path`, `script`, `restartTriggers`,
`serviceConfig`, …) that generate a unit file; `serviceConfig`/
`unitConfig`/`socketConfig`/`timerConfig` are
each a freeform `attrsOf` — any `[Service]`/`[Unit]`/`[Socket]`/`[Timer]`
key you write passes through verbatim, uncatalogued by the option system
(so a typo there is not a `citations`-checkable option path — verify with
`systemd-analyze verify`, not `nix eval`).

## PATH in units

System and user units run with **no** `PATH` into
`/run/current-system/sw/bin` — that is a shell login-session concern, not
a systemd one. Give a unit its tools with `path = [ pkgs.x ]`, a
`runtimeInputs`-built script (`pkgs.writeShellApplication`), or a full
`/run/current-system/sw/bin/x` literal in `ExecStart`. `path` does
**not** prepend to an existing `$PATH` — the `systemd.services.<name>.environment`
entry `PATH` it sets is assigned outright to `makeBinPath config.path`
(plus each package's `sbin`), and `path` appends `/bin`/`/sbin` to each
entry itself, so a unit that also needs `/run/current-system/sw/bin`
must list `/run/current-system/sw` (not the `bin` dir — that yields the
non-existent `.../sw/bin/bin`) among `path`'s entries. (Stage-2 services
already get a default `path` of coreutils/findutils/gnugrep/gnused/systemd
via `mkAfter`, so the rendered `PATH` is never only what the author wrote.)
**Never** the internal, uncatalogued
_system.path_ attribute (the accumulated `environment.systemPackages` bin
closure, read as _config.system.path_ from a module) from a package that
is itself reachable from `environment.systemPackages` — evaluating it
forces the full `environment.systemPackages` closure, and if anything in
that closure was itself built by interpolating it, the two attributes
wait on each other.

**Right:**

```nix module
{ pkgs, ... }:
{
  systemd.services.example = {
    wantedBy = [ "multi-user.target" ];
    path = [ pkgs.jq ];
    script = "jq --version";
  };
}
```

**Wrong:** a package added to `environment.systemPackages` builds itself
by reading _config.system.path_ — the exact error at this pin:

```text
$ nix eval --impure --expr '(import <nixos-min>) [ ({ config, pkgs, ... }: {
    environment.systemPackages = [
      (pkgs.writeShellScriptBin "example-wrapper" ''
        export PATH=${config.system.path}/bin:$PATH
      '')
    ];
  }) ]'
error: infinite recursion encountered
       at «string»:5:19:
            4|       (pkgs.writeShellScriptBin "example-wrapper" ''
            5|         export PATH=${config.system.path}/bin:$PATH
             |                   ^
```

## User units, `ConditionUser`, linger

`systemd.user.services` are per-user units; `users.users.<name>.linger`
sets one user's linger so their units start at boot instead of at
login (`loginctl enable-linger` declaratively). A switch does **not**
start a newly-enabled _user_ unit in a session that is already logged
in — the user's systemd instance only reloads its unit files, it does not
start what it did not already have wanted; log out/in, `loginctl
enable-linger`, or `systemctl --user daemon-reload && systemctl --user
start <name>` by hand. See gotchas for the general form of this trap; see
activation-and-switch for what a switch actually does to user units
(re-exec, not a diff).

`ConditionUser=` is a `[Unit]` condition checked against the **service
manager's own** uid, not against who the unit's process will run as
(that's `User=`/`DynamicUser`) — it takes a uid, a username, or the
special `@system` (true when the manager's uid falls in the system-user
range). On a system unit this is always true (the system manager only
ever runs as root), so it is meaningless there; on a per-user unit it
answers "is this _my_ user's manager instance" — useful only once
something (a template, a shared drop-in) could otherwise apply across
different users' managers.

## Timers

`systemd.timers.<name>.timerConfig` (freeform) takes `OnCalendar`
(wall-clock, `systemd.time(7)` syntax), `OnBootSec`/`OnStartupSec`/
`OnUnitActiveSec` (monotonic, relative to boot / manager start / the
unit's own last activation), and `Persistent` (fire once, on activation,
if an `OnCalendar` elapse was missed entirely while the system was off —
`systemd.timer(5)` states this applies to `OnCalendar` only, not the
monotonic directives). `systemd.services.<name>.startAt` is shorthand for
an `OnCalendar` timer. Only `OnBootSec`/`OnStartupSec` get the "already
past, fire immediately" behavior on activation (a short boot past a
5-minute `OnBootSec`, say); `OnUnitActiveSec` does not — a timer whose
`OnUnitActiveSec` interval elapsed while the unit or the whole system was
down waits out a fresh interval from activation, it does not catch up.

```nix module
{
  systemd.timers.example = {
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "5m";
      OnUnitActiveSec = "1d";
    };
  };
  systemd.services.example.script = "true";
}
```

## Socket activation

`systemd.sockets` (per unit: `listenStreams`/`listenDatagrams`) starts
the matching `<name>.service` on first connection instead of at boot;
`notSocketActivated = true` on the service tells a switch to always
stop/start it rather than assuming a live socket handoff.

## Template units

`name@.service` declares a template; `systemctl start name@foo` (or a
unit that depends on `name@foo.service`) instantiates it. `%i` expands to
the instance string **with escaping applied** (path-like or otherwise
special characters come out `\x2d`-style escaped — see
`systemd.unit(5)` SPECIFIERS); `%I` is the same instance string with
that escaping undone. For an instance name typed by hand (`foo`, `bar`)
the two are identical, so most in-tree templates use `%i`; reach for `%I`
only when the instance itself was built from an escaped path (e.g. a
mount-generator style unit) and the _original_ string is what's needed —
a real in-tree template passes `%i` straight to the script:

```nix module
{ pkgs, ... }:
{
  systemd.services."worker@" = {
    description = "Worker pipe '%i'";
    scriptArgs = "%i";
    script = ''${pkgs.coreutils}/bin/cat "/etc/worker/$1.conf"'';
  };
}
```

`$1` here is whatever `systemctl start worker@<anything>` was called
with — validate it against an allowlist regex before using it in a path
or command line, the same way any other untrusted input is validated:

```bash cmd
[[ "$1" =~ ^[a-z0-9_-]+$ ]] || { echo "bad instance: $1" >&2; exit 1; }
```

Inspect one instance's logs with `journalctl -u 'name@*'` (glob, quoted
so the shell does not expand it) or `journalctl -u name@foo`. A polkit
rule that should apply to one instance only must match the exact unit
string, not a prefix — `action.lookup("unit")` returns the full
`name@instance.service`:

```text
polkit.addRule(function(action, subject) {
  if (action.id == "org.freedesktop.systemd1.manage-units" &&
    subject.isInGroup("operators")) {
    if (action.lookup("unit") == "worker@backup.service") {
      var verb = action.lookup("verb");
      if (verb == "start" || verb == "stop" || verb == "restart") {
        return polkit.Result.YES;
      }
    }
  }
});
```

## `systemd.packages` and drop-ins

`systemd.packages` installs unit files a package ships (its own
`lib/systemd/system/*`). When `systemd.services` also configures a unit
of the same name, the default `overrideStrategy` is
`asDropinIfExists`: your config is written as `<name>.service.d/
overrides.conf`, layered on top of the packaged unit rather than
replacing it — every field you don't set still comes from the package.
Systemd list directives (`ExecStart=` chief among them) **accumulate**
across a unit and its drop-ins, so replacing one means clearing it first
with an empty assignment, then setting the new value — the actual pattern
this nixpkgs uses to re-point polkit's own packaged unit:

```nix module
{ pkgs, ... }:
{
  systemd.services.example.serviceConfig.ExecStart = [
    ""
    "${pkgs.coreutils}/bin/true"
  ];
}
```

## `systemd.tmpfiles.rules` and `settings`

`systemd.tmpfiles.rules` takes raw `tmpfiles.d(5)` line strings;
`systemd.tmpfiles.settings` is the structured form (config-name →
path → rule-type → fields). `d` creates a directory (and, notably,
**adjusts the mode/owner of one that already exists** — it is not
create-if-missing-only); `z`/`Z` adjust an existing path's mode/owner
without creating it (`Z` recurses); `L+` (re)creates a symlink,
replacing anything already at that path.

```nix module
{
  systemd.tmpfiles.settings."10-example" = {
    "/var/lib/example-svc"."d" = {
      mode = "0750";
      user = "root";
      group = "root";
    };
  };
}
```

## Sources

- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (systemd unit options, tmpfiles)
- `/nix/store/k9cmnypyppj2dza7ak4p924lr3g3wxfn-systemd-257.10-man`
  (`systemd.unit(5)` SPECIFIERS: `%i` escaped vs `%I` unescaped;
  `systemd.timer(5)`: immediate-elapse scoped to `OnBootSec`/
  `OnStartupSec`, `Persistent=` scoped to `OnCalendar`)
- `nixos/lib/systemd-unit-options.nix` (`restartTriggers`, `reloadTriggers`,
  `startAt`, `timerConfig`, `socketConfig` declarations) in the pinned
  nixpkgs source
- `nixos/lib/systemd-lib.nix` (`overrideStrategy`, drop-in generation,
  `X-ReloadIfChanged`/`X-RestartIfChanged`/`X-StopIfChanged`; lines
  639-640 render `path` via `makeBinPath`/`makeSearchPathOutput "bin"
  "sbin"`; lines 686-696 append the stage-2 default `path` via `mkAfter`)
- `nixos/modules/system/boot/systemd/tmpfiles.nix` (`settings` type,
  rule-type description)
- `nixos/modules/security/polkit.nix` (the real `ExecStart = [ "" … ]`
  reset, `restartTriggers`, `stopIfChanged`)
- `nixos/modules/services/networking/spiped.nix` (a real `name@` template
  passing `%i` to a script via `scriptArgs`)
- `nixos/modules/services/networking/fastnetmon-advanced.nix` (a real
  polkit rule matching one exact `action.lookup("unit")`)
