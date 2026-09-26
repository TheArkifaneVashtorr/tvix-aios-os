# The seat behind a broker — implementation plan (DeepSeek V4 Pro, effort high)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) and `tools/factory/dark-factory.js` both read the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and `commit subject`.

> **Provenance:** this plan is one arm of the 2026-09-05 plan-writing comparison — written blind by DeepSeek V4 Pro (effort high) from the spec below, with no access to the orchestrator's own plan. It is a record, not executed here. Every fact about the tree cited below (option names, line numbers, check names, address blocks) came from the commands listed alongside the fact in the task's FACTORY-NOTES.

**Goal:** put the operator's DeepSeek seat behind the same egress broker the lanes use — one `seat` broker instance on 10.100.4.x that injects the real OpenRouter key from `/var/lib/secrets/openrouter-key`, a `seat@<job>` system unit that runs the harness as the operator inside that namespace with only a placeholder key in its environment, a `seat-submit` job spool and a `--broker` mode on the wrapper, a web path that reaches the operator's browser through the namespace, and the migration that deletes the operator's plaintext `~/.config/openrouter/key`.

**Architecture:** a new NixOS module `nixosModules/seatLane.nix` declares `services.egress-broker.instances.seat` (allowlist `openrouter.ai`, credential injection from the key file, the lane's ZDR + training-opt-out body patch, `/api/v1/messages` denied) and a `seat@.service` template (`User = dalhaka`, `NetworkNamespacePath = /run/netns/egress-seat`, proxy/CA/placeholder-key environment, `ProtectSystem=strict` with an explicit operator `ReadWritePaths`). Two stdlib Python scripts, `seat-submit.py` (write the job directory, start the unit, wait and relay the result) and `seat-run.py` (the unit's entry: run `dsh-openrouter --broker`), back binaries the module builds exactly the way `modelLane.nix` builds `lane-submit`/`lane-wait`. The wrapper gains `--broker` (skip the key file, keep the placeholder, verify the default route is the broker's veth gateway) and `--bind-namespace` (web UI, `--broker` only); `factory-task` and `factory-review` switch their launch line to `seat-submit`.

**Tech Stack:** NixOS modules (mirroring `nixosModules/modelLane.nix` and `nixosModules/egressBroker.nix`), Python 3 stdlib only under `pkgs/seat/`, bash (the `dsh-openrouter.sh` wrapper, `writeShellApplication`), a NixOS VM test (`tests/integration/seat-vm.nix`), bats (`tests/unit/72-seat-broker.bats`, `tests/unit/82-seat-factory.bats`), pytest (`tests/seat/`), nftables + polkit, treefmt/ruff/shellcheck/statix/deadnix.

**Spec:** `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md` (approved in approach, 2026-09-05 evening). The plan argues from the spec, so the spec travels with it; an executor reads both.

## Global Constraints

- **Build-only.** Never `sudo`, `nixos-rebuild`, `systemctl start/stop/restart`, or basket mount/teardown — the operator switches and runs the acceptance steps (SB6's migration is the operator's runbook, separated below from the factory's build work). Never read or copy `/var/lib/secrets/*`, `~/.config/openrouter/key`, or `~/.config/restic/password` into the repo or the store.
- Commits go through the devShell only (`nix develop -c git commit -F <msgfile>`); `git add` new files **before** any `nix build` (flakes see only tracked files); never `2>/dev/null` a gated command; never `--no-verify`.
- Every check named in a task's acceptance runs as `nix build .#checks.x86_64-linux.<name> -L --no-link`; the full lint gate is `nix develop -c githooks/pre-commit`.
- TDD: the failing check first, shown red, then green. A load-bearing test counts only once it has been shown to fail.
- One writer per tree — `touches` is a contract; a file outside it is a deviation to report, not to write. `nixosModules/egressBroker.nix` (the `inbound` option) and `flake.nix` (the `checks` attrset, `host-core`, the `lint` ruff lists) are shared: the wave table below serialises every editor.
- No secrets in the repo; the unit's `OPENROUTER_API_KEY=injected-by-broker` is a placeholder the broker overwrites — never a real key. `keyFile` stays out of the store (asserted; the negative check proves a real key in the unit's environment fails the build).
- Nix style: statix rejects `{ ... }:` module headers (write `_:` or name args); `hosts/core/hardware-configuration.nix` is exempt from formatting.
- Python under `pkgs/seat/` is stdlib-only (mirrors `pkgs/lane/`); `nix develop -c ruff check pkgs/seat tests/seat` and `ruff format --check` must stay clean.
- The wrapper (`pkgs/dsh-openrouter/dsh-openrouter.sh`) is only changed by SB2; every other task consumes `--broker`/`--bind-namespace` by the exact spellings in SB2's Interfaces block.

## Waves

| wave | groups (seat driver) | dependsOn | starts / file-conflict calls |
|---|---|---|---|
| 1 | `"SB2"` `"SB3"` | SB2: none; SB3: none | now — SB2 (pkgs/dsh-openrouter/*, new bats) and SB3 (pkgs/seat/*, tests/seat/*) touch disjoint files; SB3 is the wave-1 editor of `flake.nix`/`githooks/pre-commit`/`docs/MAP.md` |
| 2 | `"SB1"` `"SB4"` | SB1: [SB3]; SB4: [SB3] | after wave 1 — SB1 (module + host wiring, the wave-2 editor of `flake.nix`/`docs/MAP.md`) and SB4 (factory-task/review, no flake.nix) touch disjoint files |
| 3 | `"SB5"` `"SB6"` | SB5: [SB1, SB2, SB3]; SB6: [SB1] | after wave 2 — **both edit `flake.nix`** (and SB5 also regenerates `docs/MAP.md`), so run SB5 before SB6 in key order within the wave |

`flake.nix` is edited by SB3 (wave 1: `seat-unit` check + ruff lists + `packages`), SB1 (wave 2: `nixosModules.seatLane`, `seatEvalSystem`, `seatBadSystem`, `seatPolkitRules`, `seat-eval`/`seat-assertion-negative`/`seat-polkit-unit` checks, `host-core` seat asserts, core modules list), SB5 (wave 3: `seat-vm`), SB6 (wave 3: `host-core` backup asserts). `docs/MAP.md` is regenerated by whoever adds a check (SB3, SB1, SB5) before their commit, or the lint gate's MAP-vs-flake diff fails. `nixosModules/egressBroker.nix` is edited only by SB1 (the `inbound` option + one render line).

---

## Tasks

### SB2 (code, M) — the wrapper gains `--broker` and `--bind-namespace`

**dependsOn:** none

**Files:**
- Modify: `pkgs/dsh-openrouter/dsh-openrouter.sh` (usage lines 39–65; mode/arg init near line 76; the arg-parsing loop lines 88–131; the key block lines 220–243; the exec lines 559–582)
- Modify: `pkgs/dsh-openrouter/default.nix` (runtimeInputs lines 70–76; passthru lines 101–105)
- Test: `tests/unit/72-seat-broker.bats` (new)

**Interfaces:**
- Produces (consumed by SB1's module, SB3's `seat-run.py`, SB5's VM fake):
  - `dsh-openrouter --broker` — skips the key file entirely (never reads, never mode-checks or ownership-checks it); keeps the existing `OPENROUTER_API_KEY` untouched (the unit's `injected-by-broker` placeholder); requires `SEAT_BROKER_GATEWAY` (the broker's `hostAddress`) and `ip route show default` to contain `via $SEAT_BROKER_GATEWAY`, else exits **6**.
  - `dsh-openrouter --broker --bind-namespace <ns-addr>` — web mode binds the UI to `<ns-addr>` instead of `127.0.0.1`; `--bind-namespace` without `--broker` exits **2**.
  - Without `--broker`, an actual launch (`web`/`headless`) prints one deprecation line to **stderr** pointing at the seat unit; `--dump-config`/`--denials` print nothing.
  - `dsh-openrouter` gains `passthru.proxyShim = "${dsh}/lib/proxy-shim.cjs"` (SB1's unit uses it for `NODE_OPTIONS`).

Facts behind these edits (commands run: `read pkgs/dsh-openrouter/dsh-openrouter.sh`, `read pkgs/dsh-openrouter/default.nix`): the key block is lines 220–243 (`key_file=${OPENROUTER_KEY_FILE:-...}` through `export OPENROUTER_API_KEY=$key`); the exec dispatch is lines 559–582 with the web line 580 hard-coding `--host 127.0.0.1`; the wrapper's runtimeInputs are `nodejs_22 bubblewrap coreutils findutils zstd` (default.nix:70–76) — **no `iproute2`**, which `--broker`'s `ip route` check needs; `passthru` already carries `guardPython` (default.nix:101–105).

- [ ] **Step 1: Write the failing tests** — create `tests/unit/72-seat-broker.bats`:

```bats
#!/usr/bin/env bats
# dsh-openrouter --broker / --bind-namespace (seat-behind-broker plan SB2): the
# wrapper under --broker skips the key file, keeps the placeholder, and only
# launches inside the seat namespace (default route via the broker gateway).
# Shown to fail first: with no --broker flag today, every case below exits
# differently (no exit 6, no "seat namespace" message, and --bind-namespace is
# an unknown option -> exit 2 for the wrong reason).

setup() {
  TMPHOME=$(mktemp -d)
  export HOME="$TMPHOME"
  export XDG_CONFIG_HOME="$TMPHOME/.config"
  export XDG_DATA_HOME="$TMPHOME/.local/share"
  export DSH_CACHE_ROOT="$TMPHOME"
  export CLAUDE_PROJECT_DIR="$TMPHOME/ws"
  unset OPENROUTER_API_KEY OPENROUTER_KEY_FILE OPENROUTER_BASE_URL OPENROUTER_MODEL \
    DSH_HOME DSH_PERMISSION_MODE DSH_HOOK_GUARD OPENROUTER_REASONING_EFFORT \
    SEAT_BROKER_GATEWAY SEAT_NAMESPACE_ADDRESS
  unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy
  mkdir -p "$TMPHOME/ws"
  cd "$TMPHOME/ws"
}

teardown() {
  rm -rf "$TMPHOME"
}

@test "--bind-namespace without --broker refuses (exit 2)" {
  run dsh-openrouter --bind-namespace 10.100.4.2 --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace is only accepted with --broker"* ]]
}

@test "--broker with no SEAT_BROKER_GATEWAY refuses (exit 6)" {
  run dsh-openrouter --broker --dump-config
  [ "$status" -eq 6 ]
  [[ "$output" == *"SEAT_BROKER_GATEWAY"* ]]
}

@test "--broker outside the seat namespace refuses (exit 6)" {
  run env SEAT_BROKER_GATEWAY=10.100.4.1 dsh-openrouter --broker --dump-config
  [ "$status" -eq 6 ]
  [[ "$output" == *"not the seat broker gateway"* ]]
}

@test "--broker never inspects the key file (a 000-mode key is untouched)" {
  mkdir -p "$XDG_CONFIG_HOME/openrouter"
  printf 'sk-fake-from-a-000-file\n' > "$XDG_CONFIG_HOME/openrouter/key"
  chmod 000 "$XDG_CONFIG_HOME/openrouter/key"
  # The normal (non-broker) path would die 4 on the mode here; --broker must
  # not reach it -- the only failure allowed is the namespace refusal. This is
  # the strace-free proof: no "no key", no "0600/0400", no mode complaint.
  run env SEAT_BROKER_GATEWAY=10.100.4.1 dsh-openrouter --broker --dump-config
  [ "$status" -eq 6 ]
  [[ "$output" != *"no key"* ]]
  [[ "$output" != *"0600"* ]]
  [[ "$output" != *"0400"* ]]
}
```

- [ ] **Step 2: Run it to see it fail**

Run: `nix develop -c bats tests/unit/72-seat-broker.bats`
Expected: FAIL — `--bind-namespace` is unknown (exit 2 with "unknown option"); `--broker` is unknown too (exit 2, and no exit 6 path exists yet), so the four cases fail against today's wrapper.

- [ ] **Step 3: Implement the wrapper flags**

3a. In `pkgs/dsh-openrouter/dsh-openrouter.sh`, add to the usage text after the `--permission` line:

```text
  --broker             run behind the seat broker: skip the key file, keep
                       OPENROUTER_API_KEY (the unit's placeholder), require the
                       seat namespace (exit 6 otherwise)
  --bind-namespace ADDR  web mode binds the UI to ADDR instead of 127.0.0.1
                       (only with --broker); without it the --host passthrough
                       stays rejected
```

3b. After the argument defaults (near `mode=web`, `model=…`, `base_url=…`, `port_given=0`), initialise the two flags and add their cases to the `while` argument loop beside `--headless`/`--dump-config`:

```bash
broker=0
bind_namespace=
...
    --broker)
      broker=1
      shift
      ;;
    --bind-namespace)
      [ $# -ge 2 ] || die 2 "--bind-namespace needs an address"
      bind_namespace=$2
      shift 2
      ;;
```

3c. Immediately after the loop, enforce the coupling:

```bash
if [ -n "$bind_namespace" ] && [ "$broker" -eq 0 ]; then
  die 2 "--bind-namespace is only accepted with --broker"
fi
```

3d. Wrap the key block (lines 220–243) so it runs only when **not** broker, and add the broker branch and the deprecation, replacing the current `if [ -n "${OPENROUTER_API_KEY:-}" ]` … `fi`:

```bash
if [ "$broker" -eq 1 ]; then
  key_source="broker (seat broker injects the Authorization header; env holds only the placeholder)"
  if [ -z "${SEAT_BROKER_GATEWAY:-}" ]; then
    die 6 "dsh-openrouter --broker needs SEAT_BROKER_GATEWAY (the broker's hostAddress; the seat@ unit sets it)"
  fi
  if ! ip route show default | grep -q "via ${SEAT_BROKER_GATEWAY} "; then
    die 6 "dsh-openrouter --broker refuses: the default route is not the seat broker gateway ${SEAT_BROKER_GATEWAY} (not in egress-seat; a request here would leak the placeholder as if it were a key)"
  fi
elif [ -n "${OPENROUTER_API_KEY:-}" ]; then
  key_source="OPENROUTER_API_KEY (environment)"
else
  key_file=${OPENROUTER_KEY_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/openrouter/key}
  if [ ! -e "$key_file" ]; then
    die 4 "no key: export OPENROUTER_API_KEY, or create $key_file with: (umask 077; mkdir -p \"\$(dirname $key_file)\"; IFS= read -r -s k; printf '%s' \"\$k\" > $key_file) -- paste the key at the blank line"
  fi
  if [ -L "$key_file" ] || [ ! -f "$key_file" ]; then
    die 4 "$key_file must be a regular file, not a symlink"
  fi
  if [ "$(stat -c %u -- "$key_file")" != "$(id -u)" ]; then
    die 4 "$key_file is not owned by you"
  fi
  key_mode=$(stat -c %a -- "$key_file")
  case $key_mode in
    600 | 400) ;;
    *) die 4 "$key_file has mode $key_mode; it must be 0600 or 0400 (chmod 0600 $key_file)" ;;
  esac
  key=$(head -n 1 -- "$key_file")
  key=${key//[[:space:]]/}
  [ -n "$key" ] || die 4 "$key_file is empty"
  export OPENROUTER_API_KEY=$key
  key_source=$key_file
  printf 'dsh-openrouter: deprecated: this launch reads %s; run through the seat unit instead (seat-submit headless|web) -- docs/runbooks/lanes.md\n' "$key_file" >&2
fi
```

(Exit code 6 is new; it is distinct from 2/3/4/5 already used, and the test greps its message.)

3e. In the exec `web` branch (line 580), honour `--bind-namespace`:

```bash
    if [ -n "$bind_namespace" ]; then
      exec node --expose-internals "$bin_js" --profile web --patch "$overlay" --host "$bind_namespace" "$@"
    else
      exec node --expose-internals "$bin_js" --profile web --patch "$overlay" --host 127.0.0.1 "$@"
    fi
```

3f. In `pkgs/dsh-openrouter/default.nix`, add `iproute2` to `wrapper.runtimeInputs` (so `ip route` exists on the wrapper's own PATH) and `proxyShim` to the `passthru` attrset:

```nix
    runtimeInputs = [
      nodejs_22
      bubblewrap
      coreutils
      findutils
      iproute2
      zstd
    ];
...
  passthru = {
    guardPython = python3Minimal;
    proxyShim = "${dsh}/lib/proxy-shim.cjs";
  };
```

(`iproute2` must join the `{ lib, writeShellApplication, symlinkJoin, writers, nodejs_22, bubblewrap, coreutils, iproute2, findutils, zstd, dsh, python3Minimal, buildPackages }` argument list.)

- [ ] **Step 4: Run the tests to see them pass**

Run: `nix develop -c bats tests/unit/72-seat-broker.bats`
Expected: PASS (4/4).

- [ ] **Step 5: Run the existing wrapper suite and the lint gate**

Run: `nix develop -c bats tests/unit/70-dsh-openrouter.bats` (unchanged behaviour — the non-broker path is identical except the stderr deprecation line) and `nix develop -c githooks/pre-commit`.
Expected: PASS; pre-commit green (the `--dump-config` cases print no deprecation, so their stdout assertions hold).

- [ ] **Step 6: Commit**

```bash
git add pkgs/dsh-openrouter/dsh-openrouter.sh pkgs/dsh-openrouter/default.nix tests/unit/72-seat-broker.bats
nix develop -c git commit -F - <<'MSG'
dsh: the seat wrapper gains --broker (skip the key file, require the seat namespace) and --bind-namespace (web UI, broker only) (test: unit, lint)
MSG
```

**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, pkgs/dsh-openrouter/default.nix, tests/unit/72-seat-broker.bats
**acceptance:** unit, lint
**commit subject:** `dsh: the seat wrapper gains --broker (skip the key file, require the seat namespace) and --bind-namespace (web UI, broker only) (test: unit, lint)`

---

### SB3 (code, L) — `seat-submit` and `seat-run`: jobs, not arguments

**dependsOn:** none

**Files:**
- Create: `pkgs/seat/seat-submit.py`
- Create: `pkgs/seat/seat-run.py`
- Test: `tests/seat/test_seat_submit.py` (new)
- Test: `tests/seat/test_seat_run.py` (new)
- Modify: `flake.nix` (checks — add `seat-unit`; lint — add `pkgs/seat tests/seat` to both ruff lists at lines ~889–890; the `checks` attrset; `packages` optional)
- Modify: `githooks/pre-commit` (ruff lists, lines 25–26)
- Regenerate: `docs/MAP.md` (`nix develop -c python3 pkgs/evidence/repomap.py --root . write` — the new `seat-unit` check must reach the Checks section or the lint MAP-vs-flake diff fails)

**Interfaces:**
- Consumes (from SB2, by spelling only; these are exercised, not executed, by this task's unit tests): `dsh-openrouter --broker --model <id> --headless "<brief>"` and `dsh-openrouter --broker --bind-namespace <ns> --model <id> -- --no-open --port N`.
- Produces (consumed by SB1 — which wraps them — and SB4 — which drives the CLI):
  - `seat-submit [--jobs-dir DIR] [--no-start] headless --workspace PATH --dsh-home PATH --model ID --effort LEVEL [--brief FILE] [--timeout S]` — writes `/var/lib/seat/jobs/<id>/` (0700) with `job.json` and `brief.txt`, `systemctl start seat@<id>.service` (unless `--no-start`), then polls `result.txt` every 2 s up to `--timeout` (default 10800), prints `stdout.txt` to stdout, exits with `exit_code.txt`'s integer.
  - `seat-submit [--jobs-dir DIR] [--no-start] web --workspace PATH --dsh-home PATH --model ID --effort LEVEL --port N` — same job-dir write + start, then polls `url.txt`, prints it, exits 0.
  - `<id>` = `"<unix-ts>-<6 hex>"`. `SEAT_STATE_DIR` overrides the jobs root (tests).
  - `seat-run <job-id>` — reads `job.json`; exports `DSH_HOME=<job.dsh_home>` and `OPENROUTER_REASONING_EFFORT=<job.effort>`; cds to `<job.workspace>`; runs the headless or web `dsh-openrouter --broker` line above; writes `stdout.txt`, `stderr.txt`, `exit_code.txt`, `result.txt` (the `FACTORY-RESULT`/`-CHECKS`/`-COMMITS`/`-NOTES` lines, or `FACTORY-RESULT status=failed` if none) and, for web, `url.txt = http://<SEAT_NAMESPACE_ADDRESS>:<port>/`.

Facts behind the shape (commands run: `read pkgs/lane/lane-submit.py`, `read pkgs/lane/lane-run.py`, `read nixosModules/modelLane.nix`): `lane-submit`/`lane-wait` are both `writeShellApplication` wrappers over one Python file in `modelLane.nix` (its `let` block), each `export LANE_MODE=…; exec python3 ${../pkgs/lane/lane-submit.py}` — the seat binaries mirror this exactly, which is why SB1 can wrap SB3's scripts without SB3 touching the module.

- [ ] **Step 1: Write the failing tests**

Create `tests/seat/test_seat_submit.py`:

```python
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUBMIT = ROOT / "pkgs/seat/seat-submit.py"


def run_submit(args, env_extra=None):
    env = dict(os.environ)
    env["SEAT_STATE_DIR"] = str(env_extra.pop("state_dir"))
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SUBMIT), *args],
        capture_output=True, text=True, env=env,
    )


def test_job_dir_and_fields(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    dsh = tmp_path / "dsh"
    dsh.mkdir()
    brief = tmp_path / "brief.txt"
    brief.write_text("Reply ok.\n")
    proc = run_submit(
        ["--no-start", "headless", "--workspace", str(ws), "--dsh-home", str(dsh),
         "--model", "test/model", "--effort", "high", "--brief", str(brief)],
        {"state_dir": tmp_path / "jobs"},
    )
    assert proc.returncode == 0, proc.stderr
    job_id = proc.stdout.strip()
    job_dir = Path(os.environ["SEAT_STATE_DIR"]) / job_id
    assert oct(stat.S_IMODE(job_dir.stat().st_mode)) == "0o700"
    job = json.loads((job_dir / "job.json").read_text())
    assert job["mode"] == "headless"
    assert job["workspace"] == str(ws.resolve())
    assert job["dsh_home"] == str(dsh)
    assert job["model"] == "test/model"
    assert job["effort"] == "high"
    assert job["brief"] == "brief.txt"
    assert (job_dir / "brief.txt").read_text() == "Reply ok.\n"


def test_refuses_a_missing_workspace(tmp_path):
    dsh = tmp_path / "dsh"; dsh.mkdir()
    brief = tmp_path / "brief.txt"; brief.write_text("hi\n")
    proc = run_submit(
        ["--no-start", "headless", "--workspace", str(tmp_path / "nope"),
         "--dsh-home", str(dsh), "--model", "m", "--effort", "medium",
         "--brief", str(brief)],
        {"state_dir": tmp_path / "jobs"},
    )
    assert proc.returncode == 2
    assert "workspace" in proc.stderr
```

Create `tests/seat/test_seat_run.py`:

```python
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "pkgs/seat/seat-run.py"

FAKE_DSH = """#!/usr/bin/env bash
printf 'dsh-openrouter argv='
printf '%s ' "$@"
printf '\\n'
printf 'FACTORY-RESULT status=done\\nFACTORY-CHECKS seat=pass\\nFACTORY-COMMITS 1\\nFACTORY-NOTES ok\\n'
exit 0
"""


def make_fake(tmp_path):
    b = tmp_path / "bin"
    b.mkdir()
    dsh = b / "dsh-openrouter"
    dsh.write_text(FAKE_DSH)
    dsh.chmod(0o755)
    return b


def make_job(tmp_path, mode, **kw):
    ws = tmp_path / "ws"; ws.mkdir()
    job_dir = tmp_path / "jobs" / "j1"; job_dir.mkdir(parents=True)
    job = {"mode": mode, "workspace": str(ws), "dsh_home": str(tmp_path / "dsh"),
           "model": "test/model", "effort": "xhigh",
           "brief": "brief.txt" if mode == "headless" else None,
           "port": kw.get("port")}
    (job_dir / "job.json").write_text(json.dumps(job))
    (job_dir / "brief.txt").write_text("Reply ok.\n")
    return job_dir, ws


def run_seat(tmp_path, job_dir, bin_dir, env_extra=None):
    env = dict(os.environ)
    env["SEAT_STATE_DIR"] = str(tmp_path)
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    env["SEAT_NAMESPACE_ADDRESS"] = "10.100.4.2"
    env["SEAT_BROKER_GATEWAY"] = "10.100.4.1"
    if env_extra:
        env.update(env_extra)
    r = subprocess.run([sys.executable, str(RUN), "j1"],
                       capture_output=True, text=True, env=env,
                       cwd=str(job_dir))
    return r, job_dir


def test_headless_argv_and_result(tmp_path):
    job_dir, _ = make_job(tmp_path, "headless")
    r, job_dir = run_seat(tmp_path, job_dir, make_fake(tmp_path))
    assert r.returncode == 0
    out = (job_dir / "stdout.txt").read_text()
    assert "--broker --model test/model --headless Reply ok." in out, out
    assert (job_dir / "exit_code.txt").read_text().strip() == "0"
    assert "FACTORY-RESULT status=done" in (job_dir / "result.txt").read_text()


def test_web_argv_writes_url_before_launch(tmp_path):
    job_dir, _ = make_job(tmp_path, "web", port=43201)
    r, job_dir = run_seat(tmp_path, job_dir, make_fake(tmp_path))
    assert r.returncode == 0
    out = (job_dir / "stdout.txt").read_text()
    assert "--broker --bind-namespace 10.100.4.2 --model test/model -- --no-open --port 43201" in out, out
    assert (job_dir / "url.txt").read_text().strip() == "http://10.100.4.2:43201/"
```

- [ ] **Step 2: Run them to see them fail**

Run: `nix develop -c pytest tests/seat -q`
Expected: FAIL — `pkgs/seat/seat-submit.py` does not exist yet (collection/E imports error), so nothing runs.

- [ ] **Step 3: Implement the two scripts**

`pkgs/seat/seat-submit.py`:

```python
"""Operator CLI for the seat (seat-behind-broker plan SB3): writes a job
directory for seat-run (pkgs/seat/seat-run.py) and starts seat@<id>, or waits
for that unit's result. Backs the seat-submit binary built by
nixosModules/seatLane.nix (the same one-file/one-binary-in-the-module shape as
lane-submit -- see modelLane.nix's let block).

  seat-submit [--jobs-dir DIR] [--no-start] headless \
      --workspace PATH --dsh-home PATH --model ID --effort LEVEL \
      [--brief FILE] [--timeout S]
  seat-submit [--jobs-dir DIR] [--no-start] web \
      --workspace PATH --dsh-home PATH --model ID --effort LEVEL --port N

Writes /var/lib/seat/jobs/<id>/ (0700, invoking user) holding job.json +
brief.txt; starts seat@<id>.service (unless --no-start); headless polls
result.txt every 2 s up to --timeout (default 10800) then relays stdout.txt to
its own stdout and exits with exit_code.txt's integer; web polls url.txt,
prints it, exits 0. SEAT_STATE_DIR overrides the jobs root (tests).
"""

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

EFFORTS = ("off", "low", "medium", "high", "xhigh")


def _jobs_root(args):
    return Path(os.environ.get("SEAT_STATE_DIR", "/var/lib/seat")) / "jobs"


def main(argv):
    p = argparse.ArgumentParser(prog="seat-submit")
    p.add_argument("--jobs-dir", default="/var/lib/seat/jobs")
    p.add_argument("--no-start", action="store_true")
    p.add_argument("mode", choices=("headless", "web"))
    p.add_argument("--workspace", required=True)
    p.add_argument("--dsh-home", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--effort", required=True, choices=EFFORTS)
    p.add_argument("--brief")
    p.add_argument("--timeout", type=float, default=10800.0)
    p.add_argument("--port", type=int)
    p.add_argument("--poll-interval", type=float, default=2.0)
    args = p.parse_args(argv)

    jobs = _jobs_root(args)
    ws = Path(args.workspace).expanduser()
    if not ws.is_dir():
        print(f"seat-submit: --workspace {args.workspace} is not a directory", file=sys.stderr)
        return 2
    if args.mode == "headless":
        if not args.brief or not Path(args.brief).is_file():
            print(f"seat-submit: --brief {args.brief} is not a readable file", file=sys.stderr)
            return 2
    if args.mode == "web" and not args.port:
        print("seat-submit: web mode requires --port (within the seat web range)", file=sys.stderr)
        return 2

    job_id = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    job_dir = jobs / job_id
    os.makedirs(job_dir, exist_ok=True)
    os.chmod(job_dir, 0o700)

    job = {
        "mode": args.mode,
        "workspace": str(ws.resolve()),
        "dsh_home": args.dsh_home,
        "model": args.model,
        "effort": args.effort,
        "brief": "brief.txt" if args.mode == "headless" else None,
        "port": args.port,
        "submitted": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (job_dir / "job.json").write_text(json.dumps(job) + "\n", encoding="utf-8")
    os.chmod(job_dir / "job.json", 0o600)
    if args.mode == "headless":
        data = Path(args.brief).read_bytes()
        (job_dir / "brief.txt").write_bytes(data)
        os.chmod(job_dir / "brief.txt", 0o600)

    print(job_id)

    if not args.no_start:
        subprocess.run(["systemctl", "start", f"seat@{job_id}.service"], check=False)

    if args.mode == "web":
        url_path = job_dir / "url.txt"
        deadline = time.time() + args.timeout
        while not url_path.exists():
            if time.time() >= deadline:
                print(f"seat-submit: timed out waiting for {url_path}", file=sys.stderr)
                return 1
            time.sleep(args.poll_interval)
        print(url_path.read_text(encoding="utf-8").strip())
        return 0

    result_path = job_dir / "result.txt"
    deadline = time.time() + args.timeout
    while not result_path.exists():
        if time.time() >= deadline:
            print(f"seat-submit: timed out waiting for {result_path}", file=sys.stderr)
            return 1
        time.sleep(args.poll_interval)
    stdout_path = job_dir / "stdout.txt"
    if stdout_path.exists():
        sys.stdout.write(stdout_path.read_text(encoding="utf-8"))
    code_path = job_dir / "exit_code.txt"
    if code_path.exists():
        try:
            return int(code_path.read_text(encoding="utf-8").strip())
        except ValueError:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

`pkgs/seat/seat-run.py`:

```python
"""Seat job runner (seat-behind-broker plan SB3): the entry
nixosModules/seatLane.nix's seat@.service runs as `seat-run %i`. Reads one
job.json, exports DSH_HOME + OPENROUTER_REASONING_EFFORT, cds to the job's
workspace, runs dsh-openrouter --broker, and writes stdout.txt / stderr.txt /
exit_code.txt / result.txt (the FACTORY-* block) / url.txt (web) into the job
directory. Every terminal outcome leaves exit_code.txt + result.txt so the
submitter can never hang.

  headless: dsh-openrouter --broker --model M --headless "$(cat brief.txt)"
  web:      dsh-openrouter --broker --bind-namespace A --model M -- --no-open --port N
            (A = SEAT_NAMESPACE_ADDRESS from the unit); url.txt is written
            before launch from the known port so the operator browser can be
            opened while the harness is still booting.
"""

import json
import os
import subprocess
import sys

FACTORY_FIELDS = ("FACTORY-RESULT", "FACTORY-CHECKS", "FACTORY-COMMITS", "FACTORY-NOTES")


def _job_dir(job_id):
    return os.path.join(os.environ.get("SEAT_STATE_DIR", "/var/lib/seat"), "jobs", job_id)


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _env(job):
    env = dict(os.environ)
    env["DSH_HOME"] = job["dsh_home"]
    env["OPENROUTER_REASONING_EFFORT"] = job["effort"]
    return env


def main(argv):
    if len(argv) != 2:
        print("usage: seat-run <job-id>", file=sys.stderr)
        return 2
    job_id = argv[1]
    job_dir = _job_dir(job_id)

    try:
        with open(os.path.join(job_dir, "job.json"), encoding="utf-8") as f:
            job = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        _write(os.path.join(job_dir, "exit_code.txt"), "1")
        _write(os.path.join(job_dir, "result.txt"), "FACTORY-RESULT status=failed\n")
        _write(os.path.join(job_dir, "stdout.txt"), "")
        print(f"seat-run: cannot read job: {e}", file=sys.stderr)
        return 1

    env = _env(job)
    stdout_path = os.path.join(job_dir, "stdout.txt")
    stderr_path = os.path.join(job_dir, "stderr.txt")

    if job["mode"] == "headless":
        with open(os.path.join(job_dir, "brief.txt"), encoding="utf-8") as f:
            brief = f.read()
        args = ["dsh-openrouter", "--broker", "--model", job["model"], "--headless", brief]
        proc = subprocess.run(args, cwd=job["workspace"], env=env,
                              capture_output=True, text=True, check=False)
        _write(stdout_path, proc.stdout)
        _write(stderr_path, proc.stderr)
        _write(os.path.join(job_dir, "exit_code.txt"), str(proc.returncode))
        result = [ln for ln in proc.stdout.splitlines() if ln.split(" ", 1)[0] in FACTORY_FIELDS]
        result_text = "\n".join(result) if result else "FACTORY-RESULT status=failed exit_code=%d\n" % proc.returncode
        _write(os.path.join(job_dir, "result.txt"), result_text.rstrip("\n") + "\n")
        return proc.returncode

    # web: write the URL first (the browser can open while the harness boots),
    # then run the harness streaming to the job files until the operator stops
    # the unit (Type=simple keeps it running).
    port = job.get("port") or 43200
    ns = os.environ.get("SEAT_NAMESPACE_ADDRESS", "")
    _write(os.path.join(job_dir, "url.txt"), f"http://{ns}:{port}/\n")
    print(f"seat web: http://{ns}:{port}/", file=sys.stderr)
    args = ["dsh-openrouter", "--broker", "--bind-namespace", ns,
            "--model", job["model"], "--", "--no-open", "--port", str(port)]
    with open(stdout_path, "w", encoding="utf-8") as out, \
         open(stderr_path, "w", encoding="utf-8") as err:
        proc = subprocess.run(args, cwd=job["workspace"], env=env,
                              stdout=out, stderr=err, text=True, check=False)
    _write(os.path.join(job_dir, "exit_code.txt"), str(proc.returncode))
    result = []
    with open(stdout_path, encoding="utf-8") as f:
        for ln in f:
            if ln.split(" ", 1)[0] in FACTORY_FIELDS:
                result.append(ln.rstrip("\n"))
    with open(os.path.join(job_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(result) if result else "FACTORY-RESULT status=failed\n")
        f.write("\n")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `nix develop -c pytest tests/seat -q`
Expected: PASS.

- [ ] **Step 5: Wire the `seat-unit` check and the lint lists**

In `flake.nix`, add `pkgs/seat tests/seat` to both `ruff check`/`ruff format --check` lists (the lines listing `pkgs/lane tests/lane`), mirror `lane-unit`'s `runCommand` to add a `seat-unit` check to `checks.${system}`:

```nix
        seat-unit =
          pkgs.runCommand "seat-unit-tests"
            {
              nativeBuildInputs = [ helmPython pkgs.git ];
            }
            ''
              mkdir -p pkgs tests
              cp -r ${self}/pkgs/seat pkgs/seat
              cp -r ${self}/tests/seat tests/seat
              pytest tests/seat -q
              touch $out
            '';
```

In `githooks/pre-commit`, add `pkgs/seat tests/seat` to its two ruff lines (mirroring how `pkgs/lane tests/lane` is listed today). Then regenerate the map:

Run: `nix develop -c python3 pkgs/evidence/repomap.py --root . write`
Then: `git add docs/MAP.md` and confirm `git diff` shows only the `seat-unit` line added under Checks.

- [ ] **Step 6: Run the check and the lint gate**

Run: `nix build .#checks.x86_64-linux.seat-unit -L --no-link` then `nix develop -c githooks/pre-commit`.
Expected: PASS both (pre-commit now scans `pkgs/seat tests/seat` and the MAP/flake check list agree).

- [ ] **Step 7: Commit**

```bash
git add pkgs/seat tests/seat flake.nix githooks/pre-commit docs/MAP.md
nix develop -c git commit -F - <<'MSG'
seat: seat-submit writes the job spool and seat-run runs dsh-openrouter --broker into it (test: seat-unit, lint)
MSG
```

**touches:** pkgs/seat/seat-submit.py, pkgs/seat/seat-run.py, tests/seat/test_seat_submit.py, tests/seat/test_seat_run.py, flake.nix, githooks/pre-commit, docs/MAP.md
**acceptance:** seat-unit, lint
**commit subject:** `seat: seat-submit writes the job spool and seat-run runs dsh-openrouter --broker into it (test: seat-unit, lint)`

---

### SB1 (code, L) — the `seatLane` module: broker instance, `seat@` template, polkit, nftables, host wiring

**dependsOn:** SB3 (wraps `pkgs/seat/seat-submit.py` and `pkgs/seat/seat-run.py`), SB2 (the `--broker` flag and `passthru.proxyShim` the unit consumes)

**Files:**
- Create: `nixosModules/seatLane.nix`
- Modify: `nixosModules/egressBroker.nix` (add the `inbound` instance option; render its accept into the `input-<name>` chain)
- Create: `hosts/core/seat.nix`
- Modify: `hosts/core/default.nix` (import `./seat.nix`)
- Test: `tests/seat/polkit.test.mjs` (new)
- Modify: `flake.nix` (`nixosModules.seatLane`, `seatEvalSystem`, `seatBadSystem`, `seatPolkitRules`, `seat-eval`/`seat-assertion-negative`/`seat-polkit-unit` checks, `host-core` seat asserts, core modules list)
- Regenerate: `docs/MAP.md` (adds three checks)

**Interfaces:**
- Consumes: SB3's `seat-submit`/`seat-run` scripts (wrapped via `writeShellApplication`); SB2's `dsh-openrouter --broker`/`--bind-namespace` and `passthru.proxyShim`.
- Produces: module options `services.seat-lane.{enable,host,keyFile,hostAddress,namespaceAddress,listenPort,webPortRange,operatorUser,harnessPackage}`; the `seat@.service` template; `services.egress-broker.instances.seat`; the rendered `seat-submit` binary on `environment.systemPackages`; the generalised polkit grant for `seat@*`.

Facts behind the module (commands run: `read nixosModules/modelLane.nix`, `read nixosModules/egressBroker.nix:159-194`, `read hosts/core/lanes.nix`, `read flake.nix:503-559,616-666,690-779,1283-1494`): the lane mirror is `modelLane.nix`'s `laneModule` (`User`/`NetworkNamespacePath`/`environment`/`serviceConfig`) with its `caBundle` path function; `egressBroker.nix`'s `input-<name>` chain ends `iifname "veb-${name}" drop`; `hosts/core/lanes.nix:10-17` declares the openrouter lane's `hostAddress`/`namespaceAddress`/`listenPort` (3131, block 10.100.3.x); `hosts/core/default.nix:4-13` imports modules; `flake.nix:616-625` exports modules and `:640-666` lists core's modules.

- [ ] **Step 1: Write the failing check — `seat-eval`**

Create `nixosModules/seatLane.nix` first (the module under test must exist for the check to reference it), then add to `flake.nix`, above `in {`, beside `laneEvalSystem`:

```nix
      seatEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            services.seat-lane = {
              enable = true;
              host = "example.com";
              keyFile = "/var/lib/secrets/seat-key";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3132;
            };
          })
        ];
      };
      seatBadSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seatLane
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.dalhaka = { isNormalUser = true; uid = 1000; };
            services.seat-lane = {
              enable = true;
              host = "example.com";
              keyFile = "/var/lib/secrets/seat-key";
            };
            # a REAL key in the unit's environment must fail the seatLane
            # assertion (the placeholder is the only allowed value).
            systemd.services."seat@".environment.OPENROUTER_API_KEY = nixpkgs.lib.mkForce "sk-leaked-real-key";
          })
        ];
      };
```

And add `seat-eval` and `seat-assertion-negative` to `checks.${system}` (mirroring `lane-eval` at flake.nix:1283 and `lane-unit`'s structure), using `seatEvalSystem`/`seatBadSystem`. Write the assertions as steps 3–4 below, but first ensure the check **fails**: `seat-eval`'s first assertion must reference an option (`services.seat-lane`) that does not exist yet, so the eval errors.

- [ ] **Step 2: Run it to see it fail**

Run: `nix build .#checks.x86_64-linux.seat-eval -L --no-link` (with the assertions written to reference `c.services.egress-broker.instances.seat`, which nothing renders yet).
Expected: FAIL — `seat-eval: egress-broker instance 'seat' must be rendered …` (the instance is absent).

- [ ] **Step 3: Implement `nixosModules/seatLane.nix`**

```nix
_: {
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.seat-lane;
  seatSubmit = pkgs.writeShellApplication {
    name = "seat-submit";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 ${../pkgs/seat/seat-submit.py} "$@"
    '';
  };
  seatRun = pkgs.writeShellApplication {
    name = "seat-run";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 ${../pkgs/seat/seat-run.py} "$@"
    '';
  };
  # The public-only copy egressBroker.nix's ExecStartPost publishes outside
  # the /var/lib/egress-broker tree that InaccessiblePaths hides (same
  # reasoning modelLane.nix's caBundle comment records): hiding the broker's
  # private CA + audit log must not also cut off the one file the seat needs.
  caBundle = "/var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt";
  opHome = "/home/${cfg.operatorUser}";
in
{
  options.services.seat-lane = {
    enable = lib.mkEnableOption "the operator's seat behind the egress broker (docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md)";
    host = lib.mkOption {
      type = lib.types.str;
      default = "openrouter.ai";
      description = "The single upstream hostname the seat's broker instance allows.";
    };
    keyFile = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/secrets/openrouter-key";
      description = "Key file the broker injects for `host`; never read by the module or the seat. Must stay outside /nix/store (asserted).";
    };
    hostAddress = lib.mkOption { type = lib.types.str; default = "10.100.4.1"; };
    namespaceAddress = lib.mkOption { type = lib.types.str; default = "10.100.4.2"; };
    listenPort = lib.mkOption { type = lib.types.port; default = 3132; };
    webPortRange = lib.mkOption {
      type = lib.types.str;
      default = "43200-43299";
      description = "Host->namespace tcp dport range the web seat may bind; fed to nftables (egressBroker.inbound).";
    };
    operatorUser = lib.mkOption { type = lib.types.str; default = "dalhaka"; };
    harnessPackage = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ../pkgs/dsh-openrouter { dsh = pkgs.callPackage ../pkgs/dsh { }; };
      description = "The dsh-openrouter wrapper the seat@ unit runs --broker (and whose passthru.proxyShim the unit preloads).";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
        {
          assertion = !(lib.hasPrefix "/nix/store" cfg.keyFile);
          message = "services.seat-lane.keyFile must be a path outside /nix/store (never a store copy of a secret), got '${cfg.keyFile}'";
        }
        {
          assertion = lib.hasPrefix "10.100.4." cfg.hostAddress && lib.hasPrefix "10.100.4." cfg.namespaceAddress;
          message = "services.seat-lane: the seat owns address block 10.100.4.x; hostAddress/namespaceAddress must sit inside it (the openrouter lane is 10.100.3.x, media 10.100.2.x)";
        }
        {
          assertion = config.systemd.services."seat@".environment.OPENROUTER_API_KEY == "injected-by-broker";
          message = "services.seat-lane: seat@ must carry the placeholder OPENROUTER_API_KEY = \"injected-by-broker\" -- a real key in the unit's environment is forbidden (the broker injects the real header)";
        }
      ];

      services.egress-broker.instances.seat = {
        inherit (cfg) hostAddress namespaceAddress listenPort;
        allow = [ cfg.host ];
        inject.${cfg.host}.valueFile = cfg.keyFile;
        # Same data policy the lane stamps (decision 2026-09-03, brief §3
        # invariant 5): ZDR + training opt-out at the chokepoint.
        bodyPatch.${cfg.host} = {
          pathPrefixes = [ "/api/v1/chat/completions" ];
          merge.provider = {
            zdr = true;
            data_collection = "deny";
          };
        };
        # O3 resolved: fail closed -- nothing the seat consumes uses the
        # Anthropic-style /api/v1/messages path, so deny it before injection.
        denyPaths.${cfg.host}.pathPrefixes = [ "/api/v1/messages" ];
        # Host->namespace inbound for the web UI (rendered into input-seat by
        # egressBroker.nix's new `inbound` option).
        inbound = [
          { portRange = cfg.webPortRange; source = cfg.hostAddress; }
        ];
      };

      systemd.tmpfiles.rules = [
        "d /var/lib/seat 0750 ${cfg.operatorUser} users -"
        "d /var/lib/seat/jobs 0700 ${cfg.operatorUser} -"
      ];

      environment.systemPackages = [ seatSubmit ];

      systemd.services."seat@" = {
        description = "Operator seat: run one %i job through its own broker instance";
        requires = [ "egress-netns-seat.service" "egress-broker-seat.service" ];
        after = [ "egress-netns-seat.service" "egress-broker-seat.service" ];
        path = [ "/run/current-system/sw" cfg.harnessPackage ];
        environment = {
          HTTPS_PROXY = "http://${cfg.hostAddress}:${toString cfg.listenPort}";
          HTTP_PROXY = "http://${cfg.hostAddress}:${toString cfg.listenPort}";
          NO_PROXY = "127.0.0.1,${cfg.namespaceAddress}";
          SSL_CERT_FILE = caBundle;
          NIX_SSL_CERT_FILE = caBundle;
          NODE_EXTRA_CA_CERTS = caBundle;
          NODE_USE_ENV_PROXY = "1";
          NODE_OPTIONS = "--require ${cfg.harnessPackage.passthru.proxyShim}";
          OPENROUTER_API_KEY = "injected-by-broker";
          SEAT_BROKER_GATEWAY = cfg.hostAddress;
          SEAT_NAMESPACE_ADDRESS = cfg.namespaceAddress;
        };
        serviceConfig = {
          Type = "simple";
          User = cfg.operatorUser;
          NetworkNamespacePath = "/run/netns/egress-seat";
          ExecStart = "${seatRun}/bin/seat-run %i";
          ReadWritePaths = [
            "/var/lib/seat"
            "${opHome}/factory"
            "${opHome}/nixos-agent-env"
            "${opHome}/flakes"
            "${opHome}/.local/share/dsh-openrouter"
          ];
          NoNewPrivileges = true;
          ProtectSystem = "strict";
          PrivateTmp = true;
          CapabilityBoundingSet = "";
          RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX";
          InaccessiblePaths = [
            "-/run/baskets"
            "-/var/lib/baskets"
            "-/var/lib/helm"
            "-/var/lib/egress-broker"
            "-/var/lib/lanes"
            "-/var/lib/secrets"
          ];
        };
      };

      security.polkit.extraConfig = ''
        polkit.addRule(function(action, subject) {
          if (action.id == "org.freedesktop.systemd1.manage-units") {
            var verb = action.lookup("verb");
            var unit = action.lookup("unit");
            if ((verb == "start" || verb == "stop") &&
                unit.indexOf("seat@") === 0 &&
                unit.indexOf(".service", unit.length - 8) !== -1 &&
                subject.user == "${cfg.operatorUser}") {
              return polkit.Result.YES;
            }
          }
        });
      '';
  };
};
```

(Note the `_:` outer arg — statix rejects a `{ ... }:` header, per Global Constraints.)

- [ ] **Step 4: Add the `inbound` option to `nixosModules/egressBroker.nix`**

Add to the instance submodule's options (beside `denyPaths`):

```nix
          inbound = lib.mkOption {
            type = lib.types.listOf (
              lib.types.submodule {
                options = {
                  portRange = lib.mkOption {
                    type = lib.types.str;
                    description = "Host->namespace inbound tcp dport or range (e.g. \"43200-43299\") this instance accepts.";
                  };
                  source = lib.mkOption {
                    type = lib.types.str;
                    description = "Only ip saddr allowed to reach the namespace on portRange from the host side (the instance's hostAddress).";
                  };
                };
              }
            );
            default = [ ];
            description = "Inbound accepts rendered into the instance's input-<name> chain (e.g. a web UI bound inside the namespace).";
          };
```

And in the `input-<name>` chain render (the `content` builder that ends `iifname "veb-${name}" drop`), insert between the `established,related` accept and the final drop:

```nix
  ${lib.concatMapStrings (r: "        iifname \"veb-${name}\" tcp dport ${r.portRange} ip saddr ${r.source} accept\n") i.inbound}
```

- [ ] **Step 5: Wire `hosts/core`**

Create `hosts/core/seat.nix`:

```nix
{ dsh-openrouter-pkg, ... }:

{
  services.seat-lane = {
    enable = true;
    host = "openrouter.ai";
    keyFile = "/var/lib/secrets/openrouter-key";
    hostAddress = "10.100.4.1";
    namespaceAddress = "10.100.4.2";
    listenPort = 3132;
    operatorUser = "dalhaka";
    harnessPackage = dsh-openrouter-pkg;
  };
}
```

Add `./seat.nix` to `hosts/core/default.nix`'s imports (after `./lanes.nix`), and add `self.nixosModules.seatLane` to `flake.nix`'s `nixosConfigurations.core` modules list (beside `self.nixosModules.modelLane`), plus `seatLane = import ./nixosModules/seatLane.nix;` in the `nixosModules` attrset.

- [ ] **Step 6: Write the `seat-eval` assertions (green for the module)**

In `flake.nix`, express `seat-eval` (mirroring `lane-eval` at 1283–1455), reading `c = seatEvalSystem.config`, `unit = c.systemd.services."seat@"`, `sc = unit.serviceConfig`, `i = c.services.egress-broker.instances.seat`:

```nix
        seat-eval =
          let
            c = seatEvalSystem.config;
            unit = c.systemd.services."seat@";
            sc = unit.serviceConfig;
            i = c.services.egress-broker.instances.seat;
            caBundle = "/var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt";
          in
          assert nixpkgs.lib.assertMsg
            (i.hostAddress == "10.100.4.1" && i.namespaceAddress == "10.100.4.2" && i.listenPort == 3132 && i.allow == [ "example.com" ])
            "seat-eval: egress-broker instance 'seat' must render the seat address block and allow == [ host ]";
          assert nixpkgs.lib.assertMsg (i.inject."example.com".valueFile == "/var/lib/secrets/seat-key")
            "seat-eval: egress-broker instance 'seat' must inject from the seat's keyFile";
          assert nixpkgs.lib.assertMsg (i.denyPaths."example.com".pathPrefixes == [ "/api/v1/messages" ])
            "seat-eval: egress-broker instance 'seat' must deny /api/v1/messages (fail closed)";
          assert nixpkgs.lib.assertMsg (i.bodyPatch."example.com".pathPrefixes == [ "/api/v1/chat/completions" ])
            "seat-eval: egress-broker instance 'seat' must scope the ZDR patch to the chat-completions path";
          assert nixpkgs.lib.assertMsg
            (unit.requires == [ "egress-netns-seat.service" "egress-broker-seat.service" ] && unit.after == unit.requires)
            "seat-eval: seat@ must Require+After its netns and broker units";
          assert nixpkgs.lib.assertMsg
            (sc.Type == "simple" && sc.User == "dalhaka" && sc.NetworkNamespacePath == "/run/netns/egress-seat" && sc.ProtectSystem == "strict" && sc.NoNewPrivileges == true)
            "seat-eval: seat@ must run as the operator in the broker netns, hardened";
          assert nixpkgs.lib.assertMsg (sc.ExecStart == "${self.packages.${system}.seat-run}/bin/seat-run %i")
            "seat-eval: seat@ ExecStart must be seat-run %i";
          assert nixpkgs.lib.assertMsg
            (nixpkgs.lib.elem "/var/lib/seat" sc.ReadWritePaths && nixpkgs.lib.elem "/home/dalhaka/factory" sc.ReadWritePaths && nixpkgs.lib.elem "/home/dalhaka/nixos-agent-env" sc.ReadWritePaths && nixpkgs.lib.elem "/home/dalhaka/flakes" sc.ReadWritePaths)
            "seat-eval: seat@ ReadWritePaths must name the operator's trees";
          assert nixpkgs.lib.assertMsg
            (nixpkgs.lib.elem "-/var/lib/secrets" sc.InaccessiblePaths && !(nixpkgs.lib.any (p: nixpkgs.lib.hasPrefix p caBundle) sc.InaccessiblePaths))
            "seat-eval: seat@ must hide /var/lib/secrets without hiding the public CA bundle";
          assert nixpkgs.lib.assertMsg
            (unit.environment.HTTPS_PROXY == "http://10.100.4.1:3132" && unit.environment.OPENROUTER_API_KEY == "injected-by-broker" && unit.environment.NODE_USE_ENV_PROXY == "1" && unit.environment.SEAT_BROKER_GATEWAY == "10.100.4.1" && unit.environment.SEAT_NAMESPACE_ADDRESS == "10.100.4.2" && unit.environment.SSL_CERT_FILE == caBundle)
            "seat-eval: seat@ environment must carry the proxy, CA, placeholder key and gateway";
          assert nixpkgs.lib.assertMsg
            (nixpkgs.lib.any (r: r == "d /var/lib/seat 0750 dalhaka users -") c.systemd.tmpfiles.rules && nixpkgs.lib.any (r: r == "d /var/lib/seat/jobs 0700 dalhaka -") c.systemd.tmpfiles.rules)
            "seat-eval: /var/lib/seat and its jobs spool must be tmpfiles-declared operator-owned";
          assert nixpkgs.lib.assertMsg
            (nixpkgs.lib.hasInfix "iifname \"veb-seat\" tcp dport 43200-43299 ip saddr 10.100.4.1 accept" c.networking.nftables.tables.egress-broker.content)
            "seat-eval: the web accept must be rendered into input-seat";
          assert nixpkgs.lib.assertMsg (c.services.egress-broker.instances.seat.listenPort != c.services.egress-broker.instances.openrouter.listenPort)
            "seat-eval: the seat listenPort must differ from the openrouter lane's";
          pkgs.runCommand "seat-eval-ok" { } "touch $out";
```

`seat-assertion-negative` mirrors `lane-eval`'s sibling at flake.nix:827 (`tryEval` of `seatBadSystem.config.system.build.toplevel.drvPath`, throw on success, `touch $out` on failure).

`seat-polkit-unit` (below) proves the start+stop grant is real.

- [ ] **Step 7: The polkit test** — create `tests/seat/polkit.test.mjs` (adapted from `tests/lane/polkit.test.mjs`, start+stop instead of start-only):

```js
import fs from 'node:fs'
import assert from 'node:assert/strict'

const rulesPath = process.env.SEAT_POLKIT_RULES
if (!rulesPath) {
  throw new Error('polkit.test.mjs: SEAT_POLKIT_RULES must point at the rendered extraConfig (checks.seat-polkit-unit sets it)')
}
const text = fs.readFileSync(rulesPath, 'utf8')

const es6Patterns = [
  [/=>/, 'arrow function ("=>")'], [/\blet\s/, '"let"'], [/\bconst\s/, '"const"'],
  [/\.includes\s*\(/, '.includes('], [/\.endsWith\s*\(/, '.endsWith('],
  [/\.startsWith\s*\(/, '.startsWith('], [/`/, 'template literal (backtick)'],
]
for (const [pattern, label] of es6Patterns) {
  assert.ok(!pattern.test(text), `polkit rule text must be ES5 -- found ${label}`)
}

const rules = []
const polkitStub = { addRule: (fn) => rules.push(fn), Result: { YES: 'yes' }, log: () => {} }
// eslint-disable-next-line no-new-func
new Function('polkit', text)(polkitStub)
assert.ok(rules.length > 0, 'the rendered text must call polkit.addRule at least once')

function decide({ verb, unit }, { user } = {}) {
  const action = {
    id: 'org.freedesktop.systemd1.manage-units',
    lookup: (key) => ({ verb, unit })[key],
  }
  const subject = { user, isInGroup: () => false }
  for (const rule of rules) {
    const result = rule(action, subject)
    if (result !== undefined) return result
  }
  return undefined
}

const UNIT = 'seat@abc.service'
const OPERATOR = 'dalhaka'

assert.equal(decide({ verb: 'start', unit: UNIT }, { user: OPERATOR }), 'yes', 'operator start must be granted')
assert.equal(decide({ verb: 'stop', unit: UNIT }, { user: OPERATOR }), 'yes', 'operator stop must be granted')
for (const verb of ['restart', 'kill']) {
  assert.equal(decide({ verb, unit: UNIT }, { user: OPERATOR }), undefined, `verb "${verb}" must NOT be granted`)
}
assert.equal(decide({ verb: 'start', unit: UNIT }, { user: 'eve' }), undefined, 'a non-operator must NOT be granted')
assert.equal(decide({ verb: 'start', unit: 'seatx@a.service' }, { user: OPERATOR }), undefined, 'a non-seat prefix must NOT be granted')

console.log('polkit.test.mjs: all assertions passed')
```

Wire `seatPolkitRules = pkgs.writeText "seat-polkit-rules.js" self.nixosConfigurations.core.config.security.polkit.extraConfig;` (like `lanePolkitRules` at flake.nix:533) and add the `seat-polkit-unit` check (copy `lane-polkit-unit` at flake.nix:1478–1489, substituting `SEAT_POLKIT_RULES`/`seat-polkit-rules.js`/`tests/seat/polkit.test.mjs`).

- [ ] **Step 8: Extend `host-core` with the seat**

In `flake.nix`'s `host-core` (after the `openrouter` asserts at 705–727), add `si`/`sp` to the `let` and these asserts:

```nix
            si = c.services.egress-broker.instances.seat;
            sp = c.services.egress-broker.policy.seat;
...
          assert nixpkgs.lib.assertMsg (si.allow == [ "openrouter.ai" ])
            "host-core: egress-broker instance 'seat' allow list must be exactly [ \"openrouter.ai\" ]";
          assert nixpkgs.lib.assertMsg (si.inject."openrouter.ai".valueFile == "/var/lib/secrets/openrouter-key")
            "host-core: egress-broker instance 'seat' must inject from /var/lib/secrets/openrouter-key";
          assert nixpkgs.lib.assertMsg (sp.body_patch."openrouter.ai".path_prefixes == [ "/api/v1/chat/completions" ] && sp.deny_paths."openrouter.ai".path_prefixes == [ "/api/v1/messages" ])
            "host-core: seat broker policy must patch chat/completions and deny messages";
```

- [ ] **Step 9: Run all three, then lint**

Run: `nix build .#checks.x86_64-linux.seat-eval -L --no-link`, `nix build .#checks.x86_64-linux.seat-assertion-negative -L --no-link`, `nix build .#checks.x86_64-linux.seat-polkit-unit -L --no-link`, `nix build .#checks.x86_64-linux.host-core -L --no-link`, then `nix develop -c githooks/pre-commit` (and `nix develop -c python3 pkgs/evidence/repomap.py --root . write` + `git add docs/MAP.md` first).
Expected: PASS all; host-core still green with the three new asserts.

- [ ] **Step 10: Commit**

```bash
git add nixosModules/seatLane.nix nixosModules/egressBroker.nix hosts/core/seat.nix hosts/core/default.nix tests/seat/polkit.test.mjs flake.nix docs/MAP.md
nix develop -c git commit -F - <<'MSG'
seat: the seatLane module -- broker instance + seat@ template (operator, netns, placeholder key), polkit + nftables, host wiring (test: seat-eval, seat-assertion-negative, seat-polkit-unit, host-core, lint)
MSG
```

**touches:** nixosModules/seatLane.nix, nixosModules/egressBroker.nix, hosts/core/seat.nix, hosts/core/default.nix, tests/seat/polkit.test.mjs, flake.nix, docs/MAP.md
**acceptance:** seat-eval, seat-assertion-negative, seat-polkit-unit, host-core, lint
**commit subject:** `seat: the seatLane module -- broker instance + seat@ template (operator, netns, placeholder key), polkit + nftables, host wiring (test: seat-eval, seat-assertion-negative, seat-polkit-unit, host-core, lint)`

---

### SB4 (code, M) — `factory-task` and `factory-review` launch the seat through `seat-submit`

**dependsOn:** SB3 (the `seat-submit` CLI this task drives)

**Files:**
- Modify: `tools/factory/seat/factory-task` (the launch block, lines 131–145)
- Modify: `tools/factory/seat/factory-review` (the launch block, lines 157–167)
- Test: `tests/unit/82-seat-factory.bats` (new)

**Interfaces:**
- Consumes: SB3's `seat-submit headless --workspace <w> --dsh-home <d> --model <m> --effort <e> --brief <file> --timeout <s>`; its headless mode blocks until the job's `result.txt` exists, relays `stdout.txt` to stdout (the `FACTORY-*` block flows through), and exits with the job's `exit_code.txt` code.
- Produces: an unchanged `.result` shape on `factory-task` (`extract_field 'FACTORY-RESULT'` … over the teed `$log`, the `run/key/model/effort/route/workspace/branch/head/base/wall_s/exit_code/commits/diffstat/usage` block) and an unchanged `.review.md` on `factory-review` (the `FACTORY-REVIEW verdict=` grep) — keyed by making `seat-submit` the single launch path.

Facts behind the edits (command run: `read tools/factory/seat/factory-task`, `read tools/factory/seat/factory-review`, `grep -n extract_field tools/factory/seat/factory-task`): `factory-task` launches at lines 134–139 (`DSH_HOME=$dsh_home OPENROUTER_REASONING_EFFORT=$effort timeout -- "$timeout_s" dsh-openrouter --model "$model" --headless "$brief"` teed to `$log`), `extract_field` is 152–154, the result block is 170, and the `.result` writer is 211–234; `factory-review` launches identically at 159–164 and greps `FACTORY-REVIEW verdict=` at 171.

- [ ] **Step 1: Write the failing tests** — `tests/unit/82-seat-factory.bats`:

```bats
#!/usr/bin/env bats
# factory-task / factory-review (seat-behind-broker plan SB4): the launch line
# goes through seat-submit, not raw dsh-openrouter, and the .result/.review
# extraction that reads the (now relayed) output is byte-for-byte unchanged.

SEAT="$BATS_TEST_DIRNAME/../../tools/factory/seat"

@test "factory-task launches via seat-submit headless and drops the raw dsh-openrouter launch" {
  run grep -n . "$SEAT/factory-task"
  [ "$status" -eq 0 ]
  [[ "$output" == *"seat-submit headless"* ]]
  [[ "$output" == *"--brief"* ]]
  ! [[ "$output" == *'dsh-openrouter --model "$model" --headless'* ]]
}

@test "factory-review launches via seat-submit headless too" {
  run grep -n . "$SEAT/factory-review"
  [ "$status" -eq 0 ]
  [[ "$output" == *"seat-submit headless"* ]]
  ! [[ "$output" == *'dsh-openrouter --model "$model" --headless "$brief"'* ]]
}

@test "factory-task .result writer still extracts the FACTORY-* block from the teed log" {
  run grep -n . "$SEAT/factory-task"
  [ "$status" -eq 0 ]
  [[ "$output" == *"extract_field()"* ]]
  [[ "$output" == *"grep -E \"^\\\$1"* ]]
  [[ "$output" == *"result_block=\$(printf '%s\\n%s\\n%s\\n%s'"* ]]
  [[ "$output" == *"printf '%s\\n' \"$result_block\""* ]]
}
```

- [ ] **Step 2: Run it to see it fail**

Run: `nix develop -c bats tests/unit/82-seat-factory.bats`
Expected: FAIL — today's `factory-task`/`factory-review` still launch `dsh-openrouter` directly, so the `seat-submit headless` assertion fails and the `!` (absent-line) assertions pass.

- [ ] **Step 3: Implement the launch-line swap**

In `tools/factory/seat/factory-task`, replace the launch block (lines 131, 134–140) with:

```bash
factory_log "launching seat-submit headless --model $model in $ws (timeout ${timeout_s}s, log $log)"
brief_file=$runs_dir/$key.brief.txt
printf '%s\n' "$brief" > "$brief_file"
start_ts=$(date +%s)
set +e
(
  seat-submit headless --workspace "$ws" --dsh-home "$dsh_home" --model "$model" \
    --effort "$effort" --brief "$brief_file" --timeout "$timeout_s"
) 2>&1 | tee -a -- "$log"
exit_code=${PIPESTATUS[0]}
set -e
```

(The `seat-submit` headless path blocks until the job's `result.txt` exists, prints the job's `stdout.txt` — with the final `FACTORY-*` block — to stdout where `tee` captures it, and exits with the job's `exit_code.txt`, so `extract_field` at 152–154, the `status`/`task_rc` mapping at 172–181, and the `.result` writer at 211–234 are untouched.)

The `--dsh-home "$dsh_home"` value is the `factory_seed_dsh_home` result already on `$dsh_home` (line 114 today). The `--model/--effort` are the same `$model`/`$effort` already resolved at lines 78–100.

In `tools/factory/seat/factory-review`, do the same: replace lines 157 and 159–164 with the `seat-submit headless` analogue writing `$runs_dir/$key.review.brief.txt`, teed to `$log`; the `verdict=$(grep -oE '^FACTORY-REVIEW verdict=…' -- "$log" …)` at 171 stays as-is because seat-submit relays the review seat's stdout verbatim.

- [ ] **Step 4: Run the tests to see them pass**

Run: `nix develop -c bats tests/unit/82-seat-factory.bats`
Expected: PASS (3/3).

- [ ] **Step 5: Run the seat-driver suite and lint**

Run: `nix build .#checks.x86_64-linux.seat-unit -L --no-link` then `nix develop -c bats tests/unit` and `nix develop -c githooks/pre-commit`.
Expected: PASS — `tools/factory/seat/factory-task`/`factory-review` stay shellcheck-clean (no new shellcheck; they were already listed) and `tests/unit` (which now includes `82-seat-factory.bats`) passes.

- [ ] **Step 6: Commit**

```bash
git add tools/factory/seat/factory-task tools/factory/seat/factory-review tests/unit/82-seat-factory.bats
nix develop -c git commit -F - <<'MSG'
seat: factory-task and factory-review launch through seat-submit; the .result/.review shapes stay unchanged (test: unit, lint)
MSG
```

**touches:** tools/factory/seat/factory-task, tools/factory/seat/factory-review, tests/unit/82-seat-factory.bats
**acceptance:** unit, lint
**commit subject:** `seat: factory-task and factory-review launch through seat-submit; the .result/.review shapes stay unchanged (test: unit, lint)`

---

### SB5 (code, L) — `seat-vm`: the fake `openrouter.ai` proves the broker, and the web UI reaches the browser

**dependsOn:** SB1, SB2, SB3 (the module, the `--broker` flag, and `seat-submit`/`seat-run` the VM drives)

**Files:**
- Create: `tests/integration/seat-vm.nix`
- Modify: `flake.nix` (`seat-vm = import ./tests/integration/seat-vm.nix { inherit pkgs; egressBrokerModule = self.nixosModules.egressBroker; seatLaneModule = self.nixosModules.seatLane; };`)
- Regenerate: `docs/MAP.md` (the new `seat-vm` check)

**Interfaces:**
- Consumes: SB1's `services.seat-lane` (instance `seat`, `seat@` template, tmpfiles, `seat-submit` on PATH), SB2's `--broker` env contract (`SEAT_BROKER_GATEWAY`, `SEAT_NAMESPACE_ADDRESS`, `HTTPS_PROXY`), SB3's `seat-submit`/`seat-run`.
- Produces: `checks.seat-vm` — the gate the operator runs before the switch.

Facts behind the VM (commands run: `read tests/integration/lane-vm.nix`, `read nixosModules/egressBroker.nix`): `lane-vm.nix` builds a single-host fake upstream (`fakeUpstream`) logging `path`/`Authorization`/body per POST to `/var/log/lane-vm-fake-upstream.log`, a `lane-secret` service writing the key to `/run/lane-secret` 0440 root:egress-broker read by `ExecStartPost`, and the broker's deny reason `path-not-permitted`; the seat VM reuses that pattern with the seat's address block and a fake `dsh-openrouter`.

- [ ] **Step 1: Write the failing VM test** — `tests/integration/seat-vm.nix` (structure follows `lane-vm.nix`, adapted):

The `machine` (one node, like lane-vm) imports `egressBrokerModule` + `seatLaneModule`, enables `services.seat-lane` with `host = "openrouter.test"`, `keyFile = "/run/seat-secret"`, block 10.100.4.x, listenPort 3132; a `seat-secret` service writes `sk-vm-seat-fake-key` to `/run/seat-secret` (0440 root:egress-broker) before the broker's ExecStartPost reads it; a fake `openrouter.test` TLS upstream (single-host certs from a `runCommand`, exactly like `testCerts`) serving `/api/v1/chat/completions` and logging `path`/`Authorization`/body to `/var/log/seat-vm-fake-upstream.log`; and a fake `dsh-openrouter` on the PATH of `seat@` (via `services.seat-lane.harnessPackage` override or a `writeShellScriptBin` in `path`) that — headless — POSTs a chat body to `https://openrouter.test/api/v1/chat/completions` through `$HTTPS_PROXY` with `--cacert "$SSL_CERT_FILE"` and prints a `FACTORY-RESULT status=done` block, and — web — serves `python3 -m http.server "$port" --bind "$SEAT_NAMESPACE_ADDRESS"`. Both modes honour `--broker`/`--bind-namespace`/`--` as the real wrapper would.

The `testScript` (run with `machine.succeed`/`machine.fail`, as lane-vm):

1. Headless job reaches the fake with the real key injected, environment holds only the placeholder:

```python
    machine.wait_for_unit("egress-broker-seat.service")
    machine.succeed("su - operator -c 'seat-submit headless --workspace /var/lib/seat-vm-ws --dsh-home /var/lib/seat-vm-dsh --model test/model --effort high --brief /etc/seat-vm-brief.txt --timeout 120'")
    machine.succeed("grep -q 'Bearer sk-vm-seat-fake-key' /var/log/seat-vm-fake-upstream.log")
    machine.fail("grep -rq 'sk-vm-seat-fake-key' /var/lib/seat/jobs")
    machine.succeed("grep -q 'injected-by-broker' /var/lib/seat/jobs/*/job.json")
```

2. `POST /api/v1/messages` is refused before injection:

```python
    machine.fail("ip netns exec egress-seat curl -s -x http://10.100.4.1:3132 --cacert /var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt https://openrouter.test/api/v1/messages")
    machine.succeed("grep -q 'path-not-permitted' /var/lib/egress-broker/seat/audit.jsonl")
```

3. A request to any other host is dropped by the namespace:

```python
    machine.fail("ip netns exec egress-seat curl -s -x http://10.100.4.1:3132 https://other.test/ -m 10")
    machine.fail("grep -q other.test /var/log/seat-vm-fake-upstream.log")
```

4. The web job's UI answers on `10.100.4.2:<port>` from the host side only:

```python
    machine.succeed("su - operator -c 'seat-submit web --workspace /var/lib/seat-vm-ws --dsh-home /var/lib/seat-vm-dsh --model test/model --effort high --port 43201 --no-start' || true")
```

(adjust: the web job must actually START the unit; use the real `seat-submit web … --port 43201` without `--no-start`, give the fake server a moment, then:)

```python
    machine.succeed("curl -s http://10.100.4.2:43201/ | grep -q .")
    machine.fail("ip netns exec egress-seat curl -s http://10.100.4.2:43201/ -m 5")
```

5. The audit log carries both the injected chat request and the messages denial:

```python
    machine.succeed("grep -q 'chat/completions' /var/lib/egress-broker/seat/audit.jsonl")
    machine.succeed("grep -q 'path-not-permitted' /var/lib/egress-broker/seat/audit.jsonl")
```

(The `/var/lib/seat-vm-ws`/`/var/lib/seat-vm-dsh` dirs and `/etc/seat-vm-brief.txt` are fixture files owned 0700 by `operator` created by a `fixture` service, mirroring lane-vm's fixture handling.)

- [ ] **Step 2: Run it to see it fail**

Run: `nix build .#checks.x86_64-linux.seat-vm -L --no-link`
Expected: FAIL — with the module/`--broker`/`seat-submit` wired (SB1–SB3) but no `seat-vm` check yet, the first run fails at eval (no `seat-vm` attribute) — this is the red; after wiring the `seat-vm = import …` line, the first real `testScript` run fails at the injected-header or denial assertion until the fake/fixtures are complete (each of those failures is shown before the corresponding fix).

- [ ] **Step 3: Wire the check and iterate to green**

Add the `seat-vm = import ./tests/integration/seat-vm.nix { inherit pkgs; egressBrokerModule = self.nixosModules.egressBroker; seatLaneModule = self.nixosModules.seatLane; };` line to `checks.${system}` (beside `lane-vm` at flake.nix:1490), regenerate `docs/MAP.md`, then run and fix until green.

- [ ] **Step 4: Run the full VM gate**

Run: `nix build .#checks.x86_64-linux.seat-vm -L --no-link`
Expected: PASS (all five assertions above).

- [ ] **Step 5: Lint and commit**

Run: `nix develop -c githooks/pre-commit` (with `docs/MAP.md` added), then:

```bash
git add tests/integration/seat-vm.nix flake.nix docs/MAP.md
nix develop -c git commit -F - <<'MSG'
seat: seat-vm proves the broker injects the real key behind a placeholder env, denies messages, drops other hosts, and serves the web UI on 10.100.4.2 from the host only (test: seat-vm, lint)
MSG
```

**touches:** tests/integration/seat-vm.nix, flake.nix, docs/MAP.md
**acceptance:** seat-vm, lint
**commit subject:** `seat: seat-vm proves the broker injects the real key behind a placeholder env, denies messages, drops other hosts, and serves the web UI on 10.100.4.2 from the host only (test: seat-vm, lint)`

---

### SB6 (docs, S) — the migration: backup rewire, the runbook's switch/acceptance/rollback, and every caller of the old key

**dependsOn:** SB1 (the `seat` instance and `/var/lib/seat` spool exist to back up; the `host-core` seat asserts already landed)

**Files:**
- Modify: `hosts/core/proton-backup.nix` (add `/var/lib/seat` to `paths`; add `/var/lib/seat/jobs/*/dsh-home/sessions` to `exclude`)
- Modify: `flake.nix` (`host-core`: assert `/var/lib/seat` ∈ `paths` and the sessions exclusion ∈ `exclude`)
- Modify: `docs/runbooks/lanes.md` (rewrite the "Working with dsh yourself" section: one-command seat via `seat-submit`, the migration delete, the rollback)
- Modify: `tools/factory/seat/launch-today.sh` (header comment, lines 1–5 — it no longer "spends the key"; the factory runs it dispatches now go through seat-submit)
- Modify: `hosts/core/agent-prereqs.nix` (stale comment at lines 16–19: "Reads its key from ~/.config/openrouter/key.")
- Modify: `tools/factory/seat/README.md` (the "no broker, no netns, no lane" sentence at line 21, and any key-file paragraph)

**Interfaces:** none (documentation + host backup wiring only).

Facts behind the edits (commands run: `grep -rn 'dsh-openrouter|openrouter/key|launch-today' tools/ hosts/`, `read hosts/core/proton-backup.nix`, `grep -n exclude nixosModules/protonBackup.nix`, `read docs/runbooks/lanes.md:228-300`, `read tools/factory/seat/launch-today.sh`): the four in-repo callers that expect the key or the old launch are `dsh-openrouter.sh` (handled by SB2), `factory-task`/`factory-review` (SB4), `launch-today.sh` (dispatches `factory-wave`, header comment line 4), and `hosts/core/agent-prereqs.nix` (comment lines 16–19); `services.proton-backup.paths` is an explicit include list (hosts/core/proton-backup.nix:29–42) and `services.proton-backup.exclude` defaults to `[ "**/.pytest_cache" "**/.ruff_cache" "/home/*/.cache" ]` (nixosModules/protonBackup.nix:35–42).

- [ ] **Step 1: Write the failing host-core backup assertions**

Add to `flake.nix`'s `host-core` (after the seat asserts from SB1):

```nix
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "/var/lib/seat" c.services.proton-backup.paths)
            "host-core: /var/lib/seat must join the backup paths (the operator's briefs)";
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "/var/lib/seat/jobs/*/dsh-home/sessions" c.services.proton-backup.exclude)
            "host-core: /var/lib/seat/jobs/*/dsh-home/sessions must be excluded from backup (bulk transcripts)";
```

- [ ] **Step 2: Run to see it fail**

Run: `nix build .#checks.x86_64-linux.host-core -L --no-link`
Expected: FAIL — `/var/lib/seat` is not among the eleven `paths` and no sessions exclusion exists yet.

- [ ] **Step 3: Rewire the backup**

In `hosts/core/proton-backup.nix`, add `/var/lib/seat` to `services.proton-backup.paths` and define `exclude` (restating the module default so the define replaces, not drops, it):

```nix
      "/var/lib/evidence"
      "/var/lib/seat"
    ];
    exclude = [
      "**/.pytest_cache"
      "**/.ruff_cache"
      "/home/*/.cache"
      "/var/lib/seat/jobs/*/dsh-home/sessions"
    ];
```

- [ ] **Step 4: Write the operator runbook (switch / acceptance / rollback)**

Replace `docs/runbooks/lanes.md`'s "Working with dsh yourself" section (lines 228–299) with three explicit blocks:

**Switch (operator, once, after `nix build .#checks.x86_64-linux.seat-vm -L --no-link` is green):**

```bash
sudo nixos-rebuild switch --flake ~/nixos-agent-env#core    # the operator's action, never the factory's
```

**Acceptance (operator):**

```bash
seat-submit headless --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter --model deepseek/deepseek-v4-pro-0813 --effort high --brief /tmp/seat-brief.txt --timeout 600
seat-submit web --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter --model deepseek/deepseek-v4-pro-0813 --effort high --port 43201
# open http://10.100.4.2:43201/ ; then confirm the broker audited both:
sudo grep -c 'openrouter.ai' /var/lib/egress-broker/seat/audit.jsonl
```

(expect at least one `chat/completions` record; the headless job's `Authorization` header was injected — `grep Authorization` shows the `Bearer` form the broker added)

**Migration + rollback:**

```bash
rm ~/.config/openrouter/key    # the one-command delete; after this the old non-broker path dies with the existing "no key" message
# rollback: the key file is the operator's own copy -- restore it from Proton Pass with the original one-liner
# (umask 077; mkdir -p ~/.config/openrouter; IFS= read -r -s k; printf '%s' "$k" > ~/.config/openrouter/key; echo saved)
# and the seat stays enabled: the non-broker path and seat-submit coexist until the file is gone (spec §7)
```

Also update the section's caller list to note `factory-task`/`factory-review`/`launch-today.sh` now reach OpenRouter only through `seat-submit`.

- [ ] **Step 5: Fix the stale caller comments**

`tools/factory/seat/launch-today.sh` line 4: replace "Spends the operator's OpenRouter key." with "Jobs run through the seat broker (seat-submit), never the plaintext key." `hosts/core/agent-prereqs.nix` lines 16–19: replace "Reads its key from `~/.config/openrouter/key`." with "The key is injected by the seat broker; the wrapper runs `--broker` inside the seat unit." `tools/factory/seat/README.md` line 21: replace "key (`~/.config/openrouter/key`) — there is no broker, no netns, no lane." with "key, injected by the seat broker; the scripts run through `seat-submit`."

- [ ] **Step 6: Run host-core and lint**

Run: `nix build .#checks.x86_64-linux.host-core -L --no-link` then `nix develop -c githooks/pre-commit`.
Expected: PASS both (shellcheck still clean on the tweaked comments/README).

- [ ] **Step 7: Commit**

```bash
git add hosts/core/proton-backup.nix flake.nix docs/runbooks/lanes.md tools/factory/seat/launch-today.sh hosts/core/agent-prereqs.nix tools/factory/seat/README.md
nix develop -c git commit -F - <<'MSG'
docs: the seat migration -- back up /var/lib/seat minus transcripts, runbook switch/acceptance/rollback, and every stale caller of the old key (test: host-core, lint)
MSG
```

**touches:** hosts/core/proton-backup.nix, flake.nix, docs/runbooks/lanes.md, tools/factory/seat/launch-today.sh, hosts/core/agent-prereqs.nix, tools/factory/seat/README.md
**acceptance:** host-core, lint
**commit subject:** `docs: the seat migration -- back up /var/lib/seat minus transcripts, runbook switch/acceptance/rollback, and every stale caller of the old key (test: host-core, lint)`

---

## Operator (separated from the factory's work)

The factory's build work ends at SB6's commit. The remaining steps are the operator's alone — the factory never runs them:

1. **Switch** (SB6's runbook, one command): `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core`.
2. **Acceptance** (one headless + one web job through the units, SB6's runbook): confirm the audit log shows injected requests and the web UI answers on `10.100.4.2:<port>`.
3. **Rollback safety** (spec §7): the key file at `~/.config/openrouter/key` is deleted only after the acceptance passes; until then the old non-broker path and `seat-submit` coexist. Restore from Proton Pass with the original one-liner if the switch is reverted.