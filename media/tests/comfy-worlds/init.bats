#!/usr/bin/env bats
# comfy-worlds-init builds the two-world tree (spec §1), is idempotent, and
# adopts an existing single-directory ComfyUI tree only when told to.

setup() {
  INIT="$BATS_TEST_DIRNAME/../../pkgs/comfy-worlds/init.sh"
  ROOT="$BATS_TEST_TMPDIR/comfyui"
  export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@x GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@x
}

@test "creates store, both worlds, labs as git repos, user symlink into the lab" {
  run bash "$INIT" --root "$ROOT"
  [ "$status" -eq 0 ]
  for w in sfw nsfw; do
    for d in custom_nodes input output temp models; do [ -d "$ROOT/worlds/$w/$d" ]; done
    [ -d "$ROOT/worlds/$w/lab/.git" ]
    [ -d "$ROOT/worlds/$w/lab/prompts" ]
    [ -f "$ROOT/worlds/$w/lab/manifest.toml" ]
    [ -f "$ROOT/worlds/$w/lab/README.md" ]
    grep -q "^# models of world $w$" "$ROOT/worlds/$w/lab/manifest.toml"
    [ -L "$ROOT/worlds/$w/user" ]
    [ "$(readlink "$ROOT/worlds/$w/user")" = "lab/user" ]
  done
  [ -d "$ROOT/store" ]
}

@test "is idempotent: a second run changes nothing" {
  bash "$INIT" --root "$ROOT"
  before=$(find "$ROOT" -mindepth 1 | sort | md5sum)
  run bash "$INIT" --root "$ROOT"
  [ "$status" -eq 0 ]
  [ "$(find "$ROOT" -mindepth 1 | sort | md5sum)" = "$before" ]
}

@test "refuses to touch existing content without --adopt" {
  mkdir -p "$ROOT/output" "$ROOT/models/checkpoints"
  echo img >"$ROOT/output/a.png"
  run bash "$INIT" --root "$ROOT"
  [ "$status" -ne 0 ]
  [[ "$output" == *"pass --adopt <world> to move it"* ]]
  [ -f "$ROOT/output/a.png" ]
  [ ! -e "$ROOT/worlds" ]
  [ ! -e "$ROOT/store" ]
}

@test "--adopt of a world not in --worlds refuses before any move" {
  mkdir -p "$ROOT/output"
  echo img >"$ROOT/output/a.png"
  run bash "$INIT" --root "$ROOT" --adopt other
  [ "$status" -eq 2 ]
  [[ "$output" == *"not one of: sfw nsfw"* ]]
  [ -f "$ROOT/output/a.png" ]
  [ ! -e "$ROOT/worlds" ]
}

@test "a root holding only models/ is refused without --adopt, file untouched" {
  mkdir -p "$ROOT/models/checkpoints"
  printf 'mm' >"$ROOT/models/checkpoints/m.safetensors"
  run bash "$INIT" --root "$ROOT"
  [ "$status" -ne 0 ]
  [[ "$output" == *"pass --adopt <world> to move it"* ]]
  [ -f "$ROOT/models/checkpoints/m.safetensors" ]
  [ ! -e "$ROOT/worlds" ]
  [ ! -e "$ROOT/store" ]
}

@test "--adopt sfw moves output/input/user/custom_nodes and the models into the store, printing each move" {
  mkdir -p "$ROOT/output" "$ROOT/input" "$ROOT/user/default/workflows" "$ROOT/custom_nodes" "$ROOT/models/checkpoints"
  echo img >"$ROOT/output/a.png"; echo wf >"$ROOT/user/default/workflows/w.json"; printf 'mm' >"$ROOT/models/checkpoints/m.safetensors"
  FETCH_PY="$BATS_TEST_DIRNAME/../../pkgs/media-fetch/fetch.py" run bash "$INIT" --root "$ROOT" --adopt sfw
  [ "$status" -eq 0 ]
  [ -f "$ROOT/worlds/sfw/output/a.png" ]
  [ ! -e "$ROOT/output" ]
  [ -f "$ROOT/worlds/sfw/lab/user/default/workflows/w.json" ]
  h=$(printf 'mm' | sha256sum | cut -d' ' -f1)
  [ -f "$ROOT/store/$h/m.safetensors" ]
  [ -L "$ROOT/worlds/sfw/models/checkpoints/m.safetensors" ]
  [ ! -e "$ROOT/models" ]
  grep -q 'dest = "checkpoints/m.safetensors"' "$ROOT/worlds/sfw/lab/manifest.toml"
  [[ "$output" == *"MOVE output -> worlds/sfw/output"* ]]
  [[ "$output" == *"ADOPT checkpoints/m.safetensors -> ${h:0:12}"* ]]
}