# The seat behind a broker — implementation plan (2026-09-05)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) and `tools/factory/dark-factory.js` both read the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and `commit subject`.

**Goal:** the operator's DeepSeek seat (`dsh-openrouter`) gets its OpenRouter key the way the lanes do — injected by a dedicated egress-broker instance `seat` from the root-only `/var/lib/secrets/openrouter-key` — so no agent process ever holds the key and the plaintext `~/.config/openrouter/key` goes away; `factory-task` submits seat jobs instead of launching the wrapper directly. Closes claim `seat-key-exception-undecided`.

**Architecture:** one new NixOS module (`nixosModules/seat.nix`) declares `services.egress-broker.instances.seat` (allowlist `openrouter.ai` only, credential injection, `/api/v1/messages` denied before injection, address block 10.100.4.x), a system unit template `seat@<job>` that runs as the operator inside the broker's netns with only a placeholder `OPENROUTER_API_KEY`, a polkit rule granting the operator start **and** stop on `seat@*`, and tmpfiles for `/var/lib/seat`. Jobs are directories under `/var/lib/seat/jobs/<id>/` written by a new `seat-submit`/`seat-wait` CLI (`pkgs/seat/seat-submit.py`) and executed by `seat-run` (`pkgs/seat/seat-run.py`), which execs `dsh-openrouter --broker`. The wrapper's new `--broker` mode never touches the key file and refuses to run outside the seat namespace; `--bind-namespace` (only valid with `--broker`) binds the web UI to the namespace address, reached from the host through a new per-instance `exposePort` accept in the broker's nftables forward chain. `factory-task` calls `seat-submit` and reads the same `.result` shape from the job's log.

**Tech Stack:** NixOS modules + tmpfiles + polkit (ES5), nftables, Python 3 stdlib only (`pkgs/seat`), bash (the wrapper), bats (`tests/unit`), pytest (`tests/seat`), a NixOS VM test (`tests/integration/seat-vm.nix`), treefmt/ruff/shellcheck/statix/deadnix.

**Spec:** `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md` (approved in approach, 2026-09-05 evening). Executors read it together with this plan; invariants touched are brief §3 (the broker is the only route; credentials never in agent hands), so the VM test (`seat-vm`) is the gate and the operator switches.

## What exists today (inventory, 2026-09-05)

Every fact below names the command that produced it; the full list is also in the appendix.

- `nixosModules/egressBroker.nix` renders one mitmproxy instance per `services.egress-broker.instances.<name>`: netns `/run/netns/egress-<name>`, veth `veb-<name>`/`ven-<name>` (`grep -n "veb-\|ven-" nixosModules/egressBroker.nix` → lines 163–191, 209–217), `--mode regular` proxy at `hostAddress:listenPort` (line 289–292), inject defaults `header = "Authorization"`, `prefix = "Bearer "` (lines 108–115), audit at `/var/lib/egress-broker/<name>/audit.jsonl` (line 29), and a public CA bundle published at `/var/lib/egress-broker-ca-bundle/<name>/ca-bundle.crt` (lines 256–279). Its forward chain drops **all** forwarded traffic on `veb-<name>` today (lines 187–191) — the seat's web UI needs the new `exposePort` accept (S3).
- `nixosModules/modelLane.nix` is the pattern the seat mirrors: template unit with `NetworkNamespacePath` (line 261), the proxy/CA environment (lines 220–239), hardening block (lines 258–299), tmpfiles `z <keyFile> 0440 root egress-broker -` (line 202), and the ES5 polkit rule granting **start only** (lines 308–325). `dsh` ignores `HTTPS_PROXY` unless `NODE_USE_ENV_PROXY=1` and the `lib/proxy-shim.cjs` preload are set (comment lines 226–234; the same is asserted by `lane-eval`, `grep -n "NODE_USE_ENV_PROXY\|proxy-shim" flake.nix` → lines 1424–1429).
- Address blocks in use (`grep -rn "10\.100\." --include="*.nix" hosts/ nixosModules/ tests/`): 10.100.0.x broker-vm fixture, 10.100.1.x cowork (`nixosModules/cowork.nix:174-175`), 10.100.2.x reserved for media (comment, `hosts/core/lanes.nix:6`), 10.100.3.x the openrouter lane (`hosts/core/lanes.nix:14-15`), 10.100.9.x `laneEvalSystem`, 10.100.30.x `lane-vm`. **10.100.4.x is free** — the spec assigns it to the seat. Broker listen ports in use: 3128 (default, `nixosModules/egressBroker.nix:47-49`), 3129 (cowork, `nixosModules/cowork.nix:176`), 3131 (lane, `hosts/core/lanes.nix:16`), 3199 (test fixtures); `grep -rn "3141\|8480" --include="*.nix" --include="*.sh" --include="*.py" .` has no hits — the seat takes listen port **3141** and web port **8480**.
- `pkgs/dsh-openrouter/dsh-openrouter.sh` reads the key at lines 220–243: `${OPENROUTER_KEY_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/openrouter/key}`, must be a regular file owned by the caller with mode 0600/0400, else `die 4`; exit codes 2 usage / 3 refused workspace / 4 key problem / 5 bad value (usage text, line 65). `--host` passthrough is rejected at lines 142–148; the web mode execs `node --expose-internals bin.js --profile web --patch "$overlay" --host 127.0.0.1 "$@"` (line 580) and the headless mode `node bin.js --profile headless --patch "$overlay" "$task"` (line 567). It does **not** set `NODE_OPTIONS`/`NODE_USE_ENV_PROXY` today (`grep -n "NODE_OPTIONS\|NODE_USE_ENV_PROXY" pkgs/dsh-openrouter/dsh-openrouter.sh` → no hits) — the seat unit sets them, as the lane unit does.
- `tools/factory/seat/factory-task` launches `dsh-openrouter --model "$model" --headless "$brief"` under `timeout` at line 138 and writes `~/factory/runs/<run>/<KEY>.result` at lines 211–234 (FACTORY-RESULT block plus run/key/model/effort/route/workspace/branch/head/base/wall_s/exit_code, commit log, diffstat, usage). That shape does not change.
- Every caller of the key path (`grep -rn "openrouter/key\|\.config/openrouter" -l .`): the wrapper itself; `hosts/core/agent-prereqs.nix:19` (installs the package); `tools/factory/seat/factory-task:138` (launches it); `tools/factory/seat/launch-today.sh` (via `factory-wave` → `factory-task`); `tools/factory/seat/README.md` and `docs/runbooks/lanes.md` (docs); `tests/unit/70-dsh-openrouter.bats` (tests); the forbidden-prefix lists in `pkgs/lane/lane-submit.py:52-62`, `pkgs/dsh-openrouter/dsh-openrouter.sh:202-212` and `pkgs/dsh-openrouter/hook-guard.py` (these name `~/.config/openrouter` as a *workspace* refusal — they stay; a nonexistent directory simply never matches).
- The backup (`hosts/core/proton-backup.nix:29-42`) does not include `/var/lib/seat` yet; `services.proton-backup.exclude` defaults to `.pytest_cache`/`.ruff_cache`/`/home/*/.cache` (`nixosModules/protonBackup.nix:35-42`). The lane's precedent: its `dsh` job kind writes the per-job `dsh-home` under the job dir (`pkgs/lane/lane-run.py:378`), and `/var/lib/lanes` is not a restic path at all. `core-backup-wiring` (`flake.nix:1818-1839`) throws unless every restic path is named in `docs/runbooks/backup.md`.
- Check names this plan uses (`docs/MAP.md` lines 28–67): existing `host-core`, `core-backup-wiring`, `unit`, `lint`, `lane-polkit-unit`, `integration`; new `seat-unit`, `seat-eval`, `seat-assertion-negative`, `seat-vm`. The eval/negative patterns copied below are `lane-eval` (`flake.nix:1283-1450`), `lane-assertion-negative` (`flake.nix:1451-1458`), `lane-unit` (`flake.nix:1459-1477`), `lane-polkit-unit` (`flake.nix:1478-1489`, fed by `lanePolkitRules` at `flake.nix:533`), and `lane-vm` (`flake.nix:1490-1494` + `tests/integration/lane-vm.nix`).

## Decisions

- **D1 One module, one seat.** `nixosModules/seat.nix` declares `services.seat` as a flat option set with `enable` — there is exactly one seat (the operator's), so no `attrsOf` indirection. The module owns: the broker instance, tmpfiles, the `seat@` template, the polkit rule, `environment.systemPackages` for `seat-submit`/`seat-wait`, and all assertions.
- **D2 Fixed numbers.** Address block 10.100.4.x per the spec: host `10.100.4.1`, namespace `10.100.4.2`. Broker listen port `3141`; web UI port `8480` (both free — see the inventory). The web port must be **fixed**, not OS-assigned, because the nftables forward accept names it; the unit passes `--port $SEAT_WEB_PORT` and prints the URL.
- **D3 No `bodyPatch` on the seat instance.** The spec (§1) lists allowlist, inject, address block, audit and deny paths — nothing else. Zero-data-retention for the seat stays the OpenRouter **account** setting the operator already flipped (`dsh-openrouter.sh` header lines 26–30; `docs/runbooks/lanes.md` "OpenRouter account settings"). `denyPaths."openrouter.ai".pathPrefixes = [ "/api/v1/messages" ]` is set exactly as the lane does (`nixosModules/modelLane.nix:181-183`).
- **D4 `seat@` is `Type = "simple"`.** One template serves both modes: headless jobs exit, the web UI runs until stopped. `systemctl start seat@<id>` returns once the process forks, so `seat-submit` prints the job id immediately and `seat-wait <id>` polls the job dir's `done` marker (written by `seat-run`'s exit path, including on SIGTERM). This is also why the polkit rule grants **stop**: `factory-task`'s timeout must be able to kill a hung seat job (spec §2 grants start and stop; the lane needs only start because its `oneshot` unit blocks `systemctl start` for the job's whole life — `pkgs/lane/lane-submit.py:363-389`).
- **D5 The placeholder contract is three environment variables.** The unit sets `OPENROUTER_API_KEY=injected-by-broker`, `SEAT_BROKER_GATEWAY=10.100.4.1`, `SEAT_NAMESPACE_ADDR=10.100.4.2` (plus `SEAT_WEB_PORT`, `SEAT_STATE_DIR`). The wrapper under `--broker` refuses to run unless `SEAT_BROKER_GATEWAY` is set **and** `ip route show default` contains `via <gateway>` — a mis-launch outside the netns would otherwise send the placeholder to OpenRouter as if it were a key, bypassing allowlist, deny paths and audit. A module assertion pins the placeholder value so a real key in the unit's environment fails the build (`seat-assertion-negative` proves it).
- **D6 `exposePort` on the broker instance.** `nixosModules/egressBroker.nix` gains a per-instance option `exposePort` (`nullOr port`, default `null`). When set, the forward chain accepts `oifname veb-<name>` to `<namespaceAddress>:<port>` and the established return traffic, before the existing drops. Host-side processes reach `http://10.100.4.2:8480`; nothing else changes — the broker's own input chain (host-namespace drop included) is untouched.
- **D7 `factory-task` tolerates both seats (spec §7).** `FACTORY_SEAT=seat|direct`, default `seat`. `seat` submits through `seat-submit` and waits with `seat-wait`; `direct` is today's code path verbatim. After the operator deletes the key file, `direct` dies with the wrapper's existing "no key" message — an acceptable, audible failure.
- **D8 Backup.** `/var/lib/seat` joins the restic paths and the exclude list gains `/var/lib/seat/jobs/*/dsh-home/sessions` (spec §3: briefs and results are the operator's data; session transcripts are regenerable bulk). `docs/runbooks/backup.md` names both, or `core-backup-wiring` throws.
- **D9 The guard is untouched (spec §6).** `pkgs/dsh-openrouter/hook-guard.py` is not modified by any task: the same wrapper writes the same `hooks.json`, so the deny-only guard works identically inside the unit; its `~/.config/openrouter` workspace-refusal entry becomes moot once the key file is deleted and stays. No task below touches `hook-guard.py` or the three forbidden-prefix lists.

## Global Constraints

- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown, no reading `/var/lib/secrets/*` or `~/.config/openrouter/key`. The operator switches and runs the acceptance (§"Operator" below).
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null` a gated command; commit subjects `<area>: summary (test: <check names>)` with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer.
- TDD: the failing check first, shown red, then green. A load-bearing test counts only once it has been shown to fail; a test that cannot fail is a `vacuous-test` finding. Red before green is shown for every task below.
- **The Python blocks below are specifications, not byte-exact files.** `ruff format` (88 columns, via treefmt and `checks.lint`) may rewrap them; after writing each block run `nix develop -c ruff format <paths>`, re-run the task's tests, then the lint gate. A reformatting-only difference is not a deviation.
- Python is stdlib only in `pkgs/seat` (same rule as `pkgs/lane`); tests may use pytest.
- **One writer per tree; `touches` is a contract** — a file outside it is a deviation to report, not to write. Mutation targets for the reviewer are exactly each task's `touches` line.
- Nix style: statix rejects `{ ... }:` module headers (write `_: ` or name the args); polkit rules are ES5 (duktape): no arrow functions, `let`/`const`, template literals, `.includes`/`.startsWith`/`.endsWith` — `tests/lane/polkit.test.mjs` scans for these.
- No secrets in the repo: fixture keys are named `vm-seat-fake-key`-style and asserted never to leave the broker.
- Shell pasted into `githooks/pre-commit` is reformatted by shfmt: paste, run treefmt, then copy the formatted text into any Nix string that must stay identical.

## Waves

Waves follow `dependsOn` (Kahn's algorithm; two tasks in one wave that edit the same file serialise in key order).

| wave | tasks | dependsOn | notes |
|---|---|---|---|
| 1 | S1, S2 | — | disjoint files: S1 creates `pkgs/seat` + `tests/seat` and edits `flake.nix` + `githooks/pre-commit`; S2 touches only `pkgs/dsh-openrouter/dsh-openrouter.sh` + `tests/unit/70-dsh-openrouter.bats` (never `flake.nix`) |
| 2 | S3, S4 | S3: [S1]; S4: [S1] | S3 edits `flake.nix` (module export, fixtures, seat-eval, seat-assertion-negative) — serialised after S1's flake.nix edit; S4 edits `tools/factory/seat/factory-task` + `tests/unit/80-seat-driver.bats` — disjoint from S3 |
| 3 | S5 | S5: [S1, S2, S3] | the VM gate drives the real wrapper, module and CLI together; edits `flake.nix` again (serialised after S3) |
| 4 | S6 | S6: [S3, S5] | host wiring: `hosts/core/*`, `flake.nix` host-core (serialised after S5), `tests/lane/polkit.test.mjs`, runbooks |

Every task edits at most one of the contended files per wave; `flake.nix` is touched by S1 → S3 → S5 → S6 in strict sequence. `docs/runbooks/lanes.md`, `tests/unit/70-dsh-openrouter.bats`, `tests/unit/80-seat-driver.bats`, `tests/lane/polkit.test.mjs` each have exactly one writer.

## Operator

One switch, after wave 4 lands. Nothing in waves 1–4 needs the switch to be built or tested.

1. **Switch:** `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core` — starts `egress-netns-seat.service` and `egress-broker-seat.service`, creates `/var/lib/seat`, puts `seat-submit`/`seat-wait` on PATH, loads the polkit rule, adds `/var/lib/seat` to the nightly restic paths. The lane and the deprecated direct-key `dsh-openrouter` are untouched by the switch.
2. **Acceptance — one headless job:** `printf 'Reply with exactly: seat-ok' > /tmp/seat-brief && seat-submit --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter --mode headless --brief-file /tmp/seat-brief --model deepseek/deepseek-v4-flash` → prints a job id; `seat-wait <id>` prints the run; then `journalctl -u seat@<id>.service --no-pager | tail` and `jq -c 'select(.verdict=="allow")' /var/lib/egress-broker/seat/audit.jsonl | tail -3` show the brokered, injected requests (the job's environment held only `injected-by-broker`).
3. **Acceptance — one web job:** `seat-submit --workspace ~ --dsh-home ~/.local/share/dsh-openrouter --mode web --brief-file /tmp/seat-brief --model deepseek/deepseek-v4-flash` → open `http://10.100.4.2:8480` (the unit prints the URL to the journal and the job's `output.log`); when done, `systemctl stop seat@<id>.service` (the polkit stop grant).
4. **Delete the plaintext key (the runbook's one command):** `shred -u ~/.config/openrouter/key` — Proton Pass stays the vault of record for the human copy. From this moment the deprecated direct path dies with the wrapper's existing "no key" message, by design.
5. **Rollback:** `sudo nixos-rebuild switch --rollback` (previous generation: no seat instance, no seat units, `factory-task`'s `FACTORY_SEAT=direct` still works while the key file exists). If the key file was already deleted, restore it once from Proton Pass with the recipe in `docs/runbooks/lanes.md` ("One-time: the key file").

---

## Tasks

### S1 (code, M) — `pkgs/seat`: `seat-submit`/`seat-wait` CLI and the `seat-run` unit runner, unit-tested

**dependsOn:** none

**Files:**
- Create: `pkgs/seat/seat-submit.py`, `pkgs/seat/seat-run.py`, `pkgs/seat/seat-run.nix`, `tests/seat/test_seat_submit.py`, `tests/seat/test_seat_run.py`
- Modify: `flake.nix` (`packages.seat-run`; `checks.seat-unit`; the `lint` ruff lists), `githooks/pre-commit` (the ruff lists)

**Interfaces:**
- Produces the CLI contract S3's module wraps and S4's `factory-task` calls:
  - `seat-submit --workspace DIR --dsh-home DIR --mode headless|web --brief-file FILE --model ID [--effort E]` → creates `${SEAT_STATE_DIR:-/var/lib/seat}/jobs/<id>/` (mode 0700, owner = the invoking operator) holding one file per field — `workspace`, `dsh-home`, `mode`, `brief` (the brief *text*), `model`, `effort` (each 0600) — starts `seat@<id>.service` via `systemctl`, prints `<id>` (12 lowercase hex chars, `uuid.uuid4().hex[:12]`, the same id shape `lane-submit` uses at `pkgs/lane/lane-submit.py:299`). Exit 0; usage errors exit 2 with a `seat-submit:` message on stderr.
  - `seat-wait <id> [--timeout S] [--poll-interval S]` → polls `jobs/<id>/done`; once it exists, prints `jobs/<id>/output.log` verbatim to stdout and exits 0; on timeout prints `seat-wait: timed out waiting for <path>` to stderr and exits 1.
- Produces the unit runner S3's `seat@.service` execs: `seat-run <job-id>` reads the six job files, cds to `workspace`, sets `DSH_HOME` and `OPENROUTER_REASONING_EFFORT`, and runs `dsh-openrouter --broker --model <model> --headless <brief>` (headless) or `dsh-openrouter --broker --model <model> --bind-namespace -- --no-open --port $SEAT_WEB_PORT` (web). stdout+stderr stream to the journal **and** `jobs/<id>/output.log`; on any exit (including SIGTERM) it writes `jobs/<id>/done` = `{"exit_code": N, "ts": <epoch float>}` and, for web mode, first prints the line `seat: web UI at http://<SEAT_NAMESPACE_ADDR>:<SEAT_WEB_PORT> (reachable from the host only)`.
- Consumes nothing from other tasks; S3 provides the unit's environment (`SEAT_WEB_PORT`, `SEAT_NAMESPACE_ADDR`, `SEAT_STATE_DIR`).

- [ ] **Step 1: Write the failing tests** — `tests/seat/test_seat_submit.py`:

```python
"""seat-submit / seat-wait unit tests (plan 2026-09-05-seat-behind-broker, S1).

The module is imported in-process (same idiom as tests/lane/
test_lane_submit.py): subprocess.run -- the `systemctl start` call at the
end of a submit -- is monkeypatched out, and SEAT_STATE_DIR points at a
tmp_path.
"""

import importlib.util
import json
import os
import pathlib
import stat
import sys

import pytest

HERE = pathlib.Path(__file__).resolve()


def load_module():
    src = HERE.parents[2] / "pkgs" / "seat" / "seat-submit.py"
    spec = importlib.util.spec_from_file_location("seat_submit", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["seat_submit"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def mod(monkeypatch, tmp_path):
    monkeypatch.setenv("SEAT_STATE_DIR", str(tmp_path))
    return load_module()


@pytest.fixture()
def no_systemctl(monkeypatch):
    """Replaces subprocess.run (the `systemctl start` at the end of
    cmd_submit) with a stub that records its argv."""
    calls = []

    def fake_run(argv, **_kw):
        calls.append(argv)

        class R:
            returncode = 0

        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    return calls


def write_brief(tmp_path, text="do the thing"):
    brief = tmp_path / "brief.txt"
    brief.write_text(text)
    return brief


def args(tmp_path, brief, *extra):
    return [
        "--workspace",
        str(tmp_path),
        "--dsh-home",
        str(tmp_path / "dsh-home"),
        "--mode",
        "headless",
        "--brief-file",
        str(brief),
        "--model",
        "test/model",
        *extra,
    ]


def test_submit_writes_the_six_job_files_0700_and_prints_the_id(
    mod, no_systemctl, tmp_path, capsys
):
    brief = write_brief(tmp_path)
    rc = mod.cmd_submit(args(tmp_path, brief, "--effort", "high"))
    assert rc == 0
    job_id = capsys.readouterr().out.strip()
    assert len(job_id) == 12 and all(c in "0123456789abcdef" for c in job_id)
    jobdir = tmp_path / "jobs" / job_id
    assert stat.S_IMODE(jobdir.stat().st_mode) == 0o700
    assert (jobdir / "workspace").read_text() == str(tmp_path)
    assert (jobdir / "dsh-home").read_text() == str(tmp_path / "dsh-home")
    assert (jobdir / "mode").read_text() == "headless"
    assert (jobdir / "brief").read_text() == "do the thing"
    assert (jobdir / "model").read_text() == "test/model"
    assert (jobdir / "effort").read_text() == "high"
    for name in ("workspace", "dsh-home", "mode", "brief", "model", "effort"):
        assert stat.S_IMODE((jobdir / name).stat().st_mode) == 0o600, name
    assert no_systemctl == [["systemctl", "start", f"seat@{job_id}.service"]]


def test_submit_defaults_effort_to_medium(mod, no_systemctl, tmp_path, capsys):
    brief = write_brief(tmp_path)
    assert mod.cmd_submit(args(tmp_path, brief)) == 0
    job_id = capsys.readouterr().out.strip()
    assert (tmp_path / "jobs" / job_id / "effort").read_text() == "medium"


def test_submit_refuses_a_bad_mode_and_never_starts_a_unit(
    mod, no_systemctl, tmp_path, capsys
):
    brief = write_brief(tmp_path)
    argv = args(tmp_path, brief)
    argv[argv.index("headless")] = "telepathic"
    assert mod.cmd_submit(argv) == 2
    assert "mode" in capsys.readouterr().err
    assert no_systemctl == []


def test_submit_refuses_a_missing_brief_file(mod, no_systemctl, tmp_path, capsys):
    rc = mod.cmd_submit(args(tmp_path, tmp_path / "no-such-brief"))
    assert rc == 2
    assert "brief" in capsys.readouterr().err
    assert no_systemctl == []


def test_submit_refuses_a_workspace_that_is_not_a_directory(
    mod, no_systemctl, tmp_path, capsys
):
    brief = write_brief(tmp_path)
    argv = args(tmp_path, brief)
    argv[argv.index("--workspace") + 1] = str(tmp_path / "not-there")
    assert mod.cmd_submit(argv) == 2
    assert "workspace" in capsys.readouterr().err
    assert no_systemctl == []


def test_wait_prints_the_output_log_once_done_exists(mod, tmp_path, capsys):
    jobdir = tmp_path / "jobs" / "abc123abc123"
    jobdir.mkdir(parents=True)
    (jobdir / "output.log").write_text("line one\nFACTORY-RESULT status=done\n")
    (jobdir / "done").write_text(json.dumps({"exit_code": 0, "ts": 1.0}))
    assert mod.cmd_wait(["abc123abc123", "--timeout", "1"]) == 0
    out = capsys.readouterr().out
    assert "line one" in out and "FACTORY-RESULT status=done" in out


def test_wait_times_out_with_exit_1(mod, tmp_path, capsys):
    rc = mod.cmd_wait(["never000never", "--timeout", "0.2", "--poll-interval", "0.05"])
    assert rc == 1
    assert "timed out" in capsys.readouterr().err
```

`tests/seat/test_seat_run.py`:

```python
"""seat-run unit tests (plan 2026-09-05-seat-behind-broker, S1).

A stub `dsh-openrouter` on PATH records argv and the environment it was
handed; SEAT_STATE_DIR points at tmp_path. The stub prints one line so the
output.log/done contract is exercised end to end.
"""

import importlib.util
import json
import os
import pathlib
import stat
import sys

HERE = pathlib.Path(__file__).resolve()


def load_module():
    src = HERE.parents[2] / "pkgs" / "seat" / "seat-run.py"
    spec = importlib.util.spec_from_file_location("seat_run", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["seat_run"] = mod
    spec.loader.exec_module(mod)
    return mod


def make_job(tmp_path, monkeypatch, mode="headless"):
    monkeypatch.setenv("SEAT_STATE_DIR", str(tmp_path))
    monkeypatch.setenv("SEAT_WEB_PORT", "8480")
    monkeypatch.setenv("SEAT_NAMESPACE_ADDR", "10.100.4.2")
    ws = tmp_path / "ws"
    ws.mkdir()
    jobdir = tmp_path / "jobs" / "abc123abc123"
    jobdir.mkdir(parents=True)
    fields = {
        "workspace": str(ws),
        "dsh-home": str(tmp_path / "dsh-home"),
        "mode": mode,
        "brief": "the brief text",
        "model": "test/model",
        "effort": "low",
    }
    for name, value in fields.items():
        (jobdir / name).write_text(value)
    stub = tmp_path / "bin" / "dsh-openrouter"
    stub.parent.mkdir()
    stub.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$@\" > \"$CAPTURE/argv\"\n"
        "printf 'DSH_HOME=%s EFFORT=%s\\n' \"$DSH_HOME\" "
        "\"$OPENROUTER_REASONING_EFFORT\" > \"$CAPTURE/env\"\n"
        "echo STUB-OUTPUT\n"
    )
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{stub.parent}:{os.environ['PATH']}")
    monkeypatch.setenv("CAPTURE", str(tmp_path))
    return jobdir


def test_headless_runs_broker_headless_with_the_job_fields(tmp_path, monkeypatch):
    make_job(tmp_path, monkeypatch)
    rc = load_module().main(["abc123abc123"])
    assert rc == 0
    argv = (tmp_path / "argv").read_text().splitlines()
    assert argv == [
        "--broker",
        "--model",
        "test/model",
        "--headless",
        "the brief text",
    ]
    env = (tmp_path / "env").read_text()
    assert f"DSH_HOME={tmp_path}/dsh-home" in env
    assert "EFFORT=low" in env
    jobdir = tmp_path / "jobs" / "abc123abc123"
    assert "STUB-OUTPUT" in (jobdir / "output.log").read_text()
    done = json.loads((jobdir / "done").read_text())
    assert done["exit_code"] == 0 and done["ts"] > 0


def test_web_mode_passes_bind_namespace_and_the_fixed_port(tmp_path, monkeypatch):
    jobdir = make_job(tmp_path, monkeypatch, mode="web")
    rc = load_module().main(["abc123abc123"])
    assert rc == 0
    argv = (tmp_path / "argv").read_text().splitlines()
    assert argv == [
        "--broker",
        "--model",
        "test/model",
        "--bind-namespace",
        "--",
        "--no-open",
        "--port",
        "8480",
    ]
    log = (jobdir / "output.log").read_text()
    assert "http://10.100.4.2:8480" in log
    assert json.loads((jobdir / "done").read_text())["exit_code"] == 0


def test_a_failing_stub_is_recorded_in_done(tmp_path, monkeypatch):
    jobdir = make_job(tmp_path, monkeypatch)
    stub = tmp_path / "bin" / "dsh-openrouter"
    stub.write_text("#!/bin/sh\nexit 3\n")
    stub.chmod(0o755)
    rc = load_module().main(["abc123abc123"])
    assert rc == 3
    assert json.loads((jobdir / "done").read_text())["exit_code"] == 3
```

- [ ] **Step 2: Red** — register the check first so the failure is the *tests*, not a missing attrset. In `flake.nix` next to `lane-unit` (`flake.nix:1459-1477`) add:

```nix
        seat-unit =
          pkgs.runCommand "seat-unit-tests"
            {
              nativeBuildInputs = [
                helmPython
                pkgs.git
              ];
            }
            ''
              mkdir -p pkgs tests
              cp -r ${self}/pkgs/seat pkgs/seat
              cp -r ${self}/tests/seat tests/seat
              pytest tests/seat -q
              touch $out
            '';
```

(`helmPython` is the `python3.withPackages (ps: [ ps.pytest ])` at `flake.nix:112`.) Add `pkgs/seat tests/seat` to both ruff lists in `flake.nix` (lines 889–890) and to the two ruff lines in `githooks/pre-commit` (lines 25–26). Then:

```bash
git add pkgs/seat tests/seat flake.nix githooks/pre-commit
nix build .#checks.x86_64-linux.seat-unit -L --no-link
```

Expected: FAIL — pytest collection error, `ModuleNotFoundError`/`FileNotFoundError` for `pkgs/seat/seat-submit.py` (the fixture `load_module()` cannot find the module; the job-file assertions are never reached).

- [ ] **Step 3: Implement** — `pkgs/seat/seat-submit.py`:

```python
"""seat-submit / seat-wait -- the operator's CLI for the brokered seat
(plan 2026-09-05-seat-behind-broker, S1).

One file backs two binaries: nixosModules/seat.nix wraps this file twice
with SEAT_MODE=submit|wait, mirroring pkgs/lane/lane-submit.py's LANE_MODE
dispatch. Direct invocation (as in tests) defaults to submit.

  seat-submit --workspace DIR --dsh-home DIR --mode headless|web
      --brief-file FILE --model ID [--effort E]
    Writes ${SEAT_STATE_DIR:-/var/lib/seat}/jobs/<id>/ (0700, the invoking
    operator) holding one file per field, then starts seat@<id>.service
    (polkit grants the operator start+stop) and prints <id>.

  seat-wait <id> [--timeout S] [--poll-interval S]
    Polls jobs/<id>/done (written by seat-run on any exit), then prints
    jobs/<id>/output.log verbatim. factory-task extracts the
    FACTORY-RESULT block from that text exactly as it did from a direct
    seat's log -- the .result shape is unchanged.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import uuid

FIELDS = ("workspace", "dsh-home", "mode", "brief", "model", "effort")


def _job_dir(job_id):
    base = os.environ.get("SEAT_STATE_DIR", "/var/lib/seat")
    return os.path.join(base, "jobs", job_id)


def _err(message):
    print(f"seat-submit: {message}", file=sys.stderr)
    return 2


def cmd_submit(argv):
    p = argparse.ArgumentParser(prog="seat-submit")
    p.add_argument("--workspace", required=True)
    p.add_argument("--dsh-home", required=True)
    p.add_argument("--mode", required=True)
    p.add_argument("--brief-file", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--effort", default="medium")
    args = p.parse_args(argv)

    if args.mode not in ("headless", "web"):
        return _err(f"--mode must be headless or web, got {args.mode!r}")
    if not os.path.isdir(args.workspace):
        return _err(f"--workspace {args.workspace} is not a directory")
    try:
        with open(args.brief_file, encoding="utf-8") as f:
            brief = f.read()
    except OSError:
        return _err(f"--brief-file {args.brief_file} cannot be read")

    job_id = uuid.uuid4().hex[:12]
    jobdir = _job_dir(job_id)
    os.makedirs(jobdir, mode=0o700)
    os.chmod(jobdir, 0o700)
    fields = {
        "workspace": args.workspace,
        "dsh-home": args.dsh_home,
        "mode": args.mode,
        "brief": brief,
        "model": args.model,
        "effort": args.effort,
    }
    for name in FIELDS:
        path = os.path.join(jobdir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(fields[name])
        os.chmod(path, 0o600)

    # Type=simple: `systemctl start` returns once seat-run forks, so the id
    # is usable immediately and seat-wait does the waiting. check=False:
    # a non-zero here means systemd never started the unit -- the job id is
    # still printed, and the warning names the journal to read.
    unit = f"seat@{job_id}.service"
    proc = subprocess.run(["systemctl", "start", unit], check=False)
    if proc.returncode != 0:
        print(
            f"seat-submit: warning: systemctl start {unit} exited "
            f"{proc.returncode} -- check journalctl -u {unit}",
            file=sys.stderr,
        )
    print(job_id)
    return 0


def cmd_wait(argv):
    p = argparse.ArgumentParser(prog="seat-wait")
    p.add_argument("job_id")
    p.add_argument("--timeout", type=float, default=10800)
    p.add_argument("--poll-interval", type=float, default=2.0)
    args = p.parse_args(argv)

    jobdir = _job_dir(args.job_id)
    done_path = os.path.join(jobdir, "done")
    deadline = time.time() + args.timeout
    while not os.path.exists(done_path):
        if time.time() >= deadline:
            print(
                f"seat-wait: timed out waiting for {done_path}", file=sys.stderr
            )
            return 1
        time.sleep(args.poll_interval)
    with open(os.path.join(jobdir, "output.log"), encoding="utf-8") as f:
        sys.stdout.write(f.read())
    return 0


def main():
    mode = os.environ.get("SEAT_MODE", "submit")
    if mode == "wait":
        return cmd_wait(sys.argv[1:])
    return cmd_submit(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
```

`pkgs/seat/seat-run.py`:

```python
"""Seat job runner (plan 2026-09-05-seat-behind-broker, S1) -- the ExecStart
of nixosModules/seat.nix's seat@.service.

seat-run <job-id> reads the job directory seat-submit wrote (six files:
workspace, dsh-home, mode, brief, model, effort) and runs the seat
wrapper in --broker mode: the unit's environment (set in Nix) carries the
proxy, the CA bundle, the placeholder OPENROUTER_API_KEY and the
SEAT_BROKER_GATEWAY/SEAT_NAMESPACE_ADDR the wrapper checks. This script
never sees a key. stdout+stderr stream to the journal AND to
jobs/<id>/output.log; on ANY exit -- including SIGTERM from
`systemctl stop` -- jobs/<id>/done is written so seat-wait can finish.
"""

import json
import os
import signal
import subprocess
import sys
import time

FIELDS = ("workspace", "dsh-home", "mode", "brief", "model", "effort")


def _read(jobdir, name):
    with open(os.path.join(jobdir, name), encoding="utf-8") as f:
        return f.read()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: seat-run <job-id>", file=sys.stderr)
        return 2
    base = os.environ.get("SEAT_STATE_DIR", "/var/lib/seat")
    jobdir = os.path.join(base, "jobs", argv[0])
    job = {name: _read(jobdir, name) for name in FIELDS}

    env = dict(os.environ)
    env["DSH_HOME"] = job["dsh-home"]
    env["OPENROUTER_REASONING_EFFORT"] = job["effort"]

    args = ["dsh-openrouter", "--broker", "--model", job["model"]]
    if job["mode"] == "headless":
        args += ["--headless", job["brief"]]
    else:
        web = f"http://{env['SEAT_NAMESPACE_ADDR']}:{env['SEAT_WEB_PORT']}"
        print(
            f"seat: web UI at {web} (reachable from the host only)", flush=True
        )
        args += [
            "--bind-namespace",
            "--",
            "--no-open",
            "--port",
            env["SEAT_WEB_PORT"],
        ]

    log_path = os.path.join(jobdir, "output.log")
    log = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        args,
        cwd=job["workspace"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    def _terminate(_signum, _frame):
        proc.terminate()

    signal.signal(signal.SIGTERM, _terminate)
    signal.signal(signal.SIGINT, _terminate)

    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        log.write(line)
        log.flush()
    rc = proc.wait()
    log.close()
    with open(os.path.join(jobdir, "done"), "w", encoding="utf-8") as f:
        json.dump({"exit_code": rc if rc >= 0 else 128 - rc, "ts": time.time()}, f)
    return rc if rc >= 0 else 128 - rc


if __name__ == "__main__":
    sys.exit(main())
```

`pkgs/seat/seat-run.nix` (mirrors `pkgs/lane/lane-run.nix`):

```nix
{ writeShellApplication, python3 }:
# S1 (seat-behind-broker): the ExecStart of seat@.service -- runs one
# /var/lib/seat/jobs/<id> job through dsh-openrouter --broker. Stdlib-only;
# dsh-openrouter itself is on the unit's PATH (nixosModules/seat.nix), not a
# runtime input here, same division of labour as pkgs/lane/lane-run.nix.
writeShellApplication {
  name = "seat-run";
  runtimeInputs = [ python3 ];
  text = ''
    exec python3 ${./seat-run.py} "$@"
  '';
}
```

Add to `flake.nix`'s `packages.${system}` next to `lane-run` (`flake.nix:603`): `seat-run = pkgs.callPackage ./pkgs/seat/seat-run.nix { };`

- [ ] **Step 4: Green**

```bash
git add pkgs/seat tests/seat flake.nix githooks/pre-commit
nix build .#checks.x86_64-linux.seat-unit -L --no-link
```

Expected: PASS (8 tests). Then `nix develop -c ruff format pkgs/seat tests/seat`, re-run the check, then `nix develop -c githooks/pre-commit`.

- [ ] **Step 5: Commit**

```bash
git add pkgs/seat tests/seat flake.nix githooks/pre-commit
nix develop -c git commit -F <msgfile>   # subject below
```

**touches:** pkgs/seat/seat-submit.py, pkgs/seat/seat-run.py, pkgs/seat/seat-run.nix, tests/seat/test_seat_submit.py, tests/seat/test_seat_run.py, flake.nix, githooks/pre-commit
**acceptance:** seat-unit, lint
**commit subject:** `seat: seat-submit/seat-wait job CLI and the seat-run unit runner, unit-tested (test: seat-unit, lint)`

### S2 (code, M) — the wrapper gains `--broker` (and internal `--bind-namespace`), the direct path prints a deprecation line

**dependsOn:** none

**Files:**
- Modify: `pkgs/dsh-openrouter/dsh-openrouter.sh` (usage text, argument parser, the key block, the web exec)
- Modify: `tests/unit/70-dsh-openrouter.bats` (new `--broker` cases)

**Interfaces:**
- Produces the flags S1's `seat-run` already calls and S5's VM drives:
  - `dsh-openrouter --broker [--model ID] --headless "TASK"` — never opens the key file (no existence check, no mode check, no read); requires `SEAT_BROKER_GATEWAY` set **and** `ip route show default` to contain `via $SEAT_BROKER_GATEWAY`, else `die 6`; exports `OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-injected-by-broker}` (a placeholder the seat broker replaces).
  - `dsh-openrouter --broker --bind-namespace [--model ID] -- --port N` — web profile bound to `$SEAT_NAMESPACE_ADDR` instead of `127.0.0.1`; `--bind-namespace` without `--broker` exits 2; without `SEAT_NAMESPACE_ADDR` exits 6.
  - New exit code **6**: "`--broker` outside the seat namespace". Without `--broker` the wrapper behaves exactly as today plus one stderr line: `dsh-openrouter: note: the direct-key seat is deprecated -- use seat-submit/seat@ (docs/runbooks/lanes.md); ~/.config/openrouter/key goes away after the migration`.
- Consumes nothing; the unit-side environment it checks is produced by S3.

- [ ] **Step 1: Write the failing tests** — append to `tests/unit/70-dsh-openrouter.bats` (the file's `setup()` already unsets proxy vars and points HOME at a tmpdir; `make_key`, `start_fake`/`FAKE_CAPTURE` and the python3-capture idiom are the file's own, lines 43–68 and 202–219):

```bash
# S2 (--broker): an `ip` stub stands in for the netns default route the
# seat unit provides; SEAT_BROKER_GATEWAY names the gateway the unit
# renders (nixosModules/seat.nix, 10.100.4.1 in production).
stub_ip_matching() {
  mkdir -p "$TMPHOME/bin"
  cat >"$TMPHOME/bin/ip" <<'EOF'
#!/usr/bin/env bash
if [ "$1 $2" = "route show" ]; then
  echo "default via 10.100.4.1 dev ven-seat"
  exit 0
fi
exit 1
EOF
  chmod +x "$TMPHOME/bin/ip"
  export PATH="$TMPHOME/bin:$PATH"
}

stub_ip_empty() {
  mkdir -p "$TMPHOME/bin"
  cat >"$TMPHOME/bin/ip" <<'EOF'
#!/usr/bin/env bash
if [ "$1 $2" = "route show" ]; then
  echo "default via 192.168.1.1 dev wlp0s20f3"
  exit 0
fi
exit 1
EOF
  chmod +x "$TMPHOME/bin/ip"
  export PATH="$TMPHOME/bin:$PATH"
}

@test "--broker never opens the key file: a mode-000 key file does not stop the launch" {
  make_key "sk-or-must-not-be-read"
  chmod 000 "$XDG_CONFIG_HOME/openrouter/key"
  stub_ip_matching
  start_fake '[{"content": "FAKE-OK"}]'
  SEAT_BROKER_GATEWAY=10.100.4.1 \
    OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --broker --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"FAKE-OK"* ]]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat, requests
# The wire carries the PLACEHOLDER (the broker would overwrite it in
# production); the mode-000 file's key never appears -- and the launch
# itself proves the file was never read (a read would have died EACCES).
assert chat[0]["headers"].get("authorization") == "Bearer injected-by-broker", chat[0]["headers"]
PY
}

@test "--broker keeps a placeholder the unit already set" {
  make_key
  stub_ip_matching
  start_fake '[{"content": "FAKE-OK"}]'
  SEAT_BROKER_GATEWAY=10.100.4.1 OPENROUTER_API_KEY=seat-placeholder \
    OPENROUTER_BASE_URL="http://127.0.0.1:$FAKE_PORT/api/v1" \
    run dsh-openrouter --broker --headless "Reply with the word ok."
  [ "$status" -eq 0 ]
  python3 - "$FAKE_CAPTURE" <<'PY'
import json, sys
requests = json.load(open(sys.argv[1]))
chat = [r for r in requests if r["path"].endswith("/chat/completions")]
assert chat[0]["headers"].get("authorization") == "Bearer seat-placeholder", chat[0]["headers"]
PY
}

@test "--broker without SEAT_BROKER_GATEWAY refuses with exit 6" {
  make_key
  stub_ip_matching
  run dsh-openrouter --broker --dump-config
  [ "$status" -eq 6 ]
  [[ "$output" == *"SEAT_BROKER_GATEWAY"* ]]
}

@test "--broker whose default route is not the broker refuses with exit 6" {
  make_key
  stub_ip_empty
  SEAT_BROKER_GATEWAY=10.100.4.1 run dsh-openrouter --broker --dump-config
  [ "$status" -eq 6 ]
  [[ "$output" == *"10.100.4.1"* ]]
}

@test "--bind-namespace without --broker is a usage error" {
  make_key
  run dsh-openrouter --bind-namespace --dump-config
  [ "$status" -eq 2 ]
  [[ "$output" == *"--broker"* ]]
}

@test "--broker --bind-namespace binds SEAT_NAMESPACE_ADDR, not 127.0.0.1" {
  make_key
  stub_ip_matching
  WEB_PIDS=()
  # 127.0.0.2 stands in for the namespace address: on Linux any 127/8
  # address answers on lo, and it is NOT the 127.0.0.1 the web exec would
  # bind without --bind-namespace -- so the URL line proves which branch ran.
  SEAT_BROKER_GATEWAY=10.100.4.1 SEAT_NAMESPACE_ADDR=127.0.0.2 \
    OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 \
    dsh-openrouter --broker --bind-namespace -- --no-open --port 38952 \
    >"$TMPHOME/web-broker.log" 2>&1 &
  WEB_PIDS+=("$!")
  for _ in $(seq 1 100); do
    grep -q '^dsh web: http' "$TMPHOME/web-broker.log" 2>/dev/null && break
    sleep 0.1
  done
  run cat "$TMPHOME/web-broker.log"
  stop_web
  [[ "$output" == *"http://127.0.0.2:38952"* ]]
}

@test "without --broker the deprecation line names the seat unit" {
  make_key
  OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --dump-config
  [ "$status" -eq 0 ]
  [[ "$output" == *"deprecated"* ]]
  [[ "$output" == *"seat-submit"* ]]
}
```

- [ ] **Step 2: Red**

```bash
git add tests/unit/70-dsh-openrouter.bats
nix build .#checks.x86_64-linux.unit -L --no-link
```

Expected: FAIL — `unknown option --broker (try --help)` (exit 2) in every `--broker` case; the deprecation case fails on the missing `deprecated` line.

- [ ] **Step 3: Implement** — four edits to `pkgs/dsh-openrouter/dsh-openrouter.sh`.

(a) Usage text (line 39–43) gains one line per form, and the exit-code line (line 65) becomes:

```
Exit codes: 2 usage, 3 refused workspace, 4 key problem, 5 bad value, 6 --broker outside the seat namespace.
```

plus a paragraph:

```
  --broker            the seat unit drives this (seat@.service): never opens
                      the key file, keeps the placeholder OPENROUTER_API_KEY,
                      and refuses to run unless SEAT_BROKER_GATEWAY is set and
                      the default route goes via it (exit 6 otherwise)
  --bind-namespace    with --broker only: bind the web UI to
                      SEAT_NAMESPACE_ADDR instead of 127.0.0.1
```

(b) The parser: add `broker=0` and `bind_namespace=0` next to `mode=web` (line 76), and two cases inside the `while` loop before `-*)`:

```bash
    --broker)
      broker=1
      shift
      ;;
    --bind-namespace)
      bind_namespace=1
      shift
      ;;
```

Immediately after the loop:

```bash
if [ "$bind_namespace" = 1 ] && [ "$broker" = 0 ]; then
  die 2 "--bind-namespace is only accepted together with --broker"
fi
```

(c) The key block (lines 220–243) becomes conditional:

```bash
if [ "$broker" = 1 ]; then
  # The seat unit (nixosModules/seat.nix) set the proxy/CA environment and
  # the placeholder; the egress broker overwrites the Authorization header
  # for the allowlisted host, so a request the broker refuses never carries
  # a real key. The key file is never touched: no existence check, no mode
  # check, no read. Refuse to run outside the seat namespace -- the unit
  # names the broker's veth gateway in SEAT_BROKER_GATEWAY and the netns
  # default route must point at it, or a mis-launch would send the
  # placeholder DIRECT to OpenRouter as if it were a key, bypassing the
  # allowlist, the deny paths and the audit log.
  command -v ip >/dev/null ||
    die 6 "--broker needs iproute2 on PATH (seat@.service provides it)"
  [ -n "${SEAT_BROKER_GATEWAY:-}" ] ||
    die 6 "--broker needs SEAT_BROKER_GATEWAY (seat@.service sets it); refusing to run outside the seat unit"
  ip route show default | grep -q "via $SEAT_BROKER_GATEWAY " ||
    die 6 "--broker outside its namespace: 'ip route show default' has no 'via $SEAT_BROKER_GATEWAY ' (the seat unit joins /run/netns/egress-seat)"
  export OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-injected-by-broker}
  key_source="the seat broker (placeholder in the environment; the broker injects the real header)"
else
  printf 'dsh-openrouter: note: the direct-key seat is deprecated -- use seat-submit/seat@ (docs/runbooks/lanes.md); ~/.config/openrouter/key goes away after the migration\n' >&2
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then
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
  fi
fi
```

(The `else` branch is today's lines 220–243 verbatim, indented — only the `if` arm and the deprecation `printf` are new. The trailing space in `"via $SEAT_BROKER_GATEWAY "` keeps `10.100.4.1` from matching `10.100.4.10`.)

(d) The web exec (line 569–580): replace the hardcoded bind address:

```bash
  web)
    bind_addr=127.0.0.1
    if [ "$bind_namespace" = 1 ]; then
      [ -n "${SEAT_NAMESPACE_ADDR:-}" ] ||
        die 6 "--bind-namespace needs SEAT_NAMESPACE_ADDR (seat@.service sets it)"
      bind_addr=$SEAT_NAMESPACE_ADDR
    fi
    printf 'dsh-openrouter: %s via %s, %s, key from %s, workspace %s\n' \
      "$model" "$base_url" "$permission" "$key_source" "$workspace" >&2
    printf 'dsh-openrouter: zero-data-retention is an OpenRouter account setting, not stamped per request here (docs/runbooks/lanes.md)\n' >&2
    if [ -z "$port_given" ]; then
      set -- --port 0 "$@"
    fi
    exec node --expose-internals "$bin_js" --profile web --patch "$overlay" --host "$bind_addr" "$@"
    ;;
```

The operator-facing `--host` rejection at lines 142–148 stays exactly as it is — the web seat's address comes from the unit's environment, never from a passthrough flag (spec §5).

- [ ] **Step 4: Green**

```bash
git add pkgs/dsh-openrouter/dsh-openrouter.sh tests/unit/70-dsh-openrouter.bats
nix build .#checks.x86_64-linux.unit -L --no-link
nix develop -c githooks/pre-commit
```

Expected: PASS (all pre-existing cases unchanged — the `else` arm is byte-identical behavior — plus the 7 new ones).

- [ ] **Step 5: Commit**

```bash
git add pkgs/dsh-openrouter/dsh-openrouter.sh tests/unit/70-dsh-openrouter.bats
nix develop -c git commit -F <msgfile>   # subject below
```

**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats
**acceptance:** unit, lint
**commit subject:** `dsh: --broker skips the key file and refuses outside the seat namespace; --bind-namespace binds the web UI to the namespace address; the direct path is deprecated (test: unit, lint)`

### S3 (code, L) — `nixosModules/seat.nix`: the broker instance, the `seat@` template, polkit start+stop, `exposePort` in the broker module; `seat-eval` and `seat-assertion-negative`

**dependsOn:** S1 (the module's `ExecStart` is `${pkgs.callPackage ../pkgs/seat/seat-run.nix { }}/bin/seat-run %i` and it wraps `pkgs/seat/seat-submit.py` twice)

**Files:**
- Create: `nixosModules/seat.nix`
- Modify: `nixosModules/egressBroker.nix` (the `exposePort` option + two forward-chain lines)
- Modify: `flake.nix` (`nixosModules.seat` export; `seatEvalSystem`/`seatBadSystem` fixtures; `checks.seat-eval`, `checks.seat-assertion-negative`)

**Interfaces:**
- Produces the NixOS option set `services.seat`: `enable`; `host` (default `"openrouter.ai"`); `model` (default `"deepseek/deepseek-v4-pro-0813"`); `keyFile` (no default); `hostAddress` (default `"10.100.4.1"`); `namespaceAddress` (default `"10.100.4.2"`); `listenPort` (default `3141`); `webPort` (default `8480`); `baseUrl` (default `"https://openrouter.ai/api/v1"` — the VM points it at the fake); `operatorUser` (default `config.services.helm.operatorUser or "dalhaka"`, the same fallback `nixosModules/modelLane.nix:115` uses); `stateDir` (default `"/var/lib/seat"`); `dshPackage` (default `pkgs.callPackage ../pkgs/dsh { }`); `seatPackage` (default `pkgs.callPackage ../pkgs/dsh-openrouter { dsh = cfg.dshPackage; }` — `dsh` is a required argument of `pkgs/dsh-openrouter/default.nix`).
- Produces on the host: `services.egress-broker.instances.seat`; tmpfiles rules; `environment.systemPackages` `seat-submit`/`seat-wait`; `systemd.services."seat@"`; a polkit rule granting `operatorUser` start **and** stop on `seat@*.service`; three assertions.
- Consumes S1's `seat-run` package and `seat-submit.py`; consumed by S5 (VM imports the module) and S6 (host wiring).

- [ ] **Step 1: Write the failing checks** — in `flake.nix`:

(a) Export the module in the `nixosModules` attrset (`flake.nix:616-625`): `seat = import ./nixosModules/seat.nix;`

(b) Add fixtures next to `laneEvalSystem` (`flake.nix:503`):

```nix
      seatEvalSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seat
          (_: {
            boot.loader.grub.enable = false;
            fileSystems."/".device = "none";
            fileSystems."/".fsType = "tmpfs";
            system.stateVersion = "25.11";
            users.users.dalhaka = {
              isNormalUser = true;
              uid = 1000;
            };
            # A second broker instance in a DISJOINT /24: the collision
            # assertion must pass for this (and would fail for a fixture
            # reusing the seat's own block).
            services.egress-broker.instances.other = {
              hostAddress = "10.100.9.1";
              namespaceAddress = "10.100.9.2";
            };
            services.seat = {
              enable = true;
              host = "example.com";
              keyFile = "/var/lib/secrets/seat-key";
              hostAddress = "10.100.8.1";
              namespaceAddress = "10.100.8.2";
              listenPort = 3298;
              webPort = 8481;
              baseUrl = "https://example.com/api/v1";
            };
          })
        ];
      };
      seatBadSystem = nixpkgs.lib.nixosSystem {
        inherit system;
        modules = [
          self.nixosModules.egressBroker
          self.nixosModules.seat
          (
            { lib, ... }:
            {
              boot.loader.grub.enable = false;
              fileSystems."/".device = "none";
              fileSystems."/".fsType = "tmpfs";
              system.stateVersion = "25.11";
              users.users.dalhaka = {
                isNormalUser = true;
                uid = 1000;
              };
              services.seat = {
                enable = true;
                host = "example.com";
                keyFile = "/var/lib/secrets/seat-key";
              };
              # seat-assertion-negative: a REAL key in the unit's environment
              # must fail the build (spec, "Negative assertion").
              systemd.services."seat@".environment.OPENROUTER_API_KEY = lib.mkForce "sk-live-real-key";
            }
          )
        ];
      };
```

(c) Add the checks next to `lane-eval` (`flake.nix:1283`):

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
            (
              i.hostAddress == "10.100.8.1"
              && i.namespaceAddress == "10.100.8.2"
              && i.listenPort == 3298
              && i.allow == [ "example.com" ]
              && i.exposePort == 8481
            )
            "seat-eval: instance 'seat' must be rendered from services.seat's address block, allow == [ host ], exposePort == webPort";
          assert nixpkgs.lib.assertMsg (
            i.inject."example.com".valueFile == "/var/lib/secrets/seat-key"
          ) "seat-eval: instance 'seat' must inject from services.seat.keyFile";
          assert nixpkgs.lib.assertMsg (i.denyPaths."example.com".pathPrefixes == [ "/api/v1/messages" ])
            "seat-eval: instance 'seat' must deny /api/v1/messages before injection (fail closed, as the lane)";
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.any
            (r: nixpkgs.lib.hasInfix "/var/lib/secrets/seat-key" r && nixpkgs.lib.hasInfix "0440" r)
            c.systemd.tmpfiles.rules
          ) "seat-eval: tmpfiles must reset the key file to 0440 root:egress-broker";
          assert nixpkgs.lib.assertMsg
            (
              nixpkgs.lib.any (r: r == "d /var/lib/seat 0750 dalhaka users -") c.systemd.tmpfiles.rules
              && nixpkgs.lib.any (r: r == "d /var/lib/seat/jobs 0750 dalhaka users -") c.systemd.tmpfiles.rules
            )
            "seat-eval: /var/lib/seat and jobs/ must be tmpfiles-declared 0750 <operator>:users";
          assert nixpkgs.lib.assertMsg (
            unit.requires == [ "egress-broker-seat.service" ]
            && unit.after == [ "egress-broker-seat.service" ]
          ) "seat-eval: seat@ must Require+After egress-broker-seat.service";
          assert nixpkgs.lib.assertMsg
            (
              sc.Type == "simple"
              && sc.User == "dalhaka"
              && sc.NetworkNamespacePath == "/run/netns/egress-seat"
            )
            "seat-eval: seat@ must run as the operator (Type=simple, never DynamicUser) in the seat netns";
          assert nixpkgs.lib.assertMsg (
            sc.ExecStart == "${self.packages.${system}.seat-run}/bin/seat-run %i"
          ) "seat-eval: seat@ ExecStart must be seat-run's stable path, then %i";
          assert nixpkgs.lib.assertMsg (
            unit.environment.HTTPS_PROXY == "http://10.100.8.1:3298"
            && unit.environment.HTTP_PROXY == "http://10.100.8.1:3298"
            && unit.environment.SSL_CERT_FILE == caBundle
            && unit.environment.NIX_SSL_CERT_FILE == caBundle
            && unit.environment.NODE_EXTRA_CA_CERTS == caBundle
            && unit.environment.NODE_USE_ENV_PROXY == "1"
            && (nixpkgs.lib.hasInfix "/lib/proxy-shim.cjs" (unit.environment.NODE_OPTIONS or ""))
          ) "seat-eval: seat@ must carry the proxy + CA environment (dsh ignores HTTPS_PROXY without NODE_USE_ENV_PROXY and the shim)";
          assert nixpkgs.lib.assertMsg (
            unit.environment.OPENROUTER_API_KEY == "injected-by-broker"
          ) "seat-eval: seat@ must carry only the placeholder OPENROUTER_API_KEY=injected-by-broker";
          assert nixpkgs.lib.assertMsg (
            unit.environment.SEAT_BROKER_GATEWAY == "10.100.8.1"
            && unit.environment.SEAT_NAMESPACE_ADDR == "10.100.8.2"
            && unit.environment.SEAT_WEB_PORT == "8481"
            && unit.environment.OPENROUTER_BASE_URL == "https://example.com/api/v1"
          ) "seat-eval: seat@ must export the broker gateway, namespace address, web port and base URL";
          assert nixpkgs.lib.assertMsg (
            sc.ReadWritePaths == [
              "/home/dalhaka/factory"
              "/home/dalhaka/nixos-agent-env"
              "/home/dalhaka/flakes"
              "/var/lib/seat"
            ]
          ) "seat-eval: seat@ ReadWritePaths must be exactly the factory root, the checkout, the sibling flakes and the state dir";
          assert nixpkgs.lib.assertMsg (
            sc.NoNewPrivileges == true
            && sc.ProtectSystem == "strict"
            && sc.PrivateTmp == true
            && sc.CapabilityBoundingSet == ""
            && sc.RestrictAddressFamilies == "AF_INET AF_INET6 AF_UNIX AF_NETLINK"
            && sc.ProtectHome == false
          ) "seat-eval: seat@ must carry the hardening contract, with ProtectHome explicitly false (AF_NETLINK included: the wrapper's --broker check runs `ip route`)";
          assert nixpkgs.lib.assertMsg
            (
              nixpkgs.lib.elem "-/var/lib/secrets" sc.InaccessiblePaths
              && nixpkgs.lib.elem "-/var/lib/egress-broker" sc.InaccessiblePaths
              && !(nixpkgs.lib.any (
                p:
                let
                  hidden = nixpkgs.lib.removePrefix "-" p;
                in
                unit.environment.SSL_CERT_FILE == hidden
                || nixpkgs.lib.hasPrefix (hidden + "/") unit.environment.SSL_CERT_FILE
              ) sc.InaccessiblePaths)
            )
            "seat-eval: InaccessiblePaths must hide secrets and broker state but never the public CA bundle (the lane-eval path-component-aware cross-check)";
          assert nixpkgs.lib.assertMsg
            (
              nixpkgs.lib.hasInfix "seat@" c.security.polkit.extraConfig
              && nixpkgs.lib.hasInfix "\"start\"" c.security.polkit.extraConfig
              && nixpkgs.lib.hasInfix "\"stop\"" c.security.polkit.extraConfig
              && nixpkgs.lib.hasInfix "subject.user == \"dalhaka\"" c.security.polkit.extraConfig
              && nixpkgs.lib.hasInfix "polkit.Result.YES" c.security.polkit.extraConfig
            )
            "seat-eval: polkit must gate verb=start AND verb=stop on seat@*.service to operatorUser";
          assert nixpkgs.lib.assertMsg
            (nixpkgs.lib.hasInfix ''oifname "veb-seat" ip daddr 10.100.8.2 tcp dport 8481 accept'' c.networking.nftables.tables.egress-broker.content)
            "seat-eval: forward-seat must accept host->namespaceAddress:webPort (the web seat; everything else still drops)";
          builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "seat-eval-ok" { } "touch $out");
        seat-assertion-negative =
          let
            attempt = builtins.tryEval seatBadSystem.config.system.build.toplevel.drvPath;
          in
          if attempt.success then
            throw "seat-assertion-negative: a real key in seat@'s environment DID NOT FAIL the build"
          else
            pkgs.runCommand "seat-assertion-negative-ok" { } "touch $out";
```

- [ ] **Step 2: Red**

```bash
git add flake.nix nixosModules/seat.nix nixosModules/egressBroker.nix
nix build .#checks.x86_64-linux.seat-eval -L --no-link
```

Expected: FAIL — `attribute 'seat' missing` in the `nixosModules` import, or (once the export exists but the module file is still absent) a file-not-found; with an empty module the first `assertMsg` fires. `nix build .#checks.x86_64-linux.seat-assertion-negative -L --no-link` must fail too — the build *succeeds* with the mkForce'd real key because nothing asserts the placeholder yet (that is the negative check doing its job: red means "the bad config is not caught").

- [ ] **Step 3: Implement** — `nixosModules/egressBroker.nix`: inside the per-instance submodule options (next to `listenPort`, line 47–50) add:

```nix
          exposePort = lib.mkOption {
            type = lib.types.nullOr lib.types.port;
            default = null;
            description = ''
              When set, the host side may forward to
              <namespaceAddress>:<port> -- a web UI bound inside the
              namespace (the seat's browser UI; plan
              2026-09-05-seat-behind-broker S3/D6). Everything else on the
              forward path still drops, and the broker's own input chain is
              untouched.
            '';
          };
```

and in the `forward-${name}` chain (lines 187–191), before the two drops:

```nix
            chain forward-${name} {
              type filter hook forward priority filter - 1;
              ${lib.optionalString (i.exposePort != null) ''
                oifname "veb-${name}" ip daddr ${i.namespaceAddress} tcp dport ${toString i.exposePort} accept
                iifname "veb-${name}" ip saddr ${i.namespaceAddress} tcp sport ${toString i.exposePort} ct state established accept
              ''}
              iifname "veb-${name}" drop
              oifname "veb-${name}" drop
            }
```

`nixosModules/seat.nix`, in full:

```nix
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.seat;
  seatRun = pkgs.callPackage ../pkgs/seat/seat-run.nix { };
  # One file (pkgs/seat/seat-submit.py) backs both operator binaries, the
  # same SEAT_MODE dispatch modelLane.nix uses for lane-submit/lane-wait.
  seatSubmit = pkgs.writeShellApplication {
    name = "seat-submit";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      export SEAT_MODE=submit
      exec python3 ${../pkgs/seat/seat-submit.py} "$@"
    '';
  };
  seatWait = pkgs.writeShellApplication {
    name = "seat-wait";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      export SEAT_MODE=wait
      exec python3 ${../pkgs/seat/seat-submit.py} "$@"
    '';
  };
  caBundle = "/var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt";
  prefix24 =
    addr: lib.concatStringsSep "." (lib.take 3 (lib.splitString "." addr));
in
{
  options.services.seat = {
    enable = lib.mkEnableOption "the operator seat behind its own egress-broker instance";
    host = lib.mkOption {
      type = lib.types.str;
      default = "openrouter.ai";
      description = "The single upstream hostname the seat's broker instance allows.";
    };
    model = lib.mkOption {
      type = lib.types.str;
      default = "deepseek/deepseek-v4-pro-0813";
      description = "Default model id recorded when a job omits none (the wrapper's own default still applies to --model).";
    };
    keyFile = lib.mkOption {
      type = lib.types.str;
      description = ''
        Path to the API key file the seat's broker instance injects for
        `host`. Must be outside /nix/store (asserted below, the same
        assertion modelLane.nix makes). Never read by this module or by any
        seat process; consumed only by
        services.egress-broker.instances.seat.inject.
      '';
    };
    hostAddress = lib.mkOption {
      type = lib.types.str;
      default = "10.100.4.1";
      description = "Host-side veth address for the seat's broker instance (10.100.4.x per the spec; 10.100.2.x media, 10.100.3.x the lane).";
    };
    namespaceAddress = lib.mkOption {
      type = lib.types.str;
      default = "10.100.4.2";
      description = "Netns-side veth address; the web seat binds here.";
    };
    listenPort = lib.mkOption {
      type = lib.types.port;
      default = 3141;
      description = "Port the seat's broker listens on inside the netns (3128 broker-vm, 3129 cowork, 3131 the lane, 3199 fixtures).";
    };
    webPort = lib.mkOption {
      type = lib.types.port;
      default = 8480;
      description = "Fixed port the web seat binds on namespaceAddress; the broker's forward chain accepts exactly this port (fixed, because nftables names it).";
    };
    baseUrl = lib.mkOption {
      type = lib.types.str;
      default = "https://openrouter.ai/api/v1";
      description = "OPENROUTER_BASE_URL for seat jobs (the VM test points it at its fake upstream).";
    };
    operatorUser = lib.mkOption {
      type = lib.types.str;
      default = config.services.helm.operatorUser or "dalhaka";
      description = "The operator: the seat units run as this user and polkit gates start/stop to them.";
    };
    stateDir = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/seat";
      description = "Job spool root (jobs/<id>/ one directory per job).";
    };
    dshPackage = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ../pkgs/dsh { };
      description = "The pinned harness, for the NODE_OPTIONS proxy shim (the same preload the lane unit sets).";
    };
    seatPackage = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ../pkgs/dsh-openrouter { dsh = cfg.dshPackage; };
      description = "The dsh-openrouter wrapper on the unit's PATH.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = !(lib.hasPrefix "/nix/store" cfg.keyFile);
        message = "services.seat.keyFile must be a path outside /nix/store, got '${cfg.keyFile}'";
      }
      {
        # The placeholder is the whole point of the design (spec §4, and the
        # "Negative assertion" test): seat-assertion-negative proves a
        # mkForce'd real key fails here.
        assertion = config.systemd.services."seat@".environment.OPENROUTER_API_KEY == "injected-by-broker";
        message = "seat@ must carry only the placeholder OPENROUTER_API_KEY=injected-by-broker -- a real key in the unit's environment defeats the broker";
      }
      {
        # 10.100.4.x must not collide with 10.100.2.x (media), 10.100.3.x
        # (the lane) or any other instance's block (spec, Tests).
        assertion = !(lib.elem (prefix24 cfg.hostAddress) (
          lib.mapAttrsToList (_: i: prefix24 i.hostAddress) (
            lib.filterAttrs (n: _: n != "seat") config.services.egress-broker.instances
          )
        ));
        message = "services.seat: address block ${prefix24 cfg.hostAddress}.x collides with another egress-broker instance (10.100.2.x media, 10.100.3.x lane are taken; the seat is 10.100.4.x)";
      }
    ];

    services.egress-broker.instances.seat = {
      inherit (cfg) hostAddress namespaceAddress listenPort;
      allow = [ cfg.host ];
      inject.${cfg.host}.valueFile = cfg.keyFile;
      # Deny paths as the lane (O3 resolved, fail closed): refused before
      # the key is injected, audited reason "path-not-permitted".
      denyPaths.${cfg.host}.pathPrefixes = [ "/api/v1/messages" ];
      exposePort = cfg.webPort;
    };

    systemd.tmpfiles.rules = [
      "z ${cfg.keyFile} 0440 root egress-broker -"
      "d ${cfg.stateDir} 0750 ${cfg.operatorUser} users -"
      "d ${cfg.stateDir}/jobs 0750 ${cfg.operatorUser} users -"
    ];

    environment.systemPackages = [
      seatSubmit
      seatWait
    ];

    systemd.services."seat@" = {
      description = "Operator seat job %i: dsh-openrouter --broker behind egress broker 'seat'";
      requires = [ "egress-broker-seat.service" ];
      after = [ "egress-broker-seat.service" ];
      # iproute2: the wrapper's --broker namespace check runs `ip route`.
      # /run/current-system/sw: git and friends, same idiom as the lane
      # unit's `path` (a systemd unit's default PATH lacks the system profile).
      path = [
        pkgs.iproute2
        cfg.seatPackage
        "/run/current-system/sw"
      ];
      environment = {
        HTTPS_PROXY = "http://${cfg.hostAddress}:${toString cfg.listenPort}";
        HTTP_PROXY = "http://${cfg.hostAddress}:${toString cfg.listenPort}";
        SSL_CERT_FILE = caBundle;
        NIX_SSL_CERT_FILE = caBundle;
        NODE_EXTRA_CA_CERTS = caBundle;
        # dsh (Node) ignores HTTPS_PROXY without these two -- verified
        # 2026-09-03 and pinned by checks.lane-eval; the seat runs the same
        # harness, so the same two lines apply.
        NODE_USE_ENV_PROXY = "1";
        NODE_OPTIONS = "--require ${cfg.dshPackage}/lib/proxy-shim.cjs";
        # The placeholder the broker replaces (spec §4): a request the
        # broker refuses never carries a real key, and this string
        # authenticates nothing anywhere else.
        OPENROUTER_API_KEY = "injected-by-broker";
        SEAT_BROKER_GATEWAY = cfg.hostAddress;
        SEAT_NAMESPACE_ADDR = cfg.namespaceAddress;
        SEAT_WEB_PORT = toString cfg.webPort;
        SEAT_STATE_DIR = cfg.stateDir;
        OPENROUTER_BASE_URL = cfg.baseUrl;
      };
      serviceConfig = {
        # simple, not oneshot: one template serves headless jobs (process
        # exits) and the web UI (process runs until stopped). `systemctl
        # start` returns at fork, so seat-submit prints the id at once and
        # seat-wait polls the job's done marker.
        Type = "simple";
        # The operator, never DynamicUser: the seat edits the operator's
        # clones under ~/factory/ws and, interactively, the checkout (spec §2).
        User = cfg.operatorUser;
        Group = "users";
        NetworkNamespacePath = "/run/netns/egress-seat";
        ExecStart = "${seatRun}/bin/seat-run %i";
        ReadWritePaths = [
          "/home/${cfg.operatorUser}/factory"
          "/home/${cfg.operatorUser}/nixos-agent-env"
          "/home/${cfg.operatorUser}/flakes"
          cfg.stateDir
        ];
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        # ProtectHome is false ON PURPOSE (stated, not defaulted): writing
        # the operator's own files is the point of the seat (spec, Risks).
        # The hardening that remains is NoNewPrivileges +
        # ProtectSystem=strict with the explicit ReadWritePaths above, and
        # no /var/lib/secrets anywhere below.
        ProtectHome = false;
        PrivateTmp = true;
        CapabilityBoundingSet = "";
        # AF_NETLINK: the wrapper's --broker check reads the default route
        # via netlink (`ip route`).
        RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX AF_NETLINK";
        InaccessiblePaths = [
          "-/run/baskets"
          "-/var/lib/baskets"
          "-/var/lib/helm"
          "-/var/lib/egress-broker"
          "-/var/lib/secrets"
          "-/var/lib/lanes"
        ];
        UMask = "0077";
      };
    };

    security.polkit.enable = lib.mkDefault true;
    # ES5 (duktape -- see tests/lane/polkit.test.mjs's scanner): the
    # operator starts AND stops their own seat jobs (stop: a hung headless
    # seat must be killable, D4; the lane grants start only because its
    # oneshot blocks `systemctl start` for the job's whole life).
    security.polkit.extraConfig = ''
      polkit.addRule(function(action, subject) {
        if (action.id == "org.freedesktop.systemd1.manage-units") {
          var verb = action.lookup("verb");
          var unit = action.lookup("unit");
          var prefix = "seat@";
          var suffix = ".service";
          if ((verb == "start" || verb == "stop") &&
              unit.indexOf(prefix) === 0 &&
              unit.indexOf(suffix, unit.length - suffix.length) !== -1 &&
              subject.user == "${cfg.operatorUser}") {
            return polkit.Result.YES;
          }
        }
      });
    '';
  };
}
```

- [ ] **Step 4: Green**

```bash
git add nixosModules/seat.nix nixosModules/egressBroker.nix flake.nix
nix build .#checks.x86_64-linux.seat-eval -L --no-link
nix build .#checks.x86_64-linux.seat-assertion-negative -L --no-link
nix build .#checks.x86_64-linux.lane-eval -L --no-link        # the broker module edit must not disturb the lane
nix build .#checks.x86_64-linux.integration -L --no-link      # the forward chain's default path (exposePort == null) is byte-unchanged
nix develop -c githooks/pre-commit
```

Expected: all PASS; `seat-assertion-negative` now passes *because the bad fixture fails its build*.

- [ ] **Step 5: Commit**

```bash
git add nixosModules/seat.nix nixosModules/egressBroker.nix flake.nix
nix develop -c git commit -F <msgfile>   # subject below
```

**touches:** nixosModules/seat.nix, nixosModules/egressBroker.nix, flake.nix
**acceptance:** seat-eval, seat-assertion-negative, lane-eval, integration, lint
**commit subject:** `seat: the seat module — broker instance on 10.100.4.x, seat@ template as the operator in the netns, polkit start+stop, broker exposePort; eval + negative checks (test: seat-eval, seat-assertion-negative, lane-eval, integration, lint)`

### S4 (code, M) — `factory-task` submits seat jobs: `seat-submit` + `seat-wait` in, the `.result` shape unchanged, `FACTORY_SEAT=direct` fallback

**dependsOn:** S1 (the CLI contract it calls: `seat-submit --workspace … --dsh-home … --mode headless --brief-file … --model … --effort …` printing a job id, `seat-wait <id> --timeout S` printing `output.log`)

**Files:**
- Modify: `tools/factory/seat/factory-task` (the launch block, lines 131–144)
- Modify: `tests/unit/80-seat-driver.bats` (new factory-task cases)

**Interfaces:**
- Consumes S1's CLI and S3's polkit stop grant (`systemctl stop seat@<id>.service` on timeout).
- Produces: `FACTORY_SEAT=seat|direct` (default `seat`). The `.result` file keeps today's exact shape (`factory-task` lines 211–234: the FACTORY-RESULT block, then `run:`/`key:`/`model:`/`effort:`/`route:`/`workspace:`/`branch:`/`head:`/`base:`/`wall_s:`/`exit_code:`, commits, diffstat, usage) — the seat's stdout lands in `$log` via `seat-wait`, so the existing `extract_field` block runs unchanged.

- [ ] **Step 1: Write the failing tests** — append to `tests/unit/80-seat-driver.bats` (its header already sets the convention: scripts run through `bash`, `FACTORY_ROOT` points at the tmpdir, and the file already has a "factory-ws clones a real git repo" test whose repo-fixture idiom these cases reuse):

```bash
# S4: factory-task drives the brokered seat. Stubs for seat-submit,
# seat-wait and systemctl stand in for the systemd boundary (never crossed
# in a build sandbox); the git repo and plan fixtures are real, as in the
# factory-ws cases above.
make_seat_stubs() {
  stub_bin="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$stub_bin"
  cat >"$stub_bin/seat-submit" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$STUB_DIR/seat-submit.argv"
echo "abc123abc123"
EOF
  cat >"$stub_bin/seat-wait" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$STUB_DIR/seat-wait.argv"
cat "$STUB_DIR/seat-output.log"
exit "${STUB_WAIT_RC:-0}"
EOF
  cat >"$stub_bin/systemctl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >> "$STUB_DIR/systemctl.argv"
EOF
  cat >"$stub_bin/zstd" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  chmod +x "$stub_bin"/seat-submit "$stub_bin"/seat-wait "$stub_bin"/systemctl "$stub_bin"/zstd
  export STUB_DIR="$BATS_TEST_TMPDIR"
  export PATH="$stub_bin:$PATH"
}

make_repo_and_plan() {
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$repo/docs/superpowers/plans"
  git -C "$repo" init -q
  git -C "$repo" config user.email t@t && git -C "$repo" config user.name t
  cat >"$repo/docs/superpowers/plans/plan.md" <<'EOF'
## Global Constraints

- Constraint one.

### N17 (code, M) — the seat driver joins the repo

The task body.
EOF
  git -C "$repo" add . && git -C "$repo" commit -qm init
  printf 'FACTORY-RESULT status=done\nFACTORY-CHECKS lint=pass\nFACTORY-COMMITS 1\nFACTORY-NOTES stub seat run\n' \
    > "$BATS_TEST_TMPDIR/seat-output.log"
}

@test "factory-task submits a headless seat job and keeps the .result shape" {
  make_seat_stubs
  make_repo_and_plan
  FACTORY_ROOT="$BATS_TEST_TMPDIR/factory" \
    FACTORY_PLAN="$repo/docs/superpowers/plans/plan.md" \
    FACTORY_RUN=run7 \
    run "$REAL_BASH" "$SEAT/factory-task" run7 "$repo" N17
  [ "$status" -eq 0 ]
  # seat-submit was called with the job contract; the workspace it got is
  # the clone factory-ws made, not the source repo.
  run cat "$BATS_TEST_TMPDIR/seat-submit.argv"
  [[ "$output" == *"--mode headless"* ]]
  [[ "$output" == *"--model"* ]]
  [[ "$output" == *"--effort"* ]]
  [[ "$output" == *"--brief-file"* ]]
  [[ "$output" == *"$BATS_TEST_TMPDIR/factory/ws/run7/N17"* ]]
  [ -f "$BATS_TEST_TMPDIR/seat-wait.argv" ]
  run cat "$BATS_TEST_TMPDIR/factory/runs/run7/N17.result"
  [[ "$output" == *"FACTORY-RESULT status=done"* ]]
  [[ "$output" == *"run: run7"* ]]
  [[ "$output" == *"key: N17"* ]]
  [[ "$output" == *"branch: task/N17"* ]]
  [[ "$output" == *"wall_s: "* ]]
  [[ "$output" == *"exit_code: "* ]]
  [[ "$output" == *"usage: "* ]]
}

@test "factory-task stops the seat job when seat-wait times out" {
  make_seat_stubs
  make_repo_and_plan
  # No FACTORY-RESULT in what the timed-out job printed: the .result must
  # carry the synthesized failure record and a 124, not a fake success.
  printf 'partial output, no result block\n' >"$BATS_TEST_TMPDIR/seat-output.log"
  export STUB_WAIT_RC=1
  FACTORY_ROOT="$BATS_TEST_TMPDIR/factory" \
    FACTORY_PLAN="$repo/docs/superpowers/plans/plan.md" \
    FACTORY_RUN=run7 FACTORY_TIMEOUT=5 \
    run "$REAL_BASH" "$SEAT/factory-task" run7 "$repo" N17
  [ "$status" -ne 0 ]
  run cat "$BATS_TEST_TMPDIR/systemctl.argv"
  [[ "$output" == *"stop seat@abc123abc123.service"* ]]
  run cat "$BATS_TEST_TMPDIR/factory/runs/run7/N17.result"
  [[ "$output" == *"exit_code: 124"* ]]
}

@test "FACTORY_SEAT=direct keeps the pre-seat launch path" {
  make_seat_stubs
  make_repo_and_plan
  cat >"$stub_bin/dsh-openrouter" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$STUB_DIR/direct.argv"
cat "$STUB_DIR/seat-output.log"
EOF
  chmod +x "$stub_bin/dsh-openrouter"
  FACTORY_ROOT="$BATS_TEST_TMPDIR/factory" \
    FACTORY_PLAN="$repo/docs/superpowers/plans/plan.md" \
    FACTORY_RUN=run7 FACTORY_SEAT=direct \
    run "$REAL_BASH" "$SEAT/factory-task" run7 "$repo" N17
  [ "$status" -eq 0 ]
  [ -f "$BATS_TEST_TMPDIR/direct.argv" ]
  [ ! -e "$BATS_TEST_TMPDIR/seat-submit.argv" ]
}
```

- [ ] **Step 2: Red**

```bash
git add tests/unit/80-seat-driver.bats
nix build .#checks.x86_64-linux.unit -L --no-link
```

Expected: FAIL — the first case finds no `seat-submit.argv` (today's factory-task launches `dsh-openrouter` directly, which is not even on the stub PATH, so the run dies on the real binary being absent or on the wrong launch), and the timeout case finds no `systemctl stop` line.

- [ ] **Step 3: Implement** — in `tools/factory/seat/factory-task`, replace the launch block (today's lines 131–144, `factory_log "launching dsh-openrouter …"` through `wall_s=$((end_ts - start_ts))`) with:

```bash
factory_seat=${FACTORY_SEAT:-seat}
factory_log "launching the seat (mode $factory_seat): --model $model --headless in $ws (timeout ${timeout_s}s, log $log)"
start_ts=$(date +%s)
set +e
if [ "$factory_seat" = seat ]; then
  # The brokered seat (plan 2026-09-05-seat-behind-broker, S4): the brief
  # goes to a file, seat-submit writes the job directory and starts
  # seat@<id>; seat-wait prints the job's output.log once the done marker
  # lands. The seat's stdout is this script's stdout, so the FACTORY-RESULT
  # extraction below is byte-for-byte the pre-seat logic.
  brief_file=$(mktemp -p "$runs_dir" ".brief-$key.XXXXXX")
  printf '%s' "$brief" >"$brief_file"
  job_id=$(seat-submit --workspace "$ws" --dsh-home "$dsh_home" --mode headless \
    --brief-file "$brief_file" --model "$model" --effort "$effort")
  factory_log "seat job: $job_id (journalctl -u seat@$job_id.service; job dir /var/lib/seat/jobs/$job_id)"
  (
    timeout -- "$timeout_s" seat-wait "$job_id" --timeout "$timeout_s"
  ) 2>&1 | tee -a -- "$log"
  wait_rc=${PIPESTATUS[0]}
  if [ "$wait_rc" -ne 0 ]; then
    # Timed out (or seat-wait itself failed): the unit may still be running
    # -- the polkit rule grants the operator stop on seat@* exactly for
    # this. 124 keeps the pre-seat timeout semantics for the .result file.
    factory_log "seat job $job_id did not finish in ${timeout_s}s; stopping seat@$job_id.service"
    systemctl stop "seat@$job_id.service" || true
    exit_code=124
  else
    exit_code=0
  fi
else
  # FACTORY_SEAT=direct: the deprecated pre-seat path, kept until the
  # operator deletes ~/.config/openrouter/key (spec §7 -- "tolerates both
  # until the file is gone"); after that the wrapper's "no key" message is
  # the audible end of it.
  (
    cd -- "$ws" &&
      DSH_HOME=$dsh_home \
        OPENROUTER_REASONING_EFFORT=$effort \
        timeout -- "$timeout_s" dsh-openrouter --model "$model" --headless "$brief"
  ) 2>&1 | tee -a -- "$log"
  exit_code=${PIPESTATUS[0]}
fi
set -e
end_ts=$(date +%s)
wall_s=$((end_ts - start_ts))
factory_log "seat exited $exit_code after ${wall_s}s"
```

The `usage_json` block below it is untouched: `$dsh_home/sessions` is the seat job's own dsh-home directory either way, so the transcript discovery keeps working.

- [ ] **Step 4: Green**

```bash
git add tools/factory/seat/factory-task tests/unit/80-seat-driver.bats
nix build .#checks.x86_64-linux.unit -L --no-link
nix develop -c githooks/pre-commit   # shellcheck covers the extensionless factory-task (flake.nix:875)
```

Expected: PASS, including the three new cases.

- [ ] **Step 5: Commit**

```bash
git add tools/factory/seat/factory-task tests/unit/80-seat-driver.bats
nix develop -c git commit -F <msgfile>   # subject below
```

**touches:** tools/factory/seat/factory-task, tests/unit/80-seat-driver.bats
**acceptance:** unit, lint
**commit subject:** `factory: factory-task submits headless jobs to the brokered seat and stops them on timeout; FACTORY_SEAT=direct keeps the pre-seat path; the .result shape is unchanged (test: unit, lint)`

### S5 (code, L) — `seat-vm`: the gate — a fake `openrouter.ai`, one headless job and one web job through the units

**dependsOn:** S1 (submit/run), S2 (`--broker`/`--bind-namespace`), S3 (the module)

**Files:**
- Create: `tests/integration/seat-vm.nix`
- Modify: `flake.nix` (`checks.seat-vm`)

**Interfaces:**
- Consumes: `self.nixosModules.egressBroker`, `self.nixosModules.seat`; S3's `services.seat.baseUrl` (points the seat at the VM's fake); the audit fields `path`/`verdict`/`reason` the broker's `policy.py` writes (the `jq` selectors are the ones `tests/integration/lane-vm.nix:348-351` already runs against the same audit format).
- Produces `checks.seat-vm`, the spec's VM gate (spec, Tests): placeholder-only environment, injection at the broker, `/api/v1/messages` refused before injection, non-allowlisted hosts dropped, the web UI reachable from the host side and nowhere else, both requests in the audit log.

- [ ] **Step 1: Write the failing test** — `tests/integration/seat-vm.nix`, in full:

```nix
{
  pkgs,
  egressBrokerModule,
  seatModule,
}:
let
  # The lane-vm cert recipe (tests/integration/lane-vm.nix:10-24), single
  # host: this seat's broker instance allows exactly "openrouter.test".
  testCerts =
    pkgs.runCommand "seat-vm-test-certs"
      {
        nativeBuildInputs = [ pkgs.openssl ];
      }
      ''
        mkdir -p $out
        openssl req -x509 -newkey rsa:2048 -nodes -days 2 \
          -keyout $out/ca.key -out $out/ca.crt -subj "/CN=seat-vm-test-ca"
        openssl req -newkey rsa:2048 -nodes \
          -keyout $out/openrouter.test.key -out $out/openrouter.test.csr \
          -subj "/CN=openrouter.test" -addext "subjectAltName=DNS:openrouter.test"
        openssl x509 -req -in $out/openrouter.test.csr -CA $out/ca.crt -CAkey $out/ca.key \
          -CAcreateserial -days 2 -copy_extensions copy -out $out/openrouter.test.crt
      '';
  # The canned OpenAI-shaped answer the fake upstream returns to every
  # chat-completions POST; the headless seat job must surface it end to end.
  fakeAnswer = builtins.toJSON {
    id = "gen-1";
    model = "test/model-flash";
    provider = "DeepSeek";
    choices = [
      {
        message = {
          role = "assistant";
          content = "vm-seat-fake-answer";
        };
      }
    ];
    usage = {
      prompt_tokens = 3;
      completion_tokens = 2;
      total_tokens = 5;
    };
  };
  messagesProbeBody = builtins.toJSON {
    model = "m";
    max_tokens = 16;
    messages = [
      {
        role = "user";
        content = "messages-direct-probe";
      }
    ];
  };
  # The lane-vm fake (tests/integration/lane-vm.nix:88-115): a plain stdlib
  # TLS server logging path, Authorization header and body per POST.
  fakeUpstream = pkgs.writeText "seat-vm-fake-upstream.py" ''
    import http.server
    import ssl

    ANSWER = ${builtins.toJSON fakeAnswer}.encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            with open("/var/log/seat-vm-fake-upstream.log", "a") as f:
                f.write(self.path + "\n")
                f.write(self.headers.get("Authorization", "") + "\n")
                f.write(body.decode("utf-8", "replace") + "\n---\n")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(ANSWER)

    httpd = http.server.HTTPServer(("0.0.0.0", 443), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain("${testCerts}/openrouter.test.crt", "${testCerts}/openrouter.test.key")
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    httpd.serve_forever()
  '';
in
pkgs.testers.runNixOSTest {
  name = "seat-openrouter";
  nodes.machine =
    { pkgs, ... }:
    {
      imports = [
        egressBrokerModule
        seatModule
      ];
      security.pki.certificateFiles = [ "${testCerts}/ca.crt" ];
      networking.hosts."127.0.0.1" = [
        "openrouter.test"
        "not-allowed.test"
      ];
      virtualisation.memorySize = 4096;

      environment = {
        etc = {
          "seat-vm-brief.txt".text = "Reply with the word ok.";
          "seat-vm-messages-probe.json".text = messagesProbeBody;
        };
        systemPackages = [ pkgs.curl ];
      };

      users.users.operator = {
        isNormalUser = true;
        uid = 2000;
      };
      users.users.bystander = {
        isNormalUser = true;
        uid = 2001;
      };

      services.seat = {
        enable = true;
        host = "openrouter.test";
        model = "test/model-flash";
        keyFile = "/run/seat-secret";
        hostAddress = "10.100.40.1";
        namespaceAddress = "10.100.40.2";
        listenPort = 3297;
        webPort = 8480;
        baseUrl = "https://openrouter.test/api/v1";
        operatorUser = "operator";
      };

      systemd.services = {
        "egress-broker-seat" = {
          after = [ "seat-secret.service" ];
          requires = [ "seat-secret.service" ];
        };
        fake-upstream = {
          description = "Fake TLS OpenRouter-compatible upstream for the seat VM test";
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            ExecStart = "${pkgs.python3}/bin/python3 ${fakeUpstream}";
            Restart = "on-failure";
          };
        };
        # Stands in for the operator's /var/lib/secrets/openrouter-key: a
        # fixture string, never a real credential; the test greps for it to
        # prove it never leaves the broker.
        seat-secret = {
          wantedBy = [ "multi-user.target" ];
          before = [ "egress-broker-seat.service" ];
          serviceConfig = {
            Type = "oneshot";
            RemainAfterExit = true;
          };
          script = ''
            umask 077
            echo "vm-seat-fake-key" > /run/seat-secret
            chown root:egress-broker /run/seat-secret
            chmod 0440 /run/seat-secret
          '';
        };
        # The operator's writable workspace and dsh-home (the unit runs as
        # User=operator with ProtectSystem=strict; /home is writable because
        # the seat deliberately does not set ProtectHome).
        seat-vm-dirs = {
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            Type = "oneshot";
            RemainAfterExit = true;
          };
          script = ''
            mkdir -p /home/operator/ws /home/operator/dsh-home
            chown -R operator:users /home/operator
          '';
        };
      };
    };
  testScript = ''
    machine.wait_for_unit("fake-upstream.service")
    machine.wait_for_unit("egress-broker-seat.service")
    machine.wait_for_unit("seat-vm-dirs.service")
    machine.wait_until_succeeds(
        "test -f /var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt"
    )

    # 1. a headless seat job runs end to end: submit as the operator, wait
    #    for the done marker, the fake upstream's answer is in the job log.
    job_id = machine.succeed(
        "su - operator -c 'seat-submit --workspace /home/operator/ws "
        "--dsh-home /home/operator/dsh-home --mode headless "
        "--brief-file /etc/seat-vm-brief.txt --model test/model-flash --effort low'"
    ).strip()
    machine.wait_until_succeeds(
        f"test -f /var/lib/seat/jobs/{job_id}/done", timeout=600
    )
    output = machine.succeed(f"cat /var/lib/seat/jobs/{job_id}/output.log")
    assert "vm-seat-fake-answer" in output, output

    # 2. the fake upstream saw the broker-INJECTED credential, while the
    #    unit's environment held only the placeholder.
    api_log = machine.succeed("cat /var/log/seat-vm-fake-upstream.log")
    assert "Bearer vm-seat-fake-key" in api_log, api_log
    environment = machine.succeed(
        f"systemctl show seat@{job_id}.service -p Environment --value"
    )
    assert "OPENROUTER_API_KEY=injected-by-broker" in environment, environment
    assert "vm-seat-fake-key" not in environment, environment
    machine.fail(f"grep -rq vm-seat-fake-key /var/lib/seat/jobs/{job_id}")
    machine.fail("systemctl cat 'seat@.service' | grep -q vm-seat-fake-key")

    # 3. /api/v1/messages is refused BEFORE injection (deny paths as the
    #    lane, fail closed): the client sees the deny, the audit records
    #    path-not-permitted, the fake upstream never sees the path.
    deny_resp = machine.succeed(
        "ip netns exec egress-seat curl -s --max-time 15 "
        "-x http://10.100.40.1:3297 "
        "--cacert /var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt "
        "-X POST -H 'content-type: application/json' "
        "--data-binary @/etc/seat-vm-messages-probe.json "
        "https://openrouter.test/api/v1/messages"
    )
    assert "egress-broker: denied" in deny_resp, deny_resp
    machine.succeed(
        "jq -es '[.[] | select(.path==\"/api/v1/messages\" and "
        ".verdict==\"deny\" and .reason==\"path-not-permitted\")] "
        "| length == 1' /var/lib/egress-broker/seat/audit.jsonl"
    )
    api_log2 = machine.succeed("cat /var/log/seat-vm-fake-upstream.log")
    assert "/api/v1/messages" not in api_log2, api_log2

    # 4. a request to any other host is dropped: the broker's allowlist is
    #    exactly [ openrouter.test ], so a proxy request for not-allowed.test
    #    never reaches an upstream (it resolves to the same fake -- only the
    #    allowlist can be what stops it).
    machine.fail(
        "ip netns exec egress-seat curl -s --max-time 15 "
        "-x http://10.100.40.1:3297 "
        "--cacert /var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt "
        "https://not-allowed.test/api/v1/models"
    )

    # 5. the web seat: the UI answers on 10.100.40.2:8480 from the HOST
    #    side; nothing listens on that port in the host's own namespace;
    #    the forward chain accepts ONLY 8480 (a neighbour port fails).
    web_id = machine.succeed(
        "su - operator -c 'seat-submit --workspace /home/operator/ws "
        "--dsh-home /home/operator/dsh-home-web --mode web "
        "--brief-file /etc/seat-vm-brief.txt --model test/model-flash'"
    ).strip()
    machine.wait_until_succeeds(
        "curl -s --max-time 10 http://10.100.40.2:8480/ -o /dev/null",
        timeout=600,
    )
    web_log = machine.succeed(f"cat /var/lib/seat/jobs/{web_id}/output.log")
    assert "http://10.100.40.2:8480" in web_log, web_log
    machine.fail("ss -tln | grep -q ':8480 '")
    machine.fail("curl -s --max-time 5 http://10.100.40.2:8481/ -o /dev/null")

    # 6. polkit: the operator stops their own web job; the bystander can
    #    neither stop it nor start a job; even the operator cannot restart.
    machine.fail(
        f"su - bystander -c 'systemctl stop seat@{web_id}.service'"
    )
    machine.fail(
        f"su - operator -c 'systemctl restart seat@{web_id}.service'"
    )
    machine.succeed(
        f"su - operator -c 'systemctl stop seat@{web_id}.service'"
    )

    # 7. the audit log carries both brokered requests: the job's chat
    #    completion (allow) beside step 3's deny.
    machine.succeed(
        "jq -es '[.[] | select(.path==\"/api/v1/chat/completions\" and "
        ".verdict==\"allow\")] | length >= 1' "
        "/var/lib/egress-broker/seat/audit.jsonl"
    )
  '';
}
```

Register it in `flake.nix` next to `lane-vm` (`flake.nix:1490-1494`):

```nix
        seat-vm = import ./tests/integration/seat-vm.nix {
          inherit pkgs;
          egressBrokerModule = self.nixosModules.egressBroker;
          seatModule = self.nixosModules.seat;
        };
```

- [ ] **Step 2: Red**

```bash
git add tests/integration/seat-vm.nix flake.nix
nix build .#checks.x86_64-linux.seat-vm -L --no-link
```

Expected: FAIL at step 1 — `seat-submit: command not found` inside the VM if the module's `environment.systemPackages` were missing, but against the landed S1–S3 the meaningful red is produced by *temporarily reverting one load-bearing piece*, which the implementer shows explicitly (pick exactly one, name it in the commit body): run the VM once with the wrapper's `--broker` namespace check neutered (the `ip route show default | grep -q` line removed) **and** the unit's `NetworkNamespacePath` dropped — step 1 then fails TLS/DNS (no broker to reach, no injection), proving the test pins the broker path rather than a direct connection. Restore, then proceed. (The unit/env/proxy pieces each have their own assertion above: removing `inject` fails step 2's `Bearer vm-seat-fake-key`; removing `denyPaths` fails step 3; removing `exposePort` fails step 5.)

- [ ] **Step 3: Green**

```bash
nix build .#checks.x86_64-linux.seat-vm -L --no-link
nix build .#checks.x86_64-linux.lane-vm -L --no-link   # the broker module change must leave the lane's gate green
nix develop -c githooks/pre-commit
```

Expected: PASS. The VM boots the real pinned harness through `services.seat.seatPackage`; `virtualisation.memorySize = 4096` matches the harness's footprint (the same harness boots in the `unit` check's sandbox on loopback).

- [ ] **Step 4: Commit**

```bash
git add tests/integration/seat-vm.nix flake.nix
nix develop -c git commit -F <msgfile>   # subject below
```

**touches:** tests/integration/seat-vm.nix, flake.nix
**acceptance:** seat-vm, lane-vm, lint
**commit subject:** `seat: VM gate — headless and web jobs through the broker with placeholder-only environment, deny-before-injection, host-only web UI, audit coverage (test: seat-vm, lane-vm, lint)`

### S6 (docs, S) — host wiring and the runbooks: `hosts/core/seat.nix`, the backup path + exclusion, host-core assertions, polkit test cases, the migration section

**dependsOn:** S3 (the module it wires), S5 (the gate is green before the host ships it)

**Files:**
- Create: `hosts/core/seat.nix`
- Modify: `hosts/core/default.nix` (imports), `hosts/core/proton-backup.nix` (restic path + exclude), `flake.nix` (`nixosConfigurations.core.modules`; host-core assertions), `tests/lane/polkit.test.mjs` (seat cases), `docs/runbooks/lanes.md` (the seat section + migration), `docs/runbooks/backup.md` (name the path and the exclusion), `tools/factory/seat/README.md` (FACTORY_SEAT), `tools/factory/seat/launch-today.sh` (header comment)

**Interfaces:**
- Consumes S3's `services.seat` option set and S4's `FACTORY_SEAT`.
- Produces the live wiring the Operator section's switch activates; `core-backup-wiring` (`flake.nix:1818-1839`) requires every restic path named in `docs/runbooks/backup.md`, so the path and the doc land in the same commit.

- [ ] **Step 1: The failing assertions** — extend `checks.host-core` (`flake.nix:691-779`): add `s = c.services.egress-broker.instances.seat;` to its `let`, and before `c.system.build.toplevel;`:

```nix
          assert nixpkgs.lib.assertMsg
            (
              s.allow == [ "openrouter.ai" ]
              && s.inject."openrouter.ai".valueFile == "/var/lib/secrets/openrouter-key"
              && s.denyPaths."openrouter.ai".pathPrefixes == [ "/api/v1/messages" ]
              && s.hostAddress == "10.100.4.1"
              && s.namespaceAddress == "10.100.4.2"
              && s.listenPort == 3141
              && s.exposePort == 8480
            )
            "host-core: egress-broker instance 'seat' must allow exactly openrouter.ai, inject /var/lib/secrets/openrouter-key, deny /api/v1/messages, and live on 10.100.4.x:3141 with exposePort 8480";
          assert nixpkgs.lib.assertMsg (nixpkgs.lib.elem "/var/lib/seat" c.services.proton-backup.paths)
            "host-core: /var/lib/seat must be a restic path (seat job payloads are the operator's data)";
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.elem "/var/lib/seat/jobs/*/dsh-home/sessions" c.services.proton-backup.exclude
          ) "host-core: seat dsh session transcripts must be excluded from the backup (the lane's job-dir dsh-home precedent, pkgs/lane/lane-run.py:378)";
          assert nixpkgs.lib.assertMsg (
            nixpkgs.lib.hasInfix "seat@" polkit && nixpkgs.lib.hasInfix "\"stop\"" polkit
          ) "host-core: polkit must grant the operator start and stop on seat@*.service";
```

and extend `tests/lane/polkit.test.mjs` before its final `console.log`:

```javascript
// S6 (seat-behind-broker): the seat rule grants the operator start AND
// stop on seat@*.service (a hung headless seat must be killable), nothing
// else, nobody else.
const SEAT_UNIT = 'seat@abc123abc123.service'

assert.equal(
  decide({ verb: 'start', unit: SEAT_UNIT }, { user: OPERATOR }),
  'yes',
  'operator starting their own seat job must be granted',
)
assert.equal(
  decide({ verb: 'stop', unit: SEAT_UNIT }, { user: OPERATOR }),
  'yes',
  'operator stopping their own seat job must be granted (factory-task timeout)',
)
for (const verb of ['restart', 'kill']) {
  assert.equal(
    decide({ verb, unit: SEAT_UNIT }, { user: OPERATOR }),
    undefined,
    `verb "${verb}" on the seat unit must NOT be granted`,
  )
}
assert.equal(
  decide({ verb: 'start', unit: SEAT_UNIT }, { user: 'eve' }),
  undefined,
  'a non-operator subject must NOT be granted the seat unit',
)
assert.equal(
  decide({ verb: 'start', unit: 'seatx@a.service' }, { user: OPERATOR }),
  undefined,
  'a unit whose prefix merely starts with "seat" minus the "@" must NOT be granted',
)
```

- [ ] **Step 2: Red**

```bash
git add flake.nix tests/lane/polkit.test.mjs
nix build .#checks.x86_64-linux.host-core -L --no-link
nix build .#checks.x86_64-linux.lane-polkit-unit -L --no-link
```

Expected: FAIL — host-core's first new `assertMsg` fires (`instances.seat` missing; evaluating `s.allow` errors), and polkit.test.mjs fails its first seat assertion (`decide(...)` is `undefined` for `seat@…` because core renders no seat rule yet).

- [ ] **Step 3: Implement** — `hosts/core/seat.nix`:

```nix
_: {
  # The operator's seat behind its own broker (spec
  # docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md; plan
  # S3/S6): the same /var/lib/secrets/openrouter-key the lane injects from,
  # address block 10.100.4.x (10.100.2.x media, 10.100.3.x the lane --
  # grep -rn "10\.100\." hosts/ nixosModules/). Nothing here is wantedBy
  # anything: the operator starts jobs with seat-submit, gated by the
  # polkit rule (start+stop) the module renders.
  services.seat = {
    enable = true;
    host = "openrouter.ai";
    model = "deepseek/deepseek-v4-pro-0813";
    keyFile = "/var/lib/secrets/openrouter-key";
    hostAddress = "10.100.4.1";
    namespaceAddress = "10.100.4.2";
    listenPort = 3141;
    webPort = 8480;
  };
}
```

`hosts/core/default.nix`: add `./seat.nix` to the `imports` list (after `./lanes.nix`).

`flake.nix` `nixosConfigurations.core.modules` (`flake.nix:640-656`): add `self.nixosModules.seat` after `self.nixosModules.modelLane`.

`hosts/core/proton-backup.nix`: add `"/var/lib/seat"` to `services.proton-backup.paths` (after `"/var/lib/evidence"`), and below the attrset add:

```nix
  # Seat job payloads (briefs, results) are the operator's data and back
  # up; the dsh session transcripts under each job's dsh-home are
  # regenerable bulk -- the same exclusion the lane's per-job dsh-home
  # embodies by living outside every restic path (pkgs/lane/lane-run.py:378).
  services.proton-backup.exclude = [ "/var/lib/seat/jobs/*/dsh-home/sessions" ];
```

`docs/runbooks/backup.md`: in the paths list (after the `/var/lib/evidence` bullet, lines 29–31) add a bullet naming `/var/lib/seat` ("seat job payloads: briefs, logs, results — transcripts excluded"), and extend the `exclude` paragraph (line 33–34): "`services.proton-backup.exclude` drops `.pytest_cache`, `.ruff_cache`, `~/.cache`, and `/var/lib/seat/jobs/*/dsh-home/sessions` from whatever's underneath those paths."

`docs/runbooks/lanes.md`: retitle the section at line 228 (`## Working with dsh yourself, on the host (dsh-openrouter)`) to `## The seat behind the broker (seat-submit / seat@)` and prepend:

```markdown
Since 2026-09-05 the seat runs behind its own egress-broker instance
`seat` (10.100.4.x, allowlist `openrouter.ai`, `/api/v1/messages` denied
before injection): the broker injects the key from
`/var/lib/secrets/openrouter-key` and no seat process ever holds it — the
unit's environment carries only the placeholder
`OPENROUTER_API_KEY=injected-by-broker`.

    seat-submit --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter \
        --mode headless --brief-file /tmp/brief --model deepseek/deepseek-v4-pro-0813 [--effort high]
    seat-wait <id>                      # prints the job's output.log once done
    seat-submit --workspace ~ --dsh-home ~/.local/share/dsh-openrouter --mode web \
        --brief-file /tmp/brief --model deepseek/deepseek-v4-pro-0813
        # then open http://10.100.4.2:8480 (the unit prints the URL)
    systemctl stop seat@<id>.service    # polkit grants the operator start+stop

`dsh-openrouter` without `--broker` still works during the migration and
prints a deprecation line. Once the acceptance jobs above pass, delete the
plaintext key (Proton Pass stays the vault of record):

    shred -u ~/.config/openrouter/key
```

`tools/factory/seat/README.md`: in the `factory-task` description add the paragraph: "`FACTORY_SEAT=seat` (default) submits the task to the brokered seat (`seat-submit`/`seat-wait`, stopping `seat@<id>` on timeout); `FACTORY_SEAT=direct` is the pre-seat `dsh-openrouter --headless` launch, kept until `~/.config/openrouter/key` is deleted." `tools/factory/seat/launch-today.sh`: extend the header comment with "# 2026-09-05: factory-task now reaches the seat through seat-submit (the brokered seat); this file's factory-wave calls are unaffected." `hosts/core/agent-prereqs.nix` keeps `dsh-openrouter-pkg` installed (the deprecated direct path and `--denials` still need it) — no edit, and say so in the commit body.

The full caller list for the key file, for the reviewer (from `grep -rn "openrouter/key\|\.config/openrouter" -l .`): the wrapper (S2 changed), `factory-task` (S4 changed), `launch-today.sh` (indirect, comment updated here), `hosts/core/agent-prereqs.nix` (install only, unchanged), `docs/runbooks/lanes.md` + `tools/factory/seat/README.md` (updated here), `tests/unit/70-dsh-openrouter.bats` (S2), and the three forbidden-prefix lists (unchanged by design: they refuse *workspaces* under `~/.config/openrouter`, a directory that simply stops existing).

- [ ] **Step 4: Green**

```bash
git add hosts/core/seat.nix hosts/core/default.nix hosts/core/proton-backup.nix flake.nix \
  tests/lane/polkit.test.mjs docs/runbooks/lanes.md docs/runbooks/backup.md \
  tools/factory/seat/README.md tools/factory/seat/launch-today.sh
nix build .#checks.x86_64-linux.host-core -L --no-link
nix build .#checks.x86_64-linux.core-backup-wiring -L --no-link
nix build .#checks.x86_64-linux.lane-polkit-unit -L --no-link
nix build .#checks.x86_64-linux.seat-eval -L --no-link
nix build .#nixosConfigurations.core.config.system.build.toplevel --no-link
nix develop -c githooks/pre-commit
```

Expected: all PASS (the toplevel builds: what the operator's switch would activate).

- [ ] **Step 5: Commit** (host wiring + docs + assertions in one commit — the switch is atomic)

```bash
git add hosts/core/seat.nix hosts/core/default.nix hosts/core/proton-backup.nix flake.nix \
  tests/lane/polkit.test.mjs docs/runbooks/lanes.md docs/runbooks/backup.md \
  tools/factory/seat/README.md tools/factory/seat/launch-today.sh
nix develop -c git commit -F <msgfile>   # subject below
```

**touches:** hosts/core/seat.nix, hosts/core/default.nix, hosts/core/proton-backup.nix, flake.nix, tests/lane/polkit.test.mjs, docs/runbooks/lanes.md, docs/runbooks/backup.md, tools/factory/seat/README.md, tools/factory/seat/launch-today.sh
**acceptance:** host-core, core-backup-wiring, lane-polkit-unit, seat-eval, lint
**commit subject:** `seat: wire the brokered seat onto core — 10.100.4.x instance, /var/lib/seat in the backup with transcripts excluded, host-core assertions, polkit cases, runbooks and the migration note (test: host-core, core-backup-wiring, lane-polkit-unit, seat-eval, lint)`

## Risks and the answers the plan carries

- The interactive seat becomes a systemd job (spec, Risks): the runbook section in S6 gives one command each way (`seat-submit` / `systemctl stop seat@<id>`), and `seat-submit` is the only new habit.
- The unit runs as the operator with the operator's files writable **by design**; what remains denied is enumerated and asserted: `InaccessiblePaths` (secrets, broker state, baskets, Helm, lanes), `ProtectSystem=strict` outside the four `ReadWritePaths`, `NoNewPrivileges`, empty `CapabilityBoundingSet` (all in seat-eval's hardening assertion).
- The placeholder in the environment is printable but authenticates nothing (spec's named gap) — and the `--broker` route check (D5) keeps even the placeholder off the wire to anywhere but the broker.
- `factory-task` during migration: `FACTORY_SEAT=direct` keeps working until the key file is deleted; after deletion the failure is the wrapper's existing, explicit "no key" message, and rollback restores the file from Proton Pass.

## Appendix: tree facts and the commands that produced them

| fact | command |
|---|---|
| spec content, §§1–7 (instance, unit, jobs, `--broker`, web seat, guard, migration, tests) | `read docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md` |
| lane module: unit env/hardening/polkit/tmpfiles shapes; `operatorUser` default; NODE_USE_ENV_PROXY + shim rationale | `read nixosModules/modelLane.nix` (lines 113–117, 200–325) |
| broker module: instance options, inject defaults, nft chains, netns script, CA bundle publish, audit path | `read nixosModules/egressBroker.nix` (lines 29, 35–129, 159–194, 208–279) |
| address blocks in use; 10.100.4.x free | `grep -rn "10\.100\." --include="*.nix" hosts/ nixosModules/ tests/` and `grep -rn "10\.100\.2" --include="*.nix" .` |
| ports 3128/3129/3131/3199 in use; 3141 and 8480 free | `grep -n "listenPort" hosts/core/lanes.nix nixosModules/cowork.nix`; `grep -rn "3141\|8480" --include="*.nix" --include="*.sh" --include="*.py" .` (no hits) |
| wrapper key block, exit codes, `--host` rejection, exec lines | `read pkgs/dsh-openrouter/dsh-openrouter.sh` (lines 1–148, 200–243, 540–582) |
| wrapper sets no proxy env today | `grep -n "NODE_OPTIONS\|NODE_USE_ENV_PROXY\|HTTPS_PROXY" pkgs/dsh-openrouter/dsh-openrouter.sh` (no hits) |
| factory-task launch line and `.result` writer | `read tools/factory/seat/factory-task` (lines 122–144, 211–237) |
| key-file callers | `grep -rn "openrouter/key\|\.config/openrouter" -l .` |
| check names | `read docs/MAP.md` (lines 28–67) |
| lane-eval / lane-assertion-negative / lane-unit / lane-polkit-unit / lane-vm shapes and the eval fixtures | `read flake.nix` (lines 503–559, 616–656, 690–779, 1283–1504, 1735–1787, 1818–1839); `grep -n "laneEvalSystem\|laneBadSystem\|lanePolkitRules" flake.nix` |
| backup paths/exclude and the runbook-naming gate | `read hosts/core/proton-backup.nix`; `read nixosModules/protonBackup.nix` (lines 25–63); `read flake.nix` (lines 1818–1839) |
| lane's per-job dsh-home precedent | `read pkgs/lane/lane-run.py` (lines 360–439; `dsh_home` at line 378) |
| polkit rule is ES5; start-only today; test harness shape | `read tests/lane/polkit.test.mjs`; `read nixosModules/modelLane.nix` (lines 303–325) |
| bats transport-test idioms (`make_key`, `start_fake`, `start_web`/`stop_web`, capture assertions) | `read tests/unit/70-dsh-openrouter.bats` (lines 1–120, 200–300, 441–470) |
| seat-driver test conventions (`FACTORY_ROOT`, `REAL_BASH`, real-git fixtures) | `read tests/unit/80-seat-driver.bats` (lines 1–80) |
| pytest systemctl-monkeypatch seam for submit CLIs | `grep -n "systemctl\|monkeypatch\|LANE_STATE_DIR" tests/lane/test_lane_submit.py` |
| `dsh` is a required arg of the wrapper package | `read pkgs/dsh-openrouter/default.nix` (lines 30–44) |
| `helmPython` = python3 + pytest | `grep -n "helmPython\s*=" flake.nix` (line 112) |
| hosts/core import list | `read hosts/core/default.nix` (imports block) |
| ruff lists in the hook and the lint check | `grep -n "ruff" githooks/pre-commit`; `read flake.nix` (lines 863–891) |
| house format for this plan | `read docs/superpowers/plans/2026-09-05-evidence-store.md` (header, Waves, E1, E8) and `read docs/superpowers/plans/2026-09-05-session-context.md` (G1) |
