import pathlib, re
p = pathlib.Path("/tmp/draft-scratch/draft-0.md")
t = p.read_text()

waves = r'''Peel-off groups from the graph's own code over the draft attached to this tree — P1's form (`check --draft`); every draft rule passed (acceptance names against `docs/MAP.md`, explicit `touches`, the four house sections, the byte-exact subjects against `acceptance`, sizes, one section per key):

```
$ python3 pkgs/evidence/tasks.py --root /home/user/tvix-aios-os --runs-dir /nonexistent --store /nonexistent check --draft /tmp/draft-scratch/draft-0.md
waves: [[["SD1"], ["SD2"], ["SD4", "SD6"]], [["SD3"], ["SD5"], ["SD7"]], [["SD10"], ["SD9"]]]
conflicts: … 51 rows (the table below sequences every one) …
exit=0
```

`SD8` is absent from the printed waves because its dependencies T2 and T10a are not `landed` in this tree (Assumption 1); it is the fourth wave on core, after the telemetry plan's `tel3`.

| wave | tasks | dependsOn | notes |
|---|---|---|---|
| 1 | SD1 ‖ SD2 ‖ (SD4 → SD6) | none | four seats; SD4 and SD6 both edit `flake.nix` (`seat-unit`'s copy line; `lint`'s `--check-rules` line), so the graph chains them in one workspace in key order; the other touches are disjoint |
| 2 | SD3 ‖ SD5 ‖ SD7 | SD3: [SD1, SD2]; SD5: [SD4]; SD7: [SD6] | three seats; disjoint (`tools/factory/seat` + `80-seat-driver.bats` / `pkgs/seat` + `nixosModules/seatLane.nix` + `flake.nix` + `seat-vm.nix` / `pkgs/dsh-openrouter` + `70-dsh-openrouter.bats` + `tests/lane`) |
| 3 | SD10 ‖ SD9 | SD10: [SD3, SD5]; SD9: [SD3] | SD9 runs in `~/flakes/dsh-harness` (a Flash docs seat by the table's `implement/docs/any` row); SD10 a docs seat here |
| 4 | SD8 | [SD3, T2, T10a] | after the telemetry plan's wave 3 (`tel3`) lands |

**The cross-plan hits, sequenced** (`check --draft`'s `conflicts:` lines; every row has one of four causes):

- **Snapshot artefacts** (Assumption 1): `N13`, `N14`, `N15`, `N17`, `N18` of `2026-09-04-loose-ends-wave-a7.md` read `ready` here because nothing derives `landed` in a one-commit history; on core that wave landed on 2026-09-04 (board: "loose-end wave a7 … all Opus-gated"). No order to impose.
- **The telemetry plan (in flight):** `T1` × SD1/SD3 (`factory-lib.sh`), × SD2 (`tasks.py`), × SD4/SD5/SD6 (`flake.nix`), × SD8 (`streams.py`, `report.py`, `SCHEMA.md`, `test_streams_policy.py`); `T1W` × SD4/SD5/SD6 (`flake.nix`, `githooks/pre-commit`); `T2` × SD1/SD3 (`factory-lib.sh`, `factory-task`, `80-seat-driver.bats`), × SD8 (`ingest_result.py`, its test); `T3` × SD2 (`tasks.py`, `test_tasks.py`); `T10a` × SD8 (`SCHEMA.md`). Order: wave 1 launches after `T1` has fast-forwarded (Operator step 1); SD8 depends on T2/T10a by `dependsOn`; for every other pair the second to land merges `main` into its task branch at integration (recipe step 2 — the integrator's step, never the seat's) — the edits are additive lines in different functions and blocks.
- **Held siblings:** `SB5` × SD1 (`docs/ledger/claims.toml` — both append rows); `SB6` × SD4 (`seat-submit.py`), × SD5 (`seatLane.nix`, `seat-vm.nix`), × SD7 (`dsh-openrouter.sh`, `70-dsh-openrouter.bats`). SB5/SB6 are HELD by the operator (board, 2026-09-06 08:55); this plan lands first; when the hold lifts, SB5/SB6 merge `main` first (recipe step 2). SB6's contract items 1–5 (a validated `--port`, the forwarder lifecycle, the unit `Result` watch) do not overlap SD4/SD5's changes in meaning — the `--port` integer check SD4 adds for `drive` is SB6's item 1 for `--bind-namespace`; both can stand.
- **Dispatchable sibling:** `CR4` × SD6 (`githooks/pre-commit` — CR4 is on the board's queue; both add lines): whichever lands second merges `main` first.
- In `dsh-harness`: `P13` (blocked on P8 here; landed on core as 81c5925) shares `CHANGELOG.md` with SD9 — one dated line each; the integrator's merge.'''

dispatch = r'''Runs: `sd1` (wave 1), `sd2` (wave 2), `sd3` (wave 3: SD10 here), `sd4` (SD9 in `~/flakes/dsh-harness`, hand-launched — the dispatcher's graph query needs the repo's own `repos.toml`), `sd5` (SD8). None exists under `~/factory/runs` on this tree (no `~/factory` here; on core check `ls ~/factory/runs | grep -c '^sd'` → expected `0`). Plan path after the Ship phase: `docs/superpowers/plans/2026-09-06-seat-driver.md`.

Dry run over the draft (not yet under the plans directory, so the dispatcher's graph query is supplied through its own `FACTORY_WAVES_CMD` seam by `/tmp/draft-scratch/parts/waves-next.sh`, which calls `tasks.scan_repo`, `tasks.load_draft` and `tasks.wave_lines` — the graph's own functions, no logic re-derived — and prints the draft's next wave exactly as `waves --next` would; `FACTORY_ROOT` pointed at an empty path to prove nothing is written):

```
$ DRAFT=/tmp/draft-scratch/draft-0.md ROOT=/home/user/tvix-aios-os /tmp/draft-scratch/parts/waves-next.sh
"SD1" "SD2" "SD4 SD6"
$ FACTORY_WAVES_CMD=/tmp/draft-scratch/parts/waves-next.sh FACTORY_ROOT=/tmp/draft-scratch/factory-root tools/factory/seat/factory-dispatch sd1 /home/user/tvix-aios-os /tmp/draft-scratch/draft-0.md --dry-run
would run: factory-wave sd1 /home/user/tvix-aios-os "SD1" "SD2" "SD4 SD6"
exit=0
$ ls /tmp/draft-scratch/factory-root
ls: cannot access '/tmp/draft-scratch/factory-root': No such file or directory
```

Per wave, the command to run on core (after the plan file exists on main; the repo path is core's):

```
tools/factory/seat/factory-dispatch sd1 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md --dry-run
tools/factory/seat/factory-dispatch sd1 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md      # prints "SD1" "SD2" "SD4 SD6"; in the background (setsid -f … </dev/null)
tools/factory/seat/factory-dispatch sd2 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md      # after wave 1 landed; prints "SD3" "SD5" "SD7"
tools/factory/seat/factory-dispatch sd3 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md      # after SD3 and SD5 landed; prints "SD10" (SD9 is the harness repo's: below)
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-06-seat-driver.md tools/factory/seat/factory-wave sd4 /home/dalhaka/flakes/dsh-harness "SD9"   # after SD3 landed
tools/factory/seat/factory-dispatch sd5 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md      # after T2 and T10a landed; prints "SD8"
```

Every launch goes in the background (`setsid -f bash -c 'exec <line> >> ~/factory/runs/<run>.wave.log 2>&1' </dev/null`): a foreground call is killed by the tool timeout (tel1, 2026-09-06 10:40).

**Landing recipe, per key (A1), in order:**

1. Keep only the one commit the section names: `git -C ~/factory/ws/<run>/<KEY> log --format='%h %s' <base>..task/<KEY>` (base from `~/factory/ws/<run>/<KEY>/.factory-meta`); if more than one line, `git -C ~/factory/ws/<run>/<KEY> reset --hard <that sha>`.
2. If main moved under a file the task touches (or under `docs/MAP.md`): `git -C ~/factory/ws/<run>/<KEY> fetch ~/nixos-agent-env main && git -C ~/factory/ws/<run>/<KEY> merge --no-edit FETCH_HEAD`, then `python3 pkgs/evidence/repomap.py --root . write` in the workspace and a merge commit `merge: main into task/<KEY> (board block and MAP regenerated) (test: lint)` — the orchestrator's step, never the seat's.
3. Commit the gate review (`docs: gate review — <run> <KEY> …`) with the front-matter block.
4. `tools/factory/seat/factory-integrate <run> ~/nixos-agent-env <KEY> && git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>` — gated on both exit codes; never pull after a `CHECK … fail` line.
5. Dispatch what it unblocks (A7): SD1 + SD2 → SD3; SD4 → SD5; SD6 → SD7; SD3 → SD9 (harness) and, with SD5, SD10; SD3 + T2 + T10a → SD8. Switch #21 after SD5 (Operator step 2).

**Relaunch after a seat death (A6):** the dead seat's diff stays in `~/factory/ws/<run>/<KEY>`; relaunch the one key as `FACTORY_PLAN=docs/superpowers/plans/2026-09-06-seat-driver.md setsid -f bash -c 'exec tools/factory/seat/factory-wave <run>b ~/nixos-agent-env "<KEY>" >> ~/factory/runs/<run>b.wave.log 2>&1' </dev/null`, after the `error_class` of the dead result is read (T2's line; until it lands, the `.result`'s notes): `budget-402` waits for the top-up, `provider-error` and `boot-failure` relaunch once — after SD3 lands, with `OPENROUTER_MODEL` unset and `factory-task --fallback` through a one-key wave when the row carries one; `unknown-model`/`template-echo`/`no-result-line` never relaunch blind.'''

old_w = "_(filled after the draft check)_"
old_d = "_(filled after the dry run)_"
assert old_w in t and old_d in t
t = t.replace(old_w, waves).replace(old_d, dispatch)

# SD3: the fenced block's heading line must not sit at column 0 (factory-brief's awk ends a section at /^## /).
old_block = "```\n## Prior attempt (<prun>/<pkey>)\n\n- result:"
assert old_block in t, "block anchor"
t = t.replace(old_block, "```\n    ## Prior attempt (<prun>/<pkey>)\n\n- result:")
old_tail = "verbatim>\n```\n\n  The review file:"
assert old_tail in t, "tail anchor"
t = t.replace(old_tail, "verbatim>\n```\n\n  (The block's first line starts at column 0 in the brief; it is indented here only so this plan's own section extractor — `factory-brief`, which ends a section at the next line beginning `## ` — reads the whole section.) The review file:")

# A9 row: name CR4 and T3 too
old_a9 = "wave 1 waits for T1's fast-forward (Operator step 1) — three of its four tasks share files with T1/T2 (`factory-lib.sh`, `tasks.py`, `flake.nix`);"
assert old_a9 in t
t = t.replace(old_a9, "wave 1 waits for T1's fast-forward (Operator step 1) — three of its four tasks share files with T1/T2/T3 (`factory-lib.sh`, `tasks.py`, `flake.nix`) and SD6 shares `githooks/pre-commit` with CR4 and T1W;")
p.write_text(t)
print("filled;", len(t.split()), "words")
