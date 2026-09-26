#!/usr/bin/env bash
# Fake `proton-drive` for tests: serves a remote tree from $MOCK_REMOTE_ROOT,
# logs calls to $MOCK_CALLS. Only the subcommands proton-backup-push uses.
set -euo pipefail
root="${MOCK_REMOTE_ROOT:?}"
echo "$*" >>"${MOCK_CALLS:?}"
cmd="$1 $2"
shift 2
case "$cmd" in
  "filesystem info")
    # <path> --json
    [ -e "$root$1" ] || exit 1
    echo '{"type":"folder"}'
    ;;
  "filesystem create-folder")
    # <parent> <name>
    mkdir -p "$root$1/$2"
    ;;
  "filesystem upload")
    # -t -f skip -d merge <local...> <remoteParent>
    shift 5
    args=("$@")
    dest="${args[-1]}"
    unset 'args[-1]'
    [ "${MOCK_UPLOAD_NOOP:-0}" = "1" ] && exit 0
    for src in "${args[@]}"; do
      if [ -d "$src" ]; then
        mkdir -p "$root$dest/$(basename "$src")"
        while IFS= read -r f; do
          t="$root$dest/$(basename "$src")/$f"
          [ -e "$t" ] || {
            mkdir -p "$(dirname "$t")"
            cp "$src/$f" "$t"
          }
        done < <(cd "$src" && find . -type f | sed 's|^\./||')
      else
        t="$root$dest/$(basename "$src")"
        [ -e "$t" ] || cp "$src" "$t"
      fi
    done
    ;;
  "filesystem list")
    # -t file <path> --json
    dir="$root$3"
    printf '['
    sep=''
    for f in "$dir"/*; do
      [ -f "$f" ] || continue
      printf '%s{"name":{"ok":true,"value":"%s"}}' "$sep" "$(basename "$f")"
      sep=','
    done
    printf ']\n'
    ;;
  "filesystem trash")
    # <path...>: real CLI moves my-files items into a flat-by-name trash;
    # a trashed item is then addressed as /trash/<basename>.
    for p in "$@"; do
      src="$root$p"
      [ -e "$src" ] || continue
      mkdir -p "$root/trash"
      mv "$src" "$root/trash/$(basename "$p")"
    done
    ;;
  "filesystem delete")
    # <path...>: real CLI (SUPPORTED_PATH_TYPES = [Trash, PhotosTrash]) only
    # permanently deletes items already in trash, addressed /trash/<name>.
    for p in "$@"; do
      case "$p" in
        /trash/*) rm -f "$root$p" ;;
        *)
          echo "mock: filesystem delete only accepts /trash/<name> paths (got $p)" >&2
          exit 1
          ;;
      esac
    done
    ;;
  *)
    echo "mock: unsupported $cmd" >&2
    exit 99
    ;;
esac
