# Opus gate — seat run cr14, task CR3r — REJECTED

## Summary

CR3r is one commit (`a06d098`) on `task/CR3r`, base `3e2d720` (main, *without*
CR3b — CR3b never landed, so this round re-implements CR3b's work and CR9's
seven minors in one go). Subject byte-identical to the plan's, both trailers,
all seven touched files inside `touches`. Every named check is green:
shellcheck on the five scripts, 103/103 across `80-seat-driver.bats` +
`92-ritual.bats` + `90-session-start.bats`, `unit` (323 tests, also with
`--rebuild`), `lint`, and the `pre-commit` gate (whose only failure is the
known stale-queue-block artefact — re-run with the block staged it exits 0).

**Both CR9 MAJORs are genuinely closed, and the fixes are real, not cosmetic.**
The per-key pid preference is now pinned by four discriminating fixtures
(M-A/M-A2/M-A3 all die, 65/66/67/68/71); the marker's trap-before-write
ordering is pinned twice — structurally by a line-number assertion (test 38)
and behaviourally by a FIFO that blocks `printf` between the two lines
(test 39) — and swapping the lines leaves the marker stranded and fails both.
All seven minors are addressed. `--then` is in the hint, the mixed wave is
handled, a live per-key seat suppresses the hint, `group:` is `%q` and
round-trips a quote and a backslash byte-for-byte, the reaper works, `meta` and
`live` are `local` again, and a finished gate reads `gate done`. 24 of 24
mutations die, including cr9's whole table and CR5's eleven. Red-before-green
is strong: 27 tests red on the task's own base, 13 red on CR3b's tree.

**One MAJOR stops it, and it is behavioural, not coverage.** The new
`gate done` branch is placed *above* the stale-after cut, so it never reaches
it: every `<KEY>.review.log` that has a `<KEY>.review.md` and no
`.review.result` — which is *every review that has ever finished*, forever — is
listed in the in-flight table. Measured live: 23 extra lines aged 1801–1920
minutes (30–32 h), output 563 → **1518 bytes**, over the 1200-char
`SESSION_START_CAP_INFLIGHT`, so the SessionStart brief's In-flight part now
truncates mid-list and the newest runs (fd2, og5, rt8, s1, sb3–sb6 — including
the live seat sb6) and the stale-summary line are cut off. That contradicts the
function's own doc comment, contradicts the contract sentence "CR3b's behaviour
stands", and is the same failure class CR1 was rejected for. It is a two-line
fix (move the `gate_done` test below the staleness cut) plus one fixture.

## Rule behaviour

Fixtures: throwaway `FACTORY_ROOT` under
`…/scratchpad/fx*`, throwaway `git init` repos, `FACTORY_BIN_OVERRIDE` fakes
for `factory-task`, a fake `dsh-openrouter` on `PATH`, a copied seat directory
with a stub `factory-ws`, and a counting `setsid` shim. No real seat, no write
under `~/factory` at any point (the live probe is read-only and was verified so).

| row | fixture | expected | observed |
|---|---|---|---|
| **1a** old log (3 h) + dead `K.pid` + **alive** run pid | counted stale, not listed | `… and 1 stale logs older than 2h`, no `K` line, no `alive` |
| **1b** old log (3 h) + **alive** `K.pid` + dead run pid | `pid N alive` | `rb K - pid 386341 alive - log age 180m` |
| **1c** old `CR3.review.log` + dead `CR3.gate` + alive run pid | counted stale | `… and 1 stale logs older than 2h` |
| **1d** old `CR3.review.log` + alive `CR3.gate` + dead run pid | listed | `rd CR3.review - running - log age 180m` |
| **1e** (CR3b) fresh log + dead run pid | live, never DEAD | `rf K - running - log age 0m - then: gate; ff - relaunch: …` |
| **1f** (CR3b) fresh review log + alive gate + landed key | running, no DEAD, no relaunch | `rg CR3.review - running - log age 0m - then: gate CR3; ff` |
| **2a** structural: `factory-review` line numbers | trap < write | `68:trap 'rm -f -- "$gate_marker"' EXIT` / `69:printf '%s\n' "$$" >"$gate_marker"` |
| **2b** behavioural: `K1.gate` is a FIFO, `printf` blocks between the lines, SIGTERM | marker removed | `marker removed` |
| **2c** same, two lines swapped (M-H/M-B) | marker stranded | `MARKER LEFT BEHIND` |
| **3a** `run.meta` with `then:` + two groups, dead wave pid | hint reproduces argv incl. `--then` | `relaunch: factory-wave rh /home/dalhaka/nixos-agent-env K1 K2\ K3 --then "integrate K1; ff"` |
| **3b** dead wave pid + **alive** `K.pid` | no hint on any line | `ri K - pid 387423 alive - log age 0m` (no `relaunch:`) |
| **3c** mixed wave: `K1.result` done, `K2` without one | hint names K2's group only | `rj K2 - running - log age 0m - relaunch: factory-wave rj /tmp/repo K2` (no `K1`) |
| **3d** group `a"b\c d` through `%q` → eval-free unquote → `%q` | byte-identical | run.meta `group: a\"b\\c\ d`; unquoted bytes `a " b \ c   d` == original; hint `… /tmp/repo a\"b\\c\ d` |
| **4a** dead `Old.pid` + dead `OldG.gate` 3 h old, dead `Fresh.pid` now | old two reaped and counted, fresh kept | after: only `Fresh.pid`; `… and 2 stale pid files` |
| **4b** real `ps -o lstart= -p $$` → `date -d` | parses | `Sat Sep  5 21:41:09 2026` → `1788662469` (file mtime `1788662470`) |
| **4c** alive pid whose `ps` start is AFTER the pid file's mtime | deny "alive" | with the fake `ps`: not listed, `… and 1 stale logs older than 2h`. **Also with the REAL `ps`** — see MINOR-7 |
| **5a** `CR3.review.md` beside a **fresh** review log | `gate done` | `r1 CR3.review - gate done - log age 0m` |
| **5b** `CR3.review.md` beside a **3 h old** review log | should be counted stale | **`r1 CR3.review - gate done - log age 180m`** — **MAJOR-1** |
| **5c** `meta` / `live` local | yes | `local meta live stale_after stale_count wave_pid` (`ritual.sh:265`) |
| **6a** COMMITS 1 claimed, branch has 0 | failed, names it | `status=failed` / `FACTORY-NOTES claimed 1 commits, found 0`, rc 2 |
| **6b** `NOTES ok` + 1 real commit | failed | `FACTORY-NOTES a bare result was echoed, not a real completion`, rc 2 |
| **6c** template block early in the log, then a provider error, 0 commits | failed | `FACTORY-NOTES claimed 1 commits, found 0`, rc 2 |
| **6d** genuine block + 1 real commit | done | `status=done`, rc 0 |
| **6e** claimed 1, branch has 2 (the stray board commit) | plan says failed | `FACTORY-NOTES claimed 1 commits, found 2`, rc 2 — per contract, message names it; see MINOR-1 for the judgement |
| **6f** genuine `status=failed` + real notes, claimed 0, branch has 1 | notes preserved | **notes replaced** by `claimed 0 commits, found 1` — MINOR-1 |
| **7a** exit code under `set -m`, fake task sleeps 4 s, `status=failed` | rc 1 after ≥ 4 s | `K1 status=failed …` / `LAUNCHER SAW RC=1` / `ELAPSED=4s` |
| **7b** `kill -KILL -<launcher pgid>` mid-run | wave completes, writes `.result` | killed 21:43:06, `K1.result PRESENT at 21:43:09` |
| **7c** already a session leader (counting `setsid` shim) | 0 shim calls | `shim calls=0`, result present |
| **7c** not a session leader | exactly 1 call, no loop | `shim calls=1`: `-w -- …/factory-wave r2 <repo> K1` |
| **8** CR5 intact | tree renderer, `stop_hook_active`, caps | `92` 32/32 + `90` 28/28 green; CR3r's `ritual.sh` diff is confined to `inflight_stdout` and its two new helpers; `session-start.sh` untouched; CR5's mutations all still die (below) |
| **9** live probe, read-only | no DEAD-with-fresh-log lines; newest runs sensible; nothing reaped | no `DEAD`; cr12/cr14/cr15/sb6 all `running`; `~/factory/runs` had **no** `*.pid`/`*.gate` before or after, so the reaper deleted nothing. **But 23 dead `gate done` lines appear** — MAJOR-1 |
| **10** README | pid files, marker pid, `base:`/`group:`, `--then`, mixed wave, reaper, item 6, retired `setsid -f` | all present (`README.md:38-47, 73-79, 88-107, 120-126`) except the `<KEY>.pid` strand/reaper sentence and the recycled-pid guard — MINOR-6 |

Row 9, the live output (CR3r left, base right, same moment):

```
CR3r: 1518 bytes, 37 lines   base: 563 bytes, 14 lines
a1 N10FIX.review - gate done - log age 1883m      <- 23 lines like this,
a1 N10.review   - gate done - log age 1910m          ages 1801-1920 minutes
…                                                    (30-32 hours)
b3 F9.review    - gate done - log age 1801m
s1 S1.review    - gate done - log age 1920m
… and 186 stale logs older than 2h   (base: 209 — exactly the 23)
```

The reaper is sanctioned by the plan's item 4 ("reaped by the reader"), so a
`ritual.sh inflight` invocation is not strictly read-only. It deleted nothing
here because the real runs dir holds no `.pid`/`.gate` at all (they come only
from the new driver) — verified by `ls` before and after both probes.

## Checks

Run in the fresh clone `…/scratchpad/gate-cr14-CR3r` at `a06d098`.

| check | rc | wall |
|---|---|---|
| `nix develop -c shellcheck factory-wave factory-review factory-task factory-lib.sh tools/ritual.sh` | 0 | 2.1 s |
| `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats` | 0 (103/103) | 17.7 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 | 1.1 s (cached) |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0 (323/323) | 45.1 s |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 | 3.9 s |
| `nix develop -c githooks/pre-commit` | **1** → 0 after `git add docs/OPERATIONS.md` | 3.0 s |

The `pre-commit` failure is the known landed-task artefact: its only output is
`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`, and
the regenerated diff is exactly `… B1 CR2b CR3r PW1glm …` → `… B1 CR2b PW1glm …`.
Re-run with the block staged: `All checks passed!`,
`render.test.mjs: all assertions passed`, rc 0. Not a defect.

Inside the `unit` derivation, tests 172 and 173 (`setsid -w keeps the wave's
exit code`, `the wave survives … SIGKILLed`) **skip** — `no real setsid/ps in
this sandbox`. They run in the devShell (green) and I reproduced both by hand
(rows 7a/7b). The new FIFO kill test (179) does *not* skip; it runs inside the
derivation.

Commit convention: exactly 1 commit; subject byte-identical to the plan's
(byte-compare `IDENTICAL`); `Generated-By:` and
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` both present, in
order; the seven changed files are exactly the plan's `touches`.

## Red before green

**Against CR3b's tree** (`git -C /home/dalhaka/factory/ws/cr9/CR3b show
task/CR3b:<path>` over the four driver/reader files — `factory-review` is
byte-identical in both, so only three files change — CR3r's tests kept),
`bats tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats`: **13 red**.

```
not ok 29 factory-wave writes run.meta recording identity, base SHA, quoted groups, pid and --then before dispatch
not ok 30 factory-wave writes one quoted group: line per wave group, so parallel and a chain differ
not ok 40 factory-wave writes group: with %q, round-tripping a quote and a backslash
not ok 41 factory-task demotes status=done when the FACTORY-COMMITS claim does not match the branch
not ok 42 factory-task never records status=done for a run with no commit
not ok 43 factory-task rejects a bare-ok result as a template echo, not a completion
not ok 58 inflight reports a dead wave as live-by-rule with a relaunch hint that reproduces the argv
not ok 69 inflight's relaunch hint reproduces the original argv including --then
not ok 70 inflight's relaunch hint for a mixed wave lists only the missing key's group
not ok 71 inflight's relaunch hint never appears beside a live per-key pid
not ok 73 inflight reaps stranded pid and gate files older than stale-after, naming them in the summary
not ok 74 inflight denies alive for a recycled pid (process younger than the pid file)
not ok 75 inflight lists a finished gate as gate done once its review.md exists
```

Tests 38/39 (marker ordering) and 65–68 (per-key pid discriminators) are green
on CR3b, which is exactly right: CR9 found those behaviours already correct and
only their *coverage* missing. So the new fixtures are honest additions, not
re-proofs.

**Against the task's own base** (`3e2d720`, main): **27 red**, including 31,
33–39, 59, 60, 65–68, 72 — i.e. every new behaviour in the diff.

Restored (`git restore tools/`, tree clean): 103/103 green.

## Mutation table

Applied to the clone, `git diff --stat -- tools/` asserted non-empty before
each run, `bats tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats` under
`timeout`, `git restore tools/` after. Test numbers are that combined run
(1–43 driver, 44–75 ritual).

**The plan's table — 14 of 14 die.**

| # | mutation | site | died? | failing tests |
|---|---|---|---|---|
| M-A | `pid=$wave_pid` unconditionally | ritual.sh:344-347 | yes | 65, 66, 67, 68, 71 |
| M-A2 | `<KEY>.gate` arm never read (`elif false`) | ritual.sh:331 | yes | 67, 68 |
| M-A3 | `<KEY>.pid` arm never read (`if false`) | ritual.sh:337 | yes | 65, 66, 71 |
| M-B | trap and marker write swapped | factory-review:68-69 | yes | 38, 39 |
| M-C | `--then` dropped from the hint | ritual.sh:393 | yes | 58, 69 |
| M-D | hint printed regardless of a live per-key seat (`if true`) | ritual.sh:377 | yes | 71 |
| M-E | `group: %q` → `%s` | factory-wave:122 | yes | 29, 30, 40 |
| M-F | reaper age check removed (reap everything) | ritual.sh:286 | yes | 65, 67, 73 |
| M-F2 | reaper glob emptied (no reaper) | ritual.sh:279 | yes | 73 |
| M-G | recycled-pid guard removed | ritual.sh:350 | yes | 74 |
| M-H | `gate done` → `running` | ritual.sh:349 | yes | 75 |
| M-I | commit verification block disabled (`if false`) | factory-task:251 | yes | 41, 42, 43 |
| M-I2 | bare-`ok` template rejection removed | factory-task:263 | yes | 43 |
| M-J | `setsid -w` → `setsid` | factory-wave:53 | yes | 31, 32 |

**cr9's table, re-applied on CR3r's tree — 11 of 11 die.**

| cr9 # | mutation | died? | failing tests |
|---|---|---|---|
| M-A | `-w` dropped (= M-J) | yes | 31, 32 |
| M-B | `pid=$wave_pid` (= M-A) | yes | 65, 66, 67, 68, 71 |
| M-C | DEAD printed for a fresh log with a dead pid | yes | 58, 59, 64, 70 |
| M-D | `base:` back to `symbolic-ref --short` | yes | 29 |
| M-E | groups space-joined (`${groups[*]}`) | yes | 30 |
| M-F | `pid:` written as 0 | yes | 29 |
| M-G | `run.meta` block moved after the dispatch loop | yes | 29, 30, 34, 40 |
| M-H | trap after marker (= M-B) | yes | 38, 39 |
| M-I | `<KEY>.pid` EXIT trap deleted | yes | 35 |
| M-J | hint printed regardless of landed keys | yes | 70, 75 |
| M-K | re-exec applied when already a session leader | yes | 29, 30 |

cr9's M-B2 and M-B3 (the two arms of the per-key `case`) are M-A2/M-A3 above —
both now die, closing cr9 MAJOR-1; M-H closes cr9 MAJOR-2.

**CR5's eleven, re-applied on CR3r's tree** (`bats 92 + 90`) — all still die.
CR3r's `ritual.sh` diff is confined to `inflight_stdout` and its two new
helpers, and `session-start.sh` is untouched, so this is structurally safe;
measured anyway.

| CR5 # | mutation | died? (failing tests) |
|---|---|---|
| M-A | board check back to the packaged `evidence` | yes (4, 34, 35, 38, 39) |
| M-B | the fake wins whenever `evidence` is on PATH | = M-A |
| M-C | `stop_hook_active` guard removed | yes (36) |
| M-C2 | `get_flag` also matches `false` | yes (16 failures: 1–7, 11, 12, 22–24, 26–28, 32) |
| M-D | no interpreter → block instead of degrade | covered by test 39 (green) |
| M-E | `session-start`'s brief back to the packaged `evidence` | yes (45, 53, 54, 55) |
| M-F | `RITUAL_PYTHON` ignored (both) | yes |
| M-F (ritual) | `ritual.sh` only | yes (38) |
| M-F (session) | `session-start.sh` only | yes (54) |
| M-G | wrapper-parsing fallback removed (both) | yes |
| M-G (ritual) | `ritual.sh` only | yes (39) |

One extra mutation of my own — the wrapper-parsing fallback removed in
`session-start.sh` **only** — survives. That is a pre-existing CR5 coverage gap
in a file CR3r does not touch, not a CR3r regression; noting it so it is not
lost.

**Score: 14/14 of the plan's, 11/11 of cr9's, 11/11 of CR5's — 36/36.**

## Findings

### MAJOR-1 — `gate done` is above the stale-after cut, so every review that has ever finished is listed forever; the live in-flight table grows 563 → 1518 bytes and now overflows the SessionStart cap

`tools/ritual.sh:348-359`

```sh
    if [ "$gate_done" -eq 1 ]; then
      status="gate done"
    elif [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && ! pid_recycled "$pid" "$pidfile"; then
      …
    elif [ "$mt" -gt "$stale_after" ]; then
      stale_count=$((stale_count + 1))
      continue
    else
      status="running"
    fi
```

`gate_done` short-circuits above the staleness `continue`. A `<KEY>.review.log`
never gets a `<KEY>.review.result`, so the loop never skips it; the only thing
that used to retire it was its age. Now, as soon as `factory-review` writes
`<KEY>.review.md` — i.e. the moment a gate *succeeds* — that log is listed
permanently.

The function's own doc comment, written by this diff, promises the opposite
(`ritual.sh:260-262`):

> `Logs older than stale-after with a dead or missing pid are never listed, only counted in one summary line so the brief's budget goes to the runs actually in flight, not dead corpses.`

A gate-done log has no pid at all (`pid` stays empty, the fallback is skipped by
`[ "$gate_done" -eq 0 ]` at `:344`), so it is squarely "a dead or missing pid" —
and it is listed.

Measured on a throwaway fixture (rule row 5b): a `CR3.review.log` touched
3 hours back with `CR3.review.md` beside it →

```
r1 CR3.review - gate done - log age 180m
```

Measured live, read-only, against the real `~/factory/runs` (rule row 9):
**23 such lines**, ages 1801–1920 minutes (30–32 hours), every one of them a
review that finished on 2026-09-04:

```
a1 N10FIX.review - gate done - log age 1883m
a1 N10.review    - gate done - log age 1910m
…
s1 S1.review     - gate done - log age 1920m
```

The stale counter drops from 209 to 186 — exactly those 23 — and the output
grows from **563 bytes / 14 lines** (base) to **1518 bytes / 37 lines**.
`tools/session-start.sh:164` budgets this part at
`SESSION_START_CAP_INFLIGHT:-1200`, so the In-flight section of every
SessionStart brief is now cut. What survives the 1200-char slice ends at

```
cr15 wave-group-1 - running -
```

— dropping `fd2`, `og5`, `rt8`, `s1`, `sb3`, `sb4`, `sb5`, **`sb6` (the live
seat run)** and the `… and N stale logs` summary. The base's 563 bytes fit
whole. This is the same failure the cr2 gate rejected CR1 for ("the in-flight
part floods and truncates"), and it grows by one line per gate from here on.

It also breaks the contract's own first sentence — *"CR3b's behaviour stands;
this round changes tests first and code only where a minor says so."* CR9's
MINOR-6 asked for `gate done` **instead of** the two-hour `running`, not
instead of the staleness cut.

**Fix (small):** move the `gate_done` test below the `elif [ "$mt" -gt
"$stale_after" ]` arm — or gate it with `[ "$mt" -le "$stale_after" ]` — and add
the missing fixture: `CR3.review.md` beside a `CR3.review.log` aged 3 h must be
counted stale, not listed. Test 75 uses a *fresh* log only, which is why the
suite is green.

### MINOR-1 — the commits-mismatch arm fires for every status, overwriting the seat's real diagnosis

`tools/factory/seat/factory-task:255-259`

```sh
  if [ -n "$claimed_commits" ] && [ -n "$actual_commits" ] && [ "$claimed_commits" != "$actual_commits" ]; then
    …
    status=failed
    notes_line="FACTORY-NOTES claimed $claimed_commits commits, found $actual_commits"
```

There is no `[ "$status" = "done" ]` on this arm (the two below it have one).
Measured (rule row 6f): a seat that honestly reports
`status=failed / COMMITS 0 / NOTES the unit check failed on tests/unit/80; see the log`
on a branch holding one checkpoint commit records

```
FACTORY-RESULT status=failed
FACTORY-CHECKS unit=fail
FACTORY-COMMITS 0
FACTORY-NOTES claimed 0 commits, found 1
```

The status was already `failed`, so the demotion changes nothing — but the one
line the operator reads to learn *why* it failed is gone. Same for the
synthesised no-result record, whose `see $log` pointer is replaced. **Fix:**
scope the arm to `status=done` (as item 6's sentence intends — "never record
`status=done` for a run with no commit"), or append rather than replace the
notes.

Related, same block, `factory-task:269`: `result_line="FACTORY-RESULT
status=failed"` discards any other field on the original line, notably the
`exit_code=$exit_code` the synthesised failures carry.

### MINOR-2 — a claimed/actual mismatch of *extra* commits is recorded as a lie

Rule row 6e: claimed 1, branch has 2 → `status=failed`,
`claimed 1 commits, found 2`, rc 2. This is exactly what the plan's item 6
says, and the message does name the numbers, so it is not a contract breach —
but it is worth the operator knowing before it bites. This repo's own
`pre-commit` gate ends with *"git add docs/OPERATIONS.md and commit again"*, and
a seat that follows it lands two commits while reporting one; a chained group
`"A B"` then skips B. The fork point is per-key (`factory-ws` writes
`base_sha` = the workspace's HEAD at clone time and the workspace is recreated
every run, so chains and re-runs are counted correctly — I checked), so the
only false positive is a seat that miscounts its own commits. **Fix, if the
operator wants it softer:** demote only when `actual < claimed` or
`actual == 0`; keep the note when `actual > claimed`.

### MINOR-3 — two new names escape `local`, the exact class item 5 asked to fix

`tools/ritual.sh:273` (`stale_pid_count=0`) and `:315`
(`while IFS= read -r gline`). Neither appears in the `local` list at
`:264-269`. `meta` and `live` were correctly restored, and then two fresh
globals were introduced in the same function. No effect today (both are set
before use and `inflight_stdout` resets `stale_pid_count` on entry), but the
function is called from both `inflight` and `precompact` and the file runs under
`set -u`. **Fix:** add both to the `local` line.

Also at `:267`: `local ps_epoch file_epoch` is dead — those two names are only
used inside `pid_recycled`, which declares its own.

### MINOR-4 — `--then` in the relaunch hint is hand-double-quoted, not `%q`

`tools/ritual.sh:393`

```sh
          [ -n "$then_text" ] && relaunch="$relaunch --then \"$then_text\""
```

The groups were moved to `%q` (MINOR-7 of cr9, correctly fixed and pinned by
test 40/72); the `--then` value beside them was not. Measured: a `run.meta`
carrying `then: say "hi"; ff` produces

```
z K - running - log age 0m - then: say "hi"; ff - relaunch: factory-wave z /tmp/repo K --then "say "hi"; ff"
```

which no longer reproduces the argv — the very property contract item 3 names.
The plan's matrix spells the expected form with literal double quotes, so this
follows the letter of the plan; `printf %q` would satisfy both. Low reachability
(`--then` values are orchestrator-written prose today), but they *are* prose,
which is where a quote turns up first.

### MINOR-5 — the recycled-pid test's fake `ps` is decorative

`tests/unit/92-ritual.bats` test 74 writes a fake `ps` and then asserts the pid
is not "alive". I ran the same fixture with the **real** `ps` and got the same
result:

```
-- with fake ps  -> … and 1 stale logs older than 2h
-- with real ps  -> … and 1 stale logs older than 2h
```

because the fixture `touch -d '3 hours ago'`es the pid file while `$$` started
seconds ago — the guard fires on the real timestamps. The test does kill M-G
(the guard's removal), which is what the plan asks, so this is not a coverage
hole; it just does not prove the fake-`ps` path it claims to. The real-format
check the matrix asked for passes independently: `ps -o lstart= -p $$` →
`Sat Sep  5 21:41:09 2026` → `date -d` → `1788662469`.

### MINOR-6 — the README documents the reaper for `.gate` only, and not the recycled-pid guard or the new summary line

`README.md:105-107` covers the marker's strand and its reaping. `README.md:38-39`
and `:73-74` still say only "(removed on exit)" for `<KEY>.pid` — cr9's MINOR-5
asked for one sentence there about the `SIGKILL` strand, and the reaper now
covers `.pid` too. The `… and N stale pid files` summary line and the
recycled-pid denial are undocumented. Everything else the matrix asked for is
there: pid files (`:38-47`), the marker pid (`:120-126`), `base:`/`group:`
(`:41-47`), the `--then` rules (`:79-88`), the mixed-wave rule (`:88-94`), item 6
(`:73-79`), `gate done` (`:125`), and the retired `setsid -f` rule (`:86-87`).

### MINOR-7 — the eval-free unquote does not cover bash's `$'…'` `%q` form

`tools/ritual.sh:316-319` reads a `group:` line back with
`xargs printf '%s'`. `printf %q` emits `$'a\nb'` for a value containing a
newline or a tab, which `xargs` does not parse; the fallback `|| g=$gline` does
not fire (xargs succeeds), so the group silently becomes the literal
`$'a\nb'`. Groups come from argv and can contain a newline. Task keys are
alphanumeric today, so this is theoretical — the same standing this minor had
in cr9 for `group:` on the write side. Worth one line in the README (key
charset) or a `$'` guard.

## Landing note

**Landing CR3r while the old-driver run `sb6` is live is safe** — but I would
land the `gate done` fix with it, because the reader half takes effect the
moment the merge lands.

- **Running processes are unaffected.** `git merge --ff-only` writes a new file
  and renames over it, so every in-flight `factory-wave` / `factory-task` /
  `factory-review` keeps its old inode and its old body for its whole life
  (re-measured in cr9's gate; nothing in the integrate → fast-forward recipe
  overwrites a file in place).
- **A `factory-task` spawned *after* the landing by the *old* `factory-wave`
  still works.** `FACTORY_BIN` resolves to the directory of `factory-lib.sh`
  (`factory-lib.sh:23`), i.e. the repo tree, so the old wave will invoke the
  **new** `factory-task`. The call is unchanged
  (`"$FACTORY_BIN/factory-task" "$run" "$repo_path" "$key" [--after "$prev"]`,
  `factory-wave:151/153`), and the new script adds no required input and no new
  output the wave parses: it writes `<KEY>.pid` + an EXIT trap, and it can now
  demote a `done` to `failed`. The `.result` keeps the same four-line block and
  the same fields, so the old wave's summary parsing is unchanged.
  The one *behavioural* consequence to accept: a key dispatched after the
  landing by `sb6`'s old wave is now subject to the commit check, so a seat that
  reports `done` with no commit (the cr13 failure this item exists for) will make
  that wave exit non-zero and skip the rest of its chain. That is the intended
  new behaviour, and it applies to the old wave too.
- **The reader half is immediate.** `tools/ritual.sh` is re-read on every
  `SessionStart`/`Stop`/`PreCompact`, so MAJOR-1 lands the moment the merge does
  — 23 dead `gate done` lines in the very next brief, and the In-flight part
  over its 1200-char cap. That is the concrete reason to fix it before landing
  rather than after.
- **Old runs degrade correctly.** `sb6` and every other pre-CR3r run has no
  `run.meta`, no `<KEY>.pid` and no `<KEY>.gate`; those keys keep reading by
  CR1b's mtime rule (verified live — no `DEAD` lines, `sb6 SB2r - running` and
  `sb6 wave-group-1 - running` both correct). The reaper globs
  `runs/*/*.pid` and `runs/*/*.gate`, of which the real dir has **none** (checked
  before and after both probes), so landing deletes nothing.

## Verdict

**REJECTED** — one MAJOR, behavioural, two lines of code and one fixture from
being green.

Everything this round was re-planned for is done and done well: cr9's MAJOR-1
(the per-key pid preference) is pinned by four discriminating fixtures and dies
under M-A, M-A2 and M-A3; cr9's MAJOR-2 (the marker ordering) is pinned twice,
structurally and behaviourally, and the FIFO test is a genuinely good piece of
work — I swapped the two lines and watched the marker stay behind. All seven
minors are closed, 36 of 36 mutations die, red-before-green is 27 tests on the
base and 13 on CR3b, all five checks are green, and the commit convention is
exact.

What stops it is the one place where a new status was added above the reader's
oldest rule: `gate done` never reaches the stale-after cut, so every finished
review gate is listed forever. Live, that is 23 lines of 30-hour-old corpses,
1518 bytes against a 1200-byte budget, and a truncated In-flight section that
drops the live seat run — the same defect class that got CR1 rejected, arriving
the moment this lands. Move the `gate_done` test below the staleness arm, add
the aged-review fixture that test 75 is missing, and fold the seven minors
(chiefly the `status=done` scoping on the commits-mismatch arm, which today
erases a failing seat's own explanation).
