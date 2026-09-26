---
reviewer: opus
majors: null
minors: 7
---
# Opus gate — seat run cr5, task CR1b — APPROVED

## Summary

One commit, `c4f0bbb`, on base `940f21f`; subject byte-identical to the plan's
(196 bytes, `cmp` clean), both trailers present in order, `tools/ritual.sh`
`100755`. Seven files touched, every one inside the declared `touches`
(`docs/runbooks/session.md` is declared but untouched — correct, CR1b has no
runbook work). The four majors the cr2/CR1 gate found are all fixed, and each
fix is pinned by a test that goes red on CR1's scripts. The three minors are
folded in and also pinned. **M15 and M17, CR1's two survivors, now die**, and
all fourteen of CR1's killed mutants still die.

Evidence for each: the in-flight part against my own 170-stale/3-live fixture
prints exactly the three live keys, sorted, plus one summary line, 155 chars
total (CR1: 196 lines / 13 639 bytes, truncated at line 16). A review path
carrying a space, a double quote, a backslash and a non-ASCII byte produces
stdout that `json.load` parses with `decision == "block"` (CR1: `Expecting ','
delimiter`). `ritual.sh stop` and `tools/session-start.sh` return in 13 ms and
1.5 s with stdin closed, with a never-writing pipe, with 20 MB on stdin, and on
a real pty via `script -qec` (CR1: hangs forever). `RITUAL_EVIDENCE` pointing at
a missing binary, and a stub exiting 2, both allow with
`ritual: evidence unavailable (exit 127|2) - allowing the board check` on
stderr, while exit 1 still blocks. All five must-block cases still block, each
naming its file.

`unit` (192/192) and `lint` both build green — and I forced `unit` with
`--rebuild`, so that is a fresh 29 s build in the sandbox, not a cache hit.
Five mutations survive; all five are coverage gaps on code I verified correct by
hand, none is a behavioural defect, so none is a MAJOR. The one residual worth
the operator's eye is not CR1b's doing: nothing in the repo ever writes
`run.meta` (0 of 235 real run dirs have one), so on the real host the pid branch
is unreachable and the in-flight table over-reports — 20 keys shown "running"
against one live `factory-task`. Recorded as MINOR-5.

## Rule behaviour

All fixtures built by me in
`/tmp/claude-1000/…/scratchpad/`; `XDG_STATE_HOME` and `FACTORY_ROOT` point at
scratch dirs except in the live probe, where the real `~/factory/runs` is read
(read-only: `stat` and a `sed` on a `run.meta` that does not exist). The repo
under test is always the throwaway clone, never `/home/dalhaka/nixos-agent-env`.

| case | expected | observed |
|---|---|---|
| **1a** 170 logs at mtime −29 h + 3 live (`og5/OG1r2b` w/ live pid, `rt8/RT5rb`, `zz9/AAA`) | only the 3 live keys, sorted, ≤1200 chars, one stale summary line, heading present | **pass** — 4 lines / 155 chars: `og5 OG1r2b - pid … alive - log age 0m - then: gate`, `rt8 RT5rb - running - log age 0m`, `zz9 AAA - running - log age 0m`, `… and 170 stale logs older than 2h`; `## In flight` present in the rendered part; no `d001` anywhere |
| **1b** 3 stale logs, 0 live | says so, lists nothing | **pass** — the part is `## In flight` + `… and 3 stale logs older than 2h` |
| **1b'** runs dir with no logs at all | — | the part is omitted entirely (heading only printed when `inflight_out` is non-empty). Acceptable |
| **1c** stale boundary, `RITUAL_STALE_AFTER=7200` | say which side | **`-gt` is the test**: age 7199 s → listed, age **7200 s exactly → listed** (`b EXACT - running - log age 120m`), age 7201 s → collapsed. The boundary falls on the **live** side |
| **2** `docs/reviews/naïve "x"\y.md` (space, quote, backslash, non-ASCII) | stdout parses as JSON, decision block, reason names the path | **pass** — `{"decision":"block","reason":"ritual: commit the review file(s) \"docs/reviews/naïve \\\"x\\\"\\\\y.md\""}`; `json.load` → `decision= block`, reason round-trips to `"docs/reviews/naïve \"x\"\y.md"` |
| **3a** `ritual.sh stop` / `session-start.sh` with `exec 0<&-` | return < 2 s | **pass** — 13 ms / 1525 ms (`timeout 5` never fired) |
| **3b** stdin a fifo held by `sleep 30`, then the sleep killed | return < 2 s | **pass** — both rc 0, returning as soon as the writer closed |
| **3c** 20 MB on stdin, as a file and through `cat \|` | return < 2 s, cap enforced | **pass** — ritual 13/16 ms, session-start 1536/1544 ms. **Cap = 8192** (`RITUAL_STDIN_MAX` / `SESSION_START_STDIN_MAX`, `tools/ritual.sh:45`, `tools/session-start.sh:26`). Enforced: `session_id` at byte ~4000 → block; the same id pushed past 9000 → `malformed Stop input (no session_id) - allowing`; with `RITUAL_STDIN_MAX=20000` the same input blocks again |
| **3d** real pty (`script -qec`), not in the plan but the command CR1 broke | returns | **pass** — `ritual.sh stop` 25 ms, `session-start.sh` 1562 ms |
| **4a** `RITUAL_EVIDENCE=/nonexistent/evidence`, clean tree | allow, stderr line | **pass** — stdout empty, stderr `ritual: evidence unavailable (exit 127) - allowing the board check` |
| **4b** evidence stub printing a traceback, exit 2 | allow | **pass** — `… (exit 2) - allowing the board check` |
| **4c** evidence exit 1 (real drift) | still blocks | **pass** — `{"decision":"block","reason":"ritual: the board's queue block is stale - …"}` |
| **4d** `SESSION_START_EVIDENCE=/nonexistent/evidence` | SessionStart prints `unavailable:` | **pass** — `unavailable: evidence not on PATH` |
| **5a** untracked `docs/reviews/2026-09-05-opus-review-x-Y.md` | block naming it | **pass** |
| **5b** untracked `docs/superpowers/plans/2026-09-05-x.md` | block naming it | **pass** — `commit or revert docs/superpowers/plans/2026-09-05-x.md; …` |
| **5c** modified `docs/OPERATIONS.md` | block naming it | **pass** |
| **5d** untracked `docs/board/log-2026-09.md` | block naming it | **pass** |
| **5e** stale queue block, evidence available (rc 1) | block naming `write-board` | **pass** |
| **5f** clean tree, evidence rc 0 | silent | **pass** — empty stdout |
| **6a** PreCompact handoff | carries the newest board-log line | **pass** — `## newest board log` / `**2026-09-05 19:10** — cr5 CR1b landed; the gate ran.`, alongside trigger, HEAD, dirty, in flight, unmet checks |
| **6b** override notice stream | stderr, not stdout | **pass** — stdout `[]`, stderr `ritual: override present - allowing (dalhaka 2026-09-05 19:01:50…)` |
| **6c** `.blocks` reaping | >7 d deleted, younger kept | **pass** — 8 d and 9 d deleted; 7 d, 6 d and 1 h kept (`find -mtime +7`, so a file at exactly 7 d survives — consistent with "older than 7 days") |
| **7** `.claude/settings.json` | G6's SessionStart entry preserved; Stop/PreCompact point at ritual.sh; parses; no PreToolUse | **pass** — the SessionStart object is byte-identical (only its array's closing `]` gained a comma); `PreCompact` matcher `manual\|auto` → `ritual.sh precompact "$CLAUDE_PROJECT_DIR"`, `Stop` no matcher → `ritual.sh stop "$CLAUDE_PROJECT_DIR"`, both `type: command`, `timeout: 10`; `json.load` → `['SessionStart','PreCompact','Stop']`; no `PreToolUse` (OG1 is not on this base) |
| **8** live probe, real runs dir | returns promptly, live keys match `pgrep -af factory-task`, stale count is one line | **partial — see MINOR-5.** Returns in **1528 ms**; the part is 21 lines / 836 chars ending in one line `… and 181 stale logs older than 2h` (CR1: 196 lines, all live work truncated away — that MAJOR is fixed). `pgrep -af factory-task` showed **one** run at that moment, `rt8 … RT5rb`, and the table does list `rt8 RT5rb - running - log age 0m`. og5's OG1r2b had just finished (`OG1r2b.result` written 18:55) and is correctly **absent**. But the table also shows 19 `wave-group-1` / `integrate` keys for runs that are over (`cr2 wave-group-1 - running - log age 73m`, whose `CR1.result` was written at 17:46) |
| **live-probe safety** | the probe writes nowhere but stdout/stderr | verified by reading `tools/session-start.sh` (no redirection, no `mkdir`, no `touch` — `grep -nE '>[^&\|=]\|mkdir\|touch \|rm \|tee ' ` matches only two comment lines) and by pointing `[repo]` at the clone |

Forbidden calls in the hook path: `grep -nE '(^|[^a-z])nix |git (commit|add)|sudo|systemctl|nixos-rebuild'` over both scripts → none.

## Checks

| check | result | time |
|---|---|---|
| `nix develop -c shellcheck tools/ritual.sh tools/session-start.sh` | **exit 0**, no output | 1.7 s |
| `nix develop -c bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats` | **41 ok, 0 not ok** | 3.9 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | **pass** (cache hit) | 1.1 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass, forced fresh build**, `1..192`, 192 ok, 0 not ok, rc 0 | 29.0 s |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | **pass** | 1.1 s |
| `nix develop -c python3 pkgs/evidence/repomap.py --root . check` | **exit 0** — `docs/MAP.md` honestly regenerated | 2 s |
| `nix develop -c githooks/pre-commit` (post-commit clone) | **exit 1** — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` | 3 s |
| `nix develop -c githooks/pre-commit` (same tree, base history — i.e. as it ran at commit time) | **exit 0** | 3 s |
| `nix develop -c githooks/pre-commit` at base `940f21f` | **exit 0** | 3 s |
| `nix develop -c bats tests/unit` (local, unsandboxed) | 191 ok, 1 not ok — `#148 basket set and not mounted: … waits for Enter`, the same pre-existing tty-dependent test the cr2/CR1 gate saw as #144 | 30 s |

The lint-gate exit 1 is **not** a CR1b defect and is not counted as a red check.
It is post-landing board debt: `evidence tasks` derives the queue from the tree,
and once commit `c4f0bbb` exists the derived queue no longer lists `CR1b`, so
the committed block goes stale. Proof: `tasks.py check --board` returns 0 at
base and 1 at HEAD; the full gate returns 0 on the identical working tree with
base history (the state the hook actually saw when the seat committed), and the
only diff it wants is `-… B1 CR1b CR3 …` → `+… B1 CR3 …`. `docs/OPERATIONS.md`
is not in `touches`, and writing the board is the orchestrator's step at
integrate. I restored the file; the clone is clean.

## Red before green

CR1's `tools/ritual.sh` and `tools/session-start.sh`
(`git -C /home/dalhaka/factory/ws/cr2/CR1 show task/CR1:<path>`, read-only) put
in place of CR1b's, CR1b's tests kept:

```
not ok 18 an old log with no run.meta is collapsed into the stale summary, never listed
not ok 19 inflight lists only the live runs, sorted, collapsing 170 stale logs into one summary line
not ok 20 stop blocks with valid JSON when the path has a space and a non-ASCII byte
not ok 21 a missing evidence degrades to allow on the board check with a stderr warning
not ok 22 stop returns within 2s when stdin is closed
not ok 24 precompact's handoff carries the newest board-log line
not ok 25 the override notice goes to stderr, leaving stdout empty
not ok 26 blocks files older than 7 days are reaped on each run
not ok 40 session-start returns within 2s when stdin is closed
```

Nine red, 32 still green. All four majors are covered (18/19 in-flight, 20 JSON,
21 evidence, 22/40 stdin) **and all three minors go red too** (24 board-log,
25 stderr, 26 reaper) — the plan asked whether they would, and they do. The
failures are behavioural, not "command not found": #19 fails on
`[ "${#output}" -le 1200 ]`, #20 on `json.decoder.JSONDecodeError: Expecting ','
delimiter: line 1 column 66`, #21 on non-empty stdout, #22 on `$status -eq 0`
(rc 124 from `timeout 2`).

Two of the new tests are **not** load-bearing: #23 and #41 ("stdin is a pipe
that never writes") pass on CR1's `input=$(cat)` too, because `0< <(:)` is a
pipe that closes immediately and `cat` returns at EOF. The plan asked for that
shape explicitly, so this is not a deviation, but the closed-stdin tests (#22,
#40) are the ones doing the work.

Restored → 41 ok, 0 not ok; `git status --short` empty.

## Mutation table

Applied to the shipped tree, `git diff --quiet` asserted non-clean before each
run (any unapplied edit is reported VOID and rerun), `bats
tests/unit/92-ritual.bats tests/unit/90-session-start.bats </dev/null` under
`timeout 90`, then `git checkout -- tools tests`.

**Gate matrix**

| # | mutation | result |
|---|---|---|
| M-A | `inflight_out=""` — the table dropped from the SessionStart part (= CR1's **M15**) | **killed** — #39 |
| M-B1 | dead pid **and** stale log listed instead of counted (`ritual.sh:205-208`) | ***SURVIVES*** — MINOR-1 |
| M-B2 | stale log with no `run.meta` listed instead of counted (`ritual.sh:211-213`) | **killed** — #18, #19 |
| M-C | the escaping `sed` removed, reason interpolated raw (`ritual.sh:155`) | **killed** — #20 |
| M-D1 | `ritual.sh` tty guard + bounded read → `input=$(cat)` | **killed** — #22 (and it hangs bats outright when bats' own stdin is a live pipe) |
| M-D2 | `session-start.sh` tty guard + bounded read → `input=$(cat)` | **killed** — #40 |
| M-D3 | only the `[ -t 0 ]` guard removed, bounded read kept | ***SURVIVES*** — MINOR-4 |
| M-E1 | `-n "${RITUAL_STDIN_MAX:-8192}"` removed | ***SURVIVES*** — MINOR-2 |
| M-E2 | `-n "${SESSION_START_STDIN_MAX:-8192}"` removed | ***SURVIVES*** — MINOR-2 |
| M-F | missing evidence blocks instead of allowing | **killed** — #21 |
| M-G1 | reaper `-mtime +7` → `+0` | ***SURVIVES*** — MINOR-3 |
| M-G2 | reaper `-mtime +7` → `+1000` | **killed** — #26 |

**CR1's seventeen, re-applied on the CR1b tree**

| # | mutation | result |
|---|---|---|
| M1 | `docs/reviews` dropped from the review status path | killed — #1, #5, #6, #20 |
| M2 | the `check --board` branch made unreachable | killed — #4 |
| M3 | `.claude/ritual-override` ignored | killed — #7, #25 |
| M4 | the two-block bound removed | killed — #5 |
| M5 | the block counter never incremented | killed — #5 |
| M6 | board debt `-ge` → `-gt` | killed — #11 |
| M7 | `precompact` also writes `$repo/handoff-leak.md` | killed — #13 |
| M8 | a dead pid reported as `alive` | killed — #15 |
| M9 | `stop` exits 1 on malformed stdin | killed — #10, #22, #23 |
| M10 | the mtime-stale branch removed (old logs listed as running) | killed — #18, #19 |
| M11 | the `.result` skip removed | killed — #17 |
| M12 | the `relaunch:` hint dropped | killed — #15 |
| M13 | the idle line's text changed | killed — #38 |
| M14 | the `## Handoff` heading and `cat` removed | killed — #37 |
| M16 | the whole ritual part dropped from SessionStart | killed — #37, #38, #39 |
| **M15** | `inflight_out=''` (CR1 survivor) | **killed** — #39 |
| **M17** | `## In flight` heading → `x` (CR1 survivor) | **killed** — #39 |

**17 of 17 of CR1's mutants die.** Across the gate matrix, 7 of 12 die and 5
survive; every survivor is a missing test on code I confirmed correct by hand,
so none is a defect and none is a MAJOR.

## Findings

No MAJORs.

**MINOR-1 — the dead-pid-and-stale branch of the collapse is untested.**
`tools/ritual.sh:205-208`. Listing that corpse instead of counting it survives
the suite:

```
M-B1 (stale w/ pid: listed instead of counted): *** SURVIVES ***
```

The shipped behaviour is right — a fixture with `pid: 999999` and a log at
mtime −29 h prints only `… and 1 stale logs older than 2h` — and the branch
cannot fire on this host today (no `run.meta` exists anywhere, MINOR-5), but it
is the branch through which CR1's corpse flood could return the day `run.meta`
starts being written. Fix: one test — dead pid **and** a stale log → collapsed,
key absent from the output.

**MINOR-2 — the 8192-byte stdin cap has no test.**
`tools/ritual.sh:45`, `tools/session-start.sh:26`. Removing `-n
"${…_STDIN_MAX:-8192}"` from either script leaves the suite green (M-E1, M-E2),
because the 20 MB timing case is not in the suite and, without the cap, `read
-d ''` still terminates at EOF. It is trivially pinnable and the cap does work
— by hand, a `session_id` pushed past byte 9000 is not seen (`malformed Stop
input (no session_id) - allowing`) and reappears with `RITUAL_STDIN_MAX=20000`.
Fix: that exact three-line test.

**MINOR-3 — the reaper's lower edge is untested.**
`tools/ritual.sh:68`. `-mtime +7` → `+0` survives (M-G1): no test asserts that a
*young* `.blocks` file is kept, only that an 8-day one is deleted. By hand the
shipped threshold keeps 1 h / 6 d / 7 d and deletes 8 d / 9 d. Fix: add a fresh
`.blocks` file to test #26 and assert it survives the run.

**MINOR-4 — the `[ -t 0 ]` guard itself is unpinned.**
`tools/ritual.sh:44`, `tools/session-start.sh:25`. Removing the guard while
keeping the bounded read survives (M-D3) — bats has no pty, which the plan
anticipated ("`</dev/tty` unavailable in bats"). I closed the gap by hand
instead: `script -qec "bash tools/ritual.sh stop <repo>" /dev/null` returns in
25 ms and `script -qec "bash tools/session-start.sh <repo>"` in 1562 ms, so the
guard is doing its job today. Noted so the next round knows the guard is held by
nothing but this review.

**MINOR-5 — on the real host the in-flight table still over-reports, because
nothing writes `run.meta`.** `tools/ritual.sh:190-201`. `find ~/factory/runs
-maxdepth 2 -name run.meta` returns **0 hits across 235 run dirs**, and a
repo-wide grep finds `run.meta` only in `ritual.sh`, its tests, the spec, the
plan and CR1's review — no tool produces it. The pid branch is therefore
unreachable in production and every log falls to the mtime heuristic, where a
finished run's `wave-group-1.log` never gets a `.result` sibling to skip it.
Measured at 19:00: `pgrep -af factory-task` → one process (`rt8 … RT5rb`), the
table → 20 keys, of which 19 are wave-group/integrate logs of runs that are
over, e.g. `cr2 wave-group-1 - running - log age 73m` whose `CR1.result` was
written at 17:46. Not a MAJOR: CR1's actual rejection was that live work was
*invisible* (196 lines truncated at 16, zero live keys shown), and that is
fixed — `rt8 RT5rb - running` is right there in 836 chars. The over-report is
also the codebase's own convention (`tasks.py` calls a key running until its log
passes `stale-after`) and the missing `run.meta` writer is orchestration work
outside CR1b's `touches`. Fix belongs in a later task: have `factory-wave` write
`run.meta`, or skip a `wave-group-*.log` once a sibling key has a `.result`.

**MINOR-6 — the `relaunch:` hint is still not a runnable command** when
`run.meta` carries no `repo`/`groups`: `relaunch: factory-wave r1  ` with two
empty fields. This is CR1's MINOR-6, which CR1b's plan deliberately did not fold
in (it folded CR1's MINOR-5, -7 and -8). Recorded as still open, not as a
regression.

**MINOR-7 — the in-flight budget has about nine lines of headroom.** The part
is 836 chars today against `SESSION_START_CAP_INFLIGHT` 1200, and the stale
summary is printed *last*, after the sorted live block, so it is the first thing
a truncation eats. With ~30 live lines the part would truncate again — not with
corpses this time, but the failure mode is the same shape. Ordering the summary
line first, or capping the live list itself, would make the budget safe.

**NOTE — `2>/dev/null` on the stdin read.** `tools/ritual.sh:45`,
`tools/session-start.sh:26`. CLAUDE.md's rule is about gated commands, and
`read` is not one, so this is style only; shellcheck is silent. Worth an eye
because it also swallows a genuine fd-0 error.

## Verdict

**APPROVED.** All four MAJORs from `docs/reviews/2026-09-05-opus-review-cr2-CR1.md`
are fixed and each is pinned by a test that goes red on CR1's scripts; the three
minors the plan named are folded in and pinned too. Every required-matrix row
passes except row 8, whose shortfall is a pre-existing orchestration gap
(`run.meta` is written by nothing) rather than a CR1b defect — CR1's actual
complaint, that the part showed no in-flight work at all, is fixed and measured.
`unit` passes 192/192 on a forced rebuild, `lint` passes, `shellcheck` is
silent, `repomap check` agrees, the commit is one commit with a byte-identical
subject, both trailers and no file outside `touches`. All seventeen of CR1's
mutants die, M15 and M17 included. The five surviving mutations are test-coverage
gaps on behaviour I verified by hand, and are recorded as MINOR-1 through -4 for
the next round.

Verified in a throwaway clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-cr5-CR1b`.
`/home/dalhaka/factory` was read only (`git show`, `stat`); the live repo was
not touched apart from this review file.
