Runs: `sd1` (wave 1), `sd2` (wave 2), `sd3` (wave 3, this repo), `sd3h` (SD10 in `~/flakes/dsh-harness`), `sd4` (SD9, after T10a). None exists here (`ls -d ~/factory/runs` → No such file in this environment; on core: `ls ~/factory/runs | grep -c '^sd'` must print `0` before the launch). Plan path after the Ship phase: `docs/superpowers/plans/2026-09-06-seat-driver.md`.

**Dry run over the draft** (the draft is not under the plans directory yet, so the dispatcher's graph query is supplied through its own `FACTORY_WAVES_CMD` seam with the line `tasks.py waves --next` printed for the scratch copy above — no graph logic re-derived; `--repo-name` because this environment's `HOME` is not the operator's):

```
$ cat /tmp/draft-scratch/waves-next.sh
#!/usr/bin/env bash
printf %s\\n '"SD1" "SD2" "SD3" "SD5"'
$ FACTORY_ROOT=/tmp/draft-scratch/factory-root FACTORY_WAVES_CMD=/tmp/draft-scratch/waves-next.sh tools/factory/seat/factory-dispatch sd1 . /tmp/draft-scratch/draft-0.md --dry-run --repo-name nixos-agent-env
would run: factory-wave sd1 /home/user/tvix-aios-os "SD1" "SD2" "SD3" "SD5"
exit=0
$ find /tmp/draft-scratch/factory-root | wc -l
1
```

(A dry run touched nothing: the factory root holds only itself.)

**Per wave, the command to run** (after the plan file is on main; the dry-run line first, every time):

```
tools/factory/seat/factory-dispatch sd1 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md --dry-run
tools/factory/seat/factory-dispatch sd1 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md            # prints "SD1" "SD2" "SD3" "SD5"
tools/factory/seat/factory-dispatch sd2 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md            # after wave 1 landed; prints "SD4" "SD6" "SD7"
tools/factory/seat/factory-dispatch sd3 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md            # after SD7 landed; prints "SD8"
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-06-seat-driver.md tools/factory/seat/factory-wave sd3h /home/dalhaka/flakes/dsh-harness "SD10"   # the harness repo as the repo path, the plan stays here (the board's RECIPES line)
tools/factory/seat/factory-dispatch sd4 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md            # after SD8 and telemetry T10a landed; prints "SD9"
```

Every launch line runs in the background (`setsid -f bash -c '… >> ~/factory/runs/<run>.dispatch.log 2>&1' </dev/null`); a foreground tool call killed `tel1` at its three-minute timeout on 2026-09-06 (board).

**Landing recipe, per key (A1), in order:**

1. Keep only the one commit the section names: `git -C ~/factory/ws/<run>/<KEY> log --format='%h %s' <base>..task/<KEY>` (base from `~/factory/ws/<run>/<KEY>/.factory-meta`); more than one line → `git -C ~/factory/ws/<run>/<KEY> reset --hard <that sha>` (three seats appended a fabricated board commit on 2026-09-05; the integrator refuses one, this step drops it before the gate).
2. If main moved under a file the task touches — for this plan: `factory-lib.sh`, `factory-task`, `80-seat-driver.bats`, `tasks.py`, `flake.nix`, `docs/runbooks/lanes.md`, `docs/runbooks/session.md`, `claims.toml` are the shared files with the telemetry, CR4 and held SB tasks — or under `docs/MAP.md`: `git -C ~/factory/ws/<run>/<KEY> fetch ~/nixos-agent-env main && git -C ~/factory/ws/<run>/<KEY> merge --no-edit FETCH_HEAD`, then in the workspace `python3 pkgs/evidence/repomap.py --root . write` and, on a board conflict, `git show FETCH_HEAD:docs/OPERATIONS.md > docs/OPERATIONS.md && nix develop -c python3 pkgs/evidence/tasks.py --root . write-board`, then `git add <the named files>` and `nix develop -c git commit -q --no-edit`; re-run the shared test file (`nix develop -c bats tests/unit/80-seat-driver.bats`, or `pytest tests/evidence -q`) before the gate. This is the orchestrator's step, never the seat's.
3. Commit the gate review (`docs: gate review — <run> <KEY> …`) with the P3A front-matter block (`plan_defect`, the mutant counts).
4. `tools/factory/seat/factory-integrate <run> ~/nixos-agent-env <KEY> && git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/<run>` — gated on both exit codes; never pull after a `CHECK … fail` line. For SD10: `factory-integrate sd3h ~/flakes/dsh-harness SD10` with `FACTORY_CHECK_CMD` set to the harness's gate command (the repo has no flake), then the fast-forward it prints.
5. Dispatch what it unblocks (A7): SD3 → SD4; SD1 + SD5 → SD6; SD1 + SD2 + SD5 → SD7 (so `sd2` fires once all four of wave 1 landed); SD7 → SD8 and SD10; SD8 + T10a → SD9.

**Relaunch after a seat death (A6):** the dead seat's diff stays in `~/factory/ws/<run>/<KEY>`; relaunch the one key as `FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-06-seat-driver.md setsid -f bash -c 'exec tools/factory/seat/factory-wave <run>b ~/nixos-agent-env "<KEY>" >> ~/factory/runs/<run>b.wave.log 2>&1' </dev/null` after reading the dead result's `FACTORY-NOTES` (and, once T2 lands, its `error_class:`): a credit outage waits for the top-up, a provider error relaunches at once, `template-echo`/`no-result-line`/a near miss never relaunch blind (telemetry decision, answer 3). A key recorded `status=escalated` (SD7) is not a death: paste its `launch:` line.
