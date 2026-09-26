---
plan_defect: none
mutants_total: 31
mutants_killed: 27
mutants_outside_named: 4
---
# Opus gate — seat run sh3, task SH4 — APPROVED

## Summary

Branch `task/SH4` in `/home/dalhaka/factory/ws/sh3/SH4`, base `a2b758c`, head `d04664b`, one
commit, 12 files. Reviewed in a fresh clone at
`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/2e56f544-dc33-4c36-836e-c2b840c3e5fc/scratchpad/gate-sh3-SH4/gate-sh3-SH4`.

Every numbered item of the SH4 section is met. The three acceptance checks build green with
`--rebuild`; `ruff check`, `ruff format --check`, the MAP regeneration and `tasks.py check` are
clean. Red-before-green reproduces exactly the two reds the commit body pastes. All 27 mutants the
section names are killed (one, row 9's "demote cache-miss", only after respelling it to the cell its
own fixture actually exercises — see MINOR-6). Four mutants outside the named set survive; each
marks a stated contract with no fixture, none is a wrong behaviour, and they are recorded as MINORs.

No MAJOR. Thirteen MINORs, none gating.

The carried SH3r question — `tests/unit/94-seat-harness.bats` setting neither `FACTORY_EVIDENCE_CMD`
nor `EVIDENCE_STORE`, so the driver's ingest aimed at `/var/lib/evidence` — is answered under
"Checks": SH4's own end-to-end helper sets both, and the older helpers are blocked before any store
is opened by `evidence.py`'s runs-root guard. Nothing in this branch can reach the live store.

## Contract items

Interfaces, taken literally, in the section's order.

1. **`FACTORY_VERIFY_TIMEOUT` (seconds, default 1800), one budget per task.**
   `tools/factory/seat/factory-task:282` `verify_budget=${FACTORY_VERIFY_TIMEOUT:-1800}`, passed to
   `factory_verify_checks` at `:303`. Met.
2. **`FACTORY_VERIFY=0` skips verification, no `checks_verified:` line, the log says
   `verify: skipped (FACTORY_VERIFY=0)`.** `factory-task:278-279`; asserted by
   `tests/unit/94-seat-harness.bats:1807` (both the absent line and the log sentence). Met.
3. **`factory_record_check <name> <rev> ok|fail <dur> [<src>]`, default `seat-integrate`.**
   `factory-lib.sh:85` `local name=$1 rev=$2 verdict=$3 dur=$4 src=${5:-seat-integrate} flag`; the
   two call sites now pass `--src "$src"` (`:95`, `:98`). Pinned by
   `tests/unit/80-seat-driver.bats:261`. Met.
4. **`factory_latest_check <name> <rev>`** — `FACTORY_EVIDENCE_CMD` when set, else
   `factory_python3 …/evidence.py`, with `${EVIDENCE_STORE:+--store …} latest-check`.
   `factory-lib.sh:196-204`, byte for byte the stated form. Met.
5. **`factory_acceptance_names <plan> <KEY>`** — the section's `**acceptance:**` line, split on
   commas and whitespace, never the commit subject. `factory-lib.sh:209-217`; the discriminating
   fixture (a section whose subject names `helm-unit`) is `94-seat-harness.bats:1462`. Met.
6. **`factory_flake_checks <ws> <rev>`** — `nix eval --json "git+file://$ws?ref=$rev#checks.x86_64-linux"
   --apply builtins.attrNames`, one name per line, returns 1 and prints nothing on failure with the
   last 200 bytes logged. `factory-lib.sh:221-231`
   (`factory_log "nix eval checks failed: $(printf '%s' "$out" | tail -c 200)"`). Met.
7. **`factory_check_deferred <ws> <rev> <name> <toplevel-drv>`** — kvm or the toplevel drvPath, with
   the dry-run escape. `factory-lib.sh:272-286`. Met for every shape the section's rows exercise; the
   two arms are coded as mutually exclusive rather than as the stated OR — MINOR-4.
8. **`factory_verify_checks <ws> <rev> <budget-s> <name>…`, the five verdicts, the four srcs, the
   four-step order, `return 3` after a timeout, `<remaining>` from the loop start, each run verdict
   recorded with `seat-verify`.** `factory-lib.sh:297-360`. Steps in the stated order at `:308`
   (recorded), `:320` (eval), `:324` (absent), `:329` (deferred), `:338` (build). Met; the printed
   line carries `<duration_s>` only for the two `run` verdicts — MINOR-1.
9. **`factory-task`, between the extraction of the seat's lines and the synthesis arms.** The block
   sits at `factory-task:264-330`; `extract_field 'FACTORY-NOTES'` is `:259`, the first synthesis arm
   `:333`. Met.
10. **The name set = acceptance ∪ the seat's claimed passes, in that order.** `factory-task:284-299`;
    asserted by `94-seat-harness.bats:1573` (`checks_verified: unit=pass pre-commit=not-run:absent` —
    the acceptance name first, the claimed-only name after). Met, with the extra guard at `:281` —
    MINOR-2.
11. **`.result` lines after `touches_*`: `checks_verified`, `checks_verified_src`, `verify_s`,
    `checks_scope`, `checks_scope_files`, and `checks_scope_list` when dirty.**
    `factory-task:595-603`, immediately after the `touches_files` block at `:591-593`. Met.
12. **`checks_scope` dirty when the branch diff touches `flake.nix`, `tests` or `githooks` under the
    SH3 `/`-boundary rule.** `factory-task:313-328` (`factory_touches_covers "$p" "$scope_roots"`);
    the `tests2` and `githooks` fixtures are `94-seat-harness.bats:1711`. Met.
13. **SH2's `unreported` arm sets `checks_line` from `checks_verified` with every `not-run:*` folded,
    `none=not-run` only when empty.** `factory-task:331` (the fold), `:355` and `:370`
    (`factory_derived_checks_line`), `factory-lib.sh:259-266`. Asserted at
    `94-seat-harness.bats:1788` → `FACTORY-CHECKS unit=pass seat-vm=not-run`. Met.
14. **The demotion table, only on a status still `done` after CR3r; misreported outranks
    unverifiable; a clause per firing cell; `status=` rewritten in place; SH3's arm runs after and is
    outranked.** `factory-task:426-460`, placed after the commit-echo block that ends at `:424` and
    before SH3's touches block at `:462`. The four demoting cells are the case at `:438-441`; the
    precedence at `:448-452`; the in-place rewrite at `:457`. Every demoting cell has a fixture
    except `absent × fail` (MINOR-9); the checks-over-touches precedence has none (MINOR-11). Met.
15. **`factory_error_class`'s eighth argument.** `factory-lib.sh:110` adds `verify=${8:-}`; the
    `done` guard at `:125-131` and the final fallback at `:174-178` print `verify-timeout`, and the
    `case $demoted` gains the two arms at `:148-155` — after `touches`, before the tail patterns.
    `factory-task:561` passes `"$verify_flag"`. The five-row precedence table is
    `tests/unit/80-seat-driver.bats:3418-3431`. Met.
16. **`streams.py`: the three `ERROR_CLASSES` arms before `none`, after `touches-violation`; the
    `checks_verified` map class; `checks_scope`; `checks_scope_files`; `verify_s`.**
    `pkgs/evidence/streams.py:128-134` and `:301-321`. The map class is the stated tuple verbatim,
    key regex and cap 64 included. Met.
17. **`ingest_result.py`: `_parse_verified` (any violation → `None`, never a partial map),
    `checks_scope` by enum else `None`, the two ints, `checks_verified_src` and `checks_scope_list`
    never ingested.** `pkgs/evidence/ingest_result.py:134-153`, `:313-319`, `:368-371`. Met and
    asserted (`tests/evidence/test_ingest_result.py:645-679`, including
    `assert "checks_scope_list" not in row`).
18. **`SCHEMA.md`'s table.** `pkgs/evidence/SCHEMA.md:15-18` carries the map, the two enums, the two
    nullable ints and the three new `error_class` arms. Met.
19. **README: the `.result` lines, "What the driver verifies" under "## Running a wave", the table,
    `FACTORY_VERIFY_TIMEOUT`, `FACTORY_VERIFY`.** `tools/factory/seat/README.md:340-374`, under
    `## Running a wave (the low-level tool)` at `:285`. The table's cells match the section's
    outcome for outcome ("done" where the section writes "stands"). Met.

## Red before green

Base implementation files (`factory-task`, `factory-lib.sh`, `streams.py`, `ingest_result.py`)
checked out from `a2b758c` against the branch's tests, in
`…/scratchpad/gate-sh3-SH4/red`.

`nix develop -c bats tests/unit/94-seat-harness.bats` — 42 ok, 16 not ok (tests 43–58, exactly the
SH4 rows), with the exit-127 warning bats prints:

```
BW01: `run`'s command `… factory-lib.sh'; factory_verify_checks '…/wsdir' 'cccc…' 1800 unit lint
nosuch seat-vm host-core 2>/dev/null` exited with code 127, indicating 'Command not found'.
not ok 43 factory_verify_checks runs, defers, and records exactly the buildable checks
…
not ok 58 FACTORY_VERIFY=0 skips verification and logs verify: skipped
```

`nix develop -c bats tests/unit/80-seat-driver.bats`:

```
not ok 8 factory_record_check defaults src to seat-integrate and honours the fifth arg
not ok 77 factory_error_class classifies the tail patterns with the done/124/synth/demoted precedence
```

`nix develop -c pytest tests/evidence/test_ingest_result.py -q -k checks_verified`:

```
>       assert row["checks_verified"] == {"unit": "pass", "lint": "not-run:cache-miss"}
E       KeyError: 'checks_verified'
tests/evidence/test_ingest_result.py:655: KeyError
1 failed, 17 deselected
```

`nix develop -c pytest tests/evidence -q` → `24 failed, 408 passed, 1 skipped` (the three new
`error_class` arms and both `checks_scope` arms among them). Restored to HEAD: 58 ok in
`94-seat-harness.bats`, `433 passed` in `tests/evidence`. Both reds are the two the commit body
pastes, verbatim.

## Mutants

Applied in a scratch clone, one at a time, reverted with `git checkout -- .` between. All 27 named
mutants die.

| # | mutant | test | failing line |
|---|---|---|---|
| 1a | drop the attrNames step | row 1 | `[ "${lines[2]}" = "nosuch not-run:absent -" ]' failed` |
| 1b | drop the kvm rule | row 1 | `[ "${lines[3]}" = "seat-vm not-run:cache-miss -" ]' failed` |
| 1c | drop the drvPath rule | row 1 | `[ "${lines[4]}" = "host-core not-run:cache-miss -" ]' failed` |
| 1d | record with `seat-integrate` | row 1 | `[[ "${lines[0]}" == *"record-check --name unit --rev $REV --ok --class nix-check --src seat-verify --duration "* ]]' failed` |
| 2 | defer every kvm check | row 2 | `[[ "${lines[0]}" == "seat-vm pass run"* ]]' failed` |
| 3 | always build | row 3 | `[ "${lines[1]}" = "lint fail recorded" ]' failed` |
| 4 | no `timeout` | row 4 | `[ "$status" -eq 3 ]' failed` |
| 5 | eval failure → `not-run:absent` | row 5 | `[ "${lines[0]}" = "unit fail eval" ]' failed` |
| 6 | read the commit subject | row 6 | `[ "${lines[0]}" = "unit" ]' failed` |
| 7 | never demote | row 7 | `not ok 1 a claimed pass over a red check demotes a done to partial checks-misreported` |
| 8 | accept a claimed pass with no check | row 8 | `not ok 1 a claimed pass whose check is absent from the flake demotes to checks-unverifiable` |
| 9a | demote a claimed fail (`fail:fail`) | row 9 | `not ok 1 an honest fail and a deferred check leave the done status standing` |
| 9b | demote cache-miss (`absent:not-run:cache-miss`) | row 9 | `not ok 1 an honest fail and a deferred check leave the done status standing` |
| 10 | leave `not-run` claims alone | row 10 | `not ok 1 an unclaimed red check demotes to checks-misreported` |
| 11 | pick the last firing cell | row 11 | `not ok 1 a misreport and an unverifiable both firing keep checks-misreported and both clauses` |
| 12 | demote every status | row 12 | `not ok 1 a failed seat keeps its own status and still records the verified verdicts` |
| 13 | verify-timeout outranks a demotion | row 13 | `not ok 1 a cut budget leaves a done standing with verify-timeout, or checks-misreported over a red check` |
| 14a | substring instead of the `/` boundary | row 14 | `not ok 1 checks_scope is dirty when the diff touches flake.nix, tests, or githooks` |
| 14b | drop `githooks` from the roots | row 14 | `not ok 1 checks_scope is dirty when the diff touches flake.nix, tests, or githooks` |
| 15a | keep `none=not-run` | row 15 | `not ok 1 the unreported arm derives the seat-grammar FACTORY-CHECKS …` |
| 15b | write `not-run:cache-miss` into the seat grammar | row 15 | `not ok 1 the unreported arm derives the seat-grammar FACTORY-CHECKS …` |
| 16 | verify anyway | row 16 | `not ok 1 FACTORY_VERIFY=0 skips verification and logs verify: skipped` |
| 17 | put the verify rule first | 80-seat-driver row | `not ok 1 factory_error_class classifies the tail patterns …` |
| 18 | drop the `seat-integrate` default | 80-seat-driver row | `not ok 1 factory_record_check defaults src to seat-integrate and honours the fifth arg` |
| 19 | copy the seat's three-arm enum | row 19 | `Left contains one more item: 'checks_verified.unit: not in enum (pass\|fail\|not-run)'` |
| 20a | store a partial map | row 20 | `assert {} is None` |
| 20b | ingest `checks_scope_list` | row 20 | `…T2.result: checks_scope_list: undeclared field` (exit 1, `assert 1 == 0`) |

Mutant 9b as the section spells it ("demote cache-miss") does not apply to its own fixture: row 9's
seat claims only `unit=pass`, so `seat-vm`'s claimed token is `absent`, not `pass`. Spelled
`pass:not-run:cache-miss` the mutant **survives**; spelled `absent:not-run:cache-miss` — the cell the
fixture really exercises — it dies. Counted as killed; recorded as MINOR-6/MINOR-9.

Four mutants outside the named set, all **survived** (each is an unpinned contract, not a wrong
behaviour). Command: the full `bats tests/unit/94-seat-harness.bats`, no `not ok`.

| id | mutant | contract it leaves unpinned |
|---|---|---|
| ON1 | `verify_s=0` instead of the loop wall | "`verify_s` = the wall of the whole loop" |
| ON2 | delete the `$runs_dir/$key.verify-budget` write | "the caller passes the budget file SH5 reuses" |
| ON3 | drop the `head_sha != unknown` guard | "when … `head_sha` is not `unknown`" |
| ON4 | consult the recorded row *after* the absent test | "Per name, in order: (1) … (2) …" |

## Checks

Run in the clone, from the devShell, `XDG_CACHE_HOME` under the scratchpad.

| command | result |
|---|---|
| `nix build .#checks.x86_64-linux.unit -L --no-link --rebuild` | rc=0; `ok 554 FACTORY_VERIFY=0 skips verification and logs verify: skipped` |
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | rc=0; `433 passed in 11.32s` |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | rc=0 |
| `nix develop -c ruff check pkgs/evidence tests/evidence` | rc=0, `All checks passed!` |
| `nix develop -c ruff format --check pkgs/evidence tests/evidence` | rc=0, `80 files already formatted` |
| `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | rc=0 (MAP is current) |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | rc=0, silent |
| `nix develop -c githooks/pre-commit` | rc=1 on the first pass, rc=0 on the second — see below |

**The pre-commit line is not a red check.** The only output is
`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md
and commit again`, and the whole diff it produces is one line:
`… SD8 SH4 (…)` → `… SD8 SH5 (…)`. The queue is derived from landed commit subjects, so SH4's own
commit is what makes the block stale; at the base rev `a2b758c` the same hook exits 0. Staging the
regenerated block and re-running gives rc=0 (`pass1 rc=1` / `pass2 rc=0`). The hook could not have
refused at commit time, because the commit object did not yet exist. Structural, not the seat's.

**The carried SH3r store question.** SH4's own end-to-end helper sets both seams —
`tests/unit/94-seat-harness.bats:1545`
`FACTORY_EVIDENCE_CMD="$BIN/evidence" EVIDENCE_STORE="$BATS_TEST_TMPDIR/ev"` — so no SH4 test reaches
`evidence.py` at all. The older helpers (`run_task`, `run_task_touches`) still set neither, but I
probed one directly with `EVIDENCE_STORE` pointed at a temp dir and no row is written: the store is
never opened, because `ingest result` refuses first on its runs-root guard —

```
evidence: ingest result: /tmp/…/factory/runs/r1/K1.result is outside /home/dalhaka/factory/runs
```

and the temp store directory is not created (`find …/ev` → `No such file or directory`). The file's
`teardown_file` additionally diffs `~/factory/runs` before and after. Nothing in this branch can
write to `/var/lib/evidence`. No file under `/var/lib/evidence` was read or written by this review.

## Touches and commit

Diff files against the section's `touches`:

```
docs/MAP.md                                   (exempt by the standing rule)
pkgs/evidence/SCHEMA.md                       in touches
pkgs/evidence/ingest_result.py                in touches
pkgs/evidence/streams.py                      in touches
tests/evidence/fixtures/results/checks.result in touches (Create)
tests/evidence/test_ingest_result.py          in touches
tests/evidence/test_streams_policy.py         in touches
tests/unit/80-seat-driver.bats                in touches
tests/unit/94-seat-harness.bats               in touches
tools/factory/seat/README.md                  in touches
tools/factory/seat/factory-lib.sh             in touches
tools/factory/seat/factory-task               in touches
```

No file outside; no `Deviation:` line needed and none present. The plan file is untouched; there is
no board commit; `docs/OPERATIONS.md` is not in the diff.

`git rev-list --count a2b758c..HEAD` → `1`. The subject is byte-identical to the section's (compared
programmatically against the string parsed out of the plan file: `SUBJECT IDENTICAL`,
`PLAN==EXPECTED`). The body states the why over eleven lines and pastes both reds
(`factory_verify_checks: command not found` (exit 127); `KeyError: 'checks_verified'`); the two
trailers follow a blank line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sh3)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

## Findings

No MAJOR.

**MINOR-1 — the verdict line drops `<duration_s>` on every non-`run` verdict.**
`tools/factory/seat/factory-lib.sh:309-345`. The signature says
`<name> <verdict> <src> <duration_s>`; only the two `run` arms print four fields
(`printf '%s %s %s %s\n' "$name" "pass" "run" "$dur"` at `:340`), the rest print three
(`printf '%s %s %s\n' "$name" "not-run:absent" "-"` at `:325`). The section's own fixture rows expect
three (`[ "${lines[2]}" = "nosuch not-run:absent -" ]`), so the section contradicts itself and the
code follows the fixtures. No consumer breaks — `factory-task:308` reads
`while read -r vname vverdict vsrc _`.

**MINOR-2 — verification is gated on a non-empty acceptance list, not on the stated union.**
`tools/factory/seat/factory-task:281` `if [ "${#verify_names[@]}" -gt 0 ]; then`. The section's only
stated guards are `FACTORY_VERIFY != 0` and `head_sha != unknown`, with the name set the *union* of
the acceptance names and the seat's claimed passes — so a section with no `**acceptance:**` line and
a seat claiming `unit=pass` should still verify `unit`. It does not. The choice is D6-consistent
("a missing contract degrades to no record", the same shape as
`factory_log "touches: no contract for $key …"`) and is what keeps the SH2/SH3 helpers from opening
the default store; but it is a literal deviation and no test covers either reading.

**MINOR-3 — `checks_scope:` and `checks_scope_files:` are written with empty values when the
workspace has no `.factory-meta`.** `tools/factory/seat/factory-task:315` guards the scope
computation on `[ -n "$base_sha" ]` while `:599-600` print the two lines unconditionally. Proven with
a probe test (`mk_verify_ws` with the meta removed, acceptance `unit`, seat `done`):

```
checks_verified: unit=pass
checks_verified_src: unit=run
verify_s: 0
checks_scope: 
checks_scope_files: 
```

Harmless downstream — the section itself declares both nullable and says the ingest maps a non-enum
word to `None`, which `_parse_verified`/`_as_int` do — but the stated `.result` grammar is
`checks_scope: clean|dirty` and `checks_scope_files: <n>`. Omitting both lines, or writing `clean`,
would match it.

**MINOR-4 — `factory_check_deferred` codes the two deferral rules as exclusive, not as the stated
OR.** `tools/factory/seat/factory-lib.sh:275-281`:

```
  if printf '%s' "$show" | grep -q -- '"requiredSystemFeatures"'; then
    printf '%s' "$show" | grep -q -- 'kvm' || return 1
  elif [ -n "$toplevel_drv" ] && printf '%s' "$show" | grep -qF -- "\"$toplevel_drv\""; then
```

A derivation that declares `requiredSystemFeatures` without `kvm` returns 1 before the drvPath test
ever runs, so a host-toplevel check carrying any other feature would be built rather than deferred.
Unreachable for today's `host-core`, and no fixture distinguishes it. Separately the `kvm` grep scans
the whole `derivation show` JSON rather than that field's value, so a derivation whose store path
contains `kvm` would defer on a false positive.

**MINOR-5 — the exhausted-budget path re-arms a one-second window per name.**
`tools/factory/seat/factory-lib.sh:336` `[ "$remaining" -ge 1 ] || remaining=1`. The section says
`<remaining>` is the budget minus the time spent; it does not say what a non-positive remaining does
(the judge panel flagged exactly this as open, errata 8/12 of the first judgement). In practice the
`timed_out=1` short-circuit at `:347` hides it, because a 124 stops the loop; the clamp only bites
when repeated fast *failures* overrun the budget without any single build timing out.

**MINOR-6 — the section's row-9 mutant does not apply to the section's row-9 fixture.** Plan
`docs/superpowers/plans/2026-09-07-seat-harness-redesign.md`, SH4 test table row 9: the mutant
"demote cache-miss" spelled against the claimed token `pass` survives, because the fixture's seat
claims only `unit=pass` and `seat-vm`'s claimed token is therefore `absent`. Pasted above under
Mutants. A plan-text defect, recorded, not gating.

**MINOR-7 — `verify_s`'s value is unpinned.** `tools/factory/seat/factory-task:305`. Every assertion
is `[[ "$output" == *"verify_s: "* ]]`; ON1 (`verify_s=0`) survives the whole file.

**MINOR-8 — the verify-budget file has no reader and no test.**
`tools/factory/seat/factory-task:283` writes `$runs_dir/$key.verify-budget` (the budget in seconds,
not a deadline). ON2 (delete the write) survives. This is the plan's own open "budget file" clause,
named by both judgement rounds; the implementer produced an artefact for a consumer SH5 has not yet
defined.

**MINOR-9 — three cells of the demotion table have no fixture.** `absent × fail` (a name on the
acceptance line that the seat's `FACTORY-CHECKS` simply omits — row 10's `none=not-run` yields the
claimed token `not-run`, not `absent`, via the blanket at `factory-lib.sh:234-256`),
`pass × not-run:cache-miss`, and every cell of the `fail` row except `fail × fail`.

**MINOR-10 — D5's checks-over-touches precedence has no fixture.** `factory-task:426` and `:462`
put the two blocks in the right order, and SH3's arm is correctly skipped once the status is
`partial`; but no test carries both a checks demotion and an undisclosed touches extra, so the
stated "its arm is outranked, its clause still appended" is unverified.

**MINOR-11 — the "(1) recorded wins, (2) absent" ordering is unpinned.** ON4 (swap the two steps)
survives: row 3's recorded `lint` is also present in the flake, so no fixture distinguishes a
recorded row for a name the flake no longer declares.

**MINOR-12 — SH3's touches clause is now appended for every status, not only a demoted one.**
`tools/factory/seat/factory-task:506-512` hoists the note append out of the `status = done` guard.
That is what the section asks for in the outranked case ("its clause still appended"), but it also
adds the clause to a `failed` or `unreported` seat's notes, which nothing states and nothing tests —
`94-seat-harness.bats:868` asserts only the status and the error class.

**MINOR-13 — the commit body pastes the red but not the green.** It says "both are green now"
without a check name or output. Step 2 of the section only demands the reds; matrix item 6 asks for
both.

## Verdict

**APPROVED.** Every numbered contract item of the SH4 section is met at the cited line; the two reds
the section names reproduce exactly against the base implementation and go green at HEAD; all 27
named mutants are killed; `unit`, `evidence-unit` and `lint` build green with `--rebuild`, as do
`ruff check`, `ruff format --check`, the MAP regeneration and `tasks.py check`; the diff is inside
`touches` with `docs/MAP.md` exempt by rule; one commit, subject byte-identical, both trailers
present, no board commit and the plan untouched. The thirteen MINORs are unpinned contracts,
two plan-text defects and one commit-body omission — none of them a wrong behaviour, none gating.
`plan_defect: none`.
