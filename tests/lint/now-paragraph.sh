#!/usr/bin/env bash
# now-paragraph.sh [--self-test | FILE] — cap the board's Now paragraph at ten
# wrapped lines. The measure is wrapped width at 80 columns, not raw physical
# newlines: the real board writes its Now paragraph as ONE physical line, so a
# raw `wc -l` reads 1 and can never fail it. The text from the **OPEN line to
# the next blank line is folded at 80 columns and the folded line count is what
# the cap bounds.
#
#   check_file FILE  caps the extracted paragraph's wrapped line count at 10
#   --self-test      builds one-physical-line fixtures at the boundary (793 x's
#                    folds to exactly 10; 794 folds to 11) and asserts each is
#                    judged right
#
# Exit codes: 0 the paragraph fits; 1 it does not (or a fixture misbehaved); 2 a
# measuring tool is missing from PATH. `fold` is coreutils, already on the
# devShell and the pkgs.runCommand sandbox PATHs (alongside wc/grep/test).
set -euo pipefail

CAP=10

for tool in fold wc; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "now-paragraph: $tool not on PATH" >&2
    exit 2
  fi
done

# Print the Now paragraph's text: the **OPEN line and every following non-blank
# line up to the next blank line (the blank line itself is not part of the
# paragraph). Physical lines inside the paragraph keep their breaks, which fold
# treats as existing wrap points. The text is newline-terminated so the pipeline
# below counts the final partial folded line too, not one fewer; a board with no
# **OPEN paragraph prints nothing — nothing to cap.
extract_now() {
  local file="$1" started=0 text="" line
  while IFS= read -r line || [ -n "$line" ]; do
    if [ -z "$line" ]; then
      if [ "$started" -eq 1 ]; then break; fi
      continue
    fi
    if [ "$started" -eq 0 ]; then
      if [[ "$line" =~ ^\*\*OPEN ]]; then
        started=1
        text="$line"$'\n'
      fi
    else
      text="${text}${line}"$'\n'
    fi
  done <"$file"
  printf '%s' "$text"
}

# The wrapped line count of the Now paragraph in FILE: folded at 80 columns,
# pinned to bytes with LC_ALL=C so the count never depends on the caller's LANG
# (a bare git-hook environment may export none at all).
wrapped_lines() {
  extract_now "$1" | LC_ALL=C fold -w 80 | wc -l
}

check_file() {
  local n
  if [ ! -f "$1" ]; then
    echo "now-paragraph: $1: no such file" >&2
    return 1
  fi
  n="$(wrapped_lines "$1")"
  if [ "$n" -gt "$CAP" ]; then
    echo "lint: START HERE's Now paragraph is $n wrapped lines at 80 columns (allowed at most 10) — rewrite it in ten wrapped lines or fewer (the Now paragraph opens **OPEN)" >&2
    return 1
  fi
}

# self-test: the two boundary fixtures, each ONE physical line. `**OPEN ` is 7
# bytes; 793 x's make 800 bytes = exactly 10 folded lines (must pass), 794 x's
# make 801 bytes = 11 folded lines (must fail). Both are a single physical line,
# so a raw newline count reads 1 for either — these fixtures reproduce CR4's
# shipped algorithm directly, not hypothetically.
self_check() {
  local pass_x fail_x
  d="$(mktemp -d)"
  trap 'rm -rf "$d"' EXIT
  printf -v pass_x '%793s' ''
  pass_x=${pass_x// /x}
  printf -v fail_x '%794s' ''
  fail_x=${fail_x// /x}
  printf '**OPEN %s\n' "$pass_x" >"$d/pass"
  printf '**OPEN %s\n' "$fail_x" >"$d/fail"

  if ! check_file "$d/pass"; then
    echo "now-paragraph: self-test: the 793-x fixture (10 folded lines) was rejected" >&2
    exit 1
  fi
  # The negative case: this check must FAIL. Its expected refusal message is
  # suppressed (this is not a gated command — its exit status is asserted on the
  # next line), so a passing self-test is silent.
  if check_file "$d/fail" 2>/dev/null; then
    echo "now-paragraph: self-test: the 794-x fixture (11 folded lines) passed; the cap is vacuous" >&2
    exit 1
  fi
}

if [ $# -gt 0 ] && [ "$1" = "--self-test" ]; then
  self_check
else
  check_file "${1:-docs/OPERATIONS.md}"
fi
