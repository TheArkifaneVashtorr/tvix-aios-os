---
reviewer: opus
majors: 1
minors: 7
mutants_total: 30
mutants_killed: 30
---
# Opus gate — seat run cr19, task CR2r2b — REJECTED

## Summary

One commit (`eeb558a`) on base `b361dca` (main), branch `task/CR2r2b` in
`/home/dalhaka/factory/ws/cr19/CR2r2b`. Reviewed in a fresh clone at
`…/scratchpad/gate-cr19-CR2r2b`; nothing under `/home/dalhaka/factory` was
modified and the live repo's `.claude/ritual-override` was never touched — every
guard run drove a throwaway fixture at `…/scratchpad/fix/proj`.

**The cr18 MAJOR is genuinely fixed.** All seventeen allowing spellings now DENY,
with **empty stderr on every one**:

```
                                              main   CR2r2   CR2r2b
rm -rf .claude/ritual-override &              DENY   allow   DENY
rm -rf .claude/ritual-override&               DENY   allow   DENY
rm -rf .claude &                              DENY   allow   DENY
rm docs/superpowers/plans/x.md &              DENY   allow   DENY
sed -i s/a/b/ docs/superpowers/plans/x.md &   DENY   allow   DENY
rm -rf docs/superpowers/plans &               DENY   allow   DENY
git clean -fd &                               DENY   allow   DENY
git stash -u &                                allow  allow   DENY
touch/cp/tee/echo-redirect <override> &       allow  allow   DENY ×4
{ rm -rf .claude/ritual-override; } &         DENY   allow   DENY
rm -rf .claude/ritual-override; ls &          DENY   allow   DENY
rm -rf .claude/ritual-override | / > / 1>     DENY   allow   DENY ×3
```

Nothing else moved: over the 390-row committed sweep fixture, head differs from
CR2r2 on **exactly those seventeen rows and nothing else**. Zero of 672 driven
rows (390 fixture + 232 historic + 50 recipes) wrote a byte to stderr. Zero rows
where main DENIES and this tree allows, except the two `sed -n … | grep` rows the
CR2r narrowing already withdrew (`sed -n '1,30p' <plan> | grep -i CR2`, recorded
by cr17/cr18). 50 of 50 documented recipes ALLOW. Checks are green — shellcheck
rc 0, bats **104/104**, `unit` **403/403** (fresh and `--rebuild`), `lint` pass,
`docs/MAP.md` reproduces byte for byte. Commit conventions are clean: one commit,
subject byte-identical to the plan line (`cmp` → identical), both trailers, and
the two files outside `touches` are exactly what the brief allows —
`docs/MAP.md` changed by rule (`tests/unit` 15 → 16 files, nothing else) and
`tests/unit/91-orchestrator-guard-sweep.txt` is the test asset the bats file
reads. All 21 re-applied cr15/cr17/cr18 mutations still die; all 9 of this
round's mutations die. Six tests go red on CR2r2 and green on head.

It is rejected on **one MAJOR**: the fault-deny mechanism the plan's item 2
specified as covering *every* `reason=$(…)` command substitution over a verdict
function covers only two of the three. The outermost one — `reason=$(bash_verdict
…)` in `main` (`tools/orchestrator-guard.sh:1356`) — has no status check, so a
fault anywhere in `bash_verdict` outside the two inner substitutions drops the
whole Bash rule set and **ALLOWS**, silently, with no guard-authored line. The
EXIT trap cannot catch it (`main` returns 0). Demonstrated below on
`rm -rf .claude/ritual-override`.

Method: fresh clone (`git clone -q --branch task/CR2r2b …`); the guard driven
only from extracted copies (`…/scratchpad/guards/{head,main,cr2r2}.sh`) with
`env CLAUDE_PROJECT_DIR=<fixture> bash <guard>` on compact `ensure_ascii=False`
payloads carrying `cwd` at the **top level**, stdout and stderr captured
separately on every run. Fixture: a git repo with
`.claude/{ritual-override,settings.json,worktrees/x}`,
`docs/superpowers/plans/x.md`, `docs/second/plans/y.md`, `docs/notes/plans/x.md`
(decoy), `k`, `sub/`, `elsewhere/ritual-override`, `link-to-override` → the
override, `plans-link` → the plans dir, 200 `link<N>` symlinks, plus
`…/fix/other/.claude/ritual-override` outside the project and `…/fix/nogit` (a
non-repo). Drivers: `…/scratchpad/{mkfix.sh,gdrive.py,fault.sh,fault2.sh,
minors.sh,edit19.py,timing.py,timing.sh,cover.py,mut19.py,runmut19.sh}`; case
files `c17.tsv`, `adv19.tsv`, `fixture.tsv`, and the cr18 gate's `sweep.tsv`
(232 historic rows) and `recipes.tsv` (50). ~750 payloads, each replayed against
`main` (`b361dca:tools/orchestrator-guard.sh`, 723 lines) and CR2r2
(`git -C /home/dalhaka/factory/ws/cr18/CR2r2 show task/CR2r2:…`, 1372 lines) so
every difference is attributed.

## Faults and the trap

The two mechanisms the plan asked for are both present and both work.

```bash
# tools/orchestrator-guard.sh:107-119
_guard_active=0
_guard_decided=0
_guard_trap() {
  local st=$?
  [ "$_guard_active" -eq 1 ] || return 0
  [ "$st" -eq 0 ] && return 0
  [ "$_guard_decided" -eq 1 ] && return 0
  warn "guard fault: the guard exited with status $st"
  deny "guard fault: the guard exited with status $st"
  exit 0
}
trap _guard_trap EXIT
```

```bash
# tools/orchestrator-guard.sh:494-511 (both inner substitutions checked)
  reason=$(git_verdict "$command")
  st=$?
  if [ "$st" -ne 0 ]; then
    warn "guard fault: git_verdict failed (status $st)"
    printf '%s' "guard fault: git_verdict failed (status $st)"
    return 0
  fi
  …
  reason=$(write_verdict "$command" "$project_dir" "$cwd")
  st=$?
  if [ "$st" -ne 0 ]; then …
```

Injections, all without editing the guard (`source` + an override function that
reads an unbound variable under `set -u`, then `main <<< "$payload"`):

| injected fault | path | stdout | exit | guard's own stderr |
|---|---|---|---|---|
| `tokenise_ctx` (harmless Bash payload) | inside `write_verdict`'s substitution | **DENY** `guard fault: write_verdict failed (status 1)` | 0 | 1 line |
| `git_verdict` | its own substitution | **DENY** `guard fault: git_verdict failed (status 1)` | 0 | 1 line |
| `write_verdict` (protected payload) | its own substitution | **DENY** `guard fault: write_verdict failed (status 1)` | 0 | 1 line |
| `lex_norm` (protected payload) | inside `write_verdict` | **DENY** `guard fault: write_verdict failed (status 1)` | 0 | 1 line |
| `is_plan_file` (Edit payload) | **main shell**, called directly at `:1383` | **DENY** `guard fault: the guard exited with status 127` | 0 | 1 line |
| `deny` itself (protected payload) | main shell | allow (nothing can be printed) | 0 | trap line present |
| **`bash_verdict`** (protected payload) | **`main`'s own substitution, `:1356`** | **ALLOW** | 0 | **none** |
| `json_unescape` (protected payload) | `main`'s substitution at `:1356` | **ALLOW** | 0 | none |
| `json_string` (Bash payload) | `main`'s substitution at `:1348` | allow (`malformed hook input`) | 0 | 1 line |
| `resolve_path` (heading-removing Edit) | `main`'s substitution at `:1366` | **ALLOW** | 0 | none |
| `missing_headings` (heading-removing Edit) | `main`'s substitution at `:1408` | **ALLOW** | 0 | none |

(The second stderr line in each row is bash's own `GUARD_FAULT_VAR: unbound
variable`, emitted by the shell, not by the guard; the guard writes exactly one
line of its own, as the contract asks.)

Missing evidence still ALLOWS, with **empty stderr and exit 0** in every case:

| case | verdict | stderr |
|---|---|---|
| project dir is not a git repository (`…/fix/nogit`), protected command | DENY (the rule fires lexically — no git evidence needed) | empty |
| project dir does not exist | allow | empty |
| payload without `cwd`, harmless command | allow | empty |
| payload without `cwd`, protected command | DENY (correct — the path is project-relative) | empty |
| `command` is an object `{"a":1}` | allow | empty |
| `command` is a number `123` | allow | empty |
| empty payload / malformed payload / no `tool_name` | allow | 1 `warn` line (`malformed hook input (allowing)`) — by design |
| ordinary non-zero helpers: `git status` in a non-repo, `grep -q zzz k`, Edit on a non-existent file, an unknown tool | allow ×4 | empty ×4 |

The trap does not fire on any of those: `_guard_active`/`$st`/`_guard_decided`
gate it correctly, and **M-D** (the gate lines removed, so the trap fires on
every exit) makes 94 tests red — the missing-evidence allows among them.

The residual hole is the unchecked outermost substitution:

```bash
# tools/orchestrator-guard.sh:1354-1358 — no `st=$?` here
    Bash | bash)
      reason=$(bash_verdict "$(json_unescape "$(json_string "$payload" command)")" "$project_dir" "$(json_string "$payload" cwd)")
      [ -n "$reason" ] && deny "$reason"
      return 0
```

See MAJOR-1.

## Rule behaviour

Fixture `<proj>` = `…/scratchpad/fix/proj`; every payload carries `cwd` at the
top level; stderr captured on every run and **empty** unless the row says
otherwise.

### The seventeen spellings + the operator-only and degenerate rows (45 rows, 0 stderr)

| spelling | main | CR2r2 | CR2r2b |
|---|---|---|---|
| `rm -rf .claude/ritual-override &` | DENY | allow | **DENY** |
| `rm -rf .claude/ritual-override&` | DENY | allow | **DENY** |
| `rm -rf .claude &` | DENY | allow | **DENY** |
| `rm docs/superpowers/plans/x.md &` | DENY | allow | **DENY** |
| `sed -i s/a/b/ docs/superpowers/plans/x.md &` | DENY | allow | **DENY** |
| `rm -rf docs/superpowers/plans &` | DENY | allow | **DENY** |
| `git clean -fd &` | DENY | allow | **DENY** |
| `git stash -u &` | allow | allow | **DENY** |
| `touch .claude/ritual-override &` | allow | allow | **DENY** |
| `cp k .claude/ritual-override &` | allow | allow | **DENY** |
| `tee .claude/ritual-override &` | allow | allow | **DENY** |
| `echo x > .claude/ritual-override &` | allow | allow | **DENY** |
| `{ rm -rf .claude/ritual-override; } &` | DENY | allow | **DENY** |
| `rm -rf .claude/ritual-override; ls &` | DENY | allow | **DENY** |
| `rm -rf .claude/ritual-override \|` | DENY | allow | **DENY** |
| `rm -rf .claude/ritual-override >` | DENY | allow | **DENY** |
| `rm -rf .claude/ritual-override 1>` | DENY | allow | **DENY** |

Degenerate and operator-only commands — none raises:

| command | CR2r2 | CR2r2b |
|---|---|---|
| `&` / `\|` / `>` (only an operator) | allow, **raises** ×3 | allow ×3, silent |
| the empty command | allow | allow |
| `&&` / `\|\|` / `>>` / `>\|` / `;` alone | allow ×5 | allow ×5 |
| `k` (single character) | allow | allow |
| `rm -rf <override>` + `&&` / `\|\|` / `>>` / `>\|` / `;` | DENY ×5 | DENY ×5 |
| `rm -rf <override> 2>` | allow, raises | **DENY** |
| `{ rm -rf <override>; }` / `(rm -rf <override>)` | DENY ×2 | DENY ×2 |

30 further adversarial trailing shapes (`&&&`, `\|\|\|`, `>>>`, `&\|`, `>&`,
`&>`, a trailing `\`, `"`, `'`, backtick, tab, newline; `2>&1 &`, `2>&1 \|`,
`nohup … >/dev/null 2>&1 &`, `( … ) &`, `&`+newline, `\|`+newline, `>`+newline)
— **0 stderr, 0 surprises**; the protected rows all DENY, the bare-operator rows
all allow, `echo "unterminated &` allows (the tail is inside a quote and names
nothing protected).

### The two pathspec-limited rows (item 2)

| spelling | main | CR2r2 | CR2r2b |
|---|---|---|---|
| `git clean 'a\|b' -f` | allow | allow | allow — by design |
| `git stash 'a\|b' -u` | allow | allow | allow — by design |

`docs/runbooks/session.md:216-221` now records them explicitly ("Two narrow
**accepted allows** remain by design … the quote fix narrows the clause split, it
does not claim every row denies"), which is what item 5 asked for. Neither
command can reach `.claude/ritual-override` through a pathspec that names
nothing protected.

### Everything CR2r2 established (item 7) — 0 deviations

Re-ran the cr18 gate's three tables (48 + 51 + 25 rows) against head, CR2r2 and
main. Head matches CR2r2 on **every** row except the seventeen above:

- quotes bound clauses: the nine plans spellings and the five override spellings
  DENY; `sed -i 's|a|b|' <plan>` and `sed 's|a|b|' -i <plan>` agree; the four
  allow-controls (`echo 'a;b' && rm /tmp/x`, `echo 'a|b' | cat`,
  `printf '%s\n' 'x;y'`, `git commit -q -m 'guard: rm x; touch y | z'`) allow.
- extracts: the project-root and `.claude`-cwd extracts DENY (23 rows, the
  documented over-denial), `-C /tmp` / `-d /tmp` / `tar -tf` allow.
- every `-m` argument exempt, including `-am`, `-m'…'`, `--message='…'`, two
  `-m`s; the newline and `;` spellings after a message still DENY (28 rows).
- one PROTECTED list with no early break (**C15-C** kills 18), the delete family,
  clause-local flags (`rm -f result && git clean` allows), glob spellings,
  `git stash push -u`, directory `chmod`.
- Edit/Write/MultiEdit: the override denies relative, absolute and through
  `link-to-override`; a heading-removing Edit and MultiEdit deny; an appending
  edit, `.claude/settings.json`, the decoy plan and an out-of-project
  `.claude/ritual-override` allow.
- the lift: `ORCHESTRATOR_GUARD=off` in the hook environment → stdout empty, one
  stderr line `orchestrator-guard: lifted by ORCHESTRATOR_GUARD=off`; the same
  string inside the payload → DENY.

### Item 5 — the folded minors

| item | result |
|---|---|
| `_ctx_emit` hoisted **and pinned** | `tools/orchestrator-guard.sh:258` vs `tokenise_ctx()` at `:269`; test 102 asserts the order; **M-E** (moved back inside) kills it |
| `dq sq dqd sqd` local | `:665` `local raw i j t dq sq dqd sqd`; after a sourced `write_verdict` run (harmless *and* override-reaching) `declare -p` fails for all four; **M-F** kills test 103 |
| the old nested-`cwd` test | `tests/unit/91-orchestrator-guard.bats:577` now carries `cwd` at the top level ✓ (one such payload remains at `:844` — MINOR-4) |
| a quoted newline is a newline | `tokenise_ctx $'echo "a\nb"'` → `toks[1]` = `$'a\nb'` (verified directly); **M-G** kills test 104 |
| the runbook amendments | present (`:90-97` the fault contract, `:216-221` the two accepted allows, `:226-233` the timing and the bounded lookahead) |

### Item 6 — the sweep

`tests/unit/91-orchestrator-guard-sweep.txt`: **390 rows**, no blanks, no
comments, **no duplicates**; all seventeen spellings present (rows 214-230). Ran
it myself through the guard: **0 rows with any stderr**, 0 rows where main
DENIES and head allows other than the two documented `sed -n … | grep`
narrowings. The bats test (`:1330-1350`) reads it line by line, captures stderr
per row, and fails on the first non-empty one — proven by **M-A**, which prints:

```
not ok 101 the guard never raises — every historic row, recipe and spelling is stderr-silent
# row 214 raised: rm -rf .claude/ritual-override &
# …/tools/orchestrator-guard.sh: line 303: chars[i + 1]: unbound variable
# orchestrator-guard: guard fault: write_verdict failed (status 1)
```

Note that under M-A the row now *denies* (the fault-deny catches it) and the
sweep still fails — the "never raises" proof is independent of the verdict, which
is exactly right.

The fixture is **not literally** the union the contract names. Against the cr18
gate's own corpora it misses 34 of 225 single-line historic rows (`rm
.claude/ritual-override`, `rm -- .claude/ritual-override`, `unlink …`, `: >
…`, `echo x >| …`, `sh -c "rm …"`, `git rm -f …`, `rm plans-link/x.md`,
`sed --in-place …`, the six bare `git stash` subcommands, …) and 31 of 49
recipes (`nix flake check -L`, `evidence bundle --markdown`, `git cherry-pick -n
FETCH_HEAD`, `nix store diff-closures …`, `dsh-openrouter --denials 5`, …); the
8 multi-line rows cannot be expressed in a line-per-row file at all. It is
larger than the historic corpus (390 vs 233) and I drove every missing row
myself with zero stderr, so this is a MINOR, not a hole (MINOR-5).

## Over-denial audit

**50 of 50** documented recipes ALLOW, with empty stderr, identical to main on 49
and better than main on one (`nix develop -c git commit -q -m "<prose naming rm,
.claude and a plan path>"`: main DENY → allow). **No documented recipe is
refused.**

New over-denials introduced by this commit relative to CR2r2: **none**. Head vs
CR2r2 over the 390-row fixture differs on exactly 17 rows, all of them the
intended fixes. Over the 232 historic rows head and main agree on every DENY
main makes.

Over-denials carried forward, all recorded in the runbook and none a documented
recipe: the project-root extract with no `-C`/`-d`, `rm -rf .claude/worktrees/*`,
`git checkout --`, `echo "git commit --amend"`, `ls .claude && rm /tmp/x`.

No run in the whole corpus produced a spurious `guard fault` denial: a fault
verdict always writes a `warn` line, and stderr was empty on all 672 corpus rows
plus the 45 spelling rows and the 30 adversarial rows.

## Timing

Median of five whole-hook calls, host load 1.86–2.09 / 24 cores, seats live.
Two harnesses: a python driver, and a bash harness with `$EPOCHREALTIME` around
the same pipe the bats tests use.

| command | main | CR2r2b (python harness, 4 rounds) | CR2r2b (bats-shaped harness, 3 rounds) | cap | met |
|---|---|---|---|---|---|
| `git status` (baseline) | 18.6 ms | 21.0 / 20.8 / 21.2 / 21.4 | — | — | — |
| **200 path tokens** | 60.3 ms | **95.8 / 94.3 / 96.0 / 96.8** | **95.0 / 96.9 / 95.2** | 100 ms | yes, 3–6 ms |
| **200 symlink tokens** | 297.1 ms | **89.1 / 90.3 / 89.7 / 91.5** | **89.4 / 90.5 / 90.0** | 200 ms | yes |
| `rm` × 200 symlink tokens | 268.2 ms | 91.5 / 89.7 / 90.2 / 90.9 | 91.5 / 89.2 / 89.8 | — | yes |

Both caps are met on every one of the seven medians I took, and both bats timing
tests pass. The runbook (`docs/runbooks/session.md:229-231`) says **88 ms** and
**83 ms** "measured in the CR2r2b workspace at 1-min load ~1.8 on 24 cores". I
cannot reproduce either on this tree at that load: 94.3–96.9 ms and 89.1–91.5 ms.
The path figure moved 91 → 88 (further from what I measure); the symlink figure
**83 ms is byte-identical** to the number cr17 flagged as carried over from CR2r
and cr18 flagged again — the exact carry-over item 4 asked this round to fix
(MINOR-2).

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| check | command | rc | result |
|---|---|---|---|
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **0** | clean |
| bats 91 | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | **0** | `1..104`, **104 ok**, no `not ok` |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link` | **0** | `1..403`, **403/403** |
| unit (rebuild) | `… --rebuild` | **0** | same |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **0** | pass |
| pre-commit | `nix develop -c githooks/pre-commit` | **1** → **0** | treefmt 94 files, **0 changed**, `All checks passed!`; rc 1 only on `tasks: docs/OPERATIONS.md queue block was stale`; **rc 0** once the regenerated board is staged (the board is not in `touches`) — structural, as in every prior gate |
| MAP | `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | **0** | **identical** to the committed file |

Working tree left clean (`git status --porcelain` empty) after every experiment;
the guard's md5 matches `HEAD:tools/orchestrator-guard.sh`.

## Red before green

CR2r2's guard (`git -C /home/dalhaka/factory/ws/cr18/CR2r2 show
task/CR2r2:tools/orchestrator-guard.sh`, 1372 lines) copied over the clone's
guard, CR2r2b's tests kept. Tree asserted changed (`git diff --numstat` →
`8 49 tools/orchestrator-guard.sh`), bats run, restored, re-run green.

```
1..104
not ok  97 the operator lookahead is bounded — the seventeen trailing-&, | and > spellings deny
not ok  99 a fault inside the verdict substitution denies, not allows (guard fault)
not ok 100 a fault in the main shell denies via the EXIT trap (guard fault)
not ok 101 the guard never raises — every historic row, recipe and spelling is stderr-silent
not ok 103 write_verdict does not leak dq/sq/dqd/sqd into the global namespace
not ok 104 a quoted newline stays a newline character in the token, not a space
```

with, on 101:

```
# row 214 raised: rm -rf .claude/ritual-override &
# …/tools/orchestrator-guard.sh: line 278: chars[i + 1]: unbound variable
```

Six of the eight new tests are red on CR2r2 — the trailing-operator rows, both
fault injections, the sweep with the unbound-variable line, the `local` leak and
the quoted newline. **98** (the `;`/`&&`/`||`/`>>` and `nix build … &` control)
and **102** (the `_ctx_emit` hoist, which CR2r2 already had) pass on CR2r2
honestly; 102 exists to pin the hoist against **M-E**, and it does. After
`git checkout --`, `git status --porcelain` empty and 104/104 green.

## Mutation table

Each mutation applied by content anchor to `tools/orchestrator-guard.sh` in the
clone, the tree asserted changed (`numstat` printed per row), the full bats file
run, then reverted; `git status --porcelain` empty after every batch
(`ALL REVERTED: []`). Scripts: `…/scratchpad/{mut19.py,runmut19.sh}`.

### This round's nine

| # | mutation | numstat | bats rc | killed |
|---|---|---|---|---|
| **M-A** | `:-` removed at the `'&'` lookahead (`:303`) | 1+/1− | **1** | 97 98 101 |
| **M-A2p** | the same at `'\|'` (`:304`) | 1+/1− | **1** | 97 101 |
| **M-A2g** | the same at `'>'` (`:305`) | 1+/1− | **1** | 97 101 |
| **M-B** | the `EXIT` trap removed (`:119`) | 1+/1− | **1** | **100** (the main-shell injection allows) |
| **M-C** | both substitution status checks removed (`:495-500`, `:506-511`) | 2+/10− | **1** | **99** (the subshell injection allows) |
| **M-D** | the trap made unconditional (`$st`/`_guard_decided` gates dropped) | 0+/2− | **1** | **94 tests**, the missing-evidence allows among them |
| **M-E** | `_ctx_emit` moved back inside `tokenise_ctx` | 10+/10− | **1** | 102 |
| **M-F** | `dq` dropped from `write_verdict`'s `local` list (`:665`) | 1+/1− | **1** | 103 (see MINOR-3: reported only as `Executed 103 instead of expected 104`) |
| **M-G** | the quoted newline emitted as a space again (`:345`) | 1+/1− | **1** | 104 (same reporting caveat) |

All nine behave as the plan demands. **M-F** and **M-G** kill their test — bats
exits 1 and the test vanishes from the TAP stream — but neither prints a
`not ok` line; see MINOR-3.

### cr18's / cr17's / cr15's twenty-one, re-applied — all still die

| # | mutation | numstat | fails | killed by |
|---|---|---|---|---|
| C15-A | the plans entry deleted from `PROTECTED_PATHS` | 0+/1− | 23 | 16 17 18 22 24 25 28 30 31 33 34 35 36 43–48 80 87 89 **97** |
| C15-B | the override entry deleted | 0+/1− | 23 | 55 57–60 62–69 71 72 74 78 80 82 84 88 92 **97** |
| C15-C | the PROTECTED loop `break`s after the first entry | 1+/0− | 18 | 55 60 62–64 66–68 71 72 74 78 80 82 84 88 92 **97** |
| C15-D | the glob/raw-text fallback disabled | 1+/1− | 1 | 71 |
| C15-E | `git stash -u`/`-a` dropped from the family | 1+/1− | 3 | 72 81 **97** |
| C15-F | `tar` dropped from the extract arm | 1+/1− | 4 | 72 82 88 92 |
| C15-G | `git clean -n` treated like `-f` | 1+/1− | 1 | 73 |
| C15-H | the `-m` exemption removed | 1+/1− | 3 | 75 94 95 |
| C15-I | the batched `realpath` replaced by per-token resolution | 1+/1− | 1 | 54 |
| C15-K | the lift flag ignored | 1+/1− | 2 | 77 86 |
| C17-B2 | stash subcommand words taken as pathspecs | 0+/1− | 1 | 81 |
| C17-C2 | the extract cwd check removed | 1+/1− | 3 | 82 88 92 |
| C17-D2 | whole-command flag attribution restored | 1+/1− | 1 | 83 |
| C17-E2 | directory `chmod` not denied | 1+/1− | 1 | 84 |
| C17-F2 | a `break` in main's Edit/Write loop | 1+/0− | 1 | 85 |
| C17-G2 | the lift's stderr line removed | 1+/1− | 1 | 86 |
| C17-M-B | the `-m` loop's `break` restored | 1+/0− | 1 | 94 |
| C17-M-C | extracts at the project root allowed | 1+/1− | 2 | 88 92 |
| C17-M-D | the O(n²) `${s:i:1}` form restored | 1+/1− | 1 | **53** (the 100 ms cap) |
| C17-M-E | the raw-text plan fallback back to the literal | 1+/1− | (rc 1) | **96** — vanished from TAP, MINOR-3 |
| X-SHFMT | `canon_result` write respelled `[$i / $bi]` | 1+/1− | 55 | 5 6 8 10 12 15–19 22 23 43–51 55 56 60 62–68 70–75 78 80–84 87–95 97 98 101 |

**Twenty-one of twenty-one prior mutations die; with this round's nine, thirty of thirty.**

## Findings

### MAJOR-1 — `main`'s own verdict substitution has no status check, so a fault in `bash_verdict` ALLOWS what it must deny

The plan's item 2: *"every `reason=$(…)` command substitution over a verdict
function checks its status and denies on non-zero with the same reason"*. Three
such substitutions exist. Two are checked (`:494-500`, `:505-511`). The third —
the outermost, the one that wraps the **entire Bash rule set** — is not:

```bash
# tools/orchestrator-guard.sh:1354-1358
    Bash | bash)
      reason=$(bash_verdict "$(json_unescape "$(json_string "$payload" command)")" "$project_dir" "$(json_string "$payload" cwd)")
      [ -n "$reason" ] && deny "$reason"
      return 0
```

Measured, `source`-and-override injection, payload
`{"tool_name":"Bash","cwd":"<proj>","tool_input":{"command":"rm -rf .claude/ritual-override"}}`:

```
== bash_verdict faults (main's own substitution, prot cmd)   ALLOW exit=0
   stdout=<EMPTY>
   stderr=_: line 1: GUARD_FAULT_VAR: unbound variable
== control: no injection, same payload                        DENY  exit=0
   stdout={"…","permissionDecision":"deny","permissionDecisionReason":"the ritual override is the operator's; ask for it"}
```

The `EXIT` trap cannot cover it: only the substitution's subshell dies, `main`
carries on and the script exits 0, so `[ "$st" -eq 0 ] && return 0` at `:112`
returns early. The guard writes **no line of its own** — the only stderr is
bash's raw diagnostic — so the failure is exactly as silent as the cr18 MAJOR
was. The same gap swallows `json_unescape` (`:1356`), and on the Edit/Write arm
`resolve_path` (`:1366`) and `missing_headings` (`:1408`): a fault in any of them
allows a heading-removing Edit on a plan, again silently.

This falsifies the file's own new contract at `:75-82` and the runbook's at
`:90-97`, both of which now assert the general property:

```
# tools/orchestrator-guard.sh:75-82
# Deny-only and never raising: it always exits 0, only ever *adding* a deny
# decision on stdout. A guard FAULT fails closed, never open: an internal error
# that would otherwise abort the shell or silently drop a rule is DENIED, not
# allowed, through two mechanisms — every verdict-function command substitution
# checks its status and reports "guard fault" (denied by the caller), and an
# EXIT trap denies when the shell leaves with a non-zero status and no decision
# has been written.
```

"every verdict-function command substitution checks its status" is false for the
one at `:1356`, and `bash_verdict` is a verdict function by name and by role.
No input I found reaches it today — the body between the two inner calls is
builtins and `[[ =~ ]]` over `PROTECTED` — so this is a robustness gap rather
than a live hole; but it is the precise class of gap this round exists to close,
it is the widest of the three sites, and any future line added to `bash_verdict`
or to `main`'s Bash arm inherits an unguarded fail-open. No test pins it.

Fix shape: `st=$?` after `:1356` (and after `:1366`/`:1408` on the Edit arm),
denying `guard fault: bash_verdict failed (status $st)`; red test first — inject
a fault into `bash_verdict` on a payload that must deny and assert DENY, plus a
mutation that removes the new check.

### MINOR-1 — the seat ended with prose and no `FACTORY-RESULT` block

The driver reports the run failed while the commit exists and is complete. Noted
as the process deviation the gate brief asked me to record; it did not affect any
verdict above.

### MINOR-2 — the runbook's timing figures are still not this tree's, and `83 ms` is the same byte-identical carry-over cr17 and cr18 already flagged

`docs/runbooks/session.md:229-231`:

```
single `realpath` call, so a 200-path-token command measures 88 ms and a
200-symlink-token command 83 ms (median of five, `$EPOCHREALTIME` in
tests/unit/91-orchestrator-guard.bats — measured in the CR2r2b workspace at
1-min load ~1.8 on 24 cores)
```

Measured here, seven independent medians of five across two harnesses (one of
them shaped exactly like the bats test), load 1.86–2.09: paths **94.3–96.9 ms**,
symlinks **89.1–91.5 ms**. The path number moved 91 → 88, further from what is
reproducible; the symlink number **did not move at all** — 83 ms is the same
figure cr17 raised as a CR2r carry-over and cr18 raised again, and item 4 of this
plan asked specifically for "the numbers measured in THIS workspace". Both caps
are met on every median, so this is a minor — but the stated path headroom (12 ms)
is about four times the real one (3–6 ms).

### MINOR-3 — the guard's new `EXIT` trap clobbers bats' own, so a failure in any test that sources the guard produces no `not ok` line

`trap _guard_trap EXIT` (`:119`) is installed at file scope, so `source "$GUARD"`
inside a bats test body replaces bats' result-reporting EXIT trap. Five test
bodies source the guard (`tests/unit/91-orchestrator-guard.bats:53` in
`guard_tokens`, `:987`, `:1254`, `:1373`, `:1387`). When such a test fails, its
TAP line disappears entirely:

```
# M-F (the `local` mutation) — test 103 should be `not ok`:
ok 102 _ctx_emit is hoisted to file scope and precedes tokenise_ctx (M-F dies)
ok 104 a quoted newline stays a newline character in the token, not a space
# bats warning: Executed 103 instead of expected 104 tests
```

Same for **M-G** (test 104) and **C17-M-E** (test 96). `bats` still exits 1, so
the `unit` derivation still fails and no mutation escapes — but the operator
gets a count mismatch instead of a named failure and no diagnostics. Fix shape:
in the sourcing tests, `trap - EXIT` immediately after `source "$GUARD"` (or
source in a subshell), with a red test that asserts a deliberate failure in a
sourcing test reports `not ok`.

### MINOR-4 — one nested-`cwd` payload remains

`tests/unit/91-orchestrator-guard.bats:844` still writes
`{"tool_name":"Bash","tool_input":{"command":"rm ritual-override","cwd":…}}` —
the same shape the plan asked to fix at `:577` (which is fixed). It passes only
because `json_string` scans the whole payload for `"cwd"`. Third occurrence of
this defect across cr17/cr18/cr19, one test over each time.

### MINOR-5 — the sweep fixture is not the corpus the contract names, and its row-count pin is loose

Item 3 says the sweep runs "every row of the historic sweep (the review's 233),
the 50 recipes and the seventeen spellings". The committed fixture is 390 rows
and contains all seventeen spellings, but measured against the cr18 gate's own
`sweep.tsv`/`recipes.tsv` it omits 34 of 225 single-line historic rows and 31 of
49 recipes (the 8 multi-line rows cannot be expressed at all). The test's only
size pin is `[ "$row" -gt 300 ]` (`:1349`), so the fixture could lose 89 rows and
still pass. I drove every omitted row myself against this guard: zero stderr,
zero verdict surprises — so nothing is hiding there today.

### MINOR-6 — a fault injection emits two stderr lines, only one of them the guard's

The matrix asked for "exactly one line on stderr". Each injected fault yields
bash's own `GUARD_FAULT_VAR: unbound variable` plus the guard's
`orchestrator-guard: guard fault: …`. The guard writes exactly one line, which is
what the contract governs; the first line is the shell's and is unavoidable for a
`set -u` fault. Recorded, not a defect.

### NOTE — the implementer's claims, checked

| claim | verdict |
|---|---|
| the seventeen spellings deny | **true** — 17/17 DENY, empty stderr, verified against main and CR2r2 |
| the two pathspec rows stay allowed by design and are documented | **true** — runbook `:216-221` |
| "a fault denies" via both mechanisms | **partly true** — both mechanisms work and are pinned by M-B/M-C, but the outermost verdict substitution (`:1356`) is unchecked and allows (MAJOR-1) |
| missing evidence still allows | **true** — 13 cases, allow, empty stderr, exit 0; M-D proves the trap is gated |
| "never raises", proven by a sweep | **true in effect** — 0 stderr over 390 fixture + 232 historic + 50 recipe + 45 spelling + 30 adversarial rows; the fixture is not literally the named corpus (MINOR-5) |
| timing inside the caps, runbook numbers from this workspace | **half** — caps met on all seven medians; the runbook numbers are not reproducible and 83 ms is the third-time carry-over (MINOR-2) |
| the five minors folded | **true** — hoist pinned, locals clean, `:577` reshaped, quoted newline a newline, runbook amended |
| "104/104, 403/403, lint pass" | **true** |
| commit conventions | **true** — one commit, byte-identical subject, both trailers, MAP by rule, the sweep file a test asset |

## Verdict

**REJECTED** — one MAJOR.

CR2r2b does what it was re-planned for. The three operator lookaheads are bounded
(`${chars[i + 1]:-}`, plus an explicit `i + 1 < n` test at the backslash arm), and
all seventeen spellings the cr18 gate found allowing now deny with empty stderr —
including the four plans-dir regressions against main. Nothing else moved: head
differs from CR2r2 on exactly those seventeen rows out of 390, the 232 historic
rows reproduce with zero mismatches and zero DENY→allow regressions, 50 of 50
recipes allow, and 30 of 30 mutations die. The fault machinery is real: an EXIT
trap catches a main-shell fatal, the two inner verdict substitutions check their
status, and both are pinned by mutations that make the injections allow again;
missing evidence — no git, no project dir, no `cwd`, a non-string command,
ordinary non-zero helpers — still allows, silently, with exit 0. The sweep gives
"never raises" an independent proof that survives the fault-deny. The five folded
minors all land. Timing stays inside both caps.

What fails is the completeness of the very mechanism this round added. The
contract says *every* `reason=$(…)` substitution over a verdict function checks
its status; the outermost one, `reason=$(bash_verdict …)` at
`tools/orchestrator-guard.sh:1356`, does not, and the EXIT trap cannot reach it
because `main` returns 0. Injecting a fault into `bash_verdict` on
`rm -rf .claude/ritual-override` ALLOWS, with no guard-authored stderr — the same
silent shape as the cr18 hole. The Edit/Write arm has the same gap at `:1366` and
`:1408`. Both the guard header and the runbook now assert the general property in
prose, so the tree documents a safety guarantee it does not have, and no test
pins the missing check.

A re-plan is XS: add the `st=$?` check after `:1356` (and the two Edit-arm
substitutions), red tests first — a `bash_verdict` injection that must DENY, a
`resolve_path`/`missing_headings` injection on a heading-removing Edit that must
DENY — plus a mutation per new check. While the file is open, fold in MINOR-2
(re-measure both runbook figures on this tree, including the symlink one, which
has now been carried over three rounds), MINOR-3 (`trap - EXIT` after each
`source "$GUARD"` in the bats file, so a failing sourcing test reports `not ok`),
MINOR-4 (the last nested-`cwd` payload at `:844`) and MINOR-5 (fill the sweep
fixture out to the corpus the contract names, and pin its row count exactly).
Everything else in CR2r2b should be kept as it is.
