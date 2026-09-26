#!/usr/bin/env bash
# session-start.sh [repo] -- the SessionStart hook (.claude/settings.json).
# Prints what a fresh session needs: the board's derived queue block, the
# evidence bundle, the task brief, the in-flight state, the derived operator
# model and one pointer. Never fails the session, never evaluates the flake,
# silent for factory agents and linked worktrees. Each part is budgeted
# separately (SESSION_START_CAP_BOARD/BUNDLE/BRIEF/INFLIGHT/OPERATOR) so the
# brief, the operator model and the pointer survive even when the board or
# bundle is huge; SESSION_START_CAP is the total ceiling applied after the
# parts. A non-numeric SESSION_START_CAP_<NAME> falls back to that part's
# default. All caps slice characters, hence the word "chars" in every
# truncation line.
# Plan: docs/superpowers/plans/2026-09-05-session-context.md (G6).
set -u
repo=${1:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}
cap=${SESSION_START_CAP:-8000}
ev=${SESSION_START_EVIDENCE:-evidence} # tests point this at a missing binary
[ -n "${FACTORY_RUN:-}" ] && exit 0
common=$(git -C "$repo" rev-parse --git-common-dir 2>&1) || common=.git
case $common in .git | "$repo/.git") ;; *) exit 0 ;; esac

# The reset ritual (CR1): the handoff and in-flight state live outside the
# repo under $XDG_STATE_HOME; the hook stdin carries session_id and source.
self_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
ritual="$self_dir/ritual.sh"
statedir="${XDG_STATE_HOME:-$HOME/.local/state}/nixos-agent-env/ritual"
input=""
if [ ! -t 0 ]; then
  IFS= read -r -d '' -n "${SESSION_START_STDIN_MAX:-8192}" input <&0 2>/dev/null || true
fi
field() {
  printf '%s' "$input" | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -n 1
}
src=$(field source)
sid=$(field session_id)

# renderer_python -- the interpreter that runs the TREE's tasks.py (the task
# renderer), or empty when none is found. Same resolution as tools/ritual.sh:
# RITUAL_PYTHON, else a python3 on PATH, else the interpreter the packaged
# `evidence` wrapper names. The brief is always the tree's renderer; only
# `evidence bundle` (which reads the store) stays the packaged command.
renderer_python() {
  local ev ev_real py pydir
  if [ -n "${RITUAL_PYTHON:-}" ]; then
    printf '%s' "$RITUAL_PYTHON"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  ev=$(command -v evidence 2>/dev/null) || return 1
  ev_real=$(readlink -f "$ev" 2>/dev/null) || return 1
  py=$(sed -n 's|^[[:space:]]*exec[[:space:]]\+\(/[^[:space:]]*python3[0-9.]*\)[[:space:]].*|\1|p' "$ev_real" 2>/dev/null | head -n 1)
  if [ -n "$py" ] && [ -x "$py" ]; then
    printf '%s' "$py"
    return 0
  fi
  pydir=$(sed -n 's|^export PATH="\([^":]*\)/bin:.*|\1|p' "$ev_real" 2>/dev/null | head -n 1)
  if [ -n "$pydir" ] && [ -x "$pydir/bin/python3" ]; then
    printf '%s' "$pydir/bin/python3"
    return 0
  fi
  return 1
}

cap_part() {
  # cap_part NAME TEXT DEFAULT -- print TEXT, capped at SESSION_START_CAP_<NAME>
  # when that variable is a number, else at DEFAULT. NAME is a uppercase part and
  # names both the env var and (lowercased) the truncation word. Every part's cap
  # resolves through this one helper, so a non-numeric SESSION_START_CAP_<NAME>
  # (e.g. "abc") falls back to the default instead of printing the part uncapped.
  # A cut part is followed by one "…<part> truncated at N chars
  # (SESSION_START_CAP_<NAME>)" line.
  local name=$1 text=$2 default=$3 limit part var
  var="SESSION_START_CAP_$name"
  limit=${!var:-$default}
  case $limit in
    '' | *[!0-9]*) limit=$default ;;
  esac
  part=$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')
  if [ "${#text}" -gt "$limit" ]; then
    printf '%s\n…%s truncated at %s chars (SESSION_START_CAP_%s)\n' \
      "${text:0:$limit}" "$part" "$limit" "$name"
  else
    printf '%s\n' "$text"
  fi
}

board=$(
  echo "## Board — derived queue (docs/OPERATIONS.md)"
  awk '/^<!-- tasks:begin -->/{s=1;next} /^<!-- tasks:end -->/{exit} s' "$repo/docs/OPERATIONS.md" 2>&1 || echo "unavailable: docs/OPERATIONS.md not readable"
)
if command -v "$ev" >/dev/null; then
  bundle=$("$ev" bundle --markdown 2>&1 || echo "unavailable: evidence bundle failed")
else
  bundle="unavailable: evidence not on PATH"
fi
# The brief runs the TREE's tasks.py (CR5) through the resolved interpreter, so
# the session reports the task graph of this tree, not the live generation's
# packaged copy. Never fails the session: any failure degrades to a stub.
py=$(renderer_python)
if [ -n "$py" ] && [ -f "$repo/pkgs/evidence/tasks.py" ]; then
  brief=$("$py" "$repo/pkgs/evidence/tasks.py" --root "$repo" brief 2>&1 || echo "unavailable: evidence tasks failed")
else
  brief=""
fi
# operator_model -- the derived operator model (docs/board/operator-model.md),
# printed between the in-flight part and the pointer under a literal heading,
# budgeted by SESSION_START_CAP_OPERATOR. Never fails the session: a missing or
# unreadable file degrades to one unavailable line, tested with [ -r ] rather
# than by swallowing the read error.
operator_model=$(
  if [ -r "$repo/docs/board/operator-model.md" ]; then
    cat "$repo/docs/board/operator-model.md"
  else
    echo "unavailable: docs/board/operator-model.md not readable"
  fi
)

# ritual_part -- the in-flight table and ritual status, printed between the
# brief and the pointer, budgeted by SESSION_START_CAP_INFLIGHT.
ritual_part() {
  local inflight_out handoff last_stop elapsed
  inflight_out=$(bash "$ritual" inflight "$repo" 2>/dev/null || true)
  if [ -n "$inflight_out" ]; then
    printf '## In flight\n%s\n' "$inflight_out"
  fi
  handoff="$statedir/handoff-$sid.md"
  case "$src" in
    compact | resume)
      if [ -n "$sid" ] && [ -f "$handoff" ]; then
        printf '## Handoff\n'
        cat "$handoff" 2>/dev/null || true
        printf '\n'
      fi
      ;;
  esac
  if [ -f "$statedir/last-stop" ]; then
    last_stop=$(cat "$statedir/last-stop" 2>/dev/null || true)
    if [ -n "$last_stop" ]; then
      elapsed=$(($(date +%s) - last_stop))
      if [ "$elapsed" -gt $((${RITUAL_IDLE_MIN:-60} * 60)) ]; then
        printf 'ritual: idle %s min - reset point; run the ritual and /new before new work\n' "$((elapsed / 60))"
      fi
    fi
  fi
  if [ -f "$repo/.claude/ritual-override" ]; then
    printf 'ritual: override present - remember to remove it when done\n'
  fi
  # The Stop hook's checks (dirty reviews/plans/board, a stale queue block,
  # board debt), recomputed read-only on the live tree by `ritual.sh unmet`.
  # ritual.log is the audit trail of forced stops and is never replayed:
  # nothing rotates it, so its lines outlive the state they name.
  bash "$ritual" unmet "$repo" 2>/dev/null || true
}
ritual_text=$(ritual_part 2>/dev/null || true)

out=$(
  cap_part BOARD "$board" 2300
  echo
  cap_part BUNDLE "$bundle" 2100
  echo
  cap_part BRIEF "$brief" 1400
  echo
  cap_part INFLIGHT "$ritual_text" 1000
  echo
  echo "## Operator model (docs/board/operator-model.md)"
  cap_part OPERATOR "$operator_model" 500
  echo
  echo "Where everything is: docs/runbooks/session.md"
)
if [ "${#out}" -gt "$cap" ]; then
  printf '%s\n…truncated at %s chars (SESSION_START_CAP)\n' "${out:0:$cap}" "$cap"
else
  printf '%s\n' "$out"
fi
exit 0
