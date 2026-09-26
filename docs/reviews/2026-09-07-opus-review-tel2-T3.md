---
plan_defect: implementer
plan_defect_secondary: vacuous
mutants_total: 39
mutants_killed: 33
mutants_outside_named: 6
reviewer: opus
majors: 6
minors: 7
---
# Opus gate — seat run tel2, task T3 — REJECTED

## Summary

The section's substance landed and works end to end: the completed review block
and its five new lint arms, `migrate_reviews.py`, `ingest_reviews.py` behind the
`evidence ingest reviews` delegation, and the `factory-integrate` hook. All
three acceptance checks are green on a fresh clone (`evidence-unit`, `unit`,
`lint`, each with `--rebuild`), 378 pytest cases pass, both new bats cases run
inside `unit` (`ok 293`, `ok 294`), `ruff check`/`ruff format --check` are clean,
`docs/MAP.md` is current and `tasks.py check` is silent. The CLI smoke over the
live corpus prints `ingested 170 gate rows (docs/reviews: 166, H1 parsed 139,
blocks 20, legacy 27; runs: 4)`, and `migrate_reviews.py . --check` prints
`checked: 166; would change: 139`, exits 1, lists the files and writes nothing —
the shape Step 4 asked for, counts shifted by the two reviews added today.

Five MAJORs stand. One is a rule-5 breach that also weakens an existing pin: the
seat edited `tests/unit/80-seat-driver.bats` (a T2 file) outside `touches` and
explained it nowhere in the commit body, and the edit it made turns two
"exactly N observations" assertions into truncated reads — a spurious third
check observation now survives. One is a body-bytes violation: the migration
strips the final newline from every file that already has a block (20 files in
the live corpus), against "the H1 and body untouched". Two are named mutants
that survive: row 19's `(run_id, key)` keying and row 14's `review_commit`
producer. One is a stated counting rule the code narrows: only `## Major(s)` /
`## Minor(s)` headings are read, so the corpus's `### Minors` is missed.

Two of the five are the plan's own doing (row 19's fixture cannot discriminate
its named mutant; row 14 gives no fixture that separates the first log line from
the last), and the section still carries the errata-9 wrong fact in the
Operator's step 4. The primary class is nevertheless `implementer`: MAJOR-1,
MAJOR-2 and MAJOR-5 are contracts the section states plainly and the seat did
not meet.

Process facts recorded, not counted against the seat: the seat's FACTORY-NOTES
line was literally `...` and the driver still accepted the block
(`status=done`, one commit); `docs/OPERATIONS.md`'s two-line change is entirely
inside `<!-- tasks:begin -->…<!-- tasks:end -->`, which the Global Constraints
exempt; `docs/MAP.md` is the other standing exemption. `githooks/pre-commit`
exits 1 on a fresh clone today only because that same queue block has since
moved on (`T3` → `T3M`, derived from `~/factory/runs`); with the regenerated
block staged it exits 0.

## Contract items

| # | contract (section, taken literally) | met | evidence |
|---|---|---|---|
| 1 | block keys are exactly the nine names; the block never carries a verdict | yes | `pkgs/evidence/tasks.py:83-93` `REVIEW_BLOCK_KEYS`; `verdict:` refused as `unknown key verdict` (`test_check_unknown_key`) |
| 2 | unknown key → `tasks: review {name}: unknown key {k}`, on every block file whatever its date | yes | `tasks.py:1073-1078`; rule sits inside `if has_block:` with no date gate |
| 3 | duplicate key → `duplicate key {k}`; a helper re-reads the block's lines; `_split_front_matter`'s tuple API unchanged | yes | `tasks.py:262-275` `_block_keys`; `tasks.py:1079-1080`; `_split_front_matter` signature untouched in the diff |
| 4 | `majors`/`minors`/the three mutants keys: non-negative integer or the literal `null`, else `{k} must be an integer or null` | yes | `tasks.py:1059-1070`; `test_check_counts_must_be_integer_or_null` |
| 5 | `reviewer` outside `opus\|sonnet\|deepseek\|fable\|unknown` → `reviewer {v} not in …` | yes | `tasks.py:94` `REVIEWER_ENUM`; `tasks.py:1071-1076` |
| 6 | on a file dated ≥ `front_matter_from` whose H1 has the shape with WORD outside APPROVED\|REJECTED → `H1 verdict {WORD} not in APPROVED \| REJECTED` | partly | `tasks.py:99-101, 1046-1057` — correct for block files, but the check is nested under `tasks.py:1045 if has_block:`, so a blockless file with a REWORK H1 is never flagged (MINOR-6) |
| 7 | `plan_defect` required only from `front_matter_from` (D9); files before it without a block stay silent | yes | `tasks.py:1081-1085`; `test_check_plan_defect_scope` (2026-09-05 silent, 2026-09-08 errors) |
| 8 | `migrate_reviews <repo> [--check]` over `<repo>/docs/reviews/*opus-review*.md` in name order | yes | `pkgs/evidence/migrate_reviews.py:146-150` (`sorted(...glob(...))`) |
| 9 | a block file gains only its missing keys; existing keys and order untouched | yes | `migrate_reviews.py:98-130`; `test_migrate_block_five_keys_appends` pins the five in place |
| 10 | **the H1 and body untouched** | **no** | `migrate_reviews.py:129-130` joins with `"\n"` and drops the file's final newline — 20 live files change beyond the block (MAJOR-2) |
| 11 | a `REVIEW_RE` first line gets a block prepended, H1 first after the block | yes | `migrate_reviews.py:83-95`; `test_migrate_counts_markers_and_mutations` asserts the H1 at index 7 |
| 12 | any other first line → skipped, counted | yes | `migrate_reviews.py:143`; `skipped legacy 1` asserted |
| 13 | never writes `plan_defect` / `plan_defect_secondary` | yes | no such literal in the additions; `assert "plan_defect" not in markers` |
| 14 | marker line: ≤3 leading spaces, optional decoration, MAJOR/MINOR case-insensitively, optional `-N`/` N`, not followed by a letter | yes | `migrate_reviews.py:24-28`; `## Majors` excluded, `**major (reject)**` and `  - MINOR 4:` included |
| 15 | no marker + a heading line whose text is `Major`/`Majors`/`Minor`/`Minors` followed within two lines by `none`/`(none)`/`None.` → 0 | **no** | `migrate_reviews.py:60` matches only `## …`; probe: `'## Minors' -> 0`, `'### Minors' -> None`, `'# Minors' -> None`. The section's own Facts count `### Minors` 1 in the corpus (MAJOR-5) |
| 16 | mutation counts: the `N/N killed` family first, else the first `(\d+)\s+killed` → killed only | yes (untested) | `migrate_reviews.py:31-35, 69-76`; the fallback arm has no test (MINOR-3) |
| 17 | output: `would change: <file>` per file under `--check`; summary `checked: <total>; would change: <N>`; `--check` exits 1 when N>0 | yes | live run: 139 `would change:` lines then `checked: 166; would change: 139`, `exit=1`, `git status --porcelain` empty |
| 18 | a real run prints `migrated: blocks added A, keys added K, unchanged U, skipped legacy L` and exits 0 | yes | `migrate_reviews.py:186-190`; asserted by `test_migrate_skips_legacy_h1` |
| 19 | CLI `evidence [--store S] ingest reviews [--runs-root DIR] <repo> <runs-dir>` via `ingest_reviews.main`, subparser `reviews` | yes | `pkgs/evidence/evidence.py:37` table entry (pre-existing); smoke run printed the ingest line, exit 0 |
| 20 | `<repo>/docs/reviews/` must exist; `<runs-dir>` must resolve under `--runs-root` or equal it, else exit 2 **before any write** | yes | `ingest_reviews.py:201-204, 262-272`; `test_runs_root_fence` asserts exit 2 and no `derived/gates.jsonl` |
| 21 | one row per docs review and per `<runs-dir>/*/*.review.md`, written with `replace_stream` to `derived/gates`; exit 1 on a refusal | yes | `ingest_reviews.py:274-280` |
| 22 | stdout `ingested {n} gate rows (docs/reviews: {r}, H1 parsed {h}, blocks {b}, legacy {l}; runs: {d})` | yes | `ingest_reviews.py:283-286`; live line quoted in Summary |
| 23 | the body is never stored: only the block, the H1, the name, the hash and `git log` | yes | `ingest_reviews.py:148-183`; `test_ingest_counts_and_body_fence` (a `sk-or-v1-abc` body ingests, no row value carries it) |
| 24 | doc-row producers: run/key from the H1 else the file-name rule; chain_root; round_of; reviewer; route claude; model; verdict map; counts; plan_defect(_secondary); gate_tokens/wall_s None; review_path; review_sha256; review_commit(_ts) = **the last line** of the add-commit log, `%cI` → UTC `Z` | mostly | all asserted by `test_block_review_row` / `test_blockless_and_legacy_reviews` except the "last line" rule, which no fixture discriminates (MAJOR-4, `ingest_reviews.py:119`) |
| 25 | seat-row producers: run_id ← directory, key ← stem, reviewer deepseek, route openrouter, model None, verdict map (rework→rejected, none→`none`), counts None, **review_path ← the real path**, review_commit(_ts) None, round/chain via `round_of`/`chain_root` | mostly | `ingest_reviews.py:230-243`; `review_path` is synthesised as `~/factory/runs/<run>/<key>.review.md`, not the real path (MINOR-1 — forced by T1's `review_path` prefix fence, `streams.py:338`) |
| 26 | `factory-integrate`: a local `ingest_reviews()` after the summary and before the fast-forward print, `FACTORY_EVIDENCE_CMD` else `factory_py …`, `${EVIDENCE_STORE:+--store …}`, called as `ingest_reviews \|\| logboth …`, `overall_rc` unchanged | yes | `tools/factory/seat/factory-integrate:191-201`, placed between `logboth "head: $head"` and the fast-forward comment |

## Red before green

A fresh clone of `task/T3` with the base's `pkgs/evidence/tasks.py` and
`tools/factory/seat/factory-integrate` checked out and the two new modules
deleted, against the branch's tests — the section's Step 2 commands:

```
$ nix develop -c pytest tests/evidence/test_tasks.py -q -k 'rework or integer_or_null or duplicate_key or unknown_key or plan_defect_scope or five_line_block or reviewer_enum'
FAILED tests/evidence/test_tasks.py::test_check_rejects_rework_verdict
FAILED tests/evidence/test_tasks.py::test_check_counts_must_be_integer_or_null
FAILED tests/evidence/test_tasks.py::test_check_reviewer_enum - assert False
FAILED tests/evidence/test_tasks.py::test_check_duplicate_key - assert False
FAILED tests/evidence/test_tasks.py::test_check_unknown_key - assert False
FAILED tests/evidence/test_tasks.py::test_check_plan_defect_scope - assert no...
6 failed, 5 passed, 116 deselected in 0.30s

$ nix develop -c pytest tests/evidence/test_migrate_reviews.py tests/evidence/test_ingest_reviews.py -q
E   StopIteration
ERROR tests/evidence/test_migrate_reviews.py - StopIteration
ERROR tests/evidence/test_ingest_reviews.py - StopIteration

$ nix develop -c bats tests/unit/84-factory-integrate-reviews.bats
not ok 1 factory-integrate ingests reviews after a successful integration
#   `[ "$output" = "--store $BATS_TEST_TMPDIR/ev ingest reviews $src $root/runs" ]' failed
not ok 2 factory-integrate still exits 0 when the reviews ingest fails
#   `[[ "$output" == *"evidence: could not record reviews"* ]]' failed
```

Green on the branch as committed: `377 passed, 1 skipped` for
`nix develop -c pytest tests/evidence -q`; `ok 1`/`ok 2` for the new bats file.

Row 7 (`test_read_reviews_five_line_block`) passes on the base too. That is
correct — the section marks its mutant column `—` and calls it a regression
pin — so it is not counted as a vacuous test.

## Mutants

Named by the section: 33 instantiations, 31 killed, 2 survived. Tried beyond
the section's list: 6, of which 2 killed. Totals below: 39 / 33 / 6.

| id | section row | mutant | result |
|---|---|---|---|
| M1 | 1 | admit `REWORK` in `REVIEW_SHAPE_RE`'s allowed words | KILLED — `assert False` at `test_tasks.py:3056` |
| M2 | 2 | counts accept any string | KILLED — `test_tasks.py:3088` |
| M3 | 3 | reviewer accepts any value | KILLED — `test_tasks.py:3128` |
| M4 | 4 | duplicate keys stay last-wins | KILLED — `test_tasks.py:3148` |
| M5 | 5 | unknown keys accepted | KILLED — `test_tasks.py:3168` |
| M6 | 6 | drop the date condition on `plan_defect` | KILLED — `assert not True`, `test_tasks.py:3189` |
| M8a | 8 | count inline mentions (drop the line anchor) | KILLED — `test_migrate_reviews.py:93` |
| M8b | 8 | swap killed/total | KILLED — `'…mutants_killed: 14…' == '…mutants_killed: 12…'` |
| M8c | 8 | anchor the marker regex at column 0 | KILLED — `assert 'minors: 1\n' in '…minors: null…'` |
| M8d | 8 | drop `re.I` | KILLED — `assert 'majors: 1\n' in '…majors: null…'` |
| M9 | 9 | write `0` for no markers | KILLED — `assert 'majors: null\n' in '…majors: 0…'` |
| M10a | 10 | overwrite existing block keys | KILLED — `test_migrate_reviews.py:184` |
| M10b | 10 | add `plan_defect: none` | KILLED — `test_migrate_reviews.py:93` |
| M11 | 11 | migrate the legacy H1 | KILLED — `assert 'skipped legacy 1' in 'migrated: blocks added 1, … skipped legacy 0'` |
| M12a | 12 | restamp (rewrite unchanged files) | KILLED — `assert 1 == 0` at `test_migrate_reviews.py:185` |
| M12b | 12 | write under `--check` | KILLED |
| M13 | 13 | the migration writes `reviewer: claude` (a value the lint refuses) | KILLED — `test_migrate_reviews.py:93` |
| M14a | 14 | verdict producer: not lowercased | KILLED |
| M14b | 14 | `chain_root` producer: `chain_root = key` | KILLED |
| M14c | 14 | `review_commit` producer: `lines[0]` instead of `lines[-1]` | **SURVIVED — 7 passed** |
| M14d | 14 | `review_sha256` producer: hash the H1 only | KILLED |
| M15 | 15 | use the H1 only (drop the file-name fallback) | KILLED |
| M16a | 16 | any weight (`b` weighs 2) | KILLED — `SB4b: ('fix', 3) == ('fix', 2)` |
| M16b | 16 | strip `a` (any trailing a–d is a fix round) | KILLED — `T10a: ('fix', 2) == ('first', 1)` |
| M16c | 16 | treat b/c/d as a fix letter unconditionally | KILLED — `T10b: ('fix', 2) == ('first', 1)` |
| M17a | 17 | map `rework` to `unknown` | KILLED — `assert 'unknown' == 'rejected'` |
| M17b | 17 | skip the round/chain computation for `.review.md` rows | KILLED |
| M18 | 18 | check the runs fence after writing | KILLED — `assert 0 == 2` at `test_ingest_reviews.py:228` |
| M19 | 19 | key the gates stream on `(run_id, key)` | **SURVIVED — 7 passed** |
| M20 | 20 | miscount the blocks | KILLED — `assert 'blocks 2' in '… blocks 4 …'` |
| M21 | 21 | store `first` in the row | KILLED — `assert 1 == 0` (the stream fence refuses the extra field) |
| M22 | 22 | drop the ingest call | KILLED — `not ok 1`, `not ok 2` |
| M23 | 23 | bare call, no `\|\|` guard | KILLED — `not ok 2` |
| O1 | — | drop the bare `N killed` mutation fallback | SURVIVED — 6 passed |
| O2 | — | drop the `(none)` / `None.` heading forms | SURVIVED — 6 passed |
| O3 | — | refuse the literal `null` in the counts | KILLED — `test_tasks.py:3087` |
| O4 | — | drop `realpath` from the runs fence | SURVIVED — 7 passed |
| O5 | — | record the failed check observation twice | KILLED |
| O6 | — | record a spurious third check observation | **SURVIVED — `ok 1 factory-integrate records one check observation per check it runs`** |

M19 in detail. Repointing `streams.py`'s `gate-verdict` key from
`("review_path",)` to `("run_id", "key")` leaves every test green, and the
collision is silent: with one `docs/reviews/2026-09-06-opus-review-r1-K1.md`
and the four `runs/r1/K*.review.md` fixtures,

```
ingested 5 gate rows (docs/reviews: 1, H1 parsed 1, blocks 0, legacy 0; runs: 4)
rc 0 rows 4 [('r1','K1','openrouter'), ('r1','K2','openrouter'),
             ('r1','K3','openrouter'), ('r1','K4','openrouter')]
```

— five rows written, four readable, the docs row dropped. The section's chosen
discriminator (the `K1`/`K1b` pair) cannot catch this: `K1` and `K1b` are
distinct under both keyings.

M14c in detail. `_add_commit` (`ingest_reviews.py:98-120`) takes `lines[-1]`,
the earliest add commit, exactly as the section states. Every fixture repo has a
single commit, so `lines[0]` and `lines[-1]` coincide and the rule is untested.

## Checks

| command | exit | note |
|---|---|---|
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | 0 | `evidence-unit> 378 passed in 7.43s` |
| `… evidence-unit … --rebuild` | 0 | |
| `nix build .#checks.x86_64-linux.unit -L --no-link` | 0 | `ok 293 factory-integrate ingests reviews after a successful integration`, `ok 294 … still exits 0 when the reviews ingest fails` |
| `… unit … --rebuild` | 0 | |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | 0 | |
| `… lint … --rebuild` | 0 | |
| `nix develop -c githooks/pre-commit` | 1, then 0 | the only hunk is the queue block (`T3` → `T3M`, derived from `~/factory/runs` since the seat committed); staged and re-run it exits 0. Exempt by the Global Constraints |
| `nix develop -c ruff check pkgs/evidence tests/evidence` | 0 | `All checks passed!` |
| `nix develop -c ruff format --check pkgs/evidence tests/evidence` | 0 | `76 files already formatted` |
| `nix develop -c treefmt` | 0 | `formatted 113 files (0 changed)` |
| `python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | 0 | MAP current |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | 0 | silent |
| `nix develop -c pytest tests/evidence -q` | 0 | `377 passed, 1 skipped` |
| `nix develop -c bats tests/unit/80-seat-driver.bats` | 0 | all pass |
| `nix develop -c python3 pkgs/evidence/migrate_reviews.py . --check` | 1 | `checked: 166; would change: 139`; 139 `would change:` lines; tree unchanged |
| `evidence.py … ingest reviews … . tests/evidence/fixtures/runs` | 0 | `ingested 170 gate rows (docs/reviews: 166, H1 parsed 139, blocks 20, legacy 27; runs: 4)` |

No check is red on the section's own terms.

## Touches and commit

Diff `e0b80e2..072491a`, 21 files. Inside the section's `touches`: the two new
modules, the three test files, the ten fixtures, the new bats file, `tasks.py`
and `factory-integrate` — 19 of 21. `docs/MAP.md` is the standing exemption.

`docs/OPERATIONS.md` (2 lines) is the board's queue block and is confined to the
`<!-- tasks:begin -->…<!-- tasks:end -->` markers — by rule, not a deviation.

`tests/unit/80-seat-driver.bats` (13 lines) is **outside `touches` and outside
both exemptions**, and the commit body says nothing about it. It is a T2 file:
T2 ran in the same wave and also edits it, so T2's landing will have to merge
over these three hunks. What the edit does: at `:159` and `:190`
`run cat "$log"` becomes `run head -n 1 "$log"`, and at `:226`
`run sort "$log"` becomes `run head -n 2 "$log"`, each with a two- or
three-line comment saying the reviews ingest now trails the recorder log. The
`[ "${#lines[@]}" -eq 1 ]` at `:191` and `[ "${#lines[@]}" -eq 2 ]` at `:227`
survive textually but no longer bound anything — see MAJOR-1.

Commit convention: exactly one commit, `072491a`. Subject is byte-identical to
the section's (verified by `diff` against the literal, `od -c` confirms the two
U+2014 em dashes at 342 200 224). Both trailers are present after a blank line
(`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 …`,
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`). No board commit;
the plan file is untouched. The body states the why but **pastes neither the
red nor the green** (MINOR-7).

## Findings

**MAJOR-1 — `tests/unit/80-seat-driver.bats` is edited outside `touches`, unexplained, and the edit disarms two existing pins.**
`tests/unit/80-seat-driver.bats:226-227`

```
-  run sort "$log"
+  # The two check observations lead the recorder log (the checks loop sorts
+  # names, so lint then unit) and the reviews ingest (added by T3) trails them,
+  # so read the head of the log.
+  run head -n 2 "$log"
   [ "${#lines[@]}" -eq 2 ]
```

`head -n 2` can never emit more than two lines, so `[ "${#lines[@]}" -eq 2 ]`
no longer means "exactly two check observations were recorded". Proof — mutant
O6, a spurious third `factory_record_check "zzz" "$head" ok 0` inside the checks
loop of `tools/factory/seat/factory-integrate`:

```
MUTANT O6 record a third check observation in the two-check case: SURVIVED (rc=0)
   . ok 1 factory-integrate records one check observation per check it runs, at the integration head
```

Under the base's `run sort "$log"` the same mutant makes `${#lines[@]}` three
and the assertion fails. The same truncation applies at `:190-191`. A narrower
edit that keeps the count (for example filtering the recorder log to
`record-check` lines) was available. The commit body does not mention the file
at all, so rule 5's escape does not apply, and T2 edits this same file in this
wave — the merge must reconcile these hunks knowingly.

**MAJOR-2 — the migration changes the body: every already-blocked review loses its final newline.**
`pkgs/evidence/migrate_reviews.py:129-130`

```
    new_lines = lines[:close] + additions + lines[close:]
    return "\n".join(new_lines), "keys", len(additions)
```

`splitlines()` drops the trailing `\n` and the join never restores it. The
section states "existing keys and their order untouched; the H1 and body
untouched". Probe over the real corpus in the clone (`migrate_file` in memory,
nothing written):

```
files that would lose their final newline: 20
  2026-09-06-opus-review-cr21-CR2r3b.md keys
  2026-09-06-opus-review-pa10-P10.md keys
  … (18 more, every file that already carries a block)
  2026-09-07-opus-review-tel1bf-T1b.md keys
```

T3M's commit would carry those 20 no-newline-at-end-of-file diffs. The
idempotence test (row 12) cannot see it: every fixture under
`tests/evidence/fixtures/reviews-migrate/` is itself written without a final
newline, so the second run is byte-identical for the wrong reason.

**MAJOR-3 — the named mutant of row 19 survives, and the collision it hides is silent.**
`pkgs/evidence/streams.py:315-318` (the key) / `tests/evidence/test_ingest_reviews.py:236-273`

Repointing the `gate-verdict` key to `("run_id", "key")` leaves all seven
ingest tests green:

```
MUTANT M19 key the gates stream on (run_id, key): SURVIVED (rc=0)
   . 7 passed in 0.19s
```

The failure mode it admits is a dropped row, not an error: with a docs review
for `(r1, K1)` and the seat's `runs/r1/K1.review.md`, the ingest reports
`ingested 5 gate rows` while `evidence.read` returns 4, the docs row gone. No
test asserts the total row count in a repo where a docs review and a seat review
share `(run_id, key)` — and that is precisely the shape of the live corpus,
where `docs/reviews/*-opus-review-<run>-<KEY>.md` and
`~/factory/runs/<run>/<KEY>.review.md` routinely name the same pair.

**MAJOR-4 — the named mutant of row 14's `review_commit` producer survives.**
`pkgs/evidence/ingest_reviews.py:119`

```
    sha, _, ts = lines[-1].partition("\t")
```

```
MUTANT M14c producer: review_commit = the first log line: SURVIVED (rc=0)
   . 7 passed in 0.18s
```

`_git_repo` (`tests/evidence/test_ingest_reviews.py:45-67`) always makes exactly
one commit, so `lines[0] == lines[-1]` and "the last line … (the add commit)" —
the rule the section names, and the reason the Facts call it "the add commit,
not the gate-review commit" — is never exercised. A file added, deleted and
re-added yields two lines in the live repo.

**MAJOR-5 — the "none" heading rule reads only `## `-level headings.**
`pkgs/evidence/migrate_reviews.py:58-60`

```
        headings = ("major", "majors") if cls == "major" else ("minor", "minors")
        for i, ln in enumerate(lines):
            if ln.strip().lower() not in {f"## {w}" for w in headings}:
```

The section says "the body has **a heading line** whose text is
`Major`/`Majors`/`Minor`/`Minors`", and its own Facts enumerate `### Minors` 1
alongside `## Minors` 11. Probe in the clone:

```
'## Minors'    -> 0
'### Minors'   -> None
'# Minors'     -> None
'## Majors'    -> 0
```

That file migrates to `minors: null` where the contract says `minors: 0`, and
T3M would land the wrong value with no way to tell it from a genuinely
uncounted file. No fixture covers any level but `##`.

**MINOR-1 — a seat row's `review_path` is synthesised, not real.**
`pkgs/evidence/ingest_reviews.py:241`

```
            row["review_path"] = f"~/factory/runs/{run}/{key}.review.md"
```

The section says `review_path ← the real path`. Under a non-default
`--runs-root` the stored value names a file that does not exist. The
implementation's hand is largely forced: T1's schema
(`pkgs/evidence/streams.py:338`) declares
`"review_path": ("path", ("docs/reviews/", "~/factory/runs/"), 200)`, so a real
temp path would be refused. Recorded as a plan-side conflict, not an implementer
fault; `tests/evidence/test_ingest_reviews.py:207` pins the synthesised form.

**MINOR-2 — the section's named functions do not exist.**
`pkgs/evidence/ingest_reviews.py`

Step 3 names `round_of`, `parse_review(path, repo)`, `parse_seat_review(path)`,
`ingest(store, repo, runs_dir, runs_root)`, `main`. Only `round_of` and `main`
are there; the rest are `_doc_row`, `_seat_verdict` and `_build_rows`, all
private. Nothing depends on the names, but errata 6 speaks of
`parse_seat_review`'s round fields and a later task looking for it will not find
it.

**MINOR-3 — the bare `N killed` mutation fallback is stated and untested.**
`pkgs/evidence/migrate_reviews.py:35, 73-75`

```
MUTANT O1 drop the bare-'N killed' mutation fallback: SURVIVED (rc=0)
   . 6 passed in 0.02s
```

The Facts count `N killed` 30 in the corpus against `N/N killed` 4 — the
untested arm is the common one.

**MINOR-4 — the `(none)` and `None.` forms are stated and untested.**
`pkgs/evidence/migrate_reviews.py:36`

```
MUTANT O2 drop the (none)/None. heading forms: SURVIVED (rc=0)
```

Only the bare `none` appears in a fixture (`majors-none.md`).

**MINOR-5 — the runs fence's symlink resolution is untested.**
`pkgs/evidence/ingest_reviews.py:201-204`

```
MUTANT O4 drop realpath from the runs fence: SURVIVED (rc=0)
   . 7 passed in 0.20s
```

`test_runs_root_fence` uses a plainly outside path; a symlink under the root
pointing out of it is never tried.

**MINOR-6 — the H1-verdict rule is scoped to block files only.**
`pkgs/evidence/tasks.py:1045` (`if has_block:`) enclosing `:1046-1057`

The section says "on **any file** dated on or after `front_matter_from` whose H1
has the … shape". A blockless 2026-09-07 file with a `— REWORK` H1 gets the
`no front-matter block` error but never the `H1 verdict REWORK` one. The
section's own test row 1 uses a block file, so the gap is untested either way.

**MINOR-7 — the commit body pastes neither the red nor the green.**
`git log -1 072491a`

The body states the why in six lines and stops. The Global Constraints' TDD
clause and the gate's own commit rule ask for the red and the green output in
the body; T1b's landing commit carried them.

## Verdict

**REJECTED.** Five MAJORs: the unexplained out-of-`touches` edit to
`tests/unit/80-seat-driver.bats` that also disarms two existing observation
pins; the migration's silent removal of the final newline from all 20
already-blocked reviews, against the "body untouched" contract; and three
contract points the tests do not hold — the `(run_id, key)` keying mutant
(silent row loss), the `review_commit` "last line" producer, and the `##`-only
heading rule that misreads the corpus's `### Minors`.

`plan_defect: implementer` — MAJOR-1, MAJOR-2 and MAJOR-5 are contracts the
section states plainly. `plan_defect_secondary: vacuous` — row 19's named
discriminating fixture (`K1`/`K1b`) cannot distinguish the mutant it is named
against, and row 14's single-commit fixture cannot separate the first log line
from the last, which is what let MAJOR-3 and MAJOR-4 through.

Two plan-side items to fix in the section before the fix round, neither charged
to the seat: the Operator's step 4 predicts `unchanged: 164; would change: 0`
while the Interfaces specify `checked: <total>; would change: <N>` (errata 9 —
the live shape is `checked: 166; would change: 139` today, `checked: 166;
would change: 0` after T3M); and `review_path ← the real path` for seat rows
contradicts T1's `review_path` prefix fence, so the section should say
`~/factory/runs/<run>/<KEY>.review.md`.
