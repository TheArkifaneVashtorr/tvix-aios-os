# Opus gate — seat run cr8, task CR2 — REJECTED

## Summary

Task CR2 on `task/CR2` in `/home/dalhaka/factory/ws/cr8/CR2`, base
`3d03caa` (main with OG1r2b's guard), head `91493a5`. Reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-cr8-CR2`.
Nothing under `/home/dalhaka/factory` was modified; the live repo's
`.claude/ritual-override` was never touched (every guard run used a throwaway
fixture at `…/scratchpad/fixture`).

**The gate brief's premise is wrong and must be corrected before anything else.**
The brief states "diffstat shows ONLY `tests/unit/91-orchestrator-guard.bats` +63 —
`tools/orchestrator-guard.sh` is NOT touched". It is touched. Verified in both the
clone and the source workspace:

```
$ git show --stat --format= 8a8705a          # identical in /home/dalhaka/factory/ws/cr8/CR2
 docs/OPERATIONS.md                    |   2 +-
 tests/unit/91-orchestrator-guard.bats |  63 ++++++++++++-
 tools/orchestrator-guard.sh           | 171 +++++++++++++++++++++++++++++++++-
 3 files changed, 232 insertions(+), 4 deletions(-)
```

So this is not a test-only pin: 8a8705a adds a new `override_verdict()` rule
(`tools/orchestrator-guard.sh:646-793`) plus an Edit/Write/MultiEdit arm
(`:853-859`). Red-before-green is genuinely satisfied — four of the five new tests
fail against the base guard. Checks are all green. All six CR2-targeted mutations
die, and og5's whole table reproduces unchanged.

It is rejected anyway, on the matrix. **Nine write/removal spellings of
`.claude/ritual-override` still ALLOW on the task's tree**, including
`rm -rf .claude` and `git clean -fd` — and `git clean` is a spelling the commit
body explicitly claims to cover. The file is untracked and not gitignored
(`git check-ignore .claude/ritual-override` → rc 1; `git ls-files .claude/` lists
only `settings.json`), so `git clean -fd` really does delete it. The root cause is
one line: the rule returns early unless some *token* canonicalises to the exact
file path (`:691`), so every directory-level spelling is invisible to it. The plan
rule solved exactly this problem with `is_plans_dir_or_ancestor` (`:389`); the new
rule has no equivalent arm.

## The central question

Branch (a) vs (b) as posed does not apply, because the guard *did* change. The
question reduces to (b): **does the task's guard leave a write/removal spelling
open?** It does — nine of them.

Method: `git show 3d03caa:tools/orchestrator-guard.sh` and
`git show 8a8705a:tools/orchestrator-guard.sh` extracted to
`…/scratchpad/guards/{base,task}.sh`; `cmp` says they differ (723 vs 890 lines),
and the task guard is byte-identical to the tip guard (`cmp` clean — 91493a5
touches only `docs/OPERATIONS.md`). Both were driven against a fixture project
(`…/scratchpad/fixture`, containing `.claude/ritual-override`, `k`,
`docs/superpowers/plans/test.md`, and a symlink `link-to-override`) with payloads
exactly as Claude Code sends them: compact JSON, `ensure_ascii=False`, `cwd` at the
top level, `CLAUDE_PROJECT_DIR` at the fixture. Driver:
`…/scratchpad/matrix.py`, `…/scratchpad/matrix2.py`.

The mechanism, at `tools/orchestrator-guard.sh:682-691`:

```bash
  # Does any token name the override file (any base)?
  local seen=0 b orig
  for t in "${toks[@]}"; do
    for b in "${bases[@]}"; do
      canon_path "$t" "$b"
      [ "$_canon" = "$override_canon" ] && seen=1
    done
    [ "$seen" -eq 1 ] && break
  done
  [ "$seen" -eq 0 ] && return
```

`override_canon` is the exact file (`:667`). A command that names only the
*directory* — `rm -rf .claude`, `mv .claude .claude-old`, `git clean -fd` (which
names nothing at all) — never sets `seen`, so the rule returns empty and the guard
allows. Contrast `plan_write_verdict`, which carries a second flag
`dir_ancestor_seen` fed by `is_plans_dir_or_ancestor` (`:389-400`, used at `:471`
and `:481`) precisely so that `rm -rf .` and `cd docs && rm -rf superpowers` are
caught. That arm was not carried over.

A second, narrower defect: the `dd` arm (`:730-754`) is **unreachable in practice**.
It scans forward for an `of=` token, but the token `of=.claude/ritual-override`
does not itself canonicalise to the override path, so `seen` is still 0 and the
function has already returned at `:691`. Measured:

```
dd if=/dev/null of=.claude/ritual-override                          -> ALLOW
dd of=<proj>/.claude/ritual-override if=/dev/null                   -> ALLOW
dd if=/dev/null of=.claude/ritual-override .claude/ritual-override  -> DENY   (needs a second, bare token)
```

The reason text is correct and matches what the subject promises:
`the ritual override is the operator's; ask for it` (`OVERRIDE_REASON`, `:93`).
Reads are all allowed with no over-denial (see the table and the over-deny probes
below). Performance is fine: 87 ms on a 200-path-token command, and bats test 53
(median < 300 ms) passes.

## The second commit

`91493a5` — `docs: board — CR2 landed (…); queue regen drops CR2, picks up CR3 CR4`.
Diffstat: `docs/OPERATIONS.md | 2 +-`. The only content change is the derived queue
block: `B1 CR2 CR3 CR5 FD1b …` → `B1 CR3 CR4 CR5 FD1b …`.

- **Not in `touches`** (`tools/orchestrator-guard.sh`, `tests/unit/91-orchestrator-guard.bats`),
  and the plan gives CR2 one commit. A convention breach.
- **Its subject overstates.** "CR2 landed" was not true of `main` when it was written;
  the body corrects it ("CR2 now landing on `task/CR2`"). The committed *board content*
  is not prose — it is the machine-derived queue block — and that block's content is
  true of the tree at that point, so the board of record is not falsified. The
  overstatement lives in the commit subject only.
- **Does 8a8705a stand alone?** For the acceptance gates, yes: at 8a8705a alone,
  `bats tests/unit/91-orchestrator-guard.bats`, `checks.unit` (251 tests) and
  `checks.lint` are all green (exit 0), and the guard + tests are self-contained.
  For `githooks/pre-commit`, no — but for a structural reason, not an implementer
  error. `pkgs/evidence/tasks.py:192` derives the queue from
  `git -C <repo> log --format=%s`, so the commit whose subject names CR2 changes the
  derivation the moment it exists. Measured at 8a8705a:

  ```
  $ nix develop -c githooks/pre-commit          # rc=1
  tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
  $ git diff docs/OPERATIONS.md
  -… B1 CR2 CR3 CR5 FD1b …
  +… B1 CR3 CR4 CR5 FD1b …
  ```

  No single commit can land CR2 with a self-consistent queue block. This is the H1
  chicken-and-egg already on the board, not a defect introduced here.

Recommendation: **drop 91493a5 at integration** and let the queue block be
regenerated by whatever commit lands next. It is a MINOR.

## Rule behaviour

Fixture `<proj>` = `…/scratchpad/fixture`; payload `cwd` = `<proj>` unless noted.
`base` = guard at 3d03caa, `task` = guard at 8a8705a (= tip). Reason column names
which rule produced the deny.

| spelling | base | task | reason |
|---|---|---|---|
| `rm .claude/ritual-override` | ALLOW | DENY | override |
| `rm -rf .claude/ritual-override` | ALLOW | DENY | override |
| `rm <proj>/.claude/ritual-override` | ALLOW | DENY | override |
| `mv k .claude/ritual-override` | ALLOW | DENY | override |
| `mv .claude/ritual-override /tmp/x` | ALLOW | DENY | override |
| `touch .claude/ritual-override` | ALLOW | DENY | override |
| `echo x > .claude/ritual-override` | ALLOW | DENY | override |
| `echo x >> .claude/ritual-override` | ALLOW | DENY | override |
| `echo x >\| .claude/ritual-override` | ALLOW | DENY | override |
| `echo x \| tee .claude/ritual-override` | ALLOW | DENY | override |
| `cp k .claude/ritual-override` | ALLOW | DENY | override |
| `install -m 644 k .claude/ritual-override` | ALLOW | DENY | override |
| `ln -sf /etc/hostname .claude/ritual-override` | ALLOW | DENY | override |
| `truncate -s 0 .claude/ritual-override` | ALLOW | DENY | override |
| `unlink .claude/ritual-override` | ALLOW | DENY | override |
| `shred -u .claude/ritual-override` | ALLOW | DENY | override |
| `git rm -f .claude/ritual-override` | ALLOW | DENY | override (via the bare `rm` token) |
| `git checkout -- .claude/ritual-override` | ALLOW | DENY | override |
| `git clean -fdx .claude/ritual-override` | ALLOW | DENY | override |
| `sed -i s/a/b/ .claude/ritual-override` | ALLOW | DENY | override |
| `perl -i -pe s/a/b/ .claude/ritual-override` | ALLOW | DENY | override |
| `cd .claude && rm ritual-override` | ALLOW | DENY | override (cd rebase) |
| `rm ritual-override` *(cwd=`<proj>/.claude`)* | ALLOW | DENY | override (payload cwd) |
| `echo x > ritual-override` *(cwd=`<proj>/.claude`)* | ALLOW | DENY | override |
| `cd sub && rm ../.claude/ritual-override` | ALLOW | DENY | override |
| `rm ../.claude/ritual-override` *(cwd=`<proj>/sub`)* | ALLOW | DENY | override |
| `pushd .claude && rm ritual-override` | ALLOW | DENY | override |
| `rm link-to-override` *(symlink)* | ALLOW | DENY | override |
| `echo x > link-to-override` *(symlink)* | ALLOW | DENY | override |
| `rm -rf .` | DENY | DENY | **plan rule**, not override |
| `rm -rf <proj>` | DENY | DENY | **plan rule** |
| `cd .claude && rm -rf .` | DENY | DENY | **plan rule** |
| `git clean -xdf <proj>` | DENY | DENY | **plan rule** |
| `find . -name ritual-override -delete` | DENY | DENY | **plan rule** |
| `python3 -c "open('.claude/ritual-override','w').write('x')"` | DENY | DENY | **plan rule** (`python*` arm, `:605`) |
| `python3 -c "…pathlib.Path('.claude/ritual-override').write_text('x')"` | DENY | DENY | **plan rule** |
| **`rm -rf .claude`** | ALLOW | **ALLOW** | — **HOLE** |
| **`rm -rf .claude/`** | ALLOW | **ALLOW** | — **HOLE** |
| **`rm -r <proj>/.claude`** | ALLOW | **ALLOW** | — **HOLE** |
| **`rm -rf .claude/*`** | ALLOW | **ALLOW** | — **HOLE** |
| **`cd .claude && rm *`** | ALLOW | **ALLOW** | — **HOLE** |
| **`rmdir .claude`** | ALLOW | **ALLOW** | — **HOLE** |
| **`mv .claude /tmp/gone`** / **`mv .claude .claude-old`** | ALLOW | **ALLOW** | — **HOLE** |
| **`git clean -fd`** (bare) | ALLOW | **ALLOW** | — **HOLE** |
| **`git clean -fd .claude`** / **`git clean -fdx .claude`** | ALLOW | **ALLOW** | — **HOLE** |
| **`git checkout HEAD -- .claude`** / **`git restore .claude`** | ALLOW | **ALLOW** | — **HOLE** |
| **`find .claude -name ritual-override -delete`** | ALLOW | **ALLOW** | — **HOLE** |
| **`dd if=/dev/null of=.claude/ritual-override`** | ALLOW | **ALLOW** | — **HOLE** (dead `dd` arm) |
| **`python3 -c "import os;os.remove('.claude/ritual-override')"`** | ALLOW | **ALLOW** | — **HOLE** |
| **`python3 -c "…pathlib.Path('.claude/ritual-override').unlink()"`** | ALLOW | **ALLOW** | — **HOLE** |
| `rsync -a /tmp/empty/ .claude/` | ALLOW | ALLOW | — (note) |
| `chmod 000 .claude/ritual-override` | ALLOW | ALLOW | — (note; not a content write) |
| `cat .claude/ritual-override` | ALLOW | ALLOW | correct |
| `cat <proj>/.claude/ritual-override` | ALLOW | ALLOW | correct |
| `ls -la .claude` | ALLOW | ALLOW | correct |
| `stat .claude/ritual-override` | ALLOW | ALLOW | correct |
| `git status` | ALLOW | ALLOW | correct |
| `test -f .claude/ritual-override` | ALLOW | ALLOW | correct |
| `cp .claude/ritual-override /tmp/y` | ALLOW | ALLOW | correct |
| `grep -c . .claude/ritual-override` | ALLOW | ALLOW | correct |
| Write `.claude/ritual-override` | ALLOW | DENY | override |
| Write `<proj>/.claude/ritual-override` | ALLOW | DENY | override |
| Write `link-to-override` (symlink) | ALLOW | DENY | override |
| Write `.claude/./ritual-override` | ALLOW | DENY | override |
| Write `.claude/../.claude/ritual-override` | ALLOW | DENY | override |
| Edit `.claude/ritual-override` (rel + abs) | ALLOW | DENY | override |
| MultiEdit `.claude/ritual-override` (rel + abs) | ALLOW | DENY | override |
| NotebookEdit on it | ALLOW | ALLOW | not matched (out of the settings.json matcher) |

Reason text on every override deny, verbatim:
`the ritual override is the operator's; ask for it` — it does say the override is
the operator's, as the subject promises.

Over-deny probes (`…/scratchpad/overdeny.sh`), all correctly ALLOW:
`rm .claude/ritual-override-notes`, `rm .claude/settings.json`,
`touch /tmp/ritual-override`, `rm /tmp/other/.claude/ritual-override`,
`echo ritual-override >> notes.md`, `git log --oneline`,
`ls .claude/ritual-override`. Perf: `elapsed_ms=87` on 200 path tokens.

## Checks

All run in the clone with `nix develop -c` / `nix build`.

| check | at tip `91493a5` | at `8a8705a` |
|---|---|---|
| `shellcheck tools/orchestrator-guard.sh` | rc 0 | rc 0 |
| `bats tests/unit/91-orchestrator-guard.bats` | rc 0, 59/59 ok | rc 0, 59/59 ok |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | rc 0 | rc 0 |
| `… unit --rebuild` (once) | rc 0, `ok 251 blocks files older than 7 days are reaped on each run` | — |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | rc 0, `All checks passed!` | rc 0 |
| `githooks/pre-commit` | rc 0, tree clean after | **rc 1** — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` |

No red check attributable to the code. The one rc 1 is the derived-queue
chicken-and-egg described under "The second commit"; the acceptance the plan names
(`unit`, `lint`) is green at both commits. 251 unit tests, matching the
implementer's note.

## Red before green

The base guard and the task guard are **different files** (723 vs 890 lines) — the
brief's "they are the same file" does not hold. So the red run is meaningful.

Method: the task's `tests/unit/91-orchestrator-guard.bats` left in place,
`tools/orchestrator-guard.sh` replaced by `git show 3d03caa:…` (`git diff --stat`
printed to prove the tree changed: `1 file changed, 2 insertions(+), 169
deletions(-)`), then `bats` run, then `git checkout --` and `cmp` back to the task
guard.

```
1..59
55 ok
not ok 54 bash: writing .claude/ritual-override is denied
not ok 56 write: the Write tool on .claude/ritual-override is denied
not ok 57 edit: the Edit tool on .claude/ritual-override is denied
not ok 58 multiedit: MultiEdit on .claude/ritual-override is denied
```

Four of the five new tests go red on the base; test 55
(`bash: reading .claude/ritual-override is allowed`) passes on the base by
construction, which is correct for an allow-side companion. After restoring the
task guard all 59 pass. Red-before-green is **satisfied**.

The section's premise ("the guard must change") was therefore **true**, and the
brief's premise correction runs the other way: the guard did change, and OG1r2b's
base guard covered none of these spellings.

One deviation from the plan's literal wording worth recording, not a finding: the
plan says "add the destination path to the protected prefixes (Bash)". The
implementer did **not** touch `PROTECTED` (`:75-82`, still the six absolute host
prefixes) and wrote a separate `override_verdict` rule instead. That is defensible —
`PROTECTED` is kept byte-identical to `hook-guard.py` and lane-submit by
`tests/lane/test_forbidden_lists_agree.py` (see the comment at `:73-74`), so a
project-relative path could not go there. But the substitution is what lost the
prefix/ancestor semantics that `rm -rf .claude` needs.

## Mutation table

Applied to `tools/orchestrator-guard.sh` in the clone, tree asserted changed
(`git diff --numstat` printed each row), full bats file run, then reverted;
`git status --porcelain` empty after every row (`ALL REVERTED, tree clean`).
Scripts: `…/scratchpad/mutate.py`, `…/scratchpad/runmut.sh`, `…/scratchpad/runmut2.sh`.

### CR2's own pin

| # | Mutation | numstat | Failures | Killed by |
|---|---|---|---|---|
| **M-A** | `override_verdict()` returns immediately (`:655`) | 1+/0− | 1 | 54 |
| **M-A2** | the `override_verdict` call unwired from `bash_verdict` (`:295`) | 1+/1− | 1 | 54 |
| **M-B** | the Edit/Write/MultiEdit override arm short-circuited (`:856`) | 1+/1− | 3 | 56, 57, 58 |
| **M-C** | `OVERRIDE_REASON` changed to `"nope"` (`:93`) | 1+/1− | 4 | 54, 56, 57, 58 — **reason text is pinned** |
| **M-D** | `rm`/`mv` dropped from the override verb list (`:707`) | 1+/1− | 1 | 54 |
| **M-E** | `override_canon` pointed at a different filename (`:667`) | 1+/1− | 1 | 54 |
| **CR2-M2** | both override token scans truncated to the first token (`:671`, `:704`, `i < n` → `i < 1`) | 2+/2− | **0** | **SURVIVES — the "no command position" contract is unpinned** |
| **CR2-M-cd** | the `cd`/`pushd` rebase removed from `override_verdict` (`:673`) | 1+/1− | **0** | **SURVIVES — relative-from-subdir behaviour is unpinned** |

The brief's M-A as literally worded (".claude removed from the protected
prefixes") does not exist: `PROTECTED` never contained `.claude`. The two rows
above are the equivalent kills, and both die. The pin is load-bearing: six of eight
CR2 mutations are killed. The two survivors are behaviours the guard *does* have
(measured DENY in the table above) but that no test asserts.

### og5's table, re-run on this tree

| # | Mutation | numstat | Failures | Killed by | vs og5 |
|---|---|---|---|---|---|
| **M-A** | `mv` removed from the plan operand writers (`:499`) | 1+/1− | 3 | 16, 43, 44 | same |
| **M-B** | `is_plans_dir_or_ancestor` short-circuited (`:391`) | 1+/1− | 1 | 44 | same |
| **M-D** | `-i*`/`--in-place*` detection disabled (`:488`) | 1+/1− | 2 | 16, 47 | og5 had 1 (47); my anchor is broader than og5's |
| **M-E** | lexical normaliser replaced by `realpath -m` per token (`:369-373`) | 6+/5− | 1 | 53 | same |
| **M-F** | quote stripping back to a space (`:121-123`) | 3+/3− | 1 | 52 | same |
| **M-G** | symlink exception removed (`[ -L ]` branch → `_canon=$p`) | 6+/5− | 1 | 35 | same |
| **M-H** | `>\|` removed from the redirect folds (`:138`) | 0+/1− | 1 | 48 | same |
| **M-I** | `pushd` dropped from the plan rebase verbs (`:455`) | 1+/1− | **0** | **SURVIVES** | same (og5 MINOR-3) |
| **M1** | `\n` dropped from `normalise_command` (`:120`) | 0+/1− | 2 | 20, 22 | same |
| **M2** | all five token scans stop after the first token | 5+/5− | 8 | 9, 16, 17, 20, 21, 22, 44, 45 | same list |
| **M3** | basename rule off (`:184`) | 1+/1− | 1 | 9 | same |
| **M4** | `plan_write_verdict` returns immediately (`:434`) | 1+/1− | 10 | 16, 17, 18, 22, 43, 44, 45, 46, 47, 48 | same list |

og5's results reproduce exactly, including the M-I survivor. CR2 did not weaken
OG1r2b's pins.

## Findings

### MAJOR-1 — `rm -rf .claude` and every other directory-level removal allows

`tools/orchestrator-guard.sh:691`

```bash
  [ "$seen" -eq 0 ] && return
```

`seen` is set only by a token whose canonical path equals the file itself
(`:682-690`, against `override_canon` at `:667`). Any spelling that names the
containing directory instead is invisible. Measured ALLOW on the task tree:
`rm -rf .claude`, `rm -rf .claude/`, `rm -r <proj>/.claude`, `rm -rf .claude/*`,
`cd .claude && rm *`, `rmdir .claude`, `mv .claude /tmp/gone`,
`mv .claude .claude-old`. Each destroys the operator's file. The plan rule solves
this with a second flag `dir_ancestor_seen` fed by `is_plans_dir_or_ancestor`
(`:389-400`, `:471`, `:481`); the override rule has no equivalent arm. `rm -rf .`
happens to deny — but by the *plan* rule, with the plan's reason, not the
override's.

### MAJOR-2 — `git clean` allows, contradicting the commit body

`tools/orchestrator-guard.sh:755-772` (the `git` arm) is behind the same `:691`
gate, so it fires only when a token already names the file exactly. Measured ALLOW:
`git clean -fd`, `git clean -fdx`, `git clean -fd .claude`, `git clean -fdx .claude`,
`git checkout HEAD -- .claude`, `git restore .claude`. The override file is
untracked and not ignored —

```
$ git check-ignore -v .claude/ritual-override ; echo rc=$?
rc=1
$ git ls-files .claude/
.claude/settings.json
```

— so a bare `git clean -fd`, a routine worktree-tidying command for an agent,
deletes it. The commit body claims coverage in so many words: "git
checkout/restore/clean on it". That claim is false for every spelling that does not
name the file.

### MAJOR-3 — the `dd` arm is dead code

`tools/orchestrator-guard.sh:730-754`. It reads `of=` and compares the destination,
but the token `of=<path>` never satisfies the `:691` gate, so the arm is
unreachable unless the command *also* carries a separate bare token naming the
file. Measured:

```
dd if=/dev/null of=.claude/ritual-override                          -> ALLOW
dd of=<proj>/.claude/ritual-override if=/dev/null                   -> ALLOW
dd if=/dev/null of=.claude/ritual-override .claude/ritual-override  -> DENY
```

Coverage that reads as present in the source and in the header comment (`:646-654`)
but is not.

### MAJOR-4 — `find … -delete` and python removal spellings allow

Measured ALLOW on the task tree:
`find .claude -name ritual-override -delete`,
`python3 -c "import os;os.remove('.claude/ritual-override')"`,
`python3 -c "import pathlib;pathlib.Path('.claude/ritual-override').unlink()"`.
Note the asymmetry: the *write* spellings
(`open(…,'w')`, `write_text`) do deny — but by the plan rule's `python*` arm
(`:605-627`), incidentally and with the plan's reason, on the base guard too. The
override rule contributes nothing to them, and the removal spellings have no such
incidental cover. `find . -name ritual-override -delete` denies only because `.` is
a plans ancestor; changing `.` to `.claude` opens it.

### MINOR-1 — the "no command position" contract is unpinned for the new rule

Truncating both `override_verdict` token scans to the first token (`:671`, `:704`)
kills **zero** tests. Every command in test 54 has its write verb as token 0, and
the one redirect case is caught by the separate loop at `:781-791`. The guard does
handle `cd .claude && rm ritual-override` (measured DENY), but nothing asserts it.

### MINOR-2 — the `cd`/`pushd` and payload-`cwd` rebase is unpinned

Removing the `cd | pushd)` case from `override_verdict` (`:673`) kills zero tests.
No new test passes a payload `cwd`, and none uses `cd`/`pushd`. Both work
(measured DENY for `cd .claude && rm ritual-override`, for `rm ritual-override`
with `cwd=<proj>/.claude`, and for `pushd .claude && rm ritual-override`) —
untested.

### MINOR-3 — the symlink case is unpinned

`rm link-to-override` and `Write link-to-override` both deny (measured), thanks to
`canon_path`'s `[ -L ]` branch, but no new test covers a symlink to the override.
og5's test 35 pins the symlink branch for plans only.

### MINOR-4 — garbled comment

`tools/orchestrator-guard.sh:651`

```
# write-capable verb — touch/opera/bewriters, the copy/link family whose
```

"touch/opera/bewriters" is not English and names nothing in the code.

### MINOR-5 — unused local

`tools/orchestrator-guard.sh:683`: `local seen=0 b orig` — `orig` is never
assigned or read in `override_verdict`. shellcheck is clean (rc 0), so nothing
catches it.

### MINOR-6 — 8a8705a touches `docs/OPERATIONS.md`, outside `touches`

The plan's `touches` is `tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats`.
Prior *task* commits in this history do not carry a board hunk (`7dd40d6`,
`c4f0bbb`, `50bc237` all `ops=0`); board hunks come from orchestrator docs commits.
I record it as MINOR rather than MAJOR because the hunk is the machine-derived
queue block that `githooks/pre-commit` itself writes and then refuses to commit
without — see "The second commit". Treating it as a MAJOR would make the task
unlandable by construction. It should still be dropped or folded at integration.

### MINOR-7 — the extra commit 91493a5

Second commit where the plan gives one; out of `touches`; its subject says "CR2
landed" of a task that had landed only on `task/CR2`. Drop at integration.

### Note (not a finding) — spellings outside the rule's stated scope

`chmod 000 .claude/ritual-override` and `rsync -a /tmp/empty/ .claude/` allow.
Neither is a content write in the sense the rule defines, but the second is another
directory-level clobber that MAJOR-1's missing ancestor arm would have caught.

## Verdict

**REJECTED** — four MAJORs.

The shape of the work is right and the pin is real: the guard genuinely changed,
red-before-green holds (4/5 new tests fail on the base), all checks are green, six
of eight CR2 mutations die including the reason text, and og5's whole table
reproduces unchanged. What fails is coverage. The rule keys on the exact file path
and nothing else, so the operator-only guarantee the subject asserts — "no agent
may create, overwrite, or delete `.claude/ritual-override`" — is false for
`rm -rf .claude`, for `git clean -fd` (a command an agent runs to tidy a worktree,
against an untracked, un-ignored file), for `mv .claude .claude-old`, for
`find .claude … -delete`, for python `os.remove`/`unlink`, and for `dd of=…` whose
handler cannot be reached at all.

The fix is one arm, modelled on the rule sitting 200 lines above it: an
`is_override_dir_or_ancestor` companion to `is_plans_dir_or_ancestor` (`:389`),
feeding a `dir_ancestor_seen` flag alongside `seen` at `:691`, so the delete family
(`rm`, `mv`, `rmdir`, `rsync`, `shred`), `git clean`/`checkout`/`restore` with no
path or with `.claude`, and `find` with `-delete`/`-exec` deny when they name
`.claude` or an ancestor of it. The `dd` arm needs the `of=` value admitted into
the `seen` scan. A re-plan should also pin the two surviving mutations (a `cd`
case and a payload-`cwd` case in the new tests) and the symlink spelling.

At integration, 91493a5 is dropped; 8a8705a stands alone for `unit` and `lint`.
