#!/usr/bin/env bash
# seat-drive -- launch a "drive" job: resolve the orchestrate routing row,
# seed an isolated DSH_HOME from the driver's skill set, and submit a web seat
# through seat-submit's `drive` mode, printing the job id and (unless
# --no-start) the URL it reaches.
#
# usage: seat-drive [--port N] [--workspace DIR] [--dsh-home DIR] [--no-start]
#
# The routed model/effort come from factory_route --rung 1 orchestrate any any
# (OPENROUTER_MODEL / OPENROUTER_REASONING_EFFORT override them, exactly as
# factory-task honours the same two overrides). The DSH_HOME is fresh (seeded
# by factory_seed_dsh_home from FACTORY_SHARED_DSH_HOME_SRC, so it carries the
# operator's skills/AGENTS.md by symlink but NOT the saved picker selection);
# the wrapper then writes this run's explicit --model into it, never the
# operator's shared home. SEAT_DRIVE_JOBS_DIR (default /var/lib/seat/jobs)
# names the job directory the url.txt wait reads; SEAT_DRIVE_URL_TIMEOUT
# (whole seconds, default 60) is how long that wait runs (polling every 2 s)
# before it reports a missing url.txt on stderr.
set -euo pipefail

here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# shellcheck source=./factory-lib.sh
# shellcheck disable=SC1091
. "$here/factory-lib.sh"

usage() {
  cat <<'USAGE' >&2
usage: seat-drive [--port N] [--workspace DIR] [--dsh-home DIR] [--no-start]
USAGE
}

port=43210
workspace=$FACTORY_TOOLBOX_REPO
dsh_home=
no_start=0
while [ $# -gt 0 ]; do
  case $1 in
    --port)
      [ $# -ge 2 ] || factory_die 2 "--port needs a value"
      port=$2
      shift 2
      ;;
    --workspace)
      [ $# -ge 2 ] || factory_die 2 "--workspace needs a value"
      workspace=$2
      shift 2
      ;;
    --dsh-home)
      [ $# -ge 2 ] || factory_die 2 "--dsh-home needs a value"
      dsh_home=$2
      shift 2
      ;;
    --no-start)
      no_start=1
      shift
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

# A web port is required (a browser must reach the seat): an integer strictly
# inside the registered range, matching seat-submit drive's own rule.
case $port in
  '' | *[!0-9]*)
    factory_die 2 "bad --port $port (an integer 1024-65535)"
    ;;
esac
if [ "$port" -lt 1024 ] || [ "$port" -gt 65535 ]; then
  factory_die 2 "bad --port $port (an integer 1024-65535)"
fi
factory_need_dir "$workspace"

# Resolve the model/effort from the orchestrate row (rung 1). A broken
# routing table dies 3 with factory_route's own message already on stderr.
if ! route_line=$(factory_route --rung 1 orchestrate any any); then
  factory_die 3 "no orchestratable route (the routing table is unusable)"
fi
route_model=${route_line%% *}
route_effort=${route_line##* }

# OPENROUTER_MODEL / OPENROUTER_REASONING_EFFORT override the routed values,
# exactly as factory-task honours them (each is an "explicit" override).
model=$route_model
effort=$route_effort
if [ -n "${OPENROUTER_MODEL:-}" ]; then
  model=$OPENROUTER_MODEL
  printf 'seat-drive: explicit model (override)\n' >&2
fi
if [ -n "${OPENROUTER_REASONING_EFFORT:-}" ]; then
  effort=$OPENROUTER_REASONING_EFFORT
  printf 'seat-drive: explicit effort (override)\n' >&2
fi

printf 'seat-drive: orchestrate/any/any rung 1 → %s %s\n' "$model" "$effort"

# Seed a fresh, isolated DSH_HOME (unless the caller named one): the shared
# home's catalog by symlink, settings.yaml without the saved selection -- never
# the operator's shared home itself (Assumption 14 / addendum rule 1).
if [ -z "$dsh_home" ]; then
  stamp=$(date -u +%Y%m%d-%H%M%S)
  dsh_home="$FACTORY_ROOT/drive/$stamp.dsh-home"
  factory_seed_dsh_home "$dsh_home"
  printf 'seat-drive: DSH_HOME %s\n' "$dsh_home"
fi

# seat-submit is a flake package, not on the host PATH (Assumption 8); resolve
# it by name from PATH (or SEAT_SUBMIT), else through `nix run` of the flake.
if [ -n "${SEAT_SUBMIT:-}" ]; then
  seat_cmd=("$SEAT_SUBMIT")
elif command -v seat-submit >/dev/null 2>&1; then
  seat_cmd=(seat-submit)
else
  seat_cmd=(nix run "$FACTORY_TOOLBOX_REPO#seat-submit" --)
fi

submit_args=(
  drive
  --workspace "$workspace"
  --dsh-home "$dsh_home"
  --model "$model"
  --effort "$effort"
  --port "$port"
)
[ "$no_start" -eq 0 ] || submit_args+=(--no-start)

job_id=$("${seat_cmd[@]}" "${submit_args[@]}" | head -n1)
printf '%s\n' "$job_id"

# Unless --no-start, wait up to SEAT_DRIVE_URL_TIMEOUT seconds (poll every
# 2 s) for the unit's url.txt under SEAT_DRIVE_JOBS_DIR and print its line; a
# timeout is only a message on stderr, the exit stays the id (exit 0). The URL
# line is the last thing on stdout.
#
# SD12: a url.txt beside a non-zero exit_code.txt is a DEAD job, not a
# success. seat-run writes url.txt as soon as the unit binds (before dsh
# finishes booting), so a job that crashes on boot still leaves its address on
# disk; that address must not be printed (the browser would race a corpse).
# exit_code.txt only exists once a run has actually ended.
if [ "$no_start" -eq 0 ]; then
  jobs_dir=${SEAT_DRIVE_JOBS_DIR:-/var/lib/seat/jobs}
  url_timeout=${SEAT_DRIVE_URL_TIMEOUT:-60}
  url_file="$jobs_dir/$job_id/url.txt"
  exit_file="$jobs_dir/$job_id/exit_code.txt"
  found=0
  elapsed=0
  while [ "$elapsed" -lt "$url_timeout" ]; do
    if [ -f "$url_file" ]; then
      found=1
      break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  if [ "$found" -eq 0 ]; then
    printf 'seat-drive: no url.txt after %s s — journalctl -u seat@%s\n' \
      "$url_timeout" "$job_id" >&2
  else
    if [ -f "$exit_file" ]; then
      exit_code=$(cat -- "$exit_file")
      if [ "$exit_code" != "0" ]; then
        printf 'seat-drive: job %s failed (exit %s) — journalctl -u seat@%s\n' \
          "$job_id" "$exit_code" "$job_id" >&2
        exit 1
      fi
    fi
    cat -- "$url_file"
  fi
fi
