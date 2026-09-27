#!/usr/bin/env bash
# tools/experiments/jaz/run-arm-c.sh -- the operator's launcher for arm C
# (docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md §6b).
# Starts gateway.py on the HOST (the one process that ever touches `claude`
# and the subscription login), then runs run_arm_c.py under bubblewrap:
# --unshare-all (no network), the fixture read-only, a scratch dir
# writable, the gateway's socket directory bound in, /nix/store read-only,
# HOME and /tmp as tmpfs, and a cleared environment. Stops the gateway on
# exit either way.
#
# Build-only per this repo's rule: this script itself never runs sudo,
# nixos-rebuild or systemctl, and it is meant to be launched by the
# operator, never by factory-dispatch/a seat/a timer (decision
# 2026-09-27-claude-subscription-for-operator-launched-work.md).
#
# Usage:
#   run-arm-c.sh --fixture DIR --spec REL --name NAME --date YYYY-MM-DD \
#       [--model M] [--effort E] [--calls-budget N] [--stop-at-utilization F] \
#       [--run-dir DIR] [--dry-run]
#   run-arm-c.sh --fixture DIR --smoke [--dry-run]
#
# --dry-run prints the bwrap argv (one token per line is avoided on
# purpose -- printf %q keeps it copy-pasteable) and exits 0 without
# starting the gateway, touching the network, or creating ANY directory
# (the run dir's path is computed, never mkdir'd, until a real launch) --
# it never mentions ~/.claude or a `claude` binary path, which is exactly
# what the launcher must never bind into the basket.
#
# 2026-09-27 Opus review fixes:
#   - bwrap applies its mount args IN ORDER, so a --tmpfs /tmp issued
#     AFTER a --bind under /tmp would silently shadow it. --tmpfs /tmp
#     (and the basket HOME tmpfs) now come BEFORE every --bind/--ro-bind
#     that could land under /tmp;
#   - the run dir defaults OUTSIDE /tmp entirely (under
#     ./.jaz-armc-runs, next to wherever the operator launches from) so
#     the ordering bug has no default-case foothold even if it ever
#     regresses;
#   - REPO is derived from this script's OWN location (three directories
#     up from tools/experiments/jaz), never a hardcoded home path;
#   - the gateway is started with --stopped-file so a stop (the usage
#     limit, a rejected status) leaves a record the operator can read
#     without grepping the JSONL log.
set -euo pipefail

usage() {
  cat <<'EOF'
usage: run-arm-c.sh --fixture DIR (--smoke | --spec REL --name NAME --date DATE)
                     [--model M] [--effort E] [--calls-budget N]
                     [--stop-at-utilization F] [--run-dir DIR] [--repo DIR]
                     [--dry-run]
EOF
}

FIXTURE=""
SPEC=""
NAME=""
DATE=""
RUN_DIR=""
MODEL="claude-fable-5-1"
EFFORT="high"
CALLS_BUDGET="40"
STOP_AT="0.90"
SMOKE=0
DRY_RUN=0
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# tools/experiments/jaz -> repo root is three levels up. Never a
# hardcoded operator home path; --repo still overrides it.
REPO="$(cd "$HERE/../../.." && pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    --fixture)
      FIXTURE="$2"
      shift 2
      ;;
    --spec)
      SPEC="$2"
      shift 2
      ;;
    --name)
      NAME="$2"
      shift 2
      ;;
    --date)
      DATE="$2"
      shift 2
      ;;
    --run-dir)
      RUN_DIR="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --effort)
      EFFORT="$2"
      shift 2
      ;;
    --calls-budget)
      CALLS_BUDGET="$2"
      shift 2
      ;;
    --stop-at-utilization)
      STOP_AT="$2"
      shift 2
      ;;
    --repo)
      REPO="$2"
      shift 2
      ;;
    --smoke)
      SMOKE=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "run-arm-c.sh: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$FIXTURE" ]; then
  echo "run-arm-c.sh: --fixture is required" >&2
  exit 2
fi
if [ "$SMOKE" -eq 0 ] && { [ -z "$SPEC" ] || [ -z "$NAME" ] || [ -z "$DATE" ]; }; then
  echo "run-arm-c.sh: --spec, --name and --date are required unless --smoke" >&2
  exit 2
fi

GATEWAY_PY="$HERE/gateway.py"
RUN_ARM_C_PY="$HERE/run_arm_c.py"

# Computed, never mkdir'd here: a --dry-run must create nothing at all.
# Outside /tmp by default (next to wherever the operator launches this
# from), so the mount-order fix above has no default-case foothold even
# if it ever regresses.
RUN_DIR="${RUN_DIR:-$PWD/.jaz-armc-runs/run-$(date +%Y%m%d-%H%M%S)-$$}"
SCRATCH="$RUN_DIR/scratch"
SOCKET_DIR="$RUN_DIR/socket"
SOCKET="$SOCKET_DIR/gateway.sock"
GATEWAY_LOG="$RUN_DIR/gateway.jsonl"
# Under $SCRATCH (not just $RUN_DIR) on purpose: $SCRATCH is bind-mounted
# into the basket too, so both the operator (host side) and the run
# itself (basket side, were it ever taught to check) can see why a run
# stopped from the same path.
STOPPED_FILE="$SCRATCH/stopped.json"
BASKET_HOME="$RUN_DIR/home"

# The runner env (jaz-lang + duckdb + git + grep, NO claude): resolved from
# the flake unless the caller already has it built and exported. --dry-run
# never builds anything (it only proves the argv's SHAPE), so it uses a
# placeholder path instead of paying for a real evaluation/build.
if [ "$DRY_RUN" -eq 1 ]; then
  JAZ_ARMC_RUNTIME="${JAZ_ARMC_RUNTIME:-/nix/store/dry-run-placeholder-jaz-armc-runtime}"
elif [ -z "${JAZ_ARMC_RUNTIME:-}" ]; then
  JAZ_ARMC_RUNTIME="$(nix build "$REPO#jaz-armc-runtime" --no-link --print-out-paths)"
fi
PYTHON_BIN="$JAZ_ARMC_RUNTIME/bin/python3"

BWRAP_ARGV=(
  bwrap
  --unshare-all
  --die-with-parent
  --new-session
  # tmpfs mounts FIRST: bwrap applies --tmpfs/--bind/--ro-bind IN THE
  # ORDER GIVEN, so a tmpfs issued after a bind under the same path would
  # silently shadow it. Every --bind/--ro-bind below is safe specifically
  # BECAUSE it comes after these two.
  --tmpfs /tmp
  --tmpfs "$BASKET_HOME"
  --ro-bind "$FIXTURE" "$FIXTURE"
  --bind "$SCRATCH" "$SCRATCH"
  --bind "$SOCKET_DIR" "$SOCKET_DIR"
  --ro-bind /nix/store /nix/store
  # run_arm_c.py and its sibling modules (confined_tools.py, claude_llm.py,
  # sessions.py, extract_draft_prompt.py) live in this checkout, not under
  # /nix/store -- bind this one directory (never the whole repo) read-only
  # so the interpreter inside the basket can read them.
  --ro-bind "$HERE" "$HERE"
  --dev /dev
  --proc /proc
  --clearenv
  --setenv HOME "$BASKET_HOME"
  --setenv PATH "$JAZ_ARMC_RUNTIME/bin"
  --
  "$PYTHON_BIN" "$RUN_ARM_C_PY"
  --fixture "$FIXTURE"
  --scratch "$SCRATCH"
  --socket "$SOCKET"
  --model "$MODEL"
  --effort "$EFFORT"
  --calls-budget "$CALLS_BUDGET"
)
if [ "$SMOKE" -eq 1 ]; then
  BWRAP_ARGV+=(--smoke)
else
  BWRAP_ARGV+=(--spec "$SPEC" --name "$NAME" --date "$DATE")
fi

if [ "$DRY_RUN" -eq 1 ]; then
  printf '%q ' "${BWRAP_ARGV[@]}"
  printf '\n'
  exit 0
fi

mkdir -p "$RUN_DIR" "$SCRATCH" "$SOCKET_DIR" "$BASKET_HOME"

GATEWAY_PID=""
# shellcheck disable=SC2329  # invoked indirectly, via `trap cleanup EXIT` below
cleanup() {
  if [ -n "$GATEWAY_PID" ] && kill -0 "$GATEWAY_PID" 2>/dev/null; then
    kill "$GATEWAY_PID" 2>/dev/null || true
    wait "$GATEWAY_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# The gateway runs on the HOST, outside the basket -- it alone resolves
# `claude` (from the operator's own PATH/login) and holds the socket the
# basket only ever sees as a bind-mounted file.
python3 "$GATEWAY_PY" --socket "$SOCKET" --log "$GATEWAY_LOG" \
  --stop-at-utilization "$STOP_AT" --stopped-file "$STOPPED_FILE" &
GATEWAY_PID=$!

for _ in $(seq 1 100); do
  [ -S "$SOCKET" ] && break
  sleep 0.1
done
if [ ! -S "$SOCKET" ]; then
  echo "run-arm-c.sh: gateway did not create $SOCKET" >&2
  exit 1
fi

set +e
"${BWRAP_ARGV[@]}"
RUNNER_RC=$?
set -e

echo "run-arm-c.sh: run dir: $RUN_DIR"
echo "run-arm-c.sh: scratch: $SCRATCH"
echo "run-arm-c.sh: gateway log: $GATEWAY_LOG"
echo "run-arm-c.sh: jaz log: $SCRATCH/jaz.log"
echo "run-arm-c.sh: queries log: $SCRATCH/queries.log"
if [ -f "$SCRATCH/draft-0.md" ]; then
  echo "run-arm-c.sh: draft: $SCRATCH/draft-0.md"
fi
if [ -f "$STOPPED_FILE" ]; then
  echo "run-arm-c.sh: STOPPED -- see $STOPPED_FILE"
fi

exit "$RUNNER_RC"
