#!/usr/bin/env bash
# FL7 (plan 2026-09-24-fleet-and-forge.md): the mirror script -- the
# ExecStart of the fleet-mirror user unit the fleet module renders from
# fleet.mirror. It pushes main and the live-* tags of the declared checkout
# to the forge over the one SSH shape (the identity the unit names, no
# UserKnownHostsFile override: /etc/ssh/ssh_known_hosts, the pinned
# identities the module writes, is this unit's only trust root). The
# checkout's own pre-push hook (githooks/pre-push over
# githooks/allowed-remotes.txt) runs under the push, so the URL must be
# allowlisted there. git's failure is this script's exit code, never
# swallowed: the unit fails and `systemctl --user status fleet-mirror`
# shows it (Helm does not -- the timers tile audits only what Helm's
# config lists).
set -euo pipefail

if [ -z "${FLEET_MIRROR_CHECKOUT:-}" ]; then
  echo 'fleet-mirror: FLEET_MIRROR_CHECKOUT is not set' >&2
  exit 2
fi
if [ -z "${FLEET_MIRROR_URL:-}" ]; then
  echo 'fleet-mirror: FLEET_MIRROR_URL is not set' >&2
  exit 2
fi
if [ -z "${FLEET_MIRROR_KEY:-}" ]; then
  echo 'fleet-mirror: FLEET_MIRROR_KEY is not set' >&2
  exit 2
fi

export GIT_SSH_COMMAND="ssh -i $FLEET_MIRROR_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -o BatchMode=yes"

git -C "$FLEET_MIRROR_CHECKOUT" push "$FLEET_MIRROR_URL" 'refs/heads/main:refs/heads/main' 'refs/tags/live-*:refs/tags/live-*'

echo "fleet-mirror: pushed main and live-* to $FLEET_MIRROR_URL"
