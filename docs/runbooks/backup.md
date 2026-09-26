# Off-site backup — what you run

Daily, client-side-encrypted backup of the load-bearing state on `core`,
mirrored to your Proton Drive through Proton's official CLI. restic never
sends Proton anything but ciphertext.

## What is backed up and where it lands

- Local repo `/var/lib/restic/core` (ciphertext)
- Remote `/my-files/backups/core` (ciphertext mirror)
- Key = restic password (Proton Pass + paper)
- Nothing else is needed to restore.

The paths restic actually walks are `services.proton-backup.paths` in
`hosts/core/proton-backup.nix`, thirteen of them (a check,
`core-backup-wiring`, fails the build if any named path is missing from
this list):

- this repo — `/home/dalhaka/nixos-agent-env`, the working tree including
  `.git` — and `/etc/nixos`;
- the basket store `/var/lib/baskets/store` and `~/.config/basket`;
- the sibling flakes `~/flakes` and `~/strategy`;
- the five per-flake Claude memory directories —
  `~/.claude/projects/-home-dalhaka/memory`,
  `~/.claude/projects/-home-dalhaka-nixos-agent-env/memory`,
  `~/.claude/projects/-home-dalhaka-flakes-gaming/memory`,
  `~/.claude/projects/-home-dalhaka-flakes-media/memory`, and
  `~/.claude/projects/-home-dalhaka-strategy/memory`;
- the evidence store `/var/lib/evidence` (landed with switch #15);
- the lane ledgers — `/var/lib/lanes` (each lane's `ledger.jsonl`; its
  `jobs/` and `results/` are excluded). The broker audit logs
  (`/var/lib/egress-broker`) are never backed up by decision
  2026-09-05-audit-logs-backed-up.md; by its addendum they never leave the
  machine.

Restic runs as the operator (`services.proton-backup.user` = `dalhaka`), who
reads the lane directories through the `lane` group (`dalhaka` is a member).
That group-read path is asserted nowhere in this repo — see the `gap`
`backup-user-lane-group-unasserted` in `docs/ledger/claims.toml`.

`services.proton-backup.exclude` drops `.pytest_cache`, `.ruff_cache`,
`~/.cache`, and the lane patterns `/var/lib/lanes/*/jobs` and
`/var/lib/lanes/*/results` from whatever those paths cover, so under
`/var/lib/lanes/*` nothing survives the backup except the ledgers.

The backup itself never contains `~/.config/restic/password`.

## One-time setup after the switch

1. `proton-drive auth login` once, in the desktop session — it opens a
   browser sign-in and saves the session in your GNOME Keyring. Nothing else
   in this setup needs your Proton password again.
2. `shred -u ~/.config/rclone/rclone.conf` — rclone is retired (the Proton
   Drive CLI replaces it), and that file holds your Proton account password
   in the clear. Delete it now.
3. Confirm the restic password is where you expect it: in Proton Pass, and
   on paper. It is the only key that can decrypt either copy of the backup.
4. `systemctl --user start proton-drive-push.timer` — once. A switch installs
   the 00:30 push timer but does not start it inside a desktop session that
   was already logged in (logging out and back in does the same). Check with
   `systemctl --user list-timers proton-drive-push.timer`: a NEXT time must
   show. Without this, only the kick after each nightly backup pushes.

## Daily rhythm

- `00:00` — the system restic job runs: backup, prune, `check
  --read-data-subset`.
- Right after that backup succeeds, if you're logged in, it also kicks the
  push immediately — no need to wait for the timer.
- `00:30` — the push timer runs anyway (catches up if you were logged out
  at 00:00, or the immediate kick had no session to reach). It mirrors the
  local repository to Proton Drive and reconciles anything prune removed.
- If you're logged out at both points, the push simply waits for your next
  login before the timer's next tick reaches it.

## Check it worked

```
systemctl status restic-backups-core-local
systemctl --user status proton-drive-push
proton-drive filesystem list /my-files/backups/core/snapshots
```

The push unit's own journal line, on success, reads
`proton-backup-push: OK snapshots=<n> remote=<n>` — the two counts should
match.

## Restore

From the local repository (fastest, this machine):

```
restic -r /var/lib/restic/core restore latest --target /tmp/restore
```

From Proton Drive, on a fresh machine (after `proton-drive auth login`):

```
proton-drive filesystem download /my-files/backups/core /tmp
restic -r /tmp/core snapshots
```

Either way, restic asks for the repository password — Proton Pass or the
paper copy.

## Known limits

- The push needs your login keyring unlocked (a logged-in desktop session)
  — it's a `systemd --user` unit, not a system one, because the Proton
  Drive CLI's credential store is your GNOME Keyring.
- We never call `filesystem empty-trash` — your Proton Drive trash is yours;
  the push only ever deletes the specific objects it itself trashed.
- The first push uploads the whole repository. Today that's small (tens of
  MB) — expect it to take longer once the repository has grown.

## If a backed-up path is missing

restic exits 3 ("some files could not be read") when a path in
`services.proton-backup.paths` doesn't exist, and the backup unit then
reports failure even though everything that *did* exist got backed up.
Check `systemctl status restic-backups-core-local` for which path, and
either restore it or drop it from the list in
`hosts/core/proton-backup.nix`.

## Overriding the reconcile refusal

The push refuses to delete more than half of all remote objects in one run
(a legitimate prune removes a fraction at a time; deleting a majority is
far likelier to mean the local repository is damaged than a busy prune). If
you've verified the local repository is fine and the deletion is expected
— for example after a manual prune with unusually aggressive retention —
override it once.

`systemctl start` does **not** forward your shell's environment to the
unit — a service only ever sees the manager's environment plus whatever
`Environment=` lines the unit itself declares, and `proton-drive-push.service`
declares no `PROTON_BACKUP_FORCE_RECONCILE`. So
`PROTON_BACKUP_FORCE_RECONCILE=1 systemctl --user start proton-drive-push.service`
looks right but does nothing — the push refuses again exactly as before.
Two ways that actually work:

Push it into the user manager's own environment, run the unit, then take it
back out (leaving it set would silently force every future reconcile, so
always unset-environment afterwards):

```
systemctl --user set-environment PROTON_BACKUP_FORCE_RECONCILE=1
systemctl --user start proton-drive-push.service
systemctl --user unset-environment PROTON_BACKUP_FORCE_RECONCILE
```

Or skip the unit and run the script directly in your desktop session (it's
on `PATH` via `environment.systemPackages`, and a login session already has
`XDG_RUNTIME_DIR` set for the Proton Drive CLI's keyring):

```
PROTON_BACKUP_REPO=/var/lib/restic/core PROTON_BACKUP_FORCE_RECONCILE=1 proton-backup-push
```
