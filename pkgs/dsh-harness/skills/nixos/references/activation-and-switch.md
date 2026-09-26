verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Reasoning about what `nixos-rebuild switch`/`test`/`boot` actually does.

Procedural reference — no idiom pair. It reads real behaviour off the
pinned `nixos-rebuild` shell script and the Rust `switch-to-configuration`
implementation this pin defaults to
(`system.switch.enableNg` — see below), not general systemd lore.

## `nixos-rebuild` verbs

`switch`/`boot`/`test`/`build`/`dry-build`/`dry-activate`/`build-vm`/
`build-vm-with-bootloader`/`build-image`/`list-generations`/`edit`/`repl`.
`switch` and `boot` build, make the new closure the *default* boot entry
(`nix-env -p /nix/var/nix/profiles/system --set <path>`), and — `switch`
only — activate it now. `boot` builds and installs the bootloader entry
but exits before activating: the new generation runs after the *next*
reboot, not now. `test`/`build`/`dry-build` never touch the profile or
the bootloader at all: `test` activates the new closure into the running
system for this boot only, `build`/`dry-build` only build (`build` leaves
a `./result` symlink; `dry-build` does not even do that).
`dry-activate` builds and runs the activation logic in report-only mode —
prints what would restart/reload/stop without doing it.

## `switch-to-configuration` at this pin

`system.switch.enableNg` defaults to `system.switch.enable`
(`true`) — this pin runs the Rust rewrite
(`pkgs.switch-to-configuration-ng`) by default, not the historical Perl
script (still present, opt back in with `enableNg = false`, deprecated
here with a build warning). `nixos-rebuild` invokes it as
`switch-to-configuration <verb>` (`switch`/`boot`/`test`/`dry-activate`)
inside a `systemd-run --unit=nixos-rebuild-switch-to-configuration`
wrapper, so a PTY drop or SSH disconnect mid-switch does not kill it.

**Deciding restart vs. reload vs. leave alone:** for every *system* unit
present in both the running system and the new one, it diffs the two
rendered unit files section by section. Equal → untouched. Any
difference outside a small ignore-list (`Description`, `Documentation`,
`OnFailure`, …) → restart, **unless** the *only* difference is the
`[Unit]` key `X-Reload-Triggers` (from
`systemd.services.<name>.reloadTriggers` — a list of arbitrary items,
hashed into a store path written to that key; a change anywhere in the
list changes the path, which the diff sees as *a* difference, just one
routed to reload instead of restart) or the `[Mount]` key `Options` —
those two cases reload instead. `restartTriggers` works the same way
but writes an ordinary `[Unit]` key, `X-Restart-Triggers` — it gets no
special case, so a change there is just one more "any other difference"
→ restart. `reloadIfChanged = true` writes `[Service]` key
`X-ReloadIfChanged=true`, a blanket "any change to this unit → reload,
never restart" — coarser than `reloadTriggers` and the option's own
description in this nixpkgs recommends `reloadTriggers` instead for
that reason. A unit present in the new system but not the old one starts
if it is wanted by something already running; a unit dropped from the
new system stops. `restartIfChanged = false` (used on
`systemd-udev-settle` and `user@` itself, among other boot-critical
units in this nixpkgs) opts a unit out of the restart decision entirely
— the module stays running across any change until the next reboot;
this is a *system*-unit mechanism, so `user@`'s own setting affects only
how the **system** manager treats the `user@<uid>.service` instance
units (each logged-in user's session manager process), not what happens
inside that user's own unit tree — see below for that. `stopIfChanged =
false` (used on `polkit`, `systemd-logind`, `user-runtime-dir@`)
restarts those in a single step instead of stop-then-start.

**Socket-activated units** whose socket is unchanged are left running;
`notSocketActivated = true` forces the normal stop/start decision
even when a matching socket exists.

**User managers:** none of the diffing above applies to *user* units at
all — `do_user_switch` (the code this pin's Rust rewrite runs, once per
currently logged-in user, spawned with that user's uid/gid and
`XDG_RUNTIME_DIR`) does no unit comparison whatsoever. It opens that
user's own session D-Bus, calls `systemd.reexecute()` on their user
manager (a `systemctl --user daemon-reexec`, which reloads unit files
but does not by itself start, stop, or restart anything already
running), then `restart_unit("nixos-activation.service", "replace")`
against that same user manager and waits for the job to finish. That is
the entire user-scope mechanism: no changed unit is restarted, no
removed unit is stopped, no per-unit diff is computed at all. The
"switch does not start a newly-enabled user unit in an already-logged-in
session" fact from the systemd-units reference follows directly — there
is no step here that would start *any* user unit, changed or new; only a
fresh `nixos-activation.service` run and whatever that run's own script
does (which does not touch `systemd --user start <name>`).

## Specialisations: snapshot semantics

`specialisation.<name>.configuration` builds a **complete separate**
`system.build.toplevel`, symlinked at `<parent-toplevel>/specialisation/
<name>` when the parent is built — not re-evaluated later. A running
specialisation is whatever was baked into whichever generation's
toplevel is currently active; switching *into* a specialisation
(`/run/current-system/specialisation/<name>/bin/switch-to-configuration
test`) does not change which generation is the profile's default, and a
plain `nixos-rebuild switch` from inside a specialisation still builds
and activates the **base** configuration, not a re-evaluation of the one
you are standing on. Specialisation names may not contain `/`
(a build-time assertion).

## `test` never touches the bootloader

Confirmed at both layers this pin uses: `nixos-rebuild`'s own verb
dispatch only calls `nix-env --set`/installs a boot entry for
`switch`/`boot`; and inside `switch-to-configuration-ng`,
`do_install_bootloader` is called only for `Action::Switch`/`Action::Boot`
— `test` and `dry-activate` never reach it. `test` activates the new
closure into the *running* system and stops there; nothing on disk that
the bootloader reads (`/boot`, the profile's default generation symlink)
changes, so a reboot after `test` (with no `switch`/`boot` since) comes
back on the old generation.

## Generations, rollback, GC roots

Each `switch`/`boot` adds a generation to the `system` profile
(`/nix/var/nix/profiles/system-<N>-link`); `nixos-rebuild switch
--rollback` re-activates the previous one without rebuilding.
`nixos-rebuild list-generations` reads them back. A profile generation
is a GC root — see nix-cli's roots section for how `nix-collect-garbage`
prunes old ones and what keeps a closure alive in between.

## Closure and activation diffs

`nix store diff-closures <old> <new>` (nix-cli reference) is
package-level and **closure-inclusive**: because each specialisation's
toplevel is itself a store path reachable from its parent, diffing two
*base* toplevels reports package changes pulled in through their
specialisations too, not just the base configuration's own packages.

For what will actually change on activation — the part `diff-closures`
does not show — diff the two toplevels' rendered output directly:

```bash cmd
diff -rq /run/current-system/etc/systemd/system ./result/etc/systemd/system
diff -rq /run/current-system/etc/systemd/user ./result/etc/systemd/user
diff -rq /run/current-system/etc ./result/etc
```

Anything under `etc/systemd/system` that differs is a *system* unit the
switch will restart/reload/stop per the rules above — that diff is
exactly what `compare_units` itself computes. `etc/systemd/user` differs
the same way on disk, but nothing reads that diff at switch time: the
user-manager step above reloads and re-execs regardless of what changed
there, so a diff under it tells you what a logged-in session will pick
up (now, via the reload) or not pick up (a newly-wanted unit, until next
login) — not what will be restarted, because nothing there gets
restarted by the switch itself. Anything else under `etc` is a plain
file replacement with no unit-restart consequence on its own (unless
something's `restartTriggers`/`reloadTriggers` names it).

## Sources

- `pkgs/by-name/sw/switch-to-configuration-ng/src/src/main.rs` (verb
  dispatch, `compare_units`, bootloader-install gating, user-manager
  reload) in the pinned nixpkgs source
- `pkgs/os-specific/linux/nixos-rebuild/nixos-rebuild.sh` (verb → action
  mapping, profile set, systemd-run wrapping)
- `nixos/modules/system/activation/switchable-system.nix`
  (`system.switch.enableNg`)
- `nixos/modules/system/activation/specialisation.nix` (snapshot build,
  the `/` name assertion)
- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (generations, rollback)
