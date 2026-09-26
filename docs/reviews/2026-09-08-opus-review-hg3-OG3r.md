---
plan_defect: none
mutants_total: 22
mutants_killed: 19
mutants_outside_named: 6
model: opus
---
# Opus gate — seat run hg3, task OG3r — APPROVED

## Summary

The re-plan lands. The hole two rounds of text rules left open is closed twice over, and I
measured both halves red first.

**The mount.** `nixosModules/seatLane.nix:243-245` gives the `seat@` `serviceConfig`
`ReadOnlyPaths = [ "-/home/${cfg.operatorUser}/nixos-agent-env/tools/orchestrator-guard.sh" ]`
beside `ReadWritePaths`; `flake.nix:1766-1768` pins that exact one-element list; and
`tests/integration/seat-vm.nix` proves the effect from inside a real `seat@` instance —
`guard_write=1`, `guard_rename=1`, `guard_read=0`, each asserted with `grep -qx`
(`:488-490`) after the completeness wait grew 8 → 11 lines (`:477`). Removing the entry
kills the assertion (`error: attribute 'ReadOnlyPaths' missing`) and the VM probe
(`grep -qx 'guard_write=1' … failed (exit code 1)`) — I ran both.

**The text rule.** `tokenise_ctx` (`tools/orchestrator-guard.sh:370-386`) now keeps a
`${NAME}` parameter expansion inside its one word, so `lex_norm`'s `${HOME}/` arm
(`:641-644`) is reachable. Measured against the guard executing from a fake checkout with
`CLAUDE_PROJECT_DIR` = a fake seat workspace and `HOME` = the checkout's parent — the
deployment shape the hg2 gate used — every one of the prior review's ALLOW rows flips:

```
                                                                     hg2 (595b6ab)   this branch
printf x > ${HOME}/nixos-agent-env/tools/orchestrator-guard.sh          ALLOW            DENY
printf x > "${HOME}"/nixos-agent-env/tools/orchestrator-guard.sh        DENY             DENY
sed -i s/deny/allow/ ${HOME}/…/orchestrator-guard.sh                    ALLOW            DENY
cp /tmp/evil.sh ${HOME}/…/orchestrator-guard.sh                         ALLOW            DENY
rm -f ${HOME}/…/orchestrator-guard.sh                                   ALLOW            DENY
tee ${HOME}/…/orchestrator-guard.sh < /tmp/evil.sh                      ALLOW            DENY
mv /tmp/evil.sh ${HOME}/…/orchestrator-guard.sh                         ALLOW            DENY
truncate -s 0 ${HOME}/…/orchestrator-guard.sh                           ALLOW            DENY
rm -rf ${HOME}/nixos-agent-env/tools                                    ALLOW            DENY
rm -rf ${HOME}/nixos-agent-env/tools/*                                  ALLOW            DENY
cat / grep -n PROTECTED ${HOME}/…/orchestrator-guard.sh                 ALLOW            ALLOW
printf x > ${HOME}/nixos-agent-env/docs/other.md                        ALLOW            ALLOW
echo hi ; rm -rf /tmp/unrelated                                         ALLOW            ALLOW
```

All five acceptance checks are green under `--rebuild`, all sixteen named mutants (OG3r's
A–H and OG3b's A–H, both sets named by the section's Step 4) die on their claimed lines,
the 442 pre-existing sweep rows are byte-identical in decision **and** reason to main's
guard with zero stderr, one commit with a byte-identical subject, nothing outside
`touches`. Five MINORs, none gating: the commit body's ancestor-row list is wrong, the VM
probe substitutes `touch` for the section's `: >` (justified — I measured the
justification), three branches of the new tokeniser block have no falsifying test, two
exotic `${…}` spellings still reach the text rules, and the section's mutant E is
attributed to the wrong test.

## Contract items

Line numbers are `cd34211`'s.

1. **The kernel pin — MET.**
   - `nixosModules/seatLane.nix:243-245`, inside `serviceConfig`, immediately after the
     `ReadWritePaths` list (`:228-235`):
     ```
     ReadOnlyPaths = [
       "-/home/${cfg.operatorUser}/nixos-agent-env/tools/orchestrator-guard.sh"
     ];
     ```
     `cat -A` of `:244` shows the entry is the exact string the section names, `-` prefix
     included, and no other element. The comment (`:236-242`) says what the section asks:
     the file the hook runs as the house guard (`FACTORY_HOUSE_GUARD`, `:179`), a kernel
     mount, no write/unlink/rename-over from any process in the unit however a command
     spells the path, the `-` tolerating an absent checkout, the `~/factory/ws` copies
     untouched.
   - `flake.nix:1766-1768`:
     `sc.ReadOnlyPaths == [ "-/home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh" ]`
     with `sc = unit.serviceConfig` (`:1664`). The message is byte-identical to the
     section's — `cmp` against the section text: identical.
     ```
     seat-eval: seat@ must mount the tree's guard read-only (ReadOnlyPaths)
     ```
   - Mutant A (below): removing the entry is `error: attribute 'ReadOnlyPaths' missing`,
     exactly the red the section accepts.
2. **Proven from inside the unit — MET, with one deviation (MINOR-2).**
   `tests/integration/seat-vm.nix:439-461` adds three probes to `probe.sh` and
   `:466-471` creates the fixture before `systemctl start seat@probe.service` (`:473`):
   `mkdir -p /home/dalhaka/nixos-agent-env/tools`, one line written by `printf`,
   `chown -R dalhaka /home/dalhaka/nixos-agent-env`. The completeness wait is
   `wc -l … = 11` (`:477`, was 8) and each new line is asserted with `grep -qx`
   (`:488-490`). Green run, verbatim from the `--rebuild` log:
   ```
   machine: must succeed: grep -qx 'guard_write=1' /var/lib/seat/probe.out
   machine: (finished: … in 0.02 seconds)
   machine: must succeed: grep -qx 'guard_rename=1' /var/lib/seat/probe.out
   machine: (finished: … in 0.02 seconds)
   machine: must succeed: grep -qx 'guard_read=0' /var/lib/seat/probe.out
   machine: (finished: … in 0.02 seconds)
   ```
   The deviation: the section prescribes `if : > <path>; then echo guard_write=0; …`; the
   implementer wrote `if touch <path> 2>/dev/null; then …` with a comment claiming `: >`
   would abort the `sh` script. I measured the claim and it is true — `probe.sh` is
   `#!/bin/sh` (`:407`), `/bin/sh` here is bash-as-sh (POSIX mode), and a redirection
   failure on the special builtin `:` exits the script:
   ```
   $ /bin/sh p.sh          # p.sh: `if : > <0444 file>; then …; fi` then `echo REACHED_END`
   p.sh: line 1: …/f: Permission denied
   exit=1                  # REACHED_END never printed
   ```
   The literal probe would have left `probe.out` at 8 lines and hung the `wc -l = 11`
   wait. See MINOR-2 for what `touch` costs.
3. **`${HOME}` reaches the text rule — MET.**
   `tools/orchestrator-guard.sh:375-386`: inside the operator arm and only when unquoted,
   a `{` whose preceding buffer byte is `$` opens `_ctx_exp`, every operator byte is then
   buffered, and a `}` closes it. `:643-644` are `lex_norm`'s two arms. Test (h2) at
   `tests/unit/91-orchestrator-guard.bats:967-989` asserts the three commands the section
   names — `printf x > ${HOME}/tools/orchestrator-guard.sh`,
   `printf x > "${HOME}"/tools/orchestrator-guard.sh`, `rm -rf ${HOME}/tools` — all denied
   from the fake workspace with the guard reason; the bare-brace negative is test
   `:991-996` (`printf x > /tmp/{a,b}/orchestrator-guard.sh` ALLOW). Measured
   independently in the table above, and separators still separate:
   `echo hi ; rm -rf /tmp/unrelated` ALLOW, `sudo ${A:-x} true` DENY
   (`sudo is refused (an operator action)`), `echo ${A:-x} && rm -f $HOME/…/orchestrator-guard.sh`
   DENY.
4. **`SELF_CANON` under the trap — MET.** `:211` declares it empty at file scope;
   `:1537-1543` resolves it inside `main`, after the trap, and a `realpath` failure
   `warn`s `guard fault: …` and `exit 1` into the fail-closed EXIT trap. The consumer
   `:814-818` is guarded by `[ -n "$SELF_CANON" ]`, so an empty value adds no `""` parent
   to `file_dirs`. Test `:1004-1019` prepends a `realpath` that exits 1 and asserts the
   reason contains `guard fault` **and** does not contain the protected-path wording.
5. **The python needles — MET.** `:1421-1451` scans the raw text for `SELF_CANON` beside
   the relative names, with the same write/removal idiom gate (`os.remove`, `unlink(`,
   `write_text`, `open(` with `'w'`/`"w"`). Test `:1022-1029`:
   `python3 -c "open('$GUARD_ABS', 'w')"` from the fake workspace, denied.
6. **The descendant and glob branches — MET.** `:816`
   `file_dirs+=("${SELF_CANON%/*}")` retained; test `:1034-1042`
   (`rm -rf <tree root>/tools/*` from the fake workspace) denied, naming the guard.
7. **The header and the body — MET for the header, NOT for the body's ancestor rows
   (MINOR-1).** The header contract now reads "five rules" (`:4`) and rule 4 (`:34-50`)
   says exactly what the section asks: the mount is the seat's protection
   ("A seat runs inside `seat@`, whose ReadOnlyPaths mounts this very file read-only, a
   kernel pin no command spelling from a job can slip"), the text rules are the
   orchestrator's own session's ("the orchestrator runs in no unit, so no kernel mount
   holds its guard"). The body pastes the five reds and the eight greens and the A–H
   mutant table, and every number I re-ran matches (153 bats tests, 661 unit tests, five
   checks exit 0). It does **not** list OG3b's seven ancestor sweep rows one by one — see
   MINOR-1. `FACTORY-RESULT` / `FACTORY-CHECKS unit=pass seat-eval=pass seat-vm=pass
   host-core=pass lint=pass` / `FACTORY-COMMITS 1` are in
   `/home/dalhaka/factory/runs/hg3/OG3r.result`.

## Prior review, item by item

`docs/reviews/2026-09-08-opus-review-hg2-OG3b.md`:

| hg2 finding | status |
|---|---|
| **MAJOR-1** — the `${HOME}/` spelling writes the live guard from a seat | **CLOSED twice, each shown red first.** (a) The tokeniser: against the carried guard `595b6ab` the branch's test 77 is `not ok … the ${HOME} spellings … 'denied "$output"' failed`; against the branch it passes, and the ten write spellings in the Summary table all flip ALLOW → DENY. (b) The mount: `seat-vm` proves `guard_write=1`/`guard_rename=1` from inside `seat@`, and with `ReadOnlyPaths` removed the same VM reports `guard_write=0` — the write succeeded. Either pin alone closes it; both are in. |
| MINOR-1 — a python write to the guard's absolute path allowed from a workspace | **CLOSED.** `:1421-1451`, test `:1022`; mutant G kills it. |
| MINOR-2 — deleting the checkout's `tools/` from a workspace allowed | **CLOSED** for the glob/descendant form (`rm -rf <tree>/tools/*` denies, test `:1034`) and moot for a seat under the mount; `rm -rf <checkout>/tools` from a workspace still allows (the ancestor rule is project-scoped by construction) — the section chose the glob case and says so. |
| MINOR-3 — `SELF_CANON`'s parent widens two branches, untested | **CLOSED.** Test `:1034`; mutant H kills it. |
| MINOR-4 — `SELF_CANON` computed before the EXIT trap | **CLOSED.** `:1537-1541`; test `:1004`; mutants C and F kill it. |
| MINOR-5 — "never in a subshell" has no test | **Recorded, not closed** — the section restated the clause and it is still met by inspection only. Not owed by the section's test list. |
| MINOR-6 — the body names the ancestor rows only as a class | **NOT closed — regressed.** MINOR-1 below. |

## Red before green

Every red re-run by me in a fresh clone, then restored.

**1. The `seat-eval` assertion against the base module.** `nixosModules/seatLane.nix:243-245`
deleted (the base's shape), everything else at `cd34211`:

```
$ nix build .#checks.x86_64-linux.seat-eval -L --no-link
       error: attribute 'ReadOnlyPaths' missing
       at …/flake.nix:1767:13:
         1766|           assert nixpkgs.lib.assertMsg (
         1767|             sc.ReadOnlyPaths == [ "-/home/dalhaka/nixos-agent-env/tools/orchestrator-guard.sh" ]
             |             ^
         1768|           ) "seat-eval: seat@ must mount the tree's guard read-only (ReadOnlyPaths)";
exit=1
```

**2. The VM probe against the base module.** Same deletion, `seat-vm` built:

```
machine: must succeed: grep -qx 'guard_write=1' /var/lib/seat/probe.out
!!! RequestedAssertionFailed: command `grep -qx 'guard_write=1' /var/lib/seat/probe.out` failed (exit code 1)
error: Cannot build '/nix/store/f8dh775a…-vm-test-run-seat-behind-broker.drv'.
```

**3. The branch's tests against the carried guard** (`git checkout 595b6ab -- tools/orchestrator-guard.sh`,
everything else at `cd34211`):

```
$ nix develop -c bats tests/unit/91-orchestrator-guard.bats tests/unit/93-house-guard.bats
150 ok
not ok 77 bash: the ${HOME} spellings of the guard's path are denied from the fake workspace
#  in test file tests/unit/91-orchestrator-guard.bats, line 973)
#   `denied "$output"' failed
not ok 79 bash: a realpath failure fault-denies before an empty file_dirs entry
# (in test file tests/unit/91-orchestrator-guard.bats, line 1013)
#   `[[ "$output" == *"guard fault"* ]]' failed
not ok 80 bash: a python open(...,'w') of the guard's absolute path is denied from the fake workspace
#  in test file tests/unit/91-orchestrator-guard.bats, line 1026)
#   `denied "$output"' failed
```

Exactly the three the commit body claims, and no more: the glob test 81 is green against
the carried guard, as the body says, and rests on mutant H. Restored → 153 ok, 0 not ok.

Every new test is falsifiable: (h2) by D and E, the realpath-fault test by C and F, the
python test by G, the glob test by H, the bare-brace negative by nothing in the named set
(it is an ALLOW assertion; its discriminating mutant would be the inverse of D).

## Mutants

`mutants_total: 22`, `mutants_killed: 19`, `mutants_outside_named: 6`. Each applied in a
throwaway clone, run, reverted (`git status --porcelain` empty after each).

### Named by the section (16, all killed)

| id | mutation | killed by |
|---|---|---|
| A | `seatLane.nix:243-245` `ReadOnlyPaths` removed | `seat-eval`: `error: attribute 'ReadOnlyPaths' missing at …/flake.nix:1767:13`, exit 1 |
| B | the same removal, `seat-vm` built | `!!! RequestedAssertionFailed: command \`grep -qx 'guard_write=1' /var/lib/seat/probe.out\` failed (exit code 1)` |
| C | `SELF_CANON` resolved at source time (`:211`), the `main` block dropped | `not ok 79` / `(line 1013)` / `` `[[ "$output" == *"guard fault"* ]]' failed `` |
| D | `:375-386` the tokeniser's `${NAME}` join reverted | `not ok 77` / `(line 973)` / `` `denied "$output"' failed `` |
| E | `:644` `lex_norm`'s `${HOME}/` arm deleted | `not ok 77` / `(line 973)` / `` `denied "$output"' failed `` (the section attributes E to OG3b's test (h); it is (h2) — MINOR-5) |
| F | `:1540-1543` the failure arm removed (`… \|\| SELF_CANON=''`) | `not ok 79` / `(line 1013)` / `` `[[ "$output" == *"guard fault"* ]]' failed `` |
| G | `:1421-1451` the `SELF_CANON` python/perl needle dropped | `not ok 80` / `(line 1026)` / `` `denied "$output"' failed `` |
| H | `:816` the parent replaced by a non-matching dir (alignment kept) | `not ok 81 … rm -rf of the tree's tools/*` / `(line 1040)` / `` `denied "$output"' failed `` (also `not ok 77`) |
| OG3b-A | `:815` `file_canons+=("$SELF_CANON")` neutralised | `not ok 66, 67, 68, 69, 73, 77` — `` `denied "$output"' failed `` at lines 857, 865, 873, 885, 924, 973 |
| OG3b-B | `:1466` redirect destination compared by basename | `not ok 72 … a write to a different orchestrator-guard.sh elsewhere is allowed` / `(line 915)` / `` `[ -z "$output" ]' failed `` |
| OG3b-C | `:1594-1597` the Write/Edit `SELF_CANON` block deleted | `not ok 70` / `(line 893)` / `` `denied "$output"' failed `` |
| OG3b-D | `:642-645` the whole `$HOME`/`${HOME}` case removed | `not ok 73` (line 924) and `not ok 77` (line 973) |
| OG3b-E | sweep header `455` → `448` | `not ok 129 the guard never raises …` / `sweep data-row count 455 does not match header 448` (line 1708) |
| OG3b-F | `:989-995` the ancestor branch's reason assignment removed | `not ok 74` / `(line 938)` / `` `[[ "$output" == *"orchestrator-guard.sh"* ]]' failed `` |
| OG3b-G | `:1008-1019` the glob / raw-text fallback removed | `not ok 75` / `(line 945)` / `` `denied "$output"' failed `` (also 77, 81, 93) |
| OG3b-H | `:996-1003` the descendant branch left without a reason | `not ok 76` / `(line 954)` / `` `[[ "$output" == *"orchestrator-guard.sh"* ]]' failed `` |

### Outside the named set (6 tried, 3 killed)

| id | mutation | result |
|---|---|---|
| X1 | `seat-vm` with `ReadOnlyPaths` removed **and** the `guard_write=1` assertion deleted | **killed** — `` `grep -qx 'guard_rename=1' …` failed (exit code 1) ``. The rename probe is independently discriminating, not carried by the write probe. |
| X2 | the entry changed to the `tools` **directory** | **killed** — `error: seat-eval: seat@ must mount the tree's guard read-only (ReadOnlyPaths)` |
| X3 | the `-` prefix dropped from the entry | **killed** — same message. The assertion pins the exact string, not mere presence. |
| X4 | `:383` the `}` reset (`[ "$c" = '}' ] && _ctx_exp=0`) deleted | **SURVIVES** — 153 ok, 0 not ok (MINOR-3) |
| X5 | `:358` the per-call `_ctx_exp=0` reset at `tokenise_ctx` entry deleted | **SURVIVES** — 153 ok, 0 not ok (MINOR-3) |
| X6 | `:375` the `[ -z "$inq" ]` quoting guard dropped | **SURVIVES** — 153 ok, 0 not ok (MINOR-3) |

X4 is verdict-neutral on the probes I tried (`echo ${X} && printf x > $HOME/…/orchestrator-guard.sh`,
`echo ${X} ; printf x > …`, `echo ${X} ; rm -f …` all still DENY under it), so the three
survivors are untested branches, not a measured hole.

## Checks

Fresh clone `git clone -q --branch task/OG3r /home/dalhaka/factory/ws/hg3/OG3r …`; each
check built, then re-run with `--rebuild` (a bare `--rebuild` errors when the derivation
was never built here).

| check | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | pass, exit 0 (`unit-tests> ok 661 no banner and no rollout refuses the usage source …`) |
| `… seat-eval …` | pass, exit 0 (`checking outputs of '…-seat-eval-ok.drv'`) |
| `… seat-vm …` | pass, exit 0 (the eleven probe assertions all `finished`) |
| `… host-core …` | pass, exit 0 (`checking outputs of '…-nixos-system-core-26.05.20260903.a5cc6f2.drv'`) |
| `… lint …` | pass, exit 0 (`lint> Found 0 warnings and 0 errors.`) |
| `nix develop -c bats tests/unit/91-orchestrator-guard.bats tests/unit/93-house-guard.bats` | `--count` 153 (141 + 12); 153 ok, 0 not ok, exit 0 |
| `nix develop -c shellcheck tools/orchestrator-guard.sh` | exit 0 |
| `python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | clean, exit 0 |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |
| `nix develop -c githooks/pre-commit` | exit 1 — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` (MINOR-4) |

No `.py` file changed, so no `ruff` run is owed; `treefmt`, `statix`, `deadnix`, the js
arms and the prettier arms all passed inside the same `pre-commit` run before the queue
line.

**Verdict parity.** The 442 pre-existing sweep rows driven through main's guard
(`8f67fb9`) and this branch's, same fixture project, capturing decision **and** reason:

```
$ diff main442.out new442.out      # exit 0
PARITY_442_IDENTICAL
stderr_bytes=0                      # from both runs
```

The sweep is `# rows: 455` with 455 data rows; it is byte-identical to `595b6ab`'s (OG3b's
thirteen rows carried, none added by this round).

## Touches and commit

`git diff 8f67fb9..HEAD --name-only` → `flake.nix`, `nixosModules/seatLane.nix`,
`tests/integration/seat-vm.nix`, `tests/unit/91-orchestrator-guard-sweep.txt`,
`tests/unit/91-orchestrator-guard.bats`, `tools/orchestrator-guard.sh` — six files, every
one inside the section's `touches`. Nothing outside; `docs/` untouched, so the plan file is
untouched and there is no board commit; `docs/MAP.md` correctly unchanged. The driver record
`/home/dalhaka/factory/runs/hg3/OG3r.result` agrees: `touches_extra: 0`,
`touches_disclosed: 0`, `checks_verified_src: unit=run seat-eval=run seat-vm=run
host-core=run lint=run`, `FACTORY-COMMITS 1`, head `cd34211`, base `8f67fb9`, `wall_s: 4339`.

One commit, `cd34211`. Subject byte-identical to the section's `commit subject` (`cmp`
against line 88 of the plan: identical, 243 bytes + newline). The body states the why (two
rounds of text rules, "pin the environment, not the text"), pastes the five reds and the
eight greens and the A–H mutant table; the two trailers follow a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run hg3)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

## Findings

No MAJORs.

### MINOR-1 — the commit body does not list OG3b's seven ancestor sweep rows, and the seven things it does list are not ancestor rows

Contract item 7 requires "the commit body lists OG3b's seven ancestor rows one by one".
The body says:

> the seven ancestor rows it added — a redirect, sed -i, cp, rm -f, Write/Edit, ~/$HOME
> spellings, and xargs rm naming the guard, all from a fake workspace — still pass

Those seven are OG3b's **bats tests** (a)–(e), (h), (k), not sweep rows. The seven ancestor
rows are `tests/unit/91-orchestrator-guard-sweep.txt:449-455`: `rm -rf tools`,
`mv tools tools2`, `chmod -R 755 tools`, `find tools -delete`, `rm -rf tools/*`,
`git checkout -- tools`, `xargs rm < tools/list`. This is hg2's MINOR-6 restated by the
section and still not met — now with a wrong label attached. The rows themselves are
present and correct; only the body is wrong.

### MINOR-2 — the VM's write probe is `touch`, which is not a write

`tests/integration/seat-vm.nix:445-450`. The substitution is forced (see contract item 2 —
I measured that `: >` aborts `probe.sh`) and it is discriminating here (mutant B flips it
to `guard_write=0`), because a read-only bind mount returns `EROFS` to `utimensat` as well
as to `open(O_WRONLY)`. But `touch` and a content write are not the same test: on a file
the caller owns, `touch` succeeds even when the mode forbids writing —

```
$ ls -l f; /bin/sh t.sh          # t.sh: `if touch f 2>/dev/null; then echo guard_write=0; …`
-r--r--r-- 1 dalhaka users 2 … f
guard_write=0
```

— so the probe would pass a hypothetical pin that made the file read-only by mode rather
than by mount. A POSIX-safe content write (`if (printf x >> f) 2>/dev/null`, or
`sh -c ': > f'` in a child) would have tested the thing the mount protects. Also
`2>/dev/null` on the probe means a `touch` that failed for an unrelated reason would read
as `guard_write=1`; mutant B rules that out for this build but not by construction.

### MINOR-3 — three branches of the new tokeniser block have no falsifying test

`tools/orchestrator-guard.sh:375-386`. Mutants X4 (`:383`, the `}` never closes the
expansion), X5 (`:358`, the per-call `_ctx_exp=0` reset dropped) and X6 (`:375`, the
`[ -z "$inq" ]` quoting guard dropped) each leave all 153 tests green. The section's item 3
states three behaviours — a `{` after `$` opens, "ends at the matching `}`", and "a bare
`{a,b}` brace expansion is unchanged" — and only the first and third have a test
(`:967` and `:991`). The close and the quoting guard are met by inspection. I found no
verdict flip under X4 on the probes I tried, so this is test strength, not a hole.

### MINOR-4 — `githooks/pre-commit` exits 1 on the derived board queue block

Same verdict-neutral artefact as the hg1 and hg2 gates: the queue is derived from the git
log's subjects, so once `cd34211` exists the block drops `OG3r`
(`… CR4 OG3r PW1glm …` → `… CR4 PW1glm …`). The board is correctly left uncommitted (it is
outside `touches` and the gate forbids a board commit); the working tree was restored. Not
a defect of this branch.

### MINOR-5 — two residual `${…}` spellings still reach the live guard's text rules, and the section's mutant E names the wrong test

Measured in the deployment fixture against this branch's guard:

```
ALLOW  printf x > ${HOME:?}/nixos-agent-env/tools/orchestrator-guard.sh
ALLOW  printf x > ${X:-${HOME}}/nixos-agent-env/tools/orchestrator-guard.sh
```

`lex_norm` matches the two literal prefixes `$HOME/` and `${HOME}/` only, and the
tokeniser's expansion close is not nested. Neither spelling is named by the section (item 3
names `${HOME}/` and `"${HOME}"/`), and both are moot for a seat — the mount refuses them
whatever the text says — so this is the orchestrator's own session's residue, worth
recording rather than owed. Separately: the section attributes mutant E ("the `:616` arm
deleted") to "OG3b's (h) red"; measured, E kills test 77 (h2), not test 73 (h) — (h)
exercises `$HOME/` and `~/`, which E leaves intact. The mutant dies; the attribution is
imprecise.

## Verdict

**APPROVED.** The section's seven contract items are met (item 7's body clause partly, and
item 2 with a forced and measured deviation). The MAJOR the hg2 gate rejected on is closed
twice over and both closures were shown red first: the tokeniser change makes every
`${HOME}` write spelling deny, and the kernel mount denies them from a seat regardless of
spelling — proven from inside a real `seat@` instance and falsified by removing the mount.
All sixteen named mutants die on their claimed lines; three of six extra mutants die, and
the three survivors are untested branches of the new tokeniser block with no measured
verdict flip. Five acceptance checks green under `--rebuild`, 442 sweep rows verdict- and
reason-identical to main with zero stderr, one commit, subject byte-identical, nothing
outside `touches`. `plan_defect: none`.
