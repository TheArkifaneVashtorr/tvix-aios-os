---
plan_defect: none
mutants_total: 14
mutants_killed: 11
mutants_outside_named: 6
---
# Opus gate — seat run ca1fa, task CA1b — APPROVED

## Summary

Both MAJORs of the CA1 gate are closed, and closed by the mechanism the section
named. The decisive measurement first: with a recording shim called `codex`
placed ahead of `/home/dalhaka/.local/bin` on my PATH (the real binary never
touched), `nix develop -c bats tests/unit/95-codex-arm.bats` in a fresh clone of
`task/CA1b` runs **22/22 `ok` on core and the shim is never invoked**:

```
1..22
ok  1 FACTORY_SEAT outside the rule refuses at exit 2 before a run dir or workspace
ok  2 FACTORY_SEAT=codex with no codex on PATH refuses at exit 2 before a run dir
…
ok 19 the helper's PATH holds no codex: command -v codex through it prints nothing
ok 20 a malformed session id in the banner is dropped, and usage still parses via the marker
ok 21 the classifier copy is .log-free and removed, leaving only the task log
ok 22 no banner and no rollout refuses the usage source and logs the marker fallback
BATS_EXIT=0
=== SHIM LOG ===
=== shim invocations: 0 ===
```

The same shim proves the mutant is what it claims to be. Restoring the old
spelling (`PATH="$BIN:$PATH"` at `tests/unit/95-codex-arm.bats:239`) turns row 2
red **and** records the seat launch the CA1 gate caught:

```
not ok 1 FACTORY_SEAT=codex with no codex on PATH refuses at exit 2 before a run dir
#   `[ "$status" -eq 2 ]' failed
GUARD-SHIM: the driver invoked codex with argv: --version
GUARD-SHIM: the driver invoked codex with argv: exec -c features.plugins=false \
  -c otel.metrics_exporter="none" --sandbox danger-full-access --color never -
GUARD-SHIM: cwd=/tmp/nix-shell.Nfrvmm/bats-run-FEZKgL/test/1/ws
```

At HEAD that launch does not happen — under `SAFE_PATH` the shim log stays empty
across all 174 tests of `95`+`80`+`94`.

The negated-assertion audit is clean (`grep -n '^[[:space:]]*!' … ` prints
nothing), and the section's mutant for row 8 now kills it. Rows 19–22 are all
load-bearing: each dies to at least one mutant, and rows 20 and 21 die to
mutants I invented that the section did not name. The arm itself is byte-for-byte
CA1's — `factory-task`, `factory-brief`, `factory-codex-usage.py` and the README
do not appear in `git diff ca1..HEAD`; only the test file changed (+80/−6). The
dsh arm is untouched: `80-seat-driver.bats` and `94-seat-harness.bats` are not in
the diff against the base at all, and `1..152` is green.

`unit` and `lint` both pass with `--rebuild`. `githooks/pre-commit` exits 1 at
HEAD, on the queue block alone — and I proved it is an artefact of running the
hook *after* the commit, not a defect of the diff (## Checks).

Four MINORs, none gating: two are plan-side (a named mutant that is unkillable
in isolation — the seat disclosed it in the body — and a fixture that
discriminates the session-id character class but not its length), one is a
pre-existing leak outside CA1b's items, one is a missing final newline carried
over from CA1.

## Contract items

Taken literally, item by item, against
`git diff 2b34351..a6f4b86` and `git diff ca1..HEAD`.

| # | contract (CA1b) | met | evidence |
|---|---|---|---|
| 1 | MAJOR-1: `SAFE_PATH` computed in `setup` (an `IFS=:` walk dropping every dir with an executable `codex`); `run_codex_task` **and every other driver invocation** pass `"$BIN:$SAFE_PATH"`; row 2 exits 2 with `no codex on PATH` on core; new row 19 pins the helper | **yes** | `tests/unit/95-codex-arm.bats:55-64` (the walk), `:239` (`PATH="$BIN:$SAFE_PATH"`), `:586` (the only other driver invocation, `PATH="$psbin:$SAFE_PATH"`), `:667-678` (row 19). `grep -n 'PATH=' ` finds no other spelling. Row 2 green on core under the shim; the shim never fired |
| 2 | MAJOR-2: every negated assertion becomes status-capturing; `grep -n '^[[:space:]]*!' …` prints nothing; the empty-id mutant turns row 8 red | **yes** | `:398` `[ "$(grep -c '^seat:' "$FACTORY_RUNS/r1/K1.result" \|\| true)" -eq 0 ]`; the audit grep exits 1 with no output; mutant 2 red at `:398` (## Mutants) |
| 3 | MINOR-1: a row with `FAKE_SID=not-a-uuid` → no `seat:` line, usage still parsed through the marker fallback (`"input": 68620`), `no banner and no rollout` absent | **yes** | row 20, `:680-691`; `:684` `FAKE_SID=not-a-uuid`, `:687` the absent-message clause, `:689` the input clause, `:690` the status-capturing `seat:` clause. Mutant 3 red at `:690` |
| 4 | MINOR-2/-3: after the default row, the run dir holds no `.agent-*` and no `*.log` besides the task log; both mutants red | **partly** — `rm -f`→`:` dies, the `.log`-suffix mutant survives in isolation | row 21, `:693-705`; `:703` the `\.log$` count, `:704` the `\.agent-` count. Mutant 4a red at `:704`. Mutant 4b alone leaves row 21 `ok` (MINOR-1 below); composed with the removal dropped it is red at `:703`, which is what the commit body pastes and labels as such |
| 5 | MINOR-6: `FAKE_NO_BANNER=1 FAKE_NO_ROLLOUT=1` → `usage: {}`, `error_class: boot-failure`, `$output` contains `no banner and no rollout newer than the launch marker` | **yes** | row 22, `:707-719`; `:715`, `:717`, `:718`. Mutant 5 red at `:715` |
| 6 | MINOR-4/-5: the two ill-posed mutants struck; **no test deleted** | **yes** | row 14's comment now reads "Mutant (struck by CA1b item 6): `exit_code=$?` … is equivalent under `set -o pipefail`" (`:517-518`); row 6's comment names only the two live mutants (`:334-335`). Row count went 18 → 22; no `@test` removed (`git diff ca1..HEAD` has no `-@test` line) |
| 7 | the body pastes the command lines, row 2's red, the new rows' reds, every mutant of items 1–5 red and reverted, and the greens | **yes** | every pasted line reproduces exactly: `:398` (item 2), `:690` (item 3), `:704` (item 4a), `:703` (item 4b composed), `:715` (item 5); the green `ok 174 an empty or nonempty probe …` and `ok 589 no banner and no rollout …` both reproduce (## Checks) |

Step 1's shape holds too: `docs/OPERATIONS.md` is **not** in the diff (main's copy
kept), `docs/MAP.md` is one generated line, and the plan file is untouched.

The one clause of item 1 the file does not assert directly is the positive probe
(`PATH="$BIN:$SAFE_PATH" command -v codex` printing `$BIN/codex`). It is covered
transitively — every other row reaches the fake and writes `$REC` — so nothing is
owed.

## Red before green

The section's own red for row 2 is item 1's mutant, pasted above and reproduced.
For the file as a whole I ran the branch's tests against the **base's**
implementation (`git checkout 2b34351 -- tools/factory/seat/factory-task
tools/factory/seat/factory-brief`, `factory-codex-usage.py` deleted), in a
scratch copy, under the shim:

```
1..22
not ok  1 FACTORY_SEAT outside the rule refuses at exit 2 before a run dir or workspace
not ok  2 FACTORY_SEAT=codex with no codex on PATH refuses at exit 2 before a run dir
ok      3 empty or unset FACTORY_SEAT keeps today's dsh arm
not ok  4 … 15 (every codex-arm row)
ok     16 factory-wave passes FACTORY_SEAT through to every factory-task
not ok 17 factory-brief prints the codex trailer pair …
not ok 18 factory-codex-usage.py summarises a rollout …
ok     19 the helper's PATH holds no codex …
not ok 20 a malformed session id in the banner is dropped …
ok     21 the classifier copy is .log-free and removed …
not ok 22 no banner and no rollout refuses the usage source …
--- shim calls: 0
```

18 of 22 red. Rows 3 and 16 pin behaviour the base already has (killed by the
CA1 section's mutants 3d and 16ai). Row 19 tests the harness, not the driver, so
it is impl-independent by construction — its red is mutant O-A below, which kills
it. Row 21 is green against the base because the base makes no classifier copy at
all; its reds are its own mutants (4a, 4b-composed, O-I), all shown below.

Every one of the four new rows therefore has a demonstrated red.

## Mutants

14 applied — 8 named (6 by the CA1b section's items, 2 CA1 mutants spot-checked
because the `Tests` line carries rows 1–18 forward), 6 outside. 11 killed.

**Named, killed (7):**

| mutant | site | kill |
|---|---|---|
| 1 — `PATH="$BIN:$SAFE_PATH"` → `"$BIN:$PATH"` | `95-codex-arm.bats:239` | `not ok 1 FACTORY_SEAT=codex with no codex on PATH …` `` `[ "$status" -eq 2 ]' failed `` (line 263) — plus the shim log above |
| 2 — `[ "$seat_arm" = codex ] && [ -n "$session_id" ]` → `[ "$seat_arm" = codex ]` | `factory-task:816` | `not ok 1 no banner: the .result …` `` `[ "$(grep -c '^seat:' "$FACTORY_RUNS/r1/K1.result" \|\| true)" -eq 0 ]' failed `` (line 398) |
| 3 — the session-id regex `([0-9a-fA-F-]{36})` → `(.+)` | `factory-task:324` | `not ok 1 a malformed session id …` same assertion, line 690 |
| 4a — `rm -f -- "$class_log"` → `:` | `factory-task:803` | `not ok 1 the classifier copy is .log-free …` `` `[ "$(printf '%s\n' "$output" \| grep -c '\.agent-' \|\| true)" -eq 0 ]' failed `` (line 704) |
| 5 — the marker-branch message dropped | `factory-task:759` | `not ok 1 no banner and no rollout …` `` `[[ "$output" == *"no banner and no rollout newer than the launch marker"* ]]' failed `` (line 715) |
| CA1 1a — the `*)` arm neutered | `factory-task:130` | `not ok 1 FACTORY_SEAT outside the rule …` `` `[ "$status" -eq 2 ]' failed `` (line 252) |
| CA1 4e — the trailing `-` dropped from the argv | `factory-task:242` | `not ok 1 the codex launch: argv, workspace, brief …` `` `[ "$status" -eq 0 ]' failed `` (line 295) |

**Named, survived (1):**

- **4b** — `mktemp -p "$runs_dir" ".agent-$key.XXXXXX"` → `".agent-$key.XXXXXX.log"`,
  applied **alone** (the removal at `:803` intact):

  ```
  1..1
  ok 1 the classifier copy is .log-free and removed, leaving only the task log
  EXIT=0
  ```

  It is ill-posed rather than uncaught: the copy is `rm -f`'d before the row can
  list the directory, so the suffix is observable only on a leak. Applied
  together with the removal dropped it dies at `:703`
  (`` `[ "$(printf '%s\n' "$output" | grep -c '\.log$' || true)" -eq 1 ]' failed ``)
  — which is exactly what the commit body pastes, and the body says why in the
  same breath. Same class as the two mutants item 6 struck. MINOR-1.

**Outside the named set (6 tried, 4 killed):**

- **O-A** `SAFE_PATH=$PATH` (the walk skipped) — **killed twice**: `not ok 1 …
  no codex on PATH` (line 263) and `not ok 2 the helper's PATH holds no codex …`
  `` `[ "$status" -eq 1 ]' failed `` (line 676), with 4 shim invocations. Row 19
  is load-bearing.
- **O-D** the usage branch forced to the by-id arm (`if [ -n "$session_id" ]` →
  `if true`) — **killed**: `not ok 1 a malformed session id …`
  `` `[[ "$output" == *"\"input\": 68620"* ]]' failed `` (line 689). Row 20's
  marker-fallback clause is load-bearing.
- **O-I** `rm -f -- "$class_log"` → `rm -f -- "$log"` (the task log removed
  instead) — **killed** at line 704.
- **4b composed** (the `.log` template *and* the removal dropped) — **killed** at
  line 703.
- **O-B** the regex `{36}` → `{1,36}` — **survived**: `not-a-uuid` fails the
  `[0-9a-fA-F-]` character class whatever the length, so the fixture cannot see a
  length-only loosening. MINOR-2.
- **O-C** `rm -f -- "$marker"` (`factory-task:777`) neutered — **survived**: the
  leaked `.marker-K1.*` matches neither `\.log$` nor `\.agent-`, so row 21 stays
  `ok`. Pre-existing on both arms and outside CA1b's items. MINOR-3.

## Checks

Every command run in the fresh clone
(`/tmp/claude-1000/…/scratchpad/gate/gate-ca1fa-CA1b`), with the shim on PATH.

| check | command | result |
|---|---|---|
| unit | `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **pass**, exit 0 — `ok 586 the helper's PATH holds no codex …` … `ok 589 no banner and no rollout refuses the usage source and logs the marker fallback` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass**, exit 0 |
| 95 on core, under the shim | `nix develop -c bats tests/unit/95-codex-arm.bats` | **pass**, `1..22`, 22 `ok`, **0 shim invocations** |
| Step 4's combined run | `nix develop -c bats tests/unit/95-codex-arm.bats tests/unit/80-seat-driver.bats tests/unit/94-seat-harness.bats` | **pass**, `1..174`, last line `ok 174 an empty or nonempty probe runs end to end through factory-task with its command intact` — byte-identical to the body's paste; 0 shim invocations |
| dsh arm | `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/94-seat-harness.bats` | **pass**, `1..152`, no `not ok`; and both files are absent from `git diff 2b34351..HEAD` — byte for byte intact |
| ruff | `nix develop -c ruff check tools/factory/seat pkgs/evidence` / `ruff format --check tools/factory/seat` | `All checks passed!` / `3 files already formatted` |
| shellcheck | `nix develop -c shellcheck -x tools/factory/seat/factory-task tools/factory/seat/factory-brief` | exit 0 |
| bats chain lint | `nix develop -c tests/lint/bats-and-chain.sh` | exit 0 |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0, no drift |
| task graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 at HEAD — **queue block only**, and not this diff's |

The pre-commit exit 1 needs its account, because the CA1 gate could only call it
"structural". I pinned it down. At HEAD the hook's whole complaint is

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
```

and the rewrite it makes is one line inside `<!-- tasks:begin -->…<!-- tasks:end -->`:
`CA1b` and `2026-09-08-codex-driver-arm.md` leave the queue. At the base the same
command exits **0**. And with the branch's tree staged but the commit *not yet
made* (`git reset --soft 2b34351` on a second clone, all six files staged) it also
exits **0** and leaves `docs/OPERATIONS.md` untouched:

```
HOOK_PRECOMMIT_EXIT=0
```

So the staleness is created by the existence of the commit — a landed key leaves
the derived queue — exactly as the hook's own comment and the Global Constraints'
exemption for that block describe. The seat's commit passed its own hook; nothing
here is the seat's to fix, and `docs/OPERATIONS.md` is correctly absent from the
diff.

## Touches and commit

`git diff 2b34351..a6f4b86 --stat`:

```
 docs/MAP.md                               |   2 +-
 tests/unit/95-codex-arm.bats              | 719 +++++++++++++++++++++++++++++
 tools/factory/seat/README.md              |  31 ++
 tools/factory/seat/factory-brief          |  23 +-
 tools/factory/seat/factory-codex-usage.py | 105 +++++
 tools/factory/seat/factory-task           | 240 ++++++++--
 6 files changed, 1072 insertions(+), 48 deletions(-)
```

Every file is inside the section's `touches`; `docs/MAP.md` is the exempt
generator output and its whole diff is `- tests/unit — 19 files` / `+ tests/unit
— 20 files`. Nothing outside the list, so no `Deviation:` line is owed, and none
is claimed.

`git rev-list --count 2b34351..HEAD` → `1`. The subject `diff`s clean against the
section's:

```
seat: the codex arm of the driver, fix round — the tests' PATH holds no real codex, every negated assertion captures its status, the session-id rule, the copy's cleanup and the marker-branch message pinned (test: unit, lint)
```

The body states the why (the two MAJORs, the mechanism, "Only the test file
changes — factory-task already implements all six behaviours"), pastes every red
with its item label and every green, and discloses that mutant 4b was shown
composed with the removal. The two trailers follow a blank line, in order:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run ca1fa)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

No board commit; `docs/superpowers/plans/2026-09-08-codex-driver-arm.md` and
`docs/OPERATIONS.md` are untouched; CA1's subject is not reused.

## Findings

### MINOR-1 — item 4's second named mutant is unkillable in isolation

`tools/factory/seat/factory-task:793`, against `tests/unit/95-codex-arm.bats:703`.

The section says: "the template given a `.log` suffix → a second `*.log` → red."
It does not, on its own:

```
$ sed -i 's@mktemp -p "$runs_dir" ".agent-$key.XXXXXX"@mktemp -p "$runs_dir" ".agent-$key.XXXXXX.log"@' tools/factory/seat/factory-task
$ nix develop -c bats -f 'classifier copy is .log-free' tests/unit/95-codex-arm.bats
1..1
ok 1 the classifier copy is .log-free and removed, leaving only the task log
```

(GNU `mktemp` accepts a template with a suffix after the `X`s — verified
directly, `mktemp -p . ".agent-K1.XXXXXX.log"` → `./.agent-K1.ulUEL8.log`, exit
0 — so the mutant is faithful, not malformed.) The `.log`-free name is
observable only when the copy leaks, i.e. only when the removal is also gone; the
composed mutant is red at `:703`. This is the same class as the two mutants item
6 struck (row 6's window-to-EOF, row 14's `$?`): the prediction in the plan's
sentence is false for the correct code. The seat named it, showed the composed
form, and said so in the body — nothing is owed by the implementer. Worth
striking from the Tests table the way item 6 struck the other two.

### MINOR-2 — the session-id fixture discriminates the character class, not the length

`tools/factory/seat/factory-task:324`, `tests/unit/95-codex-arm.bats:684`.

The section prescribed `FAKE_SID=not-a-uuid`, and the seat used it verbatim; the
named mutant `(.+)` dies. But `not-a-uuid` contains `u`, `i` and `t`, so it fails
`[0-9a-fA-F-]` at any length, and a length-only loosening survives:

```
$ sed -i '324s/{36}/{1,36}/' tools/factory/seat/factory-task
$ nix develop -c bats -f 'malformed session id' tests/unit/95-codex-arm.bats
1..1
ok 1 a malformed session id in the banner is dropped, and usage still parses via the marker
EXIT_OB=0
```

A second fixture with a short but well-formed id (say `0f1e2d3c`) would close the
`{36}` half of the rule. Plan-side: the section chose the fixture.

### MINOR-3 — the launch marker's removal is unasserted, and a leaked marker is invisible to row 21

`tools/factory/seat/factory-task:777` (`rm -f -- "$marker"`).

```
$ sed -i 's@^rm -f -- "$marker"$@: rm -f -- "$marker"@' tools/factory/seat/factory-task
$ nix develop -c bats -f 'classifier copy is .log-free' tests/unit/95-codex-arm.bats
1..1
ok 1 the classifier copy is .log-free and removed, leaving only the task log
EXIT_OC=0
```

Row 21 counts `\.log$` and `\.agent-`; `.marker-K1.XXXXXX` matches neither. The
marker predates CA1 and serves both arms, so this is outside CA1b's seven items —
recorded, not owed. Row 21 could be tightened to `ls -A1 | grep -vc '^K1\.log$'`
= 0 if the run dir is meant to be clean.

### MINOR-4 — `tests/unit/95-codex-arm.bats` has no final newline

`tests/unit/95-codex-arm.bats:718` — `tail -c1` is `}`, where
`94-seat-harness.bats` and `80-seat-driver.bats` both end in `\n`, and `git diff`
prints `\ No newline at end of file`. Carried over from CA1 (`git show
ca1:tests/unit/95-codex-arm.bats | tail -c1` is also `}`); `treefmt` does not
cover `.bats`, so `lint` is green either way. Cosmetic.

## Verdict

**APPROVED.** Both MAJORs are closed by the named mechanism and proved closed by
the CA1 gate's own method: 22/22 green on core with a recording `codex` shim ahead
of the real binary on PATH and zero shim invocations, while the old spelling turns
row 2 red and fires `codex exec --sandbox danger-full-access` from the test. The
negated-assertion audit is empty, row 8's mutant now dies, and the three
previously untested contracts (the 36-hex-and-dash rule, the classifier copy's
name and removal, the marker-branch message) each have a row that a mutant kills.
Rows 19–22 all die to at least one mutant, two of them to mutants outside the
named set. `unit` and `lint` pass with `--rebuild`; the dsh arm is byte for byte
intact (`1..152`, and neither file is in the diff); one commit, subject
byte-identical, both trailers, `touches` respected. Four MINORs, none gating: two
plan-side (an ill-posed named mutant the seat disclosed, and a fixture that only
tests the session-id character class), one pre-existing leak outside the
contract, one missing final newline.
