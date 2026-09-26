---
plan_defect: implementer
plan_defect_secondary: missing-case
mutants_total: 37
mutants_killed: 31
mutants_outside_named: 15
model: opus
---
# Opus gate — seat run sp1, task SP1 — REJECTED
## Summary

The mechanism is right and the acceptance is real. In a fresh clone of `task/SP1`
(`9f89135`, base `46f113b`) all four named checks are green on `--rebuild`
(`addon` 71 passed, `evidence-unit` 492 passed, `host-core` ok, `lint` ok), every
one of the section's 22 named mutants dies, both reds reproduce (`2 failed` for
the kind, `15 failed` for the broker, `error: attribute 'usage_log' missing` for
`host-core`), the tee forwards bytes unchanged, the tail trim is real in both
directions, the request id joins both records, and no response content reaches
the usage line.

One stated contract is violated. The section's Interfaces say of `_record_usage`:
"`status` ∈ `ok`, `no-usage` …, `unparsed` (nothing parseable; **any exception →
`unparsed`, the line still written**)", and §Errata applied **I** says
"`_record_usage` **never raises out of the `response` hook**". A completions
response that is valid JSON but whose `usage.prompt_tokens_details` /
`completion_tokens_details` / `cost_details` is not an object raises
`AttributeError` straight out of `response(flow)` and writes **no** usage line —
on the buffered path and on the streamed (production) path alike. The plan's
Tests row 5 fixture (`b"<html>"` and a frameless SSE) cannot reach it, so the
suite is green with the hole open: hence `plan_defect: implementer` (the
sentence was in the seat's own Interfaces) with `missing-case` secondary (the
Tests table never named the discriminating fixture).

## Contract items

Each item taken literally from the `### SP1 (` section, verified in the clone.

| # | contract item | verdict | evidence |
|---|---|---|---|
| 1 | Policy JSON gains `usage_log`, defaulted by the addon to `dirname(audit_log)/usage.jsonl` so the existing tests need no change | met | `pkgs/broker/policy.py:102-104`; `tests/broker/test_usage_log.py:304-310`; the 56 pre-existing `test_policy.py` tests still pass unchanged but for the disclosed one line |
| 2 | Policy JSON gains `usage_path_prefixes`, default `["/api/v1/chat/completions"]` in the addon **and** in the Nix option `usagePathPrefixes` | met | `pkgs/broker/policy.py:105-107`; `nixosModules/egressBroker.nix:57-64` |
| 3 | `renderPolicy` renders `usage_log = "/var/lib/egress-broker/${name}/usage.jsonl"; usage_path_prefixes = i.usagePathPrefixes;` | met | `nixosModules/egressBroker.nix:30-31` (byte-for-byte the section's two lines) |
| 4 | `_request_id(self, flow) -> str` = `flow.metadata.setdefault("egress_request_id", uuid.uuid4().hex)` | met | `pkgs/broker/policy.py:149-152` |
| 5 | `_audit`'s record gains `"request_id"` **after** `"instance"` | met | `pkgs/broker/policy.py:132-135` (`ts`, `instance`, `request_id`, `client`, …) |
| 6 | `_usage_path(self, flow) -> bool` = `bool(_prefix_match(flow.request.path, self.usage_path_prefixes))` | met | `pkgs/broker/policy.py:154-157` |
| 7 | `_usage_tee` returns a `tee(data)` that appends to `flow.metadata["egress_usage_tail"]` (a `bytearray`), trims to the last `USAGE_TAIL_BYTES = 65536`, returns `data` unchanged, `b""` → `b""`, never decodes, never raises | met | `pkgs/broker/policy.py:32`, `159-172`; proven by `test_tee_forwards_bytes_unchanged_and_end_returns_empty` and by mutants `tail_bytes_64` / `trim_keeps_first` both dying |
| 8 | `responseheaders`: `flow.response.stream = self._usage_tee(flow) if self._usage_path(flow) else True` | met | `pkgs/broker/policy.py:505-510` |
| 9 | `response`: `_audit` then `_record_usage`; `error` unchanged (no usage line) | met | `pkgs/broker/policy.py:512-517`; mutant `error_records_usage` dies |
| 10 | `_record_usage` no-op off the usage path | met | `pkgs/broker/policy.py:180-181`; mutant `path_rule_removed` dies |
| 11 | Source: the tail when `egress_usage_tail` in metadata (`streamed = True`), else `raw_content` (`streamed = False`, `None` → `unparsed`) | met | `pkgs/broker/policy.py:182-198` |
| 12 | `_last_usage_frame(tail)` walks from the END, takes `data:` lines, skips `[DONE]`, `json.loads` each (a failure → continue), returns the first object whose `usage` is a dict, else `None` | met | `pkgs/broker/policy.py:60-78`; mutants A/B/C all die |
| 13 | `status` ∈ `ok`, `no-usage`, `unparsed`; **any exception → `unparsed`, the line still written** | **NOT met** | MAJOR-1 below — `pkgs/broker/policy.py:217-219` raises `AttributeError` out of `response` and writes nothing |
| 14 | The record's 18 keys, in the section's order, each null when absent, never the content | met | `pkgs/broker/policy.py:220-238`; probe: keys printed in exactly the section's order, `SECRET-REPLY-TEXT` absent from the file |
| 15 | Written as `json.dumps(rec) + "\n"` with `open(self.usage_log, "a", encoding="utf-8")`, no `chmod` — the umask decides the mode | met | `pkgs/broker/policy.py:200-202`; `test_usage_file_mode_follows_umask` pins `0o644`; mutant `chmod_600` dies |
| 16 | Errata I: the open/write wrapped `try/except OSError`, one stderr line `egress-broker: usage log write failed: {exc}`, the audit line and the flow still complete | met (for the write) | `pkgs/broker/policy.py:199-204`; `test_unwritable_usage_dir_does_not_break_flow`; mutants `write_failure_escapes` and `x_stderr_message_changed` both die |
| 17 | The `openrouter-usage` kind exactly as the section's literal, placed after `lane-job` | met | `pkgs/evidence/streams.py:520-545`; `lane-job` at `:506` |
| 18 | `host-core` assertions for `openrouter` **and** `seat`, beside the `body_patch` assertion, with the section's message | met | `flake.nix:770`, `823-833`; the message string matches byte-for-byte and fires under both nix mutants |
| 19 | Fixture `tests/evidence/fixtures/openrouter-usage/usage.jsonl`: four lines — one `ok` with Assumption 4's shape and `gen_id: null`, one `no-usage`, one `unparsed`, one `"model": "Bad Model"`, synthetic 32-hex ids | met | the file's four lines; ids `0…01`–`0…04` |
| 20 | `test_streams_policy.py`: the valid row in the per-kind table plus three refused rows | met | `tests/evidence/test_streams_policy.py:341-362`, `381`, `391-402` |
| 21 | Privacy: the broker never records a response's content | met | probe 6 — a body carrying `SECRET-REPLY-TEXT` writes a line without it |

## Red before green

| step | command in the clone | red | green |
|---|---|---|---|
| 1 (kind) | `git checkout 46f113b -- pkgs/evidence/streams.py` then `pytest tests/evidence/test_streams_policy.py -q -k openrouter` | `assert ["undeclared ...outer-usage'"] == ['cost_usd: not a num']` … `2 failed, 2 passed` | at HEAD: `evidence-unit` `492 passed` |
| 2 (addon) | `git checkout 46f113b -- pkgs/broker/policy.py` then `pytest tests/broker -q` | `TypeError: 'bool' object is not callable` at `test_usage_log.py:116`; `15 failed, 56 passed` (14 of them `test_usage_log.py`, the 15th the disclosed `test_audit_record_has_exact_fields`) | `addon` check: `broker-addon-tests> 71 passed in 0.32s` |
| 4 (host-core) | `git checkout 46f113b -- nixosModules/egressBroker.nix`, `git add -A`, `nix build .#checks.x86_64-linux.host-core -L --no-link --rebuild` | `error: attribute 'usage_log' missing at …/flake.nix:828:15` | at HEAD: exit 0 |

The commit body's reds are honest. Its "(14 failed)" is the count before
`test_policy.py`'s one-line deviation was applied; with the branch's tests it is
15, as shown. Note the base's implementation does **not** turn
`test_response_preserves_headers_and_raw_content` red (nothing in the base
`response` hook touches the body) — it is a regression guard, and it is not
vacuous: its named mutant kills it (below).

Every one of the 17 assertions the section names is killed by at least one
mutant; none is vacuous.

## Mutants

**Named by the section: 22 applied, 22 killed.**

| mutant (section row) | killed by | line |
|---|---|---|
| A — the tee returns the chunk uninspected (1) | `test_sse_completion_records_one_ok_line`, `test_usage_tail_caps_at_last_64k` | `2 failed, 271 passed` |
| B — the first `data:` frame, `usage` not required (1) | `test_sse_completion_records_one_ok_line` | `1 failed, 272 passed` |
| C — the tail keeps only the last chunk (1) | `test_sse_completion_records_one_ok_line`, `test_usage_tail_caps_at_last_64k` | `2 failed, 271 passed` |
| the tee returns `b""` for a chunk (2) | `test_tee_forwards_bytes_unchanged_and_end_returns_empty` | `1 failed, 272 passed` |
| `gen_id` read from `usage.id` (3) | `test_buffered_completion_ok_gen_id_from_top_level` | `1 failed, 272 passed` |
| `frame["usage"]` → `KeyError` (4) | `test_completions_object_without_usage_is_no_usage` | `1 failed, 272 passed` |
| the parse exception propagates (5) | `test_unparseable_bodies_and_frameless_sse_are_unparsed` | `1 failed, 272 passed` |
| D — the path rule removed (6) | `test_non_completions_path_writes_no_usage_line` | `1 failed, 272 passed` |
| the `True` arm dropped (6) | `test_non_completions_path…`, `test_responseheaders_streams_event_stream_content_type` | `2 failed, 271 passed` |
| `stream = True` for every SSE (7) | five tests incl. `test_completions_sse_path_makes_stream_callable` | `5 failed, 268 passed` |
| `_request_id` mints per call (8) | `test_audit_and_usage_share_request_id_across_flows` | `1 failed, 272 passed` |
| the field dropped from `_audit` (8) | `test_audit_record_has_exact_fields`, `test_audit_and_usage_share_request_id…` | `2 failed, 271 passed` |
| `policy["usage_log"]` with no default (9) | `test_usage_log_defaults_beside_audit_and_honours_key` (+69 collateral) | `70 failed, 203 passed` |
| `os.chmod(path, 0o600)` after the write (10) | `test_usage_file_mode_follows_umask` | `1 failed, 272 passed` |
| `error` calls `_record_usage` (11) | `test_error_flow_writes_no_usage_line` | `1 failed, 272 passed` |
| `cached_tokens` read flat off `usage` (12) | `test_nested_token_fields…`, `test_sse_completion_records_one_ok_line` | `2 failed, 271 passed` |
| `response` assigns `flow.response.content` (13) | `test_response_preserves_headers_and_raw_content` (+2 in `test_policy.py`) | `3 failed, 270 passed` |
| `cost_usd` declared `("null", "id")` (14) | `test_openrouter_usage_refusals`, the valid-row parametrize | `2 failed, 271 passed` |
| `usage_log` rendered as `audit.jsonl` (15) | `host-core` | `error: host-core: broker policy must carry usage_log = /var/lib/egress-broker/<name>/usage.jsonl …` |
| I — the write failure escapes `response` (16) | `test_unwritable_usage_dir_does_not_break_flow` | `1 failed, 272 passed` |
| J — `USAGE_TAIL_BYTES = 64` (17) | `test_usage_tail_caps_at_last_64k`, `test_sse_completion…` | `2 failed, 271 passed` |
| J — the trim keeps the FIRST 64 KiB (17) | `test_usage_tail_caps_at_last_64k` | `1 failed, 272 passed` |

**Outside the named set: 15 applied, 9 killed, 6 survived.**

Killed: `model` declared `("null", "id")` inside the `openrouter-usage` block
(2 failed); the `status` enum widened with `"weird"` (1 failed);
`usagePathPrefixes` default emptied (`host-core` red with the section's
message); the tail trim removed entirely (1 failed); `streamed` flag inverted
(10 failed); the stderr text changed (1 failed); every buffered object counted
`ok` (1 failed); `provider` hardcoded `None` (1 failed); `streamed` declared
`("null", "num")` in the kind (2 failed).

Survived (each a coverage gap, none a code defect — see MINORs 2–5):

- `"http_status": 200` hardcoded → `273 passed`. No test drives a non-200.
- `upstream_cost_usd` read off `usage` instead of `usage.cost_details` →
  `273 passed`. No test asserts that field at all.
- `"instance"` dropped from the usage record → `273 passed`. It is half the
  kind's `key`.
- the kind's `request_id` class weakened from `("re", r"^[0-9a-f]{32}$")` to
  `"id"` → `273 passed`.
- the kind's `"key"` reduced to `("instance",)` → `273 passed`.
- the `[DONE]` skip removed → `273 passed`. **Equivalent mutant**: `[DONE]` is
  not JSON, so the `json.loads` guard already drops it. Not a gap.

Two further attempts were discarded as invalid rather than counted: a `model`
mutation whose anchor matched an earlier kind's field (it mutated an untouched
kind — out of SP1's scope), and `flow.response.content = flow.response.content`,
which is byte-preserving with no content-encoding and so is a no-op, not a
mutant. Both were re-applied correctly and are in the tables above.

## Checks

Every check re-run by me in the fresh clone, `--rebuild`, nothing reused from
the seat's report.

| check | command | result |
|---|---|---|
| `addon` | `nix build .#checks.x86_64-linux.addon -L --no-link --rebuild` | exit 0 — `broker-addon-tests> 71 passed in 0.32s` |
| `evidence-unit` | same, `evidence-unit` | exit 0 — `evidence-unit> 492 passed in 13.60s` |
| `host-core` | same, `host-core` | exit 0 |
| `lint` | same, `lint` | exit 0 — `Found 0 warnings and 0 errors.` ×4 |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 on the first run: `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the regenerated block is `… SP2 SP3 SP8` in place of `… SP1`. Staged and re-run: **exit 0**. Derived-state artifact of SP1 having landed on the branch, not a seat action (MINOR-8) |
| ruff | `nix develop -c ruff check pkgs/broker tests/broker pkgs/evidence tests/evidence` | `All checks passed!` |
| ruff format | `ruff format --check …` | `83 files already formatted` |
| repomap | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0 — the committed `docs/MAP.md` is what the generator writes |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

## Touches and commit

Nine files in `46f113b..9f89135`:

- Inside the section's `touches`: `pkgs/broker/policy.py`,
  `tests/broker/test_usage_log.py`, `nixosModules/egressBroker.nix`,
  `flake.nix`, `pkgs/evidence/streams.py`,
  `tests/evidence/test_streams_policy.py`,
  `tests/evidence/fixtures/openrouter-usage/usage.jsonl` — all seven, none
  missing.
- `docs/MAP.md` — exempt by the Global Constraints; the tests-count lines only
  (`tests/broker` 1→2, `tests/evidence` 88→89), and it round-trips through the
  generator.
- `tests/broker/test_policy.py` — one line (`:103`, `"request_id"` added to the
  exact-field list), disclosed in the commit body with its reason. MINOR-6.

Exactly one commit. The subject is byte-identical to the section's (verified by
`cmp` against the section's string). The body states the why, pastes the reds
and the greens, and carries the two trailers after a blank line
(`Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 …`,
`Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`). No board commit;
`docs/OPERATIONS.md` untouched; the plan file untouched.

## Findings

### MAJOR-1 — `_record_usage` raises out of the `response` hook and writes no line when a nested usage detail is not an object

`pkgs/broker/policy.py:217-219`

```python
        prompt_details = usage.get("prompt_tokens_details") or {}
        completion_details = usage.get("completion_tokens_details") or {}
        cost_details = usage.get("cost_details") or {}
```

`usage` itself is type-guarded (`isinstance(frame.get("usage"), dict)` at `:195`,
and `_last_usage_frame` at `:77` only returns a frame whose `usage` is a dict),
but the three nested objects are not: a non-empty non-object survives `or {}`
and the following `.get` raises.

The contract broken, from the section's own Interfaces:

> `status` ∈ `ok`, `no-usage` (an object without `usage`), `unparsed` (nothing
> parseable; any exception → `unparsed`, the line still written).

and §Errata applied **I**:

> SP1's `_record_usage` never raises out of the `response` hook.

Measured in the clone against the shipped addon (probe driving the real hooks;
the streamed case is the production path, `flow.response.stream` the tee):

```
PROBE1 (buffered, usage.cost_details = "not-an-object")
  RAISED OUT OF response(): AttributeError: 'str' object has no attribute 'get'
  usage lines: []      audit lines: 1

PROBE2 (buffered, usage.prompt_tokens_details = [1, 2])
  RAISED OUT OF response(): AttributeError: 'list' object has no attribute 'get'
  usage lines: []

SSE PROBE (streamed, one data: frame, usage.prompt_tokens_details = "none")
  RAISED OUT OF response(): AttributeError: 'str' object has no attribute 'get'
  usage lines: <none>   audit lines: 1
```

Consequence: mitmproxy's `addonmanager.safecall`
(`…/mitmproxy/addonmanager.py:44-56`) catches the escape and logs a traceback,
so the flow survives — but the usage row for that request is lost silently, and
lost rows are exactly what SP4 sums into dollars. The failure mode is the one
erratum I was written to close, on the same hook, one function away from the
`try/except OSError` that closes it for the write.

Not covered by any test: Tests row 5 drives `b"<html>"` and a frameless SSE —
both fail at `json.loads`, which *is* caught. No fixture in the section or the
file supplies valid JSON with a hostile nested type, so the suite is green with
the hole open. (Not fixed here — reporting only.)

### MINOR-1 — a broker-minted 403 on the completions path writes a usage row

`pkgs/broker/policy.py:512-514`. When `requestheaders` denies (a host outside
`allow`, a fail-closed body patch), mitmproxy emulates `responseheaders` and
still fires `HttpResponseHook`
(`…/mitmproxy/proxy/layers/http/__init__.py:379-387`, `:511`). `_audit` is a
no-op there thanks to its `egress_audited` guard (`:127-129`); `_record_usage`
has no equivalent guard, so a denied completions request writes a row:

```
PROBE3 denied -> status 403
PROBE3 audit verdicts = ['deny']
PROBE3 usage lines = [{… 'http_status': 403, 'status': 'unparsed', 'cost_usd': None …}]
```

Correctly typed and costless, so it does not corrupt a spend total, but the
section's heading is "the broker records every OpenRouter **response's** usage"
and a 403 the broker minted itself is not one. The `error` arm is excluded by
contract and by a test (row 11); the deny arm is excluded by neither. Worth a
line in SP8's ingest or a guard here.

### MINOR-2 — `upstream_cost_usd`'s source is untested

`pkgs/broker/policy.py:231`. Reading it flat off `usage` instead of
`usage.cost_details` survives the entire suite (`273 passed`). Tests row 12
pins only `cached_tokens` and `reasoning_tokens`; no test asserts
`upstream_cost_usd` non-null anywhere. Stated interface, no test.

### MINOR-3 — `instance` in the usage record is untested

`pkgs/broker/policy.py:222`. Dropping it survives (`273 passed`), though it is
the first half of the kind's `key: ("instance", "request_id")`
(`pkgs/evidence/streams.py:523`) and SP8's merge depends on it.

### MINOR-4 — `http_status` is pinned only at 200

`pkgs/broker/policy.py:225`. Hardcoding `200` survives (`273 passed`). The
non-200 behaviour is in fact sensible — a 429 with a JSON error body records
`status: no-usage`, `http_status: 429` (probe 4) — but nothing holds it there,
and 429s are the shape SP2/SP6 care about most.

### MINOR-5 — the kind's `request_id` regex and `key` tuple are untested

`pkgs/evidence/streams.py:523`, `:527`. Weakening the regex to the `"id"` class,
or reducing the key to `("instance",)`, both survive (`273 passed`). The
section named three refusal rows (`cost_usd`, `model`, `status`) and no
bad-`request_id` row; a plan-level gap the seat inherited rather than made.

### MINOR-6 — the disclosed deviation

`tests/broker/test_policy.py:103`. One line, forced by the Interfaces change
(the audit record gains `request_id`, and that test pins the exact field set),
disclosed in the commit body with its reason. Correct handling; recorded as the
one file outside `touches`.

### MINOR-7 — the fixture is unvalidated and has no trailing newline

`tests/evidence/fixtures/openrouter-usage/usage.jsonl:4`. The four rows match
the section's spec, but no test in this task reads them, and the file ends
without the `\n` the addon always writes (`policy.py:201`). SP8 reads it; a
last line without its newline is exactly the "torn last line" shape SP8 must
distinguish, so it is worth being deliberate about there.

### MINOR-8 — pre-commit is red in a post-commit clone (process)

`githooks/pre-commit` exits 1 in the fresh clone with
`tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`,
because with SP1 landed the derived queue moves from `… SP1` to
`… SP2 SP3 SP8`. Staging the regeneration and re-running is green. This is the
board's derived block doing its job, not a seat defect — recorded so the
integrator expects it.

## Verdict

**REJECTED** on MAJOR-1: the section states, twice, that no exception leaves
`_record_usage`'s path without a written line, and a valid-JSON completions
response with a non-object `usage.*_details` raises `AttributeError` out of the
`response` hook and writes nothing — on the streamed path as well as the
buffered one. Everything else in the section is met: 22/22 named mutants dead,
both reds reproduced, all four checks green on `--rebuild` plus ruff, repomap
and `tasks check`, the touches list honoured with one correctly disclosed
deviation, and the commit subject byte-identical with both trailers.

The fix round is small — guard the three nested lookups with `isinstance`
(or wrap the frame handling so any exception yields `status: "unparsed"` with
the line still written), and add the fixture the Tests table lacks: a
completions body that is valid JSON whose `usage.prompt_tokens_details` is a
string, asserting one `unparsed` line and no exception, driven on both the
buffered and the streamed path.
