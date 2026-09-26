---
plan_defect: none
mutants_total: 15
mutants_killed: 14
mutants_outside_named: 3
---
# Opus gate — seat run sb11, task SB6c — APPROVED

## Summary

SB6c does exactly what its section asks and nothing else. The MAJOR that
rejected SB6b is closed at the source: `tests/seat/test_seat_submit.py:479` now
reads `rc, _, err = _submit(argv, monkeypatch)`, and
`nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` exits 0 in a fresh
clone of `task/SB6c` — I rebuilt it rather than trusting the cache. All six named
acceptance checks are green under `--rebuild`, including one full `seat-vm` run
(27.15 s of test script) in which the lifecycle block and step 8 both fire.

The two owed MINORs are closed with killing tests, not with prose. The new bats
case (g) `SB6b: --port=80 dies 2 (below 1024)` kills O2 (`-lt 1024` → `-lt 1`)
while case (c) stays green under the same mutant — which is precisely why (g)
had to exist. The two new pytest cases kill O3 and O4, the `_unit_state` guard
arms that the SB6b gate found unproven.

The delta over SB6b is three tests, one fixture extension and one character:
`git diff 8710456 HEAD -- pkgs nixosModules flake.nix tests/integration` is
**empty**, so nothing under the VM changed and M5/M6 needed no VM rebuild. I
re-ran SB6b's M1–M4 and M6–M10 in a scratch copy anyway; all nine still die on
the tests the SB6b section names. Fifteen mutants tried, fourteen killed; the one
survivor is an off-by-a-lot boundary nobody named (MINOR-2).

To the orchestrator's standing question: **the diff carries no
`docs/OPERATIONS.md` hunk at all this round.** Eight files, all inside the
section's `touches` list.

## Contract items

**Item 1 — the one-line fix, `lint` and `githooks/pre-commit` green, pasted from
the committed tree.** MET.

`tests/seat/test_seat_submit.py:479` (the carried `:469`, shifted by the ten
lines the fixture grew):

```
479:    rc, _, err = _submit(argv, monkeypatch)
```

in `test_inactive_success_without_result_keeps_polling`, matching the file's own
convention at `:232` and `:382`. `nix develop -c ruff check tests/seat pkgs/seat`
→ `All checks passed!`; `ruff format --check` → `4 files already formatted`.

`nix build .#checks.x86_64-linux.lint -L --no-link` → exit 0, then the same with
`--rebuild` → exit 0, last line:

```
lint> Finished in 22ms on 1 file with 96 rules using 24 threads.
```

(the body pastes `… in 20ms …`; the millisecond count is the only difference and
is not reproducible by construction).

`nix develop -c githooks/pre-commit` in a fresh clone → exit 1 on one line and
one line only:

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
```

`git add docs/OPERATIONS.md` and re-run → exit 0, last line byte-identical to the
body's paste:

```
render.test.mjs: all assertions passed
```

The regeneration is only the queue block dropping `SB6c` (and its plan filename)
now that this commit is in history — the prior gate's MINOR-3, exempt by rule and
unavoidable for any task the block derives. Nothing in the gate itself is red.
See MINOR-1.

**Item 2 — bats case (g), and mutant O2.** MET.
`tests/unit/70-dsh-openrouter.bats:1692-1702`, name byte-exact
(`SB6b: --port=80 dies 2 (below 1024)`), placed immediately after case (c) at
`:1681` and built the same way:

```
1692:@test "SB6b: --port=80 dies 2 (below 1024)" {
1693:  make_key
1694:  make_fake_node
1695:  DSH_OPENROUTER_NODE="$TMPHOME/bin/fake-node" \
1696:    DSH_OPENROUTER_TEST_SEAM=1 \
1697:    run dsh-openrouter -- --no-open --port=80
1698:  [ "$status" -eq 2 ]
1699:  [[ "$output" == *"--port must be an integer 1024-65535"* ]]
1700:  [ ! -e "$TMPHOME/node-argv.txt" ]
1701:}
```

Three assertions, one `[ … ]` per line, exactly the contracted set. O2 kills it
and leaves (c) green — proof below.

**Item 3 — pytest (f) and (f2), and mutants O3, O4.** MET.

The fixture gained the two contracted keys, `tests/seat/test_seat_submit.py:39-49`
(`answers`) and `:59-70` (`_no_systemctl._run`):

```
62:        if argv[:2] == ["systemctl", "show"]:
63:            if answers.get("show_raise"):
64:                raise OSError("systemctl missing")
65:            return subprocess.CompletedProcess(
66:                argv, answers.get("show_rc", 0), stdout=answers["show"]
67:            )
```

`show_rc` defaults to 0 in the dict, `show_raise` is absent by default — so the
fifteen carried tests see the same behaviour as before (they do: `17 passed`,
i.e. 15 + 2).

(f) `test_unit_state_unreadable_keeps_polling` at `:485-528`: `POLL_INTERVAL = 0`,
`answers["show"] = "ActiveState=failed\nResult=exit-code\n"`,
`answers["show_rc"] = 1`, the fake `time.sleep` raising `RuntimeError` on its 5th
call and writing `result.txt` / `stdout.txt` / `exit_code.txt` (`5`) on its 2nd,
then `assert rc == 5` and `assert "ended without a result" not in err`. Literal.

(f2) `test_unit_state_oserror_keeps_polling` at `:531-571`: identical but for
`answers["show_raise"] = True`. Literal.

**Item 4 — the body's pastes.** MET. The body carries the three mutant reds
(O2 → (g), O3 → (f), O4 → (f2)) with the runner's failing line, states each was
reverted, pastes `bats tests/unit/70-dsh-openrouter.bats` → 123 ok,
`pytest tests/seat -q` → 17 passed and item 1's two lint lines, and carries
SB6b's M1–M10 table with the note that the reviewer re-runs it. Every paste I
could re-run reproduces (see Mutants and Checks); the three mutant reds
reproduce **including their line numbers** (`bats … line 1698`,
`test_seat_submit.py:527`, `test_seat_submit.py:63`).

## Red before green

Scratch copy of the branch, base files (`328e471`) checked out against the
branch's tests, flake-visible via `git add -A`, everything under `nix develop -c`.

Base `pkgs/dsh-openrouter/dsh-openrouter.sh` + `default.nix`,
`bats tests/unit/70-dsh-openrouter.bats -f 'SB6b'` — all five red, (g) among them:

```
not ok 1 SB6b: --bind-namespace without --port dies 2 before socat
#   `[ "$status" -eq 2 ]' failed
not ok 2 SB6b: --port '43210,su=nobody' dies 2 before socat
#   `[ "$status" -eq 2 ]' failed
not ok 3 SB6b: --port=70000 dies 2 in plain web mode
#   `[ "$status" -eq 2 ]' failed
not ok 4 SB6b: --port=80 dies 2 (below 1024)
# (in test file tests/unit/70-dsh-openrouter.bats, line 1698)
#   `[ "$status" -eq 2 ]' failed
not ok 5 SB6b: the harness package exports one socat binary and none of its siblings
#   `[ ! -e "$bindir/socat1" ]' failed
```

Base `pkgs/seat/seat-submit.py`, `pytest tests/seat -q -k 'unit_state'` →
`2 passed`. That is correct and is what the section says: (f) and (f2) assert
that an unreadable unit state never ends the wait, and the base never reads the
unit state at all, so it passes them trivially. Their red is O3's and O4's,
delivered below — the same shape the SB6b section used for its case (e).

Green on the branch: `bats tests/unit/70-dsh-openrouter.bats` → `ok 123`;
`pytest tests/seat -q` → `17 passed in 0.05s`;
`shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` → exit 0.

## Mutants

Named by SB6c: 3 tried, 3 killed. Named by SB6b and re-run: 9 tried, 9 killed
(M5 not re-run — justified below). Outside the named set: 3 tried, 2 killed.
Totals: **15 tried, 14 killed, 3 outside the named set.**

| # | mutant | file | killed by | evidence |
| --- | --- | --- | --- | --- |
| O2 | `-lt 1024` → `-lt 1` | dsh-openrouter.sh:227 | (g) | `not ok 4 SB6b: --port=80 dies 2 (below 1024)` / `(in test file …, line 1698)` / `` `[ "$status" -eq 2 ]' failed `` — cases 1,2,3,5 all `ok`, so (c) really does survive it |
| O3 | delete `if proc.returncode != 0: return "unknown", ""` | seat-submit.py:61-62 | (f) | `> assert rc == 5` / `E assert 3 == 5` / `tests/seat/test_seat_submit.py:527` |
| O4 | delete the `except (OSError, ValueError)` arm | seat-submit.py:59-60 | (f2) | `E OSError: systemctl missing` / `tests/seat/test_seat_submit.py:63` (a bare deletion is a `SyntaxError`, so the arm was removed with its `try:` and the body dedented — the faithful form of "delete the arm") |
| M1 | delete the `bind_seen && -z web_port` if | dsh-openrouter.sh | (a) | `not ok 1 …` / `line 1657` / `` `[ "$status" -eq 2 ]' failed `` |
| M2 | delete the `'' \| *[!0-9]*` case arm | dsh-openrouter.sh | (b) | `not ok 2 …` / `line 1675` |
| M3 | delete the range if | dsh-openrouter.sh | (c), (g) | `not ok 3 …` / `line 1687`; `not ok 4 …` / `line 1698` |
| M4 | wrap the 2nd block in `[ "$bind_seen" -eq 1 ]` | dsh-openrouter.sh | (c), (g) | `not ok 3 …` / `line 1687`; `not ok 4 …` / `line 1698` |
| M6 | early-exit condition → `False` | seat-submit.py | (d) | `E RuntimeError: polled too long` / `:421` |
| M7 | `return 3` → `return 1` | seat-submit.py | (d) | `> assert rc == 3` / `E assert 1 == 3` / `:429` |
| M8 | drop `and result not in ("", "success")` | seat-submit.py | (e) | `> assert rc == 7` / `E assert 3 == 7` / `:481` |
| M9 | drop the journalctl write | seat-submit.py | (d) | `E AssertionError: assert 'line-1' in 'seat-submit: seat@… ended without a result: ActiveState=failed Result=exit-code\n'` / `:431` |
| M10 | `socatBin` → `socat` in the join | default.nix | (f-socat) | `not ok 5 …` / `line 1706` / `` `[ ! -e "$bindir/socat1" ]' failed `` |
| O5 | `-lt 1024` → `-lt 81` (outside) | dsh-openrouter.sh | **survives** | full `-f 'SB6b'` run: five `ok`, no `not ok` — see MINOR-2 |
| O6 | `except (OSError, ValueError)` → `except ValueError` (outside) | seat-submit.py | (f2) | `E OSError: systemctl missing` / `:63` — (f2) pins the `OSError` half specifically |
| O7 | the returncode arm returns `"failed", "exit-code"` instead of `"unknown", ""` (outside) | seat-submit.py | (f) | `> assert rc == 5` / `E assert 3 == 5` / `:527` — (f) pins the value, not just the presence of a branch |

**M5 (`KillMode = "process"`) was not re-run.** The section's carried code is
byte-identical to SB6b's: `git diff 8710456 HEAD -- pkgs nixosModules flake.nix
tests/integration` prints nothing. M5 costs one full `seat-vm` build and the
sb10 gate already killed it there (`seat-eval` assertion red plus
`wait_until_fails` timing out at 30.72 s). M6's pytest half is re-run above and
dies; its VM half is in the same carried-code class.

## Checks

Fresh clone of `task/SB6c` at `597262d`, every check built plain first (so
`--rebuild` has something to rebuild) and then again with `--rebuild`.

| check | result | note |
| --- | --- | --- |
| seat-vm | **pass** | `--rebuild`, exit 0; `test script finished in 27.15s`. The lifecycle block runs with the unit still up (`must succeed: pgrep -x socat` → `finished … in 0.02 seconds`), then the unit is brought down, `waiting for failure: pgrep -x socat` finishes in 0.02 s, and `must fail: ip netns exec egress-seat ss -ltn \| grep -q ':43201 '` passes. Step 8 fires for real: `seat@…service: Main process exited, code=exited, status=226/NAMESPACE`. |
| seat-eval | **pass** | `--rebuild`, exit 0 |
| seat-unit | **pass** | `--rebuild`: `17 passed in 0.04s` |
| unit | **pass** | `--rebuild`: `ok 594` |
| host-core | **pass** | `--rebuild`, exit 0 |
| **lint** | **pass** | `--rebuild`, exit 0 — the MAJOR of the previous round is closed |

`nix develop -c githooks/pre-commit` → exit 1 on the queue-block regeneration
alone; exit 0 after `git add docs/OPERATIONS.md`, last line `render.test.mjs: all
assertions passed` (MINOR-1). `nix develop -c ruff check tests/seat pkgs/seat` →
`All checks passed!`. `ruff format --check tests/seat pkgs/seat` → `4 files
already formatted`. `python3 pkgs/evidence/repomap.py --root . write` then
`git diff --exit-code docs/MAP.md` → exit 0, no change.
`python3 pkgs/evidence/tasks.py --root . check` → silent, exit 0.

The driver's own record (`/home/dalhaka/factory/runs/sb11/SB6c.result`) reads
`checks_verified: seat-vm=pass seat-eval=pass seat-unit=pass unit=pass
host-core=pass lint=pass` with `checks_verified_src:` every one `=run`,
`error_class: none`, `touches_extra: 0`, `touches_disclosed: 0`,
`FACTORY-COMMITS 1`. Confirmed, not assumed: my runs agree with all six, and this
time so does the seat's own `FACTORY-CHECKS` line.

## Touches and commit

Eight files in `git diff 328e471..HEAD --name-only`:

```
flake.nix
nixosModules/seatLane.nix
pkgs/dsh-openrouter/default.nix
pkgs/dsh-openrouter/dsh-openrouter.sh
pkgs/seat/seat-submit.py
tests/integration/seat-vm.nix
tests/seat/test_seat_submit.py
tests/unit/70-dsh-openrouter.bats
```

That is the section's `touches` list exactly — nothing outside it, and **no
`docs/OPERATIONS.md` hunk this round** (the SB6b commit carried one; this branch
was cut from `328e471`, whose queue block was still fresh at commit time). The
plan file is untouched; there is no board commit.

Exactly one commit, `597262d`. `cmp` of `git log -1 --format='%s'` against the
section's commit-subject string: identical, byte for byte. The body states the
why (the MAJOR it closes and its `plan_defect: implementer` classification),
gives item 1's one-character change, the three mutant reds with their runner
lines and "Reverted.", the four greens, and the carried M1–M10 table. Two
trailers after a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sb11)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

## Interfaces and error contracts

Every contract the SB6b/SB6c sections state now has a test that dies when the
code stops honouring it:

- `die 2 "--bind-namespace needs --port …"` — (a), mutant M1.
- `die 2 "--port must be an integer 1024-65535 …"`, three refusal paths:
  non-integer (b)/M2, above the upper bound (c)/M3, **below the lower bound
  (g)/O2** — new this round. The any-mode rule is pinned by M4.
- `_unit_state`'s docstring, "never an exception, never a false early exit":
  the `except (OSError, ValueError)` arm by (f2)/O4 (and O6), the
  `returncode != 0` arm by (f)/O3 (and O7) — both new this round. The happy path
  and the `inactive`/`success` non-exit are (d)/(e), M6–M9.
- exit 3 on a failed unit: (d)/M7 and VM step 8; exit 124 on timeout: the
  carried timeout test; exit 5/7 on a job's own code: (e), (f), (f2).
- `KillMode = "control-group"`: pinned by `seat-eval`, its effect proven by the
  `seat-vm` lifecycle block.
- one `socat` on the unit's PATH: the bats siblings case, mutant M10.

No stated contract is left without a test, and none is violated by the code.

## Findings

**MINOR-1 — `githooks/pre-commit` exits 1 in a fresh clone of the committed
tree, on the queue block alone.** `docs/OPERATIONS.md`, `<!-- tasks:begin -->`
block: the regeneration drops `SB6c` and
`2026-09-05-seat-behind-broker.md` from the queued list, because the task's own
commit is now in history:

```
-… CR4 PW1glm PW1kimi PW1pro SB6c SD1 SD4 SD5 SD8 (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-06-seat-driver.md)
+… CR4 PW1glm PW1kimi PW1pro SD1 SD4 SD5 SD8 (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-06-seat-driver.md)
```

`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. Every
other arm of the gate is green, and staging the block gives exit 0 with the body's
exact last line. This is the sb10 gate's MINOR-3, carried unchanged: exempt by the
orchestrator's rule and unavoidable for any task the block derives. Recorded so
the integrator expects one regeneration on merge.

**MINOR-2 — the `1024` boundary is pinned only loosely.**
`pkgs/dsh-openrouter/dsh-openrouter.sh:227`. Case (g) uses `--port=80`, so it
kills the named mutant O2 (`-lt 1`) and any bound at or below 80, but an
off-by-a-lot bound survives: O5 (`-lt 1024` → `-lt 81`) leaves the whole `SB6b`
filter green (five `ok`, no `not ok`). A case at `--port=1023` (dies) plus the
existing `--port 43210` acceptance would pin the boundary exactly. Section-level,
not the seat's: SB6c named `-lt 1` and (g) kills it. Not owed.

**MINOR-3 — the VM's `timeout=30` still raises the driver's deprecation
warning.** `tests/integration/seat-vm.nix:350`; my `seat-vm` log line 1142:

```
??? Warning (UserWarning): wait_until_fails(): passing a bare int/float as a duration is deprecated. Use datetime.timedelta instead.
```

The literal is the SB6b section's own text, carried unchanged (the code diff
against `8710456` is empty). Plan text, not the seat's choice; it does not fail
the check. The sb10 gate's MINOR-4, recorded again, not owed.

## Verdict

**APPROVED.** All four contract items are met literally: the one-character fix is
in place and `lint` is green under `--rebuild` (the MAJOR that rejected SB6b is
closed at its root, not papered over); (g), (f) and (f2) exist with the
contracted names, shapes and assertions; O2, O3 and O4 each die on the test named
for them, with the failing lines the body pastes; and the body's own pastes
reproduce. All six named acceptance checks pass under `--rebuild`, `seat-vm`
included and exercised. SB6b's nine cheap mutants were re-run and all nine still
die; M5 was skipped on the measured ground that the carried code is byte-identical
to `8710456`. Fourteen of fifteen mutants killed; the survivor is an unnamed
boundary refinement (MINOR-2). Eight files, all in `touches`; one commit; the
subject byte-identical; both trailers; no board commit; the plan file untouched.

`plan_defect: none`. The SB6c section named the defect, the fix, the two tests
and the three mutants, and the seat delivered each one — including the discipline
the last round failed at: it ran the checks after the final edit and reported what
they printed.
