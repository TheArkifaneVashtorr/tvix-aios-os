# Opus gate — seat run cr7, task CR5 — APPROVED

## Summary

Branch `task/CR5` carries **two** commits on base `224e818`. The task commit is
`b882ac5`; `d93c344` is a board write that is not CR5's to make. **b882ac5 alone
satisfies the plan: yes** — nothing in it reads, references or is tested against
`docs/OPERATIONS.md`'s queue block (the two bats files build their own throwaway
boards and their own `pkgs/evidence/tasks.py` stub), and every declared check
(`unit`, `lint`) is green on `b882ac5` checked out on its own.

`b882ac5`: subject byte-identical to the plan's (148 bytes with the newline,
`cmp` clean), both trailers present in order (`Generated-By`, then
`Co-Authored-By: Claude Fable 5.1`), `tools/ritual.sh` and
`tools/session-start.sh` still `100755`, and the five touched files are exactly
the five in `touches` — no extras, none of the declared five missing.

All three contract items hold, and I verified them on the shape that actually
runs in production, which is *not* the shape the bats suite runs in: the real
host has **no `python3` on `PATH`** (`ls /run/current-system/sw/bin | grep -x
python3` → nothing), so the live resolution path is the third one — parse the
packaged `evidence` wrapper for an interpreter. With `PATH=/run/current-system/sw/bin`
only, against a pristine clone of the real repo at `18bfb67`, `ritual.sh stop`
prints **no block**, stderr empty, in **224 ms**; with the same PATH and the
queue block deliberately made stale *in a commit* it prints exactly
`{"decision":"block","reason":"ritual: the board's queue block is stale - evidence tasks --root . write-board, then commit"}`,
stderr still empty. Empty stderr is the proof the interpreter was resolved: a
failed resolution would have printed `ritual: no python3 for the tree's renderer
- allowing`. A `RITUAL_PYTHON` recording wrapper on the same clone records
`…/realclone/pkgs/evidence/tasks.py --root …/realclone check --board docs/OPERATIONS.md`
— the tree's file, never the store's.

The packaged copy no longer decides: with a fake `evidence` that always exits 1
placed first on `PATH`, the clean clone still allows and the fake is **never
invoked** (its argv log does not exist). Over a full `session-start` +
`ritual.sh stop` pass the recording `evidence` logs exactly one line,
`bundle --markdown`, and zero `tasks` calls.

`ritual.sh stop` timing on this host: 227/232/232/238/261 ms over five runs on a
repo-sized tree, 9–15 ms on a small fixture — **well under 0.5 s**, and under
the 10 s `Stop` timeout in `.claude/settings.json:22`.

Eleven tests go red on CR1b's scripts; all eleven are behavioural. Every
mutation the plan names dies. Three extra mutations I invented survive; all
three are coverage gaps on branches I then exercised by hand and found correct,
so none is a defect and none is a MAJOR. **No MAJORs. Approved.**

The implementer's notes are accurate as far as they go and I could not refute
them, but two of the three claims are weaker than they sound and I re-proved
them the hard way: "47 bats tests green" is true but the suite's fake repo ships
a *stub* renderer, so bats never proves the wrapper-parsing path that the real
host actually takes — I proved that separately (rows 3c, G, G2 below); and "real-host
probe prints no block" is true but on the real repo it is true for the wrong
reason — `/home/dalhaka/nixos-agent-env/.claude/ritual-override` exists (empty,
19:46:52), and `stop` short-circuits on it at `tools/ritual.sh:182` before the
board check ever runs. The honest probe is the one on the pristine clone, and it
also prints no block. Also worth the orchestrator's eye: the disagreement CR5
was written to fix is **already gone on the host** — switch #19 landed (gen 44),
so `/run/current-system/sw/bin/evidence` is now
`kj644vlv…-evidence` and both renderers return 0 on the real board. CR5 is still
the right fix; it just cannot be demonstrated as a *disagreement* today, which
is why I forced the disagreement with a fake stale `evidence` instead.

## The second commit

`d93c344` "docs: board — CR5 landed; queue block regenerated (test: lint)"
touches one file, `docs/OPERATIONS.md`, one line: it drops `CR5` from the derived
queue block (`… B1 CR3 CR5 OG1r2b …` → `… B1 CR3 OG1r2b …`). Nothing else.

- **It is outside `touches`.** CR5's `touches` names five files and
  `docs/OPERATIONS.md` is not one of them. The plan says "Step 5: One commit."
  There are two. That is a commit-convention breach — but of the *branch*, not of
  `b882ac5`.
- **Its board text is not true yet.** The commit subject asserts "CR5 landed";
  at the moment it was written CR5 had landed on `task/CR5` only, not on `main`,
  and the gate had not run. Worse, it leaves the board internally inconsistent:
  the paragraph immediately below the block it edited still reads "the hook has
  no `stop_hook_active` guard … Operator unblock: switch #19 now … or `touch
  .claude/ritual-override` until CR5 lands", and the Live line still says
  "generation 43 … switch #18". A board that says CR5 both landed and has not
  landed is worse than one that says neither.
- **Nothing in `b882ac5` depends on it.** `git show b882ac5` touches no board
  file; the two bats files write their own `docs/OPERATIONS.md` into
  `$BATS_TEST_TMPDIR/repo`; neither script hard-codes a queue string. Dropping
  `d93c344` leaves `b882ac5` self-contained.
- **Why it was written is visible in the checks**: on `b882ac5` alone
  `githooks/pre-commit` exits 1 with `tasks: docs/OPERATIONS.md queue block was
  stale and has been regenerated`. That is post-landing board debt — the queue is
  *derived from the tree*, so the moment CR5's commit exists the committed block
  is stale — exactly what the cr5/CR1b gate recorded and did not count as a red
  check. `pre-commit` is 0 at base `224e818` and 0 at the tip. Writing the board
  is the orchestrator's step at integrate, not the seat's.

Recorded as **MINOR-6**, a process breach the orchestrator drops at integration.
Integrate `b882ac5` only.

## Rule behaviour

Fixtures are mine, built under
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/…/scratchpad/` (`mut/fixture.sh`,
`mut/matrix.sh`, `mut/matrix2.sh`, `mut/live.sh`, `mut/live2.sh`). Every probe
ran with `XDG_STATE_HOME` pointed at a scratch dir. The repo under test is the
throwaway clone or a throwaway clone of the real repo, except probe A, which is
the real repo read-only.

| case | expected | observed |
|---|---|---|
| **1a** fake `evidence` on PATH exits 1 on every `tasks`, tree renderer says current, clean tree | allow, no block JSON | **pass** — rc 0, stdout empty, stderr empty |
| **1b** reverse: fake `evidence` exits 0, tree renderer says stale | block | **pass** — `{"decision":"block","reason":"ritual: the board's queue block is stale - evidence tasks --root . write-board, then commit"}` |
| **2a** `stop_hook_active: true` + stale board | allow, the exact stderr line, no stamp | **pass** — stdout empty, stderr `ritual: continuing after a block - allowing`, state dir empty (`ls -A` → nothing; no `gp1.blocks`) |
| **2b** `stop_hook_active: false` + stale board | still blocks, stamp written | **pass** — the stale block on stdout, `…/ritual/gp1.blocks` = `1`. The guard does not disable blocking |
| **3a** `RITUAL_PYTHON` = recording wrapper, `stop` | argv names the *clone's* `pkgs/evidence/tasks.py` | **pass** — `…/fx/repo/pkgs/evidence/tasks.py --root …/fx/repo check --board docs/OPERATIONS.md` |
| **3a'** same, `session-start` brief part | same | **pass** — `…/fx/repo/pkgs/evidence/tasks.py --root …/fx/repo brief`; the brief printed is `# Task brief (from the TREE renderer)`; the fake `evidence`'s argv log for that run is exactly `bundle --markdown` |
| **3a''** in-flight part | — | `inflight` makes no `tasks` call at all (it reads `$FACTORY_ROOT/runs`), so there is nothing to redirect; contract item 1's "in-flight parts" is vacuous here, correctly |
| **3b** no `RITUAL_PYTHON`, a recording `python3` first on PATH | that interpreter runs the tree's file | **pass** — same argv, recorded by the PATH `python3` |
| **3c-A** no `python3`; fake wrapper whose text is `exec /nix/store/…-python3-3.14.7/bin/python3 /nonexistent/evidence.py "$@"` | that interpreter used | **pass** — clean board → silent allow, stderr empty; stale board → the stale block. Both prove resolution (a failure would have printed the degrade line) |
| **3c-B** no `python3`; wrapper whose text is `export PATH="/nix/store/…-python3-3.14.7/bin:$PATH"` (the real wrapper's shape) | that interpreter used | **pass** — same two outcomes; and `session-start` printed `# Task brief (from the TREE renderer)` under it |
| **3d** no `python3`, no `evidence` at all, stale board | allow with the exact stderr line | **pass** — stdout empty, stderr `ritual: no python3 for the tree's renderer - allowing`. Blocking never happens on the hook's own missing tooling |
| **3d'** same for `session-start` | `unavailable:`, no crash | **pass** — rc 0, board printed, `unavailable: evidence not on PATH`, empty brief section, pointer line last. Same as CR1b |
| **4** `evidence bundle` still packaged | a recording `evidence` shows `bundle` and no `tasks` | **pass** — the whole log after a `session-start` + a `stop` is one line, `bundle --markdown`; `grep -c tasks` → 0. Statically, the only `"$ev"` invocation left in either script is `tools/session-start.sh:83` (`"$ev" bundle --markdown`) |
| **5-A** live probe, clone's scripts vs the **real repo** `/home/dalhaka/nixos-agent-env` | no block | **allow, but for the wrong reason** — `.claude/ritual-override` is present (empty file, `dalhaka 2026-09-05 19:46:52`), so stderr is `ritual: override present - allowing (…)` and `collect_unmet` never runs. 15 ms. `git status --short` on the real repo was empty before and after; no file under it changed; no `.blocks` anywhere under it |
| **5-B** same scripts vs a **pristine clone of the real repo** at `18bfb67` (clean, no override) | no block | **pass** — stdout empty, stderr empty, 260 ms; `git status --short` on the clone empty afterwards. A `RITUAL_PYTHON` recording wrapper on the same probe records `…/realclone/pkgs/evidence/tasks.py --root …/realclone check --board docs/OPERATIONS.md` |
| **5-C** same, with a fake always-stale `evidence` **first** on PATH | still no block; the fake never consulted | **pass** — stdout empty, 261 ms, and the fake's argv log was never created (`none`). The packaged copy no longer decides |
| **5-D** same, host `evidence` first on PATH | no block | **pass** — 247 ms |
| **G** same, **production-shaped** `PATH=/run/current-system/sw/bin` only (no `python3`; `evidence` → `kj644vlv…`) | no block | **pass** — stdout empty, **stderr empty** (⇒ the wrapper-named interpreter was resolved and ran), 224 ms |
| **G2** production PATH, queue block made stale **in a commit** so the dirty check cannot fire first | block | **pass** — exactly the stale-board JSON, stderr empty. This is the row that proves the wrapper fallback really drives the verdict on this host |
| **G3** production PATH, same stale commit, `stop_hook_active: true` | allow, no stamp | **pass** — stderr `ritual: continuing after a block - allowing`, no `*.blocks` written |
| **6** runbook | states the rule and the order | **pass** — `docs/runbooks/session.md:36-40` "A hook never calls a host-packaged copy of tree code: the task renderer is always this tree's `pkgs/evidence/tasks.py` …", and `:24-27` gives the order `RITUAL_PYTHON`, else `python3` on `PATH`, else the interpreter the packaged wrapper names, plus `:17-18` "This is the one part that stays the packaged command: it reads the store, not the tree" |
| **7a** CR1b JSON escaping, path `docs/reviews/naïve "x"\y.md` | valid JSON, decision block | **pass** — raw stdout `{"decision":"block","reason":"ritual: commit the review file(s) \"docs/reviews/naïve \\\"x\\\"\\\\y.md\""}`; `json.load` → `decision = block` |
| **7b** CR1b non-blocking stdin | returns fast | **pass** — closed fd 0: rc 0 in **9 ms**; fifo held open by a `sleep 3` and never written: rc 0 in **3007 ms**, i.e. it returned the instant the writer closed, never hung |
| **7c** CR1b in-flight / reaper / degrade-to-allow / stdin caps | intact | **pass** — tests #15–19, #27–28, #31 all green, and CR1b's own mutants still die (table below) |

**Where the `.blocks` stamps go — for the orchestrator:** `tools/ritual.sh:21`
puts all hook state at `${XDG_STATE_HOME:-$HOME/.local/state}/nixos-agent-env/ritual`,
and the per-session counter is `<statedir>/<session_id>.blocks`
(`tools/ritual.sh:190,195,205`). **Nothing is ever written inside the repo.**
My probe against the real repo wrote only `…/scratchpad/livestate/nixos-agent-env/ritual/last-stop`
under my scratch `XDG_STATE_HOME`; `find /home/dalhaka/nixos-agent-env -name '*.blocks'`
is empty and the real repo's `git status --short` is empty and its HEAD is
unchanged at `18bfb67`.

## Checks

Run in the clone. `--rebuild` forced once, so `unit` is a genuine sandbox build,
not a cache hit.

| check | on tip `d93c344` | on `b882ac5` alone | time |
|---|---|---|---|
| `nix develop -c shellcheck tools/ritual.sh tools/session-start.sh` | **exit 0**, no output | **exit 0**, no output | 1.7 s |
| `nix develop -c bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats` | **47 ok, 0 not ok** | **47 ok, 0 not ok** | 5.8 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | **exit 0** | **exit 0** | 1.1 s |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **exit 0**, `1..198`, 198 ok / 0 not ok (fresh build) | — | 29.7 s |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | **exit 0** | **exit 0** | 1.1 s |
| `nix develop -c githooks/pre-commit` | **exit 0** | **exit 1** — see below | 2.8 s |
| `nix develop -c githooks/pre-commit` at base `224e818` | **exit 0** | — | 2.8 s |

**The one difference between tip and `b882ac5` is the `pre-commit` exit code, and
it is not a red check.** The only failing line is
`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git
add docs/OPERATIONS.md and commit again`, and the only diff it wants is
`… B1 CR3 CR5 OG1r2b …` → `… B1 CR3 OG1r2b …`. That is the derived queue
reacting to CR5's own landing: 0 at base, 1 once the commit exists, 0 again once
the board is rewritten. `docs/OPERATIONS.md` is not in `touches`; the board write
is the orchestrator's step at integrate. CR5's declared `acceptance` is
`unit, lint`, and both are exit 0 on `b882ac5` alone. I restored the file; the
clone is clean.

## Red before green

CR1b's `tools/ritual.sh` and `tools/session-start.sh` (`git show 224e818:<path>`)
put in place of CR5's, CR5's tests kept:

```
not ok 4  a stale board check blocks naming write-board
not ok 21 a stale packaged evidence plus a current tree renderer still allows
not ok 22 a current packaged evidence plus a stale tree renderer still blocks
not ok 23 stop_hook_active true allows without writing a block, naming the loop guard
not ok 24 no python3 and no evidence degrades to allow with the renderer stderr line
not ok 25 RITUAL_PYTHON wrapper runs the tree's tasks.py for the stop board check
not ok 26 no python3 on PATH but the packaged evidence wrapper names one uses it
not ok 32 prints START HERE, bundle, brief and the runbook pointer, in order
not ok 40 a failing evidence bundle says unavailable while the brief still prints from the tree
not ok 41 the brief runs the tree's tasks.py through RITUAL_PYTHON
not ok 42 with defaults the brief and the pointer print last even when all three parts overflow
```

**Eleven red, 36 green.** All five of the plan's Step 1 tests are in there:
(1) → #21, (2) → #22, (3) → #23, (4) → #24, (5) → #25 for `stop` and #41 for
`session-start`'s brief, with #26 covering the wrapper-parsing case the plan
folds into item 1. The failures are behavioural, not "command not found": #21
fails on non-empty stdout (CR1b's `$ev` returned 1 and blocked), #22 on the
absence of `"decision":"block"` (CR1b trusted the fake's 0), #23 on the missing
stderr line, #25/#41 on an empty argv record, #32/#40/#42 on a brief that CR1b
routed through the fake `evidence` instead of the tree. #4 is red because CR5
rewrote it from `EVIDENCE_RC=1` to the tree-stub marker — the same assertion,
re-pinned to the new mechanism.

Restored → **47 ok, 0 not ok**, `git status --short` empty.

## Mutation table

Applied to the shipped tree by `scratchpad/mut/mutate.py`, `git diff --quiet`
asserted non-clean before each run (any unapplied edit prints `VOID` and is
rerun), `bats tests/unit/92-ritual.bats tests/unit/90-session-start.bats
</dev/null` under `timeout 120`, then `git checkout -- tools tests`. No row was
void.

**The plan's table**

| # | mutation | result |
|---|---|---|
| M-A | board check back to `"${RITUAL_EVIDENCE:-evidence}" tasks … check --board` | **killed** — #4, #21, #22, #25, #26 |
| M-B | the fake wins: consult `$ev` whenever it exists on PATH, tree only as fallback | **killed** — #4, #21, #22, #25, #26 |
| M-C | the `stop_hook_active` guard removed (flag still parsed, ignored) | **killed** — #23 |
| M-C2 | the guard made to allow for `false` too (`= "true" || != "true"`) | **killed** — #1, #2, #3, #4, #5, #6, #7, #11, #12, #20, #21, #22, #24, #25, #26, #30 |
| M-D | no interpreter → emit the stale line (block) instead of the degrade line | **killed** — #24 |
| M-E | `session-start`'s brief back to `"$ev" tasks --root "$repo" brief` | **killed** — #32, #40, #41, #42 |
| M-F | `RITUAL_PYTHON` ignored: `python3` on PATH preferred (both scripts) | **killed** — #25, #41 |
| M-F (ritual only) | as above, `tools/ritual.sh` only | **killed** — #25 |
| M-F (session only) | as above, `tools/session-start.sh` only | **killed** — #41 |
| M-G | wrapper-parsing fallback removed (both scripts) | **killed** — #26 |
| M-G (ritual only) | `tools/ritual.sh` only | **killed** — #26 |
| M-G (session only) | `tools/session-start.sh` only | ***SURVIVES*** — **unpinned**, MINOR-1 |
| M-H (mine) | the "no tree renderer at `pkgs/evidence/tasks.py`" branch made to block | ***SURVIVES*** — MINOR-2 |
| C-MF (mine) | renderer exits ≠0,≠1 → block instead of the degrade line | ***SURVIVES*** — MINOR-3 |

**CR1b's set, re-applied on the CR5 tree**

| # | mutation | result |
|---|---|---|
| C-MA (CR1b M-A) | `inflight_out=""` in `session-start` | killed — #45 |
| C-MB2 (CR1b M-B2) | stale log with no `run.meta` listed instead of counted | killed — #18, #19 |
| C-MC (CR1b M-C) | the escaping `sed` removed, reason interpolated raw | killed — #20 |
| C-MD1 (CR1b M-D1) | `ritual.sh` tty guard + bounded read → `input=$(cat)` | killed — #27 |
| C-MD2 (CR1b M-D2) | `session-start.sh` tty guard + bounded read → `input=$(cat)` | killed — #46 |
| C-MG2 (CR1b M-G2) | reaper `-mtime +7` → `+1000` | killed — #31 |
| C-M1 | `docs/reviews` dropped from the review status path | killed — #1, #5, #6, #20 |
| C-M2 | the `rc -eq 1` branch made unreachable | killed — #4, #22 |
| C-M3 | `.claude/ritual-override` ignored | killed — #7, #30 |
| C-M4 | the two-block bound removed | killed — #5 |
| C-M5 | the block counter never incremented | killed — #5 |
| C-M6 | board debt `-ge` → `-gt` | killed — #11 |
| C-M7 | `precompact` also writes `$repo/handoff-leak.md` | killed — #13 |
| C-M8 | a dead pid reported as `alive` | killed — #15 |
| C-M9 | `stop` exits 1 on malformed stdin | killed — #10, #27, #28 |
| C-M11 | the `.result` skip removed | killed — #17 |
| C-M12 | the `relaunch:` hint dropped | killed — #15 |
| C-M13 | the idle line's text changed | killed — #44 |
| C-M14 | the `## Handoff` heading and `cat` removed | killed — #43 |
| C-M16 | the whole ritual part dropped from `session-start` | killed — #43, #44, #45 |
| C-M17 | the `## In flight` heading → `x` | killed — #45 |

**All 21 of CR1b's re-applied mutants still die.** CR1b's own known survivors
(its M-B1, M-D3, M-E1/E2, M-G1) were survivors there too and are unchanged here;
I did not re-count them as new.

Score on the plan's table: **11 of 11 named mutations killed.** Three extra
mutations of my own survive and are recorded as MINORs.

## Findings

No MAJORs.

**MINOR-1 — `session-start.sh`'s wrapper-parsing fallback is unpinned.**
`tools/session-start.sh:49-60`. Removing it (an early `return 1` before
`ev=$(command -v evidence …)`) leaves the whole suite green:

```
M-G-session: *** SURVIVES ***
```

The ritual's copy of the same code *is* pinned (#26 kills M-G-ritual), and I
verified the session-start copy works by hand — with `PATH` carrying no
`python3` and a wrapper whose text is
`export PATH="/nix/store/…-python3-3.14.7/bin:$PATH"`, `session-start.sh` printed
`# Task brief (from the TREE renderer)`. So this is a missing test, not a defect.
It matters because on the real host this branch is the *only* one that fires
(no `python3` on `/run/current-system/sw/bin`), so the brief silently going
empty would be the failure mode nobody notices. Fix: one test in
`tests/unit/90-session-start.bats` mirroring #26 — a PATH with no `python3` and a
wrapper `evidence` whose `PATH=` line names one, asserting the brief still
prints.

**MINOR-2 — the "no tree renderer" branch is untested.**
`tools/ritual.sh:149-150`. Turning that degrade into a block survives:

```
M-H: *** SURVIVES ***
```

Shipped behaviour is right (a repo with no `pkgs/evidence/tasks.py` allows with
`ritual: no tree renderer at pkgs/evidence/tasks.py - allowing` on stderr) — I
checked by hand. Fix: one test with the stub deleted, asserting allow + that
stderr line.

**MINOR-3 — the crashing-renderer degrade is untested; this is a coverage
regression from CR1b.** `tools/ritual.sh:156-157`. Making a renderer exit of 2
block instead of allow survives:

```
C-MF: *** SURVIVES ***
```

CR1b pinned the equivalent path with test #21 ("a missing evidence degrades to
allow …", plus the gate's own stub-exits-2 probe); CR5 rewrote #21 into the
"no python3 and no evidence" test, which covers `-z "$py"` (M-D dies) but not
`rc ∉ {0,1}`. The behaviour is still correct — a `tasks.py` that raises exits 1
from Python, so in practice this branch guards against exit 2+ from a broken
interpreter — but the plan's spec §4 degrade-to-allow rule is now one branch less
pinned than it was. Fix: a stub `tasks.py` that `sys.exit(2)`, asserting allow
and `the tree renderer failed (exit 2) - allowing the board check`.

**MINOR-4 — `RITUAL_EVIDENCE` is dead code in the tests.** `b882ac5` removed
`ev=${RITUAL_EVIDENCE:-evidence}` from `tools/ritual.sh` (it appears nowhere in
the script now), but `tests/unit/92-ritual.bats:71,413,421,443` still export
`RITUAL_EVIDENCE="$BATS_TEST_TMPDIR/bin/evidence"` into every run. It is inert,
and it reads as if the ritual still had a packaged-evidence knob. Fix: drop the
four exports, or keep one and rename the comment to say it only puts the fake on
`PATH` for the wrapper-parsing path.

**MINOR-5 — two stale test/behaviour descriptions.**
`tests/unit/90-session-start.bats:56` is still titled "without evidence on PATH
the board still prints and **each missing part** says unavailable", but the brief
is no longer a missing part — it prints from the tree whenever an interpreter
resolves; the body only asserts the bundle's line, so the title over-claims.
Separately, CR1b's distinct message `unavailable: evidence not on PATH (bundle
skipped)` is gone: with no `evidence` the bundle now says plain
`unavailable: evidence not on PATH` in both cases, losing the hint that the
brief nevertheless came from the tree. Cosmetic; no test depends on it.

**MINOR-6 — the second commit (process).** `d93c344` writes
`docs/OPERATIONS.md`, which is outside CR5's `touches`, against a plan that says
"Step 5: One commit", and its subject claims a landing that had not happened
while leaving the paragraph below it still describing the pre-CR5 block. It is
not a defect in `b882ac5` and `b882ac5` does not depend on it. Fix: integrate
`b882ac5` only; the orchestrator writes the board at integrate, including the
"Blocked at turn end" paragraph and the Live line (which still says generation
43 / switch #18, though switch #19 has since landed — gen 44, `18bfb67`).

## Verdict

**APPROVED.** All three contract items met and verified on the production-shaped
PATH, not just in the bats sandbox: the ritual and the session hook run the
tree's `pkgs/evidence/tasks.py` under `RITUAL_PYTHON` → `python3` on `PATH` →
the interpreter the packaged wrapper names, degrading to allow with the exact
stderr line when none exists; `stop_hook_active: true` allows with the exact
stderr line and writes no stamp, while `false` still blocks; `evidence bundle`
is the one packaged call left. `unit` (198/198, forced rebuild) and `lint` are
green, `shellcheck` is clean, 47/47 bats. Eleven tests red on CR1b, all eleven
behavioural; all eleven named mutations die and all 21 re-applied CR1b mutants
still die. `ritual.sh stop` costs 224–261 ms on a real-sized tree.

**b882ac5 alone satisfies the plan: yes.** Integrate `b882ac5`; drop `d93c344`
and write the board at integrate.
