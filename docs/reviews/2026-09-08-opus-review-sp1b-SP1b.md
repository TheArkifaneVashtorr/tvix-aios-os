---
plan_defect: none
mutants_total: 18
mutants_killed: 16
mutants_outside_named: 8
model: opus
---
# Opus gate — seat run sp1b, task SP1b — APPROVED

## Summary

The MAJOR is closed and the five carried MINORs are pinned. In a fresh clone of
`task/SP1b` (`0eb7666`, base `5066ae9`) the three nested details are guarded
exactly as the section dictates, a broker-minted 403 writes no usage row, and
each of the ten named mutants dies. All four acceptance checks are green under
`--rebuild` (`addon` 81 passed, `evidence-unit` 495 passed, `host-core` ok,
`lint` ok — the same numbers the commit body pastes), plus ruff, ruff format,
repomap round-trip and `tasks check`.

The review's own three probes were re-run against the shipped addon, driving the
real hooks with no seat test helper: `usage.cost_details = "not-an-object"`,
`usage.prompt_tokens_details = [1, 2]` and an SSE frame whose detail is a string
each now produce **one** usage line, `status: "ok"` unaffected, the guarded
fields `null`, no exception out of `response(flow)`, and the response body byte
identical. The streamed arm is included and the tee still forwards bytes
unchanged.

Every deny mechanism was probed, not just the one the section names: the
allowlist deny at `requestheaders`, a `deny_paths` deny, an `http_connect` deny
and the `request` (defence-in-depth) deny all write zero usage rows and one
`deny` audit line, while an allowed completion still writes its row — the guard
is neither leaky nor sticky. `_deny` (`policy.py:287`) is the only site in the
addon that mints a `flow.response`; the two `flow.kill()` sites never reach the
`response` hook.

One coverage gap remains, one level up from the closed MAJOR and outside the
section's named set: the `isinstance` guard on `usage` **itself** is untested
(MINOR-1). The shipped code is correct there — a non-object `usage` degrades to
`status: "no-usage"` with no raise (probes P6/P7) — so it is a MINOR, not a
MAJOR.

## Contract items

The section's seven numbered items, taken literally, in the clone.

| # | contract item | verdict | evidence |
|---|---|---|---|
| 1 | each of the three nested details guarded the way `usage` is — `d = usage.get(key); d = d if isinstance(d, dict) else {}` | met | `pkgs/broker/policy.py:219-226` (the three pairs, `completion_details` wrapped by ruff format); the string/list/number fixtures are `tests/broker/test_usage_log.py:425-429` (`HOSTILE_DETAILS`), driven buffered `:438-460` and streamed `:462-484` |
| 1 | red before the fix with the review's own `AttributeError`, zero usage lines; green after — status unaffected, guarded fields null, `flow.response` untouched | met | red reproduced below (`6 failed`, the three exact `AttributeError` lines); green: probes P1–P5 and `assert f.response.raw_content == raw` at `tests/broker/test_usage_log.py:459` |
| 2 | `_deny` sets `flow.metadata["egress_denied"] = True` **before** building the response; `_record_usage` returns immediately on that flag | met | `pkgs/broker/policy.py:286` (first statement of `_deny`, before `flow.response = …` at `:287`); `pkgs/broker/policy.py:180-181` (the return precedes even the `_usage_path` check) |
| 2 | fixture: a flow denied by `_check`'s allowlist on the completions path, `requestheaders` → `response`; zero usage lines, one audit line, `verdict: "deny"` | met | `tests/broker/test_usage_log.py:483-495`; the flow's path is the completions default (`https_flow(host, path="/api/v1/chat/completions")`, `:43`) so the assertion is not satisfied by the path rule — proven by mutant M2 |
| 3 | `upstream_cost_usd` from `cost_details.upstream_inference_cost`, fixture with `cost = 1.0` and `upstream_inference_cost = 0.5` | met, no code change | `pkgs/broker/policy.py:238`; `tests/broker/test_usage_log.py:497-514` (`cost_usd == 1.0`, `upstream_cost_usd == 0.5`) |
| 4 | `instance` on the record, fixture `self.instance == "openrouter-fixture"` | met, no code change | `pkgs/broker/policy.py:229`; `tests/broker/test_usage_log.py:517-527` (asserts `addon.instance` and the written field) |
| 5 | a 429 JSON error body on the completions path → `status: "no-usage"`, `http_status: 429` | met, no code change | `pkgs/broker/policy.py:232`; `tests/broker/test_usage_log.py:530-545` |
| 6 | `request_id` regex: `{**OPENROUTER_USAGE, "request_id": "g" * 32}` refused `["request_id: not a re"]` | met | `tests/evidence/test_streams_policy.py:406-411`; the kind unchanged at `pkgs/evidence/streams.py:527` |
| 6 | key: two rows sharing `instance`, differing only in `request_id`, through `evidence.replace_stream` → `evidence.read` returns 2 | met | `tests/evidence/test_streams_policy.py:414-422`; `pkgs/evidence/streams.py:523` |
| 7 | the fixture's trailing newline appended | met | `tests/evidence/fixtures/openrouter-usage/usage.jsonl:4` now ends `\n` (the diff's `\ No newline at end of file` removed) |
| 7 | new test: four lines, `json.loads` each, first three validate `[]`, the fourth exactly `["model: not a model-id"]`, last byte `\n` | met | `tests/evidence/test_streams_policy.py:425-434` |
| — | Steps 3–4: items 3–6 add tests only, no further code change | met | the only `policy.py` hunks against `9f89135` are items 1 and 2 (`git diff 9f89135..HEAD -- pkgs/broker/policy.py` = 14 lines); `streams.py` untouched since SP1 |

### The prior review's items, one by one

| prior item | closed | how |
|---|---|---|
| MAJOR-1 — a non-object nested detail raises out of `response`, no line written, buffered and streamed | **closed** | `policy.py:219-226`; six new parametrised tests (three types × two paths); probes P1–P5 raise nothing and write one line each; mutants M1a/M1b/M1c all die |
| MINOR-1 — a broker-minted 403 writes a usage row | **closed** | `policy.py:180-181, 286`; `test_broker_minted_deny_writes_no_usage_line`; mutant M2 dies; probes D1–D4 cover all four deny mechanisms |
| MINOR-2 — `upstream_cost_usd`'s source untested | **closed** | `test_upstream_cost_usd_reads_nested_upstream_inference_cost`; mutant M3 dies (`assert None == 0.5`) |
| MINOR-3 — `instance` untested | **closed** | `test_usage_record_pins_instance`; mutant M4 dies (`KeyError: 'instance'`) |
| MINOR-4 — `http_status` pinned only at 200 | **closed** | `test_http_status_pinned_for_429_no_usage`; mutant M5 dies (`assert 200 == 429`) |
| MINOR-5 — the kind's `request_id` regex and `key` untested | **closed** | two new tests in `test_streams_policy.py`; mutants M6a and M6b die |
| MINOR-6 — the `tests/broker/test_policy.py` deviation | **closed** | the file is now inside SP1b's own `touches` list; zero undisclosed files in the diff |
| MINOR-7 — the fixture unvalidated and unterminated | **closed** | the newline appended and every line validated; mutant M7 dies |
| MINOR-8 — pre-commit red in a post-commit clone | recurs (process) | see MINOR-2 below; identical derived-queue artifact, not a seat action |

## Red before green

Base implementation = SP1's `9f89135` (fetched read-only from
`~/factory/ws/sp1/SP1`), branch tests kept.

| item | command in the clone | red | green |
|---|---|---|---|
| 1 | `git checkout 9f89135 -- pkgs/broker/policy.py` then `nix develop -c pytest tests/broker/test_usage_log.py -q -k nested_detail` | `AttributeError: 'str' object has no attribute 'get'` (`policy.py:231`), `'list'` (`:236`), `'int'` (`:238`), each twice — buffered and streamed — `6 failed, 19 deselected` | at HEAD `81 passed` |
| 2 | same checkout, `-k deny` | `assert usage_lines(addon.usage_log) == []` → `Left contains one more item: {… 'http_status': 403 …}`, `1 failed` | at HEAD green; whole suite on SP1's code: `7 failed, 74 passed` |
| 7 | `git checkout 9f89135 -- tests/evidence/fixtures/openrouter-usage/usage.jsonl` then `-k fixture` | `assert p.read_bytes().endswith(b"\n")` → `assert False`, `1 failed` | at HEAD `evidence-unit` `495 passed` |
| 3–6 | no code change by contract; their reds are their mutants (M3, M4, M5, M6a, M6b below), each pasted | — | — |

The commit body's reds match what I measured line for line, including the
`'int' object` case the review had not itself probed. No test is vacuous: every
one of the ten new assertions is killed by at least one mutant below.

## Mutants

**Named by the section: 10 applied, 10 killed.** (The section writes item 1's
mutant as "drop the `isinstance` guard on any one detail"; all three were
applied separately.)

| mutant | test that kills it | failing line |
|---|---|---|
| M1a — `prompt_details = usage.get("prompt_tokens_details") or {}` | `test_nested_detail_{buffered,streamed}_degrades_to_nulls[prompt_tokens_details]` | `AttributeError: 'list' object has no attribute 'get'` — `2 failed, 79 passed` |
| M1b — same on `completion_tokens_details` | the same pair | `AttributeError: 'int' object has no attribute 'get'` — `2 failed, 79 passed` |
| M1c — same on `cost_details` | the same pair | `AttributeError: 'str' object has no attribute 'get'` — `2 failed, 79 passed` |
| M2 — the `egress_denied` guard deleted from `_record_usage` | `test_broker_minted_deny_writes_no_usage_line` | `Left contains one more item: {… 'streamed': False …}` — `1 failed, 80 passed` |
| M3 — `"upstream_cost_usd": usage.get("upstream_inference_cost")` | `test_upstream_cost_usd_reads_nested_upstream_inference_cost` | `assert None == 0.5` — `1 failed, 80 passed` |
| M4 — `"instance"` dropped from the usage record | `test_usage_record_pins_instance` | `KeyError: 'instance'` — `1 failed, 80 passed` |
| M5 — `"http_status": 200` hardcoded | `test_http_status_pinned_for_429_no_usage` | `assert 200 == 429` — `1 failed, 80 passed` |
| M6a — `request_id` class widened to `"id"` | `test_openrouter_usage_request_id_regex_is_hex` | `assert [] == ['request_id: not a re']` — `1 failed, 204 passed` |
| M6b — `"key"` reduced to `("instance",)` | `test_openrouter_usage_key_discriminates_request_id` | `assert 1 == 2` (`evidence.read` returned one row) — `1 failed, 204 passed` |
| M7 — the fixture's trailing newline dropped again | `test_openrouter_usage_fixture_validates_and_is_terminated` | `assert p.read_bytes().endswith(b"\n")` → `assert False` — `1 failed, 204 passed` |

The prior review's five survivors are exactly M3, M4, M5, M6a and M6b — all five
now die.

**Outside the named set: 8 applied, 6 killed, 2 survived.**

Killed:

- O1 — the guard reads `egress_audited` instead of `egress_denied` (the
  plausible wrong fix): `18 failed, 63 passed`, e.g.
  `AssertionError: assert [] == ['ok', 'unparsed']`.
- O2 — `cost_details` falls back to `None` instead of `{}`:
  `AttributeError: 'NoneType' object has no attribute 'get'`, many failed.
- O5 — the guard widened to `isinstance(prompt_details, (dict, list))`:
  `AttributeError: 'list' object has no attribute 'get'`, `2 failed`.
- O6 — fixture row 3's `status` → `"weird"`:
  `At index 2 diff: ['status: not in enum (ok|no-usage|unparsed)'] != []`.
- O7 — fixture row 4's `model` → a valid model id:
  `assert [] == ['model: not a model-id']`.
- O8 — `nixosModules/egressBroker.nix:30` renders `audit.jsonl` (SP1's line,
  carried in this diff): `host-core` red with
  `error: host-core: broker policy must carry usage_log = /var/lib/egress-broker/<name>/usage.jsonl and usage_path_prefixes == [ "/api/v1/chat/completions" ] for openrouter and seat`.

Survived:

- O3 — `usage = usage or {}` in `_usage_record` (the `isinstance` guard on
  `usage` itself removed): `81 passed`. A coverage gap, not a code defect —
  MINOR-1.
- O4 — `_deny` sets the flag *after* `_audit` rather than before: `81 passed`.
  **Equivalent mutant**: both orderings set the flag before the `response` hook
  can run. Not a gap.

## Checks

Every check re-run by me in the fresh clone with `--rebuild`; nothing reused
from the seat's report.

| check | command | result |
|---|---|---|
| `addon` | `nix build .#checks.x86_64-linux.addon -L --no-link --rebuild` | exit 0 — `broker-addon-tests> 81 passed in 0.36s` |
| `evidence-unit` | same | exit 0 — `evidence-unit> 495 passed in 13.36s` |
| `host-core` | same | exit 0 |
| `lint` | same | exit 0 — `Found 0 warnings and 0 errors.` |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 on the first run: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated` (`… SP1b` → `… SP2 SP3 SP8`); staged and re-run: **exit 0** (MINOR-2) |
| ruff | `nix develop -c ruff check pkgs/broker tests/broker pkgs/evidence tests/evidence` | `All checks passed!` |
| ruff format | `ruff format --check` over the same | `83 files already formatted` |
| repomap | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0 |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

## Touches and commit

Nine files in `5066ae9..0eb7666` (the range carries SP1's cherry-picked work
plus SP1b's own edits):

- Inside the section's `touches`, all eight: `pkgs/broker/policy.py`,
  `tests/broker/test_usage_log.py`, `tests/broker/test_policy.py`,
  `nixosModules/egressBroker.nix`, `flake.nix`, `pkgs/evidence/streams.py`,
  `tests/evidence/test_streams_policy.py`,
  `tests/evidence/fixtures/openrouter-usage/usage.jsonl`.
- `docs/MAP.md` — exempt by the Global Constraints; the two test-count lines
  only (`tests/broker` 1→2, `tests/evidence` 88→89), and it round-trips through
  the generator.

Zero undisclosed files; zero deviations to record. Exactly one commit. The
subject is byte-identical to the section's (297 bytes each, compared
programmatically against the plan text: `IDENTICAL: True`). The body states the
why and pastes each red and each green; the two trailers follow a blank line
(`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless,
factory run sp1b)`, `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`).
No board commit; `docs/OPERATIONS.md` untouched; the plan file untouched.

## Findings

### MINOR-1 — the `isinstance` guard on `usage` itself is untested

`pkgs/broker/policy.py:215` (`usage = usage if isinstance(usage, dict) else {}`).
Replacing it with SP1's old idiom survives the whole suite:

```
O3 the usage-dict guard in _usage_record removed  ->  81 passed in 0.16s
```

The shipped code is correct — a completions body whose `usage` is a non-empty
non-object degrades cleanly, measured against the shipped addon:

```
P6 usage = string: raised=None lines=1
   status='no-usage' cost_usd=None upstream=None cached=None …
P7 usage = list:   raised=None lines=1
   status='no-usage' …
```

so this is the same *class* of gap the MAJOR closed, one level up, with the code
already right. The section named only the three nested details, so it is not a
contract miss; worth one more fixture whenever this file is next touched.

### MINOR-2 — pre-commit is red in a post-commit clone (process)

`githooks/pre-commit` exits 1 in the fresh clone with `tasks:
docs/OPERATIONS.md queue block was stale and has been regenerated — git add
docs/OPERATIONS.md and commit again`; the regenerated block replaces `CR4 PW1glm
PW1kimi PW1pro SP1b` with `CR4 PW1glm PW1kimi PW1pro SP2 SP3 SP8`. Staging it
and re-running is exit 0. Identical to the prior round's MINOR-8: the derived
queue moving on once SP1b exists on the branch, not a seat action. Recorded so
the integrator expects it.

### MINOR-3 — `src` has no producer in the broker (carried from SP1, for SP8)

`pkgs/evidence/streams.py:525` declares `"src": ("enum", ("broker",))`, but
`_usage_record` (`pkgs/broker/policy.py:227-246`) writes no `src` key and none
of the four fixture rows in
`tests/evidence/fixtures/openrouter-usage/usage.jsonl` carries one (a missing
declared field is not refused, so the fixture test's `[]` results stand). The
enum arm is exercised only by the synthetic valid row
`tests/evidence/test_streams_policy.py:343`. By the plan's split that is SP8's
job — the ingest must synthesise `src: "broker"` — and nothing in SP1 or SP1b
states otherwise. Not gating here; flagged so SP8's section does not inherit it
silently.

## Verdict

**APPROVED.** The section's seven items are each met literally, and every item
of the rejecting review is closed with the fixture and the mutant the section
named: the three nested details are guarded the way `usage` is (the review's own
three probes, plus their SSE twins, now write one line each with the guarded
fields null and nothing raised), a broker-minted 403 writes no usage row on all
four deny mechanisms while an allowed completion still writes its own, and the
cost source, `instance`, a 429 `http_status`, the `request_id` regex, the key
tuple and the fixture's newline are each pinned by a test that a named mutant
kills. Ten named mutants, ten dead; eight more outside the set, six dead, one
equivalent and one a disclosed coverage gap (MINOR-1). All four checks green
under `--rebuild` plus ruff, repomap and `tasks check`; one commit, the subject
byte-identical, both trailers, zero files outside `touches`.
