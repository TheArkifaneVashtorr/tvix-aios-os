#!/usr/bin/env bats
# dsh-openrouter (pkgs/dsh-openrouter/dsh-openrouter.sh): the DeepSeek Harness on the
# host, routed to OpenRouter. The transport tests boot the real pinned
# harness against tests/mocks/openai-fake.py on loopback -- no network, no
# key of any value. Shown to fail first (2026-09-03): the Authorization
# assertion fails when the overlay names the wrong apiKeyEnv, and the
# refusal test fails when the prefix loop is removed.

MOCK="$BATS_TEST_DIRNAME/../mocks/openai-fake.py"

# run --separate-stderr (the payload-warning test) needs bats >= 1.5;
# declare it above the first @test so the BW02 heuristic stays quiet.
bats_require_minimum_version 1.5.0

setup() {
  TMPHOME=$(mktemp -d)
  export TMPHOME
  export HOME="$TMPHOME"
  export XDG_CONFIG_HOME="$TMPHOME/.config"
  export XDG_DATA_HOME="$TMPHOME/.local/share"
  # Scope the nix fetcher cache default to the temp root so the ~35
  # non-cache cases never create/chmod the shared
  # /tmp/dsh-openrouter-cache-$(id -u); the cache-root cases override it
  # locally where they need to.
  export DSH_CACHE_ROOT="$TMPHOME"
  # N7: the hook guard reads this directly when driven as a bare process.
  export CLAUDE_PROJECT_DIR="$TMPHOME/ws"
  unset OPENROUTER_API_KEY OPENROUTER_KEY_FILE OPENROUTER_BASE_URL OPENROUTER_MODEL DSH_HOME DSH_PERMISSION_MODE XDG_CACHE_HOME DSH_HOOK_GUARD OPENROUTER_REASONING_EFFORT
  unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
  mkdir -p "$TMPHOME/ws"
  cd "$TMPHOME/ws"
  FAKE_PID=
  WEB_PIDS=()
}

teardown() {
  stop_web
  if [ -n "${FAKE_PID:-}" ]; then
    kill "$FAKE_PID" 2>/dev/null || true
    wait "$FAKE_PID" 2>/dev/null || true
  fi
  rm -rf "$TMPHOME"
}

make_key() {
  mkdir -p "$XDG_CONFIG_HOME/openrouter"
  (
    umask 077
    printf '%s\n' "${1-sk-or-test-key}" > "$XDG_CONFIG_HOME/openrouter/key"
  )
}

# Start the scripted upstream; sets FAKE_PORT and FAKE_CAPTURE.
start_fake() {
  printf '%s' "$1" > "$TMPHOME/script.json"
  FAKE_CAPTURE="$TMPHOME/capture.json"
  python3 "$MOCK" --script "$TMPHOME/script.json" --capture "$FAKE_CAPTURE" \
    > "$TMPHOME/fake.port" 2> "$TMPHOME/fake.err" &
  FAKE_PID=$!
  local i
  for i in $(seq 1 100); do
    if grep -q '^PORT=' "$TMPHOME/fake.port" 2>/dev/null; then
      break
    fi
    sleep 0.1
  done
  FAKE_PORT=$(sed -n 's/^PORT=//p' "$TMPHOME/fake.port")
  [ -n "$FAKE_PORT" ]
}

@test "dsh-openrouter --help exits 0 and names the key sources" {
  run dsh-openrouter --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"usage: dsh-openrouter"* ]]
  [[ "$output" == *"OPENROUTER_KEY_FILE"* ]]
}

@test "--help names the OPENROUTER_MODELS default the wrapper composes" {
  run dsh-openrouter --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"deepseek/deepseek-v4-flash moonshotai/kimi-k3 z-ai/glm-5.3 z-ai/glm-5.3-flash"* ]]
}

@test "--help documents the OPENROUTER_REASONING_EFFORT override and its default" {
  run dsh-openrouter --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"OPENROUTER_REASONING_EFFORT"* ]]
  [[ "$output" == *"medium"* ]]
}

@test "unknown option exits 2" {
  run dsh-openrouter --bogus
  [ "$status" -eq 2 ]
}

@test "refuses a workspace under ~/.claude before looking for a key" {
  mkdir -p "$HOME/.claude/some-project"
  cd "$HOME/.claude/some-project"
  run dsh-openrouter --dump-config
  [ "$status" -eq 3 ]
  [[ "$output" == *"local-only"* ]]
  # No key exists in this HOME: a refusal must come from the prefix check,
  # never from the key check that follows it.
  [[ "$output" != *"no key"* ]]
}

@test "refuses a workspace under ~/.codex before looking for a key" {
  mkdir -p "$HOME/.codex/some-project"
  cd "$HOME/.codex/some-project"
  run dsh-openrouter --dump-config
  [ "$status" -eq 3 ]
  [[ "$output" == *"local-only"* ]]
  # No key exists in this HOME: a refusal must come from the prefix check,
  # never from the key check that follows it.
  [[ "$output" != *"no key"* ]]
}

@test "refuses a workspace under ~/strategy" {
  mkdir -p "$HOME/strategy/economics"
  cd "$HOME/strategy/economics"
  make_key
  run dsh-openrouter --dump-config
  [ "$status" -eq 3 ]
  [[ "$output" == *"strategy"* ]]
}

@test "without any key: exit 4 and the creation recipe, nothing else" {
  run dsh-openrouter --dump-config
  [ "$status" -eq 4 ]
  [[ "$output" == *"no key"* ]]
  [[ "$output" == *"umask 077"* ]]
}

@test "a key file readable by the group is refused and never echoed" {
  make_key
  chmod 640 "$XDG_CONFIG_HOME/openrouter/key"
  run dsh-openrouter --dump-config
  [ "$status" -eq 4 ]
  [[ "$output" == *"0600"* ]]
  [[ "$output" != *"sk-or-test-key"* ]]
}

@test "a symlinked key file is refused" {
  make_key
  mv "$XDG_CONFIG_HOME/openrouter/key" "$XDG_CONFIG_HOME/openrouter/real"
  ln -s real "$XDG_CONFIG_HOME/openrouter/key"
  run dsh-openrouter --dump-config
  [ "$status" -eq 4 ]
  [[ "$output" == *"symlink"* ]]
}

@test "an empty key file is refused" {
  make_key ""
  run dsh-openrouter --dump-config
  [ "$status" -eq 4 ]
  [[ "$output" == *"empty"* ]]
}

@test "OPENROUTER_KEY_FILE overrides the default location" {
  (
    umask 077
    printf 'sk-or-elsewhere\n' > "$TMPHOME/other-key"
  )
  make_key
  chmod 644 "$XDG_CONFIG_HOME/openrouter/key"
  OPENROUTER_KEY_FILE="$TMPHOME/other-key" OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 \
    run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
}

@test "a malformed model id exits 5" {
  make_key
  run dsh-openrouter --model 'deepseek/v4 flash' --dump-config
  [ "$status" -eq 5 ]
}

@test "an unknown permission mode exits 5" {
  make_key
  run dsh-openrouter --permission yolo --dump-config
  [ "$status" -eq 5 ]
}

@test "a base URL that is not http(s) exits 5" {
  make_key
  OPENROUTER_BASE_URL=ftp://example.invalid run dsh-openrouter --dump-config
  [ "$status" -eq 5 ]
}

@test "--host passthrough to the browser UI is rejected" {
  make_key
  run dsh-openrouter -- --host 0.0.0.0
  [ "$status" -eq 2 ]
  [[ "$output" == *"127.0.0.1 only"* ]]
}

@test "composed profile carries exactly the OpenRouter route and no key" {
  make_key
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --model fake/model --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" == *"baseURL: http://127.0.0.1:1/api/v1"* ]]
  [[ "$output" == *"apiKeyEnv: OPENROUTER_API_KEY"* ]]
  [[ "$output" == *"provider: openrouter"* ]]
  [[ "$output" == *"model: fake/model"* ]]
  [[ "$output" != *"sk-or-test-key"* ]]
  printf '%s\n' "$output" | grep -A 8 '^- id: tool-web$' | grep -q 'disabled: true'
  # The built-in DeepSeek-platform route must not exist: a picker click on it
  # fails for want of a key nobody here has.
  printf '%s\n' "$output" | grep -A 2 '^- id: llm-deepseek$' | grep -q 'disabled: true'
  # The overlay it wrote is private to the operator.
  [ "$(stat -c %a "$XDG_DATA_HOME/dsh-openrouter/openrouter-route.yml")" = "600" ]
  [ "$(stat -c %a "$XDG_DATA_HOME/dsh-openrouter")" = "700" ]
}

@test "headless task reaches the upstream with the file's key and prints the answer" {
  make_key
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
first = chat[0]
assert first["path"] == "/api/v1/chat/completions", first["path"]
assert first["headers"].get("authorization") == "Bearer sk-or-test-key", first["headers"]
assert first["body"]["model"] == "deepseek/deepseek-v4-pro-0813", first["body"]["model"]
assert any(m.get("role") == "user" and "Reply with the word ok." in str(m.get("content")) for m in first["body"]["messages"]), first["body"]["messages"]
PY
}

@test "the default seat requests reasoning effort medium in the request body" {
  make_key
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
for r in chat:
    assert "reasoning" in r["body"], r["body"]
    assert r["body"]["reasoning"]["effort"] == "medium", r["body"]["reasoning"]
PY
}

@test "OPENROUTER_REASONING_EFFORT overrides the default reasoning effort" {
  make_key
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" OPENROUTER_REASONING_EFFORT=high \
    run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
for r in chat:
    assert "reasoning" in r["body"], r["body"]
    assert r["body"]["reasoning"]["effort"] == "high", r["body"]["reasoning"]
PY
}

@test "OPENROUTER_REASONING_EFFORT=xhigh reaches the wire as xhigh" {
  make_key
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" OPENROUTER_REASONING_EFFORT=xhigh \
    run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
for r in chat:
    assert "reasoning" in r["body"], r["body"]
    assert r["body"]["reasoning"]["effort"] == "xhigh", r["body"]["reasoning"]
PY
}

@test "an unknown OPENROUTER_REASONING_EFFORT exits 5" {
  make_key
  OPENROUTER_REASONING_EFFORT=yolo run dsh-openrouter --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"OPENROUTER_REASONING_EFFORT"* ]]
}

# Write a minimal $DSH_HOME/settings.yaml carrying a saved agent
# `reasoningEffort` (what the browser UI persists when the operator picks an
# effort in the model picker). N19: a saved `xhigh` used to refuse the launch
# with UNSUPPORTED_REASONING_EFFORT because the per-model reasoningEfforts map
# (N14) did not declare xhigh.
write_settings() {
  local effort="$1"
  mkdir -p "$XDG_DATA_HOME/dsh-openrouter"
  cat > "$XDG_DATA_HOME/dsh-openrouter/settings.yaml" <<YAML
ui-onboarding:
  welcomeNoticeVersion: 2026-08-13.1
agent-default-model:
  provider: openrouter
  model: deepseek/deepseek-v4-pro-0813
  reasoningEffort: $effort
YAML
}

@test "a saved settings.yaml reasoningEffort xhigh launches headless and sends effort xhigh" {
  make_key
  write_settings xhigh
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
main = next(r for r in chat if any(
    m.get("role") == "user" and "Reply with the word ok." in str(m.get("content"))
    for m in r["body"].get("messages", [])))
assert main["body"]["reasoning"]["effort"] == "xhigh", main["body"]["reasoning"]
PY
}

@test "a saved settings.yaml reasoningEffort off still sends none" {
  make_key
  write_settings off
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
main = next(r for r in chat if any(
    m.get("role") == "user" and "Reply with the word ok." in str(m.get("content"))
    for m in r["body"].get("messages", [])))
assert main["body"]["reasoning"]["effort"] == "none", main["body"]["reasoning"]
PY
}

# N21 (2026-09-05): OPENROUTER_REASONING_EFFORT only reached the route's
# `reasoning:` field, which is dsh's fallback when the *agent selection*
# carries no effort. A saved (or launch-written) `agent-default-model.
# reasoningEffort` in settings.yaml beat it, so an env var could be set and
# silently ignored. The fix writes the requested level into that selection
# before launch; these two tests pin the override (off beats a saved medium)
# and the non-override (no env var leaves a saved *high* alone -- high is
# non-default, and the settings.yaml read-back proves it was preserved, which
# a `medium` seed could not: medium equals the route default the wrapper would
# write).
@test "an explicit OPENROUTER_REASONING_EFFORT=off overrides a saved medium selection" {
  make_key
  write_settings medium
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" OPENROUTER_REASONING_EFFORT=off \
    run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
main = next(r for r in chat if any(
    m.get("role") == "user" and "Reply with the word ok." in str(m.get("content"))
    for m in r["body"].get("messages", [])))
assert main["body"]["reasoning"]["effort"] == "none", main["body"]["reasoning"]
PY
  # The override is written into the agent selection (settings.yaml), not
  # only into the route fallback, and the file is rewritten 0600.
  [ "$(grep -c 'reasoningEffort: off' "$XDG_DATA_HOME/dsh-openrouter/settings.yaml")" -eq 1 ]
  [ "$(stat -c %a "$XDG_DATA_HOME/dsh-openrouter/settings.yaml")" = "600" ]
}

@test "without the env var a saved reasoningEffort high is left intact" {
  make_key
  write_settings high
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
main = next(r for r in chat if any(
    m.get("role") == "user" and "Reply with the word ok." in str(m.get("content"))
    for m in r["body"].get("messages", [])))
assert main["body"]["reasoning"]["effort"] == "high", main["body"]["reasoning"]
PY
  # The non-default saved level survives the launch untouched: the wrapper
  # must not write anything into the selection when the env var is unset.
  [ "$(grep -c 'reasoningEffort: high' "$XDG_DATA_HOME/dsh-openrouter/settings.yaml")" -eq 1 ]
}

@test "OPENROUTER_API_KEY in the environment wins over the file and --model routes" {
  make_key
  start_fake '[{"content": "ENV-OK"}]'
  OPENROUTER_API_KEY=sk-or-from-env OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --model other/model --headless "hello"
  [ "$status" -eq 0 ]
  [[ "$output" == *"ENV-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat[0]["headers"].get("authorization") == "Bearer sk-or-from-env", chat[0]["headers"]
assert chat[0]["body"]["model"] == "other/model", chat[0]["body"]["model"]
PY
}

@test "OPENROUTER_MODELS adds picker entries on the same route, default first" {
  make_key
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 OPENROUTER_MODELS='deepseek/deepseek-v4-pro deepseek/deepseek-v4-flash' \
    run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" == *"- id: deepseek/deepseek-v4-flash"* ]]
  [[ "$output" == *"- id: deepseek/deepseek-v4-pro"* ]]
  # the default is not listed twice
  [ "$(printf '%s\n' "$output" | grep -c -- '- id: deepseek/deepseek-v4-flash$')" -eq 1 ]
}

@test "a malformed OPENROUTER_MODELS entry exits 5" {
  make_key
  OPENROUTER_MODELS='bad$model' run dsh-openrouter --dump-config
  [ "$status" -eq 5 ]
}

@test "DeepSeek V4 Flash is offered by default; OPENROUTER_MODELS='' removes it" {
  make_key
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" == *"- id: deepseek/deepseek-v4-flash"* ]]
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 OPENROUTER_MODELS='' run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" != *"deepseek-v4-flash"* ]]
}

# Boot the browser UI in the background against nothing (no request is made
# until a chat turn). $1 names the log; the rest are extra wrapper args.
# The child must close bats' own fd 3 (3>&-) or bats waits on it forever;
# WEB_PIDS is filled in the test's shell, never in a subshell, so teardown
# and the test itself can kill what they started.
start_web() {
  local log="$TMPHOME/web-$1.log"
  shift
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 dsh-openrouter -- --no-open "$@" \
    > "$log" 2>&1 3>&- &
  WEB_PIDS+=("$!")
  local i
  for i in $(seq 1 300); do
    if grep -q '^dsh web: http://127.0.0.1:' "$log" 2>/dev/null; then
      break
    fi
    sleep 0.1
  done
}

web_port() {
  sed -n 's#^dsh web: http://127.0.0.1:\([0-9]*\)/.*#\1#p' "$TMPHOME/web-$1.log"
}

stop_web() {
  local pid
  for pid in "${WEB_PIDS[@]+"${WEB_PIDS[@]}"}"; do
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
  WEB_PIDS=()
}

@test "two browser-UI sessions boot side by side on free ports (no --port)" {
  make_key
  WEB_PIDS=()
  start_web a
  start_web b
  first=$(web_port a)
  second=$(web_port b)
  stop_web
  [ -n "$first" ]
  [ -n "$second" ]
  [ "$first" != "$second" ]
  [ "$first" != "3080" ]
}

@test "an explicit -- --port is honoured" {
  make_key
  WEB_PIDS=()
  start_web c --port 38951
  got=$(web_port c)
  stop_web
  [ "$got" = "38951" ]
}

@test "a cache directory you do not own is refused with exit 5" {
  # Under a uid-0 caller the ownership guard passes and the wrapper would
  # chmod 700 the real /etc; the guard is only exercisable as a non-root user.
  [ "$(id -u)" -eq 0 ] && skip "the ownership guard needs a non-root caller"
  make_key
  # /etc is a system directory never owned by the caller, in the devShell and
  # the nix build sandbox alike. A directory INSIDE the temp root owned by
  # another uid would be preferable, but arranging one needs chown (root), so
  # /etc stands in for "a cache path the caller does not own".
  XDG_CACHE_HOME=/etc run dsh-openrouter --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"not owned by you"* ]]
}

@test "the default cache dir is DSH_CACHE_ROOT-scoped, created 0700 and owned by the caller" {
  make_key
  cache_dir="$TMPHOME/dsh-openrouter-cache-$(id -u)"
  [ ! -e "$cache_dir" ]
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 DSH_CACHE_ROOT="$TMPHOME" run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [ -d "$cache_dir" ]
  [ "$(stat -c %a "$cache_dir")" = "700" ]
  [ "$(stat -c %u "$cache_dir")" = "$(id -u)" ]
}

@test "an exported XDG_CACHE_HOME wins over DSH_CACHE_ROOT" {
  make_key
  cache_default="$TMPHOME/dsh-openrouter-cache-$(id -u)"
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 DSH_CACHE_ROOT="$TMPHOME" XDG_CACHE_HOME="$TMPHOME/mine" \
    run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [ -d "$TMPHOME/mine" ]
  [ ! -e "$cache_default" ]
}

@test "a symlink at the cache path is refused" {
  make_key
  cache_dir="$TMPHOME/dsh-openrouter-cache-$(id -u)"
  ln -s "$TMPHOME/dsh-openrouter-cache-target" "$cache_dir"
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 DSH_CACHE_ROOT="$TMPHOME" run dsh-openrouter --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"symlink"* ]]
  [[ "$output" == *"$cache_dir"* ]]
}

@test "the default model list covers the factory's five models" {
  make_key
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" == *"- id: deepseek/deepseek-v4-flash"* ]]
  [[ "$output" == *"- id: moonshotai/kimi-k3"* ]]
  [[ "$output" == *"- id: z-ai/glm-5.3"* ]]
  [[ "$output" == *"- id: z-ai/glm-5.3-flash"* ]]
  [ "$(printf '%s\n' "$output" | grep -c -- '- id: deepseek/deepseek-v4-flash$')" -eq 1 ]
  [ "$(printf '%s\n' "$output" | grep -c -- '- id: moonshotai/kimi-k3$')" -eq 1 ]
  [ "$(printf '%s\n' "$output" | grep -c -- '- id: z-ai/glm-5.3$')" -eq 1 ]
  [ "$(printf '%s\n' "$output" | grep -c -- '- id: z-ai/glm-5.3-flash$')" -eq 1 ]
  [ "$(printf '%s\n' "$output" | grep -c -- '- id: deepseek/deepseek-v4-pro-0813$')" -eq 1 ]
}

@test "a missing or empty \$DSH_HOME/skills warns on stderr" {
  make_key
  dsh_home="$XDG_DATA_HOME/dsh-openrouter"
  # absent: both the skill catalog and the bootstrap memory are missing.
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" == *"$dsh_home/skills"* ]]
  [[ "$output" == *"$dsh_home/AGENTS.md"* ]]
  [[ "$output" == *"ln -s"* ]]
  # a dangling symlink counts as missing.
  mkdir -p "$dsh_home"
  ln -s /nonexistent-target "$dsh_home/skills"
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" == *"$dsh_home/skills"* ]]
  # an empty directory counts as missing.
  rm -f "$dsh_home/skills"
  mkdir -p "$dsh_home/skills"
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" == *"$dsh_home/skills"* ]]
  # a non-empty directory warns nothing about skills.
  touch "$dsh_home/skills/some-skill"
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" != *"$dsh_home/skills"* ]]
}

@test "a deployed payload (symlinks to non-empty skills/ and AGENTS.md outside \$DSH_HOME) warns nothing" {
  make_key
  dsh_home="$XDG_DATA_HOME/dsh-openrouter"
  payload="$TMPHOME/payload"
  mkdir -p "$payload/skills"
  printf 'a skill\n' > "$payload/skills/some-skill"
  printf '# AGENTS\n' > "$payload/AGENTS.md"
  mkdir -p "$dsh_home"
  ln -s "$payload/skills" "$dsh_home/skills"
  ln -s "$payload/AGENTS.md" "$dsh_home/AGENTS.md"
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" != *"$dsh_home/skills"* ]]
  [[ "$output" != *"$dsh_home/AGENTS.md"* ]]
}

@test "the payload warning lands on stderr, not stdout" {
  make_key
  dsh_home="$XDG_DATA_HOME/dsh-openrouter"
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run --separate-stderr dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$stderr" == *"$dsh_home/skills"* ]]
  [[ "$output" != *"$dsh_home/skills"* ]]
}

# --- N7: the deny-only "protect the model" hook set (pkgs/dsh-openrouter/hook-guard.py) ---
# hook-guard is a pure stdin->stdout PreToolUse hook: it reads the bridge's
# payload, denies dangerous bash/edit/write calls by emitting a deny decision
# on stdout, and (round 2, review 2026-09-04: a workspace log file is
# erasable by the audited model and dirties the tree) prints one compact
# JSON record per denial to stderr instead -- no file. dsh's own hook bridge
# (@deepseek-ai/dsh-hook-protocol) captures that stderr and stores it
# verbatim as `stderrSummary` on the session transcript's `hook/result`
# event; `dsh-openrouter --denials` (dsh-denials.py) reads it back. Driven
# directly here -- a hook needs no harness. The wrapper wiring (the
# generated hooks.json and the bridge mount in --dump-config) is asserted
# at the bottom. Shown to fail first: the deny cases fail while the guard is
# a stub, and the wiring cases fail until the wrapper writes hooks.json.

# Build a PreToolUse hook payload for a tool and its tool_input (JSON text).
guard_payload() {
  printf '{"hook_event_name":"PreToolUse","tool_name":"%s","tool_input":%s}' "$1" "$2"
}

# Run hook-guard on a payload and assert it emitted a deny decision on stdout.
guard_denies() {
  # --separate-stderr: every denial now also writes a JSON record to
  # stderr (round 2, review 2026-09-04); plain `run` merges stdout and
  # stderr into $output, which would hand the deny-JSON assertion below two
  # JSON documents on one stream and fail it on "Extra data", not on the
  # denial itself.
  run --separate-stderr hook-guard <<< "$1"
  [ "$status" -eq 0 ] || return 1
  run python3 -c 'import json,sys; o=json.load(sys.stdin); h=o["hookSpecificOutput"]; assert h["hookEventName"]=="PreToolUse", o; assert h["permissionDecision"]=="deny", o; assert h["permissionDecisionReason"], o' <<< "$output"
  [ "$status" -eq 0 ]
}

# Run hook-guard on a payload and assert a deny whose stdout JSON carries a
# permissionDecisionReason containing $2 (the human-readable field
# `dsh-openrouter --denials` shows the operator).
guard_denies_reason() {
  local reason="$2"
  run --separate-stderr hook-guard <<< "$1"
  [ "$status" -eq 0 ] || return 1
  run python3 -c 'import json,sys; o=json.load(sys.stdin); h=o["hookSpecificOutput"]; assert h["hookEventName"]=="PreToolUse", o; assert h["permissionDecision"]=="deny", o; assert sys.argv[1] in h["permissionDecisionReason"], (h["permissionDecisionReason"], sys.argv[1])' "$reason" <<< "$output"
  [ "$status" -eq 0 ]
}

# Run hook-guard on a payload and assert it emitted nothing (allowed).
guard_allows() {
  run hook-guard <<< "$1"
  [ "$status" -eq 0 ] || return 1
  [ -z "$output" ]
}

@test "hook-guard denies sudo" {
  guard_denies "$(guard_payload bash '{"command":"sudo rm -rf /"}')"
}

@test "hook-guard denies nixos-rebuild" {
  guard_denies "$(guard_payload bash '{"command":"nixos-rebuild switch --flake .#core"}')"
}

@test "hook-guard denies systemctl --user start" {
  guard_denies "$(guard_payload bash '{"command":"systemctl --user start helm-serve"}')"
}

@test "hook-guard denies systemctl restart" {
  guard_denies "$(guard_payload bash '{"command":"systemctl restart nginx"}')"
}

@test "hook-guard denies a command reading the OpenRouter key file" {
  guard_denies "$(guard_payload bash '{"command":"cat ~/.config/openrouter/key"}')"
}

@test "hook-guard denies a command aimed at the Helm control port or its token" {
  guard_denies_reason "$(guard_payload bash '{"command":"curl -s -X POST http://127.0.0.1:7700/action/switch -d profile=gaming -d token=$(cat /run/user/1000/helm/token)"}')" "Helm control port"
  guard_denies "$(guard_payload bash '{"command":"cat /run/user/1000/helm/token"}')"
  guard_denies "$(guard_payload bash '{"command":"curl -s http://[::1]:7700/state"}')"
  guard_denies "$(guard_payload bash '{"command":"cat $XDG_RUNTIME_DIR/helm/token"}')"
  guard_denies "$(guard_payload bash '{"command":"wget -qO- localhost:7700/"}')"
}

@test "hook-guard leaves other loopback ports alone" {
  guard_allows "$(guard_payload bash '{"command":"curl -s http://127.0.0.1:8188/object_info | head -c 100"}')"
}

@test "hook-guard allows nix build, git status and read-only systemctl" {
  guard_allows "$(guard_payload bash '{"command":"nix build .#checks.x86_64-linux.unit"}')"
  guard_allows "$(guard_payload bash '{"command":"git status"}')"
  guard_allows "$(guard_payload bash '{"command":"systemctl status helm-serve"}')"
  guard_allows "$(guard_payload bash '{"command":"systemctl --user show-environment"}')"
}

@test "hook-guard denies an edit outside the project directory" {
  guard_denies "$(guard_payload edit '{"file_path":"/etc/passwd"}')"
}

@test "hook-guard denies writes under the protected prefixes" {
  local input
  for path in \
    "$TMPHOME/.claude/settings.json" \
    "$TMPHOME/.codex/auth.json" \
    "$TMPHOME/.config/openrouter/key" \
    "$TMPHOME/strategy/plan.md" \
    "/run/baskets/x" \
    "/var/lib/baskets/x" \
    "/var/lib/helm/x" \
    "/var/lib/egress-broker/x" \
    "/var/lib/lanes/x" \
    "/var/lib/secrets/x"; do
    input=$(printf '{"file_path":"%s"}' "$path")
    guard_denies "$(guard_payload write "$input")"
  done
}

@test "hook-guard denies a write under ~/.codex with the protected-path reason" {
  # SB7b pin: the decision-only path entry above cannot fail a guard that
  # dropped ~/.codex -- ~/.codex lies OUTSIDE CLAUDE_PROJECT_DIR, so the
  # outside-the-project rule denies it all on its own whatever
  # _protected_prefixes() holds. The deny REASON is what discriminates the
  # prefix rule from the outside-the-project rule, so this asserts that
  # ~/.codex is refused "under protected path" and that the reason names the
  # .codex prefix.
  local payload input
  input='{"file_path":"'"$TMPHOME"'/.codex/auth.json"}'
  payload="$(guard_payload write "$input")"
  guard_denies_reason "$payload" "under protected path"
  guard_denies_reason "$payload" "$TMPHOME/.codex"
}

@test "hook-guard denies a symlink inside the workspace resolving outside it" {
  mkdir -p "$TMPHOME/outside"
  echo hi > "$TMPHOME/outside/real"
  ln -s "$TMPHOME/outside/real" "$TMPHOME/ws/escape"
  guard_denies "$(guard_payload write "{\"file_path\":\"$TMPHOME/ws/escape\"}")"
}

@test "hook-guard allows a path inside the workspace" {
  guard_allows "$(guard_payload write "{\"file_path\":\"$TMPHOME/ws/file.txt\"}")"
}

# Round 2 (review 2026-09-04): the workspace log file is gone -- it was
# erasable by the audited model (its own edit/write checks never covered
# it) and left untracked dirt in whatever tree happened to be current. Every
# denial now writes exactly one JSON record to stderr, unconditionally
# (nothing to fail to write), while the deny decision itself still comes
# through on stdout. dsh's own hook bridge stores that stderr verbatim as
# `stderrSummary` on the session transcript's `hook/result` event -- a root
# the audited model cannot reach at all; see the --denials reader test
# below for the read side.
@test "a denied guard call writes the JSON record on stderr and the deny JSON on stdout, exit 0" {
  run --separate-stderr hook-guard <<< "$(guard_payload bash '{"command":"sudo id"}')"
  [ "$status" -eq 0 ]
  python3 -c 'import json,sys; o=json.loads(sys.argv[1]); h=o["hookSpecificOutput"]; assert h["hookEventName"]=="PreToolUse", o; assert h["permissionDecision"]=="deny", o; assert h["permissionDecisionReason"], o' "$output"
  run python3 -c 'import json,sys
rec = json.load(sys.stdin)
for k in ("ts", "event", "tool", "reason", "subject"):
    assert k in rec, rec
assert rec["event"] == "PreToolUse", rec
assert rec["tool"] == "bash", rec
assert rec["reason"], rec
assert rec["subject"] == "sudo id", rec
assert len(json.dumps(rec)) < 400, rec' <<< "$stderr"
  [ "$status" -eq 0 ]
}

# Opus gate 2 (round 2 review): the only prior record-length assertion used
# "sudo id", ~120 chars -- far under the point where the truncation loop in
# _denial_record (hook-guard.py) ever has to do anything. A denied edit/write
# under /etc/ with a 600+ char file_path forces both the `reason` and
# `subject` fields over budget at once, so this is the case that actually
# exercises the loop's re-serialize-until-it-fits behaviour (and the one a
# naive `_record_json(...)[:400]` slice of the finished JSON string would
# still pass under -- until this path length breaks it into invalid JSON).
@test "hook-guard truncates a 600+ char /etc/ path denial to one valid JSON line under 400 chars" {
  local long_path="/etc/$(printf 'a%.0s' $(seq 1 610))"
  [ "${#long_path}" -ge 600 ]
  run --separate-stderr hook-guard <<< "$(guard_payload write "{\"file_path\":\"$long_path\"}")"
  [ "$status" -eq 0 ]
  [ "$(printf '%s\n' "$stderr" | wc -l)" -eq 1 ]
  run python3 -c 'import json,sys
rec = json.loads(sys.argv[1])
for k in ("ts", "event", "tool", "reason", "subject"):
    assert k in rec, rec
assert rec["event"] == "PreToolUse", rec
assert rec["tool"] == "write", rec
assert rec["reason"], rec
assert len(json.dumps(rec)) < 400, rec' "$stderr"
  [ "$status" -eq 0 ]
}

# --- RT5: the model rule (hook-guard refuses a sub-agent or nested-seat model
# that is not an OpenRouter row of the routing table) ---
# The wrapper resolves the table once at seat launch and passes it to every
# matcher as --routing-table (the path is ${FACTORY_ROUTING_TABLE:-
# $HOME/nixos-agent-env/docs/ledger/routing.toml}}; driving hook-guard bare
# here, we pass the same path so the tests parse the committed
# docs/ledger/routing.toml (flakes copy it into the unit-check sandbox). The
# rules:
#   * a subagent/subagent_fork/workflow tool_input.model that is not the model
#     of an OpenRouter row (rows without `route`, or route="openrouter") is
#     denied -- the table is applied by the OS, not followed by prose;
#   * a claude row (fable/sonnet/opus) never allows -- unreachable from this
#     seat;
#   * no model in the input -> allow (the seat default applies);
#   * a missing/unparsable table fails CLOSED for an explicit model;
#   * the same check runs over bash commands carrying --model ID or
#     OPENROUTER_MODEL=ID (a nested dsh-openrouter is how a launch would dodge
#     the sub-agent tools).
ROUTING_TABLE="$BATS_TEST_DIRNAME/../../docs/ledger/routing.toml"

# Run hook-guard on $2 with --routing-table $1 and assert a deny whose reason
# contains $3. Mirrors guard_denies_reason but forces the table the wrapper
# would pass -- the model rule must fail closed on a missing table, so the
# bare helper's env-default is never what these tests want to rely on.
guard_denies_table() {
  local table="$1" payload="$2" reason="$3"
  run --separate-stderr hook-guard --routing-table "$table" <<< "$payload"
  [ "$status" -eq 0 ] || return 1
  run python3 -c 'import json,sys; o=json.load(sys.stdin); h=o["hookSpecificOutput"]; assert h["hookEventName"]=="PreToolUse", o; assert h["permissionDecision"]=="deny", o; assert sys.argv[1] in h["permissionDecisionReason"], (h["permissionDecisionReason"], sys.argv[1])' "$reason" <<< "$output"
  [ "$status" -eq 0 ]
}

# Run hook-guard on $2 with --routing-table $1 and assert a deny whose stdout
# reason contains $3 AND whose stderr audit record names $4 as `subject` -- the
# OFFENDING model id, not merely the first id the walk found.
guard_denies_table_subject() {
  local table="$1" payload="$2" reason="$3" subject="$4"
  run --separate-stderr hook-guard --routing-table "$table" <<< "$payload"
  [ "$status" -eq 0 ] || return 1
  local record="$stderr"
  run python3 -c 'import json,sys; o=json.load(sys.stdin); h=o["hookSpecificOutput"]; assert h["hookEventName"]=="PreToolUse", o; assert h["permissionDecision"]=="deny", o; assert sys.argv[1] in h["permissionDecisionReason"], (h["permissionDecisionReason"], sys.argv[1])' "$reason" <<< "$output"
  [ "$status" -eq 0 ] || return 1
  run python3 -c 'import json,sys; rec=json.load(sys.stdin); assert rec["subject"]==sys.argv[1], (rec["subject"], sys.argv[1])' "$subject" <<< "$record"
  [ "$status" -eq 0 ]
}

# Run hook-guard on $2 with --routing-table $1 and assert it emitted nothing.
guard_allows_table() {
  local table="$1" payload="$2"
  run hook-guard --routing-table "$table" <<< "$payload"
  [ "$status" -eq 0 ] || return 1
  [ -z "$output" ]
}

@test "hook-guard denies a subagent model that is not an OpenRouter row of the routing table" {
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload subagent '{"model":"z-ai/glm-5.3","prompt":"feasibility"}')" \
    "z-ai/glm-5.3 is not a row of"
}

@test "hook-guard allows a subagent model that is an OpenRouter row" {
  guard_allows_table "$ROUTING_TABLE" \
    "$(guard_payload subagent '{"model":"deepseek/deepseek-v4-flash","prompt":"x"}')"
}

@test "hook-guard allows a subagent launch with no model (the seat default applies)" {
  guard_allows_table "$ROUTING_TABLE" "$(guard_payload subagent '{"prompt":"x"}')"
}

@test "hook-guard denies a claude row's model (unreachable from this seat)" {
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload subagent '{"model":"opus","prompt":"x"}')" \
    "opus is not a row of"
}

@test "hook-guard fails closed on a missing routing table: an explicit model is denied as unreadable" {
  guard_denies_table "$TMPHOME/does-not-exist.toml" \
    "$(guard_payload subagent '{"model":"z-ai/glm-5.3"}')" \
    "routing table unreadable at"
}

@test "hook-guard denies a subagent_fork and a workflow model not in the table" {
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload subagent_fork '{"model":"moonshotai/kimi-k3"}')" \
    "moonshotai/kimi-k3 is not a row of"
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload workflow '{"model":"z-ai/glm-5.3"}')" \
    "z-ai/glm-5.3 is not a row of"
}

@test "hook-guard denies a bash --model nested-seat launch whose model is not a row" {
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload bash '{"command":"dsh-openrouter --model moonshotai/kimi-k3 --headless x"}')" \
    "moonshotai/kimi-k3 is not a row of"
}

@test "hook-guard allows a bash OPENROUTER_MODEL nested-seat launch whose model is a row" {
  guard_allows_table "$ROUTING_TABLE" \
    "$(guard_payload bash '{"command":"OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 dsh-openrouter --headless x"}')"
}

# --- RT5b (fix round, gate 2026-09-05-opus-review-rt5-RT5) ---
# The bash rule was bypassed by the two most ordinary spellings the shell
# then executes: a quoted id (`--model "z-ai/glm-5.3"`, `--model 'z-ai/glm-5.3'`,
# `OPENROUTER_MODEL="z-ai/glm-5.3"`) and a `\`-newline continuation -- none of
# which the old [A-Za-z0-9._:/-]+ capture could start on, and the old
# `OPENROUTER_MODEL=` allow test was vacuous (a dead rule also allows). The
# structured half also only read a flat top-level `model`, so a workflow's
# `steps[*].model` sailed through. Every deny below is one the cherry-picked
# guard ALLOWED (Step 2 of the run); the equals form, `env ` prefix, tab
# separator and malformed-table denies kill the M5/M10 survivors and pin
# behaviours that were already correct but untested.
#
# `bash_payload` JSON-encodes the command with python3 so a single quote, a
# backslash-newline or a tab needs no hand escaping in the JSON; the command
# string the guard actually scans is exactly the shell's own spelling.

# Build a bash-command PreToolUse payload whose `command` is the argument,
# verbatim (JSON-encoded by python3 so quotes/backslashes/newlines survive).
bash_payload() {
  printf '{"hook_event_name":"PreToolUse","tool_name":"bash","tool_input":%s}' \
    "$(printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps({"command": sys.stdin.read()}))')"
}

@test "hook-guard denies every quoted/continued spelling of a bash --model that is not a row" {
  guard_denies_table "$ROUTING_TABLE" "$(bash_payload 'dsh-openrouter --model "z-ai/glm-5.3" --headless x')" "z-ai/glm-5.3 is not a row of"
  guard_denies_table "$ROUTING_TABLE" "$(bash_payload $'dsh-openrouter --model \'z-ai/glm-5.3\' --headless x')" "z-ai/glm-5.3 is not a row of"
  guard_denies_table "$ROUTING_TABLE" "$(bash_payload 'dsh-openrouter --model=z-ai/glm-5.3 --headless x')" "z-ai/glm-5.3 is not a row of"
  guard_denies_table "$ROUTING_TABLE" "$(bash_payload 'dsh-openrouter --model="z-ai/glm-5.3" --headless x')" "z-ai/glm-5.3 is not a row of"
  guard_denies_table "$ROUTING_TABLE" "$(bash_payload $'dsh-openrouter --model \\\nz-ai/glm-5.3 --headless x')" "z-ai/glm-5.3 is not a row of"
  guard_denies_table "$ROUTING_TABLE" "$(bash_payload $'dsh-openrouter --model\tz-ai/glm-5.3 --headless x')" "z-ai/glm-5.3 is not a row of"
}

@test "hook-guard denies every spelling of a bash OPENROUTER_MODEL that is not a row" {
  guard_denies_table "$ROUTING_TABLE" "$(bash_payload 'OPENROUTER_MODEL="z-ai/glm-5.3" dsh-openrouter --headless x')" "z-ai/glm-5.3 is not a row of"
  guard_denies_table "$ROUTING_TABLE" "$(bash_payload $'OPENROUTER_MODEL=\'z-ai/glm-5.3\' dsh-openrouter --headless x')" "z-ai/glm-5.3 is not a row of"
  guard_denies_table "$ROUTING_TABLE" "$(bash_payload 'env OPENROUTER_MODEL=z-ai/glm-5.3 dsh-openrouter --headless x')" "z-ai/glm-5.3 is not a row of"
}

@test "hook-guard allows a bash --model / OPENROUTER_MODEL that is a row, and a launch naming no model" {
  guard_allows_table "$ROUTING_TABLE" "$(bash_payload 'dsh-openrouter --model deepseek/deepseek-v4-flash --headless x')"
  guard_allows_table "$ROUTING_TABLE" "$(bash_payload 'OPENROUTER_MODEL=deepseek/deepseek-v4-pro-0813 dsh-openrouter --headless x')"
  guard_allows_table "$ROUTING_TABLE" "$(bash_payload 'dsh-openrouter --headless x')"
}

@test "hook-guard denies a provider-present subagent whose model is a claude row (the model alone gates)" {
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload subagent '{"provider":"anthropic","model":"opus","prompt":"x"}')" \
    "opus is not a row of"
}

@test "hook-guard walks nested model keys: a workflow steps[*].model that is not a row is denied" {
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload workflow '{"steps":[{"model":"z-ai/glm-5.3","prompt":"x"}]}')" \
    "z-ai/glm-5.3 is not a row of"
}

@test "hook-guard fails closed on a malformed routing table: an explicit model is denied as unreadable" {
  cat > "$TMPHOME/malformed.toml" <<'TOML'
[[route]
  route = "openrouter"
  model =
TOML
  guard_denies_table "$TMPHOME/malformed.toml" \
    "$(guard_payload subagent '{"model":"z-ai/glm-5.3"}')" \
    "routing table unreadable at"
}

@test "an empty FACTORY_ROUTING_TABLE reaching the guard resolves to the seat default, not an empty path" {
  mkdir -p "$HOME/nixos-agent-env/docs/ledger"
  cp "$ROUTING_TABLE" "$HOME/nixos-agent-env/docs/ledger/routing.toml"
  run env FACTORY_ROUTING_TABLE= hook-guard <<< "$(guard_payload subagent '{"model":"deepseek/deepseek-v4-flash"}')"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

# --- RT5r (re-plan, gate 2026-09-05-opus-review-rt5-RT5): the guard gets an
# error contract ---
# A crash (non-zero exit, empty stdout) is what the harness reads as ALLOW, so
# the model rule now FAILS CLOSED and main() exits 0 on EVERY path: a too-deep
# or too-large tool_input, and a routing table that is unreadable or not valid
# UTF-8, are each a DENY with exit 0, never a crash. The walk is iterative (an
# explicit stack) with a node budget (10,000) and a depth budget (64);
# exceeding either denies "tool_input too deep/large to inspect". Every test
# below asserts `[ "$status" -eq 0 ]` explicitly because a non-zero exit IS the
# bug -- today these payloads crash (exit 1, empty stdout) and are therefore
# allowed.

# Build a subagent tool_input JSON with a top-level non-row `model` and a
# chain `{"a":{"a":...}}` of depth $1 under `deep`. python3 assembles the JSON
# TEXT without recursing -- json.dumps over a 2000-deep object would hit
# Python's own recursion limit long before the guard's walk would.
deep_subagent_payload() {
  local depth="$1"
  python3 -c 'import sys; d=int(sys.argv[1]); print("{\"model\":\"z-ai/glm-5.3\",\"deep\":" + "{\"a\":"*d + "0" + "}"*d + "}")' "$depth"
}

# Build a tool_input JSON with a non-row `model` nested $1 levels deep
# (`{"x":{"x":...{"model":"z-ai/glm-5.3"}...}}`), again without recursing.
deep_nested_model_payload() {
  local depth="$1"
  python3 -c 'import sys; d=int(sys.argv[1]); print("{\"x\":"*d + "{\"model\":\"z-ai/glm-5.3\"}" + "}"*d)' "$depth"
}

@test "hook-guard fails closed (not crashed) on a 2000-deep tool_input: deny 'too deep/large', exit 0" {
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload subagent "$(deep_subagent_payload 2000)")" \
    "tool_input too deep/large to inspect"
}

@test "hook-guard fails closed (not crashed) on a non-UTF-8 routing table: deny 'could not be evaluated', exit 0" {
  printf '\xff\xfe\x00not-toml' > "$TMPHOME/non-utf8.toml"
  guard_denies_table "$TMPHOME/non-utf8.toml" \
    "$(guard_payload subagent '{"model":"z-ai/glm-5.3"}')" \
    "model rule could not be evaluated"
}

@test "hook-guard denies a model nested beyond the depth budget as too deep (not silently missed), exit 0" {
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload workflow "$(deep_nested_model_payload 69)")" \
    "tool_input too deep/large to inspect"
}

@test "hook-guard denies a tool_input with more keys than the node budget as too large, exit 0" {
  local big
  big=$(python3 -c 'print("{" + ",".join("\"k%d\":0" % i for i in range(20000)) + "}")')
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload subagent "$big")" \
    "tool_input too deep/large to inspect"
}

@test "the audit subject names the OFFENDING model id, not the first id found" {
  # RT5rb (gate 2026-09-05-opus-review-rt7-RT5r, MAJOR-2): the top-level model
  # is a routing-table ROW and the offending id is the nested one. The LIFO
  # walk yields the top-level row first, so `model_ids[0]` is "deepseek/...",
  # NOT the offending "z-ai/glm-5.3" -- mutating the subject to model_ids[0]
  # makes this assertion fail. The old payload (steps:[row, non-row]) had the
  # offending id already first under the LIFO walk and so was vacuous.
  guard_denies_table_subject "$ROUTING_TABLE" \
    "$(guard_payload workflow '{"model":"deepseek/deepseek-v4-flash","steps":[{"model":"z-ai/glm-5.3"}]}')" \
    "z-ai/glm-5.3 is not a row of" \
    "z-ai/glm-5.3"
}

@test "the walk yields the top-level row before the nested offending id (walk-order helper)" {
  # An unreadable table makes _model_verdict return model_ids[0] as the audit
  # subject, so asserting subject == the ROW proves the walk yields the row
  # FIRST -- which is what makes the test above discriminating against a
  # `subject = model_ids[0]` reversion.
  guard_denies_table_subject "$TMPHOME/does-not-exist.toml" \
    "$(guard_payload workflow '{"model":"deepseek/deepseek-v4-flash","steps":[{"model":"z-ai/glm-5.3"}]}')" \
    "routing table unreadable at" \
    "deepseek/deepseek-v4-flash"
}

@test "a bash --model nested-seat launch also fails closed on a non-UTF-8 routing table, exit 0" {
  printf '\xff\xfe\x00not-toml' > "$TMPHOME/non-utf8-bash.toml"
  guard_denies_table "$TMPHOME/non-utf8-bash.toml" \
    "$(bash_payload 'dsh-openrouter --model z-ai/glm-5.3 --headless x')" \
    "model rule could not be evaluated"
}

# --- RT5rb (fix round, gate 2026-09-05-opus-review-rt7-RT5r): the parse is
# fail-closed, the depth budget is exact, and a non-object tool_input on a
# sub-agent tool denies ---
# The parse now sits inside the guard (contract item 1): stdin is read with a
# 4 MiB bound, its bracket nesting is pre-scanned so the JSON decoder is never
# fed hostile depth, and json.loads runs inside main()'s BaseException region.
# A read over the bound, nesting beyond the parse guard, or any parse failure
# (RecursionError / MemoryError / ValueError, or a top level that is not an
# object) is a DENY with reason "payload could not be parsed: <too large|too
# deep|ExceptionName>", exit 0 -- never a crash, because a non-zero exit with
# empty stdout is what the harness reads as ALLOW. The tool name is unknown at
# parse time, so the denial applies to every tool (an accepted over-denial the
# runbook states). Every test below asserts `[ "$status" -eq 0 ]` explicitly.

@test "hook-guard refuses a 100000-deep payload as unparsable: deny 'too deep', exit 0" {
  guard_denies_reason "$(guard_payload subagent "$(deep_subagent_payload 100000)")" \
    "payload could not be parsed: too deep"
}

@test "hook-guard refuses a >4 MiB stdin as too large, exit 0" {
  python3 -c 'import sys; sys.stdout.write("a" * (5 * 1024 * 1024))' > "$TMPHOME/too-big.json"
  run --separate-stderr hook-guard < "$TMPHOME/too-big.json"
  [ "$status" -eq 0 ]
  run python3 -c 'import json,sys; o=json.load(sys.stdin); h=o["hookSpecificOutput"]; assert h["permissionDecision"]=="deny", o; assert h["permissionDecisionReason"]=="payload could not be parsed: too large", h["permissionDecisionReason"]' <<< "$output"
  [ "$status" -eq 0 ]
}

@test "hook-guard denies a top-level JSON array (not an object), exit 0" {
  guard_denies_reason '[{"model":"z-ai/glm-5.3"}]' "payload could not be parsed"
}

@test "a sub-agent tool whose tool_input is not an object is denied; bash keeps the coercion" {
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload workflow 'null')" \
    "model rule could not be evaluated: tool_input is not an object"
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload subagent '[]')" \
    "model rule could not be evaluated: tool_input is not an object"
  guard_allows_table "$ROUTING_TABLE" "$(guard_payload bash 'null')"
}

@test "a non-row model at depth exactly 64 is reached by the model rule; depth 65 is the budget overrun" {
  guard_denies_table_subject "$ROUTING_TABLE" \
    "$(guard_payload workflow "$(deep_nested_model_payload 64)")" \
    "z-ai/glm-5.3 is not a row of" \
    "z-ai/glm-5.3"
  guard_denies_table "$ROUTING_TABLE" \
    "$(guard_payload workflow "$(deep_nested_model_payload 65)")" \
    "tool_input too deep/large to inspect"
}

@test "--dump-config mounts the hooks bridge and hooks.json has bash, edit|write and sub-agent matchers passing one routing table" {
  make_key
  dsh_home="$XDG_DATA_HOME/dsh-openrouter"
  # the path the wrapper resolves at seat launch and passes to every matcher
  # (RT5); mirror its resolution so the assertion names the exact arg.
  routing_table=${FACTORY_ROUTING_TABLE:-$HOME/nixos-agent-env/docs/ledger/routing.toml}
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" == *"@deepseek-ai/dsh-hooks-claude-code"* ]]
  # dsh's YAML emitter folds a long scalar into a block (`configPath: >-`
  # then the value on the next, more-indented line), so the old one-line
  # substring match broke under the devShell's long TMPDIR. Assert on the
  # parsed value instead: handle both the inline `key: value` form and the
  # folded block. python3's stdlib has no YAML module, so this is a focused
  # extractor for the two forms dsh emits here -- it reads the dump once for
  # the single configPath key and compares the scalar to the path the wrapper
  # wrote.
  printf '%s' "$output" > "$TMPHOME/dump-config.yml"
  run python3 - "$TMPHOME/dump-config.yml" "$dsh_home/hooks.json" <<'PY'
import sys

lines = open(sys.argv[1]).read().splitlines()
expected = sys.argv[2]
value = None
for i, line in enumerate(lines):
    if line.lstrip().startswith('configPath:'):
        rest = line.split(':', 1)[1].strip()
        if rest[:1] in ('>', '|'):
            # blocked scalar: the value is on the following, more-indented lines
            indent = len(line) - len(line.lstrip())
            parts = []
            for cont in lines[i + 1:]:
                if not cont.strip():
                    continue
                if len(cont) - len(cont.lstrip()) > indent:
                    parts.append(cont.strip())
                else:
                    break
            value = ' '.join(parts)
        else:
            value = rest
        break
assert value is not None, 'configPath not found in --dump-config output'
assert value == expected, (value, expected)
PY
  [ "$status" -eq 0 ]
  [ -f "$dsh_home/hooks.json" ]
  [ "$(stat -c %a "$dsh_home/hooks.json")" = "600" ]
  run python3 - "$dsh_home/hooks.json" "$routing_table" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
groups = cfg["hooks"]["PreToolUse"]
assert sorted(g.get("matcher", "") for g in groups) == [
    "bash",
    "edit|write",
    "subagent|subagent_fork|workflow",
], groups
for g in groups:
    assert g["hooks"], g
    for h in g["hooks"]:
        assert h["type"] == "command", h
        assert h["command"], h
        # every matcher hands the guard the one resolved table (RT5), so the
        # bash, edit|write and sub-agent matchers all see one table.
        assert f" --routing-table '{sys.argv[2]}'" in h["command"], h["command"]
PY
  [ "$status" -eq 0 ]
}

# Round 2 (review 2026-09-04) replaces the old "hooks.json's denial log
# lives under the workspace" test: the workspace log file is gone, so
# hooks.json's hook commands must name no log path at all -- just the
# guard, invoked plain. SD8 additionally pins the house-guard wiring: every
# matcher's command hands the guard --house-guard (the orchestrator guard,
# a store path) and --house-shell $BASH (the wrapper's own interpreter), so
# the seat unit's PATH (no bash) is never relied on.
@test "hooks.json's hook commands carry no denial log path -- just the guard, its routing table and the house guard" {
  make_key
  dsh_home="$XDG_DATA_HOME/dsh-openrouter"
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [ -f "$dsh_home/hooks.json" ]
  run grep -c "DSH_HOOK_DENIAL_LOG" "$dsh_home/hooks.json"
  [ "$output" = "0" ]
  run python3 - "$dsh_home/hooks.json" <<'PY'
import json, re, sys
cfg = json.load(open(sys.argv[1]))
groups = cfg["hooks"]["PreToolUse"]
assert len(groups) == 3, groups
for g in groups:
    for h in g["hooks"]:
        # `exec '<guard>' --routing-table '<table>' --house-guard '<path>'
        # --house-shell '<shell>'`: the guard invoked plain, plus the one
        # resolved table and the house guard (RT5/SD8) -- and no log path.
        assert re.fullmatch(
            r"exec '[^']+' --routing-table '[^']+' --house-guard '[^']+' --house-shell '[^']+'",
            h["command"],
        ), h["command"]
PY
  [ "$status" -eq 0 ]
}

# RT5rb (contract item 5): the wrapper JSON-escapes the routing-table path into
# hooks.json (jq --arg, never string interpolation), so an operator-set path
# containing a `"` and a space round-trips: hooks.json stays valid JSON and the
# command, shell-parsed, hands hook-guard the path intact.
@test "hooks.json JSON-escapes the routing-table path: a quote and a space round-trip" {
  make_key
  dsh_home="$XDG_DATA_HOME/dsh-openrouter"
  table='/tmp/a "b"/routing.toml'
  FACTORY_ROUTING_TABLE="$table" OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [ -f "$dsh_home/hooks.json" ]
  run python3 - "$dsh_home/hooks.json" "$table" <<'PY'
import json, shlex, sys
cfg = json.load(open(sys.argv[1]))
path = sys.argv[2]
groups = cfg["hooks"]["PreToolUse"]
assert len(groups) == 3, groups
for g in groups:
    for h in g["hooks"]:
        argv = shlex.split(h["command"])
        assert "exec" == argv[0], argv
        i = argv.index("--routing-table")
        assert argv[i + 1] == path, (argv[i + 1], path)
PY
  [ "$status" -eq 0 ]
}

# --- N7 round 2: dsh-denials, the reader for hook-guard's stderr records ---
# hook-guard's denial record never touches disk on its own; dsh's hook
# bridge is what durably captures it, into the denying call's `hook/result`
# event as `stderrSummary`, inside the session transcript
# ($DSH_HOME/sessions/<cwd-key>/<session-id>/session.jsonl.zstd). dsh-denials
# reads that back. Driven here against a small fixture transcript
# (tests/fixtures/dsh-sessions/slug-fixture/session-.../session.jsonl.zstd)
# rather than a live harness session -- committed once, so the test never
# depends on the pinned dsh actually producing one.
@test "dsh-denials lists a fixture transcript's denial: timestamp, stderr record, denied command" {
  denials_home="$TMPHOME/denials-home"
  mkdir -p "$denials_home/sessions"
  cp -r "$BATS_TEST_DIRNAME/../fixtures/dsh-sessions/slug-fixture" "$denials_home/sessions/"
  DSH_HOME="$denials_home" run dsh-denials
  [ "$status" -eq 0 ]
  [[ "$output" == *"1788560000.140"* ]]
  [[ "$output" == *'"tool":"bash"'* ]]
  [[ "$output" == *'"reason":"sudo is refused (an operator action)"'* ]]
  [[ "$output" == *'"subject":"sudo rm -rf /"'* ]]
  [[ "$output" == *"<- sudo rm -rf /"* ]]
}

@test "dsh-denials --denials via the wrapper reads the same fixture, and an empty \$DSH_HOME says so on stderr" {
  denials_home="$TMPHOME/denials-home2"
  mkdir -p "$denials_home/sessions"
  cp -r "$BATS_TEST_DIRNAME/../fixtures/dsh-sessions/slug-fixture" "$denials_home/sessions/"
  DSH_HOME="$denials_home" run dsh-openrouter --denials
  [ "$status" -eq 0 ]
  [[ "$output" == *"<- sudo rm -rf /"* ]]

  empty_home="$TMPHOME/denials-empty"
  DSH_HOME="$empty_home" run --separate-stderr dsh-openrouter --denials
  [ "$status" -eq 0 ]
  [ -z "$output" ]
  [[ "$stderr" == *"no denial records found"* ]]
}

# Opus gate 2 (round 2 review, "notes, not blockers"): dsh-denials.py:123
# silently swallows every unreadable/corrupt transcript, so a corrupt tree
# prints the same "no denial records found" as a genuinely clean one -- an
# audit reader must never look clean because it failed to read something.
# Each skipped transcript now gets one warning line on stderr.
@test "dsh-denials warns per skipped (corrupt) transcript on stderr and still exits 0" {
  denials_home="$TMPHOME/denials-home3"
  corrupt="$denials_home/sessions/corrupt-session/session.jsonl.zstd"
  mkdir -p "$(dirname "$corrupt")"
  printf 'not a valid zstd frame' > "$corrupt"
  DSH_HOME="$denials_home" run --separate-stderr dsh-denials
  [ "$status" -eq 0 ]
  [[ "$stderr" == *"warning: skipped $corrupt:"* ]]
}

# P3 (2026-09-05): N21 covered only the env var over a saved reasoning effort.
# The same "env beats saved" rule has to cover the model: an explicit
# --model / OPENROUTER_MODEL rewrites the saved agent-default-model.model in
# settings.yaml before dsh boots, because dsh's *agent selection* (the saved
# model) beats the route's `model:`, and a saved Pro selection against a
# route listing only the requested model dies UNKNOWN_MODEL. The seed here
# uses the home write_settings targets ($XDG_DATA_HOME/dsh-openrouter, the
# wrapper's default DSH_HOME) so there is one settings.yaml, not two.
@test "an explicit OPENROUTER_MODEL overrides a saved model selection instead of dying UNKNOWN_MODEL" {
  make_key
  dsh_home="$XDG_DATA_HOME/dsh-openrouter"
  mkdir -p "$dsh_home"
  printf 'ui-onboarding:\n  welcomeNoticeVersion: 2026-08-13.1\nagent-default-model:\n  provider: openrouter\n  model: deepseek/deepseek-v4-pro-0813\n  reasoningEffort: medium\n' >"$dsh_home/settings.yaml"
  chmod 600 "$dsh_home/settings.yaml"
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" OPENROUTER_MODEL=fake/model \
    run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  [[ "$output" != *"UNKNOWN_MODEL"* ]]
  run grep -c 'model: fake/model' "$dsh_home/settings.yaml"
  [ "$output" = "1" ]
  run grep -c 'deepseek-v4-pro' "$dsh_home/settings.yaml"
  [ "$output" = "0" ]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat and all(r["body"]["model"] == "fake/model" for r in chat), [r["body"].get("model") for r in chat]
PY
}

@test "without an explicit model the saved model selection is left intact" {
  make_key
  mkdir -p "$XDG_DATA_HOME/dsh-openrouter"
  printf 'ui-onboarding:\n  welcomeNoticeVersion: 2026-08-13.1\nagent-default-model:\n  provider: openrouter\n  model: z-ai/glm-5.3\n  reasoningEffort: high\n' >"$XDG_DATA_HOME/dsh-openrouter/settings.yaml"
  chmod 600 "$XDG_DATA_HOME/dsh-openrouter/settings.yaml"
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  [ "$(grep -c 'model: z-ai/glm-5.3' "$XDG_DATA_HOME/dsh-openrouter/settings.yaml")" -eq 1 ]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat and all(r["body"]["model"] == "z-ai/glm-5.3" for r in chat), [r["body"].get("model") for r in chat]
PY
}

@test "an explicit --model overrides a saved model selection" {
  make_key
  write_settings medium
  start_fake '[{"content": "FAKE-OK"}]'
  OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --model fake/model --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" != *"UNKNOWN_MODEL"* ]]
  [ "$(grep -c 'model: fake/model' "$XDG_DATA_HOME/dsh-openrouter/settings.yaml")" -eq 1 ]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat and all(r["body"]["model"] == "fake/model" for r in chat), [r["body"].get("model") for r in chat]
PY
}

# --- SB2: the wrapper's --broker mode (no key, proxy + CA from the unit,
# the gateway route check, namespace bind for the UI) ---
# The wrapper's runtimeInputs carry no `ip`, so a fake `ip` on the test's
# PATH is the one the wrapper runs. It answers `ip -4 route show default`
# with exactly one default route via the chosen gateway -- the broker's
# hostAddress in the real unit (10.100.4.1) -- and fails any other invocation.
make_ip() {
  local gateway="$1"
  mkdir -p "$TMPHOME/bin"
  cat > "$TMPHOME/bin/ip" <<SH
#!/bin/sh
if [ "\$1" != "-4" ] || [ "\$2" != "route" ] || [ "\$3" != "show" ] || [ "\$4" != "default" ]; then
  exit 1
fi
echo "default via $gateway dev veth0 proto static"
exit 0
SH
  chmod +x "$TMPHOME/bin/ip"
}

# A CA bundle the wrapper's NODE_EXTRA_CA_CERTS check can see as an existing
# file; the broker's public bundle in the real unit.
make_ca() {
  mkdir -p "$TMPHOME"
  printf '%s\n' '-----BEGIN CERTIFICATE-----' > "$TMPHOME/ca.crt"
}

@test "--broker skips the key block: a mode-000 key file launches headless and sends the placeholder credential" {
  make_key
  # Mode 000: any stat or read of the key file by the wrapper would fail.
  # --broker must never touch it, so the launch succeeds and the request
  # carries the placeholder, proving the real key was never read.
  chmod 000 "$XDG_CONFIG_HOME/openrouter/key"
  make_ip 10.100.4.1
  make_ca
  start_fake '[{"content": "BROKER-OK"}]'
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --broker --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"BROKER-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
assert chat[0]["headers"].get("authorization") == "Bearer injected-by-broker", chat[0]["headers"]
PY
}

@test "--broker without HTTPS_PROXY exits 5" {
  make_key
  make_ip 10.100.4.1
  make_ca
  PATH="$TMPHOME/bin:$PATH" \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"HTTPS_PROXY"* ]]
}

@test "--broker with a default route via another gateway exits 5" {
  make_key
  make_ip 10.100.4.99
  make_ca
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"--broker outside a broker namespace"* ]]
}

# SB4b: dsh's web server is deliberately loopback-only (the pinned harness
# refuses --host 10.100.4.2 and --host 0.0.0.0 alike). --bind-namespace no
# longer reaches dsh's --host: dsh is always started with --host 127.0.0.1,
# and under --bind-namespace the wrapper spawns a unit-owned socat forwarder
# that carries the namespace address to dsh's loopback on the same port.
@test "--bind-namespace with --broker passes --host 127.0.0.1 and spawns socat with bind, port and target" {
  make_key
  make_ip 10.100.4.1
  make_ca
  make_fake_node
  make_fake_socat
  start_fake '[{"content": "BROKER-OK"}]'
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    DSH_OPENROUTER_NODE="$TMPHOME/bin/fake-node" \
    DSH_OPENROUTER_TEST_SEAM=1 \
    OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --broker --bind-namespace 10.100.4.2 -- --no-open --port 43210
  # The fake node records the real argv the wrapper exec'd (one token per
  # line) plus the OPENROUTER_BASE_URL it inherited, then exits 0 -- so the
  # test pins the actual exec line and exit status without booting the real
  # harness or scraping `bash -x`. dsh must always reach --host 127.0.0.1
  # (never the namespace address: dsh's own loopback guard refuses it).
  [ "$status" -eq 0 ]
  argv_flat=$(tr '\n' ' ' < "$TMPHOME/node-argv.txt")
  [[ "$argv_flat" == *"--host 127.0.0.1"* ]]
  [[ "$argv_flat" != *"--host 10.100.4.2"* ]]
  [ "$(cat "$TMPHOME/node-baseurl.txt")" = "http://127.0.0.1:$FAKE_PORT/api/v1" ]
  # The fake socat recorded the exact forwarder argv: listen on the namespace
  # address at the requested port (forked, reusing the address), relaying to
  # dsh's loopback on the SAME port.
  socat_flat=$(tr '\n' ' ' < "$TMPHOME/socat-argv.txt")
  [[ "$socat_flat" == *"TCP-LISTEN:43210,bind=10.100.4.2,fork,reuseaddr"* ]]
  [[ "$socat_flat" == *"TCP:127.0.0.1:43210"* ]]
}

@test "--broker without --bind-namespace spawns no socat (dsh still binds 127.0.0.1)" {
  make_key
  make_ip 10.100.4.1
  make_ca
  make_fake_node
  make_fake_socat
  start_fake '[{"content": "BROKER-OK"}]'
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    DSH_OPENROUTER_NODE="$TMPHOME/bin/fake-node" \
    DSH_OPENROUTER_TEST_SEAM=1 \
    OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --broker -- --no-open --port 43211
  [ "$status" -eq 0 ]
  # No --bind-namespace: no forwarder, and the fake socat never ran.
  [ ! -e "$TMPHOME/socat-argv.txt" ]
  argv_flat=$(tr '\n' ' ' < "$TMPHOME/node-argv.txt")
  [[ "$argv_flat" == *"--host 127.0.0.1"* ]]
}

@test "--bind-namespace without --broker is rejected like --host" {
  make_key
  run dsh-openrouter --bind-namespace 10.100.4.2 --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"127.0.0.1 only"* ]]
}

@test "the key-file path prints a deprecation line on stderr" {
  make_key
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run --separate-stderr dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$stderr" == *"the key file is deprecated"* ]]
  [[ "$stderr" == *"docs/runbooks/seat.md"* ]]
  [[ "$output" != *"deprecated"* ]]
}

# A fake `ip` whose `ip -4 route show default` prints the literal text given
# (for the synthetic-route hardening test: a line with two `via` tokens, which
# a substring match would wrongly accept).
make_ip_line() {
  printf '%s\n' "$1" > "$TMPHOME/ip-default.txt"
  mkdir -p "$TMPHOME/bin"
  cat > "$TMPHOME/bin/ip" <<SH
#!/bin/sh
if [ "\$1" != "-4" ] || [ "\$2" != "route" ] || [ "\$3" != "show" ] || [ "\$4" != "default" ]; then
  exit 1
fi
cat "$TMPHOME/ip-default.txt"
exit 0
SH
  chmod +x "$TMPHOME/bin/ip"
}

# A fake `node` that records the argv the wrapper execs (one token per line)
# and the OPENROUTER_BASE_URL it inherited, then exits 0. The web bind test
# names it via DSH_OPENROUTER_NODE (a test-only seam, honoured only with
# DSH_OPENROUTER_TEST_SEAM=1) so the real exec argv and exit status are
# pinned without booting the harness or scraping `bash -x`.
make_fake_node() {
  mkdir -p "$TMPHOME/bin"
  cat > "$TMPHOME/bin/fake-node" <<SH
#!/bin/sh
printf '%s\n' "\$@" > "$TMPHOME/node-argv.txt"
printf '%s\n' "\${OPENROUTER_BASE_URL-}" > "$TMPHOME/node-baseurl.txt"
exit 0
SH
  chmod +x "$TMPHOME/bin/fake-node"
}

# A fake `socat` that records the argv the wrapper passed it (one token per
# line) and exits 0. The wrapper spawns socat in the background before
# exec'ing dsh, so a fake that records and exits is enough to pin the
# forwarder's argv (bind address, port, target) without a real relay.
make_fake_socat() {
  mkdir -p "$TMPHOME/bin"
  cat > "$TMPHOME/bin/socat" <<SH
#!/bin/sh
printf '%s\n' "\$@" > "$TMPHOME/socat-argv.txt"
exit 0
SH
  chmod +x "$TMPHOME/bin/socat"
}

@test "--broker without NODE_EXTRA_CA_CERTS exits 5" {
  make_key
  make_ip 10.100.4.1
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=http://10.100.4.1:3141 \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"NODE_EXTRA_CA_CERTS"* ]]
}

@test "--broker with a missing NODE_EXTRA_CA_CERTS file exits 5" {
  make_key
  make_ip 10.100.4.1
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/nope.crt" \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"is not an existing file"* ]]
}

@test "--broker with a NODE_EXTRA_CA_CERTS that is a directory exits 5" {
  make_key
  make_ip 10.100.4.1
  mkdir -p "$TMPHOME/ca-dir"
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca-dir" \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"is not an existing file"* ]]
}

@test "--broker replaces a pre-set OPENROUTER_API_KEY with the placeholder and says so" {
  make_key
  make_ip 10.100.4.1
  make_ca
  start_fake '[{"content": "BROKER-OK"}]'
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    OPENROUTER_API_KEY=sk-or-fixture \
    OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run --separate-stderr dsh-openrouter --broker --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"BROKER-OK"* ]]
  # A pre-set key is ignored: the stderr says so, the launch banner names the
  # placeholder (never the real key), and the placeholder is what the fake
  # upstream received.
  [[ "$stderr" == *"ignored"* ]]
  [[ "$stderr" == *"placeholder (broker injects)"* ]]
  [[ "$stderr" != *"sk-or-fixture"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
assert chat[0]["headers"].get("authorization") == "Bearer injected-by-broker", chat[0]["headers"]
PY
}

@test "--bind-namespace 0.0.0.0 is rejected" {
  run dsh-openrouter --broker --bind-namespace 0.0.0.0 --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace"* ]]
}

@test "--bind-namespace --profile (a flag-shaped value) is rejected" {
  run dsh-openrouter --broker --bind-namespace --profile --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace"* ]]
}

@test "--bind-namespace 127.0.0.1 (loopback) is rejected" {
  run dsh-openrouter --broker --bind-namespace 127.0.0.1 --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace"* ]]
}

@test "--bind-namespace 10.100.4.2 with --broker is accepted" {
  make_key
  make_ip 10.100.4.1
  make_ca
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    run dsh-openrouter --broker --bind-namespace 10.100.4.2 --dump-config -- --port 43210
  [ "$status" -eq 0 ]
}

# SB6b: --port is validated wherever it is given (any mode, not only under
# --bind-namespace), and --bind-namespace now REQUIRES a --port (the forwarder
# would otherwise build TCP-LISTEN:,bind=... -- a port-less listen).
@test "SB6b: --bind-namespace without --port dies 2 before socat" {
  make_key
  make_ip 10.100.4.1
  make_ca
  make_fake_node
  make_fake_socat
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    DSH_OPENROUTER_NODE="$TMPHOME/bin/fake-node" \
    DSH_OPENROUTER_TEST_SEAM=1 \
    run dsh-openrouter --broker --bind-namespace 10.100.4.2 -- --no-open
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace needs --port"* ]]
  [ ! -e "$TMPHOME/socat-argv.txt" ]
  [ ! -e "$TMPHOME/node-argv.txt" ]
}

@test "SB6b: --port '43210,su=nobody' dies 2 before socat" {
  make_key
  make_ip 10.100.4.1
  make_ca
  make_fake_node
  make_fake_socat
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    DSH_OPENROUTER_NODE="$TMPHOME/bin/fake-node" \
    DSH_OPENROUTER_TEST_SEAM=1 \
    run dsh-openrouter --broker --bind-namespace 10.100.4.2 -- --no-open --port '43210,su=nobody'
  [ "$status" -eq 2 ]
  [[ "$output" == *"--port must be an integer 1024-65535"* ]]
  [ ! -e "$TMPHOME/socat-argv.txt" ]
  [ ! -e "$TMPHOME/node-argv.txt" ]
}

@test "SB6b: --port=70000 dies 2 in plain web mode" {
  make_key
  make_fake_node
  DSH_OPENROUTER_NODE="$TMPHOME/bin/fake-node" \
    DSH_OPENROUTER_TEST_SEAM=1 \
    run dsh-openrouter -- --no-open --port=70000
  [ "$status" -eq 2 ]
  [[ "$output" == *"--port must be an integer 1024-65535"* ]]
  [ ! -e "$TMPHOME/node-argv.txt" ]
}

@test "SB6b: --port=80 dies 2 (below 1024)" {
  make_key
  make_fake_node
  DSH_OPENROUTER_NODE="$TMPHOME/bin/fake-node" \
    DSH_OPENROUTER_TEST_SEAM=1 \
    run dsh-openrouter -- --no-open --port=80
  [ "$status" -eq 2 ]
  [[ "$output" == *"--port must be an integer 1024-65535"* ]]
  [ ! -e "$TMPHOME/node-argv.txt" ]
}

@test "SB6b: the harness package exports one socat binary and none of its siblings" {
  bindir=$(dirname "$(command -v dsh-openrouter)")
  [ -e "$bindir/socat" ]
  [ ! -e "$bindir/socat1" ]
  [ ! -e "$bindir/filan" ]
  [ ! -e "$bindir/procan" ]
  [ ! -e "$bindir/socat-broker.sh" ]
  [ ! -e "$bindir/socat-chain.sh" ]
  [ ! -e "$bindir/socat-mux.sh" ]
}

@test "--broker reads the gateway as the token after via, never a substring" {
  make_key
  make_ip_line 'default via 192.168.1.1 dev via 10.100.4.1 x'
  make_ca
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"--broker outside a broker namespace"* ]]
}

@test "--broker with HTTPS_PROXY=https://... exits 5 on the http:// form" {
  make_key
  make_ip 10.100.4.1
  make_ca
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=https://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"must be http://<host>:<port>"* ]]
}

@test "--broker with HTTPS_PROXY=socks5://... exits 5 on the http:// form" {
  make_key
  make_ip 10.100.4.1
  make_ca
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=socks5://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"must be http://<host>:<port>"* ]]
}

# --- SB2r: the corrections the SB2b gate rejected ---
# (1) the bind address must be a real IPv4 (octets each 0-255, no leading
# zeros), never empty; (2) exactly one default route is pinned; (3) the
# ignored-key line fires only when the pre-set key differs from the
# placeholder; (4) the launch banner prints the contracted credential string;
# (5) the interpreter seam is honoured only with the test flag.

@test "--bind-namespace 256.1.1.1 (an out-of-range octet) is rejected" {
  run dsh-openrouter --broker --bind-namespace 256.1.1.1 --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace"* ]]
}

@test "--bind-namespace 999.999.999.999 (all octets out of range) is rejected" {
  run dsh-openrouter --broker --bind-namespace 999.999.999.999 --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace"* ]]
}

@test "--bind-namespace 300.300.300.300 (all octets out of range) is rejected" {
  run dsh-openrouter --broker --bind-namespace 300.300.300.300 --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace"* ]]
}

@test "--bind-namespace 01.2.3.4 (a leading zero) is rejected" {
  run dsh-openrouter --broker --bind-namespace 01.2.3.4 --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace"* ]]
}

@test "--bind-namespace '' (an empty value) is rejected" {
  run dsh-openrouter --broker --bind-namespace '' --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace"* ]]
}

@test "--broker with two default routes (one via the proxy host) exits 5" {
  make_key
  make_ip_line 'default via 10.100.4.99 dev veth9
default via 10.100.4.1 dev veth0'
  make_ca
  PATH="$TMPHOME/bin:$PATH" HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    run dsh-openrouter --broker --dump-config
  [ "$status" -eq 5 ]
  [[ "$output" == *"--broker outside a broker namespace"* ]]
}

@test "--broker with a pre-set placeholder OPENROUTER_API_KEY stays silent (no ignored-key line)" {
  make_key
  make_ip 10.100.4.1
  make_ca
  start_fake '[{"content": "BROKER-OK"}]'
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    OPENROUTER_API_KEY=injected-by-broker \
    OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run --separate-stderr dsh-openrouter --broker --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"BROKER-OK"* ]]
  # The placeholder is exactly what the unit sets, so nothing was carried in
  # and the "ignored" line must not fire.
  [[ "$stderr" != *"ignored"* ]]
}

@test "--broker launch banner prints 'credential: placeholder (broker injects)'" {
  make_key
  make_ip 10.100.4.1
  make_ca
  start_fake '[{"content": "BROKER-OK"}]'
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run --separate-stderr dsh-openrouter --broker --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$stderr" == *"credential: placeholder (broker injects)"* ]]
  [[ "$stderr" != *"key from placeholder"* ]]
}

@test "DSH_OPENROUTER_NODE without DSH_OPENROUTER_TEST_SEAM is ignored: the real interpreter runs" {
  make_key
  make_ip 10.100.4.1
  make_ca
  make_fake_node
  PATH="$TMPHOME/bin:$PATH" \
    HTTPS_PROXY=http://10.100.4.1:3141 \
    NODE_EXTRA_CA_CERTS="$TMPHOME/ca.crt" \
    DSH_OPENROUTER_NODE="$TMPHOME/bin/fake-node" \
    run --separate-stderr dsh-openrouter --broker --dump-config
  [ "$status" -eq 0 ]
  # The fake never ran (it would have written node-argv.txt); the real node
  # produced a real dump, and the wrapper said it ignored the seam.
  [ ! -e "$TMPHOME/node-argv.txt" ]
  [[ "$output" == *"apiKeyEnv: OPENROUTER_API_KEY"* ]]
  [[ "$stderr" == *"DSH_OPENROUTER_NODE"* ]]
}
