verified: nixpkgs ac62194c · nix 2.28.5 · 2026-09-03

## Read when

Looking for "the option for X" — you know the subsystem, not the exact
path or which module declares it.

Procedural reference — no idiom pair. A map from subsystem to option
prefix to the module source that declares it, plus the two recipes that
turn "I think it's under this prefix" into a confirmed type and default
before you write anything that uses it (SKILL.md rule 1).

## Query recipes

`nixos-option <path>` **evaluates** (it does not build) a configuration's
option (type, current value, declared-by list) — it takes either a
`--flake`/`-F` target naming a `nixosConfigurations` output, or falls
back to the host's classic `<nixos-config>` (`$NIXOS_CONFIG`, or
`nixos-config=` in `NIX_PATH`) when no flake target is given, so a
`nixosConfigurations` output is not required.

```bash cmd
nixos-option services.openssh.enable
```

`nix eval .#nixosConfigurations.<host>.options.<path>.{type,default,
description}` reads the same information straight from a flake's
`options` tree without building anything — the one that works from any
flake with a `nixosConfigurations` output, including one you have not
switched to yet (`core` stands in below for the flake's own host name):

```bash cmd
nix eval .#nixosConfigurations.core.options.services.openssh.enable.type --offline
nix eval .#nixosConfigurations.core.options.services.openssh.enable.default --offline
```

The two recipes fail _differently_ on a typo'd path, and neither
produces the module-system "option does not exist" shape (debugging
reference) — that shape fires only when the bad path is **defined** in
a config, not when it is read out of `options`.

The `nix eval .../options.<path>` recipe reads the `options` tree with
a plain attribute lookup, so a typo'd segment fails as a plain
attribute-set lookup failure, complete with nix's own suggestion:

```text
$ nix eval .#nixosConfigurations.core.options.services.openshh.enable.type --offline
error: attribute 'openshh' missing
       …
       Did you mean openssh?
```

`nixos-option` does not walk `options` to check existence — it checks
`config` first and raises its own error, a third shape distinct from
both of the above:

```text
$ nixos-option services.openshh.enable
error: Couldn't resolve config path 'services.openshh.enable'
```

Either message in place of a type and default is exactly the
confirmation these recipes exist to produce, before the path is used
anywhere else — but expect the shape above from each, not the
module-system one.

## Subsystem → option prefix → module

An attrsOf/submodule option (`systemd.services`, `users.users`,
`fileSystems`, …) is declared once per **instance name**, shown here as
`<name>`; a plain nested option (SSH, NVIDIA, and most of the rows
below) has no bare prefix in the options set — only full leaf paths
exist, so the table cites one representative leaf under each. The
declaring module for every row is listed under Sources (one systemd
module declares both the service and timer rows).

| subsystem | representative option |
| --- | --- |
| SSH server | `services.openssh.enable` |
| Firewall (iptables, default) | `networking.firewall.enable` |
| Firewall (nftables backend) | `networking.nftables.enable` |
| systemd service fields | `systemd.services.<name>.serviceConfig` |
| systemd timer fields | `systemd.timers.<name>.timerConfig` |
| tmpfiles rules | `systemd.tmpfiles.settings` |
| NVIDIA driver | `hardware.nvidia.open` |
| GPU / 32-bit graphics | `hardware.graphics.enable` |
| setuid/capability wrapper | `security.wrappers.<name>.source` |
| polkit | `security.polkit.enable` |
| PAM service | `security.pam.services.<name>.enable` |
| users and groups | `users.users.<name>.uid` |
| bootloader (grub) | `boot.loader.grub.enable` |
| nix daemon settings | `nix.settings` |
| filesystems | `fileSystems.<name>.device` |
| files under `/etc` | `environment.etc.<name>.text` |
| specialisations | `specialisation.<name>.configuration` |
| foreign-binary loader | `programs.nix-ld.enable` |
| release/state marker | `system.stateVersion` |

A prefix not in this table is still findable the same two ways: the
manual's own option index (below) or `nix eval
.#nixosConfigurations.<host>.options` walked with _builtins.attrNames_
one level at a time from the subsystem's top-level name
(`networking`, `services`, `hardware`, …).

## The rendered manual as an index

`/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html` renders
every catalogued option with its own type, default and description and
cross-links to related options — open its option-search page and search
the subsystem word (`nginx`, `postgresql`, `borgbackup`) when the prefix
is not one of the common ones above; every result there is a real,
catalogued option, unlike an internal `serviceConfig`/`extraConfig`
freeform key (systemd-hardening, security references), which resolves
only by reading the declaring module's source directly since the manual
does not render freeform sub-keys at all.

## Sources

- `/nix/store/04m100144p8sn2507crh8bx1sqqb696w-nixos-manual-html`
  (rendered option index, option search)
- `/nix/store/ccppgf5px2d3ig46swcqy0jkiq3nw5bm-nix-2.28.5-doc`
  (`nix3-eval`)
- `nixos/modules/services/networking/ssh/sshd.nix`
- `nixos/modules/services/networking/firewall.nix`
- `nixos/modules/services/networking/nftables.nix`
- `nixos/lib/systemd-unit-options.nix`
- `nixos/modules/system/boot/systemd/tmpfiles.nix`
- `nixos/modules/hardware/video/nvidia.nix`
- `nixos/modules/hardware/graphics.nix`
- `nixos/modules/security/wrappers/default.nix`
- `nixos/modules/security/polkit.nix`
- `nixos/modules/security/pam.nix`
- `nixos/modules/config/users-groups.nix`
- `nixos/modules/system/boot/loader/grub/grub.nix`
- `nixos/modules/config/nix.nix`
- `nixos/modules/tasks/filesystems.nix`
- `nixos/modules/system/etc/etc.nix`
- `nixos/modules/system/activation/specialisation.nix`
- `nixos/modules/programs/nix-ld.nix`
- `nixos/modules/misc/version.nix`
