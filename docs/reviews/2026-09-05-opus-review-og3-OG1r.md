---
reviewer: opus
majors: 2
minors: 6
---
# Opus gate — seat run og3, task OG1r — REJECTED

## Summary

One commit (`8330622`) on base `5349582`, subject md5 `7b1b679d…` — byte-identical
to OG1's and to OG1r's — both trailers present, touches exactly OG1r's declared
seven files, `.claude/settings.json` keeps G6's SessionStart entry byte-for-byte,
`flake.nix` is the one sanctioned `cp` line. 39 bats tests green (`unit` 158–196
of 196), `lint` green, shellcheck clean, 13–50 ms per call. Honest red: OG1r's
tests against OG1b's guard fail 5 (9, 15, 16, 17, 18). All four demanded
mutations are killed, and OG1b's surviving mutation 16 now dies (MINOR 10 fixed).
Every case in the gate brief's two lists — 18 tokeniser denies, 6 allows, 11
plan-file denies, 7 allows — behaves as specified, and every kept OG1b fix still
holds.

It is rejected because **the tokeniser replaced one enumeration with two others,
and both leak the same MAJOR**. The walker only inspects the *first* word of each
segment, and its segment boundaries are an enumerated set that omits the newline;
its transparent-prefix set is an enumerated set that omits every launcher but
`env`/`command`/`VAR=`. So `nix develop -c git commit --amend` — this repo's own
documented way to run anything ("All tooling lives in the devShell"; "commits must
go through the devShell") — is **ALLOWED**, as is a two-line `cd /x⏎git commit
--amend`, `timeout 5 git push`, `nix develop -c rm docs/superpowers/plans/x.md`
and `echo a⏎rm docs/superpowers/plans/x.md`. Both design changes are defeated by
spellings that require no adversarial intent.

## Tokeniser cases

Guard run as `env CLAUDE_PROJECT_DIR=<fixture> bash tools/orchestrator-guard.sh`
with compact `ensure_ascii=False` payloads on stdin, exactly as Claude Code sends
them. All 24 brief cases behave as demanded.

| Command | Expected | Observed |
|---|---|---|
| `git --work-tree=. commit --amend` | deny | **DENY** |
| `git -P commit --amend` | deny | **DENY** |
| `git --literal-pathspecs commit --amend` | deny | **DENY** |
| `git --exec-path=/x commit --amend` | deny | **DENY** |
| `git --no-replace-objects push` | deny | **DENY** |
| `git --namespace=n push` | deny | **DENY** |
| `git --icase-pathspecs rebase -i` | deny | **DENY** |
| `git -c a=b -C . reset --hard` | deny | **DENY** |
| `/run/current-system/sw/bin/git commit --amend` | deny | **DENY** |
| `command git commit --amend` | deny | **DENY** |
| `\git commit --amend` | deny | **DENY** |
| `GIT_EDITOR=true git commit --amend` | deny | **DENY** |
| `git   commit   --amend` | deny | **DENY** |
| `git commit \`⏎`--amend` | deny | **DENY** |
| `git -c a=b commit --amend` (value-taking flag) | deny | **DENY** |
| `git --git-dir .git commit --amend` (space value) | deny | **DENY** |
| `x && git push` | deny | **DENY** |
| `(git push)` | deny | **DENY** |
| `git --work-tree=. status` | allow | allow |
| `git -c a=b log -1` | allow | allow |
| `git -P diff` | allow | allow |
| `git --no-pager show` | allow | allow |
| `git commit -F msg` | allow | allow |
| `git -c a=b status` | allow | allow |
| `echo "git commit --amend is banned"` | decide | **allow** — the right call; see the NOTE below |

Extras of mine that also behave: `/usr/bin/git rebase -i`, `env git push`,
`git -c core.editor=true commit --amend`, `git -C/home/x commit --amend`,
`git --work-tree . commit --amend`, `git --super-prefix=x/ push`,
`git push --dry-run` (denied outright, as the plan asked), `git status; git push`
— all DENY. MINOR 7 from OG1b is gone: absolute-path `git push`/`rebase` now deny.

Extras that do **not** — the rejection:

| Command | Expected | Observed |
|---|---|---|
| `nix develop -c git commit --amend` | deny | **ALLOWED** |
| `nix develop -c git push` | deny | **ALLOWED** |
| `timeout 5 git push` | deny | **ALLOWED** |
| `cd /x`⏎`git commit --amend -m y` | deny | **ALLOWED** |
| `set -e`⏎`git push origin main` | deny | **ALLOWED** |
| `true & git push` (single `&`) | deny | **ALLOWED** |
| `if true; then git push; fi` | deny | **ALLOWED** |
| `for f in x; do git push; done` | deny | **ALLOWED** |
| `f() { git push; }; f` | deny | **ALLOWED** |
| `! git push`, `time git push`, `nohup git push` | deny | **ALLOWED** ×3 |
| `bash -c "git push"`, `` `git push` ``, `echo x \| xargs -I{} git push` | deny | **ALLOWED** (quoting/nesting — MINOR) |

Control: `cd /x`⏎`sudo y` **denies** — the sudo *regex* carries `\n` in its
boundary class (`(^|[;&|()$NL])`). The two new walkers do not. The guard is
therefore internally inconsistent about what a command boundary is.

## Plan-file cases

Fixture: `<proj>/docs/superpowers/plans/x.md` with two typed headings, a
`docs/notes/plans/x.md` decoy, a symlink into the plans dir and one out of it.
All 18 brief cases behave as demanded.

| Command | Expected | Observed |
|---|---|---|
| `sed -i 's/x/y/' docs/superpowers/plans/x.md` | deny | **DENY** |
| `rm docs/superpowers/plans/x.md` | deny | **DENY** |
| `mv a docs/superpowers/plans/x.md` | deny | **DENY** |
| `cat > docs/superpowers/plans/../plans/x.md` | deny | **DENY** |
| `nix develop -c python3 - <<'PY'` … `open("…/plans/x.md","w")` | deny | **DENY** |
| `python3 -c "pathlib.Path('…/plans/x.md').write_text('')"` | deny | **DENY** |
| `git checkout -- docs/superpowers/plans/x.md` | deny | **DENY** |
| `git restore docs/superpowers/plans/x.md` | deny | **DENY** |
| `perl -i -pe s/a/b/ docs/superpowers/plans/x.md` | deny | **DENY** |
| `tee docs/superpowers/plans/x.md` | deny | **DENY** |
| `truncate -s0 docs/superpowers/plans/x.md` | deny | **DENY** |
| `rm <abs plan path>`, `rm docs/superpowers/plans//x.md` | deny | **DENY** ×2 |
| `cat docs/superpowers/plans/x.md` | allow | allow |
| `grep -n '^### ' docs/superpowers/plans/x.md` | allow | allow |
| `sed -n 1,5p docs/superpowers/plans/x.md` | allow | allow |
| `git diff -- docs/superpowers/plans/x.md` | allow | allow |
| `wc -l docs/superpowers/plans/x.md` | allow | allow |
| `git add docs/superpowers/plans/x.md` | decide | **allow** — correct; see the NOTE |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | allow | allow |
| `rm docs/notes/plans/x.md` (decoy) | allow | allow |
| `git checkout -- README.md`, `git restore README.md` | allow | allow ×2 |

Extras that do **not** behave:

| Command | Expected | Observed |
|---|---|---|
| `nix develop -c rm docs/superpowers/plans/x.md` | deny | **ALLOWED** |
| `nix develop -c sed -i s/a/b/ docs/superpowers/plans/x.md` | deny | **ALLOWED** |
| `echo a`⏎`rm docs/superpowers/plans/x.md` | deny | **ALLOWED** |
| `echo a`⏎`sed -i /d/ docs/superpowers/plans/x.md` | deny | **ALLOWED** |
| `xargs -a f rm docs/superpowers/plans/x.md` | deny | **ALLOWED** |
| `cp k docs/superpowers/plans/x.md && echo done` | deny | **ALLOWED** (MINOR 12) |
| `cp k docs/superpowers/plans/x.md /dev/null` | deny | **ALLOWED** (same) |
| `dd of=docs/superpowers/plans/x.md if=/dev/null` | deny | **ALLOWED** (MINOR 13) |
| `install -m644 k docs/superpowers/plans/x.md` | deny | **ALLOWED** (same) |
| `ed docs/superpowers/plans/x.md` | deny | **ALLOWED** (same) |
| `rm /tmp/junk && cat docs/superpowers/plans/x.md` | allow | **DENIED** (MINOR 14, over-reach) |
| `git commit -m x; echo --amend` | allow | **DENIED** (same) |

## Kept fixes

Every OG1b fix still holds; nothing regressed.

| Finding | Probe | Expected | Observed |
|---|---|---|---|
| MAJOR 1 | `Edit` via `…/plans/../plans/x.md`, `…/superpowers/./plans/x.md`, `…/plans//x.md`, relative, absolute | deny | **DENY** ×5 |
| MAJOR 1 | `Edit` through a symlink **into** the plans dir | deny | **DENY** |
| MAJOR 1 | `docs/notes/plans/x.md` decoy | allow | allow |
| heading rule | key rename `A1`→`A9`; size `S`→`M`; `Write` dropping a heading | deny | **DENY** ×3 |
| heading rule | body edit; append a new `### C3` section | allow | allow ×2 |
| MINOR 3 | `grep -rn sudo docs/brief.md`, `echo 'never sudo here'`, `cat … \| grep sudo`, `rg nixos-rebuild docs/` | allow | allow ×4 |
| MINOR 3 | `sudo x`, `x; sudo y`, `x && sudo y`, `(sudo y)`, `x \|\| sudo y`, `⏎sudo y` | deny | **DENY** ×6 |
| MINOR 4 | `tee -a /var/lib/secrets/x`, `cp k /run/baskets/x`, `mv k /var/lib/lanes/x`, `install -m600 k /var/lib/secrets/x`, `>  /var/lib/helm/x`, `>>/var/lib/helm/x` | deny | **DENY** ×6 |
| MINOR 5 | malformed JSON, `{`-prefixed truncated JSON, empty input | allow + warn | allow + warn ×3 |
| MINOR 6 | `MultiEdit` with an escaped quote, both orderings | deny | **DENY** ×2 |
| **MINOR 9** | `cp /var/lib/secrets/x /tmp/y` | **allow** | **allow** — fixed |
| **MINOR 9** | `cp k /var/lib/secrets/x` | **deny** | **DENY** |
| **MINOR 10** | symlinked `CLAUDE_PROJECT_DIR` test | present | test 32, and it kills the old survivor |
| MINOR 8 | `Write` through a symlink **out of** the plans dir | stated | allowed, and the choice is now stated at `tools/orchestrator-guard.sh:28-32` — accepted |

## Checks

| Check | Command | Result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass** — 196 tests; 158–196 are the 39 `91-orchestrator-guard` tests, all `ok` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **pass** |
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **clean** |
| bats (devShell) | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | 39/39 |
| pre-commit | `nix develop -c githooks/pre-commit` | **exit 1** — `tasks: docs/OPERATIONS.md queue block was stale`; **exit 0** once the regenerated board is staged. Base `5349582` is exit 0. Structural, identical to OG1b's NOTE, not the implementer's. |
| `docs/MAP.md` | `repomap.py check` at HEAD / with MAP reverted to base | clean at HEAD; `stale` at base ⇒ the change is forced. Carried from OG1b as FACTORY-NOTES says; in OG1r's declared touches. |
| wall time (10 calls each) | `git status` 16–18 ms; deny-sudo 13–14 ms; `git --work-tree=. commit --amend` 14–16 ms; plan-write `sed -i` 29–30 ms; 201-`git`-word command 21–23 ms; 8 KB single token 21–22 ms; `Write` of the real 41 923-byte plan 46–50 ms | all far under 300 ms |

**Red before green.** OG1b's guard (`git show FETCH_HEAD:tools/orchestrator-guard.sh`
from `ws/og1/OG1b`) with OG1r's bats file fails 5 tests: 9 (git tokeniser behind
any global option), 15 (MINOR 9 read-from-protected), 16/17/18 (the three
plan-write rules). Honest red — the new deny cases genuinely pass through the old
guard. Tests 11 and 32 were already green on OG1b, correctly: `git push` was
already denied outright there, and the MINOR 10 test is a mutation-killer, not a
behaviour change.

## Mutation table

Each applied to `tools/orchestrator-guard.sh`, the bats file run, then reverted.
The clone was left clean.

| # | Mutation | Failures | Killed by |
|---|---|---|---|
| **M1** | value-taking option list neutered (tokeniser stops skipping flag values; `-c a=b commit` misread) | **2** | 7, 9 |
| **M2** | basename rule removed (`*/git` dropped) — `/…/bin/git` allowed | **1** | 9 |
| **M3** | `plan_write_verdict` returns immediately (plan-path rule removed) | **3** | 16, 17, 18 |
| **M4** | `resolve_path` returns the raw path (realpath removed) | **4** | 16, 29, 30, 31 |
| M5 | `is_plan_file` stops canonicalising the *plans-dir* side (OG1b's mutation 16, the survivor) | **1** | 32 — **now dies**, MINOR 10 fixed |
| M6 | `;`, `\|`, `(`, `)` removed from the command-position *entry* set in both walkers | 0 | **survivor** |
| **M7** | `;`, `\|`, `(`, `)` removed from the "back to command position" reset in both walkers | **1** | only 16 — and `git status; git push` becomes **ALLOWED** with no test failing |

The four demanded mutations all die. M7 is the tell: the git rule's entire
boundary handling rests on one enumerated token list, and the suite pins only
`&&` and a leading `(`. Nothing tests `;`, `|`, `)` or a newline for git, which
is precisely where the shipped guard leaks.

## Findings

**MAJOR 12 — a newline is not a command boundary; both design changes fall to a
two-line command.** `tools/orchestrator-guard.sh:130,182` (git) and `:343,398`
(plan writes). `normalise_command` folds `\`+newline and tabs; a bare newline
survives into `tokenise`, which splits on it as plain whitespace, so the walkers
never learn a new command started. Verified ALLOWED: `cd /x`⏎`git commit --amend
-m y`, `set -e`⏎`git push origin main`, `echo a`⏎`rm docs/superpowers/plans/x.md`,
`echo a`⏎`sed -i /d/ docs/superpowers/plans/x.md`. Multi-line Bash commands are
the ordinary spelling in this repo — the transcript for this very task is full of
them — so this is not an exotic bypass. The guard's own sudo rule carries `\n` in
its boundary class and denies `cd /x`⏎`sudo y`; the new walkers regressed against
the rule they sit beside. The single `&` (`true & git push`), `{`/`}`, and the
shell keywords `then`, `do`, `else` are missing from the same set.

**MAJOR 13 — the walk stops at the first non-transparent word, so any launcher
prefix hides everything after it.** `tools/orchestrator-guard.sh:131,178` and
`:344,394`: only `env`, `command` and a `VAR=value`-shaped token keep
`cmd_pos=1`; every other first word sets `cmd_pos=0`, and nothing restores it
until an enumerated separator. Verified ALLOWED: **`nix develop -c git commit
--amend`**, **`nix develop -c git push`**, **`nix develop -c rm
docs/superpowers/plans/x.md`**, `nix develop -c sed -i s/a/b/
docs/superpowers/plans/x.md`, `timeout 5 git push`, `nohup git push`,
`time git push`, `! git push`, `xargs -a f rm docs/superpowers/plans/x.md`.
`nix develop -c …` is the house prefix CLAUDE.md prescribes for *everything*
("All tooling lives in the devShell… commits must go through the devShell"), so
the guard is defeated by the repo's own documented invocation style with zero
intent to evade. The implementer already knew launchers nest — the python3 scan
at `:406` is deliberately run *outside* the command-position walk with the comment
"the interpreter is often nested behind a launcher (`nix develop -c python3 -`)"
— and applied that insight to exactly one rule of four.

Both MAJORs share one root, and it is the root OG1 and OG1b were rejected for:
**an enumeration standing in for a rule.** The flag list became a proper walk, but
two new enumerations (the boundary set, the transparent-prefix set) were minted in
the same commit and both are short. The durable shape is to stop asking "is this
word in command position" and instead scan *every* token: treat any token whose
basename is `git` as a git invocation and walk forward from it, and treat any
write-verb token anywhere in a command that also names a plan path as a plan
write. That over-denies slightly (a `git` inside a quoted string), which for a
deny-only guard is the correct direction and is already the accepted trade for
`rm`/`mv`/`tee`/`truncate` today.

**MINOR 12 — `cp` checks the last token of the whole command, not of the `cp`
invocation.** `:352` reads `${toks[n - 1]}`. `cp k docs/superpowers/plans/x.md &&
echo done` and `cp k docs/superpowers/plans/x.md /dev/null` are both ALLOWED while
`cp k docs/superpowers/plans/x.md` denies. Bound the destination search to the
current segment. (The protected-prefix `cp|mv|install` rule at `:268` anchors on
`$` for the same reason and has the same suffix weakness: `cp k /var/lib/secrets/x
&& true` — untested by the suite.)

**MINOR 13 — the plan-write verb list misses ordinary writers.** `install`,
`dd of=`, `ed`, `awk -i inplace`, `ln -sf` and `sponge` on a plan path are all
allowed. The plan enumerated the verbs, so this is not a deviation — but the same
enumeration reflex is what the re-plan existed to remove, and `install` is
inconsistent: it *is* in the protected-prefix rule two functions away.

**MINOR 14 — deny-side over-reach.** `rm`, `mv`, `tee` and `truncate` fire
whenever the raw command contains the literal `superpowers/plans/` *anywhere*, so
`rm /tmp/junk && cat docs/superpowers/plans/x.md` is refused. Symmetrically, the
`--amend`/`--hard` searches at `:152` and `:168` run to the end of the whole
command across separators, so `git commit -m x; echo --amend` is refused. Deny-only,
so the cost is an annoyed orchestrator, but both are one-line fixes (scope the
search to the segment).

**MINOR 15 — quoted and nested shells escape.** `bash -c "git push"`,
`` `git push` ``, `sh -c 'rm <plan>'` are allowed because quote characters stay
glued to the token. Inherent to a token-level guard and shared with
`hook-guard.py`; worth one line in the header so it is a stated limit rather than
an assumed cover.

**MINOR 16 — the runbook over-promises again (OG1b's MINOR 11, recurring).**
`docs/runbooks/session.md` rule 3 says the git rewrites are refused "no matter how
many global options … sit in front of the subcommand", and rule 2 lists the plan
writers flatly. Neither survives a newline or a `nix develop -c` prefix. Narrow
the prose or widen the rule — widen it.

**NOTE — `echo "git commit --amend is banned"` is ALLOWED, and that is right.**
The quote stays attached to the token (`"git`), which is not a `git` word, so no
heuristic deny fires. Reporting as the brief asked: no heuristic deny is needed
here, and the allow is principled rather than accidental.

**NOTE — `git add <plan>` is ALLOWED, and that is right.** Staging copies the
worktree into the index; it cannot alter the file, and refusing it would break the
ordinary commit path the runbook prescribes. Correct call.

**NOTE — `pre-commit` is red on the committed tree, blamelessly.** Identical to
OG1b: `landed_subjects()` reads git log, so OG1r's key drops out of the generated
queue block the moment its commit exists. Exit 0 once the board is regenerated and
staged; base is exit 0. The merge step must include the board regeneration.

## Deviations

Accepted:

- `tools/orchestrator-guard.sh` (bash) rather than the plan's `.py` — sanctioned
  at OG1, re-measured here at 13–50 ms/call against a 41 923-byte plan.
- `docs/MAP.md` carried from OG1b, inside OG1r's declared touches, proved forced
  (`repomap check` says `stale` on the base copy), disclosed in FACTORY-NOTES.
- `flake.nix`: exactly the one `cp` line plus its two comment lines, mirroring G6's.
- `.claude/settings.json`: G6's SessionStart entry byte-for-byte plus the two
  PreToolUse matchers and nothing else.
- MINOR 8 settled by stating the symlink-out choice in the header, as the gate
  asked; `docs/ledger/task-status.toml` and the runbook's rule 1 carried intact.
- FACTORY-NOTES says "39 bats tests green" and 39 is what runs — no inflation.

Not accepted:

- The plan's design change 1 says "Find every `git` WORD: at a command boundary
  (start, `;`, `&&`, `||`, `|`, `(`, **newline**)". The newline is in the spec and
  absent from the implementation, and the absence is a working `--amend`. MAJOR.
- Design change 2 says "**Any** Bash command whose normalised text contains a path
  under `docs/superpowers/plans/` together with a write-capable verb". The
  implementation restricts the verb to command position and then loses command
  position after any launcher, so `nix develop -c rm <plan>` deletes a plan. MAJOR.

Verdict: **REJECTED** (third rejection on this task).
