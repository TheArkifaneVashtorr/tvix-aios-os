#!/usr/bin/env bash
# js-lint.sh [--self-test] — prettier (format) and oxlint (lint) gate for every
# tracked JavaScript file, mirroring the lint check and the pre-commit hook.
#
# A "Workflow script" is a file whose first statement is `export const meta`,
# which the Workflow harness evaluates as the body of an async function: it may
# use top-level `await`/`return`, both illegal in a module or plain script. Such
# a file is checked in the shape the harness runs it (arm B for a tool that
# cannot parse it in place), or left out of the treefmt js formatter's sweep by
# naming it in that formatter's `excludes` (arm B for prettier).
#
# Exit codes: 0 every file passes; 1 a file fails (tool output shown); 2 a tool
# is missing from PATH; 3 a Workflow script no tool parses in either shape.
set -euo pipefail

# --- Step 1 probe: these two literals record how prettier and oxlint each
# handle tools/factory/dark-factory.js (this repo's Workflow script), decided
# by the probe outputs pasted into the landing commit body:
#   A = the tool accepts the file in place
#   B = the tool cannot parse the in-place shape (top-level `return`/`await`)
FORMATTER_ARM=A
LINTER_ARM=A

self_test=0
if [ $# -gt 0 ] && [ "$1" = "--self-test" ]; then
  self_test=1
  shift
fi

# A missing linter is exit 2 (this script runs in the lint check and the
# hook, both of which carry prettier/oxlint in their tool set). git is used
# only for the enumeration convenience and falls back to `find` below; node is
# not needed here (the lint check's own `node --check` covers the factory
# script's syntax in a separate step).
for tool in prettier oxlint; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "js-lint: $tool not on PATH" >&2
    exit 2
  fi
done

# A Workflow script is identified by its `export const meta = {` opener.
is_workflow() { grep -q '^export const meta = {' -- "$1"; }

# prettier --check on one file, honouring the formatter arm for Workflow
# scripts: under arm B prettier cannot parse them in place, so the treefmt js
# formatter's `excludes` names them and they are skipped here (the lockstep
# rule in --self-test keeps that `excludes` enumeration honest).
format_check_file() {
  local f="$1"
  if [ "$FORMATTER_ARM" = "B" ] && is_workflow "$f"; then
    return 0
  fi
  prettier --check "$f"
}

# oxlint --deny-warnings on one file, honouring the linter arm for Workflow
# scripts: under arm B the file is wrapped in the harness shape first.
lint_file() {
  local f="$1"
  if [ "$LINTER_ARM" = "B" ] && is_workflow "$f"; then
    lint_workflow_wrapped "$f"
  else
    oxlint --deny-warnings "$f"
  fi
}

# arm B (linter): wrap the Workflow script as an async-function body (the same
# transformation the lint check's darkFactorySyntaxCheckSrc applies) and lint
# the wrapped copy; a reported line is the file's line plus one. A normal lint
# finding exits 1; a parse error in this shape too (oxlint prints `: error:`
# with no `eslint(` rule tag on a parse failure) means no shape parses it,
# which exits 3.
lint_workflow_wrapped() {
  local f="$1"
  local tmp tmpf out
  tmp="$(mktemp -d)"
  tmpf="$tmp/$(basename "$f")"
  {
    echo 'async function __wf() {'
    sed 's/^export const meta/const meta/' "$f"
    echo '}'
  } >"$tmpf"
  if out="$(oxlint --deny-warnings "$tmpf" 2>&1)"; then
    rm -rf "$tmp"
    return 0
  fi
  if printf '%s\n' "$out" | grep -q 'eslint('; then
    printf '%s\n' "$out"
    echo "js-lint: a reported line number above is the file's line plus one (harness wrapper)" >&2
    rm -rf "$tmp"
    return 1
  fi
  echo "js-lint: $f: no arm parses this Workflow script" >&2
  printf '%s\n' "$out" >&2
  rm -rf "$tmp"
  exit 3
}

# The files the project run sweeps: every tracked .js/.mjs outside the fixtures
# the self-test probes directly. Prefer `git ls-files` (the devShell/hook
# context) but fall back to `find` for the lint check sandbox, whose src copy
# carries the tracked files with no .git directory and no git on PATH.
tracked_js_files() {
  if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git ls-files '*.js' '*.mjs' ':!tests/lint/fixtures/js/*'
  else
    find . -type f \( -name '*.js' -o -name '*.mjs' \) -not -path './tests/lint/fixtures/js/*' |
      sed 's|^\./||'
  fi
}

# The treefmt js formatter's `excludes` line, or empty when there is none.
js_excludes_line() {
  awk '/^\[formatter\.js\]/{s=1;next} /^\[/{s=0} s && /^excludes[[:space:]]*=/{print; exit}' \
    treefmt.toml
}

# Lockstep rule: under FORMATTER_ARM=B every Workflow script must be named in
# the js formatter's `excludes`; under arm A none may be.
lockstep_check() {
  local f excluded excludes
  excludes="$(js_excludes_line)"
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    is_workflow "$f" || continue
    if printf '%s\n' "$excludes" | grep -Fq "\"$f\""; then
      excluded=1
    else
      excluded=0
    fi
    if [ "$FORMATTER_ARM" = "B" ]; then
      if [ "$excluded" -eq 0 ]; then
        echo "js-lint: self-test: $f is a Workflow script the treefmt js formatter would still format" >&2
        exit 1
      fi
    elif [ "$excluded" -eq 1 ]; then
      echo "js-lint: self-test: $f is excluded from the formatter although it parses" >&2
      exit 1
    fi
  done < <(tracked_js_files)
}

# treefmt must name a js formatter, or the fixtures' formatter gate is vacuous
# (prettier --check would never run in the treefmt sweep).
treefmt_js_check() {
  local out
  if ! command -v treefmt >/dev/null 2>&1; then
    echo "js-lint: treefmt not on PATH" >&2
    exit 2
  fi
  if out="$(treefmt --ci --config-file treefmt.toml --tree-root . --formatters js 2>&1)"; then
    return 0
  fi
  if printf '%s\n' "$out" | grep -q 'formatter js not found'; then
    echo "js-lint: self-test: treefmt has no js formatter" >&2
    exit 1
  fi
  printf '%s\n' "$out" >&2
  exit 1
}

# --self-test: the fixtures must FAIL their tool, or the gate is vacuous.
self_check() {
  echo "js-lint: workflow-script formatter arm $FORMATTER_ARM"
  echo "js-lint: workflow-script linter arm $LINTER_ARM"
  if lint_file tests/lint/fixtures/js/bad.mjs; then
    echo "js-lint: self-test: bad.mjs passed; the gate is vacuous" >&2
    exit 1
  fi
  if format_check_file tests/lint/fixtures/js/unformatted.mjs; then
    echo "js-lint: self-test: unformatted.mjs passed; the gate is vacuous" >&2
    exit 1
  fi
  if lint_file tests/lint/fixtures/js/workflow-bad.js; then
    echo "js-lint: self-test: workflow-bad.js passed; the gate is vacuous" >&2
    exit 1
  fi
  lockstep_check
  treefmt_js_check
}

# Project run (no arguments): every tracked file must pass both tools.
run_project() {
  local f
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    format_check_file "$f" || exit 1
    lint_file "$f" || exit 1
  done < <(tracked_js_files)
}

if [ "$self_test" -eq 1 ]; then
  self_check
else
  run_project
fi
