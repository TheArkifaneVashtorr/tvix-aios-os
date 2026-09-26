# Opus gate — seat run cr18, task CR2r2 — REJECTED

## Summary

One commit (`4bc1b09`) on base `214398a` (main), branch `task/CR2r2` in
`/home/dalhaka/factory/ws/cr18/CR2r2`. Reviewed in a fresh clone at
`…/scratchpad/gate-cr18-CR2r2`; nothing under `/home/dalhaka/factory` was
modified, and the live repo's `.claude/ritual-override` was never touched — every
guard run drove a throwaway fixture at `…/scratchpad/fix/proj`.

Commit conventions are clean. **One** commit; subject byte-identical to the plan
line at `docs/superpowers/plans/2026-09-05-context-reset-ritual.md:222` (`cmp` →
identical, md5 `01f0737e5da0edc2d7d640313ec46ac4` on both); both trailers
(`Generated-By: dsh … factory run cr18`, `Co-Authored-By: Claude Fable 5.1`);
three files — `tools/orchestrator-guard.sh` (+784/−135),
`tests/unit/91-orchestrator-guard.bats` (+593/−6), `docs/runbooks/session.md`
(+68/−3) — all inside `touches`; no board commit; `docs/MAP.md` identical to a
fresh regeneration.

**The MAJOR of cr17 is genuinely fixed.** All sixteen rows of that review's two
tables that name a protected write now behave, the four allow-controls hold, and
the four folded minors land:

```
sed 's|a|b|' -i docs/superpowers/plans/x.md   DENY  (CR2rb: ALLOW, main: DENY)
perl -pe 's|a|b|' -i <plan>                   DENY  (CR2rb: ALLOW)
sed 's/a&b/c/' -i <plan>, sed 's/a;b/c/' …    DENY  (CR2rb: ALLOW)
find <plans-dir> -name 'a|b' -delete          DENY  (CR2rb: ALLOW)
sed 's|a|b|' -i .claude/ritual-override       DENY  (CR2rb: ALLOW)
tar 'a|b' -x -C .claude ; cpio 'a|b' -idm     DENY  (CR2rb: ALLOW)
echo 'a;b' && rm /tmp/x ; echo 'a|b' | cat    allow (correct)
git commit -m 'a' -m 'b: rm -rf .claude'      allow (CR2rb: DENY — MINOR-2 closed)
git commit -am '…' / -m'…' / --message='…'    allow (CR2rb: DENY — MINOR-3 closed)
```

Checks are green — shellcheck rc 0, bats **96/96**, `unit` **395/395**, `lint`
pass, treefmt 0 changed. 233 historic rows reproduce with **0** mismatches and
**no** verdict moved from DENY on main to ALLOW anywhere in that corpus. All 50
documented recipes ALLOW. Six of the ten new tests go red on CR2rb. All seven
CR2r2 mutations and all seventeen re-applied cr15/cr17 mutations behave as
demanded (M-F excepted, which the matrix asked me only to characterise).

It is rejected on **one MAJOR**, introduced by the *timing* fix rather than by
the quote fix:

```
                                              main   CR2rb  CR2r2
rm -rf .claude/ritual-override &              DENY   DENY   ALLOW
rm docs/superpowers/plans/x.md &              DENY   DENY   ALLOW
sed -i s/a/b/ docs/superpowers/plans/x.md &   DENY   DENY   ALLOW
git clean -fd &                               DENY   DENY   ALLOW
touch .claude/ritual-override &               allow  DENY   ALLOW
```

A command whose **last byte** is an unquoted `&`, `|` or `>` makes
`tokenise_ctx` read `${chars[i + 1]}` one past the end of the array; under
`set -u` bash aborts the `$(write_verdict …)` subshell, `reason` comes back
empty, and *both* the plan-write arm and the override arm silently vanish. Three
of the rows above are plans-dir regressions against main. Trailing `&` is how a
command is backgrounded; this is not an evasion shape.

Method: fresh clone (`git clone -q --branch task/CR2r2 …`); the guard driven only
from extracted copies with `env CLAUDE_PROJECT_DIR=<fixture> bash <guard>` on
compact `ensure_ascii=False` payloads of the real Claude Code shape with `cwd` at
the **top level**. Fixture: a git repo with
`.claude/{ritual-override,settings.json,worktrees/x}`,
`docs/superpowers/plans/x.md`, `docs/second/plans/y.md`, `docs/notes/plans/x.md`
(decoy), `k`, `sub/`, `elsewhere/ritual-override`, `link-to-override` → the
override, `plans-link` → the plans dir, 200 `link<N>` symlinks, and
`…/fix/other/.claude/ritual-override` outside the project. Drivers:
`…/scratchpad/{mkfix.sh,drive.py,timing.py,timing2.py,mutate.py,runmut.sh,
redgreen.sh,editcheck.py}`, case files `c1.tsv`, `c2.tsv`, `c3.tsv`, `sweep.tsv`,
`recipes.tsv`. 380+ payloads, each also replayed against
`git show 214398a:tools/orchestrator-guard.sh` (main, 723 lines) and
`git show task/CR2rb:tools/orchestrator-guard.sh` (CR2rb, 1307 lines) so every
difference is attributed.

## Quotes and clauses

The restructuring is confined to `tokenise_ctx` and its emit helper.

| before (CR2rb) | after (CR2r2) |
|---|---|
| a character loop over `${s:i:1}` — a fresh substring expansion per byte, O(n²) | `s` with newlines re-encoded to `\x01`, split once by `fold -w1` into `chars[]`, then one O(n) scan (`:265-268`) |
| `_ctx_emit()` defined **inside** `tokenise_ctx` | `_ctx_emit()` and its `_ctx_*` scratch globals hoisted to file scope (`:225-242`) |
| every `;` `&` `\|` `>` `(` `)` `{` `}` and newline emitted as an operator token, quote state ignored | each arm gated on `[ -n "$inq" ]` (`:272`, `:319`): inside a quote the byte joins `_ctx_buf` and marks the token quoted |
| the `-m` skip broke after the first `-m` | the walk continues to the end of the argument list; the glued arm `--message=*\|-m*` skips a quoted glued token and the quoted run after it (`:751-776`) |
| the extract-with-no-destination rule already judged the base at the verb | unchanged; the project-root case is now *documented* as an accepted over-denial |

The quote fix is exactly the shape the cr17 review asked for, and the
tokeniser's header comment (`:209-211`) now matches the code. What it does **not**
survive is the array rewrite: the operator arms keep a one-byte lookahead
(`&&`, `||`, `>>`, `>|`) and that lookahead is no longer a safe substring
expansion.

```bash
# tools/orchestrator-guard.sh:277-281
          case "$c" in
            '&') [ "${chars[i + 1]}" = '&' ] && i=$((i + 1)) ;;
            '|') [ "${chars[i + 1]}" = '|' ] && i=$((i + 1)) ;;
            '>') case "${chars[i + 1]}" in '|' | '>') i=$((i + 1)) ;; esac ;;
          esac
```

`${s:i+1:1}` yields the empty string past the end; `${chars[i+1]}` under `set -u`
(`:85`) is a fatal *unbound variable*. Observed, verbatim, on
`rm -rf .claude/ritual-override &`:

```
orchestrator-guard.sh: line 278: chars[i + 1]: unbound variable
```

Verdict: stdout empty → **allow**. `;`, `(`, `)`, `{`, `}` have no lookahead and
still deny (`rm -rf .claude/ritual-override ;` → DENY), and the `git`, `sudo`,
`nixos-rebuild`, `systemctl` and protected-prefix rules survive because they run
outside that subshell (`git push &` → DENY, `sudo rm -rf .claude &` → DENY,
`cp k /var/lib/secrets/x &` → DENY).

## Rule behaviour

Fixture `<proj>` = `…/scratchpad/fix/proj`; payload `cwd` = `<proj>` unless noted.

### Item 1 — quoted operators (the cr17 tables), 16 + 4 + 5 rows

| spelling | main | CR2rb | CR2r2 | matrix |
|---|---|---|---|---|
| `sed 's\|a\|b\|' -i <plan>` | DENY | ALLOW | **DENY** | ✓ |
| `sed -e 's\|/old/path\|/new/path\|' -i <plan>` | DENY | ALLOW | **DENY** | ✓ |
| `sed -e 's/a/b/' -e 's\|c\|d\|' -i <plan>` | DENY | ALLOW | **DENY** | ✓ |
| `perl -pe 's\|a\|b\|' -i <plan>` | DENY | ALLOW | **DENY** | ✓ |
| `sed 's/a;b/c/' -i <plan>` | DENY | ALLOW | **DENY** | ✓ |
| `sed 's/a&b/c/' -i <plan>` | DENY | ALLOW | **DENY** | ✓ |
| `sed -e 's/a/⏎b/' -i <plan>` | DENY | ALLOW | **DENY** | ✓ |
| `perl -pe 's/a/⏎b/' -i <plan>` | DENY | ALLOW | **DENY** | ✓ |
| `find <plans-dir> -name 'a\|b' -delete` | DENY | ALLOW | **DENY** | ✓ |
| `sed 's\|a\|b\|' -i .claude/ritual-override` | allow¹ | ALLOW | **DENY** | ✓ |
| `sed -e 's/a\|b/c/' -i .claude/ritual-override` | allow¹ | ALLOW | **DENY** | ✓ |
| `find .claude -name 'a\|b' -delete` | allow¹ | ALLOW | **DENY** | ✓ |
| `tar 'a\|b' -x -C .claude` | allow¹ | ALLOW | **DENY** | ✓ |
| `cpio 'a\|b' -idm` | allow¹ | ALLOW | **DENY** | ✓ |
| **`git clean 'a\|b' -f`** | allow¹ | ALLOW | allow | ✗ still allows — MINOR-4 |
| **`git stash 'a\|b' -u`** | allow¹ | ALLOW | allow | ✗ still allows — MINOR-4 |
| `sed -i 's\|a\|b\|' <plan>` / `sed 's\|a\|b\|' -i <plan>` | DENY | — | **DENY** ×2 | ✓ order irrelevant |
| `sed -i 's\|a\|b\|' <override>` / `sed 's\|a\|b\|' -i <override>` | — | — | **DENY** ×2 | ✓ |
| `echo 'a;b' && rm /tmp/x` | allow | allow | allow | ✓ |
| `echo 'a\|b' \| cat` | allow | allow | allow | ✓ |
| `printf '%s⏎' 'x;y'` | allow | allow | allow | ✓ |
| `git commit -q -m 'guard: rm x; touch y \| z'` | allow | allow | allow | ✓ |

¹ main has no override rule at all.

Boundaries:

| spelling | CR2r2 | reading |
|---|---|---|
| `echo a; rm /tmp/x` | allow | an unquoted `;` still splits |
| `ls; git stash -u` | **DENY** | the flag arms its own clause |
| `rm -f result && git clean` / `ls -a && git stash` | allow | clause-local flags kept |
| `sed -n '1,30p' <plan> \| grep -i CR2` | allow | og5's rule-4 over-denial stays withdrawn |
| `echo a\;b` | allow | escaped operator, nothing protected named |
| `rm -rf a\;b .claude/ritual-override` | **DENY** | escaped operator does not hide the path |
| `sed 's\|a\|b -i .claude/ritual-override` (unterminated) | **DENY** | no crash, no allow |
| `rm -rf '.claude/ritual-override` (unterminated) | **DENY** | same |
| `rm -rf "docs/superpowers/plans/x.md` (unterminated) | **DENY** | same |
| **`rm -rf .claude/ritual-override &`** | **allow** | **MAJOR-1** |
| `rm -rf .claude/ritual-override ;` / `&&` / `\|\|` / `>>` | DENY ×4 | the two-byte forms are safe |

### Item 2 — extracts (23 rows, 0 deviations)

| spelling | cwd | main | CR2r2 |
|---|---|---|---|
| `tar -xf /tmp/a.tar`, `tar -xzf …`, `unzip …`, `cpio -idm` | `<proj>` | allow | **DENY** ×4 (documented over-denial) |
| the same four | `<proj>/.claude` | allow | **DENY** ×4 |
| `tar --extract --file /tmp/a.tar` | `<proj>/.claude` | allow | **DENY** |
| `tar -xf … -C /tmp`, `unzip -d /tmp …` | `<proj>` | allow | allow ✓ |
| `tar -xf … -C /tmp` | `<proj>/.claude` | allow | allow ✓ |
| `tar -tf …` | `<proj>` / `<proj>/.claude` / `/tmp` | allow | allow ×3 ✓ |
| `tar -xf /tmp/a.tar` | `<proj>/sub`, `/tmp` | allow | allow ×2 ✓ |
| `tar -C .claude -xf …`, `tar -xf … -C .claude`, `unzip -d .claude …` | `<proj>` | allow | **DENY** ×3 |
| `cd .claude && cpio -idm`, `cd .claude && tar -xf …` | `<proj>` | allow | **DENY** ×2 |
| `tar -x -f /tmp/a.tar && ls .claude` | `<proj>` | allow | **DENY** (the root rule, as documented) |

`docs/runbooks/session.md:171-176` names the project-root extract among the
accepted over-denials, as the contract requires.

### Item 3 — `git commit -m` (28 rows, 0 deviations)

| spelling | main | CR2rb | CR2r2 |
|---|---|---|---|
| `git commit -m 'subject' -m 'body: rm -rf .claude …'` | allow | DENY | **allow** ✓ |
| `git commit -am 'fix: rm -rf .claude …'` | allow | DENY | **allow** ✓ |
| `git commit -m'guard: rm -rf .claude …'` | allow | DENY | **allow** ✓ |
| `git commit --message='guard: rm -rf .claude …'` | allow | DENY | **allow** ✓ |
| `git commit -m'a' -m'b rm -rf .claude'` | allow | DENY | **allow** ✓ |
| `git commit -am 'x' -m 'body rm -rf .claude'` | allow | allow | allow ✓ |
| `git commit --message 'guard: …'`, `-m "x" -F k`, `-q -m '…'` | allow | allow | allow ✓ |
| `git commit -m rm .claude/ritual-override` (unquoted) | allow | DENY | **DENY** ✓ |
| `git commit -m 'x'`⏎`rm -rf .claude/ritual-override` | allow | DENY | **DENY** ✓ |
| the other nine newline spellings of the cr15/cr17 tables | — | DENY | **DENY** ×9 ✓ |
| `git commit -m 'x' ; rm -rf .claude` | allow | DENY | **DENY** ✓ |
| `git commit -m 'line one⏎line two rm -rf .claude'` | allow | allow | allow ✓ |
| `git commit -m 'plans: <plan> rewritten'` | allow | allow | allow ✓ |
| `git commit -m 'x'`⏎`git push` / `sudo rm -rf .claude` | DENY | DENY | **DENY** ✓ |

### Item 5 — the folded minors

| item | result |
|---|---|
| the raw-text fallback derived from `PROTECTED_PATHS` | pinned — test 96 adds `docs/second/plans\|dir`, whose literal appears nowhere in the guard (`grep -n 'second'` → only a comment at `:218`); **M-E** (the literal restored) kills it |
| test 82's payload | `cwd` at the **top level** (`tests/unit/91-orchestrator-guard.bats:1079`) ✓ |
| `_ctx_emit` hoisted | yes, `tools/orchestrator-guard.sh:233` at file scope ✓ — but **unpinned** (M-F kills 0 tests) |

### Item 7 — everything CR2rb established still holds

One PROTECTED list feeding all three arms (**C17-A** kills 22, **C17-B** 22,
**C17-C** 18); glob spellings (14/14 DENY, **C17-D** kills 71); the delete family
including `git stash push -u`/`save -u`/`-au`/`-ua`, `tar`/`unzip`/`cpio`,
`chmod`/`chown`/`chattr` on the file **and** on `.claude`; clause-local flags
(`rm -f result && git clean` → allow); the lift line (`ORCHESTRATOR_GUARD=off` →
stdout empty, exactly one stderr line `orchestrator-guard: lifted by
ORCHESTRATOR_GUARD=off`; the same string inside the payload → DENY); the
Edit/Write loop pin (**C17-F2** kills 85). Edit/Write/MultiEdit probes: the
override denies relative and absolute, a plan write that drops a heading denies,
an appending write allows, the decoy and an out-of-project `.claude/ritual-override`
allow, `.claude/settings.json` allows.

### Item 6 — the historic sweep

233 payloads across og4's 38 git rows, og4/og5's 56 plan-write rows, the 11 host
rows, cr12's 69 override rows, cr15's 14 glob rows and 44 narrowing/family rows:
**0 mismatches** against what those gates recorded, and **0** rows where main
DENIES and this tree allows. Every difference from main is an intended override
rule or a documented narrowing (`git clean -n` / `git checkout main` /
`git stash push` allow; `git clean -df|-xdf|-dxf`, `git stash push -u`, the eight
glob spellings and the directory `chmod` deny).

## Over-denial audit

**50 of 50** documented recipes ALLOW, identical to main on 49 and *better* than
main on one (`nix develop -c git commit -q -m "<prose naming rm, .claude and a
plan path>"`: main DENY → allow). **No documented recipe is refused.**

Over-denials carried forward, all recorded in the runbook, none a documented
recipe: the project-root extract with no `-C`/`-d` (`tar -xf /tmp/a.tar`,
`unzip`, `cpio -idm` — main allows), `rm -rf .claude/worktrees/*`,
`git checkout --`, `echo "git commit --amend"`, `rm /tmp/x && cat <plan>`.

New over-denials introduced by this commit: **none** measured.

## Timing

Median of five whole-hook calls (including the ~21 ms process baseline), host
load 3.21/3.84/3.96 with seats live; same harness, same fixture, all three trees.

| command | main | CR2rb | CR2r2 | cap | met |
|---|---|---|---|---|---|
| `git status` (baseline) | 21.4 ms | 20.4 ms | 23.0 ms | — | — |
| 200 path tokens | 62.6 ms | 141.5 ms | **95.9 ms** | 100 ms | yes, 4 ms |
| 200 `.claude` path tokens | 61.9 ms | 165.0 ms | 103.6 ms | — | (not the tested case) |
| 200 symlink tokens | 274.1 ms | 102.4 ms | **97.2 ms** | 200 ms | yes |
| `rm` × 200 symlink tokens | 293.1 ms | 101.6 ms | 89.7 ms | — | yes |

Five further rounds of the two tested commands: paths 96.0 / 96.4 / 97.5 / 97.4 /
96.2 ms, symlinks 92.0 / 92.0 / 91.5 / 94.3 / 92.6 ms (load 3.50). Both bats
timing tests (`:643` cap 100 ms, `:661` cap 200 ms) pass here. The regression
CR2rb introduced is genuinely reversed — the `fold -w1` array beats the
`${s:i:1}` loop by ~45 ms — and **M-D** (the substring form restored) makes test
53 red, so the single-pass property is pinned.

The runbook (`docs/runbooks/session.md:198-201`) states **91 ms** and **83 ms**.
I measure 96–97.5 ms and 91.5–94.3 ms on this host at this load. The path figure
is 5–7 % optimistic; the symlink figure 83 ms is byte-identical to the number the
cr17 gate flagged as carried over from CR2r (MINOR-2 below). The cap is met on
every median I took, so this is not a MAJOR — but the headroom is ~3 ms, not the
~9 ms the seat claimed, and the very similar `.claude` path variant already
measures 103.6 ms.

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| check | command | rc | result |
|---|---|---|---|
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **0** | clean |
| bats 91 | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | **0** | `1..96`, **96 ok**, no `not ok` |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **0** | `1..395`, **395/395** |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **0** | `All checks passed!`, 94 files, **0 changed** |
| pre-commit | `nix develop -c githooks/pre-commit` | **1** → **0** | treefmt clean; rc 1 only on `tasks: docs/OPERATIONS.md queue block was stale`; **rc 0** once the regenerated board is staged (the board is not in `touches`) — structural, as in every prior gate |
| MAP | `repomap.py --root . write` | — | **identical** to the committed `docs/MAP.md` |

Working tree left clean (`git status --porcelain` empty) after every experiment.

## Red before green

CR2rb's guard (`git -C /home/dalhaka/factory/ws/cr17/CR2rb show
task/CR2rb:tools/orchestrator-guard.sh`, 1307 lines) copied over the clone's
guard, CR2r2's tests kept. Tree asserted changed (`git diff --numstat` →
`89 154 tools/orchestrator-guard.sh`), bats run, restored, re-run green.

```
1..96
not ok 53 a 200-path-token command stays under 100 ms (median of five calls)
not ok 87 bash: a quoted operator does not split a clause — the nine plan spellings deny
not ok 88 bash: a quoted operator does not split a clause — the override spellings deny
not ok 89 bash: sed -i and the script-first order both deny a plan (argument order is irrelevant)
not ok 94 bash: every git commit -m argument is exempt, not only the first
not ok 95 bash: git commit glued message forms are exempt (-am, -m'…', --message='…')
```

Six of the ten new tests are red on CR2rb — the quoted-operator rows (plans and
override), the argument-order pair, the two-message case, the glued forms and the
100 ms timing cap. The other four pass on CR2rb honestly and are declared as such:
**90** and **91** are allow-controls; **92** (extract at the project root) pins the
behaviour cr17 recorded as MINOR-1 and now documents; **93** is its allow-control;
**96** (the second `dir` entry) pins a derivation CR2rb already had but nothing
tested — cr17's MINOR-5 — and **M-E** proves it now bites. After
`git checkout --`, `git status --porcelain` empty and 96/96 green. No test covers
the runbook sentences (they are prose), and **no test covers a command ending in
a bare operator** — the MAJOR below.

## Mutation table

Each mutation applied to `tools/orchestrator-guard.sh` in the clone, the tree
asserted changed (`numstat` printed per row), the full bats file run, then
reverted; `git status --porcelain` empty after every batch (`ALL REVERTED: []`).
Scripts: `…/scratchpad/{mutate.py,runmut.sh}`.

### CR2r2's seven

| # | mutation | numstat | fails | killed by |
|---|---|---|---|---|
| **M-A** | the quote test removed from the operator arms (`:272` → `if false`) | 1+/1− | **3** | 87 88 89 |
| **M-A2** | only the newline arm loses the quote test (`:319` → `if false`) | 1+/1− | **1** | 87 |
| **M-B** | the `-m` loop's `break` restored (after `:759`) | 1+/0− | **1** | 94 |
| **M-C** | extracts at the project root allowed (`base != project_canon` guard at `:997`) | 1+/1− | **2** | 88 92 |
| **M-D** | the O(n²) form restored — `c=${chars[i]}` → `c=${s:i:1}` (`:269`), CR2rb's per-byte substring re-scan | 1+/1− | **1** | **53** (the 100 ms timing test) |
| **M-E** | the raw-text plan fallback back to the literal `*superpowers/plans/*` (`:857`) | 1+/1− | **1** | 96 |
| **M-F** | `_ctx_emit` moved back inside `tokenise_ctx` | 2+/2− | **0** | **SURVIVES — unpinned** (the matrix asked only that I say so) |

### cr15's and cr17's seventeen, re-applied — all still die

| # | mutation | numstat | fails | killed by |
|---|---|---|---|---|
| C15-A | the plans entry deleted from `PROTECTED_PATHS` (`:114`) | 1+/1− | **22** | 16 17 18 22 24 25 28 30 31 33 34 35 36 43 44 45 46 47 48 80 87 89 |
| C15-B | the override entry deleted (`:115`) | 1+/1− | **22** | 55 57 58 59 60 62 63 64 65 66 67 68 69 71 72 74 78 80 82 84 88 92 |
| C15-C | the `write_verdict` list loop `break`s after the first entry (`:664`) | 1+/0− | **18** | 55 60 62 63 64 66 67 68 71 72 74 76 78 80 82 84 88 92 |
| C15-D | the glob/raw-text fallback disabled (`:837`) | 1+/1− | **1** | 71 |
| C15-E | `git stash -u`/`-a` dropped from the family (`:721`) | 1+/1− | **2** | 72 81 |
| C15-F | `tar` dropped from the extract arm (`:978`) | 1+/1− | **4** | 72 82 88 92 |
| C15-G | `git clean -n` treated like `-f` (`:720`) | 1+/1− | **1** | 73 |
| C15-H | the `-m` exemption removed (`:753`) | 1+/1− | **3** | 75 94 95 |
| C15-I | the batched `realpath` replaced by per-token resolution (`:794`) | 1+/1− | **1** | 54 |
| C15-K | the lift flag ignored entirely (`:1285`) | 1+/1− | **2** | 77 86 |
| C17-B2 | stash subcommand words taken as pathspecs (`:1145` deleted) | 1+/1− | **1** | 81 |
| C17-C2 | the extract cwd check removed (`:994`) | 1+/1− | **3** | 82 88 92 |
| C17-D2 | whole-command flag attribution restored (`clause_of[i]=0`, `:697`) | 1+/1− | **1** | 83 |
| C17-E2 | directory `chmod` not denied (`ovr_dir_seen` dropped at `:958`) | 1+/1− | **1** | 84 |
| C17-F2 | a `break` added to the Edit/Write loop in `main` (`:1340`) | 1+/0− | **1** | 85 |
| C17-G2 | the lift's stderr line removed (`:1286`) | 1+/1− | **1** | 86 |
| X-SHFMT | `canon_result` write respelled `[$i / $bi]` (`:793`) | 1+/1− | **34** | 16 17 18 22 43–48 55 60–68 71 72 74 76 78 80–82 84 87–89 92 96 |

**Twenty-three of twenty-four mutations die; M-F survives, as characterised.**

## Findings

### MAJOR-1 — a command ending in a bare `&`, `|` or `>` faults the tokeniser under `set -u`, and every protected-path rule vanishes: `rm -rf .claude/ritual-override &` ALLOWS

`tokenise_ctx` reads one byte past the end of `chars[]` when an operator is the
last character of the command (`tools/orchestrator-guard.sh:277-281`):

```bash
          case "$c" in
            '&') [ "${chars[i + 1]}" = '&' ] && i=$((i + 1)) ;;
            '|') [ "${chars[i + 1]}" = '|' ] && i=$((i + 1)) ;;
            '>') case "${chars[i + 1]}" in '|' | '>') i=$((i + 1)) ;; esac ;;
          esac
```

`set -u` is on (`:85`), and bash treats an out-of-range *array element* reference
as an unbound variable and exits the shell. `write_verdict` is called from a
command substitution (`:474`, `reason=$(write_verdict …)`), so the subshell dies,
`reason` is empty, `bash_verdict` falls through its remaining rules and the hook
exits 0 with empty stdout — an **allow**. Measured, `cwd = <proj>`, each row also
run against main and CR2rb:

```
                                                     main    CR2rb   CR2r2
rm -rf .claude/ritual-override &                     DENY    DENY    ALLOW
rm -rf .claude/ritual-override&                      DENY    DENY    ALLOW
rm -rf .claude &                                     DENY    DENY    ALLOW
rm docs/superpowers/plans/x.md &                     DENY    DENY    ALLOW
sed -i s/a/b/ docs/superpowers/plans/x.md &          DENY    DENY    ALLOW
rm -rf docs/superpowers/plans &                      DENY    DENY    ALLOW
git clean -fd &                                      DENY    DENY    ALLOW
{ rm -rf .claude/ritual-override; } &                DENY    DENY    ALLOW
rm -rf .claude/ritual-override; ls &                 DENY    DENY    ALLOW
touch .claude/ritual-override &                      allow¹  DENY    ALLOW
echo x > .claude/ritual-override &                   allow¹  DENY    ALLOW
cp k .claude/ritual-override &                       allow¹  DENY    ALLOW
tee .claude/ritual-override &                        allow¹  DENY    ALLOW
git stash -u &                                       allow¹  DENY    ALLOW
rm -rf .claude/ritual-override 1>                    DENY    DENY    ALLOW
rm -rf .claude/ritual-override >                     DENY    DENY    ALLOW
rm -rf .claude/ritual-override |                     DENY    DENY    ALLOW
```

¹ main has no override rule at all.

Four of those are **plans-dir regressions against main** (`rm <plan> &`,
`sed -i … <plan> &`, `rm -rf <plans-dir> &`, and `rm -rf .claude/ritual-override &`
counts against CR2rb's own contract). Each run leaves the bash fault on stderr:

```
orchestrator-guard.sh: line 278: chars[i + 1]: unbound variable
```

so the guard is *raising*, contradicting the file's own contract at `:75-77`
("an internal error prints a one-line warning to stderr and allows") — this is
not a `warn` line and the rule does not merely degrade, it disappears without any
guard-authored message.

CR2rb did not have this: it used `${s:i+1:1}`, which yields the empty string past
the end. The regression is a side effect of the `fold -w1` array rewrite that
bought the timing fix. `;`, `(`, `)`, `{`, `}` are unaffected (no lookahead), and
the pre-`write_verdict` rules (git, sudo, nixos-rebuild, systemctl, the
`/var/lib/*` prefixes) still fire, which is why `git push &` and
`sudo rm -rf .claude &` still deny — masking how wide the hole is.

Fix shape: bound the three lookaheads, e.g. `[ $((i + 1)) -lt "$n" ] &&
[ "${chars[i + 1]}" = '&' ]`, or read them as `${chars[i + 1]-}`. Red tests
first: every row above, plus an allow-control (`nix build … &`), plus a
`;`/`)`/`}`-terminated control that must keep denying.

### MINOR-1 — the seat ended with prose and no `FACTORY-RESULT` block

The driver reports the run failed while the commit exists and is complete. Noted
as the process deviation the gate brief asked me to record; it did not affect any
verdict above.

### MINOR-2 — the runbook's timing figures understate this host, and the symlink figure is unchanged from the number cr17 flagged

`docs/runbooks/session.md:198-201`:

```
single `realpath` call, so a 200-path-token command measures 91 ms and a
200-symlink-token command 83 ms (median of five, `$EPOCHREALTIME` in
tests/unit/91-orchestrator-guard.bats) — both under the 100 ms / 200 ms
caps
```

Measured here, median of five, six independent rounds: paths 95.9–97.5 ms,
symlinks 91.5–97.2 ms (load 3.2–3.5). The plan's item 4 asks for "the measured
numbers of THIS tree, never a previous round's"; **83 ms** is byte-identical to
the CR2r figure the cr17 gate raised as MINOR-4, and I could not reproduce it on
any run. The seat's claim of "median 91 ms with ~9 ms headroom" is not
reproducible here — the headroom is ~3 ms. The cap is met, so this is a minor.

### MINOR-3 — `_ctx_emit`'s hoist is unpinned

The hoist itself is done (`:225-242`, file scope, with the `_ctx_*` scratch
globals beside it), which is exactly what the contract asked. But **M-F** —
moving the definition back inside `tokenise_ctx` — changes the tree (2+/2−) and
kills **zero** of 96 tests. The plan allowed "say whether pinned"; it is not.

### MINOR-4 — two rows of the cr17 override table still ALLOW

```
git clean 'a|b' -f     allow   (main allow, CR2rb ALLOW)
git stash 'a|b' -u     allow   (main allow, CR2rb ALLOW)
```

Test 91 asserts these as **allow** on purpose: the quoted token is now a single
pathspec, and the CR2r narrowing says a `git clean -f`/`git stash -u` limited to a
pathspec that is not protected does not touch the override. That is defensible —
neither command can remove `.claude/ritual-override` — but the plan's item 1 says
"every row of the review's two tables → DENY", and the runbook does not record the
carve-out. Judgement, not a hole: no protected path is destroyed by either.

### MINOR-5 — four locals leak into the global namespace in `write_verdict`

`tools/orchestrator-guard.sh:876-879` assigns `dq`, `sq`, `dqd`, `sqd`, none of
which appear in the function's `local` list (`:627-639`):

```bash
      dq="\"${rel}\""     # ".claude/ritual-override"
      sq="'${rel}'"       # '.claude/ritual-override'
      dqd="\"${rel%/*}\"" # ".claude"
      sqd="'${rel%/*}'"   # '.claude'
```

`normalise_command` declares `local dq sq bt` so it is shadowed correctly today,
but the names now exist globally after the first `write_verdict` call. Cosmetic;
shellcheck is clean.

### MINOR-6 — one older test still nests `cwd` inside `tool_input`

Test 82's payload was reshaped as the contract asked, but
`tests/unit/91-orchestrator-guard.bats:577` ("the payload cwd rebases relative
plan-write paths") still writes `{"tool_input":{"command":…,"cwd":…}}`. It passes
only because `json_string` scans the whole payload for `"cwd"`. Same shape defect
as cr17's MINOR-6, one test over.

### MINOR-7 — a quoted newline becomes a space *inside* the token, not a newline

`tools/orchestrator-guard.sh:318-322`:

```bash
      $'\x01')
        if [ -n "$inq" ]; then
          _ctx_buf+=' '
          _ctx_bufq=1
```

The contract says a quoted newline is "an ordinary character of that one token";
the implementation substitutes a space, so the token text differs from the
argument a shell would pass. I found no verdict that turns on it (a token holding
a space matches no path and no verb either way), and the `-m` exemption keys on
`quoted[]`, not on the text. Recorded, not a defect.

### NOTE — the implementer's claims, checked

| claim | verdict |
|---|---|
| "96/96 guard tests" | **true** — `1..96`, no `not ok` |
| "full unit green" | **true** — `1..395`, 395/395 |
| "pre-commit clean" | **partial** — treefmt/lint clean and 0 changed; `githooks/pre-commit` exits **1** on the derived board queue block until `docs/OPERATIONS.md` is staged, then 0. Structural, as in every prior gate |
| "path-token timing median 91 ms with ~9 ms headroom" | **not reproduced** — 95.9–97.5 ms here (six rounds, load 3.2–3.5), ~3 ms headroom; the cap is still met |
| "the O(n²) regression mutation caught" | **true** — restoring `c=${s:i:1}` makes test 53 red |
| "_ctx_emit hoisted" | **true** at `:233` — but unpinned (M-F kills 0) |
| "the raw-text fallback derived from PROTECTED_PATHS" | **true and pinned** — test 96 uses a second `dir` entry whose literal is nowhere in the guard; M-E kills it |
| the cr17 MAJOR fixed | **true** — all sixteen protected-write rows of the two tables deny (the two `'a\|b'`-pathspec rows excepted by design), both allow-controls hold |

## Verdict

**REJECTED** — one MAJOR.

CR2r2 does what it was re-planned for. Quotes now bound clauses: the nine plans
spellings and the five override spellings of the cr17 tables deny again,
`sed 's|a|b|' -i <plan>` and `sed -i 's|a|b|' <plan>` behave identically, and the
allow-controls (`echo 'a;b' && rm /tmp/x`, `echo 'a|b' | cat`, a commit message
carrying `;` and `|`) stay allowed. The remaining minors land: every `-m`
argument is exempt including `-am`, `-m'…'` and `--message='…'`; the
extract-at-the-project-root over-denial is documented in the runbook; the
raw-text fallback's derivation is pinned by a second `dir` entry whose literal
appears nowhere in the guard; test 82 carries `cwd` at the top level; `_ctx_emit`
is hoisted. The timing regression is genuinely reversed — 141.5 ms → 95.9 ms on
the 200-path-token command — and pinned by a mutation. 233 historic rows
reproduce with zero mismatches, 50 of 50 recipes allow, no verdict moved from
DENY on main to ALLOW anywhere in that corpus, 23 of 24 mutations die, and the
commit conventions are clean.

What fails is the mechanism the timing fix was built on. Replacing CR2rb's
`${s:i+1:1}` lookahead with `${chars[i + 1]}` over a `fold -w1` array made the
one-byte operator lookahead a fatal `set -u` fault whenever the operator is the
command's last character. `write_verdict` runs in a command substitution, so the
fault is silent: both protected-path arms disappear and the hook allows.
`rm -rf .claude/ritual-override &` allows. So do `rm <plan> &`,
`sed -i s/a/b/ <plan> &`, `rm -rf <plans-dir> &`, `git clean -fd &`,
`touch <override> &`, `echo x > <override> &`, `cp k <override> &` and the `|`
and `>` terminations. Four are writes or deletions of a plan path that **main
refuses today**. Backgrounding a command with a trailing `&` is ordinary usage,
not a probe, and nothing in the 96-test suite covers a command that ends in an
operator.

A re-plan is XS and three lines wide: bound each lookahead at
`tools/orchestrator-guard.sh:277-281` (`[ $((i + 1)) -lt "$n" ] && …`, or
`${chars[i + 1]-}`), with red tests first over the seventeen rows above plus a
`;`/`)`/`}`-terminated control and an allow-control ending in `&`. While the file
is open, fold in MINOR-2 (re-measure both runbook figures on the tree, including
the symlink one), MINOR-3 (a test that fails when `_ctx_emit` moves back inside),
MINOR-5 (add `dq sq dqd sqd` to the `local` list) and MINOR-6 (the second nested
`cwd` payload). Everything else in CR2r2 should be kept as it is.
