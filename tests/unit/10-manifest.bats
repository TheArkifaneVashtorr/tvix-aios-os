#!/usr/bin/env bats

setup() {
  cd "$BATS_TEST_TMPDIR"
  cat >good.json <<'EOF'
{ "id": "work-notes", "classification": "local-only", "mount": "/data/notes", "access": "ro" }
EOF
}

@test "accepts a valid manifest" {
  run basket validate-manifest good.json
  [ "$status" -eq 0 ]
}

@test "rejects unknown classification" {
  jq '.classification = "public"' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
  [[ "$output" == *"classification"* ]]
}

@test "rejects extra keys" {
  jq '. + {evil: true}' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
}

@test "rejects missing keys" {
  jq 'del(.mount)' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
}

@test "rejects relative mount path" {
  jq '.mount = "data/notes"' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
  [[ "$output" == *"mount"* ]]
}

@test "rejects bad id" {
  jq '.id = "Work Notes!"' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
  [[ "$output" == *"id"* ]]
}

@test "rejects non-JSON" {
  echo "not json" >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
}
