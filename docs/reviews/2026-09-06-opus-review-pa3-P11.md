# Opus gate — seat run pa3, task P11 — REJECTED

## Summary

One commit (`e96158e`), six files, all inside `touches`, subject byte-identical
to the plan's, both trailers present, no board commit. Rules 1–5 are implemented
and the nine plan-named mutants all die. Every check is green: shellcheck on the
four scripts, `bats` 54/54 on `80-seat-driver.bats` and 15/15 on
`82-factory-dispatch.bats`, `unit` (362 tests), `factory-unit`, `lint`, and the
lint gate (which regenerates only the board's queue block, inside the markers —
the branch itself never touches `docs/OPERATIONS.md`). `docs/MAP.md` regenerates
with no diff. Red-before-green reproduces: with `git show 91dcc5f`'s four
scripts, 8 of the 9 new tests go red and the old 45 stay `ok`.

One MAJOR stops it. `FACTORY_PLAN` is now required on every `factory-wave`
launch, but `tools/ritual.sh`'s in-flight **relaunch hint** — the operator's one
printed recipe for resuming a wave whose driver died — still prints
`relaunch: factory-wave <run> <repo> "<group>"` with no `FACTORY_PLAN=`. Run
verbatim it now exits 2 and launches nothing. `run.meta` carries the `plan:` line
this needs, but `tools/ritual.sh` is outside P11's `touches` and the plan never
asks for the hint to change: this is a plan defect, not an implementer's slip,
and it is fixed by re-planning, not by editing this branch.

Facts checked against a fresh clone of `task/P11` at
`…/scratchpad/gate-pa3-P11`; every driver invocation used a fixture repo, a
`FACTORY_ROOT` under the scratchpad, and a fake `dsh-openrouter`/`factory-task`
on PATH. The real repo and the real `~/factory/runs` were never written.

## Rule 1 (the plan)

`factory-task:73-77` and `factory-wave:98-103` refuse before anything is
created. Measured, `factory-task r1 <fixture-repo> K1`:

| FACTORY_PLAN | expected | observed | exit | `runs/` |
|---|---|---|---|---|
| unset | refuse, nothing written | `factory-task: FACTORY_PLAN is unset — name the plan (FACTORY_PLAN=<plan.md> …) or launch through factory-dispatch` | 2 | absent |
| empty | same | same message | 2 | absent |
| a directory | `factory_need_file` die | `factory-task: no such file: …/repo/docs` | 2 | absent |
| a missing path | same | `factory-task: no such file: …/nope.md` | 2 | absent |
| a file, mode 000 | `factory_need_file` die | **workspace cloned, `runs/r1` created**, then `awk: fatal: cannot open file … Permission denied` | 2 | `r1` |

`factory-wave` behaves identically for unset/empty/directory (`runs=[ABSENT]`,
exit 2, nothing called: the `FACTORY_BIN_OVERRIDE` recorder file stayed empty),
and for mode 000 it **dispatches the whole wave** (`factory-wave: run 'r1': 1
group(s)`, exit 0 with the fake task). `factory_need_file` is `[ -f "$1" ]`, not
`[ -r ]` — the plan's "the existing `factory_need_file` die (exit 2, `no such
file:`)" is a wrong fact about that helper, and `README.md:77`'s "a
set-but-unreadable path dies with the same `no such file:` exit 2" is wrong with
it. No paid seat starts in either case (the death is at `factory-brief`, before
the launch), so this is a MINOR, not a MAJOR.

Relative and spaced paths (`FACTORY_ROOT` fixture, `factory-wave r1 <repo> "K1"`):

- relative `FACTORY_PLAN=pfile.md`, cwd `…/gate-p11-fx` → `run.meta` records
  `plan: /…/gate-p11-fx/pfile.md` (absolute, via `plan_abs`), but the child saw
  `FACTORY_PLAN=[pfile.md]` — the raw value, **not** `plan_abs`. `factory-wave`
  never exports `plan_abs`; the child inherits the caller's value. The contract
  says it "exports it unchanged to every `factory-task` it starts". It still
  resolves today only because cwd is inherited unchanged. MINOR-1.
- `…/with space/p sp.md` → `plan:` line and the child's value both carry the
  space verbatim; the wave completed.
- the scratch-launcher shape `FACTORY_PLAN=<abs> factory-wave r1 <repo> "K1 K2"`
  → two keys in one group, `K2` called `--after K1`, both saw the absolute plan,
  `group: K1\ K2` in `run.meta`.

`run.meta` ordering is as specified — `run:`, `repo:`, **`plan:`**, `base:`,
`pid:`, `launched:`, `group:` — matching the live shape in
`/home/dalhaka/factory/runs/pa5/run.meta` with one line inserted.
`factory-dispatch:204` is unchanged and still sets `FACTORY_PLAN="$plan_file"`;
its 15 bats tests (dry run and a real launch through `factory-wave`) are green.

## Rule 2 (the board)

`factory-integrate:82-91`. Nine real git fixtures in one run (`K1 … K9`), where
`main` moved its own queue block **and** added board prose after every branch
forked:

| key | branch's board change | expected | observed |
|---|---|---|---|
| K1 | prose outside the markers | REFUSED | `REFUSED K1: docs/OPERATIONS.md changed outside the queue block` |
| K2 | none | merge | `MERGE K2 ok` |
| K3 | only between the markers | merge | `CONFLICT K3` — main's block moved too, so it is a textual conflict, not a refusal (the guard let it through; with a still block it merges — bats 50) |
| K4 | inside **and** outside | REFUSED | `REFUSED K4` |
| K5 | none, forked before main's board moved | merge | `MERGE K5 ok` (kills the tip-vs-merge-base mutant) |
| K6 | outside, and main's block also moved | REFUSED | `REFUSED K6` |
| K7 | block only, conflicting with main's block | conflict path | `CONFLICT K7` (`CONFLICT (content): Merge conflict in docs/OPERATIONS.md`) |
| K8 | deletes the `tasks:end` marker | REFUSED | `REFUSED K8` (the mask swallows the tail, so the masked texts differ) |
| K9 | markers absent on the branch side | REFUSED | `REFUSED K9` |

Summary: `merged: K2 K5` / `conflicts: 7` / `refused: 5` / `head: 2589d85`,
exit 1. The loop continued past every refusal; `FACTORY_CHECK_CMD` ran exactly
once (`CHECKRAN`, `CHECK custom pass`) against an integ tree holding only `K2`
and `K5`; `integ/r1`'s log carries `k2: add y` and `k5: add z` and neither `k1:`
nor `k4:`.

Two summary blemishes (MINORs 4 and 5): `conflicts=$((${#keys[@]} -
${#merged[@]}))` at `factory-integrate:163` counts refused keys as conflicts, so
one refusal reports `conflicts: 1` *and* `refused: 1`; and when **every** key is
refused the early exit at `factory-integrate:102-107` prints
`no branch merged cleanly` / `merged: (none)` and exits 1 with **no `refused:`
line at all** — measured on a one-key run. One code smell: `[ -n "$mb" ] && …`
at line 83 makes an empty `merge-base` (unrelated histories) skip the guard
silently — fail-open, though the surrounding `git fetch origin` under `set -e`
makes it hard to reach.

## Rule 3 (the near miss)

`factory-task:224-238, 249-257`. Fake seat, one payload per run, `.result` read
back:

| payload | `.result` line 1 | notes | exit |
|---|---|---|---|
| `FACTORY-RESULT: status=done` | `FACTORY-RESULT status=failed exit_code=0` | `result-misparse: FACTORY-RESULT: status=done` | 2 |
| `FACTORY-RESULT status: done` | failed | `result-misparse: FACTORY-RESULT status: done` | 2 |
| `FACTORY-RESULT status=succeeded` | failed | verbatim | 2 |
| `**FACTORY-RESULT status=done**` | failed | verbatim | 2 |
| `- FACTORY-RESULT status=done` | failed | verbatim | 2 |
| tabs: `FACTORY-RESULT\tstatus:\tdone\tand\ttabs` | failed | `result-misparse: FACTORY-RESULT status: done and tabs` (tabs → spaces) | 2 |
| ESC bytes: `…status=bogus \x1b[31mred\x1b[0m tail` | failed | `…status=bogus  [31mred [0m tail` (ESC → space) | 2 |
| 300-byte near miss | failed | note body exactly **200** bytes | 2 |
| line containing `<` only | failed | `the seat produced no usable FACTORY-RESULT line; see <log>` (ignored for both classes) | 2 |
| `FACTORY-RESULT status=partial` | `status=partial` | `(none given)`, no misparse | 1 |
| `FACTORY-RESULT status=done extra=1` | `status=done extra=1` | no misparse | 0 |
| near miss **then** a real `status=done` block | `status=done` | the seat's own notes | 0 |
| a real `status=done` block **then** a near miss | `status=done` | the seat's own notes — never re-classified | 0 |
| two accepted lines | `status=partial` (the last wins) | — | 1 |
| `FACTORY-RESULT status=done\r` (CRLF) | `status=done` — CR is `[[:space:]]`, so it is ACCEPTED | — | 0 |
| `FACTORY-RESULT status=done   ` | accepted, trailing spaces kept | — | 0 |

`factory-wave`'s summary reads the synthesised block: with a real workspace and
the colon payload it printed `K1 status=failed checks=none=not-run commits=0`.
CR3rb's commit check composes cleanly — the near-miss arm sets `status=failed`,
so the `done`-scoped `claimed N / found M` block at `factory-task:281-301` never
fires, and its own tests (42–45) stay green.

**MINOR-3, the collision rule 4 creates.** The grammar sentence rule 4 adds
contains `FACTORY-RESULT` and **no `<`**, so it is itself a NEAR-MISS line. Fed
a seat that echoes it and then dies:

```
FACTORY-NOTES result-misparse:   The first line is exactly FACTORY-RESULT, one space, status=done|partial|failed — no colon, no markdown; any other spelling is recorded as failed.
```

instead of the honest `the seat produced no usable FACTORY-RESULT line; see
<log>`. The status is still `failed`, so nothing is recorded as done; the record
is merely a false diagnosis. `factory-task:215-220`'s own comment says a
headless model's reasoning "routinely echoes that template back", so this is a
live path, not a hypothetical.

## The in-flight reader

`tools/ritual.sh` is byte-identical between `91dcc5f` and `e96158e` (`diff` →
IDENTICAL). Against a fixture `runs/r1/run.meta` carrying the new `plan:` line,
both copies print the same single line and exit 0 — the unknown key is ignored,
as Assumption 5 promised:

```
r1 K1 - running - log age 0m - then: gate; ff - relaunch: factory-wave r1 /…/repo K1\ K2 --then gate\;\ ff
```

Removing the `plan:` line changes nothing. The reader is intact.

The **hint** is not. It is built at `tools/ritual.sh:390-395` from `run:`,
`repo:`, the `group:` lines and `then:` — and never from `plan:`. Run verbatim
against this branch's `factory-wave` with `FACTORY_PLAN` absent from the
environment (which is how the operator's launch recipe works — the variable is
set per command, not exported):

```
$ env -u FACTORY_PLAN factory-wave r1 /…/repo K1\ K2 --then gate\;\ ff
factory-wave: FACTORY_PLAN is unset — name the plan (FACTORY_PLAN=<plan.md> …) or launch through factory-dispatch
exit=2      runs=[ABSENT]
```

The same argv against `91dcc5f`'s `factory-wave` launched both keys (exit 0).
So P11 converts every relaunch hint the ritual prints into a dead launch.
`tools/ritual.sh` is not in P11's `touches` and the plan's interface 1 never
mentions the hint, so the implementer could not have fixed it without a
deviation. MAJOR-1, against the plan.

## Tests and mutants

`bats --count`: 45 on `91dcc5f`'s file, 54 on HEAD's — nine appended, none
renamed or deleted. All 54 pass, plus 15 in `82-factory-dispatch.bats`.

`setup()` now writes an empty `$PLAN` and exports `FACTORY_PLAN` for every test
(`80-seat-driver.bats:20-22`); `FACTORY_PLAN` mentions go 17 → 31. Spot-checked
the old tests that reach `factory-task` without their own `FACTORY_PLAN` (e.g.
"dispatches to the seat directory it was run from"): the assertion and the
reason it holds are unchanged.

| mutant | change | died? | on |
|---|---|---|---|
| M-A | the 2026-09-04 default plan restored | yes | 46 |
| M-B | wave's guard moved after `run.meta` is written | yes | 29, 30, 32, 33, 34, 41, 47, 48 |
| M-C | `plan:` line dropped | yes | 48 |
| M-D | board check dropped | yes | 49, 50 |
| M-E | `mb` → `origin/$default_branch` tip | yes | 51 |
| M-F | block masking dropped (raw file compare) | yes | 50 |
| M-G | near-miss capture arm dropped | yes | 52, 53 |
| M-H | ACCEPTED regex loosened to `status[:=][[:space:]]*(done\|…)` | yes | 53 |
| M-I | the 200-byte cut removed | yes | 53 |
| extra | ACCEPTED regex loosened to `status[:=](done\|…)` (no space) | **no** | — |
| extra | `\| tr '[:cntrl:]' ' '` removed | **no** | — |
| CR3rb M-I | commit verification block disabled | yes | 42, 44, 45 |
| CR3rb M-I2 | bare-`ok` rejection removed | yes | 45 |
| CR3rb M-E | `group: %q` → `%s` | yes | 29, 30, 41 |

**12 of 14.** Every mutant the plan names dies; CR3rb's prior kills still die.
The two survivors are coverage gaps, not behaviour bugs (MINORs 6 and 7): rule
3's "tabs and control bytes replaced by a space" clause is pinned by no test —
I verified the behaviour by hand with a tab and an ESC byte — and
`FACTORY-RESULT status:done` (colon, no space), a NEAR-MISS by the contract's
own definition, is not pinned either. Each mutant was applied to the file,
`diff`ed to prove the tree changed, run, and reverted (`git diff --quiet` after
each).

## Checks

| check | result |
|---|---|
| `shellcheck` on the four scripts | clean |
| `bats tests/unit/80-seat-driver.bats tests/unit/82-factory-dispatch.bats` | 69/69 ok |
| `bats --count` 80-seat-driver | 54 (was 45) |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0, 362 tests |
| `nix build .#checks.x86_64-linux.factory-unit -L --no-link` | 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 |
| `nix develop -c githooks/pre-commit` | 1 — only the known board regeneration, and the one changed line is between `tasks:begin`/`tasks:end` |
| `python3 pkgs/evidence/repomap.py --root . write` | no diff to `docs/MAP.md` |
| bare-host-PATH dependencies | `cmp awk grep tr head git sed cut` all in `/run/current-system/sw/bin`; no python3/jq/node added |
| host `grep` vs devShell `grep` on the new patterns | identical output (both GNU grep 3.12) |

Rule 4's sentence is byte-exact against the plan text (`cmp` on the line minus
its two-space indent). Rule 5: `README.md` names both scripts' `FACTORY_PLAN`
refusal and exit 2 (75-77, 104-106), the `plan:` line in `run.meta` (47), the
near-miss record (98), and `REFUSED <KEY>` with `refused: N` (138).

## Red before green

`git show 91dcc5f:tools/factory/seat/<script>` for all four, this branch's test
file:

```
ok  1..45   (unchanged in verdict)
not ok 46 factory-task refuses to run when FACTORY_PLAN is unset …
#   `[[ "$output" == *"FACTORY_PLAN is unset"* ]]' failed
not ok 47 factory-wave refuses to run when FACTORY_PLAN is unset …
#   `[ "$status" -eq 2 ]' failed
not ok 48 factory-wave records plan: in run.meta and passes FACTORY_PLAN through …
not ok 49 factory-integrate refuses a board rewrite outside the queue block …
#   `[ "$status" -eq 1 ]' failed
not ok 50 factory-integrate's board guard merges a queue-block-only change …
#   `[ "$status" -eq 1 ]' failed
ok     51 … compares against the merge base, not origin's moving tip
not ok 52 factory-task records a near-miss result block verbatim as failed
#   `[[ "$output" == *"FACTORY-NOTES result-misparse: FACTORY-RESULT: status=done"* ]]' failed
not ok 53 factory-task records every near-miss spelling verbatim …
not ok 54 factory-brief quotes the exact FACTORY-RESULT grammar …
```

46 ok / 8 not ok. Test 51 passing on main is by design — it is the
discriminating row that only the tip-vs-merge-base mutant reddens, and M-E
proves it does. Restoring the branch's scripts → 54/54.

## Findings

### MAJOR-1 — the ritual's relaunch hint is now a dead launch

`tools/ritual.sh:390-395` (unchanged) vs `tools/factory/seat/factory-wave:98-100`

```
relaunch="relaunch: factory-wave $run"
[ -n "$repo_meta" ] && relaunch="$relaunch $repo_meta"
for g in "${missing_groups[@]}"; do relaunch="$relaunch $(printf %q "$g")"; done
[ -n "$then_text" ] && relaunch="$relaunch --then $(printf %q "$then_text")"
```

No `FACTORY_PLAN=`. Measured above: the hint's own argv now exits 2 and launches
nothing, where on `91dcc5f` it launched both keys. `run.meta` already carries
`plan:`, so the repair is one line in the hint — but `tools/ritual.sh` is
outside P11's `touches` and the plan asks only that the reader tolerate the new
key. Re-plan.

### MINOR-1 — `factory-wave` does not export the absolute plan path

`tools/factory/seat/factory-wave:103` computes `plan_abs` and writes it to
`run.meta:152`, but `run_group` at 185/187 starts `factory-task` with the
inherited `FACTORY_PLAN`. With a relative value the record and the child
disagree (`plan: /…/gate-p11-fx/pfile.md` vs `FACTORY_PLAN=[pfile.md]`).
Contract: "exports it unchanged to every `factory-task` it starts."

### MINOR-2 — an unreadable plan is not refused

`factory_need_file` is `[ -f ]`. A mode-000 plan clones a workspace, creates
`runs/<run>`, and dies at `factory-brief` with an `awk … Permission denied`;
`factory-wave` dispatches the whole wave. `README.md:77` documents the opposite.
`[ -r "$plan" ]` is the one-line fix.

### MINOR-3 — rule 4's sentence sits inside the result-block template

`tools/factory/seat/factory-brief:92-98`. The rule reads "each item on its own
line and **nothing after it**", then lists the four template lines, and the new
sentence is line five of that list. It is prose, not a template item, and the
plan says "appended to the WORKSPACE RULES block's **summary rule**". Because
it holds `FACTORY-RESULT` with no `<`, an echo of it is a NEAR-MISS: a seat that
quotes the rules and then dies is recorded as
`result-misparse: The first line is exactly FACTORY-RESULT…` (demonstrated)
instead of `the seat produced no usable FACTORY-RESULT line`. Moving it above
the template — into the bullet's own prose — fixes both halves.

### MINOR-4 — refused keys are also counted as conflicts

`tools/factory/seat/factory-integrate:163`. One refusal prints `conflicts: 1`
and `refused: 1`.

### MINOR-5 — an all-refused run prints no `refused:` line

`tools/factory/seat/factory-integrate:102-107` exits before the summary block.
Measured: one key, refused → `no branch merged cleanly` / `merged: (none)`,
exit 1, no `refused:`.

### MINOR-6 — rule 3's control-byte fold is untested

Deleting `| tr '[:cntrl:]' ' '` from `factory-task:252` leaves all 54 tests
green. The behaviour is right; nothing pins it.

### MINOR-7 — the `status:done` near-miss spelling is untested

Loosening the ACCEPTED regex to `status[:=](done|partial|failed)` leaves all 54
tests green, so a colon-with-no-space spelling would be recorded as done with no
test objecting.

### MINOR-8 — the board guard fails open on an empty merge-base

`tools/factory/seat/factory-integrate:83`: `[ -n "$mb" ] && …`. Unreachable in
practice today, but the safe default is to refuse, not to skip.

## Verdict

REJECTED — MAJOR-1. Rules 1–5 are correct, tested and mutant-killing, and I
would land them unchanged; what stops the branch is that the plan requires
`FACTORY_PLAN` without giving the ritual's relaunch hint a way to supply it, and
the file that prints the hint is outside P11's `touches`. Re-plan as **P11r**
adding `tools/ritual.sh` to `touches`: read `plan:` from `run.meta` and prefix
the hint with `FACTORY_PLAN=$(printf %q "$plan_meta") `, omitting the prefix when
`run.meta` has no `plan:` (a pre-P11 run), with a bats row in
`tests/unit/9x-ritual*.bats` for each. Fold MINORs 1–3 into the same section
(export `plan_abs`; `[ -r ]` in `factory_need_file` or at the two call sites;
move the grammar sentence above the template and out of the near-miss class) and
MINORs 4–8 as the section's minor list.

plan_defect: missing-case — P11 requires FACTORY_PLAN but never updates ritual.sh's relaunch hint
