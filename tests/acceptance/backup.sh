#!/usr/bin/env bash
# Off-site backup acceptance (operator-run, docs/runbooks/backup.md): the
# daily restic job produces a local snapshot, the push mirrors it to Proton
# Drive with a matching snapshot count, a real file round-trips
# byte-for-byte through a restore, and rclone is fully retired. Needs sudo
# (starts the system restic unit -- this machine, not a throwaway test VM)
# and a logged-in desktop session (the push is a systemd --user unit reading
# the Proton Drive CLI's keyring login).
#
# Run from the repo root: nix develop -c tests/acceptance/backup.sh
set -euo pipefail

repo="${PROTON_BACKUP_REPO:-/var/lib/restic/core}"
password_file="${PROTON_BACKUP_PASSWORD_FILE:-/home/dalhaka/.config/restic/password}"
remote_snapshots_path="${PROTON_BACKUP_REMOTE_SNAPSHOTS:-/my-files/backups/core/snapshots}"
restore_file="${PROTON_BACKUP_RESTORE_FILE:-/home/dalhaka/nixos-agent-env/README.md}"

export RESTIC_PASSWORD_FILE="$password_file"

pass=0
fail=0
step() {
  echo
  echo "== $1"
}
ok() {
  echo "   PASS: $1"
  pass=$((pass + 1))
}
bad() {
  echo "   FAIL: $1"
  fail=$((fail + 1))
}
warn() {
  echo "   WARN: $1"
}

step "1. system restic job: local repository has at least one snapshot"
if sudo systemctl start restic-backups-core-local.service; then
  ok "restic-backups-core-local.service ran to completion"
else
  bad "restic-backups-core-local.service failed -- see journalctl -u restic-backups-core-local"
fi
local_snapshots=0
snap_err=$(mktemp)
if snap_json=$(restic -r "$repo" snapshots --json 2>"$snap_err"); then
  if local_snapshots=$(echo "$snap_json" | jq 'length'); then
    if [ "$local_snapshots" -ge 1 ]; then
      ok "local repository has ${local_snapshots} snapshot(s)"
    else
      bad "local repository has zero snapshots"
    fi
  else
    bad "could not parse restic snapshots --json output"
    local_snapshots=0
  fi
else
  bad "restic snapshots --json failed: $(cat "$snap_err")"
fi
rm -f "$snap_err"

step "2. push mirrors the local repository to Proton Drive"
if systemctl --user start proton-drive-push.service; then
  ok "proton-drive-push.service ran to completion"
else
  bad "proton-drive-push.service failed -- see journalctl --user -u proton-drive-push"
fi
push_invocation=$(systemctl --user show -p InvocationID --value proton-drive-push.service 2>/dev/null || true)
if [ -n "$push_invocation" ] && journalctl --user -u proton-drive-push "_SYSTEMD_INVOCATION_ID=${push_invocation}" --no-pager | grep -q 'proton-backup-push: OK'; then
  ok "push unit reported OK in its journal for this run"
else
  bad "push unit did not report 'proton-backup-push: OK' for this run -- see journalctl --user -u proton-drive-push"
fi

step "3. remote parity: Proton Drive snapshot count matches local"
remote_err=$(mktemp)
if remote_json=$(proton-drive filesystem list -t file "$remote_snapshots_path" --json 2>"$remote_err"); then
  if remote_count=$(echo "$remote_json" | jq 'length'); then
    if [ "$remote_count" -eq "$local_snapshots" ]; then
      ok "remote snapshot count (${remote_count}) matches local (${local_snapshots})"
    else
      bad "remote snapshot count (${remote_count}) does not match local (${local_snapshots})"
    fi
  else
    bad "could not parse proton-drive filesystem list --json output"
  fi
else
  bad "proton-drive filesystem list failed: $(cat "$remote_err")"
fi
rm -f "$remote_err"

step "4. restore drill: a real file round-trips byte-for-byte"
restore_dir=$(mktemp -d)
trap 'rm -rf "$restore_dir"' EXIT
if restic -r "$repo" restore latest --target "$restore_dir" --include "$restore_file" >/dev/null; then
  if cmp -s "${restore_dir}${restore_file}" "$restore_file"; then
    ok "restored ${restore_file} matches the live file"
  else
    bad "restored ${restore_file} differs from the live file"
  fi
else
  bad "restic restore latest --include ${restore_file} failed"
fi

step "5. rclone is retired"
if ! command -v rclone >/dev/null 2>&1; then
  ok "rclone is not on PATH"
else
  bad "rclone is still on PATH -- retirement incomplete"
fi
if [ ! -e "${HOME}/.config/rclone/rclone.conf" ]; then
  ok "no rclone.conf remains"
else
  warn "\$HOME/.config/rclone/rclone.conf still exists -- it holds your Proton account password in the clear; shred -u it (docs/runbooks/backup.md)"
fi

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "BACKUP ACCEPTANCE: PASS"
else
  echo "BACKUP ACCEPTANCE: FAIL"
  exit 1
fi
