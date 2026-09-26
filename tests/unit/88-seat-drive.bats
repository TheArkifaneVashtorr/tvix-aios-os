#!/usr/bin/env bats
# SD7: seat-drive.sh -- launch a "drive" job: resolve the orchestrate row,
# seed an isolated DSH_HOME from the driver's skill set, and submit a drive
# job through seat-submit (faked on PATH: it records its argv and prints a
# fixed id). The routing table, the shared home and FACTORY_ROOT are all
# fixtures under BATS_TEST_TMPDIR; nothing here touches the operator's real
# ~/factory, the real shared DSH_HOME or a real seat unit. Every script runs
# through "$REAL_BASH", never a shebang (the build sandbox has no /usr/bin/env).

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

setup_file() {
  bats_require_minimum_version 1.5.0

  # The orchestrate fixture: a default any/any/any row plus an orchestrate
  # row that is strictly more specific, so the lookup lands on m/o high.
  cat >"$BATS_FILE_TMPDIR/routing.toml" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/default"
effort = "low"

[[route]]
route = "openrouter"
role = "orchestrate"
kind = "any"
size = "any"
model = "m/o"
effort = "high"
EOF

  # The same table WITHOUT the orchestrate row: the lookup must fall back to
  # the any/any/any default (so a deleted orchestrate row is visible in the
  # printed line, not silently routed elsewhere).
  cat >"$BATS_FILE_TMPDIR/routing-no-orchestrate.toml" <<'EOF'
[[route]]
route = "openrouter"
role = "any"
kind = "any"
size = "any"
model = "m/default"
effort = "low"
EOF
}

setup() {
  REAL_BASH="$(command -v bash)"
  # The seat's own environment carries OPENROUTER_REASONING_EFFORT; the base
  # cases must resolve from the routing table, so clear both overrides here
  # and set them explicitly (via `env`) only in the override cases.
  unset OPENROUTER_MODEL OPENROUTER_REASONING_EFFORT

  # A fake seat-submit on PATH: records its argv one word per line, then
  # prints a fixed, printf-shaped job id (the id seat-drive.sh captures and
  # re-prints). The shebang is $REAL_BASH, never /usr/bin/env.
  mkdir -p "$BATS_TEST_TMPDIR/bin"
  cat >"$BATS_TEST_TMPDIR/bin/seat-submit" <<FAKE
#!$REAL_BASH
: > "\$SEAT_SUBMIT_RECORD"
for a in "\$@"; do printf '%s\\n' "\$a" >> "\$SEAT_SUBMIT_RECORD"; done
printf '20260908-120000-abcdef\\n'
FAKE
  chmod +x "$BATS_TEST_TMPDIR/bin/seat-submit"
  export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
  export SEAT_SUBMIT_RECORD="$BATS_TEST_TMPDIR/seat-submit-argv"

  export FACTORY_ROOT="$BATS_TEST_TMPDIR/root"
  export FACTORY_TOOLBOX_REPO="$BATS_TEST_TMPDIR/toolbox"
  mkdir -p "$FACTORY_TOOLBOX_REPO"

  # A fake shared home: skills/ and AGENTS.md to symlink into the seeded home,
  # and a settings.yaml carrying a saved selection the seed must strip.
  export FACTORY_SHARED_DSH_HOME_SRC="$BATS_TEST_TMPDIR/shared"
  mkdir -p "$FACTORY_SHARED_DSH_HOME_SRC/skills"
  printf 'skills\n' >"$FACTORY_SHARED_DSH_HOME_SRC/AGENTS.md"
  cat >"$FACTORY_SHARED_DSH_HOME_SRC/settings.yaml" <<'EOF'
agent-default-model:
  model: saved/one
some-other-key: value
EOF

  export FACTORY_ROUTING_TABLE="$BATS_FILE_TMPDIR/routing.toml"
}

@test "seat-drive resolves the orchestrate row, seeds an isolated home, and submits drive" {
  run "$REAL_BASH" "$SEAT/seat-drive.sh" --port 43210 --no-start
  [ "$status" -eq 0 ]
  script_output=$output

  mapfile -t argv <"$SEAT_SUBMIT_RECORD"
  [ "${argv[0]}" = "drive" ]
  [ "${argv[1]}" = "--workspace" ]
  [ "${argv[2]}" = "$FACTORY_TOOLBOX_REPO" ]
  [ "${argv[3]}" = "--dsh-home" ]
  [[ "${argv[4]}" == "$FACTORY_ROOT/drive/"*".dsh-home" ]]
  [ "${argv[5]}" = "--model" ]
  [ "${argv[6]}" = "m/o" ]
  [ "${argv[7]}" = "--effort" ]
  [ "${argv[8]}" = "high" ]
  [ "${argv[9]}" = "--port" ]
  [ "${argv[10]}" = "43210" ]
  [ "${argv[11]}" = "--no-start" ]

  # The seeded home: settings.yaml has no saved/one (the selection was
  # stripped), skills is a symlink into the shared home, AGENTS.md too.
  dsh_home="${argv[4]}"
  [ -d "$dsh_home" ]
  [ -f "$dsh_home/settings.yaml" ]
  # The seeded home's settings.yaml has no saved/one (the selection was
  # stripped): a status the test reads, so the assertion can actually fail
  # (a `! grep` command is exempt from errexit and would always pass).
  run grep -q 'saved/one' "$dsh_home/settings.yaml"
  [ "$status" -eq 1 ]
  [ -L "$dsh_home/skills" ]
  [ "$(readlink "$dsh_home/skills")" = "$FACTORY_SHARED_DSH_HOME_SRC/skills" ]
  [ -L "$dsh_home/AGENTS.md" ]

  # stdout carries the resolved route line, the DSH_HOME notice and the id.
  [[ "$script_output" == *"orchestrate/any/any rung 1 → m/o high"* ]]
  [[ "$script_output" == *"seat-drive: DSH_HOME $dsh_home"* ]]
  [[ "$script_output" == *"20260908-120000-abcdef"* ]]
}

@test "OPENROUTER_REASONING_EFFORT overrides the routed effort and prints the override" {
  run --separate-stderr env OPENROUTER_REASONING_EFFORT=medium \
    "$REAL_BASH" "$SEAT/seat-drive.sh" --port 43210 --no-start
  [ "$status" -eq 0 ]

  mapfile -t argv <"$SEAT_SUBMIT_RECORD"
  [ "${argv[8]}" = "medium" ]
  [[ "$stderr" == *"seat-drive: explicit effort (override)"* ]]
}

@test "OPENROUTER_MODEL overrides the routed model and prints the override" {
  run --separate-stderr env OPENROUTER_MODEL=deepseek/deepseek-v4-flash \
    "$REAL_BASH" "$SEAT/seat-drive.sh" --port 43210 --no-start
  [ "$status" -eq 0 ]

  mapfile -t argv <"$SEAT_SUBMIT_RECORD"
  [ "${argv[6]}" = "deepseek/deepseek-v4-flash" ]
  [[ "$stderr" == *"seat-drive: explicit model (override)"* ]]
}

@test "--dsh-home skips seeding and submits the given home" {
  given="$BATS_TEST_TMPDIR/given"
  mkdir -p "$given"

  run "$REAL_BASH" "$SEAT/seat-drive.sh" --port 43210 --no-start --dsh-home "$given"
  [ "$status" -eq 0 ]

  mapfile -t argv <"$SEAT_SUBMIT_RECORD"
  [ "${argv[4]}" = "$given" ]
  # No seeded home was created under FACTORY_ROOT/drive.
  [ ! -e "$FACTORY_ROOT/drive" ]
}

@test "a table without the orchestrate row routes to the any/any/any default" {
  export FACTORY_ROUTING_TABLE="$BATS_FILE_TMPDIR/routing-no-orchestrate.toml"

  run "$REAL_BASH" "$SEAT/seat-drive.sh" --port 43210 --no-start
  [ "$status" -eq 0 ]

  mapfile -t argv <"$SEAT_SUBMIT_RECORD"
  [ "${argv[6]}" = "m/default" ]
  [[ "$output" == *"orchestrate/any/any rung 1 → m/default low"* ]]
}

@test "--port 80 is refused" {
  run "$REAL_BASH" "$SEAT/seat-drive.sh" --port 80 --no-start
  [ "$status" -eq 2 ]
}

@test "seat-drive waits for url.txt and prints its line" {
  jobs="$BATS_TEST_TMPDIR/jobs"
  mkdir -p "$jobs/20260908-120000-abcdef"
  # The unit's url.txt appears a moment after the submit (the fake seat-submit
  # prints the fixed id 20260908-120000-abcdef); the wait must find it under
  # SEAT_DRIVE_JOBS_DIR and print its line last on stdout.
  (
    sleep 1
    printf 'http://10.100.4.2:43210\n' >"$jobs/20260908-120000-abcdef/url.txt"
  ) &

  run env SEAT_DRIVE_JOBS_DIR="$jobs" SEAT_DRIVE_URL_TIMEOUT=6 \
    "$REAL_BASH" "$SEAT/seat-drive.sh" --port 43210
  [ "$status" -eq 0 ]
  [ "$(tail -n 1 <<<"$output")" = "http://10.100.4.2:43210" ]
}

@test "seat-drive reports a missing url.txt after the timeout" {
  jobs="$BATS_TEST_TMPDIR/jobs"
  mkdir -p "$jobs"

  run --separate-stderr env SEAT_DRIVE_JOBS_DIR="$jobs" SEAT_DRIVE_URL_TIMEOUT=2 \
    "$REAL_BASH" "$SEAT/seat-drive.sh" --port 43210
  [ "$status" -eq 0 ]
  [[ "$stderr" == *"no url.txt after 2 s — journalctl -u seat@20260908-120000-abcdef"* ]]
  [[ "$output" == *"20260908-120000-abcdef"* ]]
  [[ "$output" != *"http://"* ]]
}