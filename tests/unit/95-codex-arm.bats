#!/usr/bin/env bats
# CA1: the codex arm of the seat driver (FACTORY_SEAT=codex). codex exec runs
# in the workspace clone, the .result model/effort/route/seat and usage come
# from the banner and the rollout, the classifier sees only the agent's output,
# and the brief carries the codex trailer pair. Exercised with fakes on PATH --
# the same idiom as 80-seat-driver.bats: a fake codex that prints the banner and
# writes the rollout, a fake dsh-openrouter that never runs under codex, a real
# git workspace, and FACTORY_ROOT under the tmpdir. Every script runs through
# $REAL_BASH (never exec'd by path: the build sandbox has no /usr/bin/env).

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup_file() {
  bats_require_minimum_version 1.5.0
  # No test in this file may write to the operator's real runs dir
  # ($HOME/factory/runs). Snapshot it once, before any test runs, so
  # teardown_file can prove none gained an entry.
  if [ -d "$HOME/factory/runs" ]; then
    LC_ALL=C ls -A1 "$HOME/factory/runs" 2>/dev/null |
      LC_ALL=C sort >"$BATS_FILE_TMPDIR/runs.before"
  else
    : >"$BATS_FILE_TMPDIR/runs.before"
  fi
}

teardown_file() {
  if [ -d "$HOME/factory/runs" ]; then
    LC_ALL=C ls -A1 "$HOME/factory/runs" 2>/dev/null |
      LC_ALL=C sort >"$BATS_FILE_TMPDIR/runs.after"
  else
    : >"$BATS_FILE_TMPDIR/runs.after"
  fi
  if ! diff -u "$BATS_FILE_TMPDIR/runs.before" "$BATS_FILE_TMPDIR/runs.after" >&2; then
    printf 'a test wrote to the real ~/factory/runs\n' >&2
    return 1
  fi
}

setup() {
  REAL_BASH="$(command -v bash)"
  PLAN="$BATS_TEST_TMPDIR/plan.md"
  : >"$PLAN"
  export FACTORY_PLAN="$PLAN"
  export FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"
  export FACTORY_RUNS="$BATS_TEST_TMPDIR/factory/runs"
  export FACTORY_SEAT=codex
  unset OPENROUTER_MODEL OPENROUTER_REASONING_EFFORT
  # CA1b item 1: SAFE_PATH is the ambient PATH with every directory that holds
  # an executable `codex` removed. This host has /home/dalhaka/.local/bin/codex,
  # so a helper that passes "$BIN:$PATH" would let row 2 reach the real binary
  # and fire `codex exec … --sandbox danger-full-access` from a unit test.
  # Every driver invocation below passes "$BIN:$SAFE_PATH" (never "$BIN:$PATH"),
  # so with the fake absent `command -v codex` under the helper's PATH finds
  # nothing on any host.
  SAFE_PATH=
  IFS=: read -r -a _path_dirs <<<"$PATH"
  for _d in "${_path_dirs[@]}"; do
    [ -x "$_d/codex" ] && continue
    if [ -z "$SAFE_PATH" ]; then
      SAFE_PATH=$_d
    else
      SAFE_PATH="$SAFE_PATH:$_d"
    fi
  done
}

# Build a real git workspace at $WS: a base commit on main, task/K1 branched
# from it with <n> commits on top (0 = the branch sits on the base), and --
# unless the second arg is "0" -- a .factory-meta recording that base sha at the
# path factory_task_base_sha reads ($FACTORY_ROOT/ws/r1/K1/.factory-meta).
mk_ws_with_commits() {
  local n=$1 meta=${2:-1} i=0
  WS="$BATS_TEST_TMPDIR/ws"
  rm -rf "$WS"
  git init -q -b main "$WS"
  git -C "$WS" config user.email t@x
  git -C "$WS" config user.name t
  printf 'base\n' >"$WS/f"
  git -C "$WS" add f
  git -C "$WS" commit -qm base
  BASE_SHA=$(git -C "$WS" rev-parse HEAD)
  git -C "$WS" checkout -qb task/K1
  while [ "$i" -lt "$n" ]; do
    printf '%s\n' "$i" >"$WS/work$i"
    git -C "$WS" add "work$i"
    git -C "$WS" commit -qm "work $i"
    i=$((i + 1))
  done
  if [ "$meta" = "1" ]; then
    mkdir -p "$FACTORY_ROOT/ws/r1/K1"
    printf 'base_sha=%s\n' "$BASE_SHA" >"$FACTORY_ROOT/ws/r1/K1/.factory-meta"
  fi
}

# Write a fake codex to $BIN. With --version it prints ${FAKE_VERSION}; otherwise
# it records its argv/cwd/stdin to $REC, prints the banner (unless
# FAKE_NO_BANNER=1), echoes the stdin after a `user` line and a `codex` marker,
# prints ${FAKE_BODY} (four default result lines) and the token line, writes the
# rollout (unless FAKE_NO_ROLLOUT=1), then sleeps ${FAKE_SLEEP} and exits
# ${FAKE_EXIT}.
fake_codex() {
  cat >"$BIN/codex" <<'FXC'
#!/usr/bin/env bash
sid=${FAKE_SID:-0f1e2d3c-4b5a-4c6d-8e9f-0a1b2c3d4e5f}
if [ "$1" = "--version" ]; then
  printf '%s\n' "${FAKE_VERSION:-codex-cli 0.153.4}"
  exit 0
fi
input=$(cat)
printf 'args=%s\n' "$*" >>"$REC"
printf 'cwd=%s\n' "$PWD" >>"$REC"
printf 'stdin_begin\n' >>"$REC"
printf '%s\n' "$input" >>"$REC"
printf 'stdin_end\n' >>"$REC"
if [ "${FAKE_NO_BANNER:-}" != "1" ]; then
  printf 'OpenAI Codex v0.153.4\n'
  printf '%s\n' '--------'
  printf 'workdir: %s\n' "$PWD"
  printf 'model: %s\n' "${FAKE_MODEL:-gpt-6-astra}"
  printf 'provider: openai\n'
  printf 'approval: never\n'
  printf 'sandbox: danger-full-access\n'
  printf 'reasoning effort: %s\n' "${FAKE_EFFORT:-medium}"
  printf 'reasoning summaries: auto\n'
  printf 'session id: %s\n' "$sid"
  printf '%s\n' '--------'
  printf 'user\n'
  printf '%s\n' "$input"
  printf 'codex\n'
fi
if [ -n "${FAKE_BODY:-}" ]; then
  printf '%s\n' "$FAKE_BODY"
else
  printf 'FACTORY-RESULT status=done\n'
  printf 'FACTORY-CHECKS unit=pass\n'
  printf 'FACTORY-COMMITS 1\n'
  printf 'FACTORY-NOTES the arm ran\n'
fi
printf 'tokens used\n'
printf '%s\n' "${FAKE_TOKENS:-12345}"
if [ "${FAKE_NO_ROLLOUT:-}" != "1" ]; then
  rd="$CODEX_HOME/sessions/2026/09/08"
  mkdir -p "$rd"
  rf="$rd/rollout-2026-09-08T00-00-00-$sid.jsonl"
  {
    printf '{"timestamp":"2026-09-08T00:00:00.000Z","type":"session_meta","payload":{}}\n'
    printf '{"timestamp":"2026-09-08T00:00:01.000Z","type":"turn_context","payload":{"model":"%s","effort":"%s"}}\n' "${FAKE_MODEL:-gpt-6-astra}" "${FAKE_EFFORT:-medium}"
    i=0
    while [ "$i" -lt "${FAKE_FILLER:-57}" ]; do
      printf '{"timestamp":"2026-09-08T00:10:00.000Z","type":"response_item","payload":{}}\n'
      i=$((i + 1))
    done
    printf '{"timestamp":"2026-09-08T00:40:00.000Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":%s,"cached_input_tokens":%s,"output_tokens":%s,"reasoning_output_tokens":%s}}}}\n' "${FAKE_IN:-1710988}" "${FAKE_CACHED:-1642368}" "${FAKE_OUT:-13584}" "${FAKE_REASON:-3631}"
  } >"$rf"
fi
sleep "${FAKE_SLEEP:-0}"
exit "${FAKE_EXIT:-0}"
FXC
  sed -i "1s@.*@#!$REAL_BASH@" "$BIN/codex"
  chmod +x "$BIN/codex"
}

# Write a fake dsh-openrouter to $BIN that records its own use and prints the
# four default result lines -- so a codex run must never reach it.
fake_dsh() {
  cat >"$BIN/dsh-openrouter" <<'FXD'
#!/usr/bin/env bash
: >"$DSH_CALLED"
printf 'FACTORY-RESULT status=done\n'
printf 'FACTORY-CHECKS unit=pass\n'
printf 'FACTORY-COMMITS 1\n'
printf 'FACTORY-NOTES the arm ran\n'
FXD
  sed -i "1s@.*@#!$REAL_BASH@" "$BIN/dsh-openrouter"
  chmod +x "$BIN/dsh-openrouter"
}

# Run the real factory-task in a seat_copy against the workspace/brief built by
# mk_ws_with_commits/fake_codex. FACTORY_SEAT defaults to codex (setup); each
# test overrides with export/unset. Extra args are forwarded to factory-task.
run_codex_task() {
  SEAT_COPY="$BATS_TEST_TMPDIR/seat"
  rm -rf "$SEAT_COPY"
  cp -r "$SEAT" "$SEAT_COPY"
  chmod -R u+w "$SEAT_COPY"
  sed -i "1s@.*@#!$REAL_BASH@" "$SEAT_COPY/factory-brief"
  WS_CALLED="$BATS_TEST_TMPDIR/ws-called"
  rm -f "$WS_CALLED"
  cat >"$SEAT_COPY/factory-ws" <<FWS
#!$REAL_BASH
: >"$WS_CALLED"
printf '%s\n' "$WS"
FWS
  chmod +x "$SEAT_COPY/factory-ws"
  FX="$BATS_TEST_TMPDIR/toolbox"
  rm -rf "$FX"
  mkdir -p "$FX/docs/ledger"
  cat >"$FX/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  [ -s "$PLAN" ] || cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

model: decoy/model

session id: 00000000-0000-4000-8000-000000000000

body one.
EOF
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO"
  SHARE="$BATS_TEST_TMPDIR/share"
  mkdir -p "$SHARE"
  BIN="$BATS_TEST_TMPDIR/bin"
  rm -rf "$BIN"
  mkdir -p "$BIN"
  if [ "${NO_CODEX:-0}" != "1" ]; then fake_codex; fi
  fake_dsh
  codex_home_dir="$BATS_TEST_TMPDIR/codex-home"
  mkdir -p "$codex_home_dir"
  if [ ! -e "$codex_home_dir/config.toml" ]; then
    if [ "${NO_DEFAULT_CONFIG:-0}" != "1" ]; then
      printf 'model = "gpt-6-astra"\nmodel_reasoning_effort = "medium"\n' >"$codex_home_dir/config.toml"
    fi
  fi
  REC="$BATS_TEST_TMPDIR/rec"
  rm -f "$REC"
  DSH_CALLED="$BATS_TEST_TMPDIR/dsh-called"
  rm -f "$DSH_CALLED"
  EV="$BATS_TEST_TMPDIR/ev.sh"
  printf '#!%s\nexit 0\n' "$REAL_BASH" >"$EV"
  chmod +x "$EV"
  FACTORY_TOOLBOX_REPO="$FX" FACTORY_PLAN="$PLAN" \
    FACTORY_SHARED_DSH_HOME_SRC="$SHARE" PATH="$BIN:$SAFE_PATH" FACTORY_SEAT_UNIT=0 \
    CODEX_HOME="$codex_home_dir" REC="$REC" DSH_CALLED="$DSH_CALLED" \
    FACTORY_PYTHON3_CMD="$(command -v python3)" FACTORY_EVIDENCE_CMD="$EV" \
    run "$REAL_BASH" "$SEAT_COPY/factory-task" r1 "$REPO" K1 "$@"
}

@test "FACTORY_SEAT outside the rule refuses at exit 2 before a run dir or workspace" {
  # Mutant: drop the `*)` arm -> the run proceeds and $FACTORY_RUNS/r1 exists;
  # match `codex*` -> `'codex '` is accepted.
  mk_ws_with_commits 1
  for seat in bogus Codex 'codex '; do
    rm -rf "$FACTORY_RUNS"
    FACTORY_SEAT="$seat" run_codex_task
    [ "$status" -eq 2 ]
    [[ "$output" == *"FACTORY_SEAT=$seat is not a seat arm"* ]]
    [ ! -e "$FACTORY_RUNS/r1" ]
    [ ! -e "$WS_CALLED" ]
  done
}

@test "FACTORY_SEAT=codex with no codex on PATH refuses at exit 2 before a run dir" {
  # Mutant: drop `command -v codex` -> the launch fails later with a run dir.
  mk_ws_with_commits 1
  NO_CODEX=1 run_codex_task
  [ "$status" -eq 2 ]
  [[ "$output" == *"FACTORY_SEAT=codex but no codex on PATH"* ]]
  [ ! -e "$FACTORY_RUNS/r1" ]
  [ ! -e "$WS_CALLED" ]
}

@test "empty or unset FACTORY_SEAT keeps today's dsh arm" {
  # Mutant: treat empty as codex -> $REC exists (the fake codex ran).
  mk_ws_with_commits 1
  FACTORY_SEAT= run_codex_task
  [ "$status" -eq 0 ]
  [ -e "$DSH_CALLED" ]
  [ ! -e "$REC" ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"route: implement/code/M"* ]]
  [[ "$output" == *"model: deepseek/deepseek-v4-pro-0813"* ]]
  [ -d "$FACTORY_RUNS/r1/K1.dsh-home" ]
  rm -f "$DSH_CALLED" "$REC"
  rm -rf "$FACTORY_RUNS"
  unset FACTORY_SEAT
  run_codex_task
  [ "$status" -eq 0 ]
  [ -e "$DSH_CALLED" ]
  [ ! -e "$REC" ]
}

@test "the codex launch: argv, workspace, brief, no dsh-home, and the banner-sourced .result" {
  # Mutant: `-` dropped / --ephemeral or --json added / `-m` always -> the args
  # line; the seed kept -> K1.dsh-home exists; route_label left implement/...;
  # the seat: line omitted.
  mk_ws_with_commits 1
  run_codex_task
  [ "$status" -eq 0 ]
  run cat "$REC"
  args='args=exec -c features.plugins=false -c otel.metrics_exporter="none" --sandbox danger-full-access --color never -'
  grep -Fxq "$args" "$REC"
  [[ "$output" == *"cwd=$WS"* ]]
  [[ "$output" == *"### K1 (code, M) — t"* ]]
  [[ "$output" == *"## WORKSPACE RULES"* ]]
  [[ "$output" == *"Generated-By: codex-cli 0.153.4 / gpt-6-astra (codex exec, factory run r1)"* ]]
  [[ "$output" == *"Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>"* ]]
  [ ! -e "$DSH_CALLED" ]
  [ ! -e "$FACTORY_RUNS/r1/K1.dsh-home" ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"model: gpt-6-astra"* ]]
  [[ "$output" == *"effort: medium"* ]]
  [[ "$output" == *"route: codex/code/M"* ]]
  [[ "$output" == *"seat: codex 0f1e2d3c-4b5a-4c6d-8e9f-0a1b2c3d4e5f"* ]]
  [[ "$output" == *"\"input\": 68620"* ]]
  [[ "$output" == *"\"cacheRead\": 1642368"* ]]
  [[ "$output" == *"\"output\": 13584"* ]]
  [[ "$output" == *"\"reasoning\": 3631"* ]]
  [[ "$output" == *"\"events\": 60"* ]]
  [[ "$output" == *"\"model\": \"gpt-6-astra\""* ]]
  [[ "$output" == *"error_class: none"* ]]
}

@test "--model is passed as -m, the route is explicit, and the trailer names it" {
  # Mutant: `-m` after `-` -> the args line; route_label kept codex/...
  mk_ws_with_commits 1
  export FAKE_MODEL=gpt-6-mini
  run_codex_task --model gpt-6-mini
  [ "$status" -eq 0 ]
  run cat "$REC"
  [[ "$output" == *"args=exec -c features.plugins=false -c otel.metrics_exporter=\"none\" --sandbox danger-full-access --color never -m gpt-6-mini -"* ]]
  [[ "$output" == *"Generated-By: codex-cli 0.153.4 / gpt-6-mini (codex exec, factory run r1)"* ]]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"route: explicit"* ]]
}

@test "the banner window wins over the config and the plan-body decoys" {
  # Mutant: grep the whole log (last match) -> the decoys win; the config read
  # before the banner -> cfg-model in the .result.
  mk_ws_with_commits 1
  mkdir -p "$BATS_TEST_TMPDIR/codex-home"
  printf 'model = "cfg-model"\nmodel_reasoning_effort = "high"\n' >"$BATS_TEST_TMPDIR/codex-home/config.toml"
  run_codex_task
  [ "$status" -eq 0 ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"model: gpt-6-astra"* ]]
  [[ "$output" == *"effort: medium"* ]]
  [[ "$output" == *"seat: codex 0f1e2d3c-4b5a-4c6d-8e9f-0a1b2c3d4e5f"* ]]
  [[ "$output" != *"model: decoy/model"* ]]
  [[ "$output" != *"model: cfg-model"* ]]
  [[ "$output" != *"00000000-0000-4000-8000-000000000000"* ]]
  run cat "$REC"
  [[ "$output" == *"Generated-By: codex-cli 0.153.4 / cfg-model (codex exec, factory run r1)"* ]]
}

@test "trailer-time model comes from the config, else unknown, else the top-level table rule" {
  # Mutant: read the whole file -> table-model; match $key* without the = test
  # -> high.
  mk_ws_with_commits 1
  mkdir -p "$BATS_TEST_TMPDIR/codex-home"
  printf 'model = "cfg-model"\nmodel_reasoning_effort = "high"\n' >"$BATS_TEST_TMPDIR/codex-home/config.toml"
  run_codex_task
  run cat "$REC"
  [[ "$output" == *"Generated-By: codex-cli 0.153.4 / cfg-model"* ]]

  # no config.toml -> unknown
  rm -rf "$BATS_TEST_TMPDIR/codex-home" "$FACTORY_RUNS"
  mkdir -p "$BATS_TEST_TMPDIR/codex-home"
  NO_DEFAULT_CONFIG=1 run_codex_task
  run cat "$REC"
  [[ "$output" == *"Generated-By: codex-cli 0.153.4 / unknown"* ]]

  # a model = line only under a table -> unknown
  rm -rf "$BATS_TEST_TMPDIR/codex-home" "$FACTORY_RUNS"
  mkdir -p "$BATS_TEST_TMPDIR/codex-home"
  printf '[profiles.fast]\nmodel = "table-model"\n' >"$BATS_TEST_TMPDIR/codex-home/config.toml"
  run_codex_task
  run cat "$REC"
  [[ "$output" == *"Generated-By: codex-cli 0.153.4 / unknown"* ]]

  # effort line above a model line -> the model line wins
  rm -rf "$BATS_TEST_TMPDIR/codex-home" "$FACTORY_RUNS"
  mkdir -p "$BATS_TEST_TMPDIR/codex-home"
  printf 'model_reasoning_effort = "high"\nmodel = "cfg-model"\n' >"$BATS_TEST_TMPDIR/codex-home/config.toml"
  run_codex_task
  run cat "$REC"
  [[ "$output" == *"Generated-By: codex-cli 0.153.4 / cfg-model"* ]]
}

@test "no banner: the .result falls back to the config, else unknown, and no seat: line" {
  # Mutant: skip the fallback -> unknown where cfg-model is expected; print
  # `seat: codex ` with an empty id.
  mk_ws_with_commits 1
  export FAKE_NO_BANNER=1
  mkdir -p "$BATS_TEST_TMPDIR/codex-home"
  printf 'model = "cfg-model"\nmodel_reasoning_effort = "high"\n' >"$BATS_TEST_TMPDIR/codex-home/config.toml"
  run_codex_task
  [ "$status" -eq 0 ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"model: cfg-model"* ]]
  [[ "$output" == *"effort: high"* ]]
  [ "$(grep -c '^seat:' "$FACTORY_RUNS/r1/K1.result" || true)" -eq 0 ]

  rm -rf "$BATS_TEST_TMPDIR/codex-home" "$FACTORY_RUNS"
  mkdir -p "$BATS_TEST_TMPDIR/codex-home"
  NO_DEFAULT_CONFIG=1 run_codex_task
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"model: unknown"* ]]
  [[ "$output" == *"effort: unknown"* ]]
}

@test "usage reads the rollout named by the session id, ignoring a newer decoy" {
  # Mutant: pick the newest instead of the id -> "input": 999.
  mk_ws_with_commits 1
  mkdir -p "$BATS_TEST_TMPDIR/codex-home/sessions/2026/09/08"
  decoy="$BATS_TEST_TMPDIR/codex-home/sessions/2026/09/08/rollout-2026-09-09T00-00-00-11111111-2222-4333-8444-555555555555.jsonl"
  printf '{"timestamp":"2026-09-08T00:40:00.000Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":999,"cached_input_tokens":0,"output_tokens":0,"reasoning_output_tokens":0}}}}\n' >"$decoy"
  touch -d '+1 day' "$decoy"
  run_codex_task
  [ "$status" -eq 0 ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"\"input\": 68620"* ]]
  [[ "$output" != *"\"input\": 999"* ]]
}

@test "usage reads the newest rollout since the marker, ignoring an older decoy" {
  # Mutant: drop `-newer "$marker"` -> the decoy (sort|tail -n1) wins -> 999.
  mk_ws_with_commits 1
  export FAKE_NO_BANNER=1
  mkdir -p "$BATS_TEST_TMPDIR/codex-home/sessions/2026/09/08"
  decoy="$BATS_TEST_TMPDIR/codex-home/sessions/2026/09/08/rollout-2026-09-09T00-00-00-aaaa1111-2222-4333-8444-555555555555.jsonl"
  printf '{"timestamp":"2026-09-08T00:40:00.000Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":999,"cached_input_tokens":0,"output_tokens":0,"reasoning_output_tokens":0}}}}\n' >"$decoy"
  touch -d '2020-01-01' "$decoy"
  run_codex_task
  [ "$status" -eq 0 ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"\"input\": 68620"* ]]
  [[ "$output" != *"\"input\": 999"* ]]
}

@test "no rollout keeps {} and the zero event count reaches boot-failure" {
  # Mutant: default events to 50 -> none; hand the raw log to the classifier ->
  # provider-error (the banner's `provider: openai` is in its tail).
  mk_ws_with_commits 0
  export FAKE_NO_ROLLOUT=1
  export FAKE_BODY=$'FACTORY-RESULT status=failed\nFACTORY-CHECKS unit=fail\nFACTORY-COMMITS 0\nFACTORY-NOTES it broke'
  run_codex_task
  [ "$status" -eq 2 ]
  [[ "$output" == *"no rollout named by session id"* ]]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"usage: {}"* ]]
  [[ "$output" == *"error_class: boot-failure"* ]]
}

@test "the classifier sees only the agent's output, never the brief or the banner" {
  # Mutant: the raw log -> provider-error in the first case; the first `codex`
  # line anywhere -> provider-error in the second; an empty copy always -> none
  # in the third.
  mk_ws_with_commits 0
  export FAKE_BODY=$'FACTORY-RESULT status=failed\nFACTORY-CHECKS unit=fail\nFACTORY-COMMITS 0\nFACTORY-NOTES it broke'

  # (a) keywords in the brief only -> none (events 60)
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

502 upstream provider

body.
EOF
  run_codex_task
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"error_class: none"* ]]

  # (b) a bare `codex` line inside the brief, then a keyword -> still none
  rm -rf "$FACTORY_RUNS"
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

codex

502 upstream provider

body.
EOF
  run_codex_task
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"error_class: none"* ]]

  # (c) the keyword in the reply -> provider-error
  rm -rf "$FACTORY_RUNS"
  export FAKE_BODY=$'FACTORY-RESULT status=failed\nFACTORY-CHECKS unit=fail\nFACTORY-COMMITS 0\nFACTORY-NOTES it broke\n502 Bad Gateway from the provider'
  cat >"$PLAN" <<'EOF'
### K1 (code, M) — t

body.
EOF
  run_codex_task
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"error_class: provider-error"* ]]
}

@test "OPENROUTER_MODEL/REASONING_EFFORT and the routing table are ignored under codex" {
  # Mutant: honour OPENROUTER_MODEL -> -m x; call factory_route -> the routing
  # table unusable line appears; log the warning per variable read -> 2.
  mk_ws_with_commits 1
  export OPENROUTER_MODEL=x OPENROUTER_REASONING_EFFORT=high
  export FACTORY_ROUTING_TABLE=/nonexistent
  run_codex_task
  [ "$status" -eq 0 ]
  [[ "$output" != *"routing table unusable"* ]]
  [ "$(grep -c 'warning: OPENROUTER_MODEL is ignored under FACTORY_SEAT=codex' <<<"$output")" = "1" ]
  [ "$(grep -c 'warning: OPENROUTER_REASONING_EFFORT is ignored under FACTORY_SEAT=codex' <<<"$output")" = "1" ]
  args='args=exec -c features.plugins=false -c otel.metrics_exporter="none" --sandbox danger-full-access --color never -'
  grep -Fxq "$args" "$REC"
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"model: gpt-6-astra"* ]]
  [[ "$output" == *"effort: medium"* ]]
}

@test "a codex run that times out records exit_code 124, timeout, and still parses usage" {
  # Mutant (struck by CA1b item 6): `exit_code=$?` of tee is equivalent under
  # `set -o pipefail`, so no test can discriminate it; the 124 pin stands.
  mk_ws_with_commits 0
  export FAKE_SLEEP=3
  export FACTORY_TIMEOUT=1
  run_codex_task
  [ "$status" -eq 2 ]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"exit_code: 124"* ]]
  [[ "$output" == *"error_class: timeout"* ]]
  [[ "$output" == *"\"input\": 68620"* ]]
}

@test "FACTORY_SEAT_VERSION is the last token of codex --version, or the placeholder" {
  # Mutant: skip the validation -> `codex-cli garbage`.
  mk_ws_with_commits 1
  export FAKE_VERSION='codex-cli 0.153.4'
  run_codex_task
  run cat "$REC"
  [[ "$output" == *"Generated-By: codex-cli 0.153.4 /"* ]]

  rm -rf "$FACTORY_RUNS"
  export FAKE_VERSION='garbage'
  run_codex_task
  [ "$(grep -c 'printed no version' <<<"$output")" = "1" ]
  run cat "$REC"
  [[ "$output" == *"Generated-By: codex-cli <version> /"* ]]
  [[ "$output" == *"Co-Authored-By: Codex CLI <version> <noreply@openai.com>"* ]]

  rm -rf "$FACTORY_RUNS"
  export FAKE_VERSION='codex-cli 0.154.0-alpha.1'
  run_codex_task
  run cat "$REC"
  [[ "$output" == *"Generated-By: codex-cli 0.154.0-alpha.1 /"* ]]
}

@test "factory-wave passes FACTORY_SEAT through to every factory-task" {
  # Mutant: unset FACTORY_SEAT (or env -u) in factory-wave -> empty.
  repo="$BATS_TEST_TMPDIR/repo"
  git init -q -b main "$repo"
  git -C "$repo" config user.email t@x
  git -C "$repo" config user.name t
  printf 'base\n' >"$repo/f"
  git -C "$repo" add f
  git -C "$repo" commit -qm base
  planfile="$BATS_TEST_TMPDIR/plan.md"
  printf '### K1 (code, M) — t\n\nbody.\n' >"$planfile"
  seen="$BATS_TEST_TMPDIR/seen"
  psbin="$BATS_TEST_TMPDIR/psbin"; mkdir -p "$psbin"
  cat >"$psbin/ps" <<FAKE
#!$REAL_BASH
pid=""
prev=""
for a in "\$@"; do [ "\$prev" = "-p" ] && pid="\$a"; prev="\$a"; done
printf '%s\n' "\${pid:-0}"
FAKE
  chmod +x "$psbin/ps"
  printf '#!%s\nexit 9\n' "$REAL_BASH" >"$psbin/setsid"
  chmod +x "$psbin/setsid"
  fact="$BATS_TEST_TMPDIR/factbin"; mkdir -p "$fact"
  cat >"$fact/factory-task" <<FAKE
#!$REAL_BASH
printf '%s\n' "\${FACTORY_SEAT:-}" >"$seen"
run="\$1"; key="\$3"; d="\$FACTORY_ROOT/runs/\$run"; mkdir -p "\$d"
printf 'FACTORY-RESULT status=done\nFACTORY-CHECKS unit=pass\nFACTORY-COMMITS 1\nFACTORY-NOTES ok\nwall_s: 0\n' >"\$d/\$key.result"
FAKE
  chmod +x "$fact/factory-task"
  root="$BATS_TEST_TMPDIR/factory"
  FACTORY_SEAT=codex FACTORY_BIN_OVERRIDE="$fact" FACTORY_PLAN="$planfile" \
    PATH="$psbin:$SAFE_PATH" FACTORY_ROOT="$root" \
    run "$REAL_BASH" "$SEAT/factory-wave" r1 "$repo" "K1"
  [ "$status" -eq 0 ]
  run cat "$seen"
  [ "$output" = "codex" ]
}

@test "factory-brief prints the codex trailer pair, and the dsh pair for any other seat" {
  # Mutant: case-insensitive match -> Codex differs; drop the <version>
  # fallback -> an empty version; swap the order -> the adjacency assertion.
  printf '### K1 (code, M) — t\n\nbody.\n' >"$PLAN"
  FACTORY_SEAT=codex FACTORY_SEAT_VERSION=0.153.4 FACTORY_MODEL=gpt-6-astra FACTORY_RUN=cx2 \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1
  [[ "$output" == *$'Generated-By: codex-cli 0.153.4 / gpt-6-astra (codex exec, factory run cx2)\n    Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>'* ]]
  [[ "$output" != *"Claude Fable"* ]]
  [[ "$output" != *"dsh 0.1.2"* ]]

  FACTORY_SEAT=codex FACTORY_RUN=cx2 FACTORY_MODEL=gpt-6-astra \
    run "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1
  [[ "$output" == *"Generated-By: codex-cli <version> / gpt-6-astra (codex exec, factory run cx2)"* ]]
  [[ "$output" == *"Co-Authored-By: Codex CLI <version> <noreply@openai.com>"* ]]

  env -u FACTORY_SEAT FACTORY_RUN=cx2 "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1 >"$BATS_TEST_TMPDIR/o1"
  FACTORY_SEAT= FACTORY_RUN=cx2 "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1 >"$BATS_TEST_TMPDIR/o2"
  FACTORY_SEAT=Codex FACTORY_RUN=cx2 "$REAL_BASH" "$SEAT/factory-brief" "$PLAN" K1 >"$BATS_TEST_TMPDIR/o3"
  cmp "$BATS_TEST_TMPDIR/o1" "$BATS_TEST_TMPDIR/o2"
  cmp "$BATS_TEST_TMPDIR/o2" "$BATS_TEST_TMPDIR/o3"
  grep -q "Generated-By: dsh 0.1.2-rc.1 /" "$BATS_TEST_TMPDIR/o1"
  grep -q "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" "$BATS_TEST_TMPDIR/o1"
}

@test "factory-codex-usage.py summarises a rollout and is robust to torn and deep lines" {
  # Mutant: input = input_tokens -> 1710988; the last token_count regardless of
  # info -> zeros; count raw lines -> 63; raise on a decode error -> exit 1; the
  # narrow except -> (d) exits 1; first/last from token_count lines only -> 600.0.
  fx="$BATS_TEST_TMPDIR/r18a.jsonl"
  {
    printf '{"timestamp":"2026-09-08T00:00:00.000Z","type":"session_meta","payload":{}}\n'
    printf '{"timestamp":"2026-09-08T00:00:01.000Z","type":"turn_context","payload":{"model":"gpt-6-astra","effort":"medium"}}\n'
    i=0
    while [ "$i" -lt 57 ]; do
      printf '{"timestamp":"2026-09-08T00:10:00.000Z","type":"response_item","payload":{}}\n'
      i=$((i + 1))
    done
    printf '{"timestamp":"2026-09-08T00:40:00.000Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":1710988,"cached_input_tokens":1642368,"output_tokens":13584,"reasoning_output_tokens":3631}}}}\n'
    printf '{"timestamp":"2026-09-08T00:41:00Z","type":"event_msg","payload":{"type":"token_cou\n'
    printf '[]\n'
    printf '{"timestamp":"2026-09-08T00:50:00.123456789Z","type":"event_msg","payload":{"type":"token_count","info":null}}\n'
  } >"$fx"
  run python3 "$SEAT/factory-codex-usage.py" <"$fx"
  [ "$status" -eq 0 ]
  [ "$output" = '{"model": "gpt-6-astra", "events": 61, "input": 68620, "output": 13584, "cacheRead": 1642368, "reasoning": 3631, "duration_s": 3000.123456}' ]

  run python3 "$SEAT/factory-codex-usage.py" </dev/null
  [ "$status" -eq 0 ]
  [ "$output" = '{"model": null, "events": 0, "input": 0, "output": 0, "cacheRead": 0, "reasoning": 0, "duration_s": null}' ]

  head -c 2000 /dev/urandom >"$BATS_TEST_TMPDIR/r18c.bin"
  run python3 "$SEAT/factory-codex-usage.py" <"$BATS_TEST_TMPDIR/r18c.bin"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"events": 0'* ]]

  python3 -c 'print("[" * 100000 + "]" * 100000)' >"$BATS_TEST_TMPDIR/r18d.txt"
  {
    printf '{"timestamp":"2026-09-08T00:00:00.000Z","type":"session_meta","payload":{}}\n'
    printf '{"timestamp":"2026-09-08T00:00:01.000Z","type":"turn_context","payload":{"model":"gpt-6-astra","effort":"medium"}}\n'
    i=0
    while [ "$i" -lt 57 ]; do
      printf '{"timestamp":"2026-09-08T00:10:00.000Z","type":"response_item","payload":{}}\n'
      i=$((i + 1))
    done
    printf '{"timestamp":"2026-09-08T00:40:00.000Z","type":"event_msg","payload":{"type":"token_count","info":{"total_token_usage":{"input_tokens":1710988,"cached_input_tokens":1642368,"output_tokens":13584,"reasoning_output_tokens":3631}}}}\n'
    cat "$BATS_TEST_TMPDIR/r18d.txt"
    printf '\n'
  } >"$BATS_TEST_TMPDIR/r18d.jsonl"
  run python3 "$SEAT/factory-codex-usage.py" <"$BATS_TEST_TMPDIR/r18d.jsonl"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"events": 60'* ]]
  [[ "$output" == *'"input": 68620'* ]]
}

@test "the helper's PATH holds no codex: command -v codex through it prints nothing" {
  # Pins item 1's SAFE_PATH: with the fake absent (an empty $BIN stand-in) the
  # helper's PATH -- "$BIN:$SAFE_PATH" -- resolves no codex even on a host whose
  # own PATH does (/home/dalhaka/.local/bin/codex here). Under the buggy
  # "PATH=$BIN:$PATH" spelling this row would print the real binary on core.
  bin="$BATS_TEST_TMPDIR/path-bin"
  rm -rf "$bin"
  mkdir -p "$bin"
  PATH="$bin:$SAFE_PATH" run command -v codex
  [ "$status" -eq 1 ]
  [ -z "$output" ]
}

@test "a malformed session id in the banner is dropped, and usage still parses via the marker" {
  # Mutant: loosen the session-id regex ([0-9a-fA-F-]{36}) to (.+) -> the seat:
  # line carries "codex not-a-uuid".
  mk_ws_with_commits 1
  export FAKE_SID=not-a-uuid
  run_codex_task
  [ "$status" -eq 0 ]
  [[ "$output" != *"no banner and no rollout"* ]]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"\"input\": 68620"* ]]
  [ "$(grep -c '^seat:' "$FACTORY_RUNS/r1/K1.result" || true)" -eq 0 ]
}

@test "the classifier copy is .log-free and removed, leaving only the task log" {
  # Mutant: rm -f replaced by : -> a leaked .agent-K1.* entry (no .log); the
  # template given a .log suffix with the removal also dropped -> a second
  # *.log beside K1.log (the .log-free name is what keeps even a leak off
  # tasks.py's *.log glob).
  mk_ws_with_commits 1
  run_codex_task
  [ "$status" -eq 0 ]
  run ls -A1 "$FACTORY_RUNS/r1"
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$output" | grep -c '\.log$' || true)" -eq 1 ]
  [ "$(printf '%s\n' "$output" | grep -c '\.agent-' || true)" -eq 0 ]
}

@test "no banner and no rollout refuses the usage source and logs the marker fallback" {
  # Mutant: drop the "no banner and no rollout" message -> $output has nothing.
  mk_ws_with_commits 0
  export FAKE_NO_BANNER=1
  export FAKE_NO_ROLLOUT=1
  export FAKE_BODY=$'FACTORY-RESULT status=failed\nFACTORY-CHECKS unit=fail\nFACTORY-COMMITS 0\nFACTORY-NOTES it broke'
  run_codex_task
  [ "$status" -eq 2 ]
  [[ "$output" == *"no banner and no rollout newer than the launch marker"* ]]
  run cat "$FACTORY_RUNS/r1/K1.result"
  [[ "$output" == *"usage: {}"* ]]
  [[ "$output" == *"error_class: boot-failure"* ]]
}