#!/usr/bin/env bash
# One-time enrollment of a plugged-in YubiKey as a basket unlock key.
# Usage: nix develop -c tools/enroll-yubikey.sh [a|b|c]
set -euo pipefail

letter="${1:-a}"
case "$letter" in
  a | b | c) ;;
  *)
    echo "usage: tools/enroll-yubikey.sh [a|b|c]" >&2
    exit 2
    ;;
esac

# Ledger guard (keys.toml): refuse to enroll a serial already holding another
# role, and warn if this role is already ledgered under a different serial.
ledger="$(dirname "$0")/../keys.toml"
serial=$(ykman list 2>/dev/null | grep -o 'Serial: [0-9]*' | head -1 | cut -d' ' -f2)
if [[ -n "$serial" && -f "$ledger" ]]; then
  existing_role=$(grep -B1 "serial = $serial\$" "$ledger" | grep -o 'keys\.basket-[a-z]*' | cut -d. -f2 || true)
  if [[ -n "$existing_role" && "$existing_role" != "basket-$letter" ]]; then
    echo "REFUSED: connected key serial $serial is already ledgered as '$existing_role'." >&2
    echo "This is not the key you think it is — check keys.toml and the stickers." >&2
    exit 1
  fi
fi

echo "Enrolling the plugged-in YubiKey as basket key '$letter'."
echo "You will be asked for the key's PIN (the one you chose;"
echo "on a factory-fresh key it is 123456), then to touch the key when it blinks."
echo
exec age-plugin-yubikey --generate --name "basket-$letter" \
  --pin-policy once --touch-policy cached
