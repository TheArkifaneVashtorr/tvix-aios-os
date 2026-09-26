---
plan_defect: vacuous
plan_defect_secondary: implementer
mutants_total: 9
mutants_killed: 7
mutants_outside_named: 3
model: opus
---
# Opus gate — seat run fix3, task FIX3 — REJECTED

## Summary

The fix itself is right and it works: with the branch applied, a clone named
`gate-fix3-FIX3` and a clone named `nixos-agent-env`, both at `17d4e7b`,
regenerate a **byte-identical** queue block (measured below) — the defect BUG3
gathered is gone. `evidence-unit` (521 passed) and `lint` are green by
`nix build --rebuild`, `ruff check`/`ruff format --check` clean, `repomap write`
leaves no drift, `tasks.py check` silent, the subject is byte-identical, one
commit, both trailers.

Two MAJORs stand.

**MAJOR-1.** The section's B2 mutant — "*raise, **or pick the first entry**, when
no entry is flagged; B2 fails*" — has two arms, and the first-entry arm
**survives the whole suite** (155 passed, 1 skipped). `B2`'s only assertion is
`assert "W1" in block`, which is satisfied whether the fallback name is the
basename `XYZ` or the first entry `media`: neither matches the withdrawal keyed
to `nixos-agent-env`. Nothing in the 155 tests pins "no flag ⇒ the basename"; the
whole fallback arm of the new `name` expression is unprotected. The plan's own
stated fixture and assertion for B2 cannot kill the mutant the plan names
(hence `vacuous`), and the seat did not add the one line that would have — the
same line it *did* add to B4 (`assert … ["repos"][0]["name"] == "elsewhere"`).

**MAJOR-2.** `nix develop -c githooks/pre-commit` **exits 1** in a clean clone at
`17d4e7b`: the queue block the seat committed inside `docs/OPERATIONS.md` is
stale at its own commit (it queues `FIX3`, which the same commit makes `landed`).
The seat committed the board instead of taking the route this plan's Global
Constraints spell out (`git add docs/OPERATIONS.md`, then commit **by pathspec**
so the board is not in the commit). The staleness is temporal, not the basename
bug — I proved the block is basename-independent — but the branch nonetheless
ships a board block its own tree's tooling refuses, and the orchestrator's rule
for this review is explicit: identical ⇒ MINOR, differs ⇒ MAJOR. It differs.

## Contract items

Taken literally from `docs/superpowers/plans/2026-09-09-bugs.md:302-334`.

1. **`docs/ledger/repos.toml` gains `ledger = true` on the `nixos-agent-env`
   entry only.** MET. `docs/ledger/repos.toml:8` — one added line, under
   `name = "nixos-agent-env"` (:6); the file has exactly one occurrence
   (`grep -n 'ledger = true' docs/ledger/repos.toml` → `8:ledger = true`).

2. **`load_repos` refuses more than one flagged entry as a `tasks.py check`
   error naming both.** MET AS AN INTERFACE, MOVED AS A MECHANISM (MINOR-1).
   `load_repos` (`pkgs/evidence/tasks.py:424-437`) only carries the flag
   (`"ledger": bool(r.get("ledger", False))`, :434); the refusal lives in `main`
   (`pkgs/evidence/tasks.py:2315-2322`) and reads
   `os.path.join(args.root, "docs", "ledger", "repos.toml")` — not `--repos`.
   Measured consequence:

   ```
   $ nix develop -c python3 pkgs/evidence/tasks.py --root . --repos <two-flagged>.toml check
   tasks: task-status names unknown key nixos-agent-env/…/SB5
   …            # no "more than one `ledger = true`" line — the override is not checked
   ```

   The placement has house precedent (`tasks.py:2231-2237`: "The valid
   `**repo:**` targets come from the ledger under `--root`, even when the graph
   itself was scanned against a `--repos` override"), and it is the placement the
   hook needs, since `githooks/pre-commit:62-64` hands `check` a synthetic
   one-repo file. Recorded as a MINOR, not a MAJOR: the stated **Interface**
   ("two flagged entries are a `check` error") holds for the file whose flag is
   load-bearing.

3. **`board_graph` names the repo from the flagged entry when the file exists and
   carries exactly one, else the basename.** MET. `pkgs/evidence/tasks.py:1169-1170`:

   ```python
   flagged = ledger_entries(os.path.join(root, "docs", "ledger", "repos.toml"))
   name = flagged[0] if len(flagged) == 1 else (os.path.basename(root) or "repo")
   ```

   Both arms exercised (B1, B2). Producer `ledger_entries` at :440-444.

4. **Nothing else in `board_graph` changes — tasks derived from THIS tree, every
   `path` ignored.** MET. The diff of `board_graph` is the docstring plus the two
   lines above; `"path": root` at :1173 is unchanged, and B4 (`:1670-1682`) pins
   it with a flagged entry whose `path` is `~/elsewhere`.

5. **The hook untouched.** MET. `githooks/pre-commit` is not in
   `git diff 0647d55..HEAD --name-only`.

6. **Interfaces: `write-board` and `check --board` produce the same block from
   any clone, whatever the directory is called.** MET, measured:

   ```
   $ diff block-gate.txt block-canon.txt && echo IDENTICAL across basenames
   IDENTICAL across basenames
   ```

   (`block-gate.txt` from the clone named `gate-fix3-FIX3`, `block-canon.txt`
   from a second clone of the same commit named `nixos-agent-env`.)

## Red before green

Method: a second clone of `task/FIX3`, then
`git checkout 0647d55 -- pkgs/evidence/tasks.py docs/ledger/repos.toml` — the
base's implementation against the branch's tests. Whole file on the base:

```
FAILED tests/evidence/test_tasks.py::test_board_graph_derives_this_tree_ignoring_repos_toml
FAILED tests/evidence/test_tasks.py::test_board_graph_exposes_task_status_and_omits_withdrawn
FAILED tests/evidence/test_tasks.py::test_board_name_takes_ledger_entry_and_omits_withdrawn
FAILED tests/evidence/test_tasks.py::test_board_name_check_refuses_multiple_ledger_entries
4 failed, 151 passed, 1 skipped in 1.44s
```

- **B1** (`tests/evidence/test_tasks.py:2316-2325`) red on the base:
  `>       assert "W1" not in block` →
  `E       AssertionError: assert 'W1' not in '**Queued (d...(board.md)\n'`
- **B2** (`:2327-2336`) passes on the base **by design** — it pins the
  pre-existing basename behaviour; its mutant is a mutant of the new code
  (see MAJOR-1).
- **B3** (`:2338-2364`) red on the base: `>       assert rc == 1` /
  `E       assert 0 == 1` (`:2362`).
- **B4** (`:1656`, amended, now `:1670`) red on the base:
  `>       assert tk.board_graph(str(root))["repos"][0]["name"] == "elsewhere"` →
  `E       AssertionError: assert 'root' == 'elsewhere'`.
- **the amended `:2225`** (now `:2233-2263`) red on the base:
  `>       assert "W1" not in block and "K1" in block` →
  `'W1' is contained here: ef).** K1 W1 (board.md)` — i.e. the fixture no
  longer leans on its directory being named `root`, exactly as Fact 3 asked.

Green on the branch, same clone, same tests: `155 passed, 1 skipped in 1.43s`.

## Mutants

Applied one at a time in a scratch clone, whole file run each time, reverted by
`git checkout HEAD -- pkgs/evidence/tasks.py`.

| # | mutant | named? | killed by | result |
|---|---|---|---|---|
| M1 | `name = os.path.basename(root) or "repo"` | B1 (i) | B1 | killed |
| M2 | name = first entry of `repos.toml`, flagged or not | B1 (ii) | B1 | killed |
| M3 | no flag ⇒ **first entry** instead of the basename | B2 | — | **SURVIVED** |
| M3b | no flag ⇒ `raise` | B2 | B2 (+4) | killed |
| M4 | `len(flagged) > 1` refusal removed | B3 | B3 | killed |
| M5 | `"path": flagged entry's path` | B4 | B4 | killed |
| O3 | `len(flagged) >= 1` (>1 flagged ⇒ first flagged, not the basename) | no | — | **SURVIVED** |
| O4 | the `check` error names one entry, not both | no | B3 | killed |
| O5 | `repos.toml` read from the cwd, not `root` | no | B2 + B4 | killed |

Failing lines:

- **M1** → `tests/evidence/test_tasks.py:2324`
  `E  AssertionError: assert 'W1' not in '**Queued (d...(board.md)\n'`
  (`3 failed, 2 passed` — B1, B4 and the amended `:2225`).
- **M2** → `tests/evidence/test_tasks.py:2324`, same line; `1 failed, 154 passed`
  (only B1 discriminates the flagged entry from the first entry — the plan's
  "NOT first" fixture row earns its place).
- **M3** → nothing. `155 passed, 1 skipped in 1.30s`. See MAJOR-1.
- **M3b** → `pkgs/evidence/tasks.py:1171: SystemExit`; `5 failed, 150 passed`,
  including `test_board_name_falls_back_to_basename_without_ledger`.
- **M4** → `tests/evidence/test_tasks.py:2362` `E  assert 0 == 1`;
  `1 failed, 154 passed`.
- **M5** → `tests/evidence/test_tasks.py:1680`
  `E  AssertionError: assert 'T1 (board.md)' in '… nothing queued\n'`;
  `1 failed, 154 passed`.
- **O4** → `tests/evidence/test_tasks.py:2363`
  `E  AssertionError: assert ('media' in 'tasks: … `ledger = true` repo: gaming\n')`.
- **O5** → `tests/evidence/test_tasks.py:2336`
  `E  AssertionError: assert 'W1' in '… nothing queued\n'` plus B4.

`mutants_total: 9`, `mutants_killed: 7`, `mutants_outside_named: 3`.

## Checks

All from inside the fresh clone `…/scratchpad/gate/fix3-FIX3/gate-fix3-FIX3`
(`git clone -q --branch task/FIX3 /home/dalhaka/factory/ws/fix3/FIX3 …`), with
`XDG_CACHE_HOME` under the scratchpad.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **green** — `evidence-unit> 521 passed in 13.86s`, `EXIT=0` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **green** — `lint> Found 0 warnings and 0 errors.`, `EXIT=0` |
| ruff check | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` rc=0 |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `84 files already formatted` rc=0 |
| repomap | `python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | no drift, rc=0 (so `docs/MAP.md` owed nothing) |
| tasks check | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, rc=0 |
| pre-commit | `nix develop -c githooks/pre-commit` | **RED, rc=1** — see MAJOR-2 |

The pre-commit tail:

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
PRECOMMIT_RC=1
 M docs/OPERATIONS.md
```

## Touches and commit

Diff against `0647d55`: `docs/OPERATIONS.md` (2 lines), `docs/ledger/repos.toml`
(+1), `pkgs/evidence/tasks.py` (+33/-…), `tests/evidence/test_tasks.py` (+126).
Three of four are inside the section's `touches`; `docs/MAP.md` was owed nothing
(no drift). `docs/OPERATIONS.md` is **outside** `touches` and is explained in the
commit body — recorded as MINOR-2, with its consequence escalated to MAJOR-2.

The board change, measured:

- **Inside the markers only.** `git diff` shows one changed line, between
  `<!-- tasks:begin -->` and `<!-- tasks:end -->`. Re-running
  `factory-integrate`'s own guard (`tools/factory/seat/factory-integrate:83-101`,
  the `awk` strip + `cmp` against the merge base):
  `factory-integrate board guard: ACCEPTS (change confined to the queue block)`.
  So the landing run will not refuse this branch on the board.
- **NOT identical to the canonical regeneration at that commit.** In a clone
  named `nixos-agent-env` at `17d4e7b`,
  `tasks.py check --board docs/OPERATIONS.md` →
  `tasks: docs/OPERATIONS.md queue block is stale`, and `write-board` **removes**
  `FIX3`:

  ```
  -… FIX2 FIX3 HH1 HH2 HH3 HH4 PW1glm PW1kimi PW1pro SP4 (…)   # what the commit carries
  +… FIX2 HH1 HH2 HH3 HH4 PW1glm PW1kimi PW1pro SP4 (…)        # what the tree derives at 17d4e7b
  ```

- **The cause is temporal, not the basename.** At `17d4e7b`,
  `board_graph` derives `FIX3 landed` (its own commit subject is in the log):

  ```
  FIX2 ready ''
  BUG3c landed 'bugs: gather round 3 — the board repo key; …'
  FIX3 landed "evidence: board_graph names the repo from repos.toml's ledger entry, …"
  ```

  The hook regenerated the block *before* the commit existed, when `FIX3` was
  ready. The two clones (canonical and non-canonical) agree exactly, so the fix
  under review works; what fails is that the block was committed at all.

Commit convention: exactly one commit (`git rev-list --count 0647d55..HEAD` → 1);
subject byte-identical to the section's (`cmp` → `SUBJECT BYTE-IDENTICAL`); both
trailers present after a blank line (`Generated-By: dsh 0.1.2-rc.1 /
deepseek/deepseek-v4-pro-0813 …`, `Co-Authored-By: Claude Fable 5.1 …`); the plan
file untouched. The body states the why but **pastes no red and no green**
(MINOR-3) — grepping the 23-line body for `assert|passed|failed|FAILED` returns
only prose.

## Findings

**MAJOR-1 — the B2 mutant's "first entry" arm survives; nothing pins the
basename fallback.** `tests/evidence/test_tasks.py:2327-2336`.
Mutant applied at `pkgs/evidence/tasks.py:1170`:

```python
    if len(flagged) == 1:
        name = flagged[0]
    elif _all:            # M3: no flag -> first entry instead of the basename
        name = _all[0]
    else:
        name = os.path.basename(root) or "repo"
```

Result: `155 passed, 1 skipped in 1.30s`; B2 alone: `1 passed`. B2's only
assertion, `assert "W1" in block`, holds for `XYZ` and for `media` alike, since
the withdrawal is keyed to `nixos-agent-env`. The section names this mutant
("raise, **or pick the first entry**, when no entry is flagged; B2 fails") and
states the fixture and the assertion that were supposed to kill it, so the plan
is the primary defect (`vacuous`); the seat is secondary — it wrote exactly the
missing assertion in B4 and not here. The kill is one line:
`assert tk.board_graph(str(root))["repos"][0]["name"] == "XYZ"`.

**MAJOR-2 — `githooks/pre-commit` is red at `17d4e7b`, because the seat
committed the board block instead of pathspec-excluding it.**
`docs/OPERATIONS.md:23` (the queue line) and the commit body's third paragraph.
Evidence: the pre-commit tail above (rc=1), the canonical regeneration diff
above, and `FIX3 landed` at this commit. §Global Constraints of the plan says
verbatim: "`git add docs/OPERATIONS.md` (so the hook's diff is quiet), then
commit BY PATHSPEC … so the board is not in your commit; say in the body that you
did this." The seat instead staged and **committed** it and defended it in the
body ("it is confined and rides along in this commit"). Consequences: a fresh
clone at HEAD cannot commit until the board is regenerated; if this branch lands,
`main` carries a queue block asserting `FIX3` is queued while it is landed, until
the orchestrator's next `write-board` repairs it. `factory-integrate` will
**accept** it (guard reproduced above), so nothing downstream catches this.

**MINOR-1 — the multi-flag refusal is not in `load_repos` and ignores `--repos`.**
`pkgs/evidence/tasks.py:2315-2322` vs the section's "*`load_repos`
(`tasks.py:424-436`) refuses a file with more than one `ledger = true`*". Only
the `check` subcommand refuses, and only for `<root>/docs/ledger/repos.toml`;
`brief`, `json`, `waves` and any `--repos` override accept a two-flagged file
silently (measured above). Defensible — it matches the existing `configured_repos`
pattern at `:2231-2237` and is what the hook needs — but it is not what the
section says.

**MINOR-2 — `docs/OPERATIONS.md` is outside the section's `touches`.** The
section lists `pkgs/evidence/tasks.py, tests/evidence/test_tasks.py,
docs/ledger/repos.toml, docs/MAP.md`. The body explains the file, so it is an
explained deviation; the house rule that a seat never commits the board is what
turns it into MAJOR-2.

**MINOR-3 — the commit body pastes neither the red nor the green.** 23-line body
of `17d4e7b`; it states the defect, the fix and the board rationale, but carries
no failing line and no test count, which the house convention requires.

**MINOR-4 — `write-board` does not refuse two flagged entries; only `check`
does, and `board_graph`'s ">1 ⇒ basename" arm is untested.** Outside-named mutant
O3 (`len(flagged) >= 1`) survives all 155 tests, so a repos.toml with two flags
would silently name the repo by the first flagged entry in every `write-board`
run, with only `check` complaining. The section's "else the basename as today"
is stated but unpinned.

## Verdict

**REJECTED.** Two MAJORs: a named mutant that survives (`plan_defect: vacuous`,
secondary `implementer`), and a red `githooks/pre-commit` caused by the seat
committing the board against an explicit Global Constraint. The fix itself —
`ledger = true`, `ledger_entries`, the `board_graph` name resolution, the
`check` refusal — is correct, proved basename-independent by measurement, and
should survive the fix round essentially unchanged; the round owes B2 one
assertion on the derived name, a `write-board`/`>1 flagged` arm pinned or the
contract restated, and a commit that leaves `docs/OPERATIONS.md` staged but
uncommitted.
