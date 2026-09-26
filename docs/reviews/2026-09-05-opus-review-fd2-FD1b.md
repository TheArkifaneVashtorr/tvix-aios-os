# Opus gate — seat run fd2, task FD1b — APPROVED

## Summary

FD1b closes the defect FD1 was rejected for. The dispatcher contains no graph logic
at all: `grep` over `tools/factory/seat/factory-dispatch` finds `dependsOn` only
inside a comment saying it never reads it, and no `chain_root`, `dep_roots`,
`first_wave`, `awk`, `sed` or `factory_extract_task`. `<plan-file>` is now touched
in exactly three ways — resolved against `<repo-path>` when relative (lines 78-81),
`-f`/`-r` tested (82-83), and `basename`d (84). The wave comes from
`tasks.py … waves --repo NAME --plan <basename> --next` (line 143) or the
`FACTORY_WAVES_CMD` seam (139-142); a non-zero graph exit dies 6 instead of
reading as "nothing schedulable"; `--all` has a progress guard that dies 7; and
both spec'd log writes are now mutation-pinned (dropping either kills a test —
FD1's two survivors are dead).

Every required matrix row was reproduced on throwaway fixtures under a scratchpad
`FACTORY_ROOT` with a fake `factory-wave`; no real seat, wave or task was launched
and the real repo was never used as `<repo-path>`. The FD1 script run against FD1b's
tests goes red on the wrong-cwd case, the unreadable plan, exit 6, and hangs
outright on the `--all` progress case (rc 124). `shellcheck`, `bats` (15/15),
`checks.unit` (including `--rebuild`, with all fifteen tests **running**, none
skipped) and `checks.lint` are green. One commit, subject byte-identical to the
plan's, both trailers.

Two mutations survive — `--repo-name` ignored (M-G) and the launched wave's exit
code replaced by a constant (M-K). Neither is a behavioural defect: I proved
`--repo-name` really does reach the graph query (`--repo-name nosuchrepo` →
`tasks: unknown repo nosuchrepo` → exit 6) and the code propagates `$?` verbatim.
Both are test-strength gaps, filed as MINORs, because the plan's only explicit
"mutation must kill" requirement (dispatch.log, stderr) is met and no path can
launch a blocked task. `nix develop -c githooks/pre-commit` returns 1 in a fresh
clone at HEAD — the queue block goes stale the moment FD1b's own commit lands, and
the same staleness exists at the base commit; not a defect of this round (MINOR-3).

## Rule behaviour

Fixtures: a throwaway git repo `$FX/repo` with `docs/ledger/repos.toml`
(`name = "fx"`, `path = <that repo>`) and one typed plan (`A1 (code,S)` dependsOn
none, `A2 (code,S)` dependsOn A1, `B1 (docs,XS)` dependsOn none, touches disjoint);
`FACTORY_ROOT=$FX/factory`; `FACTORY_TOOLBOX_REPO=` the clone;
`FACTORY_WAVE_CMD=$FX/bin/fake-wave` (records argv + `FACTORY_PLAN`, exits
`$FAKE_WAVE_RC`); `FACTORY_WAVES_CMD` a generated one-line fake where the row calls
for it. Driver: `scratchpad/fx/matrix.sh`, `fx/edge.sh`, run via `nix develop -c bash`.

| Row | Expected | Observed |
| --- | --- | --- |
| 1 — graph is the only source | no `dependsOn`/`chain_root`/`dep_roots`/`first_wave`/plan parsing | only `# … it never re-reads dependsOn` (`factory-dispatch:6`); no other hit. Plan file used only at lines 78-84 |
| 1 — two groups from a fake | launches exactly those | `FACTORY_WAVES_CMD` printing `"A1 A2" "B1"` → `CALL: <r1> <$REPO> <A1 A2> <B1>`, exit 0 |
| 1 — fake prints nothing | no launch, exit 0, named line | `factory-dispatch: nothing schedulable in plan.md (all landed, in flight, or blocked)`, exit 0, rec file absent |
| 2 — real graph, first wave only | `"A1" "B1"`, A2 absent | `would run: factory-wave r2 $REPO "A1" "B1"` (dry-run) and `CALL: <r2> <$REPO> <A1> <B1>` (launch). A2 never appears |
| 2 — after A1+B1 land | next wave is A2 | two `--allow-empty` commits carrying `fx: add a1 (test: unit)` / `fx: add b1 (test: lint)` → `would run: factory-wave r4 $REPO "A2"` |
| 2 — wrong cwd, relative plan | resolved against `<repo-path>` | `cd /tmp && factory-dispatch r3 $REPO docs/superpowers/plans/plan.md --dry-run` → `would run: factory-wave r3 $REPO "A1" "B1"`, exit 0. FD1's F1 is dead |
| 3 — plan missing / unreadable | 2, nothing launched | `no/such/plan.md` → `no such plan`, exit 2; `chmod 000` on the real plan → `plan not readable`, exit 2. rec absent both times |
| 3 — graph query exits 1 | 6, nothing launched | `factory-dispatch: graph query failed`, exit 6, rec absent |
| 3 — `--all`, wave never changes | one launch then 7 | one `CALL:` line, stderr `wave groups: A1 B1` then `no progress`, exit 7 |
| 3 — `--dry-run` | prints, launches nothing, 0 | `would run: …`, rec absent, exit 0 |
| 4 — dispatch.log + stderr | both carry the wave line | `$FACTORY_ROOT/runs/r9/dispatch.log`: `factory-dispatch: run r9 plan plan.md groups: A1 A2 B1`; stderr: `factory-dispatch: run 'r9' plan 'plan.md': wave groups: A1 A2 B1` |
| 5 — `--repo-name` override | the graph is queried with it | `--repo-name nosuchrepo` → `tasks: unknown repo nosuchrepo` → exit 6, so the override does reach `--repo`. Without it the name comes from `repos.toml`, matched by `canon_path` (`~` expansion + `cd … && pwd -P`) against the same `cd … && pwd -P` of `<repo-path>` (`factory-dispatch:100-130`); a trailing slash on `<repo-path>` still matches (E3) |
| 6 — routed models | models come from `factory_route` | the dispatcher passes only `<run> <repo-path> <groups>` plus `FACTORY_PLAN` (line 204) — no `--model`, no `OPENROUTER_MODEL`. `factory-wave:71,73` calls `factory-task` without `--model`, which resolves `factory_route implement <kind> <size>` (`factory-task:80-93`); from the clone's `docs/ledger/routing.toml`: `implement code S → deepseek/deepseek-v4-pro-0813 medium`, `implement docs XS → deepseek/deepseek-v4-flash off`. An explicit `factory-task --model` still wins (`factory-task:51-53,80-93`); `factory-dispatch` has no `--model` pass-through and the plan asks for none |
| 7 — injection guard | refused before any eval | six probes, all exit 5 with `malformed wave line`, nothing launched, `/tmp/pwn` never created: `"A1"; touch /tmp/pwn`, `"$(touch /tmp/pwn)"`, `` "`touch /tmp/pwn`" ``, `"A1" \`, `"A1" $IFS`, `"A1"\n"B1"` |
| 8 — `FACTORY_PYTHON3_CMD` | needed by the unit sandbox | `factory-dispatch:89-96` runs `$FACTORY_PYTHON3_CMD` instead of `factory_python3`'s `nix develop -c python3`, which the nix build sandbox cannot do; documented in the script header (20-31) and the bats header (18-22). `flake.nix` +8/−2, one hunk: `cp -r ${self}/pkgs/evidence pkgs/evidence` and `mkdir -p docs; cp -r ${self}/docs/ledger docs/ledger` replacing the single `routing.toml` copy. Nothing else in flake.nix changed |
| 9 — README | interface, exit codes, flags, env | interface, `--dry-run`, `--all`, `--repo-name` and the manual gate/integrate steps: **yes**. Numeric exit codes, `FACTORY_WAVES_CMD`, `FACTORY_PYTHON3_CMD`: **no** — script header only (MINOR-6) |
| 10 — OPERATIONS.md | exactly the regenerated queue block | yes, byte-identical: a worktree at base `3d03caa` + `tasks.py write-board` produced the same blob transition `2633d4b → 2095cd6` as the commit. One line inside `<!-- tasks:begin -->`; no prose touched |

## Checks

Fresh clone of `/home/dalhaka/factory/ws/fd2/FD1b` at `task/FD1b` (`f82ef42`),
`XDG_CACHE_HOME` under the session scratchpad, every tool via `nix develop -c`.

| Check | rc | Note |
| --- | --- | --- |
| `nix develop -c shellcheck tools/factory/seat/factory-dispatch` | 0 | clean |
| `nix develop -c bats tests/unit/82-factory-dispatch.bats` | 0 | 15/15 ok |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 | |
| … same with `--rebuild` | 0 | log tests 152–166 = FD1b a…o, **all run, none skipped** |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 | |
| `nix develop -c githooks/pre-commit` | **1** | `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` — removes `FD1b` and its plan filename, i.e. the block goes stale because FD1b's own commit landed. The base commit is stale the same way (see MINOR-3). `checks.lint` does not check the board, which is why it is green |
| one commit, base `3d03caa` | pass | `git rev-list --count 3d03caa..f82ef42` = 1 |
| subject byte-identical to the plan (line 57) | pass | `seat: factory-dispatch launches a plan's next wave from the derived graph with routed models, dry-run and --all (test: unit, lint)` |
| trailers | pass | `Generated-By:` + `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` |
| `factory-dispatch` mode | pass | `100755` |
| forbidden files (`80-seat-driver.bats`, `factory-lib.sh`, `githooks/pre-commit`) | pass | untouched; `flake.nix` is in FD1b's Files |
| `docs/MAP.md` | pass | `repomap.py --root . write` in the clone leaves the tree clean — the committed MAP is a fresh write (`tests/unit — 14 → 15 files`) |
| hard-rule scan of the diff (`sudo`, `nixos-rebuild`, `systemctl`, network) | clean | two `2>/dev/null`, both benign probes (`git init` in the bats fixture; the `cd` inside `canon_path`, whose `|| printf` fallback keeps the value) |

## Red before green

FD1's dispatcher (`git -C /home/dalhaka/factory/ws/fd1/FD1 show
task/FD1:tools/factory/seat/factory-dispatch`) dropped into the clone, FD1b's tests
kept, `nix develop -c bats tests/unit/82-factory-dispatch.bats`:

```
not ok 1  … (FD1b a)  `[[ "$output" != *"A2"* ]]' failed      # FD1 offers the blocked A2
not ok 8  … (FD1b h)  `[[ "$output" != *"A2"* ]]' failed      # relative plan resolved against cwd
not ok 9  … (FD1b i)  `[ "$status" -eq 2 ]' failed            # unreadable plan does not refuse
not ok 10 … (FD1b j)  `[ "$status" -eq 6 ]' failed            # graph failure not distinguished
(FD1b k) — hangs; killed at 90 s, K_RC=124                    # no --all progress guard
ok 2,3,4,5,6,7 and ok (l|m|n|o) under FD1
```

`l`/`m` pass under FD1 because FD1 *did* write the log lines — they were merely
untested there; the mutation table below is what pins them now. Script restored,
`git status --porcelain` empty, 15/15 green again.

## Mutation table

Each: apply → assert `git diff --numstat` shows the file changed → `bats` (240 s
cap) → `git checkout --`. Driver `scratchpad/fx/mutate.sh`, `fx/mutate2.sh`.

| # | Mutation | Result |
| --- | --- | --- |
| M-A | `plan_file="$repo_path/$plan_arg"` → `"$PWD/$plan_arg"` | **killed** — `not ok 8 (FD1b h)` |
| M-B | the `-f`/`-r` plan refusals (82-83) replaced by `:` | **killed** — `not ok 9 (FD1b i)` |
| M-C | `factory_die 6` → `out=$(…) \|\| out=""` | **killed** — `not ok 10 (FD1b j)` |
| M-D | `factory_die 7 "no progress"` → `break` | **killed** — `not ok 11 (FD1b k)` |
| M-E | the `dispatch.log` append → `: "$dispatch_log"` | **killed** — `not ok 12 (FD1b l)` (FD1's M8 survivor) |
| M-F | the `factory_log` wave line → `:` | **killed** — `not ok 13 (FD1b m)` (FD1's M10 survivor) |
| M-G | `--repo-name` value discarded (`repo_name=""`) | **SURVIVED** — 15/15 ok (MINOR-1) |
| M-H | routed model replaced by a constant | **not applicable** — the dispatcher holds no routing code and passes no model (see Rule row 6); routing lives in `factory-task`, out of this task's touches |
| M-I | the validation regex → `if false` | **killed** — `not ok 6 (FD1b f)` |
| M-J | bash re-derivation reintroduced (`groups+=("A2")` when the plan names A2) | **killed** — `not ok 1, 2, 8, 15` (a, b, h, o). The "graph is the only source" pin holds |
| M-K (gate extra) | `wave_rc=$?; exit "$wave_rc"` → `exit 7` | **SURVIVED** — 15/15 ok (MINOR-2) |

Killed 8 of 10 applicable.

## Findings

No MAJORs.

**MINOR-1 — the `--repo-name` test cannot tell "honoured" from "ignored".**
`tests/unit/82-factory-dispatch.bats:255-263` passes `--repo-name fx`, which is the
same name `repos.toml` resolves to, so M-G (`tools/factory/seat/factory-dispatch:63`,
`repo_name=$2` → `repo_name=""`) leaves 15/15 green; the test's own comment admits
"Resolve still defaults to `fx` here". The behaviour is correct — my probe
`--repo-name nosuchrepo` gives `tasks: unknown repo nosuchrepo` /
`factory-dispatch: graph query failed`, exit 6 — but §FD1b's Step-1 item
"`--repo-name` override honoured" is not load-bearing. Fix: assert a name the path
lookup would never produce (bogus → exit 6), or add a second `repos.toml` row and
assert the wave differs.

**MINOR-2 — the launched wave's exit code is not pinned.** The fake exits `7` on
`FAKE_WAVE_FAIL=1` (`tests/unit/82-factory-dispatch.bats:91`) and test (g)
(`:194-200`) asserts `status -eq 7` — the same number the dispatcher itself uses for
"no progress" (`tools/factory/seat/factory-dispatch:188`). M-K replaced
`exit "$wave_rc"` (`:207-208`) with a constant `exit 7` and nothing failed, so
"propagates its exit code" is untested. Carried unchanged from FD1, but FD1b is what
made `7` a dispatcher-owned code, so the collision is new. Fix: fake exits `3`,
assert `3`.

**MINOR-3 — `nix develop -c githooks/pre-commit` fails at HEAD in a fresh clone.**
`docs/OPERATIONS.md:15`: the committed block lists `FD1b` and
`2026-09-05-factory-dispatch.md`; once FD1b's commit exists the derived block drops
both, so the hook regenerates and exits 1. This is self-referential and unavoidable:
the hook refuses a commit whose block is stale, so the block *must* be committed in
its pre-landing form. The same staleness exists at the base commit — a worktree at
`3d03caa` plus `tasks.py write-board` produces exactly the blob the commit carries.
`checks.lint` (the named acceptance) does not check the board, so it is green. This
is board issue H1, whose fix is CR5. Not a defect of this round; recorded so the
integrator does not read the hook's refusal as a new failure.

**MINOR-4 — `docs/OPERATIONS.md` is outside the plan's `touches`.** The plan lists
five touches (`2026-09-05-factory-dispatch.md:55`); the commit has six files. Forced
by MINOR-3's hook, and disclosed in `FACTORY-NOTES` ("docs/MAP.md and
docs/OPERATIONS.md (queue block) regenerated by the derived checks"), so the
disclosure rule is met — but the plan's touches line should gain it.

**MINOR-5 — §FD1b Step 4's verbatim real dry run is not in `FACTORY-RESULT`.**
The step asks for a real `--dry-run` against this repo, reported verbatim;
`/home/dalhaka/factory/runs/fd2/FD1b.result` has no such line. I could not supply it
either: this gate forbids running `factory-dispatch` against the real repo. Fix:
paste it in the result, or drop the step from the plan.

**MINOR-6 — the README omits the exit codes and the two env seams.**
`tools/factory/seat/README.md:92-121` documents the interface, `--dry-run`, `--all`,
`--repo-name` and that a non-zero `factory-wave` exit is propagated, but never the
numeric codes (2/5/6/7) nor `FACTORY_WAVES_CMD` / `FACTORY_PYTHON3_CMD`; those live
only in the script header (`tools/factory/seat/factory-dispatch:15-31`). Fix: one
line of exit codes and one of env overrides in the README section.

**MINOR-7 — die messages carry the prefix twice.** `factory_log` already prefixes
with `$(basename "$0")` (`tools/factory/seat/factory-lib.sh:29-32`), and the
messages at `factory-dispatch:82,83,141,144,172,188` start with `factory-dispatch:`
again, so the operator sees
`factory-dispatch: factory-dispatch: graph query failed`. Fix: drop the literal
prefix from the `factory_die` strings.

**MINOR-8 — an unrelated one-line reformat in the README.**
`tools/factory/seat/README.md:63` loses the two-space indent that made
"Writes the `.log` and `.result` described above." a continuation of the
`factory-task` bullet. CommonMark lazy continuation keeps the rendering identical
and `treefmt` is clean either way, but the line is not part of FD1b's work and is
not disclosed.

**Nits (no fix required).** (a) `resolve_repo_name`
(`tools/factory/seat/factory-dispatch:112-130`) assumes `name` precedes `path`
inside a `[[repo]]` table; with the order swapped it yields an empty name and the
run dies 6 (`tasks: unknown repo`) rather than guessing — safe, and the committed
`docs/ledger/repos.toml` always writes `name` first. (b) `--repo-name --dry-run`
swallows the flag as the value; result is exit 6, nothing launched. (c) `"-rf"`
satisfies the wave-line class and arrives at `factory-wave` as the group word
`<-rf>` — positional after `set --`, no shell escape; carried from FD1 unchanged.

## Verdict

**APPROVED.** Every FD1 rejection ground is closed and mutation-pinned: the graph is
the only source of the wave (M-J dies), a relative plan resolves against
`<repo-path>` (M-A dies), an unreadable plan refuses with 2 (M-B dies), a failed
graph query dies 6 instead of reading as "nothing schedulable" (M-C dies), `--all`
cannot spin (M-D dies), and FD1's two untested log writes now both kill a test
(M-E, M-F). No fixture, probe or mutation produced a launch of a blocked task, and
all fifteen tests really run under `checks.unit`. The two surviving mutations are
test-strength gaps on behaviour I verified directly, and the `githooks/pre-commit`
refusal is the board's pre-existing H1 queue-block loop, present at the base commit
too. Gate work stayed inside a throwaway clone, the session scratchpad and this
file; `/home/dalhaka/factory` was never modified and no seat, wave or task was
launched.
