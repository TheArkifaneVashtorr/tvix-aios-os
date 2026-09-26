#!/usr/bin/env bash
# Helm acceptance drill (operator-run, docs/runbooks/helm.md): the status
# page loads at http://localhost:7700, helm-status lists all nine tiles,
# the collector timer is armed, static-web-server is loopback-only, and a
# real timer-down/timer-up cycle proves the "timers armed" tile actually
# notices a stopped timer and recovers once it is started again. No sudo --
# every step here is a user-scope systemd action or a read against the
# already-running system.
#
# Run from the repo root: nix develop -c tests/acceptance/helm.sh
set -euo pipefail

# Make the script's own cwd predictable no matter how it was invoked --
# every path below is already absolute, but this keeps "run from the repo
# root" true rather than merely documented (F18). readlink -f resolves a
# bare-name invocation (PATH lookup, or a relative symlink) to the script's
# real location first; "$0" alone is only a path when the caller invoked it
# as one, and dirname on a bare "helm.sh" yields "." -- silently wrong cwd.
cd "$(dirname "$(readlink -f "$0")")/../.."

url="${HELM_URL:-http://localhost:7700}"
status_file="${HELM_STATUS_FILE:-/var/lib/helm/status.json}"
port="${HELM_PORT:-7700}"

pass=0
fail=0
step() {
  echo
  echo "== $1"
}
ok() {
  echo "   PASS: $1"
  pass=$((pass + 1))
}
bad() {
  echo "   FAIL: $1"
  fail=$((fail + 1))
}
warn() {
  echo "   WARN: $1"
}

# tile_status <name> -- prints the tile's "status" field from status.json,
# or "unreadable" if the file can't be read/parsed.
tile_status() {
  jq -r --arg n "$1" '.tiles[] | select(.name == $n) | .status' "$status_file" 2>/dev/null || echo "unreadable"
}

step "0. warm the collector: run helm-collect.service synchronously"
if systemctl --user start helm-collect.service; then
  ok "helm-collect.service ran a fresh collection before the page/status checks"
else
  bad "helm-collect.service failed to run -- see systemctl --user status helm-collect.service"
fi

step "1. status page loads at ${url}"
# Even with step 0 above, static-web-server's socket can still be mid-start
# or the page mid-write, so retry the GET for up to 60s (every 5s) instead
# of failing on the first 404 (F8).
got_ok=0
last_code="000"
start=$SECONDS
while true; do
  # No -f here: with -f, curl exits 22 on a non-2xx response *without*
  # writing the -w format string, so the old `curl -f ... || echo 000`
  # fallback ran unconditionally and concatenated onto whatever curl had
  # already printed (a 404 read as "404000", a connection refusal as
  # "000000") -- last_code never matched "200" or "404" again after the
  # first such response. Plain curl always writes %{http_code} on a
  # completed request and only fails (empty output) on a transport error
  # (connection refused, DNS, etc.), which the explicit fallback below
  # catches.
  last_code=$(curl -sS -o /dev/null -w '%{http_code}' "$url/" 2>/dev/null || true)
  [ -n "$last_code" ] || last_code="000"
  if [ "$last_code" = "200" ]; then
    got_ok=1
    break
  fi
  if [ "$last_code" = "404" ]; then
    echo "   waiting for the first collection"
  fi
  if [ $((SECONDS - start)) -ge 60 ]; then
    break
  fi
  sleep 5
done
if [ "$got_ok" -eq 1 ]; then
  page=$(curl -fsS "$url/" 2>/dev/null || echo "")
  if printf '%s' "$page" | grep -q "Helm"; then
    ok "GET ${url}/ returned 200 with \"Helm\" in the body"
  else
    bad "GET ${url}/ returned 200 but the body did not contain \"Helm\""
  fi
else
  bad "GET ${url}/ did not return 200 within 60s (last status: ${last_code})"
fi

step "2. helm-status exits 0 and lists all nine tiles"
if status_out=$(helm-status 2>&1); then
  ok "helm-status exited 0"
else
  bad "helm-status exited non-zero -- see output above"
fi
missing=""
for name in backup-snapshot backup-parity timers basket-doctor broker gpu host drift flake-check; do
  if ! printf '%s\n' "$status_out" | grep -q "$name"; then
    missing="${missing} ${name}"
  fi
done
if [ -z "$missing" ]; then
  ok "all nine tiles present in helm-status output"
else
  bad "helm-status output is missing tile(s):${missing}"
fi

step "3. helm-collect.timer is armed"
if systemctl --user is-active --quiet helm-collect.timer; then
  ok "helm-collect.timer is active"
else
  bad "helm-collect.timer is not active -- see systemctl --user status helm-collect.timer"
fi

step "4. static-web-server listens on loopback only"
listen_addrs=$(ss -ltn 2>/dev/null | awk -v p=":${port}\$" '$4 ~ p { print $4 }')
if [ -z "$listen_addrs" ]; then
  bad "nothing is listening on port ${port} -- is static-web-server.socket up?"
else
  bad_addrs=$(printf '%s\n' "$listen_addrs" | grep -vE "^(127\.0\.0\.1|\[::1\]):${port}\$" || true)
  if [ -n "$bad_addrs" ]; then
    bad "port ${port} is reachable on a non-loopback address: ${bad_addrs}"
  else
    ok "port ${port} listens on loopback only (${listen_addrs})"
  fi
fi

# F25: step 5 below stops proton-drive-push.timer and restarts it once the
# negative proof is done. If the drill is interrupted (Ctrl-C, or any error
# under `set -e`) in between, the timer would be left down and future
# backups would silently stop running. This trap restarts it no matter how
# the script exits; systemctl start on an already-active timer is a no-op,
# so it is harmless on the normal, non-interrupted path too.
trap 'systemctl --user start proton-drive-push.timer || true' EXIT

step "5. negative proof: a stopped user timer turns the timers tile red, restarting it turns it green"
timer_was_active=0
if systemctl --user is-active --quiet proton-drive-push.timer; then
  timer_was_active=1
fi
if systemctl --user stop proton-drive-push.timer; then
  ok "stopped proton-drive-push.timer"
else
  bad "could not stop proton-drive-push.timer -- aborting the negative proof"
fi
if systemctl --user start helm-collect.service; then
  ok "helm-collect.service ran a fresh collection with the timer down"
else
  bad "helm-collect.service failed to run"
fi
down_status=$(tile_status timers)
if [ "$down_status" = "fail" ]; then
  ok "timers tile is fail with proton-drive-push.timer stopped"
else
  bad "timers tile is '${down_status}', expected fail"
fi
if systemctl --user start proton-drive-push.timer; then
  ok "restarted proton-drive-push.timer"
else
  bad "could not restart proton-drive-push.timer -- fix this by hand: systemctl --user start proton-drive-push.timer"
fi
if systemctl --user start helm-collect.service; then
  ok "helm-collect.service ran a fresh collection with the timer back up"
else
  bad "helm-collect.service failed to run"
fi
up_status=$(tile_status timers)
if [ "$up_status" = "ok" ]; then
  ok "timers tile is ok again with proton-drive-push.timer restarted"
else
  bad "timers tile is '${up_status}', expected ok -- proton-drive-push.timer may still be down: systemctl --user start proton-drive-push.timer"
fi
if [ "$timer_was_active" -eq 0 ]; then
  warn "proton-drive-push.timer was not active before this drill ran -- check it separately (docs/runbooks/backup.md)"
fi

step "6. the API port (7710) is loopback-only and answers its routes"
# Operator step 2: ss -ltn | grep 7710 shows one loopback bind, nothing else.
api_listen=$(ss -ltn 2>/dev/null | awk '$4 ~ /:7710$/ { print $4 }')
if [ -z "$api_listen" ]; then
  bad "nothing is listening on API port 7710 -- is helm-api.service up?"
else
  bad_api=$(printf '%s\n' "$api_listen" | grep -vE "^(127\.0\.0\.1|\[::1\]):7710\$" || true)
  if [ -n "$bad_api" ]; then
    bad "API port 7710 is reachable on a non-loopback address: ${bad_api}"
  else
    ok "API port 7710 listens on loopback only (${api_listen})"
  fi
fi

# GET /v1/status -> 200 (Operator step 2).
code=$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:7710/v1/status)
if [ "$code" = "200" ]; then
  ok "GET http://127.0.0.1:7710/v1/status answered 200"
else
  bad "GET http://127.0.0.1:7710/v1/status answered ${code}, expected 200"
fi

# POST /v1/control -> 405 (Operator step 2: the API has no POST route there).
code=$(curl -sS -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:7710/v1/control)
if [ "$code" = "405" ]; then
  ok "POST http://127.0.0.1:7710/v1/control answered 405"
else
  bad "POST http://127.0.0.1:7710/v1/control answered ${code}, expected 405"
fi

# GET /v1/switch -> 404 (Operator step 2: there is no switch route).
code=$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:7710/v1/switch)
if [ "$code" = "404" ]; then
  ok "GET http://127.0.0.1:7710/v1/switch answered 404 (no switch route)"
else
  bad "GET http://127.0.0.1:7710/v1/switch answered ${code}, expected 404"
fi

# POST / on 7700 -> 405 as before (Operator step 2).
code=$(curl -sS -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:7700/)
if [ "$code" = "405" ]; then
  ok "POST http://127.0.0.1:7700/ answered 405 as before"
else
  bad "POST http://127.0.0.1:7700/ answered ${code}, expected 405"
fi

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "HELM ACCEPTANCE: PASS"
else
  echo "HELM ACCEPTANCE: FAIL"
  exit 1
fi
