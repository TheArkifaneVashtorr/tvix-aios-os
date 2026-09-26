---
reviewer: opus
majors: null
minors: null
mutants_total: 19
mutants_killed: 16
---
# Opus gate — seat run sc5, task G12 — REJECTED

## Summary

G12 builds the right shape: `running` is added to `STATES` after `ran`, derived in
`read_results` from a `<KEY>.log` with no `<KEY>.result` and attributed by the run's
workspace clone origin; precedence sits at rule 2.5 (after reviews, before results) and
participates in the chain so the last member's live log outranks an *earlier* member's
review — I proved that on a purpose-built fixture (root `K1` REJECTED, member `K1b` with a
live log → `K1` reports `running`, and no longer appears under "Rejected, fix round owed").
`running` never reaches `waves`, `conflicts` or `factory_args` (it is not in `open_tasks`),
the brief gains a `running` column and a `**Running:**` line, and `waves` now prints one
shell-quoted line per wave with `--next` (first line only, nothing when empty, exit 0) and
`--json` (`[[["E3"],["E7"]],[["D1"]]]`). One commit on `f10636c`, three files, subject
byte-identical to the plan's, both trailers, stdlib only, tree clean; `evidence-unit`,
`lint` and the hook (after the one expected board regenerate) are green; red before green
is real — 7 of the 9 new assertions fail against base `tasks.py`; 16 of 19 mutants died,
including all six of G9's re-run.

It is rejected on one behavioural deviation with a live consequence and one plan-mandated
assertion that cannot fail. **The deviation:** the "a result ends `running`" rule is scoped
to the *same run directory* (`has_result` is keyed by `(run_dir, key)`, `tasks.py:225,255`),
so a stale `<KEY>.log` in an older run dir overrides a newer, attributed `<KEY>.result` in a
different one. Probe: `r1/K1.log` back-dated 24 h, `r2/K1.result` `status=done` →
`read_results` returns `{"status": "running", "run": "r1"}`. That contradicts the section's
per-`(repo, key)` rule and Step 1's `K.log` + older `K.result` → `ran`, and it inverts the
module's own newest-run-wins ordering (`test_read_results_newest_run_wins`). It bites right
now: the five reboot-killed logs (SB3b, G11r, OG1r, PW1glm, PW1kimi) will keep their keys
pinned to `running` even after a successful re-run in a fresh run dir — the state the task
exists to prevent, arrived at from the other side. **The vacuous assertion:** the plan's
Step 1 demands a running task be proven "absent from waves *and* conflicts", but the
fixture holds a single task, so `assert tk.conflicts(g) == []` cannot fail — the mutation
that puts `running` into `conflicts` survives the whole suite, and on a two-plan fixture it
does report a false conflict. This is the same defect class G11r's MINOR 5 already names
for the other conflicts test.

## Checks

By ref, in a throwaway clone of `/home/dalhaka/factory/ws/sc5/G12` at `task/G12`
(`9df4ef3283bdba2051debd98a676d05d1580df11`), base `f10636c`:

- green — **one commit on base**: `git rev-list --count f10636c..task/G12` → `1`.
- green — **files**: `git show --stat HEAD` → `docs/OPERATIONS.md` (+1/-1),
  `pkgs/evidence/tasks.py` (+163/-35 region), `tests/evidence/test_tasks.py` (+151/-1);
  nothing else. `touches` names the two code files; `docs/OPERATIONS.md` is the hook's
  forced queue-block regenerate, expected.
- green — **subject byte-identical** to the plan's line 1606 (`[ "$S" = "$P" ]` → IDENTICAL,
  `od -c` inspected: em dash and the `(test: evidence-unit, lint)` tail intact).
- green — **trailers**: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 …`
  and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- green — **`evidence-unit`**: `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`
  → rc 0. **`lint`**: rc 0. **pytest**: `89 passed`.
- green (one regenerate) — **hook**: first `nix develop -c githooks/pre-commit` → rc 1,
  `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the block
  changes `B1 G12 OG1b RT5` → `B1 OG1b RT5` because G12's own commit is now on the branch
  (the block is derived from the tree, so a task's own commit always makes it stale —
  G8c's known artefact, not a G12 defect). After `git add`, the hook is rc 0, `All checks
  passed`, `render.test.mjs: all assertions passed`.
- green — **interfaces roll-call**: `STATES` = `landed, approved, rejected, ran, running,
  recorded, ready, blocked, withdrawn, parked` (running after ran, G11b's two kept last);
  `_repo_from_workspace` (`:203`) shared by results and logs; rule 2.5 at `:325-329`;
  `open_tasks` unchanged (`ready`/`blocked` only) so `waves`/`conflicts`/`factory_args`
  exclude `running` by construction; `seat_group_lists` (unquoted) now backs both
  `seat_groups` and `wave_structure`; `wave_lines`/`wave_structure` at `:606,:612`;
  CLI `--next`/`--json` at `:998-1010`; brief header + `**Running:**` at `:755,:783`.
- green — **`--next` exact output**: `main([… waves --repo … --plan typed.md --next])` →
  rc 0, stdout exactly `"E3" "E7"\n`; default → `"E3" "E7"\n"D1"\n`; `--json` →
  `[[["E3"],["E7"]],[["D1"]]]`. Empty case returns 0 with no output (unpinned, see Findings).
- green — **no downstream breakage from the output change**: nothing in the tree parses
  `waves` stdout (`grep` over `tools/`, `pkgs/`, `githooks/`, `*.nix`); the only consumer is
  FD1b's plan, which is written against `--next`.
- green — **hard rules**: stdlib only (`glob`, `os`, `re`, `pathlib`, `json`); no `sudo`,
  no `nixos-rebuild`, no `systemctl`, no bypass flags, no new `2>/dev/null`, no network,
  no secrets; implementer worktree clean; no writes outside the workspace.

## Red before green

Base `tasks.py` (`git checkout f10636c -- pkgs/evidence/tasks.py`) with HEAD's tests:
`7 failed, 82 passed`.

- `test_read_results_detects_running_log` — no running derivation at all.
- `test_running_task_not_scheduled_and_counted` — state is `ready`, no `running` column.
- `test_derive_status_running_between_review_and_result` — `derive_status()` has no
  `running=` parameter.
- `test_wave_lines_one_per_wave`, `test_wave_structure_json_shape` — `AttributeError`.
- `test_main_waves_next_json_and_default` — `tasks: error: unrecognized arguments: --next`.
- `test_states_include_withdrawn_and_parked_in_brief` (G11b's, amended for the new column).

The two remaining new tests pass against base — `test_read_results_ignores_running_log_
without_workspace` and `test_running_log_with_result_is_ran` are guards, not red-first
tests (both are killed by mutations M9/M10 below, so they are load-bearing, just not red).
Restored with `git checkout HEAD -- pkgs/evidence/tasks.py`; tree clean.

## Mutation table

19 mutations, each applied alone to the clone, full `tests/evidence` run, then reverted
(tree verified clean afterwards).

| # | mutation | file | killed | by |
|---|---|---|---|---|
| M1 | the `*.log` scan removed — `running` never derived | tasks.py | yes | `test_read_results_detects_running_log`, `test_running_task_not_scheduled_and_counted` |
| M2 | `open_tasks` includes `running` (scheduled again) | tasks.py | yes | `test_running_task_not_scheduled_and_counted` (`waves != []`) |
| M3 | `conflicts` iterates ready+blocked+running | tasks.py | **no** | — (fixture has one task; see Findings) |
| M4 | rule 2.5 deleted — `running` never outranks a result | tasks.py | yes | `test_derive_status_running_…`, `test_running_task_…` |
| M4b | rule 2.5 disabled (`if False and last in running`) | tasks.py | yes | same two |
| M5 | `--next` prints every wave | tasks.py | yes | `test_main_waves_next_json_and_default` |
| M6 | `--next` prints a blank line when nothing is schedulable | tasks.py | **no** | — (empty case unpinned) |
| M7 | `--json` flattens waves → groups | tasks.py | yes | `test_main_waves_next_json_and_default` |
| M8 | brief header loses the `running` column | tasks.py | yes | `test_running_task_not_scheduled_and_counted` |
| M9 | a same-dir `.result` no longer suppresses the log | tasks.py | yes | `test_running_log_with_result_is_ran` |
| M10 | log attribution ignored (workspace need not exist) | tasks.py | yes | `test_read_results_ignores_running_log_without_workspace` |
| M11 | the `**Running:**` line dropped from the brief | tasks.py | yes | `test_running_task_not_scheduled_and_counted` |
| M12 | running keys excluded from `_chain_members` | tasks.py | **no** | — (chain semantic unpinned; see Findings) |
| M13 | default `waves` back to one group per line | tasks.py | yes | `test_main_waves_next_json_and_default` |
| G9-a | chain: the *first* review in the chain decides, not the last member | tasks.py | yes | 5 tests incl. `test_chain_last_member_result_beats_root_review` |
| G9-b | `conflicts` drops the different-plan condition | tasks.py | yes | `test_conflicts_same_plan_not_reported` |
| G9-c | brief counts every legacy row as `open` | tasks.py | yes | `test_brief_legacy_open_counts_only_open` |
| G9-d | `waves --factory-args` without `--plan` exits 0 | tasks.py | yes | `test_main_waves_factory_args_requires_plan` |
| G9-e | repomap counts untracked files | repomap.py | yes | `test_count_files_git_tracked_and_ruff_cache_fallback` |
| G9-f | repomap stops ignoring `.ruff_cache` | repomap.py | yes | same |

All six re-run G9 mutants still die on this branch: G12 did not loosen anything G9 pinned.

Two survivors were confirmed non-equivalent by direct probe (fixture: plan `a.md` with
`K1` REJECTED + `K1b` live log, plan `b.md` with `Z1` ready, all three touching
`shared.py`):

- M3: HEAD → `conflicts == []`; mutant → two rows (`K1`–`Z1`, `K1b`–`Z1`) and `waves`
  offers `K1 K1b Z1`. Real behaviour change, no test sees it.
- M12: HEAD → `K1` state `running (K1b run=r1)`; mutant → `K1` state `rejected (K1 by r0)`
  and the brief re-lists it under `**Rejected, fix round owed:**` while its fix round is
  live. Real behaviour change, no test sees it.

## Real data

Read-only, against the live `~/factory/runs` and the repos in `docs/ledger/repos.toml`:
`python3 pkgs/evidence/tasks.py --root . brief`.

```
| repo | landed | approved | rejected | ran | running | recorded | ready | blocked | withdrawn | parked | legacy open | untracked |
| nixos-agent-env | 62 | 3 | 1 | 5 | 11 | 0 | 2 | 3 | 0 | 0 | 1 | 0 |
**Next wave** — nixos-agent-env: SB1 SB2 (plan 2026-09-05-seat-behind-broker.md)
**Running:** nixos-agent-env/B1 (B1 run=bk1) · nixos-agent-env/PW1glm (PW1glm run=pwg2) ·
nixos-agent-env/PW1kimi (PW1kimi run=pwk2) · nixos-agent-env/SB3 (SB3b run=sb2) ·
nixos-agent-env/OG1 (OG1r run=og3) · nixos-agent-env/G11 (G11r run=sc7)
```

The 11 tasks counted `running` (the line dedups to 6 chain roots, the column counts task
sections — the same root/member arithmetic G9 fixed for the rejected line):

`B1` (bk1) · `PW1glm` (pwg2) · `PW1kimi` (pwk2) · `SB3`, `SB3b` (sb2) · `OG1`, `OG1b`,
`OG1r` (og3) · `G11`, `G11b`, `G11r` (sc7).

**Nothing is actually running** — the host rebooted and every one of those seats is dead;
the logs are the corpses. G12's rule is presence-only, so all 11 read `running`, are
withheld from `waves`, and `--next` offers `SB1 SB2` instead of the fix rounds the
orchestrator actually owes. Other dead logs whose workspaces still exist (`sc1/G7.log`,
`sc1/G9.log`, `sc1/G10b.log`, `sc3/G8b.log`, `rt2/RT2.log`, `rt2b/RT2.log`, `pb0/PB0.log`)
do **not** show, because rule 1 (`landed`) outranks `running` — the false-positive surface
is exactly the not-yet-landed keys. G12 itself reads correctly: `sc5/G12.result` exists, so
it is not `running`. `waves --next` and `--json` render on live data without error.

## Findings

- **major (reject)** `pkgs/evidence/tasks.py:225,255` — result-suppression is scoped to the
  run directory (`has_result` keyed by `(run_dir, key)`), so a `<KEY>.log` in *any* run dir
  unconditionally overwrites a `<KEY>.result` from a *different* run dir, whatever their
  ages. Probe: `r1/K1.log` (mtime −24 h, no result) + `r2/K1.result` `status=done` →
  `read_results[("nixos-agent-env","K1")] == {"status": "running", "run": "r1"}`. The
  section says `running` holds "when `<KEY>.log` exists and `<KEY>.result` does not", per
  `(repo, key)`, and Step 1 pins `K.log` + **older** `K.result` → `ran`; the code satisfies
  that only within one directory. It also inverts the function's own newest-run-wins
  ordering (`test_read_results_newest_run_wins`), and the in-code comment ("a live log
  outranks a stale result from an earlier run dir") asserts a recency comparison the code
  never makes. Live consequence: once SB3b / G11r / OG1r / PW1glm / PW1kimi are re-run in
  fresh run dirs and finish, their `.result` will be ignored and the keys will stay
  `running` — never re-offered, never gated — until someone deletes the stale log.
  **Fix:** make the suppression per `(repo, key)` — build `has_result` from the attributed
  results map, not from `(run_dir, key)` — and pin it with a test that puts the log and the
  result in *different* run dirs (mutation: revert to `(run_dir, key)` → the test fails).
  If instead the orchestrator wants "the newest run dir wins whichever kind of file it
  holds", say so in the section and compare run-dir mtimes explicitly; either way it needs
  a cross-run-dir test, since today neither rule is pinned.
- **major (reject)** `tests/evidence/test_tasks.py:1379-1391` — `assert tk.conflicts(g) == []`
  in `test_running_task_not_scheduled_and_counted` is unfalsifiable: `running_graph`
  contains exactly one task (`K1`), and `conflicts` only ever reports *pairs from different
  plans*. The plan's Step 1 explicitly requires the running task to be shown "absent from
  `waves` and `conflicts`"; the `waves` half is load-bearing (M2 dies), the `conflicts` half
  is not (M3 survives the full suite). **Fix:** give the fixture a second plan with a `ready`
  task whose `touches` overlap the running one, assert `conflicts(g) == []`, and check the
  mutation (`open_tasks` + `running`, or `conflicts` over all tasks) makes it fail — exactly
  the shape G11r's MINOR 5 prescribes for the other conflicts test.
- **minor** `pkgs/evidence/tasks.py:285-288` — the section's headline chain sentence ("a
  member with a live log outranks an older review") is implemented (running keys join
  `_chain_members`, so the last member can be a log-only key) but not pinned: M12 survives,
  flipping a chain root whose fix round is live from `running` back to `rejected` and
  re-listing it under "Rejected, fix round owed" — the precise false alarm G12 exists to
  remove, and the shape of the live `G11 / G11b / G11r` and `OG1 / OG1b / OG1r` chains.
  **Fix:** one test — root with a REJECTED review, suffix member with a live log → root
  state `running`, detail names the member, and the brief's rejected line does not name it.
- **minor** `pkgs/evidence/tasks.py:1004-1007` — `--next` with nothing schedulable prints
  nothing and exits 0 (correct, and FD1b depends on it: "empty output → the
  nothing-schedulable line"), but it is unpinned; M6 (`print(lines[0] if lines else "")`)
  survives. A blank line would make FD1b's `^("[A-Za-z0-9 -]+" ?)+$` validation die 5 on a
  perfectly normal "all landed" run. **Fix:** assert `rc == 0 and out == ""` on an
  all-landed fixture.
- **finding, not a defect — the design gap for the orchestrator (liveness).** `running` is
  derived from the *presence* of a log file. Nothing on the host is running now, yet 11
  tasks read `running` (list above) and are withheld from `waves`; the brief's
  `**Running:**` line is, today, a list of processes that died in the reboot. The section
  has no liveness notion — no pid file, no mtime staleness bound, no run-dir "ended"
  marker — so a killed, crashed or Ctrl-C'd seat parks its key in `running` permanently and
  the dispatcher can never re-offer it. Options for the re-plan, cheapest first: (a) treat a
  log whose mtime is older than N minutes as not-live (N from the seat's own heartbeat
  cadence; the seat already appends continuously, so mtime is a real signal); (b) the seat
  writes `<KEY>.pid` next to the log and removes it on exit, and `read_results` checks
  `os.kill(pid, 0)`; (c) the seat writes a `<KEY>.result` with `status=killed` from a trap —
  the most honest, since it also records *why*. (a) is a one-line change to this code and
  needs no seat change; (b)/(c) belong with SB3/the seat driver. Whichever is chosen, it
  wants a stated bound in the section, because "running" is now load-bearing for
  scheduling.
- **note (G11r interaction, no action for G12 itself).** G12 sits on `f10636c` = G11b's tip,
  and G11b was re-planned as G11r. G12's code does not touch anything G11r's contract
  changes — `waves`' readiness set (G11r item 1) is computed inside `waves`, which G12 only
  wraps (`wave_lines`/`wave_structure` call it unchanged), so the `landed_here ∪
  resolved_elsewhere` union will apply to `--next` and `--json` for free. Two merge points
  to watch when G12 is re-applied over G11r: (i) `docs/OPERATIONS.md` — G12 edits the
  generated queue line, whose header text G11r rewrites ("… tasks whose dependencies run in
  other repos, and in-flight state, are in the session brief"); take G11r's header and let
  the hook regenerate the keys. (ii) G11r's MINOR 5 (a conflicts test that can actually
  fail) is the same fix this gate demands for G12's conflicts assertion — do them together.
  Also worth the orchestrator's eye: G11r's `board_graph` marks cross-repo-dependent tasks
  `deferred-to-brief`; `running` is a second reason a key is absent from the board block,
  and the new header sentence already covers it ("in-flight state … in the session brief").

## Deviations

- The commit touches `docs/OPERATIONS.md`, which G12's `touches` line does not name. Not a
  deviation in substance: the pre-commit hook refuses the commit until the generated queue
  block is regenerated (G8c), and the orchestrator's own gate brief expects the file. No
  hand-written prose was changed — only the derived line inside `<!-- tasks:begin -->`.
- `read_results` now returns entries without a `file` key for running rows (results keep
  theirs). No consumer reads `["file"]` off that map (`grep` verified), and `scan_repo`
  splits the two kinds on `v["status"] == "running"` — but that split also means a genuine
  `.result` carrying `FACTORY-RESULT status=running` would be misfiled as a live log. The
  seat never writes that status today; worth one line in the section if `running` ever
  becomes a legal result status.
- The workspace for a log is derived by convention — `<runs_dir>/../ws/<run>/<key>` —
  whereas a result's workspace is read from its `workspace:` line. The section says
  "attribution by the run dir's workspace clone origin as for results" without fixing the
  path, and the implementer's own test writes a decoy `workspace /some/where` line into the
  log to prove the convention (not the log text) is used. It matches the live layout, but it
  silently yields "not running" if `FACTORY_RUNS` and the workspace root are ever
  configured apart. Acceptable as built; name the convention in the section.
- Gate procedure: run in a throwaway clone under the session scratchpad with
  `XDG_CACHE_HOME` set there; the implementer's workspace was read only (`git status`), and
  nothing outside the clone, the nix cache dir and this file was written.
