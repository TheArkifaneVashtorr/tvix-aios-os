# Phase 4a — switching the machine onto the repo

After the acceptance script shows a clean diff, the switch is:

    sudo nixos-rebuild switch --flake ~/nixos-agent-env#core

From then on this repo IS the machine's configuration; /etc/nixos stays as a
frozen fallback. If anything is wrong after the switch: reboot and pick the
previous generation in the boot menu (nothing is deleted), or run
`sudo nixos-rebuild switch --rollback`, and tell Claude.

Switch from a CLEAN tree. A dirty tree bakes a `-dirty` configuration
revision, which leaves the `drift` tile at warn ("switched from a dirty
tree") however current the code is; committing and switching again is the
only way to clear it (measured 2026-09-21, gen 75 then 76).

Sanity after switching: hostname now `core`, monitors still lit (the NVIDIA
config traveled into the repo), and the Helm board green at
<http://127.0.0.1:7700> — the board is what reports the rest, and reads the
same from a shell:

    evidence bundle --markdown

`drift` should read `live = HEAD <rev>`. `flake-check` lags until the nightly
runs against the new HEAD; it says so in its own words ("covers neither HEAD
nor live") rather than claiming a green it does not have, and
`systemctl --user start helm-flake-check.service` settles it now.

The two host checks, by the names the units actually carry:

    "$(nix eval --raw .#nixosConfigurations.core.config.services.helm.basketPackage)/bin/basket" doctor
    systemctl status restic-backups-core-local.timer

Both were wrong in this runbook until 2026-09-21. `basket` is not in
`environment.systemPackages` — the `basket-doctor` tile calls an absolute
`services.helm.basketPackage` path, so a bare `basket doctor` is `command not
found` even while the tile reports six checks passed. And
`restic-backups-proton-drive.timer` no longer exists: the live timer is
`restic-backups-core-local.timer`, and proton backup reports through the
`backup-parity` tile instead.
