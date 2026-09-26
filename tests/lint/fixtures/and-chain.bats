#!/usr/bin/env bats
# Fixture for tests/lint/bats-and-chain.sh: this file must be REFUSED.
@test "vacuous chain" {
  [ 1 -eq 2 ] && [ 2 -eq 2 ]
}