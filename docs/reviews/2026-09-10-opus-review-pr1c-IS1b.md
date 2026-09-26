---
plan_defect: missing-case
mutants_total: 3
mutants_killed: 3
mutants_outside_named: 3
model: opus
---
# Opus gate — seat run pr1c, task IS1b — REJECTED

## Summary

Both of IS1's findings are closed, cleanly and measurably. Exit 3 is reserved
for the cap alone, the `_poll` ended-without-a-result path exits 4, `maxUnits =
0` is refused at eval, all four `acceptance` checks are green in a fresh clone
under `--rebuild`, red before green reproduces, and all three named mutants die
with the errors the commit body pastes. On the section's own terms this round
is correct.

It is rejected on something the section's terms do not reach. IS1's cap runs on
**every** submit path, including `--no-start`, and fails closed when `systemctl`
is unavailable. Inside a `seat@` unit `systemctl` is denied *by design* — the
seat-vm probe pins `systemctl=1` — and `factory-task:411-414` submits with
`--no-start --wait` exactly there. So the cap refuses the one path a drive seat
uses to dispatch work:

```
machine # [ 29.118134] probe.sh[1257]: seat-submit: cannot count seat units (systemctl list-units exited 1)
```

`checks.x86_64-linux.seat-vm` (`flake.nix:2312`) goes from green to a 900-second
hang and `error: Cannot build … vm-test-run-seat-behind-broker.drv`. This is not
a test detail: switched onto core, every task a driver seat submits would be
refused with exit 3.

The cause is in the plan, not in the seat's hands — IS1's Files line puts the
cap "before writing the spool marker (the `--no-start` path …)" and mandates
fail-closed on a non-zero `systemctl`, and no one had read SD3/SD6 against it.
`plan_defect: missing-case`. The implementer's contribution is smaller but real:
it edited `tests/integration/seat-vm.nix` and never ran `seat-vm`.

**REJECTED.**

## Diff against the section

Fresh clone of `task/IS1b` at `c38988a`, base `e0c2457` from `IS1b.result`.

```
$ git -C <clone> log --oneline -3
c38988a isolation: exit 3 reserved for the running-unit cap; the ended-without-a-result path exits 4, maxUnits=0 refused at eval (test: seat-unit, seat-eval, seat-assertion-negative, lint)
e0c2457 program: the 23 owed errata folded into the plan; increment 0 closed; wave 1 of increment 1 dispatched (test: lint)
4f06adc integrate HH4b into integ/hh1rf

$ git -C <clone> rev-list --count e0c2457..HEAD
1

$ git -C <clone> diff --stat e0c2457..HEAD
 docs/runbooks/seat.md          |  19 +++++++
 flake.nix                      |  40 ++++++++++++++
 nixosModules/seatLane.nix      |  21 ++++++++
 pkgs/seat/seat-submit.py       |  84 ++++++++++++++++++++++++++++-
 tests/integration/seat-vm.nix  |   5 +-
 tests/seat/test_seat_submit.py | 119 +++++++++++++++++++++++++++++++++++++++--
 6 files changed, 281 insertions(+), 7 deletions(-)
```

One commit, as Step 5 orders. IS1b is a fresh pass forked from main on top of
IS1's rejection, so the commit carries the whole cap — the option, the `/etc`
file, the count, the five pytest cases, the two `seat-eval` assertions and the
runbook — plus this round's exit-4 renumber and the `maxUnits = 0` negative pin.

**Touches.** A fix round's contract is the chain's union:

```
$ nix develop -c python3 pkgs/evidence/tasks.py touches docs/superpowers/plans/2026-09-09-program.md IS1b
nixosModules/seatLane.nix
pkgs/seat/seat-submit.py
tests/seat/test_seat_submit.py
flake.nix
docs/runbooks/seat.md
```

Five of the six changed files are those five. The sixth,
`tests/integration/seat-vm.nix`, is **outside the union** — disclosed in the
commit body under `Deviation:` and counted by the harness as
`touches_extra: 1 / touches_disclosed: 1`, which is why the result stayed
`status=done` (`factory-task:857-861` demotes only when
`touches_extra > touches_disclosed`). See MINOR-1: the edit itself is right and
required, the omission is the plan's. `docs/MAP.md` and `docs/OPERATIONS.md` are
correctly untouched:

```
$ git -C <clone> diff --name-only e0c2457..HEAD | grep -E 'MAP.md|OPERATIONS.md'
(neither touched)
```

`docs/MAP.md` is not owed — no check name was added or removed, and `lint`
(which runs `repomap.py --root . check`) is green below.

**The commit message.** Subject byte-identical to the section's
`**commit subject:**` line (`docs/superpowers/plans/2026-09-09-program.md:428`)
— both 180 bytes, `md5sum` `938c79e0265e80b04f62cdc08fc860f0` on each. `(test: …)`
equals the `acceptance` list. Both trailers, in policy order
(`docs/board/policies.md:30-36`):

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pr1c)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

`Generated-By` first, the model equal to `IS1b.result`'s `model:` line
(`deepseek/deepseek-v4-pro-0813`), the run equal to `pr1c`. Correct.

**The prior round's findings, both closed.**

> **major** `pkgs/seat/seat-submit.py:185` — Interface 1 of the task states
> "Exit 3 is the cap refusal … and nothing else exits 3 in `seat-submit`", but
> the pre-existing `_poll` "ended without a result" path still `return 3` …
> pinned by `tests/seat/test_seat_submit.py:440` `assert rc == 3`.

Closed. Every exit-3 site in the file is now a cap arm, and the `_poll` branch
is 4:

```
$ grep -n "return 3\|return 4" <clone>/pkgs/seat/seat-submit.py
191:                return 4
306:        return 3
309:        return 3
```

`191` is `_poll`'s ended-without-a-result branch; `306` is
`cannot count seat units (…)` and `309` is `<n> seat units running, cap <max>`
— the cap's two arms and nothing else. The pinning test was renamed and
re-asserted (`test_failed_unit_ends_the_wait_at_once_exit_4`, `assert rc == 4`),
and mutant **A** below proves that assertion can fail.

> **minor** `nixosModules/seatLane.nix:105-109` — the `maxUnits >= 1` eval
> assertion (Interface 3) is implemented but has no test … the refuse-zero-at-
> eval guard is never shown to fail.

Closed. `flake.nix:783-810` adds `seatMaxUnitsZeroSystem` (the seat lane with
`maxUnits = 0`) and `seat-assertion-negative` gains a third `tryEval` arm that
throws when that system builds. Mutant **B** below proves it fires.

**The section's Interfaces, each measured.**

*Interface 1 — exit 3 only for the cap; `_poll` exits 4; no other path exits 3.*
The `grep` above is the whole answer for the file. Nothing outside it consumes
the old code either — the section's own audit command, re-run in the clone:

```
$ grep -rn 'return 3\|rc == 3\|exit_code == 3\|== 3' tools pkgs tests docs/runbooks
pkgs/seat/seat-submit.py:306:        return 3
pkgs/seat/seat-submit.py:309:        return 3
tests/seat/test_seat_submit.py:951/967/977/989:    assert rc == 3
tools/factory/seat/factory-lib.sh: (its own returns; no seat-submit rc)
tests/seat/test_seat_run.py:129:    assert rc == 3   (seat-run passing a dsh returncode through)
pkgs/evidence/tasks.py:314,344:        return 3      (unrelated CLI)
```

The four `assert rc == 3` in `test_seat_submit.py` are the four cap refusals
(lines 951, 967, 977, 989); `test_seat_run.py:129` is `seat-run` forwarding a
faked `Popen` returncode, not a `seat-submit` exit code; no shell caller
branches on `seat-submit`'s status (`factory-task:580`'s `verify_rc -eq 3` comes
from `factory_verify_checks`). `tests/integration/seat-vm.nix` no longer appears
because this commit moved its step-8 pin to `assert rc == 4` — the deviation.

*Interface 2 — the four checks pass and the five IS1 cap cases stay green.*
The checks are in the table below; the five cases are present and inside the 57:

```
$ grep -n "^def test_cap" <clone>/tests/seat/test_seat_submit.py
939:def test_cap_refuses_at_max_counting_activating
955:def test_cap_accepts_below_max
963:def test_cap_zero_refuses_even_with_no_units
971:def test_cap_fails_closed_when_systemctl_exits_nonzero
981:def test_cap_fails_closed_when_systemctl_absent
```

*Interface 3 — `maxUnits = 0` refused at eval.* `seat-assertion-negative` is
green, meaning `builtins.tryEval` on the zero-cap system did **not** succeed;
mutant **B** shows the arm is live, not decorative. Interface 3's second half
(the `/etc` file is the only runtime source besides the test override) holds:
`_max_units_cap()` reads `SEAT_MAX_UNITS`, then `/etc/seat-lane/max-units`, then
`5`, and mutant **e** shows `seat-eval` catches the file's removal. See MINOR-2
for the one soft edge in that resolution order.

## Red before green

Reproduced in the clone, independently of the commit body, by reverting the cap
check (`sed -i '297,309d' <clone>/pkgs/seat/seat-submit.py`, the thirteen lines
between the `--brief` guard and the job-id block) and running the suite:

```
$ nix develop -c pytest tests/seat -q
>       assert rc == 3
E       assert 0 == 3
tests/seat/test_seat_submit.py:989: AssertionError
=========================== short test summary info ============================
FAILED tests/seat/test_seat_submit.py::test_cap_refuses_at_max_counting_activating
FAILED tests/seat/test_seat_submit.py::test_cap_zero_refuses_even_with_no_units
FAILED tests/seat/test_seat_submit.py::test_cap_fails_closed_when_systemctl_exits_nonzero
FAILED tests/seat/test_seat_submit.py::test_cap_fails_closed_when_systemctl_absent
4 failed, 53 passed in 0.15s
```

Four cap cases fail with `assert 0 == 3`; `test_cap_accepts_below_max` — the
fixture row — passes, exactly as a fixture should. `git checkout` restored the
file and `git status --porcelain` is empty.

The commit body's red is `5 failed, 52 passed`, one more than mine, because the
seat reverted *both* halves at once (the cap **and** `_poll`'s `return 4`). The
fifth is mutant **A** below, which fails with the same `assert 3 == 4` the body
pastes. Together the two reproductions account for the body's five, so the
number is real and re-derived, not copied (G11).

The eval red is mutant **B**, whose message is byte-identical to the one the
commit body pastes.

## Checks

Fresh clone, `XDG_CACHE_HOME` under the gate scratch directory, `--rebuild` on
every acceptance check so none is a cached echo of the seat's own run.

| check | command | result |
|---|---|---|
| seat-unit | `nix build <clone>#checks.x86_64-linux.seat-unit -L --no-link --rebuild` | **PASS** — `57 passed in 0.11s`, `EXIT=0` |
| seat-eval | `… seat-eval -L --no-link --rebuild` | **PASS** — `checking outputs of '…-seat-eval-ok.drv'`, `EXIT=0` |
| seat-assertion-negative | `… seat-assertion-negative -L --no-link --rebuild` | **PASS** — `checking outputs of '…-seat-assertion-negative-ok.drv'`, `EXIT=0` |
| lint | `… lint -L --no-link --rebuild` | **PASS** — `EXIT=0`; every formatter and linter arm zero, `repomap check` silent |
| **seat-vm** (not in `acceptance`) | `nix build <clone>#checks.x86_64-linux.seat-vm -L --no-link` | **FAIL** — `RequestedAssertionFailed: action timed out after 900.76 seconds`, `error: Cannot build '/nix/store/…-vm-test-run-seat-behind-broker.drv'` |

All four `acceptance` names are green. `seat-vm` is a real check
(`flake.nix:2312`, `checks.x86_64-linux.seat-vm`), part of `nix flake check`,
and it is red — MAJOR-1.

The `57 passed` reproduces the commit body's count exactly, and it is 52 + 5:
the pre-existing suite plus the five cap cases.

## Mutants

Applied in the clone, run, reverted; the tree ends `git status --porcelain`
empty after each. `mutants_total: 3` counts the section's Step 4 set; three more
were applied outside it (IS1's A, C and D, which a fresh pass must still
satisfy).

| # | mutant | named? | outcome |
|---|---|---|---|
| **A** | `_poll` `return 4` → `return 3` (`seat-submit.py:191`) | yes (Step 4) | **KILLED** — `seat-unit` red: `FAILED …::test_failed_unit_ends_the_wait_at_once_exit_4 - assert 3 == 4`, `1 failed, 56 passed`, `EXIT=1`. Matches the commit body verbatim |
| **B** | delete the `maxUnits >= 1` assertion (`seatLane.nix:109-112`) | yes (Step 4) | **KILLED** — `seat-assertion-negative` red: `error: seat-assertion-negative: services.seat-lane.maxUnits = 0 DID NOT FAIL the build (the maxUnits >= 1 assertion is missing or wrong)`, `EXIT=1`. Matches the body verbatim |
| **C** | `if count >= cap:` → `if count > cap:` (`seat-submit.py:307`) | yes (Step 4) | **KILLED** — `seat-unit` red: `FAILED …::test_cap_refuses_at_max_counting_activating - assert 0 == 3` **and** `…::test_cap_zero_refuses_even_with_no_units`, `2 failed, 55 passed`, `EXIT=1`. The boundary is pinned twice over |
| d | `if proc.returncode != 0: return 0, None` — swallow a non-zero `systemctl` and call it zero units (IS1's mutant D) | OUTSIDE | **KILLED** — `seat-unit` red: `FAILED …::test_cap_fails_closed_when_systemctl_exits_nonzero - assert 0 == 3`, `1 failed, 56 passed`. Fail-closed is real |
| e | delete `environment.etc."seat-lane/max-units"` (IS1's mutant C) | OUTSIDE | **KILLED** — `seat-eval` red: `error: attribute '"seat-lane/max-units"' missing … at flake.nix:2278:41`, `EXIT=1`. The `/etc` mechanism is wired, not asserted into existence |
| f | `--state=active,activating` → `--state=active` (IS1's mutant A) | OUTSIDE | **KILLED** — `seat-unit` red: `FAILED …::test_cap_refuses_at_max_counting_activating - assert 0 == 3`, `1 failed, 56 passed`. Hand-started `activating` units are counted |

Six for six. IS1's cap arrives in this fresh pass with its whole mutation set
dead, which is the reason MAJOR-1 is *not* a "the tests are weak" finding: the
unit suite is strong on everything it was pointed at. It was pointed at a fake
`systemctl` on `PATH`, and the case that breaks is the one where there is a real
`systemctl` that is real-denied.

## Defects

**MAJOR-1 — the cap refuses the nested `--no-start` spool, and `seat-vm` is
red.** Plan defect: `missing-case` (with a contributory implementer defect).

`cmd_submit` counts units before *any* side effect, on every path including
`--no-start`, and fails closed when the count is unreadable
(`seat-submit.py:301-309`). Inside a `seat@` unit `systemctl` is denied by
design — the seat-vm probe asserts it:

```
$ sed -n '455,459p' <clone>/tests/integration/seat-vm.nix
"if systemctl start seat@nope >/dev/null 2>&1; then\n"
"  echo \"systemctl=0\" >> \"$out\"\n"
"else\n"
"  echo \"systemctl=1\" >> \"$out\"\n"
"fi\n"
$ grep -n "systemctl=1" <clone>/tests/integration/seat-vm.nix
519:    machine.succeed("grep -qx 'systemctl=1' /var/lib/seat/probe.out")
```

and the SD6 comment immediately below says why the spool exists: "the spool is
the one host-side actor the seat may reach — a `--no-start` submit writes the
marker … never a systemctl call from here."

So the cap's fail-closed arm fires on exactly that submit. Measured, in the VM:

```
$ nix build <clone>#checks.x86_64-linux.seat-vm -L --no-link
vm-test-run-seat-behind-broker> machine # [ 29.118134] probe.sh[1257]: seat-submit: cannot count seat units (systemctl list-units exited 1)
vm-test-run-seat-behind-broker> machine: waiting for success: test -f /var/lib/seat/jobs//result.txt
vm-test-run-seat-behind-broker> !!! RequestedAssertionFailed: action timed out after 900.76 seconds (timeout=900.0)
error: Cannot build '/nix/store/cvdavkjiy73p380daz8dk9mzsfb3fvkx-vm-test-run-seat-behind-broker.drv'.
```

The empty path `/var/lib/seat/jobs//result.txt` is the tell: `spooled_id` is the
empty string because `seat-submit` printed no id and exited 3. The refusal
message is emitted by code this commit introduces, into a probe step this diff
does not modify, and the base has no such call at all
(`grep -c list-units` on `e0c2457:pkgs/seat/seat-submit.py` → `0`; Assumption 3
says the same). The regression is this commit's. I also started `seat-vm` on a
base clone as a control; it was still building the base VM closure when this
gate closed, so the regression claim rests on the causal chain above — the
refusal message, the empty id, and a base with no `list-units` call — not on a
green control run.

This is not confined to a VM. `factory-task` takes the same path on the live
host whenever it runs inside a seat:

```
$ sed -n '408,414p' <clone>/tools/factory/seat/factory-task
  # SD3: inside a seat unit (SEAT_JOB_ID exported by seat-run) the submit is
  # spooled, not started -- the enclosing unit's spool starts the job and
  # --wait streams it. On the host the started call is unchanged.
  if [ -n "${SEAT_JOB_ID:-}" ]; then
    spool_flags=(--no-start --wait)
```

Switched onto core, a drive seat could no longer dispatch a single task: every
`factory-task` submit from inside the drive unit would die on
`cannot count seat units (systemctl list-units exited 1)`. That is the daily
workflow, refused by its own safety rail.

*Whose defect.* Principally the plan's, class `missing-case`. IS1's Files line
places the cap "before writing the spool marker (the `--no-start` path
documented at `:23-26` …) **or** starting a unit" and mandates "if `systemctl`
is absent from PATH or exits non-zero, refuse (fail closed) … exit 3". Those two
sentences, taken together and applied to SD3/SD6, are the bug; the seat
implemented them faithfully and its unit tests pin them (mutant d). The plan's
Assumption 3 measured `seat-submit` and `FACTORY_JOBS` but never looked at the
nested submit, and neither IS1's nor IS1b's Interfaces mention `--no-start`.

The implementer's share is smaller and real: it opened
`tests/integration/seat-vm.nix` to renumber step 8's `assert rc == 3`, declared
that deviation on the grounds that "interface 3 requires no consumer of the old
exit 3 to remain" — and then never ran the check it had just edited. Interface 3
was discharged as a `grep` for `== 3`; the behavioural consumer sat forty lines
below the line it changed. A single `nix build .#checks.x86_64-linux.seat-vm`
would have caught it.

*The shape of the fix* (for the orchestrator to type, not for this gate to
choose): the cap belongs where a unit is actually started. `--no-start` writes a
marker and starts nothing, so it should not be capped at all; `seat-spool.py` —
host-side, with a working `systemctl`, and today carrying no cap
(`grep -n 'list-units\|max-units' pkgs/seat/seat-spool.py` → empty) — is the
place that turns a marker into a running unit. A follow-on round that (a) skips
the count on the `--no-start` path, (b) enforces the cap in `seat-spool` before
it starts a unit, and (c) adds a `seat-vm` step asserting the nested spool still
returns an id, would satisfy decision 72a without breaking SD6. `seat-vm` must
be in that round's `acceptance`.

**MINOR-1 — `tests/integration/seat-vm.nix` is outside the chain's `touches`
union.** Plan defect, the same `missing-case`, non-gating on its own.

The edit is correct and was forced: step 8 pins the exit code of the very path
IS1b renumbers, and `seat-vm` is a check, so leaving it would have turned
`nix flake check` red for a different reason. But IS1b's Files list does not name
it, so the union does not contain it. The seat disclosed it
(`FACTORY-NOTES`, the commit body's `Deviation:` line, `touches_extra: 1 /
touches_disclosed: 1`), which is why `factory-task:857-861` did not demote the
result — the harness's demoting class is the *undisclosed* extra, and there is
none here. Recorded rather than gated: the owed correction is one line in the
plan (add `tests/integration/seat-vm.nix` to IS1b's — or its successor's —
`touches`), and it is the orchestrator's to make. Had MAJOR-1 not existed, this
alone would not have been worth a round.

**MINOR-2 — the cap resolution fails *open* on a malformed `/etc` file, and
tracebacks on a malformed env override.** Implementer defect, non-gating: no
Interface names it and no test covers it.

```python
    env = os.environ.get("SEAT_MAX_UNITS")
    if env is not None and env.strip() != "":
        return int(env)          # SEAT_MAX_UNITS=x -> uncaught ValueError
    ...
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return DEFAULT_MAX_UNITS     # a corrupt /etc file silently becomes 5
```

The module is built around failing closed — an unreadable *count* refuses — but
an unreadable *cap* quietly becomes 5. If the operator ever lands a cap of 2 and
the file is truncated or garbled, the effective cap silently rises. A
non-numeric `SEAT_MAX_UNITS` raises `ValueError` out of `cmd_submit` and prints
a traceback instead of a refusal. Both are cheap to close (refuse with the same
`cannot count seat units`-style message, exit 3) and belong in whatever round
fixes MAJOR-1, since it will be editing these lines anyway.

## Verdict

**REJECTED.**

The round did what its section asked. IS1's MAJOR is closed — exit 3 belongs to
the cap's two arms alone (`seat-submit.py:306,309`), `_poll` exits 4
(`:191`), and mutant A shows the new assertion can fail with the body's own
`assert 3 == 4`. IS1's minor is closed — `seatMaxUnitsZeroSystem` and a third
`tryEval` arm pin the `maxUnits >= 1` assertion, and mutant B fires with the
body's own message. All four `acceptance` checks are green in a fresh clone
under `--rebuild` (`57 passed`), red before green reproduces independently
(4 cap cases at `assert 0 == 3`, the fifth via mutant A), all three named
mutants die and three more from IS1's set die with them, one commit, subject
byte-identical at `md5 938c79e0265e80b04f62cdc08fc860f0`, both trailers in
policy order with the model from `IS1b.result`, `docs/MAP.md` and
`docs/OPERATIONS.md` correctly untouched.

It is rejected because the cap it re-lands refuses the nested `--no-start`
spool. `systemctl` is denied inside a `seat@` unit by design, the cap fails
closed on that, and `factory-task:411-414` submits with `--no-start --wait`
precisely there — so `checks.x86_64-linux.seat-vm` times out at 900 s on an
empty job id, with `seat-submit: cannot count seat units (systemctl list-units
exited 1)` in the unit's journal, and a switched host would refuse every task a
drive seat dispatches. The plan wrote that behaviour (`missing-case`: IS1's
Files line puts the cap on the `--no-start` path and mandates fail-closed on a
non-zero `systemctl`, against SD3/SD6), so the next round is a re-plan, not a
retry: move the cap to where a unit is started, leave the marker path alone, and
put `seat-vm` in `acceptance`.
