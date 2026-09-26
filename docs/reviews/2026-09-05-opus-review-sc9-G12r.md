# Opus gate — seat run sc9, task G12r — APPROVED

Task: `G12r` (code, S) — re-plan of G12 under rule A1: the satisfied-dependency set is keyed by
`(repo, chain root)`, never a bare key. Plan `docs/superpowers/plans/2026-09-05-session-context.md`
§`G12r` (lines 1670-1682); the rejection it answers is
`docs/reviews/2026-09-05-opus-review-sc8-G12b.md`. Workspace `/home/dalhaka/factory/ws/sc9/G12r`,
branch `task/G12r`, head `50bc23774fe7`, base `8ed3d2dd748d`. Reviewed in a throwaway clone under
the session scratchpad; the implementer's workspace was read only and is still at `50bc237`
(`git status --porcelain` shows only its own pre-existing untracked `scratch/`).

## Summary

**The G12b regression is dead, and it is dead for the right reason.** The satisfied set is now a
set of `(repo, chain_root)` pairs (`tasks.py:538`, `:562`, `:623`); each task carries a `dep_repo`
map built in its DEFINING repo's namespace (`tasks.py:566-579`); `derive_status` (`:395-407`) and
`waves` (`:730-748`) both consult it, judging a locally attributed dependency against
`landed_keys`/`local_landed` and a foreign one against the keyed `extra_landed`. I proved every
row of the required matrix on **real `git init` repositories with real commits and a real
`git log`** — never the implementer's `fake_git`: 42 hand-built assertions across two probe
scripts, all pass. The exact G12b fixture now gives `X1 ready`, `BL blocked | L1`,
`waves(repo-b) == [['L1','X1'], ['BL']]`, `check` clean, and `resolved_elsewhere(repo-b) ==
[('repo-a','L1')]` — and the mirror, the no-import collision, and the third-repo attribution all
behave. All five of G12's own rules still hold. Twenty-eight mutations applied on the delivered
tree, **twenty-six killed**, including all eighteen from the G12b review's table.

`evidence-unit` (106 tests), `lint`, `ruff` and `tasks.py check` are green, and green on
`--rebuild` (not merely cached). One commit, two files, subject byte-identical, both trailers in
order, stdlib only. On live data the running keys are exactly the two seats alive at the time
(`cr5 CR1b`, `og5 OG1r2b`), `--next` on the plan-writing plan is zero bytes, and the contract
drift the G12b gate noted in passing — `dsh-harness` publishing its own roots in
`resolved_elsewhere` — is closed: it is now `[]`.

Two of my mutations survive (**MINOR 1**, **MINOR 2**). Neither is a behavioural defect — I
verified by A/B that the delivered code does the right thing in both cases — but both are
*unpinned*: the "landing is judged in the ATTRIBUTED repo" clause is only half covered, and the
"never keyed to this repo" guard is covered by nothing at all. Their worst observable effect is
the contents of the published `resolved_elsewhere` list; neither can reach the scheduling path,
because a dependency whose `dep_repo` names this repo never consults `extra_landed` in either
`derive_status` or `waves`. The plan's own Test line requires exactly one mutation to die (the
flat set), and that one dies. So these are MINORs to fold into the next task on this file, not a
third rejection.

**The `waves(repo-b)` discrepancy is the orchestrator's, not the implementer's.** The plan text
(line 1676) writes `waves(B) == [["L1"], ["BL", "X1"]]`. That is the BASE tree's value. Reasoning
from the contract: `X1` is defined in A, attributed to B, and depends on A's `L1`, which A has
landed — so `X1` is `ready` with nothing pending and enters the **first** layer. B's own `L1` is
unlanded, so it is `ready` as a root and also enters the first layer, while `BL` waits on it and
falls to the second. `[['L1','X1'], ['BL']]` is the value that follows, exactly as the G12b
gate's Required test states and exactly what the implementer asserted; my real-git probe returns
it. Recorded as a plan-text error, not a finding.

## Rule behaviour

Every row is my own fixture: `git init`, real commits, real `git log`, real workspace clones whose
`.git/config` origin ends `/base/<repo>`. Scripts `probe_ns.py` (24 assertions) and
`probe_run.py` (18 assertions).

| # | case | expected | observed |
|---|---|---|---|
| 1 | A lands its own `L1`, defines `X1 (**repo:** repo-b, dependsOn L1)`; B defines its own unlanded `L1` and `BL (dependsOn L1)` | `X1 ready`, `BL blocked \| L1` | `X1 ready`; `BL ('blocked','L1')` — **pass** |
| 1b | …the scheduling half | `waves(repo-b) == [['L1','X1'], ['BL']]` | exactly that — **pass** |
| 1c | …`check` and the published set | clean; only roots attributed elsewhere AND landed there | `check(...) == []`; `resolved_elsewhere(repo-b) == [('repo-a','L1')]`, `(repo-a) == []` — **pass** |
| 2 | mirror: B lands its own `L1`, A's `L1` unlanded | `BL ready`, `X1 blocked` | `BL ready`; `X1 ('blocked','L1')`; `resolved_elsewhere(repo-b) == []`; `check` clean — **pass** |
| 3 | same-named `L1` in two repos, **no import at all**; A lands its `L1` | never cross-satisfied | `repo-a/AD ready`, `repo-b/BD ('blocked','L1')`, `waves(repo-b) == [['L1'],['BD']]`, `resolved_elsewhere == []` — **pass** |
| 3b | mirror of 3 (B lands its `L1`) | never cross-satisfied | `repo-a/AD ('blocked','L1')`, `repo-b/BD ready` — **pass** |
| 4 | A defines `T1 (**repo:** repo-c)` and `X1 (**repo:** repo-b, dependsOn T1)`; landing judged in the third repo | ready only when **repo-c** landed it | landed in repo-c → `X1 ready`, `resolved_elsewhere(repo-b) == [('repo-c','T1')]`, `waves == [['X1']]`; landed in repo-a → `blocked`; landed in repo-b → `blocked` — **pass** |
| 4b | A defines `Q1 (**repo:** repo-b)` and `X1 (**repo:** repo-b, dependsOn Q1)` — the dep is attributed **back to this repo** | judged locally, never published as "elsewhere" | Q1 landed in b → `Q1 landed`, `X1 ready`, `resolved_elsewhere == []`; landed in a or nowhere → `X1 ('blocked','Q1')` — **pass** (the `continue` at `:555` costs no legitimate satisfaction) |
| 5a | fresh `r1/K1.log` | `running`, never re-offered | `read_results` → `running/r1`; state `('running','K1 run=r1')`; `waves == [['T2']]`; `conflicts == []` — **pass** |
| 5b | log older than `stale_after` | falls through, schedulable again | default 7200 → `{}`, state `ready`, `waves == [['K1','T2']]`; with `stale_after=200000` → `running` both at `read_results` and graph level — **pass** |
| 5c | `K1.log.killed-by-reboot-…`, `K1.log.misfire`, `K1.truncated-response` | not read | `read_results` → `{}` — **pass** |
| 5d | a `.result` whose block says `status=running` | `ran`, not a live log | entry carries `file`; state `('ran','K1 status=running run=r1')` — **pass** |
| 5e | older run's `status=done` `.result` + **stale** newer log | the `.result` wins (rule 3 reachable) | `{'status':'done','run':'r1','file':…}`; state `('ran','K1 status=done run=r1')` — **pass** |
| 5f | older `.result` + **fresh** newer log | `running` | `{'status':'running','run':'r2'}` — **pass** |
| 5g | a log beside a result in the **same** run | the result | `{'status':'done','run':'r1',…}` — **pass** |
| 5h | a log whose workspace clone is missing | non-evidence | `read_results` → `{}` — **pass** |
| 6 | `TASKS_STALE_AFTER=abc` (and `''`, `'12 3'`, `'9e9x'`) on `check`, `brief`, `waves`, `json`, `board-drift` | error message naming the variable, no traceback, no crash | every combination: stderr `tasks: TASKS_STALE_AFTER='abc' is not an integer; using 7200`, `Traceback` count 0, stdout clean (`waves --json` still prints the structure). `check`/`brief` rc 0; `waves`/`graph`/`board-drift` rc 2 is argparse's missing `--repo` — **identical rc with a valid value** — **pass**, with the exit-code caveat in MINOR 5 |
| 7 | live `brief` running column vs `pgrep -af factory-task` at 18:38 CDT | must match | `pgrep`: `670444 … cr5 … CR1b`, `671575 … og5 … OG1r2b`. Graph running rows: `CR1`, `CR1b` (`CR1b run=cr5`) and `OG1r2`, `OG1r2b` (`OG1r2b run=og5`) — the two live chains, both members each, column `running 4`; `**Running:** nixos-agent-env/CR1 (CR1b run=cr5) · nixos-agent-env/OG1r2 (OG1r2b run=og5)` dedupes to the chain roots. sc9/G12r itself has a `.result` and reads `ran`. No corpses — **pass** |
| 7b | live `--next` on the plan-writing plan | zero bytes | `od -c` → `0000000`, `wc -c` → `0`; `--json` → `[]`; whole-repo `--next` → `"B1 SB1" "CR3" "SB2"`, `--json` → `[[["B1","SB1"],["CR3"],["SB2"]],[["SB4"]],[["SB5"]]]`; live `check` rc 0 — **pass** |
| 7c | live `resolved_elsewhere` | keyed pairs; no self-referential entries | `nixos-agent-env: [('dsh-harness','H1'), ('dsh-harness','H2'), ('gaming','PB0')]`; `dsh-harness: []` — the G12b gate's noted drift (`['H1','H2']`, its own roots) is closed — **pass** |
| 8 | module docstring | documents the `imported` map and states rule 3 reachability | `tasks.py:1-21`: the `(repo, chain_root)` keying, `imported` (`task key -> defining repo`) and `resolved_elsewhere`, and "rule 3 stays reachable — a stale newest log does not discard an older run's `.result`" — **pass** (wording caveat in MINOR 3) |

`resolved_elsewhere` is consumed nowhere outside `tasks.py` and `test_tasks.py` (grepped `*.js`,
`*.sh`, `*.nix`, `*.mjs`, `*.py` across the tree), so the type change from `list[str]` to
`list[tuple]` breaks no caller; `tasks.py json` still round-trips (`json.dumps` renders the pairs
as two-element lists, and `waves` unpacks lists as happily as tuples), and `evidence.py tasks …
brief` — the wrapper the SessionStart hook uses — renders.

Commit hygiene: **one** commit on `8ed3d2d` (`git rev-list --count` → 1). Files are
`pkgs/evidence/tasks.py` (+205/-48 vs `task/G12b`) and `tests/evidence/test_tasks.py` (+135),
both inside `touches`; `docs/OPERATIONS.md` is declared but correctly untouched (G12r was already
in the queue block on this base). Subject `cmp`-identical to the plan's line 1682 (156 bytes both
sides). `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run
sc9)` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`, in that order. Diff against
`task/G12b` is confined to the four seams the plan names (the keying, the `read_results`
result/log split, the `.result`-carries-`file` test, the `TASKS_STALE_AFTER` guard) plus the
docstring — G12b's content is otherwise verbatim. Stdlib only; no `sudo`, `nixos-rebuild`,
`systemctl`, no bypass flag, no new `2>/dev/null`, no network, no secrets.

## Checks

Run in the clone with `XDG_CACHE_HOME` under the session scratchpad.

| check | command | result | wall |
|---|---|---|---|
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | **rc 0** — `All checks passed!` | 2 s |
| pytest | `pytest tests/evidence -q -p no:cacheprovider` | **rc 0** — 106 passed | 5 s |
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **rc 0** — `evidence-unit> 106 passed in 3.76s` | 4 s |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **rc 0** — treefmt 88 files 0 changed; statix/deadnix/ruff `All checks passed!`; 34 files already formatted | 2 s |
| tasks check (clone) | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | **rc 0**, no output | <1 s |
| tasks check (live) | `… --root /home/dalhaka/nixos-agent-env check` | **rc 0**, no output | 2 s |
| pre-commit | `nix develop -c githooks/pre-commit` | rc 1 — `docs/OPERATIONS.md queue block was stale and has been regenerated` → `git add` → **rc 0**, `All checks passed`, `render.test.mjs: all assertions passed`. **One** regenerate, exactly the plan's allowance | 2 s + 2 s |

Both nix checks were re-run with `--rebuild`, so the passes are this tree's, not a cached
derivation's. The hook's single regenerate drops `G12r` itself from the queue block (its subject
is now in `git log`) — G8c's known tax, identical to G12b and G11r. The clone was restored
(`git status --porcelain` empty) afterwards.

## Red before green

G12b's `pkgs/evidence/tasks.py` (`git show task/G12b:…` from `/home/dalhaka/factory/ws/sc8/G12b`)
substituted into the clone, G12r's tests kept: **5 failed, 101 passed.** All five are the tests
this commit exists to satisfy, and each fails for exactly the rejected reason — the `(repo, root)`
fixture **and** all three folded minors go red.

| test | failure on G12b's `tasks.py` |
|---|---|
| `test_satisfaction_keyed_by_repo_not_bare_root` | `AssertionError: assert 'ready' == 'blocked'` — MAJOR 1: `BL` reads `ready` off A's landed `L1` |
| `test_resolved_elsewhere_feeds_waves_and_brief` | `assert ['PB0'] == [('gaming', 'PB0')]` — the bare, unqualified set |
| `test_stale_newest_log_does_not_discard_older_result` | `KeyError: ('nixos-agent-env', 'K1')` — MINOR 2: the older run's genuine `.result` was discarded |
| `test_result_with_running_status_is_ran` | `assert 'running' == 'ran'` — MINOR 5 |
| `test_malformed_tasks_stale_after_warns_not_crashes` | `ValueError: invalid literal for int() with base 10: 'abc'` — MINOR 3, the bare traceback |

`tasks.py` restored; SHA-256 back to `53d47762a33358235e83a76ff91ae497eef4dee3a56959a6c2b461bffe8e0a3a`
and `git status --porcelain` empty; **106 passed** green again.

## Mutation table

Each applied alone to the delivered tree, the file's SHA-256 asserted changed before the run, full
`tests/evidence` run, then `git checkout --` and the SHA-256 asserted back to
`53d47762a3335823…`. No void rows: every anchor matched exactly once. **28 applied, 26 killed.**

The plan's / gate's required set:

| # | mutation | verdict | killed by |
|---|---|---|---|
| M-A | `derive_status`: fold the imported resolution back into a flat set (a bare root satisfies a local key) | **killed** | `test_satisfaction_keyed_by_repo_not_bare_root` |
| M-A2 | the same flattening on the scheduling half (`waves`) | **killed** | `test_satisfaction_keyed_by_repo_not_bare_root` |
| M-B | judge landing in the DEFINING repo instead of the attributed one (`dep_repo[root] = defining`) | **killed** | `test_cross_repo_dep_resolves_via_attributed_repo`, `test_resolved_elsewhere_feeds_waves_and_brief`, `test_check_accepts_dep_redirected_to_other_repo` |
| M-B2 | the same rule on the other seam: `target = od.get(droot) or defining` → always `defining` (`tasks.py:551-554`) | **SURVIVED** | — (MINOR 1) |
| M-C | let `extra_landed` receive a root this repo defines locally (drop the `continue` at `tasks.py:555-556`) | **SURVIVED** | — (MINOR 2) |
| M-D | `TASKS_STALE_AFTER` parse guard removed | **killed** | `test_malformed_tasks_stale_after_warns_not_crashes` |
| M-E | a `status=running` `.result` treated as a live log | **killed** | `test_result_with_running_status_is_ran` |
| M-F | the newest-`.result` rule inverted (a stale newest log discards the older `.result`) | **killed** | `test_stale_newest_log_does_not_discard_older_result` |
| M-G | `resolved_elsewhere` reports roots attributed elsewhere but NOT landed (imported loop) | **killed** | `test_imported_task_dep_blocked_when_foreign_local_not_landed` |
| M-G2 | the same on the local cross-repo loop | **killed** | `test_cross_repo_dep_resolves_via_attributed_repo`, `test_running_elsewhere_dependency_not_satisfied` |

The G12b review's eighteen, re-applied on the G12r tree — **all eighteen still die**:

| # | mutation | killed by |
|---|---|---|
| M1 | G12's defect: a log always outranks a result from another run | `test_running_log_with_result_is_ran`, `test_read_results_newer_result_beats_older_log` |
| M2 | the staleness bound dropped (any log is live) | `…stale_log_is_not_running`, `…stale_log_key_reads_ready`, `…stale_newest_log_does_not_discard_older_result` |
| M3 | `open_tasks` includes `running` | `…not_scheduled_and_counted`, `…absent_from_conflicts_across_plans` |
| M4 | rule 2.5 deleted (`running` never derived) | 4 tests incl. `…chain_running_member_outranks_root_review` |
| M5 | running keys dropped from `_chain_members` | `…chain_running_member_outranks_root_review` |
| M6 | `--next` prints a blank line when nothing is schedulable | `…waves_next_nothing_schedulable_prints_zero_bytes` |
| M7 | the imported-task resolution loop removed | `…imported_task_dep_resolves_against_defining_repo`, `…satisfaction_keyed_by_repo_not_bare_root` |
| M8 | `check` resolves an imported task against the repo it RUNS in | both imported-task tests |
| M9 | `deferred-to-brief` removed from `STATES` | `…states_include_deferred_to_brief`, `…withdrawn_and_parked_in_brief` |
| M10 | a cross-repo edge satisfied by mere existence | `…cross_repo_dep_resolves_via_attributed_repo`, `…running_elsewhere_dependency_not_satisfied` |
| R1 | the `*.log` scan removed | 4 tests |
| R2 | `--next` prints every wave | `…main_waves_next_json_and_default` |
| R3 | `--json` flattens waves → groups | `…main_waves_next_json_and_default` |
| R4 | brief header loses the `running` column | `…not_scheduled_and_counted` |
| R5 | log attribution ignored (workspace need not exist) | `…ignores_running_log_without_workspace` |
| R6 | the `**Running:**` line dropped | `…not_scheduled_and_counted` |
| R7 | default `waves` back to one group per line | `…wave_lines_one_per_wave`, `…main_waves_next_json_and_default` |
| R8 | same-run tie-break inverted (`>=`) | `…running_log_with_result_is_ran` |

## Findings

No MAJORs.

**MINOR 1 — `pkgs/evidence/tasks.py:551-554`: "landing is judged in the ATTRIBUTED repo" is only
half pinned; the third-repo case is uncovered.** The contract's attribution rule lives on two
seams: the `dep_repo` map (`:576-578`, killed by three tests) and the `extra_landed` loop's own
target resolution:

```python
            target = od.get(droot)
            if target is None:
                target = defining
```

Collapsing that to `target = defining` — "landing judged in the defining repo, never the
attributed one" — leaves **106 passed**. It is not an equivalent mutant: on my real-git row-4
fixture (A defines `T1 (**repo:** repo-c)` and `X1 (**repo:** repo-b, dependsOn T1)`, and repo-c
has landed `T1`'s subject) the delivered code gives `X1 ready`, `resolved_elsewhere(repo-b) ==
[('repo-c','T1')]`, `waves == [['X1']]`, while the mutant gives `X1 blocked`,
`resolved_elsewhere == []`, `waves == []` — a task that should schedule silently stops
scheduling. The behaviour is right; nothing holds it there. Today's tree hides it because every
imported dependency happens to be attributed to its own defining repo. **Fix:** add the row-4
fixture as a test — an imported task whose `dependsOn` names a key the defining repo attributes to
a *third* repo, asserting `ready` when that third repo landed it and `blocked` when the defining
repo or the running repo landed it instead.

**MINOR 2 — `pkgs/evidence/tasks.py:555-556`: the "never keyed to this repo" guard is pinned by
nothing.** Deleting

```python
            if target == repo["name"]:
                continue  # judged locally, never "elsewhere"
```

leaves **106 passed**. Again not equivalent: on **live data** the mutant makes `dsh-harness`
publish `resolved_elsewhere == [('dsh-harness','H1'), ('dsh-harness','H2')]` — its own roots —
which is precisely the contract drift the G12b gate flagged in passing and which this commit
closes (HEAD: `[]`). The blast radius is bounded — a pair whose repo is this repo is inert in both
`derive_status` (`:402-404` takes the `landed_keys` branch) and `waves` (`:743-746` takes
`local_landed`), so it can never satisfy anything — but the published field's documented meaning
is unguarded. I confirmed the guard costs nothing legitimate: fixture 4b (`Q1` attributed back to
repo-b and landed there) still gives `X1 ready` through `landed_keys`. **Fix:** a test on that
fixture asserting `resolved_elsewhere == []` while `X1` is `ready`.

**MINOR 3 — `pkgs/evidence/tasks.py:15-16`: the docstring's "never a root this repo itself defines
locally" is literally false.** In the headline fixture, `repo-b` defines `L1` locally *and*
publishes `resolved_elsewhere == [('repo-a','L1')]` — correctly, because the pair is qualified.
The plan's contract sentence has the same literal problem. What is true and load-bearing is
*never keyed to this repo*. Reword both, or a future reader will "fix" the wrong thing.

**MINOR 4 — `pkgs/evidence/tasks.py:306-307`: the final `elif log_fresh:` branch is unreachable.**
When `result is None`, `log_newer` is `True` by construction (`:302`), so a fresh log with no
result is already taken by the first branch, and a stale one falls out of all three. Dead code in
the seam that has now been rejected twice; delete it or make the three cases explicit.

**MINOR 5 — `pkgs/evidence/tasks.py:395-407`: the `repo=None` fallback comment is stale, and a
direct caller passing `extra_landed` now silently loses every cross-repo edge.** The comment says
"when absent (direct callers) fall back to the bare-root sets, exactly as before", but
`extra_landed` holds `(repo, root)` pairs, so `root in (set(landed_keys) | resolved_elsewhere)`
can never match one. No in-tree caller is affected — `scan_repo` always passes `repo["name"]`
(`:598`), and every direct call in `test_tasks.py` passes `extra_landed=None` — but the parameter
is now a trap. Either make `repo` required or say in the docstring that `extra_landed` is ignored
without it.

**Note — the malformed-`TASKS_STALE_AFTER` exit code.** The required matrix asked for a non-zero
exit. The delivered code warns on stderr and falls back to `DEFAULT_STALE_AFTER`, so `check` and
`brief` exit 0. I judge the delivered behaviour correct and the matrix row wrong: the plan says
"error message, **not a crash**", and the G12b gate's MINOR 3 prescribed this fix in these words —
"Parse it defensively and fall back to the default with a one-line warning" — precisely because
the crash was breaking the `lint` gate's `check` and the SessionStart hook's `brief`. Refusing to
run would reintroduce that outage for a variable that is merely a tuning knob. Recorded, allowed.

**Note — the live `running` column reads 4 for two seats.** `CR1b` and `OG1r2b` are both typed
tasks whose chain roots (`CR1`, `OG1r2`) are also typed tasks, so each live seat contributes two
`running` rows while `**Running:**` dedupes to one line per chain root. Consistent with rule 2.5
and with the deduping loop at `:995-1009`; worth one sentence in the section so the count is not
read as four seats.

## Verdict

**APPROVED.** The regression G12b was rejected for is gone, and gone by the design the gate
required: satisfaction keyed by `(repo, chain root)`, `depends_on` resolved in the defining repo,
landing judged in the attributed repo, `extra_landed` never keyed to this repo. Every required
matrix row passes on real git repositories, all three folded minors are delivered and each is
red-first on G12b, the eighteen mutations from the previous round all still die, both acceptance
checks are green on `--rebuild`, and the commit conventions are clean. The contract-derived value
of `waves(repo-b)` is `[['L1','X1'], ['BL']]` — the implementer's assertion is right and the plan
text's `[["L1"], ["BL", "X1"]]` is the orchestrator's copy of the base tree's value.

Two mutations survive. Both are coverage gaps on clauses whose behaviour I verified correct by
direct A/B, and neither can reach the scheduling path; the plan's Test line requires one mutation
to die and it dies. Fold MINOR 1 and MINOR 2 (two tests) plus MINOR 3-5 (three one-line
corrections) into the next task that touches `pkgs/evidence/tasks.py`.

### Deviations

- **Recorded, allowed:** `docs/OPERATIONS.md` is declared in `touches` but not modified — on base
  `8ed3d2d` the queue block already listed `G12r`, so no change was owed. A subset of `touches`,
  not a breach. The hook's one regenerate on my clone removes `G12r` itself — G8c's known tax.
- **Recorded, allowed:** `resolved_elsewhere` changed type from `list[str]` to `list[tuple]`. No
  consumer exists outside `tasks.py`/`test_tasks.py`; `json` output and `waves`' unpacking both
  tolerate the list form.
- **Recorded, allowed:** `derive_status` gained a ninth parameter with a default, so every
  existing caller stays source-compatible (see MINOR 5 for the caveat).
- **Orchestrator error, not the implementer's:** the plan's `waves(B)` value at line 1676.
- **Gate procedure:** a throwaway clone under the session scratchpad, `XDG_CACHE_HOME` set there;
  `pytest` with `PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`; fixtures built with real
  `git init` and real commits under `tempfile.mkdtemp`, never `fake_git`; the implementer's
  workspace and both real repos read only; live probes read-only against
  `/home/dalhaka/nixos-agent-env` and `/home/dalhaka/factory/runs`; `write-board` never run;
  nothing outside the clone, the scratchpad and this file was written; no `sudo`, no host
  mutation.
