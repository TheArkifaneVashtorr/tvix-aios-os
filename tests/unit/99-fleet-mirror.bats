#!/usr/bin/env bats
# tests/unit/99-fleet-mirror.bats -- the mirror script (pkgs/fleet/mirror.sh,
# the ExecStart of the fleet-mirror user unit FL7 renders from
# fleet.mirror) against a PATH fake git standing in for a live push: the
# refspec pair (main and the live-* tags, whole-line compared), the one SSH
# shape (GIT_SSH_COMMAND with the identity and the three pinned options, no
# UserKnownHostsFile override -- the system ssh_known_hosts is this unit's
# trust root), each variable's own refusal, and the failure that propagates.
# The fake covers the protocol the script speaks, not the remote side's own
# behaviour (a real forge, a real pre-push hook over githooks/allowed-
# remotes.txt), the gap named per docs/decisions/2026-09-03-test-based-
# reality-amendments.md; the unit's own rendering is fleet-eval's.

M="$BATS_TEST_DIRNAME/../../pkgs/fleet/mirror.sh"

setup() {
  bats_require_minimum_version 1.5.0
  T="$BATS_TEST_TMPDIR"
  export T
  mkdir -p "$T/bin"
  # The fake is /bin/sh (never #!/usr/bin/env: the unit sandbox has no
  # /usr/bin/env -- the same reason tests/unit/99-fleet.bats' fakes use it).
  cat >"$T/bin/git" <<'EOF'
#!/bin/sh
# fake git: records argv, then GIT_SSH_COMMAND; exits FAKE_GIT_RC.
printf '%s\n' "$*" >>"$T/git.log"
printf 'GIT_SSH_COMMAND=%s\n' "${GIT_SSH_COMMAND:-}" >>"$T/git.log"
exit "${FAKE_GIT_RC:-0}"
EOF
  chmod +x "$T/bin/git"
  export PATH="$T/bin:$PATH"
  # Interface 4's fixture values, so every case below pins the same shape
  # fleet-eval asserts on the rendered unit.
  export FLEET_MIRROR_CHECKOUT='/home/tester/nixos-agent-env'
  export FLEET_MIRROR_URL='ssh://forgejo@forge/operator/nixos-agent-env.git'
  export FLEET_MIRROR_KEY='/home/tester/.ssh/forge-mirror'
}

@test "push: one git call, the two refspecs, the one SSH shape, the success line" {
  run bash "$M"
  [ "$status" -eq 0 ]
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == "fleet-mirror: pushed main and live-* to $FLEET_MIRROR_URL" ]]
  [ "$(grep -c '' "$T/git.log")" -eq 2 ]
  # The push line, compared whole: a partial refspec set (M1) and a
  # different flag like --all (M2) are both rows a substring test would miss.
  [[ "$(sed -n 1p "$T/git.log")" == "-C $FLEET_MIRROR_CHECKOUT push $FLEET_MIRROR_URL refs/heads/main:refs/heads/main refs/tags/live-*:refs/tags/live-*" ]]
  ssh_cmd="$(sed -n 2p "$T/git.log")"
  [[ "$ssh_cmd" == *"ssh -i $FLEET_MIRROR_KEY "* ]]
  [[ "$ssh_cmd" == *"-o IdentitiesOnly=yes"* ]]
  [[ "$ssh_cmd" == *"-o StrictHostKeyChecking=yes"* ]]
  [[ "$ssh_cmd" == *"-o BatchMode=yes"* ]]
  # No UserKnownHostsFile override: /etc/ssh/ssh_known_hosts (the pinned
  # identities the fleet module renders) is this unit's only trust root.
  [[ "$ssh_cmd" != *"UserKnownHostsFile"* ]]
}

@test "FLEET_MIRROR_URL unset or empty is refused with exit 2, no git call" {
  run --separate-stderr env -u FLEET_MIRROR_URL bash "$M"
  [ "$status" -eq 2 ]
  [ "$stderr" = 'fleet-mirror: FLEET_MIRROR_URL is not set' ]
  [ ! -e "$T/git.log" ]
  run --separate-stderr env FLEET_MIRROR_URL= bash "$M"
  [ "$status" -eq 2 ]
  [ "$stderr" = 'fleet-mirror: FLEET_MIRROR_URL is not set' ]
  [ ! -e "$T/git.log" ]
}

@test "FLEET_MIRROR_CHECKOUT unset is refused with exit 2, no git call" {
  run --separate-stderr env -u FLEET_MIRROR_CHECKOUT bash "$M"
  [ "$status" -eq 2 ]
  [ "$stderr" = 'fleet-mirror: FLEET_MIRROR_CHECKOUT is not set' ]
  [ ! -e "$T/git.log" ]
}

@test "FLEET_MIRROR_KEY unset is refused with exit 2, no git call" {
  run --separate-stderr env -u FLEET_MIRROR_KEY bash "$M"
  [ "$status" -eq 2 ]
  [ "$stderr" = 'fleet-mirror: FLEET_MIRROR_KEY is not set' ]
  [ ! -e "$T/git.log" ]
}

@test "a failed push is the script's exit code, never swallowed" {
  run --separate-stderr env FAKE_GIT_RC=1 bash "$M"
  [ "$status" -eq 1 ]
  [[ "$output" != *pushed* ]]
}
