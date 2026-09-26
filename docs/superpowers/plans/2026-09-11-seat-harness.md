# Plan 2026-09-11 — Seat/Harness (SA): N seats, the drive preset, the three hooks, the memory store, the payload seam

- **Charter:** `docs/concepts/2026-09-09a-redesign-charter.md` — the §2 row (`:49`; area `seat`, Opus gate, prefix `SA`, answers 13, 36, 57–60); §6 increment 2 (`:167-173`): **the drive launch at `danger-full-access`, the three hooks, the off-tree memory store, N seats with allocated ports** are SA's — the Nix-built payload and the dsh-harness absorption are Platform's, the generated AGENTS.md Knowledge's (increment 4).
- **Decisions:** `docs/decisions/2026-09-09-redesign-answers.md`, listed by number in `## Decisions relied on`.
- **Context block:** `docs/context/seat-harness.md` (anchor `e535e53`, delta at `22b7b35`); anchors re-resolved at `21f6a6a` by the fill and at `662e87f` by this revision (`## Assumptions`).
- **Program plan:** `docs/superpowers/plans/2026-09-09-program.md` `## Global Constraints` G1–G12 — quoted verbatim in `## Global Constraints` below, because `factory-brief` (`tools/factory/seat/factory-brief:51-52`) reads that section from this file alone. This plan's own brief-§3 bindings are in `## Invariant bindings`, because G12 names no SA task.
- **Plan file:** `docs/superpowers/plans/2026-09-11-seat-harness.md` — the spelling the manifest's SA row already carries (`docs/ledger/subsystems.toml:139`), so G7's prefix guard admits `SA*` keys here. `PLAN-SA`'s typed `out:` still says `2026-09-10-seat-harness.md` (`program.md:553`): see `## Cross-plan`.
- **Author:** Fable (`claude-fable-5.1`), batched planning pass 2 — every task body, on the audited pass-1 structure.
- **Status:** revision 1 (2026-09-14) of the 2026-09-12 judgement (32/42), errata re-measured at `662e87f`. Not dispatchable until the operator lands it under `docs/superpowers/plans/` and answers the three `## Operator questions` (or accepts their defaults, on which every task below is drafted); every other decision is an Assumption with its veto surface.
- **Gate:** Opus for every task (manifest `gate = "opus"`). **Area:** `seat`; every subject is `seat: … (test: …)` (G4).

## Global Constraints

Quoted verbatim from `docs/superpowers/plans/2026-09-09-program.md` (`:33-46`), each with its line; all twelve bind this plan (SA1, SA4, SA7, SA8 edit `flake.nix` or the lane module: G1, G9, G10; every task commits: G2–G6, G11; G7 admits `SA*` keys only because the manifest names this file).

- **G1 Build-only.** Never `sudo`, `nixos-rebuild`, `systemctl start|stop|restart|enable|kill`, basket mount or teardown. The operator switches; a task that needs the live system to change says so in its `## Operator` line and stops. — G1 (program.md:35)
- **G2 Red first.** Every check or test a task adds is shown failing before the change that makes it pass, and the red output is pasted in the commit body. A load-bearing test counts only once it has failed (CLAUDE.md). — G2 (program.md:36)
- **G3 Trailers.** Both trailers, in this order: the machine-set `Generated-By:` then `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` (`docs/board/policies.md:30-36`, decision 52a). A gate reads the implement model from the task's own `.result` (FIX7, `6a84fae`). — G3 (program.md:37)
- **G4 Subject.** `<area>: summary (test: <check names>)`, the area being the subsystem's prefix in lower case once PR1 lands (`evidence:`, `factory:`, `isolation:`, `knowledge:`, `program:`), the check names being exactly the task's `acceptance` list. Guarded twice: the workspace's `commit-msg` hook that `factory-ws` installs (`tools/factory/seat/factory-ws:131-136`, `factory-commit-msg.sh`) and the gate's convention section, which compares the subject byte for byte with the section's `commit subject` line. — G4 (program.md:38)
- **G5 Touches.** Edit only the files the task's `touches` names; a new file is named there too. An undeclared touch demotes the result (`factory-task:857-861`). `git add` every new file before any `nix build` (flakes see tracked files only). **One standing exemption, added 2026-09-10 after it was flagged twice:** the *derived queue block* of `docs/OPERATIONS.md`, and nothing else in that file, when the pre-commit's G8c forces its regeneration — G6 orders that regeneration, so listing the file in every task's `touches` would be noise and omitting it made the gate read a forced, derived, machine-written hunk as an undeclared touch (HH3's minor, PR1's MAJOR). A gate treats a queue-block-only diff there as declared; any other hunk in that file is an undeclared touch as before, and board prose stays the orchestrator's (the rule that refused W6b at the integrator). **`docs/MAP.md` is exempt on the same ground and for the same reason** (KN1's minor): `lint` asserts it is current (`flake.nix:1081-1086`), so any task that adds or renames a module, package, check or test must run `python3 pkgs/evidence/repomap.py --root . write` and commit the result whether or not its `touches` names the file. Both exemptions cover *derived* files a check or hook forces; neither excuses a hand edit. — G5 (program.md:39)
- **G6 Commit route.** `nix develop -c git commit -F <msgfile>` on `task/<KEY>`; one commit per task. **A fix round that starts by cherry-picking its predecessor folds that cherry-pick into its own single commit** (`git cherry-pick -n`, or `git reset --soft` back to the base before committing) — added 2026-09-10 after the instruction proved ambiguous: PR1b's seat folded and PR1c's did not, and `factory-task:757` demoted the second for claiming one commit where the branch carried two. The chain's history lives in the plan and the reviews, not in a stack of replayed commits on one task branch. If the pre-commit refuses only on G8c (a stale board queue block), regenerate with `nix develop -c python3 pkgs/evidence/tasks.py --root . write-board` and include the block in the same commit; never `--no-verify`. — G6 (program.md:40)
- **G7 Reserved prefixes** (decision 63a): `IS PL HM SA FA EV GN KN PR` and the two-part keys `SPEC-<XX>`, `PLAN-<XX>`. No other plan may define a key under them. **EV2 landed this guard on 2026-09-10 (`f31b8bb`, integrated `776b492`); it is live and no longer a sentence a reviewer enforces by reading the key.** `tasks.py check` refuses a key whose leading letters match a manifest prefix when its plan file matches none of that subsystem's `plans` globs (`pkgs/evidence/tasks.py:1835-1849`), beside the older refusal of a key defined in more than one plan (now `:1758-1766`). `reserved_prefix` reads the letters before the first digit or hyphen, so `SPEC-<XX>` and `PLAN-<XX>` resolve to `SPEC`/`PLAN`, match no manifest row, and pass. The practical consequence, paid for on 2026-09-10: a subsystem's `plans` list must name a plan file BEFORE that plan may hold keys under its prefix — the eight `2026-09-11-*.md` batch outputs were added to `docs/ledger/subsystems.toml` for exactly this reason. Fix rounds add a lower-case letter (`EV1b`); a re-key never reuses a landed key. — G7 (program.md:41)
- **G12 Invariants** (program.md:42) enumerates the program plan's own tasks and names no SA task; its opening clause binds here verbatim — "every task here is written against the six verbatim" — and this plan's per-task bindings, in G12's shape, are `## Invariant bindings`.
- **G8 Privacy.** Nothing leaves the machine. IS2 reads and writes nothing outside `docs/`; no credential, token or key is copied, moved, printed or redirected by any task in this plan. — G8 (program.md:43)
- **G9 Areas.** From EV2 on, a task whose `touches` fall in two subsystems declares `**areas:**` with both; `tasks.py check` refuses it otherwise. **EV2 landed this on 2026-09-10 (`f31b8bb`); it is enforced in code, not by hand** (`pkgs/evidence/tasks.py:1823-1834`). The refusal fires only while a task's derived state is `ready`, `blocked`, `ran` or `running`, so a landed key is never refused retroactively, and it exempts exactly the twenty-five keys in `docs/ledger/areas-grandfather.toml` — a list frozen at `dbedfe9`, so a key typed later is refused like any other. Note the grandfather ledger is read from the repo's live path rather than the tree under `--root`, so inside a workspace it exempts nothing (`BUG-ledger-read-from-live-path`): declare `**areas:**` rather than relying on the exemption. — G9 (program.md:44)
- **G10 Nix hygiene.** Module headers are `_:` never `{ ... }:` (statix); `hosts/core/hardware-configuration.nix` is never touched; a new language brings its formatter and linter in the same task (none is expected here). — G10 (program.md:45)
- **G11 Numbers.** Every integer a task pastes (row counts, line numbers, test counts) is re-run at commit time, not copied from this plan (concept 2026-09-08g). Guarded by the gate: the review rubric's "correct facts" row re-runs the commit body's commands, and a pasted integer that does not reproduce is a MAJOR (the record's `wrong-fact` class in `docs/ledger/plan-defects.toml`). — G11 (program.md:46)

## Operator questions

Three questions, each bounded, with a recommendation and the answer's effect per task; silence dispatches the recommendation. Every other decision the outline asked is an Assumption (A16–A24) with its veto surface.

1. **Who rewrites the enforcer wording** (was OQ3; block §5.3, IS1c minor 3) — SA1. Bound: SA1 carries the strings at `nixosModules/seatLane.nix:79` and `flake.nix:2414`, `:2424`, `:2428` under `areas: seat, isolation, platform`, or the Isolation plan types them. Recommendation: SA1 — the substance is SA's (`seat-spool` enforces since IS1c) and a cross-plan key for four strings is dearer than an `areas:` line; the audit already struck the fixture half (IS10). On "Isolation": SA1 is withdrawn, its Interface 2 assertion and strings move to an IS key, and SA4's and SA7's `dependsOn: SA1` become `IS10`.
2. **The payload seam and the warn fallback's life** (was OQ8; §5.5, 36a) — SA8. Bound: (a) `harnessPayload ? null`, asserted by the build and deployed by the wrapper, the symlink-and-warn path (`dsh-openrouter.sh:557-558`) alive only while the input is null and deleted next increment once Platform binds the payload; (b) the wrapper refuses at launch now; (c) SA waits for Platform. Recommendation: (a) — (b) locks the operator out of the seat that drives the batch (69a) while the payload lives in `~/flakes/dsh-harness`; (c) leaves invariant 4's one measured violation unowned for an increment. On (b): SA8 Interface 3 becomes `die 5` with the deploy recipe, M4 inverts, drill step 7 changes. On (c): SA8 is withdrawn and SA9 loses `## The payload seam`.
3. **SA1's commit subject after the audit's cut** (was OQ12) — SA1. The audit struck the fixture edit but left the subject "the seat-vm fixture sets waveJobs below its maxUnits, and …", which G4's `commit-msg` hook honours byte for byte while it misdescribes the diff. Bound: the corrected subject `seat: the cap's messages name seat-spool, the enforcer since IS1c (test: seat-vm, seat-eval)`, or the audited subject verbatim. Recommendation: the corrected subject — SA1's heading and `commit subject` line carry it (`check --draft` confirms it is not a landed subject). On "audited verbatim": both revert and the review tells the gate why the subject names an edit the diff lacks.

## Charter-to-task map

| Charter item (§6 increment 2, SA) | Decision | Tasks |
|---|---|---|
| N seats with allocated ports | 13b, 72a | SA3 (the allocator), SA4 (the lane option, its assertions, the two-seat VM proof) |
| The drive launch at `danger-full-access`, job seats default | 57a | SA5 |
| The three hooks running the same scripts | 58a, 21c | SA6 |
| Ritual scope: driver only | 60a | SA5 (`SEAT_MODE`), SA6 (the pass-through) |
| The off-tree memory store under the evidence store | 59a, 40a | SA7 |
| The harness payload into `/nix/store` — SA's seam for Platform's build | 36a | SA8 (the binding is Platform's) |
| IS1c's three minors owed to `SPEC-SA` | 72a as corrected | SA1 (minor 3), SA2 (minors 1, 2) |
| The live `flake-check` red in an SA-owned file (`seat-vm.nix:170`) | — | IS10 (Isolation's draft); SA1 depends on it |
| The operator surface, and the job-directory contract Helm's list reads | 13b | SA9 |

## Decisions relied on

`docs/decisions/2026-09-09-redesign-answers.md`, by number: **13b** N seats, backend-allocated ports, Helm's list (SA3, SA4; SA9 documents the contract; the list is Helm's) · **21c** the inbox only, no self-nudges (SA6's Stop never blocks) · **36a** the payload into the package (SA8) · **40a** per-subsystem memory and backup rows (SA7) · **52a** `policies.md` wins on the trailer (A24) · **57a** drive at `danger-full-access`, the guard stays the boundary, job seats default (SA5) · **58a** three hooks, the same scripts (SA6) · **59a** the rules source is KN's; the seat's memory is a machine-local store under the evidence store (SA7) · **60a** the driver only (SA5's `SEAT_MODE`, SA6's pass-through) · **69a** the seat drives the batch (SA5–SA8 shape that session and keep it launchable) · **72a** as corrected by IS1c, the spool enforces (SA1, SA2) · **76a** SD11b/SD11c are increment 0's, outside · **§4/§6 amendments**: no SA task touches the lane, the ZDR exception (`seatLane.nix:182`) or the model list; `--broker` stays in all three modes.

## Invariant bindings

Brief §3, verbatim numbering, whole invariants (the block's warning: none is breached at this anchor, so the bindings are not written against a live breach):

- **1** (baskets): no task mounts, tears down or reads a basket. **2** (no plaintext credential): no task touches the key path or the broker; SA5 changes dsh's permission prompts, not egress; SA8 deploys documents. **3** (one chokepoint): `--broker` stays in all three `seat-run.py` modes (A6); SA3/SA4's ports bind the web UI on the namespace address, not an egress path.
- **4** (reproducible; imperative setup is a bug): SA8 answers the two hand-made symlinks — the one measured live violation in the seat path; SA7's directory is tmpfiles-declared, SA4's range an option with a default. **5** (policy as Nix): SA4 and SA7 are options written to `/etc` in the caps' idiom; SA8's payload is a store path. **6** (dsh plugins, promotion): SA6's `seat-hooks.py` and SA8's payload are repo-authored or store-built, never promoted from a basket. **G8**: the memory store is machine-local; nothing sends a byte the broker does not already see. Blast radius stated once: SA5 widens the drive seat's *prompting* only (the PreToolUse guard, the kernel confinement and the broker are untouched — SA5 Interface 3 proves the first), and SA7 adds one writable path already inside `-/var/lib/evidence` (`seatLane.nix:311`); a job seat gains neither.

## Assumptions

Measured at `920ef3e` on 2026-09-12 02:55 UTC (`git log --oneline -1`; `date -u`) by re-running the block's own commands, and re-checked by this fill at `21f6a6a` (every anchor below re-resolved unchanged); G11 re-runs every integer at commit time.

- **A1 — FA11 has landed; no SA task waits on `fa11a`.** `grep -c claude-fable pkgs/dsh-openrouter/dsh-openrouter.sh` → `3`; `git log --oneline -1 -- pkgs/dsh-openrouter/dsh-openrouter.sh` → `0081322`; `wc -l` → 805. The block's post-FA11 anchors hold: the payload comment at `:534-535`, `warn_missing_payload` defined at `:544`, its two calls at `:557-558`, `export DSH_PERMISSION_MODE=$permission` at `:562`, `hooks_json=$DSH_HOME/hooks.json` at `:689`, the `hooks.json` heredoc `:709-733`, the bridge's overlay insert `:735-740`, the three `exec` lines at `:762`, `:767`, and the `web` arm after `:771` (`grep -n 'dsh-harness\|warn_missing_payload\|DSH_PERMISSION_MODE\|hooks_json\|exec "\$node_bin"' pkgs/dsh-openrouter/dsh-openrouter.sh`). The wrapper already accepts `--permission MODE` with `read-only | workspace-write | danger-full-access` (`:55`, `:115-117`, `:235-237`), default `${DSH_PERMISSION_MODE:-workspace-write}` (`:93`).
- **A2 — the hook mechanism is in-tree.** The `@deepseek-ai/dsh-hooks-claude-code` bridge runs Claude Code command hooks on dsh's seams (`:641-643`), only `hookSpecificOutput.permissionDecision` acts (`:653`); the generated `hooks.json` declares only `PreToolUse` with three matchers (`:712-731`). Which of SessionStart, PreCompact and Stop the bridge fires is **UNMEASURED** — SA6 measures it first (A20).
- **A3 — the live `flake-check` red.** `grep -n 'maxUnits\|waveJobs' tests/integration/seat-vm.nix` → only `170:        maxUnits = 2;`; `grep -n 'waveJobs = \|default = cfg.waveJobs' nixosModules/seatLane.nix` → `:73` (default 8), `:78` (`cfg.waveJobs + 1`); the fixture trips `maxUnits > waveJobs` (`seatLane.nix:133`). IS10 fixes the fixture; SA1 depends on it.
- **A4 — the enforcer wording.** `grep -n 'before seat-submit refuses' nixosModules/seatLane.nix` → `:79`; `grep -n 'seat-submit enforces' flake.nix` → `:2424`, `:2428` (the two `seat-eval` messages); the IS1 comment at `:2414` — re-resolve at commit.
- **A5 — `_poll`.** `grep -n 'def _poll\|10800\|POLL_INTERVAL =' pkgs/seat/seat-submit.py` → `:61 DEFAULT_TIMEOUT = 10800`, `:176 def _poll`; `_poll` waits for `result.txt` at `:181-183`, streams `stdout.txt` at `:231-234`, reads `exit_code.txt` at `:236-245`, and never opens `result.txt`. `--timeout` is an argparse float at `:261`; the two call sites are `:376` (`started=False`) and `:407` (`started=True`). The spool's refusal writer `_write_failed_result` is `seat-spool.py:183-188` (`FACTORY-RESULT status=failed` then `seat-spool: <note>`).
- **A6 — `seat-run.py`.** `grep -n 'DSH_HOME\|SEAT_JOB_ID\|--port\|--broker\|permission' pkgs/seat/seat-run.py` → exports at `:77`, `:83`; `--broker` at `:94`, `:110`, `:123`; `--port` at `:117`, `:128`; `port = job["port"]` at `:102`; no `permission` anywhere.
- **A7 — sizes.** `wc -l`: `seat-submit.py` 415, `seat-spool.py` 259, `seat-run.py` 195, `dsh-openrouter/default.nix` 131, `seat-vm.nix` 704, `80-seat-driver.bats` 4167; `grep -c '^@test' tests/unit/70-dsh-openrouter.bats` → 125, `tests/unit/94-seat-harness.bats` → 71.
- **A8 — the live host.** `cat /etc/seat-lane/max-units /etc/seat-lane/wave-jobs` → `9`, `8`; `command -v seat-submit` → `/run/current-system/sw/bin/seat-submit`; generation 55 (block).
- **A9 — no spec, no plan, no SA run yet.** `ls docs/superpowers/specs/2026-09-10-seat-harness-design.md docs/superpowers/plans/2026-09-10-seat-harness.md docs/superpowers/plans/2026-09-11-seat-harness.md` → three "No such file"; `ls ~/factory/runs | grep -i '^sa'` → nothing.
- **A10 — ownership (block §1, §3, not re-run).** SA's `owns` are the ten globs at `subsystems.toml:125-136`; `nixosModules/seatLane.nix` → `isolation`, `flake.nix` → `platform`, `docs/runbooks/seat.md` → `knowledge`, `tools/factory/*` → `factory` under `file_area`; every task below that spans two areas carries `areas:` (G9).
- **A11 — the guard's contract (block §2, not re-run).** `hook-guard.py:1-40` deny-only, exit 0 on every path; `PROTECTED_ABSOLUTE` at `:86-93` — SA7's memory directory is deliberately not in it. `seatLane.nix:309-316` already lists `-/var/lib/evidence` in `ReadWritePaths`; SA7 adds the memory directory as its own explicit row so the grant is visible in a diff.
- **A12 — the record's priors (block §4, not re-run).** Defect classes over SA's 21 ledger rows: `vacuous` 7, `implementer` 7, `missing-case` 4, `underspecified` 3 — the shapes the mutants below are written against.
- **A13 — `seat-assertion-negative` has five arms** (`flake.nix:2440-2445`, fixtures `seatBadKeySystem`, `seatBadEnvSystem`, `seatMaxUnitsZeroSystem`, `seatMaxUnitsEqWaveSystem` `:878`, `seatWaveJobsZeroSystem` `:818`). SA4 adds two (a range one port too narrow; a range outside `webPortRange`), SA8 one (a payload without `skills/`) — eight arms once both land, in either order.
- **A14 — the VM's fixed ports.** `grep -n '432[0-9][0-9]' tests/integration/seat-vm.nix` → first line per port: `43201` at `:329` (step 6), `43204`/`43205` at `:587` (step 11b's `for _port in`), `43202` at `:642` (step 12), `43203` at `:697` (step 13); the VM's `webPortRange` is the module default `43200-43299` (`seatLane.nix:61-64`). SA4's default range `43210-43219` lies inside it and collides with none of them.
- **A15 — the pytest seams.** `tests/seat/test_seat_submit.py` patches `subprocess.run` (`:39-40`, `:59`), sets `SEAT_MAX_UNITS` via `monkeypatch.setenv` (`:936`, `:959`) and already has a `_poll` timeout case at `:323` (`test_timeout_exits_124_and_stops_the_unit`); `tests/seat/test_seat_spool.py` drives `main` through `_run_spool` (`:98`) with a fake `--systemctl` (`:196`); `tests/seat/test_seat_run.py` records the launch argv through `_popen_fake` (`:66`).

Demoted operator questions — each the outline's own recommendation applied into the field it names, with its bound, cite and veto surface:

- **A16 (was OQ1)** — `_poll` reads `result.txt` after the exit code and emits it (bound: the spool writes its refusal where `_poll` already looks; block §5.1, IS1c minor 1) — the draft's own recommendation, unopposed; veto surface: SA2 **Files** bullet 1.
- **A17 (was OQ2)** — the poll bound is `SEAT_POLL_TIMEOUT` beside `--timeout` (bound: `--timeout` alone; a pytest timeout plugin; §5.2, minor 2) — the draft's own recommendation, unopposed; veto surface: SA2 Interface 4.
- **A18 (was OQ4)** — the allocator is `seat-spool`, the range defaults to `43210-43219` (bound: `seat-submit` or Helm's backend; any unprivileged range ≥ `maxUnits` = 9 wide; §5.4, 13b) — the draft's own recommendation, unopposed; veto surface: SA3 **Files** (`_port_range`), SA4's option default.
- **A19 (was OQ5)** — `seat-run.py`'s drive branch passes `--permission danger-full-access` and exports `SEAT_MODE` for all three modes (bound: the wrapper or the unit env sets the preset; a marker file or argv discriminates; §5.6, §5.9, 57a, 60a) — the draft's own recommendation, unopposed; veto surface: SA5 **Files**.
- **A20 (was OQ6)** — SA6 measures which events the `@deepseek-ai/dsh-hooks-claude-code` bridge fires (`dsh-openrouter.sh:641-643`, `:689`), emulates an unfired SessionStart or Stop at the seat's own boundary, leaves an unfired PreCompact to Platform's `patches/dsh/` series (37a) (bound: wait for the patch for all three; §5.7, 58a) — the draft's own recommendation, unopposed; veto surface: SA6 Step 4, Interface 5.
- **A21 (was OQ7)** — `services.seat-lane.memoryDir`, default `/var/lib/evidence/seat-memory`, tmpfiles + `ReadWritePaths`, linked at `$DSH_HOME/memory` → `<memoryDir>/<cwd-key>`; its backup row SA's own (bound: any directory under `/var/lib/evidence`, never tracked; §5.8, 59a, 40a) — the draft's own recommendation, unopposed; veto surface: SA7 **Files**.
- **A22 (was OQ9)** — after Platform's absorption, one `PR` manifest edit adds the payload path to SA's `owns` (`subsystems.toml:125-136`), because `check` reads the manifest, not the charter (bound: `charter:49` stays the only statement; §5.10) — the draft's own recommendation, unopposed; veto surface: the manifest row; outside this plan.
- **A23 (was OQ10)** — (a) Evidence closes `docs/bugs/2026-09-09-broker-bypass.md` on `FIX1`'s evidence (bound: an SA closing round, `areas: seat, evidence`); (b) `FACTORY_SEAT_UNIT=0` (`factory-task:359-377`, `:460-471`) stays the logged, refuse-by-default opt-out until Factory retires `factory-task` (bound: removed now); §5.11 — the draft's own recommendations, unopposed; veto surface: `## Not in this plan`.
- **A24 (was OQ11)** — the operator strikes `R-conv-seat-one-trailer`'s source line (`~/flakes/dsh-harness/AGENTS.md:45`) by hand now, because every SA gate reads G3's two trailers and the seat's bootstrap tells it one (bound: wait for KN's generated AGENTS.md, increment 4; `rules.toml:563-570`, 52a) — the draft's own recommendation, unopposed; veto surface: the operator's act, drill step 9.

## Waves

Derived by hand from `dependsOn` and touch overlap, because `tasks.py waves` reads only `docs/superpowers/plans/` and cannot schedule SA1 until IS10 exists in the graph — `tasks.py check --draft` on this file today: `SA1 dependsOn IS10: unknown key`, the one expected line. **The SA1 → IS10 edge resolves when the Isolation plan lands** (`2026-09-11-isolation.md`, IS10 `(code, XS)`, `touches: tests/integration/seat-vm.nix`, `areas: isolation, seat`); until then `waves --json` returns SA2, SA5, SA8 then SA3, SA6 and omits SA1, SA4, SA7, SA9 (the judgement's measurement). Wave 1: SA2 (`_poll`), SA5 (the preset), SA8 (the payload seam); SA1 joins it once IS10 lands. Wave 2: SA3 (on SA2), SA6 (on SA5), SA7 (on SA1). Wave 3: SA4 (on SA1, SA3). Wave 4: SA9 (on SA3–SA8). Touch groups: SA1, SA4, SA8 share `flake.nix`; SA5–SA8 share `dsh-openrouter.sh`; so SA8 and SA1 serialise inside wave 1 and SA6 and SA7 inside wave 2. Re-run `nix develop -c python3 pkgs/evidence/tasks.py --root . waves --repo nixos-agent-env --plan 2026-09-11-seat-harness.md --json` after IS10 lands and paste it here (G11).

## Cross-plan

**Measured against the live graph, 2026-09-14** (`nix develop -c python3 pkgs/evidence/tasks.py --root . conflicts --repo nixos-agent-env` → three lines, all `EV6 × HH6|HH8|HH9: flake.nix`; the draft is invisible to it, so this plan's `touches` were matched against every open live key by hand):

- **`flake.nix`** — open live keys `EV6` (blocked), `HH6` (ready), `HH8`, `HH9` (blocked); SA1, SA4, SA8 join that queue behind them (their arms are `helm-home` and `patches` checks, disjoint from `seat-eval` / `seat-assertion-negative`, `:2226-2458`), in the order SA1, SA8, SA4. A rebase conflict is confined to the `seat-assertion-negative` `let` block and resolved by keeping every arm.
- **`nixosModules/seatLane.nix`** — `IS5`, `IS5b` are `ran`, not integrated; SA1, SA4, SA7 land after `IS5b` integrates. IS5b's hunk is the broker policy region; SA's are `:79`, `:61-64`/`:110-135`, `:196-202`/`:234-258`/`:309-316` — distinct.
- Every other touched file (`seat-vm.nix`, `pkgs/dsh-openrouter/*`, `pkgs/seat/*`, `tests/seat/*`, `tests/unit/70-*`, `94-*`, `docs/runbooks/seat.md`) — no open live key touches it (`FA11` landed; `SD11b`/`SD11c` edit the sibling, not this tree).

**Prediction — the sibling drafts of this batch, which land together in dependency order** (labelled a prediction: none of these keys is in the graph yet):

- `flake.nix`: PL2–PL5 (Platform changes the package set every arm evaluates), IS11–IS20, then SA1, SA8, SA4, then FA23, HM3, EV16, GN10–GN12, KN13–KN19. `nixosModules/seatLane.nix`: IS20 (`:389`) → SA1 → SA4 → SA7. `tests/integration/seat-vm.nix`: IS10 (until it lands nothing else is observable) → IS20 → SA4 (step 14) → SA7 (step 15); SA1 no longer touches it (audit 5a). `pkgs/dsh-openrouter/dsh-openrouter.sh` (no sibling): SA5 (`:762-771`), SA8 (`:534-558`), SA6 (`:689-740`), SA7 (after `:558`).
- **Platform:** the absorption of `~/flakes/dsh-harness` and the binding of `harnessPayload` are PL's (charter §6); SA8 leaves the input they fill; the fallback's deletion, a PreCompact patch under `patches/dsh/` (A20) and the memory store's backup row in `hosts/core/proton-backup.nix` (40a; GN10 and PL6 add rows there) are next-increment SA tasks on PL keys.
- **Factory:** SA2 makes `seat-submit` emit the `result.txt` block after the streamed stdout — `factory-task` already parses `FACTORY-RESULT` from that stream and must keep doing so; `FACTORY_SEAT_UNIT=0` is FA's (A23b); `factory-wave` is untouched. FA's edits to `tools/factory/seat/*` (DF7, DF8, FA12, FA16) need no order against SA: SA6's bats cases drive `seat-hooks` directly, never `factory-task`.
- **Helm:** 13b's session list reads the job-directory contract SA9 documents and calls `seat-submit` without `--port`; Helm never allocates (A18). HM3/HM5/IS13's `helm.nix` edits are disjoint.
- **Evidence:** `subsystems.toml:139` already names this file; `PLAN-SA`'s typed touches (`2026-09-10-seat-harness.md`, `program.md:553-555`) are reconciled by a PR/EV row. EV's ingest must ignore `/var/lib/evidence/seat-memory`. The bug close-out (A23a) and the six-row `plan-defects.toml` gap are EV's.
- **Knowledge:** `docs/runbooks/seat.md` is SA9's only touch (area `knowledge`; one file spans no second area). SA6 calls the workspace's `tools/session-start.sh` and `tools/ritual.sh` — KN keeps those paths or bumps SA6; KN's rules source (increment 4) resolves `R-conv-seat-one-trailer` for good (A24 is the interim). **Program:** the manifest `owns` widening (A22).

## Operator

**Switch.** SA4 and SA7 change the lane module and SA5–SA8 change the packages the unit runs, so this increment ends with the operator's switch (G1); the drill runs after it. Until then every task is build-only and its checks prove it in the sandbox and the VM.

**Drill** (each step names the task it proves; the composed increment drill takes these lines verbatim; each line's rollback is the generation rollback below):

1. `nix flake check -L` — green, including `seat-vm` (IS10 closes the live `flake-check` red; SA1 keeps it green).
2. `seat-submit web --workspace ~/nixos-agent-env --dsh-home ~/.local/share/dsh-openrouter` twice, no `--port` — two job ids and two distinct ports inside `cat /etc/seat-lane/port-range`; `ip netns exec egress-seat ss -ltn` shows both bound (SA3, SA4). A third launch with `--port <one of them>` returns an id whose `cat /var/lib/seat/jobs/<id>/result.txt` reads `seat-spool: port <p> is held by seat@<other id>` (SA3).
3. With `SEAT_MAX_UNITS=1` exported for one `factory-task` headless launch while a seat runs — the run's `.log` carries `seat-spool: 1 seat units running, cap 1`, not a bare job id (SA2).
4. `seat-submit drive …` then `journalctl -u seat@<id>` — the launch line reads `dsh-openrouter: <model> via <url>, danger-full-access, …`; `dsh-openrouter --denials 1` after the seat's first refused `sudo` probe shows the denial, i.e. the guard is still wired under the preset (SA5). A headless seat's journal line reads `workspace-write` (SA5).
5. The drive seat's first turn shows the session-start facts; a headless job's transcript (`~/factory/runs/<run>/*.log`) shows no ritual output (SA6).
6. The drive seat writes one memory note; after its unit ends, `ls /var/lib/evidence/seat-memory/<cwd-key>/` lists it and `git -C ~/nixos-agent-env status --porcelain` is clean (SA7).
7. `nix build .#dsh-openrouter --no-link --print-out-paths` and the wrapper's launch log — the payload still deploys from the two symlinks until Platform binds `harnessPayload` (SA8). Then, before the switch, `nix build .#nixosConfigurations.core.config.system.build.toplevel` (writes `./result`) and `nix store diff-closures /run/current-system ./result`. **Prediction** (design §4 A2; never a fact before the code exists): `dsh-openrouter` (the wrapper plus `seat-hooks`), `seat` (its three scripts), `etc` (`seat-lane/port-range`) and `tmpfiles.d` (the `seat-memory` row) change; the `seat@` unit gains `SEAT_MEMORY_DIR` and one `ReadWritePaths` entry; `dsh`, the broker and every non-seat package are unchanged; no unit is added or removed. The measured delta is pasted beside this line.
8. `docs/runbooks/seat.md` answers steps 2–7 without this plan open (SA9).
9. (A24, the operator's own act, outside the tree) the one-trailer line struck from `~/flakes/dsh-harness/AGENTS.md`: `grep -c 'exactly ONE machine-set trailer' ~/flakes/dsh-harness/AGENTS.md` → `0`.

**Rollback.** The previous generation (the operator's `nixos-rebuild --rollback` or the boot menu; gen 55 is the last switched state). Every option this plan adds has a default and every new file under `/var/lib/seat/jobs` and `/var/lib/evidence/seat-memory` is ignored by the older packages, so a rollback needs no cleanup; a job submitted under the new `job.json` schema (`port: null`) is refused by the old `seat-spool`'s port validation (`test_refuses_bad_port_web`, `test_seat_spool.py:294`) with a `result.txt`, never started. The `live-gen28` restore point is unaffected.

## Dispatch

Run name **`sa1`** — `ls ~/factory/runs | grep -x sa1` → empty (2026-09-14; no `sa*` run among 468). Preconditions: this file at `docs/superpowers/plans/2026-09-11-seat-harness.md` (`subsystems.toml:139`) and IS10 in the graph. Measured today on the draft path: `factory-dispatch sa1 /home/dalhaka/nixos-agent-env <this draft> --dry-run` → `factory-dispatch: nothing schedulable in 2026-09-11-seat-harness.md (all landed, in flight, or blocked)`, exit 0 — the graph query sees only the plans directory, so the real dry run is taken at landing. Per wave, `--dry-run` first with its output pasted here, then the same line without:

```
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-seat-harness.md tools/factory/seat/factory-dispatch sa1 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-seat-harness.md --dry-run
FACTORY_PLAN=/home/dalhaka/nixos-agent-env/docs/superpowers/plans/2026-09-11-seat-harness.md tools/factory/seat/factory-dispatch sa1 /home/dalhaka/nixos-agent-env docs/superpowers/plans/2026-09-11-seat-harness.md
```

Expected groups (a prediction until pasted): wave 1 `"SA2" "SA5" "SA1 SA8"` (`flake.nix`; before IS10 lands, `"SA2" "SA5" "SA8"`), wave 2 `"SA3" "SA6 SA7"` (`dsh-openrouter.sh`), wave 3 `"SA4"`, wave 4 `"SA9"`. The regenerated board block is committed before every dispatch (G6); an unset `FACTORY_PLAN` is refused (the A5 guard).

Per landing, the recipe of design §4 A1, in order: (1) in the workspace keep only the one commit the section names — `git -C ~/factory/ws/sa1/<KEY> log --format='%h %s' <base>..task/<KEY>`, then `git -C ~/factory/ws/sa1/<KEY> reset --hard <that sha>`; (2) if main moved under a file the task touches, merge it into the task branch first — `git -C ~/factory/ws/sa1/<KEY> fetch ~/nixos-agent-env main && git -C ~/factory/ws/sa1/<KEY> merge --no-edit FETCH_HEAD` (expected for every `flake.nix` and `seatLane.nix` task here, given the queue in `## Cross-plan`); (3) commit the review; (4) `factory-integrate sa1 ~/nixos-agent-env <KEY>` then `git -C ~/nixos-agent-env pull --ff-only ~/factory/base/nixos-agent-env integ/sa1`, gated on both exit codes; (5) dispatch what it unblocks (A7): SA2 → SA3; SA5 → SA6; SA1 → SA7 and, with SA3, SA4; SA3–SA8 → SA9. Relaunch after a dead seat (A6): `FACTORY_PLAN=<plan> setsid -f bash -c 'exec tools/factory/seat/factory-wave sa1b ~/nixos-agent-env <KEY> >> ~/factory/runs/sa1b.wave.log 2>&1' </dev/null`, the dead seat's diff kept in `~/factory/ws/sa1/<KEY>`.

## Anticipation

- **SA6's Step 1 may measure that the bridge fires none of the three events.** Then SessionStart and Stop are emulated at the wrapper's boundaries (Step 4b, its own bats case and exit-code contract) and PreCompact is a Platform patch follow-up; the task lands smaller and the commit body says which arm was taken (A20).
- **SA6 adds a seat hook (A13).** The dsh bridge runs `seat-hooks` from the store (`runtimeEnv.DSH_SEAT_HOOKS`, the package's python3); it resolves `tools/session-start.sh` and `tools/ritual.sh` from the workspace tree `seat-run.py` cd'd into, never the live generation's packaged `evidence`; the loop-guard field is `stop_hook_active`, read and logged, never a block (Interface 4). No second reader of a derived file is added.
- **The `flake.nix` queue forces merges (A1 step 2):** SA1, SA4, SA8 land behind HH6/EV6/HH8/HH9 and the batch's PL2–PL5, IS11–IS20; a conflict is confined to the `seat-assertion-negative` `let` block.
- **SA3's one unreachable race** (two overlapping spool runs) is closed by the unit's shape — `Type=oneshot` under a path unit, one instance ever — not by code (M6b; `seat-eval` pins both, `flake.nix:2393-2407`).
- **The switch delta is predicted, then measured** (A2): drill step 7 builds the toplevel before `diff-closures`; anything outside `dsh-openrouter`, `seat`, `etc` and `tmpfiles.d` in the delta is a finding.
- **No SA task adds a deny rule (A14) or closes an open claim (A8)**; the `seat-vm` `flake-check` red closes with IS10. **Handoff (A11):** "seat-harness: on the seat `sa1` wave N (<keys>); in gate <keys>; next <A7's unblocked keys>; operator owes the switch after SA7 and the A24 strike".

## Not in this plan

- Platform's absorption of `~/flakes/dsh-harness`, the binding of `harnessPayload`, the patch series (37a, 38b), any `pkgs/dsh/*` bump; SA8's fallback deletion and the memory store's backup row (next SA increment).
- Knowledge's rules source and generated CLAUDE.md/AGENTS.md (59a, 52a), the audit of the four AGENTS.md-sourced rules (54a), the final resolution of `R-conv-seat-one-trailer`. Helm's session list and backend (13b, 8a, 12c). SD11b/SD11c (76a; they edit the sibling).
- The broker-bypass close-out, `docs/ledger/bugs.toml` (EV4 on EV3), the `FACTORY_SEAT_UNIT=0` seam (A23); the `plan-defects.toml` gap (no numeric prior is derived here, only A12's class names); a `seat-submit --list` verb (Helm reads the job directory, SA9).
- The `seat-vm` fixture fix (IS10, Isolation's draft, audit 5a); the manifest `owns` widening (A22); whether `2026-09-07-seat-harness-redesign.md` is superseded (UNMEASURED; the manifest keeps both names); the drafter question for `SPEC-SA`/`PLAN-SA` (FA2's row); the ZDR exception's width (`seatLane.nix:182`, the operator's data-policy setting).

## Tasks

### SA1 (code, S) — the cap's messages name seat-spool, the enforcer since IS1c

**dependsOn:** IS10
**touches:** nixosModules/seatLane.nix, flake.nix
**areas:** seat, isolation, platform
**acceptance:** seat-vm, seat-eval
**commit subject:** `seat: the cap's messages name seat-spool, the enforcer since IS1c (test: seat-vm, seat-eval)`

**Why.** Since IS1c the running-unit cap is enforced by `seat-spool`, not `seat-submit` (`pkgs/seat/seat-spool.py:16-23`; `seat-submit.py:379-384` keeps only the started-path arm). Three operator-facing strings still say otherwise: `grep -n 'before seat-submit refuses' nixosModules/seatLane.nix` → `:79` (the `maxUnits` description), and `grep -n 'seat-submit enforces' flake.nix` → `:2424`, `:2428` (two `seat-eval` messages). IS1c's gate logged this as minor 3 (`program.md:757`). The wording is the operator's only description of the cap in `nixos-option` and in a failed `seat-eval`; a wrong actor name sends the operator to the wrong program when the cap refuses. The fixture half of the audited outline is IS10's; this task depends on it so `seat-vm` evaluates when this task's green step runs (A3).

**Files.**
- `nixosModules/seatLane.nix` (modify): the `maxUnits` description at `:79` — "before seat-submit refuses a launch (IS1, decision 72a)" → "before seat-spool refuses a launch (IS1, decision 72a; enforced by the spool since IS1c) — seat-submit's started path keeps a second arm"; and "Written to /etc/seat-lane/max-units for seat-submit to read" → "for seat-spool and seat-submit to read".
- `flake.nix` (modify): the two `seat-eval` messages at `:2424` and `:2428` — "(the running-unit cap seat-submit enforces)" → "(the running-unit cap seat-spool enforces)", "the file seat-submit reads" → "the file seat-spool reads"; the comment at `:2414` ("the running-unit cap seat-submit enforces, now") → "seat-spool enforces" (`grep -c 'seat-submit enforces\|file seat-submit reads' flake.nix` → `3` today, all three in this range); and one new `seat-eval` assertion (Interface 2) that pins the description's actor.

**Interfaces.**
1. `services.seat-lane.maxUnits`'s description names `seat-spool` as the enforcer and mentions `seat-submit` only as the started path's second arm; `nixos-option services.seat-lane.maxUnits` shows it.
2. `seat-eval` asserts a rule over the description `d = options.services.seat-lane.maxUnits.description`, not a phrase: (i) the first actor named is the enforcer — `lib.hasInfix "seat-spool" (lib.head (lib.splitString "seat-submit" d))`; (ii) every refusal is the spool's — `let p = lib.splitString " refuses" d; in builtins.length p >= 2 && lib.all (s: lib.hasSuffix "seat-spool" s) (lib.init p)`; message `seat-eval: services.seat-lane.maxUnits must name seat-spool as the cap's enforcer (IS1c)`. Any wording that names `seat-submit` before `seat-spool`, or credits any other noun with "refuses", reddens the check rather than surviving as prose.
3. Neither `seat-eval` cap-message change alters the assertion it labels; the five `seat-eval` cap assertions (`:2421-2429`) still hold at the module defaults.
4. `seat-vm` is unchanged by this task and stays green: the fixture is IS10's.

**Steps.**
1. **Red.** In the workspace (IS10 landed: `grep -c 'waveJobs = 1' tests/integration/seat-vm.nix` → `1`), add Interface 2's assertion to `seat-eval` before touching the description, then `nix build .#checks.x86_64-linux.seat-eval -L 2>&1 | tail -3` → `error: seat-eval: services.seat-lane.maxUnits must name seat-spool as the cap's enforcer (IS1c)`. Paste that line into the commit body.
2. Edit `nixosModules/seatLane.nix:79` as **Files** says; `grep -c 'before seat-submit refuses' nixosModules/seatLane.nix` → `0`; `grep -c 'seat-spool refuses' nixosModules/seatLane.nix` → `1`.
3. Edit `flake.nix:2414`, `:2424` and `:2428`; `grep -c 'seat-submit enforces\|file seat-submit reads' flake.nix` → `0` (from `3`).
4. **Green.** `nix build .#checks.x86_64-linux.seat-eval -L` → exit 0, `seat-eval-ok`; `nix build .#checks.x86_64-linux.seat-vm -L 2>&1 | tail -2` → `(finished: run the VM test)`, exit 0. `nix develop -c statix check nixosModules/seatLane.nix` → exit 0.
5. **Mutants.**
   - *M1 revert-description*: `git stash` the `seatLane.nix` hunk only (`git checkout -- nixosModules/seatLane.nix`); `nix build .#checks.x86_64-linux.seat-eval` → `error: seat-eval: services.seat-lane.maxUnits must name seat-spool as the cap's enforcer (IS1c)`. Restore with `git stash pop`.
   - *M2 second-actor*: keep "seat-spool refuses" and append "; seat-submit also refuses on its started path" → rule (ii)'s `init` segment ends with `seat-submit` → the same message. Kills any description that credits a second noun with refusing, whatever the phrasing.
   - *M2b first-named*: "seat-submit's started path keeps a second arm; seat-spool refuses a launch …" → rule (i) fails (the first segment before `seat-submit` holds no `seat-spool`) → the same message. Kills the reordering that leaves the operator reading `seat-submit` first.
   - *M3 negative control*: the unchanged `seat-vm` must pass — `nix build .#checks.x86_64-linux.seat-vm` → exit 0. Its discriminating mutant: `sed -i 's/waveJobs = 1;/waveJobs = 8;/' tests/integration/seat-vm.nix` → `error: … services.seat-lane.maxUnits (2) must be greater than services.seat-lane.waveJobs (8)`; revert with `git checkout -- tests/integration/seat-vm.nix` (a probe only — the file is not in this task's `touches` and the working tree must be clean of it before the commit).
6. Commit with the subject above (operator question 3: it is the corrected subject; on "audited verbatim" the heading and this line revert); body carries Step 1's red line, the M1 output, and the three `grep -c` counts.

**probes:**
- seatlane-old-wording: `grep -c 'before seat-submit refuses' nixosModules/seatLane.nix` :: le 0 :: SA1 Step 2
- flake-old-wording: `grep -c 'seat-submit enforces\|file seat-submit reads' flake.nix` :: le 0 :: SA1 Step 3

### SA2 (code, S) — a capped job's reason reaches factory-task, and the poll is bounded in test mode

**dependsOn:** none
**touches:** pkgs/seat/seat-submit.py, tests/seat/test_seat_submit.py
**acceptance:** seat-unit
**commit subject:** `seat: _poll reads result.txt and SEAT_POLL_TIMEOUT bounds it, so a capped job's reason reaches factory-task and a mutant reddens instead of hanging (test: seat-unit)`

**Why.** `_poll` (`pkgs/seat/seat-submit.py:176-245`) waits for `result.txt` to exist (`:181-183`), streams `stdout.txt` (`:231-234`) and returns `exit_code.txt` (`:236-245`) — it never opens `result.txt`. When `seat-spool` refuses a job at the cap it writes only `result.txt` (`seat-spool.py:183-188`: `FACTORY-RESULT status=failed` and `seat-spool: <count> seat units running, cap <cap>`) and never starts the unit, so no `stdout.txt` or `exit_code.txt` exists: `_poll` prints nothing, returns 0, and `factory-task` synthesises a generic `status=failed` with no reason (IS1c minor 1, `program.md:755`). Separately, the only bound on the wait is `--timeout` (`:261`, default `DEFAULT_TIMEOUT = 10800`, `:61`); a `>=` regression that lets a refused submit fall through to `_poll` hangs `seat-unit` for the full default — measured at 20 minutes before IS1c's gate killed it (minor 2, `program.md:756`).

**Files.**
- `pkgs/seat/seat-submit.py` (modify): `_poll` gains a final stage that reads `result.txt` and, when `stdout.txt` is absent or does not already end with the `FACTORY-RESULT` block, writes the block to stdout after the streamed stdout, then returns the exit code — `exit_code.txt`'s value when present, else 1 when `result.txt` carries `status=failed`, else 0. `_poll`'s effective timeout becomes `min(args.timeout, SEAT_POLL_TIMEOUT)` when the variable is set and a positive float; a malformed value prints `seat-submit: SEAT_POLL_TIMEOUT=<raw> is not a positive number` and exits 2 before any wait. The module docstring (`:14-16`, `:39-46`) gains both facts.
- `tests/seat/test_seat_submit.py` (modify): an autouse fixture `_bounded_poll` that `monkeypatch.setenv("SEAT_POLL_TIMEOUT", "3")`; five new cases (Steps 1, 5). The shape every case copies is `test_headless_waits_streams_and_propagates_exit_code` (`:274-300`): fixtures `ws, dsh, tmp_path, monkeypatch, _no_systemctl`; `jobs = tmp_path / "jobs"`; `argv = ["--jobs-dir", str(jobs), "headless", "--workspace", str(ws), "--dsh-home", str(dsh), "--model", "m", "--effort", "off"]`; `monkeypatch.setattr(seat_submit, "POLL_INTERVAL", 0)`; a `_sleep(_seconds)` stand-in for the unit, patched over `time.sleep`, that on the poll loop's first call writes the job directory — `job_id = _no_systemctl[0][2][len("seat@"):]` (from the recorded `systemctl start` argv; under `--no-start`, from the printed first stdout line via `_job_dir(jobs, printed_id)`, `:97`), then `(jobs / job_id / "result.txt").write_text(...)`, likewise `stdout.txt` and `exit_code.txt` — and `seat_submit.main(argv)`, whose return is the exit code. `_no_systemctl` (`:58-70`) is the autouse `subprocess.run` replacement that records argv and answers `list-units` with zero units. The refused case's stand-in writes only `result.txt`.

**Interfaces.**
1. After `result.txt` exists, `seat-submit` (started path or `--no-start --wait`) emits `stdout.txt` verbatim, then — if that stream lacks a `FACTORY-RESULT` line — the contents of `result.txt`, so every `FACTORY-*` label `seat-run.py` or `seat-spool` wrote appears exactly once on `seat-submit`'s stdout.
2. A refused job (no `exit_code.txt`, `result.txt` with `status=failed`) exits 1, never 0; the spool's reason line reaches stdout.
3. A job with `exit_code.txt` keeps that code unchanged (the existing contract, `test_headless_waits_streams_and_propagates_exit_code`, `:274`).
4. `SEAT_POLL_TIMEOUT=<seconds>` caps every `_poll` deadline; unset, `--timeout` alone rules. Malformed → exit 2 with the message above.
5. `seat-run.py`'s `result.txt` is emitted once — the stream is not doubled when `stdout.txt` already carries the block.

**Steps.**
1. **Red.** Add `test_refused_job_reason_reaches_stdout_exit_1`: write `job.json`, a `result.txt` of `FACTORY-RESULT status=failed\nseat-spool: 2 seat units running, cap 2\n`, no `stdout.txt`, no `exit_code.txt`; run `cmd_submit(["headless","--no-start","--wait",…])` under the `_no_systemctl` patch; assert `capsys` stdout contains `seat-spool: 2 seat units running, cap 2` and the return is 1. `nix develop -c pytest tests/seat/test_seat_submit.py -q -k refused_job_reason` → `1 failed` with `AssertionError: assert 'seat-spool: 2 seat units' in ''` and `assert 0 == 1`. Add `test_poll_timeout_env_bounds_the_wait`: `SEAT_POLL_TIMEOUT=0.5`, `--timeout 10800`, never create `result.txt`, wrap in `time.monotonic()`; assert return 124 and elapsed < 5 s → today this case runs 10 800 s; run it with `timeout 30 nix develop -c pytest … -k timeout_env` → exit 124 from `timeout`, pasted as the red. Add `test_poll_timeout_env_malformed_exits_2` (`SEAT_POLL_TIMEOUT=abc` → assert 2 and the message) → `1 failed`, `assert 124 == 2` (it timed out instead; run under the same 30 s `timeout`).
2. Implement Interface 4 in `_poll`'s callers: a `_poll_timeout(cli_timeout)` helper resolving the env var, called at `:376` and `:407`; the malformed branch returns 2 before `_poll`.
3. Implement Interfaces 1, 2, 3, 5: after the `stdout.txt` stream, read `result.txt`; if `"FACTORY-RESULT" not in streamed`, `sys.stdout.write(result_text)`; compute the exit code as **Files** says.
4. Add the autouse `_bounded_poll` fixture (`SEAT_POLL_TIMEOUT=3`), and `test_result_block_not_doubled` (a `stdout.txt` that already ends with the four labels; assert `capsys` stdout counts `FACTORY-RESULT` once) and `test_poll_timeout_unset_uses_cli_timeout` (`monkeypatch.delenv`, `--timeout 0.5`, assert 124 within 5 s — the existing `:323` case's shape, pinned to the CLI path).
5. **Green.** `nix develop -c pytest tests/seat -q` → `N passed` where N is today's count plus 5 (`nix develop -c pytest tests/seat -q --co | tail -1` before and after; paste both). `nix build .#checks.x86_64-linux.seat-unit -L` → exit 0. `nix develop -c ruff check pkgs/seat tests/seat && nix develop -c ruff format --check pkgs/seat tests/seat` → exit 0.
6. **Mutants.**
   - *M1 no-result-read*: delete the `result.txt` read (Step 3) → `test_refused_job_reason_reaches_stdout_exit_1` fails `assert 'seat-spool: 2 seat units' in ''`.
   - *M2 exit-zero-on-refusal*: replace the `status=failed → 1` branch with `0` → the same case fails `assert 0 == 1`.
   - *M3 always-append*: drop the `"FACTORY-RESULT" not in streamed` guard → `test_result_block_not_doubled` fails `assert 2 == 1`.
   - *M4 ignore-env*: make `_poll_timeout` return `cli_timeout` unconditionally → `test_poll_timeout_env_bounds_the_wait` and `_malformed_exits_2` fail (the first by exceeding its 5 s budget: `assert 10800.0 < 5` after the fixture's own `--timeout 10` guard; set `--timeout 10` in the case so the mutant fails in ten seconds, not three hours).
   - *M5 the minor-2 regression itself*: change `count >= cap` at `:393` to `count > cap` → `test_cap_refuses_at_max_counting_activating` (`:939`) fails within `SEAT_POLL_TIMEOUT=3` s with `assert 124 == 3` instead of hanging: paste the wall time (`pytest --durations=1`) to prove minor 2 is closed.
   - *Negative control*: `test_headless_waits_streams_and_propagates_exit_code` (`:274`) must still pass; its discriminating mutant is M2's sibling — return `1` for every job → it fails `assert 1 == 7` (whatever code the fixture writes; re-read the case).
7. Commit; body pastes Step 1's three reds, Step 5's two counts, M5's duration.

**probes:**
- poll-reads-result: `grep -c 'result_text\|open(result_path' pkgs/seat/seat-submit.py` :: ge 1 :: SA2 Step 3
- poll-timeout-env: `grep -c SEAT_POLL_TIMEOUT pkgs/seat/seat-submit.py` :: ge 2 :: SA2 Step 2

### SA3 (code, M) — seat-spool allocates each web or drive seat's port from a range, and --port becomes a request

**dependsOn:** SA2
**touches:** pkgs/seat/seat-submit.py, pkgs/seat/seat-spool.py, pkgs/seat/seat-run.py, tests/seat/test_seat_submit.py, tests/seat/test_seat_spool.py, tests/seat/test_seat_run.py
**acceptance:** seat-unit
**commit subject:** `seat: seat-spool allocates each web or drive seat's port from a range, and --port becomes a request (test: seat-unit)`

**Why.** `web` and `drive` require the caller to pick a port: `seat-submit drive` refuses without one (`seat-submit.py:287-290`, "drive needs --port"), writes it into `job.json` (`:336`), and `seat-run.py` passes it verbatim (`:102`, `:117`, `:128`). Every historical drive job hard-coded 43210 (block §5.4), so a second concurrent drive seat died on `Address already in use`. Decision 13b wants N seats with backend-allocated ports; the one actor that sees every job directory and every running unit is `seat-spool` (`seat-spool.py:4-27`, root, one `systemctl list-units` per run at `:157-178`). The spool today validates `port` as an int 1024–65535 for web/drive (`test_refuses_bad_port_web`, `test_seat_spool.py:294`) and would refuse `null`. The VM (`seat-vm.nix:327-329`, `:589-592`, `:640-642`) still passes explicit ports, which stay valid as requests.

**Files.**
- `pkgs/seat/seat-submit.py` (modify): `--port` optional for `drive` too (drop `:288-290`; keep the 1024–65535 range check when given); `job.json` gains `"port": null` when unset; after the marker is written (started path or `--no-start`) for web/drive, wait — under SA2's `_poll_timeout` bound — for `.spooled` or `result.txt`, then print `port=<n>` from the rewritten `job.json` (or the `result.txt` reason, exit 1, via SA2's path). Docstring updated.
- `pkgs/seat/seat-spool.py` (modify): `_port_range()` — `SEAT_PORT_RANGE` env, else `/etc/seat-lane/port-range`, else `"43210-43219"`; parsed `a-b`, malformed → exit 1 `seat-spool: cannot read the port range (...)` in the cap's idiom (`:127-155`). `_held_ports(jobs_dir, systemctl)` — the `port` of every job whose unit is active/activating (reusing the `list-units` output at `:157`) plus every `.spooled` job without `exit_code.txt`. `_allocate(job, held, rng)` — an explicit `port` in `held` → refuse, `result.txt` `seat-spool: port <p> is held by seat@<id>`; `null` → the lowest free port in the range, none free → `seat-spool: no free port in <a>-<b> (<n> held)`; the chosen port is written back into `job.json` (0600, same owner) **before** `.spooled` is written. Validation at `:285-300`'s target accepts `null` for web/drive.
- `pkgs/seat/seat-run.py` (modify): `port = job["port"]` (`:102`) refuses `None` — `seat-run: job <id> has no allocated port (seat-spool did not run)`, exit 2 — so a directly started unit never binds a random port.
- `tests/seat/test_seat_submit.py`, `test_seat_spool.py`, `test_seat_run.py` (modify): cases in Steps 1, 6.

**Interfaces.**
1. `seat-submit web|drive` without `--port` writes `port: null`; with `--port N` writes N as a request; drive no longer refuses a missing port.
2. `seat-spool` allocates before `.spooled`: `null` → lowest free port in the range; explicit and free → kept; explicit and held → refused with the reason in `result.txt`, unit never started, marker consumed.
3. The range is `SEAT_PORT_RANGE`, else `/etc/seat-lane/port-range`, else `43210-43219`; a malformed range fails the whole spool run closed (exit 1) like a malformed cap.
4. "Held" = ports of active/activating `seat@*` jobs and of spooled-but-unfinished jobs; a finished job's port is free again.
5. `seat-submit` prints `port=<n>` on its second stdout line once `.spooled` appears, within SA2's bound; `factory-task`'s first-line job-id contract (`:349-352`) is unchanged.
6. `seat-run` refuses an unallocated port rather than inventing one.

**Steps.**
1. **Red.** `test_seat_spool.py`: `test_allocates_lowest_free_port_for_null` (two markers, both `port: null`, `SEAT_PORT_RANGE=43210-43212`, fake `systemctl` listing no units; assert `job.json` ports are 43210 and 43211, both `.spooled` exist), `test_refuses_held_explicit_port` (one job spooled with 43210 and listed active, a second with explicit 43210; assert `result.txt` contains `port 43210 is held by seat@` and no start), `test_no_free_port_refuses` (range `43210-43210`, one held; assert the reason), `test_malformed_port_range_exits_1`. `nix develop -c pytest tests/seat/test_seat_spool.py -q -k 'port'` → `4 failed`, the first with `refused … : port` (today's validator refuses `null`); paste. `test_seat_submit.py`: `test_drive_without_port_writes_null` → fails `assert 2 == 0` (today's "drive needs --port"). `test_seat_run.py`: `test_web_without_port_exits_2` → fails `TypeError`/`assert … == 2` (today `str(None)` is passed).
2. Implement `seat-spool.py` as **Files** says; the allocation happens after the cap check and before `.spooled` (`:237-249`).
3. Implement `seat-submit.py`: drop the drive refusal; add the post-marker wait `_await_spooled(job_dir, timeout)` polling `.spooled`/`result.txt` every `POLL_INTERVAL`, bounded by `_poll_timeout` (SA2), printing `port=<n>`.
4. Implement `seat-run.py`'s `None` refusal.
5. Update the three docstrings.
6. **Green.** `nix develop -c pytest tests/seat -q` → today's count plus 8 (`--co | tail -1` before/after, pasted); `nix build .#checks.x86_64-linux.seat-unit -L` → exit 0; `ruff check`/`format --check` clean. Add `test_submit_prints_port_after_spooled` (fixture writes `.spooled` and a rewritten `job.json` from a thread after 0.2 s; assert second stdout line `port=43215`) and `test_explicit_free_port_is_kept` (spool keeps 43217 when free).
7. **Mutants.**
   - *M1 highest-not-lowest*: allocate `max` instead of `min` → `test_allocates_lowest_free_port_for_null` fails `assert 43212 == 43210`.
   - *M2 no-held-check*: return the explicit port unconditionally → `test_refuses_held_explicit_port` fails (`.spooled` exists, `result.txt` absent).
   - *M3 write-after-spooled*: move the `job.json` rewrite after `.spooled` → `test_submit_prints_port_after_spooled`'s fixture reads `port: null` → `assert 'port=None' == 'port=43215'`.
   - *M4 default-range*: change `"43210-43219"` to `"43210-43210"` → `test_allocates_lowest_free_port_for_null` with `SEAT_PORT_RANGE` unset (a second parametrisation, `monkeypatch.delenv`, `MAX_UNITS_FILE`-style patch of `PORT_RANGE_FILE` to a missing path) fails on the second job: `no free port`.
   - *M5 run-invents-port*: revert `seat-run.py`'s refusal → `test_web_without_port_exits_2` fails `assert 0 == 2`.
   - *M6 stale-held-within-a-run*: compute `held` once per spool run instead of after each `job.json` write-back → `test_allocates_lowest_free_port_for_null`'s second marker also gets 43210 → `assert 43210 == 43211` (the fixture's second row is what discriminates).
   - *M6b double-allocation across two overlapping spool runs* (named; deliberately unaddressed in code): two `seat-spool` processes sharing one `held` snapshot would both pick 43210. On the host it cannot occur — `seat-spool.service` is `Type=oneshot` fired by `paths.seat-spool` (`nixosModules/seatLane.nix:357-371`), systemd never runs two instances of one service unit, and a marker arriving mid-run re-arms `DirectoryNotEmpty` for a next run that reads the first's `job.json`; `seat-eval` pins the oneshot type and the path unit (`flake.nix:2393-2407`), so a templated or long-running spool reddens there. The one route is a hand-run `seat-spool` beside the unit; SA9's follow-ups list a `flock` for it.
   - *Negative control*: `test_explicit_free_port_is_kept` must pass; its mutant — always allocate, ignoring the request — fails `assert 43210 == 43217`. And `test_refuses_bad_port_web` (`:294`, an out-of-range int) must still refuse — mutant: drop the range check → fails.
8. Commit; body pastes Step 1's reds, Step 6's counts, and the range default with its source (`grep -n '43210-43219' pkgs/seat/seat-spool.py`).

**probes:**
- spool-default-range: `grep -c '43210-43219' pkgs/seat/seat-spool.py` :: ge 1 :: SA3 Step 2
- spool-default-range-once: `grep -c '43210-43219' pkgs/seat/seat-spool.py` :: le 1 :: exact count, SA3 Step 2
- submit-drive-port-optional: `grep -c 'drive needs --port' pkgs/seat/seat-submit.py` :: le 0 :: SA3 Step 3

### SA4 (code, M) — the port range is a lane option that holds at least maxUnits ports, proven by two web seats in the VM

**dependsOn:** SA1, SA3
**touches:** nixosModules/seatLane.nix, flake.nix, tests/integration/seat-vm.nix
**areas:** seat, isolation, platform
**acceptance:** seat-eval, seat-assertion-negative, seat-vm
**commit subject:** `seat: services.seat-lane.portRange wires the range, asserts it holds maxUnits ports, and seat-vm starts two web seats on distinct ports (test: seat-eval, seat-assertion-negative, seat-vm)`

**Why.** SA3's allocator reads `/etc/seat-lane/port-range` and falls back to a literal (`seat-spool.py`, SA3 Interface 3); nothing declares that file, so on the live host the range is a program constant, not policy in a diff (brief §3 invariant 5), and nothing ties its width to `maxUnits` — nine units (`cat /etc/seat-lane/max-units` → `9`) with a range one port too narrow would refuse the last seat the cap admits, the same off-by-one shape IS3 fixed for the caps. The module already publishes both caps as files (`seatLane.nix:151-158`) and allows `webPortRange = "43200-43299"` through nftables (`:61-64`, `:389`); the range must sit inside it or the UI is allocated a port the firewall drops. The VM's cap scenario still passes fixed ports (`seat-vm.nix:589-592`; A14), so no test yet proves two seats get distinct allocated ports.

**Files.**
- `nixosModules/seatLane.nix` (modify): `portRange = lib.mkOption { type = lib.types.str; default = "43210-43219"; description = …; }` beside `webPortRange`; `environment.etc."seat-lane/port-range".text = cfg.portRange`; two assertions in the list at `:110-135`: width — `let p = lib.splitString "-" cfg.portRange; in (lib.toInt (lib.elemAt p 1)) - (lib.toInt (lib.elemAt p 0)) + 1 >= cfg.maxUnits`, message `services.seat-lane.portRange (${cfg.portRange}) must hold at least maxUnits (${toString cfg.maxUnits}) ports`; containment — the range lies inside `webPortRange`, message `services.seat-lane.portRange must lie inside webPortRange (${cfg.webPortRange})`.
- `flake.nix` (modify): two fixtures in `seatMaxUnitsEqWaveSystem`'s shape (`:878`) — `seatPortRangeNarrowSystem` with `portRange = "43210-43217"` (eight ports against the default `maxUnits` 9) and `seatPortRangeOutsideSystem` with `portRange = "44210-44219"` (outside the default `webPortRange`); two `seat-assertion-negative` arms — `portRangeAttempt`, throw `seat-assertion-negative: services.seat-lane.portRange one port narrower than maxUnits DID NOT FAIL the build (the width assertion is missing or wrong)`, and `portRangeOutsideAttempt`, throw `seat-assertion-negative: services.seat-lane.portRange outside webPortRange DID NOT FAIL the build (the containment assertion is missing or wrong)` — one fault per fixture; `seat-eval` assertions: `c.services.seat-lane.portRange == "43210-43219"`, `c.environment.etc."seat-lane/port-range".text == "43210-43219"`, and a `tryEval` that `portRange = "43210-43218"` (exactly nine) evaluates green (the boundary admits equality, mirroring `:2431-2437`).
- `tests/integration/seat-vm.nix` (modify): the fixture sets `portRange = "43210-43211"` (two ports for `maxUnits = 2`, `waveJobs = 1` from IS10); a new step 14 submits two `web` seats **without** `--port`, reads `port=` from each second stdout line, asserts they are distinct and inside 43210–43211 and both appear in `ip netns exec egress-seat ss -ltn`; a third `web` without `--port` gets `result.txt` with `no free port in 43210-43211 (2 held)`.

**Interfaces.**
1. `services.seat-lane.portRange` (string `a-b`, default `43210-43219`) is written to `/etc/seat-lane/port-range`, the file SA3's spool reads before its literal.
2. Evaluation refuses a range narrower than `maxUnits` and a range outside `webPortRange`; equality of width and `maxUnits` is admitted.
3. `seat-vm` proves two `--port`-less web seats bind two distinct ports inside the declared range, and a third is refused with the reason in `result.txt`.

**Steps.**
1. **Red, in three parts, taken with the option declared but neither its assertions nor its `environment.etc` line present** (an undeclared option is itself an eval error, which would make the negative arm pass vacuously — so declare it first). (a) `seat-eval` with its three new assertions: `nix build .#checks.x86_64-linux.seat-eval 2>&1 | tail -2` → `error: seat-eval: environment.etc."seat-lane/port-range" must render "43210-43219"`. (b) The two fixtures and the two arms: `nix build .#checks.x86_64-linux.seat-assertion-negative 2>&1 | tail -2` → `error: seat-assertion-negative: services.seat-lane.portRange one port narrower than maxUnits DID NOT FAIL the build (the width assertion is missing or wrong)` (the width arm is evaluated first; after the width assertion alone is added the same command reports the containment arm's throw — paste both). (c) Step 14 in `seat-vm.nix`: with no `/etc/seat-lane/port-range`, SA3's spool falls back to `43210-43219`, the third seat is allocated 43212 and never refused, so `machine.wait_until_succeeds("grep -q 'no free port in 43210-43211' /var/lib/seat/jobs/<id>/result.txt")` fails: `nix build .#checks.x86_64-linux.seat-vm -L 2>&1 | grep -m1 'did not succeed'` → pasted. All three reds go in the commit body.
2. Add the two assertions and the `environment.etc` line.
3. **Green.** `nix build .#checks.x86_64-linux.seat-eval -L` → `seat-eval-ok`; `.seat-assertion-negative` → `seat-assertion-negative-ok`; `.seat-vm -L` → exit 0, and the log shows step 14's two `port=` lines. `nix develop -c statix check nixosModules/seatLane.nix` → exit 0. `nix build .#nixosConfigurations.core.config.system.build.toplevel --dry-run` → evaluates (the default range passes both assertions with `maxUnits = 9`).
4. **Mutants.**
   - *M1 width-off-by-one*: `>=` → `>` in the width assertion → `seat-eval`'s nine-port `tryEval` fails: `portRange = "43210-43218" must evaluate green`.
   - *M2 no-width-assertion*: delete it → `seat-assertion-negative` throws `… DID NOT FAIL the build`.
   - *M3 wrong-file*: `environment.etc."seat-lane/port-range".text = cfg.webPortRange` → `seat-eval` fails `must render "43210-43219"`; and `seat-vm` step 14's third seat is not refused (range now 100 wide) → `did not succeed`.
   - *M4 no-containment-assertion*: delete it → `seat-assertion-negative` throws `… outside webPortRange DID NOT FAIL the build`; and the sibling mutant — the option default changed to `44210-44219` — fails `seat-eval`'s `must render "43210-43219"` and `nix build .#nixosConfigurations.core… --dry-run` with `must lie inside webPortRange (43200-43299)`.
   - *Negative control*: the existing five arms and step 11b (fixed ports 43204/43205, inside `webPortRange`, outside `portRange`) must still pass — the spool keeps an explicit free request (SA3 Interface 2). Discriminating mutant: change step 11b's ports to `43210`/`43211`, then step 14's first seat is refused `no free port` → `did not succeed`; revert.
5. Commit; body pastes Step 1's reds and M1's message; every line number re-run (G11).

**probes:**
- portrange-option: `grep -c 'portRange = lib.mkOption' nixosModules/seatLane.nix` :: ge 1 :: SA4 Step 2
- portrange-option-once: `grep -c 'portRange = lib.mkOption' nixosModules/seatLane.nix` :: le 1 :: exact count, SA4 Step 2
- negative-arms: `grep -c 'Attempt = builtins.tryEval seat' flake.nix` :: ge 7 :: SA4 Step 1, five arms plus two

### SA5 (code, S) — the drive launch sets danger-full-access with the guard still wired; job seats keep the default

**dependsOn:** none
**touches:** pkgs/seat/seat-run.py, pkgs/dsh-openrouter/dsh-openrouter.sh, tests/seat/test_seat_run.py, tests/unit/70-dsh-openrouter.bats
**acceptance:** seat-unit, unit
**commit subject:** `seat: the drive launch sets danger-full-access with the PreToolUse guard still wired; job seats keep the default (test: seat-unit, unit)`

**Why.** Decision 57a: the drive launch runs at `danger-full-access`, job seats keep the default. Today no mode sets a preset: `grep -n permission pkgs/seat/seat-run.py` → nothing (A6), so every seat runs the wrapper's default `permission=${DSH_PERMISSION_MODE:-workspace-write}` (`dsh-openrouter.sh:93`), and the driving session is prompted on every write outside the tree — the very session that drives the whole batch (69a). The wrapper already accepts `--permission MODE` (`:55`, `:115-117`) and validates the three values (`:235-237`), so the change is one argument in one branch. The risk 57a names is that the preset be read as "no guard": the guard is a PreToolUse hook (`:709-733`), independent of the permission mode, and this task proves that with a case rather than a sentence. SA6 needs a discriminator for the drive seat (60a); `SEAT_MODE` is exported here for all three modes.

**Files.**
- `pkgs/seat/seat-run.py` (modify): `os.environ["SEAT_MODE"] = job["mode"]` beside `SEAT_JOB_ID` (`:83`); the `drive` command (`:106-119`) gains `"--permission", "danger-full-access"` before `"--"`; `headless` and `web` commands unchanged. Docstring (`:10-13`) updated.
- `pkgs/dsh-openrouter/dsh-openrouter.sh` (modify): the launch log lines at `:765-766` and `:770-771` already print `$permission`; no wrapper code change is needed for the preset — the one edit is `--dump-config` (`:762`) exporting `DSH_PERMISSION_MODE` before exec, which `:562` already does; **verify** with `grep -n 'export DSH_PERMISSION_MODE' pkgs/dsh-openrouter/dsh-openrouter.sh` → `:562` precedes `:762`; if so the file's only change is a comment line at `:562` naming SA5/57a, kept in `touches` because the seat may otherwise need to move the export.
- `tests/seat/test_seat_run.py` (modify): three cases (Step 1).
- `tests/unit/70-dsh-openrouter.bats` (modify): one case (Step 1).

**Interfaces.**
1. `seat-run.py` exports `SEAT_MODE` ∈ {`headless`,`web`,`drive`} to the harness for every job.
2. The `drive` argv carries `--permission danger-full-access` before the `--`; `headless` and `web` argv carry no `--permission`.
3. Under `--permission danger-full-access`, `dsh-openrouter --dump-config` still shows the `@deepseek-ai/dsh-hooks-claude-code` insert with `configPath` pointing at a `hooks.json` whose `PreToolUse` matchers are exactly `bash`, `edit|write`, `subagent|subagent_fork|workflow` — the guard is wired regardless of preset.
4. The launch log line names the preset (`… via …, danger-full-access, …`), so `journalctl -u seat@<id>` shows it (drill step 4).

**Steps.**
1. **Red.** `test_seat_run.py`: `test_drive_passes_danger_full_access_before_the_dashes` (argv recorded by `_popen_fake`, `:66`; assert `argv.index("--permission") < argv.index("--")` and the next element is `danger-full-access`) → `ValueError: '--permission' is not in list`; `test_headless_and_web_carry_no_permission` (parametrised; assert `"--permission" not in argv`) → passes today (a control — its mutant is M2); `test_exports_seat_mode` (assert `os.environ["SEAT_MODE"] == "drive"` inside the fake) → `KeyError: 'SEAT_MODE'`. `nix develop -c pytest tests/seat/test_seat_run.py -q -k 'permission or seat_mode'` → `2 failed, 2 passed`; paste. `70-dsh-openrouter.bats`: `@test "danger-full-access keeps the PreToolUse guard wired"` — `OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 run dsh-openrouter --permission danger-full-access --dump-config` (the shape at `:198`), assert `$status -eq 0`, `configPath` in the output, and `jq -r '.hooks.PreToolUse[].matcher' "$DSH_HOME/hooks.json"` prints the three matchers; to see it red first, run it against a mutant wrapper that skips the hooks block when `$permission = danger-full-access` (`if [ "$permission" != danger-full-access ]; then … fi` around `:709-740`) → `not ok … jq: … hooks.json: No such file`; paste, revert the mutant.
2. Edit `seat-run.py` as **Files** says.
3. Add the wrapper's comment at `:562`; confirm `grep -c 'SA5' pkgs/dsh-openrouter/dsh-openrouter.sh` → `1`.
4. **Green.** `nix develop -c pytest tests/seat -q` → count plus 3 (paste `--co | tail -1` before/after); `nix build .#checks.x86_64-linux.seat-unit -L` and `.unit -L` → exit 0; `nix develop -c bats tests/unit/70-dsh-openrouter.bats -f 'danger-full-access'` → `ok`. `shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` → exit 0 (inside `lint`, run it directly as well).
5. **Mutants.**
   - *M1 no-preset*: remove the two argv elements → `test_drive_passes_danger_full_access_before_the_dashes` fails `ValueError: '--permission' is not in list`.
   - *M2 preset-everywhere*: add `--permission danger-full-access` to the `headless` command too → `test_headless_and_web_carry_no_permission[headless]` fails `assert '--permission' not in […]` (the control discriminates).
   - *M3 after-the-dashes*: place `--permission` after `"--"` → the index assertion fails `assert 9 < 7` (dsh's web-app flags would swallow it).
   - *M4 mode-constant*: `os.environ["SEAT_MODE"] = "drive"` for every mode → `test_exports_seat_mode[headless]` fails `assert 'drive' == 'headless'`.
   - *M5 guard-dropped-under-preset*: the Step 1 mutant wrapper → the bats case fails on `hooks.json`.
   - *Negative control*: `test_drive_passes_the_model_before_the_dashes` (`:305`) must still pass; mutant: move `--model` after `--` → fails.
6. Commit; body pastes Step 1's pytest and bats reds and M5's `not ok` line.

**probes:**
- run-exports-mode: `grep -c 'SEAT_MODE' pkgs/seat/seat-run.py` :: ge 1 :: SA5 Step 2
- run-preset-count: `grep -c 'danger-full-access' pkgs/seat/seat-run.py` :: ge 1 :: SA5 Step 2
- run-preset-once: `grep -c 'danger-full-access' pkgs/seat/seat-run.py` :: le 1 :: exact count, the drive branch only, SA5 Step 2

### SA6 (code, M) — SessionStart, PreCompact and Stop run one packaged hook that rituals a drive seat and passes a job seat through

**dependsOn:** SA5
**touches:** pkgs/dsh-openrouter/seat-hooks.py, pkgs/dsh-openrouter/default.nix, pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats, tests/unit/94-seat-harness.bats
**acceptance:** unit, lint
**commit subject:** `seat: SessionStart, PreCompact and Stop run one packaged hook that rituals a drive seat and passes a job seat through (test: unit, lint)`

**Why.** Decision 58a wants SessionStart, PreCompact and Stop "running the same scripts" — the workspace's `tools/session-start.sh` and `tools/ritual.sh`; 60a scopes them to the driver session; 21c forbids self-nudges. Today the generated `hooks.json` declares `PreToolUse` only (`grep -c '"PreToolUse"' pkgs/dsh-openrouter/dsh-openrouter.sh` → `1`; `grep -c 'SessionStart\|PreCompact\|"Stop"' …` → `0`), so the drive seat starts every session blind and compacts without a ritual. Whether the `@deepseek-ai/dsh-hooks-claude-code` bridge fires those three events is UNMEASURED (A2) — Step 1 measures it, and A20 emulates SessionStart and Stop at the seat's own boundaries if absent. `SEAT_MODE` (SA5) is the discriminator.

**Files.**
- `pkgs/dsh-openrouter/seat-hooks.py` (create): stdlib-only; reads the hook payload from stdin **only if `not sys.stdin.isatty()`**, at most 1 MiB (`sys.stdin.read(1 << 20)`), and parses it with `json.loads`; a terminal, an empty read, non-JSON, a non-object or a missing `hook_event_name` → one stderr line `seat-hooks: no hook payload on stdin (<terminal|empty|not JSON|no hook_event_name>)`, exit 0, empty stdout — it never waits on a terminal and never tracebacks; a Stop payload's `stop_hook_active` (the harness's loop-guard field, true when the turn already continued from a Stop hook) is logged to stderr and changes nothing, because this hook never blocks. Then reads `SEAT_MODE`; if not `drive` → exit 0, empty stdout; if `drive` → runs `tools/session-start.sh` (SessionStart) or `tools/ritual.sh` (PreCompact, Stop) from `$PWD` (the workspace `seat-run.py` cd'd into), with a 60 s timeout, prints the script's stdout as `{"hookSpecificOutput":{"hookEventName":…,"additionalContext":<stdout>}}` for SessionStart and PreCompact, and **plain stdout, no decision field** for Stop (21c: never a `{"decision":"block"}`, so a Stop can never re-prompt the seat); a missing or failing script → one stderr line, exit 0 (the guard's fail-open-on-exit contract, A11). Module docstring is the contract.
- `pkgs/dsh-openrouter/default.nix` (modify): `seatHooks = writePython3MinimalBin "seat-hooks" { … } ./seat-hooks.py` beside `hookGuard` (`:65`), exported as `runtimeEnv.DSH_SEAT_HOOKS` (`:83`'s idiom) and in the `symlinkJoin` (`:108`).
- `pkgs/dsh-openrouter/dsh-openrouter.sh` (modify): `seat_hooks=${DSH_SEAT_HOOKS:?…}` beside `:679`; the `hooks.json` heredoc (`:709-733`) gains `"SessionStart"`, `"PreCompact"`, `"Stop"` arrays, each one `{ "type": "command", "command": <jq @sh of $seat_hooks> }`; a wrapper constant `emulated_events=` set from Step 1(a)'s measurement (the names the bridge does not fire, of `SessionStart` and `Stop`; empty if both fire) drives Step 4b's emulation for `SEAT_MODE=drive` only; `seat-run.py` is not touched.
- `tests/unit/70-dsh-openrouter.bats` (modify): the `hooks.json` shape case (Step 1).
- `tests/unit/94-seat-harness.bats` (modify): the `seat-hooks` behaviour cases (Step 1).

**Interfaces.**
1. `hooks.json` declares four events: the existing `PreToolUse` triple and `SessionStart`, `PreCompact`, `Stop`, each of the latter pointing at the packaged `seat-hooks`.
2. `seat-hooks` under `SEAT_MODE` ≠ `drive` (or unset) exits 0 with empty stdout in under 1 s and runs no script.
3. `seat-hooks` under `SEAT_MODE=drive` runs `tools/session-start.sh` for SessionStart and `tools/ritual.sh` for PreCompact and Stop, from the current directory, and returns their stdout as `additionalContext` (SessionStart, PreCompact) or plain text (Stop).
4. `seat-hooks` never emits a `decision` or `permissionDecision` field and always exits 0: a hook failure, a terminal on stdin, an empty or malformed payload are each one stderr line, never a blocked turn (21c; `seat-run.py`'s exit code is the harness's, `:133`); `stop_hook_active` is read and logged, never acted on.
5. Which of the three events the bridge fires is recorded in the commit body as the output of Step 1(a); an unfired SessionStart or Stop is emulated by the wrapper for `SEAT_MODE=drive` (Step 4b); an unfired PreCompact is left to Platform's patch series (A20).
6. Emulated Stop keeps the exit-code contract: the unit's exit code is the harness's (`wait` returns it; `seat-run.py` records it unchanged, `:133`); the unit's main PID becomes the wrapper instead of `node`, and SIGTERM reaches `node` twice over — the wrapper's trap and systemd's control-group kill (the default `KillMode`), so no signal is lost.

**Steps.**
1. **Red.** (a) Measure: `grep -rn 'SessionStart\|PreCompact\|"Stop"\|hook_event_name' "$(nix build .#dsh --no-link --print-out-paths)/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-hooks-claude-code/" | head -20` → paste the matched event names; then for each of the three write it as `fires`/`does not fire` in the body. (b) `94-seat-harness.bats`: `@test "seat-hooks passes a job seat through"` (`SEAT_MODE=headless printf '{"hook_event_name":"SessionStart"}' | seat-hooks` → status 0, empty output, and a `tools/ritual.sh` stub in `$BATS_TEST_TMPDIR` that touches a marker is **not** run); `@test "seat-hooks rituals a drive seat on each event"` (parametrised by three events, `SEAT_MODE=drive`, stubs under `tools/` that echo `ran <event>`; assert stdout carries `ran` and, for Stop, no `decision` key); `@test "seat-hooks survives a missing script"` (no `tools/`; status 0, stderr names the path); `@test "seat-hooks exits 0 on an empty or malformed stdin"` (`SEAT_MODE=drive` with the stubs present: `seat-hooks </dev/null` and `printf 'garbage' | seat-hooks` → each status 0, empty stdout, stderr contains `no hook payload on stdin`, and no `ran` marker — the pass-through is not what saves it). `nix develop -c bats tests/unit/94-seat-harness.bats -f seat-hooks` → `4 not ok`, `seat-hooks: command not found`; paste. (c) `70-dsh-openrouter.bats`: `@test "hooks.json declares SessionStart, PreCompact and Stop against seat-hooks"` — `--dump-config` then `jq -r '.hooks | keys[]' "$DSH_HOME/hooks.json"` → assert the four names → today `not ok`, prints `PreToolUse` only; paste.
2. Create `seat-hooks.py`; `nix develop -c ruff check pkgs/dsh-openrouter && ruff format --check pkgs/dsh-openrouter` → clean.
3. Package it in `default.nix`; `nix build .#dsh-openrouter --no-link --print-out-paths` and `ls "$(…)/bin"` shows `seat-hooks`.
4. Wire `hooks.json`; set `emulated_events=` to the names 1(a) measured unfired.
4b. **Emulation (conditional on 1(a); written only for the names in `emulated_events`).** SessionStart: before the drive launch, `printf '{"hook_event_name":"SessionStart"}' | "$seat_hooks" || true`. Stop: the `web`/drive arm replaces its `exec` with, verbatim,
   ```
   if [ "${SEAT_MODE:-}" = drive ] && case " $emulated_events " in *" Stop "*) true ;; *) false ;; esac; then
     "$node_bin" --expose-internals "$bin_js" --profile web --patch "$overlay" --host 127.0.0.1 "$@" &
     child=$!
     trap 'kill -TERM "$child" 2>/dev/null' TERM INT
     wait "$child"; rc=$?
     printf '{"hook_event_name":"Stop","stop_hook_active":false}' | "$seat_hooks" || true
     exit "$rc"
   fi
   ```
   (the `--trusted-host` form under `--bind-namespace` gets the same block). `70-dsh-openrouter.bats`: `@test "an emulated Stop runs seat-hooks after the harness and keeps its exit code"` — `make_fake_node` then `sed -i 's/^exit 0$/exit 7/' "$TMPHOME/bin/fake-node"`; a stub `seat-hooks` in `$TMPHOME/bin` appending stdin to `$TMPHOME/hooks.log`; `SEAT_MODE=drive DSH_SEAT_HOOKS=$TMPHOME/bin/seat-hooks DSH_OPENROUTER_NODE=$TMPHOME/bin/fake-node DSH_OPENROUTER_TEST_SEAM=1 run dsh-openrouter -- --no-open --port 43210` (the `:1477-1483` shape) → `[ "$status" -eq 7 ]` and `grep -q '"Stop"' "$TMPHOME/hooks.log"` (when `emulated_events` omits Stop: status 7 and no `hooks.log`). Red before the block: status 7, no `hooks.log` → `not ok`; paste.
5. **Green.** `nix build .#checks.x86_64-linux.unit -L` → exit 0 with the new `ok` lines (`grep -c '^ok' `-style count pasted before/after: `nix develop -c bats tests/unit/70-dsh-openrouter.bats tests/unit/94-seat-harness.bats | grep -c '^ok'`); `.lint -L` → exit 0 (`shellcheck` over the wrapper, `ruff` over the new file, `repomap` current — run `nix develop -c python3 pkgs/evidence/repomap.py --root . write` and commit `docs/MAP.md` if it changes, per G5's exemption).
6. **Mutants.**
   - *M1 no-discriminator*: drop the `SEAT_MODE` check → "passes a job seat through" fails (the marker exists / stdout non-empty).
   - *M2 wrong-script*: run `session-start.sh` for Stop → the drive case's Stop parametrisation fails `ran SessionStart` ≠ `ran Stop`.
   - *M3 blocking-stop*: emit `{"decision":"block"}` on Stop → the Stop case fails `jq -e 'has("decision")'` → 21c preserved by test.
   - *M4 exit-nonzero-on-missing*: `sys.exit(1)` when the script is missing → "survives a missing script" fails `status 1`.
   - *M5 three-events-dropped*: revert the heredoc → the `70` case prints `PreToolUse` only.
   - *M6 stdin-unguarded*: drop the `isatty`/empty/`JSONDecodeError` handling → `seat-hooks </dev/null` tracebacks (`json.decoder.JSONDecodeError`), status 1 → the stdin case fails `status 1`.
   - *M7 exec-kept* (only when Stop is emulated): `exec` instead of `&`/`wait` → the Stop payload never runs → the `70` emulation case finds no `hooks.log`.
   - *M8 exit-code-dropped*: `exit 0` instead of `exit "$rc"` → the same case fails `assert status 7`.
   - *Negative control*: the existing PreToolUse deny cases (`70-dsh-openrouter.bats:889-974`, the `hook-guard denies …` block) must still pass — the hooks block is edited in place; mutant: delete the `bash` matcher → the wiring case fails on `hooks.json`.
7. Commit; body pastes 1(a)'s measurement, 1(b)/(c)'s and 4b's reds, and the emulation decision.

**probes:**
- hooks-declare-three: `grep -c '"SessionStart"\|"PreCompact"\|"Stop"' pkgs/dsh-openrouter/dsh-openrouter.sh` :: ge 3 :: SA6 Step 4
- seat-hooks-no-decision: `grep -c '"decision"' pkgs/dsh-openrouter/seat-hooks.py` :: le 0 :: SA6 Step 2
- seat-hooks-stdin-guard: `grep -c 'isatty' pkgs/dsh-openrouter/seat-hooks.py` :: ge 1 :: SA6 Step 2, Interface 4

### SA7 (code, M) — the seat's memory lives under the evidence store, granted to seat@ and linked into DSH_HOME

**dependsOn:** SA1
**touches:** nixosModules/seatLane.nix, pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats, tests/integration/seat-vm.nix
**areas:** seat, isolation
**acceptance:** unit, seat-eval, seat-vm
**commit subject:** `seat: the seat's memory lives under the evidence store, granted to seat@ and linked into DSH_HOME, never in the tree (test: unit, seat-eval, seat-vm)`

**Why.** Decision 59a's second half: "the seat's memory is a machine-local store under the evidence store", never a tracked file. Today the seat has no declared memory location at all — `grep -c 'memory' nixosModules/seatLane.nix` → `0`, and `grep -n 'memory' pkgs/dsh-openrouter/dsh-openrouter.sh` → two lines, neither a store: `:16` is the refusal list's mention of Claude memory in the header comment, `:558` is the `warn_missing_payload` call that names `AGENTS.md` "bootstrap memory" (the payload) — so anything a drive seat wants to remember lands in the workspace, where `git status` shows it and a commit can sweep it (Assumption 11 of the program plan records exactly such a sweep, `2678983`). The unit already may write under `-/var/lib/evidence` (`seatLane.nix:311`), but nothing creates a seat-owned directory there (tmpfiles rows at `:196-202` cover `/var/lib/seat` only), and no `DSH_HOME` path points at it. Brief §3 invariant 4 requires the directory be declared, not made by hand.

**Files.**
- `nixosModules/seatLane.nix` (modify): `memoryDir = lib.mkOption { type = lib.types.path; default = "/var/lib/evidence/seat-memory"; … }`; tmpfiles row `"d ${cfg.memoryDir} 0700 ${cfg.operatorUser} users -"` after `:202`; `ReadWritePaths` gains `cfg.memoryDir` as an explicit row (kept beside `-/var/lib/evidence`, `:311`, so the grant is visible even if the broad row is later narrowed); `environment.SEAT_MEMORY_DIR = cfg.memoryDir` in the unit env (`:234-258`); an assertion `lib.hasPrefix "/var/lib/evidence/" cfg.memoryDir`, message `services.seat-lane.memoryDir must lie under /var/lib/evidence (decision 59a)`.
- `pkgs/dsh-openrouter/dsh-openrouter.sh` (modify): a block after `:558`: if `SEAT_MEMORY_DIR` is set, `cwd_key=$(printf %s "$workspace" | sha256sum | cut -c1-16)`, `if mkdir -p "$SEAT_MEMORY_DIR/$cwd_key" 2>"$err"; then ln -sfn "$SEAT_MEMORY_DIR/$cwd_key" "$DSH_HOME/memory"; else warn "SEAT_MEMORY_DIR=$SEAT_MEMORY_DIR/$cwd_key: $(cat "$err") — no memory link"; fi` (`mkdir`'s own message carries the errno text, e.g. `Permission denied`); unset → no link, one `warn` line naming the missing variable (an interactive operator run outside the unit). The launch continues in every arm; the exit code is never the memory link's.
- `tests/unit/70-dsh-openrouter.bats` (modify): three cases (Step 1).
- `tests/integration/seat-vm.nix` (modify): step 15 (Step 1).

**Interfaces.**
1. `services.seat-lane.memoryDir` (default `/var/lib/evidence/seat-memory`) is created by tmpfiles `0700 <operatorUser>`, granted to `seat@` via `ReadWritePaths`, and exported to the unit as `SEAT_MEMORY_DIR`; a value outside `/var/lib/evidence/` fails eval.
2. The wrapper links `$DSH_HOME/memory` → `$SEAT_MEMORY_DIR/<cwd-key>` where `<cwd-key>` is the first 16 hex chars of `sha256(workspace)`; the directory is created if absent; nothing is created under the workspace.
3. Three arms on `SEAT_MEMORY_DIR`: unset → one warn line, no link; set and creatable → the link; set but `mkdir -p` fails (the state of any host whose unit lacks the `ReadWritePaths` grant, or an operator run against a root-owned path) → one stderr line naming the path and the errno text, no link, launch unaffected.
4. A file a seat writes through `$DSH_HOME/memory` survives the unit's end, sits under `memoryDir`, and leaves the workspace's `git status --porcelain` empty.

**Steps.**
1. **Red.** (a) `seat-eval`: add `c.services.seat-lane.memoryDir == "/var/lib/evidence/seat-memory"`, `lib.elem "d /var/lib/evidence/seat-memory 0700 dalhaka users -" c.systemd.tmpfiles.rules`, `lib.elem "/var/lib/evidence/seat-memory" unit.serviceConfig.ReadWritePaths`, `unit.environment.SEAT_MEMORY_DIR == "/var/lib/evidence/seat-memory"` → `nix build .#checks.x86_64-linux.seat-eval 2>&1 | tail -2` → `error: attribute 'memoryDir' missing`; paste. (b) `70-dsh-openrouter.bats`: `@test "the wrapper links DSH_HOME/memory into SEAT_MEMORY_DIR by cwd-key"` (`SEAT_MEMORY_DIR=$BATS_TEST_TMPDIR/mem … --dump-config`; assert `readlink "$DSH_HOME/memory"` equals `$SEAT_MEMORY_DIR/$(printf %s "$PWD" | sha256sum | cut -c1-16)` and that directory exists; assert `find "$PWD" -newer "$BATS_TEST_TMPDIR/stamp" | wc -l` → 0) `@test "without SEAT_MEMORY_DIR the wrapper warns and links nothing"`, and `@test "an unwritable SEAT_MEMORY_DIR warns with the path and errno and links nothing"` (`mkdir -p "$BATS_TEST_TMPDIR/ro" && chmod 0500 "$BATS_TEST_TMPDIR/ro"`; `SEAT_MEMORY_DIR=$BATS_TEST_TMPDIR/ro/mem … --dump-config` → `[ "$status" -eq 0 ]`, stderr contains `SEAT_MEMORY_DIR=$BATS_TEST_TMPDIR/ro/mem/` and `Permission denied`, `[ ! -e "$DSH_HOME/memory" ]`; skipped when `id -u` is 0, where `chmod` binds nothing) → `nix develop -c bats tests/unit/70-dsh-openrouter.bats -f memory` → `3 not ok` (`readlink: … No such file`); paste. (c) `seat-vm.nix` step 15: a headless job whose brief is `echo note > "$DSH_HOME/memory/note.txt"` (the fake model's canned tool call — reuse the step-5 headless shape at `:260`), then `machine.wait_until_succeeds("test -f /var/lib/seat/jobs/<id>/exit_code.txt")`, `machine.succeed("test -f /var/lib/evidence/seat-memory/*/note.txt")`, `machine.succeed("test -z \"$(git -C /home/dalhaka/factory/ws status --porcelain)\"")` → `did not succeed` on the `test -f`; paste.
2. Add the option, tmpfiles row, `ReadWritePaths` row, env export, assertion.
3. Add the wrapper block.
4. **Green.** `seat-eval`, `unit`, `seat-vm` → exit 0 each (`nix build .#checks.x86_64-linux.{seat-eval,unit,seat-vm} -L`); `statix check nixosModules/seatLane.nix`, `shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` → exit 0.
5. **Mutants.**
   - *M1 no-grant*: remove the explicit `ReadWritePaths` row → `seat-eval` fails `must grant memoryDir`; **and** with `-/var/lib/evidence` also removed for the probe, `seat-vm` step 15 fails `Read-only file system` in the unit's journal — paste once to show the kernel grant is load-bearing, then restore both.
   - *M2 no-tmpfiles*: drop the row → `seat-eval` fails the `elem` assertion; `seat-vm` step 15 fails `No such file or directory` on `mkdir -p` under a non-existent parent owned by root.
   - *M3 link-into-workspace*: `ln -sfn "$workspace/.memory" …` → the bats `find -newer` count is 1 and the VM's `git status --porcelain` is non-empty.
   - *M4 wrong-key*: use `basename "$workspace"` instead of the hash → the bats `readlink` assertion fails (`/mem/ws` ≠ `/mem/<hash>`).
   - *M5 outside-evidence*: set the default to `/var/lib/seat/memory` → the `hasPrefix` assertion fails eval; paste via `nix build .#nixosConfigurations.core… --dry-run`.
   - *M6 die-on-unwritable*: replace the `else warn …` arm with `die 5` → the unwritable case fails `status 5`; and *M6b silent-on-unwritable*: drop the `warn` → the case fails on the missing `Permission denied` line (the operator would never learn why memory is absent).
   - *Negative control*: the without-variable case must pass; mutant: make the wrapper `die` when the variable is unset → fails `status 5`. And the existing payload cases in `70` (`:589`, `:617`, `:633`) must still pass (the new block sits after them).
6. Commit; body pastes the three reds, M1's journal line, and `readlink` from the bats run.

**probes:**
- memorydir-option: `grep -c 'memoryDir = lib.mkOption' nixosModules/seatLane.nix` :: ge 1 :: SA7 Step 2
- memorydir-option-once: `grep -c 'memoryDir = lib.mkOption' nixosModules/seatLane.nix` :: le 1 :: exact count, SA7 Step 2
- wrapper-memory-link: `grep -c 'DSH_HOME/memory' pkgs/dsh-openrouter/dsh-openrouter.sh` :: ge 1 :: SA7 Step 3

### SA8 (code, M) — dsh-openrouter takes a Nix harness payload that the build asserts and the wrapper deploys

**dependsOn:** none
**touches:** pkgs/dsh-openrouter/default.nix, pkgs/dsh-openrouter/dsh-openrouter.sh, tests/fixtures/harness-payload/AGENTS.md, tests/fixtures/harness-payload/skills/smoke/SKILL.md, tests/fixtures/harness-payload-broken/AGENTS.md, tests/unit/70-dsh-openrouter.bats, flake.nix
**areas:** seat, platform
**acceptance:** seat-assertion-negative, unit
**commit subject:** `seat: dsh-openrouter takes a Nix harness payload that the build asserts and the wrapper deploys, the symlink fallback kept until absorption (test: seat-assertion-negative, unit)`

**Why.** The seat's mind — `skills/` and `AGENTS.md` — is deployed by two hand-made symlinks into `~/flakes/dsh-harness` and a missing payload only warns (`dsh-openrouter.sh:534-535`, `warn_missing_payload` `:544-556`, calls `:557-558`); `git ls-files | grep -ci agents.md` → `0`, so nothing in this tree carries it. That is the one measured live violation of brief §3 invariant 4 in the seat path, and decision 36a's answer is a store path. Platform's absorption of the sibling is not this plan's (charter §6); what SA owns is the seam: an input the package asserts and the wrapper deploys, with the warn path alive only while the input is null, so the drive seat that runs this batch (69a) stays launchable. `pkgs/dsh-openrouter/default.nix` takes no such input today (`grep -c harnessPayload pkgs/dsh-openrouter/default.nix` → `0`).

**Files.**
- `pkgs/dsh-openrouter/default.nix` (modify): `harnessPayload ? null` in the argument set (`:30-46`); `assert harnessPayload == null || (builtins.pathExists "${harnessPayload}/AGENTS.md" && builtins.pathExists "${harnessPayload}/skills" && builtins.readDir "${harnessPayload}/skills" != { })` with `lib.assertMsg` message `dsh-openrouter: harnessPayload must carry AGENTS.md and a non-empty skills/ (decision 36a)`; `runtimeEnv.DSH_HARNESS_PAYLOAD = if harnessPayload == null then "" else "${harnessPayload}"`.
- `pkgs/dsh-openrouter/dsh-openrouter.sh` (modify): the block at `:557-558` becomes: if `DSH_HARNESS_PAYLOAD` is non-empty → `ln -sfn "$DSH_HARNESS_PAYLOAD/skills" "$DSH_HOME/skills"`, `ln -sfn "$DSH_HARNESS_PAYLOAD/AGENTS.md" "$DSH_HOME/AGENTS.md"`, one stderr line `dsh-openrouter: harness payload from <store path>`; else today's two `warn_missing_payload` calls, unchanged, plus one line `dsh-openrouter: harness payload not bound (harnessPayload = null); deploying from the operator's symlinks until Platform's absorption`.
- `tests/fixtures/harness-payload/AGENTS.md` (create, one line), `tests/fixtures/harness-payload/skills/smoke/SKILL.md` (create, one line): the good fixture.
- `tests/fixtures/harness-payload-broken/AGENTS.md` (create, one line; no `skills/`): the broken fixture.
- `tests/unit/70-dsh-openrouter.bats` (modify): three cases (Step 1).
- `flake.nix` (modify): `dshOpenrouterWithPayload = pkgs.callPackage ./pkgs/dsh-openrouter { dsh = …; harnessPayload = ./tests/fixtures/harness-payload; }` and `…Broken` with the broken fixture; a `seat-assertion-negative` arm `payloadAttempt = builtins.tryEval dshOpenrouterBrokenPayload.drvPath` with throw `seat-assertion-negative: a harness payload without skills/ DID NOT FAIL the build (the harnessPayload assertion is missing or wrong)`; the `unit` check's environment (`:2876-2935`, where `dshOpenrouter` already enters the sandbox) gains `DSH_OPENROUTER_PAYLOAD_FIXTURE=${./tests/fixtures/harness-payload}` and `DSH_OPENROUTER_WITH_PAYLOAD=${dshOpenrouterWithPayload}`, so one bats case runs the *packaged* wrapper and sees the `runtimeEnv` export for real.

**Interfaces.**
1. `pkgs/dsh-openrouter` accepts `harnessPayload` (a path or null). Non-null and lacking `AGENTS.md` or a non-empty `skills/` → evaluation fails with the message above.
2. Non-null → the wrapper deploys both links from the store path and logs the path; the symlink recipes are not printed.
3. Null → today's behaviour byte-for-byte plus one informational line; `seat-submit drive`'s `_missing_drive_skill` check (`seat-submit.py:80-85`) is unaffected because the links land at the same `$DSH_HOME` paths.
4. The default `harnessPackage` in `seatLane.nix` (`:66-68`) passes no `harnessPayload`, so the live unit is unchanged by this task (drill step 7).

**Steps.**
1. **Red.** (a) First add `harnessPayload ? null` to `default.nix`'s argument set **without** the assertion — `callPackage` with an undeclared argument fails inside `tryEval` and would let the arm pass vacuously. Then add the two fixture packages and the `payloadAttempt` arm to `flake.nix` → `nix build .#checks.x86_64-linux.seat-assertion-negative 2>&1 | tail -2` → `error: seat-assertion-negative: a harness payload without skills/ DID NOT FAIL the build (the harnessPayload assertion is missing or wrong)`. Paste. (b) `70-dsh-openrouter.bats`: `@test "a bound harness payload deploys skills and AGENTS.md from the store"` (`DSH_HARNESS_PAYLOAD=$DSH_OPENROUTER_PAYLOAD_FIXTURE … --dump-config`; assert `readlink "$DSH_HOME/skills"` = `$DSH_HARNESS_PAYLOAD/skills`, `readlink "$DSH_HOME/AGENTS.md"` likewise, stderr contains `harness payload from`, and **not** `ln -s ~/flakes`) `@test "an unbound payload keeps the warn path"` (variable empty; assert stderr contains `harness payload not bound` and the existing `Deploy it:` recipe when `$DSH_HOME/skills` is absent), and `@test "the packaged payload deploys with no DSH_HARNESS_PAYLOAD in the environment"` (`make_key`; `env -u DSH_HARNESS_PAYLOAD OPENROUTER_BASE_URL=http://127.0.0.1:1/api/v1 "$DSH_OPENROUTER_WITH_PAYLOAD/bin/dsh-openrouter" --dump-config`; assert status 0, `readlink "$DSH_HOME/skills"` starts with `/nix/store/` and ends with `/skills`, `readlink "$DSH_HOME/AGENTS.md"` ends with `/AGENTS.md` under the same store path — the export itself, not a hand-set variable, is what deploys) → `nix develop -c bats tests/unit/70-dsh-openrouter.bats -f 'payload'` → `3 not ok`; paste.
2. Add the assertion and `runtimeEnv` line to `default.nix`; `nix build .#dshOpenrouterWithPayload --no-link` (expose it under `packages` only if the check needs it; otherwise keep it in the `let`) → exit 0; `nix eval .#checks.x86_64-linux.seat-assertion-negative.drvPath` → a path.
3. Edit the wrapper block; `shellcheck pkgs/dsh-openrouter/dsh-openrouter.sh` → exit 0.
4. Create the three fixture files; `git add tests/fixtures/harness-payload tests/fixtures/harness-payload-broken` before any build (G5).
5. **Green.** `nix build .#checks.x86_64-linux.seat-assertion-negative -L` → `…-ok`; `.unit -L` → exit 0, `ok` count plus 2 (paste before/after); `nix build .#dsh-openrouter --no-link --print-out-paths` and `nix store diff-closures /run/current-system ./result` (drill 7) show the wrapper changed and nothing else in the seat's closure; `nix develop -c python3 pkgs/evidence/repomap.py --root . check` → exit 0 (regenerate and commit `docs/MAP.md` if the new fixtures move it, per G5).
6. **Mutants.**
   - *M1 no-assertion*: delete the `assert` → `payloadAttempt` throws `DID NOT FAIL`.
   - *M2 empty-skills-admitted*: weaken the assertion to `pathExists "${harnessPayload}/skills"` alone → proven by the good fixture in reverse: `git rm tests/fixtures/harness-payload/skills/smoke/SKILL.md` (probe only) leaves an empty `skills/`, and `nix eval .#checks.x86_64-linux.seat-assertion-negative.drvPath` still succeeds under the mutant where the unmutated assertion fails with `harnessPayload must carry AGENTS.md and a non-empty skills/`; restore the file. Paste both outcomes.
   - *M3 deploy-from-home*: keep `ln -s ~/flakes/dsh-harness/skills` even when bound → the bats `readlink` fails (`/home/…/flakes/…` ≠ the store path).
   - *M4 refuse-when-null*: replace the warn path with `die 5` → "an unbound payload keeps the warn path" fails `status 5` — the guarantee the drive seat stays launchable (69a).
   - *M5 env-not-exported*: drop `runtimeEnv.DSH_HARNESS_PAYLOAD` → the packaged-wrapper case finds no variable, falls to the warn path, and `readlink "$DSH_HOME/skills"` fails (`No such file`) — killed by a test; the `payload-env` probe below is redundant, not load-bearing.
   - *Negative control*: the existing payload cases in `70` (`:589` missing/empty skills warns, `:617` a deployed payload warns nothing, `:633` the warning lands on stderr) must still pass; mutant: delete the two `warn_missing_payload` calls → `:589` fails.
7. Commit; body pastes 1(a), 1(b), M1's throw, M4's status, M5's `readlink` failure.

**probes:**
- payload-input: `grep -c 'harnessPayload' pkgs/dsh-openrouter/default.nix` :: ge 3 :: SA8 Step 2
- payload-env: `grep -c 'DSH_HARNESS_PAYLOAD' pkgs/dsh-openrouter/default.nix` :: ge 1 :: SA8 Step 2
- payload-env-once: `grep -c 'DSH_HARNESS_PAYLOAD' pkgs/dsh-openrouter/default.nix` :: le 1 :: exact count, SA8 Step 2
- fallback-alive: `grep -c 'warn_missing_payload "\$DSH_HOME' pkgs/dsh-openrouter/dsh-openrouter.sh` :: ge 2 :: SA8 Step 3
- fallback-alive-exact: `grep -c 'warn_missing_payload "\$DSH_HOME' pkgs/dsh-openrouter/dsh-openrouter.sh` :: le 2 :: exact count, the two calls at 557-558, SA8 Step 3

### SA9 (docs, S) — the runbook carries the job-directory contract and this increment's operator surface

**dependsOn:** SA3, SA4, SA5, SA6, SA7, SA8
**touches:** docs/runbooks/seat.md
**acceptance:** lint
**commit subject:** `seat: the runbook carries the job-directory contract, the port range, the drive preset, the hooks, the memory store and the payload seam (test: lint)`

**Why.** `docs/runbooks/seat.md` describes the caps (`## The two caps`, `:38` per the block) and the pre-SA3 launch, in which the operator picks a port: `grep -n -- '--port\|port-range\|danger-full-access\|SessionStart\|seat-memory\|harnessPayload\|result.txt\|\.spooled' docs/runbooks/seat.md` → re-run at commit; at `21f6a6a` the matches are `--port 43210` (`:97`, the operator picking the historical port by hand) and four `result.txt` lines (`:20`, `:35`, `:77`, `:114`, the cap and poll story) — none of `port-range`, `danger-full-access`, `SessionStart`, `seat-memory`, `harnessPayload` or `.spooled`. After SA3–SA8 the operator surface has six new facts and Helm's session list (13b) needs one written contract for what a job directory holds. Without this page the composed drill (`## Operator`) has no runbook line to read from, and drill step 8 fails by definition.

**Files.**
- `docs/runbooks/seat.md` (modify): six new sections, each with a command and its expected output — `## The job directory` (the contract: `job.json` fields `mode, workspace, dsh_home, model, effort, brief, port, submitted`, `port` null-until-allocated for web/drive; `.spooled`; `stdout.txt`, `stderr.txt`, `exit_code.txt`, `result.txt`; what exists at each stage: submitted → spooled → running → ended → refused; the reader is Helm's backend, which never allocates); `## Ports` (`portRange`, `/etc/seat-lane/port-range`, the sentence "`--port` is a request, not a claim: a held port is refused", the refusal text, the `port=` second stdout line); `## The drive preset` (`danger-full-access` on drive only, `journalctl` line, `dsh-openrouter --denials` as the proof the guard is wired); `## Hooks` (the four events, drive-only ritual, where an emulated event runs, 21c's no-block rule); `## Memory` (`memoryDir`, the `cwd-key` recipe, `ls` line, the "never in the tree" rule, the backup row as a follow-up); `## The payload seam` (`harnessPayload`, what the null fallback prints, when it goes); plus a `## Follow-ups` list: the fallback's deletion, the memory backup row, a `flock` on the jobs directory for a hand-run `seat-spool` beside the unit (SA3 M6b). Every command is taken from the drill in `## Operator` verbatim.

**Interfaces.**
1. The runbook answers drill steps 2–7 with a command and an expected output each, with this plan closed.
2. The job-directory section is the single statement of the contract Helm reads; every field name matches `seat-submit.py`'s `job` dict (`:329-338` at `21f6a6a`, plus SA3's rewrite) — checked by Step 3's `grep` against the code.
3. `lint` passes: markdown formatting per the repo's checker, `docs/MAP.md` unchanged (no module, package, check or test is added).

**Steps.**
1. **Red.** The docs task's red is the measured absence: `grep -c 'The job directory\|## Ports\|## The drive preset\|## Hooks\|## Memory\|## The payload seam' docs/runbooks/seat.md` → `0`; and the contract check in Step 3 run before the edit: `for f in mode workspace dsh_home model effort brief port submitted; do grep -q "\`$f\`" docs/runbooks/seat.md || echo "missing $f"; done` → eight `missing` lines. Paste both.
2. Write the six sections and the follow-ups list.
3. **Green.** The Step 1 `grep -c` → `6`; the field loop → no output; `grep -c -- '--port <one of them>\|port=' docs/runbooks/seat.md` → `ge 2`; `nix build .#checks.x86_64-linux.lint -L` → exit 0; `nix develop -c python3 pkgs/evidence/repomap.py --root . check` → exit 0.
4. **Mutants.**
   - *M1 field-drift*: rename `dsh_home` to `dsh-home` in the runbook → the field loop prints `missing dsh_home`.
   - *M2 section-dropped*: delete `## The job directory` → the `grep -c` → `5`.
   - *M3 stale-port-story*: reinstate a "pick a free port with `--port`" sentence in place of the request sentence → `grep -c -- '--port. is a request' docs/runbooks/seat.md` → `0`; the probe below fails (today the page's one `request` at `:127` is the broker's request log, which the old probe wrongly counted).
   - *Negative control*: `## The two caps` (`grep -c '## The two caps' docs/runbooks/seat.md` → `1`) must survive unchanged — mutant: delete it → `0`; and `lint` must stay green on the unchanged sections (mutant: a trailing-whitespace line → `lint`'s markdown step fails; paste the checker's line).
5. Commit; body pastes Step 1's two reds and Step 3's counts.

**probes:**
- runbook-sections: `grep -c '^## The job directory\|^## Ports\|^## The drive preset\|^## Hooks\|^## Memory\|^## The payload seam' docs/runbooks/seat.md` :: ge 6 :: SA9 Step 2
- runbook-sections-exact: `grep -c '^## The job directory\|^## Ports\|^## The drive preset\|^## Hooks\|^## Memory\|^## The payload seam' docs/runbooks/seat.md` :: le 6 :: exact count, SA9 Step 2
- runbook-port-request: `grep -c -- '--port. is a request' docs/runbooks/seat.md` :: ge 1 :: SA9 Step 2, the Ports section's contract sentence
- runbook-caps-kept: `grep -c '^## The two caps' docs/runbooks/seat.md` :: ge 1 :: SA9 control
- runbook-caps-once: `grep -c '^## The two caps' docs/runbooks/seat.md` :: le 1 :: exact count, SA9 control

