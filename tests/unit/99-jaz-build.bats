#!/usr/bin/env bats
# tools/experiments/jaz/build-fixtures.sh, end to end against a tiny
# synthetic repo (Opus review, TESTS item 8) -- not the three real
# nixos-agent-env commits (those need the real host tree and are exercised
# by hand during the actual build). Covers: the branch names neither the
# experiment nor a token, a file dated after the cutoff never lands, the
# neutral SNAPSHOT.md/notice/commit author-subject, and derived/gates'
# null-review_commit_ts existence rule. FIXTURE_TABLE (build-fixtures.sh's
# test-only seam) points the real script at this synthetic repo's own
# commit instead of the three hardcoded ones.

setup_file() {
  JAZ_DIR="$BATS_TEST_DIRNAME/../../tools/experiments/jaz"
  BUILD_SH="${BUILD_SH:-$JAZ_DIR/build-fixtures.sh}"
  SRC="$BATS_FILE_TMPDIR/src"
  OUT="$BATS_FILE_TMPDIR/out"
  WF="$BATS_FILE_TMPDIR/workflows"
  STORE="$BATS_FILE_TMPDIR/store"
  mkdir -p "$SRC" "$WF" "$STORE/derived"

  git -C "$SRC" init -q
  git -C "$SRC" config user.name "src-author"
  git -C "$SRC" config user.email "src-author@example.invalid"

  # -- the fixture commit (build-fixtures.sh's `commit`, the parent of the
  #    landing commit below) -- committer date fixes the cutoff.
  mkdir -p "$SRC/docs/bugs" "$SRC/docs/reviews"
  # Privacy redaction fodder (a later @test rebuilds with REDACT_PRIVACY=1):
  # a distinctive fake serial in the fixture tree, and the commit author
  # email below (src-author@example.invalid) doubles as the operator-email
  # rule's source.
  cat >"$SRC/keys.toml" <<'EOF'
[keys.test-a]
serial = 87654321
EOF
  cat >"$SRC/docs/bugs/2026-09-09-drive-seat-url-token.md" <<'EOF'
captured token in a bug report; must be deleted outright.
EOF
  cat >"$SRC/docs/reviews/2026-09-09-opus-review-tok1-TOK1.md" <<'EOF'
---
plan_defect: none
mutants_total: 1
mutants_killed: 1
mutants_outside_named: 0
model: opus
---
# Opus gate — seat run tok1, task TOK1 — APPROVED

the captured line: dsh web: http://10.0.0.5:9/?token=SECRETVALUE123
EOF
  # A file dated far after this commit's own committer date, planted
  # directly into the fixture snapshot to exercise the after-cutoff safety
  # net (a real repo should never have one; this is deliberately
  # constructed to prove the check catches it if it ever did).
  cat >"$SRC/docs/reviews/2099-01-01-opus-review-late-LATE1.md" <<'EOF'
---
plan_defect: none
mutants_total: 1
mutants_killed: 1
mutants_outside_named: 0
model: opus
---
# Opus gate — seat run late1, task LATE1 — APPROVED

this file must never survive into the fixture branch.
EOF
  git -C "$SRC" add -A
  # After 2026-09-09 (the TOK1 review's own filename date): a cutoff
  # earlier than a review's filename date would make the SEPARATE
  # after-cutoff safety net (build-fixtures.sh's own dated-filename scan)
  # delete TOK1 outright before the token= scrub path is even exercised.
  GIT_AUTHOR_DATE="2026-09-10T00:00:00" GIT_COMMITTER_DATE="2026-09-10T00:00:00" \
    git -C "$SRC" commit -q -m "the fixture snapshot"
  FIXTURE_COMMIT=$(git -C "$SRC" rev-parse HEAD)
  CUTOFF_EPOCH=$(git -C "$SRC" log -1 --format=%ct "$FIXTURE_COMMIT")

  # -- the landing commit (its PARENT is what build-fixtures.sh archives)
  echo "landed" >"$SRC/docs/landed.md"
  git -C "$SRC" add -A
  GIT_AUTHOR_DATE="2026-09-11T00:00:00" GIT_COMMITTER_DATE="2026-09-11T00:00:00" \
    git -C "$SRC" commit -q -m "the landing commit"
  LANDING_COMMIT=$(git -C "$SRC" rev-parse HEAD)

  # -- a placeholder plan.js (build-fixtures.sh requires one to exist)
  cat >"$WF/plan.js" <<'EOF'
export const meta = { name: "plan" }
EOF

  # -- a fake derived/gates.jsonl exercising the null-review_commit_ts rule:
  #    kept-by-time, dropped-by-time, a NaN time (never "before"), a
  #    null-time row whose review_path exists in the archived tree (kept),
  #    and a null-time row whose review_path does not exist (dropped).
  before=$((CUTOFF_EPOCH - 100))
  after=$((CUTOFF_EPOCH + 100))
  {
    printf '{"key":"BEFORE","review_commit_ts":"%s","review_path":"docs/reviews/2026-09-09-opus-review-tok1-TOK1.md"}\n' \
      "$(date -u -d "@$before" +%Y-%m-%dT%H:%M:%SZ)"
    printf '{"key":"AFTER","review_commit_ts":"%s","review_path":"docs/reviews/2026-09-09-opus-review-tok1-TOK1.md"}\n' \
      "$(date -u -d "@$after" +%Y-%m-%dT%H:%M:%SZ)"
    printf '{"key":"NANTIME","review_commit_ts":NaN,"review_path":"docs/reviews/2026-09-09-opus-review-tok1-TOK1.md"}\n'
    printf '{"key":"NULLTIME-EXISTS","review_commit_ts":null,"review_path":"docs/reviews/2026-09-09-opus-review-tok1-TOK1.md"}\n'
    printf '{"key":"NULLTIME-GONE","review_commit_ts":null,"review_path":"docs/reviews/nonexistent-NOPE.md"}\n'
  } >"$STORE/derived/gates.jsonl"

  # Not under bats' setup_file `set -e`: a non-zero build is a test result
  # (asserted below), never a reason to abort setup_file before the other
  # tests get a chance to report why.
  set +e
  FIXTURE_TABLE="TESTKEY=$LANDING_COMMIT" REDACT_PRIVACY=0 EVIDENCE_STORE_SRC="$STORE" \
    bash "$BUILD_SH" "$SRC" "$OUT" "$WF" >"$BATS_FILE_TMPDIR/build.out" 2>"$BATS_FILE_TMPDIR/build.err"
  echo "$?" >"$BATS_FILE_TMPDIR/build.status"
  set -e

  # setup_file runs once per file, but each @test is its own bash process:
  # a plain shell variable set here (LANDING_COMMIT, BUILD_SH, JAZ_DIR) does
  # not survive into a @test's `run`/subshell context even when `export`ed
  # (measured: an `export` list here left them unresolved -- "bash: :  No
  # such file or directory" -- while the file-backed values below and the
  # ones setup() recomputes from $BATS_FILE_TMPDIR paths work every time).
  echo "$LANDING_COMMIT" >"$BATS_FILE_TMPDIR/landing_commit"
  echo "$BUILD_SH" >"$BATS_FILE_TMPDIR/build_sh"
  echo "$JAZ_DIR" >"$BATS_FILE_TMPDIR/jaz_dir"
}

teardown_file() {
  rm -rf "$BATS_FILE_TMPDIR"
}

setup() {
  # setup_file runs once per file in its own process; each @test is a
  # separate bash process that does not inherit its plain (or even
  # `export`ed) shell variables, only $BATS_FILE_TMPDIR itself and whatever
  # setup_file wrote under it. Recompute/re-read everything from there.
  SRC="$BATS_FILE_TMPDIR/src"
  OUT="$BATS_FILE_TMPDIR/out"
  WF="$BATS_FILE_TMPDIR/workflows"
  STORE="$BATS_FILE_TMPDIR/store"
  BUILD_STATUS=$(cat "$BATS_FILE_TMPDIR/build.status")
  LANDING_COMMIT=$(cat "$BATS_FILE_TMPDIR/landing_commit")
  BUILD_SH=$(cat "$BATS_FILE_TMPDIR/build_sh")
  JAZ_DIR=$(cat "$BATS_FILE_TMPDIR/jaz_dir")
}

assert_absent() {
  run grep -riq "$1" "$2"
  [ "$status" -ne 0 ]
}

@test "the build exits 0" {
  [ "$BUILD_STATUS" -eq 0 ] || {
    cat "$BATS_FILE_TMPDIR/build.out" "$BATS_FILE_TMPDIR/build.err" >&2
    false
  }
}

@test "no experiment-name match anywhere the build controls" {
  [ "$BUILD_STATUS" -eq 0 ]
  run grep -rliE 'jaz|experiment|arm [ab]\b|by-reference' "$OUT/.claude" "$OUT/tools/cloud" "$OUT/SNAPSHOT.md"
  [ "$status" -ne 0 ]
}

@test "no captured token survives anywhere in the branch" {
  [ "$BUILD_STATUS" -eq 0 ]
  assert_absent 'token=SECRETVALUE123' "$OUT"
}

@test "the post-cutoff file never lands" {
  [ "$BUILD_STATUS" -eq 0 ]
  [ ! -e "$OUT/docs/reviews/2099-01-01-opus-review-late-LATE1.md" ]
}

@test "the captured-token bug file is deleted outright" {
  [ "$BUILD_STATUS" -eq 0 ]
  [ ! -e "$OUT/docs/bugs/2026-09-09-drive-seat-url-token.md" ]
}

@test "the token review is scrubbed to the neutral notice, front matter and verdict kept" {
  [ "$BUILD_STATUS" -eq 0 ]
  local f="$OUT/docs/reviews/2026-09-09-opus-review-tok1-TOK1.md"
  [ -f "$f" ]
  grep -q '\[body redacted: contained a credential\]' "$f"
  grep -q 'plan_defect: none' "$f"
  grep -q '# Opus gate — seat run tok1, task TOK1 — APPROVED' "$f"
  assert_absent 'SECRETVALUE123' "$f"
}

@test "the commit author and subject are neutral" {
  [ "$BUILD_STATUS" -eq 0 ]
  run git -C "$OUT" log -1 --format='%an <%ae> %s' fixture/TESTKEY
  [ "$status" -eq 0 ]
  [ "$output" = "snapshot <noreply@example.invalid> snapshot" ]
}

@test "SNAPSHOT.md is neutral and EXPERIMENT.md never lands" {
  [ "$BUILD_STATUS" -eq 0 ]
  [ -f "$OUT/SNAPSHOT.md" ]
  [ ! -e "$OUT/EXPERIMENT.md" ]
  grep -q 'bash tools/cloud/setup.sh' "$OUT/SNAPSHOT.md"
}

@test "derived/gates.jsonl: time rule and the null-time existence override" {
  [ "$BUILD_STATUS" -eq 0 ]
  local f="$OUT/evidence/derived/gates.jsonl"
  [ -f "$f" ]
  grep -q '"key": "BEFORE"' "$f"
  assert_absent '"key": "AFTER"' "$f"
  assert_absent '"key": "NANTIME"' "$f"
  grep -q '"key": "NULLTIME-EXISTS"' "$f"
  assert_absent '"key": "NULLTIME-GONE"' "$f"
}

@test "REDACT_PRIVACY=1 replaces a planted serial and email, and the --check gate passes clean / fails on a planted survivor" {
  local out2="$BATS_FILE_TMPDIR/out-redact"
  local build2_out="$BATS_FILE_TMPDIR/build2.out" build2_err="$BATS_FILE_TMPDIR/build2.err"

  set +e
  FIXTURE_TABLE="TESTKEY2=$LANDING_COMMIT" REDACT_PRIVACY=1 EVIDENCE_STORE_SRC="$STORE" \
    bash "$BUILD_SH" "$SRC" "$out2" "$WF" >"$build2_out" 2>"$build2_err"
  local build2_status=$?
  set -e
  [ "$build2_status" -eq 0 ] || {
    cat "$build2_out" "$build2_err" >&2
    false
  }

  # the planted serial and the commit author email are gone from the branch
  run grep -rq '87654321' "$out2"
  [ "$status" -ne 0 ]
  run grep -rq 'src-author@example.invalid' "$out2"
  [ "$status" -ne 0 ]

  # the gate itself passes on the clean, already-redacted output
  run python3 "$JAZ_DIR/redact.py" "$out2" "$SRC" --check
  [ "$status" -eq 0 ]

  # and it is not a tautology: plant a survivor (the original serial, back
  # in the tree) and confirm the SAME gate call now fails
  echo "87654321" >"$out2/planted-survivor.txt"
  run python3 "$JAZ_DIR/redact.py" "$out2" "$SRC" --check
  [ "$status" -ne 0 ]
  [[ "$output" == *"LEAK"*"planted-survivor.txt"*"yubikey-serial"* ]]
}
