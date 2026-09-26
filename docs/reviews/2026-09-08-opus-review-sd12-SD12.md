---
plan_defect: implementer
plan_defect_secondary: process
mutants_total: 9
mutants_killed: 8
mutants_outside_named: 2
model: opus
---
# Opus gate — seat run sd12, task SD12 — REJECTED

## Summary

The boot fix is real and proven to the hilt. `PrivateTmp = true` lands on `seat@`,
`seat-eval` pins it in the stated idiom, and — the section's whole premise —
`seat-vm` genuinely reproduces the operator's production death once the fixture's
`ReadWritePaths = [ "/tmp" ]` override is dropped: I removed `PrivateTmp` from the
module in a scratch copy and the VM died with the exact `EROFS: read-only file
system, mkdtemp '/tmp/dsh-spill-XXXXXX'` raised by `@deepseek-ai/dsh-spill-local`'s
`privateRoot`, at the same `seat-submit headless` step, not a different failure
wearing the same name. With `PrivateTmp` present the same VM is green over the
SHIPPED unit — no remaining test-only escape re-widens the hardening anywhere in
the file, and the fixture paths moved to `/home/dalhaka/factory` are reachable
from inside the unit (the drive step's assertion reads a `settings.yaml` the unit
itself wrote there). `seat-drive` refuses a URL for a dead job and still prints
one for a live job, both pinned by discriminating rows that I killed with two
independent mutants each way. All five acceptance checks are green on
`--rebuild`, one commit, subject byte-identical, `touches` respected exactly.

One MAJOR blocks it, and it is in the row the orchestrator flagged. The
executable-bit row's failure path calls `fail`, which does not exist: bats-core
ships no `fail` builtin, no `bats_load_library`/`bats-support` is loaded anywhere
in this repo, and `fail` appears in no other test file. Running the chmod mutant
the section made this row's *sole* proof — the mutant the session harness denied
the seat, disclosed honestly — the row does go red, but as
`fail: command not found` with status 127, never naming the offending file.
Interface 5 states the row must name the file in the failure; it does not. The one
proof the section demanded is exactly the proof that exposes the defect.

The fix is one line. Everything else in this task is landing-quality.

## Contract items

Numbered as the section's Interfaces, taken literally.

1. **`seat@` gets its own `/tmp`** — MET. `nixosModules/seatLane.nix:231`
   `PrivateTmp = true;`, preceded (`:220–230`) by a comment naming the harness's
   spill store as the writer, the absolute `/tmp/dsh-spill-XXXXXX` prefix inside
   `@deepseek-ai/dsh-spill-local`'s `privateRoot` as the reason no environment
   variable can serve, the choice of a private instance over widening
   `ReadWritePaths` ("it keeps one job from reading another job's spill"), and the
   mount dying with the unit under `KillMode=control-group`. `DSH_CACHE_ROOT`
   stays `/var/lib/seat/cache` (`nixosModules/seatLane.nix:190`, unchanged).

2. **`seat-eval` pins it** — MET. `flake.nix:1753–1754`, immediately after the
   `KillMode` pin at `:1742–1744`:
   `assert nixpkgs.lib.assertMsg ((sc.PrivateTmp or false) == true)` with the
   message byte-identical to the section's text (`flake.nix:1754`). The
   `or false` / `== true` form is used, and the comment at `:1751–1752` says why.
   Verified live: the `or true` mutant passes eval, the shipped form does not
   (Mutants B, C).

3. **The VM asserts the shipped unit** — MET. `tests/integration/seat-vm.nix:180`
   now carries only `environment.OPENROUTER_BASE_URL`; the
   `serviceConfig.ReadWritePaths = [ "/tmp" ]` line and its justifying paragraph
   are gone (`:172–177` replaced them). `grep -n '/tmp' tests/integration/seat-vm.nix`
   returns three hits, all inside comments (`:173`, `:174`, `:175`) — no fixture
   path, no override. Fixtures moved to `/home/dalhaka/factory/{ws,dsh,drive-home}`
   and `/home/dalhaka/factory/brief` (`:234–241`, `:547–560`), created and
   `chown -R dalhaka` in the same steps; every `seat-submit` invocation follows
   (`:255`, `:388`, `:440`, `:566`, `:590`). No assertion weakened — see MINOR-3
   for the one proof that narrows, which the section's own fixture move requires
   and the seat discloses at `:243–250`. No other test-only escape: the only two
   remaining drop-ins are the SB6b negative probe, which *adds* a nonexistent
   `ReadWritePaths` entry to force 226/NAMESPACE and is removed again (`:378–395`),
   and the step-9 probe drop-in, which overrides `ExecStart` alone (`:404–408`).

4. **`seat-drive` never prints a URL for a dead job** — MET.
   `tools/factory/seat/seat-drive.sh:146` reads
   `exit_file="$jobs_dir/$job_id/exit_code.txt"`; `:161–167` prints
   `seat-drive: job %s failed (exit %s) — journalctl -u seat@%s` on stderr and
   `exit 1` without printing a URL; `:169` `cat -- "$url_file"` moved out of the
   wait loop so it runs only past the guard. `SEAT_DRIVE_JOBS_DIR` is the seam the
   two new rows point at (`tests/unit/88-seat-drive.bats:205`, `:227`). The string
   compare is correct against the real producer: `pkgs/seat/seat-run.py:148`
   writes `f"{proc.returncode}\n"`, and `$(cat)` strips the newline, so a live job
   compares equal to `0`. An empty or torn `exit_code.txt` fails closed (no URL).

5. **The executable bit is pinned** — VIOLATED in its failure contract; see
   MAJOR-1. The row exists (`tests/unit/88-seat-drive.bats:233–249`), covers both
   arms (`"$SEAT"/*.sh` at `:239–241`, extensionless at `:242–248`), uses
   `[ -x "$f" ]`, and the existing `"$REAL_BASH" "$SEAT/seat-drive.sh"` behaviour
   rows are untouched. But it does not name the file in the failure: the helper it
   calls does not exist.

## Red before green

* **Step 1(a) — `seat-eval`.** Scratch copy with `PrivateTmp` deleted from
  `nixosModules/seatLane.nix`, the flake assertion present:

  ```
  error:
         … in the condition of the assert statement
           at …/mut/flake.nix:1753:11:
           1753|           assert nixpkgs.lib.assertMsg ((sc.PrivateTmp or false) == true)
         error: seat-eval: seat@ must set PrivateTmp so the harness's /tmp spill store is writable (ProtectSystem=strict makes /tmp read-only)
  ```
  Restored (branch HEAD): `nix build .#checks.x86_64-linux.seat-eval -L --no-link --rebuild` → `seat-eval EXIT=0`.

* **Step 1(b) — `seat-vm`. THE PREMISE. Genuinely reproduced.** Same scratch copy
  (fixture change kept, `PrivateTmp` absent),
  `nix build .#checks.x86_64-linux.seat-vm -L --no-link` → exit 1:

  ```
  machine # [ 14.000932] seat-run[747]: Error: dsh: plugin tree failed to load: failed to apply loader entry include (cordis:include): failed to apply loader entry spill-local (@deepseek-ai/dsh-spill-local): EROFS: read-only file system, mkdtemp '/tmp/dsh-spill-XXXXXX'
  machine # [ 14.006041] seat-run[747]:     at privateRoot (file:///nix/store/ljwbhn6q…-dsh-0.1.2-rc.1/lib/node_modules/dsh-wrapper/node_modules/@deepseek-ai/dsh-spill-local/lib/index.js:35:18)
  machine # [ 14.056865] seat-run[747]:         code: 'EROFS',
  machine # [ 14.058436] seat-run[747]:         path: '/tmp/dsh-spill-XXXXXX'
  machine # [ 14.062452] systemd[1]: seat@20260909-042155-9fa6e2.service: Failed with result 'exit-code'.
  !!! RequestedAssertionFailed: command `su - dalhaka -c 'seat-submit headless --workspace /home/dalhaka/factory/ws …'` failed (exit code 1)
  ```
  Same error class, same module, same `privateRoot` frame, same absolute prefix as
  the operator's 21:27 failure — not a different failure wearing the name. The
  seat's FACTORY-NOTES claim for Step 5 is true. Restored (branch HEAD):
  `nix build .#checks.x86_64-linux.seat-vm -L --no-link --rebuild` → `EXIT=0`,
  `test script finished in 36.48s`.

* **Step 1(c) — the bats dead-job row.** Branch tests, base implementation
  (`git checkout 0c8eeec0 -- tools/factory/seat/seat-drive.sh`):

  ```
  not ok 9 seat-drive refuses to print a URL for a job whose exit_code.txt is non-zero
  # (in test file tests/unit/88-seat-drive.bats, line 216)
  #   `[ "$status" -eq 1 ]' failed
  ok 10 seat-drive still prints the URL when exit_code.txt is zero
  ```
  Restored: `nix develop -c bats tests/unit/88-seat-drive.bats` → 11/11 ok.

* **The executable-bit row.** No red is possible (40f0285 restored the bit on
  main) and the section says so; its proof is the mutant run — Mutant G below.

## Mutants

| # | mutant | named? | test that must kill it | outcome |
|---|---|---|---|---|
| A | `PrivateTmp` line deleted from `seatLane.nix` | yes (Step 1) | `seat-eval` + `seat-vm` | KILLED twice — assertion message above; `seat-vm` EROFS above |
| B | `PrivateTmp = false;` (literal) | yes (interface 1) | `seat-eval` | KILLED — `error: seat-eval: seat@ must set PrivateTmp so the harness's /tmp spill store is writable …`, `EXIT=1` |
| C | assertion rewritten `assert nixpkgs.lib.assertMsg (sc.PrivateTmp or true)`, option absent | yes (interface 2) | `seat-vm` only | seat-eval `EXIT=0` (survives eval, exactly as the section predicts); KILLED by `seat-vm` (same module as A) — which is why the shipped form is `(… or false) == true` |
| D | keep `serviceConfig.ReadWritePaths = [ "/tmp" ]` in the VM with `PrivateTmp` absent | yes (interface 3) | — | SURVIVES BY DESIGN: `seat-vm` `EXIT=0`, zero EROFS lines in 1471 lines of log. This is today's masking bug demonstrated; the discriminating fixture is the unpatched unit, and the shipped file has no override |
| E | print the URL whenever `url.txt` exists (= base `seat-drive.sh`) | yes (interface 4) | `unit` row 9 | KILLED — `not ok 9 … \`[ "$status" -eq 1 ]' failed` |
| F | always `exit 1` when `exit_code.txt` exists (`if true; then`) | yes (interface 4) | `unit` row 10 | KILLED — `not ok 10 … (line 230) \`[ "$status" -eq 0 ]' failed` |
| G | `chmod -x tools/factory/seat/seat-drive.sh` | yes (interface 5) | `unit` row 11 | KILLED, but wrongly — see MAJOR-1: `not ok 11 … (line 240) \`[ -x "$f" ] \|\| fail "not executable: $f"' failed with status 127` / `line 240: fail: command not found`. No file named |
| H | `chmod -x tools/factory/seat/factory-task` (the extensionless arm) | OUTSIDE | `unit` row 11 | KILLED — `not ok 11 … (line 247)`, same 127/`fail: command not found`. The second loop is load-bearing |
| I | drop `exit 1`, keep the stderr message | OUTSIDE | `unit` row 9 | KILLED — `not ok 9 … (line 216) \`[ "$status" -eq 1 ]' failed` |

mutants_total 9, mutants_killed 8, mutants_outside_named 2. (D is counted as
killed's complement only in the sense the section intends: its survival is the
demonstration the section asks for, not a hole.)

## Checks

All from the fresh clone at `705a5d0`, `XDG_CACHE_HOME` under the scratch dir.

| check | command | result |
|---|---|---|
| seat-eval | `nix build .#checks.x86_64-linux.seat-eval -L --no-link --rebuild` | `EXIT=0` |
| seat-vm | `nix build .#checks.x86_64-linux.seat-vm -L --no-link --rebuild` | `EXIT=0`, `test script finished in 36.48s` |
| host-core | `nix build .#checks.x86_64-linux.host-core -L --no-link --rebuild` | `EXIT=0` |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | `EXIT=0` |
| lint | `nix develop -c githooks/pre-commit` | `EXIT=1` — board queue block only, see MINOR-1; green (`EXIT=0`) once `docs/OPERATIONS.md` is staged, with every formatter/linter arm already passing on the first run |
| bats file | `nix develop -c bats tests/unit/88-seat-drive.bats` | 11/11 ok |
| shellcheck | `nix develop -c shellcheck tools/factory/seat/seat-drive.sh` | `EXIT=0` |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | `EXIT=0`, no change (no package/module/check/top-level entry added — correct) |
| graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, `EXIT=0` |

No python touched, so no `ruff` arm applies beyond the lint gate's own (green).

## Touches and commit

`git diff 0c8eeec0..HEAD --name-only`:

```
flake.nix
nixosModules/seatLane.nix
tests/integration/seat-vm.nix
tests/unit/88-seat-drive.bats
tools/factory/seat/seat-drive.sh
```

Exactly the section's `touches`, nothing outside, `docs/MAP.md` correctly not
regenerated, the plan file untouched, `docs/OPERATIONS.md` untouched (0 files).

Exactly one commit, `705a5d0`. Subject compared byte-for-byte against the
section's `**commit subject:**` (plan line 494) with `cmp`: identical. Body states
the why (the absolute prefix, why no env var can redirect it, why a private
instance over widening `ReadWritePaths`, why the VM's old fixture masked it, the
`url.txt`-before-outcome race, the 0644 regression). Both trailers present after a
blank line, in WORKSPACE RULES order: `Generated-By:` then `Co-Authored-By:`. The
body does not paste the red or the green output — MINOR-2.

## Findings

**MAJOR-1 — `tests/unit/88-seat-drive.bats:240,247`: the executable-bit row's
failure path calls an undefined command, so it never names the file interface 5
requires it to name.**

```
    [ -x "$f" ] || fail "not executable: $f"
```

`fail` is not a bats-core builtin; it ships in `bats-support`. This repo loads no
bats library — `grep -rn "bats_load_library|^load |BATS_LIB_PATH|bats-support|bats-assert" tests/ flake.nix githooks/`
returns nothing — and `fail` appears in no other test file
(`grep -rn '\bfail "' tests/unit/` → only these two lines). Running the section's
named mutant (`chmod -x tools/factory/seat/seat-drive.sh`), which the session
harness denied the seat and which the section makes this row's *only* proof:

```
not ok 11 every *.sh and extensionless script in the seat dir ships executable
# (in test file tests/unit/88-seat-drive.bats, line 240)
#   `[ -x "$f" ] || fail "not executable: $f"' failed with status 127
# …/tests/unit/88-seat-drive.bats: line 240: fail: command not found
```

Same for the extensionless arm at `:247` (mutant H). Interface 5: "…is executable
(`[ -x "$f" ]`), **naming the file in the failure**." The failure names a line
number and an unexpanded `$f`; with 17 files in that directory the operator is
told a loop, not a file. The row still turns red — it is not vacuous — but its
failure path is dead code, and it is dead precisely on the only path that ever
runs. `[ -x "$f" ] || { printf 'not executable: %s\n' "$f" >&2; return 1; }` (or
`echo`/`false`) is the whole fix.

I do not hold the missing chmod red against the seat: the denial is the session
harness's, it was disclosed clearly in FACTORY-NOTES, and the section itself says
this row's proof is a mutant run rather than a red. But the orchestrator's
question was whether the named-file assertion plus the green run is proof enough
for what this row needs, and the answer measured here is no — the proof the
section demanded is exactly the proof that exposes the defect.

**MINOR-1 — `docs/OPERATIONS.md` (not in the diff): the branch's lint gate exits
1, and `SD12.result` reports `lint=pass`.**
`nix develop -c githooks/pre-commit` at `705a5d0`:

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
```

Cause: `landed_subjects` (`pkgs/evidence/tasks.py:465`) reads commit subjects from
`git log`, so the task's own byte-identical subject makes SD12 "landed" on its
branch and drops it from the queue block. At the base commit the same gate is
`EXIT=0`, so this is the branch's own commit, not pre-existing drift. It is also
structural for every task branch in this repo, is anticipated verbatim by the
plan's Global Constraints, and is handled downstream: no landed task commit on
main carries `docs/OPERATIONS.md` (checked `c8c37ec`, `9ea240f`, `0eb7666`,
`81ae876`), and the orchestrator's gate-review commit carries the queue block
instead (`5d31181`: "…; the board's queue block"). Recorded, not gating. Every
other arm of the gate — treefmt, shellcheck, statix, deadnix, ruff, prettier,
eslint, the bats-and-chain lint, `render.test.mjs` — passed on the first run, and
the gate is `EXIT=0` once the block is staged.

**MINOR-2 — commit `705a5d0` body: states the why, pastes neither the red nor the
green.** Global Constraints: "Paste the red command and its output, then the
change, then the green check by name." The body paraphrases the red ("this EROFS
is reproduced by the check that was green over it and stays dead") and names the
checks only through the subject's `(test: …)`. The `.result`'s FACTORY-NOTES does
carry the Step 5 sentence the section requires, correctly and honestly.

**MINOR-3 — `tests/integration/seat-vm.nix:243–250`: SB4b's "-"-prefix proof
narrows from four absent home paths to three.** The VM now creates
`/home/dalhaka/factory` for its fixtures, so `Result == success` no longer proves
the "-" prefix tolerates an absent `~/factory` — only `~/nixos-agent-env`,
`~/flakes` and `~/.local/share/dsh-openrouter`. Interface 3 mandates exactly this
fixture move and says "no assertion is weakened"; strictly one proof is narrower.
The seat rewrote the SB4b comment to say so precisely, which is the right handling.
Recorded so the plan's defect ledger can see it, not gating.

**MINOR-4 — `tests/unit/88-seat-drive.bats`: no newline at end of file.**
Pre-existing at `0c8eeec0` (`… ]]\n}` with no trailing byte) and lint accepts it,
but the seat wrote the file's final byte and could have closed it. Noted only.

## Verdict

**REJECTED** on MAJOR-1.

The boot fix itself is correct, minimal and better-evidenced than most work that
passes this gate: the EROFS is reproduced by the check that was blind to it, no
test-only escape re-widens the shipped hardening anywhere, `PrivateTmp` gives the
job the writable `/tmp` the absolute spill prefix demands while `~/factory` stays
reachable, and the dead-job refusal is pinned in both directions. The switch #24
surface is sound. What blocks it is one line in one bats row whose failure path
does not run — the row the section could only prove by a mutant, and whose mutant
the harness denied the seat. A fix round replacing `fail "not executable: $f"`
with a `printf … >&2; return 1` on both loops, plus a pasted chmod mutant red,
closes it; nothing else in this diff needs to change.

`plan_defect: implementer` — the plan stated the failure contract ("naming the
file in the failure") plainly and the seat wrote a helper this repo does not have.
`plan_defect_secondary: process` — the session harness's house guard denied the
`chmod` mutant that the section designated as this row's sole proof, so the one
check that would have caught it could not be run by the implementer.
