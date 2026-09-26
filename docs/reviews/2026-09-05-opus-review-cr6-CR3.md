# Opus gate — seat run cr6, task CR3 — REJECTED

## Summary

CR3 is one commit (008cf15), subject byte-identical to the plan's, both trailers
present, four files all inside `touches`. Shellcheck is clean, the whole
`80-seat-driver.bats` file is green (31 tests; main has 28, CR3 adds 3), the
`unit` and `lint` derivations build (including `--rebuild`), red-before-green is
real (all three new tests fail against main's drivers and pass against CR3's),
and 6 of 8 mutations die. The three headline behaviours all work on throwaway
fixtures: `run.meta` is written before the first task is dispatched, the
`setsid` re-exec really does put the wave in its own session and the run really
does survive its launcher's process group being SIGKILLed, and the `<KEY>.gate`
marker is present during a gate and removed on approve, reject and seat-failure.

Three MAJORs stop it.

1. The re-exec silently discards the wave's exit code and summary whenever the
   launching shell gives `factory-wave` its own process group — which is exactly
   what an interactive prompt does, and exactly the invocation the README's own
   "Running a wave" section prints. `setsid` must `fork(2)` for a process-group
   leader, and without `-w` the parent exits 0 immediately: I watched a wave
   whose task ended `status=failed` return `0` to its launcher in 0 s. The same
   paragraph of the README that introduces the re-exec still promises "exits
   non-zero if any task did not reach `status=done`". One word (`setsid -w`)
   fixes it and I verified the fix keeps the detach.
2. `run.meta`'s `pid:` is the *wave's* pid, but CR1b's `inflight` applies the
   run's pid to every `<KEY>.log` in that run's directory — and `factory-review`
   writes `<KEY>.review.log`, which matches that glob. So the ordinary workflow
   (wave lands, wave exits, orchestrator gates the key) now reports a **running
   gate as DEAD** and prints a `relaunch: factory-wave …` hint for a task that
   already landed. Before CR3 the same fixture read `running`. CR3 turns CR1b's
   pid branch on and this is the first thing it says.
3. `run.meta`'s `base:` is the branch name, not the repo's HEAD (and collides
   with `factory-task`'s `.result`, where `base:` is a SHA), and `groups:` is
   flattened with `${groups[*]}`, so `"K1" "K2"` (two parallel groups) and
   `"K1 K2"` (one chain) both serialise to `groups: K1 K2` — the derived
   relaunch reconstructs a chain as parallel groups, the FD1-class trap.

The two surviving mutations (`pid: 0`; `run.meta` written after dispatch) are
coverage gaps, filed as minors. The `pre-commit` gate exits 1 in a standalone
clone, but only because HEAD makes CR3 landed while the committed board block
still queues it; regenerating the block makes it exit 0. Not a defect.

Landing does **not** need to wait for an idle driver — measured, see below.

## Rule behaviour

Fixtures: throwaway `FACTORY_ROOT=…/scratchpad/froot-<n>`, a throwaway
`git init` repo, a fake `factory-task` injected with `FACTORY_BIN_OVERRIDE`, a
fake `dsh-openrouter` on `PATH`, and a `setsid` shim that logs its argv before
`exec`ing the real one. No real seat was launched at any point.

| case | expected | observed |
|---|---|---|
| **1** `factory-wave r1 <repo> "K1" --then 'integrate K1'` | seven fields, base = repo HEAD at launch, `then:` verbatim | all seven present, `then: integrate K1` verbatim; **`base: main`** — the branch name, not the HEAD sha (finding MAJOR-3) |
| **1** ordering: file exists before the first task starts | yes | yes — the fake `factory-task` recorded `K1: run.meta PRESENT at task launch` |
| **1** `pid:` is the driver's own pid and alive while it runs | yes | yes — `pid: 1476119`; `ps -o pid=,pgid=,sid= -p 1476119` → `1476119 1476119 1476119` while running |
| **1** `groups:` verbatim | yes | **no** — `"K1" "K2"` and `"K1 K2"` both yield `groups: K1 K2` (MAJOR-3) |
| **2** no `--then` | `run.meta` still written | written; `then: ` (key present, value empty). README does not say (MINOR-3) |
| **2** `--then ""` | documented, no crash | `then: ` (identical to the absent case); no crash; undocumented |
| **2** `--then $'a\nb\nc'` | documented, no crash | no crash, but run.meta gains three lines (`then: a` / `b` / `c`) — the one-key-per-line format is broken; `ritual.sh` takes `head -n 1` so it degrades quietly. Undocumented (MINOR-3) |
| **2** `--then` twice | documented, no crash | last wins (`then: second`); undocumented (MINOR-3) |
| **2** `--then` with no value | error, no `run.meta` | `factory-wave: --then needs a value`, rc 2, no `run.meta`. Correct |
| **3** launched from a non-session-leader shell | own sid = own pid ≠ launcher's | launcher sid 1476104; wave pid=pgid=sid=1476119. Detached, pid stable (exec in place, no fork) |
| **3** launched already a session leader (`setsid -w bash factory-wave …`) | no second re-exec | `setsid` shim log empty (0 lines); rc 0 |
| **3** run survives the launcher | yes | launcher pgroup 1485963 `kill -KILL -1485963`; wave 1485972 survived, reparented to pid 1991, ran to completion, wrote `K1.result` |
| **3** re-exec preserves env and argv | yes | `FACTORY_PLAN=/some/plan.md` and `MYVAR=keep me` arrived at the fake seat; `then: gate K1; ff; dispatch CR4` written verbatim through the re-exec |
| **3** launched as a process-group leader (interactive prompt) | contract kept | **broken** — launcher saw exit 0 in 0 s for a run that ended `status=failed`; summary printed asynchronously afterwards (MAJOR-1) |
| **4** marker present while gating, gone after success | yes | `gate marker present at seat time: YES`; gone, rc 0 |
| **4** …gone after failure | yes | gone after `verdict=reject` (rc 2) and after a seat exiting 7 with no verdict (rc 3) |
| **4** killed mid-review | reaped or documented | TERM/INT/HUP: EXIT trap fires, marker gone. **SIGKILL (and a reboot): marker stays**, contradicting the comment at `factory-review:63-64`. Nothing reaps it, nothing documents it (MINOR-4) |
| **5** live pid + log older than stale-after | listed as live | `rA K1 - pid 1512547 alive - log age 300m - then: integrate K1` — CR1b's pid branch, `tools/ritual.sh:202-203`, now reachable |
| **5** dead pid + old log | counted stale, not listed | `… and 1 stale logs older than 2h` (`tools/ritual.sh:204-207`) |
| **5** live gate, finished wave | gate visible as in flight | **`cr6 CR3.review - pid 1531451 DEAD - … - relaunch: factory-wave cr6 /home/dalhaka/nixos-agent-env CR3`** (MAJOR-2) |
| **6** README documents run.meta fields, `--then`, marker, detach rule | yes | yes — `README.md:39-41`, `69-79`, `88-91` |
| **6** README says the board's `setsid -f …` launch rule is now unnecessary | say whether | **it does not** — the README never mentions the board's launch rule (MINOR-6) |
| **7** shellcheck clean on the three scripts | yes | rc 0 |
| **7** `factory_route`, model/effort resolution, pre-existing tests unchanged | yes | untouched by the diff; tests 1–28 identical to main's and green |

## Checks

Run in the fresh clone `…/scratchpad/gate-cr6-CR3` at 008cf15.

| check | rc | wall |
|---|---|---|
| `nix develop -c shellcheck tools/factory/seat/{factory-wave,factory-review,factory-lib.sh}` | 0 | 1.8 s |
| `nix develop -c bats tests/unit/80-seat-driver.bats` | 0 (31/31) | 4.5 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 | 1.1 s (cached) |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0 (195/195) | 28.8 s |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 | 1.1 s |
| `nix develop -c githooks/pre-commit` | **1** | 3.4 s |

The `pre-commit` failure is not a CR3 defect. Its only output is

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
```

and the regenerated diff is exactly `-… B1 CR3 OG1r2b …` → `+… B1 OG1r2b …`: with CR3's commit present, `tasks.py` derives CR3 as landed while the committed board block still queues it. Controls: the same hook at base 4b96f7c in the same clone exits 0; at 008cf15 with the block regenerated it exits 0 ("All checks passed", 34 files already formatted, `render.test.mjs` assertions passed). Every task branch that completes a queued key trips this in a standalone clone; the board is regenerated on `main` after the fast-forward.

## Red before green

`git show 4b96f7c:tools/factory/seat/factory-wave` and `…:factory-review` written
over CR3's, CR3's tests kept, `nix develop -c bats tests/unit/80-seat-driver.bats`:

```
ok 1..28   (unchanged, all pass)
not ok 29 factory-wave writes run.meta recording the run's identity and --then intent
#   `[ -f "$root/runs/r1/run.meta" ]' failed
not ok 30 factory-wave re-execs under setsid when it is not a session leader
#   `[ "$status" -eq 0 ]' failed
not ok 31 factory-review leaves a <KEY>.gate marker while gating and removes it after
#   `[[ "$output" == *"gate-present"* ]]' failed
```

Restored (`git checkout -- tools/factory/seat/`, tree clean): 31/31 green. All
three new tests are load-bearing; the 28 pre-existing tests are untouched.

## Mutation table

Applied to the clone, tree-change asserted by `git diff --stat` before each run,
reverted after. 6 killed / 8.

| # | mutation | file | died? | failing test |
|---|---|---|---|---|
| M-A | delete the `run.meta` write block | factory-wave:100-108 | yes | 29 |
| M-B | drop the `then:` printf | factory-wave:107 | yes | 29 |
| M-C | `printf 'pid: %s\n' 0` | factory-wave:105 | **NO** | — (31/31 still green) |
| M-D | remove the `setsid` re-exec block | factory-wave:46-51 | yes | 30 |
| M-E | re-exec unconditionally (`if true`) | factory-wave:48 | yes | 29 |
| M-F | never create the gate marker | factory-review:66 | yes | 31 |
| M-G | drop the EXIT trap (marker never removed) | factory-review:67 | yes | 31 |
| M-H | write `run.meta` after the dispatch loop | factory-wave:100-108 → after `wait` | **NO** | — (31/31 still green) |

M-D dying answers the plan's "§5's seat-driver tests red first" for detach at the
argv level (test 30 pins that `setsid -- <script> <argv>` is invoked with the
arguments verbatim). Real detach cannot be observed inside the bats sandbox; I
proved it by hand instead (matrix row 3), so the behaviour is covered, just not
by bats. That is acceptable, not a finding.

## Findings

### MAJOR-1 — the `setsid` re-exec throws away the wave's exit code and summary whenever the launcher gives it its own process group

`tools/factory/seat/factory-wave:49` — `exec setsid -- "$0" "$@"`.

`setsid(2)` fails for a process-group leader, so util-linux `setsid(1)` forks
when `getpgrp() == getpid()`; without `-w` the parent exits 0 the instant the
child is started. A foreground command typed at an interactive prompt *is* a
process-group leader (job control puts it in its own group), and that is exactly
the invocation `tools/factory/seat/README.md:110` prints:

```
tools/factory/seat/factory-wave "$run" "$repo" "N1" "N2" "N10" "N11 N3 N6" "N5 N8"
```

while `README.md:79`, in the paragraph this commit rewrote, still promises
"exits non-zero if any task did not reach `status=done`". Measured, with a fake
`factory-task` that sleeps 4 s and writes `status=failed`:

```
$ bash -c 'set -m
    FACTORY_ROOT=… FACTORY_BIN_OVERRIDE=…/failbin \
      bash …/factory-wave r3d …/repo K1 --then x
    echo "WAVE EXIT CODE SEEN BY LAUNCHER = $?"'
WAVE EXIT CODE SEEN BY LAUNCHER = 0
elapsed = 0 s  (fake task sleeps 4 s)
--- setsid shim log ---
setsid-called: -- …/factory-wave r3d …/repo K1 --then x
--- run.meta pid vs what ran ---
cat: …/froot-3d/runs/r3d/run.meta: No such file or directory     <- not written yet
factory-wave: run 'r3d': 1 group(s), FACTORY_JOBS=5              <- arrives later, asynchronously
K1 status=failed checks=unit=fail commits=0 minutes=0.0 tokens=-
```

The launcher gets `0` for a failed run, in 0 s, before `run.meta` even exists.
The house recipe (`setsid -f bash -c 'exec … factory-wave …'`) and the
orchestrator's Bash tool both happen to escape this — in the first the wave
*is* the session leader so no re-exec fires, in the second there is no job
control so `setsid` execs in place — but the operator's own documented
invocation does not, and nothing warns.

**Fix:** `exec setsid -w -- "$0" "$@"`. Verified on a copy: exit code 1
preserved, launcher blocked the full 4 s, summary printed synchronously — and
the detach is unaffected (wave pid 1624083 had pgid=sid=1624083, survived
`kill -KILL -<launcher pgid>`, and wrote its `.result`). Add a bats case that
pins a non-zero wave exit through the re-exec path.

### MAJOR-2 — `run.meta`'s pid makes the in-flight table report a *running* gate as DEAD, with a relaunch hint for an already-landed task

`tools/factory/seat/factory-wave:105` (`printf 'pid: %s\n' "$$"` — the wave's
pid, one per run) meets `tools/ritual.sh:202-210`, which globs `"$runs_dir"/*/*.log`
and applies the run's `pid:` to every log in the directory. `factory-review:160`
writes `$runs_dir/$key.review.log`, which matches that glob and has no
`.review.result` — and its lifetime is independent of the wave's.

Fixture: run `cr6` with `CR3.log` + `CR3.result` (wave finished, its pid dead)
and a fresh `CR3.review.log` + `CR3.gate` (a gate running right now):

```
$ FACTORY_ROOT=…/froot-6 bash tools/ritual.sh inflight <repo>
cr6 CR3.review - pid 1531451 DEAD - log age 0m - then: gate CR3; integrate; ff - relaunch: factory-wave cr6 /home/dalhaka/nixos-agent-env CR3

$ mv run.meta run.meta.off      # pre-CR3 behaviour, same fixture
cr6 CR3.review - running - log age 0m
```

"log age 0m" and "DEAD" in the same line. This is the standard sequence in this
repo — wave lands, wave exits, orchestrator gates the key — so the first thing
CR3 makes CR1b's pid branch say is wrong, and the derived `relaunch:` would
re-dispatch a paid seat for work that already landed. Symmetrically, while the
wave is alive every unfinished key reads `alive` even if its own seat died.

**Fix:** make the liveness record per-key rather than per-run — either
`factory-review` writes its own `<KEY>.review.meta` with its pid (and
`ritual.sh` prefers a per-key meta), or `factory-wave` records
`pid-<KEY>:` lines and `ritual.sh` looks up the key it is reporting. Cheapest
interim: teach `ritual.sh` to ignore `*.review.log` for the run-level pid and
fall back to mtime for it, and put the gate's pid in the `.gate` marker
(see MINOR-4). Whichever, add the fixture above as a bats case.

### MAJOR-3 — `run.meta`'s `base:` is a branch name, not the HEAD, and `groups:` is lossy

`tools/factory/seat/factory-wave:96-99, 104`.

`base:` is `git symbolic-ref --short -q HEAD` with a `rev-parse HEAD` fallback
only for a detached head, so a normal run records `base: main`:

```
run: r1
repo: …/fx1/repo
base: main            <- repo HEAD at launch was 658c923f34002d3ebeabc08dcdf1d26e9d11c0ca
groups: K1
```

A branch name is a moving target — after a fast-forward it no longer names the
commit the run forked from, which is the only thing `base:` is useful for after
a reboot. It also collides with the neighbouring file's field of the same name:
`factory-task:288` writes `base: <sha>` into `<KEY>.result`, so two files in one
directory use `base:` for two different things. The required matrix defines the
field as "the repo's HEAD at launch"; the plan text does not define it, so if
the branch name is what was intended, say so and this drops to a minor.

`groups:` is `${groups[*]}`, a space-join, so the group *structure* is lost:

```
factory-wave r8 <repo> "K1" "K2"    ->  groups: K1 K2
factory-wave r8 <repo> "K1 K2"      ->  groups: K1 K2
```

`ritual.sh:210` builds `relaunch: factory-wave $run $repo_meta $groups`
unquoted, so a killed *chain* `"K1 K2"` is relaunched as two parallel groups —
K2 dispatched from a workspace that never saw K1's commit, which is the exact
failure `factory-wave:8-11` exists to prevent. The README's own example
(`README.md:110`) contains such a chain (`"N11 N3 N6"`).

**Fix:** `base: $(git -C "$repo_path" rev-parse HEAD)` (append the branch name
if it is wanted for readability, e.g. `base: <sha> (main)`), and write one
`group:` line per group (or quote each group) so the structure round-trips.
Extend test 29 to a two-group and a one-chain invocation and assert they differ.

### MINOR-1 — `pid:`'s value is unpinned, and the wrong value fails open

Mutation M-C (`printf 'pid: %s\n' 0` at `factory-wave:105`) leaves 31/31 green:
`tests/unit/80-seat-driver.bats:1430` asserts only `[[ "$output" == *"pid: "* ]]`.
This matters because `kill -0 0` succeeds — it signals the caller's own process
group — so `pid: 0` would make `ritual.sh:202` report every run `alive` forever,
the failure mode that hides a dead run instead of showing it. **Fix:** capture
the value (`p=$(sed -n 's/^pid: //p' …)`) and assert `kill -0 "$p"` succeeds
while the wave runs, or that it equals the pid bats observed.

### MINOR-2 — "written before the first task starts" is unpinned

Mutation M-H (move the `run.meta` block to after `wait`) leaves 31/31 green.
The spec's whole point is "in-flight intent is written **at dispatch time**",
and the behaviour is correct today — my fake `factory-task` recorded
`K1: run.meta PRESENT at task launch` — but nothing stops a later edit from
reordering it. **Fix:** the fake `factory-task` in test 29
(`tests/unit/80-seat-driver.bats:1404-1419`) already runs at the right moment;
have it append `present`/`absent` for `$FACTORY_ROOT/runs/$1/run.meta` to a file
and assert `present`.

### MINOR-3 — `--then`'s edge cases are undocumented, and a multi-line value breaks run.meta's format

`tools/factory/seat/factory-wave:59-63, 107`. Absent and `--then ""` both write
`then: ` (empty value, key present); `--then` twice silently takes the last; a
value containing newlines emits extra bare lines into a file whose contract is
one `key: value` per line (`ritual.sh` survives it via `head -n 1`, but any
stricter reader will not). `README.md:69-79` documents none of these.
**Fix:** one README sentence (single-line text, last `--then` wins, absent =
empty) and either reject or fold newlines in the value.

### MINOR-4 — the `.gate` marker has no consumer, no pid, and no staleness rule

`tools/factory/seat/factory-review:61-67`. Nothing reads `*.gate`: `ritual.sh`'s
`inflight` iterates `<KEY>.log` only, and `grep -rn '\.gate' tools/ pkgs/ tests/`
finds only the writer, the README and the new bats case. The comment at
`factory-review:63-64` — "Removed on every exit path below (the trap), never
left behind as a stale 'still gating'" — is false for `SIGKILL` and for the
reboot the spec cites as the motivating incident:

```
kill -TERM  -> marker GONE      kill -INT  -> marker GONE
kill -HUP   -> marker GONE      kill -KILL -> marker PRESENT (stale)
```

The marker is an empty file, so a future consumer cannot tell a live gate from a
reboot leftover except by mtime. **Fix:** write the gate's pid into the marker
(`printf '%s\n' "$$" > "$gate_marker"`), soften the comment to name the SIGKILL
case, and say in the README how a stale marker is recognised. Doing this also
gives MAJOR-2 its cheapest fix.

### MINOR-5 — test 30 can reach the real `factory-task`, against the file's own promise

`tests/unit/80-seat-driver.bats:1454` sets `PATH` and `FACTORY_ROOT` but **not**
`FACTORY_BIN_OVERRIDE`, unlike test 29 at line 1421. Only the fake `setsid`
exiting 0 before the dispatch loop keeps the real `$FACTORY_BIN/factory-task`
from running. Reproducing that state by hand (main's `factory-wave`, no
override), the real driver cloned repos and created three workspaces
(`ws/r1/--then`, `ws/r1/gate`, `ws/r1/K1`) and stopped one step short of the
seat only because the fixture repo has no plan file:

```
factory-brief: no such file: …/fx7repo/docs/superpowers/plans/2026-09-04-dsh-review-fix-round.md
```

`dsh-openrouter` *is* on the devShell PATH
(`/nix/store/4va93cxln3wp11d7bqqrz74anzrzyvah-dsh-openrouter/bin/dsh-openrouter`),
and the file header (lines 10-13) promises "nothing here ever touches the
operator's real ~/factory or the network". **Fix:** add
`FACTORY_BIN_OVERRIDE="$fact"` (or an empty stub bin) to test 30.

### MINOR-6 — the README does not retire the board's `setsid -f` launch rule

`tools/factory/seat/README.md:69-79` describes the detach but never says the
orchestrator can stop wrapping launches in `setsid -f bash -c 'exec …'`, which
is what the board's START HERE currently mandates. The point of CR3's G1 half is
that the wrapper becomes the driver's job; without a sentence saying so, the
hand-written rule stays. **Fix:** one sentence in the `factory-wave` bullet, and
a matching board edit at landing.

### MINOR-7 — one-line window between creating the marker and arming the trap

`tools/factory/seat/factory-review:66-67` — `: >"$gate_marker"` then
`trap … EXIT`. A signal between the two leaves the marker. **Fix:** set the
trap first, then create the marker.

## Landing note

**Landing does not need to wait for an idle driver.** The concern is real in
principle — bash reads a script incrementally, and the live host runs the driver
from this checkout — but `git` never rewrites a tracked file in place; it writes
a new file and renames over it, so a running `bash` keeps its old inode open.
Measured, in a throwaway repo, with a 6-second script running while
`git merge --ff-only` swapped in a longer version:

```
inode before: 243540518
A start inode=243540518
--- git merge --ff-only v2 while s.sh is running ---
inode after : 243539920            <- new inode
A end -- the OLD script body ran to completion
running script exit=0
```

For contrast, an in-place byte overwrite of the same inode does corrupt the
running script (`unexpected EOF while looking for matching '"'`, exit 2) — but
nothing in the integrate → fast-forward recipe does that.

Two consequences to carry, not blockers:

- A `factory-wave` or `factory-review` already executing when CR3 lands keeps the
  **old** body for its whole life: no `run.meta`, no detach, no `.gate` marker.
  Those runs stay invisible to the ritual's pid branch until they are relaunched,
  degrading to CR1b's mtime rule — which is the documented pre-CR3 behaviour, so
  nothing regresses.
- `factory-wave` spawns `$FACTORY_BIN/factory-task` as a fresh process per key,
  so a task dispatched after the landing runs the new file. CR3 touches neither
  `factory-task` nor `factory-lib.sh`, so no mixed-version hazard exists there.

If MAJOR-2's fix lands in `tools/ritual.sh`, note that `ritual.sh` runs from the
checkout on every `SessionStart` and `Stop`, i.e. it is re-read per invocation —
no such caution needed.

## Verdict

**REJECTED** — three MAJORs. MAJOR-1 (`setsid` without `-w` discards the wave's
exit code and summary on the README's own documented invocation) and MAJOR-2
(the run-level pid makes the in-flight table call a live gate DEAD and offer to
relaunch a landed task) are behavioural defects in the paths this task exists to
serve; MAJOR-3 is `run.meta` not carrying what its two consumers need. All three
are small edits — `setsid -w`, a per-key liveness record, `rev-parse HEAD` plus
a per-group line — plus the two coverage gaps M-C and M-H, so a fix round should
be short. Everything else about the task is in good shape: correct scope, exact
commit convention, genuine red-before-green, 6/8 mutants killed, and the detach
and marker behaviours verified working by hand outside bats.
