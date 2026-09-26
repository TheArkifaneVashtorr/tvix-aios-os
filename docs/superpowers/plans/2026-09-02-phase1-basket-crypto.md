# Phase 1 — Basket Crypto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tested `basket` CLI that encrypts/decrypts classified data baskets with age (YubiKey recipients), mounts plaintext only into tmpfs, and pins content with `baskets.lock` — plus the flake/lint scaffolding every later phase builds on.

**Architecture:** One bash CLI (`pkgs/basket/basket.sh`) packaged via `writeShellApplication`, exercised by bats tests using *software* age keys (hardware YubiKey path is covered by the operator acceptance script only). Deterministic tar gives a stable plaintext content hash so re-encryption never churns `baskets.lock` content identity. Mount lifecycle tests run unprivileged inside `unshare --user --map-root-user --mount`; the nix-sandboxed `checks` run everything except mount tests.

**Tech Stack:** Nix flake (nixpkgs pinned), bash, age + age-plugin-yubikey, GNU tar, jq, bats-core, treefmt + nixfmt-rfc-style + shfmt, shellcheck, statix, deadnix.

**Spec:** `docs/superpowers/specs/2026-09-02-agent-environment-design.md` (§2.2 baskets) and `docs/brief.md` §5.2, §7 Phase 1.

## Global Constraints

- nixpkgs pinned to exactly `github:NixOS/nixpkgs/34ab99075ac4f7e40cf037eef32cb1c360bb85e9` (nixos-unstable, verified 2026-09-02). No other flake inputs in Phase 1.
- No secret material in the repo ever: software test keys are generated at test runtime into `$BATS_TEST_TMPDIR`, never committed. Recipients files in-repo contain only placeholder comments.
- Plaintext basket content may exist only under the caller-supplied target directory (tmpfs in real use, test tmpdirs in tests) — never in `/tmp`, never in the store dir.
- All bash: `set -euo pipefail`, shellcheck-clean at 0.11.0 defaults, formatted by shfmt (via treefmt).
- Deterministic tar invocation, verbatim everywhere it appears:
  `tar --format=posix --pax-option=exthdr.name=%d/PaxHeaders/%f,delete=atime,delete=ctime --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner -cf - -C "$src" .`
- Store layout produced/consumed by every task: `<store>/<id>/manifest.json`, `<store>/<id>/payload.tar.age`, `<store>/<id>/content.sha256`.
- Classifications: exactly `local-only`, `redacted`, `permitted`. Access: exactly `ro`, `rw`.
- Commits: one per task minimum, message `phase1: <task summary>`, trailer lines exactly:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01YF8cJcGgr39Erx7zDATAjP`.
- Never push. Never add a remote. Work only in `/home/dalhaka/nixos-agent-env`.
- Run `nix develop -c <cmd>` for ALL tool invocations **including `git commit`**
  (the pre-commit hook needs the devShell's lint tools and refuses to run without
  them): `nix develop -c git commit -m "..."`.
- bash `set -e` discipline: never write `cond && die ...` (a false `cond` aborts the
  script); use `if cond; then die ...; fi`. Never rely on `if ! some_fn` to catch a
  function that calls `die` (die exits the shell); run it in a subshell:
  `if ! (some_fn ...); then`.

---

### Task 1: Flake bootstrap + lint toolchain + hooks

**Files:**
- Create: `flake.nix`
- Create: `treefmt.toml`
- Create: `githooks/pre-commit`
- Create: `pkgs/basket/basket.sh` (skeleton: arg parsing + `usage` only)
- Create: `tests/unit/00-smoke.bats`

**Interfaces:**
- Produces: `packages.x86_64-linux.basket` (command `basket`), `devShells.x86_64-linux.default` (provides basket's runtime deps + bats + lint tools; shellHook sets `core.hooksPath`), `checks.x86_64-linux.lint`, `checks.x86_64-linux.unit`. Later tasks add subcommands to `basket.sh` and files under `tests/unit/`; they change nothing in `flake.nix`.

- [ ] **Step 1: Write the failing smoke test**

`tests/unit/00-smoke.bats`:

```bash
#!/usr/bin/env bats

@test "basket prints usage and exits 2 with no args" {
  run basket
  [ "$status" -eq 2 ]
  [[ "$output" == *"usage: basket"* ]]
}

@test "basket --help exits 0" {
  run basket --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"usage: basket"* ]]
}
```

- [ ] **Step 2: Write `flake.nix`**

```nix
{
  description = "NixOS agent environments with encrypted data baskets";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/34ab99075ac4f7e40cf037eef32cb1c360bb85e9";

  outputs =
    { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      basketRuntimeInputs = with pkgs; [
        age
        age-plugin-yubikey
        coreutils
        gnutar
        jq
        util-linux
      ];
      basket = pkgs.writeShellApplication {
        name = "basket";
        runtimeInputs = basketRuntimeInputs;
        text = builtins.readFile ./pkgs/basket/basket.sh;
      };
      lintTools = with pkgs; [
        treefmt
        nixfmt-rfc-style
        shfmt
        shellcheck
        statix
        deadnix
      ];
    in
    {
      packages.${system} = {
        inherit basket;
        default = basket;
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = basketRuntimeInputs ++ lintTools ++ [
          basket
          pkgs.bats
        ];
        shellHook = ''
          git config core.hooksPath githooks
        '';
      };

      checks.${system} = {
        lint =
          pkgs.runCommand "lint"
            {
              nativeBuildInputs = lintTools;
            }
            ''
              cp -r ${self} src && chmod -R u+w src && cd src
              treefmt --ci --config-file treefmt.toml --tree-root .
              shellcheck pkgs/basket/basket.sh githooks/pre-push githooks/pre-commit
              find tests -name '*.sh' -print0 | xargs -0 --no-run-if-empty shellcheck
              statix check .
              deadnix --fail .
              touch $out
            '';
        unit =
          pkgs.runCommand "unit-tests"
            {
              nativeBuildInputs = [
                pkgs.bats
                basket
              ] ++ basketRuntimeInputs;
            }
            ''
              cp -r ${self}/tests tests
              bats tests/unit
              touch $out
            '';
      };

      formatter.${system} = pkgs.treefmt;
    };
}
```

- [ ] **Step 3: Write `treefmt.toml`**

```toml
[formatter.nix]
command = "nixfmt"
includes = ["*.nix"]

[formatter.shell]
command = "shfmt"
options = ["-i", "2", "-ci", "-w"]
includes = ["*.sh", "githooks/pre-push", "githooks/pre-commit"]
```

- [ ] **Step 4: Write the CLI skeleton `pkgs/basket/basket.sh`**

Note: `writeShellApplication` prepends the shebang and `set -euo pipefail`; the file starts directly with code. shellcheck of the bare file needs a shebang, so include one; writeShellApplication tolerates it.

```bash
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
EOF
}

die() {
  echo "basket: $*" >&2
  exit 1
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
    *)
      usage
      exit 2
      ;;
  esac
}

main "$@"
```

- [ ] **Step 5: Write `githooks/pre-commit`**

```bash
#!/usr/bin/env bash
# Autolint gate: formatting and static analysis must pass before any commit.
set -euo pipefail
if ! command -v treefmt >/dev/null; then
  echo "pre-commit: lint tools missing — commit from the devShell: nix develop -c git commit ..." >&2
  exit 1
fi
treefmt --ci --config-file treefmt.toml --tree-root . ||
  { echo "pre-commit: treefmt found unformatted files (run: treefmt)" >&2; exit 1; }
shellcheck pkgs/basket/basket.sh githooks/pre-push githooks/pre-commit
find tests -name '*.sh' -print0 2>/dev/null | xargs -0 --no-run-if-empty shellcheck
statix check .
deadnix --fail .
```

Make it executable: `chmod +x githooks/pre-commit`.

- [ ] **Step 6: Run the failing test, then make it pass**

Run: `nix develop -c bats tests/unit/00-smoke.bats` — first confirm both tests pass against the skeleton (`no args` → exit 2 via usage; `--help` → 0). If `basket` is not found, the devShell build failed — fix `flake.nix` first.

- [ ] **Step 7: Full check**

Run: `nix flake check` — expect all checks green. `git status` must show no unstaged formatter rewrites afterwards (run `nix develop -c treefmt` once and re-stage if it reformatted files).

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "phase1: flake bootstrap, lint toolchain, basket CLI skeleton"
```
(with the two mandatory trailer lines from Global Constraints)

---

### Task 2: Manifest validation

**Files:**
- Modify: `pkgs/basket/basket.sh` (add `cmd_validate_manifest`, wire into `main`)
- Create: `tests/unit/10-manifest.bats`
- Create: `examples/manifest.json`

**Interfaces:**
- Produces: `basket validate-manifest <file>` — exit 0 valid, exit 1 with `basket: manifest: <reason>` on stderr otherwise. Function `validate_manifest <file>` reusable by Tasks 3–5. Valid manifest = JSON object with exactly the keys `id`, `classification`, `mount`, `access`; `id` matches `^[a-z0-9][a-z0-9-]*$`; `classification` ∈ {local-only, redacted, permitted}; `mount` absolute path; `access` ∈ {ro, rw}.

- [ ] **Step 1: Write the failing tests** — `tests/unit/10-manifest.bats`:

```bash
#!/usr/bin/env bats

setup() {
  cd "$BATS_TEST_TMPDIR"
  cat >good.json <<'EOF'
{ "id": "work-notes", "classification": "local-only", "mount": "/data/notes", "access": "ro" }
EOF
}

@test "accepts a valid manifest" {
  run basket validate-manifest good.json
  [ "$status" -eq 0 ]
}

@test "rejects unknown classification" {
  jq '.classification = "public"' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
  [[ "$output" == *"classification"* ]]
}

@test "rejects extra keys" {
  jq '. + {evil: true}' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
}

@test "rejects missing keys" {
  jq 'del(.mount)' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
}

@test "rejects relative mount path" {
  jq '.mount = "data/notes"' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
  [[ "$output" == *"mount"* ]]
}

@test "rejects bad id" {
  jq '.id = "Work Notes!"' good.json >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
  [[ "$output" == *"id"* ]]
}

@test "rejects non-JSON" {
  echo "not json" >bad.json
  run basket validate-manifest bad.json
  [ "$status" -eq 1 ]
}
```

- [ ] **Step 2: Run to verify failure** — `nix develop -c bats tests/unit/10-manifest.bats` → expect FAIL (usage exit 2).

- [ ] **Step 3: Implement** — add to `basket.sh` above `main`, and a `validate-manifest)` case arm calling `cmd_validate_manifest "$@"` (after `shift`):

```bash
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
```

- [ ] **Step 4: Run tests to verify pass** — `nix develop -c bats tests/unit/10-manifest.bats` → all PASS. Also create `examples/manifest.json` with the exact `good.json` content above.

- [ ] **Step 5: Lint + commit**

```bash
nix develop -c treefmt && nix flake check
git add -A && git commit -m "phase1: manifest schema validation"
```

---

### Task 3: Deterministic pack, encrypt, decrypt

**Files:**
- Modify: `pkgs/basket/basket.sh` (add `pack_deterministic`, `cmd_encrypt`, `cmd_decrypt`; wire into `main`)
- Create: `tests/unit/20-crypto.bats`

**Interfaces:**
- Consumes: `validate_manifest` (Task 2).
- Produces: store entries `<store>/<id>/{manifest.json,payload.tar.age,content.sha256}`; `basket encrypt <src-dir> --manifest <m> --recipients <r> --store <s>` (exit 0, prints `encrypted <id> content=<sha256>`); `basket decrypt <store>/<id> --identity <i> --into <dir>` (exit 0; exit 1 on bad identity/hash mismatch). `pack_deterministic <src-dir>` writes the deterministic tar to stdout. Tasks 4–5 rely on all three.

- [ ] **Step 1: Write the failing tests** — `tests/unit/20-crypto.bats`:

```bash
#!/usr/bin/env bats

setup() {
  cd "$BATS_TEST_TMPDIR"
  age-keygen -o key.txt 2>/dev/null
  age-keygen -y key.txt >recipients.txt
  mkdir -p src/sub store out
  echo "hello" >src/a.txt
  echo "world" >src/sub/b.txt
  cat >manifest.json <<'EOF'
{ "id": "demo", "classification": "permitted", "mount": "/data/demo", "access": "rw" }
EOF
}

encrypt_demo() {
  basket encrypt src --manifest manifest.json --recipients recipients.txt --store store
}

@test "encrypt creates the store layout" {
  encrypt_demo
  [ -f store/demo/manifest.json ]
  [ -f store/demo/payload.tar.age ]
  [ -f store/demo/content.sha256 ]
}

@test "content hash is deterministic across re-encryption" {
  encrypt_demo
  h1=$(cat store/demo/content.sha256)
  rm -r store/demo
  encrypt_demo
  h2=$(cat store/demo/content.sha256)
  [ "$h1" = "$h2" ]
}

@test "round-trip preserves content" {
  encrypt_demo
  basket decrypt store/demo --identity key.txt --into out
  [ "$(cat out/a.txt)" = "hello" ]
  [ "$(cat out/sub/b.txt)" = "world" ]
}

@test "decrypt fails with wrong identity" {
  encrypt_demo
  age-keygen -o wrong.txt 2>/dev/null
  run basket decrypt store/demo --identity wrong.txt --into out
  [ "$status" -eq 1 ]
}

@test "decrypt fails when payload is tampered" {
  encrypt_demo
  # age authenticates its payload; flipping ciphertext must fail decryption
  printf 'X' | dd of=store/demo/payload.tar.age bs=1 seek=100 conv=notrunc 2>/dev/null
  run basket decrypt store/demo --identity key.txt --into out
  [ "$status" -eq 1 ]
}

@test "encrypt refuses an invalid manifest" {
  jq '.access = "rwx"' manifest.json >bad.json
  run basket encrypt src --manifest bad.json --recipients recipients.txt --store store
  [ "$status" -eq 1 ]
}

@test "plaintext never lands outside the target dir" {
  encrypt_demo
  basket decrypt store/demo --identity key.txt --into out
  [ -z "$(find /tmp -maxdepth 1 -name 'basket*' 2>/dev/null)" ]
}
```

- [ ] **Step 2: Run to verify failure** — `nix develop -c bats tests/unit/20-crypto.bats` → FAIL.

- [ ] **Step 3: Implement** — add to `basket.sh`:

```bash
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
      --manifest) manifest="$2"; shift 2 ;;
      --recipients) recipients="$2"; shift 2 ;;
      --store) store="$2"; shift 2 ;;
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
      --identity) identity="$2"; shift 2 ;;
      --into) into="$2"; shift 2 ;;
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
```

Wire `encrypt)` and `decrypt)` case arms in `main` (each does `shift` then `cmd_encrypt "$@"` / `cmd_decrypt "$@"`).

- [ ] **Step 4: Run tests to verify pass** — `nix develop -c bats tests/unit/20-crypto.bats` → all PASS.

- [ ] **Step 5: Lint + commit**

```bash
nix develop -c treefmt && nix flake check
git add -A && git commit -m "phase1: deterministic pack + age encrypt/decrypt round-trip"
```

---

### Task 4: tmpfs mount and teardown

**Files:**
- Modify: `pkgs/basket/basket.sh` (add `cmd_mount`, `cmd_teardown`; wire into `main`)
- Create: `tests/unit/30-mount.bats`
- Create: `tests/run-mount-tests.sh`

**Interfaces:**
- Consumes: `cmd_decrypt`, `validate_manifest`, store layout (Task 3).
- Produces: `basket mount <store-entry> --identity <i> [--runtime-dir /run/baskets] [--size 512M]` — requires root (exit 1 `mount: must run as root` otherwise); creates `<runtime-dir>/<id>` as tmpfs `mode=0700`, decrypts into it, remounts read-only when manifest access is `ro`. `basket teardown <id> [--runtime-dir <dir>]` — unmounts, removes the mountpoint dir, exit 1 if still mounted after. Mount tests run via `tests/run-mount-tests.sh` (userns), NOT inside `nix flake check`.

- [ ] **Step 1: Write the failing tests** — `tests/unit/30-mount.bats`. Guard: these tests skip unless running as (namespace) root, so `checks.unit` skips them in the sandbox and `run-mount-tests.sh` runs them for real:

```bash
#!/usr/bin/env bats

setup() {
  if [[ "$(id -u)" -ne 0 ]]; then
    skip "mount tests need (namespace) root — run tests/run-mount-tests.sh"
  fi
  cd "$BATS_TEST_TMPDIR"
  age-keygen -o key.txt 2>/dev/null
  age-keygen -y key.txt >recipients.txt
  mkdir -p src store run
  echo "secret" >src/data.txt
  cat >manifest.json <<'EOF'
{ "id": "demo", "classification": "local-only", "mount": "/data/demo", "access": "ro" }
EOF
  basket encrypt src --manifest manifest.json --recipients recipients.txt --store store
}

@test "mount decrypts into a tmpfs and teardown removes it" {
  basket mount store/demo --identity key.txt --runtime-dir run --size 16M
  mountpoint -q run/demo
  [ "$(cat run/demo/data.txt)" = "secret" ]
  [ "$(findmnt -no FSTYPE --target run/demo)" = "tmpfs" ]
  basket teardown demo --runtime-dir run
  ! mountpoint -q run/demo
  [ ! -e run/demo/data.txt ]
}

@test "ro manifest yields a read-only mount" {
  basket mount store/demo --identity key.txt --runtime-dir run --size 16M
  run touch run/demo/new.txt
  [ "$status" -ne 0 ]
  basket teardown demo --runtime-dir run
}

@test "teardown fails loudly on unknown id" {
  run basket teardown nope --runtime-dir run
  [ "$status" -eq 1 ]
}
```

- [ ] **Step 2: Write the userns runner** — `tests/run-mount-tests.sh`:

```bash
#!/usr/bin/env bash
# Runs the mount-lifecycle bats suite unprivileged inside a user+mount namespace.
set -euo pipefail
cd "$(dirname "$0")/.."
exec unshare --user --map-root-user --mount bats tests/unit/30-mount.bats
```

`chmod +x tests/run-mount-tests.sh`.

- [ ] **Step 3: Run to verify failure** — `nix develop -c tests/run-mount-tests.sh` → FAIL (unknown command).

- [ ] **Step 4: Implement** — add to `basket.sh`:

```bash
cmd_mount() {
  local entry="" identity="" runtime_dir="/run/baskets" size="512M"
  entry="$1"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --identity) identity="$2"; shift 2 ;;
      --runtime-dir) runtime_dir="$2"; shift 2 ;;
      --size) size="$2"; shift 2 ;;
      *) die "mount: unknown arg $1" ;;
    esac
  done
  [[ "$(id -u)" -eq 0 ]] || die "mount: must run as root"
  [[ -d "$entry" && -f "$identity" ]] || die "mount: need <store-entry-dir> --identity <file>"
  validate_manifest "$entry/manifest.json"
  local id access mnt
  id=$(jq -r '.id' "$entry/manifest.json")
  access=$(jq -r '.access' "$entry/manifest.json")
  mnt="$runtime_dir/$id"
  if mountpoint -q "$mnt" 2>/dev/null; then
    die "mount: $mnt is already mounted"
  fi
  mkdir -p "$mnt"
  mount -t tmpfs -o "size=$size,mode=0700" "basket-$id" "$mnt"
  # subshell: cmd_decrypt uses die (exit); the subshell converts that into a
  # catchable failure so the tmpfs is torn down instead of leaking
  if ! (cmd_decrypt "$entry" --identity "$identity" --into "$mnt"); then
    umount "$mnt"
    rmdir "$mnt"
    die "mount: decryption failed, tmpfs torn down"
  fi
  if [[ "$access" == "ro" ]]; then
    mount -o remount,ro "$mnt"
  fi
  echo "mounted $id at $mnt ($access)"
}

cmd_teardown() {
  local id="" runtime_dir="/run/baskets"
  id="$1"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --runtime-dir) runtime_dir="$2"; shift 2 ;;
      *) die "teardown: unknown arg $1" ;;
    esac
  done
  local mnt="$runtime_dir/$id"
  mountpoint -q "$mnt" || die "teardown: $mnt is not mounted"
  umount "$mnt"
  rmdir "$mnt"
  if mountpoint -q "$mnt" 2>/dev/null; then
    die "teardown: $mnt still mounted"
  fi
  echo "torn down $id"
}
```

Wire `mount)` / `teardown)` case arms in `main`.

- [ ] **Step 5: Run tests to verify pass** — `nix develop -c tests/run-mount-tests.sh` → all PASS. Also `nix flake check` (sandboxed unit check must show mount tests as skipped, everything else green).

- [ ] **Step 6: Lint + commit**

```bash
nix develop -c treefmt && nix flake check
git add -A && git commit -m "phase1: tmpfs mount/teardown lifecycle (userns-tested)"
```

---

### Task 5: baskets.lock generate and verify

**Files:**
- Modify: `pkgs/basket/basket.sh` (add `cmd_lock`, `cmd_verify`; wire into `main`)
- Create: `tests/unit/40-lock.bats`

**Interfaces:**
- Consumes: store layout (Task 3).
- Produces: `basket lock <store> --out <file> [--order id,id,...]` writes canonical JSON `{"version":1,"baskets":[{id,classification,mount,access,content_sha256,payload_sha256,manifest_sha256},...]}` (array order = `--order`, default alphabetical; unknown ids in `--order` are an error). `basket verify <store> --lock <file>` recomputes every field and exits 1 on any mismatch, missing entry, or extra store entry not in the lock, printing which basket and field diverged.

- [ ] **Step 1: Write the failing tests** — `tests/unit/40-lock.bats`:

```bash
#!/usr/bin/env bats

setup() {
  cd "$BATS_TEST_TMPDIR"
  age-keygen -o key.txt 2>/dev/null
  age-keygen -y key.txt >recipients.txt
  mkdir -p a b store
  echo "alpha" >a/x.txt
  echo "beta" >b/y.txt
  printf '{ "id": "alpha", "classification": "permitted", "mount": "/data/a", "access": "ro" }\n' >ma.json
  printf '{ "id": "beta", "classification": "local-only", "mount": "/data/b", "access": "rw" }\n' >mb.json
  basket encrypt a --manifest ma.json --recipients recipients.txt --store store
  basket encrypt b --manifest mb.json --recipients recipients.txt --store store
}

@test "lock captures every basket with all hash fields" {
  basket lock store --out baskets.lock
  [ "$(jq -r '.version' baskets.lock)" = "1" ]
  [ "$(jq -r '.baskets | length' baskets.lock)" = "2" ]
  [ "$(jq -r '.baskets[0].id' baskets.lock)" = "alpha" ]
  for f in content_sha256 payload_sha256 manifest_sha256; do
    [ "$(jq -r ".baskets[0].$f | length" baskets.lock)" = "64" ]
  done
}

@test "lock respects explicit order" {
  basket lock store --out baskets.lock --order beta,alpha
  [ "$(jq -r '.baskets[0].id' baskets.lock)" = "beta" ]
}

@test "lock rejects unknown id in order" {
  run basket lock store --out baskets.lock --order alpha,ghost
  [ "$status" -eq 1 ]
}

@test "verify passes on an untouched store" {
  basket lock store --out baskets.lock
  basket verify store --lock baskets.lock
}

@test "verify catches manifest tampering" {
  basket lock store --out baskets.lock
  jq '.access = "rw"' store/alpha/manifest.json >t && mv t store/alpha/manifest.json
  run basket verify store --lock baskets.lock
  [ "$status" -eq 1 ]
  [[ "$output" == *"alpha"* ]]
}

@test "verify catches payload swap" {
  basket lock store --out baskets.lock
  cp store/beta/payload.tar.age store/alpha/payload.tar.age
  run basket verify store --lock baskets.lock
  [ "$status" -eq 1 ]
}

@test "verify catches an extra store entry" {
  basket lock store --out baskets.lock
  mkdir -p c && echo "gamma" >c/z.txt
  printf '{ "id": "gamma", "classification": "permitted", "mount": "/data/c", "access": "ro" }\n' >mc.json
  basket encrypt c --manifest mc.json --recipients recipients.txt --store store
  run basket verify store --lock baskets.lock
  [ "$status" -eq 1 ]
  [[ "$output" == *"gamma"* ]]
}
```

- [ ] **Step 2: Run to verify failure** — `nix develop -c bats tests/unit/40-lock.bats` → FAIL.

- [ ] **Step 3: Implement** — add to `basket.sh`:

```bash
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
      --out) out="$2"; shift 2 ;;
      --order) order="$2"; shift 2 ;;
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
  local id
  while IFS= read -r id; do
    [[ -n "$id" ]] || continue
    entries=$(jq --argjson e "$(lock_entry_json "$store" "$id")" '. + [$e]' <<<"$entries")
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
      --lock) lock="$2"; shift 2 ;;
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
```

Wire `lock)` / `verify)` case arms in `main`.

- [ ] **Step 4: Run tests to verify pass** — `nix develop -c bats tests/unit/40-lock.bats` → all PASS.

- [ ] **Step 5: Lint + commit**

```bash
nix develop -c treefmt && nix flake check
git add -A && git commit -m "phase1: baskets.lock generation and tamper-detecting verify"
```

---

### Task 6: Operator acceptance runbook

**Files:**
- Create: `tests/acceptance/phase1.sh`
- Create: `docs/runbooks/phase1-acceptance.md`
- Modify: `README.md` (status paragraph: Phase 1 implemented, acceptance pending)

**Interfaces:**
- Consumes: every `basket` subcommand (Tasks 2–5).
- Produces: a single interactive script the operator runs with YubiKey A inserted; it is the brief §7 Phase 1 acceptance test, verbatim, with PASS/FAIL per step and a final verdict.

- [ ] **Step 1: Write `tests/acceptance/phase1.sh`**

```bash
#!/usr/bin/env bash
# Phase 1 acceptance (brief §7): encrypt a basket, decrypt with YubiKey A,
# confirm the tmpfs mount disappears on teardown, confirm decryption fails
# with no key present. Run from the repo root with YubiKey A inserted:
#   nix develop -c tests/acceptance/phase1.sh
set -euo pipefail

work=$(mktemp -d /run/user/"$(id -u)"/basket-acceptance.XXXXXX 2>/dev/null || mktemp -d)
trap 'rm -rf "$work"' EXIT
pass=0
fail=0
step() { echo; echo "== $1"; }
ok() { echo "   PASS: $1"; pass=$((pass + 1)); }
bad() { echo "   FAIL: $1"; fail=$((fail + 1)); }

step "0. YubiKey identity"
if ! age-plugin-yubikey --identity >"$work/identity.txt" 2>/dev/null; then
  echo "No YubiKey identity found. Insert YubiKey A and re-run." >&2
  exit 1
fi
age-plugin-yubikey --list >"$work/recipients.txt"
grep -c '^age1yubikey' "$work/recipients.txt" >/dev/null || {
  echo "No YubiKey recipients listed." >&2
  exit 1
}
ok "YubiKey present, identity and recipients read"

step "1. Encrypt a basket"
mkdir -p "$work/src" "$work/store"
echo "acceptance-secret-$(date +%s)" >"$work/src/proof.txt"
cat >"$work/manifest.json" <<'EOF'
{ "id": "acceptance", "classification": "local-only", "mount": "/data/acceptance", "access": "ro" }
EOF
if basket encrypt "$work/src" --manifest "$work/manifest.json" \
  --recipients "$work/recipients.txt" --store "$work/store"; then
  ok "basket encrypted to store"
else
  bad "encrypt failed"
fi

step "2. Decrypt with YubiKey A into a real tmpfs (sudo; touch the key when it blinks)"
if sudo "$(command -v basket)" mount "$work/store/acceptance" \
  --identity "$work/identity.txt" --runtime-dir /run/baskets --size 16M &&
  sudo cat /run/baskets/acceptance/proof.txt >/dev/null &&
  [ "$(findmnt -no FSTYPE --target /run/baskets/acceptance)" = "tmpfs" ]; then
  ok "decrypted via YubiKey into tmpfs at /run/baskets/acceptance"
else
  bad "mount/decrypt via YubiKey failed"
fi

step "3. Teardown removes the tmpfs"
if sudo "$(command -v basket)" teardown acceptance --runtime-dir /run/baskets &&
  ! mountpoint -q /run/baskets/acceptance; then
  ok "tmpfs mount gone after teardown"
else
  bad "teardown left the mount behind"
fi

step "4. Decryption fails with no key present"
echo "   REMOVE the YubiKey now, then press Enter."
read -r
mkdir -p "$work/out"
if basket decrypt "$work/store/acceptance" --identity "$work/identity.txt" --into "$work/out" 2>/dev/null; then
  bad "decryption succeeded WITHOUT the key — this is a failure"
else
  ok "decryption refused with no key present"
fi

echo
echo "== Result: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]] && echo "PHASE 1 ACCEPTANCE: PASS" || {
  echo "PHASE 1 ACCEPTANCE: FAIL"
  exit 1
}
```

`chmod +x tests/acceptance/phase1.sh`.

- [ ] **Step 2: Static-verify it** — `nix develop -c shellcheck tests/acceptance/phase1.sh` → clean. (It cannot be fully run without hardware; that is the point — it is the operator's test.)

- [ ] **Step 3: Write `docs/runbooks/phase1-acceptance.md`** — operator-facing, no internals:

```markdown
# Phase 1 acceptance — what you run

One command, YubiKey A inserted, from the repo root:

    nix develop -c tests/acceptance/phase1.sh

It will: encrypt a throwaway basket → ask sudo to mount it decrypted into
tmpfs (touch the YubiKey when it blinks) → tear the mount down and prove it
is gone → ask you to unplug the key and prove decryption then fails.

Expected final line: `PHASE 1 ACCEPTANCE: PASS`.

If you see FAIL anywhere, copy the output back to Claude; nothing on your
system is left mounted or decrypted either way (everything lives in a
temp dir that is deleted on exit, and the tmpfs is torn down by the test).

Notes for later phases, no action now: tmpfs pages can reach swap; core
runs no swap today, and a swap-free (or encrypted-swap) assertion becomes
part of the basketStore NixOS module in Phase 3/4.
```

- [ ] **Step 4: Update `README.md` status paragraph** — replace the "Status: Phase 0" paragraph with:

```markdown
**Status: Phase 1 implemented (basket CLI: encrypt/decrypt/mount/teardown/
lock/verify; unit + userns mount suites green). Awaiting operator
acceptance: `nix develop -c tests/acceptance/phase1.sh` with YubiKey A.**
```

- [ ] **Step 5: Full verification + lint + commit**

```bash
nix flake check && nix develop -c tests/run-mount-tests.sh
git add -A && git commit -m "phase1: operator acceptance runbook (test: brief §7 Phase 1)"
```

---

## Verification (whole phase)

From a clean `git status`:
1. `nix flake check` → lint + unit checks green (mount tests skipped in sandbox).
2. `nix develop -c bats tests/unit` → all non-mount tests pass, mount tests skip.
3. `nix develop -c tests/run-mount-tests.sh` → mount lifecycle tests pass unprivileged.
4. `nix develop -c shellcheck tests/acceptance/phase1.sh` → clean.
5. Operator (only hardware-dependent step): `nix develop -c tests/acceptance/phase1.sh` → `PHASE 1 ACCEPTANCE: PASS`.
