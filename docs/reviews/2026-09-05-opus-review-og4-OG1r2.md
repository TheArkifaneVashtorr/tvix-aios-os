---
reviewer: opus
majors: 5
minors: 4
---
# Opus gate — seat run og4, task OG1r2 — REJECTED

## Summary

One commit (`d808c99`) on base `6b58752`, subject byte-identical to OG1's
(md5 `1d37b988…`, the same value OG1b's and OG1r's heads produce), both
trailers present, touches six of OG1r2's declared seven files
(`docs/ledger/task-status.toml` correctly left alone, as the brief says),
`.claude/settings.json` keeps G6's SessionStart entry byte-for-byte (no CR1
Stop/PreCompact entries exist on base), `flake.nix` is the one sanctioned `cp`
line. 43 bats tests green (`unit` 162–204 of 204), `lint` green, shellcheck
clean. Honest red: OG1r's guard against OG1r2's tests fails exactly the three
new tests (20, 21, 22) and correctly passes the allow-control (23). All four
demanded mutations die. **Every one of the 62 cases in the gate brief's four
lists behaves as specified** — the two MAJORs of og3 are genuinely fixed:
`nix develop -c git commit --amend`, `cd /x`⏎`git push`, `timeout 5 git push`,
`` `git push` ``, `bash -c "git push"`, `nix develop -c rm <plan>` and
`echo a`⏎`rm <plan>` all DENY now.

It is rejected because **the token scan is complete but the rules it feeds are
not, and four holes let a plan file be destroyed or a plan write land**:
`mv <plan> /tmp/x` (and `mv <plan> ./y`) moves a plan away — ALLOWED, and the
plan's own contract lists `mv` as an unconditional write verb; `rm -r
docs/superpowers/plans` without the trailing slash deletes every plan —
ALLOWED (with the slash it denies); `cd docs/superpowers/plans && rm x.md` —
ALLOWED, because relative paths are resolved against `CLAUDE_PROJECT_DIR` and
the payload's `cwd` is ignored; `sed -e s/a/b/ -i <plan>` — ALLOWED, because
the `-i` search stops at the first operand while GNU sed accepts options after
operands. A fifth: the stated `< 300 ms/call on a 200-token command` acceptance
is missed — a 200-path-token command costs **907 ms/call**.

## Git rule cases

Guard run as `env CLAUDE_PROJECT_DIR=<fixture> bash tools/orchestrator-guard.sh`
with compact `ensure_ascii=False` payloads on stdin, exactly as Claude Code
sends them. All 31 brief cases behave as demanded.

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

Extras of mine that also behave: `git commit --amend`, `git status`,
`git commit -F /tmp/msg`, `git log --format=%s \| grep push` (allow),
`cd ~/src/git && make`, `ls /usr/bin/git`, `grep -rn amend docs/reviews`,
`nix develop -c githooks/pre-commit` (allow — no false positive from a `git`
directory component), `git "push"` (deny).

Extras that do **not** behave (all require deliberate evasion — MINOR 17):

| Command | Expected | Observed |
|---|---|---|
| `git p''ush` | deny | **ALLOWED** (quote → space splits the word) |
| `git pu"sh"` | deny | **ALLOWED** (same) |
| `g=git; $g push` | deny | **ALLOWED** |
| `git $(echo push)` | deny | **ALLOWED** |
| `eval git\ push` | deny | **ALLOWED** |

## Plan-write cases

Fixture: `<proj>/docs/superpowers/plans/x.md` with two typed headings, a
`docs/notes/plans/x.md` decoy, a symlink into the plans dir and one out of it.
All 26 brief cases behave as demanded, including both accepted over-denials.

| Command | Expected | Observed |
|---|---|---|
| `sed -i 's/x/y/' <plan>` | deny | **DENY** |
| `rm <plan>` | deny | **DENY** |
| `mv a <plan>` | deny | **DENY** |
| `cp k <plan> && echo done` | deny | **DENY** |
| `cat > docs/superpowers/plans/../plans/x.md` | deny | **DENY** |
| `install -m644 k <plan>` | deny | **DENY** |
| `dd of=<plan>` | deny | **DENY** |
| `ln -sf k <plan>` | deny | **DENY** |
| `tee <plan>` | deny | **DENY** |
| `truncate -s0 <plan>` | deny | **DENY** |
| `perl -i -pe s/a/b/ <plan>` | deny | **DENY** |
| `nix develop -c python3 - <<'PY'` … `open("<plan>","w")` | deny | **DENY** |
| `python3 -c "pathlib.Path('<plan>').write_text('')"` | deny | **DENY** |
| `nix develop -c rm <plan>` | deny | **DENY** |
| `xargs rm <plan>` | deny | **DENY** |
| `echo a`⏎`rm <plan>` | deny | **DENY** |
| `echo a`⏎`sed -i /d/ <plan>` | deny | **DENY** |
| `cat <plan>` | allow | allow |
| `grep -n '^### ' <plan>` | allow | allow |
| `sed -n 1,5p <plan>` | allow | allow |
| `cat <plan> \| wc -l` | allow | allow |
| `nix develop -c pytest tests/evidence -q` | allow | allow |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | allow | allow |
| `nix develop -c python3 … --root . write-board --board docs/OPERATIONS.md` | allow | **allow** — the board write is not refused |
| `echo "git commit --amend"` | deny (accepted over-denial) | **DENY** — confirmed |
| `rm /tmp/x && cat <plan>` | deny (accepted over-denial) | **DENY** — confirmed |

Extras of mine that also behave: `rm docs/superpowers/../superpowers/plans/x.md`,
`rm docs/superpowers/plans//x.md`, `rm <abs plan path>`, `rm <symlink into the
plans dir>` (deny ×4); `rm docs/notes/plans/x.md`, `cp <plan> /tmp/y`,
`diff <plan> other.md` (allow ×3); `echo x>` / `>>` / `2>` a plan, `cat k | tee
-a <plan>`, `rm -r docs/superpowers/plans/`, `sed -i -e`, `sed --in-place`,
`sed -n -i`, `git mv <plan> y` (deny ×9).

Extras that do **not** behave — the rejection:

| Command | Expected | Observed | Finding |
|---|---|---|---|
| `mv <plan> /tmp/x` | deny | **ALLOWED** | MAJOR 14 |
| `mv <plan> ./y` | deny | **ALLOWED** | MAJOR 14 |
| `mv -f <plan> ../x.md` | deny | **ALLOWED** | MAJOR 14 |
| `mv <plan> <plan>.bak` | deny | **ALLOWED** | MAJOR 14 |
| `rm -r docs/superpowers/plans` (no trailing `/`) | deny | **ALLOWED** | MAJOR 15 |
| `rm -rf docs/superpowers` | deny | **ALLOWED** | MAJOR 15 |
| `mv docs/superpowers/plans /tmp/` | deny | **ALLOWED** | MAJOR 15 |
| `find docs/superpowers/plans -name "*.md" -delete` | deny | **ALLOWED** | MAJOR 15 |
| `git clean -fdx docs/superpowers/plans` | deny | **ALLOWED** | MAJOR 15 |
| `cd docs/superpowers/plans && rm x.md` | deny | **ALLOWED** | MAJOR 16 |
| `cd docs/superpowers/plans; rm x.md` | deny | **ALLOWED** | MAJOR 16 |
| `cd docs/superpowers && rm plans/x.md` | deny | **ALLOWED** | MAJOR 16 |
| `sed -e s/a/b/ -i <plan>` | deny | **ALLOWED** | MAJOR 17 |
| `sed s/a/b/ -i <plan>` | deny | **ALLOWED** | MAJOR 17 |
| `perl -pe s/a/b/ -i <plan>` | deny | **ALLOWED** | MAJOR 17 |
| `printf x >\| <plan>` | deny | **ALLOWED** | MINOR 19 |
| `patch <plan> < d` | deny | **ALLOWED** | MINOR 18 |
| `awk -i inplace 1 <plan>` | deny | **ALLOWED** | MINOR 18 |
| `ex -sc wq <plan>` | deny | **ALLOWED** | MINOR 18 |
| `sponge <plan> < k` | deny | **ALLOWED** | MINOR 18 |
| `r''m <plan>` | deny | **ALLOWED** | MINOR 17 |

## Kept fixes

Every OG1b/OG1r fix still holds; nothing regressed.

| Finding | Probe | Expected | Observed |
|---|---|---|---|
| realpath normalisation | `rm` via `../`, `//`, absolute, and a symlink **into** the plans dir | deny | **DENY** ×4 |
| realpath normalisation | `Edit` via `…/plans/../plans/x.md`, `…/superpowers/./plans/x.md`, a symlink into the plans dir | deny | **DENY** ×3 |
| decoy | `rm docs/notes/plans/x.md`, `Edit docs/notes/plans/x.md` | allow | allow ×2 |
| sudo anchors | `grep -rn sudo docs/brief.md`, `echo 'never sudo here'` | allow | allow ×2 |
| sudo anchors | `x; sudo y`, `sudo nixos-rebuild switch`, `x`⏎`sudo y`, `systemctl start foo` | deny | **DENY** ×4 |
| protected prefixes on destinations (MINOR 9) | `cp /var/lib/secrets/x /tmp/y` | allow | allow |
| protected prefixes on destinations | `cp k /var/lib/secrets/x`, `tee -a /var/lib/secrets/x`, `echo x > /var/lib/helm/x`, `mv k /var/lib/lanes/x` | deny | **DENY** ×4 |
| malformed-JSON warning | garbage, `{`-prefixed truncated object, empty input | allow + warn | allow + warn ×3 |
| escape-aware MultiEdit (MINOR 6) | `MultiEdit` whose first edit carries an escaped quote, heading removal second | deny | **DENY** |
| heading rule | `Edit` removing `### A1`; key rename `A1`→`A9`; size `S`→`M`; `Write` dropping a heading; `MultiEdit` removing `### B2` | deny | **DENY** ×5 |
| heading rule | `Edit` body text; `Edit` appending `### C3`; `Write` appending a section | allow | allow ×3 |
| MINOR 10 | symlinked `CLAUDE_PROJECT_DIR` test present and green (test 197 of `unit`) | present | present |

## Checks

| Check | Command | Result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass** — 204 tests; 162–204 are the 43 `91-orchestrator-guard` tests, all `ok` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **pass** (exit 0) |
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **clean** |
| bats (devShell) | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | 43/43 |
| pre-commit | `nix develop -c githooks/pre-commit` | **exit 1** — `tasks: docs/OPERATIONS.md queue block was stale`; **exit 0** once the regenerated board is staged. Structural and identical to OG1b/OG1r, not the implementer's — but `FACTORY-CHECKS pre-commit=pass` is only reproducible with the board staged, which the result line does not say. |
| wall time (10 calls) | `git status` 14 ms; `nix develop -c git commit --amend` 12 ms; `rm <plan>` 18 ms; 200 plain tokens 18 ms; 200 bare `git` words 18 ms | under budget |
| **wall time — 200-token command of paths** | `ls <200 × docs/aN/bN.md>` | **907 ms/call** — over the plan's `< 300 ms/call on a 200-token command`. Scaling measured: 10 paths 53 ms, 25 → 117 ms, 50 → 238 ms, 100 → 451 ms, 500 → 2140 ms (≈4.3 ms per path token; the budget is crossed at ~65 paths). MAJOR 18. |

**Red before green.** OG1r's guard (`git show FETCH_HEAD:tools/orchestrator-guard.sh`
from `ws/og3/OG1r`) with OG1r2's bats file fails exactly three tests: 20 (`a git
rewrite across a newline`), 21 (`a launcher prefix does not hide a git rewrite`),
22 (`a launcher, newline or extra writer does not hide a plan write`). Test 23
(`no command position — the allow cases stay allowed`) passes on the old guard,
correctly: it is an allow-control, not a behaviour change. Honest red — no
inflation, and the three reds are precisely og3's two MAJORs.

## Mutation table

Each applied to `tools/orchestrator-guard.sh`, the bats file run, then reverted.
The clone was left clean (`git status --porcelain` empty after each).

| # | Mutation | Failures | Killed by |
|---|---|---|---|
| **M1** | `\n` dropped from `normalise_command`'s separators (`c=${c//$'\n'/ }` removed) | **2** | 20, 22 |
| **M2** | both token scans stop after the first token (`i < n` → `i < 1`) — a launcher hides the rest | **6** | 9, 16, 17, 20, 21, 22 |
| **M3** | basename rule off (`base=${t##*/}` → `base=$t`) | **1** | 9 |
| **M4** | `plan_write_verdict` returns immediately (plan-path write rule off) | **4** | 16, 17, 18, 22 |
| **M5** | value-skip list neutered in `git_verdict` (`-c/-C/--git-dir/…` case removed) | **2** | 7, 9 |

All four demanded mutations die, and so does M5. **M5, reported as the brief
asked:** with the value skip off, `git -c a=b commit --amend` is **not** still
denied — the walk reads `a=b` as the subcommand and the command is ALLOWED
(likewise `git -c a=b -C . reset --hard` and `git --git-dir .git commit
--amend`). The suite catches it: tests 7 and 9 both fail. The value-skip is
therefore load-bearing and pinned.

## Findings

**MAJOR 14 — `mv <plan> <anywhere>` moves a plan away, and it is ALLOWED.**
`tools/orchestrator-guard.sh:386-401`. `mv` is grouped with the "copy/link
family" and only denies when the plan path is the *destination*, on the stated
ground that "reading *from* a plan stays allowed". That reasoning is right for
`cp`/`ln`/`install`/`dd` and wrong for `mv`: moving *from* a plan destroys it at
its path. Verified ALLOWED: `mv <plan> /tmp/x`, `mv <plan> ./y`,
`mv -f <plan> ../x.md`, `mv <plan> <plan>.bak` (a rename inside the plans dir —
the typed headings vanish from the path the task graph reads). The behaviour is
also shape-sensitive in a way no reader would predict: `mv <plan> y` (a bare
destination with no `/`) **denies**, because the destination search only accepts
`*/*` tokens and so falls back to the plan itself. The plan's contract is
explicit and was not followed: "any WRITE VERB token anywhere (`sed` with `-i*`,
`rm`, **`mv`**, `cp`, …) in a command that ALSO names a realpath-normalised plan
path → deny". Fix: move `mv` into the operand-writer group with `rm`/`tee`.

**MAJOR 15 — the plans *directory* is never recognised, so directory-level
destruction is allowed.** `:347-359`. `plan_seen` is set only when a token
realpath-resolves to a `*.md` file **directly under** the plans dir, or when the
raw text contains the literal `superpowers/plans/` **with its trailing slash**.
So the trailing slash decides the verdict: `rm -r docs/superpowers/plans/`
denies, `rm -r docs/superpowers/plans` — every plan in the repo — is **ALLOWED**.
Also ALLOWED: `rm -rf docs/superpowers`, `mv docs/superpowers/plans /tmp/`,
`find docs/superpowers/plans -name "*.md" -delete`, `git clean -fdx
docs/superpowers/plans`. Fix: treat a token that resolves to the plans dir (or
any ancestor of it) as naming plans, and keep the write-verb scan as it is.

**MAJOR 16 — relative paths are resolved against `CLAUDE_PROJECT_DIR`, never
against the shell's working directory.** `:303-311`, `:536`. Verified ALLOWED:
`cd docs/superpowers/plans && rm x.md`, `cd docs/superpowers/plans; rm x.md`,
`cd docs/superpowers && rm plans/x.md`. This is one Bash call, not a
multi-turn trick, and `cd … && <verb>` is ordinary spelling. The Claude Code
PreToolUse payload carries a `cwd` field the guard never reads; even without it,
a leading `cd` token in the same command could rebase the resolution (or, for a
deny-only guard, any `cd` into or under the plans dir plus a write verb could
simply deny).

**MAJOR 17 — the in-place-editor scan stops at the first operand, but `sed` and
`perl` accept options after operands.** `:371-382`: the loop walks forward from
`sed`/`perl` and `break`s on the first token that does not start with `-`.
GNU sed parses options anywhere, so `sed -e s/a/b/ -i <plan>`, `sed s/a/b/ -i
<plan>` and `perl -pe s/a/b/ -i <plan>` all edit the plan in place and are
**ALLOWED**, while `sed -i -e s/a/b/ <plan>` denies. The fix is one word: scan
the whole invocation (to the next separator) for an `-i*`/`--in-place` token
instead of stopping at the first operand — this is a deny-only guard, so there
is no cost to looking further.

**MAJOR 18 — the stated wall-time acceptance is missed on a 200-token command.**
Plan step 4: "< 300 ms/call on a 200-token command". Measured over 10 calls, a
200-token command whose tokens are paths (`ls docs/a0/b0.md … docs/a199/b199.md`)
costs **907 ms/call**; `git add` of 100 paths costs 451 ms, of 500 paths
2140 ms. Root: `:348-355` calls `resolve_path` **and** `is_plan_file` for every
token containing `/`, and each forks `realpath` (plus `basename`/`dirname`, plus
two command substitutions) — and `is_plan_file` recomputes `plans_canon` with a
fresh `realpath` on every call. Both are removable: hoist `plans_canon` to a
one-time computation, and pre-filter tokens with a pure-bash `case` on the
plans-dir prefix before paying for a fork. The suite's timing test (204) uses a
short command and so never sees this; the `.claude/settings.json` timeout is
10 s, which a ~2 300-path command would exceed — and a timed-out PreToolUse hook
is a non-blocking error, i.e. an **allow**.

**MINOR 17 — stripping quotes to a *space* splits words, creating a new
bypass class.** `:99-104`. Replacing `"`/`'`/`` ` `` with a space is what makes
`bash -c "git push"` and `` `git push` `` work (good), but it also means
`git p''ush` becomes `git p  ush`, so the subcommand reads as `p`. Verified
ALLOWED: `git p''ush`, `git pu"sh"`, `r''m <plan>`, and the expansion family
`g=git; $g push`, `git $(echo push)`, `eval git\ push`. Adversarial only, and
shared with `hook-guard.py`; the cheap kill for the quote half is to scan *two*
token streams — quotes→space and quotes→empty — and deny if either fires. The
header should stop implying quote handling is complete.

**MINOR 18 — the write-verb list is still an enumeration, and still short.**
`patch <plan> < d`, `awk -i inplace 1 <plan>`, `ex -sc wq <plan>` and
`sponge <plan> < k` are all ALLOWED. The plan enumerates the verbs, so this is
not a deviation — but it is the third gate at which the enumeration reflex is
the finding, and `patch` in particular is an ordinary way to apply a diff.

**MINOR 19 — `>|` is not a redirect token.** `:120-121` pads `>>` and `>`, so
`>|` becomes `> |` and the redirect scan (`:477-485`) looks at `|` rather than
the path: `printf x >| <plan>` is ALLOWED. One more substitution in
`pad_operators`.

**MINOR 20 — the runbook over-promises again (og3's MINOR 16, recurring).**
`docs/runbooks/session.md` rule 2 lists `mv` flatly among the write verbs (it is
destination-only — MAJOR 14) and rule 2's preamble promises that no separator
or launcher hides a write (true) without saying that the plans *directory* and a
`cd` are outside the rule (MAJOR 15, 16). The closing line "far over the
<300 ms per-edit budget (bash is ~12 ms)" is true only for short commands
(MAJOR 18). Narrow the prose or widen the rules — widen them.

**NOTE — the accepted over-denials are real and confirmed.** `echo "git commit
--amend"` and `rm /tmp/x && cat <plan>` both DENY, as OG1r2 said they would.
Recording them as the brief asked: this is the correct direction for a deny-only
guard, and the runbook states it plainly instead of over-promising.

**NOTE — `git add <plan>` and the board write are ALLOWED, and both are right.**
Staging cannot alter the worktree file, and `nix develop -c python3
pkgs/evidence/tasks.py --root . write-board --board docs/OPERATIONS.md` writes
the board, not a plan — the guard lets it through.

**NOTE — `pre-commit` is red on the committed tree, blamelessly.** Identical to
OG1b and OG1r: `landed_subjects()` reads git log, so OG1r2's key drops out of the
generated queue block the moment its commit exists; exit 0 once the regenerated
board is staged. The merge step must include the board regeneration. The result
line's `pre-commit=pass` is true only under that condition and does not say so.

## Deviations

Accepted:

- `tools/orchestrator-guard.sh` (bash) rather than the plan's `.py` — sanctioned
  at OG1; 12–18 ms/call on ordinary commands (but see MAJOR 18).
- `docs/ledger/task-status.toml` untouched because base already carries OG1b's
  superset — disclosed in FACTORY-NOTES and correct; `touches` is a superset,
  not an obligation.
- `docs/MAP.md` regenerated (one `tests/unit` count and one `tools/` line),
  inside OG1r2's declared touches.
- `flake.nix`: exactly the one `cp` line plus its two comment lines, mirroring
  G6's.
- `.claude/settings.json`: G6's SessionStart entry byte-for-byte plus the two
  PreToolUse matchers and nothing else; no CR1 Stop/PreCompact entries exist on
  base to preserve.
- The header states the symlink-out choice (MINOR 8) and the deny-only
  over-denial trade; FACTORY-NOTES claims 43 tests and 43 is what runs.

Not accepted:

- The plan's contract (b) lists `mv` as an unconditional write verb; the
  implementation made it destination-only and `mv <plan> /tmp/x` therefore
  deletes a plan. MAJOR 14.
- The contract says a command that "ALSO names a realpath-normalised plan path"
  denies. `rm -r docs/superpowers/plans` names the plans by naming their
  directory, and `cd docs/superpowers/plans && rm x.md` names one by relative
  path; both are ALLOWED. MAJOR 15, 16.
- The contract's verb spelling is "`sed` with `-i*`" — a property of the
  invocation, not of the token immediately after `sed`. `sed -e s/a/b/ -i
  <plan>` has `-i*` and is ALLOWED. MAJOR 17.
- Step 4's "< 300 ms/call on a 200-token command" is unmet at 907 ms. MAJOR 18.

Verdict: **REJECTED** (fourth rejection on this task). The token scan itself is
correct and complete — every og3 MAJOR is dead and every demanded case passes.
What remains is four rule-level gaps, each a one-to-three-line fix: `mv` belongs
with `rm`, the plans *directory* must count as naming plans, a leading `cd` must
rebase (or simply deny), and the `-i` search must cover the whole invocation.
