# Opus gate — seat run sc4, task G8b — REJECTED

Reviewed read-only from a throwaway clone of `/home/dalhaka/factory/ws/sc4/G8b`
(branch `task/G8b`, head `f0494546f73e`, base `2273b8b`). Nothing was written to
the workspace, to `~/factory`, or to the live checkout.

## Summary

The code is G8's staged work recovered intact plus the git-only correction and a
third test, and the mechanism works: markers, splice, drift diff, the hook's
stale message, `evidence-unit` and `lint` green, ten of twelve mutants dead.
But the deliverable fails its own gate. **`nix develop -c githooks/pre-commit`
exits 1 on the delivered tree** with `tasks: docs/OPERATIONS.md queue block is
stale — run: evidence tasks write-board`, and the documented remedy
(`evidence tasks write-board`) does **not** produce what the hook checks: the
default derivation reads `docs/ledger/repos.toml`, whose paths are host-local
(`~/nixos-agent-env`, `~/flakes/media`, …), so it derives the block from the
*live host checkout* rather than from the tree being committed. Four different
blocks come out of the same commit depending on where you stand, including
`nothing queued` on a machine that has no `~/nixos-agent-env`. That is the MAJOR
the task brief named: the block still depends on host-local state, and on a
clean clone or a second machine the hook would refuse every commit with no way
to satisfy it. One bounded fix round (G8c) is owed.

## Design (git-only derivation)

The fix the implementer made is real and load-bearing. `main` now builds a
second graph and uses it for both `write-board` and `check --board`:

```python
board_graph = {
    "generated": graph["generated"],
    "repos": [scan_repo(r, plan_status, "/nonexistent", "/nonexistent") for r in repos],
}
```

so `~/factory/runs` and the evidence store cannot enter the block. Mutation M7
(revert to `args.runs_dir, args.store`) is killed by
`test_write_board_queue_ignores_run_results`, which builds a `ran` result and
asserts the queue still lists `E1`. So the runs/store half of the problem G8 hit
is genuinely fixed and genuinely tested.

The **repos half is not fixed**. `load_repos` expands `~` from
`docs/ledger/repos.toml`; the hook deliberately overrides it:

```sh
printf '[[repo]]\nname = "nixos-agent-env"\npath = "%s"\n' "$PWD" >"$repos_file"
python3 pkgs/evidence/tasks.py --root . --repos "$repos_file" \
  --runs-dir /nonexistent --store /nonexistent check --board docs/OPERATIONS.md
```

`write-board` has no such override, so the two derivations read different trees.
Measured on the same commit, same clone (`docs/OPERATIONS.md` restored between
each):

| how it is derived | block |
|---|---|
| what is committed | `nixos-agent-env: B1 G8 G8b PB0 RT2 (backup-audit-paths, operator-items, seat-routing, session-context)` |
| `tasks.py --root . write-board` (the documented command, this host) | `nixos-agent-env: B1 G8 G8b PB0 (backup-audit-paths, operator-items, session-context)` |
| hook-style (`--repos` → `$PWD`), i.e. what `check --board` compares against | `nixos-agent-env: B1 PB0 RT2 (backup-audit-paths, operator-items, seat-routing)` |
| `HOME=<empty dir> … write-board` (clean clone / second machine) | `nothing queued` |

Three consequences:

1. The committed block was derived from the operator's live `~/nixos-agent-env`,
   not from the workspace being committed. `RT2` is in it because the live tree
   said so at 14:53; by the time this gate ran, the live tree no longer did.
   The block is a snapshot of a *different* directory — host-local state by any
   reading.
2. The hook derives `B1 PB0 RT2` — `G8`/`G8b` drop out because this commit's
   subject is now in `git log`, so both tasks read `landed`. The block names the
   two tasks the commit itself lands, which makes it self-invalidating: it is
   stale the instant the commit exists.
3. On a clean clone (no `~/nixos-agent-env`) the documented remedy writes
   `nothing queued` while the hook demands the real block. The hook then refuses
   the commit, the remedy makes it worse, and there is no flag combination in
   the error message that escapes it.

The fix direction (for G8c, not prescriptive): `write-board` and `check --board`
must share one derivation rooted at `--root` — either synthesise the same
single-repo list the hook builds, or have `write-board` accept and default to
the hook's flags — so that "run: evidence tasks write-board" is literally the
command that satisfies the gate, on any machine.

## Checks

Throwaway clone at `…/scratchpad/gate-sc4-G8b`, `XDG_CACHE_HOME` under the
scratchpad, everything through `nix develop -c`.

- `git show --stat HEAD`: one commit on `2273b8b`; exactly
  `docs/OPERATIONS.md` (+5/−34), `githooks/pre-commit` (+1/−1),
  `pkgs/evidence/tasks.py` (+90/−1), `tests/evidence/test_tasks.py` (+79/−0).
  `flake.nix` untouched, as G8b's correction requires. Subject byte-identical to
  the plan's G8 subject. `Co-Authored-By: Claude Fable 5.1` present,
  `Generated-By` extra. Working tree clean.
- Against `/home/dalhaka/factory/ws/sc3/G8` (`git diff --cached`, read-only):
  G8 staged 4 files, +121/−36, and did **not** touch `flake.nix`. G8b contains
  that work verbatim plus the `board_graph` change (+9 lines in `main`) and the
  third test (+44 lines). Nothing from G8 was dropped.
- `nix build .#checks.x86_64-linux.evidence-unit -L --no-link` → **pass**.
- `nix build .#checks.x86_64-linux.lint -L --no-link` → **pass**.
- `nix develop -c pytest tests/evidence -q -p no:cacheprovider` → **69 passed**.
- `nix develop -c githooks/pre-commit` on the delivered tree → **exit 1**,
  `tasks: docs/OPERATIONS.md queue block is stale — run: evidence tasks
  write-board`. **This is the task's own Step 3 acceptance and it fails.**
- `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board` in the
  clone → the file **changes** (`RT2` and `2026-09-05-seat-routing.md` removed);
  `git diff --quiet docs/OPERATIONS.md` fails. The gate brief's step 4 condition
  — "the committed block is exactly what the hook derives" — does not hold, and
  the two disagreeing outputs are themselves both different from the hook's.
- Board shape (E8's guard): exactly one `## START HERE` (line 10), 58 lines
  (≤ 160), `<!-- tasks:begin -->`/`<!-- tasks:end -->` at lines 25/27, inside
  START HERE and above `## Log` (line 55). `**Now.**` is one line (≤ 10),
  `**How work runs.**` and `**Where things are.**` both intact, as are
  `**Operator owns:**` and `**Parked by decision**`.
- Stdlib only: `argparse datetime difflib fnmatch glob json os pathlib re
  subprocess sys tomllib`. No `sudo`, `nixos-rebuild`, `systemctl`, network
  calls, or writes outside the board path in the changed files.
- Real data: `nix develop -c bash tools/session-start.sh "$PWD"` renders START
  HERE with the block in place; the generated line reads naturally between the
  switch paragraphs and `**Now.**`, and the markers are HTML comments so they do
  not show in rendered markdown. Formatting is fine — the content is what is
  wrong.

## Red before green

- **(a) one character inside the block → hook fails.** Vacuous as written,
  because the hook already fails on the untouched tree. Ran it properly instead:
  re-derived the block with the hook's own flags → `nix develop -c
  githooks/pre-commit` **exit 0**; then `s/B1 PB0/B1 PBX/` inside the block →
  **exit 1** with exactly `tasks: docs/OPERATIONS.md queue block is stale — run:
  evidence tasks write-board`; re-derived → **exit 0** again. The guard itself is
  sound; the committed content is not.
- **(b) base `tasks.py` + HEAD's tests** (`git show HEAD~1:pkgs/evidence/tasks.py`)
  → 3 failed, 66 deselected: `test_board_block_roundtrip_and_drift`
  (`AttributeError: module … has no attribute 'board_drift'`),
  `test_board_without_markers_is_an_error`,
  `test_write_board_queue_ignores_run_results` (`invalid choice: 'write-board'`).
  Restored byte-identical.
- **(c) a board without markers** → `write_board` raises `SystemExit(1)` after
  printing `tasks: … is missing the <!-- tasks:begin --> … <!-- tasks:end -->
  markers`; pinned by `test_board_without_markers_is_an_error` and proven
  load-bearing by M4 below.

## Mutation table

Fourteen single-site edits on `pkgs/evidence/tasks.py`, each run against
`pytest tests/evidence -q -p no:cacheprovider` and reverted with a byte
comparison; the tree was `git status --porcelain`-clean after every batch.
Eight probe this task, six re-run mutants the G9 gate killed.

| # | mutation | killed | by |
|---|---|---|---|
| M1 | `write_board` always writes and returns True (the `new == text` short-circuit deleted) | yes | `test_board_block_roundtrip_and_drift` (1 failed, 68 passed) |
| M2 | `board_drift` returns None when stale (`if True: return None`) | yes | `test_board_block_roundtrip_and_drift` |
| M3 | the block omits the first repo with open work (`graph["repos"][1:]`) | yes | `test_board_block_roundtrip_and_drift` + `test_write_board_queue_ignores_run_results` |
| M4 | markers not required — `_splice_board` appends instead of returning None | yes | `test_board_without_markers_is_an_error` |
| M5 | `check --board` ignores the flag (`if args.board:` → `if False:`) | **no** | 69 passed — see Findings m1 |
| M6 | `render_board_block` uses every task, not the open-task waves (ran/rejected included) | yes | `test_board_block_roundtrip_and_drift` + `test_write_board_queue_ignores_run_results` |
| M7 | `board_graph` built from `args.runs_dir, args.store` (the git-only fix reverted) | yes | `test_write_board_queue_ignores_run_results` |
| M8 | `check --board` compares against the live `graph`, not `board_graph` | **no** | 69 passed — see Findings m1 |
| R-G9-M3 | `conflicts` drops the same-plan `continue` | yes | `test_conflicts_same_plan_not_reported` |
| R-G9-M5 | `legacy_open` counts every legacy row | yes | `test_brief_legacy_open_counts_only_open` |
| R-G9-M8 | `render_brief` dedupes by key instead of `chain_root` | yes | `test_brief_lists_chain_once_by_root` |
| R-G9-M9 | `last = members[0]` — the root owns rules 2–4 | yes | 5 failed, incl. `test_derive_status_precedence` |
| R-G9-C1 | `CHAIN_RE` suffix narrowed to `[a-z]` | yes | `test_chain_root` |
| R-G9-R3 | `touches_overlap` loses the directory-prefix rule | yes | `test_touches_overlap` |

All six re-run G9 mutants are still dead. Twelve of fourteen die overall; the two
survivors are the same hole (`main`'s `check --board` branch).

## What the board lost and where it lives

The commit removed 34 lines (the hand-written "Queued, in order." paragraph) and
added 5 (the two markers, the generated line, and a blank line).

| removed item | where it lives now |
|---|---|
| `B1` — the audit-records backup task | **the block** (`B1`, plan `2026-09-05-backup-audit-paths.md`) |
| B1's substance: the decision file, `/var/lib/lanes` + `/var/lib/egress-broker` join restic, payloads/results/broker CAs excluded, "lands with the next switch" | the decision and plan files; **not on the board** — acceptable (the block names the plan) |
| "running as seat run `bk1`" | **nowhere** — the git-only derivation cannot know about runs, so B1 now reads as queued although it is dispatched (finding m3) |
| evidence plan: 18 tasks landed, closes with switch #16 | **the Now paragraph** |
| follow-ups: parity tile summary, `evidence bundle` repo rows | **the Now paragraph** — but misattributed (finding m2) |
| the `] && [` bats lint guard and the `launch-today.sh` tidy = the model-comparison plan's two measurement tasks | **nowhere** — the Now paragraph gives that role to the two items above instead (finding m2) |
| ComfyUI: wave 1 landed 5edf092; wave 2 `W3 W5` as `cw2`; then `W4`/`W6`; host tasks WH1/WH2 | **the Now paragraph** |
| ComfyUI W2r's content (v0.34.5 at the tag's pins, comfy-angle, native `aimdo.so`, startup-clean check, model store, `comfy-worlds-init`) | the media plan and the board log — fine, it is landed history |
| what WH1/WH2 actually are (media becomes an input; two worlds; Caddy on eno1; two lab backup paths; a `media-refresh` tile) | **nowhere** on this board (finding m5) |
| session-context: spec+plan committed; `sc1` wave 1 running; waves 2–3 gating note | **the block** (`G8`, `G8b` — though see MAJOR-1) ; the sc1 status is obsolete, correctly dropped |
| Helm Home sub-project 1: spec, D-H1…D-H4, plan when the operator says so, first task the GlobalShortcuts measurement | **the Now paragraph**, intact |

Two items the block adds that the paragraph never had — `PB0` and `RT2` — are
correct derivations from `2026-09-05-operator-items.md` and
`2026-09-05-seat-routing.md`. The block's content is sensible against the real
plans; its problem is *which tree* it was derived from, not the rendering rule.

## Findings

**MAJOR-1 — the delivered tree fails its own acceptance gate.**
`nix develop -c githooks/pre-commit` exits 1 on `f0494546f73e` with the stale
message. The committed block names `G8` and `G8b`, whose `commit_subject` is this
commit's own subject; once the commit exists both read `landed` and must leave
the block. A generated block that lists the task landing it is self-invalidating,
and the hook is a *pre*-commit hook, so nothing catches it before the fact. The
practical effect: the next commit in this repo is refused until someone
regenerates the block — and per MAJOR-2 the documented command does not
regenerate it correctly. G8c must either exclude tasks whose subject equals the
commit being made, or (cleaner) accept that the board is rewritten every turn and
make the regeneration command actually work, so the treadmill is one command
long.

**MAJOR-2 — the block is not derived from the tree it is committed into.**
`write-board` reads `docs/ledger/repos.toml`, i.e. `~/nixos-agent-env` and four
sibling `~/flakes/*` paths; the hook overrides `--repos` to `$PWD` and one repo.
The FACTORY-NOTES claim "board re-derived git-only so write-board matches the
hook" is half true: the runs/store dependency is gone (M7 proves it), the
host-path dependency is not. Measured four different blocks from one commit
(table in **Design**), including `nothing queued` when `~/nixos-agent-env` is
absent. On a clean clone or a second machine the hook refuses every commit and
the remedy in its own error message writes the wrong content. This is the failure
mode the task brief called a MAJOR, and it is present.

**m1 (minor, teeth) — `main`'s `check --board` branch has no unit coverage.**
M5 (the `--board` flag ignored entirely) and M8 (drift compared against the live
`graph` instead of `board_graph`) both survive the whole suite. The functions
`write_board`/`board_drift` are well pinned; the wiring that makes the hook work
is proven only by running the hook, and M8 in particular would silently restore
the runs/store dependency on the *check* side while `test_write_board_queue_…`
kept passing. G8c should add a `tk.main([… "check", "--board", …])` test that
asserts rc 1 and the exact message with a stale fixture board, and rc 0 with a
current one — with a `ran` result present, so it also pins `board_graph`.

**m2 (minor) — the Now paragraph misstates what it inherited.** The removed
paragraph said the parity-tile summary and the `evidence bundle` repo rows are
*evidence-plan follow-ups*, and that the `] && [` bats lint guard and the
`launch-today.sh` tidy are *the model-comparison plan's two measurement tasks*.
The rewrite merges the two sentences and gives the measurement-task role to the
wrong pair; the bats guard and the `launch-today.sh` tidy have disappeared from
the board entirely.

**m3 (minor) — dispatched work now reads as queued.** By design the block cannot
see `~/factory/runs`, so `B1` (running as `bk1`) is listed under "Queued
(derived)". The word "Queued" now means "not landed", which is not what the
operator will read. Either the label should say so, or the Now paragraph should
keep the run ids (the hand-written paragraph did).

**m4 (minor) — `board_graph` is built unconditionally.** Every subcommand,
including `brief`, `json`, `waves` and `conflicts`, now pays a second full
`scan_repo` of every repo (a second `git log` per repo) that only `check --board`
and `write-board` ever read. Build it lazily.

**m5 (minor) — WH1/WH2 lost their description.** "media becomes an input; two
worlds, Caddy on eno1, two lab backup paths; a `media-refresh` tile" is now on no
board and in no derived line; only the bare keys survive in the Now paragraph.

**m6 (cosmetic) — wrong remedy for a missing marker.** When the markers are
absent `board_drift` returns a "markers missing" string, so `check --board`
prints "queue block is stale — run: evidence tasks write-board"; running that
command then exits 1 with a different message. Report the marker case distinctly.

## Deviations

- **From G8's plan, sanctioned by G8b:** `flake.nix`'s `lint` does *not* gain
  `--board`. Correct — the flake sandbox has no git history. The commit subject
  still says "the hook and lint refuse drift"; the plan required a byte-identical
  subject, so this is accepted as a known cosmetic inaccuracy in the subject
  line, not a finding.
- The gate's step 5(a) (mutate one character, expect the hook to go red) could
  not be run as written because the hook is already red on the untouched tree;
  it was run against a re-derived board instead, and the result is recorded
  above.
- No `--runs-dir`/`--store` were pointed at real data for the board checks; every
  board derivation in this review used either the clone or the hook's own
  `/nonexistent` flags. The live repo was read only by the default `write-board`
  path (git log, read-only) to demonstrate MAJOR-2.
