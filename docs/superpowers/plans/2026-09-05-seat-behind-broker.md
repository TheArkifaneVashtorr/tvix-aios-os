# The seat behind a broker — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox syntax. The seat driver reads the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance`, `commit subject`.

**Goal:** the seat (interactive and headless) runs as the operator inside a network namespace whose only route is its own egress-broker instance; the broker injects the OpenRouter key from the root-only `/var/lib/secrets/openrouter-key`; no seat or agent process ever holds a key; the plaintext file in the operator's home is deleted after the first jobs run.

**Spec:** `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md` (approved by the operator 2026-09-05 evening). Reuse: `nixosModules/egressBroker.nix` (instances, netns `/run/netns/egress-<name>`, `--mode regular` proxy at `hostAddress:listenPort`, `inject.<host>.valueFile`, `allow`, `denyPaths`, public CA bundle `/var/lib/egress-broker-ca-bundle/<name>/ca-bundle.crt`), `nixosModules/modelLane.nix` (a template unit joining the netns with `NetworkNamespacePath`, `NODE_EXTRA_CA_CERTS`, placeholder credential, polkit rule for the operator, tmpfiles for the spool — read it in full before SB1), `pkgs/lane/lane-submit.py` (job dir + `systemctl start` + wait), `tests/integration/lane-vm.nix` (fake `openrouter.test` with a generated CA; the fake logs the `Authorization` header verbatim).

**Facts (2026-09-05, read from the tree):** the openrouter lane uses `hostAddress 10.100.3.1`, `namespaceAddress 10.100.3.2`, `listenPort 3131`; media reserves 10.100.2.x; the seat takes **10.100.4.1 / 10.100.4.2 / 3141**. The wrapper today: `OPENROUTER_API_KEY` env or the 0600 key file (`pkgs/dsh-openrouter/dsh-openrouter.sh` lines ~218–242), UI bound to 127.0.0.1 (`--host` rejected, line ~145), dsh started with `exec node … --profile web --patch "$overlay" --host 127.0.0.1` (~580) or `--headless`. `factory-task` runs `dsh-openrouter --model "$model" --headless "$brief"` directly in the workspace (lines ~97–115). `hook-guard.py` rules keep applying inside a unit (same wrapper, same hooks.json).

## Global Constraints

- Build-only; never `sudo`, `nixos-rebuild`, `systemctl start/stop/restart` on the host; the operator switches and runs the acceptance jobs. Checks via `nix build .#checks.x86_64-linux.<name> -L --no-link`; lint gate `nix develop -c githooks/pre-commit` (it may regenerate the board block once: `git add docs/OPERATIONS.md` and commit again); commits via `nix develop -c git commit -F <msgfile>` with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer.
- TDD, red first; a VM test is the gate for anything touching the broker or the firewall (brief §3). Never widen an allowlist beyond `openrouter.ai`; never put a key in a Nix expression or a unit environment; `keyFile` must not be a store path (assert, as modelLane does).
- `docs/superpowers/plans/2026-09-05-seat-behind-broker.md` is this file; task text is the section, nothing else.

## Waves

| wave | groups | dependsOn | starts |
|---|---|---|---|
| 1 | `"SB3"` | — | now |
| 1' | `"SB2"` | RT5 landed (both edit the wrapper and 70-dsh-openrouter.bats) | after RT5 integrates |
| 1'' | `"SB1"` | OG1b landed (both edit flake.nix) | after OG1b integrates |
| 2 | `"SB4"` | SB1, SB2, SB3 | after wave 1 |
| 3 | `"SB5"` | SB4 | after SB4 |

Operator after wave 3 lands: switch; `systemctl start seat@web-1` (polkit allows it); open the URL the journal prints; run one headless job through `factory-task` (it uses `seat-submit` when present); confirm `/var/lib/egress-broker/seat/audit.jsonl` shows injected requests; then `rm ~/.config/openrouter/key`. Rollback: the previous generation; the key file stays until the operator deletes it.

## Tasks

### SB3 (code, S) — `seat-submit` writes a job and starts the unit; `factory-task` uses it when present

**dependsOn:** none

**Files:**
- Create: `pkgs/seat/seat-submit.py`, `pkgs/seat/default.nix` (a `writeShellApplication`/python wrapper like `pkgs/lane/lane-run.nix` — read it), `tests/seat/test_seat_submit.py`
- Modify: `tools/factory/seat/factory-task` (the launch block: if `command -v seat-submit` succeeds AND `FACTORY_SEAT_UNIT` is not `0`, submit a job instead of running `dsh-openrouter` directly; otherwise today's path), `tests/unit/80-seat-driver.bats` (append), `tools/factory/seat/README.md`

**Interfaces:**
- `seat-submit [--jobs-dir DIR] [--no-start] {headless|web} --workspace PATH --dsh-home PATH --model ID --effort LEVEL [--brief FILE] [--port N]` → creates `/var/lib/seat/jobs/<id>/` (0700, owner = invoking user; `<id>` = `YYYYmmdd-HHMMSS-<6 hex>`) containing `job.json` (`{"mode","workspace","dsh_home","model","effort","brief":"brief.txt"|null,"port":N|null,"submitted":iso}`) and the brief copied to `brief.txt`; prints the job id; unless `--no-start`, runs `systemctl start seat@<id>` (`check=False`, as `lane-submit.py` does) and, for `headless`, waits (poll every 2 s, `--timeout` default 10800 s) until `result.txt` exists in the job dir, then copies `stdout.txt` to its own stdout and exits with the code in `exit_code.txt`. The unit (SB1) writes `stdout.txt`, `stderr.txt`, `exit_code.txt`, `result.txt` (the `FACTORY-RESULT` block or `status=failed`). Refuses a `--workspace` that is not a directory or a `--brief` that is unreadable (exit 2). `--jobs-dir` default `/var/lib/seat/jobs` (tests use a tmp dir and `--no-start`).
- `factory-task`: when the submit path is taken, `FACTORY-RESULT` extraction and the `.result` file are UNCHANGED (it reads the job's `stdout.txt` as if it were the seat's stdout), plus one line `seat: unit seat@<id>`; the `DSH_HOME` isolation (P0) and the routing (RT1) apply exactly as before — the model/effort chosen by `factory_route` are passed to `seat-submit`.

- [ ] **Step 1: Failing tests** — pytest: a submit with `--no-start` creates the dir with the right files and modes, prints the id, `job.json` shape exact; a missing workspace → exit 2; `--brief` unreadable → exit 2; the id format. bats (80-seat-driver.bats): with a fake `seat-submit` on PATH that records its arguments and writes `stdout.txt` containing a `FACTORY-RESULT status=done` block, `factory-task` (fake `dsh-openrouter` NOT called — assert) produces the same `.result` shape as today plus the `seat:` line; with `FACTORY_SEAT_UNIT=0` the old path runs (fake `dsh-openrouter` called, `seat-submit` not). The `model`/`effort` handed to the fake equal the routed values.
- [ ] **Step 2: Red.** **Step 3: Implement** (python stdlib; the wrapper package mirrors `pkgs/lane/lane-run.nix`). **Step 4: Green** — ruff; shellcheck; `nix develop -c pytest tests/seat -q`; `nix develop -c bats tests/unit/80-seat-driver.bats`; add a check `seat-unit` in flake.nix ONLY if no other task of this plan is editing flake.nix at dispatch time — it is (OG1b, SB1): so DO NOT touch flake.nix; the pytest runs in the devShell and the bats under `unit`; SB1 wires `seat-unit` into the flake. **Step 5: Commit.**

**touches:** pkgs/seat/seat-submit.py, pkgs/seat/default.nix, tests/seat/test_seat_submit.py, tools/factory/seat/factory-task, tests/unit/80-seat-driver.bats, tools/factory/seat/README.md
**acceptance:** unit, lint
**commit subject:** `seat: seat-submit writes a job directory and starts seat@<id>; factory-task submits through it when the unit exists (test: unit, lint)`

### SB2 (code, S) — the wrapper's `--broker` mode: no key, proxy and CA from the environment, UI on the namespace address

**dependsOn:** none (dispatch after RT5 integrates — same files)

**Files:** `pkgs/dsh-openrouter/dsh-openrouter.sh`, `tests/unit/70-dsh-openrouter.bats` (append), `pkgs/dsh-openrouter/hook-guard.py` (only if the placeholder key spelling needs exempting — it should not)

**Interfaces:**
- `--broker`: (1) the key block is skipped entirely — the key file is never stat'ed or read (a bats test gives it mode 000 and asserts no failure and no read); `OPENROUTER_API_KEY` is set to `injected-by-broker` if unset; (2) requires `HTTPS_PROXY` (or `https_proxy`) to be set to `http://<host>:<port>` and `NODE_EXTRA_CA_CERTS` to an existing file, else `die 5`; (3) refuses to run unless the default route's gateway is a link-local veth peer — implement as: `ip -4 route show default` must print exactly one route whose `via` equals the proxy host (the broker's `hostAddress`), else `die 5 "--broker outside a broker namespace"` (tests stub `ip` on PATH); (4) `--bind-namespace ADDR` (accepted only with `--broker`) replaces `--host 127.0.0.1` with `--host ADDR` in the web exec line; without `--broker` it is rejected like `--host`.
- Without `--broker`: behaviour unchanged, plus one stderr line when the key file path is used: `dsh-openrouter: the key file is deprecated; seat jobs run behind the broker (docs/runbooks/seat.md)`.
- `--dump-config` shows the resulting route overlay with `apiKeyEnv: OPENROUTER_API_KEY` unchanged (the placeholder is what reaches the broker, which replaces the header).

- [ ] **Step 1: Failing tests** (fake `ip` on PATH printing a chosen default route; fake upstream as in the file): `--broker` with a mode-000 key file → exit 0 through the fake, request carries `Authorization: Bearer injected-by-broker` (the broker would replace it — here we assert the placeholder, proving no real key was read); `--broker` without `HTTPS_PROXY` → exit 5; with a default route via another gateway → exit 5; `--bind-namespace 10.100.4.2 --broker -- --no-open --port 43210 --dump-config` shows `--host 10.100.4.2` (or the dump's equivalent); `--bind-namespace` without `--broker` → exit 2; the deprecation line on the old path.
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/70-dsh-openrouter.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `host-core`; lint gate. **Step 5: Commit.**

**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: --broker runs the seat without a key behind an egress broker (proxy + CA from the unit, placeholder credential, namespace bind for the UI); the key-file path is deprecated (test: unit, host-core, lint)`

### SB1 (code, M) — `nixosModules/seatLane.nix`: the broker instance, the netns, `seat@<job>` as the operator, polkit, the spool

**dependsOn:** none (dispatch after OG1b integrates — flake.nix)

**Files:**
- Create: `nixosModules/seatLane.nix`, `hosts/core/seat.nix`, `pkgs/seat/seat-run.py` (the unit's entry: reads `/var/lib/seat/jobs/%i/job.json`, exports `DSH_HOME`, cds to the workspace, runs `dsh-openrouter --broker --model M --headless "$(cat brief.txt)"` or `--broker --bind-namespace <namespaceAddress> -- --no-open --port N`, tees stdout/stderr to the job dir, writes `exit_code.txt` and `result.txt`, prints the web URL to the journal and `url.txt`)
- Modify: `flake.nix` (`nixosModules.seatLane`; `packages.seat-submit`/`seat-run`; checks `seat-eval`, `seat-assertion-negative`, `seat-unit` (pytest tests/seat)), `hosts/core/default.nix` (import `./seat.nix`), `nixosModules/egressBroker.nix` ONLY if an option is missing (say so)

**Interfaces (module `services.seat-lane`):** options `enable`, `host` (default `openrouter.ai`), `keyFile` (assert not a store path), `hostAddress`, `namespaceAddress`, `listenPort`, `operatorUser`, `webPortRange` (default `43200-43299`), `harnessPackage` (dsh-openrouter). Renders: `services.egress-broker.instances.seat = { allow = [host]; inject.${host}.valueFile = keyFile; denyPaths = the lane's list; bodyPatch.${host} = the lane's ZDR + training-opt-out patch (data policy at the chokepoint, decision 2026-09-03 — copy modelLane.nix's block verbatim); hostAddress; namespaceAddress; listenPort; }`; tmpfiles `/var/lib/seat 0750 <operator> users`, `/var/lib/seat/jobs 0700 <operator>`; `systemd.services."seat@"` with `User = operatorUser`, `NetworkNamespacePath = /run/netns/egress-seat`, `Requires/After = egress-netns-seat.service egress-broker-seat.service`, `Environment = HTTPS_PROXY=http://<hostAddress>:<listenPort> HTTP_PROXY=… NO_PROXY=127.0.0.1,<namespaceAddress> NODE_EXTRA_CA_CERTS=<public bundle> SSL_CERT_FILE=<public bundle> OPENROUTER_API_KEY=injected-by-broker FACTORY_ROUTING_TABLE=/home/<operator>/nixos-agent-env/docs/ledger/routing.toml`, `ExecStart = seat-run %i`, `WorkingDirectory` unset (seat-run cds), `ProtectSystem = strict`, `ReadWritePaths = [ "/var/lib/seat" "/home/<operator>/factory" "/home/<operator>/nixos-agent-env" "/home/<operator>/flakes" "/home/<operator>/.local/share/dsh-openrouter" ]`, `InaccessiblePaths = [ "/var/lib/secrets" ]`, `NoNewPrivileges = true`, `Type = simple` (web) — one template serves both modes (`seat-run` reads the mode). nftables on `veb-seat`: accept `hostAddress → namespaceAddress` tcp dports in `webPortRange`; nothing else inbound (egressBroker's chain already drops everything except the proxy port from the namespace side — read it and add the one rule the way it adds its own). polkit: the lane's rule shape for `seat@*` (start/stop/restart) for `operatorUser`.
- `hosts/core/seat.nix`: `services.seat-lane = { enable = true; keyFile = "/var/lib/secrets/openrouter-key"; hostAddress = "10.100.4.1"; namespaceAddress = "10.100.4.2"; listenPort = 3141; operatorUser = "dalhaka"; }`.

- [ ] **Step 1: Failing checks** — `seat-eval` (pattern: `lane-eval`): asserts on the evaluated core config — instance `seat` exists with `allow == ["openrouter.ai"]` and the inject valueFile; the template's `NetworkNamespacePath`, `User`, every `Environment` entry above, `InaccessiblePaths` contains `/var/lib/secrets`, no `Environment` value looks like a key (regex `sk-or-`), polkit rule text contains `seat@`, 10.100.4.x collides with no other instance (assertion over all instances' addresses); `seat-assertion-negative` (pattern: `lane-assertion-negative`): a config that sets `keyFile` to a store path fails eval with the module's message, and one that puts a real-looking key into the unit environment fails. `seat-unit`: `pytest tests/seat -q` (SB3's tests + seat-run's).
- [ ] **Step 2: Red** — the checks fail (module absent). **Step 3: Implement** (read modelLane.nix and egressBroker.nix in full first; copy their shapes; do not modify the lane). **Step 4: Green** — `nix build .#checks.x86_64-linux.{seat-eval,seat-assertion-negative,seat-unit,host-core,lint} -L --no-link`; the toplevel builds (`nix build .#nixosConfigurations.core.config.system.build.toplevel --no-link`); lint gate. **Step 5: Commit.**

**touches:** nixosModules/seatLane.nix, hosts/core/seat.nix, hosts/core/default.nix, pkgs/seat/seat-run.py, pkgs/seat/default.nix, flake.nix, tests/seat/test_seat_run.py
**acceptance:** seat-eval, seat-assertion-negative, seat-unit, host-core, lint
**commit subject:** `seat: services.seat-lane — a broker instance, netns and seat@<job> units running as the operator with the key injected at egress; polkit, spool, eval and negative checks (test: seat-eval, seat-assertion-negative, seat-unit, host-core, lint)`

### SB4 (code, M) — `seat-vm`: the VM proves injection, refusal, isolation and the UI path

**dependsOn:** SB1, SB2, SB3

**Files:** `tests/integration/seat-vm.nix` (new; pattern `tests/integration/lane-vm.nix`: generated CA, fake `openrouter.test` logging the `Authorization` header and path), `flake.nix` (check `seat-vm`)

- [ ] **Step 1: The test** — node `machine` with `services.seat-lane` on `openrouter.test`, a fake upstream, a fake key file `/var/lib/secrets/openrouter-key` = `sk-or-vm-fixture`, user `dalhaka`. Script: as the operator, `seat-submit headless --workspace /tmp/ws --dsh-home /tmp/dsh --model deepseek/deepseek-v4-flash --effort off --brief /tmp/brief` (a brief the fake answers) → the fake's log shows `Authorization: Bearer sk-or-vm-fixture` while `systemctl show -p Environment seat@<id>` shows only `injected-by-broker`; a `POST /api/v1/messages` from inside the unit is refused before injection (audit reason as the lane's); `curl https://example.test` from inside the namespace fails (no route); a web job's `url.txt` names `10.100.4.2:<port>`; `curl` from the host side reaches it, `curl` from a second namespace (or with a spoofed source) does not; the audit log has both requests. Red: with the module's inject removed (a `lib.mkForce {}` in a negative node or by asserting the header BEFORE the fix in the first run), the header is the placeholder — show the assertion that would fail.
- [ ] **Step 2: Green** — `nix build .#checks.x86_64-linux.seat-vm -L --no-link` (minutes); lint gate. **Step 3: Commit.**

**touches:** tests/integration/seat-vm.nix, flake.nix
**acceptance:** seat-vm, lint
**commit subject:** `seat: seat-vm proves the injected header, the refused path, namespace isolation and the host-side UI path (test: seat-vm, lint)`

### SB5 (docs, S) — the runbook, the board, the claim; the operator's migration commands

**dependsOn:** SB4

**Files:** `docs/runbooks/seat.md` (new), `docs/runbooks/lanes.md` (one paragraph: the seat is a lane now), `CLAUDE.md` (Commands: `systemctl start seat@web-1` and where the URL is), `docs/ledger/claims.toml` (`seat-key-exception-undecided` → text/closes_by pointing at the switch and the deletion), `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md` (addendum: the exception closed by design)

- [ ] **Step 1** Runbook, plain language, one command each: start a web seat and open it; run a headless job by hand; watch the audit; stop a job; delete the key file after the first successful jobs; rollback. **Step 2** lint gate; commit.

**touches:** docs/runbooks/seat.md, docs/runbooks/lanes.md, CLAUDE.md, docs/ledger/claims.toml, docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md
**acceptance:** lint
**commit subject:** `docs: the seat runs behind its broker — runbook, board, claim, decision addendum (test: lint)`

### SB2b (code, S) — SB2 fix round: the CA requirement is pinned, a pre-set key never leaves the process under `--broker`, the bind address is validated, the route check reads the `via` field, the bind test pins argv and exit status

**dependsOn:** none

Gate `docs/reviews/2026-09-05-opus-review-sb4-SB2.md` — REJECTED on one major (the `NODE_EXTRA_CA_CERTS` half of contract item 2 has no test: deleting the guard leaves 95/95 green) with six minors; the credential path itself was proven clean by strace (the key file is never opened or stat'ed under `--broker`). Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/sb4/SB2 task/SB2 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with SB2's subject.

**Contract additions:**
1. `NODE_EXTRA_CA_CERTS` unset → `die 5`; set to a missing file → `die 5`; set to a directory → `die 5`; each its own test (mutation: the guard deleted → three tests fail).
2. Under `--broker` the credential is ALWAYS the placeholder: a pre-set `OPENROUTER_API_KEY` is replaced by `injected-by-broker` (one stderr line says a key was present and ignored), so no real key can leave the process from this wrapper; the launch banner states `credential: placeholder (broker injects)` truthfully (mutation: the placeholder only when unset → the test with a pre-set `sk-or-` value fails, asserting the fake upstream saw the placeholder).
3. `--bind-namespace ADDR` accepts only a dotted IPv4 address that is not `0.0.0.0`, not loopback and not a flag-shaped string; anything else → `die 2` (mutation: validation removed → fails).
4. The route check parses `ip -4 route show default` line by line and compares the token AFTER `via` to the proxy host — never a substring test — and requires exactly one default route (mutation: substring test → the synthetic `default via 192.168.1.1 dev via 10.100.4.1 x` line is accepted → fails).
5. The dead `[ -n "$proxy" ]` line goes; `HTTPS_PROXY` must match `^http://[^/:]+:[0-9]+/?$` (mutation: the form check removed → `https://` and socks values pass → fails).
6. The bind test pins the real argv and the exit status: a fake `node` (or the interpreter the wrapper execs — read `runtimeEnv` and put a fake first on PATH, or point `DSH_OPENROUTER_BIN_JS` at a fixture the fake reads) records its argv; the test asserts `--host 10.100.4.2` in the recorded argv, exit 0, and `OPENROUTER_BASE_URL` at the fake upstream — no `bash -x` scraping (mutation: `--host` stays `127.0.0.1` → fails).
7. Not in this task, recorded for SB4: the proof that traffic traverses the broker (`NODE_USE_ENV_PROXY=1` or the harness's proxy setting; `AF_NETLINK` in the unit's `RestrictAddressFamilies` for `ip route`).

- [ ] **Step 1: Tests, red on SB2** — the three CA cases; the pre-set-key case; `--bind-namespace 0.0.0.0`, `--bind-namespace --profile`, `--bind-namespace 127.0.0.1`, `--bind-namespace 10.100.4.2` (accepted); the synthetic route line; `HTTPS_PROXY=https://…` and `socks5://…` → 5; the argv-recording bind test with exit status and base URL. SB2's six tests and RT5rb's 89 stay as they are.
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/70-dsh-openrouter.bats`; `unit`; `host-core`; lint gate; SB2's 9 kills still die; the seven mutations above each fail a test. **Step 5: One commit**, SB2's subject.

**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: --broker runs the seat without a key behind an egress broker (proxy + CA from the unit, placeholder credential, namespace bind for the UI); the key-file path is deprecated (test: unit, host-core, lint)`

### SB2r (code, XS) — re-plan of SB2 (rule A1): the bind address is a real IPv4 address (octet range), exactly one default route is pinned, the ignored-key line fires only on a real key, the banner string is the contracted one, an empty bind value is refused, the interpreter seam is a test-only seam

**dependsOn:** none

Gates `docs/reviews/2026-09-05-opus-review-sb4-SB2.md` and `…-sb5-SB2b.md`: SB2b closed sb4's gap (the CA guard now kills three tests; strace proves the key file is never opened under `--broker`) and was rejected on one narrow major — the IPv4 check tests the dotted-quad shape only, so `--bind-namespace 256.1.1.1` reaches the real `--host` argv — plus six minors. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/sb5/SB2b task/SB2b && git cherry-pick -n FETCH_HEAD`; read both reviews in full; ONE commit with SB2's subject.

**Contract:** SB2b's behaviour stands; these are the corrections.
1. `--bind-namespace` accepts a dotted IPv4 address whose four octets are each 0–255 (leading zeros refused), not `0.0.0.0`, not `127.0.0.0/8`, not empty, not flag-shaped; `256.1.1.1`, `999.999.999.999`, `300.300.300.300`, `01.2.3.4`, `--bind-namespace ''` → `die 2` (mutation: octet range dropped → fails; empty accepted → fails).
2. Exactly one default route is pinned: two default routes, one of them via the proxy host → `die 5` (mutation: `-eq 1` → `-ge 1` → fails).
3. The ignored-key stderr line fires only when the pre-set `OPENROUTER_API_KEY` differs from the placeholder (SB1's unit sets the placeholder itself, so production launches are silent); a test pins both cases.
4. The launch banner prints the contracted string `credential: placeholder (broker injects)` under `--broker` (mutation: string changed → fails).
5. `DSH_OPENROUTER_NODE` (the interpreter seam SB2b added for the argv-pinned test) is honoured only when `DSH_OPENROUTER_TEST_SEAM=1` is also set; otherwise the wrapper ignores it with one stderr line; the seat unit never sets either (a test pins: seam set without the flag → the real interpreter path is what runs).
6. A runbook line in `docs/runbooks/lanes.md` names the bind rule and the seam flag.

- [ ] **Step 1: Tests, red on SB2b** — the four invalid addresses and the empty value; the two-default-routes case; the ignored-key line present/absent; the banner string; the seam without the flag. **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/70-dsh-openrouter.bats`; `unit`; `host-core`; lint gate; SB2b's 8 kills and RT5rb's 27 still die; the five mutations above each fail a test. **Step 5: One commit**, SB2's subject.

**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats, docs/runbooks/lanes.md
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: --broker runs the seat without a key behind an egress broker (proxy + CA from the unit, placeholder credential, namespace bind for the UI); the key-file path is deprecated (test: unit, host-core, lint)`

### SB3b (code, S) — SB3 fix round: the job id is read from stdout alone and validated; isolation and the start/wait half pinned

**dependsOn:** none

Gate: `docs/reviews/2026-09-05-opus-review-sb1-SB3.md` — REJECTED: F1 `factory-task` reads the id from merged stdout+stderr (a failure path records an error line as the id); F2 the P0 `DSH_HOME` isolation, `--workspace` and the brief content are not asserted through the fake; F3 `seat-submit`'s start/wait/stream/exit half is untested. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/sb1/SB3 task/SB3 && git cherry-pick -n FETCH_HEAD`; read the review; ONE commit with SB3's subject.

**Files:** `tools/factory/seat/factory-task`, `pkgs/seat/seat-submit.py`, `tests/seat/test_seat_submit.py`, `tests/unit/80-seat-driver.bats` (+ carried SB3 files)

- [ ] **Step 1: Tests first, red on SB3** — bats: the fake `seat-submit` prints a warning line to STDERR before the id on STDOUT → `.result`'s `seat:` line names the id, not the warning (F1); the fake receives `--dsh-home <runs_dir>/<KEY>.dsh-home` (the isolated home, never the shared one), `--workspace <the factory-ws path>`, and a `--brief` file whose content equals the composed brief (F2 / M13 / M14); a fake that prints a non-id first line (`garbage`) → `factory-task` writes `status=failed` and a `seat:` line reading `seat: submit failed (no job id)` instead of recording garbage. pytest (F3, monkeypatched `subprocess.run` and a fake job dir the test fills): `--no-start` never calls `systemctl` (assert the mock was not called); `headless` waits until `result.txt` appears, copies `stdout.txt` to stdout, exits with `exit_code.txt` (0 and 3 both asserted); `--timeout 1` with no result → exit 124 and a `systemctl stop seat@<id>` call (so a timed-out job is not orphaned — new, disclosed); a `PermissionError` on the jobs dir → exit 2 with a message (M9), not a traceback.
- [ ] **Step 2: Red.** **Step 3: Implement**: `factory-task` captures stdout and stderr separately (`seat_id=$(… 2>"$err_file")`), validates `^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$` before use, and streams `seat-submit`'s stderr to the task log as it arrives (so the operator sees the id early); `seat-submit` flushes stdout after printing the id (`print(id, flush=True)`) and adds the stop-on-timeout. **Step 4: Green** — ruff; shellcheck; `nix develop -c pytest tests/seat -q`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; lint gate; SB3's 9 killed mutants + the 5 survivors (M3, M4, M13, M14, the id one) all die. **Step 5: One commit**, SB3's subject.

**touches:** tools/factory/seat/factory-task, pkgs/seat/seat-submit.py, pkgs/seat/default.nix, tests/seat/test_seat_submit.py, tests/unit/80-seat-driver.bats, tools/factory/seat/README.md, docs/MAP.md
**acceptance:** unit, lint
**commit subject:** `seat: seat-submit writes a job directory and starts seat@<id>; factory-task submits through it when the unit exists (test: unit, lint)`

## Amendments from the plan-writing comparison (2026-09-05 late; judge: docs/reviews/2026-09-05-plan-writing-comparison.md)

Three blind plans for this spec were scored against this one; two beat it. Their technically correct points are folded in here as requirements (the blind plans are the record under docs/reviews/plan-comparison/):
1. **SB1 — UI reachability is an `output`-hook rule.** Host → namespace traffic to `10.100.4.2:<port>` from the host side is matched in the `output` hook (host-originated), in the seat's own chain with a trailing drop — not in `input` or `forward` (GLM plan; Kimi's `forward` rule would be dead and Pro's `input` rule wrong saddr). SB4's VM step must prove the rule is live (a mutation dropping it → the host-side curl fails).
2. **SB1 — `RestrictAddressFamilies` must include `AF_NETLINK`**, or the wrapper's `--broker` route check (`ip route`) dies on every launch (Kimi plan). SB4 asserts the check passes inside the unit.
3. **SB1 — proxy for Node.** dsh is a Node program: set `NODE_USE_ENV_PROXY=1` (Node ≥ 24 honours `HTTPS_PROXY` only with it) in the unit environment, or state the shim used; SB4 proves a request actually traverses the broker (the audit line), not just that env vars are set.
4. **SB1/SB5 — the backup exclusion task exists** (spec §3: `/var/lib/seat/jobs/*/dsh-home/sessions` excluded from restic as the lane's are): SB1 adds the exclude to `hosts/core/proton-backup.nix`'s list the way the lane's is added, with the eval check asserting it.
5. **Every SB section names mutation targets for the reviewer and shows red-before-green commands** (criterion 4; this plan scored 2/3 there).

### SB4b (code, M) — SB4 fix round: dsh stays on loopback and a forwarder bound to the namespace address carries the UI; two module bugs the VM found are fixed in the module; the VM proof completes

**dependsOn:** none

Seat run sb7 (2026-09-06, 2 h 53 min, no commit) stopped at a real finding, not a seat failure: the pinned dsh harness (0.1.2-rc.1) pins its web server to loopback — `--host 10.100.4.2` is refused by the webserver schema (`expected "127.0.0.1" | "0.0.0.0"`) and `--host 0.0.0.0` by a deliberate guard in `dsh-web-app/lib/startup.js` ("would expose remote code execution to the network"). So the spec's §5 sentence "inside the namespace the UI binds `10.100.4.2:<port>`" and SB2r's `--bind-namespace ADDR → --host ADDR` rest on a false assumption. The seat's staged, uncommitted work in `/home/dalhaka/factory/ws/sb7/SB4` (`tests/integration/seat-vm.nix` + the `flake.nix` wiring; steps 1–5 green, red proven with the inject removed) is the starting point: fresh workspace from main; `git -C /home/dalhaka/factory/ws/sb7/SB4 diff --cached | git apply --index`; read `/home/dalhaka/factory/runs/sb7/SB4.log` from its last 300 lines; ONE commit with SB4's subject.

**Decision (orchestrator, 2026-09-06 ~01:25 CDT; the operator may veto):** dsh's loopback guard is honoured, not routed around inside dsh. Inside the seat's namespace dsh binds `127.0.0.1:<port>` as it insists; a forwarder owned by the same unit (`socat`, a runtime dependency of the wrapper under `--broker` only) listens on `10.100.4.2:<port>` and relays to `127.0.0.1:<port>`. The exposure is unchanged from the spec: `10.100.4.2` is the namespace end of a veth whose only peer is this host, the nftables rule already limits host→namespace traffic to the UI port range, and nothing on the network can reach either address. The spec's §5 sentence is amended to "the UI is reachable at `10.100.4.2:<port>`; dsh itself binds loopback and a unit-owned forwarder relays" (SB5 writes the amendment into the spec and the runbook). Option C (a newer dsh with an authenticated non-loopback bind) is a research item for the dsh repo, not this plan.

**Contract:**
1. Wrapper: `--bind-namespace ADDR` keeps every SB2r validation and no longer reaches `--host`; dsh is always started with `--host 127.0.0.1`; under `--bind-namespace` the wrapper starts `socat TCP-LISTEN:<port>,bind=ADDR,fork,reuseaddr TCP:127.0.0.1:<port>` in the background before exec'ing dsh, and the forwarder dies with the unit (control-group kill) — a bats test with a fake `socat` on PATH pins the argv (bind address, port, target) and that `--host 127.0.0.1` is what reaches the interpreter seam; a second test pins that without `--bind-namespace` no `socat` is spawned (mutation: `--host` given ADDR again → the seam test fails; the fork flag dropped → the argv test fails).
2. Module bug 1, fixed in the module not the fixture: `ReadWritePaths` entries that may be absent on a fresh machine carry the `-` prefix (systemd ignores a missing path), so `seat@` no longer fails at namespace setup with status 226 on a machine without `~/factory`, `~/nixos-agent-env`, `~/flakes` or `~/.local/share/dsh-openrouter` (mutation: one `-` removed → the fresh VM run fails 226; the VM asserts `systemctl show -p Result seat@<id>` is `success`).
3. Module bug 2, fixed in the module: the secrets directory the `seat-secret` path creates is traversable by the broker user (the mode and group the lane module already uses for its own key — read it, never invent a new one; never 0700 root-only), so the broker starts once (`NRestarts=0` asserted in the VM) instead of crash-looping on `PermissionError: openrouter-key` (mutation: the mode restored to 0700 → the VM's `NRestarts=0` assertion fails).
4. The VM's step 6 completes: a web job's `url.txt` names `10.100.4.2:<port>`; `curl` from the host reaches the UI through the forwarder; `curl` from a second namespace does not; inside the unit `ss -ltn` shows dsh on `127.0.0.1:<port>` only and the forwarder on `10.100.4.2:<port>` only (this line is what proves dsh's guard is honoured; mutation: the forwarder bound to `0.0.0.0` → fails); the audit log has both requests.
5. Red-before-green in the report: the first VM run's failure at step 6 (dsh refusing the address) is quoted; with the forwarder removed (`lib.mkForce` on the wrapper argv or an empty `socat` fake) the host `curl` fails — show the assertion.

- [ ] **Step 1: Tests** — the wrapper's bats cases of item 1 (red on main: the fake `socat` is never called, `--host` carries ADDR); the VM assertions of items 2–4 added to `seat-vm.nix`. **Step 2: Red** (paste the bats numbers and the VM failure line). **Step 3: Implement** — wrapper, `nixosModules/seatLane.nix`, the wrapper package's runtime deps (`socat`). **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/70-dsh-openrouter.bats`; `unit`; `host-core`; `nix build .#checks.x86_64-linux.seat-vm -L --no-link`; lint gate; SB2r's kills still die plus the five mutations above. **Step 5: One commit**, SB4's subject; end with the FACTORY-RESULT block, never prose.

**touches:** tests/integration/seat-vm.nix, flake.nix, nixosModules/seatLane.nix, pkgs/dsh-openrouter/dsh-openrouter.sh, pkgs/dsh-openrouter/default.nix, tests/unit/70-dsh-openrouter.bats
**acceptance:** seat-vm, unit, host-core, lint
**commit subject:** `seat: seat-vm proves the injected header, the refused path, namespace isolation and the host-side UI path (test: seat-vm, lint)`

### SB6 (code, S) — the seat's hand-launch footguns close and a failed unit is reported at once: `--bind-namespace` requires a validated `--port`, the forwarder's lifecycle is asserted in the VM, `seat-submit` watches the unit's `Result`

**dependsOn:** none

From the sb8 gate (`docs/reviews/2026-09-06-opus-review-sb8-SB4b.md`, APPROVED with seven minors, SB4b landed 0029f89): (1) `--bind-namespace` without an explicit `--port` spawns a forwarder with an empty listen port (`TCP-LISTEN:,bind=…`) while dsh takes `--port 0` — exit 0, UI unreachable, nothing reported (production is unaffected: `seat-run.py` always passes `--port`); (2) the port reaches socat's address-option string unvalidated (`--port '43210,su=nobody'` is spliced in verbatim; no privilege boundary is crossed, but the argument is a string where a number belongs); (3) the VM never asserts the forwarder dies with the unit — the reviewer added the assertion in the clone and it passed, so the tree lacks a guard the contract rests on; (4) a failed `seat@` unit is noticed only when `seat-submit`'s 10,800 s poll for `result.txt` gives up — the reviewer's mutant run was still polling at forty minutes; the same shape would hang the operator; (5) the secrets-directory tmpfiles rule sits per lane though the 2026-09-03 broker-secret-ownership amendment puts it once in the broker module at 0750 (note only; the broker module is outside this task); (6) joining the whole `socat` package exports seven binaries onto the unit's PATH and collides cosmetically with `hosts/core/agent-prereqs.nix`'s socat (same version); (7) the `/api/v1/messages` refusal probe runs from the namespace, not from inside the unit's user and cgroup.

**Contract:**
1. `--bind-namespace` without `--port` → `die 2 "--bind-namespace needs --port"`; `--port` must be an integer 1024–65535 (a value with any non-digit → `die 2`) before it reaches either argv (mutation: the integer test dropped → the `43210,su=nobody` test fails; the pairing dropped → the no-port test fails).
2. The VM asserts the forwarder's lifecycle: `pgrep -x socat` succeeds while the unit runs; after `systemctl stop seat@<id>` it fails and `ss -ltn` inside the namespace no longer lists the port (mutation: `KillMode` changed so the forwarder outlives the unit → fails).
3. `seat-submit` watches the unit: while polling for `result.txt` it also polls `systemctl show -p ActiveState,Result seat@<id>`; `inactive` with `Result != success` (or `failed`) ends the wait at once with exit 3 and the unit's `Result` and the last ten journal lines on stderr (the VM asserts it: a job whose unit fails on purpose — a bad `ReadWritePaths` entry via `lib.mkForce` in a negative node — returns within 30 s, not 10,800; mutation: the unit poll dropped → the negative node's timing assertion fails).
4. The refusal probe runs from inside the unit (`systemd-run --scope`-free: through the job's own script or a `seat@` exec) so the unit's user and cgroup are the ones refused (mutation: the probe moved back to `ip netns exec` → a test asserting the audit line's peer is the unit's user fails, if the audit line carries it; else say what pins it).
5. The wrapper package joins `socat`'s single binary only (`lib.getBin` or a `symlinkJoin` of `bin/socat`), with the comment naming the collision it avoids; the tmpfiles note from (5) is carried to the broker module's next task as a board line.

- [ ] **Step 1: Tests, red on main** — the two wrapper cases (bats); the lifecycle and the negative-node assertions in `seat-vm.nix`; the in-unit probe. **Step 2: Red** (paste). **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/70-dsh-openrouter.bats`; `unit`; `host-core`; `seat-vm --rebuild`; lint gate; SB4b's mutants still die plus the four above. **Step 5: One commit.**

**touches:** pkgs/dsh-openrouter/dsh-openrouter.sh, pkgs/dsh-openrouter/default.nix, tests/unit/70-dsh-openrouter.bats, nixosModules/seatLane.nix, tests/integration/seat-vm.nix, pkgs/seat/seat-submit.py
**acceptance:** seat-vm, unit, host-core, lint
**commit subject:** `seat: --bind-namespace needs a validated --port, the forwarder dies with the unit (asserted), seat-submit reports a failed unit at once, the probe runs from inside the unit (test: seat-vm, unit, host-core, lint)`
