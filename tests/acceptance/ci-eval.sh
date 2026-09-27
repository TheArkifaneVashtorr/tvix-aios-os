#!/usr/bin/env bash
# tests/acceptance/ci-eval.sh — PL26 (plan 2026-09-11-platform.md): CI
# evaluates every flake check in its own process, bounded memory, instead of
# one `nix flake check --no-build` whose single heap must hold the whole
# ~135-check evaluation graph (many whole nixosSystems): measured 24-27 GiB
# `heapSize` (NIX_SHOW_STATS) where the GitHub runner has 16 GB — why CI
# runs #1-3 died with no logs: the runner VM OOMed at the cgroup level,
# before Nix's own 20-minute step timeout could fire and before any log
# uploaded. Both properties measured (plan Facts 3-5), not assumed: each
# per-check eval process peaks at <=1.7 GiB (the largest whole-nixosSystem
# check), so the loop survives the same 14G cap that SIGKILLs the old
# single-process run; and the full loop takes minutes warm, well inside
# the job's 45-minute budget.
#
# The per-check eval also carries --option allow-import-from-derivation
# false: the structural IFD lint. Its refusal is unconditional, never
# cache-dependent (plan Facts 6-7), so a check that coerces a derivation
# output during evaluation is reported by name as FAIL, never papered over
# — a named FAIL line per check beats the old single log wall.
#
# PL27 (plan 2026-09-11-platform.md): the named, permanent exceptions —
# checks whose guard failure is a measured, accepted limit, never a
# silent catch-all (a FAIL from any check not listed here stays a loud
# FAIL). A SKIP is not a pass: each check below still builds and runs for
# real on every actual build; only this eval-only lens cannot see it.
#   seat-assertion-negative — the harness-payload-empty-skills arm (SA8b)
#     needs a Nix-built truly-empty skills/ dir (git carries none), and the
#     dsh-openrouter assert's pathExists on that derivation's output is the
#     exact IFD this guard refuses, unconditionally (PL26 Facts 6); the
#     assert still fires on every real build.
#   invariant-credential-plaintext, invariant-policy-nix — the same arm,
#     reached through their deps on seat-assertion-negative.
#   export-eval — PL19's own documented, unconditional IFD (the export
#     tree is realised to be imported; measured 2026-09-26). It is defined
#     wherever docs/ledger/publish.toml exists, so in this tree it cannot
#     stay outside the loop — it gets the same named SKIP.
#
# Usage: tests/acceptance/ci-eval.sh [flake]
#   <flake> defaults to '.'. Any flake ref nix accepts works, which is how
#   tools/publish-snapshot points this script at a clean clone of the
#   public mirror instead of the working tree.
# Exit: 0 every check evaluated (SKIPs are named exceptions, not failures);
#   1 at least one named FAIL; 2 the check list could not even be
#   enumerated (nix missing, flake broken).

set -uo pipefail

flake=${1:-.}

command -v nix >/dev/null 2>&1 || {
  echo 'ci-eval: nix is not on PATH' >&2
  exit 2
}

# The check list: attrNames forces nothing, so this single eval is cheap no
# matter how big the checks are. The plan's `nix eval --json --apply
# builtins.attrNames` shape, printed newline-separated via --raw's
# concatStringsSep so a bare CI runner needs no JSON parser.
names=$(nix eval --raw "$flake#checks.x86_64-linux" \
  --apply 'cs: builtins.concatStringsSep "\n" (builtins.attrNames cs)') || {
  echo "ci-eval: cannot list $flake#checks.x86_64-linux" >&2
  exit 2
}
[ -n "$names" ] || {
  echo "ci-eval: $flake#checks.x86_64-linux holds no checks" >&2
  exit 2
}

fail=0
skip=0
total=0
while IFS= read -r name; do
  [ -n "$name" ] || continue
  total=$((total + 1))
  # PL27's named exceptions (the header comment carries each reason):
  # skipped before the eval, printed as SKIP — never counted as FAIL and
  # never silently dropped from the table.
  case $name in
    seat-assertion-negative | invariant-credential-plaintext | invariant-policy-nix | export-eval)
      printf '%s SKIP\n' "$name"
      skip=$((skip + 1))
      continue
      ;;
  esac
  # One process per check: the memory bound is the loop's whole point. The
  # IFD option rides every invocation — the guard is the loop, not a flag
  # somewhere else.
  if err=$(nix eval --raw "$flake#checks.x86_64-linux.$name.drvPath" \
    --option allow-import-from-derivation false 2>&1); then
    printf '%s PASS\n' "$name"
  else
    printf '%s FAIL\n' "$name"
    # The failure's first lines, indented under the name — a named cause
    # per check, never a second log wall.
    printf '%s\n' "$err" | sed -n '1,4p' | sed 's/^/    /'
    fail=$((fail + 1))
  fi
done <<EOF
$names
EOF

printf 'ci-eval: %d checks, %d pass, %d skip, %d fail (%s)\n' \
  "$total" "$((total - fail - skip))" "$skip" "$fail" "$flake"
[ "$fail" -eq 0 ]
