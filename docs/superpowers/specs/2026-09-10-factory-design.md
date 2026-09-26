# The Factory subsystem — design (spec for review)

**Date:** 2026-09-10 (draft, revised 2026-09-15 for the 2026-09-10 amendment's
backend collapse). **Authority:** the charter's §2 Factory row
(`docs/concepts/2026-09-09a-redesign-charter.md` §2, the Factory row;
area `factory`, Opus gate, prefix `FA`, answers 21–34); the charter's §5
mechanics (the batching bullet as corrected OpenRouter-only by the decisions
file's §4 amendment);
§6 increment 2's Factory build list (§6 "Increment 2" section); §8 item 4
(the batch lane's two measurements, §8 item 4). **Decisions:**
`docs/decisions/2026-09-09-redesign-answers.md` rows 21–34 (§1 "The answers"),
53 (row 53), 64–66 (rows 64–66), 69–71 (rows 69–71), 73 (row 73);
the departures for 21, 28/73 and 30 (§2 "Where the operator departed from the
recommendation"); the amendments §4
OpenRouter-only (§4 amendment), §5 (§5 amendment) and §6 (§6 amendment).
**Context block:** `docs/context/factory.md`. **Charter-to-task map:** the plan
`docs/superpowers/plans/2026-09-11-factory.md` (§Charter-to-task map).

**Approved by the operator: [pending].**

---

## §1 Header — what this spec describes

The Factory subsystem is the repo-side task-execution engine for the NixOS agent
environment. It owns the declarative workflow graphs, the agent registry with
generated `.md` shims, the bash tools as the one executor, the declared rung
and the machine-readable escalation payload, the bug workflow's rungs and
re-resolver, the provider batch API measured against `plan.js`, the guarded
workflows directory, and the retired `dark-factory.js` archived in the tree.
Every automated model call in this program runs on the OpenRouter lane; the
heading's "`claude -p` and `dsh headless`" is superseded by the 2026-09-10
amendment — the two backends collapse to one, and `claude -p` survives only as
the rung-3 terminus the operator runs by hand.

This spec names the batch-latency measurement (charter §8 item 4) as its first
task.

### §1.1 What it is not

- Not a NixOS module — Factory owns no `nixosModules/*` entry.
- Not a seat — the seat lane, `seat-submit`, `pkgs/seat/*`, `pkgs/dsh-openrouter/*`
  and the seat hooks belong to Seat/Harness (`SA`).
- Not an evidence store, a ledger, a bug database or a status page — those are
  Evidence (`EV`).
- Not the rules audit, the generated CLAUDE.md/AGENTS.md, or the runbooks —
  those are Knowledge (`KN`).
- Not `flake.nix`, the host config, or the check derivations — Platform (`PL`).

### §1.2 Invariants kept

Every task in this plan is written against the six brief §3 invariants
(`docs/brief.md` §3, re-ratified per decision 55a). The specific bindings,
per `docs/superpowers/plans/2026-09-11-factory.md` (the "Invariants" subsection):

- FA20 carries no credential and reaches the endpoint only through the lane's
  proxy (invariants 2, 3).
- FA24 narrows a seat's reach and widens none (invariant 6).
- FA13's registry, FA14's graphs and `routing.toml` stay configuration
  reviewable in a diff (invariant 5).
- No task touches basket mounting (1) or adds imperative setup (4).

---

## §2 What exists today (reused, not rebuilt)

Measured at HEAD `92369a1` (2026-09-15, re-measured at commit time per G11). Source: `docs/context/factory.md`.

### §2.1 The bash tools under `tools/factory/seat/`

16 files, 5940 lines (measured: `git ls-files tools/factory/seat/ | wc -l` × `xargs wc -l | tail -1`). The seat's per-task toolset:

- `factory-lib.sh` (1562 lines) — shared library: `factory_route`, ladder
  checks, rung derivation, prior-record reading.
- `factory-task` (1046 lines) — runs one typed task in an isolated workspace.
- `factory-wave` (319 lines) — dispatches a wave of tasks with a concurrency
  cap (`FACTORY_JOBS`, default 5).
- `factory-review` (296 lines) — the Opus gate, reads Global Constraints.
- `factory-integrate` (231 lines) — records every check and merges.
- `factory-dispatch` (213 lines) — asks the derived graph for the next wave.
- `factory-brief` (158 lines), `factory-ws` (144 lines), `factory-plan.sh` (105
  lines), `factory-plan-brief.sh` (485 lines), `factory-codex-usage.py` (105
  lines), `factory-usage.py` (97 lines), `factory-commit-msg.sh` (72 lines),
  `launch-today.sh` (17 lines), `seat-drive.sh` (171 lines).

The route resolver `tools/factory/route.py` (486 lines) is the single source of
truth for model selection, cross-checked against the bash `factory_route` by
`factory-unit`. `docs/ledger/routing.toml` (278 lines, 25 rows) carries the
`route × role × kind × size × class × area` ladder.

### §2.2 The workflow scripts under `.claude/workflows/`

Five JS scripts, 1846 lines (measured: `for f in $(git ls-files .claude/workflows/); do wc -l < "$f"; done | awk '{s+=$1} END {print s}'`):

- `plan.js` (458 lines) — the planning agent, used by the operator's session.
- `batch-plan.js` (268 lines) — the batched planning step, nine Fable calls.
- `gather.js` (527 lines), `context-blocks.js` (307 lines), `loose-ends.js`
  (286 lines).

No `.claude/agents/` directory exists today. `batch-plan.js` numbers the
Factory plan from FA12 (the `{ key: 'factory', start: 12 }` entry).

### §2.3 The existing mechanism — key names as routing

Today, `factory_rung_of_key` (`factory_rung_of_key` in `factory-lib.sh`) reads a trailing one-or-
two lowercase letters after a digit as the rung: `r` → rung 3, any other suffix
→ rung 2, no suffix → rung 1. Key names are routing. Decision 26a says the node
declares the rung; key suffixes stop being routing.

### §2.4 The escalation path

On route exit 4 (an empty `route_line` after the cross-route search),
`factory_task_escalate` (the `factory_task_escalate` function in `factory-task`) writes a flat `<KEY>.escalate`
whose `launch:` line calls `Workflow({ scriptPath: 'tools/factory/dark-factory.js', ... })` — the script decision 33a archives. No paragraph, no
claims, no repro, no JSON artifact. Decisions 28, 32a and 73 require a
machine-readable artifact with claims, repro and errata, and a launch line that
names `factory-run.py` instead.

### §2.5 The guard's protected paths

`R-guard-protected-paths` (the `R-guard-protected-paths` rule in `docs/ledger/rules.toml`) does not list
`.claude/workflows/*` or the agent registry today. Decision 34a moves the
workflows directory and the agent registry under the guard's protection.
`R-guard-plan-append-only` (`R-guard-plan-append-only` in `docs/ledger/rules.toml`) and `R-guard-plan-write-tools`
(`R-guard-plan-write-tools` in `docs/ledger/rules.toml`) protect only `docs/superpowers/plans/`.

### §2.6 The agent registry

None exists today. Decision 23b wants one pinned registry (role → model, effort,
tools, schema, prompt file) with generated, drift-checked `.md` shims.

### §2.7 The batch lane measurement

FA2 (`18678b1`) recorded the endpoint in
`docs/research-2026-09-11-batch-lane.md` (§2 "The batch endpoint: request
shape, poll, result grammar, turnaround"): `POST /api/beta/batches` with
inline `requests` → `202`, `status: "validating"`; `GET /api/beta/batches/<id>`
through `validating → in_progress → completed`, terminal
`completed|failed|expired|cancelled`; `results[]` keyed by `custom_id` with
`response.status_code`/`response.body`; 259 s on one probe (the "Turnaround and
cost" paragraph in §2); `usage.cost` at the 50 % rate.

### §2.8 The task-class rows

`docs/ledger/task-classes.toml` carries the `docs-spec` and `docs-plan-run`
classes (FA1 landed them). The spec-writing tasks (SPEC-FA, SPEC-PL, SPEC-SA)
carry `class = "docs-spec"` which routes them through the rung-3 claude terminus
(Fable at $10/$50, the operator's session).

---

## §3 The goal

A repo-side graph runner reads declarative workflow graphs from `.claude/workflows/*.toml`, dispatches agent and tool nodes through the seat's bash
tools (the one executor), checks soundness at build time, carries the rung in
the node declaration (not the key name), writes a machine-readable escalation
artifact on exhaustion, drives the bug workflow through a Flash→re-resolver→gate
ladder, and calls the provider batch API for Fable drafting through the lane.
The agent registry pins every role's model and generates drift-checked `.md`
shims. The workflows directory and the registry join the guard's protected paths.
`dark-factory.js` moves to the archive.

---

## §4 The changes

### Change 1 — The declarative graph runner (FA14, FA15, FA16)

**Decisions:** 22a as amended by §4 (the repo-side runner, backends collapsed to
the lane), 24a (declarative graph file per workflow), 33a (bash tools as the
executor).

**What changes.**

Graph files are TOML under `.claude/workflows/<workflow>.toml`. Each has four
node types:

- **agent** — `role = "implement"`, `rung = 1`, `budget = 3`, reads from a
  registry row, runs the seat's bash tools.
- **tool** — `kind = "nix-build"`, `budget = 1`, runs a named script from
  `tools/factory/seat/`.
- **gate** — `kind = "review"`, `budget = 1`, runs `factory-review`.
- **refusal** — terminal, writes the escalation artifact.

Edges carry attempt budgets: `edge { from = "A", to = "B", attempts = 3 }`.
A node that exhausts its budget passes the artifact to the next node.

A new runner script `tools/factory/seat/factory-run.py` reads the graph, walks
the edges, dispatches each node through `factory-task` (for agent nodes) or
directly (for tool/gate nodes), and passes the machine-readable artifact between
nodes. It is the bash executor the charter requires — the one executor, no
`dark-factory.js`, no Workflow tool call.

A soundness check `factory-graph.py check <paths>` runs at build time:

- Every `from`/`to` name references an existing node.
- Every agent node's `role` exists in the registry.
- Every tool node's `kind` is known.
- Every node has at least one incoming edge (except the start node).
- No cycles.

**How it fits.** FA14 creates the graph file schema, `factory-graph.py` and the
first two graph files (`bug.toml`, `plan.toml`). FA15 creates `factory-run.py`.
FA16 teaches `factory-task` to accept a prompt file and schema flag from the
graph runner (passed through `seat-submit`).

### Change 2 — The agent registry with generated shims (FA13)

**Decisions:** 23b (one pinned registry, `.md` shims generated and drift-checked).

**What changes.**

A TOML registry `tools/factory/agents.toml` with one `[[agent]]` row per role:

- `implement`, `review`, `draft`, `judge`, `judge-fable` (the fifth for the
  panel's batch judge).
- Each row carries `route`, `role`, `kind`, `size`, `class`, `rung`, `effort`,
  `tools[]`, `schema` (an artifact kind name from the graph grammar), `prompt`
  (a path under `tools/factory/plan/` or `tools/factory/seat/`).

A new script `tools/factory/seat/factory-registry.py` with verbs:

- `resolve ROLE` — calls `route.py lookup` for the row's keys, prints `MODEL
  EFFORT`.
- `check` — exits 0 silently when every row resolves, every `prompt` exists,
  every `schema` names a known kind, and every `.claude/agents/<role>.md`
  byte-equals `render`'s output; else `registry: <role>: <fault>`, exit 2.
- `render [--out DIR]` — writes five `.md` shims deterministically from the
  registry and the current routing table.

Five shims under `.claude/agents/{implement,review,draft,judge,judge-fable}.md`,
each with frontmatter (`model:`, `effort:`, `tools:` verbatim) and a one-
paragraph body with `<!-- generated by factory-registry.py; do not edit -->`.

The registry is the only place a role's model is named outside `routing.toml`;
the graph names roles, never models.

The `judge-fable` row is the fifth row, needed for the batch-plan panel
(Assumption 23 of the plan; FA21 does not touch it, FA24 protects it).

### Change 3 — The rung declared, not derived from the key (FA12)

**Decisions:** 26a (node declares the rung; key suffixes stop being routing).

**What changes.**

Three new functions in `factory-lib.sh`:

- `factory_rung_check KEY PRIOR_RUN_DIR` — exits 0 when the suffix letter count
  equals the prior record's `attempts:`, exits 3 with a contradiction message
  otherwise.
- `factory_rung_from_prior PRIOR_RUN_DIR` — reads `rung:` from the prior
  `.result`, returns that plus one, or 1 with no prior.
- `factory_attempts_from_prior PRIOR_RUN_DIR` — the prior's `attempts:` plus one,
  or 1.

In `factory-task`: `--rung` sets the rung; without it, `factory_rung_from_prior`;
without `--prior`, it is 1. The key's suffix never sets the rung. Every `.result`
carries `attempts: N` (the prior's plus one) after `rung:`.

`factory_rung_of_key` is deleted.

### Change 4 — The escalation artifact (FA12)

**Decisions:** 28 (operator's words: "Escalate to me describing it in simple
terms and a ready made command"), 32a (machine-readable artifact with claims,
repro, errata), 73 (escalation is a design failure).

**What changes.**

On exhaustion (route exit 4 with an empty `route_line`), `factory-task` writes:

1. `<KEY>.escalation.json` — `kind = "escalation"`, `key`, `rung`, `attempts`,
   `design_failure = true`, `claims[]` (each `text`, `command`, `citation`),
   `repro` (`command`, `expected`, `observed`), `errata[]`,
   `verdict = "exhausted"`. Accepted by `factory-artifact.py check`.
2. `<KEY>.escalate` — one plain paragraph whose first line reads
   `<KEY>: <what failed> at rung <R> after <A> attempt(s)`, then exactly one
   `launch:` line: `nix develop -c python3 tools/factory/seat/factory-run.py
   .claude/workflows/plan.toml --input <run>/<KEY>.escalation.json --run <run>`.

The old `Workflow({ scriptPath: 'tools/factory/dark-factory.js', ... })` launch
line is replaced. Exit code stays 4; `factory-wave` reports the key as
escalated.

### Change 5 — Mechanical verification: the runner does itself (FA17)

**Decisions:** 25b (the runner re-runs the named mutants and the named checks;
the agent's own claim is never a signal).

**What changes.**

The gate node (`factory-review`) is the runner's verification step. It receives
the agent's artifact (commit, result block, probes) and runs:

- `nix build .#checks.x86_64-linux.unit -L --no-link` for bats tests.
- `nix build .#checks.x86_64-linux.lint -L --no-link` for lint.
- `nix build .#checks.x86_64-linux.factory-unit -L --no-link` for route parity.

A new `FACTORY_NIX` environment variable (overridable in bats fixtures) allows
the gate to run in a sandbox that logs `argv` and exits as the test expects.
No bats check runs a real `nix build` — the fixture replaces it.

The gate's review is filed under `docs/reviews/` (FA17 fixes the gate-record gap
forward; the four existing gaps — FIX5, UI1, FA1, FA3 — are not backfilled per
the plan's Assumption 21).

### Change 6 — The bug workflow's rungs and re-resolver (FA18, FA19)

**Decisions:** 27c (Flash first, a mechanical citation-and-command re-resolver
before any paid gate), 29a (typed bug ledger).

**What changes.**

A new graph file `.claude/workflows/bug.toml` defines the ladder:

```
flash → reresolve → gate → pro → reresolve → gate → refusal
```

- **Flash** (rung 1): `deepseek/deepseek-v4-flash`, 0 effort. Reads the bug
  fixture, attempts a fix.
- **Re-resolver** (tool node): a script that runs each claim's `command` from
  the prior node, compares `observed` to `expected`, and writes the verdict per
  claim to the artifact. It is mechanical — no model call.
- **Gate** (rung 1): `factory-review` on the flash commit; if it passes, the
  bug is fixed. If it fails, the artifact goes to the re-resolver, then to Pro.
- **Pro** (rung 2): `deepseek/deepseek-v4-pro-0813`, medium effort.
- **Gate** (rung 2): review of the pro commit.
- **Refusal**: terminal, writes the escalation artifact with the full claim
  history.

The bug ledger (`docs/ledger/bugs.toml`, EV4) feeds the graph's start node.
Each bug row has `id`, `symptom`, `repro command`, `status`, `closing check`.

### Change 7 — The batch-API draft node (FA20, FA21, FA22)

**Decisions:** 30b (provider's batch API, OpenRouter only per §4 amendment),
64a/65a as amended by §4, §5 and §6 (Fable through the lane's batch endpoint),
31a (incremental planning).

**What changes.**

FA20 replays the batch endpoint measurement from
`docs/research-2026-09-11-batch-lane.md` as replayable fixtures — the submit
body, the poll sequence, the result grammar. It wires the `openrouter-batch`
route into `route.py` and the routing table, and adds the batch-judge tool node
to the factory graph.

FA21 creates `tools/factory/seat/factory-batch.py` with verbs `submit`, `poll`,
`results` and `node` (the graph-runner verb that wraps submit→poll→fetch into
one artifact call). The `node` verb maps every terminal status to `broken` and
the timeout to `broken`, so the edge grammar never sees a batch status. It also
creates `tools/factory/seat/factory-artifact.py` with verbs `check`, `tally`
(implementing `plan.js`'s 14-row rubric, median-of-three scoring, the six
required floor rows ≥ 2, total ≥ 34).

FA22 drafts one plan through the batch endpoint against `plan.js`'s own rubric,
then judges it through the same batch endpoint, reports the delta in score,
dollars and turnaround. Its report is held for the operator's go (the plan's
question 2); the seat writes the frame with `HELD` rows and stops as `partial`.

### Change 8 — `dark-factory.js` archived (FA23)

**Decisions:** 33a (seat's bash tools only; `dark-factory.js` archived).

**What changes.**

`tools/factory/dark-factory.js` moves to `tools/factory/archive/dark-factory.js`
(inside Factory's `owns` glob, outside every check path). The ten references in
`flake.nix` are removed: the `darkFactorySyntaxCheckSrc` derivation (the
`darkFactorySyntaxCheckSrc` attribute at `flake.nix`), the `node --check` line
(the `${darkFactorySyntaxCheckSrc}` reference in `flake.nix`), the `factory-unit`
copy (the `cp ${self}/tools/factory/dark-factory.js` line in `flake.nix`), and
seven comment lines. `render.test.mjs` (161 asserts — 83 equal + 43 ok + 21 match + 9 deepEqual +
4 rejects + 1 doesNotMatch; measured: `grep -cE '\bassert\.(equal|ok|match|deepEqual|rejects|doesNotMatch)\b' tests/factory/render.test.mjs`) retires its dark-factory-specific
cases; the `route.py` parity assertion stays and moves to `factory-unit`.

The archiving is the final act — FA23 touches `flake.nix` and yields to any
live key that is `ready` on `flake.nix` when FA23 is (HH6 today).

### Change 9 — The guarded workflows directory (FA24)

**Decisions:** 34a (the workflows directory and the agent registry join the
guard's protected paths).

**What changes.**

`.claude/workflows/*` is added to `R-guard-protected-paths` and to the Bash
write denials in `orchestrator-guard.sh` and `hook-guard.py`. A Bash redirect or
`>>` into a path under `.claude/workflows/` is refused with "plan files change
only through the Edit and Write tools" — the same wording the plans denial
carries. The Edit and Write tools are not denied.

The agent registry file `tools/factory/agents.toml` is added on the same
ground.

A new row is added to `tests/lane/test_forbidden_lists_agree.py` to assert that
the three guard implementations (orchestrator-guard.sh, hook-guard.py,
lane-submit.py) agree on the new prefix.

FA24 is the last FA task to land; after it, the switch carries the new
`dsh-openrouter` package with `hook-guard.py` live.

---

## §5 What stays unchanged

- **The routing table format** — `route.py` and `factory_route` stay the two
  resolvers, cross-checked by `factory-unit`. The `area` column, the class-
  scoped `claude` terminus rows, and the `openrouter-batch` rows are additive.
- **The seat tools' interface** — `factory-task` remains the per-task runner,
  called by the seat; `factory-wave` dispatches; `factory-integrate` records
  checks. The graph runner calls them by the same paths.
- **The Opus gate** — `factory-review` stays the gate for every task
  (the Factory row's `gate = "opus"` in `docs/ledger/subsystems.toml`).
- **The evidence store** — all result blocks, usage rows and check logs continue
  to flow through `evidence.py`. No new store is created.
- **The key-namespace guard** — `tasks.py check` continues to refuse a key whose
  prefix matches another subsystem's. The two-part `SPEC-*` and `PLAN-*` keys
  are exempt.
- **No budget ceiling** — per decision 71b, the operator sets one after the
  ingest and OTel tasks land and one increment is measured.

---

## §6 Open questions for the operator

1. **Which panel judges a plan drafted on the lane?** Every automated call runs
   on the OpenRouter lane; IS4's exception admits only
   `anthropic/claude-fable-5.1`. Options: (a) two DeepSeek V4 Pro judges and
   one Fable judge; (b) an Isolation task widening the exception to
   Sonnet/Opus ids; (c) three Fable judges. Default at dispatch: (a).

2. **How much may FA22 spend, and does it wait for your go?** One context block,
   drafted once each way, judged once. Bound: the drafter is Fable through the
   lane at $10/$50 per MTok, the batch alias at half. The seat writes the
   report frame with `HELD` rows and stops as `partial` until you say "go".

3. **FA19's `dependsOn`: the bug ledger is EV4, not EV3.** EV3 is the
   `integrated` state; EV4 creates `docs/ledger/bugs.toml`. The field defaults
   to EV4.

---

## §7 Order of operations

The plan derives these waves (from
`docs/superpowers/plans/2026-09-11-factory.md` §Waves):

- **Wave 1:** FA13 (registry), FA14 (graph files), FA20 (batch fixtures).
- **Wave 2:** FA12 (rung declaration), FA15 (runner), FA18 (bug graph).
- **Wave 3:** FA16 (prompt-file flag).
- **Wave 4:** FA17 (verification), FA23 (dark-factory.js archive).
- **Wave 5:** FA19 (bug-resolver, depends on EV4), FA21 (batch runner).
- **Wave 6:** FA22 (held, operator's go), FA24 (guard paths, then the switch).

No FA edge points at a sibling draft. The two outward edges (FA19 → EV4,
FA20 → FA2) are live keys.

---

## §8 The switch

Only FA24's `hook-guard.py` half changes the live seat (the `dsh-openrouter`
package: the `dsh-openrouter-pkg` list entry in `hosts/core/agent-prereqs.nix`,
the `harnessPackage` option in `nixosModules/seatLane.nix`);
its `orchestrator-guard.sh` half is live at integration
(the `FACTORY_HOUSE_GUARD` env var in `seatLane.nix`). After FA24 integrates:

1. `nix build .#nixosConfigurations.core.config.system.build.toplevel`
2. `nix store diff-closures /run/current-system ./result` — predicted delta:
   `dsh-openrouter` and its embedders (`system-path`, `etc`, the `seat@` unit.
3. `sudo nixos-rebuild switch` (operator's act).

No other FA task needs a switch (G1).

---

## §9 Tests and checks

Every task carries its own acceptance checks, named in the plan. The full
increment's drill (`docs/superpowers/plans/2026-09-11-factory.md` §Drill):

1. `nix build .#checks.x86_64-linux.unit -L --no-link`, then `factory-unit`,
   then `lint` — all green.
2. `factory-graph.py check .claude/workflows/bug.toml .claude/workflows/plan.toml`
   → exit 0, silent; on a copy with one edge target misspelled → one refusal
   line naming the node.
3. `factory-registry.py check` → exit 0; append one blank line to a shim →
   `check` prints `registry: <role>: drift`, exit 2.
4. `factory-run.py .claude/workflows/bug.toml --dry-run --input <fixture>
   --run /tmp/drill4` → node path with each edge's budget.
5. One real bug row through `bug.toml` capped at rung 1 → journal shows the
   re-resolver's verdict per claim and the gate's review filed under
   `docs/reviews/`.
6. A copy of `bug.toml` with every budget at 1 and a stub that always fails →
   run ends at the refusal node; `factory-artifact.py check` → exit 0.
7. After FA24's switch: a job seat given a one-line task "append a comment to
   `.claude/workflows/bug.toml`" → `dsh-openrouter --denials 1` shows the
   refusal.
8. `git ls-files tools/factory/dark-factory.js` → empty;
   `grep -c dark-factory flake.nix` → 0; `test -f tools/factory/archive/dark-
   factory.js`.
9. `test -s docs/research-2026-09-11-batch-draft-vs-planjs.md` and its table
   carries the batch node's row, `plan.js`'s row and the delta in score, dollars
   and turnaround.

---

## §10 Cross-plan touches

- **`flake.nix`** — FA23 removes ten dark-factory lines; may yield to a
  ready live key (HH6 today).
- **`docs/ledger/subsystems.toml`** — FA13 appends to Factory's `owns`.
- **`docs/MAP.md`** — regeneration only (G5's exemption).
- **`factory-lib.sh`, `factory-wave`, `factory-task`** — FA12, FA16 × DF7, DF8
  (defects plan); DF7, DF8 before FA12.
- **`factory-review`** — FA17 alone.
- **`tools/orchestrator-guard.sh`, `tests/lane/`** — FA24 (Isolation).
- **`pkgs/dsh-openrouter/hook-guard.py`** — FA24 (Seat/Harness).
- **`docs/research-*`** — FA22 (Knowledge).

---

## §11 Sources

- `docs/concepts/2026-09-09a-redesign-charter.md` — the program charter.
- `docs/decisions/2026-09-09-redesign-answers.md` — the 80 answers and three
  amendments.
- `docs/context/factory.md` — the Factory context block, measured at HEAD.
- `docs/research-2026-09-11-batch-lane.md` — FA2's measurement report.
- `docs/superpowers/plans/2026-09-11-factory.md` — the Factory plan.
- `docs/ledger/subsystems.toml` — the subsystem manifest, Factory row.
- `docs/ledger/rules.toml` — the rules, including the guard rules.
- `docs/ledger/routing.toml` — the routing table.