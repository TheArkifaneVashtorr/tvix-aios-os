#!/usr/bin/env bash
set -euo pipefail
# End-to-end unit test of the acceptance drill's success path:
# tests/acceptance/gaming.sh, run with GAMING_DRILL_NONINTERACTIVE=1 (skips
# the steps that start Steam or need an operator watching the screen) and a
# PATH of stub binaries standing in for the whole gaming tool set, must exit
# 0 and print "GAMING ACCEPTANCE: PASS" as its last line. This is the
# regression test for the EXIT trap bug: `work` was declared `local` inside
# main(), so the top-level `trap 'rm -rf "$work"' EXIT` referenced an unset
# variable under `set -u` once main() returned, and a fully passing drill
# still exited non-zero.

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$here/../.." && pwd)"
drill="$repo_root/tests/acceptance/gaming.sh"

stub_dir=$(mktemp -d)
trap 'rm -rf "$stub_dir"' EXIT

# #!/bin/sh (not /usr/bin/env, which the pure Nix build sandbox behind
# checks.drill-unit does not provide) and POSIX-only syntax: these are
# exec'd directly by gaming.sh (and, for iptables-save/ip6tables-save, by
# the sudo stub in turn), so their shebang has to resolve inside that
# sandbox too.
cat >"$stub_dir/steam" <<'EOF'
#!/bin/sh
exit 0
EOF

cat >"$stub_dir/gamemoded" <<'EOF'
#!/bin/sh
if [ "${1:-}" = "-s" ]; then
  echo "gamemode is inactive"
fi
exit 0
EOF

cat >"$stub_dir/gamescope" <<'EOF'
#!/bin/sh
echo "gamescope 3.14.0"
exit 0
EOF

cat >"$stub_dir/mangohud" <<'EOF'
#!/bin/sh
echo "MangoHud 0.7.1"
exit 0
EOF

cat >"$stub_dir/ss" <<'EOF'
#!/bin/sh
exit 0
EOF

cat >"$stub_dir/sudo" <<'EOF'
#!/bin/sh
exec "$@"
EOF

cat >"$stub_dir/iptables-save" <<'EOF'
#!/bin/sh
exit 0
EOF

cat >"$stub_dir/ip6tables-save" <<'EOF'
#!/bin/sh
exit 0
EOF

chmod +x "$stub_dir"/steam "$stub_dir"/gamemoded "$stub_dir"/gamescope \
  "$stub_dir"/mangohud "$stub_dir"/ss "$stub_dir"/sudo \
  "$stub_dir"/iptables-save "$stub_dir"/ip6tables-save

set +e
output=$(PATH="$stub_dir:$PATH" GAMING_DRILL_NONINTERACTIVE=1 bash "$drill" 2>&1)
status=$?
set -e

if [[ "$status" -ne 0 ]]; then
  echo "drill-success: expected exit 0, got $status" >&2
  printf '%s\n' "$output" >&2
  exit 1
fi

last_line=$(printf '%s\n' "$output" | tail -n1)
if [[ "$last_line" != "GAMING ACCEPTANCE: PASS" ]]; then
  echo "drill-success: expected last line 'GAMING ACCEPTANCE: PASS', got: $last_line" >&2
  printf '%s\n' "$output" >&2
  exit 1
fi

echo ok
