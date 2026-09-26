#!/usr/bin/env bash
# factory-lib.sh -- shared helpers for the factory-* driver scripts.
# Sourced, never executed directly (no shebang execution path is documented).
#
# What this whole driver is: a manual precursor of the dark-factory.js N10/F8
# scheduler, running implementation tasks through the operator's dsh-openrouter
# seat (headless DeepSeek via OpenRouter) instead of Claude, so day-to-day
# task work is paid in OpenRouter tokens. See ~/factory/README.md.

# Guard against being executed instead of sourced.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  printf 'factory-lib.sh: this file is meant to be sourced, not executed\n' >&2
  exit 2
fi

: "${FACTORY_ROOT:=$HOME/factory}"
# shellcheck disable=SC2034  # used by the scripts that source this file, not by this file itself
FACTORY_BASE=$FACTORY_ROOT/base
FACTORY_WS=$FACTORY_ROOT/ws
# shellcheck disable=SC2034  # used by the scripts that source this file, not by this file itself
FACTORY_RUNS=$FACTORY_ROOT/runs
# shellcheck disable=SC2034  # used by the scripts that source this file, not by this file itself
FACTORY_BIN=${FACTORY_BIN_OVERRIDE:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)}
# The one repo whose devShell carries python3/jq -- neither is on the bare
# host PATH. Every use of either tool in this driver goes through this repo's
# flake, regardless of which repo-path a task targets.
FACTORY_TOOLBOX_REPO=${FACTORY_TOOLBOX_REPO:-/home/dalhaka/nixos-agent-env}

factory_log() {
  # Structured stderr line, prefixed with the calling script's basename.
  printf '%s: %s\n' "$(basename "$0")" "$*" >&2
}

factory_die() {
  local code=$1
  shift
  factory_log "$*"
  exit "$code"
}

factory_need_dir() {
  [ -d "$1" ] || factory_die 2 "no such directory: $1"
}

factory_need_file() {
  [ -f "$1" ] || factory_die 2 "no such file: $1"
  [ -r "$1" ] || factory_die 2 "no such file: $1"
}

# Resolve a plan path to its canonical absolute form, following symlinks in
# the file's own basename (realpath on the file, not only its directory), so a
# symlinked plan is recorded by the path it actually names, basename included.
# The caller has already passed factory_need_file, so $1 exists and is
# readable; realpath then cannot fail (and a failure would be a bug to surface).
# Usage: factory_abs_plan <plan>
factory_abs_plan() {
  realpath -- "$1"
}

# Run python3 via the toolbox repo's devShell. stdin/stdout/args pass through.
# Usage: factory_python3 <script-path> [args...]
factory_python3() {
  (cd "$FACTORY_TOOLBOX_REPO" && nix develop -c python3 "$@")
}

# Run python for the tree's Python tools: the toolbox repo's devShell python,
# unless FACTORY_PYTHON3_CMD overrides the interpreter (the nix build sandbox
# has no devShell but does have python). Every use of `tasks.py`/`claims.py`
# in this driver goes through here. Usage: factory_py <script-path> [args...]
factory_py() {
  if [ -n "${FACTORY_PYTHON3_CMD:-}" ]; then
    # shellcheck disable=SC2086  # FACTORY_PYTHON3_CMD is a command word
    (cd "$FACTORY_TOOLBOX_REPO" && $FACTORY_PYTHON3_CMD "$@")
  else
    factory_python3 "$@"
  fi
}

# Record one check observation in the evidence store (plan 2026-09-05-evidence-store, E7).
# Never fails the caller: a recording problem is logged and the check verdict stands.
# Usage: factory_record_check <name> <rev> ok|fail <duration_s> [<src>]
#   The optional <src> defaults to seat-integrate (the integrator's calls are
#   unchanged); SH4's factory_verify_checks records with seat-verify.
factory_record_check() {
  local name=$1 rev=$2 verdict=$3 dur=$4 src=${5:-seat-integrate} flag
  case $verdict in
    ok) flag=--ok ;;
    fail) flag=--fail ;;
    *)
      factory_log "evidence: bad verdict $verdict for $name@$rev"
      return 0
      ;;
  esac
  if [ -n "${FACTORY_EVIDENCE_CMD:-}" ]; then
    "$FACTORY_EVIDENCE_CMD" ${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} record-check --name "$name" --rev "$rev" "$flag" --class nix-check --src "$src" --duration "$dur" >>"${log:-/dev/null}" ||
      factory_log "evidence: could not record $name@$rev ($?)"
  else
    factory_python3 "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py" ${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} record-check --name "$name" --rev "$rev" "$flag" --class nix-check --src "$src" --duration "$dur" >>"${log:-/dev/null}" ||
      factory_log "evidence: could not record $name@$rev ($?)"
  fi
}

# Classify why a seat produced no usable result. The driver's own synthesising
# and demotion branches (synth/demoted) are deterministic and win over the
# log-tail heuristics; the log is read only for the tail patterns. Never fails:
# an unreadable log reads as empty. Usage:
#   factory_error_class <log> <status> <exit_code> <wall_s> <events> <synth> <demoted> [<verify>]
# The optional eighth argument `verify=timeout` makes the function print
# `verify-timeout` wherever it would otherwise print `none` (the done guard and
# the final fallback), and nowhere else.
factory_error_class() {
  local log=$1 status=$2 exit_code=$3 wall_s=$4 events=$5 synth=$6 demoted=$7 verify=${8:-} tail
  [ -n "${wall_s:-}" ] || wall_s=0
  [ -n "${events:-}" ] || events=0
  case $synth in
    submit)
      printf 'submit-failed\n'
      return 0
      ;;
  esac
  if [ "$exit_code" = "124" ]; then
    printf 'timeout\n'
    return 0
  fi
  if [ "$status" = "done" ]; then
    if [ "$verify" = "timeout" ]; then
      printf 'verify-timeout\n'
    else
      printf 'none\n'
    fi
    return 0
  fi
  case $synth in
    nearmiss | none)
      printf 'no-result-line\n'
      return 0
      ;;
  esac
  case $demoted in
    zero-commits | echo)
      printf 'template-echo\n'
      return 0
      ;;
    touches)
      printf 'touches-violation\n'
      return 0
      ;;
    checks-misreported)
      printf 'checks-misreported\n'
      return 0
      ;;
    checks-unverifiable)
      printf 'checks-unverifiable\n'
      return 0
      ;;
    probe-mismatch)
      printf 'probe-mismatch\n'
      return 0
      ;;
    probe-missing)
      printf 'probe-missing\n'
      return 0
      ;;
  esac
  tail=$(tail -c 4000 -- "$log" 2>/dev/null || true)
  if printf '%s' "$tail" | grep -q -- '402' && printf '%s' "$tail" | grep -q -- 'budget_exhausted'; then
    printf 'budget-402\n'
    return 0
  fi
  if printf '%s' "$tail" | grep -qE -- '\b(502|503|529)\b|upstream|provider'; then
    printf 'provider-error\n'
    return 0
  fi
  if printf '%s' "$tail" | grep -q -- 'UNKNOWN_MODEL'; then
    printf 'unknown-model\n'
    return 0
  fi
  if [ "$wall_s" -lt 10 ] && [ "$events" -lt 50 ]; then
    printf 'boot-failure\n'
    return 0
  fi
  if [ "$verify" = "timeout" ]; then
    printf 'verify-timeout\n'
  else
    printf 'none\n'
  fi
}

# Record one task result in the evidence store (plan 2026-09-06-telemetry-store-1, T2).
# Never fails the caller: stdout+stderr are appended to $log and the command's
# status is returned for the caller to note. Usage: factory_ingest_result <result>
factory_ingest_result() {
  local result=$1
  if [ -n "${FACTORY_EVIDENCE_CMD:-}" ]; then
    "$FACTORY_EVIDENCE_CMD" ${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} ingest result "$result" >>"${log:-/dev/null}" 2>&1
  else
    factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py" ${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} ingest result "$result" >>"${log:-/dev/null}" 2>&1
  fi
}

# Ingest the broker's seat usage stream into ledger/openrouter-usage (UI1), so
# SP4 reads a stream that is current after every run. Same seams and posture as
# factory_ingest_result; never fails the caller. Usage: factory_ingest_usage [path]
factory_ingest_usage() {
  local usage=${1:-/var/lib/egress-broker/seat/usage.jsonl}
  if [ -n "${FACTORY_EVIDENCE_CMD:-}" ]; then
    "$FACTORY_EVIDENCE_CMD" ${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} ingest openrouter-usage "$usage" >>"${log:-/dev/null}" 2>&1
  else
    factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py" ${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} ingest openrouter-usage "$usage" >>"${log:-/dev/null}" 2>&1
  fi
}

# The newest recorded observation for a check at a revision: prints the store
# row (JSON) and returns 0 when one exists, 1 otherwise. Never fails the
# caller on a store problem. Usage: factory_latest_check <name> <rev>
factory_latest_check() {
  local name=$1 rev=$2
  if [ -n "${FACTORY_EVIDENCE_CMD:-}" ]; then
    "$FACTORY_EVIDENCE_CMD" ${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} latest-check --name "$name" --rev "$rev" 2>>"${log:-/dev/null}"
  else
    factory_python3 "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py" ${EVIDENCE_STORE:+--store "$EVIDENCE_STORE"} latest-check --name "$name" --rev "$rev" 2>>"${log:-/dev/null}"
  fi
}

# The acceptance names of a plan section: the `**acceptance:**` line's value,
# split on commas and whitespace, one per line. The section's own line -- never
# the commit subject's `(test: …)`. Empty when there is no section or no line.
# Usage: factory_acceptance_names <plan> <KEY>
factory_acceptance_names() {
  local plan=$1 key=$2 section val
  section=$(factory_extract_task "$plan" "$key")
  val=$(printf '%s\n' "$section" | sed -nE 's/^\*\*acceptance:\*\*[[:space:]]*(.*)$/\1/p' | head -n1)
  [ -n "$val" ] || return 0
  printf '%s\n' "$val" | awk -F'[, ]+' '{ for (i = 1; i <= NF; i++) if ($i != "") print $i }'
}

# Every check name of a workspace's flake at a revision, one per line, via
# `nix eval --json … --apply builtins.attrNames`. Returns 1 and prints nothing
# when the evaluation fails (the last 200 bytes of the error are logged).
# Usage: factory_flake_checks <ws> <rev>
factory_flake_checks() {
  local ws=$1 rev=$2 out
  if ! out=$(nix eval --json "git+file://$ws?ref=$rev#checks.x86_64-linux" --apply builtins.attrNames 2>&1); then
    factory_log "nix eval checks failed: $(printf '%s' "$out" | tail -c 200)"
    return 1
  fi
  printf '%s\n' "$out" | tr -d '"[]' | tr ',' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | sed '/^$/d'
}

# The seat's token for a name in a FACTORY-CHECKS body, or `absent` when the
# name is not on the line. A `none=not-run` sentinel is read as a blanket
# `not-run` claim for every unlisted name (the seat ran nothing). Usage:
#   factory_checks_token <name> <body>
factory_checks_token() {
  local name=$1 body=$2 token blanket=
  local -a tokens
  read -r -a tokens <<<"$body" || true
  for token in "${tokens[@]}"; do
    token=${token%[;,.]}
    case "$token" in
      "$name="*)
        printf '%s\n' "${token#*=}"
        return 0
        ;;
      none=not-run) blanket=not-run ;;
    esac
  done
  if [ -n "$blanket" ]; then
    printf '%s\n' "$blanket"
  else
    printf 'absent\n'
  fi
  return 0
}

# The seat-grammar FACTORY-CHECKS line the driver derives for an unreported
# block, from the folded verification verdicts; `none=not-run` only when the
# set is empty. Usage: factory_derived_checks_line <folded-verdicts>
factory_derived_checks_line() {
  local folded=$1
  if [ -n "$folded" ]; then
    printf 'FACTORY-CHECKS %s\n' "$folded"
  else
    printf 'FACTORY-CHECKS none=not-run\n'
  fi
}

# 0 when the workspace's check at <rev> is deferred: its derivation requires
# `kvm` or is the host toplevel closure (<toplevel-drv>), AND a dry-run shows
# it still has derivations to build (a store hit is not deferred). Usage:
#   factory_check_deferred <ws> <rev> <name> <toplevel-drv>
factory_check_deferred() {
  local ws=$1 rev=$2 name=$3 toplevel_drv=$4 show
  show=$(nix derivation show "git+file://$ws?ref=$rev#checks.x86_64-linux.$name" 2>/dev/null || true)
  if printf '%s' "$show" | grep -q -- '"requiredSystemFeatures"'; then
    printf '%s' "$show" | grep -q -- 'kvm' || return 1
  elif [ -n "$toplevel_drv" ] && printf '%s' "$show" | grep -qF -- "\"$toplevel_drv\""; then
    :
  else
    return 1
  fi
  if nix build --dry-run "git+file://$ws?ref=$rev#checks.x86_64-linux.$name" 2>&1 | grep -q -- 'will be built:'; then
    return 0
  fi
  return 1
}

# Re-run the acceptance checks at the committed rev. Prints one line per name:
# `<name> <verdict> <src> [<duration_s>]` with verdict in pass|fail|not-run:absent|
# not-run:cache-miss|not-run:verify-timeout and src in recorded|run|eval|-.
# Per name, in order: a recorded row wins (recorded, nothing run); the flake
# eval failing marks every name fail; a name absent from the flake is
# not-run:absent; a deferred check is not-run:cache-miss; otherwise the build
# runs under `timeout` against the remaining budget. Returns 3 once a build
# times out (later names are not-run:verify-timeout without running).
# Usage: factory_verify_checks <ws> <rev> <budget-s> <name>…
factory_verify_checks() {
  local ws=$1 rev=$2 budget=$3 name dur verdict src row now remaining rc
  shift 3
  local start_ts
  start_ts=$(date +%s)
  local toplevel_drv flake_names flake_rc timed_out=0
  toplevel_drv=$(nix eval --raw "git+file://$ws?ref=$rev#nixosConfigurations.core.config.system.build.toplevel.drvPath" 2>/dev/null || true)
  flake_names=$(factory_flake_checks "$ws" "$rev") && flake_rc=0 || flake_rc=$?
  for name in "$@"; do
    if [ "$timed_out" -eq 1 ]; then
      printf '%s %s %s\n' "$name" "not-run:verify-timeout" "-"
      continue
    fi
    # (1) a recorded row at this rev wins.
    if row=$(factory_latest_check "$name" "$rev"); then
      if printf '%s' "$row" | grep -q -- '"ok": *true'; then
        printf '%s %s %s\n' "$name" "pass" "recorded"
      else
        printf '%s %s %s\n' "$name" "fail" "recorded"
      fi
      continue
    fi
    # (2) eval failure / absent.
    if [ "$flake_rc" -ne 0 ]; then
      printf '%s %s %s\n' "$name" "fail" "eval"
      continue
    fi
    if ! printf '%s\n' "$flake_names" | grep -qx -- "$name"; then
      printf '%s %s %s\n' "$name" "not-run:absent" "-"
      continue
    fi
    # (3) deferred.
    if factory_check_deferred "$ws" "$rev" "$name" "$toplevel_drv"; then
      printf '%s %s %s\n' "$name" "not-run:cache-miss" "-"
      continue
    fi
    # (4) build under the remaining budget.
    now=$(date +%s)
    remaining=$((budget - (now - start_ts)))
    [ "$remaining" -ge 1 ] || remaining=1
    dur=0
    if timeout -- "$remaining" nix build "git+file://$ws?ref=$rev#checks.x86_64-linux.$name" --no-link >/dev/null 2>&1; then
      dur=$(($(date +%s) - now))
      printf '%s %s %s %s\n' "$name" "pass" "run" "$dur"
      factory_record_check "$name" "$rev" ok "$dur" seat-verify
    else
      rc=$?
      if [ "$rc" -eq 124 ]; then
        printf '%s %s %s\n' "$name" "not-run:verify-timeout" "run"
        timed_out=1
      else
        dur=$(($(date +%s) - now))
        printf '%s %s %s %s\n' "$name" "fail" "run" "$dur"
        factory_record_check "$name" "$rev" fail "$dur" seat-verify
      fi
    fi
  done
  if [ "$timed_out" -eq 1 ]; then
    return 3
  fi
  return 0
}

# The branch currently checked out in a repo, falling back to its bare commit
# sha when detached (e.g. a CI checkout). Never fails.
# `git clone` never copies a source repo's *local* config (only
# global/system config would carry over automatically, and there is none
# here) -- so every fresh clone this driver makes starts with no committer
# identity, which breaks anything that has to create a real commit (a task's
# own commit if the agent does not think to set one itself, and
# unconditionally `git merge --no-ff` in factory-integrate, which needs one
# even for an otherwise-fast-forwardable merge). Copy it explicitly from
# wherever it is findable: the given source repo's local config, falling
# back to the operator's global config.
factory_set_identity() {
  local repo=$1 src=$2
  local name email
  name=$(git -C "$src" config user.name 2>/dev/null || git config --global user.name 2>/dev/null || true)
  email=$(git -C "$src" config user.email 2>/dev/null || git config --global user.email 2>/dev/null || true)
  [ -z "$name" ] || git -C "$repo" config user.name "$name"
  [ -z "$email" ] || git -C "$repo" config user.email "$email"
}

factory_current_branch() {
  local repo=$1
  local b
  b=$(git -C "$repo" symbolic-ref --short -q HEAD || true)
  if [ -z "$b" ]; then
    git -C "$repo" rev-parse HEAD
  else
    printf '%s\n' "$b"
  fi
}

# Extract a markdown section between a "## Heading" line matched as a
# *prefix* (some headings carry a parenthetical after the title, e.g.
# "## Assumptions (stated, not verified here)") and the next line starting
# "## ", or EOF. The heading line itself is not included.
# Usage: factory_extract_h2 <file> "## Heading"
factory_extract_h2() {
  local file=$1 heading=$2
  awk -v heading="$heading" '
    !found && substr($0, 1, length(heading)) == heading { found=1; next }
    found && /^## / { exit }
    found { print }
  ' "$file"
}

# Extract a "### KEY ..." task section (heading line included) up to the next
# "### " or "## " heading, or EOF. Empty output (not an error) if KEY has no
# section in the file -- callers decide whether that is fatal.
# Usage: factory_extract_task <file> <KEY>
factory_extract_task() {
  local file=$1 key=$2
  awk -v key="$key" '
    BEGIN { pat = "^### " key "([^A-Za-z0-9]|$)"; found = 0 }
    !found && $0 ~ pat { found = 1; print; next }
    found && (/^### / || /^## /) { exit }
    found { print }
  ' "$file"
}

# Parse the "(kind, size)" parenthetical from a "### KEY ..." task heading.
# Prints "KIND SIZE"; prints "any any" when the plan file is missing, KEY has
# no section, or the heading is untyped (no "(...)" ). Pure bash: the seat
# runs on the bare host PATH.
# Usage: factory_task_kind_size <plan> <KEY>
factory_task_kind_size() {
  local plan=$1 key=$2
  local section heading inner kind size
  if [ ! -f "$plan" ]; then
    printf 'any any\n'
    return 0
  fi
  section=$(factory_extract_task "$plan" "$key")
  case $section in
    *$'\n'*) heading=${section%%$'\n'*} ;;
    *) heading=$section ;;
  esac
  heading=${heading#"### $key"}
  heading=${heading#"${heading%%[![:space:]]*}"}
  case $heading in
    '('*) ;;
    *) {
      printf 'any any\n'
      return 0
    } ;;
  esac
  inner=${heading#*'('}
  inner=${inner%%')'*}
  kind=${inner%%,*}
  size=${inner#*,}
  size=${size%%,*}
  kind=${kind#"${kind%%[![:space:]]*}"}
  kind=${kind%"${kind##*[![:space:]]}"}
  size=${size#"${size%%[![:space:]]*}"}
  size=${size%"${size##*[![:space:]]}"}
  if [ -z "$kind" ] || [ -z "$size" ]; then
    printf 'any any\n'
    return 0
  fi
  printf '%s %s\n' "$kind" "$size"
}

# Look up the winning [[route]] row in the routing table for
# ROUTE/ROLE/KIND/SIZE (plus an optional CLASS, default "any"). A row carries
# the six base keys and three optional ladder keys -- `class` (the technical
# class, default "any"), `rung` (a positive integer, default 1) and `fallback`
# (a sideways model id). A ladder is the rows of one (route, role, kind, size,
# class) key ordered by rung; rung 1 is the default lookup, a higher --rung N
# climbs to the row sharing the rung-1 winner's key with rung=N (exit 4 with
# "ladder exhausted" when absent). --fallback prints the winning row's
# `fallback` and effort (exit 4, "no fallback", when the row has none). Output
# stays "MODEL EFFORT" (two fields). Returns 3 with a message on stderr when
# the file is missing, a row is malformed (missing one of the five required
# keys, a value not matching [A-Za-z0-9._:/-]+, an unknown
# route/role/kind/size/class word, a bad effort, a non-positive rung), a
# ladder is broken (a duplicate, gapped or unreachable rung, two adjacent
# rungs changing model AND effort, a fallback naming no row of its route), or
# there is no default (any/any/any) row for the requested route. Pure bash
# line walk.
# Usage: factory_route [--route R] [--rung N] [--class C] [--fallback] <role> <kind> <size> [FILE]
# The default table is ${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/
# docs/ledger/routing.toml}; an explicit FILE still wins over the env var.
factory_route() {
  local route=openrouter rung=1 cls=any want_fallback=0
  while [ $# -gt 0 ]; do
    case $1 in
      --route)
        route=$2
        shift 2
        ;;
      --rung)
        rung=$2
        shift 2
        ;;
      --class)
        cls=$2
        shift 2
        ;;
      --fallback)
        want_fallback=1
        shift
        ;;
      *) break ;;
    esac
  done
  local role=$1 kind=$2 size=$3
  local file=${4:-${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml}}
  local -a lines=() rows=()
  local line key val i n
  local row=0 started=0 have_default=0
  local cur_route cur_role cur_kind cur_size cur_class cur_area cur_rung cur_model cur_effort cur_fallback
  local rec
  local wroute wrole wkind wsize wclass warea wrung wmodel weffort wfb
  local wkey win_model win_effort win_fb out_model out_effort out_fb best=-1 spec_i found
  local cbest=-1 cmodel ceffort cspec

  [ -f "$file" ] || {
    printf 'factory_route: no routing table: %s\n' "$file" >&2
    return 3
  }
  mapfile -t lines <"$file"
  n=${#lines[@]}

  # Validate the just-finished row (if any) and append it to the row list.
  # Reads/writes factory_route's locals via dynamic scoping.
  _factory_route_finish_row() {
    local missing=0 word
    [ "$started" -eq 1 ] || return 0
    # A row without a route key defaults to openrouter; class/rung default.
    [ -n "${cur_route+x}" ] || cur_route=openrouter
    [ -n "${cur_class+x}" ] || cur_class=any
    [ -n "${cur_area+x}" ] || cur_area=any
    [ -n "${cur_rung+x}" ] || cur_rung=1
    [ -n "${cur_role+x}" ] || missing=1
    [ -n "${cur_kind+x}" ] || missing=1
    [ -n "${cur_size+x}" ] || missing=1
    [ -n "${cur_model+x}" ] || missing=1
    [ -n "${cur_effort+x}" ] || missing=1
    if [ "$missing" -eq 1 ]; then
      printf 'factory_route: %s: row %d: missing one of role/kind/size/model/effort\n' "$file" "$row" >&2
      return 3
    fi
    for word in "$cur_route" "$cur_role" "$cur_kind" "$cur_size" "$cur_model" "$cur_effort" "$cur_class" "$cur_area" ${cur_fallback:+"$cur_fallback"}; do
      case $word in
        '' | *[!A-Za-z0-9._:/-]*) ;;
        *) continue ;;
      esac
      printf 'factory_route: %s: row %d: bad value %q\n' "$file" "$row" "$word" >&2
      return 3
    done
    case $cur_route in
      openrouter | openrouter-batch | claude) ;;
      *)
        printf 'factory_route: %s: row %d: unknown route %q\n' "$file" "$row" "$cur_route" >&2
        return 3
        ;;
    esac
    case $cur_role in
      implement | review | verify | baseline | research | audit | orchestrate | plan | any) ;;
      *)
        printf 'factory_route: %s: row %d: unknown role %q\n' "$file" "$row" "$cur_role" >&2
        return 3
        ;;
    esac
    case $cur_kind in
      docs | code | any) ;;
      *)
        printf 'factory_route: %s: row %d: unknown kind %q\n' "$file" "$row" "$cur_kind" >&2
        return 3
        ;;
    esac
    case $cur_size in
      XS | S | M | L | any) ;;
      *)
        printf 'factory_route: %s: row %d: unknown size %q\n' "$file" "$row" "$cur_size" >&2
        return 3
        ;;
    esac
    case $cur_effort in
      off | low | medium | high | xhigh) ;;
      *)
        printf 'factory_route: %s: row %d: bad effort %q\n' "$file" "$row" "$cur_effort" >&2
        return 3
        ;;
    esac
    case $cur_class in
      nix-module | nix-check | bash-driver | python-evidence | js-workflow | bats-test | vm-test | docs-runbook | docs-plan | docs-board | docs-spec | docs-plan-run | any) ;;
      *)
        printf 'factory_route: %s: row %d: unknown class %q\n' "$file" "$row" "$cur_class" >&2
        return 3
        ;;
    esac
    case $cur_rung in
      '' | *[!0-9]* | 0)
        printf 'factory_route: %s: row %d: bad rung %q\n' "$file" "$row" "$cur_rung" >&2
        return 3
        ;;
      *) ;;
    esac
    rows+=("$cur_route|$cur_role|$cur_kind|$cur_size|$cur_class|$cur_area|$cur_rung|$cur_model|$cur_effort|${cur_fallback:-}")
    if [ "$cur_route" = "$route" ] && [ "$cur_role" = "any" ] && [ "$cur_kind" = "any" ] && [ "$cur_size" = "any" ] && [ "$cur_class" = "any" ] && [ "$cur_area" = "any" ]; then
      have_default=1
    fi
    return 0
  }

  # Post-walk pass: validate every ladder across the collected rows.
  _factory_route_check_ladders() {
    local j k rkey
    local rroute rrole rkind rsize rclass rarea rrung rmodel reffort rfb
    local fr frroute frmodel found
    local prev prev_model prev_effort cur cur_model cur_effort
    local -A seen=() row_at=() minrung=() maxrung=() seen_key=() terminus=()
    local -a keyorder=()
    for rec in "${rows[@]}"; do
      IFS='|' read -r rroute rrole rkind rsize rclass rarea rrung rmodel reffort rfb <<<"$rec"
      rkey="$rroute/$rrole/$rkind/$rsize/$rclass/$rarea"
      k="$rkey|$rrung"
      if [ -n "${seen[$k]:-}" ]; then
        printf 'factory_route: %s: ladder %s: rung %s twice\n' "$file" "$rkey" "$rrung" >&2
        return 3
      fi
      seen[$k]=1
      row_at[$k]="$rmodel|$reffort"
      if [ -z "${minrung[$rkey]:-}" ] || [ "$rrung" -lt "${minrung[$rkey]}" ]; then
        minrung[$rkey]=$rrung
      fi
      if [ -z "${maxrung[$rkey]:-}" ] || [ "$rrung" -gt "${maxrung[$rkey]}" ]; then
        maxrung[$rkey]=$rrung
      fi
      if [ "$rroute" = "claude" ] && [ "$rclass" != "any" ]; then
        terminus[$rkey]=1
      fi
      if [ -z "${seen_key[$rkey]:-}" ]; then
        seen_key[$rkey]=1
        keyorder+=("$rkey")
      fi
    done
    for rkey in "${keyorder[@]}"; do
      if [ -z "${terminus[$rkey]:-}" ]; then
        if [ "${minrung[$rkey]}" -gt 1 ]; then
          printf 'factory_route: %s: rung %s without rung 1 for its key\n' "$file" "${minrung[$rkey]}" >&2
          return 3
        fi
        for ((j = 2; j <= ${maxrung[$rkey]}; j++)); do
          if [ -n "${seen["$rkey|$j"]:-}" ] && [ -z "${seen["$rkey|$((j - 1))"]:-}" ]; then
            printf 'factory_route: %s: rung %s without rung %s\n' "$file" "$j" "$((j - 1))" >&2
            return 3
          fi
        done
      fi
      for ((j = ${minrung[$rkey]}; j < ${maxrung[$rkey]}; j++)); do
        prev="${row_at["$rkey|$j"]}"
        cur="${row_at["$rkey|$((j + 1))"]}"
        prev_model=${prev%%|*}
        prev_effort=${prev##*|}
        cur_model=${cur%%|*}
        cur_effort=${cur##*|}
        if [ "$prev_model" != "$cur_model" ] && [ "$prev_effort" != "$cur_effort" ]; then
          printf 'factory_route: %s: rungs %s→%s change model and effort\n' "$file" "$j" "$((j + 1))" >&2
          return 3
        fi
      done
    done
    for rec in "${rows[@]}"; do
      IFS='|' read -r rroute rrole rkind rsize rclass rarea rrung rmodel reffort rfb <<<"$rec"
      [ -n "$rfb" ] || continue
      found=0
      for fr in "${rows[@]}"; do
        IFS='|' read -r frroute _ _ _ _ _ _ frmodel _ _ <<<"$fr"
        if [ "$frroute" = "$rroute" ] && [ "$frmodel" = "$rfb" ]; then
          found=1
          break
        fi
      done
      if [ "$found" -eq 0 ]; then
        printf 'factory_route: %s: fallback %s has no row of its own\n' "$file" "$rfb" >&2
        return 3
      fi
    done
    return 0
  }

  for ((i = 0; i < n; i++)); do
    line=${lines[i]}
    line=${line#"${line%%[![:space:]]*}"}
    case $line in
      '' | '#'*) continue ;;
      '[[route]]' | '[[route]]'*)
        _factory_route_finish_row || return 3
        row=$((row + 1))
        started=1
        unset cur_route cur_role cur_kind cur_size cur_class cur_area cur_rung cur_model cur_effort cur_fallback
        continue
        ;;
      *=*)
        [ "$started" -eq 1 ] || {
          printf 'factory_route: %s: key %q outside a [[route]] block\n' "$file" "$line" >&2
          return 3
        }
        key=${line%%=*}
        key=${key%"${key##*[![:space:]]}"}
        val=${line#*=}
        val=${val#"${val%%[![:space:]]*}"}
        val=${val%"${val##*[![:space:]]}"}
        case $val in
          '"'*'"') val=${val#\"} val=${val%\"} ;;
          \'*\') val=${val#\'} val=${val%\'} ;;
        esac
        case $key in
          route) cur_route=$val ;;
          role) cur_role=$val ;;
          kind) cur_kind=$val ;;
          size) cur_size=$val ;;
          class) cur_class=$val ;;
          area) cur_area=$val ;;
          rung) cur_rung=$val ;;
          model) cur_model=$val ;;
          effort) cur_effort=$val ;;
          fallback) cur_fallback=$val ;;
          *)
            printf 'factory_route: %s: row %d: unknown key %q\n' "$file" "$row" "$key" >&2
            return 3
            ;;
        esac
        ;;
      *)
        printf 'factory_route: %s: row %d: malformed line %q\n' "$file" "$row" "$line" >&2
        return 3
        ;;
    esac
  done
  _factory_route_finish_row || return 3
  _factory_route_check_ladders || return 3
  [ "$have_default" -eq 1 ] || {
    printf 'factory_route: %s: no default (any/any/any) row\n' "$file" >&2
    return 3
  }

  # FA1 cross-route winner: a class-scoped claude row at the requested rung
  # beats the openrouter ladder and escalates (decision 28's operator
  # terminus). An explicit --route claude keeps its own meaning, so this fires
  # only for the default openrouter lookup. The winning row is printed and the
  # caller returns 4, so factory-task can consume the row directly.
  if [ "$route" != "claude" ]; then
    for rec in "${rows[@]}"; do
      IFS='|' read -r wroute wrole wkind wsize wclass warea wrung wmodel weffort wfb <<<"$rec"
      [ "$wroute" = "claude" ] || continue
      [ "$wclass" != "any" ] || continue
      [ "$wrung" = "$rung" ] || continue
      { [ "$wrole" = "$role" ] || [ "$wrole" = "any" ]; } || continue
      { [ "$wkind" = "$kind" ] || [ "$wkind" = "any" ]; } || continue
      { [ "$wsize" = "$size" ] || [ "$wsize" = "any" ]; } || continue
      [ "$wclass" = "$cls" ] || continue
      cspec=0
      [ "$wrole" = "any" ] || cspec=$((cspec + 1))
      [ "$wkind" = "any" ] || cspec=$((cspec + 1))
      [ "$wsize" = "any" ] || cspec=$((cspec + 1))
      [ "$wclass" = "any" ] || cspec=$((cspec + 1))
      [ "$warea" = "any" ] || cspec=$((cspec + 1))
      if [ "$cspec" -gt "$cbest" ]; then
        cbest=$cspec
        cmodel=$wmodel
        ceffort=$weffort
      fi
    done
    if [ "$cbest" -ge 0 ]; then
      printf '%s %s\n' "$cmodel" "$ceffort"
      return 4
    fi
  fi

  # Find the rung-1 winner (specificity over role/kind/size/class/area), then climb.
  for rec in "${rows[@]}"; do
    IFS='|' read -r wroute wrole wkind wsize wclass warea wrung wmodel weffort wfb <<<"$rec"
    [ "$wroute" = "$route" ] || continue
    [ "$wrung" = "1" ] || continue
    { [ "$wrole" = "$role" ] || [ "$wrole" = "any" ]; } || continue
    { [ "$wkind" = "$kind" ] || [ "$wkind" = "any" ]; } || continue
    { [ "$wsize" = "$size" ] || [ "$wsize" = "any" ]; } || continue
    { [ "$wclass" = "$cls" ] || [ "$wclass" = "any" ]; } || continue
    spec_i=0
    [ "$wrole" = "any" ] || spec_i=$((spec_i + 1))
    [ "$wkind" = "any" ] || spec_i=$((spec_i + 1))
    [ "$wsize" = "any" ] || spec_i=$((spec_i + 1))
    [ "$wclass" = "any" ] || spec_i=$((spec_i + 1))
    [ "$warea" = "any" ] || spec_i=$((spec_i + 1))
    if [ "$spec_i" -gt "$best" ]; then
      best=$spec_i
      win_model=$wmodel
      win_effort=$weffort
      win_fb=$wfb
      wkey="$wroute/$wrole/$wkind/$wsize/$wclass/$warea"
    fi
  done
  if [ "$rung" = "1" ]; then
    out_model=$win_model
    out_effort=$win_effort
    out_fb=$win_fb
  else
    found=0
    for rec in "${rows[@]}"; do
      IFS='|' read -r wroute wrole wkind wsize wclass warea wrung wmodel weffort wfb <<<"$rec"
      if [ "$wroute/$wrole/$wkind/$wsize/$wclass/$warea" = "$wkey" ] && [ "$wrung" = "$rung" ]; then
        out_model=$wmodel
        out_effort=$weffort
        out_fb=$wfb
        found=1
        break
      fi
    done
    if [ "$found" -eq 0 ]; then
      printf 'factory_route: ladder exhausted at rung %s for %s\n' "$rung" "$wkey" >&2
      return 4
    fi
  fi
  if [ "$want_fallback" -eq 1 ]; then
    if [ -z "$out_fb" ]; then
      printf 'factory_route: no fallback at rung %s for %s\n' "$rung" "$wkey" >&2
      return 4
    fi
    printf '%s %s\n' "$out_fb" "$out_effort"
  else
    printf '%s %s\n' "$out_model" "$out_effort"
  fi
}

# The rung a KEY implies under rule A1 (SD3). A key's chain suffix is the
# trailing one or two lowercase letters that immediately follow a digit
# (tasks.py's CHAIN_RE ^(.*\d)([a-z]{1,2})$): a key ending in a digit has no
# suffix and is its own root (rung 1); a suffix without an `r` is a fix round
# (rung 2); a suffix with an `r` is a re-plan (rung 3). P3Ar2 ends in a digit,
# so its trailing `r2` is not a suffix (rung 1); SD3rb ends in `3rb`, suffix
# `rb`, rung 3. Pure bash. Prints one of 1/2/3. Usage: factory_rung_of_key <KEY>
factory_rung_of_key() {
  local key=$1 suffix=
  case $key in
    *[0-9][a-z][a-z]) suffix=${key: -2} ;;
    *[0-9][a-z]) suffix=${key: -1} ;;
  esac
  case $suffix in
    '') printf '1\n' ;;
    *r*) printf '3\n' ;;
    *) printf '2\n' ;;
  esac
}

# Validate the routing table: probe each of the two routes this driver knows
# -- openrouter (factory_route's default) and claude -- so a malformed row or
# a missing (any/any/any) default for either route fails. Exit 0 when both
# probes resolve, else 3 (factory_route's message names the offending row).
# Usage: factory_route_check [FILE]
# The default FILE follows factory_route's default: an explicit FILE wins over
# FACTORY_ROUTING_TABLE, which wins over the FACTORY_TOOLBOX_REPO default.
factory_route_check() {
  local file=${1:-${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml}}
  factory_route any any any "$file" >/dev/null || return 3
  factory_route --route claude any any any "$file" >/dev/null || return 3
}

# Compute a spec's size label from its word count: S <= 1500 < M <= 4000 < L.
# This is the ONE definition of the size rule; both factory-plan and
# factory-plan-brief call it, so a threshold has no second home to drift from.
# Prints "S", "M" or "L". Usage: factory_plan_size <file>
factory_plan_size() {
  local words
  words=$(wc -w <"$1")
  if [ "$words" -le 1500 ]; then
    printf 'S\n'
  elif [ "$words" -le 4000 ]; then
    printf 'M\n'
  else
    printf 'L\n'
  fi
}

# Record/read a small key=value metadata file a workspace carries about its
# own creation (currently: which commit and branch it was forked from).
factory_write_meta() {
  local ws=$1 base_sha=$2 base_branch=$3
  {
    printf 'base_sha=%s\n' "$base_sha"
    printf 'base_branch=%s\n' "$base_branch"
  } >"$ws/.factory-meta"
}

# Prints the base_sha recorded for ws/<run>/<key>, or nothing if absent.
factory_task_base_sha() {
  local run=$1 key=$2
  local meta="$FACTORY_WS/$run/$key/.factory-meta"
  [ -f "$meta" ] || return 0
  # shellcheck disable=SC1090
  (
    base_sha=
    base_branch=
    . "$meta"
    printf '%s\n' "$base_sha"
  )
}

# Copy a dsh settings.yaml minus its `agent-default-model:` block, so the
# wrapper writes a fresh selection with the model this task asked for
# (field bug 2026-09-05: a symlinked settings.yaml carried the operator's
# saved Pro selection into a Flash run -> UNKNOWN_MODEL at boot).
factory_copy_settings_without_selection() {
  local src=$1 dst=$2
  local -a lines=()
  local line skipping=0 old_umask
  mapfile -t lines <"$src"
  old_umask=$(umask)
  umask 077
  : >"$dst"
  for line in "${lines[@]}"; do
    if [ "$line" = "agent-default-model:" ]; then
      skipping=1
      continue
    fi
    if [ "$skipping" -eq 1 ]; then
      case "$line" in
        '' | [[:space:]]*) continue ;;
        *) skipping=0 ;;
      esac
    fi
    printf '%s\n' "$line" >>"$dst"
  done
  chmod 600 -- "$dst"
  umask "$old_umask"
}

# Seed a fresh, isolated DSH_HOME with symlinks to whatever the shared home
# carries that dsh-openrouter itself does NOT regenerate at every launch
# (the route overlay and, once N7 lands, hooks.json) and that a headless
# session needs to behave like an already-onboarded one (skills, AGENTS.md,
# auth/profile state). Sessions are deliberately not shared, so each isolated
# home gets its own, empty at first. settings.yaml is also skipped from the
# symlink loop and instead copied without its saved `agent-default-model:`
# block, so this task's --model / OPENROUTER_MODEL actually takes effect.
factory_seed_dsh_home() {
  local dst=$1
  local src=${FACTORY_SHARED_DSH_HOME_SRC:-$HOME/.local/share/dsh-openrouter}
  # shellcheck disable=SC2174  # $dst's parent (a fixed DSH_HOME-shaped path we or the wrapper already created) always exists; -m applies to the one directory -p actually creates
  mkdir -p -m 700 -- "$dst"
  [ -d "$src" ] || return 0
  local entry name
  for entry in "$src"/*; do
    [ -e "$entry" ] || continue
    name=$(basename -- "$entry")
    case "$name" in
      sessions | openrouter-route.yml | hooks.json | settings.yaml) continue ;;
    esac
    [ -e "$dst/$name" ] || ln -s -- "$entry" "$dst/$name"
  done
  if [ -f "$src/settings.yaml" ] && [ ! -e "$dst/settings.yaml" ]; then
    factory_copy_settings_without_selection "$src/settings.yaml" "$dst/settings.yaml"
  fi
}

# The union of `touches` for KEY's chain, from `tasks.py touches` through the
# FACTORY_PYTHON3_CMD / FACTORY_TOOLBOX_REPO seams. Prints the entries on stdout
# and returns the subcommand's status; a non-zero status or empty output means
# "no contract" and the caller logs `touches: no contract for <KEY> (<reason>)`.
factory_task_touches() {
  local plan=$1 key=$2
  factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/tasks.py" touches "$plan" "$key"
}

# The technical class derived from a task's touches (SD2): reads the touches for
# KEY via factory_task_touches, then classifies each path against RULES (default
# $FACTORY_TOOLBOX_REPO/docs/ledger/task-classes.toml). A file's class is the
# class of the first rule whose glob matches it (a `case` pattern: `*` spans
# `/`, `?` one character); a task's class is the most-common file class, a tie
# going to the class whose rule appears earliest; no touches (or none matching
# any rule) is `any`. A missing rules file, section or plan tweaks nothing (an
# empty rules list or empty touches matches nothing -> `any`); a malformed rule
# is skipped with one stderr warning `factory_task_class: <file>: rule N: …`
# (the degrade-and-warn shape the routing table uses). Pure bash: a `mapfile`
# line walk over `[[rule]]`/`class = `/`glob = ` plus `case` glob matching; only
# the touches come from tasks.py.
# Usage: factory_task_class <plan> <KEY> [RULES]
factory_task_class() {
  local plan=$1 key=$2
  local file=${3:-${FACTORY_TOOLBOX_REPO:-}/docs/ledger/task-classes.toml}
  local names='nix-module nix-check bash-driver python-evidence js-workflow bats-test vm-test docs-runbook docs-plan docs-board docs-spec docs-plan-run'
  local -a lines=() classes=() globs=() touch_lines=()
  local -A counts=()
  local line lkey lval i j n
  local row=0 started=0 cur_class cur_glob
  local klass globv valid
  local touches path best_class='' best_count=0

  # Validate the just-finished [[rule]] block (if any) and, when well-formed,
  # append it to classes/globs. Reads/writes factory_task_class's locals via
  # dynamic scoping.
  _tc_finish_rule() {
    [ "$started" -eq 1 ] || return 0
    klass=${cur_class-}
    globv=${cur_glob-}
    valid=1
    [ -n "$klass" ] || {
      printf 'factory_task_class: %s: rule %d: missing class\n' "$file" "$row" >&2
      valid=0
    }
    [ -n "$globv" ] || {
      printf 'factory_task_class: %s: rule %d: missing glob\n' "$file" "$row" >&2
      valid=0
    }
    if [ -n "$klass" ]; then
      case " $names " in
        *" $klass "*) ;;
        *)
          printf 'factory_task_class: %s: rule %d: unknown class %s\n' "$file" "$row" "$klass" >&2
          valid=0
          ;;
      esac
    fi
    if [ -n "$globv" ]; then
      case "$globv" in
        '' | *[!A-Za-z0-9._/*?-]*)
          printf 'factory_task_class: %s: rule %d: glob %s is not a plain pattern\n' "$file" "$row" "$globv" >&2
          valid=0
          ;;
      esac
    fi
    if [ "$valid" -eq 1 ]; then
      classes+=("$klass")
      globs+=("$globv")
    fi
  }

  [ -f "$file" ] || {
    printf 'any\n'
    return 0
  }
  mapfile -t lines <"$file"
  n=${#lines[@]}
  for ((i = 0; i < n; i++)); do
    line=${lines[i]}
    line=${line#"${line%%[![:space:]]*}"}
    case $line in
      '' | '#'*) continue ;;
      '[[rule]]' | '[[rule]]'*)
        _tc_finish_rule
        row=$((row + 1))
        started=1
        unset cur_class cur_glob
        continue
        ;;
      *=*)
        [ "$started" -eq 1 ] || continue
        lkey=${line%%=*}
        lkey=${lkey%"${lkey##*[![:space:]]}"}
        lval=${line#*=}
        lval=${lval#"${lval%%[![:space:]]*}"}
        lval=${lval%"${lval##*[![:space:]]}"}
        case $lval in
          '"'*'"') lval=${lval#\"} lval=${lval%\"} ;;
          \'*\') lval=${lval#\'} lval=${lval%\'} ;;
        esac
        case $lkey in
          class) cur_class=$lval ;;
          glob) cur_glob=$lval ;;
        esac
        ;;
    esac
  done
  _tc_finish_rule

  touches=$(factory_task_touches "$plan" "$key" 2>/dev/null) || touches=
  mapfile -t touch_lines <<<"$touches"
  for path in "${touch_lines[@]}"; do
    [ -n "$path" ] || continue
    for j in "${!globs[@]}"; do
      # shellcheck disable=SC2254  # $glob is meant as a pattern, not a literal
      case "$path" in
        ${globs[j]})
          klass=${classes[j]}
          counts[$klass]=$((${counts[$klass]:-0} + 1))
          break
          ;;
      esac
    done
  done
  if [ "${#counts[@]}" -eq 0 ]; then
    printf 'any\n'
    return 0
  fi
  for j in "${!classes[@]}"; do
    klass=${classes[j]}
    n=${counts[$klass]:-0}
    [ "$n" -gt 0 ] || continue
    if [ -z "$best_class" ] || [ "$n" -gt "$best_count" ]; then
      best_class=$klass
      best_count=$n
    fi
  done
  printf '%s\n' "$best_class"
  return 0
}

# The section's probe contract: `tasks.py probes <plan> <KEY>` printed to stdout
# (an `env\t…` line then one tab-separated row per probe, command last). A
# non-zero subcommand status (an older toolbox without the graph, a missing
# section, an unreadable plan) logs "no contract" and returns that status.
factory_task_probes() {
  local plan=$1 key=$2 out rc=0
  out=$(factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/tasks.py" probes "$plan" "$key") || rc=$?
  if [ "$rc" -ne 0 ]; then
    factory_log "probes: no contract for $key (exit $rc)"
    return "$rc"
  fi
  printf '%s\n' "$out"
  return 0
}

# `factory_probe_compare <op> <bound> <value>` prints `pass` or `fail`. Numeric
# ops compare `<value>` as a decimal (a non-numeric value fails); `eq`/`ne`
# compare the trimmed strings; `empty`/`nonempty` test the value's presence.
factory_probe_compare() {
  local op=${1-} bound=${2-} value=${3-} verdict
  case $op in
    le | lt | ge | gt)
      if ! printf '%s' "$value" | grep -qE '^-?[0-9]+(\.[0-9]+)?$'; then
        printf 'fail\n'
        return 0
      fi
      verdict=$(awk -v b="$bound" -v v="$value" -v o="$op" 'BEGIN {
        if (o == "le") p = (v <= b);
        else if (o == "lt") p = (v < b);
        else if (o == "ge") p = (v >= b);
        else p = (v > b);
        print (p ? "pass" : "fail")
      }')
      printf '%s\n' "$verdict"
      return 0
      ;;
    eq | ne)
      value=$(printf '%s' "$value" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
      bound=$(printf '%s' "$bound" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
      if [ "$value" = "$bound" ]; then
        [ "$op" = "eq" ] && printf 'pass\n' || printf 'fail\n'
      else
        [ "$op" = "eq" ] && printf 'fail\n' || printf 'pass\n'
      fi
      return 0
      ;;
    empty)
      # empty/nonempty carry no bound: the tested value is the third argument.
      if [ -z "$value" ]; then printf 'pass\n'; else printf 'fail\n'; fi
      return 0
      ;;
    nonempty)
      if [ -n "$value" ]; then printf 'pass\n'; else printf 'fail\n'; fi
      return 0
      ;;
  esac
  printf 'fail\n'
  return 0
}

# `factory_run_probe <ws> <env-tokens> <remaining-s> <command>`: run `<command>`
# from the workspace with FACTORY_RUN unset and the section's `probe_env` tokens
# applied after, stdout to the last line, stderr to $log. Prints the last
# non-empty stdout line, trimmed, truncated to 200 bytes, control bytes folded
# to a space. Returns 124 on a timeout, else 0 (the command's exit status is not
# the verdict — the value is).
factory_run_probe() {
  local ws=$1 env_tokens=$2 remaining=$3 cmd=$4
  local raw trimmed rc=0
  local -a envs=()
  if [ -n "$env_tokens" ]; then
    read -r -a envs <<<"$env_tokens" || true
  fi
  if [ "${#envs[@]}" -gt 0 ]; then
    raw=$(cd -- "$ws" && timeout -- "$remaining" env -u FACTORY_RUN "${envs[@]}" bash -c "$cmd" 2>>"${log:-/dev/null}") || rc=$?
  else
    raw=$(cd -- "$ws" && timeout -- "$remaining" env -u FACTORY_RUN bash -c "$cmd" 2>>"${log:-/dev/null}") || rc=$?
  fi
  trimmed=$(printf '%s\n' "$raw" | awk 'NF { last=$0 } END { if (last != "") { sub(/^[[:space:]]+/, "", last); sub(/[[:space:]]+$/, "", last); print last } }')
  if [ -n "$trimmed" ]; then
    printf '%s' "$trimmed" | head -c 200 | tr '[:cntrl:]' ' '
    printf '\n'
  fi
  if [ "$rc" -eq 124 ]; then
    return 124
  fi
  return 0
}

# 0 when some entry E of $2 (trailing "/" stripped) equals $1 or prefixes it
# with a "/" boundary; 1 otherwise. A directory entry covers every file under
# it as a path prefix with the "/" boundary; never a substring, never a glob.
factory_touches_covers() {
  local path=$1 file=$2 entry
  while IFS= read -r entry; do
    entry=${entry%/}
    [ -n "$entry" ] || continue
    if [ "$path" = "$entry" ] || [ "${path#"$entry"/}" != "$path" ]; then
      return 0
    fi
  done <"$file"
  return 1
}

# 0 when `git show <spec>:docs/OPERATIONS.md` for both specs, each cut with the
# queue-block awk, are byte-equal AND both versions carry exactly one
# `<!-- tasks:begin -->` and exactly one `<!-- tasks:end -->` line; 1 otherwise
# (including when either `git show` fails).
factory_board_confined() {
  local repo=$1 spec_a=$2 spec_b=$3
  local a b a_begin a_end b_begin b_end a_cut ref_a ref_b
  ref_a=":docs/OPERATIONS.md"
  [ "$spec_a" = ":" ] || ref_a="$spec_a:docs/OPERATIONS.md"
  ref_b=":docs/OPERATIONS.md"
  [ "$spec_b" = ":" ] || ref_b="$spec_b:docs/OPERATIONS.md"
  a=$(git -C "$repo" show "$ref_a" 2>/dev/null) || return 1
  b=$(git -C "$repo" show "$ref_b" 2>/dev/null) || return 1
  a_begin=$(printf '%s\n' "$a" | grep -c '<!-- tasks:begin -->' || true)
  a_end=$(printf '%s\n' "$a" | grep -c '<!-- tasks:end -->' || true)
  b_begin=$(printf '%s\n' "$b" | grep -c '<!-- tasks:begin -->' || true)
  b_end=$(printf '%s\n' "$b" | grep -c '<!-- tasks:end -->' || true)
  [ "$a_begin" -eq 1 ] && [ "$a_end" -eq 1 ] && [ "$b_begin" -eq 1 ] && [ "$b_end" -eq 1 ] || return 1
  a_cut=$(printf '%s\n' "$a" | awk '/<!-- tasks:begin -->/{s=1} !s{print} /<!-- tasks:end -->/{s=0}')
  b_cut=$(printf '%s\n' "$b" | awk '/<!-- tasks:begin -->/{s=1} !s{print} /<!-- tasks:end -->/{s=0}')
  [ "$a_cut" = "$b_cut" ]
}

# Prints, one per line and in the changed list's order, every path of
# <changed-file> that factory_touches_covers does not cover, except docs/MAP.md
# (always exempt) and docs/OPERATIONS.md when factory_board_confined returns 0.
factory_touches_extra() {
  local repo=$1 touches_file=$2 spec_a=$3 spec_b=$4 changed_file=$5
  local path
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    if [ "$path" = "docs/MAP.md" ]; then
      continue
    fi
    if [ "$path" = "docs/OPERATIONS.md" ] && factory_board_confined "$repo" "$spec_a" "$spec_b"; then
      continue
    fi
    if ! factory_touches_covers "$path" "$touches_file"; then
      printf '%s\n' "$path"
    fi
  done <"$changed_file"
}

# 0 when some line of $2, split on whitespace and backticks, has a token equal
# to $1 after stripping one trailing `,`, `;`, `.`, `:` or `)`; 1 otherwise.
# The split is word-splitting only, never pathname expansion: `*`, `?` and `[`
# are literal characters, so a token discloses a path only when it is spelled
# exactly so -- `set -f` holds for the whole function and `local -` restores the
# caller's options on every return path.
factory_disclosed() {
  local path=$1 file=$2 line token
  local -a tokens
  [ -r "$file" ] || return 1
  # `local -` saves and restores the caller's shell options on every return path,
  # and `set -f` turns pathname expansion off for the whole function: a token
  # spelled `*`, `?` or `[` is a literal character, never a pattern.
  local -
  set -f
  while IFS= read -r line; do
    line=${line//\`/ }
    # `read -a` word-splits on IFS only; it never pathname-expands.
    read -r -a tokens <<<"$line"
    for token in "${tokens[@]}"; do
      token=${token%[;,.:)]}
      if [ "$token" = "$path" ]; then
        return 0
      fi
    done
  done <"$file"
  return 1
}

# Cap a newline-joined list read from stdin at <limit> lines, appending
# "… (N more lines)" when it is cut. Empty input pipes nothing. Usage:
#   printf '%s\n' "$list" | factory_prior_cap <limit>
factory_prior_cap() {
  local limit=$1 line n emitted=0
  local -a buff=()
  while IFS= read -r line; do
    buff+=("$line")
  done
  n=${#buff[@]}
  if [ "$n" -le "$limit" ]; then
    if [ "$n" -gt 0 ]; then
      printf '%s\n' "${buff[@]}"
    fi
    return 0
  fi
  while [ "$emitted" -lt "$limit" ]; do
    printf '%s\n' "${buff[$emitted]}"
    emitted=$((emitted + 1))
  done
  printf '… (%d more lines)\n' "$((n - limit))"
}

# Cap the whole block (stdin) at 8,000 bytes on complete lines, appending
# "… (N more lines)" when it is cut. Bytes, not characters: LC_ALL=C makes
# ${#line} a byte count, and the cut marker is charged against the cap too.
# Usage:
#   printf '%s' "$block" | factory_prior_byte_cap
factory_prior_byte_cap() {
  local -x LC_ALL=C
  local line n emitted=0 bytes=0 marker reserve=0
  local -a buff=()
  while IFS= read -r line; do
    buff+=("$line")
  done
  n=${#buff[@]}
  while [ "$emitted" -lt "$n" ]; do
    line=${buff[$emitted]}
    # Reserve room for the "… (N more lines)" marker so the whole output --
    # content lines and the marker -- stays within the 8,000-byte bound.
    reserve=0
    if [ "$emitted" -lt $((n - 1)) ]; then
      marker=$(printf '… (%d more lines)' "$((n - emitted - 1))")
      reserve=$((${#marker} + 1))
    fi
    if [ $((bytes + ${#line} + 1 + reserve)) -gt 8000 ]; then
      break
    fi
    printf '%s\n' "$line"
    bytes=$((bytes + ${#line} + 1))
    emitted=$((emitted + 1))
  done
  if [ "$emitted" -lt "$n" ]; then
    printf '… (%d more lines)\n' "$((n - emitted))"
  fi
}

# A fix round composes the prior attempt from the prior .result -- its four
# FACTORY-* lines and keyed metadata, the diffstat, the rejecting Opus review's
# front-matter facts, numbered findings and mutation-table survivors, and the
# seat review's defects. Never reads <KEY>.log, a transcript or a .dsh-home.
# Prints the block to stdout; exits 2 with a message when the prior .result is
# missing. Each list (result lines, diffstat, each review's findings, survivors)
# is capped at 60 lines and the whole block at 8,000 bytes, a cut marked
# "… (N more lines)". Usage:
#   factory_prior_block <runs-dir> <repo-path> <run> <KEY>
factory_prior_block() {
  local runs_dir=$1 repo_path=$2 run=$3 key=$4
  local result="$runs_dir/$run/$key.result"
  local opus_file='' opus_name='' seat_file="$runs_dir/$run/$key.review.md"
  local h1 f line stripped n=0 found cell
  local -a cells=()
  local res_list="" diff_list="" opus_fm="" opus_findings="" seat_findings="" mut_list=""
  local block=""

  [ -f "$result" ] && [ -r "$result" ] || {
    printf 'factory_prior_block: no prior result %s\n' "$result" >&2
    return 2
  }

  # The newest (by name) REJECTED Opus review for KEY -- an APPROVED review
  # that sorts later is skipped, the newest REJECTED wins.
  if [ -d "$repo_path/docs/reviews" ]; then
    while IFS= read -r f; do
      h1=$(grep -m1 '^# Opus gate' "$f" 2>/dev/null || true)
      case $h1 in
        *REJECTED)
          opus_file=$f
          opus_name=docs/reviews/$(basename -- "$f")
          break
          ;;
      esac
    done < <(find "$repo_path/docs/reviews" -maxdepth 1 -type f -name "*opus-review*-$key.md" -print | sort -r)
  fi

  # Result: the first four lines (the FACTORY-* block) then every keyed line.
  res_list=$(awk -F': ' '
    NR <= 4 { print; next }
    $1 == "model" || $1 == "effort" || $1 == "route" || $1 == "class" ||
    $1 == "rung" || $1 == "fallback" || $1 == "seat" || $1 == "exit_code" ||
    $1 == "wall_s" || $1 == "error_class" || $1 == "usage" { print }
  ' "$result" | factory_prior_cap 60)

  # Diffstat: the lines after the `diffstat:` label up to the next blank line.
  diff_list=$(awk '/^diffstat:$/ { f = 1; next } f && /^$/ { exit } f { print }' "$result" | factory_prior_cap 60)

  # The Opus review: front-matter facts verbatim, then numbered findings.
  if [ -n "$opus_file" ]; then
    for f in plan_defect mutants_total mutants_killed mutants_outside_named; do
      h1=$(awk -v k="$f" '
        /^---$/ { c++; next }
        c == 1 && index($0, k":") == 1 { print; exit }
      ' "$opus_file")
      if [ -n "$h1" ]; then
        opus_fm="${opus_fm:+$opus_fm$'\n'}$h1"
      fi
    done
    while IFS= read -r line; do
      # A line is a finding only when it also begins with a heading marker
      # (#, * or -) or a digit: a line that begins with a word is prose.
      case $line in
        [\#*0-9-]*) ;;
        *) continue ;;
      esac
      stripped=$(printf '%s\n' "$line" | sed -E 's/^[#*_. 0-9-]+//')
      case $stripped in
        MAJOR* | MINOR*)
          n=$((n + 1))
          opus_findings="${opus_findings:+$opus_findings$'\n'}$n. $line"
          ;;
      esac
    done <"$opus_file"
    opus_findings=$(printf '%s\n' "$opus_findings" | factory_prior_cap 60)

    # Mutation-table survivors: rows carrying `surviv` (any case) or an exact
    # `no` cell.
    while IFS= read -r line; do
      case $line in
        '|'*)
          if printf '%s' "$line" | grep -qi surviv; then
            mut_list="${mut_list:+$mut_list$'\n'}$line"
            continue
          fi
          IFS='|' read -r -a cells <<<"$line"
          found=0
          for cell in "${cells[@]}"; do
            # A cell means `no` when, after stripping leading/trailing
            # whitespace and emphasis markers (*, _ and backticks), it equals
            # `no` case-insensitively -- `| **no** |`, `| *no* |` and
            # `| \`no\` |` all count.
            # shellcheck disable=SC2016  # the backtick is a literal sed match
            cell=$(printf '%s\n' "$cell" | sed -E 's/^[[:space:]*_`]+//; s/[[:space:]*_`]+$//')
            if [ "${cell,,}" = "no" ]; then
              found=1
              break
            fi
          done
          if [ "$found" -eq 1 ]; then
            mut_list="${mut_list:+$mut_list$'\n'}$line"
          fi
          ;;
      esac
    done <"$opus_file"
    mut_list=$(printf '%s\n' "$mut_list" | factory_prior_cap 60)
  fi

  # The seat review: every line starting with a defect severity.
  if [ -f "$seat_file" ]; then
    while IFS= read -r line; do
      case $line in
        blocker\ * | major\ * | minor\ *)
          n=$((n + 1))
          seat_findings="${seat_findings:+$seat_findings$'\n'}$n. $line"
          ;;
      esac
    done <"$seat_file"
    seat_findings=$(printf '%s\n' "$seat_findings" | factory_prior_cap 60)
  fi

  # Assemble: heading, result, diffstat, each review's findings, survivors,
  # then the none-filed marker when neither review contributed a line.
  block="## Prior attempt ($run/$key)"$'\n'
  block="$block"'**Result:**'$'\n'
  [ -z "$res_list" ] || block="$block$res_list"$'\n'
  block="$block"'**Diffstat:**'$'\n'
  [ -z "$diff_list" ] || block="$block$diff_list"$'\n'
  if [ -n "$opus_file" ]; then
    block="$block**Review findings ($opus_name):**"$'\n'
    [ -z "$opus_fm" ] || block="$block$opus_fm"$'\n'
    [ -z "$opus_findings" ] || block="$block$opus_findings"$'\n'
  fi
  if [ -n "$seat_findings" ]; then
    block="$block**Review findings ($run/$key.review.md):**"$'\n'
    block="$block$seat_findings"$'\n'
  fi
  block="$block"'**Mutation-table survivors:**'$'\n'
  if [ -n "$mut_list" ]; then
    block="$block$mut_list"$'\n'
  else
    block="$block(none)"$'\n'
  fi
  if [ -z "$opus_file" ] && [ ! -f "$seat_file" ]; then
    block="$block"'**Review:** none filed'$'\n'
  fi

  printf '%s' "$block" | factory_prior_byte_cap
}
