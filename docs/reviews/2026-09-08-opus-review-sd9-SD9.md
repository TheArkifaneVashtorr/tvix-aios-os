---
plan_defect: none
mutants_total: 27
mutants_killed: 15
mutants_outside_named: 17
model: opus
---
# Opus gate — seat run sd9, task SD9 — APPROVED

## Summary

`evidence report ladder` lands as the section specifies. Every numbered contract
item is met in the code and, where the section prints a line, the bytes match the
section's text exactly (both headers and the fixture's group line compared
programmatically, below). The six new tests are red against the base's
`pkgs/evidence/{report,tasks}.py` and green at HEAD; all ten mutants the section
names die on the assertion the section names. `evidence-unit` (485 passed) and
`lint` are green under `--rebuild` in a fresh clone, the pre-commit gate passes,
`ruff check` / `ruff format --check` are clean, `repomap` leaves `docs/MAP.md`
unchanged and `tasks.py check` is silent. One commit, subject byte-identical,
both trailers, the plan file untouched, `docs/OPERATIONS.md` changed only inside
the derived queue block.

Eight MINORs, none gating: seven are *untested* arms of contracts the code
implements correctly (I verified each by hand or by mutation) — the three
`absent → default` rules, the seat review's `approve`/`reject` arms, `--plan`,
the ladder's `ReportUnreadable` exit 2, the orchestrate section's full (n ≥
min_n) line and its header, the group ordering, the torn-file arm — and the
eighth is the commit body pasting only the live proxy, not the red and the green.

Working directory: fresh clone
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/dc26f70a-de2c-4054-899c-dd9bf972644c/scratchpad/scratch/SD9/gate-sd9-SD9`
of `task/SD9` (base `8a81816`, head `401bb01`).

## Contract items

**Interface 1 — `tasks.read_result_fields(path) -> dict`** (`pkgs/evidence/tasks.py:729-751`): MET.

- `status` from `FACTORY-RESULT status=` — `tasks.py:741-743`.
- Every named metadata key into its key — `RESULT_FIELD_KEYS`
  (`pkgs/evidence/tasks.py:669-686`) is exactly the section's sixteen: `run key
  model effort route class rung prior fallback seat workspace head base wall_s
  exit_code usage`, read through the existing `_field` helper
  (`pkgs/evidence/tasks.py:572`).
- `commits` = non-empty lines under `commits (base..task/<KEY>):` excluding
  `(none)`, `(no commits)`, `(base commit unknown …)` — `_commit_count`
  (`pkgs/evidence/tasks.py:691-710`). The markers are the real ones:
  `tools/factory/seat/factory-task:996` writes the header, `:868`
  `(base commit unknown -- .factory-meta missing)`, `:872` `(no commits)`.
- `output_tokens` = `usage`'s `output` int, else `None` — `_output_tokens`
  (`pkgs/evidence/tasks.py:712-726`); the non-int case is tested (`"lots"`).
- Missing lines are absent keys — asserted at
  `tests/evidence/test_tasks.py:4011` (`assert "model" not in n and "usage" not
  in n`).
- A torn file is skipped by the caller — `pkgs/evidence/tasks.py:736-739`
  returns `{}` on `OSError`, and `report.py:763-764` skips a row without
  `run`/`key`. Untested (MINOR-6).

**Interface 2 — `evidence report ladder …`** (`pkgs/evidence/report.py:744-891`,
CLI `pkgs/evidence/report.py:918-923`): MET.

- Flags and defaults exactly as stated: `--repo` required, `--runs-dir`
  `~/factory/runs`, `--jobs-dir` `/var/lib/seat/jobs`, `--min-n` 5, `--plan`
  (`pkgs/evidence/report.py:919-923`).
- Rows = every `.result` under `<runs-dir>/*/` with a parseable `run:`/`key:` —
  `pkgs/evidence/report.py:758-764`, read through `tasks.read_result_fields`
  (`report.py:760`), not a second parser.
- The review join: `<repo>/docs/reviews/*opus-review*-<run>-<key>.md` H1, else
  the run's `<key>.review.md` `FACTORY-REVIEW verdict=` (`approve` → approved,
  `rework`/`reject` → rejected), else none — `_row_review`
  (`pkgs/evidence/report.py:690-717`). The H1 is read through
  `tasks._read_review` + `tasks._review_h1` (`report.py:699-700`), i.e. through
  `tasks.REVIEW_RE` at `pkgs/evidence/tasks.py:93-95` — the same regex
  `read_reviews` uses.
- Group tuple, `kind`/`size` from `route:`, `class` absent → `any`, `rung`'s
  leading integer absent → 1 — `_route_kind_size`
  (`pkgs/evidence/report.py:664-670`), `_rung`
  (`pkgs/evidence/report.py:673-676`), the row build
  (`pkgs/evidence/report.py:775-791`), the group key
  (`pkgs/evidence/report.py:797-799`). Confirmed on live data: the read-only
  proxy prints `openrouter/implement/unknown/unknown/any … rung 1` for the
  pre-SD3 `.result` files that carry none of those three lines.
- The header is byte-identical to the section (compared programmatically against
  the plan text):

```
PLAN HEADER : "# evidence report ladder — the seat driver's ladder (spec 2026-09-06-operator-seat-driver-design.md §6); n printed with every line; refused under <min_n>"
CODE HEADER : "# evidence report ladder — the seat driver's ladder (spec 2026-09-06-operator-seat-driver-design.md §6); n printed with every line; refused under <min_n>"
HEADER MATCH: True
PLAN ORCH   : '# orchestrate — drive sessions (run.meta driver: ⋈ job.json)'
CODE ORCH   : '# orchestrate — drive sessions (run.meta driver: ⋈ job.json)'
ORCH MATCH  : True
```

- The group line's shape (`pkgs/evidence/report.py:829-834`) carries the
  section's tokens in order, and the section's example line is byte-identical to
  the string the test asserts (`tests/evidence/test_report.py:455-459`):

```
PLAN: 'openrouter/implement/code/S/bash-driver m/a medium rung 1: n=5 first-gate 3/4 (75%) landed-commits 1.00 fix-rounds 1/3 wall-median 300s out-tokens-median 3000'
TEST: 'openrouter/implement/code/S/bash-driver m/a medium rung 1: n=5 first-gate 3/4 (75%) landed-commits 1.00 fix-rounds 1/3 wall-median 300s out-tokens-median 3000'
MATCH: True
```

- `g`, `a`, `f`, `l` and the medians follow the section's definitions
  (`pkgs/evidence/report.py:811-828`). `f` counts suffix rows whose *root* is
  approved in the group — the section's literal wording ("rows whose key has a
  chain suffix (`CHAIN_RE`) whose root is in the group and approved"); narrowing
  the count to rows inside the group is a mutant that dies (X1 below).
- `n < min_n` → `<tuple>: insufficient (n=<n>)` and nothing else
  (`pkgs/evidence/report.py:808-810`).
- Orchestrate section: `run.meta` `driver:` → `<jobs-dir>/<id>/job.json` with
  `mode == "drive"`; per pair distinct session ids, run count, refusal under
  `min_n` sessions; `orchestrate: no drive session recorded` when nothing is
  readable — `pkgs/evidence/report.py:836-891`.
- Exit 0; unreadable repo → `ReportUnreadable`, exit 2, as `plans`
  (`pkgs/evidence/report.py:755-756` and `:950-952`). Verified by hand:

```
$ nix develop -c python3 pkgs/evidence/evidence.py report ladder --repo /nope/nope --runs-dir ~/factory/runs
report: cannot read repo /nope/nope
EXIT=2
```

**Interface 3 — the docstring names the seam:** MET.
`pkgs/evidence/report.py:753-754`: "(SD9; the join moves onto `join_tasks_gates`
when T10a lands — these output lines stay.)";
`pkgs/evidence/tasks.py:735` closes with "(SD9 interface 1.)".

**Step 3's live proxy:** reproduced read-only in the clone against
`~/factory/runs` (exit 0, 19 group lines plus the orchestrate marker); identical
to the commit body's paste except for two rows added by runs that landed after
the seat's paste (`…/code/S/python-evidence` — this task's own `.result` — and
`…/docs/XS/docs-runbook … rung 2`).

## Red before green

The section's red command, run in the clone with the base's implementation files
checked out over the branch's tests
(`git checkout 8a81816 -- pkgs/evidence/report.py pkgs/evidence/tasks.py`):

```
$ nix develop -c pytest tests/evidence -q -k 'ladder or result_fields'
>       f = tk.read_result_fields(full)
E       AttributeError: module 'tasks' has no attribute 'read_result_fields'
tests/evidence/test_tasks.py:3995: AttributeError
FAILED tests/evidence/test_report.py::test_ladder_refuses_under_five_and_prints_the_synthetic_table
FAILED tests/evidence/test_report.py::test_ladder_joins_the_review_by_run_and_key
FAILED tests/evidence/test_report.py::test_ladder_reads_the_seat_review_when_no_opus_review
FAILED tests/evidence/test_report.py::test_ladder_orchestrate_section - Attri...
FAILED tests/evidence/test_report.py::test_ladder_cli_subcommand_is_wired - S...
FAILED tests/evidence/test_tasks.py::test_read_result_fields - AttributeError...
6 failed, 479 deselected in 0.29s
```

Every test the section names is in that list; the sixth,
`test_ladder_cli_subcommand_is_wired`, is the seat's own extra and covers the
section's predicted `argparse: invalid choice: 'ladder'`. Restored:

```
$ git checkout HEAD -- pkgs/evidence/report.py pkgs/evidence/tasks.py
$ nix develop -c pytest tests/evidence -q -k 'ladder or result_fields'
6 passed, 479 deselected in 0.47s
```

No test in the set is vacuous: each of the six is killed by at least one mutant
below.

## Mutants

Applied one at a time in the clone, reverted with `git checkout HEAD --` after
each. Named set — 10 named, 10 dead:

| # | mutant (the section's words) | applied at | killed by | died? |
|---|---|---|---|---|
| M1 | the n-gate: `n >= 4` | `report.py:808` `if n < min_n` → `if n < min_n - 1` | `test_ladder_refuses_…` (the `min_n=6` arm) | yes |
| M2 | first-gate: count unreviewed as rejected | `report.py:811` `g = sum(… review is not None)` → `g = n` | `test_ladder_refuses_…` | yes |
| M3 | the join on key alone | `report.py:698` glob `*opus-review*-{run}-{key}.md` → `*opus-review*-{key}.md` | `test_ladder_joins_the_review_by_run_and_key` | yes |
| M4 | medians → mean | `report.py:721` `statistics.median` → `statistics.mean` | `test_ladder_refuses_…` | yes |
| M5 | landed-commits over reviewed rows only | `report.py:814` `/ n` → reviewed-only `/ g` | `test_ladder_refuses_…` | yes |
| M6 | count `K4b` in the rung-1 group | `report.py:798` the group key drops effort/rung | `test_ladder_refuses_…` | yes |
| M7 | read only Opus reviews | `report.py:703` early `return None` before the `.review.md` read | `test_ladder_reads_the_seat_review_when_no_opus_review` | yes |
| M8 | orchestrate: count runs as sessions | `report.py:862` `len(info["sessions"])` → `len(info["runs"])` | `test_ladder_orchestrate_section` | yes |
| M9 | any mode is a drive job | `report.py:848` drop `job.get("mode") != "drive"` | `test_ladder_orchestrate_section` | yes |
| M10 | `(none)` counted as a commit | `tasks.py:706` drop the `COMMIT_NONE_MARKERS` skip | `test_read_result_fields` and `test_ladder_refuses_…` | yes |

Representative failing lines:

```
M2  E assert 'openrouter/implement/code/S/bash-driver m/a medium rung 1: n=5 first-gate 3/4 (75%) landed-commits 1.00 fix-rounds 1/3 wall-median 300s out-tokens-median 3000' in [...]
    FAILED tests/evidence/test_report.py::test_ladder_refuses_under_five_and_prints_the_synthetic_table
M3  E assert 'openrouter/implement/code/S/bash-driver m/a medium rung 1: n=2 first-gate 1/2 (50%) …' in [...]
    FAILED tests/evidence/test_report.py::test_ladder_joins_the_review_by_run_and_key
M1  E assert 'openrouter/implement/code/S/bash-driver m/a medium rung 1: insufficient (n=5)' in [...]
M8  E assert 'orchestrate dm de: sessions=2 runs=3 insufficient (n=2)' in "… orchestrate dm de: sessions=3 runs=3 insufficient (n=3)"
M9  E assert 'orchestrate dm de: sessions=2 runs=3 insufficient (n=2)' in "… orchestrate dm de: sessions=3 runs=4 insufficient (n=3)"
M10 E assert (1 == 0)   FAILED tests/evidence/test_tasks.py::test_read_result_fields
```

M6 was run twice: the coarse form (drop `rung` from the group key) turns three
tests red with a `ValueError`; the clean form (fold `K4b` into the rung-1 group
by pinning `"medium", 1` in the key) turns the byte-exact assertion red
(`… out-tokens-median 2500` instead of `3000`). Both kill.

Outside the named set — 17 tried, 5 dead, 12 survivors; every survivor is a
MINOR below or an unstated nicety, none a wrong behaviour:

| # | mutant | result |
|---|---|---|
| X1 | `f` counted over the group only (`for r in gr`) instead of all rows (`report.py:823`) | DIED (`fix-rounds 0/3`) |
| X7 | orchestrate never refuses (`report.py:864` `if sessions < 0`) | DIED |
| X9 | the boundary the other way (`report.py:808` `if n <= min_n`) | DIED — "5 printed at min_n=5" is pinned as well as "refused under" |
| X12 | `_commit_count` `break` → `continue` on the blank line (`tasks.py:703`) | DIED (`assert (5 == 2)`) |
| X15 | the H1 verdict ignored, always `approved` (`report.py:701`) | DIED |
| X2 | `_rung` default 1 → 0 (`report.py:676`) | SURVIVED (MINOR-1) |
| X3 | class default `any` → `unknown` (`report.py:784`) | SURVIVED (MINOR-1) |
| X4 | route fallback `unknown, unknown` → `any, any` (`report.py:670`) | SURVIVED (MINOR-1) |
| X13 | seat verdict: drop the `reject` arm (`report.py:714`) | SURVIVED (MINOR-2) |
| X14 | seat verdict: `approve` → rejected (`report.py:712`) | SURVIVED (MINOR-2) |
| X11 | `--plan` filter disabled (`report.py:765` `if False`) | SURVIVED (MINOR-3) |
| X10 | drop the `ReportUnreadable` raise (`report.py:755-756`) | SURVIVED (MINOR-4) |
| X16 | `ORCHESTRATE_HEADER` text replaced (`report.py:58`) | SURVIVED (MINOR-5) |
| X17 | `sorted(groups)` → `list(groups)` (`report.py:801`) | SURVIVED (MINOR-7) |
| X8 | `read_result_fields` drops the `OSError` guard (`tasks.py:736-739`) | SURVIVED (MINOR-6) |
| X5 | `_output_tokens` drops the `bool` guard (`tasks.py:723`) | SURVIVED (not a stated contract) |
| X6 | `pct` `round` → `int` (`report.py:813`) | SURVIVED (the section does not state the rounding) |

mutants_total 27, killed 15, outside the named set 17.

## Checks

All from inside the fresh clone, `XDG_CACHE_HOME` under the session scratch.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | pass — `evidence-unit> 485 passed in 15.27s`, `EXIT=0` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | pass — `LINT_EXIT=0` |
| lint gate | `nix develop -c githooks/pre-commit` | pass (exit 0); it regenerated the clone's queue block `SD9` → `SD10`, expected in a branch clone where SD9 is landed; reverted, tree clean |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted` |
| MAP | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | no diff |
| graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, rc=0 |
| live proxy | `python3 pkgs/evidence/evidence.py report ladder --repo . --runs-dir ~/factory/runs` | exit 0, 19 group lines + the orchestrate marker (read-only) |

The driver's own record agrees: `~/factory/runs/sd9/SD9.result` →
`FACTORY-CHECKS evidence-unit=pass lint=pass`, `checks_verified_src:
evidence-unit=run lint=run`, `touches_extra: 0`, `FACTORY-COMMITS 1`.

## Touches and commit

Diff `8a81816..401bb01`:

```
 docs/OPERATIONS.md            |   2 +-
 pkgs/evidence/report.py       | 257 +++++++++++++++++++++++++++++++++++++++++-
 pkgs/evidence/tasks.py        |  89 +++++++++++++++
 tests/evidence/test_report.py | 243 +++++++++++++++++++++++++++++++++++++++
 tests/evidence/test_tasks.py  |  52 +++++++++
 5 files changed, 641 insertions(+), 2 deletions(-)
```

The four code/test files are exactly the section's `touches`. `docs/OPERATIONS.md`
is the pre-commit hook's regeneration of the derived queue block: the one changed
line sits inside `<!-- tasks:begin -->…<!-- tasks:end -->` (adding `SD9` and the
plan basename), nothing outside it — generated content the Global Constraints
allow explicitly, not a touches violation. `docs/MAP.md` is unchanged, correctly:
the task adds no package, module, host file, check or top-level entry.

Commit: exactly one (`git rev-list 8a81816..HEAD | wc -l` → 1). The subject was
compared byte for byte with the section's `commit subject` by `cmp` →
`SUBJECT BYTE-IDENTICAL`. Trailers, after a blank line, in the WORKSPACE RULES
order:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sd9)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

No board commit; `docs/superpowers/plans/` untouched
(`git diff 8a81816..HEAD --stat -- docs/superpowers/plans/` is empty). The body
states the why and pastes the live proxy Step 3 asks for, but not the red and the
green (MINOR-8).

## Findings

No MAJORs.

**MINOR-1 — the three `absent → default` rules are stated but untested.**
`pkgs/evidence/report.py:676` (`_rung` → 1), `pkgs/evidence/report.py:784`
(`class` → `any`), `pkgs/evidence/report.py:670` (`route` `explicit`/absent →
`unknown`/`unknown`). Every fixture `.result` written by `write_result`
(`tests/evidence/test_report.py:356`) carries `rung=`, `klass=` and `route=`, so
none of the defaults ever executes in the suite: mutants X2 (`else 1` → `else
0`), X3 (`"any"` → `"unknown"`) and X4 (`return "any", "any"`) each leave the
whole 484-test evidence suite green. The behaviour itself is right — the live
proxy prints `openrouter/implement/unknown/unknown/any … rung 1` for `.result`
files carrying none of the three lines.

**MINOR-2 — the seat review's `approve` and `reject` arms are untested.**
`pkgs/evidence/report.py:712-716`. The only seat-review fixture is
`verdict=rework` (`tests/evidence/test_report.py:517`), so X13 (drop the
`"reject"` arm) and X14 (`approve` → `"rejected"`) both survive the full suite.
The section names all three words: "`approve` = approved, `rework`/`reject` =
rejected".

**MINOR-3 — `--plan GLOB` is unexercised, and is the one place a second parser
reads the `.result`.** `pkgs/evidence/report.py:765-774`: the filter re-reads the
file with `p.read_text()` + `tasks._field(text, r"^plan:…")`, because `plan` is
deliberately outside `RESULT_FIELD_KEYS` (the section's interface 1 lists sixteen
keys and `plan` is not one). Mutant X11 (`if plan is not None:` → `if False:`)
survives: no test passes `--plan`.

**MINOR-4 — the ladder's `ReportUnreadable` / exit 2 arm is untested.**
`pkgs/evidence/report.py:755-756`. Mutant X10 (delete the raise) survives the
suite; `plans` has `test_malformed_today_is_exit_two`
(`tests/evidence/test_report.py:348`) but `ladder` has no equivalent. I verified
the arm by hand (`report: cannot read repo /nope/nope`, exit 2).

**MINOR-5 — the orchestrate section's full line and its header are asserted by
nothing.** `pkgs/evidence/report.py:866-891` (the `sessions >= min_n` branch) and
`pkgs/evidence/report.py:58` (`ORCHESTRATE_HEADER`). The only orchestrate fixture
has two sessions against `min_n=5`, so `tasks=<keys> first-gate <a>/<g>` never
renders: mutant X7 (`if sessions < 0`) is needed just to reach the branch, and
X16 (rewrite the header text) leaves the suite green. Two consequences worth
recording: (a) the section's `tasks=<keys across those runs' group: lines>` is
implemented as a space-joined sorted key list
(`pkgs/evidence/report.py:889`), but by analogy with `sessions=<distinct ids>`
(rendered as a count) a count was also a legal reading, and nothing pins which;
(b) `_group_keys` (`pkgs/evidence/report.py:735-741`) re-derives keys with its
own `[A-Za-z][A-Za-z0-9-]*` instead of reusing `tasks.parse_keys` / `KEY_RE`,
and `tools/factory/seat/factory-wave:164` writes `%q`-quoted group values, a
shape the fixture's `group: "K1 K2"` does not reproduce.

**MINOR-6 — `read_result_fields`'s torn-file arm is untested.**
`pkgs/evidence/tasks.py:736-739`. Mutant X8 (remove the `try/except OSError`)
survives; the section's "a torn file is skipped by the caller" is covered only
for a torn `usage:` value, not for an unreadable file.

**MINOR-7 — the group ordering is untested.** `pkgs/evidence/report.py:801`
(`for gkey in sorted(groups)`). Mutant X17 (`list(groups)`) survives, because
every assertion is `<line> in lines`, never an index. The section says "one line
per group, sorted by the group tuple"; the live proxy does come out sorted.

**MINOR-8 — the commit body pastes the live proxy but not the red and the
green.** Commit `401bb01`'s body. The Global Constraints' TDD rule ("Paste the
red command and its output, then the change, then the green check by name") is
not satisfied by the body; Step 3's live-proxy paste is. Not gating — the red is
reproducible and is pasted above — but the next round should carry it.

## Verdict

**APPROVED.** The section's contract is met literally, the tests are red before
green, every named mutant dies on the assertion the section names, and both
acceptance checks plus the lint gate, the formatters, the MAP regeneration and
the task-graph check are green in a fresh clone. The eight MINORs are untested
arms and one commit-body convention, none of them a wrong behaviour.
`plan_defect: none`.
