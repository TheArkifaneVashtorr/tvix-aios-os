Two forms, both run at planning time. **P1's form** (`check --draft` over the live tree with a one-repo `--repos` file, because this environment's `HOME` is not the operator's and `repos.toml`'s `~` would resolve elsewhere — the lint check's own form):

```
$ printf '[[repo]]\nname = "nixos-agent-env"\npath = "%s"\n' "$PWD" > /tmp/draft-scratch/repos.toml
$ nix develop -c python3 pkgs/evidence/tasks.py --root . --repos /tmp/draft-scratch/repos.toml --runs-dir /nonexistent --store /nonexistent check --draft /tmp/draft-scratch/draft-0.md
waves: [[["SD1"], ["SD2"], ["SD3"], ["SD5"]], [["SD4"], ["SD6"], ["SD7"]], [["SD10"], ["SD8"]]]
conflicts: … 59 rows, listed below by sibling plan …
exit=0
```

**The scratch-copy form** (Step 3 of the design: `cp -a` the tree to `/tmp/draft-scratch/tree`, the draft placed at `docs/superpowers/plans/2026-09-06-seat-driver.md`, a one-repo file naming the copy):

```
$ nix develop -c python3 pkgs/evidence/tasks.py --root /tmp/draft-scratch/tree --repos /tmp/draft-scratch/repos-tree.toml --runs-dir /nonexistent --store /nonexistent check; echo exit=$?
exit=0
$ … waves --repo nixos-agent-env --plan 2026-09-06-seat-driver.md --json
[[["SD1"], ["SD2"], ["SD3"], ["SD5"]], [["SD4"], ["SD6"], ["SD7"]], [["SD8"]]]
$ … waves --repo nixos-agent-env --plan 2026-09-06-seat-driver.md --next
"SD1" "SD2" "SD3" "SD5"
$ … conflicts | grep -c seat-driver.md
59
```

(SD10 appears in the first form's wave 3 and not in the second: `load_draft` adds every draft task to the scanned repo, while the scan of a committed plan attributes SD10 to `dsh-harness` — where it belongs and where its wave is computed live. SD9 is in neither: its `dependsOn` T10a is not landed, and an unlanded dependency outside the plan never schedules.)

| wave | tasks | dependsOn | notes |
|---|---|---|---|
| 1 | SD1 ‖ SD2 ‖ SD3 ‖ SD5 | — | four seats; `touches` pairwise disjoint (routing/driver-lib · evidence · guard · seat module) |
| 2 | SD4 ‖ SD6 ‖ SD7 | SD4: [SD3]; SD6: [SD1, SD5]; SD7: [SD1, SD2, SD5] | three seats; SD6 (pkgs/seat, tests/seat, seat-vm) and SD7 (the driver scripts, 80-bats, README) are disjoint after the README moved to SD7 |
| 3 | SD8 ‖ SD10 | SD8: [SD7]; SD10: [SD7] (repo `dsh-harness`) | SD10 runs as a seat over `~/flakes/dsh-harness` with this plan named |
| 4 | SD9 | [SD8, T10a] | dispatched by the telemetry plan's landing of T10a; blocked until then |

**The cross-plan hits, sequenced** (every row of `conflicts` names one of these plans):

- **`2026-09-04-loose-ends-wave-a7.md` (N13–N18)** × SD1, SD4, SD5, SD6, SD7, SD8 on `tools/factory/seat/` (N17's directory-prefix `touches`), `flake.nix`, `docs/runbooks/lanes.md`, `pkgs/dsh-openrouter/*`, `tests/unit/70-…`, `80-…`: these six read `ready` only because this snapshot's single commit carries none of their subjects; the board log records the wave landed on 2026-09-04 (`grep -n 'loose-end wave a7' docs/board/log-2026-09.md` → "READY TO SWITCH #12 … loose-end wave a7 … all Opus-gated … Landed: N13 …"). On the live tree these rows vanish; no order to impose.
- **`2026-09-06-telemetry-store-1.md` (T1, T1W, T2, T3, T10a)** — the real overlaps: T1 × SD1/SD7/SD8 on `factory-lib.sh` (T1 edits `factory_record_check`'s `--store` clause; this plan adds functions — a textual merge), T1 × SD2 on `tasks.py` (T1 changes the `--store` default literal), T1/T1W × SD5 on `flake.nix` (different check blocks), T2 × SD1/SD7/SD8 on `factory-lib.sh`, `factory-task`, `80-seat-driver.bats` (T2 writes `error_class:`/`plan:` into the same `.result` block SD7 extends with `rung:`/`class:` and SD8 with `prior:`), T3 × SD2 on `tasks.py`/`test_tasks.py`, T1/T2/T10a × SD9 (by design: SD9 edits T1's and T2's files and waits for T10a). Rule: T1 is in gate now; wave 1 here may run beside `tel2`; **whichever of two overlapping tasks lands second merges main into its branch first (Dispatch recipe step 2) and re-runs the shared test file before its gate**; SD9 waits by `dependsOn`.
- **`2026-09-05-seat-behind-broker.md` (SB5, SB6 — HELD by the operator 2026-09-06 08:55)** × SD1 (`claims.toml`), SD4 (`dsh-openrouter.sh`, `default.nix`, `70-…bats`, `lanes.md`), SD5/SD6 (`seatLane.nix`, `seat-vm.nix`, `seat-submit.py`): nothing here waits for a held task; when the hold lifts, SB6's seat merges main first (its fix concerns `--bind-namespace`/`--port` validation and `seat-submit`'s unit watch, both compatible with `--spool` and `drive`). SB5's runbook `docs/runbooks/seat.md` does not exist yet, so this plan writes no seat runbook (the Operator section carries the commands until SB5).
- **`2026-09-05-context-reset-ritual.md` (CR4)** × SD3 on `docs/runbooks/session.md`: CR4 is dispatchable live (its chain landed); both append a paragraph — recipe step 2 for the second lander.
- Same-plan overlaps are the waves' own: none inside a wave after the SD6/SD7 split (`waves --json` shows singleton groups only).
