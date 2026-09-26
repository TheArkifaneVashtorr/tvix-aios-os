#!/usr/bin/env bats

setup() {
  cd "$BATS_TEST_TMPDIR"
  age-keygen -o key.txt 2>/dev/null
  age-keygen -y key.txt >recipients.txt
  mkdir -p a b store
  echo "alpha" >a/x.txt
  echo "beta" >b/y.txt
  printf '{ "id": "alpha", "classification": "permitted", "mount": "/data/a", "access": "ro" }\n' >ma.json
  printf '{ "id": "beta", "classification": "local-only", "mount": "/data/b", "access": "rw" }\n' >mb.json
  basket encrypt a --manifest ma.json --recipients recipients.txt --store store
  basket encrypt b --manifest mb.json --recipients recipients.txt --store store
}

@test "lock captures every basket with all hash fields" {
  basket lock store --out baskets.lock
  [ "$(jq -r '.version' baskets.lock)" = "1" ]
  [ "$(jq -r '.baskets | length' baskets.lock)" = "2" ]
  [ "$(jq -r '.baskets[0].id' baskets.lock)" = "alpha" ]
  for f in content_sha256 payload_sha256 manifest_sha256; do
    [ "$(jq -r ".baskets[0].$f | length" baskets.lock)" = "64" ]
  done
}

@test "lock respects explicit order" {
  basket lock store --out baskets.lock --order beta,alpha
  [ "$(jq -r '.baskets[0].id' baskets.lock)" = "beta" ]
}

@test "lock rejects unknown id in order" {
  run basket lock store --out baskets.lock --order alpha,ghost
  [ "$status" -eq 1 ]
}

@test "verify passes on an untouched store" {
  basket lock store --out baskets.lock
  basket verify store --lock baskets.lock
}

@test "verify catches manifest tampering" {
  basket lock store --out baskets.lock
  jq '.access = "rw"' store/alpha/manifest.json >t && mv t store/alpha/manifest.json
  run basket verify store --lock baskets.lock
  [ "$status" -eq 1 ]
  [[ "$output" == *"alpha"* ]]
}

@test "verify catches payload swap" {
  basket lock store --out baskets.lock
  cp store/beta/payload.tar.age store/alpha/payload.tar.age
  run basket verify store --lock baskets.lock
  [ "$status" -eq 1 ]
}

@test "verify catches an extra store entry" {
  basket lock store --out baskets.lock
  mkdir -p c && echo "gamma" >c/z.txt
  printf '{ "id": "gamma", "classification": "permitted", "mount": "/data/c", "access": "ro" }\n' >mc.json
  basket encrypt c --manifest mc.json --recipients recipients.txt --store store
  run basket verify store --lock baskets.lock
  [ "$status" -eq 1 ]
  [[ "$output" == *"gamma"* ]]
}
