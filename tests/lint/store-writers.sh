#!/usr/bin/env bash
# store-writers.sh [--self-test] — fence the store: every evidence row enters
# through evidence.append / evidence.replace_stream, so no other code may open
# a store path for writing or hard-code the store root. Three shapes are the
# escape hatches, each one rule:
#   O_APPEND                       the raw append flag (flock-less writers)
#   open(…, "a…")                  a direct append-mode open
#   /var/lib/evidence              the store-root literal (only evidence.py's
#                                  DEFAULT_STORE may carry it; the wrappers and
#                                  CLI defaults honour EVIDENCE_STORE instead)
# Files are enumerated with find (the lint sandbox has no git); markdown and
# bytecode are skipped, and pkgs/evidence/evidence.py is the one sanctioned
# writer excluded from the sweep. The sweep's base directory is TREE (default
# "."; --self-test points it at a temporary planted tree so the root list is
# pinned, not just the patterns).
#
# Exit codes: 0 clean; 1 a hit (each printed as
# `store-writers: <file>:<line>: <pattern>`); 2 grep/find missing from PATH.
set -euo pipefail

ROOTS=(pkgs/evidence pkgs/helm tools/ledger tools/factory tools/session-start.sh tools/ritual.sh)
FIXTURES="tests/lint/fixtures/store"
TREE="."

P_APPEND='O_APPEND'
P_OPEN="open\([^)]*['\"]a[bt+]*['\"]"
P_LITERAL='/var/lib/evidence'

for tool in grep find; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "store-writers: $tool not on PATH" >&2
    exit 2
  fi
done

# The files a project sweep examines: every file under ROOTS except markdown,
# bytecode, and evidence.py, resolved under TREE.
sweep_files() {
  (
    cd "$TREE" || exit 2
    find "${ROOTS[@]}" -type f \
      ! -name '*.md' \
      ! -path '*/__pycache__/*' \
      ! -path 'pkgs/evidence/evidence.py'
  )
}

had_hit=0

# Print `store-writers: <file>:<line>: <label>` for every hit of `pattern` in
# `file`, setting the global `had_hit`.
scan() {
  local f="$1" pattern="$2" label="$3"
  local lineno
  while IFS=: read -r lineno _; do
    printf 'store-writers: %s:%s: %s\n' "$f" "$lineno" "$label"
    had_hit=1
  done < <(grep -nE "$pattern" "$TREE/$f" || true)
}

run_project() {
  local f
  had_hit=0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    scan "$f" "$P_APPEND" 'O_APPEND'
    scan "$f" "$P_OPEN" 'open(…,"a…")'
    scan "$f" "$P_LITERAL" '/var/lib/evidence'
  done < <(sweep_files)
  return "$had_hit"
}

# Count the hits of `pattern` in `file` (0 when none).
count_hits() {
  local f="$1" pattern="$2"
  grep -cE "$pattern" "$f" || true
}

# The six declared roots, written a second time as this assertion's own
# literal, so a root dropped from ROOTS fails the planted sweep rather than
# silently narrowing the fence.
PLANTED_ROOTS=(pkgs/evidence pkgs/helm tools/ledger tools/factory tools/session-start.sh tools/ritual.sh)

# Build a temporary tree carrying the six declared roots with exactly one
# O_APPEND hit per root (a _planted.py inside each directory root; one line
# appended to a copy of each file root), run the sweep over it, and require
# exactly one hit per root. A root missing from ROOTS yields no hit and fails
# here; pkgs/evidence/evidence.py is planted with a hit too and must stay
# excluded from the sweep.
planted_roots_check() {
  local root hits n
  SELF_TMP="$(mktemp -d)"
  trap 'rm -rf "$SELF_TMP"' EXIT
  for root in "${PLANTED_ROOTS[@]}"; do
    if [ -d "$root" ]; then
      mkdir -p "$SELF_TMP/$root"
      printf 'import os\n_PLANTED = os.O_APPEND\n' >"$SELF_TMP/$root/_planted.py"
    else
      mkdir -p "$SELF_TMP/$(dirname "$root")"
      cp "$root" "$SELF_TMP/$root"
      printf 'O_APPEND  # planted\n' >>"$SELF_TMP/$root"
    fi
  done
  printf 'import os\n_PLANTED = os.O_APPEND\n' >"$SELF_TMP/pkgs/evidence/evidence.py"

  TREE="$SELF_TMP"
  hits="$(run_project || true)"
  TREE="."

  for root in "${PLANTED_ROOTS[@]}"; do
    n="$(printf '%s\n' "$hits" | grep -cE "^store-writers: ${root}(/|:)" || true)"
    if [ "$n" -eq 0 ]; then
      echo "store-writers: self-test: root $root not swept" >&2
      exit 1
    fi
    if [ "$n" -gt 1 ]; then
      echo "store-writers: self-test: root $root swept $n times, expected 1" >&2
      exit 1
    fi
  done
  if printf '%s\n' "$hits" | grep -qF 'pkgs/evidence/evidence.py'; then
    echo "store-writers: self-test: pkgs/evidence/evidence.py must stay excluded from the sweep" >&2
    exit 1
  fi
}

self_check() {
  # Each bad fixture must produce exactly one hit of its own pattern, and
  # clean.py must produce none of any pattern; otherwise the gate is vacuous.
  # clean.py is probed with three separate counts (never a combined pattern:
  # under grep -E `\|` is a literal pipe, not alternation).
  local c
  c="$(count_hits "$FIXTURES/bad-append.py" "$P_APPEND")"
  if [ "$c" -ne 1 ]; then
    echo "store-writers: self-test: bad-append.py: expected 1 O_APPEND hit, got $c" >&2
    exit 1
  fi
  c="$(count_hits "$FIXTURES/bad-open.py" "$P_OPEN")"
  if [ "$c" -ne 1 ]; then
    echo "store-writers: self-test: bad-open.py: expected 1 open(…\"a…\") hit, got $c" >&2
    exit 1
  fi
  c="$(count_hits "$FIXTURES/bad-literal.sh" "$P_LITERAL")"
  if [ "$c" -ne 1 ]; then
    echo "store-writers: self-test: bad-literal.sh: expected 1 /var/lib/evidence hit, got $c" >&2
    exit 1
  fi
  c="$(count_hits "$FIXTURES/clean.py" "$P_APPEND")"
  if [ "$c" -ne 0 ]; then
    echo "store-writers: self-test: clean.py: expected 0 O_APPEND hits, got $c" >&2
    exit 1
  fi
  c="$(count_hits "$FIXTURES/clean.py" "$P_OPEN")"
  if [ "$c" -ne 0 ]; then
    echo "store-writers: self-test: clean.py: expected 0 open(…\"a…\") hits, got $c" >&2
    exit 1
  fi
  c="$(count_hits "$FIXTURES/clean.py" "$P_LITERAL")"
  if [ "$c" -ne 0 ]; then
    echo "store-writers: self-test: clean.py: expected 0 /var/lib/evidence hits, got $c" >&2
    exit 1
  fi
  planted_roots_check
}

if [ $# -gt 0 ] && [ "$1" = "--self-test" ]; then
  self_check
else
  run_project
fi
