---
plan_defect: missing-case
plan_defect_secondary: wrong-fact
mutants_total: 16
mutants_killed: 12
mutants_outside_named: 7
---
# Opus gate — seat run pa9, task P8 — REJECTED

Branch `task/P8`, base `1d6d9ab`, head `e18b3e5`, ONE commit, six files
(+366/−4). Reviewed in a fresh clone
(`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-pa9-P8`);
nothing under `/home/dalhaka/factory` or `/home/dalhaka/nixos-agent-env` was
modified except this file. No seat was run: `factory-plan.sh` was exercised only
against a fake `factory-plan-brief` and a fake `factory-task` on fixtures under
the scratch directory.

## Summary

The role, the router and the driver are right, and every claim the implementer
made is true — including the deviation, which is a genuine plan wrong-fact
found and adapted around correctly. `unit`, `factory-unit` and `lint` are green
from a forced rebuild; 50/50 bats in the devShell; the reds reproduce on main's
code exactly as the plan predicted.

One MAJOR, and it is the mirror image of P11b's: the branch's own assertion that
`seat-plan.md` carries no typed task heading **does not run inside the `unit`
check** — the acceptance check, and the one `factory-integrate` re-runs by ref.
`tools/factory/plan/` is not in `checks.unit`'s copy list, so the test takes its
own `|| skip` arm. I appended a typed heading to `seat-plan.md` and
`nix build .#checks.x86_64-linux.unit` **passed**. The named mutant survives the
gate; today's green `unit` is 4 of 5 new tests, not 5.

A second, smaller vacuity: the size rule is duplicated in `factory-plan.sh` and
`factory-plan-brief.sh`, and neither of its two boundaries is pinned — `-le
1500 → -lt 1500` and `-le 4000 → -lt 4000` both leave the whole bats file green.
The implementation is correct at all four boundary values (I measured them); the
test fixtures (3, 1501, 4001 words) simply never touch a boundary.

Six minors below. Nothing here is a paid-seat hazard, a routing-row leak or a
wrong model.

## The role

`route.py` gains `"plan"` before `"any"` in `ROLES` (`tools/factory/route.py:46`)
and `factory_route`'s arm gains `| plan`
(`tools/factory/seat/factory-lib.sh:257`). Nothing else changed in either file.
Measured, in the clone, on fixtures and the committed table:

| probe | expected | observed | exit |
|---|---|---|---|
| `route.py check` (committed table) | green | (silent) | 0 |
| `route.py --file <plan-row fixture> check` | green | (silent) | 0 |
| `route.py --file <planner fixture> check` | `unknown role 'planner'`, 1 | `route.py: row 1: unknown role 'planner'` | 1 |
| `route.py lookup openrouter plan docs S` | default row | `deepseek/deepseek-v4-pro-0813 medium` | 0 |
| … `docs M` / `docs XS` / `docs L` / `docs any` | default row | `deepseek/deepseek-v4-pro-0813 medium` (each) | 0 |
| `grep -c 'role = "plan"' docs/ledger/routing.toml` | 0 | `0` | 1 |
| `factory_route_check` (committed table) | green | (silent) | 0 |
| `factory_route --route openrouter plan docs S` | default row | `deepseek/deepseek-v4-pro-0813 medium` | 0 |
| `factory_route … <planner fixture>` | refusal | `factory_route: …: row 1: unknown role planner` | 3 |

**No `plan` row is written** (spec §6.2 holds), and the two lists are in
lockstep: reverting either half alone turns test 46 red (both directions run,
evidence under "Tests and mutants"). `factory-unit` is green — `render.test.mjs`
derives its models map from `route.py` and the output is unchanged.

## factory-plan.sh

85 lines, `set -euo pipefail`, sources `factory-lib.sh`, arity fenced at 4,
`[ -r "$spec" ]`, then the four contracted steps. Driven with a recording fake
`factory-task` (`FACTORY_BIN_OVERRIDE`) and a fake brief (`FACTORY_PLAN_BRIEF`),
`FACTORY_TOOLBOX_REPO` pointed at a fixture tree:

```
brief ARGC=2 ARGV=[…/s1500.md docs/reviews/plan-drafts/2026-09-06-helm-home-1-deepseek-deepseek-v4-pro-0813.md]
brief SIZE=S
task ARGV=[run1 …/repo PLAN-helm-home-1 --model deepseek/deepseek-v4-pro-0813]
task PLAN=…/tb/tools/factory/plan/seat-plan.md
task EFFORT=medium
task TEXT=BRIEF
  exit=0
```

Every element of the interface is as contracted: the key is `PLAN-<name>`, the
model is passed with `--model` (so `factory-task`'s `route_label` is `explicit`
— `tools/factory/seat/factory-task:95-100`, `printf 'route: %s\n' "$route_label"`
at :324), the effort rides `OPENROUTER_REASONING_EFFORT`, the packet rides
`FACTORY_TASK_TEXT`, and `FACTORY_PLAN` is the **absolute** path
`$FACTORY_TOOLBOX_REPO/tools/factory/plan/seat-plan.md` — the toolbox tree's
copy, not the workspace clone's, which is what §P8 asks for and what P11r's
"readable plan" requirement will accept (the file exists in the tree).

The size seam and the refusals, all measured:

| spec | expected | observed | exit |
|---|---|---|---|
| 1,500 words | S | `brief SIZE=S` | 0 |
| 1,501 words | M | `brief SIZE=M` | 0 |
| 4,000 words | M | `brief SIZE=M` | 0 |
| 4,001 words | exit 2, no seat | `factory-plan.sh: factory-plan: an L spec is split before a plan is written` | 2 |
| brief exits 2 | exit 2, stderr forwarded, no seat | `fake brief: refusing -- the graph is not sound` | 2 |
| brief exits 3 | (contract says 2) | `fake brief: part M3 failed mid-packet` | **3** |
| unreadable routing table | `factory_route`'s message, exit 3 | `factory_route: …: row 1: missing one of role/kind/size/model/effort` | 3 |
| missing spec | refusal | `factory-plan.sh: no such spec: …` | 2 |
| model with `/` | `-` in the out path | `…-helm-home-1-deepseek-deepseek-v4-pro-0813.md` | 0 |
| name `a/b` | (unspecified) | `…/plan-drafts/2026-09-06-a/b-…md`, key `PLAN-a/b` | 0 |
| name `helm home 1` | (unspecified) | key `PLAN-helm home 1` | 0 |

The refusals fail closed in the right order: the L refusal happens before the
brief and before any `factory-task`, and a refusing brief never reaches the
seat (`[ ! -e "$rec_task" ]` in test 49, and my own probes agree). The thresholds
match `factory-plan-brief.sh:408-415` exactly, value for value.

## The size seam (the deviation judged)

The implementer's one declared deviation: *"size passed to the brief as
`FACTORY_PLAN_SIZE` (env) not a third positional, since `factory-plan-brief`
refuses the extra argument."* Judged: **the plan's Fact is wrong and the
adaptation is right.**

§P8 Step 1 says "pass `size` as the brief's third argument,
`factory-plan-brief.sh` ignores extra arguments". P2b's landed script does not:
after `shift 2` it parses only `--since`/`--date` and every other token hits the
`*)` arm (`tools/factory/seat/factory-plan-brief.sh:53-71`). Run against the
real script in the clone:

```
$ tools/factory/seat/factory-plan-brief.sh docs/superpowers/specs/2026-09-05-planning-agent-design.md docs/reviews/plan-drafts/x.md S
usage: factory-plan-brief <spec> <out> [--since YYYY-MM-DD] [--date YYYY-MM-DD]
  exit=2
```

A third positional would have made every real planning run exit 2 before the
packet was composed. The env var is inert instead: `grep -c FACTORY_PLAN_SIZE
tools/factory/seat/factory-plan-brief.sh` → `0`. So the real brief ignores the
size either way, and the packet's `TARGET` part computes its own from `wc -w`
with the identical S ≤ 1500 / M ≤ 4000 / L rule
(`factory-plan-brief.sh:405-420`, `printf 'size: %s\n' "$size"`). **The seam is
test-only in both designs; no production behaviour is lost**, and the test still
pins the value the seam carries (`brief-size=S` / `brief-size=M`,
`tests/unit/80-seat-driver.bats:2287,2299`). The deviation is reported in the
commit body, in the script's comment at :71-75 and in the header's Env block.
Correct call; the plan's Facts should carry `wrong-fact` for it.

The one thing the deviation does not cover: the two copies of the size rule are
now pinned only away from their boundaries (MAJOR 2).

## seat-plan.md

31 lines under `tools/factory/plan/`, not under `docs/superpowers/plans/`, and
the graph never sees it (`tasks.py check` on the branch: silent, exit 0). It
carries exactly the constraints §P8 lists, each verified by reading it:

- one output file — the draft the brief named, under `docs/reviews/plan-drafts/`
  (:14-15);
- no typed `### <KEY> (code|docs, XS|S|M|L) — ` heading in any file (:16-17);
- no transcript, seat log, `dispatch.log`, `.dsh-home` or store body (:18-19);
- no network (:20);
- `factory-brief <draft> <KEY>` the one seat tool, `factory-dispatch` only with
  `--dry-run` (:21-22);
- a draft until the panel says otherwise (Assumptions 1, :26-27).

`grep -cE '^### [A-Za-z][A-Za-z0-9-]* \((code|docs), (XS|S|M|L)\)'` → `0`, run
myself. `factory_task_kind_size <seat-plan.md> PLAN-helm-home-1` → `any any`,
exit 0, as §P8 says. `factory-brief tools/factory/plan/seat-plan.md PLAN-x` with
`FACTORY_TASK_TEXT` set composes the two H2s, then
`### PLAN-x (ad-hoc task, not in seat-plan.md)` with the packet under it, then
WORKSPACE RULES and the result template — the ad-hoc heading is untyped, so it
is not a graph heading either. Shape:

```
## Global Constraints
- Write ONE output file — …
## Assumptions
1. The draft is a draft until the panel says otherwise …
### PLAN-x (ad-hoc task, not in seat-plan.md)

PACKET-BODY-HERE

## WORKSPACE RULES
…
FACTORY-RESULT status=<done|partial|failed>
```

## Tests and mutants

50/50 in the devShell (45 → 50; five new tests, none skipped there).

**Named mutants (9): 7 killed, 2 survived.**

| mutant | result |
|---|---|
| `plan` in `route.py` only (lib reverted to base) | killed — `not ok 46` |
| `plan` in `factory-lib.sh` only (route.py reverted) | killed — `not ok 46` |
| a `plan` row written into `docs/ledger/routing.toml` | killed — `not ok 47` |
| the `FACTORY_PLAN=` export dropped from the exec | killed — `not ok 48` |
| the brief's exit ignored (`… \|\| true`) | killed — `not ok 49` |
| the `/` kept in the out path | killed — `not ok 48` |
| the L refusal dropped (`size=L` instead of `factory_die 2`) | killed — `not ok 49` |
| **a typed heading in `seat-plan.md`** | killed by `bats` in the devShell; **SURVIVES `nix build .#checks.x86_64-linux.unit`** (MAJOR 1) |
| **`-le 1500` → `-lt 1500`** | **SURVIVED** — whole file green (MAJOR 2) |

**Outside the named list (7): 5 killed, 2 survived.**

| mutant | result |
|---|---|
| `-le 4000` → `-lt 4000` (a 4,000-word spec becomes an L refusal) | **SURVIVED** — whole file green |
| `--model "$model"` dropped from the exec | killed — `not ok 48` |
| `OPENROUTER_REASONING_EFFORT` emptied | killed — `not ok 48` |
| the `PLAN-` prefix dropped from the key | killed — `not ok 48` |
| `read -r effort model` (fields swapped) | killed — `not ok 48` |
| the model dropped from the out path | killed — `not ok 48` |
| the `[ -r "$spec" ]` guard replaced by `true` | **SURVIVED** — no test covers the missing-spec refusal (minor 5) |

Total 16 mutants, 12 killed.

## Checks

All from inside the clone, all with `--rebuild` where the derivation already
existed:

| check | result |
|---|---|
| `shellcheck factory-plan.sh factory-lib.sh` | 0 |
| `shfmt -d -i 2 -ci factory-plan.sh` | 0 (no diff) |
| `ruff check tools/factory/route.py` | `All checks passed!` |
| `bats tests/unit/80-seat-driver.bats 82-factory-dispatch.bats 83-plan-brief.bats` | 89/89 ok |
| `nix build .#checks.x86_64-linux.unit --rebuild` | 0 (390 tests; **`ok 217 … # skip`** — see MAJOR 1) |
| `nix build .#checks.x86_64-linux.factory-unit --rebuild` | 0 — `render.test.mjs: all assertions passed` |
| `nix build .#checks.x86_64-linux.lint` | 0 |
| `nix develop -c githooks/pre-commit` | regenerated the board's queue block once (an artifact of my clone reading the live `~/factory/runs`: the block drops `P8` because pa9 already ran). Reverted; **not** a finding against the branch — the seat's commit does not touch `docs/OPERATIONS.md`. |
| `repomap.py write` + `git diff --exit-code docs/MAP.md` | no diff — `tools/factory/plan/` is not a top-level `tools/` entry, so no MAP regeneration was owed |
| `tasks.py check` on the branch | silent, exit 0 |

Commit convention: exactly one commit; subject byte-identical to §P8's
(`cmp` against the plan line, 194 bytes, exit 0); both trailers present, in the
WORKSPACE RULES order; all six touched files inside `touches`; no board commit;
no file outside `touches`.

## Red before green

With main's `route.py` and `factory-lib.sh` restored (`git checkout 1d6d9ab --`)
and `factory-plan.sh` / `seat-plan.md` removed, this branch's tests fail exactly
as §P8 predicts:

```
not ok 46 route.py and factory_route accept the plan role and refuse the planner role
#   `[ "$status" -eq 0 ]' failed
not ok 48 factory-plan sizes the spec, routes plan/docs, and hands the brief and seat-plan to factory-task
not ok 49 factory-plan refuses an L spec or a refusing brief before the drafting seat runs
BW01: … factory-plan.sh … exited with code 127, indicating 'Command not found'
```

(`unknown role 'plan'` from the lib on test 46; `No such file` — exit 127 — on
48 and 49.) Restored: all 50 green. Test 47 is green on main by construction —
`factory_route`/`route.py lookup` never validate the *requested* role, only the
table's rows — so it is a pinning test, not a red-first one; its own mutant (a
`plan` row in the committed table) does turn it red, so it is not vacuous.

## Findings

### MAJOR 1 — the `seat-plan.md` assertion is dead in the acceptance check

`tests/unit/80-seat-driver.bats:2355-2356`:

```
  f="$BATS_TEST_DIRNAME/../../tools/factory/plan/seat-plan.md"
  [ -f "$f" ] || skip "tools/factory/plan/seat-plan.md not copied into the unit-check sandbox"
```

`checks.unit` copies `tests`, `pkgs/helm`, `pkgs/evidence`,
`tools/factory/seat` (`flake.nix:2014`), `tools/factory/route.py` (:2018),
`docs/ledger` (:2020) and three `tools/*.sh` files. It does **not** copy
`tools/factory/plan/`. Every other `|| skip` guard in this file names a path the
sandbox does have (`:405`, `:790`, `:2215` — routing.toml and route.py are
copied, so they never skip); this one is the only guard whose file is genuinely
absent, and it fires on every gated run:

```
$ nix log .#checks.x86_64-linux.unit
…
ok 213 route.py and factory_route accept the plan role and refuse the planner role
ok 214 role plan resolves to the openrouter default row, not a typed plan row
ok 215 factory-plan sizes the spec, routes plan/docs, and hands the brief and seat-plan to factory-task
ok 216 factory-plan refuses an L spec or a refusing brief before the drafting seat runs
ok 217 seat-plan.md carries the seat constraints and no typed task heading # skip tools/factory/plan/seat-plan.md not copied into the unit-check sandbox
```

Proof that the named mutant survives the gate, not merely the theory of it: I
appended `### PLAN-x (docs, S) - a typed heading` to `tools/factory/plan/
seat-plan.md`, `git add`-ed it, and ran the acceptance check —
`nix build .#checks.x86_64-linux.unit -L --no-link` **succeeded** (the same
mutation turns `nix develop -c bats tests/unit/80-seat-driver.bats` red at
`not ok 50`). So the only mechanical guard on the planning seat's plan file is
absent from CI and from `factory-integrate`'s re-run by ref.

What the missing guard would have caught is not cosmetic: `factory-brief`
prefers a `### <KEY>` section in the plan file over `FACTORY_TASK_TEXT`
(`tools/factory/seat/factory-brief:53-56` — the ad-hoc text is the *fallback*),
so a `### PLAN-…` section typed into `seat-plan.md` would silently replace the
composed packet with whatever that section says, and `factory_task_kind_size`
would stop printing `any any`.

Fix: one line in `checks.unit`'s copy list beside :2014
(`cp -r ${self}/tools/factory/plan tools/factory/plan`, after `mkdir -p
tools/factory`). `flake.nix` is outside `touches`, so under the Global
Constraints that is "a deviation to report, not to write" — the seat reported
the size-seam deviation and not this one, and §P8's Files paragraph positively
asserts "neither `flake.nix` nor the hook changes", which is where the
`missing-case` sits. Either the plan admits the copy line or the assertion moves
to a file the sandbox already has; a check that cannot fail is worth nothing
here, and P11b was rejected two days ago for the mirror image of it.

### MAJOR 2 — neither boundary of the duplicated size rule is pinned

`tools/factory/seat/factory-plan.sh:52,54` restate
`factory-plan-brief.sh:409,411`. Two one-character mutants leave the entire bats
file green:

```
--- -le 1500 -> -lt 1500       (a 1,500-word spec becomes M)
  ALL GREEN -> SURVIVED
--- -le 4000 -> -lt 4000       (a 4,000-word spec becomes an L refusal)
  ALL GREEN -> SURVIVED
```

The fixtures are 3, 1,501 and 4,001 words — the S/M assertion cannot see the
1,500 edge and the L refusal cannot see the 4,000 edge. The implementation is
right at all four values (measured, table above), so this is a coverage hole
rather than a bug, and its worst production cost today is a fail-closed refusal
of a 4,000-word spec that the packet's own `TARGET` line would call M. Two more
fixtures (1,500 → `brief-size=S`; 4,000 → `brief-size=M`) close it, and they are
what keeps the two copies of the rule from drifting apart.

### MINOR 1 — a brief that exits 3 makes `factory-plan` exit 3, not the contracted 2

`tools/factory/seat/factory-plan.sh:76` relies on `set -e` to propagate the
assignment's status verbatim, so the exit code is the brief's own, not 2. §P8
says "a non-zero exit (the graph refusal) is propagated as **exit 2** with the
script's stderr", and this script's own header reserves 3 for "a routing-table
failure". The collision is reachable: the real brief exits 3 when a mandatory
part is missing or a part fails mid-packet (`factory-plan-brief.sh:24-26`).
Measured: a fake brief exiting 3 → `factory-plan.sh` exits 3. It still fails
closed and forwards stderr, so nothing is lost but the caller's ability to tell
a routing fault from a packet fault.

### MINOR 2 — `<name>` is never validated, though `<model>` is defended

The model's `/` is replaced (`:69`), the name's is not. `name=a/b` yields the out
path `docs/reviews/plan-drafts/2026-09-06-a/b-deepseek-….md` (a subdirectory
that does not exist, and one the brief's prefix check still accepts) and the key
`PLAN-a/b`; `name='helm home 1'` yields the key `PLAN-helm home 1` and the ref
`task/PLAN-helm home 1`, which git will refuse later, after the workspace step.
An empty fourth argument is accepted too (`PLAN-`). A `case $name in *[!A-Za-z0-9-]*)`
refusal beside the spec check would cost one line.

### MINOR 3 — the header's `FACTORY_BIN` seam does not exist under that name

`factory-plan.sh:15` lists `FACTORY_BIN` in its Env block (as §P8's interface
paragraph does). `factory-lib.sh:23` assigns
`FACTORY_BIN=${FACTORY_BIN_OVERRIDE:-…}` unconditionally, so an exported
`FACTORY_BIN` is discarded. Measured — with `FACTORY_BIN=<fixtures>/bin` the
**real** driver ran:

```
factory-task: workspace: factory-ws run1 …/h/repo PLAN-nm
factory-ws: …/h/repo is not a git repository
exit=2
```

(It died at the workspace step, before any model call.) The tests use the right
variable (`FACTORY_BIN_OVERRIDE`, `:2276`), and the header's parenthetical names
it, so this is documentation only — but the failure mode of following the Env
line as written is "invokes the paid driver", which deserves the header saying
`FACTORY_BIN_OVERRIDE` outright.

### MINOR 4 — `FACTORY_TOOLBOX_REPO` is not exported to the brief

`factory-plan.sh` reads `factory-lib.sh`'s hard-coded
`/home/dalhaka/nixos-agent-env` default (:27, a plain assignment, not an
export), while the child `factory-plan-brief.sh` re-derives its own default from
its own location (`:33`, deliberately set before sourcing the lib). Run from the
live repo — the documented use — the two agree; run from a clone or the factory
base, `FACTORY_PLAN` and the routing table come from the live tree while the
packet comes from the clone. One `export` (or passing the value explicitly, as
the size now is) removes the split.

### MINOR 5 — the spec argument is resolved against two different roots, and the missing-spec arm is untested

`[ -r "$spec" ]` and `wc -w <"$spec"` resolve against the **CWD**; the brief
resolves the same string against the tree root and refuses anything outside
`docs/superpowers/specs/`. So an absolute spec path passes `factory-plan.sh` and
is then refused by the real brief:

```
$ tools/factory/seat/factory-plan-brief.sh /…/docs/superpowers/specs/2026-09-05-planning-agent-design.md docs/reviews/plan-drafts/x.md
factory-plan-brief: spec must be under docs/superpowers/specs/
  exit=2
```

Only "run from the toolbox repo root with a repo-relative spec" works (which is
what the plan's Operator item 4 types), and neither the script header nor the
README says so. Replacing the `[ -r "$spec" ]` guard with `true` leaves every
test green, so the arm is also unpinned.

### MINOR 6 — the trailers are glued to the body, so git does not parse them

Both trailer lines are present, on their own lines, in the WORKSPACE RULES
order, but there is no blank line before them, so
`git log -1 --format='%(trailers)'` prints nothing for `e18b3e5` (it prints the
`Generated-By` value for the landed precedent `9ceae52`). Landed precedent is
mixed (`8afca1b`, `be43169`, `1aa66d8` also fail to parse), so this is not a
convention breach — noted so the next attribution sweep is not surprised.

## Verdict

**REJECTED.** Two MAJORs, both vacuity rather than wrongness: the `seat-plan.md`
assertion never runs in the acceptance check (proved by a passing `unit` build
with a typed heading in the file), and neither boundary of the duplicated size
rule is pinned. The role, the router, the driver, the refusals, the export, the
out path and the packet hand-off are all correct and all rebuilt; the declared
deviation is right and the plan's Fact behind it is wrong.

A fix round `P8b` needs: (1) the `seat-plan.md` assertion running in `unit` —
either `tools/factory/plan` added to `checks.unit`'s copy list (a `flake.nix`
line, so `touches` must admit it, which is the plan's `missing-case` to correct)
or the assertion re-homed where the sandbox can see it; (2) fixtures at 1,500
and 4,000 words; (3) the six minors, of which 1 and 2 are worth code and 3–6 are
a header, an `export` and a note.
