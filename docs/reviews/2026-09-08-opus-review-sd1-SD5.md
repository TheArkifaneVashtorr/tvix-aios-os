---
plan_defect: none
mutants_total: 10
mutants_killed: 10
mutants_outside_named: 2
---
# Opus gate — seat run sd1, task SD5 — APPROVED

## Summary

Every numbered item of SD5's contract is met literally, in the five files the
section's `touches` names and nowhere else, in exactly one commit whose subject
is byte-identical to the section's. All three reds the section states were
reproduced independently in a fresh clone (the pytest `KeyError`, the
`seat-eval` `assertMsg`, the VM's `bash=127`), and all five acceptance checks
plus the lint gate, ruff, the MAP diff and `tasks.py check` are green here.
Ten mutants were applied and all ten died — the eight the section names and two
more of my own.

The one deviation the seat disclosed (the dbus probe changed from `test -S` to
`test -r`) is a **corrected plan fact**, not an implementer defect: I ran the
plan's own named mutant in the VM and the corrected probe discriminates —
with `-/run/dbus/system_bus_socket` dropped the probe file holds `dbus=0` **and**
`systemctl=0`, exactly as the section's Tests row predicts, and the VM check
fails. Five MINORs, none gating.

Work was done in `/tmp/claude-1000/-home-dalhaka-nixos-agent-env/dc26f70a-de2c-4054-899c-dd9bf972644c/scratchpad/gate-sd1-SD5`
(a fresh clone of `task/SD5`), with mutants in three private sibling clones.
Nothing under `/home/dalhaka/factory` or `/home/dalhaka/nixos-agent-env` was
modified except this file. No `sudo`, no `systemctl` on the host, no seat
launched, no key read.

## Contract items

**Interface 1 — `seat@`'s `path`.** `nixosModules/seatLane.nix:189-194`:

```
      path = [
        "/run/current-system/sw"
        cfg.harnessPackage
        pkgs.iproute2
        seatSubmit
      ];
```

with `seatSubmit = (pkgs.callPackage ../pkgs/seat { }).seat-submit;`
(`nixosModules/seatLane.nix:22`), beside the pre-existing
`seatRun = (pkgs.callPackage ../pkgs/seat { }).seat-run;` (`:9`) — the same
idiom the section asks for. The old comment `/run/current-system/sw is not
needed here` is gone; `:179-188` states why it is needed now. **MET.**

**Interface 1 — environment.** `nixosModules/seatLane.nix:177`
`DSH_CACHE_ROOT = "/var/lib/seat/cache";` with the reasoning at `:173-176`.
**MET.**

**Interface 1 — tmpfiles.** `nixosModules/seatLane.nix:134`
`"d /var/lib/seat/cache 0700 ${cfg.operatorUser} users -"`. **MET.**

**Interface 1 — `InaccessiblePaths`.** `nixosModules/seatLane.nix:234-238`:

```
        InaccessiblePaths = [
          "/var/lib/secrets"
          "-/run/systemd/private"
          "-/run/dbus/system_bus_socket"
        ];
```

exactly the stated three entries in the stated order. **MET.**

**Interface 1 — `ReadWritePaths` unchanged.** The diff touches no line of the
`ReadWritePaths` block (`nixosModules/seatLane.nix:216-222`, still the five
entries of Assumption 8); `git diff 55753ba..HEAD -- nixosModules/seatLane.nix`
shows no hunk there. **MET.**

**Interface 2 — `seat-run` exports `SEAT_JOB_ID`.** `pkgs/seat/seat-run.py:81`
`os.environ["SEAT_JOB_ID"] = job_id`, placed after `DSH_HOME`/
`OPENROUTER_REASONING_EFFORT` and before `os.chdir` and the mode branch, so it
holds for **every mode**; the module docstring is updated (`:6`). **MET.**

**Interface 3 — `seat-eval` pins each, with its own `assertMsg`.**
`flake.nix:1729-1760`, five new assertions immediately after the `KillMode`
assertion (item 24's placement) and before `builtins.seq`:

- `:1732-1735` `lib.elem "/run/current-system/sw" unit.path && lib.any (p: lib.hasSuffix "-seat-submit" (toString p)) unit.path`
  → `"seat-eval: seat@ path must carry /run/current-system/sw and seat-submit"`
- `:1736-1737` `unit.environment.DSH_CACHE_ROOT == "/var/lib/seat/cache"`
- `:1738-1746` `sc.InaccessiblePaths == [ … the three entries … ]`
- `:1747-1757` `sc.ReadWritePaths == [ … the five entries … ]`
- `:1758-1760` `lib.elem "d /var/lib/seat/cache 0700 dalhaka users -" c.systemd.tmpfiles.rules`

**MET** (see MINOR-3 and MINOR-4 for two wrinkles in how, not whether).

**Interface 4 — the VM probe.** `tests/integration/seat-vm.nix:395-449`, added
as **step 9** after step 8's drop-in cleanup — correct per Assumption item 24,
which supersedes the section's "step 8" wording; not judged a deviation. A
per-instance drop-in for `seat@probe` replaces only `ExecStart`
(`:401-405`), the probe script is written by the test as root and `chmod 755`
before the start (`:407-435`), and the seven lines are asserted one per
`machine.succeed("grep -qx …")` at `:443-449` with exactly the required values
`bash=0 git=0 nix=0 seat_submit=0 cache=0 systemctl=1 dbus=1`. The `/tmp`
`ReadWritePaths` fixture stays (`:181`). `SEAT_JOB_ID` is pinned by the pytest,
not the VM, as the section requires. **MET.**

The seat added one thing the section did not name: a wait for the file to hold
seven lines before asserting (`:439-442`), which removes a start-up race
against `Type=simple`. It cannot mask a failure — under both reds I ran the
seven lines were written and the first `grep` then failed at once.

## Red before green

All three reproduced in fresh clones, base implementation files against the
branch's tests.

**(a) pytest.** `git checkout 55753ba -- pkgs/seat/seat-run.py`, then
`nix develop -c pytest tests/seat -q -k job_id`:

```
>       assert os.environ["SEAT_JOB_ID"] == JOB_ID
E   KeyError: 'SEAT_JOB_ID'
FAILED tests/seat/test_seat_run.py::test_exports_seat_job_id - KeyError: 'SEA...
1 failed, 1 passed, 16 deselected in 0.05s
```

Restored → `nix develop -c pytest tests/seat -q` → `18 passed in 0.03s`.

**(b) seat-eval.** `git checkout 55753ba -- nixosModules/seatLane.nix`, then
`nix build .#checks.x86_64-linux.seat-eval -L --no-link`:

```
error: seat-eval: seat@ path must carry /run/current-system/sw and seat-submit
```

— byte-for-byte the message the section's Step 1(b) predicts. Restored → green.

**(c) seat-vm.** Base `nixosModules/seatLane.nix` + the branch's step 9 (plus a
diagnostic `print` of the probe file, mine, to read the values):

```
PROBEOUT>>bash=127
git=127
nix=127
seat_submit=127
cache=1
systemctl=0
dbus=0

machine: must succeed: grep -qx 'bash=0' /var/lib/seat/probe.out
!!! RequestedAssertionFailed: command `grep -qx 'bash=0' /var/lib/seat/probe.out` failed (exit code 1)
error: Cannot build '/nix/store/x27k9f7az04dl450cwzxg8bl2pzf5svh-vm-test-run-seat-behind-broker.drv'.
```

Exactly the section's predicted red (`bash=127`), and in one build it also
demonstrates the `git=127`, `seat_submit=127` and `cache=1` arms of the Tests
block. Green on the branch: `test script finished in 30.14s`, all seven greps
pass.

## Mutants

Named by the section — 8 of 8 dead. Outside the named set — 2 of 2 dead.

| # | mutant | file | test run | died? |
| - | ------ | ---- | -------- | ----- |
| 1 | drop `"/run/current-system/sw"` from `path` | seatLane.nix:190 | seat-eval (+ VM red c: `git=127`) | yes |
| 2 | drop `seatSubmit` from `path` | seatLane.nix:193 | seat-eval (+ VM red c: `seat_submit=127`) | yes |
| 3 | remove `DSH_CACHE_ROOT` from `environment` | seatLane.nix:177 | seat-eval | yes |
| 4 | drop `"-/run/dbus/system_bus_socket"` | seatLane.nix:237 | **seat-vm** | yes |
| 5 | drop `"/var/lib/secrets"` | seatLane.nix:235 | seat-eval (the pre-existing assertion) | yes |
| 6 | add `"-/tmp"` to `ReadWritePaths` | seatLane.nix:216 | seat-eval | yes |
| 7 | tmpfiles mode `0700` → `0750` | seatLane.nix:134 | seat-eval | yes |
| 8 | `SEAT_JOB_ID = "probe"` (constant) | seat-run.py:81 | pytest | yes |
| 9 | *(outside)* drop `"-/run/systemd/private"` | seatLane.nix:236 | seat-eval | yes |
| 10 | *(outside)* `DSH_CACHE_ROOT = "/var/lib/seat/cache2"` | seatLane.nix:177 | seat-eval | yes |

Failing lines (seat-eval mutants, `nix build .#checks.x86_64-linux.seat-eval -L --no-link`):

```
M1  error: seat-eval: seat@ path must carry /run/current-system/sw and seat-submit
M2  error: seat-eval: seat@ path must carry /run/current-system/sw and seat-submit
M3  error: attribute 'DSH_CACHE_ROOT' missing                      (see MINOR-4)
M5  error: seat-eval: seat@ InaccessiblePaths must hide /var/lib/secrets
M6  error: seat-eval: seat@ ReadWritePaths must be exactly the five entries (the spool + the four -/home tooling paths)
M7  error: seat-eval: seat@ tmpfiles must create the writable cache dir /var/lib/seat/cache (0700 dalhaka, group users)
M9  error: seat-eval: seat@ InaccessiblePaths must hide /var/lib/secrets and systemd's two control sockets (private + dbus)
M10 error: seat-eval: seat@ must set DSH_CACHE_ROOT to /var/lib/seat/cache (the wrapper's writable cache root)
```

**Mutant 4 (the dbus entry) — the one that judges the disclosed deviation.** A
full `seat-vm` build with only that list entry removed:

```
PROBEOUT>>bash=0
git=0
nix=0
seat_submit=0
cache=0
systemctl=0
dbus=0

machine: must succeed: grep -qx 'systemctl=1' /var/lib/seat/probe.out
!!! RequestedAssertionFailed: command `grep -qx 'systemctl=1' /var/lib/seat/probe.out` failed (exit code 1)
error: Cannot build '/nix/store/6mdbxsaml0axz7jcnmmhqbf99kznmc3i-vm-test-run-seat-behind-broker.drv'.
```

Both `systemctl=1` and `dbus=1` flip, so neither probe is vacuous and the
mutant dies twice over. This also settles the seat's disclosed deviation:
`test -r` discriminates where the plan's `test -S` would not (systemd's
inaccessible node is itself a socket), and hiding `-/run/systemd/private`
alone is *not* sufficient — `systemctl start seat@nope` succeeds from inside
the unit when the dbus socket is reachable. Recorded as MINOR-1 against the
plan, not the seat.

Three `seat-vm` builds were spent (green baseline with `--rebuild`, red (c),
mutant 4); the remaining named mutants have a `seat-eval` arm that kills them
in seconds, so their VM arms were not separately built — except where red (c)
already exhibited them (`git=127`, `seat_submit=127`, `cache=1`).

## Checks

In the fresh clone, each `nix build .#checks.x86_64-linux.<name> -L --no-link --rebuild`:

| check | result |
| ----- | ------ |
| seat-eval | exit 0 |
| seat-unit | exit 0 |
| seat-vm | exit 0 (`test script finished in 30.14s`; all seven step-9 greps green) |
| host-core | exit 0 |
| lint | exit 0 |

Also:

- `nix develop -c ruff check pkgs/seat tests/seat` → `All checks passed!`
- `nix develop -c ruff format --check pkgs/seat tests/seat` → `4 files already formatted`
- `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then
  `git diff --exit-code docs/MAP.md` → exit 0 (no MAP change is owed: no new
  package, module, host file, check or top-level entry)
- `nix develop -c python3 pkgs/evidence/tasks.py --root . check` → silent, exit 0
- `nix develop -c githooks/pre-commit` → exit 1, and the ONLY reason is
  `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`.
  The regenerated block differs from HEAD's by one token — `SD5` → `SD6` in the
  derived queue — i.e. it is stale only *because SD5 has since produced a
  `.result` under `~/factory/runs`. It was not stale while the seat ran, and it
  is live-state, not tree-state. Not charged to the seat. Every other gate in
  the hook (treefmt, shellcheck, statix, deadnix, ruff, the bats-chain lint,
  the MAP diff, the one-repo `tasks.py check`) passed.

Driver's record (`~/factory/runs/sd1/SD5.result`) confirmed:
`checks_verified: seat-eval=pass seat-unit=pass seat-vm=pass host-core=pass lint=pass`,
`checks_verified_src: seat-eval=run seat-unit=run seat-vm=run host-core=run lint=run`
— all five `run`, `touches_extra: 0`, `touches_disclosed: 0`, `exit_code: 0`,
`error_class: none`. Every one of those five I re-ran myself, from scratch.

## Touches and commit

`git diff 55753ba..HEAD --name-only`:

```
flake.nix
nixosModules/seatLane.nix
pkgs/seat/seat-run.py
tests/integration/seat-vm.nix
tests/seat/test_seat_run.py
```

Exactly the section's `touches` list, no file outside it, `docs/MAP.md`
correctly not regenerated, the plan file untouched, no board commit.

`git rev-list --count 55753ba..HEAD` → `1`. Subject byte-compared against the
section's `**commit subject:**` (both 281 bytes, `cmp` silent):
**byte-identical**. The two trailers follow a blank line in the WORKSPACE RULES
order:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sd1)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

The body states the why in full (the dsh bash tool spawning `bash` by name, the
driver job's git/nix, the follow-on submission, the read-only `/tmp`, the two
control sockets, `SEAT_JOB_ID`) but pastes neither the red nor the green —
MINOR-5.

## Findings

**MINOR-1 — the plan's dbus probe is a wrong fact; the seat corrected it and
disclosed it.** `docs/superpowers/plans/2026-09-06-seat-driver.md:204` specifies
`dbus=1` from `test -S /run/dbus/system_bus_socket`. systemd hides a socket path
by bind-mounting `/run/systemd/inaccessible/sock` over it, which is itself a
socket, so `test -S` is true whether or not the entry is present — the probe as
written could never go red. The seat switched to `test -r` (the inaccessible
node is mode 0000) and disclosed it in FACTORY-NOTES. Measured: with the entry
dropped the probe file holds `dbus=0` and the check fails (Mutants, #4).
Against the plan (`wrong-fact` shape), not the seat; no action owed on this
branch.

**MINOR-2 — the drop-in path deviates from the section's text and was not
disclosed.** `tests/integration/seat-vm.nix:401-404` writes
`/run/systemd/system/seat@probe.service.d/override.conf`; the section
(`…seat-driver.md:204`) names `/etc/systemd/system/seat@probe.service.d/override.conf`.
The `/run` form is the in-tree precedent (step 8, `:379`) and is equivalent for
a per-instance drop-in on a NixOS machine whose `/etc` is generated; the
FACTORY-NOTES line mentions only the dbus change.

**MINOR-3 — `seat-eval` identifies `seat-submit` by store-path suffix, not by
`name`/`pname`.** `flake.nix:1734`
`nixpkgs.lib.any (p: nixpkgs.lib.hasSuffix "-seat-submit" (toString p)) unit.path`
against the section's "a package whose `name`/`pname` is `seat-submit`"
(`…seat-driver.md:203`). Equivalent for the rendered config (mutant 2 dies), but
any store path ending `-seat-submit` would satisfy it.

**MINOR-4 — the `DSH_CACHE_ROOT` assertion throws before its own `assertMsg`
when the key is absent.** `flake.nix:1736-1737` evaluates
`unit.environment.DSH_CACHE_ROOT` directly, so mutant 3 fails with
`error: attribute 'DSH_CACHE_ROOT' missing` rather than the message the section
asks each assertion to carry. The mutant still dies; only the diagnostic is
lost. A `(unit.environment.DSH_CACHE_ROOT or "")` would restore it.

**MINOR-5 — the commit body pastes neither the red nor the green.**
`git log -1` at `9dfa151`: the body is one prose paragraph of rationale. The
WORKSPACE RULES require red-then-green in the seat's *reply* (which the run log
`~/factory/runs/sd1/SD5.log:950, :3405` carries), not in the commit, so this is
convention drift, not a rule breach.

**Noted, not charged.** `tests/integration/seat-vm.nix:135-138, 148-149` add
`nix.settings.experimental-features = [ "nix-command" "flakes" ]` and
`pkgs.git`/`pkgs.nix` to the VM node's `environment.systemPackages` so the
probe's `git`/`nix` resolve out of the VM's `/run/current-system/sw`. I checked
the fixture is faithful to the host rather than convenient:
`/run/current-system/sw/bin/{bash,git,nix}` all exist on live core, and
`/etc/nix/nix.conf:8` reads `experimental-features = nix-command flakes`. Both
edits are inside `touches`.

**Also noted.** `test_exports_seat_job_id` exercises the headless fixture only,
while interface 2 says "every mode"; the export sits above the mode branch
(`pkgs/seat/seat-run.py:81` vs the `if mode == "headless"` below it), so web
mode is covered by construction rather than by a test.

## Verdict

**APPROVED.** No MAJOR. The section's contract is met item by item, every named
mutant dies (8/8, plus 2/2 of mine), all three reds reproduce, and the five
acceptance checks are green under `--rebuild` in a fresh clone. The five MINORs
are recorded; MINOR-1 belongs to the plan's Tests row and should be carried into
the defect ledger as a corrected fact, not a rejection.
