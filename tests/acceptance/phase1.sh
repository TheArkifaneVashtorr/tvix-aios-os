#!/usr/bin/env bash
# Phase 1 acceptance (brief §7): encrypt a basket, decrypt with YubiKey A,
# confirm the tmpfs mount disappears on teardown, confirm decryption fails
# with no key present. Run from the repo root with YubiKey A inserted:
#   nix develop -c tests/acceptance/phase1.sh
set -euo pipefail

work=$(mktemp -d /run/user/"$(id -u)"/basket-acceptance.XXXXXX 2>/dev/null || mktemp -d)
trap 'rm -rf "$work"' EXIT
pass=0
fail=0
step() {
  echo
  echo "== $1"
}
ok() {
  echo "   PASS: $1"
  pass=$((pass + 1))
}
bad() {
  echo "   FAIL: $1"
  fail=$((fail + 1))
}

step "0. YubiKey identity"
if ! age-plugin-yubikey --identity >"$work/identity.txt" 2>/dev/null; then
  echo "No YubiKey identity found. Insert YubiKey A and re-run." >&2
  exit 1
fi
age-plugin-yubikey --list >"$work/recipients.txt"
grep -c '^age1yubikey' "$work/recipients.txt" >/dev/null || {
  echo "No YubiKey recipients listed." >&2
  exit 1
}
ok "YubiKey present, identity and recipients read"

step "1. Encrypt a basket"
mkdir -p "$work/src" "$work/store"
echo "acceptance-secret-$(date +%s)" >"$work/src/proof.txt"
cat >"$work/manifest.json" <<'EOF'
{ "id": "acceptance", "classification": "local-only", "mount": "/data/acceptance", "access": "ro" }
EOF
if basket encrypt "$work/src" --manifest "$work/manifest.json" \
  --recipients "$work/recipients.txt" --store "$work/store"; then
  ok "basket encrypted to store"
else
  bad "encrypt failed"
fi

step "2. Decrypt with YubiKey A into a real tmpfs (sudo; touch the key when it blinks)"
if sudo "$(command -v basket)" mount "$work/store/acceptance" \
  --identity "$work/identity.txt" --runtime-dir /run/baskets --size 16M &&
  sudo cat /run/baskets/acceptance/proof.txt >/dev/null &&
  [ "$(findmnt -no FSTYPE --target /run/baskets/acceptance)" = "tmpfs" ]; then
  ok "decrypted via YubiKey into tmpfs at /run/baskets/acceptance"
else
  bad "mount/decrypt via YubiKey failed"
fi

step "3. Teardown removes the tmpfs"
if sudo "$(command -v basket)" teardown acceptance --runtime-dir /run/baskets &&
  ! mountpoint -q /run/baskets/acceptance; then
  ok "tmpfs mount gone after teardown"
else
  bad "teardown left the mount behind"
fi

step "4. Decryption fails with no key present"
echo "   REMOVE the YubiKey now, then press Enter."
read -r
mkdir -p "$work/out"
if basket decrypt "$work/store/acceptance" --identity "$work/identity.txt" --into "$work/out" 2>/dev/null; then
  bad "decryption succeeded WITHOUT the key — this is a failure"
else
  ok "decryption refused with no key present"
fi

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "PHASE 1 ACCEPTANCE: PASS"
else
  echo "PHASE 1 ACCEPTANCE: FAIL"
  exit 1
fi
