# Session start — what a fresh session sees and how to fix it

When you open a session at `/new` (or clear, resume, or compact it), Claude Code
runs `tools/session-start.sh` through the `.claude/settings.json` SessionStart
hook and adds its output to the session context. That output has six parts, in
order:

1. **The board block** — the single `## START HERE` section of
   `docs/OPERATIONS.md`. This carries the plan: what is queued and parked, and
   what the operator owns. The queue's judgement lives in the START HERE block's
   "Now" paragraph, so when you want to know what to do next, read that
   paragraph first.

2. **The evidence bundle** — live facts (generation and revision, repo heads,
   which checks cover HEAD, Helm verdicts and since-when, open gaps) from the
   evidence store. The bundle is produced by `evidence bundle --markdown`; its
   source of truth is documented in `docs/runbooks/evidence.md`. This is the one
   part that stays the packaged command: it reads the store, not the tree.

3. **The task brief** — the near-term work, assembled from the plans
   (`docs/superpowers/plans`), reviews (`docs/reviews`), recent
   factory runs (`~/factory/runs`), the run log (`runs.jsonl`), and the ledger
   files `docs/ledger/plan-status.toml` and `docs/ledger/repos.toml`. It is
   produced by the *tree's* renderer, `pkgs/evidence/tasks.py
   --root <repo> brief`, run under the resolved interpreter
   (`RITUAL_PYTHON`, else `python3` on `PATH`, else the interpreter the packaged
   `evidence` wrapper names).

4. **The in-flight state** — the live seat runs (run, key, status, log age)
   listed by `tools/ritual.sh inflight`, plus the reset-ritual pointers: a
   handoff on `compact`/`resume`, a stale-stop idle notice and a board-debt
   warning, kept under `$XDG_STATE_HOME/nixos-agent-env/ritual`.

5. **The operator model** — `docs/board/operator-model.md`, the operator's
   preferences, owned items, the six invariants and the live-items index,
   derived from the brief and the decisions. It is printed between the in-flight
   part and the pointer.

6. **One pointer** — `docs/runbooks/session.md` (this file), so you always know
   where the map to all of this lives.

The script never fails the session, never evaluates the flake, and prints
nothing at all when `FACTORY_RUN` is set (factory agents) or when the checkout
is a linked worktree.

A hook never calls a host-packaged copy of tree code: the task renderer is
always this tree's `pkgs/evidence/tasks.py` (via `ritual.sh` for the board
check and `session-start.sh` for the brief). The packaged `evidence` command is
used only for `bundle`, which reads the store rather than the tree.

## Budgets (per-part caps)

Each part is budgeted separately so the task brief and the pointer survive even
when the board or the bundle is huge. A part over its cap is cut at the cap and
followed by one line `…<part> truncated at N chars (SESSION_START_CAP_<PART>)`.
Every cap slices characters (hence "chars"), not bytes:

- `SESSION_START_CAP_BOARD` (default **2300**) — the board block.
- `SESSION_START_CAP_BUNDLE` (default **2100**) — the evidence bundle.
- `SESSION_START_CAP_BRIEF` (default **1400**) — the task brief.
- `SESSION_START_CAP_INFLIGHT` (default **1000**) — the in-flight state.
- `SESSION_START_CAP_OPERATOR` (default **500**) — the operator model.
- the **pointer** — `docs/runbooks/session.md`, printed last, never capped.
- `SESSION_START_CAP` (default **8000**) — the total ceiling, applied to the
  assembled output after the per-part caps.

The five capped parts default to 2,300 + 2,100 + 1,400 + 1,000 + 500 = 7,300
chars; the six headings, the truncation lines and the pointer fit in the
remaining 700 chars of the 8,000 total, so the pointer always survives even
when every part overflows. A non-numeric `SESSION_START_CAP_<PART>` falls back
to that part's default rather than printing it uncapped.

To keep the task brief inside its budget, the brief's `Record (7 d)` line is
abbreviated (`N rej, M plan (vac a, miss b, under c, fact d)`; the exact counts
and their meaning live in `docs/ledger/plan-defects.toml`, see
`docs/runbooks/evidence.md`).

## Regenerate by hand

```bash
bash tools/session-start.sh </dev/null
```

This prints exactly what the hook would have added. The operator model is one
`## Operator model` heading (the file's own `# ` H1 does not match), so:

```bash
bash tools/session-start.sh </dev/null | grep -c '^## Operator model'   # prints 1
```

Always close stdin when running the hook by hand: when stdin is not a terminal
the hook reads the SessionStart payload from it (`read -r -d '' -n 8192`), so a
hand run whose stdin is an open, silent pipe — an agent's shell tool, a
`timeout` wrapper without `</dev/null` — blocks until killed. Under Claude Code
the payload arrives and closes, so the real session start is unaffected; a
`read -t` guard is owed to the next session-start task.

## When nothing shows at `/new`

First see what the script itself prints:

```bash
bash tools/session-start.sh </dev/null | head
```

If that shows the board block, the hook is misconfigured: confirm
`.claude/settings.json` is present (it must contain the `SessionStart` hook with
matcher `startup|clear|resume|compact`). If the script is silent, confirm the
checkout you opened is not a linked worktree (the hook is deliberately silent
there) and that `FACTORY_RUN` is not set.

## The reset ritual

The reset ritual is what you run before any reset — compaction, `/new`, or a
pause — so the next session (or you, after a reboot) can pick up where you left
off from what is written down, not from what the context happened to hold. It is
the orchestrator-side half of the context-reset design
(`docs/superpowers/specs/2026-09-05-context-reset-ritual-design.md`); the lint
hook below is its derived half.

### The ten ordered steps

Derived steps carry no judgement and are what the hooks check; judgement steps
are the model's and are bounded by shape. Cost: steps 1–5 and 9 are commands,
under a minute together; 6–7 are the only prose.

1. **File and commit every review** (`docs/reviews/`): untracked or modified
   review files are a Stop-hook block, and reviews are committed *before* any
   integrate → ff (a commit between the two diverges `main`).
2. **Land or park staged work.** Plan sections written this turn are committed
   (docs-only, `(test: lint)`); code you changed is committed or reverted. Test:
   `git status --short --untracked-files=no` is empty for the paths in the Stop
   list below.
3. **Integrate then fast-forward, back to back, gated on both exit codes**
   (`factory-integrate … || exit 1` then `git pull --ff-only || exit 1`), then
   assert the dependency's file exists in `main` before any dispatch.
4. **Regenerate and commit the board block** — `evidence tasks --root .
   write-board`; the pre-commit hook re-derives and refuses drift.
5. **Record in-flight runs and gates** — derived from `~/factory/runs`: every
   `<KEY>.log` without `<KEY>.result` plus its `run.meta` (repo, base, groups,
   pid, launched-at, `then:`).
6. **Append the turn's log entry** (`docs/board/log-2026-09.md`, newest first,
   ≤12 lines): what landed, what was decided, what was rejected, what is running.
7. **Rewrite START HERE's Now paragraph** (≤10 lines): objective, in flight →
   next action, open operator decisions, the one next step. Commit board + log
   together: `docs: board — … (test: lint)`.
8. **Memory** only for durable lessons (a rule that generalises), never for
   status. Usually nothing.
9. **Print the brief** — `bash tools/session-start.sh | head -60` — and read it
   as the next session will: if the board and brief alone would not let a
   stranger continue, fix the Now paragraph, not the memory.
10. **Reset** — `/new`. After a reboot or a crash the same ten steps are the
    recovery path, run by the next session from the handoff the PreCompact hook
    prints.

### The three hooks and their reasons

Two of the three hooks share one script, `tools/ritual.sh <subcommand> <repo>` —
Stop and PreCompact; SessionStart is the separate `tools/session-start.sh`, which
calls the ritual script's `inflight` subcommand as one internal step for the
in-flight table — a helper call, not a hook registration. The shared script is
bash, `set -u` and never exits non-zero except to block, silent when
`FACTORY_RUN` is set or the checkout is a linked worktree. State lives outside
the repo under `${XDG_STATE_HOME:-$HOME/.local/state}/nixos-agent-env/ritual/`;
malformed stdin degrades to allow with a warning, never to a block.

- **Stop** (`ritual.sh stop`) — blocks the end of a turn. Registered under
  `"Stop"` in `.claude/settings.json`. On a block it prints
  `{"decision":"block","reason":"<fix>"}` (exit 0); otherwise prints nothing. It
  enforces the *derived* half of the ritual so a reset never loses state:
  untracked or modified reviews, dirty plans/board/log/ledger, a stale queue
  block (`evidence tasks --root <repo> check --board`), and board debt (≥
  `RITUAL_BOARD_DEBT`·6 landings/gates since the board was written). It blocks at
  most `RITUAL_MAX_BLOCKS` (2) per `session_id`; on allow it stamps `last-stop`
  for the idle detector.
- **PreCompact** (`ritual.sh precompact`) — writes a derived `handoff-<sid>.md`
  to the state dir on compaction/`/new`, carrying the dirty path and the
  in-flight line, so the state survives even when you walk away mid-step.
- **SessionStart** (`tools/session-start.sh`) — prints the board's START HERE
  (the plan), the evidence bundle, the task brief, the in-flight table and the
  reset-ritual pointers (a handoff, a stale-stop idle notice, and the Stop
  checks still unmet — recomputed on the live tree by `ritual.sh unmet`, never
  replayed from `ritual.log`, whose lines outlive the state they name) at the
  start of the next session.

The **Stop hook enforces the derived half** of the ritual: the mechanical steps
(commits, board currency) are checkable and checked; the judgement (the Now
paragraph's content, the log's quality) is bounded by shape instead — the lint
keeps the Now paragraph to ten lines (`githooks/pre-commit`).

### The override

`.claude/ritual-override` is the operator's (the response to a blocked ritual is
"ask for it"). When the operator installs it, the Stop and SessionStart hooks
note it and stop blocking on the derived checks — a deliberate, operator-only
escape hatch for a turn that must end without the full ritual. The orchestrator
guard refuses to write or remove that file.

### When to `/new`

The operator's relevance rule, quoted in substance (see the design spec for the
full input): **the data gives a slope, not a threshold** — the dominant
degradation in agentic sessions is *context pollution*, not raw length; a 150K
context of dead ends is worse than a 400K context of relevant code. Practically:
`/new` at **task boundaries regardless of size** — a wave landed and
fast-forwarded onto `main`, a gate batch filed and committed, a decision/spec/
plan recorded and committed, the operator's "test passed"; and, for one coherent
task, before the context grows past ~300–400K tokens (the only measured no-loss
point is ~256K), so auto-compaction is never the *first* reset of a long task.
A secondary trigger: any idle gap past the cache TTL is a natural reset point
(the next turn re-prefills the whole context at full price anyway). The ritual
runs before each `/new`; `/new` itself is step 10.

## Closing a legacy plan

When a plan is finished and no longer needs to appear in the task brief, mark it
closed by editing `docs/ledger/plan-status.toml` — set the plan's `status` row
to `done` (or `superseded`/`parked` as the decision dictates; the allowed values
are `done | superseded | parked | open`), and add a `note`. The task brief reads
that file, so the plan drops out of the brief on the next session start. Typed
plans (those with `### KEY (kind, size)` headings) need no row here — their
status is derived per task.

## Guard — what the orchestrator refuses to do

A second hook (`.claude/settings.json`, `PreToolUse`) runs
`tools/orchestrator-guard.sh` before every `Bash`, `Edit`, `Write` and
`MultiEdit` call in this checkout. It is deny-only and never raises: it only
ever *adds* a denial on stdout and always exits 0. A guard **fault** fails
closed, never open, by construction: no function the guard defines is ever
called inside a subshell — not a command substitution, process substitution,
pipe stage or `( … )` list; every guard function returns its result through one
global (`_ret`, copied to a local at once by the caller), so a fault
that aborts the shell under `set -u` reaches the `EXIT` trap, which **denies**
("guard fault"); either way it still exits 0 with one line on stderr, so a
broken guard can never lock the session by allowing what it must deny. It
enforces three rules:

1. **Typed plan headings are append-only.** The `### KEY (kind, size) — title`
   lines in `docs/superpowers/plans/*.md` — the ones the task graph reads —
   may be added but never removed or rewritten. To withdraw a task, add a
   status row (`withdrawn` or `parked`) to `docs/ledger/task-status.toml`
   rather than touching the heading.
2. **A Bash command that names a plan path together with a write verb is
   refused.** There is no "command position": the guard normalises a command
   (continuations, quotes, newlines and shell separators to spaces) and scans
   *every* token, so a launcher (`nix develop -c`, `timeout`, `nohup`, `time`,
   `!`, `xargs`, `bash -c "…"`, backticks), a newline, or a `;`/`&&`/`||` does
   not hide a write. The write verbs are `sed -i`/`perl -i` (with the `-i`
   option wherever it sits), `rm`, `mv`, `rsync`, `shred`, `unlink`, `rmdir`,
   `cp`/`install`/`ln`/`dd` (which deny only when the plan is the destination),
   `tee`, `truncate`, `ed`, `find` with `-delete`/`-exec`, `git clean`, `git
   mv`, `git rm`, `python*` writing with `write_text`/`open(…,"w")`, a
   `>`/`>>`/`>|` redirect, and `git checkout --`/`git restore`. The plans
   *directory* — or any ancestor of it (`docs/superpowers`, `docs`, `.`, the
   project root) — names every plan for the delete family, and a relative path
   is resolved against the command's working directory (the payload `cwd`, plus
   every `cd`/`pushd`). Read verbs (`cat`, `grep`, `sed -n`, `head`, `tail`,
   `diff`, `wc`, `git diff/show/log`, `ls`, `find` without `-delete`/`-exec`)
   never deny. To append a section to
   a plan, use the **Edit**/**Write**/**MultiEdit** tool rather than a shell
   heredoc: the guard reads the payload, lets a *new* `### KEY (kind, size) —
   title` heading through, and refuses any removal or rewrite of an existing
   one.
3. **Any git invocation that rewrites history is refused, wherever it appears.**
   A token whose basename is `git` marks a git invocation; its subcommand is the
   first later token that is not a `-…` option (nor the value of a value-taking
   option), and `git commit --amend`, `git push`, `git rebase`, and `git reset
   --hard` are refused. The host mutations — `sudo`, `nixos-rebuild`, mutating
   `systemctl`, writes under `/run/baskets` and `/var/lib/{baskets,helm,
   egress-broker,lanes,secrets}` — are refused as before.

4. **`.claude/ritual-override` is the operator's (`the ritual override is the
   operator's; ask for it`).** One PROTECTED list of `(path, kind)` entries —
   `docs/superpowers/plans` (dir) and `.claude/ritual-override` (file) — feeds
   every arm (the plan-write arm, the override arm, and the Edit/Write/MultiEdit
   path rule); there is no hard-coded path and no early `break`, so every entry
   is evaluated. For the file, its parent `.claude` and every ancestor down to
   the project root and `/` count as naming it for the **delete family** — `rm`,
   `mv`, `rmdir`, `rsync`, `shred`, `truncate`, `find -delete`/`-exec`, `git
   stash -u`/`--include-untracked`/`-a`/`-au` (and the modern `git stash push
   -u` / `save -u`), `tar`/`unzip`/`cpio` extracting into `.claude` (`-C
   .claude` or an output path under it, or a `cwd` already inside `.claude` with
   no `-C`/`-d`), `chmod`/`chown`/`chattr` on the file or on its parent
   `.claude` (reachable via `-R`), and `xargs` carrying a delete verb — so
   `rm -rf .claude`, `mv .claude .claude-old`, `git stash -u`, `git stash push
   -u`, `tar -C .claude -xf x.tar`, `chmod 000 .claude/ritual-override`, `chmod
   -R 000 .claude`, `xargs rm < .claude/list`, and a bare `git clean -fd` are
   all refused even when they never name the file itself. A
   *glob* token under `.claude/` — `rm -rf .claude/*`, `mv .claude/* /tmp/`,
   `shred .claude/*`, `rm .claude/[r]itual-override` and every other `*`/`?`/
   `[`/`{` spelling — names the file too (a raw-text fallback, because a glob
   token cannot canonicalise). `dd of=…` is admitted into the token scan, and
   python/perl removal spellings (`os.remove`, `os.unlink`, `unlink(`,
   `.unlink()`, `os.rename`, `os.replace`, `shutil.move`, `shutil.rmtree`) and
   write spellings (`write_text`, `open(…,"w")`) naming it are refused. Reads
   (`cat`, `ls -la .claude`, `stat`, `git status`, `test -f`) stay allowed.

   The pathless git over-denials are narrowed: `git clean` denies only with
   `-f` (so `git clean -n`, `git clean -nd` allow), `git checkout`/`git restore`
   deny only on a protected path or a bare `--`/`.` (so `git checkout main`,
   `git checkout -b x`, `git restore --staged k` allow), and `git stash` without
   `-u`/`-a` allows. A `git commit -m "…"` message is prose and is never scanned
   for verbs or paths: every `-m`/`--message` argument is exempt (not only the
   first), in its glued forms too — `-am '…'`, `-m'…'`, `--message='…'` — so a
   newline or a bare word after a message resumes the scan. The ancestor rule
   counts only *ancestors* of `.claude`, not its
   descendants: a named sibling such as `.claude/worktrees/x` is **not**
   over-denied — `rm -rf .claude/worktrees/x` stays allowed — and
   `.claude/ritual-override` outside the project
   (`rm /tmp/other/.claude/ritual-override`) is also allowed. A *glob* under
   `.claude` at any depth (`rm -rf .claude/worktrees/*`) does name the file and
   is refused, even though the specific sibling is not.

   Over-denials are accepted on purpose. `ls .claude && rm /tmp/x` is refused
   (the `rm` is a delete verb and `.claude` is named, even though the two are in
   different clauses), `git checkout --` is refused (a bare `--` means the whole
   worktree), a glob under `.claude` at any depth (`rm -rf
   .claude/worktrees/*`) is refused (the raw-text fallback treats it as naming
   the file), and extracting an archive into the project root with no
   destination (`tar -x`, `unzip`, `cpio -i` without `-C`/`-d`) is refused (the
   archive could carry the override). Flags are clause-local, so a flag in one
   clause does not arm a
   verb in another — `rm -f result && git clean` and `ls -a && git stash` allow.
   These are the deny-only trade: a command that only *reads* `.claude` or that
   names a specific sibling still allows.

   **To lift the guard, the operator sets `ORCHESTRATOR_GUARD=off` in the
   session.** The flag is read from the hook process's own environment — an
   agent's Bash payload cannot set it for itself, because a `VAR=x cmd` prefix in
   a command only affects that command's child process, not the PreToolUse hook.
   (The alternative — removing the PreToolUse entries from `.claude/settings.json`
   — also works but is not the wired switch.)

Because the guard scans tokens rather than command positions, it deliberately
over-denies: `echo "git commit --amend"` and `rm /tmp/x && cat <plan>` are
refused even though no refusal-worthy command actually runs. That is the
accepted trade of a deny-only guard. Three more accepted over-denials were met
on 2026-09-06 after CR2r3b landed, each with its recipe: a `sed -i` on the
board whose replacement text merely mentions the plans directory is refused —
edit the board with the Edit tool; a compound merge command that carries
`git checkout <rev> -- <paths>` or `git add -u` beside the merge is refused —
run the plain `git fetch … && git merge --no-edit FETCH_HEAD`, resolve a board
or MAP conflict by regenerating the file (`write-board`, `repomap.py write`, or
`git show FETCH_HEAD:<file> > <file>`), then `git add <named files>`; a heredoc
whose prose contains the word "override" beside a redirect is refused — write
message and memory files with the Write tool. Two narrow **accepted allows** remain by
design: `git clean 'a|b' -f` and `git stash 'a|b' -u` — where a quoted operator
is a single *pathspec* argument that names no protected path — stay allowed (the
quote fix narrows the clause split, it does not claim every row denies), and a
quoted newline inside a token is emitted as a newline character of that token,
not a space.

The guard is bash, not python3: the bare host has no `python3`, and
`nix develop -c python3` costs ~5 s of flake evaluation per call. One token pass
computes both arms' facts, and every symlink token in a command is resolved in a
single `realpath` call. The timing caps are **100 ms** for a 200-path-token
command and **200 ms** for a 200-symlink-token command — median of five, measured
with `nix develop -c bats tests/unit/91-orchestrator-guard.bats --filter timing`
— inside the <300 ms per-call budget. The operator lookahead in the tokeniser is
bounded (`${chars[i + 1]:-}`), so a command whose last byte is an unquoted
`&`, `|` or `>` is denied, never faulted into a silent allow.

## Recipes — the workflow commands the guard must allow

The sweep fixture (`tests/unit/91-orchestrator-guard-sweep.txt`) is pinned
to this section: every command below must ALLOW, and the bats suite fails
if any line is missing from the fixture. One command per line.

```bash
git add docs/superpowers/plans/x.md
git add docs/OPERATIONS.md
git add -A
nix develop -c git commit -q -F /tmp/msg
nix develop -c git commit -q -m 'guard prose naming rm .claude and a plan path'
bash /tmp/scratch/launch.sh cr9 CR3b 2026-09-05-context-reset-ritual.md
git pull --ff-only /home/dalhaka/factory/ws/cr12/CR2b task/CR2b
tools/factory/seat/factory-integrate cr12 CR2b
nix build .#checks.x86_64-linux.unit -L --no-link
nix develop -c bats tests/unit/91-orchestrator-guard.bats
curl --noproxy '*' -s http://127.0.0.1:8080/health
pgrep -af factory-wave
git merge --abort
git checkout --theirs -- docs/OPERATIONS.md
git branch -f task/CR2rb deadbeefdeadbeef
git checkout -q --detach deadbeefdeadbeef
nix develop -c githooks/pre-commit
nix develop -c treefmt
evidence bundle --markdown
nix develop -c python3 pkgs/evidence/tasks.py --root . brief
python3 pkgs/evidence/repomap.py --root . write
nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06
nix build .#nixosConfigurations.core.config.system.build.toplevel
nix store diff-closures /run/current-system ./result
rm -f result
mv result result.old
git clean -nd
git checkout -b task/CR2rb
git checkout main
git restore --staged docs/OPERATIONS.md
git stash list
dsh-openrouter --denials 5
nix develop -c shellcheck tools/orchestrator-guard.sh
nix flake check -L
git log --oneline -5
git diff --stat
git show HEAD
sed -n '1,30p' docs/superpowers/plans/x.md
git worktree list
git fetch
nix develop -c pytest tests/broker -q
nix develop -c tests/run-mount-tests.sh
git status --porcelain
git rev-parse HEAD
git cherry-pick -n FETCH_HEAD
git merge --ff-only
tar -czf /tmp/backup.tgz docs
```

## Lessons of 2026-09-07 — two sessions in one checkout, and the guard's shape

Two orchestrator sessions wrote this tree the same afternoon (the landing-run
session and the orchestrator turn). It worked under one rule: **each session
commits only its own files and the derived queue block, and never edits the
other's in-flight board text.** What that took in practice:

- **Commit around the peer's staged edits with a pathspec commit** —
  `nix develop -c git commit -q -F <msgfile> -- <your file>`. A plain commit
  sweeps whatever the peer has staged into your commit under your message.
  The hook's queue-block regeneration still lands in the working tree; the
  peer adds `docs/OPERATIONS.md` before its own commit.
- **The pre-commit lint scans UNTRACKED plan and review files too.** A plan
  being written in ≤ 250-line pieces (a section without `acceptance` yet), or
  a review whose H1 is not literally
  `# Opus gate — seat run <run>, task <KEY> — <VERDICT>` on the line after
  the front-matter block, blocks BOTH sessions' commits until it is fixed. A
  review of a non-seat run (Codex's CX1b) still says `seat run`.
- **Talk to the peer, never poll it:** `ListAgents` names the other session;
  `SendMessage` with `notify_when_idle` delivers one message and one idle
  notice. The first such message unblocked a twenty-minute stall of staged
  edits.
- **The Stop hook blocks the turn on the PEER's uncommitted plan or review
  files too.** Wait for its commit; never revert or commit its files.
- **Scripts go through the Write tool, then `chmod +x`.** A single Bash
  command writing several files with `cat > … <<'EOF'` heredocs was refused
  with the ritual-override reason although nothing in it named the override.
- **A waiter that `pgrep -f`s its own pattern never exits** — match the
  binary's own argument, or watch for the result file.
- Under an agent harness the classifier's cwd is the audit directory and
  its shell commands are on record in `~/.codex/sessions/…/rollout-*.jsonl`
  (`"type":"custom_tool_call"` lines): the leak check for any hidden-label
  experiment is a grep over those.

## Lessons of 2026-09-08 — landing a wave alone, and the codex arm's first night

- **Trim a review's blank line by content, never by line number.** The gate
  writes a blank line between the closing `---` and the H1; a review with a
  `plan_defect_secondary` key has it on line 8, not 7. The form that always
  works: `awk 'prev=="---" && $0=="" && !done {done=1; prev=$0; next}
  {print; prev=$0}' "$r" > "$r.tmp" && mv "$r.tmp" "$r"` — in its OWN Bash
  command (the guard refused it beside a commit as a plan-file write).
- **`git add` an untracked review before a pathspec commit**, or the commit
  reports `pathspec … did not match any file(s) known to git`.
- **An approval's review commit carries the queue block.** The hook
  regenerates `docs/OPERATIONS.md` when a key leaves the queue and refuses
  the commit without it: run `tasks.py --root . write-board`, then commit the
  review and `docs/OPERATIONS.md` together (only when the board holds no
  peer edits).
- **A test that fakes a seat binary must build its PATH without the real
  one.** `PATH="$BIN:$PATH"` reaches `~/.local/bin/codex` on core when the
  fake is absent — a real `codex exec --sandbox danger-full-access` from a
  bats row. `SAFE_PATH` = the ambient PATH minus every directory holding an
  executable of that name; every driver invocation in the file uses it.
- **A negated assertion mid-test is inert under bats** (`set -e` ignores a
  `!` command that is not the test's last): write `[ "$(grep -c … || true)"
  -eq 0 ]` or `run …; [ "$output" = 0 ]`.
- **`checks_scope: dirty` means "the committed diff touches tests, flake.nix
  or githooks"** (`factory-task`, the SH4 mechanism), not an uncommitted
  file; do not chase it as one.
- **A seat's `partial` on a falsified plan assumption is the protocol
  working.** Codex staged its work, wrote the evidence, bypassed no hook and
  made no commit; the fix round carried the measured facts (the plan's
  Assumption 8 rewritten) and the staged diff (`git -C <old ws> diff
  --cached | git apply --index`). Measure before typing the fix round: a
  scratch `CODEX_HOME` without `auth.json` runs `codex exec` to the banner
  and the connect error without spending tokens; bwrap with a fake `/etc`
  proves a managed-config layer.
- **The guard reads shell redirects into TOML fixtures and `mv` beside a
  `docs/` path as plan-file writes.** Fixtures and scripts go through the
  Write tool; only the pure-read parts stay in Bash.
- **One session landing alone:** the runbook's two-session rules cost
  nothing when the peer has closed — keep the pathspec commits and the
  queue-block habit; the Stop hook still holds on a review the gate has just
  written, which is the cue to commit it.

## Where the rules live

Every rule the house enforces — the six invariants, the deny-only guards, the
standing policies, the working practices and the reset ritual — is inventoried
one row each in `docs/ledger/rules.toml`, each with its origin date, today's
measurement and the check that keeps it true (`python3 pkgs/evidence/rules.py
validate docs/ledger/rules.toml --root .` prints the `owed` count of load-bearing
rules with no check yet). A row's `verdict` is left empty for the operator, who
records `keep`, `amend` or `retire` through the dialog.

## Reading the map

`docs/MAP.md` is the repo map: a generated index of what lives where. It is
regenerated with:

```bash
python3 pkgs/evidence/repomap.py write
```