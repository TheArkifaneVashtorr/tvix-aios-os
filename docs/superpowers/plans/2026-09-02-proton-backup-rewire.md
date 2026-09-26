# Off-site backup rewire — restic local + official Proton Drive CLI push (retire rclone)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Build-only: **never** `nixos-rebuild switch`, never start/stop/restart units on the host, never `sudo`.

**Goal:** a daily, verified, client-side-encrypted backup of the load-bearing state on `core` (repo, host config, encrypted basket store, orchestrator memory) that lands on the operator's Proton Drive through Proton's official CLI, with the rclone bridge (CAPTCHA-walled, Code 9001) removed.

**Architecture:** restic keeps encrypting into a **local** repository (`/var/lib/restic/core`, NixOS `services.restic.backups` module, system timer 00:00, prune + `check --read-data-subset`). A **user** unit (`proton-drive-push`, `systemd --user` for the operator, timer 00:30 + best-effort kick from the restic unit) mirrors that repository to `/my-files/backups/core` on Proton Drive with `proton-drive filesystem upload`, deletes remote objects that prune removed locally, and fails loudly unless remote snapshot count == local. The CLI keeps its login in the operator's GNOME keyring (libsecret); a user unit reaches it automatically via `$XDG_RUNTIME_DIR/bus` — verified 2026-09-02 (`env -i HOME=… XDG_RUNTIME_DIR=/run/user/1000 proton-drive filesystem list /my-files/backups --json` succeeds; without `XDG_RUNTIME_DIR` it fails with "Cannot autolaunch D-Bus without X11 $DISPLAY"). Proton only ever receives ciphertext.

**Tech Stack:** restic 0.18 (nixpkgs-host), Proton Drive CLI 0.8.0 built from tag `cli/v0.8.0` of `github.com/ProtonDriveApps/sdk` with bun 1.3.13 (flake input `nixpkgs`, reproduced from the 2026-09-02 ad-hoc build: source hash `sha256-JLyl5I3t5297LEB7ka8RUNwU0BnYy5jeLp3mywoV/YE=`, node-modules FOD hash `sha256-iRq1KepMbZpGuBC6FMl+qiwjm81ptwDcP5SmHr/39OE=`), bats (existing unit-test rung), NixOS VM test (existing integration rung), shellcheck/treefmt gate.

**Spec:** operator decision 2026-09-02 ("Proton utility suite … remote get stored via restic … back up to proton drive"; later "why can't we just use the official proton drive client?") recorded in memory + `docs/OPERATIONS.md` Lane C risk line; brief §3 invariants (no secrets in repo, prefer build-time assertions); `docs/superpowers/specs/2026-09-02-agent-environment-design.md` (restic paths note).

## Global Constraints

- All Phase 1–4b Global Constraints. Commits: `backup: <summary> (test: <check names>)` + trailers `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_0198W9P9iK9fSLcC6x45aZeX`. Commit from the devShell (`nix develop -c git commit -F <msgfile>`). `git add` before `nix build`. statix: use `_:` headers. Never `2>/dev/null` a gated command.
- Pin exactly: CLI tag `cli/v0.8.0` + the two hashes above. No secrets in the repo: the restic password stays at `/home/dalhaka/.config/restic/password` (operator has it in Proton Pass + on paper); the Proton session lives only in the operator's keyring.
- What persists where (say it in the runbook verbatim): local repo `/var/lib/restic/core` (ciphertext); remote `/my-files/backups/core` (ciphertext mirror); key = restic password (Proton Pass + paper); nothing else is needed to restore. The backup itself never contains `~/.config/restic/password`.
- Backed-up paths (operator may amend in `hosts/core/proton-backup.nix`): `/home/dalhaka/nixos-agent-env` (incl. `.git` — there is no remote), `/etc/nixos`, `/var/lib/baskets/store` (age ciphertext, world-readable files — verified), `/home/dalhaka/.claude/projects/-home-dalhaka/memory`, `/home/dalhaka/.claude/projects/-home-dalhaka-nixos-agent-env/memory`, `/home/dalhaka/.config/basket`. Excluded: `**/.pytest_cache`, `**/.ruff_cache`, `/home/*/.cache`.
- The push never calls `filesystem empty-trash` (it would empty the operator's whole Drive trash) and never touches `keys/` or `config` remotely; reconcile-deletes are confined to `index/`, `snapshots/`, `data/*/` and refuse to run when the local repo has zero snapshots or when more than half of all remote objects would go (override: `PROTON_BACKUP_FORCE_RECONCILE=1`, documented in the runbook).
- rclone is retired: package and `rcloneConfigFile` removed; operator action (runbook): `shred -u ~/.config/rclone/rclone.conf` — it holds the Proton account password.

---

### Task 1: package the official Proton Drive CLI in the flake

**Files:**
- Create: `pkgs/proton-drive-cli/default.nix`
- Modify: `flake.nix` (`packages.x86_64-linux.proton-drive-cli`, `checks.x86_64-linux.proton-drive-cli` = the package build; expose to `nixosConfigurations.core` via `specialArgs.proton-drive-cli-pkg` like `claude-code-pkg`)

**Interfaces:**
- Produces: `packages.x86_64-linux.proton-drive-cli` with `bin/proton-drive` (standalone bun executable, libsecret on rpath). Task 2's module option `services.proton-backup.cliPackage` takes it; Task 3 passes it via `specialArgs`.

- [ ] **Step 1: write the failing check** — in `flake.nix` `checks.${system}` add `proton-drive-cli = self.packages.${system}.proton-drive-cli;` and in `packages.${system}` add `proton-drive-cli = pkgs.callPackage ./pkgs/proton-drive-cli { };`. Run `nix build .#checks.x86_64-linux.proton-drive-cli -L --no-link` → expected: error "path ./pkgs/proton-drive-cli does not exist" (red).

- [ ] **Step 2: write the package** (`pkgs/proton-drive-cli/default.nix`), reproducing the proven 2026-09-02 build:

```nix
{
  lib,
  stdenv,
  stdenvNoCC,
  fetchFromGitHub,
  bun,
  libsecret,
  glib,
  makeShellWrapper,
  writableTmpDirAsHomeHook,
}:
let
  pname = "proton-drive-cli";
  version = "0.8.0";
  sdkVersion = "0.21.0";
  commit = "5491f2e"; # short sha of tag cli/v0.8.0 in the SDK repo (embedded in --version output)

  src = fetchFromGitHub {
    owner = "ProtonDriveApps";
    repo = "sdk";
    tag = "cli/v${version}";
    hash = "sha256-JLyl5I3t5297LEB7ka8RUNwU0BnYy5jeLp3mywoV/YE=";
  };

  # Fixed-output: bun's lockfile-driven installs for the three workspaces the
  # CLI bundles (cli, client/js, incubating/account/js). Hash proven on the
  # 2026-09-02 ad-hoc build of the same tag.
  nodeModules = stdenvNoCC.mkDerivation {
    pname = "${pname}-node-modules";
    inherit version src;
    nativeBuildInputs = [
      bun
      writableTmpDirAsHomeHook
    ];
    dontConfigure = true;
    buildPhase = ''
      runHook preBuild
      export BUN_INSTALL_CACHE_DIR=$(mktemp -d) # keeps the outputHash stable
      cd cli
      bun install --frozen-lockfile --ignore-scripts --no-progress --production
      cd ../client/js
      bun install --frozen-lockfile --ignore-scripts --no-progress --production
      cd ../../incubating/account/js
      bun install --frozen-lockfile --ignore-scripts --no-progress --production
      cd ../../../
      runHook postBuild
    '';
    installPhase = ''
      runHook preInstall
      mkdir -p $out/cli $out/client/js $out/incubating/account/js
      cp -R cli/node_modules $out/cli/
      cp -R client/js/node_modules $out/client/js/
      cp -R incubating/account/js/node_modules $out/incubating/account/js/
      runHook postInstall
    '';
    dontFixup = true;
    outputHashMode = "recursive";
    outputHash = "sha256-iRq1KepMbZpGuBC6FMl+qiwjm81ptwDcP5SmHr/39OE=";
  };
in
stdenv.mkDerivation {
  inherit pname version src;

  nativeBuildInputs = [
    bun
    makeShellWrapper
  ];
  # libsecret + glib are dlopen'd at runtime by the compiled CLI for the
  # OS keychain (PROTON_DRIVE_CREDENTIALS_STORE=keychain, the default).
  buildInputs = [
    libsecret
    glib
  ];

  configurePhase = ''
    runHook preConfigure
    cp -R ${nodeModules}/cli/node_modules cli/
    cp -R ${nodeModules}/client/js/node_modules client/js/
    cp -R ${nodeModules}/incubating/account/js/node_modules incubating/account/js
    runHook postConfigure
  '';

  # Same invocation as cli/scripts/build-cli.mjs at this tag, with the
  # version strings pinned (the script derives them from git, unavailable
  # in the sandbox). APP_VERSION name "external-drive-sdkclijs" is the
  # identifier the README assigns to self-built CLIs.
  buildPhase = ''
    runHook preBuild
    cd cli
    bun build \
      --compile \
      --bytecode \
      --target=bun \
      --format=esm \
      --minify \
      --sourcemap=inline \
      --define "APP_VERSION=\"external-drive-sdkclijs@${version}+${commit}\"" \
      --define "SDK_VERSION=\"js@${sdkVersion}+${commit}\"" \
      --define SENTRY_DSN=undefined \
      src/proton-drive.ts \
      --outfile=release/proton-drive
    cd ..
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    install -Dm755 cli/release/proton-drive $out/bin/proton-drive
    wrapProgram $out/bin/proton-drive \
      --prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [ libsecret glib ]}
    runHook postInstall
  '';

  meta = {
    description = "Official Proton Drive command-line client (built from the SDK repository)";
    homepage = "https://proton.me/support/drive-cli";
    license = lib.licenses.mit;
    platforms = [ "x86_64-linux" ];
    mainProgram = "proton-drive";
  };
}
```

  Implementer notes: (a) if `fetchFromGitHub` at the `nixpkgs` pin lacks the `tag` argument, use `rev = "cli/v${version}"`. (b) If `wrapProgram` is unavailable because the compiled binary already links libsecret via autoPatchelf, keep the wrapper anyway (harmless) — the 2026-09-02 build had libsecret+glib in `buildInputs` and used `makeShellWrapper`. (c) The README says Bun ≥ 1.3.14 for dev builds; 1.3.13 (nixpkgs pin) produced a working binary on 2026-09-02 — keep it, note the drift in a comment.

- [ ] **Step 3: build** — `nix build .#checks.x86_64-linux.proton-drive-cli -L --no-link` → green. Then `nix build .#proton-drive-cli -o $SCRATCH/pdc && $SCRATCH/pdc/bin/proton-drive filesystem upload --help | grep -q 'file-conflict-strategy'` (no network needed for `--help` of a subcommand).
- [ ] **Step 4: wire specialArgs** — `nixosConfigurations.core`: `specialArgs.proton-drive-cli-pkg = self.packages.x86_64-linux.proton-drive-cli;` (consumed in Task 3).
- [ ] **Step 5: lint gate → commit** `backup: package the official Proton Drive CLI 0.8.0 from the SDK tag (test: proton-drive-cli)`.

### Task 2: `protonBackup.nix` module — restic local repo + user push unit, with unit tests

**Files:**
- Create: `nixosModules/protonBackup.nix`, `pkgs/proton-backup/push.sh`, `tests/mocks/proton-drive-mock.sh` (one fake CLI shared by the bats tests and the VM test), `tests/unit/60-proton-push.bats`, `tests/integration/proton-backup-vm.nix`
- Modify: `flake.nix` (export module; `checks.proton-backup-eval`, `checks.proton-backup-vm`; add `pkgs/proton-backup/push.sh` to the shellcheck list in `checks.lint` and `githooks/pre-commit`; make `push.sh` available to bats via a `writeShellApplication` named `proton-backup-push` in the `unit` check's `nativeBuildInputs` and the devShell)

**Interfaces:**
- Produces module options:
  - `services.proton-backup.enable` (bool)
  - `services.proton-backup.user` (str, default `"dalhaka"`) — owner of the keyring holding the CLI login; runs both the restic job and the push
  - `services.proton-backup.repositoryPath` (str, default `"/var/lib/restic/core"`)
  - `services.proton-backup.paths` (listOf str), `services.proton-backup.exclude` (listOf str, default `[ "**/.pytest_cache" "**/.ruff_cache" "/home/*/.cache" ]`)
  - `services.proton-backup.passwordFile` (str, default `"/home/dalhaka/.config/restic/password"`)
  - `services.proton-backup.remoteParent` (str, default `"/my-files/backups"`)
  - `services.proton-backup.backupOnCalendar` (str, default `"daily"`), `services.proton-backup.pushOnCalendar` (str, default `"*-*-* 00:30:00"`)
  - `services.proton-backup.cliPackage` (package, no default — Task 3 passes `proton-drive-cli-pkg`)
- Produces: system unit `restic-backups-core-local.service/.timer` (module-generated), user unit `proton-drive-push.service/.timer` (ConditionUser = `cfg.user`), tmpfiles `d /var/lib/restic 0755 root root -` and `d ${repositoryPath} 0700 ${user} users -`, `environment.systemPackages = [ restic cliPackage ]`.
- Push script contract (`pkgs/proton-backup/push.sh`, installed as `proton-backup-push`): env `PROTON_BACKUP_REPO` (local repo), `PROTON_BACKUP_REMOTE_PARENT`, `PROTON_DRIVE_CLI` (binary, default `proton-drive`), `PROTON_BACKUP_LOCK_WAIT_SECONDS` (default 1800), `PROTON_BACKUP_FORCE_RECONCILE` (default unset). Exit 0 with a final line `proton-backup-push: OK snapshots=<n> remote=<n>`; exit 1 on parity mismatch or refused reconcile; exit 0 with `another push is running` if the flock is held.

- [ ] **Step 1a: the shared fake CLI** `tests/mocks/proton-drive-mock.sh` (shellcheck-clean; add to both shellcheck lists). It logs every invocation to `$MOCK_CALLS` and serves a fake remote tree rooted at `$MOCK_REMOTE_ROOT` (folder per remote folder, file per remote file). It implements exactly the CLI surface the push script uses and rejects anything else with exit 99. `MOCK_UPLOAD_NOOP=1` makes uploads do nothing (used to simulate a remote that silently lost data).

```bash
#!/usr/bin/env bash
# Fake `proton-drive` for tests: serves a remote tree from $MOCK_REMOTE_ROOT,
# logs calls to $MOCK_CALLS. Only the subcommands proton-backup-push uses.
set -euo pipefail
root="${MOCK_REMOTE_ROOT:?}"
echo "$*" >>"${MOCK_CALLS:?}"
cmd="$1 $2"
shift 2
case "$cmd" in
  "filesystem info")
    # <path> --json
    [ -e "$root$1" ] || exit 1
    echo '{"type":"folder"}'
    ;;
  "filesystem create-folder")
    # <parent> <name>
    mkdir -p "$root$1/$2"
    ;;
  "filesystem upload")
    # -t -f skip -d merge <local...> <remoteParent>
    shift 5
    args=("$@")
    dest="${args[-1]}"
    unset 'args[-1]'
    [ "${MOCK_UPLOAD_NOOP:-0}" = "1" ] && exit 0
    for src in "${args[@]}"; do
      if [ -d "$src" ]; then
        mkdir -p "$root$dest/$(basename "$src")"
        while IFS= read -r f; do
          t="$root$dest/$(basename "$src")/$f"
          [ -e "$t" ] || { mkdir -p "$(dirname "$t")"; cp "$src/$f" "$t"; }
        done < <(cd "$src" && find . -type f | sed 's|^\./||')
      else
        t="$root$dest/$(basename "$src")"
        [ -e "$t" ] || cp "$src" "$t"
      fi
    done
    ;;
  "filesystem list")
    # -t file <path> --json
    dir="$root$3"
    printf '['
    sep=''
    for f in "$dir"/*; do
      [ -f "$f" ] || continue
      printf '%s{"name":{"ok":true,"value":"%s"}}' "$sep" "$(basename "$f")"
      sep=','
    done
    printf ']\n'
    ;;
  "filesystem delete")
    for p in "$@"; do rm -f "$root$p"; done
    ;;
  *)
    echo "mock: unsupported $cmd" >&2
    exit 99
    ;;
esac
```

- [ ] **Step 1b: failing bats tests** — `tests/unit/60-proton-push.bats`. The local repo fixture is a fake restic layout: `config`, `keys/k1`, `index/i1`, `snapshots/s1 s2`, `data/00/p1`, `data/ab/p2`, empty `locks/`.

```bash
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
  # deletes are batched into one CLI call; assert the path was in it
  grep '^filesystem delete ' calls.log | grep -q '/my-files/backups/repo/data/00/p1'
  ! grep '^filesystem delete ' calls.log | grep -q '/my-files/backups/repo/keys'
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
```

- [ ] **Step 2: run bats to see them fail** — `nix develop -c bats tests/unit/60-proton-push.bats` → all fail with `proton-backup-push: command not found` (the devShell/unit check must gain the `proton-backup-push` writeShellApplication in Step 3). The `unit` check copies `${self}/tests` wholesale, so `tests/mocks/proton-drive-mock.sh` is reachable from the bats file as `$BATS_TEST_DIRNAME/../mocks/proton-drive-mock.sh`; mark it executable in git (`chmod +x` before `git add`).

- [ ] **Step 3: write `pkgs/proton-backup/push.sh`** (shellcheck-clean; runtimeInputs for the writeShellApplication: `coreutils findutils jq util-linux`):

```bash
#!/usr/bin/env bash
# proton-backup-push: mirror a local restic repository to Proton Drive with
# the official Proton Drive CLI. Local is the source of truth; the remote is a
# byte-for-byte mirror of the repository's object store minus locks/.
# Safety rails: never empty-trash, never touch keys/ or config remotely,
# refuse to reconcile with zero local snapshots or when more than half of
# all remote objects would be deleted; verify snapshot parity at the end.
set -euo pipefail

repo="${PROTON_BACKUP_REPO:?PROTON_BACKUP_REPO (local restic repository) is required}"
remote_parent="${PROTON_BACKUP_REMOTE_PARENT:-/my-files/backups}"
cli="${PROTON_DRIVE_CLI:-proton-drive}"
lock_wait="${PROTON_BACKUP_LOCK_WAIT_SECONDS:-1800}"
name="$(basename "$repo")"
remote="$remote_parent/$name"

exec 9>"${XDG_RUNTIME_DIR:-/tmp}/proton-backup-push.lock"
if ! flock -n 9; then
  echo "proton-backup-push: another push is running"
  exit 0
fi

# A restic job in flight leaves lock files; wait for it, then give up loudly.
waited=0
while [ -n "$(ls -A "$repo/locks" 2>/dev/null)" ]; do
  if [ "$waited" -ge "$lock_wait" ]; then
    echo "proton-backup-push: restic lock still present after ${lock_wait}s; not pushing a repository mid-write" >&2
    exit 1
  fi
  sleep 2
  waited=$((waited + 2))
done

local_snapshots=$(find "$repo/snapshots" -maxdepth 1 -type f | wc -l)
if [ "$local_snapshots" -lt 1 ]; then
  echo "proton-backup-push: refusing to push a repository with zero snapshots (is it initialized?)" >&2
  exit 1
fi

if ! "$cli" filesystem info "$remote" --json >/dev/null 2>&1; then
  "$cli" filesystem create-folder "$remote_parent" "$name"
fi

# Upload the object store (locks/ deliberately absent). The CLI skips
# identical content itself; -f skip handles same-name/different-content,
# which content-addressed restic names never produce except for config.
uploads=("$repo/config" "$repo/keys" "$repo/index" "$repo/snapshots" "$repo/data")
"$cli" filesystem upload -t -f skip -d merge "${uploads[@]}" "$remote"

remote_names() { # <subdir> -> names of remote files in it
  "$cli" filesystem list -t file "$remote/$1" --json | jq -r '.[].name.value'
}

stale=()
remote_total=0
collect_stale() { # <subdir>: remember remote files that prune removed locally
  local sub="$1" names
  names=$(remote_names "$sub") || return 0
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    remote_total=$((remote_total + 1))
    [ -e "$repo/$sub/$f" ] || stale+=("$remote/$sub/$f")
  done <<<"$names"
}

collect_stale index
collect_stale snapshots
for d in "$repo"/data/*/; do
  [ -d "$d" ] || continue
  collect_stale "data/$(basename "$d")"
done
if [ "${#stale[@]}" -gt 0 ]; then
  # A legitimate prune removes a fraction of the object store. Deleting more
  # than half of everything remote is far likelier to mean the local
  # repository is damaged than that prune was busy -- refuse, and make the
  # override explicit.
  if [ $((${#stale[@]} * 2)) -gt "$remote_total" ] && [ "${PROTON_BACKUP_FORCE_RECONCILE:-0}" != "1" ]; then
    echo "proton-backup-push: refusing to delete ${#stale[@]} of $remote_total remote objects (more than half; verify the local repository, then set PROTON_BACKUP_FORCE_RECONCILE=1)" >&2
    exit 1
  fi
  "$cli" filesystem delete "${stale[@]}"
fi

remote_snapshots=$(remote_names snapshots | grep -c . || true)
if [ "$remote_snapshots" -ne "$local_snapshots" ]; then
  echo "proton-backup-push: parity FAIL snapshots local=$local_snapshots remote=$remote_snapshots" >&2
  exit 1
fi
echo "proton-backup-push: OK snapshots=$local_snapshots remote=$remote_snapshots"
```

  Wrap it in `flake.nix` like `basket`: `protonBackupPush = pkgs.writeShellApplication { name = "proton-backup-push"; runtimeInputs = with pkgs; [ coreutils findutils jq util-linux ]; text = builtins.readFile ./pkgs/proton-backup/push.sh; };` and expose as `packages.${system}.proton-backup-push`; add it to the `unit` check's `nativeBuildInputs` and the devShell; add `pkgs/proton-backup/push.sh` to both shellcheck lists.

- [ ] **Step 4: bats green** — `nix develop -c bats tests/unit/60-proton-push.bats`, then `nix build .#checks.x86_64-linux.unit -L --no-link`.

- [ ] **Step 5: the module** `nixosModules/protonBackup.nix`:

```nix
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.proton-backup;
  pushScript = pkgs.writeShellApplication {
    name = "proton-backup-push";
    runtimeInputs = with pkgs; [
      coreutils
      findutils
      jq
      util-linux
    ];
    text = builtins.readFile ../pkgs/proton-backup/push.sh;
  };
  userUid = toString config.users.users.${cfg.user}.uid;
in
{
  options.services.proton-backup = {
    enable = lib.mkEnableOption "daily restic backup to a local repository, mirrored to Proton Drive by the official CLI";
    user = lib.mkOption {
      type = lib.types.str;
      default = "dalhaka";
      description = "Runs the restic job and the push; owns the keyring that holds the Proton Drive CLI login.";
    };
    repositoryPath = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/restic/core";
    };
    paths = lib.mkOption { type = lib.types.listOf lib.types.str; };
    exclude = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [
        "**/.pytest_cache"
        "**/.ruff_cache"
        "/home/*/.cache"
      ];
    };
    passwordFile = lib.mkOption {
      type = lib.types.str;
      default = "/home/dalhaka/.config/restic/password";
    };
    remoteParent = lib.mkOption {
      type = lib.types.str;
      default = "/my-files/backups";
    };
    backupOnCalendar = lib.mkOption {
      type = lib.types.str;
      default = "daily";
    };
    pushOnCalendar = lib.mkOption {
      type = lib.types.str;
      default = "*-*-* 00:30:00";
    };
    cliPackage = lib.mkOption {
      type = lib.types.package;
      description = "The proton-drive-cli package (built from the SDK tag by this flake).";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = config.users.users ? ${cfg.user} && config.users.users.${cfg.user}.uid != null;
        message = "services.proton-backup.user '${cfg.user}' must be a declared user with a fixed uid (the push unit needs /run/user/<uid>)";
      }
    ];

    environment.systemPackages = [
      pkgs.restic
      cfg.cliPackage
      pushScript
    ];

    systemd.tmpfiles.rules = [
      "d /var/lib/restic 0755 root root -"
      "d ${cfg.repositoryPath} 0700 ${cfg.user} users -"
    ];

    # restic keeps encrypting locally exactly as before; only the transport
    # changed (rclone -> official CLI, see docs/runbooks/backup.md).
    services.restic.backups.core-local = {
      inherit (cfg) user paths exclude passwordFile;
      repository = cfg.repositoryPath;
      initialize = true;
      timerConfig = {
        OnCalendar = cfg.backupOnCalendar;
        Persistent = true;
      };
      pruneOpts = [
        "--keep-daily 7"
        "--keep-weekly 4"
        "--keep-monthly 6"
      ];
      checkOpts = [ "--read-data-subset=10%" ];
      # Best-effort immediate push after a successful backup: the push is a
      # user unit (it needs the operator's keyring); reach that user manager
      # through its runtime dir. If the operator is logged out, the push
      # timer at pushOnCalendar catches up. $SERVICE_RESULT is set by
      # systemd for ExecStopPost, where the module runs this command.
      backupCleanupCommand = ''
        if [ "''${SERVICE_RESULT:-}" = "success" ]; then
          XDG_RUNTIME_DIR=/run/user/${userUid} ${pkgs.systemd}/bin/systemctl --user start --no-block proton-drive-push.service \
            || echo "proton-backup: no user session to kick the push; the push timer will catch up"
        fi
      '';
    };

    systemd.user = {
      services.proton-drive-push = {
        description = "Mirror the local restic repository to Proton Drive (official CLI)";
        unitConfig.ConditionUser = cfg.user;
        environment = {
          PROTON_BACKUP_REPO = cfg.repositoryPath;
          PROTON_BACKUP_REMOTE_PARENT = cfg.remoteParent;
          PROTON_DRIVE_CLI = "${cfg.cliPackage}/bin/proton-drive";
          PROTON_DRIVE_LOG_LEVEL = "INFO";
        };
        serviceConfig = {
          Type = "oneshot";
          ExecStart = "${pushScript}/bin/proton-backup-push";
        };
      };
      timers.proton-drive-push = {
        description = "Daily Proton Drive push of the local restic repository";
        unitConfig.ConditionUser = cfg.user;
        wantedBy = [ "timers.target" ];
        timerConfig = {
          OnCalendar = cfg.pushOnCalendar;
          Persistent = true;
        };
      };
    };
  };
}
```

  Implementer notes: `users.users.dalhaka.uid` is not fixed in `hosts/core/default.nix` today (it's 1000 on the live host, `id` verified); Task 3 sets `users.users.dalhaka.uid = 1000;` explicitly so the assertion holds and `/run/user/1000` is deterministic. `systemd.user.timers` with `wantedBy = [ "timers.target" ]` is the NixOS idiom for user timers.

- [ ] **Step 6: eval check** — `checks.proton-backup-eval`: a `nixosSystem` with the module + a `users.users.tester = { isNormalUser = true; uid = 1000; }` + `services.proton-backup = { enable = true; user = "tester"; paths = [ "/etc" ]; cliPackage = pkgs.writeShellScriptBin "proton-drive" "true"; }`; runCommand greps the rendered units: `restic-backups-core-local.service` contains `RESTIC_REPOSITORY=/var/lib/restic/core`, `User=tester`, `--read-data-subset=10%`, does NOT contain `RCLONE`; user unit `proton-drive-push.service` contains `ConditionUser=tester` and `PROTON_BACKUP_REPO=/var/lib/restic/core`; user timer contains `OnCalendar=*-*-* 00:30:00`. Red first (module file absent) → green.

- [ ] **Step 7: VM test** `tests/integration/proton-backup-vm.nix` (wired as `checks.proton-backup-vm` via `pkgs.testers.runNixOSTest`, module passed in like `broker-vm.nix`): node with user `alice` (uid 1000, isNormalUser), a password file at `/etc/restic-password` (content `vm-test`, mode 0644 — a test VM, not a secret), `services.proton-backup = { enable = true; user = "alice"; passwordFile = "/etc/restic-password"; paths = [ "/etc/hostname" "/var/lib/sample" ]; cliPackage = mockCli; }` where `mockCli = pkgs.writeShellScriptBin "proton-drive" (builtins.readFile ../mocks/proton-drive-mock.sh);` — the same file the bats tests use — with `systemd.user.services.proton-drive-push.environment = { MOCK_REMOTE_ROOT = "/var/lib/mock-remote"; MOCK_CALLS = "/var/lib/mock-remote/calls.log"; }` added in the test node and `systemd.tmpfiles.rules = [ "d /var/lib/mock-remote 0777 root root -" ]` so alice can write there. Test script:

```python
machine.wait_for_unit("multi-user.target")
machine.succeed("mkdir -p /var/lib/sample && echo hello > /var/lib/sample/f.txt")
machine.succeed("loginctl enable-linger alice")
machine.wait_until_succeeds("systemctl --user -M alice@ is-active timers.target")
# 1. the restic job initializes and backs up into the local repository as alice
machine.succeed("systemctl start restic-backups-core-local.service")
machine.succeed("test -f /var/lib/restic/core/config")
machine.succeed("su alice -c 'RESTIC_PASSWORD_FILE=/etc/restic-password restic -r /var/lib/restic/core snapshots --json | jq -e \"length == 1\"'")
# 2. the cleanup kick reached alice's user manager and the push ran with the mock CLI
machine.wait_until_succeeds("grep -q 'filesystem upload' /var/lib/mock-remote/calls.log")
machine.succeed("test -f /var/lib/mock-remote/my-files/backups/core/config")
machine.succeed("test $(ls /var/lib/mock-remote/my-files/backups/core/snapshots | wc -l) -eq 1")
machine.fail("test -e /var/lib/mock-remote/my-files/backups/core/locks")
# 3. the push unit itself reports parity OK (user-unit journal entries carry
#    _SYSTEMD_USER_UNIT and are readable by root from the system journal)
machine.succeed("journalctl _SYSTEMD_USER_UNIT=proton-drive-push.service | grep -q 'proton-backup-push: OK snapshots=1 remote=1'")
# 4. restore drill from the local repository
machine.succeed("su alice -c 'RESTIC_PASSWORD_FILE=/etc/restic-password restic -r /var/lib/restic/core restore latest --target /tmp/restore'")
machine.succeed("grep -q hello /tmp/restore/var/lib/sample/f.txt")
# 5. rclone is gone from the closure of this configuration
machine.fail("command -v rclone")
```

  If the ExecStopPost kick cannot reach the user manager in the VM (no `/run/user/1000` before linger), start the push explicitly with `systemctl --user -M alice@ start proton-drive-push.service` and ALSO assert the kick's fallback message appeared in the system journal — record which path the VM exercised in the commit body. Every path in `services.proton-backup.paths` must exist: restic exits 3 ("some files could not be read") for a missing path and the unit then fails — the runbook says so, and Task 3's list was checked against the live host on 2026-09-02 (all six exist; the second memory directory is empty but present).

- [ ] **Step 8: run** `proton-backup-eval`, `proton-backup-vm`, `unit`, `lint`. Lint gate → commit `backup: protonBackup module — restic local repo + Proton Drive CLI mirror with safety rails (test: unit, proton-backup-eval, proton-backup-vm)`.

### Task 3: wire `core`, retire rclone

**Files:**
- Modify: `hosts/core/proton-backup.nix` (replace the `services.restic.backups.proton-drive` block; drop `rclone` from packages; keep `protonmail-desktop`, `proton-pass`, `protonmail-bridge`), `hosts/core/default.nix` (`users.users.dalhaka.uid = 1000;`), `flake.nix` (`nixosConfigurations.core.modules` gains `self.nixosModules.protonBackup`; `specialArgs.proton-drive-cli-pkg` from Task 1)

- [ ] **Step 1: red** — `checks.managed-settings-user-scope` style assertion in a new `checks.core-backup-wiring`: `self.nixosConfigurations.core.config.services.proton-backup.enable == true`, `services.restic.backups ? core-local`, `!(services.restic.backups ? proton-drive)`, and `!(builtins.elem pkgs.rclone config.environment.systemPackages)` (evaluate with `nixpkgs-host` pkgs to compare the same derivation, or grep the systemPackages names for `rclone-`). Run → red.
- [ ] **Step 2: green** — `hosts/core/proton-backup.nix`:

```nix
{ pkgs, proton-drive-cli-pkg, ... }:

{
  environment.systemPackages = with pkgs; [
    # Proton suite (official apps). rclone retired 2026-09-02: Proton's
    # anti-abuse wall blocks the unofficial bridge (Code 9001); the official
    # CLI (services.proton-backup.cliPackage) is the sanctioned transport.
    protonmail-desktop
    proton-pass
    protonmail-bridge
  ];

  # Daily client-side-encrypted backup: restic -> /var/lib/restic/core, then
  # the official Proton Drive CLI mirrors the ciphertext to
  # /my-files/backups/core (nixosModules/protonBackup.nix; runbook:
  # docs/runbooks/backup.md). What persists where: local repo + remote
  # mirror are ciphertext; the only key is ~/.config/restic/password (Proton
  # Pass + paper); the backup never contains that file.
  services.proton-backup = {
    enable = true;
    user = "dalhaka";
    cliPackage = proton-drive-cli-pkg;
    paths = [
      "/home/dalhaka/nixos-agent-env"
      "/etc/nixos"
      "/var/lib/baskets/store"
      "/home/dalhaka/.claude/projects/-home-dalhaka/memory"
      "/home/dalhaka/.claude/projects/-home-dalhaka-nixos-agent-env/memory"
      "/home/dalhaka/.config/basket"
    ];
  };
}
```

- [ ] **Step 3:** `nix build .#checks.x86_64-linux.core-backup-wiring -L --no-link`, `nix build .#checks.x86_64-linux.host-core -L --no-link`, then `nix build .#nixosConfigurations.core.config.system.build.toplevel -o $SCRATCH/result-core && nix store diff-closures /run/current-system $SCRATCH/result-core` — expect: `restic-backups-proton-drive` units gone, `restic-backups-core-local` + user `proton-drive-push` units added, `proton-drive-cli` added, `rclone` removed, nothing else surprising.
- [ ] **Step 4:** lint gate → commit `backup: core uses protonBackup (local repo + CLI mirror); rclone retired (test: core-backup-wiring, host-core)`.

### Task 4: runbook, acceptance drill, board, concept

**Files:**
- Create: `docs/runbooks/backup.md`, `tests/acceptance/backup.sh`, `docs/concepts/2026-09-02j-backup-parity-self-test.md`
- Modify: `docs/OPERATIONS.md`, `README.md`

- [ ] **Step 1: runbook** `docs/runbooks/backup.md`, plain language, sections: *What is backed up and where it lands* (the persistence matrix from Global Constraints, verbatim); *One-time setup after the switch*: (1) `proton-drive auth login` once in the desktop session — browser sign-in, session saved in GNOME Keyring; (2) `shred -u ~/.config/rclone/rclone.conf` — it contains the Proton account password; (3) confirm the restic password is in Proton Pass and on paper; *Daily rhythm* (00:00 backup+prune+check, 00:30 push; the push also runs right after a successful backup while you are logged in; if you're logged out the push waits for your next login); *Check it worked*: `systemctl status restic-backups-core-local`, `systemctl --user status proton-drive-push`, `proton-drive filesystem list /my-files/backups/core/snapshots`; *Restore*: from local (`restic -r /var/lib/restic/core restore latest --target /tmp/restore`) and from Proton on a fresh machine (`proton-drive filesystem download /my-files/backups/core /tmp && restic -r /tmp/core snapshots`), password from Proton Pass/paper; *Known limits*: push needs an unlocked login keyring (logged-in desktop); Proton's trash is never emptied by us; the first push uploads the whole repository (small: tens of MB today).
- [ ] **Step 2: acceptance** `tests/acceptance/backup.sh` (operator-run, sudo for the system unit, PASS/FAIL accounting like `phase4b.sh`): (1) `sudo systemctl start restic-backups-core-local.service` and wait for it to finish; PASS if `restic -r /var/lib/restic/core snapshots --json` (RESTIC_PASSWORD_FILE from the password file) shows ≥ 1 snapshot; (2) `systemctl --user start proton-drive-push.service`; PASS if the user journal shows `proton-backup-push: OK`; (3) remote parity: `proton-drive filesystem list -t file /my-files/backups/core/snapshots --json | jq length` equals the local count; (4) restore drill: restore `/home/dalhaka/nixos-agent-env/README.md` from `latest` into a temp dir and `cmp` it with the live file; (5) `! command -v rclone` and `! test -e ~/.config/rclone/rclone.conf` (WARN, not FAIL, if the config still exists — with the shred instruction). Final line `BACKUP ACCEPTANCE: PASS|FAIL`. shellcheck-clean.
- [ ] **Step 3: board + README** — OPERATIONS.md: new Lane F "Off-site backup (built, gate pending)" with the four tasks checked and the operator gate line (`sudo nixos-rebuild switch …` then `proton-drive auth login` once, then `nix develop -c tests/acceptance/backup.sh`); Lane C: strike the "zero off-machine backup" risk once the acceptance passes (leave it until then), add the rclone.conf shred action; README status sentence.
- [ ] **Step 4: concept** `docs/concepts/2026-09-02j-backup-parity-self-test.md` in the house style (Class / Status / Origin / Idea / Payoffs / Dependencies / Earliest landing): a nightly self-test unit that emits one line — basket doctor verdict, latest restic snapshot age, remote parity (snapshot count local vs Proton), `nix flake check` result — into the journal and a Helm dashboard tile; "if you cannot measure it, it isn't real" as a standing habit; depends on this plan + Helm.
- [ ] **Step 5:** lint gate (shellcheck on the acceptance script) → commit `backup: runbook, acceptance drill, board lane F, concept: backup parity self-test (test: lint)`.

## Verification (whole change)

1. `nix flake check -L` green (new: `proton-drive-cli`, `unit` with the push bats, `proton-backup-eval`, `proton-backup-vm`, `core-backup-wiring`).
2. Closure diff of `nixosConfigurations.core` vs `/run/current-system` as in Task 3 Step 3, pasted into the final commit body.
3. Operator gate (NOT the factory): switch → `proton-drive auth login` once (browser) → `nix develop -c tests/acceptance/backup.sh` → on PASS, strike the Lane C risk and `shred -u ~/.config/rclone/rclone.conf`.

## Decisions taken (flag to the operator, change if disagreed)

- Backup paths include the encrypted basket store and the orchestrator memory directories; the restic password file is excluded by construction.
- The push is a **user** unit (needs your login keyring). If you would rather have it run without a logged-in desktop, the CLI supports `PROTON_DRIVE_CREDENTIALS_STORE=pass` (gpg-backed store) — a later change, weaker at rest.
- Remote reconcile permanently removes restic objects that prune removed, so the remote mirror does not grow forever, guarded by the >50% and zero-snapshot refusals. **Correction 2026-09-02 (review):** the CLI's `filesystem delete` only accepts already-trashed items (`/trash/<name>`; `filesystem delete /my-files/...` exits 1 — verified against the built `proton-drive-cli` 0.8.0's `--help` and its SDK source, `cli/src/commands/fileSystem/commandFileSystemDelete.ts`), so the push does `filesystem trash <stale my-files paths>` followed by `filesystem delete /trash/<basename>` per object; the operator's Drive trash still ends up empty of these objects (we delete what we trash), we just never call `empty-trash` on trash the operator put there themselves.
