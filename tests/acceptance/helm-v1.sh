#!/usr/bin/env bash
# Helm v1 acceptance (operator-run, docs/runbooks/helm-v1.md): the read-only
# control surface is live on http://127.0.0.1:7700, the Profile section shows
# the running profile with base — active and no form; the password-gated
# switch to gaming and back is run by the operator from a desktop terminal
# (the script prints the exact `systemctl start helm-switch@…` line, waits
# for Enter, then checks the marker, the Steam arrival/departure and the
# journal pair), a real Firefox load of the page shows `base — active` with
# no form, and across every switch the boot default is untouched and no
# agent-prefixed unit (egress-|cowork|basket|restic-backups-|helm-) is
# restarted (D2/D4/D6). media and cowork SKIP — a distinct, logged verdict,
# never FAIL and never silently passed — while their preconditions are
# absent (D6: media waits for wiring round 2; cowork is parked off, so
# restic-backups-core-local and the agent-prefix sweep stand in for its
# broker audit).
#
# No sudo: every step is a loopback request, an operator-run user-scope
# systemd action (the desktop password authorizes it), or a read against
# the already-running system.
#
# Run from the repo root: nix develop -c tests/acceptance/helm-v1.sh
# Needs: the enabling switch already active (docs/runbooks/helm-v1.md), a
# live desktop session (Firefox + a terminal), and ideally a clean
# tree at the switched HEAD -- the drift check degrades to a warning on
# pre-existing dirt (step 5), it never invents a pass.
set -euo pipefail

# Same cwd discipline as tests/acceptance/helm.sh (F18): every path below
# is absolute, but "run from the repo root" stays true rather than merely
# documented, no matter how the script was invoked.
cd "$(dirname "$(readlink -f "$0")")/../.."

url="${HELM_URL:-http://127.0.0.1:7700}"
host_header="${HELM_HOST:-localhost:7700}"
marker_file="${HELM_MARKER:-/etc/helm/profile}"
config_file="${HELM_CONFIG:-/etc/helm/config.json}"
status_file="${HELM_STATUS_FILE:-/var/lib/helm/status.json}"
steam_bin="${HELM_STEAM_BIN:-/run/current-system/sw/bin/steam}"
# The system profile root -- the ROOT helm-switch itself selects (D4):
# the boot default lives here, and so does every specialisation's
# activation binary, whichever profile is currently running.
system_root="${HELM_SYSTEM_ROOT:-/nix/var/nix/profiles/system}"

pass=0
fail=0
skipped=0
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
skip() {
  echo "   SKIP: $1"
  skipped=$((skipped + 1))
}
warn() {
  echo "   WARN: $1"
}
# Operator confirms a check only a human watching the screen can judge (the
# same confirm() as tests/acceptance/phase4b.sh). Answered y -> PASS,
# anything else -> FAIL; the check is recorded either way.
confirm() {
  local reply
  read -r -p "   $1 [y/N] " reply || return 1
  [[ $reply =~ ^[Yy]$ ]]
}
# Fatal precondition: print the summary the same way a finished run does,
# then leave (nothing downstream can run) -- phase4b.sh's pattern.
gate_refused() {
  echo
  echo "== Result: $pass passed, $fail failed, $skipped skipped"
  echo "HELM V1 ACCEPTANCE: FAIL"
  exit 1
}

marker() {
  cat "$marker_file" 2>/dev/null || echo unreadable
}

# GET / with the accepted Host header (the rebinding defense applies to
# GET too, D10): body on stdout, empty on failure.
page_get() {
  curl -fsS -m 30 -H "Host: ${host_header}" "$url/"
}

# D-H1: the switch moved behind the desktop password (polkit
# auth_admin_keep), so it can only run from a session that can answer the
# prompt -- the script cannot start the unit itself. It prints the exact
# terminal line, waits for the operator to run it and press Enter, then
# (in the caller) the marker and the journal pair are checked.
run_switch_expect() {
  local profile=$1
  echo "   Run this in a desktop terminal (the system asks for your password):"
  echo "     systemctl start helm-switch@${profile}.service"
  read -r -p "   Then press Enter here to continue..." _
}

# The marker is normally already flipped once the operator presses Enter;
# the poll window is belt-and-braces against a slow activation.
wait_for_marker() {
  local want=$1 limit=$2 start=$SECONDS
  while [[ $(marker) != "$want" ]]; do
    if ((SECONDS - start >= limit)); then
      return 1
    fi
    sleep 2
  done
  return 0
}
# Steam's .desktop entry ships in the same package as the binary, so the
# binary on the new system PATH is the scriptable stand-in for "Steam is in
# the app grid" (consolidated acceptance #13); the operator's eyes on the
# grid are the free out-of-band confirmation while the drill runs.
wait_for_steam() {
  local want=$1 limit=$2 start=$SECONDS
  while true; do
    if [[ $want == present ]]; then
      [[ -x $steam_bin ]] && return 0
    else
      [[ ! -x $steam_bin ]] && return 0
    fi
    if ((SECONDS - start >= limit)); then
      return 1
    fi
    sleep 2
  done
}

# -- agent-unit baselines (D2/D4/D6) -------------------------------------
# The "profiles never touch agent units" guard's observable consequence.
# The agent prefixes are the module's agentUnitPrefix; templates ("@.")
# are skipped because systemctl show cannot address them -- only instances
# ever run, and the loaded sweep below covers those.
AGENT_RE='^(egress-|cowork|basket|restic-backups-|helm-)'
agent_units() { # agent_units <files|loaded> <scope args...>
  local which=$1
  shift
  {
    if [[ $which == files ]]; then
      systemctl "$@" list-unit-files --no-legend --no-pager
    else
      systemctl "$@" list-units --all --no-legend --plain
    fi
  } | awk '{print $1}' | grep -E "$AGENT_RE" | grep -v '@\.' | sort -u || true
}
# NRestarts + ActiveEnterTimestampMonotonic, joined with "|". Both,
# because NRestarts counts only Restart=-policy restarts: a switch that
# stops and starts a unit leaves NRestarts at 0 while the monotonic enter
# timestamp moves -- D6's "no restart across the switches" needs the pair.
# The pipe matters: NRestarts is a service-only property, so a timer or
# target shows an EMPTY first field, and a whitespace split would collapse
# the two fields into one; IFS='|' keeps empty fields intact.
unit_props() { # unit_props <unit> <scope args...>
  local unit=$1
  shift
  systemctl "$@" show "$unit" -p NRestarts -p ActiveEnterTimestampMonotonic --value |
    tr '\n' '|' | sed 's/|$//'
}

work=$(mktemp -d)
scope_flags() { # scope_flags <system|user> -> stdout: nothing or "--user"
  if [[ $1 == user ]]; then
    printf '%s' --user
  fi
}
snapshot_agents() { # snapshot_agents <before|after>
  local when=$1 scope
  for scope in system user; do
    # shellcheck disable=SC2046  # word-split is the point: 0 or 1 flags
    agent_units files $(scope_flags "$scope") >"$work/agent-files-$scope-$when"
    {
      cat "$work/agent-files-$scope-$when"
      # shellcheck disable=SC2046
      agent_units loaded $(scope_flags "$scope")
    } | sort -u >"$work/agent-units-$scope-$when"
    : >"$work/agent-props-$scope-$when"
    while IFS= read -r unit; do
      [[ -n $unit ]] || continue
      # shellcheck disable=SC2046
      printf '%s %s\n' "$unit" "$(unit_props "$unit" $(scope_flags "$scope"))" >>"$work/agent-props-$scope-$when"
    done <"$work/agent-units-$scope-$when"
  done
}

run_start=$(date +%s)

echo "Helm v1 acceptance -- $(date -u +%FT%TZ)"
echo "page: ${url} (Host: ${host_header})   marker: ${marker_file}"
echo "journal window starts at unix ${run_start}"

# == 1. preconditions =====================================================
step "1. the control surface is the live server on :7700"
got_ok=0
last_code=000
start=$SECONDS
while true; do
  # Plain curl (no -f): with -f a non-2xx exits 22 without writing the -w
  # format string (helm.sh's F8 lesson). 000 = transport error.
  last_code=$(curl -sS -o /dev/null -w '%{http_code}' -H "Host: ${host_header}" "$url/" || true)
  [ -n "$last_code" ] || last_code=000
  if [ "$last_code" = 200 ]; then
    got_ok=1
    break
  fi
  if [ $((SECONDS - start)) -ge 60 ]; then
    break
  fi
  sleep 5
done
if [ "$got_ok" -ne 1 ]; then
  bad "GET / did not return 200 within 60s (last status: ${last_code})"
  gate_refused
fi
page=$(page_get) || {
  bad "GET / stopped answering between the retry loop and now"
  gate_refused
}
if printf '%s' "$page" | grep -q '>Profile'; then
  ok "GET / serves the read-only v1 control page (the Profile section is present)"
else
  # v0 page (or the v1 boot-fresh fallback without the Profile section):
  # the enabling switch may be active while helm-serve was never started --
  # a switch does not start a newly enabled USER unit in an already-logged-
  # in session (D7). Start it exactly as the runbook says; anything else is
  # a gate refusal. The start's own error text is the diagnostic (unit not
  # found = the enabling switch is not active), so it is never silenced.
  if systemctl --user start helm-serve.service; then
    ok "started helm-serve.service by hand (the runbook's post-switch step, D7)"
    sleep 2
    page=$(page_get) || page=""
  fi
  if printf '%s' "$page" | grep -q '>Profile'; then
    ok "GET / now serves the read-only v1 control page"
  else
    bad "the page on :7700 has no Profile section -- still the v0 read-only page."
    echo "   The switch that enables services.helm.control is not active on"
    echo "   this machine. Run the enabling switch, then the two D7 lines in"
    echo "   docs/runbooks/helm-v1.md, then re-run this drill."
    gate_refused
  fi
fi
# D-H1: the page carries no form, no action= and no per-boot token -- there
# is no token file to read, and none is ever minted.
if printf '%s' "$page" | grep -qF '<form' || printf '%s' "$page" | grep -qF 'action='; then
  bad "the served page still carries a form or an action= (D-H1: it must be read-only)"
else
  ok "the served page carries no form and no action= (read-only, D-H1)"
fi

# == 2. baselines, before any switch ======================================
step "2. baselines: boot default, agent units, drift (before any switch)"
# A fresh collection first, so the drift baseline is a real read and not
# whatever the last 5-minute cycle happened to leave behind.
if systemctl --user start helm-collect.service; then
  ok "a fresh collection ran for the drift baseline"
else
  bad "helm-collect.service would not run -- see systemctl --user status helm-collect.service"
fi
baseline_drift=$(jq -r '.tiles[] | select(.name == "drift") | .status' "$status_file" || echo unknown)
if [[ $baseline_drift == ok ]]; then
  ok "drift tile is green before any switch"
else
  warn "drift tile reads '${baseline_drift}' before the drill -- pre-existing (a dirty"
  echo "   tree or an unswitched HEAD; docs/runbooks/helm-v1.md). The switch"
  echo "   cannot change drift (both toplevels carry the same revision), so"
  echo "   step 5 will require it UNCHANGED rather than green."
fi
sys_profile_before=$(readlink "$system_root")
booted_before=$(readlink /run/booted-system)
ok "boot default now: ${sys_profile_before} (the drill must leave it untouched)"
snapshot_agents before
agent_total_before=$(cat "$work/agent-units-system-before" "$work/agent-units-user-before" | sort -u | wc -l || true)
ok "agent-prefixed units under watch (system + user manager): ${agent_total_before}"

# == 3. start from base; the page shows the Profile section ================
step "3. the page shows the Profile section, base active"
current=$(marker)
if [[ $current != base ]]; then
  echo "   marker is '${current}' -- returning to base first (the drill starts from base)"
  run_switch_expect base
  if wait_for_marker base 30; then
    ok "back on base"
  else
    bad "could not return to base -- see journalctl -u helm-switch@base.service"
    gate_refused
  fi
fi
page=$(page_get) || page=""
if printf '%s' "$page" | grep -q '>Profile' && printf '%s' "$page" | grep -q 'base — active'; then
  ok "the Profile section shows base as the active profile (K10: verbatim lowercase)"
else
  bad "the Profile section does not show 'base — active'"
fi
# D-H1: one plain text line per profile, the active one marked -- no
# buttons, no disabled attribute, no form.
if printf '%s' "$page" | grep -q 'disabled>base'; then
  bad "the base entry still renders as a disabled button (D-H1: plain text now)"
else
  ok "the profile list is plain text (no disabled button, K11's render-disable is gone with the forms)"
fi
if printf '%s' "$page" | grep -qF '<script' || printf '%s' "$page" | grep -qF 'src=' ||
  printf '%s' "$page" | grep -qF 'href="http'; then
  bad "the served page violates the read-only invariant (no <script, no src=, no href=\"http)"
else
  ok "the served page carries no <script, no src=, no href=\"http (read-only)"
fi
statusjson=$(curl -fsS -m 30 -H "Host: ${host_header}" "$url/control.json") || statusjson=""
if [[ $(printf '%s' "$statusjson" | jq -r '.active_profile') == base ]]; then
  ok "/control.json agrees with the marker (serve-time state, D10)"
else
  bad "/control.json active_profile is not base -- the marker and the state disagree"
fi

# == 4. switch to gaming (operator-run, behind the password) ==============
step "4. switch to gaming (password-gated, D-H1)"
run_switch_expect gaming
if wait_for_marker gaming 30; then
  ok "the marker flipped: ${marker_file} -> gaming"
else
  bad "the marker did not flip to gaming (still '$(marker)') -- journalctl -u helm-switch@gaming.service"
fi
if wait_for_steam present 60; then
  ok "Steam is present on the new system path within a minute (${steam_bin})"
else
  bad "Steam did not appear at ${steam_bin} within a minute of the gaming switch"
fi

# == 5. the dashboard under it stays healthy ==============================
step "5. the dashboard under the switch (the safety case, K2)"
if systemctl --user start helm-collect.service; then
  ok "a fresh collection ran under the gaming profile (helm-serve's own agent unit untouched)"
else
  bad "helm-collect.service would not run -- see systemctl --user status helm-collect.service"
fi
drift_now=$(jq -r '.tiles[] | select(.name == "drift") | .status' "$status_file" || echo unknown)
if [[ $drift_now == "$baseline_drift" ]]; then
  if [[ $drift_now == ok ]]; then
    ok "the drift tile is still green after the switch -- the safety case held"
  else
    ok "the drift tile is unchanged ('${drift_now}') across the switch, as it must be"
  fi
else
  bad "the drift tile changed across the switch: '${baseline_drift}' -> '${drift_now}' (a switch cannot change drift -- file it)"
fi

# == 6. back to base (operator-run, behind the password) ==================
step "6. back to base (password-gated, D-H1)"
run_switch_expect base
if wait_for_marker base 30; then
  ok "the marker flipped back: ${marker_file} -> base (now, not forever -- K3)"
else
  bad "the marker did not flip back to base (still '$(marker)')"
fi
if wait_for_steam absent 30; then
  ok "Steam left the system path with the profile (${steam_bin} gone)"
else
  bad "Steam is still present at ${steam_bin} after returning to base"
fi

# == 7. a real Firefox load shows the read-only page (D-H1) ===============
step "7. a real Firefox load shows the read-only page"
echo "   In Firefox, open (or RELOAD) http://localhost:7700."
echo "   The page should show the Profile section with 'base — active' and"
echo "   no form, no button and no token (the page is read-only now)."
if confirm "Did Firefox show 'base — active' with no form?"; then
  ok "a real Firefox load shows the read-only page (base — active, no form)"
else
  bad "the real-browser load did not show the read-only page"
fi

# == 8. open the gaming workspace =========================================
step "8. open the gaming workspace (a Console window -- operator judgment)"
workspaces_n=$(jq -r '.control.workspaces | length' "$config_file" || echo 0)
if [[ $workspaces_n -eq 0 ]]; then
  # H4: the workspace buttons left the live page until Helm Home ships, so
  # there is nothing to open -- a distinct, logged SKIP, never a FAIL.
  skip "no workspaces declared (H4): nothing to open until Helm Home ships"
else
  echo "   D-H1 parked the page's Open button; run the launcher directly:"
  echo "     helm-open-workspace gaming"
  echo "   A GNOME Console window should appear on the desktop, cd'd into"
  echo "   /home/dalhaka/flakes/gaming, in its dev shell at a shell prompt."
  if confirm "Did a Console window open in ~/flakes/gaming in its dev shell (no claude)?"; then
    ok "operator confirms the Console window (D3's systemd-run --user escape works live)"
  else
    bad "no Console window (or wrong contents) -- the launcher path is operator-verified; file what you saw"
  fi
fi

# == 9. media round trip (conditional, D6) ================================
step "9. media round trip (conditional)"
if jq -e '(.control.profiles // []) | index("media") != null' "$config_file" >/dev/null &&
  [[ -x ${system_root}/specialisation/media/bin/switch-to-configuration ]]; then
  run_switch_expect media
  if wait_for_marker media 30; then
    ok "switched to media (marker: media)"
  else
    bad "switch to media did not flip the marker (marker '$(marker)')"
  fi
  run_switch_expect base
  if wait_for_marker base 30; then
    ok "back to base from media"
  else
    bad "switch back from media did not flip the marker (marker '$(marker)')"
  fi
else
  skip "media round trip: specialisation.media is not wired yet (round 2) -- D6 keeps this a SKIP, not a FAIL"
fi

# == 10. leave it on base ==================================================
step "10. leave the machine on base"
# Before the audit, deliberately: the cleanup switch (when one is needed)
# is a switch too, and "no agent unit restarted across the switches" must
# cover it -- the sweep below snapshots only after this.
if [[ $(marker) == base ]]; then
  ok "the drill ends on base, where it started (K3: a reboot also lands here)"
else
  warn "marker is '$(marker)' -- one cleanup switch to base"
  run_switch_expect base
  if wait_for_marker base 30; then
    ok "cleanup switch done -- back on base"
  else
    bad "could not return to base -- finish by hand: systemctl start helm-switch@base.service in a terminal and check the marker"
  fi
fi

# == 11. across the switches ==============================================
step "11. across the switches: boot default, agent units, journal pairs"
sys_profile_after=$(readlink "$system_root")
booted_after=$(readlink /run/booted-system)
if [[ $sys_profile_after == "$sys_profile_before" ]]; then
  ok "the boot default is unchanged (${sys_profile_after}) -- the test action never touches the bootloader (D4)"
else
  bad "the boot default MOVED: ${sys_profile_before} -> ${sys_profile_after}"
fi
if [[ $booted_after == "$booted_before" ]]; then
  ok "the booted system identity is unchanged (${booted_after})"
else
  bad "the booted system identity moved: ${booted_before} -> ${booted_after}"
fi

snapshot_agents after
agents_clean=1
for scope in system user; do
  if ! cmp -s "$work/agent-files-$scope-before" "$work/agent-files-$scope-after"; then
    bad "agent unit files appeared or disappeared in the ${scope} manager:"
    diff "$work/agent-files-$scope-before" "$work/agent-files-$scope-after" || true
    agents_clean=0
  fi
  # The stored line is "unit nrest|ts" (props joined with "|" -- see
  # unit_props), so the split is: unit by whitespace, props as the
  # remainder, compared verbatim against a fresh read.
  while read -r unit props; do
    [[ -n $unit ]] || continue
    if [[ $unit == helm-collect.service && $scope == user ]]; then
      # The drill's own baseline (step 2) and dashboard check (step 5) each
      # start a collection on purpose; those starts move this unit's
      # ActiveEnterTimestamp by the drill's hand, not by a switch.
      # Everything else about it (the file, NRestarts) still compares, and
      # the boot-default/audit checks above are unaffected.
      continue
    fi
    # shellcheck disable=SC2046
    after=$(unit_props "$unit" $(scope_flags "$scope"))
    if [[ $after != "$props" ]]; then
      bad "agent unit '$unit' (${scope} manager) was touched across the switches: '${props}' -> '${after}'"
      agents_clean=0
    fi
  done <"$work/agent-props-$scope-before"
done
if [[ $agents_clean -eq 1 ]]; then
  ok "no agent-prefixed unit restarted, appeared or disappeared across the switches (both managers)"
fi
if grep -q '^restic-backups-core-local.service ' "$work/agent-props-system-before"; then
  if cmp -s <(grep '^restic-backups-core-local.service ' "$work/agent-props-system-before") \
    <(grep '^restic-backups-core-local.service ' "$work/agent-props-system-after"); then
    ok "restic-backups-core-local was not restarted across the switches (D6's stand-in for the parked cowork broker)"
  else
    bad "restic-backups-core-local moved across the switches (D6's named unit)"
  fi
else
  skip "restic-backups-core-local is not present in the system manager (D6's stand-in unit)"
fi
if systemctl list-unit-files --no-legend --no-pager | grep -q '^cowork'; then
  ok "cowork units are present and were covered by the agent-unit sweep above"
else
  skip "cowork broker audit: cowork is parked off on core (services.cowork.enable=false) -- D6 replaces it with the sweep + restic-backups-core-local above"
fi

# The journal state machine (D8): every switch closed its begin/end pair
# -- a dangling begin would read as "switching" forever on the page.
switch_journal=$(journalctl -u 'helm-switch@*' --since "@${run_start}" --no-pager) || switch_journal=""
begins=$(printf '%s\n' "$switch_journal" | grep -c 'helm-switch: begin' || true)
ends=$(printf '%s\n' "$switch_journal" | grep -c 'helm-switch: end' || true)
if [[ $begins -gt 0 && $begins -eq $ends ]]; then
  ok "every switch left a closed begin/end pair in the journal (${begins} pairs since the drill started)"
else
  bad "unbalanced switch journal: ${begins} begins vs ${ends} ends (a dangling begin reads 'switching' forever)"
fi

echo
echo "== Result: $pass passed, $fail failed, $skipped skipped"
if [[ $fail -eq 0 ]]; then
  echo "HELM V1 ACCEPTANCE: PASS"
else
  echo "HELM V1 ACCEPTANCE: FAIL"
  exit 1
fi
