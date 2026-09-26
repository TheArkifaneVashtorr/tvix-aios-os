# Opus gate — seat run sb1, task SB3 — REJECTED

Reviewed 2026-09-05 from a throwaway clone of `/home/dalhaka/factory/ws/sb1/SB3`
(branch `task/SB3`, head `c185db65d99f`, base `cefe8e7`). Plan section: `### SB3
(code, S)` of `docs/superpowers/plans/2026-09-05-seat-behind-broker.md`; spec
§Design items 3 and 7 of `docs/superpowers/specs/2026-09-05-seat-behind-broker-design.md`.
Nothing in the workspace was touched; no unit was started; no `sudo`.

## Summary

The shape is right and the acceptance checks are genuinely green: `seat-submit`
is stdlib-only, mirrors `pkgs/lane/lane-submit.py`'s `check=False` reasoning and
`pkgs/lane/lane-run.nix`'s wrapper verbatim in structure, and `factory-task`'s
new branch is a clean fork that leaves the direct-launch path byte-for-byte
intact. Red-before-green reproduces on both suites. Scope is exactly SB3's
`touches` plus two lint-forced generated docs; `flake.nix` is untouched as the
section demands; the subject is byte-identical and the trailer is present.

It is rejected on two things. First, a reproducible defect I demonstrated:
`factory-task` takes the job id as `head -n1` of `seat-submit`'s **merged**
stdout+stderr, and Python block-buffers stdout to a pipe while stderr is
unbuffered — so on every failure path of the new code (`--timeout` expiry, exit-2
on a bad workspace or unreadable brief) the stderr line arrives first and the
`.result` records `seat: unit seat@seat-submit: timed out waiting for …`. The id
is lost exactly where the operator needs it to find the unit. Second, five of
fourteen mutations survive, three of them on `factory-task`'s argument contract —
including `--dsh-home`, the P0 isolation the plan's Interfaces line requires be
preserved "exactly as before" and the commit message claims in prose. The whole
start/wait/stream/exit half of `seat-submit` has zero coverage.

Both are a short fix round, not a redesign: validate the id against the format
regex (or take it from a dedicated stream/file), and add four assertions.

## Checks

All run in the throwaway clone with `XDG_CACHE_HOME` under the session scratchpad;
tooling only via `nix develop -c`.

| check | how | result |
|---|---|---|
| `pytest tests/seat -q` | `nix develop -c pytest tests/seat -q` | **4 passed**. Not in any flake check yet **by design** — the plan forbids touching `flake.nix` (OG1b and SB1 own it) and assigns `seat-unit` to SB1. So this ran **only in the devShell**, not in CI. |
| `bats tests/unit/80-seat-driver.bats` | `nix develop -c bats …` | **26/26 ok** (24 and 25 are the new ones) |
| `unit` | `nix build .#checks.x86_64-linux.unit -L --no-link` | **exit 0** (re-run capturing the build's own status, not `tail`'s) |
| `lint` | `nix build .#checks.x86_64-linux.lint -L --no-link` | **exit 0** |
| lint gate | `nix develop -c githooks/pre-commit` | **exit 0**, tree left clean (no regeneration pending) |
| ruff | `ruff check` + `ruff format --check` on `pkgs/seat tests/seat` | **clean** |
| shellcheck | `shellcheck tools/factory/seat/factory-task` | **clean** |

**Scope.** `git show --stat HEAD`: `pkgs/seat/{seat-submit.py,default.nix}`,
`tests/seat/test_seat_submit.py`, `tools/factory/seat/{factory-task,README.md}`,
`tests/unit/80-seat-driver.bats` — all in `touches` — plus `docs/OPERATIONS.md`
(the `tasks:begin/end` generated block only; the hook regenerated it during the
commit, transcript line 1345) and `docs/MAP.md`. `docs/MAP.md` is outside the
allowed set on the letter, but I proved it is **forced**: reverting it to base
makes `lint` fail with `repomap: docs/MAP.md is stale`. It is the same class of
gate-regenerated file as the board block. Not counted as a deviation.

**Hard rules.** One commit on base (`git rev-list --count cefe8e7..task/SB3` = 1).
Subject byte-identical to the section's (`cmp` against the literal). Trailer
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` present.
`flake.nix` not touched. `seat-submit.py` imports only `argparse datetime json os
secrets shutil subprocess sys time` — stdlib only.

**Safety.** No test invokes a real `systemctl`. The pytest suite monkeypatches
`subprocess.run` on the module object (autouse fixture `_no_systemctl`); the bats
tests put a fake `seat-submit` on `PATH` so the real script never runs. Grepping
the transcript for a real `systemctl start` finds only quotations of the spec.
On **this host today** `command -v seat-submit` → not found (exit 1), so
`factory-task` keeps the direct `dsh-openrouter` path until SB1 installs the
package; I read the branch condition and confirmed it (`command -v seat-submit
>/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]`).

## Red before green

Both reproduced by me in the clone, not taken on the implementer's word.

- **`factory-task` at base + HEAD's bats** — restored `cefe8e7`'s `factory-task`
  and ran the file: `not ok 24 factory-task submits through seat-submit …`,
  failing at `[ ! -e "$dsh_called" ]` (the old path ran `dsh-openrouter`).
  Test 26 and the other 23 stayed green.
- **`seat-submit.py` absent** — moved the file aside: `pytest tests/seat` aborts
  at collection with `FileNotFoundError … pkgs/seat/seat-submit.py`, `1 error`.
- Note on test 25 (`FACTORY_SEAT_UNIT=0`): it **passes** at base, as expected —
  it pins the escape hatch rather than the new feature, and it is load-bearing
  only against HEAD. Mutation M6 below proves it is not vacuous there.

## Mutation table

Fourteen mutations, each applied → suite run → reverted. 9 killed, **5 survived**.

| # | mutation | file | suite | outcome |
|---|---|---|---|---|
| M1 | job dir `chmod 0o700` → `0o755` | seat-submit.py | pytest | **killed** (mode assertion) |
| M2 | `job.json` drops `"effort"` | seat-submit.py | pytest | **killed** (exact dict compare) |
| M3 | `systemctl start` moved above the `--no-start` return | seat-submit.py | pytest | **SURVIVED** — 4 passed |
| M4 | headless `return exit_code` → `return 0` | seat-submit.py | pytest | **SURVIVED** — 4 passed |
| M5 | `--workspace` isdir guard disabled | seat-submit.py | pytest | **killed** (`test_missing_workspace_exits_2`) |
| M9 | `--brief` readability guard disabled | seat-submit.py | pytest | **killed** — but by an uncaught `PermissionError` from `shutil.copyfile`, not by the `rc == 2` assertion |
| M10 | id suffix `token_hex(3)` → `(4)` | seat-submit.py | pytest | **killed** (`ID_RE`) |
| M6 | `FACTORY_SEAT_UNIT` condition dropped from the branch | factory-task | bats | **killed** (`not ok 25`) |
| M7 | `--model "$model"` → a literal | factory-task | bats | **killed** (`not ok 15`, `not ok 24`) |
| M11 | `--effort "$effort"` → a literal | factory-task | bats | **killed** (`not ok 24`) |
| M8 | `seat: unit seat@%s` line removed from `.result` | factory-task | bats | **killed** (`not ok 24`) |
| M12 | `--dsh-home "$dsh_home"` → `/tmp/shared` | factory-task | bats | **SURVIVED** — 24 and 25 ok |
| M13 | `--workspace "$ws"` → `/tmp` | factory-task | bats | **SURVIVED** — 24 and 25 ok |
| M14 | brief content replaced with `EMPTY` | factory-task | bats | **SURVIVED** — 24 and 25 ok |

M12/M13/M14 are one hole: the bats fake records `args=$*` but only two
substrings are ever asserted (`--model`, `--effort`). Three of the five arguments
`factory-task` hands the seat — the workspace, the isolated `DSH_HOME`, and the
brief itself — are unpinned. M3/M4 are the other hole: nothing exercises
`seat-submit` past the `--no-start` return, so the `systemctl start`, the
`result.txt` poll, the `stdout.txt` copy and the `exit_code.txt` parse — roughly
a third of the script and the whole mechanism the task's subject promises — are
untested. The `_no_systemctl` fixture returns its `calls` list, but no test takes
it as a parameter, so nothing ever asserts on it.

## Findings

**F1 (blocking) — the `seat:` line is corrupted on every failure path.**
`tools/factory/seat/factory-task`:

```
) 2>&1 | tee -a -- "$log" >"$submit_out"
...
seat_id=$(head -n1 -- "$submit_out" || true)
```

`2>&1` merges stderr into the same pipe. Python block-buffers stdout to a pipe
and flushes at exit; stderr is unbuffered and lands first. I reproduced it with a
five-line stand-in for `seat-submit`'s timeout path:

```
--- head -n1 (what becomes seat_id) ---
seat-submit: timed out waiting for /var/lib/seat/jobs/x/result.txt
```

`factory-task` then writes `seat: unit seat@seat-submit: timed out waiting for …`
into `$key.result`. Reachable on all three of the new code's failure exits
(`--timeout` expiry → rc 1; `--workspace` not a directory and `--brief`
unreadable → rc 2, where there is no id at all). I traced the control flow past
the extraction block: `set -e` is restored, `exit_code` non-zero does not exit
early, the synthesized-failure branch runs, and the `[ -n "$seat_id" ]` guard is
true — so the malformed line is written. This corrupts the artifact the
orchestrator reads, precisely in the case where the operator needs
`systemctl status seat@<id>`. Fix: validate against `^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$`
before assigning (empty otherwise), or keep stderr out of `$submit_out`.

**F2 (blocking) — the P0 `DSH_HOME` isolation is claimed but unmeasured.**
The plan's Interfaces line requires "the `DSH_HOME` isolation (P0) … apply
exactly as before"; the commit body asserts "passes … the isolated `DSH_HOME`
through". M12 proves no test holds it: hardcoding `--dsh-home /tmp/shared` leaves
both new bats tests green. Concurrent `factory-wave` groups sharing one dsh home
is the exact regression P0 exists to prevent. Add `[[ "$output" == *"--dsh-home
$root/runs/r1/K1.dsh-home"* ]]` (and the same for `--workspace` and the brief
file's content, killing M13/M14).

**F3 (blocking) — `seat-submit`'s start/wait/exit half is untested.**
M3 and M4 both survive. At minimum: a test that asserts the recorded `calls` are
empty under `--no-start` and equal `["systemctl","start",f"seat@{id}"]` without
it; and a headless test that pre-seeds `result.txt`, `stdout.txt` and
`exit_code.txt` in the job dir (with `POLL_INTERVAL` monkeypatched to 0) and
asserts the streamed stdout and the propagated exit code. SB4's VM will exercise
the real thing later, but that is a downstream gate, not coverage of this unit.

**F4 (minor) — M9 is killed by the wrong mechanism.** With the readability guard
removed, `test_unreadable_brief_exits_2` fails on an uncaught `PermissionError`
from `shutil.copyfile`, not on `rc == 2`. The test does hold the line, but it
would also "pass" against a version that crashes instead of returning 2. Assert
the stderr message alongside the code.

**F5 (minor, not blocking) — a timed-out job is orphaned.** On `--timeout`
expiry `seat-submit` returns 1 and leaves `seat@<id>` running; the old path's
`timeout -- "$timeout_s" dsh-openrouter` killed the process. The plan does not
ask for a `systemctl stop`, so this is spec-conformant — but it is a real change
in behaviour for a three-hour default and belongs in SB5's runbook if it is not
fixed here.

**F6 (informational) — the submit path no longer streams to the terminal.**
`tee -a -- "$log" >"$submit_out"` redirects what used to reach `factory-task`'s
stdout. Inherent to the job model (the unit's `stdout.txt` only arrives at the
end anyway), but it also means the job id is invisible in `$log` until the run
finishes, so an operator cannot find the unit to watch or stop it mid-run.
Printing the id via `factory_log` as soon as it is known would cost one line and
would also fix half of F1's ergonomics.

## Deviations

No **undisclosed** deviations found. `FACTORY-NOTES` was the non-disclosure
"one line.", so I judged the transcript directly (1409 lines) and the diff
against the section's `touches`.

- `docs/MAP.md` (outside `touches`). **Disclosed in the transcript**, lines
  1132–1173, with the reasoning shown; and I proved it is forced — reverting it
  fails `lint` with `repomap: docs/MAP.md is stale`. Gate-regenerated, same class
  as the board block. Not a deviation.
- `docs/OPERATIONS.md` (allowed): the `tasks:begin/end` block only, regenerated
  by the pre-commit hook during the commit (transcript line 1345). Allowed
  explicitly.
- `--timeout S` appears in the implemented CLI. The plan's synopsis line omits it
  but its prose specifies "`--timeout` default 10800 s", and the flag is in this
  gate's stated interface. Conformant.
- Everything the transcript claims about red (line 1400) I re-ran and confirmed
  independently; the claims hold.
- One process note in the implementer's favour: it explicitly checked, at
  transcript line 214 and again at 280, whether `factory-task` should do the
  `systemctl start` itself, and correctly kept it in `seat-submit` per the
  section. It also anticipated F1's premise at line 441 ("is the job id
  guaranteed to be the first line?") and reasoned only about stdout ordering,
  missing the merged stderr. The right question, the wrong answer.
