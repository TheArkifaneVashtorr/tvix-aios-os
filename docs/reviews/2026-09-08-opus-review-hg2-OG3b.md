---
plan_defect: wrong-fact
plan_defect_secondary: missing-case
mutants_total: 15
mutants_killed: 14
mutants_outside_named: 4
---
# Opus gate — seat run hg2, task OG3b — REJECTED

## Summary

The fix round closes the thing OG3 was rejected for. `SELF_CANON` is computed once at
the top of the guard (`tools/orchestrator-guard.sh:204`) and joins the `file` facts of
both arms (`:783-785`, `:1521-1524`), so the guard now refuses writes to the file it is
executing from whatever `CLAUDE_PROJECT_DIR` names. Measured with the branch guard placed
at a fake checkout and the project set to a fake seat workspace — the deployment shape —
the prior review's five ALLOW rows all flip:

```
DENY   printf x > <checkout>/tools/orchestrator-guard.sh   [orchestrator-guard.sh is the operator's; ask for it]
DENY   cp /tmp/g.sh <checkout>/tools/orchestrator-guard.sh [orchestrator-guard.sh …]
DENY   rm -f <checkout>/tools/orchestrator-guard.sh        [orchestrator-guard.sh …]
DENY   sed -i s/a/b/ <checkout>/tools/orchestrator-guard.sh[orchestrator-guard.sh …]
ALLOW  cat / bash / grep -n PROTECTED <checkout>/tools/orchestrator-guard.sh
ALLOW  cp <checkout>/tools/orchestrator-guard.sh /tmp/g.sh
ALLOW  printf x > <scratch>/other/orchestrator-guard.sh
ALLOW  sed -i s/a/b/ <this gate's own clone>/tools/orchestrator-guard.sh
```

Seventeen write verbs on the absolute self path deny (`sed -i`, `tee`, `>`, `>>`, `cp`,
`install`, `ln`, `rm`, `rm -f`, `mv` both directions, `truncate`, `chmod`, `touch`, `dd
of=`, `git checkout --`, `git restore`). All four acceptance checks are green under
`--rebuild`, the eight named mutants A–H all die, OG3's A, B and D still die, the seven
ancestor rows and the header `# rows: 455` are in the sweep, the reason branches (i)/(j)/(k)
are pinned, the duplicate `local` is gone and the header contract gains rule 4. Verdict
parity is exact: all 442 pre-existing sweep rows produce byte-identical decision AND reason
through main's guard and this one, and against OG3's guard only row 455 moves — the
intended MINOR-4 fix. One commit, subject byte-identical, nothing outside `touches`.

It is rejected on one measured hole, and it is in the clause the plan added for exactly
this reason. Contract item 2 requires `~/`, `$HOME/` **and `${HOME}/`** to expand. The
first two do. `${HOME}/` does not, because the tokeniser makes `{` and `}` word boundaries
(`:358`) long before `lex_norm` ever sees the token, so the `\$\{HOME\}/*` arm at `:616` is
unreachable from the Bash arm. Against the guard executing from that very file, from a
fake workspace, with `HOME` the checkout's parent:

```
DENY   printf x > $HOME/nixos-agent-env/tools/orchestrator-guard.sh   [orchestrator-guard.sh is the operator's; ask for it]
ALLOW  printf x > ${HOME}/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  sed -i s/deny/allow/ ${HOME}/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  cp /tmp/evil.sh ${HOME}/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  rm -f ${HOME}/nixos-agent-env/tools/orchestrator-guard.sh
```

One pair of braces and a seat still edits the rules it obeys. The arm is dead code:
deleting `:616` alone (mutant X2) leaves all 136 tests green. The plan named the spelling
in item 2 but named a mechanism that cannot deliver it and a test (h) that covers only the
other two — `wrong-fact`, secondary `missing-case`.

## Contract items

Line numbers are `595b6ab`'s.

1. **The guard protects the file it is executing from, in every project — MET, except the
   `${HOME}/` spelling of item 2 (MAJOR-1).**
   - `SELF_CANON=$(realpath -- "${BASH_SOURCE[0]}")` at `:204`, file top level, before
     `main` and outside every function — "computed once at startup, never in a subshell
     inside a rule function" is met by inspection.
   - Bash arm: `file_canons+=("$SELF_CANON")` / `file_dirs` / `file_reasons` at `:783-785`,
     feeding the token-equality check (`:949`), the `cp|install|ln` destination check
     (`:1180-1184`) and the redirect-destination check (`:1399-1403`). Measured above:
     independent of `CLAUDE_PROJECT_DIR`.
   - Write/Edit/MultiEdit arm: `:1521-1524` `if [ "$resolved" = "$SELF_CANON" ]; then deny
     "$GUARD_REASON"`. Measured: `Write`, `Edit` and `MultiEdit` payloads with `file_path`
     = the absolute self path all deny from the fake workspace (`MultiEdit -> {"…","permissionDecision":"deny","permissionDecisionReason":"orchestrator-guard.sh is the operator's; ask for it"}`).
   - The negative case (g), run three ways: a copy at `$BATS_TEST_TMPDIR/other/`, a copy at
     `<scratch>/other/`, and **this gate's own clone's** `tools/orchestrator-guard.sh` —
     all ALLOW while the executing guard sits elsewhere. The gates' mutant workflow is
     safe: the orchestrator's hook is `bash "$CLAUDE_PROJECT_DIR/tools/orchestrator-guard.sh"`
     (`.claude/settings.json:44,54`) with the project = the live checkout, so a scratch
     clone's copy is neither `SELF_CANON` nor the project-relative entry.
   - Tests (a)–(g) at `tests/unit/91-orchestrator-guard.bats:853, 861, 869, 881, 889, 902,
     911`, all through `run_guard_ws` (`:42`), i.e. `CLAUDE_PROJECT_DIR="$BATS_TEST_TMPDIR/ws"`
     (`:107-109`), a directory that is not the tree. Every denial asserts
     `*"orchestrator-guard.sh"*`.
2. **`~/`, `$HOME/`, `${HOME}/` expansion in `lex_norm` — NOT MET for `${HOME}/` (MAJOR-1).**
   `:611-617`. In isolation `lex_norm` does expand all three
   (`${HOME}/tools/g.sh -> /fakehome/tools/g.sh`), but the Bash arm never hands it a
   `${HOME}/…` token. Test (h) at `:918-931` covers `$HOME/` and `~/` only, and passes.
3. **Seven ancestor rows and the header `# rows: 455` — MET.**
   `tests/unit/91-orchestrator-guard-sweep.txt:1` `# rows: 455`; data rows counted 455; the
   last seven are exactly `rm -rf tools`, `mv tools tools2`, `chmod -R 755 tools`,
   `find tools -delete`, `rm -rf tools/*`, `git checkout -- tools`, `xargs rm < tools/list`,
   each DENY with the guard reason. The first 448 rows are byte-identical to OG3's file.
4. **The reason branches — MET.** (i) `:933`, (j) `:941`, (k) `:949` (which also asserts
   `[[ "$output" != *"ritual override"* ]]`). The machinery: `ovr_reason`/`ovr_reason_chosen`
   set in the ancestor branch (`:956-962`), the descendant branch (`:963-971`) and the glob
   fallback (`:975-986`), consumed at every `_ret=$ovr_reason` site.
5. **Housekeeping — MET.** One `local ovr_reason ovr_reason_chosen` (`:738`); `:730` is now
   `local plan_reason` alone. `nix develop -c shellcheck tools/orchestrator-guard.sh` exit 0.
   Header rule 4 added (`:34-45`), the rule count 4 → 5 (`:4`). Note the header's own line
   `:43-45` repeats the false `${HOME}/` claim.
6. **The commit body — MET in substance.** It pastes the seven reds, the greens, the mutant
   table A–H with a killing line each, OG3's A–D, and the FACTORY-RESULT block. Every
   number I re-ran matches (148 bats tests, 648 unit tests, four checks exit 0). It names
   the ancestor rows only as a class, not one by one (MINOR-6).

## Prior review, item by item

| hg1 finding | status |
|---|---|
| MAJOR-1 — the guard protects the workspace's copy, not the checkout it is read from | **CLOSED.** Measured above; the four write spellings on the absolute self path deny from a fake workspace. |
| MINOR-1 — `$HOME/…` is not a spelling the arms normalise | **PARTLY closed.** `$HOME/` and `~/` now deny; `${HOME}/` does not — MAJOR-1 of this round. |
| MINOR-2 — `tools/` silently a protected ancestor, untested and unmentioned | **CLOSED.** Seven sweep rows; the body names the class. |
| MINOR-3 — mutants I and J survive (two untested reason branches) | **CLOSED.** Tests (i)/(j); mutants F and G die. |
| MINOR-4 — the descendant path prints the ritual-override wording | **CLOSED.** Test (k); mutant H dies; sweep row 455's reason moved to the guard's. |
| MINOR-5 — `ovr_reason` declared `local` twice | **CLOSED.** `:730`, `:738`. |
| MINOR-6 — the header contract not updated | **CLOSED.** Rule 4, `:34-45`. |

## Red before green

The section's Step 1 red: the branch's tests against OG3's carried guard
(`git checkout fc97e47 -- tools/orchestrator-guard.sh` in a fresh clone), with everything
else at `595b6ab`:

```
$ nix develop -c bats tests/unit/91-orchestrator-guard.bats
not ok 66 bash: a redirect onto the guard's own absolute path is denied from the fake workspace
not ok 67 bash: sed -i on the guard's own absolute path is denied from the fake workspace
not ok 68 bash: cp onto the guard's absolute path is denied but reading from it is allowed
not ok 69 bash: rm -f the guard's own absolute path is denied from the fake workspace
not ok 70 write/edit: the Write and Edit tools on the guard's absolute path are denied
not ok 73 bash: ~/ and $HOME/ spellings of the guard's path are denied from the fake workspace
not ok 76 bash: xargs rm < tools/list denies naming the guard, not the ritual override
```

Exactly (a)–(e), (h), (k) — the commit body's list, verbatim. Restored
(`git checkout HEAD -- …`) → 136 ok, 0 not ok in that file; with `93-house-guard.bats`,
148 ok, 0 not ok. (i) and (j) are green against the carried guard, as the section says;
their falsifiability rests on mutants F and G, both of which die. (f) and (g) are ALLOW
assertions; (g)'s discriminating mutant is B, which dies.

OG3's own red is re-proven: with `nixosModules/seatLane.nix`'s `FACTORY_HOUSE_GUARD` line
deleted, `nix build .#checks.x86_64-linux.seat-eval -L --no-link` →
`error: attribute 'FACTORY_HOUSE_GUARD' missing at …/flake.nix:1703:13`, exit 1.

## Mutants

`mutants_total: 15`, `mutants_killed: 14`, `mutants_outside_named: 4`. Each applied in a
throwaway clone, run, reverted.

| id | mutation | killed by |
|---|---|---|
| A (named) | `:783` `file_canons+=("$SELF_CANON")` deleted | `not ok 66..69, 73` — `` `denied "$output"' failed `` (bats line 857) |
| B (named) | `:1401` redirect-dest compare by basename (`${_canon##*/}`) | `not ok 72 … a write to a different orchestrator-guard.sh elsewhere is allowed` / `` `[ -z "$output" ]' failed `` (line 915) |
| C (named) | `:1521-1524` the Write/Edit `SELF_CANON` block deleted | `not ok 70 write/edit: … the guard's absolute path are denied` / `` `denied "$output"' failed `` (line 893) |
| D (named) | `:614-617` the `$HOME`/`${HOME}` case removed from `lex_norm` | `not ok 73 … ~/ and $HOME/ spellings …` / `` `denied "$output"' failed `` (line 924) |
| E (named) | sweep header `455` → `448` | `not ok 124 the guard never raises …` / `sweep data-row count 455 does not match header 448` (line 1622) |
| F (named) | `:958-961` the ancestor branch's reason assignment removed | `not ok 74 … rm -rf tools denies naming the guard` / `` `[[ "$output" == *"orchestrator-guard.sh"* ]]' failed `` (line 938) |
| G (named) | `:975-986` the glob/raw-text fallback removed | `not ok 75 … rm -rf tools/* …` / `` `denied "$output"' failed `` (line 945); also `not ok 88` |
| H (named) | `:966-969` the descendant branch left without a reason | `not ok 76 … xargs rm < tools/list …` / `` `[[ "$output" == *"orchestrator-guard.sh"* ]]' failed `` (line 954) |
| OG3-A (named in Step 4) | the relative `'tools/orchestrator-guard.sh\|file'` entry removed | `not ok 60..64` (OG3's five deny tests) |
| OG3-B (named in Step 4) | the entry's kind `file` → `dir` | `not ok 63 … rm … with the file reason` / `` `[[ … *"orchestrator-guard.sh"* ]]' failed `` (line 821), plus 60, 61, 62, 64, 74 |
| OG3-D (named in Step 4) | `seatLane.nix`'s `FACTORY_HOUSE_GUARD` line removed | `seat-eval`: `error: attribute 'FACTORY_HOUSE_GUARD' missing`, exit 1 |
| X1 (extra) | `:204` → `SELF_CANON=${BASH_SOURCE[0]}` (no `realpath`) | `not ok 66..70, 73` — 6 red |
| X2 (extra) | `:616` only — the `\$\{HOME\}/*` arm alone deleted | **SURVIVES** — 0 not ok of 136 (MAJOR-1's evidence) |
| X3 (extra) | `:1522` `deny "$GUARD_REASON"` → `deny "$OVERRIDE_REASON"` | `not ok 70` |
| X4 (extra) | `SELF_CANON` moved into `write_verdict` (a subshell inside a rule function) | `not ok 70` only — killed incidentally by (e), not by any placement assertion (MINOR-5) |

OG3-C (the sweep header left at 442) is the same assertion and the same failure line as E
and was not re-run separately.

## Checks

Fresh clone `git clone -q --branch task/OG3b …`, all four built and then re-run with
`--rebuild` (a bare `--rebuild` errors when the derivation was never built here, so each is
`nix build … -L --no-link` followed by `nix build … -L --no-link --rebuild`):

| check | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass, exit 0 (`unit-tests> ok 648 no banner and no rollout refuses the usage source …`) |
| `… seat-eval …` | pass, exit 0 (`checking outputs of '…-seat-eval-ok.drv'`) |
| `… host-core …` | pass, exit 0 (`checking outputs of '…-nixos-system-core-26.05.20260903.a5cc6f2.drv'`) |
| `… lint …` | pass, exit 0 (`lint> Found 0 warnings and 0 errors.`) |
| `nix develop -c bats tests/unit/91-orchestrator-guard.bats tests/unit/93-house-guard.bats` | `--count` 148; 148 ok, 0 not ok, exit 0 |
| `nix develop -c shellcheck tools/orchestrator-guard.sh` | exit 0 |
| `python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | clean, exit 0 |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |
| `nix develop -c githooks/pre-commit` | exit 1 — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` |

No python changed, so no `ruff` run is owed.

The `pre-commit` exit 1 is the same artefact hg1's gate recorded and is **not** a defect of
this branch: the derived queue is read from the git log's subjects, so once `595b6ab`
exists the block drops `OG3b` (`-… CR4 OG3b PW1glm …` → `+… CR4 PW1glm …`). The board is
correctly left uncommitted; verdict-neutral, and the working tree was restored.

**Verdict parity.** All 455 sweep rows driven through OG3's carried guard (`fc97e47`) and
this branch's guard, same fixture project, capturing decision *and* reason, 0 bytes of
stderr from both runs:

```
$ diff old455.out new455.out
455c455
< DENY   xargs rm < tools/list   [the ritual override is the operator's; ask for it]
---
> DENY   xargs rm < tools/list   [orchestrator-guard.sh is the operator's; ask for it]
```

One row, and it is item 4's intended fix. Against **main's** guard (`dcec8cd`) over the 442
pre-existing rows: `diff base442.out new442.out` → exit 0, byte-identical decision and
reason (172 ALLOW / 283 DENY over the 455). SD8's parity test (`93-house-guard.bats`, 12
tests) is green inside the 148.

## Touches and commit

`git diff dcec8cd..HEAD --name-only` → `flake.nix`, `nixosModules/seatLane.nix`,
`tests/unit/91-orchestrator-guard-sweep.txt`, `tests/unit/91-orchestrator-guard.bats`,
`tools/orchestrator-guard.sh` — five files, every one inside the section's `touches`.
Nothing outside; `docs/` untouched (so the plan file untouched, no board commit); `docs/MAP.md`
correctly unchanged.

One commit, `595b6ab`. Subject byte-identical to the section's `commit subject` (`cmp`
against line 68 of the plan: identical, 220 bytes). The body states the why, pastes the
reds, the greens, the mutant table and the FACTORY block; the two trailers follow a blank
line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run hg2)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

Driver record `/home/dalhaka/factory/runs/hg2/OG3b.result` confirmed:
`checks_verified: unit=pass seat-eval=pass host-core=pass lint=pass`,
`checks_verified_src: unit=run seat-eval=run host-core=run lint=run`, `touches_extra: 0`,
`touches_disclosed: 0`, `FACTORY-COMMITS 1`, head `595b6ab`, base `dcec8cd`, `wall_s: 1435`.

## Findings

### MAJOR-1 — the `${HOME}/` spelling of contract item 2 does not deny: a seat can still write the live guard with one pair of braces

`tools/orchestrator-guard.sh:616` (`\$\{HOME\}/*) p=${HOME:-}${p#\$\{HOME\}} ;;`) is
unreachable from the Bash arm. `tokenise_ctx` treats `{` and `}` as unquoted operators and
emits them as their own tokens (`:358`), so `${HOME}/nixos-agent-env/tools/orchestrator-guard.sh`
never reaches `lex_norm` as one token — it arrives as `$`, `{`, `HOME`, `}`,
`/nixos-agent-env/tools/orchestrator-guard.sh`, and that last token is an absolute path
that is neither `SELF_CANON` nor any protected entry.

Measured against the branch guard executing from `<home>/nixos-agent-env/tools/orchestrator-guard.sh`,
`CLAUDE_PROJECT_DIR` = a seat workspace, `HOME` = `<home>` (the deployed shape):

```
DENY   printf x > $HOME/nixos-agent-env/tools/orchestrator-guard.sh   [orchestrator-guard.sh is the operator's; ask for it]
DENY   printf x > "$HOME"/nixos-agent-env/tools/orchestrator-guard.sh [orchestrator-guard.sh is the operator's; ask for it]
ALLOW  printf x > ${HOME}/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  sed -i s/deny/allow/ ${HOME}/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  cp /tmp/evil.sh ${HOME}/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  rm -f ${HOME}/nixos-agent-env/tools/orchestrator-guard.sh
```

The shell expands `${HOME}` exactly as it expands `$HOME`, so the ALLOW rows write the live
guard. This is the plan's contract item 2 verbatim ("`lex_norm` expands a token's leading
`~/`, `$HOME/` or `${HOME}/`") and the file's own header claim (`:43-45`), and it is the
same threat MINOR-11 and hg1's MAJOR-1 name: a seat editing the rules it obeys. The clause
is dead code — mutant X2, deleting `:616` and nothing else, leaves all 136 tests in
`91-orchestrator-guard.bats` green (`notok_count=0`), because test (h) (`:918-931`) exercises
only `$HOME/` and `~/`.

The defect is the section's: item 2 prescribed the expansion in `lex_norm`, which is the
wrong place for a spelling the tokeniser destroys first (a `wrong-fact`), and item 2's test
(h) named only two of the three spellings, so nothing could catch it (`missing-case`). A
re-typed section should either expand `${HOME}` before tokenisation (in the raw command
text) or drop the `${HOME}/` clause explicitly and record the residue — and, whichever, name
a test for the third spelling.

### MINOR-1 — a python write to the guard's *absolute* path is allowed from a workspace, while the relative spelling denies

`tools/orchestrator-guard.sh:1015-1046` and `:1360-1380`: the raw-text fallbacks build their
needles from `rel` (the project-relative entry), never from `SELF_CANON`. Measured, guard
executing from the fake checkout, project = fake workspace:

```
ALLOW  python3 -c "open('<checkout>/tools/orchestrator-guard.sh','w').write('x')"
```

whereas `python3 -c "open('tools/orchestrator-guard.sh','w').write('x')"` with the project =
the tree denies (hg1's table). Item 1 specifies a token comparison and names tests (a)–(g),
none of them python, so this is a gap the section did not ask to close — but it is the same
control and it has no test and no sweep row.

### MINOR-2 — deleting or moving the checkout's `tools/` directory is allowed from a workspace

Measured, same fixture:

```
ALLOW  rm -rf <checkout>/tools
ALLOW  mv <checkout>/tools /tmp/x        (via mv <src> <dst>)
ALLOW  find <checkout>/tools -name '*.sh' -delete
```

`is_protected_dir_or_ancestor` is project-scoped by construction (`:671`), and the
implementer's comment at `:778-781` says so. The outcome is safe rather than exploitable —
Assumption 3's `_house_guard_verdict` denies on an unreadable guard, so removing the guard
fails closed and only self-DoSes the seat, and re-creating it is blocked (`cp /tmp/g <abs>`
denies) — but it is untested and the commit body does not mention it.

### MINOR-3 — `SELF_CANON`'s parent dir joins `file_dirs`, widening two branches outside the project, untested

`tools/orchestrator-guard.sh:784`. The descendant branch (`:963-971`) and the glob fallback
(`:975-986`) are *not* project-scoped, so from any project `rm -rf <checkout>/tools/*` and
`xargs rm < <checkout>/tools/list` now DENY (measured). The direction is safe and none of
the 442 pre-existing sweep rows moved, but the comment at `:778-781` claims the addition
"adds no ancestor denial beyond the project (and none at all when the project is the
workspace)", which these two branches contradict. No test, no sweep row, not in the body.

### MINOR-4 — `SELF_CANON` is computed before `main` installs the EXIT trap, and a failure would silently over-deny

`:204` runs at source time; the fail-closed EXIT trap is installed as `main`'s first
statement (`:1458`), and the script sets only `set -u` (`:114`), not `set -e`. If `realpath`
ever failed, `SELF_CANON` would be empty, `file_dirs` would gain `""`, and the descendant
pattern `""/*` would match every absolute token — every `xargs rm <abs>` would deny.
Unreachable in practice (the file is the one being executed); recorded, not owed.

### MINOR-5 — item 1's "never in a subshell inside a rule function" has no test

Mutant X4 moves the `$(realpath …)` into `write_verdict` and is killed only by test (e),
which fails because `main`'s comparison then reads an empty `SELF_CANON` — an accident of
scope, not an assertion about where the value is computed. The Bash-arm tests (a)–(d) all
stay green under X4. The clause is met by inspection (`:204`), not by a falsifiable test.

### MINOR-6 — the commit body names the seven ancestor rows only as a class

Item 3 asks that "the commit body names them as intended consequences of protecting a file
under `tools/`". The body says "pins the newly-protected tools/ ancestor rows in the sweep"
and lists no row. The rows themselves are correct and in the sweep
(`tests/unit/91-orchestrator-guard-sweep.txt:450-456`).

## Verdict

**REJECTED** on MAJOR-1. Everything else in the section lands and lands well: the
project-independent self-protection is real and measured from the deployment fixture, the
negative case holds for a scratch clone (including this gate's own), all eight named
mutants plus OG3's three re-run mutants die, the four checks are green under `--rebuild`,
455 sweep rows are verdict- and reason-identical to OG3's guard but for the one row item 4
set out to change, and 442 rows are identical to main's. But contract item 2 names three
spellings and one of them — `${HOME}/` — is allowed against the very file the guard is
executing from, so a seat can still overwrite the live guard, which is the whole point of
the task. `plan_defect: wrong-fact` (the expansion was specified in `lex_norm`, which the
tokeniser's `{`/`}` boundaries make unreachable for that spelling), secondary
`missing-case` (test (h) covers only two of the three spellings the same item requires).
