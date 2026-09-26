#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
usage: basket <command> [args]

commands:
  validate-manifest <manifest.json>
  encrypt <src-dir> --manifest <manifest.json> --recipients <file> --store <dir>
  decrypt <store-entry-dir> --identity <file> --into <dir>
  mount <store-entry-dir> --identity <file> [--runtime-dir <dir>] [--size <size>]
  teardown <id> [--runtime-dir <dir>]
  lock <store> --out <baskets.lock> [--order <id,id,...>]
  verify <store> --lock <baskets.lock>
  doctor [--root <prefix>]
EOF
}

die() {
  echo "basket: $*" >&2
  exit 1
}

validate_manifest() {
  local f="$1"
  jq -e . "$f" >/dev/null 2>&1 || die "manifest: not valid JSON: $f"
  local keys
  keys=$(jq -r 'keys_unsorted | sort | join(",")' "$f")
  [[ "$keys" == "access,classification,id,mount" ]] ||
    die "manifest: must have exactly keys id, classification, mount, access (got: $keys)"
  local id classification mount access
  id=$(jq -r '.id' "$f")
  classification=$(jq -r '.classification' "$f")
  mount=$(jq -r '.mount' "$f")
  access=$(jq -r '.access' "$f")
  [[ "$id" =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "manifest: bad id: $id"
  case "$classification" in
    local-only | redacted | permitted) ;;
    *) die "manifest: bad classification: $classification" ;;
  esac
  [[ "$mount" == /* ]] || die "manifest: mount must be an absolute path: $mount"
  case "$access" in
    ro | rw) ;;
    *) die "manifest: bad access: $access" ;;
  esac
}

cmd_validate_manifest() {
  [[ $# -eq 1 ]] || die "validate-manifest takes exactly one file"
  validate_manifest "$1"
}

pack_deterministic() {
  local src="$1"
  tar --format=posix --pax-option=exthdr.name=%d/PaxHeaders/%f,delete=atime,delete=ctime \
    --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -cf - -C "$src" .
}

cmd_encrypt() {
  local src="" manifest="" recipients="" store=""
  src="$1"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --manifest)
        manifest="$2"
        shift 2
        ;;
      --recipients)
        recipients="$2"
        shift 2
        ;;
      --store)
        store="$2"
        shift 2
        ;;
      *) die "encrypt: unknown arg $1" ;;
    esac
  done
  [[ -d "$src" && -f "$manifest" && -f "$recipients" && -n "$store" ]] ||
    die "encrypt: need <src-dir> --manifest --recipients --store"
  validate_manifest "$manifest"
  local id entry
  id=$(jq -r '.id' "$manifest")
  entry="$store/$id"
  mkdir -p "$entry"
  local hash
  hash=$(pack_deterministic "$src" | sha256sum | cut -d' ' -f1)
  pack_deterministic "$src" | age --encrypt --recipients-file "$recipients" -o "$entry/payload.tar.age"
  cp "$manifest" "$entry/manifest.json"
  printf '%s\n' "$hash" >"$entry/content.sha256"
  echo "encrypted $id content=$hash"
}

cmd_decrypt() {
  local entry="" identity="" into=""
  entry="$1"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --identity)
        identity="$2"
        shift 2
        ;;
      --into)
        into="$2"
        shift 2
        ;;
      *) die "decrypt: unknown arg $1" ;;
    esac
  done
  [[ -d "$entry" && -f "$identity" && -d "$into" ]] ||
    die "decrypt: need <store-entry-dir> --identity <file> --into <existing-dir>"
  local expected tarball
  expected=$(cat "$entry/content.sha256")
  tarball="$into/.basket-payload.$$.tar"
  if ! age --decrypt --identity "$identity" -o "$tarball" "$entry/payload.tar.age"; then
    rm -f "$tarball"
    die "decrypt: age decryption failed"
  fi
  local actual
  actual=$(sha256sum "$tarball" | cut -d' ' -f1)
  if [[ "$actual" != "$expected" ]]; then
    rm -f "$tarball"
    die "decrypt: content hash mismatch (expected $expected, got $actual)"
  fi
  tar -xf "$tarball" -C "$into"
  rm -f "$tarball"
}

cmd_mount() {
  local entry="" identity="" runtime_dir="/run/baskets" size="512M"
  entry="$1"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --identity)
        identity="$2"
        shift 2
        ;;
      --runtime-dir)
        runtime_dir="$2"
        shift 2
        ;;
      --size)
        size="$2"
        shift 2
        ;;
      *) die "mount: unknown arg $1" ;;
    esac
  done
  [[ "$(id -u)" -eq 0 ]] || die "mount: must run as root"
  [[ -d "$entry" && -f "$identity" ]] || die "mount: need <store-entry-dir> --identity <file>"
  validate_manifest "$entry/manifest.json"
  local id access mnt staging
  id=$(jq -r '.id' "$entry/manifest.json")
  access=$(jq -r '.access' "$entry/manifest.json")
  mnt="$runtime_dir/$id"
  staging="$runtime_dir/.basket-tmpfs-$id"
  if mountpoint -q "$mnt" 2>/dev/null; then
    die "mount: $mnt is already mounted"
  fi
  if mountpoint -q "$staging" 2>/dev/null; then
    die "mount: stale staging mount at $staging (tear it down first)"
  fi
  # The tmpfs lives at a hidden staging mountpoint and is bind-mounted into
  # place at $mnt. Two host realities force this shape: (1) a plain
  # `mount -o remount,ro` on the tmpfs fails inside user namespaces
  # ("fsconfig() failed: tmpfs: Invalid uid"), because libmount re-derives
  # fs-specific options with ids the namespace cannot map — a bind remount
  # touches only generic VFS flags; (2) `mount --move` is refused under the
  # shared mount propagation systemd hosts use, so the tmpfs must start at
  # the staging path rather than be moved there. The bind leaves exactly one
  # mount entry at $mnt, so `findmnt --target` sees a single tmpfs.
  mkdir -p "$staging" "$mnt"
  local mount_done=0
  cleanup_mount() {
    [[ $mount_done -eq 1 ]] && return 0
    umount "$mnt" 2>/dev/null || true
    umount "$staging" 2>/dev/null || true
    rmdir "$mnt" "$staging" 2>/dev/null || true
    echo "mount: aborted; staging tmpfs torn down" >&2
  }
  trap cleanup_mount EXIT INT TERM
  mount -t tmpfs -o "size=$size,mode=0700" "basket-$id" "$staging"
  # subshell: cmd_decrypt uses die (exit); the subshell turns that into a
  # failure the trap above cleans up after.
  (cmd_decrypt "$entry" --identity "$identity" --into "$staging") || die "mount: decryption failed, tmpfs torn down"
  mount --bind "$staging" "$mnt"
  if [[ "$access" == "ro" ]]; then
    mount -o remount,bind,ro "$mnt"
  fi
  mount_done=1
  trap - EXIT INT TERM
  echo "mounted $id at $mnt ($access)"
}

cmd_teardown() {
  local id="" runtime_dir="/run/baskets"
  id="$1"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --runtime-dir)
        runtime_dir="$2"
        shift 2
        ;;
      *) die "teardown: unknown arg $1" ;;
    esac
  done
  local mnt="$runtime_dir/$id" staging="$runtime_dir/.basket-tmpfs-$id"
  if ! mountpoint -q "$mnt" 2>/dev/null && ! mountpoint -q "$staging" 2>/dev/null; then
    die "teardown: $id is not mounted (neither $mnt nor $staging)"
  fi
  # A basket may carry more than one mount layer (a stray bind on top of the
  # bind); unmount until nothing is left, bounded, lazy only as a last resort.
  unmount_all() {
    local p=$1 n=0
    while mountpoint -q "$p" 2>/dev/null; do
      n=$((n + 1))
      [[ $n -le 8 ]] || die "teardown: $p still mounted after 8 rounds"
      if ! umount "$p" 2>/dev/null; then
        echo "teardown: umount $p failed, detaching lazily (open handles keep the tmpfs alive until they close)" >&2
        umount -l "$p"
      fi
    done
  }
  unmount_all "$mnt"
  [[ -d "$mnt" ]] && rmdir "$mnt"
  unmount_all "$staging"
  [[ -d "$staging" ]] && rmdir "$staging"
  if mountpoint -q "$mnt" 2>/dev/null || mountpoint -q "$staging" 2>/dev/null; then
    die "teardown: $id still mounted"
  fi
  echo "torn down $id"
}

lock_entry_json() {
  local store="$1" id="$2" entry
  entry="$store/$id"
  [[ -d "$entry" ]] || die "lock: no such basket in store: $id"
  local content payload manifest
  content=$(cat "$entry/content.sha256")
  payload=$(sha256sum "$entry/payload.tar.age" | cut -d' ' -f1)
  manifest=$(sha256sum "$entry/manifest.json" | cut -d' ' -f1)
  jq -n \
    --arg content "$content" --arg payload "$payload" --arg manifest "$manifest" \
    --slurpfile m "$entry/manifest.json" \
    '$m[0] + {content_sha256: $content, payload_sha256: $payload, manifest_sha256: $manifest}'
}

cmd_lock() {
  local store="" out="" order=""
  store="$1"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --out)
        out="$2"
        shift 2
        ;;
      --order)
        order="$2"
        shift 2
        ;;
      *) die "lock: unknown arg $1" ;;
    esac
  done
  [[ -d "$store" && -n "$out" ]] || die "lock: need <store> --out <file>"
  local ids
  if [[ -n "$order" ]]; then
    ids=$(tr ',' '\n' <<<"$order")
  else
    ids=$(find "$store" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort)
  fi
  local entries="[]"
  local id entry_json
  while IFS= read -r id; do
    [[ -n "$id" ]] || continue
    entry_json="$(lock_entry_json "$store" "$id")"
    entries=$(jq --argjson e "$entry_json" '. + [$e]' <<<"$entries")
  done <<<"$ids"
  jq -n --argjson baskets "$entries" '{version: 1, baskets: $baskets}' >"$out"
  echo "locked $(jq -r '.baskets | length' "$out") baskets to $out"
}

cmd_verify() {
  local store="" lock=""
  store="$1"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --lock)
        lock="$2"
        shift 2
        ;;
      *) die "verify: unknown arg $1" ;;
    esac
  done
  [[ -d "$store" && -f "$lock" ]] || die "verify: need <store> --lock <file>"
  local failed=0
  local id
  while IFS= read -r id; do
    local expected actual
    expected=$(jq -c --arg id "$id" '.baskets[] | select(.id == $id)' "$lock")
    if [[ ! -d "$store/$id" ]]; then
      echo "verify: $id: missing from store" >&2
      failed=1
      continue
    fi
    actual=$(lock_entry_json "$store" "$id")
    if [[ "$(jq -S . <<<"$expected")" != "$(jq -S . <<<"$actual")" ]]; then
      echo "verify: $id: mismatch" >&2
      diff <(jq -S . <<<"$expected") <(jq -S . <<<"$actual") >&2 || true
      failed=1
    fi
  done < <(jq -r '.baskets[].id' "$lock")
  local extra
  while IFS= read -r extra; do
    if ! jq -e --arg id "$extra" '.baskets[] | select(.id == $id)' "$lock" >/dev/null; then
      echo "verify: $extra: present in store but not in lock" >&2
      failed=1
    fi
  done < <(find "$store" -mindepth 1 -maxdepth 1 -type d -printf '%f\n')
  [[ "$failed" -eq 0 ]] || exit 1
  echo "verified: store matches $lock"
}

cmd_doctor() {
  local root="/"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --root)
        root="$2"
        shift 2
        ;;
      *) die "doctor: unknown arg $1" ;;
    esac
  done
  root="${root%/}"
  local failed=0
  probe() {
    local verdict="$1" name="$2" detail="$3"
    printf '%-4s %-12s %s\n' "$verdict" "$name" "$detail"
    if [[ "$verdict" == "FAIL" ]]; then
      failed=1
    fi
  }
  if [[ -f "$root/proc/swaps" ]] && [[ "$(wc -l <"$root/proc/swaps")" -gt 1 ]]; then
    probe FAIL swap "swap is active — tmpfs pages could reach disk (invariant 1)"
  else
    probe PASS swap "no active swap"
  fi
  if [[ -e "$root/run/pcscd/pcscd.comm" ]]; then
    probe PASS pcscd "smartcard daemon socket present"
  else
    probe WARN pcscd "pcscd socket absent — YubiKey decryption will fail"
  fi
  if command -v age-plugin-yubikey >/dev/null; then
    probe PASS age-plugin "age-plugin-yubikey on PATH"
  else
    probe WARN age-plugin "age-plugin-yubikey not on PATH for this process"
  fi
  if [[ -e "$root/dev/kvm" ]]; then
    probe PASS kvm "/dev/kvm present"
  else
    probe WARN kvm "/dev/kvm absent — Cowork and microvms unavailable"
  fi
  if [[ -d "$root/sys/module/vhost_vsock" ]]; then
    probe PASS vsock "vhost_vsock loaded"
  else
    probe WARN vsock "vhost_vsock not loaded"
  fi
  if [[ -d "$root/run/baskets" ]] && [[ -n "$(ls -A "$root/run/baskets" 2>/dev/null)" ]]; then
    probe FAIL stale-mounts "entries under /run/baskets — decrypted material may linger (run basket teardown)"
  else
    probe PASS stale-mounts "no leftover basket mounts"
  fi
  [[ "$failed" -eq 0 ]] || exit 1
}

main() {
  if [[ $# -eq 0 ]]; then
    usage
    exit 2
  fi
  case "$1" in
    -h | --help)
      usage
      ;;
    validate-manifest)
      shift
      cmd_validate_manifest "$@"
      ;;
    encrypt)
      shift
      cmd_encrypt "$@"
      ;;
    decrypt)
      shift
      cmd_decrypt "$@"
      ;;
    mount)
      shift
      cmd_mount "$@"
      ;;
    teardown)
      shift
      cmd_teardown "$@"
      ;;
    lock)
      shift
      cmd_lock "$@"
      ;;
    verify)
      shift
      cmd_verify "$@"
      ;;
    doctor)
      shift
      cmd_doctor "$@"
      ;;
    *)
      usage
      exit 2
      ;;
  esac
}

main "$@"
