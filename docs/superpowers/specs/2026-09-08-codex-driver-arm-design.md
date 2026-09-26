# The `codex` arm of the seat driver — design (spec for the planning agent, 2026-09-08)

**Operator, 2026-09-07 ~18:55 CDT:** "You may continue to use codex as an agent
and collect information about it." Decision
`docs/decisions/2026-09-07-codex-stays-an-operator-app.md`, point 4: the
mechanism is a `codex` arm of the seat driver, sequenced after the
seat-harness wave (SH4–SH6 touch the same driver and evidence files).

**Goal.** A Codex run is a row in `derived/tasks` like every seat's: the same
brief, grammar, demotions, `.result` and ingest, the session's own token
counters — so the brief shows DeepSeek and Codex side by side and the first
Codex task on `~/flakes/codex` lands through the driver, not around it.

**Invariants touched.** Brief §3 binds agents; a Codex task runs on the host
under `--sandbox danger-full-access` with the operator's rights, outside the
seat lane and the broker — accepted by the operator for Codex (the decision,
point 4; the sandbox flag was their choice, CX1b ~16:57). No key moves; no Nix
expression changes; the closure diff stays one line (`evidence: 69.8 KiB` at
`eb8d47d`).

## What exists (verified 2026-09-07 at eb8d47d)

- `tools/factory/seat/factory-task` has two launch arms: `seat-submit headless`
  when on PATH and `FACTORY_SEAT_UNIT` ≠ 0, else `dsh-openrouter --headless
  "$brief"` under `timeout -- "$timeout_s"` after `cd -- "$ws"` (`grep -n
  'seat-submit headless\|dsh-openrouter --model' tools/factory/seat/factory-task`).
  Both tee stdout into `$log`; the FACTORY-RESULT extraction, the SH2
  `unreported` arms and the CR3r demotions read `$log` and the branch, never
  the seat. `.result` lines: `run, key, model, effort, route, plan, workspace,
  [seat], branch, head, base, wall_s, exit_code, error_class, [derived]`, the
  commit log, the diffstat, `usage: <json>`. `FACTORY_SEAT` is read nowhere.
- The dsh usage JSON (`factory-usage.py`): `{"model","events","input",
  "output","cacheRead","reasoning","duration_s"}`; `input` excludes cache
  reads (sh2f/SH3b: `"input": 882612, "cacheRead": 7965440`). The ingest
  (`ingest_result.py`) maps `input→in, output→out, cacheRead→cache_read`;
  `effort` outside `off|low|medium|high|xhigh` → `unknown` (line 296);
  `route:` parses by `ROUTE_IMPL_RE = ^implement/(code|docs)/(XS|S|M|L)$` into
  `(route, task_kind, size)`, anything else → `unknown` ×3; the fence
  (`streams.py`, `task-result`) pins `route` to
  `^(explicit|unknown|implement/(code|docs)/(XS|S|M|L))$` and `model` to
  `MODEL_ID_RE` (`gpt-6-astra` matches). A `seat:` line other than `seat: unit
  seat@…` / `seat: submit failed` is ignored.
- `factory_error_class` (`factory-lib.sh`) greps the log's last 4,000 bytes
  for `402`+`budget_exhausted`, `502|503|529|upstream|provider`,
  `UNKNOWN_MODEL`, then `wall_s < 10 && events < 50` → `boot-failure` — only
  for a result line with a status other than `done` and no synth or demotion.
- `codex exec` 0.153.4 (`codex exec --help`): the prompt from stdin with `-`;
  `-c key=value` (a TOML value), `-m`, `--sandbox`, `--color never`,
  `--ephemeral` (no rollout). Measured 2026-09-07 19:40 with `--strict-config
  -c features.plugins=false -c 'otel.metrics_exporter="none"' --sandbox
  read-only --color never --ephemeral -`: exit 0; stdout is the banner
  (`OpenAI Codex v0.153.4`, `--------`, `workdir:`, `model: gpt-6-astra`,
  `provider: openai`, …, `reasoning effort: medium`, …, `session id:
  <uuid>`, `--------`), then `user` + the prompt echoed, `codex` + the reply,
  `tokens used`, a count, the final message once more.
- The rollout `~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<session id>.jsonl`
  (`CODEX_HOME` unset → `~/.codex`): `session_meta` first, one `turn_context`
  (`model`, `effort`), `event_msg` lines of `payload.type == "token_count"`
  whose `payload.info.total_token_usage` is cumulative — CX1b's last
  (`jq 'select(.payload.type=="token_count") | .payload.info.total_token_usage'
  <rollout> | tail -1`): `input_tokens 1710988, cached_input_tokens 1642368,
  output_tokens 13584, reasoning_output_tokens 3631`; the board's "82 k
  billed" is `(1710988 − 1642368) + 13584`; 239 lines.
- The brief's trailer (`factory-brief`, RULES): `Generated-By: dsh 0.1.2-rc.1
  / <model> (seat headless, factory run <RUN>)` then `Co-Authored-By: Claude
  Fable 5.1 <noreply@anthropic.com>`, byte-exact in
  `tests/unit/80-seat-driver.bats:94-97`, named in `factory-review:140`.
  CX1b's commits carry `Co-Authored-By: Codex CLI 0.153.4 <noreply@openai.com>`.
- `evidence tasks brief` (`tasks.py render_brief`) prints nothing per model.
  A section line `**repo:** <name>` attributes a task to another repo
  (`2026-09-05-harness-router.md:17`); `docs/ledger/repos.toml` has no `codex`
  row; the ingest's `repo` is the workspace origin's `…/base/<name>`.

## Design

1. **Selection.** `FACTORY_SEAT=codex` selects the arm in `factory-task`
   before the `seat-submit` test; unset or empty is today's behaviour, byte
   for byte; any other value refuses with exit 2 before a workspace or run dir
   exists (the `FACTORY_PLAN` guard's shape). `factory-wave` and
   `factory-dispatch` pass the environment through: a wave is Codex's whole,
   never per task. `factory_route` is not called under `codex`; a
   `route = "codex"` row is a later spec, after n ≥ 5 runs.
2. **The launch.** `cd -- "$ws" && printf '%s\n' "$brief" | timeout --
   "$timeout_s" codex exec -c features.plugins=false -c
   'otel.metrics_exporter="none"' --sandbox danger-full-access --color never
   [-m "$model"] - 2>&1 | tee -a -- "$log"` — the brief `factory-brief`
   prints, cwd the workspace clone (no `-C`, no `--skip-git-repo-check`),
   never `--ephemeral` (the rollout is the usage source), never `--json`.
   `--model ID` → `-m ID` and `route: explicit`; `OPENROUTER_MODEL` and
   `OPENROUTER_REASONING_EFFORT` are ignored with one logged warning each. No
   `DSH_HOME` is seeded. Exit 124 → `timeout`, as today.
3. **The `.result`.** `model:` and `effort:` are the banner's `model:` and
   `reasoning effort:` lines, falling back to `~/.codex/config.toml`'s
   `model` / `model_reasoning_effort`, then `unknown`. `route:
   codex/<kind>/<size>` from the heading, `explicit` with
   `--model`. `seat: codex <session id>` from the banner. The rest as today.
4. **Usage.** `tools/factory/seat/factory-codex-usage.py` (stdin = the
   rollout; stdout = one JSON object; never raises): `model` from
   `turn_context`, `events` = JSON lines, `input` = `input_tokens −
   cached_input_tokens`, `cacheRead` = `cached_input_tokens`, `output` =
   `output_tokens`, `reasoning` = `reasoning_output_tokens`, from the last
   `token_count` whose `info` is not null; `duration_s` = last − first
   `timestamp`. The rollout is the one named by the banner's session id
   (`find "${CODEX_HOME:-$HOME/.codex}/sessions" -name "rollout-*-<id>.jsonl"`)
   — two Codex tasks in one wave never share a file; without a banner, the
   newest rollout newer than the launch marker, else `{}` (events 0 → the
   boot-failure arm). CX1b: `input 68620, cacheRead 1642368, output 13584,
   reasoning 3631`.
5. **Error class.** `factory_error_class` is unchanged; the arm hands it a
   copy of the log holding only the agent's output: from the first line that
   is exactly `codex`, else after the banner's second `--------`. Reason: the
   banner's `provider: openai` and an echoed brief about `502`s would read as
   `provider-error`. Codex's own failure strings are unmeasured (no failure
   log exists); the first is classified by hand and its pattern added — a gap.
6. **The fence.** `ROUTE_IMPL_RE` and the stream regex gain
   `codex/(code|docs)/(XS|S|M|L)`; `SCHEMA.md`'s row says so; a CX1b-shaped
   fixture `tests/evidence/fixtures/results/codex.result`.
7. **The trailer.** Under `FACTORY_SEAT=codex` `factory-brief` prints
   `Generated-By: codex-cli <ver> / <model> (codex exec, factory run <RUN>)`
   and `Co-Authored-By: Codex CLI <ver> <noreply@openai.com>` — CX1b's shape,
   so the flake's history stays uniform and the trailer names the author;
   `<ver>` from `FACTORY_SEAT_VERSION`, set by `factory-task` from `codex
   --version` (`codex-cli 0.153.4` → `0.153.4`), the literal `<version>` when
   unset. Without `FACTORY_SEAT` the output is byte-identical to today.
   Rejected: keeping `Co-Authored-By: Claude Fable 5.1` — false of the commit.
8. **Side by side.** `render_brief` gains one line after the record:
   `**Seats (7 d):** <model>: <n> runs, <done> done, <median wall> min,
   <in+out> billed · …` from the `.result` files under the runs root whose
   mtime is within 7 days (never a log), models by runs then name, `none`
   when empty. `docs/ledger/repos.toml` gains `[[repo]] name = "codex",
   path = "~/flakes/codex"` so a section with `**repo:** codex` resolves
   `landed` against the flake's log.

## Tasks (the plan types them; sizes are the author's estimate)

- **CA1 (code, S)** — items 1–7: `factory-task`, `factory-brief`,
  `factory-codex-usage.py` (new), `streams.py`, `ingest_result.py`,
  `SCHEMA.md`, the fixture, `tests/unit/95-codex-arm.bats` (new; a fake
  `codex` on PATH records argv, cwd and stdin, prints the banner and a block,
  writes a fake rollout under a test `CODEX_HOME`),
  `tests/evidence/test_codex_usage.py` (new), `test_ingest_result.py`,
  `test_streams_policy.py`, the README. Acceptance: unit, evidence-unit,
  lint. Mutants: the arm chosen without `FACTORY_SEAT`; `-` dropped;
  `--ephemeral` added; `input` not net of cache; the newest rollout instead of
  the id; the raw log to the classifier; `Generated-By` unchanged under
  `codex`; `codex/any/any` accepted.
- **CA2 (code, XS)** — item 8: `tasks.py`, `test_tasks.py`, `repos.toml`.
  Acceptance: evidence-unit, lint. Mutants: a `.log` counted; an 8-day-old
  result counted; `billed` = in only.
- **CX2 (code, XS; `repo: codex`; dependsOn CA1)** — the CX1b MINORs on
  `~/flakes/codex` (`docs/reviews/2026-09-07-opus-review-cx1b-CX1b.md`,
  MINOR-1, -3, -4, -5): MAP.md complete with a currency check; precedence
  proven for `features.plugins` and the three `otel.*_exporter` keys; the
  three network-touching checks assert only pre-network output under a
  scratch `CODEX_HOME` with no auth and a `timeout` (decision: a check never
  dials `api.openai.com`);
  `config-precedence` skipped with a printed reason when `unshare -Ur true`
  fails. Run as `FACTORY_SEAT=codex FACTORY_PLAN=… setsid factory-wave cx2
  ~/flakes/codex "CX2"`; gated by `~/factory/bin/opus-gate.js`; landed by
  `factory-integrate`.

## Waves, touches, conflicts (the plan confirms with `tasks.py`)

[CA1 ‖ CA2] → [CX2]. CA1 and CA2 share no file. Both conflict with SH4/SH5
(`factory-task`, `factory-brief`, `streams.py`, `ingest_result.py`,
`tasks.py`) and SD2–SD4: dispatched only after SH6 lands.

## Operator steps

None: no switch, no unit, no key.

## Questions (defaults apply)

1. `Co-Authored-By: Codex CLI …` on Codex commits (item 7)? Default yes.
2. `route: codex/<kind>/<size>` rather than the bare `codex`? Default yes:
   the row keeps its class.

## Risks weighed

`danger-full-access` on the host (accepted, the decision); a run editing
outside the workspace — SH3's `touches` enforcement and the integrator's
refusal hold for every seat; the rollout format drifting with the app's
self-update — the usage script never raises, and `events` 0 on a long run
shows as `boot-failure`.

## Not in this spec

A `route = "codex"` routing row and per-task mixing; the ladder (SD1, SD3);
Codex under the seat lane or broker; Codex on core (parked).
