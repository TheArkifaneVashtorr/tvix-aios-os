#!/usr/bin/env bash
# dsh-openrouter -- the DeepSeek Harness (dsh, pkgs/dsh) on the host, talking
# to OpenRouter directly, for the operator's own interactive work.
#
# Why this exists (2026-09-03): the lane runs dsh as a batch job inside a
# sandboxed unit (lane-submit --kind dsh: snapshot in, diff out) -- right for
# the factory, slow for a person. This wrapper boots the same pinned harness
# in the current directory with an OpenAI-compatible route to OpenRouter, so
# DeepSeek does the day-to-day editing and the Claude budget is spent on
# judgement. What it deliberately is NOT: a lane. Nothing here is network-
# confined by a namespace or a broker -- the harness reaches openrouter.ai
# on its own, with a key the operator holds under their own uid.
#
# What it guarantees instead, and tests (tests/unit/70-dsh-openrouter.bats):
#   * it refuses to start in a local-only tree (the lane's own refusal list:
#     Claude memory, mounted and stored baskets, ~/strategy, Helm, broker,
#     lane spools, secrets) -- before it touches the key;
#   * the key comes from OPENROUTER_API_KEY or from a file that is yours
#     alone (0600/0400, regular, owned by you); it is never printed;
#   * telemetry is off, the web-search/fetch tool is off, the browser UI
#     binds 127.0.0.1 only (a --host passthrough is rejected), and the model
#     route is exactly the one composed here (--dump-config shows it);
#   * the harness's own sandbox (bubblewrap, then Landlock) confines tool
#     calls to the working tree by default (workspace-write); danger-full-
#     access is opt-in per launch.
#
# What it cannot do: stamp OpenRouter's zero-data-retention on each request
# (dsh's provider config carries headers, not body fields). ZDR and the
# training opt-out are ACCOUNT settings the operator flips by hand --
# docs/runbooks/lanes.md, "OpenRouter account settings".
#
# The profile boot of dsh 0.1.2-rc.1 injects a hot-reload plugin for the
# web profile that demands Node's --expose-internals; that flag is refused
# in NODE_OPTIONS, so the web mode runs bin.js through node explicitly.
set -euo pipefail

usage() {
  cat <<'USAGE'
usage: dsh-openrouter [--model ID] [--permission MODE] [-- web-app flags...]
       dsh-openrouter [--model ID] [--permission MODE] --headless "TASK"
       dsh-openrouter [--model ID] --dump-config
       dsh-openrouter --denials [N]

Runs the DeepSeek Harness in the current directory against OpenRouter.
Default: the browser UI on 127.0.0.1 at a free port (dsh prints the token URL
and opens it; add `-- --no-open`, or `-- --port N` for a fixed port). --headless answers one task on stdout
and exits. --dump-config prints the composed profile (no secrets) and exits.
--denials lists the last N (default 20) PreToolUse denial records recorded
by the seat's hook guard, read back from the session transcripts under
$DSH_HOME/sessions (no key or workspace check needed; see
docs/runbooks/lanes.md, "Reading the denial audit").

  --model ID          OpenRouter model id (default: $OPENROUTER_MODEL or
                      deepseek/deepseek-v4-pro-0813)
  --permission MODE   read-only | workspace-write (default) | danger-full-access
  --broker            run behind the egress broker: no key (OPENROUTER_API_KEY
                      becomes the placeholder injected-by-broker), HTTPS_PROXY
                      and NODE_EXTRA_CA_CERTS taken from the unit, and the
                      default route's gateway must be the broker's hostAddress
  --bind-namespace ADDR (with --broker only) relay the browser UI to ADDR
                      with a unit-owned forwarder: dsh itself stays on
                      127.0.0.1 (its loopback guard) and socat carries
                      ADDR:<port> to 127.0.0.1:<port>

Environment: OPENROUTER_API_KEY (used as is) or OPENROUTER_KEY_FILE
(default ~/.config/openrouter/key, must be 0600 and yours); OPENROUTER_BASE_URL
(default https://openrouter.ai/api/v1); OPENROUTER_CONTEXT_WINDOW (default
262144); OPENROUTER_MODELS (extra picker entries, space-separated; default
deepseek/deepseek-v4-flash moonshotai/kimi-k3 z-ai/glm-5.3 z-ai/glm-5.3-flash anthropic/claude-fable-5.1; set it empty for none);
OPENROUTER_REASONING_EFFORT (default medium; off | low | medium | high | xhigh);
DSH_HOME (default ~/.local/share/dsh-openrouter);
DSH_CACHE_ROOT (default /tmp, parent of the nix fetcher cache dir).
Exit codes: 2 usage, 3 refused workspace, 4 key problem, 5 bad value.
USAGE
}

die() {
  local code=$1
  shift
  printf 'dsh-openrouter: %s\n' "$*" >&2
  exit "$code"
}

mode=web
model=${OPENROUTER_MODEL:-deepseek/deepseek-v4-pro-0813}
# P3 (2026-09-05): N21 let an explicit effort env var override a saved
# selection; the model needs the same rule. model_explicit records whether
# the model came from the operator (--model or a non-empty OPENROUTER_MODEL)
# rather than the wrapper default, so the call site below can rewrite the
# saved agent-default-model.model before dsh boots.
model_explicit=0
[ -n "${OPENROUTER_MODEL:-}" ] && model_explicit=1
permission=${DSH_PERMISSION_MODE:-workspace-write}
reasoning=${OPENROUTER_REASONING_EFFORT:-medium}
task=
# SB2: --broker runs the seat behind the egress broker (no key; proxy and CA
# from the unit environment; the UI binds the namespace address instead of
# 127.0.0.1). --bind-namespace names that address and is accepted only with
# --broker.
broker=0
bind_namespace=
bind_seen=0
while [ $# -gt 0 ]; do
  case $1 in
    -h | --help)
      usage
      exit 0
      ;;
    --model)
      [ $# -ge 2 ] || die 2 "--model needs a value"
      model=$2
      model_explicit=1
      shift 2
      ;;
    --permission)
      [ $# -ge 2 ] || die 2 "--permission needs a value"
      permission=$2
      shift 2
      ;;
    --broker)
      broker=1
      shift
      ;;
    --bind-namespace)
      [ $# -ge 2 ] || die 2 "--bind-namespace needs a value"
      bind_namespace=$2
      bind_seen=1
      shift 2
      ;;
    --headless)
      [ $# -ge 2 ] || die 2 "--headless needs the task text"
      mode=headless
      task=$2
      shift 2
      ;;
    --dump-config)
      mode=dump
      shift
      ;;
    --denials)
      mode=denials
      shift
      break
      ;;
    --)
      shift
      break
      ;;
    -*)
      die 2 "unknown option $1 (try --help)"
      ;;
    *)
      break
      ;;
  esac
done

# --bind-namespace is accepted only with --broker (checked here, after the
# loop, so it holds regardless of the flag's order relative to --broker).
# SB2b: the address must be a real dotted IPv4 that is not 0.0.0.0, not
# loopback and not a flag-shaped string; anything else is a usage error. The
# unit always supplies the namespace veth peer (10.100.4.2), so a hand-typed
# value that would bind the UI somewhere else is refused here rather than
# reaching --host unreviewed.
# SB2r: each octet must be 0-255 with no leading zeros (a shape-only regex
# accepted 256.1.1.1), and an explicitly empty value is refused too -- both
# gates now key on bind_seen, so `--bind-namespace ''` no longer slips past
# the `[ -n ... ]` checks and degrades to 127.0.0.1.
if [ "$bind_seen" -eq 1 ]; then
  if [ "$broker" -ne 1 ]; then
    die 2 "the browser UI binds 127.0.0.1 only; --bind-namespace needs --broker"
  fi
  if [ -z "$bind_namespace" ]; then
    die 2 "--bind-namespace needs a dotted IPv4 address (got '')"
  fi
  case $bind_namespace in
    0.0.0.0 | 127.*) die 2 "--bind-namespace must be a dotted IPv4 address that is not 0.0.0.0 or loopback (got '$bind_namespace')" ;;
  esac
  [[ $bind_namespace =~ ^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])$ ]] ||
    die 2 "--bind-namespace needs a dotted IPv4 address (got '$bind_namespace')"
fi

# --denials is a read-only report over past sessions, not a launch: it needs
# neither the OpenRouter key nor the workspace refusal check below, so it
# dispatches before either runs. "$@" here is the optional N, verbatim.
if [ "$mode" = denials ]; then
  export DSH_HOME=${DSH_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/dsh-openrouter}
  denials_reader=${DSH_DENIALS_READER:?dsh-openrouter: DSH_DENIALS_READER must point at the denials reader}
  exec "$denials_reader" "$@"
fi

port_given=
web_port=
_port_value_pending=0
for arg in "$@"; do
  if [ "$_port_value_pending" -eq 1 ]; then
    web_port=$arg
    _port_value_pending=0
    continue
  fi
  case $arg in
    --host | --host=*) die 2 "the browser UI binds 127.0.0.1 only; --host is not accepted" ;;
    --port=*)
      port_given=1
      web_port=${arg#--port=}
      ;;
    --port)
      port_given=1
      _port_value_pending=1
      ;;
  esac
done

# SB6b: --port is validated wherever it is given (any mode, not only under
# --bind-namespace), and --bind-namespace now REQUIRES a --port -- the
# forwarder at the bottom would otherwise build socat's argv with an empty
# port (TCP-LISTEN:,bind=...). The integer check runs only when a --port was
# actually given; an absent --port without --bind-namespace still gets the
# wrapper's own `--port 0` in the web case below (the OS picks the port).
if [ "$bind_seen" -eq 1 ] && [ -z "$web_port" ]; then
  die 2 "--bind-namespace needs --port (pass -- --port N)"
fi
if [ -n "$port_given" ]; then
  case $web_port in
    '' | *[!0-9]*) die 2 "--port must be an integer 1024-65535 (got '$web_port')" ;;
  esac
  if [ "$web_port" -lt 1024 ] || [ "$web_port" -gt 65535 ]; then
    die 2 "--port must be an integer 1024-65535 (got '$web_port')"
  fi
fi

case $model in
  '' | *[!A-Za-z0-9._:/-]*) die 5 "model id '$model' must match [A-Za-z0-9._:/-]+" ;;
esac
case $permission in
  read-only | workspace-write | danger-full-access) ;;
  *) die 5 "--permission must be read-only, workspace-write or danger-full-access" ;;
esac
case $reasoning in
  off | low | medium | high | xhigh) ;;
  *) die 5 "OPENROUTER_REASONING_EFFORT must be off, low, medium, high or xhigh" ;;
esac
base_url=${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}
case $base_url in
  http://* | https://*) ;;
  *) die 5 "OPENROUTER_BASE_URL must start with http:// or https://" ;;
esac
case $base_url in
  *[[:space:]\'\"]*) die 5 "OPENROUTER_BASE_URL contains whitespace or quotes" ;;
esac
context_window=${OPENROUTER_CONTEXT_WINDOW:-262144}
case $context_window in
  '' | *[!0-9]*) die 5 "OPENROUTER_CONTEXT_WINDOW must be a positive integer" ;;
esac
# Extra OpenRouter model ids offered in the UI's picker beside the default
# (space-separated); each gets the same context window. Only ids that exist
# on OpenRouter make sense here -- the picker cannot tell. The default model
# is DeepSeek V4 Pro (dated id = the pin). The picker set is the dsh
# factory's role->model map, documented in the harness repo at
# ~/flakes/dsh-harness/README.md (this repo's tools/factory/dark-factory.js
# names the roles in Claude shorthand sonnet/opus/fable, not these OpenRouter
# ids): Flash = structured backend worker, Kimi K3 = product/UX/frontend,
# GLM 5.3 = feasibility/routine, GLM 5.3 Flash = cheap routine. With Flash
# alone (the old default) a three-model probe died UNKNOWN_MODEL and cost a
# relaunch. FA11 (2026-09-10) adds anthropic/claude-fable-5.1 -- the lane's
# full provider id, never the routing table's `fable` shorthand, or the two
# schemes collide (see the naming trap below).
# OPENROUTER_MODELS='' offers nothing extra.
extra_models=()
for extra in ${OPENROUTER_MODELS-deepseek/deepseek-v4-flash moonshotai/kimi-k3 z-ai/glm-5.3 z-ai/glm-5.3-flash anthropic/claude-fable-5.1}; do
  case $extra in
    *[!A-Za-z0-9._:/-]*) die 5 "OPENROUTER_MODELS entry '$extra' must match [A-Za-z0-9._:/-]+" ;;
  esac
  [ "$extra" = "$model" ] || extra_models+=("$extra")
done

# The lane's refusal list (pkgs/lane/lane-submit.py FORBIDDEN_REPO_PREFIXES),
# applied to the working directory: a network-capable harness must never
# be started inside a local-only tree. Checked before the key is read, so a
# refusal never touches the credential. This array must stay identical to
# that tuple and to hook-guard.py's PROTECTED_ABSOLUTE + HOME-relative
# literals; tests/lane/test_forbidden_lists_agree.py proves the three agree.
# Generating the list from a single Nix source is still a gap (claim
# `forbidden-list-single-source`).
workspace=$(pwd -P)
forbidden=(
  "$HOME/.claude"
  "$HOME/.codex"
  "$HOME/.config/openrouter"
  "$HOME/strategy"
  /run/baskets
  /var/lib/baskets
  /var/lib/helm
  /var/lib/egress-broker
  /var/lib/lanes
  /var/lib/secrets
)
for prefix in "${forbidden[@]}"; do
  resolved=$(realpath -m -- "$prefix")
  case "$workspace/" in
    "$resolved/"*) die 3 "refusing to start in $workspace: it is under $resolved, which is local-only (docs/runbooks/lanes.md)" ;;
  esac
done

# SB2: behind the broker the seat holds no key of its own. The whole key
# block is skipped -- the key file is never stat'ed or read (a mode-000 file
# must not even be touched) -- and OPENROUTER_API_KEY is ALWAYS replaced with
# a placeholder, even when a key was pre-set, so no real key can leave this
# wrapper's process. The placeholder is what reaches the broker, which
# replaces the Authorization header with the real key injected from the
# root-only secret.
if [ "$broker" -eq 1 ]; then
  # SB2r: the ignored-key line fires only when a pre-set key *differs* from
  # the placeholder. SB1's unit already sets OPENROUTER_API_KEY to the
  # placeholder itself, so a normal production launch is silent; the line is
  # reserved for the real leak it is meant to signal (an operator key carried
  # into the namespace).
  if [ -n "${OPENROUTER_API_KEY:-}" ] && [ "$OPENROUTER_API_KEY" != injected-by-broker ]; then
    printf 'dsh-openrouter: a pre-set OPENROUTER_API_KEY is ignored under --broker (the broker injects the real key)\n' >&2
  fi
  OPENROUTER_API_KEY=injected-by-broker
  export OPENROUTER_API_KEY
  key_source="credential: placeholder (broker injects)"
elif [ -n "${OPENROUTER_API_KEY:-}" ]; then
  key_source="key from OPENROUTER_API_KEY (environment)"
else
  key_file=${OPENROUTER_KEY_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/openrouter/key}
  if [ ! -e "$key_file" ]; then
    die 4 "no key: export OPENROUTER_API_KEY, or create $key_file with: (umask 077; mkdir -p \"\$(dirname $key_file)\"; IFS= read -r -s k; printf '%s' \"\$k\" > $key_file) -- paste the key at the blank line"
  fi
  if [ -L "$key_file" ] || [ ! -f "$key_file" ]; then
    die 4 "$key_file must be a regular file, not a symlink"
  fi
  if [ "$(stat -c %u -- "$key_file")" != "$(id -u)" ]; then
    die 4 "$key_file is not owned by you"
  fi
  key_mode=$(stat -c %a -- "$key_file")
  case $key_mode in
    600 | 400) ;;
    *) die 4 "$key_file has mode $key_mode; it must be 0600 or 0400 (chmod 0600 $key_file)" ;;
  esac
  key=$(head -n 1 -- "$key_file")
  key=${key//[[:space:]]/}
  [ -n "$key" ] || die 4 "$key_file is empty"
  export OPENROUTER_API_KEY=$key
  key_source="key from $key_file"
  # SB2: the key-file path is deprecated -- seat jobs run behind the broker,
  # and the secret stays root-only. Warn (do not refuse) so the operator is
  # nudged without being locked out in the meantime.
  printf 'dsh-openrouter: the key file is deprecated; seat jobs run behind the broker (docs/runbooks/seat.md)\n' >&2
fi

# SB2: --broker requires the proxy and CA the unit provides, and refuses
# anywhere but inside the broker's network namespace. The namespace is proven
# by the default route: exactly one route, whose `via` equals the proxy host
# (the broker's hostAddress). A real namespace has one veth peer gateway; the
# host has none, so a bare-host launch dies here before it can reach anywhere.
if [ "$broker" -eq 1 ]; then
  proxy=${HTTPS_PROXY:-${https_proxy:-}}
  # SB2b: the proxy must be exactly http://<host>:<port> (an optional trailing
  # slash is accepted). One form check covers the empty/absent case too; the
  # old `[ -n "$proxy" ]` line was dead weight.
  if [[ ! $proxy =~ ^http://[^/:]+:[0-9]+/?$ ]]; then
    die 5 "--broker: HTTPS_PROXY must be http://<host>:<port> (got '$proxy')"
  fi
  proxy_hostport=${proxy#http://}
  proxy_host=${proxy_hostport%%:*}

  [ -n "${NODE_EXTRA_CA_CERTS:-}" ] || die 5 "--broker needs NODE_EXTRA_CA_CERTS set to the broker's CA bundle"
  [ -f "$NODE_EXTRA_CA_CERTS" ] || die 5 "--broker: NODE_EXTRA_CA_CERTS ($NODE_EXTRA_CA_CERTS) is not an existing file"

  routes=$(ip -4 route show default) || die 5 "--broker outside a broker namespace"
  n=0
  via_gw=
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    n=$((n + 1))
    # Parse the line field by field: the gateway is the token immediately
    # AFTER the `via` keyword, compared exactly to the proxy host. A substring
    # test would accept `default via 192.168.1.1 dev via 10.100.4.1 x`; this
    # walk takes the FIRST `via` (192.168.1.1) and refuses. `via` with no
    # following token leaves via_gw empty and fails closed.
    read -r -a tokens <<<"$line"
    for i in "${!tokens[@]}"; do
      if [ "${tokens[i]}" = via ]; then
        [ $((i + 1)) -lt ${#tokens[@]} ] && via_gw=${tokens[i + 1]}
        break
      fi
    done
  done <<<"$routes"
  [ "$n" -eq 1 ] || die 5 "--broker outside a broker namespace"
  [ "$via_gw" = "$proxy_host" ] || die 5 "--broker outside a broker namespace"
fi

export DSH_HOME=${DSH_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/dsh-openrouter}
mkdir -p -- "$DSH_HOME"
chmod 700 -- "$DSH_HOME"

# N21 (2026-09-05, field finding from the M2 measurement): a set
# OPENROUTER_REASONING_EFFORT used to reach only the route's `reasoning:`
# field, which dsh treats as the *fallback* it reads only when the agent
# selection carries no effort. The selection is the saved
# `agent-default-model.reasoningEffort` in $DSH_HOME/settings.yaml -- dsh
# writes it at launch with the per-model default (medium), and a saved
# preference beats the env var, so an env var could be set and silently
# ignored. Writing the requested level into that selection *before* dsh
# boots is what makes the env var really override a saved (or default)
# level. When the var is unset the saved selection is the operator's choice
# and is left alone; only the route default applies to a fresh home.
#
# P3 (2026-09-05): the same env-beats-saved rule now covers the model.
# dsh's *agent selection* saved in settings.yaml also beats the route's
# `model:` line, so an explicit --model/OPENROUTER_MODEL used to be silently
# ignored when a saved selection existed -- and worse, a saved Pro selection
# against a route that lists only the requested model died UNKNOWN_MODEL at
# boot. Writing the requested model into the selection before dsh boots is
# what makes the explicit model really win. Without an explicit model the
# saved selection is left alone, exactly as the effort rule leaves a saved
# effort.
#
# Pure bash here on purpose: the wrapper's runtime PATH carries only
# coreutils/findutils (no awk/sed/grep), so the edit is a line walk over the
# three keys this YAML block always holds -- `agent-default-model:` and its
# `reasoningEffort:` and `model:`. The file is otherwise left intact, written
# atomically (temp file in the same 0700 home, then rename) and forced 0600.
# The two arguments are LEVEL_OR_EMPTY then MODEL_OR_EMPTY: whichever is
# non-empty is rewritten (or inserted when the block lacks it); an empty one
# leaves that key untouched.
write_agent_selection() {
  local level=$1 model_arg=$2 settings=$DSH_HOME/settings.yaml tmp=$DSH_HOME/settings.yaml.tmp.$$
  local -a lines=()
  local i n agent_idx=-1 effort_idx=-1 model_idx=-1 line indent
  local old_umask
  # N21b (2026-09-05): the temp file is only ever appended to (>>) below, so a
  # stale same-PID temp left by a crashed earlier run would prepend its content
  # to the new settings.yaml. Truncate it before the first append.
  : >"$tmp"
  # A function is not a subshell: scope the 077 mask here and restore it after
  # the write, rather than letting it leak to the rest of the script.
  old_umask=$(umask)
  umask 077
  if [ -f "$settings" ]; then
    mapfile -t lines <"$settings"
  fi
  n=${#lines[@]}
  for ((i = 0; i < n; i++)); do
    if [ "${lines[i]}" = "agent-default-model:" ]; then
      agent_idx=$i
      break
    fi
  done
  if [ "$agent_idx" -ge 0 ]; then
    for ((i = agent_idx + 1; i < n; i++)); do
      line=${lines[i]}
      [ -z "$line" ] && continue
      case "$line" in
        [[:space:]]*)
          case "$line" in
            *reasoningEffort:*)
              [ "$effort_idx" -lt 0 ] && effort_idx=$i
              ;;
            *model:*)
              [ "$model_idx" -lt 0 ] && model_idx=$i
              ;;
          esac
          ;;
        *) break ;;
      esac
    done
  fi
  for ((i = 0; i < n; i++)); do
    if [ "$i" -eq "$effort_idx" ] && [ -n "$level" ]; then
      line=${lines[i]}
      indent=${line%%[![:space:]]*}
      printf '%sreasoningEffort: %s\n' "$indent" "$level" >>"$tmp"
    elif [ "$i" -eq "$model_idx" ] && [ -n "$model_arg" ]; then
      line=${lines[i]}
      indent=${line%%[![:space:]]*}
      printf '%smodel: %s\n' "$indent" "$model_arg" >>"$tmp"
    else
      printf '%s\n' "${lines[i]}" >>"$tmp"
      if [ "$i" -eq "$agent_idx" ]; then
        if [ -n "$model_arg" ] && [ "$model_idx" -lt 0 ]; then
          printf '  model: %s\n' "$model_arg" >>"$tmp"
        fi
        if [ -n "$level" ] && [ "$effort_idx" -lt 0 ]; then
          printf '  reasoningEffort: %s\n' "$level" >>"$tmp"
        fi
      fi
    fi
  done
  if [ "$agent_idx" -lt 0 ]; then
    {
      printf 'agent-default-model:\n'
      printf '  provider: openrouter\n'
      printf '  model: %s\n' "$model"
      printf '  reasoningEffort: %s\n' "${level:-medium}"
    } >>"$tmp"
  fi
  chmod 600 -- "$tmp"
  mv -f -- "$tmp" "$settings"
  chmod 600 -- "$settings"
  umask "$old_umask"
}

if { [ -n "${OPENROUTER_REASONING_EFFORT:-}" ] || [ "$model_explicit" -eq 1 ]; } && [ "$mode" != dump ]; then
  write_agent_selection "${OPENROUTER_REASONING_EFFORT:+$reasoning}" "$([ "$model_explicit" -eq 1 ] && printf %s "$model")"
fi

# H4 (review 2026-09-04): the harness sandbox makes $HOME read-only for
# model-run commands, so nix cannot write its fetcher cache. 14 of 29
# sessions hit "attempt to write a readonly database"; each invented its
# own workaround and 20+ distinct paths appear across the corpus, one
# session using $(mktemp -d) per call (a cold cache every command).
# writableRoots under workspace-write is exactly {workspaceRoot, /tmp,
# os.tmpdir()}: a state dir under $HOME or $DSH_HOME is blocked
# identically. The launcher is the only lever -- dsh refuses XDG_* from
# $DSH_HOME/.env and its shell tool has no env knob.
# The seat default stays /tmp so the warm cache is not fragmented into a
# fresh dir every session; DSH_CACHE_ROOT redirects that default (the tests
# point it at their own temp root so they never read or delete the shared
# /tmp path). Order matters: mkdir first, then the ownership guard, then
# chmod. A pre-existing dir owned by someone else must die 5 here, not blow
# up in chmod with a raw "Operation not permitted" (status 1) -- placed
# ahead, chmod makes the guard unreachable (review N1-2).
cache_root=${DSH_CACHE_ROOT:-/tmp}
export XDG_CACHE_HOME=${XDG_CACHE_HOME:-$cache_root/dsh-openrouter-cache-$(id -u)}
[ -L "$XDG_CACHE_HOME" ] && die 5 "$XDG_CACHE_HOME is a symlink; refusing"
mkdir -p -- "$XDG_CACHE_HOME"
[ "$(stat -c %u -- "$XDG_CACHE_HOME")" = "$(id -u)" ] || die 5 "$XDG_CACHE_HOME is not owned by you"
chmod 700 -- "$XDG_CACHE_HOME"

# U6 step 1 (review 2026-09-04): the seat is wired into the OS, but the
# payload that gives it a mind -- skills/ and AGENTS.md -- is still deployed
# by two hand-made symlinks in ~/flakes/dsh-harness ("Deploy (no flake yet
# -- manual symlinks)"). A missing, dangling or empty payload is exactly the
# state in which the operator must fix it, so warn rather than refuse: a
# refusal would lock the operator out of the seat precisely when the payload
# is what is broken. dsh follows a working symlink, so a deployed symlink
# must not warn.
warn() {
  printf 'dsh-openrouter: %s\n' "$*" >&2
}
warn_missing_payload() {
  local path=$1 kind=$2 recipe=$3
  if [ ! -e "$path" ]; then
    warn "$path is missing or a dangling symlink: the seat has no $kind. Deploy it: $recipe"
    return
  fi
  if [ -d "$path" ] && [ -z "$(find -H "$path" -mindepth 1 -print -quit)" ]; then
    warn "$path is empty: the seat has no $kind. Deploy it: $recipe"
  fi
  if [ -f "$path" ] && [ ! -s "$path" ]; then
    warn "$path is empty: the seat has no $kind. Deploy it: $recipe"
  fi
}
warn_missing_payload "$DSH_HOME/skills" "skill catalog" "ln -s ~/flakes/dsh-harness/skills $DSH_HOME/skills"
warn_missing_payload "$DSH_HOME/AGENTS.md" "bootstrap memory" "ln -sf ~/flakes/dsh-harness/AGENTS.md $DSH_HOME/AGENTS.md"

export DSH_TELEMETRY_MODE=DISABLED
export DSH_TELEMETRY_DISABLED=1
export DSH_PERMISSION_MODE=$permission
if [ -z "${SSL_CERT_FILE:-}" ] && [ -r /etc/ssl/certs/ca-certificates.crt ]; then
  export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
fi

# The route overlay lives under DSH_HOME (0700) and names the key only by
# its environment variable; it is rewritten on every launch so a stale
# model or URL can never survive a change of arguments.
overlay=$DSH_HOME/openrouter-route.yml
umask 077
# N14 (2026-09-04): the seat asks default reasoning effort medium. The route's
# `reasoning:` field is the knob dsh's request path reads (profile.reasoning,
# the fallback used when the agent selection carries no effort);
# the per-model `reasoningEfforts` map is what makes low/medium selectable at
# all -- pi-ai's shipped OpenRouter catalog marks DeepSeek low/medium as
# unsupported (null), so without this override a medium/high/low request dies
# UNSUPPORTED_REASONING_EFFORT. The wire spelling is the map's value; `off`
# stays `none` (the explicit no-reasoning request OpenRouter accepts). The
# quality/cost effect of medium over none is UNMEASURED -- see the commit.
#
# N19/N19b (2026-09-04): every effort level dsh's picker can offer for this
# route is declared here, so a saved preference can never refuse the launch.
# dsh validates the operator's saved `reasoningEffort` (settings.yaml, written
# by the UI picker) against this map, and a level absent from it dies
# UNSUPPORTED_REASONING_EFFORT before any request -- a saved `xhigh` bricked
# the seat exactly that way (generation 37). OpenRouter lists effort values
# max, xhigh, high, medium, low, minimal, none
# (https://openrouter.ai/docs/use-cases/reasoning-tokens); the picker's five
# levels are `off` (wire `none`), `low`, `medium`, `high` and `xhigh`, each
# passed through unmangled -- `xhigh` is a value this model's catalog entry
# accepts, so it is NOT downgraded to `high`. `off` stays `none`.
cat >"$overlay" <<YAML
# written by dsh-openrouter; edit nothing here, it is regenerated each launch
- id: llm-pi-ai
  config:
    providers:
      openrouter:
        api: openai-completions
        baseURL: $base_url
        apiKeyEnv: OPENROUTER_API_KEY
        reasoning: $reasoning
        models:
          - id: $model
            contextWindow: $context_window
            reasoningEfforts:
              off: none
              low: low
              medium: medium
              high: high
              xhigh: xhigh
YAML
for extra in "${extra_models[@]+"${extra_models[@]}"}"; do
  printf '%s\n' \
    "          - id: $extra" \
    "            contextWindow: $context_window" \
    "            reasoningEfforts:" \
    "              off: none" \
    "              low: low" \
    "              medium: medium" \
    "              high: high" \
    "              xhigh: xhigh" >>"$overlay"
done
cat >>"$overlay" <<YAML
- id: agent-default-model
  config:
    provider: openrouter
    model: $model
- id: tool-web
  disabled: true
# dsh's built-in "deepseek-official" route (DeepSeek's own platform, its own
# key) is removed outright: with it present the UI's model picker lists its
# entries beside ours, and a click there ends in "no API key for provider
# route deepseek-official" (operator, 2026-09-03). Only OpenRouter routes
# exist in this profile.
- id: llm-deepseek
  disabled: true
YAML

# N7 (review 2026-09-04): the deny-only "protect the model" hook set. The
# bridge dsh ships (@deepseek-ai/dsh-hooks-claude-code) runs Claude Code
# command hooks on dsh's interception seams; we point it at hook-guard (the
# packaged hook-guard.py, exposed as DSH_HOOK_GUARD by the wrapper's nix).
# Two traps, both read from the pin (0.1.2-rc.1) and both worth keeping in
# sight:
#   * the patch that adds the entry MUST be `- insert:` -- a bare top-level
#     `- name:` composes nothing (dsh-app-boot requires `id` on non-insert
#     patches, and a plugin entry has none);
#   * dsh's tool is `bash`, not Claude Code's `Bash` -- a verbatim Claude
#     Code hooks.json matches nothing and fails silently.
# Deny-only: {"continue": false} is recorded but not applied, `updatedInput`
# is logged but not honoured, and a top-level {"decision":"deny"} is ignored
# -- only hookSpecificOutput.permissionDecision works. A deny-list over shell
# command strings is a heuristic and an audit trail, NOT a boundary: the
# boundaries remain file mode, PAM, the wrapper's refusal list and the lane's
# netns.
#
# CLAUDE_PROJECT_DIR is supplied by the bridge from `projectDir` (== the
# workspace) and does reach the hook -- hook-guard.py needs it to resolve a
# relative edit/write path. Regenerated each launch under the umask 077 set
# for the overlay, so hooks.json is private.
#
# Round 2 (review 2026-09-04): the first cut logged one JSON line per denial
# to a dotfile under $workspace -- the one root the hook's own sandboxed
# shell can durably write to (workspace-write mounts only the workspace and
# a *per-invocation* tmpfs `/tmp` that vanishes the instant that one hook
# process exits; confirmed empirically, HOOKPROBE2). That file was rejected
# on review: it sits inside the tree the audited model itself can write to
# (hook-guard's own edit/write checks never cover it, so `rm` or a stray
# write erases the trail), and it is untracked, unignored dirt in whatever
# workspace happens to be current -- a factory run's `git status --porcelain`
# gate would trip on it. hook-guard.py now writes each denial's JSON record
# to **stderr** instead, and nothing to disk here: dsh's own hook bridge
# (@deepseek-ai/dsh-hook-protocol) captures a hook's stderr and stores it
# verbatim as `stderrSummary` on that call's `hook/result` event in the
# session transcript ($DSH_HOME/sessions/<cwd-key>/<session>/session.jsonl.zstd)
# -- a root the model cannot reach at all. `dsh-openrouter --denials` reads
# it back; see docs/runbooks/lanes.md.
hook_guard=${DSH_HOOK_GUARD:?dsh-openrouter: DSH_HOOK_GUARD must point at the hook guard}
# RT5: the routing table the hook guard applies to sub-agent and nested-seat
# model choices. Resolved once here (never by the guard itself, so the guard
# sees one table regardless of which matcher fired) and passed to every
# matcher as --routing-table: ${FACTORY_ROUTING_TABLE:-$HOME/nixos-agent-env/
# docs/ledger/routing.toml}, the same default the seat's factory_route reads.
# The guard denies a sub-agent (or a nested --model / OPENROUTER_MODEL) whose
# model is not an OpenRouter row of this table, and fails closed when the
# table is unreadable -- see docs/runbooks/lanes.md.
routing_table=${FACTORY_ROUTING_TABLE:-$HOME/nixos-agent-env/docs/ledger/routing.toml}
hooks_json=$DSH_HOME/hooks.json
# SD8: the house guard hook-guard hands every bash/edit/write payload to (the
# orchestrator's tools/orchestrator-guard.sh), so the seat enforces the same
# house rules as the controller (append-only plan headings, plan files change
# only through Edit/Write, .claude/ritual-override, history rewrites). The path
# resolves once here, mirroring the routing table; the shell is $BASH (the
# wrapper's own interpreter, a store path) so the hook never depends on a
# `bash` on the seat unit's PATH.
house_guard=${FACTORY_HOUSE_GUARD:-$HOME/nixos-agent-env/tools/orchestrator-guard.sh}
house_shell=$BASH
# RT5rb (contract item 5): the routing-table path is an operator-set value and
# must survive two quoting layers -- this JSON document, and the shell the
# hook bridge runs the `command` through. Build the command with jq (@sh for
# the shell, the JSON string for the document) rather than interpolating the
# path into a hand-written JSON string, so a path containing a `"` and a space
# round-trips intact. SD8 composes --house-guard and --house-shell the same
# way, so those two paths round-trip too.
hook_command=$(jq -n --arg g "$hook_guard" --arg t "$routing_table" \
  --arg h "$house_guard" --arg s "$house_shell" \
  '("exec " + ($g | @sh) + " --routing-table " + ($t | @sh) + " --house-guard " + ($h | @sh) + " --house-shell " + ($s | @sh))')
cat >"$hooks_json" <<JSON
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "bash",
        "hooks": [
          { "type": "command", "command": $hook_command }
        ]
      },
      {
        "matcher": "edit|write",
        "hooks": [
          { "type": "command", "command": $hook_command }
        ]
      },
      {
        "matcher": "subagent|subagent_fork|workflow",
        "hooks": [
          { "type": "command", "command": $hook_command }
        ]
      }
    ]
  }
}
JSON
cat >>"$overlay" <<YAML
- insert:
    - name: '@deepseek-ai/dsh-hooks-claude-code'
      config:
        configPath: $hooks_json
        projectDir: $workspace
YAML

bin_js=${DSH_OPENROUTER_BIN_JS:?dsh-openrouter: DSH_OPENROUTER_BIN_JS must point at the harness lib/bin.js}
# SB2b: the node interpreter is named here (default `node`, resolved from the
# wrapper's runtime PATH). The unit tests point DSH_OPENROUTER_NODE at a
# recording fake so the bind test can pin the real exec argv and exit status
# without booting the harness.
# SB2r: DSH_OPENROUTER_NODE is a test-only seam, honoured only when
# DSH_OPENROUTER_TEST_SEAM=1 is also set (the seat unit sets neither). Without
# the flag the wrapper ignores the variable -- with one stderr line -- and
# runs the PATH's real node, so a stray env var cannot swap the interpreter
# in production.
node_bin=node
if [ -n "${DSH_OPENROUTER_NODE:-}" ] && [ "${DSH_OPENROUTER_TEST_SEAM:-}" != 1 ]; then
  printf 'dsh-openrouter: DSH_OPENROUTER_NODE is a test-only seam; ignored unless DSH_OPENROUTER_TEST_SEAM=1\n' >&2
fi
if [ "${DSH_OPENROUTER_TEST_SEAM:-}" = 1 ]; then
  node_bin=${DSH_OPENROUTER_NODE:-node}
fi
case $mode in
  dump)
    exec "$node_bin" "$bin_js" --profile web --patch "$overlay" --dump-config
    ;;
  headless)
    printf 'dsh-openrouter: %s via %s, %s, %s, workspace %s\n' \
      "$model" "$base_url" "$permission" "$key_source" "$workspace" >&2
    exec "$node_bin" "$bin_js" --profile headless --patch "$overlay" "$task"
    ;;
  web)
    printf 'dsh-openrouter: %s via %s, %s, %s, workspace %s\n' \
      "$model" "$base_url" "$permission" "$key_source" "$workspace" >&2
    printf 'dsh-openrouter: zero-data-retention is an OpenRouter account setting, not stamped per request here (docs/runbooks/lanes.md)\n' >&2
    # dsh's web profile defaults to port 3080; a second session (another
    # repo, an older window still open) then dies with EADDRINUSE (field
    # bug D2, 2026-09-03). Unless a port was asked for, let the OS pick a
    # free one -- dsh prints the URL it got either way.
    if [ -z "$port_given" ]; then
      set -- --port 0 "$@"
    fi
    # SB4b (2026-09-06): the pinned dsh harness pins its web server to
    # loopback -- --host 10.100.4.2 is refused by the webserver schema and
    # --host 0.0.0.0 by a deliberate guard ("would expose remote code
    # execution to the network"). dsh is therefore always started with
    # --host 127.0.0.1, and --bind-namespace (which SB2r previously fed to
    # --host) instead means: spawn a unit-owned socat forwarder that listens
    # on the namespace address and relays to dsh's loopback on the same
    # port. The forwarder is a child of this wrapper in the seat unit's
    # control group, so it dies with the unit; anything else on the network
    # still cannot reach either address (10.100.4.2 is the netns end of a
    # veth whose only peer is this host, and the nftables rule confines
    # host -> namespace traffic to the web port range).
    if [ -n "$bind_namespace" ]; then
      exec socat "TCP-LISTEN:${web_port},bind=${bind_namespace},fork,reuseaddr" "TCP:127.0.0.1:${web_port}" &
      # FIX4 (2026-09-09): the browser reaches dsh through the socat relay,
      # so its Host header is the namespace authority (10.100.4.2:<port>), not
      # loopback. dsh's host fence (isTrustedApiRequest) then 403s every API
      # call -- the page rendered but directoryPicker/list answered `forbidden`.
      # --trusted-host admits that authority before auth runs, so the API
      # answers 401 (authentication) exactly as it does on loopback. Only set
      # under --bind-namespace; a bare loopback launch passes nothing.
      exec "$node_bin" --expose-internals "$bin_js" --profile web --patch "$overlay" --host 127.0.0.1 --trusted-host "${bind_namespace}:${web_port}" "$@"
    fi
    exec "$node_bin" --expose-internals "$bin_js" --profile web --patch "$overlay" --host 127.0.0.1 "$@"
    ;;
esac
