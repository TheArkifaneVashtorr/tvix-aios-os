#!/usr/bin/env bats

setup() {
  cd "$BATS_TEST_TMPDIR"
  age-keygen -o key.txt 2>/dev/null
  age-keygen -y key.txt >recipients.txt
  mkdir -p src/sub store out
  echo "hello" >src/a.txt
  echo "world" >src/sub/b.txt
  cat >manifest.json <<'EOF'
{ "id": "demo", "classification": "permitted", "mount": "/data/demo", "access": "rw" }
EOF
}

encrypt_demo() {
  basket encrypt src --manifest manifest.json --recipients recipients.txt --store store
}

@test "encrypt creates the store layout" {
  encrypt_demo
  [ -f store/demo/manifest.json ]
  [ -f store/demo/payload.tar.age ]
  [ -f store/demo/content.sha256 ]
}

@test "content hash is deterministic across re-encryption" {
  encrypt_demo
  h1=$(cat store/demo/content.sha256)
  rm -r store/demo
  encrypt_demo
  h2=$(cat store/demo/content.sha256)
  [ "$h1" = "$h2" ]
}

@test "round-trip preserves content" {
  encrypt_demo
  basket decrypt store/demo --identity key.txt --into out
  [ "$(cat out/a.txt)" = "hello" ]
  [ "$(cat out/sub/b.txt)" = "world" ]
}

@test "decrypt fails with wrong identity" {
  encrypt_demo
  age-keygen -o wrong.txt 2>/dev/null
  run basket decrypt store/demo --identity wrong.txt --into out
  [ "$status" -eq 1 ]
}

@test "decrypt fails when payload is tampered" {
  encrypt_demo
  # age authenticates its payload; flipping ciphertext must fail decryption.
  # Flip the final byte (inside the last AEAD chunk tag) by XOR-ing it with
  # 0xff: writing a fixed literal at a fixed offset was a no-op whenever that
  # byte already held the literal, and the test then failed by chance.
  last=$(($(stat -c %s store/demo/payload.tar.age) - 1))
  orig=$(dd if=store/demo/payload.tar.age bs=1 skip="$last" count=1 status=none | od -An -tu1 | tr -d ' ')
  printf '%b' "\\0$(printf '%03o' $((orig ^ 0xff)))" |
    dd of=store/demo/payload.tar.age bs=1 seek="$last" conv=notrunc status=none
  run basket decrypt store/demo --identity key.txt --into out
  [ "$status" -eq 1 ]
}

@test "encrypt refuses an invalid manifest" {
  jq '.access = "rwx"' manifest.json >bad.json
  run basket encrypt src --manifest bad.json --recipients recipients.txt --store store
  [ "$status" -eq 1 ]
}

@test "plaintext never lands outside the target dir" {
  encrypt_demo
  basket decrypt store/demo --identity key.txt --into out
  [ -z "$(find /tmp -maxdepth 1 -name 'basket*' 2>/dev/null)" ]
}
