---
reviewer: opus
majors: 4
minors: 3
---
# Opus gate — seat run cr20, task CR2r3 — REJECTED

## Summary

One commit (`b073863`) on base `5500e06` (main), branch `task/CR2r3` in
`/home/dalhaka/factory/ws/cr20/CR2r3`. Reviewed in a fresh clone at
`…/scratchpad/gate-cr20-CR2r3`; nothing under `/home/dalhaka/factory` was
modified, the live repo's `.claude/ritual-override` was never touched, and every
guard run drove a throwaway fixture at `…/scratchpad/fix/proj`.

**The cr19 MAJOR is fixed, and the refactor is real.** cr2r2b called guard
functions inside **24** command substitutions (`json_string` 7, `json_unescape`
6, `apply_edit` 2, and one each for `write_verdict`, `resolve_path`,
`pad_operators`, `normalise_command`, `multiedit_after`, `missing_headings`,
`git_verdict`, `bash_verdict`). Head has **zero**: my own extraction of every
`$(` in the file finds only `printf`, `sed`, `realpath`, `cat` and `comm`
callees, and all eight fault injections that cr19 asked for now DENY with
`guard fault`, exit 0 and one guard-authored stderr line. Removing the `EXIT`
trap makes all eight allow again, so the trap is demonstrably the mechanism. The
trap is installed as `main`'s first statement, `trap -p EXIT` after sourcing
prints nothing, and the vanishing-TAP defect of cr19's MINOR-3 is gone (a
mutation of a sourcing test now prints a named `not ok`). Missing evidence still
allows silently: 13 cases, exit 0, empty stderr except the by-design
`malformed hook input (allowing)` warn. Over the committed 416-row sweep head is
**identical to cr2r2b on 416/416 rows**, 0 rows write to stderr, all seventeen
cr18 spellings DENY, and **47 of 47** documented recipes ALLOW. shellcheck 0,
bats **115/115**, `unit` **414/414** (`--rebuild`), `lint` pass, `docs/MAP.md`
reproduces byte for byte, timing inside both caps on 10/10 medians, the subject
byte-identical to the plan line (`cmp` → identical), both trailers, one commit,
and the driver recorded `FACTORY-RESULT status=done`.

It is rejected on **two MAJORs**.

**MAJOR-1** — the structural rule covers command substitutions and nothing else.
`missing_headings` (`tools/orchestrator-guard.sh:1328`) calls the guard-defined
function `headings` inside two **process substitutions**, `<(headings "$1")
<(headings "$2")`. A process substitution is a subshell exactly like `$(…)`: a
`set -u` fault there dies in the child, `comm` succeeds on empty streams, `_ret`
comes back empty, and a **heading-removing Edit on a plan is ALLOWED**, silently,
with no guard-authored stderr — the same shape as the cr18 and cr19 holes, one
site over. Measured below. The structural test at
`tests/unit/91-orchestrator-guard.bats:1495` greps only `\$\(`, so it is green
on this hole, and adding a second guard-function pipe site (`headings "$1" |
cat`) keeps the whole suite green. Both the file header (`:75-87`) and the
runbook (`docs/runbooks/session.md:91-97`) assert the general fail-closed
property, so the tree again documents a guarantee it does not have.

**MAJOR-2** — `flake.nix` is outside the plan's `touches`
(`tools/orchestrator-guard.sh`, `tests/unit/91-orchestrator-guard.bats`,
`tests/unit/91-orchestrator-guard-sweep.txt`, `docs/runbooks/session.md`, plus
`docs/MAP.md` by rule). The change is five lines, correct and necessary — the new
recipe-pin test reads `docs/runbooks/session.md`, which the `unit` sandbox does
not otherwise contain — but the plan never authorised it. Clerical; waivable by
the operator, recorded because the convention is enumerated as a MAJOR.

Method: fresh clone (`git clone -q --branch task/CR2r3 …`); the guard driven only
from extracted copies (`…/scratchpad/guards/{head,main,cr2r2b,head-notrap}.sh`)
with `env CLAUDE_PROJECT_DIR=<fixture> bash <guard>` on compact
`ensure_ascii=False` payloads carrying `cwd` at the **top level**, stdout and
stderr captured separately on every run. Fixture: a git repo with
`.claude/{ritual-override,settings.json,worktrees/x}`, the plans dir and a plan,
`docs/second/plans/y.md`, `docs/notes/plans/x.md` (decoy), `k`, `sub/`,
`elsewhere/ritual-override`, `link-to-override` → the override, `plans-link` →
the plans dir, 200 `link<N>` symlinks, plus `…/fix/other/.claude/ritual-override`
outside the project, `…/fix/nogit` (a non-repo) and `…/fix/nogit2` (a non-repo
that does hold an override). Drivers: `…/scratchpad/{mkfix.sh,mkpayloads.py,
fault.sh,runfaults.sh,notrap.sh,evid.sh,sweep.py,cmp3.py,probe.sh,probe2.sh,
retcheck.py,timing.sh,mut.py,runmut.sh}`. Roughly 1,900 payloads, each replayed
against `main` (`5500e06:tools/orchestrator-guard.sh`, 723 lines) and cr2r2b
(`git -C /home/dalhaka/factory/ws/cr19/CR2r2b show task/CR2r2b:…`, 1413 lines) so
every difference is attributed. Host load 2.4 → 3.9 on 24 cores, seats live.

## The structural rule

My own extraction, not the test's. Guard-defined functions come from the 24
`^name()` lines (`grep -nE '^[a-zA-Z_][a-zA-Z0-9_]*\(\)'`); there are no
indented and no `function`-keyword definitions.

**Command substitutions `$(…)`** — every non-arithmetic site in the file, with
its callee:

| line | site | callee | guard function? |
|---|---|---|---|
| 462 | `_ret=$(printf … \| sed …)` | `printf`/`sed` | no |
| 469 | `_ret=$(printf … \| sed …)` | `printf`/`sed` | no |
| 595 | `_canon=$(realpath -m -- "$p")` | `realpath` | no |
| 641 | `project_canon=$(realpath …)` | `realpath` | no |
| 699 | `project_canon=$(realpath …)` | `realpath` | no |
| 1328 | `_ret=$(comm -23 …)` | `comm` | no |
| 1349 | `payload=$(cat 2>/dev/null)` | `cat` | no |
| 1400 | `pc=$(realpath -m -- …)` | `realpath` | no |
| 1414 | `before=$(cat -- "$resolved" …)` | `cat` | no |

**Zero hits.** Every other `$(` in the file is `$((…))` arithmetic. cr2r2b, for
contrast, had 24 guard-function callees. Test 110 agrees and M-A kills it.

**Backticks** — none outside comments (`grep -n '`'` hits only the header prose).

**Process substitutions `<(…)`** — five sites:

| line | site | callee | guard function? |
|---|---|---|---|
| 304 | `mapfile -t chars < <(printf … \| fold -w1)` | `printf`/`fold` | no |
| 848 | `mapfile -t rres < <(realpath -m -- …)` | `realpath` | no |
| 1312 | `mapfile -t olds < <(printf \| grep \| sed)` | external | no |
| 1313 | `mapfile -t news < <(printf \| grep \| sed)` | external | no |
| **1328** | `_ret=$(comm -23 <(headings "$1") <(headings "$2"))` | **`headings`** | **YES** |

```bash
# tools/orchestrator-guard.sh:1327-1329
missing_headings() {
  _ret=$(comm -23 <(headings "$1") <(headings "$2"))
}
```

```bash
# tools/orchestrator-guard.sh:475-477
headings() {
  printf '%s\n' "$1" | grep -E "$HEADING_ERE" | sort -u
}
```

`missing_headings` is the heading rule's whole verdict
(`tools/orchestrator-guard.sh:1441-1444`: `missing_headings "$before" "$after";
if [ -n "$_ret" ]; then deny "$HEADING_REASON"`). See MAJOR-1.

**Pipes** — no guard function appears on the right of a `|` anywhere in the file
(searched each of the 24 names against `\|[[:space:]]*(command +)?<name>\b`: no
hits). **Parenthesised subshell lists `( … )`** — none containing a guard call.

**The `_ret` discipline** — `…/scratchpad/retcheck.py` walks every statement-
position call to a guard function and every `$_ret` read in file order. The
twelve `_ret`-setting functions (`apply_edit`, `bash_verdict`, `git_verdict`,
`json_string`, `json_unescape`, `missing_headings`, `multiedit_after`,
`normalise_command`, `pad_operators`, `resolve_path`, `write_verdict`,
`_guard_trap`) are **never called twice without an intervening read**:

```
 1375 CALL  json_string      json_string "$payload" command
 1376 READ                   bcmd=$_ret
 1377 CALL  json_unescape    json_unescape "$bcmd"
 1378 READ                   bcmd=$_ret
 1379 CALL  json_string      json_string "$payload" cwd
 1380 READ                   bcwd=$_ret
 1381 CALL  bash_verdict     bash_verdict "$bcmd" "$project_dir" "$bcwd"
 1382 READ                   reason=$_ret
```

The functions that return by status or by other globals (`lex_norm` → `_lex`,
`canon_path` → `_canon`, `is_plan_file`, `is_plan_file_canon`,
`is_protected_dir_or_ancestor`, `tokenise`, `tokenise_ctx`, `_ctx_emit`) write
no `_ret`, so interleaving them is safe. **No clobber exists and I could not
construct one** — the only deviation from the stated wording is `:1441-1442`,
where `_ret` is read by `[ -n "$_ret" ]` rather than copied to a local first
(safe today, MINOR-2).

## Faults and the trap

`fault.sh` sources the guard, replaces one function with a body that reads an
unbound variable under `set -u`, then runs `main` on a payload, in a subshell,
with the guard's trap installed by `main` itself. Bash payload =
`rm -rf .claude/ritual-override`; Edit payload = an Edit on the fixture plan
removing `### A1 (code, S) — first task`. Controls, no injection: both DENY on
head (and on main), exit 0, empty stderr.

### The seven the plan lists, plus `is_plan_file`

| injected fault | arm | verdict | exit | guard's own stderr |
|---|---|---|---|---|
| `bash_verdict` | Bash | **DENY** `guard fault: the guard exited with status 127` | 0 | 1 line |
| `git_verdict` | Bash | **DENY** | 0 | 1 line |
| `write_verdict` | Bash | **DENY** | 0 | 1 line |
| `json_unescape` | Bash | **DENY** | 0 | 1 line |
| `resolve_path` | Edit | **DENY** | 0 | 1 line |
| `missing_headings` | Edit | **DENY** | 0 | 1 line |
| `apply_edit` | Edit | **DENY** | 0 | 1 line |
| `is_plan_file` | Edit | **DENY** | 0 | 1 line |

(The second stderr line in each row is bash's own `GUARD_FAULT_VAR: unbound
variable`; the guard writes exactly one line of its own, as the contract asks.)

### Helpers not on the plan's list — the structural claim tested

| injected fault | arm | verdict | guard's stderr |
|---|---|---|---|
| `json_string` | Bash / Edit | **DENY** ×2 | 1 line |
| `pad_operators` | Bash | **DENY** | 1 line |
| `normalise_command` | Bash | **DENY** | 1 line |
| `tokenise` | Bash | **DENY** | 1 line |
| `_ctx_emit` | Bash | **DENY** | 1 line |
| `tokenise_ctx` | Bash | **DENY** | 1 line |
| `lex_norm` | Bash | **DENY** | 1 line |
| `is_plan_file_canon` | Bash | **DENY** | 1 line |
| `is_protected_dir_or_ancestor` | Bash | **DENY** | 1 line |
| `multiedit_after` | Edit | **DENY** (rule reason) | 0 — never reached |
| `canon_path` | Bash | **DENY** (rule reason) | 0 — never reached |
| **`headings`** | **Edit, heading-removing** | **ALLOW** | **none** |

That last row is MAJOR-1:

```
### FN=headings EXIT=0
STDOUT:
<EMPTY>
STDERR:
_: line 3: GUARD_FAULT_VAR: unbound variable
_: line 3: GUARD_FAULT_VAR: unbound variable
GUARDLINES-stderr-lines: 0
VERDICT=ALLOW
```

against the control on the identical payload:

```
exit=0
stdout: {"…","permissionDecision":"deny","permissionDecisionReason":"typed task headings are append-only — …"}
stderr:
```

The mechanism, isolated from the guard entirely:

```
$ bash -c 'set -u; trap "echo TRAP st=$?" EXIT; f(){ local x=$NOPE; };
           _r=$(comm -23 <(f) <(echo)); echo "parent survived, _r=[$_r] rc=$?"'
bash: line 1: NOPE: unbound variable
parent survived, _r=[] rc=0
TRAP st=0                      # ← the trap sees a clean exit; nothing denies

$ bash -c 'set -u; trap "echo TRAP st=$?" EXIT; f(){ local x=$NOPE; }; f; echo NOT REACHED'
bash: line 1: NOPE: unbound variable
TRAP st=127                    # ← the main-shell call the plan relies on
```

### The trap is the mechanism (M-B, by hand)

Head with `trap _guard_trap EXIT` replaced by `:` (`…/guards/head-notrap.sh`,
`diff` printed): **all eight injections ALLOW**, 0 guard stderr lines.

### The trap and missing evidence

`trap -p EXIT` after `source "$GUARD"` prints **nothing**. Every missing-evidence
case allows with exit 0:

| case | verdict | stderr |
|---|---|---|
| project dir is not a git repo, but holds the override (`…/fix/nogit2`) | DENY (lexical, correct) | empty |
| project dir is not a git repo, path outside it | allow | empty |
| project dir does not exist | allow | empty |
| payload without `cwd`, harmless | allow | empty |
| payload without `cwd`, protected | DENY (correct — project-relative) | empty |
| `command` is an object `{"a":1}` | allow | empty |
| `command` is a number `123` | allow | empty |
| unknown tool (`Glob`) | allow | empty |
| empty payload / malformed JSON / no `tool_name` | allow ×3 | 1 `warn` line each — by design |
| `git status` in a non-repo; `grep -q zzz k`; Edit on a missing file | allow ×3 | empty ×3 |

Ordinary non-zero helper exits do not trip the trap. **TRAP-UNGATED** (the
`$st`/`_guard_decided` gates removed) makes **93** tests red, the
missing-evidence allows among them, so the gating is pinned.

## Rule behaviour

Fixture `<proj>` = `…/scratchpad/fix/proj`; `cwd` top-level on every payload;
stderr captured on every run and **empty** unless the row says otherwise.

### The seventeen cr18 spellings — 17/17 DENY, 0 stderr

| spelling | main | head |
|---|---|---|
| `rm -rf .claude/ritual-override &` | DENY | **DENY** |
| `rm -rf .claude/ritual-override&` | DENY | **DENY** |
| `rm -rf .claude &` | DENY | **DENY** |
| `rm docs/superpowers/plans/x.md &` | DENY | **DENY** |
| `sed -i s/a/b/ docs/superpowers/plans/x.md &` | DENY | **DENY** |
| `rm -rf docs/superpowers/plans &` | DENY | **DENY** |
| `git clean -fd &` | DENY | **DENY** |
| `{ rm -rf .claude/ritual-override; } &` | DENY | **DENY** |
| `rm -rf .claude/ritual-override; ls &` | DENY | **DENY** |
| `touch .claude/ritual-override &` | allow | **DENY** |
| `echo x > .claude/ritual-override &` | allow | **DENY** |
| `cp k .claude/ritual-override &` | allow | **DENY** |
| `tee .claude/ritual-override &` | allow | **DENY** |
| `git stash -u &` | allow | **DENY** |
| `rm -rf .claude/ritual-override 1>` | DENY | **DENY** |
| `rm -rf .claude/ritual-override >` | DENY | **DENY** |
| `rm -rf .claude/ritual-override \|` | DENY | **DENY** |

### The two pathspec-limited rows (accepted allows)

| spelling | main | head | runbook |
|---|---|---|---|
| `git clean 'a\|b' -f` | allow | allow | `docs/runbooks/session.md:203-208` |
| `git stash 'a\|b' -u` | allow | allow | same |

### Degenerate, operator-only and control rows — 0 stderr on all

| command | head | main |
|---|---|---|
| `&` `\|` `>` `&&` `\|\|` `>>` `>\|` `;` alone, the empty command, `k` | allow ×10 | allow ×10 |
| `rm -rf <override>` + `&&` `\|\|` `>>` `>\|` `;` `2>` | DENY ×6 | DENY ×6 |
| `(rm -rf <override>)` | DENY | DENY |
| `rm -rf .claude/worktrees/x` | allow | allow |
| `rm /tmp/…/other/.claude/ritual-override` | allow | allow |
| `cat .claude/ritual-override`, `ls -la .claude`, `git status` | allow ×3 | allow ×3 |
| `rm -f result && git clean`, `ls -a && git stash` (clause-local flags) | allow ×2 | allow ×2 |
| `git clean -n`, `git checkout main`, `git checkout -b x`, `git restore --staged k` | allow ×4 | allow ×4 |
| `echo 'a;b' && rm /tmp/x`, `echo 'a\|b' \| cat`, `printf '%s\n' 'x;y'`, `git commit -q -m 'guard: rm x; touch y \| z'` | allow ×4 | allow ×4 |

### Head vs cr2r2b — 0 differing rows out of 416

The whole committed sweep replayed against both: **identical verdict on every
row**, so the entire body cr19 verified in detail (extracts, every `-m`, the
delete family, the glob fallback, `git stash` narrowing, the Edit/Write loop pin,
the lift) is carried over unchanged. Head vs main: 117 rows differ — **115** are
main-ALLOW → head-DENY (the intended CR2 hardening) and **2** are DENY → ALLOW:

| row | command | main | head |
|---|---|---|---|
| 99 | `sed -n '1,30p' <plan> \| grep -i ritual` | DENY | allow |
| 208 | `sed -n '1,30p' <plan> \| grep -i CR2` | DENY | allow |

Both are read-only pipelines, both are the CR2r narrowing cr17/cr18/cr19 already
recorded and accepted, and both are documented — `docs/runbooks/session.md:117`
lists `sed -n` and `grep` as read verbs that never deny. No **write** shape gets
through the same door: `cat k | tee <plan>`, `cat <plan> | tee <plan>.bak`,
`cat <plan> | rm <plan>`, `grep -i x <plan> | sed -i s/a/b/ <plan>`,
`echo x | tee .claude/ritual-override` and
`sed -n 1p k | xargs rm .claude/ritual-override` all DENY (the last two are
improvements over main). **No plans-dir write regression against main.**

## Over-denial audit

**47 of 47** recipes in `docs/runbooks/session.md:216-271` ALLOW on head, with
**empty stderr on every one**. **No documented recipe is refused.**

New over-denials relative to cr2r2b: **none** (0 differing rows out of 416).
Relative to main: the 115 intended new denials, each one a write/removal spelling
of `.claude/ritual-override`, `.claude`, an ancestor, a glob under `.claude`, an
extract into a protected directory, or a `git stash -u`/`clean -f`/`checkout --`
family member — every one covered by the runbook's rule 4 and its explicit
"Over-denials are accepted on purpose" paragraph (`:196-208`).

Over-denials carried forward and documented: the project-root extract with no
`-C`/`-d`, `rm -rf .claude/worktrees/*`, `git checkout --`,
`echo "git commit --amend"`, `ls .claude && rm /tmp/x`.

No run in the entire corpus produced a spurious `guard fault` denial: over 416
sweep rows + 47 recipes + 45 spelling/degenerate rows + 8 pipe probes, **zero
rows wrote a byte to stderr** and every exit was 0.

## The sweep

`tests/unit/91-orchestrator-guard-sweep.txt`: first line `# rows: 416`, **416**
data rows, **no blanks, no comment rows, no duplicates**. I checked each pin
myself rather than trusting the test:

- **header/row-count**: 416 = 416. Test 107 asserts equality (`[ "$data_rows"
  -eq "$n" ]`), not the loose `> 300` cr19 flagged. **M-D2** (`# rows: 415`)
  kills 107.
- **recipes**: I extracted the runbook's recipe fence myself
  (`awk '/^## Recipes/{r=1} r&&/^```bash$/{f=1;next} f&&/^```$/{exit} f{print}'`)
  and grep-Fx'd each of the 47 lines against the fixture — **0 missing**. Test
  108 does exactly that. **M-D** (`git add -A` removed from the fixture) kills
  107 and 108.
- **the seventeen spellings**: present as literals in test 109 and present in the
  fixture; verified independently.
- **stderr**: I drove all 416 rows through head, main and cr2r2b —
  **0 non-empty stderr rows, 0 non-zero exits** on all three.

The runbook's recipe section is new in this commit and is now the single source
the fixture is pinned to, which is what item 4 asked for. What item 4 did *not*
ask for, and what did not happen, is filling the fixture out to cr18's historic
corpus: `rm .claude/ritual-override`, `rm -- …`, `unlink …`, `: > …`,
`echo x >| …`, `sh -c "rm …"`, `git rm -f …`, `sed --in-place …` and five of the
seven bare `git stash` subcommands are still absent (MINOR-1). I drove all of
them by hand — every one DENIES where it should, ALLOWS where it should, and
writes nothing to stderr.

## Timing

Median of five whole-hook calls, five independent rounds per case, host load
3.83 → 3.95 on 24 cores, seats live, harness shaped exactly like the bats test
(`$EPOCHREALTIME` around the same pipe).

| command | main | head, five medians | cap | met |
|---|---|---|---|---|
| **200 path tokens** | 62 ms | **92, 91, 92, 91, 94** | 100 ms | yes |
| **200 symlink tokens** | 369 ms | **93, 89, 90, 89, 88** | 200 ms | yes |

Both bats timing tests pass on their own (`--filter timing` → `1..2`, 2 ok).
**C17-M-D** (the O(n²) `${s:i:1}` tokeniser restored) kills test 53, so the cap
is genuinely pinned.

The runbook carries **no measured figures**: `grep -nE '[0-9]+ ?ms'
docs/runbooks/session.md` returns exactly three hits — `**100 ms**`, `**200 ms**`
and the `<300 ms` budget (`:209-212`) — plus the measuring command
`nix develop -c bats tests/unit/91-orchestrator-guard.bats --filter timing`.
cr19's MINOR-2 (the three-round `83 ms` carry-over) is gone.

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| check | command | rc | result |
|---|---|---|---|
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **0** | clean |
| bats 91 | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | **0** | `1..115`, **115 ok**, no `not ok` |
| bats timing | `… --filter timing` | **0** | `1..2`, 2 ok |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **0** | **414/414** |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **0** | pass |
| pre-commit | `nix develop -c githooks/pre-commit` | **1** → **0** | treefmt 94 files, **0 changed**, `All checks passed!`; rc 1 only on `tasks: docs/OPERATIONS.md queue block was stale`; **rc 0** once the regenerated board is staged (the board is not in `touches`) — structural, as in every prior gate |
| MAP | `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | **0** | **identical** to the committed file |

Working tree left clean (`git status --porcelain` empty) after every experiment;
`md5sum tools/orchestrator-guard.sh` matches `HEAD:tools/orchestrator-guard.sh`.

## Red before green

cr2r2b's guard (`git -C /home/dalhaka/factory/ws/cr19/CR2r2b show
task/CR2r2b:tools/orchestrator-guard.sh`, 1413 lines) copied over the clone's
guard, CR2r3's tests kept. Tree asserted changed (`git diff --numstat` →
`97 139 tools/orchestrator-guard.sh`), bats run, restored, re-run green.

```
1..115
not ok  52 bash: quotes strip to nothing so echo "a'b" stays one word
not ok  99 a fault in bash_verdict denies via the EXIT trap (guard fault)
not ok 102 a fault in json_unescape denies via the EXIT trap (guard fault)
not ok 103 a fault in resolve_path denies via the EXIT trap (guard fault)
not ok 104 a fault in missing_headings denies via the EXIT trap (guard fault)
not ok 105 a fault in apply_edit denies via the EXIT trap (guard fault)
not ok 110 no guard function is called inside a command substitution (structural)
not ok 111 sourcing the guard installs no EXIT trap (the trap lives only on the entry path)
# bats warning: Executed 113 instead of expected 115 tests
```

Every test the plan named goes red: the structural callee test (110, the 24
sites), five of the seven injections (99, 102–105 — the other two,
`git_verdict` and `write_verdict`, honestly passed on cr2r2b because those two
substitutions already carried a status check), the trap-at-source test (111), and
the nested-`cwd` test's neighbours. **52** goes red because cr2r2b's source-time
trap clobbers bats' own — the very defect cr19's MINOR-3 named, now fixed. The
two tests that vanish from the TAP stream (113 instead of 115) are cr2r2b's
clobber again.

The three sweep pins (107, 108, 109) **cannot** go red on a guard swap — they
test the fixture and the runbook, not the guard — so they are pinned by M-D and
M-D2 instead (below). After `git checkout --`, tree clean and **115/115** green.

## Mutation table

Each mutation applied by content anchor, the tree asserted changed (`numstat`
printed per row), the full bats file run, then reverted; `git status
--porcelain` empty after every row. Scripts: `…/scratchpad/{mut.py,runmut.sh}`.

### This round's

| # | mutation | numstat | bats rc | killed |
|---|---|---|---|---|
| **M-A** | `reason=$(bash_verdict …; printf '%s' "$_ret")` restored (behaviour-preserving) | 1+/2− | **1** | **99 100 101 110** — the structural test **and** the injection, exactly as the plan says |
| M-A-plain | the same without the `printf` (verdict lost too) | 1+/2− | **1** | 50 tests |
| **M-B** | the `EXIT` trap removed (`:1335`) | 1+/1− | **1** | **99 100 101 102 103 104 105 106** — every injection allows |
| **M-C** | the trap moved back to top level (removed from `main`, added after `_ret=''`) | 1+/1− | **1** | **111** |
| **M-D** | one recipe (`git add -A`) removed from the fixture | 0+/1− | **1** | **107 108** |
| **M-D2** | `# rows: 415` (header wrong by one) | 1+/1− | **1** | **107** |
| **M-E** | the nested-`cwd` grep weakened | — | — | **pinned, but self-referentially** — see below |
| **M-F** | a guard function on the right of a pipe (`headings "$1" \| cat`) added to `missing_headings` | 1+/0− | **0** | **NOTHING — 115/115 still green** (MAJOR-1's test gap) |

**M-E**: the pattern cannot be weakened into a false pass, because the test greps
the file it lives in — any literal I substitute matches its own line and the test
fails (`! grep -q 'ZZZ_NEVER_MATCHES'` → `not ok 112`, since the file now
contains `ZZZ_NEVER_MATCHES`). The real pattern `"tool_input":{[^}]*"cwd"` does
*not* self-match (the `}` inside `[^}]` breaks it). So the pin is real but
accidental. I verified it catches the thing it is for: inserting
`# p={"tool_name":"Bash","tool_input":{"command":"rm x","cwd":"/tmp"}}` at
`:1513` makes 112 red. The committed file has **0** nested-`cwd` occurrences.

### Prior rounds re-applied — all still die

| # | mutation | numstat | bats rc | killed |
|---|---|---|---|---|
| C15-A | the plans entry deleted from `PROTECTED_PATHS` | 0+/1− | 1 | **25** |
| C15-B | the override entry deleted | 0+/1− | 1 | **23** |
| C15-K | the lift flag ignored | 1+/1− | 1 | 77 86 |
| C17-M-D | the O(n²) `${s:i:1}` tokeniser restored | 1+/1− | 1 | **53** (the 100 ms cap) |
| LOOKAHEAD-`&` | `:-` removed at the `'&'` lookahead (`:316`) | 1+/1− | 1 | 97 98 107 |
| LOOKAHEAD-`\|` | the same at `'\|'` (`:317`) | 1+/1− | 1 | 97 107 |
| LOOKAHEAD-`>` | the same at `'>'` (`:318`) | 1+/1− | 1 | 97 107 |
| TRAP-UNGATED | the `$st`/`_guard_decided` gates dropped | 0+/2− | 1 | **93** |
| C19-M-F | `dq` dropped from `write_verdict`'s `local` list (`:674`) | 1+/1− | 1 | **114, as a named `not ok`** — cr19's MINOR-3 is fixed |

## Findings

### MAJOR-1 — `headings` runs inside a process substitution, so a fault there ALLOWS a heading-removing edit, silently

The plan's decision: *"No function defined in the guard is ever called inside
`$(…)`: every guard function returns through one global, runs in the main shell,
and a fault under `set -u` therefore kills the main shell, where the EXIT trap
denies."* The rule was implemented for `$(…)` and only `$(…)`. One site remains:

```bash
# tools/orchestrator-guard.sh:1327-1329
missing_headings() {
  _ret=$(comm -23 <(headings "$1") <(headings "$2"))
}
```

`<( … )` is a subshell with exactly the property the plan is defending against.
Measured, `source`-and-override injection, Edit payload removing
`### A1 (code, S) — first task` from the fixture plan:

```
== headings faults (Edit arm, heading-removing payload)   ALLOW exit=0
   stdout=<EMPTY>
   stderr=_: line 3: GUARD_FAULT_VAR: unbound variable
          _: line 3: GUARD_FAULT_VAR: unbound variable
   guard-authored stderr lines: 0
== control: no injection, same payload                    DENY  exit=0
   stdout={"…","permissionDecision":"deny","permissionDecisionReason":"typed task headings are append-only — …"}
   stderr=<EMPTY>
```

The subshell dies, `comm -23` reads two empty streams and succeeds, `_ret` is
empty, `main` concludes nothing was removed, `[ -n "$_ret" ]` is false, the
script exits 0, and `_guard_trap` returns early at `[ "$st" -eq 0 ]`
(`:118`). The guard writes **no line of its own** — as silent as the cr18 and
cr19 holes.

The test that is supposed to make this class impossible only looks for `$(`:

```bash
# tests/unit/91-orchestrator-guard.bats:1495
  grep -oE '\$\([A-Za-z_][A-Za-z0-9_]*' "$GUARD" | sed 's/\$(//' | sort -u >"$BATS_TEST_TMPDIR/callees"
```

so it is green on `<(headings …)`, and **M-F** proves the blindness extends to
pipes: adding `headings "$1" | cat >/dev/null` to `missing_headings` leaves the
suite at 115/115.

Both the guard header and the runbook now assert the general property:

```
# tools/orchestrator-guard.sh:76-81
# A guard FAULT fails closed, never open, by construction:
# no function this file defines is ever called inside a command substitution —
# … so every function runs in the main shell and a fault that
# aborts the shell under `set -u` reaches the EXIT trap, which denies.
```

```
docs/runbooks/session.md:91-95
closed, never open, by construction: no function the guard defines is ever
called inside a command substitution — every guard function returns its result
through one global (`_ret`, …), so a fault
that aborts the shell under `set -u` reaches the `EXIT` trap, which **denies**
```

The sentence is literally true of `$(…)` and false of the guarantee it claims:
`headings` runs in a subshell and its fault does not reach the trap. This is the
same defect the round exists to close, so it is a MAJOR, not a minor. No live
input reaches it today — `headings`' body is `printf | grep | sort`, all
external, and nothing in the current file can make it fault — so it is a
robustness gap, exactly as cr19's was.

Fix shape: make `missing_headings` self-contained (inline the two `grep -E |
sort -u` pipelines, keeping only external commands inside the substitutions), or
give `headings` an `_ret` contract and call it twice in the main shell writing to
two temp files. Red test first — a `headings` fault injection on a
heading-removing Edit that must DENY. Then widen the structural test to cover
`<(`, `` ` ``, `| <fn>` and `( <fn>` — M-F is the mutation that must die.

### MAJOR-2 — `flake.nix` is outside the plan's touches

The commit changes six files. Five are accounted for: the four in `touches` plus
`docs/MAP.md`, which reproduces byte for byte from
`pkgs/evidence/repomap.py --root . write` and whose only change is
`tests/unit` 15 → 16 files. The sixth is `flake.nix`:

```nix
+              # tests/unit/91-orchestrator-guard.bats reads the runbook's recipe
+              # section at ../../docs/runbooks/session.md (the sweep fixture is
+              # pinned to it), so copy it in like the resolves above.
+              mkdir -p docs/runbooks
+              cp ${self}/docs/runbooks/session.md docs/runbooks/session.md
```

The change is correct, minimal and necessary — test 108 reads
`$BATS_TEST_DIRNAME/../../docs/runbooks/session.md`, which the `unit` sandbox
does not otherwise contain, and without it the check the plan's step 4 requires
cannot pass. The defect is scope, not content: the plan authorised four files and
did not anticipate that pinning the fixture to the runbook drags the runbook into
the build sandbox. Recorded because the brief enumerates a commit-convention
breach as a MAJOR; waivable by the operator with a one-line amendment to the plan
section's touches.

### MINOR-1 — the sweep fixture still is not cr18's historic corpus

Item 4 pinned the fixture to the runbook's recipe section, the row count and the
seventeen spellings, and all three pins hold exactly. cr19's MINOR-5 — that the
fixture omits rows from the historic corpus — is untouched: `rm
.claude/ritual-override`, `rm -- .claude/ritual-override`, `unlink …`, `: > …`,
`echo x >| …`, `sh -c "rm …"`, `git rm -f …`, `sed --in-place …`, `git stash
push`/`pop`/`apply`/`drop`/`show` are all absent. Not a regression and not what
this round promised; I drove every one of them against head with zero stderr and
the right verdict.

### MINOR-2 — one `_ret` read is not the "copy to a local at once" the contract states

```bash
# tools/orchestrator-guard.sh:1441-1442
  missing_headings "$before" "$after"
  if [ -n "$_ret" ]; then
```

Safe today (nothing runs between the call and the read) but it is the one site
that does not follow the discipline the header states, and it is the site a
future edit is most likely to break — the caller already has a `reason` local
declared at `:1368`.

### MINOR-3 — a fault injection emits two stderr lines, only one of them the guard's

As in cr19: bash's own `GUARD_FAULT_VAR: unbound variable` precedes the guard's
`orchestrator-guard: guard fault: …`. The guard writes exactly one line, which is
what the contract governs. Recorded, not a defect.

### NOTE — `rm plans-link/x.md` allows on head and on main

A write through the symlink `plans-link` → the plans dir is not caught. Head and
main agree, so it is not a regression this round and is out of scope, but the
header's claim at `:70-73` ("a symlink INTO the plans dir … cannot dodge the plan
rules") is about the other direction and this row is worth a line in some future
plan.

### NOTE — the implementer's claims, checked

| claim | verdict |
|---|---|
| "all verdict functions return via `_ret` (no guard function in a `$()` subshell)" | **true** — 24 sites removed, my own extraction finds 0, M-A kills the structural test |
| the fault channel is structural, every fault reaches the trap | **false in one place** — `headings` inside `<( )` allows a heading-removing Edit (MAJOR-1) |
| "trap on the entry path only" | **true** — `trap -p EXIT` empty after sourcing; M-C kills 111; cr19's TAP-clobber defect gone |
| "runbook carries caps not figures" | **true** — three `ms` hits, all caps/budget, plus the measuring command |
| "sweep pinned to sources" | **true for what item 4 named** — `# rows: 416` = 416, 47/47 recipes, 17/17 spellings, M-D/M-D2 kill; the historic corpus is still not folded in (MINOR-1) |
| "four mutations and seven fault injections verified dead" | **true as far as it goes** — I reproduce all four and all eight injections; the eighth helper class was not tested and is where the hole is |
| "unit=pass lint=pass" | **true** — 414/414, lint pass, shellcheck 0, MAP identical |
| commit conventions | **one breach** — subject byte-identical, both trailers, one commit, `FACTORY-RESULT status=done` recorded; `flake.nix` outside touches (MAJOR-2) |

## Verdict

**REJECTED** — two MAJORs.

CR2r3 is a good refactor and it does what cr19 asked for in every place cr19
looked. Twenty-four command substitutions over guard functions are gone; the
`_ret` discipline holds at every one of the rewritten sites and no clobber can be
constructed; eight fault injections deny with `guard fault`, exit 0 and one
guard-authored line; removing the trap makes all eight allow, so the mechanism is
proven; the trap no longer clobbers bats' own, so a failing sourcing test finally
prints a named `not ok`; missing evidence still allows silently in thirteen
shapes; the sweep's three pins are exact and their mutations die; the runbook
carries caps and a command instead of stale numbers; timing is inside both caps
on ten of ten medians; and the whole rule surface is bit-identical to cr2r2b over
416 rows, with 47 of 47 recipes allowed and zero stderr anywhere in ~1,900 driven
payloads.

What fails is the completeness of the rule, again, one construct over. The plan's
decision is that *no guard function runs in a subshell on a verdict path*; the
implementation, the test and both prose contracts all say "command substitution".
`missing_headings` calls `headings` inside two **process substitutions**, and an
injected fault there ALLOWS a heading-removing Edit on a plan — silently, with no
guard-authored stderr, the exact failure mode of cr18 and cr19. The structural
test greps only `$(`, so it is green on the shipped hole, and M-F shows a
guard-function pipe site passes too. Separately, `flake.nix` is edited outside
the plan's touches.

A re-plan is XS. Make `missing_headings` self-contained — inline `printf | grep
-E "$HEADING_ERE" | sort -u` on both sides so only external commands stand inside
the substitutions — with the red test first (a `headings` fault injection on a
heading-removing Edit that must DENY, plus the mutation that puts `headings`
back inside `<( )`). Widen test 110 from `\$\(` to every subshell spelling —
`$(`, `` ` ``, `<(`, `>(`, a guard name on the right of a `|`, and a guard name
inside a `( … )` list — and pin it with M-F. Correct both prose contracts
(`tools/orchestrator-guard.sh:76-81`, `docs/runbooks/session.md:91-97`) to say
*subshell*, not *command substitution*. Add `flake.nix` to the section's touches.
While the file is open, MINOR-1 (fill the fixture out to the historic corpus, now
that the row count is pinned exactly) and MINOR-2 (`reason=$_ret` at `:1442`) are
cheap. Everything else in CR2r3 should be kept as it is.
