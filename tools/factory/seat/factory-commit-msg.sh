#!/usr/bin/env bash
# factory-commit-msg.sh <message-file> — the per-workspace commit-msg hook
# factory-ws installs at githooks/commit-msg. Run by git with cwd = the worktree
# root. Enforces the task's `touches` contract at commit time: a file outside the
# contract must be disclosed in the commit body, or the commit is refused. The
# allowance is only a fast-fail — the driver recomputes the same diff from the
# branch after the seat exits, and that is the record.
set -euo pipefail

here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=./factory-lib.sh
# shellcheck disable=SC1091
. "$here/factory-lib.sh"

message_file=$1

# A merge carries main's files; the driver recomputes touches after the seat exits.
if git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
  exit 0
fi

# No .factory-touches contract -> nothing to enforce.
if [ ! -f .factory-touches ]; then
  exit 0
fi

# An unreadable message file -> allow (the driver recomputes after the seat exits).
if [ ! -r "$message_file" ]; then
  printf 'commit-msg: message file unreadable; allowing (the driver recomputes touches after the seat exits)\n' >&2
  exit 0
fi

changed=$(mktemp)
trap 'rm -f -- "$changed"' EXIT
# A git failure (the cwd outside a work tree, GIT_DIR naming no repository, a corrupt index) -> allow; a repo with no commits diffs against the empty tree and takes the normal path.
if ! git diff --cached --name-only >"$changed" 2>/dev/null; then
  printf 'commit-msg: git diff failed; allowing (the driver recomputes touches after the seat exits)\n' >&2
  exit 0
fi

extra=$(factory_touches_extra . .factory-touches HEAD : "$changed")

undisclosed=""
while IFS= read -r path; do
  [ -n "$path" ] || continue
  if ! factory_disclosed "$path" "$message_file"; then
    undisclosed="${undisclosed}${undisclosed:+$'\n'}$path"
  fi
done <<<"$extra"

if [ -z "$undisclosed" ]; then
  exit 0
fi

n=0
while IFS= read -r path; do
  [ -n "$path" ] || continue
  n=$((n + 1))
done <<<"$undisclosed"

printf 'commit-msg: %s file(s) outside this task'"'"'s touches:\n' "$n" >&2
while IFS= read -r path; do
  [ -n "$path" ] || continue
  printf '  %s\n' "$path" >&2
done <<<"$undisclosed"
printf 'Add one line per file to the commit body, exactly this form, then the reason:\n' >&2
while IFS= read -r path; do
  [ -n "$path" ] || continue
  printf 'Deviation: %s — <why this task needs it; say so if an acceptance check needs it (a nix-sandbox copy list in flake.nix, a fixture a bats file reads)>\n' "$path" >&2
done <<<"$undisclosed"
printf 'The driver recomputes this from the branch after you exit; --no-verify does not change the record.\n' >&2
exit 1
