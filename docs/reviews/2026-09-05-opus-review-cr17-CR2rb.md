---
reviewer: opus
majors: 1
minors: 8
---
# Opus gate — seat run cr17, task CR2rb — REJECTED

## Summary

One commit (`6c5462e`) on base `c15f4ac` (main), branch `task/CR2rb` in
`/home/dalhaka/factory/ws/cr17/CR2rb`. Reviewed in a fresh clone at
`…/scratchpad/gate-cr17-CR2rb`; nothing under `/home/dalhaka/factory` was
modified and the live repo's `.claude/ritual-override` was never touched — every
guard run drove a throwaway fixture at `…/scratchpad/fix/nixos-fixture`.

Commit conventions are clean. **One** commit; subject byte-identical to the plan
line at `docs/superpowers/plans/2026-09-05-context-reset-ritual.md:202`
(`cmp` → identical, md5 `01f0737e…` on both); both trailers (`Generated-By: dsh
… factory run cr17`, `Co-Authored-By: Claude Fable 5.1`); three files touched —
`tools/orchestrator-guard.sh` (+719/−135), `tests/unit/91-orchestrator-guard.bats`
(+466/−3), `docs/runbooks/session.md` (+64/−3) — all inside `touches`; no board
commit; `docs/MAP.md` identical to a fresh regeneration. The seat's result block
was well-formed this time.

All four cr15 MAJORs are genuinely fixed, and I could not refute any of the
implementer's four headline claims:

```
git commit -m 'x'⏎rm -rf .claude/ritual-override   DENY   (was ALLOW)
the four plans newline spellings                   DENY   (was ALLOW — matches main)
git clean -df / -xdf / -dxf                        DENY   (was ALLOW)
git stash push -u / save -u / -au / -ua            DENY   (was ALLOW)
cpio -idm / tar -xf / unzip, cwd inside .claude    DENY   (was ALLOW)
```

Checks are green — shellcheck rc 0, bats **86/86**, `unit` **353/353**, `lint`
pass, `pre-commit` rc 0, treefmt 0 changed. 182 historic rows (og4's git table,
og5's Step-1/ancestor/rebase/sed/quote/symlink rows, og4's plan-write table,
CR2b's override matrix, CR2r's glob and narrowing rows) reproduce with **0**
mismatches. All 50 documented orchestrator recipes ALLOW. Six of the seven new
tests go red on CR2r's guard. Twenty of the twenty-one demanded mutations die.

It is rejected on **one MAJOR**, which is a side effect of the fix for cr15's
MINOR-2 (clause-local flag attribution):

```
sed 's|a|b|' -i docs/superpowers/plans/x.md        ALLOW   (main: DENY, CR2r: DENY)
perl -pe 's|a|b|' -i docs/superpowers/plans/x.md   ALLOW   (main: DENY, CR2r: DENY)
sed 's|a|b|' -i .claude/ritual-override            ALLOW   (CR2r: DENY)
find docs/superpowers/plans -name 'a|b' -delete    ALLOW   (main: DENY, CR2r: DENY)
```

A shell metacharacter (`|`, `;`, `&`) or a newline **inside a quoted argument**
is emitted as a clause-boundary token, so a flag that follows that argument is
attributed to a different clause from its verb and no longer arms it. `sed
's|a|b|' -i <plan>` — sed with pipe delimiters, the flag after the script — is
an ordinary spelling, and it is exactly the shape og4 raised as MAJOR 17 and
og5 fixed.

Method: fresh clone (`git clone -q --branch task/CR2rb …`); the guard driven only
from that clone with `env CLAUDE_PROJECT_DIR=<fixture> bash
tools/orchestrator-guard.sh` on compact `ensure_ascii=False` payloads of the real
Claude Code shape with `cwd` at the **top level**. Fixture: a git repo with
`.claude/{ritual-override,settings.json,worktrees/x,list}`,
`docs/superpowers/plans/x.md`, `docs/second/plans/y.md`, `docs/notes/plans/x.md`
(decoy), `k`, `sub/`, `elsewhere/ritual-override`, `link-to-override` → the
override, `plans-link` → the plans dir, `docs/superpowers/plans/out.md` →
outside, and `…/fix/other/.claude/ritual-override` outside the project. Drivers:
`…/scratchpad/{mkfix.sh,drive.py,cmp.py,mutate.py,runmut.sh,timing.py,lift.sh,
twodir2.sh}`, case files `sweep.tsv`, `c1–c7.tsv`, `recipes.tsv`. 380 payloads in
all, each also replayed against `git show c15f4ac:tools/orchestrator-guard.sh`
(main, 723 lines) and `git show task/CR2r:tools/orchestrator-guard.sh` (CR2r,
1098 lines) so every difference is attributed.

## What the restructuring actually is

The diff is large because the token pipeline was rewritten, not patched.

| before (CR2r) | after (CR2rb) |
|---|---|
| `normalise_command` + `pad_operators` + `tokenise` — three string passes, quotes and newlines erased before tokenising | a new `tokenise_ctx` (`:200-322`) — one character-at-a-time scan of the **raw** command producing the same token text plus two parallel arrays, `quoted[i]` and `nlsep[i]` |
| the `-m` skip range ran to the first `;&\|(){}` token, and a newline was never one | the skip range is the run of consecutive **quoted** tokens after `-m`/`--message` (`:727-740`) |
| `has_clean_force` etc., one set of flags for the whole command | `c_clean_force[c]` etc., one set **per clause** (`:670-704`), clauses cut on `;`, `&`, `\|` and `nlsep` before any attribution |
| `-f*`, `-u`, `-a` matched positionally/exactly | `-*f*`, `-*u*`, `-*a*` — clusters read by character (`:700-703`) |
| the stash pathspec walk took the first non-option token | `push\|save\|pop\|apply\|drop\|list\|show\|branch\|create\|store` are skipped first (`:1080`) |
| an extract denied only when a token named `.claude` | with no `-C`/`-d`, the **base in effect at the verb** (`base_of[i]`, `:658-664`) is judged against the protected dirs (`:929-938`) |
| `chmod`/`chown`/`chattr` read `ovr_seen` only | they read `ovr_dir_seen` too (`:893`) |
| the plans raw-text fallback was the literal `*superpowers/plans/*` | it derives `rel` from `PROTECTED_PATHS` and iterates every `dir` entry (`:815-827`) |
| the lift returned silently | `warn "lifted by ORCHESTRATOR_GUARD=off"` (`:1221`) |

`git_verdict` still uses the old `normalise_command`/`pad_operators` pipeline
(`:325-329`); only `write_verdict` moved to `tokenise_ctx`. The two token streams
are asserted byte-identical by construction (the trailing-empty-token
reproduction at `:315-321`), and the 182-row sweep confirms no git-rule row
moved.

Every prior behaviour I could put a payload against is retained; see the sweep
below.

## Rule behaviour

Fixture `<proj>` = `…/scratchpad/fix/nixos-fixture`; payload `cwd` = `<proj>`
unless noted.

### Item 1 — the `-m` exemption (25 rows, 1 deviation)

| spelling | CR2r | CR2rb | matrix |
|---|---|---|---|
| `git commit -m 'x'`⏎`rm -rf .claude/ritual-override` | ALLOW | **DENY** | deny ✓ |
| `git commit -m 'x'`⏎`rm -rf .claude` | ALLOW | **DENY** | ✓ |
| `git commit -m 'x'`⏎`git clean -fd` | ALLOW | **DENY** | ✓ |
| `git commit -m 'x'`⏎`find .claude -delete` | ALLOW | **DENY** | ✓ |
| `git commit -m 'x'`⏎`touch .claude/ritual-override` | ALLOW | **DENY** | ✓ |
| `git commit -m 'x'`⏎`echo y > .claude/ritual-override` | ALLOW | **DENY** | ✓ |
| `nix develop -c git commit -q -m "…"`⏎`rm -rf .claude` | ALLOW | **DENY** | ✓ |
| `git commit -m x`⏎`rm -rf <plan>` | ALLOW | **DENY** | ✓ (matches main) |
| `git commit -m 'subject line'`⏎`sed -i s/a/b/ <plan>` | ALLOW | **DENY** | ✓ |
| `git commit -m 'subject'`⏎`tee <plan>` | ALLOW | **DENY** | ✓ |
| `git commit -m 'subject'`⏎`mv <plan> /tmp/` | ALLOW | **DENY** | ✓ |
| `git commit -q -m 'guard: rm -rf .claude no longer allowed'` | allow | allow | ✓ |
| `git commit -m "x" -F k` | allow | allow | ✓ ("say": `-F k` is no longer swallowed — the skip stops at the unquoted `-F`) |
| `git commit -m rm .claude/ritual-override` (unquoted) | allow | **DENY** | ✓ |
| `git commit -m 'line one`⏎`line two rm -rf .claude'` (newline inside the quotes) | — | allow | ✓ |
| `git commit -m 'x' ; rm -rf .claude` | DENY | DENY | ✓ |
| `git commit --message='rm x'` | allow | allow | ✓ |
| `git commit -m 'plans: <plan> rewritten'` | allow | allow | ✓ |
| **`git commit -m 'subject' -m 'body: rm -rf .claude …'`** | allow | **DENY** | ✗ matrix asks both exempt — **MINOR-2** |
| `git commit -m 'x'`⏎`git push` / `sudo rm -rf .claude` / `cp k /var/lib/secrets/x` | DENY | DENY | ✓ still caught before `write_verdict` |

### Item 2 — flag clusters (33 rows, 0 deviations)

`git clean` **DENY**: `-df`, `-xdf`, `-dxf`, `-ffd`, `-f`, `--force`, `-d -f`,
`-fd`, `-fdx`, `-fdx .claude`. **allow**: `-n`, `-nd`, `-dn`, bare, `--dry-run`.

`git stash` **DENY**: `push -u`, `save -u`, `-au`, `-ua`, `--include-untracked`,
`-a`, `--all`, `-u`, `-u -- .`. **allow**: bare, `pop`, `list`, `push`, `apply`,
`show`, `drop`, `push -- k`, `push -m 'wip'`.

### Item 3 — extracts and the payload cwd (17 rows, 3 deviations)

| spelling | cwd | CR2r | CR2rb | matrix |
|---|---|---|---|---|
| `cpio -idm` | `<proj>/.claude` | ALLOW | **DENY** | ✓ |
| `tar -xf /tmp/a.tar` | `<proj>/.claude` | ALLOW | **DENY** | ✓ |
| `unzip /tmp/a.zip` | `<proj>/.claude` | ALLOW | **DENY** | ✓ |
| `tar --extract --file /tmp/a.tar` | `<proj>/.claude` | ALLOW | **DENY** | ✓ |
| `tar -tf x.tar` | `<proj>/.claude` | allow | allow | ✓ |
| `tar -xf x.tar -C /tmp` | `<proj>/.claude` | allow | allow | ✓ ("say") |
| `unzip -d /tmp x.zip` | `<proj>/.claude` | allow | allow | ✓ |
| **`cpio -idm` / `tar -xf /tmp/a.tar` / `unzip /tmp/a.zip`** | `<proj>` | allow | **DENY** | ✗ matrix asks allow — **MINOR-1** |
| `tar -xf /tmp/a.tar` | `<proj>/sub` | allow | allow | ✓ |
| `tar -xf /tmp/a.tar` | `/tmp` | allow | allow | ✓ |
| `tar -C .claude -xf x.tar`, `tar -xf x.tar -C .claude`, `unzip -d .claude x.zip` | `<proj>` | DENY | DENY | ✓ |
| `cd .claude && cpio -idm` / `&& tar -xf …` | `<proj>` | DENY | DENY | ✓ |

### Item 4 — clause-local attribution (11 rows)

| spelling | CR2r | CR2rb | matrix |
|---|---|---|---|
| `rm -f result && git clean` | DENY | **allow** | ✓ |
| `ls -a && git stash` | DENY | **allow** | ✓ |
| `sed -n '1,30p' <plan> \| grep -i CR2rb` | DENY | **allow** | ✓ (og5's rule-4 over-denial, withdrawn) |
| `tar -x -f a.tar && ls .claude` | DENY | DENY | ✗ — but by MINOR-1's cwd rule, not by flag leakage |
| `git clean -f; ls` | DENY | DENY | ✓ |
| `ls; git stash -u` | DENY | DENY | ✓ |
| `rm -f result` / `ls -a` / `ls .claude` alone | allow | allow | ✓ |
| `rm -f result && ls <plan>` | DENY | DENY | ✓ (facts stay whole-command by design) |

### Item 5 — the folded minors

| item | result |
|---|---|
| `chmod 000 .claude`, `chmod -R 000 .claude`, `chown root .claude`, `chattr +i .claude` | **DENY** (`:893`); the file spellings still deny; `chmod 755 k` allows |
| Edit/Write no early break | pinned by test 85; **M-F** (a `break` at `:1275`) kills it — cr15's X-MAINBRK survivor is dead |
| the lift | `ORCHESTRATOR_GUARD=off` in the hook env → allow, stdout empty, **exactly one** stderr line `orchestrator-guard: lifted by ORCHESTRATOR_GUARD=off`; in the payload text, as an `env` prefix, or as a payload `env` key → **DENY** |
| no hard-coded path | `grep -n 'superpowers/plans\|ritual-override' tools/orchestrator-guard.sh` outside comments → only `:114`, `:115` (the list) and `:121` (the reason string) |
| `plans_canon` over two `dir` entries | adding `'docs/second/plans\|dir'` to the list: `rm docs/second/plans/y.md` **DENY**, `rm <plan>` still **DENY**, Write dropping the second dir's heading **DENY**, Write keeping it allow, the unlisted decoy `docs/notes/plans/x.md` allow — both entries honoured, no early return |
| sibling glob | `rm -rf .claude/worktrees/x` allow, `rm -rf .claude/worktrees/*` **DENY**; `docs/runbooks/session.md:159-161` and `:172-176` now state the over-denial explicitly — the runbook and the code agree |

### Item 6 — the historic sweep

182 payloads, **0 mismatches**: og4's 31 git rows + 6 quote rows, og4/og5's 43
plan-write rows, og5's ancestors/edges (10), rebase (3), sed/perl (4),
quote/redirect (2), symlink (2), CR2b's 44 override rows, CR2r's 14 glob
spellings and 17 family/narrowing rows. Replayed against main and CR2r, the only
verdict that moved from DENY to ALLOW anywhere in the whole 380-payload corpus,
other than the MAJOR below, is `sed -n '1,30p' <plan> | grep -i CR2rb` — a
read-only pipeline that main refused as og5's rule-4 over-denial and CR2rb now
correctly allows.

## Over-denial audit

**50 of 50** documented recipes ALLOW — identical to main on all 50:
`git add <plan>`, `git add docs/OPERATIONS.md`, `git add -A`, `nix develop -c git
commit -q -F <file>`, `nix develop -c git commit -q -m "<prose naming rm,
.claude and a plan path>"`, `bash <scratch>/launch.sh …`, `git pull --ff-only …`,
`tools/factory/seat/factory-integrate cr17 CR2rb`, `nix build .#checks…`,
`nix develop -c bats …`, `curl --noproxy '*' …`, `pgrep -af factory-wave`,
`git merge --abort`, `git checkout --theirs -- docs/OPERATIONS.md`,
`git branch -f task/CR2rb <sha>`, `git checkout -q --detach <sha>`,
`nix develop -c python3 - <<'PY' … open('docs/OPERATIONS.md','w') … PY`,
`nix develop -c githooks/pre-commit`, `treefmt`, `evidence bundle --markdown`,
`tasks.py brief`, `repomap.py write`, `claims.py validate`, `nix build
.#nixosConfigurations.core…`, `nix store diff-closures`, `rm -f result`,
`mv result result.old`, `git clean -nd`, `git checkout -b task/CR2rb`,
`git checkout main`, `git restore --staged docs/OPERATIONS.md`, `git stash list`,
`dsh-openrouter --denials 5`, `shellcheck`, `nix flake check -L`, `git log`,
`git diff --stat`, `git show`, `sed -n '1,30p' <plan>`, `git worktree list`,
`git fetch`, `pytest tests/broker -q`, `tests/run-mount-tests.sh`, `git status
--porcelain`, `git rev-parse`, `git cherry-pick -n`, `git merge --ff-only`,
`tar -czf /tmp/backup.tgz docs`. **No documented recipe is refused.**

New over-denials, none a documented recipe, all recorded as minors:

```
tar -xf /tmp/a.tar        cwd=<proj>   DENY   (main: allow, CR2r: allow)   MINOR-1
tar -xzf /tmp/x.tar.gz    cwd=<proj>   DENY   (same)                       MINOR-1
unzip /tmp/a.zip          cwd=<proj>   DENY   (same)                       MINOR-1
cpio -idm                 cwd=<proj>   DENY   (same)                       MINOR-1
git commit -m 'a' -m 'body: rm -rf .claude …'  DENY                        MINOR-2
git commit -am 'fix: rm -rf .claude no longer allowed'  DENY               MINOR-3
git commit -m'guard: rm -rf .claude no longer allowed'  DENY               MINOR-3
```

`git commit -am` and `-m'glued'` also deny on main (main exempts nothing), so
they are gaps in the new exemption, not regressions.

## Timing

Median of five whole-hook calls (including the ~19 ms process baseline), host
load 2.55/2.89/3.10 with seats live. Same harness, same fixture, both trees.

| command | CR2r | CR2rb | cap | met |
|---|---|---|---|---|
| `git status` (baseline) | 21.9 ms | 18.6 ms | — | — |
| 200 path tokens | 77.1 ms | **139.8 ms** | 150 ms | yes, 7% headroom |
| 200 `.claude` path tokens | 75.6 ms | 138.9 ms | — | yes |
| 200 symlink tokens | 86.7 ms | **153.5 ms** | 300 ms | yes |
| `rm` × 200 symlink tokens | 83.6 ms | 150.8 ms | — | yes |

Both bats timing tests (`:643`, `:661`) pass here — `[ "$median" -lt 150 ]` and
`[ "$median" -lt 300 ]`. The cost is `tokenise_ctx`: a bash character loop over
the raw command, ~3000 iterations for a 200-token command, where the old
pipeline did three parameter expansions. The runbook
(`docs/runbooks/session.md:194-199`) states **73 ms and 83 ms** — those are
cr15's measured *CR2r* figures, not this tree's, and the commit body's claim
"the timing figures are corrected" is false (MINOR-4).

## Checks

Run in the clone, `XDG_CACHE_HOME` under the session scratchpad.

| check | command | rc | result |
|---|---|---|---|
| shellcheck | `nix develop -c shellcheck tools/orchestrator-guard.sh` | **0** | clean |
| bats 91 | `nix develop -c bats tests/unit/91-orchestrator-guard.bats` | **0** | `1..86`, **86 ok**, no `not ok` |
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **0** | `1..353`, **353/353** |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **0** | pass |
| pre-commit | `nix develop -c githooks/pre-commit` | **0** | treefmt `All checks passed!`, 94 files, **0 changed**; then the known board-staleness note |
| MAP | `repomap.py --root . write` | — | **identical** to the committed `docs/MAP.md` |

`pre-commit` leaves `docs/OPERATIONS.md` modified (the derived queue block).
Reverted; `git status --porcelain` empty.

### The shfmt hazard (item 9) — still guarded

treefmt reports **0 changed files** on this tree, so the `canon_result[$idx]`
hoist survives the formatter. `X-SHFMT` — the write respelled
`canon_result[$i / $bi]` while the reads stay on `$idx` — fails **29** tests
(16 17 18 22 43 44 45 46 47 48 55 60 61 62 63 64 65 66 67 68 71 72 74 76 78 80
81 82 84). A recurrence would be loud, not silent.

## Red before green

CR2r's guard (`git -C /home/dalhaka/factory/ws/cr15/CR2r show
task/CR2r:tools/orchestrator-guard.sh`, 1098 lines) copied over the clone's
guard, CR2rb's tests kept. Tree asserted changed (`git diff --numstat` →
`83 292 tools/orchestrator-guard.sh`), bats run, restored, re-run green.

```
1..86
not ok 80 bash: the git commit -m exemption ends at the message word (a newline or bare word after it is scanned)
not ok 81 bash: git clean force and git stash untracked read flag clusters and skip subcommand words
not ok 82 bash: an extract whose cwd is inside .claude with no destination denies
not ok 83 bash: flags are clause-local so a flag in one clause does not arm another
not ok 84 bash: chmod/chown/chattr on the .claude directory deny
ok     85 write: a third protected file entry in the list is honoured (no early break in main)
not ok 86 ORCHESTRATOR_GUARD=off lift prints one stderr line
```

Six of the seven new tests are red on CR2r — the newline cases, the cluster
cases, the extract-into-cwd cases, the clause-local cases, the directory chmod
and the lift line. Test **85** passes on CR2r honestly: CR2r's `main` loop
already had no early break (that was cr15's MINOR-4 — *unpinned*, not broken), so
85 is a new pin of existing behaviour, and **M-F** proves it bites. After
`git checkout --`, `git status --porcelain` empty and 86/86 green. No test for
the runbook sentences exists (the plan's Step-1 list named them; they are prose).

## Mutation table

Each mutation applied to `tools/orchestrator-guard.sh` in the clone, the tree
asserted changed (`numstat` printed per row), the full bats file run, then
reverted; `git status --porcelain` empty after every batch (`ALL REVERTED: []`).
Scripts: `…/scratchpad/{mutate.py,runmut.sh}`.

### The five (ten) CR2rb demands

| # | mutation | numstat | fails | killed by |
|---|---|---|---|---|
| **M-A** | the exemption extended to the token after the quoted run (`:733-736`) | 1+/0− | **1** | 80 |
| **M-A2** | bare words after `-m` exempt (the quoted test replaced by "exactly one token") | 1+/1− | **2** | 75 80 |
| **M-B** | the cluster test anchored to a leading `f` (`-*f*` → `-f*`, `:702`) | 1+/1− | **1** | 81 |
| **M-B2** | subcommand words taken as pathspecs (`:1080` deleted) | 0+/1− | **1** | 81 |
| **M-C** | the extract cwd check removed (`:929`) | 1+/1− | **1** | 82 |
| **M-D** | whole-command flag attribution restored (`clause_of[i]=0`, `:679`) | 1+/1− | **1** | 83 |
| **M-E** | directory `chmod` not denied (`ovr_dir_seen` dropped at `:893`) | 1+/1− | **1** | 84 |
| **M-F** | a `break` added to the Edit/Write loop in `main` (`:1275`) | 1+/0− | **1** | 85 |
| **M-G** | the lift's stderr line removed (`:1221`) | 0+/1− | **1** | 86 |
| **M-H** | the raw-text fallback's hard-coded plans path restored (`:821`) | 1+/1− | **0** | **SURVIVES — unpinned (MINOR-5)** |

Nine of ten. M-H is the case the plan itself allowed for ("a test fails **or say
unpinned**"): with only one `dir` entry in the shipped list the literal and the
derived pattern are behaviourally identical, and no test adds a second entry.

### cr15's eleven, re-applied — all still die

| # | mutation | numstat | fails | killed by |
|---|---|---|---|---|
| M-A | the plans entry deleted from `PROTECTED_PATHS` (`:114`) | 0+/1− | **20** | 16 17 18 22 24 25 28 30 31 33 34 35 36 43 44 45 46 47 48 80 |
| M-B | the override entry deleted (`:115`) | 0+/1− | **20** | 55 57 58 59 60 62 63 64 65 66 67 68 69 71 72 74 78 80 82 84 |
| M-C | the `write_verdict` list loop `break`s after the first entry (`:645`) | 1+/0− | **17** | 55 60 62 63 64 65 66 67 68 71 72 74 76 78 80 82 84 |
| M-D | the glob/raw-text fallback disabled (`:809`) | 1+/1− | **1** | 71 |
| M-E | `git stash -u`/`-a` dropped from the family (`:703`) | 1+/1− | **2** | 72 81 |
| M-F | `tar` dropped from the extract arm (`:914`) | 1+/1− | **2** | 72 82 |
| M-G | `git clean -n` treated like `-f` (`:1046`) | 1+/1− | **2** | 73 83 |
| M-H | the `-m` exemption removed (`:726`) | 1+/0− | **1** | 75 |
| M-I | the batched `realpath` replaced by per-token resolution (`:766-769`) | 1+/2− | **1** | 54 |
| M-J | the lift flag read from the payload text (`main`) | 4+/5− | **1** | 78 |
| M-K | the lift flag ignored entirely (`:1220-1223`) | 0+/4− | **2** | 77 86 |

### Extra probes of mine

| # | mutation | numstat | fails | reading |
|---|---|---|---|---|
| **X-SHFMT** | `canon_result` write respelled `[$i / $bi]` | 1+/1− | **29** | the shfmt regression stays loud |
| **X-MAINBRK** | `break` in `main`'s Edit/Write loop (= M-F) | 1+/0− | **1** (85) | cr15's survivor is now killed |
| **X-WVBRK** | `break` in `write_verdict`'s list loop | 1+/0− | **17** | the shared loop is pinned on all arms |

**20 of 21 demanded mutations die; cr12's and cr15's tables are fully covered.**

## Findings

### MAJOR-1 — a quoted `|`, `;`, `&` or newline splits the clause, so a trailing flag no longer arms its verb: `sed 's|a|b|' -i <plan>` ALLOWS

`tokenise_ctx` emits an operator token for `;`, `&`, `|`, `(`, `)`, `{`, `}`, `>`
and for a newline **without ever consulting `$inq`**
(`tools/orchestrator-guard.sh:234-305`):

```bash
      '|')
        _ctx_emit
        [ "${s:i+1:1}" = '|' ] && i=$((i + 1))
        m_toks+=('|')
        m_quoted+=("$inside")
        m_nlsep+=(0)
```

The clause splitter then increments on exactly those tokens
(`:672-681`):

```bash
      case "${toks[i - 1]}" in
        ';' | '&' | '|') cid=$((cid + 1)) ;;
      esac
      [ "${nlsep[i]}" -eq 1 ] && cid=$((cid + 1))
```

and CR2rb's new clause-local attribution (`:693-704`) requires the flag and the
verb to share a clause. So a quoted argument holding a `|`, `;`, `&` or a newline
pushes everything after it into a later clause, and the flag that follows it is
credited to that later clause instead of to its verb. Measured, `cwd = <proj>`,
each row also run against main and CR2r:

```
                                                     main    CR2r    CR2rb
sed 's|a|b|' -i docs/superpowers/plans/x.md          DENY    DENY    ALLOW
sed -e 's|/old/path|/new/path|' -i <plan>            DENY    DENY    ALLOW
sed -e 's/a/b/' -e 's|c|d|' -i <plan>                DENY    DENY    ALLOW
perl -pe 's|a|b|' -i <plan>                          DENY    DENY    ALLOW
sed 's/a;b/c/' -i <plan>                             DENY    DENY    ALLOW
sed 's/a&b/c/' -i <plan>                             DENY    DENY    ALLOW
sed -e 's/a/⏎b/' -i <plan>                           DENY    DENY    ALLOW
perl -pe 's/a/⏎b/' -i <plan>                         DENY    DENY    ALLOW
find docs/superpowers/plans -name 'a|b' -delete      DENY    DENY    ALLOW
```

Seven of those are **plans-dir regressions against main** — in-place rewrites and
deletions of a plan file that main refuses today. And on the override side, four
write/removal spellings of the protected path ALLOW:

```
                                                     main    CR2r    CR2rb
sed 's|a|b|' -i .claude/ritual-override              allow¹  DENY    ALLOW
sed -e 's/a|b/c/' -i .claude/ritual-override         allow¹  DENY    ALLOW
find .claude -name 'a|b' -delete                     allow¹  DENY    ALLOW
git clean 'a|b' -f                                   allow¹  ALLOW   ALLOW
git stash 'a|b' -u                                   allow¹  DENY    ALLOW
tar 'a|b' -x -C .claude                              allow¹  DENY    ALLOW
cpio 'a|b' -idm                                      allow¹  ALLOW   ALLOW
```

¹ main has no override rule at all.

`sed 's|a|b|' -i file` is not adversarial: pipe delimiters are the standard way
to write a sed substitution over a path, and a flag after the script is exactly
the spelling og4 raised as MAJOR 17 and og5 closed. `sed -i 's|a|b|' <plan>`
still denies (the flag precedes the quoted script), so the hole depends only on
argument order.

`{`, `}`, `(`, `)` and `>` are emitted as operator tokens too but do **not**
increment the clause id, so `find <plan-dir> -name '{x}' -delete` still denies.
The exposure is `;`, `&`, `|` and newline.

The header comment the implementer wrote for `tokenise_ctx` (`:204-207`) states
the opposite of what the code does:

```
#   NLSEP[i] is 1 when a newline separated token i from the token before it (a
#   clause boundary — but NOT the newline folded inside a quoted string, which
#   stays part of the quoted argument).
```

The `$'\n'` arm at `:302-306` has no `inq` test, so a newline inside a quoted
string *is* recorded as a boundary. (The `-m` exemption survives this only
because it keys on `quoted[]`, which *is* tracked correctly, not on `nlsep[]`.)

Fix shape: make the operator arms — at minimum `;`, `&`, `|` and `$'\n'` —
conditional on `[ -z "$inq" ]`, emitting the character into `buf` when inside a
quote. That restores the tokeniser's own documented contract and closes every row
above. Red tests first: `sed 's|a|b|' -i <plan>`, `perl -pe 's|a|b|' -i <plan>`,
`sed 's/a&b/c/' -i <plan>`, `find <plan-dir> -name 'a|b' -delete` and
`sed 's|a|b|' -i .claude/ritual-override` must all DENY, while
`rm -f result && git clean` and `ls -a && git stash` keep allowing.

### MINOR-1 — an extract at the project root (or any ancestor of `.claude`) denies

`tools/orchestrator-guard.sh:929-938`:

```bash
          if [ "$has_dest" -eq 0 ]; then
            base=${bases[${base_of[i]}]}
            for kk in "${!file_dirs[@]}"; do
              if is_protected_dir_or_ancestor "$base" "${file_dirs[kk]}" "$project_canon"; then
```

`is_protected_dir_or_ancestor` returns true for the project root, which is an
ancestor of `.claude`, so any destination-less extract run from the repo root
denies:

```
tar -xf /tmp/a.tar        cwd=<proj>   DENY   (main and CR2r: allow)
tar -xzf /tmp/x.tar.gz    cwd=<proj>   DENY
unzip /tmp/a.zip          cwd=<proj>   DENY
cpio -idm                 cwd=<proj>   DENY
tar -xf /tmp/a.tar        cwd=<proj>/sub   allow   (correct)
```

The plan's contract says "when the cwd (or a cd-rebased base) is a protected
directory **or an ancestor** → deny", so the implementer built what was written;
the gate matrix's row 3 ("the same with cwd at the project root and no path →
allow") is the one that loses. Deny-only, no documented recipe hit (nothing in
the repo extracts an archive), but the runbook's over-denial paragraph does not
mention it. This is also why `tar -x -f a.tar && ls .claude` still denies — not
flag leakage.

### MINOR-2 — only the first `-m` is exempt

`:729-740` `break`s out of the argument walk at the first `-m`/`--message`:

```bash
      if [ "${toks[m]}" = "-m" ] || [ "${toks[m]}" = "--message" ]; then
        s=$((m + 1))
        while [ "$s" -lt "$n" ] && [ "${quoted[s]}" -eq 1 ]; do
          skip[s]=1
          s=$((s + 1))
        done
        break
      fi
```

Measured: `git commit -m 'subject' -m 'body: rm -rf .claude no longer allowed'`
→ **DENY**. The gate matrix's item 1 asks for "two `-m` arguments → both exempt,
the rest scanned". Deny-only; a two-`-m` commit is not a documented recipe here
(the house uses `-F <msgfile>`). Drop the `break` and keep walking.

### MINOR-3 — `-am` and `-m'glued'` get no exemption

```
git commit -am 'fix: rm -rf .claude no longer allowed'   DENY
git commit -m'guard: rm -rf .claude no longer allowed'   DENY
git commit --message 'guard: rm -rf .claude …'           allow  (correct)
```

The exemption tests the token for equality with `-m`/`--message` only. Both also
deny on main, so these are gaps in the new exemption rather than regressions.

### MINOR-4 — the runbook's timing figures are CR2r's, and the commit body claims they were corrected

`docs/runbooks/session.md:194-199`:

```
single `realpath` call, so a 200-path-token command measures 73 ms and a
200-symlink-token command 83 ms (median of three, `$EPOCHREALTIME` in
tests/unit/91-orchestrator-guard.bats) — both well under the 150 ms / 300 ms
caps
```

73 ms and 83 ms are exactly cr15's measured numbers for **CR2r**. This tree
measures **139.8 ms** and **153.5 ms** on the same harness under the same load
(CR2r re-measured at 77.1 / 86.7 in the same session), so the path-token figure
is off by 1.9× and now sits 7% under its own cap. The commit body says "the
timing figures are corrected"; they were carried over unchanged. The bats tests
still pass, but a slower host or a longer command will make test at `:643` the
first thing to go red.

### MINOR-5 — the raw-text fallback's derivation is unpinned

`M-H` (restoring `case "$raw" in *superpowers/plans/*` at `:821`) changes the
tree and kills **zero** of 86 tests. With one `dir` entry in the shipped list the
two spellings are indistinguishable; the discriminating test would add a second
`dir` entry, as test 85 does for the `file` kind. I verified by hand that the
derived form does honour a second entry (see item 5), so this is a coverage gap,
not a defect.

### MINOR-6 — test 82's payload puts `cwd` inside `tool_input`

`tests/unit/91-orchestrator-guard.bats:1049,1058`:

```bash
  p=$(python3 -c '…json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1],"cwd":sys.argv[2]}}…)' "$cmd" "$PROJECT/.claude")
```

Real Claude Code PreToolUse payloads carry `cwd` at the **top level**; every
other test uses `bpayload`, which carries none. The test passes only because
`json_string` scans the whole payload for `"cwd"`. It happens to still exercise
the rule (I reproduced all three rows with a top-level `cwd`), but the fixture
does not match the shape the hook actually receives.

### MINOR-7 — `_ctx_emit` leaks into the shell's function namespace

`tokenise_ctx` defines `_ctx_emit()` inside itself (`:216-227`); bash has no
function-local functions, so the definition persists after the call and closes
over the caller's locals by dynamic scope. It works, and shellcheck is clean, but
a second definition anywhere would silently win. Cosmetic.

### NOTE — the implementer's claims, checked

| claim | verdict |
|---|---|
| "four majors … fixed" | **true** — all four cr15 MAJORs deny on every spelling the review listed, and the four plans newline spellings match main again |
| "all eight minors fixed" | **six true, two partial** — the sibling glob is now documented (not narrowed, which the plan chose), the flag scan is clause-local, the directory `chmod` denies, the Edit/Write break is pinned (M-F kills 85), the lift prints one line, the hard-coded plans path is gone and both `dir` entries are honoured; the *timings* were not corrected (MINOR-4) and the raw-text derivation is unpinned (MINOR-5) |
| "86/86 guard tests" | **true** — `1..86`, no `not ok`; `unit` 353/353, `lint` pass, shellcheck rc 0 |
| "both trailers present, one commit" | **true** — `Generated-By` and `Co-Authored-By`, one commit, subject byte-identical, three files, all in `touches`, no board commit |
| "the timing figures are corrected" (commit body) | **false** — 73/83 are CR2r's; this tree measures 139.8/153.5 |

## Verdict

**REJECTED** — one MAJOR.

CR2rb does the job it was re-planned for, and does it well. The `-m` exemption
now ends where it should: all ten newline spellings of the cr15 review deny, the
four plans ones matching main again, an unquoted word after `-m` is scanned, and
`git commit -m "x" -F k` no longer swallows the `-F`. Flag clusters are read as
clusters — `-df`, `-xdf`, `-dxf`, `-au`, `-ua` all deny — and `push`/`save` are
no longer mistaken for pathspecs, so `git stash push -u` denies while `git stash
push -m 'wip'` allows. An extract with no destination judges the payload cwd, so
`cpio -idm` inside `.claude` denies. Flags are clause-local, which withdraws
three over-denials including og5's long-standing `sed -n … | grep -i` refusal.
The folded minors land: the directory `chmod` denies, the Edit/Write no-break is
pinned by a mutation that used to survive, the lift prints exactly one stderr
line and is still unreachable from a payload, and the last hard-coded path is
gone with both `dir` entries provably honoured. 182 historic rows reproduce with
zero mismatches, 50 of 50 documented recipes allow, 20 of 21 demanded mutations
die, the checks are green and the commit conventions are clean.

What fails is the mechanism the clause-local fix was built on. `tokenise_ctx`
emits `;`, `&`, `|` and newline as clause boundaries even when they sit inside a
quoted argument — contradicting its own header comment — and the new per-clause
flag attribution then credits a trailing flag to the wrong clause.
`sed 's|a|b|' -i docs/superpowers/plans/x.md` allows. So do the `perl` form, the
`;`/`&`-in-script forms, the real-newline forms, `find <plan-dir> -name 'a|b'
-delete`, and the same shapes aimed at `.claude/ritual-override`. Seven of them
are writes to a plan file that **main denies today**, which is the same class of
regression that sank CR2r — introduced this time by the fix for a MINOR rather
than by the fix for a MAJOR. Pipe-delimited sed with the flag after the script is
ordinary usage, not a probe.

A re-plan should be XS/S and is one function wide: gate the `;`, `&`, `|` and
`$'\n'` arms of `tokenise_ctx` on `[ -z "$inq" ]` so a quoted metacharacter goes
into `buf` like any other byte, keeping the `quoted[]` machinery the `-m`
exemption depends on exactly as it is. Red tests first — `sed 's|a|b|' -i
<plan>`, `perl -pe 's|a|b|' -i <plan>`, `sed 's/a&b/c/' -i <plan>`, `find
<plan-dir> -name 'a|b' -delete`, `sed 's|a|b|' -i .claude/ritual-override` — with
`rm -f result && git clean` and `ls -a && git stash` kept green. Fold in MINOR-2
(drop the `break` after the first `-m`), MINOR-4 (measure and restate the runbook
numbers, and say whether 140 ms under a 150 ms cap is the budget the project
wants), MINOR-1 (decide between the plan's "ancestor → deny" and the matrix's
"project root → allow", then document whichever) and MINOR-5 (a second `dir`
entry in the raw-fallback test). Nothing else here needs to move.
