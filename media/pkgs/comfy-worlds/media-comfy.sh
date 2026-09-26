#!/usr/bin/env bash
# media-comfy: the operator's switch between worlds. Reads the worlds from the
# JSON the module renders (COMFY_WORLDS_JSON, default /etc/comfy-worlds.json)
# and drives the per-user systemctl:
#   media-comfy <world>   -> systemctl --user start comfy-world-<world>.target
#   media-comfy stop      -> systemctl --user stop comfyui-<every>.service
#   media-comfy status    -> one line per world (generator state, comfyPort),
#                            then one feed line (the one feed server, feedPort)
# Never start both targets in one command: their generators conflict and
# systemd refuses the transaction.
set -euo pipefail

json="${COMFY_WORLDS_JSON:-/etc/comfy-worlds.json}"
cmd="${1:-}"

names="$(jq -r '.worlds | keys_unsorted | join(" ")' "$json")"

world_in() {
  local w="$1"
  local n
  for n in $names; do
    [ "$n" = "$w" ] && return 0
  done
  return 1
}

fail_unknown() {
  echo "media-comfy: unknown world '$1'; worlds: $names" >&2
  exit 2
}

case "$cmd" in
  stop)
    args=()
    for n in $names; do
      args+=("comfyui-$n.service")
    done
    systemctl --user stop "${args[@]}"
    ;;
  status)
    for n in $names; do
      gen="$(systemctl --user is-active "comfyui-$n" || true)"
      [ -n "$gen" ] || gen="inactive"
      comfy_port="$(jq -r ".worlds[\"$n\"].comfyPort" "$json")"
      echo "$n: generator $gen, :$comfy_port"
    done
    feed_state="$(systemctl --user is-active "comfy-feed" || true)"
    [ -n "$feed_state" ] || feed_state="inactive"
    feed_port="$(jq -r '.feedPort' "$json")"
    echo "feed: $feed_state, :$feed_port"
    ;;
  *)
    if [ -z "$cmd" ]; then
      echo "media-comfy: usage: media-comfy <world>|stop|status; worlds: $names" >&2
      exit 2
    fi
    if world_in "$cmd"; then
      systemctl --user start "comfy-world-$cmd.target"
    else
      fail_unknown "$cmd"
    fi
    ;;
esac
