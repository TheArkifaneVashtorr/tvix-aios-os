# The seat behind a broker — implementation plan (the GLM 5.3 arm, plan-writing comparison 2026-09-05)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) and `tools/factory/dark-factory.js` both read the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and `commit subject`.

**Goal:** the operator's seat (`dsh-openrouter`) runs behind its own egress-broker instance — the OpenRouter key is injected at the namespace edge from the root-only `/var/lib/secrets/openrouter-key`, no seat process ever holds a real credential, and the plaintext `~/.config/openrouter/key` is deleted after the operator's acceptance run.

**Architecture:** one new NixOS module `nixosModules/seat.nix` — the lane module's shape (`nixosModules/modelLane.nix`) generalised, minus `DynamicUser` and the repo snapshot: it declares `services.egress-broker.instances.seat` (allowlist `openrouter.ai` only, inject from the same key file the lane uses, deny `/api/v1/messages` before injection), a `seat@<job>` systemd template that runs **as the operator** inside `/run/netns/egress-seat`, a start-and-stop polkit rule, and one nftables rule admitting only `hostAddress → 10.100.4.2:<webPort>` into the namespace. Two new stdlib-only CLIs in `pkgs/seat/` — `seat-submit` (the operator's job spool writer) and `seat-run` (the unit's ExecStart) — mirror `pkgs/lane/`. The wrapper `dsh-openrouter` gains `--broker` (no key read, namespace proof) and `--bind-namespace` (namespace-side web bind). `factory-task` submits seat jobs and reads the job directory, keeping its `.result` shape. Gates: `seat-eval` and `seat-assertion-negative` (eval), `seat-vm` (VM, fake `openrouter.ai`), bats under `checks.unit`, and the new pytest check `seat-unit`.

**Tech Stack:** NixOS modules + systemd templates + nftables, the mitmproxy broker (unchanged, `nixosModules/egressBroker.nix`), Python 3 stdlib in `pkgs/seat` (mirroring `pkgs/lane`), pytest, bats, `pkgs.testers.runNixOSTest`, treefmt/ruff/shellcheck/statix/deadnix.

**Spec:** `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md` (approved in approach, 2026-09-05 evening; 39 lines). Executors read the spec and this plan together. Spec §Design items map to tasks: item 1 → SB3; item 2 → SB3; item 3 → SB2, SB5, SB6; item 4 → SB1; item 5 → SB1, SB3, SB4; item 6 → SB1 (no change, asserted); item 7 → §Operator. Spec §Tests map: `seat-eval` → SB3, `seat-vm` → SB4, unit bats → SB1 + SB5, negative assertion → SB3.

## Global Constraints

- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown, no reading `/var/lib/secrets/*`, `~/.config/openrouter/key` or `~/.config/restic/password`. The operator switches (§Operator below).
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` new files **before** any `nix build` (a flake only sees tracked files); never `--no-verify`, never `2>/dev/null` a gated command.
- Every check named in a task's acceptance is run as `nix build .#checks.x86_64-linux.<name> -L --no-link`; the lint gate is `nix develop -c githooks/pre-commit`.
- TDD: the failing check first, shown red, then green. A load-bearing test counts only once it has been shown to fail. Each task below names its **mutation targets** — what a reviewer flips to prove the new tests bite.
- Python is stdlib only in `pkgs/seat` (mirroring `pkgs/lane`); tests may use pytest. `ruff format` (via treefmt) rewraps the blocks below — a reformatting-only difference is not a deviation.
- Bash: shellcheck clean. The lint gate's ruff lists must gain `pkgs/seat tests/seat` (SB2) in **both** places: `githooks/pre-commit` (lines 25–26) and the `lint` check in `flake.nix` (lines 889–890).
- Nix style: statix rejects `{ ... }:` module headers (write `_:` or name the args).
- `touches` is a contract — a file outside it is a deviation to report, not to write.
- No secrets in the repo; every key value in tests is a fixture string (`vm-seat-fake-key`), never a real key.
- Commit subjects: `<area>: summary (test: <check names>)`; the trailer is exactly `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` (plus the seat's own machine-set `Generated-By:` line, per the workspace rules).

## Facts on the tree — each with the command that produced it

Every tree fact this plan relies on, with the exact command run against this checkout (2026-09-05, branch `task/PW1glm`, HEAD `5349582`):

1. The broker names its netns/veth `egress-<name>` / `veb-<name>` / `ven-<name>` and sets the namespace's default route via the host address — `grep -n 'ip netns add\|ip route add default\|ip link add' nixosModules/egressBroker.nix` → `209: ip netns add egress-${name}`, `210: ip link add veb-${name} type veth peer name ven-${name}`, `217: ip netns exec egress-${name} ip route add default via ${i.hostAddress}`. The wrapper's namespace proof (SB1) matches on `dev ven-`.
2. The broker's input chain drops any `veb-<name>` traffic that is not the namespace talking to the broker port, and the **forward** chain drops both directions — `grep -n 'iifname "veb-\${name}"\|oifname "veb-\${name}"' nixosModules/egressBroker.nix` → lines 182–190, incl. `189: iifname "veb-seat" drop` and `190: oifname "veb-seat" drop` (rendered per instance). This is what makes "a request to any other host is dropped by the namespace" true in SB4's VM test, and why host→namespace (an **output**-hook packet, locally originated) needs its own chain (SB3).
3. The broker publishes a public CA bundle per instance at `/var/lib/egress-broker-ca-bundle/<name>/ca-bundle.crt` — `grep -n 'publicDir\|ca-bundle.crt' nixosModules/egressBroker.nix` → `256: publicDir=/var/lib/egress-broker-ca-bundle/${name}`, `277: cp "$dir/ca-bundle.crt" "$publicDir/ca-bundle.crt.tmp"`. The seat unit points `SSL_CERT_FILE`/`NODE_EXTRA_CA_CERTS` at the `seat` copy.
4. The broker's audit log path is per instance — `grep -n 'audit_log' nixosModules/egressBroker.nix` → `29: audit_log = "/var/lib/egress-broker/${name}/audit.jsonl"`. The seat's is `/var/lib/egress-broker/seat/audit.jsonl` (spec item 1).
5. The broker instance options are exactly `hostAddress namespaceAddress prefixLength listenPort allow bodyPatch denyPaths inject` — `read nixosModules/egressBroker.nix` (full; options at lines 41–125). `inject` defaults: header `Authorization`, prefix `Bearer `, paths `[ "/" ]` (lines 108–120).
6. The lane module is the shape to generalise: `DynamicUser = true` (line 262), `NetworkNamespacePath` (261), `UMask = "0027"` (298), `NODE_USE_ENV_PROXY = "1"` (231), `NODE_OPTIONS = "--require ${i.harnessPackage}/lib/proxy-shim.cjs"` (234), `InaccessiblePaths` hides `/run/baskets /var/lib/baskets /var/lib/helm /var/lib/egress-broker /var/lib/secrets /home` (286–293), polkit gates `verb == "start"` only, ES5, to `i.operatorUser` — `grep -n 'DynamicUser\|NetworkNamespacePath\|NODE_USE_ENV_PROXY\|proxy-shim\|UMask\|operatorUser' nixosModules/modelLane.nix`. The lane's key-file tmpfiles rule (`"z ${i.keyFile} 0440 root egress-broker -"`, line 202) already exists for `/var/lib/secrets/openrouter-key`, so the seat adds **no** new tmpfiles rule for the key.
7. The lane's deny path is `denyPaths.${i.host}.pathPrefixes = [ "/api/v1/messages" ]` — `grep -n 'denyPaths' nixosModules/modelLane.nix` → lines 181–183. The seat instance copies it (spec item 1: "Deny paths as the lane").
8. The lane module asserts against the merged broker instances (an assertion may read `config`) — `sed -n '151,154p' nixosModules/modelLane.nix` (`config.services.egress-broker.instances.${name}.allow == [ i.host ]`). SB3's placeholder-key assertion reads the merged `systemd.services."seat@".environment` the same way, and the negative check proves it bites.
9. The wrapper's key block is `dsh-openrouter.sh:220-243` (env key, else `OPENROUTER_KEY_FILE` defaulting to `~/.config/openrouter/key`, mode/owner checks, `die 4`), its option parser is lines 88–131 (`mode=web` default, `--headless` at 105–110, `die 2 "unknown option $1"` at 125), the `--host` rejection and `port_given` scan is 142–148, the workspace forbidden-prefix loop is 201–218, `DSH_CACHE_ROOT`/`XDG_CACHE_HOME` handling is 376–379, the exec lines are 559–582 — `read pkgs/dsh-openrouter/dsh-openrouter.sh` (offsets 37–194, 195–264, 545–582) and `grep -n -E '(--host|--port|port_given|mode=|usage|OPENROUTER_KEY_FILE|die [0-9])' pkgs/dsh-openrouter/dsh-openrouter.sh`.
10. The wrapper's runtime inputs do **not** include iproute2 — `grep -n 'runtimeInputs' -A6 pkgs/dsh-openrouter/default.nix` → `nodejs_22 bubblewrap coreutils findutils zstd` (lines 73–79). SB1 adds `iproute2` (the `ip route` proof needs it).
11. Usage/exit codes documented at `dsh-openrouter.sh:39-65`: `2 usage, 3 refused workspace, 4 key problem, 5 bad value` — SB1 adds `6` (broker misuse). The web exec passes `--host 127.0.0.1` (line 580); the seat passes `--bind-namespace` instead, never `--host` (the 145 rejection stays).
12. The guard refuses `sudo`/`nixos-rebuild`/mutating `systemctl` — `grep -n 'systemctl\|nixos-rebuild\|sudo' pkgs/dsh-openrouter/hook-guard.py` → lines 63–69. Unchanged by this plan (spec item 6); it keeps the seat's agent off the operator's system even though the unit runs as the operator.
13. `factory-task` launches the seat directly today — `read tools/factory/seat/factory-task` (lines 131–141: `DSH_HOME=… timeout -- "$timeout_s" dsh-openrouter --model "$model" --headless "$brief"` teed to the run log; `.result` composed at 211–234; `FACTORY_TIMEOUT` default 10800 at line 19). SB5 replaces the launch block, keeps `.result` byte-shape.
14. The bats suite already boots the real harness against a mock upstream and drives `factory-task` end-to-end with PATH stubs — `read tests/unit/80-seat-driver.bats` (the `factory-task resolves model and effort…` test at line 429 stubs `factory-ws`, `factory-brief`'s shebang, and `dsh-openrouter`; asserts the `.result` lines). SB5 adds a sibling test that stubs `seat-submit` instead; the existing test keeps exercising the fallback path (no `seat-submit` on its PATH → green unchanged).
15. The lane submitter's job id shape and systemctl posture — `grep -n 'uuid4\|systemctl' pkgs/lane/lane-submit.py` → `299: job_id = uuid.uuid4().hex[:12]`, `373: proc = subprocess.run(["systemctl", "start", unit], check=False)` with the journalctl warning at 383–388. `seat-submit` mirrors both.
16. `lane-run.py`'s dsh job disables the harness's own sandbox because "the systemd unit IS the sandbox" — `sed -n '360,371p' pkgs/lane/lane-run.py` (`DSH_PERMISSION_MODE=danger-full-access`, line 426). The seat unit sets the same, with the same rationale (its sandbox is the netns + broker + guard).
17. Existing address blocks: openrouter lane `10.100.3.1/.2` (`hosts/core/lanes.nix:14-15`), cowork `10.100.1.1/.2` (`nixosModules/cowork.nix:174-175`), `10.100.2.x` reserved for media (`hosts/core/lanes.nix:6`) — `grep -rn '10\.100\.' hosts/ nixosModules/`. The spec fixes the seat block as **10.100.4.x** (host `10.100.4.1`, namespace `10.100.4.2`).
18. Existing check names (for `acceptance` lines): `host-core, proton-drive-cli, assertion-positive, assertion-negative, manifests-validate, lint, addon, factory-unit, helm-unit, evidence-unit, claims-validate, ledger-unit, helm-eval, evidence-eval, …, lane-eval, lane-assertion-negative, lane-unit, lane-polkit-unit, lane-vm, integration, …, unit, proton-backup-eval, core-backup-wiring, core-gaming-wiring` — `sed -n '28,70p' docs/MAP.md` (the `## Checks` list). New checks created by this plan: `seat-eval`, `seat-assertion-negative`, `seat-unit`, `seat-vm`.
19. `lane-eval`'s fixture system shape and `lane-assertion-negative`'s tryEval shape — `sed -n '503,545p' flake.nix` (`laneEvalSystem`, `lanePolkitRules`, `laneBadSystem`) and `sed -n '1451,1458p' flake.nix`; `checks.lane-unit` copies `pkgs/lane tests/seat`-style trees into a runCommand sandbox — `sed -n '1459,1479p' flake.nix`. SB2/SB3 mirror these; the two-fixture negative pattern (`helm-control-assertion-negative-agentunit`) is `sed -n '1255,1276p' flake.nix`. The pytest interpreter is `helmPython = pkgs.python3.withPackages (ps: [ ps.pytest ])` — `grep -n 'helmPython =' flake.nix` → line 112.
20. `core-backup-wiring` fails the build if a backup path is not named in `docs/runbooks/backup.md` — `sed -n '1818,1839p' flake.nix` (`undocumented` filter at 1824–1837). SB6 adds `/var/lib/seat` to `paths` (hosts/core/proton-backup.nix:29–42), so `backup.md` must name it in the same task or the check goes red (that red is SB6's step 2).
21. The backup exclude default lives in the module — `grep -n 'exclude = \|"/home/\*/.cache"' nixosModules/protonBackup.nix` → lines 35–40 (`["**/.pytest_cache" "**/.ruff_cache" "/home/*/.cache"]`). SB6 appends `/var/lib/seat/jobs/*/dsh-home/sessions` there (spec item 3). Note: `/var/lib/lanes` is in **no** backup path today (`grep -n 'paths = \|exclude' hosts/core/proton-backup.nix`) — the seat spool is the first lane-shaped spool to be backed up, which is why the spec's exclusion matters.
22. `flake.nix` exports modules at `nixosModules = { … }` (lines 616–626) and `nixosConfigurations.core.modules` lists them (lines 627–648, `self.nixosModules.modelLane` at 644) — `sed -n '616,660p' flake.nix`. `hosts/core/default.nix` imports `./lanes.nix` at line 12 — `grep -n 'lanes' hosts/core/default.nix`.
23. `dshOpenrouter = pkgs.callPackage ./pkgs/dsh-openrouter { dsh = dshHost; }`, `dshHost = pkgs.callPackage ./pkgs/dsh { }` (flake.nix:49–52) — the seat module's `package`/`harnessPackage` defaults call the same two paths.
24. Every current caller of the operator key file (`~/.config/openrouter/key`), for the migration's caller list (spec §Risks) — `grep -rn 'openrouter/key' --include='*.nix' --include='*.sh' --include='*.py' --include='*.md' . | grep -v docs/reviews | grep -v docs/superpowers/plans`:
    - `pkgs/dsh-openrouter/dsh-openrouter.sh:223` — the wrapper's key block itself (dies with "no key" after deletion; SB1 keeps that message);
    - `pkgs/dsh-openrouter/hook-guard.py:87` — the guard's key-spelling rule (stays, becomes moot; spec item 6);
    - `docs/runbooks/lanes.md:244,286,289` — the runbook's key-file sections (SB7 rewrites them);
    - `hosts/core/agent-prereqs.nix:18` — the comment explaining where dsh-openrouter reads its key (SB7's runbook pass also fixes this comment's claim in the module doc, see SB3 step 5);
    - `tools/factory/seat/README.md:21` — "no broker, no netns, no lane" (SB7 rewrites with SB5);
    - `tools/factory/seat/launch-today.sh` — dispatches through `factory-wave` → `factory-task` (SB5 makes that path broker-backed; the launcher itself needs no edit).
25. The claim this closes — `grep -n -A6 'seat-key-exception-undecided' docs/ledger/claims.toml` → lines 165–172 (`status = "gap"`, `owner = "orchestrator"`, `review_by = 2026-09-19`). The flip to `verified` is the orchestrator's, after the operator's acceptance (§Operator).
26. The lane VM test's fake-upstream, fixture-secret and sandbox-probe shapes SB4 mirrors — `read tests/integration/lane-vm.nix` (testCerts 10–24, fakeUpstream 88–115, `lane-secret` service 205–218, `su - operator -c 'lane-submit …'` 273–276, deny probe 338–353, polkit step 457–465).
27. `lane-vm` is wired as `import ./tests/integration/lane-vm.nix { inherit pkgs; egressBrokerModule = …; modelLaneModule = …; }` — `sed -n '1480,1486p' flake.nix`. SB4 wires `seat-vm` identically.
28. The lane polkit rule is exercised by a node test against the real rendered rules — `sed -n '1480,1492p' flake.nix` (`lane-polkit-unit`, `LANE_POLKIT_RULES`) and `ls tests/lane/` → `polkit.test.mjs`. The seat's rule is asserted in `seat-eval` (string shape) and executed in `seat-vm` (polkit denials), so no new polkit check is added.
29. Lint sweeps: `grep -n 'ruff\|shellcheck' githooks/pre-commit` → ruff lists at lines 25–26 (identical lists in the `lint` check, flake.nix:889–890). SB2 appends ` pkgs/seat tests/seat` to both pairs.
30. `docs/MAP.md` is generated; regenerate with `nix develop -c python3 pkgs/evidence/repomap.py --root . write` (CLAUDE.md "Where things are"; the command is also the one the session-start hook prints). SB7 runs it so the four new checks appear.

## Waves

| wave | tasks | dependsOn | notes |
|---|---|---|---|
| 1 | SB1, SB2 | — | disjoint files: SB1 owns `pkgs/dsh-openrouter/*` + `tests/unit/70-dsh-openrouter.bats`; SB2 owns `pkgs/seat/`, `tests/seat/`, `flake.nix` (seat-unit + ruff lists) and `githooks/pre-commit` |
| 2 | SB3, SB5 | SB3: [SB1, SB2]; SB5: [SB2] | disjoint: SB3 owns `flake.nix` this wave (export, fixtures, seat-eval, seat-assertion-negative) plus `nixosModules/seat.nix` and `hosts/core/*`; SB5 owns `tools/factory/seat/*` + `tests/unit/80-seat-driver.bats` |
| 3 | SB4, SB6 | SB4: [SB3]; SB6: [SB3] | SB4 edits `flake.nix` (seat-vm) + `tests/integration/seat-vm.nix`; SB6 touches no flake file (core-backup-wiring reads the paths dynamically) — no conflict |
| 4 | SB7 | SB7: [SB1, SB2, SB3, SB4, SB5, SB6] | docs after every CLI and check it names exists; regenerates `docs/MAP.md` |

Dispatch (wave 1): `FACTORY_PLAN=$HOME/nixos-agent-env/docs/reviews/plan-comparison/2026-09-05-seat-behind-broker-glm.md OPENROUTER_REASONING_EFFORT=medium nohup tools/factory/seat/factory-wave sb1 "$HOME/nixos-agent-env" "SB1" "SB2" >"$HOME/factory/runs/sb1.wave.log" 2>&1 &` — then wave 2 `"SB3" "SB5"`, wave 3 `"SB4" "SB6"`, wave 4 `"SB7"`. Gate: review per task (`tools/factory/seat/factory-review sb1 ~/nixos-agent-env <KEY>`), one bounded fix round, then re-plan (rule A1). Integrate wave by wave with `factory-integrate`.

## Operator

One switch after wave 3 lands (the instance, the netns, the template, polkit, `seat-submit` on PATH, the wrapper's `--broker`, `factory-task`'s new launch path):

```
sudo nixos-rebuild switch --flake ~/nixos-agent-env#core
```

**Acceptance (the operator's, in order; the factory never runs these):**

1. One headless job through the unit:
   `seat-submit --workspace ~/nixos-agent-env --model deepseek/deepseek-v4-pro-0813 <<< 'Reply with the single word ok.'`
   → prints a job id; `journalctl -u seat@<id> -n 20` shows the banner; `/var/lib/seat/jobs/<id>/log` holds the run; `/var/lib/seat/jobs/<id>/exit` says `0`.
2. One web job: `seat-submit --workspace ~/nixos-agent-env --model deepseek/deepseek-v4-pro-0813 --mode web` → open the URL the journal/log prints (`http://10.100.4.2:8790`, one web seat at a time — the nftables rule admits exactly that port); close it with `systemctl stop seat@<id>.service` (polkit allows the operator stop).
3. Confirm the audit shows injected requests: `sudo tail /var/lib/egress-broker/seat/audit.jsonl` — rows for `openrouter.ai` with the injected header, and `path-not-permitted` denials for `/api/v1/messages` if probed.
4. Delete the plaintext key (the runbook's one command): `rm ~/.config/openrouter/key`. From here a direct `dsh-openrouter` (no `--broker`) dies with its existing "no key" message; `factory-task` no longer needs the key at all.
5. Tell the orchestrator; the claim row `seat-key-exception-undecided` (docs/ledger/claims.toml:166) flips `gap` → `verified` with the evidence pointer.

**Rollback:** `sudo nixos-rebuild switch --rollback` (or boot the previous generation). The seat units and the `seat` broker instance vanish with the generation; re-paste the key from Proton Pass with the runbook's one-time command (`docs/runbooks/lanes.md`) if the old launch path is needed again; `factory-task` falls back to the direct launch on its own whenever `seat-submit` is not on PATH.

---

## Tasks

### SB1 (code, M) — the wrapper gains `--broker` and `--bind-namespace`

**dependsOn:** none

**Files:**
- Modify: `pkgs/dsh-openrouter/dsh-openrouter.sh` (usage 37–67; option loop 88–131; broker proof block after the denials dispatch 140; key block 220–243; web exec 569–581), `pkgs/dsh-openrouter/default.nix` (runtimeInputs 73–79)
- Test: `tests/unit/70-dsh-openrouter.bats`

**Interfaces:**
- Consumes nothing new. Produces (SB3's unit and SB5's fallback rely on these exact names):
  - `--broker` — flag. Under it the wrapper (a) never reads or checks any key file (`OPENROUTER_KEY_FILE`/`~/.config/openrouter/key` untouched; a mode-000 canary proves it), (b) keeps `OPENROUTER_API_KEY` as the placeholder when the unit sets it, (c) refuses with **exit 6** unless `ip route show default` names a `ven-*` device (the broker's namespace-side veth, fact 1), (d) in web mode additionally requires `--bind-namespace <port>`.
  - `--bind-namespace <PORT>` — internal flag, accepted only with `--broker` and only in web mode; the wrapper resolves the namespace's global v4 address with `ip -o -4 addr show scope global`, prints `web UI on http://<addr>:<port>`, and execs dsh with `--host <addr> --port <PORT>` instead of `--host 127.0.0.1`. The operator-facing `--host` rejection (line 145) is unchanged.
  - Exit code 6 = broker misuse (usage block documents it).
  - Without `--broker`: behaviour as today, plus one stderr deprecation line after the key block pointing at the seat unit.

- [ ] **Step 1: Write the failing tests.** Append to `tests/unit/70-dsh-openrouter.bats` (the file's `setup()`/`make_key()`/`start_fake()` helpers already exist; the fake upstream and capture file conventions are the ones the existing transport tests use):

```bash
# --- SB1: --broker / --bind-namespace (spec 2026-09-05-seat-behind-broker, item 4) ---

# A stand-in for the broker's namespace-side routing: inside egress-<name> the
# default route leaves via ven-<name> (nixosModules/egressBroker.nix:217). The
# real `ip` in the build sandbox has no such route, so the unstubbbed tests
# below prove the refusal; this stub proves the pass-through.
seat_vm_stub_ip() {
  mkdir -p "$TMPHOME/bin"
  printf '#!/usr/bin/env bash\nprintf "default via 10.100.4.1 dev ven-seat\\n"\n' \
    >"$TMPHOME/bin/ip"
  chmod +x "$TMPHOME/bin/ip"
  PATH="$TMPHOME/bin:$PATH"
}

@test "--broker without --bind-namespace in web mode is a usage error" {
  make_key
  seat_vm_stub_ip
  run dsh-openrouter --broker -- --no-open
  [ "$status" -eq 2 ]
  [[ "$output" == *"--bind-namespace"* ]]
}

@test "--bind-namespace is refused without --broker and in headless mode" {
  make_key
  run dsh-openrouter --bind-namespace 8790
  [ "$status" -eq 2 ]
  seat_vm_stub_ip
  run dsh-openrouter --broker --headless "hi" --bind-namespace 8790
  [ "$status" -eq 2 ]
}

@test "--broker outside the broker namespace refuses with exit 6" {
  make_key
  # The sandbox's real iproute2 shows no ven-* default route -> refusal
  # before anything else; the key file is never opened (die 4 would prove
  # the opposite).
  run dsh-openrouter --broker --headless "hi"
  [ "$status" -eq 6 ]
  [[ "$output" == *"refused"* ]]
  [[ "$output" != *"key"* ]]
}

@test "--broker never opens the key file (mode-000 canary, stub route, mock upstream)" {
  start_fake '{
    "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    "model": "m"
  }'
  make_key sk-or-secret-canary
  chmod 000 "$XDG_CONFIG_HOME/openrouter/key"
  seat_vm_stub_ip
  run dsh-openrouter --broker --headless "Reply with the single word ok."
  [ "$status" -eq 0 ]
  # The run reached the fake upstream (through the env proxy the wrapper
  # composes) and the captured credential stream never contains the canary:
  # the placeholder is what left this process, the real key never existed here.
  ! grep -q "sk-or-secret-canary" "$FAKE_CAPTURE"
  [[ "$output" == *"egress broker"* ]]
  # The canary file is still mode 000 -- nothing rewrote or read it.
  [ "$(stat -c %a "$XDG_CONFIG_HOME/openrouter/key")" = "000" ]
}

@test "without --broker the deprecation line still launches the old way" {
  start_fake '{
    "choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    "model": "m"
  }'
  make_key
  run dsh-openrouter --headless "Reply with the single word ok."
  [ "$status" -eq 0 ]
  [[ "$output" == *"deprecation"*"seat unit"* ]]
}
```

- [ ] **Step 2: Red** — `nix develop -c bats tests/unit/70-dsh-openrouter.bats` → every new test fails: `--broker` hits `die 2 "unknown option $1"` (line 125), the deprecation line does not exist. Show one failure verbatim in the run log.
- [ ] **Step 3: Implement.** In `pkgs/dsh-openrouter/dsh-openrouter.sh`:

  (a) `usage()`: after the `--denials` paragraph (line 48–51) add:

```text
        dsh-openrouter [--model ID] --broker --headless "TASK"
                       (inside a seat@ unit: the egress broker injects the key;
                       no key file is read -- docs/runbooks/lanes.md)
```

  and extend the exit-codes line (65) to: `Exit codes: 2 usage, 3 refused workspace, 4 key problem, 5 bad value, 6 --broker misuse (not inside the broker's namespace).`

  (b) Initialisation beside `mode=web` (line 76): `broker=0` and `bind_ns=`.

  (c) Option loop (before the `--)` case at line 120):

```bash
    --broker)
      broker=1
      shift
      ;;
    --bind-namespace)
      [ $# -ge 2 ] || die 2 "--bind-namespace needs a port"
      bind_ns=$2
      shift 2
      ;;
```

  (d) After the denials dispatch (line 140), before `port_given=`:

```bash
# --broker (the seat behind its broker, spec 2026-09-05-seat-behind-broker,
# item 4): this process must already be inside the broker's namespace -- the
# default route leaves via the broker's namespace-side veth ven-<name>
# (nixosModules/egressBroker.nix's egress-netns sets exactly that). Checked
# BEFORE the key block below, so a mis-launch can never present the
# placeholder as if it were a key.
if [ "$broker" = 1 ]; then
  if [ "$mode" = denials ]; then
    die 2 "--broker changes how the harness reaches its model; --denials only reads transcripts"
  fi
  default_route=$(ip route show default) || die 6 "--broker needs iproute2 to prove it is inside the broker's namespace"
  case $default_route in
    *"dev ven-"*) ;;
    "") die 6 "--broker refused: no default route -- not inside the broker's namespace (run me as a seat@ job; docs/runbooks/lanes.md)" ;;
    *) die 6 "--broker refused: default route is not the broker's veth ($default_route)" ;;
  esac
  if [ "$mode" = web ] && [ -z "$bind_ns" ]; then
    die 2 "--broker web mode needs --bind-namespace <port> (the seat unit passes it)"
  fi
  if [ "$mode" != web ] && [ -n "$bind_ns" ]; then
    die 2 "--bind-namespace applies only to --broker web mode"
  fi
fi
if [ -n "$bind_ns" ] && [ "$broker" = 0 ]; then
  die 2 "--bind-namespace needs --broker"
fi
case $bind_ns in
  "" | *[!0-9]*) [ -n "$bind_ns" ] && die 5 "--bind-namespace port must be a positive integer" ;;
esac
```

  (e) Key block: replace the `if [ -n "${OPENROUTER_API_KEY:-}" ]` head (line 220) with a three-way branch:

```bash
if [ "$broker" = 1 ]; then
  # No key file is read or checked in broker mode. OPENROUTER_API_KEY, when
  # the unit set it, IS the placeholder -- the broker injects the real
  # credential for this host at the namespace edge, so nothing here can
  # spend, print or leak it (spec item 4).
  if [ -n "${OPENROUTER_API_KEY:-}" ]; then
    key_source="placeholder in OPENROUTER_API_KEY (the egress broker injects the real key)"
  else
    key_source="the egress broker (injected at the namespace edge)"
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
fi
```

  (the `elif`/`else` body above is today's lines 223–242, byte-for-byte; only the `if`/first branch and the trailing deprecation below are new). Then, immediately after that block:

```bash
if [ "$broker" = 0 ]; then
  printf 'dsh-openrouter: deprecation: the key-file launch is being replaced by the seat unit behind the broker (--broker under systemd seat@; docs/runbooks/lanes.md)\n' >&2
fi
```

  (f) Web exec (line 569–581): inside the `web)` case, after the two existing `printf` banners and before the `if [ -z "$port_given" ]` block:

```bash
    if [ "$broker" = 1 ]; then
      # --bind-namespace: the UI binds the namespace's own address (the only
      # global v4 address in there is the ven- veth's); nftables on the host
      # admits only hostAddress -> <addr>:<port> (nixosModules/seat.nix).
      # The operator-facing --host rejection above is untouched: nobody on
      # the host can name an address themselves.
      ns_addr=$(ip -o -4 addr show scope global | awk '{print $4; exit}' | cut -d/ -f1)
      [ -n "$ns_addr" ] || die 6 "--broker web mode: no global address in this namespace"
      printf 'dsh-openrouter: web UI on http://%s:%s (inside the broker namespace; open it from the host)\n' "$ns_addr" "$bind_ns" >&2
      exec node --expose-internals "$bin_js" --profile web --patch "$overlay" --host "$ns_addr" --port "$bind_ns" "$@"
    fi
```

  (g) `pkgs/dsh-openrouter/default.nix`: add `pkgs.iproute2` to the wrapper's `runtimeInputs` (after `zstd`; fact 10), with a one-line comment: `# --broker's namespace proof runs ip route (nixosModules/seat.nix's unit)`.

- [ ] **Step 4: Green + full suite.** `nix develop -c bats tests/unit/70-dsh-openrouter.bats` → all green, old tests included (the deprecation line is additive stderr; if any existing byte-exact stderr assertion complains, widen it — the payload tests grep substrings, so none should). Then `nix develop -c githooks/pre-commit` (shellcheck sees the new case arms) and `nix build .#checks.x86_64.unit -L --no-link`.
- [ ] **Step 5: Mutations (for the reviewer).** (i) Delete the `case $default_route` refusal → the exit-6 test goes red with status 2/0. (ii) Let `--broker` fall into the key block (drop the first branch) → the mode-000 canary test dies 4. (iii) Swap `--host "$ns_addr"` for `--host 127.0.0.1` → the web-mode VM check in SB4 later catches it; here the `--bind-namespace` usage test still passes, so name this mutation as SB4's to kill.
- [ ] **Step 6: Commit.**

**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, pkgs/dsh-openrouter/default.nix, tests/unit/70-dsh-openrouter.bats
**acceptance:** unit, lint
**commit subject:** `seat: the wrapper gains --broker and --bind-namespace — no key read, namespace proof, namespace-side bind (test: unit, lint)`

### SB2 (code, M) — `seat-submit` and `seat-run`: the job spool and the unit's runner

**dependsOn:** none

**Files:**
- Create: `pkgs/seat/seat-submit.py`, `pkgs/seat/seat-run.py`, `tests/seat/test_seat_submit.py`, `tests/seat/test_seat_run.py`
- Modify: `flake.nix` (the `checks` attrset gains `seat-unit` after `lane-unit`'s block, ~line 1479; the lint ruff lists at 889–890), `githooks/pre-commit` (ruff lists at lines 25–26)

**Interfaces:**
- Consumes: SB1's `--broker`/`--bind-namespace` flags (invoked by `seat-run` at runtime; the tests here stub `dsh-openrouter`, so SB2 does not depend on SB1 to land, only to run).
- Produces (SB3's unit, SB5's factory-task and SB4's VM test rely on these exact shapes):
  - CLI `seat-submit [--workspace DIR] [--model ID] [--effort off|low|medium|high|xhigh] [--mode headless|web] [--web-port N] [--dsh-home DIR] [--brief FILE]` — brief from `--brief FILE` or stdin; prints the job id; starts `seat@<id>.service` (check=False, warning on non-zero like `lane-submit.py:372-388`); exit 0/1/2.
  - Job-directory contract under `$SEAT_STATE_DIR` (default `/var/lib/seat`) `/jobs/<uuid hex 12>/`, mode 0700, files 0600, all read back by `seat-run`: `workspace` (absolute path; **no snapshot** — the seat edits the operator's real clone), `mode` (`headless`|`web`), `model`, `brief`, optional `effort`, optional `dsh_home` (an existing DSH_HOME; default a fresh `jobs/<id>/dsh-home`), optional `web_port`.
  - CLI `seat-run <job-id>` (the unit's ExecStart): reads the job dir, sets `DSH_HOME` (+ `OPENROUTER_REASONING_EFFORT` when the job carries one), execs `dsh-openrouter --broker --model <model>` + (`--headless <brief>` | `--bind-namespace <port> -- --no-open`), tees the wrapper's stdout+stderr to `jobs/<id>/log` **and** its own stdout (the journal), writes the wrapper's exit code to `jobs/<id>/exit` — the completion signal SB5 and SB4 poll. Exit = the wrapper's exit code; 2 = usage.
  - NixOS env consumed by `seat-run`: `SEAT_STATE_DIR` (spool root), `SEAT_WEB_PORT` (the configured web port, used when the job has no `web_port` file).

- [ ] **Step 1: Write the failing tests** — `tests/seat/test_seat_submit.py`:

```python
"""seat-submit unit tests (plan 2026-09-05-seat-behind-broker-glm, SB2).

seat-submit is driven as a module (main(argv)) with SEAT_STATE_DIR pointed at
tmp_path and subprocess.run monkeypatched -- no systemd, no network, the same
style tests/lane/test_lane_submit.py uses for lane-submit.
"""

import importlib.util
import io
import os
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()


def load(name):
    src = HERE.parents[2] / "pkgs" / "seat" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ss = load("seat_submit")


def test_submit_writes_job_dir_and_starts_unit(tmp_path, monkeypatch, capsys):
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setenv("SEAT_STATE_DIR", str(tmp_path / "state"))
    calls = []

    def fake_run(args, check=False):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(ss.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    brief = tmp_path / "brief.txt"
    brief.write_text("do the thing\n")
    rc = ss.main(
        [
            "--workspace", str(ws),
            "--model", "deepseek/deepseek-v4-pro-0813",
            "--effort", "high",
            "--brief", str(brief),
        ]
    )
    assert rc == 0
    job_id = capsys.readouterr().out.strip()
    assert len(job_id) == 12 and job_id.isalnum()
    job_dir = tmp_path / "state" / "jobs" / job_id
    assert stat.S_IMODE(job_dir.stat().st_mode) == 0o700
    assert (job_dir / "workspace").read_text() == str(ws)
    assert (job_dir / "mode").read_text() == "headless"
    assert (job_dir / "model").read_text() == "deepseek/deepseek-v4-pro-0813"
    assert (job_dir / "brief").read_text() == "do the thing\n"
    assert (job_dir / "effort").read_text() == "high"
    assert not (job_dir / "dsh_home").exists()
    assert stat.S_IMODE((job_dir / "model").stat().st_mode) == 0o600
    assert calls == [["systemctl", "start", f"seat@{job_id}.service"]]


def test_submit_reads_brief_from_stdin_and_records_dsh_home(tmp_path, monkeypatch, capsys):
    ws = tmp_path / "ws"
    ws.mkdir()
    dsh_home = tmp_path / "shared-home"
    dsh_home.mkdir()
    monkeypatch.setenv("SEAT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        ss.subprocess, "run", lambda args, check=False: subprocess.CompletedProcess(args, 0)
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("from stdin\n"))
    rc = ss.main(["--workspace", str(ws), "--model", "m", "--dsh-home", str(dsh_home)])
    assert rc == 0
    job_id = capsys.readouterr().out.strip()
    job_dir = tmp_path / "state" / "jobs" / job_id
    assert (job_dir / "brief").read_text() == "from stdin\n"
    assert (job_dir / "dsh_home").read_text() == str(dsh_home)


def test_submit_web_mode_takes_no_brief_and_web_port(tmp_path, monkeypatch, capsys):
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setenv("SEAT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        ss.subprocess, "run", lambda args, check=False: subprocess.CompletedProcess(args, 0)
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    rc = ss.main(
        ["--workspace", str(ws), "--model", "m", "--mode", "web", "--web-port", "8790"]
    )
    assert rc == 0
    job_id = capsys.readouterr().out.strip()
    job_dir = tmp_path / "state" / "jobs" / job_id
    assert (job_dir / "mode").read_text() == "web"
    assert (job_dir / "web_port").read_text() == "8790"


def test_submit_refusals(tmp_path, monkeypatch):
    monkeypatch.setenv("SEAT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    # missing workspace
    rc = ss.main(["--workspace", str(tmp_path / "nope"), "--model", "m"])
    assert rc == 1
    # headless with an empty brief
    ws = tmp_path / "ws"
    ws.mkdir()
    rc = ss.main(["--workspace", str(ws), "--model", "m"])
    assert rc == 1
    # --dsh-home that does not exist
    rc = ss.main(
        ["--workspace", str(ws), "--model", "m", "--dsh-home", str(tmp_path / "gone"), "--brief", "-"]
    )
    assert rc == 1


def test_submit_warns_but_returns_zero_when_start_fails(tmp_path, monkeypatch, capsys):
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setenv("SEAT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(
        ss.subprocess,
        "run",
        lambda args, check=False: subprocess.CompletedProcess(args, 1),
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("b\n"))
    rc = ss.main(["--workspace", str(ws), "--model", "m"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "systemctl start" in err and "journalctl" in err
```

  and `tests/seat/test_seat_run.py`:

```python
"""seat-run unit tests (plan 2026-09-05-seat-behind-broker-glm, SB2).

A fake dsh-openrouter on PATH records argv and the interesting environment,
prints a FACTORY-RESULT block, and exits with $SEAT_FAKE_RC (default 0).
"""

import importlib.util
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))  # reuse the loader from test_seat_submit
from test_seat_submit import load  # noqa: E402

sr = load("seat_run")

FAKE_DSH = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$SEAT_FAKE_ARGS"
printf 'DSH_HOME=%s\\n' "${DSH_HOME:-}" >> "$SEAT_FAKE_ARGS"
printf 'EFFORT=%s\\n' "${OPENROUTER_REASONING_EFFORT:-}" >> "$SEAT_FAKE_ARGS"
printf 'FACTORY-RESULT status=done\\n'
printf 'FACTORY-NOTES seat-run tee\\n'
exit "${SEAT_FAKE_RC:-0}"
"""


def _make_job(state, job_id="j0b1d", **files):
    job_dir = state / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (job_dir / name).write_text(text)
    return job_dir


def _fake_dsh(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "dsh-openrouter"
    script.write_text(FAKE_DSH)
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return script


def test_headless_passes_broker_flags_and_tees(tmp_path, monkeypatch, capfd):
    state = tmp_path / "state"
    ws = tmp_path / "ws"
    ws.mkdir()
    _fake_dsh(tmp_path, monkeypatch)
    _make_job(
        state,
        workspace=str(ws),
        mode="headless",
        model="deepseek/deepseek-v4-pro-0813",
        brief="say ok\n",
        effort="xhigh",
    )
    monkeypatch.setenv("SEAT_STATE_DIR", str(state))
    args_file = tmp_path / "args"
    monkeypatch.setenv("SEAT_FAKE_ARGS", str(args_file))
    rc = sr.main(["j0b1d"])
    assert rc == 0
    argv = args_file.read_text()
    assert "--broker" in argv
    assert "--model" in argv and "deepseek/deepseek-v4-pro-0813" in argv
    assert "--headless" in argv and "say ok" in argv
    assert f"DSH_HOME={state / 'jobs' / 'j0b1d' / 'dsh-home'}" in argv
    assert "EFFORT=xhigh" in argv
    job_dir = state / "jobs" / "j0b1d"
    log = (job_dir / "log").read_text()
    assert "FACTORY-RESULT status=done" in log
    assert (job_dir / "exit").read_text() == "0"
    # the tee reached our own stdout too (the journal, in the real unit)
    assert "FACTORY-RESULT status=done" in capfd.readouterr().out
    assert stat.S_IMODE((job_dir / "exit").stat().st_mode) == 0o600


def test_headless_honours_job_dsh_home(tmp_path, monkeypatch):
    state = tmp_path / "state"
    ws = tmp_path / "ws"
    ws.mkdir()
    home = tmp_path / "shared"
    home.mkdir()
    _fake_dsh(tmp_path, monkeypatch)
    _make_job(state, workspace=str(ws), mode="headless", model="m", brief="b", dsh_home=str(home))
    monkeypatch.setenv("SEAT_STATE_DIR", str(state))
    args_file = tmp_path / "args"
    monkeypatch.setenv("SEAT_FAKE_ARGS", str(args_file))
    rc = sr.main(["j0b1d"])
    assert rc == 0
    assert f"DSH_HOME={home}" in args_file.read_text()


def test_web_mode_binds_namespace_port_and_no_open(tmp_path, monkeypatch):
    state = tmp_path / "state"
    ws = tmp_path / "ws"
    ws.mkdir()
    _fake_dsh(tmp_path, monkeypatch)
    _make_job(state, workspace=str(ws), mode="web", model="m", brief="")
    monkeypatch.setenv("SEAT_STATE_DIR", str(state))
    monkeypatch.setenv("SEAT_WEB_PORT", "8790")
    args_file = tmp_path / "args"
    monkeypatch.setenv("SEAT_FAKE_ARGS", str(args_file))
    rc = sr.main(["j0b1d"])
    assert rc == 0
    argv = args_file.read_text()
    assert "--bind-namespace" in argv and "8790" in argv
    assert "--no-open" in argv
    assert "--headless" not in argv


def test_job_web_port_beats_the_unit_env(tmp_path, monkeypatch):
    state = tmp_path / "state"
    ws = tmp_path / "ws"
    ws.mkdir()
    _fake_dsh(tmp_path, monkeypatch)
    _make_job(state, workspace=str(ws), mode="web", model="m", brief="", web_port="9001")
    monkeypatch.setenv("SEAT_STATE_DIR", str(state))
    monkeypatch.setenv("SEAT_WEB_PORT", "8790")
    args_file = tmp_path / "args"
    monkeypatch.setenv("SEAT_FAKE_ARGS", str(args_file))
    rc = sr.main(["j0b1d"])
    assert rc == 0
    argv = args_file.read_text()
    assert "9001" in argv and "8790" not in argv


def test_web_without_any_port_refuses(tmp_path, monkeypatch):
    state = tmp_path / "state"
    ws = tmp_path / "ws"
    ws.mkdir()
    _fake_dsh(tmp_path, monkeypatch)
    _make_job(state, workspace=str(ws), mode="web", model="m", brief="")
    monkeypatch.setenv("SEAT_STATE_DIR", str(state))
    monkeypatch.delenv("SEAT_WEB_PORT", raising=False)
    assert sr.main(["j0b1d"]) == 2


def test_headless_without_brief_refuses(tmp_path, monkeypatch):
    state = tmp_path / "state"
    ws = tmp_path / "ws"
    ws.mkdir()
    _fake_dsh(tmp_path, monkeypatch)
    _make_job(state, workspace=str(ws), mode="headless", model="m", brief="")
    monkeypatch.setenv("SEAT_STATE_DIR", str(state))
    assert sr.main(["j0b1d"]) == 2


def test_missing_job_dir_refuses(tmp_path, monkeypatch):
    monkeypatch.setenv("SEAT_STATE_DIR", str(tmp_path / "state"))
    assert sr.main(["n0pe"]) == 2


def test_nonzero_wrapper_exit_is_recorded(tmp_path, monkeypatch):
    state = tmp_path / "state"
    ws = tmp_path / "ws"
    ws.mkdir()
    _fake_dsh(tmp_path, monkeypatch)
    _make_job(state, workspace=str(ws), mode="headless", model="m", brief="b")
    monkeypatch.setenv("SEAT_STATE_DIR", str(state))
    monkeypatch.setenv("SEAT_FAKE_RC", "7")
    args_file = tmp_path / "args"
    monkeypatch.setenv("SEAT_FAKE_ARGS", str(args_file))
    rc = sr.main(["j0b1d"])
    assert rc == 7
    assert (state / "jobs" / "j0b1d" / "exit").read_text() == "7"
```

- [ ] **Step 2: Red.** With only the two test files in place (no `pkgs/seat/` yet), run `nix develop -c python3 -m pytest tests/seat -q` → the loaders fail at collection: `FileNotFoundError`/`StopIteration` for `pkgs/seat/seat-submit.py` and `pkgs/seat/seat-run.py`. Also `nix build .#checks.x86_64-linux.seat-unit -L --no-link` → `flake does not provide attribute` (the check is not wired yet). Record both reds verbatim.
- [ ] **Step 3: Implement.** `pkgs/seat/seat-submit.py`:

```python
"""Operator CLI for the seat behind its broker (spec
docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md, item 3).

Writes one job directory under SEAT_STATE_DIR/jobs/<id>/ (default
/var/lib/seat) and starts seat@<id>.service. The unit runs as the same user
that submits (the operator -- no DynamicUser, no group dance), so the spool
is plain 0700 operator-owned.

Job files (all read back by pkgs/seat/seat-run.py):
    workspace  absolute path of the tree the seat works on. No snapshot is
               taken -- the seat edits the operator's real clone, that is
               the point of it (spec item 2). The wrapper's own
               forbidden-prefix check (dsh-openrouter.sh:201-218, unchanged)
               is the local-only refusal point for a workspace; this CLI does
               not duplicate that list (claim forbidden-list-single-source).
    mode       headless | web
    model      OpenRouter model id
    brief      task text (headless); may be empty for web
    effort     optional OPENROUTER_REASONING_EFFORT
    dsh_home   optional existing DSH_HOME (factory-task passes its per-run
               home); default: a fresh jobs/<id>/dsh-home that seat-run makes
    web_port   optional web UI port (tests; production web jobs use the port
               configured on the unit -- nftables admits exactly that one)

Stdlib only, mirroring pkgs/lane/lane-submit.py.
"""

import argparse
import os
import subprocess
import sys
import uuid


def _write_file(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(path, 0o600)


def main(argv=None):
    p = argparse.ArgumentParser(prog="seat-submit")
    p.add_argument("--workspace", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--effort", choices=["off", "low", "medium", "high", "xhigh"])
    p.add_argument("--mode", choices=["headless", "web"], default="headless")
    p.add_argument("--web-port", type=int)
    p.add_argument("--dsh-home")
    p.add_argument("--brief", help="file holding the task text; default: stdin")
    args = p.parse_args(argv)

    if args.brief:
        try:
            with open(args.brief, encoding="utf-8") as f:
                brief = f.read()
        except OSError as e:
            print(f"seat-submit: cannot read --brief {args.brief}: {e}", file=sys.stderr)
            return 1
    else:
        brief = sys.stdin.read()
    if args.mode == "headless" and not brief.strip():
        print("seat-submit: headless needs a non-empty brief (--brief FILE or stdin)", file=sys.stderr)
        return 1

    workspace = os.path.realpath(os.path.expanduser(args.workspace))
    if not os.path.isdir(workspace):
        print(f"seat-submit: --workspace {args.workspace} is not a directory", file=sys.stderr)
        return 1
    dsh_home = None
    if args.dsh_home:
        dsh_home = os.path.realpath(os.path.expanduser(args.dsh_home))
        if not os.path.isdir(dsh_home):
            print(f"seat-submit: --dsh-home {args.dsh_home} is not a directory", file=sys.stderr)
            return 1

    state = os.environ.get("SEAT_STATE_DIR", "/var/lib/seat")
    job_id = uuid.uuid4().hex[:12]
    job_dir = os.path.join(state, "jobs", job_id)
    try:
        os.makedirs(job_dir, mode=0o700)
    except OSError as e:
        print(f"seat-submit: cannot create {job_dir}: {e}", file=sys.stderr)
        return 1
    os.chmod(job_dir, 0o700)  # makedirs' mode meets the caller's umask

    files = {"workspace": workspace, "mode": args.mode, "model": args.model, "brief": brief}
    if args.effort:
        files["effort"] = args.effort
    if dsh_home:
        files["dsh_home"] = dsh_home
    if args.web_port:
        files["web_port"] = str(args.web_port)
    for name, text in files.items():
        _write_file(os.path.join(job_dir, name), text)

    unit = f"seat@{job_id}.service"
    # check=False, mirroring pkgs/lane/lane-submit.py:363-388 -- a non-zero
    # start is not the job's outcome (the unit is Type=exec; the job's own
    # result is the exit/ file seat-run writes), it means systemd could not
    # run the unit at all (bad netns, unknown user). Warn with the journal
    # command, still print the id.
    proc = subprocess.run(["systemctl", "start", unit], check=False)
    if proc.returncode != 0:
        print(
            f"seat-submit: warning: systemctl start {unit} exited {proc.returncode} "
            f"-- check journalctl -u {unit}",
            file=sys.stderr,
        )
    print(job_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

  `pkgs/seat/seat-run.py`:

```python
"""Job runner for the seat behind its broker: ExecStart of seat@<job-id>
(nixosModules/seat.nix), the seat-side mirror of pkgs/lane/lane-run.py.

Reads the job directory pkgs/seat/seat-submit.py wrote (one small file per
input, no JSON to keep operator debugging trivial) and exec's the
dsh-openrouter wrapper with --broker: the unit's environment (set by the
module) already carries HTTPS_PROXY/HTTP_PROXY, the CA bundle, the
placeholder OPENROUTER_API_KEY and DSH_PERMISSION_MODE. This process never
reads, holds or sends a credential -- the placeholder in the environment is
overwritten by the broker at the namespace edge.

Outputs, back into the job directory:
    log   the wrapper's stdout+stderr, teed so systemd's journal carries it
          too (our own stdout IS the journal under the unit)
    exit  the wrapper's exit code -- the completion signal factory-task
          (tools/factory/seat/factory-task, SB5) and the VM check (SB4) poll

Stdlib only.
"""

import os
import subprocess
import sys

EXIT_ERROR = 1
EXIT_USAGE = 2


def _read(job_dir, name):
    try:
        with open(os.path.join(job_dir, name), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def main(argv):
    if len(argv) != 2:
        print("usage: seat-run <job-id>", file=sys.stderr)
        return EXIT_USAGE
    job_id = argv[1]
    state = os.environ.get("SEAT_STATE_DIR", "/var/lib/seat")
    job_dir = os.path.join(state, "jobs", job_id)
    if not os.path.isdir(job_dir):
        print(f"seat-run: no job directory {job_dir}", file=sys.stderr)
        return EXIT_USAGE

    mode = (_read(job_dir, "mode") or "").strip()
    model = (_read(job_dir, "model") or "").strip()
    workspace = (_read(job_dir, "workspace") or "").strip()
    brief = _read(job_dir, "brief") or ""
    effort = (_read(job_dir, "effort") or "").strip()
    dsh_home = (_read(job_dir, "dsh_home") or "").strip()

    if mode not in ("headless", "web"):
        print(f"seat-run: job {job_id} has no usable mode (got {mode!r})", file=sys.stderr)
        return EXIT_USAGE
    if not model:
        print(f"seat-run: job {job_id} has no model", file=sys.stderr)
        return EXIT_USAGE
    if not workspace or not os.path.isdir(workspace):
        print(f"seat-run: job {job_id} has no usable workspace (got {workspace!r})", file=sys.stderr)
        return EXIT_USAGE
    if mode == "headless" and not brief.strip():
        print(f"seat-run: job {job_id} is headless with an empty brief", file=sys.stderr)
        return EXIT_USAGE
    web_port = (_read(job_dir, "web_port") or "").strip() or os.environ.get("SEAT_WEB_PORT", "")
    if mode == "web" and not web_port.isdigit():
        print(
            f"seat-run: web job {job_id} needs a port (job web_port or SEAT_WEB_PORT)",
            file=sys.stderr,
        )
        return EXIT_USAGE

    if not dsh_home:
        dsh_home = os.path.join(job_dir, "dsh-home")
    os.makedirs(dsh_home, exist_ok=True)

    env = dict(os.environ)
    env["DSH_HOME"] = dsh_home
    if effort:
        env["OPENROUTER_REASONING_EFFORT"] = effort

    args = ["dsh-openrouter", "--broker", "--model", model]
    if mode == "headless":
        args += ["--headless", brief]
    else:
        args += ["--bind-namespace", web_port, "--", "--no-open"]

    log_path = os.path.join(job_dir, "log")
    with open(log_path, "ab", buffering=0) as log:
        try:
            proc = subprocess.Popen(
                args,
                cwd=workspace,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except OSError as e:
            log.write(f"seat-run: cannot exec dsh-openrouter: {e}\n".encode())
            with open(os.path.join(job_dir, "exit"), "w", encoding="utf-8") as f:
                f.write(str(EXIT_ERROR))
            return EXIT_ERROR
        assert proc.stdout is not None
        for chunk in iter(lambda: proc.stdout.read(4096), b""):
            log.write(chunk)
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
        rc = proc.wait()
    with open(os.path.join(job_dir, "exit"), "w", encoding="utf-8") as f:
        f.write(str(rc))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Wire the check + lint lists.** In `flake.nix`, after the `lane-vm` binding (~line 1486):

```nix
        seat-unit =
          pkgs.runCommand "seat-unit-tests"
            {
              nativeBuildInputs = [ helmPython ];
            }
            ''
              mkdir -p pkgs tests
              cp -r ${self}/pkgs/seat pkgs/seat
              cp -r ${self}/tests/seat tests/seat
              pytest tests/seat -q
              touch $out
            '';
```

  (`helmPython` is the pytest-carrying interpreter `lane-unit` already uses — fact 19.) Append ` pkgs/seat tests/seat` to the two ruff invocations in the `lint` check (flake.nix:889–890) and to the two in `githooks/pre-commit` (lines 25–26) — all four lists must stay identical.
- [ ] **Step 5: Green.** `git add pkgs/seat tests/seat flake.nix githooks/pre-commit` (before any `nix build`), then `nix develop -c ruff format pkgs/seat tests/seat`, `nix develop -c python3 -m pytest tests/seat -q` → green, `nix build .#checks.x86_64-linux.seat-unit -L --no-link` → green, `nix develop -c githooks/pre-commit` → green, `nix build .#checks.x86_64-linux.lint -L --no-link` → green.
- [ ] **Step 6: Mutations (for the reviewer).** (i) In `seat-run.py`, drop `"--broker"` from `args` → `test_headless_passes_broker_flags_and_tees` red. (ii) Swap the `exit` file write to a constant `"0"` → `test_nonzero_wrapper_exit_is_recorded` red. (iii) In `seat-submit.py`, remove the 0700 chmod → the mode assertion red.
- [ ] **Step 7: Commit.**

**touches:** pkgs/seat/seat-submit.py, pkgs/seat/seat-run.py, tests/seat/test_seat_submit.py, tests/seat/test_seat_run.py, flake.nix, githooks/pre-commit
**acceptance:** seat-unit, lint
**commit subject:** `seat: seat-submit and seat-run — job spool, unit runner, tests, seat-unit check (test: seat-unit, lint)`

### SB3 (code, M) — `nixosModules/seat.nix`: the `seat` broker instance, the `seat@` template, polkit, nftables, host wiring

**dependsOn:** SB1, SB2

**Files:**
- Create: `nixosModules/seat.nix`, `hosts/core/seat.nix`
- Modify: `flake.nix` (`nixosModules` export ~line 616–626; `nixosConfigurations.core.modules` list ~line 644; new `seatEvalSystem`, `seatBadKeySystem`, `seatBadAddressSystem` fixtures beside `laneEvalSystem` ~line 503; new checks `seat-eval`, `seat-assertion-negative` after the lane checks), `hosts/core/default.nix` (imports, line 12 area)

**Interfaces:**
- Consumes: SB1's `--broker`/`--bind-namespace`; SB2's `pkgs/seat/seat-submit.py`, `pkgs/seat/seat-run.py` (wrapped here exactly the way `nixosModules/modelLane.nix` wraps `pkgs/lane/lane-submit.py`), and the job-dir env contract `SEAT_STATE_DIR`/`SEAT_WEB_PORT`.
- Produces (SB4 and SB6 rely on these exact names):
  - NixOS options under `services.seat`: `enable` (bool, default `false`), `host` (str), `keyFile` (str), `hostAddress` (str), `namespaceAddress` (str), `listenPort` (port, default `3132`), `webPort` (port, default `8790`), `operatorUser` (str, default `"dalhaka"`), `stateDir` (str, default `"/var/lib/seat"`), `extraReadWritePaths` (list of str, default `[ ]`), `package` (the dsh-openrouter wrapper, default `pkgs.callPackage ../pkgs/dsh-openrouter { dsh = pkgs.callPackage ../pkgs/dsh { }; }`), `harnessPackage` (default `pkgs.callPackage ../pkgs/dsh { }`).
  - The broker instance `services.egress-broker.instances.seat`: `allow = [ host ]`, `inject.${host}.valueFile = keyFile`, `denyPaths.${host}.pathPrefixes = [ "/api/v1/messages" ]` — and **no** `bodyPatch` (the wrapper prints "zero-data-retention is an OpenRouter account setting", `dsh-openrouter.sh:572`; the lane's chokepoint patch is a lane decision, `modelLane.nix:164-172`).
  - The unit `seat@<job>.service`: `Type = "exec"`, `User = operatorUser` (**not** DynamicUser), `NetworkNamespacePath = "/run/netns/egress-seat"`, environment `HTTPS_PROXY`/`HTTP_PROXY = "http://<hostAddress>:<listenPort>"`, `SSL_CERT_FILE = NODE_EXTRA_CA_CERTS = "/var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt"`, `NODE_USE_ENV_PROXY = "1"`, `NODE_OPTIONS = "--require <harnessPackage>/lib/proxy-shim.cjs"`, `OPENROUTER_API_KEY = "injected-by-broker"`, `DSH_PERMISSION_MODE = "danger-full-access"` (the unit IS the sandbox, `lane-run.py:360-371` precedent), `SEAT_STATE_DIR = stateDir`, `SEAT_WEB_PORT = toString webPort`; serviceConfig hardening `NoNewPrivileges`, `ProtectSystem = "strict"`, `ProtectHome = "read-only"`, `ReadWritePaths = [ "/home/<operatorUser>/factory" "/home/<operatorUser>/nixos-agent-env" "/home/<operatorUser>/flakes" stateDir ] ++ extraReadWritePaths`, `PrivateTmp`, `CapabilityBoundingSet = ""`, `RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX"`, `UMask = "0077"`, `InaccessiblePaths = ["-/run/baskets" "-/var/lib/baskets" "-/var/lib/helm" "-/var/lib/egress-broker" "-/var/lib/lanes" "-/var/lib/secrets"]`, `TimeoutStopSec = "30s"`, `ExecStart = "<seatRun>/bin/seat-run %i"`.
  - tmpfiles: `d <stateDir> 0700 <operatorUser> users -` and `d <stateDir>/jobs 0700 <operatorUser> users -`. No new rule for the key file (the lane's `z 0440` rule already covers `/var/lib/secrets/openrouter-key`, fact 6).
  - polkit (ES5, `modelLane.nix:308-325` shape, plus **stop**): start and stop of `seat@*.service` allowed to `operatorUser` only.
  - nftables: `networking.nftables.tables.seat-web` — an **output**-hook chain (host→namespace traffic is locally originated; the broker's forward chain already drops forwarded `veb-seat` traffic, fact 2): `oifname "veb-seat" ct state established,related accept`, then `oifname "veb-seat" ip saddr <hostAddress> ip daddr <namespaceAddress> tcp dport <webPort> accept`, then `oifname "veb-seat" drop`.
  - `environment.systemPackages = [ seat-submit ]` (`seat-run` is unit-only).
  - Module assertions (the `seat-assertion-negative` check proves two of them bite): keyFile outside `/nix/store`; the seat's two addresses collide with **no** other egress-broker instance's addresses (10.100.2.x/3.x are taken, fact 17); no `extraReadWritePaths` entry under `/var/lib/secrets`; the merged `seat@` unit's `OPENROUTER_API_KEY` is exactly `"injected-by-broker"`.

- [ ] **Step 1: Red.** `nix build .#checks.x86_64-linux.seat-eval -L --no-link` → `flake does not provide attribute 'checks.x86_64-linux.seat-eval'` (same for `seat-assertion-negative`). Both check names are created by this task; record the error verbatim.
- [ ] **Step 2: Implement the module** — `nixosModules/seat.nix` in full:

```nix
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.seat;
  # The placeholder (spec item 2): the broker replaces the Authorization
  # header for cfg.host at the namespace edge; a request the broker refuses
  # never carries a real key. A string an agent can print, but it
  # authenticates nothing.
  placeholder = "injected-by-broker";
  caBundle = "/var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt";
  seatSubmit = pkgs.writeShellApplication {
    name = "seat-submit";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 ${../pkgs/seat/seat-submit.py} "$@"
    '';
  };
  seatRun = pkgs.writeShellApplication {
    name = "seat-run";
    runtimeInputs = [
      pkgs.python3
      cfg.package
    ];
    text = ''
      exec python3 ${../pkgs/seat/seat-run.py} "$@"
    '';
  };
in
{
  options.services.seat = {
    enable = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "The operator's seat behind its own egress broker: one instance, one seat@ job template (spec docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md).";
    };
    host = lib.mkOption {
      type = lib.types.str;
      description = "The single upstream hostname the seat's broker instance allows (openrouter.ai).";
    };
    keyFile = lib.mkOption {
      type = lib.types.str;
      description = "Path to the API key file the broker injects. Same file the lane uses (/var/lib/secrets/openrouter-key); never read by this module or any seat process.";
    };
    hostAddress = lib.mkOption {
      type = lib.types.str;
      description = "Host-side veth address (the seat's block is 10.100.4.x).";
    };
    namespaceAddress = lib.mkOption {
      type = lib.types.str;
      description = "Netns-side veth address; the web UI binds this.";
    };
    listenPort = lib.mkOption {
      type = lib.types.port;
      default = 3132;
      description = "Broker listen port inside the seat's netns.";
    };
    webPort = lib.mkOption {
      type = lib.types.port;
      default = 8790;
      description = "The one TCP port nftables admits from the host into the namespace for the web seat's UI. One web seat at a time by design.";
    };
    operatorUser = lib.mkOption {
      type = lib.types.str;
      default = "dalhaka";
      description = "The user the seat@ unit runs as (not DynamicUser: the seat edits this user's clones) and the only polkit-allowed starter/stopper.";
    };
    stateDir = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/seat";
      description = "Job spool root (0700 operator).";
    };
    extraReadWritePaths = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Extra ReadWritePaths for the seat@ unit beyond the operator's factory/checkout/flakes trees and the spool. Never under /var/lib/secrets (asserted).";
    };
    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ../pkgs/dsh-openrouter { dsh = pkgs.callPackage ../pkgs/dsh { }; };
      description = "The dsh-openrouter wrapper (flake.nix's dshOpenrouter shape).";
    };
    harnessPackage = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ../pkgs/dsh { };
      description = "The pinned harness; supplies the undici proxy shim the unit preloads (NODE_OPTIONS).";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions =
      let
        others = lib.filterAttrs (name: _: name != "seat") config.services.egress-broker.instances;
        taken = lib.foldl' (acc: i: acc ++ [ i.hostAddress i.namespaceAddress ]) [ ] (
          lib.attrValues others
        );
      in
      [
        {
          assertion = !(lib.hasPrefix "/nix/store" cfg.keyFile);
          message = "services.seat.keyFile must be a path outside /nix/store, got '${cfg.keyFile}'";
        }
        {
          assertion = !lib.any (a: builtins.elem a taken) [
            cfg.hostAddress
            cfg.namespaceAddress
          ];
          message = "services.seat: address block ${cfg.hostAddress}/${cfg.namespaceAddress} collides with another egress-broker instance (10.100.2.x media, 10.100.3.x openrouter lane and 10.100.1.x cowork are taken; the seat's block is 10.100.4.x)";
        }
        {
          assertion = !lib.any (p: p == "/var/lib/secrets" || lib.hasPrefix "/var/lib/secrets/" p) cfg.extraReadWritePaths;
          message = "services.seat.extraReadWritePaths must not reach under /var/lib/secrets";
        }
        {
          assertion = (config.systemd.services."seat@".environment.OPENROUTER_API_KEY or null) == placeholder;
          message = "seat@.service must carry only the placeholder OPENROUTER_API_KEY \"${placeholder}\" -- a real key in the unit's environment is exactly what this design removes";
        }
      ];

    services.egress-broker.instances.seat = {
      inherit (cfg) hostAddress namespaceAddress listenPort;
      allow = [ cfg.host ];
      inject.${cfg.host}.valueFile = cfg.keyFile;
      # Deny paths as the lane (spec item 1): nothing consumes OpenRouter's
      # Anthropic-style /api/v1/messages, and the refusal fires before the
      # credential is injected (nixosModules/modelLane.nix:181-183).
      denyPaths.${cfg.host}.pathPrefixes = [ "/api/v1/messages" ];
      # No bodyPatch here, deliberately: the wrapper's banner is the contract
      # (zero-data-retention is an OpenRouter account setting,
      # dsh-openrouter.sh:572); the lane's chokepoint patch is a lane
      # decision (modelLane.nix:164-172).
    };

    environment.systemPackages = [ seatSubmit ];

    systemd.tmpfiles.rules = [
      "d ${cfg.stateDir} 0700 ${cfg.operatorUser} users -"
      "d ${cfg.stateDir}/jobs 0700 ${cfg.operatorUser} users -"
    ];

    systemd.services."seat@" = {
      description = "Operator seat job %i: dsh-openrouter behind the seat's egress broker";
      requires = [ "egress-broker-seat.service" ];
      after = [ "egress-broker-seat.service" ];
      environment = {
        HTTPS_PROXY = "http://${cfg.hostAddress}:${toString cfg.listenPort}";
        HTTP_PROXY = "http://${cfg.hostAddress}:${toString cfg.listenPort}";
        SSL_CERT_FILE = caBundle;
        NODE_EXTRA_CA_CERTS = caBundle;
        # dsh (Node) ignores HTTPS_PROXY on its own; the shim + this switch
        # are the lane's proven pair (modelLane.nix:226-234).
        NODE_USE_ENV_PROXY = "1";
        NODE_OPTIONS = "--require ${cfg.harnessPackage}/lib/proxy-shim.cjs";
        OPENROUTER_API_KEY = placeholder;
        # The systemd unit IS the sandbox (own netns, broker as the only
        # route, guard hooks, local-only trees inaccessible) -- the harness's
        # own tool sandbox is redundant inside it and its approval seam
        # denies every tool in headless mode (lane-run.py:360-371 precedent).
        DSH_PERMISSION_MODE = "danger-full-access";
        SEAT_STATE_DIR = cfg.stateDir;
        SEAT_WEB_PORT = toString cfg.webPort;
      };
      serviceConfig = {
        Type = "exec";
        User = cfg.operatorUser;
        NetworkNamespacePath = "/run/netns/egress-seat";
        ExecStart = "${seatRun}/bin/seat-run %i";
        ReadWritePaths = [
          "/home/${cfg.operatorUser}/factory"
          "/home/${cfg.operatorUser}/nixos-agent-env"
          "/home/${cfg.operatorUser}/flakes"
          cfg.stateDir
        ] ++ cfg.extraReadWritePaths;
        NoNewPrivileges = true;
        ProtectSystem = "strict";
        # read-only /home, punched through only by ReadWritePaths above: the
        # seat edits the operator's clones BY DESIGN (spec item 2) -- unlike
        # the lane, ProtectHome=true is wrong here.
        ProtectHome = "read-only";
        PrivateTmp = true;
        CapabilityBoundingSet = "";
        RestrictAddressFamilies = "AF_INET AF_INET6 AF_UNIX";
        UMask = "0077";
        InaccessiblePaths = [
          "-/run/baskets"
          "-/var/lib/baskets"
          "-/var/lib/helm"
          "-/var/lib/egress-broker"
          "-/var/lib/lanes"
          "-/var/lib/secrets"
        ];
        TimeoutStopSec = "30s";
      };
    };

    security.polkit.enable = lib.mkDefault true;
    # ES5 (duktape, no template literals / arrow functions), the lane's rule
    # (modelLane.nix:308-325) generalised: the operator may START and STOP
    # seat@* (the web seat is long-running; stopping it is the operator's
    # way to close it). Every other subject and unit falls through to
    # polkit's implicit deny.
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

    networking.nftables.tables.seat-web = {
      family = "inet";
      content = ''
        chain output-seat-web {
          type filter hook output priority filter - 1;
          # Host -> namespace traffic is LOCALLY ORIGINATED (an output-hook
          # packet), not forwarded: the broker's forward chain already drops
          # both directions of forwarded veb-seat traffic (egressBroker.nix:
          # 187-191), and its input chain admits only the broker port from
          # the namespace. This chain is the ONLY inbound path to the web
          # seat: established broker replies, then exactly
          # hostAddress -> namespaceAddress:webPort, then drop (a drop is
          # final across same-hook base chains; an accept is not --
          # egressBroker.nix:150-155 relies on the same semantics).
          oifname "veb-seat" ct state established,related accept
          oifname "veb-seat" ip saddr ${cfg.hostAddress} ip daddr ${cfg.namespaceAddress} tcp dport ${toString cfg.webPort} accept
          oifname "veb-seat" drop
        }
      '';
    };
  };
}
```

- [ ] **Step 3: Host wiring.** `hosts/core/seat.nix` (new):

```nix
_: {
  # The operator's seat behind its own broker (spec
  # docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md): the
  # same key file the lane injects from, an address block of its own
  # (10.100.4.x -- 10.100.2.x media and 10.100.3.x openrouter lane are
  # taken), the web UI on one admitted port. Not started by anything here:
  # jobs are started one at a time by the operator through seat-submit,
  # gated by the polkit rule the module renders.
  services.seat = {
    enable = true;
    host = "openrouter.ai";
    keyFile = "/var/lib/secrets/openrouter-key";
    hostAddress = "10.100.4.1";
    namespaceAddress = "10.100.4.2";
    listenPort = 3132;
    operatorUser = "dalhaka";
    webPort = 8790;
  };
}
```

  `hosts/core/default.nix`: add `./seat.nix` to `imports` (after `./lanes.nix`, line 12). `flake.nix`: add `seat = import ./nixosModules/seat.nix;` to the `nixosModules` attrset (line 616–626) and `self.nixosModules.seat` to `nixosConfigurations.core.modules` (beside `self.nixosModules.modelLane`, line 644).
- [ ] **Step 4: Eval fixtures + checks in `flake.nix`.** Beside `laneEvalSystem` (line 503):

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
            services.seat = {
              enable = true;
              host = "openrouter.test";
              keyFile = "/run/seat-secret";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3199;
              webPort = 8790;
              operatorUser = "dalhaka";
            };
          })
        ];
      };
      # seat-assertion-negative fixture A: a REAL key forced into the seat@
      # unit's environment must fail eval (the module's placeholder
      # assertion is the load-bearing one -- spec §Tests "negative
      # assertion").
      seatBadKeySystem = nixpkgs.lib.nixosSystem {
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
            services.seat = {
              enable = true;
              host = "openrouter.test";
              keyFile = "/run/seat-secret";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3199;
              operatorUser = "dalhaka";
            };
            systemd.services."seat@".environment.OPENROUTER_API_KEY =
              nixpkgs.lib.mkForce "sk-or-live-key";
          })
        ];
      };
      # seat-assertion-negative fixture B: a second egress-broker instance
      # squatting the seat's address block must fail eval (the collision
      # assertion; 10.100.4.x must never collide with 2.x/3.x -- spec item 1).
      seatBadAddressSystem = nixpkgs.lib.nixosSystem {
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
            services.seat = {
              enable = true;
              host = "openrouter.test";
              keyFile = "/run/seat-secret";
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3199;
              operatorUser = "dalhaka";
            };
            services.egress-broker.instances.squatter = {
              hostAddress = "10.100.4.1";
              namespaceAddress = "10.100.4.2";
              listenPort = 3198;
              allow = [ "squatter.test" ];
            };
          })
        ];
      };
```

  and in the `checks` attrset after the lane checks:

```nix
        seat-eval =
          let
            c = seatEvalSystem.config;
            unit = c.systemd.services."seat@";
            sc = unit.serviceConfig;
            i = c.services.egress-broker.instances.seat;
            hasSeatSubmit = builtins.any (p: p.name or "" == "seat-submit") c.environment.systemPackages;
            placeholder = "injected-by-broker";
            caBundle = "/var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt";
            rwPaths = [
              "/home/dalhaka/factory"
              "/home/dalhaka/nixos-agent-env"
              "/home/dalhaka/flakes"
              "/var/lib/seat"
            ];
            nftContent = c.networking.nftables.tables.seat-web.content;
          in
          nixpkgs.lib.assertMsg (i.allow == [ "openrouter.test" ]) "seat-eval: the seat instance must allow exactly its one host"
          && nixpkgs.lib.assertMsg (i.inject.openrouter.test.valueFile == "/run/seat-secret") "seat-eval: the seat instance must inject from the configured keyFile"
          && nixpkgs.lib.assertMsg (i.denyPaths.openrouter.test.pathPrefixes == [ "/api/v1/messages" ]) "seat-eval: the seat instance must deny /api/v1/messages (fail closed, before injection)"
          && nixpkgs.lib.assertMsg (c.services.egress-broker.policy.seat.audit_log == "/var/lib/egress-broker/seat/audit.jsonl") "seat-eval: the seat instance's audit log must be its own"
          && nixpkgs.lib.assertMsg (!builtins.hasAttr "bodyPatch" i) "seat-eval: the seat instance must not body-patch (ZDR is an OpenRouter account setting)"
          && nixpkgs.lib.assertMsg (sc.NetworkNamespacePath == "/run/netns/egress-seat") "seat-eval: seat@ must join the seat broker's netns"
          && nixpkgs.lib.assertMsg (sc.User == "dalhaka") "seat-eval: seat@ must run as the operator, not a DynamicUser"
          && nixpkgs.lib.assertMsg (sc.Type or "simple" == "exec") "seat-eval: seat@ must be Type=exec"
          && nixpkgs.lib.assertMsg (builtins.elem "egress-broker-seat.service" unit.requires or [ ]) "seat-eval: seat@ must Require egress-broker-seat.service"
          && nixpkgs.lib.assertMsg (unit.environment.HTTPS_PROXY or "" == "http://10.100.4.1:3199") "seat-eval: seat@ must point HTTPS_PROXY at the broker instance"
          && nixpkgs.lib.assertMsg (unit.environment.HTTP_PROXY or "" == "http://10.100.4.1:3199") "seat-eval: seat@ must point HTTP_PROXY at the broker instance"
          && nixpkgs.lib.assertMsg (unit.environment.SSL_CERT_FILE or "" == caBundle) "seat-eval: seat@ must point SSL_CERT_FILE at the public CA bundle"
          && nixpkgs.lib.assertMsg (unit.environment.NODE_EXTRA_CA_CERTS or "" == caBundle) "seat-eval: seat@ must point NODE_EXTRA_CA_CERTS at the public CA bundle"
          && nixpkgs.lib.assertMsg (unit.environment.NODE_USE_ENV_PROXY or "" == "1") "seat-eval: seat@ must set NODE_USE_ENV_PROXY=1 (dsh ignores HTTPS_PROXY without it)"
          && nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "proxy-shim.cjs" (unit.environment.NODE_OPTIONS or "")) "seat-eval: seat@ must preload the undici proxy shim"
          && nixpkgs.lib.assertMsg (unit.environment.OPENROUTER_API_KEY or "" == placeholder) "seat-eval: seat@ must carry only the placeholder OPENROUTER_API_KEY"
          && nixpkgs.lib.assertMsg (unit.environment.DSH_PERMISSION_MODE or "" == "danger-full-access") "seat-eval: the systemd unit IS the sandbox; the harness's own sandbox is off (lane-run.py precedent)"
          && nixpkgs.lib.assertMsg (unit.environment.SEAT_STATE_DIR or "" == "/var/lib/seat") "seat-eval: seat@ must export the spool root to seat-run"
          && nixpkgs.lib.assertMsg (unit.environment.SEAT_WEB_PORT or "" == "8790") "seat-eval: seat@ must export the configured web port"
          && nixpkgs.lib.assertMsg (sc.ReadWritePaths or [ ] == rwPaths) "seat-eval: seat@ ReadWritePaths must be exactly the operator trees and the spool"
          && nixpkgs.lib.assertMsg (!nixpkgs.lib.any (p: p == "/var/lib/secrets" || nixpkgs.lib.hasPrefix "/var/lib/secrets/" p) (sc.ReadWritePaths or [ ])) "seat-eval: no /var/lib/secrets in the seat unit's paths"
          && nixpkgs.lib.assertMsg (nixpkgs.lib.hasPrefix "-/var/lib/secrets" (builtins.toString (sc.InaccessiblePaths or [ ])) || nixpkgs.lib.elem "-/var/lib/secrets" (sc.InaccessiblePaths or [ ])) "seat-eval: /var/lib/secrets must be InaccessiblePaths-hidden from the seat"
          && nixpkgs.lib.assertMsg (sc.ProtectSystem == "strict") "seat-eval: seat@ must keep ProtectSystem=strict"
          && nixpkgs.lib.assertMsg (sc.ProtectHome == "read-only") "seat-eval: seat@ must keep ProtectHome=read-only (the operator's home is visible, only ReadWritePaths are writable)"
          && nixpkgs.lib.assertMsg (sc.NoNewPrivileges == true) "seat-eval: seat@ must keep NoNewPrivileges"
          && nixpkgs.lib.assertMsg (sc.UMask == "0077") "seat-eval: seat@ must keep UMask=0077 (job payloads are the operator's)"
          && nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "seat-run %i" (sc.ExecStart or "")) "seat-eval: seat@ ExecStart must be seat-run with the instance id"
          && nixpkgs.lib.assertMsg (builtins.length (builtins.filter (r: nixpkgs.lib.hasPrefix "d /var/lib/seat" r) c.systemd.tmpfiles.rules) == 2) "seat-eval: the spool and its jobs dir must be tmpfiles-declared 0700 operator"
          && nixpkgs.lib.assertMsg hasSeatSubmit "seat-eval: seat-submit must be a system package"
          && nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "subject.user == \"dalhaka\"" c.security.polkit.extraConfig) "seat-eval: polkit must gate seat@* to the operator"
          && nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "verb == \"start\" || verb == \"stop\"" c.security.polkit.extraConfig) "seat-eval: polkit must allow the operator start AND stop (the web seat is long-running)"
          && nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "ip saddr 10.100.4.1 ip daddr 10.100.4.2 tcp dport 8790 accept" nftContent) "seat-eval: the seat-web output chain must admit exactly hostAddress -> namespaceAddress:webPort"
          && nixpkgs.lib.assertMsg (nixpkgs.lib.hasInfix "oifname \"veb-seat\" drop" nftContent) "seat-eval: the seat-web output chain must end in a drop (no other inbound path)"
          && builtins.seq c.system.build.toplevel.drvPath (pkgs.runCommand "seat-eval-ok" { } "touch $out");
        seat-assertion-negative =
          let
            attemptKey = builtins.tryEval seatBadKeySystem.config.system.build.toplevel.drvPath;
            attemptAddr = builtins.tryEval seatBadAddressSystem.config.system.build.toplevel.drvPath;
            failing =
              c:
              nixpkgs.lib.concatStringsSep "\n" (
                map (a: a.message) (nixpkgs.lib.filter (a: !a.assertion) c.assertions)
              );
          in
          if attemptKey.success then
            throw "seat-assertion-negative: a REAL key in seat@'s environment DID NOT FAIL the build"
          else if !(nixpkgs.lib.hasInfix "placeholder" (failing seatBadKeySystem.config)) then
            throw "seat-assertion-negative: the real-key fixture failed but did not name the placeholder rule (got: ${failing seatBadKeySystem.config})"
          else if attemptAddr.success then
            throw "seat-assertion-negative: a colliding address block DID NOT FAIL the build"
          else if !(nixpkgs.lib.hasInfix "collides with another egress-broker instance" (failing seatBadAddressSystem.config)) then
            throw "seat-assertion-negative: the address fixture failed but did not name the collision (got: ${failing seatBadAddressSystem.config})"
          else
            pkgs.runCommand "seat-assertion-negative-ok" { } "touch $out";
```

  (`seat-eval` mirrors `lane-eval`'s chained-assertMsg style, flake.nix:1283–1450, and ends with the same `builtins.seq … toplevel.drvPath` build-completes proof; `seat-assertion-negative` mirrors `helm-control-assertion-negative-agentunit`'s two-fixture tryEval shape, flake.nix:1255–1276.)
- [ ] **Step 5: Green.** `git add` every new/modified file, then:
  - `nix build .#checks.x86_64-linux.seat-eval -L --no-link` → iterate until green (fix only what the assertions name).
  - `nix build .#checks.x86_64-linux.seat-assertion-negative -L --no-link` → green.
  - `nix build .#checks.x86_64-linux.host-core -L --no-link` (the host grew a module + a seat-submit package; the check must stay green) and `nix build .#nixosConfigurations.core.config.system.build.toplevel` to prove core still evaluates.
  - `nix develop -c githooks/pre-commit`.
- [ ] **Step 6: Mutations (for the reviewer).** (i) In the module, change `OPENROUTER_API_KEY = placeholder;` to a literal real-looking value → `seat-eval` red AND `seat-assertion-negative` red (fixture A now builds — the throw fires). (ii) Delete the collision assertion → fixture B builds → `seat-assertion-negative` red. (iii) Delete the `oifname "veb-seat" drop` line → `seat-eval` red on the drop assertion. (iv) Set `ProtectHome = true` → `seat-eval` red.
- [ ] **Step 7: Commit.**

**touches:** nixosModules/seat.nix, hosts/core/seat.nix, hosts/core/default.nix, flake.nix
**acceptance:** seat-eval, seat-assertion-negative, host-core, lint
**commit subject:** `seat: nixosModules/seat.nix — broker instance seat@, template unit, polkit, nftables, host wiring (test: seat-eval, seat-assertion-negative, host-core, lint)`

### SB4 (code, M) — the VM check `seat-vm`: the job through the broker, the web UI host-side only

**dependsOn:** SB3

**Files:**
- Create: `tests/integration/seat-vm.nix`
- Modify: `flake.nix` (one binding in the `checks` attrset, beside `lane-vm` ~line 1486)

**Interfaces:**
- Consumes: SB3's module (imported as `seatModule`), `services.seat` options, the `seat-submit` CLI on the machine's system packages, SB1's wrapper flags, SB2's job contract (`exit`/`log` files).
- Produces: the check `seat-vm` (spec §Tests names it); nothing downstream consumes it. Proves, in one VM: a submitted job reaches the fake `openrouter.ai` with the real header injected while the job holds only the placeholder; `/api/v1/messages` is refused before injection; another host is dropped by the namespace; the web UI answers on `10.100.4.2:8790` from the host side and not from another source address; the audit log carries the requests; polkit lets the operator start and stop and refuses a bystander.

- [ ] **Step 1: Red.** `nix build .#checks.x86_64-linux.seat-vm -L --no-link` → `flake does not provide attribute` (the check does not exist). Record it.
- [ ] **Step 2: Write the VM test** — `tests/integration/seat-vm.nix` in full:

```nix
{
  pkgs,
  egressBrokerModule,
  seatModule,
}:
let
  # Certificates for the fake openrouter.ai (the seat's broker allows the
  # real hostname; /etc/hosts maps it onto the VM's loopback where the fake
  # upstream listens). Same shape as tests/integration/lane-vm.nix's
  # testCerts, different CN.
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
          -keyout $out/openrouter.ai.key -out $out/openrouter.ai.csr \
          -subj "/CN=openrouter.ai" -addext "subjectAltName=DNS:openrouter.ai"
        openssl x509 -req -in $out/openrouter.ai.csr -CA $out/ca.crt -CAkey $out/ca.key \
          -CAcreateserial -days 2 -copy_extensions copy -out $out/openrouter.ai.crt
      '';
  # A chat completion the real dsh harness accepts for a one-turn headless
  # task (finish_reason included); every POST to the fake gets it.
  fakeAnswer = builtins.toJSON {
    id = "gen-1";
    model = "test/model-flash";
    choices = [
      {
        index = 0;
        message = {
          role = "assistant";
          content = "vm-seat-answer";
        };
        finish_reason = "stop";
      }
    ];
    usage = {
      prompt_tokens = 3;
      completion_tokens = 2;
      total_tokens = 5;
    };
  };
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
    ctx.load_cert_chain("${testCerts}/openrouter.ai.crt", "${testCerts}/openrouter.ai.key")
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    httpd.serve_forever()
  '';
in
pkgs.testers.runNixOSTest {
  name = "seat-behind-broker";
  nodes.machine =
    { pkgs, ... }:
    {
      imports = [
        egressBrokerModule
        seatModule
      ];
      security.pki.certificateFiles = [ "${testCerts}/ca.crt" ];
      networking.hosts."127.0.0.1" = [ "openrouter.ai" ];

      environment.etc."seat-vm-brief.txt".text = "Reply with the single word ok.";

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
        host = "openrouter.ai";
        keyFile = "/run/seat-secret";
        hostAddress = "10.100.4.1";
        namespaceAddress = "10.100.4.2";
        listenPort = 3199;
        operatorUser = "operator";
        webPort = 8790;
        # The fixture workspace sits outside the operator's home trees, so it
        # must be declared explicitly -- this also exercises the option
        # seat-eval's default-list assertion leaves uncovered.
        extraReadWritePaths = [ "/var/lib/seat-vm-workspace" ];
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
        # Stands in for the operator's one-time procedure (mirrors
        # lane-vm's lane-secret): a root-only fixture string the test greps
        # for to prove it never leaves the broker.
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
        seat-vm-fixtures = {
          description = "Seat VM fixtures: the operator's workspace";
          wantedBy = [ "multi-user.target" ];
          serviceConfig = {
            Type = "oneshot";
            RemainAfterExit = true;
          };
          script = ''
            mkdir -p /var/lib/seat-vm-workspace
            echo "seat vm fixture repo" > /var/lib/seat-vm-workspace/README.md
            chmod 0755 /var/lib/seat-vm-workspace
            chmod 0644 /var/lib/seat-vm-workspace/README.md
          '';
        };
      };
    };
  testScript = ''
    machine.wait_for_unit("fake-upstream.service")
    machine.wait_for_unit("seat-vm-fixtures.service")
    machine.wait_for_unit("egress-broker-seat.service")
    machine.wait_until_succeeds(
        "test -f /var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt"
    )

    # 1. one headless job through the unit: the real harness runs behind the
    #    broker, answers, and its FACTORY-shaped output lands in the job dir.
    job_id = machine.succeed(
        "su - operator -c 'seat-submit "
        "--workspace /var/lib/seat-vm-workspace --model test/model-flash "
        "< /etc/seat-vm-brief.txt'"
    ).strip()
    machine.wait_until_succeeds(
        f"test -f /var/lib/seat/jobs/{job_id}/exit"
    )
    machine.succeed(f"test \"$(cat /var/lib/seat/jobs/{job_id}/exit)\" = 0")
    log = machine.succeed(f"cat /var/lib/seat/jobs/{job_id}/log")

    # 2. the fake upstream saw the broker-injected credential on the chat
    #    path (this process only ever held the placeholder).
    api_log = machine.succeed("cat /var/log/seat-vm-fake-upstream.log")
    assert "/api/v1/chat/completions" in api_log, api_log
    assert "Bearer vm-seat-fake-key" in api_log, api_log

    # 3. the job's environment and spool hold only the placeholder: no
    #    rendered unit text, no job file carries the real key.
    machine.fail("systemctl cat 'seat@.service' | grep -q vm-seat-fake-key")
    machine.fail("grep -rq vm-seat-fake-key /var/lib/seat/jobs")
    env = machine.succeed(
        f"systemctl show 'seat@{job_id}.service' -p Environment --value"
    )
    assert "OPENROUTER_API_KEY=injected-by-broker" in env, env
    assert "vm-seat-fake-key" not in env, env

    # 4. /api/v1/messages is denied at the broker, fail closed, BEFORE the
    #    key is injected (lane-vm step 2c shape).
    deny_resp = machine.succeed(
        "ip netns exec egress-seat curl -s --max-time 15 "
        "-x http://10.100.4.1:3199 "
        "--cacert /var/lib/egress-broker-ca-bundle/seat/ca-bundle.crt "
        "-X POST -H 'content-type: application/json' "
        "--data '{\"model\":\"m\"}' "
        "https://openrouter.ai/api/v1/messages"
    )
    assert "egress-broker: denied" in deny_resp, deny_resp
    machine.succeed(
        "jq -es '[.[] | select(.path==\"/api/v1/messages\" and "
        ".verdict==\"deny\" and .reason==\"path-not-permitted\")] "
        "| length == 1' /var/lib/egress-broker/seat/audit.jsonl"
    )
    api_log2 = machine.succeed("cat /var/log/seat-vm-fake-upstream.log")
    assert "/api/v1/messages" not in api_log2, api_log2

    # 5. any other host is dropped by the namespace: the netns's only route
    #    is the broker veth, and the host's forward chain drops veb-seat
    #    traffic both ways (egressBroker.nix's forward chain).
    machine.fail(
        "ip netns exec egress-seat curl -s --max-time 5 -o /dev/null http://192.0.2.1/"
    )

    # 6. the web seat: UI on the namespace address, admitted from the host
    #    side only (the seat-web output chain's saddr rule).
    web_id = machine.succeed(
        "su - operator -c 'seat-submit "
        "--workspace /var/lib/seat-vm-workspace --model test/model-flash "
        "--mode web < /dev/null'"
    ).strip()
    machine.wait_until_succeeds(
        "curl -s --max-time 5 -o /dev/null http://10.100.4.2:8790/"
    )
    web_log = machine.succeed(f"cat /var/lib/seat/jobs/{web_id}/log")
    assert "http://10.100.4.2:8790" in web_log, web_log
    # From a source address other than the veth's own (the VM's primary
    # NIC), the saddr-scoped rule drops the connection.
    primary = machine.succeed(
        "ip -o -4 addr show scope global | awk '{print $4; exit}' | cut -d/ -f1"
    ).strip()
    machine.fail(
        f"curl -s --max-time 5 -o /dev/null --interface {primary} http://10.100.4.2:8790/"
    )
    # And the UI is not bound anywhere else.
    machine.fail("curl -s --max-time 5 -o /dev/null http://127.0.0.1:8790/")

    # 7. the audit log carries the seat's requests (injected chat call;
    #    denied messages path already proven in step 4).
    machine.succeed(
        "jq -es '[.[] | select(.host==\"openrouter.ai\" and "
        ".verdict==\"allow\")] | length >= 1' /var/lib/egress-broker/seat/audit.jsonl"
    )

    # 8. polkit: the operator may start AND stop; a bystander may do
    #    neither (lane-vm step 6 shape, plus stop).
    machine.fail(
        f"su - bystander -c 'systemctl start seat@{job_id}.service'"
    )
    machine.succeed(
        f"su - operator -c 'systemctl start seat@{job_id}.service'"
    )
    machine.succeed(
        f"su - operator -c 'systemctl stop seat@{web_id}.service'"
    )
    machine.fail(
        f"su - bystander -c 'systemctl stop seat@{web_id}.service'"
    )
  '';
}
```

  (The audit `jq` field names are the broker addon's wire shape, verified: `pkgs/broker/policy.py` writes `"host"` (line 101), `"path"` (104), `"verdict" (107 — "allow" with reason "ok" at line 383, "deny" with "path-not-permitted") and "reason" (108) — `grep -n '"verdict"\|"reason"\|"host"\|"path"' pkgs/broker/policy.py` and `grep -n '"allow"' pkgs/broker/policy.py`.)

  Wire it beside `lane-vm`:

```nix
        seat-vm = import ./tests/integration/seat-vm.nix {
          inherit pkgs;
          egressBrokerModule = self.nixosModules.egressBroker;
          seatModule = self.nixosModules.seat;
        };
```

- [ ] **Step 3: Red→green on the real run.** `git add tests/integration/seat-vm.nix flake.nix`, then `nix build .#checks.x86_64-linux.seat-vm -L --no-link`. Expect the first run to surface one or two integration facts (audit field names, the fake answer's fitness for the harness, timing of the dsh boot) — fix exactly what the failure names, re-run. The check is green when the whole testScript passes. This is the spec's gate: "the VM test is the gate".
- [ ] **Step 4: Mutations (for the reviewer).** (i) In `nixosModules/seat.nix`, drop `inject.${cfg.host}.valueFile` → step 2 red (no `Bearer vm-seat-fake-key`). (ii) Drop `denyPaths` → step 4 red (no `path-not-permitted` row; the fake upstream would see `/api/v1/messages`). (iii) Drop the nft `ip saddr` from the accept line → step 6's `--interface` probe turns green (the assertion `machine.fail` fails). (iv) In `seat-run.py`, pass `--host 127.0.0.1` instead of `--bind-namespace` → step 6's wait on `10.100.4.2:8790` times out.
- [ ] **Step 5: Full gate.** `nix develop -c githooks/pre-commit`; re-run `nix build .#checks.x86_64-linux.seat-eval -L --no-link` (module untouched since SB3 — still green).
- [ ] **Step 6: Commit.**

**touches:** tests/integration/seat-vm.nix, flake.nix
**acceptance:** seat-vm, seat-eval, lint
**commit subject:** `seat: seat-vm — the seat job through the broker in a VM, web UI host-side only (test: seat-vm, lint)`

### SB5 (code, S) — `factory-task` launches the seat through `seat-submit`, result shape unchanged

**dependsOn:** SB2

**Files:**
- Modify: `tools/factory/seat/factory-task` (the launch block, lines 131–141; the poll/copy block replaces the direct invocation), `tools/factory/seat/README.md`
- Test: `tests/unit/80-seat-driver.bats`

**Interfaces:**
- Consumes: SB2's `seat-submit` CLI exactly (`--workspace`, `--model`, `--effort`, `--dsh-home`, brief on stdin; prints job id) and the job contract (`$SEAT_STATE_DIR/jobs/<id>/log`, `…/exit`).
- Produces: the same `.result` file shape as today (`factory-task:211-234` untouched — FACTORY-RESULT/CHECKS/COMMITS/NOTES extraction at 152–170 untouched); env `FACTORY_SEAT_STATE_DIR` (default `/var/lib/seat`) as the poll root, mirroring `LANE_STATE_DIR`'s test seam (`lane-submit.py:66`). Falls back to today's direct `dsh-openrouter` launch whenever `seat-submit` is not on PATH (pre-switch hosts; spec item 7: "it tolerates both until the file is gone").

- [ ] **Step 1: Write the failing test.** Append to `tests/unit/80-seat-driver.bats`, beside the existing `factory-task resolves model and effort…` test (line 429 — copy its seat-copy/shebang/routing-fixture/plan helpers verbatim, they are the established harness for driving factory-task in the sandbox):

```bash
@test "factory-task launches through seat-submit when it is on PATH and reads the job dir" {
  seat_copy="$BATS_TEST_TMPDIR/seat"; cp -r "$SEAT" "$seat_copy"; chmod -R u+w "$seat_copy"
  sed -i "1s@.*@#!$REAL_BASH@" "$seat_copy/factory-brief"
  mkdir -p "$BATS_TEST_TMPDIR/ws"
  printf '#!%s\nprintf "%%s\\n" %q\n' "$REAL_BASH" "$BATS_TEST_TMPDIR/ws" >"$seat_copy/factory-ws"; chmod +x "$seat_copy/factory-ws"
  fx="$BATS_TEST_TMPDIR/toolbox"; mkdir -p "$fx/docs/ledger"
  cat >"$fx/docs/ledger/routing.toml" <<'EOF'
[[route]]
role = "implement"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"
EOF
  plan="$BATS_TEST_TMPDIR/plan.md"
  cat >"$plan" <<'EOF'
### K1 (docs, XS) — t

body one.
EOF
  repo="$BATS_TEST_TMPDIR/repo"; mkdir -p "$repo"
  # A stub seat-submit: records its argv, prints a job id, and lays down the
  # job dir (log + exit) factory-task must poll and read. No dsh-openrouter
  # stub is placed on PATH: if factory-task still tries the direct launch,
  # it fails loudly (and the REC assertion below stays empty -> red).
  seat_state="$BATS_TEST_TMPDIR/seatstate"
  rec="$BATS_TEST_TMPDIR/submit.calls"
  bin="$BATS_TEST_TMPDIR/bin"; mkdir -p "$bin"
  cat >"$bin/seat-submit" <<FAKE
#!$REAL_BASH
printf '%s\\n' "\$*" >> "$rec"
jobid=stubjob1
mkdir -p "$seat_state/jobs/\$jobid"
printf 'seat-submit: launched\\n' > "$seat_state/jobs/\$jobid/log"
printf 'FACTORY-RESULT status=done\\n' >> "$seat_state/jobs/\$jobid/log"
printf 'FACTORY-CHECKS unit=pass\\n' >> "$seat_state/jobs/\$jobid/log"
printf 'FACTORY-COMMITS 1\\n' >> "$seat_state/jobs/\$jobid/log"
printf 'FACTORY-NOTES via seat-submit\\n' >> "$seat_state/jobs/\$jobid/log"
printf '0\\n' > "$seat_state/jobs/\$jobid/exit"
printf '%s\\n' "\$jobid"
FAKE
  chmod +x "$bin/seat-submit"
  root="$BATS_TEST_TMPDIR/factory"; mkdir -p "$root"
  share="$BATS_TEST_TMPDIR/share"; mkdir -p "$share"
  FACTORY_ROOT="$root" FACTORY_TOOLBOX_REPO="$fx" FACTORY_PLAN="$plan" \
    FACTORY_SHARED_DSH_HOME_SRC="$share" FACTORY_SEAT_STATE_DIR="$seat_state" \
    PATH="$bin:$PATH" OPENROUTER_REASONING_EFFORT= OPENROUTER_MODEL= \
    run "$REAL_BASH" "$seat_copy/factory-task" s1 "$repo" K1
  [ "$status" -eq 0 ]
  # seat-submit was called with the workspace, the routed model, the
  # effort and the per-task dsh-home; the brief went in on stdin.
  run cat "$rec"
  [[ "$output" == *"--workspace $BATS_TEST_TMPDIR/ws"* ]]
  [[ "$output" == *"--model deepseek/deepseek-v4-pro-0813"* ]]
  [[ "$output" == *"--effort medium"* ]]
  [[ "$output" == *"--dsh-home $root/runs/s1/K1.dsh-home"* ]]
  # The .result keeps its shape: the FACTORY block parsed out of the JOB
  # DIR's log, not out of a direct-launch tee.
  run cat "$root/runs/s1/K1.result"
  [[ "$output" == *"FACTORY-RESULT status=done"* ]]
  [[ "$output" == *"FACTORY-CHECKS unit=pass"* ]]
  [[ "$output" == *"FACTORY-NOTES via seat-submit"* ]]
  [[ "$output" == *"workspace: $BATS_TEST_TMPDIR/ws"* ]]
  [[ "$output" == *"exit_code: 0"* ]]
  # The job's log was copied to the per-task log the operator tails.
  run cat "$root/runs/s1/K1.log"
  [[ "$output" == *"FACTORY-RESULT status=done"* ]]
}
```

- [ ] **Step 2: Red.** `nix develop -c bats tests/unit/80-seat-driver.bats` → the new test fails: factory-task execs `dsh-openrouter` directly (which does not exist on this PATH), the `REC` file never appears, the `.result` says `status=failed`. The existing `factory-task resolves model and effort…` test stays green (no `seat-submit` on its PATH → it must keep exercising the fallback).
- [ ] **Step 3: Implement.** In `tools/factory/seat/factory-task`, replace the launch block (today's lines 131–141) with:

```bash
factory_log "launching the seat for $ws (timeout ${timeout_s}s, log $log)"
start_ts=$(date +%s)
# The seat behind its broker (plan 2026-09-05-seat-behind-broker-glm, SB5):
# when the switch has landed, seat-submit is on PATH and the job runs as a
# seat@ unit behind the egress broker -- no key in this process's tree at
# all. Before the switch (or on a rolled-back host) the direct launch keeps
# working; the two paths write the same .result.
if command -v seat-submit >/dev/null 2>&1; then
  seat_state=${FACTORY_SEAT_STATE_DIR:-/var/lib/seat}
  effort_args=()
  [ -n "$effort" ] && effort_args=(--effort "$effort")
  job_id=$(printf '%s' "$brief" | seat-submit \
    --workspace "$ws" --model "$model" "${effort_args[@]}" --dsh-home "$dsh_home")
  job_dir=$seat_state/jobs/$job_id
  while [ ! -f "$job_dir/exit" ] && [ $(( $(date +%s) - start_ts )) -lt "$timeout_s" ]; do
    sleep 5
  done
  if [ -f "$job_dir/exit" ]; then
    exit_code=$(cat "$job_dir/exit")
  else
    factory_log "seat job $job_id exceeded FACTORY_TIMEOUT; stopping the unit"
    systemctl stop "seat@$job_id.service"
    exit_code=124
  fi
  # The unit already teed the job's output to the journal; copy it to the
  # per-task log so tail -f and the .result extractor read the same text.
  cp -f -- "$job_dir/log" "$log"
  factory_log "seat exited $exit_code after $(( $(date +%s) - start_ts ))s"
else
  factory_log "seat-submit not on PATH; direct launch (pre-switch host)"
  set +e
  (
    cd -- "$ws" &&
      DSH_HOME=$dsh_home \
        OPENROUTER_REASONING_EFFORT=$effort \
        timeout -- "$timeout_s" dsh-openrouter --model "$model" --headless "$brief"
  ) 2>&1 | tee -a -- "$log"
  exit_code=${PIPESTATUS[0]}
  set -e
fi
```

  Everything after (`wall_s`, `extract_field`, the `.result` block, 142–234) is untouched. `systemctl stop` here is the operator's own driver stopping its own job through the polkit rule SB3 renders — never a factory-agent action.
- [ ] **Step 4: Green + neighbours.** `nix develop -c bats tests/unit/80-seat-driver.bats` → all green (old tests included). `nix develop -c githooks/pre-commit` (shellcheck sweeps factory-task).
- [ ] **Step 5: README.** In `tools/factory/seat/README.md`, replace the "no broker, no netns, no lane" seat description (line 21 area) with two sentences: post-switch, `factory-task` submits a `seat@` job through `seat-submit` and reads `/var/lib/seat/jobs/<id>/` (`log`, `exit`); the live view is `journalctl -u seat@<id> -f` (the per-task log is written when the job exits). Pre-switch the direct launch still runs.
- [ ] **Step 6: Mutations (for the reviewer).** (i) Revert the `if` to always take the direct branch → the new test red (`seat-submit` never called, status 2 from the missing `dsh-openrouter`). (ii) Read `exit_code` from `$?` instead of the exit file → the `exit_code: 0` assertion red (0 vs the stub's). (iii) Skip the `cp` of the job log → the `K1.log` assertion red.
- [ ] **Step 7: Commit.**

**touches:** tools/factory/seat/factory-task, tools/factory/seat/README.md, tests/unit/80-seat-driver.bats
**acceptance:** unit, lint
**commit subject:** `factory: factory-task launches the seat through seat-submit, result shape unchanged (test: unit, lint)`

### SB6 (code, S) — the backup takes the seat spool, excludes its transcripts

**dependsOn:** SB3

**Files:**
- Modify: `nixosModules/protonBackup.nix` (the `exclude` default, lines 35–40), `hosts/core/proton-backup.nix` (`paths`, lines 29–42), `docs/runbooks/backup.md` (the "What is backed up" list, lines 17–30)

**Interfaces:**
- Consumes: SB3's spool root `/var/lib/seat` (the only new persistent tree on the host).
- Produces: `/var/lib/seat` in `services.proton-backup.paths` (job briefs and results are the operator's data, spec item 3) and the exclusion `/var/lib/seat/jobs/*/dsh-home/sessions` in the module's default `exclude` (the zstd session transcripts are machine bulk, not operator data). No other consumer.

- [ ] **Step 1: Red.** Add `"/var/lib/seat"` to `paths` in `hosts/core/proton-backup.nix` (after `/var/lib/evidence`, line 41) and run `nix build .#checks.x86_64-linux.core-backup-wiring -L --no-link` → the check throws `docs/runbooks/backup.md does not name these backup paths: /var/lib/seat` (fact 20 — the `undocumented` filter). Record the exact message.
- [ ] **Step 2: Green.** (a) In `docs/runbooks/backup.md`'s "What is backed up" list add one bullet after the evidence-store bullet (line 29): `- the seat spool \`/var/lib/seat\` — job briefs and results; the session transcripts under \`jobs/*/dsh-home/sessions\` are excluded as machine bulk;`. (b) In `nixosModules/protonBackup.nix` append `"/var/lib/seat/jobs/*/dsh-home/sessions"` to the `exclude` default list (after `"/home/*/.cache"`, line 40) with the comment `# the seat's session transcripts (plan 2026-09-05-seat-behind-broker-glm, SB6; spec item 3): job briefs and results are the operator's data, the zstd transcripts are machine bulk`. (c) Re-run `nix build .#checks.x86_64-linux.core-backup-wiring -L --no-link` → green.
- [ ] **Step 3: Verify the module default didn't drift.** `nix build .#checks.x86_64-linux.proton-backup-eval -L --no-link` → green (the exclude list grew; nothing asserts its old length). `nix develop -c githooks/pre-commit`.
- [ ] **Step 4: Mutations (for the reviewer).** (i) Remove the backup.md bullet → `core-backup-wiring` red (step 1's message returns). (ii) Typo the exclusion pattern (`dsh-homes`) → no check goes red today (the exclusion is restic-side, untestable at eval) — name this gap here, as the spec's own wording does: the exclusion's proof is the operator's first backup (`restic ls latest | grep sessions` comes back empty).
- [ ] **Step 5: Commit.**

**touches:** nixosModules/protonBackup.nix, hosts/core/proton-backup.nix, docs/runbooks/backup.md
**acceptance:** core-backup-wiring, proton-backup-eval, lint
**commit subject:** `backup: the seat spool is backed up, its transcripts excluded (test: core-backup-wiring, proton-backup-eval, lint)`

### SB7 (docs, S) — the runbook for the seat behind its broker; MAP regenerated

**dependsOn:** SB1, SB2, SB3, SB4, SB5, SB6

**Files:**
- Modify: `docs/runbooks/lanes.md` (the seat sections, lines ~235–300), `docs/MAP.md` (generated), `hosts/core/agent-prereqs.nix` (the stale comment, line 16–18)

**Interfaces:**
- Consumes: every CLI and check SB1–SB6 produced; changes no code.
- Produces: the operator's one-command-each-way runbook (spec §Risks: "The runbook gives one command each way") and the caller list for the key file's deletion.

- [ ] **Step 1: Rewrite the seat sections in `docs/runbooks/lanes.md`.** Replace the block from "straight to OpenRouter. It is **not a lane**…" (line 235) through the "One-time: the key file" block (lines 282–290) with:

```markdown
**The seat behind its broker (2026-09-05).** The seat is a lane with the
operator's own user instead of a DynamicUser: `services.seat`
(nixosModules/seat.nix) declares its own egress-broker instance — allowlist
`openrouter.ai` only, the key injected from the root-only
`/var/lib/secrets/openrouter-key`, `/api/v1/messages` refused before
injection — and `seat@<job>` runs `dsh-openrouter --broker` inside
`/run/netns/egress-seat` as you. No seat process ever holds the key.

One job, one command (headless — the brief on stdin):

    seat-submit --workspace ~/nixos-agent-env --model deepseek/deepseek-v4-pro-0813 <<< 'brief text'

The job id prints; the run lands in `/var/lib/seat/jobs/<id>/log`, the exit
code in `…/exit`, the live view in `journalctl -u seat@<id> -f`.

The web seat (one at a time — nftables admits exactly the configured port):

    seat-submit --workspace ~/nixos-agent-env --model deepseek/deepseek-v4-pro-0813 --mode web

then open the URL the journal prints (`http://10.100.4.2:8790`) and close
the seat with `systemctl stop seat@<id>.service` (polkit allows you start
and stop, nobody else either).

**Migration (one command).** After the switch and one green headless job
and one green web job (audit rows in
`/var/lib/egress-broker/seat/audit.jsonl` show the injected requests):

    rm ~/.config/openrouter/key

From here a direct `dsh-openrouter` (no `--broker`) dies with its existing
"no key" message; `factory-task` no longer needs the key — it submits
`seat@` jobs. Everything that used to read the key file: the wrapper's own
key block (now deprecated, `--broker` replaces it), the hook guard's
key-spelling rule (moot, stays), and this runbook. Rollback is
`sudo nixos-rebuild switch --rollback` plus re-pasting the key from Proton
Pass if the old launch path is wanted again.
```

  Keep the "Reading the denial audit" section (unchanged — spec item 6: the guard keeps working inside the unit) and the existing transport-test bullet list; update only the key-file bullet (line 244) to say the key file is gone post-migration and `--broker` never reads it.
- [ ] **Step 2: Fix the stale comment** in `hosts/core/agent-prereqs.nix` (lines 16–18): `# dsh-openrouter: the operator's seat; post-2026-09-05 it runs behind the seat broker under seat@ units — the direct command's key file is gone (docs/runbooks/lanes.md).` (the package itself stays a system package — the fallback path and `--denials` still use it).
- [ ] **Step 3: Regenerate the map.** `nix develop -c python3 pkgs/evidence/repomap.py --root . write` → `docs/MAP.md` gains `nixosModules/seat.nix`, `pkgs/seat`, `tests/seat`, `tests/integration/seat-vm.nix`, `hosts/core/seat.nix` and the four new check names (`seat-eval`, `seat-assertion-negative`, `seat-unit`, `seat-vm`). Diff it: only generated content moves.
- [ ] **Step 4: Gate.** `nix develop -c githooks/pre-commit` → green (the runbook is prose; MAP is generated). Re-run `nix build .#checks.x86_64-linux.lint -L --no-link`.
- [ ] **Step 5: Commit.**

**touches:** docs/runbooks/lanes.md, docs/MAP.md, hosts/core/agent-prereqs.nix
**acceptance:** lint
**commit subject:** `docs: runbook for the seat behind its broker; the key file's callers listed; MAP regenerated (test: lint)`
