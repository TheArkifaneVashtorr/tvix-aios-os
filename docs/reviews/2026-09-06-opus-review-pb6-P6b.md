---
reviewer: opus
majors: null
minors: 7
---
# Opus gate — seat run pb6, task P6b — APPROVED

## Summary

Branch `task/P6b` in `/home/dalhaka/factory/ws/pb6/P6b`, base `a55b6b5` (main),
head `aa7cf18`, ONE commit, 15 files (+996/−1). Reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-pb6-P6b`.
Every CLI run used a `--store` under that scratch directory; `/var/lib/evidence`
was never touched, nothing under `/home/dalhaka/factory` was modified, and the
only file written outside the scratch directory is this review.

Both pa5 MAJORs are dead, and dead in the way the plan contracted:

- **The arity fence now refuses on its own.** `thirteen-scores.md` carries
  `total: 35` against a list summing to 35 and `fifteen-scores.md` `total: 45`
  against a list summing to 45, so the sum check accepts both and only the count
  arm can refuse. Deleting the count arm in a scratch copy lands **both rows**
  (`scores` of 13 and of 15 in `plans.jsonl`) and fails two tests.
- **`judgement_path` passes the fence.** The 243-byte prose filename that
  reached the store under P6 is now refused with the reason naming the field,
  exit 1, zero rows. The row-level `validate_judgement(row)` runs at
  `judgements.py:306` and the single `evidence.append(` at `:316`, in the same
  function, with nothing between them but the idempotency skip.

The three pa5 minors are all closed: `..` segments and a leading `/` are refused
for `plan` and `spec`; duplicate keys are refused by name; the
missing-directory line names the repo path given on the command line.

Eleven mutants applied and reverted — the four new ones and P6's seven —
**all eleven killed**. Red before green reproduces: P6's `judgements.py` under
P6b's tests is 6 failed / 120 passed.

`ruff check`, `ruff format --check`, `pytest tests/evidence -q` (126 passed),
`evidence-unit` (126 passed), `lint`, `repomap write` + `git diff --exit-code
docs/MAP.md`, `claims.py validate` and `tasks.py check` are all green. The
`githooks/pre-commit` exit 1 is the known task-branch queue staleness, proven
below not to be a finding.

Seven minors, none blocking. **APPROVED.**

## The row-level fence

`ingest_judgements` (`pkgs/evidence/judgements.py:299–327`) assembles the row
from the raw block fields plus the two transport fields, validates it, and only
then appends:

```python
        judged = judged_ts(str(repo), rel)
        row = {
            "kind": "plan-judgement",
            **fields,
            "judged_ts": judged,
            "judgement_path": rel,
        }
        errors = validate_judgement(row)
        if errors:
            print(f"refused {rel}: {'; '.join(errors)}", file=sys.stderr)
            failed = True
            continue
```

Structurally, in the clone:

```
$ grep -n "append(" pkgs/evidence/judgements.py | grep -v "errors.append"
210:                vals.append(n)
316:        evidence.append(
$ grep -nE "open\(|\.write\(|json\.dump|os\.replace" pkgs/evidence/judgements.py
(none)
$ grep -n "validate_judgement(" pkgs/evidence/judgements.py
...
306:        errors = validate_judgement(row)
```

`evidence.append(` occurs exactly once, at `:316`, and the row-level
`validate_judgement(row)` at `:306` precedes it **inside the same function**
(`ingest_judgements`, `:267–328`). There is no second writer: no `open()`, no
`.write()`, no `json.dump`. `git diff a55b6b5..HEAD -- pkgs/evidence/evidence.py`
removes zero lines, so `append()` and its flock are byte-identical to base.

### Behaviourally (fixture repo under the scratch dir, `git init`-ed, committed; tmp store)

| # | case | expected | observed | exit |
|---|------|----------|----------|------|
| 1 | 242-char prose filename (271-byte `judgement_path`), body byte-identical to `good.md` | refused, no row, reason names `judgement_path` | `refused …forever.md: judgement_path: 271 bytes (limit 200); judgement_path: invalid path`, 0 rows | 1 |
| 2 | 150-char `[A-Za-z0-9._-]` stem + `.md` (name 153) | accepted | `ingested …aaa….md`, stored `judgement_path` 182 bytes | 0 |
| 3 | 151-char stem + `.md` (name 154) | refused (class) | `judgement_path: invalid path`, 0 rows | 1 |
| 4 | total name length 150 / 151 | accepted (both inside the class) | ingested, 179 / 180 stored bytes | 0 |
| 5 | a space in the name (`bad name.md`) | refused | `judgement_path: invalid path`, 0 rows | 1 |
| 6 | a second `/` (`…/sub/x.md`) | refused | `['judgement_path: invalid path']` at the fence | — |
| 7 | `..` in the path (`…/../x.md`) | refused | `['judgement_path: invalid path']` at the fence | — |
| 8 | a leading `/` | refused | `['judgement_path: invalid path']` at the fence | — |
| 9 | `..md` (a `.` stem) | ? | **accepted** — the class admits `.` in the stem; no traversal is possible (no `/` in the class, the glob is non-recursive). Minor 7 | 0 |
| 10 | `judged_ts` from a fake `git` printing a 300-byte "date" | refused? | **refused** — `refused …good.md: judged_ts: 300 bytes (limit 200)`, 0 rows. `judged_ts` is inside the 200-byte rule exactly as the contract says | 1 |

Row 1 verbatim (this is the pa5 MAJOR 2 case, byte-for-byte the same filename):

```
[prose-243] namelen=242 exit=1 rows=0
  stderr: refused docs/reviews/plan-judgements/2026-09-06-the operator said the
  broker leaked and the reason is that the seat guard interpolated the agent
  supplied file path into a reason string which is exactly the free text this
  fence exists to keep out of the telemetry store forever.md:
  judgement_path: 271 bytes (limit 200); judgement_path: invalid path
```

The widest string that can enter the store through `judgement_path` is
**182 bytes** (`docs/reviews/plan-judgements/` = 29 + 150 stem + `.md`), well
inside the rule. Every string field of an accepted row is bounded: I set each
of the 17 row keys in turn to a garbage value and every one but two produced its
own class error.

### Class coverage — the 17 row keys

```
ROW_KEYS = ['author', 'decision', 'effort', 'judged_ts', 'judgement_path',
            'judges', 'judges_dropped', 'kind', 'plan', 'revision', 'scores',
            'self_score', 'spec', 'tasks', 'threshold', 'total', 'words']  (17)
```

Fifteen carry a format class (probed with a garbage value each):

| field | class | garbage value refused by |
|---|---|---|
| `plan`, `spec` | `^docs/[A-Za-z0-9._/-]{1,190}$`, no `..` segment (`:25`, `:110–116`) | `plan/spec: invalid path` |
| `judgement_path` | `^docs/reviews/plan-judgements/[A-Za-z0-9._-]{1,150}\.md$` (`:26–28`) | `judgement_path: invalid path` |
| `author` | `^(fable\|hand\|dsh:[a-z0-9./-]{1,64})$` (`:29`) | `author: invalid (fable \| hand \| dsh:<model>)` |
| `effort` | 7-member enum (`:30`) | `effort: invalid (…)` |
| `words`, `tasks`, `revision` | int ≥ 0 (`:160–164`) | `…: invalid integer (>= 0)` |
| `threshold`, `total` | int (`:166–169`), `total` = `sum(scores)` (`:216–220`) | `…: invalid integer` |
| `self_score` | 0–42 or `null` (`:171–175`) | `self_score: invalid (0-42 or null)` |
| `decision` | 4-member enum (`:177–181`) | `decision: invalid (…)` |
| `judges` | 0–3 of a 4-member enum (`:183–187`) | `judges: invalid (…)` |
| `judges_dropped` | list over a 3-member enum (`:189–193`) | `judges_dropped: invalid (…)` |
| `scores` | exactly 14 ints 0–3 (`:195–214`) | `scores: invalid list` |

Sixteenth, `judged_ts`: the ≤ 200-byte rule only — which is precisely the class
the contract assigns it ("every field, `judged_ts` included, under the 200-byte
rule"), and it is not vacuous (row 10 above). Seventeenth, `kind`: no value
class — see Minor 1. It is not a hole in the store, because the appended row's
`kind` is the literal `"plan-judgement"` at `:320`, never the block's value; I
proved that by putting prose in a `kind:` block key and reading the row back
(`stored kind = 'plan-judgement'`).

### Prose never reaches the store

Ingesting all ten fixtures into a tmp store and grepping `plans.jsonl` for the
distinctive prose tokens of the fixture bodies:

```
absent: Errata          absent: six-row floor   absent: Judge reasons
absent: packet          absent: belongs in prose
absent: duplicate key   absent: arity fence
```

Both stored rows carry exactly 19 keys: `v`, `ts`, `kind`, the 14 fields,
`judged_ts`, `judgement_path`. Nothing else.

## Arity and the refusal table

`thirteen-scores.md`: `scores: [3,3,3,3,3,3,3,3,3,3,2,2,1]` (sum 35),
`total: 35`. `fifteen-scores.md`: fifteen 3s (sum 45), `total: 45`. The sum
check therefore accepts both and only the count arm can refuse. Run against the
real CLI at HEAD and with the count arm deleted:

```
[HEAD] exit=1 rows=0
   err: refused …/fifteen-scores.md: scores: must be exactly 14 entries (got 15)
      | refused …/thirteen-scores.md: scores: must be exactly 14 entries (got 13)
[MUTANT-count-arm-deleted] exit=0 rows=2
   out: ingested …/fifteen-scores.md | ingested …/thirteen-scores.md
   stored scores=[3,3,3,3,3,3,3,3,3,3,3,3,3,3,3] (15 entries) total=45
   stored scores=[3,3,3,3,3,3,3,3,3,3,2,2,1]     (13 entries) total=35
```

That is the pa5 MAJOR 1 inverted: the arm is now the *only* thing standing
between a mis-arity row and the store, and its deletion is caught.

The table-driven test is
`tests/evidence/test_judgements.py:272` (`test_every_refusal_isolates_its_reason`).
It builds from `base_row()` — the 14 fields **plus** `kind`, `judged_ts` and
`judgement_path`, i.e. the assembled row — varies exactly one field per case,
and asserts `errors == expected`, an equality, not a membership. A second
reason from any other rule fails the case. Twenty-one rows: unknown field,
missing key, `plan` path, `spec` path, `author`, `effort`, `words`, `tasks`,
`revision`, `threshold`, `total` (int), `self_score`, `decision`, `judges`,
`judges_dropped`, `scores` list, arity 13, arity 15, score entries 0–3, total ≠
sum, `judgement_path`. I checked each row for a rule that could also satisfy it
and found none — the arity rows carry a matching `total`, the `total="x"` row
short-circuits the sum check (`_as_int` is `None`, `:218`), the `scores="nope"`
row leaves `scores` `None` so the sum check is skipped.

The one refusal class **not** in the table is the 200-byte rule; it is covered
at `:229–242` and is still discriminating — the test asserts the substring
`"201 bytes"` (which only the byte rule emits) and separately that a 200-byte
value raises no byte error at all, which is what kills the `>` → `>=` mutant.
See Minor 6.

## Paths and keys

`_path_ok` (`:110–116`) is the regex **and** a segment scan:

```python
    return (
        isinstance(value, str)
        and PLAN_PATH_RE.match(value)
        and all(seg != ".." for seg in value.split("/"))
    )
```

At the fence:

| value (`plan`, same for `spec`) | result |
|---|---|
| `docs/../../etc/passwd` | `['plan: invalid path']` |
| `docs/x/../y.md` | `['plan: invalid path']` |
| `/docs/x.md` | `['plan: invalid path']` |
| `docs/` | `['plan: invalid path']` |
| `docs//x.md` | `[]` — **accepted** (empty segment; not contracted, Minor 4) |
| `docs/./x.md` | `[]` — **accepted** (`.` segment; not contracted, Minor 4) |

`dotdot.md` through the CLI: `refused docs/reviews/plan-judgements/dotdot.md:
plan: invalid path`, exit 1, 0 rows.

Duplicate keys are a parse-level refusal (`parse_front_matter:104–105` raising
`DuplicateKey`, caught at `:291–294`), so the name is in the message and the
values never matter:

```
[dup-key.md          revision: 0 then 8] exit=1 rows=0  refused …: duplicate key revision
[identical values    revision: 0 then 0] exit=1 rows=0  refused …: duplicate key revision
```

A duplicated key whose values are **identical is still refused** — the check is
`if key in fields`, not a value comparison.

Missing directory names the repo path given on the command line
(`ingest_judgements:271, :275` keeps `repo_arg` before the `Path()`):

```
[missing-dir] exit=0 out='no judgements under /tmp/…/scratchpad/m/mx'
   repo path given = /tmp/…/scratchpad/m/mx
```

pa5's minor 3 (the line named the judgements sub-directory) is closed.

### The pa5 29-case matrix, re-run in brief

All ten fixtures in one repo, one run:

```
refused …/bad-decision.md: decision: invalid (dispatch|revise|revise-exhausted|panel-short)
refused …/body-only.md: no front-matter block
refused …/dotdot.md: plan: invalid path
refused …/dup-key.md: duplicate key revision
refused …/extra-field.md: unknown field errata
refused …/fifteen-scores.md: scores: must be exactly 14 entries (got 15)
refused …/long-note.md: spec: 201 bytes (limit 200); spec: invalid path
refused …/thirteen-scores.md: scores: must be exactly 14 entries (got 13)
ingested …/good.md
ingested …/second-revision.md
EXIT=1
```

And the remainder of the matrix, each on its own fixture repo:

| case | observed | exit |
|---|---|---|
| a required key missing (`threshold`) | `refused …: missing threshold`, 0 rows | 1 |
| `self_score: null` | ingested, 1 row | 0 |
| a 195-byte `plan` (`docs/` + 190) | ingested | 0 |
| 100 × `é` after `docs/` (205 bytes, 105 chars) | `spec: 205 bytes (limit 200); spec: invalid path` — the limit is bytes | 1 |
| closing `---` missing | `no front-matter block` | 1 |
| a continuation line without a `:` | `no front-matter block` | 1 |
| one refused + one good in the same run | good ingested, 1 row, exit 1 | 1 |
| two files, same `(plan, revision)`, one run | `ingested …aaa.md` then `skipped …bbb.md (present)`, 1 row | 0 |
| re-run (idempotency) | `skipped …good.md (present)`, still 1 row | 0 |
| a torn last line appended to `plans.jsonl` | `skipped …good.md (present)`, no duplicate row | 0 |
| `good.md` + `second-revision.md` | two rows, `(plan, 0)` and `(plan, 1)` | 0 |
| a `.markdown` file in the directory | not globbed, no output, 0 rows | 0 |

Idempotency is unchanged, keyed on `(plan, revision)` as ints
(`ingest_judgements:277–281, :312`).

## Tests and mutants

`tests/evidence/test_judgements.py` is 470 lines / 20 tests (up from 15); the
suite is 126 (up from 121). Every test uses `tmp_path` for both the store and
the fixture repo; no reference to `/var/lib/evidence` or `EVIDENCE_STORE`.

Eleven mutants, each applied to a scratch copy of the clone, `pytest
tests/evidence -q`, then reverted. **All eleven killed:**

| # | mutant | result | killed by |
|---|---|---|---|
| A | the exactly-14 count arm deleted (the pa5 survivor) | **KILLED** | `test_scores_arity_is_isolated_from_the_sum_check`, `test_every_refusal_isolates_its_reason` |
| B | the row-level `validate_judgement(row)` call removed | **KILLED** (7 failed) | `test_append_is_only_after_the_row_level_validate`, `test_long_prose_filename_is_refused`, `test_dotdot_segment_fixture_is_refused`, `test_extra_field_is_refused_as_unknown`, `test_bad_decision_is_refused`, `test_201_byte_string_is_refused_and_200_is_accepted`, `test_scores_arity_is_isolated_from_the_sum_check` |
| C | the `..` segment scan dropped from `_path_ok` | **KILLED** | `test_dotdot_segment_fixture_is_refused`, `test_plan_and_spec_refuse_dotdot_and_leading_slash` |
| D | last-wins restored (the `DuplicateKey` raise removed) | **KILLED** | `test_duplicate_key_is_refused` |
| E | `JUDGEMENT_PATH_RE` widened to `.*` | **KILLED** | `test_every_refusal_isolates_its_reason` |
| F | the file's prose copied into a `body` key (allowlist relaxed so the row builds) | **KILLED** | `test_no_free_text_key_is_interpreted`, `test_good_ingests_one_row_with_every_field_from_git` |
| G | the `(plan, revision)` skip dropped | **KILLED** | `test_rerun_is_idempotent_and_prints_skipped` |
| H | `> 200` → `>= 200` | **KILLED** | `test_201_byte_string_is_refused_and_200_is_accepted` |
| I | unknown keys ignored | **KILLED** | `test_no_free_text_key_is_interpreted`, `test_extra_field_is_refused_as_unknown`, `test_every_refusal_isolates_its_reason` |
| J | `dsh:` prefix-only (`{0,64}`) | **KILLED** | `test_every_author_arm_is_accepted_and_empty_dsh_id_refused`, `test_every_refusal_isolates_its_reason` |
| K | the `total` = sum check skipped | **KILLED** | `test_every_refusal_isolates_its_reason` |

Mutant A also lands the two rows behaviourally (pasted above), and mutant B
lands the 243-byte prose filename — both exactly as the plan predicted.

## Checks

All run inside the clone with `nix develop -c`.

| check | result |
|---|---|
| `ruff check pkgs/evidence tests/evidence` | `All checks passed!` — exit 0 |
| `ruff format --check pkgs/evidence tests/evidence` | `24 files already formatted` — exit 0 |
| `pytest tests/evidence -q` | `126 passed in 4.78s` — exit 0 |
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | `126 passed in 4.41s` — exit 0 (`--rebuild` refuses on a never-built drv; built fresh instead) |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | `All checks passed!` / `50 files already formatted` — exit 0 |
| `githooks/pre-commit` | exit 1 — **not a finding.** The only failure is `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`, and the regeneration removes exactly `P6b` from the queue line, because `tasks.py` reads "landed" from `git log` subjects and this branch carries P6's subject. The same hook on base `a55b6b5` is **exit 0** (`render.test.mjs: all assertions passed`), verified in a separate checkout. Committing the board change would have been the breach. |
| `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0, tree clean — `tests/evidence — 18 files` reproduces (7 base + `test_judgements.py` + 10 fixtures) |
| `python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06` | silent, exit 0 |
| `python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

`pkgs/evidence/SCHEMA.md` gains one `plans` row naming all 14 fields,
`judged_ts` and `judgement_path`, and now records that "every field validated by
`judgements.validate_judgement`" — accurate as of this commit.

**Commit convention.** Exactly one commit (`git rev-list --count a55b6b5..HEAD`
= 1). Subject byte-identical to the plan's `**commit subject:**` (compared
programmatically: `subject == plan subject: True`). Both trailers, in the order
`tools/factory/seat/factory-brief:89–90` requires:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pb6)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

Fifteen files: thirteen in P6b's `touches`, `docs/MAP.md` in by rule (the
fixture count changed a top-level entry and `repomap.py write` reproduces it),
and `pkgs/evidence/evidence.py`, which is in **P6's** `touches` and is carried
by the cherry-pick the P6b section itself prescribes — the implementer flagged
it in `FACTORY-NOTES`. No board commit. `~/factory/runs/pb6/P6b.result` is the
exact form (`FACTORY-RESULT status=done`, `FACTORY-CHECKS evidence-unit=pass
lint=pass`, `FACTORY-COMMITS 1`, `FACTORY-NOTES …`). The implementer's claim
`evidence-unit=pass lint=pass` is **confirmed**.

## Red before green

P6's implementation (`git -C /home/dalhaka/factory/ws/pa5/P6 show
task/P6:pkgs/evidence/judgements.py`, 298 lines) dropped into a copy of the
branch tree, P6b's tests unchanged:

```
FAILED tests/evidence/test_judgements.py::test_every_refusal_isolates_its_reason
FAILED tests/evidence/test_judgements.py::test_plan_and_spec_refuse_dotdot_and_leading_slash
FAILED tests/evidence/test_judgements.py::test_dotdot_segment_fixture_is_refused
FAILED tests/evidence/test_judgements.py::test_duplicate_key_is_refused
FAILED tests/evidence/test_judgements.py::test_long_prose_filename_is_refused
FAILED tests/evidence/test_judgements.py::test_append_is_only_after_the_row_level_validate
6 failed, 120 passed in 5.64s
```

with, for the structural test:

```
>       assert validate is not None, "row-level validate_judgement(row) call missing"
E       AssertionError: row-level validate_judgement(row) call missing
```

That is the row-level fence, the long prose filename, `..`, duplicates and the
structural order test — five of the six contracted reds, plus the refusal table.
Restored, the clone is 126 passed.

The **sixth** contracted red is not red: `test_scores_arity_is_isolated_from_
the_sum_check` **passes on P6**, because P6 already had the count arm — only the
*test* was non-discriminating, not the implementation. Its discriminating power
is proven by mutant A instead, which is the right proof and is exactly what the
contract's own mutation clause asks for. This is a wording defect in the plan,
not in the build; see the plan_defect line.

## Findings

No MAJORs. Seven minors, none of which lets free text, an over-long string, or
an unvalidated value reach the store.

### Minor 1 — `kind` is the one row key with no value class, and three transport names are admitted inside the block

`judgements.py:52` puts `kind`, `judged_ts` and `judgement_path` into
`ROW_KEYS`, so the "no other key" fence lets a *file* declare them in its front
matter. Probed with 67 bytes of prose as the value:

```
[block key 'kind']           exit=0 rows=1  stored kind = 'plan-judgement'
[block key 'judged_ts']      exit=0 rows=1  stored judged_ts = '2026-09-06T07:49:43Z'
[block key 'judgement_path'] exit=0 rows=1  stored judgement_path = 'docs/reviews/plan-judgements/good.md'
```

Nothing leaks: `judged_ts` and `judgement_path` are overwritten at row assembly
(`:303–304`, after `**fields`) so the fence never even sees the prose, and
`kind` — which *does* survive into the validated row, unclassed — is replaced by
the literal at `:320`. But the design's file contract is "No other key", and
these three are accepted and silently discarded rather than refused. One line
would close it: validate the block's `fields` against `set(FIELDS)` before
assembling the row, or drop `kind` from `ROW_KEYS` and set it after validation.

### Minor 2 — the appended dict is not the validated object

`validate_judgement(row)` at `:306` sees `row`; `evidence.append` at `:316–325`
writes a **freshly built** dict from `_row_fields(fields)` plus `judged`, `rel`
and the literal `kind`. I traced every value: each derives from a field the
fence just accepted, so the guarantee holds today. But the contract's phrasing —
"so no field can bypass it" — is only true because of that derivation, not
because the validated object is the one written; a future edit to `_row_fields`
would not be caught by the structural test. Appending `row` itself (typed in
place) would make the invariant structural rather than incidental.

### Minor 3 — `judged_ts` carries only the byte class

Contract-sanctioned ("`judged_ts` included, under the 200-byte rule") and not
vacuous — a fake `git` printing 300 bytes is refused
(`refused …good.md: judged_ts: 300 bytes (limit 200)`). But a subverted `git` on
`PATH` printing ≤ 200 bytes of prose would store it verbatim; the value has no
RFC3339 shape check. The threat model is thin (a `git` you do not control
already owns the process), so this is a note, not a hole. An
`^\d{4}-\d\d-\d\dT[\d:]{8}` class would cost one line.

### Minor 4 — `plan` and `spec` still admit empty and `.` segments

`docs//x.md` and `docs/./x.md` both validate clean. The contract named only `..`
and a leading `/`, so this is conformant; both forms resolve to the same file as
their normalised spelling, so it is cosmetic — but a fence this strict should
probably reject `""` and `"."` segments in the same `all(...)` that rejects
`".."` (`:115`).

### Minor 5 — the structural test is file-wide, not function-scoped

`test_judgements.py:461–470` reads the whole source and `re.search`es for the
literal `= validate_judgement(row)` and `evidence.append(`, then compares
offsets. It does not assert the two are in the same function (they are —
`:306` and `:316` in `ingest_judgements`), and a comment containing the literal
would satisfy it. `src.count("evidence.append(") == 1` also would not see a
`from evidence import append` writer. Adequate for the mutants it was built to
kill; a stricter version would parse the function body.

### Minor 6 — the byte class is the one refusal class outside the isolating table

`long-note.md` still emits two reasons —
`spec: 201 bytes (limit 200); spec: invalid path` — because 201 `d`s are neither
≤ 200 bytes nor a `docs/…` path. The contract asks the table to name each class
alone, and the byte class is not a table row. It is nonetheless discriminating
where it lives (`:229–242`): only the byte rule emits `"201 bytes"`, and the
companion assertion that a 200-byte value raises *no* byte error is what kills
the `>` → `>=` mutant (confirmed, mutant H). A `spec="docs/" + "d"*196` row in
the table would isolate it properly.

### Minor 7 — `..md` is an accepted judgement filename

`JUDGEMENT_PATH_RE`'s stem class includes `.`, so
`docs/reviews/plan-judgements/..md` validates and ingests. No traversal follows:
the class forbids `/`, and `jdir.glob("*.md")` is non-recursive, so the name
always denotes a real file inside the judgements directory. Cosmetic.

## Verdict

**APPROVED.** Both pa5 MAJORs are fixed and each fix is now guarded by a
discriminating test: the arity arm is the sole refusal for the two new fixtures
and its deletion lands both rows; `judgement_path` is a field of the assembled
row, validated by a rooted class and the byte rule immediately before the single
`append()`, and the 243-byte prose filename that got through P6 is refused with
the field named. All three pa5 minors are closed. Eleven mutants — the four new
ones and P6's seven — all die. Red before green reproduces (6 failed / 120
passed on P6's implementation). Every contracted check is green; the
`pre-commit` exit 1 is task-branch queue staleness, proven by base being exit 0.
The commit convention holds: one commit, byte-identical subject, both trailers,
files inside `touches` plus `docs/MAP.md` by rule and `evidence.py` by P6's
`touches` via the prescribed cherry-pick. The seven minors are all inside the
fence, not through it, and none of them puts a byte of free text in the store.

plan_defect: wrong-fact — the isolated arity pair is green on P6, not red
