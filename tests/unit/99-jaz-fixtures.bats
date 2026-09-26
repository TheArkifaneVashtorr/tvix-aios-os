#!/usr/bin/env bats
# tools/experiments/jaz/{filter_evidence.py,scrub_plan_byref.py} — the two
# scripts build-fixtures.sh (docs/superpowers/specs/
# 2026-09-25-jaz-planning-experiment-design.md, D5) relies on to keep a
# fixture branch inside the cutoff and free of the experiment's own
# vocabulary: filter_evidence.py cuts one evidence stream at a real
# event-time field and strips identity keys; scrub_plan_byref.py drops the
# JAZ/arm/experiment vocabulary from a workflow file's comments and meta
# strings without touching its code. Python3 only (stdlib), same as the
# scripts themselves.

setup() {
  JAZ_DIR="$BATS_TEST_DIRNAME/../../tools/experiments/jaz"
  FILTER_PY="$JAZ_DIR/filter_evidence.py"
  SCRUB_PY="$JAZ_DIR/scrub_plan_byref.py"
  T="$(mktemp -d "${BATS_TEST_TMPDIR:-/tmp}/jazfix.XXXXXX")"
}

teardown() {
  rm -rf "$T"
}

# `! grep ...` directly in a test body is a trap under bats' set -e: bash
# never treats a `!`-negated command's failure as script-ending, so a bare
# `! grep -q pattern file` silently passes even when the pattern IS present.
# Route the negative assertion through `run` (which always captures the
# status without tripping set -e) and check it explicitly instead.
assert_absent() {
  run grep -qi "$1" "$2"
  [ "$status" -ne 0 ]
}

@test "filter_evidence.py keeps rows at/before the cutoff, drops rows after it, and strips an identity key" {
  local input="$T/stream.jsonl" outfile="$T/out.jsonl"
  {
    # kept: before cutoff (1000), carries an email key to be stripped
    printf '{"key":"k1","ts_epoch":900,"email":"a@example.invalid","v":1}\n'
    # kept: exactly at cutoff
    printf '{"key":"k2","ts_epoch":1000,"v":1}\n'
    # dropped: after cutoff
    printf '{"key":"k3","ts_epoch":1100,"v":1}\n'
    # dropped: no event-time field at all (unknowable is never kept)
    printf '{"key":"k4","v":1}\n'
    # dropped: a NaN epoch (json.loads' NaN extension) is not finite, so
    # never "<=cutoff" -- kills the `math.isfinite` check if it is ever
    # removed (measured: the row leaks through and the count goes to 3)
    printf '{"key":"k5","ts_epoch":NaN,"v":1}\n'
  } >"$input"

  # NOT `run ... >"$outfile"`: bats' `run` captures the command's stdout via
  # its own command substitution, which wins over an outer `>` redirect --
  # the file would come out empty regardless of what the script wrote.
  # Redirect directly and read `$?` instead.
  python3 "$FILTER_PY" ts_epoch epoch 1000 <"$input" >"$outfile" 2>"$T/stderr.log"
  local rc=$?
  [ "$rc" -eq 0 ]

  [ "$(wc -l <"$outfile")" -eq 2 ]
  grep -q '"key": "k1"' "$outfile"
  grep -q '"key": "k2"' "$outfile"
  assert_absent '"key": "k3"' "$outfile"
  assert_absent '"key": "k4"' "$outfile"
  assert_absent '"key": "k5"' "$outfile"
  # the identity key is gone from the row it was carried on, the rest of
  # that row survives
  assert_absent 'email' "$outfile"
  assert_absent 'example.invalid' "$outfile"
  grep -q '"key": "k1"' "$outfile"
}

@test "filter_evidence.py --exists-root refuses an absolute path and a .. escape" {
  local root="$T/tree" input="$T/gates.jsonl" outfile="$T/out.jsonl"
  mkdir -p "$root/docs/reviews"
  # a file that genuinely exists, both inside and outside the tree root --
  # the existence override must still refuse to look outside root even
  # though the file is really there.
  echo real >"$root/docs/reviews/real.md"
  mkdir -p "$T/outside"
  echo secret >"$T/outside/escape.md"

  {
    printf '{"key":"OK","review_commit_ts":null,"review_path":"docs/reviews/real.md"}\n'
    printf '{"key":"ABS","review_commit_ts":null,"review_path":"%s"}\n' "$T/outside/escape.md"
    printf '{"key":"DOTDOT","review_commit_ts":null,"review_path":"../outside/escape.md"}\n'
  } >"$input"

  python3 "$FILTER_PY" review_commit_ts iso 1000 --exists-root "$root" --exists-field review_path \
    <"$input" >"$outfile" 2>"$T/stderr.log"
  local rc=$?
  [ "$rc" -eq 0 ]

  grep -q '"key": "OK"' "$outfile"
  assert_absent '"key": "ABS"' "$outfile"
  assert_absent '"key": "DOTDOT"' "$outfile"
}

@test "scrub_plan_byref.py removes the experiment's vocabulary from comments and meta strings, leaves code alone" {
  local input="$T/plan-byref.js" outfile="$T/scrubbed.js"
  {
    printf '// .claude/workflows/plan-byref.js — arm B of the JAZ planning experiment, pinned.\n'
    printf '// Spec: docs/superpowers/specs/2026-09-25-jaz-planning-experiment-design.md\n'
    printf '\n'
    printf 'export const meta = {\n'
    printf "  name: 'plan-byref',\n"
    printf "  description:\n"
    printf "    'JAZ experiment arm B: a by-reference drafter',\n"
    printf "  whenToUse:\n"
    printf "    'Only for the JAZ planning experiment',\n"
    printf '}\n'
    printf '\n'
    printf '// this block names the experiment, an arm, JAZ — drop the whole block\n'
    printf '// second line of the same block, no trigger word here\n'
    printf 'function draftPrompt() {\n'
    printf "  return 'a distinctive marker line the scrub must never touch'\n"
    printf '}\n'
  } >"$input"

  run python3 "$SCRUB_PY" "$input" "$outfile"
  [ "$status" -eq 0 ]

  assert_absent 'JAZ' "$outfile"
  assert_absent 'arm B' "$outfile"
  assert_absent 'experiment' "$outfile"
  assert_absent '2026-09-25-jaz' "$outfile"

  # code is untouched: the function name, the distinctive return line, and
  # meta.name survive byte-identical
  grep -q 'function draftPrompt' "$outfile"
  grep -q 'a distinctive marker line the scrub must never touch' "$outfile"
  grep -q "name: 'plan-byref'" "$outfile"
}
