---
reviewer: opus
majors: 1
minors: 10
---
# Opus gate — seat run og5, task OG1r2b — APPROVED

## Summary

One commit (`7dd40d6`) on base `f2d30d9`, subject byte-identical to OG1's
(md5 `7b1b679dede0b363baf333bc631f5f35` for both the commit subject and the
plan's), both trailers present (`Generated-By: dsh 0.1.2-rc.1 /
deepseek/deepseek-v4-pro-0813 (seat headless, factory run og5)` and
`Co-Authored-By: Claude Fable 5.1`). Six files touched, all inside the declared
`touches`; `docs/ledger/task-status.toml` correctly left alone (already on base);
`docs/MAP.md` is exactly what `repomap.py write` regenerates (re-ran it: no
diff); `flake.nix` is the one sanctioned `cp` line plus its two comment lines.

**All five og4 MAJORs are fixed and nothing regressed.** Every one of the 25
Step-1 rows behaves; all 31 rows of og4's git-rule table and all 26 rows of its
plan-write table still behave, as do the 25 extras of og4's two "extras that
also behave" lists and its whole Kept-fixes table. The 21 rows og4 listed as
"extras that do not behave" now split cleanly: the 15 rows under MAJOR 14–17 all
DENY, `>|` (MINOR 19) DENIES, `r''m <plan>` (the quote half of MINOR 17) DENIES;
only MINOR 18's four verbs (`patch`, `awk -i inplace`, `ex`, `sponge`) and the
expansion family (`$g push`, `eval`) still allow — both were left out of this
plan's contract on purpose.

MAJOR 18 is dead with room to spare: og4's 907 ms is now **64 ms** on the
plan's acceptance command (`ls <200 × docs/aN/bN.md>`, median of 5), against the
same OG1r2 guard re-measured here at **884 ms**. 54 bats tests green, `unit`
215/215, `lint` green, `shellcheck` clean. Honest red: OG1r2's guard against
OG1r2b's tests fails exactly the six new deny groups, the token test and the
timing test (8 of 54) and correctly passes the three allow-controls. All nine
demanded mutations behave as the plan says except M-I, which the plan itself
allows me to report as unpinned — and og4's M1–M5 all still die.

Nothing rises to a MAJOR. The findings below are ten MINORs; the one worth the
implementer's next hour is MINOR-1: `git checkout -- docs/superpowers/plans`
(and `git restore` on the directory) overwrites every plan from HEAD and is
ALLOWED, because the directory/ancestor rule is scoped — exactly as the plan's
contract writes it — to the delete family, which does not include those two
verbs. The contract is met as written; the hole is real.

Method: fresh clone of `task/OG1r2b`; the guard run only from that clone with
`env CLAUDE_PROJECT_DIR=<fixture> HOME=<fixture parent> bash
tools/orchestrator-guard.sh` and a compact `ensure_ascii=False` payload of the
real Claude Code shape (`{"session_id":…,"cwd":…,"hook_event_name":"PreToolUse",
"tool_name":"Bash","tool_input":{"command":…}}`) on stdin. Fixture: a git repo
at `<scratch>/fix/nixos-agent-env` with `docs/superpowers/plans/x.md` (two typed
headings), a `docs/notes/plans/x.md` decoy, `link-into-plans.md` → the plan,
`plans-link` → the plans dir, `docs/superpowers/plans/out.md` → a file outside,
500 symlinks under `sym/`, and `<scratch>/plans-not-ours/x.md` outside the
project. `HOME` pointed at the fixture's parent so `~` is an ancestor of the
fixture and the real repo was never named with a write verb.

## Git rule cases

og4's 31-row table — **31/31 as demanded**, no regression.

| Command | Expected | Observed |
|---|---|---|
| `cd /x`⏎`git commit --amend -m y` | deny | **DENY** |
| `set -e`⏎`git push origin main` | deny | **DENY** |
| `nix develop -c git commit --amend` | deny | **DENY** |
| `nix develop -c git push` | deny | **DENY** |
| `timeout 5 git push` | deny | **DENY** |
| `nohup git push` | deny | **DENY** |
| `time git push` | deny | **DENY** |
| `! git push` | deny | **DENY** |
| `bash -c "git push"` | deny | **DENY** |
| `` `git push` `` | deny | **DENY** |
| `git status; git push` | deny | **DENY** |
| `x \| git push` | deny | **DENY** |
| `{ git push; }` | deny | **DENY** |
| `git --work-tree=. commit --amend` | deny | **DENY** |
| `git -c a=b -C . reset --hard` | deny | **DENY** |
| `git --git-dir .git commit --amend` | deny | **DENY** |
| `/run/current-system/sw/bin/git commit --amend` | deny | **DENY** |
| `command git commit --amend` | deny | **DENY** |
| `\git commit --amend` | deny | **DENY** |
| `GIT_EDITOR=true git commit --amend` | deny | **DENY** |
| `git   commit   --amend` | deny | **DENY** |
| `git commit \`⏎`--amend` | deny | **DENY** |
| `git checkout -- docs/superpowers/plans/x.md` | deny | **DENY** |
| `git restore docs/superpowers/plans/x.md` | deny | **DENY** |
| `git status; git log` | allow | allow |
| `git --work-tree=. status` | allow | allow |
| `git -c a=b log -1` | allow | allow |
| `git -P diff` | allow | allow |
| `git commit -F msg` | allow | allow |
| `git add docs/superpowers/plans/x.md` | allow | allow |
| `git diff -- docs/superpowers/plans/x.md` | allow | allow |

og4's nine extras also unchanged: `git commit --amend`, `git "push"` deny;
`git status`, `git commit -F /tmp/msg`, `git log --format=%s | grep push`,
`cd ~/src/git && make`, `ls /usr/bin/git`, `grep -rn amend docs/reviews`,
`nix develop -c githooks/pre-commit` allow.

Of og4's five MINOR-17 evasions, the quote half is now fixed and the expansion
half is not (MINOR-6 below):

| Command | og4 | og5 |
|---|---|---|
| `git p''ush` / `git pu"sh"` / `r''m <plan>` | ALLOWED | **DENY** (quotes strip to nothing) |
| `g=git; $g push` / `git $(echo push)` / `eval git\ push` | ALLOWED | ALLOWED (unchanged, out of contract) |

## Plan-write cases

### Step 1's 18 deny rows and 7 allow rows — 25/25

| Command | Expected | Observed | Reason |
|---|---|---|---|
| `mv <plan> /tmp/x` | deny | **DENY** | `mv` is an operand writer (`:484`) |
| `mv <plan> ./y` | deny | **DENY** | same |
| `mv -f <plan> ../x.md` | deny | **DENY** | same |
| `mv <plan> <plan>.bak` | deny | **DENY** | same |
| `rm -r docs/superpowers/plans` | deny | **DENY** | token = plans dir (`:374`) |
| `rm -rf docs/superpowers` | deny | **DENY** | ancestor inside project |
| `rm -rf docs` | deny | **DENY** | ancestor inside project |
| `mv docs/superpowers/plans /tmp/` | deny | **DENY** | dir + delete family |
| `find docs/superpowers/plans -name "*.md" -delete` | deny | **DENY** | `-delete` + dir (`:580`) |
| `git clean -fdx docs/superpowers/plans` | deny | **DENY** | `clean` + dir (`:571`) |
| `cd docs/superpowers/plans && rm x.md` | deny | **DENY** | `cd` base + `rm` |
| `cd docs/superpowers/plans; rm x.md` | deny | **DENY** | same |
| `cd docs/superpowers && rm plans/x.md` | deny | **DENY** | same |
| payload `cwd` = plans dir, `rm x.md` | deny | **DENY** | cwd is the initial base (`:437`) |
| `sed -e s/a/b/ -i <plan>` | deny | **DENY** | `-i*` scanned anywhere (`:470-476`) |
| `sed s/a/b/ -i <plan>` | deny | **DENY** | same |
| `perl -pe s/a/b/ -i <plan>` | deny | **DENY** | same |
| `cat k >\| <plan>` | deny | **DENY** | `>\|` is a redirect token (`:128`) |
| `ls docs/superpowers/plans` | allow | allow | no write verb |
| `find docs/superpowers/plans -name '*.md'` | allow | allow | no `-delete`/`-exec` |
| `cd /tmp && rm x.md` | allow | allow | `/tmp` is not "ours" (`:381-384`) |
| `cd docs/superpowers/plans && cat x.md` | allow | allow | `cat` is not a write verb |
| `git diff -- <plan>` | allow | allow | subcommand `diff` |
| `rm <scratch>/plans-not-ours/x.md` | allow | allow | outside the project |
| `echo "a'b"` | allow, ONE token | allow; tokeniser gives 2 lines for 2 tokens (`echo`, `a'b`) | quotes → nothing (`:111-113`) |

### og4's plan-write table — 26/26 unchanged

All 17 deny rows still DENY (`sed -i`, `rm`, `mv a <plan>`, `cp k <plan> &&`,
`cat > …/plans/../plans/x.md`, `install`, `dd of=`, `ln -sf`, `tee`, `truncate`,
`perl -i -pe`, the python heredoc, `python3 -c … write_text`,
`nix develop -c rm`, `xargs rm`, `echo a`⏎`rm`, `echo a`⏎`sed -i`); all 7 allow
rows still allow (`cat`, `grep -n '^### '`, `sed -n 1,5p`, `cat | wc -l`,
`pytest`, `tasks.py check`, `tasks.py write-board`); both accepted over-denials
(`echo "git commit --amend"`, `rm /tmp/x && cat <plan>`) still DENY.

og4's 16 "extras that also behave" — 16/16 unchanged (deny: `../`-spelled,
`//`-spelled, absolute, symlink-into-plans, `> / >> / 2>`, `tee -a`,
`rm -r …/plans/`, `sed -i -e`, `sed --in-place`, `sed -n -i`, `git mv`; allow:
`docs/notes/plans/x.md`, `cp <plan> /tmp/y`, `diff <plan> other.md`).

### Kept fixes (heading rule, host rules) — 26/26

Edit removing `### A1`, key rename `A1`→`A9`, size `S`→`M`, `Write` dropping a
heading, `MultiEdit` removing `### B2` → **DENY ×5**; Edit of body text, Edit
appending `### C3`, `Write` appending a section → allow ×3; Edit via
`…/plans/../plans/x.md`, via `…/superpowers/./plans/x.md`, via the symlink into
the plans dir → **DENY ×3**; the `docs/notes/plans` decoy and the symlink out of
the plans dir → allow ×2 (the header's stated MINOR-8 choice); unknown tool →
allow. `grep -rn sudo docs/brief.md`, `echo 'never sudo here'`,
`cp /var/lib/secrets/x /tmp/y` → allow ×3; `x; sudo y`, `sudo nixos-rebuild
switch`, `x`⏎`sudo y`, `systemctl start foo`, `cp k /var/lib/secrets/x`,
`tee -a /var/lib/secrets/x`, `echo x > /var/lib/helm/x`, `mv k /var/lib/lanes/x`
→ **DENY ×8**.

### 3. Ancestors and edges

| Command | Expected | Observed | Reason |
|---|---|---|---|
| `rm -rf /` | (unstated) | **DENY** | `/` is special-cased (`:376`) |
| `rm -rf ~` (~ IS an ancestor of the fixture) | (unstated) | **ALLOWED** | ancestors above the project dir are "not ours" (`:381-384`) — MINOR-2 |
| `rm -rf ./result` | allow | allow | not an ancestor |
| `rm -rf /tmp/x` | allow | allow | not an ancestor |
| `rm -r docs/superpowers/plans/` | deny | **DENY** | trailing slash collapses in `lex_norm` |
| `rmdir docs/superpowers/plans` | deny | **DENY** | delete family |
| `rsync --delete src/ docs/superpowers/plans/` | deny | **DENY** | delete family |
| `git mv <plan> y.md` | deny | **DENY** | bare `mv` token |
| `git rm <plan>` | deny | **DENY** | bare `rm` token |
| `shred <plan>` | deny | **DENY** | delete family |

Extra: `rm -rf <parent of the project>` ALLOWED (same cause as `rm -rf ~`);
`rm -rf docs/reviews` allowed (correct — not an ancestor of the plans dir).

### 4. Rebase

| Command | Expected | Observed | Reason |
|---|---|---|---|
| `cd docs && cd superpowers && rm plans/x.md` | deny | **DENY** | each `cd` joins onto the previous base (`:442`) |
| `pushd docs/superpowers/plans && rm x.md` | deny | **DENY** | `pushd` is a rebase verb |
| `cd ~ && rm nixos-agent-env/docs/…/x.md` | deny | **DENY** | `~` → `$HOME` in `lex_norm` (`:322`) |
| `cd /tmp; cd - && rm docs/…/x.md` | (unstated) | **DENY** | `cd -` adds the junk base `/tmp/-`, but the *initial* base (the payload cwd) is never dropped, so the relative plan path still resolves — deny for the right reason by accident of never popping a base |
| payload `cwd` outside the project + `rm x.md` | allow | allow | resolves under `plans-not-ours` |

Extra probes that isolate the `cd` half (not in any test): `cd
docs/superpowers/plans && sed -i s/a/b/ x.md`, `… && tee x.md`, `… && cat k >
x.md`, `pushd … && sed -i s/a/b/ x.md` all **DENY** — and all four flip to
ALLOW when the `cd`/`pushd` loop is disabled. See MINOR-3.

### 5. sed / perl

| Command | Expected | Observed |
|---|---|---|
| `sed --in-place=.bak s/a/b/ <plan>` | deny | **DENY** |
| `sed -i.bak s/a/b/ <plan>` | deny | **DENY** |
| `perl -i -pe s/a/b/ <plan>` | deny | **DENY** |
| `sed -n p <plan>` | allow | allow |
| `sed -i s/a/b/ /tmp/other.md` | allow | allow |

### 6. Quotes and redirects

| Command | Expected | Observed |
|---|---|---|
| `echo "a'b"` | allow | allow (one token, pinned by test 52) |
| `echo "rm <plan>"` | over-denial, either way | **DENY** — the accepted over-denial |
| `cat k >\| <plan>` | deny | **DENY** |
| `cat <plan> > /tmp/out` | allow | allow |
| `cat <plan> \| wc -l` | allow | allow |

### 7. Symlinks

| Command | Expected | Observed |
|---|---|---|
| `rm link-into-plans.md` (symlink INTO the plans dir) | deny | **DENY** — rule 5's `[ -L ]` exception (`:354`) |
| `rm <abs>/link-into-plans.md` | deny | **DENY** |
| `rm plans-link` (symlink AT the plans dir) | — | **DENY** — resolves to the dir, delete family |
| `rm docs/superpowers/plans/out.md` (symlink OUT) | judged by its target | **DENY** — but by the raw `*superpowers/plans/*` fallback (`:462`), not by the target; MINOR-9 |
| `Edit docs/superpowers/plans/out.md` | judged by its target | allow — the header's stated choice, correct |

### Extra adversarial probes (all correct)

`cd docs && rm -rf superpowers`, `find . -delete`, `cd docs/superpowers/plans &&
cat k >x.md`, `git -C docs/superpowers/plans rm x.md`, `mv ./docs/./superpowers/
plans /tmp`, `rm ~/nixos-agent-env/<plan>`, `rm -rf plans-link`, `cd plans-link
&& rm x.md`, `nix develop -c mv <plan> /tmp/z`, `timeout 5 rm <plan>`,
`bash -c "rm <plan>"`, `rm <plan>; echo done`, `rsync -a --delete /tmp/empty/
docs/superpowers/plans/`, `cd docs; cd superpowers; rm -r plans`,
`env -C docs/superpowers/plans rm x.md`, `> <plan>`, `cp /dev/null <plan>`,
`git clean -fdx docs`, `git rm -r docs/superpowers/plans` — **DENY ×19**.

No false denial on ordinary repo work: `nix develop -c githooks/pre-commit`,
`repomap.py --root . write`, `tasks.py --root . brief`, `tasks.py … write-board`,
`nix build .#checks…`, `git add -A && git commit -F /tmp/msg`,
`nix develop -c bats tests/unit`, `nix develop -c treefmt`, `rm -f result`,
`mv result result.old`, `cd .. && ls`, `git log --oneline -5` — allow ×12.
(`rm -rf .` and `git clean -fdx .` DENY — the correct over-denial: `.` is the
project dir.)

## Timing

Measured from the clone against the fixture, wall time of the whole hook process
including the harness's ~19 ms `git status` baseline; five calls each, median
reported.

| Command | Median | Min–max | Budget |
|---|---|---|---|
| `git status` (baseline, incl. harness overhead) | **19 ms** | 18–20 | — |
| **`ls <200 × docs/aN/bN.md>` (the plan's acceptance)** | **64 ms** | 62–64 | **< 300 ms — met, 4.7× headroom** |
| `ls <500 × docs/aN/bN.md>` | 129 ms | 128–130 | — |
| `rm <200 × docs/aN/bN.md>` | 72 ms | 66–78 | — |
| `cd docs && cd superpowers && cd plans && ls <200 rel tokens>` (4 bases) | 37 ms | 32–38 | faster — the scan breaks once both flags are set |
| **`ls <200 symlink tokens>` (worst case of rule 5)** | **296 ms** | 289–304 | at the line — MINOR-8 |
| `ls <500 symlink tokens>` | 725 ms | 707–835 | — |
| OG1r2's guard, same 200-path-token command | **884 ms** | 854–887 | og4's MAJOR 18, reproduced |

The suite's own timing test (53) measures the same command with
`$EPOCHREALTIME`, median of three, and passed on three isolated re-runs.
Seat runs are live; the numbers above were taken with the machine otherwise
idle and are stable to ±3 ms on the path-token cases.

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| Check | Command | Exit | Time | Result |
|---|---|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **0** | 35 s | 215/215 `ok`, 0 `not ok`; guard tests are 162–215 (54 of them) |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **0** | 1 s | pass |
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **0** | 2 s | clean |
| bats (devShell) | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | **0** | 9 s | 54/54 |
| pre-commit | `nix develop -c githooks/pre-commit` | **1** | 3 s | `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`; **exit 0** once the regenerated board (a one-line diff) is staged |

The `pre-commit` red is the same structural condition og4, og3 and OG1b all
recorded and is not the implementer's: `landed_subjects()` reads git log, so the
task's key drops out of the generated queue block the moment its commit exists.
The result line's `pre-commit=pass` is true only with the board staged and, as
in og4, does not say so. The merge step must include the board regeneration.

Repository hygiene: `git rev-list --count base..HEAD` = **1**; the six changed
files are all inside `touches`; `docs/ledger/task-status.toml` unchanged and
already on base; `docs/MAP.md` byte-identical to a fresh `repomap.py write`;
`flake.nix` adds only the sanctioned `cp` line and its two comments;
`.claude/settings.json` keeps G6's SessionStart entry byte-for-byte.

## Red before green

OG1r2's guard (`git -C /home/dalhaka/factory/ws/og4/OG1r2 show
task/OG1r2:tools/orchestrator-guard.sh`, 576 lines) dropped into the clone in
place of OG1r2b's, OG1r2b's tests kept: `nix develop -c bats
tests/unit/91-orchestrator-guard.bats` → **exit 1, 8 of 54 red**:

```
not ok 43 bash: mv taking a plan in ANY operand position is denied
not ok 44 bash: the plans directory or an ancestor names every plan for the delete family
not ok 45 bash: a cd rebases relative plan-write paths
not ok 46 bash: the payload cwd rebases relative plan-write paths
not ok 47 bash: sed/perl -i anywhere in the invocation refuses a plan
not ok 48 bash: a clobber redirect to a plan is denied
not ok 52 bash: quotes strip to nothing so echo "a'b" stays one word
not ok 53 a 200-path-token command stays under 300 ms (median of three calls)
```

Exactly the six new deny groups, the token test and the timing test. The three
allow-controls (49 `read verbs on the plans directory`, 50 `a cd elsewhere does
not rebase`, 51 `a directory merely named plans outside the project`) pass on
the old guard — correct: they are controls, not behaviour changes. Honest red,
no inflation. Restored (`git checkout --`), tree clean, 54/54 green.

## Mutation table

Each applied to `tools/orchestrator-guard.sh` in the clone, the tree asserted
changed (`git diff --numstat` printed for every row), the full bats file run,
then reverted; `git status --porcelain` empty after each.

| # | Mutation | Diff | Failures | Killed by |
|---|---|---|---|---|
| **M-A** | `mv` removed from the operand writers (`:484`) | 1+/1− | **3** | 16, 43, 44 |
| **M-B** | `is_plans_dir_or_ancestor` short-circuited to false (`:374`) | 1+/0− | **1** | 44 |
| **M-C** | `cd`/`cwd` rebase off (bases fixed to the project dir *and* the `cd\|pushd` case renamed) | 2+/2− | **1** | 46 |
| **M-D** | `-i` search limited to the token right after `sed`/`perl` (`:499`) | 1+/1− | **1** | 47 |
| **M-E** | lexical normaliser replaced by `realpath -m` per token (`:350-359`) | 1+/5− | **1** | 53 — **measured 279 ms** median on the 200-path-token command (see MINOR-5: not a robust kill) |
| **M-F** | quote stripping back to a space (`:111-113`) | 3+/3− | **1** | 52 |
| **M-G** | symlink exception removed (`[ -L ]` branch → `_canon=$p`) | 1+/5− | **1** | 35 (`edit: a symlink into the plans dir is still denied`) |
| **M-H** | `>\|` removed from the redirect tokens (`:128`) | 0+/1− | **1** | 48 |
| **M-I** | `pushd` dropped from the rebase verbs (`:440`) | 1+/1− | **0** | **SURVIVES — unpinned** (MINOR-3) |
| — | *sub-mutation:* only the `cd`/`pushd` loop disabled, payload `cwd` kept | 1+/1− | **0** | **SURVIVES — unpinned** (MINOR-3) |
| **M1** (og4) | `\n` dropped from `normalise_command` | 0+/1− | **2** | 20, 22 |
| **M2** (og4) | both token scans stop after the first token (`i < n` → `i < 1`) | 3+/3− | **8** | 9, 16, 17, 20, 21, 22, 44, 45 |
| **M3** (og4) | basename rule off (`base=${t##*/}` → `base=$t`) | 1+/1− | **1** | 9 |
| **M4** (og4) | `plan_write_verdict` returns immediately | 1+/0− | **10** | 16, 17, 18, 22, 43, 44, 45, 46, 47, 48 |
| **M5** (og4) | value-skip list neutered in `git_verdict` | 0+/3− | **2** | 7, 9 |

M1–M4 (og4's four demanded) all still die, and so does M5. Note that M-A also
kills test 16 and M2/M4 now kill more tests than in og4 — the new rows widen the
net. M-C dies on 46 only: test 45 survives it because all three of its commands
*also* name the plans directory as a literal token, so the delete-family
ancestor rule denies them with the rebase off. That is why M-I and the cd-only
sub-mutation survive; see MINOR-3.

## Findings

**MINOR-1 — `git checkout -- docs/superpowers/plans` (and `git restore` on the
directory) overwrites every plan from HEAD, and it is ALLOWED.**
`tools/orchestrator-guard.sh:564-577`. The `checkout|restore` arm tests only
`plan_file_seen`; the `clean` arm tests `plan_file_seen || dir_ancestor_seen`.
Measured:

```
allow   git checkout -- docs/superpowers/plans
allow   git checkout HEAD -- docs/superpowers
allow   git restore docs/superpowers/plans
allow   git restore --source=HEAD~1 docs
allow   git stash -- docs/superpowers/plans
DENY    git checkout -- docs/superpowers/plans/     (trailing slash: raw fallback)
DENY    git checkout -- docs/superpowers/plans/x.md
```

This is og4's MAJOR 15 shape — the trailing slash deciding the verdict —
surviving for these two verbs. It is **not** a MAJOR here: the plan's contract
item 2 scopes the directory/ancestor rule to "the delete family (`rm`, `mv`,
`rsync`, `shred`, `rmdir`, `find`, `git clean`)", and `git checkout`/`git
restore` are not in that list, so the contract is met as written. Fix: add
`checkout|restore` (and `stash`) to the arm that already accepts
`dir_ancestor_seen` — one `case` label.

**MINOR-2 — every ancestor strictly between `/` and the project dir is exempt,
so `rm -rf ~` is ALLOWED while `rm -rf /` DENIES.**
`tools/orchestrator-guard.sh:374-385`:

```bash
  [ "$p" = "/" ] && return 0
  case "$plans" in "$p" | "$p"/*) : ;; *) return 1 ;; esac
  case "$p" in "$project" | "$project"/*) return 0 ;; *) return 1 ;; esac
```

Measured with `HOME` = the fixture's parent: `rm -rf ~` → **ALLOWED**;
`rm -rf <parent of the project>` → **ALLOWED**; `rm -rf /` → DENY. On the real
host that means `rm -rf /home/dalhaka` allows while `rm -rf /` denies. The cutoff
is deliberate, documented at `:367-373`, and forced by the plan's own allow rows
(`cd /tmp && rm x.md`, `rm /tmp/plans-not-ours/x.md`) whenever the project lives
under `/tmp` — but the plan's rule 2 says "ANY ancestor of it", and the special
case for `/` makes the omission of the ones in between look accidental rather
than chosen. Fix: either drop the `/` special case (consistent) or say in the
header why `/` is in and `~` is out.

**MINOR-3 — the `cd`/`pushd` half of rule 3 is load-bearing but unpinned by the
suite.** `tests/unit/91-orchestrator-guard.bats`, test 45 (`bash: a cd rebases
relative plan-write paths`). All three of its commands (`cd
docs/superpowers/plans && rm x.md`, `…; rm x.md`, `cd docs/superpowers && rm
plans/x.md`) also name the plans directory or an ancestor as a literal token, so
the delete-family ancestor rule denies them even with the rebase gone. Proof:
disabling only the `cd | pushd)` case at `:440` leaves the whole 54-test file
green, and so does M-I. Yet the rebase is real: with it off,

```
cd docs/superpowers/plans && sed -i s/a/b/ x.md     DENY -> allow
cd docs/superpowers/plans && tee x.md               DENY -> allow
cd docs/superpowers/plans && cat k > x.md           DENY -> allow
pushd docs/superpowers/plans && sed -i s/a/b/ x.md  DENY -> allow   (M-I alone)
```

Fix: add one of those four commands (a non-delete-family verb after the `cd`) to
test 45, and one `pushd` row.

**MINOR-4 — the `cwd` test uses a payload shape Claude Code does not send.**
`tests/unit/91-orchestrator-guard.bats`, test 46 builds
`{"tool_name":"Bash","tool_input":{"command":"rm x.md","cwd":…}}` — `cwd` inside
`tool_input`. The real PreToolUse payload carries `cwd` at the top level, a
sibling of `tool_name`. `json_string` (`:223-227`) scans the whole JSON for the
key, so both work, and I verified the **real** shape myself (top-level `cwd` =
the plans dir with `rm x.md` → DENY; top-level `cwd` outside the project with
`rm x.md` → allow). But nothing in the suite would catch a future narrowing to
`tool_input.cwd`, and `bpayload` never emits a `cwd` at all.

**MINOR-5 — M-E's kill is not robust: 279 ms against a 300 ms threshold.**
Applied on its own and run three times in isolation
(`bats -f '200-path-token'`), the `realpath -m`-per-token mutant fails twice and
**passes once**; measured cost is 279 ms median (277/279/293), only 7% over the
threshold. The mutation does die under the prescribed protocol (full file, one
run) and the real implementation has 4.7× headroom, so the acceptance itself is
safe — but the implementer's note claims "~670 ms" for this mutation, which I
could not reproduce on this host (my figure is 279 ms). Report the number, not
the margin.

**MINOR-6 — the write-verb list is still an enumeration (og4's MINOR 18,
recurring).** `patch <plan> < d`, `awk -i inplace 1 <plan>`, `ex -sc wq <plan>`,
`sponge <plan> < k` are all still ALLOWED. Not a deviation — the plan's contract
did not add them — but this is the fourth gate at which the enumeration reflex is
the finding, and `patch` remains an ordinary way to apply a diff.

**MINOR-7 — the expansion half of og4's MINOR 17 is untouched.**
`g=git; $g push`, `git $(echo push)`, `eval git\ push` still ALLOW. Adversarial
only, shared with `hook-guard.py`, and out of this plan's contract; recorded so
it is not lost. The quote half is genuinely fixed (`r''m <plan>` now DENIES).

**MINOR-8 — the worst case of rule 5 sits on the budget line.** A 200-token
command whose every token is a symlink costs **296 ms** median (289–304), i.e.
the `[ -L ]` exception can still put a real command at the 300 ms mark, and 500
such tokens cost 725 ms. The plan's acceptance is the path-token case (64 ms) so
this is not a miss, and the `.claude/settings.json` timeout is 10 s, but the
header's "realpath … once more only for a token whose lexical form is a symlink"
understates it: the token loop (`:451-459`) calls `canon_path` once per (token,
base) pair, so a symlink token with three `cd` bases forks three times.

**MINOR-9 — the header's symlink-out sentence is true only for Edit/Write.**
`tools/orchestrator-guard.sh:44-47` says a symlink FROM the plans dir outward "is
judged by its target". For the Edit path that is exactly what happens (verified:
`Edit docs/superpowers/plans/out.md` → allow). For Bash it does not: `rm
docs/superpowers/plans/out.md` DENIES, via the raw-text fallback at `:462-464`
(`*superpowers/plans/*`), not via the target. The denial is the safe direction
and is an accepted over-denial, but the sentence should say "for the Edit and
Write tools".

**MINOR-10 — the runbook asserts the budget rather than reporting it.**
`docs/runbooks/session.md:124-127`: "the guard's own token scan is lexical bash —
a 200-token command stays under the <300 ms per-call budget." The gate brief
asked for the claim "stated as measured"; it is stated as a property. "far over"
is gone from the runbook (it survives only at
`tools/orchestrator-guard.sh:54`, where it correctly describes `nix develop -c
python3`'s ~5 s against the same budget — accurate, keep it). Everything else in
the two rules checks out against the implementation: rule 2's verb list matches
`:484-585` item for item, it names the plans directory and its in-project
ancestors (and does not over-claim ancestors above the project), it names the
`cwd`/`cd`/`pushd` rebase, and the over-denial paragraph names both accepted
cases exactly. Suggested edit: "a 200-token command measures 64 ms on `core`
(budget: 300 ms)".

**NOTE — `.claude/settings.json` is a pure addition, but the merge is not
mechanical.** OG1r2b adds only the `"PreToolUse"` key (two matchers,
`Edit|Write|MultiEdit` and `Bash`) after G6's `SessionStart` array, which it
keeps byte-for-byte; no other line changes. Main has since gained CR1b's
`PreCompact` and `Stop` keys at the same insertion point, so a real merge does
**conflict** — I ran it (`git merge --no-commit --no-ff task/OG1r2b` onto
`main`, base confirmed an ancestor):

```
Auto-merging .claude/settings.json
CONFLICT (content): Merge conflict in .claude/settings.json
Auto-merging docs/MAP.md            (clean)
Auto-merging flake.nix
CONFLICT (content): Merge conflict in flake.nix
```

- `.claude/settings.json`: conflict markers at lines 11 / 24 / 36 — both sides
  append a key after `SessionStart`'s closing `],`. Resolution: keep
  `PreCompact` and `Stop`, then append the `PreToolUse` block; one comma to
  place. No semantic overlap.
- `flake.nix` lines 1780–1789: both sides add a `cp ${self}/tools/<x>.sh` line
  after the `session-start.sh` copy. Resolution: keep both `cp` lines (ritual.sh
  and orchestrator-guard.sh). No semantic overlap.
- `docs/MAP.md` merges cleanly, but the merged tree's MAP must be regenerated
  once (both sides bumped the `tests/unit` file count).

Two textual conflicts, both pure additions, both a one-minute resolution — but
the integrator should be told rather than surprised.

**NOTE — the accepted over-denials are confirmed.** `echo "git commit --amend"`,
`echo "rm <plan>"`, `rm /tmp/x && cat <plan>`, `rm -rf .` and `git clean -fdx .`
all DENY. Correct for a deny-only guard, and the runbook states it plainly.

**NOTE — no false denial on ordinary work.** Twelve everyday repo commands
(pre-commit, repomap, tasks brief and write-board, `nix build`, `git add -A &&
git commit -F`, bats, treefmt, `rm -f result`, `mv result result.old`, `cd ..`,
`git log`) all allow.

## Verdict

**APPROVED.** All five og4 MAJORs are fixed and verified against the fixture, not
just against the suite: `mv` denies from any operand position; the plans
directory and its in-project ancestors name every plan for the delete family with
or without a trailing slash; the payload `cwd` and every `cd`/`pushd` rebase
relative paths; `-i`/`--in-place` is found anywhere in a `sed`/`perl` invocation;
and the 200-path-token command costs 64 ms against a 300 ms budget (884 ms on the
guard this round replaces). All 25 Step-1 rows, all 31 git rows, all 26 og4
plan-write rows, both extras lists, the whole Kept-fixes table and 19 further
adversarial probes behave; nothing regressed. The red proof is honest (8 of 54,
exactly the new behaviour plus the timing test), eight of the nine demanded
mutations die, og4's M1–M5 all still die, and the commit conventions are clean:
one commit, byte-identical subject, both trailers, six files inside `touches`,
MAP identical to a fresh regeneration, one sanctioned `cp` line.

The ten MINORs are all inside the contract as written or outside it entirely; the
one to fix next is MINOR-1 (`git checkout`/`git restore` on the plans
*directory*), which the next task should fold in together with MINOR-3's two
missing test rows. The `pre-commit` red is the same blameless board-staleness
every gate on this line has recorded; the integrator must stage the regenerated
board and resolve two one-minute textual conflicts against CR1b.
