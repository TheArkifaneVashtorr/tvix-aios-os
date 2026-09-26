---
plan_defect: implementer
plan_defect_secondary: wrong-fact
mutants_total: 11
mutants_killed: 9
mutants_outside_named: 1
---
# Opus gate — seat run pa10, task P10 — REJECTED

## Summary

Branch `task/P10`, base `3937d98`, head `3a7994b`, ONE commit, 16 files
(+596/−1), subject byte-identical to the plan's, both trailers, every touched
file inside `touches` plus `docs/MAP.md` by rule (`repomap.py write` reproduces
it exactly). Reviewed in a fresh clone
(`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/1a867da7-fe9a-4370-b33f-d6d080d0afad/scratchpad/gate-pa10-P10`);
nothing under `/home/dalhaka/factory` or `/home/dalhaka/nixos-agent-env` was
modified except this file, and every run used `--store /nonexistent` or a
scratch store.

Most of the task is right: the header, the six lines, the exit-2 paths, the
`--plan` scoping, the threshold's `min` with ties and the "no score separates"
branch, the `—/0` join for a plan absent from the repo, the survivors line and
its `unmeasured` fallback all behave as contracted, and my independent hand
tally of the chain rule reproduces the report's live figures digit for digit.
Three MAJORs stop it.

Line 2 does not implement the rule §P10 states. `report.py:126` calls
`tasks.plan_defect_record`, which is P3A's **seven-day** record, where §P10 says
"over all rejection rows". It prints `45/48` on this branch only because every
seeded row is dated 2026-09-04…06 and `--today` defaults to today; move `--today`
and the figure moves (`--today 2026-09-12` → `39/42`, `--today 2026-09-20` →
`0/0 (0%)` — a 0 % plan-caused share, printed as a conclusion, with no refusal).
The same call also counts an APPROVED review carrying a `plan_defect` block as a
rejection row: with `front_matter_from` in the past my fixture prints `2/3 (67%)`
where the contract yields `2/2 (100%)`. `front_matter_from` is 2026-09-07, so
that dilution starts tomorrow.

Third, the design's own named mutant survives: lowering the n-gate default from
5 to 2 leaves all 165 evidence tests green, because `test_refuses_below_min_n`
passes `min_n=5` explicitly and no test ever exercises the default.

The stated difference on lines 1/3/4 is honest and I confirm it independently —
but the design's tally is the wrong fact, not the seat's scope choice, and the
commit body's diagnosis of *why* is incomplete (see below).

## The chain rule and the corpus (hand tally)

Rule applied by hand (my own script, no import of `report.py`): a chain is a
`tasks.chain_root` key with ≥ 1 review among its members; first-try = the root's
own review is `APPROVED`; landed = the last member's review is `APPROVED`;
re-plan = a member whose suffix contains `r`.

Scope note first: `ls docs/superpowers/plans/2026-09-05-*.md` is **thirteen**
files, twelve of which carry typed tasks (`2026-09-05-night-plan.md` has none),
not the "ten typed 2026-09-05 plans" the Facts paragraph names.

The 63 gated chains over the twelve typed 2026-09-05 plans:

| root | plan | root verdict | first-try | re-plan | landed | rounds | members |
|---|---|---|---|---|---|---|---|
| B1 | backup-audit-paths | (none) | no | no | yes | 2 | B1, B1b, B1c |
| CR1 | context-reset-ritual | REJECTED | no | no | yes | 1 | CR1, CR1b |
| CR2 | context-reset-ritual | REJECTED | no | **yes** | no | 3 | CR2, CR2b, CR2r, CR2rb |
| CR2r2 | context-reset-ritual | REJECTED | no | no | no | 1 | CR2r2, CR2r2b |
| CR2r3 | context-reset-ritual | REJECTED | no | no | no | 0 | CR2r3 |
| CR3 | context-reset-ritual | REJECTED | no | **yes** | yes | 3 | CR3, CR3b, CR3r, CR3rb |
| CR5 | context-reset-ritual | APPROVED | **yes** | no | yes | 0 | CR5 |
| X1med / X1xhigh / X2med / X2xhigh | effort-comparison | APPROVED ×4 | **yes** ×4 | no | yes ×4 | 0 | singletons |
| E1 | evidence-store | APPROVED | **yes** | no | yes | 1 | E1, E1b |
| E2 | evidence-store | REJECTED | no | **yes** | yes | 2 | E2, E2b, E2r |
| E3 / E4 / E5 / E8 | evidence-store | APPROVED ×4 | **yes** ×4 | no | yes ×4 | 0 | singletons |
| E6 | evidence-store | REJECTED | no | no | yes | 1 | E6, E6b |
| E7 | evidence-store | REJECTED | no | **yes** | yes | 2 | E7, E7b, E7r |
| E9 | evidence-store | REJECTED | no | no | yes | 1 | E9, E9b |
| R1 | evidence-store | REJECTED | no | no | yes | 1 | R1, R1b |
| R2 / R4 / R7 / R9 / R10 | evidence-store | APPROVED ×5 | **yes** ×5 | no | yes ×5 | 0 | singletons |
| R3 | evidence-store | REJECTED | no | **yes** | yes | 3 | R3, R3b, R3r, R3rb |
| R5 | evidence-store | REJECTED | no | no | yes | 1 | R5, R5b |
| R8 | evidence-store | REJECTED | no | no | yes | 1 | R8, R8b |
| FD1 | factory-dispatch | REJECTED | no | no | yes | 1 | FD1, FD1b |
| H2 | harness-router | REJECTED | no | no | yes | 2 | H2, H2b, H2c |
| P0 | model-comparison | APPROVED | **yes** | no | yes | 0 | P0 |
| P1flash | model-comparison | REJECTED | no | no | **no** | 0 | P1flash |
| P1flashb / P1pro / P2flash / P2pro | model-comparison | APPROVED ×4 | **yes** ×4 | no | yes ×4 | 0 | singletons |
| P3 | model-comparison | REJECTED | no | no | yes | 1 | P3, P3b |
| DA1 | operator-items | REJECTED | no | no | yes | 1 | DA1, DA1b |
| PB0 / PB1 | operator-items | APPROVED ×2 | **yes** ×2 | no | yes ×2 | 0 | singletons |
| SB1 | seat-behind-broker | APPROVED | **yes** | no | yes | 0 | SB1 |
| SB2 | seat-behind-broker | REJECTED | no | **yes** | yes | 2 | SB2, SB2b, SB2r |
| SB3 | seat-behind-broker | REJECTED | no | no | yes | 1 | SB3, SB3b |
| SB4 | seat-behind-broker | (none) | no | no | yes | 1 | SB4, SB4b |
| OG1 | seat-routing | REJECTED | no | **yes** | **no** | 2 | OG1, OG1b, OG1r |
| OG1r2 | seat-routing | REJECTED | no | no | yes | 1 | OG1r2, OG1r2b |
| RT1 | seat-routing | REJECTED | no | no | yes | 1 | RT1, RT1b |
| RT2 | seat-routing | REJECTED | no | no | yes | 1 | RT2, RT2b |
| RT4 | seat-routing | APPROVED | **yes** | no | yes | 0 | RT4 |
| RT5 | seat-routing | REJECTED | no | **yes** | yes | 3 | RT5, RT5b, RT5r, RT5rb |
| G1 / G2 / G5 / G7 / G10 | session-context | REJECTED ×5 | no | no | yes ×5 | 1 each | X, Xb |
| G3 / G6 / G9 | session-context | APPROVED ×3 | **yes** ×3 | no | yes ×3 | 0 | singletons |
| G4 | session-context | APPROVED | **yes** | no | yes | 1 | G4, G4b |
| G8 | session-context | (none) | no | no | yes | 2 | G8, G8b, G8c |
| G11 | session-context | REJECTED | no | **yes** | yes | 2 | G11, G11b, G11r |
| G12 | session-context | REJECTED | no | **yes** | yes | 2 | G12, G12b, G12r |

Totals by hand:

| line | by hand, 2026-09-05 scope | by hand, all plans (clone) | the report (clone) | the design §7 |
|---|---|---|---|---|
| 1 first-try | 28/63 (44 %) | 31/69 (45 %) | `31/69 chains (45%)` | 28/58 = 48 % |
| 3 re-plan | 10/63 | 10/69 | `10/69 chains` | 11/58 = 19 % |
| 4 rework (rounds over *gated* chains) | 52/58 = 0.90 | 54/63 = 0.86 | `54/63 = 0.86` | 30/58 ≈ 0.52 |
| 4 rework (rounds over *landed* chains) | 46/58 = 0.79 | 48/63 = 0.76 | — | — |

**The design's tally is the wrong fact, and the seat's report of a difference is
correct — but its explanation is not the whole one.** Three separate things:

1. **The denominator.** The design's `58` is not "chains gated"; it is the number
   of *landed* chains, which my hand tally also makes exactly 58 over the
   2026-09-05 plans. Under §7's own definition ("chains approved at their first
   gate ÷ chains gated") the rule yields **28/63**. The numerator 28 is right.
   The design's row for rework says "÷ landings", so it used landings for all
   three rows. This is the single biggest source of the difference and the commit
   body does not name it.
2. **Re-plan 11 vs 10.** No reading of the rule I tried yields 11; the ten
   re-plan chains are CR2, CR3, E2, E7, R3, SB2, RT5, OG1, G11, G12.
3. **Rework 30.** Neither reading gets near 30 (46 or 52 over the same chains).

**Scope: contracted, not the seat's error.** §P10's Interfaces sentence says
line 1 is "per plan when `--plan` is given, **else over every typed plan**"; the
Facts paragraph says the figures must match "when computed over the ten typed
2026-09-05 plans". Those are two different scopes and the plan asserts both. The
seat implemented the Interfaces sentence — the behavioural contract — and
disclosed the choice. Not a finding against the seat. Worth recording for the
re-plan: the 2026-09-05 view is not reachable from the CLI at all, because
`--plan` takes one basename and does not glob (`--plan '2026-09-05-*.md'` →
`refused: n=0 < 5`), so the contract's own verification cannot be run.

**`chain_root`'s suffix limit is real but small.** `CHAIN_RE` is
`^(.*\d)([a-z]{1,2})$`, so `CR2r2`, `CR2r3` and `OG1r2` are roots of their own
(their keys end in a digit). Merging them would drop n from 69 to 66 and *raise*
the first-try rate from 45 % to 47 %; the commit body's "the repo-wide figures
run higher" is the wrong direction for the rate.

**Line 4's rule contradicts the plan's own worked example.** §P10 says "rounds =
members beyond the root across **landed** chains"; §P10 Step 1 says the fixture
must print `3/4 = 0.75`. In that fixture the E1 chain (E1 REJECTED → E1r
REJECTED) is gated and *not* landed and carries one round, so "across landed
chains" gives `2/4 = 0.50` and only "across all gated chains" gives 3. The seat
matched the byte-exact worked example. I do not count this against the seat, but
it is a plan defect and it is why line 4 reads 54/63 rather than 48/63.

## Line 2 on both trees

Hand count of `docs/ledger/plan-defects.toml`:

| tree | rows | vacuous | missing-case | underspecified | wrong-fact | implementer | process | plan-caused | report prints |
|---|---|---|---|---|---|---|---|---|---|
| clone (branch base) | 48 | 15 | 16 | 8 | 6 | 2 | 1 | 45 | `plan-caused share of rejections: 45/48 (94%)` |
| live (`/home/dalhaka/nixos-agent-env`) | 54 | 15 | 19 | 9 | 7 | 3 | 1 | 50 | `plan-caused share of rejections: 50/54 (93%)` |

Both match by hand, as the implementer claimed for the branch, and the live tree
gives the expected `50/54`. But the figure is right by coincidence of dates:

```
--today 2026-09-05  -> plan-caused share of rejections: 44/47 (94%)
--today 2026-09-06  -> plan-caused share of rejections: 45/48 (94%)
--today 2026-09-12  -> plan-caused share of rejections: 39/42 (93%)
--today 2026-09-20  -> plan-caused share of rejections: 0/0 (0%)
```

`report.py:126` is `tasks.plan_defect_record([{"path": repo}], today_d)`, whose
docstring is "The seven-day rejection record"; §P10 says "over all rejection
rows". Every seeded row is dated 2026-09-04…06, so today's window happens to
contain all 48 (54).

Blocks: `front_matter_from = 2026-09-07`, so no review block is counted yet on
either tree. I built a fixture with `front_matter_from = 2026-09-01`, one ledger
row (`vacuous`), one **REJECTED** `…opus-review…` block (`plan_defect:
missing-case`) and one **APPROVED** block (`plan_defect: none`), all inside the
window:

```
plan-caused share of rejections: 2/3 (67%)      # what the code does
                                 2/2 (100%)     # what "over all rejection rows" yields
```

`tasks.plan_defect_record` counts *any* review whose front matter carries a
`plan_defect`, verdict-blind, so an APPROVED gate carrying `plan_defect: none`
lands in the denominator of a "share of rejections". The root cause sits in
`tasks.py:1037-1051` (P3A), but §P10's line 2 is the contract being broken here,
and from 2026-09-07 every APPROVED review dilutes the figure.

## The six cases

Driven through `evidence.py … report plans` (not the library) unless noted.

| case | result |
|---|---|
| Step 1 (1) fixture repo + fixture store | `2/5 (40%)`, `1/5 (20%)`, `1/5`, `3/4 = 0.75` — byte-exact, matches the plan's hand computation |
| (2) `--min-n 5`, four chains | `refused: n=4 < 5 (no conclusion under five)`, no line 1 ✔ |
| n-gate at exactly 5 | prints (`first-try landing rate: 5/5 chains (100%)`) ✔ |
| `--min-n 2` on four chains | prints all four lines ✔; on one chain the message is `refused: n=1 < 2 (no conclusion under five)` — the parenthetical is hardcoded |
| (3) one judgement | `rubric score before dispatch: n=1, refused` ✔ |
| (3) six judgements, a plan absent from the repo | `plan0.md total 30 decision dispatch first-try —/0` ✔ |
| (4) ten dispatched, totals 36/38/35/41 + six under 70 % | `threshold proposal: 35` ✔ |
| (4) tie at the minimum (two plans at 35) | `threshold proposal: 35` ✔ |
| (4) all ten under 70 % | `no score separates ≥ 70% first-try plans yet` ✔ |
| (4) nine dispatched | no line 6, no "no score" line ✔ |
| (5) `mutants_outside_named` on two of four reviews | `survivors outside the named set: 10/2` ✔; absent → `unmeasured (no review carries mutants_outside_named)` ✔ |
| (6) `--plan keep.md` / `drop.md` / unset | `5/5 (100%)` / `0/5 (0%)` / `5/10 (50%)` ✔ |
| `--today`'s effect | line 2 only (it is the only consumer of `today`) — see above |
| unreadable store (`chmod 000 plans.jsonl`) | `report: cannot read store …: [Errno 13] Permission denied` on stderr, **exit 2** ✔ |
| unreadable repo | `report: cannot read repo /…/nope`, **exit 2** ✔ |
| empty store | line 5 `n=0, refused`; lines 1–4 from the repo ✔ |
| `--today notadate` | uncaught `ValueError: Invalid isoformat string`, traceback, **exit 1** — contract says exit 0 always except store/repo (exit 2) |
| the same plan judged twice (a revision row) | two join lines for one plan, and `j` counts rows, not plans |

## Tests and mutants

165 evidence tests green in the devShell and in the `evidence-unit` derivation.
11 mutants applied to `pkgs/evidence/report.py`, `pytest tests/evidence` after
each, reverted after each; 9 killed.

| # | mutant | named in §P10? | result |
|---|---|---|---|
| M1 | a `b` member counted as a re-plan | yes | **killed** (corpus test) |
| M2 | the open chain counted (`gated = list(roots)`) | yes | **killed** |
| M3 | the n-gate default lowered from 5 to 2 | **yes — the design's own** | **SURVIVED** |
| M4 | `max` instead of `min` for the threshold | yes | **killed** |
| M5 | the join keyed on the full `plan` path, not the basename | yes | **killed** |
| M6 | the plan class set widened to include `implementer` | yes | **killed** |
| M7 | survivors `gates` counted over every review | yes | **killed** |
| M8 | the n-gate on line 5 dropped | yes | **killed** |
| M9 | `--plan` ignored | yes | **killed** |
| M10 | rounds counted across landed chains only (the plan's prose rule) | no | killed (the test locks the worked example) |
| M11 | line 2 over ALL ledger rows, no seven-day window (the contracted rule) | no | **SURVIVED** |

M3 is the plan's own mutant ("lower the gate to 2 → the refusal fixture prints →
fails — the design's mutant"). It survives because `test_report.py:119` passes
`min_n=5` explicitly:

```python
lines = rp.plans_report(str(store), str(repo), today="2026-09-06", min_n=5)
```

I also lowered the argparse default (`p.add_argument("--min-n", type=int,
default=2)`) at the same time: **165 passed**. Nothing in the suite pins the
default 5, and no test drives `main()` down the plans path at all except the
exit-2 case.

M11 survives because every fixture ledger row is dated inside the window, so the
suite cannot tell the contracted rule from the implemented one.

## Checks

All run inside the clone, in the devShell.

| check | result |
|---|---|
| `ruff check pkgs/evidence tests/evidence` | `All checks passed!` |
| `ruff format --check pkgs/evidence tests/evidence` | `54 files already formatted` |
| `pytest tests/evidence -q` | `165 passed in 4.82s` |
| `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` | built, `165 passed in 4.60s` |
| `nix build .#checks.x86_64-linux.lint -L --no-link` | exit 0 |
| `githooks/pre-commit` | **exit 1**: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again`; exit 0 once the regenerated block is staged. The base `3937d98` passes clean, so this commit is what makes the block stale (P10 leaves the queue). Global Constraints call the regenerate-and-commit-again path "still ONE commit"; every prior wave has the orchestrator regenerating the block at integration instead, so I record it, not count it as a MAJOR. |
| `repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | no diff — the `+1/−1` (37 → 49) is reproduced exactly |
| `tasks.py --root . check` | silent, exit 0 |
| `claims.py validate docs/ledger/claims.toml --today 2026-09-06` | silent, exit 0 |
| stdout discipline | header first; every figure carries its n; **0 bytes on stderr** on success |
| runbook | the four lines match the code — including the seven-day window, which the runbook documents and §P10 contradicts |

Live output on this tree (`--store /nonexistent report plans --repo .`, clone):

```
# evidence report plans — proxies for docs/superpowers/specs/2026-09-05-planning-agent-design.md §7; n printed with every figure
first-try landing rate: 31/69 chains (45%)
plan-caused share of rejections: 45/48 (94%)
re-plan rate: 10/69 chains
rework rounds per landed task: 54/63 = 0.86
rubric score before dispatch: n=0, refused
```

and on the live tree (54 ledger rows, two more reviews):

```
first-try landing rate: 31/70 chains (44%)
plan-caused share of rejections: 50/54 (93%)
re-plan rate: 10/70 chains
rework rounds per landed task: 55/63 = 0.87
rubric score before dispatch: n=0, refused
```

## Red before green

`3937d98`'s tree (no `report.py`) with this branch's tests, in a detached
worktree:

```
E   FileNotFoundError: [Errno 2] No such file or directory: '…/pkgs/evidence/report.py'
ERROR ../red/tests/evidence/test_report.py - FileNotFoundError
1 error in 0.11s
```

A genuine red — collection fails without the module — but not the contracted
`ModuleNotFoundError: report`, because `load()` uses
`importlib.util.spec_from_file_location` rather than `import report`. Restoring
the branch: 165 passed.

## Findings

### MAJOR 1 — line 2 is a seven-day window, not "over all rejection rows"

`pkgs/evidence/report.py:126`

```python
        record = tasks.plan_defect_record([{"path": repo}], today_d)
```

`tasks.plan_defect_record` (`pkgs/evidence/tasks.py:1021`, "The seven-day
rejection record") filters `start = today - 7 days ≤ date ≤ today`. §P10: "from
the ledger plus blocks, `plan_defect` primary in the four plan classes **over all
rejection rows**". The contracted figure is reproduced today only because the
seed's newest row is 2026-09-06:

```
--today 2026-09-12 -> plan-caused share of rejections: 39/42 (93%)
--today 2026-09-20 -> plan-caused share of rejections: 0/0 (0%)
```

`0/0 (0%)` is printed as a conclusion — the n-gate covers only the chain count,
so a zero-row line 2 is never refused. Untested: M11 (replacing the window with
the contracted all-rows count) leaves all 165 tests green. The runbook
(`docs/runbooks/evidence.md:113`) documents the window rather than the contract,
and the commit body does not state this difference.

### MAJOR 2 — an APPROVED review counts as a rejection row in line 2's denominator

`pkgs/evidence/report.py:126` → `pkgs/evidence/tasks.py:1041-1050`

```python
                pd = block.get("plan_defect")
                if pd is not None:
                    block_primary["docs/reviews/" + path.name] = pd
```

No verdict test. Fixture with `front_matter_from = 2026-09-01`, one ledger row
(`vacuous`), one REJECTED block (`missing-case`) and one APPROVED block
(`plan_defect: none`):

```
plan-caused share of rejections: 2/3 (67%)     # actual
plan-caused share of rejections: 2/2 (100%)    # "over all rejection rows"
```

Latent on this tree only because `front_matter_from` is 2026-09-07 — from
tomorrow every APPROVED gate review dilutes the headline number the operator
reads. The root cause is in P3A's helper; §P10's line 2 is the contract broken.
No test in `test_report.py` puts a block in the window at all.

### MAJOR 3 — the design's named mutant survives: the n-gate default is untested

`tests/evidence/test_report.py:119`

```python
    lines = rp.plans_report(str(store), str(repo), today="2026-09-06", min_n=5)
```

The one refusal test passes `min_n=5` explicitly, so the default is never
exercised. Lowering it to 2 in both `plans_report`'s signature and the argparse
default leaves **165 passed**. §P10 names exactly this mutant as the one the
refusal fixture must kill ("the design's mutant"). A vacuous test for the task's
headline behaviour — "a refusal under five plans" is in the commit subject.

## Minors

1. `pkgs/evidence/report.py:121` — the refusal's parenthetical is hardcoded:
   `--min-n 2` prints `refused: n=1 < 2 (no conclusion under five)`.
2. `pkgs/evidence/report.py:101` — `--today notadate` raises an uncaught
   `ValueError` and exits 1 with a traceback; §P10 says exit 0 always except an
   unreadable store or repo (exit 2 with a message).
3. `pkgs/evidence/report.py:164` — the join iterates rows, not plans: a plan
   judged twice (P6 carries `revision`) prints two lines and counts twice
   towards `j` and towards line 6's "ten judged plans".
4. `pkgs/evidence/report.py:133,155` — `0/0 (0%)` and `0/0 = 0.00` are printed
   as figures; a zero-denominator line ought to refuse the way the n-gate does.
5. `pkgs/evidence/report.py:207` — `--plan` matches one basename with no
   globbing, so the Facts paragraph's own scope (the 2026-09-05 plans) cannot be
   produced by the CLI.
6. `tests/evidence/test_report.py:26-44` — `load()` file-loads the module, so the
   contracted red (`ModuleNotFoundError: report`) can never be the message; the
   red is real but reads `FileNotFoundError`.
7. Commit body — §P10 Step 3 asks for all lines of the live run pasted; the body
   paraphrases the figures in prose instead, and its causal account of the
   difference omits the largest cause (the design used landings, 58, as the
   denominator) and misstates the direction of the suffix-limit effect (splitting
   raises n and *lowers* the rate).
8. `docs/runbooks/evidence.md:113` — documents the seven-day window as if it were
   the rule; it contradicts §P10 and should not have been written down as
   correct without a note.
9. No test drives the `plans` CLI path end to end (only `main()`'s exit-2 case),
   so the `evidence.py` dispatch of `report` and the `--store` forwarding are
   exercised nowhere.

## Plan defects (not counted against the seat)

- **wrong-fact.** §7's "today" column: `28/58`, `11/58`, `30/58`. The rule as
  written yields `28/63`, `10/63` and `46/58`(prose)/`52/58`(example) over the
  2026-09-05 plans. `58` is the count of *landed* chains, not chains gated; the
  re-plan figure is one high and the rework numerator is far low. Reported
  honestly by the seat, as the plan requires.
- **wrong-fact.** "the ten typed 2026-09-05 plans (`ls
  docs/superpowers/plans/2026-09-05-*.md`)" — that glob is thirteen files, twelve
  of them typed.
- **underspecified.** Line 4's prose ("rounds = members beyond the root across
  landed chains") contradicts Step 1's byte-exact expectation (`3/4 = 0.75`,
  which needs rounds over all gated chains). The seat matched the example.
- **underspecified.** Line 1's scope: Interfaces says "over every typed plan",
  Facts says "over the ten typed 2026-09-05 plans". Both are in §P10.

## Verdict

**REJECTED** on three MAJORs: line 2 implements P3A's seven-day record instead of
the contracted "all rejection rows" (0/0 (0%) within a fortnight, undisclosed and
untested); line 2's denominator counts APPROVED reviews as rejections from
2026-09-07; and the design's own named mutant — the n-gate default lowered to 2 —
survives the whole suite because the only refusal test hardcodes `min_n=5`.
Everything else in the task is sound, the chain arithmetic is exactly right, and
the stated difference against the design is honest and independently confirmed
(with a fuller explanation above for the re-plan to carry).
