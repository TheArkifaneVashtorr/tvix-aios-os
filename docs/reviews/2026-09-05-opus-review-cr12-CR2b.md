---
reviewer: opus
majors: 1
minors: 11
---
# Opus gate — seat run cr12, task CR2b — REJECTED

## Summary

One commit (`7fd7da1`) on base `09d7cfc`, branch `task/CR2b` in
`/home/dalhaka/factory/ws/cr12/CR2b`. Reviewed in a fresh clone at
`…/scratchpad/gate-cr12-CR2b`. Nothing under `/home/dalhaka/factory` was
modified; the live repo's `.claude/ritual-override` was never touched — every
guard run drove a throwaway fixture at `…/scratchpad/fix/nixos-fixture`.

Commit conventions are clean: **one** commit, subject byte-identical to the
plan's (md5 `8f4d122803197b0f877b28e9b40282e1` for both), both trailers
(`Generated-By: dsh … factory run cr12`, `Co-Authored-By: Claude Fable 5.1`),
three files touched — `tools/orchestrator-guard.sh`,
`tests/unit/91-orchestrator-guard.bats`, `docs/runbooks/session.md` — all inside
`touches`, no board commit.

The work is real and most of it is right. **All four CR2 MAJORs are fixed** and
all three CR2 MINORs that were "unpinned behaviour" are now pinned by tests
(cr8's two surviving mutations now die). The base for this branch is main
(`09d7cfc`, 723-line guard) which carries **no** override rule at all, so the
whole rule is new here; against CR2's guard the new suite goes red on exactly
five tests, honestly. Checks are green: shellcheck rc 0, bats 70/70, `unit`
311/311, `lint` pass. All ten demanded mutations die, og5's whole table
reproduces (only its known M-I survivor survives), and there is **no plans-dir
regression**: 24 og5 Step-1 rows, 31 og4 git rows, 26 og4 plan-write rows, 7
heading rows and 10 host rows all behave (135 payloads, 0 mismatches).

It is rejected on one MAJOR. **`rm -rf .claude/*` still ALLOWS** — together with
`mv .claude/* /tmp/`, `shred .claude/*`, `rm -rf .claude/ritual*` and
`rm .claude/[r]itual-override`. That row is a bolded **HOLE** in the CR2 review's
table, and Step 1 says "every spelling of the review's table as a DENY case". A
glob token never canonicalises to `.claude` and the override rule — unlike the
plan rule — has no raw-text fallback, so the ancestor arm never sees it. The
asymmetry is measurable in one pair:

```
rm -rf docs/superpowers/plans/*   -> DENY   (plan rule, raw fallback :497-499)
rm -rf .claude/*                  -> ALLOW  (no fallback in override_verdict)
```

The runbook's own claim — "protected the same way the plans *directory* is" —
is therefore false for this spelling, and `rm -rf .claude/*` is a routine
"empty a directory but keep it" idiom that deletes the operator's file.

Method: fresh clone; the guard driven only from that clone with
`env CLAUDE_PROJECT_DIR=<fixture> HOME=<fixture parent> bash
tools/orchestrator-guard.sh` on a compact `ensure_ascii=False` payload of the
real Claude Code shape, `cwd` at the **top level**
(`{"session_id":…,"cwd":…,"hook_event_name":"PreToolUse","tool_name":…,
"tool_input":{…}}`). Fixture: a git repo with `.claude/ritual-override`,
`.claude/settings.json`, `.claude/worktrees/x`, `docs/superpowers/plans/x.md`,
`docs/notes/plans/x.md` (decoy), `k`, `sub/`, `link-to-override` → the override,
`plans-link` → the plans dir, `link-into-plans.md` → the plan,
`docs/superpowers/plans/out.md` → outside, `elsewhere/ritual-override` → `/tmp`,
and `…/fix/other/.claude/ritual-override` outside the project. Drivers:
`…/scratchpad/drive.py`, `gencases{,2,3}.py`, `mutate.py`, `runmut.sh`,
`red.sh`, `timing.py`. 271 payloads in all.

## One mechanism

Half met, and the half that is met is the important half.

**Met.** The directory/ancestor logic is genuinely *one function*.
`is_protected_dir_or_ancestor()` (`tools/orchestrator-guard.sh:409-420`) replaces
OG1r2b's `is_plans_dir_or_ancestor` and has exactly two callers — the plan rule
at `:491` and the override rule at `:730` — each passing its own protected
directory (`plans_canon`, `override_dir`) and the same project canon. Each rule
carries the same `dir_ancestor_seen` flag beside its own exact-path flag, and the
same `cd`/`pushd`/payload-`cwd` base list. Mutating the shared function to
`return 1` (og5-M-B) kills six tests across **both** rules (44 on the plans side,
59/60/61/62/64 on the override side), which is the proof that it is shared.

**Not met.** `PROTECTED_PATHS` (`:97-100`) is read in exactly one place —
`override_verdict:696-704` — and there it `continue`s past anything whose kind is
not `file` (`:699`). So:

- the `'docs/superpowers/plans|dir'` entry is **decorative**. `plan_write_verdict`
  still hardcodes the path (`:433`, `:467`:
  `plans_canon=$(realpath -m -- "$project_dir/docs/superpowers/plans")`).
  Mutation **X1** — delete the `dir` entry from `PROTECTED_PATHS` — changes the
  tree (`0+/1−`) and kills **zero** tests, because nothing reads it.
- the Edit/Write/MultiEdit arm also hardcodes the override
  (`:960`: `[ "$resolved" = "$(realpath -m -- "$project_dir/.claude/ritual-override")" ]`)
  rather than walking the list.
- only the *first* `file` entry is ever used (`break` at `:703`), so a second
  protected file added to the list would be silently ignored.

A future protected path therefore still needs code in three places. This is
MINOR-1, not a MAJOR: the contract's operative sentence is about the
directory/ancestor logic, and that is unified.

The one behavioural consequence of the split is the MAJOR: `plan_write_verdict`
has a raw-text fallback (`:497-499`, `case "$raw" in *superpowers/plans/*`) that
catches spellings the token scan cannot canonicalise; `override_verdict` has
none.

## Rule behaviour

Fixture `<proj>` = `…/scratchpad/fix/nixos-fixture`; payload `cwd` = `<proj>`
unless noted. `base` = the guard at `09d7cfc` (main; no override rule at all),
`CR2` = `git show task/CR2:tools/orchestrator-guard.sh` (890 lines),
`CR2b` = this tree (994 lines). Reason column names which rule produced the deny.

### Step 1 — DENY spellings

| spelling | base | CR2 | CR2b | rule |
|---|---|---|---|---|
| `rm -rf .claude` | ALLOW | ALLOW | **DENY** | override |
| `rm -r .claude/` | ALLOW | ALLOW | **DENY** | override |
| `rm -rf .` | DENY | DENY | DENY | plan |
| `git clean -fd` | ALLOW | ALLOW | **DENY** | override (bare-path arm) |
| `git clean -fdx .claude` | ALLOW | ALLOW | **DENY** | override |
| `git checkout -- .claude` | ALLOW | ALLOW | **DENY** | override |
| `git restore .claude` | ALLOW | ALLOW | **DENY** | override |
| `mv .claude .claude-old` | ALLOW | ALLOW | **DENY** | override |
| `mv .claude/ritual-override /tmp/x` | ALLOW | DENY | DENY | override |
| `find .claude -name 'ritual-*' -delete` | ALLOW | ALLOW | **DENY** | override |
| `find . -name ritual-override -exec rm {} +` | DENY | DENY | DENY | plan (`.` is a plans ancestor) |
| `dd if=/dev/null of=.claude/ritual-override` | ALLOW | ALLOW | **DENY** | override (`of=` admitted, `:725`) |
| `python3 -c '…os.remove(".claude/ritual-override")'` | ALLOW | ALLOW | **DENY** | override |
| `python3 -c '…Path(".claude/ritual-override").unlink()'` | ALLOW | ALLOW | **DENY** | override |
| `python3 -c '…shutil.rmtree(".claude")'` | ALLOW | ALLOW | **DENY** | override |
| `cd .claude && rm ritual-override` | ALLOW | DENY | DENY | override (cd rebase) |
| `rm ritual-override` *(cwd=`<proj>/.claude`)* | ALLOW | DENY | DENY | override (payload cwd) |
| `rm link-to-override` *(symlink)* | ALLOW | DENY | DENY | override |
| Write/Edit/MultiEdit `.claude/ritual-override` (rel) | ALLOW | DENY | DENY | override |
| Write/Edit/MultiEdit `<proj>/.claude/ritual-override` (abs) | ALLOW | DENY | DENY | override |

### Step 1 — ALLOW spellings

| spelling | CR2b | note |
|---|---|---|
| `ls -la .claude` | allow | correct |
| `cat .claude/ritual-override` | allow | correct |
| `stat .claude/ritual-override` | allow | correct |
| `git status` | allow | correct |
| `test -f .claude/ritual-override` | allow | correct |
| `rm -rf .claude/worktrees/x` | allow | **no over-denial of the sibling** — the ancestor rule counts ancestors, not descendants; the runbook says so |
| `rm <scratch>/fix/other/.claude/ritual-override` | allow | correct (outside the project) |

### The brief's additional spellings

| spelling | CR2b | rule |
|---|---|---|
| `rmdir .claude` | DENY | override |
| **`rm -rf .claude/*`** | **ALLOW** | — **HOLE (MAJOR-1)** |
| `cd .claude && rm *` | DENY | override (the `cd` argument names `.claude`) |
| `mv .claude /tmp/gone` | DENY | override |
| `git clean -fdx` | DENY | override (bare-path arm) |
| `git checkout HEAD -- .claude` | DENY | override |
| `rsync -a /tmp/empty/ .claude/` | DENY | override |
| `shred .claude/ritual-override` | DENY | override |
| `chmod 000 .claude/ritual-override` | ALLOW | **not covered by the plan** — `chmod` is in neither rule's verb list and is not a content write; a note, not a finding |
| `truncate -s0 .claude/ritual-override` | DENY | override |
| `tee .claude/ritual-override` | DENY | override |
| `cp k .claude/ritual-override` | DENY | override (destination) |
| `install -m644 k .claude/ritual-override` | DENY | override |
| `ln -sf k .claude/ritual-override` | DENY | override |
| `perl -e 'unlink ".claude/ritual-override"'` | DENY | override (bare `unlink` token, `:762`) |
| `python3 -c '…os.rename(".claude/ritual-override","x")'` | DENY | override |
| `python3 -c '…shutil.move(".claude","y")'` | DENY | override |

All fourteen of the same spellings with **absolute** paths DENY
(`rm -rf <proj>/.claude`, `rmdir`, `mv`, `rm <abs override>`, `shred`,
`truncate`, `tee`, `cp`, `install`, `ln`, `dd of=`, `find … -delete`,
`python3 os.remove`, `perl unlink`). All eight with a **payload `cwd` of the
project's parent** DENY (`rm -rf nixos-fixture/.claude`, `rmdir`, `mv`, `rm
…/ritual-override`, `cp k …`, `dd of=…`, `python3 os.remove`, and bare
`git clean -fd`).

### Further adversarial probes

DENY (26): `rm -rf ./.claude`, `rm -rf .claude/.`, `rm -rf .claude/./`,
`rm -rf ./.claude/`, `find .claude -delete`, `bash -c 'rm -rf .claude'`,
`cp /dev/null .claude/ritual-override`, `: > …`, `printf '' > …`,
`env -C .claude rm ritual-override`, `sh -c "rm …"`, `echo x >| …`,
`echo x >> …`, `cat k > …`, `rm -- …`, `rm -rf -- .claude`, `unlink …`,
`git rm -f …`, `nix develop -c rm -rf .claude`, `timeout 5 rm -rf .claude`,
`rm -rf .claude ; echo done`, `echo a`⏎`rm -rf .claude`, `r''m -rf .claude`,
`rm -rf ~/nixos-fixture/.claude`, `echo x > link-to-override`,
`rm <abs>/link-to-override`.

ALLOW, correctly: `git worktree remove .claude/worktrees/x`,
`rm elsewhere/ritual-override` (a symlink of that name pointing at `/tmp`),
`python3 -c 'open(".claude/ritual-override","w")'` — denies, but by the **plan**
rule's `python*` arm, not the override's (the override's `open(…,"w")` arm needs
`seen`, which it has; the plan rule simply fires first).

ALLOW, out of contract, recorded: `tar -C .claude -xf /tmp/a.tar`,
`xargs rm < .claude/list`, `git stash -u` (see MINOR-4).

### Symlinks (item 4)

| case | CR2b |
|---|---|
| `rm link-to-override` (symlink INTO the file) | **DENY** — `canon_path`'s `[ -L ]` branch (`:387`) |
| `rm <abs>/link-to-override` | **DENY** |
| `echo x > link-to-override` | **DENY** (redirect loop, `:883-892`) |
| a symlink OUT of `.claude` — `docs/superpowers/plans/out.md` → `/tmp/elsewhere` | DENY, by the plan rule's raw fallback (og5 MINOR-9, unchanged) |
| `rm elsewhere/ritual-override` (named `ritual-override`, points at `/tmp`) | **ALLOW** — judged by its target, correct |
| `rm plans-link` (symlink AT the plans dir) | DENY (plan rule), unchanged |

Pinned: test 67 (`rm through a symlink to the override denies`); mutation M-F
(symlink resolution off) kills 35 and 67.

### Plans-dir regression — none

Re-ran og5's Step-1 rows as payloads (23 command rows + the payload-`cwd` row =
**24/24** as og5 recorded; the 25th og5 row is the `echo "a'b"` tokeniser
assertion, which is bats test 52 and passes), og4's **31/31** git rows, og4's
**26/26** plan-write rows (17 deny + 7 allow + both accepted over-denials),
**7/7** heading/Edit rows and **10/10** host rows. 135 payloads, **0**
mismatches. Nothing regressed.

## Over-denial audit

Every documented launch/commit recipe **ALLOWS** (22/22):

`git add docs/superpowers/plans/x.md`, `git add docs/OPERATIONS.md`,
`nix develop -c git commit -q -F /tmp/msg`,
`bash <scratch>/launch.sh cr9 CR3b 2026-09-05-context-reset-ritual.md`,
`git pull --ff-only /home/dalhaka/factory/ws/cr12/CR2b task/CR2b`,
`tools/factory/seat/factory-integrate cr12 CR2b`,
`nix build .#checks.x86_64-linux.unit -L --no-link`,
`nix develop -c bats tests/unit/91-orchestrator-guard.bats`,
`curl --noproxy '*' -s http://127.0.0.1:8080/health`, `pgrep -af factory-wave`,
`cat docs/OPERATIONS.md`, `cat .claude/settings.json`,
`sed -n '1,30p' docs/runbooks/session.md`, `nix develop -c githooks/pre-commit`,
`git log --oneline -5`, `git status --porcelain`, `rm -f result`,
`mv result result.old`, `nix develop -c treefmt`, `git add -A`, `ls .claude`,
`git diff --stat`.

The brief's four named probes:

| probe | base (main) | CR2b | verdict |
|---|---|---|---|
| `git commit -q -m '…rm…mv…git clean….claude…'` (prose) | allow | **DENY** (override) | new over-denial — MINOR-3 |
| `git commit -q -m 'docs: … removes .claude/ritual-override when done'` | allow | allow | no delete verb token |
| `sed -n '1,30p' <plan> \| grep -i ritual` (a read with `-i`) | DENY | DENY | **unchanged** — og5's rule-4 `-i*` over-denial, not new |
| `sed -n '1,30p' .claude/ritual-override \| grep -i x` | allow | **DENY** (override) | same shape, now on the override side |
| `nix develop -c python3 - <<'PY' … open('docs/OPERATIONS.md','w') … PY` | allow | **allow** | the board edit is *not* refused by this guard; whatever refused one today was a different token (no plan or override path is named) |

Newly refused by CR2b, none of them a documented recipe:

```
git clean -n        DENY   (a dry run that deletes nothing)
git clean -nd       DENY
git clean           DENY
git checkout        DENY
git checkout -      DENY   (switch to the previous branch)
git restore         DENY
echo 'git checkout' DENY   (prose)
```

Cause: the bare-path arm at `:830-846`. After a `clean|checkout|restore`
subcommand it scans forward for the first non-option token; finding none it
denies unconditionally, on the (correct) reasoning that a pathless
clean/checkout/restore touches the whole worktree. It cannot tell `-n` from
`-f`. `git checkout <branch>`, `git checkout -b <branch>` and
`git restore --staged <file>` all still allow, and the documented recipes are
untouched — so this is MINOR-2, but the runbook does not mention it.

Mutation **X2** (delete the bare-path arm) kills test 61, so the arm is pinned.

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| check | command | rc | result |
|---|---|---|---|
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **0** | clean |
| bats 91 | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | **0** | **70/70 ok** |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **0** | **311/311 ok**, last `ok 311 blocks files older than 7 days are reaped on each run` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **0** | pass |
| pre-commit | `nix develop -c githooks/pre-commit` | **1** | treefmt `All checks passed!`, 34 files already formatted, then `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again` |

The `pre-commit` rc 1 is the known H1 chicken-and-egg every gate on this line has
recorded, and the implementer's note names it. Its one-line diff:

```
-… B1 CR2b CR3r PW1glm PW1kimi PW1pro SB2b …
+… B1 CR3r CR4  PW1glm PW1kimi PW1pro SB2b …
```

Not the implementer's: `pkgs/evidence/tasks.py` derives the queue from
`git log --format=%s`, so the commit whose subject lands CR2b changes the
derivation the moment it exists. The plan's acceptance (`unit`, `lint`) is green.
Tree restored (`git checkout -- docs/OPERATIONS.md`), `git status --porcelain`
empty.

### Timing (item 5)

Wall time of the whole hook process including the ~23 ms harness baseline; five
calls each, median reported.

| command | CR2b median | og5's figure | budget |
|---|---|---|---|
| `git status` (baseline) | 23 ms | 19 ms | — |
| **og5 test 53: `ls <200 × docs/aN/bN.md>`** | **102 ms** (100–104) | 64 ms | **< 300 ms — met** |
| `ls <200 × .claude/aN/bN>` | **104 ms** (103–105) | — | met |
| `rm <200 × .claude/aN/bN>` | **103 ms** (102–103) | — | met |
| `ls <200 × link-to-override>` (all symlinks) | **602 ms** (598–604) | 296 ms | **over — MINOR-6** |

Bats test 53 (the suite's own `$EPOCHREALTIME` median-of-three) passes. The
path-token cost is 1.6× og5's because the guard now makes two full per-token
`canon_path` scans (plan rule then override rule) instead of one; the symlink
worst case doubles for the same reason, from og5's "at the line" 296 ms to
602 ms. Not the plan's acceptance case and far under the hook's 10 s timeout,
but the runbook's unqualified sentence is now wrong for it.

## Red before green

The branch's base (`09d7cfc`, main) carries **no** override rule — 723 lines, no
`override_verdict` — so the honest red against the base is all seventeen new
override tests. The brief asks for the red against **CR2's** guard, which is the
stricter test.

Method: `git -C /home/dalhaka/factory/ws/cr8/CR2 show task/CR2:tools/orchestrator-guard.sh`
(890 lines) copied over the clone's guard, CR2b's tests kept; tree asserted
changed (`git diff --numstat` → `57 161 tools/orchestrator-guard.sh`); bats run;
restored; re-run green.

```
1..70
not ok 59 bash: the delete family naming .claude or an ancestor of the override denies
not ok 61 bash: git clean/checkout/restore naming .claude or bare denies
not ok 62 bash: find .claude -delete denying the override
not ok 63 bash: dd of= the override denies (the of= value is admitted into the scan)
not ok 64 bash: python removal spellings naming the override deny
```

Exactly the four CR2 MAJORs (directory-level delete family, `git clean`/
`checkout`/`restore`, `find -delete`, `dd of=`, python removals), five tests. The
three tests that pin CR2's *unpinned* behaviours — 65 (`cd` rebase), 66 (payload
`cwd`), 67 (symlink) — correctly pass on CR2's guard: they are new pins of
existing behaviour (cr8 MINOR-1/2/3), not new behaviour. No inflation. After
`git checkout --`, `git status --porcelain` empty and 70/70 green.

## Mutation table

Each mutation applied to `tools/orchestrator-guard.sh` in the clone, the tree
asserted changed (`git diff --numstat` printed per row), the full bats file run,
then reverted; `git status --porcelain` empty after every batch
(`ALL REVERTED`). Scripts: `…/scratchpad/mutate.py`, `runmut.sh`.

### The plan's / brief's ten

| # | mutation | numstat | fails | killed by |
|---|---|---|---|---|
| **M-A** | the override entry removed from `PROTECTED_PATHS` (`:99`) | 0+/1− | **9** | 54 59 61 62 63 64 65 66 67 |
| **M-B** | the ancestor rule limited to the plans dir (override call at `:730` off) | 1+/1− | **4** | 59 61 62 64 |
| **M-C** | `dd of=` not admitted (`:725`) | 1+/1− | **1** | 63 |
| **M-D** | the python arm without `os.remove`/`os.unlink`/`unlink(` (`:859`) | 1+/1− | **1** | 64 |
| **M-E** | the `cd`/`cwd` rebase off for the override (`:707-717`) | 1+/11− | **2** | 65 66 |
| **M-F** | the symlink resolution off (`canon_path:387-391`) | 1+/5− | **2** | 35 67 |
| **M-G** | `OVERRIDE_REASON` changed to `"nope"` (`:111`) | 1+/1− | **13** | 54 56 57 58 59 61 62 63 64 65 66 67 68 — **the reason text is pinned** |
| **M-H** | the ancestor rule off for the plans dir (og5's M-B; call at `:491`) | 1+/1− | **1** | 44 |
| **M-I** | `clean` dropped from the override git arm (`:821`) | 1+/1− | **1** | 61 |
| **M-J** | the Edit/Write path rule without the override (`:960`) | 1+/1− | **4** | 56 57 58 68 |

Ten of ten die, as the plan demands.

### og5's table, re-run

| # | mutation | numstat | fails | killed by | vs og5 |
|---|---|---|---|---|---|
| og5-M-A | `mv` removed from the plan operand writers (`:519`) | 1+/1− | 3 | 16 43 44 | same |
| og5-M-B | `is_protected_dir_or_ancestor` → `return 1` (shared) | 1+/0− | **6** | 44 59 60 61 62 64 | wider (shared fn) |
| og5-M-C | plan-rule `cd`/`cwd` rebase off | 1+/11− | 1 | 46 | same |
| og5-M-D | `-i*`/`--in-place*` detection off (`:508`) | 0+/1− | 2 | 16 47 | same |
| og5-M-E | lexical normaliser → `realpath -m` per token | 5+/7− | 1 | 53 | same |
| og5-M-F/G | quote stripping back to a space (`:139-141`) | 3+/3− | 1 | 52 | same |
| og5-M-H | `>\|` removed from the redirect folds (`:156`) | 0+/1− | 1 | 48 | same |
| og5-M-I | `pushd` dropped from the plan rebase verbs (`:475`) | 1+/1− | **0** | **SURVIVES** | same (og5 MINOR-3) |
| og4-M1 | `\n` dropped from `normalise_command` (`:138`) | 0+/1− | 2 | 20 22 | same |
| og4-M3 | basename rule off (`:202`) | 1+/1− | 1 | 9 | same |
| og4-M4 | `plan_write_verdict` returns immediately | 1+/0− | 10 | 16 17 18 22 43 44 45 46 47 48 | same |
| og4-M5 | value-skip list neutered in `git_verdict` (`:212-214`) | 0+/3− | 2 | 7 9 | same |

Same or better everywhere; the one survivor is og5's own known one.

### cr8's table, re-run — the two survivors now die

| # | mutation | numstat | fails | killed by | vs cr8 |
|---|---|---|---|---|---|
| cr8-M-A | `override_verdict` returns immediately | 1+/0− | 9 | 54 59 61 62 63 64 65 66 67 | cr8: 1 |
| cr8-M-A2 | the `override_verdict` call unwired (`:313`) | 1+/1− | 9 | same list | cr8: 1 |
| cr8-M-B | = M-J | 1+/1− | 4 | 56 57 58 68 | cr8: 3 |
| cr8-M-C | = M-G | 1+/1− | 13 | — | cr8: 4 |
| cr8-M-D | `rm`/`mv` dropped from the override delete family (`:755`) | 1+/1− | 5 | 54 59 65 66 67 | cr8: 1 |
| cr8-M-E | the override path pointed at a different filename (`:99`) | 1+/1− | 6 | 54 59 63 65 66 67 | cr8: 1 |
| **cr8-M2** | the override token scan truncated to the first token (`:723`) | 1+/1− | **9** | 54 59 61 62 63 64 65 66 67 | **cr8: SURVIVED → now dies** |
| **cr8-M-cd** | = M-E, the `cd`/`cwd` rebase off | 1+/11− | **2** | 65 66 | **cr8: SURVIVED → now dies** |

cr8 MINOR-1 (no-command-position unpinned), MINOR-2 (`cd`/`cwd` unpinned) and
MINOR-3 (symlink unpinned, killed by M-F) are all now pinned.

### Extra probes of my own

| # | mutation | numstat | fails | reading |
|---|---|---|---|---|
| **X1** | the `'docs/superpowers/plans\|dir'` entry deleted from `PROTECTED_PATHS` | 0+/1− | **0** | the `dir` entry is never read — MINOR-1 |
| X2 | the bare-path `git clean/checkout/restore` arm deleted (`:830-845`) | 0+/16− | 1 | 61 — pinned |
| X3 | the override redirect loop deleted (`:883-892`) | 0+/10− | 1 | 54 — pinned |
| X4 | `touch` dropped from the override file-level writers (`:762`) | 1+/1− | 1 | 54 — pinned |

## Findings

### MAJOR-1 — `rm -rf .claude/*` (and every other glob spelling) still ALLOWS

`tools/orchestrator-guard.sh:722-733` — the override token scan — has no
counterpart to the plan rule's raw-text fallback at `:497-499`. A glob token is
canonicalised literally (`read -a` never expands it, by design), so it matches
neither the exact override path nor `is_protected_dir_or_ancestor`, whose `case`
patterns are quoted and therefore literal (`:412-415`):

```bash
  case "$dir" in
    "$p" | "$p"/*) : ;;
    *) return 1 ;;
  esac
```

Isolated against the fixture by sourcing the guard and calling its own helpers:

```
token .claude/*               -> canon <proj>/.claude/*                ancestor=no
token .claude                 -> canon <proj>/.claude                  ancestor=YES
token .claude/ritual*         -> canon <proj>/.claude/ritual*          ancestor=no
token .claude/ritual-override -> canon <proj>/.claude/ritual-override  ancestor=no
```

Measured ALLOW on this tree (each its own payload, `cwd=<proj>`):

```
rm -rf .claude/*                 -> ALLOW
rm -rf .claude/*/                -> ALLOW
rm -rf <proj>/.claude/*          -> ALLOW
mv .claude/* /tmp/               -> ALLOW
shred .claude/*                  -> ALLOW
rm -rf .claude/ritual*           -> ALLOW
rm .claude/[r]itual-override     -> ALLOW
rm -rf .claude/?itual-override   -> ALLOW
```

`.claude/ritual-override` is not a dotfile, so `.claude/*` expands over it: each
of these deletes the operator's file. `rm -rf .claude/*` is the row the CR2
review printed in bold as a **HOLE**, and Step 1 opens "every spelling of the
review's table as a DENY case".

The asymmetry is what makes it a MAJOR rather than a scope question. The same
spelling on the plans side denies, because the plan rule keeps a raw-text
fallback the override rule was not given:

```
rm -rf docs/superpowers/plans/*   -> DENY   (plan rule)
rm docs/superpowers/plans/*.md    -> DENY   (plan rule)
rm -rf .claude/*                  -> ALLOW
```

So `docs/runbooks/session.md:128-131` ("protected the same way the plans
*directory* is") and the commit body ("directory-level removals … the delete
family") both over-claim. The fix is one `case` beside `:733`, in the shape the
plan rule already uses — e.g.
`case "$raw" in *.claude/*|*.claude\ *|*.claude) dir_ancestor_seen=1 ;; esac`
guarded to project-relative spellings — plus a DENY row for `rm -rf .claude/*`
and `mv .claude/* /tmp/` in test 59.

### MINOR-1 — `PROTECTED_PATHS` is read by one rule only; the `dir` entry is dead

`tools/orchestrator-guard.sh:97-100`, read only at `:696-704` and only for
`kind = file` (`:699`), with a `break` at `:703` that stops after the first such
entry. `plan_write_verdict` still hardcodes the plans path (`:433`, `:467`) and
the Edit/Write arm hardcodes the override (`:960`). Mutation X1 deletes the
`'docs/superpowers/plans|dir'` line and kills **zero** of 70 tests. The contract
says "a function over a PROTECTED list of `(path, kind)` entries"; what landed is
a shared *function* (which is the load-bearing half, and it works) plus a list
that only one of its two callers consults.

### MINOR-2 — a pathless `git clean`/`checkout`/`restore` denies even when it deletes nothing

`tools/orchestrator-guard.sh:830-846`. The arm cannot distinguish a dry run from
a destructive one. Measured, new relative to main:

```
git clean -n     -> DENY   (a preview; deletes nothing)
git clean -nd    -> DENY
git clean        -> DENY   (no -f: git refuses to do anything anyway)
git checkout     -> DENY   (prints status)
git checkout -   -> DENY   (switch to the previous branch)
git restore      -> DENY   (git errors: "you must specify path(s)")
echo 'git checkout' -> DENY  (prose)
```

Correctly still allowed: `git checkout main`, `git checkout -b task/X`,
`git restore --staged docs/OPERATIONS.md`, and every documented recipe. Accepted
for a deny-only guard — but nothing in the runbook says a `git clean -n` will be
refused, and an agent that hits it has no hint that adding a pathspec is the way
through.

### MINOR-3 — a commit message that names `.claude` beside a delete word is refused

Measured, new relative to main:

```
git commit -q -m 'guard: rm -rf .claude no longer allowed'   -> DENY (override)
git commit -q -m 'docs: … removes .claude/ritual-override …' -> allow
```

The first denies because the prose supplies both a `.claude` token
(→ `dir_ancestor_seen`) and an `rm` token (the delete family). The documented
commit recipe is `nix develop -c git commit -q -F <file>`, which is unaffected
(measured allow), so this is not a MAJOR — but this repo's commit subjects
routinely discuss `rm`, `mv` and `.claude`, and the accepted-over-denial
paragraph of the runbook does not name this case.

### MINOR-4 — `git stash -u` removes the untracked override and allows

`tools/orchestrator-guard.sh:820-821` lists `clean | checkout | restore`. `stash`
is not there, so `git stash -u` and `git stash -u .claude` allow. `git stash -u`
stashes untracked files — the override is untracked and not ignored — so the file
disappears from the worktree. Out of the plan's contract (which enumerates the
same three verbs), and og5 recorded the same gap on the plans side as its
MINOR-1; recorded so it is not lost.

### MINOR-5 — the runbook does not say how the operator lifts the guard

`docs/runbooks/session.md:128-145`. The brief's item 6 asks the two sentences to
name "how the operator lifts the guard". They do not, and neither does anything
else in the file (`grep -i 'lift|disable'` → nothing). The new paragraph also
names only the *non*-over-denial (the `.claude/worktrees/x` sibling) and not the
two over-denials this rule introduces (MINOR-2, MINOR-3). Everything it does
assert I verified against the implementation and it is accurate.

### MINOR-6 — the runbook's timing sentence is asserted, and now false for the symlink case

`docs/runbooks/session.md:157-159`: "a 200-token command stays under the
<300 ms per-call budget". Measured on this tree: 102 ms for 200 path tokens
(og5: 64 ms), **602 ms** for 200 symlink tokens (og5: 296 ms). The doubling is
the direct cost of the second full per-token scan the override rule adds; each
symlink token now forks `realpath` once per rule per base. og5's MINOR-10 asked
for the number rather than the property; it is still the property, and the
property no longer holds in the worst case. Suggested: "a 200-path-token command
measures 102 ms on `core` (budget: 300 ms); a command of 200 symlink tokens costs
~600 ms".

### MINOR-7 — `chmod` and `tar -C` are outside both rules

`chmod 000 .claude/ritual-override` and `tar -C .claude -xf /tmp/a.tar` allow.
Neither is a content write in the sense the contract defines and the plan does
not name them; the second is another directory-level clobber. Recorded as the
enumeration-reflex note og4/og5 have raised at every gate on this line
(`patch`, `awk -i inplace`, `ex`, `sponge` remain allowed on the plans side too).

### NOTE — the accepted over-denials and the reads all behave

`rm -rf .` and `find . -name ritual-override -exec rm {} +` deny by the **plan**
rule (`.` is a plans ancestor), not the override rule; tests 60's assertion is
`denied` only, not the reason, which is the right call. Reads are clean:
`cat`, `ls -la .claude`, `stat`, `git status`, `test -f`,
`cp .claude/ritual-override /tmp/y`, `git log`, `git diff --stat` all allow. The
sibling `rm -rf .claude/worktrees/x` allows, exactly as the runbook promises.

### NOTE — cr8's MINOR-4 and MINOR-5 are fixed

The garbled comment ("touch/opera/bewriters") is gone, and the unused `orig`
local is now used (`:722`, `:728`). shellcheck rc 0.

## Verdict

**REJECTED** — one MAJOR.

This is a good round that stops one spelling short. The four CR2 MAJORs are
genuinely fixed and verified against a fixture rather than against the suite:
`rm -rf .claude`, `mv .claude .claude-old`, `rmdir .claude`, a bare
`git clean -fd`, `git checkout -- .claude`, `git restore .claude`,
`find .claude … -delete`, `dd if=/dev/null of=…`, and every python/perl removal
spelling all deny, in relative, absolute, `cd`-rebased, payload-`cwd`-rebased and
symlinked form. The directory/ancestor logic really is one shared function with
two callers, proved by a single mutation killing tests on both sides. Ten of ten
demanded mutations die, cr8's two survivors now die, og5's whole table reproduces
with only its own known survivor, there is no plans-dir regression across 135
rows, every documented recipe allows, and the commit conventions are clean:
one commit, byte-identical subject, both trailers, three files inside `touches`,
no board commit.

What fails is the review's table, one row of it: `rm -rf .claude/*` — a glob, an
everyday idiom, printed in bold as a HOLE by the gate this task exists to answer —
still ALLOWS, along with `mv .claude/* /tmp/`, `shred .claude/*` and
`rm -rf .claude/ritual*`. The same spelling denies on the plans side, because the
plan rule kept a raw-text fallback the override rule was not given. Until that
one `case` is carried across, the runbook's "protected the same way the plans
directory is" is not true and neither is the commit body's claim about
directory-level removals.

A re-plan should be XS: one raw-text fallback in `override_verdict` beside
`:733`, two DENY rows in test 59 (`rm -rf .claude/*`, `mv .claude/* /tmp/`), and
— cheaply, in the same commit — MINOR-1's `PROTECTED_PATHS` wiring so the `dir`
entry is actually read (X1 must then kill a test), plus the two runbook sentences
MINOR-2/3/5/6 ask for. At integration the board's queue block is regenerated by
whatever lands next; `7fd7da1` stands alone for `unit` and `lint`.
