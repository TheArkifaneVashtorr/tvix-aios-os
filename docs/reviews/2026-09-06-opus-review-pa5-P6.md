# Opus gate — seat run pa5, task P6 — REJECTED

## Summary

Branch `task/P6` in `/home/dalhaka/factory/ws/pa5/P6`, base `91dcc5f`, head
`23767f8`, one commit, reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-pa5-P6`.
Every run used a `--store` under that scratch directory; `/var/lib/evidence`
was never touched.

The fence itself is good. I drove the CLI by hand over 32 cases against a
`git init`-ed fixture repo and every contracted refusal fired with the
contracted reason; the prose below the closing `---` never reaches the store;
`evidence.append()` is the only writer and is byte-identical to base;
`judged_ts` comes from git for a committed file and from the mtime otherwise
(both proven); a torn last line in `plans.jsonl` does not break the
`(plan, revision)` idempotency; `docs/MAP.md` reproduces byte for byte; ruff,
`pytest tests/evidence`, `evidence-unit` and the `lint` check are all green;
red-before-green reproduces exactly as contracted.

Two MAJORs stop it.

1. **A named mutant survives.** Deleting the "exactly 14 entries" check from
   `scores` leaves the entire `tests/evidence` suite green (121 passed). The
   contracted case (9) — a 13-entry `scores` — is killed by the `total` ≠ sum
   check, not by the count check, so the count fence is untested. With the
   check removed, a 13-score row lands in the store.
2. **A 272-byte free-text string reaches the store.** `judgement_path` is
   assembled from the globbed filename and never passes `validate_judgement`,
   so a judgement file whose *name* is prose is stored verbatim, unbounded.

Both are one-line fixes. Neither is a design error; the plan section
under-specified both.

## The fence (table)

Every row run by hand with
`python3 pkgs/evidence/evidence.py --store <tmp> ingest judgements <repo>` on a
fixture repo built from the six committed fixtures (`GIT_COMMITTER_DATE`
pinned to `2026-09-06T05:39:00 +0000`).

| # | case | expected | observed | exit |
|---|------|----------|----------|------|
| 1 | `good.md` | one row, `ingested <path>` | `ingested docs/reviews/plan-judgements/good.md`, 1 row | 0 |
| 2 | run twice | still one row, `skipped … (present)` | `skipped docs/reviews/plan-judgements/good.md (present)`, 1 row | 0 |
| 3 | `good` + `second-revision` | two rows, rev 0 and 1 | `[(…helm-home.md, 0), (…helm-home.md, 1)]` | 0 |
| 4 | `long-note.md` (`spec` 201 B) | refused, byte count, no row | `refused …long-note.md: spec: 201 bytes (limit 200); spec: invalid path`, 0 rows | 1 |
| 5 | a 200-byte value accepted | accepted | **no field class admits one** — see note below; at `validate_judgement` a 200-byte value raises no byte error, a 201-byte one does | — |
| 6 | `extra-field.md` | `unknown field errata`, no row | `refused …extra-field.md: unknown field errata`, 0 rows | 1 |
| 7 | `bad-decision.md` | refused, no row | `decision: invalid (dispatch\|revise\|revise-exhausted\|panel-short)` | 1 |
| 8 | `body-only.md` | `no front-matter block` | `refused …body-only.md: no front-matter block` | 1 |
| 9 | `total` ≠ sum | refused | `total 40 does not equal scores sum 38` | 1 |
| 10 | 13 scores | refused | `scores: must be exactly 14 entries (got 13)` | 1 |
| 11 | 15 scores (total 41 = sum) | refused | `scores: must be exactly 14 entries (got 15)` | 1 |
| 12 | a score of 4 | refused | `scores: entries must be integers 0-3` | 1 |
| 13 | `revision: -1` | refused | `revision: invalid integer (>= 0)` | 1 |
| 14 | `self_score: null` | accepted | one row, `"self_score": null` | 0 |
| 15 | `self_score: 43` | refused | `self_score: invalid (0-42 or null)` | 1 |
| 16 | `judges` with 4 entries | refused | `judges: invalid (0-3 of sonnet\|opus\|deepseek\|fable)` | 1 |
| 17 | `judges_dropped: [whatever]` | refused | `judges_dropped: invalid (implementer\|reviewer\|whole)` | 1 |
| 18 | `author: dsh:` (empty id) | refused | `author: invalid (fable \| hand \| dsh:<model>)` | 1 |
| 19 | `author: dsh:DeepSeek` | refused | same | 1 |
| 20 | `plan: docs/../../etc/passwd` | ? | **ACCEPTED**, stored verbatim — the contract's own regex `^docs/[A-Za-z0-9._/-]{1,190}$` admits `..` (minor 1) | 0 |
| 21 | `plan: /docs/x.md` | refused | `plan: invalid path` | 1 |
| 22 | a required key missing (`threshold`) | ? | **refused** — `missing threshold`. Judged against §5.4: the design shows all fourteen keys in every record and the row shape needs all fourteen, so requiring presence is correct and stricter than the letter of "No other key" | 1 |
| 23 | duplicate keys (`revision` twice) | ? | **ACCEPTED**, last wins — the row carried `revision: 7` (minor 2) | 0 |
| 24 | 200 bytes of multibyte text | refused as bytes, not chars | `spec: 201 bytes (limit 200)` for 103 chars; and at the fence, 100 × `é` (200 B) raises no byte error while 101 × `é` (202 B) and 67 × `世` (201 B) do — **the limit is bytes** | 1 |
| 25 | a value continued on the next line | ? | **refused** `no front-matter block` — a line inside the block without a `:` is not a block | 1 |
| 26 | closing `---` missing | refused | `no front-matter block` | 1 |
| 27 | missing directory | `no judgements under <path>`, exit 0 | `no judgements under …/docs/reviews/plan-judgements`, 0 rows | 0 |
| 28 | one refused + one good | good ingested, exit 1, refused appends nothing | `ingested …good.md` on stdout, `refused …bad-decision.md: …` on stderr, 1 row | 1 |
| 29 | two files, same `(plan, revision)`, one run | — | `ingested …aaa.md` then `skipped …bbb.md (present)`, 1 row (the in-run `existing.add` works) | 0 |

Note on row 5: the 200-byte cap is never the binding constraint. `plan` and
`spec` are the only free-ish strings and their class caps them at
`docs/` + 190 = **195 bytes**; every other field is an enum, an int or a
bracketed list. I put a 200-byte value into each of the fourteen fields in turn
and all fourteen were refused by their class check, never by the byte fence.
So no string wider than 195 bytes can enter the store *through a block field* —
stronger than the contract asks. The byte fence is still exercised
non-vacuously at the `validate_judgement` level and the `> 200` → `>= 200`
mutant dies there.

## The row and the writer

The `good.md` row, verbatim from `plans.jsonl`:

```json
{"author":"fable","decision":"dispatch","effort":"max","judged_ts":"2026-09-06T05:39:00Z","judgement_path":"docs/reviews/plan-judgements/good.md","judges":["sonnet","sonnet","opus"],"judges_dropped":[],"kind":"plan-judgement","plan":"docs/superpowers/plans/2026-09-06-helm-home.md","revision":0,"scores":[3,2,3,3,2,3,3,3,3,3,2,2,3,3],"self_score":40,"spec":"docs/superpowers/specs/2026-09-04-helm-home-design.md","tasks":9,"threshold":34,"total":38,"ts":"2026-09-06T06:51:20Z","v":1,"words":6140}
```

- Exactly 19 keys: the 14 fields + `kind` + `judged_ts` + `judgement_path` +
  `append()`'s own `v` and `ts`. Nothing else.
- **Prose never reaches the store.** `good.md`'s body carries
  `Errata: none known.` and a `Judge reasons:` sentence about the six-row floor
  and the packet. Grepping `plans.jsonl` for `Errata`, `six-row floor`,
  `Judge reasons` and `packet` → `False` for all four.
- `judged_ts` from git, proven both ways: with the working-tree mtime forced to
  `2000-01-01` on a committed file the row reads `2026-09-06T05:39:00Z` (the
  commit time); in a tree with no `.git` the same file yields
  `2000-01-01T00:00:00Z`.
- `judgement_path` is repo-relative (`docs/reviews/plan-judgements/good.md`).
- **`append()` is the only writer.** `git diff 91dcc5f..HEAD -- pkgs/evidence/evidence.py`
  removes zero lines — `append()` and its flock are untouched. Grepping
  `judgements.py` for writers finds exactly one:
  `pkgs/evidence/judgements.py:277: evidence.append(store, "plans", row)`. No
  `open(…, "a")`, no `json.dump`, no direct write.
- **A torn last line does not break idempotency.** Appending
  `{"kind": "plan-judgement", "plan": "docs/x.md", "revi` to `plans.jsonl` and
  re-running printed `skipped … (present)` and left the file at one good row
  plus the torn fragment.
- Mode is `0640` on the created stream (asserted by the test as well).
- Structural injection is not possible: a filename containing a newline and a
  JSON object is escaped by `json.dumps` and stays one line (probed).

## Tests and mutants

`tests/evidence/test_judgements.py` has 15 tests covering the nine contracted
cases; every one uses `tmp_path` for both the store and the fixture repo, and
the file contains no reference to `/var/lib/evidence` or `EVIDENCE_STORE`.
`ruff check` and `ruff format --check` are clean over `pkgs/evidence` and
`tests/evidence`.

Eight mutants applied in a scratch copy of the clone, seven killed:

| mutant | result | killed by |
|---|---|---|
| the file's prose copied into a `body` key (allowlist relaxed so the row builds) | **killed** (3 failed) | `test_good_ingests_one_row_with_every_field_from_git`, `test_extra_field_is_refused_as_unknown`, `test_no_free_text_key_is_interpreted` |
| the `(plan, revision)` skip dropped | **killed** | `test_rerun_is_idempotent_and_prints_skipped` — `assert 'skipped … (present)' in 'ingested …'` |
| `> 200` → `>= 200` | **killed** | `test_201_byte_string_is_refused_and_200_is_accepted:222` |
| unknown keys ignored | **killed** (2 failed) | `test_extra_field_is_refused_as_unknown`, `test_no_free_text_key_is_interpreted` |
| `dsh:` prefix-only regex (`{0,64}`) | **killed** | `test_every_author_arm_is_accepted_and_empty_dsh_id_refused:276` |
| the `total` = sum check skipped | **killed** | `test_total_must_equal_scores_sum:256` |
| the `decision` class check removed | **killed** (2 failed) | `test_bad_decision_is_refused`, `test_every_decision_arm_is_accepted` |
| **the exactly-14 `scores` count check removed** | **SURVIVES** | nothing — 15 passed on the file, **121 passed on all of `tests/evidence`** |

## Checks

All in the clone, `nix develop -c` throughout.

| check | result |
|---|---|
| `ruff check pkgs/evidence tests/evidence` | `All checks passed!` — exit 0 |
| `ruff format --check pkgs/evidence tests/evidence` | `20 files already formatted` — exit 0 |
| `pytest tests/evidence -q` | `121 passed in 4.44s` — exit 0 |
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | `121 passed in 4.33s` — exit 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | `All checks passed!` — exit 0 |
| `nix develop -c githooks/pre-commit` | exit 1 — **expected, not a finding**: the only failure is `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`, and the regeneration is exactly `P6` leaving the queue. `tasks.py` judges "landed" from `git log` subjects (`landed_subjects`, `tasks.py:189`, `:360`), so on a task branch the queue necessarily goes stale the moment the task's own commit exists. The same hook is exit 0 on base `91dcc5f`, and it was exit 0 for the implementer because it ran before the commit existed. Including the board change would have been the breach, not omitting it. |
| `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0 — MAP.md reproduces byte for byte; tree clean afterwards |
| `python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06` | silent, exit 0 |
| `evidence.py --help` | lists `ingest` alongside `tasks`/`repomap`; `ingest --help` lists `judgements`; the dispatch at `evidence.py:332–340` mirrors `tasks` exactly (`here` inserted on `sys.path`, `--store` forwarded), and `judgements.py`'s only module-level import of a sibling is `import evidence`, which resolves both under the dispatch and when the file is run directly. The packaged CLI (`flake.nix:678`) execs from `${./pkgs/evidence}`, so the sibling is present there too. |
| `pkgs/evidence/SCHEMA.md` | one new row for the `plans` stream naming all 14 fields, `judged_ts` (first git commit time, RFC3339 Z) and `judgement_path`, with the `plan-judgement` kind and the writer. Complete. |

Commit convention: exactly one commit; subject byte-identical to the plan's
`**commit subject:**`; both trailers present, `Generated-By` then
`Co-Authored-By`, matching `tools/factory/seat/factory-brief:89–90`; every
touched file is in `touches` except `docs/MAP.md`, which is in by rule; no board
commit; the `FACTORY-RESULT` block in `~/factory/runs/pa5/P6.result` is the
exact form.

## Red before green

`git show 91dcc5f:pkgs/evidence/evidence.py` over the branch tree with
`judgements.py` deleted, then this branch's tests:

```
../mut/tests/evidence/test_judgements.py:35: in <module>
    import judgements
E   ModuleNotFoundError: No module named 'judgements'
ERROR ../mut/tests/evidence/test_judgements.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.12s
```

Exactly the contracted red. Restored, the same file is 15 passed and the suite
121 passed.

## Findings

### MAJOR 1 — the exactly-14 `scores` fence is untested; the mutant survives the whole suite

`tests/evidence/test_judgements.py:259` (`test_scores_must_have_exactly_14_entries`)
uses a 13-entry list against the fixture's `total: 38`:

```python
def test_scores_must_have_exactly_14_entries():
    assert judgements.validate_judgement(base_fields()) == []
    thirteen = "[3,2,3,3,2,3,3,3,3,3,2,2,3]"
    assert judgements.validate_judgement(base_fields(scores=thirteen)) != []
```

That list sums to 35, not 38, so the assertion is satisfied by the
`total` ≠ sum error at `pkgs/evidence/judgements.py:188` and never reaches the
count check at `:169`. Deleting the count check

```python
        elif len(ls) != 14:
            errors.append(f"scores: must be exactly 14 entries (got {len(ls)})")
```

leaves `pytest tests/evidence -q` at **121 passed**, and the fence is really
gone — same fixture repo, same CLI, `total` set to the honest sum:

```
[HEAD-13scores-total35]   exit=1  refused …x.md: scores: must be exactly 14 entries (got 13)
[MUTANT-13scores-total35] exit=0  ingested …x.md
   row scores=[3, 2, 3, 3, 2, 3, 3, 3, 3, 3, 2, 2, 3] total=35 (13 entries)
```

A row with the wrong arity lands in `plans` and every downstream reader that
indexes rubric rows (P10's report joins scores to landings) reads a shifted
vector. The fix is one character in the fixture: make the 13-entry test use a
`total` equal to its own sum (35), so only the count check can refuse it — and
add the symmetric 15-entry case, which is likewise unrepresented.

### MAJOR 2 — `judgement_path` bypasses the fence: a 272-byte free-text string reached the store

`pkgs/evidence/judgements.py:250–276` builds the row's `judgement_path` from
the globbed filename:

```python
    for path in sorted(jdir.glob("*.md")):
        rel = path.relative_to(repo).as_posix()
        ...
        row = {
            "kind": "plan-judgement",
            **row_fields,
            "judged_ts": judged_ts(str(repo), rel),
            "judgement_path": rel,
        }
```

`rel` never passes through `validate_judgement`, so neither the 200-byte cap
nor a path class applies to it. A judgement file whose *name* is prose is
stored verbatim. One file, name 243 bytes, otherwise a byte-identical copy of
`good.md`:

```
exit= 0
stored judgement_path bytes: 272
stored judgement_path: docs/reviews/plan-judgements/2026-09-06-the operator said the broker leaked and the reason is that the seat guard interpolated the agent supplied file path into a reason string which is exactly the free text this fence exists to keep out of the telemetry store forever .md
```

This is the class of leak P6 exists to prevent — the telemetry design's rule is
that no declared field is free text and that a stored path is "rooted,
≤ 200" (`2026-09-05-telemetry-store-design.md:450`, `:484`). Structural
injection is not possible (a newline in a filename is JSON-escaped and the row
stays one line, probed), so the damage is content and length, not a torn
stream. The fix is one check beside the others: `judgement_path` must match a
rooted `^docs/reviews/plan-judgements/[A-Za-z0-9._-]{1,190}\.md$` and be
refused, not stored, when it does not — plus a test with a long, prose-shaped
filename.

### Minor 1 — `plan` and `spec` admit `..`

`pkgs/evidence/judgements.py:25`, `PLAN_PATH_RE = ^docs/[A-Za-z0-9._/-]{1,190}$`,
is the contract's own regex and it admits dot segments:
`plan: docs/../../etc/passwd` was ingested and stored verbatim (matrix row 20).
Nothing opens these paths today — only `judgement_path`, which comes from the
glob — so this is a latent hazard for the first reader that resolves `plan`
against the repo (P10). Worth a `..`-segment rejection when the class is next
touched.

### Minor 2 — duplicate keys in one block are accepted, last wins

`parse_front_matter` (`:74–89`) builds a plain dict, so a block with
`revision: 0` followed by `revision: 7` is accepted and the row carries
`revision: 7` (matrix row 23). Combined with `key.strip()`, an indented
continuation line that happens to contain a colon can silently replace a field.
Not contracted, and it cannot smuggle a non-allowlisted name, but a duplicate
key should be a refusal in a fence this strict.

### Minor 3 — the missing-directory line names the judgements directory, not the repo

`:242` prints `no judgements under <repo>/docs/reviews/plan-judgements` while
the contract's wording is `no judgements under <path>` where `<path>` is the
argument. Harmless; the test asserts only the prefix.

## Verdict

**REJECTED** on two MAJORs: a named mutant (the exactly-14 `scores` count
check) survives the entire `tests/evidence` suite, and `judgement_path` reaches
the store unvalidated — a 272-byte free-text string was stored, which is the
"numbers, never content" rule the whole task exists to hold. Everything else in
P6 is correct and well built: the allowlist, the byte fence, the class checks,
the `(plan, revision)` idempotency, the git/mtime `judged_ts`, the single
writer, the dispatch, SCHEMA.md, MAP.md, the commit convention and the red
before green all hold under direct examination.

Re-plan as P6b, small: (a) make the 13-entry `scores` test discriminating
(`total` = 35) and add the 15-entry case; (b) validate `judgement_path` against
a rooted pattern and a length bound inside `validate_judgement`, refusing the
file rather than storing the name, with a long prose-filename test; (c) while
in there, refuse duplicate keys and `..` segments. Keep everything else as it
stands.

plan_defect: missing-case — 13-score fixture sum-killable; judgement_path length class never specified
