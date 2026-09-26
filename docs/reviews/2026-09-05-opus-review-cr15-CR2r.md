# Opus gate — seat run cr15, task CR2r — REJECTED

## Summary

One commit (`2cbc2c1`) on base `bb64007` (main), branch `task/CR2r` in
`/home/dalhaka/factory/ws/cr15/CR2r`. Reviewed in a fresh clone at
`…/scratchpad/gate-cr15-CR2r`; nothing under `/home/dalhaka/factory` was
modified. The live repo's `.claude/ritual-override` was never touched — every
guard run drove a throwaway fixture at `…/scratchpad/fix/nixos-fixture`. The
clone is clean after checkout (`git status --porcelain` empty; the workspace's
untracked `scratch/` is **not** in the commit and not in the clone).

Commit conventions are clean: **one** commit, subject byte-identical to the
plan's (`cmp` against the plan line at `docs/superpowers/plans/2026-09-05-context-reset-ritual.md:160`
→ identical; md5 `8f4d1228…` on both), both trailers (`Generated-By: dsh …
factory run cr15`, `Co-Authored-By: Claude Fable 5.1`), three files touched —
`tools/orchestrator-guard.sh`, `tests/unit/91-orchestrator-guard.bats`,
`docs/runbooks/session.md` — all inside `touches`, no board commit, `docs/MAP.md`
identical to a fresh regeneration.

Most of CR2r is right and the cr12 MAJOR is genuinely fixed. All eight glob
spellings deny, in relative, absolute, `./`, `../`, quoted and brace form; the
delete family really did widen; `PROTECTED_PATHS` is now read by all three arms;
the pathless git over-denials are narrowed; the single batched `realpath` cut the
symlink worst case from 590 ms to 83 ms; the runbook names the lift, the accepted
over-denials and measured numbers. Checks are green — shellcheck rc 0, bats
**79/79**, `unit` **320/320**, `lint` pass. All eleven demanded mutations die.
196 historic rows (og4's git table, og5's Step-1/ancestor/rebase/sed/quote/
symlink/adversarial rows, og4's plan-write table, the host rules, CR2b's override
matrix, the Edit/Write rows) reproduce with **0** mismatches.

It is rejected on **four MAJORs**, all of them spellings that remove or overwrite
a protected path and ALLOW:

```
git commit -m "x"⏎rm -rf .claude/ritual-override   -> ALLOW   (new; also on the plans side — a REGRESSION)
git clean -df   /  -xdf  /  -dxf                   -> ALLOW   (contract says "with or without -d/-x")
git stash push -u  /  git stash save -u  /  -au    -> ALLOW   (the modern spelling of git stash -u)
tar -xf a.tar / unzip a.zip / cpio -idm, cwd=.claude -> ALLOW (matrix row 2 requires cpio DENY)
```

The first is the serious one. The new `git commit -m` prose exemption stops at
the first `;`/`&`/`|`/paren/brace token — and a **newline is not one of them**,
because `normalise_command` folds `\n` to a plain space. So in a two-line Bash
command everything after `-m` on *both* lines is treated as commit-message prose
and never scanned. Measured against the base guard, four spellings that DENY on
`bb64007` now ALLOW:

```
                                                        base bb64007   CR2r
git commit -m x⏎rm -rf docs/superpowers/plans/x.md         DENY        ALLOW
git commit -m 'subject line'⏎sed -i s/a/b/ <plan>          DENY        ALLOW
git commit -m 'subject'⏎tee <plan>                         DENY        ALLOW
git commit -m 'subject'⏎mv <plan> /tmp/                    DENY        ALLOW
```

Method: fresh clone; the guard driven only from that clone with
`env CLAUDE_PROJECT_DIR=<fixture> bash tools/orchestrator-guard.sh` on compact
`ensure_ascii=False` payloads of the real Claude Code shape with `cwd` at the
**top level**. Fixture: a git repo with `.claude/ritual-override`,
`.claude/settings.json`, `.claude/worktrees/x`, `.claude/list`,
`docs/superpowers/plans/x.md`, `docs/notes/plans/x.md` (decoy), `k`, `sub/`,
`link-to-override` → the override, `plans-link` → the plans dir,
`docs/superpowers/plans/out.md` → outside, `elsewhere/ritual-override` → `/tmp`,
and `…/fix/other/.claude/ritual-override` outside the project. Drivers:
`…/scratchpad/{mkfix.sh,drive.py,mutate.py,runmut.sh,timing.py}`,
case files `c1–c4.tsv`, `creg.tsv`, `crecipe.tsv`. 346 payloads in all.

## One list, three arms

**Met.** `PROTECTED_PATHS` (`tools/orchestrator-guard.sh:113-116`) is read by all
three arms, and the wiring is proved by mutation, not by inspection:

| arm | reader | proof |
|---|---|---|
| plan-write | `plans_canon()` `:442-453`, called from `write_verdict:512` and `is_plan_file:457-461` | **M-A** (the `dir` entry deleted) kills **15** tests: 16 22 24 25 28 30 31 33 34 35 36 44 45 46 48 |
| override (Bash) | `write_verdict:513-520` builds `file_canons`/`file_dirs` | **M-B** (the `file` entry deleted) kills **17** tests: 55 57 58 59 60 62 63 64 65 66 67 68 69 71 72 74 78 |
| Edit/Write/MultiEdit | `main:1058-1067` walks the list | **M-B** kills 57 58 69 on that arm; `:960`'s hard-coded `realpath -m -- "$project_dir/.claude/ritual-override"` (cr12 MINOR-1) is gone |

cr12's X1 is dead: deleting the `dir` entry now kills 15 tests instead of 0.

**No early break in `write_verdict`.** Adding `break` to the file loop (**M-C**,
`1+/0−`) kills test 76. Test 76 appends `'elsewhere/secret.txt|file'` and calls
`write_verdict` directly.

**Not fully met, two places.**

- Test 76 exercises **one** arm, not three. `X-MAINBRK` — a `break` added to
  `main:1067`'s Edit/Write loop — changes the tree (`1+/0−`) and kills **zero**
  of 79 tests. The no-break property on the Edit/Write arm is unpinned
  (MINOR-4).
- One hard-coded path survives in an arm: the plans raw-text fallback at
  `:653-655`, `case "$raw" in *superpowers/plans/* )`. The override's equivalent
  (the glob fallback, `:640-647`) is derived from `file_dirs`; the plans one is a
  literal. The contract says "no hard-coded path left in any arm" (MINOR-6).

## Rule behaviour

Fixture `<proj>` = `…/scratchpad/fix/nixos-fixture`; payload `cwd` = `<proj>`
unless noted. `base` = the guard at `bb64007` (main; no override rule),
`CR2b` = `git show task/CR2b:tools/orchestrator-guard.sh` (994 lines), `CR2r` =
this tree (1098 lines).

### Item 1 — the eight glob spellings (the cr12 MAJOR) — all fixed

| spelling | CR2b | CR2r |
|---|---|---|
| `rm -rf .claude/*` | ALLOW | **DENY** |
| `rm -rf .claude/*/` | ALLOW | **DENY** |
| `rm -rf <proj>/.claude/*` | ALLOW | **DENY** |
| `mv .claude/* /tmp/` | ALLOW | **DENY** |
| `shred .claude/*` | ALLOW | **DENY** |
| `rm -rf .claude/ritual*` | ALLOW | **DENY** |
| `rm .claude/[r]itual-override` | ALLOW | **DENY** |
| `rm -rf .claude/?itual-override` | ALLOW | **DENY** |

Plus brace/quoted/rebased forms, all **DENY**: `rm -rf .claude/{a,b}` (via the
plan rule — `{` pads to its own token, leaving a bare `.claude/`),
`rm -rf ".claude/"*`, `rm -rf '.claude'/*`, `rm -rf ./.claude/*`,
`rm -rf ../.claude/*` (cwd `<proj>/sub`), `rm -rf .claude/rit*ual-override`.
Mechanism: `:620-623` marks a token containing `*`/`?`/`[`/`{`, and `:640-647`
treats such a token whose lexical form is the protected dir or under it as
naming the file. **M-D** (the fallback disabled) kills test 71.

### Item 2 — family additions

| spelling | CR2r | note |
|---|---|---|
| `git stash -u` / `--include-untracked` / `-a` | **DENY** | `:861-885` |
| `tar -C .claude -xf x.tar` | **DENY** | |
| `tar -xf x.tar -C <proj>/.claude` | **DENY** | |
| `unzip -d .claude x.zip` | **DENY** | |
| **`cpio -idm` (cwd `<proj>/.claude`)** | **ALLOW** | **MAJOR-4** |
| **`tar -xf /tmp/a.tar` (cwd `<proj>/.claude`)** | **ALLOW** | MAJOR-4 |
| **`unzip /tmp/a.zip` (cwd `<proj>/.claude`)** | **ALLOW** | MAJOR-4 |
| `cd .claude && cpio -idm` | DENY | the `cd` argument is a token |
| `cd .claude && tar -xf /tmp/a.tar` | DENY | same |
| `chmod 000 / chown root / chattr +i .claude/ritual-override` | **DENY** | `:712-717` |
| `chmod 000 .claude`, `chmod -R 000 .claude` | ALLOW | the arm reads `ovr_seen` only — MINOR-3 |
| `xargs rm < .claude/list` | **DENY** | `:680-683` |
| `truncate -s0 .claude/ritual-override` | **DENY** | |
| `git stash` (no `-u`) | allow | correct |
| `tar -tf x.tar` | allow | correct |
| **`git stash push -u` / `save -u` / `-au`** | **ALLOW** | **MAJOR-3** |

### Item 3 — the narrowed git rules

| spelling | CR2b | CR2r | correct? |
|---|---|---|---|
| `git clean -n`, `git clean -nd`, `git clean` | DENY | **allow** | yes — the over-denial withdrawn |
| `git checkout main`, `git checkout -b x`, `git checkout HEAD~1`, `git checkout` | DENY (bare) | **allow** | yes |
| `git restore --staged k`, `git checkout -- k` | allow | allow | yes |
| `git stash` | allow | allow | yes |
| `git clean -f`, `git clean -fd`, `git clean --force`, `git clean -ffd`, `git clean -d -f` | DENY | DENY | yes |
| `git clean -fdx .claude` | DENY | DENY | yes |
| `git checkout -- .claude`, `git checkout -- .`, `git checkout .`, `git checkout --` | DENY | DENY | yes |
| `git restore .claude`, `git restore -- .` | DENY | DENY | yes |
| **`git clean -df`, `git clean -xdf`, `git clean -dxf`** | DENY | **ALLOW** | **MAJOR-2** |

### Item 4 — the `-m` exemption

| spelling | base | CR2r | verdict |
|---|---|---|---|
| `git commit -q -m 'guard: rm -rf .claude no longer allowed'` | allow¹ | allow | correct — cr12 MINOR-3 withdrawn |
| `git commit -m 'plans: docs/superpowers/plans/x.md rewritten'` | DENY | allow | correct, intended |
| `git commit -q -F /tmp/msg` | allow | allow | `-F` unaffected |
| `git commit -m "x" -F k` | allow | allow | **judged:** everything after `-m` to the end of the clause is prose, so `-F k` is swallowed too. Harmless here (`-F` is not a write verb), but it shows the exemption is clause-wide, not argument-wide |
| `git commit -m rm .claude/ritual-override` (unquoted) | DENY | **allow** | **judged:** a real shell runs `git commit -m rm` and passes `.claude/ritual-override` as a *pathspec* — git would not delete it, so the ALLOW is defensible on its own. It is the same code path as MAJOR-1 |
| **`git commit -m "x"⏎rm -rf .claude`** | allow¹ | **ALLOW** | **MAJOR-1** |
| **`git commit -m x⏎rm docs/superpowers/plans/x.md`** | **DENY** | **ALLOW** | **MAJOR-1 — plans regression** |

¹ base has no override rule at all.

Still caught after a `-m`, because the rules that run *before* `write_verdict` do
not consult `skip`: `git commit -m "x"⏎git push` (git rule), `…⏎sudo rm -rf
.claude` (sudo rule), `…⏎cp k /var/lib/secrets/x` (protected-prefix regex), and
`…⏎python3 -c 'import os;os.remove(…)'` (the `;` inside the python literal pads
to a separator token and ends the skip range).

### Reads, siblings and out-of-project — unchanged and correct

`cat .claude/ritual-override`, `ls -la .claude`, `ls .claude/*`, `stat`,
`test -f`, `git status`, `cp .claude/ritual-override /tmp/y`,
`rm -rf .claude/worktrees/x`, `rm <scratch>/fix/other/.claude/ritual-override`,
`rm -rf <scratch>/fix/other/.claude`, `rm elsewhere/ritual-override`,
`git worktree remove .claude/worktrees/x` → **allow**, all correct.

One new over-denial contradicts the runbook: **`rm -rf .claude/worktrees/*` →
DENY** (MINOR-1).

### Historic rows — no regression outside MAJOR-1

196 payloads, **0 mismatches**: og4's 31 git rows + 8 extras; og5's 25 Step-1
plan-write rows; the ancestors/edges, rebase, sed/perl, quote/redirect and
symlink tables; og5's 19 adversarial probes; og4's 21 plan-write extras; the 11
host rows; CR2b's 44 override rows; 9 Edit/Write/MultiEdit rows. Everything the
three prior gates recorded still behaves.

## Over-denial audit

**37 of 38** documented recipes ALLOW, including every one the brief names:
`git add <plan>`, `git add docs/OPERATIONS.md`, `git add -A`,
`nix develop -c git commit -q -F <file>`,
`nix develop -c git commit -q -m "<prose>"`, `bash <scratch>/launch.sh …`,
`git pull --ff-only …`, `tools/factory/seat/factory-integrate cr15 CR2r`,
`nix build .#checks…`, `nix develop -c bats …`, `curl --noproxy '*' …`,
`pgrep -af factory-wave`, `nix develop -c python3 - <<'PY' … open('docs/OPERATIONS.md','w') … PY`,
`nix develop -c githooks/pre-commit`, `nix develop -c treefmt`, `evidence bundle
--markdown`, `tasks.py brief`, `repomap.py write`, `claims.py validate`,
`nix build .#nixosConfigurations.core…`, `nix store diff-closures`, `rm -f
result`, `mv result result.old`, `git clean -nd`, `git checkout -b task/CR2r`,
`git checkout main`, `git restore --staged docs/OPERATIONS.md`, `git stash list`,
`dsh-openrouter --denials 5`.

The one refusal is **pre-existing, not new**:

```
sed -n '1,30p' <plan> | grep -i CR2r   ->  DENY   (plan rule)
```

Identical on `bb64007` (verified by re-running the same 38 rows against the base
guard: same single mismatch). This is og5's rule-4 `-i*` over-denial and is not
CR2r's.

Newly refused, none a documented recipe, all MINOR-2 (whole-command flags leak
across clauses, `:539-545`):

```
rm -f result && git clean         DENY   (rm's -f sets has_clean_force)
ls -a && git stash                DENY   (ls's -a sets has_stash_untracked)
tar -x -f a.tar && ls .claude     DENY   (has_extract + ovr_dir_seen)
rm -rf .claude/worktrees/*        DENY   (MINOR-1)
```

Each is allowed on its own (`rm -f result`, `ls -a`, `git clean`, `git stash`,
`ls .claude` all allow).

## Timing

Median of five whole-hook calls (including the ~22 ms process baseline), host
load 2.26/2.52/2.80 with seats live.

| command | CR2b | CR2r | cap | met |
|---|---|---|---|---|
| `git status` (baseline) | 23.6 ms | 21.7 ms | — | — |
| 200 path tokens (`ls docs/aN/bN.md ×200`) | 105.1 ms | **73.3 ms** | 150 ms | yes |
| 200 `.claude` path tokens | 104.5 ms | 74.5 ms | — | yes |
| **200 symlink tokens** | **589.7 ms** | **83.0 ms** | 300 ms | **yes** |
| `rm` × 200 symlink tokens | 535.5 ms | 80.4 ms | — | yes |

The claim is real: cr12's MINOR-6 (602 ms) is gone. The mechanism is `:586-609` —
one lexical pass collects the symlink indices, then a **single**
`realpath -m -- "${rargs[@]}"` resolves them all. `M-I` (the batch replaced by a
per-token `canon_path`) fails test 54 (`bats -f 'symlink-token'`,
`[ "$median" -lt 300 ]` failed).

Both bats timing tests use `$EPOCHREALTIME` and a median of three, as the
contract demands. The runbook (`docs/runbooks/session.md:180-186`) states both
numbers as measured — "~60 ms" against my 73 / 83 ms; right order, mildly
optimistic under load, and well inside the stated 150/300 caps (MINOR-7).

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| check | command | rc | result |
|---|---|---|---|
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **0** | clean |
| bats 91 | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | **0** | **79/79 ok**, `1..79`, no `not ok` |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **0** | **320/320 ok** |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **0** | pass |
| pre-commit | `nix develop -c githooks/pre-commit` | **0** | treefmt `All checks passed!`, 94 files, **0 changed**; then the known board-staleness note ("`docs/OPERATIONS.md` queue block was stale and has been regenerated") |
| MAP | `repomap.py --root . write` | — | **identical** to the committed `docs/MAP.md` |

`pre-commit` exits 0 here; it leaves `docs/OPERATIONS.md` modified (1 line — the
queue block derived from `git log --format=%s`, which the landing commit itself
changes). Reverted; `git status --porcelain` empty.

### The shfmt hazard (item 10) — reproduced, fixed, low risk of recurrence

The implementer's bug report is true. Reproduced in isolation:

```
$ nix develop -c shfmt -d probe.sh
-  canon_result[$i/$bi]=x
-  printf '%s\n' "${canon_result[$i/$bi]}"
+	canon_result[$i / $bi]=x
+	printf '%s\n' "${canon_result[$i / $bi]}"
```

shfmt parses an array subscript as arithmetic and pads the `/`. In an
**associative** array the subscript is a literal string, so the key becomes
`1 / 2` — which diverges from the `"$i/$bi"` strings that `pending` carries.

The fix is right and idiomatic: the index is hoisted into a plain variable
(`idx="$i/$bi"`, `:594`), and every read/write uses `canon_result[$idx]` or
`canon_result[${pending[k]}]` (`:596-607, 626`). shfmt has nothing to rewrite —
treefmt reports 0 changed files on this tree.

Can a future formatter run silently change it again? **No, not silently.** I
reintroduced the divergence (`X-SHFMT`: the write spelled `canon_result[$i / $bi]`
while reads stay on `$idx`) and it fails **25** tests — 16 17 18 22 43 44 45 46
47 48 55 60 61 62 63 64 65 66 67 68 71 72 74 76 78. Every path-resolving rule
collapses at once. No shfmt directive is needed; I would not raise this as a
finding beyond the note.

## Red before green

CR2b's guard (`git -C /home/dalhaka/factory/ws/cr12/CR2b show
task/CR2b:tools/orchestrator-guard.sh`, 994 lines) copied over the clone's guard,
CR2r's tests kept. Tree asserted changed (`git diff --numstat` →
`336 440 tools/orchestrator-guard.sh`), bats run, restored, re-run green.

```
1..79
not ok 54 a 200-symlink-token command stays under 300 ms (median of three calls)
not ok 71 bash: the eight glob spellings of .claude deny the override (raw-text fallback)
not ok 72 bash: git stash -u / tar -C / chmod / xargs delete verb deny the override
not ok 73 bash: pathless git clean/checkout/restore that delete nothing allow
not ok 75 bash: a git commit -m message is prose and never scanned (deny-only over-denial withdrawn)
not ok 76 a third protected file entry in the list is honoured (no early break)
not ok 77 ORCHESTRATOR_GUARD=off in the hook's own environment lifts the guard
```

Seven red — the timing test plus six of the nine new ones. The two that pass on
CR2b are honest and correctly so: test **74** (`git clean -f` / `checkout --
.claude` deny) passed on CR2b because CR2b denied *every* pathless clean, and
test **78** (the lift not settable from the payload) passed because CR2b had no
lift at all and denied anyway. Both are new pins of existing behaviour, not
inflation. After `git checkout --`, `git status --porcelain` empty and 79/79
green.

## Mutation table

Each mutation applied to `tools/orchestrator-guard.sh` in the clone, the tree
asserted changed (`numstat` printed per row), the full bats file run, then
reverted; `git status --porcelain` empty after every batch (`ALL REVERTED`).
Scripts: `…/scratchpad/{mutate.py,runmut.sh}`.

| # | mutation | numstat | fails | killed by |
|---|---|---|---|---|
| **M-A** | the plans entry deleted from `PROTECTED_PATHS` (`:114`) | 0+/1− | **15** | 16 22 24 25 28 30 31 33 34 35 36 44 45 46 48 |
| **M-B** | the override entry deleted (`:115`) | 0+/1− | **17** | 55 57 58 59 60 62 63 64 65 66 67 68 69 71 72 74 78 |
| **M-C** | the file loop `break`s after the first entry (`:520`) | 1+/0− | **1** | 76 |
| **M-D** | the raw-text/glob fallback disabled (`:640`) | 1+/1− | **1** | 71 |
| **M-E** | `git stash -u` dropped from the family (`:544`) | 1+/1− | **1** | 72 |
| **M-F** | `tar` dropped from the extract arm (`:730`) | 1+/1− | **1** | 72 |
| **M-G** | `git clean -n` treated like `-f` (`:543`) | 1+/1− | **1** | 73 |
| **M-H** | the `-m` exemption removed (`:572`) | 1+/1− | **1** | 75 |
| **M-I** | the batched `realpath` replaced by per-token `canon_path` (`:595-597`) | 2+/3− | **1** | 54 (`[ "$median" -lt 300 ]` failed) |
| **M-J** | the lift flag read from the payload text (`main:1033`) | 1+/0− | **1** | 78 |
| **M-K** | the lift flag ignored entirely (`:1012-1014`) | 0+/3− | **1** | 77 |

**Eleven of eleven die**, exactly as the plan demands.

### Extra probes of mine

| # | mutation | numstat | fails | reading |
|---|---|---|---|---|
| **X-SHFMT** | the `canon_result` write spelled `[$i / $bi]`, reads on `$idx` | 1+/1− | **25** | the shfmt regression would be loud, not silent |
| **X-MAINBRK** | `break` added to `main:1067`'s Edit/Write PROTECTED loop | 1+/0− | **0** | **SURVIVES** — the Edit/Write arm's no-break is unpinned (MINOR-4) |

### Prior tables

cr12's ten (M-A…M-J) and og5's M-A…M-I are structurally superseded — the code
they anchored on was restructured — but their behaviour is covered: M-A and M-B
above subsume cr12's M-A/M-H and og5's M-B (the shared ancestor function), M-D/
M-E/M-F/M-G/M-I above are new, and the **196-row historic regression sweep with
0 mismatches** is the stronger statement: every row those 34 + 9 mutations
protected still behaves on this tree. The only prior survivor recorded
(og5 M-I, `pushd` dropped) is now moot — `pushd` is still in the rebase verb list
at `:526` and `pushd docs/superpowers/plans && rm x.md` denies.

## Findings

### MAJOR-1 — the `git commit -m` exemption swallows every following line; a plans-dir regression

`tools/orchestrator-guard.sh:154` folds a newline to a plain space:

```bash
  c=${c//$'\n'/ }   # newline → space (a boundary, not a position)
```

`pad_operators` never makes a newline its own token, so the only tokens that end
the `-m` skip range are `;`, `&`, `|`, `(`, `)`, `{`, `}` (`:566-579`):

```bash
        s=$((m + 1))
        while [ "$s" -lt "$n" ]; do
          case "${toks[s]}" in
            ';' | '&' | '|' | '(' | ')' | '{' | '}') break ;;
            *) skip[s]=1 ;;
          esac
```

In a two-line Bash command there is no such token, so `skip` runs to the end and
neither the fact scan (`:589-650`) nor the verb loop (`:664-932`) ever sees the
second line. Measured, `cwd = <proj>`:

```
git commit -m 'x'⏎rm -rf .claude/ritual-override                -> ALLOW
git commit -m 'x'⏎rm -rf .claude                                -> ALLOW
git commit -m 'x'⏎rm -rf docs                                   -> ALLOW
git commit -m 'x'⏎git clean -fd                                 -> ALLOW
git commit -m 'x'⏎find .claude -delete                          -> ALLOW
git commit -m 'x'⏎touch .claude/ritual-override                 -> ALLOW
git commit -m 'x'⏎echo y > .claude/ritual-override              -> ALLOW
nix develop -c git commit -q -m "session: guard lands"⏎rm -rf .claude -> ALLOW
```

and on the plans side, against the base guard `bb64007`:

```
                                                       base    CR2r
git commit -m x⏎rm -rf docs/superpowers/plans/x.md     DENY    ALLOW
git commit -m 'subject line'⏎sed -i s/a/b/ <plan>      DENY    ALLOW
git commit -m 'subject'⏎tee <plan>                     DENY    ALLOW
git commit -m 'subject'⏎mv <plan> /tmp/                DENY    ALLOW
```

Four spellings that main refuses today are allowed by CR2r. That is a plans-dir
regression as well as an override hole, and the shape — commit, then a newline,
then cleanup — is the ordinary way work is done in this repo. The commit body's
claim that "a `git commit -m` message is prose and is no longer scanned" is
true; what is not true is that the scan resumes after the message.

The exemption is also clause-wide rather than argument-wide even on one line:
`git commit -m "x" -F k` marks `-F` and `k` as prose too. Harmless today, but it
is the same over-broad range.

Fix shape: make the newline a boundary token in `pad_operators` (it is already a
boundary for the sudo/nixos-rebuild anchors via `$NL`), or bound the skip range
to the single token after `-m` when the message was a quoted word, or end the
range at the first token that starts with `-` after the message. A red test:
`git commit -m 'x'` + a real newline + `rm -rf .claude/ritual-override` must
DENY, and the same with a plan path must DENY.

### MAJOR-2 — `git clean -df` (and `-xdf`, `-dxf`) ALLOW

`tools/orchestrator-guard.sh:543`:

```bash
      -f* | --force) has_clean_force=1 ;;
```

The pattern anchors `f` at the front of the cluster. Measured:

```
git clean -f     DENY      git clean -df    ALLOW
git clean -fd    DENY      git clean -xdf   ALLOW
git clean -fdx   DENY      git clean -dxf   ALLOW
git clean --force DENY     git clean -ffd   DENY
git clean -d -f  DENY
```

`git clean -df` removes untracked files and directories — the override is
untracked and not ignored, so it goes. The plan's contract item 4 is explicit:
"`git clean` denies only with `-f` (**with or without `-d`/`-x`**)". `-df` is
`-f` with `-d`; the guard reads the cluster positionally instead of by
character. CR2b denied this (it denied every pathless clean), so the narrowing
overshot. Fix: test for an `f` anywhere in a single-dash cluster, e.g.
`-[!-]*f*`.

### MAJOR-3 — `git stash push -u`, `git stash save -u` and `git stash -au` ALLOW

Two causes. First, `:544` matches the flag **exactly**:

```bash
      -u | -a | --include-untracked | --all) has_stash_untracked=1 ;;
```

so `-au` (and `-ua`) never sets the fact. Second, even when the flag is seen,
the pathspec walk at `:866-880` takes the **first non-option token after
`stash`** as a pathspec:

```bash
                  *)
                    has_pathspec=1
                    break
                    ;;
```

`git stash push -u` and `git stash save -u` put the *subcommand word* there, so
`has_pathspec=1`, no protected path is named, and the deny is skipped.
Measured:

```
git stash -u                DENY      git stash push -u   ALLOW
git stash --include-untracked DENY    git stash save -u   ALLOW
git stash -a                DENY      git stash -au       ALLOW
git stash -u -- .           DENY      git stash           allow (correct)
```

`git stash push -u` is the spelling git's own documentation now prefers, and it
does exactly what `git stash -u` does to the untracked override. Fix: match the
flag by character inside a cluster, and skip `push`/`save`/`create`/`store`
before looking for a pathspec.

### MAJOR-4 — an extract whose *cwd* is inside `.claude` ALLOWS

`tools/orchestrator-guard.sh:730-737` denies `tar`/`unzip`/`cpio` only when a
**token** names the protected directory:

```bash
      tar | unzip | cpio)
        if [ "$t" = "tar" ] && [ "$has_extract" -eq 0 ]; then
          :
        elif [ "$ovr_seen" -eq 1 ] || [ "$ovr_dir_seen" -eq 1 ]; then
```

`cpio -idm` extracts into the current directory and names no path at all, so
with the payload `cwd` inside `.claude` nothing sets `ovr_dir_seen`. Measured
with top-level `cwd = <proj>/.claude`:

```
cpio -idm            ALLOW      (the matrix's row 2 requires DENY)
tar -xf /tmp/a.tar   ALLOW
unzip /tmp/a.zip     ALLOW
```

versus `cd .claude && cpio -idm` → DENY and `cd .claude && tar -xf /tmp/a.tar` →
DENY, because there the `cd` argument is a token. The `cwd` machinery itself
works — `rm ritual-override` with `cwd = <proj>/.claude` denies (test 67) — it
just needs a path token to rebase, and an extract has none. Fix: when an extract
verb is present and no `-C`/`-d` destination is given, judge the *bases*
themselves against the protected dirs.

### MINOR-1 — `rm -rf .claude/worktrees/*` denies, contradicting the runbook

`:640-647` treats any glob token whose lexical form is under the protected
parent as naming the file:

```bash
          case "$orig" in
            "${file_dirs[kk]}" | "${file_dirs[kk]}"/*)
              ovr_seen=1
              ovr_dir_seen=1
```

`"$file_dirs"/*` matches descendants at any depth, so a glob deep inside
`.claude` fires. Measured: `rm -rf .claude/worktrees/x` → allow (correct);
`rm -rf .claude/worktrees/*` → **DENY**. The runbook
(`docs/runbooks/session.md:151-155`) promises the opposite in the sibling
paragraph: "a sibling such as `.claude/worktrees/x` is **not** over-denied".
Narrow the glob fallback to a token whose glob-free prefix is the protected
directory itself, or say so in the runbook.

### MINOR-2 — the whole-command flag scan leaks across clauses

`:536-546` collects `has_inplace`, `has_find_delete`, `has_xargs`,
`has_extract`, `has_clean_force`, `has_stash_untracked` over **every** token of
the command, so a flag belonging to one clause arms another clause's rule.
Measured, each new relative to base:

```
rm -f result && git clean       DENY   (rm's -f)
ls -a && git stash              DENY   (ls's -a)
tar -x -f a.tar && ls .claude   DENY   (has_extract + .claude named by ls)
```

Each alone allows. Deny-only, no documented recipe hit, and the same shape as
og5's `-i*` over-denial — but the runbook's over-denial paragraph names only
`ls .claude && rm /tmp/x` and `git checkout --`.

### MINOR-3 — `chmod`/`chown`/`chattr` on the *directory* allow

`:712-717` checks `ovr_seen` only, never `ovr_dir_seen`:

```
chmod 000 .claude/ritual-override   DENY
chmod 000 .claude                   ALLOW
chmod -R 000 .claude                ALLOW   (recursive — reaches the file)
```

The contract says "`chmod`/`chown`/`chattr` on a protected **file**", so this is
inside the contract as written; `chmod -R` on the parent reaches the file all the
same. Recorded.

### MINOR-4 — the Edit/Write arm's "no early break" is unpinned

Test 76 (`a third protected file entry in the list is honoured (no early break)`,
`tests/unit/91-orchestrator-guard.bats:985-993`) sources the guard, appends
`'elsewhere/secret.txt|file'` and calls **`write_verdict`** only. The matrix
asked the third entry to be exercised "through all three arms". `X-MAINBRK` — a
`break` added to `main`'s loop at `:1067` — changes the tree and kills **zero**
tests. Add a Write-payload row for the third entry.

### MINOR-5 — the lift prints nothing

`:1012-1014`:

```bash
  if [ "${ORCHESTRATOR_GUARD:-}" = "off" ]; then
    return 0
  fi
```

Verified: with `ORCHESTRATOR_GUARD=off` in the hook's environment,
`rm -rf .claude` allows with **empty stdout and empty stderr**. The gate matrix
asked for "allow with one stderr line" so a lifted session is visible in the
transcript; the plan's contract item 7 does not, and the runbook does not claim
one. Recorded as the gap between the two. (The rest of item 8 is correct:
`ORCHESTRATOR_GUARD=off rm -rf .claude/ritual-override` inside the payload
**DENIES**, `env ORCHESTRATOR_GUARD=off rm -rf .claude` **DENIES**, and an `env`
key in the payload JSON is ignored — the flag is read from the hook process's
own environment at `main`'s first line, before the payload is even read from
stdin, and a `VAR=x cmd` prefix inside a Bash payload would only ever set the
variable in the *tool's* child shell, which is a different process spawned after
the hook has already returned. **M-J** — reading the flag out of `$payload` —
kills test 78.)

### MINOR-6 — one hard-coded protected path survives, in the plans arm

`:653-655`:

```bash
  [ "$plan_file_seen" -eq 0 ] && case "$raw" in
    *superpowers/plans/*) plan_file_seen=1 ;;
  esac
```

The contract says "no hard-coded path left in any arm". The override's
equivalent fallback derives its pattern from `file_dirs`; this one does not, so a
third `dir` entry would get no raw-text fallback. `plans_canon()` (`:442-453`)
also `return`s after the first `dir` entry, so a second `dir` entry would be
silently ignored — the mirror of cr12's `break`, on the other kind.

### MINOR-7 — the runbook's timing numbers are ~20% optimistic

`docs/runbooks/session.md:180-186` says "a 200-path-token command measures ~60 ms
and a 200-symlink-token command ~60 ms". I measure 73.3 ms and 83.0 ms (median of
five, load 2.26). Right order, correctly framed as measured, comfortably inside
the 150/300 ms caps the same sentence names — but the symlink case is 40% above
the stated figure.

### MINOR-8 — process: the result block was written with colons; `scratch/` left behind

The seat emitted `FACTORY-RESULT: PASS` instead of the parseable form, so the run
is recorded `status=failed` although `2cbc2c1` exists and is complete. An
untracked `scratch/` directory remains in `/home/dalhaka/factory/ws/cr15/CR2r`;
it is **not** in the commit and **not** in a fresh clone (`git status
--porcelain` on the clone is empty). Neither affects the code.

### NOTE — the implementer's claims, checked

| claim | verdict |
|---|---|
| unit 320/320 | **true** (`nix build … unit --rebuild`, rc 0) |
| lint clean | **true** (rc 0; treefmt 94 files, 0 changed; shellcheck rc 0) |
| 200 symlink tokens ~60 ms, one `realpath` for all symlinks | **substantially true** — 83.0 ms measured (CR2b: 589.7 ms); the single batched call is at `:600-609` and M-I kills the timing test |
| tests 71–79 added, red on CR2b | **mostly true** — 71 72 73 75 76 77 go red (plus 54, the timing test); 74 and 78 pass on CR2b, honestly, because CR2b denied those cases for other reasons |
| the shfmt bug is real | **true**, reproduced above; the fix holds and a recurrence would fail 25 tests |
| "the eight glob spellings deny" | **true**, plus five more spellings I added |
| "the pathless git over-denials are narrowed" | **true but overshot** — MAJOR-2 and MAJOR-3 |
| "a `git commit -m` message is prose and is no longer scanned" | **true, and it does not stop at the message** — MAJOR-1 |

## Verdict

**REJECTED** — four MAJORs.

CR2r fixes the thing it was re-planned for. Every glob spelling of the override
directory now denies, in eight demanded and five extra forms; `PROTECTED_PATHS`
is genuinely read by all three arms with mutation proof on each (15, 17 and 3
tests respectively); the file loop no longer breaks early; the delete family
gained `git stash -u`, the extract verbs, `chmod`/`chown`/`chattr`, `xargs` and
`truncate`; `git clean -n`, `git checkout main`, `git checkout -b`, `git restore
--staged` and a plain `git stash` are no longer refused; the symlink worst case
dropped 7× to 83 ms by batching one `realpath`; the runbook names the lift, the
accepted over-denials and the measured numbers; the lift cannot be reached from a
payload. Eleven of eleven demanded mutations die, 196 historic rows reproduce
with zero mismatches, 37 of 38 documented recipes allow (the 38th refuses
identically on main), the checks are green, and the commit conventions are clean.

What fails is the new work's own edges. The `-m` prose exemption has no end: a
newline is folded to a space and never becomes a boundary token, so everything
after `git commit -m` on every following line is treated as commit-message text.
`git commit -m 'x'` then a newline then `rm -rf .claude/ritual-override` allows —
and so does the same shape with a plan path, which **main denies today**. That is
a regression in the rule this whole line of tasks exists to protect, introduced
by the fix for a MINOR. Beside it, the narrowing overshot twice: `git clean -df`
and `git stash push -u` — both ordinary spellings of the exact operations the
plan enumerated — now allow where CR2b denied them, because the flag tests read a
cluster positionally and the pathspec walk mistakes a subcommand word for a path.
And an extract whose cwd is inside `.claude` names nothing and passes, the one
row of the required matrix that does not hold.

A re-plan should be S and is well bounded: make the newline a boundary token (or
end the `-m` range at the message word), match `f` and `u`/`a` anywhere inside a
single-dash cluster, skip `push`/`save`/`create`/`store` before the stash
pathspec walk, and judge the bases against the protected dirs when an extract
verb carries no destination. Four red tests first — `git commit -m 'x'`⏎`rm -rf
.claude/ritual-override`, the same with a plan path, `git clean -df`, `git stash
push -u` — plus the `cpio -idm` cwd row. Fold in MINOR-1 (the sibling glob, which
the runbook already promises the other way) and MINOR-4 (a Write row for the
third list entry) in the same commit. Nothing else here needs to move.
