---
plan_defect: none
mutants_total: 10
mutants_killed: 10
mutants_outside_named: 4
model: opus
---
# Opus gate — seat run fix3b, task FIX3b — APPROVED

## Summary

The round does exactly what `### FIX3b` asked and nothing else. Against
`refs/fix3` (`17d4e7b`, the rejected commit) the delta is three things: the
multi-flag refusal moved out of `main` into `load_repos`, `board_graph`'s
`len(flagged) == 1` arm collapsed to `if flagged` (the ">1 ⇒ basename" arm gone
with the refusal), and B2 gained the assertion on the derived NAME. The board is
not in the commit.

Both of the prior review's MAJORs are closed, measured:

- **MAJOR-1 (the surviving mutant).** `no flag ⇒ first entry`, applied at
  `pkgs/evidence/tasks.py:1181`, now dies:
  `tests/evidence/test_tasks.py:2337` `E AssertionError: assert 'media' == 'XYZ'`
  (`1 failed, 154 passed, 1 skipped`). It survived all 155 tests in FIX3.
- **MAJOR-2 (the committed board).** `git diff ee12845..HEAD --name-only` is
  `docs/ledger/repos.toml`, `pkgs/evidence/tasks.py`,
  `tests/evidence/test_tasks.py` — `docs/OPERATIONS.md` is **not** in the commit,
  and the body says so.

`evidence-unit` (521 passed) and `lint` green by `nix build --rebuild`,
`ruff check` / `ruff format --check` clean, `repomap write` leaves no drift,
`tasks.py check` silent, subject byte-identical, one commit, both trailers, every
file inside `touches`. `githooks/pre-commit` exits 1 on G8c alone, and the diff
is the FIX3b row leaving the queue at its own landing commit — the orchestrator's
post-landing board pass, not a finding (see ## Checks).

Ten mutants applied, ten killed — six the sections name, four outside.

## Contract items

Taken literally from `docs/superpowers/plans/2026-09-09-bugs.md:302-356` (FIX3's
design carried by FIX3b's `Interfaces: as FIX3's, plus …`).

1. **`docs/ledger/repos.toml` gains `ledger = true` on the `nixos-agent-env`
   entry, and only there.** MET. `docs/ledger/repos.toml:8`, under
   `name = "nixos-agent-env"` (:6). `grep -c 'ledger = true'` → `1`.

2. **FIX3b item 2 — the multi-flag refusal lives in `load_repos`, not in `main`.**
   MET. `pkgs/evidence/tasks.py:438-445`:

   ```python
       flagged = [r["name"] for r in repos if r["ledger"]]
       if len(flagged) > 1:
           print(
               f"tasks: {path} names more than one `ledger = true` repo: "
               + " and ".join(sorted(flagged)),
               file=sys.stderr,
           )
           raise SystemExit(1)
   ```

   `git diff refs/fix3 HEAD -- pkgs/evidence/tasks.py` shows the `main` block
   (FIX3's `:2315-2322`) **deleted**. One message naming both, on stderr.

3. **`check`, `write-board`, `brief`, `json` and `waves` all refuse.** MET,
   measured against a two-flagged tree (`…/scratchpad/gate/fix3b-FIX3b/twoflag`):

   ```
   --- check       rc=1 :: tasks: …/repos.toml names more than one `ledger = true` repo: gaming and media
   --- write-board rc=1 :: …same line…
   --- brief       rc=1 :: …same line…
   --- json        rc=1 :: …same line…
   --- waves --repo media  rc=1 :: …same line…
   ```

   And, closing the prior MINOR-1's second half, the `--repos` override is
   refused too — FIX3 read only `<root>/docs/ledger/repos.toml`:

   ```
   $ nix develop -c python3 pkgs/evidence/tasks.py --root . --repos <two-flagged>.toml check
   rc=1
   tasks: …/twoflag/docs/ledger/repos.toml names more than one `ledger = true` repo: gaming and media
   ```

4. **`board_graph`'s ">1 flagged ⇒ basename" arm disappears; the resolution is
   one flag → that name, no flag → the basename, two or more → `load_repos`
   refuses.** MET. `pkgs/evidence/tasks.py:1180-1181`:

   ```python
       flagged = ledger_entries(os.path.join(root, "docs", "ledger", "repos.toml"))
       name = flagged[0] if flagged else (os.path.basename(root) or "repo")
   ```

   `ledger_entries` (:449-453) goes through `load_repos`, so `flagged` is at most
   one by construction; the docstring (:1173-1175) states it. Both live arms are
   asserted: the flag arm by B1 (`tests/evidence/test_tasks.py:2315-2326`), the
   fallback arm by B2's **name** assertion (`:2337`).

5. **FIX3b item 1 — B2 asserts the fallback NAME beside the key.** MET.
   `tests/evidence/test_tasks.py:2336-2339`:

   ```python
       g = tk.board_graph(str(root))
       assert g["repos"][0]["name"] == "XYZ"
       block = tk.render_board_block(g)
       assert "W1" in block
   ```

6. **FIX3b item 2 — B3 asserts the refusal through `check` AND `write-board`
   (exit non-zero, both names in stderr).** MET.
   `tests/evidence/test_tasks.py:2359-2378` loops
   `for command in (["check"], ["write-board"])`, reading `capsys` fresh each
   iteration and asserting `rc == 1` and `"media" in err and "gaming" in err`.
   The `write-board` arm is load-bearing, not decorative: mutant **O4**, which
   restores FIX3's placement (refusal in `check` only), fails it —
   `tests/evidence/test_tasks.py:2377` `E assert 0 == 1`.

7. **Nothing else about `board_graph` changes — every task derives from THIS
   tree, every `path` ignored.** MET. `"path": root` at
   `pkgs/evidence/tasks.py:1184` is unchanged, and B4
   (`tests/evidence/test_tasks.py:1656-1682`) pins it with a flagged entry whose
   `path` is `~/elsewhere`; mutant M5 (read the tasks from that path) dies at
   `:1680`.

8. **Fact 3 — `:1656` and `:2225` amended, keeping what each protects.** MET.
   `:1656` (`test_board_graph_derives_this_tree_ignoring_repos_toml`) now flags
   its `elsewhere` entry and adds `assert … ["repos"][0]["name"] == "elsewhere"`
   (:1670) beside the unchanged empty-HOME/real-HOME comparison.
   `:2225` (now `:2232`, `test_board_graph_exposes_task_status_and_omits_withdrawn`)
   gains a `repos.toml` flagging `nixos-agent-env` (:2253-2255) and its
   `task-status.toml` row moves from `repo = "root"` to
   `repo = "nixos-agent-env"` (:2256-2258) — so it **no longer depends on its
   fixture directory being named `root`**, which is what Fact 3 asked. Proof it
   still discriminates: mutant M1 (basename always) kills it at `:2263`
   `E AssertionError: assert ('W1' not in '**Queued (d…(board.md)\n'`.

9. **The hook untouched.** MET. `githooks/pre-commit` is not in
   `git diff ee12845..HEAD --name-only`.

10. **Interface — `write-board` and `check --board` produce the same block from
    any clone whatever the directory is called.** MET, measured on two clones of
    `04065d4`, one named `gate-fix3b-FIX3b` and one named `nixos-agent-env`:

    ```
    $ diff block-gate.txt block-canon.txt && echo IDENTICAL_ACROSS_BASENAMES
    IDENTICAL_ACROSS_BASENAMES
    +**Queued (…).** FIX2 HH1 HH2 HH3 HH4 PW1glm PW1kimi PW1pro SP4 (…)
    ```

11. **A tree without `repos.toml`, or without a flagged entry, behaves exactly as
    before.** MET. `load_repos` returns `[]` for a missing file
    (`pkgs/evidence/tasks.py:425-426`; `tests/evidence/test_tasks.py:506`), so
    `name` falls to the basename. The missing-file arm is live in the suite —
    `test_board_graph_excludes_cross_repo_task` (`:1814`) and
    `test_board_graph_defers_cross_repo_dependent` (`:1843`) build trees with no
    `docs/ledger` at all, and both fail under mutant M3b.

12. **FIX3b item 3 — the board stays out of the commit.** MET, see MAJOR-2 above
    and ## Touches and commit.

13. **FIX3b item 4 — the body pastes the reds and the greens.** MET. The body
    carries four failing lines (B1 `:2324`, B2's mutant `:2337`, B3 `:2377`, B4
    `:1670`), the five green commands with their output, and the six mutants with
    their killing lines; `git log -1 --format=%B | grep -cE 'assert|passed|failed|FAILED'`
    → `15`.

## Red before green

Method: a second clone of `task/FIX3b`, then
`git checkout ee12845 -- pkgs/evidence/tasks.py docs/ledger/repos.toml` — the
base's implementation against the branch's tests. (`git diff 0647d55 ee12845 --
pkgs/evidence/tasks.py docs/ledger/repos.toml` is empty, so this base is the
body's `0647d55` for these files.)

```
FAILED tests/evidence/test_tasks.py::test_board_graph_derives_this_tree_ignoring_repos_toml
FAILED tests/evidence/test_tasks.py::test_board_graph_exposes_task_status_and_omits_withdrawn
FAILED tests/evidence/test_tasks.py::test_board_name_takes_ledger_entry_and_omits_withdrawn
FAILED tests/evidence/test_tasks.py::test_board_name_check_refuses_multiple_ledger_entries
4 failed, 151 passed, 1 skipped in 1.63s
```

- **B1** (`:2315`) → `tests/evidence/test_tasks.py:2324`
  `>       assert "W1" not in block`
  `E       AssertionError: assert 'W1' not in '**Queued (d...(board.md)\n'`
- **B2** (`:2328`) passes on the base by design — it pins pre-existing
  behaviour; its red is under the mutant it names (M3, below), which is precisely
  what this round owed.
- **B3** (`:2342`) → `tests/evidence/test_tasks.py:2377`
  `>           assert rc == 1` / `E           assert 0 == 1` — red on **both**
  arms here, since the base has no refusal anywhere.
- **B4** (`:1656`, amended) → `tests/evidence/test_tasks.py:1670`
  `>       assert tk.board_graph(str(root))["repos"][0]["name"] == "elsewhere"`
  `E       AssertionError: assert 'root' == 'elsewhere'`
- **the amended `:2225`** → `tests/evidence/test_tasks.py:2263`
  `>       assert "W1" not in block and "K1" in block`
  `E       AssertionError: assert ('W1' not in '**Queued (d...(board.md)\n'`

Green on the branch, same clone, same tests: `155 passed, 1 skipped in 1.45s`.

## Mutants

Each applied alone in a scratch clone, the whole file run, reverted with
`git checkout HEAD -- pkgs/evidence/tasks.py`.

| # | mutant | named? | killed by | result |
|---|---|---|---|---|
| M1 | `name = os.path.basename(root) or "repo"` always | FIX3 B1(i) | B1, B4, `:2232` | killed |
| M2 | name = the first entry of `repos.toml`, flagged or not | FIX3 B1(ii) | B1, B2 | killed |
| M3 | **no flag ⇒ the first entry** (the one that survived FIX3) | FIX3 B2 / FIX3b-1 | B2 | killed |
| M3b | no flag ⇒ `raise` | FIX3 B2 | B2 + 4 others | killed |
| M4 | **the `load_repos` refusal removed — two flags ⇒ first flagged silently** | FIX3 B3 / FIX3b-2 | B3 | killed |
| M5 | `"path"` = the flagged entry's path | FIX3 B4 | B4 | killed |
| O1 | the refusal message names one entry, not both | no | B3 | killed |
| O2 | `repos.toml` read from the cwd, not `root` | no | B4, B2 | killed |
| O3 | `len(flagged) > 2` (off-by-one: two flags accepted) | no | B3 | killed |
| O4 | the refusal moved back to `check` only (FIX3's placement) | no | B3's `write-board` arm | killed |

Failing lines:

- **M1** → `tests/evidence/test_tasks.py:1670` `E AssertionError: assert 'root' == 'elsewhere'`;
  `:2263` `E assert ('W1' not in …)`; `:2324` `E assert 'W1' not in …` —
  `3 failed, 152 passed, 1 skipped`.
- **M2** → `:2324` `E assert 'W1' not in '**Queued (d...(board.md)\n'` and
  `:2337` `E AssertionError: assert 'media' == 'XYZ'` — `2 failed, 153 passed`.
- **M3** → `tests/evidence/test_tasks.py:2337`
  `>       assert g["repos"][0]["name"] == "XYZ"` /
  `E       AssertionError: assert 'media' == 'XYZ'` — `1 failed, 154 passed`.
  **This is the mutant that survived FIX3's whole suite.**
- **M3b** → `E SystemExit: M3b: no ledger entry` at `:1606`, `:1694`, `:1814`,
  `:1843`, `:2336` — `5 failed, 150 passed`.
- **M4** → `tests/evidence/test_tasks.py:2377` `>           assert rc == 1` /
  `E           assert 0 == 1` — `1 failed, 154 passed`.
- **M5** → `tests/evidence/test_tasks.py:1680`
  `E AssertionError: assert 'T1 (board.md)' in '**Queued (…).** nothing queued\n'`
  — `1 failed, 154 passed`.
- **O1** → `:2378`
  `E AssertionError: assert ('media' in 'tasks: …/repos.toml names more than one `ledger = true` repo: gaming\n')`.
- **O2** → `:1670` `E assert 'nixos-agent-env' == 'elsewhere'` and `:2337`
  `E assert 'nixos-agent-env' == 'XYZ'` — `2 failed, 153 passed`.
- **O3** → `:2377` `E assert 0 == 1` — `1 failed, 154 passed`.
- **O4** → `:2377` `E assert 0 == 1` on the **second** loop iteration
  (`check` refuses, `write-board` does not) — `1 failed, 154 passed`. This is the
  measurement that makes B3's `write-board` arm non-vacuous and closes the prior
  MINOR-4.

`mutants_total: 10`, `mutants_killed: 10`, `mutants_outside_named: 4`.

## Checks

All from inside the fresh clone
`…/scratchpad/gate/fix3b-FIX3b/gate-fix3b-FIX3b`
(`git clone -q --branch task/FIX3b /home/dalhaka/factory/ws/fix3b/FIX3b …`), with
`XDG_CACHE_HOME` under the scratchpad.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **green** — `evidence-unit> 521 passed in 13.83s`, `EVIDENCE_UNIT_EXIT=0` |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **green** — `lint> Found 0 warnings and 0 errors.`, `LINT_EXIT=0` |
| ruff check | `nix develop -c ruff check pkgs/evidence tests/evidence` | `All checks passed!` rc=0 |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | `84 files already formatted` rc=0 |
| repomap | `python3 pkgs/evidence/repomap.py --root . write` + `git diff --exit-code docs/MAP.md` | no drift, rc=0 — so `docs/MAP.md` owes nothing |
| tasks check | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, rc=0 |
| pre-commit | `nix develop -c githooks/pre-commit` | rc=1 on **G8c alone** — see below |

The hook's tail and the whole of its board diff:

```
tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again
PRECOMMIT_RC=1
 M docs/OPERATIONS.md

-**Queued (…).** FIX2 FIX3b HH1 HH2 HH3 HH4 PW1glm PW1kimi PW1pro SP4 (…)
+**Queued (…).** FIX2 HH1 HH2 HH3 HH4 PW1glm PW1kimi PW1pro SP4 (…)
```

The single dropped key is **`FIX3b` itself**: at `04065d4` its own commit subject
is in the log, so the tree derives it `landed` and the block the seat's hook
validated (with `FIX3b` still `ready`) is stale by exactly one landing. This is
post-landing staleness — the orchestrator's board pass, explicitly not a finding
for this gate — and it is materially different from FIX3's MAJOR-2, where the
seat had **committed** the block. Here the working tree is clean at HEAD
(`git status --porcelain` empty) and `docs/OPERATIONS.md` is untouched by the
commit. Every other hook arm (treefmt, ruff, statix/deadnix, js-lint, prettier,
the render tests) passed.

## Touches and commit

`git diff ee12845..HEAD --name-only`:

```
docs/ledger/repos.toml
pkgs/evidence/tasks.py
tests/evidence/test_tasks.py
```

All three are inside the section's `touches`
(`pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, docs/ledger/repos.toml,
docs/MAP.md`); `docs/MAP.md` owed nothing (repomap leaves no drift). Nothing
outside. `docs/superpowers/plans/2026-09-09-bugs.md` is untouched, and so is
`docs/OPERATIONS.md`.

- `git rev-list --count ee12845..HEAD` → `1`.
- Subject vs the section's, byte for byte: `cmp` → `SUBJECT_BYTE_IDENTICAL`.
- Trailers, after a blank line (`cat -A` tail):
  `Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run fix3b)$`
  and `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>$`.
- The body states the why (the basename bug and its blast radius), pastes four
  reds, five greens and six mutants with their killing lines, and says in its own
  words that the board is not in the commit — which the diff confirms.

Against `refs/fix3` (`17d4e7b`, fetched read-only from
`/home/dalhaka/factory/ws/fix3/FIX3`) the recreation is faithful: the whole delta
in `pkgs/evidence/tasks.py` is the refusal moving into `load_repos`, the
`len(flagged) == 1` → `if flagged` collapse, two docstrings, and the deletion of
`main`'s block; in `tests/evidence/test_tasks.py` it is B2's name assertion and
B3's two-arm loop. `docs/ledger/repos.toml` is identical. No third change rode
along.

## Findings

No MAJORs.

**MINOR-1 — the two-flag refusal is now a hard abort inside a loader, so it
pre-empts every other `check` error.** `pkgs/evidence/tasks.py:439-445`. FIX3's
Interfaces call it "a `check` error"; FIX3b moves it to `load_repos`, where it
must `raise SystemExit(1)` rather than join `check`'s accumulated error list. The
consequence is only that a two-flagged `repos.toml` hides the rest of a `check`
run's errors until it is fixed. Measured: with the two-flagged tree, `check`
prints the one line and nothing else, rc=1. This is what FIX3b asked for, so it
is recorded, not charged.

**MINOR-2 — the new `ledger` key of a `load_repos` row has no direct
assertion.** `pkgs/evidence/tasks.py:434` (`"ledger": bool(r.get("ledger", False))`)
vs `tests/evidence/test_tasks.py:489-506`, the one test of `load_repos`'s row
shape, which checks `name`, `path` and `plans` and not `ledger`. The default-False
arm is exercised indirectly by every unflagged fixture (and by B2), and the True
arm by B1/B3/B4, so nothing is unprotected in behaviour — but the row contract
itself is unpinned.

**MINOR-3 — the refusal message reads oddly for three or more flags.**
`pkgs/evidence/tasks.py:441-442`: `" and ".join(sorted(flagged))` renders
`"a and b and c"`. Cosmetic; the contract only ever names two.

## Verdict

**APPROVED.** Both of FIX3's MAJORs are closed by measurement — the mutant that
survived FIX3's whole suite (`no flag ⇒ first entry`) now dies at
`tests/evidence/test_tasks.py:2337`, and `docs/OPERATIONS.md` is absent from the
commit — and the prior MINOR-1 and MINOR-4 are closed as well: the refusal is in
`load_repos`, honoured by `check`, `write-board`, `brief`, `json`, `waves` and by
a `--repos` override, and B3's `write-board` arm is proved non-vacuous by mutant
O4. Ten mutants, ten killed. `evidence-unit` and `lint` green by
`nix build --rebuild`; the only red command is `githooks/pre-commit` on G8c, whose
whole diff is FIX3b leaving the queue at its own landing commit — the
orchestrator's board pass. Three MINORs, none owed; MINOR-2 is the only one worth
a line in a later task.
