#!/usr/bin/env bash
# orchestrator-guard.sh — the orchestrator's (Claude Code) deny-only PreToolUse
# hook, wired in .claude/settings.json under matchers `Edit|Write|MultiEdit`
# and `Bash`. It enforces five rules the plain dsh seat guard does not cover:
#
#   1. Typed plan headings in docs/superpowers/plans/*.md — the
#      `### KEY (kind, size) — title` lines the task graph (pkgs/evidence/
#      tasks.py HEADING_RE) reads — are append-only: an edit/write that removes
#      or alters an existing one is refused; adding sections is fine. Withdraw
#      a task with a status row in docs/ledger/task-status.toml instead.
#   2. Plan files change only through the Edit/Write/MultiEdit tools. A Bash
#      command whose text names a plan path — a file directly under
#      docs/superpowers/plans/, or (for the delete family) the plans directory
#      itself or any ancestor of it — together with a write-capable verb is
#      refused. Relative paths are resolved against the payload cwd (when
#      present) and every `cd`/`pushd` base, not just CLAUDE_PROJECT_DIR.
#      Read-only verbs (cat, grep, sed -n, head, tail, diff, wc, git
#      diff/show/log, find without -delete/-exec, …) never deny.
#   3. .claude/ritual-override is the operator's (spec §3.4): every write to,
#      overwrite of, or removal of it is refused — touch, a redirect/cp/mv onto
#      it, rm, sed/perl -i, git checkout/restore/clean on it (Bash), and any
#      Edit/Write/MultiEdit whose path lands on it. It is protected like the
#      plans *directory*: its parent `.claude` and every ancestor down to the
#      project and `/` name it for the delete family (rm/mv/rmdir/rsync/shred/
#      truncate, tar/unzip/cpio extracting into `.claude`, find -delete/-exec,
#      chmod/chown/chattr on the file, `git stash -u`/`-a`, `xargs` carrying a
#      delete verb), a glob token under `.claude/` (`rm -rf .claude/*`) names it
#      via the raw-text fallback, `dd of=…` is admitted into the token scan, and
#      python/perl removal/write spellings naming it are refused. Reading it
#      (cat) is allowed. The pathless git over-denials are narrowed: `git clean`
#      denies only with `-f`, `git checkout`/`git restore` only on a protected
#      path or a bare `--`/`.`, `git stash` only without `-u`/`-a`; and a
#      `git commit -m "…"` message is prose, never scanned for verbs or paths.
#   4. The guard protects the one file it is executing from (SELF_CANON, the
#      canonical path of its own source, resolved inside `main` after the
#      fail-closed EXIT trap is installed — a failed `realpath` faults, never an
#      empty entry), whatever CLAUDE_PROJECT_DIR names: a Bash token — resolved
#      like the plan/override rules against the payload cwd, every `cd`/`pushd`
#      base and the project dir — or an Edit/Write/MultiEdit file_path that
#      canonicalises to SELF_CANON, together with a write-capable verb, is
#      refused with the guard-file reason of the `file` entry. A leading `~/`,
#      `$HOME/` or `${HOME}/` on a path token expands to the guard's $HOME
#      before comparison (only widens denials); the tokeniser keeps a `${NAME}`
#      parameter expansion in its one word so the `${HOME}/` arm is reachable.
#      These text rules are the orchestrator's own session's defence — the
#      orchestrator runs in no unit, so no kernel mount holds its guard. A seat
#      runs inside `seat@`, whose ReadOnlyPaths mounts this very file read-only,
#      a kernel pin no command spelling from a job can slip (see the header of
#      nixosModules/seatLane.nix); the text rules below are belt-and-suspenders
#      for the seat, not its only line.
#   5. The host rules from pkgs/dsh-openrouter/hook-guard.py (same wording) —
#      sudo, nixos-rebuild, mutating systemctl, writes under the protected
#      prefixes — plus the house history rules (git commit --amend, push,
#      rebase, reset --hard).
#
# There is NO command position. The Bash rules scan *every* token of the
# normalised command — the word "git" (or any path token whose basename is
# `git`) marks a git invocation wherever it sits, and a write-verb token fires
# wherever it sits — so a launcher prefix (`nix develop -c`, `timeout`, `nohup`,
# `time`, `!`, `xargs`, `bash -c "…"`, backticks) or a newline or a `;`/`&&`/
# `||` cannot hide a refused subcommand or write. This is a deny-only guard, so
# it deliberately over-denies: `echo "git commit --amend"` and
# `rm /tmp/x && cat <plan>` are refused even though no refusal-worthy command
# actually runs. Write verbs are destination-aware only for the copy/link
# family (cp/install/ln/dd): reading *from* a plan stays allowed — `mv` is an
# operand writer, so `mv <plan> <anywhere>` is refused.
#
# One PROTECTED list (`PROTECTED_PATHS`) feeds every arm — the plan-write arm,
# the override arm and the Edit/Write/MultiEdit path rule — and every entry is
# evaluated (no early `break`). Both Bash arms share one token pass: a symlink
# token is resolved exactly once, and every symlink token in the command is
# resolved in a single `realpath` call, so 200 symlink tokens cost one
# `realpath`, not 200.
#
# The operator lifts the guard by setting `ORCHESTRATOR_GUARD=off` in the
# session; the flag is read from the hook process's own environment, which a
# `VAR=x cmd` prefix in a Bash payload (a separate child process) cannot reach.
#
# Normalisation: `\`+newline → space; tab, newline, `;`, `&&`, `||`, `|`, `(`,
# `)`, `{`, `}`, `&` → boundaries; `>`, `>>`, `>|` stay as redirect tokens;
# matching (and stray) quotes — `"`, `'`, backtick — are stripped to NOTHING (so
# `git p''ush` stays `git push`, one word) while a `git` or a write verb inside
# a quoted string or `` `…` `` is still seen as a token. Paths are compared
# lexically (collapse `~`, `.`, `..`, `//`; join a relative token onto the
# cwd/`cd` base) with `realpath` paid only once for the project and plans dirs
# and once per symlink token, so a symlink INTO the plans dir or a `..`/`./`
# segment cannot dodge the plan rules. A symlink FROM the plans dir outward is
# judged by its target — where a write actually lands — so it does not trip the
# heading rule, but a write through it cannot alter a real regular-file plan
# either (MINOR 8: stated here, not silently assumed). Known gap, carried from
# main and out of scope: a removal THROUGH a symlink that points INTO the plans
# directory (`rm plans-link/x.md`, where `plans-link` → `docs/superpowers/
# plans`) allows here and on main alike — the guard judges a symlink FROM the
# plans dir outward (the write's real target), not a link whose name sits
# outside while its target is inside (a CR2 follow-up if the operator wants it).
#
# Deny-only and never raising: it always exits 0, only ever *adding* a deny
# decision on stdout. A guard FAULT fails closed, never open, by construction:
# no function this file defines is ever called inside a subshell — not in a
# `$(…)` or backtick command substitution, a `<( … )`/`>( … )` process
# substitution, a pipe stage, or a `( … )` subshell list. Every guard function
# returns its result through the one global `_ret` (copied to a local at once
# by the caller, with never a second guard call between the call and the read),
# so every function runs in the main shell and a fault that aborts the shell
# under `set -u` reaches the EXIT trap, which denies. Only external commands
# (`git`, `realpath`, `readlink`, `cat`, `ps`, …) may stand inside a
# substitution, and their failure is missing evidence, handled at the site. The
# trap is installed on the entry path only (never at source time), so a
# sourcing test keeps its own traps. Either way the guard still exits 0 and
# prints one line on stderr, so a broken guard can never lock the session by
# allowing what it must deny.
#
# Bash, not python3, on purpose: the bare host has no python3, and
# `nix develop -c python3` costs ~5 s of flake evaluation per call, far over
# the <300 ms per-edit budget (plan 2026-09-05-seat-routing.md OG1). The token
# scans use bash builtins only (parameter expansion, `read -a`, `case`), never
# a grep/sed/awk pipeline over the command — globbing stays off because `read`
# never expands a `*` in a command against the filesystem.
set -u

# deny REASON — emit the Claude Code PreToolUse deny decision on stdout.
deny() {
  _guard_decided=1
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
}

# warn MSG — the only stderr this guard ever writes (one line).
warn() { printf 'orchestrator-guard: %s\n' "$1" >&2; }

# Fail-closed fault handling (CR2r3): a fault that would otherwise abort the
# shell (fatal under `set -u`) or silently drop a verdict is denied, never
# allowed. `_guard_active` is set only once `main` is actually running, so a
# sourced bats test that never calls `main` is never misclassified; the EXIT
# trap then only fires when a real run faults (non-zero status) with no decision
# already written. The trap is installed on the entry path only (see the
# BASH_SOURCE gate at the foot of this file), never at source time, so a
# sourcing bats test keeps its own EXIT trap.
_guard_active=0
_guard_decided=0
_guard_trap() {
  local st=$?
  [ "$_guard_active" -eq 1 ] || return 0
  [ "$st" -eq 0 ] && return 0
  [ "$_guard_decided" -eq 1 ] && return 0
  warn "guard fault: the guard exited with status $st"
  deny "guard fault: the guard exited with status $st"
  exit 0
}

# _ret — the one global every guard function returns its result through. A
# function writes its result to `_ret` and returns; the caller copies it to a
# local at once (never calling another guard function in between), so no guard
# function is ever wrapped in a subshell (substitution, process substitution,
# pipe or list) and a fault always fires in the main shell, where the EXIT trap
# denies.
_ret=''

# The six absolute prefixes from hook-guard.py PROTECTED_ABSOLUTE (kept
# identical to the wrapper and lane-submit via tests/lane/test_forbidden_lists_agree.py).
PROTECTED=(
  /run/baskets
  /var/lib/baskets
  /var/lib/helm
  /var/lib/egress-broker
  /var/lib/lanes
  /var/lib/secrets
)

# PROTECTED_PATHS — the guard's own protected paths (CR2b: one mechanism for
# every protected path). Each entry is "relative-path|kind", relative to
# CLAUDE_PROJECT_DIR. `dir` — the directory names every member for the delete
# family (docs/superpowers/plans); `file` — the path's parent directory and
# every ancestor up to `/` name it for the delete family (`.claude/
# ritual-override`, whose parent `.claude` is the directory a `rm -rf .claude`
# or `git clean -fd` destroys).
PROTECTED_PATHS=(
  'docs/superpowers/plans|dir'
  '.claude/ritual-override|file'
  # OG3 (SD8's gate, MINOR-11): the guard the house runs is read from the
  # mutable checkout, so it must name itself — a seat must not be able to edit
  # the rules it obeys.
  'tools/orchestrator-guard.sh|file'
)

# The typed-heading line, mirroring tasks.py HEADING_RE (separator em-dash or
# hyphen — the two chars of tasks.py's `[—-]` class).
HEADING_ERE='^### [A-Za-z][A-Za-z0-9-]* \((code|docs), (XS|S|M|L)\) (—|-) .+$'
HEADING_REASON='typed task headings are append-only — withdraw a task with a status row in docs/ledger/task-status.toml, not by editing docs/superpowers/plans/…'

# The operator-only escape hatch (spec §3.4): .claude/ritual-override belongs to
# the operator. No agent may write, overwrite or remove it — only the operator
# touches it and removes it when done (CR2). The Stop/SessionStart hooks read it
# (that stays allowed); the guard refuses every *write* to it.
OVERRIDE_REASON="the ritual override is the operator's; ask for it"

# OG3 (SD8's gate, MINOR-11): the house guard's own file. Every `file` entry's
# deny reason is its own — a refusal of the guard names the guard, not the ritual
# override (see `file_reason`). Reading the file (cat, bash it, grep it) stays
# allowed; only writing or removing it is refused.
GUARD_REASON="orchestrator-guard.sh is the operator's; ask for it"

# SELF_CANON — the guard's own canonical path, the one file it protects wherever
# it executes from (OG3b item 1). Declared empty here; resolved inside main,
# after the fail-closed EXIT trap is installed (OG3r item 4) — never at source
# time, never inside a rule function, never in a subshell — with the single
# external `realpath` the guard already uses. That is independent of
# CLAUDE_PROJECT_DIR: a seat whose project is the WORKSPACE still cannot write
# the live checkout's guard by absolute path. A copy of the file elsewhere (a
# scratch clone) is a different file and stays untouched. A failed `realpath` is
# a guard fault that reaches the trap's deny, never an empty file_dirs entry.
SELF_CANON=''

# file_reason REL — the deny reason a `file` entry with relative path REL prints
# (the default is the ritual-override reason for any future file entry).
file_reason() {
  case "$1" in
    '.claude/ritual-override') _ret=$OVERRIDE_REASON ;;
    'tools/orchestrator-guard.sh') _ret=$GUARD_REASON ;;
    *) _ret=$OVERRIDE_REASON ;;
  esac
}

# A real newline, for the command-position anchors of the sudo/nixos-rebuild
# rules below. Those two count as commands after a shell separator — start,
# `;`, `&`, `|`, `(`, `)`, or a newline — but not after a plain space, so
# `grep sudo docs/brief.md` and `echo 'never sudo here'` do not fire
# (hook-guard.py's exact [;&|\n()] class).
NL=$'\n'

# --- command normalisation (the "no command position" contract) ---
# A command is folded to a flat token stream, then *every* token is scanned —
# no notion of where a command "starts" survives, so a launcher or a newline
# can never hide a git invocation or a write verb.

# normalise_command COMMAND — fold `\`+newline line continuations, tabs and
# newlines to spaces, and strip quote characters (`"`, `'`, backtick) so a
# quoted `git`/verb inside `bash -c "…"` or `` `…` `` becomes a bare token.
# Quotes strip to NOTHING, not to a space (MINOR 17): stripping to a space
# would split `git p''ush` into `git p ush` and hide the `push`. Returns the
# text the pad step then splits into tokens.
normalise_command() {
  local c=$1 dq sq bt
  dq='"'            # double quote
  sq="'"            # single quote
  bt='`'            # backtick
  c=${c//\\$'\n'/ } # backslash-newline line continuation → space
  c=${c//$'\t'/ }   # tab → space
  c=${c//$'\n'/ }   # newline → space (a boundary, not a position)
  c=${c//"$dq"/}    # " → nothing
  c=${c//"$sq"/}    # ' → nothing
  c=${c//"$bt"/}    # ` → nothing
  _ret=$c
}

# pad_operators STRING — space-pad the shell separators so they split into
# their own tokens: `;`, `|`, `(`, `)`, `{`, `}`, `&` each become one token, and
# `&&`/`||` collapse to a single `&`/`|` token; `>`/`>>` become one `>` redirect
# token. The separators are *not* command positions — the scans below ignore
# them (they are neither `git` nor a verb) except as the end of one copy/link
# invocation's argument list.
pad_operators() {
  local s=$1
  s=${s//'&&'/' & '} # && → a single & boundary (before a bare &)
  s=${s//'&'/' & '}  # & → token
  s=${s//'||'/' | '} # || → a single | boundary (before a bare |)
  s=${s//'>|'/'>'}   # >| → one redirect token (clobber; MINOR 19), before bare |
  s=${s//'|'/' | '}  # | → token
  s=${s//'>>'/'>'}   # >> → > (append is a write; one redirect token)
  s=${s//'>'/' > '}  # > → token
  s=${s//';'/' ; '}  # ; → token
  s=${s//'('/' ( '}  # ( → token
  s=${s//')'/' ) '}  # ) → token
  s=${s//'{'/' { '}  # { → token
  s=${s//'}'/' } '}  # } → token
  _ret=$s
}

# tokenise STRING OUTNAME — split STRING on spaces into the array OUTNAME (a
# nameref to the caller's array). `read -a` (not `for w in $s`) so a glob
# metacharacter in a command is taken literally, never expanded against the
# filesystem. normalise_command turned tabs and newlines into spaces, so space
# is the only separator left; `-d ''` reads the whole here-string and the
# here-string's own trailing newline is trimmed off the last token.
tokenise() {
  local s=$1
  local -n out=$2
  local n
  IFS=' ' read -r -d '' -a out <<<"$s"
  n=${#out[@]}
  if [ "$n" -gt 0 ]; then
    out[n - 1]=${out[n - 1]%$'\n'}
  fi
}

# tokenise_ctx RAW TOKS QUOTED NLSEP — tokenise RAW (the *raw* command, before
# normalise/pad) into the same flat token stream tokenise() produces from the
# normalise+pad pipeline, plus two parallel arrays: QUOTED[i] is 1 when token i
# was written inside a quoted string (single, double, or backtick), and
# NLSEP[i] is 1 when a newline separated token i from the token before it (a
# clause boundary). Quote characters are deleted exactly as normalise_command
# deletes them; operators and whitespace split exactly as
# normalise_command+pad_operators+tokenise do, so the token TEXT is identical to
# the old pipeline — EXCEPT that an operator (`;`, `&`, `|`, `>`, `(`, `)`, `{`,
# `}`) or a newline *inside a quoted string* is an ordinary character of that one
# token (CR2r2 item 1), never a clause boundary. CR2rb: the quoted flag is what
# bounds the `git commit -m` prose exemption to the single quoted message
# argument.
#
# The bytes are split once with `fold -w1` into an indexed array (embedded
# newlines are re-encoded as a sentinel first, since `fold` drops them), then
# scanned once — one O(n) pass plus one `fold` fork, no per-token subshell and no
# second scan, so 200 tokens stay far under the timing budget (CR2r2 item 4,
# reversing the CR2rb `${s:i:1}` per-character re-scan).
#
# _ctx_emit (and the _ctx_* scratch globals it fills) are hoisted out of
# tokenise_ctx: a bash function defined *inside* a function still leaks into the
# shell's function namespace and would be silently shadowed by any later
# definition (CR2r2 item 5).
_ctx_toks=()
_ctx_quoted=()
_ctx_nlsep=()
_ctx_buf=''
_ctx_bufq=0
_ctx_nlpend=0
_ctx_lastop=0
# _ctx_exp — 1 while a ${NAME} parameter expansion is open (a `{` immediately
# preceded by `$` opened it; the matching `}` closes it). Only ever set inside
# the tokenise_ctx loop, reset at entry, like the other _ctx_* scratch globals.
_ctx_exp=0

_ctx_emit() {
  [ -n "$_ctx_buf" ] || return
  _ctx_toks+=("$_ctx_buf")
  _ctx_quoted+=("$_ctx_bufq")
  _ctx_nlsep+=("$_ctx_nlpend")
  _ctx_buf=''
  _ctx_bufq=0
  _ctx_nlpend=0
  _ctx_lastop=0
}

tokenise_ctx() {
  local s=$1
  local -n m_toks=$2 m_quoted=$3 m_nlsep=$4
  local c inq='' bs=$'\\'
  local -a chars=()
  local n i
  m_toks=()
  m_quoted=()
  m_nlsep=()
  _ctx_toks=()
  _ctx_quoted=()
  _ctx_nlsep=()
  _ctx_buf=''
  _ctx_bufq=0
  _ctx_nlpend=0
  _ctx_lastop=0
  _ctx_exp=0
  # One `fold -w1` fork yields the byte stream as an indexed array (O(1) access
  # for the operator/newline lookahead, no per-token subshell). `fold` treats a
  # newline as a record separator, so first re-encode every newline as the SOH
  # sentinel (which `fold` emits as an ordinary one-column byte) and match the
  # sentinel below where the newline arm used to live.
  s=${s//$'\n'/$'\x01'}
  mapfile -t chars < <(printf '%s' "$s" | fold -w1)
  n=${#chars[@]}
  for ((i = 0; i < n; i++)); do
    c=${chars[i]}
    case "$c" in
      '{' | '}' | ';' | '(' | ')' | '&' | '|' | '>')
        # OG3r: a `{` immediately preceded by `$` opens a parameter expansion
        # ${NAME} that runs to the matching `}` — it stays inside its one word,
        # so lex_norm's ${HOME}/ arm is reachable. A bare `{a,b}` brace
        # expansion (no `$` before the `{`) is unchanged: it still splits.
        if [ -z "$inq" ]; then
          if [ "$c" = '{' ] && [ "${_ctx_buf: -1}" = '$' ]; then
            _ctx_exp=1
            _ctx_buf+='{'
            continue
          fi
          if [ "$_ctx_exp" -eq 1 ]; then
            _ctx_buf+="$c"
            [ "$c" = '}' ] && _ctx_exp=0
            continue
          fi
        fi
        if [ -n "$inq" ]; then
          _ctx_buf+="$c"
          _ctx_bufq=1
        else
          _ctx_emit
          case "$c" in
            '&') [ "${chars[i + 1]:-}" = '&' ] && i=$((i + 1)) ;;
            '|') [ "${chars[i + 1]:-}" = '|' ] && i=$((i + 1)) ;;
            '>') case "${chars[i + 1]:-}" in '|' | '>') i=$((i + 1)) ;; esac ;;
          esac
          _ctx_toks+=("$c")
          _ctx_quoted+=(0)
          _ctx_nlsep+=(0)
          _ctx_lastop=1
        fi
        ;;
      \')
        if [ "$inq" = "'" ]; then
          inq=''
        elif [ -z "$inq" ]; then
          inq="'"
        fi
        ;;
      '"')
        if [ "$inq" = '"' ]; then
          inq=''
        elif [ -z "$inq" ]; then
          inq='"'
        fi
        ;;
      '`')
        if [ "$inq" = '`' ]; then
          inq=''
        elif [ -z "$inq" ]; then
          inq='`'
        fi
        ;;
      "$bs")
        if [ $((i + 1)) -lt "$n" ] && [ "${chars[i + 1]}" = $'\x01' ]; then
          _ctx_emit
          i=$((i + 1))
        else
          _ctx_buf+="$bs"
          [ -n "$inq" ] && _ctx_bufq=1
        fi
        ;;
      $'\x01')
        if [ -n "$inq" ]; then
          _ctx_buf+=$'\n'
          _ctx_bufq=1
        else
          _ctx_emit
          _ctx_nlpend=1
        fi
        ;;
      $'\t' | ' ')
        _ctx_emit
        ;;
      *)
        _ctx_buf+="$c"
        [ -n "$inq" ] && _ctx_bufq=1
        ;;
    esac
  done
  _ctx_emit
  # A trailing operator leaves a trailing space in pad_operators, which the old
  # tokenise() turns into a final empty token; reproduce it so the canonical
  # stream is byte-identical (that empty token names the project root, an
  # ancestor of the protected dirs).
  if [ "$_ctx_lastop" -eq 1 ]; then
    _ctx_toks+=('')
    _ctx_quoted+=(0)
    _ctx_nlsep+=(0)
  fi
  m_toks+=("${_ctx_toks[@]}")
  m_quoted+=("${_ctx_quoted[@]}")
  m_nlsep+=("${_ctx_nlsep[@]}")
}

# git_verdict COMMAND — the deny reason if COMMAND runs a history/rewrite git
# subcommand, else empty. Scans EVERY token: any token whose basename is `git`
# (a bare `git`, a `\git`, or a path like `/run/current-system/sw/bin/git`)
# marks a git invocation wherever it sits, then walks forward to its subcommand
# (the first later token that does not start with `-` and is not the value of a
# value-taking long option in space form). Denies `commit` (with a later
# `--amend`), `push`, `rebase`, and `reset` (with a later `--hard`) — each
# searched over the whole remaining token list, deny-only.
git_verdict() {
  local command=$1
  local norm base
  _ret=''
  normalise_command "$command"
  norm=$_ret
  pad_operators "$norm"
  norm=$_ret
  local -a toks
  tokenise "$norm" toks
  local n=${#toks[@]} i t j sub k
  for ((i = 0; i < n; i++)); do
    t=${toks[i]}
    base=${t##*/}   # basename: strip any directory prefix
    base=${base#\\} # strip one leading backslash (\git)
    [ "$base" = "git" ] || continue
    sub=""
    j=$((i + 1))
    while [ "$j" -lt "$n" ]; do
      case "${toks[j]}" in
        # value-taking long options in space form: skip the option and its
        # value; their `=` form (-c=x, --work-tree=.) is self-contained and
        # falls into -*) below.
        -c | -C | --git-dir | --work-tree | --exec-path | --namespace | --config-env | --super-prefix)
          j=$((j + 2))
          ;;
        -*) j=$((j + 1)) ;;
        *)
          sub=${toks[j]}
          break
          ;;
      esac
    done
    case "$sub" in
      commit)
        for ((k = j + 1; k < n; k++)); do
          [ "${toks[k]}" = "--amend" ] && {
            _ret='git commit --amend is refused (history rules of the house)'
            return
          }
        done
        ;;
      push | rebase)
        _ret="git $sub is refused (history rules of the house)"
        return
        ;;
      reset)
        for ((k = j + 1; k < n; k++)); do
          [ "${toks[k]}" = "--hard" ] && {
            _ret='git reset --hard is refused (history rules of the house)'
            return
          }
        done
        ;;
    esac
  done
  _ret=''
}

# json_string JSON KEY — the raw (still-escaped) string value of the one
# `"KEY"` field. The capture stops at the first *unescaped* quote, so a value
# containing \" or \\ is preserved whole. Fields this targets (command,
# content, file_path, old_string, new_string) each appear once as a key.
json_string() {
  local json=$1 key=$2
  _ret=$(printf '%s\n' "$json" |
    sed -n 's/.*"'"$key"'"[[:space:]]*:[[:space:]]*"\(\(\\.\|[^"\\]\)*\)".*/\1/p')
}

# json_unescape STR — undo the JSON escapes a plan body or command carries
# (\\ then \" then \n\t\r; a backslash is parked first so the order is safe).
json_unescape() {
  _ret=$(printf '%s\n' "$1" |
    sed -e 's/\\\\/__BS__/g' -e 's/\\"/"/g' -e 's/\\n/\n/g' -e 's/\\t/\t/g' \
      -e 's/\\r/\r/g' -e 's/__BS__/\\/g')
}

# headings TEXT — the sorted, unique typed-heading lines in TEXT, via _ret.
headings() {
  _ret=$(printf '%s\n' "$1" | grep -E "$HEADING_ERE" | sort -u)
}

# apply_edit BEFORE OLD NEW — BEFORE with the first literal occurrence of OLD
# replaced by NEW. `"$old"` quoted inside a glob is literal, so a title that
# contains *, ?, or [ is matched as text, never as a pattern.
apply_edit() {
  local before=$1 old=$2 new=$3
  if [ -z "$old" ]; then
    _ret=$before
    return
  fi
  if [[ "$before" == *"$old"* ]]; then
    _ret="${before%%"$old"*}$new${before#*"$old"}"
  else
    _ret=$before
  fi
}

# bash_verdict COMMAND PROJECT_DIR CWD — the deny reason COMMAND is refused, or
# empty to allow. CWD (may be empty) is the payload's cwd, the initial base a
# relative path rebases onto.
bash_verdict() {
  local command=$1 project_dir=$2 cwd=$3 prefix re reason
  _ret=''
  if [[ $command =~ (^|[;&|()$NL])[[:space:]]*sudo([[:space:]]|$) ]]; then
    _ret='sudo is refused (an operator action)'
    return
  fi
  if [[ $command =~ (^|[;&|()$NL])[[:space:]]*nixos-rebuild([[:space:]]|$) ]]; then
    _ret='nixos-rebuild is refused (an operator action)'
    return
  fi
  if [[ $command =~ systemctl([[:space:]]+--?[A-Za-z0-9=-]+)*[[:space:]]+(start|stop|restart|reload|enable|disable)([[:space:]]|$) ]]; then
    _ret="systemctl ${BASH_REMATCH[2]} is refused (an operator action)"
    return
  fi
  git_verdict "$command"
  reason=$_ret
  [ -n "$reason" ] && {
    _ret=$reason
    return
  }
  write_verdict "$command" "$project_dir" "$cwd"
  reason=$_ret
  [ -n "$reason" ] && {
    _ret=$reason
    return
  }
  for prefix in "${PROTECTED[@]}"; do
    # a write under PREFIX: a redirect (`>`, `>>`, `2>`) with any run of
    # spaces; `tee` (bare or with flags) writing there; or cp/mv/install whose
    # *destination* (the final path token) is there — reading or moving *from*
    # a protected path is allowed (MINOR 9).
    re=">>?[[:space:]]*${prefix}([/[:space:]]|$)"
    if [[ $command =~ $re ]]; then
      _ret="refusing to write under protected path ${prefix} (an operator action)"
      return
    fi
    re="(^|[^[:alnum:]_-])tee([[:space:]]+--?[A-Za-z0-9=-]+)*[[:space:]]+${prefix}([/[:space:]]|$)"
    if [[ $command =~ $re ]]; then
      _ret="refusing to write under protected path ${prefix} (an operator action)"
      return
    fi
    re="(^|[^[:alnum:]_-])(cp|mv|install)([[:space:]]+[^[:space:];|&]+)*[[:space:]]+${prefix}([^[:space:];|&]*)$"
    if [[ $command =~ $re ]]; then
      _ret="refusing to write under protected path ${prefix} (an operator action)"
      return
    fi
  done
}

# Scratch globals for the lexical normalisers. Rule 5: the normaliser must not
# fork, so it writes its result into a global instead of a subshell.
_lex=''
_canon=''

# lex_norm RAW BASE — lexically normalise the path RAW (a bare token: no spaces,
# no shell quoting) against the absolute directory BASE, with no subprocess: a
# leading `~` becomes $HOME, a relative RAW joins onto BASE, and `.`, `..`,
# `//` and a trailing slash collapse. The result is the absolute path (or `/`)
# left in `_lex`. This is rule 5's lexical normalisation — the plan rules pay
# `realpath` only for the project/plans dirs once per command and once per
# symlink token.
lex_norm() {
  local raw=$1 base=$2 p comp
  p=${raw/#\~/"${HOME:-}"}
  # OG3b item 2: expand a leading $HOME/ or ${HOME}/ to the guard's $HOME, exactly
  # as a leading ~ is (only widens denials; a token like $HOMEX/ stays literal).
  case "$p" in
    \$HOME/*) p=${HOME:-}${p#\$HOME} ;;
    \$\{HOME\}/*) p=${HOME:-}${p#\$\{HOME\}} ;;
  esac
  case "$p" in
    /*) ;;
    *) p="$base/$p" ;;
  esac
  local -a segs=() acc=()
  IFS='/' read -r -a segs <<<"$p"
  for comp in "${segs[@]}"; do
    case "$comp" in
      '' | '.') : ;;
      '..') [ "${#acc[@]}" -gt 0 ] && unset 'acc[-1]' ;;
      *) acc+=("$comp") ;;
    esac
  done
  if [ "${#acc[@]}" -eq 0 ]; then
    _lex='/'
    return
  fi
  local k s='/'${acc[0]}
  for ((k = 1; k < ${#acc[@]}; k++)); do
    s+='/'${acc[k]}
  done
  _lex=$s
}

# canon_path RAW BASE — the canonical absolute path RAW denotes: lex_norm, then a
# single `realpath` only when the lexical form is a symlink (`[ -L ]` is a
# syscall, not a fork). The result lands in `_canon`.
canon_path() {
  local p
  lex_norm "$1" "$2"
  p=$_lex
  if [ -L "$p" ]; then
    _canon=$(realpath -m -- "$p")
  else
    _canon=$p
  fi
}

# is_plan_file_canon PATH PLANS_CANON — PATH (canonical) is a *.md directly
# under the plans dir PLANS_CANON (a pure string check; no subprocess).
is_plan_file_canon() {
  [ "${1%/*}" = "$2" ] && [[ "${1##*/}" == *.md ]]
}

# is_protected_dir_or_ancestor PATH DIR PROJECT_CANON — PATH (canonical) names
# the protected directory DIR or an ancestor of it that still counts as "ours"
# (CR2b: one mechanism for every protected path). DIR is the directory whose
# deletion destroys the protected path — the plans dir itself for a `dir` entry,
# and the path's parent (`.claude`) for a `file` entry. Ancestors down to (and
# including) the project dir and the root `/` count; a parent *above* the project
# dir (`/tmp`, `/home`) is not ours — `rm /tmp/plans-not-ours/x.md`,
# `rm /tmp/other/.claude/ritual-override`, and `cd /tmp && rm x.md` stay allowed
# even when the project lives under there.
is_protected_dir_or_ancestor() {
  local p=$1 dir=$2 project=$3
  [ "$p" = "/" ] && return 0
  case "$dir" in
    "$p" | "$p"/*) : ;;
    *) return 1 ;;
  esac
  case "$p" in
    "$project" | "$project"/*) return 0 ;;
    *) return 1 ;;
  esac
}

# resolve_path RAW PROJECT_DIR — the canonical absolute path RAW denotes, for
# the Edit/Write tools: canon_path with PROJECT_DIR as the base.
resolve_path() {
  canon_path "$1" "$2"
  _ret=$_canon
}

# is_plan_file FILE_PATH PROJECT_DIR — FILE_PATH (already canonical) is a *.md
# directly under any `dir` entry of the PROTECTED list (docs/superpowers/plans).
# Every `dir` entry is evaluated (CR2rb item 5: no early return on the first).
is_plan_file() {
  local file=$1 project_dir=$2 project_canon e rel kind
  project_canon=$(realpath -m -- "$project_dir")
  for e in "${PROTECTED_PATHS[@]}"; do
    rel=${e%%|*}
    kind=${e##*|}
    [ "$kind" = "dir" ] || continue
    lex_norm "$rel" "$project_canon"
    is_plan_file_canon "$file" "$_lex" && return 0
  done
  return 1
}

# write_verdict COMMAND PROJECT_DIR CWD — the deny reason if COMMAND writes or
# removes a protected path (rule 2: a plan file under docs/superpowers/plans;
# CR2/CR2r: .claude/ritual-override, spec §3.4), else empty. One function, one
# PROTECTED list, one token pass: the plan-write arm and the override arm share
# the single per-token canonicalisation (rule 5 / CR2r item 6), so a symlink
# token pays `realpath` once, not twice, and both arms read the same facts.
#
# There is no command position: every token is scanned for a write-capable verb,
# and any such verb in a command that ALSO names a protected path refuses. The
# operand writers (the delete family) deny on any protected path present
# (deny-only over-denial, e.g. `rm /tmp/x && cat <plan>`), while the copy/link
# family (cp, install, ln, dd) denies only when the protected path is the
# *destination*, so reading from a plan or the override stays allowed. Relative
# tokens are judged against the payload cwd (when present) and every
# `cd`/`pushd` base. The override's delete family also covers the directory and
# every ancestor of `.claude` (so `rm -rf .claude` denies), plus (CR2r) `git
# stash -u`/`-a`, `tar`/`unzip`/`cpio` extracting into a protected dir,
# `chmod`/`chown`/`chattr` on the file, `truncate`, and `xargs` carrying a
# delete verb; and a glob token under `.claude/` (`rm -rf .claude/*`) names the
# file via the raw-text fallback.
write_verdict() {
  local command=$1 project_dir=$2 cwd=$3
  local raw i j t dq sq dqd sqd
  local plan_reason
  local project_canon e rel kind
  local -a toks quoted nlsep clause_of base_of
  local -a file_canons=() file_dirs=() file_reasons=() plan_canons=()
  local -a bases
  local -a c_inplace c_find_delete c_xargs c_extract c_cpio_extract c_clean_force c_stash_untracked
  local -a skip=()
  local plan_file_seen plan_dir_seen ovr_seen ovr_dir_seen ovr_desc_seen
  local ovr_reason ovr_reason_chosen
  local orig tv kk is_glob sub dest of_val
  local m s r saw_dd path_after_dd has_pathspec
  local nb idx bi k c cid maxcid curb base has_dest

  raw=$command
  tokenise_ctx "$raw" toks quoted nlsep
  local n=${#toks[@]}

  plan_reason='plan files change only through the Edit and Write tools (append-only headings) — see docs/runbooks/session.md'
  # OG3: every `file` entry carries its own deny reason; `ovr_reason` is the
  # reason of the entry the pending facts matched, defaulting to the ritual
  # override (so the bare/pathless git denials and any future file entry keep
  # the current wording until a site proves otherwise).
  ovr_reason="$OVERRIDE_REASON"
  ovr_reason_chosen=0

  # One-time canonicalisations. The PROTECTED list feeds BOTH arms here and the
  # Edit/Write/MultiEdit arm in main — no hard-coded path anywhere, no early
  # `break`: every entry is evaluated (a `dir` entry names a protected directory,
  # a `file` entry a protected file whose parent dir and ancestors name it for
  # the delete family).
  project_canon=$(realpath -m -- "$project_dir")
  for e in "${PROTECTED_PATHS[@]}"; do
    rel=${e%%|*}
    kind=${e##*|}
    lex_norm "$rel" "$project_canon"
    case "$kind" in
      file)
        file_canons+=("$_lex")
        file_dirs+=("${_lex%/*}")
        file_reason "$rel"
        file_reasons+=("$_ret")
        ;;
      dir) plan_canons+=("$_lex") ;;
    esac
  done
  # OG3b item 1: SELF_CANON joins the file facts as one more `file` entry, so the
  # token-==-file comparison (ovr_seen) and the copy/link/redirect destination
  # checks all name the guard wherever it executes from — independent of
  # CLAUDE_PROJECT_DIR. Its "parent dir" is the checkout's tools/ dir, which
  # is_protected_dir_or_ancestor already scopes to the project, so this adds no
  # ancestor denial beyond the project (and none at all when the project is the
  # workspace). A basename-only comparison is the wrong shape exactly because it
  # would also refuse a scratch clone's own differently-sited copy. OG3r item 4:
  # an empty SELF_CANON (a direct call that skipped main, or a realpath failure
  # that reached here) adds NOTHING — its empty parent dir would otherwise make
  # the descendant/glob pattern `/*` match every absolute path.
  if [ -n "$SELF_CANON" ]; then
    file_canons+=("$SELF_CANON")
    file_dirs+=("${SELF_CANON%/*}")
    file_reasons+=("$GUARD_REASON")
  fi

  # Bases for relative rebasing (the payload cwd, plus every cd/pushd arg), and
  # the base in effect at each token index (for the extract-into-cwd rule).
  bases=("${cwd:-$project_canon}")
  curb=0
  for ((i = 0; i < n; i++)); do
    base_of[i]=$curb
    case "${toks[i]}" in
      cd | pushd)
        if [ $((i + 1)) -lt "$n" ]; then
          lex_norm "${toks[i + 1]}" "${bases[curb]}"
          bases+=("$_lex")
          curb=$((curb + 1))
        fi
        ;;
    esac
  done

  # Clauses are split on `;`, `&&`/`&`, `||`/`|` and an unquoted newline BEFORE
  # verbs and flags are attributed (CR2rb item 4), so a flag in one clause never
  # arms a verb in another. Facts (a protected path named anywhere) stay
  # whole-command — the accepted deny-only over-denial.
  cid=0
  maxcid=0
  for ((i = 0; i < n; i++)); do
    if [ "$i" -gt 0 ]; then
      case "${toks[i - 1]}" in
        ';' | '&' | '|') cid=$((cid + 1)) ;;
      esac
      [ "${nlsep[i]}" -eq 1 ] && cid=$((cid + 1))
    fi
    clause_of[i]=$cid
    [ "$cid" -gt "$maxcid" ] && maxcid=$cid
  done
  for ((c = 0; c <= maxcid; c++)); do
    c_inplace[c]=0
    c_find_delete[c]=0
    c_xargs[c]=0
    c_extract[c]=0
    c_cpio_extract[c]=0
    c_clean_force[c]=0
    c_stash_untracked[c]=0
  done
  for ((i = 0; i < n; i++)); do
    c=${clause_of[i]}
    # Each flag class is scanned independently: one token arms several (e.g.
    # `-xdf` is tar-extract `-x` AND git-clean-force `f`; `-au` is stash `-a`
    # and `-u`; `--include-untracked` holds an `i`). The verb arm reads only its
    # own class, so the extra matches are harmless (CR2rb items 1–4).
    case "${toks[i]}" in -i* | --in-place*) c_inplace[c]=1 ;; esac
    case "${toks[i]}" in -delete | -exec) c_find_delete[c]=1 ;; esac
    case "${toks[i]}" in xargs) c_xargs[c]=1 ;; esac
    case "${toks[i]}" in -x* | --extract) c_extract[c]=1 ;; esac
    case "${toks[i]}" in -*i*) c_cpio_extract[c]=1 ;; esac
    case "${toks[i]}" in -*f*) c_clean_force[c]=1 ;; esac
    case "${toks[i]}" in -*u* | -*a*) c_stash_untracked[c]=1 ;; esac
  done

  # A `git commit -m "…"` message is prose: exempt the quoted argument after
  # EVERY `-m`/`--message` (not only the first — CR2r2 item 3), never the rest of
  # the clause and never a bare word. The glued forms `-am '…'`, `-m'…'` and
  # `--message='…'` are exempt too: a glued token carries its message inside the
  # one (quoted) token, while the space forms put the message in the following
  # run of quoted tokens. A newline inside the message stays inside that quoted
  # run (CR2r2 item 1), so `git commit -m 'x'` + newline + `rm -rf .claude` still
  # scans the `rm`.
  for ((i = 0; i < n; i++)); do
    skip[i]=0
  done
  for ((i = 0; i < n; i++)); do
    [ "${toks[i]}" = "git" ] || continue
    sub=""
    j=$((i + 1))
    while [ "$j" -lt "$n" ]; do
      case "${toks[j]}" in
        -c | -C | --git-dir | --work-tree | --exec-path | --namespace | --config-env | --super-prefix) j=$((j + 2)) ;;
        -*) j=$((j + 1)) ;;
        *)
          sub=${toks[j]}
          break
          ;;
      esac
    done
    [ "$sub" = "commit" ] || continue
    m=$((j + 1))
    while [ "$m" -lt "$n" ]; do
      case "${toks[m]}" in
        -m | --message | -am)
          # space form: the message is the following run of quoted tokens
          s=$((m + 1))
          while [ "$s" -lt "$n" ] && [ "${quoted[s]}" -eq 1 ]; do
            skip[s]=1
            s=$((s + 1))
          done
          ;;
        --message=* | -m*)
          # glued form: the message begins inside this one (quoted) token and
          # runs on through the following quoted tokens, exactly like the space
          # form (a space still splits a quoted message into several tokens)
          if [ "${quoted[m]}" -eq 1 ]; then
            skip[m]=1
            s=$((m + 1))
            while [ "$s" -lt "$n" ] && [ "${quoted[s]}" -eq 1 ]; do
              skip[s]=1
              s=$((s + 1))
            done
          fi
          ;;
      esac
      m=$((m + 1))
    done
  done

  # --- ONE token pass computes both arms' facts ---
  # Canonicalise lexically first (no fork), collect the symlinks, then resolve
  # every symlink in a single `realpath` call: a 200-token command of symlinks
  # pays `realpath` once, not 200 times (rule 5 / CR2r item 6).
  nb=${#bases[@]}
  declare -A canon_result=()
  local -a pending=()
  for ((i = 0; i < n; i++)); do
    [ "${skip[i]}" -eq 0 ] || continue
    tv=${toks[i]}
    [[ "$tv" == of=* ]] && tv=${tv#of=}
    for ((bi = 0; bi < nb; bi++)); do
      idx="$i/$bi"
      lex_norm "$tv" "${bases[bi]}"
      canon_result[$idx]=$_lex
      [ -L "$_lex" ] && pending+=("$idx")
    done
  done
  if [ "${#pending[@]}" -gt 0 ]; then
    local -a rargs=() rres=()
    for idx in "${pending[@]}"; do
      rargs+=("${canon_result[$idx]}")
    done
    mapfile -t rres < <(realpath -m -- "${rargs[@]}" 2>/dev/null)
    for ((k = 0; k < ${#pending[@]}; k++)); do
      canon_result[${pending[k]}]=${rres[k]}
    done
  fi

  # Second pass: facts from the canonical paths (no fork — resolution is done).
  plan_file_seen=0
  plan_dir_seen=0
  ovr_seen=0
  ovr_dir_seen=0
  ovr_desc_seen=0
  for ((i = 0; i < n; i++)); do
    [ "${skip[i]}" -eq 0 ] || continue
    t=${toks[i]}
    case "$t" in
      *'*'* | *'?'* | *'['* | *'{'*) is_glob=1 ;;
      *) is_glob=0 ;;
    esac
    for ((bi = 0; bi < nb; bi++)); do
      idx="$i/$bi"
      orig=${canon_result[$idx]}
      for kk in "${!plan_canons[@]}"; do
        is_plan_file_canon "$orig" "${plan_canons[kk]}" && plan_file_seen=1
        is_protected_dir_or_ancestor "$orig" "${plan_canons[kk]}" "$project_canon" && plan_dir_seen=1
      done
      for kk in "${!file_canons[@]}"; do
        if [ "$orig" = "${file_canons[kk]}" ]; then
          ovr_seen=1
          if [ "$ovr_reason_chosen" -eq 0 ]; then
            ovr_reason=${file_reasons[kk]}
            ovr_reason_chosen=1
          fi
        fi
        if is_protected_dir_or_ancestor "$orig" "${file_dirs[kk]}" "$project_canon"; then
          ovr_dir_seen=1
          if [ "$ovr_reason_chosen" -eq 0 ]; then
            ovr_reason=${file_reasons[kk]}
            ovr_reason_chosen=1
          fi
        fi
        case "$orig" in
          "${file_dirs[kk]}"/*)
            ovr_desc_seen=1
            if [ "$ovr_reason_chosen" -eq 0 ]; then
              ovr_reason=${file_reasons[kk]}
              ovr_reason_chosen=1
            fi
            ;;
        esac
        # a glob token under the protected file's parent directory names the
        # file even though the canonical path keeps `*`/`?`/`[`/`{` literal
        # (raw-text fallback, CR2r item 2).
        if [ "$is_glob" -eq 1 ]; then
          case "$orig" in
            "${file_dirs[kk]}" | "${file_dirs[kk]}"/*)
              ovr_seen=1
              ovr_dir_seen=1
              if [ "$ovr_reason_chosen" -eq 0 ]; then
                ovr_reason=${file_reasons[kk]}
                ovr_reason_chosen=1
              fi
              ;;
          esac
        fi
      done
    done
  done
  # A plan path embedded in a python heredoc/-c literal survives only in the raw
  # text (token mangling splits it); derive the fallback from the PROTECTED list,
  # never from a hard-coded path (CR2rb item 5).
  if [ "$plan_file_seen" -eq 0 ]; then
    for e in "${PROTECTED_PATHS[@]}"; do
      rel=${e%%|*}
      kind=${e##*|}
      [ "$kind" = "dir" ] || continue
      case "$raw" in
        *"${rel}"/*)
          plan_file_seen=1
          break
          ;;
      esac
    done
  fi
  # The override (a `file` entry) and its parent dir likewise survive only in the
  # raw text when the CR2r2 quote fix buries them inside a quoted one-liner (e.g.
  # `python3 -c '…os.remove(".claude/ritual-override")…'` — the `;`/`(`/`)` no
  # longer split the path out into its own token). Match the *quoted* relative
  # spellings only — never a bare substring, so an absolute path to some other
  # `.claude` (e.g. `rm /tmp/other/.claude/ritual-override`) stays allowed.
  # Derived from PROTECTED_PATHS, never a hard-coded path.
  if [ "$ovr_seen" -eq 0 ] || [ "$ovr_dir_seen" -eq 0 ]; then
    for e in "${PROTECTED_PATHS[@]}"; do
      rel=${e%%|*}
      kind=${e##*|}
      [ "$kind" = "file" ] || continue
      dq="\"${rel}\""     # ".claude/ritual-override"
      sq="'${rel}'"       # '.claude/ritual-override'
      dqd="\"${rel%/*}\"" # ".claude"
      sqd="'${rel%/*}'"   # '.claude'
      if [ "$ovr_seen" -eq 0 ]; then
        case "$raw" in
          *"$dq"* | *"$sq"*)
            ovr_seen=1
            if [ "$ovr_reason_chosen" -eq 0 ]; then
              file_reason "$rel"
              ovr_reason=$_ret
              ovr_reason_chosen=1
            fi
            ;;
        esac
      fi
      if [ "$ovr_dir_seen" -eq 0 ]; then
        case "$raw" in
          *"$dqd"* | *"$sqd"*)
            ovr_dir_seen=1
            if [ "$ovr_reason_chosen" -eq 0 ]; then
              file_reason "$rel"
              ovr_reason=$_ret
              ovr_reason_chosen=1
            fi
            ;;
        esac
      fi
    done
  fi

  # No early allow: the verb loop runs for every command. The pathless git
  # cases (`git clean -f`, `git stash -u`, a bare `git checkout --`) deny with
  # no protected path named at all, so the loop cannot be gated on the facts
  # above. The loop itself is cheap — it only pays `canon_path` when a
  # cp/install/ln/dd destination or a `>` redirect is present.

  # The verb loop: the plan arm first (its reason wins for `rm -rf .`, which
  # names both a plan ancestor and the override), then the override arm.
  for ((i = 0; i < n; i++)); do
    [ "${skip[i]}" -eq 0 ] || continue
    t=${toks[i]}
    c=${clause_of[i]}
    case "$t" in
      # the delete family (also deletes a directory)
      rm | mv | rsync | shred | rmdir)
        if [ "$plan_file_seen" -eq 1 ] || [ "$plan_dir_seen" -eq 1 ]; then
          _ret=$plan_reason
          return
        fi
        if [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; then
          _ret=$ovr_reason
          return
        fi
        # xargs carrying a delete verb: the deletion targets it reads from stdin
        # are unknowable, so a `.claude` descendant names the override too.
        if [ "${c_xargs[c]}" -eq 1 ] && [ "$ovr_desc_seen" -eq 1 ]; then
          _ret=$ovr_reason
          return
        fi
        ;;
      # file-only writers
      tee | ed | unlink)
        if [ "$plan_file_seen" -eq 1 ]; then
          _ret=$plan_reason
          return
        fi
        if [ "$ovr_seen" -eq 1 ]; then
          _ret=$ovr_reason
          return
        fi
        ;;
      # truncate: file-only for the plan arm, delete family for the override arm.
      truncate)
        if [ "$plan_file_seen" -eq 1 ]; then
          _ret=$plan_reason
          return
        fi
        if [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; then
          _ret=$ovr_reason
          return
        fi
        if [ "${c_xargs[c]}" -eq 1 ] && [ "$ovr_desc_seen" -eq 1 ]; then
          _ret=$ovr_reason
          return
        fi
        ;;
      # touch names the file exactly; chmod/chown/chattr on it OR on its parent
      # directory (`.claude`, reachable via -R) deny (CR2rb item 5).
      touch)
        if [ "$ovr_seen" -eq 1 ]; then
          _ret=$ovr_reason
          return
        fi
        ;;
      chmod | chown | chattr)
        if [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; then
          _ret=$ovr_reason
          return
        fi
        ;;
      # in-place editors
      sed | perl)
        if [ "$plan_file_seen" -eq 1 ] && [ "${c_inplace[c]}" -eq 1 ]; then
          _ret=$plan_reason
          return
        fi
        if [ "$ovr_seen" -eq 1 ] && [ "${c_inplace[c]}" -eq 1 ]; then
          _ret=$ovr_reason
          return
        fi
        ;;
      # tar/unzip/cpio extracting into a protected directory. `tar` needs `-x`,
      # `cpio` needs `-i` (both cluster-read); `unzip` always extracts. When no
      # `-C`/`-d` destination is named, the extract lands in the cwd, so the
      # base in effect here is judged against the protected dirs (CR2rb item 3).
      tar | unzip | cpio)
        if [ "$t" = "tar" ] && [ "${c_extract[c]}" -eq 0 ]; then
          :
        elif [ "$t" = "cpio" ] && [ "${c_cpio_extract[c]}" -eq 0 ]; then
          :
        elif [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; then
          _ret=$ovr_reason
          return
        else
          has_dest=0
          for ((r = i + 1; r < n && clause_of[r] == c; r++)); do
            case "${toks[r]}" in
              -C | -C* | --directory*) [ "$t" = "tar" ] && has_dest=1 ;;
              -d | -d*) [ "$t" = "unzip" ] && has_dest=1 ;;
            esac
          done
          if [ "$has_dest" -eq 0 ]; then
            base=${bases[${base_of[i]}]}
            for kk in "${!file_dirs[@]}"; do
              if is_protected_dir_or_ancestor "$base" "${file_dirs[kk]}" "$project_canon"; then
                _ret=$ovr_reason
                return
              fi
            done
          fi
        fi
        ;;
      # copy/link family — deny only when the destination (the last path arg
      # before the next separator) is the protected path, so reading stays allowed.
      cp | install | ln)
        dest=""
        for ((j = i + 1; j < n; j++)); do
          case "${toks[j]}" in
            ';' | '&' | '|' | '(' | ')' | '{' | '}') break ;;
            -*) : ;;
            *) dest=${toks[j]} ;;
          esac
        done
        [ -n "$dest" ] || continue
        for b in "${bases[@]}"; do
          canon_path "$dest" "$b"
          for kk in "${!plan_canons[@]}"; do
            is_plan_file_canon "$_canon" "${plan_canons[kk]}" && {
              _ret=$plan_reason
              return
            }
          done
          for kk in "${!file_canons[@]}"; do
            [ "$_canon" = "${file_canons[kk]}" ] && {
              _ret=${file_reasons[kk]}
              return
            }
          done
        done
        ;;
      # dd writes to of=… — the plan arm checks the of= value directly, the
      # override arm's of= value was admitted into the token scan (seen).
      dd)
        of_val=""
        for ((j = i + 1; j < n; j++)); do
          case "${toks[j]}" in
            ';' | '&' | '|' | '(' | ')' | '{' | '}') break ;;
            of=*)
              of_val=${toks[j]#of=}
              break
              ;;
          esac
        done
        for b in "${bases[@]}"; do
          [ -n "$of_val" ] || break
          canon_path "$of_val" "$b"
          for kk in "${!plan_canons[@]}"; do
            is_plan_file_canon "$_canon" "${plan_canons[kk]}" && {
              _ret=$plan_reason
              return
            }
          done
        done
        if [ "$ovr_seen" -eq 1 ]; then
          _ret=$ovr_reason
          return
        fi
        ;;
      # git — plan checkout/restore/clean, and (override) clean/checkout/restore/
      # stash with the pathless over-denials narrowed (CR2r item 4).
      git)
        sub=""
        j=$((i + 1))
        while [ "$j" -lt "$n" ]; do
          case "${toks[j]}" in
            -c | -C | --git-dir | --work-tree | --exec-path | --namespace | --config-env | --super-prefix) j=$((j + 2)) ;;
            -*) j=$((j + 1)) ;;
            *)
              sub=${toks[j]}
              break
              ;;
          esac
        done
        case "$sub" in
          checkout | restore)
            if [ "$plan_file_seen" -eq 1 ]; then
              _ret=$plan_reason
              return
            fi
            if [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; then
              _ret=$ovr_reason
              return
            fi
            # a bare `--` (no path after it) means the whole worktree.
            r=$((j + 1))
            saw_dd=0
            path_after_dd=0
            while [ "$r" -lt "$n" ]; do
              case "${toks[r]}" in
                ';' | '&' | '|' | '(' | ')' | '{' | '}') break ;;
                '--') saw_dd=1 ;;
                *) [ "$saw_dd" -eq 1 ] && path_after_dd=1 ;;
              esac
              r=$((r + 1))
            done
            [ "$saw_dd" -eq 1 ] && [ "$path_after_dd" -eq 0 ] && {
              _ret=$ovr_reason
              return
            }
            ;;
          clean)
            if [ "$plan_file_seen" -eq 1 ] || [ "$plan_dir_seen" -eq 1 ]; then
              _ret=$plan_reason
              return
            fi
            # override: deny only with -f and no path or a protected path, so a
            # dry run (`git clean -n`) or a pathless non-force clean allows.
            if [ "${c_clean_force[c]}" -eq 1 ]; then
              r=$((j + 1))
              has_pathspec=0
              while [ "$r" -lt "$n" ]; do
                case "${toks[r]}" in
                  ';' | '&' | '|' | '(' | ')' | '{' | '}') break ;;
                  -*)
                    r=$((r + 1))
                    continue
                    ;;
                  *)
                    has_pathspec=1
                    break
                    ;;
                esac
              done
              if [ "$has_pathspec" -eq 0 ] || [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; then
                _ret=$ovr_reason
                return
              fi
            fi
            ;;
          stash)
            # `git stash -u`/`-a` stashes untracked files (the override is
            # untracked), so it joins the delete family; without the flag it
            # touches only tracked files and allows. Subcommand words (`push`,
            # `save`, `pop`, `apply`, `drop`, `list`, `show`, `branch`,
            # `create`, `store`) are never pathspecs (CR2rb item 2).
            if [ "${c_stash_untracked[c]}" -eq 1 ]; then
              r=$((j + 1))
              has_pathspec=0
              while [ "$r" -lt "$n" ]; do
                case "${toks[r]}" in
                  ';' | '&' | '|' | '(' | ')' | '{' | '}') break ;;
                  -*) r=$((r + 1)) ;;
                  push | save | pop | apply | drop | list | show | branch | create | store) r=$((r + 1)) ;;
                  *)
                    has_pathspec=1
                    break
                    ;;
                esac
              done
              if [ "$has_pathspec" -eq 0 ] || [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; then
                _ret=$ovr_reason
                return
              fi
            fi
            ;;
        esac
        ;;
      # find -delete/-exec is a delete-family write (read-only find allows).
      find)
        if [ "${c_find_delete[c]}" -eq 1 ] && { [ "$plan_file_seen" -eq 1 ] || [ "$plan_dir_seen" -eq 1 ]; }; then
          _ret=$plan_reason
          return
        fi
        if [ "${c_find_delete[c]}" -eq 1 ] && { [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; }; then
          _ret=$ovr_reason
          return
        fi
        ;;
      # python write on a plan file — matched on the raw text because token
      # mangling would strip the `'w'` quote the open(…,"w") test needs.
      python*)
        if [ "$plan_file_seen" -eq 0 ] && [ "$plan_dir_seen" -eq 0 ]; then
          :
        else
          for ((j = i + 1; j < n; j++)); do
            case "${toks[j]}" in
              -c | '-')
                case "$raw" in
                  *write_text*) {
                    _ret=$plan_reason
                    return
                  } ;;
                  *open\(*)
                    case "$raw" in
                      *'"w"'* | *"'w'"*) {
                        _ret=$plan_reason
                        return
                      } ;;
                    esac
                    ;;
                esac
                break
                ;;
              '-'*) : ;;
              *) break ;;
            esac
          done
        fi
        ;;
    esac
  done

  # python/perl removal and write spellings naming the override (matched on the
  # raw text — token mangling strips the quoting these idioms need).
  if [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; then
    case "$raw" in
      *os.remove* | *os.unlink* | *unlink\(* | *os.rename* | *os.replace* | *shutil.move* | *shutil.rmtree*)
        _ret=$ovr_reason
        return
        ;;
    esac
    if [ "$ovr_seen" -eq 1 ]; then
      case "$raw" in
        *write_text*)
          _ret=$ovr_reason
          return
          ;;
        *open\(*)
          case "$raw" in
            *'"w"'* | *"'w'"*)
              _ret=$ovr_reason
              return
              ;;
          esac
          ;;
      esac
    fi
  fi

  # OG3r item 5: SELF_CANON joins the python/perl needle as its own literal,
  # beside the relative names above — `python3 -c "open('<abs>', 'w')"` buries
  # the path inside open(), so the token==file_canons comparison never sees it;
  # the raw text still names it. Read-only spellings (a bare path in prose)
  # never fire: the write/removal idiom must be present too.
  if [ -n "$SELF_CANON" ]; then
    case "$raw" in
      *"$SELF_CANON"*)
        case "$raw" in
          *os.remove* | *os.unlink* | *unlink\(* | *os.rename* | *os.replace* | *shutil.move* | *shutil.rmtree*)
            _ret=$GUARD_REASON
            return
            ;;
        esac
        case "$raw" in
          *write_text*)
            _ret=$GUARD_REASON
            return
            ;;
          *open\(*)
            case "$raw" in
              *'"w"'* | *"'w'"*)
                _ret=$GUARD_REASON
                return
                ;;
            esac
            ;;
        esac
        ;;
    esac
  fi

  # a `>`/`>>`/`>|` redirect whose target is a plan file or the override writes it.
  for ((i = 0; i + 1 < n; i++)); do
    [ "${skip[i]}" -eq 0 ] || continue
    [ "${toks[i]}" = ">" ] || continue
    for b in "${bases[@]}"; do
      canon_path "${toks[i + 1]}" "$b"
      for kk in "${!plan_canons[@]}"; do
        is_plan_file_canon "$_canon" "${plan_canons[kk]}" && {
          _ret=$plan_reason
          return
        }
      done
      for kk in "${!file_canons[@]}"; do
        [ "$_canon" = "${file_canons[kk]}" ] && {
          _ret=${file_reasons[kk]}
          return
        }
      done
    done
  done
  # A clean "allow" (no reason found) leaves `_ret` empty.
  _ret=''
  return 0
}

# multiedit_after BEFORE PAYLOAD — BEFORE with every old->new edit applied in
# order. Each old_string/new_string is extracted with the same escape-aware
# pattern as json_string (a byte is taken verbatim inside a \" or \\ pair), so
# an edit whose text carries an escaped quote is captured whole — a [^"]*
# capture would truncate at the \" and silently drop the rest of the edit.
multiedit_after() {
  local before=$1 payload=$2
  local -a olds=() news=()
  local after=$before i o n
  mapfile -t olds < <(printf '%s\n' "$payload" | grep -o '"old_string"[[:space:]]*:[[:space:]]*"\(\\.\|[^"\\]\)*"' | sed 's/^[^:]*:[[:space:]]*"//; s/"$//')
  mapfile -t news < <(printf '%s\n' "$payload" | grep -o '"new_string"[[:space:]]*:[[:space:]]*"\(\\.\|[^"\\]\)*"' | sed 's/^[^:]*:[[:space:]]*"//; s/"$//')
  for i in "${!olds[@]}"; do
    json_unescape "${olds[$i]}"
    o=$_ret
    json_unescape "${news[$i]}"
    n=$_ret
    apply_edit "$after" "$o" "$n"
    after=$_ret
  done
  _ret=$after
}

# missing_headings BEFORE AFTER — the before-heading lines missing from (or
# changed in) AFTER; sorted inputs, so comm -23 reports the removed ones.
# headings is called in the MAIN shell on both sides (a fault in it must reach
# the EXIT trap), each result copied to a local before the comm, whose two
# `<(printf …)` process substitutions hold only the external printf — never a
# guard function.
missing_headings() {
  local bheads aheads
  headings "$1"
  bheads=$_ret
  headings "$2"
  aheads=$_ret
  if [ -z "$bheads" ]; then
    _ret=''
    return 0
  fi
  _ret=$(comm -23 <(printf '%s\n' "$bheads") <(printf '%s\n' "$aheads"))
}

main() {
  # The EXIT trap is installed here, as main's first statement — on the entry
  # path only, never at source time, so a sourcing bats test keeps its own traps
  # (CR2r3). Removing this line is the mutation that must let every fault through.
  trap _guard_trap EXIT
  local payload tool file_path resolved project_dir before after old new reason
  local e rel kind pc bcmd bcwd cnt
  _guard_active=1

  # The operator's lift: ORCHESTRATOR_GUARD=off in the hook's own environment
  # disables every rule. The orchestrator's shell cannot set this for itself —
  # the flag is read from this hook process's environment, which a `VAR=x cmd`
  # prefix in a Bash payload (a separate child process) never touches.
  if [ "${ORCHESTRATOR_GUARD:-}" = "off" ]; then
    warn "lifted by ORCHESTRATOR_GUARD=off"
    return 0
  fi

  # OG3r item 4: resolve SELF_CANON here, after the trap is installed (a fault
  # in the `realpath` below reaches the trap's fail-closed deny as "guard
  # fault", never an empty file_dirs entry downstream).
  if ! SELF_CANON=$(realpath -- "${BASH_SOURCE[0]}"); then
    warn "guard fault: realpath could not resolve ${BASH_SOURCE[0]}"
    exit 1
  fi

  payload=$(cat 2>/dev/null) || {
    warn "cannot read hook input (allowing)"
    return 0
  }
  # A non-empty payload that is not a complete JSON object is malformed: allow,
  # but say so on stderr so a real shell-out (including a truncated object that
  # still begins with `{`) is never silent. An object is complete when its last
  # non-blank byte is `}`.
  case "$payload" in
    '') : ;;
    *)
      if [[ $payload != '{'* || ${payload%"${payload##*[![:space:]]}"} != *'}' ]]; then
        warn "malformed hook input (allowing)"
        return 0
      fi
      ;;
  esac
  json_string "$payload" tool_name
  tool=$_ret
  [ -n "$tool" ] || {
    warn "malformed hook input (allowing)"
    return 0
  }
  project_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
  case "$tool" in
    Bash | bash)
      json_string "$payload" command
      bcmd=$_ret
      json_unescape "$bcmd"
      bcmd=$_ret
      json_string "$payload" cwd
      bcwd=$_ret
      bash_verdict "$bcmd" "$project_dir" "$bcwd"
      reason=$_ret
      [ -n "$reason" ] && deny "$reason"
      return 0
      ;;
    Edit | edit | Write | write | MultiEdit | multiedit) : ;;
    *) return 0 ;;
  esac

  json_string "$payload" file_path
  file_path=$_ret
  [ -n "$file_path" ] || return 0
  resolve_path "$file_path" "$project_dir"
  resolved=$_ret
  # OG3b item 1: the Edit/Write/MultiEdit arm refuses a file_path that resolves to
  # SELF_CANON — the guard's own file — independent of CLAUDE_PROJECT_DIR, so a
  # seat cannot edit the rules it obeys even when its project is the workspace.
  if [ "$resolved" = "$SELF_CANON" ]; then
    deny "$GUARD_REASON"
    return 0
  fi
  # CR2r: the Edit/Write/MultiEdit arm reads the PROTECTED list directly — no
  # hard-coded path. A `file` entry whose canonical path equals `resolved` is
  # the override (or any future operator-only file); a write that lands on it is
  # refused, whatever the tool. Reading it never reaches here (unknown tools
  # return above).
  pc=$(realpath -m -- "$project_dir")
  for e in "${PROTECTED_PATHS[@]}"; do
    rel=${e%%|*}
    kind=${e##*|}
    [ "$kind" = "file" ] || continue
    lex_norm "$rel" "$pc"
    if [ "$resolved" = "$_lex" ]; then
      file_reason "$rel"
      deny "$_ret"
      return 0
    fi
  done
  is_plan_file "$resolved" "$project_dir" || return 0

  before=""
  [ -r "$resolved" ] && before=$(cat -- "$resolved" 2>/dev/null)

  case "$tool" in
    Write | write)
      json_string "$payload" content
      cnt=$_ret
      json_unescape "$cnt"
      after=$_ret
      ;;
    MultiEdit | multiedit)
      multiedit_after "$before" "$payload"
      after=$_ret
      ;;
    *)
      json_string "$payload" old_string
      old=$_ret
      json_unescape "$old"
      old=$_ret
      json_string "$payload" new_string
      new=$_ret
      json_unescape "$new"
      new=$_ret
      apply_edit "$before" "$old" "$new"
      after=$_ret
      ;;
  esac

  missing_headings "$before" "$after"
  reason=$_ret
  if [ -n "$reason" ]; then
    deny "$HEADING_REASON"
  fi
  return 0
}

# Run only when executed, not when sourced — the bats suite sources this file
# to observe the tokeniser directly (guard_tokens in 91-orchestrator-guard.bats).
# The EXIT trap is installed by main itself, on the entry path only, so a
# sourcing test keeps its own traps (CR2r3).
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main
  exit 0
fi
