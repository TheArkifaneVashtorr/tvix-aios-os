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
# Usage: factory_record_check <name> <rev> ok|fail <duration_s>
factory_record_check() {
  local name=$1 rev=$2 verdict=$3 dur=$4 flag
  case $verdict in
    ok) flag=--ok ;;
    fail) flag=--fail ;;
    *)
      factory_log "evidence: bad verdict $verdict for $name@$rev"
      return 0
      ;;
  esac
  local store=${EVIDENCE_STORE:-/var/lib/evidence}
  if [ -n "${FACTORY_EVIDENCE_CMD:-}" ]; then
    "$FACTORY_EVIDENCE_CMD" --store "$store" record-check --name "$name" --rev "$rev" "$flag" --class nix-check --src seat-integrate --duration "$dur" >>"${log:-/dev/null}" ||
      factory_log "evidence: could not record $name@$rev ($?)"
  else
    factory_python3 "$FACTORY_TOOLBOX_REPO/pkgs/evidence/evidence.py" --store "$store" record-check --name "$name" --rev "$rev" "$flag" --class nix-check --src seat-integrate --duration "$dur" >>"${log:-/dev/null}" ||
      factory_log "evidence: could not record $name@$rev ($?)"
  fi
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
# ROUTE/ROLE/KIND/SIZE. Prints "MODEL EFFORT" for the most specific matching
# row (specificity = number of fields not "any"); ties go to the earliest row.
# Only rows whose `route` equals the requested route are considered; a row
# without a `route` key defaults to openrouter. Returns 3 with a message on
# stderr when the file is missing, a row is malformed (missing one of the five
# required keys, a value not matching [A-Za-z0-9._:/-]+, an unknown
# route/role/kind/size word, or an effort outside off|low|medium|high|xhigh),
# or there is no default (any/any/any) row for the requested route. Pure bash
# line walk.
# Usage: factory_route [--route R] <role> <kind> <size> [FILE]
# The default table is ${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/
# docs/ledger/routing.toml}; an explicit FILE still wins over the env var.
factory_route() {
  local route=openrouter
  if [ "$1" = "--route" ]; then
    route=$2
    shift 2
  fi
  local role=$1 kind=$2 size=$3
  local file=${4:-${FACTORY_ROUTING_TABLE:-$FACTORY_TOOLBOX_REPO/docs/ledger/routing.toml}}
  local -a lines=()
  local line key val i n
  local row=0 started=0 cur_route cur_role cur_kind cur_size cur_model cur_effort
  local best=-1 best_model best_effort have_default=0 cur_spec

  [ -f "$file" ] || {
    printf 'factory_route: no routing table: %s\n' "$file" >&2
    return 3
  }
  mapfile -t lines <"$file"
  n=${#lines[@]}

  # Validate the just-finished row (if any) and fold it into the best match.
  # Reads/writes factory_route's locals via dynamic scoping.
  _factory_route_finish_row() {
    local missing=0 word
    [ "$started" -eq 1 ] || return 0
    # A row without a route key defaults to openrouter.
    [ -n "${cur_route+x}" ] || cur_route=openrouter
    [ -n "${cur_role+x}" ] || missing=1
    [ -n "${cur_kind+x}" ] || missing=1
    [ -n "${cur_size+x}" ] || missing=1
    [ -n "${cur_model+x}" ] || missing=1
    [ -n "${cur_effort+x}" ] || missing=1
    if [ "$missing" -eq 1 ]; then
      printf 'factory_route: %s: row %d: missing one of role/kind/size/model/effort\n' "$file" "$row" >&2
      return 3
    fi
    for word in "$cur_route" "$cur_role" "$cur_kind" "$cur_size" "$cur_model" "$cur_effort"; do
      case $word in
        '' | *[!A-Za-z0-9._:/-]*) ;;
        *) continue ;;
      esac
      printf 'factory_route: %s: row %d: bad value %q\n' "$file" "$row" "$word" >&2
      return 3
    done
    case $cur_route in
      openrouter | claude) ;;
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
    cur_spec=0
    [ "$cur_role" = "any" ] || cur_spec=$((cur_spec + 1))
    [ "$cur_kind" = "any" ] || cur_spec=$((cur_spec + 1))
    [ "$cur_size" = "any" ] || cur_spec=$((cur_spec + 1))
    if [ "$cur_route" = "$route" ] && [ "$cur_role" = "any" ] && [ "$cur_kind" = "any" ] && [ "$cur_size" = "any" ]; then
      have_default=1
    fi
    if [ "$cur_route" = "$route" ] &&
      { [ "$cur_role" = "$role" ] || [ "$cur_role" = "any" ]; } &&
      { [ "$cur_kind" = "$kind" ] || [ "$cur_kind" = "any" ]; } &&
      { [ "$cur_size" = "$size" ] || [ "$cur_size" = "any" ]; }; then
      if [ "$cur_spec" -gt "$best" ]; then
        best=$cur_spec
        best_model=$cur_model
        best_effort=$cur_effort
      fi
    fi
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
        unset cur_route cur_role cur_kind cur_size cur_model cur_effort
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
          model) cur_model=$val ;;
          effort) cur_effort=$val ;;
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
  [ "$have_default" -eq 1 ] || {
    printf 'factory_route: %s: no default (any/any/any) row\n' "$file" >&2
    return 3
  }
  printf '%s %s\n' "$best_model" "$best_effort"
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
