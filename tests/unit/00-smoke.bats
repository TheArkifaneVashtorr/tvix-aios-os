#!/usr/bin/env bats

@test "basket prints usage and exits 2 with no args" {
  run basket
  [ "$status" -eq 2 ]
  [[ "$output" == *"usage: basket"* ]]
}

@test "basket --help exits 0" {
  run basket --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"usage: basket"* ]]
}
