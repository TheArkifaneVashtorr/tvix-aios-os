# The context-reset ritual — design (2026-09-05; plan next)

What must be true at the moment an orchestrator session loses its context
(compaction, `/new`, `/clear`, a reboot), the ordered steps that make it true,
and which Claude Code hook enforces each step deterministically. Companion to
`2026-09-05-session-context-and-task-graph-design.md` (what a fresh session
*receives*); this spec is about what the dying session *leaves behind*, and
about when to die on purpose.

## Decisions taken in this design

- **Reset on relevance, not on a token count** (operator, below). The primary
  trigger is a task boundary; the ritual must be cheap enough to run at every
  boundary, so most of it is derived, not typed.
- **A reset happens through the written state — never by "just continuing".**
  The carriers are the board (START HERE + generated block), the board log, the
  plan sections, the review files, and the in-flight record. Transcripts are
  not a carrier.
- **Hooks enforce cleanliness, not judgement.** A Stop hook blocks a turn that
  would leave durable state uncommitted or the board block stale; a PreCompact
  hook writes a derived handoff; SessionStart prints it back. The Now paragraph
  and the log entry stay the model's, bounded by the shape guard.
- **No hook calls nix, commits, or writes inside the repo.** Hooks run under a
  second on the bare host PATH (bash, git, `evidence`; no jq or python3) and
  are silent for factory agents and linked worktrees, as `session-start.sh` is.
- **The escape hatch belongs to the operator.** `.claude/ritual-override`
  disables the Stop hook's block; the orchestrator guard (OG1r) denies the
  orchestrator writing it. Blocks are bounded (two per session) so a hook can
  never hold a turn forever.
- **In-flight intent is written at dispatch time**, not at reset time: the
  seat driver records what a run is and what happens when it lands
  (`~/factory/runs/<run>/run.meta`, `--then`), so the record exists even when
  the reset is a reboot nobody prepared for.

## When to `/new` (operator, 2026-09-05)

Operator input, quoted in substance; the studies cited are operator-supplied
and **not verified by us**:

> The data gives a slope, not a threshold. The dominant degradation in agentic
> sessions is context pollution — stale tool output, abandoned approaches the
> model keeps anchoring on; the context-rot literature (Chroma's study across
> 18 models) found distractor content hurts more than raw length. A 150K
> context of dead ends is worse than a 400K context of relevant code.
> Practically: `/new` at task boundaries regardless of size; for a single
> coherent task, 256K is the only measured no-loss point and linear
> interpolation puts multi-hop at about −5 F1 near 550K, so 300–400K is a
> defensible ceiling before you hand off via a written state file and restart.
> Anthropic's own Fable 5 launch data supports that pattern — file-based
> memory improved Fable's long-horizon performance three times more than it
> did Opus 4.8. Secondary trigger: any idle gap past the cache TTL (5 min, or
> 1 hr on this session) is a natural reset point, since the next turn
> re-prefills the whole context at full price ($6.25–$10 for 500K) anyway.

Design consequences, in our architecture:

1. **A task boundary is** any of: a wave landed and fast-forwarded onto `main`
   (integrate → ff done, `evidence tasks brief` shows the keys `landed`); a
   gate batch filed and committed (review files under `docs/reviews/` on
   `main`); a decision, spec or plan recorded and committed; the operator's
   "test passed". Each is a commit or a set of commits — so the ritual is
   keyed on git, and "boundary passed since the last board commit" is computable.
2. **Soft ceiling:** 300–400K tokens for one coherent task. No hook can
   observe context size (gap: the transcript's byte count is a proxy at best;
   not used). The rule is a rule of conduct: at a boundary, run the ritual and
   `/new`; never let auto-compaction be the first reset of a long task.
3. **Idle gap:** hooks cannot see idle time directly, but the Stop hook stamps
   the turn's end and SessionStart compares that stamp to now: an idle gap over
   `RITUAL_IDLE_MIN` (default 60) prints `ritual: idle 143 min — reset point;
   run the ritual and /new before new work`.
4. **Pollution hygiene:** the handoff carries the objective, what is in flight
   and its next action, open operator decisions, the one next step — never
   dead ends, abandoned approaches, tool output or chronology (rejections live
   in review files, chronology in the log). Now is capped at ten lines (CR4).

## What exists today (2026-09-05)

- `tools/session-start.sh` on `SessionStart` (`startup|resume|clear|compact`):
  START HERE, `evidence bundle --markdown`, `evidence tasks brief`, pointer;
  per-part caps; silent for `FACTORY_RUN` and linked worktrees.
- `githooks/pre-commit`: `tasks.py check`, `write-board` + refuse on drift, the
  E8 shape guard (one START HERE, ≤160 lines), `repomap.py check`.
- `tasks.py`: states `landed > approved/rejected > ran > recorded > ready/blocked`;
  G12b (queued) adds `running` for a `<KEY>.log` without `.result` younger
  than `--stale-after` (7200 s) — liveness by mtime only.
- Seat driver: `factory-task` writes `~/factory/runs/<run>/<KEY>.log` then
  `<KEY>.result` (`run:`, `key:`, `workspace:`, …); `factory-review` writes
  `docs/reviews/<date>-opus-review-<run>-<KEY>.md` (first line `# Opus gate —
  seat run <run>, task <KEY> — APPROVED|REJECTED`). Nothing records what the
  orchestrator meant to do when a run lands.
- OG1r (queued): deny-only PreToolUse guard; protected prefixes apply to write
  destinations; plan files change only through Edit/Write.
- Today's reboot killed five seat runs and two gates (nothing committed lost;
  relaunches reconstructed by hand from `pgrep`); twice a task was dispatched
  from a `main` missing its dependency because a review commit sat between
  integrate and ff.

## 1. State carriers: durable or lost at a reset

| carrier | where | survives compaction / `/new` | survives reboot | notes |
|---|---|---|---|---|
| START HERE prose (Now, operator owns) | `docs/OPERATIONS.md`, committed | yes | yes | judgement; ≤10-line Now |
| generated queue block | same, `tasks:begin/end` | yes | yes | derived; stale after every landing |
| board log entry | `docs/board/log-2026-09.md` | yes | yes | judgement; newest first |
| plan sections | `docs/superpowers/plans/*.md` | only when committed | same | uncommitted: the brief shows them (tree read), the seat's clone of `main` does not — the FD1-class trap |
| review files | `docs/reviews/*.md` | only when committed | same | untracked review = graph says approved, `main` says nothing |
| claims, plan-status, task-status | `docs/ledger/*.toml` | when committed | yes | |
| evidence store | `/var/lib/evidence` | yes | yes | append-only |
| seat logs and results | `~/factory/runs/<run>/` | yes | files yes, processes no | `.log` without `.result` = running or dead |
| in-flight intent | nowhere today → `run.meta` (CR3) | — | yes | written at dispatch |
| memory files | `~/.claude/projects/…/memory/` | yes | yes | preferences and lessons only, never status |
| background agents, Monitor watches, `run_in_background` shells | the Claude process | **no** | no | seat runs launched from Bash die if their process group dies — gap G1 below |
| scratchpad, transcript | `/tmp/claude-…`, `~/.claude/projects/…/*.jsonl` | scratch no; transcript yes | — | transcript is not a carrier by policy |

Invariant at the reset moment: every "only when committed" row is committed;
the queue block is not stale; every live run has a `run.meta`; the log has the
turn's entry; Now names the next step. The "yes/yes" rows need no step.

## 2. The ritual — ordered steps

Derived steps carry no judgement and are what the hooks check; judgement steps
are the model's and are bounded by shape.

1. **File and commit every review** (`docs/reviews/`): untracked or modified
   review files are a Stop-hook block (§3). Reviews are committed *before* any
   integrate → ff (field lesson: a commit between the two diverges `main`).
2. **Land or park staged work.** Plan sections written this turn are committed
   (docs-only, `(test: lint)`); code the orchestrator itself changed is
   committed or reverted. Test: `git status --short --untracked-files=no` is
   empty for the paths in §3's list. Scratch stays under the scratchpad.
3. **Integrate then fast-forward, back to back, gated on both exit codes**
   (`factory-integrate … || exit 1` then `git pull --ff-only || exit 1`).
   Then assert the dependency's file exists in `main` before any dispatch.
4. **Regenerate and commit the board block** —
   `evidence tasks --root . write-board`; the pre-commit hook re-derives and
   refuses drift. Derived; the Stop hook checks `check --board`.
5. **Record in-flight runs and gates** — derived from `~/factory/runs`: every
   `<KEY>.log` without `<KEY>.result` plus its `run.meta` (repo, base, groups,
   pid, launched-at, `then:`). No step for the orchestrator once CR3 lands;
   until then the Now paragraph carries run names and next actions by hand.
6. **Append the turn's log entry** (`docs/board/log-2026-09.md`, newest first,
   ≤12 lines): what landed, what was decided, what was rejected (review
   pointers), what is running and what happens when it lands. No dead ends
   beyond one clause each; no tool output.
7. **Rewrite START HERE's Now paragraph** (≤10 lines): objective, in flight
   → next action, open operator decisions, the one next step. Heading carries
   the time. Commit board + log together: `docs: board — … (test: lint)`.
8. **Memory** only for durable lessons (a rule that generalises), never for
   status. Usually nothing.
9. **Print the brief** — `bash tools/session-start.sh | head -60` — and read
   it as the next session will: if the board and brief alone would not let a
   stranger continue, fix the Now paragraph, not the memory.
10. **Reset** — `/new`. After a reboot or a crash the same ten steps are the
    recovery path, run by the next session from the handoff §3.2 prints.

Cost: steps 1–5 and 9 are commands, under a minute together; 6–7 are the only
prose — cheap enough for every boundary.

## 3. Deterministic enforcement — the hooks

All three hooks are one script, `tools/ritual.sh <subcommand> <repo>`, bash
only, `set -u`, never exits non-zero except to block, silent when
`FACTORY_RUN` is set or the checkout is a linked worktree (same test as
`session-start.sh`). State lives outside the repo in
`${XDG_STATE_HOME:-$HOME/.local/state}/nixos-agent-env/ritual/` (per
`session_id`; nothing new to gitignore). stdin JSON is read with bash pattern
matching on the flat fields we need (`session_id`, `stop_hook_active`,
`trigger`, `source`); a malformed stdin degrades to "allow" with a warning
line, never to a block.

### 3.1 Stop — `ritual.sh stop` (blocks the end of a turn)

Registered in `.claude/settings.json` under `"Stop"` with no matcher. Input
carries `stop_hook_active` (true when this turn is already a continuation
forced by a Stop hook). Output on block: stdout
`{"decision":"block","reason":"<fix>"}` with exit 0; otherwise nothing, exit 0.

Checks, in order, each under a second, each with the reason naming the fix:

| check | command | reason printed |
|---|---|---|
| untracked or modified reviews | `git status --short -- docs/reviews` non-empty | `ritual: commit the review file(s) <paths> — docs: gate review — <run> <KEY> <verdict> (test: lint)` |
| dirty plans, board, log, ledger | `git status --short --untracked-files=all -- docs/superpowers/plans docs/OPERATIONS.md docs/board docs/ledger` non-empty | `ritual: commit or revert <paths>; uncommitted plan sections are invisible to the seat's clone of main` |
| stale queue block | `evidence tasks --root <repo> check --board docs/OPERATIONS.md` non-zero | `ritual: the board's queue block is stale — evidence tasks --root . write-board, then commit` |
| board debt (proxy) | commits since the last commit touching `docs/OPERATIONS.md` that touch `docs/reviews/` or any non-`docs/` path ≥ `RITUAL_BOARD_DEBT` (default 6) | `ritual: N landings/gates since the board was last written — rewrite Now and append the log entry` |

Not checked (judgement, or not observable): the Now paragraph's content, the
log entry's quality, context size, whether a boundary is "really" a boundary.
The shape guard (one START HERE, ≤160 lines, Now ≤10 lines from CR4) and the
derived block reduce what judgement must carry to two paragraphs.

Bounding: the hook blocks at most `RITUAL_MAX_BLOCKS` (2) times per
`session_id` (counter file in the state dir; reset when a block's checks pass);
after that it allows and appends `ritual: allowed after 2 blocks — <unmet
checks>` to the state dir's `ritual.log`, which SessionStart prints. When
`stop_hook_active` is true the counter is honoured, not bypassed (the first
continuation is the point). On allow, the hook stamps `last-stop` (epoch) for
the idle detector. The whole `stop` path must measure under 1 s on core
(`check --board` is the heavy step — gap H2).

### 3.2 PreCompact — `ritual.sh precompact` (writes the handoff)

Registered under `"PreCompact"`, matcher `manual|auto`. It cannot cancel
compaction and we do not rely on its stdout reaching the model (gap H1); it
writes `handoff-<session_id>.md` in the state dir, and `SessionStart(compact)`
prints it. Contents, all derived: the time and `trigger`; `HEAD` and its
subject; `git status --short` for the §3.1 paths (what the ritual did not
finish); the in-flight table (§3.3); the first line of the newest log entry;
the unmet checks from §3.1 run in report mode. It never regenerates the board
or writes inside the repo — a compaction must not create a diff.

### 3.3 SessionStart — `session-start.sh` gains two parts

After the brief and before the pointer, budget `SESSION_START_CAP_INFLIGHT`
(1200 chars):

- **In flight** (`ritual.sh inflight`): one line per `<KEY>.log` without
  `<KEY>.result` under `~/factory/runs/*/`: `run key — pid alive|DEAD — log
  age — then: <text>`. Liveness: the pid from `run.meta` checked with
  `kill -0`; when no `run.meta` exists, the log's mtime against `stale-after`
  (G12b's rule). `DEAD` lines end with `relaunch: factory-wave <newname> <repo>
  <keys>` — the reboot recovery path, derived.
- **Ritual status**: `idle N min` when `now − last-stop > RITUAL_IDLE_MIN`;
  `handoff from <time>` + the handoff file when `source` is `compact` (or
  `resume` and a handoff for this session exists); the `ritual.log` tail
  (allowed-after-blocks lines) if any; `board debt N`.

### 3.4 Guard — `.claude/ritual-override` is operator-only

OG1r's protected-prefix rule gains the destination `.claude/ritual-override`
for Bash, and its Edit/Write/MultiEdit path rule denies the same path, reason
`the ritual override is the operator's; ask for it`. The Stop hook honours the
file when present (`ritual: override present — allowing`) and prints who last
touched it (`stat -c %U %y`). The operator removes it when done; the hook
reminds at every SessionStart while it exists.

### 3.5 Hook registration — `.claude/settings.json`

```json
"PreCompact": [{ "matcher": "manual|auto", "hooks": [
  { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/tools/ritual.sh\" precompact \"$CLAUDE_PROJECT_DIR\"", "timeout": 10 } ] }],
"Stop": [{ "hooks": [
  { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/tools/ritual.sh\" stop \"$CLAUDE_PROJECT_DIR\"", "timeout": 10 } ] }]
```

Shape pinned from the existing `SessionStart` entry and the superpowers
plugin's `hooks.json` (`type: command`, `matcher`, per-hook `timeout`). The
matcher values, `stop_hook_active`, the block JSON and SessionStart's `source`
are verified by CR1 step 0, not assumed (gap H1).

## 4. Failure modes

- **A hook that blocks forever.** Bounded to two blocks per session; the
  operator-only override; every reason names a command; malformed stdin or a
  failing `evidence` degrade to allow with a printed warning. A block never
  fires in worktrees or under `FACTORY_RUN`, so subagents and seats never see it.
- **Reboot mid-run.** Processes die, files stay: `run.meta` + dead pid → the
  `DEAD … relaunch:` lines at the next SessionStart; `tasks.py` (G12b) stops
  reporting the key as `running` once the log is older than `stale-after`, so
  it is schedulable again. Committed state is never at risk; the loss is bounded
  to the run's wall time. Improvement G1 (CR3): `factory-wave` re-execs under
  `setsid` when it is not a session leader, so a `/new` or a closed terminal
  does not kill a run — a reboot still does.
- **Two sessions on one checkout.** The Stop hook is path-scoped, so a peer's
  scratch never blocks; a peer's uncommitted review does — by design (the file
  is the durable state, whoever wrote it). Peer protocol, unchanged: explicit
  `git add <path>` never `-A`; `--untracked-files=no` is the cleanliness test;
  integrate → ff in one gated command; a review is committed by the command
  that filed it. Worktree sessions have their own tree and see no hook.
- **The board debt proxy misfires** (six small commits, no boundary). It blocks
  once with a reason; the fix (a two-line log entry, a Now refresh) is what the
  house rule asked for anyway. Threshold tunable; the count is printed.
- **Compaction with the ritual half done.** The handoff lists the dirty paths
  and unmet checks; the fresh context's first action is to finish them — the
  "reset through written state" rule holding even for an unchosen reset.

## 5. Testing — red first, mutation at the gate

bats under the existing `unit` check (`tests/unit/92-ritual.bats`, fake repo
and fake `evidence` as in `90-session-start.bats`; one `[ … ]` per line):

- stop: an untracked `docs/reviews/x.md` → stdout is the block JSON naming the
  file (mutation: drop `docs/reviews` from the path list → fails); a modified
  plan → block; a clean tree with fake `evidence … check --board` exiting 0 →
  empty stdout, exit 0, `last-stop` written; fake `check --board` exiting 1 →
  block naming `write-board`; third block in one session → allow + `ritual.log`
  line (mutation: counter never incremented → fails); `.claude/ritual-override`
  present → allow with the override line; `FACTORY_RUN` set → empty; linked
  worktree → empty; stdin garbage → allow with warning.
- board debt: fixture history with a board commit then 6 review commits →
  block; 5 → allow (mutation: `>=` → `>` fails).
- precompact: writes `handoff-<sid>.md` containing the dirty path and the
  in-flight line; makes no change under the repo (`git status` before == after).
- inflight: `r1/K.log` + `run.meta` with a dead pid → `DEAD … relaunch:` line;
  live pid (the test's own `$$`) → `alive`; `K.log` + `K.result` → absent;
  no `run.meta` and an old mtime → `DEAD (mtime)`.
- session-start: `source=compact` with a handoff file → printed under
  `## Handoff`; `last-stop` 2 h old → `idle 120 min`; existing tests unchanged.
- guard (`91-orchestrator-guard.bats`, on OG1r): DENY `touch`, `echo x >`,
  `rm` and the Write tool on `.claude/ritual-override`; ALLOW `cat` of it.
- seat driver (`80-seat-driver.bats`): `factory-wave --then "gate; ff; dispatch
  G12b"` writes `run.meta` with `then:`, `pid:`, `base:`, `groups:` (mutation:
  `then` not written → fails); `factory-review` leaves `<KEY>.gate` while running.
- lint (`githooks/pre-commit`): an 11-line Now paragraph fails; 10 passes.

## 6. Risks weighed

- **Hook stdout and matcher shapes are from memory of the Claude Code docs**
  (H1). Mitigation: CR1 step 0 runs each hook once by hand with `claude` and
  records the real stdin (`tee` to the state dir) before writing tests to it.
- **`check --board` in the Stop path may cost >1 s** (H2: it scans sibling
  repos and git logs). Measured in CR1; if over budget, Stop compares the
  block text against `write-board --stdout`-style output from a tree-only
  run (`--runs-dir /nonexistent --store /nonexistent`, as pre-commit does).
- **Blocking a turn that ends with a question to the operator.** The fix is a
  commit; the operator sees one extra turn. Accepted: an uncommitted plan
  behind a question is exactly the state that bit us.
- **More board commits.** One block regeneration per landing; the debt
  threshold keeps Now/log rewrites to boundaries, not turns. Runs launched
  before CR3 have no `run.meta` and degrade to G12b's mtime rule.

## 7. Tasks (for the orchestrator to place; house format)

### CR1 (code, S) — `tools/ritual.sh`: stop, precompact and inflight subcommands; PreCompact hook; SessionStart prints the handoff and in-flight state

**dependsOn:** none (G12b lands the `running` state independently; CR1 reads
the runs dir itself)

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

**dependsOn:** none (touches conflict with SB3b on `factory-task`? no — SB3b
touches the wrapper; `evidence tasks conflicts` to confirm at dispatch)

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
