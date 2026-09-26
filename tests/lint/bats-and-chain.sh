#!/usr/bin/env bash
# bats-and-chain.sh [FILE...] -- refuse `] && [` chains in bats tests.
# Inside a @test, bash's errexit ignores a failing command followed by `&&`,
# so `[ a ] && [ b ]` on any line but the last passes when `[ a ]` is false:
# the assertion is vacuous. Write the two brackets on two lines instead.
# Exit 1 and print file:line for every offender; exit 0 when clean.
set -euo pipefail
if [ $# -eq 0 ]; then
  set -- tests/unit/*.bats
fi
bad=0
for f in "$@"; do
  if grep -n '\] && \[' "$f"; then
    bad=1
  fi
done
if [ "$bad" -ne 0 ]; then
  echo "lint: '] && [' chain in a bats test is vacuous under errexit — split it onto two lines (tests/lint/bats-and-chain.sh)" >&2
  exit 1
fi
