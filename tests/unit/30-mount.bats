#!/usr/bin/env bats

setup() {
  if [[ "$(id -u)" -ne 0 ]]; then
    skip "mount tests need (namespace) root — run tests/run-mount-tests.sh"
  fi
  cd "$BATS_TEST_TMPDIR"
  age-keygen -o key.txt 2>/dev/null
  age-keygen -y key.txt >recipients.txt
  mkdir -p src store run
  echo "secret" >src/data.txt
  cat >manifest.json <<'EOF'
{ "id": "demo", "classification": "local-only", "mount": "/data/demo", "access": "ro" }
EOF
  basket encrypt src --manifest manifest.json --recipients recipients.txt --store store
}

@test "mount decrypts into a tmpfs and teardown removes it" {
  basket mount store/demo --identity key.txt --runtime-dir run --size 16M
  mountpoint -q run/demo
  [ "$(cat run/demo/data.txt)" = "secret" ]
  [ "$(findmnt -no FSTYPE --target run/demo)" = "tmpfs" ]
  basket teardown demo --runtime-dir run
  ! mountpoint -q run/demo
  [ ! -e run/demo/data.txt ]
}

@test "ro manifest yields a read-only mount" {
  basket mount store/demo --identity key.txt --runtime-dir run --size 16M
  run touch run/demo/new.txt
  [ "$status" -ne 0 ]
  basket teardown demo --runtime-dir run
}

@test "teardown fails loudly on unknown id" {
  run basket teardown nope --runtime-dir run
  [ "$status" -eq 1 ]
}

@test "teardown removes every stacked mount layer and leaves no plaintext readable" {
  basket mount store/demo --identity key.txt --runtime-dir run --size 16M
  mount --bind run/demo run/demo # a second layer on the same mountpoint
  basket teardown demo --runtime-dir run
  ! mountpoint -q run/demo
  ! mountpoint -q run/.basket-tmpfs-demo
  [ ! -e run/demo/data.txt ]
  [ ! -d run/.basket-tmpfs-demo ]
}

@test "teardown cleans a staging tmpfs left behind by an interrupted mount" {
  mkdir -p run/.basket-tmpfs-demo
  mount -t tmpfs -o size=1M basket-demo run/.basket-tmpfs-demo
  echo leak >run/.basket-tmpfs-demo/x
  run basket teardown demo --runtime-dir run
  [ "$status" -eq 0 ]
  ! mountpoint -q run/.basket-tmpfs-demo
  [ ! -d run/.basket-tmpfs-demo ]
}

@test "a mount whose decryption fails leaves no staging tmpfs and no directories" {
  age-keygen -o wrong.txt 2>/dev/null
  run basket mount store/demo --identity wrong.txt --runtime-dir run --size 16M
  [ "$status" -ne 0 ]
  ! mountpoint -q run/.basket-tmpfs-demo
  [ ! -d run/.basket-tmpfs-demo ]
  [ ! -d run/demo ]
}
