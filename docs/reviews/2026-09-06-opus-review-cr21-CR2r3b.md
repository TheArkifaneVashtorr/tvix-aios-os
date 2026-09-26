---
plan_defect: underspecified
plan_defect_secondary: missing-case
mutants_total: 22
mutants_killed: 22
mutants_outside_named: 1
---
# Opus gate — seat run cr21, task CR2r3b — APPROVED

## Summary

One commit (`3939c87`) on base `cebb3d7` (main), branch `task/CR2r3b` in
`/home/dalhaka/factory/ws/cr21/CR2r3b`. Reviewed in a fresh clone at
`…/scratchpad/gate-cr21-CR2r3b`; nothing under `/home/dalhaka/factory` was
modified, the live repo's `.claude/ritual-override` was never touched, and every
guard run drove a throwaway fixture at `…/scratchpad/fix/proj`.

**Both cr20 MAJORs are fixed, and the fix is the structural one the plan asked
for.** `missing_headings` now calls `headings` twice **in the main shell** and
copies each result into a local before `comm` runs over two `<(printf …)`
substitutions that hold nothing but an external `printf`
(`tools/orchestrator-guard.sh:1339-1350`). My own eight-pattern audit of the
file — `$(`, backticks, `<(`, `>(`, a guard name on the right of a `|`, a guard
name on the **left** of a `|`, `( name`, a trailing `&`, `xargs`/`-exec` —
finds **zero** guard-function callees in any child process. The behavioural
loop I ran myself over **all 24** defined functions × 3 payloads is **DENY in
every one of the 60 cells** belonging to the 20 functions that are guard logic,
exit 0, with the guard's own single stderr line wherever the fault is actually
on that arm's path. `flake.nix` is now inside the section's `touches`.

shellcheck 0; bats **119/119**; `unit` **426/426** (`--rebuild`); `lint` pass;
`docs/MAP.md` reproduces byte for byte; the pre-commit gate is rc 0 once the
regenerated board is staged; the subject is byte-identical to the plan line
(`cmp` → identical); both trailers; one commit; the tree clean after every
experiment. Timing is inside both caps on **5/5** medians for both cases. Over
the committed **442**-row sweep replayed against head and main, plus 50
hand-driven probe rows, 47 recipes, 14 missing-evidence shapes and 24 × 4 fault
injections — roughly 1,500 payloads — **zero** rows wrote a byte to stderr
(beyond the by-design `malformed hook input` warning) and **zero** exited
non-zero. Against `main`, **0** write or removal spellings of a protected path
regress. **22 of 22** mutations die.

Method: `git clone -q --branch task/CR2r3b …`; the guard driven only from
extracted copies (`…/scratchpad/guards/{head,main,cr2r3}.sh`) with
`env CLAUDE_PROJECT_DIR=<fixture> bash <guard>` on compact `ensure_ascii=False`
payloads carrying `cwd` at the **top level**, stdout and stderr captured
separately on every run. Fixture: a git repo with
`.claude/{ritual-override,settings.json,worktrees/x}`, the plans dir and a plan
holding two typed headings, `docs/second/plans/y.md`, `docs/notes/plans/x.md`
(decoy), `k`, `sub/`, `link-to-override` → the override, `plans-link` → the
plans dir, `leaf-plan-link` → the plan file, 200 `link<N>` symlinks, plus
`…/fix/other/.claude/ritual-override` outside the project, `…/fix/nogit` (a
non-repo) and `…/fix/nogit2` (a non-repo that does hold an override). Drivers:
`…/scratchpad/g21/{loop.sh,loop4.py,subshell.py,sweep.py,extract.py,recipes.py,
probe.py,leaf.py,retcheck.py,timing.sh,verbatim.sh,mut*.py,runmut*.sh}`. Host
load 2.9 → 3.7 on 24 cores, seats live.

Four MINORs, none blocking. The plan's item 1 ("EVERY function the file
defines") is not literally implementable for the four functions that *are* the
fault channel, and its three payloads never reach `multiedit_after`. That is
where `plan_defect: underspecified` / `missing-case` comes from — not from the
implementation, which handled both honestly.

## The loop (N × 3 table)

I enumerated the functions myself from the `^name()` lines — `grep -oE
'^[A-Za-z_][A-Za-z0-9_]*\(\)'` finds **24**; there are no indented and no
`function`-keyword definitions. For each, `…/g21/loop.sh` sources the guard,
replaces that one function with `{ local x=$GUARD_FAULT_VAR; : "$x"; }` (fatal
under `set -u`), and runs `main` in a subshell on three payloads: **p1** a Bash
`rm -rf .claude/ritual-override`, **p2** an Edit removing
`### A1 (code, S) — first task` from the fixture plan, **p3** a Write onto the
plan that drops both headings. `fault=yes` means the deny reason is
`guard fault: …` (the fault channel fired); `fault=no` means the arm denied on
its own rule because that function is not on this arm's path. `gl` counts
guard-authored stderr lines. Exit is 0 on every row except the two marked.

| function | p1 Bash rm override | p2 Edit heading-removing | p3 Write onto plan |
|---|---|---|---|
| `deny` | **ALLOW** rc=127 gl=1 | **ALLOW** rc=127 gl=1 | **ALLOW** rc=127 gl=1 |
| `warn` | DENY fault=no | DENY fault=no | DENY fault=no |
| `_guard_trap` | DENY fault=no | DENY fault=no | DENY fault=no |
| `normalise_command` | DENY fault=yes gl=1 | DENY fault=no | DENY fault=no |
| `pad_operators` | DENY fault=yes gl=1 | DENY fault=no | DENY fault=no |
| `tokenise` | DENY fault=yes gl=1 | DENY fault=no | DENY fault=no |
| `_ctx_emit` | DENY fault=yes gl=1 | DENY fault=no | DENY fault=no |
| `tokenise_ctx` | DENY fault=yes gl=1 | DENY fault=no | DENY fault=no |
| `git_verdict` | DENY fault=yes gl=1 | DENY fault=no | DENY fault=no |
| `json_string` | DENY fault=yes gl=1 | DENY fault=yes gl=1 | DENY fault=yes gl=1 |
| `json_unescape` | DENY fault=yes gl=1 | DENY fault=yes gl=1 | DENY fault=yes gl=1 |
| **`headings`** | DENY fault=no | **DENY fault=yes gl=1** | **DENY fault=yes gl=1** |
| `apply_edit` | DENY fault=no | DENY fault=yes gl=1 | DENY fault=no |
| `bash_verdict` | DENY fault=yes gl=1 | DENY fault=no | DENY fault=no |
| `lex_norm` | DENY fault=yes gl=1 | DENY fault=yes gl=1 | DENY fault=yes gl=1 |
| `canon_path` | DENY fault=no | DENY fault=yes gl=1 | DENY fault=yes gl=1 |
| `is_plan_file_canon` | DENY fault=yes gl=1 | DENY fault=yes gl=1 | DENY fault=yes gl=1 |
| `is_protected_dir_or_ancestor` | DENY fault=yes gl=1 | DENY fault=no | DENY fault=no |
| `resolve_path` | DENY fault=no | DENY fault=yes gl=1 | DENY fault=yes gl=1 |
| `is_plan_file` | DENY fault=no | DENY fault=yes gl=1 | DENY fault=yes gl=1 |
| `write_verdict` | DENY fault=yes gl=1 | DENY fault=no | DENY fault=no |
| `multiedit_after` | DENY fault=no | DENY fault=no | DENY fault=no |
| `missing_headings` | DENY fault=no | DENY fault=yes gl=1 | DENY fault=yes gl=1 |
| `main` | **ALLOW** rc=127 gl=0 | **ALLOW** rc=127 gl=0 | **ALLOW** rc=127 gl=0 |

**60 of 60 cells over the 20 guard-logic functions DENY with exit 0.** The
cr20 hole is closed, verbatim (`…/g21/verbatim.sh`):

```
### control, no injection, Edit removing a heading  EXIT=0
STDOUT: {"hookSpecificOutput":{…,"permissionDecision":"deny","permissionDecisionReason":"typed task headings are append-only — …"}}
STDERR:

### FN=headings, Edit removing a heading  EXIT=0
STDOUT: {"hookSpecificOutput":{…,"permissionDecision":"deny","permissionDecisionReason":"guard fault: the guard exited with status 127"}}
STDERR:
_: line 3: GUARD_FAULT_VAR: unbound variable
orchestrator-guard: guard fault: the guard exited with status 127
```

cr20 measured `ALLOW`, empty stdout and **0** guard-authored stderr lines on
this exact payload. The guard writes exactly one line of its own; bash's own
`GUARD_FAULT_VAR: unbound variable` precedes it, as in every prior round.

**The two ALLOW rows are the fault channel itself, not guard logic.** With
`deny` replaced by a faulting body there is no primitive left that can emit a
deny — the trap still writes `orchestrator-guard: guard fault …` but the JSON
never appears; with `main` replaced there is no entry path and no trap is ever
installed. No implementation can do better. Two of the four excluded names
(`warn`, `_guard_trap`) in fact still DENY here, because these payloads deny on
their own rules. See MINOR-1.

**The bats loop test derives its list; it does not hard-code it**
(`tests/unit/91-orchestrator-guard.bats:1604-1633`):

```bash
  while IFS= read -r fn; do
    case "$fn" in
      main | deny | warn | _guard_trap) : ;;
      *) fns+=("$fn") ;;
    esac
  done < <(grep -oE '^[A-Za-z_][A-Za-z0-9_]*\(\)' "$guard" | sed 's/()//')
  [ "${#fns[@]}" -eq 20 ]
```

A function added tomorrow **is** covered automatically (it falls into the `*`
arm), and the `-eq 20` line is a tripwire that turns the test red until the
author looks at it — stronger than a silent widening, and not a hard-coded
list. All three payloads run per function; `[ "$status" -eq 0 ]` and
`denied "$output"` are asserted per cell. The test is red on CR2r3 with the
named message `headings fault ALLOWED on a payload`.

## Subshell forms

My own extraction (`…/g21/subshell.py`), executable lines only (comment lines
stripped), every callee resolved against the 24 definitions.

| form | raw sites | guard-function callees |
|---|---|---|
| `$(name` command substitution | 10 | **0** — `printf` ×3, `realpath` ×4, `comm`, `cat` ×2 |
| backtick | 0 | **0** |
| `<(name` / `>(name` process substitution | 6 | **0** — `printf` ×5, `realpath` ×1 |
| guard name after `\|` | 72 | **0** (all `case`-arm alternations, `\|\|` tests, `grep`/`sort`/`fold`) |
| guard name inside `( … )` list | 0 | **0** |
| guard name before `\|` (left of a pipe) | 40 | **0** — the only definition-name hit is `:1432` `is_plan_file … \|\| return 0`, a `\|\|`, not a pipe |
| trailing `&` background | 0 | **0** |
| `xargs` / `find -exec` | 1 | **0** (`local -a … c_extract`) |

The remaining `$(…)` sites and their callees: `:470` `printf|sed`, `:477`
`printf|sed`, `:484` `printf|grep|sort`, `:603` `realpath`, `:649` `realpath`,
`:707` `realpath`, `:1349` `comm`, `:1370` `cat`, `:1421` `realpath`, `:1435`
`cat`. The five `mapfile … < <(…)` sites run, in order: `printf … | fold -w1`
(`:312`); `realpath -m -- "${rargs[@]}"` (`:856`); `printf … | grep -o … | sed`
twice (`:1320`, `:1321`); plus the two `printf '%s\n' "$bheads"/"$aheads"`
inside `comm` (`:1349`). **External commands only, everywhere.**

The new implementation:

```bash
# tools/orchestrator-guard.sh:1339-1350
missing_headings() {
  local bheads aheads
  headings "$1"
  bheads=$_ret
  headings "$2"
  aheads=$_ret
  if [ -z "$bheads" ]; then
    _ret=''
    return 0
  fi
  _ret=$(comm -23 <(printf '%s\n' "$bheads") <(printf '%s\n' "$aheads"))
}
```

`headings` itself became `_ret=$(printf … | grep -E "$HEADING_ERE" | sort -u)` —
a substitution over externals only, which the contract permits. I checked the
`comm` edge cases by hand: `bheads` empty short-circuits to `''`; `aheads` empty
feeds `comm` a single blank line, which sorts first and leaves every heading in
the `-23` output, so a Write that drops every heading still denies (measured:
p3 control DENIES).

The structural test (`:1494-1517`) now scans `$(`, backticks, `[<>](`,
`\|[[:space:]]*name` and `\([[:space:]]*name`, then `comm -12`s the callees
against the definitions. It is red on CR2r3 with `functions called in a subshell
form: headings`. It does **not** scan a guard name on the *left* of a pipe or a
trailing `&` — both are subshells — but the plan enumerated exactly five forms,
and the behavioural loop covers those two anyway. See MINOR-3.

## The sweep

`tests/unit/91-orchestrator-guard-sweep.txt`: first line `# rows: 442`,
**442** data rows, **no blanks, no comment rows, 0 duplicates**. Every pin
checked by me, not by the test:

- **row count** — 442 = 442; test 107 asserts equality; **M-C2** (`# rows: 441`)
  kills it.
- **the runbook's recipes** — I extracted the fence myself
  (`awk '/^## Recipes/{r=1} r&&/^```bash$/{f=1;next} f&&/^```$/{exit} f{print}'`)
  → **47** lines, `grep -Fxq` against the fixture → **0 missing**. Test 108 does
  the same and additionally asserts `in_recipes` and `in_fence` are 1, so it
  cannot pass vacuously. **c20-M-D** (`git add -A` removed) kills 107 and 108.
- **the seventeen cr18 spellings** — literals in test 109 (with a
  `[ "${#spellings[@]}" -eq 17 ]` guard) and present in the fixture; all
  seventeen re-driven below.
- **the cr17/cr18 review corpus** — I wrote my own extractor
  (`…/g21/extract.py`) rather than trusting the test's. The two byte-frozen
  reviews (last touched by `9f5fb13`) hold **95** and **108** table rows across
  11 tables each (203 total). Restricting to tables whose first header cell is
  `spelling` — what the test does — yields **58** distinct runnable commands;
  taking **every** table yields **63**. **All 63 are fixture rows; 0 missing on
  either extraction.** The five the `spelling` restriction drops
  (`chattr +i .claude`, `chmod -R 000 .claude`, `chmod 000 .claude`,
  `chown root .claude`, `git status`) are in the fixture too. The rows neither
  extractor takes are the ⏎-joined two-line commands, the `…`-elided ones and
  bare fragments — not flat fixture rows by construction. **M-C** (one review
  row, `git clean -f; ls`, removed from the fixture) kills 107 and 119 with
  `command from a review table missing from the sweep: git clean -f; ls`.
- **cr20's MINOR-1 (the historic corpus) is folded in**: `rm
  .claude/ritual-override`, `rm -- …`, `unlink …`, `: > …`, `echo x >| …`,
  `git rm -f …` and `git stash push/pop/apply/drop/show` are all present now.

I drove all **442** rows through `head` and through `main`
(`cebb3d7:tools/orchestrator-guard.sh`, 723 lines), stderr captured separately:
**0 non-empty stderr rows and 0 non-zero exits on either**, 884 runs.

**Head vs main: 131 rows differ — 128 are main-ALLOW → head-DENY (the intended
CR2 hardening) and 3 are DENY → ALLOW:**

| row | command | main | head |
|---|---|---|---|
| 98 | `sed -n '1,30p' <plan> \| grep -i ritual` | DENY | allow |
| 207 | `sed -n '1,30p' <plan> \| grep -i CR2` | DENY | allow |
| 426 | `sed -n '1,30p' <plan> \| grep -i CR2rb` | DENY | allow |

All three are the same read-only shape — the CR2r clause-local narrowing that
cr17, cr18, cr19 and cr20 each recorded and accepted (426 is new only because
the corpus rows were added this round). `docs/runbooks/session.md:145` lists
`sed -n` and `grep` as read verbs that never deny. **No write or removal
spelling regresses**: `cat k | tee <plan>`, `cat <plan> | tee <plan>.bak`,
`echo x | tee .claude/ritual-override`, `sed -n 1p k | xargs rm
.claude/ritual-override`, `sed --in-place … <plan>`, `find .claude -name x
-delete`, `dd of=.claude/ritual-override if=k`, `rm -rf .claude/*` and the
python `os.remove` spelling all DENY (several are improvements over main).

**Over-denial audit — 47 of 47 documented recipes ALLOW on head, with empty
stderr on every one. No documented recipe is refused.**

## Rule behaviour

Fixture `<proj>` = `…/scratchpad/fix/proj`; `cwd` top-level on every payload;
stderr captured on every run and **empty** unless the row says otherwise.

### The seventeen cr18 spellings — 17/17 DENY, 0 stderr, all 17 in the fixture

`rm -rf <override> &` · `rm -rf <override>&` · `rm -rf .claude &` ·
`rm <plan> &` · `sed -i s/a/b/ <plan> &` · `rm -rf <plans-dir> &` ·
`git clean -fd &` · `{ rm -rf <override>; } &` · `rm -rf <override>; ls &` ·
`touch <override> &` · `echo x > <override> &` · `cp k <override> &` ·
`tee <override> &` · `git stash -u &` · `rm -rf <override> 1>` ·
`rm -rf <override> >` · `rm -rf <override> |` — **DENY ×17**, exit 0, no stderr.

### The two pathspec-limited rows (accepted allows)

`git clean 'a|b' -f` and `git stash 'a|b' -u` allow on main and head alike, and
are documented at `docs/runbooks/session.md:221-227`.

### Degenerate, operator-only and control rows — 0 stderr on all

| command | main | head |
|---|---|---|
| `&` `\|` `>` `&&` `\|\|` `>>` `>\|` `;` alone, the empty command, `k` | allow ×10 | allow ×10 |
| `rm -rf <override>` + `&&` `\|\|` `>>` `>\|` `;` `2>` | allow ×6 | **DENY ×6** |
| `(rm -rf <override>)` | DENY | DENY |
| `rm -rf .claude/worktrees/x` | allow | allow |
| `rm <outside-project>/.claude/ritual-override` | allow | allow |
| `cat <override>`, `ls -la .claude`, `git status` | allow ×3 | allow ×3 |
| `rm -f result && git clean`, `ls -a && git stash` (clause-local flags) | allow ×2 | allow ×2 |
| `git clean -n`, `git checkout main`, `git checkout -b x`, `git restore --staged k` | allow ×4 | allow ×4 |
| `echo 'a;b' && rm /tmp/x`, `echo 'a\|b' \| cat`, `printf '%s\n' 'x;y'`, `git commit -q -m 'guard: rm x; touch y \| z'` | allow ×4 | allow ×4 |
| `git commit -m 'x' -m 'rm -rf .claude'`, `git commit -am 'fix: rm -rf .claude now'` | allow ×2 | allow ×2 |
| `find . -name x -delete` / `find .claude -name x -delete` | DENY / allow | DENY / **DENY** |
| `tar -xf a.tar` (root, no `-C`) / `tar -xf a.tar -C /tmp` | allow / allow | **DENY** / allow |

### The Edit/Write/MultiEdit arm

| case | main | head |
|---|---|---|
| Edit / Write / MultiEdit onto `.claude/ritual-override` | allow ×3 | **DENY ×3** |
| Edit through `link-to-override` (leaf symlink to the override) | allow | **DENY** |
| Edit removing a heading / altering a heading / Write dropping a heading | DENY ×3 | DENY ×3 |
| Edit appending a heading / Write keeping both | allow ×2 | allow ×2 |
| Edit on the decoy `docs/notes/plans/x.md` | allow | allow |
| Edit through `sub/../docs/superpowers/plans/x.md` | DENY | DENY |
| Edit through `leaf-plan-link` (leaf symlink to the plan) | DENY | DENY |
| Edit through `plans-link/x.md` (symlinked *directory* into the plans dir) | allow | allow |
| `rm plans-link/x.md` | allow | allow |

The last two rows are the known gap item 5 orders stated, not fixed; head and
main agree, so nothing regresses. See MINOR-4.

### Missing evidence still allows, silently

Fourteen shapes, exit 0 on all: a non-repo project dir holding an override
(DENY — lexical and correct), a non-repo with the path outside it, a missing
project dir, a payload with no `cwd` (harmless → allow; protected → DENY,
project-relative and correct), `command` as an object, `command` as a number,
an unknown tool (`Glob`), `git status` in a non-repo, `grep -q zzz k`, an Edit
on a missing plan file — **all with empty stderr**; the empty payload,
malformed JSON and a payload with no `tool_name` allow with the by-design
single `orchestrator-guard: malformed hook input (allowing)` line.

`trap -p EXIT` after `source`ing the guard prints **nothing** — the trap is
installed by `main` as its first statement (`:1356`).

### The `_ret` discipline

My own walk (`…/g21/retcheck.py`) over every statement-position call to one of
the **13** `_ret`-setting functions and every `$_ret` read, in file order:
**every call is followed on the very next line by a copy into a local**, with
no second guard call in between — `:1341/1342` and `:1343/1344` (the two
`headings` calls), `:1462/1463` (`missing_headings` in `main`, cr20's MINOR-2,
now fixed), and the twenty others. **No clobber exists and I could not construct
one.** My own grep for a direct test finds none:

```bash
$ grep -nE '\[\[?[^]]*\$_ret|^[[:space:]]*case[[:space:]]+"?\$?_ret' tools/orchestrator-guard.sh
(no output)
```

**M-D** (`if [ -n "$_ret" ]` reintroduced at `:1464`) kills test 111.

### The header's symlink note (item 5)

Present at `tools/orchestrator-guard.sh:74-79`:

```
# either (MINOR 8: stated here, not silently assumed). Known gap, carried from
# main and out of scope: a removal THROUGH a symlink that points INTO the plans
# directory (`rm plans-link/x.md`, where `plans-link` → `docs/superpowers/
# plans`) allows here and on main alike — the guard judges a symlink FROM the
# plans dir outward (the write's real target), not a link whose name sits
# outside while its target is inside (a CR2 follow-up if the operator wants it).
```

Both prose contracts now say *subshell*, not *command substitution*
(`tools/orchestrator-guard.sh:81-89`, `docs/runbooks/session.md:114-121`), and
both are true of the shipped file.

## Timing

Median of five whole-hook calls, five independent rounds per case, harness
shaped like the bats test (`$EPOCHREALTIME` around the same pipe), host load
3.66 on 24 cores, seats live.

| command | main (cr20) | head, five medians | cap | met |
|---|---|---|---|---|
| **200 path tokens** | 62 ms | **77, 77, 79, 78, 78** | 100 ms | yes |
| **200 symlink tokens** | 369 ms | **87, 87, 87, 87, 90** | 200 ms | yes |

Both bats timing tests pass on their own (`--filter timing` → `1..2`, 2 ok).
**C17-M-D** (the O(n²) `${s:i:1}` tokeniser restored) kills test 53, so the cap
is genuinely pinned. The runbook carries **no measured figures**: `grep -nE
'[0-9]+ ?ms' docs/runbooks/session.md` returns exactly three hits — `**100 ms**`,
`**200 ms**` and the `<300 ms` budget — plus the measuring command.

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| check | command | rc | result |
|---|---|---|---|
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **0** | clean, no output |
| bats 91 | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | **0** | `1..119`, **119 ok**, no `not ok` |
| bats timing | `… --filter timing` | **0** | `1..2`, 2 ok |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **0** | **426/426** |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **0** | `Found 0 warnings and 0 errors` |
| pre-commit | `nix develop -c githooks/pre-commit` | **1** → **0** | rc 1 only on `tasks: docs/OPERATIONS.md queue block was stale`; **rc 0** once the regenerated board is staged (the board is not in `touches`) — structural, as in every prior gate |
| MAP | `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | **0** | **identical**; the only change is `tests/unit` 15 → 16 files |

Working tree left clean (`git status --porcelain` empty) after every experiment;
`md5sum tools/orchestrator-guard.sh` = `7d154da7f406e25593b32568661c3687`,
matching `HEAD:tools/orchestrator-guard.sh`.

Commit convention: one commit on the base; subject byte-identical to the plan's
(`cmp` of `git log -1 --format=%s` against the plan line → identical); both the
`Generated-By` and `Co-Authored-By: Claude Fable 5.1` trailers; six files
touched, five of them the section's `touches` and `docs/MAP.md` by rule; no
board commit.

## Red before green

CR2r3's guard **and** CR2r3's 416-row fixture (`git -C
/home/dalhaka/factory/ws/cr20/CR2r3 show task/CR2r3:…`) copied over the clone's,
CR2r3b's tests kept. Tree asserted changed (`git diff --numstat` →
`17 39 tools/orchestrator-guard.sh`, `1 27
tests/unit/91-orchestrator-guard-sweep.txt`), bats run, restored, re-run green.

```
1..119
not ok 110 no guard function is called inside any subshell form (structural)
not ok 111 no line tests $_ret directly — every guard call copies it to a local first
not ok 117 a fault in every guard function denies on every arm (behavioural loop)
not ok 118 a fault in headings on a heading-removing Edit denies (guard fault)
not ok 119 the sweep holds every command in the cr17 and cr18 review tables
```

with the named diagnostics

```
# functions called in a subshell form: headings                          (110)
# headings fault ALLOWED on a payload                                    (117)
# command from a review table missing from the sweep: git clean -f; ls   (119)
```

**All four tests the plan's step 1 names go red, each for the reason the plan
gives**; 111 goes red on the `:1441` direct-`$_ret` site the gate flagged, and
118 is the isolated `headings` injection. Five `not ok`, no vanishing TAP
entries. After `git checkout --`, tree clean and **119/119** green.

## Mutation table

Each mutation applied by content anchor (`…/g21/mut*.py`), the tree asserted
changed (`numstat` printed per row), the full bats file run, then reverted;
`git status --porcelain` empty and the guard's md5 back to `7d154da7…` after
every row. **22 applied, 22 killed.**

### This round's — the plan's four plus the brief's three

| # | mutation | numstat | bats rc | killed |
|---|---|---|---|---|
| **M-A** | `<(headings …)` restored in `missing_headings` | 1+/10− | **1** | **110 117 118** + 9 rule tests — the loop **and** the structural scan, exactly as the plan says |
| **M-B** | a guard function moved to the right of a pipe (`printf … \| json_string …` at `:1411`) | 1+/1− | **1** | **110 117 118** + 16 more |
| **M-C** | one review row (`git clean -f; ls`) removed from the fixture | 0+/1− | **1** | **107 119** |
| **M-C2** | `# rows: 441` (header off by one) | 1+/1− | **1** | **107** |
| **M-D** | a direct `[ -n "$_ret" ]` test reintroduced at `:1464` | 1+/1− | **1** | **111** |
| **M-E** | the five `docs/runbooks/session.md` copy lines dropped from `flake.nix` | 0+/5− | **1** | `nix build .#checks.x86_64-linux.unit` fails: `not ok 369 the sweep fixture contains every recipe from the runbook's recipe section` |
| **M-F** | the `EXIT` trap removed from `main` (`:1356`) | 1+/1− | **1** | **99 100 101 102 103 104 105 106 117 118** — every fault test, the whole loop included |

### Prior rounds re-applied — all still die

| # | mutation | numstat | bats rc | killed |
|---|---|---|---|---|
| c20-M-A | `reason=$(bash_verdict …; printf '%s' "$_ret")` restored | 1+/2− | 1 | **99 100 101 110 117** |
| c20-M-C | the trap line deleted from `main` | 0+/1− | 1 | **99–106 117 118** |
| c20-M-C3 | the trap moved back to source time (file scope) | 1+/0− | 1 | **112** (the trap-at-source test) |
| c20-M-D | one recipe (`git add -A`) removed from the fixture | 0+/1− | 1 | **107 108** |
| c20-M-E | a nested-`cwd` payload inserted in the bats file | 1+/0− | 1 | **113** |
| C15-A | the plans entry deleted from `PROTECTED_PATHS` | 0+/1− | 1 | **27 tests** (16 17 18 22 24 25 28 30 31 33–36 43–48 80 87 89 97 104 105 117 118) |
| C15-B | the override entry deleted | 0+/1− | 1 | **24 tests** (55 57–60 62–69 71 72 74 78 80 82 84 88 92 97 117) |
| C15-K | the lift flag ignored | 1+/1− | 1 | **77 86** |
| C17-M-D | the O(n²) `${s:i:1}` tokeniser restored | 1+/1− | 1 | **53** (the 100 ms cap) |
| LOOKAHEAD-`&` | `:-` removed at the `'&'` lookahead | 1+/1− | 1 | **97 98 107** |
| LOOKAHEAD-`\|` | the same at `'\|'` | 1+/1− | 1 | **97 107** |
| LOOKAHEAD-`>` | the same at `'>'` | 1+/1− | 1 | **97 107** |
| TRAP-UNGATED | the `$st`/`_guard_decided` gates dropped | 0+/2− | 1 | **94 tests** |
| C19-M-F | `dq` dropped from `write_verdict`'s `local` list | 1+/1− | 1 | **115, as a named `not ok`** |

(cr20's M-C2 — a second spelling of the trap move — had no unique anchor in this
tree and was replaced by c20-M-C3, which pins the same property.)

### Gate-authored

| # | mutation | numstat | bats rc | killed |
|---|---|---|---|---|
| M-G-vacuity | the review-table test pointed at `flake.lock` (no tables), to see whether an empty extraction passes vacuously | 2+/2− | 1 | **119** — but see the NOTE: it dies only because `print('\n'.join(sorted(cmds)))` still emits one blank line, which fails `grep -Fxq ""` |

## Findings

**No MAJORs.** No guard function runs in a child process on any verdict path;
no loop cell over guard logic allows; the loop test derives its function list;
no write or removal spelling of a protected path allows that main denies; no
plans-dir regression; no documented recipe refused; both timing caps met on the
median; every mutation the plan names dies; every check green; the commit
convention holds.

### MINOR-1 — the loop excludes four functions, and two of them genuinely allow

`tests/unit/91-orchestrator-guard.bats:1610-1614` carves `main`, `deny`, `warn`
and `_guard_trap` out of the derived list, with a comment saying why, and pins
the remainder at 20. Measured over all 24 (my table above), a fault in `deny`
or in `main` **ALLOWS**, exit 127, no deny JSON:

```
### FN=deny, Bash rm of the override  EXIT=127
STDOUT:
STDERR:
_: line 3: GUARD_FAULT_VAR: unbound variable
orchestrator-guard: guard fault: the guard exited with status 127
_: line 3: GUARD_FAULT_VAR: unbound variable

### FN=main, Bash rm of the override  EXIT=127
STDOUT:
STDERR:
_: line 3: GUARD_FAULT_VAR: unbound variable
```

This is irreducible — replacing the deny primitive or the entry point removes
the very thing under test, and no arrangement of the file can deny afterwards —
and the implementer named it honestly rather than hiding it. It is recorded
because the header (`:80-81`) and the runbook (`:113-115`) still state the
property without qualification ("A guard FAULT fails closed, never open, by
construction"), which is true of the twenty guard-logic functions and not of
`deny`/`main` themselves. A half-sentence in both places would close it. The
plan's "EVERY function the file defines" is the underspecification.

### MINOR-2 — the three payloads never reach `multiedit_after`

All three of its cells DENY on the arm's own rule (`fault=no`), so the loop
never exercises a `multiedit_after` fault. A fourth payload does: with a
MultiEdit payload (`…/g21/loop4.py`) the injection **DENIES with `guard fault`,
exit 0, one guard stderr line**, so the guard itself is sound — only the test's
payload set is short. Adding a MultiEdit payload to the loop makes the totality
claim hold on all four arms. (The same run confirms all 20 functions DENY on the
MultiEdit arm as well, and the no-injection control DENIES.) The plan named three
payloads; this is `missing-case` on the plan, not on the implementation.

### MINOR-3 — the structural scan misses two subshell spellings

The scan covers `$(`, backticks, `<(`, `>(`, `| name` and `( name` — the five
the plan enumerated. It does **not** cover `name args | …` (a guard function on
the *left* of a pipe) or `name args &`, both of which run in a child process
exactly like the site cr20 caught. The file has zero of either today (my own
audit), and the behavioural loop would catch either (M-B, which moves
`json_string` to the right of a pipe, kills 117 as well as 110), so this is a
hint-test gap, not a hole. Two more `grep -oE` lines would close it.

### MINOR-4 — the documented symlink gap also has an Edit/Write spelling

The header's known-gap paragraph names `rm plans-link/x.md`. Measured, the
Edit-tool spelling through the same symlinked directory —
`{"tool_name":"Edit","tool_input":{"file_path":"<proj>/plans-link/x.md",
"old_string":"### A1 (code, S) — first task\n","new_string":""}}` — also
**ALLOWS**, on head and on main alike. The cause is one line:

```bash
# tools/orchestrator-guard.sh:598-608
canon_path() {
  …
  if [ -L "$p" ]; then
    _canon=$(realpath -m -- "$p")
```

`[ -L ]` tests only the *leaf*, so a symlink in the middle of the path is never
resolved. A leaf symlink to the plan (`leaf-plan-link`) is resolved and DENIES,
on head and main both, so the sentence at `:68-70` ("a symlink INTO the plans
dir … cannot dodge the plan rules") is right about the case it means. Not a
regression, and item 5 ordered the gap stated rather than fixed — but the note
says "a removal", and the hole is wider than removal.

### NOTE — `flake.nix` adds eleven lines, not the five item 6 names

Six of them copy the two byte-frozen review files into the `unit` sandbox, which
item 3's new test needs; they are correct, minimal and inside the section's
`touches`, so there is no convention breach. Recorded because the plan text says
"the five lines".

### NOTE — the review-table pin survives an empty extraction only by accident

`tests/unit/91-orchestrator-guard.bats:1651-1730` reads `$extracted` line by
line and asserts `missing -eq 0`; there is no `[ -s "$extracted" ]` and no
lower-bound count. M-G-vacuity (both review paths repointed at `flake.lock`)
still fails — but only because the heredoc's `print('\n'.join(sorted(cmds)))`
emits one blank line for an empty set, and `grep -Fxq ""` finds no empty line in
the sweep. One `[ "$(wc -l <"$extracted")" -ge 50 ]` would make the pin
deliberate instead of lucky.

### NOTE — environment

The session scratchpad is shared with other sessions on this host: a file I had
written there (`mkfix.sh`) was overwritten mid-run by another process writing an
unrelated fixture script to the same path. I verified my fixture and every
captured result byte for byte before continuing and moved my drivers under
`…/scratchpad/g21/`; no measurement in this review used the replaced file.

### NOTE — the implementer's claims, checked

| claim | verdict |
|---|---|
| "both MAJORs fixed (headings main-shell + `_ret` local)" | **true** — `headings` runs in the main shell on both sides, its fault DENIES with `guard fault`; `:1462-1463` copies to `reason` before the test; my own audit finds 0 guard callees in any subshell form |
| "sweep at 442 rows pinned to cr17/cr18 tables" | **true** — `# rows: 442` = 442 data rows; my independent extraction of both reviews (58 narrow / 63 broad commands) finds **0** missing; M-C and M-C2 kill the pins |
| "unit 426/426 and lint green" | **true** — plus shellcheck 0, bats 119/119, MAP byte-identical, pre-commit rc 0 once the board is staged |
| the loop is behavioural and total | **true for the 20 that are guard logic**; four fault-channel functions are excluded (MINOR-1) and the three payloads miss `multiedit_after` (MINOR-2) |
| the structural scan is widened | **true for the five forms the plan lists**; left-of-pipe and `&` are still unscanned (MINOR-3) |
| commit conventions | **clean** — one commit, subject byte-identical, both trailers, every file inside `touches` or MAP by rule |

## Verdict

**APPROVED.**

The round does what cr20 asked and does it structurally rather than site by
site. `missing_headings` no longer runs a guard function in a child process:
`headings` returns through `_ret`, is called twice in the main shell, and only
`printf` stands inside the two process substitutions `comm` reads. My own
audit across eight subshell spellings — including the two the widened test does
not scan — finds **zero** guard-function callees anywhere in a child process,
and the behavioural loop I ran outside bats over every one of the 24 defined
functions × 3 payloads DENIES in all 60 cells that belong to guard logic, with
exit 0 and one guard-authored stderr line wherever the fault is on the path.
The exact payload that ALLOWED silently on CR2r3 now denies with
`guard fault: the guard exited with status 127`. The loop test derives its
list from the file's own `^name()` lines and would cover a function added
tomorrow; the `_ret` discipline holds at every one of the twenty-two call
sites and cr20's MINOR-2 is gone; the sweep grew to 442 rows, absorbed the
historic corpus cr20 flagged, and is now pinned to two byte-frozen reviews
whose tables I extracted myself with a broader extractor than the test's and
found fully present; 47 of 47 recipes allow; the seventeen spellings deny;
missing evidence still allows silently in fourteen shapes; the trap is on the
entry path only; both timing caps are met on five of five medians with room to
spare; `flake.nix` is inside `touches`; and **22 of 22** mutations die,
including all fourteen carried forward from cr15 through cr20.

The four MINORs are worth folding into the next CR2 task that opens this file,
none of them blocking: qualify the two prose contracts so the fail-closed claim
excludes `deny`/`main` (MINOR-1); add a MultiEdit payload to the loop so
`multiedit_after` is actually exercised (MINOR-2); add `name |` and `name &` to
the structural scan (MINOR-3); widen the header's symlink note past "a removal"
to the Edit/Write spelling, or fix `canon_path` to canonicalise the whole path
(MINOR-4). The plan's item 1 asked for something no shell program can deliver
for its own deny primitive, and its three payloads left one function unreached —
that is the plan defect, recorded as `underspecified` / `missing-case`; the
implementation handled both honestly and in the open.
