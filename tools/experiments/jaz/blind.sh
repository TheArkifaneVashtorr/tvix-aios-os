#!/usr/bin/env bash
# tools/experiments/jaz/blind.sh — strip authorship and the JAZ-experiment's
# own vocabulary out of a drafted plan before any grader sees it (spec
# docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md, D5: a
# grader must never learn which arm or workflow wrote a plan). Bash and
# coreutils only (shuf, sed, mkdir, find) — this runs on the host, outside
# any devShell, so no nix, python3 or jq.
#
# usage: blind.sh <mapping-out> <blind-dir> <draft-path>...
#   mapping-out   file to write "id<TAB>original-path" lines to, one per
#                 draft; kept away from graders (it is the answer key)
#   blind-dir     directory the blinded copies are written into, as P<n>.md
#   draft-path... one or more plan/draft files to blind
#
# Per draft: lines starting "**Author:**", "**Status:**" or "**Plan file:**"
# are dropped; any whitespace-free token containing packet/, draft-,
# queries.log or /q/ is replaced whole by the literal string <path>; and the
# whole words (case-insensitive) packet, packets, JAZ, arm, by-reference are
# replaced by [x]. Which draft gets which P<n> id is randomized (shuf) so the
# id order carries no information about the input order.
set -euo pipefail
export LC_ALL=C

usage() {
  printf 'usage: blind.sh <mapping-out> <blind-dir> <draft-path>...\n'
}

die() {
  printf 'blind.sh: %s\n' "$1" >&2
  exit 2
}

(($# >= 3)) || {
  usage >&2
  die 'need a mapping-out path, a blind-dir and at least one draft-path'
}

mapping_out=$1
blind_dir=$2
shift 2
drafts=("$@")

for d in "${drafts[@]}"; do
  [ -f "$d" ] || die "not a file: $d"
done

case $mapping_out in
  */*) mkdir -p "${mapping_out%/*}" ;;
esac
mkdir -p "$blind_dir"

n=${#drafts[@]}
# order[i] is the P-number the (i+1)th draft gets; a shuffled permutation of
# 1..n, so the id assigned to a draft carries no information about its
# position in argv.
mapfile -t order < <(seq 1 "$n" | shuf)

: >"$mapping_out"
for ((i = 0; i < n; i++)); do
  draft=${drafts[i]}
  id="P${order[i]}"
  out="$blind_dir/$id.md"
  if ! sed -E \
    -e '/^\*\*Author:\*\*/d' \
    -e '/^\*\*Status:\*\*/d' \
    -e '/^\*\*Plan file:\*\*/d' \
    -e 's#[^[:space:]]*(packet/|draft-|queries\.log|/q/)[^[:space:]]*#<path>#g' \
    -e 's/\b(packets?|jaz|arm|by-reference)\b/[x]/gI' \
    "$draft" >"$out"; then
    die "could not write $out"
  fi
  printf '%s\t%s\n' "$id" "$draft" >>"$mapping_out"
done
