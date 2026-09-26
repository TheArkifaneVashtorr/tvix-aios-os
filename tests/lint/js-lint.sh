#!/usr/bin/env bash
# js-lint.sh [--self-test] — prettier (format) and oxlint (lint) gate for
# every tracked JavaScript file, plus prettier (format) for every tracked
# stylesheet — the css arm landed with the deck client's own assets (GN25;
# oxlint parses no css, so css is format-checking only). Mirrors the lint
# check and the pre-commit hook.
#
# Exit codes: 0 every file passes; 1 a file fails (tool output shown); 2 a tool
# is missing from PATH.
set -euo pipefail

self_test=0
if [ $# -gt 0 ] && [ "$1" = "--self-test" ]; then
  self_test=1
  shift
fi

# A missing linter is exit 2 (this script runs in the lint check and the
# hook, both of which carry prettier/oxlint in their tool set). git is used
# only for the enumeration convenience and falls back to `find` below.
for tool in prettier oxlint; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "js-lint: $tool not on PATH" >&2
    exit 2
  fi
done

# prettier --check on one file.
format_check_file() {
  local f="$1"
  prettier --check "$f"
}

# oxlint --deny-warnings on one file.
lint_file() {
  local f="$1"
  oxlint --deny-warnings "$f"
}

# The files the project run sweeps: every tracked .js/.mjs outside the fixtures
# the self-test probes directly. Prefer `git ls-files` (the devShell/hook
# context) but fall back to `find` for the lint check sandbox, whose src copy
# carries the tracked files with no .git directory and no git on PATH.
tracked_js_files() {
  if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git ls-files '*.js' '*.mjs' ':!tests/lint/fixtures/js/*' ':!pkgs/dsh-harness/*'
  else
    find . -type f \( -name '*.js' -o -name '*.mjs' \) -not -path './tests/lint/fixtures/js/*' -not -path './pkgs/dsh-harness/*' |
      sed 's|^\./||'
  fi
}

# GN25: the css arm — the same sweep shape for stylesheets (prettier only;
# oxlint parses no css). The fixtures live outside the sweep: the css
# self-test prober must stay misformatted.
tracked_css_files() {
  if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git ls-files '*.css' ':!tests/lint/fixtures/css/*'
  else
    find . -type f -name '*.css' -not -path './tests/lint/fixtures/css/*' |
      sed 's|^\./||'
  fi
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

# GN25: the css mirror of the js vacuous-gate guard — treefmt must name a css
# formatter, or the css arm's formatter half would run only in this script
# and never in the treefmt sweep.
treefmt_css_check() {
  local out
  if ! command -v treefmt >/dev/null 2>&1; then
    echo "js-lint: treefmt not on PATH" >&2
    exit 2
  fi
  if out="$(treefmt --ci --config-file treefmt.toml --tree-root . --formatters css 2>&1)"; then
    return 0
  fi
  if printf '%s\n' "$out" | grep -q 'formatter css not found'; then
    echo "js-lint: self-test: treefmt has no css formatter" >&2
    exit 1
  fi
  printf '%s\n' "$out" >&2
  exit 1
}

# --self-test: the fixtures must FAIL their tool, or the gate is vacuous.
self_check() {
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
  if format_check_file tests/lint/fixtures/css/unformatted.css; then
    echo "js-lint: self-test: unformatted.css passed; the css gate is vacuous" >&2
    exit 1
  fi
  treefmt_js_check
  treefmt_css_check
}

# Project run (no arguments): every tracked file must pass its tools.
run_project() {
  local f
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    format_check_file "$f" || exit 1
    lint_file "$f" || exit 1
  done < <(tracked_js_files)
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    format_check_file "$f" || exit 1
  done < <(tracked_css_files)
}

if [ "$self_test" -eq 1 ]; then
  self_check
else
  run_project
fi
