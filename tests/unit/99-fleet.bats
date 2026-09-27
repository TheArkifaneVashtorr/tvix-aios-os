#!/usr/bin/env bats
# tests/unit/99-fleet.bats -- the fleet command (pkgs/fleet/fleet.py) against
# PATH fakes standing in for a live forge: ssh, ssh-keyscan, ssh-keygen and
# nix. The fakes cover the protocol fleet speaks -- the one SSH option shape,
# the command order, the known_hosts pin, the canonical JSON writer, the
# exit-code contract -- and not the remote side's own behaviour (a real sshd,
# a real store copy, a real switch), which is fleet-vm's to exercise (FL6),
# the gap named per docs/decisions/2026-09-03-test-based-reality-amendments.md.

FLEET_PY="$BATS_TEST_DIRNAME/../../pkgs/fleet/fleet.py"
REPO_ROOT="$BATS_TEST_DIRNAME/../.."
HOST_KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILI+XsoX/3cLjEKKe/6FuKD91bemmU/of1raCjTOMQOB'
FINGERPRINT='SHA256:5A87i/oxDPw4fPiu3miWBatyv19yGznNAMKgl6uJLGM'

write_fakes() {
  # All four fakes are /bin/sh (never #!/usr/bin/env: the unit sandbox has
  # no /usr/bin/env -- the same reason the flake patches tests/mocks).
  cat >"$T/bin/ssh" <<'SSHEOF'
#!/bin/sh
# fake ssh: records argv, mirrors the known_hosts pin, dispatches remote
# commands by their exact text (the last argv element, after --).
printf '%s\n' "$*" >>"$T/ssh.log"
printf 'ssh: %s\n' "$*" >>"$T/order.log"
for a in "$@"; do
  case "$a" in
    UserKnownHostsFile=*) cp "${a#UserKnownHostsFile=}" "$T/kh.copy" ;;
  esac
done
if [ "${FAKE_SSH_FAIL:-}" = hostkey ]; then
  echo 'Host key verification failed.' >&2
  exit 255
fi
if [ "${FAKE_SSH_FAIL:-}" = denied ]; then
  echo 'Permission denied (publickey).' >&2
  exit 255
fi
case " $* " in
  *" -O exit "*) exit 0 ;;
esac
for cmd in "$@"; do
  :
done
case "$cmd" in
  'readlink -f /run/current-system')
    cat "$T/current"
    ;;
  'sudo -n /run/current-system/sw/bin/nixos-generate-config --show-hardware-config')
    cat "$T/hw.nix"
    ;;
  'ip -o -4 addr show to 192.0.2.10/32')
    printf '2: eth1    inet 192.0.2.10/24 brd 192.0.2.255 scope global eth1\\       valid_lft forever preferred_lft forever\n'
    ;;
  'ip -4 route show default')
    printf 'default via 192.0.2.1 dev eth1 proto dhcp src 192.0.2.10 metric 1002\n'
    ;;
  'cat /etc/resolv.conf')
    printf 'nameserver 192.0.2.1\n'
    ;;
  'test -d /sys/firmware/efi && echo efi || echo bios')
    echo efi
    ;;
  "grep -o 'system.stateVersion = \"[0-9.]*\"' /etc/nixos/configuration.nix")
    if [ -n "${FAKE_NO_STATEVERSION:-}" ]; then
      exit 1
    fi
    printf 'system.stateVersion = "25.11"\n'
    ;;
  'sudo -n /run/current-system/sw/bin/nix-env --profile '*)
    printf 'nix-env: %s\n' "$cmd" >>"$T/remote.log"
    ;;
  'sudo -n '*'/bin/switch-to-configuration switch')
    printf 'switch: %s\n' "$cmd" >>"$T/remote.log"
    if [ -n "${FAKE_SWITCH_FAIL:-}" ]; then
      exit 1
    fi
    if [ -z "${FAKE_NO_SWITCH:-}" ]; then
      tl=${cmd#sudo -n }
      printf '%s\n' "${tl%/bin/switch-to-configuration switch}" >"$T/current"
    fi
    ;;
esac
SSHEOF
  cat >"$T/bin/ssh-keyscan" <<'SCANEOF'
#!/bin/sh
# fake ssh-keyscan: one ed25519 line, nothing under FAKE_SCAN_EMPTY, an
# ssh-rsa line only under FAKE_SCAN_RSA.
printf '%s\n' "$*" >>"$T/scan.log"
if [ -n "${FAKE_SCAN_EMPTY:-}" ]; then
  exit 0
fi
if [ -n "${FAKE_SCAN_RSA:-}" ]; then
  printf '192.0.2.10 ssh-rsa AAAAB3\n'
  exit 0
fi
printf '192.0.2.10 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILI+XsoX/3cLjEKKe/6FuKD91bemmU/of1raCjTOMQOB\n'
SCANEOF
  cat >"$T/bin/ssh-keygen" <<'KEYGENEOF'
#!/bin/sh
# fake ssh-keygen: -lf F prints the fixture host key's real fingerprint (F23).
case "$1" in
  -lf*) printf '256 SHA256:5A87i/oxDPw4fPiu3miWBatyv19yGznNAMKgl6uJLGM 192.0.2.10 (ED25519)\n' ;;
esac
KEYGENEOF
  cat >"$T/bin/nix" <<'NIXEOF'
#!/bin/sh
# fake nix: records argv and NIX_SSHOPTS; build prints the new system,
# path-info answers only for FAKE_LOCAL_PREVIOUS, diff-closures echoes.
printf '%s :: NIX_SSHOPTS=%s\n' "$*" "${NIX_SSHOPTS:-}" >>"$T/nix.log"
printf 'nix: %s\n' "$*" >>"$T/order.log"
case "$1" in
  build)
    printf '/nix/store/aaaa-nixos-system-forge-1\n'
    ;;
  path-info)
    [ "$2" = "${FAKE_LOCAL_PREVIOUS:-}" ]
    ;;
  copy)
    exit 0
    ;;
  store)
    if [ "$2" = diff-closures ]; then
      printf '<<diff %s %s>>\n' "$3" "$4"
    fi
    ;;
esac
NIXEOF
  chmod +x "$T/bin/ssh" "$T/bin/ssh-keyscan" "$T/bin/ssh-keygen" "$T/bin/nix"
}

# The enrolment cases run against a repo with no forge entry, lan = null and
# no hosts/forge: what the operator's tree looks like before the first enrol.
strip_forge() {
  jq 'del(.machines.forge) | .lan = null' hosts/fleet.json >"$T/stripped.json"
  mv "$T/stripped.json" hosts/fleet.json
  rm -rf hosts/forge
}

setup() {
  bats_require_minimum_version 1.5.0
  T="$BATS_TEST_TMPDIR"
  export T
  mkdir -p "$T/repo/hosts/core" "$T/repo/hosts/forge" "$T/bin" "$T/sys/bin" "$T/nopython"
  # The fixture declaration, Interface 1's grammar. The key order is
  # deliberately NOT the canonical dump's (machines, deployKeys, lan): the
  # keys-add case's cmp against python's sort_keys re-dump must really
  # discriminate the writer's sort_keys, not compare the fixture to itself.
  cat >"$T/repo/hosts/fleet.json" <<'EOF'
{
  "machines": {
    "core": {
      "roles": [
        "operator"
      ]
    },
    "forge": {
      "roles": [
        "forge"
      ],
      "address": "192.0.2.10",
      "prefix": 24,
      "interface": "eth1",
      "hostKey": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILI+XsoX/3cLjEKKe/6FuKD91bemmU/of1raCjTOMQOB",
      "efi": true,
      "stateVersion": "25.11"
    }
  },
  "deployKeys": [
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIBsCvg7ed6UUs7JOwbF9jJQiMok+UFpdq0ZcRRP6jzbf fleet-fixture-deploy"
  ],
  "lan": {
    "subnet": "192.0.2.0/24",
    "gateway": "192.0.2.1",
    "nameservers": [
      "192.0.2.1"
    ]
  }
}
EOF
  printf '# core hardware, three lines\nsecond line\nthird line\n' >"$T/repo/hosts/core/hardware-configuration.nix"
  printf '# Do not modify this file! (fixture)\n_: { }\n' >"$T/repo/hosts/forge/hardware-configuration.nix"
  printf '# Do not modify this file! (fixture)\n_: { }\n' >"$T/hw.nix"
  (
    cd "$T/repo"
    sha256sum hosts/*/hardware-configuration.nix >hosts/hardware-pins.sha256
  )
  printf 'identity bytes\n' >"$T/id"
  printf '#!/bin/sh\nexit 0\n' >"$T/sys/bin/switch-to-configuration"
  chmod +x "$T/sys/bin/switch-to-configuration"
  printf '/nix/store/bbbb-nixos-system-forge-0\n' >"$T/current"
  write_fakes
  # A PATH with bash, dirname and coreutils but no python3, for the shim case.
  for tool in bash dirname cat ls cp mv rm; do
    ln -s "$(command -v "$tool")" "$T/nopython/$tool"
  done
  export PATH="$T/bin:$PATH"
  cd "$T/repo"
}

@test "deploy forge: the one ssh shape, ordered steps, the pin, exit 0" {
  run --separate-stderr python3 "$FLEET_PY" deploy forge --identity "$T/id"
  [ "$status" -eq 0 ]
  [[ "$output" == *"fleet: deployed forge /nix/store/aaaa-nixos-system-forge-1"* ]]
  [[ "$output" == *"fleet: previous: /nix/store/bbbb-nixos-system-forge-0"* ]]
  [[ "$output" == *"fleet: deploy: diff-closures: the machine's current system /nix/store/bbbb-nixos-system-forge-0 is not in the local store; skipped"* ]]
  grep -q -- '-o UserKnownHostsFile=' "$T/ssh.log"
  grep -q -- '-o GlobalKnownHostsFile=/dev/null' "$T/ssh.log"
  grep -q -- '-o StrictHostKeyChecking=yes' "$T/ssh.log"
  grep -q -- '-o IdentitiesOnly=yes' "$T/ssh.log"
  grep -qF -- "-i $T/id" "$T/ssh.log"
  grep -q -- '-o ControlMaster=auto' "$T/ssh.log"
  [ "$(cat "$T/kh.copy")" = "forge,192.0.2.10 $HOST_KEY" ]
  cmds=$(sed -n 's/^.* -- //p' "$T/ssh.log")
  [ "$(printf '%s\n' "$cmds" | sed -n 1p)" = 'readlink -f /run/current-system' ]
  [ "$(printf '%s\n' "$cmds" | sed -n 2p)" = 'sudo -n /run/current-system/sw/bin/nix-env --profile /nix/var/nix/profiles/system --set /nix/store/aaaa-nixos-system-forge-1' ]
  [ "$(printf '%s\n' "$cmds" | sed -n 3p)" = 'sudo -n /nix/store/aaaa-nixos-system-forge-1/bin/switch-to-configuration switch' ]
  [ "$(printf '%s\n' "$cmds" | sed -n 4p)" = 'readlink -f /run/current-system' ]
  tail -n 1 "$T/ssh.log" | grep -q -- '-O exit'
  # anchored: the sandbox's BATS_TEST_TMPDIR sits under /build, so a bare
  # 'build' would match the ControlPath logged with every fake-nix call
  grep -q -- '^build .#' "$T/nix.log"
  grep -qF 'copy --no-check-sigs --to ssh-ng://deploy@192.0.2.10 /nix/store/aaaa-nixos-system-forge-1 ::' "$T/nix.log"
  grep '^copy ' "$T/nix.log" | grep -q -- 'UserKnownHostsFile='
  build_line=$(grep -n '^nix: build' "$T/order.log" | cut -d: -f1)
  readlink_line=$(grep -n '^ssh: .*readlink -f /run/current-system' "$T/order.log" | head -n 1 | cut -d: -f1)
  copy_line=$(grep -n '^nix: copy' "$T/order.log" | head -n 1 | cut -d: -f1)
  [ -n "$build_line" ]
  [ -n "$readlink_line" ]
  [ -n "$copy_line" ]
  [ "$build_line" -lt "$copy_line" ]
  [ "$readlink_line" -lt "$copy_line" ]
}

@test "deploy prints diff-closures when the machine's system is local" {
  run env FAKE_LOCAL_PREVIOUS=/nix/store/bbbb-nixos-system-forge-0 python3 "$FLEET_PY" deploy forge --identity "$T/id"
  [ "$status" -eq 0 ]
  [[ "$output" == *'<<diff /nix/store/bbbb-nixos-system-forge-0 /nix/store/aaaa-nixos-system-forge-1>>'* ]]
}

@test "deploy --toplevel skips the build and switches the given system" {
  run python3 "$FLEET_PY" deploy forge --toplevel "$T/sys" --identity "$T/id"
  [ "$status" -eq 0 ]
  [[ "$output" == *"fleet: deployed forge $T/sys"* ]]
  # anchored: the sandbox's BATS_TEST_TMPDIR sits under /build (see case 1)
  [ ! -e "$T/nix.log" ] || [ "$(grep -c -- '^build ' "$T/nix.log")" -eq 0 ]
  grep -qF -- "sudo -n $T/sys/bin/switch-to-configuration switch" "$T/ssh.log"
}

@test "deploy --toplevel without bin/switch-to-configuration is refused before any connection" {
  run --separate-stderr python3 "$FLEET_PY" deploy forge --toplevel "$T" --identity "$T/id"
  [ "$status" -eq 2 ]
  [[ "$stderr" == *"is not a NixOS system"* ]]
  [ ! -e "$T/ssh.log" ]
}

@test "a host-key refusal is exit 3, ssh's line verbatim, before any copy" {
  run --separate-stderr env FAKE_SSH_FAIL=hostkey python3 "$FLEET_PY" deploy forge --identity "$T/id"
  [ "$status" -eq 3 ]
  [ "$stderr" = 'fleet: refused: Host key verification failed.' ]
  [ "$(grep -c copy "$T/nix.log")" -eq 0 ]
  ! grep -q nix-env "$T/ssh.log"
}

@test "an authentication refusal is exit 3, ssh's line verbatim" {
  run --separate-stderr env FAKE_SSH_FAIL=denied python3 "$FLEET_PY" deploy forge --identity "$T/id"
  [ "$status" -eq 3 ]
  [ "$stderr" = 'fleet: refused: Permission denied (publickey).' ]
}

@test "the placeholder hardware file refuses the deploy before any connection" {
  printf '# PLACEHOLDER: x\n_: { }\n' >hosts/forge/hardware-configuration.nix
  run --separate-stderr python3 "$FLEET_PY" deploy forge --identity "$T/id"
  [ "$status" -eq 2 ]
  [ "$stderr" = 'fleet: deploy: forge is not enrolled (hosts/forge/hardware-configuration.nix is the placeholder)' ]
  [ ! -e "$T/ssh.log" ]
}

@test "an operator machine does not accept deploys" {
  run --separate-stderr python3 "$FLEET_PY" deploy core --identity "$T/id"
  [ "$status" -eq 2 ]
  [[ "$stderr" == *"core is not declared with a deploy-accepting role"* ]]
}

@test "a missing identity file is refused before any connection" {
  run --separate-stderr python3 "$FLEET_PY" deploy forge --identity missing
  [ "$status" -eq 2 ]
  [[ "$stderr" == *"identity missing is missing"* ]]
  [ ! -e "$T/ssh.log" ]
}

@test "a switch that reports success without changing /run/current-system is exit 5" {
  run --separate-stderr env FAKE_NO_SWITCH=1 python3 "$FLEET_PY" deploy forge --identity "$T/id"
  [ "$status" -eq 5 ]
  [[ "$stderr" == *"/run/current-system is /nix/store/bbbb-nixos-system-forge-0, not /nix/store/aaaa-nixos-system-forge-1"* ]]
}

@test "a failed switch is exit 4 naming the step" {
  run --separate-stderr env FAKE_SWITCH_FAIL=1 python3 "$FLEET_PY" deploy forge --identity "$T/id"
  [ "$status" -eq 4 ]
  [[ "$stderr" == *"switch failed"* ]]
}

@test "enroll writes the fetched hardware verbatim, the entry, the lan and the pins" {
  strip_forge
  run --separate-stderr python3 "$FLEET_PY" enroll forge 192.0.2.10 --fingerprint "$FINGERPRINT" --identity "$T/id"
  [ "$status" -eq 0 ]
  cmp hosts/forge/hardware-configuration.nix "$T/hw.nix"
  [ "$(jq -r .machines.forge.hostKey hosts/fleet.json)" = "$HOST_KEY" ]
  [ "$(jq -r .machines.forge.prefix hosts/fleet.json)" = 24 ]
  [ "$(jq -r .machines.forge.interface hosts/fleet.json)" = eth1 ]
  [ "$(jq -r .machines.forge.efi hosts/fleet.json)" = true ]
  [ "$(jq -r .machines.forge.stateVersion hosts/fleet.json)" = 25.11 ]
  [ "$(jq -r .machines.forge.roles[0] hosts/fleet.json)" = forge ]
  [ "$(jq -r .lan.subnet hosts/fleet.json)" = 192.0.2.0/24 ]
  [ "$(jq -r .lan.gateway hosts/fleet.json)" = 192.0.2.1 ]
  [ "$(jq -r .lan.nameservers[0] hosts/fleet.json)" = 192.0.2.1 ]
  sha256sum -c --quiet hosts/hardware-pins.sha256
  [ "$(wc -l <hosts/hardware-pins.sha256)" -eq 2 ]
  [ "$(cat "$T/kh.copy")" = "forge,192.0.2.10 $HOST_KEY" ]
  [ "$(sed -n 's/^.* -- //p' "$T/ssh.log" | sed -n 1p)" = 'sudo -n /run/current-system/sw/bin/nixos-generate-config --show-hardware-config' ]
  [ "${output##*$'\n'}" = 'fleet: commit: git add hosts/forge hosts/fleet.json hosts/hardware-pins.sha256' ]
}

@test "a fingerprint that is a prefix of the real one is refused, nothing written" {
  strip_forge
  cp hosts/fleet.json "$T/fj.copy"
  run --separate-stderr python3 "$FLEET_PY" enroll forge 192.0.2.10 --fingerprint SHA256:5A87i --identity "$T/id"
  [ "$status" -eq 3 ]
  [ "$stderr" = "fleet: refused: host key fingerprint $FINGERPRINT does not match SHA256:5A87i" ]
  [ ! -e "$T/ssh.log" ]
  [ ! -e hosts/forge ]
  cmp hosts/fleet.json "$T/fj.copy"
}

@test "a fingerprint without the SHA256: prefix gets it prepended" {
  strip_forge
  run python3 "$FLEET_PY" enroll forge 192.0.2.10 --fingerprint 5A87i/oxDPw4fPiu3miWBatyv19yGznNAMKgl6uJLGM --identity "$T/id"
  [ "$status" -eq 0 ]
  [ "$(jq -r .machines.forge.hostKey hosts/fleet.json)" = "$HOST_KEY" ]
}

@test "--fingerprint is required when stdin is not a terminal" {
  strip_forge
  run --separate-stderr python3 "$FLEET_PY" enroll forge 192.0.2.10 --identity "$T/id" </dev/null
  [ "$status" -eq 2 ]
  [[ "$stderr" == *'--fingerprint is required when stdin is not a terminal'* ]]
}

@test "a scan with no ed25519 line, or only ssh-rsa, is exit 3" {
  strip_forge
  run --separate-stderr env FAKE_SCAN_EMPTY=1 python3 "$FLEET_PY" enroll forge 192.0.2.10 --identity "$T/id"
  [ "$status" -eq 3 ]
  [ "$stderr" = 'fleet: enroll: no ed25519 host key from 192.0.2.10' ]
  strip_forge
  run --separate-stderr env FAKE_SCAN_RSA=1 python3 "$FLEET_PY" enroll forge 192.0.2.10 --identity "$T/id"
  [ "$status" -eq 3 ]
  [ "$stderr" = 'fleet: enroll: no ed25519 host key from 192.0.2.10' ]
}

@test "a failed stateVersion fetch writes nothing; --state-version overrides it" {
  strip_forge
  cp hosts/fleet.json "$T/fj.copy"
  cp hosts/hardware-pins.sha256 "$T/pins.copy"
  run --separate-stderr env FAKE_NO_STATEVERSION=1 python3 "$FLEET_PY" enroll forge 192.0.2.10 --fingerprint "$FINGERPRINT" --identity "$T/id"
  [ "$status" -eq 4 ]
  [[ "$stderr" == *'--state-version'* ]]
  [ ! -e hosts/forge ]
  cmp hosts/fleet.json "$T/fj.copy"
  cmp hosts/hardware-pins.sha256 "$T/pins.copy"
  strip_forge
  run env FAKE_NO_STATEVERSION=1 python3 "$FLEET_PY" enroll forge 192.0.2.10 --fingerprint "$FINGERPRINT" --identity "$T/id" --state-version 25.05
  [ "$status" -eq 0 ]
  [ "$(jq -r .machines.forge.stateVersion hosts/fleet.json)" = 25.05 ]
}

@test "re-enrol keeps roles and lan; an address outside lan.subnet is refused before the scan" {
  run python3 "$FLEET_PY" enroll forge 192.0.2.10 --fingerprint "$FINGERPRINT" --identity "$T/id"
  [ "$status" -eq 0 ]
  [ "$(jq -c .machines.forge.roles hosts/fleet.json)" = '["forge"]' ]
  [ "$(jq -r .lan.subnet hosts/fleet.json)" = 192.0.2.0/24 ]
  run --separate-stderr python3 "$FLEET_PY" enroll lab 198.51.100.5 --fingerprint "$FINGERPRINT" --identity "$T/id"
  [ "$status" -eq 2 ]
  [[ "$stderr" == *"outside the declared lan.subnet"* ]]
  [ "$(grep -c 198.51.100.5 "$T/scan.log")" -eq 0 ]
}

@test "keys add appends once, refuses a bad key, writes the canonical JSON" {
  printf 'sk-ssh-ed25519@openssh.com AAAAC3NzaC1lZDI1NTE5AAAAIexample fleet-test-key\n' >k.pub
  printf 'ssh-rsa AAAA x\n' >bad.pub
  run --separate-stderr python3 "$FLEET_PY" keys add k.pub
  [ "$status" -eq 0 ]
  [ "$stderr" = '' ]
  [[ "$output" == *'fleet: keys: added fleet-test-key'* ]]
  [ "$(jq '.deployKeys | length' hosts/fleet.json)" -eq 2 ]
  run --separate-stderr python3 "$FLEET_PY" keys add k.pub
  [ "$status" -eq 0 ]
  [[ "$output" == *'fleet: keys: already declared fleet-test-key'* ]]
  [ "$(jq '.deployKeys | length' hosts/fleet.json)" -eq 2 ]
  run --separate-stderr python3 "$FLEET_PY" keys add bad.pub
  [ "$status" -eq 2 ]
  [ "$(jq '.deployKeys | length' hosts/fleet.json)" -eq 2 ]
  python3 -c 'import json,sys; json.dump(json.load(open(sys.argv[1])), sys.stdout, indent=2, sort_keys=True); print()' hosts/fleet.json >"$T/canonical.json"
  cmp hosts/fleet.json "$T/canonical.json"
}

@test "join-script prints the bootstrap with the declared keys and the parent import" {
  run --separate-stderr python3 "$FLEET_PY" join-script
  [ "$status" -eq 0 ]
  [ "${output%%$'\n'*}" = '#!/usr/bin/env bash' ]
  printf '%s\n' "$output" | grep -qF 'fleet-fixture-deploy'
  # PL27: the bootstrap is the function file verbatim plus a one-line
  # application -- the parent import rides the application line, not an
  # imports = [ ... ] literal inside the module body.
  printf '%s\n' "$output" | grep -qF 'parentImports = [ ./configuration.nix ];'
  printf '%s\n' "$output" | grep -qF 'nixos-rebuild switch -I nixos-config=/etc/nixos/fleet-join.nix'
  printf '%s\n' "$output" | grep -qF 'fleet-join: host key'
  printf '%s\n' "$output" | grep -qF 'fleet-join: address'
  printf '%s\n' "$output" >"$T/join.sh"
  run bash -n "$T/join.sh"
  [ "$status" -eq 0 ]
  jq '.deployKeys = []' hosts/fleet.json >"$T/nokeys.json"
  mv "$T/nokeys.json" hosts/fleet.json
  run --separate-stderr python3 "$FLEET_PY" join-script
  [ "$status" -eq 2 ]
}

@test "a repo without hosts/fleet.json and a bad declaration are exit 2 naming the field" {
  mkdir -p "$T/empty"
  run --separate-stderr python3 "$FLEET_PY" --repo "$T/empty" join-script
  [ "$status" -eq 2 ]
  [[ "$stderr" == *"is not a checkout with hosts/fleet.json"* ]]
  jq '.machines.forge.prefix = 40' hosts/fleet.json >"$T/bad.json"
  mv "$T/bad.json" hosts/fleet.json
  run --separate-stderr python3 "$FLEET_PY" deploy forge --identity "$T/id"
  [ "$status" -eq 2 ]
  [[ "$stderr" == *"forge.prefix"* ]]
}

@test "the shim refuses without python3 and runs the command with it" {
  cd "$REPO_ROOT"
  run --separate-stderr env PATH="$T/nopython" bash tools/fleet --help
  [ "$status" -eq 2 ]
  [ "$stderr" = 'tools/fleet: python3 is not on PATH; run under nix develop -c, or use the fleet command core installs after the switch' ]
  run bash tools/fleet --help
  [ "$status" -eq 0 ]
  [[ "$output" == *deploy* ]]
}
