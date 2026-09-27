#!/usr/bin/env bash
# secret-shapes.sh [--self-test] — the commit-time secret scan (KN13 (b)
# R-practice-brief8-no-secrets, BUG-secret-shapes-drift, PL22). The arms are
# no longer hand-copied here: the script reads docs/ledger/publish.toml's
# [deny].patterns live (python3/tomllib), the very list the export-time
# publish gate (checks.publish-gate, pkgs/evidence/publish.py) denies on, so
# the two gates share one source and cannot drift apart again;
# pkgs/evidence/streams.py's SECRET_RE (evidence values) is pinned to the
# same families by tests/evidence/test_streams_policy.py's family-parity
# test. docs/ is excluded from the sweep because it is prose that
# legitimately quotes these very shapes (the plan and review documents spell
# the arms and their mutants), not material. The planted fixtures below are
# split across quoted halves for the same reason: this file is itself
# swept, so a contiguous key-shaped literal here would trip the gate on its
# own test corpus.
#
# Exit codes: 0 the tree is clean; 1 secret-shaped material found, or a
# self-test fixture misbehaved; 2 python3/grep missing from PATH or no
# manifest to read.
set -euo pipefail

MANIFEST="docs/ledger/publish.toml"

for tool in python3 grep; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "secret-shapes: $tool not on PATH" >&2
    exit 2
  }
done
[ -f "$MANIFEST" ] || {
  echo "secret-shapes: no $MANIFEST under the working directory (run from the repo root)" >&2
  exit 2
}

# read_patterns MANIFEST — the deny patterns, one per line, on stdout. The
# one place the commit-time gate meets the export-time gate's own list; an
# empty read is refused by the callers, never silently swept with nothing.
read_patterns() {
  python3 -c 'import sys, tomllib
for p in tomllib.load(open(sys.argv[1], "rb"))["deny"]["patterns"]:
    print(p)' "$1"
}

# sweep TREE MANIFEST — every deny pattern as one grep -e arm over TREE, the
# inline block's own scope (excluding .git and docs). Hits on stdout, grep's
# own exit status (0 hits found, 1 clean) — callers assert on it.
sweep() {
  local tree="$1" manifest="$2" p
  local args=()
  while IFS= read -r p; do
    [ -n "$p" ] || {
      echo "secret-shapes: $manifest read an empty pattern line" >&2
      return 2
    }
    args+=(-e "$p")
  done < <(read_patterns "$manifest")
  [ "${#args[@]}" -gt 0 ] || {
    echo "secret-shapes: $manifest carries no deny patterns" >&2
    return 2
  }
  grep -rEn "${args[@]}" --exclude-dir=.git --exclude-dir=docs "$tree"
}

# emit_manifest OUT [EXCLUDE] — a minimal publish manifest for the planted
# tree: planted.txt published, the manifest itself withheld, every deny
# pattern of the real manifest except EXCLUDE (the per-arm mutant). Quoting
# is json.dumps', never by hand.
emit_manifest() {
  local out="$1" exclude="${2:-}"
  python3 -c 'import json, sys, tomllib
pats = tomllib.load(open(sys.argv[2], "rb"))["deny"]["patterns"]
pats = [p for p in pats if p != sys.argv[3]]
with open(sys.argv[1], "w") as fh:
    fh.write("publish = [\"planted.txt\"]\n")
    fh.write("withhold = [\"manifest.toml\"]\n")
    fh.write("[deny]\npatterns = [\n")
    for p in pats:
        fh.write("  " + json.dumps(p) + ",\n")
    fh.write("]\n")' "$out" "$MANIFEST" "$exclude"
}

# self_test — the discriminating fixtures. (a) the live manifest's own list
# catches every planted line; (c) a temp manifest missing exactly one arm's
# pattern line drops exactly that arm's planted line and no other (the
# three selectors are the arms' own pattern text: if the manifest ever
# renames one, the removal matches nothing, the mutant becomes the full
# list, and the "no longer caught" assertion fails red — drift cannot pass
# unnoticed); (d) pkgs/evidence/publish.py validate refuses the identical
# planted lines over the identical pattern source, proving the two gates
# agree because they read the same list, not because one copies the other.
self_test() {
  # Global on purpose: the EXIT trap below must see it after the function
  # scope is gone (the same shape as publish-manifest.sh's WORK).
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT

  # One planted line per arm this gate and the manifest widened for: AWS
  # access-key id, Slack token, GitHub PAT (PL16's shape). Each is split
  # across quoted halves — see the header.
  local aws slack gh
  aws="AKIA""ABCDEFGHIJKLMNOP"
  slack="xox""r-1234567890-abcdefghij"
  gh="ghp""_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
  printf 'a synthetic AWS key %s is here\n' "$aws" >"$work/planted.txt"
  printf 'a synthetic slack token %s is here\n' "$slack" >>"$work/planted.txt"
  printf 'a synthetic github token %s is here\n' "$gh" >>"$work/planted.txt"

  # (a) the live list catches all three.
  local hits line
  hits="$(sweep "$work" "$MANIFEST" || true)"
  for line in 1 2 3; do
    printf '%s\n' "$hits" | grep -q "planted.txt:$line:" || {
      echo "secret-shapes: self-test: planted line $line was not caught by the live manifest's patterns" >&2
      exit 1
    }
  done

  # (c) the per-arm mutant: drop one pattern line, its own planted line (in
  # order: AKIA -> 1, xox -> 2, gh[opsur]_ -> 3) goes uncaught, the other two
  # stay caught.
  local sel own
  for sel in 'AKIA[0-9A-Z]{16}' 'xox[baprs]-[0-9A-Za-z-]{10,}' 'gh[opsur]_[A-Za-z0-9]{36}'; do
    case "$sel" in
      'AKIA'*) own=1 ;;
      'xox'*) own=2 ;;
      *) own=3 ;;
    esac
    emit_manifest "$work/manifest.toml" "$sel"
    hits="$(sweep "$work" "$work/manifest.toml" || true)"
    if printf '%s\n' "$hits" | grep -q "planted.txt:$own:"; then
      echo "secret-shapes: self-test: the mutant without '$sel' still caught planted line $own; the arm is not load-bearing" >&2
      exit 1
    fi
    for line in 1 2 3; do
      [ "$line" -eq "$own" ] && continue
      printf '%s\n' "$hits" | grep -q "planted.txt:$line:" || {
        echo "secret-shapes: self-test: the mutant without '$sel' lost planted line $line too; the drop was not surgical" >&2
        exit 1
      }
    done
  done

  # (d) the export-time gate agrees on the same source.
  [ -f pkgs/evidence/publish.py ] || {
    echo "secret-shapes: self-test: no pkgs/evidence/publish.py under the working directory" >&2
    exit 2
  }
  emit_manifest "$work/manifest.toml"
  local rc=0
  python3 pkgs/evidence/publish.py validate "$work/manifest.toml" --tree "$work" \
    >"$work/validate.out" 2>"$work/validate.err" || rc=$?
  [ "$rc" -eq 1 ] || {
    echo "secret-shapes: self-test: publish.py validate exited $rc, expected 1 (the planted lines must be refused)" >&2
    cat "$work/validate.out" "$work/validate.err" >&2 || true
    exit 1
  }
  for line in 1 2 3; do
    grep -q "planted.txt:$line patterns\[" "$work/validate.out" || {
      echo "secret-shapes: self-test: publish.py validate did not refuse planted line $line" >&2
      exit 1
    }
  done
}

if [ "${1:-}" = "--self-test" ]; then
  self_test
else
  # The commit-time gate itself: the export-time gate's own pattern list,
  # swept over the tree the way the inline block always did. grep's exit is
  # asserted per arm: 0 hits found -> refuse; 1 clean -> pass; anything else
  # (including an unreadable manifest, swept-with-nothing above) -> refuse
  # without the "secret material" wording, so a broken read can never pass
  # green by sweeping nothing.
  rc=0
  sweep . "$MANIFEST" || rc=$?
  case "$rc" in
    0)
      echo "lint: secret material in the tree (brief §8): the lines above" >&2
      exit 1
      ;;
    1)
      exit 0
      ;;
    *)
      exit "$rc"
      ;;
  esac
fi
