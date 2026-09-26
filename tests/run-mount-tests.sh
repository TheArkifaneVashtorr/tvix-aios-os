#!/usr/bin/env bash
# Runs the mount-lifecycle bats suite unprivileged inside a user+mount
# namespace, twice: once with private mount propagation (the unshare default)
# and once with shared propagation — what systemd hosts actually use, and the
# environment where `mount --move` under a shared parent is refused.
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== mount tests: private propagation"
unshare --user --map-root-user --mount --propagation private \
  bats tests/unit/30-mount.bats
echo "== mount tests: shared propagation (systemd-host conditions)"
unshare --user --map-root-user --mount --propagation shared \
  bats tests/unit/30-mount.bats
