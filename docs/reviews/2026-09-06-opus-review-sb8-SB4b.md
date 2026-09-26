# Opus gate — seat run sb8, task SB4b — APPROVED

Branch `task/SB4b`, base `dd0030f` (main), head `e072d76`, one commit, seven
files. Reviewed in a fresh clone
(`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-sb8-SB4b`);
nothing under `/home/dalhaka/factory` or `/home/dalhaka/nixos-agent-env` was
modified except this file.

## Summary

Every claim the implementer made is true and I rebuilt all of it. `seat-vm`,
`unit`, `host-core`, `lint` are green from a forced rebuild; 116/116 bats; the
`docs/MAP.md` regeneration reproduces byte for byte; the closure delta that
switch #20 carries for *this branch alone* is one line (`dsh: 8.1 KiB`).

The plan's central design decision — honour dsh's loopback guard and put a
unit-owned `socat` forwarder on the namespace address — is implemented as
specified and **proved**, not asserted. The strongest single piece of evidence
is the real `ss -ltnp` from inside the seat's namespace (I re-ran the VM with
the output printed):

```
State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process
LISTEN 0      511        127.0.0.1:43201      0.0.0.0:*    users:(("node",pid=893,fd=22))
LISTEN 0      5         10.100.4.2:43201      0.0.0.0:*    users:(("socat",pid=922,fd=5))
```

dsh (`node`) on loopback only; the forwarder on the veth address only; nothing
on `0.0.0.0`. Nine mutations run (three bats, two VM, plus SB2r's whole table
re-applied), and one reviewer-added VM assertion; every behaviour-changing row
dies. Seven minors, no MAJOR.

## The VM proof (assertions, cited)

`nix build .#checks.x86_64-linux.seat-vm -L --no-link --rebuild` → exit 0,
`(finished: run the VM test script, in 24.01 seconds)`. Every item the gate
required is a real assertion (`machine.succeed` / `machine.fail` / a python
`assert`), never a log line. Line numbers are `tests/integration/seat-vm.nix`.

| required | assertion | line |
|---|---|---|
| fake upstream logs `Authorization: Bearer sk-or-vm-fixture` | `assert "Bearer sk-or-vm-fixture" in api_log, api_log` | 256 |
| …and the placeholder never reaches upstream | `assert "injected-by-broker" not in api_log, api_log` | 257 |
| `systemctl show -p Environment seat@<id>` shows only the placeholder | `assert "OPENROUTER_API_KEY=injected-by-broker" in env` / `assert "sk-or-vm-fixture" not in env` | 265, 266 |
| …and the key is nowhere in the unit or the spool | `machine.fail("systemctl cat 'seat@.service' \| grep -q sk-or-vm-fixture")`, `machine.fail("grep -rq sk-or-vm-fixture /var/lib/seat/jobs")` | 267, 268 |
| POST `/api/v1/messages` refused before injection, with the lane's reason | `assert "egress-broker: denied" in deny_resp` + `jq -es '… .verdict=="deny" and .reason=="path-not-permitted" … length == 1'` | 281, 282–286 |
| …and it never reached upstream | `assert "/api/v1/messages" not in api_log2` | 288 |
| `curl https://example.test` from the namespace fails | `machine.fail("ip netns exec egress-seat curl … https://example.test/")` | 293–295 |
| `url.txt` names `10.100.4.2:<port>` | `assert url == "http://10.100.4.2:43201", url` | 310 |
| host curl reaches the UI | `machine.wait_until_succeeds("curl … http://10.100.4.2:43201/")` (finished in 1.46 s) | 312–314 |
| a second namespace does not | `machine.fail("ip netns exec seat-vm-probe curl … http://10.100.4.2:43201/")` (5.03 s = dropped, not refused) | 339–341 |
| `ss -ltn`: dsh loopback only, forwarder veth only | `assert "127.0.0.1:43201" in listen` / `"10.100.4.2:43201" in listen` / `"0.0.0.0:43201" not in listen` / `"[::]:43201" not in listen` | 322–325 |
| `systemctl show -p Result seat@<id>` = success | `machine.succeed(f"test \"$(systemctl show 'seat@{job_id}.service' -p Result --value)\" = success")` | 243–245 |
| broker `NRestarts` = 0 | `machine.succeed("test \"$(systemctl show egress-broker-seat.service -p NRestarts --value)\" = 0")` | 249–251 |
| the audit log has both requests | deny pinned at 282–286; allow at 345–348 (`select(.host=="openrouter.test" and .verdict=="allow") … length >= 1`) | 345–348 |

Full round trip, not just a 200: `assert "vm-seat-answer" in submit` (line 240)
— the fake's content came back through `seat-submit`'s streamed stdout.

## Exposure

- **The forwarder's bind is the veth address only.** Proved by the `ss -ltnp`
  above and by the `0.0.0.0` / `[::]` negative assertions (322–325). The
  wrapper's argv is `bind=${bind_namespace}` and `bind_namespace` survives
  SB2r's full validation unchanged (`pkgs/dsh-openrouter/dsh-openrouter.sh:169–181`:
  needs `--broker`, non-empty, not `0.0.0.0`, not `127.*`, per-octet
  0–255 with no leading zeros). Under strace the exec is literally
  `execve(".../socat", ["socat", "TCP-LISTEN:43210,bind=10.100.4.2"..., "TCP:127.0.0.1:43210"], …)`.
- **The nftables rule confines the host→namespace direction and the port is in
  range.** `nixosModules/seatLane.nix:215–222` renders
  `oifname "veb-seat" ip daddr 10.100.4.2 tcp dport 43200-43299 accept` with
  `oifname "veb-seat" drop` last; `webPortRange` default `43200-43299`
  (`seatLane.nix:53–57`) contains the VM's 43201. The other direction is already
  closed by `egressBroker.nix:187–190`, `chain forward-<name>` dropping both
  `iifname` and `oifname` `veb-seat` — which is why the second-namespace probe
  times out rather than being refused.
- **The forwarder is inside the unit's namespace and cgroup and dies with it.**
  The branch does *not* assert this, so I added the assertion myself and ran the
  VM: `must succeed: pgrep -x socat` → ok;
  `must succeed: systemctl st{op} 'seat@20260906-075731-467d0b.service'` → ok;
  `must fail: pgrep -x socat` → ok; `must fail: ip netns exec egress-seat ss -ltn | grep -q 43201`
  → ok. The claim holds; its absence from the branch is minor 3 below.
- **The forwarder never listens on the host side.** `NetworkNamespacePath = /run/netns/egress-seat`
  (`seatLane.nix:176`, and in the built unit) puts the whole `ExecStart` tree —
  seat-run, the wrapper, node and socat — inside the netns; `ss` had to be run
  with `ip netns exec egress-seat` to see either listener.
- **`reuseaddr` cannot hijack a running job's port.** socat's `reuseaddr` is
  `SO_REUSEADDR`, not `SO_REUSEPORT`; on Linux a second listener on the same
  (address, port) still gets `EADDRINUSE`. Two web jobs on the same port: the
  second job's socat exits, and its dsh also fails to bind `127.0.0.1:43201`
  (the first job's node holds it), so the second job fails closed rather than
  stealing the first. `reuseaddr` only shortens `TIME_WAIT` after the first job
  is gone. This is visible in the M-D run below, where a `0.0.0.0` socat and a
  `127.0.0.1` node contend and the UI simply never comes up.
- **Injection through the argv:** ADDR is validated; **the port is not** — see
  minor 2. It cannot cross a privilege boundary (see there), and it cannot move
  the listener outside the netns.

## Wrapper

`pkgs/dsh-openrouter/dsh-openrouter.sh:745–763`. dsh is now unconditionally
`--host 127.0.0.1`; `--bind-namespace` reaches only the forwarder.

- The bats cases exist and are load-bearing: test 93 pins
  `argv_flat == *"--host 127.0.0.1"*`, `!= *"--host 10.100.4.2"*`,
  `socat_flat == *"TCP-LISTEN:43210,bind=10.100.4.2,fork,reuseaddr"*` and
  `*"TCP:127.0.0.1:43210"*`; test 94 pins `[ ! -e "$TMPHOME/socat-argv.txt" ]`
  without `--bind-namespace`. `make_fake_socat`
  (`tests/unit/70-dsh-openrouter.bats:1515–1526`) shadows the real socat because
  `default.nix` deliberately joins socat as a package sibling rather than a
  `runtimeInput` (which `writeShellApplication` would prepend to the wrapper's
  own PATH).
- **A refused launch leaves no forwarder.** I ran the wrapper with a fake `ip`
  reporting a wrong gateway: `STATUS=5`,
  `OUTPUT=dsh-openrouter: --broker outside a broker namespace`,
  `SOCATEXISTS=NO`. The spawn sits after the proxy/CA/route checks and after the
  workspace refusal list, so a refusal never starts a relay.
- **The key file is never opened.** strace over the full `--broker
  --bind-namespace` launch, tracing `openat,open,stat,newfstatat,execve`:
  `grep -F "openrouter/key" strace.txt` → `NONE`. (No strace case exists in the
  bats file; this is my own run, matching sb4/rt8's method.)
- **SB2r's whole matrix still holds.** 116/116 pass, including 101–103 and
  108–112 (the `0.0.0.0`, flag-shaped, loopback, out-of-range-octet,
  leading-zero and empty-value rejections), 105 (`via` as a token, not a
  substring), 113 (exactly one default route), 114/115 (the ignored-key line
  and the banner), 90/100 (the mode-000 key file launches and sends the
  placeholder), 116 (the seam flag).
- **`pkgs/dsh-openrouter/default.nix` adds exactly `socat`** to the
  `symlinkJoin` `paths` (and to the argument set). Nothing else in the wrapper's
  closure changed — see the closure diff below.

## Module

- **`ReadWritePaths` `-` prefixes** are on the four operator-home paths only
  (`seatLane.nix:186–192`); `/var/lib/seat` — created by this module's own
  tmpfiles rule and therefore always present — keeps no prefix. Correct scoping.
  The prefix survives the NixOS option type and reaches the unit file verbatim;
  from the built `host-core` toplevel
  (`/nix/store/9xnzhksy…-nixos-system-core-…/etc/systemd/system/seat@.service`):

  ```
  ReadWritePaths=/var/lib/seat
  ReadWritePaths=-/home/dalhaka/factory
  ReadWritePaths=-/home/dalhaka/nixos-agent-env
  ReadWritePaths=-/home/dalhaka/flakes
  ReadWritePaths=-/home/dalhaka/.local/share/dsh-openrouter
  ```

  `systemd.exec(5)` documents `-` for `ReadWritePaths=` ("ignore … if it does
  not exist"), and the VM is the empirical proof: the test creates none of the
  four (comment at 225–230, and no such `mkdir` appears anywhere in the run log)
  and `Result` is `success`.
- **The secrets directory** is `"d /var/lib/secrets 0710 root egress-broker -"`
  (`seatLane.nix:134`). The group is exactly the one the lane already uses for
  the key file — `nixosModules/modelLane.nix:202`,
  `"z ${i.keyFile} 0440 root egress-broker -"` — and `egress-broker` is a single
  system user shared by all instances (`egressBroker.nix:321,338–342`), so this
  grants no new principal anything. `0710` is traverse-only: the broker can open
  the known key path and cannot list the directory's siblings, i.e. narrower
  than both the `0750` in the 2026-09-03 amendment and the `0711` workaround
  sb7 had in its fixture. Not wider than needed. See minor 4 on where the rule
  lives.
- **`InaccessiblePaths = [ "/var/lib/secrets" ]`** is untouched
  (`seatLane.nix:197`) and present in the built unit above, so the seat still
  cannot read the key it just made traversable for the broker.
- `host-core` evaluates and the toplevel builds.

## Checks and the closure diff

All from the clone, all forced rebuilds where the flag exists.

| check | command | result |
|---|---|---|
| shellcheck | `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` | `SHELLCHECK=0` |
| bats 70 | `nix develop -c bats tests/unit/70-dsh-openrouter.bats` | 116/116, last `ok 116` |
| unit | `… .#checks.x86_64-linux.unit -L --no-link --rebuild` | `unit=0` |
| host-core | `… host-core … --rebuild` | `host-core=0` |
| seat-vm | `… seat-vm … --rebuild` | exit 0, script 24.01 s |
| lint | `… lint … --rebuild` | `lint=0` |
| lint gate | `nix develop -c githooks/pre-commit` | `PRECOMMIT=0` (`All checks passed!`, 0 files reformatted; it regenerated the board queue block, which this branch correctly does not commit) |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | `MAPDIFF=0` — byte identical |
| toplevel | `nix build .#nixosConfigurations.core.config.system.build.toplevel` | ok |

`nix store diff-closures /run/current-system ./result` — what switch #20 would
change (this is the whole backlog since the live generation, not just SB4b):

```
dsh: 57.5 KiB
egress-policy-seat.json: ∅ → ε
hook: 43.2 KiB
python3-minimal: ∅ → 3.13.15, 25.3 MiB
seat: ∅ → ε
seat-run.py: ∅ → ε
unit-egress-broker-seat.service: ∅ → ε
unit-egress-netns-seat.service: ∅ → ε
unit-script-egress-netns-seat: ∅ → ε
unit-script-egress-netns-seat-pre: ∅ → ε
unit-seat: ∅ → .service
```

Every line is the seat lane (SB1/SB2/SB3 + this round): the broker instance's
policy and netns/broker units, the `seat@` unit, `seat-run.py` and its
`python3-minimal` interpreter, and the wrapper. `hook` is RT5rb's. Nothing
unexplained. I also isolated **SB4b's own** contribution by building `dd0030f`'s
toplevel and diffing it against HEAD's:

```
dsh: 8.1 KiB
```

One line, no new store paths — socat 1.8.1.3 was already in the live closure
(`/run/current-system/sw/bin/socat`), so joining it into the harness adds
symlinks and nothing else. (One within-closure side effect that
`diff-closures` does not surface: minor 5.)

## Red before green

**(a) The wrapper's new bats cases on main's wrapper.** Restoring
`git show dd0030f:pkgs/dsh-openrouter/dsh-openrouter.sh` is exactly mutation
M-A + M-C below (main has `--host "${bind_namespace:-127.0.0.1}"` and no socat
spawn at all). Both die: test 93 fails on `--host` carrying the address and on
the missing `socat-argv.txt`. Restored → 116/116 green.

**(b) sb7's staged work versus this branch.** `git -C /home/dalhaka/factory/ws/sb7/SB4 diff --cached`
carried two fixture workarounds that this branch deletes:

- `chmod 0711 /var/lib/secrets` inside the `seat-secret` fixture script (staged
  diff line 203) — now the module's tmpfiles rule `d /var/lib/secrets 0710 root
  egress-broker -`, and narrower (group-traverse, not world-traverse).
- `machine.succeed("mkdir -p /home/dalhaka/factory /home/dalhaka/nixos-agent-env …")`
  plus `chown -R dalhaka:users /home/dalhaka` (staged diff lines 233–236) — now
  the module's `-` prefixes, and the test deliberately creates none of the four.

Both workarounds papered over module bugs that would have hit a fresh machine at
switch time; both are fixed where the plan said (the module), and the VM run
proves the fixture no longer needs them.

**(c) The `--host` red the round answers.** From
`/home/dalhaka/factory/runs/sb7/SB4.log`: `$.host expected "127.0.0.1" | "0.0.0.0" but got "10.100.4.2"`
(webserver schema) and `--host 0.0.0.0 is intentionally not supported yet for
safety: it would expose remote code execution to the network; use 127.0.0.1
instead` (`dsh-web-app/lib/startup.js`). Both are honoured, not routed around.

**(d) The forwarder removed.** M-D (below) is the stronger form of the same
proof and I ran it rather than M-E: with the forwarder present the host curl
finishes in 1.46 s; with it bound wrong the same `wait_until_succeeds` at line
312 exhausts its 900 s.

## Mutation table

Method: apply → `git hash-object` asserted different from the branch baseline →
fresh run (bats via `nix develop`, so the flake rebuilds the wrapper from the
dirty tracked tree; VM via `nix build` on a staged copy) → `git checkout --`
→ final `git status --porcelain` asserted clean.

| row | mutation | result |
|---|---|---|
| M-A | `--host "${bind_namespace:-127.0.0.1}"` restored | **KILLED — `not ok 93`** |
| M-B | `fork` dropped from the socat address | **KILLED — `not ok 93`** |
| M-C | `if [ -n "$bind_namespace" ]` → `if true` (socat always spawned) | **KILLED — `not ok 94`** |
| M-D (VM) | forwarder bound `0.0.0.0` | **KILLED — `MD_EXIT=1`**, `!!! RequestedAssertionFailed: action timed out after 900.81 seconds`, at testScript line 104 = `seat-vm.nix:312` (`wait_until_succeeds` host curl). Note: it dies one assertion *earlier* than the plan predicted — with socat holding `0.0.0.0:43201`, dsh cannot get `127.0.0.1:43201`, so the relay has no target and the UI never answers. The `ss` assertion at 324 would also have failed had the run reached it. |
| M-E (VM) | forwarder removed | not run — M-D subsumes it (same assertion, and M-D additionally exercises the guard the plan cares about). Stated as skipped. |
| M-F (VM) | one `-` removed (`"-/home/${cfg.operatorUser}/factory"` → `"/home/…"`) | **KILLED — `MF2_EXIT=1`**, and by exactly the assertion the plan named: `!!! RequestedAssertionFailed: command \`test "$(systemctl show 'seat@20260906-082241-fa093e.service' -p Result --value)" = success\` failed (exit code 1)` (`seat-vm.nix:243–245`). The guest journal: `Failed to set up mount namespacing: /home/dalhaka/factory: No such file or directory` / `Failed at step NAMESPACE spawning …/seat-run: No such file or directory` / `status=226/NAMESPACE` / `Result=exit-code`. See minor 7 on how long the unmodified test takes to get there. |
| M-G (VM) | secrets dir back to `0700` | **not run** — budget; the mechanism is verified statically instead (the tmpfiles rule at `seatLane.nix:134`, the shared `egress-broker` user at `egressBroker.nix:338–342`, sb7's log showing the `PermissionError: openrouter-key` crash-loop the `NRestarts=0` assertion at 249–251 pins). Stated as skipped. |

SB2r's table re-applied to this tree (numbering shifted by the one test SB4b
adds):

| row | mutation | result |
|---|---|---|
| SB2r M-A | octet range dropped | **KILLED — 108, 109, 110, 111** |
| SB2r M-A2'' | empty `--bind-namespace` accepted | **KILLED — 112** |
| SB2r M-B | route count `-eq 1` → `-ge 1` | **KILLED — 113** |
| SB2r M-C | ignored-key line unconditional | **KILLED — 114** |
| SB2r M-D | banner string changed | **KILLED — 100, 115** |
| SB2r M-E | `DSH_OPENROUTER_TEST_SEAM` check removed | **KILLED — 116** |
| sb4 M-A | key block not skipped under `--broker` | **KILLED — 90, 100, 115** |

sb5's M-F (`--host` stays `127.0.0.1`) is no longer a mutation — that is now the
product's behaviour — and M-A above replaces it on the same test.

Reviewer-added assertion (not a mutation): the forwarder lifecycle probe in
"Exposure" above, which passed.

Method note for M-F: run unchanged, the mutant reaches the `Result` assertion
only after `seat-submit`'s 10800 s poll expires, so I ran it a second way —
`--no-start` plus a direct unit start, everything else identical — to reach the
same assertion in seconds. The quoted failure is the branch's own assertion at
`seat-vm.nix:243–245`, and the journal above is the mutant's real 226. The
first, unmodified run was still polling after 40 minutes and was abandoned;
minor 7 records why.

## Findings

No MAJORs. Seven minors, none blocking.

1. **`--bind-namespace` without an explicit `--port` spawns a broken forwarder,
   silently** (`pkgs/dsh-openrouter/dsh-openrouter.sh:196–212` sets `web_port`
   only from an explicit `--port`, while `:745–747` defaults dsh to `--port 0`
   afterwards). My run:
   `SOCATARGV=[TCP-LISTEN:,bind=10.100.4.2,fork,reuseaddr TCP:127.0.0.1: ]`,
   `NODEARGV=[… --host 127.0.0.1 --port 0 --no-open]`, `STATUS=0`. socat fails
   to parse, dsh takes a random loopback port, the UI is unreachable and nothing
   reports it. Production is unaffected (`seat-run.py:102–103` always passes
   `--port`), so this is a hand-launch footgun; `--bind-namespace` should
   `die 2` when no port is pinned.
2. **The port reaches socat's address-option string unvalidated.** ADDR gets
   SB2r's full regex; the port gets none. My run with
   `--port '43210,su=nobody'` produced
   `SOCATARGV=[TCP-LISTEN:43210,su=nobody,bind=10.100.4.2,fork,reuseaddr TCP:127.0.0.1:43210,su=nobody]`.
   No privilege boundary is crossed — the caller already owns the wrapper's
   argv; `seat-submit.py:50` coerces `--port` with `type=int`; the unit is
   `NoNewPrivileges=true` and runs as the operator — and the listener cannot
   leave the netns whatever options are appended. Still, a `[0-9]+` guard (and
   ideally a `webPortRange` check) costs nothing. `seat-run.py:94,103` also
   passes `str(job["port"])` unvalidated, so a `"port": null` web job would
   yield `--port None` and a `url.txt` of `http://10.100.4.2:None`; that half is
   SB1/SB3 territory, outside this task's `touches`.
3. **The VM does not assert the forwarder's lifecycle**, though the plan's
   contract item 1 rests on it ("dies with the unit"). I proved it holds by
   adding the assertion (see Exposure), so this is a missing guard, not a
   defect: nothing in the branch would catch a future change that moved the
   forwarder out of the unit's control group. Two lines in `seat-vm.nix` after
   line 341 would close it.
4. **The secrets-directory rule is declared per-lane.** The 2026-09-03 amendment
   in `docs/superpowers/plans/2026-09-03-broker-secret-ownership.md` says
   `d /var/lib/secrets 0750 root egress-broker -` should be "declared once by the
   broker module, not per lane". `nixosModules/egressBroker.nix` has no tmpfiles
   rule at all today (that task never landed), and it is outside SB4b's
   `touches`, so `seatLane.nix:134` was the only in-scope place — the right call
   for this round. Two consequences to carry forward: with `services.seat-lane`
   disabled nothing declares the directory, and if the broker module later adds
   its own `d` line the two rules disagree on the mode (`0750` vs `0710`).
   Worth a line in SB5's spec/runbook amendment.
5. **Joining the whole socat package exports seven binaries and flips a
   system-path collision.** `pkgs/dsh-openrouter/default.nix:102–110` adds
   `socat` to the `symlinkJoin`, which puts `socat`, `socat1`, `filan`,
   `procan`, `socat-broker.sh`, `socat-chain.sh` and `socat-mux.sh` into the
   harness's `bin/` — hence onto the seat unit's `PATH` and, because
   `hosts/core/agent-prereqs.nix:19` installs `dsh-openrouter-pkg` system-wide
   next to a standalone `socat` at line 23, into `/run/current-system/sw/bin`.
   `buildEnv` resolves the collision silently (`ignoreCollisions`), and the
   winner changes: main and the live system resolve `sw/bin/{socat,socat1,filan,procan,socat-*.sh}`
   to `/nix/store/08mnag1s…-socat-1.8.1.3`, this branch's toplevel to
   `/nix/store/a8hj1bz1…-socat-1.8.1.3`. Both are socat 1.8.1.3 and both were
   already in the live closure, so `diff-closures` shows nothing and the effect
   is cosmetic — but it is a real, operator-visible change at switch #20 and
   the comment in `default.nix` does not mention it. A `symlinkJoin` over just
   `${socat}/bin/socat` would avoid it while keeping the fake-socat
   shadowability the comment (correctly) protects.
6. **The refusal probe runs from the namespace, not from inside the unit.**
   `seat-vm.nix:273–280` uses `ip netns exec egress-seat curl`, so it proves the
   broker refuses `/api/v1/messages` on the same path the seat uses, but not
   under the seat unit's user and cgroup. The gate's wording asked for "from
   inside the unit". Equivalent in substance (same netns, same proxy, same
   audit line), weaker in letter.
7. **A failed `seat@` unit is caught only after `seat-submit`'s three-hour
   poll.** `seat-submit` waits for `result.txt` (`--timeout` default 10800 s,
   `pkgs/seat/seat-submit.py:8`) and does not watch the unit, so when the unit
   dies at NAMESPACE nothing writes `result.txt` and `seat-vm.nix:234–238`
   blocks; the `Result == success` assertion at 243–245 that the plan nominates
   as module bug 1's guard is only reached three hours later. My unmodified M-F
   run was still polling at 40 minutes. The guard is real (M-F does die) but
   effectively unusable as a fast signal — and the same shape would bite the
   operator: a `seat@` unit that fails to start leaves `seat-submit` hanging
   silently for three hours. Watching the unit (or a short `--timeout` in the
   VM) would fix both. `pkgs/seat/seat-submit.py` is outside this task's
   `touches`; this belongs to SB5 or a follow-up.

## Verdict

**APPROVED.** The design decision the plan made is implemented exactly as
written and proved by the strongest available evidence: the real listener table
inside the namespace shows dsh on loopback and the forwarder on the veth address
and nothing else, the host reaches the UI through it in 1.46 s, a second
namespace is dropped, and binding the forwarder to `0.0.0.0` makes the VM hang
for 900 s and fail. Both module bugs are fixed in the module, not the fixture,
and each fix is pinned by an assertion that the corresponding mutation kills or
that the fixture's own silence proves. All four acceptance checks are green from
forced rebuilds, the MAP regenerates byte for byte, the commit is one commit
with the plan's exact subject, both trailers and only files inside `touches`
(plus `docs/MAP.md` by rule), and SB4b's own closure delta is a single 8.1 KiB
line. The six minors are hardening and coverage items; none of them changes what
switch #20 does or weakens the exposure argument. Land it.
