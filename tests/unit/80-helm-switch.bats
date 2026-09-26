#!/usr/bin/env bats
# helm-switch (pkgs/helm/helm-switch.sh, a template whose @PROFILES@ and
# @MARKER@ the Helm module substitutes — D1 keeps the allowlist a fixed
# literal, so every toplevel bakes the same script). These tests do the
# substitution the way nixosModules/helm.nix will and drive the script
# against a stub root through the HELM_SWITCH_ROOT_OVERRIDE test seam.
#
# Every test sets the override: on the machine running the devShell,
# /nix/var/nix/profiles/system/bin/switch-to-configuration is the REAL
# activation binary, and no test may execute it (build-only; the live switch
# is the operator's, the VM test owns the real thing). The ROOT preference
# itself (/nix/var/nix/profiles/system, else /run/booted-system — a stage-2
# boot has no profile generation yet) is proven by the VM test, which logs
# the chosen root; here it is only reachable through the seam.
#
# Shown to fail first (2026-09-03): the template did not exist, sed
# produced an empty script, and every case below failed.

TEMPLATE="$BATS_TEST_DIRNAME/../../pkgs/helm/helm-switch.sh"

setup() {
  # run -N (expected exit code) needs bats >= 1.5; declare it so the BW02
  # heuristic stays quiet.
  bats_require_minimum_version 1.5.0
  REAL_BASH=$(command -v bash)
  ROOT="$BATS_TEST_TMPDIR/root"
  MARKER="$BATS_TEST_TMPDIR/marker"
  SCRIPT="$BATS_TEST_TMPDIR/helm-switch"
  mkdir -p "$ROOT/bin" "$ROOT/specialisation/alt/bin"
  write_stub "$ROOT/bin/switch-to-configuration" base
  write_stub "$ROOT/specialisation/alt/bin/switch-to-configuration" alt
  printf 'base\n' >"$MARKER"
  sed -e "s|@PROFILES@|base alt|" -e "s|@MARKER@|$MARKER|" "$TEMPLATE" >"$SCRIPT"
}

# $1: stub path, $2: label the stub prints so tests can tell which one ran.
# A "<stub>.exit" file next to the stub makes it exit with that code, so the
# exit-code propagation tests do not need a second stub flavour.
write_stub() {
  {
    echo "#!$REAL_BASH"
    echo "echo \"$2-stub: \$*\""
    echo 'if [[ -f "$0.exit" ]]; then exit "$(cat "$0.exit")"; fi'
  } >"$1"
  chmod +x "$1"
}

@test "a name outside ^[a-z][a-z0-9-]{0,31}\$ is rejected before anything runs" {
  for bad in '../x' 'gaming;reboot' 'BASE' 'a_b' 'x/../../etc'; do
    HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT" "$bad"
    [ "$status" -eq 2 ]
    [[ "$output" == *"invalid profile name"* ]]
    [[ "$output" != *"stub:"* ]]
    [[ "$output" != *"helm-switch: begin"* ]]
  done
}

@test "no argument at all is rejected with exit 2" {
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT"
  [ "$status" -eq 2 ]
  [[ "$output" == *"invalid profile name"* ]]
  [[ "$output" != *"stub:"* ]]
}

@test "the 33rd character of a name is rejected by the shape gate, not the allowlist" {
  long=$(printf 'a%.0s' $(seq 1 33))
  [ "${#long}" -eq 33 ]
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT" "$long"
  [ "$status" -eq 2 ]
  [[ "$output" == *"invalid profile name"* ]]
}

@test "a well-formed name that is not in the allowlist is rejected (exit 2, nothing runs)" {
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT" nope
  [ "$status" -eq 2 ]
  [[ "$output" == *"not in allowlist"* ]]
  [[ "$output" != *"stub:"* ]]
  [[ "$output" != *"helm-switch: begin"* ]]
}

@test "a substring of an allowed name is not allowed (no naive substring matching)" {
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT" ase
  [ "$status" -eq 2 ]
  [[ "$output" == *"not in allowlist"* ]]
}

@test "a 32-character well-formed name reaches the allowlist gate (bound is inclusive)" {
  long=$(printf 'a%.0s' $(seq 1 32))
  [ "${#long}" -eq 32 ]
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT" "$long"
  [ "$status" -eq 2 ]
  [[ "$output" == *"not in allowlist"* ]]
}

@test "base runs \$ROOT/bin/switch-to-configuration with the test action and audits begin/end" {
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT" base
  [ "$status" -eq 0 ]
  [[ "$output" == *"base-stub: test"* ]]
  [[ "$output" != *"alt-stub:"* ]]
  [[ "$output" == *"helm-switch: begin base -> base root=$ROOT"* ]]
  [[ "$output" == *"helm-switch: end base exit=0"* ]]
}

@test "a missing marker reads as unknown in the begin line" {
  rm "$MARKER"
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT" base
  [ "$status" -eq 0 ]
  [[ "$output" == *"helm-switch: begin unknown -> base root=$ROOT"* ]]
}

@test "a named profile runs its specialisation binary with the test action" {
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT" alt
  [ "$status" -eq 0 ]
  [[ "$output" == *"alt-stub: test"* ]]
  [[ "$output" != *"base-stub:"* ]]
  [[ "$output" == *"helm-switch: begin base -> alt root=$ROOT"* ]]
  [[ "$output" == *"helm-switch: end alt exit=0"* ]]
}

@test "the activation binary's exit code is propagated in the end line and as the script exit" {
  echo 7 >"$ROOT/specialisation/alt/bin/switch-to-configuration.exit"
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run "$REAL_BASH" "$SCRIPT" alt
  [ "$status" -eq 7 ]
  [[ "$output" == *"alt-stub: test"* ]]
  [[ "$output" == *"helm-switch: end alt exit=7"* ]]
}

@test "fail closed: a missing specialisation binary executes NOTHING and still closes the audit pair" {
  rm "$ROOT/specialisation/alt/bin/switch-to-configuration"
  # run -127: the expected exit code is 127 by design (missing binary), not
  # an accidental "command not found" — declaring it also silences bats' BW01.
  HELM_SWITCH_ROOT_OVERRIDE=$ROOT run -127 "$REAL_BASH" "$SCRIPT" alt
  [ "$status" -eq 127 ]
  [[ "$output" != *"stub:"* ]]
  [[ "$output" == *"helm-switch: begin base -> alt root=$ROOT"* ]]
  [[ "$output" == *"helm-switch: end alt exit=127"* ]]
  [[ "$output" == *"missing activation binary"* ]]
}

@test "fail closed: a root without the base binary executes NOTHING" {
  empty="$BATS_TEST_TMPDIR/empty-root"
  mkdir -p "$empty"
  HELM_SWITCH_ROOT_OVERRIDE=$empty run -127 "$REAL_BASH" "$SCRIPT" base
  [ "$status" -eq 127 ]
  [[ "$output" != *"stub:"* ]]
  [[ "$output" == *"helm-switch: end base exit=127"* ]]
  [[ "$output" == *"missing activation binary"* ]]
}
