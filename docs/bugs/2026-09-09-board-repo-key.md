---
bug: BUG3
status: re-gathered
round: 3
---

# The board generator names the repo by the directory basename, so a seat's pre-commit hook regenerates a wrong queue block

This document is BUG3's re-gather. The first round (`run bug3`) was rejected by
`docs/reviews/2026-09-09-opus-review-bug3-BUG3.md` on one MAJOR (establishment
2's evidence was fabricated) and eight MINORs; the second round (`run bug3b`)
was rejected by `docs/reviews/2026-09-09-opus-review-bug3b-BUG3b.md` on two
MAJORs (establishment 2's answer was wrong — a seat commit did land a wrong
block — and three pastes did not reproduce) and five MINORs. Because BUG3 never
landed, this document is recreated in full from those reviews plus fresh
re-runs; every line number below was produced by a pasted `grep -n`, every claim
carries the command that produced it and that command's real, untrimmed output
(elisions marked `…`).

## Observed

The pre-commit hook's board check (`githooks/pre-commit`, G8c) regenerates
`docs/OPERATIONS.md`'s `**Queued**` block and exits 1 when the regenerated
block differs from the index. In a clone whose directory basename is not
`nixos-agent-env`, the regeneration re-adds a withdrawn task, because the
generator keys the repo on the basename.

The reproduction, in a worktree whose basename is `BUG3base` (the wrong name),
at commit `069e337` (the commit that typed BUG3):

```
$ basename "$PWD"
BUG3base
$ nix develop -c python3 pkgs/evidence/tasks.py --root . write-board --quiet
evaluation warning: nixfmt-rfc-style is now the same as pkgs.nixfmt which should be used instead.
exit=0
$ git diff -U0 docs/OPERATIONS.md | grep -E '^[+-]\*\*Queued'
-**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** BUG1ac BUG2b BUG3 HH1 HH2 HH3 HH4 PW1glm PW1kimi PW1pro SP4 (…)
+**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** BUG1ac BUG1b BUG2b BUG3 HH1 HH2 HH3 HH4 PW1glm PW1kimi PW1pro SP4 (…)
```

One hunk, one key added: the withdrawn `BUG1b`, re-added, because in a tree
named `BUG3base` the withdrawn-row lookup — keyed `repo = "nixos-agent-env"` in
`docs/ledger/task-status.toml` — never matches the tree's basename.

The counterfactual (MINOR-4), the same commit in a worktree whose basename IS
`nixos-agent-env`:

```
$ basename "$PWD"
nixos-agent-env
$ nix develop -c python3 pkgs/evidence/tasks.py --root . write-board --quiet
evaluation warning: nixfmt-rfc-style is now the same as pkgs.nixfmt which should be used instead.
exit=0
$ git diff --stat docs/OPERATIONS.md
[empty — no output]
$ git diff --quiet docs/OPERATIONS.md; echo $?
0
```

Same tree, same commit, no diff. The directory basename is the whole
discriminator.

Side by side, the `diff --stat` for the two worktrees:

```
$ git -C .scratch/nixos-agent-env diff --stat docs/OPERATIONS.md
[empty]
$ git -C .scratch/BUG3base diff --stat docs/OPERATIONS.md
 docs/OPERATIONS.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

## Mechanism

`board_graph` — the function behind both `write-board` and `check --board` —
derives the repo's name from the tree's basename:

```
$ grep -n 'board_graph' pkgs/evidence/tasks.py
1151:def board_graph(root, run=None):
2304:            if board_drift(board, board_graph(args.root)) is not None:
2344:        write_board(board, board_graph(args.root))
```

```
$ sed -n '1151,1162p' pkgs/evidence/tasks.py
def board_graph(root, run=None):
    """The board's queue graph: THIS repo, THIS tree only. No repos.toml (home
    paths differ per machine), no runs dir, no store — so `write-board` and
    `check --board` derive the block identically anywhere, including a clean
    clone. The one repo's name is the tree's basename; the rendered block
    omits it (the header already says "this tree")."""
    root = os.path.abspath(root)
    repo = {
        "name": os.path.basename(root) or "repo",
        "path": root,
        "plans": PLANS_GLOB,
    }
```

`os.path.basename` occurs four times in `tasks.py`; only the one at `:1159`
feeds the repo name:

```
$ grep -n 'os.path.basename' pkgs/evidence/tasks.py
636:        key = os.path.basename(p)[: -len(".log")]
637:        run_name = os.path.basename(run_dir)
794:            plan = os.path.basename(row.get("plan", "") or "")
1159:        "name": os.path.basename(root) or "repo",
```

The withdrawn/parked overlay looks a task up by the tuple
`(repo.name, plan, key)`:

```
$ sed -n '1080,1090p' pkgs/evidence/tasks.py
        t["class"] = task_class(t["touches"], class_rules)

    # a task-status row withdraws/parks a key regardless of derived state:
    # never scheduled, never conflicting, shown once in the brief.
    for t in tasks:
        row = task_status.get((repo["name"], t["plan"], t["key"]))
        if row and row["status"] in ("withdrawn", "parked"):
            t["state"] = row["status"]
            t["detail"] = row.get("note", "")

    attributed_elsewhere = sorted(
```

Every row in `task-status.toml` carries `repo = "nixos-agent-env"`, and four
keys are withdrawn. The grep prints twenty lines (the header comment, the four
`repo =`/`key =`/`status =` row-triples, and the two `note =` lines at `:46`
and `:54`):

```
$ grep -n 'withdrawn\|parked\|key =\|repo = "nixos' docs/ledger/task-status.toml | wc -l
20
$ grep -n 'withdrawn\|parked\|key =\|repo = "nixos' docs/ledger/task-status.toml
1:# Withdrawn or parked typed tasks (plan 2026-09-05-seat-routing.md, OG1).
4:# append-only, so a task that is no longer wanted is withdrawn with a status
6:# learns to read it in a follow-up (OG2): a task with a `withdrawn` row is
7:# never scheduled, and `parked` rows are shown in the brief once. Until OG2
13:# key = "<task key from the heading, e.g. OG1>"
14:# status = "withdrawn" | "parked"
26:repo = "nixos-agent-env"
28:key = "SB5"
29:status = "withdrawn"
34:repo = "nixos-agent-env"
36:key = "SB6"
37:status = "withdrawn"
42:repo = "nixos-agent-env"
44:key = "BUG1"
45:status = "withdrawn"
46:note = "mis-keyed by the orchestrator and never dispatched: BUG1a reads as BUG1's chain successor, so typing the corrected re-gather as an unsuffixed BUG1 made it a root whose chain already owed a fix round, and nothing was dispatchable. The typed heading is append-only, so it is withdrawn here rather than renamed. Superseded by BUG1ab, which is the same contract keyed as the fix round it actually is"
50:repo = "nixos-agent-env"
52:key = "BUG1b"
53:status = "withdrawn"
54:note = "typed 2026-09-09 as the broker-bypass fix stage and never dispatched: pkgs/evidence/tasks.py:59 (CHAIN_RE) reads BUG1b as a member of the BUG1 chain, so it would derive as landed the moment BUG1ac lands and never schedule. The typed heading is append-only, so it is withdrawn here; FIX1 carries the same contract as its own root (implement/code routes to Pro at rung 1, no suffix needed)"
```

In a tree named anything else, `repo["name"]` is that basename, the tuple
never matches, the withdrawn/parked overlay silently fails, and the raw derived
state — including every still-queuable withdrawn key — stands.

`board_graph` is defined once (`:1151`, pasted above) and called at two sites,
and both matter for where this bites. `:2304` runs inside `check --board`, which
`githooks/pre-commit` covers by writing a temporary `repos.toml` with the fixed
name `nixos-agent-env` before calling `check` (so the check passes). `:2344` is
`write-board`, which the hook then runs *unconditionally* with no override:

```
$ sed -n '55,72p' githooks/pre-commit
# E2: the claims file's stale gaps fail the commit (a real clock lives in the
# devShell, unlike the flake sandbox, which checks shape only).
python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)" --repo-root .
# G5: the derived task graph must be well-formed and the repo map current.
# tasks.py reads its repos from a `--repos` file pointing at THIS tree ($PWD),
# not ~/nixos-agent-env (the default), so the gate inspects the commit rather
# than the operator's live checkout.
repos_file="$(mktemp)"
printf '[[repo]]\nname = "nixos-agent-env"\npath = "%s"\n' "$PWD" >"$repos_file"
python3 pkgs/evidence/tasks.py --root . --repos "$repos_file" --runs-dir /nonexistent --store /nonexistent check
rm -f "$repos_file"
# G8c: the board's Queued block is derived from THIS tree only (git landed +
# reviews, never runs/store); regenerate it first and refuse a commit where it
# drifted — a landed key leaves the queue, so staleness is by design.
python3 pkgs/evidence/tasks.py --root . write-board --board docs/OPERATIONS.md --quiet
if ! git diff --quiet -- docs/OPERATIONS.md; then
  echo "tasks: docs/OPERATIONS.md queue block was stale and has been regenerated — git add docs/OPERATIONS.md and commit again" >&2
  exit 1
```

`write_board` at `:69` thus regenerates the block with the basename-derived
repo name and none of the withdrawn rows apply, so the hook drifts the block
and exits 1.

## Where the defect is

The defect is the single line `pkgs/evidence/tasks.py:1159` — the basename
assignment. `board_graph`'s docstring straight out says "The one repo's name is
the tree's basename", which is true only in the operator's checkout.

The defect reaches the board through two routes, and both carried it to
`main`, not one:

1. **A seat's own pre-commit hook — and a seat's task commit landed the wrong
   block.** In a workspace whose basename is not `nixos-agent-env`, G8c
   regenerates a wrong block and exits 1 every time the regenerated file
   differs from the index — which it does whenever a withdrawn task would
   otherwise be queued. The hook's check is `git diff --quiet --
   docs/OPERATIONS.md`, worktree against the **index**, so it stays red on
   every run until the regenerated block is staged, and passes the moment it
   is. That staged, wrong block then travels in the seat's own task commit:
   `0443648` (run `sb10`) landed one on `main` three minutes after
   `b932735` withdrew `SB5` and `SB6` (see the survey below).

2. **A landing-run merge, independent of any seat commit.** `4ec8951`
   (2026-09-08T05:37:01, a merge into `task/SB5b`) regenerated the block 25
   minutes after `b932735` (2026-09-08T05:12:04) withdrew `SB5` and `SB6`, and
   carried the withdrawn `SB6` forward. Its hunk:

   ```
   $ git show 4ec8951 -- docs/OPERATIONS.md | grep -E '^[+-]' | grep Queued | cut -c1-12 | cat -A
   - **Queued ($
   ++**Queued ($
   ```

   The second line's `++` is the combined-diff marker: the line is in
   **neither** parent, i.e. the merge itself regenerated it rather than
   inheriting it from either side. `SB5` and `SB5b` are correctly removed, but
   `SB6` and `SB6b` — also withdrawn by `b932735` — are carried forward. This
   is the same basename mechanism reaching `main` through a branch-level merge
   of the operator's own tree, not through a seat's task commit.

`factory-integrate:79-101` (pasted in the blast-radius section below) cannot
see either route: its guard strips the `<!-- tasks:begin --> /
<!-- tasks:end -->` markers and everything between them before comparing, so a
wrong block that stays inside the markers is invisible to it.

The withdrawal that should have suppressed `SB6`:

```
$ git log -1 --format='%H %ci %s' b932735
b9327356572f2c7a71f03279b8105e194fb5b95b 2026-09-08 05:12:04 -0500 docs: plan — SB5b and SB6b typed from the row-3 reading, SB5 and SB6 withdrawn; concept 2026-09-08b (test: lint)
```

## Whether it has already landed

The question item 2 asks: has any seat commit landed a wrong (re-added
withdrawn) queue block since 2026-09-05? The answer is **one**: a single seat
task commit, `0443648` (run `sb10`), landed a wrong block on `main`, and the
landing-run merge `4ec8951` carried it forward again 22 minutes later.

The survey, in the gate's form — a `Generated-By:` test, which is the seat
marker — is:

```
$ git log --format='%H %h %cs %s' --since='2026-09-05' -- docs/OPERATIONS.md | while read -r H h d s; do git log -1 --format='%B' "$H" | grep -q '^Generated-By:' && echo "$h $d $s"; done
a26d232 2026-09-09 docs: gate review — bug3 BUG3 REJECTED; plan — BUG3b the fix round, the G8c route corrected to a pathspec commit (test: lint)
a9017da 2026-09-09 docs: plan — FIX1's seat-eval citation re-measured after CR4b; the queue block with FIX1 ready (test: lint)
6c496a5 2026-09-09 docs: gate review — bug1ac BUG1ac APPROVED, the broker-bypass findings ready to land (test: lint)
069e337 2026-09-09 docs: plan — BUG3, the board generator's repo key comes from the directory basename (test: lint)
a86e226 2026-09-09 docs: gate review — bug2 BUG2 REJECTED; plan — BUG2b, the drive-seat URL re-gathered with the loopback fact and the cookie jar (test: lint)
237b3c0 2026-09-09 docs: gate review — bug1ab BUG1ab REJECTED; plan — BUG1ac the fix round, FIX1 the broker-bypass fix, BUG1b withdrawn (test: lint)
401bb01 2026-09-08 evidence: report ladder — every .result joined to its gate review and grouped by route, role, kind, size, class, model, effort and rung, the orchestrate section from run.meta driver: and the drive jobs, every line refused under five (test: evidence-unit, lint)
0443648 2026-09-08 docs: the seat runs behind its broker — the operator's runbook, the lane paragraph, the claim's closing path, the decision addendum (test: lint)
8875436 2026-09-07 evidence: the reader learns derived and monthly streams, join_tasks_gates on (run_id, key), the n-gate, the bundle's join line (test: evidence-unit, lint)
d26333f 2026-09-06 evidence: tasks.py check --draft judges a plan file outside the plans directory against the live graph, MAP.md's check names and byte-exact subjects, and prints its waves and conflicts (test: evidence-unit, lint)
2cbcc10 2026-09-05 evidence: a task section names the repo it runs in and is attributed there; task-status.toml withdraws or parks a task without touching plan text (test: evidence-unit, lint)
0b120bd 2026-09-05 evidence: the board's queue block is generated by evidence tasks write-board; the hook and lint refuse drift (test: evidence-unit, lint)
2667a14 2026-09-05 docs: board — one START HERE that carries the plan; log, archive and policies move under docs/board; the lint gate checks the shape (test: lint)
```

The seat marker is the `Generated-By:` trailer naming a seat — never the
subject prefix. Per commit, for the eight `docs:` rows:

```
$ for H in a26d232 a9017da 6c496a5 069e337 a86e226 237b3c0 0443648 2667a14; do git log -1 --format="%h %s%n%(trailers:key=Generated-By)" "$H"; echo "---"; done
a26d232 docs: gate review — bug3 BUG3 REJECTED; plan — BUG3b the fix round, the G8c route corrected to a pathspec commit (test: lint)
Generated-By: Claude Fable 5.1 (orchestrator)
---
a9017da docs: plan — FIX1's seat-eval citation re-measured after CR4b; the queue block with FIX1 ready (test: lint)
Generated-By: Claude Fable 5.1 (orchestrator)
---
6c496a5 docs: gate review — bug1ac BUG1ac APPROVED, the broker-bypass findings ready to land (test: lint)
Generated-By: Claude Fable 5.1 (orchestrator)
---
069e337 docs: plan — BUG3, the board generator's repo key comes from the directory basename (test: lint)
Generated-By: Claude Fable 5.1 (orchestrator)
---
a86e226 docs: gate review — bug2 BUG2 REJECTED; plan — BUG2b, the drive-seat URL re-gathered with the loopback fact and the cookie jar (test: lint)
Generated-By: Claude Fable 5.1 (orchestrator)
---
237b3c0 docs: gate review — bug1ab BUG1ab REJECTED; plan — BUG1ac the fix round, FIX1 the broker-bypass fix, BUG1b withdrawn (test: lint)
Generated-By: Claude Fable 5.1 (orchestrator)
---
0443648 docs: the seat runs behind its broker — the operator's runbook, the lane paragraph, the claim's closing path, the decision addendum (test: lint)
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-flash (seat headless, factory run sb10)
---
2667a14 docs: board — one START HERE that carries the plan; log, archive and policies move under docs/board; the lint gate checks the shape (test: lint)
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run ev3)
---
```

Two of the eight `docs:` commits are seats — `0443648` (run `sb10`) and
`2667a14` (run `ev3`) — and six are the orchestrator's (`Claude Fable 5.1
(orchestrator)`). The five `evidence:` commits are all seat-task commits. The
survey filters on the `Generated-By:` trailer alone, which is the seat marker;
no subject-prefix filter is applied.

For `0443648`:

```
$ git log -1 --format='%H %P %ci' 0443648
04436484fc320ac256d81112c3f00b2671264400 b9327356572f2c7a71f03279b8105e194fb5b95b 2026-09-08 05:15:53 -0500
$ git show 0443648 -- docs/OPERATIONS.md | grep -E '^[+-]' | grep Queued
-**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** CR4 PW1glm PW1kimi PW1pro SB5b SB6b SD1 SD4 SD5 SD8 (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-06-seat-driver.md)
+**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** CR4 PW1glm PW1kimi PW1pro SB5 SB5b SB6 SB6b SD1 SD4 SD5 SD8 (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-06-seat-driver.md)
$ git show 0443648:docs/ledger/task-status.toml | grep -n 'key =\|status ='
13:# key = "<task key from the heading, e.g. OG1>"
14:# status = "withdrawn" | "parked"
28:key = "SB5"
29:status = "withdrawn"
36:key = "SB6"
37:status = "withdrawn"
```

`0443648`'s parent is `b932735` (the commit that withdrew `SB5` and `SB6`),
three minutes earlier. Its hunk's `+` side adds `SB5` and `SB6` back — the
re-addition, not the suppression — and its own `task-status.toml` already
carries both withdrawal rows. A seat's hook regenerated the block in a
wrong-named workspace (`run sb10`) and the seat's task commit landed it on
`main`. That is the bug, landed, by the exact route the previous round said
never happened.

**The seventeen further non-`docs:` commits the survey disposes of.** There
are 22 non-`docs:` commits touching the board since 2026-09-05: the five
`evidence:` commits above plus seventeen others. None of the seventeen carries
a `Generated-By:` trailer, so none is a seat commit — they are branch merges
and an integrate:

```
$ git log --format='%h %cs %s' --since='2026-09-05' -- docs/OPERATIONS.md | grep -v ' docs:'
fe2d1cf 2026-09-08 Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SD9
401bb01 2026-09-08 evidence: report ladder — … (test: evidence-unit, lint)
143540b 2026-09-08 Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SD4b
c8cdf5e 2026-09-08 Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SD6
639ca88 2026-09-08 Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SD6
4ec8951 2026-09-08 Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SB5b
f8740f5 2026-09-08 merge: main into task/SH5b (board block and MAP regenerated) (test: lint)
5ea0810 2026-09-07 merge: main into task/SH4 (board block and MAP regenerated) (test: lint)
5641111 2026-09-07 merge: main into task/SH3r (board block and MAP regenerated) (test: lint)
ceafbac 2026-09-07 merge: main into task/SH2 (board block and MAP regenerated) (test: lint)
0c004af 2026-09-07 Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/T10a
8875436 2026-09-07 evidence: the reader learns derived and monthly streams, … (test: evidence-unit, lint)
007f326 2026-09-07 merge: main into task/T3b (board block and MAP regenerated) (test: lint)
8e50eca 2026-09-06 merge: main into task/CR2r3b (board block and MAP regenerated) (test: lint)
5fcdb90 2026-09-06 merge: main into task/P2b (board block and MAP regenerated) (test: lint)
0093276 2026-09-06 merge: main into task/P3A (board block and MAP regenerated) (test: lint)
5a246e1 2026-09-06 merge: main into task/SB4b (board block and MAP regenerated) (test: lint)
1940765 2026-09-06 merge: main into task/P1 (board block and MAP regenerated) (test: lint)
d26333f 2026-09-06 evidence: tasks.py check --draft … (test: evidence-unit, lint)
0acc4ff 2026-09-05 integrate G11r into integ/sc7
2cbcc10 2026-09-05 evidence: a task section names the repo … (test: evidence-unit, lint)
0b120bd 2026-09-05 evidence: the board's queue block is generated … (test: evidence-unit, lint)
```

Of the seventeen (the rows above that are neither `evidence:` nor a `docs:`),
ten carry the `(test: …)` subject shape the plan names as the seat marker —
`f8740f5 5ea0810 5641111 ceafbac 007f326 8e50eca 5fcdb90 0093276 5a246e1
1940765`. Per commit, none has a `Generated-By:` trailer:

```
$ for H in fe2d1cf 143540b c8cdf5e 639ca88 4ec8951 f8740f5 5ea0810 5641111 ceafbac 0c004af 007f326 8e50eca 5fcdb90 0093276 5a246e1 1940765 0acc4ff; do s=$(git log -1 --format='%s' "$H"); t=$(git log -1 --format='%B' "$H" | grep -c '^Generated-By:'); echo "$H trailers=$t  $s"; done
fe2d1cf trailers=0  Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SD9
143540b trailers=0  Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SD4b
c8cdf5e trailers=0  Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SD6
639ca88 trailers=0  Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SD6
4ec8951 trailers=0  Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/SB5b
f8740f5 trailers=0  merge: main into task/SH5b (board block and MAP regenerated) (test: lint)
5ea0810 trailers=0  merge: main into task/SH4 (board block and MAP regenerated) (test: lint)
5641111 trailers=0  merge: main into task/SH3r (board block and MAP regenerated) (test: lint)
ceafbac trailers=0  merge: main into task/SH2 (board block and MAP regenerated) (test: lint)
0c004af trailers=0  Merge branch 'main' of /home/dalhaka/nixos-agent-env into task/T10a
007f326 trailers=0  merge: main into task/T3b (board block and MAP regenerated) (test: lint)
8e50eca trailers=0  merge: main into task/CR2r3b (board block and MAP regenerated) (test: lint)
5fcdb90 trailers=0  merge: main into task/P2b (board block and MAP regenerated) (test: lint)
0093276 trailers=0  merge: main into task/P3A (board block and MAP regenerated) (test: lint)
5a246e1 trailers=0  merge: main into task/SB4b (board block and MAP regenerated) (test: lint)
1940765 trailers=0  merge: main into task/P1 (board block and MAP regenerated) (test: lint)
0acc4ff trailers=0  integrate G11r into integ/sc7
```

All seventeen are `trailers=0` — not seat commits.

**The five `evidence:` commits, each hunk as it really is.** These are the
seat-task commits in the window, and each carries a `Generated-By:` trailer
naming a seat:

```
$ for H in 0b120bd 2cbcc10 d26333f 8875436 401bb01; do echo "== $H =="; git show "$H" -- docs/OPERATIONS.md | grep -E '^[+-]' | grep Queued; done
== 0b120bd ==
-**Queued, in order.** 0) backup of the audit records (operator decision
+**Queued (derived from this tree; in-flight state is in the session brief).** B1 FD1 G8c PB0 RT2b (2026-09-05-backup-audit-paths.md 2026-09-05-factory-dispatch.md 2026-09-05-operator-items.md 2026-09-05-seat-routing.md 2026-09-05-session-context.md)
== 2cbcc10 ==
-**Queued (derived from this tree; in-flight state is in the session brief).** B1 G11r H1 OG1r PW1glm PW1kimi PW1pro RT5b SB1 SB2 SB3b (2026-09-05-backup-audit-paths.md 2026-09-05-harness-router.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-05-seat-routing.md 2026-09-05-session-context.md)
+**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** B1 G11r OG1r PW1glm PW1kimi PW1pro RT5b SB1 SB2 SB3b (2026-09-05-backup-audit-paths.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-05-seat-routing.md 2026-09-05-session-context.md)
== d26333f ==
-**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** CR2r2b P1 P11 P12 P4 P6 PW1glm PW1kimi PW1pro SB4 SB4b (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-06-planning-agent.md)
+**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** CR2r2b P11 P12 P2 P3A P4 P6 PW1glm PW1kimi PW1pro SB4 SB4b (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-06-planning-agent.md)
== 8875436 ==
-**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** CR4 PW1glm PW1kimi PW1pro SB5 SB6 SD1 SD4 SD5 SD8 T10a T3M (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-06-seat-driver.md 2026-09-06-telemetry-store-1.md)
+**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** CR4 PW1glm PW1kimi PW1pro SB5 SB6 SD1 SD4 SD5 SD8 T3M (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-05-seat-behind-broker.md 2026-09-06-seat-driver.md 2026-09-06-telemetry-store-1.md)
== 401bb01 ==
-**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** CR4 OG3r PW1glm PW1kimi PW1pro (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-08-house-guard-self-protection.md)
+**Queued (derived from this tree; tasks whose dependencies run in other repos, and in-flight state, are in the session brief).** CR4 OG3r PW1glm PW1kimi PW1pro SD9 (2026-09-05-context-reset-ritual.md 2026-09-05-plan-writing-comparison.md 2026-09-06-seat-driver.md 2026-09-08-house-guard-self-protection.md)
```

Reading each: `0b120bd` *introduced* the generated block, replacing hand-written
prose (the removed line is not a queue-key span; the added line is the first
generated block, keys `B1 FD1 G8c PB0 RT2b`). `2cbcc10` removed `H1` (landed)
and added `OG1r`, plus a wording change. `d26333f` replaced `P1` with `P2 P3A`
(`P1` re-typed/split). `8875436` removed `T10a` (landed). `401bb01` added `SD9`
(newly queued). **None of these five re-adds a key that `task-status.toml` had
withdrawn or parked at that commit.** The wrong block is not here — it is
`0443648`, a `docs:`-subject seat commit the subject-prefix filter (wrongly
applied in the previous round) hid.

The five trailers:

```
$ for H in 0b120bd 2cbcc10 d26333f 8875436 401bb01; do echo "== $H =="; git log -1 --format='%B' "$H" | grep -E '^Generated-By:'; done
== 0b120bd ==
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sc4)
== 2cbcc10 ==
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sc7)
== d26333f ==
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run pa1)
== 8875436 ==
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run tel3)
== 401bb01 ==
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sd9)
```

So the full answer is: **one seat task commit landed a wrong block on `main`**
— `0443648` (run `sb10`), whose hunk re-added `SB5` and `SB6` three minutes
after its own parent `b932735` withdrew them (pasted in full above) — plus the
landing-run merge `4ec8951`, which carried the withdrawn `SB6` forward again 22
minutes later by the same basename path.

## The fix, as options

Where the name should come from: four candidates, each with a file:line and a cost.

**(a) an explicit `--repo-name` (or reuse of the hook's temporary `repos.toml`)
passed by `githooks/pre-commit:69`.** The line `python3 pkgs/evidence/tasks.py
--root . write-board --board docs/OPERATIONS.md --quiet` gains a flag carrying
the fixed name `nixos-agent-env` — exactly what the hook already does for
`check` at `:63` (`printf '[[repo]]\nname = "nixos-agent-env"\npath = "%s"\n'
"$PWD"`). Cost: a new CLI flag on `write-board` and a one-line change to the
hook; the name is still hard-coded in the hook, so a rename of the operator's
checkout breaks it again.

**(b) the workspace's `.factory-meta`.** It does not carry the repo name — only
the base sha and branch:

```
$ ls -la .factory-meta && cat .factory-meta
-rw-r--r-- 1 dalhaka users 67 Sep  9 06:10 .factory-meta
base_sha=a26d232e3ee7b3630476b20e03d40fa2e4d46547
base_branch=main
```

Cost: `.factory-meta` would have to gain a `repo` field and the seat driver be
taught to write it; as it stands it cannot answer the question.

**(c) matching the clone's `git remote` against `docs/ledger/repos.toml`.** The
remote does name the repo:

```
$ git remote -v
origin	/home/dalhaka/factory/base/nixos-agent-env (fetch)
origin	/home/dalhaka/factory/base/nixos-agent-env (push)
```

For a factory workspace the remote's basename is still `nixos-agent-env`, so
matching the remote basename against `repos.toml`'s `name` values would recover
the right key. Cost: the match is by basename, not the path, so it re-encodes
the same basename assumption one level down; and multi-remote clones would need
a disambiguation rule.

**(d) `board_graph` reading `repos.toml`'s name.** This is the source of the
first round's inaccuracy. The in-tree `docs/ledger/repos.toml` holds **seven**
repos, not one:

```
$ cat -n docs/ledger/repos.toml
     1	# Repos the derived task graph reads (plan 2026-09-05-session-context, G3).
     2	# Read-only: nothing here writes to a sibling. `plans` defaults to
     3	# docs/superpowers/plans/*.md. Order = display order in the brief.
     4
     5	[[repo]]
     6	name = "nixos-agent-env"
     7	path = "~/nixos-agent-env"
     8
     9	[[repo]]
    10	name = "media"
    11	path = "~/flakes/media"
    12
    13	[[repo]]
    14	name = "gaming"
    15	path = "~/flakes/gaming"
    16
    17	[[repo]]
    18	name = "nixos-skill"
    19	path = "~/flakes/nixos-skill"
    20
    21	[[repo]]
    22	name = "dsh-harness"
    23	path = "~/flakes/dsh-harness"
    24
    25	[[repo]]
    26	name = "codex"
    27	path = "~/flakes/codex"
    28
    29	[[repo]]
    30	name = "openai-lab"
    31	path = "~/flakes/openai-lab"
```

`board_graph` cannot read "the single name" — there are seven, so the fix must
choose one. The candidates for choosing among seven, each with its cost:

- **An explicit flag on the ledger's home entry** — mark one repo as the home
  repo (a one-line schema change, e.g. `home = true` on the `nixos-agent-env`
  entry), reviewable in a diff. Cost: a schema change plus the reader honouring
  it; unambiguous, no ordering dependency.
- **The first entry** — `repos.toml:5-7` is `nixos-agent-env` first, and the
  file's header (`:3`) says order is display order. Cost: relies on the first
  entry staying the home repo; a reordering silently re-keys the board.
- **Matching the clone's `git remote`** — see (c); the remote basename resolves
  to `nixos-agent-env` even in a factory workspace. Cost: basename matching
  again, multi-remote ambiguity.

Option (a) is the narrowest and does not require `board_graph` to resolve an
ambiguity at all: it threads the one name the hook already knows (the operator
repo) into the one caller that currently lacks it.

## Blast radius of a wrong block

`tools/factory/seat/factory-integrate:79-101` refuses a task commit whose
`docs/OPERATIONS.md` change is outside the queue block:

```
$ sed -n '79,101p' tools/factory/seat/factory-integrate
  # A5 (P11): the board (docs/OPERATIONS.md) is the orchestrator's to write,
  # never a task branch's. A change confined to the `<!-- tasks:begin -->` …
  # `<!-- tasks:end -->` queue block is the hook's own regeneration and is let
  # through; a change anywhere else in that file is refused. Compared against
  # the merge base, never origin's tip (main may have moved the board since the
  # fork, legitimately).
  mb=$(git -C "$base" merge-base "origin/$default_branch" "task/$key" 2>/dev/null || true)
  if [ -z "$mb" ]; then
    # An unrelated-history branch shares no merge base with the default branch;
    # the board guard cannot be run, so refuse rather than merge blind.
    logboth "REFUSED $key: no merge base with origin/$default_branch"
    refused=$((refused + 1))
    continue
  fi
  if ! git -C "$base" diff --quiet "$mb" "task/$key" -- docs/OPERATIONS.md; then
    mb_ops=$(git -C "$base" show "$mb:docs/OPERATIONS.md" 2>/dev/null | awk '/<!-- tasks:begin -->/{s=1} !s{print} /<!-- tasks:end -->/{s=0}')
    key_ops=$(git -C "$base" show "task/$key:docs/OPERATIONS.md" 2>/dev/null | awk '/<!-- tasks:begin -->/{s=1} !s{print} /<!-- tasks:end -->/{s=0}')
    if ! cmp -s <(printf '%s\n' "$mb_ops") <(printf '%s\n' "$key_ops"); then
      logboth "REFUSED $key: docs/OPERATIONS.md changed outside the queue block"
      refused=$((refused + 1))
      continue
    fi
  fi
```

A wrongly regenerated block that stays *inside* the `<!-- tasks:begin --> /
<!-- tasks:end -->` markers passes this guard. The guard's own logic, on a
fixture:

```
$ A=$(awk '/<!-- tasks:begin -->/{s=1} !s{print} /<!-- tasks:end -->/{s=0}' a.txt)   # block: "A B C"
$ B=$(awk '/<!-- tasks:begin -->/{s=1} !s{print} /<!-- tasks:end -->/{s=0}' b.txt)   # block: "A B C WITHDRAWN_KEY"
$ printf 'A=[%s]\nB=[%s]\n' "$A" "$B"
A=[rest]
B=[rest]
$ cmp -s <(printf '%s\n' "$A") <(printf '%s\n' "$B") && echo "GUARD: identical -> a wrong block inside the markers PASSES"
GUARD: identical -> a wrong block inside the markers PASSES
```

The `awk` strips the markers and everything between them from both sides, so the
`cmp` never sees the block's content. A wrong block is invisible to the guard.

## What a fix must not break

- `brief`, `json` and `waves` read `docs/ledger/repos.toml`'s literal name, not
  the basename, and must keep doing so: they are correct today and the fix is
  scoped to `board_graph`'s name source, not to how the other commands read the
  ledger. `load_repos` is the one reader, and it copies `r["name"]` verbatim:

  ```
  $ grep -n 'load_repos\|def load_repos' pkgs/evidence/tasks.py
  424:def load_repos(path):
  1125:    repos = load_repos(repos_path)
  2214:    repos = load_repos(repos_path)
  2223:        for r in load_repos(os.path.join(args.root, "docs", "ledger", "repos.toml"))
  $ sed -n '424,436p' pkgs/evidence/tasks.py
  def load_repos(path):
      if not pathlib.Path(path).exists():
          return []
      with open(path, "rb") as fh:
          data = tomllib.load(fh)
      return [
          {
              "name": r["name"],
              "path": os.path.expanduser(r["path"]),
              "plans": r.get("plans", PLANS_GLOB),
          }
          for r in data.get("repo", [])
      ]
  ```

- `check --board` must keep deriving the block identically to `write-board`,
  anywhere — `board_graph`'s docstring is load-bearing there; whatever override
  the fix threads must reach both `:2304` and `:2344`, or the two halves of the
  gate will disagree.
- The hook's `repos.toml` temporary-file workaround for `check` (`:62-65`) must
  remain, or be folded into the same override — the fix must not regress the one
  correct path.
- Two in-tree tests pin `board_graph`'s current basename naming, and a fix that
  re-sources the name must update both rather than blind the assertions:

  ```
  $ grep -n 'def test_board_graph' tests/evidence/test_tasks.py
  1656:def test_board_graph_derives_this_tree_ignoring_repos_toml(tmp_path, monkeypatch):
  1790:def test_board_graph_excludes_cross_repo_task(tmp_path, monkeypatch):
  1811:def test_board_graph_defers_cross_repo_dependent(tmp_path, monkeypatch):
  2225:def test_board_graph_exposes_task_status_and_omits_withdrawn(tmp_path, monkeypatch):
  ```

  `:1656` (`test_board_graph_derives_this_tree_ignoring_repos_toml`) asserts a
  `repos.toml` naming `elsewhere` "must not change the block" — the exact
  assumption option (d) inverts. `:2225`
  (`test_board_graph_exposes_task_status_and_omits_withdrawn`) is the
  withdrawn-overlay test, and it passes today only because its fixture
  directory is named `root` and its `task-status.toml` row says
  `repo = "root"` — i.e. it is the fixture whose basename/ledger mismatch the
  fix's discriminating row has to introduce.

## What it would take to be complete

A change to `pkgs/evidence/tasks.py` that makes `board_graph` name the repo from
a source other than the basename (one of the options above), reaching both call
sites, plus the corresponding `githooks/pre-commit` change if option (a); a
fitting that shows the withdrawn overlay applying in a wrong-named tree; and a
re-run of the whole `lint` gate. This gather stops at measuring the defect and
its options; it changes no behaviour.

## Hook gate (Step 3)

The full lint gate, run once, exits 0 on the first run, so no pathspec route
is needed:

```
$ nix develop -c githooks/pre-commit; echo "hook_exit=$?"
All checks passed!
108 files already formatted
js-lint: workflow-script formatter arm A
js-lint: workflow-script linter arm A
…
render.test.mjs: all assertions passed
hook_exit=0
```

(The `…` elides the treefmt/prettier/shellcheck progress lines; the last
measured line before the exit is `render.test.mjs: all assertions passed`, and
the gate's own `evaluation warning: nixfmt-rfc-style is now the same as
pkgs.nixfmt which should be used instead.` stderr line, seen on the `write-board`
invocations above, also appears here.)

## UNMEASURED

- The seat driver's exact mechanism for naming a workspace (`--workspace`,
  `.factory-meta`) beyond what `git remote -v` and `.factory-meta` show above —
  measured here only to the extent the options require.
- Whether a rename of the operator's checkout is even permitted — outside this
  stage's scope.