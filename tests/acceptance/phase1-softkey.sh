#!/usr/bin/env bash
# Phase 1 acceptance — software-key variant (operator directive 2026-09-02:
# hardware YubiKey not required). Same brief §7 substance, no hardware, no sudo:
# encrypt a basket, decrypt with the operator identity, confirm the tmpfs mount
# disappears on teardown, confirm decryption fails when the right key is absent.
# tmpfs steps run unprivileged in a user namespace. Run from the repo root:
#   nix develop -c tests/acceptance/phase1-softkey.sh
set -euo pipefail

identity="${BASKET_IDENTITY:-$HOME/.config/basket/identity-core.txt}"
work=$(mktemp -d)
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

step "0. Operator identity (software age key)"
if [[ ! -f "$identity" ]]; then
  mkdir -p "$(dirname "$identity")"
  (
    umask 077
    age-keygen -o "$identity" 2>/dev/null
  )
  echo "   generated new identity at $identity (keep this file; it decrypts your baskets)"
fi
age-keygen -y "$identity" >"$work/recipients.txt"
ok "identity present, recipient derived"

step "1. Encrypt a basket"
mkdir -p "$work/src" "$work/store"
echo "acceptance-secret-$RANDOM" >"$work/src/proof.txt"
cat >"$work/manifest.json" <<'EOF'
{ "id": "acceptance", "classification": "local-only", "mount": "/data/acceptance", "access": "ro" }
EOF
if basket encrypt "$work/src" --manifest "$work/manifest.json" \
  --recipients "$work/recipients.txt" --store "$work/store"; then
  ok "basket encrypted to store"
else
  bad "encrypt failed"
fi

step "2+3. Decrypt into tmpfs, verify, tear down (user namespace)"
cat >"$work/inner.sh" <<EOF
set -euo pipefail
mkdir -p "$work/run"
basket mount "$work/store/acceptance" --identity "$identity" \
  --runtime-dir "$work/run" --size 16M
[ "\$(cat "$work/run/acceptance/proof.txt")" = "\$(cat "$work/src/proof.txt")" ]
[ "\$(findmnt -no FSTYPE --target "$work/run/acceptance")" = "tmpfs" ]
basket teardown acceptance --runtime-dir "$work/run"
if mountpoint -q "$work/run/acceptance" 2>/dev/null; then
  exit 1
fi
[ ! -e "$work/run/acceptance/proof.txt" ]
EOF
if unshare --user --map-root-user --mount bash "$work/inner.sh"; then
  ok "decrypted into tmpfs, content verified, mount gone after teardown"
else
  bad "tmpfs mount/teardown cycle failed"
fi

step "4. Decryption fails when the right key is absent"
age-keygen -o "$work/wrong.txt" 2>/dev/null
mkdir -p "$work/out"
if basket decrypt "$work/store/acceptance" --identity "$work/wrong.txt" \
  --into "$work/out" 2>/dev/null; then
  bad "decryption succeeded WITHOUT the right key — this is a failure"
else
  ok "decryption refused without the right key"
fi

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "PHASE 1 ACCEPTANCE (softkey): PASS"
else
  echo "PHASE 1 ACCEPTANCE (softkey): FAIL"
  exit 1
fi
