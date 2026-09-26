#!/usr/bin/env bats
# tools/experiments/jaz/blind.sh — strip a drafted plan's authorship and the
# JAZ-experiment's own vocabulary before a grader ever sees it (spec
# docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md, D5:
# a grader must not learn which arm or workflow wrote a plan). Bash and
# coreutils only (shuf, sed, mkdir): the script has no devShell of its own.

setup() {
  BLIND="$BATS_TEST_DIRNAME/../../tools/experiments/jaz/blind.sh"
  T="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/jazblind.XXXXXX")"
  MAP="$T/mapping.tsv"
  BDIR="$T/blind"

  DRAFT_A="$T/draft-a.md"
  printf '**Author:** fable\n' >"$DRAFT_A"
  printf '**Status:** dispatch\n' >>"$DRAFT_A"
  printf '**Plan file:** docs/superpowers/plans/2026-09-01-a.md\n' >>"$DRAFT_A"
  printf '# Plan A\n\n' >>"$DRAFT_A"
  printf 'This reads the packet at scratch/packet/mechanical.md and writes scratch/draft-0.md,\n' >>"$DRAFT_A"
  printf 'logging to scratch/queries.log and a sub-agent answer at scratch/q/1.md.\n\n' >>"$DRAFT_A"
  printf 'It is arm B of the JAZ by-reference experiment.\n' >>"$DRAFT_A"

  DRAFT_B="$T/draft-b.md"
  printf '**Author:** hand\n' >"$DRAFT_B"
  printf '**Status:** revise\n' >>"$DRAFT_B"
  printf '**Plan file:** docs/superpowers/plans/2026-09-01-b.md\n' >>"$DRAFT_B"
  printf '# Plan B\n\n' >>"$DRAFT_B"
  printf 'No such mention here, but it does reference packets and an arm of the study.\n' >>"$DRAFT_B"
}

teardown() {
  rm -rf "$T"
}

@test "strips the metadata lines, redacts scratch paths, and redacts the vocabulary, case-insensitive whole word" {
  run bash "$BLIND" "$MAP" "$BDIR" "$DRAFT_A" "$DRAFT_B"
  [ "$status" -eq 0 ]

  # exactly two blinded files, named P<n>.md, not by the original basenames
  local n
  n=$(find "$BDIR" -maxdepth 1 -name 'P*.md' | wc -l)
  [ "$n" -eq 2 ]
  [ ! -e "$BDIR/draft-a.md" ]
  [ ! -e "$BDIR/draft-b.md" ]

  for f in "$BDIR"/P*.md; do
    ! grep -q '^\*\*Author:\*\*' "$f"
    ! grep -q '^\*\*Status:\*\*' "$f"
    ! grep -q '^\*\*Plan file:\*\*' "$f"
    ! grep -q 'packet/mechanical.md' "$f"
    ! grep -q 'draft-0.md' "$f"
    ! grep -q 'queries.log' "$f"
    ! grep -q 'q/1.md' "$f"
    ! grep -qiw 'packet' "$f"
    ! grep -qiw 'packets' "$f"
    ! grep -qiw 'jaz' "$f"
    ! grep -qiw 'arm' "$f"
    ! grep -qiw 'by-reference' "$f"
  done
  # draft-a had scratch paths and vocabulary words to redact; confirm the
  # redaction markers actually landed somewhere in the blinded output rather
  # than the whole line having been dropped some other way.
  grep -lq '<path>' "$BDIR"/P*.md
  grep -lq '\[x\]' "$BDIR"/P*.md
}

@test "the mapping has one row per draft, opaque ids, and covers both original paths" {
  run bash "$BLIND" "$MAP" "$BDIR" "$DRAFT_A" "$DRAFT_B"
  [ "$status" -eq 0 ]
  [ "$(wc -l <"$MAP")" -eq 2 ]
  while IFS=$'\t' read -r id path; do
    [[ "$id" =~ ^P[0-9]+$ ]]
  done <"$MAP"
  grep -qF "$(printf '%s' "$DRAFT_A")" "$MAP"
  grep -qF "$(printf '%s' "$DRAFT_B")" "$MAP"
}

@test "too few arguments is a usage error, exit 2, and writes nothing" {
  run bash "$BLIND" "$MAP" "$BDIR"
  [ "$status" -eq 2 ]
  [ ! -e "$MAP" ]
}
