# The operator's seat as the machine's driver — the drive job and its spool, the ladder in the routing table, the class from `touches`, the prior attempt, the ladder report (plan, 2026-09-06)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The seat driver (`tools/factory/seat`) reads the `### KEY (kind, size) — title` sections below; every section carries `dependsOn`, `touches`, `acceptance` and a commit subject. A seat sees only `## Global Constraints`, `## Assumptions` and its own section.

**Goal:** the operator talks to a `drive` job on the existing seat unit instead of to Fable; that seat dispatches the machine's work through the existing driver scripts and climbs a ladder of model × effort rows only when a rung fails, carrying the failed attempt forward; every attempt is recorded with the variables that produced it (rung, class, prior, escalate) so `evidence report ladder` prints, per model per class, how often a rung's work landed.

**Spec:** `docs/superpowers/specs/2026-09-06-operator-seat-driver-design.md` — `wc -w` → `2266`, size M (S ≤ 1,500 < M ≤ 4,000; `factory_plan_size`'s rule). Its three operator questions stand unanswered on the board (`grep -n 'Answer the questions' docs/OPERATIONS.md` → item (2)); this plan follows each question's default and names the row that changes on an answer.

**Drafting record:** by-ref drafting on the tree at HEAD `4a7374ca4842568fdc7f45caac02b503bfb80c35` (`git log -1 --format=%H`), 2026-09-27 (the machine's clock) over a tree whose board and evidence fixture stop at 2026-09-06 11:10 CDT (`head -1 evidence/MANIFEST.csv` → `# evidence snapshot -- fixture F1, cutoff 2026-09-06T11:10:32-05:00`), so the plan is dated 2026-09-06. Every command below is in `/tmp/draft-scratch/queries.log`. `python3 pkgs/evidence/tasks.py --root . check` printed nothing. Three inputs are degraded and said so where they bind: the git history is one commit (`git log --since=2026-09-06 --oneline | wc -l` → `1`, subject `snapshot`), so `landed` derives empty here (Assumption 1); `~/flakes/dsh-harness` is absent (`ls -d ~/flakes` → `No such file or directory`), so SD9's facts are `unavailable:`; `evidence bundle --markdown` reads `Live: unknown generation at none` and no check covering HEAD — the store's rows are at earlier revisions, so nothing below claims a check green at HEAD.

**Invariants:** brief §3.2 and §3.3 — the drive job runs behind the seat broker like every seat job (`HTTPS_PROXY` at `10.100.4.1:3141`, the placeholder credential, `InaccessiblePaths = [ "/var/lib/secrets" ]`; nothing here adds a route, a host or a credential); §3.5 — every routing choice (a rung, a fallback, a class row, the driver's own row) is a row in `docs/ledger/routing.toml` reviewed in a diff, and the guard rules move into `docs/ledger/guard-rules.toml`, also a diff. No basket, no new egress host, no key in any Nix expression or fixture (the fences' secret shapes are never written in full). The seat's reach widens in exactly one named way — the `seat@` unit's `PATH` gains the binaries the driving verbs need (SD5, D8) — asserted on the rendered unit and listed for the operator; `ReadWritePaths` is unchanged (the spec's own assertion).

## Questions for the operator

Three, each decidable in one word, each with the row that changes on the answer.

1. **The driver's own row** (`route = "openrouter", role = "orchestrate"`, rung 1). **Recommendation:** Pro at effort **high**, measured against Pro medium over the first five driver sessions by `evidence report ladder`. **Default if unanswered (what SD1 writes):** Pro **medium** — the seat's saved default today — as rung 1, with Pro high as rung 2 and `claude/orchestrate` (fable high) as rung 3, so the measurement the recommendation asks for happens on the ladder itself. An answer of "high" swaps the model/effort of rungs 1 and 2 in one row edit.
2. **Anthropic models on OpenRouter as rungs.** **Recommendation:** keep the hold (`docs/decisions/2026-09-05-dsh-harness-factory-parked.md`, addendum point 3: "a new data path to check against this decision's ZDR rule before any row names it"); the `claude` rungs stay printed launch lines and the report's `escalate` column shows whether they are ever reached. **Default:** hold — no `route = "openrouter"` row names an Anthropic model.
3. **The class vocabulary.** **Recommendation:** derived from `touches` (spec §5: nothing new to type, the heading regex and the guard's append-only rule untouched). Alternative: a third field in the heading, which touches `HEADING_RE`, `HEADING_ERE` in the orchestrator guard and the harness's skill. **Default:** derived (SD2).

## Spec-to-task map

Spec items are the design's numbered sections and the bullets of its Tests, Questions, Risks and Not-in-this-spec parts.

| spec item | where it lands |
|---|---|
| Design 1 — the `drive` job mode: DSH_HOME with the driver's skill set; model and effort from `openrouter/orchestrate`; the interactive seat unchanged | SD4 (`seat-submit drive`, the payload check, the row resolved by `route.py`, the shared home refused); SD1 (the row); SD9 (the `driving` skill); the interactive seat: `out:` nothing touches `~/.local/share/dsh-openrouter` or its `settings.yaml` (SD4 refuses it as a drive home) |
| Design 2 — the spool as the one host-side actor; `ExecStart` asserted in `seat-eval`; the driver's guard = hook-guard's rules plus the orchestrator guard's rules in one shared file, proven by the sweep fixture against both | SD5 (`seat-spool.path`/`.service`, `seat-spool.py`, the `seat-eval` and `seat-vm` assertions); SD6 (`docs/ledger/guard-rules.toml`, the orchestrator guard reads it); SD7 (hook-guard reads it; the 442-row parity test) |
| Design 3 — `rung`/`fallback` rows, `factory_route --rung N`, `route.py check`'s two refusals, the climb bound to rule A1, the sideways fallback, the first rows with claims, a `claude` rung printed not run | SD1 (the rows, both lookups, the validators, the claims); SD3 (rung from the key, `--rung`, `--fallback`, the printed launch line and `escalate:`); D1 corrects the spec's own table where it breaks its one-variable rule |
| Design 4 — `--prior <run>/<KEY>`, the `## Prior attempt` block composed by the driver, recorded as `prior:` | SD3 |
| Design 5 — `docs/ledger/task-classes.toml`, one primary class per task, printed in the brief, `class:` in the result, `class` in the routing key | SD2 (the table, `tasks.py`), SD3 (`class:` in the result, the lookup), SD1 (`class` in the key) |
| Design 6 — the `tasks` row carries `rung`, `class`, `prior`, `escalate`; `evidence report ladder` at n ≥ 5; rows change only by a commit citing a report line | SD8 (`dependsOn` T2 and T10a of `2026-09-06-telemetry-store-1.md` — the streams and the join this report stands on); the header rule: unchanged text in `routing.toml`, restated in SD1's row comments |
| Design 7 — what the driver may decide alone | SD9 (the skill's rules) and this plan's Global Constraints for the drive seat; the deterministic pieces are guards: SD4 refuses the shared home, SD5 refuses an invalid `job.json`, SD1 exits 3 on an exhausted ladder |
| Tests: unit (bats) — `--rung 2`, rung 4 exits 3, the two-variable ladder refused, a fallback without a row refused, the `## Prior attempt` block, `seat-submit drive --no-start`, the shared rules under hook-guard | SD1, SD3, SD4, SD7 |
| Tests: evidence-unit — the tie rule, the four new fields, `report ladder` refuses n = 4 and prints the n = 5 table | SD2, SD8 |
| Tests: factory-unit — `route.py models` and `factory_route` agree on every rung; the built-in map still matches the rung-1 `claude` rows | SD1 |
| Tests: seat-eval — the spool's `ExecStart`; the drive job inherits `ReadWritePaths` | SD5 |
| Tests: seat-vm — a drive job answers on the port; `seat-submit headless --no-start` from inside a job is started by the spool and reaches the fake upstream with the injected header; an invalid `job.json` is never started | SD5 |
| Tests: lint — the harness's whole-tree gate after the `driving` skill | SD9 (`repo: dsh-harness`; the gate is that repo's, `unavailable:` here) |
| Questions 1–3 | above |
| Risks — a wrong dispatch bounded by the spool and A1; the `claude` rungs' demand as a gap; every rung above 1 unmeasured with claims; the harness gate matching `rung`/`fallback`; the class as true as `touches` | SD5, SD1 (claims `ladder-rung3-demand-unmeasured` and one per unmeasured rung), SD9 (the gate run), D11 (the spec's false fact about the integrator — corrected here, not leaned on) |
| Not in this spec | §Not in this plan |

## Decisions

Each with the reason and the alternative; the operator vetoes any by a word.

- **D1 The one-variable rule and the spec's own table.** The spec refuses "a ladder where two adjacent rungs change more than one of {model, effort}" and then lists `implement/docs/any: Flash off → Pro medium` and `review/any/any: Pro medium → claude review (opus high)` — two variables each. Rule as SD1 validates it: on one route, adjacent rungs differ in exactly one of {model, effort}; a step that changes the route is one variable (the route) and carries the target route's own model and effort, because the effort scale is per provider and the comparison across routes is never clean anyway. The docs ladder becomes three rungs: Flash off → Flash **medium** → Pro medium (each one variable). Alternative: drop the rule — refused, it is the spec's reason for the ladder.
- **D2 Question 1's default on the ladder.** `openrouter/orchestrate`: rung 1 Pro medium, rung 2 Pro high, rung 3 `claude/orchestrate` fable high (a new row with `rung = 3`; the dark factory's own `claude/orchestrate` rung-1 row is untouched, so `route.py models` is unchanged).
- **D3 The rung comes from the key, never from a run name.** `factory-task` derives the rung with one tokeniser (`factory_key_rung`): strip trailing round tokens (`r` with optional digits, or one fix letter `b`/`c`/`d`) until none matches; any `r` token → rung 3, else any fix letter → rung 2, else rung 1 — the telemetry plan's D7 rule, so `<KEY>b` = rung 2 and `<KEY>r`, `<KEY>rb`, `<KEY>r2` = rung 3 (the climb has three rungs; a re-plan's fix round stays on rung 3). `--rung N` overrides and is recorded as such. The `.result` carries `rung:`; the ingest reads the line and never re-derives it (telemetry design §4.6).
- **D4 `factory_route`'s output stays byte-stable.** Without `--rung` it prints `MODEL EFFORT` for rung-1 rows on the requested route, as today (every existing bats test and `factory-review` keep working). With `--rung N` it prints four fields `MODEL EFFORT ROUTE FALLBACK` (`-` for no fallback) and, without `--route`, searches both routes — a `claude` rung is a real row the driver can see and refuse to run. Alternative: a separate `factory_ladder` function — one more thing to cross-check for no gain.
- **D5 One class engine.** `tasks.py` derives the class (the glob rules live in `docs/ledger/task-classes.toml`); `factory-task` asks `tasks.py class` through `factory_py` (the toolbox devShell, the seam `82-factory-dispatch.bats` already uses) and falls back to `any` with a log line when the query fails. No second glob engine in bash. The class vocabulary is the ten spec names plus `any`, pinned in `route.py`, `factory_route` and `tasks.py` by one shared fixture test.
- **D6 The drive row is resolved in `seat-submit`** by importing `tools/factory/route.py` by path (`resolve(rows, "openrouter", "orchestrate", "any", "any")` — the one Python implementation, cross-checked with the bash one by `factory-unit`); `job.json` records `route` beside the resolved `model` and `effort`, so `seat-run` needs no lookup and the job directory stays the record. Alternative: a third lookup in `seat-submit` — refused (RT2's lesson).
- **D7 `--no-start --wait` and an atomic job directory.** The spool watches the jobs directory (`PathChanged`), which fires on entries appearing in it and not on writes inside a subdirectory, so `seat-submit` builds the job under `<jobs-dir>/.tmp-<id>/` and `os.rename`s it to `<jobs-dir>/<id>` whole. `--wait` polls `result.txt` without ever calling `systemctl` (the driver inside the unit must not reach the control socket — spec Design 2). Whoever starts the unit writes a `started` marker in the job directory, so the spool never starts a job twice.
- **D8 The unit's `PATH` and cache.** The driving verbs run `factory-*` scripts, which need `bash`, `git`, `nix`, coreutils, `flock`/`setsid`, `ps`, `awk`, `grep`, `sed`, `find`, `zstd` and `seat-submit`; the `seat@` unit's `path` today is `cfg.harnessPackage` and `pkgs.iproute2` only. SD5 adds exactly those packages (asserted as a list in `seat-eval`; A2 lists them for the operator), following the lane's precedent (`nixosModules/modelLane.nix` puts `/run/current-system/sw` on its `claude` kind's PATH — this plan names packages instead of the whole profile). The wrapper writes its cache under `${XDG_CACHE_HOME:-/tmp/dsh-openrouter-cache-<uid>}` and the unit runs `ProtectSystem = "strict"` without `/tmp` in `ReadWritePaths`, so on core (unlike the VM, which admits `/tmp` for its fixtures) a job's `mkdir -p -- "$XDG_CACHE_HOME"` has nowhere to write: SD5 sets `XDG_CACHE_HOME=/var/lib/seat/cache` in the unit and declares the directory, and its VM test stops admitting `/tmp` so the production sandbox is what is tested. `ReadWritePaths` itself does not change (the spec's assertion). Whether `nix develop` runs to completion inside the unit is **unmeasured** until the operator's first drive session — claim `driver-verbs-inside-seat-unit-unmeasured` (SD1 files it; the Operator section's drill closes it).
- **D9 The rule file and its readers fail closed.** `docs/ledger/guard-rules.toml` uses only `[[table]]` blocks with scalar `key = "value"` lines (the shape `factory_route` and `factory-dispatch` already walk in pure bash; `tomllib` reads it in Python). The orchestrator guard reads it from beside itself (`<dir of $0>/../docs/ledger/guard-rules.toml`, overridable by `ORCHESTRATOR_GUARD_RULES`), hook-guard from `--guard-rules` (the wrapper passes `${FACTORY_GUARD_RULES:-$HOME/nixos-agent-env/docs/ledger/guard-rules.toml}`, the routing-table pattern). An unreadable or malformed file is a DENY with the reason on every bash call (CR2r3b's rule: a fault denies); the pre-commit lint validates the file so the orchestrator never denies itself by accident. The parity oracle is the orchestrator guard itself over the 442 sweep rows — no verdict list is typed.
- **D10 The tasks row's field names.** The envelope owns `kind`, so the task's kind is `task_kind` — the store on core already says so (`describe` over `evidence/derived/tasks.jsonl` lists `task_kind`, not `kind`, beside the envelope's `kind`; T2's plan text writes `kind`). SD8 greps the landed `streams.py` before writing and reports a deviation rather than guessing. `rung` is `("int", 1, 9)`, `class` an enum of the eleven names, `prior` `("null", ("re", …))` in the `<run>/<KEY>` shape (the `id` class has no `/`), `escalate` `("null", ("re", r"^claude/(implement|review|orchestrate)$"))`.
- **D11 The spec's false fact.** Risks: "The integrator already refuses a task whose commit touches files outside its `touches`" — `factory-integrate` refuses only `docs/OPERATIONS.md changed outside the queue block` (the board records the correction). The class is therefore as true as the plan author's `touches`, and nothing in this plan leans on the integrator. A `touches` guard at the integrator is a driver task the spec does not name — noted for the board, not typed here.
- **D12 Separate result lines, T2's `route` regex untouched.** `class:`, `rung:`, `fallback:`, `prior:`, `escalate:` are their own lines in the `.result`; the `route:` label keeps T2's grammar `^(explicit|unknown|implement/(code|docs)/(XS|S|M|L))$` so T2's ingest never sees a route it cannot parse.
- **D13 Keys.** `SD1`–`SD10`; no letter after a digit (`CHAIN_RE = ^(?P<root>.*\d)(?P<suffix>[a-z]{1,2})$` would read `SD7a` as a fix round of `SD7`).

## Global Constraints

- **Build-only.** No `sudo`, no `nixos-rebuild`, no `systemctl start/stop/restart/enable`, no basket mount/teardown, no reading `/var/lib/secrets/*`, `~/.config/openrouter/key` or `~/.config/restic/password`; never write under `/var/lib/seat` or `/var/lib/evidence`. The operator switches (§Operator). Tests set `EVIDENCE_STORE`, `--jobs-dir` and `FACTORY_ROOT` to temp dirs; every driver script under test is invoked as `"$REAL_BASH" <script>` with fakes on `PATH` (never the real `dsh-openrouter`, `seat-submit` or `systemctl`) — the idiom of `tests/unit/80-seat-driver.bats`.
- **Never open a seat log, a transcript, a session file or a store body** (`~/factory/runs/*/*.log`, `*.dsh-home`, `~/.claude/projects`, `/var/lib/evidence/*.jsonl`). The `## Prior attempt` block is composed from a `.result` and a review file only; tests use synthetic files they write.
- Commits go through the devShell (`nix develop -c git commit -F <msgfile>`); `git add` new files **before** any `nix build`; never `--no-verify`, never `2>/dev/null` a gated command. One commit per task; the subject is the section's byte-exact `commit subject`; the trailers are the WORKSPACE RULES' two lines.
- **The commit body is produced, never typed.** Before committing, write `<workspace>/.scratch/commit-body.sh` that prints the subject, a blank line, then for each command the section's Steps name as red or green: `printf '$ %s\n' "<cmd>"` followed by the command's own output (`2>&1 | tail -n 40`), then a blank line and the two trailers; run it into a message file (`bash .scratch/commit-body.sh > .scratch/msg`) and commit with `-F .scratch/msg`. `.scratch/` is never added.
- TDD: the failing check first, shown red with its output, then green. A load-bearing test counts only once it has been shown to fail; a test that cannot fail is a `vacuous-test` major finding. Every proxy names what it stands in for and its gap (`docs/decisions/2026-09-03-test-based-reality-amendments.md`).
- **The code blocks below are specifications, not byte-exact files.** After writing Python run `nix develop -c ruff format <paths>` (88 columns); shell goes through `nix develop -c treefmt`; a reformatting-only difference is not a deviation. Python is stdlib only in `pkgs/` and `tools/factory/route.py`; tests may use pytest. New Python under `pkgs/dsh-openrouter` must pass the package's build-time flake8 self-check (`flakeIgnore = [ "E501" ]` only).
- **One writer per tree.** Work only in the isolated worktree the task was started in, on `task/<KEY>`; `touches` is a contract — a file outside it is a deviation to report, not to write. One exception, never a deviation: `docs/MAP.md` (regenerate with `python3 pkgs/evidence/repomap.py --root . write` whenever a file is added or removed — `lint` checks it). Never merge `main` into your branch and never edit, regenerate or restore the board (`docs/OPERATIONS.md`): the integrator and the orchestrator do both after your commit. If the pre-commit hook rewrites the board's queue block during your commit, `git add docs/OPERATIONS.md` and re-run the same commit command; nothing else in that file is yours.
- **Vocabulary.** The ladder's words are `rung` and `fallback`; no prompt, README, skill or comment written by this plan names a model tier or an escalation policy in prose (the harness's whole-tree gate refuses "per-dispatch tier-escalation wording"); the routing table is the one place a model is chosen.
- Bats: one `[ … ]` per line (an `&&` chain cannot fail); `FACTORY_ROOT` under `$BATS_TEST_TMPDIR`, never the real `~/factory`; a fake on `PATH` records its argv to a file the test reads.
- Nix style: statix rejects `{ ... }:` headers (write `_:` or name the args); every path in a systemd unit is a store path or a literal the module owns; no `sk-or-` string anywhere (the `seat-eval` assertion and the secret-shape fence refuse it).
- The seat's final reply ends with the four `FACTORY-*` lines exactly as the WORKSPACE RULES state them; never copy the WORKSPACE RULES, the `## Prior attempt` block or the result block into a project file.

## Assumptions

1. **This tree's history is one commit** (`git log --since=2026-09-06 --oneline | wc -l` → `1`, subject `snapshot`), so `tasks.py` derives no task as `landed` here: P11, T1, T2 and T10a read `approved`/`ready`/`blocked`, and the Waves table's third wave shows SD8 blocked on T2/T10a. On core (board START HERE 2026-09-06 ~10:45): P11r landed 04:51 ("the driver line is closed"), T1 ran as `tel1b` and awaits its gate, T2/T3/T10a are not started. The driver guards A5 names — `FACTORY_PLAN` required, a board rewrite refused at integration, a near miss recorded — are in the tree (SD3's Facts paste the anchors), so no `dependsOn: P11` is needed.
2. `~/flakes/dsh-harness` is not present where this plan was drafted; SD9's facts about that repo are marked `unavailable:` and its seat verifies them first. The catalog reaches a seat through the symlink `~/.local/share/dsh-openrouter/skills` → `~/flakes/dsh-harness/skills` (the wrapper's own recipe: `warn_missing_payload "$DSH_HOME/skills" "skill catalog" "ln -s ~/flakes/dsh-harness/skills $DSH_HOME/skills"`).
3. The devShell's `python3` here is `Python 3.11.15` (`nix develop -c python3 --version`); the telemetry plan measured 3.14.7 on core on 2026-09-06 — both carry `tomllib`. Tests never depend on a `multiprocessing` start method.
4. `EVIDENCE_STORE` overrides the store root everywhere; `factory_py`/`FACTORY_PYTHON3_CMD` and `FACTORY_EVIDENCE_CMD` are the driver's test seams (the build sandbox has no `nix develop`).
5. The seat unit is live on core since switch #20 (generation 45 = `a53d2e5`; rollback generation 44 = `7d20da1`); `seat-submit` is a flake package and not on the host PATH (`nix run ~/nixos-agent-env#seat-submit -- …`), and no real task has yet run through `seat@` on core (the VM proved a one-word answer). Nothing in this plan needs the switch to be tested; SD5's switch (#21) is the operator's.
6. On core `/var/lib/evidence/derived/tasks.jsonl` will be written by T2's ingest; the fixture store read here (238 rows) carries `task_kind`, `error_class` (`none` 220, `no-result-line` 12, `template-echo` 6) and `route` (`unknown` 152, `implement/code/S` 57, `explicit` 12, …) — the group sizes `report ladder` will see.
7. `docs/ledger/claims.toml` validates silently with `--today 2026-09-06` and lists fourteen gaps past `review_by` with `--today 2026-09-27`; extending them is the operator's item outside this plan. New gap rows use `review_by` dates two weeks after landing.
8. `hosts/core/seat.nix` sets `operatorUser = "dalhaka"`; `seat-eval` asserts on the real `core` config (`c = self.nixosConfigurations.core.config`), so the spool assertions belong there, not in a fixture system.
9. `tests/evidence/fixtures/plans/` holds `legacy.md`, `second.md`, `typed.md` (`FIXTURES = HERE.parent / "fixtures" / "plans"` in `test_tasks.py`); SD2 adds its fixture beside them.
10. The orchestrator guard's payload names tools `Bash`/`Edit`/`Write`; hook-guard's names `bash`/`edit`/`write` with a `hook_event_name` field; both resolve relative paths against `CLAUDE_PROJECT_DIR`. The parity test feeds each sweep row in each guard's own shape.

## Waves

Peel-off groups from the graph's own code over the draft attached to this tree — P1's form (`check --draft`); every draft rule passed (acceptance names against `docs/MAP.md`, explicit `touches`, the four house sections, the byte-exact subjects against `acceptance`, sizes, one section per key):

```
$ python3 pkgs/evidence/tasks.py --root /home/user/tvix-aios-os --runs-dir /nonexistent --store /nonexistent check --draft /tmp/draft-scratch/draft-0.md
waves: [[["SD1"], ["SD2"], ["SD4", "SD6"]], [["SD3"], ["SD5"], ["SD7"]], [["SD10"], ["SD9"]]]
conflicts: … 50 rows (the list below sequences every one) …
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
- In `dsh-harness`: `P13` (blocked on P8 here; landed on core as 81c5925) shares `CHANGELOG.md` with SD9 — one dated line each; the integrator's merge.

## Operator

Every command is pasted from a dry run on this tree or quoted from the runbook or the board's RECIPES; nothing here is a sentence where a command would do. Steps 1, 3–7 need no switch; step 2 is the one switch.

1. **Launch wave 1** — §Dispatch's first line without `--dry-run`, in the background, after T1 has fast-forwarded (its gate is pending on the board; SD1 and SD2 share `tools/factory/seat/factory-lib.sh` and `pkgs/evidence/tasks.py` with T1 — whichever lands second is merged by the integrator, recipe step 2). Acceptance: `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep Running` names `nixos-agent-env/SD1`, `SD2`, `SD4`, `SD6`. Before the launch (A3/A9): the OpenRouter balance is your item — four Pro seats at the 2026-09-04 rate are $0.40–0.80 plus their gates; the board read $32.23 at 2026-09-06 08:55.
2. **After SD5 lands — switch #21 (A2).** Build and diff:
   ```
   nix build .#nixosConfigurations.core.config.system.build.toplevel
   nix store diff-closures /run/current-system ./result
   ```
   **Predicted delta** (a prediction, measured on the landed tree before this line is run): two NEW units `seat-spool.path` and `seat-spool.service`; the seat tools package changes (`seat-spool.py` joins `seat-submit.py`/`seat-run.py`); the `seat@` unit text changes (`PATH` gains `seat-submit`, `bash`, `coreutils`, `findutils`, `gnugrep`, `gnused`, `gawk`, `util-linux`, `procps`, `git`, `nix`, `zstd` — all already in the system closure, so no new package lines beyond the seat tools; `XDG_CACHE_HOME=/var/lib/seat/cache`); a tmpfiles line for `/var/lib/seat/cache`; and, when SD7 has landed by then, the `dsh-openrouter` wrapper (the new `hook-guard`). Nothing removed. Then `sudo nixos-rebuild switch --flake ~/nixos-agent-env#core` (your command, never a seat's). Acceptance: `systemctl status seat-spool.path | head -3` shows `active (waiting)`; `test -d /var/lib/seat/cache && stat -c %U:%a /var/lib/seat/cache` prints `dalhaka:700`. Rollback: `sudo /nix/var/nix/profiles/system-45-link/bin/switch-to-configuration switch` (generation 45 = `a53d2e5`, the board's live generation; read the number from `nixos-rebuild list-generations` if it moved).
3. **Seed the drive home (once):**
   ```
   . ~/nixos-agent-env/tools/factory/seat/factory-lib.sh && factory_seed_dsh_home ~/factory/drive/dsh-home
   ```
   Acceptance: `ls -l ~/factory/drive/dsh-home/skills ~/factory/drive/dsh-home/AGENTS.md` shows symlinks into `~/flakes/dsh-harness`, and `test -f ~/factory/drive/dsh-home/skills/driving/SKILL.md` (after SD9 landed in the harness) exits 0. The home is never `~/.local/share/dsh-openrouter` (the drive job refuses it).
4. **Start the drive job and open it:**
   ```
   nix run ~/nixos-agent-env#seat-submit -- drive --workspace ~/nixos-agent-env --dsh-home ~/factory/drive/dsh-home --port 43210
   ```
   Acceptance: it prints a job id; `cat /var/lib/seat/jobs/<id>/url.txt` → `http://10.100.4.2:43210`; `jq -r '.model, .effort, .route' /var/lib/seat/jobs/<id>/job.json` → `deepseek/deepseek-v4-pro-0813`, `medium`, `openrouter/orchestrate/any/any` (Question 1's default); open the URL in Firefox. Stop it when done: `systemctl stop seat@<id>` (yours; the polkit rule allows it).
5. **The first drive session (the drill that closes `driver-verbs-inside-seat-unit-unmeasured`):** say "brief" — the seat runs `tasks.py brief` and shows it; say "dispatch <plan> dry run" — it shows a `would run: factory-wave …` line; say "go" — it launches, and the spool starts the seat(s): `journalctl -u seat-spool.service -n 5` shows `spool: <id>: started` and `systemctl list-units 'seat@*'` lists the running job(s). If the seat reports that `nix develop` or `git` failed inside the unit, paste the line to the board: that is the measurement the claim waits for, and the fix is a unit `path`/cache change under SD5's assertions (a fix round). Record the outcome as `operator:<date>` on the claim.
6. **The record:** after SD8 and the telemetry loop (its Operator step 3) have run, `nix run ~/nixos-agent-env#evidence -- report ladder --repo ~/nixos-agent-env`. Expected on today's store: one printed group beginning `openrouter/implement/code/S/any deepseek/deepseek-v4-pro-0813 medium rung 1: n=57` and a trailer `groups: 1 printed, N refused under n=5` — every other group is under five rows until the driver has run.
7. **Rollback per task:** `git -C ~/nixos-agent-env revert <the task's commit>` through the devShell (`nix develop -c git revert …`); the guard rule file's rollback is the same revert (both guards read the file, so both roll back together); a drive job is stopped with `systemctl stop seat@<id>`; the spool with `systemctl stop seat-spool.path` (yours) — after which jobs submitted `--no-start` wait until it is started again.

## Dispatch

Runs: `sd1` (wave 1), `sd2` (wave 2), `sd3` (wave 3: SD10 here), `sd4` (SD9 in `~/flakes/dsh-harness`, hand-launched — the dispatcher's graph query needs the repo's own `repos.toml`), `sd5` (SD8). None exists under `~/factory/runs` on this tree (no `~/factory` here; on core check `ls ~/factory/runs | grep -c '^sd'` → expected `0`). Plan path after the Ship phase: `docs/superpowers/plans/2026-09-06-seat-driver.md`.

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

**Relaunch after a seat death (A6):** the dead seat's diff stays in `~/factory/ws/<run>/<KEY>`; relaunch the one key as `FACTORY_PLAN=docs/superpowers/plans/2026-09-06-seat-driver.md setsid -f bash -c 'exec tools/factory/seat/factory-wave <run>b ~/nixos-agent-env "<KEY>" >> ~/factory/runs/<run>b.wave.log 2>&1' </dev/null`, after the `error_class` of the dead result is read (T2's line; until it lands, the `.result`'s notes): `budget-402` waits for the top-up, `provider-error` and `boot-failure` relaunch once — after SD3 lands, with `OPENROUTER_MODEL` unset and `factory-task --fallback` through a one-key wave when the row carries one; `unknown-model`/`template-echo`/`no-result-line` never relaunch blind.

## Anticipation

| row | applies? | artefact |
|---|---|---|
| A1 dispatch | yes | §Dispatch: run names `sd1`–`sd4`, the dry-run line per wave (pasted for wave 1 over the draft), the five-step landing recipe |
| A2 switch | yes — SD5 touches `nixosModules/seatLane.nix` and `flake.nix`'s `seat-eval`; SD7 changes `pkgs/dsh-openrouter/hook-guard.py`, which the wrapper package embeds at build time (`hookGuard = writePython3MinimalBin "hook-guard" … (builtins.readFile ./hook-guard.py)`) | Operator step 2: the two build commands, the delta as a prediction, the acceptance, the rollback generation |
| A3 credentials, names, top-ups | the OpenRouter balance before wave 1 (four seats) and wave 2 (three); the drive home seed; no credential, no DNS name, no password file | Operator steps 1, 3 |
| A4 mutation tables | yes | every section's Tests table, one mutant per assertion |
| A5 driver guards | the tree has them: `factory-task` — `factory_die 2 "FACTORY_PLAN is unset — name the plan (FACTORY_PLAN=<plan.md> …) or launch through factory-dispatch"`; `factory-integrate` — `logboth "REFUSED $key: docs/OPERATIONS.md changed outside the queue block"`; the near miss — `notes_line="FACTORY-NOTES result-misparse: $near_note"` recorded as `failed`; a `done` with zero commits demoted (`status=done but the branch has no commits`) — all pasted from `grep -n` over the two scripts (queries.log). This plan adds the next deterministic pieces as tasks, not sentences: an exhausted ladder exits 3 before any run dir (SD1/SD3); the shared home and a missing payload refuse a drive job (SD4); an invalid `job.json` is never started (SD5); an unreadable rule file denies (SD6/SD7) | no `dependsOn: P11` (landed on core; Assumption 1) |
| A6 seat death | yes | the relaunch line under §Dispatch; after SD3, `--fallback` for the three relaunch classes |
| A7 what a landing unblocks | yes | recipe step 5 |
| A8 claims | this plan files nine gaps (SD1) and closes none; `seat-key-exception-undecided` stays SB5's; `forbidden-list-single-source` stays open (SD7 reduces the copies from three to two plus the file) | SD1's claims block; `claims.py validate --today 2026-09-06` silent (SD1 row 11) |
| A9 hold? | wave 1 waits for T1's fast-forward (Operator step 1) — three of its four tasks share files with T1/T2/T3 (`factory-lib.sh`, `tasks.py`, `flake.nix`) and SD6 shares `githooks/pre-commit` with CR4 and T1W; SB5/SB6 are HELD by the operator and SB6 shares `nixosModules/seatLane.nix`, `pkgs/seat/seat-submit.py` and `tests/integration/seat-vm.nix` with SD4/SD5 — when the hold lifts, SB6 merges main first (recipe step 2); the bundle here shows no check green at HEAD (fixture; the board records lint, evidence-unit and host-core green at a2667bc); spend unmeasured in the tree (declared) | the wait on T1 and the SB6 order are stated in §Waves |
| A10 questions | yes | three, each with a recommendation and a default, and the row each answer changes |
| A11 handoff line | prepared: "seat-driver: on the seat: sd1 (SD1 SD2 SD4 SD6) after T1 lands; in gate: —; next: sd2 (SD3 SD5 SD7); switch #21 after SD5; plan docs/superpowers/plans/2026-09-06-seat-driver.md, judgement docs/reviews/plan-judgements/2026-09-06-seat-driver.md" | for the board's START HERE |
| A12 re-plan | not a re-plan | — |
| A13 hooks / second consumers | yes: SD6 edits the orchestrator's PreToolUse hook (`tools/orchestrator-guard.sh`, run by the host's bash from the tree named in `.claude/settings.json`, reading `docs/ledger/guard-rules.toml` beside itself — live from the tree at once), SD7 the seat's hook (`hook-guard`, python3Minimal inside the `dsh-openrouter` package — live after a switch — reading the same file from `~/nixos-agent-env` through `--guard-rules`); both fail closed on an unreadable file with a named reason and never exit non-zero (the harness reads a non-zero exit as allow); the lint's `--check-rules` line keeps the file valid before it is committed; no Stop hook, so `stop_hook_active` does not apply | SD6/SD7 Interfaces and their rows 1–2 |
| A14 deny rules | yes: SD6 adds hook-guard's three `$HOME` prefixes to the orchestrator guard (`.claude`, `.config/openrouter`, `strategy` — writes there were already refused for seats; the orchestrator's recipes in `docs/runbooks/session.md` touch none: `grep -c 'strategy\|\.config/openrouter' docs/runbooks/session.md` → 0); SD7 makes the seat refuse what the orchestrator guard refuses — the 442 sweep rows. Who runs what afterwards: the seat's own recipe (`nix develop -c git commit -F <msgfile>`, `git add <files>`, `nix build .#checks…`, `python3 pkgs/evidence/repomap.py --root . write`) stays allowed and is asserted (SD7's second parity test); the driver's verbs (`factory-dispatch`, `factory-review`, `factory-integrate`, `tasks.py write-board`) are plain commands with no protected operand — allowed; the fast-forward `git -C ~/nixos-agent-env pull --ff-only …` is the operator's/orchestrator's (the sweep row `git pull --ff-only …` allows); `rm .claude/ritual-override` falls to the operator, as today | SD6 row 4, SD7 row 7 |

## Not in this plan

- The automatic relaunch itself (telemetry design §4.3, task T15 — unplanned): this plan gives the driver `--fallback` and the rule of what it may relaunch alone (SD3, SD9); the relaunch line stays a hand launch until T15.
- Anthropic models on OpenRouter as rows (Question 2, hold); Kimi K3 and GLM 5.3 rows (no measurement); any change to the interactive seat the operator opens outside the unit (`~/.local/share/dsh-openrouter`, its `settings.yaml`).
- `evidence report routing|compare` (telemetry design §4.1/§4.6, T10b) — `report ladder` is the one report this spec names.
- The seat lane's own runbook `docs/runbooks/seat.md`, the `lanes.md` paragraph and the `seat-key-exception-undecided` claim (SB5, held); SB6's footguns (held).
- Porting the orchestrator guard's typed-heading Edit/Write rule (rule 1) into the seat guard — the seat is denied every plan write instead (D9); the guard's known gap "a removal through a symlink that points into the plans directory" (its header) stays out of both guards.
- A `touches` guard at the integrator (the spec's Risks lean on one that does not exist — D11): a driver task for a later plan; noted for the board.
- `tasks.py write-board` from the drive seat: allowed by the spec (Design 7) and unchanged; the board's prose stays the orchestrator's.
- The telemetry tasks T1–T18 themselves (their own plan; SD8 depends on T2 and T10a); a `plan` routing row; the media, gaming and nixos-skill repos; fronting the Claude Code session with a broker; Helm Home; Discord.
- Parked for the concept file: the spool's own telemetry rows (a `spool-start` event with the job id and the validation verdict, once telemetry shape B exists); a `report ladder --by class` cut that prints the tie-broken second class per task.

---

## Tasks

### SD1 (code, M) — the ladder in the routing table: rung and fallback rows, class in the key, factory_route and route.py in lockstep, the first rungs marked unmeasured

**dependsOn:** none

**Files:**
- Modify: `docs/ledger/routing.toml` (the header's key grammar; the new rows), `tools/factory/seat/factory-lib.sh` (`factory_route`, `factory_route_check`, new `factory_key_rung`), `tools/factory/route.py` (`CLASSES`, `resolve`, `check`, `lookup`), `tests/unit/80-seat-driver.bats`, `docs/ledger/claims.toml` (the gap rows)

**Interfaces:**

- A `[[route]]` row's keys are exactly `route`, `role`, `kind`, `size`, `model`, `effort` (as today) plus three optional keys: `rung` (an integer `1`–`9`, default `1`), `fallback` (a model id, no default), `class` (one of `nix-module | nix-check | bash-driver | python-evidence | js-workflow | bats-test | vm-test | docs-runbook | docs-plan | docs-board | any`, default `any`). Any other key stays a row error (`unknown key`, exit 3 / `RowError`, as today).
- `factory_route [--route R] [--rung N] [--class C] <role> <kind> <size> [FILE]` (bash) and `route.py [--file PATH] lookup ROUTE ROLE KIND SIZE [--rung N] [--class C]` (python), the same rule: candidates are the rows whose `rung` equals N (default 1) and whose `role`/`kind`/`size`/`class` each equal the request or `any`; specificity = the count of the four fields not `any`; the highest wins, ties go to the earliest row. Without `--rung`: only rows on route R (default `openrouter`) and the output is `MODEL EFFORT` — byte-identical to today. With `--rung N`: rows on route R when `--route` is given, else on **both** routes; the output is `MODEL EFFORT ROUTE FALLBACK` where `FALLBACK` is the row's `fallback` or `-`. `--rung 0`, a non-integer or `--rung` twice → `factory_route: bad --rung %q` exit 3 (`route.py` prints its usage and exits 2 — its hand-rolled argv parser's own usage exit, as for a missing `--file` value). No candidate at rung N → stderr `factory_route: ladder exhausted at rung N for ROLE/KIND/SIZE/CLASS` exit 3 (python: the same words, exit 3 — a new code, distinct from the table errors' 1). The route's `any/any/any` default row is still required (unchanged).
- `factory_route_check [FILE]` / `route.py check` validate every row as today plus: (1) `rung` outside `1`–`9` or not an integer → `row N: bad rung %q`; (2) `class` outside the eleven names → `row N: unknown class %q`; (3) a `fallback` whose model is not the `model` of some other row on the **same route** → `row N: fallback %q has no row on route %s`; (4) the ladder rule over every key a rung-≥2 row names exactly (its own `role/kind/size/class` tuple): resolving that key at rungs 1..max must find a row at every rung (`ladder ROLE/KIND/SIZE/CLASS: rung N missing`) and each adjacent pair either shares the route and differs in exactly one of {model, effort} (`ladder …: rung N→N+1 changes model and effort`; a pair that changes nothing: `… changes nothing`) or changes the route. Exit 3 (bash) / 1 (python) with the first error on stderr.
- `factory_key_rung <KEY>` (bash, factory-lib.sh; D3) prints `1`, `2` or `3`: strip trailing round tokens — `r` followed by optional digits, or exactly one of `b|c|d` — until none matches; any `r` token stripped → `3`; else any fix letter → `2`; else `1`. Pure bash, never fails, an empty key prints `1`.
- `route.py resolve(rows, route, role, kind, size, rung=1, cls="any", any_route=False) -> (model, effort, route, fallback)`: the extra positional-compatible keywords keep `resolve(rows, "openrouter", "orchestrate", "any", "any")` callable (SD4 imports it); `models` still derives the dark factory's map from the `claude` rung-1 rows only.
- The rows SD1 adds (each row's comment names its measurement or `unmeasured`, and the claims file carries one gap per unmeasured rung — the spec's rule):

```toml
[[route]]                       # rung 2 of implement/code/S — unmeasured (claim ladder-implement-code-S-rung2-unmeasured)
route = "openrouter"
role = "implement"
kind = "code"
size = "S"
rung = 2
model = "deepseek/deepseek-v4-pro-0813"
effort = "high"

[[route]]                       # rung 3 of implement/code/S — the claude route; printed by the driver, never run by it (unmeasured)
route = "claude"
role = "implement"
kind = "code"
size = "S"
rung = 3
model = "sonnet"
effort = "high"

[[route]]                       # rung 2 of implement/docs/any (D1: one variable — effort; unmeasured)
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
rung = 2
model = "deepseek/deepseek-v4-flash"
effort = "medium"

[[route]]                       # rung 3 of implement/docs/any (D1: one variable — model; unmeasured)
route = "openrouter"
role = "implement"
kind = "docs"
size = "any"
rung = 3
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]                       # rung 2 of review/any/any — the claude route (unmeasured)
route = "claude"
role = "review"
kind = "any"
size = "any"
rung = 2
model = "opus"
effort = "high"

[[route]]                       # the driver's own row (Question 1 default: Pro medium; unmeasured)
route = "openrouter"
role = "orchestrate"
kind = "any"
size = "any"
model = "deepseek/deepseek-v4-pro-0813"
effort = "medium"

[[route]]                       # rung 2 of orchestrate (Question 1's recommendation, measured against rung 1 by report ladder)
route = "openrouter"
role = "orchestrate"
kind = "any"
size = "any"
rung = 2
model = "deepseek/deepseek-v4-pro-0813"
effort = "high"

[[route]]                       # rung 3 of orchestrate — the claude route (unmeasured)
route = "claude"
role = "orchestrate"
kind = "any"
size = "any"
rung = 3
model = "fable"
effort = "high"
```

  and one `fallback = "deepseek/deepseek-v4-flash"` on the existing `implement/code/any` row (Flash approved 2/2 in `docs/reviews/2026-09-05-model-comparison.md`; as a sideways fallback it is unmeasured — claim `ladder-fallback-flash-unmeasured`). The header paragraph gains one sentence: "Optional per-row keys `rung` (1–9, default 1), `fallback` (a model with a row on the same route) and `class` (the `task-classes.toml` vocabulary, default any); rows with the same role/kind/size/class and rungs 1..n are that key's ladder; adjacent rungs on one route change exactly one of model/effort."
- Claims (`docs/ledger/claims.toml`, `status = "gap"`, `class = "unmeasured"`, `owner = "orchestrator"`, `opened = 2026-09-06`, `review_by = 2026-09-20`): `ladder-rung3-demand-unmeasured` (closes_by: `report ladder` shows an `escalate` count over five driver sessions, or the rung-3 rows are withdrawn), `ladder-implement-code-S-rung2-unmeasured`, `ladder-implement-docs-rung2-unmeasured`, `ladder-implement-docs-rung3-unmeasured`, `ladder-review-rung2-unmeasured`, `ladder-orchestrate-rung1-vs-rung2-unmeasured` (Question 1's measurement: five driver sessions per rung), `ladder-fallback-flash-unmeasured`, `driver-verbs-inside-seat-unit-unmeasured` (D8; closes_by: `operator:<date>` — one `factory-dispatch … --dry-run` and one real wave from a drive job's UI succeed).

**Facts (2026-09-27 on the tree, commands beside them):**

- `python3 tools/factory/route.py --file /tmp/draft-scratch/fx-rung.toml check; echo rc=$?` → `rc=0`, and `… lookup openrouter implement code S` → `deepseek/deepseek-v4-pro-0813 high`: `route.py` accepts an unknown key (`parse_table` stores any `key = value`, `cur[key] = val`) and treats the rung-2 row as an ordinary row, while `grep -n 'unknown key %q' tools/factory/seat/factory-lib.sh` → `printf 'factory_route: %s: row %d: unknown key %q\n'` — the bash walker refuses it. A table with a `rung` key makes the two implementations disagree today: that is this task's red.
- `grep -n 'Usage: factory_route\|implement | review | verify | baseline | research | audit | orchestrate | plan | any\|cur_spec=0' tools/factory/seat/factory-lib.sh` → `# Usage: factory_route [--route R] <role> <kind> <size> [FILE]`, the role arm (`orchestrate` and `plan` already accepted), `cur_spec=0` (specificity over three fields).
- `grep -n 'def resolve\|spec = (rrole\|MODEL_KEYS = (\|resolve(rows, "claude", role, kind, size)' tools/factory/route.py` → `def resolve(rows, route, role, kind, size):`, `spec = (rrole != "any") + (rkind != "any") + (rsize != "any")`, `MODEL_KEYS = (` and the `models` derivation from the `claude` rows.
- `grep -c '^\[\[route\]\]' docs/ledger/routing.toml` → `14`; `grep -n 'Change rows here, nowhere else' docs/ledger/routing.toml` → the header's last sentence. `cat docs/ledger/routing.toml`: the openrouter rows `implement/docs/any` Flash off, `implement/any/XS` Flash off, `implement/code/any` Pro medium, `review/any/any` Pro medium, the default Pro medium; the claude rows `orchestrate` fable high, `baseline` sonnet low, `implement` sonnet high, `review/code` opus high, `review/docs` sonnet medium, `verify`/`research` sonnet medium, `audit` fable high, the default sonnet medium. No `openrouter/orchestrate` row exists.
- `grep -n 'row.get("route") == "claude"\|model = row.get("model")' pkgs/dsh-openrouter/hook-guard.py` → the seat guard's model rule reads only `route` and `model` per row and ignores other keys: the new keys change nothing there, and a `fallback` must be a model with a row of its own, so the set of permitted models does not widen.
- `grep -n '@test' tests/unit/80-seat-driver.bats | grep -i 'route'` → the existing tests to keep green: `factory_route picks the most specific matching row, first row on ties`, `factory_route rejects a malformed or missing table`, `factory_route_check validates the committed routing table`, `factory_route --route claude picks the claude row, …`, `route.py validates the committed table and cross-checks factory_route's lookup, when route.py is present`, `factory_route and route.py agree on a discriminating tie (earliest row wins)`, `route.py check rejects a row missing any required key, a bad route, or a bad effort`, `route.py and factory_route accept the plan role and refuse the planner role`.
- `grep -n 'route.py' tests/factory/render.test.mjs` → `const routePy = path.join(__dirname, '..', '..', 'tools', 'factory', 'route.py')` and `'dark-factory.js default models must equal route.py models for the committed table'` — the built-in map is derived from `route.py models`, so the rung-1 `claude` rows must be the only ones `models` reads.
- `grep -n '^id = ' docs/ledger/claims.toml | tr '\n' ' '` → 30 ids; none begins `ladder-` or `driver-verbs-`. The gap-row shape: `id`, `text`, `status = "gap"`, `class = "unmeasured"`, `owner`, `opened`, `review_by`, `closes_by` (`sed -n '36,44p' docs/ledger/claims.toml`, the `effort-policy-n1` row).
- `CHAIN_RE = re.compile(r"^(?P<root>.*\d)(?P<suffix>[a-z]{1,2})$")` (`grep -n 'CHAIN_RE = ' pkgs/evidence/tasks.py`) — the graph's chain rule; `factory_key_rung` follows the telemetry plan's D7 tokeniser instead (`grep -n 'round_of' docs/superpowers/plans/2026-09-06-telemetry-store-1.md` → the rule and its table row 16), because `OG1r2` is its own chain root to the graph but rung 3 to the ladder.

- [ ] **Step 1: Write the failing tests** in `tests/unit/80-seat-driver.bats` (each row one `@test`; the fixture tables are heredocs in the test; `factory-lib.sh` is sourced with `. "$SEAT/factory-lib.sh"` the way the existing `factory_route` tests do):

| # | assertion | the one-line mutant that turns it red |
|---|---|---|
| 1 | on a fixture with `implement/code/any` Pro medium (rung 1), `implement/code/S rung=2` Pro high, `claude implement/code/S rung=3` sonnet high and both defaults: `factory_route implement code S` → `deepseek/deepseek-v4-pro-0813 medium` (unchanged shape); `factory_route --rung 2 implement code S` → `deepseek/deepseek-v4-pro-0813 high openrouter -`; `--rung 3` → `sonnet high claude -`; `--rung 4` → exit 3, stderr `ladder exhausted at rung 4 for implement/code/S/any`; `--route openrouter --rung 3` → exit 3 (the claude row is out of the requested route) | print the rung-1 row for an unknown rung; drop the route filter |
| 2 | `--class nix-module` picks a `class = "nix-module"` row over an equally specific `class = "any"` row; `--class any` and no `--class` pick the same row; a row with `class = "bogus"` → `unknown class` exit 3 | count `class` as `any` always |
| 3 | a `fallback` present → the fourth field prints it; `--rung 1` output for a row without one prints `-` | print an empty fourth field |
| 4 | `factory_route_check` on a fixture whose rungs 1→2 change model and effort together → exit 3 `changes model and effort`; rungs 1→2 identical → `changes nothing`; a rung-3 row with no rung-2 resolution → `rung 2 missing`; a route change with both fields changed → exit 0 | drop the route-change exemption → the good fixture fails; drop the gap check |
| 5 | `fallback = "x/y"` with no row → exit 3 `has no row on route openrouter`; a fallback naming a model that exists only on the `claude` route → the same refusal (same route rule) | search all routes |
| 6 | `rung = 0`, `rung = 10`, `rung = two` → `bad rung` exit 3; `rung = 1` explicit equals no `rung` | accept any integer |
| 7 | the committed `docs/ledger/routing.toml` passes `factory_route_check` and `route.py check` (extends the existing committed-table test); `factory_route --rung 3 orchestrate any any` on it → `fable high claude -`; `factory_route orchestrate any any` → `deepseek/deepseek-v4-pro-0813 medium` | any committed row breaking rule 4 |
| 8 | cross-check (extends `route.py … cross-checks factory_route's lookup`): for every fixture key in {implement/code/S, implement/docs/any, review/any/any, orchestrate/any/any} and every rung 1..4, `route.py lookup … --rung N` and `factory_route --rung N …` print the same line or both exit 3 with `ladder exhausted` | any divergence — e.g. python counts specificity over three fields |
| 9 | `route.py models` on the committed table equals the value before this change (pinned as the literal JSON the `factory-unit` test derives) | let `models` see rung-3 `claude` rows |
| 10 | `factory_key_rung`: `SD1`→1, `SD1b`→2, `N7c`→2, `W2-N6b`→2, `SD1r`→3, `SD1rb`→3, `OG1r2`→3, `CR2r3b`→3, `T10a`→1, `BFIX4`→1, `` (empty)→1 | strip `a`; treat `b` as a round letter only at the very end |
| 11 | `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06` prints nothing after the eight rows are added (run in Step 4; the assertion is the silent exit) | a row without `closes_by` |

- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/80-seat-driver.bats --filter 'rung|class|fallback|ladder|key_rung'` → every new test fails; the first failure line reads `factory_route: …/routing.toml: row 1: unknown key rung` (the walker refuses the fixture's key); the cross-check row 8 shows `route.py` printing `deepseek/deepseek-v4-pro-0813 high` where `factory_route` exits 3. Paste both.
- [ ] **Step 3: Make the change** — `factory_route`: parse `--rung`/`--class`; store `cur_rung` (default `1`) and `cur_fallback`, `cur_class` (default `any`) in `_factory_route_finish_row`; specificity over four fields; the route filter only without `--rung`; the exhausted message. `factory_route_check`: a second pass over the finished rows collecting `(route, role, kind, size, class, rung, model, effort, fallback)` tuples, then the three new rules (keep the row array in a bash array of `|`-joined fields; no subshell). `factory_key_rung`. `route.py`: `CLASSES`, the `resolve` signature, `check`'s rules, `lookup`'s flags, the exit code 3. The eight rows and the header sentence; the eight claims.
- [ ] **Step 4: Run green** — `nix develop -c treefmt`; `nix develop -c ruff format tools/factory/route.py`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix develop -c python3 tools/factory/route.py check`; `nix develop -c python3 pkgs/evidence/claims.py validate docs/ledger/claims.toml --today 2026-09-06`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `… factory-unit`; `… claims-validate`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit** — the body from the script (Global Constraints), running Step 2's filter and Step 4's commands.

**Tests:** rows 1–11; the discriminating fixtures: a rung-3 row on the other route (rows 1, 4, 5), the equal-specificity `class` pair (row 2), the two-variable and zero-variable adjacent pairs (row 4), the four-key × four-rung cross-check (row 8), `T10a` against `SD1b` and `OG1r2` against `SD1r` (row 10).

**touches:** docs/ledger/routing.toml, tools/factory/seat/factory-lib.sh, tools/factory/route.py, tests/unit/80-seat-driver.bats, docs/ledger/claims.toml
**acceptance:** unit, factory-unit, claims-validate, lint
**commit subject:** `routing: the ladder — rung and fallback rows, class in the key, factory_route and route.py in lockstep, the first rungs marked unmeasured (test: unit, factory-unit, claims-validate, lint)`

### SD2 (code, S) — the technical class: task-classes.toml, one primary class per task from touches, the class in the brief and the json

**dependsOn:** none

**Files:**
- Create: `docs/ledger/task-classes.toml`, `tests/evidence/fixtures/plans/classes.md`
- Modify: `pkgs/evidence/tasks.py` (`load_task_classes`, `task_class`, the `class` field in `scan_repo`'s tasks and the `json` output, a `class` subcommand, one brief line), `tests/evidence/test_tasks.py`

**Interfaces:**

- `docs/ledger/task-classes.toml`: `[[rule]]` blocks, each `class = "<name>"` and `glob = "<fnmatch pattern>"`, in priority order (a tie goes to the earliest rule). The eleven names are the vocabulary SD1 pins: `nix-module`, `nix-check`, `bash-driver`, `python-evidence`, `js-workflow`, `bats-test`, `vm-test`, `docs-runbook`, `docs-plan`, `docs-board` (`any` is never a rule's class; it is the answer for no `touches`). First rules: `nix-module` ← `nixosModules/*`, `hosts/*`; `nix-check` ← `flake.nix`, `tests/integration/*.nix`; `vm-test` ← `tests/integration/*-vm.nix` (listed before `nix-check` so a VM file matches it first); `bash-driver` ← `tools/factory/seat/*`, `tools/*.sh`, `githooks/*`; `python-evidence` ← `pkgs/evidence/*`, `pkgs/seat/*`, `pkgs/helm/*`, `tools/ledger/*`, `tools/factory/route.py`, `tests/evidence/*`, `tests/seat/*`; `js-workflow` ← `tools/factory/*.js`, `.claude/workflows/*`, `tests/factory/*`; `bats-test` ← `tests/unit/*`; `docs-runbook` ← `docs/runbooks/*`, `CLAUDE.md`; `docs-plan` ← `docs/superpowers/*`, `docs/decisions/*`, `docs/reviews/*`, `docs/concepts/*`; `docs-board` ← `docs/OPERATIONS.md`, `docs/board/*`, `docs/ledger/*`. A `touches` entry is matched as a repo-relative path by `fnmatch.fnmatch(entry, glob)` and also against `entry + "/"`'s prefix for a directory entry (`docs/reviews` matches `docs/reviews/*`).
- `tasks.load_task_classes(root) -> list[dict]` reads `<root>/docs/ledger/task-classes.toml`; a missing file → `[]` (every class `any`); a rule whose `class` is outside the vocabulary or whose `glob` is empty → `ValueError("task-classes: rule N: …")`, which `check` reports as `tasks: task-classes.toml: …` and the brief degrades to `any`.
- `tasks.task_class(touches, rules) -> str`: for each entry the first rule that matches gives that entry's class; the task's class is the class with the most entries; a tie goes to the class of the earliest rule among the tied; no entry matched, or no `touches` → `any`.
- Every task dict from `scan_repo` gains `"class"`; `json` prints it; a new subcommand `tasks.py --root R class --plan <basename> <KEY>` prints the one word (exit 1 `tasks: unknown task <KEY> in <plan>` when absent; exit 2 on a broken rules file); `check` gains rule (g): a `task-classes.toml` error is an error. The brief gains, after `**Next wave**`, one line `**Classes (next wave):** <repo>: KEY=class KEY=class …` (only keys of the next wave; ≤ 200 chars, truncated with ` …`), so the existing `**Next wave** — …` line and its tests are untouched and the 40-line budget holds.

**Facts:**

- `grep -n 'class' pkgs/evidence/tasks.py` → nothing: no class derivation exists. `sed -n '114,160p' pkgs/evidence/tasks.py` (`parse_plan`) → the task dict's keys `key, kind, size, title, depends_on, touches, acceptance, repo, commit_subject, body, plan` and `cur["touches"] = parse_list(value)`.
- `grep -n 'Next wave\|len(md.splitlines()) <= 40' tests/evidence/test_tasks.py` → `assert "**Next wave** — nixos-agent-env: E7" in md` (line 485) and the 40-line budget assertion; `render_brief` writes the line as `lines.append("**Next wave** — " + …)`.
- `grep -n 'FIXTURES = ' tests/evidence/test_tasks.py` → `FIXTURES = HERE.parent / "fixtures" / "plans"`; `ls tests/evidence/fixtures/plans` → `legacy.md second.md typed.md`.
- `grep -n 'cp -r ${self}/docs/ledger docs/ledger' flake.nix` → both `evidence-unit` and `unit` copy the whole `docs/ledger`, so the new file reaches both sandboxes without a `flake.nix` change.
- The spec's tie fixture: `touches` under `nixosModules/` and `tests/` classify `nix-module` — with the rules above `tests/unit/x.bats` is `bats-test` and `nixosModules/x.nix` is `nix-module`, one entry each: the tie goes to the earliest rule, `nix-module` (the first block in the file).

- [ ] **Step 1: Write the failing tests** (`tests/evidence/test_tasks.py`; the fixture plan `classes.md` holds five typed tasks: `C1` touches `nixosModules/a.nix, tests/unit/a.bats` (tie → `nix-module`), `C2` touches `tests/unit/a.bats, tests/unit/b.bats, pkgs/evidence/x.py` (majority → `bats-test`), `C3` touches `tests/integration/x-vm.nix` (→ `vm-test`, not `nix-check`), `C4` (docs) with no `touches` (→ `any`), `C5` touches `docs/reviews` (a directory entry → `docs-plan`)):

| # | assertion | mutant |
|---|---|---|
| 1 | `task_class` over the five fixtures → `nix-module`, `bats-test`, `vm-test`, `any`, `docs-plan` | count the first entry only; drop the tie rule → `C1` becomes `bats-test`; reorder `nix-check` before `vm-test` → `C3` flips |
| 2 | `json` carries `"class"` for every task of the fixture repo (`repo_with(tmp_path, ["classes.md"])`) | omit the key |
| 3 | `tasks.py --root <fixture root> class --plan classes.md C2` prints `bats-test`; an unknown key exits 1 with `unknown task`; a rules file with `class = "bogus"` → `check` prints `tasks: task-classes.toml: rule 1: unknown class bogus` and `class` exits 2 | accept any name |
| 4 | the brief over the fixture prints `**Classes (next wave):** nixos-agent-env: C1=nix-module …` and the existing `**Next wave** — …` assertion still holds; a 30-key wave is truncated to ≤ 200 chars ending ` …` | drop the cap |
| 5 | the committed `docs/ledger/task-classes.toml` loads, every `class` is in the vocabulary, every glob is non-empty, and `task_class(["tools/factory/seat/factory-task"], rules)` → `bash-driver`, `task_class(["docs/ledger/routing.toml"], rules)` → `docs-board` | a committed rule with a typo |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence/test_tasks.py -q -k 'class'` → `AttributeError: module 'tasks' has no attribute 'task_class'` (paste the first line).
- [ ] **Step 3: Write** the table, the two functions, the field, the subcommand, the brief line; `nix develop -c ruff format pkgs/evidence tests/evidence`.
- [ ] **Step 4: Run green** — `nix develop -c pytest tests/evidence -q`; `git add` the new files; `python3 pkgs/evidence/repomap.py --root . write`; `nix develop -c python3 pkgs/evidence/tasks.py --root . check` (prints nothing); `nix develop -c python3 pkgs/evidence/tasks.py --root . brief | grep Classes` (paste the line); `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–5; the discriminating fixtures: the one-each tie (`C1`), the 2-vs-1 majority (`C2`), the VM file that matches two globs (`C3`), the no-`touches` docs task (`C4`), the directory entry (`C5`).

**touches:** docs/ledger/task-classes.toml, tests/evidence/fixtures/plans/classes.md, pkgs/evidence/tasks.py, tests/evidence/test_tasks.py
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the technical class — task-classes.toml, one primary class per task from touches, the class in the brief and the json (test: evidence-unit, lint)`

### SD3 (code, M) — the driver climbs: the rung from the key, --prior carries the failed attempt, class and rung in the result, a claude rung prints its launch line

**dependsOn:** SD1, SD2

**Files:**
- Modify: `tools/factory/seat/factory-task` (`--rung`, `--fallback`, `--prior`; the class query; the ladder lookup; the escalate path; the new result lines), `tools/factory/seat/factory-brief` (`FACTORY_PRIOR_BLOCK`), `tools/factory/seat/factory-lib.sh` (`factory_prior_block`), `tests/unit/80-seat-driver.bats`

**Interfaces:**

- `factory-task <run> <repo-path> <KEY> [--model ID] [--after KEY2] [--rung N] [--fallback] [--prior <run>/<KEY>]`.
  - The rung: `--rung N` (an integer 1–9, else usage exit 2) or `factory_key_rung "$key"`. The class: `class=$(factory_py "$FACTORY_TOOLBOX_REPO/pkgs/evidence/tasks.py" --root "$repo_path" class --plan "$(basename -- "$plan")" "$key" 2>>"$log")` — a non-zero exit or an empty word → `class=any` and `factory_log "class: unavailable (tasks.py class exited N); using any"`. The lookup: `route_line=$(factory_route --rung "$rung" --class "$class" implement "$kind" "$size")` — four fields `MODEL EFFORT ROUTE FALLBACK`. An explicit `--model`/`OPENROUTER_MODEL` still wins over the row (`route: explicit`); `OPENROUTER_REASONING_EFFORT` still wins over the effort.
  - `--fallback`: the row's fourth field replaces the model (same effort); a row without one → `factory_die 2 "--fallback: the rung-N row for … has no fallback"`. Recorded as `fallback: <model>` (else the line is absent).
  - Ladder exhausted (`factory_route` exit 3 with `ladder exhausted`) → `factory_die 3 "<factory_route's message>"` before any workspace or run dir is created; a table error → the existing built-in default path with its warning (unchanged).
  - Escalate: when the row's `ROUTE` is `claude` and no explicit model was given, the task is not launched. The run dir is created, `<KEY>.result` is written with `FACTORY-RESULT status=skipped`, `FACTORY-CHECKS none=not-run`, `FACTORY-COMMITS 0`, `FACTORY-NOTES escalate: claude/implement — run the launch line in the operator's Claude Code session`, the usual `run:/key:/model:/effort:/route:` lines (`route: implement/<kind>/<size>`), then `rung: N`, `class: <c>`, `escalate: claude/implement`, `launch: Workflow({ scriptPath: 'tools/factory/dark-factory.js', args: { plan: 'docs/superpowers/plans/<basename>', prefix: '<run>', scratch: '<scratch>', tasks: <tasks.py --root <repo> waves --repo <name> --plan <basename> --factory-args, filtered to this key> } })` — the `tasks` value is the JSON the graph's own `--factory-args` prints for the plan, filtered to the one key (no graph logic re-derived; `factory_py` runs it), on one line. Exit 4 (a new code: `done` 0, `partial` 1, `failed` 2, `unknown` 3, `skipped` 4). No seat runs; no workspace is created.
  - `--prior <prun>/<pkey>`: `$FACTORY_RUNS/<prun>/<pkey>.result` must be readable (`factory_die 2 "no such prior result: …"`); the block is built by `factory_prior_block <result> <repo-path> <prun> <pkey> <runs-dir>` and handed to `factory-brief` through `FACTORY_PRIOR_BLOCK`; `prior: <prun>/<pkey>` joins the result lines. A malformed value (not `<run>/<KEY>`, either part empty) → usage exit 2.
- `factory_prior_block` prints, from the `.result` and the review file only:

```
    ## Prior attempt (<prun>/<pkey>)

- result: <the FACTORY-RESULT line, verbatim>
- error_class: <the value of the `error_class:` line, or unknown when the line is absent>
- route: <route:>; model: <model:>; effort: <effort:>; rung: <rung: or 1>
- usage: <the usage: line's JSON, verbatim>
- diffstat (the rejected commit):
<the lines between `diffstat:` and the next blank line, verbatim>
- review: <path or `none found`>
<the review's H1 (the first line beginning `# Opus gate`), then every finding line — a line whose first token after optional decoration (`#`, `-`, `*`, `N.`, `N)`, `**`) is BLOCKER, MAJOR or MINOR, case-insensitive — then every table row (a line beginning `|`) containing `surviv` case-insensitive, all verbatim>
```

  (The block's first line starts at column 0 in the brief; it is indented here only so this plan's own section extractor — `factory-brief`, which ends a section at the next line beginning `## ` — reads the whole section.) The review file: the last of `<repo-path>/docs/reviews/*-opus-review-<prun>-<pkey>.md` in name order, else `<runs-dir>/<prun>/<pkey>.review.md`, else none. The block is capped at 200 lines; when cut, the last line is `… (truncated to 200 lines)`. Never a `.log`, a `.dsh-home` or a transcript.
- `factory-brief`: when `FACTORY_PRIOR_BLOCK` is non-empty it is printed after the task section and before the WORKSPACE RULES as given (the block's own `## Prior attempt` heading); the seat's WORKSPACE RULES gain one sentence: "A `## Prior attempt` section, when present, is the record of the rejected attempt this task replaces: address every finding it lists; never copy it into a project file."
- `FACTORY_SEAT_SPOOL=1` (set by `seat-run` for a drive job — SD4): `factory-task` adds `--no-start --wait` to its `seat-submit headless` invocation; unset → today's invocation.

**Facts:**

- `grep -n 'route_line=$(factory_route\|route_label="implement\|kind_size=$(factory_task_kind_size\|brief=$(FACTORY_TASK_TEXT' tools/factory/seat/factory-task` → `route_line=$(factory_route implement "$kind" "$size" || true)`, `route_label="implement/$kind/$size"`, `kind_size=$(factory_task_kind_size "$plan" "$key")`, `brief=$(FACTORY_TASK_TEXT=${FACTORY_TASK_TEXT:-} "$FACTORY_BIN/factory-brief" "$plan" "$key")`.
- `grep -n 'command -v seat-submit\|seat-submit headless\|printf .route: %s\|printf .exit_code: %s\|printf .usage: %s\|result=$runs_dir/$key.result' tools/factory/seat/factory-task` → the seat-submit branch `if command -v seat-submit >/dev/null 2>&1 && [ "${FACTORY_SEAT_UNIT:-1}" != "0" ]; then`, its `seat-submit headless \` call, and the result writer's `route:`, `exit_code:`, `usage:` lines around `result=$runs_dir/$key.result`. The exit-code table: `done) task_rc=0`, `partial) task_rc=1`, `failed) task_rc=2`, `*) … task_rc=3`.
- `grep -n 'FACTORY_BRIEF_EXTRA\|## REPO NOTES' tools/factory/seat/factory-brief` → `if [ -n "${FACTORY_BRIEF_EXTRA:-}" ]; then` and the `## REPO NOTES` heading — the pattern `FACTORY_PRIOR_BLOCK` copies (printed before the rules, not after).
- `grep -n 'error_class: %s\|plan: %s' docs/superpowers/plans/2026-09-06-telemetry-store-1.md` → T2 adds `printf 'plan: %s\n' "$plan"` after `route:` and `printf 'error_class: %s\n' "$error_class"` after `exit_code:`; SD3's lines go after `plan:` when it exists and after `route:` otherwise — the block reads `error_class:` when present and prints `unknown` when absent (T2 may land before or after SD3).
- `grep -n 'md=$runs_dir/$key.review.md' tools/factory/seat/factory-review` → the seat review's path; `ls docs/reviews | grep -c opus-review` → `164`, all named `<date>-opus-review-<run>-<KEY>.md` (T3's Facts: every name matches `^\d{4}-\d{2}-\d{2}-opus-review-(?P<run>[a-z0-9]+)-(?P<key>[A-Za-z0-9-]+)\.md$`).
- `grep -n 'const A = \|A\.plan\|A\.prefix\|A\.tasks\|Invoke' tools/factory/dark-factory.js` → `// Invoke:  Workflow({ scriptPath: 'tools/factory/dark-factory.js', args: {...} })` and `if (!A.plan || !A.prefix || !Array.isArray(A.tasks) || A.tasks.length === 0 || !A.scratch)` — the four required args the launch line carries; `sed -n '876,905p' pkgs/evidence/tasks.py` → `factory_args(repo_graph, plan)` builds the `tasks[]` JSON (`key, title, kind, checks, spec, dependsOn, touches`) that `waves --factory-args` prints.
- `sed -n '43,58p' tests/unit/80-seat-driver.bats` → `setup()` exports `FACTORY_PLAN`, `FACTORY_ROOT`, `FACTORY_RUNS` under `$BATS_TEST_TMPDIR`; the test at line 466 builds `seat_copy`, a fake `factory-ws`, a fixture toolbox and a fake `dsh-openrouter` that prints the four result lines — the idiom every new test copies; the fake-`seat-submit` idiom is at line 1118 (`The fake seat-submit records its argv, the --brief file's content …`).

- [ ] **Step 1: Write the failing tests** (`tests/unit/80-seat-driver.bats`; the fixture toolbox's `routing.toml` carries SD1's rows; `FACTORY_PYTHON3_CMD` points `factory_py` at the sandbox's `python3` so `tasks.py class` runs for real over a fixture repo with a `docs/ledger/task-classes.toml`):

| # | assertion | mutant |
|---|---|---|
| 1 | `factory-task r1 <repo> K1` (K1 `(code, S)`, touches `tools/factory/seat/x`) → the fake seat saw `--model deepseek/deepseek-v4-pro-0813` and effort `medium`; the result has `rung: 1`, `class: bash-driver`, `route: implement/code/S`, no `fallback:`/`prior:`/`escalate:` line | derive the rung from the run name; omit `class:` |
| 2 | `factory-task r1 <repo> K1b` → `rung: 2` and the fake seat saw effort `high` (the rung-2 row); `factory-task r1 <repo> K1r` → status `skipped`, exit 4, `escalate: claude/implement`, a `launch:` line containing `scriptPath: 'tools/factory/dark-factory.js'`, `prefix: 'r1'` and `"key": "K1r"`, and no fake seat ran (its marker file absent), no workspace created | launch anyway; derive rung 3 as 2 |
| 3 | `--rung 2` on `K1` → `rung: 2` and effort high; `--rung 9` → exit 3 `ladder exhausted`, no run dir; `--rung x` → exit 2 | accept the exhausted default |
| 4 | `--fallback` on a key whose rung-1 row carries `fallback = "deepseek/deepseek-v4-flash"` → the fake seat saw Flash, `fallback: deepseek/deepseek-v4-flash` in the result; on a row without → exit 2 | ignore the flag |
| 5 | the class query failing (a fixture repo without `task-classes.toml` → `tasks.py class` exits 2) → `class: any` in the result and `class: unavailable` in the log; the seat still runs | die on the failure |
| 6 | `--prior r0/K1` with a synthetic `r0/K1.result` (status failed, `error_class: provider-error`, `usage: {"input":1}`, a diffstat section of two lines) and a synthetic `docs/reviews/2026-09-06-opus-review-r0-K1.md` (an H1, `**MAJOR-1** x`, `- MINOR 2: y`, a table row `| M3 | survived |`, a body sentence mentioning "six minors" that is not line-initial) → the fake seat's brief holds `## Prior attempt (r0/K1)`, `- result: FACTORY-RESULT status=failed`, `- error_class: provider-error`, the two diffstat lines, the H1, the two finding lines, the survivor row, and not the sentence; the result has `prior: r0/K1` | drop the block → the brief assertion fails (the spec's mutant); count the inline sentence; drop the survivor filter |
| 7 | `--prior r0/K1` with no review anywhere → `- review: none found` and the block still present; a `.result` missing `error_class:` → `- error_class: unknown`; a 400-line review → the block ends `… (truncated to 200 lines)`; `--prior nonsense` → exit 2; `--prior r0/K9` (no such result) → exit 2 | cut nothing; accept a missing result |
| 8 | the fake seat's brief never contains the string `.log` from the prior run and `factory-task` never opens `r0/K1.log` (the fixture log is `chmod 000`) | read the log for the tail |
| 9 | `FACTORY_SEAT_SPOOL=1` with a fake `seat-submit` on PATH → its argv contains `--no-start` and `--wait`; unset → neither | drop the branch |
| 10 | `factory-brief` with `FACTORY_PRIOR_BLOCK` set prints it between the task section and `## WORKSPACE RULES`; unset → no `## Prior attempt` string | print it after the rules |

- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/80-seat-driver.bats --filter 'rung|prior|fallback|escalate|SPOOL|class:'` → the flags fail as `usage: factory-task …` exit 2 and the result files lack `rung:` (paste the first failure of rows 1, 2 and 6).
- [ ] **Step 3: Make the change** — the flags and their parsing; `factory_key_rung` (SD1) and the class query; the four-field route line; the escalate path with its `.result`; `factory_prior_block` in `factory-lib.sh`; `FACTORY_PRIOR_BLOCK` in `factory-brief`; the `--no-start --wait` branch; the result lines `rung:`, `class:`, `fallback:`, `prior:`, `escalate:`, `launch:` after `route:` (after `plan:` when that line exists).
- [ ] **Step 4: Run green** — `nix develop -c treefmt`; `nix develop -c shellcheck tools/factory/seat/factory-task tools/factory/seat/factory-brief tools/factory/seat/factory-lib.sh`; `nix develop -c bats tests/unit/80-seat-driver.bats`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–10; the discriminating fixtures: `K1`/`K1b`/`K1r` (the three rungs from one root), the row with and without a fallback, the review with an inline "six minors" sentence against line-initial markers, the survivor table row against other table rows, the `chmod 000` log.

**touches:** tools/factory/seat/factory-task, tools/factory/seat/factory-brief, tools/factory/seat/factory-lib.sh, tests/unit/80-seat-driver.bats
**acceptance:** unit, lint
**commit subject:** `factory: the driver climbs — the rung from the key, --prior carries the failed attempt, class and rung in the result, a claude rung prints its launch line (test: unit, lint)`

### SD4 (code, S) — the drive job: seat-submit drive resolves the orchestrate row, refuses the shared home, --wait polls a spooled job; seat-run runs drive as web

**dependsOn:** none

**Files:**
- Modify: `pkgs/seat/seat-submit.py`, `pkgs/seat/seat-run.py`, `tests/seat/test_seat_submit.py`, `tests/seat/test_seat_run.py`, `flake.nix` (`seat-unit` copies `tools/factory/route.py`)

**Interfaces:**

- `seat-submit [--jobs-dir DIR] [--no-start] [--wait] [--routing-table PATH] [--route-py PATH] {headless|web|drive} --workspace PATH --dsh-home PATH [--model ID] [--effort LEVEL] [--brief FILE] [--port N] [--timeout S]`.
  - `headless`/`web`: unchanged, except that `--model`/`--effort` are now checked as required per mode in code (still required for both), and the job directory is built under `<jobs-dir>/.tmp-<id>/` (0700) and renamed to `<jobs-dir>/<id>` with `os.rename` once `job.json` (and `brief.txt`) are written — the directory appears whole (D7).
  - `drive`: `--model`/`--effort` given → stderr `seat-submit: drive takes its model and effort from the routing table` exit 2; `--port` required (exit 2 without it; an integer). The row: `sys.path.insert(0, dirname(route_py))`, `import route`, `rows = route.load_rows(table)`, `model, effort = route.resolve(rows, "openrouter", "orchestrate", "any", "any")[:2]` where `table = --routing-table` or `$FACTORY_ROUTING_TABLE` or `~/nixos-agent-env/docs/ledger/routing.toml`, and `route_py = --route-py` or `<table's repo root>/tools/factory/route.py` (the repo root is the table path with `/docs/ledger/routing.toml` removed). A missing `route.py` → exit 2 `seat-submit: no route.py at …`; `route.SchemaError`/`route.RowError` → exit 2 with the message. `job.json` gains `"route": "openrouter/orchestrate/any/any"` (`headless`/`web` write `"route": null`). The payload check: `os.path.realpath(dsh_home) == os.path.realpath(os.path.expanduser("~/.local/share/dsh-openrouter"))` → exit 2 `seat-submit: drive never runs on the operator's shared home (decision 2026-09-05 addendum, point 1)`; each of `skills/driving/SKILL.md`, `skills/planning/SKILL.md`, `AGENTS.md` under `dsh_home` must be a regular file after following symlinks (`os.path.isfile`) → else exit 2 `seat-submit: drive home lacks <path>`. `drive` starts the unit like `web` and returns 0 (no polling).
  - `--wait`: allowed with `headless` only (else exit 2 `--wait is for headless jobs`); with `--no-start` it polls `result.txt` exactly as the start path does, then streams `stdout.txt` and exits with `exit_code.txt`; on timeout it prints `seat-submit: timed out waiting for <result.txt>` and returns 124 **without** calling `systemctl` (there is no unit to stop from this side — the spool's unit is the operator's to stop). `--wait` without `--no-start` is accepted and changes nothing.
  - Whoever starts: after its own `systemctl start`, `seat-submit` writes `<id>/started` (`by=seat-submit <ISO ts>`, mode 0600) so the spool skips the job (SD5 reads it).
- `seat-run`: the `web` branch becomes `else:  # web or drive` and, for `mode == "drive"`, exports `FACTORY_SEAT_SPOOL=1` before the harness runs (the driver scripts inside read it — SD3). `url.txt` and the printed URL as for web.
- Error contract unchanged elsewhere: exit 2 on a bad workspace/brief/job dir, 124 on timeout, the unit's exit code otherwise.

**Facts:**

- `grep -n 'choices=\["headless", "web"\]\|--no-start\|--model", required=True\|--effort", required=True\|systemctl", "start"\|if args.no_start\|"mode": args.mode\|return 124' pkgs/seat/seat-submit.py` → `p.add_argument("mode", choices=["headless", "web"])`, `p.add_argument("--no-start", action="store_true")`, `--model`/`--effort` `required=True`, `subprocess.run(["systemctl", "start", f"seat@{job_id}"], check=False)`, `if args.no_start:` (returns 0 before the start), the job dict starting `"mode": args.mode,`, `return 124`.
- `grep -n 'job\["mode"\] == "headless"\|else:  # web\|os.environ\["DSH_HOME"\]\|runbook docs/runbooks/seat.md' pkgs/seat/seat-run.py` → the two-branch `if job["mode"] == "headless": … else:  # web`, `os.environ["DSH_HOME"] = job["dsh_home"]`, and a comment naming `docs/runbooks/seat.md` (a file that does not exist: `ls docs/runbooks` → no `seat.md`; SB5, held, creates it).
- `grep -n 'assert job == {\|def test_' tests/seat/test_seat_submit.py` → the byte-exact `job.json` assertion (`"mode","workspace","dsh_home","model","effort","brief","port"` plus `submitted`) that gains `"route": None`; the eight existing tests, driven in-process with `subprocess.run` monkeypatched (`_no_systemctl` records argv) — the idiom the new tests copy.
- `grep -n 'exec python3' pkgs/seat/default.nix` → `exec python3 ${./seat-submit.py} "$@"` — the package runs the file by path; `route.py` is imported from the checkout at run time, like the routing table itself (the unit's `FACTORY_ROUTING_TABLE = "/home/dalhaka/nixos-agent-env/docs/ledger/routing.toml"`, `grep -n FACTORY_ROUTING_TABLE nixosModules/seatLane.nix`).
- `grep -n 'cp -r ${self}/pkgs/seat pkgs/seat\|cp -r ${self}/tests/seat tests/seat' flake.nix` → the `seat-unit` sandbox holds only those two trees; the test's `--route-py <repo>/tools/factory/route.py` needs one more `cp`.
- `grep -n 'saved selection' docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md` → "Nothing automated changes the operator's saved selection: per-task homes no longer inherit it (P0, 2026-09-05)" — the rule the shared-home refusal enforces.
- `grep -n 'warn_missing_payload "$DSH_HOME' pkgs/dsh-openrouter/dsh-openrouter.sh` → the wrapper warns (never refuses) on a missing `skills/` or `AGENTS.md`; the drive mode refuses, because a driver without its skill set is exactly the seat the spec says must not run.

- [ ] **Step 1: Write the failing tests** (`tests/seat/test_seat_submit.py`, in-process as the file does; a fixture routing table under `tmp_path` with an `openrouter/orchestrate` row and the two defaults; `--route-py` pointing at `HERE.parents[2] / "tools" / "factory" / "route.py"`; a drive home built under `tmp_path` with the three payload files):

| # | assertion | mutant |
|---|---|---|
| 1 | `drive --no-start --port 43210` with a valid home → `job.json` `mode == "drive"`, `model == "deepseek/deepseek-v4-pro-0813"`, `effort == "medium"` (the fixture row), `route == "openrouter/orchestrate/any/any"`, `port == 43210`, `brief is None`; the id printed; no `systemctl` call | fall back to the openrouter default row silently (the fixture's default row carries a different effort, `low`, so the assertion discriminates) |
| 2 | the fixture table without an orchestrate row → the default row's values (`low`) — the resolve rule, not a hard-coded pair | hard-code Pro medium |
| 3 | `drive --model x` → exit 2 `takes its model and effort`; `drive` without `--port` → exit 2; `--route-py /nonexistent` → exit 2 `no route.py`; a table with a malformed row → exit 2 and the message | accept `--model` |
| 4 | a home whose realpath is `~/.local/share/dsh-openrouter` (monkeypatch `HOME` to `tmp_path` and create it) → exit 2 `never runs on the operator's shared home`; a symlink to it → the same | compare the strings, not the realpaths |
| 5 | a home missing `skills/driving/SKILL.md` → exit 2 naming it; `AGENTS.md` as a dangling symlink → exit 2; the three present as symlinks to real files → accepted | check with `os.path.exists` (a dangling symlink passes) |
| 6 | `headless --no-start --wait` with the poll patched to populate `result.txt`/`stdout.txt`/`exit_code.txt` → the stdout is streamed, the exit code propagated, and `_no_systemctl == []` | call `systemctl start` anyway |
| 7 | `headless --no-start --wait --timeout 1` with nothing arriving → 124, `timed out`, and `_no_systemctl == []` (no `stop`) | stop the unit |
| 8 | `--wait` with `web` or `drive` → exit 2 | accept |
| 9 | after the start path, `<id>/started` exists with `by=seat-submit`; under `--no-start` it does not exist | write it under `--no-start` |
| 10 | the job directory is renamed whole: `os.rename` is monkeypatched to record its source and destination — the source is `<jobs>/.tmp-<id>`, the destination `<jobs>/<id>`, and `job.json` already exists in the source at rename time (the recorder checks) | write into the final path directly |
| 11 | `test_seat_run.py`: a `drive` job runs the same argv as `web` (`--broker --bind-namespace <ns> -- --no-open --port <port>`), writes `url.txt`, and the fake harness sees `FACTORY_SEAT_SPOOL=1` in its environment; a `web` job does not | export it for web too |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/seat -q -k 'drive or wait or started or rename'` → `SystemExit: 2` from argparse on `drive` (`invalid choice: 'drive'`); paste the first line.
- [ ] **Step 3: Make the change**; add `cp ${self}/tools/factory/route.py tools/factory/route.py` (with `mkdir -p tools/factory`) to `seat-unit`; `nix develop -c ruff format pkgs/seat tests/seat`.
- [ ] **Step 4: Run green** — `nix develop -c pytest tests/seat -q`; `nix build .#checks.x86_64-linux.seat-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–11; the discriminating fixtures: a default row whose effort differs from the orchestrate row (rows 1–2), the realpath-equal symlinked home (row 4), the dangling symlink (row 5), the recorder on `os.rename` (row 10).

**touches:** pkgs/seat/seat-submit.py, pkgs/seat/seat-run.py, tests/seat/test_seat_submit.py, tests/seat/test_seat_run.py, flake.nix
**acceptance:** seat-unit, lint
**commit subject:** `seat: the drive job — seat-submit drive resolves the orchestrate row, refuses the shared home, --wait polls a spooled job; seat-run runs drive as web (test: seat-unit, lint)`

### SD5 (code, M) — the spool: seat-spool.path starts one seat@ per validated job, the drive job on the unit, the unit PATH for the driving verbs, asserted in seat-eval and seat-vm

**dependsOn:** SD4

**Files:**
- Create: `pkgs/seat/seat-spool.py`, `tests/seat/test_seat_spool.py`
- Modify: `pkgs/seat/default.nix` (`seat-spool`), `nixosModules/seatLane.nix` (the path and service units; the `seat@` PATH and `XDG_CACHE_HOME`; two tmpfiles rules), `flake.nix` (`seat-eval` assertions; `seatSpool` passed to `seat-vm`), `tests/integration/seat-vm.nix`

**Interfaces:**

- `seat-spool [--jobs-dir DIR] [--port-range A-B] [--systemctl CMD]` (stdlib; `--jobs-dir` default `/var/lib/seat/jobs`; `--port-range` default `43200-43299`; `--systemctl` default `systemctl`, tests pass a recorder). One pass, exit 0 always except an unusable jobs dir (exit 2). For every entry of the jobs dir whose name matches `^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$` (others — `.tmp-*` included — are skipped silently): skip when `started` or `exit_code.txt` exists in it; skip when `job.json` is absent (logged `spool: <id>: no job.json yet`); otherwise validate `job.json`: a JSON object whose keys are exactly `mode, workspace, dsh_home, model, effort, brief, port, submitted, route`; `mode ∈ {headless, web, drive}`; `workspace` and `dsh_home` absolute paths that are directories; `model` matches `^[A-Za-z0-9._:/-]+$`; `effort ∈ {off, low, medium, high, xhigh}`; `brief` is `null` or `"brief.txt"` with that file present; `port` is `null` for `headless` and an integer within the range for `web`/`drive`; `submitted` parses with `datetime.fromisoformat`; `route` is `null` or a string. Valid → write `started` (`by=seat-spool <ISO ts>`, mode 0644 — the one write the spool makes, so a job is never started twice) then `run([systemctl, "start", "--no-block", f"seat@{id}"], check=False)` and log `spool: <id>: started`. Invalid → write `refused` (one reason per line, 0644) and log `spool: <id>: refused: <first reason>`; never a start. Every reason is one of the fixed strings `keys: unexpected <k>` / `keys: missing <k>` / `mode: not in headless|web|drive` / `workspace: not a directory` / `dsh_home: not a directory` / `model: bad id` / `effort: not in enum` / `brief: <reason>` / `port: <reason>` / `submitted: not a timestamp` / `route: not a string`.
- `nixosModules/seatLane.nix` gains: `systemd.paths.seat-spool = { wantedBy = [ "multi-user.target" ]; pathConfig = { PathChanged = "/var/lib/seat/jobs"; Unit = "seat-spool.service"; }; }` and `systemd.services.seat-spool = { description = "start one seat@ unit per validated job in /var/lib/seat/jobs"; serviceConfig = { Type = "oneshot"; ExecStart = "${seatSpool}/bin/seat-spool --jobs-dir /var/lib/seat/jobs --port-range ${cfg.webPortRange}"; }; }` — root, no shell, one store path. The `seat@` unit: `path` becomes `[ cfg.harnessPackage pkgs.iproute2 seatTools.seat-submit pkgs.bash pkgs.coreutils pkgs.findutils pkgs.gnugrep pkgs.gnused pkgs.gawk pkgs.util-linux pkgs.procps pkgs.git pkgs.nix pkgs.zstd ]` (D8; `seatTools` is the `pkgs/seat` attrset the module already calls); `environment.XDG_CACHE_HOME = "/var/lib/seat/cache"`; `systemd.tmpfiles.rules` gains `"d /var/lib/seat/cache 0700 ${cfg.operatorUser} -"`. `ReadWritePaths`, `InaccessiblePaths`, `NoNewPrivileges`, `ProtectSystem`, `NetworkNamespacePath` and every other option are unchanged.
- `flake.nix` `seat-eval` gains: `c.systemd.paths.seat-spool.pathConfig.PathChanged == "/var/lib/seat/jobs"` and `.Unit == "seat-spool.service"`; the service's `ExecStart` matches `^/nix/store/[^ ]*/bin/seat-spool --jobs-dir /var/lib/seat/jobs --port-range 43200-43299$` (one string: no `sh`, no `bash`, no second command), `Type == "oneshot"`, no `User` set; `sc.ReadWritePaths == [ "/var/lib/seat" "-/home/dalhaka/factory" "-/home/dalhaka/nixos-agent-env" "-/home/dalhaka/flakes" "-/home/dalhaka/.local/share/dsh-openrouter" ]` (the literal list — the drive job inherits it unchanged); the unit's `path` renders every package of D8's list (`lib.all (p: lib.elem p unit.path) [ … ]`) and `unit.environment.XDG_CACHE_HOME == "/var/lib/seat/cache"`; `lib.elem "d /var/lib/seat/cache 0700 dalhaka -" c.systemd.tmpfiles.rules`.
- `tests/integration/seat-vm.nix`: `seatSpool` becomes an argument (`flake.nix` passes `seatTools.seat-spool`); the fixture's `serviceConfig.ReadWritePaths = [ "/tmp" ]` goes and the fixtures move to `/var/lib/seat/ws`, `/var/lib/seat/dsh` and `/var/lib/seat/brief` (the operator-owned tree the unit may write — D8: the production sandbox is what runs); the drive home fixture holds `skills/driving/SKILL.md`, `skills/planning/SKILL.md`, `AGENTS.md`. New steps: (8) `su - dalhaka -c 'seat-submit drive --workspace /var/lib/seat/ws --dsh-home /var/lib/seat/dsh --routing-table /var/lib/seat/routing.toml --route-py /var/lib/seat/route.py --port 43202'` (a fixture table with the orchestrate row and `route.py` copied in) → `url.txt` reads `http://10.100.4.2:43202` and the host reaches it; `jq -r .route /var/lib/seat/jobs/<id>/job.json` → `openrouter/orchestrate/any/any`; `systemctl show seat@<id> -p Environment --value` contains `XDG_CACHE_HOME=/var/lib/seat/cache` and, after the job, `ls /var/lib/seat/cache | wc -l` ≥ 1 (`FACTORY_SEAT_SPOOL` is set by `seat-run` in the harness's own environment, not the unit's, so it is not visible here — SD4's unit test pins it); (9) from inside a running job's user and mount view (`systemd-run -P --wait --uid=dalhaka --property=NetworkNamespacePath=/run/netns/egress-seat -p ProtectSystem=strict -p ReadWritePaths=/var/lib/seat seat-submit headless --no-start --wait --timeout 120 --workspace /var/lib/seat/ws --dsh-home /var/lib/seat/dsh --model deepseek/deepseek-v4-flash --effort off --brief /var/lib/seat/brief` — the unit's own sandbox options on a transient unit, since `systemctl` is unreachable from inside the seat by design) → exit 0, the printed output holds `vm-seat-answer`, `/var/lib/seat/jobs/<id>/started` reads `by=seat-spool`, `systemctl show seat-spool.service -p Result --value` is `success`, and the fake upstream's log gained a `Bearer sk-or-vm-fixture` line; (10) a job directory written by hand with `"mode": "drive", "port": 1` → within 10 s `refused` exists with `port: outside 43200-43299` and `systemctl list-units 'seat@*' --all` does not list it; a directory named `.tmp-x` with a valid `job.json` is never started; (11) the existing web step's assertions on `ss -ltn` and the probe namespace are unchanged.

**Facts:**

- `grep -n 'systemd.services."seat@" = {\|ExecStart = "${seatRun}/bin/seat-run %i"\|ReadWritePaths = \[\|path = \[\|cfg.harnessPackage\|pkgs.iproute2\|d /var/lib/seat/jobs\|ProtectSystem\|NetworkNamespacePath' nixosModules/seatLane.nix` → the template unit, `ExecStart = "${seatRun}/bin/seat-run %i";`, the five-entry `ReadWritePaths`, `path = [ cfg.harnessPackage pkgs.iproute2 ]`, `"d /var/lib/seat/jobs 0700 ${cfg.operatorUser} -"`, `ProtectSystem = "strict";`, `NetworkNamespacePath = netnsPath;`. `grep -rn 'systemd.paths\|PathChanged' nixosModules hosts` → nothing: no path unit exists in the tree yet.
- `grep -n 'cache_root=\|export XDG_CACHE_HOME=\|mkdir -p -- "$XDG_CACHE_HOME"' pkgs/dsh-openrouter/dsh-openrouter.sh` → `cache_root=${DSH_CACHE_ROOT:-/tmp}`, `export XDG_CACHE_HOME=${XDG_CACHE_HOME:-$cache_root/dsh-openrouter-cache-$(id -u)}`, `mkdir -p -- "$XDG_CACHE_HOME"` (the wrapper runs under `writeShellApplication`'s errexit); `grep -n 'serviceConfig.ReadWritePaths = \[ "/tmp" \]' tests/integration/seat-vm.nix` → the VM's fixture admits `/tmp` with the comment "ProtectSystem=strict makes /tmp read-only for the seat unit … The harness writes its DSH_HOME (/tmp/dsh) and its nix fetcher cache (XDG_CACHE_HOME under /tmp) on every launch". On core nothing admits `/tmp`: D8's prediction, measured by this task's VM.
- `grep -n 'unit = c.systemd.services."seat@"\|/bin/seat-run %i\|seat-eval-ok' flake.nix` → `seat-eval` asserts on the real `core` config and pins `ExecStart` by infix; `grep -n 'seatSubmit = seatTools.seat-submit' flake.nix` → the VM already takes the seat tools attrset's members as arguments.
- `grep -n 'su - dalhaka -c .seat-submit headless\|su - dalhaka -c .seat-submit web\|url.txt\|grep -rq sk-or-vm-fixture /var/lib/seat/jobs' tests/integration/seat-vm.nix` → the two existing submissions, the `url.txt` wait, and the negative `grep` over the jobs tree that every new fixture file must keep passing (no fixture may contain the key string).
- `grep -n 'current-system' nixosModules/modelLane.nix` → `"/run/current-system/sw"` on the lane's PATH: the precedent for a unit that shells out to profile binaries.
- `grep -n 'operatorUser = ' hosts/core/seat.nix` → `dalhaka`; `grep -n 'python3Minimal' flake.nix` → `host-core` asserts the dsh guard's interpreter only; `pkgs/seat` takes `python3` from `callPackage` (`sed -n '1,4p' pkgs/seat/default.nix`), so `seat-spool` adds no interpreter to the closure.

- [ ] **Step 1: Write the failing tests** — `tests/seat/test_seat_spool.py` (in-process, `--jobs-dir tmp_path`, `--systemctl` a recorder script or `subprocess.run` monkeypatched as `test_seat_submit.py` does):

| # | assertion | mutant |
|---|---|---|
| 1 | a valid headless job dir (from `seat-submit --no-start`'s own writer, imported by path, so the shape stays one) → one `["systemctl","start","--no-block","seat@<id>"]` call, `started` reads `by=seat-spool`, log `started` | start without `--no-block`; skip the marker |
| 2 | the same dir on a second pass → no call (the marker); a dir with `exit_code.txt` and no marker → no call; a dir with `started` by `seat-submit` → no call | ignore the marker |
| 3 | one job per reason: an extra key, a missing key, `mode: "batch"`, a relative `workspace`, a `dsh_home` that is a file, `model: "a b"`, `effort: "max"`, `brief: "brief.txt"` without the file, `brief: "x.txt"`, `port: 43199`, `port: 43300`, `port: null` on `web`, `port: 43201` on `headless`, `submitted: "yesterday"`, `route: 3` → each refused with its fixed string, `refused` written, no call | drop any one rule |
| 4 | names: `.tmp-20260906-101010-abcdef`, `20260906-101010-ABCDEF`, `README` → skipped silently, never started; a valid-name dir without `job.json` → logged `no job.json yet`, no marker, no `refused` | start `.tmp-` dirs |
| 5 | three valid jobs → three starts in name order; one refused among them → the other two start (a bad job never blocks the rest); exit 0 | stop at the first refusal |
| 6 | `--jobs-dir /nonexistent` → exit 2 and nothing else | exit 0 |
| 7 | the range: `--port-range 1-2` makes `port: 43201` refused with `outside 1-2` | ignore the flag |

- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/seat/test_seat_spool.py -q` → `FileNotFoundError` for `pkgs/seat/seat-spool.py` in the loader (paste); `nix build .#checks.x86_64-linux.seat-eval -L --no-link` after adding the assertions and before the module change → `seat-eval: seat-spool.path must watch /var/lib/seat/jobs` (paste the message).
- [ ] **Step 3: Make the change** — `seat-spool.py`; `default.nix`'s third `writeShellApplication`; the module's units, PATH, cache and tmpfiles; the `seat-eval` assertions; the VM's fixtures and steps 8–11.
- [ ] **Step 4: Run green** — `nix develop -c ruff format pkgs/seat tests/seat`; `nix develop -c treefmt`; `nix develop -c pytest tests/seat -q`; `git add` the new files; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.seat-unit -L --no-link`; `… seat-eval`; `… seat-assertion-negative`; `… host-core`; `… seat-vm` (minutes; the VM proves the spool, the drive job and the production sandbox); `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–7, the `seat-eval` assertions (mutants: `PathChanged` → `PathModified`; a `bash -c` in `ExecStart`; a sixth `ReadWritePaths` entry; a dropped package → each assertion names the failing option), the VM steps 8–10 (mutants: `--no-block` dropped → step 9's transient unit blocks; the range check dropped → step 10 starts a unit; `/tmp` admitted again → step 8's cache assertion finds nothing under `/var/lib/seat/cache`).

**touches:** pkgs/seat/seat-spool.py, tests/seat/test_seat_spool.py, pkgs/seat/default.nix, nixosModules/seatLane.nix, flake.nix, tests/integration/seat-vm.nix
**acceptance:** seat-unit, seat-eval, seat-vm, host-core, lint
**commit subject:** `seat: the spool — seat-spool.path starts one seat@ per validated job, the drive job on the unit, the unit PATH for the driving verbs, asserted in seat-eval and seat-vm (test: seat-unit, seat-eval, seat-vm, host-core, lint)`

### SD6 (code, M) — one rule file: docs/ledger/guard-rules.toml holds the protected paths, the verb families and the history rules; the orchestrator guard reads it

**dependsOn:** none

**Files:**
- Create: `docs/ledger/guard-rules.toml`, `tests/unit/93-guard-rules.bats`
- Modify: `tools/orchestrator-guard.sh` (`load_rules`, the arrays and the verb-family arms read the file), `tests/unit/91-orchestrator-guard.bats` (the sweep test passes the rules path explicitly), `githooks/pre-commit` and `flake.nix` (`lint` validates the rule file with one line in each: `bash tools/orchestrator-guard.sh --check-rules` — no new tool)

**Interfaces:**

- `docs/ledger/guard-rules.toml` — only `[[table]]` blocks whose lines are `key = "value"` (a shape both a pure-bash line walk and `tomllib` read; no arrays, no inline tables, `#` comments allowed). Four tables:
  - `[[protected]]`: `path`, `kind ∈ {absolute, dir, file, home}`. `absolute` — an absolute prefix (edit/write refused under it; the delete family refuses it as an operand): the six of hook-guard's `PROTECTED_ABSOLUTE`. `dir` — a project-relative directory whose members and itself are protected for the delete family and for plan writes (`docs/superpowers/plans`). `file` — a project-relative file whose parent and every ancestor name it for the delete family (`.claude/ritual-override`). `home` — a `$HOME`-relative prefix (`.claude`, `.config/openrouter`, `strategy`; hook-guard's three).
  - `[[verb]]`: `word`, `family ∈ {delete, inplace, copy, extract, cpio-extract, find, xargs, truncate, chmod, shred}` — the families `bash_verdict`'s `case` arms distinguish today (`rm | mv | rsync | shred | rmdir` are `delete`; `cp | install | ln | dd` `copy`; `sed -i`/`perl -i` `inplace`; `tar`/`unzip` `extract`; `cpio` `cpio-extract`; `find` with `-delete`/`-exec` `find`; `xargs` `xargs`; `truncate`; `chmod | chown | chattr` `chmod`; `tee` and `>` redirects stay code — they are operators, not words).
  - `[[git]]`: `subcommand`, `flag` (may be empty), `reason` — `commit --amend`, `push`, `rebase`, `reset --hard` with the reasons the guard prints today (`git commit --amend is refused (history rules of the house)` and the three siblings), plus `clean -f`, `stash -u`, `stash -a`, `checkout --`, `restore --` as the flag-gated rows the header describes.
  - `[[host]]`: `rule ∈ {sudo, nixos-rebuild, systemctl, helm-control, key-file}`, `reason` — the five command-position rules both guards share word for word; the regexes stay code in each guard, the file declares that the rule exists and its reason string, so a reason edit is one diff.
- `tools/orchestrator-guard.sh`: `load_rules FILE` — a pure-bash walk (the `[[…]]` header opens a block, `key = "value"` fills it, anything else is malformed) filling `PROTECTED`, `PROTECTED_PATHS` (`path|kind` for `dir`/`file` as today), a new `PROTECTED_HOME`, associative arrays `VERB_FAMILY[word]=family`, and the git and host rows. The file: `${ORCHESTRATOR_GUARD_RULES:-$(dirname -- "$(realpath -- "$0")")/../docs/ledger/guard-rules.toml}`. A missing, unreadable or malformed file (an unknown table, key, kind, family or rule; a duplicate word) → `deny` with reason `guard rules unreadable: <file>: <reason>` on every Bash, Edit, Write and MultiEdit payload, before any other rule (fail closed — CR2r3b's contract: a fault denies). `bash_verdict`'s verb arms consult `VERB_FAMILY` instead of literal words; the literal arrays go. New flag `--check-rules [FILE]`: loads the file, prints nothing and exits 0, or prints the reason and exits 1 — the lint's line (`bash tools/orchestrator-guard.sh --check-rules` in `flake.nix`'s `lint` and in `githooks/pre-commit`, beside the `js-lint.sh` pair, on its own line).
- `tests/unit/93-guard-rules.bats`: the rule-file tests; `91-orchestrator-guard.bats` gains `ORCHESTRATOR_GUARD_RULES` pointing at the checkout's file in `run_guard` so the sandbox (which copies `docs/ledger`) resolves it.

**Facts:**

- `grep -c '^[a-z_][a-z_0-9]*() {' tools/orchestrator-guard.sh` → `24`; the names: `deny warn _guard_trap normalise_command pad_operators tokenise _ctx_emit tokenise_ctx git_verdict json_string json_unescape headings apply_edit bash_verdict lex_norm canon_path is_plan_file_canon is_protected_dir_or_ancestor resolve_path is_plan_file write_verdict multiedit_after missing_headings main`.
- `sed -n '141,163p' tools/orchestrator-guard.sh` → `PROTECTED=(` the six absolute prefixes ("kept identical to the wrapper and lane-submit via tests/lane/test_forbidden_lists_agree.py") and `PROTECTED_PATHS=(` `'docs/superpowers/plans|dir'`, `'.claude/ritual-override|file'`.
- `grep -n 'rm | mv | rsync | shred | rmdir)\|truncate)\|-delete | -exec)' tools/orchestrator-guard.sh` → the verb families are `case` arms inside `bash_verdict` (lines 961, 989, 770), not data; `grep -n '--amend\|push | rebase)\|--hard' tools/orchestrator-guard.sh` → `_ret='git commit --amend is refused (history rules of the house)'`, `push | rebase)`, `_ret='git reset --hard is refused (history rules of the house)'`.
- `sed -n '1,80p' tools/orchestrator-guard.sh` → the header's four rules and the "no command position" contract; rule 4 reads "The host rules from pkgs/dsh-openrouter/hook-guard.py (same wording)".
- `head -1 tests/unit/91-orchestrator-guard-sweep.txt` → `# rows: 442`; `sed -n '1405,1437p' tests/unit/91-orchestrator-guard.bats` → the sweep test asserts only that every row is stderr-silent and the count matches the header (no verdict oracle); `run_guard() { run --separate-stderr env CLAUDE_PROJECT_DIR="$PROJECT" bash "$GUARD" <<<"$1"; }`.
- `grep -n 'cp ${self}/tools/orchestrator-guard.sh\|cp -r ${self}/docs/ledger docs/ledger' flake.nix` → the `unit` sandbox holds the guard at `tools/orchestrator-guard.sh` and `docs/ledger/` beside it, so `<dir of $0>/../docs/ledger/guard-rules.toml` resolves there too.
- `grep -n 'bash tests/lint/js-lint.sh' flake.nix githooks/pre-commit` → the two-line self-test/sweep pair in both gates, the place the `--check-rules` line joins.

- [ ] **Step 1: Write the failing tests** — `tests/unit/93-guard-rules.bats` (the guard run as `run_guard` does, `ORCHESTRATOR_GUARD_RULES` pointing at a copy of the file under `$BATS_TEST_TMPDIR` the test edits):

| # | assertion | mutant |
|---|---|---|
| 1 | `bash tools/orchestrator-guard.sh --check-rules` on the committed file exits 0 silently; on a copy with `kind = "dirr"` → exit 1 `unknown kind`; with a second `[[verb]] word = "rm"` → `duplicate word rm`; with an array line `x = [1]` → `malformed line` | accept unknown kinds; keep last-wins |
| 2 | with `ORCHESTRATOR_GUARD_RULES=/nonexistent` every payload (`echo a`, an Edit of `README.md`) is denied with `guard rules unreadable` | allow on a missing file |
| 3 | the rule file is load-bearing: a copy without the `rm` verb row makes `rm -rf .claude` **allow** (the same guard denies it with the committed file); a copy without the `docs/superpowers/plans` protected row makes `rm -rf docs/superpowers/plans/*` allow; a copy without the `commit --amend` git row makes `git commit --amend` allow | keep the literal arrays beside the file |
| 4 | the `home` rows: an Edit of `$HOME/.claude/x` is denied under the committed file and allowed under a copy without the `.claude` home row (the orchestrator guard gains hook-guard's three `$HOME` prefixes — a new deny for the orchestrator, listed in the A14 table) | drop the `home` kind |
| 5 | every `[[host]]` reason string in the file equals the string the guard prints for that rule (`sudo x` → the file's `sudo` reason) | print a literal |
| 6 | `91-orchestrator-guard.bats` stays green whole (`nix develop -c bats tests/unit/91-orchestrator-guard.bats`) — the 442-row sweep stays stderr-silent and every existing verdict holds | any regression |
| 7 | the committed file's `absolute` rows equal hook-guard.py's `PROTECTED_ABSOLUTE` (parsed with `python3 -c 'import tomllib …'` in the test and compared as sets) — the three-way agreement `tests/lane/test_forbidden_lists_agree.py` proves gains a fourth party | a seventh prefix in one place |

- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/93-guard-rules.bats` → `--check-rules` is an unknown flag today (the guard reads stdin and prints nothing; the test's exit-1 assertions fail) and row 3's "allow under a copy" fails because the arrays are literal (paste the first two failures).
- [ ] **Step 3: Make the change** — the file (every current literal moved verbatim; the header comment names this plan and the readers); `load_rules`, `--check-rules`, the array and arm rewrites; the lint lines; `run_guard`'s env.
- [ ] **Step 4: Run green** — `nix develop -c treefmt`; `nix develop -c shellcheck tools/orchestrator-guard.sh`; `nix develop -c bats tests/unit/91-orchestrator-guard.bats tests/unit/93-guard-rules.bats`; `bash tools/orchestrator-guard.sh --check-rules`; `git add` the new files; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–7; the discriminating fixtures: the file minus one row per table (row 3), the `$HOME` edit (row 4), the malformed array line (row 1).

**touches:** docs/ledger/guard-rules.toml, tests/unit/93-guard-rules.bats, tools/orchestrator-guard.sh, tests/unit/91-orchestrator-guard.bats, githooks/pre-commit, flake.nix
**acceptance:** unit, lint
**commit subject:** `guard: one rule file — docs/ledger/guard-rules.toml holds the protected paths, the verb families and the history rules; the orchestrator guard reads it (test: unit, lint)`

### SD7 (code, M) — hook-guard reads the shared rule file: the token-scan arm, parity with the orchestrator guard over the sweep fixture

**dependsOn:** SD6

**Files:**
- Create: `tests/unit/94-guard-parity.bats`
- Modify: `pkgs/dsh-openrouter/hook-guard.py`, `pkgs/dsh-openrouter/dsh-openrouter.sh` (`--guard-rules` in the hook command), `tests/unit/70-dsh-openrouter.bats`, `tests/lane/test_forbidden_lists_agree.py` (hook-guard's list now comes from the file)

**Interfaces:**

- `hook-guard [--routing-table PATH] [--guard-rules PATH]`; the wrapper passes both: `guard_rules=${FACTORY_GUARD_RULES:-$HOME/nixos-agent-env/docs/ledger/guard-rules.toml}` built into `hook_command` with the same `jq -n --arg` shape. Driven bare, the guard falls back to `$FACTORY_GUARD_RULES` then that default (the `_routing_table_path` pattern).
- `_load_rules(path) -> dict | None`: `tomllib.load`; the same validity rules as SD6's `--check-rules` (an unknown table/key/kind/family/rule or a duplicate word → invalid). `None` or invalid → every `bash`, `edit`, `write` payload is denied with `guard rules unreadable at <path>` (fail closed; the sub-agent tools keep the model rule only). `PROTECTED_ABSOLUTE` and the three `$HOME` prefixes are read from the file (`absolute` and `home` rows); the module constant goes; `test_forbidden_lists_agree.py` reads the file with `tomllib` in hook-guard's place.
- The bash arm gains, after `_bash_verdict` and before `_bash_model_verdict`, `_token_verdict(command, rules, project_dir)`: a port of the orchestrator guard's Bash rules 2, 3 and 4 with the reference functions named — `normalise_command` (fold `\`-newline, tabs, newlines; strip `"`, `'`, backtick to nothing), `pad_operators` (`;`, `|`, `(`, `)`, `{`, `}`, `&`, `&&`→`&`, `||`→`|`, `>`/`>>`/`>|`→`>`), `tokenise`/`tokenise_ctx` (every token; `cd`/`pushd` bases, `env -C`, `tar -C` change the resolution base for what follows), `lex_norm`/`canon_path`/`resolve_path` (collapse `~`, `.`, `..`, `//`; join a relative token onto the cwd or the `cd` base; `os.path.realpath` once per symlink token), `is_plan_file`/`is_protected_dir_or_ancestor` (a token that is a protected `dir` or `file`, a member of a `dir`, an ancestor of a `file` for the delete family, a glob token under a protected directory), `git_verdict` (the `[[git]]` rows over every `git` token's following tokens; `-m "…"` prose never scanned), and the verb families of `bash_verdict` (`delete` denies on any protected operand; `copy` only on a protected destination — the last operand or `of=`; `inplace`, `extract`, `cpio-extract`, `find` with `-delete`/`-exec`, `xargs` carrying a delete verb, `truncate`, `chmod`, `shred`; `dd of=`; a `>` redirect onto a protected path; the python/perl removal spellings `os.remove`, `os.rename`, `os.unlink`, `pathlib…unlink`, `shutil.rmtree`, `shutil.move`, `unlink`, `open(…,"w")` naming a protected path as a string token). No command position: every token is scanned. Deny reasons are the orchestrator guard's own strings, so an operator reads one vocabulary from `dsh-openrouter --denials`.
- The edit/write arm: a path under a protected `dir` or equal to a protected `file` (after `_resolve`) is denied — `refusing to edit/write <path>: under protected path <entry>` (the seat never writes a plan or the override; the orchestrator's finer heading rule is not ported — D9). `_edit_verdict`'s existing rules stay first.
- Error contract (RT5r extended): the new arm reads a file and resolves paths, so any exception in it is a DENY with `bash rule could not be evaluated: <ExceptionName>` — the model rule's fail-closed shape, not the pure string-scan's allow-on-error; `main()` still returns 0 on every path. A 4 MiB payload and the nesting pre-scan are unchanged.
- `tests/unit/94-guard-parity.bats`: for each of the 442 sweep rows, both guards run over the same fixture project (`PROJECT` built as `91-orchestrator-guard.bats` builds it, `CLAUDE_PROJECT_DIR` set for both), the orchestrator guard with `{"tool_name":"Bash","tool_input":{"command":…}}` and hook-guard with `{"hook_event_name":"PreToolUse","tool_name":"bash","tool_input":{"command":…}}` and `--guard-rules docs/ledger/guard-rules.toml --routing-table <a fixture table>`; `deny` = stdout carries `"permissionDecision": "deny"`, `allow` = empty stdout; the verdicts must be equal on every row, and the test prints every differing row (`row N: orchestrator=deny seat=allow: <command>`) before failing. A second test runs the recipe commands of `docs/runbooks/session.md`'s "Recipes" section and the WORKSPACE RULES' commands (`nix develop -c git commit -F msg`, `git add x`, `nix build .#checks.x86_64-linux.unit -L --no-link`, `python3 pkgs/evidence/repomap.py --root . write`) through hook-guard and asserts allow for each (A14).

**Facts:**

- `grep -n 'def _bash_verdict\|def _edit_verdict\|^PROTECTED_ABSOLUTE\|def _routing_table_path\|arg == "--routing-table"\|except BaseException\|CLAUDE_PROJECT_DIR' pkgs/dsh-openrouter/hook-guard.py` → the two verdict functions, the literal list, the flag parser (`if arg == "--routing-table" and i + 1 < len(argv):`), the two `except BaseException as exc:  # noqa: BLE001` regions and `project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "") or os.getcwd()`. The module docstring's RT5r contract: the bash string-scan "keep today's allow-on-error: they are pure string/path checks that cannot raise" — the new arm is neither pure nor raise-free, hence its fail-closed clause.
- `grep -n 'hook_command=\|routing_table=${FACTORY_ROUTING_TABLE' pkgs/dsh-openrouter/dsh-openrouter.sh` → `routing_table=${FACTORY_ROUTING_TABLE:-$HOME/nixos-agent-env/docs/ledger/routing.toml}` and `hook_command=$(jq -n --arg g "$hook_guard" --arg t "$routing_table" …)` — the shape `--guard-rules` joins.
- `grep -n 'hookGuard = writePython3MinimalBin\|flakeIgnore\|builtins.readFile ./hook-guard.py' pkgs/dsh-openrouter/default.nix` → the guard is built into the `dsh-openrouter` package from the file at build time with a flake8 self-check (`E501` ignored): the live seat runs the new guard only after a switch (A2/A13), and the code must be flake8-clean.
- `sed -n '607,656p' tests/unit/70-dsh-openrouter.bats` → `guard_payload`, `guard_denies`, `guard_denies_reason`, `guard_allows` drive `hook-guard` from `PATH` (the `unit` sandbox's `dshOpenrouter`); `grep -n '^@test' tests/unit/70-dsh-openrouter.bats | grep -c 'hook-guard'` → the existing guard tests that stay green.
- `sed -n '13,60p' tests/unit/91-orchestrator-guard.bats` → `GUARD=…/tools/orchestrator-guard.sh`, `bpayload`, `run_guard` with `CLAUDE_PROJECT_DIR="$PROJECT"`; the fixture project the parity test reuses.
- `head -c 2500 tests/unit/91-orchestrator-guard-sweep.txt` → rows of both kinds: `rm -rf .claude/*`, `cd .claude && rm ritual-override`, `python3 -c 'import os;os.remove(".claude/ritual-override")'`, `r''m -rf .claude`, `tar -C .claude -xf /tmp/a.tar`, `xargs rm < .claude/list`, `git stash -u` (denies) and `ls -la .claude`, `cat .claude/ritual-override`, `git status`, `echo a`, `chmod 755 k`, `nix develop -c git commit -q -F /tmp/msg`, `git pull --ff-only /home/dalhaka/factory/ws/cr12/CR2b task/CR2b` (allows) — the spec's sentence "denies every command in the sweep table" is therefore read as "gives the sweep row the orchestrator guard's verdict"; the oracle is that guard.
- `grep -n 'lane_list = ' tests/lane/test_forbidden_lists_agree.py` → the three-way test reads `lane.FORBIDDEN_REPO_PREFIXES`, hook-guard's list and the wrapper's `forbidden=(…)`; the claim `forbidden-list-single-source` stays a gap (two copies remain).

- [ ] **Step 1: Write the failing tests** — `tests/unit/94-guard-parity.bats` (the two tests above), and in `tests/unit/70-dsh-openrouter.bats`:

| # | assertion | mutant |
|---|---|---|
| 1 | `hook-guard --guard-rules /nonexistent` denies `echo a` with `guard rules unreadable at /nonexistent`; with the committed file `echo a` is allowed | allow on a missing file |
| 2 | `rm -rf .claude`, `git commit --amend`, `sed -i s/a/b/ docs/superpowers/plans/x.md`, `cd docs/superpowers && rm -rf plans`, `python3 -c 'import shutil;shutil.rmtree(".claude")'` → denied with the orchestrator guard's reason strings; `cat docs/superpowers/plans/x.md`, `git log`, `nix build .#checks.x86_64-linux.unit -L --no-link` → allowed | any single family |
| 3 | an `edit` of `docs/superpowers/plans/x.md` and a `write` of `.claude/ritual-override` (relative to the project) → denied `under protected path`; an edit of `docs/reviews/x.md` → allowed | port the heading rule instead |
| 4 | a rules file with `kind = "dirr"` → every bash payload denied `guard rules unreadable` (the validator is shared with SD6's rules) | accept |
| 5 | the fail-closed clause: `monkeypatch`-free — a payload whose command holds a 20,000-token string of `x/../` path segments completes in under 2 s with a verdict (no crash, exit 0); a command naming a symlink loop in the fixture project → deny `bash rule could not be evaluated: OSError` or a verdict, never a non-zero exit | let the exception escape |
| 6 | the wrapper's generated `hooks.json` carries `--guard-rules` with the default path in all three matchers (extends the existing `--dump-config` wiring test) | drop the flag |
| 7 | parity: 442/442 rows equal; the recipe list allowed | any port defect (the test prints the rows) |

- [ ] **Step 2: Run it red** — `nix develop -c bats tests/unit/94-guard-parity.bats` → the differing rows printed (expected today: every `.claude`/plans deny row differs — the seat guard allows them) and the count; `nix develop -c bats tests/unit/70-dsh-openrouter.bats --filter 'guard-rules|protected path|could not be evaluated'` → `--guard-rules` unknown (paste the first line of each).
- [ ] **Step 3: Make the change** — `_load_rules`, `_token_verdict` and its helpers named above, the edit/write rule, the flag, the wrapper line, the lane test's source; `nix develop -c ruff format pkgs/dsh-openrouter`.
- [ ] **Step 4: Run green** — `nix develop -c bats tests/unit/70-dsh-openrouter.bats tests/unit/94-guard-parity.bats`; `nix develop -c pytest tests/lane -q`; `git add` the new file; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.unit -L --no-link` (builds the package and its flake8 self-check); `… lane-unit`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** rows 1–7 (row 7 is 442 assertions); the discriminating fixtures: the 442 rows themselves (the reviews' spellings: quoted, continued, `cd`-based, python/perl, `xargs`, `tar -C`, glob, ancestor), the malformed rules copy, the symlink loop.

**touches:** tests/unit/94-guard-parity.bats, pkgs/dsh-openrouter/hook-guard.py, pkgs/dsh-openrouter/dsh-openrouter.sh, tests/unit/70-dsh-openrouter.bats, tests/lane/test_forbidden_lists_agree.py
**acceptance:** unit, lane-unit, lint
**commit subject:** `seat: hook-guard reads the shared rule file — the token-scan arm, parity with the orchestrator guard over the sweep fixture (test: unit, lane-unit, lint)`

### SD8 (code, S) — the record answers the operator: rung, class, prior and escalate in the tasks row, evidence report ladder refused under five

**dependsOn:** SD3, T2, T10a

**Files:**
- Create: `tests/evidence/fixtures/results/rung2.result`, `tests/evidence/fixtures/results/escalate.result`
- Modify: `pkgs/evidence/streams.py` (four `task-result` fields), `pkgs/evidence/ingest_result.py` (four producers), `pkgs/evidence/report.py` (`ladder`), `pkgs/evidence/SCHEMA.md`, `tests/evidence/test_streams_policy.py`, `tests/evidence/test_ingest_result.py`, `tests/evidence/test_report.py`, `docs/runbooks/evidence.md`

**Interfaces:**

- `streams.KINDS["task-result"]["fields"]` gains `"rung": ("int", 1, 9)`, `"class": ("enum", CLASSES_TASK)` with `CLASSES_TASK = ("nix-module", "nix-check", "bash-driver", "python-evidence", "js-workflow", "bats-test", "vm-test", "docs-runbook", "docs-plan", "docs-board", "any")`, `"prior": ("null", ("re", r"^[A-Za-z0-9._-]{1,64}/[A-Za-z0-9][A-Za-z0-9_-]{0,31}$"))`, `"escalate": ("null", ("re", r"^claude/(implement|review|orchestrate)$"))`. The version stays 1 (a missing declared field is not an error — the fence's rule).
- `ingest_result` producers, each from one `.result` line: `rung` ← `rung:` int, absent → `1`; `class` ← `class:` when in the enum, absent or unknown → `any`; `prior` ← `prior:` when it matches, else `None`; `escalate` ← `escalate:` when it matches, else `None`. `fallback:`, `launch:` and the `## Prior attempt` text are never stored.
- `evidence [--store S] report ladder --repo <path> [--min-n 5] [--today YYYY-MM-DD]` (a second subparser beside `plans` in `report.py`): rows = `evidence.join_tasks_gates(store)` (T10a); role ← the `route` label's first segment when it is `implement`, else `unknown`; provider route ← `openrouter` for every seat result (the `.result` is the seat driver's). Group key `(route, role, task_kind, size, class, model, effort, rung)`; per group: `n`, `first-gate approved` = groups' rows whose `gate.verdict == "approved"` ÷ rows with a gate, printed `a/g`; `landed/attempt` = rows whose `head` is in `git -C <repo> rev-list HEAD` (read once into a set) ÷ n — the "tangible" column; `fix rounds per landing` = rows whose `gate.round_kind == "fix"` ÷ landed rows (`—` when none landed); `median wall_s` and `median out` (`usage.out`) over the group; `escalate` = rows with a non-null `escalate` (the rung-3 demand). A group under `--min-n` is not printed; the header line `# evidence report ladder — tasks ⋈ gates by (route, role, kind, size, class, model, effort, rung); n printed with every figure; groups under n=<min> refused` and a trailer `groups: <k> printed, <m> refused under n=<min>`. Lines are `<route>/<role>/<kind>/<size>/<class> <model> <effort> rung <r>: n=<n> approved <a>/<g> landed <l>/<n> fix-per-landing <f> wall-med <s>s out-med <t> escalate <e>`, sorted by the key. No store or an unreadable repo → exit 2 `report: …`; exit 0 otherwise. `n_gate` is the refusal used (`n_gate(rows, min_n)` returns the `insufficient (n=…)` string, which the report turns into the refused count).
- `docs/runbooks/evidence.md` gains the report's line grammar and its refusal rule.

**Facts:**

- `ls pkgs/evidence` → `SCHEMA.md claims.py evidence.py judgements.py repomap.py report.py tasks.py`: no `streams.py`/`ingest_result.py` in this tree — T1 and T2 create them (the `dependsOn`). `grep -n '"task-result": {"stream"\|"route": ("re"' docs/superpowers/plans/2026-09-06-telemetry-store-1.md` → the declared fields and the route regex `^(explicit|unknown|implement/(code|docs)/(XS|S|M|L))$`; the plan text names the task's kind `"kind"`, while `describe select * from read_json_auto('evidence/derived/tasks.jsonl')` (duckdb over the fixture store, 238 rows) lists `task_kind` beside the envelope's `kind` — D10: the seat greps `pkgs/evidence/streams.py` for `"task_kind"` first and reports a deviation if the landed name differs.
- The fixture store's counts (duckdb, `group by`): `status` `done` 223 / `failed` 13 / `unknown` 1 / `partial` 1; `error_class` `none` 220 / `no-result-line` 12 / `template-echo` 6; `route` `unknown` 152 / `implement/code/S` 57 / `explicit` 12 / `implement/code/XS` 7 / `implement/code/M` 6 / `implement/docs/S` 3 / `implement/docs/XS` 1; `model` Pro 220 / Flash 16 / glm 1 / kimi 1; `derived/gates` `verdict` approved 77 / rejected 66 / unknown 27, `round_kind` first 103 / fix 40 / replan 27. So on core the report will print one group with `n ≥ 5` for certain — `openrouter/implement/code/S/any deepseek/deepseek-v4-pro-0813 medium rung 1: n=57 …` — and refuse the rest until new rows arrive; the Operator section's acceptance is that shape.
- `grep -n 'def plans_report\|add_parser("plans"\|refused: n=' pkgs/evidence/report.py` → the sibling report's structure (`plans_report(store, repo, today, min_n, plan)`, one subparser, the refusal line) that `ladder` mirrors; `grep -n 'def n_gate\|n_gate(rows' docs/superpowers/plans/2026-09-06-telemetry-store-1.md` → T10a's `n_gate(rows, n=5)` "exported for T10b and the ladder report".
- `grep -n '"report"' pkgs/evidence/evidence.py` → the CLI already dispatches `report` to `report.py`; no `evidence.py` change.

- [ ] **Step 0: Verify the landed contract** — `grep -n '"task_kind"\|"kind": ("enum", ("code", "docs"' pkgs/evidence/streams.py` and `grep -n 'def join_tasks_gates\|def n_gate' pkgs/evidence/evidence.py`; paste both. If `task_kind` is absent or the join is missing, stop and report (`FACTORY-RESULT status=failed`, the notes naming the grep).
- [ ] **Step 1: Write the failing tests** — `test_streams_policy.py`: every arm of `class` accepted and `class: "bogus"` refused, `rung: 0` and `rung: 10` refused, `prior: "r1/K1"` accepted and `prior: "r1"`/`"r1/K 1"` refused, `escalate: "claude/implement"` accepted and `"claude/plan"`/`"openrouter/implement"` refused (mutants: widen the enum; drop the `re`). `test_ingest_result.py`: `rung2.result` (`rung: 2`, `class: bash-driver`, `prior: r0/K1`, `fallback: deepseek/deepseek-v4-flash`) → the row's four fields and no `fallback` key; `escalate.result` (`FACTORY-RESULT status=skipped`, `escalate: claude/implement`, a `launch:` line) → `escalate` set, `status skipped`, and the row has no `launch` key nor the launch text anywhere (`json.dumps(row)` does not contain `Workflow(`); a result without the lines → `rung 1`, `class any`, `prior None`, `escalate None` (mutants: store the launch line; default the rung to 0). `test_report.py`: a store of 12 task rows in three groups (7 rows of one key with 4 approved gates, 5 landed heads, 2 fix rounds; 4 rows of a second key; 1 row with `escalate`) and a fixture repo whose `git rev-list HEAD` holds the 5 landed heads → exactly one group line with `n=7 approved 4/7 landed 5/7 fix-per-landing 0.40` and the medians computed by hand, the trailer `groups: 1 printed, 2 refused under n=5`; `--min-n 4` prints the second group; a row whose `head` is unknown to the repo counts as not landed; the `escalate` column reads `1` for the group holding it (mutants: `>` for `>=` at the gate; count landed by `status == done`; sort unstable).
- [ ] **Step 2: Run it red** — `nix develop -c pytest tests/evidence -q -k 'ladder or rung or escalate or prior'` → `report.py: error: argument command: invalid choice: 'ladder'` and the streams tests' `undeclared field` reasons (paste).
- [ ] **Step 3: Write the code**; `nix develop -c ruff format pkgs/evidence tests/evidence`.
- [ ] **Step 4: Run green** — `nix develop -c pytest tests/evidence -q`; `git add` the new fixtures; `python3 pkgs/evidence/repomap.py --root . write`; `nix build .#checks.x86_64-linux.evidence-unit -L --no-link`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 5: Commit.**

**Tests:** as in Step 1; the discriminating fixtures: the 7/4/1 group sizes across the n=5 gate, the unknown head, the `launch:` line that must not land, the `claude/plan` escalate that must not.

**touches:** tests/evidence/fixtures/results/rung2.result, tests/evidence/fixtures/results/escalate.result, pkgs/evidence/streams.py, pkgs/evidence/ingest_result.py, pkgs/evidence/report.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_streams_policy.py, tests/evidence/test_ingest_result.py, tests/evidence/test_report.py, docs/runbooks/evidence.md
**acceptance:** evidence-unit, lint
**commit subject:** `evidence: the record answers the operator — rung, class, prior and escalate in the tasks row, evidence report ladder refused under five (test: evidence-unit, lint)`

### SD9 (docs, S) — the driving skill: brief, dispatch, gate, integrate as calls to the driver scripts; what the driver decides alone

**dependsOn:** SD3

**repo:** dsh-harness

This task runs in `~/flakes/dsh-harness` (`FACTORY_PLAN=<this plan's absolute path> tools/factory/seat/factory-wave sd4 /home/dalhaka/flakes/dsh-harness "SD9"`; the workspace is a clone of that repo, which has no flake and no hooks — P13's Assumption 11 — so the gate is the commands below; commits via `nix develop /home/dalhaka/nixos-agent-env -c git commit -F <msgfile>`). Claude agents never write inside `~/flakes/dsh-harness`; this seat does, through that repo's own gate.

**Files (in ~/flakes/dsh-harness):**
- Create: `skills/driving/SKILL.md`
- Modify: `CHANGELOG.md` (one dated line)

**Interfaces:**

- `skills/driving/SKILL.md` — frontmatter `name: driving`, `description: drive the dark factory from the operator's seat on core: read the brief, dispatch a ready wave, gate a finished task, integrate an approved one — each verb one call to the driver scripts under ~/nixos-agent-env/tools/factory/seat; use when the seat was started as a drive job`. Body: the four verbs, each exactly one command and its acceptance — **brief**: `nix develop /home/dalhaka/nixos-agent-env -c python3 pkgs/evidence/tasks.py --root /home/dalhaka/nixos-agent-env brief` (run from that directory); **dispatch**: `tools/factory/seat/factory-dispatch <run> /home/dalhaka/nixos-agent-env docs/superpowers/plans/<plan> --dry-run`, show the `would run:` line to the operator, and only on the operator's word the same line without `--dry-run`, in the background (`setsid -f … </dev/null`); **gate**: `tools/factory/seat/factory-review <run> /home/dalhaka/nixos-agent-env <KEY>` (the `review` row of the table chooses the reviewer; a rung whose row is on the `claude` route is a printed launch line for the operator's Claude Code session, never run here); **integrate**: `tools/factory/seat/factory-integrate <run> /home/dalhaka/nixos-agent-env <KEY>` and then print — never run — the fast-forward line the integrator ends with. The rules (spec Design 7, verbatim in the skill's words): the driver alone may dispatch a ready task at rung 1, relaunch a dead seat sideways with `factory-task --fallback` after a `budget-402` (once credits are recorded restored), a `provider-error` or a `boot-failure` (once each), launch the fix round `<KEY>b` (rung 2) with `--prior <run>/<KEY>` after a rejection, print a `claude` rung's launch line, and rewrite the board's queue block with `tasks.py write-board`; everything else — a pause, spend, a switch, a spec approval, a rung-3 re-plan's dispatch, any routing row — is the operator's, asked in one line. It never opens a `.log`, a `.dsh-home` or a transcript; it never merges `main` into a task branch; it never edits a plan. Every model comes from the routing table: the skill names no model and no tier — its words are `rung` and `fallback`.
- The gate (that repo's, run in the workspace; each command recorded red before and green after): (1) the harness's whole-tree model-choice gate as its README names it (P13 records the same repo's grep gates) prints nothing; (2) `grep -rniE 'tier|escalat' skills/driving/SKILL.md` prints nothing (the skill's own vocabulary rule); (3) `test -f skills/driving/SKILL.md && sed -n '2,/^---$/p' skills/driving/SKILL.md | grep -c '^name: driving$'` prints `1`; (4) the frontmatter description holds the word `drive` and no other SKILL.md's description does (`for f in skills/*/SKILL.md; do sed -n '2,/^---$/p' "$f" | sed -n 's/^description: //p' | grep -qiw drive && echo "$f"; done` prints exactly `skills/driving/SKILL.md`).

**Facts:** `unavailable:` the harness tree is not present where this plan was drafted (`ls -d ~/flakes` → no such directory); what is known comes from this repo: the catalog symlink recipe (`warn_missing_payload "$DSH_HOME/skills" "skill catalog" "ln -s ~/flakes/dsh-harness/skills $DSH_HOME/skills"` in `pkgs/dsh-openrouter/dsh-openrouter.sh`), P13's landed shape in `docs/superpowers/plans/2026-09-06-planning-agent.md` (`**repo:** dsh-harness`, the gate as grep commands, `acceptance: grep-gate, node-test`), the spec's sentence about the harness gate (`grep -n 'whole-tree gate' docs/superpowers/specs/2026-09-06-operator-seat-driver-design.md` → "its whole-tree gate refuses 'any per-dispatch tier-escalation wording' in prompts, READMEs and skills"), and `tasks.py conflicts` → P13 (blocked) still touches `README.md`, `CHANGELOG.md`, `AGENTS.md` in that repo, so this task edits `CHANGELOG.md` only and lands after P13 or merges it at integration (the integrator's step).

- [ ] **Step 1: Red** — in the workspace: `test -f skills/driving/SKILL.md; echo rc=$?` → `rc=1`; gate (4) prints nothing; paste both. Read the harness README's gate section and run its gate command once on the clean workspace (paste its output, expected nothing).
- [ ] **Step 2: Write** `skills/driving/SKILL.md` and the CHANGELOG line (`2026-09-06 — skills/driving: the drive job's four verbs as calls to the seat driver (plan 2026-09-06-seat-driver, SD9)`).
- [ ] **Step 3: Green** — gates (1)–(4) recorded: nothing, nothing, `1`, `skills/driving/SKILL.md`.
- [ ] **Step 4: One commit.**

**Tests:** the four gate commands are the assertions; mutants: write `escalation` anywhere in the skill → gate (2) prints a line; a second skill whose description says `drive` → gate (4) prints two lines; drop the frontmatter → gate (3) prints `0`.

**touches:** skills/driving/SKILL.md, CHANGELOG.md
**acceptance:** grep-gate
**commit subject:** `docs: the driving skill — brief, dispatch, gate, integrate as calls to the driver scripts; what the driver decides alone (test: grep-gate)`

### SD10 (docs, S) — the seat-driver runbook: seed the drive home, submit, open, the four verbs, the spool, rollback

**dependsOn:** SD3, SD5

**Files:**
- Create: `docs/runbooks/seat-driver.md`

**Interfaces:** plain language, one command per step, each with its acceptance — the Operator section of this plan is its source: seed the drive home (`factory_seed_dsh_home`), submit the drive job (`nix run ~/nixos-agent-env#seat-submit -- drive …`), open the URL, the four verbs as the operator sees them (what to say to the seat, what it may do alone, what it asks), the spool (`journalctl -u seat-spool.service`, the `started`/`refused` markers), the ladder (`factory-task --rung`, `--fallback`, `--prior`; how a `claude` rung's launch line reaches the operator), the report (`evidence report ladder`), stopping a job (`systemctl stop seat@<id>` — the operator's), rollback (the generation). It names `docs/runbooks/seat.md` (SB5, held) as the seat lane's own runbook and does not duplicate it.

**Facts:** `ls docs/runbooks` → `backup.md evidence.md helm-v1.md helm.md lanes.md phase1-acceptance.md phase2-acceptance.md phase3-acceptance.md phase4a-switch.md phase4b-acceptance.md session.md switch-helm-gaming.md` — no `seat.md` and no `seat-driver.md`; SB5 (`awk '/^### SB5 /,/^### SB2b /' docs/superpowers/plans/2026-09-05-seat-behind-broker.md`) creates `docs/runbooks/seat.md` and edits `docs/runbooks/lanes.md`, `CLAUDE.md`, `docs/ledger/claims.toml` — this task touches none of them. `grep -n 'runbooks' docs/MAP.md` → nothing: the map does not list runbooks, so no `MAP.md` change.

- [ ] **Step 1: Red** — `test -f docs/runbooks/seat-driver.md; echo rc=$?` → `rc=1`; `grep -rn 'seat-driver.md' docs | wc -l` → `0` (paste).
- [ ] **Step 2: Write** the runbook (≤ 120 lines; every command copied from the Operator section as it stands on main after SD3 and SD5 landed, re-checked against `seat-submit --help` and `factory-task`'s usage line in the workspace).
- [ ] **Step 3: Green** — `nix develop -c treefmt`; `nix develop -c python3 pkgs/evidence/tasks.py --root . check`; `nix develop -c githooks/pre-commit`.
- [ ] **Step 4: One commit.**

**Tests:** `grep -c '^\$ \|^    nix run\|^    tools/factory' docs/runbooks/seat-driver.md` ≥ 8 (a command per step); mutant: a step written as a sentence with no command → the count drops below eight; the lint gate is the acceptance.

**touches:** docs/runbooks/seat-driver.md
**acceptance:** lint
**commit subject:** `docs: the seat-driver runbook — seed the drive home, submit, open, the four verbs, the spool, rollback (test: lint)`
