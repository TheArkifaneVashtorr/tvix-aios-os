---
plan_defect: none
mutants_total: 19
mutants_killed: 15
mutants_outside_named: 10
---
# Opus gate — seat run sh5, task SH6 — APPROVED

## Summary

Branch `task/SH6` in `/home/dalhaka/factory/ws/sh5/SH6`, one commit `f1037ca` on
base `b440969`, gated from a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/2e56f544-dc33-4c36-836e-c2b840c3e5fc/scratchpad/gate-sh5-SH6`.

Every numbered interface item of the SH6 section (9–14, plus the `--split` flag
and its refusal path) is implemented and pinned by a test. All eleven table rows
are real tests, each shown red against the base's `report.py`. All nine mutants
the section names are killed. `evidence-unit` and `lint` both pass at HEAD under
`--rebuild`; `ruff check`, `ruff format --check`, `repomap write` (no `MAP.md`
drift) and `tasks.py check` are clean. The diff touches exactly the section's
three files. The commit subject is byte-identical to the section's, the body
carries the why plus the pasted red and green, and the two trailers follow a
blank line.

The driver's `checks_scope: dirty / checks_scope_files: 1 /
checks_scope_list: tests/evidence/test_harness_report.py` line does **not** mean
a file was uncommitted — see ## Checks. Nothing was uncommitted; the checks ran
at the committed head, on the committed test file.

Six MINORs, all of the same shape: a clause the section states that no fixture
discriminates (four unnamed mutants survive on those clauses). None is a
contract violation — the code implements every clause correctly, verified
end-to-end. No MAJOR. **APPROVED.**

## Contract items

Taken literally from `docs/superpowers/plans/2026-09-07-seat-harness-redesign.md:631–689`.

| item | verdict | evidence |
|---|---|---|
| CLI `report harness --split YYYY-MM-DD` | met | `pkgs/evidence/report.py:675` `h.add_argument("--split", default=None)`; forwarded at `report.py:680–686` |
| baseline lines print for the *before* window (`< split`, narrowed by `--since`) | met | `report.py:560` `baseline_rows = _window(rows, since, split)`; `_window` (`report.py:282–300`) is `since <= d < before` |
| after window `>= split`, narrowed by `--before` | met | `report.py:561` `after_rows = _window(rows, split, before)`; e2e run below: a `2026-09-20` row is excluded by `--before 2026-09-10` (`after: … 8 task rows`, not 9). Untested clause → MINOR-2 |
| without `--split` the block prints for the whole window | met | `report.py:563–564`; `tests/evidence/test_harness_report.py:603` |
| malformed `--split` → exit 2, `report: --split <v>: invalid date (YYYY-MM-DD)` | met | `report.py:546` adds `("--split", split)` to the shared validation loop; `test_harness_report.py:355–359` asserts rc 2 and the exact stderr |
| `harness_report(store, before=None, since=None, split=None, min_n=5)` | met | `report.py:543`, signature exact |
| 9. `after: since <split\|open> before <before\|open>; N task rows, G with a gate verdict, A approved` | met | `report.py:401–407`; e2e: `after: since 2026-09-08 before 2026-09-10; 8 task rows, 6 with a gate verdict, 3 approved` |
| 10. `touches:` line, exact wording | met | `report.py:441–445`; `test_harness_report.py:381–385` asserts the whole string |
| 10. `checks:` line, exact wording | met | `report.py:463–467`; `test_harness_report.py:471–474` |
| 10. `probes:` line, exact wording, `r` = rows with a `drift` value | met | `report.py:483–486`, drift at `report.py:474–481` reads the `probes_verified` map's values; `test_harness_report.py:490–493` |
| 10. `unreported:` line | met | `report.py:488–494`; `test_harness_report.py:507–509`. The section's preamble says "every row for `unreported`" while its line spec says `n=<rows with status unreported>`; the code follows the line spec (`report.py:425`), which is what row 7 pins. Internal plan ambiguity, recorded as MINOR-3 |
| 10. demotion = `error_class` in the change's arms; agreed/overruled/ungated by gate verdict | met | `_DEMOTION_ARMS` `report.py:342–347`; `_demotions` `report.py:350`; `_agreed_overruled_ungated` `report.py:355–370` |
| 10. `x` = rows with `touches_extra > touches_disclosed` | met | `report.py:433–439` |
| 11. `control false positives: <o_total> of <A> approved rows` | met | `report.py:493–495`, `o_total` summed across all four changes (`report.py:431`); `test_harness_report.py:534` |
| 12. verdict line: first five gated demotions by `result_mtime` (ties `run_id`, `key`); `revert` at `o >= 2`; `<5` → `insufficient (n=k)` | met | `_verdict_line` `report.py:372–392`; sort key `report.py:377`; threshold `report.py:383–385`. The `result_mtime` ordering itself is untested → MINOR-4 |
| 12. `n >= 10` and 0 demotions → the `zero demotions in <n> tasks — …` suffix | met | `report.py:387–391`; `test_harness_report.py:436–445` (10 vs 9) |
| 13. `success:` line, exact wording, bound = before-window approved median × 1.5, `yes` at ≤ bound, `insufficient` when either approved set < `min_n` | met | `report.py:497–526`; `test_harness_report.py:568–581` pins the whole string at 140/150/160 and `insufficient (n=4)` |
| 13. without `--split` the before figures print `-` | met | `report.py:497–502`; `test_harness_report.py:615` |
| 14. `untargeted:` line, proxy summed over the after window's gates | met | `report.py:528–540`; `test_harness_report.py:596–601` |
| runbook gains a "Per change" part with the six line kinds, the revert rule, and what a `revert` triggers | met | `docs/runbooks/evidence.md:189–218`: `--split` paragraph, `Per change, the after-window block prints six line kinds (lines 9–14)`, the six kinds, `revert (overruled o of 5)` when `o >= 2`, and "A `revert` line drives a `<KEY>r` re-plan under rule A1" |
| Facts: the `mutants_outside_named` gate field | correct | `pkgs/evidence/streams.py:373–375` `"mutants_total"/"mutants_killed"/"mutants_outside_named": ("null", "int")` — the section's `sed -n '331,333p'` line numbers have drifted (those lines are now `touches_extra`/`touches_disclosed`), but the fields exist as stated. Not a defect in the work under review |

End-to-end proof of the shape, from a scratch store (never `/var/lib/evidence`):

```
after: since 2026-09-08 before 2026-09-10; 8 task rows, 6 with a gate verdict, 3 approved
touches: n=5; demotions 5 (touches-violation); agreed 3 (gate rejected); overruled 2 (gate approved); ungated 0; undisclosed extras 5 rows
checks: n=1; demotions checks-misreported 0, checks-unverifiable 0; agreed 0; overruled 0; ungated 0; verify-timeout 1
probes: n=1; demotions probe-mismatch 0, probe-missing 0; agreed 0; overruled 0; ungated 0; drift 1
unreported: n=1; gated 0; approved 0
control false positives: 2 of 3 approved rows
verdict touches: revert (overruled 2 of 5)
verdict checks: insufficient (n=0)
verdict probes: insufficient (n=0)
verdict unreported: insufficient (n=0)
success: first-gate approved before 4/6 (67%) → after 3/6 (50%); output tokens per landing after 120 against control median × 1.5 = 150: insufficient (n=4)
untargeted: never-ran-named-mutants, one-arm-per-enum, ignored-section-item — unmeasured in the store; proxy: mutants_outside_named summed over the after window's gates = 3 over 1 gates carrying the field
```

Note (not a finding): with `--split`, SH1's line 2 prints `window: since open
before 2026-09-08` — the before window's real upper bound, but it silently drops
a user-supplied `--before`. And without `--split` the `after:` line prints
`since open` even when `--since` narrows the window, because item 9 spells it
`<split|open>` literally. Both are the section's own wording; recorded as
MINOR-5.

## Red before green

The section's stated red command, run in a scratch copy with the base's
`pkgs/evidence/report.py` checked out against the branch's tests:

```
$ nix develop -c pytest tests/evidence/test_harness_report.py -q -k 'split or verdict or success'
E       TypeError: harness_report() got an unexpected keyword argument 'split'
>       assert any(l.startswith("after: since open before open;") for l in lines)
E       assert False
6 failed, 16 deselected in 0.24s
```

That matches the red pasted in the commit body. The `-k` filter only reaches 6
of the 11 new tests, so I ran the whole file the same way:

```
$ nix develop -c pytest tests/evidence/test_harness_report.py -q -p no:cacheprovider
FAILED …::test_split_window_and_malformed_date
FAILED …::test_touches_change_line_and_verdict
FAILED …::test_verdict_first_five_only
FAILED …::test_verdict_zero_demotions_suffix
FAILED …::test_checks_change_line_verify_timeout_not_demotion
FAILED …::test_probes_change_line
FAILED …::test_unreported_change_line
FAILED …::test_control_false_positives
FAILED …::test_success_line_before_after
FAILED …::test_untargeted_line_sums_non_none
FAILED …::test_no_split_before_figures_dash
11 failed, 11 passed in 0.55s
```

All eleven new tests are red against the base implementation; the eleven SH1
tests in the same file stay green (row 11's first half). Restored, green:
`nix develop -c pytest tests/evidence -q` → `452 passed, 1 skipped in 12.32s`.

Row 11's second half: SH1's rows 1–12 stay green — its eleven test functions
above plus `tests/evidence/test_report.py` (row 12's regression), all inside the
452. Every one of the nine discriminating fixtures the section names is a real
fixture, not prose:

| fixture | file:line |
|---|---|
| the split-day row | `tests/evidence/test_harness_report.py:344` (`A2` at `2026-09-08T00:00:00Z`) |
| exactly two of five | `test_harness_report.py:379` (`["rejected","rejected","approved","rejected","approved"]`) |
| the late overruled rows | `test_harness_report.py:408` (`["rejected"]*5 + ["approved","approved"]`) |
| the tenth row | `test_harness_report.py:437`/`:444` (`build(10)` vs `build(9)`) |
| the verify-timeout row | `test_harness_report.py:462` (`C3`, `error_class="verify-timeout"`) |
| the drift row | `test_harness_report.py:484` (`P2`, `probes_verified={"p": "pass", "q": "drift"}`) |
| the ungated unreported row | `test_harness_report.py:502–505` (`U2` has no `grow`) |
| the 150 boundary | `test_harness_report.py:575–579` (140 → yes, 160 → no, 150 → yes) |
| the `None` gate | `test_harness_report.py:590` (`K2` without `mutants_outside_named`) |

The fixtures are schema-real: `write()` (`test_harness_report.py:125–130`) goes
through `ev.replace_stream`, so every fixture row is validated by
`pkgs/evidence/streams.py` before the report reads it.

## Mutants

19 applied in a scratch copy, one at a time, reverted after each.
**9 named by the section, 9 killed. 10 outside the named set, 6 killed.**

Named (rows 7 and 11 name no mutant — `—` in the section's table):

| row | mutant | test | result |
|---|---|---|---|
| 1 | `report.py:294` `d < since` → `d <= since` (split day falls in before) | `test_split_window_and_malformed_date` | **killed** — `E AssertionError: assert 'after: since 2026-09-08 before open; 2 task rows, 0 with a gate verdict, 0 approved' in [… 'population: 2 task rows, …']` |
| 2 | `report.py:384` `o >= 2` → `o > 2` | `test_touches_change_line_and_verdict` | **killed** — `E AssertionError: assert 'verdict touches: revert (overruled 2 of 5)' in [...]` |
| 3 | `report.py:382` `gated[:5]` → `gated` | `test_verdict_first_five_only` | **killed** — `E AssertionError: assert 'verdict touches: keep (overruled 0 of 5)' in [...]` |
| 4 | `report.py:387` `n >= 10` → `n > 10` | `test_verdict_zero_demotions_suffix` | **killed** — `E AssertionError: assert 'verdict touches: insufficient (n=0); zero demotions in 10 tasks — keep only if the target tag fell to zero (tags unmeasured)' in [...]` |
| 5 | `report.py:344` `_DEMOTION_ARMS["checks"]` gains `"verify-timeout"` | `test_checks_change_line_verify_timeout_not_demotion` | **killed** — `E AssertionError: assert 'checks: n=4; … agreed 2; overruled 1; ungated 0; verify-timeout 1' in [...]` (mutant prints `overruled 2`) |
| 6 | `report.py:430` drift rows appended to `demotions` for `probes` | `test_probes_change_line` | **killed** — `E AssertionError: assert 'probes: n=3; … agreed 0; overruled 1; ungated 1; drift 1' in [...]` (mutant prints `ungated 2`) |
| 8 | `report.py:494` `len(approved)` → `len(after_rows)` | `test_control_false_positives` | **killed** — `E AssertionError: assert 'control false positives: 3 of 8 approved rows' in [...]` (mutant prints `3 of 12`) |
| 9 | `report.py:520` `after_median <= bound` → `<` | `test_success_line_before_after` | **killed** — `E assert any("median × 1.5 = 150: yes" in l for l in lines)` → `assert False` |
| 10 | `report.py:538` `{carrying}` → `{len(after_gated)}` | `test_untargeted_line_sums_non_none` | **killed** — `E assert "… = 2 over 2 gates carrying the field" in [...]` |

Outside the named set (each run against the whole `tests/evidence` suite):

| id | mutant | result |
|---|---|---|
| O1 | `report.py:355–370` swap `rejected`/`approved` in `_agreed_overruled_ungated` | killed (4 tests) |
| O2 | `report.py:314` `_first_gate` drops the `round_kind == "first"` filter | killed (`test_success_line_before_after`) |
| O3 | `report.py:322–325` `_median_out` drops the `verdict == "approved"` filter | **survived** → MINOR-1 |
| O4 | `report.py:504` `control * 1.5` → `control * 2` | killed (`test_success_line_before_after`) |
| O5 | `report.py:436–438` `touches_extra > disclosed` → `>=` | killed (`test_touches_change_line_and_verdict`) |
| O6 | `report.py:561` `_window(rows, split, before)` → `_window(rows, split, None)` | **survived** → MINOR-2 |
| O7 | `report.py:425` `unreported` rows → every after-window row | **survived** → MINOR-3 |
| O8 | `report.py:377` sort key drops `result_mtime` | **survived** → MINOR-4 |
| O9 | `report.py:560` `_window(rows, since, split)` → `_window(rows, since, before)` | killed (2 tests) |
| O10 | `report.py:497` `if split is None:` → `if False:` | killed (`test_no_split_before_figures_dash`) |

Each survivor is an *untested clause*, not a wrong behaviour: I confirmed the
production code does the right thing for all four in the end-to-end run above
(`--before` narrows the after window; the median is over approved rows; `n`
counts only unreported rows; the verdict order is by `result_mtime`).

## Checks

All from inside the clone, `XDG_CACHE_HOME` under the session scratch directory.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **pass** — `evidence-unit> 453 passed in 12.34s`, rc 0 |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass** — rc 0 |
| pre-commit | `nix develop -c githooks/pre-commit` | rc 1 **only** on the exempt queue block; rc 0 once regenerated — see below |
| ruff check | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!`, rc 0 |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted`, rc 0 |
| MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc 0, no drift (no new file was added) |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, rc 0 |
| suite | `nix develop -c pytest tests/evidence -q` | `452 passed, 1 skipped` |

**The pre-commit rc 1.** In a fresh clone at HEAD the hook exits 1 with
`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`. The
whole staleness is one token:

```
-… SB5 SB6 SD1 SD4 SD5 SD8 SH6 (… 2026-09-07-seat-harness-redesign.md 2026-09-08-codex-driver-arm.md)
+… SB5 SB6 SD1 SD4 SD5 SD8 (… 2026-09-08-codex-driver-arm.md)
```

`SH6` leaves the derived queue *because this commit exists*. At the moment the
seat committed, `SH6` was still queued and the block was current, so its hook
passed honestly; the block only goes stale afterwards. `docs/OPERATIONS.md`'s
`tasks:begin…tasks:end` block is explicitly exempt under the plan's Global
Constraints ("the pre-commit hook rewrites"), and the landing regenerates it. I
confirmed the rest is green: with the regenerated block staged,
`nix develop -c githooks/pre-commit` exits **0**. Not a finding.

**The driver's `checks_scope: dirty` line, resolved.** The orchestrator's
reading ("the driver found that file uncommitted") is not what the field means.
`tools/factory/seat/factory-task:318–332`:

```
    # checks_scope: dirty when the diff touches flake.nix, tests, or githooks.
    …
      printf 'flake.nix\ntests\ngithooks\n' >"$scope_roots"
      …
      done < <(git -C "$ws" diff --name-only "$base_sha..task/$key" 2>/dev/null || true)
```

It is computed from the **committed** branch diff, not from the worktree. SH6's
diff contains `tests/evidence/test_harness_report.py`, which is under `tests`,
hence `dirty` with `checks_scope_files: 1`. Nothing was uncommitted: the
workspace reflog shows a single `commit:` entry at `2026-09-08 01:23:42`, the
`.result` was written at `01:24:39` with `verify_s: 27`, so verification ran
*after* the commit, and `factory_verify_checks "$ws" "$head_sha"`
(`factory-task:308`) verifies at the committed rev. The workspace has no stash
and a clean `git status`. The checks therefore passed on the committed test
file — I reproduced both at that rev with `--rebuild`.

`touches_extra: 0` reproduced: the branch diff is exactly the three files in the
section's `touches` list.

## Touches and commit

`git diff --name-only b440969..HEAD`:

```
docs/runbooks/evidence.md
pkgs/evidence/report.py
tests/evidence/test_harness_report.py
```

All three are in the section's `touches` list. Nothing outside it; no deviation
line needed, none present. `docs/MAP.md` unchanged (nothing was added), the
plan file untouched, `docs/OPERATIONS.md` untouched — no board commit.

`git rev-list --count b440969..task/SH6` → `1`.

Subject byte-identical to the section's (`cmp` against the literal from
`docs/superpowers/plans/2026-09-07-seat-harness-redesign.md:688` → no
difference, including the em dash and the apostrophe). Body states the why
(§6.3–6.4, what each line measures, that a `revert` becomes a `<KEY>r` under
A1), pastes the red (`TypeError: harness_report() got an unexpected keyword
argument 'split'` and the `after:` assertion) and the green (452/453 passed,
`lint` exit 0, pre-commit). Trailers after a blank line, exactly two, in order:

```
$
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sh5)$
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>$
```

## Findings

No MAJOR.

**MINOR-1 — the "approved only" median is untested.**
`pkgs/evidence/report.py:319–331`. Item 13 says the after figure is the "median
of approved `usage.out`". Dropping the `verdict == "approved"` filter
(`report.py:322–325`) leaves the whole `tests/evidence` suite green
(`452 passed, 1 skipped`): every row in `test_success_line_before_after`'s
before window carries `out=100` and every after row the same value, so approved
and gated medians coincide. A rejected row with a different `out` would
discriminate. The code is correct.

**MINOR-2 — `--before` narrowing the after window is untested.**
`pkgs/evidence/report.py:561`. Item 10 says the after window is `>= split`,
"narrowed by `--before`". Mutating it to `_window(rows, split, None)` leaves
`452 passed`: no fixture passes both `--split` and `--before`. Verified correct
by hand — with `split=2026-09-08, before=2026-09-10`, a `2026-09-20` row is
excluded (`after: … 8 task rows`, would be 9 under the mutant).

**MINOR-3 — the `unreported` row selection is untested, and the section
contradicts itself.**
`pkgs/evidence/report.py:423–426`; plan `:653` (preamble: "every row for
`unreported`") against `:660` (line spec: `n=<rows with status unreported>`).
Replacing the filter with `list(after_rows)` leaves `452 passed`, because
`test_unreported_change_line` (`tests/evidence/test_harness_report.py:496–509`)
stores three rows and all three are `unreported`. A non-unreported row in the
same store would discriminate. The code follows the explicit line spec, which is
the defensible reading; the consequence of the other reading is only the
`verdict unreported:` zero-demotion suffix, which under the code's reading can
essentially never fire.

**MINOR-4 — the verdict's `result_mtime` ordering is untested.**
`pkgs/evidence/report.py:376–379`. Item 12 orders the first five gated demotions
"by `result_mtime` (ties by `run_id`, `key`)". Dropping `result_mtime` from the
sort key leaves `452 passed`: in `test_verdict_first_five_only`
(`tests/evidence/test_harness_report.py:404–426`) the keys `K0…K6` sort
identically by name and by mtime, so the row-3 fixture pins "first five only"
but not "ordered by `result_mtime`". Keys whose lexical order differs from their
mtime order (e.g. `K9` before `K10`) would discriminate.

**MINOR-5 — with `--split`, SH1's `window:` line silently drops `--before`.**
`pkgs/evidence/report.py:569` `sh_before = split if split is not None else
before`. With `--split 2026-09-08 --before 2026-09-10` the line reads
`window: since open before 2026-09-08`, so the user's `--before` never appears
anywhere except inside the `after:` line. SH6 does not respecify SH1's line 2
and the printed bound is the before window's real upper bound, so this is
defensible — but no test covers it, and a reader comparing the two lines cannot
tell whether `--before` was honoured. Related: without `--split`, item 9's
literal `<split|open>` makes the `after:` line print `since open` even when
`--since` narrowed the window (`report.py:401–403`); that one is the section's
own wording, followed exactly.

**MINOR-6 — no test drives a *valid* `--split` through the CLI.**
`pkgs/evidence/report.py:675, 680–686`. `test_split_window_and_malformed_date`
(`tests/evidence/test_harness_report.py:355`) reaches `rp.main` only on the
refusal path; the success path is tested at the `harness_report()` level only.
`--split`'s forwarding into the keyword argument is therefore pinned only by the
argparse `unrecognized arguments` red, not by a green assertion on CLI output.
Low risk — SH1's `test_cli_store_forwarded` covers the surrounding wiring.

## Verdict

**APPROVED.** The section's contract is met item by item, all eleven table rows
are load-bearing tests shown red first, all nine named mutants die, and both
acceptance checks are green at the committed rev under `--rebuild`. The six
MINORs are untested clauses of correctly-implemented behaviour; four of them
correspond to unnamed mutants that survive. Recommended follow-ups, none
blocking: add a rejected row with a distinct `usage.out` (MINOR-1), a
`--split` + `--before` fixture (MINOR-2), a non-unreported row to the
`unreported` fixture (MINOR-3), and keys whose name order contradicts their
mtime order (MINOR-4).
