# Opus gate — seat run cr9, task CR3b — REJECTED

## Summary

CR3b is one commit (f46777e), subject byte-identical to the plan's, both
trailers present, all seven touched files inside `touches`. Every check is
green: shellcheck on the five scripts, 70/70 in `80-seat-driver.bats` +
`92-ritual.bats`, 86/86 with `90-session-start.bats`, `unit` (291 tests, also
with `--rebuild`), `lint`, and the `pre-commit` gate (whose only failure is the
known stale-queue-block artefact of a landed task in a standalone clone —
regenerated it exits 0, so not a defect).

**All three CR6 majors are genuinely fixed, and I could not break any of them
by hand.** Measured on throwaway fixtures: `setsid -w` returns the wave's exit
code 1 after the full 4 s under `set -m` while still detaching (wave
pid=pgid=sid, survives `kill -KILL -<launcher pgid>` and writes its `.result`);
`base:` is the fixture repo's `rev-parse HEAD`; `"K1" "K2"` and `"K1 K2"` write
different `group:` lines and produce different, shell-quoted `relaunch:` lines;
`<KEY>.pid` and `<KEY>.gate` carry the right pids and are removed on exit and
on SIGTERM; the CR6 fixture that used to print `pid … DEAD - relaunch:` for a
live gate on a landed task now prints `running`, with no relaunch hint. The
live read-only probe against the real runs dir is byte-identical to the base's
output — no DEAD lines, nothing lost.

Two MAJORs stop it, and both are **test-coverage** MAJORs, not behavioural
ones — mutations the plan's own step-1 list says must die and that survive:

1. The whole per-key-pid mechanism in the reader — the fix that this round
   exists for — is unpinned. `pid=$wave_pid` unconditionally (the plan's
   "run-level pid applied to every log"), and even deleting the `<KEY>.gate`
   branch or the `<KEY>.pid` branch outright, leaves 70/70 green. CR6's MAJOR-2
   could be reintroduced tomorrow and no test would notice.
2. The marker's trap ordering (`trap` before `printf`) is unpinned: moving the
   trap back after the marker leaves 70/70 green, against the plan's "(mutation:
   trap after marker → fails on the kill case)".

Both are fixed by adding fixtures, not by touching production code. 9 of the
11 required mutations die; CR3's 6 and CR5's 11 all still die.

## Rule behaviour

Fixtures: throwaway `FACTORY_ROOT=…/scratchpad/fx/froot<N>`, a throwaway
`git init` repo at `5f6eb46`, fake `factory-task` binaries injected with
`FACTORY_BIN_OVERRIDE`, a fake `dsh-openrouter` on `PATH`, a copy of the seat
directory with a stub `factory-ws`, and a `setsid` shim that logs its argv
before `exec`ing the real one. No real seat, no real `~/factory` write, at any
point.

| row | expected | observed |
|---|---|---|
| **1** exit code under job control (`set -m`, fake task sleeps 4 s, `status=failed`) | rc 1 after ≥ 4 s, summary on the launcher's stdout | `K1 status=failed …` then `LAUNCHER SAW RC=1`, `ELAPSED=4s` |
| **1** the driver's sid == its pid | yes | wave `3353016`: `pid=pgid=sid=3353016`, ppid = the `setsid -w` process; `run.meta` `pid: 3353016` |
| **1** already a session leader → no re-exec | 0 shim calls | `setsid -w bash factory-wave …` → shim log 0 lines, rc 0 |
| **1** not a session leader → exactly one re-exec (no loop) | 1 | shim log 1 line: `setsid-called: -w -- …/factory-wave r5 … K1` |
| **1** `kill -KILL -<launcher pgid>` mid-run | wave completes, writes `.result` | killed at 20:31:41, `K1.result` present 20:31:44 (fake sleeps 4 s), `status=failed` written |
| **2** env + argv survive the re-exec | identical inside | fake seat recorded `FACTORY_PLAN=/some/plan.md`, `MYVAR=keep me`, `ARGV: r1 <repo> K1`, and `then: gate K1; ff; dispatch CR4` verbatim |
| **2** a group `"N11 N3 N6"` survives | one chain | `group: "N11 N3 N6"` round-trips into `relaunch: … "N1" "N11 N3 N6"` |
| **3** `<KEY>.pid` while the seat runs, gone after | yes | `K1.pid` = `3381804` = the `factory-task` pid (`ps` confirmed), GONE after exit rc 0 |
| **3** …gone after SIGTERM | yes | rc 143, `K1.pid` GONE |
| **3** `<KEY>.gate` holds `factory-review`'s pid | yes | `gate present: YES; content=3389810; review pid=3389810`; GONE after success (rc 0) and after SIGTERM |
| **3** SIGKILL the reviewer | say what remains | `K1.gate` **PRESENT** with a dead pid; the reader gives it no special status — a fresh log is "running" by contract 2, an old one is counted stale. Nothing reaps it (MINOR-5) |
| **4** CR6's fixture (`CR3.log` + `CR3.result` done + fresh `CR3.review.log` + live `CR3.gate`) | running, no DEAD, no relaunch | `cr6 CR3.review - running - log age 0m - then: gate CR3; integrate; ff` |
| **4** fresh log + dead run pid | live | `rb K - running - log age 0m - relaunch: factory-wave rb /tmp/repo "K"` |
| **4** old log (3 h) + dead `<KEY>.pid` | counted stale, not listed | not listed; `… and 1 stale logs older than 2h` |
| **4** old log (3 h) + ALIVE `<KEY>.pid` | live | `rd K - pid 3412272 alive - log age 180m …` |
| **4** dead wave, all keys `status=done` | no relaunch hint | `re N1.review - running - log age 0m` (no hint) |
| **4** dead wave, one key without `.result` | relaunch reproducing the original argv, groups quoted | `rf N1 - running - log age 0m - then: integrate - relaunch: factory-wave rf /home/dalhaka/nixos-agent-env "N1" "N11 N3 N6"` |
| **4** dead wave, K1 done **and** K2 without `.result` (mixed) | matrix says hint; contract says no hint | **no hint** — `rg2 K2 - running - log age 0m` (MINOR-1) |
| **5** `base:` == `git rev-parse HEAD` | SHA | `base: 5f6eb461c1dc191452f70972226ec595922aea53` (repo HEAD) |
| **5** one `group:` line per group, quoted | yes | a1: `group: "K1"` + `group: "K2"`; a2: `group: "K1 K2"`; relaunch lines differ accordingly |
| **5** `pid:` == the wave's pid, never 0 | yes | `pid: 3673772` etc., always the post-re-exec wave pid, alive at task launch (the fake asserted `pid-alive`) |
| **5** `then:` absent when not given | absent | a3 with `--then ""` → `then: ` (present, empty); no `--then` → no `then:` line at all |
| **5** `--then` twice | last wins | `--then first --then "second; ff"` → `then: second; ff` |
| **5** multi-line `--then` | exit 2 before anything is written | `factory-wave: --then value must be a single line (run.meta is one key per line)`, rc 2, **`$FACTORY_ROOT` not even created**; rc 2 also propagates through the re-exec under `set -m` |
| **5** `run.meta` exists when the fake seat starts | yes | `run.meta at launch: PRESENT`, full content recorded by the fake |
| **6** the run-level pid is never applied to a log with its own pid file | yes | wave pid ALIVE + `K.pid` dead + 3 h old log → not listed, counted stale (the run pid would have said "alive") |
| **7** CR5 intact: tree renderer, `stop_hook_active`, cap, stale line | yes | `92-ritual.bats` 33/33 and `90-session-start.bats` 16/16 green; all 11 of CR5's named mutations still die (below); the diff touches only `inflight_stdout` |
| **8** README: pid files, marker pid, `base:`/`group:`, `--then` rules, `setsid -f` retired | yes | `README.md:38-45` (files incl. `run.meta` fields), `:71` (`<KEY>.pid`), `:79-88` (`--then` optional/last-wins/single-line, `setsid -w`), `:88-89` "the board's `setsid -f …` launch rule is retired", `:103-107` (marker pid, trap-before-marker, SIGKILL strand) |
| **9** live probe, read-only | no DEAD-with-fresh-log lines | 23 lines, **byte-identical** to the base's `ritual.sh` on the same runs dir (`diff` empty); no run.meta/.pid/.gate exists in `~/factory/runs`, so the new code degrades exactly to CR1b's mtime rule |
| **10** every driver test sets `FACTORY_BIN_OVERRIDE` | yes | all 10 `factory-wave` invocations (bats lines 1430, 1483, 1486, 1521, 1548, 1580, 1618, 1625, 1633, 1642) are covered; CR6's MINOR-5 (old test 30) is fixed at `80-seat-driver.bats:1514-1520` with a comment. The `factory-task`/`factory-review` tests invoke those scripts directly, as their subject, with a fake `dsh-openrouter` |

Row 9 detail — what the newest runs print (and `pgrep -af factory-task` at the
same moment: `cr11 CR2b`, later also `sb5 SB2b`):

```
cr10 wave-group-1 - running - log age 17m
cr11 CR2b - running - log age 0m          <- matches the live factory-task
cr11 wave-group-1 - running - log age 0m
cr9  wave-group-1 - running - log age 24m
fd2  integrate - running - log age 15m
fd2  wave-group-1 - running - log age 45m
sb4  wave-group-1 - running - log age 29m
… and 196 stale logs older than 2h
```

`cr9`/`cr10`/`fd2`/`sb4` show as "running" only because their `wave-group-N.log`
and `integrate.log` never get a `.result` — the pre-CR3b mtime rule, unchanged
by this diff (the base prints the identical 23 lines).

## Checks

Run in the fresh clone `…/scratchpad/gate-cr9-CR3b` at f46777e.

| check | rc | wall |
|---|---|---|
| `nix develop -c shellcheck factory-wave factory-review factory-task factory-lib.sh tools/ritual.sh` | 0 | 2.0 s |
| `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats` | 0 (86/86) | 15.5 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 | 1.1 s (cached) |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0 (291/291) | 41.8 s |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 | 3.5 s |
| `nix develop -c githooks/pre-commit` | **1** → 0 after `git add` | 3.0 s |

Inside the `unit` derivation, tests 172 and 173 (`setsid -w keeps the wave's
exit code`, `the wave survives … SIGKILLed`) **skip**: `no real setsid/ps in
this sandbox`. They do run outside the sandbox — both pass in the devShell
`bats` run, and I reproduced both by hand (rows 1). Worth knowing that the
`unit` gate alone does not exercise them.

The `pre-commit` failure is the known landed-task artefact, not a defect. Its
only output is

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
```

and the regenerated diff is exactly `… B1 CR2 CR3b FD1b …` → `… B1 CR2 FD1b …`.
Re-running with the block staged: `All checks passed!`, `render.test.mjs: all
assertions passed`, rc 0.

## Red before green

**Drivers.** CR3's four driver files written over CR3b's
(`git -C /home/dalhaka/factory/ws/cr6/CR3 show task/CR3:tools/factory/seat/<f>`),
CR3b's tests kept, `bats tests/unit/80-seat-driver.bats`:

```
1..37
not ok 29 factory-wave writes run.meta recording identity, base SHA, quoted groups, pid and --then before dispatch
#   `[[ "$output" == *"base: $sha"* ]]' failed
not ok 30 factory-wave writes one quoted group: line per wave group, so parallel and a chain differ
#   `[[ "$output" == *'group: "K1"'* ]]' failed
not ok 31 factory-wave re-execs under setsid -w when it is not a session leader
#   `[[ "$output" == *"-w -- $SEAT/factory-wave r1 $repo --then gate K1"* ]]' failed
not ok 32 setsid -w keeps the wave's exit code when the launcher gives it a process group
#   `[[ "$output" == *"RC=1"* ]]' failed
ok 33 the wave survives its launcher's process group being SIGKILLed and writes its result
not ok 34 factory-wave --then: absent when not given, last wins when doubled, single-line only
#   `[[ "$output" != *"then:"* ]]' failed
not ok 35 factory-task writes <KEY>.pid while it runs and removes it on exit
#   `[[ "$output" == *"pid-present"* ]]' failed
not ok 36 factory-review leaves a <KEY>.gate marker holding its pid while gating and removes it after
#   `[[ "$gp" =~ ^[1-9][0-9]*$ ]]' failed
ok 37 factory-review removes the <KEY>.gate marker on SIGTERM
```

7 of the 9 new driver tests are red on CR3; tests 1–28 (pre-existing) all stay
green, so nothing new leans on old behaviour. Test 33 is green on CR3 because
CR3 already detached (only the exit code was lost, which is test 32's job).
Test 37 is green on CR3 because CR3 already created the marker and armed the
trap — one line later; SIGTERM arrives long after both lines, so 37 cannot see
the ordering fix (see MAJOR-2).

**`tools/ritual.sh`.** CR3's `ritual.sh` predates CR5, so the honest "before"
for this file is the task's base (main + CR5), `e78217a`. With
`git show e78217a:tools/ritual.sh` in place and CR3b's tests kept,
`bats tests/unit/92-ritual.bats`:

```
1..33
not ok 15 inflight reports a dead wave as live-by-rule with a relaunch hint that reproduces the argv
#   `[[ "$output" == *"K - running - log age 0m"* ]]' failed
not ok 16 inflight treats a fresh log with a dead run pid as live, never DEAD
#   `[[ "$output" == *"K - running"* ]]' failed
not ok 17 inflight reads a running gate from <KEY>.gate, not the dead run pid
#   `[[ "$output" == *"CR3.review - running - log age 0m"* ]]' failed
```

11 red in total; the other 30 ritual tests (CR1b's and CR5's) stay green.
Restored (`git restore tools/`, tree clean): 70/70 green.

## Mutation table

Applied to the clone, `git diff --stat` asserted non-empty before each run
(one VOID row was re-applied with `awk` and re-run), `bats
tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats` under `timeout`,
`git restore tools/` after. Numbers below are test numbers in that combined
run (1–37 driver, 38–70 ritual).

**The plan's table**

| # | mutation | site | died? | failing tests |
|---|---|---|---|---|
| M-A | `-w` dropped from setsid | factory-wave:56 | yes | 31, 32 |
| M-B | the reader applies the run-level pid to every log (`pid=$wave_pid`) | ritual.sh:279 | ***SURVIVES*** | — (70/70 green) — **MAJOR-1** |
| M-C | DEAD printed for a fresh log with a dead pid | ritual.sh:289 | yes | 52, 53 |
| M-D | `base:` back to `symbolic-ref --short` | factory-wave:115 | yes | 29 |
| M-E | groups space-joined (`${groups[*]}`) | factory-wave:122-124 | yes | 29, 30 |
| M-F | `pid:` written as 0 | factory-wave:120 | yes | 29 |
| M-G | `run.meta` block moved after `wait` | factory-wave:115-128 | yes | 29 |
| M-H | trap armed **after** the marker | factory-review:68-69 | ***SURVIVES*** | — (70/70 green) — **MAJOR-2** |
| M-I | `<KEY>.pid` EXIT trap deleted | factory-task:112 | yes | 35 |
| M-J | relaunch hint printed regardless of landed keys (`if true`) | ritual.sh:295 | yes | 54 |
| M-K | re-exec applied when already a session leader | factory-wave:55 | yes | 29, 30, 34 |

M-K also demonstrated as a real loop outside bats: with a counting `setsid`
shim, a session-leader launch re-execs until the shim refuses — `setsid calls
with M-K applied: 4` (correct code: 0).

**Extra mutations of mine, isolating MAJOR-1**

| # | mutation | died? |
|---|---|---|
| M-B2 | never read `<KEY>.gate` for a `*.review` log (branch → `:`) | ***SURVIVES*** |
| M-B3 | never read `<KEY>.pid` for a task log (branch → `:`) | ***SURVIVES*** |

**CR3's six kills, re-applied on CR3b's tree** — all still die.

| CR3 # | mutation | failing tests |
|---|---|---|
| M-A | delete the `run.meta` write block | 29, 30, 34 |
| M-B | drop the `then:` printf | 29, 34 |
| M-D | remove the `setsid` re-exec block | 31, 33 |
| M-E | re-exec unconditionally | = M-K: 29, 30, 34 |
| M-F | never create the gate marker | 36, 37 |
| M-G | drop the marker EXIT trap | 36, 37 |

**CR5's eleven kills, re-applied on CR3b's tree** — all still die
(`bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats`, numbering
shifted by CR3b's two new ritual tests).

| CR5 # | mutation | died? (failures) |
|---|---|---|
| M-A | board check back to the packaged `evidence` | yes (5) |
| M-B | the fake wins whenever `evidence` is on PATH | yes (5) |
| M-C | `stop_hook_active` guard removed | yes (1) |
| M-C2 | guard allows for `false` too | yes (16: #1-7, 11, 12, 22-24, 26-28, 32) |
| M-D | no interpreter → block instead of degrade | yes (1) |
| M-E | `session-start`'s brief back to the packaged `evidence` | yes (4) |
| M-F | `RITUAL_PYTHON` ignored (both scripts) | yes (2) |
| M-F (ritual) | as above, `ritual.sh` only | yes (1) |
| M-F (session) | as above, `session-start.sh` only | yes (1) |
| M-G | wrapper-parsing fallback removed (both) | yes (1) |
| M-G (ritual) | `ritual.sh` only | yes (1) |

Score: **9 of 11 of the plan's mutations killed**, 6/6 of CR3's, 11/11 of CR5's.

## Findings

### MAJOR-1 — the per-key pid preference, the whole point of this round, is unpinned: the reader can be reverted to CR3's run-level pid and every test stays green

`tools/ritual.sh:269-279`

```sh
    case "$key" in
      *.review)
        basekey=${key%.review}
        [ -f "$rundir/$basekey.gate" ] && pid=$(cat "$rundir/$basekey.gate")
        ;;
      *)
        [ -f "$rundir/$key.pid" ] && pid=$(cat "$rundir/$key.pid")
        ;;
    esac
    # Fall back to the run-level pid only when there is no pid file.
    [ -n "$pid" ] || pid=$wave_pid
```

Replacing the last line with `pid=$wave_pid` — the plan's step-1 test (4),
verbatim: *"(mutation: the run-level pid applied to every log → fails)"* —
leaves **70/70 green**. So does deleting the `*.review)` branch (M-B2), and so
does deleting the `*)` branch (M-B3). The entire `case` block is dead weight as
far as the suite is concerned.

Why the three new ritual tests miss it: after CR3b, a dead pid on a fresh log
falls through to `status="running"` (contract 2, correct), and test 54's
fixture (`92-ritual.bats:269-290`) has a fresh `CR3.review.log`. With the gate
read, the pid is alive → `running`; with the gate ignored, the pid is the dead
wave pid → `running` by the freshness rule. The assertion
`[[ "$output" == *"CR3.review - running - log age 0m"* ]]` cannot tell the two
apart, so the test named *"reads a running gate from `<KEY>.gate`, not the dead
run pid"* passes without reading the gate at all.

The behaviour itself is right — I verified the discriminating cases by hand
(rule rows 4 and 6): old log + dead `K.pid` + **alive** run pid → correctly
counted stale, not "alive"; old log + **alive** `K.pid` + dead run pid →
`rd K - pid 3412272 alive - log age 180m`. Nothing stops the next edit from
undoing it, which is exactly how CR6's MAJOR-2 shipped.

**Fix (tests only):** add the two fixtures above to `92-ritual.bats` — a log
older than `RITUAL_STALE_AFTER` is the only place where "alive" and "running"
are distinguishable, so both cases must use an old log:
(a) `K.log` aged 3 h + `K.pid` holding a dead pid + `run.meta` `pid: $$` →
assert the line is **absent** and the stale summary counts it;
(b) `K.log` aged 3 h + `K.pid` holding `$$` + `run.meta` `pid: 999999` →
assert `pid $$ alive`. (a) kills M-B and M-B3; for the gate, (c) `CR3.review.log`
aged 3 h + `CR3.gate` holding `$$` + a dead run pid → assert the line is listed
(kills M-B2).

### MAJOR-2 — the marker's trap-before-marker ordering is unpinned; the plan's own kill case does not kill

`tools/factory/seat/factory-review:64-69`

```sh
# ... The trap
# is armed BEFORE the marker is created so a signal between the two cannot
# strand the marker; ...
gate_marker=$runs_dir/$key.gate
trap 'rm -f -- "$gate_marker"' EXIT
printf '%s\n' "$$" >"$gate_marker"
```

The source order is correct. But swapping the two statements (M-H) leaves
**70/70 green**, against the plan's step-1 test (3): *"(mutation: trap after
marker → fails on the kill case)"*. `80-seat-driver.bats:1768-1824` (test 37)
waits for the marker to appear and only then sends SIGTERM — by which time both
lines have run either way, so the ordering is invisible to it. CR3 shipped the
reverse order and test 37 is green on CR3 too (see Red before green), which
confirms the test never covered this.

**Fix (tests only):** the race cannot be won by timing, so pin it structurally —
e.g. assert in `80-seat-driver.bats` that in `tools/factory/seat/factory-review`
the `trap … EXIT` line for `$gate_marker` precedes the line that writes it
(`awk`/`grep -n` on the two line numbers), the same way a "no `2>/dev/null` on a
gated command" rule would be pinned. Cheap, deterministic, and it dies on M-H.

### MINOR-1 — a mixed wave (one key landed, one not) gets no relaunch hint

`tools/ritual.sh:294-302`. The suppression is *any* `.result` with
`status=done` in the run directory:

```
rg2 K2 - running - log age 0m          # K1.result done, K2 has no result, wave pid dead
```

The plan's contract sentence ("whose keys have no `.result` with `status=done`")
reads exactly this way, so the implementation is defensible; the gate matrix's
"one key without `.result` → relaunch hint" reads the other way. In the common
shape — a three-key wave where one landed and two died at a reboot — the
operator now gets no hint at all, and the hint they would want is not the
original argv anyway (it would re-dispatch the landed key). Nothing tests the
mixed case either way. **Fix:** decide it in the plan (either "no hint once
anything landed", documented in the README, or "hint listing only the groups
with no done result"), and add the mixed fixture.

### MINOR-2 — the relaunch hint drops `--then`, so it does not reproduce the original argv

`tools/ritual.sh:296-300` builds `factory-wave <run> <repo> <groups…>` and
never appends `--then "<text>"`, although `then:` is right there in `run.meta`
and is printed earlier on the same line. Copy-pasting the hint relaunches the
run **without** its recorded intent, so the new `run.meta` loses it. Carried
over from CR1b, but contract 3 now says the line "reproduces the original argv
exactly". **Fix:** append `--then "<then_text>"` when `then:` is present.

### MINOR-3 — "pid N alive" and "relaunch:" can appear on the same line

Rule row 4, fixture `rd`:

```
rd K - pid 3412272 alive - log age 180m - relaunch: factory-wave rd /tmp/repo "K"
```

The wave's own pid is dead and nothing has landed, so the hint fires — while
this key's seat is demonstrably alive. That is the mirror image of CR6's
MAJOR-2 (which called a live gate DEAD): acting on the hint double-dispatches a
paid seat for a key already running. **Fix:** also require that no per-key pid
file in the run directory holds a live pid before printing the hint.

### MINOR-4 — `meta` and `live` lost their `local` declarations

`tools/ritual.sh:238-239`. The base had
`local log result meta rundir …` / `local stale_after stale_count live`; the
rewrite dropped both names, so `meta` and `live` are now globals assigned
inside `inflight_stdout`. No effect today (nothing else in the script uses
either name, and both are set before use), but the function is called twice
(`inflight`, `precompact`) and the file runs under `set -u`. **Fix:** put
`meta` and `live` back in the `local` list.

### MINOR-5 — nothing reaps a `<KEY>.pid` or `<KEY>.gate` stranded by SIGKILL, and the README documents the strand for only one of them

Measured: `kill -KILL` on `factory-task` leaves `K1.pid` behind with a dead pid;
`kill -KILL` on `factory-review` leaves `K1.gate` behind. `README.md:105-107`
says so for the marker ("`SIGKILL` (and a reboot) can still strand the marker;
its dead pid is what marks it stale") but `README.md:38-39, 71` say only
"(removed on exit)" for `<KEY>.pid`. `grep -rn '\.gate\|\.pid' tools/ pkgs/`
finds no reaper anywhere. A stranded pid is also a pid the kernel may recycle,
after which the reader reports a long-dead key as "alive" — the failure mode
that hides a dead run. **Fix:** one README sentence for `<KEY>.pid`, and either
a reaper (drop a pid file whose pid is dead, next time the reader passes) or an
explicit note that staleness is judged by the log's age.

### MINOR-6 — a finished gate still reads "running" for up to `stale-after`, and review lines no longer carry a pid

`<KEY>.review.log` never gets a `<KEY>.review.result`, so once the gate exits
(marker removed) the line falls to the freshness rule and prints
`… <KEY>.review - running - log age Nm` for two hours. Pre-existing from CR1b,
but CR3b makes "running" the only word a review line can carry (`ritual.sh:282`
drops the `pid N alive` form for `*.review`), so a live gate and a finished one
are now indistinguishable in both directions. **Fix (cheap):** print
`gate pid N` when the marker is live, leaving bare `running` for the rest.

### MINOR-7 — `group:` is hand-quoted, not shell-quoted

`tools/factory/seat/factory-wave:123` — `printf 'group: "%s"\n' "$group"`. A
group containing a `"`, a `\` or a `$` produces a `group:` line that no longer
round-trips through the `relaunch:` string. Task keys are alphanumeric today,
so this is theoretical. **Fix:** `printf 'group: %q\n' "$group"` (and drop the
literal quotes), or state the key charset in the README.

## Landing note

**Landing CR3b while old-driver runs are live is safe**, including the fact
that CR3b touches `factory-task`.

Re-measured the rename-on-write property in a throwaway repo (a 6-second script
fast-forwarded to a longer version while running):

```
inode before: 243666056
A start inode=243666056
inode after merge: 243666081        <- new inode
A end -- the OLD script body ran to completion
running script exit=0
```

`git merge --ff-only` writes a new file and renames over it, so every currently
running `factory-wave`, `factory-task` (`pgrep`: pid 3412450, `cr11 CR2b`) and
`factory-review` keeps its old inode and its old body for its whole life. Only
an in-place byte overwrite corrupts a running script, and nothing in the
integrate → fast-forward recipe does that.

**Is a `factory-task` spawned *after* the landing by an *old* `factory-wave`
still compatible?** Yes — I read both. The call is unchanged in CR3b
(`"$FACTORY_BIN/factory-task" "$run" "$repo_path" "$key" [--after "$prev"]`,
`factory-wave:150-154`), `FACTORY_BIN` resolves to the same seat directory
(`factory-lib.sh:23`), and the whole of CR3b's `factory-task` diff is three
lines at `factory-task:110-112` that write `<KEY>.pid` and arm an EXIT trap —
no new required inputs, no changed outputs (`.log`, `.result`, the summary
fields the old wave parses are untouched), and `factory-task` had no other
`trap` for the new one to clobber. The old wave never reads `<KEY>.pid`, and
the *old* `tools/ritual.sh` running on the host until the landing globs
`*/*.log` only, so a stray `<KEY>.pid` is inert to it. If anything the mixed
state is strictly better: a key dispatched after the landing gets a real
liveness record even though its wave wrote no `run.meta`.

Two consequences to carry, not blockers:

- In-flight waves launched by the old driver have no `run.meta` and no
  `<KEY>.gate`; their keys keep reading by CR1b's mtime rule. Verified live:
  the new `ritual.sh` prints **byte-identical** output to the base's against
  the real `~/factory/runs` (23 lines, `diff` empty), with no DEAD lines.
- `tools/ritual.sh` is re-read on every `SessionStart`/`Stop`, so the reader
  half takes effect immediately at the landing; nothing to wait for.

## Verdict

**REJECTED** — two MAJORs, both coverage, no production-code change needed.
Every behaviour the plan asks for works: I could not break the exit code, the
detach, the SIGKILL survival, the per-key pids, the marker's pid, the SHA
`base:`, the quoted `group:` round-trip, the `--then` rules, or CR5. But the
plan's own step-1 list names two mutations that must die and neither does:
`pid=$wave_pid` (plus dropping either arm of the per-key `case`) leaves 70/70
green, so CR6's MAJOR-2 is one careless edit from returning unnoticed; and the
trap-before-marker ordering is invisible to test 37. Three fixtures in
`92-ritual.bats` (old log × per-key pid alive/dead, and the gate variant) and
one structural assertion for the trap ordering close both. Everything else —
scope, commit convention (subject byte-identical, both trailers, seven files
all inside `touches`), red-before-green (11 tests red at the base), 9/11 + 6/6 +
11/11 mutants, all five checks green — is in good shape, and the landing is
safe today.
