#!/usr/bin/env bats
# tests/unit/99-home-classes.bats -- the home-classes checker (US0,
# pkgs/home-classes/home_classes.py through the tools/home-classes shim)
# against a fixture home under BATS_TEST_TMPDIR: the list's schema
# (Interface 1) and the CLI's three verbs (Interface 2), the default
# --file/--home resolution and the shim's python3 gate (Interface 3).
# Every case names the one-line mutant that turns it red (the section's
# Tests table). The fixtures stand in for a live user space -- the real
# operator home and the real claims ledger are the operator's own run's
# to check, never a test's; the gap is named per
# docs/decisions/2026-09-03-test-based-reality-amendments.md.

HC="$BATS_TEST_DIRNAME/../../tools/home-classes"

setup() {
  bats_require_minimum_version 1.5.0
  T="$BATS_TEST_TMPDIR"
  export T
  Z64=$(printf '%064d' 0)
  FS64=$(printf 'f%.0s' $(seq 64))
  mkdir -p \
    "$T/home/.config" \
    "$T/home/.local/share" \
    "$T/home/.local/state" \
    "$T/home/.local/bin" \
    "$T/home/.cache"
  printf 'content\n' >"$T/home/a"
  printf 'content\n' >"$T/home/.config/x"
  printf 'content\n' >"$T/home/.config/y"
  printf 'content\n' >"$T/home/.local/share/p"
  printf 'content\n' >"$T/home/.local/state/q"
  printf 'content\n' >"$T/home/.cache/c"
  # Interface 1's shape covering the fixture home: seven rows, four
  # children. `.local` is deliberately a plain data row while `.config`,
  # `.local/share` and `.local/state` are split (case 3's discriminating
  # row: only a split row's children are enumerated, never a plain
  # directory's).
  cat >"$T/list.toml" <<'EOF'
version = 1

[[entry]]
name = "a"
class = "data"

[[entry]]
name = ".config"
class = "split"

[[entry.children]]
name = "x"
class = "config"

[[entry.children]]
name = "y"
class = "data"

[[entry]]
name = ".local"
class = "data"

[[entry]]
name = ".local/share"
class = "split"

[[entry.children]]
name = "p"
class = "data"

[[entry]]
name = ".local/state"
class = "split"

[[entry.children]]
name = "q"
class = "cache"

[[entry]]
name = ".local/bin"
class = "data"

[[entry]]
name = ".cache"
class = "cache"
EOF
}

@test "lint on the covered fixture is ok with the counts" {
  run --separate-stderr bash "$HC" lint --file "$T/list.toml" --home "$T/home"
  [ "$status" -eq 0 ]
  [ "$output" = 'home-classes: ok 7 entries, 4 children, 0 stale, 0 backups' ]
  [ "$stderr" = '' ]
}

@test "a home entry with no row is unclassified and fails lint" {
  mkdir "$T/home/zz"
  run --separate-stderr bash "$HC" lint --file "$T/list.toml" --home "$T/home"
  [ "$status" -eq 1 ]
  [ "$output" = 'home-classes: unclassified: zz' ]
}

@test "a split child with no row is unclassified; a plain directory is not walked" {
  sed -i '/^\[\[entry\.children\]\]$/{N;/\nname = "y"$/{N;d;}}' "$T/list.toml"
  [ "$(grep -c 'name = "y"' "$T/list.toml")" -eq 0 ]
  run --separate-stderr bash "$HC" lint --file "$T/list.toml" --home "$T/home"
  [ "$status" -eq 1 ]
  [ "$output" = 'home-classes: unclassified: .config/y' ]
}

@test "a row whose path is gone is stale and does not fail lint" {
  printf '\n[[entry]]\nname = "gone"\nclass = "data"\n' >>"$T/list.toml"
  run --separate-stderr bash "$HC" lint --file "$T/list.toml" --home "$T/home"
  [ "$status" -eq 0 ]
  [ "$output" = "$(printf 'home-classes: stale: gone\nhome-classes: ok 8 entries, 4 children, 1 stale, 0 backups')" ]
}

@test "split on a name outside the allowed three is refused naming the row" {
  sed -i '/^name = "\.cache"$/{n;s/^class = "cache"$/class = "split"/}' "$T/list.toml"
  printf '\n[[entry.children]]\nname = "c"\nclass = "cache"\n' >>"$T/list.toml"
  run --separate-stderr bash "$HC" lint --file "$T/list.toml" --home "$T/home"
  [ "$status" -eq 2 ]
  [ "$stderr" = 'home-classes: row 7: name: split allowed only for .config, .local/share, .local/state' ]
  [ "$output" = '' ]
}

@test "a class outside the enum is refused naming the row" {
  sed -i '0,/^class = "data"$/s//class = "secret"/' "$T/list.toml"
  run --separate-stderr bash "$HC" lint --file "$T/list.toml" --home "$T/home"
  [ "$status" -eq 2 ]
  [ "$stderr" = 'home-classes: row 1: class: not one of config, data, cache, split' ]
  [ "$output" = '' ]
}

@test "hash prints the sha256 of the list's bytes" {
  hex=$(sha256sum "$T/list.toml" | cut -d' ' -f1)
  run --separate-stderr bash "$HC" hash --file "$T/list.toml"
  [ "$status" -eq 0 ]
  [ "$output" = "sha256:$hex" ]
}

@test "check --sha256 passes the real digest and fails a mismatch" {
  hex=$(sha256sum "$T/list.toml" | cut -d' ' -f1)
  run --separate-stderr bash "$HC" check --file "$T/list.toml" --home "$T/home" --sha256 "$hex"
  [ "$status" -eq 0 ]
  [ "$output" = 'home-classes: ok 7 entries, 4 children, 0 stale, 0 backups' ]
  run --separate-stderr bash "$HC" check --file "$T/list.toml" --home "$T/home" --sha256 "$Z64"
  [ "$status" -eq 1 ]
  [ "$output" = "home-classes: hash mismatch: expected $Z64 got $hex" ]
}

@test "check --claims reads the confirmed row's digest, not the decoy's" {
  hex=$(sha256sum "$T/list.toml" | cut -d' ' -f1)
  cat >"$T/claims.toml" <<EOF
[[claim]]
id = "aaa-decoy"
evidence = "operator:2026-09-24 sha256:$FS64"

[[claim]]
id = "home-classes-confirmed"
evidence = "operator:2026-09-24 sha256:$hex"
EOF
  run --separate-stderr bash "$HC" check --file "$T/list.toml" --home "$T/home" --claims "$T/claims.toml"
  [ "$status" -eq 0 ]
  [ "$output" = 'home-classes: ok 7 entries, 4 children, 0 stale, 0 backups' ]
  sed -i "s/sha256:$hex/sha256:$FS64/" "$T/claims.toml"
  run --separate-stderr bash "$HC" check --file "$T/list.toml" --home "$T/home" --claims "$T/claims.toml"
  [ "$status" -eq 1 ]
  [ "$output" = "home-classes: hash mismatch: expected $FS64 got $hex" ]
}

@test "check without --sha256 or --claims is refused" {
  run --separate-stderr bash "$HC" check --file "$T/list.toml" --home "$T/home"
  [ "$status" -eq 2 ]
  [ "$stderr" = 'home-classes: check needs --sha256 or --claims' ]
  [ "$output" = '' ]
}

@test "a name ending .hm-bak is a backup, not an unclassified entry" {
  touch "$T/home/.bashrc.hm-bak"
  run --separate-stderr bash "$HC" lint --file "$T/list.toml" --home "$T/home"
  [ "$status" -eq 0 ]
  [ "$output" = "$(printf 'home-classes: backup: .bashrc.hm-bak\nhome-classes: ok 7 entries, 4 children, 0 stale, 1 backups')" ]
}

@test "check never writes: a read-only home and scratch dir still pass" {
  hex=$(sha256sum "$T/list.toml" | cut -d' ' -f1)
  chmod a-w "$T/home" "$T"
  run bash "$HC" check --file "$T/list.toml" --home "$T/home" --sha256 "$hex"
  chmod u+w "$T/home" "$T"
  [ "$status" -eq 0 ]
  [ "$output" = 'home-classes: ok 7 entries, 4 children, 0 stale, 0 backups' ]
}

@test "an unreadable list file is refused before any output" {
  run --separate-stderr bash "$HC" lint --file "$T/absent.toml" --home "$T/home"
  [ "$status" -eq 2 ]
  [ "$stderr" = "home-classes: cannot read $T/absent.toml: No such file or directory" ]
  [ "$output" = '' ]
}

@test "a TOML parse error is refused naming the file" {
  printf 'version = 1\n[[entry]]\nname = "a"\nclass = "data"\n[[entry]\n' >"$T/bad.toml"
  run --separate-stderr bash "$HC" lint --file "$T/bad.toml" --home "$T/home"
  [ "$status" -eq 2 ]
  [[ "$stderr" == "home-classes: $T/bad.toml: "* ]]
  [ "$output" = '' ]
}

@test "the default file resolves under XDG_STATE_HOME, else under the home" {
  mkdir -p "$T/home2/.local/state/user-spaces" "$T/home3" "$T/xdg/user-spaces"
  printf 'content\n' >"$T/home2/b"
  printf 'content\n' >"$T/home3/c"
  # home2's list covers home2 only (b plus the .local its state dir
  # lives in); the xdg one covers home3 only -- reading the wrong list
  # against either home fails, so the two default resolutions are each
  # pinned by the other's absence.
  printf 'version = 1\n\n[[entry]]\nname = "b"\nclass = "data"\n\n[[entry]]\nname = ".local"\nclass = "data"\n' >"$T/home2/.local/state/user-spaces/home-classes.toml"
  printf 'version = 1\n\n[[entry]]\nname = "c"\nclass = "data"\n' >"$T/xdg/user-spaces/home-classes.toml"
  run --separate-stderr env -u XDG_STATE_HOME HOME="$T/home2" bash "$HC" lint
  [ "$status" -eq 0 ]
  [ "$output" = 'home-classes: ok 2 entries, 0 children, 0 stale, 0 backups' ]
  run --separate-stderr env HOME="$T/home3" XDG_STATE_HOME="$T/xdg" bash "$HC" lint
  [ "$status" -eq 0 ]
  [ "$output" = 'home-classes: ok 1 entries, 0 children, 0 stale, 0 backups' ]
}

@test "the shim refuses without python3 and runs --help with it" {
  mkdir -p "$T/nopython" "$T/onlypy3"
  for tool in bash dirname cat ls cp mv rm; do
    ln -s "$(command -v "$tool")" "$T/nopython/$tool"
  done
  for tool in bash dirname python3; do
    ln -s "$(command -v "$tool")" "$T/onlypy3/$tool"
  done
  run --separate-stderr env PATH="$T/nopython:/usr/bin" bash "$HC" --help
  [ "$status" -eq 2 ]
  [ "$stderr" = 'tools/home-classes: python3 is not on PATH; run under nix develop -c' ]
  run --separate-stderr bash "$HC" --help
  [ "$status" -eq 0 ]
  run --separate-stderr env PATH="$T/onlypy3" bash "$HC" --help
  [ "$status" -eq 0 ]
}
