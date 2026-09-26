---
reviewer: opus
majors: null
minors: null
mutants_killed: 17
---
# Opus gate — seat run sb2, task SB3b — APPROVED

Reviewed 2026-09-05 from a throwaway clone of `/home/dalhaka/factory/ws/sb2/SB3b`
(branch `task/SB3b`, head `6744cef0beb4`, base `5349582`). Plan section: `### SB3b
(code, S)` of `docs/superpowers/plans/2026-09-05-seat-behind-broker.md`, against
the round-1 rejection `docs/reviews/2026-09-05-opus-review-sb1-SB3.md`. Nothing
in either workspace was written; no unit was started; no `sudo`. Host is NixOS
26.05 (python 3.13).

## Summary

All three blocking findings of round 1 are fixed **and measured**, which is the
part that failed last time. F1: `factory-task` no longer merges the streams —
`2>"$submit_err"` keeps stderr out of `$submit_out`, the first stdout line is
matched against `^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$` before it is used, and a submit
that yields no valid id writes `status=failed` plus `seat: submit failed (no job
id)` instead of a bogus unit name; `seat-submit` flushes the id (`print(job_id,
flush=True)`). F2: the fake `seat-submit` now records `--dsh-home`, `--workspace`
and the `--brief` file's content, and all three are asserted — M12/M13/M14 die.
F3: the start/wait/stream/exit half is covered — `--no-start` asserts an empty
call list, a headless test seeds `result.txt`/`stdout.txt`/`exit_code.txt` and
asserts the streamed content and the propagated code for 0 and 3, `--timeout 1`
asserts exit 124 **and** the `systemctl stop seat@<id>` call, and a
`PermissionError` on the jobs dir is a clean exit 2. F5 (the orphaned timeout,
which the plan had left to SB5) is fixed here and disclosed in the commit body.

Of the 19 mutations I applied, **17 die**. Every one round 1 named — its 9 kills
plus all 5 survivors — dies now, as do the id-regex and stop-on-timeout
mutations. Two survive, both minor and both recorded below: the `stderr → task
log` tee (the third mutation this gate named; the behaviour is implemented but
unasserted — one line in test 25 fixes it) and the `flush=True` (unkillable by
in-process tests, and belt-and-braces once the streams are split).

Scope is exactly SB3b's `touches`; `flake.nix` untouched; one commit on base;
subject byte-identical; trailer present; stdlib only; no test can reach a real
`systemctl`. The one process defect is that the delivered tree fails the
pre-commit **lint gate** — the board's queue block went stale the moment the
commit entered `git log` and was not re-added — while the report claims that gate
exited 0. It is a `git add docs/OPERATIONS.md` at integration; I proved the amend
makes the gate green. Not blocking, but the orchestrator must do it.

## Checks

All run in the throwaway clone with `XDG_CACHE_HOME` under the session
scratchpad; tooling only via `nix develop -c`.

| check | how | result |
|---|---|---|
| `pytest tests/seat -q` | `nix develop -c pytest tests/seat -q` | **9 passed** (4 → 9). Still devShell-only, not in a flake check — by design: the plan forbids touching `flake.nix`, SB1 wires `seat-unit`. |
| `bats tests/unit/80-seat-driver.bats` | `nix develop -c bats …` | **28/28 ok** (24–27 are the new ones) |
| `unit` | `nix build .#checks.x86_64-linux.unit -L --no-link` | **exit 0** (161 tests) |
| `lint` | `nix build .#checks.x86_64-linux.lint -L --no-link` | **exit 0** |
| lint gate | `nix develop -c githooks/pre-commit` | **exit 1** — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. See Deviations; base `5349582` in a clean clone exits **0**, so this commit is the cause, and re-adding the regenerated file makes it exit **0** (I amended in a scratch branch and re-ran, then reset). |
| ruff | `ruff check` + `ruff format --check` on `pkgs/seat tests/seat` | **clean** |
| shellcheck | `shellcheck tools/factory/seat/factory-task` | **clean** |

**Scope.** `git diff --name-only 5349582..HEAD`: `docs/MAP.md`,
`pkgs/seat/{default.nix,seat-submit.py}`, `tests/seat/test_seat_submit.py`,
`tests/unit/80-seat-driver.bats`, `tools/factory/seat/{factory-task,README.md}` —
exactly SB3b's `touches` (which now lists `docs/MAP.md`), nothing more.

**Hard rules.** `git rev-list --count 5349582..task/SB3b` = **1**. Subject
`cmp`-identical to the section's literal. `Co-Authored-By: Claude Fable 5.1
<noreply@anthropic.com>` present and last, after `Generated-By:`. `flake.nix` not
in the diff. `seat-submit.py` imports only `argparse datetime json os secrets
shutil subprocess sys time` — stdlib.

**Safety.** No test can reach a real `systemctl`: the pytest autouse fixture
`_no_systemctl` monkeypatches `subprocess.run` on the module and the string
`systemctl` does not occur anywhere in `tests/unit/80-seat-driver.bats` (the bats
fakes are shell scripts that never invoke the real `seat-submit`). On this host
`command -v seat-submit` → **not found** (exit 1), so `factory-task` still takes
the direct `dsh-openrouter` path until SB1 installs the package. The `.result`
and `.log` writes stay under `$FACTORY_ROOT`, which every test points at
`BATS_TEST_TMPDIR`.

## Red before green

Reproduced by me, not taken on the implementer's word: I fetched
`task/SB3` from `/home/dalhaka/factory/ws/sb1/SB3` (read-only) and checked out
**SB3's** `factory-task` and `seat-submit.py` over SB3b's tests.

- **pytest** — `2 failed, 7 passed`:
  `test_timeout_exits_124_and_stops_the_unit` and
  `test_permission_error_on_jobs_dir_exits_2` (the latter dies on an uncaught
  `PermissionError`, exactly M9's old failure mode). Restored, `9 passed`.
- **bats** — `not ok 25` (id from stdout alone, not the stderr warning) and
  `not ok 26` (garbage first line → `status=failed` + `seat: submit failed (no
  job id)`). Restored, 28/28.
- Tests 24 and the two new pytest coverage tests
  (`test_no_start_never_calls_systemctl`,
  `test_headless_waits_streams_and_propagates_exit_code`) **pass against SB3**,
  correctly: they pin behaviour SB3 already had but never measured. Their
  load-bearing proof is the mutation table below (M3, M4, M12, M13, M14), not a
  red run.

## Mutation table

19 mutations, each applied → suite run → reverted (`git checkout HEAD --`, tree
verified clean after). **17 killed, 2 survived.**

| # | mutation | file | suite | outcome |
|---|---|---|---|---|
| M1 | job dir `0o700` → `0o755` (both `mode=` and `chmod`) | seat-submit.py | pytest | **killed** |
| M2 | `job.json` drops `"effort"` | seat-submit.py | pytest | **killed** |
| M5 | `--workspace` isdir guard → `if False:` | seat-submit.py | pytest | **killed** |
| M9 | `--brief` readability guard → `if False:` | seat-submit.py | pytest | **killed** (still via the `copyfile` `PermissionError`; see F3 below) |
| M10 | `token_hex(3)` → `(4)` | seat-submit.py | pytest | **killed** (4 tests) |
| M3 | `systemctl start` moved above the `--no-start` return | seat-submit.py | pytest | **killed** — `test_no_start_never_calls_systemctl` *(round-1 survivor)* |
| M4 | headless `return exit_code` → `return 0` | seat-submit.py | pytest | **killed** — `…propagates_exit_code[3]` *(round-1 survivor)* |
| N1 | `systemctl stop` on timeout removed | seat-submit.py | pytest | **killed** — `test_timeout_exits_124_and_stops_the_unit` |
| N2 | `except OSError` → `except ZeroDivisionError` (PermissionError escapes) | seat-submit.py | pytest | **killed** |
| N3 | `print(job_id, flush=True)` → `print(job_id)` | seat-submit.py | pytest | **SURVIVED** — 9 passed |
| M6 | `FACTORY_SEAT_UNIT` condition dropped | factory-task | bats | **killed** (`not ok 27`) |
| M7 | `--model "$model"` → a literal | factory-task | bats | **killed** |
| M11 | `--effort "$effort"` → a literal | factory-task | bats | **killed** |
| M8 | `seat: unit seat@%s` printf → `:` | factory-task | bats | **killed** (24 and 25) |
| M12 | `--dsh-home "$dsh_home"` → `/tmp/shared` | factory-task | bats | **killed** *(round-1 survivor — the P0 isolation is now measured)* |
| M13 | `--workspace "$ws"` → `/tmp` | factory-task | bats | **killed** *(round-1 survivor)* |
| M14 | brief content → `EMPTY` | factory-task | bats | **killed** *(round-1 survivor)* |
| N4 | id regex test → `if true; then` | factory-task | bats | **killed** (`not ok 26`) |
| N5 | `tee -a -- "$log" <"$submit_err"` removed | factory-task | bats | **SURVIVED** |

## Findings

**F1 (minor, not blocking) — `seat-submit`'s stderr reaching the task log is
unmeasured.** N5 survives: delete the `tee -a -- "$log" <"$submit_err" >/dev/null`
line and the whole suite stays green, so a regression would silently drop
`seat-submit`'s own error text (`timed out waiting for …`, `--workspace … is not
a directory`) from the operator's `.log`. This is the third of the three
mutations this gate named, and the same *shape* as round 1's F2 — a behaviour the
code comment claims and nothing holds. It is not blocking because the failure it
would cause is diagnostic, not corrupting: the `.result` still records `seat:
submit failed (no job id)` / `status=failed`, and `factory_log` still writes
`seat-submit produced no valid job id on stdout` into the same log. The fix is
one line in test 25, whose fake **already** emits the stderr warning:

```
run cat "$root/runs/r1/K1.log"
[[ "$output" == *"seat-submit: warning: something about the job"* ]]
```

Fold it into SB5 or whichever task next touches this file; it does not warrant a
round.

**F2 (minor) — `print(job_id, flush=True)` is unkillable by the current suite.**
N3 survives because every pytest drives `cmd_submit` in-process against a
`StringIO`, where buffering does not exist, and the bats fakes are shell scripts.
The flush is genuinely load-bearing only for a caller that merges the streams,
and `factory-task` no longer does — so it is belt-and-braces behind the real fix
(separate streams + the regex, both measured). Pinning it needs a subprocess test
(`seat-submit` run under a pipe with a stderr write before the id); worth it only
if SB1's `seat-unit` check ever runs the script as a process.

**F3 (informational) — round 1's F4 is improved but not fully separated.**
`test_unreadable_brief_exits_2` now asserts the stderr message (`--brief {path}`
and `not readable`) alongside `rc == 2`, so a version that returned 2 silently
would fail. M9 still kills via the uncaught `PermissionError` from
`shutil.copyfile` rather than the code assertion, which is inherent: removing the
guard removes the only route to a clean 2. Acceptable.

**F4 (informational) — the stderr is appended after the run, not "as it
arrives".** The plan's Step 3 asks that `factory-task` "streams `seat-submit`'s
stderr to the task log as it arrives (so the operator sees the id early)"; the
implementation collects it in `$submit_err` and tees it into `$log` once the
submit returns. The stated *purpose* is met by other means and better: stdout is
tee'd into `$log` live, and `seat-submit` flushes the id before it does anything
slow, so the unit name is in the log within a second of submission and the
operator can `systemctl status seat@<id>` for the whole run. Only the failure
text is late, and it arrives at the same moment the run ends. Conformant in
substance; noted because the letter differs.

**F5 (informational) — `submit_failed` overrides a real `FACTORY-RESULT`.** When
the id does not validate, `factory-task` synthesizes `status=failed` even if the
stream also carried a well-formed `FACTORY-RESULT`. Test 26 pins exactly this. It
is the right call for the seat path (no id means no job ran), but it is a
behaviour difference from the `-z "$result_line"` branch worth remembering if the
web mode ever prints its id differently.

**F6 (informational) — two `OSError` sites remain outside the guard.** The
`try/except OSError` covers `makedirs`/`chmod` only; `open(job.json)` and
`shutil.copyfile` can still raise a traceback (disk full, or a TOCTOU between
`os.access` and the copy). Low value, no test asked for it, and the process exits
non-zero either way.

## Deviations

- **The delivered tree fails the pre-commit lint gate.** `nix develop -c
  githooks/pre-commit` on `task/SB3b` exits **1**: `tasks: docs/OPERATIONS.md
  queue block was stale and has been regenerated — git add docs/OPERATIONS.md and
  commit again`. Cause, proved: `evidence tasks` reads landed subjects from `git
  log` on HEAD, so the moment this commit exists SB3b counts as landed and drops
  out of the **Queued** line. It is specific to SB3b (SB3's own commit could not
  trigger it — SB3 was already in state `rejected`, never in the queue line). A
  clean clone at base `5349582` exits **0**, so the commit is the cause; I
  confirmed the remedy by staging the regenerated file and amending in a scratch
  branch — the gate then exits 0 and the tree is clean — before resetting back to
  `6744cef`. **Not blocking**, for three reasons: the acceptance checks the plan
  names (`unit`, `lint`) are both green; the gate's scope line permits
  `docs/OPERATIONS.md` "if regenerated"; and writing "SB3b landed" into the board
  of record from an ungated task branch is arguably the wrong artifact anyway —
  the board is regenerated on `main`. **Action for the orchestrator:** run the
  hook once after integrating and commit the regenerated block.
- **The report's `lint gate: exit 0` claim is false for the delivered tree.** It
  was presumably true at commit time (the hook runs before the commit object
  exists, so `git log` did not yet contain it) and the implementer did not re-run
  it afterwards. Recorded because this gate does not accept unverified claims,
  not because it changes the verdict.
- `docs/MAP.md` is inside `touches` this round and its two added lines
  (`pkgs/seat`, `tests/seat`) are the generator's output; the `lint` check is
  green with them.
- The commit body discloses the stop-on-timeout as new behaviour beyond SB3's
  plan text ("F5, now fixed here rather than deferred to SB5"). The plan's SB3b
  Step 1 asks for it explicitly. Conformant and disclosed.
- `tools/factory/seat/README.md`'s new "Seat unit (SB3)" section matches the
  implemented behaviour, including the id-shape check, the `submit failed (no job
  id)` record and the stop-on-timeout. No prose ahead of the code.
- `FACTORY-NOTES` was a one-line summary; I judged the diff, the mutations and
  the checks directly rather than the transcript's claims. Every claim I tested
  held except the lint gate above.
