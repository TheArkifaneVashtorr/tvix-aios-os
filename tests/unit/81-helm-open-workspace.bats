#!/usr/bin/env bats
# helm-open-workspace (pkgs/helm/helm-open-workspace.sh, a template whose
# @WORKSPACES_JSON_FILE@ the Helm module substitutes with the absolute store
# path of a JSON file holding control.workspaces). These tests write that
# JSON to a file and substitute the path the way nixosModules/helm.nix will,
# then run the launcher with stub nix/bash/mountpoint on PATH (real jq): no
# nix develop, no /run/baskets is ever touched, and by default no claude -- a
# workspace opens at an interactive shell (bash -i, entering the dev shell
# when one is declared) and only runs a program when its `command` option
# names one (e.g. "claude" or "dsh-openrouter"). The basket prompt is the
# copy deck verbatim (K15) and the YubiKey ceremony stays human (K13) -- the
# launcher only prints and waits.
#
# Shown to fail first (2026-09-03): the template did not exist, sed
# produced an empty script, and every case below failed.
# Re-shown to fail (H2): the "no claude by default" assertions are red
# against the old `bash -ic claude` launcher before the launcher drops it.
# Re-shown to fail (H2b): the single-quote test is red against the old
# @WORKSPACES_JSON@ splice (the quote breaks the `readonly` literal, so
# `bash -n` fails) before the JSON moves to a file.

TEMPLATE="$BATS_TEST_DIRNAME/../../pkgs/helm/helm-open-workspace.sh"

setup() {
  REAL_BASH=$(command -v bash)
  STUBS="$BATS_TEST_TMPDIR/bin"
  LAUNCHER="$BATS_TEST_TMPDIR/helm-open-workspace"
  mkdir -p "$STUBS" "$BATS_TEST_TMPDIR/plain" "$BATS_TEST_TMPDIR/shelled" "$BATS_TEST_TMPDIR/boxed" \
    "$BATS_TEST_TMPDIR/commanded" "$BATS_TEST_TMPDIR/commanded-shell"
  make_stub bash bash-stub
  make_stub nix nix-stub
  # mountpoint: exit 0 iff "$STUBS/mounted" exists, like the real probe of
  # an (un)mounted basket directory.
  make_stub mountpoint mountpoint-stub
  printf '{"plain": {"path": "%s", "devShell": null, "basket": null, "command": null}, "shelled": {"path": "%s", "devShell": "default", "basket": null, "command": null}, "boxed": {"path": "%s", "devShell": null, "basket": "demo", "command": null}, "commanded": {"path": "%s", "devShell": null, "basket": null, "command": "dsh-openrouter"}, "commanded-shell": {"path": "%s", "devShell": "default", "basket": null, "command": "dsh-openrouter"}}' \
    "$BATS_TEST_TMPDIR/plain" "$BATS_TEST_TMPDIR/shelled" "$BATS_TEST_TMPDIR/boxed" "$BATS_TEST_TMPDIR/commanded" "$BATS_TEST_TMPDIR/commanded-shell" \
    >"$BATS_TEST_TMPDIR/workspaces.json"
  render_launcher "$BATS_TEST_TMPDIR/workspaces.json"
}

# Renders the launcher the way nixosModules/helm.nix does: substitute the
# @WORKSPACES_JSON_FILE@ placeholder with the absolute path of the workspaces
# JSON file (never the JSON itself -- a single quote in a value must not be
# spliced into shell syntax), plus the bash/nix names. $1 = JSON file path.
render_launcher() {
  sed -e "s|@WORKSPACES_JSON_FILE@|$1|" \
    -e "s|@BASH_BIN@|bash|g" \
    -e "s|@NIX_BIN@|nix|g" \
    "$TEMPLATE" >"$LAUNCHER"
}

# $1: stub name, $2: label the stub prints. bash/nix stubs exit with the code
# from "<stub>.exit" when that file exists (default 0); mountpoint exits 0
# iff "<stub dir>/mounted" exists.
make_stub() {
  {
    echo "#!$REAL_BASH"
    echo "echo \"$2 args=\$* pwd=\$PWD\""
    if [[ $1 == mountpoint ]]; then
      echo '[[ -e "$(dirname "$0")/mounted" ]]'
    else
      echo 'if [[ -f "$0.exit" ]]; then exit "$(cat "$0.exit")"; fi'
    fi
  } >"$STUBS/$1"
  chmod +x "$STUBS/$1"
}

@test "an unknown workspace exits 2 without spawning anything" {
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" nope
  [ "$status" -eq 2 ]
  [[ "$output" == *"unknown workspace: nope"* ]]
  [[ "$output" != *"stub"* ]]
}

@test "no argument exits 2 with usage" {
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER"
  [ "$status" -eq 2 ]
  [[ "$output" == *"usage"* ]]
  [[ "$output" != *"stub"* ]]
}

@test "devShell null: cd into the workspace and exec an interactive bash (no claude, no nix, no basket prompt)" {
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" plain
  [ "$status" -eq 0 ]
  [[ "$output" == *"bash-stub args=-i pwd=$BATS_TEST_TMPDIR/plain"* ]]
  [[ "$output" != *"nix-stub"* ]]
  [[ "$output" != *"mountpoint-stub"* ]]
  [[ "$output" != *"basket"* ]]
  [[ "$output" != *"claude"* ]]
}

@test "devShell set: cd into the workspace and exec nix develop .#default -c bash -i (no claude)" {
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" shelled
  [ "$status" -eq 0 ]
  [[ "$output" == *"nix-stub args=develop .#default -c bash -i pwd=$BATS_TEST_TMPDIR/shelled"* ]]
  [[ "$output" != *"bash-stub"* ]]
  [[ "$output" != *"basket"* ]]
  [[ "$output" != *"claude"* ]]
}

@test "command set, devShell null: cd into the workspace and exec bash -ic dsh-openrouter (not the old hardcoded claude)" {
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" commanded
  [ "$status" -eq 0 ]
  [[ "$output" == *"bash-stub args=-ic dsh-openrouter pwd=$BATS_TEST_TMPDIR/commanded"* ]]
  [[ "$output" != *"claude"* ]]
  [[ "$output" != *"nix-stub"* ]]
  [[ "$output" != *"basket"* ]]
}

@test "command set and devShell set: cd into the workspace and exec nix develop .#default -c bash -ic dsh-openrouter" {
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" commanded-shell
  [ "$status" -eq 0 ]
  [[ "$output" == *"nix-stub args=develop .#default -c bash -ic dsh-openrouter pwd=$BATS_TEST_TMPDIR/commanded-shell"* ]]
  [[ "$output" != *"bash-stub"* ]]
  [[ "$output" != *"basket"* ]]
}

@test "a single quote in a workspace path or command stays inside the JSON (never spliced into shell syntax)" {
  # SECURITY (H2 Opus gate): a single quote in a workspace value must not
  # break out of the JSON. The launcher is rendered from a JSON *file* (the
  # module writes one with pkgs.formats.json), so the rendered script parses
  # and the value round-trips byte-for-byte.
  quoted_dir="$BATS_TEST_TMPDIR/quo'te"
  mkdir -p "$quoted_dir"
  printf '{"quoted": {"path": "%s", "devShell": null, "basket": null, "command": "%s"}}' \
    "$quoted_dir" "cmd'with'quotes" >"$BATS_TEST_TMPDIR/workspaces-quote.json"
  render_launcher "$BATS_TEST_TMPDIR/workspaces-quote.json"
  bash -n "$LAUNCHER"
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" quoted
  [ "$status" -eq 0 ]
  [[ "$output" == *"bash-stub args=-ic cmd'with'quotes pwd=$quoted_dir"* ]]
}

@test "basket set and not mounted: prints the exact sudo mount line and waits for Enter" {
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" boxed <<< ""
  [ "$status" -eq 0 ]
  [[ "$output" == *"mountpoint-stub args=-q /run/baskets/demo"* ]]
  [[ "$output" == *"This workspace needs its basket. Run:"* ]]
  [[ "$output" == *"basket mount /var/lib/baskets/store/demo"* ]]
  [[ "$output" == *"--identity"* ]]
  [[ "$output" == *"…then press Enter."* ]]
  [[ "$output" == *"bash-stub args=-i pwd=$BATS_TEST_TMPDIR/boxed"* ]]
  [[ "$output" != *"claude"* ]]
}

@test "basket set and already mounted: no prompt, straight to the shell" {
  touch "$STUBS/mounted"
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" boxed
  [ "$status" -eq 0 ]
  # The probe ran and found the basket mounted, so no prompt lines appear.
  [[ "$output" == *"mountpoint-stub args=-q /run/baskets/demo"* ]]
  [[ "$output" != *"This workspace needs its basket"* ]]
  [[ "$output" != *"press Enter"* ]]
  [[ "$output" == *"bash-stub args=-i pwd=$BATS_TEST_TMPDIR/boxed"* ]]
}

@test "the exec target's exit code is the launcher's exit code" {
  echo 5 >"$STUBS/bash.exit"
  run env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" plain
  [ "$status" -eq 5 ]
}

@test "the basket prompt really waits: nothing is exec'd until Enter arrives" {
  fifo="$BATS_TEST_TMPDIR/enter"
  out="$BATS_TEST_TMPDIR/out"
  mkfifo "$fifo"
  # 3>&-: close bats' own fd 3 or bats waits on this child forever (same
  # lesson as 70-dsh-openrouter.bats).
  env PATH="$STUBS:$PATH" "$REAL_BASH" "$LAUNCHER" boxed <"$fifo" >"$out" 2>&1 3>&- &
  pid=$!
  # Hold the fifo's write side open so the launcher's stdin is open but
  # empty: it can only get past `read -r` when a line arrives.
  exec 9>"$fifo"
  for _ in $(seq 1 100); do
    grep -q "press Enter" "$out" 2>/dev/null && break
    sleep 0.1
  done
  grep -q "press Enter" "$out"
  # The prompt is up and the launcher is blocked in read: nothing spawned.
  ! grep -q "bash-stub" "$out"
  printf '\n' >&9
  exec 9>&-
  wait "$pid"
  [ "$?" -eq 0 ]
  grep -q "bash-stub args=-i pwd=$BATS_TEST_TMPDIR/boxed" "$out"
}
