---
plan_defect: missing-case
plan_defect_secondary: implementer
mutants_total: 22
mutants_killed: 19
mutants_outside_named: 7
model: opus
---
# Opus gate — seat run sp2, task SP2 — REJECTED

## Summary

Base `e4258e0`, head `2d40f41`, one commit, subject byte-identical, eleven files
— the ten declared `touches` plus `docs/MAP.md` (exempt). All three named
acceptance checks are green on `--rebuild`, `githooks/pre-commit` is green,
ruff check/format clean, `repomap.py write` leaves no diff, `tasks.py check`
silent. All fifteen named mutants die; three of seven mutants outside the named
set survive.

One MAJOR gates it. The section's headline — "the ledger extractor **runs on
this host** … string findings accepted" — and its test row 8 ("every emitted
row validates") are both false end to end: `factory.extract` over the new
`workflow-strfinding` fixture now raises `streams.StreamRefused: row 0:
severity: null not allowed; row 0: file: null not allowed`. The
`AttributeError` was replaced by a `StreamRefused`; the extractor still cannot
walk a transcript that carries a string finding, which is the one thing the
task exists to fix. The delivered test never notices because it calls
`factory._read_findings` directly and never goes through `extract`.

## Contract items

Taken literally, in the section's order.

| # | contract item | verdict | evidence |
|---|---|---|---|
| 1 | `_usage_groups(lines) -> list[tuple[str \| None, dict]]`; MAX per group over `input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens_details.thinking_tokens` | met | `tools/ledger/factory.py:121-155`; the five fields at `:138-144`, `group[key] = max(group[key], value)` at `:154-155` |
| 2 | the group is per `(file, message.id)`, never `message.id` alone; a line without `message.id` is its own group | met | `tools/ledger/factory.py:127` `groups` is a call-local dict and `_read_agent` runs once per file (`def` at `:172`, `_usage_groups(lines)` at `:181`); `:145-147` `if gid is None: result.append((None, fields)); continue`. Proven by mutant 1E (a module-level `groups`) → `assert 8017 == 8517` |
| 3 | `_read_agent` sums the groups' maxima across groups and across files; `message_count` = number of groups; `tool_uses`, `model`, timestamps unchanged | met | `tools/ledger/factory.py:176-185` (`tokens[key] += group.get(key, 0)` at :184, `message_count = len(groups)` at :185); `:187-201` leave `model`/`tool_uses`/`stamps` on the original loop; `test_factory_extract_rollup` still passes unchanged |
| 4 | `_model_split(model_id) -> tuple[str, str \| None]`: split at the first `[`, head must match `MODEL_ID_RE`, tail without brackets is `model_suffix`, `None` when no `[` | met in behaviour, **not in signature** | `tools/ledger/factory.py:159-168` — split and tail correct (`_model_split("claude-opus-5[1m]") == ("claude-opus-5", "1m")`); the head is not checked against `MODEL_ID_RE` in the helper — the refusal is left to `streams.validate`, which does fire (mutant 10b → `role_model: not a model-id`). The `def` carries no annotations (MINOR-1) |
| 5 | `_read_agent`'s `model`/`model_suffix` both come from the helper | met | `tools/ledger/factory.py:203` `model, model_suffix = _model_split(model)`; `:213-216` `role_model`/`model_id`/`model_suffix` |
| 6 | `_read_findings`: `str` → `title = finding`, `severity`/`file`/`class` null | code met, **contract broken downstream** | `tools/ledger/factory.py:232-236`. The row it builds cannot be written — see MAJOR-1 |
| 7 | `_read_findings`: `dict` → as today | met | `tools/ledger/factory.py:237-241` |
| 8 | anything else → skipped with stderr `factory.py: {journal}: {agentId}: finding {i} is neither a string nor an object, skipped` | met | `tools/ledger/factory.py:242-248`; observed verbatim: `factory.py: …/workflow-strfinding/journal.jsonl: a4444444444444444: finding 2 is neither a string nor an object, skipped` |
| 9 | `_labels(journal_file) -> dict[agentId, label]` from `result.label`; `extract_run` sets `agent["label"] = labels.get(agent_id)` | met | `tools/ledger/factory.py:267-280`, `:331` |
| 10 | `_limit_event(event, origin) -> dict \| None`; the three gates; the seven quota keys mapped one to one; `origin` as given | met | `tools/ledger/factory.py:283-312`; the seven mappings at `:303-309` verified field by field by `test_limit_events_extracted_and_idempotent` |
| 11 | `extract_run` collects them over every agent file with `origin = "agent"`; `extract` merges `limit-events.jsonl` | met | `tools/ledger/factory.py:333-336`, `:379` |
| 12 | `factory-agent.fields` gains `"message_count": "int"` and `"model_suffix": ("null", "id")` | met | `pkgs/evidence/streams.py:456` (`model_suffix`) and `:457` (`message_count`) |
| 13 | the `limit-event` kind, verbatim (stream, v, key, fourteen fields) | met | `pkgs/evidence/streams.py:548-568`; field-for-field identical to the plan's block after `ruff format` rewrap |
| 14 | the `main-session` kind, verbatim (stream, v, key, twelve fields incl. the `by_model` list capped 8) | met | `pkgs/evidence/streams.py:569-611` |
| 15 | the tombstone's millisecond `ts` is accepted | met | fixture `…17:01:00.123Z` validates through `replace_stream` in `test_limit_events_extracted_and_idempotent` |
| 16 | `tools/ledger/schema.md`: the dedup rule under `factory-agents.jsonl`; new sections `limit-events.jsonl` and `main-sessions.jsonl` | met | `tools/ledger/schema.md:60-64` (the MAX rule and §Errata G), `:81-99` (`limit-events.jsonl`), `:100-113` (`main-sessions.jsonl`) |
| 17 | the fixtures as specified | met with one literal deviation | `tests/ledger/fixtures/workflow-dedup/agent-a3333333333333333.jsonl` carries the counts, ids, both tombstones and the 500 line as written; the plan asked for "one line with `message.model: "claude-opus-5[1m]"`" and the fixture puts the bracketed id on all three `msg_fixture_grow` lines (MINOR-3) |
| 18 | the heading's "`backfill` over every transcript … makes it run" | **not met** | `backfill` accumulates correctly across directories (measured: two `wf_` dirs → 2 runs, 4 agents, 2 limit events, no wipe), but it still dies on the first workflow whose journal carries a string finding — MAJOR-1 |

## Red before green

Method: a fresh copy of the branch with `git checkout e4258e0 -- tools/ledger/factory.py pkgs/evidence/streams.py`, the branch's tests and fixtures kept.

Step 1 (`pytest tests/evidence/test_streams_policy.py -q -k 'limit_event or main_session'`):

```
>       assert streams.KINDS["limit-event"]["stream"] == "ledger/limit-events"
E       KeyError: 'limit-event'
E         At index 0 diff: "undeclared kind 'limit-event'" != 'origin: not in enum (main|agent)'
2 failed, 207 deselected
```

Step 2 (`pytest tests/ledger -q`) — every one of the eight new tests red:

```
E           streams.StreamRefused: row 0: role_model: not a model-id; row 0: model_id: not a model-id
E       AttributeError: module 'factory' has no attribute '_model_split'
FAILED test_dedup_uses_max_per_message_id_per_file
FAILED test_dedup_message_count_counts_groups_not_lines
FAILED test_string_finding_is_accepted - AttributeError: 'str' object has no attribute 'get'
FAILED test_agent_label_joined_from_journal_by_agent_id
FAILED test_limit_events_extracted_and_idempotent
FAILED test_non_429_error_yields_no_limit_event
FAILED test_limit_event_rows_carry_no_identity_fields
FAILED test_model_split_bracketed_and_plain
8 failed, 42 passed in 0.89s
```

Green on the branch: `pytest tests/ledger tests/evidence -q` → `550 passed, 1 skipped in 13.43s`.

Note on the plan's predicted reds: Step 2 predicted `assert 7916 == 7912` and
`KeyError: 'message_count'`. Neither can appear — the fixture's bracketed model
id makes `replace_stream` refuse the agent rows before any dedup assertion is
reached. The commit body pastes the reds actually observed rather than the
plan's, which is the right call. Consequence: the dedup arithmetic is never
shown red on its own by the red-before-green pass; the three row-1 mutants
below carry that weight instead, and they carry it.

## Mutants

Each applied to a scratch copy of the branch, the named test run, the tree
restored between mutants. `mutants_total: 22`, `mutants_killed: 19`,
`mutants_outside_named: 7`.

Named by the section — 15 of 15 killed.

| mutant | row | result | failing line |
|---|---|---|---|
| (A) MAX → first value | 1 | KILLED | `E assert 607 == (((7912 + 500) + 100) + 5)` |
| (B) MAX → sum | 1 | KILLED | `E assert 8721 == (((7912 + 500) + 100) + 5)` |
| (E) group key `message.id` alone (module-level `groups`) | 1 | KILLED | `E assert 8017 == (((7912 + 500) + 100) + 5)` |
| a missing `message.id` groups as one | 2 | KILLED | `test_factory_extract_rollup`: `E assert 1500 == 2800` |
| `message_count` counts lines | 3 | KILLED | `E assert 10 == 3` |
| (C) the `str` arm removed | 4 | KILLED | `test_string_finding_is_accepted` fails; stderr shows `finding 0 … skipped` |
| the stderr skip line removed | 4 | KILLED | `E AssertionError: assert 'finding 2 is neither a string nor an object, skipped' in ''` |
| the join keyed on `key` | 5 | KILLED | `E AssertionError: assert None == 'review:N9:r2'` |
| (D) key `("session_id",)` | 6 | KILLED | `E + where 1 = len([{...}])` |
| `resets_at` stored as a string | 6 | KILLED | `E streams.StreamRefused: row 0: resets_at: not a int; row 1: resets_at: not a int` |
| the `status == 429` test dropped | 7 | KILLED | `test_non_429_error_yields_no_limit_event` fails on the 500-with-`quotaLimits` case |
| a `cwd` field copied onto the row | 8 | KILLED | `E streams.StreamRefused: row 0: cwd: forbidden name; row 0: cwd: undeclared field; …` |
| `origin` declared `"id"` | 9 | KILLED | `test_limit_event_and_factory_agent_refusals` at `test_streams_policy.py:497` |
| the split at `]` instead of `[` | 10 | KILLED | `test_model_split_bracketed_and_plain` at `test_factory.py:1682` |
| the name passed through unsplit | 10 | KILLED | `test_model_split_bracketed_and_plain` at `test_factory.py:1682` |

Outside the named set — 7 tried, 4 killed, 3 survived.

| mutant | result | note |
|---|---|---|
| `_limit_event`'s `isinstance(q, dict)` guard → `q = q or {}` | **SURVIVED** | `50 passed` — no fixture and no assertion for a 429 without `quotaLimits` (MINOR-2) |
| `origin` written as `"main"` instead of `"agent"` | KILLED | `E + main` |
| `_usage_groups`' `isinstance(message, dict)` guard dropped | KILLED | `E assert 6 == 3` |
| the suffix keeps its closing bracket (`suffix = rest`) | KILLED | `test_model_split_bracketed_and_plain` |
| `main-session.by_model` cap 8 → 1 | **SURVIVED** | `500 passed` — the cap is untested; `main-session` has no writer until SP6, so not owed here |
| `_read_findings` title precedence `title` before `issue` | **SURVIVED** | `50 passed` — pre-existing line, unchanged by this task; the fixture carries only `issue` |
| `model_suffix` dropped from the agent row | KILLED | `E KeyError: 'model_suffix'` |

## Checks

In a fresh clone of `task/SP2`, `XDG_CACHE_HOME` under the session scratchpad.

| check | command | result |
|---|---|---|
| ledger-unit | `nix build .#checks.x86_64-linux.ledger-unit -L --no-link --rebuild` | pass — `50 passed in 0.84s` |
| evidence-unit | `nix build .#checks.x86_64-linux.evidence-unit -L --no-link --rebuild` | pass — `501 passed in 13.62s` |
| lint | `nix build .#checks.x86_64-linux.lint --no-link --rebuild` | pass — `lint exit=0` |
| pre-commit | `nix develop -c githooks/pre-commit` | exit 1 on the first run, **only** `tasks: docs/OPERATIONS.md queue block was stale and has been regenerated`; the regeneration is the derived `SP2` → `SP6` peel-off, the block is exempt from `touches` and the seat is right not to commit it. Re-run after `git add docs/OPERATIONS.md` → `hook2 exit=0`. Restored; tree clean |
| ruff | `nix develop -c ruff check tools/ledger pkgs/evidence tests/ledger tests/evidence` | `All checks passed!` (exit 0) |
| ruff format | `ruff format --check …` | `83 files already formatted` (exit 0) |
| MAP.md | `python3 pkgs/evidence/repomap.py --root . write` then `git diff --exit-code docs/MAP.md` | exit 0 — the committed `tests/ledger — 18 files` is what the generator produces |
| tasks | `nix develop -c python3 pkgs/evidence/tasks.py --root . check` | silent, exit 0 |

## Touches and commit

`git diff --name-only e4258e0..HEAD` returns exactly the ten declared files plus
`docs/MAP.md`. Nothing outside; no `Deviation:` line needed and none present.
`docs/superpowers/plans/2026-09-08-spend-telemetry.md` untouched;
`docs/OPERATIONS.md` untouched in the commit.

`git rev-list --count e4258e0..HEAD` → `1`. The subject is 328 bytes and
`cmp` against the section's `commit subject` is byte-identical (em dash,
apostrophe and the `(test: …)` tail included). The body states the why and
pastes four red lines and the green lines; the two trailers follow a blank
line:

```
Generated-By: dsh 0.1.2-rc.1 / deepseek/deepseek-v4-pro-0813 (seat headless, factory run sp2)
Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
```

Peer overlap (integration order): `tests/evidence/test_streams_policy.py` is in
SP2's declared `touches` and SP8 — same wave — modified it as an
undeclared-but-disclosed deviation. Both branches append to the module-level
`VALID_ROWS` list and both add a `KINDS` block to `pkgs/evidence/streams.py`;
SP2 appends `("limit-event", …), ("main-session", …)` at
`tests/evidence/test_streams_policy.py:426-427` and its kinds at
`pkgs/evidence/streams.py:548-611`, immediately before the closing `}` of
`KINDS`. Whichever of the two integrates second will conflict on both hunks
(adjacent-line, not semantic). The merge is mechanical — keep both `VALID_ROWS`
entries and both kind blocks — but `evidence-unit` must be re-run on the merge
result, not on either branch, because the two `KINDS` dicts and the shared
`test_no_declared_field_is_named_envelope` / name-fence walks only see each
other after the merge. Nothing in either change is order-dependent beyond that.

## Findings

**MAJOR-1 — a string finding still cannot be written: `extract` refuses the row
it builds, so the extractor still does not run on this host.**

`tools/ledger/factory.py:232-236` sets `severity`, `file_` and `class_` to
`None` for a `str` finding, exactly as the section's Interfaces prescribe. But
the `factory-finding` kind declares them non-nullable, and `file` is part of the
key:

```
pkgs/evidence/streams.py:475            "key": ("run_id", "file", "title_sha256"),
pkgs/evidence/streams.py:482            "severity": "id",
pkgs/evidence/streams.py:483            "file": ("path", ("",), 200),
```

The section did not add `factory-finding.severity` / `.file` to its `streams.py`
edit, and the delivered test never runs the fixture through the writer —
`tests/ledger/test_factory.py:1582` calls `rows = factory._read_findings(journal,
"run")` directly, and `STRFINDING_FIXTURE` appears nowhere else in the suite.
Test row 8 of the section is "every emitted row validates"; the delivered test 8
(`tests/ledger/test_factory.py:1663`) checks only that the two **limit-event**
rows lack `cwd`/`gitBranch`/`slug`.

Reproduced in the clone, on HEAD, with the branch's own fixture:

```
$ nix develop -c python3 -c "
import sys, pathlib, tempfile; sys.path.insert(0,'tools/ledger'); import factory
d=pathlib.Path(tempfile.mkdtemp())/'ledger'; d.mkdir(parents=True)
factory.extract('tests/ledger/fixtures/workflow-strfinding', d)"
  File ".../tools/ledger/factory.py", line 378, in extract
    _merge_jsonl(out / "factory-findings.jsonl", findings)
  File ".../pkgs/evidence/evidence.py", line 148, in replace_stream
    raise streams.StreamRefused(errors)
streams.StreamRefused: row 0: severity: null not allowed; row 0: file: null not allowed
```

Row 0 is the string finding; row 1 (the dict) validates. Since `backfill`
(`tools/ledger/factory.py:383-391` (`def backfill` at :383)) calls `extract` per workflow directory, the
first real transcript carrying a string finding aborts the walk — the
`AttributeError` of Assumption 6 is simply replaced by a `StreamRefused`. The
section's heading claim ("the string-finding crash fixed … `backfill` over
every transcript"), its Interfaces item for `_read_findings`, and its test row 8
are jointly unsatisfiable as written: accepting a string finding requires
`factory-finding.severity` and `.file` to become `("null", "id")` /
`("null", ("path", ("",), 200))` — with the key handling a null `file` — and the
section's `streams.py` edit does not name that change. Hence `plan_defect:
missing-case`, secondary `implementer` (row 8 was stated and the delivered test
does not exercise it; going through `extract` would have surfaced this).

*Note for the fix round:* `file` is one of the three key components, so the kind
change is not a one-liner — either `file` must be permitted to be null in a key
(and `replace_stream`'s key handling proven against it), or the string arm must
supply a non-null placeholder that is not a path. Whichever is chosen, the
discriminating test must be `factory.extract` (or `backfill`) over
`tests/ledger/fixtures/workflow-strfinding`, not `_read_findings` alone, with
the mutant "the fixture is read through `_read_findings` instead of `extract`"
turning it green again.

**MINOR-1 — `_model_split` is the one new function without annotations, and its
`None` return is outside the declared type.** `tools/ledger/factory.py:159`
reads `def _model_split(model_id):` where the section states
`_model_split(model_id) -> tuple[str, str | None]`; `_usage_groups`, `_labels`
and `_limit_event` are all annotated. `:160-161` returns `(None, None)` for a
`None` model (necessary, since `_read_agent`'s `model` may be `None`) — the
stated signature does not admit it.

**MINOR-2 — the `quotaLimits`-object arm of `_limit_event` has no test.** The
section states three gates ("`isApiErrorMessage` true, `apiErrorStatus == 429`
and a `quotaLimits` object `q`"); only the second is exercised. Replacing
`tools/ledger/factory.py:292-293` (`if not isinstance(q, dict): return None`)
with `q = q or {}` leaves `pytest tests/ledger` at `50 passed`. A 429 tombstone
without `quotaLimits`, and a line with `isApiErrorMessage` false, are both
unfixtured.

**MINOR-3 — the dedup fixture puts the bracketed model id on three lines, not
one.** The section's Files line asks for "one line with `message.model:
"claude-opus-5[1m]"`"; `tests/ledger/fixtures/workflow-dedup/agent-a3333333333333333.jsonl:2-4`
carry it on all three `msg_fixture_grow` lines. Behaviourally identical
(`_read_agent` keeps the first assistant line's model), but it is a literal
departure from the fixture spec.

**MINOR-4 — three of the five new fixture files end without a newline.**
`tests/ledger/fixtures/workflow-dedup/agent-a3333333333333333.jsonl`,
`…/agent-a3333333333333334.jsonl`, `…/workflow-dedup/journal.jsonl`,
`…/workflow-strfinding/journal.jsonl` and `…/workflow-strfinding/agent-a4444444444444444.jsonl`
all show `\ No newline at end of file` in the diff. `_read_lines` copes and
`lint` does not object, but SP1b's fix round closed exactly this on its own
fixture; the house habit is a trailing newline.

**MINOR-5 — same-wave collision on `tests/evidence/test_streams_policy.py` and
`pkgs/evidence/streams.py`.** Recorded above under Touches and commit: SP8
touched the same test file as an undeclared-but-disclosed deviation while it sits
inside SP2's declared `touches`. Merge both `VALID_ROWS` entries and both `KINDS`
blocks, then re-run `evidence-unit` on the merge result — the name-fence and
envelope walks in `tests/evidence/test_streams_policy.py:565-577` and `:602-606` iterate all of
`streams.KINDS` and can only see the combined set after the merge.

## Verdict

**REJECTED.** One MAJOR: the task's headline defect is not fixed — a string
finding is accepted by `_read_findings` and then refused by the store, so
`extract` (and therefore `backfill`) still aborts on the transcripts this task
exists to read. Everything else in the section is delivered and well tested:
fifteen of fifteen named mutants die, red-before-green holds for all ten new
tests, the three named checks and the hook are green, the commit is clean and
inside `touches`. The fix round is narrow — make the `factory-finding` kind
admit a string finding (key included), and move test row 4 onto `factory.extract`
so row 8's "every emitted row validates" is actually asserted.
