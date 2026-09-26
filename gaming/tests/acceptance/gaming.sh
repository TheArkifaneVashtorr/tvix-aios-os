#!/usr/bin/env bash
# Gaming acceptance (docs/runbooks/gaming.md): on a host with
# programs.gaming.enable = true already rebuilt, the tool set is present and
# versioned, Steam starts and shows a Proton-GE compatibility entry
# (operator judgment), starting Steam opens no new non-loopback inbound
# listener, no Steam-related firewall rule exists with every
# programs.gaming.firewall.* switch left at its default false, and a
# gamescope window renders (the NVIDIA + upscaling + explicit-sync coredump
# reports in docs/research-2026-09-02-gaming-stack.md are why this step is a
# measurement, not a rubber stamp). Needs a live GNOME/Wayland desktop
# session (the Steam/gamescope windows) and sudo for the read-only firewall
# listing.
#
# Run from the repo root: nix develop -c tests/acceptance/gaming.sh
#
# GAMING_DRILL_NONINTERACTIVE=1 skips steps 5, 7 and 8 -- the ones that
# start Steam or need an operator watching the screen -- each recorded as a
# WARN instead of run, so the rest of the drill (and its exit status) can be
# exercised unattended. See tests/unit/drill-success.sh.
set -euo pipefail

pass=0
fail=0
warn_count=0
# Top level (not inside main): the EXIT trap must resolve even if it fires
# before main() assigns a real value (this script sourced by
# tests/unit/listeners.sh, or a failure before main() runs) or after main()
# returns. "${work:-}" makes an empty value a harmless no-op rm rather than
# an unbound-variable error under set -u.
work=""
trap 'rm -rf "${work:-}"' EXIT
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
  warn_count=$((warn_count + 1))
}
# Operator confirms a check that only a human watching the screen can judge
# (a window appearing, a compatibility-tool list entry). Answered "y" ->
# PASS, anything else -> FAIL; the check is still recorded either way.
confirm() {
  local reply
  read -r -p "   $1 [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

# Filters ss -ltnuH-shaped lines (Netid State Recv-Q Send-Q Local:Port ...)
# down to listeners that are NOT loopback-only: Steam's own client binds
# loopback sockets, so a raw diff of the full listener set always changes.
# The guarantee this drill measures is "no non-loopback listener appeared".
nonloopback_listeners() {
  awk '$5 !~ /^(127\.[0-9.]+|\[::1\]):/'
}

# Steam's Remote Play / in-home-streaming discovery sockets bind on all
# interfaces (TCP+UDP 27036, UDP 27031-27035, TCP 27015, TCP 27040) the
# moment the client starts, regardless of programs.gaming.firewall.*
# switches -- that's the client discovering LAN peers, not the firewall
# admitting anything. Step 5 excludes them from what counts as a surprise;
# step 6 (the firewall ruleset) is the actual inbound-exposure guarantee.
filter_steam_discovery() {
  awk '{ n = split($5, a, ":"); port = a[n]; if (port ~ /^(27015|27031|27032|27033|27034|27035|27036|27040)$/) next; print }'
}

main() {
  work=$(mktemp -d)

  step "1. tool set on PATH"
  for bin in steam gamemoded gamescope mangohud; do
    if command -v "$bin" >/dev/null 2>&1; then
      ok "$bin is on PATH"
    else
      bad "$bin is not on PATH -- is programs.gaming.enable on and the host rebuilt?"
    fi
  done

  step "2. gamemode daemon answers"
  if command -v gamemoded >/dev/null 2>&1 && gamemoded -s >"$work/gamemoded-status.txt" 2>&1; then
    ok "gamemoded -s answered: $(tr -d '\n' <"$work/gamemoded-status.txt")"
  else
    # switch-to-configuration test never starts a newly wanted user unit, so
    # right after entering the profile by hand gamemoded may simply not be
    # running yet -- that is expected, not a break.
    warn "gamemoded -s did not answer -- see $work/gamemoded-status.txt (kept until this script exits); try: systemctl --user start gamemoded.service"
  fi

  step "3. gamescope --version"
  if gamescope_version=$(gamescope --version 2>&1); then
    ok "gamescope --version: ${gamescope_version}"
  else
    bad "gamescope --version failed"
  fi

  step "4. mangohud --version"
  if mangohud_version=$(mangohud --version 2>&1); then
    ok "mangohud --version: ${mangohud_version}"
  else
    bad "mangohud --version failed"
  fi

  step "5. starting Steam opens no new non-loopback inbound listener (informational -- the inbound-exposure verdict is step 6)"
  if [[ "${GAMING_DRILL_NONINTERACTIVE:-0}" == "1" ]]; then
    warn "GAMING_DRILL_NONINTERACTIVE=1 -- step 5 skipped (it starts Steam and waits on the operator); the inbound-exposure verdict is step 6"
  else
    if ! ss -ltnuH >"$work/ss-before-raw.txt" 2>&1; then
      warn "ss failed: $(cat "$work/ss-before-raw.txt")"
    fi
    nonloopback_listeners <"$work/ss-before-raw.txt" >"$work/ss-before.txt" || true
    echo "   Baseline non-loopback listeners captured. Loopback sockets (Steam's"
    echo "   own client binds some) are expected and excluded from this diff."
    echo "   Start Steam now (log in if asked), let it finish updating, then"
    echo "   come back here."
    read -r -p "   Press enter once Steam has fully started... " _
    if ! ss -ltnuH >"$work/ss-after-raw.txt" 2>&1; then
      warn "ss failed: $(cat "$work/ss-after-raw.txt")"
    fi
    nonloopback_listeners <"$work/ss-after-raw.txt" >"$work/ss-after.txt" || true
    new_listeners=$(comm -13 <(sort "$work/ss-before.txt") <(sort "$work/ss-after.txt") | filter_steam_discovery || true)
    if [[ -n "$new_listeners" ]]; then
      echo "   New non-loopback listener(s), Steam's documented discovery ports excluded:"
      printf '%s\n' "$new_listeners" | while IFS= read -r line; do
        echo "     ${line}"
      done
      warn "unexpected new non-loopback listener(s) after Steam started -- see above; the inbound-exposure verdict is step 6"
    else
      ok "no unexpected new non-loopback listener (Steam's documented discovery ports excluded); the inbound-exposure verdict is step 6"
    fi
  fi

  step "6. no Steam-related firewall rule with every firewall.* switch off"
  # core has no nft binary in either profile (iptables-save/ip6tables-save
  # only, nf_tables backend); prefer nft when it exists so this still works
  # on a host that does have it.
  local rules="" have_rules=0
  if command -v nft >/dev/null 2>&1; then
    if rules=$(sudo nft list ruleset 2>&1); then
      have_rules=1
    else
      bad "sudo nft list ruleset failed"
    fi
  elif command -v iptables-save >/dev/null 2>&1; then
    if rules=$(
      {
        sudo iptables-save
        sudo ip6tables-save
      } 2>&1
    ); then
      have_rules=1
    else
      warn "could not read the ruleset: $rules"
    fi
  else
    warn "no nft/iptables-save on PATH -- inbound-exposure check skipped"
  fi
  if [[ "$have_rules" -eq 1 ]]; then
    if hits=$(echo "$rules" | grep -E '2703[1-6]|27015|27040'); then
      bad "Steam port(s) found in firewall ruleset with firewall.* switches off:"
      echo "$hits" | while IFS= read -r line; do
        echo "     ${line}"
      done
    else
      ok "no Steam port in firewall ruleset"
    fi
  fi

  step "7. Proton-GE entry in Steam's compatibility tool list"
  if [[ "${GAMING_DRILL_NONINTERACTIVE:-0}" == "1" ]]; then
    warn "GAMING_DRILL_NONINTERACTIVE=1 -- step 7 skipped (needs Steam open and an operator watching)"
  else
    echo "   In Steam: Settings -> Compatibility (or right-click a game ->"
    echo "   Properties -> Compatibility), and look for a GE-Proton entry in"
    echo "   the dropdown."
    if confirm "Does a GE-Proton entry appear in the compatibility tool list?"; then
      ok "operator confirms a GE-Proton entry is listed"
    else
      bad "operator did not find a GE-Proton entry"
    fi
  fi

  step "8. gamescope smoke test"
  if [[ "${GAMING_DRILL_NONINTERACTIVE:-0}" == "1" ]]; then
    warn "GAMING_DRILL_NONINTERACTIVE=1 -- step 8 skipped (needs a gamescope window and an operator watching)"
  else
    echo "   Launch one game (or 'gamescope -- glxgears', installed by"
    echo "   mesa-demos) through gamescope. This is the NVIDIA caveat"
    echo "   measurement: driver >= 555 has reported coredumps with upscaling"
    echo "   + explicit sync (research digest, ValveSoftware/gamescope#1662)"
    echo "   -- watch for a crash, not just a window appearing."
    if confirm "Did the gamescope window render and stay up without crashing?"; then
      ok "operator confirms gamescope rendered without crashing"
    else
      bad "operator saw a crash or no window -- do not rely on gamescope daily yet"
    fi
  fi

  echo
  echo "== Result: $pass passed, $fail failed, $warn_count warned"
  if [[ "$fail" -eq 0 ]]; then
    echo "GAMING ACCEPTANCE: PASS"
  else
    echo "GAMING ACCEPTANCE: FAIL"
    exit 1
  fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
