#!/usr/bin/env bash
set -euo pipefail
# shellcheck source-path=SCRIPTDIR
# shellcheck source=../acceptance/gaming.sh
source "$(dirname "$0")/../acceptance/gaming.sh"
fixture=$'tcp   LISTEN 0 128 127.0.0.1:27060 0.0.0.0:*\ntcp   LISTEN 0 128 0.0.0.0:27036 0.0.0.0:*\nudp   UNCONN 0 0 [::1]:5353 [::]:*\ntcp   LISTEN 0 128 [::]:27015 [::]:*'
got=$(printf '%s\n' "$fixture" | nonloopback_listeners)
[[ "$got" == $'tcp   LISTEN 0 128 0.0.0.0:27036 0.0.0.0:*\ntcp   LISTEN 0 128 [::]:27015 [::]:*' ]] || {
  echo "filter wrong: $got"
  exit 1
}
echo ok
