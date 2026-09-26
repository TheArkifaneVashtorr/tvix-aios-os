# Context-reset ritual — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox syntax. The seat driver reads the `### KEY (kind, size) — title` sections below.

**Goal:** the optimal series of events before a context reset, enforced deterministically by Claude Code hooks (Stop blocks a turn that would leave state uncommitted or the board stale; PreCompact writes a derived handoff; SessionStart shows in-flight work and ritual status); an operator-only escape hatch; seat runs that survive the launching session.

**Spec:** `docs/superpowers/specs/2026-09-05-context-reset-ritual-design.md` (written by a Fable design agent at the operator's request, 2026-09-05 evening; the operator's "When to /new" data is in it). Task sections below are the spec's, verbatim.

## Global Constraints

- Build-only; never `sudo`, `nixos-rebuild`, `systemctl`. Checks via `nix build .#checks.x86_64-linux.<name> -L --no-link`; lint gate `nix develop -c githooks/pre-commit` (it may regenerate the board block once: `git add docs/OPERATIONS.md` and commit again); commits via `nix develop -c git commit -F <msgfile>` with the `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` trailer.
- Hooks never call nix, never commit, never write inside the repo (state goes under `$XDG_STATE_HOME/nixos-agent-env/ritual/`); each hook call under one second; malformed input degrades to allow with a stderr line.
- Interface facts quoted in a section come from a command run at planning time; CR1's Step 0 records the real hook stdin before any test is written.

## Tasks

### CR1 (code, S) — `tools/ritual.sh`: stop, precompact and inflight subcommands; PreCompact hook; SessionStart prints the handoff and in-flight state

**dependsOn:** none
Note (G12b lands the `running` state independently; CR1 reads the runs dir itself)

**Files:** create `tools/ritual.sh`, `tests/unit/92-ritual.bats`; modify
`tools/session-start.sh`, `tests/unit/90-session-start.bats`,
`.claude/settings.json`, `docs/MAP.md` (regenerated, disclosed).

Step 0 (measurement, pasted into the section as facts): run each hook by hand
and record real stdin for `Stop`, `PreCompact`, `SessionStart(compact)`; time
`evidence tasks --root . check --board docs/OPERATIONS.md` on core. Then §5's
stop/precompact/inflight/session-start tests red → implement → green:
shellcheck, `bats tests/unit`, `nix build .#checks.x86_64-linux.unit -L
--no-link`, lint gate; wall time of `ritual.sh stop` < 1 s recorded.

**touches:** tools/ritual.sh, tests/unit/92-ritual.bats, tools/session-start.sh, tests/unit/90-session-start.bats, .claude/settings.json, docs/MAP.md
**acceptance:** unit, lint
**commit subject:** `session: the reset ritual — a Stop hook refuses to end a turn with uncommitted reviews, plans or board, or a stale queue block; PreCompact writes a derived handoff; SessionStart prints in-flight runs and idle time (test: unit, lint)`

### CR2 (code, XS) — the operator-only override: guard denies `.claude/ritual-override`

**dependsOn:** OG1r, CR1

**Files:** modify `tools/orchestrator-guard.sh`, `tests/unit/91-orchestrator-guard.bats`.
Add the destination path to the protected prefixes (Bash) and to the
Edit/Write/MultiEdit path rule; §5's guard tests red first; OG1r's tests and
killed mutants still hold.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats
**acceptance:** unit, lint
**commit subject:** `session: the ritual override file is the operator's — the orchestrator guard denies writing or removing .claude/ritual-override (test: unit, lint)`

### CR3 (code, S) — the seat driver records in-flight intent: `run.meta` with `--then`, a gate marker, runs detached from the launching session

**dependsOn:** none
Note (touches conflict with SB3b on `factory-task`? no — SB3b touches the wrapper; `evidence tasks conflicts` to confirm at dispatch)

**Files:** modify `tools/factory/seat/factory-wave` (`--then <text>`; writes
`~/factory/runs/<run>/run.meta`: `run:`, `repo:`, `base:`, `groups:`, `pid:`,
`launched:`, `then:`; re-exec under `setsid` when `$$` is not a session
leader), `tools/factory/seat/factory-review` (`<KEY>.gate` marker while
gating), `tools/factory/seat/README.md`, `tests/unit/80-seat-driver.bats`.
Bash only (the seat's host PATH). §5's seat-driver tests red first.

**touches:** tools/factory/seat/factory-wave, tools/factory/seat/factory-review, tools/factory/seat/README.md, tests/unit/80-seat-driver.bats
**acceptance:** unit, lint
**commit subject:** `factory: every seat run records what it is and what happens when it lands (run.meta, --then); gates leave a marker; runs survive the launching session (test: unit, lint)`

### CR4 (code, XS) — the Now paragraph is at most ten lines (lint); runbook section; one CLAUDE.md line

**dependsOn:** CR1, CR2

**Files:** modify `githooks/pre-commit` (Now ≤10 lines, message names the
rule), `docs/runbooks/session.md` (section "The reset ritual": the ten steps,
the three hooks and their reasons, the override, when to `/new` with the
operator's relevance rule), `CLAUDE.md` (one line under "How work is done
here": "Before any reset — compaction, `/new`, a pause — run the ritual:
`docs/runbooks/session.md`; the Stop hook enforces the derived half"). Lint
test red on an 11-line fixture first.

**touches:** githooks/pre-commit, docs/runbooks/session.md, CLAUDE.md
**acceptance:** lint
**commit subject:** `docs: the reset ritual runbook; START HERE's Now paragraph is capped at ten lines; CLAUDE.md points at the ritual (test: lint)`

## Open questions (gaps to test, not to assume)

- **H1** — exact hook contracts (PreCompact matchers and whether its stdout
  reaches the model; Stop's `stop_hook_active`; SessionStart's `source`):
  CR1 step 0 records them. **H2** — `check --board` wall time in a Stop hook.
- **G1** — does `/new` kill `run_in_background` children today? Runs survived
  compactions; the reboot killed them. CR3's `setsid` makes it moot.
- **G2** — `tasks.py` liveness by pid once `run.meta` carries one (G12b uses
  mtime; follow-up, out of scope).
- **G3** — board debt in commits or minutes? Commits first (deterministic
  across pauses); revisit with `ritual.log` data.

### CR1b (code, S) — CR1 fix round: in-flight shows only the live, the reason is JSON, stdin never blocks, missing evidence degrades to allow

**dependsOn:** none

Gate `docs/reviews/2026-09-05-opus-review-cr2-CR1.md` — REJECTED, four majors. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr2/CR1 task/CR1 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with CR1's subject; declare `flake.nix` and `docs/MAP.md` in touches.

- [ ] **Step 1: Tests first, red on CR1** — (1) in-flight part against a fixture runs dir with 170 dead logs (mtime 29 h) and 3 live ones: prints ONLY the live keys (dead ones are counted in one summary line `… and N stale logs older than <stale-after>` — never listed), sorted, ≤ 1,200 chars, and the three live lines are present verbatim (mutation: drop the table → fails; mutation: list dead logs → fails on the cap); the part's heading pinned. (2) Stop block reason with a path containing a space and a non-ASCII byte → stdout is valid JSON (`python3 -c 'import json,sys; json.load(sys.stdin)'` passes) and the decision is `block` (mutation: raw interpolation → fails). (3) `ritual.sh stop` and `tools/session-start.sh` with stdin a terminal (`</dev/tty` unavailable in bats — use `[ -t 0 ]` emulation: run with stdin closed `<&-` and with stdin a pipe that never writes but is closed) → return within 2 s (timeout-guarded test); reading stdin only when it is not a tty and only up to a size cap. (4) `evidence` missing from PATH (`SESSION_START_EVIDENCE=/nonexistent/evidence`) → the Stop hook does NOT block on the board check (degrade-to-allow with a stderr line), and SessionStart prints `unavailable:` as before. Minors: the handoff includes the newest board-log line; the override notice goes to stderr; `<sid>.blocks` files older than 7 days are reaped on each run.
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats`; `unit`; lint gate; real: `bash tools/session-start.sh | tail -20` returns promptly on this host and shows the live in-flight keys (compare `pgrep -af factory-task`). CR1's 14 killed mutants still die. **Step 5: One commit**, CR1's subject.

**touches:** tools/ritual.sh, tools/session-start.sh, tests/unit/92-ritual.bats, tests/unit/90-session-start.bats, .claude/settings.json, flake.nix, docs/MAP.md, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: ritual.sh — Stop blocks a turn that would leave reviews uncommitted or the board stale; PreCompact writes the handoff; SessionStart shows in-flight work and idle time (test: unit, lint)`

### CR5 (code, S) — the ritual runs the tree's task renderer, never the live generation's copy, and honours `stop_hook_active`

**dependsOn:** none

Found 2026-09-05 ~19:20, minutes after CR1b landed: `ritual.sh stop` checks the queue block with `evidence` from PATH — the copy built into the LIVE generation (43, before G11r and G12r) — while `githooks/pre-commit` regenerates the block with the tree's `pkgs/evidence/tasks.py`. The two renderers disagree (the host's still lists H1 and carries the old wording), so no commit can satisfy both hooks; and the Stop hook has no loop guard, although Claude Code passes `stop_hook_active: true` when it is already continuing because of a Stop hook and expects the hook to allow then, else the session loops. Rule: every tool a hook runs against the tree comes from the tree.

**Contract:**
1. `ritual.sh` and `tools/session-start.sh` run the TREE's `pkgs/evidence/tasks.py` for every tasks call (`check --board`, `brief`, the in-flight parts). The interpreter is `RITUAL_PYTHON` when set, else `python3` on PATH, else the interpreter the packaged `evidence` wrapper names (`readlink -f "$(command -v evidence)"`; its `exec … python3` line or the `python3` directory its `PATH=` export prepends); none found → degrade to allow with the stderr line `ritual: no python3 for the tree's renderer - allowing`. `evidence bundle` stays the packaged command (it reads the store, not the tree).
2. `stop_hook_active` true in the Stop payload → allow, stderr line `ritual: continuing after a block - allowing`, no `.blocks` write: a block is asked once per turn end, never in a loop.
3. The board check's verdict equals pre-commit's by construction (same file, same kind of interpreter); the runbook states that a hook never calls a host-packaged copy of tree code.

- [ ] **Step 1: Tests, red on CR1b** — (1) a fixture where a fake `evidence` on PATH always says stale (exit 1) while the tree's `tasks.py` says current → `ritual.sh stop` allows (mutation: back to `$ev` → fails); (2) the reverse: the tree's renderer says stale, the fake says current → block (mutation: the fake wins → fails); (3) `stop_hook_active: true` with a stale board → allow, the stderr line present, no `.blocks` write (mutation: guard removed → fails); (4) no `python3` anywhere and no `evidence` → allow with the stderr line (mutation: block → fails); (5) `RITUAL_PYTHON` pointing at a wrapper that records its argv → the tree's `tasks.py` path is what runs, for `stop` AND for session-start's brief part (mutation: one of the two still calls `$ev` → fails). Measure `ritual.sh stop` on this host and state the number (< 0.5 s).
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats`; `unit`; lint gate; CR1b's kills still die; real: on this host, with the tree ahead of the live generation, `printf '{"session_id":"x","stop_hook_active":false,"cwd":"%s"}' "$PWD" | bash tools/ritual.sh stop "$PWD"` on a clean committed tree prints no `block` — paste the output. **Step 5: One commit.**

**touches:** tools/ritual.sh, tools/session-start.sh, tests/unit/92-ritual.bats, tests/unit/90-session-start.bats, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: the ritual and the session hook run the tree's task renderer, never the live generation's copy; a Stop hook never loops (test: unit, lint)`

### CR3b (code, S) — CR3 fix round: `setsid -w` keeps the wave's exit code, pids are per key (gates included), `base:` is a SHA and `group:` lines round-trip, the marker carries a pid, edge cases pinned

**dependsOn:** none
Sequencing: CR5 (in gate) also edits `tools/ritual.sh` — dispatch CR3b only after CR5 lands, from a workspace forked from that main.

Gate `docs/reviews/2026-09-05-opus-review-cr6-CR3.md` — REJECTED, three majors, seven minors. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr6/CR3 task/CR3 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with CR3's subject.

**Contract:**
1. Detach without losing the result: the re-exec is `exec setsid -w -- "$0" "$@"` (waits, propagates the exit code), so the launcher still sees the wave's exit code and summary lines while the wave survives `kill -KILL -<launcher pgid>`; already a session leader → no re-exec.
2. Pids are per key, not per run: `run.meta` keeps `pid:` (the wave); each `factory-task` writes `<KEY>.pid` (its own pid) beside `<KEY>.log` when it starts and removes it on exit; `factory-review` writes `<KEY>.gate` holding its pid, the removal trap armed BEFORE the marker is created. `ritual.sh`'s in-flight part judges each log by ITS OWN pid file (`<KEY>.pid` for `<KEY>.log`, `<KEY>.gate` for `<KEY>.review.log`), falls back to the run-level pid only for a log with no pid file, and never prints `DEAD` for a log younger than stale-after (a fresh log is live by rule); a `relaunch:` hint appears only for a wave whose pid is dead and whose keys have no `.result` with `status=done`.
3. `base:` is `git rev-parse HEAD` (always a SHA); `group:` is one line per wave group, the chain quoted for the shell (`group: "N11 N3 N6"`), so the `relaunch:` line reproduces the original argv exactly; `then:` absent when not given, given twice → the last (documented), a multi-line value → exit 2 (one key per line).
4. `run.meta` exists before the first task starts (the fake seat asserts it when launched).
5. README documents the pid files, the marker's pid, the `base:`/`group:` forms and the `--then` rules, and states that the board's `setsid -f …` launch rule is retired: the driver detaches itself.

- [ ] **Step 1: Tests, red on CR3** — (1) under `set -m` with a fake factory-task that sleeps 4 s and writes status=failed: the launcher sees exit 1 after ≥ 4 s (mutation: `-w` dropped → exit 0 at once → fails); (2) the wave survives `kill -KILL -<launcher pgid>` and writes its `.result`; (3) `<KEY>.pid` present while the fake task runs, gone after; `<KEY>.gate` holds the reviewer's pid while gating, gone after success and after SIGTERM (mutation: trap after marker → fails on the kill case); (4) the review's fixture — `CR3.log` + `CR3.result` (done) + a fresh `CR3.review.log` + `CR3.gate` with a live pid → the line says running, no `DEAD`, no `relaunch:` (mutation: the run-level pid applied to every log → fails); a fresh log with a dead run pid → live (mutation: `DEAD` by pid → fails); (5) `base:` equals `git rev-parse HEAD` of the fixture repo (mutation: branch name → fails); `factory-wave r <repo> "K1" "K2"` and `factory-wave r <repo> "K1 K2"` write different `group:` lines and different `relaunch:` lines (mutation: space-join → fails); (6) `pid:` equals the wave's own pid and is never 0 (mutation: 0 → fails; the reader treats 0 as dead); (7) `run.meta` exists when the fake seat starts (mutation: written after → fails); (8) `--then` twice, empty, multi-line per contract 3; (9) every driver test sets `FACTORY_BIN_OVERRIDE` to fakes so no test can reach the real factory-task (the review's test-30 hazard).
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck (factory-wave, factory-review, factory-task, factory-lib.sh, ritual.sh); `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats`; `unit`; lint gate; CR3's 6 kills and CR1b's and CR5's kills still die. **Step 5: One commit**, CR3's subject.

**touches:** tools/factory/seat/factory-wave, tools/factory/seat/factory-review, tools/factory/seat/factory-task, tools/factory/seat/README.md, tools/ritual.sh, tests/unit/80-seat-driver.bats, tests/unit/92-ritual.bats
**acceptance:** unit, lint
**commit subject:** `factory: every seat run records what it is and what happens when it lands (run.meta, --then); gates leave a marker; runs survive the launching session (test: unit, lint)`

### CR2b (code, XS) — CR2 fix round: the override file is protected the way the plans directory is — its directory and every ancestor count for the delete family, `dd of=` and python removals are seen, the `cd`/cwd and symlink spellings pinned

**dependsOn:** none

Gate `docs/reviews/2026-09-05-opus-review-cr8-CR2.md` — REJECTED, four majors: the rule keys on the exact file path, so `rm -rf .claude`, `git clean -fd`, `mv .claude .claude-old`, `find .claude … -delete`, python `os.remove`/`os.unlink`/`Path.unlink`/`os.rename` naming it, and `dd of=…` all ALLOW. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr8/CR2 task/CR2 && git cherry-pick -n 8a8705a` (the task commit only — the seat's board commit is not carried); read the review in full; ONE commit with CR2's subject; never commit a board change.
Note for the third attempt (cr12): two earlier seats (cr10, cr11) died on an OpenRouter credit outage with the fix nearly finished and uncommitted — `git -C /home/dalhaka/factory/ws/cr11/CR2b diff` is that work (guard, tests, runbook; it had reached "run the full checks"). Read it first and reuse what passes the contract; do not trust its self-assessment — run Step 1's red proof and Step 4's mutations yourself.

**Contract:** one mechanism for every protected path. The plans-dir rule's directory/ancestor logic (OG1r2b's `is_plans_dir_or_ancestor` and its `dir_ancestor_seen` flag) becomes a function over a PROTECTED list of `(path, kind)` entries — `docs/superpowers/plans` (dir) and `.claude/ritual-override` (file, whose parent `.claude` and every ancestor up to `/` count as naming it for the delete family: `rm`, `mv`, `rmdir`, `rsync`, `shred`, `find` with `-delete`/`-exec`, `git clean`, and `git checkout`/`restore` with no path or with `.claude`); the `dd` arm admits the `of=` value into the token scan; the python/perl arm matches `os.remove`, `os.unlink`, `unlink(`, `.unlink()`, `os.rename`, `os.replace`, `shutil.move`, `shutil.rmtree`, `write_text`, `open(…,"w")` naming a protected path; reads (`cat`, `ls -la .claude`, `stat`, `git status`, `test -f`) allow; the reason names the operator (`the ritual override is the operator's; ask for it`). Deny-only: over-denial accepted (`ls .claude && rm /tmp/x` denies).

- [ ] **Step 1: Tests, red on CR2** — every spelling of the review's table as a DENY case: `rm -rf .claude`, `rm -r .claude/`, `rm -rf .`, `git clean -fd`, `git clean -fdx .claude`, `git checkout -- .claude`, `git restore .claude`, `mv .claude .claude-old`, `mv .claude/ritual-override /tmp/x`, `find .claude -name 'ritual-*' -delete`, `find . -name ritual-override -exec rm {} +`, `dd if=/dev/null of=.claude/ritual-override`, `python3 -c 'import os; os.remove(".claude/ritual-override")'`, `python3 -c 'from pathlib import Path; Path(".claude/ritual-override").unlink()'`, `python3 -c 'import shutil; shutil.rmtree(".claude")'`, `cd .claude && rm ritual-override`, a payload whose `cwd` is the `.claude` dir with `rm ritual-override`, `rm link-to-override` (a symlink to the file), Edit/Write/MultiEdit payloads naming the file (absolute and relative); ALLOW cases: `ls -la .claude`, `cat .claude/ritual-override`, `stat .claude/ritual-override`, `git status`, `test -f .claude/ritual-override`, `rm -rf .claude/worktrees/x` (a sibling under `.claude` that is not protected — say whether the ancestor rule over-denies it; if it does, that is the accepted over-denial, state it in the runbook), `rm /tmp/other/.claude/ritual-override` (outside the project). Every OG1r2b and CR2 case stays as it is.
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `unit`; lint gate; mutations, each must fail at least one test: the override removed from the PROTECTED list; the ancestor rule limited to the plans dir; `dd of=` not admitted; the python arm without `os.remove`/`unlink`; the `cd` rebase off for the override; the symlink resolution off; the reason text changed. OG1r2b's and CR2's mutations still die. **Step 5: One commit**, CR2's subject.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: the ritual override file is the operator's — the orchestrator guard denies writing or removing .claude/ritual-override (test: unit, lint)`

### CR2r (code, S) — re-plan of CR2 (rule A1): one PROTECTED list feeds every arm, glob and raw-text spellings count, `git stash -u` and `tar -x` join the family, the pathless git over-denials are narrowed, the runbook measures and names the lift

**dependsOn:** none

Gates `docs/reviews/2026-09-05-opus-review-cr8-CR2.md` and `…-cr12-CR2b.md`: CR2b fixed every CR2 major (32/34 mutants, 22/22 recipes allow, no plans regression) and was rejected because `rm -rf .claude/*`, `mv .claude/* /tmp/`, `shred .claude/*` and every glob spelling still ALLOW — the override arm lacks the raw-text fallback the plans arm keeps; seven minors (the PROTECTED list is consulted by one arm only and stops at the first entry; pathless `git clean`/`checkout`/`restore` deny even when they delete nothing; a `git commit -m` message naming `.claude` beside a delete word is refused; `git stash -u` removes the untracked file and allows; the runbook names no lift and asserts an unmeasured timing; 200 symlink tokens now take 602 ms; `chmod 000` and `tar -C .claude -x` allow). Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr12/CR2b task/CR2b && git cherry-pick -n FETCH_HEAD`; read both reviews in full; ONE commit with CR2's subject; never commit a board change.

**Contract:**
1. One PROTECTED list `(path, kind)` read by ALL THREE arms — the plan-write arm, the override arm and the Edit/Write/MultiEdit arm — with no hard-coded path left in any arm (mutation: the plans entry deleted → the plans tests fail; the override entry deleted → the override tests fail) and no early `break`: every entry is evaluated (mutation: a third fixture entry appended and ignored → a test fails).
2. Raw-text and glob spellings: a token that, after quote stripping, lexically begins with a protected file's parent directory (`.claude/`, `<project>/.claude/`, `./.claude/`, or a `cd`/cwd-rebased form) — including tokens containing `*`, `?`, `[`, `{` — counts as naming the protected file for the delete family and the write family (mutation: the raw-text fallback removed → the eight glob spellings of the cr12 review fail).
3. The delete family gains `git stash` with `-u`/`--include-untracked`/`-a`, `tar`/`unzip`/`cpio` extracting into a protected directory (`-C <protected>` or an output path under it), `chmod`/`chown`/`chattr` on a protected file, `xargs` with any delete verb (already), `truncate`; reads stay allowed.
4. The pathless git over-denials are narrowed: `git clean` denies only with `-f` (with or without `-d`/`-x`) and no path or a path naming a protected dir/ancestor — `git clean -n`, `git clean -nd` allow; `git checkout <ref>` and `git checkout -b <x>` allow; `git checkout`/`git restore` deny only with `--` followed by a protected path, with a protected path, or with no path when `--` or `.` follows; `git stash` without `-u`/`-a` allows.
5. `git commit -m "<text>"` and `-F <file>`: the quoted message after `-m` is not scanned for verbs or paths (a commit message is prose; the deny-only over-denial on it is withdrawn) — mutation: the exemption removed → a test with a message naming `.claude` and a delete word fails; `-F` unaffected.
6. Performance: one token pass computes both arms' facts (no second full scan); 200 path tokens < 150 ms and 200 symlink tokens < 300 ms, median of three, measured in bats with `$EPOCHREALTIME` (mutation: the second scan reintroduced → the symlink timing test fails or is reported as measured).
7. Runbook: how the operator lifts the guard (remove the PreToolUse entries from `.claude/settings.json` or set `ORCHESTRATOR_GUARD=off` in the session — pick one, implement it, and pin that the orchestrator's shell cannot set it for itself: the flag is read from the hook's own environment, which the Bash tool does not control), the two accepted over-denials (`ls .claude && rm /tmp/x`; a sibling under `.claude`), and the timing numbers as measured.

- [ ] **Step 1: Tests, red on CR2b** — the eight glob spellings; `git stash -u`, `tar -C .claude -xf x.tar`, `chmod 000 .claude/ritual-override`, `xargs rm < .claude/list`; the narrowed git cases (`git clean -n` allow, `git clean -f` deny, `git checkout main` allow, `git checkout -- .claude` deny, `git restore --staged k` allow); the `-m` prose case allow; the third-entry fixture; the two timing cases; the lift flag not settable from the Bash payload's env. Every CR2b, OG1r2b, og4 case stays as it is.
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `unit`; lint gate; the cr12 review's 32 kills still die plus the seven mutations above. **Step 5: One commit**, CR2's subject.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: the ritual override file is the operator's — the orchestrator guard denies writing or removing .claude/ritual-override (test: unit, lint)`

### CR2rb (code, S) — CR2r fix round: the `-m` exemption covers one quoted token and ends at a newline, flag clusters are read as clusters, extracts honour the payload cwd, clause-local flag attribution, the remaining minors

**dependsOn:** none

Gate `docs/reviews/2026-09-05-opus-review-cr15-CR2r.md` — REJECTED, four majors: the `git commit -m` prose exemption never ends because the normaliser folds a newline to a space before the skip loop, so `git commit -m 'x'⏎rm -rf .claude/ritual-override` ALLOWS and four plans spellings REGRESS against main; `git clean -df`/`-xdf`/`-dxf` allow (the force test anchors `f` at the front of the cluster); `git stash push -u`, `save -u`, `-au` allow (exact flag match; the subcommand word taken as a pathspec); an extract (`cpio -idm`, `tar -xf`, `unzip`) with the payload cwd inside `.claude` allows (no path token to rebase). Eight minors. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr15/CR2r task/CR2r && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with CR2's subject; end the seat's output with the exact `FACTORY-RESULT status=…` block (no colons).

**Contract:**
1. Tokens carry a quoted flag from tokenisation. The `-m`/`--message=` exemption covers exactly ONE token: the quoted argument immediately after `-m` (or the value glued to `--message=`); a bare word after `-m` is scanned like any token; a newline inside a quoted message stays inside that one token and nothing after the token is exempt (mutation: the exemption extended to the next token → the newline cases fail). Tests: `git commit -m 'x'⏎rm -rf .claude/ritual-override` → deny; the four plans spellings of the review (`⏎rm -rf <plan>`, `⏎sed -i s/a/b/ <plan>`, `⏎tee <plan>`, `⏎mv <plan> /tmp/`) → deny, matching main; `git commit -q -m 'guard: rm -rf .claude no longer allowed'` → allow; `git commit -m rm .claude/ritual-override` (unquoted) → deny.
2. Option clusters are read as clusters: `git clean` is forced when any cluster after `clean` contains `f` or `--force` appears (`-df`, `-xdf`, `-dxf`, `-ffd`); `git stash` is untracked-including when any cluster contains `u` or `a`, or `--include-untracked`/`--all` appears, whatever the subcommand word (`push`, `save`) — subcommand words (`push`, `save`, `pop`, `apply`, `drop`, `list`, `show`, `branch`) are never pathspecs (mutations: cluster test anchored again → fails; subcommand word taken as pathspec → fails).
3. Extract arms honour the payload cwd: `tar -x…`, `unzip`, `cpio -i…` with no `-C`/`-d` destination extract into the cwd; when the cwd (or a `cd`-rebased base) is a protected directory or an ancestor → deny (mutation: the cwd check removed → fails).
4. Flag attribution is clause-local: the command is split on `;`, `&&`, `||`, `|`, newline into clauses BEFORE verbs and flags are attributed, so `rm -f result && git clean` and `ls -a && git stash` allow while each protected form still denies (mutation: whole-command attribution restored → the two allow cases fail). Over-denial accepted only for a real protected form in any clause.
5. Minors folded: `chmod`/`chown`/`chattr` on the protected directory deny; the Edit/Write arm's loop has no early `break` and the test pins it (X-MAINBRK dies); the lift prints one stderr line (`orchestrator-guard: lifted by ORCHESTRATOR_GUARD=off`); the last hard-coded plans path in the raw-text fallback is gone and `plans_canon` iterates every dir entry; the runbook states that `rm -rf .claude/worktrees/*` DENIES (the accepted over-denial of the glob rule; the earlier sibling promise is withdrawn) and carries the measured timings (73 ms / 83 ms today).

- [ ] **Step 1: Tests, red on CR2r** — the newline cases of item 1 (six), the cluster cases (`-df`, `-xdf`, `-dxf`, `push -u`, `save -u`, `-au`), the three extract-into-cwd cases, the two clause-local allow cases, the directory chmod, the Edit/Write break pin, the lift line, the runbook sentences. Every CR2r, CR2b, og5 and og4 case stays as it is (the 196-row sweep).
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `unit`; lint gate; the cr15 review's 12 kills still die plus the five mutations above; timing still under 150/300 ms. **Step 5: One commit**, CR2's subject.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: the ritual override file is the operator's — the orchestrator guard denies writing or removing .claude/ritual-override (test: unit, lint)`

### CR2r2 (code, S) — second re-plan of CR2 (rule A1): quotes bound clauses, so a quoted `|`, `;`, `&` or newline never splits a command; the remaining minors; the timing regression reversed

**dependsOn:** none

Gate `docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md` — REJECTED on one major: `tokenise_ctx` emits `;`, `&`, `|`, `>`, `(`, `)`, `{`, `}` and a newline as operator tokens without consulting the quote state, the clause splitter counts them, and CR2rb's clause-local flag attribution then credits a trailing flag to the wrong clause — `sed 's|a|b|' -i <plan>` ALLOWS (seven plans-dir writes main denies today; eight override spellings). Everything else stands: all four cr15 majors closed, 182 historic rows, 50/50 recipes, 20/21 mutants. Seven minors. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr17/CR2rb task/CR2rb && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with CR2's subject.

**Contract:**
1. Quotes bound clauses: inside a single- or double-quoted argument (and inside `$'…'`), `;`, `&`, `|`, `>`, `(`, `)`, `{`, `}` and a newline are ordinary characters of that one token — the tokeniser's own header comment already says so — and only an UNQUOTED operator or newline is a clause boundary (mutation: the quote test removed from the operator arms → the nine plans spellings and the eight override spellings of the cr17 review fail). Tests: every row of the review's two tables → DENY; `sed -i 's|a|b|' <plan>` and `sed 's|a|b|' -i <plan>` both deny (argument order irrelevant); `echo 'a;b' && rm /tmp/x` → allow; `echo 'a|b' | cat` → allow.
2. Extracts: with no `-C`/`-d`, `tar -x`, `unzip`, `cpio -i` extracting into the project root DENY (an archive can carry `.claude/ritual-override` inside) and the runbook lists this among the accepted over-denials; with `-C /tmp` or `-d /tmp` → allow.
3. `git commit`: every `-m` argument is exempt (not only the first), and the glued forms `-m'…'`, `-am '…'`, `--message='…'` are exempt likewise (mutation: the loop's break restored → the two-message test fails).
4. Timing: the context tokeniser is made single-pass again (no per-token subshell or second scan): 200 path tokens < 100 ms and 200 symlink tokens < 200 ms, median of five, measured in bats; the runbook carries the measured numbers of THIS tree, never a previous round's (mutation: the second scan reintroduced → the timing test fails).
5. Minors folded: the raw-text fallback's derivation from PROTECTED_PATHS is pinned (a fixture with a second dir entry whose literal appears nowhere in the guard → M-H dies); test 82's payload carries `cwd` at the top level; `_ctx_emit` is hoisted out of `tokenise_ctx`.

- [ ] **Step 1: Tests, red on CR2rb** — the seventeen rows of the review's tables; the two allow cases of item 1; the extract cases of item 2; the two-message and glued `-m` cases; the second-dir-entry fixture; the two timing tests; test 82 reshaped. Every prior case stays as it is (the 182-row sweep, the 50 recipes).
- [ ] **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `unit`; lint gate; the cr17 review's 20 kills still die plus the four mutations above. **Step 5: One commit**, CR2's subject.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: the ritual override file is the operator's — the orchestrator guard denies writing or removing .claude/ritual-override (test: unit, lint)`

### CR3r (code, S) — re-plan of CR3 (rule A1): the per-key pid preference and the marker ordering are pinned by discriminating fixtures; the relaunch hint carries `--then` and never sits beside an alive pid; `group:` uses `%q`; stranded pid files are reaped

**dependsOn:** none

Gates `docs/reviews/2026-09-05-opus-review-cr6-CR3.md` and `…-cr9-CR3b.md`: CR3b fixed every CR3 major, but the two mutations the plan named as load-bearing survive — reverting the reader to the run-level pid (or deleting either arm of its per-key `case`) leaves 70/70 green because the fixture's review log is fresh, and swapping the marker's trap and write is invisible because the test waits for the marker before killing. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr9/CR3b task/CR3b && git cherry-pick -n FETCH_HEAD`; read both reviews in full; ONE commit with CR3's subject.

**Contract:** CR3b's behaviour stands; this round changes tests first and code only where a minor says so.
1. Discriminating in-flight fixtures (each red on CR3b's reader with the run-level pid restored): an OLD log (3 h) + dead `<KEY>.pid` + ALIVE run pid → counted stale, not listed; an OLD log + ALIVE `<KEY>.pid` + dead run pid → listed live with `pid N alive`; the same two shapes for `<KEY>.review.log` with `<KEY>.gate`; mutations: `pid=$wave_pid` unconditionally → fails; either `case` arm deleted → fails.
2. The marker ordering is pinned structurally AND behaviourally: a test asserts the `trap … EXIT` line precedes the marker write in `factory-review` (line-number comparison), and a kill test sends SIGTERM to the reviewer from a wrapper that stops it with SIGSTOP between the two lines (or uses a fake that exits between them) so the reversed order leaves a marker behind → fails.
3. The relaunch hint reproduces the original argv INCLUDING `--then "<text>"` (from `run.meta`'s `then:` line), is printed only when the wave's pid is dead, and never on a line that also says `alive`; a mixed wave (one key done, one without `.result`) gets the hint for the missing key's group only (say so in the README); `group:` values are written with `printf %q` and read back with `eval`-free parsing (a `read -r`/`xargs`-style unquote the test pins with a group containing a quote and a backslash).
4. Stranded `<KEY>.pid` and `<KEY>.gate` files (dead pid) are reaped by the reader when older than stale-after and mentioned in the summary line (`… and N stale pid files`); a recycled pid is guarded by comparing the file's mtime with the process start time (`ps -o lstart=`; a fake `ps` in tests) — deny "alive" when the process is younger than the file.
5. `meta` and `live` regain their `local`; a finished gate whose `.review.md` exists is listed as `gate done` rather than running.
6. `factory-task` never records `status=done` for a run with no commit: the FACTORY-RESULT block is taken from the seat's final output only, a `FACTORY-COMMITS N` claim is checked against `git rev-list --count base..head` (mismatch → `status=failed`, note `claimed N commits, found M`), and a block whose NOTES is a bare `ok` or a template echo is not a result (cr13 on 2026-09-05 was recorded done with zero commits after a provider error — the seat's brief template had been echoed).
Note for the second attempt (cr14): cr13 died on a provider error (`finish_reason: error`) with the tests and code written but uncommitted — `git -C /home/dalhaka/factory/ws/cr13/CR3r diff` is that work (it had reached the red run of Step 2); read it first, reuse what meets the contract, and prove red and the mutations yourself.

- [ ] **Step 1: Tests, red on CR3b** — the fixtures of 1 (four shapes), the structural and behavioural marker tests of 2, the relaunch hint with `--then` and the mixed wave, the `%q` round-trip, the reaper (age and recycled-pid cases), `gate done`. **Step 2: Red** (paste the failing test numbers). **Step 3: Implement.** **Step 4: Green** — shellcheck (factory-wave, factory-review, factory-task, factory-lib.sh, ritual.sh); `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats`; `unit`; lint gate; CR3b's 9 kills, CR5's 11 and CR1b's 21 still die; the cr9 review's M-B, M-B2, M-B3 and M-H now die. **Step 5: One commit**, CR3's subject.

**touches:** tools/factory/seat/factory-wave, tools/factory/seat/factory-review, tools/factory/seat/factory-task, tools/factory/seat/README.md, tools/ritual.sh, tests/unit/80-seat-driver.bats, tests/unit/92-ritual.bats
**acceptance:** unit, lint
**commit subject:** `factory: every seat run records what it is and what happens when it lands (run.meta, --then); gates leave a marker; runs survive the launching session (test: unit, lint)`

### CR3rb (code, XS) — CR3r fix round: `gate done` obeys the stale-after cut, the commit check keeps the seat's notes and exit code, `--then` and groups round-trip through `%q` in both directions, the recycled-pid test drives a fake `ps`, the README covers the pid files

**dependsOn:** none

Gate `docs/reviews/2026-09-05-opus-review-cr14-CR3r.md` — REJECTED on one major (both cr9 majors closed, 36/36 mutants die): the new `gate done` status sits above the stale-after cut, so every review gate that ever finished is listed forever — 23 dead lines on the live runs dir, 1518 bytes against the 1200-byte SessionStart budget, truncating the live seat run; seven minors. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr14/CR3r task/CR3r && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with CR3's subject.

**Contract:**
1. A `gate done` log older than stale-after is counted in the stale summary, never listed; younger, it is listed as `gate done` (mutation: the branch order restored → the live-shaped fixture with 23 old gate logs fails on the cap and the count).
2. The commits-mismatch arm fires only when the seat claimed `status=done`; it appends `claimed N commits, found M` to the seat's own FACTORY-NOTES instead of replacing them and keeps `exit_code=` on the result line (mutation: NOTES replaced → fails; the arm firing on a failed run → fails). Extra commits (claimed 1, found 2) stay `failed`, and the README says why (a stray board commit is a convention breach).
3. `--then` is written into the relaunch hint with `%q`; a group or a `--then` value containing a newline, tab or a `$'…'`-requiring byte is refused at write time with exit 2 (one line per key), so the eval-free unquote never meets the `$'…'` form (mutation: refusal removed → the newline-group test fails).
4. `stale_pid_count`, `gline` and the dead `ps_epoch file_epoch` declaration are fixed (`local`, or removed); shellcheck with `-o all` names no new global.
5. The recycled-pid test controls the outcome through the fake `ps` alone: the pid file's mtime is NOW and the fake reports a start time one minute later (the real `ps` would say alive) → not alive (mutation: the fake ignored → fails).
6. README: `<KEY>.pid` reaping, the recycled-pid guard, the stale-pid summary line, the commit check's two outcomes.

- [ ] **Step 1: Tests, red on CR3r** — the live-shaped fixture (23 old review logs with `.review.md`, three live logs, cap asserted ≤ 1,200 chars and the newest live key present); the two commit-check cases; the newline group and newline `--then`; the fake-`ps`-decides case. **Step 2: Red.** **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats`; `unit`; lint gate; real: `bash tools/ritual.sh inflight /home/dalhaka/nixos-agent-env` on this host prints no `gate done` older than stale-after and stays under 1,200 chars — paste the byte count. CR3r's 36 kills still die. **Step 5: One commit**, CR3's subject.

**touches:** tools/factory/seat/factory-wave, tools/factory/seat/factory-review, tools/factory/seat/factory-task, tools/factory/seat/README.md, tools/ritual.sh, tests/unit/80-seat-driver.bats, tests/unit/92-ritual.bats
**acceptance:** unit, lint
**commit subject:** `factory: every seat run records what it is and what happens when it lands (run.meta, --then); gates leave a marker; runs survive the launching session (test: unit, lint)`

### CR2r2b (code, S) — CR2r2 fix round: the operator lookahead is bounded, a guard fault DENIES instead of allowing, "never raises" is proven by a sweep, the remaining minors

**dependsOn:** none

Gate `docs/reviews/2026-09-06-opus-review-cr18-CR2r2.md` — REJECTED on one major: the `fold -w1`/`chars[]` rewrite that fixed the timing reads `chars[i + 1]` past the end of the array, which under `set -u` is a fatal unbound variable; `write_verdict` runs in a command substitution, so the subshell dies with one stderr line and the guard ALLOWS — `rm -rf .claude/ritual-override &`, `rm docs/superpowers/plans/x.md &`, `sed -i s/a/b/ docs/superpowers/plans/x.md &`, `rm -rf docs/superpowers/plans &`, `git clean -fd &`, `git stash -u &`, the same with `|`, `>`, `1>`, a glued `&`, `{ …; } &` and `…; ls &` (seventeen spellings, four regressions against main). Seven minors. Everything else CR2r2 promised is done (96/96, 395/395, 233 historic rows clean, 50/50 recipes, 23/24 mutants). Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr18/CR2r2 task/CR2r2 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with CR2's subject.

**Decision (orchestrator, 2026-09-06 ~00:50 CDT):** the header's "an internal error … allows, so a broken guard can never lock the session" is reversed for FAULTS. A fault allowed the exact command the whole line exists to deny; a fault that denies is noticed at once and is fixed with the Edit tool (the guard covers only Bash), so it cannot lock the session. Missing evidence (no git, no project dir) still allows, as before.

**Contract:**
1. Every array read past the end is bounded — `${chars[i + 1]:-}` (or an explicit `i + 1 < n` test) at the three lookaheads and anywhere else the tokeniser indexes ahead; the seventeen allowing spellings of the review DENY; the two pathspec-limited rows (`git clean 'a|b' -f`, `git stash 'a|b' -u`) stay ALLOW by design (item 5) (mutation: one `:-` removed → the trailing-`&` test fails).
2. A fault denies: an `EXIT` trap emits `deny "guard fault: <line>"` when the script is leaving with a non-zero status and no decision has been written, and every `reason=$(…)` command substitution over a verdict function checks its status and denies on non-zero with the same reason; the guard still exits 0 and prints one line on stderr; the header comment says so. Tests inject the fault without touching the guard: source the script (its `BASH_SOURCE` gate), override `tokenise_ctx` with a function that reads an unbound variable, feed a harmless payload to `main` → DENY with `guard fault`; the same through a function `main` calls directly in the main shell, not in a substitution (mutation: the trap removed → the second injected fault allows; the status check removed → the first allows).
3. Never raises, proven: one sweep test runs the guard over every row of the historic sweep (the review's 233), the 50 recipes and the seventeen spellings with stderr captured per row, and fails on the first non-empty stderr, printing the row (mutation: the `:-` guards removed → this test prints the unbound-variable line and fails).
4. Timing stays inside CR2r2's caps (200 path tokens < 100 ms, 200 symlink tokens < 200 ms, median of five); the runbook carries the numbers measured in THIS workspace with the host load beside them — the review measured 95.9/97.2 ms against a runbook saying 91/83.
5. Minors folded: `_ctx_emit`'s hoist pinned by a structural test (its definition line at column 0 precedes `tokenise_ctx()`); `dq`, `sq`, `dqd`, `sqd` declared `local` in `write_verdict` (the sourced guard, after a run, has no such globals: `declare -p dq` fails); the test at line 577 carries `cwd` at the top level like test 82; a quoted newline is emitted as a newline character of the token, not a space (a test on the token text); the runbook records the two pathspec-limited rows as accepted allows and the cr17 table's "every row DENIES" is amended to say so.

- [ ] **Step 1: Tests, red on CR2r2** — the seventeen spellings; the two fault injections; the sweep with stderr capture; the hoist, `local`, cwd and quoted-newline tests. Every prior case stays (the historic sweep, the 50 recipes, the 96 tests).
- [ ] **Step 2: Red** (paste the failing numbers and the unbound-variable line). **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `unit`; lint gate; cr18's 23 kills still die plus the four mutations above. **Step 5: One commit**, CR2's subject; end with the FACTORY-RESULT block, never prose.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: the ritual override file is the operator's — the orchestrator guard denies writing or removing .claude/ritual-override (test: unit, lint)`

### CR2r3 (code, S) — third re-plan of CR2 (rule A1): no verdict passes through a command substitution — guard functions return by variable, so every fault reaches the EXIT trap; the trap is installed only on the entry path; the runbook carries caps, not measurements; the sweep is pinned to its sources

**dependsOn:** none

Gate `docs/reviews/2026-09-06-opus-review-cr19-CR2r2b.md` — REJECTED on one major: CR2r2b checked the status of two verdict substitutions and left the outermost, `reason=$(bash_verdict …)` at :1356, unchecked — an injected fault in `bash_verdict` (and likewise in `json_unescape`, `resolve_path` and `missing_headings` on the Edit/Write arm) dies in the subshell, main carries on, the script exits 0, the EXIT trap sees a clean exit, and removing the override file ALLOWS silently; the header and the runbook claim a general property that is false there. Everything else is right: the seventeen spellings deny, the sweep, the trap, 30/30 mutants, 104/104, 403/403. Six minors. Per-site status checks are the wrong shape — twenty-four substitutions over twelve guard functions each need one, and the next edit forgets one again. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr19/CR2r2b task/CR2r2b && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with CR2's subject.

**Decision (orchestrator, 2026-09-06 ~02:10 CDT):** the fault channel is structural, not per site. No function defined in the guard is ever called inside `$(…)`: every guard function returns through one global (`_ret`, copied to a local at once by the caller, never another guard call between a call and its read), runs in the main shell, and a fault under `set -u` therefore kills the main shell, where the EXIT trap denies. Only external commands (`git`, `realpath`, `readlink`, `cat`, `ps`) may stand inside a substitution, and their failure is missing evidence, handled at the site as today. The runbook stops carrying measured timings — three rounds carried stale figures — and states the two caps and the command that measures them.

**Contract:**
1. Structural: a bats test extracts every `$(<name>` callee from `tools/orchestrator-guard.sh` and asserts none is a function the file defines (its `^name()` lines); the twenty-four current sites (`json_string` 7, `json_unescape` 6, `apply_edit` 2, `write_verdict`, `resolve_path`, `pad_operators`, `normalise_command`, `multiedit_after`, `missing_headings`, `git_verdict`, `bash_verdict`) are rewritten to `fn args; x=$_ret` (mutation: one `reason=$(bash_verdict …)` restored → the structural test fails AND the `bash_verdict` fault injection allows).
2. Fault injections, one per function on both arms — `bash_verdict`, `git_verdict`, `write_verdict`, `json_unescape`, `resolve_path`, `missing_headings`, `apply_edit` — each overriding the function after sourcing with one that reads an unbound variable, running the entry path in a subshell with the trap installed, on a protected payload → DENY with `guard fault`, exit 0, the guard's own one stderr line present (bash's own diagnostic may precede it) (mutation: the EXIT trap removed → every injection allows).
3. The trap is installed only on the entry path (inside the `BASH_SOURCE` gate or as the entry function's first statement), never at source time, so a sourcing bats test keeps its own traps; a test asserts `trap -p EXIT` prints nothing after sourcing (mutation: the trap moved back to top level → fails). Missing evidence (no git, no project dir, no cwd, a non-string command) still ALLOWS with empty stderr — the CR2r2b tests for it stay.
4. The sweep pinned to its sources: the fixture's first line is `# rows: N`; the test asserts the data-row count equals N, that every recipe line of the runbook's recipe section appears in the fixture, and that the seventeen spellings of the cr18 review (literals in the test) appear (mutation: one recipe removed from the fixture → fails; N wrong → fails).
5. Minors folded: the runbook's timing paragraph carries the caps (100 ms / 200 ms, median of five) and `nix develop -c bats tests/unit/91-orchestrator-guard.bats --filter timing` as the way to measure — no figures at all; the last nested-cwd payload (:844) reshaped and a structural test forbids a `"cwd"` key nested under `tool_input` anywhere in the bats file; the header comment states the structural rule in place of the per-site claim.
6. Timing caps still met — the refactor removes twenty-four subshells and adds none.

- [ ] **Step 1: Tests, red on CR2r2b** — the structural callee test (red: 24 sites); the seven fault injections (red on CR2r2b: `bash_verdict`, `json_unescape`, `resolve_path`, `missing_headings`, `apply_edit` allow); the trap-at-source test; the sweep pins; the nested-cwd structural test. **Step 2: Red** (paste). **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `unit`; lint gate; cr19's 30 kills still die plus the four mutations above; the timing tests pass. **Step 5: One commit**, CR2's subject; end with the FACTORY-RESULT block, never prose.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, tests/unit/91-orchestrator-guard-sweep.txt, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `session: the ritual override file is the operator's — the orchestrator guard denies writing or removing .claude/ritual-override (test: unit, lint)`

### CR2r3b (code, S) — CR2r3 fix round: every guard function is fault-safe by a behavioural loop, not a grep — a fault in ANY of them denies on every arm; no guard function inside any subshell form; the sweep holds the historic corpus; flake.nix in touches

**dependsOn:** none

Gate `docs/reviews/2026-09-06-opus-review-cr20-CR2r3.md` — REJECTED on two majors: (1) `missing_headings` calls the guard function `headings` inside two process substitutions (`comm -23 <(headings …) <(headings …)`), so an injected fault there dies in the subshells, the parent survives with status 0, and a heading-removing Edit on a plan ALLOWS silently — the structural test greps only `$(`, and a pipe site passes it too; (2) `flake.nix` was edited outside touches (five lines copying `docs/runbooks/session.md` into the `unit` sandbox for the recipe-pin test — necessary, and a plan defect: the touches list omitted it). Everything else lands: the 24 substitutions gone, 8/8 injections deny, the trap on the entry path only, 115/115, 414/414, 416 rows identical to CR2r2b, 47/47 recipes, both timing caps met, zero stderr over ~1,900 payloads. Four minors. Fresh workspace from main; `git fetch -q /home/dalhaka/factory/ws/cr20/CR2r3 task/CR2r3 && git cherry-pick -n FETCH_HEAD`; read the review in full; ONE commit with CR2's subject.

**Contract:**
1. The property is pinned behaviourally and totally: one bats test sources the guard, enumerates EVERY function the file defines (its `^name()` lines — 24 today; the test derives the list, never hard-codes it), and for each one in turn overrides it with a body that reads an unbound variable and runs the entry path in a subshell on three payloads — a Bash removal of the override file, an Edit that removes a typed heading from a plan, a Write onto a plan — asserting DENY with `guard fault` and exit 0 for every function × payload (mutation: `<(headings …)` restored → the loop fails on `headings`; a guard function moved to the right of a pipe → fails on that function).
2. No guard function inside any subshell form: `headings` (and any other) is called in the main shell and its result held in a variable or a temp file before `comm`/`diff` run over external commands only; the structural test's scan covers `$(`, backticks, `<(`, `>(`, a guard-function name after `|`, and `( name` — a fast hint beside the loop of item 1 (mutation: the process substitution restored → both tests fail).
3. The sweep holds the historic corpus: the fixture carries every command in the tables of `docs/reviews/2026-09-05-opus-review-cr17-CR2rb.md` and `docs/reviews/2026-09-06-opus-review-cr18-CR2r2.md` (233 rows), the runbook's recipes and the seventeen spellings; a test extracts the table cells of those two review files (they are byte-frozen once filed) and asserts each command is a fixture row; `# rows: N` stays exact (mutation: one review row removed from the fixture → fails).
4. The `_ret` discipline everywhere: every guard call is followed by a copy into a local before any test on it (the `missing_headings` site at :1441 included); a structural test asserts no line tests `$_ret` directly (`[ … "$_ret" … ]`, `[[ … $_ret … ]]`, `case $_ret`).
5. The header records the known symlink limitation the gate noted: a removal THROUGH a symlink that points into the plans directory (`rm plans-link/x.md`) allows on main and here alike — the guard judges the write's real target for symlinks out of the plans dir, not for links into it; stated, not fixed (a CR2 follow-up if the operator wants it).
6. `flake.nix` is in touches: the five lines that copy `docs/runbooks/session.md` into the `unit` sandbox stay (mutation: the copy dropped → the recipe-pin test fails inside `nix build .#checks.x86_64-linux.unit`).

- [ ] **Step 1: Tests, red on CR2r3** — the every-function loop (red on `headings`); the widened structural scan; the review-table extraction against the fixture; the `_ret` structural test. **Step 2: Red** (paste). **Step 3: Implement.** **Step 4: Green** — shellcheck; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `unit` (with `--rebuild`); lint gate; cr20's 16 kills still die plus the four mutations above; both timing caps met. **Step 5: One commit**, CR2's subject; end with the FACTORY-RESULT block in its exact form.

**touches:** tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, tests/unit/91-orchestrator-guard-sweep.txt, docs/runbooks/session.md, flake.nix
**acceptance:** unit, lint
**commit subject:** `session: the ritual override file is the operator's — the orchestrator guard denies writing or removing .claude/ritual-override (test: unit, lint)`
