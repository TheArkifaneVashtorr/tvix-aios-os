#!/usr/bin/env bash
# Phase 3 acceptance (brief §7): a config mounting a local-only basket into a
# network-capable agent fails the build with a clear error; a correct config
# builds; basket doctor reports live host invariants.
# Run from the repo root: nix develop -c tests/acceptance/phase3.sh
set -euo pipefail

pass=0
fail=0
ok() {
  echo "   PASS: $1"
  pass=$((pass + 1))
}
bad() {
  echo "   FAIL: $1"
  fail=$((fail + 1))
}

echo "== 1. a correct config builds"
if nix build --no-link .#checks.x86_64-linux.assertion-positive; then
  ok "config with local-only basket on an offline agent evaluates and builds"
else
  bad "the known-good config failed to build"
fi

echo
echo "== 2. the forbidden config REFUSES to build, with a clear error"
set +e
err=$(nix build --no-link \
  .#phase3NegativeDemo.config.system.build.toplevel 2>&1)
status=$?
set -e
if [[ "$status" -ne 0 && "$err" == *"local-only"* && "$err" == *"leaky"* && "$err" == *"notes-local"* ]]; then
  ok "build failed and the error names the agent, the basket, and the rule"
  echo "--- the error an operator sees:"
  grep -A2 "local-only" <<<"$err" | head -5
else
  bad "expected a failing build naming agent/basket/rule; status=$status"
  echo "$err" | tail -5
fi

echo
echo "== 3. basket doctor on this host"
if basket doctor; then
  ok "doctor probes all green (WARNs acceptable)"
else
  bad "doctor reports a FAILing invariant on this host"
fi

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "PHASE 3 ACCEPTANCE: PASS"
else
  echo "PHASE 3 ACCEPTANCE: FAIL"
  exit 1
fi
