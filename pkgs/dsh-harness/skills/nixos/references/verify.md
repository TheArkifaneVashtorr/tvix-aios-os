verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Mechanically verifying a change believed complete — the exact commands
and what "good" looks like for each. Procedural reference — no idiom
pair; run every step below in order, do not stop at the first one that
looks fine.

## `nix flake check -L`

Every declared check evaluates and builds; "good" is every one green
(doc-tests, citations, budget, lint, lock-guard, router, or this
repository's own equivalents) with `-L` streaming enough output to see
which one, if any, failed rather than a bare exit code:

```bash cmd
nix flake check -L --offline
```

## The toplevel build

A green `flake check` proves the _checks_ build; it does not by itself
prove the _system_ configuration does — build it explicitly and keep
the result symlink, since the next two steps diff against it (`core`
stands in below for the flake's own host name):

```bash cmd
nix build .#nixosConfigurations.core.config.system.build.toplevel \
  --offline -L -o toplevel-after
```

"Good" is a store path with no build failures; a name mismatch (wrong
host attribute) or a missing `nixosConfigurations` output fails loudly
here rather than quietly at diff time.

## `nix store diff-closures`

Package-level, closure-inclusive (nix-cli, activation-and-switch
references — the second covers the specialisation-inclusion trap):

```bash cmd
nix store diff-closures /run/current-system ./toplevel-after
```

"Good" is a diff containing only the packages the plan says should
change — nothing pulled in unexpectedly, nothing expected missing. A
package that moved only because a specialisation changed, not the base
configuration, is not a regression in the base — read which generation
actually carries it before flagging it as one.

## The activation diff

`diff-closures` shows package changes; it does not show which _units_
will restart, reload, or stop, or which plain files under `/etc`
change. Diff the two toplevels' rendered output directly, unit
directories first, then `/etc` as a whole, then tmpfiles rules called
out on their own even though they nest under `/etc`, because a tmpfiles
`d`/`z`/`L+` change only takes effect on the next tmpfiles run, not
immediately on switch (systemd-units reference), which a reviewer
skimming only the units diff will otherwise miss entirely:

```bash cmd
diff -rq /run/current-system/etc/systemd/system ./toplevel-after/etc/systemd/system
diff -rq /run/current-system/etc/systemd/user ./toplevel-after/etc/systemd/user
diff -rq /run/current-system/etc ./toplevel-after/etc
diff -rq /run/current-system/etc/tmpfiles.d ./toplevel-after/etc/tmpfiles.d
```

"Good" is every reported difference accounted for by the plan: a unit
diff means a restart/reload per the activation-and-switch reference's
rules, a plain `/etc` diff means a file replacement with no unit
consequence unless something's `restartTriggers`/`reloadTriggers` names
it, a _tmpfiles.d_ diff means the rule change lands the next time
tmpfiles runs, not this switch.

## Evaluating a specialisation's marker

_config.isSpecialisation_ is `false` on a base configuration and `true`
on every specialisation's own evaluated `configuration` — the
mechanical way to confirm which one an already-evaluated attribute set
actually is, rather than trusting which attribute path it came from.
Read it from _outside_ the module that declares the specialisation, not
from that module's own `assertions` — a specialisation inherits its
parent's modules (`inheritParentConfig`, module-system reference), so
an assertion placed inside the same module runs a second time, inside
the child, where `isSpecialisation` is already `true` and would trip
its own check:

```nix expr
let
  sys = lib.nixosSystem {
    system = pkgs.system;
    modules = [
      {
        fileSystems."/".device = "/dev/null";
        boot.loader.grub.enable = false;
        system.stateVersion = "25.05";
        nixpkgs.hostPlatform = pkgs.system;
        specialisation.demo.configuration = _: { };
      }
    ];
  };
in
if
  sys.config.isSpecialisation == false
  && sys.config.specialisation.demo.configuration.isSpecialisation == true
then
  true
else
  throw "isSpecialisation did not distinguish base from specialisation"
```

"Good" is the base evaluating `false` and every specialisation's own
`configuration` evaluating `true`; seeing the reverse, or `false` on
both, means the wrong attribute path was read.

## Sources

- `/nix/store/ccppgf5px2d3ig46swcqy0jkiq3nw5bm-nix-2.28.5-doc`
  (`nix3-flake-check`, `nix3-build`, `nix3-store-diff-closures`)
- `nixos/modules/system/activation/specialisation.nix`
  (`isSpecialisation`, the `configuration` option)
- `nixos/modules/system/activation/no-clone.nix`
  (`isSpecialisation = mkOverride 0 true` on a specialisation's own
  config)
