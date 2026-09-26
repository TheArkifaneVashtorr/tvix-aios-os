#!/usr/bin/env bash
# comfy-worlds-init: build the tree a ComfyUI "world" lives in — a
# content-addressed store plus, per world, the base dirs ComfyUI needs and a
# git "lab" that holds prompts and the ComfyUI user dir. Idempotent. Adopts an
# existing single-directory ComfyUI tree only when --adopt names the world, so
# a plain init can never silently leave the operator's files stranded at the
# root next to freshly-created empty worlds.
set -euo pipefail

root="$HOME/comfyui"
worlds="sfw,nsfw"
adopt=""

while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      root="${2:?comfy-worlds-init: --root needs a value}"
      shift 2
      ;;
    --adopt)
      adopt="${2:?comfy-worlds-init: --adopt needs a world name}"
      shift 2
      ;;
    --worlds)
      worlds="${2:?comfy-worlds-init: --worlds needs a comma-separated list}"
      shift 2
      ;;
    *)
      echo "comfy-worlds-init: unknown option: $1" >&2
      exit 2
      ;;
  esac
done
worlds="${worlds//,/ }"

# --adopt must name a world we are about to build; a world outside --worlds has
# no placeholder dir to move into and would die on a raw mv error.
if [ -n "$adopt" ]; then
  case " $worlds " in
    *" $adopt "*) ;;
    *)
      echo "comfy-worlds-init: --adopt $adopt: not one of: $worlds" >&2
      exit 2
      ;;
  esac
fi

# default.nix exports FETCH_PY (the flake-substituted store path); tests
# override it via the environment. Only the --adopt path needs it.
: "${FETCH_PY:=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/media-fetch/fetch.py}"

# Without --adopt, existing ComfyUI content at the root is a refusal, not a
# silent no-op: init must not build empty worlds around an install it would
# then leave in place at the root.
if [ -z "$adopt" ]; then
  for d in output input user custom_nodes models; do
    if [ -e "$root/$d" ]; then
      echo "comfy-worlds-init: existing content at $root: pass --adopt <world> to move it" >&2
      exit 1
    fi
  done
fi

mkdir -p "$root/store"

for w in $worlds; do
  wdir="$root/worlds/$w"
  lab="$wdir/lab"
  mkdir -p \
    "$wdir/custom_nodes" \
    "$wdir/input" \
    "$wdir/output" \
    "$wdir/temp" \
    "$wdir/models" \
    "$lab/prompts" \
    "$lab/user"

  # The ComfyUI user dir lives under the lab (so it's versioned with the
  # world); worlds/<w>/user is a relative symlink to it for ComfyUI.
  if [ ! -e "$wdir/user" ]; then
    ln -s lab/user "$wdir/user"
  fi

  if [ ! -e "$lab/manifest.toml" ]; then
    printf '# models of world %s\n' "$w" >"$lab/manifest.toml"
  fi

  if [ ! -e "$lab/README.md" ]; then
    printf '# %s world\n' "$w" >"$lab/README.md"
  fi

  if [ ! -d "$lab/.git" ]; then
    git -C "$lab" init -q
  fi
done

if [ -n "$adopt" ]; then
  w="$adopt"
  wdir="$root/worlds/$w"
  lab="$wdir/lab"

  # Move the four ComfyUI top-level dirs into the world (the user dir goes
  # under the lab, where the symlink already points). init created empty
  # placeholders, so drop each one before moving the real dir into place.
  for d in output input custom_nodes; do
    if [ -e "$root/$d" ]; then
      if [ -d "$wdir/$d" ]; then
        rmdir "$wdir/$d"
      fi
      mv "$root/$d" "$wdir/$d"
      echo "MOVE $d -> worlds/$w/$d"
    fi
  done

  if [ -e "$root/user" ]; then
    if [ -d "$lab/user" ]; then
      rmdir "$lab/user"
    fi
    mv "$root/user" "$lab/user"
    echo "MOVE user -> worlds/$w/lab/user"
  fi

  # Adopt the models into the store and link them into this world's models
  # dir. The fetcher writes a fresh manifest and refuses if one exists, so
  # drop the empty header init just wrote for the adopted world.
  if [ -e "$root/models" ]; then
    rm -f "$lab/manifest.toml"
    python3 "$FETCH_PY" \
      --adopt-from "$root/models" \
      --store "$root/store" \
      --link-into "$wdir/models" \
      --manifest-out "$lab/manifest.toml"
    # The fetcher moved every file into the store, leaving only empty dirs;
    # drop the emptied $root/models tree so nothing sits unadopted at the root.
    find "$root/models" -depth -type d -empty -delete
  fi
fi
