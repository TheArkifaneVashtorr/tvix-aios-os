---
reviewer: opus
majors: 1
minors: 6
---
# Opus gate — seat run sc5, task G11b — REJECTED

Task: `G11b` (code, S) — G11's fix round: cross-repo dependencies resolve by the repo the
task runs in; states and rows made exact. Plan
`docs/superpowers/plans/2026-09-05-session-context.md` §`G11b`; rejection it answers
`docs/reviews/2026-09-05-opus-review-sc5-G11.md`. Workspace
`/home/dalhaka/factory/ws/sc5/G11b`, branch `task/G11b`, head `f10636cf8e7e`, base
`d664bf3`. Reviewed in a throwaway clone; the workspaces were not touched.

## Summary

Every clause of "The rule, exactly" is implemented and I verified each one with my own
fixtures on real git repositories, not the shipped ones. The cross-repo edge now resolves
against the attributed repo's own history (`AA1` → `ready` when B lands T9, `blocked | T9`
when it does not); `check`'s namespace is per-repo again and the live-shaped `PB1 →
PB0(gaming)` case passes only because the repo's own typed keys are in the resolvable set
— I proved that set load-bearing on both the suite and the real tree. Status rows validate,
`STATES` and the brief's table gain both columns, `board_graph` carries `task_status` and
`write-board` omits a withdrawn key. Nine new tests, all red on base; eighteen mutations
applied, seventeen killed, including all six G9/G8c re-runs and G11's two survivors (M7b
and the dead `defined_roots`). `evidence-unit`, `lint` and the hook are green.

It is rejected on one thing the fix round did not carry across: **the resolved edge is not
consumed by the scheduler.** `derive_status` now calls the dependent `ready`, but `waves`
still computes its satisfied set from this repo's own landed tasks, so the dependent enters
no wave — and therefore no seat group, no `**Next wave**` line and no queue block. On the
live-shaped `PB1 → PB0(gaming)` fixture the graph says `PB1 ready` and the board says
`nothing queued`, at the same instant, from the same tree. G11 was rejected for a permanent
false block; this replaces it with a permanent invisible-ready, and the commit body's "never
permanently blocked while that repo has it landed" reads as *dispatchable* when it is not.
Nothing tests it, so nothing would catch it later. G11's own rejection named this in its
fix list ("`waves` must schedule the dependent once the edge resolves"); the plan's "rule,
exactly" dropped it, so the design change belongs in the re-plan.

## The rule (each clause verified)

All rows below are my own fixtures — real `git init` repositories with real `git log`,
never the implementer's `fake_git` — run against the shipped `pkgs/evidence/tasks.py`.
Script: throwaway, under the gate scratchpad.

| clause | my evidence | verdict |
|---|---|---|
| **(a)** repo A plan `### T9 … **repo:** B` + `### AA1 … dependsOn T9`; B's log has T9's subject | `A: [('AA1','ready','')]`, `B: [('ZZ9','ready'),('T9','landed','x: t9 …')]`, `check: []` | **pass** |
| **(a′)** same, B's log *without* T9's subject | `A: [('AA1','blocked','T9')]`, `B: [('ZZ9','ready'),('T9','ready')]`, `check: []` — never satisfied by mere existence | **pass** |
| **(a″)** the dependent reaches a wave once the edge resolves | `waves(A) == []` in **both** cases; `render_brief` → `**Next wave** — none`; `render_board_block` → `nothing queued`; `factory_args` *does* include it | **FAIL — MAJOR 1** |
| **(b)** dependsOn naming a key defined only in B's own plans | `check: ['tasks: repo-a/AA2 dependsOn ZZ9: unknown key']` — no global namespace | **pass** |
| **(c)** M7b: live-shaped `PB1 → PB0(repo gaming)`, gaming's log carries PB0's subject | at HEAD `check: []` and `PB1 ready`; with M7b applied (per-repo scoping *without* the attribution set) `check` errors `tasks: nixos-agent-env/PB1 dependsOn PB0: unknown key` on my fixture, on the shipped test **and** on the real tree | **pass — M7b now dies** |
| **(d)** mistyped status row | `withdrawnn` → `tasks: task-status row repo/p.md/T1: unknown status withdrawnn`; `""` and `done` likewise; `withdrawn`/`parked` clean | **pass** |
| **(e)** `withdrawn`/`parked` in `STATES`, in the brief's columns, never scheduled, never in conflicts, once in the brief | `STATES = (…, 'blocked', 'withdrawn', 'parked')`; header gains both columns, row `\| repo \| 0 \| 0 \| 0 \| 0 \| 0 \| 2 \| 0 \| 1 \| 1 \| 0 \| 0 \|`; `waves` → `[['T3','T4']]` (T1/T2 absent); `conflicts` → only `T3/T4`, never the withdrawn T1 that shares `a.py` across two plans; `md.count('repo/T1') == 1`; every emitted state ∈ `STATES` | **pass** (the shipped test's own `conflicts == []` assertion is vacuous — see MINOR 5; I proved the behaviour myself with a two-plan fixture) |
| **(f)** `board_graph(...)["task_status"]` populated → `write-board` omits a withdrawn key | `task_status: [('root','board.md','W1')]`; block = `… K1 (board.md)`; `check(board)` clean | **pass** |
| **(g)** `defined_roots` gone | **not gone** — `scan_repo` still returns `"defined_roots": sorted(defined)` and `check` reads it. But its meaning changed: it is now the per-repo resolvable set and is load-bearing (M9 below kills it on the suite *and* on the real tree). Disclosed in NOTES. Deviation from the plan's literal step, and the right call — deleting it would break clause (c) | **deviation, accepted** |

Two further behaviours I probed that the rule does not name, both benign-looking and both
silent (MINOR 2, MINOR 3):

- `**repo:** dsh-harnes` (a typo; not in `repos.toml`): the task vanishes from **every**
  repo's graph — `T5 visible anywhere: False`, absent from the brief — and its dependent is
  `blocked | T5` forever with `check` clean. G11's rejection asked for a rule refusing an
  unconfigured `**repo:**` value; the plan's rule dropped it.
- withdrawing a cross-repo task still needs the row keyed by the **attributed** repo
  (`repo = "gaming"`, `plan = "2026-09-05-operator-items.md"`); the natural spelling
  (`repo = "nixos-agent-env"`) is refused as an unknown key. Correct per the plan, but the
  file's one-line header does not say it.

## Checks

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | **pass** — 81 passed |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **pass** — treefmt 0 changed, all checks passed |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 (`docs/OPERATIONS.md queue block was stale and has been regenerated`) → `git add` → exit 0, `render.test.mjs: all assertions passed`. One regenerate-and-re-add, exactly the allowance |
| pytest | `pytest tests/evidence -q -p no:cacheprovider` | 81 passed |

The hook's one regenerate is G8c's known tax: the commit's own subject enters `git log`
only after the commit, so the block goes stale by exactly the key that just landed
(`B1 G11b OG1b RT5` → `B1 G12 OG1b RT5`). Same as observed on G11. Not a fault.

Commit hygiene: **one** commit on `d664bf3`. Touched files —
`pkgs/evidence/tasks.py`, `tests/evidence/test_tasks.py`, `docs/ledger/task-status.toml`,
the two plan files, `docs/OPERATIONS.md` — a subset of G11b's `touches`. The plan diffs are
**only** four added `**repo:**` lines (three in `2026-09-05-harness-router.md` under H1, H2,
H2b; one in `2026-09-05-operator-items.md` under PB0); no heading is touched, and H2c's line
was already on base, so it was correctly left alone. `docs/OPERATIONS.md` changes only the
generated block line (drops `H1`). Subject byte-identical to the plan's (`cmp` against the
plan text: identical). `Generated-By: dsh …` and `Co-Authored-By: Claude Fable 5.1` both
present. The commit body discloses the cross-repo semantic, the per-repo `check` scoping and
the `STATES` extension.

`docs/ledger/task-status.toml`: 71 bytes, mode `100644`, one comment line, **ends with a
newline**, parses (`tomllib` → `{}`). Both contents are reproduced under **Findings** for the
integrator — OG1b creates the same path and is still uncommitted.

## Red before green

Base `d664bf3`'s `tasks.py` restored under HEAD's tests: **9 failed, 72 passed**.

| test | failure on base |
|---|---|
| `test_repo_field_attributes_cross_repo_task` | `TypeError: scan_repo() got an unexpected keyword argument 'repos'` |
| `test_board_graph_excludes_cross_repo_task` | `AssertionError: 'T1' not in '**Queued …(board.md)'` — behavioural |
| `test_task_status_withdrawn_and_unknown_key` | `TypeError: … unexpected keyword argument 'task_status'` |
| `test_cross_repo_dep_resolves_via_attributed_repo` | `TypeError: … 'repos'` |
| `test_check_rejects_dep_defined_only_in_other_repo` | `TypeError: … 'repos'` |
| `test_check_accepts_dep_redirected_to_other_repo` | `TypeError: … 'repos'` |
| `test_check_rejects_unknown_status_value` | `assert False` — no `unknown status` error is emitted — behavioural |
| `test_states_include_withdrawn_and_parked_in_brief` | `AssertionError: 'withdrawn' in ('landed', …)` — behavioural |
| `test_board_graph_exposes_task_status_and_omits_withdrawn` | `KeyError: 'task_status'` — behavioural |

Five of nine are signature `TypeError`s, acceptable because the keyword arguments are new
this round; four fail behaviourally. `tasks.py` restored; the clone is pristine at
`f10636c` (`git status --porcelain` empty).

## Mutation table

Each mutation applied to the delivered tree, full `tests/evidence` run, then reverted; the
tree was confirmed byte-identical afterwards.

| # | mutation | result |
|---|---|---|
| M1 | cross-repo edge **always** satisfied (drop the `landed_subjects` test) | **killed** — `test_cross_repo_dep_resolves_via_attributed_repo` |
| M2 | cross-repo edge **never** satisfied (G11's bug: stop passing `extra_landed`) | **killed** — `…resolves_via_attributed_repo`, `…accepts_dep_redirected_to_other_repo` |
| M3 | global namespace in `check` (union `defined_roots` + tasks over **all** repos) | **killed** — `test_check_rejects_dep_defined_only_in_other_repo` |
| M4 | attributed repo ignored (resolve the landing against **R**'s log, not B's) | **killed** — `…resolves_via_attributed_repo`, `…accepts_dep_redirected_to_other_repo` |
| M5 | withdrawn/parked still scheduled (`open_tasks` keeps them) | **killed** — `test_task_status_withdrawn_and_unknown_key`, `…board_graph_exposes_task_status…` |
| M6 | withdrawn reachable in `conflicts` (iterate all tasks, bypassing `open_tasks`) | **SURVIVED** — 81 passed. The shipped assertion is vacuous (MINOR 5); behaviour verified by hand |
| M7 | status validation dropped | **killed** — `test_check_rejects_unknown_status_value` |
| M8 | `board_graph` drops `task_status` from its return | **killed** — `test_board_graph_exposes_task_status_and_omits_withdrawn` |
| M9 | `defined_roots` dropped from `check` (= G11's surviving **M7b**) | **killed** — `test_check_accepts_dep_redirected_to_other_repo`; **and** on the real tree: `tasks: nixos-agent-env/PB1 dependsOn PB0: unknown key` |
| M10 | task-status unknown-**key** rule dropped | **killed** — `test_task_status_withdrawn_and_unknown_key` |
| M11 | `FIELD_RE` drops `repo` (field ignored) | **killed** — four tests |
| M12 | `own_plan_tasks` keeps foreign-repo tasks | **killed** — two tests |
| G9-a | chain rules 2–4 owned by the root, not the last member | **killed** — 5 tests incl. `test_chain_last_member_result_beats_root_review` |
| G9-b | `conflicts` drops the different-plan condition | **killed** — `test_conflicts_same_plan_not_reported` |
| G9-c | `waves --factory-args` without `--plan` no longer exits 2 | **killed** — `test_main_waves_factory_args_requires_plan` |
| G9-d | `legacy open` counts all legacy rows | **killed** — `test_brief_legacy_open_counts_only_open` |
| G8c-g | `board_graph` reads `repos.toml` | **killed** — `test_write_board_queue_ignores_run_results`, `test_board_graph_derives_this_tree_ignoring_repos_toml` |
| G8c-h | `check --board` compares against the live graph | **killed** — `test_main_check_board_stale_current_and_runs_free` |

Seventeen of eighteen killed. Both of G11's survivors (M7b, `defined_roots`) are now dead —
by the same mutation, M9, which also fails on the real tree. All six G9/G8c re-runs are
still dead. The single survivor is the vacuous-fixture MINOR, not a semantic hole.

There is no mutation for the `waves` gap because there is nothing to mutate: no code and no
test consumes the resolved edge.

## Real data

`repos.toml` in a scratch root (read-only everywhere else) names `nixos-agent-env` at the
clone and the four siblings at their real paths; `--runs-dir /home/dalhaka/factory/runs`,
`--store /home/dalhaka/factory/store`.

```
| repo | landed | approved | rejected | ran | recorded | ready | blocked | withdrawn | parked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 63 | 0 | 1 | 5 | 0 | 1 | 1 | 0 | 0 | 1 | 0 |
| media | 3 | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| gaming | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nixos-skill | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dsh-harness | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
```

- `dsh-harness`: H1, H2, H2b **and** H2c all `landed`, each by that repo's own commit
  subject. H2c's `**repo:**` line was already on base and is unchanged here.
- `gaming`: PB0 `landed` (`gaming: nixpkgs → nixos-26.05 head (2026-09-05); …`).
- `nixos-agent-env`: **none** of H1/H2/H2b/H2c/PB0. Exactly the plan's Step 4 expectation.
- `PB1` under `nixos-agent-env` is **`ran`** (`PB1 status=done run=pb1`), not `landed`. The
  gate brief expected `landed`; the difference is the clone, not the code — live main
  (`4180dca`) carries PB1's subject, base `d664bf3` (an ancestor of live main) does not, and
  the scratch `repos.toml` points at the clone. Rule 3 (`ran`) precedes rule 5, so PB1's
  state does not exercise the cross-repo edge on real data; `check` does, and M9 proves it.
- `check`: **rc=0, no errors.** With M9 applied to the same real data: rc=1,
  `tasks: nixos-agent-env/PB1 dependsOn PB0: unknown key`. With M2 applied: rc=0 (PB1 is
  `ran`, so the real tree cannot see that mutation — the suite does).
- `write-board` on the clone: block is `B1 G11b OG1b RT5 (…backup-audit-paths.md
  …seat-routing.md …session-context.md)` as committed; H1 is gone (base had it), and none of
  H2/H2b/H2c/PB0 ever appear. Re-deriving after the commit yields `B1 G12 OG1b RT5` — the
  G8c staleness tax, not a fault.
- Board-vs-graph divergence: on a live-shaped fixture, the full graph reports `PB1 ready`
  while `board_graph` (tree-only by G8c's design, so it cannot see `gaming`) reports
  `PB1 blocked` and the block says `nothing queued`. Today PB1 has landed, so this is
  invisible; the re-plan must decide the story (see MAJOR 1).

## Findings

**MAJOR 1 — the resolved cross-repo edge never reaches the scheduler; `ready` and "nothing
queued" are true at the same time.** `derive_status` unions `extra_landed` into its
satisfied set, but `waves` recomputes satisfaction from scratch:

```python
landed = {chain_root(t["key"]) for t in repo_graph["tasks"] if t["state"] == "landed"}
deps   = {k: {chain_root(d) for d in t["depends_on"] if chain_root(d) not in landed} ...}
```

The cross-repo target is not a task of this repo at all (`own_plan_tasks` removed it), so it
is neither in `landed` nor a Kahn node, and the dependent never enters `done`. Measured on
the live-shaped fixture with `gaming`'s real log carrying PB0's subject:

```
PB1 state: [('PB1', 'ready', '')]
waves(gn): []          waves(gn, plan="op.md"): []
open_tasks: ['PB1']    factory_args keys: ['PB1']
BRIEF: **Next wave** — none
board block: **Queued (…).** nothing queued
```

Three of the four dispatch surfaces — `waves`, `seat_groups` (a wave's input), the brief's
`**Next wave**` line and the queue block — still drop the task; only `--factory-args`
(which reads `open_tasks`) sees it. G11 was rejected because the dependent "stays `blocked`
and drops out of every wave, the seat groups, `--factory-args` and the queue block"; that
rejection's fix list said in terms "`waves` must schedule the dependent once the edge
resolves". The state half landed; the scheduling half did not, and the two halves now
contradict each other on the same graph — an inconsistency this commit introduces (before
it, `blocked` + empty wave were at least consistent). It is untested: no assertion anywhere
puts `AA1` or `PB1` in a wave, so nothing would catch a regression. The commit body's
"never permanently blocked while that repo has it landed" and the NOTES' "PB1->PB0 ready
once gaming lands PB0" both read as *dispatchable*, which is false.

**MINOR 2 — a `**repo:**` value `repos.toml` does not configure is a silent black hole.**
`**repo:** dsh-harnes` removes the task from its own repo (`own_plan_tasks`) and no
configured repo claims it, so it appears in no graph, no brief and no board; its dependent is
`blocked | T5` forever and `check` is clean. G11's rejection asked for a rule refusing such a
value; the plan's "rule, exactly" did not carry it, so this is a plan gap, not an
implementation fault — but it reproduces the exact failure mode G11 was rejected for, on a
one-character typo.

**MINOR 3 — the row key for a cross-repo withdrawal is still undocumented.** A withdrawal for
PB0 must be `repo = "gaming"` (the attributed repo) with `plan = "2026-09-05-operator-items.md"`
(the file that holds the section); `repo = "nixos-agent-env"` is refused as an unknown key. The
plan states this; `docs/ledger/task-status.toml`'s single header line does not, and it is the
file an operator will read. G11's MINOR 8, still open.

**MINOR 4 — `defined_roots` was kept, not removed.** The plan's Step 1(g) said to delete it;
`scan_repo` still returns it and `check` reads it. This is the right deviation — it is now the
per-repo resolvable set and M9 proves it load-bearing on both the suite and the real tree — but
the name still says "roots defined here" while its job is "keys this repo may depend on", and
it remains an unpinned key in `scan_repo`'s public return shape that G1 fixed. Rename it
(`resolvable_roots`) and pin it.

**MINOR 5 — the `conflicts(g) == []` assertion in `test_task_status_withdrawn_and_unknown_key`
is vacuous.** Its two tasks share one plan (`p.md`), and `conflicts` skips same-plan pairs, so
the assertion holds for every possible state. Mutation M6 (make `conflicts` iterate all tasks,
bypassing `open_tasks`) survives 81/81. The behaviour is correct — I verified it with a
two-plan fixture where the withdrawn T1 and T4 share `a.py` and are correctly not reported —
but the "never in conflicts" clause has no test. Give the fixture a second plan.

**MINOR 6 — one `git log` per redirected root per repo.** `landed_subjects(tgt["path"])` is
called inside the resolution loop, so each configured repo's scan spawns one `git log` per
redirected chain root it defines (five today, five repos). Cache the per-repo subject sets.

**MINOR 7 — a chain split across repos takes the first member's `repo`.**
`defined.setdefault(root, t["repo"])` reads the first task in file order, and `own_plan_tasks`
filters per member, so `### PB0 (repo gaming)` + `### PB0b (no repo)` puts PB0 under `gaming`
and PB0b under `nixos-agent-env` — one chain, two graphs (verified). No crash and no wrong
state, but the spec should say whether a chain may be split or whether the root's `repo` binds
every member.

### Both `docs/ledger/task-status.toml` contents, for the integrator

Both tasks create this path; **OG1b has not committed** (its workspace head is `d664bf3`,
the file is staged as `A` in a dirty tree), so the integrator will meet a create/create
conflict. Content as of this review:

**G11b (committed, `f10636c`) — 71 bytes, mode `100644`, trailing newline present:**

```toml
# [[task]] repo, plan, key, status = withdrawn | parked, note, decided
```

**OG1b (staged, uncommitted) — 796 bytes, mode `100600`, NO trailing newline:**

```toml
# Withdrawn or parked typed tasks (plan 2026-09-05-seat-routing.md, OG1).
# Empty today: this file is the *intended* place to withdraw a typed task —
# the orchestrator guard makes `### KEY (kind, size)` plan headings
# append-only, so a task that is no longer wanted is withdrawn with a status
# row here instead of deleting or editing its heading. The derived task graph
# learns to read it in a follow-up (OG2): a task with a `withdrawn` row is
# never scheduled, and `parked` rows are shown in the brief once. Until OG2
# lands, this file is documentation of intent.

# [[task]]
# repo = "<repos.toml name>"
# plan = "<plan file name under docs/superpowers/plans>"
# key = "<task key from the heading, e.g. OG1>"
# status = "withdrawn" | "parked"
# note = "<why>"
# decided = "<YYYY-MM-DD>"
```

Recommendation: take **OG1b's** header (it documents all six row keys and is what MINOR 3
asks for), add the attributed-repo sentence, fix the mode to `0644` and add the trailing
newline. Both parse; both are comment-only, so no rows are lost either way. G11b's file is
the one that already satisfies the plan's "must parse and end with a newline".

### The design change for the re-plan (rule A1)

1. **Publish the resolution, and make `waves` consume it.** `scan_repo` returns the set it
   already computes — `"resolved_elsewhere": sorted(extra_landed)` — and `waves` unions it
   into its `landed` set on both the unfiltered and the `plan=`-filtered path. Equivalently
   (and more robustly): `waves` should drop any dependency whose chain root is not a task of
   this repo *and* whose dependent `derive_status` already called `ready`, so the scheduler
   can never disagree with the state.
   Tests, red first: `waves(A) == [["AA1"]]` on the clause-(a) fixture with B's landing and
   `waves(A) == []` without it; `waves(gn) == [["PB1"]]` and `**Next wave** — nixos-agent-env:
   PB1` on the live-shaped fixture; one mutation dropping the union.
2. **Decide the board's story, in the spec, before coding.** `board_graph` is tree-only by
   G8c's decision, so it cannot see `gaming` and will keep calling PB1 `blocked` while the
   full graph calls it `ready`. Either the queue block deliberately omits cross-repo-dependent
   tasks (say so in `docs/OPERATIONS.md`'s block header and pin it with a test), or the block
   is derived from a different graph — but that reopens G8c. Pick one; do not leave the two
   graphs silently disagreeing.
3. **Refuse an unconfigured `**repo:**` value** in `check` (MINOR 2), so a typo is an error
   rather than a disappearance.
4. Fold in MINOR 3 (header sentence), MINOR 4 (rename + pin), MINOR 5 (two-plan conflicts
   fixture). MINOR 6 and MINOR 7 are optional.

Everything else in this commit is sound and should be preserved verbatim — cherry-pick
`task/G11b` and add the above.

## Deviations

- **Recorded, allowed by the plan (Step 0):** `docs/ledger/task-status.toml` created here
  with a one-line header, since OG1 has not landed. Disclosed in the commit body. It parses
  and ends with a newline as required. Overlaps OG1b — see Findings.
- **Recorded, disclosed, accepted:** `defined_roots` was kept rather than removed (plan Step
  1(g)) and repurposed as the per-repo resolvable set. NOTES say "G11's dead global
  `defined_roots` union removed, per-repo resolvable set now load-bearing (catches M7b)" —
  accurate; M9 confirms it is load-bearing on the suite and the real tree. The right call:
  deleting it would have broken the attribution rule.
- **Recorded, not allowed:** the resolved cross-repo edge is not consumed by `waves`,
  `seat_groups`, the brief's `**Next wave**` line or the queue block. Not disclosed in NOTES
  or the commit body, both of which imply the opposite. Rejected above; the plan's "rule,
  exactly" omitted the clause, so the fix belongs in a re-plan rather than another blind
  fix round.
- **Not a G11b fault, for the integrator:** base `d664bf3` is an ancestor of live main
  (`4180dca`), which has since landed PB1. Nothing in this commit collides with it; the
  regenerated queue block will need one more `write-board` after the merge, as always.
- **Gate-brief expectation adjusted:** the brief predicted PB1 `landed` on real data. It is
  `ran` because the scratch `repos.toml` points `nixos-agent-env` at the clone (base
  `d664bf3`), whose log predates PB1's landing commit. Live main does carry that subject —
  confirmed by exact-match `git log` grep. Not a defect.
