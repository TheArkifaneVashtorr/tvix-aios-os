---
plan_defect: none
mutants_total: 23
mutants_killed: 20
mutants_outside_named: 8
model: opus
---
# Opus gate — seat run sp67, task SP7 — APPROVED

## Summary

Reviewed in a fresh clone of `task/SP7` (`/tmp/claude-1000/-home-dalhaka-nixos-agent-env/2d3f1237-59b4-4836-b7dc-17bd99301bc8/scratchpad/gate/sp67-SP7/gate-sp67-SP7`, base `ced500a`, head `d7f9dcd`). All 23 contract items of the section are met at the code level; both acceptance checks are green on `--rebuild`; 14 of the 15 mutants the section names die, the survivor being an equivalent mutant the plan's own fixture value cannot discriminate; 6 of 8 further mutants I invented die.

The privacy invariant was judged hardest, at the level the orchestrator named. **The identity refusal operates on the DATA POINT's and the LOG RECORD's own attribute lists, not on the resource** (`pkgs/evidence/ingest_otel.py:64-87`, called from `_data_point_row` at `:136` and `_log_record_row` at `:206`), which is the level Claude Code actually attaches identity to. Mutating the rule away (both the "exact list of four keys" form the section names and a "resource-only" form I invented) turns the suite red. The refusal prints the attribute KEY and never its value (`:77-80`), so no identity reaches stderr either.

Fitness against reality, not only fixtures: `/var/lib/opentelemetry-collector` on core is **empty** at gate time (`ls -la`, dir mtime 22:55) — the live collector has written no file since switch #23, so nothing on disk could be compared. I therefore reproduced it: I ran `otelcol-contrib 0.151.0` (the same store path the host config uses) in the scratchpad under a config that mirrors `nixosModules/claudeTelemetry.nix` byte-for-byte in its processors, POSTed a Claude-Code-shaped OTLP/HTTP JSON payload carrying `organization.id`/`user.email`/`user.id` on the data points and on the log record, and ran **this branch's ingest over the collector's real output file**:

```
ingested 3 rows into ledger/otel-claude (0 refused, 1 skipped)   EXIT=0
{"…","model":"claude-opus-5","model_suffix":"1m","sample":"tokens","sample_id":"tokens:cacheRead:claude-opus-5:1m:1788906253213778862","token_type":"cacheRead","value":17584,"harness_version":"2.1.258","terminal_type":"probe","at":"2026-09-08T22:24:13.213778Z","session_id":"sess-probe"}
{"…","sample":"tokens","sample_id":"tokens:input:claude-opus-5:1m:1788906253213778862","token_type":"input","value":10}
{"…","sample":"request","sample_id":"req_probe","request_id":"req_probe","cost_usd":0.0123,"input_tokens":2,"output_tokens":77,"cache_read_tokens":1000,"cache_creation_tokens":500,"duration_ms":1200,"query_source":"main","agent_name":"gate-reviewer","skill_name":"code-review","speed":"medium","effort":"high"}
```

The fixtures are faithful: the real file carries the same typed wrappers (`intValue` a decimal string, `doubleValue`, `stringValue`), `timeUnixNano` as a decimal string, `sum.dataPoints`, the same resource/scope nesting; the only real-file key the fixtures omit is `startTimeUnixNano`, which the ingest ignores. This is **not** the OL2 failure class — the assumed record shape exists in a real file, and the code reads it. The collector's own allowlist dropped all four identity keys at the data-point and log contexts, and `filter/events` dropped the `user_prompt` record, so in production SP7's identity refusal is a canary rather than a hot path — which is the correct posture.

Two things the operator should carry forward, neither of them SP7's fault (both are consequences of the section's own stated interface, and both are recorded as MINORs below): `claude_code.token.usage` is a **cumulative** sum (`aggregationTemporality: 2`), and the section's `sample_id` pins the export's `timeUnixNano`, so successive exports of the same counter land as separate rows — measured: 17584 then 31000 for the same `(session, model, type)`. Any downstream sum over `value` double-counts, the same hazard Assumption 7 designs against on the transcript side; SP4 must reduce with MAX per `(session_id, model, model_suffix, token_type)`, not SUM. And `claude_code.cost.usage` is skipped by design, so session cost comes only from `api_request` rows.

No MAJORs. APPROVED.

## Contract items

Every item taken literally from the section's Files / Interfaces / Facts.

| # | item | verdict | evidence |
|---|---|---|---|
| 1 | Create `ingest_otel.py`, `test_ingest_otel.py`, `fixtures/otel/{metrics,logs}.jsonl` | met | `git diff --stat`: all four created |
| 2 | `metrics.jsonl` line 1 (resource `service.version: "2.1.258"`; token.usage sum, two points `input`/`asDouble: 10`, `cacheRead`/`asInt: "17584"`; `model: claude-opus-5[1m]`, `session.id: sess-fixture`, `terminal.type: probe`, `timeUnixNano: "1788906253213778862"`; a `claude_code.cost.usage` metric) | met | `tests/evidence/fixtures/otel/metrics.jsonl:1` — verified field by field |
| 3 | `metrics.jsonl` lines 2–5 (`user.email`; `user.name`; no `session.id`; no `timeUnixNano`) | met | `metrics.jsonl:2,3,4,5` |
| 4 | `logs.jsonl` (a full `api_request` with `request_id: req_fixture`, `cost_usd: 0.0123`, `input_tokens: "2"`, `output_tokens: "77"`, `cache_read_tokens: "1000"`, `duration_ms: "1200"`, `query_source: main`, `agent.name: gate-reviewer`, `skill.name: code-review`; a `user_prompt`; `model: Claude-X`; no `request_id`; no `session.id`; no `timeUnixNano`) | met | `tests/evidence/fixtures/otel/logs.jsonl:1-6` |
| 5 | The kind declared exactly as the section's block | met | `pkgs/evidence/streams.py:612-644` — stream, `v`, key `("session_id","sample_id")` and all 23 fields identical (ruff rewrapped `token_type` only) |
| 6 | `INGEST_MODULES["otel"] = "ingest_otel"` | met | `pkgs/evidence/evidence.py:39` |
| 7 | `SCHEMA.md` carries the stream | met | `pkgs/evidence/SCHEMA.md:32` |
| 8 | `evidence ingest otel [--root DIR] <path>…`, `--root` default `/var/lib/opentelemetry-collector` | met | `ingest_otel.py:355-367` (`ot.add_argument("--root", default="/var/lib/opentelemetry-collector")`); end-to-end through the real CLI above |
| 9 | Every path realpath-fenced before any read; outside → `evidence: ingest otel: {p} is outside {root}`, exit 2, nothing written | met | `ingest_otel.py:292-298, 370-377`; `test_ingest_otel.py:232-233` asserts exit 2 and that the stream file does not exist |
| 10 | Unreadable path → `{p}: not an otel file`, refused | met (untested — MINOR-3) | `ingest_otel.py:304-309` |
| 11 | Torn last line → `{p}: last line torn (the collector is writing); skipped`, not refused | met | `ingest_otel.py:310-313, 343-348`; `test_ingest_otel.py:235-238` (exit 0) |
| 12 | One `replace_stream(store, "ledger/otel-claude", rows)` after every path is read | met | `ingest_otel.py:350-351`; the `if rows:` guard is SP8's idiom (`ingest_openrouter_usage.py:98`) and `evidence.replace_stream` itself no-ops on `[]` (`evidence.py:152-153`) |
| 13 | `--help` exit 0; `evidence ingest bogus` ends `…\|otel)`, exit 2 | met | `test_ingest_otel.py:240-255`, both via a real `subprocess` through `evidence.py` |
| 14 | Per line: an object with `resourceMetrics` or `resourceLogs`, else refused `not an OTLP export line` | met (untested — MINOR-3) | `ingest_otel.py:318-330` |
| 15 | `stringValue`/`intValue` (decimal string → int)/`doubleValue`/`boolValue`; any other wrapper → `attribute {key}: unsupported value type` | met (`boolValue` untested) | `ingest_otel.py:42-56, 82-85`; `test_ingest_otel.py:153-221` plants `arrayValue` |
| 16 | Identity rule: first `.`-token `user` or `organization` → row refused `{key}: identity attribute present (the collector's allowlist is broken)`; `user.name` and `organization.slug` refuse too | met (the `organization` arm untested — MINOR-2) | `ingest_otel.py:59-61, 76-81`; `test_ingest_otel.py:81-95` pins both `user.email` and `user.name` |
| 17 | No `session.id` → refused `session_id: missing` (point and record) | met | `ingest_otel.py:139-141` (point), `:209-211` (record); `test_ingest_otel.py:137, 258-264` |
| 18 | No numeric `timeUnixNano` → refused `timeUnixNano: missing` (point and record) | met | `ingest_otel.py:142-145` (point), `:212-214` (record); `test_ingest_otel.py:138, 265-266` |
| 19 | Every `claude_code.token.usage` point → a `tokens` row (`token_type` from `type`, `value` from `asDouble` or `int(asInt)`, `sample_id = tokens:{type}:{model}:{suffix or '-'}:{ns}`); other metrics skipped | met | `ingest_otel.py:152-184, 267-273`; `test_ingest_otel.py:61-78` (2 rows, `1 skipped`) |
| 20 | `event.name == api_request` → a `request` row, `sample_id = request_id`, absent → refused `request_id: missing`; every other event skipped | met | `ingest_otel.py:191-217, 227`; `test_ingest_otel.py:105-136` (`4 refused, 1 skipped`) |
| 21 | Model split at the first `[`; head must match `MODEL_ID_RE` else `model: not a model-id`; tail is `model_suffix`, absent → null | met | `ingest_otel.py:90-100, 147-149, 218-220`; `test_ingest_otel.py:73-74, 129, 135` |
| 22 | `at` by integer arithmetic (`…213778Z`, not `…213779Z`); `harness_version` = the resource's `service.version`; `terminal_type` from the point's/record's `terminal.type` | met | `ingest_otel.py:110-118, 121-129, 168-169, 232-233`; `test_ingest_otel.py:75-77, 130-132` |
| 23 | Stdout `ingested {n} rows into ledger/otel-claude ({refused} refused, {skipped} skipped)`; exit 0/1, 2 on OutsideRoot | met | `ingest_otel.py:378-382`; `test_ingest_otel.py:63-65, 107-109`, exit codes asserted in every test |

Field-name screen against `streams.FORBIDDEN` (Global Constraints): all 23 field names clean — the near-misses are `query_source` (not `query`), `model_suffix`, `agent_name`, `skill_name`; `user`, `email`, `slug`, `message` appear nowhere. Verified against `pkgs/evidence/streams.py:33-91`.

## Red before green

Base implementation files against the branch's tests, in a copy (`…/scratchpad/gate/sp67-SP7/mut`): `git checkout ced500a -- pkgs/evidence/streams.py pkgs/evidence/evidence.py && rm pkgs/evidence/ingest_otel.py`.

Step 1's stated red, both halves, reproduced verbatim:

```
$ nix develop -c pytest tests/evidence/test_ingest_otel.py -q
tests/evidence/test_ingest_otel.py:31: in _load
    src = next(p for p in candidates if p.exists())
E   StopIteration
ERROR tests/evidence/test_ingest_otel.py - StopIteration
1 error in 0.08s

$ nix develop -c pytest tests/evidence/test_streams_policy.py -q
E       assert ["undeclared kind 'otel-claude'"] == ['sample: not in enum (request|tokens)']
FAILED …::test_one_valid_row_per_kind_and_shape[otel-claude-row16]
FAILED …::test_one_valid_row_per_kind_and_shape[otel-claude-row17]
FAILED …::test_otel_claude_sample_enum_and_identity_fields
3 failed, 210 passed in 2.75s
```

Restored (head): `nix develop -c pytest tests/evidence -q` → `517 passed, 1 skipped in 13.27s`. The commit body's pasted red and green match what I measured line for line.

## Mutants

Named by the section — 15 (the Tests table's 14, plus Step 1's streams-policy mutant). Each applied to a pristine copy, one test run, then reverted.

| # | mutant | test | result |
|---|---|---|---|
| M1 | `int(float(dp["asInt"]))` for `asInt` | `test_metrics_two_tokens_rows` | **SURVIVED** — `1 passed` (see MINOR-1) |
| M1b | `float(dp["asInt"])` (the killable reading of M1) | same | killed — `E AssertionError: assert <class 'float'> is int / where <class 'float'> = type(17584.0)` |
| M2 | `_model_split` at `]` | same | killed — `assert 'ingested 2 rows … (4 refused, 1 skipped)' in 'ingested 0 rows … (6 refused, 1 skipped)'` |
| M3 | `fromtimestamp(ns / 1e9)` in `_at` | same | killed — `E AssertionError: assert '2026-09-08T22:24:13.213779Z' == '2026-09-08T22:24:13.213778Z'` |
| M4 | the point's `session_id: missing` arm dropped silently | `test_ingest_otel.py` | killed — `E AttributeError: 'NoneType' object has no attribute 'get'` |
| M4b | the point's `timeUnixNano: missing` arm dropped silently | same | killed — same `AttributeError` |
| M5 | identity as an exact list of the four known keys | `test_identity_attributes_refused` | killed — `E assert "user.name: identity attribute present …" in '…'` (out becomes `ingested 3 rows … (3 refused, 1 skipped)`) |
| M6 | `intValue` kept as a string | `test_logs_one_request_row` | killed — `assert 'ingested 1 rows … (4 refused, 1 skipped)' in 'ingested 0 rows … (5 refused, 1 skipped)'` |
| M7 | `user_prompt` mapped as well | same | killed — `… in 'ingested 1 rows … (5 refused, 0 skipped)'` |
| M8 | the record's `session_id` arm skipped instead of refused | `test_ingest_otel.py` | killed — `… in 'ingested 1 rows … (3 refused, 2 skipped)'` |
| M8b | the record's `timeUnixNano` arm skipped instead of refused | same | killed — `… in 'ingested 1 rows … (3 refused, 2 skipped)'` |
| M9 | `evidence.append` per row instead of `replace_stream` | `test_two_runs_same_rows` | killed — `E AssertionError: assert 4 == 2` |
| M10 | the unsupported wrapper ignored | `test_unsupported_wrapper_refused` | killed — `E AssertionError: assert 0 == 1` |
| M11 | the fence removed | `test_fence_torn_help_bogus` | killed — `E AssertionError: assert 0 == 2` |
| M12 | torn treated as not-JSON (`torn_last = False`) | same | killed — `E AssertionError: assert 'last line torn' in '…'` |
| M14 | `"sample": "id"` (Step 1's mutant) | `test_otel_claude_sample_enum_and_identity_fields` | killed — `E AssertionError: assert [] == ['sample: not in enum (request\|tokens)']` |

Outside the section's list — 8 (M1b above plus these 7):

| # | mutant | result |
|---|---|---|
| O1 | the identity check disabled at the point/record level (i.e. a rule that inspects only the resource) | killed — `assert 'ingested 2 rows … (4 refused, 1 skipped)' in 'ingested 4 rows … (2 refused, 1 skipped)'` — **the orchestrator's leak scenario is covered** |
| O2 | `organization` dropped from `_is_identity` | **SURVIVED** — `7 passed` (MINOR-2) |
| O3 | a non-token metric not counted as skipped | killed — `… in 'ingested 2 rows … (4 refused, 0 skipped)'` |
| O4 | `harness_version` read from `service.name` | killed — `E AssertionError: assert None == '2.1.258'` |
| O5 | the `request_id: missing` arm skipped instead of refused | killed — `… in 'ingested 1 rows … (3 refused, 2 skipped)'` |
| O6 | the explicit `MODEL_ID_RE` check dropped from `_log_record_row` | **SURVIVED** — `7 passed`; equivalent: `streams.validate` refuses the same row with the same string, the kind's `model-id` class doing the work (`streams.py:22`) |
| O7 | `token_type` always null | killed — `E KeyError: 'input'` |

**mutants_total 23, killed 20, outside_named 8.** The three survivors are all equivalent or coverage gaps, not live defects: M1 is arithmetically identical to the code for every value below 2^53; O6 is caught by the schema instead of the guard; O2 is the untested `organization` arm of a correctly implemented rule (MINOR-2).

## Checks

All run in the fresh clone.

| check | command | result |
|---|---|---|
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | **pass** — `evidence-unit> 518 passed in 13.86s`, exit 0 |
| lint | `nix build .#checks.x86_64-linux.lint -L --no-link --rebuild` | **pass** — exit 0 |
| ruff | `nix develop -c ruff check pkgs/evidence tests/evidence` | pass — `All checks passed!` |
| ruff format | `nix develop -c ruff format --check pkgs/evidence tests/evidence` | pass — `84 files already formatted` |
| repomap | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | pass — no diff (`docs/MAP.md` already regenerated in the commit: `tests/evidence — 94 files`) |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | pass — silent, exit 0 |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1, **not attributable** — every stage passes (treefmt, shellcheck, statix, deadnix, ruff, bats-chain, js-lint, store-writers, board shape, claims, tasks check) and it stops only at `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`, which drops `SP7` from the queue *because SP7's own commit now exists on this branch*. The hook's own comment says so: "a landed key leaves the queue, so staleness is by design" (`githooks/pre-commit:62-68`). Pre-commit was green when the seat ran it (before the commit existed); a board commit from a task branch is forbidden. Nothing owed. |

## Touches and commit

Section list: `pkgs/evidence/ingest_otel.py, pkgs/evidence/streams.py, pkgs/evidence/evidence.py, pkgs/evidence/SCHEMA.md, tests/evidence/test_ingest_otel.py, tests/evidence/test_streams_policy.py, tests/evidence/fixtures/otel/metrics.jsonl, tests/evidence/fixtures/otel/logs.jsonl` (+ `docs/MAP.md` by rule).

The diff is ten files: the eight above, `docs/MAP.md` (exempt), and one outside — `tests/evidence/test_ingest_openrouter_usage.py` (MINOR-0, disclosed).

Commit: exactly one (`d7f9dcd`, parent `ced500a`). Subject byte-identical to the section's (`diff` against the section's string: no output; 271 bytes each). Body states the why, pastes the red (`StopIteration`; `3 failed`) and the green (`517 passed`; `518 passed`; `lint … exit 0`) — all of which I reproduced. Trailers after a blank line, byte-identical to `tools/factory/seat/factory-brief:79-80`'s dsh pair:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sp67)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

No board commit (`docs/OPERATIONS.md` absent from the diff); the plan file untouched.

## Findings

**MINOR-0 — the one file outside `touches`, disclosed and necessary.**
`tests/evidence/test_ingest_openrouter_usage.py:122` — `assert r.stderr.rstrip().endswith("openrouter-usage)")` → `endswith("otel)")`. The commit body carries `Deviation: tests/evidence/test_ingest_openrouter_usage.py — …`. Judged on its merits: SP7's own contract requires `evidence ingest bogus` to end `…|otel)` (item 13), and `INGEST_TARGETS` is `"|".join(INGEST_MODULES)` (`evidence.py:41`), so adding the target necessarily invalidates SP8's pin — `evidence-unit` would be red without it. The edit is one line, keeps the assertion's strength (still pins the target list's tail), and belongs to this root. The driver's `touches_extra=1` is correct and the deviation is the right call. Nothing owed.

**MINOR-1 — the section's first named mutant is an equivalent mutant under its own fixture.**
`pkgs/evidence/ingest_otel.py:155` — `value = int(dp["asInt"])`. The section names "`int(float)` for `asInt`" as row 1's mutant; applied literally (`int(float(dp["asInt"]))`) with the section's own fixture value `"17584"`, the test passes:

```
### M1-int-float-asInt: rc=0
1 passed in 0.02s
```

`int(float("17584")) == 17584` exactly; the two forms diverge only above 2^53, which no token counter reaches. The test carries the strongest assertion available for this hazard — `assert type(by_type["cacheRead"]["value"]) is int` (`tests/evidence/test_ingest_otel.py:71`) — and the killable reading of the same mutant (`float(dp["asInt"])`) dies on it. This is a non-discriminating mutant in the plan's Tests table, not a hole in the seat's test. Recorded so the next section that reuses this row picks a fixture value the mutant can move.

**MINOR-2 — the `organization` arm of the identity rule has no fixture and no test.**
`pkgs/evidence/ingest_otel.py:59-61` — `return key.split(".", 1)[0] in ("user", "organization")`. The section's Interfaces state "`user.name` and `organization.slug` refuse too", and the collector really does put `organization.id` on every data point (my probe: the payload carried it, the allowlist dropped it). But no fixture line and no assertion carries an `organization.*` key, so narrowing the rule to `("user",)` alone survives the whole file:

```
### O2-organization-dropped: rc=0
7 passed in 0.18s
```

The code is correct; the coverage is not. Since privacy is the invariant and the plan's own §Global Constraints name `organization.id` among the identity attributes, a fixture line carrying `organization.id` (or `organization.slug`) belongs beside lines 2–3 of `metrics.jsonl`. Cheap to add in any later fix round; not gating, because the implemented rule already refuses it.

**MINOR-3 — three stated refusal paths have no test.**
`pkgs/evidence/ingest_otel.py:304-309` (`{p}: not an otel file` for an unreadable path), `:318-330` (`not an OTLP export line` for a line that is not an OTLP object), and the `boolValue` wrapper arm at `:56`. All three are stated in the section's Interfaces; none is exercised by `tests/evidence/test_ingest_otel.py`. Rule 7 MINORs. The code reads correctly in each case and I exercised the OTLP-line path indirectly (the torn fixture in `test_fence_torn_help_bogus` reaches `:322` with a valid object).

**MINOR-4 — a malformed data point crashes the run instead of refusing it.**
`pkgs/evidence/ingest_otel.py:132-134` returns `(None, [])` for a non-dict data point; `:331-342` treats "no reasons and not a skip" as success and appends the `None` into `rows`, which then reaches `evidence.replace_stream`. Measured:

```
$ python3 -c "… ingest_otel.main(['--store', …, 'otel', '--root', …, 'm.jsonl'])"   # dataPoints: ["oops"]
RAISED AttributeError 'NoneType' object has no attribute 'get'
```

Nothing is written, so no corruption — but the ingest dies with a traceback rather than printing a refusal, and the same shape is what killed mutants M4/M4b (they failed on the `AttributeError`, not on a count). The collector never emits this, no contract item covers it, and it is unreachable from a well-formed OTLP file; a defensive branch that returns a sentinel skip instead would close it.

**MINOR-5 — `test_otel_claude_sample_enum_and_identity_fields` tests no identity field.**
`tests/evidence/test_streams_policy.py:561-566` asserts only the `sample` enum. The name promises that the *kind* screens identity; it does not, and it need not — the identity rule lives in the ingest by the section's design. A reader auditing privacy from the policy test would be misled. Rename, or add the assertion the name implies.

**MINOR-6 — the cumulative counter lands as one row per export; SP4 must not SUM.**
`pkgs/evidence/ingest_otel.py:158` — `sample_id = f"tokens:{token_type}:{head}:{suffix or '-'}:{ns_raw}"`, exactly as the section's Interfaces specify. `claude_code.token.usage` is a cumulative sum (`aggregationTemporality: 2` in the fixture and in the real collector output), and SP3 sets `OTEL_METRIC_EXPORT_INTERVAL = "5000"`, so the same `(session, model, token_type)` re-exports its running total every five seconds under a new `timeUnixNano` — a new key each time. Measured against the real collector, two exports of one counter:

```
tokens:cacheRead:claude-opus-5:1m:1788906253213778862 17584
tokens:cacheRead:claude-opus-5:1m:1788906258213778862 31000
```

`replace_stream` keeps both (correctly — they are distinct samples). A naive `SUM(value)` reports 48584 where the truth is 31000, and an hour-long session contributes ~720 snapshots per model and type. This is Assumption 7's inflation hazard reappearing on the metrics side; the plan's contract for SP7 is met, so nothing is owed here, but **SP4's reader must take MAX per `(session_id, model, model_suffix, token_type)`**, and the `otel-claude` row in `SCHEMA.md:32` would be the honest place to say so.

**Observation (not a finding) — the live collector has written nothing.**
`ls -la /var/lib/opentelemetry-collector` is empty (dir mtime 22:55) although `otelcol-contrib` is listening on `127.0.0.1:4318` (`ss -ltnp`). Assumption 9b already records this hazard once ("two runs with the `file` exporter ALONE left no file though the exports succeeded"). Switch #23's acceptance should not be read as passed until a non-empty `claude-metrics.jsonl` exists there; SP7 is ready for it, as the probe above shows.

## Verdict

**APPROVED.** No MAJORs. 23/23 contract items met; both acceptance checks green on `--rebuild`; red-before-green reproduced exactly as the commit body claims; 20 of 23 mutants killed, all three survivors equivalent or coverage-only. The identity refusal is at the data-point/record level, the level that matters, and it survives the collector's real output. Six MINORs, none owed as a fix round — MINOR-2 (an `organization.*` fixture) and MINOR-6 (the MAX rule for SP4) are worth carrying into the next section that touches this stream.
