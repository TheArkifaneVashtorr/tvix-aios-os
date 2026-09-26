#!/usr/bin/env bash
# tests/acceptance/media.sh — operator acceptance drill for services.comfyui.
#
# Run this BY HAND, as root (or via `sudo`), on the host AFTER the flake has
# been wired in and `nixos-rebuild switch`d, comfyui.service is up, and
# `media-fetch-models` has been run at least once for the checks that need
# an output file. This repo is build-only (see the flake's README): this
# script is the one place in the repo that assumes a live, running system —
# it is authored and syntax-checked here (`bash -n`, `shellcheck`) but never
# executed by the factory that writes it.
#
# Design basis: docs/superpowers/specs/2026-09-02-media-flake-design-rev3.md
# (rev 3.1, nix-native, no container — normative), "Testing" section,
# operator acceptance drill.
#
# nix-native (rev 3.1): there is no container to `exec` into any more —
# `comfyui.service` sets `NetworkNamespacePath` on itself directly (systemd's
# own privilege, not podman's — see docs/decisions/2026-09-02-netns-entry-
# amendment.md, which amended the now-removed podman `--network ns:…` join
# and is superseded by this rewrite for that reason: there is no podman flag
# left to amend). Every proof below either talks to ComfyUI through the
# loopback socket proxy (`comfyui-proxy.socket`, the only reachable listener)
# or reaches into the broker's namespace itself with `nsenter`, run as the
# service's own unprivileged user (`comfyui`) rather than root, matching how
# the unit itself runs.
#
# Every check appends PASS/FAIL to $RESULTS and the script exits 1 if any
# check failed — no `set -e`, because several checks assert that a command
# FAILS (the fail-closed proofs) and a blanket -e would make that awkward.
set -uo pipefail

BROKER_INSTANCE="${BROKER_INSTANCE:-media}"
NETNS="/run/netns/egress-${BROKER_INSTANCE}"
AUDIT_LOG="/var/lib/egress-broker/${BROKER_INSTANCE}/audit.jsonl"
DATA_DIR="${DATA_DIR:-/var/lib/comfyui}"
OUTPUT_DIR="${DATA_DIR}/output"
COMFY_USER="${COMFY_USER:-comfyui}"
PROXY_URL="${PROXY_URL:-http://127.0.0.1:8188}"
# Only checked when set: services.comfyui.models.hfTokenFile is a plain
# string outside the store (see the module and the runbook's "token file"
# section) — this drill has no way to read it back out of a NixOS config,
# so the operator names it explicitly when a gated model is configured.
TOKEN_FILE="${TOKEN_FILE:-}"
WORKFLOW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/workflows" && pwd)"
GEN_TIMEOUT="${GEN_TIMEOUT:-300}" # seconds; the spec's "within 5 min"

PASS=0
FAIL=0

pass() {
  echo "PASS: $1"
  PASS=$((PASS + 1))
}

fail() {
  echo "FAIL: $1" >&2
  FAIL=$((FAIL + 1))
}

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "prerequisite: $1 not on PATH"
    exit 1
  fi
}

need curl
need python3
need systemctl
need sudo
need nsenter
need runuser
need stat

# --- 1. comfyui.service is active ------------------------------------------

if systemctl is-active --quiet comfyui.service; then
  pass "comfyui.service is active"
else
  fail "comfyui.service is not active (systemctl status comfyui.service)"
fi

# --- 2. system_stats names the RTX 5090 and a CUDA 12.8 torch ---------------

stats_json="$(curl -sf -m 10 "${PROXY_URL}/system_stats" || true)"
if [ -z "$stats_json" ]; then
  fail "GET ${PROXY_URL}/system_stats: no response (proxy or comfyui.service down?)"
else
  if python3 -c "
import json, sys
d = json.loads(sys.argv[1])
devices = d.get('devices', [])
gpu_ok = any('5090' in dev.get('name', '') and dev.get('type') == 'cuda' for dev in devices)
system = d.get('system', {})
pytorch_version = str(system.get('pytorch_version', ''))
cuda_ok = '12.8' in pytorch_version or '12.8' in json.dumps(d)
sys.exit(0 if (gpu_ok and cuda_ok) else 1)
" "$stats_json"; then
    pass "system_stats names an RTX 5090 CUDA device on torch cu128 (12.8)"
  else
    fail "system_stats does not name an RTX 5090 CUDA device on torch 12.8: $stats_json"
  fi
fi

# --- 3. media-fetch-models: only OK/SKIP, and every fetch is an `allow` in
#        the broker audit ---------------------------------------------------

sudo systemctl start comfyui-fetch-models.service
fetch_status="$(systemctl show comfyui-fetch-models.service -p ExecMainStatus --value)"
fetch_log="$(journalctl -u comfyui-fetch-models.service -n 500 --no-pager --output=cat)"
fetch_exec_start="$(systemctl show comfyui-fetch-models.service -p ExecStart --value)"

if [ "$fetch_status" != "0" ]; then
  fail "comfyui-fetch-models.service exited $fetch_status"
elif echo "$fetch_log" | grep -q 'media-fetch: FAIL'; then
  fail "media-fetch-models logged a FAIL line: $(echo "$fetch_log" | grep 'media-fetch: FAIL')"
elif ! echo "$fetch_log" | grep -qE 'media-fetch: (OK|SKIP)'; then
  fail "media-fetch-models logged no OK/SKIP lines at all — did it run?"
else
  pass "media-fetch-models: only OK/SKIP lines, exit 0"
fi

if [ -r "$AUDIT_LOG" ] && python3 -c "
import json, sys
hosts = set()
with open(sys.argv[1], encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get('verdict') == 'allow' and rec.get('host', '').endswith(('huggingface.co', 'hf.co')):
            hosts.add(rec['host'])
sys.exit(0 if hosts else 1)
" "$AUDIT_LOG"; then
  pass "broker audit log has 'allow' entries for the model-fetch hosts"
else
  fail "broker audit log ($AUDIT_LOG) has no 'allow' entry for a Hugging Face host — fetch may not have gone through the broker"
fi

# --- 3b. media-fetch-models --reverify: every already-present file re-hashes
#         against the manifest and the run ends with ONLY OK lines — no
#         SKIP (SKIP would mean it trusted a file's existence, exactly what
#         --reverify exists not to do) and no FAIL (a mismatch = bit-rot or
#         a truncated prior download). --reverify never touches the network
#         for a present file (pkgs/media-fetch/fetch.py), so this runs
#         directly as the service user rather than through the confined
#         fetch unit, whose own ExecStart has no --reverify flag. -----------

reverify_manifest="$(echo "$fetch_exec_start" | grep -oE -- '--manifest [^ ]+' | awk '{print $2}')"
reverify_dest="$(echo "$fetch_exec_start" | grep -oE -- '--dest [^ ]+' | awk '{print $2}')"
reverify_cafile="$(echo "$fetch_exec_start" | grep -oE -- '--cafile [^ ]+' | awk '{print $2}')"

if [ -z "$reverify_manifest" ] || [ -z "$reverify_dest" ]; then
  fail "could not parse --manifest/--dest out of comfyui-fetch-models.service's ExecStart to run --reverify: $fetch_exec_start"
else
  reverify_args=(--manifest "$reverify_manifest" --dest "$reverify_dest" --reverify)
  if [ -n "$reverify_cafile" ]; then
    reverify_args+=(--cafile "$reverify_cafile")
  fi
  reverify_log="$(sudo runuser -u "$COMFY_USER" -- media-fetch-models "${reverify_args[@]}" 2>&1)"
  reverify_status=$?
  if [ "$reverify_status" -ne 0 ]; then
    fail "media-fetch-models --reverify exited $reverify_status: $reverify_log"
  elif echo "$reverify_log" | grep -qE 'media-fetch: (SKIP|FAIL)'; then
    fail "media-fetch-models --reverify logged a non-OK line (expected only OK — a re-hash against the manifest): $(echo "$reverify_log" | grep -E 'media-fetch: (SKIP|FAIL)')"
  elif ! echo "$reverify_log" | grep -q 'media-fetch: OK'; then
    fail "media-fetch-models --reverify logged no OK lines at all — did it run against any files?"
  else
    pass "media-fetch-models --reverify: only OK lines, every present file re-hashed against the manifest"
  fi
fi

# --- 4. no HF_TOKEN (or any TOKEN key) in comfyui.service's own environment -
#        (nix-native: the broker injects the credential itself, at its own
#        process; comfyui.service never holds it — checks.comfyui-eval and
#        checks.comfyui-vm assert the same at eval time and on a real VM) --

env_out="$(systemctl show comfyui.service -p Environment --value)"
if echo "$env_out" | grep -q 'TOKEN'; then
  fail "comfyui.service's own environment carries a TOKEN key — the credential must only ever live at the broker: $env_out"
else
  pass "no TOKEN key in \`systemctl show comfyui.service -p Environment\`"
fi

# --- 5. the token file, when one is configured, has the mode the broker
#        needs to read it and nothing else does: 0440 root:egress-broker or
#        0400 egress-broker:<group> (see the runbook's "token file" section
#        for why — never 0400 root, which the broker's own unprivileged
#        user could not read at all) --------------------------------------

if [ -n "$TOKEN_FILE" ]; then
  if [ ! -e "$TOKEN_FILE" ]; then
    fail "TOKEN_FILE=$TOKEN_FILE does not exist"
  else
    mode_owner="$(stat -c '%a %U:%G' "$TOKEN_FILE")"
    case "$mode_owner" in
      "440 root:egress-broker")
        pass "token file $TOKEN_FILE is 0440 root:egress-broker"
        ;;
      "400 egress-broker:"*)
        pass "token file $TOKEN_FILE is 0400 owned by egress-broker ($mode_owner)"
        ;;
      *)
        fail "token file $TOKEN_FILE is '$mode_owner' — expected 440 root:egress-broker or 400 egress-broker:<group>"
        ;;
    esac
  fi
else
  echo "SKIP: TOKEN_FILE not set — set TOKEN_FILE=<path> to check services.comfyui.models.hfTokenFile's mode (only meaningful when a gated model, e.g. Flux.1-dev, is configured)"
fi

# --- 6. the models directory is read-only to comfyui.service itself --------
#        (rev 3.1: `ReadOnlyPaths` on the unit, not a container mount —
#        proving this from the live unit's own hardening report, not by
#        writing into it from outside the unit, which would succeed and
#        prove nothing: the mount is per-unit, not per-filesystem; the real
#        mount is exercised end-to-end by checks.comfyui-vm) --------------

readonly_paths="$(systemctl show comfyui.service -p ReadOnlyPaths --value)"
if echo "$readonly_paths" | grep -q "${DATA_DIR}/models"; then
  pass "systemctl show comfyui.service -p ReadOnlyPaths lists ${DATA_DIR}/models"
else
  fail "systemctl show comfyui.service -p ReadOnlyPaths does not list ${DATA_DIR}/models: $readonly_paths"
fi

# --- 7. fail-closed proof, run as the service's own user: the namespace
#        itself has no route out without the broker (nsenter, no proxy env
#        — the netns-level property, independent of whether comfyui.service
#        even sets HTTPS_PROXY correctly) ------------------------------------

if sudo nsenter --net="$NETNS" -- runuser -u "$COMFY_USER" -- curl -m 5 -sS https://example.com >/dev/null 2>&1; then
  fail "nsenter --net=${NETNS} (as ${COMFY_USER}) curl https://example.com SUCCEEDED — the namespace has a route out that bypasses the broker"
else
  pass "nsenter --net=${NETNS} (as ${COMFY_USER}) curl https://example.com fails closed (no route without the broker)"
fi

# --- 8. complementary proof: through the SAME proxy comfyui.service itself
#        is configured with (read back from its own unit environment, not
#        hardcoded), a host outside the allowlist is denied BY THE BROKER
#        (not just unroutable) and the denial is audited -------------------

broker_proxy_url="$(echo "$env_out" | tr ' ' '\n' | sed -n 's/^HTTPS_PROXY=//p')"

if [ -z "$broker_proxy_url" ]; then
  fail "could not read HTTPS_PROXY back out of comfyui.service's own environment to run the broker-level deny proof"
else
  before_denies="$(grep -c '"verdict": "deny"' "$AUDIT_LOG" 2>/dev/null || echo 0)"
  code="$(sudo nsenter --net="$NETNS" -- runuser -u "$COMFY_USER" -- env "HTTPS_PROXY=${broker_proxy_url}" \
    curl -m 10 -s -o /dev/null -w '%{http_code}' https://example.com || echo curl-failed)"
  after_denies="$(grep -c '"verdict": "deny"' "$AUDIT_LOG" 2>/dev/null || echo 0)"

  if [ "$code" = "403" ] || [ "$code" = "curl-failed" ]; then
    if [ "$after_denies" -gt "$before_denies" ]; then
      pass "curl (as ${COMFY_USER}, through comfyui.service's own HTTPS_PROXY) to a non-allowlisted host is denied and audited (deny count $before_denies -> $after_denies, HTTP $code)"
    else
      fail "curl to example.com through comfyui.service's own proxy was refused (HTTP $code) but the broker audit log gained no new 'deny' line"
    fi
  else
    fail "curl to example.com through comfyui.service's own proxy returned HTTP $code — expected a denial"
  fi
fi

# --- 9-11. generation proofs: POST a bundled minimal workflow, poll
#           /history, assert an output file appears within GEN_TIMEOUT
#           seconds --------------------------------------------------------

post_and_wait() {
  local name="$1" workflow="$2" glob="$3"
  local body prompt_id waited=0

  body="$(python3 -c "
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    graph = json.load(f)
print(json.dumps({'prompt': graph, 'client_id': 'acceptance-' + sys.argv[2]}))
" "$WORKFLOW_DIR/${workflow}.json" "$name")"

  prompt_id="$(curl -sf -m 30 -X POST -H 'content-type: application/json' -d "$body" "${PROXY_URL}/prompt" |
    python3 -c "import json,sys; print(json.load(sys.stdin).get('prompt_id',''))" 2>/dev/null)"

  if [ -z "$prompt_id" ]; then
    fail "$name: POST ${PROXY_URL}/prompt did not return a prompt_id"
    return
  fi

  while [ "$waited" -lt "$GEN_TIMEOUT" ]; do
    if curl -sf -m 10 "${PROXY_URL}/history/${prompt_id}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
sys.exit(0 if d else 1)
" 2>/dev/null; then
      break
    fi
    sleep 5
    waited=$((waited + 5))
  done

  local produced
  produced="$(find "$OUTPUT_DIR" -newer "$WORKFLOW_DIR/${workflow}.json" -type f -path "$glob" 2>/dev/null | head -n1)"

  if [ -z "$produced" ]; then
    fail "$name: prompt $prompt_id — no output file matching $glob under $OUTPUT_DIR within ${GEN_TIMEOUT}s"
    return
  fi

  pass "$name: prompt $prompt_id produced $produced within ${waited}s"

  # --- ownership stat (spec: the serving process's own user owns what it
  #     writes — checked here, once, on whichever proof runs first to
  #     actually produce a file) -----------------------------------------
  local owner
  owner="$(stat -c '%U:%G' "$produced")"
  if [ "$owner" = "${COMFY_USER}:${COMFY_USER}" ]; then
    pass "$name: $produced is owned by ${COMFY_USER}:${COMFY_USER} on the host"
  else
    fail "$name: $produced is owned by $owner, expected ${COMFY_USER}:${COMFY_USER}"
  fi
}

post_and_wait "sdxl (image)" "sdxl" "*/acceptance/sdxl_*.png"
post_and_wait "ace-step (audio)" "ace-step" "*/acceptance/ace-step_*.mp3"
post_and_wait "wan2.2 (video)" "video" "*/acceptance/video_*.webm"

# --- summary -----------------------------------------------------------------

echo
echo "media acceptance drill: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ]
