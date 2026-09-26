---
reviewer: opus
majors: 1
minors: 6
mutants_total: 37
mutants_killed: 36
---
# Opus gate — seat run cr16, task CR3rb — APPROVED

## Summary

CR3rb is one commit (`a4efc86`) on `task/CR3rb`, base `c6f5928` (main), seven
files, all inside the plan's `touches`, subject byte-identical to CR3's, both
trailers present and in order. It is the fix round for the cr14 gate's single
MAJOR plus its seven minors, and **the MAJOR is genuinely closed**: the
`gate_done` test now sits *below* the stale-after cut (`tools/ritual.sh:347-362`),
so a finished review gate older than the threshold folds into the stale summary
instead of being listed forever. Measured live, read-only, on this host:
**398 bytes / 10 lines, zero `gate done` lines**, the live seat run `sb7 SB4`
present, against the 1,200-char `SESSION_START_CAP_INFLIGHT` budget — cr14's
1518-byte overflow is gone. A second probe an hour earlier read 562 bytes / 14
lines, also zero `gate done`; the implementer's claimed 595 is the same number
at a third moment (it moves with the runs dir), so treat the byte count as a
range, not a constant.

The other five contract items are met and each is proved by a discriminating
fixture of mine, not only by the suite: the commits-mismatch arm now fires only
on a `status=done` claim, appends to the seat's own notes and keeps
`exit_code=`; `--then` and groups round-trip through `%q` byte-for-byte in both
directions and a newline/tab/control byte is refused at write time with exit 2
and one message per offending value, nothing written; the recycled-pid test is
now decided by the fake `ps` alone (I ran the same fixture under the real `ps`
and got the opposite verdict); the locals are fixed and nothing leaks.

Checks are green: shellcheck on all five scripts (and `-o all` on `ritual.sh`),
107/107 bats across the three files, `unit` (327 tests, also with `--rebuild`),
`lint`, and `pre-commit` modulo the known stale-queue-block artefact. Red before
green is honest: **7 tests red** on CR3r's own driver/reader files with CR3rb's
tests. **36 of 37 mutations die** — CR3rb's own seven, cr14's fourteen, cr9's
eleven, four CR5 spot checks. The one survivor is M-E (a `local` dropped), which
`shellcheck -o all` cannot detect at all; the required *state* is met and I
verified it at runtime instead (MINOR-1).

No MAJOR. Six minors, all cosmetic or unpinnable.

## Rule behaviour

Fixtures: throwaway `FACTORY_ROOT` trees under
`…/scratchpad/fx1|fx2|fx3|fx5`, throwaway `git init` repos, `FACTORY_BIN_OVERRIDE`
fakes for `factory-task`, a fake `dsh-openrouter` on `PATH`, copied seat
directories with stub `factory-ws`, fake `ps`/`setsid`. No real seat, no write
anywhere under `~/factory` — `~/factory/runs` held **zero** `*.pid`/`*.gate`
files before and after both live probes (`diff` of the two listings: identical),
and the `ws/cr16/CR3rb` and `ws/cr14/CR3r` mtimes are untouched.

| row | fixture | expected | observed |
|---|---|---|---|
| **1** live-shaped: 23 `K.review.log` aged 3 h each with `K.review.md`, plus a seat log with an alive `K.pid`, a fresh review log with a live `K.gate`, and a plain fresh log | ≤ 1200 chars, three live keys present, **0** `gate done`, 23 counted stale | **148 bytes, 4 lines**; `L1 SEATKEY - pid 1853716 alive`, `L2 GK.review - running`, `L3 PLAIN - running`, `… and 23 stale logs older than 2h`; `gate done` count **0** |
| **1b** a **young** review log with `.review.md` beside the same 23 | listed as `gate done` | `Y1 YK.review - gate done - log age 0m` (and still `… and 23 stale logs`) |
| **2a** seat claims `done exit_code=7`, `COMMITS 1`, branch has 0 | failed, notes appended, `exit_code=` kept | `FACTORY-RESULT status=failed exit_code=7` / `FACTORY-NOTES landed the change; unit green; claimed 1 commits, found 0`, rc 2 |
| **2b** seat claims `failed`, `COMMITS 0`, branch has 1 checkpoint commit | not rewritten | `FACTORY-RESULT status=failed` / `FACTORY-NOTES the unit check failed on tests/unit/80; see the log`, no `claimed` clause, rc 2 |
| **2c** seat claims `done`, `COMMITS 1`, branch has 2 (a stray board commit) | failed, names it | `status=failed` / `… unit green; claimed 1 commits, found 2`, rc 2 |
| **2d** seat claims `done`, `COMMITS 1`, branch has 1 | done | `FACTORY-RESULT status=done`, notes intact, rc 0 |
| **3a** group `a"b\c` + `--then 'say "hi"; ff'` through `factory-wave` → `run.meta` → the hint → re-parsed as argv | byte-identical both ways | `run.meta`: `group: a\"b\\c`, `then: say "hi"; ff`; hint: `… a\"b\\c --then say\ \"hi\"\;\ ff`; re-parsed `$3` = `a " b \ c`, `$5` = `say "hi"; ff` — **IDENTICAL** (od bytes compared) |
| **3b** group with a newline / a tab / `--then` with a newline | exit 2, one line each, nothing written | rc 2 each; `factory-wave: group 1 holds a byte %q cannot round-trip …; refused` (and `group 2 …`, `--then …` when all three are bad — three lines, one per value); **no run dir at all** |
| **3c** the reader's eval-free unquote over 16 awkward values `%q` lets through (`'`, `` ` ``, `$`, `*`, `!`, `;`, `(`, spaces, `\`, UTF-8) | all round-trip | 16/16 `round-trip OK`; only the `$'…'` forms are refused upstream |
| **4** `shellcheck -o all tools/ritual.sh` | no new global | only style codes: 191 × SC2250, 57 × SC2292, 21 × SC2312, 2 × SC2249 — **and identical before/after M-E**, see MINOR-1. Runtime probe instead: after `inflight_stdout` returns, `stale_pid_count`, `gline`, `ps_epoch`, `file_epoch`, `meta`, `live` are all **UNSET** in the caller; `local ps_epoch file_epoch` is gone (`ritual.sh:264-268`, and `ps_epoch` now only inside `pid_recycled` at `:243`) |
| **5** recycled pid: pid file mtime NOW, an alive `sleep` pid, fake `ps` +60 s | not alive | `… and 1 stale logs older than 2h` |
| **5b** same, fake `ps` −60 s | alive | `r1 K - pid 1855434 alive - log age 180m` |
| **5c** same fixture, **real** `ps` (real lstart 22:35:46 vs file mtime 22:35:47) | would say alive | `r1 K - pid 1855464 alive - log age 180m` — the fake alone decides the outcome |
| **6** README | six items | `<KEY>.pid` + its reaping (`README.md:38-42`), `<KEY>.gate` (`:44-45`), `run.meta` (`:46-52`), the commit check's two outcomes (`:80-92`), the reaper + `… and N stale pid files` + the recycled-pid denial + `gate done` (`:130-140`) — all present |
| **7** CR3r's rows | still hold | the four discriminating in-flight shapes (67–70), marker ordering structural + FIFO-behavioural (39, 40), the hint only when the wave pid is dead and never beside alive (60, 73), the mixed wave (72), the reaper age case (75), `setsid -w` exit code (32) and the launcher-SIGKILL survival (33) — all green in the devShell; 32/33 still `# skip` **inside** the `unit` derivation ("no real setsid/ps in this sandbox"), unchanged from cr14 |
| **8** CR5 + CR1b | intact | `90-session-start.bats` 16/16 and `92`'s CR5 block green; `session-start.sh` is not in the diff at all; `ritual.sh`'s diff is three hunks, all inside `inflight_stdout`/its helpers; four CR5 mutations re-killed (below) |
| **9** live probe, read-only | ≤ 1200, no old `gate done`, current runs present, nothing reaped | **398 bytes / 10 lines**, `gate done` = 0, `sb7 SB4 - running - log age 2m` present, `… and 217 stale logs older than 2h`; `*.pid`/`*.gate` count 0 before and 0 after, listings identical |

Live output (probe 2, 23:14):

```
cr12 wave-group-1 - running - log age 116m
cr14 wave-group-1 - running - log age 101m
cr15 wave-group-1 - running - log age 64m
cr16 wave-group-1 - running - log age 45m
cr17 wave-group-1 - running - log age 6m
sb6 integrate - running - log age 57m
sb6 wave-group-1 - running - log age 89m
sb7 SB4 - running - log age 2m
sb7 wave-group-1 - running - log age 2m
… and 217 stale logs older than 2h
```

## Checks

Run in the fresh clone `…/scratchpad/gate-cr16-CR3rb` at `a4efc86`.

| check | rc | note |
|---|---|---|
| `nix develop -c shellcheck factory-wave factory-review factory-task factory-lib.sh tools/ritual.sh` | 0 | 2.0 s |
| `nix develop -c shellcheck -o all tools/ritual.sh` | 0 | style codes only (see rule row 4) |
| `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats` | 0 | **107/107**, 17.3 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 | cached |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0 | **327 ok, 0 not ok**; 8 skips (6 mount + tests 172/173) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 | |
| `nix develop -c githooks/pre-commit` | **1** → 0 | known artefact: sole output `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the regenerated diff is exactly `… B1 CR2r CR3rb PW1glm …` → `… B1 CR2r PW1glm …` (CR3rb's own commit satisfies it). Re-run with the block staged: `All checks passed!`, `render.test.mjs: all assertions passed`, rc 0 |

Commit convention: exactly **1** commit (`git rev-list --count c6f5928..HEAD` = 1);
subject byte-compared against the plan's — `IDENTICAL`; `Generated-By: dsh
0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run cr16)`
then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`; the seven
changed files are exactly the plan's `touches`. Tests-only deletions: 4 lines,
the CR1b `inflight reports a dead pid with a relaunch hint` test superseded by
CR3b's live-by-rule behaviour (already accepted at cr9/cr14) — no assertion was
weakened; test 60's `--then` assertion was *tightened* from the hand-quoted form
to the `%q` form the contract now requires.

## Red before green

CR3r's four driver/reader files (`git -C /home/dalhaka/factory/ws/cr14/CR3r show
task/CR3r:<path>`; `factory-review` is byte-identical, so three files change)
under CR3rb's tests, `bats tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats`
(1–45 driver, 46–91 ritual): **7 red**, exactly the ones the plan's Step 1 names.

```
not ok 35 factory-wave refuses a group or --then whose byte %q cannot round-trip (exit 2)
not ok 42 factory-task demotes status=done when the FACTORY-COMMITS claim does not match the branch
not ok 43 factory-task leaves a failed run's own notes intact, not overwritten by the commit check
not ok 60 inflight reports a dead wave as live-by-rule with a relaunch hint that reproduces the argv
not ok 71 inflight's relaunch hint reproduces the original argv including --then
not ok 78 inflight counts an aged finished gate as stale, never listing it
not ok 79 inflight keeps 23 aged finished gates under the 1200-byte cap, folded into the stale count
```

Test 76 (recycled pid, the fake-`ps` case) is **green** on CR3r, and that is
correct: cr14's MINOR-5 was that the *fixture* did not exercise the fake, not
that the code was wrong. Its load-bearing property is pinned by M-D instead
(the fake ignored → 76 fails), which dies. The seat's own log reasons this out
explicitly rather than fudging a red, which I checked (`cr16/CR3rb.log:1239+`).

Restored (`git restore tools/`, tree clean): 91/91 green again.

## Mutation table

Applied to the clone, `git diff --stat -- tools/` asserted non-empty before each
run, `bats 80 + 92` under `timeout`, `git restore tools/` after. Numbering is
that combined run.

**CR3rb's own — 7 of 8 die.**

| # | mutation | site | died? | failing tests |
|---|---|---|---|---|
| M-A | `gate done` branch moved back above the stale cut | ritual.sh:352-359 | yes | 78, 79 |
| M-B | commit check fires for any status (`[ "$status" = "done" ]` dropped) | factory-task:249 | yes | 43 |
| M-B2 | NOTES replaced instead of appended | factory-task:257 | yes | 42 |
| M-B3 | `result_line="FACTORY-RESULT status=failed"` (exit_code dropped) | factory-task:277 | yes | 42 |
| M-C | `--then` hand-double-quoted in the hint | ritual.sh:395 | yes | 60, 71 |
| M-C2 | the `$'…'` refusal removed (`exit 2` neutered) | factory-wave:118 | yes | 34, 35 |
| M-D | the fake `ps` ignored (absolute store `ps` in `process_epoch`) | ritual.sh:234 | yes | 76 |
| M-E | `stale_pid_count` dropped from the `local` list | ritual.sh:265 | **survived** | none — and `shellcheck -o all` output is byte-identical before/after. See MINOR-1 |

**cr14's table (CR3r), re-applied — 14 of 14 die.**

| # | mutation | died? | failing tests |
|---|---|---|---|
| M-A | `pid=$wave_pid` unconditionally | yes | 67, 68, 69, 70, 73, 79 |
| M-A2 | `<KEY>.gate` arm never read | yes | 69, 70 |
| M-A3 | `<KEY>.pid` arm never read | yes | 67, 68, 73, 79 |
| M-B | trap and marker write swapped | yes | 39, 40 |
| M-C | `--then` dropped from the hint | yes | 60, 71 |
| M-D | hint printed regardless of a live per-key seat | yes | 73 |
| M-E | `group: %q` → `%s` | yes | 29, 30, 41 |
| M-F | reaper age check removed | yes | 67, 69, 75 |
| M-F2 | reaper glob emptied | yes | 75 |
| M-G | recycled-pid guard removed | yes | 76 |
| M-H | `gate done` → `running` | yes | 77 |
| M-I | commit verification block disabled | yes | 42, 44, 45 |
| M-I2 | bare-`ok` rejection removed | yes | 45 |
| M-J | `setsid -w` → `setsid` | yes | 31, 32 |

**cr9's table — 11 of 11 die** (M-A = cr14's M-J, M-B = cr14's M-A, M-H =
cr14's M-B, already above).

| cr9 # | mutation | died? | failing tests |
|---|---|---|---|
| M-C | DEAD printed for a fresh log with a dead pid | yes | 60, 61, 66, 72 |
| M-D | `base:` back to `symbolic-ref --short` | yes | 29 |
| M-E | groups space-joined (`${groups[*]}`) | yes | 29, 30, 41 |
| M-F | `pid:` written as 0 | yes | 29 |
| M-G | `run.meta` block moved after the dispatch loop | yes | 29 |
| M-I | `<KEY>.pid` EXIT trap deleted | yes | 36 |
| M-J | hint printed regardless of landed keys | yes | 72, 77 |
| M-K | re-exec applied even when already a session leader | yes | 29, 30 |

**CR5 spot checks** (`bats 92 + 90`, numbering 1–46 = `92`): `ritual.sh`'s diff
is three hunks confined to `inflight_stdout` and its helpers and
`session-start.sh` is untouched, so a CR5 regression is structurally impossible;
measured anyway.

| CR5 # | mutation | died? |
|---|---|---|
| M-A | board check back to the packaged `evidence` | yes (4, 36, 37, 40, 41) |
| M-C | `stop_hook_active` guard removed | yes (38) |
| M-F | `RITUAL_PYTHON` ignored | yes (40) |
| M-G | wrapper-parsing fallback removed | yes (41) — note my first attempt removed only the `exec …` half and survived because the `PATH=` half still resolves; removing the whole fallback kills 41 |

**Score: 36 of 37.** The single survivor is M-E; see MINOR-1 for why nothing can
kill it and what I checked instead.

## Findings

No MAJORs.

### MINOR-1 — contract item 4's mutation clause is unfulfillable; the `local` fix is real but unpinned

`tools/ritual.sh:264-268`

The state item 4 asks for is met, and I checked it three ways rather than
trusting the diff:

```
local meta live stale_after stale_count stale_pid_count wave_pid
local pfile ppid pfile_mt pidfile gate_done live_seat group_done k gline
```

— `stale_pid_count` and `gline` are declared; the dead `local ps_epoch
file_epoch` is gone (those two names live only in `pid_recycled`,
`ritual.sh:243`); and a runtime probe (a copy of the script with a `declare`
line appended after the call) reports every one of `stale_pid_count`, `gline`,
`ps_epoch`, `file_epoch`, `meta`, `live` as **UNSET** in the caller after
`inflight_stdout` returns.

What cannot be done is the mutation the plan's table asks for. ShellCheck has no
"this is a global" check at any `-o` level: `shellcheck -o all -f gcc
tools/ritual.sh` emits 271 lines of pure style (SC2250 braces, SC2292 `[[ ]]`,
SC2312 masked return, SC2249 default case) and its output is **byte-identical
before and after** dropping `stale_pid_count` from the `local` line, while no
test fails either. So M-E survives by construction, not by a coverage gap the
implementer could have closed with the named tool. If the operator wants it
pinned, the cheap way is a test that sources `ritual.sh` in a subshell, calls
`inflight_stdout`, and asserts the names are unset — the probe above, promoted
to bats.

### MINOR-2 — a dead `result_block` assignment left behind by the reordering

`tools/factory/seat/factory-task:238`

```sh
result_block=$(printf '%s\n%s\n%s\n%s' "$result_line" "$checks_line" "$commits_line" "$notes_line")
```

`head_sha`/`base_sha` moved up and the commit check now rewrites `result_line`
and `notes_line` after this line, so the value is recomputed at `:289` before
its only use at `:318`. The first assignment is dead. Harmless, invisible to
shellcheck, one line to delete.

### MINOR-3 — an empty NOTES body produces a leading `; ` in the appended clause

`tools/factory/seat/factory-task:257`

A seat whose final block carries a bare `FACTORY-NOTES` header with no text
(non-empty line, empty body — so the `(none given)` fallback at `:237` does not
fire) records:

```
FACTORY-NOTES ; claimed 1 commits, found 0
```

Measured on the fixture `done_emptynotes_claim1_actual0`. Degenerate input, no
information lost, but the separator should be conditional on a non-empty
`notes_body`.

### MINOR-4 — the README's refusal sentence is narrower than the code, and the wave bullet loses the list indent

`tools/factory/seat/README.md:104` says only "a value containing a newline is
refused (exit 2)". The code refuses a newline, a tab, **or any byte `%q` must
octal-escape**, and it refuses it in a **group** as well as in `--then` — which
is the half the reader's unquote actually depends on. Also, the rewritten
`factory-wave` and `factory-dispatch` bullets (`:90-120`) drop the two-space
continuation indent every other bullet in the file uses; it still renders, but
the file no longer looks like one document.

### MINOR-5 — the reaper can print an arithmetic error if a pid file vanishes mid-scan

`tools/ritual.sh:283`

```sh
pfile_mt=$((now - $(stat -c %Y "$pfile")))
```

If the file disappears between the glob and the `stat` (a seat exiting while the
hook reads), `stat` prints nothing and bash reports an arithmetic syntax error
on stderr. Pre-existing from CR3r, not introduced here, and invisible in
practice because `session-start.sh:121` redirects the reader's stderr; noted so
it is not lost. One `|| continue` fixes it.

### MINOR-6 — the live byte count is a moving number, not a fact

The implementer's notes say "live probe 595 bytes". I measured 562 bytes / 14
lines at 22:35 and 398 bytes / 10 lines at 23:14 — the difference is entirely
which runs had finished. All three are far under the 1,200-char budget and all
three have zero `gate done` lines, which is what the contract asks; the number
itself should not be quoted anywhere as a constant.

## Landing note

**Landing CR3rb while `sb7` (launched by the OLD driver) is live is safe**, and
safer than CR3r was.

- **Running processes are unaffected.** `git merge --ff-only` writes a new file
  and renames over it, so every in-flight `factory-wave` / `factory-task` /
  `factory-review` keeps its old inode and its old body for its whole life.
  `sb7 SB4` and `sb7 wave-group-1` are both live right now (probe 2) and neither
  re-reads its script.
- **A `factory-task` spawned *after* the landing by `sb7`'s *old* wave still
  works.** `FACTORY_BIN` resolves to the directory of `factory-lib.sh`
  (`factory-lib.sh:23`), i.e. the repo tree, so the old wave invokes the **new**
  `factory-task`. The call is unchanged
  (`"$FACTORY_BIN/factory-task" "$run" "$repo_path" "$key" [--after "$prev"]`),
  the new script adds no required input, and the old wave parses the result with
  `sed -nE 's/^FACTORY-RESULT[[:space:]]+status=([a-zA-Z_-]+).*/\1/p'`
  (`c6f5928:factory-wave:102`), which tolerates the `exit_code=` this round now
  **preserves**. The only behavioural consequence is the intended one: a key
  dispatched after the landing that reports `done` with a commit count the branch
  does not support is demoted to `failed`, and the old wave's chain stops there.
  CR3rb narrows this strictly compared with CR3r — the arm no longer fires on a
  run the seat itself called `failed`, so a failing seat's own diagnosis
  survives.
- **The reader half is immediate and now safe.** `tools/ritual.sh` is re-read on
  every `SessionStart`/`Stop`/`PreCompact`, so the fix takes effect with the
  merge: measured live at 398 bytes with zero `gate done` lines, comfortably
  inside `SESSION_START_CAP_INFLIGHT=1200`. This is the reason cr14 said "fix
  before landing"; it is fixed.
- **Old runs degrade correctly and nothing is deleted.** `sb7` and every other
  pre-CR3r run has no `run.meta`, no `<KEY>.pid`, no `<KEY>.gate`; those keys
  read by CR1b's mtime rule (verified live — no `DEAD` lines, `sb7 SB4 -
  running`). The reaper globs `runs/*/*.pid` and `runs/*/*.gate`, of which the
  real dir has **none** — counted before and after both probes, identical — so
  landing deletes nothing.
- **The new refusal cannot bite a running wave.** It is a write-time check in
  `factory-wave`'s argument parse; task keys are alphanumeric and `--then`
  values are one-line prose, so the only thing it can reject is a value the
  reader could not have round-tripped anyway.

## Verdict

**APPROVED.** The cr14 MAJOR is closed at the root — `gate done` now sits below
the staleness cut, an aged finished gate is counted rather than listed, and the
live in-flight table is 398 bytes with zero dead gate lines against a 1,200-char
budget. All six contract items are met, each proved by a fixture that
discriminates: the commit check keeps the seat's notes and its `exit_code=` and
fires only on a `done` claim (four cases, including the stray-board-commit
case); `--then` and groups round-trip through `%q` byte-for-byte and the
`$'…'` forms are refused at write time with one message per value and nothing
written; the recycled-pid fixture is decided by the fake `ps` alone, which I
confirmed by running it under the real `ps` and getting the opposite verdict;
the locals are fixed and nothing leaks out of `inflight_stdout`.

Red before green is 7 tests on CR3r's own code, exactly the set the plan names.
36 of 37 mutations die — CR3rb's seven, cr14's fourteen, cr9's eleven, four CR5
spot checks — and the single survivor is a `local` keyword that no ShellCheck
option and no test can observe, whose effect I verified directly at runtime
instead. Every named check is green, the commit convention is exact, and landing
is safe with `sb7` in flight.
