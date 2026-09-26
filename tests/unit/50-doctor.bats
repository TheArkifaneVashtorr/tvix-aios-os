#!/usr/bin/env bats

setup() {
  cd "$BATS_TEST_TMPDIR"
  mkdir -p root/proc root/run root/dev root/sys
  printf 'Filename\tType\tSize\tUsed\tPriority\n' >root/proc/swaps
}

@test "doctor passes on a clean fabricated host" {
  mkdir -p root/run/pcscd root/sys/module/vhost_vsock
  touch root/run/pcscd/pcscd.comm root/dev/kvm
  run basket doctor --root root
  [ "$status" -eq 0 ]
  [[ "$output" == *"PASS"* ]]
  [[ "$output" != *"FAIL"* ]]
}

@test "doctor fails when swap is active" {
  mkdir -p root/run/pcscd root/sys/module/vhost_vsock
  touch root/run/pcscd/pcscd.comm root/dev/kvm
  printf '/dev/sda2\tpartition\t8388604\t0\t-2\n' >>root/proc/swaps
  run basket doctor --root root
  [ "$status" -eq 1 ]
  [[ "$output" == *"FAIL"*"swap"* ]]
}

@test "doctor fails on stale basket mounts" {
  mkdir -p root/run/pcscd root/sys/module/vhost_vsock root/run/baskets/leftover
  touch root/run/pcscd/pcscd.comm root/dev/kvm
  run basket doctor --root root
  [ "$status" -eq 1 ]
  [[ "$output" == *"FAIL"*"stale"* ]]
}

@test "doctor warns but does not fail when pcscd is absent" {
  mkdir -p root/sys/module/vhost_vsock
  touch root/dev/kvm
  run basket doctor --root root
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARN"*"pcscd"* ]]
}
