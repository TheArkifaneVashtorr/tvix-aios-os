---
plan_defect: missing-case
mutants_total: 24
mutants_killed: 21
mutants_outside_named: 10
reviewer: opus
majors: null
minors: 5
---
# Opus gate — seat run tel1bf, task T1b — APPROVED

## Summary

All five MAJORs of the tel1b gate are closed, each the way the T1b section states. The
code delta over T1 is exactly three lines — `_name_fence` exempts `path` only
(`streams.py:497`), `task-result.kind` → `task_kind` (`streams.py:276`), `lane-job.ts` →
`ts_epoch` (`streams.py:471`) — and `evidence.py` is byte-identical to T1's, so the
equal-row `ts` rule was closed by tests that can fail rather than by a code change, as the
body claims. Every mutant the section names dies: the six arm deletions, the respelling,
`if False:` and "never restamp", the map-site enum guard, the enum-back-in-`_name_fence`
mutant, the `task_kind` deletion and the re-declared `kind`. Red before green reproduces
on the cherry-picked T1 tree for all four new assertions. The four acceptance checks are
green with `--rebuild` on a fresh clone (evidence-unit 358 passed, factory-unit, unit
ok 486, lint), ruff, repomap and `tasks.py check` are clean, and every file in the diff is
inside the section's `touches` (plus `docs/MAP.md` by rule).

The one judgement the orchestrator asked for: the `lane-job.ts` → `ts_epoch` rename is a
**justified consequence, and the plan defect is the plan's, not the seat's**. Item 4's
mandated walk ("no declared field of any kind is named `v`, `ts` or `kind`") turns red on
`lane-job.ts` the moment it is written, and the collision is real, not cosmetic: `append`
builds `{**row, "v": …, "ts": ts or now_iso()}` (`evidence.py:75`) and `replace_stream`
does `{**_strip_env(row), …, "ts": now}` with `_strip_env` dropping `v`/`ts`
(`evidence.py:111-112,168`), so a lane-job row's epoch `ts` would have been silently
overwritten by the envelope's ISO string. Step 3 permits exactly this ("nothing else in
the code unless a test of Step 2 demands it — say what and why in the body"), and the body
says it in a dedicated paragraph. It is a `missing-case` plan defect to record against
**T1W**: that section still names `ts` (`tools/ledger/factory.py:363` writes
`"ts": data.get("ts")`, and `_lane_job_price_key`:445 and `_lane_job_in_window`:595 read it
back), so T1W must be re-typed to rename the field and both readers, or its `ledger-unit`
will go red on `ts: undeclared field`. Nothing is broken today: no writer reaches the
`lane-job` entry until T1W wires it.

Approved. Three MINORs, none owed here.

## Contract items

Numbered as the section's Contract states them.

1. **MAJOR-1, every enum arm pinned by a literal** — met.
   `tests/evidence/test_streams_policy.py:196-235` holds a literal `ENUM_ARMS` dict keyed
   `(kind, field)`. I enumerated the enum-classed declared fields of both entries from
   `streams.KINDS` and the coverage is exact, with nothing missing:
   ```
   task-result enum fields: ['checks_parse', 'effort', 'error_class', 'size', 'status', 'task_kind']
   gate-verdict enum fields: ['plan_defect', 'plan_defect_secondary', 'reviewer', 'round_kind', 'route', 'verdict']
   ```
   The three assertions are present and separate: (a) declaration equality
   (`:541-545`, `_enum_arms` unwrapping `("null", ("enum", …))` at `:530-540`); (b) every
   arm accepted, parametrised over `(kind, field, arm)` (`:548-558`); (c) every arm's
   one-letter misspelling refused with the exact `not in enum` string built from the
   *literal* arms (`:560-566`) — which makes (c) a second, independent detector of a
   changed tuple. The literal is written from the plan's Interfaces table, not derived
   (`:192-195` says so and the code confirms it).
2. **MAJOR-2, the equal-row `ts` rule under a fixed clock** — met.
   `tests/evidence/test_streams_policy.py:651-679` (row 20) monkeypatches
   `evidence.now_iso` to `2026-09-05T12:00:00Z`, appends `(1,1,"a")` and `(1,2,"b")`,
   advances the clock to `2026-09-06T00:00:00Z`, replaces with the section's three rows and
   asserts both the order/`pad` triple and the exact `ts` list
   `["2026-09-05T12:00:00Z", "2026-09-06T00:00:00Z", "2026-09-06T00:00:00Z"]` — the
   discriminating assertion the review asked for. Row 21 (`:681-702`) writes the same rows
   twice with the clock advanced a day between calls and compares file bytes. The seam is
   `evidence.now_iso` as the section names it (`evidence.py:141` `now = now_iso()`,
   resolved through module globals, so the monkeypatch bites); no other name is used and
   none is claimed in the body.
3. **MAJOR-3, the enum exemption on map keys only** — met.
   `pkgs/evidence/streams.py:494-501`:
   ```python
   def _name_fence(name, cls=None):
       """True when `name` is a forbidden field name. A declared field of class
       `path` is the one exemption (`factory-finding.file`); a closed-enum map key
       is exempt at the map site alone (`helm-status`'s `host` tile), not here."""
       if isinstance(cls, tuple) and cls[0] == "path":
           return False
       return _forbidden_name(name)
   ```
   The exemption now lives only at the map site (`streams.py:642-645`,
   `enum_keys = … ; if not enum_keys and _name_fence(k, kcls):`), which the mutant below
   proves is live. The new unit assertion is byte-for-byte the section's
   (`test_streams_policy.py:400-404`): `_name_fence("host", ("enum", ("ok",))) is True` and
   `_name_fence("file", ("path", ("docs",), 200)) is False`. Row 7
   (`:447-458`) and the declared-field walk (`:381-398`) both stay and pass.
4. **MAJOR-4, `task_kind`** — met, in all three places the section names, with the same
   arms and the same position (after `plan`, before `size`):
   `pkgs/evidence/streams.py:276` `"task_kind": ("enum", ("code", "docs", "unknown")),`;
   `pkgs/evidence/SCHEMA.md:11-12` "…key `(run_id, key)`, classification field `task_kind`
   in `code|docs|unknown`…"; the fixture `tests/evidence/test_streams_policy.py:136`
   `"task_kind": "code",`. `ENVELOPE` is unchanged (`streams.py:28`
   `ENVELOPE = ("v", "ts", "kind")`). The new walk is
   `test_no_declared_field_is_named_envelope` (`:423-427`). The plan-side half — T2's
   Interfaces bullet — was corrected by the orchestrator in the base commit
   (`docs/superpowers/plans/2026-09-06-telemetry-store-1.md:468`, "(Corrected by T1b,
   2026-09-07: the declared field for the `<kind>` part is **`task_kind`**…)"), so the T2
   seat will write `task_kind`.
5. **MAJOR-5, the bats fixture in `touches` and explained** — met. The line is unchanged
   from T1 (`tests/unit/83-plan-brief.bats:166`,
   `cp "$BATS_TEST_DIRNAME/../../pkgs/evidence/streams.py" "$REPO/pkgs/evidence/streams.py"`),
   the file is in the section's `touches`, and the commit body's penultimate paragraph
   names the file, the line and the reason (`evidence.py:29` imports `streams` at module
   top). I verified the line is genuinely load-bearing rather than taken on trust — see
   the last mutant in ## Mutants.

The section's seven carried MINORs (`key_of` dead, the eleven untested `not a {class}`
strings, the `ingest` positional, the wide `except ImportError`, the unconditional
`chmod` at `evidence.py:143`, row 29's tautological half, the errata confirmations) are
explicitly "recorded, not owed here"; all seven are still open in the code and stay the
plan's.

## Red before green

The section's stated red is "on the cherry-picked tree": T1's implementation with T1b's
tests. I reconstructed it by fetching `task/T1` read-only into a scratch copy and checking
out T1's `pkgs/evidence/streams.py` and `pkgs/evidence/SCHEMA.md` over the branch's test
file (`git fetch -q /home/dalhaka/factory/ws/tel1b/T1 task/T1` → `a8c2e34`;
`git diff FETCH_HEAD HEAD` over the code is exactly the three renames/edits above and
nothing else — `evidence.py` is untouched between T1 and T1b).

```
$ nix develop -c pytest tests/evidence/test_streams_policy.py -q     # T1 code + T1b tests
72 failed, 96 passed in 2.92s

>       assert streams._name_fence("host", ("enum", ("ok",))) is True
E       AssertionError: assert False is True
        tests/evidence/test_streams_policy.py:403          (item 3)

>               assert name not in streams.ENVELOPE, (kind, name)
E               AssertionError: ('task-result', 'kind')
E               assert 'kind' not in ('v', 'ts', 'kind')
        tests/evidence/test_streams_policy.py:427          (item 4, the walk)

>           assert _enum_arms(streams.KINDS[kind]["fields"][field]) == arms
E           KeyError: 'task_kind'
        tests/evidence/test_streams_policy.py:545          (item 1 + item 4)

>       assert streams.validate(kind, row) == []
E       AssertionError: assert ['ts_epoch: undeclared field'] == []
        tests/evidence/test_streams_policy.py:350          (the lane-job consequence)
```

Restored, the same file is green:

```
$ nix develop -c pytest tests/evidence -q
357 passed, 1 skipped in 7.10s
```

Rows 20, 21 and item 1's three assertions cannot be red on T1's code — the equal-row rule
and the enum tuples were already correct — so their red is the mutant proof the section
prescribes, and both of the section's Step-2 mutants (`arm-round_kind-replan`, `if False:`)
are shown red below. No test in the new set is one that cannot fail.

**MINOR-1 (below):** the body pastes `71 failed, 97 passed`; the tree gives `72 failed,
96 passed`. The extra failure is `test_one_valid_row_per_kind_and_shape[lane-job-row12]` —
the seat ran its red before renaming the `LANE_JOB` fixture to `ts_epoch`, which the walk
only forced afterwards. Honest sequencing, but the pasted count does not reproduce.

## Mutants

Each applied in a scratch copy of the branch, run, reverted. 24 tried, 21 killed, 10
outside the section's names.

**Named by the section — 14 tried, 14 killed.**

| mutant | killing test and line |
|---|---|
| `arm-round_kind-replan` (delete `"replan"`) | `test_enum_arms_literal_matches_declared` — `E AssertionError: assert ('first', 'fix', 'unknown') == (…) / At index 2 diff: 'unknown' != 'replan'` |
| `arm-reviewer-fable` | same test — `At index 3 diff: 'unknown' != 'fable'` |
| `arm-effort-low` | same test — `At index 1 diff: 'medium' != 'low'` |
| `arm-route-openrouter` | same test — `assert ('claude',) == ('claude', 'openrouter')` |
| `arm-checks_parse-missing` | same test — `assert ('ok', 'refused') == ('ok', 'refused', 'missing')` |
| `arm-plan_defects-process` | same test — `Right contains one more item: 'process'` |
| re-add an arm respelled (`"replan"` → `"replann"`) | same test — `At index 2 diff: 'replann' != 'replan'`; and `test_every_enum_arm_accepted` red as well ((a) and (c), as item 1 states) |
| `if False:` on the equal-row branch (`evidence.py:166`) | row 20 — `At index 0 diff: '2026-09-06T00:00:00Z' != '2026-09-05T12:00:00Z'`; row 21 also red on the byte compare |
| never restamp (keep the stored `ts` for a changed row) | row 20 — `At index 1 diff: '2026-09-05T12:00:00Z' != '2026-09-06T00:00:00Z'` (row 21 stays green, exactly as the section predicts) |
| map-site guard dropped (`if _name_fence(k, kcls):`) | `test_name_fence_at_depth_and_enum_key_exemption` — `assert ['tiles.host: forbidden name'] == []` |
| put `enum` back in `_name_fence`'s exemption | `test_name_fence_exempts_path_only_not_enum` — `assert False is True … _name_fence('host', ('enum', ('ok',)))` |
| drop the `path` exemption (T1 row 4's mutant, re-tried) | `test_one_valid_row_per_kind_and_shape` — `assert ['file: forbidden name'] == []`; and the walk's `assert True is False` |
| delete the `task_kind` field (row 1's mutant for the renamed field) | `test_one_valid_row_per_kind_and_shape[task-result-row5]` — `assert ['task_kind: undeclared field'] == []`; `test_enum_arms_literal_matches_declared` — `KeyError: 'task_kind'` |
| declare `"kind"` again on `task-result` | `test_no_declared_field_is_named_envelope` — `AssertionError: ('task-result', 'kind')` |

**Outside the section's names — 10 tried, 7 killed, 3 survived.**

| mutant | result |
|---|---|
| add an arm (`"rework"` to `gate-verdict.verdict`) | KILLED — `Left contains one more item: 'rework'` |
| delete `"unmeasured"` from `CLASSES_CHECK` | KILLED by row 2 — `'class: not in enum (…|operator)' != '… |operator|unmeasured)'` |
| `ENVELOPE = ()` | KILLED — `assert ['kind: undeclared field'] == []` |
| equal-row compares raw rows (envelope not stripped) | KILLED — row 20 `At index 0 diff: '2026-09-06…' != '2026-09-05…'` |
| re-declare `"ts"` on `lane-job` (the rename reverted) | KILLED — `AssertionError: ('lane-job', 'ts')` — the guard that forced the rename is itself live |
| `_name_fence` always `False` | KILLED — five tests red |
| remove the `streams.py` `cp` line from `tests/unit/83-plan-brief.bats` | KILLED — `bats tests/unit/83-plan-brief.bats` → `not ok 19 … not ok 24 …` (`[ "$status" -eq 0 ]' failed`); item 5's necessity claim verified, not taken on trust |
| delete `"unknown"` from `helm-status`'s tile *value* enum | **SURVIVED** — see MINOR-2 |
| declare `"kind"` inside `factory-run` shape A's `tasks` list-of-obj element | **SURVIVED** — see MINOR-3 |
| add a new enum-classed field to `task-result` | **SURVIVED** — see MINOR-3 |

No named mutant survives. None of the three survivors is a live defect: nested `kind` is
not envelope-shadowed (`ENVELOPE` is skipped only in `_check_row`, `streams.py:684`, never
in `_check_obj`), and the other two are outside the section's stated scope.

## Checks

All in a fresh clone of `task/T1b`, exit codes captured directly (not through a pipe).

```
$ nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild   exit=0   (358 passed in 7.05s)
$ nix build .#checks.x86_64-linux.factory-unit  -L --no-link --rebuild   exit=0   (render.test.mjs, plan.test.mjs: all assertions passed)
$ nix build .#checks.x86_64-linux.unit          -L --no-link --rebuild   exit=0   (ok 486)
$ nix build .#checks.x86_64-linux.lint          -L --no-link --rebuild   exit=0
$ nix develop -c ruff check pkgs/evidence tests/evidence tests/unit       exit=0   All checks passed!
$ nix develop -c ruff format --check pkgs/evidence tests/evidence         exit=0   62 files already formatted
$ nix develop -c python3 pkgs/evidence/repomap.py --root . write
$ git diff --exit-code docs/MAP.md                                        exit=0
$ nix develop -c python3 pkgs/evidence/tasks.py --root . --runs-dir /nonexistent --store /nonexistent check
                                                                          exit=0, silent
$ nix develop -c githooks/pre-commit                                      exit=1  (first run)
    tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
$ git add docs/OPERATIONS.md && nix develop -c githooks/pre-commit        exit=0  (second run)
```

The hook's first-run exit 1 is **not** a red check and not the seat's doing — see MINOR-4:
the hook is green at the base commit `8e2a5bb` (verified), and it goes red at HEAD only
because the branch's own commit changes the derived queue from `… T1b` to `… T1W T2 T3`.
A pre-commit hook runs before its commit exists, so no seat can produce the post-commit
block; §Global Constraints and D13 make the queue block a never-a-deviation exception
merged at landing (recipe step 2). Once regenerated the hook is green.

## Touches and commit

Twelve files in the diff, all inside the section's `touches` plus `docs/MAP.md` by rule:

```
docs/MAP.md (rule) | flake.nix | pkgs/evidence/SCHEMA.md | pkgs/evidence/evidence.py
pkgs/evidence/judgements.py | pkgs/evidence/report.py | pkgs/evidence/streams.py
pkgs/evidence/tasks.py | tests/evidence/test_evidence.py
tests/evidence/test_streams_policy.py | tests/unit/83-plan-brief.bats
tools/factory/seat/factory-lib.sh
```

Nothing outside. `docs/superpowers/plans/2026-09-06-telemetry-store-1.md` is untouched by
the seat (the T2 correction is the orchestrator's, in the base commit); no board commit;
no `docs/reviews/` file.

Exactly one commit, `91c6b8c`. The subject is byte-identical to the section's — checked
programmatically against the plan's `**commit subject:**` line, not by eye:

```
byte-identical: True
want: b'evidence: the fence, fix round \xe2\x80\x94 every enum arm pinned, th'
got : b'evidence: the fence, fix round \xe2\x80\x94 every enum arm pinned, th'
```

The body states the why per item, pastes the red run, the ten mutant lines and the four
green checks, and carries item 5's sentence. The two trailers follow a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run tel1bf)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

T1's subject is not reused.

## Findings

No MAJORs.

### MINOR-1 — the pasted red count does not reproduce
`git log -1` body, the "Red" block. The body says `71 failed, 97 passed`; the
cherry-picked tree gives `72 failed, 96 passed in 2.92s`. The difference is
`test_one_valid_row_per_kind_and_shape[lane-job-row12]`
(`tests/evidence/test_streams_policy.py:350`, `assert ['ts_epoch: undeclared field'] ==
[]`) — the seat captured its red before the walk forced the `LANE_JOB` fixture rename.
Every *named* failing line in the body reproduces exactly; only the totals are one apart.

### MINOR-2 — `ENUM_ARMS` covers declared enum *fields*, not enum arms reached through a map or another kind
`tests/evidence/test_streams_policy.py:196-235`. Deleting `"unknown"` from
`helm-status`'s tile value enum (`pkgs/evidence/streams.py:216`, the `("enum", ("ok",
"warn", "fail", "unknown"))` map value class) survives the whole suite — the only
`helm-status` fixture uses `"ok"`. This is inside the section's stated scope ("every
enum-classed field of `task-result` and `gate-verdict`"), so it is not owed; recording it
so the T10a/T2/T3 sections can widen the literal to map value classes if the join needs
them pinned. `check.class` is covered indirectly by row 2's exact-message assertion (its
arm deletion dies).

### MINOR-3 — two one-directional assertions
(a) `test_enum_arms_literal_matches_declared` (`:541-545`) walks `ENUM_ARMS` into
`streams.KINDS`, never the reverse, so **adding** a new enum-classed field to `task-result`
or `gate-verdict` survives (verified: `168 passed`). Adding an *arm* to an existing enum is
caught, which is what item 1's wording asks for.
(b) `_declared_field_names` (`:388-401`) descends `fields`, `shapes` and `obj` but not a
list's element `obj`, so declaring `"kind"` inside `factory-run` shape A's `tasks` element
survives (`14 passed`). Harmless today — `ENVELOPE` is skipped only at the row root
(`pkgs/evidence/streams.py:684`), so a nested `kind` is reachable and validated — but the
assertion is narrower than its docstring's "no declared field of any kind".

### MINOR-4 — the branch leaves the board's derived queue block stale (process, not the seat)
`docs/OPERATIONS.md`, the `<!-- tasks:begin -->` block. `nix develop -c githooks/pre-commit`
exits 1 on a fresh clone of `task/T1b` and 0 at the base `8e2a5bb`; the regenerated line
changes `… SD8 T1b (…)` to `… SD8 T1W T2 T3 (…)` because the branch's own commit marks T1b
as ran. A pre-commit hook cannot see its own commit, so this is structural; §Global
Constraints and D13 already class the queue block as merged at landing. Named here only so
the landing step is not skipped.

### Plan defect to record — `lane-job.ts`, against T1W (`missing-case`)
`pkgs/evidence/streams.py:471` (was `"ts": "num"`, now `"ts_epoch": "num"`). T1's
Interfaces table declares `lane-job.ts`, which `ENVELOPE` shadows exactly as it shadowed
`task-result.kind`; T1b's item 4 named only the latter, and its mandated walk caught the
former. The rename is a **justified consequence**, not a contract violation: Step 3 permits
code changes a Step-2 test demands, the body states it in full, and the collision destroys
data rather than merely hiding a check (`evidence.py:75` and `:111-112,168` overwrite or
strip a row's `ts`). The defect is the plan's, and it now sits in **T1W's** section, which
still says `ts`: `tools/ledger/factory.py:363` writes `"ts": data.get("ts")` and
`_lane_job_price_key` (`:445`) and `_lane_job_in_window` (`:595`) read it back, and
`tools/ledger/schema.md:117,125` documents it. T1W must be re-typed to rename the field in
the writer, both readers, the schema and the `ledger-unit` fixtures, or its check goes red
on `ts: undeclared field`. Nothing is broken on the tree today: no writer reaches the
`lane-job` entry until T1W wires it.

## Verdict

**APPROVED.** All five MAJORs closed as stated, every named mutant killed, red before
green shown on the cherry-picked tree, four acceptance checks green with `--rebuild`, one
commit with a byte-exact subject and both trailers, no file outside `touches`. Four MINORs
recorded, none owed. One plan defect (`missing-case`) to carry into T1W's section before
wave 2 dispatches.
