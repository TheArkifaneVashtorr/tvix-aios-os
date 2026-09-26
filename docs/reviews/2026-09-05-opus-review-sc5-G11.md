---
reviewer: opus
majors: 3
minors: 6
---
# Opus gate — seat run sc5, task G11 — REJECTED

Task: `G11` (code, S) — a task names the repo it runs in; withdrawn tasks come from
`task-status.toml`. Plan `docs/superpowers/plans/2026-09-05-session-context.md`.
Workspace `/home/dalhaka/factory/ws/sc5/G11`, branch `task/G11`, head `2dab8f8fbf5b`,
base `9804e95`. Reviewed in a throwaway clone; the workspace was not touched.

## Summary

The declared body of G11 is delivered and well tested: `**repo:**` parses, `scan_repo`
attributes a task to the repo it names (landed by that repo's git log), the tree-only
`board_graph` drops foreign tasks so the board block loses H1/H2b/PB0, and
`task-status.toml` rows withdraw or park a key without touching plan text. Three new
tests, all red on base for the stated reasons; twelve mutants killed, including six
re-runs from the G9 and G8c gates. `evidence-unit`, `lint` and the pre-commit hook are
green (one regenerate-and-re-add, per G8c's rule). One commit on base, subject
byte-identical to the plan's, both trailers present, plan-file diffs are four added
`**repo:**` lines and nothing else.

The undeclared second item — the cross-repo `dependsOn` resolution the NOTES flag —
fails on all three counts the gate asks for. It is **untested** (reverting it leaves all
75 tests green while breaking the real tree), it is **unsound** (a dependency on a task
attributed elsewhere is never satisfied — not "satisfied when that repo has it landed"),
and the part that was actually implemented — a single global key namespace across every
repo — was **not disclosed**. Three MAJORs; fix round `G11b`.

## Cross-repo dependsOn (what was implemented; sound? disclosed?)

**What the code does.** Two changes, neither in the commit body:

1. `scan_repo` returns a new graph key `defined_roots` — the chain roots of *every* typed
   key in that repo's own plans, including keys whose `**repo:**` redirects them
   elsewhere.
2. `check` no longer scopes the unknown-key rule to one repo. It builds one set before
   the per-repo loop:

   ```python
   defined = set()
   for repo in graph["repos"]:
       defined.update(repo.get("defined_roots", ()))
       defined.update(chain_root(t["key"]) for t in repo["tasks"])
   ```

   and every repo's `dependsOn` is then tested against that global set.

Nothing else changed. `derive_status` rule 5, `waves` and `open_tasks` are untouched.

**Is it sound? No — on all three of the gate's clauses.**

*(a) "satisfied when THAT repo's graph has it landed" — not implemented.* `landed_keys`
is still built only from the scanning repo's own retained tasks, so a redirected
dependency can never enter it. Demonstrated with the shipped module on a two-repo
fixture: `T9` is declared in repo-a's plan with `**repo:** repo-b`, and repo-b's git log
carries T9's subject:

```
repo-a [('AA1', 'blocked', 'T9')]     waves: []
repo-b [('ZZ9', 'ready', ''), ('T9', 'landed', 'x: t9 (test: unit)')]     waves: [['ZZ9']]
```

`AA1` is blocked forever and appears in **no wave at all** — `waves` treats `T9` as a
predecessor node that never enters `done`, so the task is invisible to the seat groups,
to `waves --factory-args` and to the board's queue block. The same holds on real data:
`PB1` is `blocked | PB0` while `PB0` is `landed` under `gaming`. G11 fixed PB0's *state*
and left the *edge* dangling; `check` was widened so it would stop saying so.

*(b) "never silently satisfied" — passes.* Nothing is ever marked satisfied; the failure
mode is a permanent false block, not a false green.

*(c) "`check` must still refuse a truly unknown key" — partially.* A key defined nowhere
is still refused. But the global set also accepts a `dependsOn` naming a key that exists
only in a **different** repo's own plans and was never redirected here:

```
check(A dependsOn ZZ9 which lives only in repo-b): []
check(truly unknown QQ7):  ['tasks: repo-a/AA1 dependsOn QQ7: unknown key']
```

G4 pins this rule as "a `depends_on` key whose chain root is not a task in any typed plan
of **the same repo**". Five repos now share one key namespace; a typo that collides with
any key in `media`, `gaming`, `nixos-skill` or `dsh-harness` passes silently.

**Was it disclosed?** Partially, and not the part that matters. FACTORY-NOTES says
"cross-repo dependsOn resolution added to keep lint green (PB1→PB0)". The commit body
does not mention it at all. Neither says the guard was made global rather than per-repo,
and neither says the dependency remains permanently unsatisfiable. A reader of the NOTES
would reasonably conclude the edge now resolves. It does not.

**Untested.** No test covers any of it. Mutant **M7b** — restoring G4's per-repo scoping,
the exact rule this change overrides — leaves **75 / 75 tests green** and only fails on
real data (`tasks: nixos-agent-env/PB1 dependsOn PB0: unknown key`). A second mutant,
deleting the `defined_roots` line alone, is also green on both the suite and the real
tree: the global union over other repos' retained tasks already covers PB0, so
`defined_roots` is dead weight for every configured-repo case.

## Checks

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | pass |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | pass |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 → regenerate → `git add` → exit 0 |
| pytest | `pytest tests/evidence -q -p no:cacheprovider` | 75 passed |

The hook's first run printed G8c's message (`docs/OPERATIONS.md queue block was stale and
has been regenerated — git add docs/OPERATIONS.md and commit again`) and rewrote the block
to drop `G11` — expected: in the clone G11's own subject is in `git log`, so it is landed
and leaves the queue. `git add` + re-run was green, `render.test.mjs` included. One
regenerate-and-re-add, exactly the allowance.

Commit hygiene: one commit on `9804e95`; touched files are `pkgs/evidence/tasks.py`,
`tests/evidence/test_tasks.py`, `docs/ledger/task-status.toml`, the two plan files and
`docs/OPERATIONS.md` — a subset of G11's `touches`. The two plan diffs are four added
`**repo:**` lines and nothing else; no heading is touched. `docs/OPERATIONS.md` changes
only the generated block line. Subject byte-identical to the plan's; `Co-Authored-By:
Claude Fable 5.1` and `Generated-By: dsh …` present.

## Red before green

Base `9804e95`'s `tasks.py` restored under HEAD's tests: `3 failed, 37 passed`.

| test | failure on base |
|---|---|
| `test_repo_field_attributes_cross_repo_task` | `TypeError: scan_repo() got an unexpected keyword argument 'repos'` |
| `test_board_graph_excludes_cross_repo_task` | `AssertionError: 'T1' is contained here: brief).** T1 TA (board.md)` — semantic, not a signature |
| `test_task_status_withdrawn_and_unknown_key` | `TypeError: scan_repo() got an unexpected keyword argument 'task_status'` |

`tasks.py` restored; the clone is pristine at `2dab8f8`.

Two of the three are signature failures rather than behavioural ones — acceptable here
because the interfaces are new, but the board_graph test is the only one that would have
survived a signature-compatible base.

## Mutation table

Applied to the delivered tree, full `tests/evidence` run, then reverted.

| # | mutation | result |
|---|---|---|
| M1 | `FIELD_RE` drops `repo` (field ignored) | **killed** — `test_repo_field_attributes_cross_repo_task`, `test_board_graph_excludes_cross_repo_task` |
| M2 | `own_plan_tasks` keeps foreign-repo tasks | **killed** — same two |
| M3 | withdrawn/parked override removed | **killed** — `test_task_status_withdrawn_and_unknown_key` |
| M4 | `open_tasks` schedules withdrawn/parked (waves + conflicts) | **killed** — same |
| M5 | `check` accepts a task-status row naming an unknown key | **killed** — same |
| M6 | rule 5 treats every dependency as satisfied (`missing = []`) | **killed** — `test_derive_status_precedence`, `test_scan_repo_and_build` |
| M7 | `defined_roots` line dropped from `check` | **SURVIVED** — 75 passed; real-data `check` also rc=0 (the global union already covers PB0) |
| M7b | `check` scoped per repo, i.e. G4's pinned rule | **SURVIVED** — 75 passed; real-data `check` rc=1: `tasks: nixos-agent-env/PB1 dependsOn PB0: unknown key` |
| M8 | brief lists a withdrawn task twice | **killed** — `test_task_status_withdrawn_and_unknown_key` (`md.count(...) == 1`) |
| G9-a | chain state = newest review across the chain, not the last member's | **killed** — `test_chain_last_member_result_beats_root_review` |
| G9-b | `conflicts` drops the different-plan condition | **killed** — `test_conflicts_same_plan_not_reported` |
| G9-c | `waves --factory-args` without `--plan` no longer exits 2 | **killed** — `test_main_waves_factory_args_requires_plan` |
| G9-d | `legacy open` counts all legacy rows | **killed** — `test_brief_legacy_open_counts_only_open` |
| G9-f | repo map counts walked files, not `git ls-files` | **killed** — `test_count_files_git_tracked_and_ruff_cache_fallback` |
| G8c-g | `board_graph` reads `repos.toml` | **killed** — `test_write_board_queue_ignores_run_results`, `test_board_graph_derives_this_tree_ignoring_repos_toml` |
| G8c-h | `check --board` compares against the live graph (runs/store) | **killed** — `test_main_check_board_stale_current_and_runs_free` |

Fourteen killed, two survivors — both on the undeclared cross-repo `dependsOn` semantic.
All six re-run mutants from the G9 and G8c gates are still dead.

## Real data

`repos.toml` maps `nixos-agent-env` to `~/nixos-agent-env` by absolute path, so running
the clone's `tasks.py` with `--root /home/dalhaka/nixos-agent-env` reads **live main's**
plans, which do not yet carry the new `**repo:**` lines — H1/H2/H2b/PB0 still land under
`nixos-agent-env` there (verified: they do). To exercise the change on real data I built a
scratch root whose `repos.toml` points `nixos-agent-env` at the clone and every sibling at
its real path; everything read-only.

```
| repo | landed | approved | rejected | ran | recorded | ready | blocked | legacy open | untracked |
|---|---|---|---|---|---|---|---|---|---|
| nixos-agent-env | 61 | 0 | 0 | 2 | 0 | 2 | 2 | 1 | 0 |
| media | 3 | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0 |
| gaming | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nixos-skill | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dsh-harness | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
```

- `dsh-harness`: H1, H2, H2b all `landed`, each by that repo's own commit subject.
- `gaming`: PB0 `landed` (`gaming: nixpkgs → nixos-26.05 head (2026-09-05); flake check
  green; upstream drift recorded (test: flake-check)`).
- `nixos-agent-env`: none of H1/H2/H2b/PB0. Matches the plan's Step 4 expectation, and
  improves on it (the plan predicted PB0 as "ran/approved"; it is landed).
- `check` on that graph: rc=0, no errors.
- The clone's own `write-board` block excludes H1/H2b/H2c/PB0:
  `B1 FD1 G11 OG1 RT4 (…backup-audit-paths.md …factory-dispatch.md …seat-routing.md
  …session-context.md)`. The base block had `B1 FD1 G11 H1 H2b OG1 PB0 RT4`.
- `PB1` is `blocked | PB0` and appears in no wave — see the cross-repo section.
- Base staleness, for the integrator: live main (`79845ed`) has moved past base `9804e95`
  and already carries `**repo:** dsh-harness` on `### H2c`. The two additions do not
  collide, but H2c's field uses a blank line after `**dependsOn:**` where this commit's
  four do not.

## Findings

**MAJOR 1 — the cross-repo `dependsOn` resolution has no test.** Mutant M7b (restore G4's
per-repo scoping) leaves 75/75 green and is caught only by the lint gate on the live tree.
The repo's rule is that a load-bearing test counts only once it has been shown to fail;
here there is no test at all for the one semantic the NOTES call out.

**MAJOR 2 — the semantic is unsound: a cross-repo dependency is never satisfied.** With
the dependency's target landed in the repo it names, the dependent task stays `blocked`
and drops out of every wave, the seat groups, `--factory-args` and the queue block
(demonstrated on a fixture and on `PB1 → PB0`). The gate's contract is that such a
dependency is satisfied when that repo's graph has it landed. Widening `check` removed the
only signal that the edge is dangling without making it resolvable — the graph is now
quieter and no more correct.

**MAJOR 3 — the guard was widened beyond what was disclosed.** `check`'s unknown-key rule
is now one global namespace over all five repos, contradicting G4's pinned "any typed plan
of the same repo". A `dependsOn` naming a key that lives only in another repo's plans is
accepted (demonstrated). Neither the NOTES nor the commit body mention this; only an
in-code comment hints at the intent.

**MINOR 4 — `defined_roots` is dead weight.** Deleting its line in `check` changes nothing
for the suite or the real tree. It adds an unpinned key to `scan_repo`'s public return
shape (G1 fixes that shape) for no observable effect in any configured-repo case.

**MINOR 5 — `STATES` was not extended.** `withdrawn`/`parked` are now possible values of
`task["state"]`, but `STATES` still lists seven. Consequences: such tasks are counted in
no column of the brief's table (the row no longer sums to the repo's task count), and the
CLI's json emits a state outside G1's published tuple — G4's own json test asserts
`state in STATES`, and it happens to sample `tasks[0]`.

**MINOR 6 — a mistyped status is a silent no-op.** `load_task_status` accepts any
`status` string; `scan_repo` acts only on exactly `"withdrawn"`/`"parked"` and `check`
validates only the key. `status = "withdrawnn"` leaves the task scheduled with no
diagnostic — the opposite of the "never silently scheduled" intent.

**MINOR 7 — `board_graph`'s dict has no `"task_status"` key.** `check` reads
`graph.get("task_status", {})`, so the row-validation rule silently does nothing on a
board graph. Harmless today (the CLI's `check` uses the full graph) but it is a
guard that reports clean on a graph it never inspected.

**MINOR 8 — withdrawing a cross-repo task needs an undocumented key.** `defined_rows` is
built from *retained* tasks, so a row for PB0 must be keyed `repo = "gaming"` with
`plan = "2026-09-05-operator-items.md"` — the repo it runs in, not the repo whose plan
file holds the section. Untested and unwritten anywhere; the natural spelling
(`repo = "nixos-agent-env"`) would be refused as an unknown key.

**MINOR 9 — `docs/ledger/task-status.toml` has no trailing newline**, and OG1's `touches`
list the same path. Both tasks create the file; the integrator will meet a
create/create conflict. Content matches OG1's documented header exactly.

### Suggested fix round `G11b`

1. Resolve a cross-repo dependency against the repo it names: build the multi-repo graph
   first, then satisfy `PB1 → PB0` iff `gaming`'s graph has PB0 `landed`; otherwise
   `blocked` with a detail naming the repo (`PB0 in gaming: approved`). Never satisfied by
   default. `waves` must schedule the dependent once the edge resolves.
2. Keep `check`'s unknown-key rule per repo, plus one explicit allowance: a key defined in
   that repo's own plans and redirected by `**repo:**`, or defined in the plans of the
   repo its `**repo:**` names. Add a rule refusing a `**repo:**` value that `repos.toml`
   does not configure.
3. Tests, red first, for: the resolved edge (landed elsewhere → ready), the unresolved
   edge (not landed elsewhere → blocked, named), a key defined only in another repo and
   not redirected → still `unknown key`, and a `**repo:**` naming an unconfigured repo.
4. Extend `STATES` (or document the exclusion) and add a `check` rule for an unrecognised
   `status` value in `task-status.toml`.

## Deviations

- **Recorded, allowed by the plan:** `docs/ledger/task-status.toml` created here with
  OG1's documented header, since OG1 has not landed. Disclosed in NOTES and the commit
  body.
- **Recorded, unallowed:** `check`'s unknown-key rule changed from per-repo to a global
  namespace, and `scan_repo` gained a `defined_roots` return key. Disclosed in NOTES only
  as "cross-repo dependsOn resolution added to keep lint green"; the semantics were not.
  Rejected above.
- **Behaviour the orchestrator should pin in the spec, whatever G11b does:** a
  `dependsOn` naming a task attributed to another repo is satisfied only when that repo's
  graph reports the key `landed`; it is never satisfied by absence, and `check` still
  refuses a key no plan defines. One sentence in
  `docs/superpowers/specs/2026-09-05-session-context-and-task-graph-design.md` §3.
- **Not a G11 fault, worth knowing:** the queue block goes stale by exactly the key that
  just landed, so every commit after one that lands a queued task pays the G8c
  regenerate-and-re-add step. Observed here on G11 itself.
