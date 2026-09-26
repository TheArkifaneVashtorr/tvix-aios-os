---
reviewer: opus
majors: 2
minors: 4
mutants_killed: 18
---
# Opus gate — seat run sc8, task G12b — REJECTED

Task: `G12b` (code, S) — G12 fix round on top of G11r: running is per key and only while the
log is live; imported-task dependencies resolve against the defining repo. Plan
`docs/superpowers/plans/2026-09-05-session-context.md` §`G12b` plus the appended "Note for
G12b"; rejections it answers `docs/reviews/2026-09-05-opus-review-sc5-G12.md` and the latent
MAJOR 2 of `…-sc7-G11r.md`. Workspace `/home/dalhaka/factory/ws/sc8/G12b`, branch
`task/G12b`, head `9950f10b56b3`, base `1a5b525`. Reviewed in a throwaway clone; the
implementer's workspace was read only and is still clean at `9950f10`.

## Summary

Every one of the nine contract points is delivered, and I verified each with my own fixtures
on **real `git init` repositories with real `git log`** — never the implementer's `fake_git`:
31 of 31 hand-built probes pass. The G12 defect is dead per key and across run dirs; the
stale-log bound is real (`--stale-after`, `TASKS_STALE_AFTER`, default 7200) and it works on
live data — the brief named exactly `OG1r2` while `pgrep -af factory-task` showed exactly
`og4 OG1r2`, and when that seat finished mid-review the column flipped `1 → 0` and the key
became `ran`. Parked logs are not read. Eighteen mutations applied, **eighteen killed**,
including seven re-runs of G12's set and all three of G12's surviving mutants (the vacuous
`conflicts` assertion, the empty `--next`, the chain rule). `evidence-unit` (102), `lint` and
the hook are green; one commit, three files, subject byte-identical, both trailers.

It is rejected on **one regression this commit introduces**, in the seam that has now been
rejected three times. The new imported-task rule feeds keys from **another repo's namespace**
into the flat, unqualified `extra_landed` set (`tasks.py:493-508`), which `derive_status`
(`:363`) and `waves` (`:647`) both read as "landed". Consequence, proved on real repos: repo A
lands its own `L1` and defines `X1 (**repo:** repo-b, dependsOn L1)`; repo B has its **own,
unrelated** `L1` (not landed) and `BL (dependsOn L1)`. B's `BL` reads `ready` and
`waves(B) == [['BL','L1','X1']]` — the dependent is put in the **same wave as its own
unlanded dependency**. On base `1a5b525` the same fixture gives `BL blocked` and
`[['L1'], ['BL','X1']]`. That is a scheduling fault worse than the failure modes G11, G11b and
G12 were each rejected for ("never satisfied by mere existence"), it contradicts G11b's rule
clause "No global namespace", it is unpinned, and it is not disclosed in FACTORY-NOTES or the
commit body. It is latent on today's tree only because no key name is currently duplicated
across the five repos — nothing enforces that, and `check`'s duplicate rule is per-repo.

The correct fix is a design decision the plan does not state (how the satisfied set is keyed),
so this is a second rejection on G12's lineage → re-plan as **G12r** under rule A1. The design
change is named in Findings.

## Contract

Every row below is my own fixture (`git init`, real commits, real `git log`, real workspace
clones under `<root>/ws/<run>/<key>`), run against the delivered `pkgs/evidence/tasks.py`.
Script: `probe.py`, 31 assertions, all pass.

| # | contract point | my evidence | verdict |
|---|---|---|---|
| a | `r1/K1.log` (old run) + `r2/K1.result` → `ran` | `{'status': 'done', 'run': 'r2', 'file': …}` — per-key newest run wins. Reversed (r1 dir newer, log fresh) → `{'status': 'running', 'run': 'r1'}`, so the ordering is real, not a constant | **pass** |
| b | fresh `r1/K1.log`, no result → `running` | `read_results` → `running/r1`; graph state `running`, detail `K1 run=r1`; brief header carries `\| running \|` and the line `**Running:** nixos-agent-env/K1` | **pass** |
| c | log older than `--stale-after` → NOT running | default 7200: `read_results` → `{}`; same log with `stale_after=100000` → `running`; at graph level the key reads **`ready`** and `waves → [['K1']]` (schedulable again). CLI: `TASKS_STALE_AFTER=100000` → `running`, `=10` → `ready`, `--stale-after 100000` → `running`; `DEFAULT_STALE_AFTER == 7200` | **pass** |
| d | two-plan fixture, running task's touches overlap → absent from `conflicts` | `K1` (p.md, running, `a.py`) vs `T2` (q.md, ready, `a.py`): `conflicts(g) == []`, `waves(g) == [['T2']]`. **Non-vacuous**: with the log removed the same fixture reports the pair `K1–T2 on a.py`. Mutation M3 (schedule/conflict running) kills it | **pass** |
| e | root REJECTED review + fix-round member with a fresh log → root `running` | `G1` REJECTED by `ev1`, `G1b.log` fresh → `G1` state `running`, detail `G1b run=r1`, and the brief prints `**Rejected, fix round owed:** none`. Control: an APPROVED review on the *last* member (`G1b`) still outranks running → `approved`. Mutations M4 and M5 both kill it | **pass** |
| f | `--next` with nothing schedulable prints zero bytes | real subprocess, `od -c` on stdout → `0000000` (empty), rc 0. Mutation M6 (`print(lines[0] if lines else "")`) kills it | **pass** |
| g | a dependency `running` in its attributed repo is NOT satisfied | `PB0 (**repo:** gaming)` with `gaming/r1/PB0.log` live: gaming reports `PB0 running`; nixos-agent-env reports `PB1 blocked \| PB0`, `waves == []`, `resolved_elsewhere == []`. Control: commit PB0's subject in gaming → `PB1 ready`, `waves == [['PB1']]`. Mutation M10 kills it | **pass** |
| h | imported `X1 (repo-b) dependsOn L1`, `L1` landed in defining repo A → `X1 ready`, `check` clean | repo-b's tasks `{ZB, X1}`; `X1` **ready**; `check(...) == []`; `X1` enters a wave. Mirror (L1 not landed) → `X1 blocked \| L1`, `check` still clean. Namespace still per-defining-repo: `X1 dependsOn ZB` (a repo-b-local key) → `tasks: repo-b/X1 dependsOn ZB: unknown key`; `dependsOn ZZ9` (no repo defines it) → unknown key. Mutations M7 (resolve against B only) and M8 (`check` uses the running repo) both kill it | **pass** |
| i | `deferred-to-brief` ∈ `STATES` | `STATES = (landed, approved, rejected, ran, running, recorded, ready, blocked, deferred-to-brief, withdrawn, parked)`; `board_graph` still defers the cross-repo dependent; the brief gains a `deferred-to-brief` column and **counts** it (`1`, header and row column counts equal) instead of silently dropping it — G11r's MINOR 4 closed. Mutation M9 kills it | **pass** |

Commit hygiene: **one** commit on `1a5b525` (`git rev-list --count` → 1). Files are exactly
G12b's `touches`: `pkgs/evidence/tasks.py` (+277/-…), `tests/evidence/test_tasks.py` (+436),
`docs/OPERATIONS.md` (+1/-1, generated block only) — nothing else. Subject `cmp`-identical to
the plan's line 1666 (156 bytes both sides, `IDENTICAL`). `Generated-By: dsh 0.1.2-rc.1 /
deepseek/deepseek-v4-pro-0813 (seat headless, factory run sc8)` and `Co-Authored-By: Claude
Fable 5.1 <noreply@anthropic.com>` both present, in order. Stdlib only (the one new import is
`time`); no `sudo`, `nixos-rebuild`, `systemctl`, no bypass flag, no new `2>/dev/null`, no
network, no secrets.

## Checks

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | **pass** — 102 passed |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link` | **pass** — treefmt 88 files 0 changed; statix/deadnix/ruff clean |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 (`docs/OPERATIONS.md queue block was stale and has been regenerated`) → `git add` → exit 0, `All checks passed`, `render.test.mjs: all assertions passed`. **One** regenerate-and-re-add, exactly the allowance |
| pytest | `pytest tests/evidence -q -p no:cacheprovider` | 102 passed |
| downstream | `evidence.py tasks … brief` (the wrapper the hook uses) | renders, 14-column table |

The hook's single regenerate drops `G12b` from the queue block (its own subject is now in
`git log`) — G8c's known tax, same as on G11r and G12. Note that nothing in the gate catches
the defect below: `check` is rc 0 on the live tree, and no test covers a cross-repo key
collision.

## Red before green

**Against base `1a5b525` (G11r + the newline fix) with HEAD's tests: 13 failed, 89 passed.**
All behavioural or signature failures, none accidental.

| test | failure on base |
|---|---|
| `test_read_results_detects_running_log` | `KeyError: ('nixos-agent-env','K1')` — no running derivation |
| `test_running_task_not_scheduled_and_counted` | `assert 'ready' == 'running'` |
| `test_derive_status_running_between_review_and_result` | `TypeError: derive_status() got an unexpected keyword argument 'running'` |
| `test_wave_lines_one_per_wave`, `test_wave_structure_json_shape` | `AttributeError` |
| `test_main_waves_next_json_and_default`, `…_nothing_schedulable_prints_zero_bytes` | `SystemExit: 2` (`--next` unrecognised) |
| `test_running_task_absent_from_conflicts_across_plans` | `assert 'ready' == 'running'` |
| `test_chain_running_member_outranks_root_review` | `assert 'rejected' == 'running'` |
| `test_imported_task_dep_resolves_against_defining_repo` | `assert 'blocked' == 'ready'` |
| `test_imported_task_dep_blocked_when_foreign_local_not_landed` | `check` emits the spurious `dependsOn L1: unknown key` (G11r MAJOR 2) |
| `test_states_include_deferred_to_brief`, `test_states_include_withdrawn_and_parked_in_brief` | `deferred-to-brief` absent from `STATES` / the brief header |

Base has no `running` at all, so the two headline **fix** tests are not red there. I ran them
against **G12's rejected `tasks.py`** (`9df4ef3` from `/home/dalhaka/factory/ws/sc5/G12`)
instead — the code they exist to correct — and they are red for exactly the rejected reasons:

```
FAILED test_read_results_newer_result_beats_older_log   (r1's log beat r2's result)
FAILED test_read_results_stale_log_is_not_running
FAILED test_stale_log_key_reads_ready                   assert 'running' == 'ready'
```

`tasks.py` restored both times; SHA-256 `bd71b4f290ea43d2…` and `git status --porcelain` empty
after each.

## Mutation table

Each applied alone to the delivered tree, full `tests/evidence` run, then reverted; the file
was confirmed SHA-256 identical (`bd71b4f290ea43d2…`) and the tree clean at the end.

| # | mutation | killed by |
|---|---|---|
| M1 | **G12's defect** — the log's recency is scoped to its own run dir again (log always outranks a result from another run) | `…newer_result_beats_older_log`, `…running_log_with_result_is_ran` |
| M2 | the staleness bound dropped (`elif True`) — any log is live | `…stale_log_is_not_running`, `…stale_log_key_reads_ready` |
| M3 | **G12's surviving M3** — `open_tasks` includes `running` (scheduled and conflicting again) | `…not_scheduled_and_counted`, `…absent_from_conflicts_across_plans` |
| M4 | rule 2.5 deleted — `running` never derived in `derive_status` | 4 tests incl. `…chain_running_member_outranks_root_review` |
| M5 | **G12's surviving M12** — running keys dropped from `_chain_members` (the root falls back to its own review) | `…chain_running_member_outranks_root_review` |
| M6 | **G12's surviving M6** — `--next` prints a blank line when nothing is schedulable | `…nothing_schedulable_prints_zero_bytes` |
| M7 | the imported-task resolution loop removed (resolve against B only) | `…imported_task_dep_resolves_against_defining_repo` |
| M8 | `check` resolves an imported task against the repo it RUNS in | both imported-task tests |
| M9 | `deferred-to-brief` removed from `STATES` | `…states_include_deferred_to_brief`, `…withdrawn_and_parked_in_brief` |
| M10 | a cross-repo edge is satisfied by mere existence (no `git log` match) | `…cross_repo_dep_resolves_via_attributed_repo`, `…running_elsewhere_dependency_not_satisfied` |
| R1 | *(G12 re-run)* the `*.log` scan removed | 4 tests |
| R2 | *(G12 re-run)* `--next` prints every wave | `…waves_next_json_and_default` |
| R3 | *(G12 re-run)* `--json` flattens waves → groups | `…waves_next_json_and_default` |
| R4 | *(G12 re-run)* brief header loses the `running` column | `…not_scheduled_and_counted` |
| R5 | *(G12 re-run)* log attribution ignored (workspace need not exist) | `…ignores_running_log_without_workspace` |
| R6 | *(G12 re-run)* the `**Running:**` line dropped | `…not_scheduled_and_counted` |
| R7 | *(G12 re-run)* default `waves` back to one group per line | `…waves_next_json_and_default` |
| R8 | same-run tie-break inverted (`>=`): a log beats the result beside it | `…running_log_with_result_is_ran` |

**18 applied, 18 killed.** Seven are G12 re-runs (more than the six asked for) and all three of
G12's outstanding survivors (M3, M6, M12) are now dead. The defect in Findings is **not** in
this table because no test in the suite can see it — I proved it by direct A/B against base
instead.

## Real data

Read-only against the live `~/factory/runs` and the repos in `docs/ledger/repos.toml`;
`--root <clone> --runs-dir /home/dalhaka/factory/runs`.

At 17:58 CDT, with exactly one seat alive (`pgrep -af factory-task` → `263356 … factory-task
og4 … OG1r2`):

```
| repo | landed | approved | rejected | ran | running | recorded | ready | blocked | deferred-to-brief | withdrawn | parked | legacy open | untracked |
| nixos-agent-env | 67 | 0 | 4 | 9 | 1 | 0 | 4 | 5 | 0 | 0 | 0 | 1 | 0 |
**Next wave** — nixos-agent-env: B1 CR3 SB1 SB2
**Running:** nixos-agent-env/OG1r2 (OG1r2 run=og4)
```

**One key running, and it is the one process on the host.** G12's eleven corpses are gone:
every other fresh log (`sb2/SB3b`, `sc7/G11r`, `og3/OG1r`, `pwk2/PW1kimi`, `cr2/CR1`,
`sc8/G12b`, `rt7/RT5r`, `pwg2/PW1glm`) has a `.result` beside it and reads `ran`. At 18:02
`OG1r2` finished and wrote its result; the very next `brief` read `running 0`, `ran 10`,
`**Running:** none` — the liveness rule tracking the process table in real time.

The glob is `<KEY>.log` exactly, verified two ways: the live run dirs hold
`sb1/SB3b.log.killed-by-reboot-2026-09-05`, `sc6/G11r.log.killed-by-reboot-2026-09-05`,
`cr1/CR1.log.misfire` and `rt6/RT5r.log.truncated-response`, and none of those keys reads
`running`; and on a purpose-built run dir containing **only**
`K1.log.killed-by-reboot-1757` + `K1.log.misfire` + `K1.truncated-response` (with a valid
workspace clone), `read_results` returns `{}`. The run dirs' `wave-group-1.log` files are also
ignored — there is no `ws/<run>/wave-group-1` clone.

`--next` outputs, verbatim:

```
$ tasks.py … waves --repo nixos-agent-env --plan 2026-09-05-plan-writing-comparison.md --next
                      (zero bytes — od -c → 0000000)
$ … --plan 2026-09-05-plan-writing-comparison.md            (default)
                      (no output)
$ … --plan 2026-09-05-plan-writing-comparison.md --json
[]
$ … waves --repo nixos-agent-env --next                     (whole repo)
"B1 SB1" "CR3" "SB2"
```

PW1pro / PW1glm / PW1kimi all read `ran … status=done` (done-ungated), so nothing in that plan
is schedulable and `--next` is correctly silent. `check` on live data: **rc 0, no output**.

One live behaviour change beyond the contract, from the defect below: `dsh-harness`'s
published `resolved_elsewhere` moves from `[]` (base) to `['H1','H2']` — roots attributed to
`dsh-harness` *itself*.

## Findings

**MAJOR 1 (reject) — `pkgs/evidence/tasks.py:493-508`: the imported-task rule injects another
repo's namespace into the flat `extra_landed` set, so a same-named local key is falsely
satisfied and its dependent is scheduled alongside it.** The new loop resolves an imported
task's `depends_on` against the defining repo and then does `extra_landed.add(droot)` — a bare
chain root, no repo. `derive_status` (`:363`) unions that into `landed_keys`, `waves` (`:647`)
unions it into `landed`, and both are keyed by root alone. Proved on real `git init` repos:

```
repo-a: L1 (A's own, LANDED in A);  X1 (**repo:** repo-b, dependsOn L1)
repo-b: L1 (B's own, DIFFERENT task, NOT landed);  BL (dependsOn L1)

HEAD        BL=ready    resolved_elsewhere=['L1']  waves=[['BL', 'L1', 'X1']]
BASE 1a5b525 BL=blocked  resolved_elsewhere=[]      waves=[['L1'], ['BL', 'X1']]
```

`BL` depends on a key attributed to `repo-b` that `repo-b` has **not** landed, yet it reads
`ready` and enters the **same wave as that dependency** — the dispatcher would launch a task
and its unfinished prerequisite together. This is the plan lineage's own rule broken in terms:
G11b's "Satisfied when the dependency's chain root is `landed` in the repo it is ATTRIBUTED
to" and "No global namespace". It is **this commit's regression** (base is correct, shown
above), it is unpinned, and it is undisclosed. Remove the imported task and `BL` goes back to
`blocked`, so the imported rule is the sole cause. It is latent on today's tree only because
no key is currently defined in two repos (`keys in >1 repo graph: {}`) — nothing enforces
that: `check`'s duplicate-definition rule is per-repo, the five repos' keys are short
(`H1`, `W3`, `PB0`, `B1`), and the collision surface today is exactly the H-namespace that
`nixos-agent-env` imports into `dsh-harness`. The related contract drift is visible live:
`dsh-harness.resolved_elsewhere == ['H1','H2']`, though G11r defines that field as roots
"attributed to another configured repo".

**The design change for the re-plan (rule A1 → G12r):** *the satisfied-dependency set must be
keyed by `(repo, chain_root)`, never by a bare root.* Concretely — resolve each task's
`depends_on` in the namespace of the repo that **defines** that task (local task → this repo;
imported task → its defining repo), decide "landed" in the repo the dependency is
**attributed** to, and hand `derive_status`/`waves` a per-repo satisfied set; `extra_landed`
must never receive a root that this repo's own plans define as a local task, and
`resolved_elsewhere` must keep its stated meaning (roots attributed elsewhere and landed
there). Required test, red first: the fixture above → `X1 ready`, `BL blocked | L1`,
`waves(repo-b) == [['L1','X1'], ['BL']]`, `check` clean; mutation: fold the imported
resolution back into one flat set → `BL` becomes `ready` and shares a wave with `L1` → the
test fails. Everything else in G12b is correct and should be preserved verbatim.

**MINOR 2 — `tasks.py:270-280`: a stale log in the *newest* run dir discards a genuine
`.result` from an older run entirely.** Probe: `r1/K1.result status=done` (older dir) +
`r2/K1.log` back-dated past `stale_after` (newer dir) → `read_results` returns `{}`, so the key
loses its `ran` evidence and falls to `ready` rather than to rule 3. The section says the stale
case "falls to rules 3–5", and rule 3 *is* the result. The behaviour is defensible ("the newest
attempt was killed, re-offer the key") but it is neither what the section says nor pinned.
Decide it in G12r and add the fixture.

**MINOR 3 — `tasks.py:1043`: a malformed `TASKS_STALE_AFTER` crashes every subcommand.**
`default=int(os.environ.get("TASKS_STALE_AFTER", …))` is evaluated while the parser is built,
so `TASKS_STALE_AFTER=abc tasks.py … check` dies with a bare `ValueError` traceback — including
inside the `lint` gate's `check` and the SessionStart hook's `brief` (which degrades to
"unavailable" rather than saying why). Parse it defensively and fall back to the default with a
one-line warning.

**MINOR 4 — the run dir's mtime is a coarse recency key.** A run dir's mtime is bumped by any
later write to any file in it, so a key's older result can outrank a newer one in a different
dir if its own dir was touched afterwards. Inherited from base's ordering, but G12b makes it
load-bearing for the log-versus-result race. Compare the *files'* mtimes, or record the run's
start time, and say which in the section.

**MINOR 5 (inherited from G12, unchanged) — a `.result` carrying `FACTORY-RESULT
status=running` is misfiled as a live log.** `scan_repo` splits on `v["status"] == "running"`,
so such a row lands in `running` (it keeps its `file` key; nothing crashes). The seat never
writes that status; one sentence in the section if `running` ever becomes a legal result
status.

**Note — a future-dated log always counts as live.** `now - log_mtime` is negative under clock
skew, which is always `< stale_after`. Harmless and arguably right; worth a word.

**Note — `scan_repo` publishes a new `imported` map** (`key → defining repo`), consumed by
`check`. Not in the plan's interface list, but needed and correct; name it in the section so
the next task does not re-invent it.

## Deviations

- **Recorded, rejected:** MAJOR 1 — a behavioural regression against base in the scheduling
  path, not disclosed in FACTORY-NOTES or the commit body, and not covered by any test.
- **Recorded, allowed, correct:** the commit touches `docs/OPERATIONS.md`, which G12b's
  `touches` line names this time; only the generated block inside `<!-- tasks:begin -->`
  changed (`… G12b PW1glm …` → `… G12b OG1r PW1glm …`), and the hook's one regenerate on my
  clone removes `G12b` itself — G8c's known tax, exactly the plan's Step 4 allowance.
- **Recorded, allowed:** `read_results` gained a second parameter with a default, so every
  existing caller (`build`, `scan_repo`, `evidence.py tasks`) is source-compatible; `build()`
  carries `stale_after` through even though `main` builds its graph inline.
- **Not this round's fault:** MINOR 4 and MINOR 5 are inherited (from base and from G12
  respectively). Carry them into G12r.
- **Gate procedure:** run in a throwaway clone under the session scratchpad with
  `XDG_CACHE_HOME` set there; `pytest` with `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`;
  the implementer's workspace was read only (`git status` clean at `9950f10`); nothing outside
  the clone, the nix cache dir and this file was written; no `sudo`, no host mutation.
