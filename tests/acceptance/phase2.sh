#!/usr/bin/env bash
# Phase 2 acceptance (brief §7): from inside a netns, an allowlisted host
# succeeds via the broker, a non-allowlisted host fails, both appear in the
# audit log with correct verdicts, and a domain-fronted request is caught by
# TLS termination. Transient: netns, veth, broker and logs are all torn down.
# Run from the repo root: nix develop -c tests/acceptance/phase2.sh
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo --preserve-env=PATH "$0" "$@"
fi

ns=basket-accept
work=$(mktemp -d)
broker_pid=""
fw_mode=""

# The host firewall drops unsolicited input on the veth by default (the same
# interplay the VM test discovered for the module, which fixes it declaratively
# via networking.firewall.interfaces). This transient test opens a matching
# pinhole for its lifetime only: broker port, this interface, netns source IP.
fw_open() {
  if command -v iptables >/dev/null && iptables -S >/dev/null 2>&1; then
    iptables -I INPUT 1 -i veb-accept -s 10.200.0.2 -p tcp --dport 3128 -j ACCEPT
    fw_mode="iptables"
  elif command -v nft >/dev/null && nft list table inet nixos-fw >/dev/null 2>&1; then
    nft insert rule inet nixos-fw input \
      iifname "veb-accept" ip saddr 10.200.0.2 tcp dport 3128 accept
    fw_mode="nft"
  else
    echo "note: no active host firewall detected; no pinhole needed"
  fi
}

fw_close() {
  case "$fw_mode" in
    iptables)
      iptables -D INPUT -i veb-accept -s 10.200.0.2 -p tcp --dport 3128 -j ACCEPT 2>/dev/null || true
      ;;
    nft)
      local handle
      handle=$(nft -a list chain inet nixos-fw input 2>/dev/null |
        grep 'iifname "veb-accept"' | grep -o 'handle [0-9]*' | head -1 | cut -d' ' -f2)
      if [[ -n "$handle" ]]; then
        nft delete rule inet nixos-fw input handle "$handle" || true
      fi
      ;;
  esac
}

cleanup() {
  if [[ -n "$broker_pid" ]]; then kill "$broker_pid" 2>/dev/null || true; fi
  fw_close
  ip link del veb-accept 2>/dev/null || true
  ip netns del "$ns" 2>/dev/null || true
  rm -rf "$work"
}
trap cleanup EXIT
pass=0
fail=0
ok() {
  echo "   PASS: $1"
  pass=$((pass + 1))
}
bad() {
  echo "   FAIL: $1"
  fail=$((fail + 1))
}

echo "== setup: throwaway netns + veth + broker (allow: example.com only)"
ip netns add "$ns"
ip link add veb-accept type veth peer name ven-accept
ip link set ven-accept netns "$ns"
ip addr add 10.200.0.1/30 dev veb-accept
ip link set veb-accept up
ip netns exec "$ns" ip addr add 10.200.0.2/30 dev ven-accept
ip netns exec "$ns" ip link set ven-accept up
ip netns exec "$ns" ip link set lo up
ip netns exec "$ns" ip route add default via 10.200.0.1
fw_open

cat >"$work/policy.json" <<EOF
{ "instance": "acceptance", "allow": ["example.com"],
  "inject": {}, "audit_log": "$work/audit.jsonl" }
EOF
BROKER_POLICY="$work/policy.json" mitmdump --mode regular \
  --listen-host 10.200.0.1 --listen-port 3128 \
  --set "confdir=$work/ca" -s pkgs/broker/policy.py \
  >"$work/mitmdump.log" 2>&1 &
broker_pid=$!
for _ in $(seq 1 50); do
  if [[ -f "$work/ca/mitmproxy-ca-cert.pem" ]]; then break; fi
  sleep 0.2
done
[[ -f "$work/ca/mitmproxy-ca-cert.pem" ]] || {
  echo "broker failed to start:" >&2
  cat "$work/mitmdump.log" >&2
  exit 1
}

curl_ns() {
  # timeouts so a firewall drop fails loudly instead of hanging the test
  ip netns exec "$ns" curl -s --connect-timeout 10 --max-time 60 \
    -x http://10.200.0.1:3128 \
    --cacert "$work/ca/mitmproxy-ca-cert.pem" "$@"
}

echo
echo "== 1. allowlisted host succeeds from inside the netns"
if curl_ns -o /dev/null -w '%{http_code}' https://example.com/ | grep -q 200; then
  ok "https://example.com reachable via broker"
else
  bad "allowlisted request failed"
fi

echo
echo "== 2. non-allowlisted host is refused"
# a proxy CONNECT 403 surfaces as a curl error message, not an HTTP code
out=$(curl_ns -S https://github.com/ 2>&1 || true)
if [[ "$out" == *"403"* ]]; then
  ok "https://github.com refused (CONNECT 403 from broker)"
else
  bad "expected CONNECT 403, got: $out"
fi

echo
echo "== 3. domain-fronted request is caught by TLS termination"
code=$(curl_ns -H "Host: github.com" -o /dev/null -w '%{http_code}' https://example.com/ || true)
if [[ "$code" == "403" ]]; then
  ok "fronted request (outer example.com, inner github.com) refused"
else
  bad "fronted request not refused (got: $code)"
fi

echo
echo "== 4. no route around the broker exists"
if ip netns exec "$ns" curl -s --max-time 3 https://example.com/ >/dev/null 2>&1; then
  bad "direct internet access from netns should be impossible"
else
  ok "direct (non-broker) egress from the netns fails"
fi

echo
echo "== 5. audit log verdicts"
allow_n=$(jq -s '[.[] | select(.verdict=="allow")] | length' "$work/audit.jsonl")
deny_n=$(jq -s '[.[] | select(.verdict=="deny")] | length' "$work/audit.jsonl")
mismatch_n=$(jq -s '[.[] | select(.reason | test("mismatch"))] | length' "$work/audit.jsonl")
if [[ "$allow_n" -ge 1 && "$deny_n" -ge 2 && "$mismatch_n" -ge 1 ]]; then
  ok "audit shows $allow_n allow, $deny_n deny (incl. $mismatch_n fronting mismatch)"
else
  bad "audit verdicts wrong: allow=$allow_n deny=$deny_n mismatch=$mismatch_n"
fi
echo
echo "--- audit log (for your review):"
jq -c '{host, sni, verdict, reason}' "$work/audit.jsonl" || true

echo
echo "== Result: $pass passed, $fail failed"
if [[ "$fail" -eq 0 ]]; then
  echo "PHASE 2 ACCEPTANCE: PASS"
else
  echo "PHASE 2 ACCEPTANCE: FAIL"
  exit 1
fi
