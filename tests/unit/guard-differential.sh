#!/usr/bin/env bash
# guard-differential.sh — the differential harness (IS22).
#
# Nothing else in this tree can answer "do these two guard implementations
# agree?", and that is the only question a security rewrite of
# tools/orchestrator-guard.sh must answer. This harness runs every corpus
# payload through both implementations and reports, per payload, whether the
# VERDICT (allow/deny) and the REASON TEXT match: two guards that deny the
# same command for different stated reasons have diverged in a way the
# operator will feel, so the reason is part of the contract, not decoration.
#
# An implementation is a bash script with tools/orchestrator-guard.sh's hook
# contract: it reads one Claude Code PreToolUse payload (JSON) on stdin and
# prints the deny decision JSON on stdout — nothing for allow. The harness
# runs both under an identical, harness-controlled environment (one scratch
# project as CLAUDE_PROJECT_DIR, one scratch HOME, ORCHESTRATOR_GUARD=on), so
# a divergence can only come from the implementations themselves. It is built
# and proven BEFORE any second implementation exists: run bash against bash —
# the same file on both sides — the whole corpus must be zero divergences.
# A harness that cannot show itself green on a known-identical pair is worth
# nothing.
#
# The corpus (no explicit file given) is three mechanical sources:
#   1. every row of tests/unit/91-orchestrator-guard-sweep.txt (header-count
#      verified against the data rows);
#   2. every payload embedded in the @test cases of
#      tests/unit/91-orchestrator-guard.bats and 93-house-guard.bats —
#      extracted, never retyped, so a case added later is covered the moment
#      it lands. Two passes per file: the bash-command shapes (bpayload/hg_bash
#      arguments, for-cmd words, cmd array elements and cmd= assignments),
#      then the Write/Edit/MultiEdit and JSON shapes (calls of every builder
#      function the two files define — discovered by rule, never named —,
#      inline `$(python3 -c '…json.dumps({…})…' ARGS)` payloads and
#      single-quoted '{"tool_name"…' literals). A site the second pass cannot
#      extract is a counted `# excluded FILE:LINE REASON` line, never dropped;
#   3. generated payloads: each protected path (the three PROTECTED_PATHS
#      entries plus the six absolute prefixes) in every write-verb position
#      (redirect, tee, cp/mv/install destination, sed -i, the delete family)
#      and in read position, through relative and absolute spellings, `..`
#      escapes that resolve into the project and ones that resolve outside,
#      glob spellings, quoted and backslash-continued forms, and path tokens
#      at 1/50/100/200 tokens deep into the command.
# An explicit corpus FILE (one payload JSON per line, `#` comments and blank
# lines skipped) overrides the generated corpus — the bats suite uses it to
# seed targeted divergences.
#
# A divergence is not a diff to eyeball: every diverging payload is printed
# verbatim with both verdicts and both reasons, the whole corpus is always
# scanned (a divergence that sorts late is never missed), and the exit status
# is non-zero the moment one exists. A harness fault (unreadable
# implementation, an implementation that exits non-zero or prints output with
# no permissionDecision) is exit 2, never a silent comparison.
set -u

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd) || exit 2
SWEEP_FILE="$SCRIPT_DIR/91-orchestrator-guard-sweep.txt"
BATS_91_FILE="$SCRIPT_DIR/91-orchestrator-guard.bats"
BATS_93_FILE="$SCRIPT_DIR/93-house-guard.bats"

usage() {
  cat >&2 <<'USAGE'
usage: guard-differential.sh <impl-a> <impl-b> [corpus-file]
       guard-differential.sh --corpus-size
       guard-differential.sh --corpus-stats
       guard-differential.sh --corpus-dump
       guard-differential.sh --builders

Compares two guard implementations (bash scripts with
tools/orchestrator-guard.sh's stdin-payload/stdout-decision contract) payload
by payload over the corpus: verdict (allow/deny) AND reason text. Without a
corpus file the corpus is generated from the sweep fixture, the payloads
extracted from the two guard bats files, and a generated protected-path
matrix. Exits 0 when every payload agrees, 1 on any divergence, 2 on a
harness fault. --corpus-dump prints every payload, one per line, then the
`# excluded` lines (a valid corpus file); --builders prints the discovered
payload-builder table, one `NAME TOOL ARITY` line each.
USAGE
}

fault() {
  printf 'guard-differential: %s\n' "$1" >&2
  exit 2
}

# The corpus (payload JSON strings) and the per-source counts.
CORPUS=()
N_SWEEP=0
N_B91=0
N_B93=0
N_GEN=0

# The harness-controlled environment both implementations run under.
WORK=''
PROJECT=''
WORK_HOME=''

# An implementation pair (set by main).
IMPL_A=''
IMPL_B=''

# run_impl's verdict pair.
RV_VERDICT=''
RV_REASON=''

# wrap_payload's result.
_payload=''

# unquote helpers' result; unq_word's first unresolved name; take_args' words
# and remainder; whether the second pass extracted or excluded on this line.
_ret=''
_unres=''
_rest=''
ARGS=()
_hit=0

# The second pass's exclusions (`# excluded FILE:LINE REASON`), in file order.
EXCL=()
N_WRITE=0
N_EDIT=0
N_MEDIT=0

# The discovered payload builders (parallel arrays, discovery order) and the
# FILE:LINE of every builder-body line, which the second pass never reads.
B_NAMES=()
B_TOOLS=()
B_ARITY=()
declare -A B_BODY=()

# The second pass's assignment table: file scope (lines above a file's first
# @test) and test scope (emptied at each @test); SCOPE_ORDER is their union,
# longest name first, rebuilt when SCOPE_DIRTY.
declare -A FSCOPE=()
declare -A TSCOPE=()
SCOPE_ORDER=()
SCOPE_DIRTY=1

# json_esc S — S with the five JSON escapes a corpus value may need, in this
# order: backslash (first, so the escapes added after it are never doubled),
# quote, tab, carriage return, newline. No surrounding quotes; result in _ret.
json_esc() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\t'/\\t}
  s=${s//$'\r'/\\r}
  s=${s//$'\n'/\\n}
  _ret=$s
}

# wrap_payload CMD — the Claude Code Bash payload JSON for CMD, in _payload.
# json_esc covers the five characters a corpus command may carry, so a payload
# with an embedded backslash-newline continuation or a quoted glob survives
# verbatim.
wrap_payload() {
  json_esc "$1"
  _payload="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$_ret\"}}"
}

# wrap_write_payload FILE CONTENT — the Claude Code Write payload, in _payload.
wrap_write_payload() {
  local f c
  json_esc "$1"
  f=$_ret
  json_esc "$2"
  c=$_ret
  _payload="{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$f\",\"content\":\"$c\"}}"
}

# wrap_edit_payload FILE OLD NEW — the Claude Code Edit payload, in _payload.
wrap_edit_payload() {
  local f o n
  json_esc "$1"
  f=$_ret
  json_esc "$2"
  o=$_ret
  json_esc "$3"
  n=$_ret
  _payload="{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$f\",\"old_string\":\"$o\",\"new_string\":\"$n\"}}"
}

# wrap_meditpayload FILE OLD NEW — the Claude Code MultiEdit payload with one
# edit, in _payload.
wrap_meditpayload() {
  local f o n
  json_esc "$1"
  f=$_ret
  json_esc "$2"
  o=$_ret
  json_esc "$3"
  n=$_ret
  _payload="{\"tool_name\":\"MultiEdit\",\"tool_input\":{\"file_path\":\"$f\",\"edits\":[{\"old_string\":\"$o\",\"new_string\":\"$n\"}]}}"
}

# setup_work — the scratch environment: one project dir as CLAUDE_PROJECT_DIR
# and one scratch HOME, identical for both implementations, removed on exit.
setup_work() {
  WORK=$(mktemp -d "${TMPDIR:-/tmp}/guard-differential.XXXXXX") || fault "cannot create scratch dir"
  PROJECT="$WORK/project"
  WORK_HOME="$WORK/home"
  mkdir -p "$PROJECT" "$WORK_HOME" || fault "cannot set up the scratch project"
  trap 'rm -rf -- "${WORK:-}"' EXIT
}

# --- source 1: the sweep fixture -------------------------------------------

load_sweep() {
  local row declared=0 rows=0
  [ -r "$SWEEP_FILE" ] || fault "sweep fixture not readable: $SWEEP_FILE"
  while IFS= read -r row || [ -n "$row" ]; do
    if [ "$rows" -eq 0 ] && [ "$declared" -eq 0 ]; then
      case "$row" in
        '# rows: '*) declared=${row#'# rows: '} ;;
        *) fault "sweep header missing (first line: $row)" ;;
      esac
      continue
    fi
    [ -n "$row" ] || continue
    wrap_payload "$row"
    CORPUS+=("$_payload")
    rows=$((rows + 1))
  done <"$SWEEP_FILE"
  [ "$rows" -eq "$declared" ] || fault "sweep declares $declared rows but holds $rows"
  N_SWEEP=$rows
}

# --- source 2: payloads extracted from the bats files ------------------------

RE_ARRAY='^[[:space:]]*(local[[:space:]]+(-a[[:space:]]+)?)?[A-Za-z_][A-Za-z0-9_]*=\([[:space:]]*$'
RE_ARRAY_END='^[[:space:]]*\)[[:space:]]*$'
RE_FOR='^[[:space:]]*for[[:space:]]+cmd[[:space:]]+in[[:space:]]+(.*);[[:space:]]*do[[:space:]]*$'
RE_CMDASSIGN="^[[:space:]]*cmd=(\".*\"|'.*'|\\\$'.*')[[:space:]]*\$"
RE_BPAYLOAD="bpayload[[:space:]]+(\".*\"|'.*'|\\\$'.*')"
RE_HGBASH="hg_bash[[:space:]]+('[^']*')"

# is_var_ref CONTENT — true when CONTENT is nothing but a variable reference
# (`$cmd`, `${cmds[@]}`): a loop hand-off whose payload comes from the
# for/array source itself, never a payload.
is_var_ref() {
  [[ "$1" =~ ^\$[A-Za-z_][A-Za-z0-9_]*$ || "$1" =~ ^\$\{[A-Za-z_][A-Za-z0-9_]*\[@\]\}$ ]]
}

# unq_dq S — the content of a double-quoted bats element, unescaped, in _ret.
# The double quotes in the source would have expanded variables, so the known
# ones get the harness's deterministic values (a write to $GUARD_ABS must hit
# the same arms in both implementations, not resolve to two different paths);
# unknown spellings stay literal — both sides see identical text either way.
unq_dq() {
  local s=$1 out='' i c n=${#1} bs=$'\\'
  for ((i = 0; i < n; i++)); do
    c=${s:i:1}
    if [ "$c" = "$bs" ] && [ $((i + 1)) -lt "$n" ]; then
      i=$((i + 1))
      c=${s:i:1}
      case "$c" in
        '"' | "$bs") out+="$c" ;;
        *) out+="\\$c" ;;
      esac
    else
      out+="$c"
    fi
  done
  out=${out//\$GUARD_ABS/"$PROJECT/tools/orchestrator-guard.sh"}
  out=${out//\$treeroot/"$PROJECT"}
  out=${out//\$PROJECT/"$PROJECT"}
  out=${out//\$BATS_TEST_TMPDIR/"$WORK/scratch"}
  out=${out//\$HOME/"$WORK_HOME"}
  _ret=$out
}

# unq_ansi S — the content of a $'…' ANSI-C element, unescaped (\n, \t, \r,
# \', \", \\ and \xHH), in _ret.
unq_ansi() {
  local s=$1 out='' i c n=${#1} hex bs=$'\\'
  for ((i = 0; i < n; i++)); do
    c=${s:i:1}
    if [ "$c" = "$bs" ] && [ $((i + 1)) -lt "$n" ]; then
      i=$((i + 1))
      c=${s:i:1}
      case "$c" in
        'n') out+=$'\n' ;;
        't') out+=$'\t' ;;
        'r') out+=$'\r' ;;
        'x')
          if [ $((i + 2)) -lt "$n" ]; then
            hex=${s:i+1:2}
            printf -v c '%b' "\\x$hex"
            i=$((i + 2))
          fi
          out+="$c"
          ;;
        "'" | '"' | "$bs") out+="$c" ;;
        *) out+="$c" ;;
      esac
    else
      out+="$c"
    fi
  done
  _ret=$out
}

# emit_elem RAW — append one corpus payload for a quoted bats element
# (a "…", '…' or $'…' literal) unless it is a bare variable reference.
emit_elem() {
  local e=$1 content=''
  e="${e#"${e%%[![:space:]]*}"}"
  e="${e%"${e##*[![:space:]]}"}"
  case "$e" in
    '$'\'*)
      e=${e#\$\'}
      e=${e%\'}
      unq_ansi "$e"
      content=$_ret
      ;;
    '"'*)
      e=${e#\"}
      e=${e%\"}
      unq_dq "$e"
      content=$_ret
      ;;
    "'"*)
      e=${e#\'}
      e=${e%\'}
      content=$e
      ;;
    *)
      return 0
      ;;
  esac
  is_var_ref "$content" && return 0
  [ -n "$content" ] || return 0
  wrap_payload "$content"
  CORPUS+=("$_payload")
}

# emit_for_words REST — append one corpus payload per double-quoted word of a
# `for cmd in …` list.
emit_for_words() {
  local rest=$1 w
  while [[ "$rest" == *\"* ]]; do
    rest=${rest#*\"}
    w=${rest%%\"*}
    rest=${rest#*\"}
    [ -n "$w" ] || continue
    unq_dq "$w"
    is_var_ref "$_ret" && continue
    [ -n "$_ret" ] || continue
    wrap_payload "$_ret"
    CORPUS+=("$_payload")
  done
}

# extract_bats FILE — source 2: every bash-command payload embedded in the
# @test cases of one bats file, appended to CORPUS.
extract_bats() {
  local file=$1 in_array=0 line
  [ -r "$file" ] || fault "bats file not readable: $file"
  while IFS= read -r line || [ -n "$line" ]; do
    if [ "$in_array" -eq 1 ]; then
      [[ "$line" =~ $RE_ARRAY_END ]] && {
        in_array=0
        continue
      }
      emit_elem "$line"
      continue
    fi
    [[ "$line" =~ $RE_ARRAY ]] && {
      in_array=1
      continue
    }
    [[ "$line" =~ $RE_FOR ]] && {
      emit_for_words "${BASH_REMATCH[1]}"
      continue
    }
    [[ "$line" =~ $RE_CMDASSIGN ]] && {
      emit_elem "${BASH_REMATCH[1]}"
      continue
    }
    [[ "$line" =~ $RE_BPAYLOAD ]] && {
      emit_elem "${BASH_REMATCH[1]}"
      continue
    }
    [[ "$line" =~ $RE_HGBASH ]] && {
      emit_elem "${BASH_REMATCH[1]}"
      continue
    }
  done <"$file"
}

# --- source 2, second pass: Write/Edit/MultiEdit and JSON payloads -----------

# The word grammar. A segment is a double-quoted, single-quoted or $'…' ANSI-C
# string; a word is a run of adjacent segments, joined the way bash joins
# them. A word never crosses unquoted whitespace, so the arguments of one call
# split where bash splits them.
Q="'"
TOK_DQ='"([^"\\]|\\.)*"'
TOK_SQ="${Q}[^${Q}]*${Q}"
TOK_AN='\$'"${Q}"'([^'"${Q}"'\\]|\\.)*'"${Q}"
TOK_WORD="(${TOK_DQ}|${TOK_SQ}|${TOK_AN})+"
RE_DQ_AT="^${TOK_DQ}"
RE_SQ_AT="^${TOK_SQ}"
RE_AN_AT="^${TOK_AN}"
RE_WORD_AT="^(${TOK_WORD})"
RE_ARG="^[[:space:]]+(${TOK_WORD})"
# the quote gate: a builder name is a call only when a quoted word follows it
RE_QUOTE_GATE='^[[:space:]]+("|'"${Q}"'|\$'"${Q}"')'
RE_COMMENT='^[[:space:]]*#'
RE_ASSIGN="^[[:space:]]*(local[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=(${TOK_WORD})[[:space:]]*\$"
RE_FORVAR='^[[:space:]]*for[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)[[:space:]]+in([[:space:]]|$)'
RE_PYDUMPS='\$\(python3 -c '"${Q}"'([^'"${Q}"']*json\.dumps\((\{.*\}),[[:space:]]*(ensure_ascii|separators)=[^'"${Q}"']*)'"${Q}"'(.*)$'
RE_ARGV='sys\.argv\[([0-9]+)\]'
RE_UNRES="\\\$([A-Za-z_][A-Za-z0-9_]*|\\{[^}]*\\}?|\\()"
RE_FUNC='^([A-Za-z_][A-Za-z0-9_]*)\(\)[[:space:]]*\{'
RE_TOOLNAME='"tool_name":"([^"]*)"'
LITERAL_START="${Q}{\"tool_name\""

# bats_readable FILE — every reader of a bats file (discovery and the second
# pass) faults on one it cannot read; none skips it.
bats_readable() {
  [ -r "$1" ] || fault "bats file not readable: $1"
}

# name_before A B — true when name A is tried before B: longer first (so
# $PLANS_DIR is replaced ahead of $PLAN), ties in byte order.
name_before() {
  [ "${#1}" -gt "${#2}" ] && return 0
  [ "${#1}" -eq "${#2}" ] && [[ "$1" < "$2" ]]
}

# scope_order — SCOPE_ORDER = the union of both scopes' names, longest first.
scope_order() {
  local -A seen=()
  local n t i j
  SCOPE_ORDER=()
  for n in "${!TSCOPE[@]}" "${!FSCOPE[@]}"; do
    [ -z "${seen[$n]+x}" ] || continue
    seen[$n]=1
    SCOPE_ORDER+=("$n")
  done
  for ((i = 1; i < ${#SCOPE_ORDER[@]}; i++)); do
    t=${SCOPE_ORDER[i]}
    j=$((i - 1))
    while [ "$j" -ge 0 ] && name_before "$t" "${SCOPE_ORDER[j]}"; do
      SCOPE_ORDER[j + 1]=${SCOPE_ORDER[j]}
      j=$((j - 1))
    done
    SCOPE_ORDER[j + 1]=$t
  done
  SCOPE_DIRTY=0
}

# resolve_names TEXT — TEXT (a double-quoted segment, already through
# unq_dq's static table) with every recorded name replaced in both its
# ${NAME} and $NAME forms, test scope before file scope, in _ret; a `$`
# left before a letter, `_`, `{` or `(` sets _unres (when still empty) to
# that bare name.
resolve_names() {
  local v=$1 n val
  [ "$SCOPE_DIRTY" -eq 0 ] || scope_order
  for n in "${SCOPE_ORDER[@]}"; do
    if [ -n "${TSCOPE[$n]+x}" ]; then
      val=${TSCOPE[$n]}
    else
      val=${FSCOPE[$n]}
    fi
    v=${v//"\${$n}"/"$val"}
    v=${v//"\$$n"/"$val"}
  done
  if [ -z "$_unres" ] && [[ "$v" =~ $RE_UNRES ]]; then
    n=${BASH_REMATCH[1]}
    n=${n#\{}
    _unres=${n%\}}
  fi
  _ret=$v
}

# unq_word WORD — WORD unquoted segment by segment ($'…' through unq_ansi,
# '…' literally, "…" through unq_dq and the assignment table), in _ret; the
# first unresolved name in _unres (empty when every name resolved). An empty
# or variable-only word is a value like any other, never skipped.
unq_word() {
  local w=$1 out='' seg
  _unres=''
  while [ -n "$w" ]; do
    if [[ "$w" =~ $RE_AN_AT ]]; then
      seg=${BASH_REMATCH[0]}
      unq_ansi "${seg:2:${#seg}-3}"
    elif [[ "$w" =~ $RE_SQ_AT ]]; then
      seg=${BASH_REMATCH[0]}
      _ret=${seg:1:${#seg}-2}
    elif [[ "$w" =~ $RE_DQ_AT ]]; then
      seg=${BASH_REMATCH[0]}
      unq_dq "${seg:1:${#seg}-2}"
      resolve_names "$_ret"
    else
      break
    fi
    out+=$_ret
    w=${w:${#seg}}
  done
  _ret=$out
}

# take_args TEXT N — consume up to N whitespace-led words from the start of
# TEXT (N < 0: every one there). ARGS holds their unquoted values, _unres the
# first unresolved name among them, _rest what follows the last word. Fails
# when fewer than N words were there.
take_args() {
  local rest=$1 want=$2 un='' whole
  ARGS=()
  while [ "$want" -lt 0 ] || [ "${#ARGS[@]}" -lt "$want" ]; do
    [[ "$rest" =~ $RE_ARG ]] || break
    whole=${BASH_REMATCH[0]}
    unq_word "${BASH_REMATCH[1]}"
    [ -n "$un" ] || un=$_unres
    ARGS+=("$_ret")
    rest=${rest:${#whole}}
  done
  _unres=$un
  _rest=$rest
  [ "$want" -lt 0 ] || [ "${#ARGS[@]}" -eq "$want" ]
}

# exclude BASE LINE REASON — one counted exclusion line.
exclude() {
  EXCL+=("# excluded $1:$2 $3")
}

# add_builder KEY NAME TOOL ARITY START END — record a builder block (KEY is
# its bats file's path): its
# body lines (START+1 … END-1) are never read by the second pass; the table
# keeps a name's first definition.
add_builder() {
  local i
  for ((i = $5 + 1; i < $6; i++)); do
    B_BODY["$1:$i"]=1
  done
  for i in "${B_NAMES[@]}"; do
    [ "$i" != "$2" ] || return 0
  done
  B_NAMES+=("$2")
  B_TOOLS+=("$3")
  B_ARITY+=("$4")
}

# discover_builders — a builder is any function 91 or 93 defines (a
# `NAME() {` line through the next `}` line at column 0) whose body holds a
# "tool_name":"TOOL" pair: TOOL is the body's first such value, ARITY its
# highest sys.argv[N]. Runs over 91 then 93; a name defined in both keeps its
# first definition. A builder whose TOOL has no emitter, or whose ARITY is not
# its emitter's, is a fault — never emitted as something else.
discover_builders() {
  local file key line ln name start tool arity rest k i want
  B_NAMES=()
  B_TOOLS=()
  B_ARITY=()
  B_BODY=()
  for file in "$BATS_91_FILE" "$BATS_93_FILE"; do
    bats_readable "$file"
    key=$file
    ln=0
    name=''
    while IFS= read -r line || [ -n "$line" ]; do
      ln=$((ln + 1))
      if [ -z "$name" ]; then
        if [[ "$line" =~ $RE_FUNC ]]; then
          name=${BASH_REMATCH[1]}
          start=$ln
          tool=''
          arity=0
        fi
        continue
      fi
      if [[ "$line" == '}'* ]]; then
        [ -z "$tool" ] || add_builder "$key" "$name" "$tool" "$arity" "$start" "$ln"
        name=''
        continue
      fi
      if [ -z "$tool" ] && [[ "$line" =~ $RE_TOOLNAME ]]; then
        tool=${BASH_REMATCH[1]}
      fi
      rest=$line
      while [[ "$rest" =~ $RE_ARGV ]]; do
        k=$((10#${BASH_REMATCH[1]}))
        [ "$k" -le "$arity" ] || arity=$k
        rest=${rest#*"${BASH_REMATCH[0]}"}
      done
    done <"$file"
  done
  for i in "${!B_NAMES[@]}"; do
    case "${B_TOOLS[i],,}" in
      bash) continue ;;
      write) want=2 ;;
      edit | multiedit) want=3 ;;
      *) fault "builder ${B_NAMES[i]} has unsupported tool ${B_TOOLS[i]}" ;;
    esac
    [ "${B_ARITY[i]}" -eq "$want" ] ||
      fault "builder ${B_NAMES[i]} takes ${B_ARITY[i]} arguments, ${B_TOOLS[i]} needs $want"
  done
}

# record_assign NAME WORD IN_TEST — `NAME=WORD` records NAME's value in the
# test scope (inside a @test) or the file scope, when WORD resolves. The
# static-table names are unq_dq's and never recorded.
record_assign() {
  case "$1" in
    PROJECT | GUARD_ABS | treeroot | BATS_TEST_TMPDIR | HOME) return 0 ;;
  esac
  unq_word "$2"
  [ -z "$_unres" ] || return 0
  if [ "$3" -eq 1 ]; then
    TSCOPE[$1]=$_ret
  else
    FSCOPE[$1]=$_ret
  fi
  SCOPE_DIRTY=1
}

# scan_builder_calls BASE LN LINE — every call of a discovered non-Bash
# builder on LINE: the name at a word boundary, then ARITY quoted words.
scan_builder_calls() {
  local base=$1 ln=$2 line=$3 i name tool off pos pre tail
  for i in "${!B_NAMES[@]}"; do
    name=${B_NAMES[i]}
    tool=${B_TOOLS[i],,}
    [ "$tool" != bash ] || continue
    off=0
    while :; do
      tail=${line:off}
      [[ "$tail" == *"$name"* ]] || break
      pre=${tail%%"$name"*}
      pos=$((off + ${#pre}))
      off=$((pos + ${#name}))
      if [ "$pos" -gt 0 ] && [[ "${line:pos-1:1}" == [A-Za-z0-9_] ]]; then
        continue
      fi
      tail=${line:off}
      [[ "$tail" =~ $RE_QUOTE_GATE ]] || continue
      _hit=1
      if ! take_args "$tail" "${B_ARITY[i]}"; then
        exclude "$base" "$ln" "unparsed $name call"
        continue
      fi
      off=$((off + ${#tail} - ${#_rest}))
      if [ -n "$_unres" ]; then
        exclude "$base" "$ln" "unresolved \$$_unres"
        continue
      fi
      case "$tool" in
        write) wrap_write_payload "${ARGS[0]}" "${ARGS[1]}" ;;
        edit) wrap_edit_payload "${ARGS[0]}" "${ARGS[1]}" "${ARGS[2]}" ;;
        multiedit) wrap_meditpayload "${ARGS[0]}" "${ARGS[1]}" "${ARGS[2]}" ;;
      esac
      CORPUS+=("$_payload")
    done
  done
}

# scan_inline_python BASE LN LINE — a `$(python3 -c '…json.dumps({…},…)…'
# ARGS)` payload whose dict names tool_name: the dict text is already JSON,
# so it is emitted verbatim with each sys.argv[N] replaced, in one
# left-to-right scan, by argument N as a JSON string. Replaced text is never
# rescanned.
scan_inline_python() {
  local base=$1 ln=$2 line=$3 dict out tok k pre
  [[ "$line" =~ $RE_PYDUMPS ]] || return 0
  dict=${BASH_REMATCH[2]}
  [[ "$dict" == *'"tool_name"'* ]] || return 0
  _hit=1
  take_args "${BASH_REMATCH[4]}" -1
  if [ -n "$_unres" ]; then
    exclude "$base" "$ln" "unresolved \$$_unres"
    return 0
  fi
  out=''
  while [[ "$dict" =~ $RE_ARGV ]]; do
    tok=${BASH_REMATCH[0]}
    k=$((10#${BASH_REMATCH[1]}))
    if [ "$k" -lt 1 ] || [ "$k" -gt "${#ARGS[@]}" ]; then
      exclude "$base" "$ln" "unbound sys.argv"
      return 0
    fi
    pre=${dict%%"$tok"*}
    json_esc "${ARGS[k - 1]}"
    out+="$pre\"$_ret\""
    dict=${dict:${#pre}+${#tok}}
  done
  CORPUS+=("$out$dict")
}

# scan_literals BASE LN LINE — every '{"tool_name"… word at line start or
# after whitespace, emitted as its unquoted text, never parsed (a malformed
# literal is an input the guard must handle identically on both sides).
scan_literals() {
  local base=$1 ln=$2 line=$3 off=0 tail pre pos word
  while :; do
    tail=${line:off}
    [[ "$tail" == *"$LITERAL_START"* ]] || break
    pre=${tail%%"$LITERAL_START"*}
    pos=$((off + ${#pre}))
    off=$((pos + 1))
    if [ "$pos" -gt 0 ] && [[ "${line:pos-1:1}" != [[:space:]] ]]; then
      continue
    fi
    [[ "${line:pos}" =~ $RE_WORD_AT ]] || continue
    word=${BASH_REMATCH[1]}
    off=$((pos + ${#word}))
    _hit=1
    unq_word "$word"
    if [ -n "$_unres" ]; then
      exclude "$base" "$ln" "unresolved \$$_unres"
      continue
    fi
    CORPUS+=("$_ret")
  done
}

# extract_payloads FILE — source 2's second pass over one bats file: builder
# calls, inline python3 payloads and JSON literals, appended to CORPUS; every
# other non-comment line naming tool_name outside a builder body is a
# `runtime-built JSON` exclusion. Comment lines and builder bodies are never
# read; both scopes start empty in each file.
extract_payloads() {
  local file=$1 base=${1##*/} line ln=0 in_test=0
  bats_readable "$file"
  FSCOPE=()
  TSCOPE=()
  SCOPE_DIRTY=1
  while IFS= read -r line || [ -n "$line" ]; do
    ln=$((ln + 1))
    [ -z "${B_BODY["$file:$ln"]+x}" ] || continue
    [[ "$line" =~ $RE_COMMENT ]] && continue
    if [[ "$line" == '@test'* ]]; then
      TSCOPE=()
      in_test=1
      SCOPE_DIRTY=1
    fi
    if [[ "$line" =~ $RE_FORVAR ]]; then
      unset "TSCOPE[${BASH_REMATCH[1]}]"
      SCOPE_DIRTY=1
    fi
    if [[ "$line" =~ $RE_ASSIGN ]]; then
      record_assign "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "$in_test"
    fi
    _hit=0
    scan_builder_calls "$base" "$ln" "$line"
    scan_inline_python "$base" "$ln" "$line"
    scan_literals "$base" "$ln" "$line"
    if [ "$_hit" -eq 0 ] && [[ "$line" == *tool_name* ]]; then
      exclude "$base" "$ln" "runtime-built JSON"
    fi
  done <"$file"
}

# --- source 3: the generated protected-path matrix ---------------------------

build_generated() {
  local -a rel_targets=(
    'docs/superpowers/plans'
    'docs/superpowers/plans/x.md'
    '.claude/ritual-override'
    'tools/orchestrator-guard.sh'
  )
  local -a prefixes=(
    /run/baskets
    /var/lib/baskets
    /var/lib/helm
    /var/lib/egress-broker
    /var/lib/lanes
    /var/lib/secrets
  )
  # every write-verb position and the read positions, one @T@ placeholder.
  local -a forms=(
    'printf x > @T@'
    'printf x >> @T@'
    'tee @T@'
    'tee -a @T@'
    'cp /tmp/src @T@'
    'mv /tmp/src @T@'
    'install -m600 /tmp/src @T@'
    'sed -i s/a/b/ @T@'
    'rm @T@'
    'rm -rf @T@'
    'rmdir @T@'
    'shred @T@'
    'mv @T@ /tmp/dst'
    'rsync -a /tmp/src @T@'
    'cat @T@'
    'grep -n foo @T@'
    'cp @T@ /tmp/dst'
  )
  # the absolute prefixes only feed the redirect/tee/copy arms and their read
  # counterparts in bash_verdict's PROTECTED loop.
  local -a pforms=(
    'printf x > @T@'
    'tee @T@'
    'cp /tmp/src @T@'
    'rm -rf @T@'
    'cat @T@'
  )
  local t d b s f text pfx base c k fill
  local LF=$'\n'
  for t in "${rel_targets[@]}"; do
    d=${t%/*}
    b=${t##*/}
    local -a spellings=(
      "$t"
      "$PROJECT/$t"
      "./$t"
      "$PROJECT/./$t"
      "$PROJECT/$d/../$b"
      "$PROJECT/$d/../../$b"
      "$PROJECT/../../$b"
      "$d/*"
      "\"$t\""
      "'$t'"
    )
    for f in "${forms[@]}"; do
      for s in "${spellings[@]}"; do
        text=${f//@T@/"$s"}
        wrap_payload "$text"
        CORPUS+=("$_payload")
      done
    done
  done
  for pfx in "${prefixes[@]}"; do
    base=${pfx##*/}
    local -a pspellings=(
      "$pfx/x"
      "$pfx/../$base/x"
      "$pfx/../../../x"
      "$pfx/*"
      "\"$pfx/x\""
      "'$pfx/x'"
    )
    for f in "${pforms[@]}"; do
      for s in "${pspellings[@]}"; do
        text=${f//@T@/"$s"}
        wrap_payload "$text"
        CORPUS+=("$_payload")
      done
    done
  done
  # the backslash-continued forms: a `\`+newline continuation the guard must
  # fold to a space before tokenising.
  for t in "${rel_targets[@]}"; do
    for f in 'printf x > ' 'rm -rf '; do
      text="${f}\\${LF}${t}"
      wrap_payload "$text"
      CORPUS+=("$_payload")
    done
  done
  # path tokens at 1/50/100/200: the protected write after that many filler
  # tokens, and the same path token repeated that many times — no notion of
  # a command position may stop the scan early.
  fill='printf x > docs/superpowers/plans/x.md'
  for c in 1 50 100 200; do
    if [ "$c" -gt 1 ]; then
      text='echo'
      for ((k = 1; k < c; k++)); do
        text+=" f$k"
      done
      text+="; $fill"
    else
      text=$fill
    fi
    wrap_payload "$text"
    CORPUS+=("$_payload")
    text='cat docs/superpowers/plans/x.md'
    for ((k = 1; k < c; k++)); do
      text+=' docs/superpowers/plans/x.md'
    done
    wrap_payload "$text"
    CORPUS+=("$_payload")
  done
}

# --- corpus assembly ---------------------------------------------------------

# load_corpus_file FILE — an explicit corpus: one payload JSON per line.
load_corpus_file() {
  local f=$1 line
  [ -r "$f" ] || fault "corpus file not readable: $f"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      '' | '#'*) continue ;;
    esac
    CORPUS+=("$line")
  done <"$f"
  [ "${#CORPUS[@]}" -gt 0 ] || fault "corpus file holds no payloads: $f"
}

build_corpus() {
  local before
  discover_builders
  load_sweep
  before=${#CORPUS[@]}
  extract_bats "$BATS_91_FILE"
  extract_payloads "$BATS_91_FILE"
  N_B91=$((${#CORPUS[@]} - before))
  before=${#CORPUS[@]}
  extract_bats "$BATS_93_FILE"
  extract_payloads "$BATS_93_FILE"
  N_B93=$((${#CORPUS[@]} - before))
  before=${#CORPUS[@]}
  build_generated
  N_GEN=$((${#CORPUS[@]} - before))
}

# count_tools — N_WRITE/N_EDIT/N_MEDIT: the corpus entries whose payload is a
# Write, Edit or MultiEdit call, counted over CORPUS, never per shape.
count_tools() {
  local p
  N_WRITE=0
  N_EDIT=0
  N_MEDIT=0
  for p in "${CORPUS[@]}"; do
    case "$p" in
      '{"tool_name":"Write"'*) N_WRITE=$((N_WRITE + 1)) ;;
      '{"tool_name":"Edit"'*) N_EDIT=$((N_EDIT + 1)) ;;
      '{"tool_name":"MultiEdit"'*) N_MEDIT=$((N_MEDIT + 1)) ;;
    esac
  done
}

# --- the comparison ------------------------------------------------------------

# run_impl IMPL PAYLOAD — one implementation's verdict over one payload, in
# RV_VERDICT / RV_REASON. The implementation runs under the harness's
# controlled environment; its stderr is discarded (the guard's warn channel).
# Non-zero exit or output without a permissionDecision is a harness fault —
# a comparison over garbage is never silently continued.
run_impl() {
  local impl=$1 payload=$2 out decision reason
  out=$(printf '%s\n' "$payload" |
    HOME="$WORK_HOME" CLAUDE_PROJECT_DIR="$PROJECT" ORCHESTRATOR_GUARD=on \
      bash "$impl" 2>/dev/null) || fault "implementation $impl exited non-zero on: $payload"
  if [ -z "$out" ]; then
    RV_VERDICT=allow
    RV_REASON=''
    return 0
  fi
  decision=$(printf '%s\n' "$out" | sed -n 's/.*"permissionDecision":"\([a-z]*\)".*/\1/p')
  reason=$(printf '%s\n' "$out" | sed -n 's/.*"permissionDecisionReason":"\(\(\\.\|[^"\\]\)*\)".*/\1/p')
  # undo the JSON escapes a reason may carry (\\ then \", a backslash parked first)
  reason=${reason//\\\\/__BS__}
  reason=${reason//\\\"/\"}
  reason=${reason//__BS__/\\}
  case "$decision" in
    deny)
      RV_VERDICT=deny
      RV_REASON=$reason
      ;;
    allow | ask)
      # a decision that is not a deny does not block the tool; ask is not a
      # deny either, so both collapse to the allow bucket with their reason
      # still compared
      RV_VERDICT=allow
      RV_REASON=$reason
      ;;
    *)
      fault "implementation $impl emitted output without a permissionDecision: $out"
      ;;
  esac
}

# compare — run every corpus payload through both implementations, print each
# divergence (payload verbatim, both verdicts, both reasons), and exit
# non-zero as soon as one exists. The whole corpus is always scanned: a
# divergence that sorts late is never missed.
compare() {
  local i n=${#CORPUS[@]} divergences=0 va ra vb rb
  for ((i = 0; i < n; i++)); do
    run_impl "$IMPL_A" "${CORPUS[$i]}"
    va=$RV_VERDICT
    ra=$RV_REASON
    run_impl "$IMPL_B" "${CORPUS[$i]}"
    vb=$RV_VERDICT
    rb=$RV_REASON
    if [ "$va" != "$vb" ] || [ "$ra" != "$rb" ]; then
      divergences=$((divergences + 1))
      printf 'DIVERGENCE %d (payload %d of %d)\n' "$divergences" "$((i + 1))" "$n"
      printf 'payload: %s\n' "${CORPUS[$i]}"
      printf 'impl-a: verdict=%s reason=%s\n' "$va" "$ra"
      printf 'impl-b: verdict=%s reason=%s\n' "$vb" "$rb"
    fi
  done
  printf 'corpus %d payloads, %d divergences\n' "$n" "$divergences"
  [ "$divergences" -eq 0 ]
}

main() {
  local mode=${1-}
  case "$mode" in
    --corpus-size)
      setup_work
      build_corpus
      printf '%d\n' "${#CORPUS[@]}"
      return 0
      ;;
    --corpus-stats)
      setup_work
      build_corpus
      printf 'sweep %d\n' "$N_SWEEP"
      printf 'bats-91 %d\n' "$N_B91"
      printf 'bats-93 %d\n' "$N_B93"
      printf 'generated %d\n' "$N_GEN"
      count_tools
      printf 'write %d\n' "$N_WRITE"
      printf 'edit %d\n' "$N_EDIT"
      printf 'multiedit %d\n' "$N_MEDIT"
      printf 'excluded %d\n' "${#EXCL[@]}"
      printf 'total %d\n' "${#CORPUS[@]}"
      return 0
      ;;
    --corpus-dump)
      setup_work
      build_corpus
      printf '%s\n' "${CORPUS[@]}"
      [ "${#EXCL[@]}" -eq 0 ] || printf '%s\n' "${EXCL[@]}"
      return 0
      ;;
    --builders)
      discover_builders
      local i
      for i in "${!B_NAMES[@]}"; do
        printf '%s %s %s\n' "${B_NAMES[i]}" "${B_TOOLS[i]}" "${B_ARITY[i]}"
      done
      return 0
      ;;
  esac
  [ "$#" -ge 2 ] && [ "$#" -le 3 ] || {
    usage
    exit 2
  }
  IMPL_A=$1
  IMPL_B=$2
  [ -r "$IMPL_A" ] || fault "impl-a is not readable: $IMPL_A"
  [ -r "$IMPL_B" ] || fault "impl-b is not readable: $IMPL_B"
  setup_work
  if [ "$#" -eq 3 ]; then
    load_corpus_file "$3"
  else
    build_corpus
  fi
  compare
}

main "$@"
