# Phase 4a — switching the machine onto the repo

After the acceptance script shows a clean diff, the switch is:

    sudo nixos-rebuild switch --flake ~/nixos-agent-env#core

From then on this repo IS the machine's configuration; /etc/nixos stays as a
frozen fallback. If anything is wrong after the switch: reboot and pick the
previous generation in the boot menu (nothing is deleted), or run
`sudo nixos-rebuild switch --rollback`, and tell Claude.

Sanity after switching: `basket doctor` all green, monitors still lit
(the NVIDIA config traveled into the repo), `systemctl status
restic-backups-proton-drive.timer` active, hostname now `core`.
