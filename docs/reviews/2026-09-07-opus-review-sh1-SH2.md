---
plan_defect: none
mutants_total: 22
mutants_killed: 20
mutants_outside_named: 4
---
# Opus gate — seat run sh1, task SH2 — APPROVED

## Summary

The section's contract is met item for item. The git facts are hoisted above both
synthesising arms; a near miss or a missing result block over a branch that holds
commits is recorded `status=unreported` with the real count and `task_rc` 0; zero
commits and a missing `.factory-meta` still fall through to `failed`; the `.result`
gains a `derived:` label; the fence, the ingest, `SCHEMA.md` and the README carry
the new arm and the new nullable field; and `factory-brief` re-prints the four
template lines after REPO NOTES with a sentence that names neither the literal
label nor the existing test's unique phrase.

All three reds the section names reproduce verbatim against the base's
implementation files, and the three lines pasted in the commit body match what I
saw. All 18 mutants the section names were applied and every one turned its
named test red. The three acceptance checks (`unit`, `evidence-unit`, `lint`) are
green under `--rebuild`. Exactly one commit; the subject is byte-identical to the
section's; every file in the diff is inside the section's `touches` (plus
`docs/MAP.md` by the standing rule); the plan file and the board are untouched.

Confirmed on the orchestrator's two specific points: the driver launches **no**
second seat call — `dsh-openrouter` is invoked at exactly one site
(`tools/factory/seat/factory-task:212`) and the diff touches zero lines
containing `dsh-openrouter` (`git diff … -- tools/factory/seat/factory-task |
grep -c 'dsh-openrouter'` → `0`); and every new test is synthetic —
`FACTORY_ROOT="$BATS_TEST_TMPDIR/factory"` (`tests/unit/94-seat-harness.bats:47`),
no real seat log is opened (the `setup_file` guard at lines 16–40 is the verbatim
`ls -A1` snapshot idiom of `tests/unit/80-seat-driver.bats:17–39`), and the
pytest rows write only into `tmp_path` stores (`_store()` at
`tests/evidence/test_ingest_result.py:139`) — no reference to `/var/lib/evidence`
anywhere in the diff.

Two MINORs, both under-assertion rather than wrong behaviour, and one plan gap
the errata already named. Nothing rises to a MAJOR.

## Contract items

| # | contract (Interfaces, taken literally) | met | evidence |
|---|---|---|---|
| 1a | `head_sha`, `base_sha`, `actual_commits` computed immediately after the seat's exit line, before `extract_field` | yes | `tools/factory/seat/factory-task:225–230`, directly under the `seat exited` log at :218 and above the near-miss classifier at :233 |
| 1b | `actual_commits=` empty when `base_sha` empty, else `rev-list --count … \|\| true` | yes | `factory-task:227–230` — `actual_commits=` then `if [ -n "$base_sha" ]; then actual_commits=$(git -C "$ws" rev-list --count "$base_sha..task/$key" 2>/dev/null \|\| true)` |
| 1c | the two later assignments of `head_sha`/`base_sha` removed | yes | the diff deletes them from the CR3r preamble (former :283–284); `grep -c '^head_sha=' factory-task` → 1, `'^base_sha='` → 1 |
| 1d | the CR3r block reads the hoisted `actual_commits` | yes | `factory-task:322–325` — the local `actual_commits=$(git …)` is gone from inside `if [ -n "$base_sha" ]` |
| 2a | `synth=nearmiss` arm: `status=unreported exit_code=$exit_code`, `FACTORY-CHECKS none=not-run`, `FACTORY-COMMITS $actual_commits`, `derived="checks commits"` when the count is a number > 0 | yes | `factory-task:276–285` |
| 2b | `synth=none` arm: the same | yes | `factory-task:294–303` |
| 2c | the arm's own `notes_line` is kept | yes | `factory-task:275` (`result-misparse: $near_note`) and `:293` (`the seat produced no usable FACTORY-RESULT line; see $log`), both set outside the new `if` |
| 2d | empty or 0 count ⇒ arms unchanged (`failed`, `FACTORY-COMMITS 0`) | yes | `factory-task:286–290`, `:304–308`; row 3 and row 5 tests green |
| 2e | the `submit` arm is unchanged | yes | not in the diff — `factory-task:262–265` untouched |
| 3 | `case $status` gains `unreported) task_rc=0 ;;` before the `*)` fallback | yes | `factory-task:357`, between `failed) task_rc=2 ;;` (:356) and `*)` (:358) |
| 4 | `printf 'derived: %s\n' "$derived"` after `error_class:`, only when non-empty | yes | `factory-task:419–421`, immediately after `printf 'error_class: %s\n'` at :418 — but see MINOR-1 (the ordering is not pinned by a test) |
| 5a | CR3r demotions keyed on `done`, never see `unreported` | yes | `factory-task:325`, `:334`, `:339` — all three arms guarded `[ "$status" = "done" ]` |
| 5b | `factory_error_class` unchanged; `unreported` + `nearmiss\|none` ⇒ `no-result-line` | yes | `tools/factory/seat/factory-lib.sh` not in the diff; `factory-lib.sh:120` is still `if [ "$status" = "done" ]`; asserted at `tests/unit/80-seat-driver.bats:3376–3382` |
| 6 | `factory-brief`: blank line, the sentence, the four template lines byte-identical to the RULES block's, last in the output | yes | `tools/factory/seat/factory-brief:115,122–126`; live brief tail with `FACTORY_BRIEF_EXTRA` set ends `Your final four lines… / FACTORY-RESULT status=<done\|partial\|failed> / FACTORY-CHECKS <name>=<pass\|fail\|not-run> ... / FACTORY-COMMITS <n> / FACTORY-NOTES <one line>`; the label line occurs at brief lines 36 and 46 |
| 7a | the sentence must not contain `FACTORY-RESULT` | yes | `factory-brief:122` — the sentence says "a space after the label"; asserted at `94-seat-harness.bats:238` |
| 7b | the sentence must not repeat `no colon, no markdown` | yes | `grep -c` over the brief → 1, asserted at `94-seat-harness.bats:234–235` |
| 7c | without `FACTORY_BRIEF_EXTRA` nothing changes | yes | `factory-brief:114` guard unchanged; `94-seat-harness.bats:216–221` counts 4 |
| 8 | `factory-wave`: no change; prints `KEY status=unreported …`; exit stays non-zero | yes | not in the diff; asserted at `94-seat-harness.bats:301–303` |
| 9 | `streams.py` status enum + `"derived": ("null", ("list", ("enum", ("checks","commits")), 2))` | yes | `pkgs/evidence/streams.py:281–284`, `:296` |
| 10 | `ingest_result.py` `STATUS_WORDS` gains `unreported`; `derived` ← whitespace tokens, no line → `None` | yes | `pkgs/evidence/ingest_result.py:41`, `:283–286`, `:318` |
| 11 | `SCHEMA.md`'s `derived/tasks` row names `unreported` and `derived` | yes | `pkgs/evidence/SCHEMA.md:14–15` |
| 12 | README's `.result` paragraph gains `unreported` and `derived:` | yes | `tools/factory/seat/README.md:35–37` |
| 13 | nothing reads `derived` to decide anything | yes | `grep -rn '"derived"' pkgs/ tools/` (minus the stream names) returns only the declaration at `streams.py:296` and the assignment at `ingest_result.py:318` |

## Red before green

Base implementation files (`factory-task`, `factory-brief`, `streams.py`,
`ingest_result.py`) checked out at `1dbc2ec` under the branch's tests:

```
not ok 1 near miss with one commit completes an unreported block from the git facts
#   `[ "${lines[0]}" = "FACTORY-RESULT status=unreported exit_code=0" ]' failed
not ok 2 no result line at all with one commit completes the same unreported block
not ok 6 factory-brief re-prints the template after REPO NOTES when FACTORY_BRIEF_EXTRA is set
#   `[ "$template_lines" = "8" ]' failed
not ok 7 factory-brief's re-print sentence does not carry the literal label or repeat the phrase
#   `[ -n "$sentence" ]' failed
```

```
tests/evidence/test_ingest_result.py -k unreported
E       AssertionError: assert 'unknown' == 'unreported'
tests/evidence/test_streams_policy.py -k enum_arms_literal
E       At index 4 diff: 'unknown' != 'unreported'
tests/evidence/test_streams_policy.py -k derived_field
E       AssertionError: assert ['derived: undeclared field'] == []
```

All three reds the section's Step 2 names reproduce, and match the three lines
the commit body pastes. Restored to the branch: `bats
tests/unit/94-seat-harness.bats` → `ok 1 … ok 8`; `pytest tests/evidence -q` →
`403 passed, 1 skipped`; `bats tests/unit/80-seat-driver.bats` → 80 ok.

Rows 3, 4, 5, 8 (the `80-seat-driver` addition) and 9, 10 are green at base by
design — they are the controls and the pins on deliberately-unchanged code
(`factory-wave`, `factory_error_class`), and each is killed by its own named
mutant below, so none is vacuous.

## Mutants

18 named, all applied in a scratch copy and reverted; every one killed.

| # | mutant | test run | red line |
|---|---|---|---|
| 1a | arm keeps `FACTORY-COMMITS 0` | row 1 | `` `[ "${lines[2]}" = "FACTORY-COMMITS 1" ]' failed `` |
| 1b | `unreported) task_rc=2` | row 1 | `` `[ "$task_rc" -eq 0 ]' failed `` |
| 2 | hoist only the near-miss arm (revert `synth=none`) | row 2 | `` `[ "${lines[0]}" = "FACTORY-RESULT status=unreported exit_code=0" ]' failed `` |
| 3 | drop the `-gt 0` guard (`if true`) | row 3 | `` `[ "${lines[0]}" = "FACTORY-RESULT status=failed exit_code=0" ]' failed `` |
| 4 | apply the arm to every status (after the arms, before the defaults) | row 4 | `` `[ "${lines[0]}" = "FACTORY-RESULT status=done exit_code=0" ]' failed `` |
| 5 | treat an empty count as > 0 (`[ "${actual_commits:-1}" -gt 0 ]`) | row 5 | `` `[ "${lines[0]}" = "FACTORY-RESULT status=failed exit_code=0" ]' failed `` |
| 6a | drop the re-print | row 6 | `` `[ "$template_lines" = "8" ]' failed `` |
| 6b | print it before REPO NOTES | row 6 | `` `[ "$last_four" = "FACTORY-RESULT status=<done\|partial\|failed>\|…" ]' failed `` |
| 7a | repeat `no colon, no markdown` in the sentence | row 7 | `` `[ "$output" = "1" ]' failed `` |
| 7b | name `FACTORY-RESULT` in the sentence | row 7 | `` `[[ "$sentence" != *"FACTORY-RESULT"* ]]' failed `` |
| 8 | revert `head -n1` in `80-seat-driver.bats` | that test | `` `[ "$sentence_line" -lt "$template_line" ]' failed with status 2 `` / `[: 38\n48: integer expected` |
| 9a | `factory-wave` prints `unknown` outside the four words | row 9 | `` `[[ "$output" == *"K1 status=unreported …"* ]]' failed `` |
| 9b | `[ "$status" = done ] \|\| overall_rc=0` | row 9 | `` `[ "$status" -eq 1 ]' failed `` |
| 10 | add `unreported` to `factory_error_class`'s `done` guard | row 10 | `` `[ "$output" = "no-result-line" ]' failed `` (line 3377) |
| 11 | leave `unreported` out of the `streams.py` declaration | row 11 | `At index 4 diff: 'unknown' != 'unreported'` |
| 12 | declare `derived` as `("null", "id")` | row 12 | `assert ['derived: not a id'] == []` |
| 13a | leave `unreported` out of `STATUS_WORDS` | row 13 | `assert 'unknown' == 'unreported'` |
| 13b | default `derived` to `[]` | row 13 | `assert [] is None` (the `done.result` assertion) |

Four mutants the section did not name:

| # | mutant | outcome |
|---|---|---|
| O1 | seed `actual_commits=abc` (the errata's non-numeric count) | **killed** row 1 — and the probe answers the errata: the driver does not die. It logs `factory-task: line 276: [: abc: integer expected` to stderr, falls through to the `failed` arm, writes `FACTORY-COMMITS 0` and exits 2. Degrades, does not crash. |
| O2 | `derived="commits"` (drop an arm) | **killed** row 1 — `` `[[ "$output" == *"derived: checks commits"* ]]' failed `` |
| O5 | move `printf 'derived: …'` **above** `error_class:` | **survived** all 8 rows — see MINOR-1 |
| O7 | add a re-printed prose line containing the literal `FACTORY-RESULT` (not the template) | **survived** all 8 rows — see MINOR-2 |

`mutants_total` 22, `mutants_killed` 20, `mutants_outside_named` 4.

## Checks

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | **rc=0** — `ok 503 factory-wave reads the word from a fake factory-task's unreported result and chains on` |
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **rc=0** — `404 passed in 10.29s` |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **rc=0** (`--rebuild` first errored only because the derivation had never been built in this store; built, then rebuilt clean) |
| `nix develop -c ruff check pkgs/evidence tests/evidence` | rc=0 — `All checks passed!` |
| `nix develop -c ruff format --check pkgs/evidence tests/evidence` | rc=0 — `101 files already formatted` |
| `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc=0 / rc=0 — `docs/MAP.md` regenerates identical |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | rc=0, silent |
| `nix develop -c githooks/pre-commit` at HEAD | rc=1 — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` — see MINOR-3 |

## Touches and commit

Every one of the twelve files in `1dbc2ec..HEAD` is inside the section's
`touches`, with `docs/MAP.md` covered by the standing rule:

```
docs/MAP.md | pkgs/evidence/SCHEMA.md | pkgs/evidence/ingest_result.py
pkgs/evidence/streams.py | tests/evidence/fixtures/results/unreported.result
tests/evidence/test_ingest_result.py | tests/evidence/test_streams_policy.py
tests/unit/80-seat-driver.bats | tests/unit/94-seat-harness.bats
tools/factory/seat/README.md | tools/factory/seat/factory-brief
tools/factory/seat/factory-task
```

No file outside the list; no `Deviation:` line needed and none present.

`git rev-list --count 1dbc2ec..HEAD` → `1`. Subject byte-identical to the
section's (`cmp` of `git log -1 --format=%s` against `sed -n '355p'` of the plan,
stripped of its backticks → `SUBJECT BYTE-IDENTICAL`). Body states the why and
pastes the three red lines; the two trailers are the last two lines after a blank
line:

```
$
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sh1)$
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>$
```

`docs/OPERATIONS.md` is not in the diff (no board commit) and
`docs/superpowers/plans/2026-09-07-seat-harness-redesign.md` is untouched.

## Findings

**MINOR-1 — the `derived:` line's stated position is not pinned by any test.**
`tools/factory/seat/factory-task:419–421` writes `derived:` immediately after
`error_class:`, exactly as Interfaces item (4) states. But
`tests/unit/94-seat-harness.bats:139` asserts only `[[ "$output" == *"derived:
checks commits"* ]]` — a substring over the whole file. Mutant O5 (swap the
`derived:` block above `printf 'error_class: …'`) leaves all eight rows green:

```
=== MUTANT O5 : test ===
1..8
ok 1 … ok 8
=== MUTANT O5 rc=0 ===
```

A stated contract with no test. Harmless in practice — `ingest_result.py:284`
matches `^derived:` per line, so ordering carries no behaviour — but the pin the
section names is absent.

**MINOR-2 — test row 7's second half is asserted only over one line.**
The section's row 7 requires "no line of the re-print contains `FACTORY-RESULT`
except the template line itself". `tests/unit/94-seat-harness.bats:236–238`
locates only the `Your final four lines` sentence and checks that one string.
Mutant O7 — an extra re-printed prose line
`Do not decorate the FACTORY-RESULT block with markdown.` inserted between the
sentence and the template — survives all eight rows (`=== MUTANT O7 rc=0 ===`).
The narrower Interfaces sentence ("The sentence must not contain
`FACTORY-RESULT`") *is* met and tested (mutant 7b kills it); it is the row's
broader phrasing that is under-asserted.

**MINOR-3 — `githooks/pre-commit` is red at HEAD, for a structural reason, not
this change.** At `7e50f41` the hook exits 1 with
`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git
add docs/OPERATIONS.md and commit again`. Cause, verified: `tasks.py` judges a
task "landed" by its commit subject appearing in the git log
(`pkgs/evidence/tasks.py:227` `landed_subjects`, `:473` `if
task["commit_subject"] in landed`), so the SH2 commit's own subject drops SH2 out
of the derived queue and pulls SH3 in — the board block committed on `main`
cannot match. Two controls:

- base `1dbc2ec`, clean: `nix develop -c githooks/pre-commit` → **rc=0**.
- the same change cherry-picked `-n` onto `1dbc2ec` (staged, uncommitted — the
  exact state the section's Step 4 runs the hook in): **rc=0**,
  `render.test.mjs: all assertions passed`.

So the hook was green where the section tells the seat to run it, and its
post-commit redness reproduces on any correctly-executed task branch. Recorded as
process, not charged to the implementer; the three named acceptance checks are
green.

**MINOR-4 (plan gap, already on the errata) — no test row for a non-numeric
commit count.** The judgement's errata row 13
(`docs/reviews/plan-judgements/2026-09-07-seat-harness.md:36`) asked the section
to state the guard as a `case` and to add a row seeding the count as `abc`. The
section text was not revised, so it still says only "a number greater than 0",
and the seat wrote the natural spelling: `factory-task:276` and `:294` read
`if [ -n "$actual_commits" ] && [ "$actual_commits" -gt 0 ]; then`. Probe O1
shows the errata's feared failure mode does not occur — inside an `if` condition
the `[` failure is not fatal under `set -e`, so the driver degrades to `failed`,
`FACTORY-COMMITS 0`, exit 2 — but it does emit
`factory-task: line 276: [: abc: integer expected` on stderr, and no test covers
it. A gap the section itself carries; per the errata this is a plan defect to
name, not an implementer MAJOR, and the landed behaviour is safe.

No MAJORs.

## Verdict

**APPROVED.** Every numbered contract item is met at the cited line; the three
reds the section names reproduce against the base and match the commit body; all
18 named mutants die against their named tests; `unit`, `evidence-unit` and
`lint` are green under `--rebuild`; `ruff`, `repomap` and `tasks check` are
clean; the touches list holds with no deviation; one commit, byte-identical
subject, both trailers, plan and board untouched. The driver launches no second
seat call and every new test is synthetic. Four MINORs, all under-assertion or
plan-side; none is a behavioural defect.
