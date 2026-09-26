#!/usr/bin/env bats
# comfy-model-guard (GN14 Interfaces 3): the ExecStartPre of
# comfy-author-model.service. It hashes the GGUF with sha256sum and refuses —
# exit 1, one stderr line naming both values — when the file is absent,
# unreadable, or its digest differs; it passes silently otherwise. The check
# sandbox exports ${comfy-model-guard}/bin on PATH (media/checks.nix, the
# one `export PATH=` line before `bats tests/comfy-worlds`), so the guard is
# called here by bare name — no store path can be interpolated into a .bats
# file.

setup() {
  MODELS="$BATS_TEST_TMPDIR/models"
  mkdir -p "$MODELS"
  printf 'not a real gguf' >"$MODELS/fake.gguf"
  DIGEST="20f7fea9a3ca4565833ecfdb6593541843dc9ae9bebcefbff1d353b5c1391f94"
}

@test "passes silently when the digest matches" {
  run comfy-model-guard "$MODELS/fake.gguf" "$DIGEST"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "refuses a wrong digest with exit 1, naming both values" {
  run comfy-model-guard "$MODELS/fake.gguf" "0000000000000000000000000000000000000000000000000000000000000000"
  [ "$status" -eq 1 ]
  [[ "$output" == *"$MODELS/fake.gguf"* ]]
  [[ "$output" == *"0000000000000000000000000000000000000000000000000000000000000000"* ]]
  [[ "$output" == *"$DIGEST"* ]]
}

@test "refuses an absent file with exit 1" {
  run comfy-model-guard "$MODELS/absent.gguf" "$DIGEST"
  [ "$status" -eq 1 ]
  [[ "$output" == *"$MODELS/absent.gguf"* ]]
}

@test "refuses a directory as the model path with exit 1" {
  run comfy-model-guard "$MODELS" "$DIGEST"
  [ "$status" -eq 1 ]
  [[ "$output" == *"$MODELS"* ]]
}

@test "refuses an unreadable file with exit 1" {
  # Permission bits cannot stop the nix build sandbox (root-like in its
  # user namespace), so the deterministic unreadable regular file is
  # /proc/self/mem: openable, stat-able as regular, and its read fails
  # with EIO for every uid — the guard's hash-failure arm, both here and
  # in the devShell.
  run comfy-model-guard /proc/self/mem "$DIGEST"
  [ "$status" -eq 1 ]
  [[ "$output" == *"/proc/self/mem"* ]]
}
