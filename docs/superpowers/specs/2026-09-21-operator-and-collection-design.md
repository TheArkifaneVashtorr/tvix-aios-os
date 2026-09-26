# The operator as a variable, and the six things the seat and driver do not record (2026-09-21)

Design, 2026-09-21. Subsystem: Evidence (EV, gate sonnet). Size M. Approved in scope by the operator in session 2026-09-21 ("we need to always be collecting data on the seat and driver; you need to start managing me as a variable"; scope answer: one EV spec for both halves). Grounded in `pkgs/evidence/SCHEMA.md`, `pkgs/evidence/streams.py`, the three ingest writers, `pkgs/broker/policy.py`, `docs/ledger/task-status.toml`, `pkgs/evidence/tasks.py`, and the store itself as read on 2026-09-21.

## 1 The numbers this serves

Three numbers, none measurable today, each printed by `evidence bundle` when this lands:

1. **Operator decision latency** — hours from a key becoming ready-but-held to the operator's go, and the age of every word still owed. Today's unrecorded points: PLAN-FA/PL/SA held since 2026-09-16 (5 days, in memory only); two switch latencies on 2026-09-21 derivable from `helm-status` drift rows, 11:31:57Z fail → 15:38:06Z ok (4 h 06 m) and 16:19:23Z fail → 19:41:09Z ok (3 h 22 m).
2. **Attributable spend** — the share of `ledger/openrouter-usage` dollars joined to a `(run_id, key)`. Today 0 %: the usage row carries neither (`policy.py:233-269`); the "USD per approved task" in this session's seat digest was a model-level average.
3. **Attributable verdicts** — the share of `derived/gates` rows that name their reviewer model and rung. Today every seat-lane row says reviewer `deepseek` by a literal (`ingest_reviews.py:240`), `model` is null on 372 of 562 rows, `rung` is not a field, and 35 of 202 rejected rows join to no task.

A recommendation about seats that cannot cite 2 and 3 is taste. A plan about the operator that cannot cite 1 is memory. Both were the case this afternoon.

## 2 Scope

Six tasks, all inside the Evidence subsystem's `owns` (`pkgs/evidence/*`, `docs/ledger/*.toml`, the evidence-store skill) plus one broker line and two seat-driver lines named in §4. No new service, no new port, no egress change. The `ledger/operator` stream (§3.3) is the only new stream; everything else is a field or a state added to a declared kind.

Out of scope: budgeting the operator's attention (asks per day, scheduling around presence). That needs the latency numbers first; it is the next spec, not this one.

## 3 Design

### 3.1 `held` is a recorded state (T1)

`docs/ledger/task-status.toml` gains a third status. A row:

```toml
[[task]]
repo = "nixos-agent-env"
plan = "2026-09-11-factory.md"
key = "PLAN-FA"
status = "held"
since = "2026-09-16"
note = "operator: planning runs wait for the effort decision"
```

Rules: `held` requires `since` (a date); `withdrawn` and `parked` keep `decided` as today (`task-status.toml:10-15`). A release is recorded, not deleted: the row's status becomes `released` with `released = "<date>"`, so the latency is `released − since` and history is in the row, not in git archaeology. `pkgs/evidence/tasks.py` adds `held` and `released` to `STATES` (`tasks.py:105-118`) and extends the validator arm that today accepts only the `withdrawn`/`parked` pair (`tasks.py:2139-2144`). A held key is excluded from the next wave and printed in the brief under a new line, `**Held (operator):** PLAN-FA since 2026-09-16 (5 d) · …`, replacing today's `**Operator owns:** none`, which is wrong. `evidence tasks json` exposes `held_since` and `released` per task so §3.2's report can read them.

The first three rows are PLAN-FA, PLAN-PL, PLAN-SA with `since = "2026-09-16"`. They are a plan-mandated hand edit: the auto-mode classifier refuses ledger commits (field lesson 2026-09-14), so the orchestrator writes the rows and the operator commits the ledger diff.

### 3.2 Operator latency is a report, derived (T2)

`evidence report operator` (new subcommand in `pkgs/evidence/report.py`) prints two tables and one line:

- **Switch latency** — pairs of `helm-status` rows with `reason = "change"` where the `drift` tile goes `fail` then `ok`; columns fail-at, ok-at, hours. Source: the eight rows quoted in §1, `pkgs/helm/collect.py:512` (`tile_drift`).
- **Held keys** — from `evidence tasks json`: key, since, released or open, days.
- One bundle line: `**Operator:** last switch 3 h 22 m; held 3 keys, oldest 5 d; asks 7 d: N, answered N, median M min` (the asks column is null until T3 lands and says so).

The recipe also lands in `.claude/skills/evidence-store/references/queries.md` so a reader can re-run it without the subcommand.

### 3.3 The `ledger/operator` stream (T3)

Kind `operator-ask`, key `(session, ask_id)`. Fields, all declared in `streams.py` per SCHEMA.md's refusal rule (`SCHEMA.md:11-15`):

| field | type | note |
|---|---|---|
| `session` | 16-hex | a hash of the harness session id, never the id |
| `ask_id` | 16-hex | one per AskUserQuestion call |
| `phase` | enum `ask` \| `answer` | two rows per question |
| `header` | string ≤ 12 chars | the tool's chip label, e.g. `Scope`; the only text stored |
| `options` | int | choices offered |
| `recommended_index` | int, nullable | which option carried "(Recommended)" |
| `chosen_index` | int, nullable | at `answer`; null when the operator typed Other |
| `took_recommended` | bool, nullable | at `answer` |
| `latency_s` | int, nullable | at `answer`: answer ts − ask ts |
| `key` | task or plan key, nullable | when the ask concerns one |
| `surface` | enum `chat` \| `run-button` \| `helm` | where the answer came from |

No question text, no option text, no answer text. Decision 18b's rule for `ledger/engagement` (`SCHEMA.md:46`, a string field is a decision, not a task) is adopted for this kind: `header` is the one string, bounded to 12 characters, and the validator refuses any other.

Writer: a `PostToolUse` hook matched on `AskUserQuestion`, beside the existing `UserPromptSubmit` hook (commit c2ab844), calling `evidence append operator` with the tool's input (options, recommended index, header) and output (chosen index). The hook is the writer so the row is emitted by the harness, never typed by the orchestrator. If the hook cannot see the tool output on this harness version, the `answer` row is written by the orchestrator through the same subcommand and the row carries `src = "orchestrator"` so the two provenances stay distinguishable; the probe that decides this is the task's first step and its result is a plan fact.

What this measures: how many decisions per day reach the operator, how often the recommended default is taken (a number the "always provide recommendations" rule can be judged by), and how long each answer takes.

### 3.4 Spend rows carry the task (T4)

The broker's usage record is built from the HTTP exchange only (`policy.py:233-269`); the seat's `FACTORY_KEY`, `FACTORY_RUNG`, `FACTORY_NODE` (`factory-lib.sh:1799`) and `FACTORY_RUN` never reach it. Two attributions, both landed, with an `attribution` enum on the row:

- `header` — the seat sends `x-factory-task: <run_id>/<key>` on every request; `policy.py` copies it into `run_id` and `key` (both nullable, task-key regex) and drops the header before forwarding upstream. Precondition, measured first: whether dsh-openrouter passes a configured extra header through to the broker. The probe is a broker unit test plus one seat request with the header set through the wrapper's config; its result decides whether this arm ships in this task or is filed as a dsh-harness task.
- `window` — `ingest_openrouter_usage.py` joins a row without a header to the single `derived/tasks` row of the same `instance` whose `[ts, ts + wall_s]` contains `ts_epoch`. Zero or more than one candidate → `attribution = "none"`; the seat cap of 9 concurrent runs makes ambiguity real, and the report prints the none-share rather than hiding it.

`evidence report ladder` and the seat digest then print USD per approved task per model from joined rows only, with the attributed share beside it.

### 3.5 Gate rows name their reviewer and rung (T5)

`factory-review` writes two header lines into `<KEY>.review.md`, `reviewer-model: <model-id>` and `rung: <n>`, from the routing lookup the driver already performs (it exports `FACTORY_RUNG`). `ingest_reviews.py` parses both; the literal `"deepseek"` at line 240 goes; `reviewer` is derived from the model id (`glm` joins the enum `opus|sonnet|deepseek|fable|unknown`, `streams.py:378-406`), `model` is set, and a new nullable int `rung` is declared. A review file without the lines yields `reviewer = "unknown"`, never `deepseek`. Old files are not backfilled; the report prints the unknown share.

### 3.6 Task rows always carry effort, size, area (T6)

`.result` gains an `area:` line, written by the driver from the key's prefix through `docs/ledger/subsystems.toml`; `ingest_result.py` parses it into a new `area` field whose enum is the manifest's area list plus `unknown`. For `route: explicit` (`ingest_result.py:87-95`), size and task kind are read from the plan section's typed heading instead of defaulting to `unknown`, since the heading carries them; `effort` unknown is kept only when the driver truly did not set one. The report prints the unknown share per field per week, so the number that motivated this (151 of 567 effort unknown, 184 of 567 size unknown) is watched, not remembered.

## 4 Where it lands

| task | files touched |
|---|---|
| T1 | `docs/ledger/task-status.toml`, `pkgs/evidence/tasks.py`, its unit test, three ledger rows |
| T2 | `pkgs/evidence/report.py`, `pkgs/evidence/bundle` line, `.claude/skills/evidence-store/references/queries.md`, unit test with the eight drift rows as fixture |
| T3 | `pkgs/evidence/streams.py`, `SCHEMA.md`, a new `evidence append operator` subcommand, the PostToolUse hook, unit test |
| T4 | `pkgs/broker/policy.py`, `tests/broker/test_usage_log.py`, `pkgs/evidence/ingest_openrouter_usage.py`, `streams.py` fields `run_id`, `key`, `attribution`, the seat wrapper's header config if the probe passes |
| T5 | `tools/factory/seat/factory-review`, `pkgs/evidence/ingest_reviews.py`, `streams.py`, unit test with a fixture review file |
| T6 | `tools/factory/seat/factory-lib.sh` (the `.result` writer), `pkgs/evidence/ingest_result.py`, `streams.py`, unit test |

The new spec file is covered by the publish manifest's existing glob (`docs/ledger/publish.toml:67`); no manifest row. No `subsystems.toml` change: the EV row has no specs field and every touched path is already in its `owns`.

## 5 Red before green

Every task opens with the check that fails today, shown red before the change:

- T1: `evidence tasks check` accepts a `held` row (today it errors on any status but the pair, `tasks.py:2139-2144`); negative control: a `held` row without `since` is refused.
- T2: the fixture of eight drift rows yields exactly two pairs, 4 h 06 m and 3 h 22 m; a fixture with a fail and no later ok yields an open row, not a pair.
- T3: `streams.validate("operator-ask", row)` refuses a row with a `question` field, and refuses a `header` longer than 12 characters.
- T4: a broker request carrying `x-factory-task` produces a usage row with `run_id` and `key` and an upstream request without the header; the window join marks two overlapping candidates `none`.
- T5: a review file without `reviewer-model:` ingests as `unknown`; one with `rung: 2` ingests `rung = 2`.
- T6: a `.result` with `area: evidence` ingests `area = "evidence"`; an `explicit` route with a typed heading `S` ingests `size = "S"`.

## 6 Sequencing

Wave 1: T1 ‖ T2 ‖ T5 ‖ T6 (independent, all S). Wave 2: T3 (S, needs the hook probe) ‖ T4 (M, needs the header probe). T2's asks column stays null until T3 lands and says so in the output.

## 7 Risks, named

- **Privacy of the operator stream.** Mitigated by design: one bounded string, hashes for ids, and the validator as the guard. Residual: the `header` chip could be chosen to leak; the reviewer checks the chips the orchestrator uses.
- **Window attribution under concurrency.** Up to nine seats share one instance; the `none` share is printed, and the header arm is the real fix. If the probe fails, T4 lands the window arm and files the header arm against dsh-harness.
- **`held` rows are ledger commits.** The classifier refuses them from the orchestrator; every hold and release is an operator commit, which is itself a measured operator action and should be the first row T3 sees.
- **Backfill.** T5 and T6 do not rewrite history; the unknown shares stay visible so the record does not pretend.

## 8 Open operator questions

1. Text-free operator stream, as designed. Recommended: yes; the number wanted is count, latency and recommendation uptake, and none needs the text.
2. The three initial `held` rows for PLAN-FA/PL/SA with `since = "2026-09-16"`. Recommended: yes, so the first latency measurement is the one already running.
3. T4's header arm depends on the probe, not on the operator; no question.
