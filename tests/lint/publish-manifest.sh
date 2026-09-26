#!/usr/bin/env bash
# publish-manifest.sh [--self-test] [--tree DIR] — the publish-gate and
# subsystems-manifest validators as a commit-time and lint-time gate. Why a
# script: checks.publish-gate and checks.subsystems-manifest run only in the
# flake sandbox, so a deny word or an unowned path lands green through the
# hook and turns the nightly red hours later (spec §2 #2). This runs the same
# two validators on the live tree, from DIR (default "."), with DIR's own
# pkgs/evidence/{publish,subsystems}.py and docs/ledger manifests — a replay
# tree is judged by the rules the commit carried. The file list is the
# tracked set under git (the sandbox has no git and enumerates with find,
# same contract as store-writers.sh). Both validators run even when the
# first refused, so one report carries both halves; the second is never
# joined by `&&` (under errexit a failing first command in an `a && b` list
# is swallowed).
#
# Exit codes: 0 clean; 1 a refusal (every validator report line printed
# verbatim on stdout, each prefixed `publish-manifest: `); 2 python3/find
# missing from PATH, or an unusable manifest (the validator's report passed
# through, prefixed).
#
# --self-test builds nothing on DIR: (a) the publish half over
# tests/fixtures/publish (exactly what checks.publish-gate-negative does —
# the planted defects refused with the exact report in expected.txt);
# (b) the manifest half over a temporary copy of docs/ledger/subsystems.toml
# minus the first subsystem's first owns entry, against the current tree's
# file list (its paths become uncovered). Temp files live under mktemp -d,
# removed on exit — a self-test never writes under the tree.
set -euo pipefail

PREFIX="publish-manifest: "
TREE="."
SELF_TEST=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --self-test)
      SELF_TEST=1
      ;;
    --tree)
      if [ "$#" -lt 2 ]; then
        echo "publish-manifest: --tree needs a value" >&2
        exit 2
      fi
      TREE=$2
      shift
      ;;
    --tree=*)
      TREE=${1#--tree=}
      ;;
    *)
      echo "publish-manifest: unknown argument: $1" >&2
      exit 2
      ;;
  esac
  shift
done

for tool in python3 find; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "publish-manifest: $tool not on PATH" >&2
    exit 2
  }
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# file_list DIR — the tree's file list on stdout, one path per line. The
# tracked set under git (a worktree's .git is a file, hence -e, and DIR's own
# git enumerates the checked-out revision); find otherwise, as in the lint
# sandbox (no git, no .git). The find arm prunes the caches tooling drops in
# a live tree — the lint sandbox's own ruff runs leave a .ruff_cache behind
# before this script runs, and __pycache__/.pytest_cache never hold source —
# so both arms see the same universe: files, not tool scratch (a worktree's
# .git file, enumerated only by a mutated find arm, shows up as unclassified,
# which is how the git arm stays load-bearing).
file_list() {
  if [ -e "$1/.git" ]; then
    command -v git >/dev/null 2>&1 || {
      echo "publish-manifest: git not on PATH" >&2
      exit 2
    }
    git -C "$1" ls-files
  else
    (
      cd "$1" &&
        find . \( -name .ruff_cache -o -name __pycache__ -o -name .pytest_cache \) \
          -prune -o -type f -printf '%P\n'
    )
  fi
}

# run_validator STREAM ARGS… — python3 ARGS…, report passed through prefixed
# when it fails, nothing printed when it passes. STREAM is where that
# validator's refusal report lives (publish.py: stdout — defects and counts;
# subsystems.py: stderr — uncovered/ambiguous), measured on both validators:
# exit 0 is the green path, 1 the refusal, 2 an unusable manifest (both
# validators report those on stderr), anything else a crash, both streams
# passed through and treated as a refusal.
run_validator() {
  local stream="$1"
  shift
  local rc=0
  python3 "$@" >"$WORK/out" 2>"$WORK/err" || rc=$?
  case "$rc" in
    0) return 0 ;;
    1)
      sed "s/^/$PREFIX/" "$WORK/$stream"
      return 1
      ;;
    2)
      if [ -s "$WORK/err" ]; then sed "s/^/$PREFIX/" "$WORK/err"; fi
      if [ -s "$WORK/out" ]; then sed "s/^/$PREFIX/" "$WORK/out"; fi
      return 2
      ;;
    *)
      if [ -s "$WORK/out" ]; then sed "s/^/$PREFIX/" "$WORK/out"; fi
      if [ -s "$WORK/err" ]; then sed "s/^/$PREFIX/" "$WORK/err"; fi
      return 1
      ;;
  esac
}

strip_prefix() {
  sed "s/^publish-manifest: //"
}

if [ "$SELF_TEST" -eq 1 ]; then
  fixture="$TREE/tests/fixtures/publish"
  expected="$TREE/tests/fixtures/publish/expected.txt"
  if [ ! -f "$fixture/publish.toml" ] || [ ! -f "$expected" ]; then
    echo "publish-manifest: self-test failed: publish no fixture at $fixture" >&2
    exit 1
  fi
  # (a) the publish half over the negative fixture, no --files — the
  # validator enumerates the fixture tree itself, exactly what
  # checks.publish-gate-negative does.
  a_rc=0
  run_validator out "$TREE/pkgs/evidence/publish.py" validate \
    "$fixture/publish.toml" --tree "$fixture" >"$WORK/a.out" || a_rc=$?
  if [ "$a_rc" -ne 1 ]; then
    echo "publish-manifest: self-test failed: publish validate exited $a_rc, expected 1" >&2
    exit 1
  fi
  strip_prefix <"$WORK/a.out" >"$WORK/a.stripped"
  if ! cmp -s "$expected" "$WORK/a.stripped"; then
    echo "publish-manifest: self-test failed: publish the report differs from tests/fixtures/publish/expected.txt" >&2
    exit 1
  fi
  # (b) the manifest half: the first subsystem's first owns entry deleted
  # from a temporary copy, validated against the current tree's file list.
  manifest_src="$TREE/docs/ledger/subsystems.toml"
  if [ ! -f "$manifest_src" ]; then
    echo "publish-manifest: self-test failed: manifest no docs/ledger/subsystems.toml in the tree" >&2
    exit 1
  fi
  # awk deletes the first entry of the first `owns` list and exits nonzero
  # when it never found one to delete (a line-count check would lie: the
  # ledger's last line carries no trailing newline, so awk's final print
  # changes wc -l by nothing).
  if ! awk '
    !saw_owns && /^owns = \[$/ { saw_owns = 1; print; next }
    saw_owns && !deleted && /^[[:space:]]*"[^"]*",?[[:space:]]*$/ { deleted = 1; next }
    { print }
    END { exit deleted ? 0 : 1 }
  ' "$manifest_src" >"$WORK/subsystems.toml"; then
    echo "publish-manifest: self-test failed: manifest the first subsystem's first owns entry was not found to delete" >&2
    exit 1
  fi
  file_list "$TREE" | LC_ALL=C sort >"$WORK/files"
  b_rc=0
  run_validator err "$TREE/pkgs/evidence/subsystems.py" validate \
    "$WORK/subsystems.toml" --files "$WORK/files" >"$WORK/b.out" || b_rc=$?
  if [ "$b_rc" -ne 1 ]; then
    echo "publish-manifest: self-test failed: manifest validate exited $b_rc, expected 1" >&2
    exit 1
  fi
  strip_prefix <"$WORK/b.out" >"$WORK/b.stripped"
  if ! grep -q '^uncovered: ' "$WORK/b.stripped"; then
    echo "publish-manifest: self-test failed: manifest no uncovered: line in the report" >&2
    exit 1
  fi
  exit 0
fi

file_list "$TREE" | LC_ALL=C sort >"$WORK/files"

rc_pub=0
(
  cd "$TREE" &&
    run_validator out pkgs/evidence/publish.py validate \
      docs/ledger/publish.toml --tree . --files "$WORK/files"
) || rc_pub=$?
# The second validator runs even when the first refused, so one run reports
# both halves (never `&&`-joined).
rc_sub=0
(
  cd "$TREE" &&
    run_validator err pkgs/evidence/subsystems.py validate \
      docs/ledger/subsystems.toml --files "$WORK/files"
) || rc_sub=$?

if [ "$rc_pub" -eq 2 ] || [ "$rc_sub" -eq 2 ]; then
  exit 2
fi
if [ "$rc_pub" -ne 0 ] || [ "$rc_sub" -ne 0 ]; then
  exit 1
fi
exit 0
