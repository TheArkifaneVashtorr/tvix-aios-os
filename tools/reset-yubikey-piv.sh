#!/usr/bin/env bash
# Factory-resets ONLY the encryption (PIV) module of the plugged-in YubiKey —
# run this only when that module is verified empty — then walks through setting
# a new PIN and recovery code, and enrolls the key as a basket unlock key.
# The key's normal 2FA/login functions are NOT affected by any of this.
# Usage: nix develop -c tools/reset-yubikey-piv.sh [a|b|c]
set -euo pipefail

letter="${1:-a}"

echo "Step 1/4 — reset the (empty) encryption module. Type y to confirm."
ykman piv reset

echo
echo "Step 2/4 — choose your new PIN (6-8 digits; you'll type it when unlocking baskets)."
ykman piv access change-pin --pin 123456

echo
echo "Step 3/4 — choose a recovery code (PUK, 8 digits)."
echo "WRITE IT DOWN somewhere safe — it rescues the key if the PIN is ever forgotten."
ykman piv access change-puk --puk 12345678

echo
echo "Step 4/4 — enroll the key (enter your NEW PIN, then touch the key)."
exec "$(dirname "$0")/enroll-yubikey.sh" "$letter"
