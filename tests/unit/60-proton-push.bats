#!/usr/bin/env bats

setup() {
  cd "$BATS_TEST_TMPDIR"
  mkdir -p repo/keys repo/index repo/snapshots repo/data/00 repo/data/ab repo/locks remote/my-files/backups
  echo cfg >repo/config; echo k >repo/keys/k1; echo i >repo/index/i1
  echo s1 >repo/snapshots/s1; echo s2 >repo/snapshots/s2; echo p1 >repo/data/00/p1; echo p2 >repo/data/ab/p2
  export MOCK_REMOTE_ROOT="$BATS_TEST_TMPDIR/remote" MOCK_CALLS="$BATS_TEST_TMPDIR/calls.log"
  export PROTON_DRIVE_CLI="$BATS_TEST_DIRNAME/../mocks/proton-drive-mock.sh"
  export PROTON_BACKUP_REPO="$BATS_TEST_TMPDIR/repo" PROTON_BACKUP_REMOTE_PARENT=/my-files/backups
  export PROTON_BACKUP_LOCK_WAIT_SECONDS=2 XDG_RUNTIME_DIR="$BATS_TEST_TMPDIR"
}

@test "first push creates the remote folder and uploads everything except locks" {
  run proton-backup-push
  [ "$status" -eq 0 ]
  [[ "$output" == *"proton-backup-push: OK snapshots=2 remote=2"* ]]
  grep -q '^filesystem create-folder /my-files/backups repo$' calls.log
  [ -f remote/my-files/backups/repo/config ]
  [ -f remote/my-files/backups/repo/snapshots/s2 ]
  [ -f remote/my-files/backups/repo/data/ab/p2 ]
  [ ! -e remote/my-files/backups/repo/locks ]
}

@test "second push is idempotent and reconciles pruned objects" {
  run proton-backup-push; [ "$status" -eq 0 ]
  rm repo/data/00/p1 repo/index/i1; echo i2 >repo/index/i2
  run proton-backup-push
  [ "$status" -eq 0 ]
  [ ! -e remote/my-files/backups/repo/data/00/p1 ]
  [ ! -e remote/my-files/backups/repo/index/i1 ]
  [ -f remote/my-files/backups/repo/index/i2 ]
  # the real CLI only permanently deletes items already in trash, so stale
  # objects are trashed (batched into one call) then deleted by /trash/<name>
  grep '^filesystem trash ' calls.log | grep -q '/my-files/backups/repo/data/00/p1'
  ! grep '^filesystem trash ' calls.log | grep -q '/my-files/backups/repo/keys'
  grep '^filesystem delete ' calls.log | grep -q '/trash/p1'
  grep '^filesystem delete ' calls.log | grep -q '/trash/i1'
  ! grep '^filesystem delete ' calls.log | grep -q '/my-files'
  ! grep -q 'empty-trash' calls.log
}

@test "refuses to reconcile when the local repo has no snapshots" {
  run proton-backup-push; [ "$status" -eq 0 ]
  rm repo/snapshots/*
  run proton-backup-push
  [ "$status" -eq 1 ]
  [[ "$output" == *"refusing"* ]]
  [ -f remote/my-files/backups/repo/snapshots/s1 ]
}

@test "refuses to delete more than half of all remote objects unless forced" {
  run proton-backup-push; [ "$status" -eq 0 ]
  for i in 3 4 5 6; do echo "s$i" >repo/snapshots/s$i; done
  run proton-backup-push; [ "$status" -eq 0 ]
  # remote now holds 9 objects (1 index, 6 snapshots, 2 packs); drop 5
  rm repo/snapshots/s1 repo/snapshots/s2 repo/snapshots/s3 repo/snapshots/s4 repo/snapshots/s5
  run proton-backup-push
  [ "$status" -eq 1 ]
  [[ "$output" == *"refusing to delete 5 of 9"* ]]
  [ -f remote/my-files/backups/repo/snapshots/s1 ]
  PROTON_BACKUP_FORCE_RECONCILE=1 run proton-backup-push
  [ "$status" -eq 0 ]
  [ ! -e remote/my-files/backups/repo/snapshots/s1 ]
  [ -f remote/my-files/backups/repo/snapshots/s6 ]
}

@test "fails when remote snapshot count does not match local after upload" {
  run proton-backup-push; [ "$status" -eq 0 ]
  echo s3 >repo/snapshots/s3
  MOCK_UPLOAD_NOOP=1 run proton-backup-push   # remote silently keeps 2 snapshots
  [ "$status" -eq 1 ]
  [[ "$output" == *"parity FAIL"* ]]
}

@test "waits for restic locks to clear, then gives up loudly" {
  touch repo/locks/abc
  run proton-backup-push
  [ "$status" -eq 1 ]
  [[ "$output" == *"restic lock"* ]]
}
