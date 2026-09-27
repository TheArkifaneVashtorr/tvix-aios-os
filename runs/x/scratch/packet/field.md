# Field packet

## (1) Dated incidents, 2026-09-04 onward

Sources checked: `docs/OPERATIONS.md` (32 lines, no dated incident entries —
only the current NEXT line), `docs/board/log-2026-09.md` (full text read),
`docs/board/archive-2026-09-02-to-05.md` (grepped for `2026-09-0[45]`; that
file's own header says it covers 2026-09-02 to 2026-09-05, superseded and
moved verbatim). No other `docs/board/archive-*.md` file exists
(`ls docs/board/` shows only `archive-2026-09-02-to-05.md`).

- **2026-09-08 (Session 20, ~09:50–17:15 CDT): fabricated/misparsed result — SD3 came back with no FACTORY-RESULT block.** SD3 "returned at 13:08 after 38 min with NO result block — its reply ended in the middle of analysing a test (`FACTORY-NOTES result-misparse: Actually wait, let me look at how the test (2) …`), so the driver completed the record itself (SH2): `status=unreported`". Closed by SD3b (typed with the fixture row, eight pins) landing later that session. — log-2026-09.md line 25.

- **2026-09-08 (Session 20, 10:55–13:05 CDT): guard denial of the orchestrator's own command — OG3 (house-guard hardening) rejected on the guard's own gap, then a launch hit a stale run dir.** "a first launch under the old `og3` run name hit an old run directory and an unexecutable launcher; the guard refused one `chmod` beside a plan path." Also OG3's gate REJECTED on one MAJOR: `PROTECTED_PATHS` entries resolve against `CLAUDE_PROJECT_DIR`, so absolute-path writes to the guard script itself were still ALLOWED from a seat workspace. Closed by OG3b, itself rejected again (`${HOME}` tokeniser hole — see next item), then by the re-plan OG3r, APPROVED and landed 08426bb. — log-2026-09.md line 27.

- **2026-09-08 (Session 20, 13:20–13:45 CDT): guard denial / gap — OG3b's own promised fix left a hole.** OG3b's gate REJECTED: "the guard's tokeniser treats `{` and `}` as operators (`:358`), so `${HOME}/nixos-agent-env/tools/orchestrator-guard.sh` never reaches the rule" and writes to it were still ALLOWED from a seat workspace. Closed by the re-plan OG3r ("pins the environment, not the text": the seat unit mounts the guard script read-only via `ReadOnlyPaths`), APPROVED and landed at 08426bb 16:20–16:25. — log-2026-09.md line 27; landing at line 27 ("OG3r APPROVED 16:20 and LANDED 16:25").

- **2026-09-08 (Session 20, 09:50–13:20 CDT): dead/incomplete launch and merge friction — SD6/SD4b integrate conflicted after a board regen race.** "SD6's workspace merged main with a MAP conflict (regenerated) — the first integrate then CONFLICTED because SD4b's review had regenerated the queue block on main in between (the recipe's lesson, relearned: no commit to main between the workspace merge and the integrate)." Closed by merging again and re-running `factory-integrate`, landing SD6 at main 43f6b13. — log-2026-09.md line 29.

- **2026-09-08 (Orchestrator Session 22, 21:20–23:00 CDT): switch #23, done clean, but a registration bug found in the recipe.** "The bare `switch-to-configuration switch` from a store path activated without registering a generation — `/run/current-system` was the new config while the profile still read gen 47 — and the two registration commands (`nix-env -p … --set`, then `… switch-to-configuration boot`) are now part of the switch recipe on the board." Closed by adding the two registration commands to the switch recipe. — log-2026-09.md line 19.

- **2026-09-08 (same session): a dead/unbootable state left deliberately — SD12 written but withheld.** SD12 documents that `seat@` runs `ProtectSystem=strict` with no `PrivateTmp` while dsh's spill store writes an absolute `/tmp/dsh-spill-XXXXXX` path, so the drive session is unbootable; "SD12 is written, committed, and NOT dispatched; the drive session stays unbootable until it lands and a switch #24 follows." — log-2026-09.md line 19.

- **2026-09-09 (Session 23, 04:53–~08:30 CDT): a fabricated/withdrawn-key commit reached main (BUG3).** "BUG3 (the board generator keys the repo on the directory basename; one seat commit, 0443648, and one merge, 4ec8951, carried withdrawn keys to main) is fixed by FIX3b". Closed by FIX3b, landed at session end, run through the unit, "ten of ten mutants dead". — log-2026-09.md line 15.

- **2026-09-09 (same session): a dead/misconfigured launch path — the direct (non-broker) seat-submit arm was reachable.** FIX1 landed at 0faa2d3: "factory-task resolves `$SEAT_SUBMIT` then PATH and REFUSES the direct arm unless `FACTORY_SEAT_UNIT=0`" — closing a bypass of the broker chokepoint. — log-2026-09.md line 15.

- **2026-09-09 (same session): switch #25, done, immediately followed by a guard/fence denial the operator hit live.** "SWITCH #25 DONE 11:49 CDT... Then the operator opened it: the page worked, its first API call did not — `directoryPicker/list` HTTP 403... dsh's host fence (`isTrustedApiRequest`, ahead of authentication) refuses any non-loopback Host header not given by `--trusted-host`, and the wrapper never passed it." Closed by FIX4, gated APPROVED, landed; then SWITCH #26 done, verified the fence passed (`401 unauthorized`). — log-2026-09.md line 15.

- **2026-09-09 (media/DSH seat-driving session): two gate launches died on a missing FACTORY_PLAN default.** "the first two gate launches died on `factory-review`'s `FACTORY_PLAN` default (`$repo_path/.../2026-09-04-dsh-review-fix-round.md` missing in media; a known P11-class reviewer defect), so re-launched with `FACTORY_PLAN=<comfy-worlds plan>`." — log-2026-09.md line 13.

- **2026-09-09/12 (same wave): a real, recurring, load-sensitive test flake surfaced at integration (not a defect, but repeatedly misread as one).** "its actual main landing came later, 2026-09-09, at `969bc0a`... after `tests/unit/94-seat-harness.bats:2118` was isolated as a real, recurring, load-sensitive flake (not a UI1 defect: it failed once, passed on a re-run of the identical build, and has since failed twice more on two separate integrate attempts)." — log-2026-09.md line 13.

- **2026-09-12 (Session 22 close, "the bad runs", 01:20–08:40 CDT, written 2026-09-14): a revision run died on the weekly spend limit and left corrupted/empty drafts.** "A revision attempt at 06:34 ... was cut by the weekly spend limit at ~06:45 — every transcript ends on the limit message; `drafts-r1/` holds platform ... and helm ... usable, seat-harness byte-identical, factory/defects/isolation with every task body lost (their exit 0 is zero tasks parsed), evidence/generation/knowledge never written; `revise/` is 226 MB of empty clones." Also: "At 08:39:57 Codex Desktop (the VS Code extension) bootstrapped `AGENTS.md` and `.codex/hooks.json` in the repo cwd" (an uninvited write into the checkout). Also a board correction: "seat `20260912-035513-c117b1` had exited at 01:08:54 CDT with status 1 — it was not running at 01:20" (a seat-death/board-accuracy incident). — log-2026-09.md line 7.

- **2026-09-14 (Session 23, revision round, 10:55 onward): guard denials of the orchestrator's own archive-move commands.** "Archive moves of `AGENTS.md`, `.codex/`, `tree/`, `.msg-ui1.txt` were refused to the orchestrator by the auto-mode classifier; the operator's commands are in the handoff." Also: "the guard's delete family (`rm mv rsync`) denies on any ancestor of the plans dir, so a set-check tree is built with `cp -a`" (a workaround for a guard denial, not an incident but a standing constraint). Also cut by a 5-hour session limit mid-run, leaving 26 of 51 agents dead, before resuming as a sequential run. — log-2026-09.md line 5.

- **Switch #27 → gen 53 (2026-09-10 00:15 CDT): clean switch; bug-ledger seeds recorded rather than a live incident.** Recorded as future bug-ledger seeds for EV4, not incidents that fired that day: run-name reuse in `factory-ws`, `factory-review` needing `FACTORY_PLAN` for `factory-task` runs, an `Escalated:` marker surviving a reviewed key, fix-round sections not inheriting `repo:`, `helm-home` non-determinism under `--rebuild`. — log-2026-09.md line 9.

No entries dated 2026-09-04 or 2026-09-05 were found describing a seat death, dead launch, fabricated commit, misparsed result, hook loop, guard denial, or red check on main in `docs/board/archive-2026-09-02-to-05.md`; that file's 2026-09-04/05 lines are wave-completion and switch-readiness notes (e.g. "SWITCH #14 DONE (2026-09-05 06:53)", "WAVE 1 LANDED (2026-09-05 09:30 CDT)") with no incident of the named classes. `docs/OPERATIONS.md` in this snapshot holds only the live NEXT-line, no dated incident log of its own (the board log was "moved verbatim from docs/OPERATIONS.md on 2026-09-05" into `docs/board/log-2026-09.md`, per that file's own header).

## (2) Driver's contract — one sentence each, anchor text pasted beside it

**factory-task — FACTORY_PLAN default when unset:** there is no default; it is required and the script dies. Anchor (`tools/factory/seat/factory-task:99-100`):
`if [ -z "${FACTORY_PLAN:-}" ]; then` / `factory_die 2 "FACTORY_PLAN is unset — name the plan (FACTORY_PLAN=<plan.md> …) or launch through factory-dispatch"`

**factory-review — FACTORY_PLAN default when unset:** falls back from the run's own `plan:` metadata line to the `FACTORY_PLAN` env var, and dies if neither is set. Anchor (`tools/factory/seat/factory-review:93-94`):
`plan=${plan_meta:-${FACTORY_PLAN:-}}` / `[ -n "$plan" ] || factory_die 2 "no plan to review: $meta has no plan: line and FACTORY_PLAN is not set"`

**FACTORY-RESULT grammar the extractor accepts:** exactly a line matching `status=(done|partial|failed)`, last such line wins. Anchor (`tools/factory/seat/factory-task:519,524`):
`# \`FACTORY-RESULT status=(done|partial|failed)\` (the last one wins, as today).` / `grep -E '^FACTORY-RESULT[[:space:]]+status=(done|partial|failed)([[:space:]]|$)' -- "$log"`

**What it synthesises otherwise:** with commits present but no usable line, it records `status=unreported`; with no commits and no usable line, it synthesizes `status=failed`. Anchor (`tools/factory/seat/factory-task:711-712,732-733`):
`factory_log "near-miss FACTORY-RESULT line, but task/$key has $actual_commits commit(s); recording unreported"` / `result_line="FACTORY-RESULT status=unreported exit_code=$exit_code"` … `factory_log "no usable FACTORY-RESULT line in the seat's output; synthesizing a failure record"` / `result_line="FACTORY-RESULT status=failed exit_code=$exit_code"`

**factory-integrate — what it merges, from where, and what it refuses:** it `git merge --no-ff`s each `task/<KEY>` branch, fetched from that key's own workspace clone, in the given order, into `integ/<run>`. Anchor (`tools/factory/seat/factory-integrate:6-8`):
`# \`git merge --no-ff\` each task/<KEY> in the given order, fetching the` / `# branch from that key's own workspace clone first. A merge conflict aborts` / `# just that merge, logs "CONFLICT <KEY>" and continues with the next key.`
It refuses a key whose branch shares no merge base with the default branch, and refuses a key whose `.result` records more files touched outside its declared `touches` than a stated reason allows. Anchor (`tools/factory/seat/factory-integrate:87-90,102-104`):
`# An unrelated-history branch shares no merge base with the default branch;` / `# the board guard cannot be run, so refuse rather than merge blind.` / `logboth "REFUSED $key: no merge base with origin/$default_branch"` … `# SH3: refuse a key whose .result records more files outside touches than it` / `# reason. Missing file or lines -> no record, and the merge proceeds as today.`

**Where dispatch.log is written and the one line it holds:** under the run directory, `$FACTORY_RUNS/<run>/dispatch.log`, and each launched wave appends one line naming the run, plan and groups. Anchor (`tools/factory/seat/factory-dispatch:11-12,187,190`):
`# logged to stderr and appended to $FACTORY_RUNS/<run>/dispatch.log; each task's` / `dispatch_log=$runs_dir/dispatch.log` / `printf 'factory-dispatch: run %s plan %s groups: %s\n' "$run" "$plan_base" "${groups[*]}" >>"$dispatch_log"`

**What a hand launch must set:** with no `seat-submit` resolvable via `$SEAT_SUBMIT` or PATH, a hand/direct launch must explicitly set `FACTORY_SEAT_UNIT=0` to opt into the non-broker arm, or the script refuses. Anchor (`tools/factory/seat/factory-task:374-375`):
`elif [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then` / `printf '%s\n' "factory-task: refusing -- no seat-submit on PATH and SEAT_SUBMIT is unset; set FACTORY_SEAT_UNIT=0 for the direct arm (docs/brief.md invariants 2 and 3)" >&2`

(factory-wave was read for context but contributed no additional distinct contract fact beyond what factory-task/factory-dispatch/factory-integrate already state; its own env-override section documents the same wave-launch mechanics factory-dispatch calls into.)
