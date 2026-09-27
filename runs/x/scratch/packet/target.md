# Target: spec read

Spec: `docs/superpowers/specs/2026-09-06-operator-seat-driver-design.md`

Command: `wc -w docs/superpowers/specs/2026-09-06-operator-seat-driver-design.md`
Result: 2266 words

Size by rule S ≤ 1500, M ≤ 4000, L above: **M** (2266 ≤ 4000). Not refused.

## Full spec text

(reproduced in full, numbering added where the spec did not number a block)

# The operator's seat as the machine's driver — design (spec for review, 2026-09-06)

**Operator, 2026-09-06 ~08:55 CDT (verbatim):** "We need to get the DSH seat or
an alternative ready for immediate use as the driver of the machine. I am
wasting too many tokens talking to a fable agent when I could be talking to a
local one that routes what I need to the correct sources with fallbacks and
gradual escalation to higher thinking levels and more competent models with
the preexisting failure run as added context. This should be a data driven
pattern that isolates variables and documents over time the performance of
various models in the system at tasks which all need to be technically
classified. It's hard because fable produces tangible results and others
often do not."

**Context the same morning:** the Claude weekly limits stood at 90 % (all) and
96 % (scoped), resetting 2026-09-07 07:00 UTC; OpenRouter held $32.23 and the
operator never preloads more than $100; SB5, SB6 and Helm Home sub-project 1
are held. Switch #20 is built (host-core recorded green at a2667bc).

**Goal.** The operator talks to a seat on core, not to Fable. That seat
dispatches the machine's work through the existing pipeline and climbs a
declared ladder of models and efforts only when a rung fails, carrying the
failed attempt forward as context. Every attempt is recorded with the
variables that produced it, so "Fable produces tangible results and others
often do not" becomes a measured column per model per task class.

**Invariants touched:** brief §3.2 and §3.3 (the driver seat runs behind the
seat broker like every seat; nothing new leaves the machine), §3.5 (every
routing choice stays a repo file reviewed in a diff). No basket, no new
credential, no new egress host.

## What exists (reused, not rebuilt)

- **The seat lane** (`nixosModules/seatLane.nix`, SB1–SB4b, live after
  switch #20): `seat@<job>` runs as the operator inside `egress-seat`, the
  broker injects the key, the web UI is reachable at `http://10.100.4.2:<port>`
  from the host only (a unit-owned forwarder; nftables allows the
  `webPortRange` alone). `seat-submit {headless|web} --workspace --dsh-home
  --model --effort [--brief] [--port] [--timeout]` (`pkgs/seat/seat-submit.py`)
  writes the job directory and starts the unit.
- **The interactive seat** the operator opens today: `dsh-openrouter` (web
  mode by default, `--headless`, `--broker`, `--bind-namespace`), default
  model `deepseek/deepseek-v4-pro-0813`, its saved selection untouched by
  anything automated (decision addendum 2026-09-05 in
  `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md`, point 1).
  The routing table's header says the interactive seat is not governed by it.
- **The routing table** `docs/ledger/routing.toml`: `[[route]]` rows keyed on
  route × role × kind × size → model, effort; most specific row wins; explicit
  overrides win; no `plan` row; Kimi K3 and GLM 5.3 have no row until a
  measurement justifies one. `factory_route` (pure bash) and `route.py`
  (python) are cross-checked by `factory-unit`. The dsh harness resolves every
  sub-agent model through it and its whole-tree gate refuses "any per-dispatch
  tier-escalation wording" in prompts, READMEs and skills
  (`~/flakes/dsh-harness/README.md`, "The routing table stays the one place a
  model is chosen").
- **The driver** `tools/factory/seat`: `factory-dispatch` asks the derived
  graph, `factory-task` runs one typed task in an isolated workspace,
  `factory-integrate` records every check it runs, `factory-plan` runs a
  headless planning seat whose draft the orchestrator's panel judges
  (`.claude/workflows/plan.js`, judgeOnly). Each `.result` carries `model:`,
  `effort:`, `route: explicit|role/kind/size`, `usage:` and the status line.
- **Rule A1**: one bounded fix round `<KEY>b`, then a re-plan `<KEY>r`; the
  fix round's section carries every rejection item (planning design §3 and
  anticipation row A12). The seat sees only Global Constraints, Assumptions
  and its own section.
- **The relaunch decision** (telemetry decisions, answer 3): automatic relaunch
  for exactly three failure classes — credit outage once credits are recorded
  restored, provider error once, boot failure once; every other class waits.
  The table form is telemetry design §4.3 (task T15, not yet planned).
- **The record**: the evidence store holds `checks.jsonl` and
  `helm-status.jsonl` today; the telemetry design (1473a22, T1–T18 approved,
  unplanned) adds the `tasks` and `gates` streams, the n ≥ 5 join helper and
  `evidence report routing|compare` (§4.1, §4.6). The plan-defect ledger
  classifies rejections (missing-case 20, vacuous 15, wrong-fact 9,
  underspecified 9, implementer 7, process 1).
- **Task typing**: `### KEY (code|docs, XS|S|M|L) — title` (tasks.py, the
  heading regex), `touches` per section, acceptance from `docs/MAP.md` check
  names. Nothing finer than kind × size exists.
- **The Claude route**: `route = "claude"` rows run through the Workflow tool
  in the operator's Claude Code session on the subscription; they are
  unreachable from any seat. Anthropic models on OpenRouter: operator hold
  (seat-behind-broker spec, "Not in this spec"; parked-factory decision,
  point 3).

## Design

1. **The driver seat is a `drive` job on the existing unit.** No new unit, no
   widening: `seat-submit web` gains a job mode `drive` that differs from
   `web` in exactly two things — its DSH_HOME carries the driver's skill set
   (the `planning` skill, the routing block, and a new `driving` skill that
   names the four verbs: brief, dispatch, gate, integrate — each a call to
   the existing driver scripts, never a hand implementation) and its model and
   effort come from a new row `route = "openrouter", role = "orchestrate"`
   instead of the saved picker selection. The operator opens
   `http://10.100.4.2:<port>` and talks. The interactive seat outside the
   unit is unchanged (the 2026-09-05 addendum stands); "immediate use" is
   switch #20 plus one `seat-submit web` job, which SB5's runbook already
   owes; this spec adds the `drive` mode after it.

2. **The driver never runs anything on the host except through a spool.** A
   unit inside `egress-seat` cannot be trusted to reach systemd's control
   socket, and must not be: the driver submits work with `seat-submit
   --no-start` into `/var/lib/seat/jobs/`, and a host-side `seat-spool.path`
   unit (Nix-declared, root-owned, watching the jobs directory) starts
   `seat@<id>` for every new job whose `job.json` validates. The spool starts
   units and nothing else; it is the one host-side actor and it is asserted
   in `seat-eval` (its `ExecStart` is exactly the start of one template
   instance; no shell). The driver's own guard is `hook-guard.py`'s deny-only
   rule set plus the orchestrator guard's rules ported as one shared rule
   file both guards read, proven by the existing sweep fixture
   (`tests/unit/91-orchestrator-guard.bats`) running against both.

3. **The ladder is data in the routing table.** A `[[route]]` row gains an
   optional integer `rung` (default 1) and an optional `fallback = "<model>"`.
   Rows with the same route × role × kind × size × class and rungs 1..n form
   that key's ladder. `factory_route --rung N` returns the rung-N row (rung
   > n: "ladder exhausted", exit 3, never a silent default); `route.py check`
   refuses a ladder where two adjacent rungs change more than one of
   {model, effort} (one variable per step, so every climb is a measured
   comparison), and refuses a `fallback` naming a model with no row of its
   own. The climb is bound to rule A1, not added to it: attempt 1 = rung 1;
   the fix round `<KEY>b` = rung 2; the re-plan `<KEY>r` = rung 3. The
   fallback is sideways, not up: the three relaunch classes of the telemetry
   decision relaunch the same rung on `fallback` when it is set, else the
   same model. No prompt, README or skill names a tier; the harness's
   whole-tree gate keeps holding. First rows, each citing its measurement or
   marked `unmeasured` in the claims file:

   | key | rung 1 | rung 2 | rung 3 |
   |---|---|---|---|
   | implement/code/S | Pro medium (today's row) | Pro high | claude implement (sonnet high) |
   | implement/docs/any | Flash off (today's row) | Pro medium | — |
   | review/any/any | Pro medium (today's row) | claude review (opus high) | — |
   | orchestrate (openrouter) | Pro high (Q1) | claude orchestrate (fable high) | — |

   A rung on the `claude` route is unreachable from the seat: the driver
   prints the Workflow launch line for the operator's Claude Code session
   (the Ship-phase pattern: launch lines it never runs) and records
   `escalate: claude/<role>` in the run; the operator pastes it or declines.

4. **The failed attempt travels with the next rung.** `factory-task` gains
   `--prior <run>/<KEY>`: the brief of the next rung carries a `## Prior
   attempt` block composed by the driver, never by the seat — the prior
   `.result`'s status, error class, `usage:` and `route:` lines; the
   rejecting review's numbered findings and its mutation-table survivors;
   `git diff --stat` of the rejected commit. Never a transcript or a log
   (the packet readers' rule). The block is recorded as `prior:` in the new
   `.result`. Rule A1's "every rejection item" is thereby mechanical, not a
   plan author's memory.

5. **Technical class, derived from `touches`, never typed.** A repo table
   `docs/ledger/task-classes.toml` maps path globs to classes
   (`nix-module`, `nix-check`, `bash-driver`, `python-evidence`,
   `js-workflow`, `bats-test`, `vm-test`, `docs-runbook`, `docs-plan`,
   `docs-board`); `tasks.py` assigns each task one primary class (most files
   matched; a tie goes to the earliest rule; no `touches` → `any`) and prints
   it in the brief; `factory-task` writes `class:` into the `.result`; the
   routing key gains `class` (default `any`, most-specific-wins unchanged).
   The heading grammar does not change; the guard's append-only rule is
   untouched.

6. **The record answers the operator's sentence.** The `tasks` stream row
   (telemetry T2, shape extended through the fence T1) carries `rung`,
   `class`, `prior`, `escalate`. `evidence report ladder` groups
   `tasks ⋈ gates` by (route, role, kind, size, class, model, effort, rung)
   and prints n, first-gate approved fraction, landed commits per attempt
   (the "tangible" column), fix rounds per landing, median wall and output
   tokens, and refuses any line at n < 5 (the existing rule). A row in
   `routing.toml`, a rung or a fallback changes only by a commit whose body
   cites a report line (the table's header rule, unchanged). The `.result`
   lines are the source of every variable; nothing is inferred from a run
   name (telemetry §4.6's refusal stands).

7. **What the driver may decide alone.** Dispatch of a ready task at rung 1;
   a sideways fallback in the three relaunch classes; a climb to rung 2 on a
   rejection; printing (never running) a `claude` rung's launch line; the
   board's queue block through `write-board`. Everything else stays the
   operator's: pauses, spend, switches, spec approval, a rung 3 re-plan's
   dispatch, any row change.

## Tests (red first)

- **unit (bats)**: `factory_route --rung 2 implement code S` prints the
  rung-2 row; rung 4 on a three-rung ladder exits 3; a fixture table whose
  rungs 1→2 change model and effort together is refused by `route.py check`;
  a `fallback` without a row is refused; the fix-round brief carries the
  `## Prior attempt` block with the review's numbered findings (mutant: drop
  the block → the assertion fails); `seat-submit drive --no-start` writes a
  `job.json` with `mode = "drive"` and starts nothing; the shared rule file
  denies every command in the orchestrator guard's sweep table under
  `hook-guard.py` too.
- **evidence-unit**: a task with `touches` under `nixosModules/` and
  `tests/` classifies `nix-module` by the tie rule fixture; a `tasks` row
  carries the four new fields; `report ladder` refuses n = 4 and prints the
  synthetic n = 5 table exactly.
- **factory-unit**: `route.py models` and `factory_route` agree on every
  rung of a fixture ladder; the dark factory's built-in map still matches
  the rung-1 `claude` rows.
- **seat-eval**: the spool unit's `ExecStart` starts exactly one template
  instance; the `drive` job inherits the template's `ReadWritePaths`
  unchanged (an assertion on the rendered unit, not a diff of prose).
- **seat-vm**: a `drive` job answers on `10.100.4.2:<port>`; from inside it
  `seat-submit headless --no-start` produces a job the spool starts, and that
  job's request reaches the fake upstream with the injected header; a job
  directory with an invalid `job.json` is never started.
- **lint**: the harness's whole-tree model-choice gate still prints nothing
  after the `driving` skill lands (run in `~/flakes/dsh-harness`).

## Questions for the operator (each with a recommendation and a default)

1. **The driver's own row** (`openrouter/orchestrate`). Recommendation: Pro at
   effort high, measured against Pro medium over the first five driver
   sessions through `report ladder`. Default if unanswered: Pro medium, the
   seat's saved default today.
2. **Anthropic models on OpenRouter as rungs.** Recommendation: keep the hold;
   the `claude` rungs stay on the subscription as printed launch lines, and
   the report will show whether they are ever reached. Default: hold.
3. **The class vocabulary.** Recommendation: derived from `touches` as in §5
   (nothing new to type, nothing for the guard to protect). Alternative: a
   third field in the heading, which touches the regex, the guard and the
   harness's skill. Default: derived.

## Risks weighed

- The driver seat is a DeepSeek session driving DeepSeek seats; a wrong
  dispatch costs OpenRouter dollars, bounded by the spool (one unit per
  validated job) and by rule A1 (two rounds, then the operator).
- The ladder's `claude` rungs are only as available as the operator's Claude
  budget; the report must show rung-3 demand or the design is a ladder to
  nowhere. Named as a gap (`ladder-rung3-demand-unmeasured`).
- Every row above rung 1 is unmeasured on day one; the claims file carries a
  row per unmeasured rung with a review date, and the header rule forbids
  quietly keeping a rung the report never justified.
- The dsh harness's model-choice gate could match a word this spec
  introduces (`rung`, `fallback`); the H-series task in that repo owns the
  alternation and is a `touches` conflict to sequence.
- `touches` is written by the plan author; a class derived from a wrong
  `touches` list is wrong. The integrator already refuses a task whose
  commit touches files outside its `touches`; the class is therefore as true
  as the landed diff.

## Not in this spec

Fronting the Claude Code session with a broker; Helm Home (held); Discord (a
basket, decided); the telemetry tasks T1–T18 themselves (their own plan, on
which §6 depends — the plan must sequence them); the media, gaming and
nixos-skill repos; Kimi or GLM rows (no measurement yet); any change to the
interactive seat the operator opens outside the unit.

## Files, options, checks and commands named — each read, anchor text pasted

- `nixosModules/seatLane.nix`
  Command: `find . -iname "seatLane*"`
  Result: `./nixosModules/seatLane.nix` (file exists in tree)

- `pkgs/seat/seat-submit.py`
  Command: `grep -n "seat-submit" pkgs/seat/seat-submit.py`
  Anchor: `    seat-submit [--jobs-dir DIR] [--no-start] {headless|web}`

- `docs/ledger/routing.toml`
  Command: `find . -iname "routing.toml"`
  Result: `./docs/ledger/routing.toml` (file exists in tree)

- `docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md`
  Command: `test -f docs/decisions/2026-09-03-openrouter-lane-permitted-transcripts.md && echo exists`
  Result: `exists`

- `tests/unit/91-orchestrator-guard.bats`
  Command: `test -f tests/unit/91-orchestrator-guard.bats && echo "exists: tests/unit/91-orchestrator-guard.bats"`
  Result: `exists: tests/unit/91-orchestrator-guard.bats`

- `pkgs/dsh-openrouter/hook-guard.py`
  Command: `find . -iname "hook-guard.py"`
  Result: `./pkgs/dsh-openrouter/hook-guard.py` (file exists in tree)

- `docs/ledger/task-classes.toml` (named in Design §5 as a new file the spec proposes to create — not yet in the tree)
  Command: `test -f docs/ledger/task-classes.toml && echo "exists" || echo "MISSING: docs/ledger/task-classes.toml"`
  Result: `MISSING: docs/ledger/task-classes.toml` — this is expected: the spec's Design §5 introduces it as new, it is not a claim about existing tree state.

- `pkgs/evidence/tasks.py` (`tasks.py`, "the heading regex")
  Command: `grep -n "def " pkgs/evidence/tasks.py`
  Anchor (first defs found): `89:def run(argv, timeout=20.0)`, `96:def chain_root(key)`, `101:def parse_keys(value)`, `110:def parse_list(value)`, `114:def parse_plan(path)`

- `docs/MAP.md` — named as source of "acceptance from `docs/MAP.md` check names"; not independently re-read beyond the spec's own reference (read-only scope of this drafting job did not require re-deriving check names).

- `evidence report routing|compare`, `evidence report ladder` — named commands (not-yet-implemented, per spec text, part of the telemetry design and this spec's Design §6); no `report ladder` subcommand found in `pkgs/evidence/report.py` today.
  Command: `grep -n "task-classes\|report ladder\|evidence report" pkgs/evidence/*.py`
  Anchor found: `pkgs/evidence/report.py:1:"""`evidence report plans` — the planning-agent metrics joined to first-gate outcomes (plan 2026-09-06-planning-agent, P10).`
  (Confirms `report plans` exists today; `report ladder`/`report routing`/`report compare` are prospective, as the spec itself frames them — "adds ... `evidence report routing|compare`" and Design §6's `evidence report ladder`.)

- Options/keys named in the routing table schema: `route`, `role`, `kind`, `size`, `class`, `rung`, `fallback` — these are TOML keys the spec proposes adding to `docs/ledger/routing.toml` (`rung`, `fallback`, `class` are new; `route`, `role`, `kind`, `size` are described as already existing in the table).

- Commands named without independent re-verification beyond the spec's own text (proposed/future behavior, not present-tree facts to confirm): `factory_route --rung N`, `route.py check`, `factory-task --prior <run>/<KEY>`, `seat-submit drive --no-start`, `write-board`.

## Decisions the spec leaves open

1. The driver's own routing row (`openrouter/orchestrate`): Pro effort high vs. Pro medium — spec recommends high, measured against medium over first five sessions; default if unanswered is Pro medium (Question 1).
2. Whether Anthropic models on OpenRouter become ladder rungs, vs. staying subscription-only printed launch lines — spec recommends keeping the hold; default is hold (Question 2).
3. The technical-class vocabulary's source: derived from `touches` (recommended) vs. a new third heading field — default is derived (Question 3).
4. Sequencing against the telemetry design's own (not-yet-planned) tasks T1–T18, on which this spec's Design §6 depends (noted under "Not in this spec").
5. Sequencing against the dsh-harness repo's H-series task, which must own introducing the words `rung`/`fallback` without tripping that harness's whole-tree model-choice gate (Risks section).
