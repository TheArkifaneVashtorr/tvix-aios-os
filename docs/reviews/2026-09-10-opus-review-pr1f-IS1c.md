---
plan_defect: underspecified
mutants_total: 4
mutants_killed: 4
mutants_outside_named: 2
model: opus
---
# Opus gate — seat run pr1f, task IS1c — APPROVED

## Summary

This round exists because IS1b would have refused every task a drive seat
dispatches, and it closes that hole where the section said to close it. The cap
now sits with the actor that starts a unit. `seat-submit --no-start` writes its
marker and returns 0 with `systemctl` absent from `PATH` entirely; the start
path still refuses at the cap and still fails closed when it cannot count;
`seat-spool` — root-side, able to both see units and start them — enforces the
cap before each start and, above it, writes `result.txt` carrying
`FACTORY-RESULT status=failed` with the cap and the observed count, removes the
marker and exits 0. A waiting caller returns in **2 s** against its own 600 s
timeout, and 1.04 s inside the VM, instead of the 900 s hang that rejected
IS1b.

The decisive fact is that `seat-vm` — the check the plan forgot to require last
time, and the one this whole round is about — is **green on the committed tree**
under `--rebuild` (45.55 s, exit 0), and mutant **A** (the count put back on the
`--no-start` path) turns it **red** with IS1b's exact signature:
`seat-submit: cannot count seat units (systemctl list-units exited 1)` followed
by `RequestedAssertionFailed: action timed out after 900.48 seconds`. A green
unit test alone is what let IS1b through; here the unit test and the VM both
move, and they move together.

All five `acceptance` checks pass, red before green reproduces independently at
the commit body's own `5 failed, 57 passed`, all four named mutants die, two
carried-over mutants from IS1 and IS1b die with them, the subject is
byte-identical to the section's, both trailers are right, and every one of the
eight changed files is inside the chain's `touches` union — the omission that
was IS1b's MINOR-1 is repaired.

Four minors are recorded, none gating. The sharpest is not in the shipped
behaviour but in the tests: under a regression of the `>=` boundary on the start
path, `seat-unit` does not go red — it **hangs**. Given that a hang is exactly
what masked the defect this round repairs, it is worth naming.

**APPROVED.**

## Diff against the section

Fresh clone of `task/IS1c` at `9c53798`, base `3b8987b` from `IS1c.result`.

```
$ git -C <clone> log --oneline -3
9c53798 isolation: the unit cap moves to the spool, the spooled submit never counts, malformed configuration refuses (test: seat-vm, seat-unit, seat-eval, seat-assertion-negative, lint)
3b8987b docs: type IS1c and file IS1b's gate — the cap would have refused every seat-dispatched task (test: lint)
6596b1e docs: type KN1b; G5 exempts the forced MAP.md regeneration too (test: lint)

$ git -C <clone> rev-list --count 3b8987b..9c53798
1

$ git -C <clone> diff --stat 3b8987b..9c53798
 docs/runbooks/seat.md          |  37 ++++++
 flake.nix                      |  40 +++++++
 nixosModules/seatLane.nix      |  21 ++++
 pkgs/seat/seat-spool.py        | 104 +++++++++++++++-
 pkgs/seat/seat-submit.py       | 105 +++++++++++++++-
 tests/integration/seat-vm.nix  |  53 ++++++++-
 tests/seat/test_seat_spool.py  |  43 ++++++-
 tests/seat/test_seat_submit.py | 264 ++++++++++++++++++++++++++++++++++++++++-
 8 files changed, 657 insertions(+), 10 deletions(-)
```

One commit, as Step 5 and G6 order. IS1c is a fresh pass forked from main on top
of IS1b's rejection, so the single commit carries IS1's cap, IS1b's exit-4
renumber and zero-cap pin, and this round's correction together — the fold G6
requires, not a stack of replayed commits.

**Touches.** The chain's union, and the eight changed files are exactly it:

```
$ nix develop -c python3 pkgs/evidence/tasks.py touches docs/superpowers/plans/2026-09-09-program.md IS1c
nixosModules/seatLane.nix
pkgs/seat/seat-submit.py
tests/seat/test_seat_submit.py
flake.nix
docs/runbooks/seat.md
pkgs/seat/seat-spool.py
tests/seat/test_seat_spool.py
tests/integration/seat-vm.nix
```

Eight names, eight changed files, no extra. `tests/integration/seat-vm.nix` —
IS1b's MINOR-1, disclosed there as a deviation because the union did not contain
it — is named in IS1c's `touches` this time, exactly as the section promised
("This file is in `touches` this time; IS1b's gate flagged its absence as
MINOR-1"). `IS1c.result` records `touches_extra: 0 / touches_disclosed: 0`.
`docs/MAP.md` and `docs/OPERATIONS.md` are correctly untouched: no check name
was added or removed (all five `acceptance` names already existed), and `lint`,
which runs `repomap.py --root . check`, is green below.

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` line (`docs/superpowers/plans/2026-09-09-program.md:747`):

```
$ md5sum /tmp/subj.commit /tmp/subj.plan
9751abac7a2968264e6e9d3a4951fbbf  /tmp/subj.commit
9751abac7a2968264e6e9d3a4951fbbf  /tmp/subj.plan
$ wc -c /tmp/subj.commit /tmp/subj.plan
178 /tmp/subj.commit
178 /tmp/subj.plan
$ cmp /tmp/subj.commit /tmp/subj.plan && echo BYTE-IDENTICAL
BYTE-IDENTICAL
```

`(test: seat-vm, seat-unit, seat-eval, seat-assertion-negative, lint)` equals the
section's `**acceptance:**` list, G4 satisfied. Both trailers, in policy order
(`docs/board/policies.md:30-36`, G3):

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pr1f)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `IS1c.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`), the run equal to `pr1f`. Correct. The body
states the design defect was the plan's, as Step 5 requires.

**IS1b's findings, all three closed.**

> **MAJOR-1** — the cap refuses the nested `--no-start` spool, and `seat-vm` is
> red.

Closed, and proved directly rather than only through the suite. The cap block
now sits *after* the `--no-start` branch returns (`seat-submit.py:381-396`,
following the `return 0` / `return _poll(...)` at `:374-376`), so the spooled
path cannot reach it. With `systemctl` absent from `PATH` **entirely**:

```
$ env -i PATH=<empty-dir> HOME=<tmp> python3 <clone>/pkgs/seat/seat-submit.py headless --no-start \
    --jobs-dir <tmp>/jobs --spool-dir <tmp>/spool --workspace <tmp>/ws --dsh-home <tmp>/dsh \
    --model deepseek/x --effort medium
EXIT=0
stdout (job id): 20260910-190414-489bce
stderr: []
spool marker: 20260910-190414-489bce
$ env -i PATH=<empty-dir> sh -c 'command -v systemctl || echo NONE'
(the PATH holds no systemctl at all)
```

Exit 0, the id on stdout, the marker written, nothing on stderr. The same thing
holds inside a real `seat@` unit, where `systemctl` is denied by design: the VM
probe still reports `systemctl=1` and still spools an id, and the spool starts
it:

```
$ nix build <clone>#checks.x86_64-linux.seat-vm -L --no-link --rebuild
machine: (finished: waiting for success: test "$(wc -l < /var/lib/seat/probe.out)" = 11, in 1.05 seconds)
machine # [   27.989236] seat-spool[1257]: seat-spool: started seat@20260910-190231-345eb3
machine: must succeed: grep -qx 'systemctl=1' /var/lib/seat/probe.out
```

> **MINOR-1** — `tests/integration/seat-vm.nix` is outside the chain's `touches`
> union.

Closed. It is the eighth name in the union above.

> **MINOR-2** — the cap resolution fails *open* on a malformed `/etc` file, and
> tracebacks on a malformed env override.

Closed, both halves, each measured on the start path:

```
$ SEAT_MAX_UNITS=x  seat-submit headless …
seat-submit: cannot read the seat cap (SEAT_MAX_UNITS='x' is not a number)      EXIT=3   (no traceback)
$ SEAT_MAX_UNITS=   seat-submit headless …
seat-submit: cannot read the seat cap (SEAT_MAX_UNITS is set but empty)         EXIT=3
$ (MAX_UNITS_FILE -> a file holding "abc")
seat-submit: cannot read the seat cap (…/max-units-bad holds 'abc', not a number)  EXIT=3
$ SEAT_MAX_UNITS=nope seat-spool --jobs-dir … --spool-dir … --owner dalhaka
seat-spool: cannot read the seat cap (SEAT_MAX_UNITS='nope' is not a number)    EXIT=1
```

Nothing falls back to 5, and the non-numeric env value raises no `ValueError`.
The spool reads the cap once before touching any marker and refuses the whole
run rather than starting at the default — fail closed, as item 4 asks.

**IS1's original findings have not regressed.** Exit 3 is still the cap's and
nothing else's, and `_poll`'s ended-without-a-result path is still 4:

```
$ git -C <clone> show 9c53798:pkgs/seat/seat-submit.py | grep -n 'return 3\|return 4'
208:                return 4
388:        return 3
392:        return 3
395:        return 3
```

`208` is `_poll`; `388`, `392`, `395` are the three cap arms (malformed cap,
unreadable count, at-or-above cap). No other exit-3 consumer survives anywhere:
`tests/seat/test_seat_run.py:129` is `seat-run` forwarding a faked `Popen`
returncode, `tests/lane/test_lane_run.py:408,436` is the unrelated lane, and
`tests/integration/seat-vm.nix:430` pins `assert rc == 4` for the `_poll` path.
No shell caller branches on `seat-submit`'s status at all.

**The section's four Interfaces, each measured.**

*Interface 1 — `--no-start` never invokes `systemctl`, never exits 3 for a count,
and with `systemctl` absent from `PATH` still writes its marker and returns 0.*
The direct run above, plus the VM probe, plus mutant A.

*Interface 2 — the start path exits 3 at or above the cap and when it cannot
count.* Both arms, directly:

```
$ SEAT_MAX_UNITS=2, a fake systemctl listing 2 units, no --no-start
20260910-190414-fede9f
seat-submit: 2 seat units running, cap 2                                        EXIT=3
$ PATH without systemctl, no --no-start
20260910-190414-e0b0b8
seat-submit: cannot count seat units ([Errno 2] No such file or directory: 'systemctl')   EXIT=3
```

Fail-closed on the start path is correct there — an unreadable `systemctl` on the
host is genuinely anomalous, which is the asymmetry the section draws.

*Interface 3 — the spool refuses above the cap with a result, not a hang.* Both
halves, end to end. A caller waiting on the job is started first, then the spool
runs with two units reported and the cap at 2:

```
$ seat-submit headless --no-start --wait … --timeout 600     (backgrounded; the waiting caller)
job id: 20260910-190438-4558e0 ; marker: 20260910-190438-4558e0

$ SEAT_MAX_UNITS=2 seat-spool --jobs-dir … --spool-dir … --owner dalhaka --systemctl <fake>
seat-spool: refused 20260910-190438-4558e0: 2 seat units running, cap 2
SPOOL EXIT=0
marker after: []
result.txt:
FACTORY-RESULT status=failed
seat-spool: 2 seat units running, cap 2
.spooled present? NO

waiter rc=0 after 2s (its --timeout was 600s)
```

`FACTORY-RESULT status=failed` naming the cap and the observed count, the marker
removed, the unit never started (`.spooled` absent), the spool exit 0 — and the
waiting caller back in **2 s**, one poll interval, against a 600 s timeout. That
is the "does not hang" half, measured on a real waiting process rather than
inferred from the unit test. The VM says the same at step 11b:

```
machine # [   39.851246] seat-spool[1582]: seat-spool: refused 20260910-190243-4494e3: 2 seat units running, cap 2
machine: (finished: waiting for success: grep -q 'FACTORY-RESULT status=failed' /var/lib/seat/jobs/20260910-190243-4494e3/result.txt, in 1.04 seconds)
```

*Interface 4 — a malformed cap exits 3 naming the value; nothing falls back to 5.*
The four runs under MINOR-2 above.

## Red before green

Reproduced in the clone independently of the commit body, and without trusting
any number in it, by restoring **IS1b's** implementation of the two programs
under **IS1c's** tests — the exact starting point Step 1 describes:

```
$ git -C <clone> fetch /home/dalhaka/factory/ws/pr1c/IS1b task/IS1b
fetched IS1b: c38988a
$ git -C <clone> checkout FETCH_HEAD -- pkgs/seat/seat-submit.py pkgs/seat/seat-spool.py
$ git -C <clone> diff --stat HEAD -- pkgs/seat
 pkgs/seat/seat-spool.py  | 104 +----------------------------------------------
 pkgs/seat/seat-submit.py |  87 +++++++++++++++------------------------
 2 files changed, 35 insertions(+), 156 deletions(-)

$ nix develop -c pytest tests/seat -q
FAILED tests/seat/test_seat_spool.py::test_refuses_above_cap_writes_failed_result
FAILED tests/seat/test_seat_submit.py::test_no_start_writes_marker_with_systemctl_absent_from_path
FAILED tests/seat/test_seat_submit.py::test_cap_non_numeric_env_exits_3 - Val...
FAILED tests/seat/test_seat_submit.py::test_cap_empty_env_exits_3 - assert 0 ...
FAILED tests/seat/test_seat_submit.py::test_cap_malformed_file_exits_3 - asse...
5 failed, 57 passed in 0.22s
```

`5 failed, 57 passed` — the commit body's count exactly, with the same five
names, including the `ValueError` on the non-numeric env value. `git checkout`
restored both files and `git status --porcelain` is empty.

The arithmetic reproduces too, which is what G11 asks for: IS1b's green suite was
57, this round adds four `seat-submit` rows (`:1027`, `:1098`, `:1111`, `:1123`)
and one `seat-spool` row, and the green suite is 62. 57 + 5 = 62, re-derived, not
copied.

The `seat-vm` half of Step 1's red is mutant **A** in the table below, which
reproduces IS1b's failure signature line for line.

## Checks

Fresh clone, `XDG_CACHE_HOME` under the gate scratch directory, `--rebuild` on
every acceptance check so none is a cached echo of the seat's own run.

| check | command | result |
|---|---|---|
| **seat-vm** | `nix build <clone>#checks.x86_64-linux.seat-vm -L --no-link --rebuild` | **PASS** — `test script finished in 45.55s`, `EXIT=0` |
| seat-unit | `… seat-unit -L --no-link --rebuild` | **PASS** — `62 passed in 0.13s`, `EXIT=0` |
| seat-eval | `… seat-eval -L --no-link --rebuild` | **PASS** — `checking outputs of '…-seat-eval-ok.drv'`, `EXIT=0` |
| seat-assertion-negative | `… seat-assertion-negative -L --no-link --rebuild` | **PASS** — `checking outputs of '…-seat-assertion-negative-ok.drv'`, `EXIT=0` |
| lint | `… lint -L --no-link --rebuild` | **PASS** — `EXIT=0`; every formatter and linter arm zero, `repomap check` silent |

All five `acceptance` names are green, `seat-vm` among them this time. The
`62 passed` reproduces the commit body's count exactly.

`seat-vm`'s green run walks the whole path this round is about: the probe inside
a `seat@` unit reports `systemctl=1` (denied, by design) and still spools an id;
`seat-spool` starts it; step 11b then holds both slots of a `maxUnits = 2` lane
with two web seats and shows the spool refusing a third with a result rather
than a hang, the marker consumed, `.spooled` absent and `seat@<id>` `inactive`.

## Mutants

Applied in the clone, run, reverted; `git status --porcelain` is empty after
each. `mutants_total: 4` counts the section's Step 4 set (A–D); two more were
applied outside it (`e` and `f`), because the section's Tests line claims IS1's
and IS1b's rows "carry over unchanged" and that claim deserves a mutant rather
than a reading. Note that `--rebuild` is meaningless on a mutated source — the
mutation yields a derivation that has never been built — so the mutant runs drop
it.

| # | mutant | named? | outcome |
|---|---|---|---|
| **A** | the count put back on the `--no-start` path (moved in front of the `if args.no_start:` branch, where IS1b had it) | yes (Step 4) | **KILLED, both halves.** `seat-unit` red: `FAILED …::test_no_start_writes_marker_with_systemctl_absent_from_path - assert 3 == 0`, `1 failed, 61 passed`, `EXIT=1`. **`seat-vm` red**: `probe.sh[1256]: seat-submit: cannot count seat units (systemctl list-units exited 1)`, then `!!! RequestedAssertionFailed: action timed out after 900.48 seconds (timeout=900.0)` and `error: Cannot build '/nix/store/6pandnk6yvjckhgclg4wlq7wm4vhpxw1-vm-test-run-seat-behind-broker.drv'` |
| **B** | the spool starts regardless of the cap (the `count >= cap` branch deleted) | yes (Step 4) | **KILLED** — `seat-unit` red: `FAILED tests/seat/test_seat_spool.py::test_refuses_above_cap_writes_failed_result - AssertionError: assert [['systemctl'...0000-abcdef']] == []`, `1 failed, 61 passed`, `EXIT=1`. The refused job was started |
| **C** | the spool drops the marker without writing a result (the `_write_failed_result` call removed from the cap branch) | yes (Step 4) | **KILLED** — `seat-unit` red: `FAILED …::test_refuses_above_cap_writes_failed_result - AssertionError: assert False` `+ where False = is_file()` on `…/result.txt`, `1 failed, 61 passed`, `EXIT=1`. This is the row that stands for the hang |
| **D** | the silent fallback to 5 on a malformed file restored | yes (Step 4) | **KILLED** — `seat-unit` red: `FAILED …::test_cap_malformed_file_exits_3 - assert 0 == 3`, `1 failed, 61 passed`, `EXIT=1` |
| e | `if count >= cap:` → `if count > cap:` on the start path (IS1's boundary) | OUTSIDE | **KILLED, but by hanging.** `seat-unit` never goes green — and it never goes red either: `pytest` ran 20 minutes before I killed it. `timeout 60` on `test_cap_refuses_at_max_counting_activating` alone: killed at 60 s; `timeout 300` on the suite with that row deselected: killed at 300 s, so at least a second row hangs too. See MINOR-2 |
| f | the `maxUnits >= 1` eval assertion deleted (IS1b's row) | OUTSIDE | **KILLED** — `seat-assertion-negative` red: `error: seat-assertion-negative: services.seat-lane.maxUnits = 0 DID NOT FAIL the build (the maxUnits >= 1 assertion is missing or wrong)` |

Six for six on the substance. Mutant **A** is the one that matters: it is the
mutant the section demanded precisely because "one of them alone is what let this
through the first time", and both halves move — the new pytest row *and*
`seat-vm`. The unit test would have caught it this round, but so would the VM,
independently, and that redundancy is the point of the round.

## Defects

None gating. Four minors, recorded.

**MINOR-1 — the refusal's readable reason never reaches the wave's record.**
Plan defect, class `underspecified`.

Item 3 of the corrected design justifies `result.txt` by its effect on the
caller: "a waiting `--wait` returns promptly **and the wave reports a failed key
with a readable reason** instead of a 900 s timeout." The first half holds and the
second half is only half true. `_poll` copies `stdout.txt` to its own stdout and
reads the exit code from `exit_code.txt`; it never reads `result.txt`
(`seat-submit.py:229-243`). The spool writes neither of the first two. So the
waiting caller returns **0** with nothing on stdout but the job id — measured
above (`waiter rc=0 after 2s`) — and `factory-task`, which greps its log for
`^FACTORY-RESULT status=(done|partial|failed)`, finds none and falls into its
synthesized-failure branch (`factory-task:715-729`):

```
result_line="FACTORY-RESULT status=failed exit_code=$exit_code"
notes_line="FACTORY-NOTES the seat produced no usable FACTORY-RESULT line; see $log"
```

The key *is* recorded failed, so the section's outcome survives; but the cap and
the observed count — the readable part — stay in the job dir and the journal,
and the board row gets the generic note. The choice of `result.txt` is right in
itself: `seat-run.py:180-183` documents it as the home of the FACTORY-* block,
so the spool wrote the reason into the file that owns it. What the section did
not check is that the reader it names never opens that file. The fix is small
and belongs to whoever next touches this: on the `--no-start --wait` path, have
`_poll` fall back to streaming `result.txt` when `stdout.txt` is absent. Not
gating — no Interface says otherwise, and Interface 3 is met to the letter.

**MINOR-2 — a regression of the `>=` boundary hangs `seat-unit` instead of
reddening it.** Implementer defect, non-gating.

Mutant `e` above. With `count > cap` on the start path,
`test_cap_refuses_at_max_counting_activating` (`test_seat_submit.py:939`) and
`test_cap_zero_refuses_even_with_no_units` (`:997`) stop refusing and fall
through into `systemctl start` and then `_poll(..., started=True)`. Those two
rows install a *real* fake `systemctl` on `PATH` and restore the real
`subprocess.run` (`_cap_env`), but unlike `test_cap_accepts_below_max` they never
seed a `result.txt` and never shorten `POLL_INTERVAL`, so `_poll` sits on its
default `--timeout` of 10800 s. Measured: pytest ran 20 minutes before I killed
it, and the single row alone survived a 60 s `timeout`.

The committed tree is correct and the four named mutants all die in 0.15 s, so
nothing is wrong today. But this is the same failure shape as the defect this
round repairs — a check that stalls instead of reporting — and it sits on the row
that pins the cap's boundary. A `--timeout 1` in `_cap_args`, or a seeded
`result.txt`, would make the boundary fail fast. Worth one line in whatever round
next opens this file.

**MINOR-3 — the module and eval messages still name `seat-submit` as the
enforcer.** Implementer defect, cosmetic.

`nixosModules/seatLane.nix:74` still reads "before **seat-submit** refuses a
launch … Written to `/etc/seat-lane/max-units` for **seat-submit** to read", and
`flake.nix:2272-2278`'s two `seat-eval` assertion messages say "the running-unit
cap seat-submit enforces" and "the file seat-submit reads". After this round the
spool is the primary enforcer on the path the factory actually uses, and it reads
the same file (`seat-spool.py:44-46`). The operator-facing document is correct —
`docs/runbooks/seat.md`'s new "The running-unit cap" section is genuinely good,
naming each actor and what a refusal looks like from each side — so this is drift
in the code's own prose, not in the runbook. One nit inside that otherwise
accurate section: it folds the malformed-cap refusal under the message
`cannot count seat units …`, where the program actually prints
`cannot read the seat cap (…)`; the paragraph two lines above states it
correctly.

**MINOR-4 — the closing pass: what this could break that the checks do not
cover.** Recorded as risks, not as faults.

Only two call sites reach `seat-submit` outside tests: `factory-task:405-427`
(`--no-start --wait` when `SEAT_JOB_ID` is set, else the started path) and
`tools/factory/seat/seat-drive.sh:109-116` (host-side, always the started path).
Both are correct under this design, and both were checked. The bats suites that
mention `seat-submit` (`80-seat-driver`, `86-rung-and-escalate`, `87-prior-attempt`,
`88-seat-drive`) all install a *fake* `seat-submit` on `PATH` and never exercise a
real exit code, so none of them can be perturbed by this change. Nothing else in
the tree branches on `seat-submit`'s status. Three things remain uncovered:

1. **The drive seat occupies one of its own slots.** A drive seat is itself a
   `seat@` unit, so the spool counts it. With `services.seat-lane.maxUnits`
   defaulting to 5 (`seatLane.nix:70-75`; `hosts/core/seat.nix` sets no override,
   and `seat-eval` pins the default at 5) and `FACTORY_JOBS` defaulting to 5
   (`factory-wave:138`), a drive seat dispatching a full wave has four slots, not
   five, and the fifth job meets the cap. No check covers that arithmetic — the VM
   sets `maxUnits = 2` to reach the refusal quickly, which is right for the test
   and says nothing about the live pairing. The operator may want `maxUnits` at
   `FACTORY_JOBS + 1`, or `FACTORY_JOBS` at `maxUnits - 1`; either way it is a
   configuration decision, not a code defect.
2. **A cap refusal is terminal, not deferred.** The spool removes the marker and
   writes `status=failed`; nothing re-queues. Under IS1's original intent the
   caller got exit 3 and could retry. This is the behaviour the section chose
   ("the wave reports a failed key"), so it is within contract — but it means a
   wave that brushes the cap loses a key rather than waiting for a slot.
3. **The cap can be overshot within one spool pass.** The count is taken per
   marker inside the loop (`seat-spool.py:229`), and `systemctl start --no-block`
   returns before the started unit is necessarily observable as `activating`. A
   single pass consuming several markers can therefore start more than `cap`.
   A narrow race, no test covers it, and no Interface names it.

## Verdict

**APPROVED.**

`seat-vm` — the check whose absence from IS1b's `acceptance` is the whole reason
this round exists — is green on the committed tree under `--rebuild`
(`test script finished in 45.55s`), and mutant **A** turns it red with IS1b's
exact signature (`cannot count seat units (systemctl list-units exited 1)`,
`RequestedAssertionFailed: action timed out after 900.48 seconds`). All five
`acceptance` checks pass (`seat-vm`, `seat-unit` at `62 passed`, `seat-eval`,
`seat-assertion-negative`, `lint`). Red before green reproduces independently at
`5 failed, 57 passed` with the body's own five names, and 57 + 5 = 62 re-derives.
All four named mutants die, and two carried-over mutants from IS1 and IS1b die
with them.

The behaviour is right where it matters and was proved directly, not only through
the suite: with `systemctl` absent from `PATH` entirely the spooled submit writes
its marker and returns 0; the start path still exits 3 at the cap and 3 when it
cannot count; above the cap the spool writes `FACTORY-RESULT status=failed`
naming the cap and the count, removes the marker, exits 0, and a real waiting
caller returns in 2 s against its own 600 s timeout; a malformed cap refuses on
both sides and never falls back to 5. Both of IS1b's minors are closed —
`tests/integration/seat-vm.nix` is inside the chain's `touches` union and the
malformed-configuration arms exist — and IS1's findings have not regressed: exit
3 belongs to the cap's three arms alone and `_poll` exits 4. One commit, subject
byte-identical at `md5 9751abac7a2968264e6e9d3a4951fbbf`, both trailers in policy
order with the model from `IS1c.result`, eight changed files against an
eight-name union, `docs/MAP.md` and `docs/OPERATIONS.md` correctly untouched.

The four minors are recorded rather than gated. MINOR-1 is the plan's
(`underspecified`): the section justified `result.txt` by an effect on the wave's
record that `_poll` does not deliver, so the failed key arrives with a generic
note instead of the cap and count. MINOR-2 is the one to act on soon — the
cap-boundary rows hang rather than fail under a regression, which is the very
shape of the problem this round repairs. Neither touches the shipped behaviour,
and neither is worth another round on its own.
