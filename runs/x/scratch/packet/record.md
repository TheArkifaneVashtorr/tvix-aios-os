# Packet record — spec 2026-09-06-operator-seat-driver-design

## 1. Paths the spec names

- `nixosModules/seatLane.nix`
- `pkgs/seat/seat-submit.py`
- `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md`
- `docs/ledger/routing.toml`
- `tools/factory/seat` (`factory-dispatch`, `factory-task`, `factory-integrate`, `factory-plan`, `factory_route`)
- `.claude/workflows/plan.js`
- `docs/ledger/plan-defects.toml`
- `docs/MAP.md`
- `tests/unit/91-orchestrator-guard.bats`
- `pkgs/dsh-openrouter/hook-guard.py`
- `docs/ledger/task-classes.toml` (new — no reviews touch it yet)
- `~/flakes/dsh-harness/README.md` (external repo, not in this tree)

## 2. Rejected-review gate history per path

### `nixosModules/seatLane.nix`
Reviews found (grep): sb3-SB1 (APPROVED), sb5-SB2b (**REJECTED**), sb6-SB2r (APPROVED), sb8-SB4b (APPROVED).

- **run sb5, key SB2b** — class `missing-case` (per `plan-defects.toml`, row `sb5/SB2b`). Sentence missing: contract item (3) required `--bind-namespace` to accept "only a dotted IPv4 address," but the plan never asked for octet-range validation, only dotted-quad shape — so `--bind-namespace 256.1.1.1` is accepted and reaches the real exec argv.

### `pkgs/seat/seat-submit.py`
Reviews found: sb1-SB3 (**REJECTED**), sb8-SB4b (APPROVED).

- **run sb1, key SB3** — class `underspecified` (ledger row `sb1/SB3`). Sentence missing: the plan never asked for a `systemctl stop` on the timeout path, so the new `seat-submit` leaves `seat@<id>` running past expiry instead of killing it the way the old `timeout -- "$timeout_s" dsh-openrouter` path did.

### `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md`
Reviews found: a7-N13-N15-N17 (chain header only, no plain verdict on this file's top line — not counted as a rejection here; skip per read-only/no-transcript rule, no plan-defect row cites it).

### `docs/ledger/routing.toml`
Reviews found: fd2-FD1b (APPROVED), hr1-H2 (**REJECTED**), hr1-H2b (APPROVED), rt1-RT1 (**REJECTED**), rt1-RT1b (APPROVED), rt2c-RT2 (**REJECTED**), rt2c-RT2b (APPROVED), rt4-RT4 (APPROVED), rt5-RT5 (**REJECTED**), rt5-RT5b (**REJECTED**), rt7-RT5r (**REJECTED**), rt8-RT5rb (APPROVED), sb3-SB1 (APPROVED), pa11-P13 (APPROVED, plan_defect: none), pa6-P2 (**REJECTED**), pa9-P8 (**REJECTED**), pb2-P2b (APPROVED), pb8-P8b (APPROVED, plan_defect: wrong-fact but "No MAJORs").

- **run hr1, key H2** — class `wrong-fact` (ledger row `hr1/H2`). Sentence missing: the plan asserted `FACTORY_ROUTING_TABLE` as a real override variable, but it is a phantom — the table path actually follows `FACTORY_TOOLBOX_REPO` plus a fourth positional argument, and the plan's `size`-escalation bullets describe `size`/`kind` as a dial when they are fixed off the task heading.
- **run rt1, key RT1** — class `vacuous` (ledger row `rt1/RT1`). Sentence missing: the plan required `--model` to win over `OPENROUTER_MODEL` and the route, but no assertion made the route clobbering an explicit `--model` fail — mutation M5 survived.
- **run rt2c, key RT2** — class `vacuous` (ledger row `rt2c/RT2`). Sentence missing: the plan's cross-check between `factory_route` and `route.py lookup` needed a fixture with a genuinely discriminating tie (two claude rows at the same specificity with *different* models), and a bad-table fixture missing `effort` to prove the missing-key validation isn't dead code — neither existed, so mutations M4a and M10 survived.
- **run rt5, key RT5** — class `missing-case` (ledger row `rt5/RT5`). Sentence missing: the nested-seat rule in `hook-guard.py` is bypassed by quoting or a line continuation, and the plan named no assertion that would catch a quoted/continued command reaching the model.
- **run rt5, key RT5b** — class `underspecified` (ledger row `rt5/RT5b`). Sentence missing: the plan treated the structured `subagent`/`workflow` half as the real gate ("the table is applied by the OS, not followed by prose") without a disclaimer, but the payload is the model's own arguments object and nothing stops a hostile shape there.
- **run rt7, key RT5r** — same bypass class as RT5b, relocated: the `try/except BaseException` in `hook-guard.py` starts *after* `json.load(sys.stdin)`, so a ~52,000-level-deep JSON payload (~312 KB) still gets through; the re-plan's fix moved the guard one line too late and the plan didn't require an assertion at the parse boundary itself.
- **run pa6, key P2** — class `missing-case`, secondary `implementer` (ledger row `pa6/P2`). Sentence missing: the packet's default interpreter path (`factory_python3` = `nix develop -c python3`) mixes flake-warning stderr into byte counts and status lines on a dirty tree, and the plan never asked for a case isolating stderr from the counted/graph bytes.
- **run pa9, key P8** — class `missing-case`, secondary `wrong-fact` (ledger row `pa9/P8`). Sentence missing: the branch's own assertion that `seat-plan.md` carries no typed task heading does not run inside the `unit` check that `factory-integrate` re-runs by ref, because `tools/factory/plan/` was never added to `checks.unit`'s copy list — the plan never named that copy-list touch.

### `tools/factory/seat`
Large set of reviews (a10-N21-A10T3, cr6/cr8/cr9/cr12/cr14/cr15/cr16/cr17, ev1-R5/R5b/R7, ev2-E7/E7b/E7r, ev3-R10, fd1-FD1/fd2-FD1b, hr1-H2/H2b, mcf2-P1flash/P1flashb, mcp-P1pro, mcp2-P0, rt1/rt2c/rt4, sb1-SB3/sb2-SB3b, pa3-P11/pa5-P6/pa6-P2/pa8-P5/pa9-P8/pa11-P13, pb2-P2b/pb6-P6b/pb8-P8b/pb11-P11b/pb11r-P11r). Rejections already itemised above (hr1/H2, rt1/RT1, rt2c/RT2, sb1/SB3, pa6/P2, pa9/P8) plus, from the plan-defect ledger directly:
- **run cr6, key CR3** — class `underspecified` (ledger row `cr6/CR3`).
- **run cr8, key CR2** — class `missing-case` (ledger row `cr8/CR2`).
- **run cr9, key CR3b** — no ledger row found (approved or superseded; not confirmed from ledger).
- **run cr15, key CR2r** — class `missing-case`, secondary `implementer` (ledger row `cr15/CR2r`).
- **run cr17, key CR2rb** — class `missing-case` (ledger row `cr17/CR2rb`).
- **run ev1, key R5** — class `missing-case`, secondary `wrong-fact` (ledger row `ev1/R5`).
- **run fd1, key FD1** — class `wrong-fact` (ledger row `fd1/FD1`).
- **run pa3, key P11** — class `missing-case` (ledger row `pa3/P11`).
- **run pa5, key P6** — class `missing-case` (ledger row `pa5/P6`).
- **run pa8, key P5** — class `wrong-fact`, secondary `underspecified` (front matter of `pa8-P5.md`; not yet in the seed ledger). Sentence missing: §P5's assertion (12) claims the 14 row names of `tools/factory/plan/rubric.md`'s table, in order, equal `CRITERIA`, but two of the fourteen do not and cannot, since both sides are pinned verbatim to the design.
- **run pb11, key P11b** — class `implementer` (ledger row `pb11/P11b`).

### `.claude/workflows/plan.js`
Reviews found: pa2-P12 (APPROVED), pa8-P5 (**REJECTED**, see above), pb3ar3-P3Ar3 (**REJECTED**, front matter `wrong-fact`).

- **run pb3ar3, key P3Ar3** — class `wrong-fact` (front matter). Sentence missing: plan §P3Ar3 Step 1 claimed "the sandbox-pin test (red: the file differs, since main copies the live ledger)," but main's `flake.nix` copies the live ledger *and* exports nothing, so the branch's own skip condition disarms the test on main — the plan asserted a red state that the tree does not produce.

### `tests/unit/91-orchestrator-guard.bats`
Reviews found: cr8-CR2 (**REJECTED**, above), cr12-CR2b, cr15-CR2r (**REJECTED**, above), cr17-CR2rb (**REJECTED**, above), og1-OG1 (**REJECTED**, ledger `missing-case`), og1-OG1b (**REJECTED**, ledger `underspecified`), og3-OG1r (**REJECTED**, ledger `underspecified`), og4-OG1r2 (**REJECTED**, ledger `missing-case`), og5-OG1r2b, cr18-CR2r2 (**REJECTED**, ledger `missing-case`/`implementer`), cr19-CR2r2b (**REJECTED**, ledger `implementer`), cr20-CR2r3 (**REJECTED**, ledger `underspecified`/`missing-case`), cr21-CR2r3b.
(Sentences for og1/og3/og4/cr18-21 not re-derived here beyond their ledger class, per the read-only budget — the ledger row is the citable fact for each.)

### `docs/MAP.md`
Touched by a very large fraction of the review set (regenerated-doc dependency of nearly every task); not analysed row-by-row here since the spec's design section never names `docs/MAP.md` as a file this design writes — it is cited only as "acceptance from `docs/MAP.md` check names" (task typing, reused). No further rows pulled.

### `docs/ledger/task-classes.toml`
No reviews grep-match this path — it does not exist yet in the tree (this spec's §5 proposes creating it).

## 3. Appendix A — the eight questions (verbatim), from `docs/superpowers/specs/2026-09-05-planning-agent-design.md`

> ## Appendix A — the eight questions every section answers before it ships
>
> Derived from the 42 plan-caused rejections; the number in brackets is how many
> of them the question would have caught (Appendix B's classes).
>
> 1. For every assertion: which one-line change turns it red? [14]
> 2. For every fixture: which row makes the assertion discriminate — a second
>    gap whose id sorts against its date, a flapping run, one payload per rule,
>    every enum arm, the default branch rather than the injectable one? [the
>    mechanical cause behind most of the 14]
> 3. For every boundary: is it a rule (tokenise; any token; every ancestor;
>    every producer; validate as an address, not a shape), never a list of
>    spellings? [14]
> 4. For every interface: which tree or file does it read, what does it emit on
>    each internal failure (exit code, stdout), and who consumes each field? [8]
> 5. For every fact: which command produced it, pasted beside it, with the
>    anchor text rather than a line number? [6, plus the G12r copy error]
> 6. Does any step's mandated output fail the task's own acceptance grep? [1]
> 7. For a fix round or re-plan: does the section carry every item of the
>    rejection, and does every deleted test name its replacement? [2]
> 8. Does the section carry everything the seat will see — is `factory-brief
>    <plan> <KEY>` the whole contract? [the G5 amendments and R10's touches gap]

## 4. Rules of record

### The three amendments — `docs/decisions/2026-09-03-test-based-reality-amendments.md`

1. **Falsifiable, not merely tested.** A load-bearing test counts only once it has been shown to fail: red before the change (TDD), and at review a mutation or refutation that turns it red again. "Has a test" is not evidence; "the test failed when it should" is. Reviewers report a test that cannot fail as a finding of class `vacuous-test` (major).
2. **Unmeasured is debt, not nonexistence.** A claim we cannot yet measure — an absence, a structural property, a judgement — is recorded as dated debt with an owner on the board, acted on when the reasoning is strong, and closed when a measurement exists. It is never treated as false, and never used as a reason to skip the reasoning.
3. **Proxies are declared.** Every measurement that stands in for the real goal names what it stands in for and the known gap. A proxy is reported as a proxy.

### Rule A1 (from this spec, citing planning design §3 and anticipation row A12)

One bounded fix round `<KEY>b`, then a re-plan `<KEY>r`; the fix round's section carries every rejection item. The seat sees only Global Constraints, Assumptions and its own section.

### Parallel-workflows ordering — `docs/decisions/2026-09-04-parallel-agent-workflows.md`

Order of authority, deterministic first, judgement last:

1. **A deterministic dependency scheduler** — the task graph is validated on entry (duplicate keys, unknown/dangling `dependsOn`, cycles, unknown `kind`/`role`, empty `spec`); the run refuses before any agent is spawned if malformed; waves come from Kahn's algorithm under an explicit concurrency cap; a task whose dependency did not finish green is `blocked` and never run.
2. **Persistent isolated workspaces per task** — a full `git clone --local` per task under a declared factory root outside every git repo (`~/factory`), one workspace per task key, created at wave start, listed in the return value; integration is deterministic (one branch per task key, merged `--no-ff` in topological order, checks plus lint re-run on the merged tree, exactly one bounded fix task on conflict/red).
3. **An LLM judge, bounded and visible** — consulted only for tasks with no `touches` annotation; overlap inside a wave is otherwise decided by a deterministic prefix check over `touches`; the judge's answer is recorded in the schedule output, is disabled by `args.judge = false` (un-annotated tasks then serialise), and never overrides an explicit `touches`.
