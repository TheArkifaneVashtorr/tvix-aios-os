#!/usr/bin/env bash
# ritual.sh <stop|precompact|inflight|unmet> [repo] -- the context-reset ritual
# hooks (.claude/settings.json): Stop blocks a turn that would leave durable
# state uncommitted or the board stale; PreCompact writes a derived handoff;
# inflight lists live seat runs; unmet prints Stop's checks read-only (what
# session-start replays, recomputed on the live tree). Never calls nix, never commits, never writes inside the
# repo (state lives under $XDG_STATE_HOME/nixos-agent-env/ritual), silent for
# factory agents (`FACTORY_RUN`), single-pass seats (`SEAT_MODE` other than
# `drive`) and linked worktrees. stdin is flat hook JSON, read with bash
# pattern matching; malformed input degrades to allow with a warning.
# Plan: docs/superpowers/specs/2026-09-05-context-reset-ritual-design.md (CR1).
set -u

cmd=${1:-}
repo=${2:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}

[ -n "${FACTORY_RUN:-}" ] && exit 0
case ${SEAT_MODE:-drive} in drive) ;; *) exit 0 ;; esac
[ -n "$cmd" ] || {
  echo "usage: ritual.sh <stop|precompact|inflight|unmet> [repo]" >&2
  exit 2
}

statedir="${XDG_STATE_HOME:-$HOME/.local/state}/nixos-agent-env/ritual"
runs_dir="${FACTORY_ROOT:-$HOME/factory}/runs"

# Repo-scoped subcommands are silent in a linked worktree (same test as
# session-start.sh); inflight reads the global runs dir, not the tree.
case $cmd in
  stop | precompact | unmet)
    common=$(git -C "$repo" rev-parse --git-common-dir 2>&1) || common=.git
    case $common in .git | "$repo/.git") ;; *) exit 0 ;; esac
    ;;
esac

# stdin carries the Stop/PreCompact JSON and is read only when it is not a
# terminal (a hook pipes the JSON in; a human running the script by hand has a
# terminal, and `cat` would block), and only up to a size cap. The bash builtin
# `read` (not `$(cat)`) also returns immediately when stdin is closed rather
# than deadlocking on fd 0. `inflight` reads no stdin at all, so the
# `$(bash ritual.sh inflight)` command substitution in session-start.sh cannot
# block on a terminal or a closed fd 0.
input=""
case $cmd in
  stop | precompact)
    if [ ! -t 0 ]; then
      IFS= read -r -d '' -n "${RITUAL_STDIN_MAX:-8192}" input <&0 2>/dev/null || true
    fi
    ;;
esac

# get_field JSON FIELD -- first string value of FIELD, or empty.
get_field() {
  printf '%s' "$1" | sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -n 1
}

# get_flag JSON FIELD -- "true" when FIELD is the JSON boolean true, else empty.
# Stop/PreCompact carry booleans (stop_hook_active) without quotes, which
# get_field's string-value regex cannot see.
get_flag() {
  printf '%s' "$1" | sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*true.*/true/p" | head -n 1
}

# renderer_python -- print the interpreter that runs the TREE's tasks.py (the
# renderer), or empty when none is found. Resolution order (the contract CR5):
# RITUAL_PYTHON when set, else a python3 on PATH, else the interpreter the
# packaged `evidence` wrapper would run (an absolute python3 in its `exec …`
# line, else the python3 directory its `PATH=` export prepends). The wrapper is
# consulted for an interpreter only — a hook never calls a host-packaged copy of
# tree code; `evidence bundle` is the one thing that stays packaged.
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

# join_lines TEXT -- newlines to single spaces, trimmed.
join_lines() {
  printf '%s' "$1" | tr '\n' ' ' | sed 's/  */ /g; s/^ //; s/ $//'
}

stamp_last_stop() {
  mkdir -p "$statedir"
  date +%s >"$statedir/last-stop"
}

# reap_blocks -- drop per-session block counters older than a week so state does
# not grow one file per session forever.
reap_blocks() {
  find "$statedir" -maxdepth 1 -name '*.blocks' -mtime +7 -delete 2>/dev/null || true
}

# board_debt -- commits since the last commit touching docs/OPERATIONS.md or a
# board log that touch docs/reviews/ or any non-docs/ path.
#
# The baseline is board-or-log because the ritual's step 7 commits them
# together and this block's own text asks for both. Counting the board file
# alone left turns with no clean exit: landings whose task keys live in another
# repo move the derived queue not at all, `write-board` is then a no-op, and the
# lint permits no hand prose in docs/OPERATIONS.md -- so nothing the
# orchestrator could legitimately write would reset the counter (observed
# 2026-09-21, blocking twice in one session at a debt of 15 and 17). Staleness
# of the derived block is a separate check in collect_unmet and still blocks on
# its own; this one is the nag for the narrative half.
board_debt() {
  local last_board reviews nondocs debt
  last_board=$(git -C "$repo" log -1 --format=%H -- docs/OPERATIONS.md 'docs/board/log-*.md' 2>/dev/null) || true
  [ -n "$last_board" ] || {
    echo 0
    return
  }
  reviews=$(git -C "$repo" log --format=%H "$last_board"..HEAD -- docs/reviews 2>/dev/null || true)
  nondocs=$(git -C "$repo" log --format=%H "$last_board"..HEAD -- ':(exclude)docs/' 2>/dev/null || true)
  debt=$({
    printf '%s\n' "$reviews"
    printf '%s\n' "$nondocs"
  } |
    sed '/^$/d' | sort -u | wc -l | tr -d ' ')
  echo "${debt:-0}"
}

# collect_unmet -- one line per unsatisfied Stop check, in order.
collect_unmet() {
  local reviews dirty debt rc py
  reviews=$(git -C "$repo" -c core.quotePath=false status --short -- docs/reviews | cut -c4-)
  if [ -n "$reviews" ]; then
    printf "ritual: commit the review file(s) %s\n" "$(join_lines "$reviews")"
  fi
  dirty=$(git -C "$repo" -c core.quotePath=false status --short --untracked-files=all -- \
    docs/superpowers/plans docs/OPERATIONS.md docs/board docs/ledger | cut -c4-)
  if [ -n "$dirty" ]; then
    printf "ritual: commit or revert %s; uncommitted plan sections are invisible to the seat's clone of main\n" \
      "$(join_lines "$dirty")"
  fi
  # The board check runs the TREE's tasks.py — never the packaged `evidence`
  # copy, whose bundled tasks.py is from the live generation and can disagree
  # with this tree (CR5). Exit 1 means the queue block drifted (documented); any
  # other non-zero is a missing or crashing renderer; no interpreter at all also
  # degrades to allow (spec §4) rather than blocking on the hook's own tooling.
  py=$(renderer_python)
  if [ -z "$py" ]; then
    printf "ritual: no python3 for the tree's renderer - allowing\n" >&2
  elif [ ! -f "$repo/pkgs/evidence/tasks.py" ]; then
    printf "ritual: no tree renderer at pkgs/evidence/tasks.py - allowing\n" >&2
  else
    "$py" "$repo/pkgs/evidence/tasks.py" --root "$repo" check --board docs/OPERATIONS.md >/dev/null 2>&1
    rc=$?
    if [ "$rc" -eq 1 ]; then
      printf "ritual: the board's queue block is stale - evidence tasks --root . write-board, then commit\n"
    elif [ "$rc" -ne 0 ]; then
      printf 'ritual: the tree renderer failed (exit %s) - allowing the board check\n' "$rc" >&2
    fi
  fi
  debt=$(board_debt)
  if [ "$debt" -ge "${RITUAL_BOARD_DEBT:-6}" ]; then
    printf "ritual: %s landings/gates since the board was last written - rewrite Now (evidence tasks --root . write-board) and append the turn's entry to docs/board/log-<month>.md; committing either clears this\n" "$debt"
  fi
}

do_stop() {
  local sid blocks max unmet reason active
  reap_blocks
  sid=$(get_field "$input" session_id)
  if [ -z "$sid" ]; then
    printf 'ritual: malformed Stop input (no session_id) - allowing\n' >&2
    exit 0
  fi
  # Claude Code re-fires the Stop hook after a block with stop_hook_active:true;
  # allow then, without writing a block, so a block is asked once per turn end
  # and the session never loops (CR5).
  active=$(get_flag "$input" stop_hook_active)
  if [ "$active" = "true" ]; then
    printf 'ritual: continuing after a block - allowing\n' >&2
    exit 0
  fi
  if [ -f "$repo/.claude/ritual-override" ]; then
    printf 'ritual: override present - allowing (%s)\n' \
      "$(stat -c '%U %y' "$repo/.claude/ritual-override" 2>/dev/null)" >&2
    stamp_last_stop
    exit 0
  fi
  unmet=$(collect_unmet)
  if [ -z "$unmet" ]; then
    rm -f "$statedir/$sid.blocks"
    stamp_last_stop
    exit 0
  fi
  mkdir -p "$statedir"
  blocks=$(cat "$statedir/$sid.blocks" 2>/dev/null || echo 0)
  max=${RITUAL_MAX_BLOCKS:-2}
  if [ "$blocks" -ge "$max" ]; then
    {
      printf 'ritual: allowed after %s blocks - %s\n' "$max" "$(join_lines "$unmet")"
    } >>"$statedir/ritual.log"
    stamp_last_stop
    exit 0
  fi
  blocks=$((blocks + 1))
  printf '%s\n' "$blocks" >"$statedir/$sid.blocks"
  reason=$(printf '%s\n' "$unmet" | head -n 1)
  # The reason may carry git-quoted paths (a space, a non-ASCII byte, a quote,
  # a backslash); escape the two JSON-significant bytes so the block stays valid
  # JSON that the hook host can parse rather than dropping as a non-blocking error.
  reason=$(printf '%s' "$reason" | sed 's/\\/\\\\/g; s/"/\\"/g')
  printf '{"decision":"block","reason":"%s"}\n' "$reason"
  exit 0
}

# stale_label SECONDS -- human form of a duration: 3600 -> 1h, 60 -> 1m, else Ns.
stale_label() {
  local s=$1
  if [ "$((s % 3600))" -eq 0 ]; then
    printf '%sh\n' "$((s / 3600))"
  elif [ "$((s % 60))" -eq 0 ]; then
    printf '%sm\n' "$((s / 60))"
  else
    printf '%ss\n' "$s"
  fi
}

# process_epoch PID -- the process's start time as epoch seconds, from
# `ps -o lstart=` and `date -d`, or nothing when ps/date cannot tell. The
# recycled-pid guard must not fire when it cannot tell, so it degrades to
# trusting kill -0 rather than to a false "alive" denial.
process_epoch() {
  local pid=$1 lstart
  command -v ps >/dev/null 2>&1 || return 1
  lstart=$(ps -o lstart= -p "$pid" 2>/dev/null | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
  [ -n "$lstart" ] || return 1
  date -d "$lstart" +%s 2>/dev/null || return 1
}

# pid_recycled PID FILE -- true (0) when the process at PID started AFTER FILE
# was written (the kernel recycled the pid), so "alive" must be denied. False
# otherwise, including when the comparison cannot be made.
pid_recycled() {
  local pid=$1 file=$2 ps_epoch file_epoch
  [ -f "$file" ] || return 1
  ps_epoch=$(process_epoch "$pid") || return 1
  file_epoch=$(stat -c %Y "$file" 2>/dev/null) || return 1
  [ "$ps_epoch" -gt "$file_epoch" ]
}

# inflight_stdout -- one line per live <KEY>.log or <KEY>.review.log (no
# <KEY>.result, not stale). Each log is judged by its OWN pid -- <KEY>.pid for
# <KEY>.log, <KEY>.gate for <KEY>.review.log -- falling back to the run-level
# pid in run.meta only for a log with no pid file. A fresh log (younger than
# stale-after) is live by rule and never printed DEAD: a dead run-level pid
# only means the wave finished, not that this key's own seat died. A recycled
# pid (the process younger than its pid file) is denied "alive". A finished
# gate (its <KEY>.review.md exists) reads "gate done". A relaunch hint,
# reproducing the original argv including --then, appears only for a wave whose
# own pid is dead, when no per-key pid file holds a live pid, and lists only
# the groups whose keys have no done .result. Logs older than stale-after with
# a dead or missing pid are never listed, only counted in one summary line so
# the brief's budget goes to the runs actually in flight, not dead corpses.
inflight_stdout() {
  local log result rundir run key basekey now age mt pid then_text repo_meta plan_meta status relaunch line g
  local meta live stale_after stale_count stale_pid_count wave_pid
  local pfile ppid pfile_mt pidfile gate_done live_seat group_done k gline
  local -a group_parts=()
  local -a missing_groups=()
  local -A hinted_run
  stale_after=${RITUAL_STALE_AFTER:-7200}
  now=$(date +%s)
  stale_count=0
  stale_pid_count=0

  # Reap stranded <KEY>.pid and <KEY>.gate files whose pid is dead and whose
  # mtime is older than stale-after (SIGKILL / a reboot leaves them; their dead
  # pid is what marks them stale). Counted here, never listed, so the brief's
  # budget stays with the runs actually in flight.
  for pfile in "$runs_dir"/*/*.pid "$runs_dir"/*/*.gate; do
    [ -f "$pfile" ] || continue
    ppid=$(cat "$pfile" 2>/dev/null) || continue
    [ -n "$ppid" ] || continue
    if ! kill -0 "$ppid" 2>/dev/null; then
      pfile_mt=$((now - $(stat -c %Y "$pfile")))
      if [ "$pfile_mt" -gt "$stale_after" ]; then
        rm -f -- "$pfile"
        stale_pid_count=$((stale_pid_count + 1))
      fi
    fi
  done

  live=""
  for log in "$runs_dir"/*/*.log; do
    [ -f "$log" ] || continue
    result=${log%.log}.result
    [ -e "$result" ] && continue
    key=$(basename "$log" .log)
    rundir=$(dirname "$log")
    run=$(basename "$rundir")
    meta="$rundir/run.meta"
    mt=$((now - $(stat -c %Y "$log")))
    age=$((mt / 60))
    relaunch=""
    then_text=""
    pid=""
    pidfile=""
    gate_done=0
    wave_pid=""
    repo_meta=""
    group_parts=()
    if [ -f "$meta" ]; then
      wave_pid=$(sed -n 's/^pid:[[:space:]]*//p' "$meta" | head -n 1)
      then_text=$(sed -n 's/^then:[[:space:]]*//p' "$meta" | head -n 1)
      repo_meta=$(sed -n 's/^repo:[[:space:]]*//p' "$meta" | head -n 1)
      plan_meta=$(sed -n 's/^plan:[[:space:]]*//p' "$meta" | head -n 1)
      while IFS= read -r gline; do
        # Each group: line is %q-quoted by factory-wave; read it back eval-free
        # (xargs shell-parses, so a quote and a backslash survive verbatim).
        g=$(printf '%s\n' "$gline" | xargs printf '%s' 2>/dev/null) || g=$gline
        group_parts+=("$g")
      done < <(sed -n 's/^group:[[:space:]]*//p' "$meta")
    fi
    # Each log's own pid: <KEY>.pid for <KEY>.log, <KEY>.gate for
    # <KEY>.review.log (the gate marker holds the reviewer's pid). A finished
    # gate (its <KEY>.review.md exists) is already over.
    case "$key" in
      *.review)
        basekey=${key%.review}
        if [ -f "$rundir/$basekey.review.md" ]; then
          gate_done=1
        elif [ -f "$rundir/$basekey.gate" ]; then
          pid=$(cat "$rundir/$basekey.gate")
          pidfile=$rundir/$basekey.gate
        fi
        ;;
      *)
        if [ -f "$rundir/$key.pid" ]; then
          pid=$(cat "$rundir/$key.pid")
          pidfile=$rundir/$key.pid
        fi
        ;;
    esac
    # Fall back to the run-level pid only when there is no pid file and the
    # gate is not already over.
    if [ "$gate_done" -eq 0 ] && [ -z "$pid" ]; then
      pid=$wave_pid
      pidfile=""
    fi
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && ! pid_recycled "$pid" "$pidfile"; then
      case "$key" in
        *.review) status="running" ;;
        *) status="pid $pid alive" ;;
      esac
    elif [ "$mt" -gt "$stale_after" ]; then
      # The stale cut is checked BEFORE `gate done`: an old log sits below it
      # whether or not its gate finished, so a finished gate is never listed
      # forever (CR3r re-review MAJOR-1).
      stale_count=$((stale_count + 1))
      continue
    elif [ "$gate_done" -eq 1 ]; then
      status="gate done"
    else
      status="running"
    fi
    # A relaunch hint only for a wave whose own pid is dead and whose run holds
    # no live per-key seat; it reproduces the original argv (groups %q-quoted,
    # --then appended) but names only the groups whose keys have no done result.
    relaunch=""
    if [ -n "$wave_pid" ] && ! kill -0 "$wave_pid" 2>/dev/null; then
      live_seat=0
      for pfile in "$rundir"/*.pid "$rundir"/*.gate; do
        [ -f "$pfile" ] || continue
        ppid=$(cat "$pfile" 2>/dev/null) || continue
        if [ -n "$ppid" ] && kill -0 "$ppid" 2>/dev/null; then
          live_seat=1
          break
        fi
      done
      if [ "$live_seat" -eq 0 ]; then
        missing_groups=()
        for g in "${group_parts[@]}"; do
          group_done=0
          for k in $g; do
            if [ -f "$rundir/$k.result" ] && grep -q '^FACTORY-RESULT[[:space:]]*status=done' "$rundir/$k.result"; then
              group_done=1
              break
            fi
            # FA35: a key is also excused when its run's own repo: carries a
            # reachable `integrate $k into ` commit (the factory-integrate
            # merge, later amended or not) even when its .result is absent or
            # status=partial -- the merge is the authoritative landed signal
            # and the hint must never re-run it. The grep is anchored on the
            # literal key followed by a single space and `into `, so a landed
            # key that is a prefix of another's name (FA3 vs FA32, FA1 vs
            # FA10) never reads as landed. Best-effort: a missing or non-git
            # repo: degrades to "not landed", never a crash, and git's stderr
            # is discarded.
            if [ -n "$repo_meta" ] && [ -n "$(git -C "$repo_meta" log -1 --grep="^integrate $k into " --format=%H -- 2>/dev/null)" ]; then
              group_done=1
              break
            fi
          done
          [ "$group_done" -eq 0 ] && missing_groups+=("$g")
        done
        if [ "${#missing_groups[@]}" -gt 0 ]; then
          # The full hint prints at most once per run: the first missing group
          # of a dead run carries it, later groups of the same run print
          # "relaunch: as above". Since P11 factory-wave requires FACTORY_PLAN,
          # the hint must name the plan (read from the plan: line) so running it
          # verbatim is a live launch, and every spliced field (plan, repo,
          # groups, --then) is %q-quoted. A run.meta older than P11 has no
          # plan: line, so its hint is a bash comment (# ...) naming the plan as
          # unknown: pasted verbatim it evaluates to no launch, not a dead argv.
          if [ -n "${hinted_run[$rundir]:-}" ]; then
            relaunch="relaunch: as above"
          else
            hinted_run[$rundir]=1
            if [ -n "$plan_meta" ]; then
              # The hint names the same run and the same plan -- exactly the
              # case factory-wave's reuse rule (DF7c) admits: a wave whose
              # run.meta pid no longer names a live factory-wave is reused,
              # never refused.
              relaunch="relaunch: FACTORY_PLAN=$(printf %q "$plan_meta") factory-wave $run"
            else
              relaunch="relaunch: # plan unknown — set FACTORY_PLAN=<plan.md> then: factory-wave $run"
            fi
            [ -n "$repo_meta" ] && relaunch="$relaunch $(printf %q "$repo_meta")"
            for g in "${missing_groups[@]}"; do
              relaunch="$relaunch $(printf %q "$g")"
            done
            [ -n "$then_text" ] && relaunch="$relaunch --then $(printf %q "$then_text")"
          fi
        fi
      fi
    fi
    line="$run $key - $status - log age ${age}m"
    [ -n "$then_text" ] && line="$line - then: $then_text"
    [ -n "$relaunch" ] && line="$line - $relaunch"
    live="${live}${line}"$'\n'
  done
  if [ -n "$live" ]; then
    printf '%s' "$live" | sort
  fi
  if [ "$stale_count" -gt 0 ]; then
    printf '… and %s stale logs older than %s\n' "$stale_count" "$(stale_label "$stale_after")"
  fi
  if [ "$stale_pid_count" -gt 0 ]; then
    printf '… and %s stale pid files\n' "$stale_pid_count"
  fi
}

do_precompact() {
  local sid trigger handoff unmet dirty head_line board_log newest_log_line
  reap_blocks
  sid=$(get_field "$input" session_id)
  if [ -z "$sid" ]; then
    printf 'ritual: malformed PreCompact input (no session_id) - allowing\n' >&2
    exit 0
  fi
  trigger=$(get_field "$input" trigger)
  mkdir -p "$statedir"
  handoff="$statedir/handoff-$sid.md"
  unmet=$(collect_unmet)
  dirty=$(git -C "$repo" status --short -- \
    docs/reviews docs/superpowers/plans docs/OPERATIONS.md docs/board docs/ledger 2>/dev/null || true)
  head_line=$(git -C "$repo" log -1 --format='%h %s' 2>/dev/null || true)
  # The chronology carrier §3.2 names: the first line of the newest board-log
  # entry (newest-first), whatever month's log file is the latest.
  board_log=""
  for f in "$repo"/docs/board/log-*.md; do
    [ -f "$f" ] && board_log="$f"
  done
  newest_log_line=""
  if [ -n "$board_log" ]; then
    newest_log_line=$(awk '!/^#/ && NF { print; exit }' "$board_log" 2>/dev/null || true)
  fi
  {
    printf '# Handoff %s\n' "$(date '+%F %T')"
    printf 'trigger: %s\n' "$trigger"
    printf 'HEAD: %s\n' "$head_line"
    printf '## dirty (what the ritual did not finish)\n%s\n' "$dirty"
    printf '## in flight\n'
    inflight_stdout
    printf '## newest board log\n%s\n' "$newest_log_line"
    printf '## unmet checks\n%s\n' "$unmet"
  } >"$handoff"
  exit 0
}

case $cmd in
  stop) do_stop ;;
  precompact) do_precompact ;;
  inflight) inflight_stdout ;;
  unmet) collect_unmet ;;
  *)
    echo "usage: ritual.sh <stop|precompact|inflight|unmet> [repo]" >&2
    exit 2
    ;;
esac
