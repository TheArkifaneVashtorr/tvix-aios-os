# Concept 2026-09-03a — the switch pre-flight is a diff of two store paths

**Class:** operator-gate instrument (pre-switch) / Helm tile candidate.
**Status:** proposed (orchestrator, first use 2026-09-03 before the round-1 switch).

**Origin (2026-09-03, preparing the Helm v0 + gaming switch):** the question
the operator actually has before typing `nixos-rebuild switch` is not "does
the source diff look right" but "what will activation *do* to the running
machine" — which units restart, which get reloaded, which files under `/etc`
change, which directories tmpfiles will chmod, how much the closure grows.
Every one of those answers is computable read-only, without root and without
`dry-activate`, from two store paths: `/run/current-system` (live) and the
freshly built toplevel. `diff -rq` over `etc/systemd/system`,
`etc/systemd/user`, `etc/tmpfiles.d` and the rest of `etc`, plus
`nix store diff-closures`, gave this session the complete activation surface
of generation 22 → HEAD in under a minute: two new system units
(static-web-server service + socket), four new user units (Helm's two timers
and services), one changed service (restic, new paths), three drop-in
overrides (dbus, polkit, accounts-daemon), eight `/etc` files, eight tmpfiles
lines. The same diff between the base toplevel and its `gaming`
specialisation told us exactly what entering the profile touches (udevd and
modules-load overrides, a user `gamemoded` service, two udev rule files, the
32-bit driver tmpfiles line) — and, just as importantly, what it does *not*
touch (no `egress-*`, `cowork*`, `basket*`, `restic-*`, `helm-*` unit differs).
The adversarial audit that followed was scoped by that list rather than by
reading 2,450 changed lines.

**Idea:** make the pre-flight a tool, then a tile. (a)
`tools/switch-preflight.sh <toplevel>`: builds nothing, takes the toplevel
path, prints the four diffs above in plain words ("would restart: …",
"would reload: …", "new units: …", "/etc changes: …", "tmpfiles would adjust
mode on existing dirs: …", "closure +N GiB, largest new paths: …"), and
exits non-zero if any agent-facing unit (`egress-*`, `cowork*`, `basket*`,
`claude-app*`) differs — the eval-time assertion from
`checks.core-gaming-wiring`, re-checked against the *built* unit texts.
(b) a Helm tile, **pending-switch**: when the drift tile says HEAD ≠ live,
the collector builds nothing either — it reads the last toplevel the
nightly flake check produced (or a `result` GC root the operator keeps) and
shows the same summary, so the page answers "if I switch now, what
restarts" before the operator opens a terminal. Restart semantics come from
the NixOS `switch-to-configuration` rules at the pin (unit text differs ⇒
restart unless `reloadIfChanged`/`restartIfChanged=false`; sockets; user
units of running managers), so the tool must read those rules from the
pinned nixpkgs, not guess.

**Payoff:** the operator's gate step gets a deterministic, test-backed
answer to "what will this do to my desktop session" instead of a
reassurance; the orchestrator's pre-switch review gets a scope in one
command; regressions where a profile starts touching an agent unit fail a
script the operator can run, not just an eval that only the factory runs.

**Dependencies:** the NixOS activation rules at the `nixpkgs-host` pin
(read from the store, verified by the VM test); Helm's collector shape
(`pkgs/helm/collect.py`, per-tile isolation); for the tile, a GC-rooted
"last built toplevel" — the nightly `helm-flake-check` does not build the
toplevel today (it runs `nix flake check`, which evaluates `host-core` but
does not keep a result link).

**Test:** a NixOS VM test with two toplevels that differ by one unit and one
tmpfiles line asserts the pre-flight prints exactly those two items and
nothing else; a negative case where a specialisation alters an `egress-*`
unit must make it exit non-zero.

**Earliest landing:** the script with wiring round 2 (the media switch is
the next gate that wants it); the tile with Helm v1's profile tile, which
already gains "last switch from `<rev>`" and is the natural neighbour.
