#!/usr/bin/env bats
# tools/orchestrator-guard.sh is the orchestrator's (Claude Code) PreToolUse
# hook (.claude/settings.json): deny-only. Typed plan headings
# (docs/superpowers/plans/*.md, the `### KEY (kind, size) — title` lines the
# task graph reads) are append-only; the operator-only .claude/ritual-override
# may never be written or removed; host mutations (sudo, nixos-rebuild,
# mutating systemctl, writes under the protected prefixes) and history
# rewrites (git commit --amend / push / rebase / reset --hard) are refused.
# The host rules mirror pkgs/dsh-openrouter/hook-guard.py, same wording.

# run --separate-stderr (the malformed-JSON warning test) needs bats >= 1.5.
bats_require_minimum_version 1.5.0

GUARD="$BATS_TEST_DIRNAME/../../tools/orchestrator-guard.sh"

# --- payload builders (python3 is on the sandbox/devShell PATH; the guard
# itself is pure bash and never touches python3) ---
# A Claude Code payload is {"tool_name":"...","tool_input":{...}} on stdin,
# compact and ensure_ascii=False so UTF-8 (the em-dash in headings) stays raw
# bytes the way Claude Code's own Node JSON encoder emits it.
bpayload() { # bpayload COMMAND -> Bash payload
  python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}},ensure_ascii=False,separators=(",",":")))' "$1"
}
wpayload() { # wpayload FILE CONTENT -> Write payload
  python3 -c 'import json,sys;print(json.dumps({"tool_name":"Write","tool_input":{"file_path":sys.argv[1],"content":sys.argv[2]}},ensure_ascii=False,separators=(",",":")))' "$1" "$2"
}
epayload() { # epayload FILE OLD NEW -> Edit payload
  python3 -c 'import json,sys;print(json.dumps({"tool_name":"Edit","tool_input":{"file_path":sys.argv[1],"old_string":sys.argv[2],"new_string":sys.argv[3]}},ensure_ascii=False,separators=(",",":")))' "$1" "$2" "$3"
}
# meditpayload FILE OLD NEW -> MultiEdit payload with a single edit
meditpayload() { # meditpayload FILE OLD NEW
  python3 -c 'import json,sys;print(json.dumps({"tool_name":"MultiEdit","tool_input":{"file_path":sys.argv[1],"edits":[{"old_string":sys.argv[2],"new_string":sys.argv[3]}]}},ensure_ascii=False,separators=(",",":")))' "$1" "$2" "$3"
}

# Run the guard on a payload; stdout in $output, stderr in $stderr. The guard
# resolves the plans path against $CLAUDE_PROJECT_DIR, so point it at the fake
# project the tests build.
run_guard() { run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" <<<"$1"; }

# Run the guard on a payload from a fake seat workspace (NOT the tree): the
# guard must still refuse a write to its own absolute path (SELF_CANON), even
# though CLAUDE_PROJECT_DIR points elsewhere. This is the discriminating fixture
# OG3b item 1 lives on — the carried OG3 guard allows every one of these.
run_guard_ws() { run --separate-stderr env CLAUDE_PROJECT_DIR="$WS" bash "$GUARD" <<<"$1"; }

# Assert $1 (the guard's stdout) is the deny decision JSON with a non-empty
# reason. Uses a direct python3 pipe (not `run`) so it does not clobber the
# test's own $output/$status for the substring assertions that follow.
denied() {
  printf '%s' "$1" | python3 -c 'import json,sys;o=json.load(sys.stdin);h=o["hookSpecificOutput"];assert h["hookEventName"]=="PreToolUse" and h["permissionDecision"]=="deny" and h["permissionDecisionReason"], o'
}

# fault_run FN PAYLOAD — source the guard, override FN (one of the guard's own
# functions) with a body that reads an unbound variable (fatal under `set -u`),
# then run `main` on PAYLOAD. Because no guard function is ever called inside a
# command substitution, the fault kills the main shell; `main` installs the EXIT
# trap as its first statement (the entry path), which must DENY — never allow.
# FN is whitelisted so the interpolation into the `bash -c` script cannot execute
# arbitrary text.
fault_run() {
  local fn=$1 payload=$2
  case "$fn" in
    bash_verdict | git_verdict | write_verdict | json_unescape | resolve_path | \
    missing_headings | apply_edit | is_plan_file) : ;;
    *) return 1 ;;
  esac
  # shellcheck disable=SC2016
  run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" bash -c '
    # shellcheck disable=SC1091
    source "$1"
    '"$fn"'() { local x=$GUARD_FAULT_VAR; : "$x"; }
    main <<< "$2"
  ' _ "$GUARD" "$payload"
}

# guard_tokens COMMAND — the guard's own token stream for COMMAND (one token per
# line), by sourcing the guard (its `main` runs only when executed, not sourced)
# and calling its normalise/pad/tokenise directly. The one-token assertion for
# `echo "a'b"` (MINOR 17) needs the tokeniser observable.
guard_tokens() {
  # shellcheck disable=SC1091
  source "$GUARD"
  local -a toks
  normalise_command "$1"
  local c=$_ret
  pad_operators "$c"
  c=$_ret
  tokenise "$c" toks
  printf '%s\n' "${toks[@]}"
}

setup() {
  PROJECT="$BATS_TEST_TMPDIR/project"
  PLANS_DIR="$PROJECT/docs/superpowers/plans"
  mkdir -p "$PLANS_DIR"
  PLAN="$PLANS_DIR/test.md"
  cat >"$PLAN" <<'EOF'
# Test plan

### A1 (code, S) — first task

body one line

### B2 (docs, S) — second task

body two line
EOF
  # OG3b: the guard's own absolute path and a fake seat workspace that is NOT
  # the tree (SELF_CANON must protect the guard independent of CLAUDE_PROJECT_DIR).
  GUARD_ABS="$(realpath "$GUARD")"
  WS="$BATS_TEST_TMPDIR/ws"
  mkdir -p "$WS"
}

# --- Bash host rules (mirror hook-guard.py's wording) ---

@test "bash: sudo is denied" {
  p=$(bpayload "sudo nixos-rebuild switch")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"sudo is refused (an operator action)"* ]]
}

@test "bash: nixos-rebuild is denied" {
  p=$(bpayload "nixos-rebuild switch --flake .#core")
  run_guard "$p"
  denied "$output"
  [[ "$output" == *"nixos-rebuild is refused (an operator action)"* ]]
}

@test "bash: mutating systemctl is denied" {
  p=$(bpayload "systemctl restart nginx")
  run_guard "$p"
  denied "$output"
  [[ "$output" == *"systemctl restart is refused (an operator action)"* ]]
}

@test "bash: git history rewrites are denied" {
  for cmd in "git commit --amend" "git push" "git rebase" "git reset --hard origin/main"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"history rules of the house"* ]]
  done
}

@test "bash: a write under a protected prefix is denied" {
  p=$(bpayload "echo hi > /var/lib/helm/x")
  run_guard "$p"
  denied "$output"
  [[ "$output" == *"/var/lib/helm"* ]]
}

@test "bash: safe commands are allowed" {
  for cmd in "git status" "nix build .#checks.x86_64-linux.unit" "systemctl status helm-serve" "ls /run/baskets"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: git global options do not hide history rewrites" {
  for cmd in "git -c core.editor=true commit --amend" "git -C /home/x push" "git --no-pager rebase -i" "git -c a=b -C . reset --hard"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"history rules of the house"* ]]
  done
}

@test "bash: git global options before a safe subcommand are allowed" {
  for cmd in "git -c a=b status" "git -C . log"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

# --- git tokeniser (design change 1): any global option, any spelling ---
# The git rule is a tokeniser, not a flag list: every `git` word at a command
# position is walked forward to its subcommand, skipping *any* `-…` option (and
# the value of the value-taking long options in their space-separated form), so
# an unenumerated option can never hide a history rewrite.

@test "bash: git tokeniser denies a history rewrite behind any global option" {
  local -a cmds=(
    "git --work-tree=. commit --amend"
    "git -P commit --amend"
    "git --literal-pathspecs commit --amend"
    "git --exec-path=/x commit --amend"
    "git --no-replace-objects push"
    "git --namespace=n push"
    "git --icase-pathspecs rebase -i"
    "git -c a=b -C . reset --hard"
    "/run/current-system/sw/bin/git commit --amend"
    "command git commit --amend"
    '\git commit --amend'
    "GIT_EDITOR=true git commit --amend"
    "git   commit   --amend"
    $'git commit \\\n--amend'
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"history rules of the house"* ]]
  done
}

@test "bash: git tokeniser keeps the positive controls allowed" {
  local -a cmds=(
    "git --work-tree=. status"
    "git -c a=b log -1"
    "git -P diff"
    "git --no-pager show"
    "git commit -F msg"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: git push is denied outright, even --dry-run" {
  p=$(bpayload "git push --dry-run")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"history rules of the house"* ]]
}

@test "bash: sudo in prose is allowed" {
  for cmd in "grep -rn sudo docs/brief.md" "echo 'never sudo here'"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: sudo in command position is denied" {
  for cmd in "sudo x" "x; sudo y" "x && sudo y" "(sudo y)"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
  done
}

@test "bash: writes via tee -a, cp, mv, install and wide redirect are denied" {
  for cmd in "echo x | tee -a /var/lib/secrets/y" "cp k /run/baskets/x" "mv k /var/lib/lanes/x" "install -m600 k /var/lib/secrets/x" "echo x >  /var/lib/helm/x"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
  done
}

@test "bash: reading FROM a protected path is allowed (MINOR 9)" {
  for cmd in "cp /var/lib/secrets/x /tmp/y" "mv /var/lib/lanes/x /tmp/y" "install /var/lib/secrets/x /tmp/y"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

# --- plan files change only through Edit/Write (design change 2) ---

@test "bash: a shell write to a plan file is denied" {
  local -a cmds=(
    "sed -i 's/x/y/' docs/superpowers/plans/x.md"
    "rm docs/superpowers/plans/x.md"
    "mv a docs/superpowers/plans/x.md"
    "cp a docs/superpowers/plans/x.md"
    "echo x > docs/superpowers/plans/x.md"
    "truncate -s 0 docs/superpowers/plans/x.md"
    "printf x | tee docs/superpowers/plans/x.md"
    "cat > docs/superpowers/plans/../plans/x.md"
    "perl -i -pe 's/x/y/' docs/superpowers/plans/x.md"
    "git checkout -- docs/superpowers/plans/x.md"
    "git restore docs/superpowers/plans/x.md"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
  done
}

@test "bash: a python heredoc writing to a plan file is denied" {
  cmd=$'nix develop -c python3 - <<\x27PY\x27\nfrom pathlib import Path\nPath("docs/superpowers/plans/x.md").write_text("x")\nPY'
  p=$(bpayload "$cmd")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
}

@test "bash: a python -c open(..., w) on a plan file is denied" {
  cmd="python3 -c \"open('docs/superpowers/plans/x.md', 'w').write('x')\""
  p=$(bpayload "$cmd")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
}

@test "bash: read-only verbs on a plan file are allowed" {
  local -a cmds=(
    "cat docs/superpowers/plans/x.md"
    "grep -n '^### ' docs/superpowers/plans/x.md"
    "sed -n 1,5p docs/superpowers/plans/x.md"
    "head docs/superpowers/plans/x.md"
    "tail docs/superpowers/plans/x.md"
    "diff a docs/superpowers/plans/x.md"
    "wc -l docs/superpowers/plans/x.md"
    "git diff -- docs/superpowers/plans/x.md"
    "git show HEAD:docs/superpowers/plans/x.md"
    "git log -- docs/superpowers/plans/x.md"
    "cp docs/superpowers/plans/x.md /tmp/y"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

# --- no command position: every token is scanned ---
# The guard folds a command to a flat token stream (continuations, newlines,
# tabs and quotes to spaces; shell separators to tokens) and scans *every* token
# for a `git` (basename) invocation or a write verb — a launcher prefix, a
# newline, or a `;`/`&&`/`||` cannot hide a refused subcommand or write. The
# guard is deny-only and deliberately over-denies.

@test "bash: a git rewrite across a newline is denied" {
  local -a cmds=(
    $'cd /x\ngit commit --amend'
    $'set -e\ngit push origin main'
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"history rules of the house"* ]]
  done
}

@test "bash: a launcher prefix does not hide a git rewrite" {
  local -a cmds=(
    "nix develop -c git commit --amend"
    "timeout 5 git push"
    "nohup git push"
    'bash -c "git push"'
    '`git push`'
    "git status; git push"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"history rules of the house"* ]]
  done
}

@test "bash: a launcher, newline or extra writer does not hide a plan write" {
  local -a cmds=(
    $'echo a\nrm docs/superpowers/plans/x.md'
    "nix develop -c rm docs/superpowers/plans/x.md"
    "xargs rm docs/superpowers/plans/x.md"
    "cp k docs/superpowers/plans/x.md && echo done"
    "install -m644 k docs/superpowers/plans/x.md"
    "dd of=docs/superpowers/plans/x.md"
    "ln -sf k docs/superpowers/plans/x.md"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
  done
}

@test "bash: no command position — the allow cases stay allowed" {
  local -a cmds=(
    "git status; git log"
    "nix develop -c pytest tests/evidence -q"
    "nix develop -c python3 pkgs/evidence/tasks.py --root . check"
    "grep -rn amend docs/reviews"
    "cat docs/superpowers/plans/x.md | wc -l"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

# --- typed-heading append-only rule ---

@test "edit: removing a typed heading is denied" {
  p=$(epayload "$PLAN" $'### A1 (code, S) — first task\n' "")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"typed task headings are append-only"* ]]
}

@test "edit: rewriting a typed heading is denied" {
  p=$(epayload "$PLAN" "### A1 (code, S) — first task" "### A1 (code, S) — first task, renamed")
  run_guard "$p"
  denied "$output"
}

@test "edit: appending a new section is allowed" {
  p=$(epayload "$PLAN" "body two line" $'body two line\n\n### C3 (code, S) — third task\n\nbody three')
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "edit: editing body text under a heading is allowed" {
  p=$(epayload "$PLAN" "body one line" "body one line, edited")
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "write: dropping a typed heading is denied" {
  content=$'# Test plan\n\n### B2 (docs, S) — second task\n\nbody two line\n'
  p=$(wpayload "$PLAN" "$content")
  run_guard "$p"
  denied "$output"
}

@test "write: appending a section is allowed" {
  content=$'# Test plan\n\n### A1 (code, S) — first task\n\nbody one line\n\n### B2 (docs, S) — second task\n\nbody two line\n\n### C3 (code, S) — third task\n'
  p=$(wpayload "$PLAN" "$content")
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "multiedit: removing a typed heading is denied" {
  p=$(meditpayload "$PLAN" $'### A1 (code, S) — first task\n' "")
  run_guard "$p"
  denied "$output"
}

@test "multiedit: an escaped quote in old_string does not bypass heading removal" {
  local quoted
  quoted="$PLANS_DIR/quoted.md"
  printf '# p\nsay "hi"\n### A1 (code, S) — first task\n' >"$quoted"
  p=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"MultiEdit","tool_input":{"file_path":sys.argv[1],"edits":[{"old_string":"say \"hi\"\n### A1 (code, S) — first task","new_string":"say \"hi\""}]}},ensure_ascii=False,separators=(",",":")))' "$quoted")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
}

@test "an edit outside the plans directory is allowed" {
  other="$PROJECT/docs/other.md"
  printf '# x\n\n### A1 (code, S) — first task\n' >"$other"
  p=$(epayload "$other" "### A1 (code, S) — first task" "### A1 (code, S) — gone")
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "edit: a .. segment into the plans dir is still denied" {
  p=$(epayload "$PLANS_DIR/../plans/test.md" $'### A1 (code, S) — first task\n' "")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
}

@test "edit: a ./ segment into the plans dir is still denied" {
  p=$(epayload "$PROJECT/docs/superpowers/./plans/test.md" $'### A1 (code, S) — first task\n' "")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
}

@test "edit: a symlink into the plans dir is still denied" {
  ln -s "$PLAN" "$PROJECT/link.md"
  p=$(epayload "$PROJECT/link.md" $'### A1 (code, S) — first task\n' "")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
}

@test "edit: a symlinked project dir still denies a heading edit (MINOR 10)" {
  local link="$BATS_TEST_TMPDIR/proj-link"
  ln -s "$PROJECT" "$link"
  p=$(epayload "$PLAN" $'### A1 (code, S) — first task\n' "")
  run --separate-stderr env CLAUDE_PROJECT_DIR="$link" bash "$GUARD" <<<"$p"
  [ "$status" -eq 0 ]
  denied "$output"
}

@test "a path that merely contains plans/ outside the plans dir is allowed" {
  other="$PROJECT/docs/notes/plans/x.md"
  mkdir -p "$PROJECT/docs/notes/plans"
  printf '# x\n\n### A1 (code, S) — first task\n' >"$other"
  p=$(epayload "$other" "### A1 (code, S) — first task" "### A1 (code, S) — gone")
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "a non-heading edit inside a plan file is allowed" {
  p=$(epayload "$PLAN" "# Test plan" "# Test plan (edited)")
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "an unknown tool is allowed" {
  run_guard '{"tool_name":"Read","tool_input":{"file_path":"'"$PLAN"'"}}'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- failure handling ---

@test "malformed JSON is allowed and warns on stderr" {
  run_guard 'this is not json'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [[ "$stderr" == *"orchestrator-guard"* ]]
}

@test "malformed JSON that starts with { is allowed and warns on stderr" {
  run_guard '{"tool_name":"Bash", broken'
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [[ "$stderr" == *"orchestrator-guard"* ]]
}

@test "empty input is allowed" {
  run_guard ''
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- OG1r2b contract additions (deny-only: an over-denial is accepted) ---

@test "bash: mv taking a plan in ANY operand position is denied" {
  local -a cmds=(
    "mv docs/superpowers/plans/x.md /tmp/x"
    "mv docs/superpowers/plans/x.md ./y"
    "mv -f docs/superpowers/plans/x.md ../x.md"
    "mv docs/superpowers/plans/x.md docs/superpowers/plans/x.md.bak"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
  done
}

@test "bash: the plans directory or an ancestor names every plan for the delete family" {
  local -a cmds=(
    "rm -r docs/superpowers/plans"
    "rm -rf docs/superpowers"
    "rm -rf docs"
    "mv docs/superpowers/plans /tmp/"
    'find docs/superpowers/plans -name "*.md" -delete'
    "git clean -fdx docs/superpowers/plans"
    "git rm docs/superpowers/plans/x.md"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
  done
}

@test "bash: a cd rebases relative plan-write paths" {
  local -a cmds=(
    "cd docs/superpowers/plans && rm x.md"
    "cd docs/superpowers/plans; rm x.md"
    "cd docs/superpowers && rm plans/x.md"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
  done
}

@test "bash: the payload cwd rebases relative plan-write paths" {
  local p
  p=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]},separators=(",",":")))' "rm x.md" "$PLANS_DIR")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
}

@test "bash: sed/perl -i anywhere in the invocation refuses a plan" {
  local -a cmds=(
    "sed -e s/a/b/ -i docs/superpowers/plans/x.md"
    "sed s/a/b/ -i docs/superpowers/plans/x.md"
    "perl -pe s/a/b/ -i docs/superpowers/plans/x.md"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
  done
}

@test "bash: a clobber redirect to a plan is denied" {
  p=$(bpayload "cat k >| docs/superpowers/plans/x.md")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
}

@test "bash: read verbs on the plans directory are allowed" {
  local -a cmds=(
    "ls docs/superpowers/plans"
    "find docs/superpowers/plans -name '*.md'"
    "cd docs/superpowers/plans && cat x.md"
    "git diff -- docs/superpowers/plans/x.md"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: a cd elsewhere does not rebase a plan write into a deny" {
  p=$(bpayload "cd /tmp && rm x.md")
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "bash: a directory merely named plans outside the project is allowed" {
  p=$(bpayload "rm /tmp/plans-not-ours/x.md")
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "bash: quotes strip to nothing so echo \"a'b\" stays one word" {
  local cmd=$'echo "a\'b"'
  run guard_tokens "$cmd"
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | wc -l)" -eq 2 ]
}

@test "timing: a 200-path-token command stays under 100 ms (median of five calls)" {
  local cmd="ls" i p t0 t1
  for ((i = 0; i < 200; i++)); do
    cmd+=" docs/a${i}/b${i}.md"
  done
  p=$(bpayload "$cmd")
  local -a ms
  for _ in 1 2 3 4 5; do
    t0=$EPOCHREALTIME
    printf '%s\n' "$p" | env CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" >/dev/null 2>&1
    t1=$EPOCHREALTIME
    ms+=("$(python3 -c 'import sys;print(int((float(sys.argv[2])-float(sys.argv[1]))*1000))' "$t0" "$t1")")
  done
  local median
  median=$(printf '%s\n' "${ms[@]}" | python3 -c 'import sys;print(sorted(int(x) for x in sys.stdin.read().split())[2])')
  [ "$median" -lt 100 ]
}

@test "timing: a 200-symlink-token command stays under 200 ms (median of five calls)" {
  local i cmd p t0 t1
  for ((i = 0; i < 200; i++)); do
    ln -s .claude/ritual-override "$PROJECT/link$i"
  done
  cmd="ls"
  for ((i = 0; i < 200; i++)); do
    cmd+=" link$i"
  done
  p=$(bpayload "$cmd")
  local -a ms
  for _ in 1 2 3 4 5; do
    t0=$EPOCHREALTIME
    printf '%s\n' "$p" | env CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" >/dev/null 2>&1
    t1=$EPOCHREALTIME
    ms+=("$(python3 -c 'import sys;print(int((float(sys.argv[2])-float(sys.argv[1]))*1000))' "$t0" "$t1")")
  done
  local median
  median=$(printf '%s\n' "${ms[@]}" | python3 -c 'import sys;print(sorted(int(x) for x in sys.stdin.read().split())[2])')
  [ "$median" -lt 200 ]
}

# --- CR2: .claude/ritual-override is the operator's (deny-only) ---
# The operator-only escape hatch (spec §3.4): the guard refuses every write to
# or removal of .claude/ritual-override — Bash (touch, redirects, rm, the copy
# family) and the Edit/Write/MultiEdit path rule — so no agent can create,
# overwrite or delete it; reading it (cat) stays allowed.

@test "bash: writing .claude/ritual-override is denied" {
  local -a cmds=(
    "touch .claude/ritual-override"
    "echo x > .claude/ritual-override"
    "rm .claude/ritual-override"
    "rm -rf .claude/ritual-override"
    "mv k .claude/ritual-override"
    "cp k .claude/ritual-override"
    "echo x > .claude/../.claude/ritual-override"
    "truncate -s 0 .claude/ritual-override"
    "sed -i s/a/b/ .claude/ritual-override"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: reading .claude/ritual-override is allowed" {
  for cmd in "cat .claude/ritual-override" "cp .claude/ritual-override /tmp/y"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "write: the Write tool on .claude/ritual-override is denied" {
  p=$(wpayload ".claude/ritual-override" "allow")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
}

@test "edit: the Edit tool on .claude/ritual-override is denied" {
  p=$(epayload ".claude/ritual-override" "allow" "deny")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
}

@test "multiedit: MultiEdit on .claude/ritual-override is denied" {
  p=$(meditpayload ".claude/ritual-override" "allow" "deny")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
}

# --- OG3: the house guard protects its own file (SD8's gate, MINOR-11) ---
# The guard the seat obeys is read from the mutable checkout, so it must name
# itself in PROTECTED_PATHS as a `file` entry (like the ritual override): a Bash
# payload that writes or removes tools/orchestrator-guard.sh, and an
# Edit/Write/MultiEdit whose file_path lands on it, are refused. Reading it
# (cat, bash it, grep it) stays allowed.

@test "bash: sed -i on tools/orchestrator-guard.sh is denied" {
  p=$(bpayload "sed -i 's/deny/allow/' tools/orchestrator-guard.sh")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "bash: a redirect onto tools/orchestrator-guard.sh is denied" {
  p=$(bpayload "printf x > tools/orchestrator-guard.sh")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "bash: cp onto tools/orchestrator-guard.sh is denied but reading from it is allowed" {
  p=$(bpayload "cp /tmp/g.sh tools/orchestrator-guard.sh")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
  p=$(bpayload "cp tools/orchestrator-guard.sh /tmp/g.sh")
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "bash: rm tools/orchestrator-guard.sh is denied with the file reason" {
  p=$(bpayload "rm tools/orchestrator-guard.sh")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "write/edit: the Write and Edit tools on tools/orchestrator-guard.sh are denied" {
  p=$(wpayload "tools/orchestrator-guard.sh" "allow")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
  p=$(epayload "tools/orchestrator-guard.sh" "allow" "deny")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "bash: reading tools/orchestrator-guard.sh is allowed" {
  for cmd in "bash tools/orchestrator-guard.sh" "grep -n PROTECTED tools/orchestrator-guard.sh"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

# --- OG3b: the guard protects the file it executes from, whatever the project ---
# SELF_CANON = realpath of the guard's own source. From a seat the project is the
# WORKSPACE, not the checkout, so the relative tools/orchestrator-guard.sh entry
# covers the wrong copy: a payload naming the guard by its absolute path (or a
# spelling that resolves to it) must still deny. A copy elsewhere — a scratch
# clone's own orchestrator-guard.sh — is a different file and stays allowed.

@test "bash: a redirect onto the guard's own absolute path is denied from the fake workspace" {
  p=$(bpayload "printf x > $GUARD_ABS")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "bash: sed -i on the guard's own absolute path is denied from the fake workspace" {
  p=$(bpayload "sed -i s/a/b/ $GUARD_ABS")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "bash: cp onto the guard's absolute path is denied but reading from it is allowed" {
  p=$(bpayload "cp /tmp/g.sh $GUARD_ABS")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
  p=$(bpayload "cp $GUARD_ABS /tmp/g.sh")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "bash: rm -f the guard's own absolute path is denied from the fake workspace" {
  p=$(bpayload "rm -f $GUARD_ABS")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "write/edit: the Write and Edit tools on the guard's absolute path are denied" {
  p=$(wpayload "$GUARD_ABS" "allow")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
  p=$(epayload "$GUARD_ABS" "allow" "deny")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "bash: reading the guard's own absolute path is allowed" {
  for cmd in "cat $GUARD_ABS" "bash $GUARD_ABS" "grep -n PROTECTED $GUARD_ABS"; do
    p=$(bpayload "$cmd")
    run_guard_ws "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: a write to a different orchestrator-guard.sh elsewhere is allowed" {
  p=$(bpayload "printf x > $BATS_TEST_TMPDIR/other/orchestrator-guard.sh")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "bash: ~/ and \$HOME/ spellings of the guard's path are denied from the fake workspace" {
  local home
  home="$(dirname "$(dirname "$GUARD_ABS")")"
  p=$(bpayload 'printf x > $HOME/tools/orchestrator-guard.sh')
  run --separate-stderr env CLAUDE_PROJECT_DIR="$WS" HOME="$home" bash "$GUARD" <<<"$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
  p=$(bpayload 'printf x > ~/tools/orchestrator-guard.sh')
  run --separate-stderr env CLAUDE_PROJECT_DIR="$WS" HOME="$home" bash "$GUARD" <<<"$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "bash: rm -rf tools denies naming the guard (the ancestor-branch reason)" {
  p=$(bpayload "rm -rf tools")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "bash: rm -rf tools/* denies naming the guard (the raw-text fallback reason)" {
  p=$(bpayload "rm -rf tools/*")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

@test "bash: xargs rm < tools/list denies naming the guard, not the ritual override" {
  p=$(bpayload "xargs rm < tools/list")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
  [[ "$output" != *"ritual override"* ]]
}

# --- OG3r: ${HOME} reaches the realpath rule; SELF_CANON under the trap ---
# ${HOME}/… is split at the braces by the old tokeniser (the `{`/`}` operator
# arm), so lex_norm's ${HOME}/ arm is dead code and a seat could still write the
# live guard by the ${HOME}/… spelling. The tokeniser must keep a parameter
# expansion ${NAME} inside its one word (a `{` immediately preceded by `$` opens
# an expansion that ends at the matching `}`; a bare {a,b} brace expansion is
# unchanged). HOME is the tree root, so ${HOME}/tools/… canonicalises to the
# guard's own absolute path.

@test "bash: the \${HOME} spellings of the guard's path are denied from the fake workspace" {
  local home
  home="$(dirname "$(dirname "$GUARD_ABS")")"
  p=$(bpayload 'printf x > ${HOME}/tools/orchestrator-guard.sh')
  run --separate-stderr env CLAUDE_PROJECT_DIR="$WS" HOME="$home" bash "$GUARD" <<<"$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
  p=$(bpayload 'printf x > "${HOME}"/tools/orchestrator-guard.sh')
  run --separate-stderr env CLAUDE_PROJECT_DIR="$WS" HOME="$home" bash "$GUARD" <<<"$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
  p=$(bpayload 'rm -rf ${HOME}/tools')
  run --separate-stderr env CLAUDE_PROJECT_DIR="$WS" HOME="$home" bash "$GUARD" <<<"$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

# --- OG3r: an unquoted ${HOME} spelling with no braces is left strictly alone
# (a brace-expansion token {a,b} stays split) so a write to an unrelated path is
# never mis-joined into one word ---

@test "bash: a bare brace expansion stays split, never joins \${HOME}" {
  p=$(bpayload "printf x > /tmp/{a,b}/orchestrator-guard.sh")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- OG3r: SELF_CANON is resolved inside main after the EXIT trap is installed
# (never at source time, never in a subshell inside a rule function), and a
# realpath failure reaches the trap's fail-closed deny before an empty file_dirs
# entry can be consumed. A fake realpath exiting 1 (prepended to PATH) must
# fault-deny with the guard-fault reason, not the protected-path wording. ---

@test "bash: a realpath failure fault-denies before an empty file_dirs entry" {
  local bin="$BATS_TEST_TMPDIR/fakebin"
  mkdir -p "$bin"
  printf '#!/bin/sh\nexit 1\n' > "$bin/realpath"
  chmod +x "$bin/realpath"
  p=$(bpayload "printf x > tools/orchestrator-guard.sh")
  run --separate-stderr env PATH="$bin:$PATH" CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" <<<"$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$output" != *"orchestrator-guard.sh is the operator's"* ]]
}

# --- OG3r: the python/perl write-spelling scan carries SELF_CANON as a needle
# beside the relative names, so `python3 -c "open('<abs>', 'w')"` — whose path is
# buried inside open(), invisible to the token==file_canons comparison — still
# refuses the guard's own absolute path from a fake workspace. ---

@test "bash: a python open(...,'w') of the guard's absolute path is denied from the fake workspace" {
  p=$(bpayload "python3 -c \"open('$GUARD_ABS', 'w')\"")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

# --- OG3r: SELF_CANON's parent stays in file_dirs (the safe direction — a
# deny-only guard may widen), so the descendant/glob branch names the tree's
# tools/ dir even when the project is the fake workspace. ---

@test "bash: rm -rf of the tree's tools/* is denied from the fake workspace" {
  local treeroot
  treeroot="$(dirname "$(dirname "$GUARD_ABS")")"
  p=$(bpayload "rm -rf $treeroot/tools/*")
  run_guard_ws "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"orchestrator-guard.sh"* ]]
}

# --- CR2b: the override is protected the way the plans dir is (deny-only) ---
# The review's four majors. The override rule must treat .claude (and every
# ancestor down to the project and /) as naming the file for the delete family,
# admit `dd of=…` into the token scan, and match python/perl removal spellings.

@test "bash: the delete family naming .claude or an ancestor of the override denies" {
  local -a cmds=(
    "rm -rf .claude"
    "rm -r .claude/"
    "mv .claude .claude-old"
    "mv .claude/ritual-override /tmp/x"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: rm -rf . and find -exec naming . deny (plan rule: . is a plans ancestor too)" {
  local -a cmds=(
    "rm -rf ."
    "find . -name ritual-override -exec rm {} +"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
  done
}

@test "bash: git clean/checkout/restore naming .claude or bare denies" {
  local -a cmds=(
    "git clean -fd"
    "git clean -fdx .claude"
    "git checkout -- .claude"
    "git restore .claude"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: find .claude -delete denying the override" {
  p=$(bpayload "find .claude -name 'ritual-*' -delete")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
}

@test "bash: dd of= the override denies (the of= value is admitted into the scan)" {
  p=$(bpayload "dd if=/dev/null of=.claude/ritual-override")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
}

@test "bash: python removal spellings naming the override deny" {
  local -a cmds=(
    "python3 -c 'import os; os.remove(\".claude/ritual-override\")'"
    "python3 -c 'import os; os.unlink(\".claude/ritual-override\")'"
    "python3 -c 'from pathlib import Path; Path(\".claude/ritual-override\").unlink()'"
    "python3 -c 'import os; os.rename(\".claude/ritual-override\", \"/tmp/x\")'"
    "python3 -c 'import os; os.replace(\".claude/ritual-override\", \"/tmp/x\")'"
    "python3 -c 'import shutil; shutil.move(\".claude/ritual-override\", \"/tmp/x\")'"
    "python3 -c 'import shutil; shutil.rmtree(\".claude\")'"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: a cd rebases a relative override path" {
  local -a cmds=(
    "cd .claude && rm ritual-override"
    "cd sub && rm ../.claude/ritual-override"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: the payload cwd in .claude rebases a relative override path" {
  local p
  p=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","cwd":sys.argv[1],"tool_input":{"command":"rm ritual-override"}},separators=(",",":")))' "$PROJECT/.claude")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
}

@test "bash: rm through a symlink to the override denies" {
  ln -s .claude/ritual-override "$PROJECT/link-to-override"
  p=$(bpayload "rm link-to-override")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
}

@test "write/edit/multiedit: the absolute override path is denied" {
  local abs="$PROJECT/.claude/ritual-override"
  run_guard "$(wpayload "$abs" "allow")"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
  run_guard "$(epayload "$abs" "allow" "deny")"
  [ "$status" -eq 0 ]
  denied "$output"
  run_guard "$(meditpayload "$abs" "allow" "deny")"
  [ "$status" -eq 0 ]
  denied "$output"
}

@test "bash: reads and safe verbs on .claude allow (no over-denial of siblings)" {
  local -a cmds=(
    "ls -la .claude"
    "cat .claude/ritual-override"
    "stat .claude/ritual-override"
    "git status"
    "test -f .claude/ritual-override"
    "rm -rf .claude/worktrees/x"
    "rm /tmp/other/.claude/ritual-override"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

# --- CR2r: glob spellings, the widened delete family, narrowed pathless git ---

@test "bash: the eight glob spellings of .claude deny the override (raw-text fallback)" {
  local -a cmds=(
    "rm -rf .claude/*"
    "rm -rf .claude/*/"
    "rm -rf $PROJECT/.claude/*"
    "mv .claude/* /tmp/"
    "shred .claude/*"
    "rm -rf .claude/ritual*"
    "rm .claude/[r]itual-override"
    "rm -rf .claude/?itual-override"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: git stash -u / tar -C / chmod / xargs delete verb deny the override" {
  local -a cmds=(
    "git stash -u"
    "git stash --include-untracked"
    "git stash -a"
    "tar -C .claude -xf /tmp/a.tar"
    "chmod 000 .claude/ritual-override"
    "chown root .claude/ritual-override"
    "chattr +i .claude/ritual-override"
    "xargs rm < .claude/list"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: pathless git clean/checkout/restore that delete nothing allow" {
  local -a cmds=(
    "git clean -n"
    "git clean -nd"
    "git clean"
    "git checkout main"
    "git checkout -b task/x"
    "git checkout"
    "git restore --staged k"
    "git stash"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: git clean -f and checkout/restore of a protected path deny" {
  local -a cmds=(
    "git clean -f"
    "git clean -fd"
    "git checkout -- .claude"
    "git restore .claude"
    "git checkout ."
    "git checkout --"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: a git commit -m message is prose and never scanned (deny-only over-denial withdrawn)" {
  local -a cmds=(
    "git commit -m 'guard: rm -rf .claude no longer allowed'"
    "git commit -q -m 'docs: git clean and mv of .claude are refused'"
    "git commit -m 'rm .claude/ritual-override happens in the operator path'"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "a third protected file entry in the list is honoured (no early break)" {
  # shellcheck disable=SC1091
  source "$GUARD"
  PROTECTED_PATHS+=('elsewhere/secret.txt|file')
  write_verdict "rm -rf elsewhere/secret.txt" "$PROJECT" ""
  local reason=$_ret
  [[ "$reason" == *"ritual override is the operator's"* ]]
}

@test "ORCHESTRATOR_GUARD=off in the hook's own environment lifts the guard" {
  p=$(bpayload "rm -rf .claude")
  run --separate-stderr env ORCHESTRATOR_GUARD=off CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" <<<"$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "the lift flag cannot be set from the Bash payload's own env" {
  p=$(bpayload "ORCHESTRATOR_GUARD=off rm -rf .claude")
  run_guard "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
}

# --- wall time ---

@test "a guard call finishes well under 300 ms" {
  local p start end ms
  p=$(bpayload "git status")
  start=$(date +%s%N)
  for _ in 1 2 3 4 5; do
    printf '%s\n' "$p" | bash "$GUARD" >/dev/null 2>&1
  done
  end=$(date +%s%N)
  ms=$(( (end - start) / 5000000 ))
  [ "$ms" -lt 300 ]
}

# --- CR2rb fixes (cr15 rejected CR2r on four majors + minors) ---

@test "bash: the git commit -m exemption ends at the message word (a newline or bare word after it is scanned)" {
  local -a plan_cmds=(
    $'git commit -m x\nrm -rf docs/superpowers/plans/x.md'
    $'git commit -m \'subject line\'\nsed -i s/a/b/ docs/superpowers/plans/x.md'
    $'git commit -m \'subject\'\ntee docs/superpowers/plans/x.md'
    $'git commit -m \'subject\'\nmv docs/superpowers/plans/x.md /tmp/'
  )
  for cmd in "${plan_cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
  done
  local -a ovr_cmds=(
    $'git commit -m \'x\'\nrm -rf .claude/ritual-override'
    "git commit -m rm .claude/ritual-override"
  )
  for cmd in "${ovr_cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: git clean force and git stash untracked read flag clusters and skip subcommand words" {
  local -a cmds=(
    "git clean -df"
    "git clean -xdf"
    "git clean -dxf"
    "git clean -ffd"
    "git stash push -u"
    "git stash save -u"
    "git stash -au"
    "git stash -ua"
    "git stash push --include-untracked"
    "git stash push -a"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: an extract whose cwd is inside .claude with no destination denies" {
  local cmd
  for cmd in "cpio -idm" "tar -xf /tmp/a.tar" "unzip /tmp/a.zip"; do
    local p
    p=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]},separators=(",",":")))' "$cmd" "$PROJECT/.claude")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
  # a list-only tar or an extract naming a destination outside .claude still allows
  for cmd in "tar -tf /tmp/a.tar" "tar -C /tmp -xf /tmp/a.tar"; do
    local p
    p=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]},separators=(",",":")))' "$cmd" "$PROJECT/.claude")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: flags are clause-local so a flag in one clause does not arm another" {
  for cmd in "rm -f result && git clean" "ls -a && git stash"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: chmod/chown/chattr on the .claude directory deny" {
  local -a cmds=(
    "chmod 000 .claude"
    "chmod -R 000 .claude"
    "chown root .claude"
    "chattr +i .claude"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "write: a third protected file entry in the list is honoured (no early break in main)" {
  export GUARD="$GUARD" PROJECT="$PROJECT"
  local p
  p=$(wpayload "elsewhere/secret.txt" "allow")
  run bash -c 'source "$GUARD"; PROTECTED_PATHS+=("elsewhere/secret.txt|file"); CLAUDE_PROJECT_DIR="$PROJECT" main' <<<"$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"ritual override is the operator's"* ]]
}

@test "ORCHESTRATOR_GUARD=off lift prints one stderr line" {
  p=$(bpayload "rm -rf .claude")
  run --separate-stderr env ORCHESTRATOR_GUARD=off CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" <<<"$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [[ "$stderr" == *"orchestrator-guard: lifted by ORCHESTRATOR_GUARD=off"* ]]
}

# --- CR2r2 fixes (cr17 rejected CR2rb on the quoted-operator clause split + minors) ---

@test "bash: a quoted operator does not split a clause — the nine plan spellings deny" {
  local -a cmds=(
    "sed 's|a|b|' -i docs/superpowers/plans/x.md"
    "sed -e 's|/old/path|/new/path|' -i docs/superpowers/plans/x.md"
    "sed -e 's/a/b/' -e 's|c|d|' -i docs/superpowers/plans/x.md"
    "perl -pe 's|a|b|' -i docs/superpowers/plans/x.md"
    "sed 's/a;b/c/' -i docs/superpowers/plans/x.md"
    "sed 's/a&b/c/' -i docs/superpowers/plans/x.md"
    $'sed -e \'s/a/\nb/\' -i docs/superpowers/plans/x.md'
    $'perl -pe \'s/a/\nb/\' -i docs/superpowers/plans/x.md'
    "find docs/superpowers/plans -name 'a|b' -delete"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
  done
}

@test "bash: a quoted operator does not split a clause — the override spellings deny" {
  local -a cmds=(
    "sed 's|a|b|' -i .claude/ritual-override"
    "sed -e 's/a|b/c/' -i .claude/ritual-override"
    "find .claude -name 'a|b' -delete"
    "tar 'a|b' -x -C .claude"
    "cpio 'a|b' -idm"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: sed -i and the script-first order both deny a plan (argument order is irrelevant)" {
  local cmd
  for cmd in "sed -i 's|a|b|' docs/superpowers/plans/x.md" "sed 's|a|b|' -i docs/superpowers/plans/x.md"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"plan files change only through the Edit and Write tools"* ]]
  done
}

@test "bash: a quoted ; or | is not a clause boundary — the other clause is a safe /tmp write" {
  local cmd
  for cmd in "echo 'a;b' && rm /tmp/x" "echo 'a|b' | cat"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: a quoted pathspec under git clean/stash stays allowed (narrows, not a quote regression)" {
  local cmd
  for cmd in "git clean 'a|b' -f" "git stash 'a|b' -u"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: an extract into the project root with no destination denies (the archive can carry the override)" {
  local cmd
  for cmd in "tar -xf /tmp/a.tar" "unzip /tmp/a.zip" "cpio -idm"; do
    local p
    p=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]},separators=(",",":")))' "$cmd" "$PROJECT")
    run_guard "$p"
    [ "$status" -eq 0 ]
    denied "$output"
    [[ "$output" == *"ritual override is the operator's"* ]]
  done
}

@test "bash: an extract naming a destination outside the project allows" {
  local cmd
  for cmd in "tar -xf /tmp/a.tar -C /tmp" "unzip -d /tmp /tmp/a.zip"; do
    local p
    p=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]},separators=(",",":")))' "$cmd" "$PROJECT")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "bash: every git commit -m argument is exempt, not only the first" {
  p=$(bpayload "git commit -m 'subject' -m 'body: rm -rf .claude no longer allowed'")
  run_guard "$p"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "bash: git commit glued message forms are exempt (-am, -m'…', --message='…')" {
  local -a cmds=(
    "git commit -am 'fix: rm -rf .claude no longer allowed'"
    "git commit -m'guard: rm -rf .claude no longer allowed'"
    "git commit --message='guard: rm -rf .claude no longer allowed'"
  )
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
  done
}

@test "the raw-text plan fallback honours a second dir entry (M-H dies)" {
  # shellcheck disable=SC1091
  source "$GUARD"
  PROTECTED_PATHS+=('docs/second/plans|dir')
  write_verdict "python3 -c \"open('docs/second/plans/y.md', 'w').write('x')\"" "$PROJECT" ""
  local reason=$_ret
  [[ "$reason" == *"plan files change only through the Edit and Write tools"* ]]
}

# --- CR2r2b fixes (cr18 rejected CR2r2 on the unbounded operator lookahead + a fault allowing) ---

@test "the operator lookahead is bounded — the seventeen trailing-&, | and > spellings deny" {
  local -a cmds=(
    "rm -rf .claude/ritual-override &"
    "rm -rf .claude/ritual-override&"
    "rm -rf .claude &"
    "rm docs/superpowers/plans/x.md &"
    "sed -i s/a/b/ docs/superpowers/plans/x.md &"
    "rm -rf docs/superpowers/plans &"
    "git clean -fd &"
    "{ rm -rf .claude/ritual-override; } &"
    "rm -rf .claude/ritual-override; ls &"
    "touch .claude/ritual-override &"
    "echo x > .claude/ritual-override &"
    "cp k .claude/ritual-override &"
    "tee .claude/ritual-override &"
    "git stash -u &"
    "rm -rf .claude/ritual-override 1>"
    "rm -rf .claude/ritual-override >"
    "rm -rf .claude/ritual-override |"
  )
  local cmd p
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    [ -z "$stderr" ]  # the bounded lookahead must not raise (or the fault-deny would mask the bug)
    denied "$output"
  done
}

@test "a control ending in ;, ), } or a bare & (nix build) keeps behaving" {
  local -a cmds=(
    "rm -rf .claude/ritual-override ;"
    "rm -rf .claude/ritual-override &&"
    "rm -rf .claude/ritual-override ||"
    "rm -rf .claude/ritual-override >>"
    "nix build .#checks.x86_64-linux.unit -L --no-link &"
  )
  local cmd p
  for cmd in "${cmds[@]}"; do
    p=$(bpayload "$cmd")
    run_guard "$p"
    [ "$status" -eq 0 ]
    if [[ "$cmd" == "nix build"* ]]; then
      [ -z "$output" ]  # allow-control: a safe command ending in & allows
    else
      denied "$output"
    fi
  done
}

@test "a fault in bash_verdict denies via the EXIT trap (guard fault)" {
  fault_run bash_verdict "$(bpayload 'rm -rf .claude/ritual-override')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$stderr" == *"orchestrator-guard: guard fault"* ]]
}

@test "a fault in git_verdict denies via the EXIT trap (guard fault)" {
  fault_run git_verdict "$(bpayload 'rm -rf .claude/ritual-override')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$stderr" == *"orchestrator-guard: guard fault"* ]]
}

@test "a fault in write_verdict denies via the EXIT trap (guard fault)" {
  fault_run write_verdict "$(bpayload 'rm -rf .claude/ritual-override')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$stderr" == *"orchestrator-guard: guard fault"* ]]
}

@test "a fault in json_unescape denies via the EXIT trap (guard fault)" {
  fault_run json_unescape "$(bpayload 'rm -rf .claude/ritual-override')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$stderr" == *"orchestrator-guard: guard fault"* ]]
}

@test "a fault in resolve_path denies via the EXIT trap (guard fault)" {
  fault_run resolve_path "$(epayload "$PLAN" $'### A1 (code, S) — first task\n' '')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$stderr" == *"orchestrator-guard: guard fault"* ]]
}

@test "a fault in missing_headings denies via the EXIT trap (guard fault)" {
  fault_run missing_headings "$(epayload "$PLAN" $'### A1 (code, S) — first task\n' '')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$stderr" == *"orchestrator-guard: guard fault"* ]]
}

@test "a fault in apply_edit denies via the EXIT trap (guard fault)" {
  fault_run apply_edit "$(epayload "$PLAN" $'### A1 (code, S) — first task\n' '')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$stderr" == *"orchestrator-guard: guard fault"* ]]
}

@test "a fault in is_plan_file (a direct main-shell call) denies via the EXIT trap" {
  fault_run is_plan_file "$(epayload "$PLAN" $'### A1 (code, S) — first task\n' '')"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$stderr" == *"orchestrator-guard: guard fault"* ]]
}

@test "the guard never raises — every sweep row is stderr-silent, and the count is pinned to its header" {
  local sweep="$BATS_TEST_DIRNAME/91-orchestrator-guard-sweep.txt"
  local cmd p err n=0 data_rows=0 seen_header=0
  while IFS= read -r cmd; do
    if [ "$seen_header" -eq 0 ]; then
      [[ "$cmd" == '# rows: '* ]] || {
        printf 'sweep header missing (first line: %s)\n' "$cmd"
        return 1
      }
      n=${cmd#'# rows: '}
      seen_header=1
      continue
    fi
    data_rows=$((data_rows + 1))
    # Minimal JSON payload (commands are single-line: escape only \\ and \"),
    # avoiding a python3 fork per row so the sweep stays fast.
    p=$cmd
    p=${p//\\/\\\\}
    p=${p//\"/\\\"}
    p="{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"$p\"}}"
    err=$(env CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" <<<"$p" 2>&1 1>/dev/null)
    if [ -n "$err" ]; then
      printf 'row %d raised: %s\n' "$data_rows" "$cmd"
      printf '%s\n' "$err"
      return 1
    fi
  done < "$sweep"
  [ "$data_rows" -eq "$n" ] || {
    printf 'sweep data-row count %d does not match header %d\n' "$data_rows" "$n"
    return 1
  }
}

@test "the sweep fixture contains every recipe from the runbook's recipe section" {
  local runbook="$BATS_TEST_DIRNAME/../../docs/runbooks/session.md"
  local sweep="$BATS_TEST_DIRNAME/91-orchestrator-guard-sweep.txt"
  local line in_recipes=0 in_fence=0
  while IFS= read -r line; do
    if [ "$in_recipes" -eq 0 ]; then
      [[ "$line" == '## Recipes'* ]] && in_recipes=1
      continue
    fi
    if [ "$in_fence" -eq 0 ]; then
      if [[ "$line" == '```bash' ]]; then
        in_fence=1
      fi
      continue
    fi
    [[ "$line" == '```' ]] && break
    grep -Fxq "$line" "$sweep" || {
      printf 'recipe missing from the sweep: %s\n' "$line"
      return 1
    }
  done < "$runbook"
  [ "$in_recipes" -eq 1 ]
  [ "$in_fence" -eq 1 ]
}

@test "the sweep fixture contains the seventeen trailing-&, | and > spellings" {
  local sweep="$BATS_TEST_DIRNAME/91-orchestrator-guard-sweep.txt"
  local -a spellings=(
    "rm -rf .claude/ritual-override &"
    "rm -rf .claude/ritual-override&"
    "rm -rf .claude &"
    "rm docs/superpowers/plans/x.md &"
    "sed -i s/a/b/ docs/superpowers/plans/x.md &"
    "rm -rf docs/superpowers/plans &"
    "git clean -fd &"
    "{ rm -rf .claude/ritual-override; } &"
    "rm -rf .claude/ritual-override; ls &"
    "touch .claude/ritual-override &"
    "echo x > .claude/ritual-override &"
    "cp k .claude/ritual-override &"
    "tee .claude/ritual-override &"
    "git stash -u &"
    "rm -rf .claude/ritual-override 1>"
    "rm -rf .claude/ritual-override >"
    "rm -rf .claude/ritual-override |"
  )
  local s
  for s in "${spellings[@]}"; do
    grep -Fxq "$s" "$sweep" || {
      printf 'spelling missing from the sweep: %s\n' "$s"
      return 1
    }
  done
  [ "${#spellings[@]}" -eq 17 ]
}

@test "no guard function is called inside any subshell form (structural)" {
  # Scan only executable lines: the header prose names functions inside
  # backticks/parens in passing, and a comment does not run in a subshell.
  grep -vE '^[[:space:]]*#' "$GUARD" >"$BATS_TEST_TMPDIR/code"
  grep -oE '^[A-Za-z_][A-Za-z0-9_]*\(\)' "$GUARD" | sed 's/()//' | sort -u >"$BATS_TEST_TMPDIR/defs"
  {
    # a `$(` command substitution
    grep -oE '\$\([A-Za-z_][A-Za-z0-9_]*' "$BATS_TEST_TMPDIR/code" | sed 's/\$(//'
    # a backtick command substitution
    grep -oE '`[A-Za-z_][A-Za-z0-9_]*' "$BATS_TEST_TMPDIR/code" | sed 's/`//'
    # a `<( … )` / `>( … )` process substitution
    grep -oE '[<>]\([A-Za-z_][A-Za-z0-9_]*' "$BATS_TEST_TMPDIR/code" | sed 's/[<>](//'
    # a guard function on the right of a pipe
    grep -oE '\|[[:space:]]*[A-Za-z_][A-Za-z0-9_]*' "$BATS_TEST_TMPDIR/code" | sed 's/|[[:space:]]*//'
    # a guard function inside a `( … )` list
    grep -oE '\([[:space:]]*[A-Za-z_][A-Za-z0-9_]*' "$BATS_TEST_TMPDIR/code" | sed 's/([[:space:]]*//'
  } | sort -u >"$BATS_TEST_TMPDIR/callees"
  local overlap
  overlap=$(comm -12 "$BATS_TEST_TMPDIR/callees" "$BATS_TEST_TMPDIR/defs")
  [ -z "$overlap" ] || {
    printf 'functions called in a subshell form: %s\n' "$overlap"
    return 1
  }
}

@test "no line tests \$_ret directly — every guard call copies it to a local first" {
  local hits
  hits=$(grep -nE '\[\[?[^]]*\$?_ret' "$GUARD" || true)
  [ -z "$hits" ] || {
    printf 'direct \$_ret test (brackets): %s\n' "$hits"
    return 1
  }
  hits=$(grep -nE '^[[:space:]]*case[[:space:]]+"?\$?_ret' "$GUARD" || true)
  [ -z "$hits" ] || {
    printf 'direct \$_ret test (case): %s\n' "$hits"
    return 1
  }
}

@test "sourcing the guard installs no EXIT trap (the trap lives only on the entry path)" {
  local t
  t=$(bash -c 'source "$1"; trap -p EXIT' _ "$GUARD")
  [ -z "$t" ] || {
    printf 'trap installed at source time: %s\n' "$t"
    return 1
  }
}

@test "no payload nests \"cwd\" under tool_input (the cwd key is top-level)" {
  # shellcheck disable=SC1091
  local bats_file="$BATS_TEST_DIRNAME/91-orchestrator-guard.bats"
  ! grep -q '"tool_input":{[^}]*"cwd"' "$bats_file"
}

@test "_ctx_emit is hoisted to file scope and precedes tokenise_ctx (M-F dies)" {
  local line emit_line=0 tctx_line=0 n=0
  while IFS= read -r line; do
    n=$((n + 1))
    case "$line" in
      '_ctx_emit()'*)
        [ "$emit_line" -eq 0 ] && emit_line=$n
        ;;
      'tokenise_ctx()'*)
        [ "$tctx_line" -eq 0 ] && tctx_line=$n
        ;;
    esac
  done < "$GUARD"
  [ "$emit_line" -gt 0 ]
  [ "$tctx_line" -gt 0 ]
  [ "$emit_line" -lt "$tctx_line" ]
}

@test "write_verdict does not leak dq/sq/dqd/sqd into the global namespace" {
  # shellcheck disable=SC1091
  source "$GUARD"
  write_verdict "echo foo" "$PROJECT" "" >/dev/null 2>&1
  run declare -p dq
  [ "$status" -ne 0 ]
  run declare -p sq
  [ "$status" -ne 0 ]
  run declare -p dqd
  [ "$status" -ne 0 ]
  run declare -p sqd
  [ "$status" -ne 0 ]
}

@test "a quoted newline stays a newline character in the token, not a space" {
  # shellcheck disable=SC1091
  source "$GUARD"
  local -a toks quoted nlsep
  tokenise_ctx $'echo "a\nb"' toks quoted nlsep
  [ "${toks[1]}" = $'a\nb' ]
}

# fault_any_run FN PAYLOAD — as fault_run, but for a function name derived from
# the guard's own `^name()` lines (already a safe identifier), so the loop below
# never hard-codes the guard's function list.
fault_any_run() {
  local fn=$1 payload=$2
  case "$fn" in
    *[!A-Za-z0-9_]*) return 1 ;;
  esac
  run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" bash -c '
    # shellcheck disable=SC1091
    source "$1"
    '"$fn"'() { local x=$GUARD_FAULT_VAR; : "$x"; }
    main <<< "$2"
  ' _ "$GUARD" "$payload"
}

@test "a fault in every guard function denies on every arm (behavioural loop)" {
  local guard="$GUARD"
  local -a fns=()
  local fn p1 p2 p3 payload
  while IFS= read -r fn; do
    # main/deny/warn/_guard_trap are the fault channel itself, not guard logic —
    # overriding them removes the very deny-under-test, so the loop covers the
    # 20 verdict/helper functions (everything else the file defines).
    case "$fn" in
      main | deny | warn | _guard_trap) : ;;
      *) fns+=("$fn") ;;
    esac
  done < <(grep -oE '^[A-Za-z_][A-Za-z0-9_]*\(\)' "$guard" | sed 's/()//')
  [ "${#fns[@]}" -eq 21 ]
  p1=$(bpayload 'rm -rf .claude/ritual-override')
  p2=$(epayload "$PLAN" $'### A1 (code, S) — first task\n' '')
  p3=$(wpayload "$PLAN" $'# Test plan\n\n### A1 (code, S) — first task\n\nbody one line\n')
  for fn in "${fns[@]}"; do
    for payload in "$p1" "$p2" "$p3"; do
      fault_any_run "$fn" "$payload"
      [ "$status" -eq 0 ] || {
        printf '%s fault on a payload exited %d\n' "$fn" "$status"
        return 1
      }
      denied "$output" || {
        printf '%s fault ALLOWED on a payload\n' "$fn"
        return 1
      }
    done
  done
}

@test "a fault in headings on a heading-removing Edit denies (guard fault)" {
  local p
  p=$(epayload "$PLAN" $'### A1 (code, S) — first task\n' '')
  run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" bash -c '
    # shellcheck disable=SC1091
    source "$1"
    headings() { local x=$GUARD_FAULT_VAR; : "$x"; }
    main <<< "$2"
  ' _ "$GUARD" "$p"
  [ "$status" -eq 0 ]
  denied "$output"
  [[ "$output" == *"guard fault"* ]]
  [[ "$stderr" == *"orchestrator-guard: guard fault"* ]]
}

@test "the sweep holds every command in the cr17 and cr18 review tables" {
  local sweep="$BATS_TEST_DIRNAME/91-orchestrator-guard-sweep.txt"
  local cr17="$BATS_TEST_DIRNAME/../../docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md"
  local cr18="$BATS_TEST_DIRNAME/../../docs/reviews/2026-09-06-opus-review-cr18-CR2r2.md"
  local extracted="$BATS_TEST_TMPDIR/review-cmds"
  local cmd missing=0
  python3 - "$cr17" "$cr18" >"$extracted" <<'PY'
import sys, re

def cells_of(line):
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    out, cur, i = [], '', 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s) and s[i + 1] == '|':
            cur += '|'; i += 2; continue
        if c == '|':
            out.append(cur.strip()); cur = ''; i += 1; continue
        cur += c; i += 1
    out.append(cur.strip())
    return out

def tables(path):
    L = open(path).read().split('\n')
    tbls, i, n = [], 0, len(L)
    while i < n:
        ln = L[i]
        if not ln.startswith('|'):
            i += 1; continue
        hdr = cells_of(ln)
        if i + 1 < n and re.fullmatch(r'\|?[\s:|-]*\|?', L[i + 1]) and '-' in L[i + 1]:
            rows = []; j = i + 2
            while j < n and L[j].startswith('|'):
                rows.append(cells_of(L[j])); j += 1
            tbls.append((hdr, rows)); i = j
        else:
            i += 1
    return tbls

PLAN = 'docs/superpowers/plans/x.md'
OVR = '.claude/ritual-override'
PLANSDIR = 'docs/superpowers/plans'
FRAG = {'&&','||','>>',';','&','>','>|','|'}

def resolve(s):
    s = s.replace('<plan>', PLAN).replace('<override>', OVR).replace('<plans-dir>', PLANSDIR)
    return s.replace('\\|', '|')

cmds = set()
for p in sys.argv[1:]:
    for (hdr, rows) in tables(p):
        if not hdr or hdr[0] != 'spelling':
            continue
        for r in rows:
            if not r:
                continue
            cell = r[0].replace('**', '')
            if '⏎' in cell:
                continue  # a newline-joined command is not a flat fixture row
            cell = re.sub(r"\s*\((baseline|unquoted|unterminated|newline inside the quotes)\)\s*$", '', cell).strip()
            for span in re.findall(r'`([^`]*)`', cell):
                rs = resolve(span.strip())
                if not rs or '…' in rs:
                    continue
                if rs in FRAG or rs.startswith('-') or ' ' not in rs:
                    continue
                cmds.add(rs)
print('\n'.join(sorted(cmds)))
PY
  while IFS= read -r cmd; do
    grep -Fxq "$cmd" "$sweep" || {
      printf 'command from a review table missing from the sweep: %s\n' "$cmd"
      missing=1
    }
  done < "$extracted"
  [ "$missing" -eq 0 ]
}