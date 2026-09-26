# Opus gate — seat run pa1, task P1 — APPROVED

## Summary

One commit `d26333f` on `task/P1`, base `91dcc5f`. `pkgs/evidence/tasks.py`
gains `map_check_names`, `load_draft`, `draft_rules` and the `check --draft`
branch (+232); `tests/evidence/test_tasks.py` gains 18 draft tests as a pure
append (+347, −0, no old test touched); the eleven contracted fixtures land
under `tests/evidence/fixtures/drafts/`; `flake.nix` gains the two contracted
`evidence-unit` copy lines; `docs/runbooks/evidence.md` gains the paragraph.
`docs/MAP.md` (a `tests/evidence` file count) and `docs/OPERATIONS.md` (queue
block only) are the two rule-driven changes outside `touches`.

Every rule the contract names fires, with the contracted message, on a fixture
root I built by hand and drove through the CLI. Nothing outside `--root` is
read (proved with a `sys.addaudithook` probe: 0 opens under
`/home/dalhaka/nixos-agent-env`, the only subprocess is `git -C <fixture root>
log`). stdout carries the two success lines and nothing else; every error goes
to stderr. Thirteen mutants, all killed. Every check green. The commit subject
is byte-identical to the plan's and both trailers are in the WORKSPACE RULES
order.

Test 14 was adapted, and the seat's stated reason is true — I reproduced it
four ways. The contract for test 14 is **unsatisfiable as written**: that is a
plan defect, not a weakened test. The adaptation still kills the mutant the
contract names for it. It does, however, throw away the live-tree dimension the
test existed for, and with it the only consumer of the two `flake.nix` copy
lines — a minor, recorded below.

## The rules (table)

Fixture root: `<scratch>/mx/root` — `docs/superpowers/plans/base.md` with
landed `B1` and open `B2`, `docs/ledger/repos.toml` naming the root,
`docs/MAP.md` listing `evidence-unit, unit, lint`; `git init` + one commit whose
subject is `x: b1 (test: unit)` supplies the landed set. Every row run as
`python3 <clone>/pkgs/evidence/tasks.py --root <root> --runs-dir /nonexistent
--store /nonexistent check --draft <file>`.

| # | case | expected | observed (stderr, or stdout where noted) | exit |
|---|---|---|---|---|
| 1 | `dup-key.md` redefines `B2` | `defined in base.md and dup-key.md` | `tasks: root/B2 defined in base.md and dup-key.md` | 1 |
| 2 | `dangling-dep.md` | `dependsOn Q9: unknown key` | `tasks: root/Z1 dependsOn Q9: unknown key` | 1 |
| 3 | `fake-check.md` | `acceptance unit-tests not in docs/MAP.md` | `tasks: Z1 acceptance unit-tests not in docs/MAP.md` | 1 |
| 4 | `glob-touch.md` | `glob is not an explicit path` | `tasks: Z1 touches pkgs/*: glob is not an explicit path` | 1 |
| 5 | `size-l.md` | `size L is refused` | `tasks: Z1: size L is refused; split it` | 1 |
| 6 | `subject-mismatch.md` | `ZB` only; `ZA` (`unit, lint` vs `lint, unit`) accepted | `tasks: ZB commit subject (test: lint) differs from acceptance` — **no `ZA` row** | 1 |
| 7 | `no-assumptions.md` | `draft lacks section Assumptions` | exactly that, one line | 1 |
| 8 | `sound.md` | stdout exactly two lines | stdout `waves: [[["Z1"]], [["Z2"]]]` / `conflicts: none`; stderr empty | 0 |
| 9 | draft `Z1` touches `tools/x.sh` (open `B2` too) | one row | stdout `conflicts: B2 (base.md) × Z1 (overlap.md): tools/x.sh ~ tools/x.sh` | 0 |
| 10 | draft inside the plans dir (absolute) | usage error | `tasks: --draft: …/plans/field.md is already under the plans directory; run check without --draft` | **2** |
| 10b | the same by **relative** path | same | same message with the relative path | **2** |
| 10c | **symlink** outside → inside (realpath) | same | same message, naming the symlink | **2** |
| 11 | `replan-drops-heading.md` as `base.md` | `draft drops heading: ### B1 …` | `tasks: draft drops heading: ### B1 (code, S) — the root` | 1 |
| 11b | `replan-keeps-headings.md` as `base.md` | accepted, `B1`/`B2` replaced | stdout `waves: [[["B2r"]]]` / `conflicts: none` (test asserts the exact two lines) | 0 |
| 12 | `dup-in-draft.md` | `defined twice` | `tasks: Z1 defined twice in dup-in-draft.md` | 1 |
| 13 | `**repo:** media`, acceptance `comfy-worlds-unit` | exempt from (a) and (c) | stdout `waves: [[["M1"]]]` / `conflicts: none` | 0 |
| 13b | the same task with **no** acceptance | the existing code-without-acceptance rule still fires | `tasks: root/M1 (code) has no acceptance` | 1 |
| 14 | see **Test 14** below | — | — | — |
| 15 | `dup-in-draft.md` (rule (f)) | as row 12 | as row 12 | 1 |

Extra rows the gate required:

| case | expected | observed | exit |
|---|---|---|---|
| `B1b` reusing `B1`'s landed subject (same chain root) | accepted | stdout `waves: []` / `conflicts: none` | 0 |
| `Z1` reusing `B1`'s landed subject (other root) | refused | `tasks: Z1 commit subject already landed: x: b1 (test: unit)` | 1 |
| two draft tasks `Z1`/`Y1`, same subject, different roots | refused | `tasks: Y1 commit subject x: same (test: unit) shared by a different chain root` | 1 |
| `Z1`/`Z1b`, same subject, **same** root | accepted | `waves: [[["Z1"], ["Z1b"]]]` / `conflicts: none` | 0 |
| only `## Assumptions` missing | one line | one line (row 7) | 1 |
| all four missing (empty file) | one line per header | four lines, `Global Constraints`, `Assumptions`, `Waves`, `Operator` | 1 |
| empty file | as above | as above, no crash | 1 |
| typed heading, no body | rules still fire | `has no acceptance`, four header lines, `Z1 touches: empty`, `Z1 commit subject (test: ?) differs from acceptance` | 1 |
| `--draft` **with** `--board` (stale board) | both run | `tasks: docs/OPERATIONS.md queue block is stale — run: evidence tasks write-board` | 1 |
| `docs/MAP.md` absent | its own error, per task | `tasks: Z1: docs/MAP.md unreadable; cannot verify acceptance` (and `Z2`) | 1 |
| `docs/MAP.md` absent + attributed task | exempt | `waves: [[["M1"]]]` / `conflicts: none` | 0 |
| repo whose plans dir does not exist yet | no crash | only the MAP-name error for `evidence-unit`; parses and runs | 1 |
| `--draft` is a directory | `cannot read` | `tasks: --draft: cannot read …/drafts` | 2 |
| `--draft` mode 000 | `cannot read` | same shape | 2 |
| `--root` with no configured repo | usage error | `tasks: --draft: no configured repo has path …` | 2 |

Ordering note: the implementation tests (1) readable, then (3) the configured
repo, then (2) the plans dir — the contract numbers them 1/2/3, but (2) cannot
be evaluated before the repo is known. Behaviour is otherwise as contracted; not
a finding.

stdout/stderr discipline: the diff adds exactly six `print` calls — three to
`sys.stderr` (`cannot read`, `no configured repo has path`, `already under the
plans directory`) and three to stdout (`waves:`, `conflicts: none`, the
conflict rows). In every failing row above stdout was **empty**; in every
passing row stderr was **empty**. No stray print.

## Replan mode

`load_draft` computes `existing_subject_roots` from the repo's tasks **before**
it strips the same-basename plan, so a re-plan's own tasks stay exempt from the
already-landed clause; it then removes the old plan's tasks and extends with the
draft's (`pkgs/evidence/tasks.py:1063-1077`).

Live, against the tree at `/home/dalhaka/nixos-agent-env`, with a copy of
`docs/superpowers/plans/2026-09-06-planning-agent.md` under the same basename
and one `### P11` heading rewritten:

```
tasks: draft drops heading: ### P11 (code, S) — the driver guards behind A5: `FACTORY_PLAN` is required, a board rewrite outside the queue block is refused at integration, a near-miss result block is recorded verbatim as failed
exit=1
```

The same file **renamed** (`altered.md`, add mode) produces the contracted
duplicate message, one line per key:

```
tasks: nixos-agent-env/P1 defined in 2026-09-06-planning-agent.md and altered.md
tasks: nixos-agent-env/P12 defined in 2026-09-06-planning-agent.md and altered.md
… (12 rows; P13 is absent because it is attributed to dsh-harness)
exit=1
```

That is `check()`'s own `tasks: <repo>/<key> defined in <a> and <b>` — the
contracted message, unchanged.

Draft tasks are given state `landed` when their subject is already landed and
`ready` otherwise (`tasks.py:1078-1079`) — the same test `derive_status` rule 1
applies to a real plan, so the graph reads consistently. Mutating it to a flat
`ready` is killed by `test_draft_replan_keeps_headings`.

## Test 14 and the adaptation

**The contract cannot be met.** §P1 step 1 (14) requires each of
`2026-09-05-evidence-store.md`, `2026-09-05-seat-behind-broker.md`,
`2026-09-05-context-reset-ritual.md`, `2026-09-05-session-context.md`, copied
under the same basename and checked against `--root` = the tree, to **exit 0**.
I ran exactly that against the live tree with the branch's `tasks.py`:

```
===== 2026-09-05-evidence-store.md            exit=1  (16 stderr lines)
tasks: R7 acceptance (plus not in docs/MAP.md
tasks: R7 acceptance tests/run-mount-tests.sh not in docs/MAP.md
tasks: R7 acceptance run not in docs/MAP.md
… 11 more …
tasks: R7 commit subject (test: unit, lint; run-mount-tests both modes) differs from acceptance

===== 2026-09-05-seat-behind-broker.md        exit=1
tasks: draft lacks section Assumptions
tasks: draft lacks section Operator
tasks: SB4 acceptance seat-vm not in docs/MAP.md
tasks: SB4b acceptance seat-vm not in docs/MAP.md
tasks: SB4b commit subject (test: seat-vm, lint) differs from acceptance

===== 2026-09-05-context-reset-ritual.md      exit=1
tasks: draft lacks section Assumptions
tasks: draft lacks section Waves
tasks: draft lacks section Operator
tasks: CR2r2 commit subject session: … (test: unit, lint) shared by a different chain root
tasks: CR2r2b commit subject session: … shared by a different chain root
tasks: CR2r3 commit subject session: … shared by a different chain root

===== 2026-09-05-session-context.md           exit=1
tasks: draft lacks section Assumptions
```

Five independent reasons, each verified in the tree, not one:

1. **Rule (e).** `grep -n '^## '` on the four files: only
   `2026-09-05-evidence-store.md` carries all four house headers. The other
   three lack `## Assumptions`; two lack `## Operator`; one lacks `## Waves`.
2. **`parse_list` and R7.** `parse_list` splits on `[,\s]+`
   (`pkgs/evidence/tasks.py:93-94`), not on commas. R7's line is
   `**acceptance:** unit, lint (plus \`tests/run-mount-tests.sh\` run by the
   implementer and the reviewer, recorded in the commit body)`, so the
   acceptance list is **fourteen** tokens (`unit`, `lint`, `(plus`,
   `tests/run-mount-tests.sh`, `run`, `by`, `the`, `implementer`, `and`, `the`,
   `reviewer`, `recorded`, `in`, `the`, `commit`, `body)`). Rule (a) fires on
   every token that is neither `lint` nor a MAP name; rule (c) then fires
   because `{unit, lint; run-mount-tests both modes}` cannot equal that set.
   I reproduced the shape in isolation with a synthetic fixture and got the same
   fifteen lines. So yes — **rule (c) misjudges a legitimate subject**, and it
   does so because rule (a)'s input was already destroyed by `parse_list`.
3. **`seat-vm`** is a real acceptance name in a landed plan that
   `docs/MAP.md`'s Checks section does not list — rule (a) refuses it.
4. **The shared-subject rule.** `CHAIN_RE = ^(?P<root>.*\d)(?P<suffix>[a-z]{1,2})$`
   makes `CR2r2` and `CR2r3` **different** chain roots, and the house's own
   re-plan (rule A1: `<KEY>r`) deliberately keeps the subject. The contract's
   "two draft tasks with different chain roots may not share a subject" refuses
   the house's real practice.
5. None of these is fixable inside P1's `touches`: three of them are properties
   of files P1 may not edit.

**Verdict on the adaptation: the contract was wrong, not the test weakened.**
`plan_defect: wrong-fact`.

What the seat put in its place
(`tests/evidence/test_tasks.py:2287-2331`,
`test_draft_replan_all_landed_same_root_and_fake_consulted`): a synthetic
two-task `house.md` written into the fixture root, re-planned byte-identically
from `tmp_path`, with `monkeypatch.setattr(tk, "run", fake_git(subjects))`
returning both subjects — so the landed clause fires for every task and only the
same-root exemption can save them — plus the contract's own control row (a
fresh `Z9` carrying one of those subjects → refused) and a third row with the
fake returning `[]` → accepted, proving the fake is consulted.

The mutant the contract names for test 14 still dies:

```
M11 the same-chain-root exemption of the landed clause dropped: KILLED (rc=1)
    FAILED …::test_draft_replan_keeps_headings
    FAILED …::test_draft_already_landed_same_root_and_different_root
    FAILED …::test_draft_replan_all_landed_same_root_and_fake_consulted
M12 the landed clause dropped entirely: KILLED (rc=1)
```

So the substitute is not vacuous. What it loses is the *live* dimension —
see Findings, minor 1.

## Isolation and the flake

**Nothing outside `--root` is read.** An audit-hook probe
(`sys.addaudithook`, recording every `open` and every `subprocess.Popen`) around
`tk.main(["--root", <fixture>, …, "check", "--draft", <fixture draft>])`:

```
[probe] exit=0
[probe] opens recorded: 52
[probe] opens under /home/dalhaka/nixos-agent-env: 0
[probe] opens under /home/dalhaka (outside scratch): 0
[probe] subprocesses: git -C <fixture root> log --format=%s   (×2)
waves: [[["Z1"]], [["Z2"]]]
conflicts: none
```

`configured_repos` still come from `<root>/docs/ledger/repos.toml`, as
Assumption 6 records, which is why the live one-repo run accepts `P13`'s
`**repo:** dsh-harness` without an "unconfigured repo" error.

**The flake.** `flake.nix:1113-1120` adds `mkdir -p … docs/superpowers`,
`cp -r ${self}/docs/superpowers/plans docs/superpowers/plans` and
`cp ${self}/docs/MAP.md docs/MAP.md` to `checks.evidence-unit` — exactly the two
contracted lines. `nix build .#checks.x86_64-linux.evidence-unit -L --no-link
--rebuild` → `124 passed`.

They are, however, **dead**. `HERE.parents[2]` appears once in
`tests/evidence/test_tasks.py` (line 16, to import `tasks.py`); no test reads
`docs/superpowers/plans` or `docs/MAP.md` from the copied tree. I removed both
lines, `git add flake.nix`, and built the check fresh:

```
building '/nix/store/fm75q95rvyrg41gs455jw67whv0ki22d-evidence-unit.drv'...
evidence-unit> 124 passed in 4.84s
```

Green without them. (flake.nix restored; `git status --porcelain` empty,
`HEAD` still `d26333f`.)

## Tests and mutants

`124 passed` (`nix develop -c pytest tests/evidence -q`), of which 18 are the
new draft tests. The old file's 71 test functions are all present and unchanged
— `comm -23` of the sorted `def test_` lines of `91dcc5f` against `HEAD` is
empty, and the diff is `+347 / −0`.

Apply → `pytest -k draft` → revert, one mutant at a time
(`<scratch>/mx/mutants.py`, `mutants2.py`):

| mutant | verdict | first killer |
|---|---|---|
| the draft not merged into the repo's task list | KILLED | `test_draft_duplicate_key_across_plans` (+4 more) |
| the MAP lookup dropped | KILLED | `test_draft_acceptance_name_not_in_map` |
| rule (b) dropped | KILLED | `test_draft_glob_touch_is_not_explicit` |
| set-compare → string-compare | KILLED | `test_draft_subject_names_compared_as_a_set` |
| unfiltered waves | KILLED | `test_draft_sound_prints_waves_and_conflicts` |
| cross-plan conflict rows skipped | KILLED | `test_draft_content_printed_on_draft_conflict` |
| the realpath test skipped | KILLED | `test_draft_inside_plans_dir_is_a_usage_error` |
| byte-identical heading test made prefix-only | KILLED | `test_draft_replan_drops_heading` |
| the "defined twice" rule dropped | KILLED | `test_draft_duplicate_key_within_one_file` |
| rule (e) dropped | KILLED | `test_draft_missing_assumptions_header` |
| the same-chain-root exemption dropped | KILLED | 3 tests |
| the landed clause dropped entirely | KILLED | 2 tests |
| draft state forced `ready` | KILLED | `test_draft_replan_keeps_headings` |

**13 / 13 killed.** Restored: `124 passed`.

## Checks

| command | result |
|---|---|
| `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `23 files already formatted` |
| `nix develop -c pytest tests/evidence -q` | `124 passed in 3.65s` |
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | `124 passed`, exit 0 |
| `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | `All checks passed!`, exit 0 |
| `nix develop -c githooks/pre-commit` | exit 0; working tree stayed clean (no board rewrite owed) |
| `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | reproduced byte-for-byte |
| `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |
| board mask: `awk '/tasks:begin/{s=1} !s{print} /tasks:end/{s=0}'` on `91dcc5f` vs `d26333f`, `cmp -s` | **identical** — the board change is confined to the queue block |

**The live run.** Against `/home/dalhaka/nixos-agent-env` at its current head,
with a tmp copy of `docs/superpowers/plans/2026-09-06-planning-agent.md` and a
one-repo `--repos` file:

```
waves: [[["P1", "P12"], ["P11"], ["P4", "P4b"], ["P6", "P6b"]], [["P2"], ["P3A"]], [["P10"], ["P5"], ["P8"]], [["P13"]]]
conflicts: CR4 (2026-09-05-context-reset-ritual.md) × P12 (2026-09-06-planning-agent.md): githooks/pre-commit ~ githooks/pre-commit
conflicts: CR4 (2026-09-05-context-reset-ritual.md) × P4  (…): docs/runbooks/session.md ~ docs/runbooks/session.md
conflicts: CR4 (2026-09-05-context-reset-ritual.md) × P4b (…): docs/runbooks/session.md ~ docs/runbooks/session.md
exit=0   (stderr empty)
```

This reproduces the seat's pasted block modulo the tree having moved since
(`P4b`, `P6b` and `CR2r3` are new; with `--runs-dir /nonexistent` I get the
seat's twelve-row shape, `SB4`/`SB4b` on `flake.nix` included). Note the plan's
own **Step 3** says the live run prints `conflicts: none`; the plan's **Waves**
section (line 54) says the same command prints three rows live and seven more
under `--runs-dir /nonexistent`. The Waves section is right and Step 3 is
wrong — the seat pasted the truth. Consequently the "exactly two lines on
stdout" expectation holds only for the `conflicts: none` case, which is what
the contract's interface text actually says.

## Red before green

`git show 91dcc5f:pkgs/evidence/tasks.py > pkgs/evidence/tasks.py` with this
branch's tests, `nix develop -c pytest tests/evidence/test_tasks.py -q -k draft`:

```
tasks: error: unrecognized arguments: --draft /tmp/…/dup-in-draft.md
…
18 failed, 71 deselected in 1.31s
```

All eighteen, each on argparse's `SystemExit: 2`:
`test_draft_duplicate_key_across_plans`, `…_unknown_dependency`,
`…_acceptance_name_not_in_map`, `…_glob_touch_is_not_explicit`,
`…_size_l_refused`, `…_subject_names_compared_as_a_set`,
`…_missing_assumptions_header`, `…_sound_prints_waves_and_conflicts`,
`…_content_printed_on_draft_conflict`, `…_inside_plans_dir_is_a_usage_error`,
`…_unreadable_is_a_usage_error`, `…_no_configured_repo_for_root`,
`…_replan_drops_heading`, `…_replan_keeps_headings`,
`…_already_landed_same_root_and_different_root`,
`…_attributed_task_exempt_from_acceptance`,
`…_replan_all_landed_same_root_and_fake_consulted`,
`…_duplicate_key_within_one_file`.

Restored → `124 passed`.

## Findings

No MAJORs.

**Minor 1 — test 14's live dimension was dropped, and with it the only
consumer of the flake's two copy lines.** `flake.nix:1118-1119`. The plan
defect justified replacing the four-house-plan assertion; it did not require
abandoning the live tree. A faithful substitute was available and I verified it
would be green: `check --draft <copy of docs/superpowers/plans/2026-09-06-planning-agent.md>`
against `--root` = the tree exits 0 today. As shipped, no automated test reads
`docs/superpowers/plans` or `docs/MAP.md` from the sandbox, and `evidence-unit`
builds green with both `cp` lines deleted (shown above). The lines are
contracted and inside `touches`, so they are not a deviation — they are simply
inert until P3A or a later task uses them.

**Minor 2 — one message covers two different failures.**
`pkgs/evidence/tasks.py:1155-1159`. A subject that fails the shape regex
outright is reported as
`tasks: <key> commit subject (test: ?) differs from acceptance`. The `?` is an
invention (the contract gives only the set-mismatch wording) and it reads as
though the names differ when in fact the subject is malformed — e.g. a task
with no `**commit subject:**` line at all produces exactly that. A distinct
"commit subject does not match the house shape" line would be clearer for the
planner reading stderr.

**Minor 3 — `git log` runs twice per invocation.**
`pkgs/evidence/tasks.py:1058` calls `landed_subjects(scanned_repo["path"])`
although the graph scan has already run the same command; the audit probe shows
both. Harmless (20 s timeout, one repo), but the second call is free to avoid.

**Minor 4 — the contracted shared-subject rule refuses the house's own
re-plan practice.** `pkgs/evidence/tasks.py:1170-1180` implements the contract
faithfully; the contract is the problem. `CHAIN_RE` makes `CR2r2` and `CR2r3`
different roots, and `docs/superpowers/plans/2026-09-05-context-reset-ritual.md`
deliberately gives `CR2r2`, `CR2r2b` and `CR2r3` one subject (rule A1: a
re-plan is `<KEY>r`, a new root, keeping the work's subject). The first draft
the planning agent writes that carries a re-plan of an existing task will be
refused for doing the right thing. Worth folding into P3A or a P1b.

**Minor 5 — rule (a) will refuse acceptance names the tree really uses.**
`seat-vm` is the acceptance of `SB4`/`SB4b` in
`docs/superpowers/plans/2026-09-05-seat-behind-broker.md` and is not in
`docs/MAP.md`'s Checks section (it is a VM test, not a flake check name). Any
draft naming it is refused. Again the contract, not the code.

Not findings, checked and clear: no landed plan is turned red by `draft_rules`
(they run over `draft["tasks"]` only, and the live add-mode run exits 0 with
`2026-09-05-evidence-store.md` and its R7 sitting in the tree); every touched
file is inside `touches` except `docs/MAP.md` (regenerated by rule — the count
change makes the lint block's MAP diff red otherwise, and `repomap.py write`
reproduces the committed file exactly) and `docs/OPERATIONS.md` (queue block
only, proved by the awk mask + `cmp`); exactly one commit; subject
byte-identical (`cmp` against the plan's `**commit subject:**`); trailers
`Generated-By` then `Co-Authored-By`, the WORKSPACE RULES order; the result
block is `FACTORY-RESULT status=done` — label, one space, `status=`, no colon,
no markdown.

## Verdict

**APPROVED.** Every contracted rule fires with its contracted message and exit
code; realpath, relative paths and symlinks are all handled; the attributed-repo
exemption and the chain-root exemption both behave as specified; isolation is
proved, stdout is clean, thirteen mutants die, every check is green, and the
commit convention holds. The one contract item the seat could not meet — test
14 — is unsatisfiable as written for five verified reasons, and the substitute
still kills the mutant the contract names for it. The residue is five minors,
none of which blocks the landing; minors 4 and 5 are the ones to fold into the
next planning-agent task, because they will bite the first real draft.

plan_defect: wrong-fact — test 14's four house plans cannot exit 0
