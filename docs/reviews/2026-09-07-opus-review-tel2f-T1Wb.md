---
plan_defect: none
mutants_total: 18
mutants_killed: 17
mutants_outside_named: 8
reviewer: opus
majors: null
minors: 4
---
# Opus gate — seat run tel2f, task T1Wb — APPROVED

## Summary

The fix round is exactly the fix round: against T1W's head `be8fc0a` the only
code file that moved is `tests/lint/store-writers.sh` (+85/−12); everything else
in the `68f5d75..4d5266d` diff is T1W's own content carried forward by the
cherry-pick. All three MAJORs of `docs/reviews/2026-09-07-opus-review-tel2-T1W.md`
are closed, and I closed them the hard way — by re-running the two mutants that
survived the previous round.

The `clean.py` arm can now fail. Three separate `count_hits` calls replace the
dead combined pattern (`tests/lint/store-writers.sh:148,153,158`), and each of
the three escape hatches appended to `clean.py` turns `--self-test` red naming
the fixture *and* the pattern. Put the combined `\|` pattern back and all three
dirtied runs go green again — the assertion is load-bearing, and the
discrimination is real, not asserted.

The root list is pinned. `TREE` (`:23`) makes the sweep's base directory a
variable, and `planted_roots_check` (`:90-125`) builds a temporary tree with one
`O_APPEND` hit per declared root and requires exactly one hit each. Dropping
`pkgs/helm` from `ROOTS` — the mutant that survived *everything* last round,
even with the pre-T1W `_append_status_row` restored underneath — now exits 1
with `store-writers: self-test: root pkgs/helm not swept`. The exclusion arm is
pinned too, and is reachable: dropping the `evidence.py` exclusion trips the
per-root count (`swept 2 times, expected 1`), and retargeting the exclusion at
`_planted.py` trips the dedicated exclusion assertion at `:121`. I found three
further ways to break the sweep — excluding `*.py`, stubbing `run_project`,
dropping the `TREE` prefix in `scan` — and the planted assertion kills all
three. This is a genuinely stronger gate than the one the section asked for.

The record is in the commit. The body is ~110 lines of pasted command output:
the nine-hit lint red, both pytest red summaries, the `bad-open.py` fixture-edit
run, the three dirtied-`clean.py` runs, the root-drop run, the two item mutants,
and the greens. I re-ran every one of them; each paste matches what I saw,
line for line (only pytest wall-clock differs).

All five acceptance checks are green on a fresh clone, `helm-vm` re-run with
`--rebuild`. The T1b correction holds (`ts_epoch`, `tools/ledger/factory.py:379`,
`tools/ledger/schema.md:118,126,223`), and reverting it still kills two ledger
tests. `touches` is clean: sixteen files, fifteen from the list plus `docs/MAP.md`
by rule — `docs/OPERATIONS.md` is not in the diff at all this time. The subject
is byte-identical (218 bytes each). No MAJORs.

## Contract items

The section's contract is its three numbered items (each a MAJOR of the prior
review carried verbatim), plus its Steps and its conventions.

| # | contract item (section, literal) | verdict | evidence |
|---|---|---|---|
| 1a | the clean arm counts each of the three patterns on its own (three `count_hits` calls, as the bad-fixture arms do) | met | `tests/lint/store-writers.sh:148`, `:153`, `:158` — `count_hits "$FIXTURES/clean.py" "$P_APPEND"` / `"$P_OPEN"` / `"$P_LITERAL"` |
| 1b | no combined pattern anywhere in the script | met | the only remaining alternation is `^store-writers: ${root}(/\|:)` at `:111` (a match-line anchor, correctly *unescaped* ERE), not a rule pattern; the `\|` line is gone from `self_check` |
| 1c | fails naming `clean.py` **and the pattern** on any hit | met | `:150`, `:155`, `:160`; the three runs below |
| 1d | the body pastes three runs, one escape hatch each → exit 1 naming `clean.py`; restored → exit 0 | met | commit body, "clean.py arm (MAJOR-1)"; reproduced verbatim below |
| 2a | the sweep takes its base directory from one variable (`TREE`, default `.`; the self-test sets it) | met | `:23` `TREE="."`, `:40` `cd "$TREE"`, `:58` `grep -nE "$pattern" "$TREE/$f"`, `:106`/`:108` set and restore |
| 2b | `--self-test` gains a planted-root assertion: a temporary tree carrying the six declared roots, one `O_APPEND` hit per root (`_planted.py` in each directory root; one line appended to a copy of each file root) | met | `:90-104`; verified by inspection and by the mutants below |
| 2c | the six-root list written a second time inside the self-test as its own literal | met | `:82` `PLANTED_ROOTS=(pkgs/evidence pkgs/helm tools/ledger tools/factory tools/session-start.sh tools/ritual.sh)` — identical to `ROOTS` at `:21` |
| 2d | runs the sweep over that tree with `TREE` pointing at it and requires exactly one hit per root | met | `:106-120`; the `-eq 0` and `-gt 1` arms both fire (mutants N2 and N3) |
| 2e | a root without a hit → exit 1 `store-writers: self-test: root <root> not swept` | met | `:113`; observed literally: `store-writers: self-test: root pkgs/helm not swept` |
| 2f | the `pkgs/evidence/evidence.py` exclusion stays and is asserted (a planted `evidence.py` produces no hit) | met | exclusion at `:44`; assertion at `:121-124`; **reachable** — mutant O8 trips it |
| 2g | drop `pkgs/helm` from `ROOTS` → `--self-test` exit 1 naming `pkgs/helm`, pasted and restored | met | body, "root-list pin (MAJOR-2)"; reproduced (N2) |
| 2h | drop the exclusion → the planted `evidence.py` hit turns the count to seven → exit 1 | met | body, "item-2 mutant"; reproduced (N3) — the message is the per-root count arm, `root pkgs/evidence swept 2 times, expected 1` |
| 3 | the body pastes, each under its command line: the nine-hit lint red, the two pytest red summaries, the `--self-test` fixture-edit run, the three dirtied-`clean.py` runs, the root-drop run, and the green counterparts | met | `git log -1 --format=%B` — every one present; each reproduced below |
| S3 | nothing else in the code unless a run demands it | met | `git diff be8fc0a..4d5266d` touches exactly one code file, `tests/lint/store-writers.sh` |
| S4 | treefmt, shellcheck, the runs, repomap, the five checks, pre-commit | met (pre-commit — MINOR-1) | all re-run below |
| S5 | one commit, this section's subject, the two trailers | met | 1 commit; subject 218 bytes, identical; trailers last after a blank line |
| T1b | `lane-job`'s epoch field is `ts_epoch` in `extract_lane` and `schema.md` | met | `tools/ledger/factory.py:379` `"ts_epoch": data.get("ts")`, windowing at `:457`, `:607`; `tools/ledger/schema.md:118`, `:126`, `:223`; reverting kills 2 tests (O2) |

The section's twenty T1W interface items are carried unchanged in this diff and
were verified item-by-item by the previous gate; I re-confirmed the load-bearing
ones by mutation (N5–N10 below) and spot-checked the citations: `import evidence`
at `pkgs/helm/collect.py:27`, `_store` at `:577`, `_status_rows` at `:745`, no
`fcntl`/`_append_status_row` anywhere; `tools/ledger/factory.py:51-54` (the
two-candidate path insertion and its `ImportError` string), `:58` `DEFAULT_LEDGER`;
the two wirings at `flake.nix:1052-1053` and `githooks/pre-commit:39-40`, each on
its own line.

## Red before green

Reproduced in a scratch copy of the branch by checking out the **base**
implementation files (`git checkout e0b80e2 -- pkgs/helm/collect.py
tools/ledger/factory.py tools/factory/dark-factory.js`; `e0b80e2` and the branch
base `68f5d75` are identical for those three files) against the **branch's**
tests, then restoring.

**(1) the lint sweep** — nine hits, matching the body byte for byte:

```
store-writers: pkgs/helm/collect.py:743: O_APPEND
store-writers: pkgs/helm/collect.py:747: open(…,"a…")
store-writers: pkgs/helm/collect.py:578: /var/lib/evidence
store-writers: pkgs/helm/collect.py:757: /var/lib/evidence
store-writers: pkgs/helm/collect.py:793: /var/lib/evidence
store-writers: tools/ledger/factory.py:25: /var/lib/evidence
store-writers: tools/ledger/factory.py:41: /var/lib/evidence
store-writers: tools/factory/dark-factory.js:785: /var/lib/evidence
store-writers: tools/factory/dark-factory.js:892: /var/lib/evidence
exit=1
```

and `--self-test` still `selftest=0` on that same tree — the non-vacuity
precondition Step 2 of T1W demands.

**(2) `tests/helm`:** `2 failed, 148 passed in 13.22s` —
`test_record_status_writes_only_through_evidence_append`,
`test_record_status_refusal_is_logged_not_raised`.

**(3) `tests/ledger`:** `10 failed, 32 passed in 0.20s` — the same ten names the
body pastes.

**(4) `render.test.mjs`:**
`AssertionError [ERR_ASSERTION]: The input did not match the regular expression
/pkgs\/evidence\/evidence\.py record-check --name flake-check --rev \$\(git rev-parse HEAD\)/`

**(5) the new assertions of this round.** The three dirtied-`clean.py` runs, one
escape hatch appended per run, each restored afterwards:

```
--- hatch: import os / F = os.O_APPEND
store-writers: self-test: clean.py: expected 0 O_APPEND hits, got 1
exit=1
--- hatch: fh = open("x", "a")
store-writers: self-test: clean.py: expected 0 open(…"a…") hits, got 1
exit=1
--- hatch: STORE = "/var/lib/evidence"
store-writers: self-test: clean.py: expected 0 /var/lib/evidence hits, got 1
exit=1
--- restored
exit=0
```

and the root-drop run:

```
$ sed -i '21s/…/ROOTS=(pkgs/evidence tools/ledger tools/factory tools/session-start.sh tools/ritual.sh)/'
$ bash tests/lint/store-writers.sh --self-test
store-writers: self-test: root pkgs/helm not swept
MUTANT_B_selftest_exit=1
```

Every assertion the section names has been shown to fail. No test in the diff is
vacuous.

## Mutants

18 applied, 17 killed. Named by the section (its two items plus T1W's mutant
table, whose first row this section replaces): 10, **all 10 killed**. Outside: 8,
7 killed.

| # | mutant | named? | result | evidence |
|---|---|---|---|---|
| N1 | the combined `\|` pattern put back in the clean arm (`:148-162` → one `count_hits` with `"$P_APPEND\|$P_OPEN\|$P_LITERAL"`) | named (item 1) | killed | with the mutant, all three dirtied-`clean.py` runs give `MUTANT_A_dirty_exit=0`; without it they give `exit=1` — the exact contrast the section prescribes |
| N2 | drop `pkgs/helm` from `ROOTS` (`:21`) | named (item 2) | killed | `store-writers: self-test: root pkgs/helm not swept`, `selftest_exit=1`. Also re-run with the base `collect.py` restored underneath: `tree_exit_with_regression=0` but `selftest_with_regression=1` — the regression the gate exists to catch is now caught |
| N3 | drop the `pkgs/evidence/evidence.py` exclusion (`:44`) | named (item 2) | killed | `store-writers: self-test: root pkgs/evidence swept 2 times, expected 1`, `exit=1` |
| N4 | `self_check` skips the per-fixture counts (`return 0` at the top) | named (T1W) | killed | baseline with `clean.py` dirtied: `exit=1`; mutated: `MUTANT_D_exit=0` |
| N5 | `record_status` writes with `open(path, "a")` instead of `evidence.append` | named (T1W) | killed | `3 failed, 147 passed` — `test_record_status_writes_only_through_evidence_append`, `…_refusal_is_logged_not_raised`, `…_writes_on_change_and_heartbeat_only` |
| N6 | drop the `try/except (OSError, ValueError)` so the refusal propagates | named (T1W) | killed | `tests/helm/test_collect.py:1245: ValueError` → `1 failed, 149 passed` |
| N7 | `_read_findings` keeps `"title": title` | named (T1W) | killed | `6 failed, 36 passed`, incl. `test_records_carry_kind_and_title_sha256` |
| N8 | `_stream_of`: `store = path.parent` | named (T1W) | killed | `15 failed, 27 passed` |
| N9 | leave one `--store "${EVIDENCE_STORE:-/var/lib/evidence}"` at the recorder prompt (`dark-factory.js:892`) | named (T1W) | killed twice | `render.test.mjs`: `expected: /pkgs\/evidence\/evidence\.py record runs --json/`; and `store-writers: tools/factory/dark-factory.js:892: /var/lib/evidence`, `lint_exit=1` |
| N10 | drop the `PYTHONPATH` export from `nixosModules/helm.nix:103` | named (T1W) | killed | `helm-vm` **red**: `helm-collect[893]: ModuleNotFoundError: No module named 'evidence'` → `RequestedAssertionFailed: command 'systemctl --user -M alice@ start helm-collect.service' failed`, `MUT_EXIT=1` |
| O1 | `bad-open.py`'s `"a"` → `"w"` | outside | killed | `store-writers: self-test: bad-open.py: expected 1 open(…"a…") hit, got 0`, `exit=1`; restored `exit=0` |
| O2 | `extract_lane` writes `"ts"` instead of `"ts_epoch"` | outside | killed | `2 failed, 40 passed` — `test_extract_lane_records_cost_usd`, `test_rollup_week_windows_activity_export` |
| O3 | the sweep excludes `*.py` (`:42`) | outside | killed | `store-writers: self-test: root pkgs/evidence not swept`, `X4_exit=1` |
| O4 | `run_project() { return 0; }` — the sweep stubbed out entirely | outside | killed | `store-writers: self-test: root pkgs/evidence not swept`, `X5_exit=1` (while `X5_tree_exit=0` — only the planted assertion catches it) |
| O5 | `scan` drops the `TREE` prefix (`:58` → `grep -nE "$pattern" "$f"`) | outside | killed | `grep: tools/factory/_planted.py: No such file or directory` … `store-writers: self-test: root pkgs/evidence not swept`, `X6_exit=1` |
| O6 | drop `tools/ritual.sh` (a *file* root) from `ROOTS` | outside | killed | `store-writers: self-test: root tools/ritual.sh not swept`, `X7_exit=1` |
| O7 | narrow `ROOTS` **and** `PLANTED_ROOTS` together (both drop `pkgs/helm`) | outside | **survived** | `X8_selftest=0`, `X8_tree=0` — the inherent limit of the double-entry pin the section prescribes; see MINOR-3 |
| O8 | the exclusion retargeted at `pkgs/evidence/_planted.py` | outside | killed | `store-writers: self-test: pkgs/evidence/evidence.py must stay excluded from the sweep`, `X9_exit=1` — proves `:121-124` is reachable, not dead |

## Checks

All in a fresh clone of `task/T1Wb` at `4d5266d`. The four non-VM checks were
built once (`--rebuild` refuses a never-built derivation here), then re-run with
`--rebuild`; both runs green.

| check | command | result |
|---|---|---|
| helm-unit | `nix build .#checks.x86_64-linux.helm-unit -L --no-link --rebuild` | **green** — `150 passed in 13.35s`, `EXIT=0` |
| ledger-unit | `… ledger-unit … --rebuild` | **green** — `42 passed in 0.61s`, `EXIT=0` |
| factory-unit | `… factory-unit … --rebuild` | **green** — `render.test.mjs: all assertions passed`, `plan.test.mjs: all assertions passed`, `EXIT=0` |
| helm-vm | `… helm-vm -L --no-link --rebuild` | **green** — VM ran; `machine: must succeed: systemctl --user -M alice@ start helm-collect.service` finished in 0.58 s, the collector logging `helm-collect: evidence: [Errno 30] Read-only file system: '/var/lib/evidence'` (so `import evidence` resolved — the wrapper's proof); `(finished: run the VM test script, in 16.62 seconds)`, `(finished: cleanup, in 0.10 seconds)`, `EXIT=0` |
| lint | `… lint … --rebuild` | **green** — `Found 0 warnings and 0 errors.`, `EXIT=0` |
| pre-commit | `nix develop -c githooks/pre-commit` | **red at HEAD, green at base** — `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`, `PRECOMMIT=1`; the same hook on a clone at base `68f5d75` is `BASE_PRECOMMIT=0`. See MINOR-1 |
| ruff check | `nix develop -c ruff check pkgs/helm tests/helm tools/ledger tests/ledger tests/lint/fixtures/store` | green — `All checks passed!` |
| ruff format | `… ruff format --check …` (same paths) | green — `12 files already formatted` |
| shellcheck | `nix develop -c shellcheck tests/lint/store-writers.sh` | green — `SHELLCHECK=0` |
| treefmt | `nix develop -c treefmt --fail-on-change` | green — `formatted 114 files (0 changed)`, `TREEFMT=0` |
| MAP.md | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | green — `MAPDIFF=0` |
| task graph | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | green — silent, `TASKSCHECK=0` |
| project sweep | `bash tests/lint/store-writers.sh` / `--self-test` | green — `tree_exit=0`, `selftest_exit=0` |
| suites | `nix develop -c pytest tests/helm tests/ledger -q`; `node tests/factory/render.test.mjs` | green — `192 passed in 14.10s`; `render.test.mjs: all assertions passed` |

## Touches and commit

Sixteen files. Fifteen are the section's `touches`, verbatim; the sixteenth is
`docs/MAP.md` (`tests/lint — 6 files` → `11 files`), the standing exemption, and
it is current (`MAPDIFF=0`). **`docs/OPERATIONS.md` is not in this diff at all** —
unlike T1W's commit, nothing outside the list and nothing to explain. The plan
file is untouched (`git diff --name-only … -- docs/superpowers/plans/` → 0 lines);
there is no board commit.

Against T1W's head the delta is minimal and on-contract:

```
$ git diff --stat be8fc0a..4d5266d
 docs/OPERATIONS.md                              |   6 +-
 docs/board/log-2026-09.md                       |   4 +
 docs/ledger/plan-defects.toml                   |  16 +
 docs/reviews/2026-09-07-opus-review-tel2-T1W.md | 415 ++++++++++
 docs/reviews/2026-09-07-opus-review-tel2-T3.md  | 444 ++++++++++
 docs/superpowers/plans/2026-09-06-telemetry-store-1.md | 59 +
 tests/lint/store-writers.sh                     |  85 +-
```

— the six docs files are main moving under the cherry-pick (Step 1's stated
condition), and the one code file is the fix.

Commit: exactly one, `4d5266d` on base `68f5d75`. Subject byte-identical to the
section's string (218 bytes each, `IDENTICAL`). Trailers correct and last, after
a blank line: `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813
(seat headless, factory run tel2f)` then `Co-Authored-By: Claude Fable 5.1
<noreply@anthropic.com>`.

## Findings

No MAJORs.

### MINOR-1 — `githooks/pre-commit` is red at HEAD, green at the base; the body's `exit=0` is the pre-commit-time run

`docs/OPERATIONS.md:15`

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
PRECOMMIT=1
```

The regenerated block drops `T1Wb` from the queued list. `tasks.py` judges
"landed" from `landed_subjects(repo_path)` (`pkgs/evidence/tasks.py:206`,
consumed at `:436`), which reads git log subjects — so this task's *own* commit
subject makes it landed and the derived block goes stale the instant the commit
exists. I confirmed the asymmetry: a clone checked out at base `68f5d75` runs the
same hook to `BASE_PRECOMMIT=0` with `T1Wb` still listed. The seat could not have
made the post-commit run green: before the commit, regenerating puts `T1Wb` back.
The body's `nix develop -c githooks/pre-commit → exit=0` is therefore the honest
pre-commit-time result. Nothing owed to the seat; it is the same self-referential
property the previous gate recorded as its MINOR-6, and it belongs in the runbook
so the next gate does not read it as a regression.

### MINOR-2 — the item-1 mutant's paste does not show the dirtying step

commit body, block `# item-1 mutant: the combined \| pattern put back`

The paste is

```
    $ bash tests/lint/store-writers.sh --self-test
    exit=0
```

with the dirtying of `clean.py` only described in the comment above it. On its
own that line is uninformative — `--self-test` exits 0 with the mutant *and*
without it when `clean.py` is clean; the whole content of the mutant is that the
*dirtied* run flips from 1 to 0. I verified it (`MUTANT_A_dirty_exit=0` three
times, against `exit=1` three times unmutated), so the claim is true, but the
record would need the `printf … >> clean.py` line above the run to stand alone.
Every other paste in the body does carry its command line.

### MINOR-3 — the root pin is double-entry, so a coordinated edit of both lists survives

`tests/lint/store-writers.sh:21` and `:82`

Dropping `pkgs/helm` from `ROOTS` **and** `PLANTED_ROOTS` together gives
`X8_selftest=0`, `X8_tree=0` — the fence silently narrows again. This is the
inherent limit of the mechanism the section itself specifies ("this list written
a second time inside the self-test as its own literal"), not a deviation, and the
single-list mutant the section names dies loudly. Worth a row only so the next
round knows the pin is a two-key lock, not a proof. A `ROOTS`-vs-`PLANTED_ROOTS`
equality assertion would close it in one line.

### MINOR-4 — the previous review's seven MINORs are still open, as the section says

`tools/ledger/factory.py:100` / `tests/ledger/test_factory.py:434` (the
`ledger dir must be named ledger:` message is still unpinned — no `capsys`);
`tests/lint/store-writers.sh:29-34` (exit 2 untested);
`tools/ledger/factory.py:51-54` (the `ImportError` message untested);
`tools/ledger/factory.py:175` (`title = finding.get("issue") or finding.get("title")`
is still `None`-able into `.encode()`);
`tests/ledger/test_factory.py:298,530` (the two narrowed fixtures, still
unexplained in a body); `tests/ledger/test_factory.py:400`
(`assert names <= {...}` still dead). The section states these are "recorded, not
owed here", so this is a carry-forward note, not a charge against the seat.

## Verdict

**APPROVED.** All three MAJORs of the tel2 gate are closed and I closed them
adversarially: the `clean.py` arm now fails on each of its three escape hatches
and goes green again the moment the combined `\|` pattern returns; the
`pkgs/helm` root drop — which survived every check last round even with the
pre-T1W `_append_status_row` restored — now exits 1 naming the root, as do five
further ways I found to narrow or stub the sweep; and the commit body carries
every red and green, each one of which I reproduced. 18 mutants applied, 17
killed, all 10 named ones dead, including the `helm-vm` `PYTHONPATH` proof
(`ModuleNotFoundError: No module named 'evidence'` inside the VM's
`helm-collect.service`). All five acceptance checks green on a fresh clone with
`--rebuild`, `touches` clean with `docs/OPERATIONS.md` no longer in the diff, the
subject byte-identical, the T1b `ts_epoch` correction intact. Four MINORs, none
blocking.
