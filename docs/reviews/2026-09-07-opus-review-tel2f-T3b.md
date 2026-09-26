---
plan_defect: none
mutants_total: 17
mutants_killed: 14
mutants_outside_named: 10
reviewer: opus
majors: null
minors: 8
---
# Opus gate — seat run tel2f, task T3b — APPROVED

## Summary

All five MAJORs of the tel2 T3 gate are closed, and each closure is held by an
assertion I could show red. The three acceptance checks are green on a fresh
clone with `--rebuild` (`evidence-unit> 378 passed in 8.17s`, `unit` through
`ok 488`, `lint` exit 0), `pytest tests/evidence -q` gives `377 passed, 1
skipped`, `ruff check`/`ruff format --check` are clean, `docs/MAP.md` is
current and `tasks.py --root . check` is silent. `migrate_reviews.py . --check`
on the clone's live `docs/reviews` prints

```
checked: 168; would change: 141
exit=1
```

(168 `*opus-review*.md` files at the branch's base 68f5d75, of 182 files in
`docs/reviews/`; the two 2026-09-07 gate reviews written after this clone was
taken are not in it — the number matches the commit body's paste exactly, and
the tree is unchanged afterwards: `git status --porcelain` empty).

The seven mutants this section names are all killed, including the five that
survived the previous round. Ten further mutants of my own: seven killed, three
survived — and those three are exactly the three MINORs the section explicitly
records as "not owed here" (`O1` the bare `N killed` fallback, `O2` the
`(none)` heading form, `O4` the runs fence's `realpath`).

Beyond the section's own tests I ran the migration over the whole live corpus
in a scratch copy: 141 of 182 files change, **zero lose their final newline**,
and for every changed file the bytes from the closing `---` fence onward are
byte-identical to the original. MAJOR-2 is closed on the corpus, not only on
the fixtures.

One factual note for T3M, not a finding: the item-5 fix changes no live-corpus
value. The corpus's single `### Minors` heading
(`2026-09-06-opus-review-pb3a-P3Ab.md:323`) is followed by a numbered list of
real minors, not by `none`, so it still reads `minors: null` — which is what
the contract says for that shape. The heading fix is nonetheless real and its
fixture discriminates both named mutants.

Eight MINORs, none blocking. Six are carried from the previous review (five of
them the section itself defers); two are new and small.

## Contract items

| # | contract item (section, taken literally) | met | evidence |
|---|---|---|---|
| 1 | `80-seat-driver.bats` starts from main's copy; the three tests read the observations exactly with `grep -- ' record-check '`, keeping `[ "${#lines[@]}" -eq N ]` with N = 1, 1, 2; the `sort` stays where it was | yes | `tests/unit/80-seat-driver.bats:157-159, 190-192, 226-228`; the base..HEAD diff of the file is exactly three hunks, 20 lines, starting from `run cat`/`run sort` (main's text) |
| 1b | each test additionally asserts exactly one line `--store $BATS_TEST_TMPDIR/ev ingest reviews <repo> <runs>` | yes (position untested here) | `:160-162, 193-195, 229-231`; "exactly one" and the content pinned, "trailing" not (MINOR-2) |
| 1c | mutant O6 (a third `factory_record_check` in the loop) → the count assertion goes red | yes | `not ok 1 … nix-build loop`, `line 227: [ "${#lines[@]}" -eq 2 ]' failed` |
| 1d | mutant "drop the `ingest_reviews` call" → the trailing-line assertion goes red | yes | `not ok 4/5/6` in 80 (`line 161/194/231: [ "${#lines[@]}" -eq 1 ]' failed`) and `not ok 76/77` in 84 |
| 1e | the commit body names the file, the reason and both mutant runs | yes | `git log -1`, "Item 1 — tests/unit/80-seat-driver.bats" paragraph plus both mutant blocks |
| 2 | the migration splices into the original string; every byte after the block is returned unchanged, the trailing newline included | yes | `pkgs/evidence/migrate_reviews.py:145-153` (`_line_offset` + `text[:fence] + … + text[fence:]`); live corpus: 141 changed, `lost-final-newline 0`, `body-differs 0` |
| 2b | a file without a final newline stays without one | yes (untested) | true by construction at `:150`; no fixture exercises it (MINOR-3) |
| 2c | the six fixtures end with a newline; the fixture diff shows only the added byte | yes | `git diff 072491a..HEAD -- tests/evidence/fixtures/` — `block-five-keys.md`, `h1-no-markers.md`, `legacy-h1.md`, `migrated.md` show only `\ No newline at end of file` → `body`; `h1-markers.md` already had it; `majors-none.md` is the item-5 fixture change |
| 2d | row 12 asserts the bytes after the closing `---` are identical before and after, and a blocked fixture grows by exactly the added key lines | yes | `tests/evidence/test_migrate_reviews.py:198-205` (`_after_close` at `:78-84`, and `len(blocked_mig) - len(blocked_orig) == len(b"reviewer: opus\nmajors: null\nminors: null\n")`) |
| 2e | mutant: rejoin through `"\n".join(splitlines())` → red | yes | `AssertionError: block-five-keys.md`, `assert b'…body' == b'…body\n'`, `test_migrate_reviews.py:200` |
| 3 | row 19's fixture is a docs review for `(r1, K1)` **and** a seat `runs/r1/K1.review.md` for the same pair → two rows, one per `review_path`; the `K1`/`K1b` pair stays as a second case | yes | `tests/evidence/test_ingest_reviews.py:315-326` (the two-element `review_path` set, then the two-element `docs_paths` list) |
| 3b | mutant: key on `(run_id, key)` → one row → red | yes | `assert {'~/factory/r…K1.review.md'} == {'docs/review…K1.review.md'}`, `Extra items in the right set: 'docs/reviews/2026-09-06-opus-review-r1-K1.md'`, `test_ingest_reviews.py:316`; stdout `ingested 6 gate rows` |
| 4 | the fixture repo makes three commits (add, delete, re-add) so `git log --diff-filter=A` prints two lines; row 14 asserts `review_commit` is the original add's sha and `review_commit_ts` its time as UTC `Z` | yes | `test_ingest_reviews.py:74-106` (`_git_repo_readd`), `:207-209` (`== original_sha`, `!= readd_sha`, `== ORIGINAL_ADD_DATE`) |
| 4b | mutant: `lines[0]` → the re-add's sha → red | yes | `assert 'a4823bddddef…' == 'bd93defb1e5b…'` at `test_ingest_reviews.py:207` — the two shas prove the fixture really has two add commits |
| 4c | `ingest_reviews.py` changes only if item 4 demands it (the rule is already `lines[-1]`; say so) | yes | `pkgs/evidence/ingest_reviews.py` is byte-identical to T3's 072491a (absent from `git diff --stat 072491a..HEAD`); the body says so |
| 5 | a heading is `^#{1,6}\s+(major\|majors\|minor\|minors)\s*$` case-insensitively | yes | `pkgs/evidence/migrate_reviews.py:40` `_HEADING_RE`, used at `:64-65` |
| 5b | `majors-none.md` gains a `### Minors` heading followed by `None.` (keeping `## Majors` + `none`) → `majors: 0`, `minors: 0` | yes | `tests/evidence/fixtures/reviews-migrate/majors-none.md:3-6`; `test_migrate_reviews.py:137-138` |
| 5c | mutant: restrict to `##` → `minors: null` → red; drop `re.I` → red | yes | `assert 'minors: 0\n' in '…minors: null…'` at `:138`; `assert 'majors: 0\n' in '…majors: null…'` at `:137` |
| 6 | the body pastes the red of each new/changed assertion of items 1–5, the five mutant runs and the green counterparts | yes | `git log -1`: reds for items 1, 2 and 5 on the cherry-picked tree; items 3 and 4 shown red through their named mutants (which is what items 3 and 4 themselves ask for — "red (pasted)"), then seven mutant blocks and the green section. Two green lines are paraphrased rather than pasted (MINOR-8) |
| — | one commit, subject byte-exact, the two trailers, no board commit, the plan file untouched | yes | see Touches and commit |

## Red before green

**Item 1 — main's bats copy against the branch's `factory-integrate`** (the
section's Step 2 red; `git checkout 68f5d75 -- tests/unit/80-seat-driver.bats`,
then `nix develop -c bats tests/unit/80-seat-driver.bats`):

```
not ok 4 factory-integrate records one check observation per check it runs, at the integration head
# (in test file tests/unit/80-seat-driver.bats, line 158)
#   `[[ "$output" =~ ^--store\ $BATS_TEST_TMPDIR/ev\ record-check\ … ]]' failed
not ok 5 factory-integrate records a failed check as --fail and exits 1
# (in test file tests/unit/80-seat-driver.bats, line 187)
#   `[ "${#lines[@]}" -eq 1 ]' failed
not ok 6 factory-integrate records one observation per check in the nix-build loop, at the integration head
# (in test file tests/unit/80-seat-driver.bats, line 220)
#   `[ "${#lines[@]}" -eq 2 ]' failed
```

Byte-for-byte the body's paste. Restored → `ok 4`, `ok 5`, `ok 6`, and the
whole file green (`ok 1` … `ok 75`, plus `ok 76`/`ok 77` in
`84-factory-integrate-reviews.bats`).

**Items 2 and 5 — T3's implementation against the branch's tests**
(`git checkout 072491a -- pkgs/evidence/migrate_reviews.py`, then
`nix develop -c pytest tests/evidence/test_migrate_reviews.py -q`):

```
E  AssertionError: assert 'minors: 0\n' in '---\nreviewer: opus\nmajors: 0\nminors: null\n---\n# Opus gate — seat run r5, task K5 — APPROVED\n\n## Majors\nnone\n### Minors\nNone.\n'
E      AssertionError: block-five-keys.md
E      assert b'# Opus gate...ECTED\n\nbody' == b'# Opus gate...TED\n\nbody\n'
FAILED tests/evidence/test_migrate_reviews.py::test_migrate_null_and_none_counts
FAILED tests/evidence/test_migrate_reviews.py::test_migrate_idempotent_and_check
2 failed, 4 passed in 0.03s
```

Restored → `6 passed`. This is the exact red the section's item 2 and item 5
name, on the cherry-picked tree.

**Items 3 and 4** cannot go red on the cherry-picked tree — `streams.py` is
already keyed on `("review_path",)` and `_add_commit` already takes
`lines[-1]`, and the section says so ("Mutant: … → red (pasted)"). Their reds
are the mutants M19 and M14c below, both of which the previous gate showed
SURVIVING against T3's fixtures and both of which now fail. No test in this
diff passes for a reason a mutant cannot remove.

## Mutants

Named by the section: 7 instantiations, 7 killed. Tried beyond the section's
list: 10, of which 7 killed. Totals: 17 / 14 / 10.

| id | item | mutant | result |
|---|---|---|---|
| N1 | 1 | O6 — a third `factory_record_check "zzz" "$head" ok 0` in `factory-integrate`'s checks loop | KILLED — `not ok 1 … nix-build loop`, `line 227: [ "${#lines[@]}" -eq 2 ]' failed` |
| N2 | 1 | drop the `ingest_reviews \|\| logboth …` call | KILLED — `not ok 4/5/6` (80) and `not ok 76/77` (84) |
| N3 | 2 | rejoin through `new_lines = lines[:close] + additions + lines[close:]` / `"\n".join(new_lines)` | KILLED — `test_migrate_reviews.py:200`, `assert b'…body' == b'…body\n'` |
| N4 | 3 | `streams.py` `gate-verdict` key → `("run_id", "key")` | KILLED — `test_ingest_reviews.py:316`, `Extra items in the right set: 'docs/reviews/2026-09-06-opus-review-r1-K1.md'` |
| N5 | 4 | `_add_commit`: `lines[0]` instead of `lines[-1]` | KILLED — `test_ingest_reviews.py:207`, `assert 'a4823bdd…' == 'bd93defb…'` |
| N6 | 5 | `_HEADING_RE` restricted to `^#{2}\s+…` | KILLED — `test_migrate_reviews.py:138`, `assert 'minors: 0\n' in '…minors: null…'` |
| N7 | 5 | `_HEADING_RE` without `re.IGNORECASE` | KILLED — `test_migrate_reviews.py:137`, `assert 'majors: 0\n' in '…majors: null…'` |
| O7 | — | `_line_offset`: `range(index - 1)` (off by one line) | KILLED — `test_migrate_block_five_keys_appends` |
| O8 | — | `_prepend_block` returns `… + text.rstrip("\n")` | KILLED — `test_migrate_idempotent_and_check` |
| O9 | — | drop `"none."` from `_NONE_FORMS` | KILLED — `test_migrate_null_and_none_counts` (the new `### Minors`/`None.` fixture) |
| O10 | — | drop `"(none)"` from `_NONE_FORMS` | SURVIVED — `6 passed` (the previous review's MINOR-4, deferred by the section) |
| O11 | — | drop the bare `N killed` fallback (`_FALLBACK_MUTATION_RE` arm) | SURVIVED — `6 passed` (MINOR-3, deferred) |
| O12 | — | call `ingest_reviews` twice | KILLED — 3 `not ok` in 80 (the `ingest reviews` count pin bites) |
| O13 | — | runs fence: `os.path.abspath` instead of `os.path.realpath` | SURVIVED — `7 passed` (MINOR-5, deferred) |
| O14 | — | splice appends an extra `"\n"` after the closing fence | KILLED — `test_migrate_idempotent_and_check` |
| O15 | — | a second observation in the `FACTORY_CHECK_CMD` pass arm | KILLED — `not ok 4` (test 1's `-eq 1` bites) |
| O16 | — | a second observation in the `FACTORY_CHECK_CMD` fail arm | KILLED — `not ok 5` (test 2's `-eq 1` bites) |

O15/O16 exist because O6 only exercises the `nix build` loop; they prove the
`-eq 1` counts in the other two tests are load-bearing too, which is precisely
what MAJOR-1 said they no longer were.

The 33 mutants T3's table names against `ingest_reviews.py`, `tasks.py`,
`factory-integrate` and `test_tasks.py` were confirmed by the previous gate,
and those four files are byte-identical between 072491a and 044f284
(`git diff --stat 072491a..HEAD` lists none of them), so they are not re-run
here; the three rows the section re-points (12, 14, 19) are re-run above.

## Checks

Fresh clone of `task/T3b` at 044f284, base 68f5d75.

| command | exit | note |
|---|---|---|
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | 0 | `evidence-unit> 378 passed in 8.17s` |
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | 0 | through `ok 488 blocks files older than 7 days are reaped on each run` |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | 0 | `lint> Found 0 warnings and 0 errors.` |
| `nix develop -c githooks/pre-commit` | 1, then 0 | the only hunk is the board's queue block (`T3b` → `T3M`, derived from `~/factory/runs` since the seat committed); staged and re-run it exits 0. Exempt by the Global Constraints |
| `nix develop -c ruff check pkgs/evidence tests/evidence` | 0 | `All checks passed!` |
| `nix develop -c ruff format --check pkgs/evidence tests/evidence` | 0 | `76 files already formatted` |
| `nix develop -c python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | 0 | MAP current |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | 0 | silent |
| `nix develop -c pytest tests/evidence -q` | 0 | `377 passed, 1 skipped in 7.39s` |
| `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/84-factory-integrate-reviews.bats` | 0 | `ok 75` … `ok 77` |
| `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check` | 1 | `checked: 168; would change: 141`; `git status --porcelain` empty afterwards |
| live-corpus migration in a scratch copy of `docs/reviews` | 0 | `migrated: blocks added 119, keys added 66, unchanged 0, skipped legacy 27`; probe: `unchanged 41, changed 141, lost-final-newline 0, body-differs 0` |

No check is red.

## Touches and commit

`git diff 68f5d75..HEAD --stat` — 20 files, 1573 insertions, 12 deletions. The
diff carries the whole of T3 plus this round's fixes, as the section's Step 1
prescribes. Every file is inside the section's `touches`:
`pkgs/evidence/ingest_reviews.py`, `pkgs/evidence/migrate_reviews.py`,
`pkgs/evidence/tasks.py`, the six `reviews-migrate` fixtures, the four
`fixtures/runs/r1/K*.review.md`, `tests/evidence/test_ingest_reviews.py`,
`tests/evidence/test_migrate_reviews.py`, `tests/evidence/test_tasks.py`,
`tests/unit/80-seat-driver.bats` (in `touches` this round, for exactly the
stated purpose), `tests/unit/84-factory-integrate-reviews.bats`,
`tools/factory/seat/factory-integrate`. `docs/MAP.md` (±2 lines: `tests/evidence`
57 → 69, `tests/unit` 17 → 18) is the standing exemption. **No file outside.**
`docs/OPERATIONS.md` is absent from the diff — Step 1's `git checkout HEAD --`
did its job, and no board commit was made. The plan file is untouched.

Commit convention: exactly one commit, `044f284`. The subject is byte-identical
to the section's `commit subject` (compared programmatically against the
literal extracted from the plan: `IDENTICAL`, 228 bytes each, the two U+2014 em
dashes intact). Both trailers follow a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run tel2f)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

The body states the why for each of the five items, pastes the reds, seven
mutant runs and the greens — item 6 met.

For the landing merge (the orchestrator's job, not this gate's): T2b has since
landed on main at 328c505 with +237 lines in `tests/unit/80-seat-driver.bats`,
and this branch's base predates it. This commit's three hunks in that file are
confined to the bodies of "records one check observation per check it runs",
"records a failed check as --fail and exits 1" and "records one observation per
check in the nix-build loop"; nothing else in the file is touched.

## Findings

**MINOR-1 — `_line_offset` counts only `\n` while its index comes from `splitlines()`, so a block containing any other line terminator makes the splice land past the closing fence.**
`pkgs/evidence/migrate_reviews.py:103-111` and `:148`

```python
def _line_offset(text, index):
    pos = 0
    for _ in range(index):
        nl = text.find("\n", pos)
```

`close` at `:117-121` is an index into `text.splitlines()`, which also splits on
`\x0b \x0c \x1c \x1d \x1e \x85    `. Probe in the clone:

```
crafted \x0c-in-block -> keys 2
'---\nreviewer: opus\nnote: a\x0cb\n---\nmajors: null\nminors: null\n# Opus gate — …'
```

The two added keys land **after** the closing `---`, i.e. inside the body — the
very thing item 2 forbids. Not reachable on today's corpus: over all 182 files
in `docs/reviews/`, `splitlines()` and `\n`-counting agree for every one, and
the live run changed no body byte. No test covers it. `text.split("\n")`
throughout would remove the class.

**MINOR-2 — item 1's "exactly one *trailing* line" is pinned as "exactly one line", not as the last line.**
`tests/unit/80-seat-driver.bats:160-162` (and `:193-195`, `:229-231`)

```
  run grep -- ' ingest reviews ' "$log"
  [ "${#lines[@]}" -eq 1 ]
  [[ "${lines[0]}" == "--store $BATS_TEST_TMPDIR/ev ingest reviews $src $root/runs" ]]
```

`grep` says nothing about position, so a `factory-integrate` that ingested
reviews *before* the checks would still pass these three tests. Ordering is
pinned only in `tests/unit/84-factory-integrate-reviews.bats:67-68`
(`run tail -n 1 "$log"`), which is why this is a MINOR and not a gap: the
observation exists, just in the other file.

**MINOR-3 — "a file without a final newline stays without one" is stated and untested.**
`pkgs/evidence/migrate_reviews.py:150`; all six fixtures now end with a newline

True by construction (`text[fence:]` is returned verbatim), and the change that
made the six fixtures newline-terminated is what item 2 asked for — but it also
removed the only inputs that would have exercised the no-newline branch. A
seventh fixture without a trailing newline would close it.

**MINOR-4 (carried, still open) — the bare `N killed` mutation fallback is untested.**
`pkgs/evidence/migrate_reviews.py:35, 78-80`

```
O11 drop the bare N-killed fallback: SURVIVED — 6 passed
```

The section records this as not owed here. It remains the common corpus form.

**MINOR-5 (carried, partly closed) — the `(none)` heading form is untested.**
`pkgs/evidence/migrate_reviews.py:36`

```
O9  drop the 'none.' form:  KILLED — test_migrate_null_and_none_counts
O10 drop the '(none)' form: SURVIVED — 6 passed
```

The new `majors-none.md` closes `None.`; `(none)` is still uncovered. Deferred
by the section.

**MINOR-6 (carried, still open) — the runs fence's symlink resolution is untested.**
`pkgs/evidence/ingest_reviews.py:201-204`

```
O13 runs fence: abspath instead of realpath: SURVIVED — 7 passed
```

Deferred by the section.

**MINOR-7 (carried, unchanged) — three previous-round MINORs stand untouched.**
`pkgs/evidence/ingest_reviews.py:241`, `pkgs/evidence/tasks.py:1045`

`review_path` for a seat row is still synthesised as
`~/factory/runs/<run>/<KEY>.review.md` (forced by T1's prefix fence at
`streams.py:338`); the section's named functions `parse_review`,
`parse_seat_review`, `ingest` are still `_doc_row`, `_seat_verdict`,
`_build_rows`; the H1-verdict rule is still nested under `if has_block:`, so a
blockless post-`front_matter_from` file with a `REWORK` H1 is never flagged.
`ingest_reviews.py` and `tasks.py` are byte-identical to T3, so this is a
statement of record, not a regression.

**MINOR-8 — two of the commit body's green pastes are paraphrases, and one is a mid-run line.**
`git log -1 044f284`

```
$ nix build .#checks.x86_64-linux.unit -L --no-link
(exit 0; every bats test ok)

$ nix build .#checks.x86_64-linux.lint -L --no-link
(exit 0)

$ nix develop -c githooks/pre-commit
All checks passed!
```

Item 6 asks for "the three checks' last lines". Two are summarised rather than
pasted, and `All checks passed!` is ruff's line from the middle of the hook's
output, not the hook's verdict — on a fresh clone today the hook exits 1 until
the regenerated queue block is staged (see Checks). Both checks are genuinely
green; only the paste is loose.

## Verdict

**APPROVED.** All five MAJORs of `docs/reviews/2026-09-07-opus-review-tel2-T3.md`
are closed, item by item:

- **MAJOR-1** — closed. `80-seat-driver.bats` restarts from main's copy; the
  three tests count `record-check` observations exactly (1, 1, 2) and pin the
  single `ingest reviews` line. O6 now dies (`line 227: [ "${#lines[@]}" -eq 2 ]'
  failed`), and so do O15/O16 in the two arms O6 does not reach. The file is in
  this section's `touches` and the body explains it.
- **MAJOR-2** — closed. The splice keeps every byte after the block; the six
  fixtures carry a final newline; row 12 asserts both the body bytes and the
  exact growth. Proven on the live corpus: 141 files changed, 0 lost a final
  newline, 0 changed a body byte. The named mutant dies.
- **MAJOR-3** — closed. Row 19's fixture is now a docs review and a seat review
  for the same `(r1, K1)`; keying on `(run_id, key)` drops the docs row and the
  test fails, naming the missing `review_path`.
- **MAJOR-4** — closed. The fixture repo adds, deletes and re-adds the review;
  `lines[0]` yields the re-add's sha and the assertion fails with both shas
  printed.
- **MAJOR-5** — closed. The heading rule is `^#{1,6}\s+(major|majors|minor|minors)\s*$`
  with `re.I`; `majors-none.md` carries `## Majors`/`none` and
  `### Minors`/`None.`; both named mutants die.
- **MINOR-7 of that review** (the body pastes neither red nor green) — closed;
  the body now carries three reds, seven mutant runs and the greens.

`plan_defect: none`. Seventeen mutants tried, fourteen killed; the three
survivors are the three the section itself defers. Eight MINORs, none blocking.
