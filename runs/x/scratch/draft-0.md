# The operator's seat as the machine's driver — ladders, the spool, the drive job, the prior attempt, the class, the record (plan, 2026-09-06)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) reads the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and a commit subject. A seat sees only `## Global Constraints`, `## Assumptions` and its own section — nothing else in this file reaches it.

**Goal:** the operator talks to a `drive` job on the existing seat unit instead of to Fable; that seat dispatches work through the existing driver scripts and climbs a ladder of rows in `docs/ledger/routing.toml` only when a rung fails, carrying the failed attempt forward; every attempt records its rung, class and prior, and `evidence report ladder` turns "Fable produces tangible results and others often do not" into a measured column per model per task class.

**Spec:** `docs/superpowers/specs/2026-09-06-operator-seat-driver-design.md` (M, 2,266 words by `wc -w`; the operator's verbatim ask of 2026-09-06 ~08:55 CDT in Fable's words; its three questions are re-asked below and the plan follows their defaults). One sentence of the spec is wrong and this plan does not lean on it (map item R5): the integrator does not refuse a commit outside `touches` — `grep -n 'REFUSED $key' tools/factory/seat/factory-integrate` prints only `REFUSED $key: docs/OPERATIONS.md changed outside the queue block` and `REFUSED $key: no merge base`. The spec's own first-rows table also breaks the spec's one-variable-per-step rule (Decisions, D3).

**Packet:** `/tmp/draft-scratch/packet/{mechanical,record,operator,target}.md`, taken 2026-09-27T00:45Z at HEAD `4a7374c` (`git rev-parse --short HEAD`); `tasks.py check` exited 0 with empty output (M1). The packet's fifth part, `field.md`, was **absent** (the harness's field reader wrote nothing: `ls /tmp/draft-scratch/packet` lists `check.err check.out graph.json mechanical.md operator.md record.md target.md`); its content — the driver's contract and the incidents — was read from the tree and the board directly and is pasted under each section's Facts. Two further harness defects noted, never routed around: the commit-body recipe the drafting prompt cites (`docs/superpowers/plans/2026-09-11-defects.md`, DF8d) and `tools/debug/bug-note` do not exist in this checkout (`ls docs/superpowers/plans/2026-09-11-defects.md tools/debug/bug-note` → both `No such file or directory`), so the recipe is written out in Global Constraints and these notes stand in for the inbox line. The snapshot has one commit (`git log --format=%s | wc -l` → 1, subject `snapshot`), so every landed task reads `approved`, not `landed`, in this tree's graph; the plan's `dependsOn` therefore never names a task the board records as landed (P11r, RT5rb, SB4b, CR2r3b) — those are facts pasted from the tree instead.

**Invariants:** brief §3.2 and §3.3 are held by construction (the drive job runs in `seat@` behind the seat broker; nothing new leaves the machine; the seat unit additionally loses `/run/dbus`, a narrowing); §3.5 holds because every routing choice — rung, fallback, class — is a row in `docs/ledger/routing.toml` or `docs/ledger/task-classes.toml`, reviewed in a diff. No basket, no new credential, no new egress host, no key in any fixture. Widening: none — the guard the driver runs under gains rules (SD3, SD4) and loses none.

## Questions for the operator

Three, each answerable in one word; each is the spec's own question, and the plan follows the default until answered.

1. **The driver's own row** (`openrouter/orchestrate`, D1) — `high` or `medium`? Recommendation: **high**, measured against medium by `evidence report ladder` over the first five driver sessions (Pro medium is the interactive seat's saved default today: `grep -n 'model = "deepseek/deepseek-v4-pro-0813"' -B4 docs/ledger/routing.toml` shows only medium rows for Pro). Default if unanswered: **medium** (the row SD1 writes; the answer `high` is a one-line edit of that row's `effort` in the same commit as the answer). Touches decision 2026-09-03-openrouter-lane-permitted-transcripts, addendum 2026-09-05 point 1 (the interactive seat's selection stays untouched: the drive job has its own `DSH_HOME`).
2. **Anthropic models on OpenRouter as rungs** — `hold` or `allow`? Recommendation: **hold** (seat-behind-broker spec "Not in this spec"; parked-factory decision point 3); the `claude` rungs stay on the subscription as printed launch lines (SD7) and the report shows whether rung 3 is ever reached (claim `ladder-rung3-demand-unmeasured`, SD1). Default: **hold**. Touches brief §3.3 (a new egress class would be a widening).
3. **The class vocabulary** — `derived` or `heading`? Recommendation: **derived** from `touches` (SD2: nothing new to type, the heading regex and the guard's append-only rule untouched — `grep -n '^HEADING_ERE=' tools/orchestrator-guard.sh` and `grep -n '^HEADING_RE = ' pkgs/evidence/tasks.py` stay byte-identical). Default: **derived**. Touches nothing under brief §3; it is the spec's question 3.

## Spec-to-task map

| spec item | task | note |
|---|---|---|
| §1 `drive` job mode on `seat-submit`/`seat-run`; model and effort from the `orchestrate` row; the driver's `DSH_HOME` carries the skill set; the interactive seat unchanged | SD6 (mode), SD1 (the row), SD10 (the `driving` skill, in `dsh-harness`) | "immediate use = switch #20 + one `seat-submit web` job" is SB5's runbook (held); the Operator section carries the interim command from the board |
| §2 the spool: `seat-submit --no-start` + `seat-spool.path` starting `seat@<id>` for every valid `job.json`; asserted in `seat-eval`; the unit cannot reach systemd | SD5 | `--no-start`'s contract (return before any wait, pinned by `test_no_start_never_calls_systemctl`) is kept; the spooled submission is `--spool` (D2) |
| §2 the driver's guard: hook-guard's deny-only set plus the orchestrator guard's rules as one shared rule file both guards read, proven by the sweep fixture against both | SD3 (the file; the orchestrator guard reads it), SD4 (hook-guard reads it; the sweep runs against both) | |
| §3 `rung`, `fallback`, `class` in the routing table; `factory_route --rung N` (exit 3 on exhaustion); `route.py check`'s two ladder rules; the first rows; claims rows per unmeasured rung; no tier wording | SD1 (table, both lookups, rows, claims), SD7 (the climb bound to rule A1), SD10 (the skill names no tier) | D3 for the first rows |
| §3 a `claude` rung is a printed launch line and `escalate: claude/<role>` in the run | SD7 | |
| §3 the sideways fallback for the three relaunch classes | SD1 (`--fallback` in both lookups) | the relaunch itself is telemetry T15 (out: not planned yet; the spec says so) |
| §4 `factory-task --prior <run>/<KEY>` → `## Prior attempt` block composed by the driver; `prior:` in the `.result` | SD8 | |
| §5 `docs/ledger/task-classes.toml`; `tasks.py` assigns a primary class and prints it in the brief; `factory-task` writes `class:`; the routing key gains `class` | SD2 (table, `tasks.py`, brief), SD1 (the key), SD7 (`class:` and `--class`) | |
| §6 the `tasks` row carries `rung`, `class`, `prior`, `escalate`; `evidence report ladder` at n ≥ 5; rows change only by a commit citing a report line | SD9 | `dependsOn` T10a (the join), sequenced after the telemetry-1 plan as the spec requires |
| §7 what the driver may decide alone | SD10 (the skill's verbs and their limits) | the mechanics are SD5–SD8 |
| Tests: `unit` bullets | SD1, SD5, SD8, SD4 | one row per bullet in the Tests tables |
| Tests: `evidence-unit` bullets | SD2, SD9 | |
| Tests: `factory-unit` bullet | SD1 | the built-in map still matches the rung-1 `claude` rows (they are unchanged) |
| Tests: `seat-eval`, `seat-vm` bullets | SD5, SD6 | |
| Tests: `lint` bullet (the harness's whole-tree gate) | SD10 | `grep-gate` is that repo's check name (the H2b precedent) |
| Risks: the harness gate matching `rung`/`fallback` | SD10 | the skill never writes either word; the H-series owns the alternation |
| Risks: `touches` written by the plan author → the class is as true as the landed diff | out: the spec's premise is wrong (see the header); the class stays derived from `touches` and the report says so (SD9 header line) | |
| Not in this spec | out: see "Not in this plan" | |

## Decisions (the plan's, for the operator to veto)

- **D1 The driver's row is `openrouter/orchestrate/any/any` at rung 1 = Pro medium** (question 1's default), with no second rung on the OpenRouter route; its climb escalates to the `claude/orchestrate` row (Fable high) as a printed line. Alternative: Pro high now (question 1's recommendation).
- **D2 `--spool` is the spooled submission; `--no-start` keeps its contract.** `--no-start` is pinned to "write the job, print the id, nothing further" by `tests/seat/test_seat_submit.py` (`test_no_start_never_calls_systemctl`, the `--no-start: nothing further is created` assertion). The driver needs the wait half (headless jobs must return the result), so `--spool` = write the job, mark it ready, never call `systemctl`, and for headless wait for `result.txt`. The unit environment sets `SEAT_SPOOL=1`, so a `factory-task` inside any seat submits with `--spool` (SD5, SD7). Alternative: make `--no-start` wait — refused, it breaks a pinned contract.
- **D3 The first rows follow the one-variable rule, not the spec's table.** The spec's `implement/docs/any` ladder (Flash off → Pro medium) changes model and effort at once, which `route.py check` must refuse per the same spec. SD1 writes Flash off → **Pro off** (model only). Every OpenRouter `implement` key and the default row get a rung 2 (Pro medium → Pro high; Flash off → Pro off), so a fix round still runs on DeepSeek for every kind and size; `review` and `orchestrate` have one OpenRouter rung and escalate at rung 2. Each rung ≥ 2 is a `gap` claim (SD1). Alternative: only the spec's four keys — refused: it would send every M and XS fix round to Claude, the opposite of the goal.
- **D4 A ladder lives inside one route; escalation is the driver's rule on exhaustion.** `factory_route --rung N` looks only at the requested route; exit 3 with `ladder exhausted` is the signal on which `factory-task`/`factory-review` look up the `claude` row for the same role/kind/size, print the launch line and record `escalate: claude/<role>` with `status=escalated` (a fourth status word, exit 4). Alternative: cross-route rows in one ladder — refused: the spec keys ladders on route.
- **D5 The rung is the key's suffix.** `1` for a chain root, `2` for a fix round (`<ROOT>b`), `3` for anything after a re-plan (a suffix containing `r`), as the spec binds rung to rule A1; deeper chains are the operator's (spec §7: a rung-3 re-plan's dispatch is the operator's).
- **D6 The seat unit loses `/run/dbus`.** The spec's premise "a unit inside `egress-seat` cannot be trusted to reach systemd's control socket, and must not be" is made true in the module (`InaccessiblePaths` gains `-/run/dbus`), asserted in `seat-eval`, so the spool is the one host actor by construction, not by discipline.
- **D7 The spool bounds every job.** `job.json` gains `timeout` (seconds) and `seat-run` enforces it (exit 124), so a spooled job the submitter cannot stop still ends; "the spool starts units and nothing else" stays exact.
- **D8 The shared rule file is `docs/ledger/guard-rules.txt`** (policy in the repo, reviewed in a diff; copied into the `unit`, `evidence-unit` and `ledger-unit` sandboxes already — `grep -n 'cp -r ${self}/docs/ledger docs/ledger' flake.nix` → two hits). The seat's copy is embedded in the wrapper package at build time, so the seat's rules change only by a switch the operator runs; the orchestrator guard reads the checkout's copy, as it reads its own script today.
- **D9 The class is printed in the brief as one grouped line** (`**Classes (next wave):** …`) and omitted when the brief would exceed the session hook's 1,400-byte cap (`grep -n 'cap_part BRIEF' tools/session-start.sh` → `cap_part BRIEF "$brief" 1400`; the brief is 1,275 bytes today by `tasks.py brief | wc -c`).
- **D10 The driver's workspace is the live checkout** (`--workspace ~/nixos-agent-env`): §7 lets the driver integrate and write the board's queue block, which only the live checkout allows without a push (`git push` is refused by both guards). The operator may instead point it at a clone and keep integration for themselves.

## Global Constraints

- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown, never a seat launch of your own (`tools/factory/seat/*` is the paid driver: read it, test it with fakes, never run a real launch); no reading `/var/lib/secrets/*`, `~/.config/openrouter/key` or `~/.config/restic/password`. The operator switches (the Operator section, invisible to you).
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` every new file **before** any `nix build` (a flake sees tracked files only); never `--no-verify`, never `2>/dev/null` on a gated command; never `git push`, `git commit --amend`, `git rebase`, `git reset --hard`.
- **Exactly one commit, its subject byte-identical to the section's `commit subject`,** with the two trailers the WORKSPACE RULES name. Stage only the files the section's `touches` names (`git add <paths>`, never `git add -A`); never commit `docs/OPERATIONS.md` (the integrator refuses it), never merge `main` into your branch, never regenerate or restore the board's queue block — the integrator and the orchestrator do that outside your commit.
- **The commit body is produced by a script, never typed.** Write `.factory-scratch/commit-body.sh` in the workspace (that directory is never staged): it prints the section's commit subject, a blank line, then for every command the section's Steps name — the red command (whose saved output `.factory-scratch/red.txt` it `cat`s) and each green command — a `$ <command>` line followed by that command's output (`bash -c "$c" 2>&1 | tail -n 20`), then the two trailers last. Run `bash .factory-scratch/commit-body.sh > .factory-scratch/msg.txt`, read the file once, and commit with `nix develop -c git commit -F .factory-scratch/msg.txt`.
- **TDD, red before green.** Every Step named "Run it red" pastes its command and its expected output; save that output to `.factory-scratch/red.txt` (`… 2>&1 | tail -n 20 > .factory-scratch/red.txt`) before changing the tree. A load-bearing test counts only once it has been shown to fail; a test that cannot fail is a `vacuous-test` major. Every proxy names what it stands in for (`docs/decisions/2026-09-03-test-based-reality-amendments.md`).
- **One writer per tree.** Work only in the isolated workspace on `task/<KEY>`; `touches` is a contract — a file outside it is a deviation to report in `FACTORY-NOTES`, not to write. Probes assert the post-state (a grep for anchor text, a count, an exit code), never a line number.
- Python is stdlib only in `pkgs/` (`tomllib`, `json`, `fnmatch`, `subprocess`); bash scripts under `tools/factory/seat` and `tools/orchestrator-guard.sh` are pure bash (no python, no awk pipeline where a builtin does); the seat's `hook-guard.py` runs on `python3Minimal` (stdlib, no third-party import). Tests: pytest under `tests/evidence`, `tests/seat`, `tests/lane`; bats under `tests/unit` — one `[ … ]` per line (an `&&` chain cannot fail; `tests/lint/bats-and-chain.sh` refuses it); a bats test launches a driver script only as `"$REAL_BASH" "$SEAT/<script>"`, never by its shebang (the structural test `no bats test launches a driver through its own shebang`).
- Formatting: `nix develop -c treefmt` after writing (ruff at 88 columns rewraps the Python blocks below: a reformatting-only difference from the plan text is not a deviation); statix rejects `{ ... }:` module headers (write `_:` or name the args); `hosts/core/hardware-configuration.nix` is exempt; the lint gate is `nix develop -c githooks/pre-commit`.
- Claude agents never write inside `~/flakes/dsh-harness`; SD10 runs as a seat with that repo as its `<repo-path>` and touches only that tree.
- No secrets in the repo: no fixture may quote a key, a token, or a path under `/var/lib/secrets` beyond the module's own literal.
- The result block ends your reply in its exact form — `FACTORY-RESULT status=done|partial|failed` (a space, no colon), then `FACTORY-CHECKS`, `FACTORY-COMMITS`, `FACTORY-NOTES`, nothing after it; any other spelling is recorded as failed.

## Assumptions

1. The devShell's `python3` is ≥ 3.11 (`tomllib`); `pytest`, `bats` ≥ 1.5, `jq`, `shellcheck`, `ruff`, `node` are in it. The build sandbox has no `/usr/bin/env`, no zoneinfo and no network; every check named below runs there.
2. `docs/MAP.md`'s Checks section is the acceptance vocabulary (`awk '/^## Checks/{s=1;next} /^## /{s=0} s&&/^- /' docs/MAP.md`): `unit`, `lint`, `factory-unit`, `evidence-unit`, `claims-validate`, `seat-eval`, `seat-unit`, `seat-vm`, `host-core` are all listed. `grep-gate` and `node-test` are the `dsh-harness` repo's names (H2b's precedent) and are exempt from the map.
3. The `unit` check copies `tools/factory/seat`, `tools/factory/plan`, `tools/factory/route.py`, `tools/orchestrator-guard.sh`, `docs/ledger`, `docs/runbooks/session.md` and `pkgs/evidence` beside `tests/` (`grep -n 'cp -r ${self}/tools/factory/seat\|cp ${self}/tools/orchestrator-guard.sh\|cp -r ${self}/docs/ledger docs/ledger' flake.nix` → lines 2031, 2052, 2042), so a bats test resolves `../../docs/ledger/guard-rules.txt`, `../../docs/ledger/routing.toml` and `../../tools/factory/route.py` without a `flake.nix` change. `evidence-unit` copies `pkgs/evidence`, `tests/evidence`, `docs/ledger`, `docs/superpowers/plans`, `docs/MAP.md`; `seat-unit` copies `pkgs/seat` and `tests/seat`; `factory-unit` copies `tools/factory/route.py` and `docs/ledger/routing.toml` by name.
4. `pkgs/evidence/streams.py` and `pkgs/evidence/ingest_result.py` do not exist in this tree (`test -f` → MISSING for both); they land with telemetry T1 and T2 (`docs/superpowers/plans/2026-09-06-telemetry-store-1.md`), whose sections are the contract SD9 writes against. SD9 is blocked until T10a lands and is dispatched by the telemetry plan's order, not this one.
5. `FACTORY_ROUTING_TABLE` names the table both lookups read (`grep -n 'FACTORY_ROUTING_TABLE' tools/factory/seat/factory-lib.sh tools/factory/route.py pkgs/dsh-openrouter/hook-guard.py` → all three read it); tests pass fixture tables through it or as the positional `FILE`/`--file`, never the committed table except in the cross-check tests that pin it.
6. `claims.py validate --today $(date +%F)` in the pre-commit hook refuses a commit while any gap is past its review date. At the packet date the file validates (`… --today 2026-09-06` → exit 0); run later, six pre-existing gaps are stale (`… --today 2026-09-27` prints six `gap past review_by` lines). The orchestrator refreshes those dates in a docs commit before wave 1 (Operator step 2); the new gap rows SD1 adds carry `review_by = 2026-10-04`.
7. `~/flakes/dsh-harness` is absent from this checkout (`ls -d /home/dalhaka/flakes` → No such file); SD10's facts about that repo are the plan file `2026-09-05-harness-router.md` and P13's section, and its Step 1 reads the gate before writing.
8. `.claude/settings.json` is `{}` in this snapshot; on the live host it wires `tools/orchestrator-guard.sh` as the `PreToolUse` hook (`docs/runbooks/session.md` "Guard — what the orchestrator refuses to do"). SD3 changes the guard's inputs, not its wiring.
9. The seat unit's `harnessPackage` is the wrapper package (`pkgs/dsh-openrouter`), which embeds `hook-guard.py` through `writePython3MinimalBin` (`grep -n 'hookGuard = ' pkgs/dsh-openrouter/default.nix`); a change to `hook-guard.py`, `dsh-openrouter.sh` or the rule file changes the host closure and needs a switch (A2).
10. `nix develop` inside `egress-seat` evaluates the flake offline when the lock's inputs are in the store (they are, every lint gate builds the devShell); the `driving` skill's verbs pass `--offline` so a missing input fails loudly instead of waiting on the broker's refusal. Unmeasured here (the VM has no devShell); the first driver session measures it (Operator step 7).

## Waves

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

## Operator

Every command is pasted from a dry run here or quoted from the board's RECIPES/the runbooks; nothing is a sentence where a command would do. The plan follows the three defaults until step 1 is answered.

1. **Answer the three questions** (one word each: `high|medium`, `hold|allow`, `derived|heading`). Acceptance: the answers on the board; `high` is a one-line `effort` edit of the `openrouter/orchestrate` row in SD1's commit or a follow-up docs commit whose body cites the answer.
2. **Before wave 1 — the claims file must validate on today's clock** (the pre-commit hook refuses every seat commit otherwise, Assumption 6):
   ```
   nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"; echo exit=$?
   ```
   Expected: no output, `exit=0`. If it prints `gap past review_by` lines (six did at 2026-09-27), the orchestrator extends those dates with a reason in one docs commit first; you re-run the line. Acceptance: `exit=0`.
3. **Launch wave 1** (the Dispatch section's first line without `--dry-run`, in the background):
   ```
   setsid -f bash -c 'exec tools/factory/seat/factory-dispatch sd1 ~/nixos-agent-env docs/superpowers/plans/2026-09-06-seat-driver.md >> ~/factory/runs/sd1.dispatch.log 2>&1' </dev/null
   ```
   Acceptance: `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep '^\*\*Running:\*\*'` names `nixos-agent-env/SD1`, `SD2`, `SD3`, `SD5`.
4. **After wave 2 lands — switch #21 (A2).** SD4 (the wrapper and its guard), SD5 (the module, `seat-run`) and SD6 (`seat-submit`, the embedded `route.py`) change the closure:
   ```
   nix build .#nixosConfigurations.core.config.system.build.toplevel
   nix store diff-closures /run/current-system ./result
   ```
   **Predicted delta** (a prediction; the measured delta is recorded beside it on the landed tree before this line ships): added — the `seat-spool` package, `seat-spool.path`, `seat-spool.service`, a `guard-rules.txt` store path; changed — `seat@.service` (InaccessiblePaths, `SEAT_SPOOL`), the `seat` runner package (`seat-run.py`, `seat-submit.py`, `seat-spool.py`, the embedded `route.py`), `dsh-openrouter` and its `hook-guard`; removed — nothing; `python3-minimal` unchanged. Then `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core`. Acceptance: `systemctl status seat-spool.path | head -3` → `active (waiting)`; `systemctl cat seat@.service | grep -c 'run/dbus'` → `1`; `systemctl show seat@.service -p Environment --value | tr ' ' '\n' | grep -c '^SEAT_SPOOL=1$'` → `1`. No user unit needs a hand start (the spool is a system path unit the switch activates). Rollback: `sudo /nix/var/nix/profiles/system-45-link/bin/switch-to-configuration switch` (generation 45 = `a53d2e5`, the live generation on the board; confirm with `nix-env --list-generations -p /nix/var/nix/profiles/system | tail -3` first).
5. **After SD10 lands in `~/flakes/dsh-harness` — deploy the driver's home once** (`git -C ~/flakes/dsh-harness pull --ff-only` first):
   ```
   mkdir -m 700 -p ~/.local/share/dsh-driver && ln -s ~/flakes/dsh-harness/skills ~/.local/share/dsh-driver/skills && ln -sf ~/flakes/dsh-harness/AGENTS.md ~/.local/share/dsh-driver/AGENTS.md
   ```
   Acceptance: `test -r ~/.local/share/dsh-driver/skills/driving/SKILL.md && echo ok` → `ok`. Your interactive seat's home (`~/.local/share/dsh-openrouter`) is untouched.
6. **Start the driver** (after step 4; SD6):
   ```
   nix run ~/nixos-agent-env#seat-submit -- drive --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-driver --port 43210
   ```
   It prints the job id. Acceptance: `cat /var/lib/seat/jobs/<id>/url.txt` → `http://10.100.4.2:43210`; `systemctl show seat@<id> -p ActiveState --value` → `active`; open the URL in the browser. Stop it with `systemctl stop seat@<id>` (your polkit right). Until step 4 the interim web seat is the board's line: `nix run ~/nixos-agent-env#seat-submit -- web --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter --model deepseek/deepseek-v4-pro-0813 --effort medium --port 43210`.
7. **The first driver session measures Assumption 10.** Say `brief`. Acceptance: the seat prints the task brief's `**Next wave**` line. If it reports that `nix develop --offline` failed inside the namespace, stop there — that is the orchestrator's item (the verbs need a devShell-free path), not a seat's. Then ask for one dispatch of a rung-1 task; acceptance: `cat "$(ls -t /var/lib/seat/jobs/*/spool.txt | head -1)"` begins `started`, and the newest `~/factory/runs/*/*.result` carries `rung: 1` and a `class:` line.
8. **Spend before wave 1 (A3, A9).** Four seats start at once (three on Pro medium, one on Flash off — the `unit`/`seat-vm`-heavy tasks are M). The balance is yours to check (the board: $32.23 at 08:55, no preload above $100); at the 2026-09-04 rate ($0.10–0.19 per XS/S run, planning design §1) wave 1 costs of the order of $1 — a proxy: the tree holds no activity-export rows, so spend since the last top-up is unmeasured here.
9. **Rollback per task:** `nix develop -c git revert <the task's commit>` in `~/nixos-agent-env`; the switch rollback is step 4's; `rm -rf ~/.local/share/dsh-driver` removes the driver's home without touching the interactive seat.
10. **The claims SD1 adds** carry `review_by = 2026-10-04`: before that date either `evidence report ladder` shows the rung's row at n ≥ 5 or the orchestrator extends the date with the n it did reach.

## Dispatch

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

## Anticipation

| row | applies? | artefact |
|---|---|---|
| A1 dispatch | yes | §Dispatch: the run names, the pasted dry run, the per-wave lines, the five-step landing recipe |
| A2 switch | yes (SD5 edits `nixosModules/seatLane.nix`; SD4's wrapper and SD6's seat package are in the closure) | Operator step 4: the two build commands, the delta as a prediction, the acceptance probes, the rollback generation |
| A3 credentials, names, top-ups | the driver's home (a directory the operator creates) and the balance check | Operator steps 5 and 8; no credential, name or password file changes |
| A4 mutation tables | yes | every section's Tests table: one mutant per assertion, the discriminating fixture per row |
| A5 driver guards | the tree already holds them: `FACTORY_PLAN` unset → `factory_die 2 "FACTORY_PLAN is unset — …"` in `factory-task` and `factory-wave`; `REFUSED <KEY>: docs/OPERATIONS.md changed outside the queue block` in `factory-integrate`; a near miss → `FACTORY-NOTES result-misparse: …` (all pasted under SD7/SD8 Facts and the header). This plan adds the next deterministic pieces as tasks, never sentences: the spool and `/run/dbus` (SD5), the seat guard's history/plan/override rules (SD3, SD4), the `escalated` record instead of a silent default (SD7). No `dependsOn` P11: it reads `approved` here only because the snapshot hides landings (header) | — |
| A6 seat death | yes | the relaunch line under §Dispatch; the escalated record is told apart from a death |
| A7 what a landing unblocks | yes | recipe step 5 |
| A8 claims | none flips in a diff here; SD1 **opens** six gaps (the unmeasured rungs, rung-3 demand) with `review_by = 2026-10-04`; `forbidden-list-single-source` moves one step (SD3's file is the shared source for two of the four copies — the lane's and the wrapper's stay, said so in SD3 Facts) | the flips are the orchestrator's after `report ladder` prints the rows |
| A9 hold? | one computed hold: the pre-commit hook's `claims.py validate --today $(date +%F)` is red on six pre-existing gaps at 2026-09-27 (Assumption 6) — a seat commit would be refused; Operator step 2 clears it before wave 1. `lint`/`unit`/`host-core`/`seat-vm` had no rows at HEAD in this snapshot's bundle (`HEAD —` for every check: the store is empty here), so "green at HEAD" is unmeasured in this environment and is the orchestrator's check on core before launch. SB5/SB6 held but nothing waits on them | Operator step 2; the pre-launch check on core |
| A10 questions | yes | three, each with recommendation and default, the spec's own |
| A11 handoff line | "seat-driver: on the seat: sd1 SD1 SD2 SD3 SD5; in gate: —; next: sd2 (SD4 SD6 SD7) after wave 1 lands, then sd3 (SD8) + sd3h (SD10 in dsh-harness), SD9 after telemetry T10a; switch #21 after wave 2; plan docs/superpowers/plans/2026-09-06-seat-driver.md, judgement docs/reviews/plan-judgements/2026-09-06-seat-driver.md" | for the board's START HERE |
| A12 re-plan | not a re-plan | — |
| A13 hooks / second consumers | yes: SD3 and SD4 edit the two PreToolUse hooks and add a second consumer (the rule file) of one policy. Consumers and their interpreters: `tools/orchestrator-guard.sh` (bash, the live checkout's copy at `$CLAUDE_PROJECT_DIR/docs/ledger/guard-rules.txt`) and `hook-guard` (python3Minimal, the store copy embedded at build time — a divergence between the two copies is visible as `--print-rules` differing and closes at the next switch). Failure behaviour on a bad or missing file: **deny** in both (the CR2r3b policy: fail closed on faults), each with its named mutant (SD3 row 2, SD4 row 7). No Stop hook is touched; `stop_hook_active` does not apply | SD3, SD4 Interfaces |
| A14 deny rules | yes: SD4 tightens the seat's guard. Commands the new rules refuse that appear in today's recipes: none of the seat's own WORKSPACE RULES commands (`nix develop -c git commit -F <msgfile>`, `git add <paths>`, `nix build .#checks…`) is refused; refused for a seat from now on: `git push`, `git commit --amend`, `git rebase`, `git reset --hard`, any write to `docs/superpowers/plans/*.md` from the shell, any write to `.claude/ritual-override`, and an Edit/Write that drops a typed heading — the orchestrator's exact list (`docs/runbooks/session.md` Guard section), so nothing the board's RECIPES ask a seat to do is lost. The operator's own commands are unaffected (the hook runs inside seats only) | SD4 Tests rows 1–6 (the allow controls beside every deny) |

## Not in this plan

- The relaunch table (telemetry T15) — the sideways `--fallback` query lands here, the relaunch that consumes it does not; until T15 the operator relaunches by the Dispatch line.
- Telemetry T1–T18 themselves; SD9 edits T1's and T2's files only for the four fields and the report, and waits for T10a.
- SB5 (`docs/runbooks/seat.md`, the claim `seat-key-exception-undecided`) and SB6 — held; the Operator section carries the interim web-seat line.
- Kimi K3 / GLM 5.3 rows; class-specific rows; a `fallback` on any committed row; Anthropic models on OpenRouter (question 2, default hold); a `plan` row.
- Fronting the Claude Code session with a broker; Helm Home (held); Discord (a basket, decided); the media, gaming and nixos-skill repos.
- Any change to the interactive seat the operator opens outside the unit (its `DSH_HOME` and saved selection are untouched by every task here).
- Correcting the spec's wrong sentence about the integrator (the header names it; a docs edit of the spec is the orchestrator's after the judgement, as the board says).
- A spool that stops units (`stop.txt`), a per-instance unit drop-in, or a runtime probe that `systemctl` fails inside `seat@` (the eval assertion on `InaccessiblePaths` and the VM's rendered-property check stand in; a probe from inside the unit's cgroup is SB6's shape).
- The orchestrator guard's known gap (a removal through a symlink that points into the plans directory — CR2 follow-up) and the lane's/wrapper's copies of the forbidden list (`forbidden-list-single-source` stays open).
- `factory-brief`'s section extractor becoming fence-aware (it stops at any `## ` line, fenced or not — found while drafting SD8; a defect note for the driver's board line, not a task the spec names).
- Parked in the concept file (Ship phase): `factory-wave` writing telemetry's shape-B start/end rows for a drive-dispatched run; a `report ladder --by class` cut once class-specific rows exist.

---

## Tasks

### SD1 (code, M) — the ladder is data: `rung`, `fallback` and `class` in the routing table, both lookups in lockstep, the first rows, the claims

**dependsOn:** none

**Files:**
- Modify: `docs/ledger/routing.toml` (the new keys, the first rows, the header), `tools/factory/seat/factory-lib.sh` (`factory_route`, `factory_route_check`), `tools/factory/route.py` (`parse_table`/`resolve`, `check`, `lookup`), `tests/unit/80-seat-driver.bats`, `docs/ledger/claims.toml` (six gap rows), `tools/factory/seat/README.md` ("Routing")

**Interfaces:**

- Row keys: the six of today plus `class` (optional, default `any`), `rung` (optional, default `1`, `^[1-9][0-9]?$`) and `fallback` (optional, a model id in `[A-Za-z0-9._:/-]+`). `CLASSES = (nix-module, nix-check, bash-driver, python-evidence, js-workflow, bats-test, vm-test, docs-runbook, docs-plan, docs-board)`, enumerated in both `factory_route` (a `case` arm, like roles) and `route.py` (a tuple); `class` accepts `CLASSES ∪ {any}`. SD2's `task-classes.toml` names the same ten in the same order and its test pins the two lists equal.
- A **ladder** is every row sharing `(route, role, kind, size, class)`; every row belongs to exactly one ladder; a row without `rung` is rung 1.
- `factory_route [--route R] [--class C] [--rung N] [--fallback] <role> <kind> <size> [FILE]` (pure bash, `FILE` defaults as today):
  1. Candidates are the **rung-1 rows** of route `R` whose `role`, `kind`, `size` and `class` each equal the request or are `any` (`C` defaults to `any`; a request with class `any` matches only rows whose class is `any`). Specificity counts the four fields that are not `any`; the highest wins; a tie goes to the earliest row. This is today's rule with one more field.
  2. The winning row names the ladder; the answer is that ladder's row with `rung == N` (default 1): stdout `MODEL EFFORT`, exit 0. No such row → stderr `factory_route: ladder exhausted: R/ROLE/KIND/SIZE/CLASS has no rung N (top n)`, exit 3, **nothing on stdout** (the caller's `route_line` stays empty, as it does for every exit 3 today).
  3. `--fallback`: stdout is the rung-N row's `fallback` model alone; unset → stderr `factory_route: no fallback: R/ROLE/KIND/SIZE/CLASS rung N`, exit 4.
  4. Table faults keep today's contract (exit 3 with a row-naming message; the requested route must have an `any/any/any/any` rung-1 row).
- Validation, applied by both implementations to every row and every ladder before any answer, in this order, with these messages (bash prefixes `factory_route: FILE:`, python `route.py:`): (r1) `row N: unknown key K` (today); (r2) `row N: bad rung V`; (r3) `row N: unknown class V`; (r4) `ladder R/ROLE/KIND/SIZE/CLASS: rungs must be 1..n without gaps or duplicates (got 1,3)` — the list is the sorted rungs seen; (r5) `ladder R/ROLE/KIND/SIZE/CLASS: rungs k->k+1 change 0 of model,effort (exactly one)` / `… change 2 of model,effort (exactly one)`; (r6) `row N: fallback M has no row of its own` — `M` must be the `model` of some rung-1 row of the same route — and `row N: fallback equals the row's model`; (r7) `no default (any/any/any) row` (today's message, kept byte-identical; the check is now the rung-1 row with class `any`). `factory_route_check [FILE]` probes both routes as today and therefore reports every rule.
- `tools/factory/route.py`: `lookup [--class C] [--rung N] [--fallback] ROUTE ROLE KIND SIZE` mirrors the bash lookup line for line (exit 3 on exhaustion with `route.py: ladder exhausted: …`, exit 4 on no fallback, exit 1 on a row or ladder error, exit 2 on usage); `check` runs r1–r7 over the whole table (exit 1 on the first error, message on stderr); `models` is unchanged — it reads rung-1 `claude` rows and prints the same JSON as today, so `tests/factory/render.test.mjs` (the built-in map) stays green.
- The first rows, all `route = "openrouter"`, appended after the existing openrouter block and before the first `claude` row; existing rows are byte-unchanged (they are rung 1 by default); every rung-2 row is preceded by a whole-line comment `# unmeasured — claim <id>` (never an inline `# …` after a key: both parsers treat only a line starting `#` as a comment, and an inline `#` becomes part of the value and is refused as `bad value`):

  | ladder (role/kind/size/class) | rung 1 | rung 2 | claim |
  |---|---|---|---|
  | implement/docs/any/any | Flash off (exists) | Pro off | `ladder-implement-docs-rung2-unmeasured` |
  | implement/any/XS/any | Flash off (exists) | Pro off | `ladder-implement-xs-rung2-unmeasured` |
  | implement/code/any/any | Pro medium (exists) | Pro high | `ladder-implement-code-rung2-unmeasured` |
  | implement/code/S/any | Pro medium (new; the spec's key) | Pro high | `ladder-implement-code-s-rung2-unmeasured` |
  | review/any/any/any | Pro medium (exists) | — | — (rung 2 escalates to `claude/review`, SD7) |
  | orchestrate/any/any/any | Pro medium (new, D1) | — | — (escalates to `claude/orchestrate`) |
  | any/any/any/any | Pro medium (exists) | Pro high | `ladder-default-rung2-unmeasured` |

  `Pro` = `deepseek/deepseek-v4-pro-0813`, `Flash` = `deepseek/deepseek-v4-flash`. No `fallback` key is set on any row (the only other provider rows would be Kimi/GLM, which the spec excludes); the mechanism is fixture-tested. The header comment gains three sentences: the keys, "a rung or a fallback changes only by a commit whose body cites an `evidence report ladder` line", and "the `claude` route has one rung per key; the driver escalates to it when an OpenRouter ladder is exhausted".
- `docs/ledger/claims.toml` gains six `[[claim]]` rows — the five above and `ladder-rung3-demand-unmeasured` (text: "a rung-3 attempt (a re-plan) is ever reached, so the claude rungs are not a ladder to nowhere") — each `status = "gap"`, `class = "unmeasured"`, `owner = "orchestrator"`, `opened = 2026-09-06`, `review_by = 2026-10-04`, `closes_by = "evidence report ladder prints this row at n >= 5 (SD9); the row then stays, moves or goes by a commit citing that line"`.
- Consumers: `factory-task`/`factory-review` (SD7) pass `--rung`/`--class` and read exit 3's message; `seat-submit drive` (SD6) runs `route.py lookup openrouter orchestrate any any`; the dark factory reads `route.py models`; the seat's hook guard reads the table with `tomllib` and ignores unknown keys (`_load_openrouter_models` reads `row.get("model")` only), so the new keys never touch its model rule.

**Facts** (2026-09-27, from the repo root):

- `grep -n 'unknown key\|route) cur_route=\|effort) cur_effort=' tools/factory/seat/factory-lib.sh` → `route) cur_route=$val ;;`, `effort) cur_effort=$val ;;`, `printf 'factory_route: %s: row %d: unknown key %q\n' "$file" "$row" "$key" >&2` — the bash parser refuses any key it does not know, so a `rung` row in the committed table would make every lookup exit 3 until this task lands (never land the rows before the parsers).
- `grep -n 'cur\[key\] = val\|for key in ("role", "kind"' tools/factory/route.py` → `cur[key] = val` and `for key in ("role", "kind", "size", "model", "effort"):` — python keeps unknown keys and validates five; today it would accept a `rung` row silently (the red for r1–r6 in python).
- `grep -n 'implement | review | verify | baseline' tools/factory/seat/factory-lib.sh` → `implement | review | verify | baseline | research | audit | orchestrate | plan | any) ;;` and `grep -n '"orchestrate",\|"plan",' tools/factory/route.py` → both — the role `orchestrate` needs no enum change.
- `grep -c '^\[\[route\]\]' docs/ledger/routing.toml` → `14`; `grep -n 'role = "orchestrate"' -B2 docs/ledger/routing.toml` → one row, `route = "claude"` (no OpenRouter orchestrate row today).
- `grep -n 'Change rows here, nowhere else\|Explicit --model, OPENROUTER_MODEL' docs/ledger/routing.toml` → both sentences in the header (the override rule and the one-home rule stay).
- `grep -n 'cp ${self}/docs/ledger/routing.toml\|cp ${self}/tools/factory/route.py' flake.nix` → the `factory-unit` copies (lines 1094–1095) and the `unit` copy of `route.py` (2040); `unit` copies `docs/ledger` whole (2042) — the committed table reaches both sandboxes.
- `grep -n 'route_line=$(factory_route' tools/factory/seat/factory-task tools/factory/seat/factory-review` → `factory-task:93:route_line=$(factory_route implement "$kind" "$size" || true)` and `factory-review:79:… review …` — today's callers, untouched here (SD7 adds the flags).
- `grep -n '^@test "factory_route and route.py agree on a discriminating tie' tests/unit/80-seat-driver.bats` → the cross-check idiom this task extends (`bash_out=$(… factory_route …)`, `py_out=$(python3 "$route_py" --file … lookup …)`, `[ "$bash_out" = "$py_out" ]`).
- `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06; echo exit=$?` → `exit=0`; the gap-row shape is the file's own (`id`, `text`, `status = "gap"`, `class`, `owner`, `opened`, `review_by`, `closes_by`).

- [ ] **Step 1: Write the failing tests** in `tests/unit/80-seat-driver.bats`, one `@test` per row of the Tests table below, using the file's idiom (`run "$REAL_BASH" -c ". '$SEAT/factory-lib.sh'; factory_route …"`, `python3 "$route_py" --file …`), fixture tables written into `$BATS_TEST_TMPDIR`. The ladder fixture every lookup row uses:

```toml
[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/default"
effort = "low"

[[route]]
role = "any"
kind = "any"
size = "any"
model = "m/default"
effort = "medium"
rung = 2

[[route]]
role = "implement"
kind = "code"
size = "S"
model = "m/pro"
effort = "medium"

[[route]]
role = "implement"
kind = "code"
size = "S"
model = "m/pro"
effort = "high"
rung = 2

[[route]]
role = "implement"
kind = "code"
size = "S"
model = "m/other"
effort = "high"
rung = 3
fallback = "m/default"

[[route]]
role = "implement"
kind = "code"
size = "S"
class = "bash-driver"
model = "m/bash"
effort = "medium"
```

- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/80-seat-driver.bats --filter 'rung|ladder|class|fallback' 2>&1 | tail -n 20 > .factory-scratch/red.txt; cat .factory-scratch/red.txt` → every new test fails; the first failure reads `factory_route: …/ladder.toml: row 2: unknown key rung` where `m/pro medium` was expected, and the python refusal test fails with `check exited 0, expected 1` (today's `route.py` keeps unknown keys).

- [ ] **Step 3: `factory-lib.sh`.** Extend the option loop (`--class`, `--rung`, `--fallback`), the key `case` (`class`, `rung`, `fallback`), the per-row validation (r2, r3, r6's shape), collect rows into indexed arrays (`row_route[]`, `row_role[]`, `row_kind[]`, `row_size[]`, `row_class[]`, `row_rung[]`, `row_model[]`, `row_effort[]`, `row_fallback[]`) instead of deciding during the walk, then after the walk: build the ladder groups keyed `"$route/$role/$kind/$size/$class"` in an associative array of rung lists, apply r4, r5, r6 (the fallback must be the model of a rung-1 row of the same route), r7, then choose the winning key from rung-1 rows and answer per the Interfaces. Keep every existing message byte-identical (the tests above pin `no default`, `unknown role`, `bad value`, `row 1`, `effort`).

- [ ] **Step 4: `route.py`.** `CLASSES` tuple; `parse_table` unchanged; a new `validate(rows) -> None` (r1–r6; `RowError` for row-scoped, a `LadderError(Exception)` for r4/r5 with the exact text) and `resolve(rows, route, role, kind, size, cls="any", rung=1, fallback=False)`; `lookup` parses the three flags before the four positionals; exit codes as in the Interfaces; `models` calls `resolve` with the defaults.

- [ ] **Step 5: The rows and the claims.** Append the seven new rows (the table above), the header sentences, the six claims; `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today "$(date +%F)"` prints nothing (Assumption 6: if it names a pre-existing stale gap, report it in `FACTORY-NOTES` and stop — it is the orchestrator's, not yours). README "Routing": the three keys, the flags, exit 3/4, r1–r7, the escalation sentence.

- [ ] **Step 6: Run it green** — `nix develop -c shellcheck tools/factory/seat/factory-lib.sh`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix develop -c python3 tools/factory/route.py --file docs/ledger/routing.toml check; echo $?` → `0`; `nix develop -c treefmt`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `… factory-unit`; `… claims-validate`; `nix develop -c githooks/pre-commit`.

- [ ] **Step 7: Commit** — the Global Constraints recipe: `.factory-scratch/commit-body.sh` prints the subject, `.factory-scratch/red.txt`, then runs and appends the four Step 6 commands' outputs and `python3 tools/factory/route.py --file docs/ledger/routing.toml lookup --rung 2 openrouter implement code S` (expected `deepseek/deepseek-v4-pro-0813 high`), then the trailers.

**Tests** (each row: the assertion; the one-line mutant that turns it red; the fixture row that makes it discriminate):

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | `factory_route implement code S FX` → `m/pro medium`; `--rung 2` → `m/pro high`; `--rung 3` → `m/other high` | pick the last matching row instead of the rung-N row → rung 1 prints `m/other high` | three rungs with three distinct (model, effort) pairs |
| 2 | `--rung 4 implement code S FX` → exit 3, stderr `ladder exhausted: openrouter/implement/code/S/any has no rung 4 (top 3)`, empty stdout | fall back to the top rung → stdout `m/other high`, exit 0 | the fixture's top is 3, not the requested 4 |
| 3 | `--class bash-driver implement code S FX` → `m/bash medium`; `--class bash-driver --rung 2 …` → exit 3 `(top 1)`; `--class nix-module implement code S FX` → `m/pro medium` | drop `class` from specificity → the class row ties with the `any` row and the earlier `m/pro` wins | the class row sits later in the file than the `any` row it must beat |
| 4 | `--rung 3 --fallback implement code S FX` → `m/default`; `--rung 2 --fallback …` → exit 4, stderr `no fallback` | print the row's model when fallback is unset → rung 2 prints `m/pro` | rung 2 has no fallback, rung 3 has one |
| 5 | `factory_route_check` refuses each of: a two-variable step (`m/a low` → `m/b high`, rungs 1→2) with `change 2 of model,effort`; a zero-variable step (`m/a low` twice) with `change 0`; rungs `1,3` with `without gaps or duplicates (got 1,3)`; two rung-2 rows with `(got 1,2,2)`; `rung = 0` and `rung = "x"` with `bad rung`; `class = "rocket"` with `unknown class`; `fallback = "m/nowhere"` with `has no row of its own`; a fallback equal to the row's model with `equals the row's model` — each its own fixture, exit 3 | delete any one rule → its fixture is accepted (exit 0) | one fixture per rule; the two-variable and zero-variable fixtures differ only in effort |
| 6 | the committed table passes `factory_route_check docs/ledger/routing.toml` and `route.py --file … check`, and the lookups `--rung 2 implement docs XS` → `deepseek/deepseek-v4-pro-0813 off`, `--rung 2 implement code S` → `… high`, `orchestrate any any` → `… medium`, `--rung 2 review any any` → exit 3 | drop the orchestrate row → exit 0 with the default row's `medium` (same text!) — so the assertion is on `--rung 2 orchestrate any any` → `(top 1)` **and** on `grep -c 'role = "orchestrate"' docs/ledger/routing.toml` → `2`; a fixture with `rung = 2  # note` (an inline comment) is refused by both parsers with `bad value` | the committed table's own rows; the inline-comment fixture |
| 7 | bash and python print identical stdout and exit codes for the seven tuples `(implement code S · rung 1,2,3,4) (--class bash-driver implement code S) (--rung 3 --fallback implement code S) (--rung 2 --fallback implement code S)` on FX, and for `check` on each Step-5 refusal fixture (python exit 1 ↔ bash exit 3, message text equal after the prefix) | flip either implementation's tie rule or specificity count → one tuple differs | the class row and the `any` row of equal role/kind/size |
| 8 | `route.py --file docs/ledger/routing.toml models` output is byte-identical to `git show HEAD:tools/factory/route.py`'s output on `git show HEAD:docs/ledger/routing.toml` (both saved to files in the test) | `models` reading rung 2 → `reviewCode` changes | the claude rows have no rung 2, so only a reading of the wrong route or rung changes the map |
| 9 | the six claim ids exist with `status = "gap"` and `review_by = 2026-10-04` (`grep -c` over the file → 6 for the ids, and `claims.py validate --today 2026-09-06` exit 0) | drop one row → count 5 | — |

**touches:** docs/ledger/routing.toml, tools/factory/seat/factory-lib.sh, tools/factory/route.py, tests/unit/80-seat-driver.bats, docs/ledger/claims.toml, tools/factory/seat/README.md
**acceptance:** unit, factory-unit, claims-validate, lint
**commit subject:** `routing: rung, fallback and class rows form ladders in one table; factory_route --rung/--class/--fallback and route.py agree; the first rungs and their claims (test: unit, factory-unit, claims-validate, lint)`

### SD2 (code, S) — the technical class is derived from `touches`: `docs/ledger/task-classes.toml`, `tasks.py class`, the class in the graph and the brief

**dependsOn:** none

**Files:**
- Create: `docs/ledger/task-classes.toml`, `tests/evidence/fixtures/plans/classes.md`
- Modify: `pkgs/evidence/tasks.py` (`load_task_classes`, `task_class`, `scan_repo`'s task dict, `render_brief`, `check`, the `class` subcommand), `tests/evidence/test_tasks.py`

**Interfaces:**

- `docs/ledger/task-classes.toml` — `[[class]]` rows, each `name` (`^[a-z][a-z0-9-]*$`, unique) and `globs` (a non-empty list of strings). Ten rows in this order, the spec's vocabulary; the header comment states the rule below:

```toml
[[class]]
name = "nix-module"
globs = ["nixosModules/*", "hosts/*"]

[[class]]
name = "nix-check"
globs = ["flake.nix", "treefmt.toml"]

[[class]]
name = "bash-driver"
globs = ["tools/factory/seat/*", "tools/*.sh", "githooks/*"]

[[class]]
name = "python-evidence"
globs = ["pkgs/evidence/*", "tests/evidence/*", "pkgs/seat/*", "tests/seat/*", "pkgs/helm/*", "tests/helm/*", "pkgs/lane/*", "tests/lane/*", "pkgs/broker/*", "tests/broker/*", "tools/ledger/*", "tests/ledger/*", "tools/factory/route.py", "pkgs/dsh-openrouter/*.py"]

[[class]]
name = "js-workflow"
globs = ["tools/factory/*.js", "tests/factory/*", ".claude/workflows/*"]

[[class]]
name = "bats-test"
globs = ["tests/unit/*"]

[[class]]
name = "vm-test"
globs = ["tests/integration/*"]

[[class]]
name = "docs-runbook"
globs = ["docs/runbooks/*", "docs/decisions/*", "CLAUDE.md", "README.md"]

[[class]]
name = "docs-plan"
globs = ["docs/superpowers/*", "docs/reviews/*", "docs/concepts/*"]

[[class]]
name = "docs-board"
globs = ["docs/OPERATIONS.md", "docs/board/*", "docs/MAP.md", "docs/ledger/*"]
```

- **The rule** (`task_class(touches, rules) -> str`): for each `touches` path the class is the **first row in file order** any of whose globs matches the path under `fnmatch.fnmatchcase(path, glob)` (so `*` crosses `/`: `nixosModules/*` matches `nixosModules/deep/x.nix`); a path no row matches counts for nothing. The task's class is the class with the most paths; a tie goes to the class that appears **earlier in the file**; no `touches`, or no matched path, → `any`. Exactly one class per task.
- `load_task_classes(root) -> list[dict] | None`: reads `<root>/docs/ledger/task-classes.toml`; `None` when the file is absent; raises `ValueError` with one of `duplicate class NAME`, `bad class name NAME`, `class NAME: globs must be a non-empty list of strings`, `no [[class]] rows` when present but malformed.
- `scan_repo` gives every task dict a `"class"` field (the rule above, or `"any"` when the table is `None`); `tasks.py json` therefore carries it; `check` appends `tasks: docs/ledger/task-classes.toml: <reason>` when the table is present and malformed (a missing table is not an error).
- `render_brief` gains one line after **Next wave**: `**Classes (next wave):** <class> KEY KEY · <class> KEY` — the next wave's keys grouped by class in the table's order (`any` last), keys in wave order — **omitted** when the brief with the line would exceed 1,400 UTF-8 bytes (D9: the session hook's `cap_part BRIEF … 1400`); when the table is unreadable the line reads `**Classes (next wave):** unavailable`.
- `tasks.py [--root …] class --repo NAME [--plan FILE] KEY` → stdout the class, exit 0; unknown key → stderr `tasks: unknown key KEY`, exit 1; malformed table → stderr `tasks: docs/ledger/task-classes.toml: <reason>`, exit 1. Consumer: `factory-task` (SD7) through `factory_py`, degrading to `any` with a log line on any non-zero exit.
- The class enum is shared with `tools/factory/route.py`'s `CLASSES` (SD1) by name and order; the lockstep test that pins them equal lives in `tests/unit/80-seat-driver.bats` (SD7, whose sandbox holds both files — `evidence-unit` does not copy `tools/factory/route.py`).

**Facts:**

- `test -f docs/ledger/task-classes.toml && echo exists || echo MISSING` → `MISSING: docs/ledger/task-classes.toml`.
- `grep -n '^HEADING_RE = \|^FIELD_RE = \|^def touches_overlap\|^def render_brief\|^def parse_list' pkgs/evidence/tasks.py` → `HEADING_RE = re.compile(` (line 40), `FIELD_RE = re.compile(` (43), `def parse_list(value):` (110), `def touches_overlap(a, b):` (774, already `fnmatch`-based), `def render_brief(graph, claims_rows=None, today=None):` (1397) — the heading grammar and the `touches` field stay untouched.
- `grep -n 'Next wave\*\* — \|Record (7 d)' pkgs/evidence/tasks.py` → `lines.append("**Next wave** — " + …)` then `lines.append(f"**Record (7 d):** …")` — the new line goes between them.
- `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | wc -c` → `1275`; `grep -n 'cap_part BRIEF' tools/session-start.sh` → `cap_part BRIEF "$brief" 1400`.
- `grep -n 'cp -r ${self}/docs/ledger docs/ledger\|cp ${self}/docs/MAP.md' flake.nix` → `evidence-unit` copies `docs/ledger` (1140) — the committed table is under test there.
- `grep -n 'def test_brief_lists_counts_next_wave_and_operator_items\|def repo_with' tests/evidence/test_tasks.py` → the brief test idiom (`repo_with(tmp_path, ["typed.md"], landed=…, reviews=…)` then `tk.render_brief({"generated": …, "repos": [g]}, claims)`).

- [ ] **Step 1: Write the failing tests** in `tests/evidence/test_tasks.py` (one function per Tests row) and the fixture plan `tests/evidence/fixtures/plans/classes.md` with three typed tasks: `C1 (code, S)` touching `nixosModules/x.nix, tests/unit/x.bats`; `C2 (code, S)` touching `tools/factory/seat/factory-task, tools/factory/seat/factory-lib.sh, tools/factory/seat/README.md, tests/unit/80-seat-driver.bats`; `C3 (docs, XS)` with no `touches` line — each with a `commit subject`, `acceptance` (`unit, lint` for the code tasks) and `dependsOn: none`.
- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence/test_tasks.py -q -k 'class or classes' 2>&1 | tail -n 20 > .factory-scratch/red.txt; cat .factory-scratch/red.txt` → `AttributeError: module 'tasks' has no attribute 'load_task_classes'` for every new test.
- [ ] **Step 3: Implement** `load_task_classes`, `task_class`, the `class` field in `scan_repo`, the `check` rule, the brief line with its cap, the `class` subparser (`--repo` required, `--plan` optional, one positional `KEY`); write the table and its header.
- [ ] **Step 4: Run it green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q`; `git add docs/ledger/task-classes.toml tests/evidence/fixtures/plans/classes.md`; `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | wc -c` (paste; the classes line is present at this length or the cap rule omitted it — say which); `nix develop -c python3 pkgs/evidence/tasks.py --root . class --repo nixos-agent-env --plan 2026-09-06-planning-agent.md P11r` → `bash-driver`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the Global Constraints recipe over the Step 4 commands.

**Tests:**

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | `task_class(["nixosModules/x.nix", "tests/unit/x.bats"], rules)` → `nix-module` (a 1–1 tie; `nix-module` is the earlier row) | tie → the later class → `bats-test` | exactly one path per class |
| 2 | C2's four paths → `bash-driver` (3 vs 1: the README counts as `bash-driver` because that row is earlier than `docs-runbook`) | per-path "last matching row wins" → README becomes `docs-runbook`, still 3–1 — so the row also asserts `task_class(["tools/factory/seat/README.md"], rules) == "bash-driver"` | one path two rows match |
| 3 | `task_class([], rules)` → `any`; `task_class(["foo/bar.txt"], rules)` → `any` | default to the first row's class | an unmatched path |
| 4 | `task_class(["nixosModules/deep/x.nix"], rules)` → `nix-module` | `pathlib.PurePath.match` (no `/` crossing) → `any` | a nested path |
| 5 | `load_task_classes` on the committed table returns ten rows whose names equal the literal list in the Interfaces, in order | reorder two rows → the list differs | the committed file |
| 6 | a table with `nix-module` twice → `check` prints `tasks: docs/ledger/task-classes.toml: duplicate class nix-module`; a table with `globs = []` → `… globs must be a non-empty list of strings`; an absent table → `check` prints nothing and every task's class is `any` | drop the duplicate rule; treat an absent table as an error | three tables |
| 7 | the brief over `classes.md` prints `**Classes (next wave):** nix-module C1 · bash-driver C2 · any C3` | drop the grouping → `C1 nix-module` | a wave with three classes |
| 8 | a fixture plan whose next-wave keys are 30 chars each × 40 makes the brief with the line exceed 1,400 bytes → the line is omitted and `len(md.encode()) <= 1400` fails only… — assert: the line is absent **and** it is present for `classes.md` | drop the cap → the line appears in both | the long-key plan |
| 9 | `tasks.py … class --repo nixos-agent-env --plan classes.md C2` (the fixture copied into a `tmp_path` repo) → `bash-driver`, exit 0; `… NOPE` → exit 1, stderr `tasks: unknown key NOPE` | exit 0 with `any` for an unknown key | — |
| 10 | every task dict in `tasks.py json` carries `class`, equal to `task_class(t["touches"], rules)` | omit the field | C1–C3 |

**touches:** docs/ledger/task-classes.toml, pkgs/evidence/tasks.py, tests/evidence/test_tasks.py, tests/evidence/fixtures/plans/classes.md
**acceptance:** evidence-unit, lint
**commit subject:** `tasks: the technical class is derived from touches by docs/ledger/task-classes.toml — first matching row, most paths, earliest on a tie; class in the graph, the brief and a class subcommand (test: evidence-unit, lint)`

### SD3 (code, S) — one shared guard rule file: `docs/ledger/guard-rules.txt`, read by the orchestrator guard in place of its literals

**dependsOn:** none

**Files:**
- Create: `docs/ledger/guard-rules.txt`
- Modify: `tools/orchestrator-guard.sh` (`load_rules`, the arrays, the verb `case` arms, `--print-rules`), `tests/unit/91-orchestrator-guard.bats`, `docs/runbooks/session.md` (the Guard section: one paragraph)

**Interfaces:**

- **The file.** Line-oriented; blank lines and lines starting `#` are ignored; every other line is `<kind> <value> [<value>…]`, split on runs of spaces or tabs. Kinds (a closed set): `protected-abs <absolute path>` (one path per line); `protected-dir <repo-relative>`; `protected-file <repo-relative>`; `host-refuse <word>`; `systemctl-refuse <verb>…`; `git-refuse <subcommand> [<flag>]`; `verb <family> <word>…` with family ∈ `delete file truncate touch mode inplace extract copy dd find python`. The committed content is today's literals, nothing more:

```
# Guard rules shared by tools/orchestrator-guard.sh (the orchestrator's PreToolUse hook)
# and pkgs/dsh-openrouter/hook-guard.py (the seat's). Kinds: protected-abs, protected-dir,
# protected-file, host-refuse, systemctl-refuse, git-refuse, verb <family> <word>...
protected-abs /run/baskets
protected-abs /var/lib/baskets
protected-abs /var/lib/helm
protected-abs /var/lib/egress-broker
protected-abs /var/lib/lanes
protected-abs /var/lib/secrets
protected-dir docs/superpowers/plans
protected-file .claude/ritual-override
host-refuse sudo
host-refuse nixos-rebuild
systemctl-refuse start stop restart reload enable disable
git-refuse commit --amend
git-refuse push
git-refuse rebase
git-refuse reset --hard
verb delete rm mv rsync shred rmdir
verb file tee ed unlink
verb truncate truncate
verb touch touch
verb mode chmod chown chattr
verb inplace sed perl
verb extract tar unzip cpio
verb copy cp install ln
verb dd dd
verb find find
verb python python python3
```

- **The orchestrator guard** loads the file at the top of `main` (`load_rules`: `mapfile` then one `read -r -a` per line — no fork per line, so the two timing tests keep their budgets) into `PROTECTED`, `PROTECTED_PATHS` (`<path>|dir` / `<path>|file`), `HOST_REFUSE`, `SYSTEMCTL_VERBS` (joined into today's alternation), `GIT_REFUSE` (an associative array `subcommand → flag-or-empty`) and `VERB_FAMILY` (`word → family`); the literal arrays and the verb `case` arms become lookups (`case "${VERB_FAMILY[$t]:-}" in delete) … ;; file) … ;; esac`, the `python*` arm becomes `python) … ;;` with the prefix match kept by testing `${VERB_FAMILY[${t%%[0-9.]*}]}`). Every deny reason stays byte-identical; no rule's semantics change (the existing 100+ tests are the net).
- **Path and failure.** The file is `$CLAUDE_PROJECT_DIR/docs/ledger/guard-rules.txt` (the project dir, resolved as today), overridden for tests by `ORCHESTRATOR_GUARD_RULES=<path>` in the hook's own environment (the lift flag's mechanism; a `VAR=x cmd` prefix in a payload cannot reach it). A missing, unreadable or malformed file (an unknown kind, a kind with no value, a `verb` line with an unknown family, a `git-refuse` with more than one flag) is a **guard fault**: one stderr line `orchestrator-guard: rule file <path>: <reason>` and `deny "guard fault: rule file <reason>"` for every Bash/Edit/Write/MultiEdit payload; exit 0 (fail closed, CR2r3b's policy). The `ORCHESTRATOR_GUARD=off` lift still returns before the load.
- `tools/orchestrator-guard.sh --print-rules`: prints the loaded rules canonically — one `kind value…` line each, families expanded one word per line (`verb delete rm`), sorted with `LC_ALL=C sort` — exit 0, stdin untouched. SD4's parity test compares it with `hook-guard --print-rules`.
- `docs/runbooks/session.md`, Guard section: one paragraph — the file, the kinds, the fail-closed rule, the override variable.

**Facts:**

- `grep -n '^PROTECTED=(\|^PROTECTED_PATHS=(\|^HEADING_ERE=\|^      commit)\|^      push | rebase)\|^      reset)' tools/orchestrator-guard.sh` → `PROTECTED=(` (143), `PROTECTED_PATHS=(` (159), `HEADING_ERE=` (166), the git arms `commit)` (439), `push | rebase)` (447), `reset)` (451) — the literals this task moves; `HEADING_ERE` stays in the script (the heading rule is the orchestrator's alone).
- `grep -n '^PROTECTED_ABSOLUTE = ' pkgs/dsh-openrouter/hook-guard.py` → line 85, the same six paths; `grep -n 'def test_' tests/lane/test_forbidden_lists_agree.py` → `test_the_three_local_only_lists_agree` — the three-copies test the claim `forbidden-list-single-source` names; this file becomes the fourth copy's source and SD4 makes hook-guard read it (the claim closes only when the lane and the wrapper read it too — out of this plan).
- `head -1 tests/unit/91-orchestrator-guard-sweep.txt` → `# rows: 442`; `grep -n '@test "the guard never raises' tests/unit/91-orchestrator-guard.bats` → line 1405 — every row must stay stderr-silent after the refactor (the rule-file stderr line is a fault path, never reached on a sound file).
- `grep -n 'cp ${self}/tools/orchestrator-guard.sh\|cp ${self}/docs/runbooks/session.md\|cp -r ${self}/docs/ledger docs/ledger' flake.nix` → 2052, 2057, 2042 — the sandbox holds the guard, the runbook and `docs/ledger` (the rule file's home) without a `flake.nix` change.
- `cat .claude/settings.json` → `{}` in this snapshot (Assumption 8); the guard's wiring is out of scope.
- `grep -n '@test "ORCHESTRATOR_GUARD=off in the hook' tests/unit/91-orchestrator-guard.bats` → the env-flag idiom (`run --separate-stderr env ORCHESTRATOR_GUARD=off CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" <<<"$p"`) the rules-path override copies.

- [ ] **Step 1: Write the failing tests** (`tests/unit/91-orchestrator-guard.bats`, one `@test` per Tests row; fixture rule files under `$BATS_TEST_TMPDIR`, pointed at by `ORCHESTRATOR_GUARD_RULES`).
- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/91-orchestrator-guard.bats --filter 'rule file|print-rules' 2>&1 | tail -n 20 > .factory-scratch/red.txt; cat .factory-scratch/red.txt` → the third-dir test fails (`rm docs/second/plans/x.md` allows: empty `$output`), the missing-file test fails (`git status` allows), `--print-rules` fails (empty output).
- [ ] **Step 3: Implement** `load_rules`, `--print-rules`, the array/`case` replacements; write the rule file; the runbook paragraph.
- [ ] **Step 4: Run it green** — `nix develop -c shellcheck tools/orchestrator-guard.sh`; `nix develop -c bats tests/unit/91-orchestrator-guard.bats`; `git add docs/ledger/guard-rules.txt`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the Global Constraints recipe over the Step 4 commands plus `bash tools/orchestrator-guard.sh --print-rules | wc -l` (expected `45`: 6 protected-abs + 1 protected-dir + 1 protected-file + 2 host-refuse + 6 systemctl verbs + 4 git-refuse + 25 verb words).

**Tests:**

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | with a rule file that adds `protected-dir docs/second/plans`, `rm docs/second/plans/x.md` denies with the plan reason and `rm docs/third/x.md` allows | keep the literal list → the second dir allows | two directories, one in the file |
| 2 | the rule file absent → `git status` and an Edit outside the plans dir both deny with `guard fault: rule file`, one stderr line each; present → they allow | fall back to built-in lists when absent → `git status` allows | — |
| 3 | a file with `verb nonsense rm` → every payload denies (`guard fault`); a file with `git-refuse reset --hard --extra` → the same | skip unknown kinds → `git push` allows only if… the assertion is on the deny | one bad line each |
| 4 | a file without `git-refuse push` → `git push` allows; with it → denies (`history rules of the house`) | hard-code `push` → allows never happens | the same command, two files |
| 5 | a file whose `systemctl-refuse` lists only `start` → `systemctl restart x` allows and `systemctl start x` denies | hard-code the alternation → restart denies | — |
| 6 | `--print-rules` on the committed file prints 45 lines equal to the file's lines with families expanded, `LC_ALL=C sort`ed; stdin is not read (a deny payload on stdin changes nothing) | drop one family from the loader → a line missing | — |
| 7 | every pre-existing test stays green; the sweep header still reads `# rows: 442` and every row is stderr-silent (the existing test, unchanged) | any semantic drift in a `case` arm | the 442 rows |
| 8 | the two timing tests (`200-path-token … under 100 ms`, `200-symlink-token … under 200 ms`) stay green with the loader in place | load with a fork per line (`while read; do … $(…)`) → over budget | — |

**touches:** docs/ledger/guard-rules.txt, tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, docs/runbooks/session.md
**acceptance:** unit, lint
**commit subject:** `guard: the orchestrator guard reads docs/ledger/guard-rules.txt — protected paths, host verbs, git and write-verb families as data, fail closed on a bad file, --print-rules (test: unit, lint)`

### SD4 (code, M) — the seat's hook guard reads the shared rule file: history rewrites, protected-path writes and append-only headings refused for the seat too; the sweep runs against both guards

**dependsOn:** SD3

**Files:**
- Modify: `pkgs/dsh-openrouter/hook-guard.py` (the loader, the bash tokeniser and the write rules, the edit/write plan rules, `--print-rules`), `pkgs/dsh-openrouter/default.nix` (`runtimeEnv.DSH_GUARD_RULES`), `pkgs/dsh-openrouter/dsh-openrouter.sh` (`hook_command` gains `--rules`), `tests/unit/70-dsh-openrouter.bats`, `tests/unit/91-orchestrator-guard.bats` (the parity sweep), `docs/runbooks/lanes.md` (the hook-set bullet list: the new rules)

**Interfaces:**

- `hook-guard [--routing-table PATH] [--rules PATH] [--print-rules]`. The rules path: `--rules`, else `$DSH_GUARD_RULES`, else `$HOME/nixos-agent-env/docs/ledger/guard-rules.txt` (the routing table's own three-step resolution). The wrapper passes `--rules "$guard_rules"` with `guard_rules=${DSH_GUARD_RULES:?dsh-openrouter: DSH_GUARD_RULES must name the guard rule file}` from `runtimeEnv.DSH_GUARD_RULES = "${../../docs/ledger/guard-rules.txt}"` — the store copy, so the seat's rules change only by a switch (D8). The grammar is SD3's; `--print-rules` prints the same canonical lines as `tools/orchestrator-guard.sh --print-rules`.
- **Failure contract, extended from the model rule's:** a rule file that is missing, unreadable, not UTF-8 or malformed (SD3's reasons) denies every `bash`, `edit`, `write`, `subagent`, `subagent_fork` and `workflow` payload with `guard rules could not be loaded: <reason>` (stdout deny JSON, stderr record, exit 0). The payload-parse contract (RT5rb) is unchanged and runs first.
- **Bash rules** (after today's `_bash_verdict`, before `_bash_model_verdict`), each fed by the file and each with the orchestrator guard's message byte for byte:
  1. `host-refuse` words replace the literal in `_SUDO`/`_NIXOS_REBUILD` (one compiled pattern per word, today's command-position class `(?:^|[;&|\n()])\s*WORD(?=\s|$)`); `systemctl-refuse` verbs build `_SYSTEMCTL`'s alternation. Messages unchanged (`sudo is refused (an operator action)` …).
  2. **History rewrites.** The command is folded to the orchestrator guard's token stream — `\`+newline to a space, tabs and newlines to spaces, the quote characters `"` `'` `` ` `` deleted, `&&`→`&`, `||`→`|`, `>|` and `>>`→`>`, then `; & | > ( ) { }` padded into their own tokens — and **every** token whose basename (after one leading `\`) is `git` marks an invocation; its subcommand is the first later token not starting `-` and not the value of `-c -C --git-dir --work-tree --exec-path --namespace --config-env --super-prefix`; a `git-refuse` entry denies when the subcommand matches and, when the entry names a flag, that flag appears among the later tokens: `git commit --amend is refused (history rules of the house)`, `git push is refused (…)`, `git rebase is refused (…)`, `git reset --hard is refused (…)`.
  3. **Protected writes.** `protected-dir` (plan files: `*.md` directly under it; the directory and every ancestor down to the project dir and `/` name every plan for the delete family) and `protected-file` (the file; its parent and every ancestor for the delete family; a glob token — `*?[{` — under the parent names it), resolved lexically against the project dir (`CLAUDE_PROJECT_DIR` or the cwd, today's `_edit_verdict` base), the payload's `cwd` when present, and every `cd`/`pushd` argument, with `..`, `.`, `//`, `~` collapsed and one `realpath` for a symlink token. The verb families from the file carry the orchestrator guard's semantics: `delete` (any protected path or ancestor named anywhere → deny; `xargs` in the clause with a descendant of the protected file's parent → deny), `file` and `truncate` (the exact file; truncate joins the delete family for the protected file), `touch` (the file), `mode` (the file or its parent), `inplace` (a `-i*`/`--in-place*` token in the same clause), `extract` (`tar` with `-x*`/`--extract`, `cpio` with `-*i*`, `unzip` always; the `-C`/`-d` destination, else the clause's cwd base, judged against the protected dirs), `copy` (the destination = the last non-option token before the next separator), `dd` (`of=`), `find` (`-delete`/`-exec` in the clause), `python` (`write_text`/`open(…,"w")` in the raw text naming a plan; `os.remove|os.unlink|unlink(|os.rename|os.replace|shutil.move|shutil.rmtree` naming the protected file or its parent); the `>` redirect's target; `git checkout|restore` on a protected path or a bare `--`/`.`; `git clean` only with `-f` (pathless or protected); `git stash` only with `-u`/`-a`/`--include-untracked` (pathless or protected); a `git commit -m|--message|-am` message's quoted run is prose and never scanned, in the space and glued forms. Clauses split on unquoted `;`, `&`, `|` and newlines, so a flag arms only its own clause. Messages: `plan files change only through the Edit and Write tools (append-only headings) — see docs/runbooks/session.md`; `the ritual override is the operator's; ask for it`.
- **Edit/write rules** (before today's project-dir check): a resolved `file_path` equal to a `protected-file` → `the ritual override is the operator's; ask for it`; a plan file (`*.md` directly under a `protected-dir`) → the append-only rule: the before-text is the file's current content (empty when absent), the after-text is `content` (write) or before with the first occurrence of `old_string` replaced by `new_string` (edit); every line of before matching `^### [A-Za-z][A-Za-z0-9-]* \((code|docs), (XS|S|M|L)\) [—-] .+$` must appear in after, else `typed task headings are append-only — withdraw a task with a status row in docs/ledger/task-status.toml, not by editing docs/superpowers/plans/…`; a payload without the field the rule needs → `plan edit could not be evaluated: missing content` / `… missing old_string` (fail closed, the model rule's policy).
- Everything else stays: the protected prefixes now come from `protected-abs` (the same six), the key-file and Helm-port rules, the sub-agent model rule, the stderr record, `main()` returning 0 on every path.
- The parity sweep (in `tests/unit/91-orchestrator-guard.bats`, beside the existing sweep test): for every data row of `91-orchestrator-guard-sweep.txt`, the orchestrator guard's decision (deny when stdout is non-empty) equals `hook-guard --rules <the committed file>`'s decision on `{"hook_event_name":"PreToolUse","tool_name":"bash","tool_input":{"command":<row>}}` with `CLAUDE_PROJECT_DIR=$PROJECT`; the first differing row is printed and the test fails. Both guards see the same fixture project (`$PROJECT` with its `docs/superpowers/plans/test.md`).

**Facts:**

- `grep -n '^def _bash_verdict\|^def _edit_verdict\|elif tool in ("edit", "write")\|^PROTECTED_ABSOLUTE = \|^_SUDO = \|^_SYSTEMCTL = ' pkgs/dsh-openrouter/hook-guard.py` → 217, 438, 574, 85, 97, 102 — the seams; today's bash rules are `_bash_verdict` (sudo, nixos-rebuild, systemctl, Helm port, key file) and `_bash_model_verdict`; no git or write-verb rule exists.
- `grep -n 'hook_command=$(jq -n --arg g "$hook_guard" --arg t "$routing_table"' pkgs/dsh-openrouter/dsh-openrouter.sh` → the one place the guard's argv is composed (`("exec " + ($g | @sh) + " --routing-table " + ($t | @sh))`); `grep -n 'hookGuard = \|DSH_HOOK_GUARD = ' pkgs/dsh-openrouter/default.nix` → `hookGuard = writePython3MinimalBin "hook-guard" {` (64) and `DSH_HOOK_GUARD = "${hookGuard}/bin/hook-guard";` (82) — the script is embedded from `./hook-guard.py`, stdlib on `python3Minimal` (`host-core` asserts `guardPython`).
- `grep -n 'run --separate-stderr hook-guard <<< "$1"\|^guard_payload()\|^guard_allows()' tests/unit/70-dsh-openrouter.bats` → the idiom: `hook-guard` on PATH in the `unit` sandbox (`dshOpenrouter` in its `nativeBuildInputs`), payloads from `guard_payload <tool> '<json tool_input>'`.
- `head -1 tests/unit/91-orchestrator-guard-sweep.txt` → `# rows: 442`; the sweep holds allow rows (`git status`, `cat docs/OPERATIONS.md`, `nix develop -c git commit -q -F /tmp/msg`, `git commit -m 'x'`) and deny rows (`rm -rf .claude/*`, `git push`, `sudo rm -rf .claude`) — the parity test is over decisions, not over "every row denies".
- `grep -c '^@test' tests/unit/91-orchestrator-guard.bats` and `grep -c '^@test "hook-guard' tests/unit/70-dsh-openrouter.bats` → the two suites this task keeps green (paste the counts in the commit body).
- `grep -n 'a deny-only hook set (`pkgs/dsh-openrouter/hook-guard.py`) refuses' docs/runbooks/lanes.md` → the runbook bullet that lists the seat's rules (extend it; the `--denials` reader is unchanged).

- [ ] **Step 1: Write the failing tests** — `tests/unit/70-dsh-openrouter.bats`: one `@test` per Tests row 1–8 and 10 (payloads through `guard_payload`, `--rules` pointing at the committed file via `hook-guard --rules "$RULES"` where `RULES="$BATS_TEST_DIRNAME/../../docs/ledger/guard-rules.txt"`, `CLAUDE_PROJECT_DIR` a fixture project with `docs/superpowers/plans/test.md` copied from 91's `setup()`); `tests/unit/91-orchestrator-guard.bats`: the parity sweep (row 9).
- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/70-dsh-openrouter.bats --filter 'history|plan file|override|print-rules|rules could not' 2>&1 | tail -n 20 > .factory-scratch/red.txt; cat .factory-scratch/red.txt` → `git commit --amend` allows (empty output) where a deny was asserted, `rm docs/superpowers/plans/x.md` allows, `--print-rules` prints nothing; then `nix develop -c bats tests/unit/91-orchestrator-guard.bats --filter parity 2>&1 | tail -n 5 >> .factory-scratch/red.txt` → the first differing row is `rm -rf .claude/*` (bash denies, hook-guard allows).
- [ ] **Step 3: Implement** in `hook-guard.py`: `_load_rules(path) -> dict` (SD3's grammar, raising `_RulesError(reason)`), `_tokenise(command) -> (tokens, quoted, nlsep)`, `_git_verdict`, `_write_verdict` (the family semantics above), `_plan_edit_verdict`, `_print_rules`; wire them into `main` after the payload parse; the wrapper's `--rules`; `runtimeEnv.DSH_GUARD_RULES`. Keep the file stdlib-only.
- [ ] **Step 4: Run it green** — `nix develop -c ruff format pkgs/dsh-openrouter`; `nix develop -c shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh`; `nix develop -c bats tests/unit/70-dsh-openrouter.bats tests/unit/91-orchestrator-guard.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `… host-core`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the Global Constraints recipe over the Step 4 commands plus `diff <(bash tools/orchestrator-guard.sh --print-rules) <(nix develop -c hook-guard --rules docs/ledger/guard-rules.txt --print-rules) && echo identical`.

**Tests:**

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | deny with `history rules of the house`: `git commit --amend`, `git push --dry-run`, `nix develop -c git commit --amend`, `git -c a=b -C . push`, `\git push`, `` `git push` ``, `git status; git push`, `git commit \`+newline+`--amend`; allow: `git commit -F msg`, `git status; git log`, `git -c a=b status` | skip only `-x` options, not `-c`'s value → `git -c a=b push` reads `a=b` as the subcommand and allows | `git -c a=b -C . push` |
| 2 | deny with the plan message: `sed -i 's/x/y/' docs/superpowers/plans/x.md`, `rm docs/superpowers/plans/x.md`, `mv a docs/superpowers/plans/x.md`, `cp a docs/superpowers/plans/x.md`, `echo x > docs/superpowers/plans/x.md`, `truncate -s 0 docs/superpowers/plans/x.md`, `printf x \| tee docs/superpowers/plans/x.md`, `cat > docs/superpowers/plans/../plans/x.md`, `perl -i -pe s/x/y/ docs/superpowers/plans/x.md`, `git checkout -- docs/superpowers/plans/x.md`, `cd docs/superpowers/plans && rm x.md`, `rm -rf docs`; allow: `cat docs/superpowers/plans/x.md`, `grep -n '^### ' docs/superpowers/plans/x.md`, `cp docs/superpowers/plans/x.md /tmp/y`, `cd /tmp && rm x.md`, `rm /tmp/plans-not-ours/x.md` | drop the `..` collapse → the `../plans` spelling allows; drop the ancestor rule → `rm -rf docs` allows | the `../plans` and `rm -rf docs` spellings |
| 3 | deny with the override message: `touch .claude/ritual-override`, `rm -rf .claude`, `rm -rf .claude/*`, `git clean -fd`, `git stash -u`, `chmod 000 .claude`, `tar -C .claude -xf a.tar`, `dd if=/dev/null of=.claude/ritual-override`, `python3 -c 'import os;os.remove(".claude/ritual-override")'`; allow: `cat .claude/ritual-override`, `git clean -n`, `git stash`, `rm -rf .claude/worktrees/x`, `rm /tmp/other/.claude/ritual-override` | drop the glob fallback → `rm -rf .claude/*` allows; drop the parent rule → `rm -rf .claude` allows | the glob spelling; the sibling `worktrees/x` that must allow |
| 4 | `git commit -m 'rm -rf .claude no longer allowed'` and `git commit -am 'fix rm -rf .claude'` allow; `git commit -m x`+newline+`rm -rf .claude` and `git commit -m rm .claude/ritual-override` deny | exempt to the end of the command → the newline case allows | the newline case |
| 5 | Write dropping `### A1 (code, S) — first task` from `test.md` → deny (heading message); Write appending `### C3 …` → allow; Edit removing the heading → deny; Edit of `body one line` → allow; a Write payload on a plan without `content` → deny `plan edit could not be evaluated: missing content`; an Edit without `new_string` → `… missing old_string`-or-`new_string` (the first missing) | allow on a missing field | the field-less payload |
| 6 | Write/Edit on `.claude/ritual-override` (relative and absolute under `$PROJECT`) → deny; on `docs/other.md` holding a heading → allow | resolve absolute paths only → the relative spelling allows | the relative path |
| 7 | `--rules /nonexistent`: `git status`, an Edit inside the project and `subagent {"prompt":"x"}` all deny with `guard rules could not be loaded: `; a file with `verb nonsense rm` → the same with the SD3 reason | allow when the file is missing | — |
| 8 | `hook-guard --rules <committed> --print-rules` is byte-identical to `bash tools/orchestrator-guard.sh --print-rules` (the `unit` sandbox holds both) | expand a family in a different order | — |
| 9 | the parity sweep: 442 rows, identical decisions; the test prints `row N differs: <command> (orchestrator: deny, hook-guard: allow)` on the first difference | any rule ported loosely | the 442 rows — the corpus of every spelling eight gate rounds collected |
| 10 | the wrapper's `hooks.json` command carries `--rules` followed by a readable path that ends in `guard-rules.txt` and equals `$DSH_GUARD_RULES` (the `--dump-config` or `hooks.json` idiom the RT5rb tests use) | drop the flag → the guard falls back to `$HOME/nixos-agent-env/…` (absent in the sandbox → the fallback would deny everything — so the assertion is on the flag's presence, not on a decision) | — |
| 11 | every pre-existing `hook-guard` test in 70 and every test in 91 stays green; `main()` exits 0 on every payload of the sweep (no traceback on stderr: the stderr record is JSON — assert each stderr line parses as JSON or is empty) | a raise on a hostile token → a traceback | the sweep |

**touches:** pkgs/dsh-openrouter/hook-guard.py, pkgs/dsh-openrouter/default.nix, pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats, tests/unit/91-orchestrator-guard.bats, docs/runbooks/lanes.md
**acceptance:** unit, host-core, lint
**commit subject:** `dsh: hook-guard reads docs/ledger/guard-rules.txt — history rewrites, protected-path writes and append-only plan headings refused for the seat; the sweep decides identically under both guards (test: unit, host-core, lint)`

### SD5 (code, M) — the spool: `seat-spool.path` starts every valid ready job, `seat@` loses `/run/dbus`, `seat-submit --spool`, a per-job `timeout` enforced by `seat-run`

**dependsOn:** none

**Files:**
- Create: `pkgs/seat/seat-spool.py`, `tests/seat/test_seat_spool.py`
- Modify: `nixosModules/seatLane.nix` (the path and service units, `InaccessiblePaths`, `SEAT_SPOOL`), `pkgs/seat/seat-submit.py` (`--spool`, `timeout`, the ready marker), `pkgs/seat/seat-run.py` (the timeout), `pkgs/seat/default.nix` (`seat-spool`), `tests/seat/test_seat_submit.py`, `tests/seat/test_seat_run.py`, `tests/integration/seat-vm.nix` (steps 8–9), `flake.nix` (`seat-eval` assertions; `inherit (seatTools) … seat-spool`)

**Interfaces:**

- `seat-submit [--jobs-dir DIR] [--no-start | --spool] {headless|web} …` — `--spool` and `--no-start` are mutually exclusive (exit 2, `seat-submit: --spool and --no-start are exclusive`). `job.json` gains `"timeout": <int>` (seconds, from `--timeout`, default 10800) on every path. `--spool` writes `job.json`, then `brief.txt` when given, then **last** the ready marker `<jobs-dir>/<id>.ready` (empty, mode 0600, created by a function `_mark_ready(jobs_dir, job_id)`), never calls `systemctl`; headless then polls `result.txt` as today and streams `stdout.txt`/`exit_code.txt`; on the deadline it prints `seat-submit: timed out waiting for <result.txt>; the unit ends at its own deadline (job timeout)` and exits 124 **without** a `systemctl stop`; web returns 0 after the marker. Today's path (neither flag) and `--no-start` never write a marker and are otherwise unchanged (their tests stay byte-identical).
- `seat-spool [--jobs-dir DIR] [--port-range A-B] [--systemctl CMD]` (`pkgs/seat/seat-spool.py`, stdlib; `--systemctl` and `--jobs-dir` are test seams, the module passes `--port-range`). For every `<jobs-dir>/<id>.ready`, in name order: validate (below); valid → run `[CMD, "start", f"seat@{id}"]` with `check=False` and write `<jobs-dir>/<id>/spool.txt` = `started <UTC RFC3339>\n`; invalid → write `spool.txt` = `refused <reason>\n` and print `seat-spool: <id>: refused <reason>` on stderr; a marker whose `<jobs-dir>/<id>` is not a directory → stderr `seat-spool: <id>: no job directory`; **in every case the marker is removed**. Exit 0 always. It never opens `brief.txt` (existence only), never reads the workspace.
- Validation, first failure wins, reason strings exact: (v1) `<id>` matches `^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$` → `bad id`; (v2) `job.json` parses to a JSON object → `job.json: unreadable` / `job.json: not an object`; (v3) keys ⊆ `{mode, workspace, dsh_home, model, effort, brief, port, submitted, timeout, route}` and `mode workspace dsh_home model effort brief port submitted` all present → `unknown key K` / `missing key K`; (v4) `mode` ∈ `headless|web|drive` → `mode: not in enum (headless|web|drive)`; (v5) `workspace` absolute and a directory → `workspace: not a directory`; (v6) `dsh_home` absolute → `dsh_home: not absolute`; (v7) `model` matches `^[A-Za-z0-9._:/-]+$` → `model: bad id`; (v8) `effort` ∈ `off|low|medium|high|xhigh` → `effort: not in enum (…)`; (v9) headless → `brief == "brief.txt"` and `<id>/brief.txt` exists (`brief: missing`) and `port` is `null` (`port: must be null for headless`); web/drive → `brief` is `null` (`brief: must be null for web`) and `port` is an int with `A <= port <= B` → `port: outside A-B`; (v10) `timeout` absent or an int in `1..86400` → `timeout: not 1..86400`; (v11) `submitted` a string → `submitted: not a string`. SD6 appends v12 for `drive`.
- `seat-run`: `timeout = job.get("timeout")`; `subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)`; on `subprocess.TimeoutExpired` the partial `exc.stdout`/`exc.stderr` (`""` when `None`) are written as today's files, `exit_code.txt` is `124`, `result.txt` is `_extract_result(partial stdout)`, the return is 124. A job without `timeout` runs unbounded (jobs written before this lands).
- `nixosModules/seatLane.nix`: `systemd.services."seat@"`: `serviceConfig.InaccessiblePaths = [ "/var/lib/secrets" "-/run/dbus" ]` (D6: the unit cannot reach the system bus, so `systemctl` inside it fails; the `-` tolerates a machine without D-Bus), `environment.SEAT_SPOOL = "1"` (read by `factory-task` in SD7). New units: `systemd.paths.seat-spool` (`wantedBy = [ "multi-user.target" ]`; `pathConfig.PathChanged = "/var/lib/seat/jobs"`, `pathConfig.PathExistsGlob = "/var/lib/seat/jobs/*.ready"` — the second re-fires after a reboot with a marker left behind; no loop is possible because the service consumes every marker) and `systemd.services.seat-spool` (`serviceConfig = { Type = "oneshot"; ExecStart = "${seatSpool}/bin/seat-spool --port-range ${cfg.webPortRange}"; ProtectSystem = "strict"; ReadWritePaths = [ "/var/lib/seat/jobs" ]; NoNewPrivileges = true; }` — root, no `User`; the one host-side actor). The polkit rule stays (the operator's own `systemctl start seat@…`). The module header states the design in three sentences.
- `flake.nix` `seat-eval` gains: `builtins.match "^/nix/store/[^ ]*/bin/seat-spool --port-range [0-9]+-[0-9]+$" c.systemd.services.seat-spool.serviceConfig.ExecStart != null` ("no shell, one program"); `c.systemd.services.seat-spool.serviceConfig ? User == false`; `c.systemd.paths.seat-spool.pathConfig.PathChanged == "/var/lib/seat/jobs"` and `.PathExistsGlob == "/var/lib/seat/jobs/*.ready"`; `lib.elem "-/run/dbus" sc.InaccessiblePaths`; `unit.environment.SEAT_SPOOL == "1"`; and the template pinned: `sc.ReadWritePaths == [ "/var/lib/seat" "-/home/dalhaka/factory" "-/home/dalhaka/nixos-agent-env" "-/home/dalhaka/flakes" "-/home/dalhaka/.local/share/dsh-openrouter" ]` (the spec's "the drive job inherits the template's ReadWritePaths unchanged" — one unit serves every mode). `packages` gains `seat-spool`.
- `tests/integration/seat-vm.nix`, after step 7: **(8)** `su - dalhaka -c 'seat-submit --spool headless --workspace /tmp/ws --dsh-home /tmp/dsh --model deepseek/deepseek-v4-flash --effort off --brief /tmp/brief --timeout 600'` → `vm-seat-answer` in the output; `spool.txt` begins `started`; `test ! -e /var/lib/seat/jobs/<id>.ready`; `systemctl show seat@<id> -p Result --value` = `success`; `systemctl show seat@<id> -p InaccessiblePaths --value` contains `/run/dbus`. **(9)** as dalhaka: `mkdir -m 700 /var/lib/seat/jobs/20260906-000000-badbad && printf '{"mode":"rocket"}' > /var/lib/seat/jobs/20260906-000000-badbad/job.json && touch /var/lib/seat/jobs/20260906-000000-badbad.ready`; `wait_until_succeeds("test -f /var/lib/seat/jobs/20260906-000000-badbad/spool.txt")`; `grep -q '^refused unknown key\|^refused missing key\|^refused mode:' spool.txt` (v3 fires first: `missing key workspace`); `test ! -e …badbad.ready`; after `machine.sleep(5)`: `ls /var/lib/seat/jobs/20260906-000000-badbad` prints exactly `job.json` and `spool.txt` (no `stdout.txt`, no `exit_code.txt`: the unit never started).

**Facts:**

- `grep -n 'ReadWritePaths = \[\|InaccessiblePaths = \[\|NetworkNamespacePath\|ExecStart = \|"d /var/lib/seat' nixosModules/seatLane.nix` → tmpfiles `d /var/lib/seat 0750 …` (123) and `d /var/lib/seat/jobs 0700 …` (124), `NetworkNamespacePath = netnsPath;` (176), `ExecStart = "${seatRun}/bin/seat-run %i";` (177), `ReadWritePaths = [` (186), `InaccessiblePaths = [ "/var/lib/secrets" ];` (197); `grep -n 'manage-units\|verb == "start"' nixosModules/seatLane.nix` → the polkit rule (231, 236) stays.
- `grep -n 'systemctl", "start"\|systemctl", "stop"\|args.no_start\|^DEFAULT_TIMEOUT\|^POLL_INTERVAL\|choices=\["headless", "web"\]\|"mode": args.mode' pkgs/seat/seat-submit.py` → `DEFAULT_TIMEOUT = 10800` (36), `POLL_INTERVAL = 2` (37), `p.add_argument("mode", choices=["headless", "web"])` (44), `"mode": args.mode,` (80), `if args.no_start:` (104), `subprocess.run(["systemctl", "start", …` (112), `… "stop", …` (125) — the two systemctl calls this task routes around under `--spool`.
- `grep -n 'subprocess.run(cmd\|^JOBS_DIR = \|def _extract_result' pkgs/seat/seat-run.py` → `JOBS_DIR = "/var/lib/seat/jobs"` (28), `def _extract_result(stdout_text):` (42), `proc = subprocess.run(cmd, capture_output=True, text=True, check=False)` (113) — no timeout today.
- `grep -n 'hasInfix "/bin/seat-run %i"\|elem "/var/lib/secrets" sc.InaccessiblePaths' flake.nix` → 1696 and 1691, the `seat-eval` idiom (`c = self.nixosConfigurations.core.config; unit = c.systemd.services."seat@"; sc = unit.serviceConfig`).
- `grep -n 'inherit (seatTools) seat-submit seat-run\|seatSubmit = seatTools.seat-submit' flake.nix` → 676 (packages) and 1748 (`seat-vm`'s argument); `grep -n 'runtimeInputs = \[ python3 \]' pkgs/seat/default.nix` → both scripts are `writeShellApplication` wrappers over `python3 ${./x.py}` — `seat-spool` follows.
- `grep -n "su - dalhaka -c 'seat-submit headless\|systemctl show 'seat@{job_id}.service' -p Result" tests/integration/seat-vm.nix` → 235, 244 — the VM's submission and result idiom (headless step 1) that steps 8–9 copy.
- `grep -n 'def _no_systemctl\|def _run_fake\|def test_timeout_exits_124_and_stops_the_unit\|def test_no_start_never_calls_systemctl' tests/seat/test_seat_submit.py tests/seat/test_seat_run.py` → the fixtures: `_no_systemctl` records every `subprocess.run` argv; `_run_fake(stdout, returncode, seen)`; the timeout test pins `["systemctl","stop",…]` for today's path (unchanged) and the `--no-start` test pins "nothing further".
- `grep -n 'seat-submit is a flake package but not on the host PATH' docs/OPERATIONS.md` → the board's finding at switch #20: the operator runs it as `nix run ~/nixos-agent-env#seat-submit -- …` (the Operator section's command shape).

- [ ] **Step 1: Write the failing tests** — `tests/seat/test_seat_spool.py` (rows 1–5, loading `seat-spool.py` by path as `test_seat_run.py` loads `seat-run.py`; a fake `--systemctl` recorder script under `tmp_path`), the `--spool`/`timeout`/marker tests in `test_seat_submit.py` (rows 6–9), the timeout tests in `test_seat_run.py` (row 10), the `seat-eval` assertions (row 11), the VM steps (row 12).
- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/seat -q -k 'spool or timeout or ready or exclusive' 2>&1 | tail -n 20 > .factory-scratch/red.txt; cat .factory-scratch/red.txt` → `FileNotFoundError: … pkgs/seat/seat-spool.py` at import; `SystemExit: 2` from argparse (`unrecognized arguments: --spool`); `AssertionError` on `timeout` in the `subprocess.run` kwargs; then `nix build .#checks.x86_64-linux.seat-eval -L --no-link 2>&1 | tail -n 5 >> .factory-scratch/red.txt` → `attribute 'seat-spool' missing`.
- [ ] **Step 3: Implement** `seat-spool.py`, the `seat-submit` and `seat-run` changes, `pkgs/seat/default.nix`, the module, the `seat-eval` assertions, the VM steps.
- [ ] **Step 4: Run it green** — `nix develop -c ruff format pkgs/seat tests/seat`; `nix develop -c pytest tests/seat -q`; `git add pkgs/seat/seat-spool.py tests/seat/test_seat_spool.py`; `nix build .#checks.x86_64-linux.seat-unit -L --no-link`; `… seat-eval`; `… host-core`; `… seat-vm` (minutes; paste its last 5 lines); `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the Global Constraints recipe over the Step 4 commands (the `seat-vm` line included).

**Tests:**

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | a valid headless job dir plus `<id>.ready` → the fake systemctl records exactly `start seat@<id>` once; `spool.txt` begins `started `; the marker is gone; exit 0 | keep the marker → present; start twice → two lines | one job |
| 2 | a second run over the same dir records no call (no marker left) | key on `job.json` existence instead of the marker → a second start | the same dir twice |
| 3 | one fixture per rule v1–v11 (a dir named `nope`; a non-JSON file; a JSON list; an extra key `evil`; `model` missing; `mode: "rocket"`; `workspace` a file; `dsh_home: "rel"`; `model: "a b"`; `effort: "max"`; headless with `port: 43201`; web with `brief: "brief.txt"`; web `port: 43199` and `port: 43300` against `--port-range 43200-43299` (both refused) while `43200` and `43299` start; `timeout: 0` and `86401`; `submitted: 3`) → `refused <reason>` in `spool.txt`, the reason string exact, no systemctl call, the marker gone | delete any one rule → its fixture starts | the port boundaries; the `evil` key beside a complete valid job |
| 4 | a marker without a job dir → stderr `no job directory`, the marker removed, no call | leave the marker → a second run reports it again | — |
| 5 | `brief.txt` with mode `000` (skipped when running as root) still validates: the spool never opens it | read the brief → `PermissionError` | — |
| 6 | `--spool headless`: `_no_systemctl` records nothing; `job.json` carries `"timeout": 10800` (default) or the `--timeout` value; `brief.txt` present; `<id>.ready` present; the monkeypatched `_mark_ready` asserts `job.json` and `brief.txt` already exist when it is called; the poll finds the result (the `sleep` stand-in writes it) and the exit code propagates | mark ready before writing the brief → the stand-in's assertion fails | the ordering assertion inside `_mark_ready` |
| 7 | `--spool headless --timeout 1` with no result → exit 124, stderr contains `own deadline`, `_no_systemctl` records nothing (no stop) | call `systemctl stop` → one call recorded | — |
| 8 | `--spool --no-start` → exit 2, stderr `exclusive`, no job dir created | accept both → a job dir | — |
| 9 | today's path still records `start`, writes no marker, and `timeout` is in `job.json`; `--no-start` writes no marker (the existing tests, plus a `not (jobs / f"{id}.ready").exists()` line in each) | write the marker on every path → the two assertions fail | — |
| 10 | `seat-run` on a job with `"timeout": 600` passes `timeout=600` to `subprocess.run` (the fake records kwargs); a fake raising `subprocess.TimeoutExpired(cmd, 600, output="partial\n", stderr="")` → `exit_code.txt` `124`, `stdout.txt` `partial\n`, `result.txt` `status=failed`, return 124; a job without `timeout` passes `timeout=None` | drop the kwarg; swallow `TimeoutExpired` as exit 0 | the raising fake |
| 11 | `seat-eval`: each new assertion, independently: remove `-/run/dbus` → the build fails naming InaccessiblePaths; change `ExecStart` to `"${pkgs.bash}/bin/sh -c …"` → the match fails; drop `SEAT_SPOOL` → fails; reorder `ReadWritePaths` → fails | as listed | the rendered `core` config |
| 12 | `seat-vm` steps 8–9 as in the Interfaces | drop the path unit → step 8's `spool.txt` never appears (the `wait_until_succeeds` times out); skip v3–v4 → the bad job starts and `stdout.txt` appears | the `rocket` job |

**touches:** nixosModules/seatLane.nix, pkgs/seat/seat-spool.py, pkgs/seat/seat-submit.py, pkgs/seat/seat-run.py, pkgs/seat/default.nix, tests/seat/test_seat_spool.py, tests/seat/test_seat_submit.py, tests/seat/test_seat_run.py, tests/integration/seat-vm.nix, flake.nix
**acceptance:** seat-eval, seat-unit, seat-vm, host-core, lint
**commit subject:** `seat: seat-spool.path starts every valid ready job and nothing else, seat@ loses /run/dbus, seat-submit --spool, a per-job timeout seat-run enforces (test: seat-eval, seat-unit, seat-vm, host-core, lint)`

### SD6 (code, S) — the `drive` job: `seat-submit drive` resolves the `orchestrate` row and requires the driver's skill set; `seat-run` hands the web seat its model and effort

**dependsOn:** SD1, SD5

**Files:**
- Modify: `pkgs/seat/seat-submit.py` (mode `drive`, the lookup, the preconditions, `route`), `pkgs/seat/seat-run.py` (the `drive` argv), `pkgs/seat/seat-spool.py` (v12), `pkgs/seat/default.nix` (`runtimeEnv.SEAT_ROUTE_PY`), `tests/seat/test_seat_submit.py`, `tests/seat/test_seat_run.py`, `tests/seat/test_seat_spool.py`, `tests/integration/seat-vm.nix` (step 10)

**Interfaces:**

- `seat-submit [--jobs-dir DIR] [--no-start | --spool] drive --workspace PATH --dsh-home PATH --port N [--model ID --effort LEVEL] [--timeout S] [--routing-table FILE] [--route-py FILE]`:
  - `--brief` → exit 2 `seat-submit: --brief is not accepted for drive`; `--port` missing → exit 2 `seat-submit: drive needs --port`; `--port` not an integer in `1024..65535` → exit 2 `seat-submit: --port must be an integer 1024-65535`.
  - `--dsh-home` must be a directory holding a readable `skills/driving/SKILL.md` → else exit 2 `seat-submit: --dsh-home <path> carries no driving skill (skills/driving/SKILL.md): deploy the harness catalog first` (headless/web keep today's absent check). The wrapper only warns on a missing catalog (`warn_missing_payload`), hence the refusal here.
  - Model and effort: both given → `"route": "explicit"`; both omitted → `python3 <route.py> --file <table> lookup openrouter orchestrate any any` with `route.py` from `--route-py`, else `$SEAT_ROUTE_PY` (the package's `runtimeEnv.SEAT_ROUTE_PY = "${../../tools/factory/route.py}"`), else `~/nixos-agent-env/tools/factory/route.py`, and the table from `--routing-table`, else `$FACTORY_ROUTING_TABLE`, else `~/nixos-agent-env/docs/ledger/routing.toml`; stdout must be exactly two tokens → `model`, `effort`, `"route": "orchestrate/any/any"`; a non-zero exit or any other shape → exit 3 `seat-submit: the orchestrate row could not be resolved: <the lookup's stderr>` (no built-in default — the table is the one home); one of the two given → exit 2 `seat-submit: --model and --effort go together`. `job.json` for `drive`: `mode: "drive"`, `brief: null`, `port: N`, `route`, `timeout`, the rest as today.
- `seat-run`, `mode == "drive"`: `["dsh-openrouter", "--broker", "--model", job["model"], "--bind-namespace", <SEAT_NAMESPACE_ADDRESS>, "--", "--no-open", "--port", str(port)]`; `url.txt` and the printed URL as for web; `OPENROUTER_REASONING_EFFORT` from `job["effort"]` as today. The wrapper's `--model` rewrites the saved selection **of this job's `DSH_HOME`** (`model_explicit=1`), so the operator's interactive home is untouched.
- `seat-spool` v12: `mode == "drive"` → `route` present and in `explicit|orchestrate/any/any` → else `route: missing` / `route: not in enum (explicit|orchestrate/any/any)`; headless/web → `route` absent or `explicit`.
- `seat-vm` step **10**: a fixture driver home `/tmp/drive-home/skills/driving/SKILL.md` (one line); `su - dalhaka -c 'seat-submit drive --workspace /tmp/ws --dsh-home /tmp/drive-home --port 43202 --model deepseek/deepseek-v4-flash --effort off'` → `url.txt` = `http://10.100.4.2:43202`; the host's `curl` reaches it; inside the namespace `ss -ltn` lists `127.0.0.1:43202` and `10.100.4.2:43202`, never `0.0.0.0:43202`; `systemctl show seat@<drive-id> -p ReadWritePaths --value` equals the same property of the web job of step 6 (one template, no per-mode widening). Then `machine.fail("su - dalhaka -c 'seat-submit drive --workspace /tmp/ws --dsh-home /tmp/dsh --port 43203 --model deepseek/deepseek-v4-flash --effort off'")` and the job-dir count is unchanged (`ls /var/lib/seat/jobs | grep -c -- '-'` before and after).
- The README's driver paragraph is SD7's (it owns `tools/factory/seat/README.md` in the same wave), so this task and SD7 touch disjoint files and run in parallel.

**Facts:**

- `grep -n 'choices=\["headless", "web"\]\|"mode": args.mode' pkgs/seat/seat-submit.py` → 44, 80; `grep -n 'else:  # web\|"--bind-namespace",\|"--no-open",' pkgs/seat/seat-run.py` → 92, 98, and the argv list without `--model` (the web job today runs on the home's saved selection).
- `grep -n 'usage: dsh-openrouter \[--model ID\] \[--permission MODE\] \[-- web-app' pkgs/dsh-openrouter/dsh-openrouter.sh` → line 39: web mode accepts `--model`; `grep -n 'model_explicit=1$' …` → 92 and 112 (the saved-selection rewrite is per `DSH_HOME`).
- `grep -n 'warn_missing_payload "$DSH_HOME/skills"' pkgs/dsh-openrouter/dsh-openrouter.sh` → 536: a missing catalog warns (`ln -s ~/flakes/dsh-harness/skills $DSH_HOME/skills` is the recipe it prints).
- `grep -n 'role = "orchestrate"' -B2 docs/ledger/routing.toml` → only `route = "claude"` today; SD1 adds `openrouter/orchestrate` (Pro medium) — the row this mode resolves.
- `grep -n 'runtimeInputs = \[ python3 \]' pkgs/seat/default.nix` → 19, 26: `route.py` (stdlib) runs on the same interpreter.
- `grep -n 'seat-submit is a flake package but not on the host PATH' docs/OPERATIONS.md` → the operator's launch shape is `nix run ~/nixos-agent-env#seat-submit -- …`.

- [ ] **Step 1: Write the failing tests** (rows 1–9 in `tests/seat/test_seat_submit.py`, `test_seat_run.py`, `test_seat_spool.py`; a fake `route.py` under `tmp_path` printing `m/orch medium`, another exiting 1; the VM step).
- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/seat -q -k drive 2>&1 | tail -n 20 > .factory-scratch/red.txt; cat .factory-scratch/red.txt` → `SystemExit: 2` (`invalid choice: 'drive'`) in every submit test; `KeyError`/`assert seen["cmd"] == […]` in the run test.
- [ ] **Step 3: Implement**; the VM step.
- [ ] **Step 4: Run it green** — `nix develop -c ruff format pkgs/seat tests/seat`; `nix develop -c pytest tests/seat -q`; `nix build .#checks.x86_64-linux.seat-unit -L --no-link`; `… seat-vm`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the Global Constraints recipe over the Step 4 commands.

**Tests:**

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | `drive --workspace W --dsh-home D --port 43210 --model m/x --effort high --no-start` (D holds the skill file) → `job.json == {mode: drive, workspace, dsh_home, model: m/x, effort: high, brief: None, port: 43210, route: explicit, timeout: 10800, submitted}`; no `brief.txt` | write `brief.txt` | — |
| 2 | the same without `--model/--effort` and `--route-py <fake printing "m/orch medium">` → the fake's argv is `[python3, <route.py>, --file, <table>, lookup, openrouter, orchestrate, any, any]`; `model m/orch`, `effort medium`, `route orchestrate/any/any` | a built-in Pro medium default → `model` differs from `m/orch` | the fake prints a model no default carries |
| 3 | the fake exiting 1 → exit 3, stderr `orchestrate row could not be resolved`, no job dir; the fake printing one token → exit 3 | fall back to a default → a job dir | — |
| 4 | `--model m/x` alone → exit 2 `go together`; `--effort high` alone → the same | accept one → a job dir | — |
| 5 | D without `skills/driving/SKILL.md` → exit 2 `carries no driving skill`, no job dir; with it → exit 0 | drop the check | the same D with and without the file |
| 6 | `--port` missing → exit 2 `drive needs --port`; `--port 80` and `--port x` → exit 2; `--brief b` → exit 2 `not accepted for drive` | accept 80 | the boundary 1024 accepted, 1023 refused |
| 7 | `--spool drive …` → the marker exists and `_no_systemctl` records nothing; plain `drive …` → `["systemctl","start",…]` once | — | — |
| 8 | `seat-run` on `{mode: drive, model: m, effort: off, port: 43210}` → argv exactly `["dsh-openrouter","--broker","--model","m","--bind-namespace","10.100.4.2","--","--no-open","--port","43210"]`; `url.txt` `http://10.100.4.2:43210\n`; `OPENROUTER_REASONING_EFFORT == off` | omit `--model` → the argv equals web's | the web test's argv beside it |
| 9 | `seat-spool` on a drive job without `route` → `refused route: missing`; with `route: bogus` → `refused route: not in enum …`; with `explicit` → started; a web job with `route: orchestrate/any/any` → refused | accept any string | the enum's two arms |
| 10 | `seat-vm` step 10 as in the Interfaces | pass a per-mode `ReadWritePaths` → the two properties differ; drop the skill precondition → `machine.fail` fails | the web job's property |

**touches:** pkgs/seat/seat-submit.py, pkgs/seat/seat-run.py, pkgs/seat/seat-spool.py, pkgs/seat/default.nix, tests/seat/test_seat_submit.py, tests/seat/test_seat_run.py, tests/seat/test_seat_spool.py, tests/integration/seat-vm.nix
**acceptance:** seat-unit, seat-vm, lint
**commit subject:** `seat: the drive job — seat-submit drive resolves the orchestrate row through route.py, requires the driver's skill set, and seat-run hands the web seat its model and effort (test: seat-unit, seat-vm, lint)`

### SD7 (code, S) — the driver climbs: the rung from the key, `--rung`/`--class` in the lookup, the escalation record and its launch line, `rung:`/`class:` in the result, `--spool` inside a seat

**dependsOn:** SD1, SD2, SD5

**Files:**
- Modify: `tools/factory/seat/factory-lib.sh` (`factory_task_rung`, `factory_task_class`, `factory_repo_name`, `factory_escalation`), `tools/factory/seat/factory-task`, `tools/factory/seat/factory-review`, `tools/factory/seat/factory-dispatch` (uses `factory_repo_name`), `tests/unit/80-seat-driver.bats`, `tools/factory/seat/README.md` ("Routing", "The scripts")

**Interfaces:**

- `factory_task_rung <KEY>` (pure bash): `1` when `KEY` does not match `^(.*[0-9])([a-z]{1,2})$` (tasks.py's `CHAIN_RE`, so `P3Ar2` is a root); otherwise `3` when the suffix contains `r`, else `2` (D5). Prints one digit, exit 0.
- `factory_repo_name <repo-path>`: the `name` of the `[[repo]]` row in `<repo-path>/docs/ledger/repos.toml` whose expanded `path` resolves to `<repo-path>` (today's `resolve_repo_name` in `factory-dispatch`, moved; the dispatcher calls it). No row → `factory_die 2 "no repo named in <toml> resolves to <path>"`.
- `factory_task_class <plan> <KEY> <repo-path>`: `factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/tasks.py" --root "$repo_path" class --repo "$(factory_repo_name "$repo_path")" --plan "$(basename -- "$plan")" "$KEY"`; prints the class when the output is one word of `CLASSES ∪ {any}`, else `any` with `factory_log "class: unavailable (<first stderr line or 'no output'>); using any"`. Never fails the caller. `FACTORY_PYTHON3_CMD` (the existing seam) makes it testable with a fixture toolbox.
- `factory-task`: after `kind size`: `rung=$(factory_task_rung "$key")`, `class=$(factory_task_class "$plan" "$key" "$repo_path")`; the lookup becomes `route_line=$(factory_route --rung "$rung" --class "$class" implement "$kind" "$size" 2>"$route_err" || true)` (`route_err=$(mktemp)`). Explicit `--model`/`OPENROUTER_MODEL` win as today (`route: explicit`, the rung still recorded). When `route_line` is empty and `$route_err` contains `ladder exhausted` → **escalation** (D4): `claude_line=$(factory_route --route claude implement "$kind" "$size" 2>/dev/null || true)`, then, with no workspace and no seat, `mkdir -p "$runs_dir"` and write `<KEY>.result`:

```
FACTORY-RESULT status=escalated
FACTORY-CHECKS none=not-run
FACTORY-COMMITS 0
FACTORY-NOTES <the ladder exhausted line from factory_route>; escalate: claude/implement <model> <effort>

run: <run>
key: <KEY>
model: <claude model, or unknown>
effort: <claude effort, or unknown>
route: claude/implement/<kind>/<size>
rung: <N>
class: <class>
escalate: claude/implement
launch: Workflow({ scriptPath: 'tools/factory/dark-factory.js', args: { plan: '<plan repo-relative>', prefix: '<area>', scratch: '<dir>', tasks: [<the KEY entry of: nix develop -c python3 pkgs/evidence/tasks.py --root . waves --repo <name> --plan <basename> --factory-args>] } })
workspace: none
branch: task/<KEY>
head: none
base: none
wall_s: 0
exit_code: 4
```

  and one stderr line `factory-task: <the exhausted line>; escalate: claude/implement <model> <effort> — paste the launch: line of <result> into the operator's Claude Code session`; exit **4**. `factory-wave`'s summary then prints `status=escalated` and the wave exits non-zero (its rule `[ "$status" = "done" ] || overall_rc=1` is unchanged); a later key in the same chain is skipped as today. Every other lookup failure keeps today's built-in-default path (a warning, never an exit).
  The normal path: the `.result` gains `rung: <N>` after `route:` and `class: <class>` after `rung:`; `route:` keeps its `implement/<kind>/<size>` form (T2's regex); and when `SEAT_SPOOL` is `1` the `seat-submit` argv gains `--spool` before the mode (the drive seat's dispatches spool; D2).
- `factory-review`: the same rung and class (role `review`); on exhaustion it prints `escalate: claude/review <model> <effort>` and `launch: Opus gate — a Workflow in a fresh clone of task/<KEY> (docs/runbooks/session.md RECIPES: Gate)` to stdout, writes no review, exits **4** (its codes: 0 approve, 1 rework, 2 reject, 3 no verdict).
- README: the suffix rule, the class source, `rung:`/`class:`/`escalate:`/`launch:`, exit 4 in both scripts, `SEAT_SPOOL`; and, under "Seat unit", a "Driver (`drive` job)" paragraph for SD6 — the operator's command (`nix run ~/nixos-agent-env#seat-submit -- drive --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-driver --port 43210`), the skill-set precondition, the `orchestrate` row, and that the driver's dispatches climb and escalate through this script.
- The class enum parity test (SD1/SD2's lockstep) lives here: `python3 -c 'import sys; sys.path.insert(0, "tools/factory"); import route; print("\n".join(route.CLASSES))'` equals the `name` fields of `docs/ledger/task-classes.toml` in order (read with `tomllib`), both present in the `unit` sandbox.

**Facts:**

- `grep -n 'route_line=$(factory_route' tools/factory/seat/factory-task tools/factory/seat/factory-review` → `factory-task:93`, `factory-review:79` — the two call sites; `grep -n 'printf .route: %s' tools/factory/seat/factory-task` → 360 — `rung:` and `class:` follow it.
- `grep -n 'case $status in' -A6 tools/factory/seat/factory-task` → `done) task_rc=0`, `partial) task_rc=1`, `failed) task_rc=2`, `*) … task_rc=3` — exit 4 is free.
- `grep -n '^CHAIN_RE = ' pkgs/evidence/tasks.py` → `CHAIN_RE = re.compile(r"^(?P<root>.*\d)(?P<suffix>[a-z]{1,2})$")` — the grammar `factory_task_rung` mirrors.
- `grep -n 'Invoke:  Workflow({ scriptPath' tools/factory/dark-factory.js` → line 13: `Workflow({ scriptPath: 'tools/factory/dark-factory.js', args: {...} })`, with `plan`, `prefix`, `tasks`, `scratch` required by its header; `grep -n '"--factory-args"' pkgs/evidence/tasks.py` → 1619: `waves --factory-args --plan <basename>` prints the launcher's `tasks` payload.
- `grep -n '^resolve_repo_name()' tools/factory/seat/factory-dispatch` → the function moved to the lib; `grep -n 'FACTORY_PYTHON3_CMD' tools/factory/seat/factory-lib.sh` → `factory_py` honours it.
- `grep -n 'seat-submit headless \\' tools/factory/seat/factory-task` → 173: the argv `--spool` joins.
- `grep -n '@test "factory-task submits through seat-submit when it is on PATH' tests/unit/80-seat-driver.bats` → the fake-`seat-submit`/fake-`dsh-openrouter` idiom (`REC` records argv; a fixture toolbox with `docs/ledger/routing.toml`; `FACTORY_SEAT_UNIT=0` selects the direct path).

- [ ] **Step 1: Write the failing tests** (rows 1–10, `tests/unit/80-seat-driver.bats`): fixture ladder table `implement/code/S` rungs 1 `m/one low`, 2 `m/two high`; a `bash-driver` row `m/bash medium`; a `review/any/any` row (one rung); `claude` rows `implement/any/any sonnet high`, `review/code/any opus high`, both routes' defaults; a fixture toolbox whose fake `pkgs/evidence/tasks.py` prints `bash-driver` (and one that exits 1) under `FACTORY_PYTHON3_CMD=bash -c 'shift; exec "$@"'`-style seam as `82-factory-dispatch.bats` does.
- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/80-seat-driver.bats --filter 'rung|class|escalat|spool' 2>&1 | tail -n 20 > .factory-scratch/red.txt; cat .factory-scratch/red.txt` → `factory_task_rung: command not found`; `.result` lacks `rung:`; the escalation test sees a seat launch (the fake's recorder exists) where exit 4 was expected.
- [ ] **Step 3: Implement** the four lib functions, the two scripts' changes, the dispatcher's call, the README.
- [ ] **Step 4: Run it green** — `nix develop -c shellcheck tools/factory/seat/factory-task tools/factory/seat/factory-review tools/factory/seat/factory-dispatch tools/factory/seat/factory-lib.sh`; `nix develop -c bats tests/unit/80-seat-driver.bats tests/unit/82-factory-dispatch.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the Global Constraints recipe over the Step 4 commands.

**Tests:**

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | `factory_task_rung`: `E1`→1, `E1b`→2, `E1r`→3, `E1rb`→3, `P3Ar2`→1, `P3Ar2b`→2, `OG1r2b`→2 | test the whole key for `r` → `P3Ar2b` gives 3 | `P3Ar2b` (an `r` in the root, `b` as the suffix) |
| 2 | `factory-task r1 <repo> K1b` on the fixture → the fake seat records `model=m/two`, `effort=high`; `.result` has `rung: 2`, `route: implement/code/S`, `class: any` (the fake `tasks.py` prints `any`) | always rung 1 → `m/one` | rungs with distinct models |
| 3 | with the fake `tasks.py` printing `bash-driver` → `class: bash-driver` and the seat sees `m/bash`; with the fake exiting 1 → `class: any`, the log has `class: unavailable`, the seat sees `m/one` | ignore the class in the lookup → `m/one` in the first case | the class row's distinct model |
| 4 | `K1r` (rung 3 on a two-rung ladder) → exit 4; no workspace created (the fake `factory-ws` leaves a marker: absent); `.result` line 1 `FACTORY-RESULT status=escalated`, and `escalate: claude/implement`, `model: sonnet`, `effort: high`, `rung: 3`, `route: claude/implement/code/S`, a `launch: Workflow({ scriptPath: 'tools/factory/dark-factory.js'` line; stderr has `paste the launch:` | fall back to the top rung → the fake seat's recorder exists, exit 0 | the two-rung ladder |
| 5 | `K1r --model x/y` → the seat runs with `x/y`, `.result` `route: explicit`, `rung: 3`, exit 0 | escalate before honouring the explicit model → exit 4 | — |
| 6 | `factory-review r1 <repo> K1b` on the fixture → exit 4, stdout `escalate: claude/review opus high` and a `launch: Opus gate` line; no seat launch; `K1` → the review seat runs (today's path) | run the review at rung 1 for every key → no exit 4 | the one-rung review ladder |
| 7 | `SEAT_SPOOL=1` → the fake `seat-submit`'s argv has `--spool` before `headless`; unset or `0` → no `--spool` | always pass it → the unset case fails | — |
| 8 | `factory_repo_name`: a fixture `repos.toml` with a `~`-path row → the name; an unmatched path → exit 2 naming the toml; `82-factory-dispatch.bats` stays green (the dispatcher's `--repo-name`/`resolve` tests) | drop the `~` expansion → the fixture fails | a `~/x` row |
| 9 | the class enums agree: `route.CLASSES` == the toml's names, in order | reorder a toml row | — |
| 10 | `factory-wave` over `"K1r K2"` (the fake task exits 4 for `K1r`) prints `K1r status=escalated …` and `K2 status=skipped …`, exits non-zero | treat exit 4 as done → `K2` runs | the chain |

**touches:** tools/factory/seat/factory-lib.sh, tools/factory/seat/factory-task, tools/factory/seat/factory-review, tools/factory/seat/factory-dispatch, tests/unit/80-seat-driver.bats, tools/factory/seat/README.md
**acceptance:** unit, lint
**commit subject:** `factory: the rung is the key's suffix, the lookup carries rung and class, an exhausted ladder is recorded as escalated with the claude row and a launch line, rung and class in every result, --spool inside a seat (test: unit, lint)`

### SD8 (code, S) — `--prior`: the failed attempt travels with the next rung as a `## Prior attempt` block the driver composes

**dependsOn:** SD7

**Files:**
- Modify: `tools/factory/seat/factory-lib.sh` (`factory_prior_default`, `factory_prior_block`), `tools/factory/seat/factory-task` (`--prior`, the `.prior` file, `prior:`), `tools/factory/seat/factory-brief` (`--prior-file`), `tests/unit/80-seat-driver.bats`, `tools/factory/seat/README.md`

**Interfaces:**

- `factory-task <run> <repo-path> <KEY> [--model ID] [--after KEY2] [--prior RUN/KEY]`. `--prior` names `$FACTORY_RUNS/RUN/KEY.result`; missing or unreadable → `factory_die 2 "no such prior result: …"` before any workspace. Without `--prior`, when `factory_task_rung KEY` is 2 or 3, the default prior is the **newest by mtime** among `$FACTORY_RUNS/*/<member>.result` where `<member>` ≠ KEY and `<member>`'s chain root (the `CHAIN_RE` rule of SD7) equals KEY's; none → no block. `FACTORY_PRIOR=none` disables the default (an explicit `--prior` still wins). A rung-1 key never has a default prior.
- `factory_prior_default <KEY>` prints `RUN/KEY` or nothing. `factory_prior_block <result-file> <repo-path> <run> <key>` prints the H2 heading line `## Prior attempt (<run>/<key>)` (written here inline: `factory-brief`'s section extractor is not fence-aware, so no line of this plan may begin with `## ` inside a task section) followed by a blank line and:

```
This attempt was rejected or failed at the rung below yours. Its result lines:

<every line of the .result matching ^(FACTORY-RESULT|FACTORY-CHECKS|FACTORY-COMMITS|FACTORY-NOTES|model:|effort:|route:|rung:|class:|error_class:|escalate:|exit_code:|wall_s:|usage:)>

The rejecting review (<path>) — its numbered findings, then the mutation-table rows that survived:

<every line matching ^### (MAJOR|MINOR)-[0-9]+>
<every table row whose third cell is `no` or `**no**`, verbatim>

The rejected commit's diff stat:

<the lines after the .result's `diffstat:` line up to the next blank line>
```

  The review path is the newest `<repo-path>/docs/reviews/*-opus-review-<run>-<key>.md`, else `$FACTORY_RUNS/<run>/<key>.review.md`; neither → the review paragraph reads `review: none found for <run>/<key>`. Only the `.result` and the review file are read — never a `.log`, never a transcript (the packet readers' rule; the review and the result are the record).
- `factory-brief <plan> <KEY> [--prior-file F]`: `F`'s content is printed between the task section and the WORKSPACE RULES block; a missing or unreadable `F` → exit 2 `no such prior file`. The M13 shape is otherwise unchanged (`## Global Constraints`, `## Assumptions`, the section, `## Prior attempt`, `## WORKSPACE RULES`, the optional REPO NOTES).
- `factory-task` writes the block to `$runs_dir/<KEY>.prior`, passes `--prior-file`, and the `.result` gains `prior: RUN/KEY` (or `prior: none`) after `class:`. Rule A1's "every rejection item" is thereby a mechanical copy of the review's numbered findings.

**Facts:**

- `grep -n 'FACTORY_BRIEF_EXTRA\|REPO NOTES' tools/factory/seat/factory-brief` → 114–115: the one optional block the brief appends today (the `--prior-file` block goes before the rules, the REPO NOTES stay last).
- `grep -n '^## Findings\|^### MAJOR-1\|^### MINOR-1\|^| mutant | change | died? | on |' docs/reviews/2026-09-06-opus-review-pa3-P11.md` → 265, 267, 284, 192 — a rejected review's shape: numbered `### MAJOR-n — …`/`### MINOR-n — …` headings and a `| mutant | change | died? | on |` table; `grep -c '| \*\*no\*\* |' …` → `2` survivors in that review.
- `ls docs/reviews | grep opus-review | sed -E 's/^([0-9-]+)-opus-review-([^-]+)-(.+)\.md$/DATE-opus-review-RUN-KEY.md/' | sort -u` → one shape, `DATE-opus-review-RUN-KEY.md`, over 164 files.
- `grep -n 'echo "diffstat:"\|printf .usage: %s' tools/factory/seat/factory-task` → 376, 379: the `diffstat:` block sits before `usage:` in every `.result` (it is `git diff --stat base..task/KEY` at task end — the spec's "git diff --stat of the rejected commit").
- `sed -n '1,16p' tools/factory/seat/factory-review | grep -n 'review.md'` → factory-review writes `~/factory/runs/<run>/<KEY>.review.md` — the fallback review path.

- [ ] **Step 1: Write the failing tests** (rows 1–7, `tests/unit/80-seat-driver.bats`): a fixture `.result` (the four FACTORY lines, `model:`…`usage:`, a `commits (base..task/K1):` block, a `diffstat:` block of two lines), a fixture review with two `### MAJOR-1`/`### MINOR-2` headings, a mutant table with one `**no**` row and two `yes` rows, prose paragraphs; `.result` fixtures under `$FACTORY_RUNS/r0/` and `r2/` with `touch -d` mtimes.
- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/80-seat-driver.bats --filter 'prior' 2>&1 | tail -n 20 > .factory-scratch/red.txt; cat .factory-scratch/red.txt` → `factory_prior_block: command not found`; `factory-brief: unknown option --prior-file` (usage, exit 2); `.result` lacks `prior:`.
- [ ] **Step 3: Implement**; the README paragraph ("Prior attempt").
- [ ] **Step 4: Run it green** — `nix develop -c shellcheck tools/factory/seat/factory-task tools/factory/seat/factory-brief tools/factory/seat/factory-lib.sh`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the Global Constraints recipe over the Step 4 commands.

**Tests:**

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | `factory_prior_block` on the fixtures contains `## Prior attempt (r0/K1)`, the four FACTORY lines, `route: implement/code/S`, `usage: {…}`, `### MAJOR-1 — …`, `### MINOR-2 — …`, the one `**no**` row, the two diffstat lines; and contains neither a `yes` row, nor the review's prose sentence, nor the `commits (base..task/K1):` block | drop the block (the spec's mutant) → `## Prior attempt` absent; select `yes` rows → a `yes` row present | one survivor beside two killed mutants |
| 2 | no review file anywhere → `review: none found for r0/K1`; a review under `$FACTORY_RUNS/r0/K1.review.md` only → its findings appear | ignore the runs-dir fallback → `none found` | — |
| 3 | `factory-brief plan K1 --prior-file F` → `### K1` … `## Prior attempt` … `## WORKSPACE RULES` in that order (`[[ "$output" == *"### K1"*"## Prior attempt"*"## WORKSPACE RULES"* ]]`); `--prior-file /nope` → exit 2 `no such prior file` | append the block after the rules → the order check fails | — |
| 4 | `factory-task r1 <repo> K1b --prior r0/K1` → `runs/r1/K1b.prior` exists; the fake `seat-submit`'s `--brief` file contains `## Prior attempt (r0/K1)`; `.result` has `prior: r0/K1` | pass the brief without the block → the recorded brief lacks the heading | — |
| 5 | the default: `K1b` with `runs/r0/K1.result` (older) and `runs/r2/K1.result` (newer) → `prior: r2/K1`; `K1` → `prior: none` and no `.prior` file; `FACTORY_PRIOR=none K1b` → `prior: none`; `--prior r0/K1` beats `r2` | choose the oldest → `r0/K1` | two results, `touch -d '-1 hour'` on `r0` |
| 6 | `--prior nope/K1` → exit 2 `no such prior result`, no run dir | ignore a missing prior | — |
| 7 | the block never reads the log: `runs/r0/K1.log` beside the result with mode `000` → the block is composed unchanged (skipped when running as root) | `cat` the log for the tail → `Permission denied` on stderr | — |

**touches:** tools/factory/seat/factory-lib.sh, tools/factory/seat/factory-task, tools/factory/seat/factory-brief, tests/unit/80-seat-driver.bats, tools/factory/seat/README.md
**acceptance:** unit, lint
**commit subject:** `factory: --prior carries the failed attempt to the next rung — result lines, the review's numbered findings and surviving mutants, the diff stat — composed by the driver, never the seat (test: unit, lint)`

### SD9 (code, S) — the record: `rung`, `class`, `prior` and `escalate` on the `task-result` row; `evidence report ladder` at n ≥ 5

**dependsOn:** SD8, T10a

**Files:**
- Create: `tests/evidence/fixtures/report/ladder/derived/tasks.jsonl`, `tests/evidence/fixtures/report/ladder/derived/gates.jsonl`
- Modify: `pkgs/evidence/streams.py` (T1's; the `task-result` entry), `pkgs/evidence/ingest_result.py` (T2's; four producers, the `escalated` status, the `route` regex), `pkgs/evidence/report.py` (`ladder_report`, the `ladder` subparser), `pkgs/evidence/SCHEMA.md`, `tests/evidence/test_streams_policy.py`, `tests/evidence/test_ingest_result.py`, `tests/evidence/test_report.py`, `docs/runbooks/evidence.md` ("The ladder report")

**Interfaces:**

- `streams.KINDS["task-result"]["fields"]` gains `"rung": ("int", 1, 99)`, `"class": ("enum", CLASSES + ("any",))` with `CLASSES` the ten names of SD2 (a tuple literal here; the parity with `docs/ledger/task-classes.toml` is SD7's test), `"prior": ("null", ("re", r"^[A-Za-z0-9._-]{1,64}/[A-Za-z][A-Za-z0-9-]{0,31}$"))`, `"escalate": ("null", ("re", r"^claude/(implement|review|verify|baseline|research|audit|orchestrate|plan|any)$"))`; `status`'s enum gains `escalated`; `route` becomes `("re", r"^(explicit|unknown|(claude/)?(implement|review)/(code|docs|any)/(XS|S|M|L|any))$")`. None of the four names is in `FORBIDDEN` (`class` is already a `check` field).
- `ingest_result.parse_result`: `rung` ← the `rung:` line as an int (absent → `1`); `class` ← `class:` when in the enum, else `any`; `prior` ← `prior:` (absent or `none` → `None`); `escalate` ← `escalate:` (absent → `None`); `status` accepts `escalated`; `route`'s `kind`/`size` come from the last two segments of either route form; an escalated result has `error_class none`, `commits 0`, `head`/`base` `None` (the `none` words map to `None`).
- `evidence [--store S] report ladder --repo R [--min-n 5] [--plan GLOB]` (`report.ladder_report(store, repo, min_n=5, plan=None) -> list[str]`): reads `evidence.join_tasks_gates(store)` (T10a: one entry per `derived/tasks` row, `{"run_id","key","task","gate","activity"}`), keeps entries whose `task["plan"]` matches `--plan` when given, and groups them by `(route, role, kind, size, class, model, effort, rung)` where `role` is the segment before `/kind/size` (`implement/code/S` → `implement`; `claude/review/code/S` → `review`; `explicit`/`unknown` → `unknown` for role, kind and size). Output: the header `# evidence report ladder — tasks ⋈ gates by (route, role, kind, size, class, model, effort, rung); n printed with every line, no line under n=<min_n>; class is derived from touches (docs/ledger/task-classes.toml) and is as true as the plan's touches list`; then, for every group with `n >= min_n`, sorted by key, one line `<route>/<role>/<kind>/<size>/<class> <model> <effort> rung <rung> | n=<n> | first-gate approved <a>/<g> | commits per attempt <mean, 2 dp> | fix rounds per landing <r>/<l> = <2 dp> | median wall_s <w> | median out <o>` — `g` = entries with a gate, `a` = those whose gate `verdict` is `approved`; commits per attempt = mean of `commits` (the "tangible" column); `r` = entries whose key is not its own chain root (`tasks.chain_root`), `l` = entries with an approved gate, `unmeasured` when `l` is 0; medians over non-`None` `wall_s` and `usage.out`; and one closing line `groups under n=<min_n>: <k> (<m> rows) — refused`. Exit 0; an unreadable store or repo → `report: …` on stderr, exit 2 (the `plans` report's `ReportUnreadable`).
- `SCHEMA.md`: the four fields in the `derived/tasks` row; the runbook: a subsection with the command and the line's definitions (the one-home rule: a row, a rung or a fallback changes only by a commit citing one of these lines).

**Facts:**

- `for p in pkgs/evidence/streams.py pkgs/evidence/ingest_result.py; do test -f $p && echo exists || echo MISSING: $p; done` → both `MISSING` in this tree (Assumption 4). Their contract is the telemetry plan: `grep -n '"task-result": {"stream"\|"route": ("re", r"^(explicit|unknown|implement\|"error_class": ("enum", ERROR_CLASSES)' docs/superpowers/plans/2026-09-06-telemetry-store-1.md` → 267, 271, 279 (the `task-result` entry, today's `route` regex `^(explicit|unknown|implement/(code|docs)/(XS|S|M|L))$`, `error_class`).
- `grep -n 'join_tasks_gates(store) -> list\[dict\]\|n_gate(rows, n=5)' docs/superpowers/plans/2026-09-06-telemetry-store-1.md` → 647–648: `{"run_id", "key", "task": <the row>, "gate": <the newest derived/gates row with the same (run_id, key)> | None, "activity": …}` and `n_gate(rows, n=5)` "exported for T10b and the ladder report".
- `grep -n '^def plans_report\|refused: n=\|rest\[0\] == "report"' pkgs/evidence/report.py pkgs/evidence/evidence.py` → `plans_report(store, repo, today=None, min_n=5, plan=None)` (141), `refused: n={n} < {min_n} (no conclusion under {min_n})` (178), the CLI forwarding `report` with `--store` (evidence.py 341) — the shapes `ladder` copies.
- `grep -n 'FIXTURES = \|STORE = ' tests/evidence/test_report.py` → `FIXTURES = HERE.parent / "fixtures" / "report"`, `STORE = FIXTURES` — a fixture store is a directory holding stream files; the ladder fixture is a sibling directory `fixtures/report/ladder/` with `derived/tasks.jsonl` and `derived/gates.jsonl`.
- The SD7 result lines this task reads: `rung: N`, `class: C`, `escalate: claude/implement`, `launch: …`, and SD8's `prior: RUN/KEY` — the `launch:` line is never ingested (a free-text line; the fence would refuse it).

- [ ] **Step 1: Write the failing tests** — `test_streams_policy.py` (row 1), `test_ingest_result.py` (row 2, with three new `.result` fixtures under `tests/evidence/fixtures/results/`: `rung2.result`, `legacy.result`, `escalated.result`), `test_report.py` (rows 3–8) over the ladder fixture: group A = five `implement/code/S/any deepseek/deepseek-v4-pro-0813 medium rung 1` rows (keys `K1 K2 K3 K4b K5`, commits `1 1 1 0 1`, `wall_s` `100 100 100 100 900`, `usage.out` `1000 1000 1000 1000 9000`) with gates `approved approved approved rejected rejected`; group B = four rows at rung 2.
- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence -q -k 'ladder or rung or prior or escalat' 2>&1 | tail -n 20 > .factory-scratch/red.txt; cat .factory-scratch/red.txt` → `rung: undeclared field` from the fence test, `KeyError: 'rung'` from the ingest test, `AttributeError: module 'report' has no attribute 'ladder_report'`.
- [ ] **Step 3: Implement**; `SCHEMA.md`; the runbook subsection.
- [ ] **Step 4: Run it green** — `nix develop -c ruff format pkgs/evidence tests/evidence`; `nix develop -c pytest tests/evidence -q`; `git add tests/evidence/fixtures/report/ladder tests/evidence/fixtures/results/rung2.result tests/evidence/fixtures/results/legacy.result tests/evidence/fixtures/results/escalated.result`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the Global Constraints recipe over the Step 4 commands.

**Tests:**

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | a `task-result` row with `rung 2, class bash-driver, prior "r0/K1", escalate None` validates to `[]`; `rung 0` → `rung: not a int`-class refusal per the fence's range wording; `rung "2"` → refused; `class "rocket"` → `class: not in enum (…)`; `prior "r1"` → `prior: not a re`; `escalate "openrouter/implement"` → refused; `status "escalated"` → accepted; `route "claude/implement/code/S"` → accepted | drop `rung` from the entry → `undeclared field`; widen `escalate` to any string → the openrouter case passes | one row per arm |
| 2 | `rung2.result` → `rung 2`, `class bash-driver`, `prior r0/K1`, `escalate None`; `legacy.result` (no such lines) → `1`, `any`, `None`, `None`; `escalated.result` → `status escalated`, `escalate claude/implement`, `route claude/implement/code/S`, `kind code`, `size S`, `commits 0`, `error_class none`, `head None`; every row lands (`ingested 3 rows … (0 refused)`) | default `rung` to `0` → the fence refuses `legacy.result` (the test asserts `0 refused`) | the three fixtures |
| 3 | the ladder fixture's report is exactly the header, `openrouter/implement/code/S/any deepseek/deepseek-v4-pro-0813 medium rung 1 | n=5 | first-gate approved 3/5 | commits per attempt 0.80 | fix rounds per landing 1/3 = 0.33 | median wall_s 100 | median out 1000`, `groups under n=5: 1 (4 rows) — refused` | median → mean → `260`/`2600`; count approved over all rows → `3/5` unchanged, so also: one gate `None` in a sixth-row variant → `3/5` vs `3/6` | the skewed `900`/`9000` values; `K4b` as the one fix round |
| 4 | `--min-n 4` prints group B's line and `groups under n=4: 0 (0 rows) — refused`; default prints one line | `>` for `>=` → the n=5 group is refused | exactly five rows |
| 5 | a fixture with no approved gate → `fix rounds per landing unmeasured` | divide by zero / print `0.00` | — |
| 6 | two rows differing only in `rung` are two groups (`groups under n=5: 2 (…)`) | drop `rung` from the key → 1 | — |
| 7 | `python3 pkgs/evidence/evidence.py --store <fixture> report ladder --repo <fixture repo>` → exit 0, stdout equals `ladder_report`'s lines; `--repo /nonexistent` → exit 2, stderr `report: cannot read repo` | forward without `--store` → the default store (absent) → `refused` lines | — |
| 8 | the header line contains `derived from touches` and `no line under n=5` | drop the proxy sentence | — |

**touches:** pkgs/evidence/streams.py, pkgs/evidence/ingest_result.py, pkgs/evidence/report.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_streams_policy.py, tests/evidence/test_ingest_result.py, tests/evidence/test_report.py, tests/evidence/fixtures/report/ladder/derived/tasks.jsonl, tests/evidence/fixtures/report/ladder/derived/gates.jsonl, tests/evidence/fixtures/results/rung2.result, tests/evidence/fixtures/results/legacy.result, tests/evidence/fixtures/results/escalated.result, docs/runbooks/evidence.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: task rows carry rung, class, prior and escalate; report ladder joins tasks and gates per (route, role, kind, size, class, model, effort, rung) and refuses a line under n=5 (test: evidence-unit, lint)`

### SD10 (docs, S) — the `driving` skill in the dsh harness: brief, dispatch, gate, integrate as calls to the seat driver; what the driver never decides

**dependsOn:** SD7
**repo:** dsh-harness

**Files (in `~/flakes/dsh-harness`):**
- Create: `skills/driving/SKILL.md`, `skills/driving/references/verbs.md`
- Modify: `README.md` (a "Driving" paragraph beside "Model routing"), `CHANGELOG.md` (one dated line), `AGENTS.md` (the skill list, where it names skills)

**Interfaces:**

- `SKILL.md` frontmatter: `name: driving`; `description: drive nixos-agent-env's task pipeline from the operator's seat — brief, dispatch, gate, integrate, each one call to tools/factory/seat and never a hand implementation; use when the operator, in a seat started as a drive job, asks what is queued, to run a wave, to gate a task or to land one`. It claims no spec and no plan (the harness gate refuses two SKILL.md descriptions that both claim a spec and a plan — `planning` holds that trigger).
- The four verbs, one command each (repeated in `references/verbs.md`; `R=/home/dalhaka/nixos-agent-env`):
  - **brief** — `cd $R && nix develop --offline -c python3 pkgs/evidence/tasks.py --root . brief`; read **Next wave**, **Classes (next wave)**, **Rejected, fix round owed**, **Running**.
  - **dispatch** — `cd $R && tools/factory/seat/factory-dispatch <run> $R docs/superpowers/plans/<plan> --dry-run` first; the same line without `--dry-run` only for a wave whose keys are chain roots or fix rounds (`<KEY>b`); never a key with `r` in its suffix (a re-plan's dispatch is the operator's); never with `--model`, `OPENROUTER_MODEL` or `OPENROUTER_REASONING_EFFORT` set (the table chooses; overrides are the operator's).
  - **gate** — `cd $R && tools/factory/seat/factory-review <run> $R <KEY>`; exit 4 → paste its `launch:` line to the operator and stop.
  - **integrate** — `cd $R && tools/factory/seat/factory-integrate <run> $R <KEY> && git -C $R pull --ff-only /home/dalhaka/factory/base/nixos-agent-env integ/<run>` — never after a `CHECK … fail` line; then `nix develop --offline -c python3 pkgs/evidence/tasks.py --root . write-board --board docs/OPERATIONS.md` and `nix develop --offline -c git commit -q -m 'board: queue block regenerated' docs/OPERATIONS.md` — the one board write the driver owns.
- The driver never: pauses or lifts a pause, spends or asks for a top-up, switches, approves a spec, dispatches a re-plan, changes a row in `docs/ledger/routing.toml` or `docs/ledger/task-classes.toml`, sets a model or an effort, pushes, runs `sudo` or `systemctl` (the seat's guard refuses the last three anyway). On any verb's failure it reports the exit code and the `.result`'s `FACTORY-NOTES` and `escalate:` lines; when a result reads `status=escalated` it pastes the `launch:` line; it never relaunches a key by hand (the relaunch table is telemetry T15's).
- Wording: no model id, no effort word, none of the words `tier`, `rung`, `fallback`, `escalat…` appear in the two files — the ladder is "the next row"; the harness's whole-tree model-choice gate must print nothing, and the H-series task in that repo owns any change to the gate's alternation.
- `README.md`: a "Driving" paragraph naming the skill and the four verbs; `CHANGELOG.md`: one dated line; `AGENTS.md`: `driving` added where the skills are listed (if a list exists; otherwise untouched, said so in the commit body).

**Facts:**

- `ls -d /home/dalhaka/flakes` → `No such file or directory` in this checkout (Assumption 7): the catalog layout is taken from P13's `touches` (`awk '/^### P13 /{p=1} p&&/^\*\*touches/{print;exit}' docs/superpowers/plans/2026-09-06-planning-agent.md` → `skills/planning/SKILL.md, skills/planning/references/inputs.md, …, skills/writing-plans/SKILL.md, AGENTS.md, README.md, skills/using-superpowers/references/dsh-tools.md, skills/subagent-driven-development/SKILL.md, CHANGELOG.md`) and its acceptance `grep-gate, node-test`.
- `grep -n '^\*\*acceptance:\*\* grep-gate' docs/superpowers/plans/2026-09-05-harness-router.md` → H2b and H2c: the repo's check names; its Global Constraints: commits via `nix develop /home/dalhaka/nixos-agent-env -c git commit -F <msgfile>`, "the harness's `githooks/pre-commit` runs on commit — read it first".
- `grep -n 'Rows with `route = "claude"` are not reachable from this seat' docs/superpowers/plans/2026-09-05-harness-router.md` → the routing block every harness agent follows; the driver's verbs never request a model.
- `grep -n 'ln -s ~/flakes/dsh-harness/skills' pkgs/dsh-openrouter/dsh-openrouter.sh` → the catalog reaches a home by that symlink — the driver's home (SD6's precondition path `skills/driving/SKILL.md`) is that catalog.

- [ ] **Step 1: Read the gate, record green on main** — `cat githooks/pre-commit`, and the gate command it names; run it and `node --test` as the README states; paste both results (the pass is the baseline the skill must keep).
- [ ] **Step 2: Red** — `test -f skills/driving/SKILL.md; echo $?` → `1` (the artefact is absent); `grep -rl 'name: driving' skills | wc -l` → `0`.
- [ ] **Step 3: Write the two files, the README paragraph, the CHANGELOG line, the AGENTS.md entry.**
- [ ] **Step 4: Green** — the gate prints nothing (paste the command and its empty output); `node --test` passes; `grep -c -i -E 'tier|rung|fallback|escalat' skills/driving/SKILL.md skills/driving/references/verbs.md` → `0` for both; `for c in factory-dispatch factory-review factory-integrate; do test -x /home/dalhaka/nixos-agent-env/tools/factory/seat/$c && echo "$c ok"; done` → three `ok` lines; the repo's own pre-commit passes.
- [ ] **Step 5: Commit** — through `nix develop /home/dalhaka/nixos-agent-env -c git commit -F <msgfile>`; the body is produced by the Global Constraints recipe over the Step 4 commands (the script lives in this workspace's `.factory-scratch/`).

**Tests** (a docs task: each assertion is a command in Step 4):

| # | assertion | mutant | discriminating fixture |
|---|---|---|---|
| 1 | the harness's model-choice gate prints nothing | write `deepseek/deepseek-v4-pro-0813` in a verb → the gate names the line | — |
| 2 | the four words are absent from both files (`grep -c` → 0) | the word `rung` in verbs.md | — |
| 3 | the three driver scripts the verbs name exist and are executable in `$R` | a typo `factory-integrat` | — |
| 4 | the description claims no spec and no plan (the two-claimants grep the gate runs — H2c — stays silent) | `description: … write a plan …` | `planning`'s description beside it |
| 5 | `node --test` count unchanged from Step 1 | — | — |

**touches:** skills/driving/SKILL.md, skills/driving/references/verbs.md, README.md, CHANGELOG.md, AGENTS.md
**acceptance:** grep-gate, node-test
**commit subject:** `docs: the driving skill — brief, dispatch, gate, integrate as calls to nixos-agent-env's seat driver; what the driver never decides (test: grep-gate, node-test)`
