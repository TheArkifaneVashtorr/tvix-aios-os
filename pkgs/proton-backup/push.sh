#!/usr/bin/env bash
# proton-backup-push: mirror a local restic repository to Proton Drive with
# the official Proton Drive CLI. Local is the source of truth; the remote is a
# byte-for-byte mirror of the repository's object store minus locks/.
# Safety rails: never empty-trash, never touch keys/ or config remotely,
# refuse to reconcile with zero local snapshots or when more than half of
# all remote objects would be deleted; verify snapshot parity at the end.
set -euo pipefail

repo="${PROTON_BACKUP_REPO:?PROTON_BACKUP_REPO (local restic repository) is required}"
remote_parent="${PROTON_BACKUP_REMOTE_PARENT:-/my-files/backups}"
cli="${PROTON_DRIVE_CLI:-proton-drive}"
lock_wait="${PROTON_BACKUP_LOCK_WAIT_SECONDS:-1800}"
name="$(basename "$repo")"
remote="$remote_parent/$name"

exec 9>"${XDG_RUNTIME_DIR:-/tmp}/proton-backup-push.lock"
if ! flock -n 9; then
  echo "proton-backup-push: another push is running"
  exit 0
fi

# A restic job in flight leaves lock files; wait for it, then give up loudly.
waited=0
while [ -n "$(ls -A "$repo/locks" 2>/dev/null)" ]; do
  if [ "$waited" -ge "$lock_wait" ]; then
    echo "proton-backup-push: restic lock still present after ${lock_wait}s; not pushing a repository mid-write" >&2
    exit 1
  fi
  sleep 2
  waited=$((waited + 2))
done

local_snapshots=$(find "$repo/snapshots" -maxdepth 1 -type f | wc -l)
if [ "$local_snapshots" -lt 1 ]; then
  echo "proton-backup-push: refusing to push a repository with zero snapshots (is it initialized?)" >&2
  exit 1
fi

if ! "$cli" filesystem info "$remote" --json >/dev/null 2>&1; then
  "$cli" filesystem create-folder "$remote_parent" "$name"
fi

# Upload the object store (locks/ deliberately absent). The CLI skips
# identical content itself; -f skip handles same-name/different-content,
# which content-addressed restic names never produce except for config.
uploads=("$repo/config" "$repo/keys" "$repo/index" "$repo/snapshots" "$repo/data")
"$cli" filesystem upload -t -f skip -d merge "${uploads[@]}" "$remote"

remote_names() { # <subdir> -> names of remote files in it
  # .name is a Result<string,...>; skip entries whose name failed to decrypt
  # rather than printing the literal "null" and treating it as a real object.
  "$cli" filesystem list -t file "$remote/$1" --json | jq -r '.[] | select(.name.ok) | .name.value'
}

stale=()
remote_total=0
collect_stale() { # <subdir>: remember remote files that prune removed locally
  local sub="$1" names
  names=$(remote_names "$sub") || return 0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    remote_total=$((remote_total + 1))
    [ -e "$repo/$sub/$f" ] || stale+=("$remote/$sub/$f")
  done <<<"$names"
}

collect_stale index
collect_stale snapshots
for d in "$repo"/data/*/; do
  [ -d "$d" ] || continue
  collect_stale "data/$(basename "$d")"
done
if [ "${#stale[@]}" -gt 0 ]; then
  # A legitimate prune removes a fraction of the object store. Deleting more
  # than half of everything remote is far likelier to mean the local
  # repository is damaged than that prune was busy -- refuse, and make the
  # override explicit.
  if [ $((${#stale[@]} * 2)) -gt "$remote_total" ] && [ "${PROTON_BACKUP_FORCE_RECONCILE:-0}" != "1" ]; then
    echo "proton-backup-push: refusing to delete ${#stale[@]} of $remote_total remote objects (more than half; verify the local repository, then set PROTON_BACKUP_FORCE_RECONCILE=1)" >&2
    exit 1
  fi
  # The CLI's `filesystem delete` only accepts already-trashed items
  # (addressed by /trash/<name>); trash the stale my-files paths first, then
  # permanently delete each by its basename under /trash.
  "$cli" filesystem trash "${stale[@]}"
  trashed=()
  for p in "${stale[@]}"; do
    trashed+=("/trash/$(basename "$p")")
  done
  "$cli" filesystem delete "${trashed[@]}"
fi

remote_snapshots=$(remote_names snapshots | grep -c . || true)
if [ "$remote_snapshots" -ne "$local_snapshots" ]; then
  echo "proton-backup-push: parity FAIL snapshots local=$local_snapshots remote=$remote_snapshots" >&2
  exit 1
fi
echo "proton-backup-push: OK snapshots=$local_snapshots remote=$remote_snapshots"
