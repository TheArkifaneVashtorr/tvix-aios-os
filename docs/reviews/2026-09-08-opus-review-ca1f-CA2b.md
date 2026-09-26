---
plan_defect: none
mutants_total: 23
mutants_killed: 17
mutants_outside_named: 16
---
# Opus gate — seat run ca1f, task CA2b — APPROVED

## Summary

CA2b is the fix round for `### CA2`, and it closes the ca1 gate's two MAJORs and its six
MINORs. The diff against `ef7830f` carries CA2's code and tests plus this round's: one
commit, two files, `pkgs/evidence/tasks.py | 71 +` and
`tests/evidence/test_tasks.py | 407 +`. The code is CA2's byte for byte except item 6 —
the inert `now=graph.get("now")` seam is gone (`git diff --no-index` of `HEAD`'s
`tasks.py` against CA2's `4ca0fe6` shows exactly that one hunk and nothing else).

The two mutants that survived at ca1 are dead:

```
===== M1 (key=lambda r: (r["model"],)) exit=1
E   AssertionError: assert '**Seats (7 d...n, 165 billed' == '**Seats (7 d...min, 0 billed'
FAILED tests/evidence/test_tasks.py::test_seats_line_sums_per_model_ordering_and_last_status

===== M3 (glob "*" instead of "*.result") exit=1
E   AssertionError: assert 3 == 1
FAILED tests/evidence/test_tasks.py::test_seats_ignores_aged_logs_and_dotfiles
```

All **seven** mutants the section names are killed; of sixteen I tried outside that set,
ten more die. Every acceptance check is green from the fresh clone with `--rebuild`
(`evidence-unit> 463 passed in 12.70s`, `lint` exit 0), `ruff check` / `ruff format
--check` clean, `repomap.py write` leaves `docs/MAP.md` unchanged, `tasks.py check`
silent. The subject is byte-identical to the section's; the body pastes every mutant red
and the greens.

Nothing here is a MAJOR. Two things the orchestrator should see anyway:

- **The seven-day cutoff lost its only test in this round.** CA2's S2 asserted an
  8-day-old `old-model` was dropped; item 2's replacement text specifies the aged
  `.log`/`.pid`/dot-file *and one aged-1-d `inside-model`* — no out-of-window file. The
  seat followed it literally, and `SEATS_DAYS = 7 → 14` and `if os.path.getmtime(p) <
  cutoff: → if False:` now both survive the **whole** `tests/evidence` suite. MINOR-1;
  one fixture line restores it.
- **Step 2's red is not achievable and the seat said so.** All nine seats tests pass on
  the cherry-picked tree (I reconstructed it from `4ca0fe6`): they are regression guards
  over behaviour CA2 already shipped, so their red *is* the named mutant. The body is
  headed "Step 2 red, each load-bearing assertion's mutant applied to the cherry-picked
  tree" — an accurate label, not a fabricated red. MINOR-6, charged to the section's
  Step 2, not to the seat.

## Contract items

The section's eight numbered items, taken literally. Line numbers are at `1abe075`.

| # | item | met | evidence |
|---|---|---|---|
| 1 | MAJOR-1: S1's fixture renamed so the 2-run model sorts LAST by name; the whole line pinned; both sort mutants red | **yes** | `tests/evidence/test_tasks.py:671` `test_seats_line_sums_per_model_ordering_and_last_status`; `alpha-model` done/2400/`{"input": 68620, "output": 13584}` at 1 d (`:678-694`), `zeta-model` done/600/`{"input": 100, "output": 50}` at 6 d (`:695-706`) and failed/1200/`{"input": 10, "output": 5}` at 2 d (`:707-718`), `two-status-model` at 1 d (`:721-731`); the assertion at `:733-737` pins the full line `**Seats (7 d):** zeta-model: 2 runs, 1 done, 10 min, 165 billed · alpha-model: 1 run, 1 done, 40 min, 82204 billed · two-status-model: 1 run, 1 done, ? min, 0 billed`. M1 and M2 both KILLED (below) |
| 2 | MAJOR-2: an aged `K2.log`, `K2.pid` and `.marker-K3.x`, each a valid result, beside one aged `inside-model`; `== ["inside-model"]`; glob `*` red | **yes** | `tests/evidence/test_tasks.py:740` `test_seats_ignores_aged_logs_and_dotfiles`; the three decoys at `:755-757`, each `os.utime`d to `now - 86400` at `:763`; the assertion `assert [r["model"] for r in stats] == ["inside-model"]` at `:771`. M3 KILLED with `assert 3 == 1` — `log-model` and `pid-model` appear, the dot-file does not, exactly as the item predicts |
| 3 | MINOR-1: a `chmod 000` result (skipped as root) and a file-shaped `<runs>/<run>`, beside one readable result; `except ValueError` red | **yes** | `tests/evidence/test_tasks.py:827` `test_seats_unreadable_file_and_file_shaped_run`; `os.utime` at `:848`, `if os.geteuid() == 0: pytest.skip` at `:849-850`, `unreadable.chmod(0)` at `:851`, the file-shaped run at `:853`, `assert md == "**Seats (7 d):** readable-model: 1 run, 1 done, 1 min, 1 billed"` at `:855`. Not root here (`id -u` → 1000) and not in the nix sandbox — the row ran in `evidence-unit` (463 passed, the single skip is `test_tasks.py:3284`, the unrelated sandbox pin). M4 KILLED: `PermissionError: [Errno 13] Permission denied: …/runs/r2/K.result` |
| 4 | MINOR-2: `wall_s: 570 → 10 min`, `569 → 9 min`; dropping `+ 30` red | **yes** | `tests/evidence/test_tasks.py:858` `test_seats_rounds_wall_s_to_the_nearest_minute`, assertions at `:880-881`. M5 KILLED: `assert 'half-model: … 10 min, 0 billed' in '… half-model: … 9 min, 0 billed · under-half-model: … 9 min, 0 billed'` |
| 5 | MINOR-3: `model: first-model` in the header, `model: second-model` after the diffstat → `first-model`; the last match red | **yes** | `tests/evidence/test_tasks.py:884` `test_seats_takes_the_first_model_line`, the two-`model:` text at `:889-898`, `assert [r["model"] for r in stats] == ["first-model"]` at `:901`. M6 KILLED: `assert ['second-model'] == ['first-model']` |
| 6 | MINOR-4: delete the `now=graph.get("now")` read — `render_seats_line(seat_stats(graph["runs_dir"]))`; S4 unchanged | **yes** | `pkgs/evidence/tasks.py:1729-1732` is exactly `if graph.get("runs_dir"): lines.append(render_seats_line(seat_stats(graph["runs_dir"])))` / `else: … none`; `grep -n '"now"' pkgs/evidence/tasks.py tests/evidence/test_tasks.py` → no match anywhere. S4 (`tests/evidence/test_tasks.py:928` `test_seats_line_in_the_cli_brief`) is CA2's, unchanged, and still kills ON12 and ON17 |
| 7 | MINOR-6: `{"input": 1}` → `1 billed`, `{"output": 2}` → `2 billed`; `usage["input"] + usage["output"]` red | **yes** | `tests/evidence/test_tasks.py:904` `test_seats_missing_usage_key_contributes_zero`, assertions at `:924-925`. M7 KILLED — the designated killer is among the six tests it reds: `FAILED …::test_seats_missing_usage_key_contributes_zero`, `E KeyError: 'output'` |
| 8 | MINOR-5: the body pastes the red, every mutant's red and reverted, and the greens | **substantially yes**, one literal miss | `git log -1 --format=%B` carries seven `$ mutate …` blocks (MAJOR-1a, MAJOR-1b, MAJOR-2, MINOR-1, MINOR-2, MINOR-3, MINOR-6) with their `E …` and `FAILED …` lines, then `Step 4 green:` with `462 passed, 1 skipped in 6.63s`, `evidence-unit> 463 passed in 12.76s`, `lint` `exit 0`, `githooks/pre-commit` `exit 0`. Reproduced: my own runs give `462 passed, 1 skipped in 12.23s` and `evidence-unit> 463 passed in 12.70s` — the counts match. The literal miss is "each new assertion's red on the cherry-picked tree", which cannot exist — MINOR-6 below |

## Red before green

**Against the base's implementation, with the branch's tests** (`git checkout ef7830f --
pkgs/evidence/tasks.py`, then `nix develop -c pytest tests/evidence/test_tasks.py -q -k
seats --tb=line`):

```
E   AttributeError: module 'tasks' has no attribute 'render_seats_line'   test_tasks.py:732
E   AttributeError: module 'tasks' has no attribute 'seat_stats'          test_tasks.py:768
…
FAILED tests/evidence/test_tasks.py::test_seats_line_sums_per_model_ordering_and_last_status
FAILED tests/evidence/test_tasks.py::test_seats_ignores_aged_logs_and_dotfiles
FAILED tests/evidence/test_tasks.py::test_seats_absent_fields_and_unreadable
FAILED tests/evidence/test_tasks.py::test_seats_unreadable_file_and_file_shaped_run
FAILED tests/evidence/test_tasks.py::test_seats_rounds_wall_s_to_the_nearest_minute
FAILED tests/evidence/test_tasks.py::test_seats_takes_the_first_model_line
FAILED tests/evidence/test_tasks.py::test_seats_missing_usage_key_contributes_zero
FAILED tests/evidence/test_tasks.py::test_seats_line_in_the_cli_brief
8 failed, 1 passed, 132 deselected in 0.10s
```

Restored: `9 passed, 132 deselected`; whole suite `462 passed, 1 skipped in 12.23s`.
(The one that passes on the base is S5, `test_seats_never_touches_the_board_block` — a
regression guard; ON16 turns it red, so it is not vacuous.)

**Against the cherry-picked tree** — the section's own Step 2. I rebuilt it exactly:
`git fetch /home/dalhaka/factory/ws/ca1/CA2 task/CA2` (`4ca0fe6`), `git checkout
FETCH_HEAD -- pkgs/evidence/tasks.py`, branch tests in place:

```
--- diff HEAD's tasks.py vs CA2's ---
@@ -1727,7 +1727,9 @@ def render_brief(graph, claims_rows=None, today=None):
     if graph.get("runs_dir"):
-        lines.append(render_seats_line(seat_stats(graph["runs_dir"])))
+        lines.append(
+            render_seats_line(seat_stats(graph["runs_dir"], now=graph.get("now")))
+        )
--- seats tests on the cherry-picked (CA2) code with CA2b's tests ---
.........                                                                [100%]
9 passed, 132 deselected in 0.17s
```

So Step 2's stated red ("the new S1 line, the aged-`.log` row, the unreadable row, the 570
row, the two-`model:` row and the single-key row fail") is unachievable: item 6's edit is
the round's only code change and no test touches it, so every new assertion is a
regression guard whose red is its mutant. Each of the nine is load-bearing under at least
one mutant (M1/M2, M3, ON5/ON9, M4, M5/ON14, M6, M7/ON6, ON12/ON17, ON16) — no test here
can pass unconditionally.

## Mutants

Applied one at a time in the fresh clone by a script that refuses a non-unique pattern,
restores the file in a `finally`, asserts the restore and prints `git status --porcelain`
(empty after every one; the tree ends at `1abe075` with `git status` clean).

### The seven the section names — 7 killed, 0 survive

| id | item | mutant | result | line |
|---|---|---|---|---|
| M1 | 1 | `key=lambda r: (r["model"],)` | KILLED | `E AssertionError: assert '**Seats (7 d...n, 165 billed' == '**Seats (7 d...min, 0 billed'` — `test_seats_line_sums_per_model_ordering_and_last_status`, `1 failed, 8 passed` |
| M2 | 1 | `key=lambda r: (r["runs"], r["model"])` | KILLED | same assertion plus `test_seats_line_in_the_cli_brief`, `2 failed, 7 passed` |
| M3 | 2 | glob `"*"` instead of `"*.result"` | KILLED | `E AssertionError: assert 3 == 1` / `+ where 3 = len([… 'inside-model' …, 'log-model' …, 'pid-model' …])`, `test_seats_ignores_aged_logs_and_dotfiles` |
| M4 | 3 | `except ValueError:` in place of `except OSError:` | KILLED | `E PermissionError: [Errno 13] Permission denied: '…/test_seats_unreadable_file_and0/runs/r2/K.result'`, `test_seats_unreadable_file_and_file_shaped_run` |
| M5 | 4 | drop `+ 30` | KILLED | `E AssertionError: assert 'half-model: 1 run, 1 done, 10 min, 0 billed' in '**Seats (7 d):** half-model: 1 run, 1 done, 9 min, 0 billed · under-half-model: 1 run, 1 done, 9 min, 0 billed'` |
| M6 | 5 | take the **last** `^model:` match | KILLED | `E AssertionError: assert ['second-model'] == ['first-model']`, `test_seats_takes_the_first_model_line` |
| M7 | 7 | `row["billed"] += usage["input"] + usage["output"]` | KILLED | `E KeyError: 'output'` … `FAILED …::test_seats_missing_usage_key_contributes_zero` (6 failed, 3 passed — the item's designated killer among them) |

### The sixteen outside the named set — 10 killed, 6 survive

| id | mutant | result |
|---|---|---|
| ON1 | `SEATS_DAYS = 7` → `14` | **SURVIVED** — `462 passed, 1 skipped` over the whole `tests/evidence` suite → MINOR-1 |
| ON2 | drop the cutoff (`if os.path.getmtime(p) < cutoff:` → `if False:`) | **SURVIVED** — `462 passed, 1 skipped` over the whole suite → MINOR-1 |
| ON3 | `statuses[-1]` → `statuses[0]` | KILLED (S1 line and the CLI line) |
| ON4 | `median_low` → `median` | KILLED |
| ON5 | `isinstance(v, int)` without the `bool` exclusion | KILLED — `assert 'm: 1 run, 1 done, ? min, 0 billed' in '… m: … 1 billed …'` |
| ON6 | `for k in ("input",)` | KILLED — `assert 'output-model: … 2 billed' in '… output-model: … 0 billed'` |
| ON7 | `run` never pluralised | KILLED |
| ON8 | drop the `$` anchor on `^wall_s:[ \t]*(\d+)[ \t]*$` | **SURVIVED** → MINOR-4 |
| ON9 | drop the `if r["wall"]` guard | KILLED — `statistics.StatisticsError: no median for empty data` |
| ON10 | never skip a file without `FACTORY-RESULT` (`if not statuses:` → `if False:`) | **SURVIVED** → MINOR-3 |
| ON11 | `render_brief` passes `now=0` | **SURVIVED** (a widening mutant: everything falls inside the window) |
| ON12 | `main` drops `"runs_dir": args.runs_dir` | KILLED — the S1 line absent from the CLI brief |
| ON14 | `+ 30` → `+ 59` (ceiling instead of nearest) | KILLED — `assert 'under-half-model: … 9 min …' in '… under-half-model: … 10 min …'` |
| ON15 | `statuses[-1] == "done"` → `.startswith("done")` | **SURVIVED** → MINOR-5 |
| ON16 | the Seats line added to `render_board_block` | KILLED — `assert 'Seats' not in '**Seats (7 …(typed.md)\n'` |
| ON17 | a blank line inserted before the Seats block (adjacency broken) | KILLED — `assert '' == '**Seats (7 d...min, 0 billed'` |

`mutants_total: 23` · `mutants_killed: 17` · `mutants_outside_named: 16`.

## Checks

All from the fresh clone `…/scratchpad/gate/gate-ca1f-CA2b` at `1abe075`.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **pass** — `evidence-unit> 463 passed in 12.70s`, `EVIDENCE-UNIT-EXIT:0` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass** — `lint> Found 0 warnings and 0 errors.`, `LINT-EXIT:0` |
| pytest | `nix develop -c pytest tests/evidence -q` | `462 passed, 1 skipped in 12.23s`; the skip is `test_tasks.py:3284` "the sandbox-pin assertion runs only in the evidence-unit sandbox" — unrelated, pre-existing |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 in the post-commit clone, **by design** and not a finding: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the regenerated block drops exactly `CA2b` (`- … CA1 CA2b CR4 …` / `+ … CA1 CR4 …`), which `githooks/pre-commit:62-64` calls out ("a landed key leaves the queue, so staleness is by design"). Reproduced the seat's own `exit 0`: a second clone at `ef7830f` with CA2b's two files applied **uncommitted** — the state the hook actually saw — runs `PRECOMMIT-EXIT:0` |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!`, exit 0 |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `80 files already formatted`, exit 0 |
| MAP | `nix develop -c python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | no change, `MAP-EXIT:0` |
| tasks check | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

On the driver's `checks_scope: dirty` / `checks_scope_list: tests/evidence/test_tasks.py`
— the orchestrator's note holds and I did not chase it: `factory-task` computes that list
from `git diff --name-only base..task/KEY`, and the committed diff does touch that path.
Everything above ran from a clone that contains only committed content.

## Touches and commit

- `git diff ef7830f..HEAD --stat` → `pkgs/evidence/tasks.py | 71 +`,
  `tests/evidence/test_tasks.py | 407 +` — 2 files, 478 insertions, 0 deletions. Both
  inside the section's `touches: pkgs/evidence/tasks.py, tests/evidence/test_tasks.py`.
  Nothing outside; no `Deviation:` line needed and none present. `docs/MAP.md` correctly
  untouched (no new file). `docs/OPERATIONS.md` untouched — no board commit. The plan file
  untouched (`git diff --name-only ef7830f..HEAD -- docs/` → empty).
- Exactly one commit: `git rev-list --count ef7830f..HEAD` → `1`.
- Subject byte-identical to the section's `commit subject` (`cmp` of `git log -1
  --format=%s` against the plan's string → `SUBJECT-BYTE-IDENTICAL`).
- Both trailer lines are present and correct in text —
  `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run ca1f)`
  and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` — but **not after a blank
  line**, so git parses neither as a trailer. MINOR-2.
- The body states the why (the ca1 gate's two MAJORs and the five untested MINORs, and
  that item 6 is the only code change) and pastes seven mutant reds and four greens.

## Findings

No MAJORs.

**MINOR-1 — this round removed the seven-day cutoff's only test.**
`tests/evidence/test_tasks.py:740-771` (`test_seats_ignores_aged_logs_and_dotfiles`)
replaces CA2's S2, and its fixture set is the aged `.log`/`.pid`/dot-file plus one
aged-1-d `inside-model` — CA2's 8-day-old `old-model`, the file that pinned
`pkgs/evidence/tasks.py:1634` `if os.path.getmtime(p) < cutoff: continue`, is gone. Both
directions now survive the **whole** suite, not just the seats selection:

```
===== ON1 (SEATS_DAYS = 7 -> 14) exit=0
462 passed, 1 skipped in 11.69s
===== ON2 (if os.path.getmtime(p) < cutoff:  ->  if False:) exit=0
462 passed, 1 skipped in 11.67s
```

S1's oldest file is 6 d, inside the window either way, so it does not cover it. The
Interfaces clause "reads every `<runs_dir>/*/*.result` whose mtime is ≥ `now −
days·86400`" is therefore stated and untested — one `_write_aged(runs, "rold", "K", …,
age_days=8, now=NOW)` line in that test restores it. This traces to the section's item 2,
whose replacement text does not carry the 8-day file over; the seat followed it literally.
Recording it rather than charging it, since no named mutant survives.

**MINOR-2 — no blank line before the two trailers, so git parses zero trailers.**
`git log -1 --format=%B | tail -6 | cat -A`:

```
$ nix develop -c githooks/pre-commit$
exit 0$
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run ca1f)$
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>$
```

```
$ git log -1 --format='%(trailers:only=true)'   → (empty)
$ git log -1 --format=%B | git interpret-trailers --parse   → (empty)
```

CA2's own commit `4ca0fe6` has the blank line and parses both
(`%(trailers:only=true,valueonly=true)` → `dsh 0.1.2-rc.1 / … | Claude Fable 5.1 …`), so
this is a regression against the house convention the section restates ("the two trailers
after a blank line"). The attribution is readable by a human and unreadable by a tool.

**MINOR-3 — "no `^FACTORY-RESULT status=` line ⇒ skipped" is asserted by a fixture the
cutoff eats first.** `tests/evidence/test_tasks.py:820-824` writes
`nones/r/K.result` with a bare `write_text` and no `os.utime`, while `NOW = 1_800_000_000`
(2027-01-15) is ahead of the real clock:

```
file mtime      : 1788850817          (2026-09-08)
cutoff at NOW   : 1799395200
inside window?  : False
seat_stats      : []
aged 1 d, inside: True
seat_stats aged : []                  ← the guard is right; the fixture never reaches it
```

and ON10 (`if not statuses:` → `if False:`) survives. Same shape as the ca1 MAJOR-2,
inherited from CA2's S3 (which the section leaves unchanged), so not owed here; one
`os.utime` closes it.

**MINOR-4 — the `wall_s` line's `$` anchor is untested.** `pkgs/evidence/tasks.py:1651`
`r"^wall_s:[ \t]*(\d+)[ \t]*$"`. ON8 (drop the `$` and the trailing-space class) SURVIVES:
no fixture carries a non-integer `wall_s` such as `12.5`, so the Interfaces' "when it is
an integer, else no sample" has no discriminating row. Pre-existing from CA2.

**MINOR-5 — the `done` comparison's exactness is untested.**
`pkgs/evidence/tasks.py:1647` `if statuses[-1] == "done":`. ON15
(`.startswith("done")`) SURVIVES — no fixture uses a status that merely begins with
`done`. Pre-existing (the ca1 review's ON7).

**MINOR-6 — the section's Step 2 red cannot exist, and item 8's literal wording inherits
that.** With CA2's `tasks.py` restored over the branch's tests, all nine seats tests pass
(`9 passed, 132 deselected in 0.17s`); item 6's removal of `now=graph.get("now")` is the
round's only code change and nothing tests it. The body therefore cannot paste "each new
assertion's red on the cherry-picked tree" and does not pretend to — it pastes the mutant
reds under the honest heading "Step 2 red, each load-bearing assertion's mutant applied to
the cherry-picked tree". A section defect, not the seat's; noted so the next fix-round
section says "the red is the named mutant" outright.

**MINOR-7 — item 2's fixtures are written inline, not through `_write_aged`.**
`tests/evidence/test_tasks.py:753-763` uses `p.write_text(...)` plus
`os.utime(p, (now - 86400, now - 86400))` rather than the item's
`_write_aged(…, age_days=1, now=NOW)`, because `_write_aged`
(`tests/evidence/test_tasks.py:278-285`) hardcodes the `.result` suffix and so cannot
write a `.log`, a `.pid` or a dot-file. The effect is identical (`os.utime` with the same
pair) and M3 kills; recording the letter-vs-substance gap only.

**MINOR-8 — two cosmetics in the new tests.** `tests/evidence/test_tasks.py:774`
`test_seats_absent_fields_and_unreadable` keeps "unreadable" in its name although the
unreadable fixture moved to `:827`; and the file-shaped run entry at `:853`
(`(runs / "file-shaped-run").write_text("not a run dir")`) cannot discriminate anything —
`glob("*/*.result")` never descends into a depth-1 file, so no code path handles it — and
under root it is skipped along with the `chmod 000` half by the `pytest.skip` at `:849`.
The item asked for it; it costs nothing and proves nothing.

## Verdict

**APPROVED.** All eight numbered items are closed as stated, with the file:line and the
red for each. All seven mutants the section names are killed, including the two that
survived at ca1 (`key=lambda r: (r["model"],)` and the glob `*`); ten of sixteen further
mutants die. `evidence-unit` and `lint` are green with `--rebuild`, `ruff`, `MAP` and
`tasks check` are clean, the pre-commit exit 1 is the by-design queue regeneration and the
seat's `exit 0` reproduces on the pre-commit state. One commit, two files, both inside
`touches`, subject byte-identical, the plan and the board untouched. The eight MINORs are
all recordable: the sharpest is MINOR-1, a coverage regression the section's item 2
authored — the seven-day cutoff is now untested and a single aged fixture line restores
it; then MINOR-2, the missing blank line that leaves the two trailers unparseable by git.
`plan_defect: none`.
