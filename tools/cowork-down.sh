#!/usr/bin/env bash
# Operator lifecycle: bring Claude Cowork down cleanly -- stop the display
# client and the app, tear down the decrypted basket, confirm no plaintext is
# left behind, and print a summary of what the broker audited this session.
# Usage: nix develop -c tools/cowork-down.sh
set -euo pipefail

basket_id="${COWORK_BASKET:-cowork-workspace}"
broker_instance="${COWORK_BROKER_INSTANCE:-cowork}"
runtime_dir="${COWORK_RUNTIME_DIR:-/run/baskets}"
audit_log="/var/lib/egress-broker/${broker_instance}/audit.jsonl"
mnt="${runtime_dir}/${basket_id}"

echo "== 1. stop the display client"
systemctl --user stop cowork-display 2>/dev/null || true

echo
echo "== 2. stop the cowork service"
sudo systemctl stop cowork

echo
echo "== 3. tear down the ${basket_id} basket"
if mountpoint -q "$mnt" 2>/dev/null; then
  sudo "$(command -v basket)" teardown "$basket_id" --runtime-dir "$runtime_dir"
else
  echo "${mnt} was not mounted -- nothing to tear down"
fi

echo
echo "== 4. confirm no plaintext remains"
if ! basket doctor; then
  echo "cowork-down: basket doctor reports a FAIL after teardown -- investigate before walking away" >&2
  exit 1
fi
echo "basket doctor: all green"

echo
echo "== 5. broker audit summary (${broker_instance})"
if sudo test -e "$audit_log"; then
  sudo jq -r '.verdict' "$audit_log" | sort | uniq -c
else
  echo "no audit log at ${audit_log} yet -- the broker never saw traffic"
fi

echo
echo "cowork is down."
