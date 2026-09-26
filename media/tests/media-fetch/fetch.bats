#!/usr/bin/env bats
# End-to-end test of media-fetch-models against a local HTTP mock: a real
# download over loopback HTTP (no proxy/TLS — that plumbing is the
# module's job, exercised by checks.comfyui-eval instead), a correct-hash
# entry that must succeed and a wrong-hash entry that must fail, without
# stopping the run.

setup() {
  cd "$BATS_TEST_TMPDIR"
  mkdir -p srv out
  printf 'abc' >srv/a.bin
  PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')
  export PORT
  SERVE_DIR="$BATS_TEST_DIRNAME/../mocks/serve-dir.py"
  python3 "$SERVE_DIR" "$PORT" srv &
  SERVER_PID=$!
  # Wait for the mock to accept connections before the test proceeds
  # (bash's /dev/tcp avoids a curl dependency in the check sandbox; fd 6,
  # not 3, because bats-exec-test reserves fd 3 for its own bookkeeping).
  for _ in $(seq 1 50); do
    if (exec 6<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
      exec 6<&- 6>&-
      break
    fi
    sleep 0.1
  done

  GOOD_SHA=$(printf 'abc' | sha256sum | cut -d' ' -f1)

  cat >manifest.toml <<EOF
[[model]]
name = "a"
url = "http://127.0.0.1:$PORT/a.bin"
sha256 = "$GOOD_SHA"
dest = "ckpt/a.bin"
size = 3
license = "MIT"
gated = false
enabled = true

[[model]]
name = "b"
url = "http://127.0.0.1:$PORT/a.bin"
sha256 = "$(printf '%064d' 0)"
dest = "ckpt/b.bin"
size = 3
license = "MIT"
gated = false
enabled = true
EOF
}

teardown() {
  kill "$SERVER_PID" 2>/dev/null || true
  wait "$SERVER_PID" 2>/dev/null || true
}

@test "fetches the good entry, fails the wrong-hash entry, exits non-zero" {
  run media-fetch-models --manifest manifest.toml --dest out
  [ "$status" -eq 1 ]
  [[ "$output" == *"media-fetch: OK a "* ]]
  [[ "$output" == *"media-fetch: FAIL b "* ]]
  [ -f out/ckpt/a.bin ]
  [ ! -f out/ckpt/b.bin ]
  run bash -c 'find out -name "*.part"'
  [ -z "$output" ]
}
