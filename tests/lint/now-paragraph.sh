#!/usr/bin/env bash
# now-paragraph.sh [--self-test | FILE] — the board-shape checker (KN17, 50a/51a).
# The board is the derived page and nothing else: a fixed header, one marked
# block, nothing after `<!-- tasks:end -->` but a trailing newline, and the
# block (markers inclusive) at most SESSION_START_CAP_BOARD (2300) bytes — the
# cap tools/session-start.sh cuts the board at, so growth goes red here before
# it is silently truncated there.
#
#   check_file FILE  asserts the shape; exits 0 iff the file is exactly
#                    header + one marked block + nothing after the end marker
#                    but a trailing newline, and the block is within the cap
#   --self-test      builds four fixtures (clean -> 0; a line after the end
#                    marker -> 1; a second paragraph before the block -> 1; a
#                    2301-byte block -> 1) and asserts each is judged right
#
# Exit codes: 0 the board is exactly header + block and within the cap; 1 it is
# not (or a fixture misbehaved); 2 a measuring tool is missing from PATH. awk,
# wc, grep and tail are coreutils, on the devShell and the pkgs.runCommand
# sandbox PATHs alike.
set -euo pipefail

CAP="${SESSION_START_CAP_BOARD:-2300}"

for tool in awk wc grep tail; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "now-paragraph: $tool not on PATH" >&2
    exit 2
  fi
done

# The fixed header, byte for byte. `H4` is the one hand-written Facts/Narrative
# line; everything else in the board is derived by `evidence tasks write-board`.
H1='# Operations board — nixos-agent-env'
H3='## START HERE'
# The backticks in H4 are markdown inline code, not command substitution.
# shellcheck disable=SC2016
H4='Facts: `evidence bundle --markdown`. Narrative: the newest `docs/board/handoff-*.md` and `docs/board/log-2026-09.md`. Below is derived by `evidence tasks write-board`; nothing here is typed.'
BEG='<!-- tasks:begin -->'
END='<!-- tasks:end -->'

check_file() {
  local file="$1" line lineno=0

  if [ ! -f "$file" ]; then
    echo "now-paragraph: $file: no such file" >&2
    return 1
  fi

  # The first five lines are the fixed header and the sixth opens the block; any
  # byte that is not one of these lines is prose outside the derived block, and
  # the first offending line is named.
  while IFS= read -r line || [ -n "$line" ]; do
    lineno=$((lineno + 1))
    case "$lineno" in
      1) [ "$line" = "$H1" ] || {
        echo "now-paragraph: $file:1: prose outside the derived block" >&2
        return 1
      } ;;
      2) [ -z "$line" ] || {
        echo "now-paragraph: $file:2: prose outside the derived block" >&2
        return 1
      } ;;
      3) [ "$line" = "$H3" ] || {
        echo "now-paragraph: $file:3: prose outside the derived block" >&2
        return 1
      } ;;
      4) [ "$line" = "$H4" ] || {
        echo "now-paragraph: $file:4: prose outside the derived block" >&2
        return 1
      } ;;
      5) [ -z "$line" ] || {
        echo "now-paragraph: $file:5: prose outside the derived block" >&2
        return 1
      } ;;
      6) [ "$line" = "$BEG" ] || {
        echo "now-paragraph: $file:6: prose outside the derived block" >&2
        return 1
      } ;;
    esac
  done <"$file"

  [ "$lineno" -ge 7 ] || {
    echo "now-paragraph: $file: the board is missing the marked block" >&2
    return 1
  }

  # One marked block: exactly one begin marker and one end marker.
  local b e
  b=$(grep -cF "$BEG" "$file" || true)
  e=$(grep -cF "$END" "$file" || true)
  [ "$b" -eq 1 ] || {
    echo "now-paragraph: $file: expected exactly one '$BEG' marker" >&2
    return 1
  }
  [ "$e" -eq 1 ] || {
    echo "now-paragraph: $file: expected exactly one '$END' marker" >&2
    return 1
  }

  # Nothing after the end marker but a trailing newline: the end marker is the
  # last line, so the first offending line is the one right after it.
  local last end_lineno
  last=$(tail -n 1 "$file")
  if [ "$last" != "$END" ]; then
    end_lineno=$(grep -nF "$END" "$file" | cut -d: -f1)
    echo "now-paragraph: $file:$((end_lineno + 1)): prose outside the derived block" >&2
    return 1
  fi

  # The block (markers inclusive) must fit the cap session-start.sh cuts at.
  local bytes
  bytes=$(tail -n +6 "$file" | wc -c)
  if [ "$bytes" -gt "$CAP" ]; then
    echo "board-shape: block is $bytes bytes, cap $CAP" >&2
    return 1
  fi
}

# Fixture builders. Each writes a complete board on stdout, newline-terminated.

clean_board() {
  printf '%s\n' "$H1"
  printf '\n'
  printf '%s\n' "$H3"
  printf '%s\n' "$H4"
  printf '\n'
  printf '%s\n' "$BEG"
  printf '%s\n' '**Queued:** none'
  printf '%s\n' "$END"
}

second_para() {
  printf '%s\n' "$H1"
  printf '\n'
  printf '%s\n' "$H3"
  printf '%s\n' "$H4"
  printf '\n'
  printf '%s\n' 'A second hand-written paragraph.'
  printf '\n'
  printf '%s\n' "$BEG"
  printf '%s\n' '**Queued:** none'
  printf '%s\n' "$END"
}

big_block() {
  # A block of exactly 2301 bytes: the begin marker line (20 + 1 newline) + one
  # 2260-byte content line + its newline + the end marker line (18 + 1 newline).
  local big
  printf -v big '%2260s' ''
  big=${big// /x}
  printf '%s\n' "$H1"
  printf '\n'
  printf '%s\n' "$H3"
  printf '%s\n' "$H4"
  printf '\n'
  printf '%s\n' "$BEG"
  printf '%s\n' "$big"
  printf '%s\n' "$END"
}

# self-test: the four discriminating fixtures. The three negative fixtures are
# asserted to FAIL; their refusal messages are suppressed (this is not a gated
# command — their exit status is asserted on the next line), so a passing
# self-test is silent.
self_check() {
  d="$(mktemp -d)"
  trap 'rm -rf "$d"' EXIT

  clean_board >"$d/clean"
  {
    clean_board
    echo 'a hand-typed line'
  } >"$d/after"
  second_para >"$d/before"
  big_block >"$d/big"

  if ! check_file "$d/clean"; then
    echo "now-paragraph: self-test: the clean fixture was rejected" >&2
    exit 1
  fi
  if check_file "$d/after" 2>/dev/null; then
    echo "now-paragraph: self-test: the line-after fixture passed; the guard is vacuous" >&2
    exit 1
  fi
  if check_file "$d/before" 2>/dev/null; then
    echo "now-paragraph: self-test: the second-paragraph fixture passed; the guard is vacuous" >&2
    exit 1
  fi
  if check_file "$d/big" 2>/dev/null; then
    echo "now-paragraph: self-test: the oversized-block fixture passed; the cap is vacuous" >&2
    exit 1
  fi
}

if [ $# -gt 0 ] && [ "$1" = "--self-test" ]; then
  self_check
else
  check_file "${1:-docs/OPERATIONS.md}"
fi
