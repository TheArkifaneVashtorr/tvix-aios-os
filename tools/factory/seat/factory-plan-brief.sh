#!/usr/bin/env bash
# factory-plan-brief <spec> <out> [--since YYYY-MM-DD] [--date YYYY-MM-DD]
#
# Composes the planning packet handed to the planning agent (plan
# 2026-09-06-planning-agent, P2): thirteen mechanical evidence parts, in a
# fixed order, then the driver's contract (FIELD), the operator model, the
# target spec (sized), the rubric, the checklist and the rules. It prints the
# brief to stdout and refuses a broken graph, so a plan is never drafted
# against a tree whose check already fails.
#
# Every command-backed part captures stdout ALONE into its fence; that part's
# stderr is captured to a per-part file, stripped of nix's own noise
# (^warning: Git tree .* is dirty$ and ^evaluation warning:), and whatever
# remains is printed under the part as a second fence headed `stderr:` (or
# nothing when empty). The whole packet is composed into a temp file and
# printed only after the last part succeeded, so a refusal never leaks a
# partial packet on stdout.
#
# FACTORY_TOOLBOX_REPO is the tree the packet reads; it defaults to the repo
# this script lives in. The interpreter for the tree's Python tools is
# FACTORY_PYTHON3_CMD when set, else the toolbox devShell python (factory_py).
#
# Exit codes: 0 the brief printed; 2 refusal (a malformed spec/out path, a
# malformed --since/--date, or an unsound graph) with nothing on stdout; 3 a
# mandatory part's file is missing/unreadable, or a part failed mid-packet,
# with nothing on stdout.
set -euo pipefail

here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# The tree this packet reads defaults to the repo the script lives in (not
# factory-lib.sh's hard-coded toolbox default), so set it BEFORE sourcing the
# lib, whose own `:-` default would otherwise win.
: "${FACTORY_TOOLBOX_REPO:=$(cd -- "$here/../../.." && pwd -P)}"

# shellcheck source=./factory-lib.sh
# shellcheck disable=SC1091
. "$here/factory-lib.sh"

usage() {
  cat <<'USAGE' >&2
usage: factory-plan-brief <spec> <out> [--since YYYY-MM-DD] [--date YYYY-MM-DD]
USAGE
}

[ $# -ge 2 ] || {
  usage
  exit 2
}
spec=$1
out=$2
shift 2

since=
today=
while [ $# -gt 0 ]; do
  case $1 in
    --since)
      [ $# -ge 2 ] || factory_die 2 "--since needs a value"
      since=$2
      shift 2
      ;;
    --date)
      [ $# -ge 2 ] || factory_die 2 "--date needs a value"
      today=$2
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

# A calendar date is exactly YYYY-MM-DD; anything else (e.g. `notadate`) is a
# refusal, never a silent degrade or a `date` fault.
is_date() {
  [[ $1 =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]
}
if [ -n "$today" ] && ! is_date "$today"; then
  printf 'factory-plan-brief: --date must be YYYY-MM-DD: %s\n' "$today" >&2
  exit 2
fi
today=${today:-$(date -u +%F)}
if [ -n "$since" ] && ! is_date "$since"; then
  printf 'factory-plan-brief: --since must be YYYY-MM-DD: %s\n' "$since" >&2
  exit 2
fi
since=${since:-$(date -u -d "$today - 7 days" +%F)}

# <spec> must sit under docs/superpowers/specs/ and <out> under
# docs/reviews/plan-drafts/ relative to the tree (outside the graph's glob by
# construction, so a draft can never become a phantom task). Resolve with
# realpath -m so a traversing `../..` path is refused rather than accepted by
# a bare prefix match.
tree_root=$(realpath -m -- "$FACTORY_TOOLBOX_REPO")
spec_canon=$(realpath -m -- "$tree_root/$spec")
out_canon=$(realpath -m -- "$tree_root/$out")
case $spec_canon in
  "$tree_root/docs/superpowers/specs/"*) ;;
  *)
    printf 'factory-plan-brief: spec must be under docs/superpowers/specs/\n' >&2
    exit 2
    ;;
esac
case $out_canon in
  "$tree_root/docs/reviews/plan-drafts/"*) ;;
  *)
    printf 'factory-plan-brief: out must be under docs/reviews/plan-drafts/\n' >&2
    exit 2
    ;;
esac

cd -- "$FACTORY_TOOLBOX_REPO"

# ---------------------------------------------------------------------------
# Whole or nothing: before any part runs, every file the packet will read must
# exist and be readable. List every missing one on stderr and exit 3.
# ---------------------------------------------------------------------------
missing=0
for f in \
  "$spec" \
  pkgs/evidence/tasks.py \
  pkgs/evidence/claims.py \
  docs/MAP.md \
  docs/OPERATIONS.md \
  docs/ledger/routing.toml \
  docs/ledger/claims.toml \
  tools/factory/seat/factory-task \
  tools/factory/seat/factory-wave \
  tools/factory/seat/factory-integrate \
  tools/factory/seat/factory-dispatch \
  tools/factory/seat/factory-brief; do
  if [ ! -r "$f" ]; then
    if [ "$f" = "$spec" ]; then
      printf 'factory-plan-brief: no such spec: %s\n' "$f" >&2
    else
      printf 'factory-plan-brief: no such command: %s\n' "$f" >&2
    fi
    missing=1
  fi
done
[ "$missing" -eq 0 ] || exit 3

py_label=${FACTORY_PYTHON3_CMD:-"nix develop -c python3"}
design=docs/superpowers/specs/2026-09-05-planning-agent-design.md
live_repo=/home/dalhaka/nixos-agent-env

# The one dated stamp the packet carries at the top.
stamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# The packet is composed into a temp file and only printed at the very end,
# so a mid-packet failure leaves stdout empty. Sidely, the per-part capture
# files lock streams apart there too.
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/factory-plan-brief.XXXXXX")
packet=$tmpdir/packet
trap 'rm -rf -- "$tmpdir"' EXIT

# Emit one part's heading (with the command verbatim) and its TS line.
part() {
  printf '## %s\n' "$1"
  printf 'TS: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}

# Strip nix's own stderr noise; everything else passes through.
filter_noise() {
  awk '/^warning: Git tree .* is dirty$/ { next }
       /^evaluation warning:/ { next }
       { print }'
}

# Run "$@" with stdout and stderr captured into separate files. Sets CAP_OUT
# (exact stdout), CAP_ERR (stderr minus nix noise), and CAP_RC (exit code).
# Never aborts: the caller inspects CAP_RC.
capture() {
  CAP_OUT=$tmpdir/cap.out
  CAP_ERR=$tmpdir/cap.err
  CAP_RAW=$tmpdir/cap.raw
  set +e
  "$@" >"$CAP_OUT" 2>"$CAP_RAW"
  CAP_RC=$?
  set -e
  filter_noise <"$CAP_RAW" >"$CAP_ERR"
  rm -f -- "$CAP_RAW"
}

emit_stdout_fence() {
  printf '~~~\n'
  cat -- "$CAP_OUT"
  printf '~~~\n'
}

emit_stderr_fence() {
  if [ -s "$CAP_ERR" ]; then
    printf 'stderr:\n'
    printf '~~~\n'
    cat -- "$CAP_ERR"
    printf '~~~\n'
  fi
}

# Run a hard part: a graph-reader that only ever fails when the tree is worse
# than M1 reported. Abort exit 3, naming the part, with nothing on stdout.
run_hard() {
  local name=$1
  shift
  capture "$@"
  if [ "$CAP_RC" -ne 0 ]; then
    printf 'factory-plan-brief: part %s failed\n' "$name" >&2
    exit 3
  fi
}

# ---------------------------------------------------------------------------
# M1 -- the graph soundness gate: `tasks.py check` exits 0 iff the graph is
# sound (its diagnostics go to stderr, and only when unsound). A sound check is
# the only way the packet is emitted at all; a refusal keeps stdout empty.
# ---------------------------------------------------------------------------
capture factory_py pkgs/evidence/tasks.py --root . check
if [ "$CAP_RC" -ne 0 ]; then
  printf 'factory-plan-brief: refusing — the graph is not sound:\n' >&2
  cat -- "$CAP_ERR" >&2
  exit 2
fi

{
  # Only now, with nothing else emitted, does the packet begin.
  printf '# Planning packet — %s — spec %s — out %s\n\n' "$stamp" "$spec" "$out"
  part "M1 — $py_label pkgs/evidence/tasks.py --root . check"
  printf 'checkEmpty: true\n\n'

  # M2 -- the task brief.
  part "M2 — $py_label pkgs/evidence/tasks.py --root . brief"
  run_hard M2 factory_py pkgs/evidence/tasks.py --root . brief
  emit_stdout_fence
  emit_stderr_fence
  printf '\n'

  # M3 -- the graph JSON, byte count only (the exact stdout, trailing newline
  # restored: wc -c reads the file, not a $( ) substitution).
  part "M3 — $py_label pkgs/evidence/tasks.py --root . json"
  run_hard M3 factory_py pkgs/evidence/tasks.py --root . json
  printf '%s bytes\n' "$(wc -c <"$CAP_OUT")"
  printf 'run it yourself in the workspace when you need the graph\n'
  emit_stderr_fence
  printf '\n'

  # M4 -- the wave structure.
  part "M4 — $py_label pkgs/evidence/tasks.py --root . waves --repo nixos-agent-env --json"
  run_hard M4 factory_py pkgs/evidence/tasks.py --root . waves --repo nixos-agent-env --json
  emit_stdout_fence
  emit_stderr_fence
  printf '\n'

  # M5 -- the touch conflicts.
  part "M5 — $py_label pkgs/evidence/tasks.py --root . conflicts"
  run_hard M5 factory_py pkgs/evidence/tasks.py --root . conflicts
  emit_stdout_fence
  emit_stderr_fence
  printf '\n'

  # M6 -- the evidence bundle. Only meaningful when the toolbox tree really is
  # the live host the store describes; otherwise the bundle reports the live
  # host's heads, not this tree's, so it degrades to an explicit notice.
  part "M6 — evidence bundle --markdown"
  if command -v evidence >/dev/null 2>&1; then
    if [ "$(realpath -m -- "$FACTORY_TOOLBOX_REPO")" = "$live_repo" ]; then
      capture evidence bundle --markdown
      emit_stdout_fence
      emit_stderr_fence
    else
      printf 'unavailable: evidence describes the live host, not this tree\n'
    fi
  else
    printf 'unavailable: evidence not on PATH\n'
  fi
  printf '\n'

  # M7 -- claims validation. `silent (exit 0)` only when claims.py ran clean
  # and printed nothing; nix noise on stderr never defeats that, and any real
  # lines land under `stderr:`.
  part "M7 — $py_label pkgs/evidence/claims.py validate docs/ledger/claims.toml --today $today --repo-root ."
  capture factory_py pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$today" --repo-root .
  if [ "$CAP_RC" -eq 0 ] && [ ! -s "$CAP_OUT" ]; then
    printf 'silent (exit 0)\n'
  elif [ -s "$CAP_OUT" ]; then
    emit_stdout_fence
  fi
  emit_stderr_fence
  printf '\n'

  # M8 -- the reset ritual's in-flight view (degradable).
  part "M8 — bash tools/ritual.sh inflight $FACTORY_TOOLBOX_REPO"
  if [ -f "tools/ritual.sh" ]; then
    capture bash tools/ritual.sh inflight "$FACTORY_TOOLBOX_REPO"
    emit_stdout_fence
    emit_stderr_fence
  else
    printf 'unavailable: tools/ritual.sh not found\n'
  fi
  printf '\n'

  # M9 -- the session-start hook (degradable), with FACTORY_RUN unset.
  part "M9 — bash tools/session-start.sh $FACTORY_TOOLBOX_REPO"
  if [ -f "tools/session-start.sh" ]; then
    capture env -u FACTORY_RUN bash tools/session-start.sh "$FACTORY_TOOLBOX_REPO" </dev/null
    emit_stdout_fence
    emit_stderr_fence
  else
    printf 'unavailable: tools/session-start.sh not found\n'
  fi
  printf '\n'

  # M10 -- the MAP.md Checks section verbatim.
  part "M10 — the ## Checks section of docs/MAP.md"
  m10_out=$(awk '/^## Checks/{s=1;print;next} /^## /{s=0} s' docs/MAP.md)
  printf '~~~\n'
  printf '%s\n' "$m10_out"
  printf '~~~\n'
  printf '\n'

  # M11 -- the routing table.
  part "M11 — cat docs/ledger/routing.toml"
  m11_out=$(cat docs/ledger/routing.toml)
  printf '~~~\n'
  printf '%s\n' "$m11_out"
  printf '~~~\n'
  printf '\n'

  # M12 -- recent commits since the cut.
  part "M12 — git log --since=$since --format='%ci%x09%s' | head -80"
  m12_out=$(git log --since="$since" --format='%ci%x09%s' | head -80 || true)
  printf '~~~\n'
  printf '%s\n' "$m12_out"
  printf '~~~\n'
  printf '\n'

  # M13 -- the seat's brief shape, read-only. Run via bash, the way
  # checks.unit's sandbox runs every seat script (no /usr/bin/env there, so a
  # direct exec of factory-brief's `#!/usr/bin/env bash` shebang would fail);
  # the heading carries the command exactly as run.
  part "M13 — bash tools/factory/seat/factory-brief docs/superpowers/plans/2026-09-05-evidence-store.md E1"
  capture bash tools/factory/seat/factory-brief docs/superpowers/plans/2026-09-05-evidence-store.md E1
  emit_stdout_fence
  emit_stderr_fence
  printf '\n'

  # ---------------------------------------------------------------------------
  # FIELD -- the driver's contract, pinned by fixed greps, each pasted with its
  # grep -n line, then the board's START HERE block and the recent board log.
  # ---------------------------------------------------------------------------
  part "FIELD"
  printf '~~~\n'

  printf '$ grep -n "plan=" tools/factory/seat/factory-task\n'
  grep -n 'plan=' tools/factory/seat/factory-task || true

  printf '\n$ grep -n "extract_field" tools/factory/seat/factory-task\n'
  grep -n 'extract_field' tools/factory/seat/factory-task || true

  printf '\n$ grep -n "status=" tools/factory/seat/factory-task\n'
  grep -n 'status=' tools/factory/seat/factory-task || true

  printf '\n$ sed -n "2,17p" tools/factory/seat/factory-integrate\n'
  sed -n '2,17p' tools/factory/seat/factory-integrate

  printf '\n$ grep -n "REFUSED" tools/factory/seat/factory-integrate\n'
  grep -n 'REFUSED' tools/factory/seat/factory-integrate || true

  printf '%s\n' '$ grep -n "factory-dispatch: run %s plan %s groups:" tools/factory/seat/factory-dispatch'
  grep -n 'factory-dispatch: run %s plan %s groups:' tools/factory/seat/factory-dispatch || true

  printf "\n\$ awk '/^## START HERE/{s=1;print;next} s&&/^## /{exit} s' docs/OPERATIONS.md\n"
  awk '/^## START HERE/{s=1;print;next} s&&/^## /{exit} s' docs/OPERATIONS.md

  printf '\n$ board log paragraphs dated >= %s\n' "$since"
  if [ -f docs/board/log-2026-09.md ]; then
    awk -v since="$since" '
      BEGIN { RS=""; FS="\n" }
      {
        first = $1
        if (match(first, /[0-9]{4}-[0-9]{2}-[0-9]{2}/)) {
          d = substr(first, RSTART, RLENGTH)
          if (d >= since) print $0
        }
      }
    ' docs/board/log-2026-09.md
  fi

  printf '~~~\n\n'

  # ---------------------------------------------------------------------------
  # OPERATOR -- the operator model in full, or unavailable.
  # ---------------------------------------------------------------------------
  part "OPERATOR"
  if [ -f "docs/board/operator-model.md" ]; then
    printf '~~~\n'
    cat -- docs/board/operator-model.md
    printf '~~~\n'
  else
    printf 'unavailable: docs/board/operator-model.md not found\n'
  fi
  printf '\n'

  # ---------------------------------------------------------------------------
  # TARGET -- the spec in full, preceded by its word count and size.
  # ---------------------------------------------------------------------------
  part "TARGET"
  words=$(wc -w <"$spec")
  size=$(factory_plan_size "$spec")
  printf 'words: %s\n' "$words"
  printf 'size: %s\n' "$size"
  if [ "$size" = L ]; then
    printf 'refuse: an L spec is split into sub-project plans before any task is typed\n'
  fi
  printf '\n'
  printf '%s\n' '- - - spec follows'
  cat -- "$spec"
  printf '%s\n' '- - - end spec'
  printf '\n'

  # ---------------------------------------------------------------------------
  # RUBRIC -- tools/factory/plan/rubric.md (P5), else the design's 5.1 table.
  # ---------------------------------------------------------------------------
  part "RUBRIC"
  if [ -f "tools/factory/plan/rubric.md" ]; then
    printf '~~~\n'
    cat -- tools/factory/plan/rubric.md
    printf '~~~\n'
  else
    rb_out=
    if [ -f "$design" ]; then
      rb_out=$(awk '/^### 5.1/{s=1} /^### 5.2/{s=0} s' "$design")
    fi
    if [ -n "$rb_out" ]; then
      printf '~~~\n'
      printf '%s\n' "$rb_out"
      printf '~~~\n'
    else
      printf 'unavailable: no rubric.md and no 5.1 table in the design spec\n'
    fi
  fi
  printf '\n'

  # ---------------------------------------------------------------------------
  # CHECKLIST -- the design's Appendix A. Not degradable: a missing Appendix A
  # is a refusal (the checklist is part of the packet), never `unavailable:`.
  # ---------------------------------------------------------------------------
  part "CHECKLIST"
  ck_out=
  if [ -f "$design" ]; then
    ck_out=$(awk '/^## Appendix A/{s=1} /^## Appendix B/{s=0} s' "$design")
  fi
  if [ -n "$ck_out" ]; then
    printf '~~~\n'
    printf '%s\n' "$ck_out"
    printf '~~~\n'
  else
    printf 'factory-plan-brief: no Appendix A in %s\n' "$design" >&2
    exit 3
  fi
  printf '\n'

  # ---------------------------------------------------------------------------
  # RULES -- the fixed contract for the drafting agent.
  # ---------------------------------------------------------------------------
  part "RULES"
  cat <<RULES
- Write only <out>, nothing else in the tree; the draft goes under
  docs/reviews/plan-drafts/.
- Write no line beginning \`### <KEY> (code|docs, XS|S|M) — \` in any other file.
- Never open a transcript, a seat log, dispatch.log, a .dsh-home, or a store
  body.
- No network access.
- Every fact beside its command; anchor text, not line numbers.
- tools/factory/seat/factory-brief <draft> <KEY> is the one seat tool you may
  run, and factory-dispatch only with --dry-run.
- The draft is a draft until the panel says otherwise.
- End with \`FACTORY-RESULT status=done\` and the word count in FACTORY-NOTES.
RULES
} >"$packet"

# Whole packet composed: now, and only now, print it.
cat -- "$packet"

exit 0
