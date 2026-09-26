# Opus gate — seat run sc4, task G8c — APPROVED

Reviewed read-only from a throwaway clone of `/home/dalhaka/factory/ws/sc4/G8c`
(branch `task/G8c`, head `0b120bdfdc11`, base `df3a1ad`). Nothing was written to
the workspace, to `~/factory`, or to the live checkout; the only writes were in
the clone, the scratch cache and this file.

## Summary

Both MAJORs from the G8b gate are closed, and closed by measurement rather than
by prose. **MAJOR-2 is dead:** the block now comes from `board_graph(root)` —
one synthesised repo, `basename(root)` as its name, no `repos.toml`, no runs
dir, no store — and the regenerated block is **byte-identical under an empty
`HOME` and under the real `HOME`**, in a clean clone whose directory is not even
called `nixos-agent-env`. **MAJOR-1 is closed under the amended rule:** on the
delivered tree `nix develop -c githooks/pre-commit` exits 1 exactly once with the
exact documented message, regenerates the block, and a single `git add
docs/OPERATIONS.md` makes the very next run green — one extra step, no loop
(measured, both runs). Fifteen mutations applied and reverted, **fifteen killed**,
including the two G8b survivors (`check --board` ignoring its flag; drift
compared against the live graph) and all six re-run G9 mutants. `evidence-unit`
and `lint` pass, and `evidence-unit` was proven live by a mutation. The board
text restores everything the G8b gate said was lost. What remains are five
minors and cosmetics, none of them load-bearing.

## Design (tree-only derivation; the regenerate step)

`board_graph(root)` is the whole fix:

```python
repo = {"name": os.path.basename(root) or "repo", "path": root, "plans": PLANS_GLOB}
return {"generated": …, "repos": [scan_repo(repo, {}, None, None, run=run)]}
```

No `load_repos`, so no `~` expansion; `plan_status` is `{}`; `runs_dir` and
`store` are `None` (`read_results(None)` globs `None/*/*.result` → empty;
`read_recorded(None)` degrades to `{}` through its existing `except`). Both
`main`'s `write-board` branch and its `check --board` branch call
`board_graph(args.root)`, so the two derivations are the same function of the
same tree and **cannot** disagree. `render_board_block` deliberately omits the
repo name, which is why the clone's directory name (`gate-sc4-G8c` in my
throwaway) does not change a byte of the block. Measured:

| derivation | block body |
|---|---|
| clone at HEAD, real `HOME` | `B1 FD1 PB0 RT2b (…backup-audit-paths.md …factory-dispatch.md …operator-items.md …seat-routing.md)` |
| same clone, `HOME=<empty dir>` | identical — `cmp` says byte-identical |
| fresh `git clone` of the clone, `HOME=<empty dir>`, via `main` | identical |

Compare the G8b gate's table, which produced four different blocks from one
commit. The host-local dependency is gone.

The **regenerate step** replaces the old "refuse and tell the user to run a
command" with "run the command yourself, then refuse":

```sh
python3 pkgs/evidence/tasks.py --root . write-board --board docs/OPERATIONS.md --quiet
if ! git diff --quiet -- docs/OPERATIONS.md; then
  echo "tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again" >&2
  exit 1
fi
```

This is the right shape for the amendment. A landing removes its own key from
the queue, so the block committed at time *T* is stale at *T+1* by construction;
the hook absorbs that at the next commit in one bounded step. I verified the
step is bounded and not a treadmill: stale index → exit 1 + regenerated worktree
→ `git add` → exit 0.

**On the `.result` note.** The implementer is right, and the plan's Step 2/Step 4
text is what is wrong. The plan asserted "the block will not list G8c … at commit
time G8c's own subject IS in the log". It is not: G8c is the *first* commit on
the branch, so pre-commit the subject is absent from `git log`, G8c reads
`ready`, and a hook-green tree **must** list G8c. Post-commit (my clone) the
subject is in the log, G8c reads `landed`, and it drops out — which is exactly
the one-line drift I measured. The plan's clean-clone probe expecting `rc=0`
therefore cannot hold for this commit and only for this commit; from the next
commit onward the block no longer names its own lander. Acceptance is judged as
the brief directs — hook green on the tree **as committed** — and that holds.

`render_board_block` lists wave-1 keys only, so a *blocked* chain (`PB1`, blocked
on `PB0` in this tree) does not appear. That matches G8's published interface
("`<wave-1 keys>`") and narrows G8c Step 1(c)'s "ready/blocked chains"; recorded
as a deviation, not a fault — a "Queued" line that lists what is actually next is
the more useful artefact.

## Checks

Throwaway clone at `…/scratchpad/gate-sc4-G8c`, `XDG_CACHE_HOME` under the
scratchpad, all tooling through `nix develop -c`, pytest with
`PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`.

- `git rev-list --count df3a1ad..HEAD` = **1**. `git show --stat HEAD`: exactly
  `docs/OPERATIONS.md` (+5/−34), `githooks/pre-commit` (+8/−0),
  `pkgs/evidence/tasks.py` (+107/−1), `tests/evidence/test_tasks.py` (+188/−0).
  **`flake.nix` untouched**, as G8b's correction requires.
- Subject `cmp`-identical to the plan's G8/G8b/G8c subject (byte comparison
  against a literal, not an eyeball). `Co-Authored-By: Claude Fable 5.1` present;
  `Generated-By` extra, allowed.
- `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` → **pass**, and
  proven live: with `if args.board:` mutated to `if False:` the same build
  **fails** (`test_main_check_board_stale_current_and_runs_free`, `assert 0 == 1`).
- `nix build .#checks.x86_64-linux.lint -L --no-link` → **pass**.
- `nix develop -c pytest tests/evidence -q -p no:cacheprovider` → **72 passed**.
- **(i) the hook on the delivered tree.** Run 1: exit **1**, stderr exactly
  `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git
  add docs/OPERATIONS.md and commit again`, and the worktree block changed by one
  line (`G8c` and `…session-context.md` removed). `git add docs/OPERATIONS.md`,
  run 2: exit **0**. One extra step, no loop, message byte-exact.
- **(ii) empty `HOME`.** `render_board_block(board_graph("."))` written to a file
  under real `HOME` and under `HOME=<empty dir>`; `cmp` → **byte-identical**.
  Repeated through `main` in a fresh `git clone` with `HOME=<empty dir>`:
  `write-board` exits 0 and produces the same one-line drift as with the real
  `HOME`. MAJOR-2 closed.
- Clean-clone `check --board` (the plan's Step 4 probe): `rc=1` under **both**
  the empty and the real `HOME`, with the same message — i.e. the residual drift
  is the landing effect, not machine state. Recorded in Deviations.
- Board shape: 58 lines (≤ 160); exactly one `## START HERE` (line 10); markers
  at lines 25/27, inside START HERE and above `## Log` (line 55); `**Now.**` is
  **1 line** (≤ 10); `**Operator owns:**`, `**Parked by decision**`, `**How work
  runs.**`, `**Where things are.**` all intact.
- Stdlib only: `argparse datetime difflib fnmatch glob json os pathlib re
  subprocess sys tomllib`. No `sudo`, `nixos-rebuild`, `systemctl`, no network,
  no writes outside the board path.
- Real data: `nix develop -c bash tools/session-start.sh "$PWD"` renders START
  HERE with the block in place; the generated line sits naturally between the
  switch paragraphs and `**Now.**`, the markers are HTML comments and do not
  render, and the header sentence tells the reader where in-flight state lives.

## Red before green

- **(a) stale block → regenerate + exit 1; `git add` → green.** First attempt was
  *vacuous* and I say so: I dirtied one character in the **worktree** while the
  index already held the correct block, and the hook exited **0** — it regenerated
  the file back and found no worktree/index difference (see Findings f4). Run
  properly, with the stale block **staged**: hook → exit **1** with the exact
  message, worktree regenerated (`PBX` → `PB0`); `git add docs/OPERATIONS.md`;
  hook → exit **0**. Tree restored clean afterwards.
- **(b) base `tasks.py` + HEAD's tests** (`git show HEAD~1:pkgs/evidence/tasks.py`)
  → **6 failed, 66 passed**: all six new tests, on
  `AttributeError: module 'tasks' has no attribute 'board_drift' / 'board_graph' /
  'render_board_block'` and `invalid choice: 'write-board'`. `tasks.py` restored
  byte-identically (sha256 compared).
- **(c) board without markers** → `write-board` prints
  `tasks: <path> is missing the <!-- tasks:begin --> … <!-- tasks:end --> markers`
  and exits 1. The message does **not** tell the user to run `write-board`, as
  the gate requires; pinned by `test_board_without_markers_is_an_error` and proven
  load-bearing by M8. (`check --board` still mislabels this case — Findings f1.)

## Mutation table

Fifteen single-site edits on `pkgs/evidence/tasks.py`, each applied, run against
`pytest tests/evidence -q -p no:cacheprovider`, reverted, and the file's sha256
compared to the original; `git status --porcelain` empty after every batch. Nine
probe this task, six re-run mutants the G9 gate killed.

| # | mutation | killed | by |
|---|---|---|---|
| M1 | `board_graph` builds its repos from `load_repos(docs/ledger/repos.toml)` | yes | `test_write_board_queue_ignores_run_results` + `test_board_graph_derives_this_tree_ignoring_repos_toml` (2 failed) |
| M2 | `write-board` splices the live `graph` (runs dir + store) instead of `board_graph` | yes | `test_write_board_queue_ignores_run_results` |
| M3 | `check --board` compares against the live `graph` (G8b's surviving M8) | yes | `test_main_check_board_stale_current_and_runs_free` |
| M4 | `check --board` ignores the flag — `if args.board:` → `if False:` (G8b's surviving M5) | yes | `test_main_check_board_stale_current_and_runs_free` |
| M5 | `write_board` always writes and returns True (the `new == text` short-circuit deleted) | yes | `test_board_block_roundtrip_and_drift` |
| M6 | `render_board_block` renders every task, not the wave-1 open tasks (ran/rejected/landed included) | yes | 4 tests, incl. `test_render_board_block_header_and_ready_blocked_only` |
| M7 | header string `this tree` → `this repo` | yes | `test_board_block_roundtrip_and_drift` + `test_render_board_block_header_and_ready_blocked_only` |
| M8 | `_splice_board` tolerates missing markers (appends instead of returning None) | yes | `test_board_without_markers_is_an_error` |
| M9 | `board_graph` gains `runs_dir`/`store` and `main` passes `args.runs_dir`/`args.store` | yes | `test_main_check_board_stale_current_and_runs_free` |
| R-G9-M3 | `conflicts` drops the same-plan `continue` | yes | `test_conflicts_same_plan_not_reported` |
| R-G9-M5 | `legacy_open` counts every legacy row | yes | `test_brief_legacy_open_counts_only_open` |
| R-G9-M8 | `render_brief` dedupes by key instead of `chain_root` | yes | `test_brief_lists_chain_once_by_root` |
| R-G9-M9 | `last = members[0]` — the chain root owns rules 2–4 | yes | 5 failed, incl. `test_derive_status_precedence` |
| R-G9-C1 | `CHAIN_RE` suffix narrowed to `[a-z]` | yes | `test_chain_root` |
| R-G9-R3 | `touches_overlap` loses the directory-prefix rule | yes | `test_touches_overlap` |

**15/15 killed.** The G8b gate's two survivors are both dead, killed by the one
new `main`-level test the review asked for; its M1 finding is closed.

## Board text

The three items the G8b gate recorded as lost are back, and the paragraph is one
line:

| G8b finding | state at G8c |
|---|---|
| m2 — the model-comparison plan's two measurement tasks lost, and the follow-ups misattributed | restored and correctly attributed: "The model-comparison plan's Pro arm has landed; its two measurement tasks are the `] && [` bats lint guard and the `launch-today.sh` tidy", separately from "The evidence plan closed with switch #16, leaving two follow-ups: the parity tile's summary and `evidence bundle` repo rows" |
| m5 — WH1/WH2 lost their description | restored: "the host tasks WH1/WH2 here — media becomes an input; two worlds; Caddy on eno1; two lab backup paths; a `media-refresh` tile" |
| m3 — dispatched work reads as queued | addressed twice: the header now says "in-flight state is in the session brief", and the Now paragraph says "B1 … is running as seat run `bk1` (paused session)"; `cw2` for ComfyUI wave 2 is likewise named |

The block itself (`B1 FD1 PB0 RT2b`) is a correct derivation from the four plans
in this tree; `PB1` is `blocked` on `PB0` and therefore in wave 2, not the line.

## Findings

**f1 (minor, carried from G8b m6) — `check --board` still mislabels a missing
marker.** With no markers, `board_drift` returns a "markers missing" string and
`check --board` prints `queue block is stale — run: evidence tasks write-board`;
running that command then exits 1 with a different message. Measured. Exposure is
now CLI-only (the hook uses `write-board`, not `check --board`), so this is
smaller than it was, but it is the same defect the last gate named. Report the
marker case distinctly.

**f2 (minor) — `write-board --quiet` is an accepted flag that nothing reads.**
`write_board_p.add_argument("--quiet", …)` is declared and the hook passes it, but
no code branches on `args.quiet` (the success path prints nothing anyway). Either
make `write-board` say what it did without `--quiet`, or drop the flag; an
argument that silently does nothing is a small lie in the hook's own text.

**f3 (cosmetic, carried from G8b m4) — the live graph is still built
unconditionally, including for `write-board`.** `main` builds `graph` (i.e.
`load_repos` on `docs/ledger/repos.toml` with its `~` paths, plus a `git log` per
repo) before dispatching, so the hook's `write-board` step reads the operator's
live checkouts read-only even though its output provably does not depend on them.
Measured cost: `write-board` 0.129 s vs 0.046 s for `board_graph` alone — small.
Still worth making lazy: it is surprising for a step whose whole point is
"this tree only", and it enlarges the hook's failure surface for no benefit.

**f4 (minor, new) — an *unstaged* edit inside the block is silently reverted.**
The guard is `git diff --quiet -- docs/OPERATIONS.md`, i.e. worktree vs index. If
the index already holds the correct block and someone hand-edits the block in the
worktree, the hook rewrites it and exits **0** with no message (measured: `PBX` →
`PB0`, rc 0). What gets committed is still correct, so this is not a correctness
hole — but a file edit disappearing without a word is worth one line of output.

**f5 (cosmetic, new) — pathspec / `--only` commits could loop.** With `git commit
--only <path>` (or `git commit <pathspec>`) git hands the hook a temporary index
that excludes `docs/OPERATIONS.md`; a stale block then makes the hook exit 1, and
the remedy (`git add docs/OPERATIONS.md`) updates the real index, not the
temporary one, so the next attempt fails identically. No tooling in this repo
commits that way (`factory-brief` and `dark-factory.js` both prescribe
`nix develop -c git commit -F <msgfile>`), so this is a hazard for a human, not a
present breakage. A sentence in the runbook would close it.

## Deviations

- **The plan's Step 2/Step 4 expectation is wrong, and the delivery is right.**
  The plan claimed the block "will not list G8c" and that the clean-clone probe
  returns `rc=0`. G8c is the first commit on its branch, so pre-commit its subject
  is not in `git log` and a hook-green tree must list it; post-commit it drops
  out and the clean-clone probe returns `rc=1` with a one-line drift. Judged as
  the gate brief directs (hook green on the tree **as committed**, one bounded
  `git add` afterwards) — accepted. This is a one-commit artefact: from the next
  commit the block no longer names its own lander.
- **`render_board_block` lists wave-1 keys only**, not every ready/blocked chain
  as G8c Step 1(c)'s wording suggests. It matches G8's published interface and is
  the more useful line; `PB1` (blocked on `PB0`) is correctly absent.
- **Carried from the G8b gate, sanctioned there:** `flake.nix`'s `lint` does not
  gain `--board` (the flake sandbox has no git history), while the commit subject
  still says "the hook and lint refuse drift". The plan requires a byte-identical
  subject, so this stays a known cosmetic inaccuracy in the subject line, not a
  finding.
- Step 5(a) was first run vacuously (worktree edit against a correct index) and
  is reported as such above; the real red was then run with the stale block
  staged.
- No `--runs-dir`/`--store` were pointed at real data. The live host checkout was
  read only by `main`'s unconditional graph build (read-only `git log`) while
  demonstrating f3, and by `tools/session-start.sh`'s evidence bundle.
