#!/usr/bin/env bash
# helm-open-workspace — open a terminal in a named workspace.
#
# Template file: nixosModules/helm.nix substitutes @WORKSPACES_JSON_FILE@ (the
# absolute store path of control.workspaces serialised with pkgs.formats.json
# as {"<name>": {"path": ..., "devShell": "default"|null, "basket": null|"<id>",
# "command": null|"<cmd>"}}). The launcher reads that file instead of carrying
# the JSON as a shell literal, so no operator-authored workspace value is ever
# spliced into shell syntax (a single quote in a value cannot break out).
# Generated per host, so the names are baked in and never looked up at
# runtime: an unknown name exits 2 before anything else happens.
#
# The launcher never mounts baskets (K13: the YubiKey ceremony stays human,
# in the terminal, in front of the operator). For a basket-gated workspace
# whose basket is not mounted it prints the one command that mounts it —
# following tools/cowork-up.sh's established ceremony (materialise the
# YubiKey identity, then mount from the blessed store) — and waits for
# Enter. The prompt copy is the product decisions deck, verbatim (K15).
set -euo pipefail

readonly WORKSPACES_JSON_FILE='@WORKSPACES_JSON_FILE@'
readonly BASKET_STORE=/var/lib/baskets/store
readonly BASKET_RUNTIME_DIR=/run/baskets

err() {
  echo "helm-open-workspace: $*" >&2
}

name=${1:-}

if [[ -z $name ]]; then
  err "usage: helm-open-workspace <name>"
  exit 2
fi

if ! jq -e --arg name "$name" 'has($name)' "$WORKSPACES_JSON_FILE" >/dev/null; then
  err "unknown workspace: $name"
  exit 2
fi

path=$(jq -r --arg name "$name" '.[$name].path' "$WORKSPACES_JSON_FILE")
devshell=$(jq -r --arg name "$name" '.[$name].devShell // ""' "$WORKSPACES_JSON_FILE")
basket=$(jq -r --arg name "$name" '.[$name].basket // ""' "$WORKSPACES_JSON_FILE")
cmd=$(jq -r --arg name "$name" '.[$name].command // ""' "$WORKSPACES_JSON_FILE")

if [[ -n $basket ]] && ! mountpoint -q "$BASKET_RUNTIME_DIR/$basket"; then
  # Resolve basket now, while the operator's PATH still applies: sudo's root
  # shell may not see the system profile (same reasoning as cowork-up.sh).
  basket_bin=$(command -v basket || echo basket)
  echo "This workspace needs its basket. Run:"
  echo "sudo sh -c 'umask 077 && age-plugin-yubikey --identity >/tmp/helm-basket-identity && exec $basket_bin mount $BASKET_STORE/$basket --identity /tmp/helm-basket-identity'"
  echo "…then press Enter."
  read -r
fi

cd "$path"

# bash/nix are the ABSOLUTE paths baked in by nixosModules/helm.nix (same
# reason kgx_bin/helm_open_workspace_bin are absolute): the terminal
# systemd-run --user spawns inherits the user manager's PATH, which lacks
# /run/current-system/sw/bin, so bare names here would be "command not found"
# and the window would close before the operator gets a shell (field bug
# 2026-09-04).
#
# Default: leave the operator at an interactive shell, in the workspace's
# dev shell when one is declared. A workspace that sets its `command` option
# instead runs that program (e.g. "claude" or "dsh-openrouter").
if [[ -z $devshell ]]; then
  if [[ -n $cmd ]]; then
    exec "@BASH_BIN@" -ic "$cmd"
  fi
  exec "@BASH_BIN@" -i
fi
if [[ -n $cmd ]]; then
  exec "@NIX_BIN@" develop ".#$devshell" -c "@BASH_BIN@" -ic "$cmd"
fi
exec "@NIX_BIN@" develop ".#$devshell" -c "@BASH_BIN@" -i
