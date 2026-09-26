#!/usr/bin/env bash
# Phase 4a acceptance: the machine's config builds from the repo, and the
# difference against the currently-running system is small and reviewable.
# The actual switch is YOUR step, in docs/runbooks/phase4a-switch.md.
# Run from the repo root: nix develop -c tests/acceptance/phase4a.sh
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

echo "== 1. the whole machine builds from the repo"
if out=$(nix build --no-link --print-out-paths .#nixosConfigurations.core.config.system.build.toplevel); then
  ok "nixosConfigurations.core builds ($out)"
else
  bad "flake build of the system failed"
  echo "== Result: $pass passed, $fail failed"
  echo "PHASE 4A ACCEPTANCE: FAIL"
  exit 1
fi

echo
echo "== 2. delta versus the system you are running right now"
nix store diff-closures /run/current-system "$out" | tee /tmp/phase4a-diff.txt
echo
lines=$(wc -l </tmp/phase4a-diff.txt)
echo "   ($lines change lines — review them above; hostname nixos->core and the"
echo "    claude-code source change are expected, big desktop-stack churn is NOT)"
ok "closure diff produced for operator review"

echo
echo "== 3. /etc/nixos untouched"
if [ -f /etc/nixos/configuration.nix ] && [ -f /etc/nixos/ai-bootstrap.nix ]; then
  ok "fallback config preserved at /etc/nixos"
else
  bad "/etc/nixos files missing"
fi

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "PHASE 4A ACCEPTANCE (build+diff): PASS — the switch itself is your call:"
  echo "  see docs/runbooks/phase4a-switch.md"
else
  echo "PHASE 4A ACCEPTANCE: FAIL"
  exit 1
fi
