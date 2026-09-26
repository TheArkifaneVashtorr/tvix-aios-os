#!/usr/bin/env bash
# Operator lifecycle: bring Claude Cowork up. Needs the YubiKey in hand (the
# cowork-workspace basket is decrypted, never mounted at boot) and sudo (the
# tmpfs mount and cowork.service are root operations). The app itself starts
# as the dedicated claude-app user inside the cowork broker's netns.
# Usage: nix develop -c tools/cowork-up.sh
set -euo pipefail

basket_id="${COWORK_BASKET:-cowork-workspace}"
broker_instance="${COWORK_BROKER_INSTANCE:-cowork}"
# Convention (no earlier phase established one): the host-wide encrypted
# basket store, one entry per basket id, populated by `basket encrypt`.
store_dir="${COWORK_STORE_DIR:-/var/lib/baskets/store}"
runtime_dir="${COWORK_RUNTIME_DIR:-/run/baskets}"
mount_size="${COWORK_MOUNT_SIZE:-2G}"
audit_log="/var/lib/egress-broker/${broker_instance}/audit.jsonl"
waypipe_socket="/run/claude-gui/wp.sock"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "== 1. basket doctor (host invariants)"
if ! basket doctor; then
  # The stale-mounts probe rightly flags anything under /run/baskets, but a
  # rerun of cowork-up with our own workspace still mounted is reuse, not a
  # leak. Vouch for exactly that case; any other doctor FAIL stays fatal.
  unexpected=""
  for e in "${runtime_dir}"/* "${runtime_dir}"/.[!.]*; do
    [[ -e "$e" ]] || continue
    b=$(basename "$e")
    if [[ "$b" != "${basket_id}" && "$b" != ".basket-tmpfs-${basket_id}" ]]; then
      unexpected="$unexpected $b"
    fi
  done
  if [[ -z "$unexpected" ]] && mountpoint -q "${runtime_dir}/${basket_id}" 2>/dev/null; then
    echo "cowork-up: only our own workspace is mounted -- treating as reuse, continuing"
  else
    echo "cowork-up: basket doctor reports a FAIL -- fix before bringing Cowork up" >&2
    exit 1
  fi
fi

echo
echo "== 2. mount ${basket_id} (touch the YubiKey when it blinks)"
entry="${store_dir}/${basket_id}"
if [[ ! -d "$entry" ]]; then
  echo "cowork-up: no encrypted store entry at ${entry}" >&2
  echo "  encrypt the workspace basket first: basket encrypt <src> --manifest <m> --recipients <r> --store ${store_dir}" >&2
  exit 1
fi
if mountpoint -q "${runtime_dir}/${basket_id}" 2>/dev/null; then
  echo "already mounted at ${runtime_dir}/${basket_id} -- reusing"
else
  if ! age-plugin-yubikey --identity >"$work/identity.txt" 2>/dev/null; then
    echo "cowork-up: no YubiKey identity found -- insert the key and re-run" >&2
    exit 1
  fi
  sudo "$(command -v basket)" mount "$entry" \
    --identity "$work/identity.txt" --runtime-dir "$runtime_dir" --size "$mount_size"
fi

echo
echo "== 3. start the display relay, then the cowork service"
# Ordering is load-bearing: the waypipe CLIENT (operator session) creates and
# listens on the socket; the confined SERVER connects to it. Server-first dies
# with ENOENT (field bug, first acceptance run 2026-09-02).
# A stale socket file from a killed relay passes a bare -S test while no
# relay listens (field bug 2026-09-02 19:32: EADDRINUSE on the client,
# ECONNREFUSED on the server, app core dump). Only an ACTIVE unit plus the
# socket counts; the unit itself clears a stale file before binding.
systemctl --user start cowork-display
relay_ok=0
for _ in $(seq 1 15); do
  if systemctl --user is-active --quiet cowork-display && [[ -S "$waypipe_socket" ]]; then
    relay_ok=1
    break
  fi
  sleep 1
done
if [[ "$relay_ok" -ne 1 ]]; then
  echo "cowork-up: display relay socket never appeared -- check: journalctl --user -u cowork-display -e" >&2
  exit 1
fi
sudo systemctl start cowork

echo
echo "== 4. wait for the service and the waypipe socket (up to 30s each)"
started=0
for _ in $(seq 1 30); do
  if systemctl is-active --quiet cowork; then
    started=1
    break
  fi
  sleep 1
done
if [[ "$started" -ne 1 ]]; then
  echo "cowork-up: cowork.service did not become active in time -- check: journalctl -u cowork -e" >&2
  exit 1
fi
socket_up=0
for _ in $(seq 1 30); do
  if [[ -S "$waypipe_socket" ]]; then
    socket_up=1
    break
  fi
  sleep 1
done
if [[ "$socket_up" -ne 1 ]]; then
  echo "cowork-up: waypipe socket did not appear at ${waypipe_socket} -- check: journalctl -u cowork -e" >&2
  exit 1
fi
echo "cowork.service active; waypipe socket present at ${waypipe_socket}"

echo
echo "== 5. broker audit log (${broker_instance})"
if sudo test -e "$audit_log"; then
  echo "last entries so far:"
  sudo tail -n 5 "$audit_log"
else
  echo "no entries yet -- watch live with: sudo tail -f ${audit_log}"
fi

echo
echo "cowork is up: the Cowork window should now appear on this desktop."
echo "(display relay was started in step 3 -- it must precede the service)"
